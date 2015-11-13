__FILENAME__ = mavproxy
#!/usr/bin/env python
'''
mavproxy - a MAVLink proxy program

Copyright Andrew Tridgell 2011
Released under the GNU GPL version 3 or later

'''

import sys, os, struct, math, time, socket
import fnmatch, errno, threading
import serial, Queue, select
import traceback
import select

# allow running without installing
#sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))


from MAVProxy.modules.lib import textconsole
from MAVProxy.modules.lib import rline
from MAVProxy.modules.lib import mp_module
from MAVProxy.modules.lib import dumpstacks

class MPStatus(object):
    '''hold status information about the mavproxy'''
    def __init__(self):
        self.gps	 = None
        self.msgs = {}
        self.msg_count = {}
        self.counters = {'MasterIn' : [], 'MasterOut' : 0, 'FGearIn' : 0, 'FGearOut' : 0, 'Slave' : 0}
        self.setup_mode = opts.setup
        self.mav_error = 0
        self.target_system = 1
        self.target_component = 1
        self.altitude = 0
        self.last_altitude_announce = 0.0
        self.last_distance_announce = 0.0
        self.last_battery_announce = 0
        self.last_avionics_battery_announce = 0
        self.battery_level = -1
        self.voltage_level = -1
        self.avionics_battery_level = -1
        self.exit = False
        self.flightmode = 'MAV'
        self.last_mode_announce = 0
        self.logdir = None
        self.last_heartbeat = 0
        self.last_message = 0
        self.heartbeat_error = False
        self.last_apm_msg = None
        self.last_apm_msg_time = 0
        self.highest_msec = 0
        self.have_gps_lock = False
        self.lost_gps_lock = False
        self.last_gps_lock = 0
        self.watch = None
        self.last_streamrate1 = -1
        self.last_streamrate2 = -1
        self.last_seq = 0
        self.armed = False

    def show(self, f, pattern=None):
        '''write status to status.txt'''
        if pattern is None:
            f.write('Counters: ')
            for c in self.counters:
                f.write('%s:%s ' % (c, self.counters[c]))
            f.write('\n')
            f.write('MAV Errors: %u\n' % self.mav_error)
            f.write(str(self.gps)+'\n')
        for m in sorted(self.msgs.keys()):
            if pattern is not None and not fnmatch.fnmatch(str(m).upper(), pattern.upper()):
                continue
            f.write("%u: %s\n" % (self.msg_count[m], str(self.msgs[m])))

    def write(self):
        '''write status to status.txt'''
        f = open('status.txt', mode='w')
        self.show(f)
        f.close()

def say_text(text, priority='important'):
    '''text output - default function for say()'''
    mpstate.console.writeln(text)

def say(text, priority='important'):
    '''text and/or speech output'''
    mpstate.functions.say(text, priority)

def add_input(cmd, immediate=False):
    '''add some command input to be processed'''
    if immediate:
        process_stdin(cmd)
    else:
        mpstate.input_queue.put(cmd)

class MAVFunctions(object):
    '''core functions available in modules'''
    def __init__(self):
        self.process_stdin = add_input
        self.param_set = param_set
        self.get_mav_param = get_mav_param
        self.say = say_text

class MPState(object):
    '''holds state of mavproxy'''
    def __init__(self):
        self.console = textconsole.SimpleConsole()
        self.map = None
        self.map_functions = {}
        self.vehicle_type = None
        self.vehicle_name = None
        from MAVProxy.modules.lib.mp_settings import MPSettings, MPSetting
        self.settings = MPSettings(
            [ MPSetting('link', int, 1, 'Primary Link', tab='Link', range=(0,4), increment=1),
              MPSetting('streamrate', int, 4, 'Stream rate link1', range=(0,20), increment=1),
              MPSetting('streamrate2', int, 4, 'Stream rate link2', range=(0,20), increment=1),
              MPSetting('heartbeat', int, 1, 'Heartbeat rate', range=(0,5), increment=1),
              MPSetting('mavfwd', bool, True, 'Allow forwarded control'),
              MPSetting('mavfwd_rate', bool, False, 'Allow forwarded rate control'),
              MPSetting('shownoise', bool, True, 'Show non-MAVLink data'),
              
              MPSetting('altreadout', int, 10, 'Altitude Readout',
                        range=(0,100), increment=1, tab='Announcements'),
              MPSetting('distreadout', int, 200, 'Distance Readout', range=(0,10000), increment=1),

              MPSetting('moddebug', int, 0, 'Module Debug Level', range=(0,3), increment=1, tab='Debug'),
              MPSetting('numcells', int, 1, range=(0,10), increment=1),
              MPSetting('flushlogs', bool, False, 'Flush logs on every packet'),
              MPSetting('requireexit', bool, False, 'Require exit command'),

              MPSetting('basealt', int, 0, 'Base Altitude', range=(0,30000), increment=1, tab='Altitude'),
              MPSetting('wpalt', int, 100, 'Default WP Altitude', range=(0,10000), increment=1),
              MPSetting('rallyalt', int, 90, 'Default Rally Altitude', range=(0,10000), increment=1)]
            )

        self.completions = {
            "script" : ["(FILENAME)"],
            "set"    : ["(SETTING)"]
            }

        self.status = MPStatus()

        # master mavlink device
        self.mav_master = None

        # mavlink outputs
        self.mav_outputs = []

        # SITL output
        self.sitl_output = None

        self.mav_param = mavparm.MAVParmDict()
        self.modules = []
        self.public_modules = {}
        self.functions = MAVFunctions()
        self.select_extra = {}
        self.continue_mode = False
        self.aliases = {}

    def module(self, name):
        '''Find a public module (most modules are private)'''
        if name in self.public_modules:
            return self.public_modules[name]
        return None
    
    def master(self):
        '''return the currently chosen mavlink master object'''
        if self.settings.link > len(self.mav_master):
            self.settings.link = 1

        # try to use one with no link error
        if not self.mav_master[self.settings.link-1].linkerror:
            return self.mav_master[self.settings.link-1]
        for m in self.mav_master:
            if not m.linkerror:
                return m
        return self.mav_master[self.settings.link-1]


def get_usec():
    '''time since 1970 in microseconds'''
    return int(time.time() * 1.0e6)

def get_mav_param(param, default=None):
    '''return a EEPROM parameter value'''
    return mpstate.mav_param.get(param, default)

def param_set(name, value, retries=3):
    '''set a parameter'''
    name = name.upper()
    return mpstate.mav_param.mavset(mpstate.master(), name, value, retries=retries)

def cmd_script(args):
    '''run a script'''
    if len(args) < 1:
        print("usage: script <filename>")
        return

    run_script(args[0])

def cmd_set(args):
    '''control mavproxy options'''
    mpstate.settings.command(args)

def cmd_status(args):
    '''show status'''
    if len(args) == 0:
        mpstate.status.show(sys.stdout, pattern=None)
    else:
        for pattern in args:
            mpstate.status.show(sys.stdout, pattern=pattern)

def cmd_setup(args):
    mpstate.status.setup_mode = True
    mpstate.rl.set_prompt("")


def cmd_reset(args):
    print("Resetting master")
    mpstate.master().reset()

def cmd_link(args):
    for master in mpstate.mav_master:
        linkdelay = (mpstate.status.highest_msec - master.highest_msec)*1.0e-3
        if master.linkerror:
            print("link %u down" % (master.linknum+1))
        else:
            print("link %u OK (%u packets, %.2fs delay, %u lost, %.1f%% loss)" % (master.linknum+1,
                                                                                  mpstate.status.counters['MasterIn'][master.linknum],
                                                                                  linkdelay,
                                                                                  master.mav_loss,
                                                                                  master.packet_loss()))

def cmd_watch(args):
    '''watch a mavlink packet pattern'''
    if len(args) == 0:
        mpstate.status.watch = None
        return
    mpstate.status.watch = args[0]
    print("Watching %s" % mpstate.status.watch)

def load_module(modname, quiet=False):
    '''load a module'''
    modpaths = ['MAVProxy.modules.mavproxy_%s' % modname, modname]
    for (m,pm) in mpstate.modules:
        if m.name == modname:
            if not quiet:
                print("module %s already loaded" % modname)
            return False
    for modpath in modpaths:
        try:
            m = import_package(modpath)
            reload(m)
            module = m.init(mpstate)
            if isinstance(module, mp_module.MPModule):
                mpstate.modules.append((module, m))
                if not quiet:
                    print("Loaded module %s" % (modname,))
                return True
            else:
                ex = "%s.init did not return a MPModule instance" % modname
                break
        except ImportError as msg:
            ex = msg
            if mpstate.settings.moddebug > 1:
                import traceback
                print(traceback.format_exc())
    print("Failed to load module: %s" % ex)
    return False

def unload_module(modname):
    '''unload a module'''
    for (m,pm) in mpstate.modules:
        if m.name == modname:
            if hasattr(m, 'unload'):
                m.unload()
            mpstate.modules.remove((m,pm))
            print("Unloaded module %s" % modname)
            return True
    print("Unable to find module %s" % modname)
    return False

def cmd_module(args):
    '''module commands'''
    usage = "usage: module <list|load|reload|unload>"
    if len(args) < 1:
        print(usage)
        return
    if args[0] == "list":
        for (m,pm) in mpstate.modules:
            print("%s: %s" % (m.name, m.description))
    elif args[0] == "load":
        if len(args) < 2:
            print("usage: module load <name>")
            return
        load_module(args[1])
    elif args[0] == "reload":
        if len(args) < 2:
            print("usage: module reload <name>")
            return
        modname = args[1]
        pmodule = None
        for (m,pm) in mpstate.modules:
            if m.name == modname:
                pmodule = pm
        if pmodule is None:
            print("Module %s not loaded" % modname)
            return
        if unload_module(modname):
            reload(pmodule)
            if load_module(modname, quiet=True):
                print("Reloaded module %s" % modname)
    elif args[0] == "unload":
        if len(args) < 2:
            print("usage: module unload <name>")
            return
        modname = os.path.basename(args[1])
        unload_module(modname)
    else:
        print(usage)


def cmd_alias(args):
    '''alias commands'''
    usage = "usage: alias <add|remove|list>"
    if len(args) < 1 or args[0] == "list":
        if len(args) >= 2:
            wildcard = args[1].upper()
        else:
            wildcard = '*'
        for a in sorted(mpstate.aliases.keys()):
            if fnmatch.fnmatch(a.upper(), wildcard):
                print("%-15s : %s" % (a, mpstate.aliases[a]))
    elif args[0] == "add":
        if len(args) < 3:
            print(usage)
            return
        a = args[1]
        mpstate.aliases[a] = ' '.join(args[2:])
    elif args[0] == "remove":
        if len(args) != 2:
            print(usage)
            return
        a = args[1]
        if a in mpstate.aliases:
            mpstate.aliases.pop(a)
        else:
            print("no alias %s" % a)
    else:
        print(usage)
        return

# http://stackoverflow.com/questions/211100/pythons-import-doesnt-work-as-expected
# has info on why this is necessary.

def import_package(name):
    """Given a package name like 'foo.bar.quux', imports the package
    and returns the desired module."""
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


command_map = {
    'script'  : (cmd_script,   'run a script of MAVProxy commands'),
    'setup'   : (cmd_setup,    'go into setup mode'),
    'reset'   : (cmd_reset,    'reopen the connection to the MAVLink master'),
    'status'  : (cmd_status,   'show status'),
    'set'     : (cmd_set,      'mavproxy settings'),
    'link'    : (cmd_link,     'show link status'),
    'watch'   : (cmd_watch,    'watch a MAVLink pattern'),
    'module'  : (cmd_module,   'module commands'),
    'alias'   : (cmd_alias,    'command aliases')
    }

def process_stdin(line):
    '''handle commands from user'''
    if line is None:
        sys.exit(0)
    line = line.strip()

    if mpstate.status.setup_mode:
        # in setup mode we send strings straight to the master
        if line == '.':
            mpstate.status.setup_mode = False
            mpstate.status.flightmode = "MAV"
            mpstate.rl.set_prompt("MAV> ")
            return
        if line != '+++':
            line += '\r'
        for c in line:
            time.sleep(0.01)
            mpstate.master().write(c)
        return

    if not line:
        return

    args = line.split()
    cmd = args[0]
    while cmd in mpstate.aliases:
        line = mpstate.aliases[cmd]
        args = line.split() + args[1:]
        cmd = args[0]
        
    if cmd == 'help':
        k = command_map.keys()
        k.sort()
        for cmd in k:
            (fn, help) = command_map[cmd]
            print("%-15s : %s" % (cmd, help))
        return
    if cmd == 'exit' and mpstate.settings.requireexit:
        reply = raw_input("Are you sure you want to exit? (y/N)")
        if reply.lower() == 'y':
            mpstate.status.exit = True
        return

    if not cmd in command_map:
        for (m,pm) in mpstate.modules:
            if hasattr(m, 'unknown_command'):
                try:
                    if m.unknown_command(args):
                        return
                except Exception as e:
                    print("ERROR in command: %s" % str(e))
        print("Unknown command '%s'" % line)
        return
    (fn, help) = command_map[cmd]
    try:
        fn(args[1:])
    except Exception as e:
        print("ERROR in command: %s" % str(e))
        if mpstate.settings.moddebug > 1:
            traceback.print_exc()


def vcell_to_battery_percent(vcell):
    '''convert a cell voltage to a percentage battery level'''
    if vcell > 4.1:
        # above 4.1 is 100% battery
        return 100.0
    elif vcell > 3.81:
        # 3.81 is 17% remaining, from flight logs
        return 17.0 + 83.0 * (vcell - 3.81) / (4.1 - 3.81)
    elif vcell > 3.2:
        # below 3.2 it degrades fast. It's dead at 3.2
        return 0.0 + 17.0 * (vcell - 3.20) / (3.81 - 3.20)
    # it's dead or disconnected
    return 0.0


def battery_update(SYS_STATUS):
    '''update battery level'''

    # main flight battery
    mpstate.status.battery_level = SYS_STATUS.battery_remaining
    mpstate.status.voltage_level = SYS_STATUS.voltage_battery

    # avionics battery
    if not 'AP_ADC' in mpstate.status.msgs:
        return
    rawvalue = float(mpstate.status.msgs['AP_ADC'].adc2)
    INPUT_VOLTAGE = 4.68
    VOLT_DIV_RATIO = 3.56
    voltage = rawvalue*(INPUT_VOLTAGE/1024.0)*VOLT_DIV_RATIO
    vcell = voltage / mpstate.settings.numcells

    avionics_battery_level = vcell_to_battery_percent(vcell)

    if mpstate.status.avionics_battery_level == -1 or abs(avionics_battery_level-mpstate.status.avionics_battery_level) > 70:
        mpstate.status.avionics_battery_level = avionics_battery_level
    else:
        mpstate.status.avionics_battery_level = (95*mpstate.status.avionics_battery_level + 5*avionics_battery_level)/100

def battery_report():
    batt_mon = get_mav_param('BATT_MONITOR',0)

    #report voltage level only 
    if batt_mon == 3:
        mpstate.console.set_status('Battery', 'Batt: %.2fV' % (float(mpstate.status.voltage_level) / 1000.0), row=1)
    elif batt_mon == 4:
        mpstate.console.set_status('Battery', 'Batt: %u%%/%.2fV' % (mpstate.status.battery_level, (float(mpstate.status.voltage_level) / 1000.0)), row=1)

        rbattery_level = int((mpstate.status.battery_level+5)/10)*10

        if rbattery_level != mpstate.status.last_battery_announce:
            say("Flight battery %u percent" % rbattery_level, priority='notification')
            mpstate.status.last_battery_announce = rbattery_level
        if rbattery_level <= 20:
            say("Flight battery warning")

    else:
        #clear battery status
        mpstate.console.set_status('Battery')

    # avionics battery reporting disabled for now
    return
    avionics_rbattery_level = int((mpstate.status.avionics_battery_level+5)/10)*10

    if avionics_rbattery_level != mpstate.status.last_avionics_battery_announce:
        say("Avionics Battery %u percent" % avionics_rbattery_level, priority='notification')
        mpstate.status.last_avionics_battery_announce = avionics_rbattery_level
    if avionics_rbattery_level <= 20:
        say("Avionics battery warning")


def handle_msec_timestamp(m, master):
    '''special handling for MAVLink packets with a time_boot_ms field'''

    if m.get_type() == 'GLOBAL_POSITION_INT':
        # this is fix time, not boot time
        return

    msec = m.time_boot_ms
    if msec + 30000 < master.highest_msec:
        say('Time has wrapped')
        print('Time has wrapped', msec, master.highest_msec)
        mpstate.status.highest_msec = msec
        for mm in mpstate.mav_master:
            mm.link_delayed = False
            mm.highest_msec = msec
        return

    # we want to detect when a link is delayed
    master.highest_msec = msec
    if msec > mpstate.status.highest_msec:
        mpstate.status.highest_msec = msec
    if msec < mpstate.status.highest_msec and len(mpstate.mav_master) > 1:
        master.link_delayed = True
    else:
        master.link_delayed = False

def report_altitude(altitude):
    '''possibly report a new altitude'''
    master = mpstate.master()
    if getattr(mpstate.console, 'ElevationMap', None) is not None and mpstate.settings.basealt != 0:
        lat = master.field('GLOBAL_POSITION_INT', 'lat', 0)*1.0e-7
        lon = master.field('GLOBAL_POSITION_INT', 'lon', 0)*1.0e-7
        alt1 = mpstate.console.ElevationMap.GetElevation(lat, lon)
        alt2 = mpstate.settings.basealt
        altitude += alt2 - alt1
    mpstate.status.altitude = altitude
    if (int(mpstate.settings.altreadout) > 0 and
        math.fabs(mpstate.status.altitude - mpstate.status.last_altitude_announce) >= int(mpstate.settings.altreadout)):
        mpstate.status.last_altitude_announce = mpstate.status.altitude
        rounded_alt = int(mpstate.settings.altreadout) * ((mpstate.settings.altreadout/2 + int(mpstate.status.altitude)) / int(mpstate.settings.altreadout))
        say("height %u" % rounded_alt, priority='notification')


def master_send_callback(m, master):
    '''called on sending a message'''
    mtype = m.get_type()

    if mtype != 'BAD_DATA' and mpstate.logqueue:
        usec = get_usec()
        usec = (usec & ~3) | 3 # linknum 3
        mpstate.logqueue.put(str(struct.pack('>Q', usec) + m.get_msgbuf()))


def master_callback(m, master):
    '''process mavlink message m on master, sending any messages to recipients'''

    if getattr(m, '_timestamp', None) is None:
        master.post_message(m)
    mpstate.status.counters['MasterIn'][master.linknum] += 1

    if getattr(m, 'time_boot_ms', None) is not None:
        # update link_delayed attribute
        handle_msec_timestamp(m, master)

    mtype = m.get_type()

    # and log them
    if mtype not in ['BAD_DATA','LOG_DATA'] and mpstate.logqueue:
        # put link number in bottom 2 bits, so we can analyse packet
        # delay in saved logs
        usec = get_usec()
        usec = (usec & ~3) | master.linknum
        mpstate.logqueue.put(str(struct.pack('>Q', usec) + m.get_msgbuf()))

    if mtype in [ 'HEARTBEAT', 'GPS_RAW_INT', 'GPS_RAW', 'GLOBAL_POSITION_INT', 'SYS_STATUS' ]:
        if master.linkerror:
            master.linkerror = False
            say("link %u OK" % (master.linknum+1))
        mpstate.status.last_message = time.time()
        master.last_message = mpstate.status.last_message

    if master.link_delayed:
        # don't process delayed packets that cause double reporting
        if mtype in [ 'MISSION_CURRENT', 'SYS_STATUS', 'VFR_HUD',
                      'GPS_RAW_INT', 'SCALED_PRESSURE', 'GLOBAL_POSITION_INT',
                      'NAV_CONTROLLER_OUTPUT' ]:
            return

    if mtype == 'HEARTBEAT' and m.get_srcSystem() != 255:
        if (mpstate.status.target_system != m.get_srcSystem() or
            mpstate.status.target_component != m.get_srcComponent()):
            mpstate.status.target_system = m.get_srcSystem()
            mpstate.status.target_component = m.get_srcComponent()
            say("online system %u component %u" % (mpstate.status.target_system, mpstate.status.target_component),'message')

        if mpstate.status.heartbeat_error:
            mpstate.status.heartbeat_error = False
            say("heartbeat OK")
        if master.linkerror:
            master.linkerror = False
            say("link %u OK" % (master.linknum+1))

        mpstate.status.last_heartbeat = time.time()
        master.last_heartbeat = mpstate.status.last_heartbeat

        armed = mpstate.master().motors_armed()
        if armed != mpstate.status.armed:
            mpstate.status.armed = armed
            if armed:
                say("ARMED")
            else:
                say("DISARMED")

        if master.flightmode != mpstate.status.flightmode and time.time() > mpstate.status.last_mode_announce + 2:
            mpstate.status.flightmode = master.flightmode
            mpstate.status.last_mode_announce = time.time()
            mpstate.rl.set_prompt(mpstate.status.flightmode + "> ")
            say("Mode " + mpstate.status.flightmode)

        if m.type in [mavutil.mavlink.MAV_TYPE_FIXED_WING]:
            mpstate.vehicle_type = 'plane'
            mpstate.vehicle_name = 'ArduPlane'
        elif m.type in [mavutil.mavlink.MAV_TYPE_GROUND_ROVER,
                        mavutil.mavlink.MAV_TYPE_SURFACE_BOAT,
                        mavutil.mavlink.MAV_TYPE_SUBMARINE]:
            mpstate.vehicle_type = 'rover'
            mpstate.vehicle_name = 'APMrover2'
        elif m.type in [mavutil.mavlink.MAV_TYPE_QUADROTOR,
                        mavutil.mavlink.MAV_TYPE_COAXIAL,
                        mavutil.mavlink.MAV_TYPE_HEXAROTOR,
                        mavutil.mavlink.MAV_TYPE_OCTOROTOR,
                        mavutil.mavlink.MAV_TYPE_TRICOPTER,
                        mavutil.mavlink.MAV_TYPE_HELICOPTER]:
            mpstate.vehicle_type = 'copter'
            mpstate.vehicle_name = 'ArduCopter'
        elif m.type in [mavutil.mavlink.MAV_TYPE_ANTENNA_TRACKER]:
            mpstate.vehicle_type = 'antenna'
            mpstate.vehicle_name = 'AntennaTracker'
        
    elif mtype == 'STATUSTEXT':
        if m.text != mpstate.status.last_apm_msg or time.time() > mpstate.status.last_apm_msg_time+2:
            mpstate.console.writeln("APM: %s" % m.text, bg='red')
            mpstate.status.last_apm_msg = m.text
            mpstate.status.last_apm_msg_time = time.time()

    elif mtype == "SYS_STATUS":
        battery_update(m)

    elif mtype == "VFR_HUD":
        have_gps_fix = False
        if 'GPS_RAW' in mpstate.status.msgs and mpstate.status.msgs['GPS_RAW'].fix_type == 2:
            have_gps_fix = True
        if 'GPS_RAW_INT' in mpstate.status.msgs and mpstate.status.msgs['GPS_RAW_INT'].fix_type == 3:
            have_gps_fix = True
        if have_gps_fix and not mpstate.status.have_gps_lock and m.alt != 0:
                say("GPS lock at %u meters" % m.alt, priority='notification')
                mpstate.status.have_gps_lock = True

    elif mtype == "GPS_RAW":
        if mpstate.status.have_gps_lock:
            if m.fix_type != 2 and not mpstate.status.lost_gps_lock and (time.time() - mpstate.status.last_gps_lock) > 3:
                say("GPS fix lost")
                mpstate.status.lost_gps_lock = True
            if m.fix_type == 2 and mpstate.status.lost_gps_lock:
                say("GPS OK")
                mpstate.status.lost_gps_lock = False
            if m.fix_type == 2:
                mpstate.status.last_gps_lock = time.time()

    elif mtype == "GPS_RAW_INT":
        if mpstate.status.have_gps_lock:
            if m.fix_type != 3 and not mpstate.status.lost_gps_lock and (time.time() - mpstate.status.last_gps_lock) > 3:
                say("GPS fix lost")
                mpstate.status.lost_gps_lock = True
            if m.fix_type == 3 and mpstate.status.lost_gps_lock:
                say("GPS OK")
                mpstate.status.lost_gps_lock = False
            if m.fix_type == 3:
                mpstate.status.last_gps_lock = time.time()

    elif mtype == "NAV_CONTROLLER_OUTPUT" and mpstate.status.flightmode == "AUTO" and mpstate.settings.distreadout:
        rounded_dist = int(m.wp_dist/mpstate.settings.distreadout)*mpstate.settings.distreadout
        if math.fabs(rounded_dist - mpstate.status.last_distance_announce) >= mpstate.settings.distreadout:
            if rounded_dist != 0:
                say("%u" % rounded_dist, priority="progress")
            mpstate.status.last_distance_announce = rounded_dist
    
    elif mtype == "GLOBAL_POSITION_INT":
        report_altitude(m.relative_alt*0.001)

    elif mtype == "COMPASSMOT_STATUS":
        print(m)

    elif mtype == "BAD_DATA":
        if mpstate.settings.shownoise and mavutil.all_printable(m.data):
            mpstate.console.write(str(m.data), bg='red')
    elif mtype in [ "COMMAND_ACK", "MISSION_ACK" ]:
        mpstate.console.writeln("Got MAVLink msg: %s" % m)
    else:
        #mpstate.console.writeln("Got MAVLink msg: %s" % m)
        pass

    if mpstate.status.watch is not None:
        if fnmatch.fnmatch(m.get_type().upper(), mpstate.status.watch.upper()):
            mpstate.console.writeln(m)

    # keep the last message of each type around
    mpstate.status.msgs[m.get_type()] = m
    if not m.get_type() in mpstate.status.msg_count:
        mpstate.status.msg_count[m.get_type()] = 0
    mpstate.status.msg_count[m.get_type()] += 1

    # don't pass along bad data
    if mtype != "BAD_DATA":
        # pass messages along to listeners, except for REQUEST_DATA_STREAM, which
        # would lead a conflict in stream rate setting between mavproxy and the other
        # GCS
        if mpstate.settings.mavfwd_rate or mtype != 'REQUEST_DATA_STREAM':
            for r in mpstate.mav_outputs:
                r.write(m.get_msgbuf())

        # pass to modules
        for (mod,pm) in mpstate.modules:
            if not hasattr(mod, 'mavlink_packet'):
                continue
            try:
                mod.mavlink_packet(m)
            except Exception as msg:
                if mpstate.settings.moddebug == 1:
                    print(msg)
                elif mpstate.settings.moddebug > 1:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_exception(exc_type, exc_value, exc_traceback,
                                              limit=2, file=sys.stdout)

def process_master(m):
    '''process packets from the MAVLink master'''
    try:
        s = m.recv(16*1024)
    except Exception:
        time.sleep(0.1)
        return
    # prevent a dead serial port from causing the CPU to spin. The user hitting enter will
    # cause it to try and reconnect
    if len(s) == 0:
        time.sleep(0.1)
        return
    
    if mpstate.logqueue_raw:
        mpstate.logqueue_raw.put(str(s))

    if mpstate.status.setup_mode:
        sys.stdout.write(str(s))
        sys.stdout.flush()
        return

    if m.first_byte and opts.auto_protocol:
        m.auto_mavlink_version(s)
    msgs = m.mav.parse_buffer(s)
    if msgs:
        for msg in msgs:
            if getattr(m, '_timestamp', None) is None:
                m.post_message(msg)
            if msg.get_type() == "BAD_DATA":
                if opts.show_errors:
                    mpstate.console.writeln("MAV error: %s" % msg)
                mpstate.status.mav_error += 1



def process_mavlink(slave):
    '''process packets from MAVLink slaves, forwarding to the master'''
    try:
        buf = slave.recv()
    except socket.error:
        return
    try:
        if slave.first_byte and opts.auto_protocol:
            slave.auto_mavlink_version(buf)
        msgs = slave.mav.parse_buffer(buf)
    except mavutil.mavlink.MAVError as e:
        mpstate.console.error("Bad MAVLink slave message from %s: %s" % (slave.address, e.message))
        return
    if msgs is None:
        return
    if mpstate.settings.mavfwd and not mpstate.status.setup_mode:
        for m in msgs:
            mpstate.master().write(m.get_msgbuf())
    mpstate.status.counters['Slave'] += 1


def mkdir_p(dir):
    '''like mkdir -p'''
    if not dir:
        return
    if dir.endswith("/"):
        mkdir_p(dir[:-1])
        return
    if os.path.isdir(dir):
        return
    mkdir_p(os.path.dirname(dir))
    os.mkdir(dir)

def log_writer():
    '''log writing thread'''
    while True:
        mpstate.logfile_raw.write(mpstate.logqueue_raw.get())
        while not mpstate.logqueue_raw.empty():
            mpstate.logfile_raw.write(mpstate.logqueue_raw.get())
        while not mpstate.logqueue.empty():
            mpstate.logfile.write(mpstate.logqueue.get())
        if mpstate.settings.flushlogs:
            mpstate.logfile.flush()
            mpstate.logfile_raw.flush()

def open_logs():
    '''open log files'''
    if opts.append_log or opts.continue_mode:
        mode = 'a'
    else:
        mode = 'w'
    logfile = opts.logfile
    if opts.aircraft is not None:
        if opts.mission is not None:
            print(opts.mission)
            dirname = "%s/logs/%s/Mission%s" % (opts.aircraft, time.strftime("%Y-%m-%d"), opts.mission)
        else:
            dirname = "%s/logs/%s" % (opts.aircraft, time.strftime("%Y-%m-%d"))
        mkdir_p(dirname)
        highest = None
        for i in range(1, 10000):
            fdir = os.path.join(dirname, 'flight%u' % i)
            if not os.path.exists(fdir):
                break
            highest = fdir
        if mpstate.continue_mode and highest is not None:
            fdir = highest
        elif os.path.exists(fdir):
            print("Flight logs full")
            sys.exit(1)
        mkdir_p(fdir)
        print(fdir)
        logfile = os.path.join(fdir, 'flight.tlog')
        mpstate.status.logdir = fdir
    mpstate.logfile_name = logfile
    mpstate.logfile = open(logfile, mode=mode)
    mpstate.logfile_raw = open(logfile+'.raw', mode=mode)
    print("Logging to %s" % logfile)

    # queues for logging
    mpstate.logqueue = Queue.Queue()
    mpstate.logqueue_raw = Queue.Queue()

    # use a separate thread for writing to the logfile to prevent
    # delays during disk writes (important as delays can be long if camera
    # app is running)
    t = threading.Thread(target=log_writer)
    t.daemon = True
    t.start()

def set_stream_rates():
    '''set mavlink stream rates'''
    if (not msg_period.trigger() and
        mpstate.status.last_streamrate1 == mpstate.settings.streamrate and
        mpstate.status.last_streamrate2 == mpstate.settings.streamrate2):
        return
    mpstate.status.last_streamrate1 = mpstate.settings.streamrate
    mpstate.status.last_streamrate2 = mpstate.settings.streamrate2
    for master in mpstate.mav_master:
        if master.linknum == 0:
            rate = mpstate.settings.streamrate
        else:
            rate = mpstate.settings.streamrate2
        if rate != -1:
            master.mav.request_data_stream_send(mpstate.status.target_system, mpstate.status.target_component,
                                                mavutil.mavlink.MAV_DATA_STREAM_ALL,
                                                rate, 1)

def check_link_status():
    '''check status of master links'''
    tnow = time.time()
    if mpstate.status.last_message != 0 and tnow > mpstate.status.last_message + 5:
        say("no link")
        mpstate.status.heartbeat_error = True
    for master in mpstate.mav_master:
        if not master.linkerror and tnow > master.last_message + 5:
            say("link %u down" % (master.linknum+1))
            master.linkerror = True

def send_heartbeat(master):
    if master.mavlink10():
        master.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                                  0, 0, 0)
    else:
        MAV_GROUND = 5
        MAV_AUTOPILOT_NONE = 4
        master.mav.heartbeat_send(MAV_GROUND, MAV_AUTOPILOT_NONE)

def periodic_tasks():
    '''run periodic checks'''
    if mpstate.status.setup_mode:
        return

    if mpstate.settings.heartbeat != 0:
        heartbeat_period.frequency = mpstate.settings.heartbeat

    if heartbeat_period.trigger() and mpstate.settings.heartbeat != 0:
        mpstate.status.counters['MasterOut'] += 1
        for master in mpstate.mav_master:
            send_heartbeat(master)

    if heartbeat_check_period.trigger():
        check_link_status()

    set_stream_rates()

    if battery_period.trigger():
        battery_report()

    # call optional module idle tasks. These are called at several hundred Hz
    for (m,pm) in mpstate.modules:
        if hasattr(m, 'idle_task'):
            try:
                m.idle_task()
            except Exception as msg:
                if mpstate.settings.moddebug == 1:
                    print(msg)
                elif mpstate.settings.moddebug > 1:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_exception(exc_type, exc_value, exc_traceback,
                                              limit=2, file=sys.stdout)


def main_loop():
    '''main processing loop'''
    if not mpstate.status.setup_mode and not opts.nowait:
        for master in mpstate.mav_master:
            send_heartbeat(master)
            master.wait_heartbeat()
        set_stream_rates()

    while True:
        if mpstate is None or mpstate.status.exit:
            return
        while not mpstate.input_queue.empty():
            line = mpstate.input_queue.get()
            cmds = line.split(';')
            for c in cmds:
                process_stdin(c)

        for master in mpstate.mav_master:
            if master.fd is None:
                if master.port.inWaiting() > 0:
                    process_master(master)

        periodic_tasks()

        rin = []
        for master in mpstate.mav_master:
            if master.fd is not None:
                rin.append(master.fd)
        for m in mpstate.mav_outputs:
            rin.append(m.fd)
        if rin == []:
            time.sleep(0.0001)
            continue

        for fd in mpstate.select_extra:
            rin.append(fd)
        try:
            (rin, win, xin) = select.select(rin, [], [], 0.01)
        except select.error:
            continue

        if mpstate is None:
            return

        for fd in rin:
            for master in mpstate.mav_master:
                if fd == master.fd:
                    process_master(master)
                    continue
            for m in mpstate.mav_outputs:
                if fd == m.fd:
                    process_mavlink(m)
                    continue

            # this allow modules to register their own file descriptors
            # for the main select loop
            if fd in mpstate.select_extra:
                try:
                    # call the registered read function
                    (fn, args) = mpstate.select_extra[fd]
                    fn(args)
                except Exception as msg:
                    if mpstate.settings.moddebug == 1:
                        print(msg)
                    # on an exception, remove it from the select list
                    mpstate.select_extra.pop(fd)



def input_loop():
    '''wait for user input'''
    while mpstate.status.exit != True:
        try:
            if mpstate.status.exit != True:
                line = raw_input(mpstate.rl.prompt)
        except EOFError:
            mpstate.status.exit = True
            sys.exit(1)
        mpstate.input_queue.put(line)


def run_script(scriptfile):
    '''run a script file'''
    try:
        f = open(scriptfile, mode='r')
    except Exception:
        return
    mpstate.console.writeln("Running script %s" % scriptfile)
    for line in f:
        line = line.strip()
        if line == "" or line.startswith('#'):
            continue
        if line.startswith('@'):
            line = line[1:]
        else:
            mpstate.console.writeln("-> %s" % line)
        process_stdin(line)
    f.close()

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser("mavproxy.py [options]")

    parser.add_option("--master", dest="master", action='append',
                      metavar="DEVICE[,BAUD]", help="MAVLink master port and optional baud rate",
                      default=[])
    parser.add_option("--out", dest="output", action='append',
                      metavar="DEVICE[,BAUD]", help="MAVLink output port and optional baud rate",
                      default=[])
    parser.add_option("--baudrate", dest="baudrate", type='int',
                      help="default serial baud rate", default=115200)
    parser.add_option("--sitl", dest="sitl",  default=None, help="SITL output port")
    parser.add_option("--streamrate",dest="streamrate", default=4, type='int',
                      help="MAVLink stream rate")
    parser.add_option("--source-system", dest='SOURCE_SYSTEM', type='int',
                      default=255, help='MAVLink source system for this GCS')
    parser.add_option("--target-system", dest='TARGET_SYSTEM', type='int',
                      default=1, help='MAVLink target master system')
    parser.add_option("--target-component", dest='TARGET_COMPONENT', type='int',
                      default=1, help='MAVLink target master component')
    parser.add_option("--logfile", dest="logfile", help="MAVLink master logfile",
                      default='mav.tlog')
    parser.add_option("-a", "--append-log", dest="append_log", help="Append to log files",
                      action='store_true', default=False)
    parser.add_option("--quadcopter", dest="quadcopter", help="use quadcopter controls",
                      action='store_true', default=False)
    parser.add_option("--setup", dest="setup", help="start in setup mode",
                      action='store_true', default=False)
    parser.add_option("--nodtr", dest="nodtr", help="disable DTR drop on close",
                      action='store_true', default=False)
    parser.add_option("--show-errors", dest="show_errors", help="show MAVLink error packets",
                      action='store_true', default=False)
    parser.add_option("--speech", dest="speech", help="use text to speach",
                      action='store_true', default=False)
    parser.add_option("--num-cells", dest="num_cells", help="number of LiPo battery cells",
                      type='int', default=0)
    parser.add_option("--aircraft", dest="aircraft", help="aircraft name", default=None)
    parser.add_option("--cmd", dest="cmd", help="initial commands", default=None)
    parser.add_option("--console", action='store_true', help="use GUI console")
    parser.add_option("--map", action='store_true', help="load map module")
    parser.add_option(
        '--load-module',
        action='append',
        default=[],
        help='Load the specified module. Can be used multiple times, or with a comma separated list')
    parser.add_option("--mav09", action='store_true', default=False, help="Use MAVLink protocol 0.9")
    parser.add_option("--auto-protocol", action='store_true', default=False, help="Auto detect MAVLink protocol version")
    parser.add_option("--nowait", action='store_true', default=False, help="don't wait for HEARTBEAT on startup")
    parser.add_option("--continue", dest='continue_mode', action='store_true', default=False, help="continue logs")
    parser.add_option("--dialect",  default="ardupilotmega", help="MAVLink dialect")
    parser.add_option("--rtscts",  action='store_true', help="enable hardware RTS/CTS flow control")
    parser.add_option("--mission", dest="mission", help="mission name", default=None)

    (opts, args) = parser.parse_args()

    # warn people about ModemManager which interferes badly with APM and Pixhawk
    if os.path.exists("/usr/sbin/ModemManager"):
        print("WARNING: You should uninstall ModemManager as it conflicts with APM and Pixhawk")

    if opts.mav09:
        os.environ['MAVLINK09'] = '1'
    from pymavlink import mavutil, mavparm
    mavutil.set_dialect(opts.dialect)

    # global mavproxy state
    mpstate = MPState()
    mpstate.status.exit = False
    mpstate.command_map = command_map
    mpstate.continue_mode = opts.continue_mode

    if opts.speech:
        # start the speech-dispatcher early, so it doesn't inherit any ports from
        # modules/mavutil
        load_module('speech')

    if not opts.master:
        serial_list = mavutil.auto_detect_serial(preferred_list=['*FTDI*',"*Arduino_Mega_2560*", "*3D_Robotics*", "*USB_to_UART*"])
        if len(serial_list) == 1:
            opts.master = [serial_list[0].device]
        else:
            print('''
Please choose a MAVLink master with --master
For example:
    --master=com14
    --master=/dev/ttyUSB0
    --master=127.0.0.1:14550

Auto-detected serial ports are:
''')
            for port in serial_list:
                print("%s" % port)
            sys.exit(1)

    # container for status information
    mpstate.status.target_system = opts.TARGET_SYSTEM
    mpstate.status.target_component = opts.TARGET_COMPONENT

    mpstate.mav_master = []

    # open master link
    for mdev in opts.master:
        if ',' in mdev and not os.path.exists(mdev):
            port, baud = mdev.split(',')
        else:
            port, baud = mdev, opts.baudrate

        m = mavutil.mavlink_connection(port, autoreconnect=True, baud=int(baud))
        m.mav.set_callback(master_callback, m)
        if hasattr(m.mav, 'set_send_callback'):
            m.mav.set_send_callback(master_send_callback, m)
        if opts.rtscts:
            m.set_rtscts(True)
        m.linknum = len(mpstate.mav_master)
        m.linkerror = False
        m.link_delayed = False
        m.last_heartbeat = 0
        m.last_message = 0
        m.highest_msec = 0
        mpstate.mav_master.append(m)
        mpstate.status.counters['MasterIn'].append(0)

    # log all packets from the master, for later replay
    open_logs()

    # open any mavlink UDP ports
    for p in opts.output:
        if ',' in p and not os.path.exists(p):
            port, baud = p.split(',')            
        else:
            port, baud = p, opts.baudrate

        mpstate.mav_outputs.append(mavutil.mavlink_connection(port, baud=int(baud), input=False))

    if opts.sitl:
        mpstate.sitl_output = mavutil.mavudp(opts.sitl, input=False)

    mpstate.settings.numcells = opts.num_cells
    mpstate.settings.streamrate = opts.streamrate
    mpstate.settings.streamrate2 = opts.streamrate

    msg_period = mavutil.periodic_event(1.0/15)
    heartbeat_period = mavutil.periodic_event(1)
    battery_period = mavutil.periodic_event(0.1)
    heartbeat_check_period = mavutil.periodic_event(0.33)

    mpstate.input_queue = Queue.Queue()
    mpstate.rl = rline.rline("MAV> ", mpstate)
    if opts.setup:
        mpstate.rl.set_prompt("")

    if 'HOME' in os.environ and not opts.setup:
        start_script = os.path.join(os.environ['HOME'], ".mavinit.scr")
        if os.path.exists(start_script):
            run_script(start_script)

    if opts.aircraft is not None:
        start_script = os.path.join(opts.aircraft, "mavinit.scr")
        if os.path.exists(start_script):
            run_script(start_script)
        else:
            print("no script %s" % start_script)

    if not opts.setup:
        # some core functionality is in modules
        standard_modules = ['log', 'wp', 'rally','fence','param','relay',
                            'tuneopt','arm','mode','calibration','rc','auxopt','misc']
        for m in standard_modules:
            load_module(m, quiet=True)

    if opts.console:
        process_stdin('module load console')

    if opts.map:
        process_stdin('module load map')

    for module in opts.load_module:
        modlist = module.split(',')
        for mod in modlist:
            process_stdin('module load %s' % mod)

    if opts.cmd is not None:
        cmds = opts.cmd.split(';')
        for c in cmds:
            process_stdin(c)

    # run main loop as a thread
    mpstate.status.thread = threading.Thread(target=main_loop)
    mpstate.status.thread.daemon = True
    mpstate.status.thread.start()

    # use main program for input. This ensures the terminal cleans
    # up on exit
    while (mpstate.status.exit != True):
        try:
            input_loop()
        except KeyboardInterrupt:
            if mpstate.settings.requireexit:
                print("Interrupt caught.  Use 'exit' to quit MAVProxy.")

                #Just lost the map and console, get them back:
                for (m,pm) in mpstate.modules:
                    if m.name in ["map", "console"]:
                        if hasattr(m, 'unload'):
                            try:
                                m.unload()
                            except Exception:
                                pass
                        reload(m)
                        m.init(mpstate)   

            else:
                mpstate.status.exit = True
                sys.exit(1)

    #this loop executes after leaving the above loop and is for cleanup on exit
    for (m,pm) in mpstate.modules:
        if hasattr(m, 'unload'):
            print("Unloading module %s" % m.name)
            m.unload()
        
    sys.exit(1)

########NEW FILE########
__FILENAME__ = geo_reference
"""
This module adapted ANUGA
https://anuga.anu.edu.au/

"""


#FIXME: Ensure that all attributes of a georef are treated everywhere
#and unit test

import types, sys
import copy
import numpy as num


DEFAULT_ZONE = -1
TITLE = '#geo reference' + "\n" # this title is referred to in the test format

DEFAULT_PROJECTION = 'UTM'
DEFAULT_DATUM = 'wgs84'
DEFAULT_UNITS = 'm'
DEFAULT_FALSE_EASTING = 500000
DEFAULT_FALSE_NORTHING = 10000000    # Default for southern hemisphere


##
# @brief A class for ...
class Geo_reference:
    """
    Attributes of the Geo_reference class:
        .zone           The UTM zone (default is -1)
        .false_easting  ??
        .false_northing ??
        .datum          The Datum used (default is wgs84)
        .projection     The projection used (default is 'UTM')
        .units          The units of measure used (default metres)
        .xllcorner      The X coord of origin (default is 0.0 wrt UTM grid)
        .yllcorner      The y coord of origin (default is 0.0 wrt UTM grid)
        .is_absolute    ??

    """

    ##
    # @brief Instantiate an instance of class Geo_reference.
    # @param zone The UTM zone.
    # @param xllcorner X coord of origin of georef.
    # @param yllcorner Y coord of origin of georef.
    # @param datum ??
    # @param projection The projection used (default UTM).
    # @param units Units used in measuring distance (default m).
    # @param false_easting ??
    # @param false_northing ??
    # @param NetCDFObject NetCDF file *handle* to write to.
    # @param ASCIIFile ASCII text file *handle* to write to.
    # @param read_title Title of the georeference text.
    def __init__(self,
                 zone=DEFAULT_ZONE,
                 xllcorner=0.0,
                 yllcorner=0.0,
                 datum=DEFAULT_DATUM,
                 projection=DEFAULT_PROJECTION,
                 units=DEFAULT_UNITS,
                 false_easting=DEFAULT_FALSE_EASTING,
                 false_northing=DEFAULT_FALSE_NORTHING,
                 NetCDFObject=None,
                 ASCIIFile=None,
                 read_title=None):
        """
        input:
        NetCDFObject - a handle to the netCDF file to be written to
        ASCIIFile - a handle to the text file
        read_title - the title of the georeference text, if it was read in.
         If the function that calls this has already read the title line,
         it can't unread it, so this info has to be passed.
         If you know of a way to unread this info, then tell us.

         Note, the text file only saves a sub set of the info the
         points file does.  Currently the info not written in text
         must be the default info, since ANUGA assumes it isn't
         changing.
        """

        if zone is None:
            zone = DEFAULT_ZONE
        self.false_easting = int(false_easting)
        self.false_northing = int(false_northing)
        self.datum = datum
        self.projection = projection
        self.zone = int(zone)
        self.units = units
        self.xllcorner = float(xllcorner)
        self.yllcorner = float(yllcorner)
            
        if NetCDFObject is not None:
            self.read_NetCDF(NetCDFObject)

        if ASCIIFile is not None:
            self.read_ASCII(ASCIIFile, read_title=read_title)
            
        # Set flag for absolute points (used by get_absolute)    
        self.absolute = num.allclose([self.xllcorner, self.yllcorner], 0)
            

    def get_xllcorner(self):
        return self.xllcorner

    ##
    # @brief Get the Y coordinate of the origin of this georef.
    def get_yllcorner(self):
        return self.yllcorner

    ##
    # @brief Get the zone of this georef.
    def get_zone(self):
        return self.zone

    ##
    # @brief Write <something> to an open NetCDF file.
    # @param outfile Handle to open NetCDF file.
    def write_NetCDF(self, outfile):
        outfile.xllcorner = self.xllcorner
        outfile.yllcorner = self.yllcorner
        outfile.zone = self.zone

        outfile.false_easting = self.false_easting
        outfile.false_northing = self.false_northing

        outfile.datum = self.datum
        outfile.projection = self.projection
        outfile.units = self.units

    ##
    # @brief Read data from an open NetCDF file.
    # @param infile Handle to open NetCDF file.
    def read_NetCDF(self, infile):
        self.xllcorner = float(infile.xllcorner[0])
        self.yllcorner = float(infile.yllcorner[0])
        self.zone = int(infile.zone[0])

        try:
            self.false_easting = int(infile.false_easting[0])
            self.false_northing = int(infile.false_northing[0])

            self.datum = infile.datum
            self.projection = infile.projection
            self.units = infile.units
        except:
            pass

        if self.false_easting != DEFAULT_FALSE_EASTING:
            print "WARNING: False easting of %f specified." % self.false_easting
            print "Default false easting is %f." % DEFAULT_FALSE_EASTING
            print "ANUGA does not correct for differences in False Eastings."

        if self.false_northing != DEFAULT_FALSE_NORTHING:
            print ("WARNING: False northing of %f specified."
                   % self.false_northing)
            print "Default false northing is %f." % DEFAULT_FALSE_NORTHING
            print "ANUGA does not correct for differences in False Northings."

        if self.datum.upper() != DEFAULT_DATUM.upper():
            print "WARNING: Datum of %s specified." % self.datum
            print "Default Datum is %s." % DEFAULT_DATUM
            print "ANUGA does not correct for differences in datums."

        if self.projection.upper() != DEFAULT_PROJECTION.upper():
            print "WARNING: Projection of %s specified." % self.projection
            print "Default Projection is %s." % DEFAULT_PROJECTION
            print "ANUGA does not correct for differences in Projection."

        if self.units.upper() != DEFAULT_UNITS.upper():
            print "WARNING: Units of %s specified." % self.units
            print "Default units is %s." % DEFAULT_UNITS
            print "ANUGA does not correct for differences in units."

################################################################################
# ASCII files with geo-refs are currently not used
################################################################################

    ##
    # @brief Write georef data to an open text file.
    # @param fd Handle to open text file.
    def write_ASCII(self, fd):
        fd.write(TITLE)
        fd.write(str(self.zone) + "\n")
        fd.write(str(self.xllcorner) + "\n")
        fd.write(str(self.yllcorner) + "\n")

    ##
    # @brief Read georef data from an open text file.
    # @param fd Handle to open text file.
    def read_ASCII(self, fd, read_title=None):
        try:
            if read_title == None:
                read_title = fd.readline()     # remove the title line
            if read_title[0:2].upper() != TITLE[0:2].upper():
                msg = ('File error.  Expecting line: %s.  Got this line: %s'
                       % (TITLE, read_title))
                raise TitleError, msg
            self.zone = int(fd.readline())
            self.xllcorner = float(fd.readline())
            self.yllcorner = float(fd.readline())
        except SyntaxError:
            msg = 'File error.  Got syntax error while parsing geo reference'
            raise ParsingError, msg

        # Fix some assertion failures
        if isinstance(self.zone, num.ndarray) and self.zone.shape == ():
            self.zone = self.zone[0]
        if (isinstance(self.xllcorner, num.ndarray) and
                self.xllcorner.shape == ()):
            self.xllcorner = self.xllcorner[0]
        if (isinstance(self.yllcorner, num.ndarray) and
                self.yllcorner.shape == ()):
            self.yllcorner = self.yllcorner[0]

        assert (type(self.xllcorner) == types.FloatType)
        assert (type(self.yllcorner) == types.FloatType)
        assert (type(self.zone) == types.IntType)

################################################################################

    ##
    # @brief Change points to be absolute wrt new georef 'points_geo_ref'.
    # @param points The points to change.
    # @param points_geo_ref The new georef to make points absolute wrt.
    # @return The changed points.
    # @note If 'points' is a list then a changed list is returned.
    def change_points_geo_ref(self, points, points_geo_ref=None):
        """Change the geo reference of a list or numeric array of points to
        be this reference.(The reference used for this object)
        If the points do not have a geo ref, assume 'absolute' values
        """
        import copy
       
        # remember if we got a list
        is_list = isinstance(points, list)

        points = ensure_numeric(points, num.float)

        # sanity checks	
        if len(points.shape) == 1:
            #One point has been passed
            msg = 'Single point must have two elements'
            assert len(points) == 2, msg
            points = num.reshape(points, (1,2))

        msg = 'Points array must be two dimensional.\n'
        msg += 'I got %d dimensions' %len(points.shape)
        assert len(points.shape) == 2, msg

        msg = 'Input must be an N x 2 array or list of (x,y) values. '
        msg += 'I got an %d x %d array' %points.shape    
        assert points.shape[1] == 2, msg                

        # FIXME (Ole): Could also check if zone, xllcorner, yllcorner 
        # are identical in the two geo refs.    
        if points_geo_ref is not self:
            # If georeferences are different
            points = copy.copy(points) # Don't destroy input                    
            if not points_geo_ref is None:
                # Convert points to absolute coordinates
                points[:,0] += points_geo_ref.xllcorner 
                points[:,1] += points_geo_ref.yllcorner 
        
            # Make points relative to primary geo reference
            points[:,0] -= self.xllcorner 
            points[:,1] -= self.yllcorner

        if is_list:
            points = points.tolist()
            
        return points

    def is_absolute(self):
        """Return True if xllcorner==yllcorner==0 indicating that points
        in question are absolute.
        """
        
        # FIXME(Ole): It is unfortunate that decision about whether points
        # are absolute or not lies with the georeference object. Ross pointed this out.
        # Moreover, this little function is responsible for a large fraction of the time
        # using in data fitting (something in like 40 - 50%.
        # This was due to the repeated calls to allclose.
        # With the flag method fitting is much faster (18 Mar 2009).

        # FIXME(Ole): HACK to be able to reuse data already cached (18 Mar 2009). 
        # Remove at some point
        if not hasattr(self, 'absolute'):
            self.absolute = num.allclose([self.xllcorner, self.yllcorner], 0)
            
        # Return absolute flag    
        return self.absolute

    def get_absolute(self, points):
        """Given a set of points geo referenced to this instance,
        return the points as absolute values.
        """

        # remember if we got a list
        is_list = isinstance(points, list)

        points = ensure_numeric(points, num.float)
        if len(points.shape) == 1:
            # One point has been passed
            msg = 'Single point must have two elements'
            if not len(points) == 2:
                raise ShapeError, msg    


        msg = 'Input must be an N x 2 array or list of (x,y) values. '
        msg += 'I got an %d x %d array' %points.shape    
        if not points.shape[1] == 2:
            raise ShapeError, msg    
            
        
        # Add geo ref to points
        if not self.is_absolute():
            points = copy.copy(points) # Don't destroy input                    
            points[:,0] += self.xllcorner 
            points[:,1] += self.yllcorner

        
        if is_list:
            points = points.tolist()
             
        return points

    ##
    # @brief Convert points to relative measurement.
    # @param points Points to convert to relative measurements.
    # @return A set of points relative to the geo_reference instance.
    def get_relative(self, points):
        """Given a set of points in absolute UTM coordinates,
        make them relative to this geo_reference instance,
        return the points as relative values.

        This is the inverse of get_absolute.
        """

        # remember if we got a list
        is_list = isinstance(points, list)

        points = ensure_numeric(points, num.float)
        if len(points.shape) == 1:
            #One point has been passed
            msg = 'Single point must have two elements'
            if not len(points) == 2:
                raise ShapeError, msg    

        if not points.shape[1] == 2:
            msg = ('Input must be an N x 2 array or list of (x,y) values. '
                   'I got an %d x %d array' % points.shape)
            raise ShapeError, msg    

        # Subtract geo ref from points
        if not self.is_absolute():
            points = copy.copy(points) # Don't destroy input                            
            points[:,0] -= self.xllcorner 
            points[:,1] -= self.yllcorner

        if is_list:
            points = points.tolist()
             
        return points

    ##
    # @brief ??
    # @param other ??
    def reconcile_zones(self, other):
        if other is None:
            other = Geo_reference()
        if (self.zone == other.zone or
            self.zone == DEFAULT_ZONE and
            other.zone == DEFAULT_ZONE):
            pass
        elif self.zone == DEFAULT_ZONE:
            self.zone = other.zone
        elif other.zone == DEFAULT_ZONE:
            other.zone = self.zone
        else:
            msg = ('Geospatial data must be in the same '
                   'ZONE to allow reconciliation. I got zone %d and %d'
                   % (self.zone, other.zone))
            raise ANUGAError, msg

    #def easting_northing2geo_reffed_point(self, x, y):
    #    return [x-self.xllcorner, y - self.xllcorner]

    #def easting_northing2geo_reffed_points(self, x, y):
    #    return [x-self.xllcorner, y - self.xllcorner]

    ##
    # @brief Get origin of this geo_reference.
    # @return (zone, xllcorner, yllcorner).
    def get_origin(self):
        return (self.zone, self.xllcorner, self.yllcorner)

    ##
    # @brief Get a string representation of this geo_reference instance.
    def __repr__(self):
        return ('(zone=%i easting=%f, northing=%f)'
                % (self.zone, self.xllcorner, self.yllcorner))

    ##
    # @brief Compare two geo_reference instances.
    # @param self This geo_reference instance.
    # @param other Another geo_reference instance to compare against.
    # @return 0 if instances have the same attributes, else 1.
    # @note Attributes are: zone, xllcorner, yllcorner.
    def __cmp__(self, other):
        # FIXME (DSG) add a tolerence
        if other is None:
            return 1
        cmp = 0
        if not (self.xllcorner == self.xllcorner):
            cmp = 1
        if not (self.yllcorner == self.yllcorner):
            cmp = 1
        if not (self.zone == self.zone):
            cmp = 1
        return cmp


##
# @brief Write a geo_reference to a NetCDF file (usually SWW).
# @param origin A georef instance or parameters to create a georef instance.
# @param outfile Path to file to write.
# @return A normalized geo_reference.
def write_NetCDF_georeference(origin, outfile):
    """Write georeference info to a netcdf file, usually sww.

    The origin can be a georef instance or parameters for a geo_ref instance

    outfile is the name of the file to be written to.
    """

    geo_ref = ensure_geo_reference(origin)
    geo_ref.write_NetCDF(outfile)
    return geo_ref


##
# @brief Convert an object to a georeference instance.
# @param origin A georef instance or (zone, xllcorner, yllcorner)
# @return A georef object, or None if 'origin' was None.
def ensure_geo_reference(origin):
    """
    Given a list/tuple of zone, xllcorner and yllcorner of a geo-ref object,
    return a geo ref object.

    If the origin is None, return None, so calling this function doesn't
    effect code logic
    """

    if isinstance(origin, Geo_reference):
        geo_ref = origin
    elif origin is None:
        geo_ref = None
    else:
        geo_ref = apply(Geo_reference, origin)

    return geo_ref


#-----------------------------------------------------------------------

if __name__ == "__main__":
    pass

########NEW FILE########
__FILENAME__ = lat_long_UTM_conversion
#!/usr/bin/env python

# Lat Long - UTM, UTM - Lat Long conversions
#
# see http://www.pygps.org
#

from math import pi, sin, cos, tan, sqrt

#LatLong- UTM conversion..h
#definitions for lat/long to UTM and UTM to lat/lng conversions
#include <string.h>

_deg2rad = pi / 180.0
_rad2deg = 180.0 / pi

_EquatorialRadius = 2
_eccentricitySquared = 3

_ellipsoid = [
#  id, Ellipsoid name, Equatorial Radius, square of eccentricity
# first once is a placeholder only, To allow array indices to match id numbers
	[ -1, "Placeholder", 0, 0],
	[ 1, "Airy", 6377563, 0.00667054],
	[ 2, "Australian National", 6378160, 0.006694542],
	[ 3, "Bessel 1841", 6377397, 0.006674372],
	[ 4, "Bessel 1841 (Nambia] ", 6377484, 0.006674372],
	[ 5, "Clarke 1866", 6378206, 0.006768658],
	[ 6, "Clarke 1880", 6378249, 0.006803511],
	[ 7, "Everest", 6377276, 0.006637847],
	[ 8, "Fischer 1960 (Mercury] ", 6378166, 0.006693422],
	[ 9, "Fischer 1968", 6378150, 0.006693422],
	[ 10, "GRS 1967", 6378160, 0.006694605],
	[ 11, "GRS 1980", 6378137, 0.00669438],
	[ 12, "Helmert 1906", 6378200, 0.006693422],
	[ 13, "Hough", 6378270, 0.00672267],
	[ 14, "International", 6378388, 0.00672267],
	[ 15, "Krassovsky", 6378245, 0.006693422],
	[ 16, "Modified Airy", 6377340, 0.00667054],
	[ 17, "Modified Everest", 6377304, 0.006637847],
	[ 18, "Modified Fischer 1960", 6378155, 0.006693422],
	[ 19, "South American 1969", 6378160, 0.006694542],
	[ 20, "WGS 60", 6378165, 0.006693422],
	[ 21, "WGS 66", 6378145, 0.006694542],
	[ 22, "WGS-72", 6378135, 0.006694318],
	[ 23, "WGS-84", 6378137, 0.00669438]
]

#Reference ellipsoids derived from Peter H. Dana's website-
#http://www.utexas.edu/depts/grg/gcraft/notes/datum/elist.html
#Department of Geography, University of Texas at Austin
#Internet: pdana@mail.utexas.edu
#3/22/95

#Source
#Defense Mapping Agency. 1987b. DMA Technical Report: Supplement to Department of Defense World Geodetic System
#1984 Technical Report. Part I and II. Washington, DC: Defense Mapping Agency

#def LLtoUTM(int ReferenceEllipsoid, const double Lat, const double Long,
#			 double &UTMNorthing, double &UTMEasting, char* UTMZone)

def LLtoUTM( Lat, Long, ReferenceEllipsoid=23):
    """
    converts lat/long to UTM coords.  Equations from USGS Bulletin 1532
    East Longitudes are positive, West longitudes are negative.
    North latitudes are positive, South latitudes are negative
    Lat and Long are in decimal degrees
    Written by Chuck Gantz- chuck.gantz@globalstar.com
    """
    a = _ellipsoid[ReferenceEllipsoid][_EquatorialRadius]
    eccSquared = _ellipsoid[ReferenceEllipsoid][_eccentricitySquared]
    k0 = 0.9996

#Make sure the longitude is between -180.00 .. 179.9
    LongTemp = (Long+180)-int((Long+180)/360)*360-180 # -180.00 .. 179.9

    LatRad = Lat*_deg2rad
    LongRad = LongTemp*_deg2rad

    ZoneNumber = int((LongTemp + 180)/6) + 1

    if Lat >= 56.0 and Lat < 64.0 and LongTemp >= 3.0 and LongTemp < 12.0:
        ZoneNumber = 32

    # Special zones for Svalbard
    if Lat >= 72.0 and Lat < 84.0:
        if  LongTemp >= 0.0  and LongTemp <  9.0:ZoneNumber = 31
        elif LongTemp >= 9.0  and LongTemp < 21.0: ZoneNumber = 33
        elif LongTemp >= 21.0 and LongTemp < 33.0: ZoneNumber = 35
        elif LongTemp >= 33.0 and LongTemp < 42.0: ZoneNumber = 37

    LongOrigin = (ZoneNumber - 1)*6 - 180 + 3 #+3 puts origin in middle of zone
    LongOriginRad = LongOrigin * _deg2rad

    #compute the UTM Zone from the latitude and longitude
    UTMZone = "%d%c" % (ZoneNumber, _UTMLetterDesignator(Lat))

    eccPrimeSquared = (eccSquared)/(1-eccSquared)
    N = a/sqrt(1-eccSquared*sin(LatRad)*sin(LatRad))
    T = tan(LatRad)*tan(LatRad)
    C = eccPrimeSquared*cos(LatRad)*cos(LatRad)
    A = cos(LatRad)*(LongRad-LongOriginRad)

    M = a*((1
            - eccSquared/4
            - 3*eccSquared*eccSquared/64
            - 5*eccSquared*eccSquared*eccSquared/256)*LatRad
           - (3*eccSquared/8
              + 3*eccSquared*eccSquared/32
              + 45*eccSquared*eccSquared*eccSquared/1024)*sin(2*LatRad)
           + (15*eccSquared*eccSquared/256 + 45*eccSquared*eccSquared*eccSquared/1024)*sin(4*LatRad)
           - (35*eccSquared*eccSquared*eccSquared/3072)*sin(6*LatRad))

    UTMEasting = (k0*N*(A+(1-T+C)*A*A*A/6
                        + (5-18*T+T*T+72*C-58*eccPrimeSquared)*A*A*A*A*A/120)
                  + 500000.0)

    UTMNorthing = (k0*(M+N*tan(LatRad)*(A*A/2+(5-T+9*C+4*C*C)*A*A*A*A/24
                                        + (61
                                           -58*T
                                           +T*T
                                           +600*C
                                           -330*eccPrimeSquared)*A*A*A*A*A*A/720)))

    if Lat < 0:
        UTMNorthing = UTMNorthing + 10000000.0; #10000000 meter offset for southern hemisphere
    #UTMZone was originally returned here.  I don't know what the
    #letter at the end was for.
    #print "UTMZone", UTMZone 
    return (ZoneNumber, UTMEasting, UTMNorthing)


def _UTMLetterDesignator(Lat):
#This routine determines the correct UTM letter designator for the given latitude
#returns 'Z' if latitude is outside the UTM limits of 84N to 80S
#Written by Chuck Gantz- chuck.gantz@globalstar.com

    if 84 >= Lat >= 72: return 'X'
    elif 72 > Lat >= 64: return 'W'
    elif 64 > Lat >= 56: return 'V'
    elif 56 > Lat >= 48: return 'U'
    elif 48 > Lat >= 40: return 'T'
    elif 40 > Lat >= 32: return 'S'
    elif 32 > Lat >= 24: return 'R'
    elif 24 > Lat >= 16: return 'Q'
    elif 16 > Lat >= 8: return 'P'
    elif  8 > Lat >= 0: return 'N'
    elif  0 > Lat >= -8: return 'M'
    elif -8> Lat >= -16: return 'L'
    elif -16 > Lat >= -24: return 'K'
    elif -24 > Lat >= -32: return 'J'
    elif -32 > Lat >= -40: return 'H'
    elif -40 > Lat >= -48: return 'G'
    elif -48 > Lat >= -56: return 'F'
    elif -56 > Lat >= -64: return 'E'
    elif -64 > Lat >= -72: return 'D'
    elif -72 > Lat >= -80: return 'C'
    else: return 'Z'	# if the Latitude is outside the UTM limits

#void UTMtoLL(int ReferenceEllipsoid, const double UTMNorthing, const double UTMEasting, const char* UTMZone,
#			  double& Lat,  double& Long )

def UTMtoLL(northing, easting, zone, isSouthernHemisphere=True,
            ReferenceEllipsoid=23):
    """
    converts UTM coords to lat/long.  Equations from USGS Bulletin 1532
    East Longitudes are positive, West longitudes are negative.
    North latitudes are positive, South latitudes are negative
    Lat and Long are in decimal degrees.
    Written by Chuck Gantz- chuck.gantz@globalstar.com
    Converted to Python by Russ Nelson <nelson@crynwr.com>

    FIXME: This is set up to work for the Southern Hemisphere.

Using
http://www.ga.gov.au/geodesy/datums/redfearn_geo_to_grid.jsp

    Site Name:    GDA-MGA: (UTM with GRS80 ellipsoid) 
Zone:   36    
Easting:  511669.521  Northing: 19328195.112 
Latitude:   84  0 ' 0.00000 ''  Longitude: 34  0 ' 0.00000 '' 
Grid Convergence:  0  -59 ' 40.28 ''  Point Scale: 0.99960166

____________
Site Name:    GDA-MGA: (UTM with GRS80 ellipsoid) 
Zone:   36    
Easting:  519384.803  Northing: 1118247.585 
Latitude:   -80  0 ' 0.00000 ''  Longitude: 34  0 ' 0.00000 '' 
Grid Convergence:  0  59 ' 5.32 ''  Point Scale: 0.99960459 
___________
Site Name:    GDA-MGA: (UTM with GRS80 ellipsoid) 
Zone:   36    
Easting:  611263.812  Northing: 10110547.106 
Latitude:   1  0 ' 0.00000 ''  Longitude: 34  0 ' 0.00000 '' 
Grid Convergence:  0  -1 ' 2.84 ''  Point Scale: 0.99975325 
______________
Site Name:    GDA-MGA: (UTM with GRS80 ellipsoid) 
Zone:   36    
Easting:  611263.812  Northing: 9889452.894 
Latitude:   -1  0 ' 0.00000 ''  Longitude: 34  0 ' 0.00000 '' 
Grid Convergence:  0  1 ' 2.84 ''  Point Scale: 0.99975325 

So this uses a false northing of 10000000 in the both hemispheres.
ArcGIS used a false northing of 0 in the northern hem though.
Therefore it is difficult to actually know what hemisphere you are in.
    """
    k0 = 0.9996
    a = _ellipsoid[ReferenceEllipsoid][_EquatorialRadius]
    eccSquared = _ellipsoid[ReferenceEllipsoid][_eccentricitySquared]
    e1 = (1-sqrt(1-eccSquared))/(1+sqrt(1-eccSquared))

    x = easting - 500000.0 #remove 500,000 meter offset for longitude
    y = northing

    ZoneNumber = int(zone)
    if isSouthernHemisphere:
        y -= 10000000.0         # remove 10,000,000 meter offset used
                                # for southern hemisphere

    LongOrigin = (ZoneNumber - 1)*6 - 180 + 3  # +3 puts origin in middle of zone

    eccPrimeSquared = (eccSquared)/(1-eccSquared)

    M = y / k0
    mu = M/(a*(1-eccSquared/4-3*eccSquared*eccSquared/64-5*eccSquared*eccSquared*eccSquared/256))

    phi1Rad = (mu + (3*e1/2-27*e1*e1*e1/32)*sin(2*mu)
               + (21*e1*e1/16-55*e1*e1*e1*e1/32)*sin(4*mu)
               +(151*e1*e1*e1/96)*sin(6*mu))
    phi1 = phi1Rad*_rad2deg;

    N1 = a/sqrt(1-eccSquared*sin(phi1Rad)*sin(phi1Rad))
    T1 = tan(phi1Rad)*tan(phi1Rad)
    C1 = eccPrimeSquared*cos(phi1Rad)*cos(phi1Rad)
    R1 = a*(1-eccSquared)/pow(1-eccSquared*sin(phi1Rad)*sin(phi1Rad), 1.5)
    D = x/(N1*k0)

    Lat = phi1Rad - (N1*tan(phi1Rad)/R1)*(D*D/2-(5+3*T1+10*C1-4*C1*C1-9*eccPrimeSquared)*D*D*D*D/24
                                          +(61+90*T1+298*C1+45*T1*T1-252*eccPrimeSquared-3*C1*C1)*D*D*D*D*D*D/720)
    Lat = Lat * _rad2deg

    Long = (D-(1+2*T1+C1)*D*D*D/6+(5-2*C1+28*T1-3*C1*C1+8*eccPrimeSquared+24*T1*T1)
            *D*D*D*D*D/120)/cos(phi1Rad)
    Long = LongOrigin + Long * _rad2deg
    return (Lat, Long)

if __name__ == '__main__':
    (z, e, n) = LLtoUTM(45.00, -75.00, 23)
    print z, e, n
    (lat, lon) = UTMtoLL(n, e, z, 23)
    print lat, lon

########NEW FILE########
__FILENAME__ = redfearn
"""
This module adapted ANUGA
https://anuga.anu.edu.au/

------------

Implementation of Redfearn's formula to compute UTM projections from latitude and longitude

Based in part on spreadsheet
www.icsm.gov.au/gda/gdatm/redfearn.xls
downloaded from INTERGOVERNMENTAL COMMITTEE ON SURVEYING & MAPPING (ICSM)
http://www.icsm.gov.au/icsm/

"""
from geo_reference import Geo_reference, DEFAULT_ZONE


def degminsec2decimal_degrees(dd,mm,ss):
    assert abs(mm) == mm
    assert abs(ss) == ss    

    if dd < 0:
        sign = -1
    else:
        sign = 1
    
    return sign * (abs(dd) + mm/60. + ss/3600.)      
    
def decimal_degrees2degminsec(dec):

    if dec < 0:
        sign = -1
    else:
        sign = 1

    dec = abs(dec)    
    dd = int(dec)
    f = dec-dd

    mm = int(f*60)
    ss = (f*60-mm)*60
    
    return sign*dd, mm, ss

def redfearn(lat, lon, false_easting=None, false_northing=None,
             zone=None, central_meridian=None, scale_factor=None):
    """Compute UTM projection using Redfearn's formula

    lat, lon is latitude and longitude in decimal degrees

    If false easting and northing are specified they will override
    the standard

    If zone is specified reproject lat and long to specified zone instead of
    standard zone

    If meridian is specified, reproject lat and lon to that instead of zone. In this case
    zone will be set to -1 to indicate non-UTM projection

    Note that zone and meridian cannot both be specifed
    """


    from math import pi, sqrt, sin, cos, tan
    


    #GDA Specifications
    a = 6378137.0                       #Semi major axis
    inverse_flattening = 298.257222101  #1/f
    if scale_factor is None:
        K0 = 0.9996                         #Central scale factor    
    else:
        K0 = scale_factor
    #print 'scale', K0
    zone_width = 6                      #Degrees

    longitude_of_central_meridian_zone0 = -183    
    longitude_of_western_edge_zone0 = -186

    if false_easting is None:
        false_easting = 500000

    if false_northing is None:
        if lat < 0:
            false_northing = 10000000  #Southern hemisphere
        else:
            false_northing = 0         #Northern hemisphere)
        
    
    #Derived constants
    f = 1.0/inverse_flattening
    b = a*(1-f)       #Semi minor axis

    e2 = 2*f - f*f#    = f*(2-f) = (a^2-b^2/a^2   #Eccentricity
    e = sqrt(e2)
    e2_ = e2/(1-e2)   # = (a^2-b^2)/b^2 #Second eccentricity
    e_ = sqrt(e2_)
    e4 = e2*e2
    e6 = e2*e4

    #Foot point latitude
    n = (a-b)/(a+b) #Same as e2 - why ?
    n2 = n*n
    n3 = n*n2
    n4 = n2*n2

    G = a*(1-n)*(1-n2)*(1+9*n2/4+225*n4/64)*pi/180


    phi = lat*pi/180     #Convert latitude to radians

    sinphi = sin(phi)   
    sin2phi = sin(2*phi)
    sin4phi = sin(4*phi)
    sin6phi = sin(6*phi)

    cosphi = cos(phi)
    cosphi2 = cosphi*cosphi
    cosphi3 = cosphi*cosphi2
    cosphi4 = cosphi2*cosphi2
    cosphi5 = cosphi*cosphi4    
    cosphi6 = cosphi2*cosphi4
    cosphi7 = cosphi*cosphi6
    cosphi8 = cosphi4*cosphi4        

    t = tan(phi)
    t2 = t*t
    t4 = t2*t2
    t6 = t2*t4
    
    #Radius of Curvature
    rho = a*(1-e2)/(1-e2*sinphi*sinphi)**1.5
    nu = a/(1-e2*sinphi*sinphi)**0.5
    psi = nu/rho
    psi2 = psi*psi
    psi3 = psi*psi2
    psi4 = psi2*psi2



    #Meridian distance

    A0 = 1 - e2/4 - 3*e4/64 - 5*e6/256
    A2 = 3.0/8*(e2+e4/4+15*e6/128)
    A4 = 15.0/256*(e4+3*e6/4)
    A6 = 35*e6/3072
    
    term1 = a*A0*phi
    term2 = -a*A2*sin2phi
    term3 = a*A4*sin4phi
    term4 = -a*A6*sin6phi

    m = term1 + term2 + term3 + term4 #OK

    if zone is not None and central_meridian is not None:
        msg = 'You specified both zone and central_meridian. Provide only one of them'
        raise Exception, msg
    
    # Zone
    if zone is None:
        zone = int((lon - longitude_of_western_edge_zone0)/zone_width)

    # Central meridian
    if central_meridian is None:
        central_meridian = zone*zone_width+longitude_of_central_meridian_zone0
    else:
        zone = -1

    omega = (lon-central_meridian)*pi/180 #Relative longitude (radians)
    omega2 = omega*omega
    omega3 = omega*omega2
    omega4 = omega2*omega2
    omega5 = omega*omega4
    omega6 = omega3*omega3
    omega7 = omega*omega6
    omega8 = omega4*omega4
     
    #Northing
    term1 = nu*sinphi*cosphi*omega2/2  
    term2 = nu*sinphi*cosphi3*(4*psi2+psi-t2)*omega4/24
    term3 = nu*sinphi*cosphi5*\
            (8*psi4*(11-24*t2)-28*psi3*(1-6*t2)+\
             psi2*(1-32*t2)-psi*2*t2+t4-t2)*omega6/720
    term4 = nu*sinphi*cosphi7*(1385-3111*t2+543*t4-t6)*omega8/40320
    northing = false_northing + K0*(m + term1 + term2 + term3 + term4)

    #Easting
    term1 = nu*omega*cosphi
    term2 = nu*cosphi3*(psi-t2)*omega3/6
    term3 = nu*cosphi5*(4*psi3*(1-6*t2)+psi2*(1+8*t2)-2*psi*t2+t4)*omega5/120
    term4 = nu*cosphi7*(61-479*t2+179*t4-t6)*omega7/5040
    easting = false_easting + K0*(term1 + term2 + term3 + term4)
    
    return zone, easting, northing



def convert_from_latlon_to_utm(points=None,
                               latitudes=None,
                               longitudes=None,
                               false_easting=None,
                               false_northing=None):
    """Convert latitude and longitude data to UTM as a list of coordinates.


    Input

    points: list of points given in decimal degrees (latitude, longitude) or
    latitudes: list of latitudes   and
    longitudes: list of longitudes 
    false_easting (optional)
    false_northing (optional)

    Output

    points: List of converted points
    zone:   Common UTM zone for converted points


    Notes

    Assume the false_easting and false_northing are the same for each list.
    If points end up in different UTM zones, an ANUGAerror is thrown.    
    """

    old_geo = Geo_reference()    
    utm_points = []
    if points == None:
        assert len(latitudes) == len(longitudes)
        points =  map(None, latitudes, longitudes)
        
    for point in points:
        
        zone, easting, northing = redfearn(float(point[0]),
                                           float(point[1]),
                                           false_easting=false_easting,
                                           false_northing=false_northing)
        new_geo = Geo_reference(zone)
        old_geo.reconcile_zones(new_geo)        
        utm_points.append([easting, northing])

    return utm_points, old_geo.get_zone()

########NEW FILE########
__FILENAME__ = dumpstacks



import threading, sys, traceback

# Import dumpstacks to install a SIGQUIT handler that shows a stack dump for all stacks
# From http://stackoverflow.com/questions/132058/showing-the-stack-trace-from-a-running-python-application

def dumpstacks(signal, frame):
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# Thread: %s(%d)" % (id2name.get(threadId, ""), threadId))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    print("\n".join(code))

try:
    import signal
    signal.signal(signal.SIGQUIT, dumpstacks)
except Exception as e:
    # Silently ignore failures installing this handler (probably won't work on Windows)
    pass

########NEW FILE########
__FILENAME__ = libchecklist
#!/usr/bin/env python

"""
  MAVProxy checklist, implemented in a child process
  Created by Stephen Dade (stephen_dade@hotmail.com)
"""

class CheckItem():
    '''Checklist item used for information transfer
    between threads/processes/pipes'''
    def __init__(self, name, state):
        self.name = name
        self.state = state


class UI():
    '''
    a UI for the MAVProxy checklist
    '''

    def __init__(self):
        import multiprocessing
        self.parent_pipe,self.child_pipe = multiprocessing.Pipe()
        self.close_event = multiprocessing.Event()
        self.close_event.clear()
        self.child = multiprocessing.Process(target=self.child_task)
        self.child.start()


    def child_task(self):
        '''child process - this holds all the GUI elements'''
        import Tkinter as tk

        '''curStep is which step in the list we are up to, increments +1 for each list completed
        it is the same as the column number of the checklist item'''
        self.curStep = 0

        self.root = tk.Tk()
        self.root.title("MAVProxy: Checklist")
        self.root.grid()
        self.createLists()
        self.createWidgets(self.root)
        self.on_timer()

        self.root.mainloop()


    def createLists(self):
        '''Generate the checklists. Note that:
        0,1 = off/on for auto-ticked items
        2,3 = off/on for manually ticked items'''

        self.beforeAssemblyList = {
        'Confirm batteries charged':2,
        'No physical damage to airframe':2,
        'All electronics present and connected':2,
        'Joe placed':2,
        'CoG of UAV correct':2,
        'Ground station operational':2
        }

        self.beforeEngineList = {
        'APM Booted':0,
        'Pandaboard Booted':2,
        'Cameras calibrated and capturing':2,
        'GPS lock':0,
        'Altitude lock':0,
        'Flight mode MANUAL':0,
        'Trim set from controller':0,
        'Avionics Battery':0,
        'Compass Calibrated':0,
        'Accelerometers and Gyros Calibrated':0,
        'UAV Level':0,
        'Aircraft Params Loaded':2,
        'Radio Links > 6db margin':0,
        'Waypoints Loaded':0
        }

        self.beforeTakeoffList = {
        'Flight control surfaces responsive':2,
        'Engine throttle responsive':2,
        'Runway clear':2,
        'Compass active':0,
        'IMU OK':2,
        'Set flight timer and alarm':2
        }

        self.beforeCruiseList = {
        'Airspeed > 10 m/s':0,
        'Altitude > 30 m':0,
        '< 100 degrees to 1st Waypoint':2
        }

        self.bottleDropList = {
        'Joe found':2,
        'Joe waypoint laid in':2,
        '< 100m to Joe waypoint':2,
        'Bottle drop mechanism activated':2
        }

        self.beforeLandingList = {
        'APM set to MANUAL mode':2,
        '< 100m from airfield home':2
        }

        self.beforeShutdownList = {
        'Engine cutoff':2,
        'Data downloaded':2
        }

    def createWidgets(self, frame):
        '''Create the controls on the UI'''
        import Tkinter as tk

        '''Group Labels'''
        AssemblyLabel = tk.Label(frame, text="During Assembly")
        EngineLabel = tk.Label(frame, text="Before Engine Start")
        BootLabel = tk.Label(frame, text="Before Takeoff")
        FlightLabel = tk.Label(frame, text="Before Cruise/AUTO")
        '''BottleLabel = tk.Label(frame, text="Bottle Drop")'''
        '''LandLabel = tk.Label(frame, text="Before Landing")'''
        '''ShutdownLabel = tk.Label(frame, text="Before Shutdown")'''
        AssemblyLabel.grid(row=0, column=0)
        EngineLabel.grid(row=0, column=1)
        BootLabel.grid(row=0, column=2)
        FlightLabel.grid(row=0, column=3)
        '''BottleLabel.grid(row=0, column=4)'''
        '''LandLabel.grid(row=0, column=5)'''
        '''ShutdownLabel.grid(row=0, column=6)'''

        '''before assembly checklist'''
        i = 1
        for key in self.beforeAssemblyList:
            if self.beforeAssemblyList[key] == 0:
                self.beforeAssemblyList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.beforeAssemblyList[key], state="disabled", wraplength=170, justify='left', onvalue=1, offvalue=0)
                aCheckButton.grid(row = i, column=0, sticky='w')
            if self.beforeAssemblyList[key] == 2:
                self.beforeAssemblyList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.beforeAssemblyList[key], wraplength=170, justify='left', onvalue=3, offvalue=2)
                aCheckButton.grid(row = i, column=0, sticky='w')
            i = i+1

        self.beforeAssemblyButton = tk.Button(text='Close final hatches', state="active", command=self.beforeAssemblyListCheck)
        self.beforeAssemblyButton.grid(row = i, column=0, sticky='w')

        '''before Engine Start checklist'''
        i = 1
        for key in self.beforeEngineList:
            if self.beforeEngineList[key] == 0:
                self.beforeEngineList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.beforeEngineList[key], state="disabled", wraplength=170, justify='left', onvalue=1, offvalue=0)
                aCheckButton.grid(row = i, column=1, sticky='w')
            if self.beforeEngineList[key] == 2:
                self.beforeEngineList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.beforeEngineList[key], wraplength=170, justify='left', onvalue=3, offvalue=2)
                aCheckButton.grid(row = i, column=1, sticky='w')
            i = i+1

        self.beforeEngineButton = tk.Button(text='Ready for Engine start', state="disabled", command=self.beforeEngineCheck)
        self.beforeEngineButton.grid(row = i, column=1, sticky='w')

        '''before takeoff checklist'''
        i = 1
        for key in self.beforeTakeoffList:
            if self.beforeTakeoffList[key] == 0:
                self.beforeTakeoffList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.beforeTakeoffList[key], state="disabled", wraplength=170, justify='left', onvalue=1, offvalue=0)
                aCheckButton.grid(row = i, column=2, sticky='w')
            if self.beforeTakeoffList[key] == 2:
                self.beforeTakeoffList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.beforeTakeoffList[key], wraplength=170, justify='left', onvalue=3, offvalue=2)
                aCheckButton.grid(row = i, column=2, sticky='w')
            i = i+1

        self.beforeTakeoffButton = tk.Button(text='Ready for Takeoff', state="disabled", command=self.beforeTakeoffCheck)
        self.beforeTakeoffButton.grid(row = i, column=2, sticky='w')

        '''After takeoff'''
        i=1
        for key in self.beforeCruiseList:
            if self.beforeCruiseList[key] == 0:
                self.beforeCruiseList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.beforeCruiseList[key], state="disabled", wraplength=170, justify='left', onvalue=1, offvalue=0)
                aCheckButton.grid(row = i, column=3, sticky='w')
            if self.beforeCruiseList[key] == 2:
                self.beforeCruiseList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.beforeCruiseList[key], wraplength=170, justify='left', onvalue=3, offvalue=2)
                aCheckButton.grid(row = i, column=3, sticky='w')
            i = i+1

        self.beforeCruiseButton = tk.Button(text='Ready for Cruise', state="disabled", command=self.beforeCruiseCheck)
        self.beforeCruiseButton.grid(row = i, column=3, sticky='w')

        '''Before bottle drop'''
        '''i=1
        for key in self.bottleDropList:
            if self.bottleDropList[key] == 0:
                self.bottleDropList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.bottleDropList[key], state="disabled", wraplength=170, justify='left', onvalue=1, offvalue=0)
                aCheckButton.grid(row = i, column=4, sticky='w')
            if self.bottleDropList[key] == 2:
                self.bottleDropList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.bottleDropList[key], wraplength=170, justify='left', onvalue=3, offvalue=2)
                aCheckButton.grid(row = i, column=4, sticky='w')
            i = i+1

        self.bottleDropButton = tk.Button(text='Bottle drop completed', state="disabled", command=self.bottleDropCheck)
        self.bottleDropButton.grid(row = i, column=4, sticky='w')'''

        '''Before landing'''
        '''i=1
        for key in self.beforeLandingList:
            if self.beforeLandingList[key] == 0:
                self.beforeLandingList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.beforeLandingList[key], state="disabled", wraplength=170, justify='left', onvalue=1, offvalue=0)
                aCheckButton.grid(row = i, column=5, sticky='w')
            if self.beforeLandingList[key] == 2:
                self.beforeLandingList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.beforeLandingList[key], wraplength=170, justify='left', onvalue=3, offvalue=2)
                aCheckButton.grid(row = i, column=5, sticky='w')
            i = i+1

        self.beforeLandingButton = tk.Button(text='Ready for landing', state="disabled", command=self.beforeLandingCheck)
        self.beforeLandingButton.grid(row = i, column=5, sticky='w')'''

        '''before shutdown checklist'''
        '''i = 1
        for key in self.beforeShutdownList:
            if self.beforeShutdownList[key] == 0:
                self.beforeShutdownList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.beforeShutdownList[key], state="disabled", wraplength=170, justify='left', onvalue=1, offvalue=0)
                aCheckButton.grid(row = i, column=6, sticky='w')
            if self.beforeShutdownList[key] == 2:
                self.beforeShutdownList[key] = tk.IntVar()
                aCheckButton = tk.Checkbutton(text=key, variable=self.beforeShutdownList[key], wraplength=170, justify='left', onvalue=3, offvalue=2)
                aCheckButton.grid(row = i, column=6, sticky='w')
            i = i+1

        self.beforeShutdownButton = tk.Button(text='Shutdown', state="disabled", command=self.beforeShutdownCheck)
        self.beforeShutdownButton.grid(row = i, column=6, sticky='w')'''


    def beforeAssemblyListCheck(self):
        '''Event for the "Checklist Complete" button for the Before Assembly section'''
        import Tkinter as tk
        import tkMessageBox

        '''Check all of the checklist for ticks'''
        for key, value in self.beforeAssemblyList.items():
            state = value.get()
            if state == 0 or state == 2:
                tkMessageBox.showinfo("Error", "Item not ticked: " + key)
                return

        '''disable all checkboxes in this column'''
        for child in self.root.winfo_children():
            if isinstance(child, tk.Checkbutton) and int(child.grid_info()['column']) == self.curStep:
                child.config(state="disabled")

        '''if we made it here, the checklist is OK'''
        self.beforeEngineButton.config(state="normal")
        self.beforeAssemblyButton.config(text='Checklist Completed', state="disabled")
        self.curStep = 1

    def beforeEngineCheck(self):
        '''Event for the "Checklist Complete" button for the Before Engine Start section'''
        import Tkinter as tk
        import tkMessageBox

        '''Check all of the checklist for ticks'''
        for key, value in self.beforeEngineList.items():
            state = value.get()
            if state == 0 or state == 2:
                tkMessageBox.showinfo("Error", "Item not ticked: " + key)
                return

        '''disable all checkboxes in this column'''
        for child in self.root.winfo_children():
            if isinstance(child, tk.Checkbutton) and int(child.grid_info()['column']) == self.curStep:
                child.config(state="disabled")

        '''if we made it here, the checklist is OK'''
        self.beforeTakeoffButton.config(state="normal")
        self.beforeEngineButton.config(text='Checklist Completed', state="disabled")
        self.curStep = 2

    def beforeTakeoffCheck(self):
        '''Event for the "Checklist Complete" button for the Before Takeoff section'''
        import Tkinter as tk
        import tkMessageBox

        '''Check all of the checklist for ticks'''
        for key, value in self.beforeTakeoffList.items():
            state = value.get()
            if state == 0 or state == 2:
                tkMessageBox.showinfo("Error", "Item not ticked: " + key)
                return

        '''disable all checkboxes in this column'''
        for child in self.root.winfo_children():
            if isinstance(child, tk.Checkbutton) and int(child.grid_info()['column']) == self.curStep:
                child.config(state="disabled")

        '''if we made it here, the checklist is OK'''
        self.beforeCruiseButton.config(state="normal")
        self.beforeTakeoffButton.config(text='Checklist Completed', state="disabled")
        self.curStep = 3


    def beforeCruiseCheck(self):
        '''Event for the "Checklist Complete" button for the Before Cruise/AUTO section'''
        import Tkinter as tk
        import tkMessageBox

        '''Check all of the checklist for ticks'''
        for key, value in self.beforeCruiseList.items():
            state = value.get()
            if state == 0 or state == 2:
                tkMessageBox.showinfo("Error", "Item not ticked: " + key)
                return

        '''disable all checkboxes in this column'''
        for child in self.root.winfo_children():
            if isinstance(child, tk.Checkbutton) and int(child.grid_info()['column']) == self.curStep:
                child.config(state="disabled")

        '''if we made it here, the checklist is OK'''
        '''self.bottleDropButton.config(state="normal")'''
        tkMessageBox.showinfo("Information", "Checklist Completed!")
        self.beforeCruiseButton.config(text='Checklist Completed', state="disabled")
        self.curStep = 4

    def bottleDropCheck(self):
        '''Event for the "Checklist Complete" button for the Before Bottle Drop section'''
        import Tkinter as tk
        import tkMessageBox

        '''Check all of the checklist for ticks'''
        for key, value in self.bottleDropList.items():
            state = value.get()
            if state == 0 or state == 2:
                tkMessageBox.showinfo("Error", "Item not ticked: " + key)
                return

        '''disable all checkboxes in this column'''
        for child in self.root.winfo_children():
            if isinstance(child, tk.Checkbutton) and int(child.grid_info()['column']) == self.curStep:
                child.config(state="disabled")

        '''if we made it here, the checklist is OK'''
        self.beforeLandingButton.config(state="normal")
        self.bottleDropButton.config(text='Checklist Completed', state="disabled")
        self.curStep = 5

    def beforeLandingCheck(self):
        '''Event for the "Checklist Complete" button for the Before Landing section'''
        import Tkinter as tk
        import tkMessageBox

        '''Check all of the checklist for ticks'''
        for key, value in self.beforeLandingList.items():
            state = value.get()
            if state == 0 or state == 2:
                tkMessageBox.showinfo("Error", "Item not ticked: " + key)
                return

        '''disable all checkboxes in this column'''
        for child in self.root.winfo_children():
            if isinstance(child, tk.Checkbutton) and int(child.grid_info()['column']) == self.curStep:
                child.config(state="disabled")

        '''if we made it here, the checklist is OK'''
        self.beforeShutdownButton.config(state="normal")
        self.beforeLandingButton.config(text='Checklist Completed', state="disabled")
        self.curStep = 6

    def beforeShutdownCheck(self):
        '''Event for the "Checklist Complete" button for the Before Landing section'''
        import Tkinter as tk
        import tkMessageBox

        '''Check all of the checklist for ticks'''
        for key, value in self.beforeShutdownList.items():
            state = value.get()
            if state == 0 or state == 2:
                tkMessageBox.showinfo("Error", "Item not ticked: " + key)
                return

        '''disable all checkboxes in this column'''
        for child in self.root.winfo_children():
            if isinstance(child, tk.Checkbutton) and int(child.grid_info()['column']) == self.curStep:
                child.config(state="disabled")

        '''if we made it here, the checklist is OK'''
        self.beforeShutdownButton.config(text='Checklist Completed', state="disabled")
        tkMessageBox.showinfo("Information", "Checklist Completed!")
        self.curStep = 7

    def close(self):
        '''close the console'''
        self.close_event.set()
        if self.is_alive():
            self.child.join(2)

    def is_alive(self):
        '''check if child is still going'''
        return self.child.is_alive()

    def on_timer(self):
        '''this timer periodically checks the inter-process pipe
        for any updated checklist items'''
        import Tkinter as tk
        if self.close_event.wait(0.001):
            self.timer.Stop()
            self.Destroy()
            return
        while self.child_pipe.poll():
            obj = self.child_pipe.recv()
            if isinstance(obj, CheckItem):
                # request to set a checklist item
                '''Go through all the controls in the main window'''
                for child in self.root.winfo_children():
                    '''If the control is a checkbutton and it's name matches and we're in the right checklist step, update it'''
                    if (isinstance(child, tk.Checkbutton) and
                        obj.name == child.cget('text') and
                        int(child.grid_info()['column']) == self.curStep):
                        if obj.state == 1:
                            child.select()
                        else:
                            child.deselect()


        '''print("in here")'''
        self.root.after(500, self.on_timer)

    def set_status(self, name, status):
        '''set a status value'''
        if self.child.is_alive():
            self.parent_pipe.send(CheckItem(name, status))


if __name__ == "__main__":
    # test the console
    import time

    checklist = UI()

    while checklist.is_alive():
        checklist.set_status("Compass Offsets", 1)
        time.sleep(0.5)

########NEW FILE########
__FILENAME__ = live_graph
#!/usr/bin/env python

"""

  MAVProxy realtime graphing module, partly based on the wx graphing
  demo by Eli Bendersky (eliben@gmail.com)

  http://eli.thegreenplace.net/files/prog_code/wx_mpl_dynamic_graph.py.txt
"""

class LiveGraph():
    '''
    a live graph object using wx and matplotlib
    All of the GUI work is done in a child process to provide some insulation
    from the parent mavproxy instance and prevent instability in the GCS

    New data is sent to the LiveGraph instance via a pipe
    '''
    def __init__(self,
                 fields,
                 title='MAVProxy: LiveGraph',
                 timespan=20.0,
                 tickresolution=0.2,
                 colors=[ 'red', 'green', 'blue', 'orange', 'olive', 'yellow', 'grey', 'black']):
        import multiprocessing
        self.fields = fields
        self.colors = colors
        self.title  = title
        self.timespan = timespan
        self.tickresolution = tickresolution
        self.values = [None]*len(self.fields)

        self.parent_pipe,self.child_pipe = multiprocessing.Pipe()
        self.close_graph = multiprocessing.Event()
        self.close_graph.clear()
        self.child = multiprocessing.Process(target=self.child_task)
        self.child.start()

    def child_task(self):
        '''child process - this holds all the GUI elements'''
        import wx, matplotlib
        matplotlib.use('WXAgg')
        app = wx.PySimpleApp()
        app.frame = GraphFrame(state=self)
        app.frame.Show()
        app.MainLoop()

    def add_values(self, values):
        '''add some data to the graph'''
        if self.child.is_alive():
            self.parent_pipe.send(values)

    def close(self):
        '''close the graph'''
        self.close_graph.set()
        if self.is_alive():
            self.child.join(2)

    def is_alive(self):
        '''check if graph is still going'''
        return self.child.is_alive()

import wx

class GraphFrame(wx.Frame):
    """ The main frame of the application
    """

    def __init__(self, state):
        wx.Frame.__init__(self, None, -1, state.title)
        self.state = state
        self.data = []
        for i in range(len(state.fields)):
            self.data.append([])
        self.paused = False

        self.create_main_panel()

        self.Bind(wx.EVT_IDLE, self.on_idle)

        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
        self.redraw_timer.Start(1000*self.state.tickresolution)

    def create_main_panel(self):
        from matplotlib.backends.backend_wxagg import \
             FigureCanvasWxAgg as FigCanvas
        self.panel = wx.Panel(self)

        self.init_plot()
        self.canvas = FigCanvas(self.panel, -1, self.fig)


        self.close_button = wx.Button(self.panel, -1, "Close")
        self.Bind(wx.EVT_BUTTON, self.on_close_button, self.close_button)

        self.pause_button = wx.Button(self.panel, -1, "Pause")
        self.Bind(wx.EVT_BUTTON, self.on_pause_button, self.pause_button)
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_pause_button, self.pause_button)

        self.hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox1.Add(self.close_button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        self.hbox1.AddSpacer(1)
        self.hbox1.Add(self.pause_button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)
        self.vbox.Add(self.hbox1, 0, flag=wx.ALIGN_LEFT | wx.TOP)

        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)

    def init_plot(self):
        self.dpi = 100
        import pylab, numpy
        from matplotlib.figure import Figure
        self.fig = Figure((6.0, 3.0), dpi=self.dpi)

        self.axes = self.fig.add_subplot(111)
        self.axes.set_axis_bgcolor('white')

        pylab.setp(self.axes.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference
        # to the plotted line series
        #
        self.plot_data = []
        if len(self.data[0]) == 0:
            max_y = min_y = 0
        else:
            max_y = min_y = self.data[0][0]
        for i in range(len(self.data)):
            p = self.axes.plot(
                self.data[i],
                linewidth=1,
                color=self.state.colors[i],
                label=self.state.fields[i],
                )[0]
            self.plot_data.append(p)
            if len(self.data[i]) != 0:
                min_y = min(min_y, min(self.data[i]))
                max_y = max(max_y, max(self.data[i]))

        # create X data
        self.xdata = numpy.arange(-self.state.timespan, 0, self.state.tickresolution)
        self.axes.set_xbound(lower=self.xdata[0], upper=0)
        if min_y == max_y:
            self.axes.set_ybound(min_y, max_y+0.1)



    def draw_plot(self):
        """ Redraws the plot
        """
        import numpy, pylab
        state = self.state

        if len(self.data[0]) == 0:
            print("no data to plot")
            return
        vhigh = max(self.data[0])
        vlow  = min(self.data[0])

        for i in range(1,len(self.plot_data)):
            vhigh = max(vhigh, max(self.data[i]))
            vlow  = min(vlow,  min(self.data[i]))
        ymin = vlow  - 0.05*(vhigh-vlow)
        ymax = vhigh + 0.05*(vhigh-vlow)

        if ymin == ymax:
            ymax = ymin + 0.1
            ymin = ymin - 0.1
        self.axes.set_ybound(lower=ymin, upper=ymax)
        self.axes.grid(True, color='gray')
        pylab.setp(self.axes.get_xticklabels(), visible=True)
        pylab.setp(self.axes.get_legend().get_texts(), fontsize='small')

        for i in range(len(self.plot_data)):
            ydata = numpy.array(self.data[i])
            xdata = self.xdata
            if len(ydata) < len(self.xdata):
                xdata = xdata[-len(ydata):]
            self.plot_data[i].set_xdata(xdata)
            self.plot_data[i].set_ydata(ydata)

        self.canvas.draw()

    def on_pause_button(self, event):
        self.paused = not self.paused

    def on_update_pause_button(self, event):
        label = "Resume" if self.paused else "Pause"
        self.pause_button.SetLabel(label)

    def on_close_button(self, event):
        self.redraw_timer.Stop()
        self.Destroy()

    def on_idle(self, event):
        import time
        time.sleep(self.state.tickresolution*0.5)

    def on_redraw_timer(self, event):
        # if paused do not add data, but still redraw the plot
        # (to respond to scale modifications, grid change, etc.)
        #
        state = self.state
        if state.close_graph.wait(0.001):
            self.redraw_timer.Stop()
            self.Destroy()
            return
        while state.child_pipe.poll():
            state.values = state.child_pipe.recv()
        if self.paused:
            return
        for i in range(len(self.plot_data)):
            if state.values[i] is not None:
                self.data[i].append(state.values[i])
                while len(self.data[i]) > len(self.xdata):
                    self.data[i].pop(0)

        for i in range(len(self.plot_data)):
            if state.values[i] is None or len(self.data[i]) < 2:
                return
        self.axes.legend(state.fields, loc='upper left', bbox_to_anchor=(0, 1.1))
        self.draw_plot()

if __name__ == "__main__":
    # test the graph
    import time, math
    livegraph = LiveGraph(['sin(t)', 'cos(t)'],
                          title='Graph Test')
    while livegraph.is_alive():
        t = time.time()
        livegraph.add_values([math.sin(t), math.cos(t)])
        time.sleep(0.05)

########NEW FILE########
__FILENAME__ = mp_image
#!/usr/bin/env python
'''
display a image in a subprocess
Andrew Tridgell
June 2012
'''

import time
import wx

try:
    import cv2.cv as cv
except ImportError:
    import cv

from MAVProxy.modules.lib import mp_util
from MAVProxy.modules.lib import mp_widgets
from MAVProxy.modules.lib.mp_menu import *


class MPImageData:
    '''image data to display'''
    def __init__(self, img):
        self.width = img.width
        self.height = img.height
        self.data = img.tostring()

class MPImageTitle:
    '''window title to use'''
    def __init__(self, title):
        self.title = title

class MPImageBrightness:
    '''image brightness to use'''
    def __init__(self, brightness):
        self.brightness = brightness

class MPImageFitToWindow:
    '''fit image to window'''
    def __init__(self):
        pass

class MPImageFullSize:
    '''show full image resolution'''
    def __init__(self):
        pass

class MPImageMenu:
    '''window menu to add'''
    def __init__(self, menu):
        self.menu = menu

class MPImagePopupMenu:
    '''popup menu to add'''
    def __init__(self, menu):
        self.menu = menu

class MPImageNewSize:
    '''reported to parent when window size changes'''
    def __init__(self, size):
        self.size = size

class MPImage():
    '''
    a generic image viewer widget for use in MP tools
    '''
    def __init__(self,
                 title='MPImage',
                 width=512,
                 height=512,
                 can_zoom = False,
                 can_drag = False,
                 mouse_events = False,
                 key_events = False,
                 auto_size = False,
                 report_size_changes = False):
        import multiprocessing

        self.title = title
        self.width = width
        self.height = height
        self.can_zoom = can_zoom
        self.can_drag = can_drag
        self.mouse_events = mouse_events
        self.key_events = key_events
        self.auto_size = auto_size
        self.report_size_changes = report_size_changes
        self.menu = None
        self.popup_menu = None

        self.in_queue = multiprocessing.Queue()
        self.out_queue = multiprocessing.Queue()

        self.default_menu = MPMenuSubMenu('View',
                                          items=[MPMenuItem('Fit Window', 'Fit Window', 'fitWindow'),
                                                 MPMenuItem('Full Zoom',  'Full Zoom', 'fullSize')])

        self.child = multiprocessing.Process(target=self.child_task)
        self.child.start()
        self.set_popup_menu(self.default_menu)

    def child_task(self):
        '''child process - this holds all the GUI elements'''
        import wx
        state = self

        self.app = wx.PySimpleApp()
        self.app.frame = MPImageFrame(state=self)
        self.app.frame.Show()
        self.app.MainLoop()

    def is_alive(self):
        '''check if child is still going'''
        return self.child.is_alive()

    def set_image(self, img, bgr=False):
        '''set the currently displayed image'''
        if not self.is_alive():
            return
        if bgr:
            img = cv.CloneImage(img)
            cv.CvtColor(img, img, cv.CV_BGR2RGB)
        self.in_queue.put(MPImageData(img))

    def set_title(self, title):
        '''set the frame title'''
        self.in_queue.put(MPImageTitle(title))

    def set_brightness(self, brightness):
        '''set the image brightness'''
        self.in_queue.put(MPImageBrightness(brightness))

    def fit_to_window(self):
        '''fit the image to the window'''
        self.in_queue.put(MPImageFitToWindow())

    def full_size(self):
        '''show the full image resolution'''
        self.in_queue.put(MPImageFullSize())

    def set_menu(self, menu):
        '''set a MPTopMenu on the frame'''
        self.menu = menu
        self.in_queue.put(MPImageMenu(menu))

    def set_popup_menu(self, menu):
        '''set a popup menu on the frame'''
        self.popup_menu = menu
        self.in_queue.put(MPImagePopupMenu(menu))

    def get_menu(self):
        '''get the current frame menu'''
        return self.menu

    def get_popup_menu(self):
        '''get the current popup menu'''
        return self.popup_menu

    def poll(self):
        '''check for events, returning one event'''
        if self.out_queue.qsize():
            return self.out_queue.get()
        return None

    def events(self):
        '''check for events a list of events'''
        ret = []
        while self.out_queue.qsize():
            ret.append(self.out_queue.get())
        return ret

from PIL import Image

class MPImageFrame(wx.Frame):
    """ The main frame of the viewer
    """
    def __init__(self, state):
        wx.Frame.__init__(self, None, wx.ID_ANY, state.title)
        self.state = state
        state.frame = self
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        state.panel = MPImagePanel(self, state)
        self.sizer.Add(state.panel, 1, wx.EXPAND)
        self.SetSizer(self.sizer)
        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.Bind(wx.EVT_SIZE, state.panel.on_size)

    def on_idle(self, event):
        '''prevent the main loop spinning too fast'''
        state = self.state
        time.sleep(0.1)

class MPImagePanel(wx.Panel):
    """ The image panel
    """
    def __init__(self, parent, state):
        wx.Panel.__init__(self, parent)
        self.frame = parent
        self.state = state
        self.img = None
        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
        self.Bind(wx.EVT_SET_FOCUS, self.on_focus)
        self.redraw_timer.Start(100)

        self.mouse_down = None
        self.drag_step = 10
        self.zoom = 1.0
        self.menu = None
        self.popup_menu = None
        self.wx_popup_menu = None
        self.popup_pos = None
        self.last_size = None
        state.brightness = 1.0

        # dragpos is the top left position in image coordinates
        self.dragpos = wx.Point(0,0)
        self.need_redraw = True

        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.mainSizer)

        # panel for the main image
        self.imagePanel = mp_widgets.ImagePanel(self, wx.EmptyImage(state.width,state.height))
        self.mainSizer.Add(self.imagePanel, flag=wx.TOP|wx.LEFT|wx.GROW, border=0)
        if state.mouse_events:
            self.imagePanel.Bind(wx.EVT_MOUSE_EVENTS, self.on_event)
        else:
            self.imagePanel.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse_event)
        if state.key_events:
            self.imagePanel.Bind(wx.EVT_KEY_DOWN, self.on_event)
        else:
            self.imagePanel.Bind(wx.EVT_KEY_DOWN, self.on_key_event)
        self.imagePanel.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

        self.redraw()
        state.frame.Fit()

    def on_focus(self, event):
        self.imagePanel.SetFocus()

    def on_focus(self, event):
        '''called when the panel gets focus'''
        self.imagePanel.SetFocus()

    def image_coordinates(self, point):
        '''given a point in window coordinates, calculate image coordinates'''
        # the dragpos is the top left position in image coordinates
        ret = wx.Point(int(self.dragpos.x + point.x/self.zoom),
                       int(self.dragpos.y + point.y/self.zoom))
        return ret

    def redraw(self):
        '''redraw the image with current settings'''
        state = self.state

        if self.img is None:
            self.mainSizer.Fit(self)
            self.Refresh()
            state.frame.Refresh()
            self.SetFocus()
            return

        # get the current size of the containing window frame
        size = self.frame.GetSize()
        (width, height) = (self.img.GetWidth(), self.img.GetHeight())

        rect = wx.Rect(self.dragpos.x, self.dragpos.y, int(size.x/self.zoom), int(size.y/self.zoom))

        #print("redraw", self.zoom, self.dragpos, size, rect);

        if rect.x > width-1:
            rect.x = width-1
        if rect.y > height-1:
            rect.y = height-1
        if rect.width > width - rect.x:
            rect.width = width - rect.x
        if rect.height > height - rect.y:
            rect.height = height - rect.y

        scaled_image = self.img.Copy()
        scaled_image = scaled_image.GetSubImage(rect);
        scaled_image = scaled_image.Rescale(int(rect.width*self.zoom), int(rect.height*self.zoom))
        if state.brightness != 1.0:
            pimg = mp_util.wxToPIL(scaled_image)
            pimg = Image.eval(pimg, lambda x: int(x * state.brightness))
            scaled_image = mp_util.PILTowx(pimg)
        self.imagePanel.set_image(scaled_image)
        self.need_redraw = False

        self.mainSizer.Fit(self)
        self.Refresh()
        state.frame.Refresh()
        self.SetFocus()
        '''
        from guppy import hpy
        h = hpy()
        print h.heap()
        '''


    def on_redraw_timer(self, event):
        '''the redraw timer ensures we show new map tiles as they
        are downloaded'''
        state = self.state
        while state.in_queue.qsize():
            obj = state.in_queue.get()
            if isinstance(obj, MPImageData):
                img = wx.EmptyImage(obj.width, obj.height)
                img.SetData(obj.data)
                self.img = img
                self.need_redraw = True
                if state.auto_size:
                    client_area = state.frame.GetClientSize()
                    total_area = state.frame.GetSize()
                    bx = max(total_area.x - client_area.x,0)
                    by = max(total_area.y - client_area.y,0)
                    state.frame.SetSize(wx.Size(obj.width+bx, obj.height+by))
            if isinstance(obj, MPImageTitle):
                state.frame.SetTitle(obj.title)
            if isinstance(obj, MPImageMenu):
                self.set_menu(obj.menu)
            if isinstance(obj, MPImagePopupMenu):
                self.set_popup_menu(obj.menu)
            if isinstance(obj, MPImageBrightness):
                state.brightness = obj.brightness
                self.need_redraw = True
            if isinstance(obj, MPImageFullSize):
                self.full_size()
            if isinstance(obj, MPImageFitToWindow):
                self.fit_to_window()
        if self.need_redraw:
            self.redraw()

    def on_size(self, event):
        '''handle window size changes'''
        state = self.state
        self.need_redraw = True
        if state.report_size_changes:
            # tell owner the new size
            size = self.frame.GetSize()
            if size != self.last_size:
                self.last_size = size
                state.out_queue.put(MPImageNewSize(size))

    def limit_dragpos(self):
        '''limit dragpos to sane values'''
        if self.dragpos.x < 0:
            self.dragpos.x = 0
        if self.dragpos.y < 0:
            self.dragpos.y = 0
        if self.img is None:
            return
        if self.dragpos.x >= self.img.GetWidth():
            self.dragpos.x = self.img.GetWidth()-1
        if self.dragpos.y >= self.img.GetHeight():
            self.dragpos.y = self.img.GetHeight()-1

    def on_mouse_wheel(self, event):
        '''handle mouse wheel zoom changes'''
        state = self.state
        if not state.can_zoom:
            return
        mousepos = self.image_coordinates(event.GetPosition())
        rotation = event.GetWheelRotation() / event.GetWheelDelta()
        oldzoom = self.zoom
        if rotation > 0:
            self.zoom /= 1.0/(1.1 * rotation)
        elif rotation < 0:
            self.zoom /= 1.1 * (-rotation)
        if self.zoom > 10:
            self.zoom = 10
        elif self.zoom < 0.1:
            self.zoom = 0.1
        if oldzoom < 1 and self.zoom > 1:
            self.zoom = 1
        if oldzoom > 1 and self.zoom < 1:
            self.zoom = 1
        self.need_redraw = True
        new = self.image_coordinates(event.GetPosition())
        # adjust dragpos so the zoom doesn't change what pixel is under the mouse
        self.dragpos = wx.Point(self.dragpos.x - (new.x-mousepos.x), self.dragpos.y - (new.y-mousepos.y))
        self.limit_dragpos()

    def on_drag_event(self, event):
        '''handle mouse drags'''
        state = self.state
        if not state.can_drag:
            return
        newpos = self.image_coordinates(event.GetPosition())
        dx = -(newpos.x - self.mouse_down.x)
        dy = -(newpos.y - self.mouse_down.y)
        self.dragpos = wx.Point(self.dragpos.x+dx,self.dragpos.y+dy)
        self.limit_dragpos()
        self.mouse_down = newpos
        self.need_redraw = True
        self.redraw()

    def show_popup_menu(self, pos):
        '''show a popup menu'''
        self.popup_pos = self.image_coordinates(pos)
        self.frame.PopupMenu(self.wx_popup_menu, pos)

    def on_mouse_event(self, event):
        '''handle mouse events'''
        pos = event.GetPosition()
        if event.RightDown() and self.popup_menu is not None:
            self.show_popup_menu(pos)
            return
        if event.Leaving():
            self.mouse_pos = None
        else:
            self.mouse_pos = pos

        if event.LeftDown():
            self.mouse_down = self.image_coordinates(pos)
        if event.Dragging() and event.ButtonIsDown(wx.MOUSE_BTN_LEFT):
            self.on_drag_event(event)

    def on_key_event(self, event):
        '''handle key events'''
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_HOME:
            self.zoom = 1.0
            self.dragpos = wx.Point(0, 0)
            self.need_redraw = True

    def on_event(self, event):
        '''pass events to the parent'''
        state = self.state
        if isinstance(event, wx.MouseEvent):
            self.on_mouse_event(event)
        if isinstance(event, wx.KeyEvent):
            self.on_key_event(event)
        if (isinstance(event, wx.MouseEvent) and
            not event.ButtonIsDown(wx.MOUSE_BTN_ANY) and
            event.GetWheelRotation() == 0):
            # don't flood the queue with mouse movement
            return
        evt = mp_util.object_container(event)
        pt = self.image_coordinates(wx.Point(evt.X,evt.Y))
        evt.X = pt.x
        evt.Y = pt.y
        state.out_queue.put(evt)

    def on_menu(self, event):
        '''called on menu event'''
        state = self.state
        if self.popup_menu is not None:
            ret = self.popup_menu.find_selected(event)
            if ret is not None:
                ret.popup_pos = self.popup_pos
                if ret.returnkey == 'fitWindow':
                    self.fit_to_window()
                elif ret.returnkey == 'fullSize':
                    self.full_size()
                else:
                    state.out_queue.put(ret)
                return
        if self.menu is not None:
            ret = self.menu.find_selected(event)
            if ret is not None:
                state.out_queue.put(ret)
                return

    def set_menu(self, menu):
        '''add a menu from the parent'''
        self.menu = menu
        wx_menu = menu.wx_menu()
        self.frame.SetMenuBar(wx_menu)
        self.frame.Bind(wx.EVT_MENU, self.on_menu)

    def set_popup_menu(self, menu):
        '''add a popup menu from the parent'''
        self.popup_menu = menu
        if menu is None:
            self.wx_popup_menu = None
        else:
            self.wx_popup_menu = menu.wx_menu()
            self.frame.Bind(wx.EVT_MENU, self.on_menu)

    def fit_to_window(self):
        '''fit image to window'''
        state = self.state
        self.dragpos = wx.Point(0, 0)
        client_area = state.frame.GetClientSize()
        self.zoom = min(float(client_area.x) / self.img.GetWidth(),
                        float(client_area.y) / self.img.GetHeight())
        self.need_redraw = True

    def full_size(self):
        '''show image at full size'''
        self.dragpos = wx.Point(0, 0)
        self.zoom = 1.0
        self.need_redraw = True

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser("mp_image.py <file>")
    parser.add_option("--zoom", action='store_true', default=False, help="allow zoom")
    parser.add_option("--drag", action='store_true', default=False, help="allow drag")
    parser.add_option("--autosize", action='store_true', default=False, help="auto size window")
    (opts, args) = parser.parse_args()

    im = MPImage(mouse_events=True,
                 key_events=True,
                 can_drag = opts.drag,
                 can_zoom = opts.zoom,
                 auto_size = opts.autosize)
    img = cv.LoadImage(args[0])
    im.set_image(img, bgr=True)

    while im.is_alive():
        for event in im.events():
            if isinstance(event, MPMenuItem):
                print(event)
                continue
            print event.ClassName
            if event.ClassName == 'wxMouseEvent':
                print 'mouse', event.X, event.Y
            if event.ClassName == 'wxKeyEvent':
                print 'key %u' % event.KeyCode
        time.sleep(0.1)

########NEW FILE########
__FILENAME__ = mp_menu
#!/usr/bin/env python
'''
menu handling widgets for wx

Andrew Tridgell
November 2013
'''

import wx

class MPMenuGeneric(object):
    '''a MP menu separator'''
    def __init__(self):
        pass

    def find_selected(self, event):
        return None

    def _append(self, menu):
        '''append this menu item to a menu'''
        pass

    def __str__(self):
        return "MPMenuGeneric()"

    def __repr__(self):
        return str(self.__str__())

class MPMenuSeparator(MPMenuGeneric):
    '''a MP menu separator'''
    def __init__(self):
        MPMenuGeneric.__init__(self)

    def _append(self, menu):
        '''append this menu item to a menu'''
        menu.AppendSeparator()

    def __str__(self):
        return "MPMenuSeparator()"


class MPMenuItem(MPMenuGeneric):
    '''a MP menu item'''
    def __init__(self, name, description='', returnkey=None, handler=None):
        MPMenuGeneric.__init__(self)
        self.name = name
        self.description = description
        self.returnkey = returnkey
        self.handler = handler
        self.handler_result = None

    def find_selected(self, event):
        '''find the selected menu item'''
        if event.GetId() == self.id():
            return self
        return None

    def call_handler(self):
        '''optionally call a handler function'''
        if self.handler is None:
            return
        call = getattr(self.handler, 'call', None)
        if call is not None:
            self.handler_result = call()

    def id(self):
        '''id used to identify the returned menu items
        uses a 16 bit unsigned integer'''
        # 0xFFFF is used as windows only allows for 16 bit IDs
        return int(hash((self.name, self.returnkey)) & 0xFFFF)

    def _append(self, menu):
        '''append this menu item to a menu'''
        menu.Append(self.id(), self.name, self.description)

    def __str__(self):
        return "MPMenuItem(%s,%s,%s)" % (self.name, self.description, self.returnkey)


class MPMenuCheckbox(MPMenuItem):
    '''a MP menu item as a checkbox'''
    def __init__(self, name, description='', returnkey=None, checked=False, handler=None):
        MPMenuItem.__init__(self, name, description=description, returnkey=returnkey, handler=handler)
        self.checked = checked

    def find_selected(self, event):
        '''find the selected menu item'''
        if event.GetId() == self.id():
            self.checked = event.IsChecked()
            return self
        return None

    def IsChecked(self):
        '''return true if item is checked'''
        return self.checked

    def _append(self, menu):
        '''append this menu item to a menu'''
        menu.AppendCheckItem(self.id(), self.name, self.description)
        menu.Check(self.id(), self.checked)

    def __str__(self):
        return "MPMenuCheckbox(%s,%s,%s,%s)" % (self.name, self.description, self.returnkey, str(self.checked))

class MPMenuRadio(MPMenuItem):
    '''a MP menu item as a radio item'''
    def __init__(self, name, description='', returnkey=None, selected=None, items=[], handler=None):
        MPMenuItem.__init__(self, name, description=description, returnkey=returnkey, handler=handler)
        self.items = items
        self.choice = 0
        self.initial = selected

    def set_choices(self, items):
        '''set radio item choices'''
        self.items = items

    def get_choice(self):
        '''return the chosen item'''
        return self.items[self.choice]

    def find_selected(self, event):
        '''find the selected menu item'''
        first = self.id()
        last = first + len(self.items) - 1
        evid = event.GetId()
        if evid >= first and evid <= last:
            self.choice = evid - first
            return self
        return None

    def _append(self, menu):
        '''append this menu item to a menu'''
        submenu = wx.Menu()
        for i in range(len(self.items)):
            submenu.AppendRadioItem(self.id()+i, self.items[i], self.description)
            if self.items[i] == self.initial:
                submenu.Check(self.id()+i, True)
        menu.AppendMenu(-1, self.name, submenu)

    def __str__(self):
        return "MPMenuRadio(%s,%s,%s,%s)" % (self.name, self.description, self.returnkey, self.get_choice())


class MPMenuSubMenu(MPMenuGeneric):
    '''a MP menu item'''
    def __init__(self, name, items):
        MPMenuGeneric.__init__(self)
        self.name = name
        self.items = items

    def add(self, items, addto=None):
        '''add more items to a sub-menu'''
        if not isinstance(items, list):
            items = [items]
        self.items.extend(items)

    def combine(self, submenu):
        '''combine a new menu with an existing one'''
        self.items.extend(submenu.items)

    def wx_menu(self):
        '''return a wx.Menu() for this menu'''
        menu = wx.Menu()
        for i in range(len(self.items)):
            m = self.items[i]
            m._append(menu)
        return menu

    def find_selected(self, event):
        '''find the selected menu item'''
        for m in self.items:
            ret = m.find_selected(event)
            if ret is not None:
                return ret
        return None

    def _append(self, menu):
        '''append this menu item to a menu'''
        menu.AppendMenu(-1, self.name, self.wx_menu())

    def __str__(self):
        return "MPMenuSubMenu(%s)" % (self.name)


class MPMenuTop(object):
    '''a MP top level menu'''
    def __init__(self, items):
        self.items = items

    def add(self, items):
        '''add a submenu'''
        if not isinstance(items, list):
            items = [items]
        self.items.extend(items)

    def wx_menu(self):
        '''return a wx.MenuBar() for the menu'''
        menubar = wx.MenuBar()
        for i in range(len(self.items)):
            m = self.items[i]
            menubar.Append(m.wx_menu(), m.name)
        return menubar

    def find_selected(self, event):
        '''find the selected menu item'''
        for i in range(len(self.items)):
            m = self.items[i]
            ret = m.find_selected(event)
            if ret is not None:
                return ret
        return None

class MPMenuCallFileDialog(object):
    '''used to create a file dialog callback'''
    def __init__(self, flags=wx.FD_OPEN, title='Filename', wildcard='*.*'):
        self.flags = flags
        self.title = title
        self.wildcard = wildcard

    def call(self):
        '''show a file dialog'''
        dlg = wx.FileDialog(None, self.title, '', "", self.wildcard, self.flags)
        if dlg.ShowModal() != wx.ID_OK:
            return None
        return dlg.GetPath()

class MPMenuCallTextDialog(object):
    '''used to create a value dialog callback'''
    def __init__(self, title='Enter Value', default=''):
        self.title = title
        self.default = default

    def call(self):
        '''show a value dialog'''
        dlg = wx.TextEntryDialog(None, self.title, self.title, defaultValue=str(self.default))
        if dlg.ShowModal() != wx.ID_OK:
            return None
        return dlg.GetValue()

if __name__ == '__main__':
    from MAVProxy.modules.lib.mp_image import MPImage
    import time
    im = MPImage(mouse_events=True,
                 key_events=True,
                 can_drag = False,
                 can_zoom = False,
                 auto_size = True)

    menu = MPMenuTop([MPMenuSubMenu('&File',
                                    items=[MPMenuItem('&Open\tCtrl+O'),
                                           MPMenuItem('&Save\tCtrl+S'),
                                           MPMenuItem('Close', 'Close'),
                                           MPMenuItem('&Quit\tCtrl+Q', 'Quit')]),
                      MPMenuSubMenu('Edit',
                                    items=[MPMenuSubMenu('Option',
                                                         items=[MPMenuItem('Foo'),
                                                                MPMenuItem('Bar'),
                                                                MPMenuSeparator(),
                                                                MPMenuCheckbox('&Grid\tCtrl+G')]),
                                           MPMenuItem('Image', 'EditImage'),
                                           MPMenuRadio('Colours',
                                                       items=['Red','Green','Blue']),
                                           MPMenuRadio('Shapes',
                                                       items=['Circle','Square','Triangle'])])])

    im.set_menu(menu)

    popup = MPMenuSubMenu('A Popup',
                          items=[MPMenuItem('Sub1'),
                                 MPMenuItem('Sub2'),
                                 MPMenuItem('Sub3')])

    im.set_popup_menu(popup)

    while im.is_alive():
        for event in im.events():
            if isinstance(event, MPMenuItem):
                print(event, getattr(event, 'popup_pos', None))
                continue
            else:
                print(event)
        time.sleep(0.1)

########NEW FILE########
__FILENAME__ = mp_module

class MPModule(object):
    '''
    The base class for all modules
    '''

    def __init__(self, mpstate, name, description=None, public=False):
        '''
        Constructor

        if public is true other modules can find this module instance with module('name')
        '''
        self.mpstate = mpstate
        self.name = name
        if description is None:
            self.description = name + " handling"
        else:
            self.description = description
        if public:
            mpstate.public_modules[name] = self

    #
    # Overridable hooks follow...
    #

    def idle_task(self):
        pass

    def unload(self):
        pass

    def unknown_command(self, args):
        '''Return True if we have handled the unknown command'''
        return False

    def mavlink_packet(self, packet):
        pass

    #
    # Methods for subclass use
    #

    def module(self, name):
        '''Find a public module (most modules are private)'''
        return self.mpstate.module(name)

    @property
    def console(self):
        return self.mpstate.console

    @property
    def status(self):
        return self.mpstate.status

    @property
    def mav_param(self):
        return self.mpstate.mav_param

    @property
    def settings(self):
        return self.mpstate.settings

    @property
    def vehicle_type(self):
        return self.mpstate.vehicle_type

    @property
    def vehicle_name(self):
        return self.mpstate.vehicle_name

    @property
    def sitl_output(self):
        return self.mpstate.sitl_output

    @property
    def target_system(self):
        return self.mpstate.status.target_system

    @property
    def target_component(self):
        return self.mpstate.status.target_component

    @property
    def master(self):
        return self.mpstate.master()

    @property
    def continue_mode(self):
        return self.mpstate.continue_mode

    @property
    def logdir(self):
        return self.mpstate.status.logdir

    def say(self, msg, priority='important'):
        return self.mpstate.functions.say(msg)

    def get_mav_param(self, param_name, default=None):
        return self.mpstate.functions.get_mav_param(param_name, default)

    def param_set(self, name, value, retries=3):
        self.mpstate.functions.param_set(name, value, retries)

    def add_command(self, name, callback, description, completions=None):
        self.mpstate.command_map[name] = (callback, description)
        if completions is not None:
            self.mpstate.completions[name] = completions

    def add_completion_function(self, name, callback):
        self.mpstate.completion_functions[name] = callback

########NEW FILE########
__FILENAME__ = mp_settings
#!/usr/bin/env python
'''settings object for MAVProxy modules'''

import time

class MPSetting:
    def __init__(self, name, type, default, label=None, tab=None,
                 range=None, increment=None, format=None,
                 digits=None, choice=None):
        if label is None:
            label = name
        self.name = name
        self.type = type
        self.default = default
        self.label = label
        self.value = default
        self.tab = tab
        self.range = range
        if range is not None:
            # check syntax
            (minv, maxv) = range
        self.increment = increment
        self.choice = choice
        self.format = format
        self.digits = digits

    def set(self, value):
        '''set a setting'''
        if value == 'None' and self.default is None:
            value = None
        if value is not None:
            if self.type == bool:
                if str(value).lower() in ['1', 'true', 'yes']:
                    value = True
                elif str(value).lower() in ['0', 'false', 'no']:
                    value = False
                else:
                    return False
            else:
                try:
                    value = self.type(value)
                except:
                    return False
        if self.range is not None:
            (minv,maxv) = self.range
            if value < minv or value > maxv:
                return False
        if self.choice is not None:
            if value not in self.choice:
                return False
        self.value = value
        return True

class MPSettings(object):
    def __init__(self, vars, title='Settings'):
        self._vars = {}
        self._title = title
        self._default_tab = 'Settings'
        self._keys = []
        self._callback = None
        self._last_change = time.time()
        for v in vars:
            self.append(v)

    def get_title(self):
        '''return the title'''
        return self._title

    def get_setting(self, name):
        '''return a MPSetting object'''
        return self._vars[name]

    def append(self, v):
        '''add a new setting'''
        if isinstance(v, MPSetting):
            setting = v
        else:
            (name,type,default) = v
            label = name
            tab = None
            if len(v) > 3:
                label = v[3]
            if len(v) > 4:
                tab = v[4]
            setting = MPSetting(name, type, default, label=label, tab=tab)

        # when a tab name is set, cascade it to future settings
        if setting.tab is None:
            setting.tab = self._default_tab
        else:
            self._default_tab = setting.tab
        self._vars[setting.name] = setting
        self._keys.append(setting.name)
        self._last_change = time.time()


    def __getattr__(self, name):
        if name in self._vars:
            return self._vars[name].value
        raise AttributeError

    def __setattr__(self, name, value):
        if name[0] == '_':
            self.__dict__[name] = value
            return
        if name in self._vars:
            self._vars[name].value = value
            return
        raise AttributeError

    def set(self, name, value):
        '''set a setting'''
        if not name in self._vars:
            raise AttributeError
        setting = self._vars[name]
        oldvalue = setting.value
        if not setting.set(value):
            print("Unable to convert %s to type %s" % (value, setting.type))
            return False
        if oldvalue != setting.value:
            self._last_change = time.time()
            if self._callback:
                self._callback(setting)
        return True

    def get(self, name):
        '''get a setting'''
        if not name in self._vars:
            raise AttributeError
        setting = self._vars[name]
        return setting.value

    def show(self, v):
        '''show settings'''
        print("%20s %s" % (v, getattr(self, v)))

    def show_all(self):
        '''show all settings'''
        for setting in sorted(self._vars):
            self.show(setting)

    def list(self):
        '''list all settings'''
        return self._keys

    def completion(self, text):
        '''completion function for cmdline completion'''
        return self.list()

    def command(self, args):
        '''control options from cmdline'''
        if len(args) == 0:
            self.show_all()
            return
        if getattr(self, args[0], [None]) == [None]:
            print("Unknown setting '%s'" % args[0])
            return
        if len(args) == 1:
            self.show(args[0])
        else:
            self.set(args[0], args[1])

    def set_callback(self, callback):
        '''set a callback to be called on set()'''
        self._callback = callback

    def save(self, filename):
        '''save settings to a file. Return True/False on success/failure'''
        try:
            f = open(filename, mode='w')
        except Exception:
            return False
        for k in self.list():
            f.write("%s=%s\n" % (k, self.get(k)))
        f.close()
        return True


    def load(self, filename):
        '''load settings from a file. Return True/False on success/failure'''
        try:
            f = open(filename, mode='r')
        except Exception:
            return False
        while True:
            line = f.readline()
            if not line:
                break
            line = line.rstrip()
            eq = line.find('=')
            if eq == -1:
                continue
            name = line[:eq]
            value = line[eq+1:]
            self.set(name, value)
        f.close()
        return True

    def last_change(self):
        '''return last change time'''
        return self._last_change

########NEW FILE########
__FILENAME__ = mp_util
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''common mavproxy utility functions'''

import math
import os

radius_of_earth = 6378100.0 # in meters

def gps_distance(lat1, lon1, lat2, lon2):
    '''return distance between two points in meters,
    coordinates are in degrees
    thanks to http://www.movable-type.co.uk/scripts/latlong.html'''
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    lon1 = math.radians(lon1)
    lon2 = math.radians(lon2)
    dLat = lat2 - lat1
    dLon = lon2 - lon1

    a = math.sin(0.5*dLat)**2 + math.sin(0.5*dLon)**2 * math.cos(lat1) * math.cos(lat2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0-a))
    return radius_of_earth * c


def gps_bearing(lat1, lon1, lat2, lon2):
    '''return bearing between two points in degrees, in range 0-360
    thanks to http://www.movable-type.co.uk/scripts/latlong.html'''
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    lon1 = math.radians(lon1)
    lon2 = math.radians(lon2)
    dLat = lat2 - lat1
    dLon = lon2 - lon1
    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(dLon)
    bearing = math.degrees(math.atan2(y, x))
    if bearing < 0:
        bearing += 360.0
    return bearing


def wrap_valid_longitude(lon):
    ''' wrap a longitude value around to always have a value in the range
        [-180, +180) i.e 0 => 0, 1 => 1, -1 => -1, 181 => -179, -181 => 179
    '''
    return (((lon + 180.0) % 360.0) - 180.0)

def gps_newpos(lat, lon, bearing, distance):
    '''extrapolate latitude/longitude given a heading and distance
    thanks to http://www.movable-type.co.uk/scripts/latlong.html
    '''
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    brng = math.radians(bearing)
    dr = distance/radius_of_earth

    lat2 = math.asin(math.sin(lat1)*math.cos(dr) +
                     math.cos(lat1)*math.sin(dr)*math.cos(brng))
    lon2 = lon1 + math.atan2(math.sin(brng)*math.sin(dr)*math.cos(lat1),
                             math.cos(dr)-math.sin(lat1)*math.sin(lat2))
    return (math.degrees(lat2), wrap_valid_longitude(math.degrees(lon2)))

def gps_offset(lat, lon, east, north):
    '''return new lat/lon after moving east/north
    by the given number of meters'''
    bearing = math.degrees(math.atan2(east, north))
    distance = math.sqrt(east**2 + north**2)
    return gps_newpos(lat, lon, bearing, distance)


def mkdir_p(dir):
    '''like mkdir -p'''
    if not dir:
        return
    if dir.endswith("/") or dir.endswith("\\"):
        mkdir_p(dir[:-1])
        return
    if os.path.isdir(dir):
        return
    mkdir_p(os.path.dirname(dir))
    try:
        os.mkdir(dir)
    except Exception:
        pass

def polygon_load(filename):
    '''load a polygon from a file'''
    ret = []
    f = open(filename)
    for line in f:
        if line.startswith('#'):
            continue
        line = line.strip()
        if not line:
            continue
        a = line.split()
        if len(a) != 2:
            raise RuntimeError("invalid polygon line: %s" % line)
        ret.append((float(a[0]), float(a[1])))
    f.close()
    return ret


def polygon_bounds(points):
    '''return bounding box of a polygon in (x,y,width,height) form'''
    (minx, miny) = (points[0][0], points[0][1])
    (maxx, maxy) = (minx, miny)
    for p in points:
        minx = min(minx, p[0])
        maxx = max(maxx, p[0])
        miny = min(miny, p[1])
        maxy = max(maxy, p[1])
    return (minx, miny, maxx-minx, maxy-miny)

def bounds_overlap(bound1, bound2):
    '''return true if two bounding boxes overlap'''
    (x1,y1,w1,h1) = bound1
    (x2,y2,w2,h2) = bound2
    if x1+w1 < x2:
        return False
    if x2+w2 < x1:
        return False
    if y1+h1 < y2:
        return False
    if y2+h2 < y1:
        return False
    return True


class object_container:
    '''return a picklable object from an existing object,
    containing all of the normal attributes of the original'''
    def __init__(self, object):
        for v in dir(object):
            if not v.startswith('__') and v not in ['this']:
                try:
                    a = getattr(object, v)
                    if (hasattr(a, '__call__') or
                        hasattr(a, '__swig_destroy__') or
                        str(a).find('Swig Object') != -1):
                        continue
                    setattr(self, v, a)
                except Exception:
                    pass

def degrees_to_dms(degrees):
    '''return a degrees:minutes:seconds string'''
    deg = int(degrees)
    min = int((degrees - deg)*60)
    sec = ((degrees - deg) - (min/60.0))*60*60
    return u'%u\u00b0%02u\'%04.1f"' % (deg, abs(min), abs(sec))


class UTMGrid:
    '''class to hold UTM grid position'''
    def __init__(self, zone, easting, northing, hemisphere='S'):
        self.zone = zone
        self.easting = easting
        self.northing = northing
        self.hemisphere = hemisphere

    def __str__(self):
        return "%s %u %u %u" % (self.hemisphere, self.zone, self.easting, self.northing)

    def latlon(self):
        '''return (lat,lon) for the grid coordinates'''
        from MAVProxy.modules.lib.ANUGA import lat_long_UTM_conversion
        (lat, lon) = lat_long_UTM_conversion.UTMtoLL(self.northing, self.easting, self.zone, isSouthernHemisphere=(self.hemisphere=='S'))
        return (lat, lon)


def latlon_to_grid(latlon):
    '''convert to grid reference'''
    from MAVProxy.modules.lib.ANUGA import redfearn
    (zone, easting, northing) = redfearn.redfearn(latlon[0], latlon[1])
    if latlon[0] < 0:
        hemisphere = 'S'
    else:
        hemisphere = 'N'
    return UTMGrid(zone, easting, northing, hemisphere=hemisphere)

def latlon_round(latlon, spacing=1000):
    '''round to nearest grid corner'''
    g = latlon_to_grid(latlon)
    g.easting = (g.easting // spacing) * spacing
    g.northing = (g.northing // spacing) * spacing
    return g.latlon()


def wxToPIL(wimg):
    '''convert a wxImage to a PIL Image'''
    from PIL import Image
    (w,h) = wimg.GetSize()
    d     = wimg.GetData()
    pimg  = Image.new("RGB", (w,h), color=1)
    pimg.fromstring(d)
    return pimg

def PILTowx(pimg):
    '''convert a PIL Image to a wx image'''
    import wx
    wimg = wx.EmptyImage(pimg.size[0], pimg.size[1])
    wimg.SetData(pimg.convert('RGB').tostring())
    return wimg

def dot_mavproxy(name):
    '''return a path to store mavproxy data'''
    dir = os.path.join(os.environ['HOME'], '.mavproxy')
    mkdir_p(dir)
    return os.path.join(dir, name)

def download_url(url):
    '''download a URL and return the content'''
    import urllib2
    try:
        resp = urllib2.urlopen(url)
        headers = resp.info()
    except urllib2.URLError as e:
        print('Error downloading %s' % url)
        return None
    return resp.read()


def download_files(files):
    '''download an array of files'''
    for (url, file) in files:
        print("Downloading %s as %s" % (url, file))
        data = download_url(url)
        if data is None:
            continue
        try:
            open(file, mode='w').write(data)
        except Exception as e:
            print("Failed to save to %s : %s" % (file, e))

########NEW FILE########
__FILENAME__ = mp_widgets
#!/usr/bin/env python
'''
some useful wx widgets

Andrew Tridgell
June 2012
'''

import wx

class ImagePanel(wx.Panel):
    '''a resizable panel containing an image'''
    def __init__(self, parent, img):
        wx.Panel.__init__(self, parent, -1, size=(1, 1))
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.set_image(img)
        self.Bind(wx.EVT_PAINT, self.on_paint)

    def on_paint(self, event):
        '''repaint the image'''
        dc = wx.AutoBufferedPaintDC(self)
        dc.DrawBitmap(self._bmp, 0, 0)

    def set_image(self, img):
        '''set the image to be displayed'''
        self._bmp = wx.BitmapFromImage(img)
        self.SetMinSize((self._bmp.GetWidth(), self._bmp.GetHeight()))

########NEW FILE########
__FILENAME__ = rline
'''
readline handling for mavproxy
'''

import sys, glob, os

rline_mpstate = None

class rline(object):
    '''async readline abstraction'''
    def __init__(self, prompt, mpstate):
        import threading
        global rline_mpstate
        self.prompt = prompt
        rline_mpstate = mpstate
        # other modules can add their own completion functions
        mpstate.completion_functions = {
            '(FILENAME)' : complete_filename,
            '(PARAMETER)' : complete_parameter,
            '(VARIABLE)' : complete_variable,
            '(SETTING)' : rline_mpstate.settings.completion,
            '(COMMAND)' : complete_command,
            '(ALIAS)' : complete_alias
            }

    def set_prompt(self, prompt):
        if prompt != self.prompt:
            self.prompt = prompt
            sys.stdout.write(prompt)


def complete_alias(text):
    '''return list of aliases'''
    global rline_mpstate
    return rline_mpstate.aliases.keys()

def complete_command(text):
    '''return list of commands'''
    global rline_mpstate
    return rline_mpstate.command_map.keys()

def complete_filename(text):
    '''complete a filename'''

    #ensure directories have trailing slashes:
    list = glob.glob(text+'*')
    for idx, val in enumerate(list):
        if os.path.isdir(val):
            list[idx] = (val + os.path.sep)

    return list

def complete_parameter(text):
    '''complete a parameter'''
    return rline_mpstate.mav_param.keys()

def complete_variable(text):
    '''complete a MAVLink variable'''
    if text.find('.') != -1:
        var = text.split('.')[0]
        if var in rline_mpstate.status.msgs:
            ret = []
            for f in rline_mpstate.status.msgs[var].get_fieldnames():
                ret.append(var + '.' + f)
            return ret
        return []
    return rline_mpstate.status.msgs.keys()

def rule_expand(component, text):
    '''expand one rule component'''
    global rline_mpstate
    if component[0] == '<' and component[-1] == '>':
        return component[1:-1].split('|')
    if component in rline_mpstate.completion_functions:
        return rline_mpstate.completion_functions[component](text)
    return [component]

def rule_match(component, cmd):
    '''see if one rule component matches'''
    if component == cmd:
        return True
    expanded = rule_expand(component, cmd)
    if cmd in expanded:
        return True
    return False

def complete_rule(rule, cmd):
    '''complete using one rule'''
    global rline_mpstate
    rule_components = rule.split(' ')

    # check it matches so far
    for i in range(len(cmd)-1):
        if not rule_match(rule_components[i], cmd[i]):
            return []

    # expand the next rule component
    expanded = rule_expand(rule_components[len(cmd)-1], cmd[-1])
    return expanded


def complete_rules(rules, cmd):
    '''complete using a list of completion rules'''
    if not isinstance(rules, list):
        rules = [rules]
    ret = []
    for r in rules:
        ret += complete_rule(r, cmd)
    return ret


last_clist = None

def complete(text, state):
    '''completion routine for when user presses tab'''
    global last_clist
    global rline_mpstate
    if state != 0 and last_clist is not None:
        return last_clist[state]

    # split the command so far
    cmd = readline.get_line_buffer().split(' ')

    if len(cmd) == 1:
        # if on first part then complete on commands and aliases
        last_clist = complete_command(text) + complete_alias(text)
    elif cmd[0] in rline_mpstate.completions:
        # we have a completion rule for this command
        last_clist = complete_rules(rline_mpstate.completions[cmd[0]], cmd[1:])
    else:
        # assume completion by filename
        last_clist = glob.glob(text+'*')
    ret = []
    for c in last_clist:
        if c.startswith(text):
            ret.append(c)
    ret.append(None)
    last_clist = ret
    return last_clist[state]



# some python distributions don't have readline, so handle that case
# with a try/except
try:
    import readline
    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete)
except Exception:
    pass

########NEW FILE########
__FILENAME__ = textconsole
#!/usr/bin/env python

"""
  MAVProxy default console
"""
import sys

class SimpleConsole():
    '''
    a message console for MAVProxy
    '''
    def __init__(self):
        pass

    def write(self, text, fg='black', bg='white'):
        '''write to the console'''
        if isinstance(text, str):
            sys.stdout.write(text)
        else:
            sys.stdout.write(str(text))
        sys.stdout.flush()

    def writeln(self, text, fg='black', bg='white'):
        '''write to the console with linefeed'''
        if not isinstance(text, str):
            text = str(text)
        self.write(text + '\n', fg=fg, bg=bg)

    def set_status(self, name, text='', row=0, fg='black', bg='white'):
        '''set a status value'''
        pass

    def error(self, text, fg='red', bg='white'):
        self.writeln(text, fg=fg, bg=bg)

    def close(self):
        pass

    def is_alive(self):
        '''check if we are alive'''
        return True

if __name__ == "__main__":
    # test the console
    import time
    console = SimpleConsole()
    while console.is_alive():
        console.write('Tick', fg='red')
        console.write(" %s " % time.asctime())
        console.writeln('tock', bg='yellow')
        time.sleep(0.5)

########NEW FILE########
__FILENAME__ = wxconsole
#!/usr/bin/env python

"""
  MAVProxy message console, implemented in a child process
"""
import textconsole, wx, sys
import mp_menu

class Text():
    '''text to write to console'''
    def __init__(self, text, fg='black', bg='white'):
        self.text = text
        self.fg = fg
        self.bg = bg

class Value():
    '''a value for the status bar'''
    def __init__(self, name, text, row=0, fg='black', bg='white'):
        self.name = name
        self.text = text
        self.row = row
        self.fg = fg
        self.bg = bg

class MessageConsole(textconsole.SimpleConsole):
    '''
    a message console for MAVProxy
    '''
    def __init__(self,
                 title='MAVProxy: console'):
        textconsole.SimpleConsole.__init__(self)
        import multiprocessing, threading
        self.title  = title
        self.menu_callback = None
        self.parent_pipe,self.child_pipe = multiprocessing.Pipe()
        self.close_event = multiprocessing.Event()
        self.close_event.clear()
        self.child = multiprocessing.Process(target=self.child_task)
        self.child.start()
        t = threading.Thread(target=self.watch_thread)
        t.daemon = True
        t.start()

    def child_task(self):
        '''child process - this holds all the GUI elements'''
        import wx
        app = wx.PySimpleApp()
        app.frame = ConsoleFrame(state=self, title=self.title)
        app.frame.Show()
        app.MainLoop()

    def watch_thread(self):
        '''watch for menu events from child'''
        from mp_settings import MPSetting
        while True:
            msg = self.parent_pipe.recv()
            if self.menu_callback is not None:
                self.menu_callback(msg)

    def write(self, text, fg='black', bg='white'):
        '''write to the console'''
        if self.child.is_alive():
            self.parent_pipe.send(Text(text, fg, bg))

    def set_status(self, name, text='', row=0, fg='black', bg='white'):
        '''set a status value'''
        if self.child.is_alive():
            self.parent_pipe.send(Value(name, text, row, fg, bg))

    def set_menu(self, menu, callback):
        if self.child.is_alive():
            self.parent_pipe.send(menu)
            self.menu_callback = callback

    def close(self):
        '''close the console'''
        self.close_event.set()
        if self.is_alive():
            self.child.join(2)

    def is_alive(self):
        '''check if child is still going'''
        return self.child.is_alive()

class ConsoleFrame(wx.Frame):
    """ The main frame of the console"""

    def __init__(self, state, title):
        self.state = state
        wx.Frame.__init__(self, None, title=title, size=(800,300))
        self.panel = wx.Panel(self)
        state.frame = self

        # values for the status bar
        self.values = {}

        self.menu = None
        self.menu_callback = None

        self.control = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY)


        self.vbox = wx.BoxSizer(wx.VERTICAL)
        # start with one status row
        self.status = [wx.BoxSizer(wx.HORIZONTAL)]
        self.vbox.Add(self.status[0], 0, flag=wx.ALIGN_LEFT | wx.TOP)
        self.vbox.Add(self.control, 1, flag=wx.LEFT | wx.BOTTOM | wx.GROW)

        self.panel.SetSizer(self.vbox)

        self.timer = wx.Timer(self)

        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(100)

        self.Bind(wx.EVT_IDLE, self.on_idle)

        self.Show(True)
        self.pending = []

    def on_menu(self, event):
        '''handle menu selections'''
        state = self.state
        ret = self.menu.find_selected(event)
        if ret is None:
            return
        ret.call_handler()
        state.child_pipe.send(ret)

    def on_idle(self, event):
        import time
        time.sleep(0.05)

    def on_timer(self, event):
        state = self.state
        if state.close_event.wait(0.001):
            self.timer.Stop()
            self.Destroy()
            return
        while state.child_pipe.poll():
            obj = state.child_pipe.recv()
            if isinstance(obj, Value):
                # request to set a status field
                if not obj.name in self.values:
                    # create a new status field
                    value = wx.StaticText(self.panel, -1, obj.text)
                    # possibly add more status rows
                    for i in range(len(self.status), obj.row+1):
                        self.status.append(wx.BoxSizer(wx.HORIZONTAL))
                        self.vbox.Insert(len(self.status)-1, self.status[i], 0, flag=wx.ALIGN_LEFT | wx.TOP)
                        self.vbox.Layout()
                    self.status[obj.row].Add(value, border=5)
                    self.status[obj.row].AddSpacer(20)
                    self.values[obj.name] = value
                value = self.values[obj.name]
                value.SetForegroundColour(obj.fg)
                value.SetBackgroundColour(obj.bg)
                value.SetLabel(obj.text)
                self.panel.Layout()
            elif isinstance(obj, Text):
                '''request to add text to the console'''
                self.pending.append(obj)
                for p in self.pending:
                    # we're scrolled at the bottom
                    oldstyle = self.control.GetDefaultStyle()
                    style = wx.TextAttr()
                    style.SetTextColour(p.fg)
                    style.SetBackgroundColour(p.bg)
                    self.control.SetDefaultStyle(style)
                    self.control.AppendText(p.text)
                    self.control.SetDefaultStyle(oldstyle)
                self.pending = []
            elif isinstance(obj, mp_menu.MPMenuTop):
                self.menu = obj
                self.SetMenuBar(self.menu.wx_menu())
                self.Bind(wx.EVT_MENU, self.on_menu)
                self.Refresh()
                self.Update()

if __name__ == "__main__":
    # test the console
    import time
    console = MessageConsole()
    while console.is_alive():
        console.write('Tick', fg='red')
        console.write(" %s " % time.asctime())
        console.writeln('tock', bg='yellow')
        console.set_status('GPS', 'GPS: OK', fg='blue', bg='green')
        console.set_status('Link1', 'Link1: OK', fg='green', bg='write')
        console.set_status('Date', 'Date: %s' % time.asctime(), fg='red', bg='write', row=2)
        time.sleep(0.5)

########NEW FILE########
__FILENAME__ = wxsettings
'''
Graphical editing of mp_settings object
'''
import os, wx, sys

class WXSettings(object):
    '''
    a graphical settings dialog for mavproxy
    '''
    def __init__(self, settings):
        import multiprocessing, threading
        self.settings  = settings
        self.parent_pipe,self.child_pipe = multiprocessing.Pipe()
        self.close_event = multiprocessing.Event()
        self.close_event.clear()
        self.child = multiprocessing.Process(target=self.child_task)
        self.child.start()
        t = threading.Thread(target=self.watch_thread)
        t.daemon = True
        t.start()

    def child_task(self):
        '''child process - this holds all the GUI elements'''
        import threading
        app = wx.PySimpleApp()
        dlg = SettingsDlg(self.settings)
        dlg.parent_pipe = self.parent_pipe
        dlg.ShowModal()
        dlg.Destroy()

    def watch_thread(self):
        '''watch for settings changes from child'''
        from mp_settings import MPSetting
        while True:
            setting = self.child_pipe.recv()
            if not isinstance(setting, MPSetting):
                break
            try:
                self.settings.set(setting.name, setting.value)
            except Exception:
                print("Unable to set %s to %s" % (setting.name, setting.value))

    def is_alive(self):
        '''check if child is still going'''
        return self.child.is_alive()

class TabbedDialog(wx.Dialog):
    def __init__(self, tab_names, title='Title', size=wx.DefaultSize):
        wx.Dialog.__init__(self, None, -1, title,
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.tab_names = tab_names
        self.notebook = wx.Notebook(self, -1, size=size)
        self.panels = {}
        self.sizers = {}
        for t in tab_names:
            self.panels[t] = wx.Panel(self.notebook)
            self.notebook.AddPage(self.panels[t], t)
            self.sizers[t] = wx.BoxSizer(wx.VERTICAL)
            self.panels[t].SetSizer(self.sizers[t])
        self.dialog_sizer = wx.BoxSizer(wx.VERTICAL)
        self.dialog_sizer.Add(self.notebook, 1, wx.EXPAND|wx.ALL, 5)
        self.controls = {}
        self.browse_option_map = {}
        self.control_map = {}
        self.setting_map = {}
        button_box = wx.BoxSizer(wx.HORIZONTAL)
        self.button_apply = wx.Button(self, -1, "Apply")
        self.button_cancel = wx.Button(self, -1, "Cancel")
        self.button_save = wx.Button(self, -1, "Save")
        self.button_load = wx.Button(self, -1, "Load")
        button_box.Add(self.button_cancel, 0, wx.ALL)
        button_box.Add(self.button_apply, 0, wx.ALL)
        button_box.Add(self.button_save, 0, wx.ALL)
        button_box.Add(self.button_load, 0, wx.ALL)
        self.dialog_sizer.Add(button_box, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        wx.EVT_BUTTON(self, self.button_cancel.GetId(), self.on_cancel)
        wx.EVT_BUTTON(self, self.button_apply.GetId(), self.on_apply)
        wx.EVT_BUTTON(self, self.button_save.GetId(), self.on_save)
        wx.EVT_BUTTON(self, self.button_load.GetId(), self.on_load)
        self.Centre()

    def on_cancel(self, event):
        '''called on cancel'''
        self.Destroy()
        sys.exit(0)

    def on_apply(self, event):
        '''called on apply'''
        for label in self.setting_map.keys():
            setting = self.setting_map[label]
            ctrl = self.controls[label]
            value = ctrl.GetValue()
            if str(value) != str(setting.value):
                oldvalue = setting.value
                if not setting.set(value):
                    print("Invalid value %s for %s" % (value, setting.name))
                    continue
                if str(oldvalue) != str(setting.value):
                    self.parent_pipe.send(setting)

    def on_save(self, event):
        '''called on save button'''
        dlg = wx.FileDialog(None, self.settings.get_title(), '', "", '*.*',
                            wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            self.settings.save(dlg.GetPath())

    def on_load(self, event):
        '''called on load button'''
        dlg = wx.FileDialog(None, self.settings.get_title(), '', "", '*.*', wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.settings.load(dlg.GetPath())
        # update the controls with new values
        for label in self.setting_map.keys():
            setting = self.setting_map[label]
            ctrl = self.controls[label]
            value = ctrl.GetValue()
            if isinstance(value, str) or isinstance(value, unicode):
                ctrl.SetValue(str(setting.value))
            else:
                ctrl.SetValue(setting.value)

    def panel(self, tab_name):
        '''return the panel for a named tab'''
        return self.panels[tab_name]

    def sizer(self, tab_name):
        '''return the sizer for a named tab'''
        return self.sizers[tab_name]

    def refit(self):
        '''refit after elements are added'''
        self.SetSizerAndFit(self.dialog_sizer)

    def _add_input(self, setting, ctrl, ctrl2=None, value=None):
        tab_name = setting.tab
        label = setting.label
        tab = self.panel(tab_name)
        box = wx.BoxSizer(wx.HORIZONTAL)
        labelctrl = wx.StaticText(tab, -1, label )
        box.Add(labelctrl, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        box.Add( ctrl, 1, wx.ALIGN_CENTRE|wx.ALL, 5 )
        if ctrl2 is not None:
            box.Add( ctrl2, 0, wx.ALIGN_CENTRE|wx.ALL, 5 )
        self.sizer(tab_name).Add(box, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.controls[label] = ctrl
        if value is not None:
            ctrl.Value = value
        else:
            ctrl.Value = str(setting.value)
        self.control_map[ctrl.GetId()] = label
        self.setting_map[label] = setting

    def add_text(self, setting, width=300, height=100, multiline=False):
        '''add a text input line'''
        tab = self.panel(setting.tab)
        if multiline:
            ctrl = wx.TextCtrl(tab, -1, "", size=(width,height), style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER)
        else:
            ctrl = wx.TextCtrl(tab, -1, "", size=(width,-1) )
        self._add_input(setting, ctrl)

    def add_choice(self, setting, choices):
        '''add a choice input line'''
        tab = self.panel(setting.tab)
        default = setting.value
        if default is None:
            default = choices[0]
        ctrl = wx.ComboBox(tab, -1, choices=choices,
                           value = str(default),
                           style = wx.CB_DROPDOWN | wx.CB_READONLY | wx.CB_SORT )
        self._add_input(setting, ctrl)

    def add_intspin(self, setting):
        '''add a spin control'''
        tab = self.panel(setting.tab)
        default = setting.value
        (minv, maxv) = setting.range
        ctrl = wx.SpinCtrl(tab, -1,
                           initial = default,
                           min = minv,
                           max = maxv)
        self._add_input(setting, ctrl, value=default)

    def add_floatspin(self, setting):
        '''add a floating point spin control'''
        from wx.lib.agw.floatspin import FloatSpin
        tab = self.panel(setting.tab)
        default = setting.value
        (minv, maxv) = setting.range
        ctrl = FloatSpin(tab, -1,
                         value = default,
                         min_val = minv,
                         max_val = maxv,
                         increment = setting.increment)
        if setting.format is not None:
            ctrl.SetFormat(setting.format)
        if setting.digits is not None:
            ctrl.SetDigits(setting.digits)
        self._add_input(setting, ctrl, value=default)

#----------------------------------------------------------------------
class SettingsDlg(TabbedDialog):
    def __init__(self, settings):
        title = "Resize the dialog and see how controls adapt!"
        self.settings = settings
        tabs = []
        for k in self.settings.list():
            setting = self.settings.get_setting(k)
            tab = setting.tab
            if tab is None:
                tab = 'Settings'
            if not tab in tabs:
                tabs.append(tab)
        title = self.settings.get_title()
        if title is None:
            title = 'Settings'
        TabbedDialog.__init__(self, tabs, title)
        for name in self.settings.list():
            setting = self.settings.get_setting(name)
            if setting.type == bool:
                self.add_choice(setting, ['True', 'False'])
            elif setting.choice is not None:
                self.add_choice(setting, setting.choice)
            elif setting.type == int and setting.increment is not None and setting.range is not None:
                self.add_intspin(setting)
            elif setting.type == float and setting.increment is not None and setting.range is not None:
                self.add_floatspin(setting)
            else:
                self.add_text(setting)
        self.refit()

if __name__ == "__main__":
    def test_callback(setting):
        '''callback on apply'''
        print("Changing %s to %s" % (setting.name, setting.value))

    # test the settings
    import mp_settings, time
    from mp_settings import MPSetting
    settings = mp_settings.MPSettings(
        [ MPSetting('link', int, 1, tab='TabOne'),
          MPSetting('altreadout', int, 10, range=(-30,1017), increment=1),
          MPSetting('pvalue', float, 0.3, range=(-3.0,1e6), increment=0.1, digits=2),
          MPSetting('enable', bool, True, tab='TabTwo'),
          MPSetting('colour', str, 'Blue', choice=['Red', 'Green', 'Blue']),
          MPSetting('foostr', str, 'blah', label='Foo String') ])
    settings.set_callback(test_callback)
    dlg = WXSettings(settings)
    while dlg.is_alive():
        time.sleep(0.1)

########NEW FILE########
__FILENAME__ = mavproxy_antenna
#!/usr/bin/env python
'''
antenna pointing module
Andrew Tridgell
June 2012
'''

import sys, os, time
from cuav.lib import cuav_util
from MAVProxy.modules.lib import mp_module

class AntennaModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(AntennaModule, self).__init__(mpstate, "antenna", "antenna pointing module")
        self.gcs_location = None
        self.last_bearing = 0
        self.last_announce = 0
        self.add_command('antenna', self.cmd_antenna, "antenna link control")

    def cmd_antenna(self, args):
        '''set gcs location'''
        if len(args) != 2:
            if self.gcs_location is None:
                print("GCS location not set")
            else:
                print("GCS location %s" % str(self.gcs_location))
            return
        self.gcs_location = (float(args[0]), float(args[1]))



    def mavlink_packet(self, m):
        '''handle an incoming mavlink packet'''
        if self.gcs_location is None and self.module('wp').wploader.count() > 0:
            home = self.module('wp').wploader.wp(0)
            self.gcs_location = (home.x, home.y)
            print("Antenna home set")
        if self.gcs_location is None:
            return
        if m.get_type() == 'GPS_RAW' and self.gcs_location is not None:
            (gcs_lat, gcs_lon) = self.gcs_location
            bearing = cuav_util.gps_bearing(gcs_lat, gcs_lon, m.lat, m.lon)
        elif m.get_type() == 'GPS_RAW_INT' and self.gcs_location is not None:
            (gcs_lat, gcs_lon) = self.gcs_location
            bearing = cuav_util.gps_bearing(gcs_lat, gcs_lon, m.lat / 1.0e7, m.lon / 1.0e7)
        else:
            return
        self.console.set_status('Antenna', 'Antenna %.0f' % bearing, row=0)
        if abs(bearing - self.last_bearing) > 5 and (time.time() - self.last_announce) > 15:
            self.last_bearing = bearing
            self.last_announce = time.time()
            self.say("Antenna %u" % int(bearing + 0.5))

def init(mpstate):
    '''initialise module'''
    return AntennaModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_arm
#!/usr/bin/env python
'''arm/disarm command handling'''

import time, os

from MAVProxy.modules.lib import mp_module

arming_masks = {
    "all"     : 0x0001,
    "baro"    : 0x0002,
    "compass" : 0x0004,
    "gps"     : 0x0008,
    "ins"     : 0x0010,
    "params"  : 0x0020,
    "rc"      : 0x0040,
    "voltage" : 0x0080,
    "battery" : 0x0100
    }

class ArmModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(ArmModule, self).__init__(mpstate, "arm", "arm/disarm handling")
        self.add_command('arm', self.cmd_arm,      'arm motors', ['check <all|baro|compass|gps|ins|params|rc|voltage|battery>',
                                      'uncheck <all|baro|compass|gps|ins|params|rc|voltage|battery>',
                                      'list',
                                      'throttle'])
        self.add_command('disarm', self.cmd_disarm,   'disarm motors')


    def cmd_arm(self, args):
        '''arm commands'''
        usage = "usage: arm <check|uncheck|list|throttle>"
        checkables = "<all|baro|compass|gps|ins|params|rc|voltage|battery>"

        if len(args) <= 0:
            print(usage)
            return

        if args[0] == "check":
            if (len(args) < 2):
                print("usage: arm check", checkables)
                return

            arming_mask = int(self.get_mav_param("ARMING_CHECK",0))
            name = args[1].lower()
            if name == 'all':
                for name in arming_masks.keys():
                    arming_mask |= arming_masks[name]
            elif name in arming_masks:
                arming_mask |= arming_masks[name]
            else:
                print("unrecognized arm check:", name)
                return
            self.param_set("ARMING_CHECK", arming_mask)
            return

        if args[0] == "uncheck":
            if (len(args) < 2):
                print("usage: arm uncheck", checkables)
                return

            arming_mask = int(self.get_mav_param("ARMING_CHECK",0))
            name = args[1].lower()
            if name == 'all':
                arming_mask = 0
            elif name in arming_masks:
                arming_mask &= ~arming_masks[name]
            else:
                print("unrecognized arm check:", args[1])
                return

            self.param_set("ARMING_CHECK", arming_mask)
            return

        if args[0] == "list":
            arming_mask = int(self.get_mav_param("ARMING_CHECK",0))
            if arming_mask == 0:
                print("NONE")
            for name in arming_masks.keys():
                if arming_masks[name] & arming_mask:
                    print(name)
            return

        if args[0] == "throttle":
            self.master.arducopter_arm()
            return

        print(usage)

    def cmd_disarm(self, args):
        '''disarm motors'''
        self.master.arducopter_disarm()

def init(mpstate):
    '''initialise module'''
    return ArmModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_auxopt
#!/usr/bin/env python
'''auxopt command handling'''

import time, os
from MAVProxy.modules.lib import mp_module


aux_options = {
    "Nothing":"0",
    "Flip":"2",
    "SimpleMode":"3",
    "RTL":"4",
    "SaveTrim":"5",
    "SaveWP":"7",
    "MultiMode":"8",
    "CameraTrigger":"9",
    "Sonar":"10",
    "Fence":"11",
    "ResetYaw":"12",
    "SuperSimpleMode":"13",
    "AcroTrainer":"14",
    "Auto":"16",
    "AutoTune":"17",
    "Land":"18"
}

class AuxoptModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(AuxoptModule, self).__init__(mpstate, "auxopt", "auxopt command handling")
        self.add_command('auxopt', self.cmd_auxopt,   'select option for aux switches on CH7 and CH8 (ArduCopter only)',
                         ['set <7|8> <Nothing|Flip|SimpleMode|RTL|SaveTrim|SaveWP|MultiMode|CameraTrigger|Sonar|Fence|ResetYaw|SuperSimpleMode|AcroTrainer|Acro|Auto|AutoTune|Land>',
                          'reset <7|8|all>',
                          '<show|list>'])

    def aux_show(self, channel):
        param = "CH%s_OPT" % channel
        opt_num = str(int(self.get_mav_param(param)))
        option = None
        for k in aux_options.keys():
            if opt_num == aux_options[k]:
                option = k
                break
        else:
            print("AUX Channel is currently set to unknown value " + opt_num)
            return
        print("AUX Channel is currently set to " + option)

    def aux_option_validate(self, option):
        for k in aux_options:
            if option.upper() == k.upper():
                return k
        return None

    def cmd_auxopt(self, args):
        '''handle AUX switches (CH7, CH8) settings'''
        if self.mpstate.vehicle_type != 'copter':
            print("This command is only available for copter")
            return
        if len(args) == 0 or args[0] not in ('set', 'show', 'reset', 'list'):
            print("Usage: auxopt set|show|reset|list")
            return
        if args[0] == 'list':
            print("Options available:")
            for s in sorted(aux_options.keys()):
                print('  ' + s)
        elif args[0] == 'show':
            if len(args) > 2 and args[1] not in ['7', '8', 'all']:
                print("Usage: auxopt show [7|8|all]")
                return
            if len(args) < 2 or args[1] == 'all':
                self.aux_show('7')
                self.aux_show('8')
                return
            self.aux_show(args[1])
        elif args[0] == 'reset':
            if len(args) < 2 or args[1] not in ['7', '8', 'all']:
                print("Usage: auxopt reset 7|8|all")
                return
            if args[1] == 'all':
                self.param_set('CH7_OPT', '0')
                self.param_set('CH8_OPT', '0')
                return
            param = "CH%s_OPT" % args[1]
            self.param_set(param, '0')
        elif args[0] == 'set':
            if len(args) < 3 or args[1] not in ['7', '8']:
                print("Usage: auxopt set 7|8 OPTION")
                return
            option = self.aux_option_validate(args[2])
            if not option:
                print("Invalid option " + args[2])
                return
            param = "CH%s_OPT" % args[1]
            self.param_set(param, aux_options[option])
        else:
            print("Usage: auxopt set|show|list")

def init(mpstate):
    '''initialise module'''
    return AuxoptModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_calibration
#!/usr/bin/env python
'''calibration command handling'''

import time, os
from pymavlink import mavutil

from MAVProxy.modules.lib import mp_module

class CalibrationModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(CalibrationModule, self).__init__(mpstate, "calibration")
        self.add_command('ground', self.cmd_ground,   'do a ground start')
        self.add_command('level', self.cmd_level,    'set level on a multicopter')
        self.add_command('compassmot', self.cmd_compassmot, 'do compass/motor interference calibration')
        self.add_command('calpress', self.cmd_calpressure,'calibrate pressure sensors')
        self.add_command('accelcal', self.cmd_accelcal, 'do 3D accelerometer calibration')

    def cmd_ground(self, args):
        '''do a ground start mode'''
        self.master.calibrate_imu()

    def cmd_level(self, args):
        '''run a accel level'''
        self.master.calibrate_level()

    def cmd_accelcal(self, args):
        '''do a full 3D accel calibration'''
        mav = self.master
        # ack the APM to begin 3D calibration of accelerometers
        mav.mav.command_long_send(mav.target_system, mav.target_component,
                                  mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION, 0,
                                  0, 0, 0, 0, 1, 0, 0)
        count = 0
        # we expect 6 messages and acks
        while count < 6:
            m = mav.recv_match(type='STATUSTEXT', blocking=True)
            text = str(m.text)
            if not text.startswith('Place '):
                continue
            # wait for user to hit enter
            self.mpstate.rl.line = None
            while self.mpstate.rl.line is None:
                time.sleep(0.1)
            self.mpstate.rl.line = None
            count += 1
            # tell the APM that we've done as requested
            mav.mav.command_ack_send(count, 1)


    def cmd_compassmot(self, args):
        '''do a compass/motor interference calibration'''
        mav = self.master
        print("compassmot starting")
        mav.mav.command_long_send(mav.target_system, mav.target_component,
                                  mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION, 0,
                                  0, 0, 0, 0, 0, 1, 0)
        self.mpstate.rl.line = None
        while True:
            m = mav.recv_match(type=['COMMAND_ACK','COMPASSMOT_STATUS'], blocking=False)
            if m is not None:
                print(m)
                if m.get_type() == 'COMMAND_ACK':
                    break
            if self.mpstate.rl.line is not None:
                # user has hit enter, stop the process
                mav.mav.command_ack_send(0, 1)
                break
            time.sleep(0.01)
        print("compassmot done")

    def cmd_calpressure(self, args):
        '''calibrate pressure sensors'''
        self.master.calibrate_pressure()

def init(mpstate):
    '''initialise module'''
    return CalibrationModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_cameraview
#!/usr/bin/env python
'''
camera view module
Malcolm Gill
Feb 2014
'''

import math
from MAVProxy.modules.mavproxy_map import mp_slipmap
from MAVProxy.modules.mavproxy_map import mp_elevation
from MAVProxy.modules.lib import mp_util
from MAVProxy.modules.lib import mp_settings
from cuav.lib import cuav_util
from cuav.camera.cam_params import CameraParams

# documented in common.xml, can't find these constants in code
scale_latlon = 1e-7
scale_hdg = 1e-2
scale_relative_alt = 1e-3

from MAVProxy.modules.lib import mp_module

class CameraViewModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(CameraViewModule, self).__init__(mpstate, "cameraview")
        self.add_command('cameraview', self.cmd_cameraview, "camera view")
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        self.mount_roll = 0
        self.mount_pitch = 0
        self.mount_yaw = 0
        self.height = 0
        self.lat = 0
        self.lon = 0
        self.home_height = 0
        self.hdg = 0
        self.elevation_model = mp_elevation.ElevationModel()
        self.camera_params = CameraParams() # TODO how to get actual camera params
        self.settings = mp_settings.MPSettings(
            [ ('r', float, 0.5),
              ('g', float, 0.5),
              ('b', float, 1.0),
            ])
        self.update_col()

    def update_col(self):
        self.col = tuple(int(255*c) for c in (self.settings.r, self.settings.g, self.settings.b))

    def cmd_cameraview(self, args):
        '''camera view commands'''
        state = self
        if args and args[0] == 'set':
            if len(args) < 3:
                state.settings.show_all()
            else:
                state.settings.set(args[1], args[2])
                state.update_col()
        else:
            print('usage: cameraview set')

    def unload(self):
        '''unload module'''
        pass

    def scale_rc(self, servo, min, max, param):
        '''scale a PWM value'''
        # default to servo range of 1000 to 2000
        min_pwm  = self.get_mav_param('%s_MIN'  % param, 0)
        max_pwm  = self.get_mav_param('%s_MAX'  % param, 0)
        if min_pwm == 0 or max_pwm == 0:
            return 0
        if max_pwm == min_pwm:
            p = 0.0
        else:
            p = (servo-min_pwm) / float(max_pwm-min_pwm)
        v = min + p*(max-min)
        if v < min:
            v = min
        if v > max:
            v = max
        return v

    def mavlink_packet(self, m):
        '''handle an incoming mavlink packet'''
        state = self
        if m.get_type() == 'GLOBAL_POSITION_INT':
            state.lat, state.lon = m.lat*scale_latlon, m.lon*scale_latlon
            state.hdg = m.hdg*scale_hdg
            state.height = m.relative_alt*scale_relative_alt + state.home_height - state.elevation_model.GetElevation(state.lat, state.lon)
        elif m.get_type() == 'ATTITUDE':
            state.roll, state.pitch, state.yaw = math.degrees(m.roll), math.degrees(m.pitch), math.degrees(m.yaw)
        elif m.get_type() in ['GPS_RAW', 'GPS_RAW_INT']:
            if self.module('wp').wploader.count() > 0:
                home = self.module('wp').wploader.wp(0).x, self.module('wp').wploader.wp(0).y
            else:
                home = [self.master.field('HOME', c)*scale_latlon for c in ['lat', 'lon']]
            old = state.home_height # TODO TMP
            state.home_height = state.elevation_model.GetElevation(*home)

            # TODO TMP
            if state.home_height != old:
                # tridge said to get home pos from wploader,
                # but this is not the same as from master() below...!!
                # using master() gives the right coordinates
                # (i.e. matches GLOBAL_POSITION_INT coords, and $IMHOME in sim_arduplane.sh)
                # and wploader is a bit off
                print('home height changed from',old,'to',state.home_height)
        elif m.get_type() == 'SERVO_OUTPUT_RAW':
            for (axis, attr) in [('ROLL', 'mount_roll'), ('TILT', 'mount_pitch'), ('PAN', 'mount_yaw')]:
                channel = int(self.get_mav_param('MNT_RC_IN_{0}'.format(axis), 0))
                if self.get_mav_param('MNT_STAB_{0}'.format(axis), 0) and channel:
                    # enabled stabilisation on this axis
                    # TODO just guessing that RC_IN_ROLL gives the servo number, but no idea if this is really the case
                    servo = 'servo{0}_raw'.format(channel)
                    centidegrees = self.scale_rc(getattr(m, servo),
                                            self.get_mav_param('MNT_ANGMIN_{0}'.format(axis[:3])),
                                            self.get_mav_param('MNT_ANGMAX_{0}'.format(axis[:3])),
                                            param='RC{0}'.format(channel))
                    setattr(state, attr, centidegrees*0.01)
            #state.mount_roll = min(max(-state.roll,-45),45)#TODO TMP
            #state.mount_yaw = min(max(-state.yaw,-45),45)#TODO TMP
            #state.mount_pitch = min(max(-state.pitch,-45),45)#TODO TMP
        else:
            return
        if self.mpstate.map: # if the map module is loaded, redraw polygon
            # get rid of the old polygon
            self.mpstate.map.add_object(mp_slipmap.SlipClearLayer('CameraView'))

            # camera view polygon determined by projecting corner pixels of the image onto the ground
            pixel_positions = [cuav_util.pixel_position(px[0],px[1], state.height, state.pitch+state.mount_pitch, state.roll+state.mount_roll, state.yaw+state.mount_yaw, state.camera_params) for px in [(0,0), (state.camera_params.xresolution,0), (state.camera_params.xresolution,state.camera_params.yresolution), (0,state.camera_params.yresolution)]]
            if any(pixel_position is None for pixel_position in pixel_positions):
                # at least one of the pixels is not on the ground
                # so it doesn't make sense to try to draw the polygon
                return
            gps_positions = [mp_util.gps_newpos(state.lat, state.lon, math.degrees(math.atan2(*pixel_position)), math.hypot(*pixel_position)) for pixel_position in pixel_positions]

            # draw new polygon
            self.mpstate.map.add_object(mp_slipmap.SlipPolygon('cameraview', gps_positions+[gps_positions[0]], # append first element to close polygon
                                                          layer='CameraView', linewidth=2, colour=state.col))

def init(mpstate):
    '''initialise module'''
    return CameraViewModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_console
"""
  MAVProxy console

  uses lib/console.py for display
"""

import os, sys, math, time

from MAVProxy.modules.lib import wxconsole
from MAVProxy.modules.lib import textconsole
from MAVProxy.modules.mavproxy_map import mp_elevation
from pymavlink import mavutil
from MAVProxy.modules.lib import mp_util
from MAVProxy.modules.lib import mp_module
from MAVProxy.modules.lib import wxsettings
from MAVProxy.modules.lib.mp_menu import *

class ConsoleModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(ConsoleModule, self).__init__(mpstate, "console", "GUI console", public=True)
        self.in_air = False
        self.start_time = 0.0
        self.total_time = 0.0
        self.speed = 0
        mpstate.console = wxconsole.MessageConsole(title='Console')

        # setup some default status information
        mpstate.console.set_status('Mode', 'UNKNOWN', row=0, fg='blue')
        mpstate.console.set_status('GPS', 'GPS: --', fg='red', row=0)
        mpstate.console.set_status('Vcc', 'Vcc: --', fg='red', row=0)
        mpstate.console.set_status('Radio', 'Radio: --', row=0)
        mpstate.console.set_status('INS', 'INS', fg='grey', row=0)
        mpstate.console.set_status('MAG', 'MAG', fg='grey', row=0)
        mpstate.console.set_status('AS', 'AS', fg='grey', row=0)
        mpstate.console.set_status('AHRS', 'AHRS', fg='grey', row=0)
        mpstate.console.set_status('Heading', 'Hdg ---/---', row=2)
        mpstate.console.set_status('Alt', 'Alt ---', row=2)
        mpstate.console.set_status('AGL', 'AGL ---', row=2)
        mpstate.console.set_status('AirSpeed', 'AirSpeed --', row=2)
        mpstate.console.set_status('GPSSpeed', 'GPSSpeed --', row=2)
        mpstate.console.set_status('Thr', 'Thr ---', row=2)
        mpstate.console.set_status('Roll', 'Roll ---', row=2)
        mpstate.console.set_status('Pitch', 'Pitch ---', row=2)
        mpstate.console.set_status('WP', 'WP --', row=3)
        mpstate.console.set_status('WPDist', 'Distance ---', row=3)
        mpstate.console.set_status('WPBearing', 'Bearing ---', row=3)
        mpstate.console.set_status('AltError', 'AltError --', row=3)
        mpstate.console.set_status('AspdError', 'AspdError --', row=3)
        mpstate.console.set_status('FlightTime', 'FlightTime --', row=3)
        mpstate.console.set_status('ETR', 'ETR --', row=3)

        mpstate.console.ElevationMap = mp_elevation.ElevationModel()

        # create the main menu
        self.menu = MPMenuTop([])
        self.add_menu(MPMenuSubMenu('MAVProxy',
                                    items=[MPMenuItem('Settings', 'Settings', 'menuSettings'),
                                           MPMenuItem('Map', 'Load Map', '# module load map')]))

    def add_menu(self, menu):
        '''add a new menu'''
        self.menu.add(menu)
        self.mpstate.console.set_menu(self.menu, self.menu_callback)

    def unload(self):
        '''unload module'''
        self.mpstate.console.close()
        self.mpstate.console = textconsole.SimpleConsole()

    def menu_callback(self, m):
        '''called on menu selection'''
        if m.returnkey.startswith('# '):
            cmd = m.returnkey[2:]
            if m.handler is not None:
                if m.handler_result is None:
                    return
                cmd += m.handler_result
            self.mpstate.functions.process_stdin(cmd)
        if m.returnkey == 'menuSettings':
            wxsettings.WXSettings(self.settings)


    def estimated_time_remaining(self, lat, lon, wpnum, speed):
        '''estimate time remaining in mission in seconds'''
        idx = wpnum
        if wpnum >= self.module('wp').wploader.count():
            return 0
        distance = 0
        done = set()
        while idx < self.module('wp').wploader.count():
            if idx in done:
                break
            done.add(idx)
            w = self.module('wp').wploader.wp(idx)
            if w.command == mavutil.mavlink.MAV_CMD_DO_JUMP:
                idx = int(w.param1)
                continue
            idx += 1
            if (w.x != 0 or w.y != 0) and w.command in [mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                                                        mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM,
                                                        mavutil.mavlink.MAV_CMD_NAV_LOITER_TURNS,
                                                        mavutil.mavlink.MAV_CMD_NAV_LOITER_TIME,
                                                        mavutil.mavlink.MAV_CMD_NAV_LAND,
                                                        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF]:
                distance += mp_util.gps_distance(lat, lon, w.x, w.y)
                lat = w.x
                lon = w.y
                if w.command == mavutil.mavlink.MAV_CMD_NAV_LAND:
                    break
        return distance / speed



    def mavlink_packet(self, msg):
        '''handle an incoming mavlink packet'''
        if not isinstance(self.console, wxconsole.MessageConsole):
            return
        if not self.console.is_alive():
            self.mpstate.console = textconsole.SimpleConsole()
            return
        type = msg.get_type()

        master = self.master
        # add some status fields
        if type in [ 'GPS_RAW', 'GPS_RAW_INT' ]:
            if type == "GPS_RAW":
                num_sats1 = master.field('GPS_STATUS', 'satellites_visible', 0)
            else:
                num_sats1 = msg.satellites_visible
            num_sats2 = master.field('GPS2_RAW', 'satellites_visible', -1)
            if num_sats2 == -1:
                sats_string = "%u" % num_sats1
            else:
                sats_string = "%u/%u" % (num_sats1, num_sats2)
            if ((msg.fix_type == 3 and master.mavlink10()) or
                (msg.fix_type == 2 and not master.mavlink10())):
                self.console.set_status('GPS', 'GPS: OK (%s)' % sats_string, fg='green')
            else:
                self.console.set_status('GPS', 'GPS: %u (%s)' % (msg.fix_type, sats_string), fg='red')
            if master.mavlink10():
                gps_heading = int(self.mpstate.status.msgs['GPS_RAW_INT'].cog * 0.01)
            else:
                gps_heading = self.mpstate.status.msgs['GPS_RAW'].hdg
            self.console.set_status('Heading', 'Hdg %s/%u' % (master.field('VFR_HUD', 'heading', '-'), gps_heading))
        elif type == 'VFR_HUD':
            if master.mavlink10():
                alt = master.field('GPS_RAW_INT', 'alt', 0) / 1.0e3
            else:
                alt = master.field('GPS_RAW', 'alt', 0)
            if self.module('wp').wploader.count() > 0:
                wp = self.module('wp').wploader.wp(0)
                home_lat = wp.x
                home_lng = wp.y
            else:
                home_lat = master.field('HOME', 'lat') * 1.0e-7
                home_lng = master.field('HOME', 'lon') * 1.0e-7
            lat = master.field('GLOBAL_POSITION_INT', 'lat', 0) * 1.0e-7
            lng = master.field('GLOBAL_POSITION_INT', 'lon', 0) * 1.0e-7
            rel_alt = master.field('GLOBAL_POSITION_INT', 'relative_alt', 0) * 1.0e-3
            if self.settings.basealt != 0:
                agl_alt = self.settings.basealt - self.console.ElevationMap.GetElevation(lat, lng)
            else:
                agl_alt = self.console.ElevationMap.GetElevation(home_lat, home_lng) - self.console.ElevationMap.GetElevation(lat, lng)
            agl_alt += rel_alt
            self.console.set_status('AGL', 'AGL %u' % agl_alt)
            self.console.set_status('Alt', 'Alt %u' % rel_alt)
            self.console.set_status('AirSpeed', 'AirSpeed %u' % msg.airspeed)
            self.console.set_status('GPSSpeed', 'GPSSpeed %u' % msg.groundspeed)
            self.console.set_status('Thr', 'Thr %u' % msg.throttle)
            t = time.localtime(msg._timestamp)
            if msg.groundspeed > 3 and not self.in_air:
                self.in_air = True
                self.start_time = time.mktime(t)
            elif msg.groundspeed > 3 and self.in_air:
                self.total_time = time.mktime(t) - self.start_time
                self.console.set_status('FlightTime', 'FlightTime %u:%02u' % (int(self.total_time)/60, int(self.total_time)%60))
            elif msg.groundspeed < 3 and self.in_air:
                self.in_air = False
                self.total_time = time.mktime(t) - self.start_time
                self.console.set_status('FlightTime', 'FlightTime %u:%02u' % (int(self.total_time)/60, int(self.total_time)%60))
        elif type == 'ATTITUDE':
            self.console.set_status('Roll', 'Roll %u' % math.degrees(msg.roll))
            self.console.set_status('Pitch', 'Pitch %u' % math.degrees(msg.pitch))
        elif type in ['SYS_STATUS']:
            sensors = { 'AS'  : mavutil.mavlink.MAV_SYS_STATUS_SENSOR_DIFFERENTIAL_PRESSURE,
                        'MAG' : mavutil.mavlink.MAV_SYS_STATUS_SENSOR_3D_MAG,
                        'INS' : mavutil.mavlink.MAV_SYS_STATUS_SENSOR_3D_ACCEL | mavutil.mavlink.MAV_SYS_STATUS_SENSOR_3D_GYRO,
                        'AHRS' : mavutil.mavlink.MAV_SYS_STATUS_AHRS}
            for s in sensors.keys():
                bits = sensors[s]
                present = ((msg.onboard_control_sensors_enabled & bits) == bits)
                healthy = ((msg.onboard_control_sensors_health & bits) == bits)
                if not present:
                    fg = 'grey'
                elif not healthy:
                    fg = 'red'
                else:
                    fg = 'green'
                self.console.set_status(s, s, fg=fg)
        elif type == 'HWSTATUS':
            if msg.Vcc >= 4600 and msg.Vcc <= 5300:
                fg = 'green'
            else:
                fg = 'red'
            self.console.set_status('Vcc', 'Vcc %.2f' % (msg.Vcc * 0.001), fg=fg)
        elif type == 'POWER_STATUS':
            if msg.flags & mavutil.mavlink.MAV_POWER_STATUS_CHANGED:
                fg = 'red'
            else:
                fg = 'green'
            status = 'PWR:'
            if msg.flags & mavutil.mavlink.MAV_POWER_STATUS_USB_CONNECTED:
                status += 'U'
            if msg.flags & mavutil.mavlink.MAV_POWER_STATUS_BRICK_VALID:
                status += 'B'
            if msg.flags & mavutil.mavlink.MAV_POWER_STATUS_SERVO_VALID:
                status += 'S'
            if msg.flags & mavutil.mavlink.MAV_POWER_STATUS_PERIPH_OVERCURRENT:
                status += 'O1'
            if msg.flags & mavutil.mavlink.MAV_POWER_STATUS_PERIPH_HIPOWER_OVERCURRENT:
                status += 'O2'
            self.console.set_status('PWR', status, fg=fg)
            self.console.set_status('Srv', 'Srv %.2f' % (msg.Vservo*0.001), fg='green')
        elif type in ['RADIO', 'RADIO_STATUS']:
            if msg.rssi < msg.noise+10 or msg.remrssi < msg.remnoise+10:
                fg = 'red'
            else:
                fg = 'black'
            self.console.set_status('Radio', 'Radio %u/%u %u/%u' % (msg.rssi, msg.noise, msg.remrssi, msg.remnoise), fg=fg)
        elif type == 'HEARTBEAT':
            self.console.set_status('Mode', '%s' % master.flightmode, fg='blue')
            for m in self.mpstate.mav_master:
                linkdelay = (self.mpstate.status.highest_msec - m.highest_msec)*1.0e-3
                linkline = "Link %u " % (m.linknum+1)
                if m.linkerror:
                    linkline += "down"
                    fg = 'red'
                else:
                    linkline += "OK (%u pkts, %.2fs delay, %u lost)" % (m.mav_count, linkdelay, m.mav_loss)
                    if linkdelay > 1:
                        fg = 'orange'
                    else:
                        fg = 'darkgreen'
                self.console.set_status('Link%u'%m.linknum, linkline, row=1, fg=fg)
        elif type in ['WAYPOINT_CURRENT', 'MISSION_CURRENT']:
            self.console.set_status('WP', 'WP %u' % msg.seq)
            lat = master.field('GLOBAL_POSITION_INT', 'lat', 0) * 1.0e-7
            lng = master.field('GLOBAL_POSITION_INT', 'lon', 0) * 1.0e-7
            if lat != 0 and lng != 0:
                airspeed = master.field('VFR_HUD', 'airspeed', 30)
                if abs(airspeed - self.speed) > 5:
                    self.speed = airspeed
                else:
                    self.speed = 0.98*self.speed + 0.02*airspeed
                self.speed = max(1, self.speed)
                time_remaining = int(self.estimated_time_remaining(lat, lng, msg.seq, self.speed))
                self.console.set_status('ETR', 'ETR %u:%02u' % (time_remaining/60, time_remaining%60))

        elif type == 'NAV_CONTROLLER_OUTPUT':
            self.console.set_status('WPDist', 'Distance %u' % msg.wp_dist)
            self.console.set_status('WPBearing', 'Bearing %u' % msg.target_bearing)
            if msg.alt_error > 0:
                alt_error_sign = "L"
            else:
                alt_error_sign = "H"
            if msg.aspd_error > 0:
                aspd_error_sign = "L"
            else:
                aspd_error_sign = "H"
            self.console.set_status('AltError', 'AltError %d%s' % (msg.alt_error, alt_error_sign))
            self.console.set_status('AspdError', 'AspdError %.1f%s' % (msg.aspd_error*0.01, aspd_error_sign))

def init(mpstate):
    '''initialise module'''
    return ConsoleModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_DGPS
#!/usr/bin/env python
'''
support for a GCS attached DGPS system
'''

import socket, errno
from pymavlink import mavutil
from MAVProxy.modules.lib import mp_module

class DGPSModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(DGPSModule, self).__init__(mpstate, "DGPS", "DGPS injection support")
        self.portnum = 13320
        self.port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.port.bind(("127.0.0.1", self.portnum))
        mavutil.set_close_on_exec(self.port.fileno())
        self.port.setblocking(0)

    def idle_task(self):
        '''called in idle time'''
        try:
            data = self.port.recv(200)
        except socket.error as e:
            if e.errno in [ errno.EAGAIN, errno.EWOULDBLOCK ]:
                return
            raise
        if len(data) > 110:
            print("DGPS data too large: %u bytes" % len(data))
            return
        self.master.mav.gps_inject_data_send(self.target_system,
                                                  self.target_component,
                                                  len(data), data)

def init(mpstate):
    '''initialise module'''
    return DGPSModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_fence
"""
    MAVProxy geofence module
"""
import os, time
from pymavlink import mavwp, mavutil
from MAVProxy.modules.lib import mp_util
from MAVProxy.modules.lib import mp_module
from MAVProxy.modules.lib.mp_menu import *

class FenceModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(FenceModule, self).__init__(mpstate, "fence", "geo-fence management", public = True)
        self.fenceloader = mavwp.MAVFenceLoader()
        self.last_fence_breach = 0
        self.last_fence_status = 0
        self.present = False
        self.enabled = False
        self.healthy = True
        self.add_command('fence', self.cmd_fence,
                         "geo-fence management",
                         ["<draw|list|clear|enable|disable|move|remove>",
                          "<load|save> (FILENAME)"])

        self.have_list = False

        if self.continue_mode and self.logdir != None:
            fencetxt = os.path.join(self.logdir, 'fence.txt')
            if os.path.exists(fencetxt):
                self.fenceloader.load(fencetxt)
                self.have_list = True
                print("Loaded fence from %s" % fencetxt)

        self.menu_added_console = False
        self.menu_added_map = False
        self.menu = MPMenuSubMenu('Fence',
                                  items=[MPMenuItem('Clear', 'Clear', '# fence clear'),
                                         MPMenuItem('List', 'List', '# fence list'),
                                         MPMenuItem('Load', 'Load', '# fence load ',
                                                    handler=MPMenuCallFileDialog(flags=wx.FD_OPEN,
                                                                                 title='Fence Load',
                                                                                 wildcard='*.fen')),
                                         MPMenuItem('Save', 'Save', '# fence save ',
                                                    handler=MPMenuCallFileDialog(flags=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT,
                                                                                 title='Fence Save',
                                                                                 wildcard='*.fen')),
                                         MPMenuItem('Draw', 'Draw', '# fence draw')])

    def idle_task(self):
        '''called on idle'''
        if not self.menu_added_console and self.module('console') is not None:
            self.menu_added_console = True
            self.module('console').add_menu(self.menu)
        if not self.menu_added_map and self.module('map') is not None:
            self.menu_added_map = True
            self.module('map').add_menu(self.menu)

    def mavlink_packet(self, m):
        '''handle and incoming mavlink packet'''
        if m.get_type() == "FENCE_STATUS":
            self.last_fence_breach = m.breach_time
            self.last_fence_status = m.breach_status
        elif m.get_type() in ['SYS_STATUS']:
            bits = mavutil.mavlink.MAV_SYS_STATUS_GEOFENCE

            present = ((m.onboard_control_sensors_present & bits) == bits)
            if self.present == False and present == True:
                self.say("fence present")
            elif self.present == True and present == False:
                self.say("fence removed")
            self.present = present

            enabled = ((m.onboard_control_sensors_enabled & bits) == bits)
            if self.enabled == False and enabled == True:
                self.say("fence enabled")
            elif self.enabled == True and enabled == False:
                self.say("fence disabled")
            self.enabled = enabled

            healthy = ((m.onboard_control_sensors_health & bits) == bits)
            if self.healthy == False and healthy == True:
                self.say("fence OK")
            elif self.healthy == True and healthy == False:
                self.say("fence breach")
            self.healthy = healthy

            #console output for fence:
            if self.enabled == False:
                self.console.set_status('Fence', 'FEN', row=0, fg='grey')
            elif self.enabled == True and self.healthy == True:
                self.console.set_status('Fence', 'FEN', row=0, fg='green')
            elif self.enabled == True and self.healthy == False:
                self.console.set_status('Fence', 'FEN', row=0, fg='red')

    def set_fence_enabled(self, do_enable):
        '''Enable or disable fence'''
        self.master.mav.command_long_send(
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_CMD_DO_FENCE_ENABLE, 0,
            do_enable, 0, 0, 0, 0, 0, 0)

    def cmd_fence_move(self, args):
        '''handle fencepoint move'''
        if len(args) < 1:
            print("Usage: fence move FENCEPOINTNUM")
            return
        if not self.have_list:
            print("Please list fence points first")
            return

        idx = int(args[0])
        if idx <= 0 or idx > self.fenceloader.count():
            print("Invalid fence point number %u" % idx)
            return

        try:
            latlon = self.module('map').click_position
        except Exception:
            print("No map available")
            return
        if latlon is None:
            print("No map click position available")
            return

        # note we don't subtract 1, as first fence point is the return point
        self.fenceloader.move(idx, latlon[0], latlon[1])
        if self.send_fence():
            print("Moved fence point %u" % idx)

    def cmd_fence_remove(self, args):
        '''handle fencepoint remove'''
        if len(args) < 1:
            print("Usage: fence remove FENCEPOINTNUM")
            return
        if not self.have_list:
            print("Please list fence points first")
            return

        idx = int(args[0])
        if idx <= 0 or idx > self.fenceloader.count():
            print("Invalid fence point number %u" % idx)
            return

        # note we don't subtract 1, as first fence point is the return point
        self.fenceloader.remove(idx)
        if self.send_fence():
            print("Removed fence point %u" % idx)
        else:
            print("Failed to remove fence point %u" % idx)

    def cmd_fence(self, args):
        '''fence commands'''
        if len(args) < 1:
            self.print_usage()
            return

        if args[0] == "enable":
            self.set_fence_enabled(1)
        elif args[0] == "disable":
            self.set_fence_enabled(0)
        elif args[0] == "load":
            if len(args) != 2:
                print("usage: fence load <filename>")
                return
            self.load_fence(args[1])
        elif args[0] == "list":
            self.list_fence(None)
        elif args[0] == "move":
            self.cmd_fence_move(args[1:])
        elif args[0] == "remove":
            self.cmd_fence_remove(args[1:])
        elif args[0] == "save":
            if len(args) != 2:
                print("usage: fence save <filename>")
                return
            self.list_fence(args[1])
        elif args[0] == "show":
            if len(args) != 2:
                print("usage: fence show <filename>")
                return
            self.fenceloader.load(args[1])
            self.have_list = True
        elif args[0] == "draw":
            if not 'draw_lines' in self.mpstate.map_functions:
                print("No map drawing available")
                return
            self.mpstate.map_functions['draw_lines'](self.fence_draw_callback)
            print("Drawing fence on map")
        elif args[0] == "clear":
            self.param_set('FENCE_TOTAL', 0, 3)
        else:
            self.print_usage()

    def load_fence(self, filename):
        '''load fence points from a file'''
        try:
            self.fenceloader.target_system = self.target_system
            self.fenceloader.target_component = self.target_component
            self.fenceloader.load(filename)
        except Exception as msg:
            print("Unable to load %s - %s" % (filename, msg))
            return
        print("Loaded %u geo-fence points from %s" % (self.fenceloader.count(), filename))
        self.send_fence()

    def send_fence(self):
        '''send fence points from fenceloader'''
        # must disable geo-fencing when loading
        self.fenceloader.target_system = self.target_system
        self.fenceloader.target_component = self.target_component
        self.fenceloader.reindex()
        action = self.get_mav_param('FENCE_ACTION', mavutil.mavlink.FENCE_ACTION_NONE)
        self.param_set('FENCE_ACTION', mavutil.mavlink.FENCE_ACTION_NONE, 3)
        self.param_set('FENCE_TOTAL', self.fenceloader.count(), 3)
        for i in range(self.fenceloader.count()):
            p = self.fenceloader.point(i)
            self.master.mav.send(p)
            p2 = self.fetch_fence_point(i)
            if p2 is None:
                self.param_set('FENCE_ACTION', action, 3)
                return False
            if (p.idx != p2.idx or
                abs(p.lat - p2.lat) >= 0.00003 or
                abs(p.lng - p2.lng) >= 0.00003):
                print("Failed to send fence point %u" % i)
                self.param_set('FENCE_ACTION', action, 3)
                return False
        self.param_set('FENCE_ACTION', action, 3)
        return True

    def fetch_fence_point(self ,i):
        '''fetch one fence point'''
        self.master.mav.fence_fetch_point_send(self.target_system,
                                                    self.target_component, i)
        tstart = time.time()
        p = None
        while time.time() - tstart < 1:
            p = self.master.recv_match(type='FENCE_POINT', blocking=False)
            if p is not None:
                break
            time.sleep(0.1)
            continue
        if p is None:
            self.console.error("Failed to fetch point %u" % i)
            return None
        return p

    def fence_draw_callback(self, points):
        '''callback from drawing a fence'''
        self.fenceloader.clear()
        if len(points) < 3:
            return
        self.fenceloader.target_system = self.target_system
        self.fenceloader.target_component = self.target_component
        bounds = mp_util.polygon_bounds(points)
        (lat, lon, width, height) = bounds
        center = (lat+width/2, lon+height/2)
        self.fenceloader.add_latlon(center[0], center[1])
        for p in points:
            self.fenceloader.add_latlon(p[0], p[1])
        # close it
        self.fenceloader.add_latlon(points[0][0], points[0][1])
        self.send_fence()
        self.have_list = True

    def list_fence(self, filename):
        '''list fence points, optionally saving to a file'''
        self.fenceloader.clear()
        count = self.get_mav_param('FENCE_TOTAL', 0)
        if count == 0:
            print("No geo-fence points")
            return
        for i in range(int(count)):
            p = self.fetch_fence_point(i)
            if p is None:
                return
            self.fenceloader.add(p)

        if filename is not None:
            try:
                self.fenceloader.save(filename)
            except Exception as msg:
                print("Unable to save %s - %s" % (filename, msg))
                return
            print("Saved %u geo-fence points to %s" % (self.fenceloader.count(), filename))
        else:
            for i in range(self.fenceloader.count()):
                p = self.fenceloader.point(i)
                self.console.writeln("lat=%f lng=%f" % (p.lat, p.lng))
        if self.status.logdir != None:
            fencetxt = os.path.join(self.status.logdir, 'fence.txt')
            self.fenceloader.save(fencetxt)
            print("Saved fence to %s" % fencetxt)
        self.have_list = True

    def print_usage(self):
        print("usage: fence <enable|disable|list|load|save|clear|draw|move|remove>")

def init(mpstate):
    '''initialise module'''
    return FenceModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_graph
"""
  MAVProxy realtime graphing module

  uses lib/live_graph.py for display
"""

from pymavlink import mavutil
import re, os, sys

from MAVProxy.modules.lib import live_graph

from MAVProxy.modules.lib import mp_module

class GraphModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(GraphModule, self).__init__(mpstate, "graph", "graph control")
        self.timespan = 20
        self.tickresolution = 0.2
        self.graphs = []
        self.add_command('graph', self.cmd_graph, "[expression...] add a live graph",
                         ['(VARIABLE) (VARIABLE) (VARIABLE) (VARIABLE) (VARIABLE) (VARIABLE)'])

    def cmd_graph(self, args):
        '''graph command'''
        if len(args) == 0:
            # list current graphs
            for i in range(len(self.graphs)):
                print("Graph %u: %s" % (i, self.graphs[i].fields))
            return

        elif args[0] == "help":
            print("graph <timespan|tickresolution|expression>")
        elif args[0] == "timespan":
            if len(args) == 1:
                print("timespan: %.1f" % self.timespan)
                return
            self.timespan = float(args[1])
        elif args[0] == "tickresolution":
            if len(args) == 1:
                print("tickresolution: %.1f" % self.tickresolution)
                return
            self.tickresolution = float(args[1])
        else:
            # start a new graph
            self.graphs.append(Graph(self, args[:]))

    def unload(self):
        '''unload module'''
        for g in self.graphs:
            g.close()
        self.graphs = []

    def mavlink_packet(self, msg):
        '''handle an incoming mavlink packet'''

        # check for any closed graphs
        for i in range(len(self.graphs) - 1, -1, -1):
            if not self.graphs[i].is_alive():
                self.graphs[i].close()
                self.graphs.pop(i)

        # add data to the rest
        for g in self.graphs:
            g.add_mavlink_packet(msg)


def init(mpstate):
    '''initialise module'''
    return GraphModule(mpstate)

class Graph():
    '''a graph instance'''
    def __init__(self, state, fields):
        self.fields = fields[:]
        self.field_types = []
        self.msg_types = set()
        self.state = state

        re_caps = re.compile('[A-Z_][A-Z0-9_]+')
        for f in self.fields:
            caps = set(re.findall(re_caps, f))
            self.msg_types = self.msg_types.union(caps)
            self.field_types.append(caps)
        print("Adding graph: %s" % self.fields)

        self.values = [None] * len(self.fields)
        self.livegraph = live_graph.LiveGraph(self.fields,
                                              timespan=state.timespan,
                                              tickresolution=state.tickresolution,
                                              title=self.fields[0])

    def is_alive(self):
        '''check if this graph is still alive'''
        if self.livegraph:
            return self.livegraph.is_alive()
        return False

    def close(self):
        '''close this graph'''
        if self.livegraph:
            self.livegraph.close()
        self.livegraph = None

    def add_mavlink_packet(self, msg):
        '''add data to the graph'''
        mtype = msg.get_type()
        if mtype not in self.msg_types:
            return
        for i in range(len(self.fields)):
            if mtype not in self.field_types[i]:
                continue
            f = self.fields[i]
            self.values[i] = mavutil.evaluate_expression(f, self.state.master.messages)
        if self.livegraph is not None:
            self.livegraph.add_values(self.values)

########NEW FILE########
__FILENAME__ = mavproxy_HIL
#!/usr/bin/env python
'''
HIL module
Andrew Tridgell
December 2012

This interfaces to Tools/autotest/jsbsim/runsim.py to run the JSBSim flight simulator
'''

import sys, os, time, socket, errno, struct, math
from math import degrees, radians
from MAVProxy.modules.lib import mp_module

class HILModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(HILModule, self).__init__(mpstate, "HIL", "rally point control")
        self.last_sim_send_time = time.time()
        self.last_apm_send_time = time.time()
        self.rc_channels_scaled = None
        self.hil_state_msg = None
        sim_in_address  = ('127.0.0.1', 5501)
        sim_out_address  = ('127.0.0.1', 5502)

        self.sim_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sim_in.bind(sim_in_address)
        self.sim_in.setblocking(0)

        self.sim_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sim_out.connect(sim_out_address)
        self.sim_out.setblocking(0)

    def unload(self):
        '''unload module'''
        self.sim_in.close()
        self.sim_out.close()

    def mavlink_packet(self, m):
        '''handle an incoming mavlink packet'''
        if m.get_type() == 'RC_CHANNELS_SCALED':
            self.rc_channels_scaled = m

    def idle_task(self):
        '''called from main loop'''
        self.check_sim_in()
        self.check_sim_out()
        self.check_apm_out()

    def check_sim_in(self):
        '''check for FDM packets from runsim'''
        try:
            pkt = self.sim_in.recv(17*8 + 4)
        except socket.error as e:
            if not e.errno in [ errno.EAGAIN, errno.EWOULDBLOCK ]:
                raise
            return
        if len(pkt) != 17*8 + 4:
            # wrong size, discard it
            print("wrong size %u" % len(pkt))
            return
        (latitude, longitude, altitude, heading, v_north, v_east, v_down,
         ax, ay, az,
         phidot, thetadot, psidot,
         roll, pitch, yaw,
         vcas, check) = struct.unpack('<17dI', pkt)
        (p, q, r) = self.convert_body_frame(radians(roll), radians(pitch), radians(phidot), radians(thetadot), radians(psidot))

        try:
            self.hil_state_msg = self.master.mav.hil_state_encode(int(time.time()*1e6),
                                                                        radians(roll),
                                                                        radians(pitch),
                                                                        radians(yaw),
                                                                        p,
                                                                        q,
                                                                        r,
                                                                        int(latitude*1.0e7),
                                                                        int(longitude*1.0e7),
                                                                        int(altitude*1.0e3),
                                                                        int(v_north*100),
                                                                        int(v_east*100),
                                                                        0,
                                                                        int(ax*1000/9.81),
                                                                        int(ay*1000/9.81),
                                                                        int(az*1000/9.81))
        except Exception:
            return




    def check_sim_out(self):
        '''check if we should send new servos to flightgear'''
        now = time.time()
        if now - self.last_sim_send_time < 0.02 or self.rc_channels_scaled is None:
            return
        self.last_sim_send_time = now

        servos = []
        for ch in range(1,9):
            servos.append(self.scale_channel(ch, getattr(self.rc_channels_scaled, 'chan%u_scaled' % ch)))
        servos.extend([0,0,0, 0,0,0])
        buf = struct.pack('<14H', *servos)
        try:
            self.sim_out.send(buf)
        except socket.error as e:
            if not e.errno in [ errno.ECONNREFUSED ]:
                raise
            return


    def check_apm_out(self):
        '''check if we should send new data to the APM'''
        now = time.time()
        if now - self.last_apm_send_time < 0.02:
            return
        self.last_apm_send_time = now
        if self.hil_state_msg is not None:
            self.master.mav.send(self.hil_state_msg)

    def convert_body_frame(self, phi, theta, phiDot, thetaDot, psiDot):
        '''convert a set of roll rates from earth frame to body frame'''
        p = phiDot - psiDot*math.sin(theta)
        q = math.cos(phi)*thetaDot + math.sin(phi)*psiDot*math.cos(theta)
        r = math.cos(phi)*psiDot*math.cos(theta) - math.sin(phi)*thetaDot
        return (p, q, r)

    def scale_channel(self, ch, value):
        '''scale a channel to 1000/1500/2000'''
        v = value/10000.0
        if v < -1:
            v = -1
        elif v > 1:
            v = 1
        if ch == 3 and self.mpstate.vehicle_type != 'rover':
            if v < 0:
                v = 0
            return int(1000 + v*1000)
        return int(1500 + v*500)

def init(mpstate):
    '''initialise module'''
    return HILModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_joystick
#!/usr/bin/env python
'''joystick interface module

Contributed by AndrewF:
  http://diydrones.com/profile/AndrewF

'''

import pygame, fnmatch
from time import sleep

mpstate = None

from MAVProxy.modules.lib import mp_module


'''
A map of joystick identifiers to channels and scalings.
Each joystick type can control 8 channels, each channel is defined
by its axis number, the multiplier and the additive offset
'''
joymap = {
    'CarolBox USB*':
    # http://www.hobbyking.com/hobbyking/store/__13597__USB_Simulator_Cable_XTR_AeroFly_FMS.html
    # has 6 usable axes. This assumes mode 1
    [(3, 500, 1500),
     (0, 500, 1500),
     (1, 700, 1500),
     (4, 500, 1500),
     (5, 500, 1500),
     None,
     (2, 500, 1500),
     (5, 500, 1500)],

    'Sony PLAYSTATION(R)3 Controller':
    # only 4 axes usable. This assumes mode 1
    [(2, 500,  1500),
     (1, -500,  1500),
     (3, -500, 1000),
     (0, -500,  1500)],

    'GREAT PLANES InterLink Elite':
    # 4 axes usable
    [(0, 500,  1500),
     (1, -500,  1500),
     (2, -1000, 1500),
     (4, -500,  1500),
     None,
     None,
     None,
     (3, 500,  1500)],

    'Great Planes GP Controller':
    # 4 axes usable
    [(0, 500,  1500),
     (1, -500,  1500),
     (2, -1000, 1500),
     (4, -500,  1500),
     None,
     None,
     None,
     (3, 500,  1500)]
}


class JSModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(JSModule, self).__init__(mpstate, "joystick", "joystick aircraft control")
        self.js = None

        #initialize joystick, if available
        pygame.init()
        pygame.joystick.init() # main joystick device system

        for i in range(pygame.joystick.get_count()):
            print("Trying joystick %u" % i)
            try:
                j = pygame.joystick.Joystick(i)
                j.init() # init instance
                name = j.get_name()
                print('joystick found: ' + name)
                for jtype in joymap:
                    if fnmatch.fnmatch(name, jtype):
                        print("Matched type '%s'" % jtype)
                        print '%u axes available' % j.get_numaxes()
                        self.js = j
                        self.num_axes = j.get_numaxes()
                        self.map = joymap[jtype]
                        break
            except pygame.error:
                continue

    def idle_task(self):
        '''called in idle time'''
        if self.js is None:
            return
        for e in pygame.event.get(): # iterate over event stack
            #the following is somewhat custom for the specific joystick model:
            override = self.module('rc').override[:]
            for i in range(len(self.map)):
                m = self.map[i]
                if m is None:
                    continue
                (axis, mul, add) = m
                if axis >= self.num_axes:
                    continue
                v = int(self.js.get_axis(axis)*mul + add)
                v = max(min(v, 2000), 1000)
                override[i] = v
            if override != self.module('rc').override:
                self.module('rc').override = override
                self.module('rc').override_period.force()

def init(mpstate):
    '''initialise module'''
    return JSModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_log
#!/usr/bin/env python
'''log command handling'''

import time, os

from MAVProxy.modules.lib import mp_module

class LogModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(LogModule, self).__init__(mpstate, "log", "log transfer")
        self.add_command('log', self.cmd_log, "log file handling", ['<download|status|erase|resume|cancel|list>'])
        self.reset()

    def reset(self):
        self.download_set = set()
        self.download_file = None
        self.download_lognum = None
        self.download_filename = None
        self.download_start = None
        self.download_last_timestamp = None
        self.download_ofs = 0
        self.retries = 0
        self.entries = {}

    def mavlink_packet(self, m):
        '''handle an incoming mavlink packet'''
        if m.get_type() == 'LOG_ENTRY':
            self.handle_log_entry(m)
        elif m.get_type() == 'LOG_DATA':
            self.handle_log_data(m)

    def handle_log_entry(self, m):
        '''handling incoming log entry'''
        if m.time_utc == 0:
            tstring = ''
        else:
            tstring = time.ctime(m.time_utc)
        self.entries[m.id] = m
        print("Log %u  numLogs %u lastLog %u size %u %s" % (m.id, m.num_logs, m.last_log_num, m.size, tstring))


    def handle_log_data(self, m):
        '''handling incoming log data'''
        if self.download_file is None:
            return
        # lose some data
        # import random
        # if random.uniform(0,1) < 0.05:
        #    print('dropping ', str(m))
        #    return
        if m.ofs != self.download_ofs:
            self.download_file.seek(m.ofs)
            self.download_ofs = m.ofs
        if m.count != 0:
            data = m.data[:m.count]
            s = ''.join(str(chr(x)) for x in data)
            self.download_file.write(s)
            self.download_set.add(m.ofs // 90)
            self.download_ofs += m.count
        self.download_last_timestamp = time.time()
        if m.count == 0 or (m.count < 90 and len(self.download_set) == 1 + (m.ofs // 90)):
            dt = time.time() - self.download_start
            self.download_file.close()
            size = os.path.getsize(self.download_filename)
            speed = size / (1000.0 * dt)
            print("Finished downloading %s (%u bytes %u seconds, %.1f kbyte/sec %u retries)" % (
                self.download_filename,
                size,
                dt, speed,
                self.retries))
            self.download_file = None
            self.download_filename = None
            self.download_set = set()

    def handle_log_data_missing(self):
        '''handling missing incoming log data'''
        if len(self.download_set) == 0:
            return
        highest = max(self.download_set)
        diff = set(range(highest)).difference(self.download_set)
        if len(diff) == 0:
            self.master.mav.log_request_data_send(self.target_system,
                                                       self.target_component,
                                                       self.download_lognum, (1 + highest) * 90, 0xffffffff)
            self.retries += 1
        else:
            num_requests = 0
            while num_requests < 20:
                start = min(diff)
                diff.remove(start)
                end = start
                while end + 1 in diff:
                    end += 1
                    diff.remove(end)
                self.master.mav.log_request_data_send(self.target_system,
                                                           self.target_component,
                                                           self.download_lognum, start * 90, (end + 1 - start) * 90)
                num_requests += 1
                self.retries += 1
                if len(diff) == 0:
                    break


    def log_status(self):
        '''show download status'''
        if self.download_filename is None:
            print("No download")
            return
        dt = time.time() - self.download_start
        speed = os.path.getsize(self.download_filename) / (1000.0 * dt)
        m = self.entries.get(self.download_lognum, None)
        if m is None:
            size = 0
        else:
            size = m.size
        print("Downloading %s - %u/%u bytes %.1f kbyte/s (%u retries)" % (self.download_filename,
                                                                          os.path.getsize(self.download_filename),
                                                                          size,
                                                                          speed,
                                                                          self.retries))

    def log_download(self, log_num, filename):
        '''download a log file'''
        print("Downloading log %u as %s" % (log_num, filename))
        self.download_lognum = log_num
        self.download_file = open(filename, "wb")
        self.master.mav.log_request_data_send(self.target_system,
                                                   self.target_component,
                                                   log_num, 0, 0xFFFFFFFF)
        self.download_filename = filename
        self.download_set = set()
        self.download_start = time.time()
        self.download_last_timestamp = time.time()
        self.download_ofs = 0
        self.retries = 0

    def cmd_log(self, args):
        '''log commands'''
        if len(args) < 1:
            print("usage: log <list|download|erase|resume|status|cancel>")
            return

        if args[0] == "status":
            self.log_status()
        if args[0] == "list":
            print("Requesting log list")
            self.download_set = set()
            self.master.mav.log_request_list_send(self.target_system,
                                                       self.target_component,
                                                       0, 0xffff)

        elif args[0] == "erase":
            self.master.mav.log_erase_send(self.target_system,
                                                self.target_component)

        elif args[0] == "resume":
            self.master.mav.log_request_end_send(self.target_system,
                                                      self.target_component)

        elif args[0] == "cancel":
            if self.download_file is not None:
                self.download_file.close()
            self.reset()

        elif args[0] == "download":
            if len(args) < 2:
                print("usage: log download <lognumber> <filename>")
                return
            if args[1] == 'latest':
                if len(self.entries.keys()) == 0:
                    print("Please use log list first")
                    return
                log_num = sorted(self.entries, key=lambda id: self.entries[id].time_utc)[-1]
            else:
                log_num = int(args[1])
            if len(args) > 2:
                filename = args[2]
            else:
                filename = "log%u.bin" % log_num
            self.log_download(log_num, filename)

    def idle_task(self):
        '''handle missing log data'''
        if self.download_last_timestamp is not None and time.time() - self.download_last_timestamp > 0.7:
            self.download_last_timestamp = time.time()
            self.handle_log_data_missing()

def init(mpstate):
    '''initialise module'''
    return LogModule(mpstate)

########NEW FILE########
__FILENAME__ = GAreader
#!/usr/bin/env python
'''
Module to read DTM files published by Geoscience Australia
Written by Stephen Dade (stephen_dade@hotmail.com
'''

import os
import sys

import numpy


class ERMap:
    '''Class to read GA files'''
    def __init__(self):
        self.header = None
        self.data = None
        self.startlongitude = 0
        self.startlatitude = 0
        self.endlongitude = 0
        self.endlatitude = 0
        self.deltalongitude = 0
        self.deltalatitude = 0

    def read_ermapper(self, ifile):
        '''Read in a DEM file and associated .ers file'''
        ers_index = ifile.find('.ers')
        if ers_index > 0:
            data_file = ifile[0:ers_index]
            header_file = ifile
        else:
            data_file = ifile
            header_file = ifile + '.ers'
        
        self.header = self.read_ermapper_header(header_file)

        nroflines = int(self.header['nroflines'])
        nrofcellsperlines = int(self.header['nrofcellsperline'])
        self.data = self.read_ermapper_data(data_file, offset=int(self.header['headeroffset']))
        self.data = numpy.reshape(self.data,(nroflines,nrofcellsperlines))

        longy =  numpy.fromstring(self.getHeaderParam('longitude'), sep=':')
        latty =  numpy.fromstring(self.getHeaderParam('latitude'), sep=':')

        self.deltalatitude = float(self.header['ydimension'])
        self.deltalongitude = float(self.header['xdimension'])

        if longy[0] < 0:
            self.startlongitude = longy[0]+-((longy[1]/60)+(longy[2]/3600))
            self.endlongitude = self.startlongitude - int(self.header['nrofcellsperline'])*self.deltalongitude
        else:
            self.startlongitude = longy[0]+(longy[1]/60)+(longy[2]/3600)
            self.endlongitude = self.startlongitude + int(self.header['nrofcellsperline'])*self.deltalongitude
        if latty[0] < 0:
            self.startlatitude = latty[0]-((latty[1]/60)+(latty[2]/3600))
            self.endlatitude = self.startlatitude - int(self.header['nroflines'])*self.deltalatitude
        else:
            self.startlatitude = latty[0]+(latty[1]/60)+(latty[2]/3600)
            self.endlatitude = self.startlatitude + int(self.header['nroflines'])*self.deltalatitude

    def read_ermapper_header(self, ifile):
        # function for reading an ERMapper header from file
        header = {}

        fid = open(ifile,'rt')
        header_string = fid.readlines()
        fid.close()

        for line in header_string:
            if line.find('=') > 0:
                tmp_string = line.strip().split('=')
                header[tmp_string[0].strip().lower()]= tmp_string[1].strip()

        return header                      

    def read_ermapper_data(self, ifile, data_format = numpy.float32, offset=0):
        # open input file in a binary format and read the input string
        fid = open(ifile,'rb')
        if offset != 0:
            fid.seek(offset)
        input_string = fid.read()
        fid.close()

        # convert input string to required format (Note default format is numpy.float32)
        grid_as_float = numpy.fromstring(input_string,data_format)
        return grid_as_float

    def getHeaderParam(self, key):
         '''Find a parameter in the associated .ers file'''
         return self.header[key]

    def printBoundingBox(self):
        '''Print the bounding box that this DEM covers'''
        print "Bounding Latitude: "
        print self.startlatitude
        print self.endlatitude

        print "Bounding Longitude: "
        print self.startlongitude
        print self.endlongitude

    def getPercentBlank(self):
        '''Print how many null cells are in the DEM - Quality measure'''
        blank = 0
        nonblank = 0
        for x in self.data.flat:
            if x == -99999.0:
                blank = blank + 1
            else:
                nonblank = nonblank + 1

        print "Blank tiles =  ", blank, "out of ", (nonblank+blank)

    def getAltitudeAtPoint(self, latty, longy):
        '''Return the altitude at a particular long/lat'''
        #check the bounds
        if self.startlongitude > 0 and (longy < self.startlongitude or longy > self.endlongitude):
            return -1
        if self.startlongitude < 0 and (longy > self.startlongitude or longy < self.endlongitude):
            return -1
        if self.startlatitude > 0 and (latty < self.startlatitude or longy > self.endlatitude):
            return -1
        if self.startlatitude < 0 and (latty > self.startlatitude or longy < self.endlatitude):
            return -1

        x = numpy.abs((latty - self.startlatitude)/self.deltalatitude)
        y = numpy.abs((longy - self.startlongitude)/self.deltalongitude)

        #do some interpolation
        # print "x,y", x, y
        x_int = int(x)
        x_frac = x - int(x)
        y_int = int(y)
        y_frac = y - int(y)
        #print "frac", x_int, x_frac, y_int, y_frac
        value00 = self.data[x_int, y_int]
        value10 = self.data[x_int+1, y_int]
        value01 = self.data[x_int, y_int+1]
        value11 = self.data[x_int+1, y_int+1]
        #print "values ", value00, value10, value01, value11

        #check for null values
        if value00 == -99999:
            value00 = 0
        if value10 == -99999:
            value10 = 0
        if value01 == -99999:
            value01 = 0
        if value11 == -99999:
            value11 = 0

        value1 = self._avg(value00, value10, x_frac)
        value2 = self._avg(value01, value11, x_frac)
        value  = self._avg(value1,  value2, y_frac)

        return value

    @staticmethod
    def _avg(value1, value2, weight):
        """Returns the weighted average of two values and handles the case where
            one value is None. If both values are None, None is returned.
        """
        if value1 is None:
            return value2
        if value2 is None:
            return value1
        return value2 * weight + value1 * (1 - weight)



if __name__ == '__main__':

    print "./Canberra/GSNSW_P756demg"
    mappy = ERMap()
    mappy.read_ermapper(os.path.join(os.environ['HOME'], './Documents/Elevation/Canberra/GSNSW_P756demg'))

    #print some header data   
    mappy.printBoundingBox()

    #get a measure of data quality
    #mappy.getPercentBlank()

    #test the altitude (around Canberra):
    alt = mappy.getAltitudeAtPoint(-35.274411, 149.097504)
    print "Alt at (-35.274411, 149.097504) is 807m (Google) or " + str(alt)
    alt = mappy.getAltitudeAtPoint(-35.239648, 149.126118)
    print "Alt at (-35.239648, 149.126118) is 577m (Google) or " + str(alt)
    alt = mappy.getAltitudeAtPoint(-35.362751, 149.165361)
    print "Alt at (-35.362751, 149.165361) is 584m (Google) or " + str(alt)
    alt = mappy.getAltitudeAtPoint(-35.306992, 149.194274)
    print "Alt at (-35.306992, 149.194274) is 570m (Google) or " + str(alt)
    alt = mappy.getAltitudeAtPoint(-35.261612, 149.542091)
    print "Alt at (-35.261612, 149.542091) is 766m (Google) or " + str(alt)
    alt = mappy.getAltitudeAtPoint(-35.052544, 149.509165)
    print "Alt at (-35.052544, 149.509165) is 700m (Google) or " + str(alt)
    alt = mappy.getAltitudeAtPoint(-35.045126, 149.257482)
    print "Alt at (-35.045126, 149.257482) is 577m (Google) or " + str(alt)
    alt = mappy.getAltitudeAtPoint(-35.564044, 149.177657)
    print "Alt at (-35.564044, 149.177657) is 1113m (Google) or " + str(alt)





########NEW FILE########
__FILENAME__ = mp_elevation
#!/usr/bin/python
'''
Wrapper for the SRTM module (srtm.py)
It will grab the altitude of a long,lat pair from the SRTM database
Created by Stephen Dade (stephen_dade@hotmail.com)
'''

import os
import sys
import time

import numpy

from MAVProxy.modules.mavproxy_map import GAreader
from MAVProxy.modules.mavproxy_map import srtm


class ElevationModel():
    '''Elevation Model. Only SRTM for now'''

    def __init__(self, database='srtm', offline=0):
        '''Use offline=1 to disable any downloading of tiles, regardless of whether the
        tile exists'''
        self.database = database
        if self.database == 'srtm':
            self.downloader = srtm.SRTMDownloader(offline=offline)
            self.downloader.loadFileList()
            self.tileDict = dict()

        '''Use the Geoscience Australia database instead - watch for the correct database path'''
        if self.database == 'geoscience':
            self.mappy = GAreader.ERMap()
            self.mappy.read_ermapper(os.path.join(os.environ['HOME'], './Documents/Elevation/Canberra/GSNSW_P756demg'))

    def GetElevation(self, latitude, longitude):
        '''Returns the altitude (m ASL) of a given lat/long pair'''
        if latitude == 0 or longitude == 0:
            return 0
        if self.database == 'srtm':
            TileID = (numpy.floor(latitude), numpy.floor(longitude))
            if TileID in self.tileDict:
                alt = self.tileDict[TileID].getAltitudeFromLatLon(latitude, longitude)
            else:
                tile = self.downloader.getTile(numpy.floor(latitude), numpy.floor(longitude))
                if tile == 0:
                    return -1
                self.tileDict[TileID] = tile
                alt = tile.getAltitudeFromLatLon(latitude, longitude)
        if self.database == 'geoscience':
             alt = self.mappy.getAltitudeAtPoint(latitude, longitude)
        return alt


if __name__ == "__main__":

    from optparse import OptionParser
    parser = OptionParser("mp_elevation.py [options]")
    parser.add_option("--lat", type='float', default=-35.052544, help="start latitude")
    parser.add_option("--lon", type='float', default=149.509165, help="start longitude")
    parser.add_option("--database", type='string', default='srtm', help="elevation database")

    (opts, args) = parser.parse_args()

    EleModel = ElevationModel(opts.database)

    lat = opts.lat
    lon = opts.lon

    '''Do a few lat/long pairs to demonstrate the caching
    Note the +0.000001 to the time. On faster PC's, the two time periods
    may in fact be equal, so we add a little extra time on the end to account for this'''
    t0 = time.time()
    alt = EleModel.GetElevation(lat, lon)
    t1 = time.time()+.000001
    print("Altitude at (%.6f, %.6f) is %u m. Pulled at %.1f FPS" % (lat, lon, alt, 1/(t1-t0)))

    lat = opts.lat+0.001
    lon = opts.lon+0.001
    t0 = time.time()
    alt = EleModel.GetElevation(lat, lon)
    t1 = time.time()+.000001
    print("Altitude at (%.6f, %.6f) is %u m. Pulled at %.1f FPS" % (lat, lon, alt, 1/(t1-t0)))

    lat = opts.lat-0.001
    lon = opts.lon-0.001
    t0 = time.time()
    alt = EleModel.GetElevation(lat, lon)
    t1 = time.time()+.000001
    print("Altitude at (%.6f, %.6f) is %u m. Pulled at %.1f FPS" % (lat, lon, alt, 1/(t1-t0)))




########NEW FILE########
__FILENAME__ = mp_slipmap
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
slipmap based on mp_tile
Andrew Tridgell
June 2012
'''

import functools
import math
import os, sys
import time

try:
    import cv2.cv as cv
except ImportError:
    import cv

from MAVProxy.modules.mavproxy_map import mp_elevation
from MAVProxy.modules.mavproxy_map import mp_tile
from MAVProxy.modules.lib import mp_util
from MAVProxy.modules.lib.mp_menu import *
from MAVProxy.modules.lib import mp_widgets


class SlipObject:
    '''an object to display on the map'''
    def __init__(self, key, layer, popup_menu=None):
        self.key = key
        self.layer = layer
        self.latlon = None
        self.popup_menu = popup_menu

    def clip(self, px, py, w, h, img):
        '''clip an area for display on the map'''
        sx = 0
        sy = 0

        if px < 0:
            sx = -px
            w += px
            px = 0
        if py < 0:
            sy = -py
            h += py
            py = 0
        if px+w > img.width:
            w = img.width - px
        if py+h > img.height:
            h = img.height - py
        return (px, py, sx, sy, w, h)

    def draw(self, img, pixmapper, bounds):
        '''default draw method'''
        pass

    def update_position(self, newpos):
        '''update object position'''
        if getattr(self, 'trail', None) is not None:
            self.trail.update_position(newpos)
        self.latlon = newpos.latlon
        if hasattr(self, 'rotation'):
            self.rotation = newpos.rotation

    def clicked(self, px, py):
        '''check if a click on px,py should be considered a click
        on the object. Return None if definately not a click,
        otherwise return the distance of the click, smaller being nearer
        '''
        return None

    def selection_info(self):
        '''extra selection information sent when object is selected'''
        return None

class SlipPolygon(SlipObject):
    '''a polygon to display on the map'''
    def __init__(self, key, points, layer, colour, linewidth, popup_menu=None):
        SlipObject.__init__(self, key, layer, popup_menu=popup_menu)
        self.points = points
        self.colour = colour
        self.linewidth = linewidth
        self._bounds = mp_util.polygon_bounds(self.points)
        self._pix_points = []
        self._selected_vertex = None

    def bounds(self):
        '''return bounding box'''
        return self._bounds

    def draw_line(self, img, pixmapper, pt1, pt2, colour, linewidth):
        '''draw a line on the image'''
        pix1 = pixmapper(pt1)
        pix2 = pixmapper(pt2)
        clipped = cv.ClipLine((img.width, img.height), pix1, pix2)
        if clipped is None:
            return
        (pix1, pix2) = clipped
        cv.Line(img, pix1, pix2, colour, linewidth)
        cv.Circle(img, pix2, linewidth*2, colour)
        if len(self._pix_points) == 0:
            self._pix_points.append(pix1)
        self._pix_points.append(pix2)

    def draw(self, img, pixmapper, bounds):
        '''draw a polygon on the image'''
        self._pix_points = []
        for i in range(len(self.points)-1):
            if len(self.points[i]) > 2:
                colour = self.points[i][2]
            else:
                colour = self.colour
            self.draw_line(img, pixmapper, self.points[i], self.points[i+1],
                           colour, self.linewidth)

    def clicked(self, px, py):
        '''see if the polygon has been clicked on.
        Consider it clicked if the pixel is within 6 of the point
        '''
        for i in range(len(self._pix_points)):
            (pixx,pixy) = self._pix_points[i]
            if abs(px - pixx) < 6 and abs(py - pixy) < 6:
                self._selected_vertex = i
                return math.sqrt((px - pixx)**2 + (py - pixy)**2)
        return None

    def selection_info(self):
        '''extra selection information sent when object is selected'''
        return self._selected_vertex


class SlipGrid(SlipObject):
    '''a map grid'''
    def __init__(self, key, layer, colour, linewidth):
        SlipObject.__init__(self, key, layer, )
        self.colour = colour
        self.linewidth = linewidth

    def bounds(self):
        '''return bounding box'''
        return None

    def draw_line(self, img, pixmapper, pt1, pt2, colour, linewidth):
        '''draw a line on the image'''
        pix1 = pixmapper(pt1)
        pix2 = pixmapper(pt2)
        clipped = cv.ClipLine((img.width, img.height), pix1, pix2)
        if clipped is None:
            return
        (pix1, pix2) = clipped
        cv.Line(img, pix1, pix2, colour, linewidth)
        cv.Circle(img, pix2, linewidth*2, colour)

    def draw(self, img, pixmapper, bounds):
        '''draw a polygon on the image'''
	(x,y,w,h) = bounds
        spacing = 1000
        while True:
            start = mp_util.latlon_round((x,y), spacing)
            dist = mp_util.gps_distance(x,y,x+w,y+h)
            count = int(dist / spacing)
            if count < 2:
                spacing /= 10
            elif count > 50:
                spacing *= 10
            else:
                break
        
        for i in range(count*2+2):
            pos1 = mp_util.gps_newpos(start[0], start[1], 90, i*spacing)
            pos3 = mp_util.gps_newpos(pos1[0], pos1[1], 0, 3*count*spacing)
            self.draw_line(img, pixmapper, pos1, pos3, self.colour, self.linewidth)

            pos1 = mp_util.gps_newpos(start[0], start[1], 0, i*spacing)
            pos3 = mp_util.gps_newpos(pos1[0], pos1[1], 90, 3*count*spacing)
            self.draw_line(img, pixmapper, pos1, pos3, self.colour, self.linewidth)



class SlipThumbnail(SlipObject):
    '''a thumbnail to display on the map'''
    def __init__(self, key, latlon, layer, img,
                 border_colour=None, border_width=0,
                 popup_menu=None):
        SlipObject.__init__(self, key, layer, popup_menu=popup_menu)
        self.latlon = latlon
        self._img = None
        self.imgstr = img.tostring()
        self.width = img.width
        self.height = img.height
        self.border_width = border_width
        self.border_colour = border_colour
        self.posx = -1
        self.posy = -1

    def bounds(self):
        '''return bounding box'''
        return (self.latlon[0], self.latlon[1], 0, 0)

    def img(self):
        '''return a cv image for the thumbnail'''
        if self._img is not None:
            return self._img
        self._img = cv.CreateImage((self.width, self.height), 8, 3)
        cv.SetData(self._img, self.imgstr)
        cv.CvtColor(self._img, self._img, cv.CV_BGR2RGB)
        if self.border_width and self.border_colour is not None:
            cv.Rectangle(self._img, (0, 0), (self.width-1, self.height-1),
                         self.border_colour, self.border_width)
        return self._img

    def draw(self, img, pixmapper, bounds):
        '''draw the thumbnail on the image'''
        thumb = self.img()
        (px,py) = pixmapper(self.latlon)

        # find top left
        px -= thumb.width/2
        py -= thumb.height/2
        w = thumb.width
        h = thumb.height

        (px, py, sx, sy, w, h) = self.clip(px, py, w, h, img)

        cv.SetImageROI(thumb, (sx, sy, w, h))
        cv.SetImageROI(img, (px, py, w, h))
        cv.Copy(thumb, img)
        cv.ResetImageROI(img)
        cv.ResetImageROI(thumb)

        # remember where we placed it for clicked()
        self.posx = px+w/2
        self.posy = py+h/2

    def clicked(self, px, py):
        '''see if the image has been clicked on'''
        if (abs(px - self.posx) > self.width/2 or
            abs(py - self.posy) > self.height/2):
            return None
        return math.sqrt((px-self.posx)**2 + (py-self.posy)**2)


class SlipTrail:
    '''trail information for a moving icon'''
    def __init__(self, timestep=0.2, colour=(255,255,0), count=60, points=[]):
        self.timestep = timestep
        self.colour = colour
        self.count = count
        self.points = points
        self.last_time = time.time()

    def update_position(self, newpos):
        '''update trail'''
        tnow = time.time()
        if tnow >= self.last_time + self.timestep:
            self.points.append(newpos.latlon)
            self.last_time = tnow
            while len(self.points) > self.count:
                self.points.pop(0)

    def draw(self, img, pixmapper, bounds):
        '''draw the trail'''
        for p in self.points:
            (px,py) = pixmapper(p)
            if px >= 0 and py >= 0 and px < img.width and py < img.height:
                cv.Circle(img, (px,py), 1, self.colour)


class SlipIcon(SlipThumbnail):
    '''a icon to display on the map'''
    def __init__(self, key, latlon, img, layer=1, rotation=0,
                 follow=False, trail=None, popup_menu=None):
        SlipThumbnail.__init__(self, key, latlon, layer, img, popup_menu=popup_menu)
        self.rotation = rotation
        self.follow = follow
        self.trail = trail

    def img(self):
        '''return a cv image for the icon'''
        SlipThumbnail.img(self)

        if self.rotation:
            # rotate the image
            mat = cv.CreateMat(2, 3, cv.CV_32FC1)
            cv.GetRotationMatrix2D((self.width/2,self.height/2),
                                   -self.rotation, 1.0, mat)
            self._rotated = cv.CloneImage(self._img)
            cv.WarpAffine(self._img, self._rotated, mat)
        else:
            self._rotated = self._img
        return self._rotated

    def draw(self, img, pixmapper, bounds):
        '''draw the icon on the image'''

        if self.trail is not None:
            self.trail.draw(img, pixmapper, bounds)

        icon = self.img()
        (px,py) = pixmapper(self.latlon)

        # find top left
        px -= icon.width/2
        py -= icon.height/2
        w = icon.width
        h = icon.height

        (px, py, sx, sy, w, h) = self.clip(px, py, w, h, img)

        cv.SetImageROI(icon, (sx, sy, w, h))
        cv.SetImageROI(img, (px, py, w, h))
        cv.Add(icon, img, img)
        cv.ResetImageROI(img)
        cv.ResetImageROI(icon)

        # remember where we placed it for clicked()
        self.posx = px+w/2
        self.posy = py+h/2


class SlipPosition:
    '''an position object to move an existing object on the map'''
    def __init__(self, key, latlon, layer=None, rotation=0):
        self.key = key
        self.layer = layer
        self.latlon = latlon
        self.rotation = rotation

class SlipCenter:
    '''an object to move the view center'''
    def __init__(self, latlon):
        self.latlon = latlon

class SlipBrightness:
    '''an object to change map brightness'''
    def __init__(self, brightness):
        self.brightness = brightness

class SlipClearLayer:
    '''remove all objects in a layer'''
    def __init__(self, layer):
        self.layer = layer

class SlipRemoveObject:
    '''remove an object by key'''
    def __init__(self, key):
        self.key = key


class SlipInformation:
    '''an object to display in the information box'''
    def __init__(self, key):
        self.key = key

    def draw(self, parent, box):
        '''default draw method'''
        pass

    def update(self, newinfo):
        '''update the information'''
        pass

class SlipDefaultPopup:
    '''an object to hold a default popup menu'''
    def __init__(self, popup, combine=False):
        self.popup = popup
        self.combine = combine

class SlipInfoImage(SlipInformation):
    '''an image to display in the info box'''
    def __init__(self, key, img):
        SlipInformation.__init__(self, key)
        self.imgstr = img.tostring()
        self.width = img.width
        self.height = img.height
        self.imgpanel = None

    def img(self):
        '''return a wx image'''
        img = wx.EmptyImage(self.width, self.height)
        img.SetData(self.imgstr)
        return img

    def draw(self, parent, box):
        '''redraw the image'''
        if self.imgpanel is None:
            self.imgpanel = mp_widgets.ImagePanel(parent, self.img())
            box.Add(self.imgpanel, flag=wx.LEFT, border=0)
            box.Layout()

    def update(self, newinfo):
        '''update the image'''
        self.imgstr = newinfo.imgstr
        self.width = newinfo.width
        self.height = newinfo.height
        if self.imgpanel is not None:
            self.imgpanel.set_image(self.img())


class SlipInfoText(SlipInformation):
    '''text to display in the info box'''
    def __init__(self, key, text):
        SlipInformation.__init__(self, key)
        self.text = text
        self.textctrl = None

    def _resize(self):
        '''calculate and set text size, handling multi-line'''
        lines = self.text.split('\n')
        xsize, ysize = 0, 0
        for line in lines:
            size = self.textctrl.GetTextExtent(line)
            xsize = max(xsize, size[0])
            ysize = ysize + size[1]
        xsize = int(xsize*1.2)
        self.textctrl.SetSize((xsize, ysize))
        self.textctrl.SetMinSize((xsize, ysize))


    def draw(self, parent, box):
        '''redraw the text'''
        if self.textctrl is None:
            self.textctrl = wx.TextCtrl(parent, style=wx.TE_MULTILINE|wx.TE_READONLY)
            self.textctrl.WriteText(self.text)
            self._resize()
            box.Add(self.textctrl, flag=wx.LEFT, border=0)
        box.Layout()

    def update(self, newinfo):
        '''update the image'''
        self.text = newinfo.text
        if self.textctrl is not None:
            self.textctrl.Clear()
            self.textctrl.WriteText(self.text)
            self._resize()

class SlipObjectSelection:
    '''description of a object under the cursor during an event'''
    def __init__(self, objkey, distance, layer, extra_info=None):
        self.distance = distance
        self.objkey = objkey
        self.layer = layer
        self.extra_info = extra_info

class SlipEvent:
    '''an event sent to the parent.

    latlon  = (lat,lon) of mouse on map
    event   = wx event
    objkeys = list of SlipObjectSelection selections
    '''
    def __init__(self, latlon, event, selected):
        self.latlon = latlon
        self.event = mp_util.object_container(event)
        self.selected = selected

class SlipMouseEvent(SlipEvent):
    '''a mouse event sent to the parent'''
    def __init__(self, latlon, event, selected):
        SlipEvent.__init__(self, latlon, event, selected)

class SlipKeyEvent(SlipEvent):
    '''a key event sent to the parent'''
    def __init__(self, latlon, event, selected):
        SlipEvent.__init__(self, latlon, event, selected)

class SlipMenuEvent(SlipEvent):
    '''a menu event sent to the parent'''
    def __init__(self, latlon, event, selected, menuitem):
        SlipEvent.__init__(self, latlon, event, selected)
        self.menuitem = menuitem


class MPSlipMap():
    '''
    a generic map viewer widget for use in mavproxy
    '''
    def __init__(self,
                 title='SlipMap',
                 lat=-35.362938,
                 lon=149.165085,
                 width=800,
                 height=600,
                 ground_width=1000,
                 tile_delay=0.3,
                 service="MicrosoftSat",
                 max_zoom=19,
                 debug=False,
                 brightness=1.0,
                 elevation=False,
                 download=True):
        import multiprocessing

        self.lat = lat
        self.lon = lon
        self.width = width
        self.height = height
        self.ground_width = ground_width
        self.download = download
        self.service = service
        self.tile_delay = tile_delay
        self.debug = debug
        self.max_zoom = max_zoom
        self.elevation = elevation
        self.oldtext = None
        self.brightness = brightness

        self.drag_step = 10

        self.title = title
        self.event_queue = multiprocessing.Queue()
        self.object_queue = multiprocessing.Queue()
        self.close_window = multiprocessing.Event()
        self.close_window.clear()
        self.child = multiprocessing.Process(target=self.child_task)
        self.child.start()
        self._callbacks = set()


    def child_task(self):
        '''child process - this holds all the GUI elements'''
        import wx
        state = self

        self.mt = mp_tile.MPTile(download=self.download,
                                 service=self.service,
                                 tile_delay=self.tile_delay,
                                 debug=self.debug,
                                 max_zoom=self.max_zoom)
        state.layers = {}
        state.info = {}
        state.need_redraw = True

        self.app = wx.PySimpleApp()
        self.app.frame = MPSlipMapFrame(state=self)
        self.app.frame.Show()
        self.app.MainLoop()

    def close(self):
        '''close the window'''
        self.close_window.set()
        if self.is_alive():
            self.child.join(2)

        self.child.terminate()

    def is_alive(self):
        '''check if graph is still going'''
        return self.child.is_alive()

    def add_object(self, obj):
        '''add or update an object on the map'''
        self.object_queue.put(obj)

    def set_position(self, key, latlon, layer=None, rotation=0):
        '''move an object on the map'''
        self.object_queue.put(SlipPosition(key, latlon, layer, rotation))

    def event_count(self):
        '''return number of events waiting to be processed'''
        return self.event_queue.qsize()

    def get_event(self):
        '''return next event or None'''
        if self.event_queue.qsize() == 0:
            return None
        return self.event_queue.get()

    def add_callback(self, callback):
        '''add a callback for events from the map'''
        self._callbacks.add(callback)

    def check_events(self):
        '''check for events, calling registered callbacks as needed'''
        while self.event_count() > 0:
            event = self.get_event()
            for callback in self._callbacks:
                callback(event)

    def icon(self, filename):
        '''load an icon from the data directory'''
        return mp_tile.mp_icon(filename)


import wx
from PIL import Image

class MPSlipMapFrame(wx.Frame):
    """ The main frame of the viewer
    """
    def __init__(self, state):
        wx.Frame.__init__(self, None, wx.ID_ANY, state.title)
        self.state = state
        state.frame = self
        state.grid = True
        state.follow = True
        state.popup_object = None
        state.popup_latlon = None
        state.popup_started = False
        state.default_popup = None
        state.panel = MPSlipMapPanel(self, state)
        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.Bind(wx.EVT_SIZE, state.panel.on_size)

        # create the View menu
        self.menu = MPMenuTop([MPMenuSubMenu('View',
                                             items=[MPMenuCheckbox('Follow\tCtrl+F', 'Follow Aircraft', 'toggleFollow',
                                                                   checked=state.follow),
                                                    MPMenuCheckbox('Grid\tCtrl+G', 'Enable Grid', 'toggleGrid',
                                                                   checked=state.grid),
                                                    MPMenuItem('Goto\tCtrl+P', 'Goto Position', 'gotoPosition'),
                                                    MPMenuItem('Brightness +\tCtrl+B', 'Increase Brightness', 'increaseBrightness'),
                                                    MPMenuItem('Brightness -\tCtrl+Shift+B', 'Decrease Brightness', 'decreaseBrightness'),
                                                    MPMenuRadio('Service', 'Select map service',
                                                                returnkey='setService',
                                                                selected=state.mt.get_service(),
                                                                items=state.mt.get_service_list())])])
        self.SetMenuBar(self.menu.wx_menu())
        self.Bind(wx.EVT_MENU, self.on_menu)

    def on_menu(self, event):
        '''handle menu selection'''
        state = self.state
        # see if it is a popup menu
        if state.popup_object is not None:
            obj = state.popup_object
            ret = obj.popup_menu.find_selected(event)
            if ret is not None:
                ret.call_handler()
                state.event_queue.put(SlipMenuEvent(state.popup_latlon, event,
                                                    [SlipObjectSelection(obj.key, 0, obj.layer, obj.selection_info())],
                                                    ret))
                state.popup_object = None
                state.popup_latlon = None
        if state.default_popup is not None:
            ret = state.default_popup.popup.find_selected(event)
            if ret is not None:
                ret.call_handler()
                state.event_queue.put(SlipMenuEvent(state.popup_latlon, event, [], ret))
            
        # otherwise a normal menu
        ret = self.menu.find_selected(event)
        if ret is None:
            return
        ret.call_handler()
        if ret.returnkey == 'toggleGrid':
            state.grid = ret.IsChecked()
        elif ret.returnkey == 'toggleFollow':
            state.follow = ret.IsChecked()
        elif ret.returnkey == 'setService':
            state.mt.set_service(ret.get_choice())
        elif ret.returnkey == 'gotoPosition':
            state.panel.enter_position()
        elif ret.returnkey == 'increaseBrightness':
            state.brightness *= 1.25
        elif ret.returnkey == 'decreaseBrightness':
            state.brightness /= 1.25
        state.need_redraw = True

    def find_object(self, key, layers):
        '''find an object to be modified'''
        state = self.state

        if layers is None:
            layers = state.layers.keys()
        for layer in layers:
            if key in state.layers[layer]:
                return state.layers[layer][key]
        return None

    def follow(self, object):
        '''follow an object on the map'''
        state = self.state
        (px,py) = state.panel.pixmapper(object.latlon)
        ratio = 0.25
        if (px > ratio*state.width and
            px < (1.0-ratio)*state.width and
            py > ratio*state.height and
            py < (1.0-ratio)*state.height):
            # we're in the mid part of the map already, don't move
            return

        if not state.follow:
            # the user has disabled following
            return

        (lat, lon) = object.latlon
        state.panel.re_center(state.width/2, state.height/2, lat, lon)

    def add_object(self, obj):
        '''add an object to a later'''
        state = self.state
        if not obj.layer in state.layers:
            # its a new layer
            state.layers[obj.layer] = {}
        state.layers[obj.layer][obj.key] = obj
        state.need_redraw = True

    def remove_object(self, key):
        '''remove an object by key from all layers'''
        state = self.state
        for layer in state.layers:
            state.layers[layer].pop(key, None)
        state.need_redraw = True

    def on_idle(self, event):
        '''prevent the main loop spinning too fast'''
        state = self.state

        # receive any display objects from the parent
        obj = None

        while state.object_queue.qsize():
            obj = state.object_queue.get()

            if isinstance(obj, SlipObject):
                self.add_object(obj)

            if isinstance(obj, SlipPosition):
                # move an object
                object = self.find_object(obj.key, obj.layer)
                if object is not None:
                    object.update_position(obj)
                    if getattr(object, 'follow', False):
                        self.follow(object)
                    state.need_redraw = True

            if isinstance(obj, SlipDefaultPopup):
                state.default_popup = obj

            if isinstance(obj, SlipInformation):
                # see if its a existing one or a new one
                if obj.key in state.info:
#                    print('update %s' % str(obj.key))
                    state.info[obj.key].update(obj)
                else:
#                    print('add %s' % str(obj.key))
                    state.info[obj.key] = obj
                state.need_redraw = True

            if isinstance(obj, SlipCenter):
                # move center
                (lat,lon) = obj.latlon
                state.panel.re_center(state.width/2, state.height/2, lat, lon)
                state.need_redraw = True

            if isinstance(obj, SlipBrightness):
                # set map brightness
                state.brightness = obj.brightness
                state.need_redraw = True

            if isinstance(obj, SlipClearLayer):
                # remove all objects from a layer
                if obj.layer in state.layers:
                    state.layers.pop(obj.layer)
                state.need_redraw = True

            if isinstance(obj, SlipRemoveObject):
                # remove an object by key
                if obj.layer in state.layers:
                    state.layers.pop(obj.layer)
                state.need_redraw = True
        
        if obj is None:
            time.sleep(0.05)


class MPSlipMapPanel(wx.Panel):
    """ The image panel
    """
    def __init__(self, parent, state):
        wx.Panel.__init__(self, parent)
        self.state = state
        self.img = None
        self.map_img = None
        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
        self.Bind(wx.EVT_SET_FOCUS, self.on_focus)
        self.redraw_timer.Start(200)
        self.mouse_pos = None
        self.mouse_down = None
        self.click_pos = None
        self.last_click_pos = None
        if state.elevation:
            self.ElevationMap = mp_elevation.ElevationModel()

        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.mainSizer)

        # display for lat/lon/elevation
        self.position = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)
        if os.name == 'nt':
            self.position.SetValue("line 1\nline 2\n")
            size = self.position.GetBestSize()
            self.position.SetMinSize(size)
            self.position.SetValue("")
        else:
            textsize = tuple(self.position.GetFullTextExtent('line 1\nline 2\n')[0:2])
            self.position.SetMinSize(textsize)

        self.mainSizer.AddSpacer(2)
        self.mainSizer.Add(self.position, flag=wx.LEFT | wx.BOTTOM | wx.GROW, border=0)
        self.position.Bind(wx.EVT_SET_FOCUS, self.on_focus)

        # a place to put control flags
        self.controls = wx.BoxSizer(wx.HORIZONTAL)
        self.mainSizer.Add(self.controls, 0, flag=wx.ALIGN_LEFT | wx.TOP | wx.GROW)
        self.mainSizer.AddSpacer(2)

        # a place to put information like image details
        self.information = wx.BoxSizer(wx.HORIZONTAL)
        self.mainSizer.Add(self.information, 0, flag=wx.ALIGN_LEFT | wx.TOP | wx.GROW)
        self.mainSizer.AddSpacer(2)

        # panel for the main map image
        self.imagePanel = mp_widgets.ImagePanel(self, wx.EmptyImage(state.width,state.height))
        self.mainSizer.Add(self.imagePanel, flag=wx.GROW, border=5)
        self.imagePanel.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse)
        self.imagePanel.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.imagePanel.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

        # a function to convert from (lat,lon) to (px,py) on the map
        self.pixmapper = functools.partial(self.pixel_coords)

        self.last_view = None
        self.redraw_map()
        state.frame.Fit()

    def on_focus(self, event):
        '''called when the panel gets focus'''
        self.imagePanel.SetFocus()

    def current_view(self):
        '''return a tuple representing the current view'''
        state = self.state
        return (state.lat, state.lon, state.width, state.height,
                state.ground_width, state.mt.tiles_pending())

    def coordinates(self, x, y):
        '''return coordinates of a pixel in the map'''
        state = self.state
        return state.mt.coord_from_area(x, y, state.lat, state.lon, state.width, state.ground_width)

    def re_center(self, x, y, lat, lon):
        '''re-center view for pixel x,y'''
        state = self.state
        if lat is None or lon is None:
            return
        (lat2,lon2) = self.coordinates(x, y)
        distance = mp_util.gps_distance(lat2, lon2, lat, lon)
        bearing  = mp_util.gps_bearing(lat2, lon2, lat, lon)
        (state.lat, state.lon) = mp_util.gps_newpos(state.lat, state.lon, bearing, distance)

    def change_zoom(self, zoom):
        '''zoom in or out by zoom factor, keeping centered'''
        state = self.state
        if self.mouse_pos:
            (x,y) = (self.mouse_pos.x, self.mouse_pos.y)
        else:
            (x,y) = (state.width/2, state.height/2)
        (lat,lon) = self.coordinates(x, y)
        state.ground_width *= zoom
        # limit ground_width to sane values
        state.ground_width = max(state.ground_width, 20)
        state.ground_width = min(state.ground_width, 20000000)
        self.re_center(x,y, lat, lon)

    def enter_position(self):
        '''enter new position'''
        state = self.state
        dlg = wx.TextEntryDialog(self, 'Enter new position', 'Position')
        dlg.SetValue("%f %f" % (state.lat, state.lon))
        if dlg.ShowModal() == wx.ID_OK:
            latlon = dlg.GetValue().split()
            dlg.Destroy()
            state.lat = float(latlon[0])
            state.lon = float(latlon[1])
            self.re_center(state.width/2,state.height/2, state.lat, state.lon)
            self.redraw_map()

    def update_position(self):
        '''update position text'''
        state = self.state
        pos = self.mouse_pos
        newtext = ''
        alt = 0
        if pos is not None:
            (lat,lon) = self.coordinates(pos.x, pos.y)
            newtext += 'Cursor: %f %f (%s)' % (lat, lon, mp_util.latlon_to_grid((lat, lon)))
            if state.elevation:
                alt = self.ElevationMap.GetElevation(lat, lon)
                newtext += ' %.1fm' % alt
        pending = state.mt.tiles_pending()
        if pending:
            newtext += ' Map Downloading %u ' % pending
        if alt == -1:
            newtext += ' SRTM Downloading '
        newtext += '\n'
        if self.click_pos is not None:
            newtext += 'Click: %f %f (%s %s) (%s)' % (self.click_pos[0], self.click_pos[1],
                                                      mp_util.degrees_to_dms(self.click_pos[0]),
                                                      mp_util.degrees_to_dms(self.click_pos[1]),
                                                      mp_util.latlon_to_grid(self.click_pos))
        if self.last_click_pos is not None:
            distance = mp_util.gps_distance(self.last_click_pos[0], self.last_click_pos[1],
                                            self.click_pos[0], self.click_pos[1])
            bearing = mp_util.gps_bearing(self.last_click_pos[0], self.last_click_pos[1],
                                            self.click_pos[0], self.click_pos[1])
            newtext += '  Distance: %.1fm Bearing %.1f' % (distance, bearing)
        if newtext != state.oldtext:
            self.position.Clear()
            self.position.WriteText(newtext)
            state.oldtext = newtext

    def pixel_coords(self, latlon, reverse=False):
        '''return pixel coordinates in the map image for a (lat,lon)
        if reverse is set, then return lat/lon for a pixel coordinate
        '''
        state = self.state
        if reverse:
            (x,y) = latlon
            return self.coordinates(x,y)
        (lat,lon) = (latlon[0], latlon[1])
        return state.mt.coord_to_pixel(state.lat, state.lon, state.width, state.ground_width, lat, lon)

    def draw_objects(self, objects, bounds, img):
        '''draw objects on the image'''
        keys = objects.keys()
        keys.sort()
        for k in keys:
            obj = objects[k]
            bounds2 = obj.bounds()
            if bounds2 is None or mp_util.bounds_overlap(bounds, bounds2):
                obj.draw(img, self.pixmapper, bounds)

    def redraw_map(self):
        '''redraw the map with current settings'''
        state = self.state

        view_same = (self.last_view and self.map_img and self.last_view == self.current_view())

        if view_same and not state.need_redraw:
            return

        # get the new map
        self.map_img = state.mt.area_to_image(state.lat, state.lon,
                                              state.width, state.height, state.ground_width)
        if state.brightness != 1.0:
            cv.ConvertScale(self.map_img, self.map_img, scale=state.brightness)


        # find display bounding box
        (lat2,lon2) = self.coordinates(state.width-1, state.height-1)
        bounds = (lat2, state.lon, state.lat-lat2, lon2-state.lon)

        # get the image
        img = cv.CloneImage(self.map_img)

        # possibly draw a grid
        if state.grid:
            SlipGrid('grid', layer=3, linewidth=1, colour=(255,255,0)).draw(img, self.pixmapper, bounds)

        # draw layer objects
        keys = state.layers.keys()
        keys.sort()
        for k in keys:
            self.draw_objects(state.layers[k], bounds, img)

        # draw information objects
        for key in state.info:
            state.info[key].draw(state.panel, state.panel.information)

        # display the image
        self.img = wx.EmptyImage(state.width,state.height)
        self.img.SetData(img.tostring())
        self.imagePanel.set_image(self.img)

        self.update_position()

        self.mainSizer.Fit(self)
        self.Refresh()
        self.last_view = self.current_view()
        self.SetFocus()
        state.need_redraw = False

    def on_redraw_timer(self, event):
        '''the redraw timer ensures we show new map tiles as they
        are downloaded'''
        state = self.state
        self.redraw_map()

    def on_size(self, event):
        '''handle window size changes'''
        state = self.state
        size = event.GetSize()
        state.width = size.width
        state.height = size.height
        self.redraw_map()

    def on_mouse_wheel(self, event):
        '''handle mouse wheel zoom changes'''
        state = self.state
        rotation = event.GetWheelRotation() / event.GetWheelDelta()
        if rotation > 0:
            zoom = 1.0/(1.1 * rotation)
        elif rotation < 0:
            zoom = 1.1 * (-rotation)
        self.change_zoom(zoom)
        self.redraw_map()

    def selected_objects(self, pos):
        '''return a list of matching objects for a position'''
        state = self.state
        selected = []
        (px, py) = pos
        for layer in state.layers:
            for key in state.layers[layer]:
                obj = state.layers[layer][key]
                distance = obj.clicked(px, py)
                if distance is not None:
                    selected.append(SlipObjectSelection(key, distance, layer, extra_info=obj.selection_info()))
        selected.sort(key=lambda c: c.distance)
        return selected

    def show_popup(self, selected, pos):
        '''show popup menu for an object'''
        state = self.state
        if selected.popup_menu is not None:
            import copy
            popup_menu = selected.popup_menu
            if state.default_popup.popup is not None and state.default_popup.combine:
                popup_menu = copy.deepcopy(popup_menu)
                popup_menu.add(MPMenuSeparator())
                popup_menu.combine(state.default_popup.popup)
            wx_menu = popup_menu.wx_menu()
            state.frame.PopupMenu(wx_menu, pos)

    def show_default_popup(self, pos):
        '''show default popup menu'''
        state = self.state
        if state.default_popup.popup is not None:
            wx_menu = state.default_popup.popup.wx_menu()
            state.frame.PopupMenu(wx_menu, pos)

    def on_mouse(self, event):
        '''handle mouse events'''
        state = self.state
        pos = event.GetPosition()
        if event.Leaving():
            self.mouse_pos = None
        else:
            self.mouse_pos = pos
        self.update_position()

        if event.ButtonIsDown(wx.MOUSE_BTN_ANY) or event.ButtonUp():
            # send any event with a mouse button to the parent
            latlon = self.coordinates(pos.x, pos.y)
            selected = self.selected_objects(pos)
            state.event_queue.put(SlipMouseEvent(latlon, event, selected))
            if event.RightDown():
                state.popup_object = None
                state.popup_latlon = None
                if len(selected) > 0:
                    obj = state.layers[selected[0].layer][selected[0].objkey]
                    if obj.popup_menu is not None:
                        state.popup_object = obj
                        state.popup_latlon = latlon
                        self.show_popup(obj, pos)
                        state.popup_started = True
                if not state.popup_started and state.default_popup is not None:
                    state.popup_latlon = latlon
                    self.show_default_popup(pos)
                    state.popup_started = True

        if not event.ButtonIsDown(wx.MOUSE_BTN_RIGHT):
            state.popup_started = False

        if event.LeftDown() or event.RightDown():
            self.mouse_down = pos
            self.last_click_pos = self.click_pos
            self.click_pos = self.coordinates(pos.x, pos.y)

        if event.Dragging() and event.ButtonIsDown(wx.MOUSE_BTN_LEFT):
            # drag map to new position
            newpos = pos
            dx = (self.mouse_down.x - newpos.x)
            dy = -(self.mouse_down.y - newpos.y)
            pdist = math.sqrt(dx**2 + dy**2)
            if pdist > state.drag_step:
                bearing = math.degrees(math.atan2(dx, dy))
                distance = (state.ground_width/float(state.width)) * pdist
                newlatlon = mp_util.gps_newpos(state.lat, state.lon, bearing, distance)
                (state.lat, state.lon) = newlatlon
                self.mouse_down = newpos
                self.redraw_map()

    def clear_thumbnails(self):
        '''clear all thumbnails from the map'''
        state = self.state
        for l in state.layers:
            keys = state.layers[l].keys()[:]
            for key in keys:
                if (isinstance(state.layers[l][key], SlipThumbnail)
                    and not isinstance(state.layers[l][key], SlipIcon)):
                    state.layers[l].pop(key)

    def on_key_down(self, event):
        '''handle keyboard input'''
        state = self.state

        # send all key events to the parent
        if self.mouse_pos:
            latlon = self.coordinates(self.mouse_pos.x, self.mouse_pos.y)
            selected = self.selected_objects(self.mouse_pos)
            state.event_queue.put(SlipKeyEvent(latlon, event, selected))

        c = event.GetUniChar()
        if c == ord('+') or (c == ord('=') and event.ShiftDown()):
            self.change_zoom(1.0/1.2)
            event.Skip()
        elif c == ord('-'):
            self.change_zoom(1.2)
            event.Skip()
        elif c == ord('G'):
            self.enter_position()
            event.Skip()
        elif c == ord('C'):
            self.clear_thumbnails()
            event.Skip()



if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    import time

    from optparse import OptionParser
    parser = OptionParser("mp_slipmap.py [options]")
    parser.add_option("--lat", type='float', default=-26.582218, help="start latitude")
    parser.add_option("--lon", type='float', default=151.840113, help="start longitude")
    parser.add_option("--service", default="MicrosoftSat", help="tile service")
    parser.add_option("--offline", action='store_true', default=False, help="no download")
    parser.add_option("--delay", type='float', default=0.3, help="tile download delay")
    parser.add_option("--max-zoom", type='int', default=19, help="maximum tile zoom")
    parser.add_option("--debug", action='store_true', default=False, help="show debug info")
    parser.add_option("--boundary", default=None, help="show boundary")
    parser.add_option("--mission", default=[], action='append', help="show mission")
    parser.add_option("--thumbnail", default=None, help="show thumbnail")
    parser.add_option("--icon", default=None, help="show icon")
    parser.add_option("--flag", default=[], type='str', action='append', help="flag positions")
    parser.add_option("--grid", default=False, action='store_true', help="add a UTM grid")
    parser.add_option("--elevation", action='store_true', default=False, help="show elevation information")
    parser.add_option("--verbose", action='store_true', default=False, help="show mount actions")
    (opts, args) = parser.parse_args()

    sm = MPSlipMap(lat=opts.lat,
                   lon=opts.lon,
                   download=not opts.offline,
                   service=opts.service,
                   debug=opts.debug,
                   max_zoom=opts.max_zoom,
                   elevation=opts.elevation,
                   tile_delay=opts.delay)

    if opts.boundary:
        boundary = mp_util.polygon_load(opts.boundary)
        sm.add_object(SlipPolygon('boundary', boundary, layer=1, linewidth=2, colour=(0,255,0)))

    if opts.mission:
        from pymavlink import mavwp
        for file in opts.mission:
            wp = mavwp.MAVWPLoader()
            wp.load(file)
            boundary = wp.polygon()
            sm.add_object(SlipPolygon('mission-%s' % file, boundary, layer=1, linewidth=1, colour=(255,255,255)))

    if opts.grid:
        sm.add_object(SlipGrid('grid', layer=3, linewidth=1, colour=(255,255,0)))

    if opts.thumbnail:
        thumb = cv.LoadImage(opts.thumbnail)
        sm.add_object(SlipThumbnail('thumb', (opts.lat,opts.lon), layer=1, img=thumb, border_width=2, border_colour=(255,0,0)))

    if opts.icon:
        icon = cv.LoadImage(opts.icon)
        sm.add_object(SlipIcon('icon', (opts.lat,opts.lon), icon, layer=3, rotation=90, follow=True))
        sm.set_position('icon', mp_util.gps_newpos(opts.lat,opts.lon, 180, 100), rotation=45)
        sm.add_object(SlipInfoImage('detail', icon))
        sm.add_object(SlipInfoText('detail text', 'test text'))

    for flag in opts.flag:
        (lat,lon) = flag.split(',')
        icon = sm.icon('flag.png')
        sm.add_object(SlipIcon('icon - %s' % str(flag), (float(lat),float(lon)), icon, layer=3, rotation=0, follow=False))
            
    while sm.is_alive():
        while sm.event_count() > 0:
            obj = sm.get_event()
            if not opts.verbose:
                continue
            if isinstance(obj, SlipMouseEvent):
                print("Mouse event at %s (X/Y=%u/%u) for %u objects" % (obj.latlon,
                                                                        obj.event.X, obj.event.Y,
                                                                        len(obj.selected)))
            if isinstance(obj, SlipKeyEvent):
                print("Key event at %s for %u objects" % (obj.latlon, len(obj.selected)))
        time.sleep(0.1)

########NEW FILE########
__FILENAME__ = mp_tile
#!/usr/bin/env python
'''
access satellite map tile database

some functions are based on code from mapUtils.py in gmapcatcher

Andrew Tridgell
May 2012
released under GNU GPL v3 or later
'''

import collections
import errno
import hashlib
import urllib2
import math
import threading
import os
import sys
import string
import time

try:
	import cv2.cv as cv
except ImportError:
	import cv

from MAVProxy.modules.lib import mp_util

class TileException(Exception):
	'''tile error class'''
	def __init__(self, msg):
		Exception.__init__(self, msg)

TILE_SERVICES = {
	# thanks to http://go2log.com/2011/09/26/fetching-tiles-for-offline-map/
	# for the URL mapping info
	"GoogleSat"      : "http://khm${GOOG_DIGIT}.google.com/kh/v=131&src=app&x=${X}&y=${Y}&z=${ZOOM}&s=${GALILEO}",
	"GoogleMap"      : "http://mt${GOOG_DIGIT}.google.com/vt/lyrs=m@121&hl=en&x=${X}&y=${Y}&z=${ZOOM}&s=${GALILEO}",
	"GoogleHyb"      : "http://mt${GOOG_DIGIT}.google.com/vt/lyrs=h@121&hl=en&x=${X}&y=${Y}&z=${ZOOM}&s=${GALILEO}",
	"GoogleTer"      : "http://mt${GOOG_DIGIT}.google.com/vt/lyrs=t@108,r@121&hl=en&x=${X}&y=${Y}&z=${ZOOM}&s=${GALILEO}",
	"GoogleChina"    : "http://mt${GOOG_DIGIT}.google.cn/vt/lyrs=m@121&hl=en&gl=cn&x=${X}&y=${Y}&z=${ZOOM}&s=${GALILEO}",
	"YahooMap"       : "http://maps${Y_DIGIT}.yimg.com/hx/tl?v=4.3&.intl=en&x=${X}&y=${YAHOO_Y}&z=${YAHOO_ZOOM}&r=1",
	"YahooSat"       : "http://maps${Y_DIGIT}.yimg.com/ae/ximg?v=1.9&t=a&s=256&.intl=en&x=${X}&y=${YAHOO_Y}&z=${YAHOO_ZOOM}&r=1",
	"YahooInMap"     : "http://maps.yimg.com/hw/tile?locale=en&imgtype=png&yimgv=1.2&v=4.1&x=${X}&y=${YAHOO_Y}&z=${YAHOO_ZOOM_2}",
	"YahooInHyb"     : "http://maps.yimg.com/hw/tile?imgtype=png&yimgv=0.95&t=h&x=${X}&y=${YAHOO_Y}&z=${YAHOO_ZOOM_2}",
	"YahooHyb"       : "http://maps${Y_DIGIT}.yimg.com/hx/tl?v=4.3&t=h&.intl=en&x=${X}&y=${YAHOO_Y}&z=${YAHOO_ZOOM}&r=1",
	"MicrosoftBrMap" : "http://imakm${MS_DIGITBR}.maplink3.com.br/maps.ashx?v=${QUAD}|t&call=2.2.4",
	"MicrosoftHyb"   : "http://ecn.t${MS_DIGIT}.tiles.virtualearth.net/tiles/h${QUAD}.png?g=441&mkt=en-us&n=z",
	"MicrosoftSat"   : "http://ecn.t${MS_DIGIT}.tiles.virtualearth.net/tiles/a${QUAD}.png?g=441&mkt=en-us&n=z",
	"MicrosoftMap"   : "http://ecn.t${MS_DIGIT}.tiles.virtualearth.net/tiles/r${QUAD}.png?g=441&mkt=en-us&n=z",
	"MicrosoftTer"   : "http://ecn.t${MS_DIGIT}.tiles.virtualearth.net/tiles/r${QUAD}.png?g=441&mkt=en-us&shading=hill&n=z",
        "OviSat"         : "http://maptile.maps.svc.ovi.com/maptiler/v2/maptile/newest/satellite.day/${Z}/${X}/${Y}/256/png8",
        "OviHybrid"      : "http://maptile.maps.svc.ovi.com/maptiler/v2/maptile/newest/hybrid.day/${Z}/${X}/${Y}/256/png8",
	"OpenStreetMap"  : "http://tile.openstreetmap.org/${ZOOM}/${X}/${Y}.png",
	"OSMARender"     : "http://tah.openstreetmap.org/Tiles/tile/${ZOOM}/${X}/${Y}.png",
	"OpenAerialMap"  : "http://tile.openaerialmap.org/tiles/?v=mgm&layer=openaerialmap-900913&x=${X}&y=${Y}&zoom=${OAM_ZOOM}",
	"OpenCycleMap"   : "http://andy.sandbox.cloudmade.com/tiles/cycle/${ZOOM}/${X}/${Y}.png"
	}

# these are the md5sums of "unavailable" tiles
BLANK_TILES = set(["d16657bbee25d7f15c583f5c5bf23f50",
                   "c0e76e6e90ff881da047c15dbea380c7",
		   "d41d8cd98f00b204e9800998ecf8427e"])

# all tiles are 256x256
TILES_WIDTH = 256
TILES_HEIGHT = 256

class TileServiceInfo:
	'''a lookup object for the URL templates'''
	def __init__(self, x, y, zoom):
		self.X = x
		self.Y = y
		self.Z = zoom
		quadcode = ''
		for i in range(zoom - 1, -1, -1):
			quadcode += str((((((y >> i) & 1) << 1) + ((x >> i) & 1))))
		self.ZOOM = zoom
		self.QUAD = quadcode
		self.YAHOO_Y = 2**(zoom-1) - 1 - y
		self.YAHOO_ZOOM = zoom + 1
		self.YAHOO_ZOOM_2 = 17 - zoom + 1
		self.OAM_ZOOM = 17 - zoom
		self.GOOG_DIGIT = (x + y) & 3
		self.MS_DIGITBR = (((y & 1) << 1) + (x & 1)) + 1
		self.MS_DIGIT = (((y & 3) << 1) + (x & 1))
		self.Y_DIGIT = (x + y + zoom) % 3 + 1
		self.GALILEO = "Galileo"[0:(3 * x + y) & 7]

	def __getitem__(self, a):
		return str(getattr(self, a))


class TileInfo:
	'''description of a tile'''
	def __init__(self, tile, zoom, service, offset=(0,0)):
		self.tile = tile
		(self.x, self.y) = tile
		self.zoom = zoom
                self.service = service
		(self.offsetx, self.offsety) = offset
		self.refresh_time()

	def key(self):
		'''tile cache key'''
		return (self.tile, self.zoom, self.service)

	def refresh_time(self):
		'''reset the request time'''
		self.request_time = time.time()

	def coord(self, offset=(0,0)):
		'''return lat,lon within a tile given (offsetx,offsety)'''
		(tilex, tiley) = self.tile
		(offsetx, offsety) = offset
		world_tiles = 1<<self.zoom
		x = ( tilex + 1.0*offsetx/TILES_WIDTH ) / (world_tiles/2.) - 1
		y = ( tiley + 1.0*offsety/TILES_HEIGHT) / (world_tiles/2.) - 1
		lon = x * 180.0
		y = math.exp(-y*2*math.pi)
		e = (y-1)/(y+1)
		lat = 180.0/math.pi * math.asin(e)
		return (lat, lon)

	def size(self):
		'''return tile size as (width,height) in meters'''
		(lat1, lon1) = self.coord((0,0))
		(lat2, lon2) = self.coord((TILES_WIDTH,0))
		width = mp_util.gps_distance(lat1, lon1, lat2, lon2)
		(lat2, lon2) = self.coord((0,TILES_HEIGHT))
		height = mp_util.gps_distance(lat1, lon1, lat2, lon2)
		return (width,height)

	def distance(self, lat, lon):
		'''distance of this tile from a given lat/lon'''
		(tlat, tlon) = self.coord((TILES_WIDTH/2,TILES_HEIGHT/2))
		return mp_util.gps_distance(lat, lon, tlat, tlon)

	def path(self):
		'''return relative path of tile image'''
		(x, y) = self.tile
		return os.path.join('%u' % self.zoom,
				    '%u' % y,
				    '%u.img' % x)

	def url(self, service):
		'''return URL for a tile'''
		if service not in TILE_SERVICES:
			raise TileException('unknown tile service %s' % service)
		url = string.Template(TILE_SERVICES[service])
		(x,y) = self.tile
		tile_info = TileServiceInfo(x, y, self.zoom)
		return url.substitute(tile_info)


class TileInfoScaled(TileInfo):
	'''information on a tile with scale information and placement'''
	def __init__(self, tile, zoom, scale, src, dst, service):
		TileInfo.__init__(self, tile, zoom, service)
		self.scale = scale
		(self.srcx, self.srcy) = src
		(self.dstx, self.dsty) = dst



class MPTile:
	'''map tile object'''
	def __init__(self, cache_path=None, download=True, cache_size=500,
		     service="MicrosoftSat", tile_delay=0.3, debug=False,
		     max_zoom=19, refresh_age=30*24*60*60):
		
		if cache_path is None:
			try:
				cache_path = os.path.join(os.environ['HOME'], '.tilecache')
			except Exception:
				import tempfile
				cache_path = os.path.join(tempfile.gettempdir(), 'MAVtilecache')

		if not os.path.exists(cache_path):
			mp_util.mkdir_p(cache_path)

		self.cache_path = cache_path
		self.max_zoom = max_zoom
		self.min_zoom = 1
		self.download = download
		self.cache_size = cache_size
		self.tile_delay = tile_delay
		self.service = service
		self.debug = debug
                self.refresh_age = refresh_age

		if service not in TILE_SERVICES:
			raise TileException('unknown tile service %s' % service)

		# _download_pending is a dictionary of TileInfo objects
		self._download_pending = {}
		self._download_thread = None
                self._loading = mp_icon('loading.jpg')
		self._unavailable = mp_icon('unavailable.jpg')
		try:
			self._tile_cache = collections.OrderedDict()
		except AttributeError:
			# OrderedDicts in python 2.6 come from the ordereddict module
			# which is a 3rd party package, not in python2.6 distribution
			import ordereddict
			self._tile_cache = ordereddict.OrderedDict()

        def set_service(self, service):
                '''set tile service'''
                self.service = service

        def get_service(self):
                '''get tile service'''
                return self.service

        def get_service_list(self):
                '''return list of available services'''
                service_list = TILE_SERVICES.keys()
                service_list.sort()
                return service_list

	def coord_to_tile(self, lat, lon, zoom):
		'''convert lat/lon/zoom to a TileInfo'''
		world_tiles = 1<<zoom
		x = world_tiles / 360.0 * (lon + 180.0)
		tiles_pre_radian = world_tiles / (2 * math.pi)
		e = math.sin(lat * (1/180.*math.pi))
		y = world_tiles/2 + 0.5*math.log((1+e)/(1-e)) * (-tiles_pre_radian)
		offsetx = int((x - int(x)) * TILES_WIDTH)
		offsety = int((y - int(y)) * TILES_HEIGHT)
		return TileInfo((int(x) % world_tiles, int(y) % world_tiles), zoom, self.service, offset=(offsetx, offsety))

	def tile_to_path(self, tile):
		'''return full path to a tile'''
		return os.path.join(self.cache_path, self.service, tile.path())

	def coord_to_tilepath(self, lat, lon, zoom):
		'''return the tile ID that covers a latitude/longitude at
		a specified zoom level
		'''
		tile = self.coord_to_tile(lat, lon, zoom)
		return self.tile_to_path(tile)

	def tiles_pending(self):
		'''return number of tiles pending download'''
		return len(self._download_pending)

	def downloader(self):
		'''the download thread'''
		while self.tiles_pending() > 0:
			time.sleep(self.tile_delay)

			keys = self._download_pending.keys()[:]

			# work out which one to download next, choosing by request_time
			tile_info = self._download_pending[keys[0]]
			for key in keys:
				if self._download_pending[key].request_time > tile_info.request_time:
					tile_info = self._download_pending[key]

			url = tile_info.url(self.service)
			path = self.tile_to_path(tile_info)
			key = tile_info.key()

			try:
				if self.debug:
					print("Downloading %s [%u left]" % (url, len(keys)))
				resp = urllib2.urlopen(url)
				headers = resp.info()
			except urllib2.URLError as e:
				#print('Error loading %s' % url)
				self._tile_cache[key] = self._unavailable
				self._download_pending.pop(key)
				if self.debug:
					print("Failed %s: %s" % (url, str(e)))
				continue
			if 'content-type' not in headers or headers['content-type'].find('image') == -1:
				self._tile_cache[key] = self._unavailable
				self._download_pending.pop(key)
				if self.debug:
					print("non-image response %s" % url)
				continue
			else:
				img = resp.read()

			# see if its a blank/unavailable tile
			md5 = hashlib.md5(img).hexdigest()
			if md5 in BLANK_TILES:
				if self.debug:
					print("blank tile %s" % url)
				self._tile_cache[key] = self._unavailable
				self._download_pending.pop(key)
				continue

			mp_util.mkdir_p(os.path.dirname(path))
			h = open(path+'.tmp','wb')
			h.write(img)
			h.close()
                        try:
                                os.unlink(path)
                        except Exception:
                                pass
                        os.rename(path+'.tmp', path)
			self._download_pending.pop(key)
		self._download_thread = None

	def start_download_thread(self):
		'''start the downloader'''
		if self._download_thread:
			return
		t = threading.Thread(target=self.downloader)
		t.daemon = True
		self._download_thread = t
		t.start()

	def load_tile_lowres(self, tile):
		'''load a lower resolution tile from cache to fill in a
		map while waiting for a higher resolution tile'''
		if tile.zoom == self.min_zoom:
			return None

		# find the equivalent lower res tile
		(lat,lon) = tile.coord()

		width2 = TILES_WIDTH
		height2 = TILES_HEIGHT

		for zoom2 in range(tile.zoom-1, self.min_zoom-1, -1):
			width2 /= 2
			height2 /= 2

			if width2 == 0 or height2 == 0:
				break

			tile_info = self.coord_to_tile(lat, lon, zoom2)

			# see if its in the tile cache
			key = tile_info.key()
			if key in self._tile_cache:
				img = self._tile_cache[key]
				if img == self._unavailable:
					continue
			else:
				path = self.tile_to_path(tile_info)
				try:
					img = cv.LoadImage(path)
					# add it to the tile cache
					self._tile_cache[key] = img
					while len(self._tile_cache) > self.cache_size:
						self._tile_cache.popitem(0)
				except IOError as e:
					continue

			# copy out the quadrant we want
                        availx = min(TILES_WIDTH - tile_info.offsetx, width2)
                        availy = min(TILES_HEIGHT - tile_info.offsety, height2)
                        if availx != width2 or availy != height2:
                                continue
			cv.SetImageROI(img, (tile_info.offsetx, tile_info.offsety, width2, height2))
			img2 = cv.CreateImage((width2,height2), 8, 3)
                        try:
                            cv.Copy(img, img2)
                        except Exception:
                            continue
			cv.ResetImageROI(img)

			# and scale it
			scaled = cv.CreateImage((TILES_WIDTH, TILES_HEIGHT), 8, 3)
			cv.Resize(img2, scaled)
			#cv.Rectangle(scaled, (0,0), (255,255), (0,255,0), 1)
			return scaled
		return None

	def load_tile(self, tile):
		'''load a tile from cache or tile server'''

		# see if its in the tile cache
		key = tile.key()
		if key in self._tile_cache:
			img = self._tile_cache[key]
			if img == self._unavailable:
				img = self.load_tile_lowres(tile)
				if img is None:
					img = self._unavailable
				return img


		path = self.tile_to_path(tile)
		try:
			ret = cv.LoadImage(path)

                        # if it is an old tile, then try to refresh
                        if os.path.getmtime(path) + self.refresh_age < time.time():
                                try:
                                        self._download_pending[key].refresh_time()
                                except Exception:
                                        self._download_pending[key] = tile
                                self.start_download_thread()
			# add it to the tile cache
			self._tile_cache[key] = ret
			while len(self._tile_cache) > self.cache_size:
				self._tile_cache.popitem(0)
			return ret
		except IOError as e:
			# windows gives errno 0 for some versions of python, treat that as ENOENT
			# and try a download
			if not e.errno in [errno.ENOENT,0]:
				raise
			pass
		if not self.download:
			img = self.load_tile_lowres(tile)
			if img is None:
				img = self._unavailable
			return img

		try:
			self._download_pending[key].refresh_time()
		except Exception:
			self._download_pending[key] = tile
		self.start_download_thread()

		img = self.load_tile_lowres(tile)
		if img is None:
			img = self._loading
		return img


	def scaled_tile(self, tile):
		'''return a scaled tile'''
		width = int(TILES_WIDTH / tile.scale)
		height = int(TILES_HEIGHT / tile.scale)
		scaled_tile = cv.CreateImage((width,height), 8, 3)
		full_tile = self.load_tile(tile)
		cv.Resize(full_tile, scaled_tile)
		return scaled_tile


	def coord_from_area(self, x, y, lat, lon, width, ground_width):
		'''return (lat,lon) for a pixel in an area image'''

		pixel_width = ground_width / float(width)
		dx = x * pixel_width
		dy = y * pixel_width

		return mp_util.gps_offset(lat, lon, dx, -dy)


	def coord_to_pixel(self, lat, lon, width, ground_width, lat2, lon2):
		'''return pixel coordinate (px,py) for position (lat2,lon2)
		in an area image. Note that the results are relative to top,left
		and may be outside the image'''
		pixel_width = ground_width / float(width)

		if lat is None or lon is None or lat2 is None or lon2 is None:
			return (0,0)

		dx = mp_util.gps_distance(lat, lon, lat, lon2)
		if lon2 < lon:
			dx = -dx
		dy = mp_util.gps_distance(lat, lon, lat2, lon)
		if lat2 > lat:
			dy = -dy

		dx /= pixel_width
		dy /= pixel_width
		return (int(dx), int(dy))


	def area_to_tile_list(self, lat, lon, width, height, ground_width, zoom=None):
		'''return a list of TileInfoScaled objects needed for
		an area of land, with ground_width in meters, and
		width/height in pixels.

		lat/lon is the top left corner. If unspecified, the
		zoom is automatically chosen to avoid having to grow
		the tiles
		'''

		pixel_width = ground_width / float(width)
		ground_height = ground_width * (height/(float(width)))
		top_right = mp_util.gps_newpos(lat, lon, 90, ground_width)
		bottom_left = mp_util.gps_newpos(lat, lon, 180, ground_height)
		bottom_right = mp_util.gps_newpos(bottom_left[0], bottom_left[1], 90, ground_width)

		# choose a zoom level if not provided
		if zoom is None:
			zooms = range(self.min_zoom, self.max_zoom+1)
		else:
			zooms = [zoom]
		for zoom in zooms:
			tile_min = self.coord_to_tile(lat, lon, zoom)
			(twidth,theight) = tile_min.size()
			tile_pixel_width = twidth / float(TILES_WIDTH)
			scale = pixel_width / tile_pixel_width
			if scale >= 1.0:
				break

		scaled_tile_width = int(TILES_WIDTH / scale)
		scaled_tile_height = int(TILES_HEIGHT / scale)

		# work out the bottom right tile
		tile_max = self.coord_to_tile(bottom_right[0], bottom_right[1], zoom)

		ofsx = int(tile_min.offsetx / scale)
		ofsy = int(tile_min.offsety / scale)
		srcy = ofsy
		dsty = 0

		ret = []

		# place the tiles
		for y in range(tile_min.y, tile_max.y+1):
			srcx = ofsx
			dstx = 0
			for x in range(tile_min.x, tile_max.x+1):
				if dstx < width and dsty < height:
					ret.append(TileInfoScaled((x,y), zoom, scale,
                                                                  (srcx,srcy), (dstx,dsty), self.service))
				dstx += scaled_tile_width-srcx
				srcx = 0
			dsty += scaled_tile_height-srcy
			srcy = 0
		return ret

	def area_to_image(self, lat, lon, width, height, ground_width, zoom=None, ordered=True):
		'''return an RGB image for an area of land, with ground_width
		in meters, and width/height in pixels.

		lat/lon is the top left corner. The zoom is automatically
		chosen to avoid having to grow the tiles'''

		img = cv.CreateImage((width,height),8,3)

		tlist = self.area_to_tile_list(lat, lon, width, height, ground_width, zoom)

		# order the display by distance from the middle, so the download happens
		# close to the middle of the image first
		if ordered:
			(midlat, midlon) = self.coord_from_area(width/2, height/2, lat, lon, width, ground_width)
			tlist.sort(key=lambda d: d.distance(midlat, midlon), reverse=True)

		for t in tlist:
			scaled_tile = self.scaled_tile(t)

			w = min(width - t.dstx, scaled_tile.width - t.srcx)
			h = min(height - t.dsty, scaled_tile.height - t.srcy)
			if w > 0 and h > 0:
				cv.SetImageROI(scaled_tile, (t.srcx, t.srcy, w, h))
				cv.SetImageROI(img, (t.dstx, t.dsty, w, h))
				cv.Copy(scaled_tile, img)
				cv.ResetImageROI(img)
				cv.ResetImageROI(scaled_tile)

		# return as an RGB image
		cv.CvtColor(img, img, cv.CV_BGR2RGB)
		return img

def mp_icon(filename):
        '''load an icon from the data directory'''
        # we have to jump through a lot of hoops to get an OpenCV image
        # when we may be in a package zip file
        try:
                import pkg_resources
                name = __name__
                if name == "__main__":
                        name = "MAVProxy.modules.mavproxy_map.mp_tile"
                raw = pkg_resources.resource_stream(name, "data/%s" % filename).read()
        except Exception:
                raw = open(os.path.join(__file__, 'data', filename)).read()
        imagefiledata = cv.CreateMatHeader(1, len(raw), cv.CV_8UC1)
        cv.SetData(imagefiledata, raw, len(raw))
        img = cv.DecodeImage(imagefiledata, cv.CV_LOAD_IMAGE_COLOR)
        return img


if __name__ == "__main__":

	from optparse import OptionParser
	parser = OptionParser("mp_tile.py [options]")
	parser.add_option("--lat", type='float', default=-35.362938, help="start latitude")
	parser.add_option("--lon", type='float', default=149.165085, help="start longitude")
	parser.add_option("--width", type='float', default=1000.0, help="width in meters")
	parser.add_option("--service", default="YahooSat", help="tile service")
	parser.add_option("--zoom", default=None, type='int', help="zoom level")
	parser.add_option("--max-zoom", type='int', default=19, help="maximum tile zoom")
	parser.add_option("--delay", type='float', default=1.0, help="tile download delay")
	parser.add_option("--boundary", default=None, help="region boundary")
	parser.add_option("--debug", action='store_true', default=False, help="show debug info")
	(opts, args) = parser.parse_args()

	lat = opts.lat
	lon = opts.lon
	ground_width = opts.width

	if opts.boundary:
		boundary = mp_util.polygon_load(opts.boundary)
		bounds = mp_util.polygon_bounds(boundary)
		lat = bounds[0]+bounds[2]
		lon = bounds[1]
		ground_width = max(mp_util.gps_distance(lat, lon, lat, lon+bounds[3]),
				   mp_util.gps_distance(lat, lon, lat-bounds[2], lon))
		print lat, lon, ground_width

	mt = MPTile(debug=opts.debug, service=opts.service,
		    tile_delay=opts.delay, max_zoom=opts.max_zoom)
	if opts.zoom is None:
		zooms = range(mt.min_zoom, mt.max_zoom+1)
	else:
		zooms = [opts.zoom]
	for zoom in zooms:
		tlist = mt.area_to_tile_list(lat, lon, width=1024, height=1024,
					     ground_width=ground_width, zoom=zoom)
		print("zoom %u needs %u tiles" % (zoom, len(tlist)))
		for tile in tlist:
			mt.load_tile(tile)
		while mt.tiles_pending() > 0:
			time.sleep(2)
			print("Waiting on %u tiles" % mt.tiles_pending())
	print('Done')

########NEW FILE########
__FILENAME__ = srtm
#!/usr/bin/env python

# Pylint: Disable name warnings
# pylint: disable-msg=C0103

"""Load and process SRTM data. Originally written by OpenStreetMap
Edited by CanberraUAV"""

from HTMLParser import HTMLParser
import httplib
import re
import pickle
import os.path
import os
import zipfile
import array
import math
import multiprocessing
from MAVProxy.modules.lib import mp_util
import tempfile

class NoSuchTileError(Exception):
    """Raised when there is no tile for a region."""
    def __init__(self, lat, lon):
        Exception.__init__(self)
        self.lat = lat
        self.lon = lon

    def __str__(self):
        return "No SRTM tile for %d, %d available!" % (self.lat, self.lon)


class WrongTileError(Exception):
    """Raised when the value of a pixel outside the tile area is requested."""
    def __init__(self, tile_lat, tile_lon, req_lat, req_lon):
        Exception.__init__(self)
        self.tile_lat = tile_lat
        self.tile_lon = tile_lon
        self.req_lat = req_lat
        self.req_lon = req_lon

    def __str__(self):
        return "SRTM tile for %d, %d does not contain data for %d, %d!" % (
            self.tile_lat, self.tile_lon, self.req_lat, self.req_lon)

class InvalidTileError(Exception):
    """Raised when the SRTM tile file contains invalid data."""
    def __init__(self, lat, lon):
        Exception.__init__(self)
        self.lat = lat
        self.lon = lon

    def __str__(self):
        return "SRTM tile for %d, %d is invalid!" % (self.lat, self.lon)

class SRTMDownloader():
    """Automatically download SRTM tiles."""
    def __init__(self, server="dds.cr.usgs.gov",
                 directory="/srtm/version2_1/SRTM3/",
                 cachedir=None,
                 offline=0):

        if cachedir is None:
            try:
                cachedir = os.path.join(os.environ['HOME'], '.tilecache/SRTM')
            except Exception:
                cachedir = os.path.join(tempfile.gettempdir(), 'MAVProxySRTM')

        self.offline = offline
        self.first_failure = False
        self.server = server
        self.directory = directory
        self.cachedir = cachedir
	'''print "SRTMDownloader - server= %s, directory=%s." % \
              (self.server, self.directory)'''
        if not os.path.exists(cachedir):
            mp_util.mkdir_p(cachedir)
        self.filelist = {}
        self.filename_regex = re.compile(
                r"([NS])(\d{2})([EW])(\d{3})\.hgt\.zip")
        self.filelist_file = os.path.join(self.cachedir, "filelist_python")
        self.childFileListDownload = None
        self.childTileDownload = None

    def loadFileList(self):
        """Load a previously created file list or create a new one if none is
            available."""
        try:
            data = open(self.filelist_file, 'rb')
        except IOError:
            '''print "No SRTM cached file list. Creating new one!"'''
            if self.offline == 0:
                self.createFileList()
            return
        try:
            self.filelist = pickle.load(data)
        except:
            '''print "Unknown error loading cached SRTM file list. Creating new one!"'''
            if self.offline == 0:
                self.createFileList()

    def createFileList(self):
        """SRTM data is split into different directories, get a list of all of
            them and create a dictionary for easy lookup."""
        if self.childFileListDownload is None or not self.childFileListDownload.is_alive():
            self.childFileListDownload = multiprocessing.Process(target=self.createFileListHTTP, args=(self.server, self.directory))
            self.childFileListDownload.start()

    def createFileListHTTP(self, server, directory):
        """Create a list of the available SRTM files on the server using
        HTTP file transfer protocol (rather than ftp).
        30may2010  GJ ORIGINAL VERSION
        """
        conn = httplib.HTTPConnection(server)
        conn.request("GET",directory)
        r1 = conn.getresponse()
        '''if r1.status==200:
            print "status200 received ok"
        else:
            print "oh no = status=%d %s" \
                  % (r1.status,r1.reason)'''

        data = r1.read()
        parser = parseHTMLDirectoryListing()
        parser.feed(data)
        continents = parser.getDirListing()
        '''print continents'''

        for continent in continents:
            '''print "Downloading file list for", continent'''
            conn.request("GET","%s/%s" % \
                         (self.directory,continent))
            r1 = conn.getresponse()
            '''if r1.status==200:
                print "status200 received ok"
            else:
                print "oh no = status=%d %s" \
                      % (r1.status,r1.reason)'''
            data = r1.read()
            parser = parseHTMLDirectoryListing()
            parser.feed(data)
            files = parser.getDirListing()

            for filename in files:
                self.filelist[self.parseFilename(filename)] = (
                            continent, filename)

            '''print self.filelist'''
        # Add meta info
        self.filelist["server"] = self.server
        self.filelist["directory"] = self.directory
        with open(self.filelist_file , 'wb') as output:
            pickle.dump(self.filelist, output)

    def parseFilename(self, filename):
        """Get lat/lon values from filename."""
        match = self.filename_regex.match(filename)
        if match is None:
            # TODO?: Raise exception?
            '''print "Filename", filename, "unrecognized!"'''
            return None
        lat = int(match.group(2))
        lon = int(match.group(4))
        if match.group(1) == "S":
            lat = -lat
        if match.group(3) == "W":
            lon = -lon
        return lat, lon

    def getTile(self, lat, lon):
        """Get a SRTM tile object. This function can return either an SRTM1 or
            SRTM3 object depending on what is available, however currently it
            only returns SRTM3 objects."""
        if self.childFileListDownload is not None and self.childFileListDownload.is_alive():
            '''print "Getting file list"'''
            return 0
        elif not self.filelist:
            '''print "Filelist download complete, loading data"'''
            data = open(self.filelist_file, 'rb')
            self.filelist = pickle.load(data)

        try:
            continent, filename = self.filelist[(int(lat), int(lon))]
        except KeyError:
            '''print "here??"'''
            return 0

        if not os.path.exists(os.path.join(self.cachedir, filename)):
            if self.childTileDownload is None or not self.childTileDownload.is_alive():
                self.childTileDownload = multiprocessing.Process(target=self.downloadTile, args=(continent, filename))
                self.childTileDownload.start()
                '''print "Getting Tile"'''
            return 0
        elif self.childTileDownload is not None and self.childTileDownload.is_alive():
            '''print "Still Getting Tile"'''
            return 0
        # TODO: Currently we create a new tile object each time.
        # Caching is required for improved performance.
        try:
            return SRTMTile(os.path.join(self.cachedir, filename), int(lat), int(lon))
        except InvalidTileError:
            return 0

    def downloadTile(self, continent, filename):
        #Use HTTP
        if self.offline == 1:
            return
        conn = httplib.HTTPConnection(self.server)
        conn.set_debuglevel(0)
        filepath = "%s%s%s" % \
                     (self.directory,continent,filename)
        '''print "filepath=%s" % filepath'''
        try:
            conn.request("GET", filepath)
            r1 = conn.getresponse()
            if r1.status==200:
                '''print "status200 received ok"'''
                data = r1.read()
                self.ftpfile = open(os.path.join(self.cachedir, filename), 'wb')
                self.ftpfile.write(data)
                self.ftpfile.close()
                self.ftpfile = None
            else:
                '''print "oh no = status=%d %s" \
                % (r1.status,r1.reason)'''
        except Exception as e:
            if not self.first_failure:
                #print("SRTM Download failed: %s" % str(e))
                self.first_failure = True
            pass


class SRTMTile:
    """Base class for all SRTM tiles.
        Each SRTM tile is size x size pixels big and contains
        data for the area from (lat, lon) to (lat+1, lon+1) inclusive.
        This means there is a 1 pixel overlap between tiles. This makes it
        easier for as to interpolate the value, because for every point we
        only have to look at a single tile.
        """
    def __init__(self, f, lat, lon):
        try:
            zipf = zipfile.ZipFile(f, 'r')
        except Exception:
            raise InvalidTileError(lat, lon)            
        names = zipf.namelist()
        if len(names) != 1:
            raise InvalidTileError(lat, lon)
        data = zipf.read(names[0])
        self.size = int(math.sqrt(len(data)/2)) # 2 bytes per sample
        # Currently only SRTM1/3 is supported
        if self.size not in (1201, 3601):
            raise InvalidTileError(lat, lon)
        self.data = array.array('h', data)
        self.data.byteswap()
        if len(self.data) != self.size * self.size:
            raise InvalidTileError(lat, lon)
        self.lat = lat
        self.lon = lon

    @staticmethod
    def _avg(value1, value2, weight):
        """Returns the weighted average of two values and handles the case where
            one value is None. If both values are None, None is returned.
        """
        if value1 is None:
            return value2
        if value2 is None:
            return value1
        return value2 * weight + value1 * (1 - weight)

    def calcOffset(self, x, y):
        """Calculate offset into data array. Only uses to test correctness
            of the formula."""
        # Datalayout
        # X = longitude
        # Y = latitude
        # Sample for size 1201x1201
        #  (   0/1200)     (   1/1200)  ...    (1199/1200)    (1200/1200)
        #  (   0/1199)     (   1/1199)  ...    (1199/1199)    (1200/1199)
        #       ...            ...                 ...             ...
        #  (   0/   1)     (   1/   1)  ...    (1199/   1)    (1200/   1)
        #  (   0/   0)     (   1/   0)  ...    (1199/   0)    (1200/   0)
        #  Some offsets:
        #  (0/1200)     0
        #  (1200/1200)  1200
        #  (0/1199)     1201
        #  (1200/1199)  2401
        #  (0/0)        1201*1200
        #  (1200/0)     1201*1201-1
        return x + self.size * (self.size - y - 1)

    def getPixelValue(self, x, y):
        """Get the value of a pixel from the data, handling voids in the
            SRTM data."""
        assert x < self.size, "x: %d<%d" % (x, self.size)
        assert y < self.size, "y: %d<%d" % (y, self.size)
        # Same as calcOffset, inlined for performance reasons
        offset = x + self.size * (self.size - y - 1)
        #print offset
        value = self.data[offset]
        if value == -32768:
            return -1 # -32768 is a special value for areas with no data
        return value


    def getAltitudeFromLatLon(self, lat, lon):
        """Get the altitude of a lat lon pair, using the four neighbouring
            pixels for interpolation.
        """
        # print "-----\nFromLatLon", lon, lat
        lat -= self.lat
        lon -= self.lon
        # print "lon, lat", lon, lat
        if lat < 0.0 or lat >= 1.0 or lon < 0.0 or lon >= 1.0:
            raise WrongTileError(self.lat, self.lon, self.lat+lat, self.lon+lon)
        x = lon * (self.size - 1)
        y = lat * (self.size - 1)
        # print "x,y", x, y
        x_int = int(x)
        x_frac = x - int(x)
        y_int = int(y)
        y_frac = y - int(y)
        # print "frac", x_int, x_frac, y_int, y_frac
        value00 = self.getPixelValue(x_int, y_int)
        value10 = self.getPixelValue(x_int+1, y_int)
        value01 = self.getPixelValue(x_int, y_int+1)
        value11 = self.getPixelValue(x_int+1, y_int+1)
        value1 = self._avg(value00, value10, x_frac)
        value2 = self._avg(value01, value11, x_frac)
        value  = self._avg(value1,  value2, y_frac)
        # print "%4d %4d | %4d\n%4d %4d | %4d\n-------------\n%4d" % (
        #        value00, value10, value1, value01, value11, value2, value)
        return value



class parseHTMLDirectoryListing(HTMLParser):

    def __init__(self):
        #print "parseHTMLDirectoryListing.__init__"
        HTMLParser.__init__(self)
        self.title="Undefined"
        self.isDirListing = False
        self.dirList=[]
        self.inTitle = False
        self.inHyperLink = False
        self.currAttrs=""
        self.currHref=""

    def handle_starttag(self, tag, attrs):
        #print "Encountered the beginning of a %s tag" % tag
        if tag=="title":
            self.inTitle = True
        if tag == "a":
            self.inHyperLink = True
            self.currAttrs=attrs
            for attr in attrs:
                if attr[0]=='href':
                    self.currHref = attr[1]


    def handle_endtag(self, tag):
        #print "Encountered the end of a %s tag" % tag
        if tag=="title":
            self.inTitle = False
        if tag == "a":
            # This is to avoid us adding the parent directory to the list.
            if self.currHref!="":
                self.dirList.append(self.currHref)
            self.currAttrs=""
            self.currHref=""
            self.inHyperLink = False

    def handle_data(self,data):
        if self.inTitle:
            self.title = data
            '''print "title=%s" % data'''
            if "Index of" in self.title:
                #print "it is an index!!!!"
                self.isDirListing = True
        if self.inHyperLink:
            # We do not include parent directory in listing.
            if  "Parent Directory" in data:
                self.currHref=""

    def getDirListing(self):
        return self.dirList

#DEBUG ONLY
if __name__ == '__main__':
    downloader = SRTMDownloader()
    downloader.loadFileList()
    tile = downloader.getTile(-36, 149)
    print tile.getAltitudeFromLatLon(-35.282, 149.1287)




########NEW FILE########
__FILENAME__ = mavproxy_misc
#!/usr/bin/env python
'''miscellaneous commands'''

import time, math
from pymavlink import mavutil

from MAVProxy.modules.lib import mp_module

class MiscModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(MiscModule, self).__init__(mpstate, "misc", "misc commands")
        self.add_command('alt', self.cmd_alt, "show altitude information")
        self.add_command('bat', self.cmd_bat, "show battery information")
        self.add_command('up', self.cmd_up, "adjust pitch trim by up to 5 degrees")
        self.add_command('reboot', self.cmd_reboot, "reboot autopilot")
        self.add_command('time', self.cmd_time, "show autopilot time")

    def altitude_difference(self, pressure1, pressure2, ground_temp):
        '''calculate barometric altitude'''
        scaling = pressure2 / pressure1
        temp = ground_temp + 273.15
        return 153.8462 * temp * (1.0 - math.exp(0.190259 * math.log(scaling)))

    def qnh_estimate(self):
        '''estimate QNH pressure from GPS altitude and scaled pressure'''
        alt_gps = self.master.field('GPS_RAW_INT', 'alt', 0) * 0.001
        pressure2 = self.master.field('SCALED_PRESSURE', 'press_abs', 0)
        ground_temp = self.get_mav_param('GND_TEMP', 21)
        temp = ground_temp + 273.15
        pressure1 = pressure2 / math.exp(math.log(1.0 - (alt_gps / (153.8462 * temp))) / 0.190259)
        return pressure1

    def cmd_alt(self, args):
        '''show altitude'''
        print("Altitude:  %.1f" % self.status.altitude)
        qnh_pressure = self.get_mav_param('FS_QNH_PRESSURE', None)
        if qnh_pressure is not None and qnh_pressure > 0:
            ground_temp = self.get_mav_param('GND_TEMP', 21)
            pressure = self.master.field('SCALED_PRESSURE', 'press_abs', 0)
            qnh_alt = self.altitude_difference(qnh_pressure, pressure, ground_temp)
            print("QNH Alt: %u meters %u feet for QNH pressure %.1f" % (qnh_alt, qnh_alt*3.2808, qnh_pressure))
        print("QNH Estimate: %.1f millibars" % self.qnh_estimate())


    def cmd_bat(self, args):
        '''show battery levels'''
        print("Flight battery:   %u%%" % self.status.battery_level)
        print("Avionics battery: %u%%" % self.status.avionics_battery_level)

    def cmd_up(self, args):
        '''adjust TRIM_PITCH_CD up by 5 degrees'''
        if len(args) == 0:
            adjust = 5.0
        else:
            adjust = float(args[0])
        old_trim = self.get_mav_param('TRIM_PITCH_CD', None)
        if old_trim is None:
            print("Existing trim value unknown!")
            return
        new_trim = int(old_trim + (adjust*100))
        if math.fabs(new_trim - old_trim) > 1000:
            print("Adjustment by %d too large (from %d to %d)" % (adjust*100, old_trim, new_trim))
            return
        print("Adjusting TRIM_PITCH_CD from %d to %d" % (old_trim, new_trim))
        self.param_set('TRIM_PITCH_CD', new_trim)

    def cmd_reboot(self, args):
        '''reboot autopilot'''
        self.master.reboot_autopilot()

    def cmd_time(self, args):
        '''show autopilot time'''
        tusec = self.master.field('SYSTEM_TIME', 'time_unix_usec', 0)
        if tusec == 0:
            print("No SYSTEM_TIME time available")
            return
        print("%s (%s)\n" % (time.ctime(tusec * 1.0e-6), time.ctime()))



def init(mpstate):
    '''initialise module'''
    return MiscModule(mpstate)

########NEW FILE########
__FILENAME__ = mmap_server
import BaseHTTPServer
import json
import os.path
import thread
import urlparse

DOC_DIR = os.path.join(os.path.dirname(__file__), 'mmap_app')


class Server(BaseHTTPServer.HTTPServer):
  def __init__(self, handler, address='', port=9999, module_state=None):
    BaseHTTPServer.HTTPServer.__init__(self, (address, port), handler)
    self.allow_reuse_address = True
    self.module_state = module_state


class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
  def do_GET(self):
    scheme, host, path, params, query, frag = urlparse.urlparse(self.path)
    if path == '/data':
      state = self.server.module_state
      data = {'lat': state.lat,
              'lon': state.lon,
              'heading': state.heading,
              'alt': state.alt,
              'airspeed': state.airspeed,
              'groundspeed': state.groundspeed}
      self.send_response(200)
      self.end_headers()
      self.wfile.write(json.dumps(data))
    else:
      # Remove leading '/'.
      path = path[1:]
      # Ignore all directories.  E.g.  for ../../bar/a.txt serve
      # DOC_DIR/a.txt.
      unused_head, path = os.path.split(path)
      # for / serve index.html.
      if path == '':
        path = 'index.html'
      content = None
      error = None
      try:
        with open(os.path.join(DOC_DIR, path), 'rb') as f:
          content = f.read()
      except IOError, e:
        error = str(e)
      if content:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(content)
      else:
        self.send_response(404)
        self.end_headers()
        self.wfile.write('Error: %s' % (error,))


def start_server(address, port, module_state):
  server = Server(
    Handler, address=address, port=port, module_state=module_state)
  thread.start_new_thread(server.serve_forever, ())
  return server

########NEW FILE########
__FILENAME__ = mavproxy_mode
#!/usr/bin/env python
'''mode command handling'''

import time, os
from pymavlink import mavutil

from MAVProxy.modules.lib import mp_module

class ModeModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(ModeModule, self).__init__(mpstate, "mode")
        self.add_command('mode', self.cmd_mode, "mode change")
        self.add_command('guided', self.cmd_guided, "fly to a clicked location on map")

    def cmd_mode(self, args):
        '''set arbitrary mode'''
        mode_mapping = self.master.mode_mapping()
        if mode_mapping is None:
            print('No mode mapping available')
            return
        if len(args) != 1:
            print('Available modes: ', mode_mapping.keys())
            return
        mode = args[0].upper()
        if mode not in mode_mapping:
            print('Unknown mode %s: ' % mode)
            return
        self.master.set_mode(mode_mapping[mode])

    def unknown_command(self, args):
        '''handle mode switch by mode name as command'''
        mode_mapping = self.master.mode_mapping()
        mode = args[0].upper()
        if mode in mode_mapping:
            self.master.set_mode(mode_mapping[mode])
            return True
        return False

    def cmd_guided(self, args):
        '''set GUIDED target'''
        if len(args) != 1:
            print("Usage: guided ALTITUDE")
            return
        try:
            latlon = self.module('map').click_position
        except Exception:
            print("No map available")
            return
        if latlon is None:
            print("No map click position available")
            return
        altitude = int(args[0])
        print("Guided %s %d" % (str(latlon), altitude))
        self.master.mav.mission_item_send(self.target_system,
                                               self.target_component,
                                               0,
                                               mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                                               mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                                               2, 0, 0, 0, 0, 0,
                                               latlon[0], latlon[1], altitude)

def init(mpstate):
    '''initialise module'''
    return ModeModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_param
#!/usr/bin/env python
'''param command handling'''

import time, os, fnmatch
from pymavlink import mavutil, mavparm
from MAVProxy.modules.lib import mp_util

from MAVProxy.modules.lib import mp_module

class ParamState:
    '''this class is separated to make it possible to use the parameter
       functions on a secondary connection'''
    def __init__(self, mav_param, logdir, vehicle_name, parm_file):
        self.mav_param_set = set()
        self.mav_param_count = 0
        self.param_period = mavutil.periodic_event(1)
        self.fetch_one = 0
        self.mav_param = mav_param
        self.logdir = logdir
        self.vehicle_name = vehicle_name
        self.parm_file = parm_file

    def handle_mavlink_packet(self, master, m):
        '''handle an incoming mavlink packet'''
        if m.get_type() == 'PARAM_VALUE':
            param_id = "%.16s" % m.param_id
            if m.param_index != -1 and m.param_index not in self.mav_param_set:
                added_new_parameter = True
                self.mav_param_set.add(m.param_index)
            else:
                added_new_parameter = False
            if m.param_count != -1:
                self.mav_param_count = m.param_count
            self.mav_param[str(param_id)] = m.param_value
            if self.fetch_one > 0:
                self.fetch_one -= 1
                print("%s = %f" % (param_id, m.param_value))
            if added_new_parameter and len(self.mav_param_set) == m.param_count:
                print("Received %u parameters" % m.param_count)
                if self.logdir != None:
                    self.mav_param.save(os.path.join(self.logdir, self.parm_file), '*', verbose=True)

    def fetch_check(self, master):
        '''check for missing parameters periodically'''
        if self.param_period.trigger():
            if len(self.mav_param_set) == 0:
                master.param_fetch_all()
            elif self.mav_param_count != 0 and len(self.mav_param_set) != self.mav_param_count:
                if master.time_since('PARAM_VALUE') >= 1:
                    diff = set(range(self.mav_param_count)).difference(self.mav_param_set)
                    count = 0
                    while len(diff) > 0 and count < 10:
                        idx = diff.pop()
                        master.param_fetch_one(idx)
                        count += 1

    def param_help_download(self):
        '''download XML files for parameters'''
        import multiprocessing
        files = []
        for vehicle in ['APMrover2', 'ArduCopter', 'ArduPlane']:
            url = 'http://autotest.diydrones.com/Parameters/%s/apm.pdef.xml' % vehicle
            path = mp_util.dot_mavproxy("%s.xml" % vehicle)
            files.append((url, path))
            url = 'http://autotest.diydrones.com/%s-defaults.parm' % vehicle
            path = mp_util.dot_mavproxy("%s-defaults.parm" % vehicle)
            files.append((url, path))
        try:
            child = multiprocessing.Process(target=mp_util.download_files, args=(files,))
            child.start()
        except Exception as e:
            print(e)

    def param_help(self, args):
        '''show help on a parameter'''
        if len(args) == 0:
            print("Usage: param help PARAMETER_NAME")
            return
        if self.vehicle_name is None:
            print("Unknown vehicle type")
            return
        path = mp_util.dot_mavproxy("%s.xml" % self.vehicle_name)
        if not os.path.exists(path):
            print("Please run 'param download' first (vehicle_name=%s)" % self.vehicle_name)
            return
        xml = open(path).read()
        from lxml import objectify
        objectify.enable_recursive_str()
        tree = objectify.fromstring(xml)
        htree = {}
        for p in tree.vehicles.parameters.param:
            n = p.get('name').split(':')[1]
            htree[n] = p
        for lib in tree.libraries.parameters:
            for p in lib.param:
                n = p.get('name')
                htree[n] = p
        for h in args:
            if h in htree:
                help = htree[h]
                print("%s: %s\n" % (h, help.get('humanName')))
                print(help.get('documentation'))
                try:
                    vchild = help.getchildren()[0]
                    print("\nValues: ")
                    for v in vchild.value:
                        print("\t%s : %s" % (v.get('code'), str(v)))
                except Exception as e:
                    pass
            else:
                print("Parameter '%s' not found in documentation" % h)

    def handle_command(self, master, args):
        '''handle parameter commands'''
        param_wildcard = "*"
        usage="Usage: param <fetch|set|show|load|preload|forceload|diff|download|help>"
        if len(args) < 1:
            print(usage)
            return
        if args[0] == "fetch":
            if len(args) == 1:
                master.param_fetch_all()
                self.mav_param_set = set()
                print("Requested parameter list")
            else:
                for p in self.mav_param.keys():
                    if fnmatch.fnmatch(p, args[1].upper()):
                        master.param_fetch_one(p)
                        self.fetch_one += 1
                        print("Requested parameter %s" % p)
        elif args[0] == "save":
            if len(args) < 2:
                print("usage: param save <filename> [wildcard]")
                return
            if len(args) > 2:
                param_wildcard = args[2]
            else:
                param_wildcard = "*"
            self.mav_param.save(args[1], param_wildcard, verbose=True)
        elif args[0] == "diff":
            wildcard = '*'
            if len(args) < 2 or args[1].find('*') != -1:
                if self.vehicle_name is None:
                    print("Unknown vehicle type")
                    return
                filename = mp_util.dot_mavproxy("%s-defaults.parm" % self.vehicle_name)
                if not os.path.exists(filename):
                    print("Please run 'param download' first (vehicle_name=%s)" % self.vehicle_name)
                    return
                if len(args) >= 2:
                    wildcard = args[1]
            else:
                filename = args[1]
                if len(args) == 3:
                    wildcard = args[2]
            print("%-16.16s %12.12s %12.12s" % ('Parameter', 'Defaults', 'Current'))
            self.mav_param.diff(filename, wildcard=wildcard)
        elif args[0] == "set":
            if len(args) < 2:
                print("Usage: param set PARMNAME VALUE")
                return
            if len(args) == 2:
                self.mav_param.show(args[1])
                return
            param = args[1]
            value = args[2]
            if not param.upper() in self.mav_param:
                print("Unable to find parameter '%s'" % param)
                return
            self.mav_param.mavset(master, param.upper(), value, retries=3)
        elif args[0] == "load":
            if len(args) < 2:
                print("Usage: param load <filename> [wildcard]")
                return
            if len(args) > 2:
                param_wildcard = args[2]
            else:
                param_wildcard = "*"
            self.mav_param.load(args[1], param_wildcard, master)
        elif args[0] == "preload":
            if len(args) < 2:
                print("Usage: param preload <filename>")
                return
            self.mav_param.load(args[1])
        elif args[0] == "forceload":
            if len(args) < 2:
                print("Usage: param forceload <filename> [wildcard]")
                return
            if len(args) > 2:
                param_wildcard = args[2]
            else:
                param_wildcard = "*"
            self.mav_param.load(args[1], param_wildcard, master, check=False)
        elif args[0] == "download":
            self.param_help_download()
        elif args[0] == "help":
            self.param_help(args[1:])
        elif args[0] == "show":
            if len(args) > 1:
                pattern = args[1]
            else:
                pattern = "*"
            self.mav_param.show(pattern)
        else:
            print(usage)


class ParamModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(ParamModule, self).__init__(mpstate, "param", "parameter handling", public = True)
        self.pstate = ParamState(self.mav_param, self.logdir, self.vehicle_name, 'mav.parm')
        self.add_command('param', self.cmd_param, "parameter handling",
                         ["<fetch|download>",
                          "<set|show|fetch|help> (PARAMETER)",
                          "<load|save|diff> (FILENAME)"])
        if self.continue_mode and self.logdir != None:
            parmfile = os.path.join(self.logdir, 'mav.parm')
            if os.path.exists(parmfile):
                mpstate.mav_param.load(parmfile)

    def mavlink_packet(self, m):
        '''handle an incoming mavlink packet'''
        self.pstate.handle_mavlink_packet(self.master, m)

    def idle_task(self):
        '''handle missing parameters'''
        self.pstate.vehicle_name = self.vehicle_name
        self.pstate.fetch_check(self.master)

    def cmd_param(self, args):
        '''control parameters'''
        self.pstate.handle_command(self.master, args)

def init(mpstate):
    '''initialise module'''
    return ParamModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_ppp
#!/usr/bin/env python
'''
A PPP over MAVLink module
Andrew Tridgell
May 2012
'''

import time, os, fcntl, pty

from MAVProxy.modules.lib import mp_module

class PPPModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(PPPModule, self).__init__(mpstate, "ppp", "PPP link")
        self.command = "noauth nodefaultroute nodetach nodeflate nobsdcomp mtu 128".split()
        self.packet_count = 0
        self.byte_count = 0
        self.ppp_fd = -1
        self.pid = -1
        self.add_command('ppp', self.cmd_ppp, "ppp link control")


    def ppp_read(self, ppp_fd):
        '''called from main select loop in mavproxy when the pppd child
        sends us some data'''
        buf = os.read(ppp_fd, 100)
        if len(buf) == 0:
            # EOF on the child fd
            self.stop_ppp_link()
            return
        print("ppp packet len=%u" % len(buf))
        master = self.master
        master.mav.ppp_send(len(buf), buf)

    def start_ppp_link(self):
        '''startup the link'''
        cmd = ['pppd']
        cmd.extend(self.command)
        (self.pid, self.ppp_fd) = pty.fork()
        if self.pid == 0:
            os.execvp("pppd", cmd)
            raise RuntimeError("pppd exited")
        if self.ppp_fd == -1:
            print("Failed to create link fd")
            return

        # ensure fd is non-blocking
        fcntl.fcntl(self.ppp_fd, fcntl.F_SETFL, fcntl.fcntl(self.ppp_fd, fcntl.F_GETFL) | os.O_NONBLOCK)
        self.byte_count = 0
        self.packet_count = 0

        # ask mavproxy to add us to the select loop
        self.mpself.select_extra[self.ppp_fd] = (self.ppp_read, self.ppp_fd)


    def stop_ppp_link(self):
        '''stop the link'''
        if self.ppp_fd == -1:
            return
        try:
            self.mpself.select_extra.pop(self.ppp_fd)
            os.close(self.ppp_fd)
            os.waitpid(self.pid, 0)
        except Exception:
            pass
        self.pid = -1
        self.ppp_fd = -1
        print("stopped ppp link")


    def cmd_ppp(self, args):
        '''set ppp parameters and start link'''
        usage = "ppp <command|start|stop>"
        if len(args) == 0:
            print(usage)
            return
        if args[0] == "command":
            if len(args) == 1:
                print("ppp.command=%s" % " ".join(self.command))
            else:
                self.command = args[1:]
        elif args[0] == "start":
            self.start_ppp_link()
        elif args[0] == "stop":
            self.stop_ppp_link()
        elif args[0] == "status":
            self.console.writeln("%u packets %u bytes" % (self.packet_count, self.byte_count))

    def unload(self):
        '''unload module'''
        self.stop_ppp_link()

    def mavlink_packet(self, m):
        '''handle an incoming mavlink packet'''
        if m.get_type() == 'PPP' and self.ppp_fd != -1:
            print("got ppp mavlink pkt len=%u" % m.length)
            os.write(self.ppp_fd, m.data[:m.length])

def init(mpstate):
    '''initialise module'''
    return PPPModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_rally
"""
    MAVProxy rally module
"""

from pymavlink import mavwp
import time
from MAVProxy.modules.lib import mp_module
from MAVProxy.modules.lib.mp_menu import *

class RallyModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(RallyModule, self).__init__(mpstate, "rally", "rally point control", public = True)
        self.rallyloader = mavwp.MAVRallyLoader(mpstate.status.target_system, mpstate.status.target_component)
        self.add_command('rally', self.cmd_rally, "rally point control", ["<add|clear|list|move|remove>",
                                    "<load|save> (FILENAME)"])
        self.have_list = False

        self.menu_added_console = False
        self.menu_added_map = False
        self.menu = MPMenuSubMenu('Rally',
                                  items=[MPMenuItem('Clear', 'Clear', '# rally clear'),
                                         MPMenuItem('List', 'List', '# rally list'),
                                         MPMenuItem('Load', 'Load', '# rally load ',
                                                    handler=MPMenuCallFileDialog(flags=wx.FD_OPEN,
                                                                                 title='Rally Load',
                                                                                 wildcard='*.rally')),
                                         MPMenuItem('Save', 'Save', '# rally save ',
                                                    handler=MPMenuCallFileDialog(flags=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT,
                                                                                 title='Rally Save',
                                                                                 wildcard='*.rally')),
                                         MPMenuItem('Add', 'Add', '# rally add ',
                                                    handler=MPMenuCallTextDialog(title='Rally Altitude (m)',
                                                                                 default=100))])


    def idle_task(self):
        '''called on idle'''
        if not self.menu_added_console and self.module('console') is not None:
            self.menu_added_console = True
            self.module('console').add_menu(self.menu)
        if not self.menu_added_map and self.module('map') is not None:
            self.menu_added_map = True
            self.module('map').add_menu(self.menu)

    def cmd_rally_add(self, args):
        '''handle rally add'''
        if len(args) < 1:
            alt = self.settings.rallyalt
        else:
            alt = float(args[0])

        if not self.have_list:
            print("Please list rally points first")
            return

        if (self.rallyloader.rally_count() > 4):
            print ("Only 5 rally points possible per flight plan.")
            return

        try:
            latlon = self.module('map').click_position
        except Exception:
            print("No map available")
            return
        if latlon is None:
            print("No map click position available")
            return

        break_alt = 0.0
        land_hdg = 0.0
        if (len(args) > 2):
            break_alt = float(args[2])
        if (len(args) > 3):
            land_hdg = float(args[3])

        self.rallyloader.create_and_append_rally_point(latlon[0] * 1e7, latlon[1] * 1e7, alt, break_alt, land_hdg, 0)
        self.send_rally_points()
        print("Added Rally point at %s %f" % (str(latlon), alt))

    def cmd_rally_move(self, args):
        '''handle rally move'''
        if len(args) < 1:
            print("Usage: rally move RALLYNUM")
            return
        if not self.have_list:
            print("Please list rally points first")
            return

        idx = int(args[0])
        if idx <= 0 or idx > self.rallyloader.rally_count():
            print("Invalid rally point number %u" % idx)
            return

        rpoint = self.rallyloader.rally_point(idx-1)

        try:
            latlon = self.module('map').click_position
        except Exception:
            print("No map available")
            return
        if latlon is None:
            print("No map click position available")
            return

        oldpos = (rpoint.lat*1e-7, rpoint.lng*1e-7)
        self.rallyloader.move(idx, latlon[0], latlon[1])
        self.send_rally_point(idx-1)
        p = self.fetch_rally_point(idx-1)
        if p.lat != int(latlon[0]*1e7) or p.lng != int(latlon[1]*1e7):
            print("Rally move failed")
            return
        self.rallyloader.reindex()
        print("Moved rally point from %s to %s at %fm" % (str(oldpos), str(latlon), rpoint.alt))


    def cmd_rally(self, args):
        '''rally point commands'''
        #TODO: add_land arg
        if len(args) < 1:
            self.print_usage()
            return

        elif args[0] == "add":
            self.cmd_rally_add(args[1:])

        elif args[0] == "move":
            self.cmd_rally_move(args[1:])

        elif args[0] == "clear":
            self.rallyloader.clear()
            self.mav_param.mavset(self.master,'RALLY_TOTAL',0,3)

        elif args[0] == "remove":
            if not self.have_list:
                print("Please list rally points first")
                return
            if (len(args) < 2):
                print("Usage: rally remove RALLYNUM")
                return
            self.rallyloader.remove(int(args[1]))
            self.send_rally_points()

        elif args[0] == "list":
            self.list_rally_points()
            self.have_list = True

        elif args[0] == "load":
            if (len(args) < 2):
                print("Usage: rally load filename")
                return

            try:
                self.rallyloader.load(args[1])
            except Exception as msg:
                print("Unable to load %s - %s" % (args[1], msg))
                return

            self.send_rally_points()
            self.have_list = True

            print("Loaded %u rally points from %s" % (self.rallyloader.rally_count(), args[1]))

        elif args[0] == "save":
            if (len(args) < 2):
                print("Usage: rally save filename")
                return

            self.rallyloader.save(args[1])

            print("Saved rally file %s" % args[1])

        else:
            self.print_usage()

    def mavlink_packet(self, m):
        '''handle incoming mavlink packet'''
        return #TODO when applicable

    def send_rally_point(self, i):
        '''send rally points from fenceloader'''
        p = self.rallyloader.rally_point(i)
        p.target_system = self.target_system
        p.target_component = self.target_component
        self.master.mav.send(p)

    def send_rally_points(self):
        '''send rally points from fenceloader'''
        self.mav_param.mavset(self.master,'RALLY_TOTAL',self.rallyloader.rally_count(),3)

        for i in range(self.rallyloader.rally_count()):
            self.send_rally_point(i)

    def fetch_rally_point(self, i):
        '''fetch one rally point'''
        self.master.mav.rally_fetch_point_send(self.target_system,
                                                    self.target_component, i)
        tstart = time.time()
        p = None
        while time.time() - tstart < 1:
            p = self.master.recv_match(type='RALLY_POINT', blocking=False)
            if p is not None:
                break
            time.sleep(0.1)
            continue
        if p is None:
            self.console.error("Failed to fetch rally point %u" % i)
            return None
        return p

    def list_rally_points(self):
        self.rallyloader.clear()
        rally_count = self.mav_param.get('RALLY_TOTAL',0)
        if rally_count == 0:
            print("No rally points")
            return
        for i in range(int(rally_count)):
            p = self.fetch_rally_point(i)
            if p is None:
                return
            self.rallyloader.append_rally_point(p)

        for i in range(self.rallyloader.rally_count()):
            p = self.rallyloader.rally_point(i)
            self.console.writeln("lat=%f lng=%f alt=%f break_alt=%f land_dir=%f" % (p.lat * 1e-7, p.lng * 1e-7, p.alt, p.break_alt, p.land_dir))

    def print_usage(self):
        print("Usage: rally <list|load|save|add|remove|move|clear>")

def init(mpstate):
    '''initialise module'''
    return RallyModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_rc
#!/usr/bin/env python
'''rc command handling'''

import time, os, struct
from pymavlink import mavutil
from MAVProxy.modules.lib import mp_module

class RCModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(RCModule, self).__init__(mpstate, "rc", "rc command handling", public = True)
        self.override = [ 0 ] * 8
        self.last_override = [ 0 ] * 8
        self.override_counter = 0
        self.add_command('rc', self.cmd_rc, "RC input control", ['<1|2|3|4|5|6|7|8|all>'])
        self.add_command('switch', self.cmd_switch, "flight mode switch control", ['<0|1|2|3|4|5|6>'])
        if self.sitl_output:
            self.override_period = mavutil.periodic_event(20)
        else:
            self.override_period = mavutil.periodic_event(1)

    def idle_task(self):
        if self.override_period.trigger():
            if (self.override != [ 0 ] * 8 or
                self.override != self.last_override or
                self.override_counter > 0):
                self.last_override = self.override[:]
                self.send_rc_override()
                if self.override_counter > 0:
                    self.override_counter -= 1

    def send_rc_override(self):
        '''send RC override packet'''
        if self.sitl_output:
            buf = struct.pack('<HHHHHHHH',
                              *self.override)
            self.sitl_output.write(buf)
        else:
            self.master.mav.rc_channels_override_send(self.target_system,
                                                           self.target_component,
                                                           *self.override)

    def cmd_switch(self, args):
        '''handle RC switch changes'''
        mapping = [ 0, 1165, 1295, 1425, 1555, 1685, 1815 ]
        if len(args) != 1:
            print("Usage: switch <pwmvalue>")
            return
        value = int(args[0])
        if value < 0 or value > 6:
            print("Invalid switch value. Use 1-6 for flight modes, '0' to disable")
            return
        if self.vehicle_type == 'copter':
            default_channel = 5
        else:
            default_channel = 8
        if self.vehicle_type == 'rover':
            flite_mode_ch_parm = int(self.get_mav_param("MODE_CH", default_channel))
        else:
            flite_mode_ch_parm = int(self.get_mav_param("FLTMODE_CH", default_channel))
        self.override[flite_mode_ch_parm - 1] = mapping[value]
        self.override_counter = 10
        self.send_rc_override()
        if value == 0:
            print("Disabled RC switch override")
        else:
            print("Set RC switch override to %u (PWM=%u channel=%u)" % (
                value, mapping[value], flite_mode_ch_parm))

    def cmd_rc(self, args):
        '''handle RC value override'''
        if len(args) != 2:
            print("Usage: rc <channel|all> <pwmvalue>")
            return
        value = int(args[1])
        if value == -1:
            value = 65535
        if args[0] == 'all':
            for i in range(8):
                self.override[i] = value
        else:
            channel = int(args[0])
            self.override[channel - 1] = value
            if channel < 1 or channel > 8:
                print("Channel must be between 1 and 8 or 'all'")
                return
        self.override_counter = 10
        self.send_rc_override()

def init(mpstate):
    '''initialise module'''
    return RCModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_relay
#!/usr/bin/env python
'''relay handling module'''

import time
from pymavlink import mavutil
from MAVProxy.modules.lib import mp_module

class RelayModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(RelayModule, self).__init__(mpstate, "relay")
        self.add_command('relay', self.cmd_relay, "relay commands")
        self.add_command('servo', self.cmd_servo, "servo commands")

    def cmd_relay(self, args):
        '''set relays'''
        if len(args) == 0 or args[0] not in ['set', 'repeat']:
            print("Usage: relay <set|repeat>")
            return
        if args[0] == "set":
            if len(args) < 3:
                print("Usage: relay set <RELAY_NUM> <0|1>")
                return
            self.master.mav.command_long_send(self.target_system,
                                                   self.target_component,
                                                   mavutil.mavlink.MAV_CMD_DO_SET_RELAY, 0,
                                                   int(args[1]), int(args[2]),
                                                   0, 0, 0, 0, 0)
        if args[0] == "repeat":
            if len(args) < 4:
                print("Usage: relay repeat <RELAY_NUM> <COUNT> <PERIOD>")
                return
            self.master.mav.command_long_send(self.target_system,
                                                   self.target_component,
                                                   mavutil.mavlink.MAV_CMD_DO_REPEAT_RELAY, 0,
                                                   int(args[1]), int(args[2]), float(args[3]),
                                                   0, 0, 0, 0)

    def cmd_servo(self, args):
        '''set servos'''
        if len(args) == 0 or args[0] not in ['set', 'repeat']:
            print("Usage: servo <set|repeat>")
            return
        if args[0] == "set":
            if len(args) < 3:
                print("Usage: servo set <SERVO_NUM> <PWM>")
                return
            self.master.mav.command_long_send(self.target_system,
                                                   self.target_component,
                                                   mavutil.mavlink.MAV_CMD_DO_SET_SERVO, 0,
                                                   int(args[1]), int(args[2]),
                                                   0, 0, 0, 0, 0)
        if args[0] == "repeat":
            if len(args) < 5:
                print("Usage: servo repeat <SERVO_NUM> <PWM> <COUNT> <PERIOD>")
                return
            self.master.mav.command_long_send(self.target_system,
                                                   self.target_component,
                                                   mavutil.mavlink.MAV_CMD_DO_REPEAT_SERVO, 0,
                                                   int(args[1]), int(args[2]), int(args[3]), float(args[4]),
                                                   0, 0, 0)


def init(mpstate):
    '''initialise module'''
    return RelayModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_sensors
#!/usr/bin/env python
'''monitor sensor consistancy'''

import time, math
from pymavlink import mavutil

from MAVProxy.modules.lib import mp_module


def angle_diff(angle1, angle2):
    ret = angle1 - angle2
    if ret > 180:
        ret -= 360;
    if ret < -180:
        ret += 360
    return ret

class sensors_report(object):
    def __init__(self):
        self.last_report = 0
        self.ok = True
        self.value = 0

class SensorsModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(SensorsModule, self).__init__(mpstate, "sensors", "monitor sensor consistancy")
        self.add_command('sensors', self.cmd_sensors, "show key sensors")
        self.add_command('speed', self.cmd_speed, "enable/disable speed report")

        self.last_report = 0
        self.ok = True
        self.value = 0
        self.ground_alt = 0
        self.gps_alt = 0
        self.max_speed = 0
        self.last_watch = 0
        self.reports = {}
        self.reports['heading'] = sensors_report()
        self.reports['altitude'] = sensors_report()
        self.reports['speed'] = sensors_report()

        from MAVProxy.modules.lib.mp_settings import MPSetting
        self.settings.append(MPSetting('speedreporting', bool, False, 'Speed Reporting', tab='Sensors'))

        if 'GPS_RAW' in self.status.msgs:
            # cope with reload
            gps = mpstate.status.msgs['GPS_RAW']
            self.ground_alt = gps.alt - self.status.altitude

        if 'GPS_RAW_INT' in self.status.msgs:
            # cope with reload
            gps = mpstate.status.msgs['GPS_RAW_INT']
            self.ground_alt = (gps.alt / 1.0e3) - self.status.altitude

    def cmd_sensors(self, args):
        '''show key sensors'''
        if self.master.WIRE_PROTOCOL_VERSION == '1.0':
            gps_heading = self.status.msgs['GPS_RAW_INT'].cog * 0.01
        else:
            gps_heading = self.status.msgs['GPS_RAW'].hdg

        self.console.writeln("heading: %u/%u   alt: %u/%u  r/p: %u/%u speed: %u/%u  thr: %u" % (
            self.status.msgs['VFR_HUD'].heading,
            gps_heading,
            self.status.altitude,
            self.gps_alt,
            math.degrees(self.status.msgs['ATTITUDE'].roll),
            math.degrees(self.status.msgs['ATTITUDE'].pitch),
            self.status.msgs['VFR_HUD'].airspeed,
            self.status.msgs['VFR_HUD'].groundspeed,
            self.status.msgs['VFR_HUD'].throttle))


    def cmd_speed(self, args):
        '''enable/disable speed report'''
        self.settings.set('speedreporting', not self.settings.speedreporting)
        if self.settings.speedreporting:
            self.console.writeln("Speed reporting enabled", bg='yellow')
        else:
            self.console.writeln("Speed reporting disabled", bg='yellow')

    def report(self, name, ok, msg=None, deltat=20):
        '''report a sensor error'''
        r = self.reports[name]
        if time.time() < r.last_report + deltat:
            r.ok = ok
            return
        r.last_report = time.time()
        if ok and not r.ok:
            self.say("%s OK" % name)
        r.ok = ok
        if not r.ok:
            self.say(msg)

    def report_change(self, name, value, maxdiff=1, deltat=10):
        '''report a sensor change'''
        r = self.reports[name]
        if time.time() < r.last_report + deltat:
            return
        r.last_report = time.time()
        if math.fabs(r.value - value) < maxdiff:
            return
        r.value = value
        self.say("%s %u" % (name, value))

    def check_heading(self, m):
        '''check heading discrepancy'''
        if 'GPS_RAW' in self.status.msgs:
            gps = self.status.msgs['GPS_RAW']
            if gps.v < 3:
                return
            diff = math.fabs(angle_diff(m.heading, gps.hdg))
        elif 'GPS_RAW_INT' in self.status.msgs:
            gps = self.status.msgs['GPS_RAW_INT']
            if gps.vel < 300:
                return
            diff = math.fabs(angle_diff(m.heading, gps.cog / 100.0))
        else:
            return
        self.report('heading', diff < 20, 'heading error %u' % diff)

    def check_altitude(self, m):
        '''check altitude discrepancy'''
        if 'GPS_RAW' in self.status.msgs:
            gps = self.status.msgs['GPS_RAW']
            if gps.fix_type != 2:
                return
            v = gps.v
            alt = gps.alt
        elif 'GPS_RAW_INT' in self.status.msgs:
            gps = self.status.msgs['GPS_RAW_INT']
            if gps.fix_type != 3:
                return
            v = gps.vel / 100
            alt = gps.alt / 1000
        else:
            return

        if v > self.max_speed:
            self.max_speed = v
        if self.max_speed < 5:
            self.ground_alt = alt
            return
        self.gps_alt = alt - self.ground_alt
        diff = math.fabs(self.gps_alt - self.status.altitude)
        self.report('altitude', diff < 30, 'altitude error %u' % diff)

    def mavlink_packet(self, m):
        '''handle an incoming mavlink packet'''
        if m.get_type() == 'VFR_HUD' and ('GPS_RAW' in self.status.msgs or 'GPS_RAW_INT' in self.status.msgs):
            self.check_heading(m)
            self.check_altitude(m)
            if self.settings.speedreporting:
                if m.airspeed != 0:
                    speed = m.airspeed
                else:
                    speed = m.groundspeed
                self.report_change('speed', speed, maxdiff=2, deltat=2)
        if self.status.watch == "sensors" and time.time() > self.sensors_state.last_watch + 1:
            self.sensors_state.last_watch = time.time()
            self.cmd_sensors([])

def init(mpstate):
    '''initialise module'''
    return SensorsModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_serial
#!/usr/bin/env python
'''serial_control MAVLink handling'''

import time, os, fnmatch, sys
from pymavlink import mavutil, mavwp
from MAVProxy.modules.lib import mp_settings
from MAVProxy.modules.lib import mp_module

class SerialModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(SerialModule, self).__init__(mpstate, "serial", "serial control handling")
        self.add_command('serial', self.cmd_serial,
                         'remote serial control',
                         ['<lock|unlock|send>',
                          'set (SERIALSETTING)'])
        self.serial_settings = mp_settings.MPSettings(
            [ ('port', int, 0),
              ('baudrate', int, 57600),
              ('timeout', int, 500)
              ]
            )
        self.add_completion_function('(SERIALSETTING)', self.serial_settings.completion)
        self.locked = False

    def mavlink_packet(self, m):
        '''handle an incoming mavlink packet'''
        if m.get_type() == 'SERIAL_CONTROL':
            data = m.data[:m.count]
            s = ''.join(str(chr(x)) for x in data)
            sys.stdout.write(s)

    def serial_lock(self, lock):
        '''lock or unlock the port'''
        mav = self.master.mav
        if lock:
            flags = mavutil.mavlink.SERIAL_CONTROL_FLAG_EXCLUSIVE
            self.locked = True
        else:
            flags = 0
            self.locked = False
        mav.serial_control_send(self.serial_settings.port,
                                flags,
                                0, 0, 0, [0]*70)

    def serial_send(self, args):
        '''send some bytes'''
        mav = self.master.mav
        flags = 0
        if self.locked:
            flags |= mavutil.mavlink.SERIAL_CONTROL_FLAG_EXCLUSIVE
        if self.serial_settings.timeout != 0:
            flags |= mavutil.mavlink.SERIAL_CONTROL_FLAG_RESPOND
        if self.serial_settings.timeout >= 500:
            flags |= mavutil.mavlink.SERIAL_CONTROL_FLAG_MULTI

        s = ' '.join(args)
        s = s.replace('\\r', '\r')
        s = s.replace('\\n', '\n')
        buf = [ord(x) for x in s]
        buf.extend([0]*(70-len(buf)))
        mav.serial_control_send(self.serial_settings.port,
                                flags,
                                self.serial_settings.timeout,
                                self.serial_settings.baudrate,
                                len(s), buf)

    def cmd_serial(self, args):
        '''serial control commands'''
        usage = "Usage: serial <lock|unlock|set|send>"
        if len(args) < 1:
            print(usage)
            return
        if args[0] == "lock":
            self.serial_lock(True)
        elif args[0] == "unlock":
            self.serial_lock(False)
        elif args[0] == "set":
            self.serial_settings.command(args[1:])
        elif args[0] == "send":
            self.serial_send(args[1:])
        else:
            print(usage)

def init(mpstate):
    '''initialise module'''
    return SerialModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_speech
#!/usr/bin/env python
'''tune command handling'''

import time, os
from MAVProxy.modules.lib import mp_module

class SpeechModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(SpeechModule, self).__init__(mpstate, "speech", "speech output")
        self.mpstate.functions.say = self.say
        self.settings.append(('speech', int, 1))
        self.kill_speech_dispatcher()
        for backend in [self.say_speechd, self.say_espeak]:
            try:
                backend("")
                self.say_backend = backend
                return
            except Exception:
                pass
        self.say_backend = None
        print("No speech available")

    def kill_speech_dispatcher(self):
        '''kill speech dispatcher processs'''
        pidpath = os.path.join(os.environ['HOME'], '.speech-dispatcher',
                               'pid', 'speech-dispatcher.pid')
        if os.path.exists(pidpath):
            try:
                import signal
                pid = int(open(pidpath).read())
                if pid > 1 and os.kill(pid, 0) is None:
                    print("Killing speech dispatcher pid %u" % pid)
                    os.kill(pid, signal.SIGINT)
                    time.sleep(1)
            except Exception as e:
                pass


    def unload(self):
        '''unload module'''
        self.kill_speech_dispatcher()

    def say_speechd(self, text, priority='important'):
        '''speak some text'''
        ''' http://cvs.freebsoft.org/doc/speechd/ssip.html see 4.3.1 for priorities'''
        import speechd
        self.speech = speechd.SSIPClient('MAVProxy%u' % os.getpid())
        self.speech.set_output_module('festival')
        self.speech.set_language('en')
        self.speech.set_priority(priority)
        self.speech.set_punctuation(speechd.PunctuationMode.SOME)
        self.speech.speak(text)
        self.speech.close()

    def say_espeak(self, text, priority='important'):
        '''speak some text using espeak'''
        ''' http://cvs.freebsoft.org/doc/speechd/ssip.html see 4.3.1 for priorities'''
        from espeak import espeak
        espeak.synth(text)

    def say(self, text, priority='important'):
        '''speak some text'''
        ''' http://cvs.freebsoft.org/doc/speechd/ssip.html see 4.3.1 for priorities'''
        self.console.writeln(text)
        if self.settings.speech and self.say_backend is not None:
            self.say_backend(text, priority=priority)

def init(mpstate):
    '''initialise module'''
    return SpeechModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_test
#!/usr/bin/env python
'''test flight for DCM noise'''

import time, math

def enum(**enums):
    return type('Enum', (), enums)

TestState = enum(INIT=1, FBWA=2, AUTO=3)

from MAVProxy.modules.lib import mp_module

class TestModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(TestModule, self).__init__(mpstate, "test", "test flight")
        self.state = TestState.INIT
        print("Module test loaded")

    def mavlink_packet(self, m):
        '''handle an incoming mavlink packet'''
        if self.state == TestState.INIT:
            if self.status.flightmode == "MANUAL":
                self.mpstate.functions.process_stdin("switch 4")
                self.mpstate.functions.process_stdin("rc 2 1300")
                self.mpstate.functions.process_stdin("rc 3 2000")
                self.mpstate.functions.process_stdin("module load sensors")
                self.mpstate.functions.process_stdin("watch sensors")
                self.mpstate.functions.process_stdin("wp list")
                self.state = TestState.FBWA
        if self.state == TestState.FBWA:
            if self.status.altitude > 60:
                self.mpstate.functions.process_stdin("rc 2 1500")
                self.mpstate.functions.process_stdin("auto")
                self.state = TestState.AUTO

def init(mpstate):
    '''initialise module'''
    return TestModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_tracker
#!/usr/bin/env python
'''
Antenna tracker control module
This module catches MAVLINK_MSG_ID_GLOBAL_POSITION_INT
and sends them to a MAVlink connected antenna tracker running
ardupilot AntennaTracker
Mike McCauley, based on earlier work by Andrew Tridgell
June 2012
'''

import sys, os, time
from MAVProxy.modules.lib import mp_settings
from MAVProxy.modules import mavproxy_map
from pymavlink import mavutil

from MAVProxy.modules.lib import mp_module
from MAVProxy.modules.mavproxy_param import ParamState

# this should be in mavutil.py
mode_mapping_antenna = {
    'MANUAL' : 0,
    'AUTO' : 10,
    'INITIALISING' : 16
    }

class TrackerModule(mp_module.MPModule):
    def __init__(self, mpstate):
        from pymavlink import mavparm
        super(TrackerModule, self).__init__(mpstate, "tracker", "antenna tracker control module")
        self.connection = None
        self.tracker_param = mavparm.MAVParmDict()
        self.pstate = ParamState(self.tracker_param, self.logdir, self.vehicle_name, 'tracker.parm')
        self.tracker_settings = mp_settings.MPSettings(
            [ ('port', str, "/dev/ttyUSB0"),
              ('baudrate', int, 57600),
              ('debug', int, 0)
              ]
            )
        self.add_command('tracker', self.cmd_tracker,
                         "antenna tracker control module",
                         ['<start|arm|disarm|level|mode|position|calpress|mode>',
                          'set (TRACKERSETTING)',
                          'param <set|show|fetch|help> (TRACKERPARAMETER)',
                          'param (TRACKERSETTING)'])
        self.add_completion_function('(TRACKERSETTING)', self.tracker_settings.completion)
        self.add_completion_function('(TRACKERPARAMETER)', self.complete_parameter)

    def complete_parameter(self, text):
        '''complete a tracker parameter'''
        return self.tracker_param.keys()

    def find_connection(self):
        '''find an antenna tracker connection if possible'''
        if self.connection is not None:
            return self.connection
        for m in self.mpstate.mav_master:
            if 'HEARTBEAT' in m.messages:
                if m.messages['HEARTBEAT'].type == mavutil.mavlink.MAV_TYPE_ANTENNA_TRACKER:
                    return m
        return None

    def cmd_tracker(self, args):
        '''tracker command parser'''
        usage = "usage: tracker <start|set|arm|disarm|level|param|mode|position> [options]"
        if len(args) == 0:
            print(usage)
            return
        if args[0] == "start":
            self.cmd_tracker_start()
        elif args[0] == "set":
            self.tracker_settings.command(args[1:])
        elif args[0] == 'arm':
            self.cmd_tracker_arm()
        elif args[0] == 'disarm':
            self.cmd_tracker_disarm()
        elif args[0] == 'level':
            self.cmd_tracker_level()
        elif args[0] == 'param':
            self.cmd_tracker_param(args[1:])
        elif args[0] == 'mode':
            self.cmd_tracker_mode(args[1:])
        elif args[0] == 'position':
            self.cmd_tracker_position(args[1:])
        elif args[0] == 'calpress':
            self.cmd_tracker_calpress(args[1:])
        else:
            print(usage)

    def cmd_tracker_position(self, args):
        '''tracker manual positioning commands'''
        connection = self.find_connection()
        if not connection:
            print("No antenna tracker found")
            return
        positions = [0, 0, 0, 0, 0] # x, y, z, r, buttons. only position[0] (yaw) and position[1] (pitch) are currently used
        for i in range(0, 4):
            if len(args) > i:
                positions[i] = int(args[i]) # default values are 0
        connection.mav.manual_control_send(connection.target_system,
                                           positions[0], positions[1],
                                           positions[2], positions[3],
                                           positions[4])

    def cmd_tracker_calpress(self, args):
        '''calibrate barometer on tracker'''
        connection = self.find_connection()
        if not connection:
            print("No antenna tracker found")
            return
        connection.calibrate_pressure()

    def cmd_tracker_mode(self, args):
        '''set arbitrary mode'''
        connection = self.find_connection()
        if not connection:
            print("No antenna tracker found")
            return
        mode_mapping = connection.mode_mapping()
        if mode_mapping is None:
            print('No mode mapping available')
            return
        if len(args) != 1:
            print('Available modes: ', mode_mapping.keys())
            return
        mode = args[0].upper()
        if mode not in mode_mapping:
            print('Unknown mode %s: ' % mode)
            return
        connection.set_mode(mode_mapping[mode])

    def mavlink_packet(self, m):
        '''handle an incoming mavlink packet from the master vehicle. Relay it to the tracker
        if it is a GLOBAL_POSITION_INT'''
        if m.get_type() in ['GLOBAL_POSITION_INT', 'SCALED_PRESSURE']:
            connection = self.find_connection()
            if not connection:
                return
            if m.get_srcSystem() != connection.target_system:
                connection.mav.send(m)

    def idle_task(self):
        '''called in idle time'''
        if not self.connection:
            return

        # check for a mavlink message from the tracker
        m = self.connection.recv_msg()
        if m is None:
            return

        if self.tracker_settings.debug:
            print(m)

        self.pstate.handle_mavlink_packet(self.connection, m)
        self.pstate.fetch_check(self.connection)

        if self.module('map') is None:
            return

        if m.get_type() == 'GLOBAL_POSITION_INT':
            (self.lat, self.lon, self.heading) = (m.lat*1.0e-7, m.lon*1.0e-7, m.hdg*0.01)
            if self.lat != 0 or self.lon != 0:
                self.module('map').create_vehicle_icon('AntennaTracker', 'red', follow=False, vehicle_type='antenna')
                self.mpstate.map.set_position('AntennaTracker', (self.lat, self.lon), rotation=self.heading)


    def cmd_tracker_start(self):
        if self.tracker_settings.port == None:
            print("tracker port not set")
            return
        print("connecting to tracker %s at %d" % (self.tracker_settings.port,
                                                  self.tracker_settings.baudrate))
        m = mavutil.mavlink_connection(self.tracker_settings.port,
                                       autoreconnect=True,
                                       baud=self.tracker_settings.baudrate)
        if self.logdir:
            m.setup_logfile(os.path.join(self.logdir, 'tracker.tlog'))
        self.connection = m

    def cmd_tracker_arm(self):
        '''Enable the servos in the tracker so the antenna will move'''
        if not self.connection:
            print("tracker not connected")
            return
        self.connection.arducopter_arm()

    def cmd_tracker_disarm(self):
        '''Disable the servos in the tracker so the antenna will not move'''
        if not self.connection:
            print("tracker not connected")
            return
        self.connection.arducopter_disarm()

    def cmd_tracker_level(self):
        '''Calibrate the accelerometers. Disarm and move the antenna level first'''
        if not self.connection:
            print("tracker not connected")
            return
        self.connection.calibrate_level()

    def cmd_tracker_param(self, args):
        '''Parameter commands'''
        if not self.connection:
            print("tracker not connected")
            return
        self.pstate.handle_command(self.connection, args)

def init(mpstate):
    '''initialise module'''
    return TrackerModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_tuneopt
#!/usr/bin/env python
'''tune command handling'''

import time, os

from MAVProxy.modules.lib import mp_module

tune_options = {
    'None':             '0',
    'StabRollPitchkP':  '1',
    'RateRollPitchkP':  '4',
    'RateRollPitchkI':  '6',
    'RateRollPitchkD':  '21',
    'StabYawkP':        '3',
    'RateYawkP':        '6',
    'RateYawkD':        '26',
    'AltitudeHoldkP':   '14',
    'ThrottleRatekP':   '7',
    'ThrottleRatekD':   '37',
    'ThrottleAccelkP':  '34',
    'ThrottleAccelkI':  '35',
    'ThrottleAccelkD':  '36',
    'LoiterPoskP':      '12',
    'LoiterRatekP':     '22',
    'LoiterRatekI':     '28',
    'LoiterRatekD':     '29',
    'WPSpeed':          '10',
    'AcroRollPitch kP': '25',
    'AcroYawkP':        '40',
    'RelayOnOff':       '9',
    'HeliExtGyro':      '13',
    'OFLoiterkP':       '17',
    'OFLoiterkI':       '18',
    'OFLoiterkD':       '19',
    'AHRSYawkP':        '30',
    'AHRSkP':           '31',
    'INAV_TC':          '32',
    'Declination':      '38',
    'CircleRate':       '39',
    'SonarGain':       '41',
}

class TuneoptModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(TuneoptModule, self).__init__(mpstate, "tuneopt", "tuneopt command handling")
        self.add_command('tuneopt', self.cmd_tuneopt,  'Select option for Tune Pot on Channel 6 (quadcopter only)')

    def tune_show(self):
        opt_num = str(int(self.get_mav_param('TUNE')))
        option = None
        for k in tune_options.keys():
            if opt_num == tune_options[k]:
                option = k
                break
        else:
            print("TUNE is currently set to unknown value " + opt_num)
            return
        low = self.get_mav_param('TUNE_LOW')
        high = self.get_mav_param('TUNE_HIGH')
        print("TUNE is currently set to %s LOW=%f HIGH=%f" % (option, low/1000, high/1000))

    def tune_option_validate(self, option):
        for k in tune_options:
            if option.upper() == k.upper():
                return k
        return None

    # TODO: Check/show the limits of LOW and HIGH
    def cmd_tuneopt(self, args):
        '''Select option for Tune Pot on Channel 6 (quadcopter only)'''
        usage = "usage: tuneopt <set|show|reset|list>"
        if self.mpstate.vehicle_type != 'copter':
            print("This command is only available for copter")
            return
        if len(args) < 1:
            print(usage)
            return
        if args[0].lower() == 'reset':
            self.param_set('TUNE', '0')
        elif args[0].lower() == 'set':
            if len(args) < 4:
                print('Usage: tuneopt set OPTION LOW HIGH')
                return
            option = self.tune_option_validate(args[1])
            if not option:
                print('Invalid Tune option: ' + args[1])
                return
            low = args[2]
            high = args[3]
            self.param_set('TUNE', tune_options[option])
            self.param_set('TUNE_LOW', float(low) * 1000)
            self.param_set('TUNE_HIGH', float(high) * 1000)
        elif args[0].lower() == 'show':
            self.tune_show()
        elif args[0].lower() == 'list':
            print("Options available:")
            for s in sorted(tune_options.keys()):
                print('  ' + s)
        else:
            print(usage)

def init(mpstate):
    '''initialise module'''
    return TuneoptModule(mpstate)

########NEW FILE########
__FILENAME__ = mavproxy_wp
#!/usr/bin/env python
'''waypoint command handling'''

import time, os, fnmatch
from pymavlink import mavutil, mavwp
from MAVProxy.modules.lib import mp_module
from MAVProxy.modules.lib.mp_menu import *

class WPModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(WPModule, self).__init__(mpstate, "wp", "waypoint handling", public = True)
        self.wp_op = None
        self.wp_save_filename = None
        self.wploader = mavwp.MAVWPLoader()
        self.loading_waypoints = False
        self.loading_waypoint_lasttime = time.time()
        self.last_waypoint = 0
        self.wp_period = mavutil.periodic_event(0.5)
        self.add_command('wp', self.cmd_wp,       'waypoint management',
                         ["<list|clear|move|remove|loop|set>",
                          "<load|update|save> (FILENAME)"])

        if self.continue_mode and self.logdir != None:
            waytxt = os.path.join(mpstate.status.logdir, 'way.txt')
            if os.path.exists(waytxt):
                self.wploader.load(waytxt)
                print("Loaded waypoints from %s" % waytxt)

        self.menu_added_console = False
        self.menu_added_map = False
        self.menu = MPMenuSubMenu('Mission',
                                  items=[MPMenuItem('Clear', 'Clear', '# wp clear'),
                                         MPMenuItem('List', 'List', '# wp list'),
                                         MPMenuItem('Load', 'Load', '# wp load ',
                                                    handler=MPMenuCallFileDialog(flags=wx.FD_OPEN,
                                                                                 title='Mission Load',
                                                                                 wildcard='*.txt')),
                                         MPMenuItem('Save', 'Save', '# wp save ',
                                                    handler=MPMenuCallFileDialog(flags=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT,
                                                                                 title='Mission Save',
                                                                                 wildcard='*.txt')),
                                         MPMenuItem('Draw', 'Draw', '# wp draw ',
                                                    handler=MPMenuCallTextDialog(title='Mission Altitude (m)',
                                                                                 default=100)),
                                         MPMenuItem('Loop', 'Loop', '# wp loop')])


    def mavlink_packet(self, m):
        '''handle an incoming mavlink packet'''
        mtype = m.get_type()
        if mtype in ['WAYPOINT_COUNT','MISSION_COUNT']:
            if self.wp_op is None:
                self.console.error("No waypoint load started")
            else:
                self.wploader.clear()
                self.wploader.expected_count = m.count
                self.console.writeln("Requesting %u waypoints t=%s now=%s" % (m.count,
                                                                                 time.asctime(time.localtime(m._timestamp)),
                                                                                 time.asctime()))
                self.master.waypoint_request_send(0)

        elif mtype in ['WAYPOINT', 'MISSION_ITEM'] and self.wp_op != None:
            if m.seq > self.wploader.count():
                self.console.writeln("Unexpected waypoint number %u - expected %u" % (m.seq, self.wploader.count()))
            elif m.seq < self.wploader.count():
                # a duplicate
                pass
            else:
                self.wploader.add(m)
            if m.seq+1 < self.wploader.expected_count:
                self.master.waypoint_request_send(m.seq+1)
            else:
                if self.wp_op == 'list':
                    for i in range(self.wploader.count()):
                        w = self.wploader.wp(i)
                        print("%u %u %.10f %.10f %f p1=%.1f p2=%.1f p3=%.1f p4=%.1f cur=%u auto=%u" % (
                            w.command, w.frame, w.x, w.y, w.z,
                            w.param1, w.param2, w.param3, w.param4,
                            w.current, w.autocontinue))
                    if self.logdir != None:
                        waytxt = os.path.join(self.logdir, 'way.txt')
                        self.save_waypoints(waytxt)
                        print("Saved waypoints to %s" % waytxt)
                elif self.wp_op == "save":
                    self.save_waypoints(self.wp_save_filename)
                self.wp_op = None

        elif mtype in ["WAYPOINT_REQUEST", "MISSION_REQUEST"]:
            self.process_waypoint_request(m, self.master)

        elif mtype in ["WAYPOINT_CURRENT", "MISSION_CURRENT"]:
            if m.seq != self.last_waypoint:
                self.last_waypoint = m.seq
                self.say("waypoint %u" % m.seq,priority='message')



    def idle_task(self):
        '''handle missing waypoints'''
        if self.wp_period.trigger():
            # cope with packet loss fetching mission
            if self.master.time_since('MISSION_ITEM') >= 2 and self.wploader.count() < getattr(self.wploader,'expected_count',0):
                seq = self.wploader.count()
                print("re-requesting WP %u" % seq)
                self.master.waypoint_request_send(seq)
        if not self.menu_added_console and self.module('console') is not None:
            self.menu_added_console = True
            self.module('console').add_menu(self.menu)
        if not self.menu_added_map and self.module('map') is not None:
            self.menu_added_map = True
            self.module('map').add_menu(self.menu)

    def process_waypoint_request(self, m, master):
        '''process a waypoint request from the master'''
        if (not self.loading_waypoints or
            time.time() > self.loading_waypoint_lasttime + 10.0):
            self.loading_waypoints = False
            self.console.error("not loading waypoints")
            return
        if m.seq >= self.wploader.count():
            self.console.error("Request for bad waypoint %u (max %u)" % (m.seq, self.wploader.count()))
            return
        wp = self.wploader.wp(m.seq)
        wp.target_system = self.target_system
        wp.target_component = self.target_component
        self.master.mav.send(self.wploader.wp(m.seq))
        self.loading_waypoint_lasttime = time.time()
        self.console.writeln("Sent waypoint %u : %s" % (m.seq, self.wploader.wp(m.seq)))
        if m.seq == self.wploader.count() - 1:
            self.loading_waypoints = False
            self.console.writeln("Sent all %u waypoints" % self.wploader.count())

    def send_all_waypoints(self):
        '''send all waypoints to vehicle'''
        self.master.waypoint_clear_all_send()
        if self.wploader.count() == 0:
            return
        self.loading_waypoints = True
        self.loading_waypoint_lasttime = time.time()
        self.master.waypoint_count_send(self.wploader.count())

    def load_waypoints(self, filename):
        '''load waypoints from a file'''
        self.wploader.target_system = self.target_system
        self.wploader.target_component = self.target_component
        try:
            self.wploader.load(filename)
        except Exception as msg:
            print("Unable to load %s - %s" % (filename, msg))
            return
        print("Loaded %u waypoints from %s" % (self.wploader.count(), filename))
        self.send_all_waypoints()

    def update_waypoints(self, filename, wpnum):
        '''update waypoints from a file'''
        self.wploader.target_system = self.target_system
        self.wploader.target_component = self.target_component
        try:
            self.wploader.load(filename)
        except Exception as msg:
            print("Unable to load %s - %s" % (filename, msg))
            return
        if self.wploader.count() == 0:
            print("No waypoints found in %s" % filename)
            return
        if wpnum == -1:
            print("Loaded %u updated waypoints from %s" % (self.wploader.count(), filename))
        elif wpnum >= self.wploader.count():
            print("Invalid waypoint number %u" % wpnum)
            return
        else:
            print("Loaded updated waypoint %u from %s" % (wpnum, filename))

        self.loading_waypoints = True
        self.loading_waypoint_lasttime = time.time()
        if wpnum == -1:
            start = 0
            end = self.wploader.count()-1
        else:
            start = wpnum
            end = wpnum
        self.master.mav.mission_write_partial_list_send(self.target_system,
                                                             self.target_component,
                                                             start, end)

    def save_waypoints(self, filename):
        '''save waypoints to a file'''
        try:
            self.wploader.save(filename)
        except Exception as msg:
            print("Failed to save %s - %s" % (filename, msg))
            return
        print("Saved %u waypoints to %s" % (self.wploader.count(), filename))

    def wp_draw_callback(self, points):
        '''callback from drawing waypoints'''
        if len(points) < 3:
            return
        from MAVProxy.modules.lib import mp_util
        home = self.wploader.wp(0)
        self.wploader.clear()
        self.wploader.target_system = self.target_system
        self.wploader.target_component = self.target_component
        self.wploader.add(home)
        for p in points:
            self.wploader.add_latlonalt(p[0], p[1], self.settings.wpalt)
        self.send_all_waypoints()

    def wp_loop(self):
        '''close the loop on a mission'''
        loader = self.wploader
        if loader.count() < 2:
            print("Not enough waypoints (%u)" % loader.count())
            return
        wp = loader.wp(loader.count()-2)
        if wp.command == mavutil.mavlink.MAV_CMD_DO_JUMP:
            print("Mission is already looped")
            return
        wp = mavutil.mavlink.MAVLink_mission_item_message(0, 0, 0, 0, mavutil.mavlink.MAV_CMD_DO_JUMP,
                                                          0, 1, 1, -1, 0, 0, 0, 0, 0)
        loader.add(wp)
        loader.add(loader.wp(1))
        self.loading_waypoints = True
        self.loading_waypoint_lasttime = time.time()
        self.master.waypoint_count_send(self.wploader.count())
        print("Closed loop on mission")

    def set_home_location(self):
        '''set home location from last map click'''
        try:
            latlon = self.module('map').click_position
        except Exception:
            print("No map available")
            return
        lat = float(latlon[0])
        lon = float(latlon[1])
        if self.wploader.count() == 0:
            self.wploader.add_latlonalt(lat, lon, 0)
        w = self.wploader.wp(0)
        w.x = lat
        w.y = lon
        self.wploader.set(w, 0)
        self.loading_waypoints = True
        self.loading_waypoint_lasttime = time.time()
        self.master.mav.mission_write_partial_list_send(self.target_system,
                                                             self.target_component,
                                                             0, 0)


    def cmd_wp_move(self, args):
        '''handle wp move'''
        if len(args) != 1:
            print("usage: wp move WPNUM")
            return
        idx = int(args[0])
        if idx < 1 or idx > self.wploader.count():
            print("Invalid wp number %u" % idx)
            return
        try:
            latlon = self.module('map').click_position
        except Exception:
            print("No map available")
            return
        if latlon is None:
            print("No map click position available")
            return
        wp = self.wploader.wp(idx)
        (lat, lon) = latlon
        if getattr(self.console, 'ElevationMap', None) is not None:
            alt1 = self.console.ElevationMap.GetElevation(lat, lon)
            alt2 = self.console.ElevationMap.GetElevation(wp.x, wp.y)
            wp.z += alt1 - alt2
        wp.x = lat
        wp.y = lon

        wp.target_system    = self.target_system
        wp.target_component = self.target_component
        self.loading_waypoints = True
        self.loading_waypoint_lasttime = time.time()
        self.master.mav.mission_write_partial_list_send(self.target_system,
                                                        self.target_component,
                                                        idx, idx)
        self.wploader.set(wp, idx)
        print("Moved WP %u to %f, %f at %.1fm" % (idx, lat, lon, wp.z))

    def cmd_wp_remove(self, args):
        '''handle wp remove'''
        if len(args) != 1:
            print("usage: wp remove WPNUM")
            return
        idx = int(args[0])
        if idx < 0 or idx >= self.wploader.count():
            print("Invalid wp number %u" % idx)
            return
        wp = self.wploader.wp(idx)
        self.wploader.remove(wp)
        self.send_all_waypoints()
        print("Removed WP %u" % idx)

    def cmd_wp(self, args):
        '''waypoint commands'''
        usage = "usage: wp <list|load|update|save|set|clear|loop|remove|move>"
        if len(args) < 1:
            print(usage)
            return

        if args[0] == "load":
            if len(args) != 2:
                print("usage: wp load <filename>")
                return
            self.load_waypoints(args[1])
        elif args[0] == "update":
            if len(args) < 2:
                print("usage: wp update <filename> <wpnum>")
                return
            if len(args) == 3:
                wpnum = int(args[2])
            else:
                wpnum = -1
            self.update_waypoints(args[1], wpnum)
        elif args[0] == "list":
            self.wp_op = "list"
            self.master.waypoint_request_list_send()
        elif args[0] == "save":
            if len(args) != 2:
                print("usage: wp save <filename>")
                return
            self.wp_save_filename = args[1]
            self.wp_op = "save"
            self.master.waypoint_request_list_send()
        elif args[0] == "savelocal":
            if len(args) != 2:
                print("usage: wp savelocal <filename>")
                return
            self.wploader.save(args[1])
        elif args[0] == "show":
            if len(args) != 2:
                print("usage: wp show <filename>")
                return
            self.wploader.load(args[1])
        elif args[0] == "move":
            self.cmd_wp_move(args[1:])
        elif args[0] == "remove":
            self.cmd_wp_remove(args[1:])
        elif args[0] == "set":
            if len(args) != 2:
                print("usage: wp set <wpindex>")
                return
            self.master.waypoint_set_current_send(int(args[1]))
        elif args[0] == "clear":
            self.master.waypoint_clear_all_send()
            self.wploader.clear()
        elif args[0] == "draw":
            if not 'draw_lines' in self.mpstate.map_functions:
                print("No map drawing available")
                return
            if self.wploader.count() == 0:
                print("Need home location - refresh waypoints")
                return
            if len(args) > 1:
                self.settings.wpalt = int(args[1])
            self.mpstate.map_functions['draw_lines'](self.wp_draw_callback)
            print("Drawing waypoints on map at altitude %d" % self.settings.wpalt)
        elif args[0] == "sethome":
            self.set_home_location()
        elif args[0] == "loop":
            self.wp_loop()
        else:
            print(usage)

    def fetch(self):
        """Download wpts from vehicle (this operation is public to support other modules)"""
        if self.wp_op is None:  # If we were already doing a list or save, just restart the fetch without changing the operation
            self.wp_op = "fetch"
        self.master.waypoint_request_list_send()

def init(mpstate):
    '''initialise module'''
    return WPModule(mpstate)

########NEW FILE########
__FILENAME__ = mavflightview
#!/usr/bin/env python

'''
view a mission log on a map
'''

import sys, time, os

from pymavlink import mavutil, mavwp, mavextra
from MAVProxy.modules.mavproxy_map import mp_slipmap, mp_tile
from MAVProxy.modules.lib import mp_util
import functools

try:
    import cv2.cv as cv
except ImportError:
    import cv

from optparse import OptionParser
parser = OptionParser("mavflightview.py [options]")
parser.add_option("--service", default="MicrosoftSat", help="tile service")
parser.add_option("--mode", default=None, help="flight mode")
parser.add_option("--condition", default=None, help="conditional check on log")
parser.add_option("--mission", default=None, help="mission file (defaults to logged mission)")
parser.add_option("--imagefile", default=None, help="output to image file")
parser.add_option("--flag", default=[], type='str', action='append', help="flag positions")
parser.add_option("--rawgps", action='store_true', default=False, help="use GPS_RAW_INT")
parser.add_option("--rawgps2", action='store_true', default=False, help="use GPS2_RAW")
parser.add_option("--dualgps", action='store_true', default=False, help="use GPS_RAW_INT and GPS2_RAW")
parser.add_option("--ekf", action='store_true', default=False, help="use EKF1 pos")
parser.add_option("--debug", action='store_true', default=False, help="show debug info")
parser.add_option("--multi", action='store_true', default=False, help="show multiple flights on one map")

(opts, args) = parser.parse_args()

def create_map(title):
    '''create map object'''

def pixel_coords(latlon, ground_width=0, mt=None, topleft=None, width=None):
    '''return pixel coordinates in the map image for a (lat,lon)'''
    (lat,lon) = (latlon[0], latlon[1])
    return mt.coord_to_pixel(topleft[0], topleft[1], width, ground_width, lat, lon)

def create_imagefile(filename, latlon, ground_width, path_objs, mission_obj, width=600, height=600):
    '''create path and mission as an image file'''
    mt = mp_tile.MPTile(service=opts.service)

    map_img = mt.area_to_image(latlon[0], latlon[1],
                               width, height, ground_width)
    while mt.tiles_pending() > 0:
        print("Waiting on %u tiles" % mt.tiles_pending())
        time.sleep(1)
    map_img = mt.area_to_image(latlon[0], latlon[1],
                               width, height, ground_width)
    # a function to convert from (lat,lon) to (px,py) on the map
    pixmapper = functools.partial(pixel_coords, ground_width=ground_width, mt=mt, topleft=latlon, width=width)
    for path_obj in path_objs:
        path_obj.draw(map_img, pixmapper, None)
    if mission_obj is not None:
        mission_obj.draw(map_img, pixmapper, None)
    cv.CvtColor(map_img, map_img, cv.CV_BGR2RGB)
    cv.SaveImage(filename, map_img)

colourmap = {
    'MANUAL'    : (255,   0,   0),
    'AUTO'      : (  0, 255,   0),
    'LOITER'    : (  0,   0, 255),
    'FBWA'      : (255, 100,   0),
    'RTL'       : (255,   0, 100),
    'STABILIZE' : (100, 255,   0),
    'LAND'      : (  0, 255, 100),
    'STEERING'  : (100,   0, 255),
    'HOLD'      : (  0, 100, 255),
    'ALT_HOLD'  : (255, 100, 100),
    'CIRCLE'    : (100, 255, 100),
    'GUIDED'    : (100, 100, 255),
    'ACRO'      : (255, 255,   0),
    'CRUISE'    : (0,   255, 255)
    }


def mavflightview(filename):
    print("Loading %s ..." % filename)
    mlog = mavutil.mavlink_connection(filename)
    wp = mavwp.MAVWPLoader()
    if opts.mission is not None:
        wp.load(opts.mission)
    path = [[]]
    types = ['MISSION_ITEM']
    if opts.rawgps:
        types.extend(['GPS', 'GPS_RAW_INT'])
    if opts.rawgps2:
        types.extend(['GPS2_RAW','GPS2'])
    if opts.dualgps:
        types.extend(['GPS2_RAW','GPS2', 'GPS_RAW_INT', 'GPS'])
    if opts.ekf:
        types.extend(['EKF1'])
    if len(types) == 1:
        types.extend(['GPS','GLOBAL_POSITION_INT'])
    print("Looking for types %s" % str(types))
    while True:
        try:
            m = mlog.recv_match(type=types)
            if m is None:
                break
        except Exception:
            break
        if m.get_type() == 'MISSION_ITEM':
            wp.set(m, m.seq)            
            continue
        if not mlog.check_condition(opts.condition):
            continue
        if opts.mode is not None and mlog.flightmode.lower() != opts.mode.lower():
            continue
        if m.get_type() in ['GPS','GPS2']:
            status = getattr(m, 'Status', None)
            if status is None:
                status = getattr(m, 'FixType', None)
                if status is None:
                    print("Can't find status on GPS message")
                    print(m)
                    break
            if status < 2:
                continue
            # flash log
            lat = m.Lat
            lng = getattr(m, 'Lng', None)
            if lng is None:
                lng = getattr(m, 'Lon', None)
                if lng is None:
                    print("Can't find longitude on GPS message")
                    print(m)
                    break                    
        elif m.get_type() == 'EKF1':
            pos = mavextra.ekf1_pos(m)
            if pos is None:
                continue
            (lat, lng) = pos            
        else:
            lat = m.lat * 1.0e-7
            lng = m.lon * 1.0e-7
        instance = 0
        if opts.dualgps and m.get_type() in ['GPS2_RAW', 'GPS2']:
            instance = 1
        if m.get_type() == 'EKF1':
            if opts.dualgps:
                instance = 2
            else:
                instance = 1
        if lat != 0 or lng != 0:
            if getattr(mlog, 'flightmode','') in colourmap:
                colour = colourmap[mlog.flightmode]
                (r,g,b) = colour
                (r,g,b) = (r+instance*50,g+instance*50,b+instance*50)
                if r > 255:
                    r = 205
                if g > 255:
                    g = 205
                if b > 255:
                    b = 205
                colour = (r,g,b)
                point = (lat, lng, colour)
            else:
                point = (lat, lng)
            while instance >= len(path):
                path.append([])
            path[instance].append(point)
    if len(path[0]) == 0:
        print("No points to plot")
        return
    bounds = mp_util.polygon_bounds(path[0])
    (lat, lon) = (bounds[0]+bounds[2], bounds[1])
    (lat, lon) = mp_util.gps_newpos(lat, lon, -45, 50)
    ground_width = mp_util.gps_distance(lat, lon, lat-bounds[2], lon+bounds[3])
    while (mp_util.gps_distance(lat, lon, bounds[0], bounds[1]) >= ground_width-20 or
           mp_util.gps_distance(lat, lon, lat, bounds[1]+bounds[3]) >= ground_width-20):
        ground_width += 10

    path_objs = []
    for i in range(len(path)):
        if len(path[i]) != 0:
            path_objs.append(mp_slipmap.SlipPolygon('FlightPath[%u]-%s' % (i,filename), path[i], layer='FlightPath',
                                                    linewidth=2, colour=(255,0,180)))
    mission = wp.polygon()
    if len(mission) > 1:
        mission_obj = mp_slipmap.SlipPolygon('Mission-%s' % filename, wp.polygon(), layer='Mission',
                                             linewidth=2, colour=(255,255,255))
    else:
        mission_obj = None

    if opts.imagefile:
        create_imagefile(opts.imagefile, (lat,lon), ground_width, path_objs, mission_obj)
    else:
        global multi_map
        if opts.multi and multi_map is not None:
            map = multi_map
        else:
            map = mp_slipmap.MPSlipMap(title=filename,
                                       service=opts.service,
                                       elevation=True,
                                       width=600,
                                       height=600,
                                       ground_width=ground_width,
                                       lat=lat, lon=lon,
                                       debug=opts.debug)
        if opts.multi:
            multi_map = map
        for path_obj in path_objs:
            map.add_object(path_obj)
        if mission_obj is not None:
            map.add_object(mission_obj)

        for flag in opts.flag:
            a = flag.split(',')
            lat = a[0]
            lon = a[1]
            icon = 'flag.png'
            if len(a) > 2:
                icon = a[2] + '.png'
            icon = map.icon(icon)
            map.add_object(mp_slipmap.SlipIcon('icon - %s' % str(flag), (float(lat),float(lon)), icon, layer=3, rotation=0, follow=False))

if len(args) < 1:
    print("Usage: mavflightview.py [options] <LOGFILE...>")
    sys.exit(1)

if __name__ == "__main__":
    if opts.multi:
        multi_map = None

    for f in args:
        mavflightview(f)

########NEW FILE########
