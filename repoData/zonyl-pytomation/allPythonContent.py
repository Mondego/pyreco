__FILENAME__ = graburns
import select

from pytomation.interfaces import UPB, InsteonPLM, TCP, Serial, Stargate, W800rf32, \
                                    NamedPipe, StateInterface, Command, HTTPServer, \
                                    HTTP, HW_Thermostat, WeMo, InsteonPLM2
from pytomation.devices import Motion, Door, Light, Location, InterfaceDevice, \
                                Photocell, Generic, StateDevice, State, Attribute, \
                                Room, Thermostat, XMPP_Client

#from pytomation.common.system import *

###################### INTERFACE CONFIG #########################
web = HTTPServer()

xmpp = XMPP_Client(id='pytomation@sharpee.com', password='password', server='talk.google.com', port=5222)

upb = UPB(Serial('/dev/ttyMI0', 4800))

#insteon = InsteonPLM(TCP('192.168.13.146', 9761))
insteon = InsteonPLM(Serial('/dev/ttyMI1', 19200, xonxoff=False))

w800 = W800rf32(Serial('/dev/ttyMI3', 4800)) 

sg = Stargate(Serial('/dev/ttyMI4', 9600))
# invert the DIO channels for these contact sensors
sg.dio_invert(1)
sg.dio_invert(2)
sg.dio_invert(3)
sg.dio_invert(4)
sg.dio_invert(5)
sg.dio_invert(6)
sg.dio_invert(7)
sg.dio_invert(8)
sg.dio_invert(9)
sg.dio_invert(10)
sg.dio_invert(11)
sg.dio_invert(12)

# My camera motion software will echo a "motion" to this pipe.
pipe_front_yard_motion = StateInterface(NamedPipe('/tmp/front_yard_motion'))

thermostat_upstairs = Thermostat(
                                 devices=HW_Thermostat(HTTP(host='192.168.13.211'), 
                                                       poll=60), 
                                 name='Thermostat Upstairs',
                                 automatic_delta=2,
                                 time = (
                                             {
                                              Attribute.TIME: (0, 30, 5,'*','*', (1,2,3,4,5)),
                                             Attribute.COMMAND: (Command.LEVEL, 72),
                                             },
                                         )
                                 )

thermostat_downstairs = Thermostat(
                                   devices=HW_Thermostat(HTTP(host='192.168.13.210'),
                                                         poll=60), 
                                   name='Thermostat Downstairs',
                                   automatic_delta=2
                                   )

###################### DEVICE CONFIG #########################

#doors
d_foyer = Door('D1', sg, name='Foyer Door')
d_laundry = Door('D2', sg, name='Laundry Door')
d_garage = Door('D3', sg, name='Garage Door')
#d_garage_overhead = Door((49, 38, 'L'), upb, name='Garage Overhead')
#d_garage_overhead = Door("19.bc.06", insteon, name='Garage Overhead')
d_garage_overhead = Door("23.d2.be", insteon, name='Garage Overhead')
d_porch = Door('D5', sg, name='Porch Door')
d_basement = Door('D6', sg, name='Basement')
d_master = Door('D4', sg, name='Master')
d_crawlspace = Door('D10', sg, name='Crawlspace Door')
d_pool = Door('D11', sg, name='Pool Door')

relay_garage_overhead = Generic(address="23.d2.be",
                                devices=insteon, 
                                name='Garage Overhead Relay')

xmpp.add_device(d_garage)
xmpp.add_device(d_garage_overhead)
xmpp.mapped(command=Command.OPEN,
            mapped=(Command.MESSAGE, 'jason@sharpee.com', 'Garage door was opened!'),
            )

#general input
i_laundry_security = Generic('D7', sg, name='Laundry Keypad')
i_master_security = Generic('D9', sg, name='Master Keypad')
i_laser_perimeter = Generic('D12', sg, name='Laser Perimeter')

#motion
# Motion sensor is hardwired and immediate OFF.. Want to give it some time to still detect motion right after
m_family = Motion(address='D8', 
                  devices=(sg),
                  delay={
                         Attribute.COMMAND: Command.STILL,
                         Attribute.SECS: 30,
                         },
                  name='Family Motion'
                  )

m_front_porch = Motion(address='F1',
                devices=w800,
                name='Front Porch Motion',
                )
ph_front_porch = Photocell(address='F2',
                devices=w800)
m_front_garage = Motion(address='F3',
                devices=w800,
                name='Front Garage Motion')
ph_front_garage = Photocell(address='F4',
                devices=w800)
m_front_driveway = Motion(address='F5',
                devices=w800,
                name='Front Driveway Motion')
ph_front_driveway = Photocell(address='F6',
                devices=w800)
m_front_camera = Motion(address=None,
                      devices=pipe_front_yard_motion)

m_garage = Motion(address='G1',
                  devices=w800,
                  name='Garage Motion')
ph_garage = Photocell(address='G2',
                  devices=w800)

m_utility = Motion(address='G3',
                  devices=w800,
                  name='Utility Motion')
ph_utility = Photocell(address='G4',
                  devices=w800)

m_breakfast = Motion(address='G7',
                  devices=w800,
                  name='Breakfast Motion')
ph_breakfast = Photocell(address='G8',
                  devices=w800)

m_foyer = Motion(address='G5',
                  devices=w800,
                  name='Foyer Motion')
ph_foyer = Photocell(address='G6',
                  devices=w800)

m_den = Motion(address='G9',
                  devices=w800,
                  name='Den Motion')
ph_den = Photocell(address='GA',
                  devices=w800)

m_kitchen = Motion(address='GB',
                  devices=w800,
                  name='Kitchen Motion')
ph_kitchen = Photocell(address='GC',
                  devices=w800)

#keypads
k_master = Generic(
                           address=(49,8),
                           devices=(upb,),
                           name='Master Bed Keypad'
                           )

#Scenes
#s_all_indoor_off = InterfaceDevice(
#                 address=(49,4,'L'),
#                 devices=(upb,),
#                 )

s_all_indoor_off = StateDevice()

#photocell
ph_standard = Location('35.2269', '-80.8433', 
                       tz='US/Eastern', 
                       mode=Location.MODE.STANDARD, 
                       is_dst=True,
                       name='Standard Photocell')
ph_civil = Location('35.2269', '-80.8433', 
                    tz='US/Eastern', 
                    mode=Location.MODE.CIVIL, 
                    is_dst=True,
                    name='Civil Photocell')

# Rooms
r_foyer = Room(name='Foyer', devices=(m_foyer))
r_den = Room(name='Den', devices=(m_den, r_foyer))
r_family = Room(name='Family', 
		devices=(m_family, r_foyer),
		trigger={ Attribute.COMMAND: Command.OCCUPY,
			  Attribute.MAPPED: Command.VACATE,
			  Attribute.SECS: 2*60*60,
			},
		)
r_kitchen = Room(name='Kitchen', devices=(m_kitchen, r_foyer))
r_foyer.add_device(r_den)
r_foyer.add_device(r_family)
r_foyer.add_device(r_kitchen)
r_breakfast = Room(name='Breakfast', devices=(m_breakfast, r_kitchen))
r_utility = Room(name='Utility', devices=(m_utility, r_kitchen, d_laundry))
r_kitchen.add_device(r_breakfast)
r_kitchen.add_device(r_utility)
r_garage = Room(name='Garage', devices=(m_garage, r_utility, d_laundry, d_garage, d_garage_overhead))
r_utility.add_device(r_garage)

#lights
# Turn on the foyer light at night when either the door is opened or family PIR is tripped.
l_foyer = Light(
                address="24.a9.14",
                devices=(insteon, d_foyer,
                         m_foyer,
                         ph_standard),
                 ignore={
                         Attribute.COMMAND: (Command.DARK, Command.STILL,)
                         },
                 time={
                       Attribute.TIME: '11:59pm',
                       Attribute.COMMAND: Command.OFF
                       },
                 mapped={
                         Attribute.COMMAND: (
                                             Command.MOTION, Command.OPEN,
                                              Command.CLOSE, Command.LIGHT,
                                              ),
                         Attribute.MAPPED: Command.OFF,
                         Attribute.SECS: 15*60,
                         },
		 name='Foyer Light',
                )

l_front_porch = Light(
                      address="24.9d.55",
                      devices=(insteon, d_foyer, m_front_porch, m_front_camera, ph_standard),
                      initial=ph_standard,
                      delay=({
                             Attribute.COMMAND: Command.OFF,
                             Attribute.SECS: 10*60*60,
                             },
                             {
                              Attribute.COMMAND: Command.OFF,
                              Attribute.SECS: 0,
                              Attribute.SOURCE: (ph_standard, web,)
                              },
                             ),
                       idle={
                             Attribute.MAPPED:(Command.LEVEL, 30),
                             Attribute.SECS: 10*60,
                             },
                       time={
                             Attribute.COMMAND: Command.OFF,
                             Attribute.TIME: '11:59pm',
                             },
                      name='Front Porch Light'
                      )


l_front_flood = Light(
                      address="24.6f.17", 
                      devices=(insteon, d_garage, d_garage_overhead, 
                               d_foyer, m_front_garage, m_front_camera, ph_standard),
                      delay=({
                             Attribute.COMMAND: Command.OFF,
                             Attribute.SECS: 10*60,
                             },
                             {
                              Attribute.COMMAND: Command.OFF,
                              Attribute.SECS: 0,
                              Attribute.SOURCE: (ph_standard, web,)
                              },
                             ),
                       idle={
                             Attribute.MAPPED:(Command.LEVEL, 30),
                             Attribute.SECS: 5*60,
                             },
                       time={
                             Attribute.COMMAND: Command.OFF,
                             Attribute.TIME: '11:59pm',
                             },
                      trigger={
                               Attribute.COMMAND: Command.ON,
                               Attribute.MAPPED: Command.OFF,
                               Attribute.SECS: 10*60,
                               },
                      name='Front Flood Light'
                      )

# Cron Format
#  secs=allMatch, min=allMatch, hour=allMatch, day=allMatch, month=allMatch, dow=allMatch
l_front_outlet = Light(
                      address=(49, 21), 
                      devices=(upb, ph_standard),
                      initial=ph_standard,
                        time = (
                            {
                             Attribute.TIME: '10:30pm',
                            Attribute.COMMAND: Command.OFF,
                            },
                        ),
                      name='Front Outlet Light'
                      )

l_front_garage = Light(
                      address="24.9d.7c", 
                      devices=(insteon, d_garage, d_garage_overhead, 
                               m_front_garage, m_front_camera, ph_standard),
                      delay=({
                             Attribute.COMMAND: Command.OFF,
                             Attribute.SECS: 10*60*60,
                             },
                             {
                              Attribute.COMMAND: Command.OFF,
                              Attribute.SECS: 0,
                              Attribute.SOURCE: (ph_standard, web,)
                              },
                             ),
                       idle={
                             Attribute.MAPPED:(Command.LEVEL, 30),
                             Attribute.SECS: 10*60,
                             },
                       time={
                             Attribute.COMMAND: Command.OFF,
                             Attribute.TIME: '11:59pm',
                             },
                      name='Front Garage Light',
                      )

l_garage = Light(
	              address='20.8b.40',    
                      devices=(insteon, m_garage, d_garage, d_garage_overhead, d_laundry, 
                               #ph_standard, 
                               s_all_indoor_off),
#                      trigger={
#                               Attribute.COMMAND: Command.ON,
#                               Attribute.MAPPED: Command.OFF,
#                               Attribute.SECS: 5*60,
#                               },
                      delay=(
                             {
                                 Attribute.COMMAND: Command.OFF,
                                 Attribute.SECS: 5*60,
                             },
                             {
                                    Attribute.COMMAND: Command.OFF,
                                    Attribute.SECS: 0,
                                    Attribute.SOURCE: web,
                             },
                             ),
                       time={
                             Attribute.COMMAND: Command.OFF,
                             Attribute.TIME: '11:59pm',
                             },
                      name='Garage Light',
                      sync=True, #Un-reliable connection this far
                      )

l_family_lamp = Light(
                address=(49, 6), 
#                devices=(upb, ph_standard, r_family),
                devices=(upb, ph_standard),
                mapped={
                        Attribute.COMMAND: (Command.MOTION, Command.LIGHT),
                        Attribute.TARGET: Command.OFF,
                        Attribute.SECS: 30*60
                        },
                ignore=({
                        Attribute.COMMAND: (Command.STILL, Command.DARK),
                        },
                        {
                         Attribute.COMMAND: (Command.MOTION, Command.OCCUPY),
                         Attribute.START: '12:00am',
                         Attribute.END: '6:00am',
                         }
                        ),
                delay={
                       Attribute.COMMAND: Command.OFF,
                       Attribute.SECS: 15*60,
                       Attribute.SOURCE: r_family,
                       },
		time={
			Attribute.COMMAND: Command.OFF,
			Attribute.TIME: '11:59pm',
			},

                name='Family Lamp Light',
                )

l_family = Light(
                 address='19.05.7b',    
                 devices=(insteon, m_family, ph_standard),
                 name='Family Light',
                mapped={
                        Attribute.COMMAND: (Command.MOTION, Command.LIGHT),
                        Attribute.TARGET: Command.OFF,
                        Attribute.SECS: 30*60
                        },
                ignore={
                        Attribute.COMMAND: (Command.STILL, Command.DARK),
                        },
                 )

l_bed_hallway = Light(
                 address='19.0d.1b',    
                 devices=(insteon,),
                 name='Bed Hallway Light',
                 )

l_playroom = Light(devices = WeMo('192.168.13.141', '49153'), 
                  name = 'Playroom')

##################### USER CODE ###############################
#Manually controlling the light
#l_foyer.on()
#l_foyer.off()
#l_front_porch.on()
#l_front_porch.off()
#l_family_lamp.l40()

upb.update_status()

def MainLoop(startup=False, *args, **kwargs):
    if startup:
        print 'Run once'
        thermostat_upstairs.circulate()
        thermostat_upstairs.automatic()
        thermostat_upstairs.level(72)
        thermostat_upstairs.hold()
        thermostat_downstairs.circulate()
        thermostat_downstairs.automatic()
        thermostat_downstairs.level(72)
        thermostat_downstairs.hold()

#    print 'Im in a main loop!'
#    if l_foyer.state == State.ON:
#        l_foyer.off()
#    else:
#        l_foyer.on()
    pass
        






########NEW FILE########
__FILENAME__ = seaview
import select
import time

from pytomation.interfaces import Serial, W800rf32, InsteonPLM, Wtdio, NamedPipe, \
                                StateInterface, Command, HTTPServer
from pytomation.devices import Motion, Door, Light, Location, InterfaceDevice, Room, \
                                Photocell, Generic, StateDevice, State, Attribute


###################### INTERFACE CONFIG #########################
web = HTTPServer()

insteon = InsteonPLM(Serial('/dev/ttyR2', 19200, xonxoff=False))
wtdio = Wtdio(Serial('/dev/mh_weeder_port', 9600))
w800 = W800rf32(Serial('/dev/mh_w800_port', 4800, xonxoff=False))

# Set the I/O points as inputs on the wtdio board, these are all set as inputs
wtdio.setChannel('ASA')
wtdio.setChannel('ASB')
wtdio.setChannel('ASC')
wtdio.setChannel('ASD')
wtdio.setChannel('ASE')
wtdio.setChannel('ASF')
wtdio.setChannel('ASG')

#wtdio.dio_invert('G')

###################### DEVICE CONFIG #########################

# ______ REMOTES ____________________________________________________ 

# X10 Slimline RF wall switch in living room
sl_sofa = Generic('A1', w800, name='Sofa Switch')
sl_stereo = Generic('A2', w800, name='Stereo Switch')
sl_outside = Generic('A3', w800, name='Outside Switch')
sl_xmas = Generic('A0', w800, name='Xmas Switch')

# X10 Slimline RF wall switch in Recroom
sl_recroom_light = Generic('D1', w800, name='Recroom Light Switch')
sl_recroom_lamp = Generic('D2', w800, name='Recroom Lamp Switch')
sl_recroom_tree = Generic('D3', w800, name='Recroom Tree Switch')
sl_alloff = Generic('D0', w800, name='Recroom all off')


# HR12A - X10 Powerhouse Palmpad in living room
pp_sofa = Generic('B1', w800, name='Sofa Pad')
pp_buffet = Generic('B2', w800, name='Buffet Pad')
pp_piano = Generic('B3', w800, name='Piano Pad')
pp_stereo = Generic('B4', w800, name='Stereo Pad')
pp_bedroom = Generic('B5', w800, name='Bedroom Pad')
pp_bathroom = Generic('B6', w800, name='Bathroom Pad')
pp_fireplace = Generic('B7', w800, name='Fireplace Pad')
pp_xmas = Generic('B8', w800, name='Xmas Pad')

pp_sofa60 = Generic('B9', w800)
pp_scene1 = Generic('B10', w800)
pp_rroom = Generic('B11', w800)



# KC674 - X10 Powerhouse keychain in bedroom
bedroom_onoff = Generic('G1', w800, name='Bedroom Remote')
all_lights = Generic('G2', w800)

#'D1' slimeline downstairs

# KR22A X10 4 button remote - low range
x1 = Generic('E1', w800, name='X1')
x2 = Generic('E2', w800)
x3 = Generic('E3', w800)
x4 = Generic('E4', w800)



# ______ MOTION SENSORS _____________________________________________ 

m_kitchen = Motion(address='AC', devices=wtdio, name='Kitchen Motion')
m_laundry = Motion(address='AD', devices=wtdio, name='Laundry Room Motion')
m_hallway = Motion(address='AE', devices=wtdio, name='Hallway Motion')

# Don't allow this to trigger ON again for 20 seconds
m_stairs  = Motion(address='H1', devices=w800, 
        retrigger_delay = {
            Attribute.SECS: 20    
        },
        name='Stair Motion')
m_recroom = Motion(address='I1', devices=w800, name='Recroom Motion')
m_backdoor = Motion(address='J1', devices=w800, name='Backdoor Motion')



# ______ DOOR CONTACTS ______________________________________________ 
d_back = Door(address='AG', devices=wtdio, name='Backdoor Contact')



# ______ LOCATION ___________________________________________________ 
#
ph_standard = Location('48.9008', '-119.8463',      #moved this east a bit
                       tz='America/Vancouver',
                       mode=Location.MODE.STANDARD, 
                       is_dst=True,
                       name='Standard Photocell')



# ______ GENERICS ___________________________________________________ 
#
# Use this for a oneshot at dark.  
on_at_night = Generic(devices=ph_standard, 
                    ignore=({Attribute.COMMAND: Command.LIGHT}), 
                    name='Dark oneshot')

# Cheap way to say some one is in the house
# Make sure the signal lasts at least one loop through mainloop, my mainloop
# is set to 30 seconds
home = Generic(devices=(m_kitchen,m_stairs,m_hallway),
                delay={ Attribute.COMMAND: Command.STILL, Attribute.SECS: 40 },
                name='Someone is home')


            
# ______ HALLWAY ____________________________________________________ 

# LampLinc
l_piano = Light(address='0E.7C.6C', 
            devices=(insteon, sl_sofa, sl_xmas, ph_standard, pp_piano, all_lights),
            time={
                Attribute.TIME: '10:25pm',
                Attribute.COMMAND: Command.OFF
            },
            name='Piano Lamp')

# Turn on the hallway light at night when the back door is opened then go back
# to previous level 2 minutes later
# Don't turn it on when it's DARK
# This device has additional code in mainloop to handle PREVIOUS levels
# SwitchLinc 2476D V5.4
l_hallway =  Light(address='17.C0.7C', 
            devices=(insteon, ph_standard, d_back, all_lights),
            ignore=({Attribute.COMMAND: Command.DARK}),
            mapped={
                Attribute.COMMAND: (Command.CLOSE),
                Attribute.MAPPED: (Command.PREVIOUS),
                Attribute.SECS: 2*60,
            },
            time={
                Attribute.TIME: '10:20pm',
                Attribute.COMMAND: Command.OFF
            },
            name="Hallway Lights",)


# ______ LIVING ROOM ________________________________________________ 

# LampLinc
# Additional rule in mainloop
l_sofa = Light(address='12.07.1F', 
            devices=(insteon, sl_sofa, pp_sofa, pp_sofa60, all_lights, web),
            send_always=True,
            mapped={
                Attribute.COMMAND: Command.ON,
                Attribute.MAPPED:  (Command.LEVEL, 60),
                Attribute.SOURCE:  pp_sofa60,
            },
            time=({
                Attribute.TIME: '10:00pm',
                Attribute.COMMAND: (Command.LEVEL, 60)
            },
            {
                Attribute.TIME: '10:20pm',
                Attribute.COMMAND: Command.OFF
            },),
            name='Sofa Lamps')

# LampLinc
l_buffet = Light(address='0F.81.88', 
            devices=(insteon, sl_sofa, sl_xmas, pp_buffet, on_at_night, all_lights),
            send_always=True,
            time={
                Attribute.TIME: '10:20pm',
                Attribute.COMMAND: Command.OFF
            },
            name='Buffet Lamp')

# LampLinc
l_fireplace = Light(address='12.06.58', 
            devices=(insteon, sl_xmas, sl_sofa, on_at_night, pp_fireplace, all_lights),
            send_always=True,
            time={
                Attribute.TIME: '10:30pm',
                Attribute.COMMAND: Command.OFF
            },
            name='Fireplace Lamp')

# LampLinc
l_stereo = Light(address='12.09.02', 
            devices=(insteon,sl_stereo, sl_xmas, pp_stereo, all_lights),
            send_always=True,
            time={
                Attribute.TIME: '10:19pm',
                Attribute.COMMAND: Command.OFF
            },
            name='Stereo Lamp')


# ______ BEDROOM ROOM _______________________________________________ 
#SwitchLinc
l_bedroom = Light(address='1A.58.E8', 
            devices=(insteon, bedroom_onoff,pp_bedroom),
            send_always=True,
            name='Master Bedroom Light')


# ______ BATHROOM UP ________________________________________________ 
#SwitchLinc dim v4.35
l_bathroom = Light(address='12.20.B0', 
            devices=(insteon,pp_bathroom, all_lights),
            send_always=True,
            name='Bathroom Lights')

# ______ STAIRS _____________________________________________________ 

# This has 2 motion detectors one at the top of the stairs and one in the 
# Laundry room at the bottom.  Go to the top of the stairs and the light 
# turns on, don't go down, it turns off 15 seconds later.  Go down and laundry
# motion keeps it on while in the room, come up the stairs and the laundry 
# timers cancels and the 15 second time turns off the light.  Nice!
#SwitchLinc 2477S V6.0
l_stair_up = Light(address='1E.39.5C', 
            devices=(insteon, m_stairs, m_laundry),
            trigger=({
                'command': Command.ON,
                'mapped': Command.OFF,
                'source': m_stairs,
                'secs': 15,
            }, {
                'command': Command.ON,
                'mapped': Command.OFF,
                'source': m_laundry,
                'secs': 3*60,
            },),
            ignore={
                'command': Command.STILL,
            },
            name='Stair Lights up')
        


#SwitchLinc 2477S V6.2 Dualband
l_stair_down = Light(address='1F.A9.86', 
            devices=(insteon),
            name='Stairs Lights Down')



# ______ RECROOM ____________________________________________________ 

# LampLinc
l_recroom_lamp = Light(address='18.A1.D3', 
            devices=(insteon, sl_recroom_lamp, m_recroom),
            send_always=True,
            delay={
                Attribute.COMMAND: Command.STILL,
                Attribute.SECS: 5*60
            },
            name='Recroom Lamp')

#SwitchLinc Relay V5.2
l_recroom_light = Light(address='12.DB.5D', 
            devices=(insteon, sl_recroom_light,pp_rroom),
            send_always=True,
            time={
                Attribute.TIME: '10:19pm',
                Attribute.COMMAND: Command.OFF
            },
            name='Recroom Light')



# ______ BATHROOM DOWN ______________________________________________ 

#SwitchLinc Relay
f_bathroom = Light(address='12.E3.54',devices=(insteon),
            mapped={
                Attribute.COMMAND: Command.ON,
                Attribute.MAPPED:  Command.OFF,
                Attribute.SECS: 10*60
            },
            name="Downstairs Bathroom Fan")



# ______ OUTSIDE _______________________________________________ 

#SwitchLinc
l_carport = Light(address='0F.45.9F', 
            devices=(insteon, sl_xmas, ph_standard, m_backdoor),
            # don't come on when dark but restrict until dark
            ignore={Attribute.COMMAND: Command.DARK},  
            send_always=True,
            trigger={
                    Attribute.COMMAND: Command.ON,
                    Attribute.MAPPED: Command.OFF,
                    Attribute.SOURCE: m_backdoor,
                    Attribute.SECS: 3*60,
            },
            time={
                Attribute.TIME: '10:10pm',
                Attribute.COMMAND: Command.OFF
            },
            name='Carport Lights')


#KeypadLinc
# On at sunset, drop back to 40% 60 seconds later
# Door open or motion, light at 100%, then idle
# Light off at 10:30 
l_backdoor = Light(address='12.B8.73', 
            devices=(insteon, sl_outside, ph_standard, d_back, all_lights, m_backdoor),
            send_always=True,
#            ignore=({Attribute.COMMAND: Command.DARK},
            ignore=({Attribute.COMMAND: Command.CLOSE},),
            idle={
                    Attribute.MAPPED:(Command.LEVEL, 40),
                    Attribute.SECS: 60,
            },
            time={
                Attribute.TIME: '10:30pm',
                Attribute.COMMAND: Command.OFF
            },
            name='Backdoor Light')



print "Current daylight state is -> ", ph_standard.state
print "Updating status..."
insteon.update_status()

# My mainloop is set at 30 seconds
def MainLoop(startup=False,*args, **kwargs):

    if startup:
        global ticcount
        global sofaOn
        
        ticcount = 0
        sofaOn = True
        print "Startup..."

    ticcount += 1   # right now every 30 seconds

    # cheap occupancy detector
    if (home.state == State.MOTION):
        ticcount = 0

    if ph_standard.state == State.DARK and d_back.state == State.OPEN:
        if ticcount > 180:   # hour and a half
            l_sofa.on()
            ticcount = 0

    # Turn the sofa light on only if we are home and it's dark
    if ph_standard.state == State.DARK and home.state == State.MOTION and sofaOn:
        l_sofa.on()
        sofaOn = False
    elif ph_standard.state == State.LIGHT:
        sofaOn = True

    htime = time.strftime('%H%M')
    if ph_standard.state == "dark" and htime <= '2230':
        l_hallway._previous_state = (State.LEVEL,40)
    else:
        l_hallway._previous_state = (State.LEVEL, 0)
        

    # Sometimes I run from console and print stuff while testing.
        
    #print "Recroom Lamp   -> ", l_recroom_lamp.state
    #print "Recroom Light  -> ", l_recroom_light.state
    print (time.strftime('%H:%M:%S'))
    #print "Ticcount ----> ", ticcount
    #print "Here --------> ", here.state
    #print "Bathroom Light -> ", l_bathroom.state
    print "Hallway Light  -> ", l_hallway.state
    #print "Carport outlet -> ", l_carport.state
    #print "Bedroom Light  -> ", l_bedroom.state
    #print "Stair Light    -> ", l_stair_up.state
    #print "Test Light     -> ", test.state
    #print "Spin Time -> ",insteon.spinTime
    print "Status Request -> ",insteon.statusRequest
    print '--------------------------'
    

########NEW FILE########
__FILENAME__ = vanorman
# import the standard python module "select"
import select
import RPi.GPIO as GPIO

# Import all the Pytomation interfaces we are going to use.
from pytomation.interfaces import UPB, InsteonPLM, TCP, Serial, Stargate, W800rf32, NamedPipe, StateInterface, Command, RPIInput, InsteonPLM2, HTTPServer

# Import all the Pytomation Devices we will use.
from pytomation.devices import Motion, Door, Light, Location, InterfaceDevice, Photocell, Generic, StateDevice, State, Attribute, Scene, Controller

#Create PLM and setup Raspberry PI board and web server
#Note: Raspberry PI inputs require root access
insteon = InsteonPLM2(Serial('/dev/ttyUSB0', 19200, xonxoff=False))
GPIO.setmode(GPIO.BOARD)
web = HTTPServer(address='raspberrypi.home')

ph_standard = Location('53.55', '-113.5',
                       tz='Canada/Mountain',
                       mode=Location.MODE.STANDARD,
                       is_dst=True,
                       name='Standard Photocell')

ll_livingroom1 = Light (address='18.97.08', devices=(insteon), name="Living Room Lamp 1")
ll_livingroom2 = Light (address='14.27.D3', devices=(insteon), name="Living Room Lamp 2")

sl_livingroom1 = Light (address='17.F7.8C', devices=(insteon), name="Living Room Lamps")
sl_livingroom2 = Light (address='16.67.06', devices=(insteon), name="Living Room Lights")

kl_master1 = Light (address='15.64.1D', devices=(insteon), name="Master Bedroom")
sl_master2 = Light (address='16.18.DD', devices=(insteon), name="Master Bathroom")

#KeypadLinc button scenes
kl_mastera = Scene (address="00.00.F3", devices=(insteon,), name="Keypad A", controllers=[Controller(kl_master1, 3)])
kl_masterb = Scene (address="00.00.F4", devices=(insteon,), name="Keypad B", controllers=[Controller(kl_master1, 4)])
kl_masterc = Scene (address="00.00.F5", devices=(insteon,), name="Keypad C", controllers=[Controller(kl_master1, 5)])
kl_masterd = Scene (address="00.00.F6", devices=(insteon,), name="Keypad D", controllers=[Controller(kl_master1, 6)])

sl_outside1 = Light (
	address='14.E7.AD', 
	devices=(insteon,ph_standard), 
	initial=ph_standard, 
	time={Attribute.COMMAND: Command.OFF, Attribute.TIME: '1:00am'},
	name="Outside Back Light")

sl_outside2 = Light (
	address='14.E6.A8', 
	devices=(insteon,ph_standard), 
	initial=ph_standard, 
	time={Attribute.COMMAND: Command.OFF, Attribute.TIME: '1:00am'},
	name="Outside Garage Lights")

ol_outside1 = Light (address='13.FE.5D', devices=(insteon), name="Outside Outlet")

#Raspberry PI inputs
pi_laundry = StateInterface(RPIInput(3))	#BCM 2
cs_laundry = Door (address=None, devices=(pi_laundry), name="Laundry Window")

pi_basementbed = StateInterface(RPIInput(5))	#BCM 3
cs_basementbed = Door (address=None, devices=(pi_basementbed), name="Basement Bedroom Window")

pi_masterbed = StateInterface(RPIInput(7))	#BCM 4
cs_masterbed = Door (address=None, devices=(pi_masterbed), name="Master Bedroom")

pi_boysbed = StateInterface(RPIInput(8))	#BCM 14
cs_boysbed = Door (address=None, devices=(pi_boysbed), name="Boys Bedroom Window")

pi_kitchen = StateInterface(RPIInput(10))	#BCM 15
cs_kitchen = Door (address=None, devices=(pi_kitchen), name="Kitchen Window")

pi_frontdoor = StateInterface(RPIInput(11))	#BCM 17
cs_frontdoor = Door (address=None, devices=(pi_frontdoor), name="Front Door")

pi_basementbath = StateInterface(RPIInput(13))	#BCM 27
cs_basementbath = Door (address=None, devices=(pi_basementbath), name="Basement Bathroom Window")

pi_storageroom = StateInterface(RPIInput(15))	#BCM 22
cs_storageroom = Door (address=None, devices=(pi_storageroom), name="Storage Room Window")

pi_familyroom = StateInterface(RPIInput(19))	#BCM 10
cs_familyroom = Door (address=None, devices=(pi_familyroom), name="Family Room Window")

pi_kaitysbed = StateInterface(RPIInput(21))	#BCM 9
cs_kaitysbed = Door (address=None, devices=(pi_kaitysbed), name="Kaity's Bedroom Window")

pi_diningroom = StateInterface(RPIInput(22))	#BCM 25
cs_diningroom = Door (address=None, devices=(pi_diningroom), name="Dining Room Window")

pi_masterbath = StateInterface(RPIInput(23))	#BCM 11
cs_masterbath = Door (address=None, devices=(pi_masterbath), name="Master Bathroom Window")

pi_backdoor = StateInterface(RPIInput(24)) 	#BCM 2
cs_backdoor = Door (address=None, devices=(pi_backdoor), name="Back Door")

pi_hallway = StateInterface(RPIInput(12))	#BCM 18
mt_hallway = Motion (address=None, devices=(pi_hallway), initial=Command.STILL, name="Hallway Motion",	
	mapped=(
		{Attribute.COMMAND: Command.OPEN, Attribute.MAPPED: Command.MOTION},
		{Attribute.COMMAND: Command.CLOSE,Attribute.MAPPED: Command.STILL}
		),
        delay={Attribute.COMMAND: Command.STILL,Attribute.SECS: 30}
        )

#Example of a hardware scene not defined in the PLM
s_masterbath =  Scene('15.64.1D:04', devices=(insteon,), name="Master Bathroom",
    controllers=[Controller(sl_master2)],
    responders = { sl_master2: {'state': State.ON} })

#Example of a hardware scene defined as scene #2 in the PLM    
s_livingroom = Scene(address="00.00.02", devices=(insteon,), update=False, name="Living Room Scene",
    controllers=[Controller(sl_livingroom1)],
    responders={
        ll_livingroom1: {'state': State.ON},
        ll_livingroom2: {'state': State.ON},
        sl_livingroom1: {'state': State.ON}
    })

#Examlpe of a scene defined as scene #3 in the PLM that has no other controllers.    
s_movietime = Scene(address="00.00.03", devices=(insteon,), update=False, name="Movie Scene",
    responders={
        ll_livingroom1: {'state': (State.LEVEL, 127)},
        ll_livingroom2: {'state': (State.LEVEL, 127)},
        sl_livingroom1: {'state': (State.LEVEL, 127)},
        sl_livingroom2: {'state': State.OFF}
    })


#Update Insteon Status
print "Updating status..."
insteon.update_status()

#Update LED status for a KeypadLinc
insteon.command(kl_master1, 'ledstatus')

def MainLoop(*args, **kwargs):
	pass


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pytomation_django.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = probeport
#! /usr/bin/python

"""
 probeport.py
 Copyright (c) 2010 George Farris <farrisg@shaw.ca>	

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.


Version history
  0.1  Jan 20, 2010 First release
  0.2  Feb 24, 2013 Change port names.
  0.3  Feb 26, 2013 Add Arduino Uno boards with Pytomation driver

USB serial port adapters have the annoying feature of changing every time 
Linux boots, probeport.py will query your devices and link them to the correct 
port.

probeport.py will probe all the ports in the SERIAL_PORTS list for any of the 
devices in the PROBE_DEVICES list.  Once a port is found it will be deleted 
from the SERIAL_PORTS so it won't continually be probed.

In your software  you should set the port devices accordingly, here is a sample
for Pytomation:

insteon = InsteonPLM(Serial('/dev/sp_insteon_plm', 19200, xonxoff=False))
wtdio = Wtdio(Serial('/dev/sp_weeder_wtdio', 9600))
w800 = W800rf32(Serial('/dev/sp_w800rf32', 4800, xonxoff=False))


This script should be run at boot time or any time before your software starts

If you have more or less than 4 ports you can add or subtract them to the 
SERIAL_PORTS list. Also, here is an example if you only have two devices such 
as a weeder board and a plm.

PROBE_DEVICES = ['probe_plm', 'probe_w800']
SERIAL_PORTS = ['/dev/ttyUSB0', '/dev/ttyUSB1']

Please feel free to forward other devices we can probe and I'll add them
to the list and release a new version.  Also please feel free to forward changes 
or bug fixes.  Thanks.  George farrisg@shaw.ca
"""


import sys, os, serial, string, binascii, time, tempfile

# -------------- User modifiable settings -----------------------------

#PROBE_DEVICES = ['test']
# make sure we probe the arduino first
PROBE_DEVICES = ['probe_plm', 'probe_wtdio', 'probe_w800', 'probe_uno']
SERIAL_PORTS = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2', '/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyR1','/dev/ttyR2']
INSTEON_PLM_BAUD_RATE = 19200
WEEDER_IO_BAUD_RATE = 9600
WEEDER_BOARD_ADDRESS = "A"
W800RF32_BAUD_RATE = 4800
ARDUINO_UNO_BAUD_RATE = 9600
spports = []


# ------------- End of user modifiable settings -----------------------

def test():
	print "This is a test run...."


#-----------------------------------------------------------------------------
# Probe for the insteon serial PLM
# plm  send 0x02 0x73, receive 0x02 0x73 0xXX 0x00 0x00 0x06/0x15
#-----------------------------------------------------------------------------
def probe_plm():
	for myport in SERIAL_PORTS:
		print "Probing for Insteon PLM port -> " + myport
		
		try:
			id = SERIAL_PORTS.index(myport)
			ser = serial.Serial(myport, INSTEON_PLM_BAUD_RATE, timeout=2)
			# Probe for Insteon response to command		

			ser.write(binascii.a2b_hex("0273"))
			s2 = binascii.b2a_hex(ser.read(8))
			print s2
			if s2[0:4] == "0273":
				#print "linking " + myport + " to /dev/sp_insteon_plm"
				spports.append("linking " + myport + " to /dev/sp_insteon_plm")
				command = "/bin/ln -sf " + myport + " /dev/sp_insteon_plm"
				os.system(command)
				del SERIAL_PORTS[id]
				ser.close()
				break
			ser.close()

		except:
			print "Error - Could not open serial port..."

#-----------------------------------------------------------------------------
# Probe for the Weeder WTDIO-M 14 channel digital IO board
# weeder send A, receive A?
#-----------------------------------------------------------------------------
def probe_wtdio():
	for myport in SERIAL_PORTS:
		print "Probing for Weeder WTDIO-M IO board port -> " + myport
		
		try:
			id = SERIAL_PORTS.index(myport)
			ser = serial.Serial(myport, WEEDER_IO_BAUD_RATE, timeout=2)
			ser.write(WEEDER_BOARD_ADDRESS)
			s2 = ser.read(5)
			print s2
			if s2[0:2] == WEEDER_BOARD_ADDRESS + '?':
				spports.append("linking " + myport + " to /dev/sp_weeder_wtdio")
				command = "/bin/ln -sf " + myport + " /dev/sp_weeder_wtdio"
				os.system(command)
				del SERIAL_PORTS[id]
				ser.close()
				break
			ser.close()

		except:
			print "Error - Could not open serial port..."

#-----------------------------------------------------------------------------
# Probe for the W800RF32 x10 RF receiver
# w800   send 0xf0 0x29, receive 0x29
#-----------------------------------------------------------------------------
def probe_w800():
	for myport in SERIAL_PORTS:
		print "Probing for W800RF32 port -> " + myport
		
		try:
			id = SERIAL_PORTS.index(myport)
			ser = serial.Serial(myport, W800RF32_BAUD_RATE, timeout=2)
			ser.write(binascii.a2b_hex("F029"))
			s2 = binascii.b2a_hex(ser.read(8))
			print s2
			if s2[0:2] == "29":
				spports.append("linking " + myport + " to /dev/sp_w800rf32")
				command = "/bin/ln -sf " + myport + " /dev/sp_w800rf32"
				os.system(command)
				del SERIAL_PORTS[id]
				ser.close()
				break
			ser.close()

		except:
			print "Error - Could not open serial port..."

#-----------------------------------------------------------------------------
# Probe for the Arduino Uno with the Pytomation firmware
# uno   send '?', receive "PYARUNO <char>" where char is board address
#-----------------------------------------------------------------------------
def probe_uno():
	for myport in SERIAL_PORTS:
		print "Probing for Arduino Uno port -> " + myport
		
		try:
			id = SERIAL_PORTS.index(myport)
			ser = serial.Serial(myport, ARDUINO_UNO_BAUD_RATE, timeout=2)
			ser.write('?')
			ser.read(100)	#clear buffer
			ser.write('?')
			s2 = ser.read(9)
			print s2
			if s2[0:7] == "PYARUNO":
				spports.append("linking " + myport + " to /dev/sp_pyaruno")
				command = "/bin/ln -sf " + myport + " /dev/sp_pyaruno"
				os.system(command)
				del SERIAL_PORTS[id]
				ser.close()
				break
			ser.close()

		except:
			print "Error - Could not open serial port..."

def show():
	print '\n\n'
	print 'Report\n--------------------------------------------------'
	for line in spports:
		print line

if __name__ == "__main__":
	for device in PROBE_DEVICES:
		func = globals()[device]
		func()
	show ()


	print "Goodbye..."


########NEW FILE########
__FILENAME__ = config_example
"""
File:
    config.py

Description:

This is the main configuration file for Pytomation.  It is divided into
sections each pertaining to a specific part of the system.  These sections 
cannot be deleted, the variables can be modified but they must have a value.


License:
    This free software is licensed under the terms of the GNU public 
    license, Version 3.

System Versions and changes:
    Initial version created on Nov 11, 2012
    2012/11/11 - 1.0 - Global debug dictionary created
    2012/11/18 - 1.1 - Log file pieces added
    2013/01/24 - 1.2 - New logging system and start loop vars
        
"""
import os
import sys

#
#********************* SYSYTEM CONFIGURATION ONLY ********************
#
admin_user = 'pyto'
admin_password = 'mation'
http_address = "0.0.0.0"
http_port = 8080
http_path = "./pytomation_web"
telnet_port = None
loop_time = 1

device_send_always = False

# ********************* LOGGING CONFIGURATION ****************************
"""
# LOGGING
 Setup logging of Pytomation to a log file.  Pytomation uses the standard
 Python logging modules which supports a wide variety of functions from
 log rotation to logging to a remote system.

 Please see http://docs.python.org/2/library/logging.html for full information.
 
 Logging Levels:

 DEBUG | INFO | WARNING | ERROR | CRITICAL
"""

## Default logging level
logging_default_level = "ERROR"

# Logging modules is dict() of modules names and their minimum logging
# levels.  If it is not listed default level is used
#
logging_modules = {
                  "apscheduler.scheduler": "CRITICAL",
                   'LoggingTests': "CRITICAL",
                   #'Stargate': 'DEBUG',
                   #'InsteonPLM': 'DEBUG',
                   #'W800rf32': 'DEBUG',
                   #'Wtdio': 'DEBUG',
                   #'UPB': 'DEBUG',
                   #"Light": "DEBUG",
                   #'Arduino': 'DEBUG',
                   #'CM11a': 'DEBUG',          
                   'Thermostat': 'DEBUG',         
                   }

# Logging file path
logging_file = os.path.join(sys.path[0], 'pylog.log')

# Logging entry message format
logging_format = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'

# Logging entry date format
logging_datefmt = "%Y/%m/%d %H:%M:%S"

#*************  NOTE ********************************
# Log rotation is currently not working, we will update this section when 
# it changes but for now please leave it set to "None"
#
#logging_rotate_when = 'midnight' # s, m, h, d, w (interval 0=Monday), midnight, None
logging_rotate_when = None # s, m, h, d, w (interval 0=Monday), midnight, None
logging_rotate_interval = 1
logging_rotate_backup = 4


########NEW FILE########
__FILENAME__ = pytomation_api
from .pytomation_object import PytomationObject
#from .pytomation_system import *
import pytomation_system
import json
import urllib
#from collections import OrderedDict

class PytomationAPI(PytomationObject):
    JSON = 'json'

    def get_map(self):
        return {
           ('get','devices'): PytomationAPI.get_devices,
           ('get', 'device'): PytomationAPI.get_device,
           ('post', 'device'): self.update_device,
           }
    
    def get_response(self, method="GET", path=None, type=None, data=None, source=None):
        response = None
        method = method.lower()
        levels = path.split('/')
        if data:
            if isinstance(data, list):
                tdata = []
                for i in data:
                    tdata.append(urllib.unquote(i).decode('utf8'))
                data = tdata
            else:
                data = urllib.unquote(data).decode('utf8')

#        print 'pizz:' + path + "l:" + levels[0] + "DDD"+ str(data)
#	print "eeeeee" + str(source)
        type = type.lower() if type else self.JSON
        f = self.get_map().get((method, levels[0]), None)
        if f:
            response = f(levels, data=data, source=source)
        elif levels[0].lower() == 'device':
            try:
                response = self.update_device(command=method, levels=levels, source=source)
            except Exception, ex:
                pass
        if type==self.JSON:
            return json.dumps(response)
        return None

    @staticmethod
    def get_devices(path=None, *args, **kwargs):
        devices = []
        for (k, v) in pytomation_system.get_instances_detail().iteritems():
            try:
                v.update({'id': k})
                a = v['instance']
                b = a.state
                del v['instance']
#                devices.append({k: v})
                devices.append(v)
            except Exception, ex:
                pass
#        f = OrderedDict(sorted(devices.items()))
#        odevices = OrderedDict(sorted(f.items(), key=lambda k: k[1]['type_name'])
#                            )
        return devices

    @staticmethod
    def get_device(levels, *args, **kwargs):
        id = levels[1]
        detail = pytomation_system.get_instances_detail()[id]
        detail.update({'id': id})
        del detail['instance']
        return detail
    
    def update_device(self, levels, data=None, source=None, *args, **kwargs):
        command = None
#	print 'kkkkkkkk' + str(source)
        if not source:
            source = self

        if data:
            if isinstance(data, list):
                for d in data:
#                    print 'ff' + str(d)
                    e = d.split('=')
#                    print 'eee' + str(e)
                    if e[0]== 'command':
                        command = e[1]
            else:
                e = data.split('=')
                command = e[1]
#        print 'Set Device' + str(command) + ":::" + str(levels)
        id = levels[1]
        # look for tuples in the command and make it a tuple
        if ',' in command:
            e = command.split(',')
            l = []
            # lets convert any strings to int's if we can
            for i in e:
                t = i
                try:
                    t = int(i)
                except:
                    pass
                l.append(t)
            command = tuple(l)
        try:
            detail = pytomation_system.get_instances_detail()[id]
            device = detail['instance']
            device.command(command=command, source=source)
            response =  PytomationAPI.get_device(levels)
        except Exception, ex:
            pass
#        print 'res['+ str(response)
        return response

########NEW FILE########
__FILENAME__ = pytomation_object
from .pyto_logging import PytoLogging

class PytomationObject(object):
    instances = []
    def __init__(self, *args, **kwargs):
        self._type_id = None
        self._po_common(*args, **kwargs)

    def _po_common(self, *args, **kwargs):
        
        self._logger = PytoLogging(self.__class__.__name__)
        self.instances.append(self)
        self._type_id = str(self.__class__.__name__) + str(len(self.instances))
        self._name = kwargs.get('name', self._type_id)
        try:
            self._logger.debug('Object created: {name} {obj}'.format(
                                                                     name=self._name,
                                                                     obj=str(self))
                               )
        except Exception, ex:
            pass
        
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value):
        self._name = value
        return self._name
    
    @property
    def name_ex(self):
        return self._name
    
    @name_ex.setter
    def name_ex(self, value):
        self._name = value
        return self._name
    
    @property
    def type_name(self):
        return self.__class__.__name__
    
    @property
    def type_id(self):
        return self._type_id
########NEW FILE########
__FILENAME__ = pytomation_system
import time
import select
from .pytomation_object import PytomationObject
from ..utility.periodic_timer import PeriodicTimer
#from ..utility.manhole import Manhole
from ..utility.http_server import PytomationHTTPServer

def get_instances():
    return PytomationObject.instances

def get_instances_detail():
    details = {}
    for object in get_instances():
        object_detail = {
                                   'instance': object,
                                   'name': object.name,
                                   'type_name': object.type_name,
                                   } 
        try:
            object_detail.update({'commands': object.COMMANDS})
            object_detail.update({'state': object.state})
        except Exception, ex:
            # Not a state device
            pass
        details.update({
                       object.type_id: object_detail,
                       })
        
    return details

def start(loop_action=None, loop_time=1, admin_user=None, admin_password=None, telnet_port=None, 
          http_address=None, http_port=None, http_path=None):
    if loop_action:
        # run the loop for startup once
        loop_action(startup=True)
        # run periodically from now on
        myLooper = PeriodicTimer(loop_time) # loop every 1 sec
        myLooper.action(loop_action, None, {'startup': False} )
        myLooper.start()
    
    if telnet_port:
        Manhole().start(user=admin_user, password=admin_password, port=telnet_port, instances=get_instances_detail())

    if http_address and http_port and http_path and False:
        PytomationHTTPServer(address=http_address, port=http_port, path=http_path).start()
    else:
        # sit and spin - Let the magic flow
        #select.select([],[],[])
        while True: time.sleep(1)

########NEW FILE########
__FILENAME__ = pyto_logging
import logging
from logging.handlers import TimedRotatingFileHandler

from ..common import config


class PytoLogging(object):
    loaded_handlers = []

    def __init__(self, *args, **kwargs):
        self._name = args[0]
        self._log_file = config.logging_file
        default_log_file = 'pytomation.log'
        if not self._log_file:
            self._log_file = default_log_file
            
        self._logger = logging.getLogger(self._name)
        module_level_name = config.logging_modules.get(self._name, config.logging_default_level)
        if config.logging_rotate_when:
            try:
                th = TimedRotatingFileHandler(filename=config.logging_file,
                                                                 when=config.logging_rotate_when,
                                                                 interval=config.logging_rotate_interval,
                                                                 backupCount=config.logging_rotate_backup )
            except Exception, ex:
                th = TimedRotatingFileHandler(filename=default_log_file,
                                                                 when=config.logging_rotate_when,
                                                                 interval=config.logging_rotate_interval,
                                                                 backupCount=config.logging_rotate_backup )
                
            if module_level_name:
                module_level = getattr(logging, module_level_name)
#                th.setLevel(module_level)
            th.setFormatter(logging.Formatter(fmt=config.logging_format, datefmt=config.logging_datefmt))
            if not self._name in self.loaded_handlers:
            	self._logger.addHandler(th)
		self.loaded_handlers.append(self._name)
        else:
            try:
                self._basic_config(self._log_file)
            except:
                self._basic_config(default_log_file)
        #get module specifics
        if module_level_name:
            module_level = getattr(logging, module_level_name)
            self._logger.setLevel(module_level)


    def _basic_config(self, filename):
        log_level = getattr(logging, config.logging_default_level)
        logging.basicConfig(
                            filename=filename,
                            format=config.logging_format,
                            datefmt=config.logging_datefmt,
                            level=log_level,
                            )
        
    def __getattr__(self, name):
        return getattr(self._logger, name)

########NEW FILE########
__FILENAME__ = attributes
class Attributes(object):
    
    def __init__(self, *args, **kwargs):
        self.command = None
        self.mapped = None
        self.source = None
        self.time = None
        self.secs = None
        
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
########NEW FILE########
__FILENAME__ = controller
'''
File:
    controller.py

Description:
    A helper class for defining an address for a scene controller

Author(s): 
    Chris Van Orman

License:
    This free software is licensed under the terms of the GNU public license, Version 1     

Usage:


Example: 

Notes:


Created on Mar 11, 2013
'''
class Controller(object):
    def __init__(self, device=None, group=1, address=None):
        self._address = device.address if device else None
        if (self._address and group):
            self._address += ':%02X' % group
        self._address = address if address else self._address

    def addressMatches(self, address):
        return self._address == address

########NEW FILE########
__FILENAME__ = door
from pytomation.interfaces import Command
from .interface import InterfaceDevice
from .state import State

class Door(InterfaceDevice):
    STATES = [State.UNKNOWN, State.OPEN, State.CLOSED]
    COMMANDS = [Command.OPEN, Command.CLOSE, Command.PREVIOUS, Command.TOGGLE, Command.INITIAL,
                Command.AUTOMATIC, Command.MANUAL, Command.STATUS]

    
    def _initial_vars(self, *args, **kwargs):
        super(Door, self)._initial_vars(*args, **kwargs)
        self._read_only = True
        self.mapped(command=Command.ON, mapped=Command.OPEN)
        self.mapped(command=Command.OFF, mapped=Command.CLOSE)
########NEW FILE########
__FILENAME__ = generic
from pytomation.devices import InterfaceDevice, State
from pytomation.interfaces import Command

class Generic(InterfaceDevice):
    STATES = [State.UNKNOWN, State.OFF, State.ON, State.ACTIVE, State.INACTIVE, State.MOTION, State.STILL, State.LIGHT, State.DARK, State.OPEN, State.CLOSED]
    COMMANDS = [Command.ON, Command.OFF, Command.ACTIVATE, Command.DEACTIVATE, Command.MOTION, Command.STILL,
                Command.LIGHT, Command.DARK, Command.OPEN, Command.CLOSE, Command.LEVEL, Command.AUTOMATIC, Command.MANUAL, Command.STATUS]
    
    
########NEW FILE########
__FILENAME__ = google_voice
from googlevoice import Voice
#from googlevoice.util import input


from pytomation.devices import StateDevice, State
from pytomation.interfaces import Command

class Google_Voice(StateDevice):
    STATES = [State.UNKNOWN, State.ON, State.OFF]
    COMMANDS = [Command.MESSAGE]

    def __init__(self, user=None, password=None, *args, **kwargs):
        self._user = user
        self._password = password
        print "big"
        self._create_connection(user, password)
        super(Google_Voice, self).__init__(*args, **kwargs)

    def _create_connection(self, user, password):
        print "ehehe"
        self._voice = Voice()
        print 'user' + user + ":" + password
        self._voice.login(email=user, passwd=password)

    def _initial_vars(self, *args, **kwargs):
        super(Google_Voice, self)._initial_vars(*args, **kwargs)

    def _delegate_command(self, command, *args, **kwargs):
        self._logger.debug('Delegating')
        print 'pie'
        print str(args) + ":" + str(kwargs)
        if isinstance(command, tuple) and command[0] == Command.MESSAGE:            
            self._logger.debug('Sending Message')
            self._voice.send_sms(command[1], command[2])
            
        super(Google_Voice, self)._delegate_command(command, *args, **kwargs)

        
    
########NEW FILE########
__FILENAME__ = interface
import random

from pytomation.utility.timer import Timer as CTimer
from .state import StateDevice, State
from pytomation.interfaces import Command
from pytomation.common import config

class InterfaceDevice(StateDevice):
    
    def __init__(self, address=None, *args, **kwargs):
        self._address = address
        super(InterfaceDevice, self).__init__(*args, **kwargs)
        
        
    def _initial_vars(self, *args, **kwargs):
        super(InterfaceDevice, self)._initial_vars(*args, **kwargs)
        self._interfaces=[]
        self._sync = False
        self._sync_timer = None
        self._read_only = False
        self._send_always = config.device_send_always
        self._previous_interface_command = None
        
    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, value):
        self._address = value
        return self._address
    
    def addressMatches(self, address):
        match = self.address == None or self.address == address
        if not match:
            try:
                match = self.address.lower() == address.lower()
            except Exception, ex:
                pass
        return match
            
    def _add_device(self, device):
        try:
            device.onCommand(device=self) # Register with the interface to receive events
            self._interfaces.append(device)
            self.delay(command=Command.ON, source=device, secs=0)
            self.delay(command=Command.OFF, source=device, secs=0)
            self._logger.debug("{name} added new interface {interface}".format(
                                                                               name=self.name,
                                                                               interface=device.name,
                                                                               ))
            return True
        except Exception, ex:
            return super(InterfaceDevice, self)._add_device(device)

    def _delegate_command(self, command, *args, **kwargs):
        original_state = kwargs.get('original_state', None)
        source = kwargs.get('source', None)
        original = kwargs.get('original', None)
        if not self._read_only:
            for interface in self._interfaces:
                if source != interface and original != interface:
                    new_state = self._command_to_state(command, None)
                    if self._send_always or (not self._send_always and original_state != new_state):
                        self._previous_interface_command = command
                        try:
                            self._logger.debug("{name} Send command '{command}' to interface '{interface}'".format(
                                                                                                name=self.name,
                                                                                                command=command,
                                                                                                interface=interface.name
                                                                                             ))
                            self._send_command_to_interface(interface, self._address, command)
#                             if isinstance(command, tuple):
# #                                getattr(interface, command[0])(self._address, *command[1:])
#                                 self._send_command_to_interface(interface, self._address, *command[1:])
#                             else:
# #                                getattr(interface, command)(self._address)
#                                 self._send_command_to_interface(interface, self._address, command)
                        except Exception, ex:
                            self._logger.error("{name} Could not send command '{command}' to interface '{interface}.  Exception: {exc}'".format(
                                                                                                name=self.name,
                                                                                                command=command,
                                                                                                interface=interface.name,
                                                                                                exc=str(ex),
                                                                                             ))
                    else:
                        self._logger.debug("{name} is already at this new state {state} originally {original_state} for command {command} -> {new_state}, do not send to interface".format(
                                                                                                name=self.name,
                                                                                                state=self.state,
                                                                                                original_state=original_state,
                                                                                                command=command,
                                                                                                new_state=new_state,
                                                                                                                  ))
                else:
                    self._logger.debug("{name} do not send to interface because either the current source {source} or original source {original} is the interface itself.".format(
                                                                                                name=self.name,
                                                                                                state=self.state,
                                                                                                source=source,
                                                                                                original=original,
                                                                                                command=command,
                                                                                                                  ))
        return super(InterfaceDevice, self)._delegate_command(command, *args, **kwargs)

    def _send_command_to_interface(self, interface, address, command):
        if isinstance(command, tuple):
            getattr(interface, command[0])(self._address, *command[1:])
        else:
            getattr(interface, command)(self._address)
            
    
    def sync(self, value):
        self._sync = value
        if value:
            self._start_sync()
        else:
            self._stop_sync()
        return self._sync
    
    def _start_sync(self):
        # get a random number of secs from 30 minutes to an hour
        offset = random.randint(0, 30 * 60) + (30 * 60) 
        self._sync_timer = CTimer(offset)
        self._sync_timer.action(self._run_sync, ())
        self._sync_timer.start()        

    def _stop_sync(self):
        self._sync_timer.stop()
        
    def _run_sync(self):
        if self.interface:
            getattr(self.interface, self._state)()
        self._start_sync()
        
    def read_only(self, value=None):
        if value:
            self._read_only=value
        return self._read_only
    
    def send_always(self, value=False):
        if value:
            self._send_always = value
        return self._send_always

########NEW FILE########
__FILENAME__ = light
from .interface import InterfaceDevice
from .state import State
from pytomation.interfaces import Command

class Light(InterfaceDevice):
    STATES = [State.UNKNOWN, State.ON, State.OFF, State.LEVEL]
    COMMANDS = [Command.ON, Command.OFF, Command.PREVIOUS, Command.TOGGLE, Command.INITIAL,
                Command.AUTOMATIC, Command.MANUAL, Command.STATUS]

    def _initial_vars(self, *args, **kwargs):
        super(Light, self)._initial_vars(*args, **kwargs)
        self._restricted = False
        self.mapped(command=Command.MOTION, mapped=Command.ON)
        self.mapped(command=Command.DARK, mapped=Command.ON)
        self.mapped(command=Command.OPEN, mapped=Command.ON)
        self.mapped(command=Command.OCCUPY, mapped=Command.ON)
        self.mapped(command=Command.STILL, mapped=Command.OFF)
        self.mapped(command=Command.LIGHT, mapped=Command.OFF)
        self.mapped(command=Command.CLOSE, mapped=Command.OFF)
        self.mapped(command=Command.VACATE, mapped=Command.OFF)

    def command(self, command, *args, **kwargs):
        source = kwargs.get('source', None)
        try:
            if source and source.state == State.DARK:
                self.restricted = False
                self._logger.debug('{name} received Dark from {source}.  Now unrestricted'.format(
                                                            name=self.name,
                                                            source=source.name if source else str(source)
                                                                                    ))
            elif source and source.state == State.LIGHT:
                self.restricted = True
                self._logger.debug('{name} received Light from {source}.  Now restricted'.format(
                                                            name=self.name,
                                                            source=source.name if source else str(source)
                                                                                    ))
        except AttributeError, ex:
            pass
        super(Light, self).command(command, *args, **kwargs)

    def _command_state_map(self, command, *args, **kwargs):
        source = kwargs.get('source', None)
        if command == Command.ON:
            a = 1
        (m_state, m_command) = super(Light, self)._command_state_map(command, *args, **kwargs)
        primary_command = m_command
        if isinstance(m_command, tuple):
            primary_command = m_command[0]
        try:
            if source and (primary_command in [Command.ON, Command.LEVEL]):
                if self.restricted and source not in self._interfaces and not source.unrestricted:
                    m_command = None
                    m_state = None 
                    self._logger.info("{name} is restricted. Ignoring command {command} from {source}".format(
                                                                                         name=self.name,
                                                                                         command=command,
                                                                                         source=source.name,
                                                                                                               ))
        except AttributeError, ex:
            pass #source is not a state device
        return (m_state, m_command)
        
    @property
    def restricted(self):
        return self._restricted
    
    @restricted.setter
    def restricted(self, value):
        self._restricted = value
        return self._restricted
    
    def level(self, value):
        self.command((Command.LEVEL, value))
########NEW FILE########
__FILENAME__ = location
import ephem
import pytz

from datetime import datetime
from time import strftime
from .state import StateDevice, State
from pytomation.utility import CronTimer
from pytomation.interfaces import Command

class Location(StateDevice):
    STATES = [State.LIGHT, State.DARK]
    COMMANDS = [Command.LIGHT, Command.DARK, Command.INITIAL, Command.TOGGLE, Command.PREVIOUS]

    class MODE():
        STANDARD = '0'
        CIVIL = '-6'
        NAUTICAL = '-12'
        ASTRONOMICAL = '-18'
    
    def __init__(self, latitude, longitude, tz='US/Eastern', mode=MODE.STANDARD, is_dst=True, *args, **kwargs):
        super(Location, self).__init__(*args, **kwargs)
        self.obs = ephem.Observer()
        self.obs.lat = latitude
        self.obs.long = longitude
        self.tz = pytz.timezone(tz)
        self.is_dst = is_dst

        self.sun = ephem.Sun(self.obs)
        self._horizon = mode
        
        self._sunset_timer = CronTimer()
        self._sunrise_timer = CronTimer()
        self._local_time = None
        self._recalc()

    @property
    def mode(self):
        return self._horizon
    
    @mode.setter
    def mode(self, value):
        self._horizon = value
        self._recalc()
        
        
    @property
    def local_time(self):
        if not self._local_time:
            return self.tz.localize(datetime.now(), is_dst=self.is_dst)
        else:
            return self.tz.localize(self._local_time, is_dst=self.is_dst)
    
    @local_time.setter
    def local_time(self, value):
        self._local_time = value
        self._recalc()

    def _recalc(self):
        self.obs.horizon = self._horizon

#        midnight = self.tz.localize(local_time.replace(hour=12, minute=0, second=0, microsecond=0, tzinfo=None), 
#                               is_dst=None)
#        self.obs.date = midnight.astimezone(pytz.utc) 

        self.obs.date = self.local_time.astimezone(pytz.utc)

        prev_rising = self._utc2tz(
                                  self.obs.previous_rising(self.sun, use_center=True).datetime())
        prev_setting = self._utc2tz(
                                  self.obs.previous_setting(self.sun, use_center=True).datetime())
        self._sunrise = self._utc2tz(
                                     self.obs.next_rising(self.sun, use_center=True).datetime())
        self._sunset = self._utc2tz(
                                     self.obs.next_setting(self.sun, use_center=True).datetime())
        self._sunrise = self._sunrise.replace(second=0, microsecond=0)
        self._sunset = self._sunset.replace(second=0, microsecond=0)
        self._logger.info('{name} Location sunset: {sunset} sunrise: {sunrise}'.format(
                                                                                       name=self.name,
                                                                                       sunset=str(self._sunset),
                                                                                       sunrise=str(self._sunrise),
                                                                                       ))
        time_now = self.local_time.replace(second=0, microsecond=0)
        if (self._sunrise > self._sunset and self._sunset != time_now) or \
            self._sunrise == time_now:
            if self.state <> Command.LIGHT:
                self.light()
            else:
                self._logger.info("{name} Location did not flip state as it already is light".format(
                                                                                                     name=self.name
                                                                                                     ))
        else:
            if self.state <> Command.DARK:
                self.dark()
            else:
                self._logger.info("{name} Location did not flip state as it already is dark".format(
                                                                                                     name=self.name
                                                                                                     ))

                         
        # Setup trigger for next transition
        self._sunset_timer.interval(*CronTimer.to_cron(strftime("%H:%M:%S", self.sunset.timetuple())))
        self._sunset_timer.action(self._recalc)
        self._sunset_timer.start()

        self._sunrise_timer.interval(*CronTimer.to_cron(strftime("%H:%M:%S", self.sunrise.timetuple())))
        self._sunrise_timer.action(self._recalc)
        self._sunrise_timer.start()
        

    @property
    def sunset(self):
        return self._sunset
    
    @sunset.setter
    def sunset(self, value):
        self._sunset = value
        self._recalc()
        return self._sunset
    
    @property
    def sunrise(self):
        return self._sunrise
    
    @sunrise.setter
    def sunrise(self, value):
        self._sunrise = value
        self._recalc()
        return self._sunrise

    def _utc2tz(self, value):
        return pytz.utc.localize(value, is_dst=self.is_dst).astimezone(self.tz)

    def _command_state_map(self, command, *args, **kwargs):
        (m_state, m_command) = super(Location, self)._command_state_map(command, *args, **kwargs)
        if m_command == Command.OFF:
            m_state = State.DARK
        elif m_command == Command.ON:
            m_state = State.LIGHT
        return (m_state, m_command)
########NEW FILE########
__FILENAME__ = motion
from pytomation.interfaces import Command
from .interface import InterfaceDevice
from .state import State

class Motion(InterfaceDevice):
    STATES = [State.UNKNOWN, State.MOTION, State.STILL, State.LEVEL]
    COMMANDS = [Command.MOTION, Command.STILL, Command.LEVEL,
                Command.PREVIOUS, Command.TOGGLE, Command.INITIAL,
                Command.AUTOMATIC, Command.MANUAL, Command.STATUS]

    def _initial_vars(self, *args, **kwargs):
        super(Motion, self)._initial_vars(*args, **kwargs)
        self._read_only = True
        self.mapped(command=Command.ON, mapped=Command.MOTION)
        self.mapped(command=Command.OFF, mapped=Command.STILL)
########NEW FILE########
__FILENAME__ = photocell
from .interface import InterfaceDevice
from .state import State
from pytomation.interfaces import Command

class Photocell(InterfaceDevice):
    STATES = [State.UNKNOWN, State.DARK, State.LIGHT, State.LEVEL]
    COMMANDS = [Command.DARK, Command.LIGHT, Command.LEVEL, Command.PREVIOUS, Command.TOGGLE, Command.INITIAL]

    def _initial_vars(self, *args, **kwargs):
        super(Photocell, self)._initial_vars(*args, **kwargs)
        self._read_only = True
        self.mapped(command=Command.ON, mapped=Command.DARK)
        self.mapped(command=Command.OFF, mapped=Command.LIGHT)
########NEW FILE########
__FILENAME__ = room
from pytomation.devices import State, StateDevice
from pytomation.interfaces import Command

class Room(StateDevice):
    STATES = [State.UNKNOWN, State.OCCUPIED, State.VACANT]
    COMMANDS = [Command.OCCUPY, Command.VACATE]
    
    def _initial_vars(self, *args, **kwargs):
        super(Room, self)._initial_vars(*args, **kwargs)
        self._restricted = False
        self.mapped(command=Command.MOTION, mapped=Command.OCCUPY)
        self.mapped(command=Command.OPEN, mapped=Command.OCCUPY)
        self.mapped(command=Command.STILL, mapped=None)
        self.mapped(command=Command.CLOSE, mapped=Command.VACATE)

    def command(self, command, *args, **kwargs):
        source = kwargs.get('source', None)
        if command == Command.OCCUPY and source and getattr(source, 'state') and source in self._devices and source.state == State.OCCUPIED:
            return super(Room, self).command(command=Command.VACATE, *args, **kwargs)
        if command == Command.VACATE and source and getattr(source, 'state') and source in self._devices and source.state == State.VACANT:
#            return super(Room, self).command(command=Command.OCCUPY, *args, **kwargs)
            return True
        return super(Room, self).command(command=command, *args, **kwargs)

########NEW FILE########
__FILENAME__ = scene
'''
File:
    scene.py

Description:
    A device that represents a Scene or group of devices.

Author(s): 
     Chris Van Orman

License:
    This free software is licensed under the terms of the GNU public license, Version 1     

Usage:

Example: 

Notes:

Created on Mar 11, 2013
'''
from .interface import InterfaceDevice
from pytomation.interfaces.common import Command
from .state import State

class Scene(InterfaceDevice):
    STATES = [State.UNKNOWN, State.ON, State.OFF]
    COMMANDS = [Command.ON, Command.OFF, Command.PREVIOUS, Command.TOGGLE, Command.INITIAL]

    def __init__(self, address=None, *args, **kwargs):
        super(Scene, self).__init__(address=address, *args, **kwargs)
        self._controllers = kwargs.get('controllers', [])
        self._responders = kwargs.get('responders', {})       
        
        self._processResponders(self._responders)

    def _initial_vars(self, *args, **kwargs):
        super(Scene, self)._initial_vars(*args, **kwargs)
        self._responders = {}
        self._controllers = []

    def addressMatches(self, address):
        matches = super(Scene, self).addressMatches(address)
        
        #check if any controller also matches
        for d in self._controllers:
            matches = matches or d.addressMatches(address)
        
        return matches

    def command(self, command, *args, **kwargs):
        source = kwargs.get('source', None)
        if source in self._responders:
            #if it was a responder, just update the scene state.
            self._updateState()
        elif source not in self._responders:
            super(Scene, self).command(command, *args, **kwargs)
            #The scene state changed, set the state of all responders.
            self._updateResponders(self.state)

    def _updateState(self):
        #set our state based on what the state of all responders are.
        state = State.ON
        for d,s in self._responders.items():
            state = State.OFF if d.state != s['state'] else state
        if state != self.state:
            self.state = state
            
    def _updateResponders(self, state):
        #set the state of our responders based upon the scene state.
        for d,s in self._responders.items():
            d.state = State.OFF if state == State.OFF else s['state']

    def _processResponders(self, responders):
        #attach to all the responders so we can update the Scene state when they change.
        for r in responders:
            r.on_command(self)

########NEW FILE########
__FILENAME__ = state
from datetime import datetime
import gc
import thread

from pytomation.common import PytomationObject
from pytomation.interfaces import Command
from pytomation.utility import CronTimer
from pytomation.utility.timer import Timer as CTimer
from pytomation.utility.time_funcs import *

class State(object):
    ALL = 'all'
    UNKNOWN = 'unknown'
    ON = 'on'
    OFF = 'off'
    LEVEL = 'level'
    MOTION = 'motion'
    STILL = 'still'
    OPEN = 'open'
    CLOSED = "close"
    LIGHT = "light"
    DARK = "dark"
    ACTIVE = 'activate'
    INACTIVE = 'deactivate'
    OCCUPIED = 'occupy'
    VACANT = 'vacate'
    HEAT = 'heat'
    COOL = 'cool'
    CIRCULATE = 'circulate'
    AUTOMATIC = 'automatic'
    HOLD = 'hold'
    

class Attribute(object):
    MAPPED = 'mapped'
    COMMAND = 'command'
    STATE = 'state'
    TARGET = 'target'
    TIME = 'time'
    SECS = 'secs'
    SOURCE = 'source'
    START = 'start'
    END = 'end'

class Property(object):
    IDLE = 'idle'
    DELAY = 'delay'
    
class StateDevice(PytomationObject):
    STATES = [State.UNKNOWN, State.ON, State.OFF, State.LEVEL]
    COMMANDS = [Command.ON, Command.OFF, Command.LEVEL, Command.PREVIOUS,
                Command.TOGGLE, Command.AUTOMATIC, Command.MANUAL, Command.INITIAL, Command.STATUS]
    
    def __init__(self, *args, **kwargs):
        self._command_lock = thread.allocate_lock()
        super(StateDevice, self).__init__(*args, **kwargs)
        if not kwargs.get('devices', None) and len(args)>0:
            kwargs.update({'devices': args[0]})
        self._initial_vars(*args, **kwargs)
        self._process_kwargs(kwargs)
        self._initial_from_devices(*args, **kwargs)
        if not self.state or self.state == State.UNKNOWN:
            self.command(Command.INITIAL, source=self)

    def _initial_vars(self, *args, **kwargs):
        self._state = State.UNKNOWN
        self._previous_state = self._state
        self._previous_command = None
        self._last_set = datetime.now()
        self._changes_only = False
        self._delegates = []
        self._times = []
        self._maps = {}
        self._delays = {}
        self._delay_timers = {}
        self._triggers = {}
        self._trigger_timers = {}
        self._ignores = {}
        self._restrictions = {}
        self._idle_timer = {}
        self._idle_command = None
        self._devices = []
        self._automatic = True
        self._retrigger_delay = None
#        self.invert(False)
        
        
    def invert(self, *args, **karwgs):
        if not self._maps.get((Command.ON, None), None):
            if args[0]:
                self.mapped(command=Command.ON, mapped=Command.OFF)
            else:
                self.mapped(command=Command.ON, mapped=Command.ON)
        if not self._maps.get((Command.OFF, None), None):
            if args[0]:
                self.mapped(command=Command.OFF, mapped=Command.ON)
            else:
                self.mapped(command=Command.OFF, mapped=Command.OFF)
        
    @property
    def state(self):
        return self._get_state()

    @state.setter
    def state(self, value, *args, **kwargs):
        return self._set_state(value, *args, **kwargs)

    def _get_state(self):
        return self._state
    
    def set_state(self, value, *args, **kwargs):
        return self._set_state(value, *args, **kwargs)
    
    def _set_state(self, value, *args, **kwargs):
        source = kwargs.get('source', None)
        if value != self._state:
            self._previous_state = self._state
        self._last_set = datetime.now()
        self._state = value
        return self._state
    
    def __getattr__(self, name):
        # Give this object methods for each command supported
        if self._is_valid_command(name):
            return lambda *a, **k: self.command(name, *a, sub_state=a, **k)

    def command(self, command, *args, **kwargs):
        # Lets process one command at a time please
        with self._command_lock:
            source = kwargs.get('source', None)
            source_property = kwargs.get('source_property', None)
#             if source_property == Property.DELAY:
#                 pass
#             if source_property == Property.IDLE:
#                 pass
#             if source_property == None:
#                 pass
            if not self._is_ignored(command, source):
                m_command = self._process_maps(*args, command=command, **kwargs)
                if m_command != command:
                    self._logger.debug("{name} Map from '{command}' to '{m_command}'".format(
                                                                            name=self.name,
                                                                            command=command,
                                                                            m_command=m_command,
                                                                                             ))

                (state, map_command) = self._command_state_map(m_command, *args, **kwargs)

                if map_command == Command.MANUAL:
                    self._automatic = False
                elif map_command == Command.AUTOMATIC:
                    self._automatic = True
                
                if self._is_restricted(map_command, source):
                    state = None
                    map_command = None
        
                if state and map_command and self._is_valid_state(state):
                    if not self._filter_retrigger_delay(command=map_command, source=source, new_state=state, original_state=self.state, original=command):
                    
                        if source == self or (not self._get_delay(map_command, source, original=command) or not self._automatic):
                            original_state = self.state
                            self._logger.info('{name} changed state from "{original_state}" to "{state}", by command {command} from {source}'.format(
                                                              name=self.name,
                                                              state=state,
                                                              original_state=original_state,
                                                              command=map_command,
                                                              source=source.name if source else None,
                                                                                                                          ))
                            self._set_state(state, source=source)
                            self._cancel_delays(map_command, source, original=command, source_property=source_property)
                            if self._automatic:
                                self._idle_start(command=map_command, source=source, original_command=command)
                            self._previous_command = map_command
                            self._delegate_command(map_command, original_state=original_state, *args, **kwargs)
                            if self._automatic:
                                self._trigger_start(map_command, source, original=command)
                            self._logger.debug('{name} Garbarge Collection queue:{queue}'.format(
                                                                                        name=self.name,
                                                                                        queue=str(StateDevice.dump_garbage()),
                                                                                                 ))
                        else:
                            self._logger.debug("{name} command {command} from {source} was delayed".format(
                                                                                                       name=self.name,
                                                                                                       command=command,
                                                                                                       source=source.name if source else None
                                                                                                       ))
                            self._delay_start(map_command, source, original=command)
                    else:
                        # retrigger
                        self._logger.debug("{name} Retrigger delay ignored command {command} from {source}".format(
                                                                                               name=self.name,
                                                                                               command=command,
                                                                                               source=source.name if source else None
                                                                                               ))
                elif command == Command.STATUS:
                    # If this is a status request, dont set state just pass along the command.
                    self._logger.debug("{name} delgating 'Status' command from {source}".format(
                                                                                               name=self.name,
                                                                                               command=command,
                                                                                               source=source.name if source else None
                                                                                               ))
                    self._delegate_command(command, original_state=self.state, *args, **kwargs)
                else:
                    self._logger.debug("{name} mapped to nothing, ignored command {command} from {source}".format(
                                                                                               name=self.name,
                                                                                               command=command,
                                                                                               source=source.name if source else None
                                                                                               ))
            else:
                self._logger.debug("{name} ignored command {command} from {source}".format(
                                                                                           name=self.name,
                                                                                           command=command,
                                                                                           source=source.name if source else None
                                                                                           ))

    def _command_state_map(self, command, *args, **kwargs):
        source = kwargs.get('source', None)
        state = None
        state = self._command_to_state(command, state)
        m_command = self._state_to_command(state, command)
        if command == Command.LEVEL or (isinstance(command, tuple) and command[0] == Command.LEVEL):
            if isinstance(command, tuple):
                state = (State.LEVEL, command[1:])
                if len(command[1:]) > 1:
                    state = sum([(State.LEVEL, ), command[1:]], ())
                else:
                    state = (State.LEVEL, command[1])
#                m_command = command
            else:
                state = (State.LEVEL, kwargs.get('sub_state', (0,))[0])
#                m_command = (Command.LEVEL,  kwargs.get('sub_state', (0,) ))
            m_command = self._state_to_command(state, m_command)
        elif isinstance(command, tuple) and self._is_valid_command(command[0]) and command[0] != Command.LEVEL:
            m_command = command
            state = self._previous_state
        elif command == Command.PREVIOUS:
            state = self._previous_state
            m_command = self._state_to_command(state, m_command)            
        elif command == Command.TOGGLE:
            state = self.toggle_state()
            m_command = self._state_to_command(state, m_command)
        elif command == Command.INITIAL:
            state = self.state
        elif command == Command.AUTOMATIC or command == Command.MANUAL:
            m_command = command
        return (state, m_command)

    def toggle_state(self):
        if self.state == State.ON:
            state = State.OFF
        else:
            state = State.ON
        return state
    
    def _command_to_state(self, command, state):
        # Try to map the same state ID
        try:
#            state = getattr(State, command)
            primary = command
            if isinstance(command, tuple):
                primary = command[0]
            for attribute in dir(State):
                if getattr(State, attribute) == primary:
                    return command
        except Exception, ex:
            self._logger.debug("{name} Could not find command to state for {command}".format(
                                                                            name=self.name,
                                                                            command=command,                                                                                                                 
                                                                            ))
        return state
    
    def _state_to_command(self, state, command):
        try:
#            return Command['state']
            primary = state
            if isinstance(state, tuple):
                primary = state[0]
            for attribute in dir(Command):
                if getattr(Command, attribute) == primary:
                    return state
            return command
        except Exception, ex:
            self._logger.debug("{name} could not map state {state} to command".format(
                                                                        name=self.name,
                                                                        state=state,
                                                                                                    ))
            return command
    
    def _process_kwargs(self, kwargs):
        # Process each initializing attribute as a method call on this object
        # devices have priority
        if kwargs.get('devices', None):
            try:
                getattr(self, 'devices')( **kwargs['devices'])
            except Exception, ex:
                getattr(self, 'devices')( kwargs['devices'])

        # run through the rest
        for k, v in kwargs.iteritems():
            if k.lower() != 'devices':
                attribute = getattr(self, k)
                if not attribute:
                    self._logger.error('Keyword: "{0}" not found in object construction.'.format(k))
                else:
                    try:
                        attribute(**v)
                    except ValueError, ex:
                        raise ex
                    except Exception, ex:
                        if callable(attribute):
                            if isinstance(v, tuple):
                                for v1 in v:
                                    try:
                                        attribute(**v1)
                                    except Exception, ex:
                                        attribute(v1)
                            else:
                                    attribute(v)
                        else:
                            attribute = v
                
            
    def _process_maps(self, *args, **kwargs):
        source = kwargs.get(Attribute.SOURCE, None)
        command = kwargs.get(Attribute.COMMAND, None)
        mapped = None

        self._logger.debug("{name} MAPS dump: {maps}".format(
                                                name=self.name,
                                                maps=str(self._maps),
                                                            ))

        for (c, s), (target, timer) in self._maps.iteritems():
            commands = []
            sources = []
            if isinstance(s, tuple):
                sources = s
            else:
                sources = (s, )
            if isinstance(c, tuple):
                commands = c
            else:
                commands = (c, )
            
            # Find specific first
            if command in commands and source in sources:
                if not timer or not self._automatic:
                    return target
                else:
                    self._logger.debug('{name} Map Timer Started for command "{command}" from source "{source}" will send "{target}" in "{secs}" secs.'.format(
                                            name=self.name,
                                            source=source.name if source else None,
                                            command=command,
                                            target=target,
                                            secs=timer.interval,
                    ))
                    timer.action(self.command, (target, ), source=self, original=source)
                    timer.restart()
                    return None

            # Go for a more general match next
            if command in commands and None in sources:
                if not timer or not self._automatic:
                    return target
                else:
                    self._logger.debug('{name} Map Timer Started for command "{command}" from source "{source}" will send "{target}" in "{secs}" secs.'.format(
                                            name=self.name,
                                            source=source,
                                            command=command,
                                            target=target,
                                            secs=timer.interval,
                    ))
                    timer.action(self.command, (target, ), source=self, original=source)
                    timer.restart()
                    return None

        
        return command
 
    def _is_valid_state(self, state):
        isFound = state in self.STATES
        if not isFound:
            try:
                isFound = state[0] in self.STATES
            except:
                pass
        if not isFound:
            self._logger.debug("{name} tried to be set to invalid state {state}".format(
                                                                        name=self.name,
                                                                        state=state,
                                                                                        ))
        return isFound

    def _is_valid_command(self, command):
        return command in self.COMMANDS

    def initial(self, state):
        try: # Check to see if this is a device reference
            last_command = state.last_command
            self.command(last_command, source=state)
#            (m_state, m_command) = self._command_state_map(last_command)
#            self.state = m_state
        except: # Just a value
#            self.state = state
            self.command(self._state_to_command(state, None), source=None)
        
    def time(self, *args, **kwargs):
        # time, command
        times = kwargs.get('time', None)
        command = kwargs.get('command', State.UNKNOWN)
        
        if times:
            if not isinstance( times, tuple) or (isinstance(times, tuple) and isinstance(times[0], (long, int))):
                times = (times, )
            for time in times:
                timer = CronTimer()
                if isinstance(time, tuple):
                    timer.interval(*time)
                else:
                    timer.interval(*CronTimer.to_cron(time))
                timer.action(self.command, (command))
                timer.start()
                self._times.append((command, timer))

    def on_command(self, device=None, remove=False):
        if not remove:
            self._delegates.append(device)
        else:
            self._delegates.remove(device)
    
    def _delegate_command(self, command, *args, **kwargs):
        source = kwargs.get('source', None)
        original_state = kwargs.get('original_state', None)
        
        for delegate in self._delegates:
#            print "here {name} s:{source} d:{delegate}".format(
#                                                               name=self.name,
#                                                               source=source.name if source else None,
#                                                               delegate=delegate.name if delegate else None,
#                                                               )
            if delegate != self and source != delegate and \
                (not self._changes_only or \
                (self._changes_only and self._state != original_state)):
                self._logger.debug("{name} delegating command {command} from {source} to object {delegate}".format(
                                                                                   name=self.name,
                                                                                   command=command,
                                                                                   source=source.name if source else None,
                                                                                   delegate=delegate.name,
                                                                           ))
                delegate.command(command=command, source=self)
            else:
                self._logger.debug("{name} Avoid duplicate delegation of {command} from {source} to object {delegate}".format(
                                                                                   name=self.name,
                                                                                   command=command,
                                                                                   source=source.name if source else None,
                                                                                   delegate=delegate.name,
                                                                           ))
                
    def devices(self, *args, **kwargs):
        devices = args[0]

        if not isinstance(devices, tuple):
            devices = (devices, )
                   
        for device in devices:
            if device:
                self._add_device(device)

    def add_device(self, device):
        return self._add_device(device)

    def _add_device(self, device):
        if not isinstance(device, dict):
            self._devices.append(device)
            self._logger.debug("{name} added new device {device}".format(
                                                                         name=self.name,
                                                                         device=device.name,
                                                                         ))
            return device.on_command(device=self)
        return True

    def remove_device(self, device):
        if device in self._devices:
            device.on_command(device=self, remove=True)
            self._devices.remove(device)
            return True
        else:
            return False
    
    def mapped(self, *args, **kwargs):
        command = kwargs.get('command', None)
        mapped = kwargs.get('mapped', None)
        source = kwargs.get('source', None)
        secs = kwargs.get('secs', None)
        timer = None
        commands = command
        if not isinstance(command, tuple):
            commands = (command, )
        for c in commands:
            if secs:
                timer = CTimer()
                timer.interval = secs
                timer.action(self.command, (mapped, ), source=self, original=source)
    #        self._maps.append({'command': command, 'mapped': mapped, 'source': source})
            sources = source
            if not isinstance(source, tuple):
                sources = (source ,)
            for s in sources:
                self._maps.update({(c, s): (mapped, timer)}) 
            
    def delay(self, *args, **kwargs):
        commands = kwargs.get('command', None)
        if (not isinstance(commands, tuple)):
            commands = (commands, )
        mapped = kwargs.get('mapped', None)
        sources = kwargs.get('source', None)
        if (not isinstance(sources, tuple)):
            sources = (sources, )
        secs = kwargs.get('secs', None)
        
        for command in commands:
            for source in sources:
                if not mapped:
                    m = command
                else:
                    m = mapped
                timer = CTimer()
                timer.interval=secs
                timer.action(self.command, (m, ), source=self, original=source, source_property=Property.DELAY)
                self._delays.update({(command, source): {'mapped': m, 'secs': secs, 'timer': timer}})
        return True

    def _get_delay(self, command, source, original=None, include_zero=False):
        delay = self._delays.get((command, source), None)
        if not delay and original:
            delay = self._delays.get((original, source), None)
        if delay:
            if delay['secs'] > 0 or include_zero:
                return delay
            else:
                return None
        
        delay = self._delays.get((command, None), None)
        if not delay and original:
            delay = self._delays.get((original, None), None)
        if delay and (delay['secs'] > 0 or include_zero):
            return delay

        return None       
    
    def _cancel_delays(self, command, source, original=None, source_property=None):
        if not self._get_delay(command, source, original) and source_property != Property.IDLE:
            for c, timer in self._delay_timers.iteritems():
                self._logger.debug("{name} stopping an existing delay timer of '{interval}' secs for command: '{command}' because the same non-delayed command was now processed. From {source} original command {original}".format(
                                                                                           name=self.name,
                                                                                           command=command,
                                                                                           source=source.name if source else None,
                                                                                           interval=timer.interval,
                                                                                           original=original,
                                                                                           ))
                timer.stop()

    def _delay_start(self, command, source, *args, **kwargs):
        original_command = kwargs.get('original', None)
        delay = self._get_delay(command, source, original_command, include_zero=True)
        if delay:
            timer = self._delay_timers.get(delay['mapped'], None)
            if not timer:
                timer = CTimer()
            timer.stop()
            if delay['secs'] > 0:
                timer.action(self.command, (delay['mapped'], ), source=self, original=source, source_property=Property.DELAY)
                timer.interval = delay['secs']
                self._delay_timers.update({delay['mapped']: timer} )
                timer.start()
                self._logger.debug('{name} command "{command}" from source "{source}" delayed, mapped to "{mapped}" waiting {secs} secs. '.format(
                                                                                      name=self.name,
                                                                                      source=source.name if source else None,
                                                                                      command=command,
                                                                                      mapped=delay['mapped'],
                                                                                      secs=delay['secs'],
                                                                                ))

    @property
    def idle_time(self):
        difference = datetime.now() - self._last_set
        return difference.total_seconds()

    def idle(self, *args, **kwargs):
        command = kwargs.get('command', None)
        source = kwargs.get('source', None)
        mapped = kwargs.get(Attribute.MAPPED, None)
        secs = kwargs.get('secs', None)
        if secs:
            timer = CTimer()
            timer.interval = secs
            timer.action(self.command, (mapped, ), source=self, original=source, source_property=Property.IDLE)
#            self._idle_timer = timer
            self._idle_timer.update({(command, source): {Attribute.SECS: secs, 
                                                         Attribute.MAPPED: mapped,
                                                         'timer': timer}})
            
    def _idle_start(self, *args, **kwargs):
        command = kwargs.get('command', None)
        source = kwargs.get('source', None)
        original_command = kwargs.get('original_command', None)
        idle = self._idle_timer.get((command, source), None)
        if not idle:
            idle = self._idle_timer.get((original_command, source), None)
        if not idle:
            idle = self._idle_timer.get((None, source), None)
        if not idle:
            idle = self._idle_timer.get((Command, None), None)
        if not idle:
            idle = self._idle_timer.get((None, None), None)
        if idle:
            if idle[Attribute.MAPPED] and source != self and self.state != State.OFF:
                timer = idle['timer']
                timer.action(self.command, (idle[Attribute.MAPPED], ), source=self, original=source, source_property=Property.IDLE)
                timer.start()
        
        
    def ignore(self, *args, **kwargs):
        commands = kwargs.get('command', None)
        sources = kwargs.get('source', None)
        start = kwargs.get(Attribute.START, None)
        end = kwargs.get(Attribute.END, None)

        if not isinstance(commands, tuple):
            commands = (commands, )
        if not isinstance(sources, tuple):
            sources = (sources, )

        for command in commands:
            for source in sources:
                self._ignores.update({
                                      (command, source): {
                                                          Attribute.START: CronTimer.to_cron(start),
                                                         Attribute.END: CronTimer.to_cron(end),
                                                     }
                                      })
                self._logger.debug("{name} add ignore for {command} from {source}".format(
        										name=self.name,
        										command=command,
        										source=source.name if source else None,
        										));
        
    def _is_ignored(self, command, source):
        is_ignored = False
        self._logger.debug("{name} check ignore for {command} from {source}".format(
                                        name=self.name,
                                        command=command,
                                        source=source.name if source else None,
                                        ));

        
        match = self._match_condition(command, source, self._ignores)
        if match:
            return True
        else:
            return False
        

    def restriction(self, *args, **kwargs):
        states = kwargs.get(Attribute.STATE, None)
        sources = kwargs.get(Attribute.SOURCE, None)
        targets = kwargs.get(Attribute.TARGET, None)
        start = kwargs.get(Attribute.START, None)
        end = kwargs.get(Attribute.END, None)

        if not isinstance(states, tuple):
            states = (states, )
        if not isinstance(sources, tuple):
            sources = (sources, )
        if not isinstance(targets, tuple):
            targets = (targets, )
        
        for state in states:
            for source in sources:
                for target in targets:
                    self._restrictions.update({
                                          (state, source, target): {
                                                              Attribute.START: CronTimer.to_cron(start),
                                                             Attribute.END: CronTimer.to_cron(end),
                                                         }
                                          })
                    self._logger.debug("{name} add restriction for {state} from {source} on {target}".format(
                                                    name=self.name,
                                                    state=state,
                                                    target=target,
                                                    source=source.name if source else None,
                                                    ));

    def _is_restricted(self, command, source):
        if self._restrictions and source != self:
            for state, source, target in self._restrictions:
                c_state = source.state
                if (state == c_state and (target==None or target==command)):
                    if (self._match_condition_item(self._restrictions.get((state, source, target)))):
                        self._logger.debug("{name} Restricted. ignoring".format(
                                                                             name=self.name,
                                                                             ))
                        return True

        return False
    
    def _match_condition(self, command, source, conditions):
        # Specific match first
        cond = self._match_condition_item(self._get_condition(command, source, conditions))
        if cond:
            return cond
        cond = self._match_condition_item(self._get_condition(command, None, conditions))
        if cond:
            return cond
        cond = self._match_condition_item(self._get_condition(None, source, conditions))
        if cond:
            return cond
        cond = self._match_condition_item(self._get_condition(None, None, conditions))
        if cond:
            return cond
        
    def _get_condition(self, command, source, conditions):
        result = conditions.get((command, source), None)

        if not result: # Check for substate matches as well (Command.LEVEL, etc)
            if isinstance(command, tuple):
                result = conditions.get((command[0], source), None)
        return result
                    
    
    def _match_condition_item(self, item):
        if not item:
            return None

        start = item.get(Attribute.START, None)
        if start:
            end = item.get(Attribute.END, None)
            if end:
                now = datetime.now().timetuple()[3:6]
                now_cron = CronTimer.to_cron("{h}:{m}:{s}".format(
                                                                  h=now[0],
                                                                  m=now[1],
                                                                  s=now[2],
                                                                  ))
                result = crontime_in_range(now_cron, start, end)
                self._logger.debug("Compare Time Range:("+ str(result) +")->" + str(now_cron) +"-" + str(start) + "-"+ str(end))
                return result 
        return item

    def trigger(self, *args, **kwargs):
        commands = kwargs.get(Attribute.COMMAND, None)
        sources = kwargs.get(Attribute.SOURCE, None)
        mapped = kwargs.get(Attribute.MAPPED, None)
        secs = kwargs.get(Attribute.SECS, None)
        start = kwargs.get(Attribute.START, None)
        end = kwargs.get(Attribute.END, None)
        
        if not isinstance(commands, tuple):
            commands = (commands, )
        if not isinstance(sources, tuple):
            sources = (sources, )
        
        for command in commands:
            for source in sources:
                m = None
                if not mapped:
                    m = command
                else:
                    m = mapped
                self._triggers.update({(command, source): {Attribute.SECS: secs, 
                                                           Attribute.MAPPED: m,
                                                           Attribute.START: CronTimer.to_cron(start),
                                                           Attribute.END: CronTimer.to_cron(end),
                                                           }})
        
#        timer = CTimer()
#        timer.interval=secs
#        timer.action(self.command, (mapped, ), source=self, original=source)
#        self._triggers.append({'command': command, 'mapped': mapped, 'source': source, 'secs': secs, 'timer': timer})

    def _trigger_start(self, command, source, *args, **kwargs):
        original_command = kwargs.get('original', None)
        trigger = self._triggers.get((command, source), None)
        if not trigger and original_command:
            trigger = self._triggers.get((original_command, source), None)
        if not trigger:
            trigger = self._triggers.get((command, None), None)
        if not trigger:
            trigger = self._triggers.get((original_command, None), None)
##       trigger = self._match_condition(command, source, self._triggers)
        
        if trigger and self._match_condition_item(trigger):
            timer = self._trigger_timers.get(trigger[Attribute.MAPPED], None)
            if not timer:
                timer = CTimer()
            timer.stop()
            if trigger[Attribute.SECS] > 0:
                timer.action(self.command, (trigger[Attribute.MAPPED], ), source=self, original=source)
                timer.interval = trigger[Attribute.SECS]
                self._trigger_timers.update({trigger[Attribute.MAPPED]: timer} )
                timer.start()
                self._logger.debug('{name} command "{command}" from source "{source}" trigger started, mapped to "{mapped}" waiting {secs} secs. '.format(
                                                                                      name=self.name,
                                                                                      source=source.name if source else None,
                                                                                      command=command,
                                                                                      mapped=trigger[Attribute.MAPPED],
                                                                                      secs=trigger[Attribute.SECS],
                                                                                ))  
            
        
#        for trigger in self._triggers:
#            if trigger['command'] == command and \
#            (not trigger['source'] or trigger['source'] == source):
#                trigger['timer'].action(self.command, (trigger['mapped'], ), source=self, original=source)
#                trigger['timer'].start()
                
    def _initial_from_devices(self, *args, **kwargs):
        state = None
        if self.state == State.UNKNOWN:
            for device in self._devices:
#                state = device.state
                (state, command) =  self._command_state_map(device.last_command)
                if state:
                    self.initial(device)
                    self._logger.debug("{name} initial for {command} from {state}".format(
        										name=self.name,
        										command=command,
        										state=state,
        										));
        return
    
    @property
    def last_command(self):
        return self._previous_command
    
    def changes_only(self, value):
        self._changes_only=value
        return self._changes_only
    
    def retrigger_delay(self, *args, **kwargs):
        secs = kwargs.get('secs', None)
        self._retrigger_delay = CTimer()
        self._retrigger_delay.interval = secs       

    def _filter_retrigger_delay(self, *args, **kwargs):
        """
        If there is a need to squelch multiple of the same command within a certain timeframe
        """
        command = kwargs.get('command', None)
        original_state = kwargs.get('original_state', None)
        new_state = kwargs.get('new_state', None)
        if new_state == original_state and self._retrigger_delay and self._retrigger_delay.isAlive():
            return True
        elif new_state != original_state and self._retrigger_delay:
            self._retrigger_delay.restart()
        return False          

    @staticmethod
    def dump_garbage():
        """
        show us what's the garbage about
        """
        c=-1
        # force collection
    #    print "\nGARBAGE:"
        gc.collect()
    
    #    print "\nGARBAGE OBJECTS:"
#        for x in gc.garbage:
#            s = str(x)
#            if len(s) > 80: s = s[:80]
#            print type(x),"\n  ", s
        try:
            c = len(gc.garbage)
        except:
            pass
        return c

########NEW FILE########
__FILENAME__ = thermostat
from pytomation.devices import InterfaceDevice, State
from pytomation.interfaces import Command

class Thermostat(InterfaceDevice):
    STATES = [State.UNKNOWN, State.OFF, State.HEAT, State.COOL, State.LEVEL, State.CIRCULATE, State.AUTOMATIC, State.HOLD, State.VACANT, State.OCCUPIED]
    COMMANDS = [Command.AUTOMATIC, Command.MANUAL, Command.COOL, Command.HEAT, Command.HOLD, Command.SCHEDULE, Command.OFF, Command.LEVEL, Command.STATUS, Command.CIRCULATE, Command.STILL, Command.VACATE, Command.OCCUPY]


    
    def __init__(self, *args, **kwargs):
        for level in range(32,100):
            self.COMMANDS.append((Command.LEVEL, level))
            
        self._level = None
        self._setpoint = None
        self._automatic_mode = False
        self._automatic_delta = 0
        self._away_delta = 0
        self._away_mode = False
        self._current_mode = None
        self._last_temp = None
        self._sync_interface = False

        super(Thermostat, self).__init__(*args, **kwargs)
    
    def _send_command_to_interface(self, interface, address, command):
        try:
            super(Thermostat, self)._send_command_to_interface(interface, address, command)
        except (AttributeError, TypeError) as ex:
            if command == Command.AUTOMATIC:
                #Thermostat doesnt have Automatic mode
                self._automatic_mode = True
                self.automatic_check()
    
    def automatic_check(self):
        self._logger.debug('Automatic Check a:{0} ad:{1} set:{2} state:{3} ltemp:{4} mode:{5}'.format(
                                                                                 self._automatic_mode,
                                                                                 self._automatic_delta,
                                                                                 self._setpoint,
                                                                                 str(self._state),
                                                                                 self._last_temp,
                                                                                 self._current_mode,
                                                                                 ))

        if self._automatic_mode:
            if self._state and self._setpoint and isinstance(self._state, tuple) and self._state[0] == State.LEVEL and self._state[1] != self._setpoint:
                previous_temp = self._state[1]
                if (self._state[1] < self._setpoint - self._automatic_delta and not self._away_mode) or \
                        (self._away_mode and self._state[1] < self._setpoint - self._away_delta):
                    # If the current mode isnt already heat or for some wild reason we are heading in the wrong dir
                    if self._current_mode != Command.HEAT or \
                        (self._last_temp and self._last_temp > self._state[1]) or \
                        self._sync_interface:
                        self._clear_sync_with_interface()
                        self.heat(address=self._address, source=self)
                elif (self._state[1] > self._setpoint + self._automatic_delta and not self._away_mode) or \
                        (self._away_mode and self._state[1] > self._setpoint + self._away_delta):
                    # If the current mode isnt already cool or for some wild reason we are heading in the wrong dir
                    if self._current_mode != Command.COOL or \
                        (self._last_temp and self._last_temp < self._state[1]) or \
                        self._sync_interface:
                        self._clear_sync_with_interface()
                        self.cool(address=self._address, source=self)
                self._last_temp = previous_temp

    def command(self, command, *args, **kwargs):
        source = kwargs.get('source', None)
        primary_command = command
        secondary_command = None
        if len(args) > 0:
            secondary_command=args[0]

        if isinstance(primary_command, tuple):
            primary_command=command[0]
            secondary_command=command[1]
        
        if primary_command == Command.LEVEL and \
            (source != self or not source) and \
            source not in self._interfaces:
            self._setpoint = secondary_command

        if primary_command == Command.HEAT:
            self._current_mode = Command.HEAT
        elif primary_command == Command.COOL:
            self._current_mode = Command.COOL
        elif primary_command == Command.OFF:
            self._current_mode = Command.OFF
        elif primary_command == Command.AUTOMATIC:
            self._current_mode = Command.AUTOMATIC
        elif primary_command == Command.MANUAL:
            self._automatic_mode = False
        elif primary_command == Command.VACATE:
            self._sync_with_interface()
            self._away_mode = True
        elif primary_command == Command.OCCUPY:
            self._sync_with_interface()
            self._away_mode = False
            

        result = super(Thermostat, self).command(command, *args, **kwargs)
        
        self.automatic_check()
        return result
        
    def automatic_delta(self, value):
        self._automatic_delta = value
        
    def away_delta(self, value):
        self._away_delta = value
        
    def _sync_with_interface(self):
        self._sync_interface = True
    
    def _clear_sync_with_interface(self):
        self._sync_interface = False
        
########NEW FILE########
__FILENAME__ = xmpp_client
import ssl

try:
    import xmpp
except:
    pass
import re
import time

from pytomation.devices import Door, StateDevice, State
from pytomation.interfaces import Command

class XMPP_Client(StateDevice):
    STATES = [State.UNKNOWN, State.ON, State.OFF]
    COMMANDS = [Command.MESSAGE]

    def __init__(self, *args, **kwargs):
        self._xmpp = None
        super(XMPP_Client, self).__init__(*args, **kwargs)

    def _initial_vars(self, *args, **kwargs):
        super(XMPP_Client, self)._initial_vars(*args, **kwargs)
        self._xmpp_id = kwargs.get('id',None)
        self._password = kwargs.get('password', None)
        self._server = kwargs.get('server', None)
        self._port = kwargs.get('port', None)

        if not self._xmpp:
            self._logger.info('Connecting to server for id:{id} ({server})'.format(
                                                   id=self._xmpp_id,
                                                   server=self._server,
                                                                                   ))
            status = None
            jid = xmpp.JID(self._xmpp_id)
            self._xmpp = xmpp.Client(jid.getDomain())
            self.connect()
            self._logger.info("Connection Result: {0}".format( status))
            result = self._xmpp.auth(re.match('(.*)\@.*', self._xmpp_id).group(1), self._password,'TESTING')
            #self._xmpp.sendInitPresence()   
            self._logger.debug('Processing' + str(result))
        else:
            self._logger.debug('Here twice?')

    def connect(self):
        status = None
        if self._server:
            status = self._xmpp.connect(server=(self._server,self._port))
        else:
            status = self._xmpp.connect()
        return status

    def _delegate_command(self, command, *args, **kwargs):
        self._logger.debug('Delegating')

        if isinstance(command, tuple) and command[0] == Command.MESSAGE:            
            self._logger.debug('Sending Message')
#             result = self._xmpp.send_message(mto=command[1],
#                                       mbody=command[2],
#                                       mtype='chat')
            message = xmpp.Message( command[1] ,command[2]) 
            message.setAttr('type', 'chat')
            try:
                self._xmpp.send(message )
            except IOError, ex:
                try:
                    self.connect()
                    self._xmpp.send(message )
                except IOError, ex1:
                    self._logger.error('Could not reconnect:' + str(ex1))
                except Exception, ex1:
                    self._logger.error('Could not reconnect error:' + str(ex1))
            except Exception, ex:
                self._logger.error('Unknown Error: ' + str(ex))
                
#            time.sleep(5)
        super(XMPP_Client, self)._delegate_command(command, *args, **kwargs)

        
    
########NEW FILE########
__FILENAME__ = arduino
"""
File: 
    arduino_uno.py

George Farris <farrisg@gmsys.com>
Copyright (c), 2013

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
MA 02110-1301, USA.



Description:

This is a driver for the Arduino UNO board used with the included uno.pde 
sketch.  The UNO board supports digital and analog I/O.  The Uno board can be 
configured to use up 18 digital I/O channels or 12 digital and 6 analog 
channels or a combination of both.

This driver will re-initialize any of the boards that experience a power on 
reset or brownout without having to restart Pytomation.

The the I/O channels on the Andunio board are set according to the following 
command set.

Every command sent to the board is three or four characters in length.  There 
is no terminating CR or NL character.

  [Board] [I/O direction] [Pin]
  ===========================================================================
  [Board] 	- 'A'
  [I/O]		- 'DN<pin>' Configure as Digital Input no internal pullup (default)
  			- 'DI<pin>'     "      " Digital Input uses internal pullup
	  		- 'DO<pin>'     "      " Digital Output 
	  		- 'AI<pin>'     "      " Analog Input
			- 'AO<pin>'     "      " Analog Output
	        - 'L<pin>'  Set Digital Output to LOW
	        - 'H<pin>'  Set Digital Output to HIGH
			- '%<pin><value>'  Set Analog Output to value (0 - 255)
  [Pin]		- Ascii 'C' to 'T'  C = pin 2, R = pin A3, etc
 
  Examples transmitted to board:
    ADIF	Configure pin 5 as digital input with pullup
	AAIR	Configure pin A3 as analog input
	AHE		Set digital pin 4 HIGH
	A%D75	Set analog output to value of 75

  Examples received from board:  NOTE the end of message (eom) char '.'
	AHE.		Digital pin 4 is HIGH
	ALE.		Digital pin 4 is LOW
	AP89.		Analog pin A1 has value 89
	
  Available pins, pins with ~ can be analog Output
                  pins starting with A can be Analog Input
                  All pins can be digital except 0 and 1
  ----------------------------------------------------------------------------
  02 03 04 05 06 07 08 09 10 11 12 13 A0 A1 A2 A3 A4 A5
  C  D  E  F  G  H  I  J  K  L  M  N  O  P  Q  R  S  T
     ~     ~  ~        ~  ~  ~
  ============================================================================ 
  The board will return a '?' on error.
  The board will return a '!' on power up or reset.


Author(s):
         George Farris <farrisg@gmsys.com>
         Copyright (c), 2013


License:
    This free software is licensed under the terms of the GNU public license, 
    Version 3

Usage:

    see /example_Arduino_use.py

Notes:
    For documentation on the Ardunio Uno please see:
    http://arduino.cc/en/Main/arduinoBoardUno

    This driver only supports 1 board at present.

Versions and changes:
    Initial version created on Feb 14, 2013
    2013/02/14 - 1.0 - Initial version
    
"""
import threading
import time
import re
from Queue import Queue
from binascii import unhexlify

from .common import *
from .ha_interface import HAInterface


class Arduino(HAInterface):
    VERSION = '1.0'
    MODEM_PREFIX = ''
    
    
    def __init__(self, interface, *args, **kwargs):
        super(Arduino, self).__init__(interface, *args, **kwargs)
        
    def _init(self, *args, **kwargs):
        super(Arduino, self)._init(*args, **kwargs)

        self.version()
        self.boardSettings = []
        self._modemRegisters = ""

        self._modemCommands = {
                               }

        self._modemResponse = {
                               }
        # for inverting the I/O point 
        self.d_inverted = [False for x in xrange(19)]
        #self._interface.read(100)        
        		
    def _readInterface(self, lastPacketHash):
        #check to see if there is anyting we need to read
        responses = self._interface.read()
        if len(responses) != 0:
            for response in responses.split():
                self._logger.debug("[Arduino] Response> " + hex_dump(response))
                d = re.compile('[A][C-T][H,L][\.]')
                a = re.compile('[A][O-T][0-9]*[\.]')    
                if d.match(response):
                    # strip end of message :a.index('.')
                    self._processDigitalInput(response[:response.index('.')], lastPacketHash)
                elif a.match(response):
                    self._processAnalogInput(response[:response.index('.')], lastPacketHash)
                elif response[0] == '!':
                    self._logger.debug("[Arduino] Board [" + response[0] + "] has been reset or power cycled, reinitializing...\n")
                    for bct in self.boardSettings:
                        self.setChannel(bct)
                elif response[1] == '?':
                    self._logger.debug("[Arduino] Board [" + response[0] + "] received invalid command or variable...\n")
                    
        else:
            time.sleep(0.1)  # try not to adjust this 

    # response[0] = board, response[1] = channel, response[2] = L or H    
    def _processDigitalInput(self, response, lastPacketHash):
        if (response[2] == 'L' and not self.d_inverted[ord(response[1]) - 65]):
        #if (response[2] == 'L'):
            contact = Command.OFF
        else:
            contact = Command.ON
        self._onCommand(address=response[:2],command=contact)

    # response[0] = board, response[1] = channel, response[2 to end] = value
    def _processAnalogInput(self, response, lastPacketHash):
        self._onCommand(address=response[:2],command=(Command.LEVEL, response[2:]))


    def _processRegister(self, response, lastPacketHash):
        foundCommandHash = None

        #find our pending command in the list so we can say that we're done (if we are running in syncronous mode - if not well then the caller didn't care)
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
            if commandDetails['modemCommand'] == self._modemCommands['read_register']:
                #Looks like this is our command.  Lets deal with it
                self._commandReturnData[commandHash] = response[4:]

                waitEvent = commandDetails['waitEvent']
                waitEvent.set()

                foundCommandHash = commandHash
                break

        if foundCommandHash:
            del self._pendingCommandDetails[foundCommandHash]
        else:
            self._logger.debug("[Arduino] Unable to find pending command details for the following packet:\n")
            self._logger.debug((hex_dump(response, len(response)) + '\n'))


    # Initialize the Uno board, input example "ADIC"
    def setChannel(self, boardChannelType):
        p = re.compile('[A][A,D][I,N,O][C-T]')
        if not p.match(boardChannelType):
            self._logger.debug("[Arduino] Error malformed command...   " + boardChannelType + '\n')
            return
        # Save the board settings in case we need to re-init
        if not boardChannelType in self.boardSettings:
            self.boardSettings.append(boardChannelType)
        
        self._logger.debug("[Arduino] Setting channel " + boardChannelType + '\n')
        command = boardChannelType
        commandExecutionDetails = self._sendInterfaceCommand(command)

    def dio_invert(self, channel, value=True):
        self.d_inverted[ord(channel) - 65] = value
                    
    def on(self, address):
        command = address[0] + 'H' + address[1]
        commandExecutionDetails = self._sendInterfaceCommand(command)
#        return self._waitForCommandToFinish(commandExecutionDetails, timeout=2.0)

    def off(self, address):
        command = address[0] + 'L' + address[1]
        commandExecutionDetails = self._sendInterfaceCommand(command)
#        return self._waitForCommandToFinish(commandExecutionDetails, timeout=2.0)

    def level(self, address, level, timeout=None, rate=None):
        command = address[0] + '%' + address[1] + level
        commandExecutionDetails = self._sendInterfaceCommand(command)

		
    def listBoards(self):
        self._logger.info(self.boardSettings + '\n')
        
    def version(self):
        self._logger.info("Ardunio Pytomation driver version " + self.VERSION + '\n')


########NEW FILE########
__FILENAME__ = cm11a
"""
File: 
    cm11a.py

George Farris <farrisg@gmsys.com>
Copyright (c), 2013

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
MA 02110-1301, USA.



Description:

This is a driver for the X10 CM11a
The serial parameters for communications between the interface and PC
are as follows:

	Baud Rate:	4,800bps
	Parity:		None
	Data Bits:	8
	Stop Bits:	1

2.1 Cable connections:

        Signal  DB9 Connector   RJ11 Connector
        SIN     Pin 2           Pin 1
        SOUT    Pin 3           Pin 3
        GND     Pin 5           Pin 4
        RI      Pin 9           Pin 2

where:  SIN     Serial input to PC (output from the interface)
        SOUT    Serial output from PC (input to the interface)
        GND     Signal ground
        RI      Ring signal (input to PC)

The housecodes and device codes range from A to P and 1 to 16
respectively although they do not follow a binary sequence. The encoding
format for these codes is as follows

	Housecode	Device Code	Binary Value	Hex Value
	A		1		0110		6
	B		2		1110		E
	C		3		0010		2
	D		4		1010		A
	E		5		0001		1
	F		6		1001		9
	G		7		0101		5
	H		8		1101		D
	I		9		0111		7
	J		10		1111		F
	K		11		0011		3
	L		12		1011		B
	M		13		0000		0
	N		14		1000		8
	O		15		0100		4
	P		16		1100		C

1.2	Function Codes.

	Function			Binary Value	Hex Value
	All Units Off			0000		0
	All Lights On			0001		1
	On				0010		2
	Off				0011		3
	Dim				0100		4
	Bright				0101		5
	All Lights Off			0110		6
	Extended Code			0111		7
	Hail Request			1000		8
	Hail Acknowledge		1001		9
	Pre-set Dim (1)			1010		A
	Pre-set Dim (2)			1011		B
	Extended Data Transfer		1100		C
	Status On			1101		D
	Status Off			1110		E
	Status Request			1111		F

Here's a log of A1, A ON.

05/03/05 7:14:09 AM > [04 66]
05/03/05 7:14:09 AM < [6A]
05/03/05 7:14:09 AM > [00]
05/03/05 7:14:10 AM < [55]
05/03/05 7:14:10 AM > [0E 62]
05/03/05 7:14:10 AM < [70]
05/03/05 7:14:10 AM > [00]
05/03/05 7:14:10 AM < [55]

Author(s):
         George Farris <farrisg@gmsys.com>
         Copyright (c), 2013


License:
    This free software is licensed under the terms of the GNU public license, 
    Version 3

Usage:

    see /example_CM11a_use.py


Versions and changes:
    Initial version created on Mar 1, 2013
    2013/03/04 - 1.0 - Initial version
    
"""
import threading
import time
import re
from Queue import Queue
from binascii import unhexlify

from .common import *
from .ha_interface import HAInterface

def simpleMap(value, in_min, in_max, out_min, out_max):
    return ((float(value) - float(in_min)) * (float(out_max) - float(out_min)) / (float(in_max) - float(in_min)) + float(out_min))
    
class CM11a(HAInterface):
    VERSION = '1.0'
    MODEM_PREFIX = ''
    
    def __init__(self, interface, *args, **kwargs):
        super(CM11a, self).__init__(interface, *args, **kwargs)
        
    def _init(self, *args, **kwargs):
        super(CM11a, self)._init(*args, **kwargs)

        self.version()
        self.ready = True   # if interface is ready to rx command
        self.chksum = 0	    # checksum for command
	
        self._houseCode = {
                'A':0x60, 'B':0xE0, 'C':0x20, 'D':0xA0, 'E':0x10,
                'F':0x90, 'G':0x50, 'H':0xD0, 'I':0x70, 'J':0xF0,
                'K':0x30, 'L':0xB0, 'M':0x00, 'N':0x80, 'O':0x40,
                'P':0xC0}
                            
        self._unitCode = {
                '1':0x06, '2':0x0E, '3':0x02, '4':0x0A, '5':0x01,
                '6':0x09, '7':0x05, '8':0x0D, '9':0x07, '10':0x0F,
                '11':0x03, '12':0x0B, '13':0x00, '14':0x08, '15':0x04,
                '16':0x0C}

    def _readInterface(self, lasPacketHash):
	time.sleep(0.5)
	
	
    def _sendInterfaceCommand(self, hCode, uCode, command, level=0x06,):
	chksum = 0
	byte0 = 0x04
	byte1 = hCode + uCode
	self._logger.debug("[CM11a] Transmit > {b0} {b1}".format(b0=hex(byte0), b1=hex(byte1)))
	while (chksum != ((byte0 + byte1) & 0xFF)):
	    self._interface.write(chr(byte0) + chr(byte1))
	    chksum = ord(self._interface.read(1))

	self._interface.write(chr(0))

	ready = 0
	loop = 0
	while (ready != 0x55):
	    if self._interface.inWaiting() == 0:
		time.sleep(0.1)
		loop += 1
		if loop > 30:
		    self._logger.debug("[CM11a] Error waiting for response from interface, giving up...")
		    break
	    	continue
	    ready = ord(self._interface.read(1))

	byte0 = level | 0x06
	byte1 =  hCode + command
	chksum = 0
	self._logger.debug("[CM11a] Transmit > {b0} {b1}".format(b0=hex(byte0), b1=hex(byte1)))
	while (chksum != ((byte0 + byte1) & 0xFF)):
	    self._interface.write(chr(byte0))
	    self._interface.write(chr(byte1))
	    chksum = ord(self._interface.read())

	self._interface.write(chr(0))

	ready = 0
	loop = 0
	while (ready != 0x55):
	    if self._interface.inWaiting() == 0:
		time.sleep(0.1)
		loop += 1
		if loop > 50:  # need longer delay here when dimming
		    self._logger.debug("[CM11a] Error waiting for response from interface, giving up...")
		    break
	    	continue
	    ready = ord(self._interface.read())
	
    def on(self, address):
	hc = self._houseCode[address[0]]
	uc = self._unitCode[address[1]]
	self._logger.debug("[CM11a] Sending ON to address> " + address)
	self._sendInterfaceCommand(hc, uc, 2)
	        
    def off(self, address):
	hc = self._houseCode[address[0]]
	uc = self._unitCode[address[1]]
	self._logger.debug("[CM11a] Sending OFF to address> " + address)
	self._sendInterfaceCommand(hc, uc, 3)

    def level(self, address, level, rate=None, timeout=None):
	hc = self._houseCode[address[0]]
	uc = self._unitCode[address[1]]
	self._logger.debug("[CM11a] Sending DIM to address> " + address)
	lv = int(simpleMap(level,1,100,248,8)) & 0xF8	# min and max out are reversed
	self._sendInterfaceCommand(hc, uc, 4, lv)

    def version(self):
        self._logger.info("CM11a Pytomation driver version " + self.VERSION + '\n')


########NEW FILE########
__FILENAME__ = common
'''

File:
        ha_common.py

Description:
        Library of Home Automation code for Python


Author(s): 
         Jason Sharpee <jason@sharpee.com>  http://www.sharpee.com
        Pyjamasam <>

License:
    This free software is licensed under the terms of the GNU public license, Version 1     

Usage:
    - 


Example: (see bottom of file) 


Notes:
    - Common functionality between all of the classes I am implementing currently.

Created on Apr 3, 2011

@author: jason
'''

import threading
import traceback
import socket
import binascii
import serial
import hashlib
import sys
import urllib, urllib2
import requests

from pytomation.common.pytomation_object import PytomationObject


class Lookup(dict):
    """
    a dictionary which can lookup value by key, or keys by value
    # tested with Python25 by Ene Uran 01/19/2008    http://www.daniweb.com/software-development/python/code/217019
    """
    def __init__(self, items=[]):
        """items can be a list of pair_lists or a dictionary"""
        dict.__init__(self, items)

    def get_key(self, value):
        """find the key as a list given a value"""
        if type(value) == type(dict()):
            items = [item[0] for item in self.items() if item[1][value.items()[0][0]] == value.items()[0][1]]
        else:
            items = [item[0] for item in self.items() if item[1] == value]
        return items[0]

    def get_keys(self, value):
        """find the key(s) as a list given a value"""
        return [item[0] for item in self.items() if item[1] == value]

    def get_value(self, key):
        """find the value given a key"""
        return self[key]

class Command(object):
    ON = 'on'
    OFF = 'off'
    L10 = 'l10'
    L20 = 'l20'
    L30 = 'l30'
    L40 = 'l40'
    L50 = 'l50'
    L60 = 'l60'
    L70 = 'l70'
    L80 = 'l80'
    L90 = 'l90'
    LEVEL = 'level'
    PREVIOUS = 'previous'
    TOGGLE = 'toggle'
    BRIGHT = 'bright'
    DIM = 'dim'
    ACTIVATE = 'activate'
    DEACTIVATE = 'deactivate'
    INITIAL = 'initial'
    MOTION = 'motion'
    STILL = 'still'
    DARK = 'dark'
    LIGHT = 'light'
    OPEN = 'open'
    CLOSE = 'close'
    AUTOMATIC = 'automatic'
    MANUAL = 'manual'
    OCCUPY = 'occupy'
    VACATE = 'vacate'
    STATUS = 'status'
    VOICE = 'voice'
    COOL = 'cool'
    HEAT = 'heat'
    CIRCULATE = 'circulate'
    HOLD = 'hold'
    SCHEDULE = 'schedule'
    MESSAGE = 'message'

class Interface(PytomationObject):
    def __init__(self):
        self._disabled = False
        super(Interface, self).__init__()

    def read(self, bufferSize):
        raise NotImplemented

    def write(self, data):
        raise NotImplemented

    @property
    def disabled(self):
        return self._disabled

#class AsynchronousInterface(threading.Thread, Interface):
class AsynchronousInterface(Interface):
    def __init__(self, *args, **kwargs):
        #threading.Thread.__init__(self)
        #print 'AAAA' + str(args) + " : " + str(kwargs)
        super(AsynchronousInterface,self).__init__()
        
        self._logger.debug('Starting thread: ' + self.name)
#        self._main_thread = threading.Thread(target=self.run, args=(None,))
        self._main_thread = threading.Thread(target=self.run)
#        self.start()
        self._init(*args, **kwargs)
        self._main_thread.start()

    def _init(self, *args, **kwargs):
#        self.setDaemon(True)
        self._main_thread.setDaemon(True)

    def command(self,deviceId,command):
        raise NotImplementedError

    def onCommand(self,callback):
        raise NotImplementedError

    def run(self, *args, **kwargs):
        pass
    
class TCP(Interface):
    def __init__(self, host, port):
        super(TCP, self).__init__()
        self.__s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print "connect %s:%s" % (host, port)
        self.__s.connect((host, port))

    def write(self,data):
        "Send raw binary"
        self.__s.send(data) 
        return None

    def read(self, bufferSize=4096):
        "Read raw data"
        data = ''
        try:
            data = self.__s.recv(bufferSize, socket.MSG_DONTWAIT)
        except socket.error, ex:
            pass
        except Exception, ex:
            print "Exception:", type(ex) 
            pass
#            print traceback.format_exc()
        return data

    def shutdown(self):
        self.__s.shutdown(socket.SHUT_RDWR)
        self.__s.close()


class TCP_old(Interface):
    def __init__(self, host, port):
        super(TCP_old, self).__init__()
        self.__s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print"connect %s:%s" % (host, port)
        self.__s.connect((host, port))
        self.start()

    def send(self, dataString):
        "Send raw HEX encoded String"
        print "Data Sent=>" + dataString
        data = binascii.unhexlify(dataString)
        self.__s.send(data)
        return None

    def run(self):
        self._handle_receive()

    def _handle_receive(self):
        while 1:
            data = self.__s.recv(1024)
            self.c(data)
        self.__s.close()


class UDP(AsynchronousInterface):
    def __init__(self, fromHost, fromPort, toHost, toPort):
        super(UDP, self).__init__(fromHost,fromPort)
        self.__ssend = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__ssend.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
#        self.__srecv = socket(socket.AF_INET, socket.SOCK_DGRAM)
#        self.__srecv.bind((fromHost,fromPort))
        self.__ssend.bind((fromHost, fromPort))
        self.__fromHost = fromHost
        self.__fromPort = fromPort
        self.__toHost = toHost
        self.__toPort = toPort
        self.start()

    def send(self, dataString):
        self.__ssend.sendto(dataString,(self.__toHost, self.__toPort))
        return None

    def _handle_receive(self):
        while 1:
#            data = self.__srecv.recv(2048)
            data = self.__ssend.recv(2048)
            print "received stuff", data
            if self.c != None:
                self.c(data)

    def run(self):
        self._handle_receive()


class Serial(Interface):
    def __init__(self, serialDevicePath, serialSpeed=19200, serialTimeout=0.1, xonxoff=True, rtscts=False, dsrdtr=True):
        super(Serial, self).__init__()
        print "Using %s for serial communication" % serialDevicePath
#       self.__serialDevice = serial.Serial(serialDevicePath, 19200, timeout = 0.1) 
        try:
            self.__serialDevice = serial.Serial(serialDevicePath, serialSpeed, timeout = serialTimeout)
        except serial.serialutil.SerialException, ex:
            self._disabled = True
            self.__serialDevice = None
            self._logger.critical("{name} Could not open serial port.  Interface disabled".format(
                                                                                    name=self.name
                                                                                                  ))
        
    
    def read(self, bufferSize=1024):
        if self.__serialDevice:
            return self.__serialDevice.read(bufferSize)
        return ""

    def write(self, bytesToSend):
        if self.__serialDevice:
            return self.__serialDevice.write(bytesToSend)
        self._logger.critical("{name} Could not write to closed serial port".format(
                                                                    name=self.name
                                                                                    ))
        return True

    def inWaiting(self):
        if self.__serialDevice:
            return self.__serialDevice.inWaiting()
        return True

class USB(Interface):
    def __init__(self, device):
        return None

class HTTP(Interface):
    def __init__(self, protocol='http', host=None, username=None, password=None):
        super(HTTP, self).__init__()

        self._protocol = protocol
        self._host = host        
        self._username = username
        self._password = password
        self._logger.debug("{name} HTTP Port created".format(
                                                                                    name=self.name
                                                                                                  ))

    def request(self, path="", data=None, verb="GET"):
        _path = None
        _data = None
        _verb = None
        # If we are passed in all the params as a tuple in the first argument, decode
        if isinstance(path, tuple):
            try:
                _path = path[0]
                _data = path[1]
                _verb = path[2]
            except:
                pass
        else:
            _path = path
            _data = data
            _verb = verb

        if _verb == None:
            _verb = "GET"
# Expect the consumer to encode to allow for raw data formats      
#         if _data:
#             encdata = urllib.urlencode(_data)
#         else:
#             encdata = None

        url = self._protocol + "://" + self._host + "/" + _path
        r = getattr(requests, _verb.lower())
        
        response = False
        if self._username:
            response = r(url,
              data=_data,
              auth=requests.auth.HTTPBasicAuth(self._username, self._password))
        else:
            response = r(url,
              data=_data,
              )
            
        return response.text
# #         #print url + ":::" + _data
# #         r = urllib2.Request(url=url)
# #         r.add_data(_data)
# #         response = False
# #         try:
# #             response_stream = urllib2.urlopen(r)
# #     #        response_stream = urllib2.urlopen(url, _data)
# #             response = response_stream.read()
# #         except Exception, ex:
# #             self._logger.error('Could not request: ' + str(ex))
# #         #print url + ":" + str(_data) + ":" + str(response)
# #         return response

    def read(self, path="", data=None, verb='GET', *args, **kwargs):
        return self.request(path, data, verb)
        
    def write(self, path="", data=None, verb="POST", *args, **kwargs):
        if isinstance(path, tuple):
            _path = path[0]
            _data = path[1]
            _verb = 'POST'
        else:
            _path = path
            _data = data
            _verb = verb
        return self.request(_path, _data, _verb)

    def inWaiting(self):
        return True
    
    @property
    def host(self):
        return self._host

class HADevice(object):

    def __init__(self, deviceId, interface=None):
        super(HADevice,self).__init__()
        self.interface = interface
        self.deviceId = deviceId

    def set(self, command):
        self.interface.command(self, command)


class InsteonDevice(HADevice):
    def __init__(self, deviceId, interface=None):
        super(InsteonDevice, self).__init__(deviceId, interface)


class X10Device(HADevice):
    def __init__(self, deviceId, interface=None):
        super(X10Device, self).__init__(deviceId, interface)


class HACommand(Lookup):
    ON = 'on'
    OFF = 'off'

    def __init__(self):
        super(HACommand,self).__init__({
                       'on'         :{'primary' : {
                                                    'insteon':0x11,
                                                    'x10':0x02,
                                                    'upb':0x00
                                                  }, 
                                     'secondary' : {
                                                    'insteon':0xff,
                                                    'x10':None,
                                                    'upb':None
                                                    },
                                     },
                       'faston'    :{'primary' : {
                                                    'insteon':0x12,
                                                    'x10':0x02,
                                                    'upb':0x00
                                                  }, 
                                     'secondary' : {
                                                    'insteon':0xff,
                                                    'x10':None,
                                                    'upb':None
                                                    },
                                     },
                       'off'         :{'primary' : {
                                                    'insteon':0x13,
                                                    'x10':0x03,
                                                    'upb':0x00
                                                  }, 
                                     'secondary' : {
                                                    'insteon':0x00,
                                                    'x10':None,
                                                    'upb':None
                                                    },
                                     },

                       'fastoff'    :{'primary' : {
                                                    'insteon':0x14,
                                                    'x10':0x03,
                                                    'upb':0x00
                                                  }, 
                                     'secondary' : {
                                                    'insteon':0x00,
                                                    'x10':None,
                                                    'upb':None
                                                    },
                                     },
                       'level'    :{'primary' : {
                                                    'insteon':0x11,
                                                    'x10':0x0a,
                                                    'upb':0x00
                                                  }, 
                                     'secondary' : {
                                                    'insteon':0x88,
                                                    'x10':None,
                                                    'upb':None
                                                    },
                                     },
                       }
                      )
        pass


import time
import re


## {{{ http://code.activestate.com/recipes/142812/ (r1)
FILTER=''.join([(len(repr(chr(x)))==3) and chr(x) or '.' for x in range(256)])

def hex_dump(src, length=8):
    N=0; result=''
    try:
        while src:
            s,src = src[:length],src[length:]
            hexa = ' '.join(["%02X"%ord(x) for x in s])
            s = s.translate(FILTER)
            result += "%04X   %-*s   %s\n" % (N, length*3, hexa, s)
            N+=length
    except Exception, ex:
        print 'Exception in Hexdump: ' + str(ex)
        result = src
    return result

## end of http://code.activestate.com/recipes/142812/ }}}

def interruptibleSleep(sleepTime, interuptEvent):
    sleepInterval = 0.05

    #adjust for the time it takes to do our instructions and such
    totalSleepTime = sleepTime - 0.04

    while interuptEvent.isSet() == False and totalSleepTime > 0:
        time.sleep(sleepInterval)
        totalSleepTime = totalSleepTime - sleepInterval


def sort_nicely( l ):
    """ Sort the given list in the way that humans expect. 
    """ 
    convert = lambda text: int(text) if text.isdigit() else text 
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    l.sort( key=alphanum_key )

    return l

def convertStringFrequencyToSeconds(textFrequency):
    frequencyNumberPart = int(textFrequency[:-1])
    frequencyStringPart = textFrequency[-1:].lower()

    if (frequencyStringPart == "w"):
        frequencyNumberPart *= 604800
    elif (frequencyStringPart == "d"):
        frequencyNumberPart *= 86400
    elif (frequencyStringPart == "h"):
        frequencyNumberPart *= 3600
    elif (frequencyStringPart == "m"):
        frequencyNumberPart *= 60

    return frequencyNumberPart


def hashPacket(packetData):
    hash = None
    try:
        hash = hashlib.md5(packetData).hexdigest()
    except:
        hash = hashlib.md5(str(packetData)).hexdigest()
    return hash

# pylog replaces the "print" keyword to enable debugging and logging
def pylog(src, s):
    t = ""
    if logging:
        if logfileTimestamp != "":
            t = time.strftime(logfileTimestamp)
        try:
            if logfilePreserve:
                fp = open(logfile, "a")
            else:
                fp = open(logfile, "w")
        except Exception, ex:
            print "Log:" + t+ s + "\n"
#            print "ERROR Can't open log file..." + str(ex) + "=>"
#            try:
#                fp = open("/tmp/pylog.txt", "a")
#                print "Trying /tmp/pylog.txt"
#            except Exception, ex1:
#                sys.exit(0)
        else:
            fp.write(t + s + "\n")
            fp.close()
    else:
        print t + s


class Conversions(object):
    @staticmethod
    def hex_to_ascii(hex_string):
        return binascii.unhexlify(hex_string)

    @staticmethod
    def ascii_to_hex(hex_string):
        return binascii.hexlify(hex_string)

    @staticmethod
    def hex_to_bytes( hexStr ):
        """
        Convert a string hex byte values into a byte string. The Hex Byte values may
        or may not be space separated.
        """
        # The list comprehension implementation is fractionally slower in this case    
        #
        #    hexStr = ''.join( hexStr.split(" ") )
        #    return ''.join( ["%c" % chr( int ( hexStr[i:i+2],16 ) ) \
        #                                   for i in range(0, len( hexStr ), 2) ] )
     
        bytes = []
    
        hexStr = ''.join( hexStr.split(" ") )
    
        for i in range(0, len(hexStr), 2):
            bytes.append( chr( int (hexStr[i:i+2], 16 ) ) )
    
        return ''.join( bytes )

    @staticmethod
    def int_to_ascii(integer):
#        ascii = str(unichr(integer))
        ascii = chr(integer)
        return ascii
    
    @staticmethod
    def hex_to_int(char):
        return Conversions.ascii_to_int(Conversions.hex_to_bytes(char))
    
    @staticmethod
    def int_to_hex(integer):
        return "%0.2X" % integer

    @staticmethod
    def ascii_to_int(char):
        return ord(char)

    ## http://code.activestate.com/recipes/142812/ }}}
    @staticmethod
    def hex_dump(src, length=8):
        result = ''
        try:
            N=0;
            while src:
                s,src = src[:length],src[length:]
                hexa = ' '.join(["%02X"%ord(x) for x in s])
                s = s.translate(FILTER)
                result += "%04X   %-*s   %s\n" % (N, length*3, hexa, s)
                N+=length
        except Exception, ex:
            pass
        return result

    @staticmethod
    def checksum2(data):
        return reduce(lambda x,y:x+y, map(ord, data)) % 256    

    @staticmethod
    def checksum(data):
        cs = 0
        for byte in data:
            cs = cs + Conversions.ascii_to_int(byte)
        cs = ~cs
        cs = cs + 1
        cs = cs & 255
        return cs
        

########NEW FILE########
__FILENAME__ = harmony_hub
import time

from interruptingcow import timeout

from harmony.client import HarmonyClient
from harmony.auth import login
from .ha_interface import HAInterface
from .common import *


"""
Harmony Interface 

"""

class HarmonyHub(HAInterface):
    def __init__(self, address=None, port=5222, user=None, password=None, *args, **kwargs):
        self._ip = address
        self._port = port
        self._user = user
        self._password = password
        
        self._create_connection()
        
        super(HarmonyHub, self).__init__(None, *args, **kwargs)

    def _create_connection(self):
        try:
            with timeout(15, exception=RuntimeError):
                self._token = login(self._user, self._password)
                self._conn = HarmonyClient(self._token)
                print "he" +str(self._ip) + ":"  + str(self._port)
                self._conn.connect(address=(self._ip, self._port),
                           use_tls=False, use_ssl=False)
                print 'adf'
                self._conn.process(block=False)
        
                while not self._conn.sessionstarted:
                    time.sleep(0.1)

        except RuntimeError:
            self._logger.error("Harmony: Connection error")
            raise RuntimeError
            return False
        return True

    def on(self, *args, **kwargs):
        print str(args, **kwargs)
#        self._conn.start_activity('7174686')
        self._conn.start_activity(args[0])
        
    def off(self, *args, **kwargs):
        self._conn.start_activity(-1)
        
    def get_config(self):
        return self._conn.get_config()
        
########NEW FILE########
__FILENAME__ = ha_interface
'''
File:
        ha_interface.py

Description:


Author(s): 
         Pyjamasam@github <>
         Jason Sharpee <jason@sharpee.com>  http://www.sharpee.com

License:
    This free software is licensed under the terms of the GNU public license, Version 1     

Usage:


Example: 

Notes:


Created on Mar 26, 2011
'''
import hashlib
import threading
import time
import binascii
import sys
from collections import deque

from .common import *
from pytomation.common.pytomation_object import PytomationObject

class HAInterface(AsynchronousInterface, PytomationObject):
    "Base protocol interface"

    MODEM_PREFIX = '\x02'
    
    def __init__(self, interface, *args, **kwargs):
        kwargs.update({'interface': interface})
        self._po_common(*args, **kwargs)
        super(HAInterface, self).__init__(*args, **kwargs)


    def _init(self, *args, **kwargs):
        super(HAInterface, self)._init(*args, **kwargs)
        self._shutdownEvent = threading.Event()
        self._interfaceRunningEvent = threading.Event()

        self._commandLock = threading.Lock()
        self._outboundQueue = deque()
        self._outboundCommandDetails = dict()
        self._retryCount = dict()

        self._pendingCommandDetails = dict()

        self._commandReturnData = dict()

        self._intersend_delay = 0.15  # 150 ms between network sends
        self._lastSendTime = 0

        self._interface = kwargs['interface']
        self._commandDelegates = []
        self._devices = []
        self._lastPacketHash = None

    def shutdown(self):
        if self._interfaceRunningEvent.isSet():
            self._shutdownEvent.set()

            #wait 2 seconds for the interface to shut down
            self._interfaceRunningEvent.wait(2000)

    def run(self, *args, **kwargs):
        self._interfaceRunningEvent.set()

        #for checking for duplicate messages received in a row

        while not self._shutdownEvent.isSet():
            try:
                self._writeInterface()
    
                self._readInterface(self._lastPacketHash)
            except Exception, ex:
                self._logger.error("Problem with interface: " + str(ex))
                
        self._interfaceRunningEvent.clear()

    def onCommand(self, callback=None, address=None, device=None):
        # Register a device for notification of commands
        if not device:
            self._commandDelegates.append({
                                       'address': address,
                                       'callback': callback,
                                       })
        else:
            self._devices.append(device)

    def _onCommand(self, command=None, address=None):
        # Received command from interface and this will delegate to subscribers
        self._logger.debug("Received Command:" + str(address) + ":" + str(command))
        self._logger.debug('Delegates for Command: ' + str(self._commandDelegates))
        
        addressC = address
        try:
            addressC = addressC.lower()
        except:
            pass
        for commandDelegate in self._commandDelegates:
            addressD = commandDelegate['address']
            try:
                addressD = addressC
            except:
                pass
            if commandDelegate['address'] == None or \
                addressD == addressC:
                    commandDelegate['callback'](
                                                command=command,
                                                address=address,
                                                source=self
                                                )
        self._logger.debug('Devices for Command: ' + str(self._devices))
        for device in self._devices:
            if device.addressMatches(address):
                try:
                    device._on_command(
                                       command=command,
                                       address=address,
                                       source=self,
                                       )
                except Exception, ex:
                    device.command(
                                   command=command,
                                   source=self,
                                   address=address)

    def _onState(self, state, address):
        for device in self._devices:
            if device.addressMatches(address):
                try:
                    device.set_state(
                                       state,
                                       address=address,
                                       source=self,
                                       )
                except Exception, ex:
                    self._logger.debug('Could not set state for device: {device}'.format(device=device.name))
                    
                    
    def _sendInterfaceCommand(self, modemCommand,
                          commandDataString=None,
                          extraCommandDetails=None, modemCommandPrefix=None):

        returnValue = False
        try:
            if self._interface.disabled == True:
                return returnValue
        except AttributeError, ex:
            pass

        try:
#            bytesToSend = self.MODEM_PREFIX + binascii.unhexlify(modemCommand)
            if modemCommandPrefix:
                bytesToSend = modemCommandPrefix + modemCommand
            else:
                bytesToSend = modemCommand
            if commandDataString != None:
                bytesToSend += commandDataString
            commandHash = hashPacket(bytesToSend)

            self._commandLock.acquire()
            if commandHash in self._outboundCommandDetails:
                #duplicate command.  Ignore
                pass

            else:
                waitEvent = threading.Event()

                basicCommandDetails = {'bytesToSend': bytesToSend,
                                       'waitEvent': waitEvent,
                                       'modemCommand': modemCommand}

                if extraCommandDetails != None:
                    basicCommandDetails = dict(
                                       basicCommandDetails.items() + \
                                       extraCommandDetails.items())

                self._outboundCommandDetails[commandHash] = basicCommandDetails

                self._outboundQueue.append(commandHash)
                self._retryCount[commandHash] = 0

                self._logger.debug("Queued %s" % commandHash)

                returnValue = {'commandHash': commandHash,
                               'waitEvent': waitEvent}

            self._commandLock.release()

        except Exception, ex:
            print traceback.format_exc()

        finally:

            #ensure that we unlock the thread lock
            #the code below will ensure that we have a valid lock before we call release
            self._commandLock.acquire(False)
            self._commandLock.release()

        return returnValue

    def _writeInterface(self):
        #check to see if there are any outbound messages to deal with
        self._commandLock.acquire()
        if self._outboundQueue and (len(self._outboundQueue) > 0) and \
            (time.time() - self._lastSendTime > self._intersend_delay):
            commandHash = self._outboundQueue.popleft()

            try:
                commandExecutionDetails = self._outboundCommandDetails[commandHash]
            except Exception, ex:
                self._logger.error('Could not find execution details: {command} {error}'.format(
                                                                                                command=commandHash,
                                                                                                error=str(ex))
                                   )
            else:
                bytesToSend = commandExecutionDetails['bytesToSend']
    
    #            self._logger.debug("Transmit>" + str(hex_dump(bytesToSend, len(bytesToSend))))
                try:
                    self._logger.debug("Transmit>" + Conversions.ascii_to_hex(bytesToSend))
                except:
                    self._logger.debug("Transmit>" + str(bytesToSend))
                    
#                result = self._interface.write(bytesToSend)
                result = self._writeInterfaceFinal(bytesToSend)
                self._logger.debug("TransmitResult>" + str(result))
    
                self._pendingCommandDetails[commandHash] = commandExecutionDetails
                del self._outboundCommandDetails[commandHash]
    
                self._lastSendTime = time.time()

        try:
            self._commandLock.release()
        except Exception, te:
            self._logger.debug("Error trying to release unlocked lock %s" % (str(te)))

    def _writeInterfaceFinal(self, data):
        return self._interface.write(data)

    def _readInterface(self, lastPacketHash):
        response = None
        #check to see if there is anything we need to read
        if self._interface:
            try:
                response = self._interface.read()
            except Exception, ex:
                self._logger.debug("Error reading from interface {interface} exception: {ex}".format(
                                                                                     interaface=str(self._interface),
                                                                                     ex=str(ex)
                                                                                     )
                                   )
        try:
            if response and len(response) != 0:
    #            self._logger.debug("[HAInterface-Serial] Response>\n" + hex_dump(response))
                self._logger.debug("Response>" + hex_dump(response) + "<")
                self._onCommand(command=response)
            else:
                #print "Sleeping"
                #X10 is slow.  Need to adjust based on protocol sent.  Or pay attention to NAK and auto adjust
                #time.sleep(0.1)
                time.sleep(0.5)
        except TypeError, ex:
            pass

    def _waitForCommandToFinish(self, commandExecutionDetails, timeout=None):

        if type(commandExecutionDetails) != type(dict()):
            self._logger.error("Unable to wait without a valid commandExecutionDetails parameter")
            return False

        waitEvent = commandExecutionDetails['waitEvent']
        commandHash = commandExecutionDetails['commandHash']

        realTimeout = 2  # default timeout of 2 seconds
        if timeout:
            realTimeout = timeout

        timeoutOccured = False

        if sys.version_info[:2] > (2, 6):
            #python 2.7 and above waits correctly on events
            timeoutOccured = not waitEvent.wait(realTimeout)
        else:
            #< then python 2.7 and we need to do the waiting manually
            while not waitEvent.isSet() and realTimeout > 0:
                time.sleep(0.1)
                realTimeout -= 0.1

            if realTimeout == 0:
                timeoutOccured = True

        if not timeoutOccured:
            if commandHash in self._commandReturnData:
                return self._commandReturnData[commandHash]
            else:
                return True
        else:
            #re-queue the command to try again
            self._commandLock.acquire()

            if self._retryCount[commandHash] >= 5:
                #too many retries.  Bail out
                self._commandLock.release()
                return False

            self._logger.debug("Timed out for %s - Requeueing (already had %d retries)" % \
                (commandHash, self._retryCount[commandHash]))

            requiresRetry = True
            if commandHash in self._pendingCommandDetails:
                self._outboundCommandDetails[commandHash] = \
                    self._pendingCommandDetails[commandHash]

                del self._pendingCommandDetails[commandHash]

                self._outboundQueue.append(commandHash)
                self._retryCount[commandHash] += 1
            else:
                self._logger.debug("Interesting.  timed out for %s, but there are no pending command details" % commandHash)
                #to prevent a huge loop here we bail out
                requiresRetry = False

            try:
                self._logger.debug("Removing Lock " + str( self._commandLock))
                self._commandLock.release()
            except:
                self._logger.error("Could not release Lock! " + str(self._commandLock))
                
            if requiresRetry:
                return self._waitForCommandToFinish(commandExecutionDetails,
                                                    timeout=timeout)
            else:
                return False

    @property
    def name(self):
        return self.name_ex
    
    @name.setter
    def name(self, value):
        self.name_ex = value
        return self.name_ex
    
    def update_status(self):
        for d in self._devices:
            self.status(d.address)
            
    def status(self, address=None):
        return None

########NEW FILE########
__FILENAME__ = honeywell_thermostat
"""
Honeywell Thermostat Pytomation Interface

Author(s):
texnofobix@gmail.com

Idea/original code from:
Brad Goodman http://www.bradgoodman.com/  brad@bradgoodman.com

some code ideas from:
 George Farris <farrisg@gmsys.com>
"""
import urllib2
import urllib
import json
import datetime
import re
import time
import math
import base64
import time
import httplib

from .ha_interface import HAInterface
from .common import *


class HoneywellWebsite(Interface):
    VERSION = '0.0.1'
    def __init__(self, username=None, password=None):
        super(HoneywellWebsite, self).__init__()
        
        self._host = "rs.alarmnet.com"
        self._username = username
        self._password = password
        self._cookie = None
        self._loggedin = False  
        self._logger.debug('Created object for user> '+str(username))   
        try:
            self._login()
        except Exception, ex:
            self._logger.debug('Error logging in> '+str(username))
    
    def _login(self):
        params=urllib.urlencode({"timeOffset":"240",
                                 "UserName":self._username,
                                 "Password":self._password,
                                 "RememberMe":"false"})
    
        headers={"Content-Type":"application/x-www-form-urlencoded",
                "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding":"sdch",
                "Host":"rs.alarmnet.com",
                "DNT":"1",
                "Origin":"https://rs.alarmnet.com/TotalComfort/",
                "User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.95 Safari/537.36"
            }
        conn = httplib.HTTPSConnection("rs.alarmnet.com")
        conn.request("POST", "/TotalConnectComfort/",params,headers)
        r1 = conn.getresponse()
        cookie = r1.getheader("Set-Cookie")
        location = r1.getheader("Location")
        newcookie=cookie
        newcookie=re.sub(";\s*expires=[^;]+","",newcookie)
        newcookie=re.sub(";\s*path=[^,]+,",";",newcookie)
        newcookie=re.sub("HttpOnly\s*[^;],","X;",newcookie)
        newcookie=re.sub(";\s*HttpOnly\s*,",";",newcookie)
        self._cookie=newcookie
    
        if ((location == None) or (r1.status != 302)):
            self._logger.warning('Failed HTTP Code> '+str(r1.status))
            self._loggedin = False
        else:
            self._logger.debug('Login passed. HTTP Code> '+str(r1.status))
            self._loggin = True

    def _query(self,deviceid):
            self._logger.debug('[HoneywellThermostat] Querying Thermostat>')
            t = datetime.datetime.now()
            utc_seconds = (time.mktime(t.timetuple()))
            utc_seconds = int(utc_seconds*1000)
        
            location="/TotalConnectComfort/Device/CheckDataSession/"+deviceid+"?_="+str(utc_seconds)
            headers={
                    "Accept":"*/*",
                    "DNT":"1",
                    "Accept-Encoding":"plain",
                    "Cache-Control":"max-age=0",
                    "Accept-Language":"en-US,en,q=0.8",
                    "Connection":"keep-alive",
                    "Host":"rs.alarmnet.com",
                    "Referer":"https://rs.alarmnet.com/TotalConnectComfort/",
                    "X-Requested-With":"XMLHttpRequest",
                    "User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.95 Safari/537.36",
                    "Cookie":self._cookie
                }
            conn = httplib.HTTPSConnection("rs.alarmnet.com")
            conn.request("GET", location,None,headers)
            r3 = conn.getresponse()
            if (r3.status != 200):
                    self._logger.debug("Bad R3 status ")
		    self._logger.debug(r3.status)
		    self._logger.debug(r3.reason)
            return r3.read()

    def write(self,deviceid=None,request=None,*args,**kwargs):
        t = datetime.datetime.now()
        utc_seconds = (time.mktime(t.timetuple()))
        utc_seconds = int(utc_seconds*1000)
        location="/TotalConnectComfort/Device/SubmitControlScreenChanges"
        headers={
            "Accept":'application/json; q=0.01',
            "DNT":"1",
            "Accept-Encoding":"gzip,deflate,sdch",
            'Content-Type':'application/json; charset=UTF-8',
            "Cache-Control":"max-age=0",
            "Accept-Language":"en-US,en,q=0.8",
            "Connection":"keep-alive",
            "Host":"rs.alarmnet.com",
            "Referer":"https://rs.alarmnet.com/TotalConnectComfort/",
            "X-Requested-With":"XMLHttpRequest",
            "User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.95 Safari/537.36",
            'Referer':"/TotalConnectComfort/Device/CheckDataSession/"+deviceid,
            "Cookie":self._cookie
        }    
        
        request["DeviceID"] = deviceid
        
        self._logger.debug(location)
        self._logger.debug(headers)    
        self._logger.debug(request)
        return True
   
    def read(self,deviceid=None, *args, **kwargs):
        return self._query(deviceid)
        
    @property
    def username(self):
        return self._username

class HoneywellThermostat(HAInterface):
    VERSION = '0.0.2'
        
    def _init(self, *args, **kwargs):
        super(HoneywellThermostat, self)._init(*args, **kwargs)
        self._deviceid = kwargs.get('deviceid', None)
          
        self._cookie = None
        self._iteration = 0
        self._poll_secs = kwargs.get('poll', 360)
        self._retries = kwargs.get('retries', 5)
        
        self._username = self._interface.username      
        
        self._fanMode = None #0-auto 1-on
        
        self._SetpointChangeAllowed = None #  off-false heat-true cool-true auto-true
        self._SystemSwitchPosition = None  #  off-2     heat-1    cool-3    auto-4
        self._SwitchAutoAllowed = None     #  is Auto Heat/Cold allowed
        
        self._last_temp = None
        self._CoolSetpoint = None
        self._HeatSetpoint = None
        self._StatusCool = None            #  off-0 temp-1 perm-2
        self._StatusHeat = None            #  off-0 temp-1 perm-2
        self._TemporaryHoldUntilTime = None   #minutes since midnight. value used when on temp  
        #import datetime; str(timedelta(minutes=1410))
        self._request= {
            "CoolNextPeriod": None,
            "CoolSetpoint": 78,
            "DeviceID": None,
            "FanMode": None,
            "HeatNextPeriod": None,
            "HeatSetpoint": 70,
            "StatusCool": 0,
            "StatusHeat": 0,
            "SystemSwitch": None
        }
        """
        The "CoolNextPeriod" and "HeatNextPeriod" parameters require special
           explanation they represent the time at which you want to resume the
           normal program. They are represented as a "time-of-day". The number
           represents a time period of 15 minutes from midnight, (just as your
           thermostat can only allow you to set temporary holds which end on a
           15-minute boundary). So for example, if you wanted a temporary hold
           which ends at midnight - set the number to zero. If you wanted it to
           end a 12:15am, set it to 1. For 12:30am, set it to 2, etc. Needless to
           say, this allows you to only set temporary holds up to 24-hours. If no
           NextPeriod is specified however, this will effectively set a
           "permanent" hold, which must be subsequently manually candled.
        """

        
    def version(self):
        self._logger.info("Honeywell Thermostat Pytomation driver version " + self.VERSION + '\n')
        
    def _readInterface(self, lastPacketHash):
        # We need to dial back how often we check the thermostat.. Lets not bombard it!

        if not self._iteration < self._poll_secs:
            self._iteration = 0       
            self._logger.debug('DeviceId:' + self._deviceid)
            response = self._interface.read(deviceid=self._deviceid)
            j = json.loads(response)
            fanData=j['latestData']['fanData']
            self._fanMode=fanData['fanMode']
            
            uiData=j['latestData']['uiData']
            current_temp = uiData["DispTemperature"]
            self._SetpointChangeAllowed = uiData["SetpointChangeAllowed"]
            self._SwitchAutoAllowed = uiData["SwitchAutoAllowed"]
            self._SystemSwitchPosition = uiData["SystemSwitchPosition"]
            self._CoolSetpoint = uiData["CoolSetpoint"]
            self._HeatSetpoint = uiData["HeatSetpoint"]
            self._StatusCool = uiData["StatusCool"]
            self._StatusHeat = uiData["StatusHeat"]
            self._TemporaryHoldUntilTime = uiData["TemporaryHoldUntilTime"]
            
            command = None
            if self._SystemSwitchPosition==2:
                self._logger.debug("system off!")
                command = Command.OFF
                
            elif self._SystemSwitchPosition==1:
                self._logger.debug("heat on!")
                command = Command.HEAT
                self._setpoint = self._HeatSetpoint
                
            elif self._SystemSwitchPosition==3:       
                self._logger.debug("cool on!")
                command = Command.COOL
                self._setpoint = self._CoolSetpoint
                
            elif self._SystemSwitchPosition==4:
                command = Command.AUTOMATIC
                if self._last_temp < self._HeatSetpoint:
                    self._logger.debug("auto: heat on!")
                    self._setpoint = self._HeatSetpoint
                elif self._last_temp > self._CoolSetpoint:
                    self._logger.debug("auto: cool on!")
                        
            self._onCommand(command=command,address=self._deviceid)
            
            if self._last_temp != current_temp:
                self._onCommand((Command.LEVEL, current_temp),address=self._deviceid)
            
        else:
            self._iteration+=1
            time.sleep(1) # one sec iteration

    def schedule(self, *args, **kwargs): #this should take us back to the schedule
        cancelHold= {
            "CoolNextPeriod": None,
            "CoolSetpoint": 75,
            "DeviceID": None,
            "FanMode": None,
            "HeatNextPeriod": None,
            "HeatSetpoint": None,
            "StatusCool": 0,
            "StatusHeat": 0,
            "SystemSwitch": None
        }

        return self._interface.write(deviceid=self._deviceid, request=cancelHold)
    
    

########NEW FILE########
__FILENAME__ = http_server
import BaseHTTPServer
import base64

from SimpleHTTPServer import SimpleHTTPRequestHandler
from pytomation.common import config
#import pytomation.common.config 
from pytomation.common.pyto_logging import PytoLogging
from pytomation.common.pytomation_api import PytomationAPI
from .ha_interface import HAInterface

file_path = "/tmp"

class PytoHandlerClass(SimpleHTTPRequestHandler):
    server = None

    def __init__(self,req, client_addr, server):
#        self._request = req
#        self._address = client_addr
        self._logger = PytoLogging(self.__class__.__name__)
        self._api = PytomationAPI()
        self._server = server

        SimpleHTTPRequestHandler.__init__(self, req, client_addr, server)

    def translate_path(self, path):
        global file_path
        path = file_path + path
        return path

    def do_HEAD(self):
        print "send header"
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_AUTHHEAD(self):
        print "send header"
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        auth_credentials = base64.b64encode(config.admin_user + ":" + config.admin_password)
        
        if self.headers.getheader('Authorization') == None:
            self.do_AUTHHEAD()
            self.wfile.write('no auth header received')
            return
        elif self.headers.getheader('Authorization') == 'Basic ' + auth_credentials:
#            self.do_HEAD()
#            self.wfile.write(self.headers.getheader('Authorization'))
#            self.wfile.write('authenticated!')
            pass
        else:
            self.do_AUTHHEAD()
            self.wfile.write(self.headers.getheader('Authorization'))
            self.wfile.write('Not authenticated')
            return
        self.route()

    def do_POST(self):
        self.route()

    def do_PUT(self):
        self.route()
        
    def do_DELETE(self):
        self.route()

    def do_ON(self):
        self.route()
        
    def do_OFF(self):
        self.route()

    def route(self):
        p = self.path.split('/')
        method = self.command
#        print "pd:" + self.path + ":" + str(p[1:])
        if p[1].lower() == "api":
            data = None
            if method.lower() == 'post':
                length = int(self.headers.getheader('content-length'))
                data = self.rfile.read(length)
#                print 'rrrrr' + str(length) + ":" + str(data) + 'fffff' + str(self._server)
                self.rfile.close()
            response = self._api.get_response(method=method, path="/".join(p[2:]), type=None, data=data, source=PytoHandlerClass.server)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-length", len(response))
            self.end_headers()
            self.wfile.write(response)
            self.finish()
        else:
            getattr(SimpleHTTPRequestHandler, "do_" + self.command.upper())(self)

class HTTPServer(HAInterface):
    def __init__(self, address=None, port=None, path=None, *args, **kwargs):
        super(HTTPServer, self).__init__(address, *args, **kwargs)
        self._handler_instances = []
        self.unrestricted = True # To override light object restrictions
    
    def _init(self, *args, **kwargs):
        super(HTTPServer, self)._init(*args, **kwargs)
        global file_path
        self._address = kwargs.get('address', config.http_address)
        self._port = kwargs.get('port', config.http_port)
        self._protocol = "HTTP/1.0"
        self._path = kwargs.get('path', config.http_path)
        file_path = self._path
        
    def run(self):
        server_address = (self._address, self._port)
        
        PytoHandlerClass.protocol_version = self._protocol
        PytoHandlerClass.server = self
        httpd = BaseHTTPServer.HTTPServer(server_address, PytoHandlerClass)
        
        sa = httpd.socket.getsockname()
        print "Serving HTTP files at ", self._path, " on", sa[0], "port", sa[1], "..."
        httpd.serve_forever()
        #BaseHTTPServer.test(HandlerClass, ServerClass, protocol)


########NEW FILE########
__FILENAME__ = hw_thermostat
"""
Homewerks Radio Thermostat CT-30-H-K2 Wireless Thermostat with Wi-Fi Module, Dual Wireless Inputs and Touch Screen
http://www.amazon.com/gp/product/B004YZFU1Q/ref=oh_details_o01_s00_i00?ie=UTF8&psc=1

Protocol Docs:
http://radiothermostat.com/documents/RTCOA%20WiFI%20API%20V1_0R3.pdf

Essentially the Device is a simple REST interface. Kudos to them for making a straightforward and simple API!

Author(s):
Jason Sharpee
jason@sharpee.com

reuse from:
 George Farris <farrisg@gmsys.com>
"""
import json
import re
import time

from .ha_interface import HAInterface
from .common import *

class HW_Thermostat(HAInterface):
    VERSION = '1.0.0'
    
    def _init(self, *args, **kwargs):
        super(HW_Thermostat, self)._init(*args, **kwargs)
        self._last_temp = None
        self._mode = None
        self._hold = None
        self._fan = None
        self._set_point = None
        
        self._iteration = 0
        self._poll_secs = kwargs.get('poll', 60)

        try:
            self._host = self._interface.host
        except Exception, ex:
            self._logger.debug('[HW Thermostat] Could not find host address: ' + str(ex))
        
    def _readInterface(self, lastPacketHash):
        # We need to dial back how often we check the thermostat.. Lets not bombard it!
        if not self._iteration < self._poll_secs:
            self._iteration = 0
            #check to see if there is anyting we need to read
            responses = self._interface.read('tstat')
            if len(responses) != 0:
                for response in responses.split():
                    self._logger.debug("[HW Thermostat] Response> " + hex_dump(response))
                    self._process_current_temp(response)
                    status = []
                    try:
                        status = json.loads(response)
                    except Exception, ex:
                        self._logger.error('Could not decode status request' + str(ex))
                    self._process_mode(status)
        else:
            self._iteration+=1
            time.sleep(1) # one sec iteration
    
    def heat(self, *args, **kwargs):
        self._mode = Command.HEAT
        return self._send_state()

    def cool(self, *args, **kwargs):
        self._mode = Command.COOL
        return self._send_state()

    def schedule(self, *args, **kwargs):
        self._mode = Command.SCHEDULE
        self._hold = False
        return self._send_state()

    def hold(self, *args, **kwargs):
        self._hold = True
        return self._send_state()

    def circulate(self, *args, **kwargs):
        self._fan = True
        return self._send_state()

    def still(self, *args, **kwargs):
        self._fan = False
        return self._send_state()
    
    def off(self, *args, **kwargs):
        self._mode = Command.OFF
        return self._send_state()
    
    def level(self, address, level, timeout=2.0):
        self._set_point = level
        return self._send_state()
    
    def version(self):
        self._logger.info("HW Thermostat Pytomation driver version " + self.VERSION + '\n')
        
    def _process_current_temp(self, response):
        temp = None
        try:
            status = json.loads(response)
            temp = status['temp']
        except Exception, ex:
            self._logger.error('HW Thermostat couldnt decode status json: ' + str(ex))
        if temp and temp != self._last_temp:
            self._onCommand(command=(Command.LEVEL, temp),address=self._host)

    def _process_mode(self, response):
        self._logger.debug("HW - process mode" + str(response))
        mode = response['tmode']
        command = None
        if mode == 0:
            command = Command.OFF
        elif mode == 1:
            command = Command.HEAT
        elif mode == 2:
            command = Command.COOL
        elif mode == 3:
            command = Command.SCHEDULE
        self._logger.debug('HW Status mode = ' + str(command))
        if command != self._mode:
            self._mode = command
            self._onCommand(command=command,address=self._host)
            
        

    def _send_state(self):
        modes = dict(zip([Command.OFF, Command.HEAT, Command.COOL, Command.SCHEDULE],
                         range(0,4)))
        try:
            attributes = {}
            if self._set_point <> None:
                if self._mode == Command.HEAT or self._mode == None:
                    attributes['t_heat'] = self._set_point
                elif self._mode == Command.COOL:
                    attributes['t_cool'] = self._set_point
            if self._fan <> None:
                attributes['fmode'] = 2 if self._fan else 1
            if self._mode <> None:
                attributes['tmode'] = modes[self._mode]
            if self._hold <> None:
                attributes['hold'] = 1 if self._hold or self._mode != Command.SCHEDULE else 0
                
            command = ('tstat', json.dumps(attributes),
                    )
        except Exception, ex:
            self._logger.error('Could not formulate command to send: ' + str(ex))

        commandExecutionDetails = self._sendInterfaceCommand(command)
        return True
        #return self._waitForCommandToFinish(commandExecutionDetails, timeout=2.0)
        
########NEW FILE########
__FILENAME__ = insteon
'''
File:
        insteon.py

Description:
        InsteonPLM Home Automation Protocol library for Python (Smarthome 2412N, 2412S, 2412U)
        
        For more information regarding the technical details of the PLM:
                http://www.smarthome.com/manuals/2412sdevguide.pdf
                http://www.insteon.com/pdf/insteondetails.pdf (message flags)
                http://www.madreporite.com/insteon/commands.htm

Author(s): 
         Pyjamasam@github <>
         Jason Sharpee <jason@sharpee.com>  http://www.sharpee.com
         George Farris <farrisg@gmsys.com>

        Based loosely on the Insteon_PLM.pm code:
        -       Expanded by Gregg Liming <gregg@limings.net>

License:
    This free software is licensed under the terms of the GNU public license, Version 1     

Usage:
    - Instantiate InsteonPLM by passing in an interface
    - Call its methods
    - ?
    - Profit

Example: (see bottom of the file) 

Notes:
    - Supports both 2412N and 2412S right now

Versions and changes:
    Initial version created on Mar 26 , 2011
    2012/11/14 - 1.1 - Added debug levels and global debug system
    2012/11/19 - 1.2 - Added logging, use pylog instead of print
    2012/11/30 - 1.3 - Unify Command and State magic strings across the system
    2012/12/09 - 1.4 - Been a lot of changes.. Bump
    2012/12/29 - 1.5 - Add support for turning scenes on and off
    2013/01/04 - 1.6 - Retry orphaned commands and deal with Modem Nak's
    2013/01/11 - 1.7 - Add status support from a linked device when manually operated
    
'''
import select
import traceback
import threading
import time
import binascii
import struct
import sys
import string
import hashlib
from collections import deque
from .common import *
from .ha_interface import HAInterface
from pytomation.devices import State

def _byteIdToStringId(idHigh, idMid, idLow):
    return '%02X.%02X.%02X' % (idHigh, idMid, idLow)


def _cleanStringId(stringId):
    return stringId[0:2] + stringId[3:5] + stringId[6:8]


def _stringIdToByteIds(stringId):
    return binascii.unhexlify(_cleanStringId(stringId))


def _buildFlags(stdOrExt=None):
    #todo: impliment this
    if stdOrExt:
        return '\x1f'  # Extended command
    else:
        return '\x0f'  # Standard command


def hashPacket(packetData):
    return hashlib.md5(packetData).hexdigest()


def simpleMap(value, in_min, in_max, out_min, out_max):
    #stolen from the arduino implimentation.  I am sure there is a nice python way to do it, but I have yet to stublem across it
    return (float(value) - float(in_min)) * (float(out_max) - float(out_min)) / (float(in_max) - float(in_min)) + float(out_min);


'''
KEYPADLINC Information

D1   Button or Group number
D2   Controls sending data to device 
D3   Button's LED follow mask  - 0x00 - 0xFF
D4   Button's LED-off mask  - 0x00 - 0xFF
D5   X10 House code, we don't support
D6   X10 Unit code, we don't support
D7   Button's Ramp rate - 0x00 - 0x1F
D8   Button's ON Level  - 0x00 - 0xFF
D9   Global LED Brightness - 0x11 - 0x7F
D10  Non-toggle Bitmap If bit = 0, associated button is Toggle, If bit = 1, button is Non-toggle - 0x00 - 0xFF
D11  Button-LED State Bitmap If bit = 0, associated button's LED is Off, If bit = 1 button's LED is On - 0x00-0xFF
D12  X10 all bitmap
D13  Button Non-Toggle On/Off bitmap, 0 if non-toggle sends Off, 1 if non-toggle sends On
D14  Button Trigger-ALL-Link Bitmap If bit = 0, associated button sends normal Command If bit = 0, button sends ED 0x30 Trigger ALL-Link Command to first device in ALDB

D2 = 01  Is response to a get data request
     02  Set LED follow mask, D3 0x00-0xFF, D4-D14 unused set to 0x00
     03  Set LED off mask, D3 0x00-0xFF, D4-D14 unused set to 0x00
     04  Set X10 address for button - unsupported
     05  Set Ramp rate for button, D3 0x00-0x1F, D4-D14 unused set to 0x00
     06  Set ON Level for button, D3 0x00-0x1F, D4-D14 unused set to 0x00
     07  Set Global LED brightness, D3 0x11-0x7F, D4-D14 unused set to 0x00
     08  Set Non-Toggle state for button, D3 0x00-0x01, D4-D14 unused set to 0x00
     09  Set LED state for button, D3 0x00-0x01, D4-D14 unused set to 0x00
     0A  Set X10 all on - unsupported
     0B  Set Non-Toggle ON/OFF state for button, D3 0x00-0x01, D4-D14 unused set to 0x00
     0C  Set Trigger-ALL-Link State for button, D3 0x00-0x01, D4-D14 unused set to 0x00
     0D-FF Unused

00 01 20 00 00 20 00 00 3F 00 03 00 00 00  Main button ON
 1     3     5     7     9    11    13     A1 button ON

00 01 20 00 00 20 00 00 3F 00 C0 00 00 00  Main button OFF
00 01 20 00 00 20 00 00 3F 00 C4 00 00 00  A ON
00 01 20 00 00 20 00 00 3F 00 C8 00 00 00  B ON
00 01 20 00 00 20 00 00 3F 00 CC 00 00 00  A and B ON
00 01 20 00 00 20 00 00 3F 00 D0 00 00 00  C ON
00 01 20 00 00 20 00 00 3F 00 D4 00 00 00  A and C ON
00 01 20 00 00 20 00 00 3F 00 DC 00 00 00  A, B and C ON
'''

#class KeypadLinc():


class InsteonPLM(HAInterface):
    VERSION = '1.7'
    
    #(address:engineVersion) engineVersion 0x00=i1, 0x01=i2, 0x02=i2cs
    deviceList = {}         # Dynamically built list of devices [address,devcat,subcat,firmware,engine,name]
                            # we store and load this from disk and only run when network changes
    currentCommand = ""
    cmdQueueList = []   	# List of orphaned commands that need to be dealt with
    spinTime = 0.1   		# _readInterface loop time
    extendedCommand = False	# if extended command ack expected from PLM
    statusRequest = False   # Set to True when we do a status request
    lastUnit = ""		# last seen X10 unit code

    
    plmAddress = ""
    
    def __init__(self, interface, *args, **kwargs):
        super(InsteonPLM, self).__init__(interface, *args, **kwargs)
        
    def _init(self, *args, **kwargs):
        super(InsteonPLM, self)._init(*args, **kwargs)
        self.version()
        # Response sizes do not include the start of message (0x02) and the command
        self._modemCommands = {'60': {  # Get IM Info
                                    'responseSize': 7,
                                    'callBack':self._process_PLMInfo
                                  },
                                '61': { # Send All Link Command
                                    'responseSize': 4,
                                    'callBack':self._process_StandardInsteonMessagePLMEcho
                                  },
                                '62': { # Send Standard or Extended Message
                                    'responseSize': 7,
                                    'callBack':self._process_StandardInsteonMessagePLMEcho
                                  },
                                '63': { # Send X10
                                    'responseSize': 3,
                                    'callBack':self._process_StandardX10MessagePLMEcho
                                  },
                                '64': { # Start All Linking
                                    'responseSize': 3,
                                    'callBack':self._process_StandardInsteonMessagePLMEcho
                                  },
                                '65': { # Cancel All Linking
                                    'responseSize': 1,
                                    'callBack':self._process_StandardInsteonMessagePLMEcho
                                  },
                                '69': { # Get First All Link Record
                                    'responseSize': 1,
                                    'callBack':self._process_StandardInsteonMessagePLMEcho
                                  },
                                '6A': { # Get Next All Link Record
                                    'responseSize': 1,
                                    'callBack':self._process_StandardInsteonMessagePLMEcho
                                  },
                                '50': { # Received Standard Message
                                    'responseSize': 9,
                                    'callBack':self._process_InboundStandardInsteonMessage
                                  },
                                '51': { # Received Extended Message
                                    'responseSize': 23,
                                    'callBack':self._process_InboundExtendedInsteonMessage
                                  },
                                '52': { # Received X10
                                    'responseSize':3,
                                    'callBack':self._process_InboundX10Message
                                 },
                                '56': { # All Link Record Response
                                    'responseSize':4,
                                    'callBack':self._process_InboundAllLinkCleanupFailureReport
                                  },
                                '57': { # All Link Record Response
                                    'responseSize':8,
                                    'callBack':self._process_InboundAllLinkRecordResponse
                                  },
                                '58': { # All Link Record Response
                                    'responseSize':1,
                                    'callBack':self._process_InboundAllLinkCleanupStatusReport
                                  },
                            }
        self._modemExtCommands = {'62': { # Send Standard or Extended Message
                                    'responseSize': 21,
                                    'callBack':self._process_ExtendedInsteonMessagePLMEcho
                                  },
                            }

        self._insteonCommands = {
                                    #Direct Messages/Responses
                                    'SD03': {        #Product Data Request (generally an Ack)
                                        'callBack' : self._handle_StandardDirect_IgnoreAck,
                                        'validResponseCommands' : ['SD03']
                                    },
                                    'SD0D': {        #Get InsteonPLM Engine
                                        'callBack' : self._handle_StandardDirect_EngineResponse,
                                        'validResponseCommands' : ['SD0D']
                                    },
                                    'SD0F': {        #Ping Device
                                        'callBack' : self._handle_StandardDirect_AckCompletesCommand,
                                        'validResponseCommands' : ['SD0F']
                                    },
                                    'SD10': {        #ID Request    (generally an Ack)
                                        'callBack' : self._handle_StandardDirect_IgnoreAck,
                                        'validResponseCommands' : ['SD10', 'SB01']
                                    },
                                    'SD11': {        #Devce On
                                        'callBack' : self._handle_StandardDirect_AckCompletesCommand,
                                        'validResponseCommands' : ['SD11', 'SDFF', 'SD00']
                                    },
                                    'SD12': {        #Devce On Fast
                                        'callBack' : self._handle_StandardDirect_AckCompletesCommand,
                                        'validResponseCommands' : ['SD12']
                                    },
                                    'SD13': {        #Devce Off
                                        'callBack' : self._handle_StandardDirect_AckCompletesCommand,
                                        'validResponseCommands' : ['SD13']
                                    },
                                    'SD14': {        #Devce Off Fast
                                        'callBack' : self._handle_StandardDirect_AckCompletesCommand,
                                        'validResponseCommands' : ['SD14']
                                    },
                                    'SD15': {        #Brighten one step
                                        'callBack' : self._handle_StandardDirect_AckCompletesCommand,
                                        'validResponseCommands' : ['SD15']
                                    },
                                    'SD16': {        #Dim one step
                                        'callBack' : self._handle_StandardDirect_AckCompletesCommand,
                                        'validResponseCommands' : ['SD16']
                                    },
                                    'SD19': {        #Light Status Response
                                        'callBack' : self._handle_StandardDirect_LightStatusResponse,
                                        'validResponseCommands' : ['SD19']
                                    },
                                    'SD2E': {        #Light Status Response
                                        'callBack' : self._handle_StandardDirect_AckCompletesCommand,
                                        'validResponseCommands' : ['SD2E']
                                    },

				    #X10 Commands
                                    'XD03': {        #Light Status Response
                                        'callBack' : self._handle_StandardDirect_AckCompletesCommand,
                                        'validResponseCommands' : ['XD03']
                                    },
                                    
                                    #Broadcast Messages/Responses
                                    'SB01': {
                                                    #Set button pushed
                                        'callBack' : self._handle_StandardBroadcast_SetButtonPressed
                                    },
                                    'SBXX12': {
                                                    #Fast On Command
                                        'callBack' : self._handle_StandardBroadcast_SetButtonPressed,
                                        'validResponseCommands' : ['SB12']
                                    },
                                    'SBXX14': {
                                                    #Fast Off Command
                                        'callBack' : self._handle_StandardBroadcast_SetButtonPressed,
                                        'validResponseCommands' : ['SB14']
                                    },

                                    #Unknown - Seems to be light level report
                                    'SDFF': {
                                             },
                                    'SD00': {
                                             },
                                }

        self._x10HouseCodes = Lookup(zip((
                            'm',
                            'e',
                            'c',
                            'k',
                            'o',
                            'g',
                            'a',
                            'i',
                            'n',
                            'f',
                            'd',
                            'l',
                            'p',
                            'h',
                            'n',
                            'j' ),xrange(0x0, 0xF)))

        self._x10UnitCodes = Lookup(zip((
                             '13',
                             '5',
                             '3',
                             '11',
                             '15',
                             '7',
                             '1',
                             '9',
                             '14',
                             '6',
                             '4',
                             '12',
                             '16',
                             '8',
                             '2',
                             '10'
                             ),xrange(0x0,0xF)))

        self._x10Commands = Lookup(zip((
                             'allUnitsOff',
                             'allLightsOn',
                             'on',
                             'off',
                             'dim',
                             'bright',
                             'allLightsOff',
                             'ext1',
                             'hail',
                             'hailAck',
                             'ext3',
                             'unused1',
                             'ext2',
                             'statusOn',
                             'statusOff',
                             'statusReq'
                             ),xrange(0x0,0xF)))

        self._allLinkDatabase = dict()
        self._intersend_delay = 0.85 #850ms between network sends

    def _sendInterfaceCommand(self, modemCommand, commandDataString = None, extraCommandDetails = None):
        self.currentCommand = [modemCommand, commandDataString, extraCommandDetails]
        command = binascii.unhexlify(modemCommand)
        return super(InsteonPLM, self)._sendInterfaceCommand(command, commandDataString, extraCommandDetails, modemCommandPrefix='\x02')

    def _readInterface(self, lastPacketHash):
        #check to see if there is anyting we need to read
        firstByte = self._interface.read(1)
        try:
            if len(firstByte) == 1:
                #got at least one byte.  Check to see what kind of byte it is (helps us sort out how many bytes we need to read now)
                
                if firstByte[0] == '\x02':
                    #modem command (could be an echo or a response)
                    #read another byte to sort that out
                    secondByte = self._interface.read(1)
    
                    responseSize = -1
                    callBack = None
                    
                    if self.extendedCommand:
                        # set the callback and response size expected for extended commands
                        modemCommand = binascii.hexlify(secondByte).upper()
                        if self._modemExtCommands.has_key(modemCommand):
                            if self._modemExtCommands[modemCommand].has_key('responseSize'):
                                responseSize = self._modemExtCommands[modemCommand]['responseSize']
                            if self._modemExtCommands[modemCommand].has_key('callBack'):
                                callBack = self._modemExtCommands[modemCommand]['callBack']

                    else:
                        # set the callback and response size expected for standard commands
                        modemCommand = binascii.hexlify(secondByte).upper()
                        if self._modemCommands.has_key(modemCommand):
                            if self._modemCommands[modemCommand].has_key('responseSize'):
                                responseSize = self._modemCommands[modemCommand]['responseSize']
                            if self._modemCommands[modemCommand].has_key('callBack'):
                                callBack = self._modemCommands[modemCommand]['callBack']
    
                    if responseSize != -1:
                        remainingBytes = self._interface.read(responseSize)
                        currentPacketHash = hashPacket(firstByte + secondByte + remainingBytes)
                        self._logger.debug("Receive< " + hex_dump(firstByte + secondByte + remainingBytes, len(firstByte + secondByte + remainingBytes)) + currentPacketHash + "\n")
    
                        if lastPacketHash and lastPacketHash == currentPacketHash:
                            #duplicate packet.  Ignore
                            pass
                        else:
                            if callBack:
                                callBack(firstByte + secondByte + remainingBytes)
                            else:
                                self._logger.debug("No callBack defined for for modem command %s" % modemCommand)
    
                        self._lastPacketHash = currentPacketHash
                        self.spinTime = 0.2     #reset spin time, there were no naks, Don't set this lower
                    else:
                        self._logger.debug("No responseSize defined for modem command %s" % modemCommand)
                        
                elif firstByte[0] == '\x15':
                    self.spinTime += 0.2
                    self._logger.debug("first byte %s" % binascii.hexlify(firstByte[0]))
                    self._logger.debug("Received a Modem NAK! Resending command, loop time %f" % (self.spinTime))
                    if self.spinTime < 12.0:
                        self._sendInterfaceCommand(self.currentCommand[0], self.currentCommand[1], self.currentCommand[2])
                    else:
                        self._logger.debug("Too many NAK's! Device not responding...")
                else:
                    self._logger.debug("Unknown first byte %s" % binascii.hexlify(firstByte[0]))
                
                self.extendedCommand = False	# go back to standard commands as default
                
            else:
                self._checkCommandQueue()
                #print "Sleeping"
                #X10 is slow.  Need to adjust based on protocol sent.  Or pay attention to NAK and auto adjust
                #time.sleep(0.1)
                time.sleep(self.spinTime)
        except TypeError, ex:
            pass

    def _sendStandardP2PInsteonCommand(self, destinationDevice, commandId1, commandId2):
        self._logger.debug("Command: %s %s %s" % (destinationDevice, commandId1, commandId2))
        return self._sendInterfaceCommand('62', _stringIdToByteIds(destinationDevice) + _buildFlags() + binascii.unhexlify(commandId1) + binascii.unhexlify(commandId2), extraCommandDetails = { 'destinationDevice': destinationDevice, 'commandId1': 'SD' + commandId1, 'commandId2': commandId2})

    def _sendStandardAllLinkInsteonCommand(self, destinationGroup, commandId1, commandId2):
        self._logger.debug("Command: %s %s %s" % (destinationGroup, commandId1, commandId2))
        return self._sendInterfaceCommand('61', binascii.unhexlify(destinationGroup) + binascii.unhexlify(commandId1) + binascii.unhexlify(commandId2),
                extraCommandDetails = { 'destinationDevice': destinationGroup, 'commandId1': 'SD' + commandId1, 'commandId2': commandId2})

    def _getX10UnitCommand(self,deviceId):
        "Send just an X10 unit code message"
        deviceId = deviceId.lower()
        return "%02x00" % ((self._x10HouseCodes[deviceId[0:1]] << 4) | self._x10UnitCodes[deviceId[1:2]])

    def _getX10CommandCommand(self,deviceId,commandCode):
        "Send just an X10 command code message"
        deviceId = deviceId.lower()
        return "%02x80" % ((self._x10HouseCodes[deviceId[0:1]] << 4) | int(commandCode,16))

    def _sendStandardP2PX10Command(self,destinationDevice,commandId1, commandId2 = None):
        # X10 sends 1 complete message in two commands
        self._logger.debug("Command: %s %s %s" % (destinationDevice, commandId1, commandId2))
        self._logger.debug("C: %s" % self._getX10UnitCommand(destinationDevice))
        self._logger.debug("c1: %s" % self._getX10CommandCommand(destinationDevice, commandId1))
            
        self._sendInterfaceCommand('63', binascii.unhexlify(self._getX10UnitCommand(destinationDevice)))

        return self._sendInterfaceCommand('63', binascii.unhexlify(self._getX10CommandCommand(destinationDevice, commandId1)))

    #low level processing methods
    def _process_PLMInfo(self, responseBytes):
        (modemCommand, InsteonCommand, idHigh, idMid, idLow, deviceCat, deviceSubCat, firmwareVer, acknak) = struct.unpack('BBBBBBBBB', responseBytes)
        
        foundCommandHash = None
        #find our pending command in the list so we can say that we're done (if we are running in syncronous mode - if not well then the caller didn't care)
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
#            if binascii.unhexlify(commandDetails['modemCommand']) == chr(modemCommand):
            if commandDetails['modemCommand'] == '\x60':
                #Looks like this is our command.  Lets deal with it
                #self._commandReturnData[commandHash] = { 'id': _byteIdToStringId(idHigh,idMid,idLow), 'deviceCategory': '%02X' % deviceCat, 'deviceSubCategory': '%02X' % deviceSubCat, 'firmwareVersion': '%02X' % firmwareVer }    
                self.plmAddress = _byteIdToStringId(idHigh,idMid,idLow).upper()
                
                waitEvent = commandDetails['waitEvent']
                waitEvent.set()

                foundCommandHash = commandHash
                break

        if foundCommandHash:
            del self._pendingCommandDetails[foundCommandHash]
        else:
            self._logger.warning("Unable to find pending command details for the following packet:")
            self._logger.warning(hex_dump(responseBytes, len(responseBytes)))

    def _process_StandardInsteonMessagePLMEcho(self, responseBytes):
        #print utilities.hex_dump(responseBytes, len(responseBytes))
        #echoed standard message is always 9 bytes with the 6th byte being the command
        #here we handle a status request as a special case the very next received message from the 
        #PLM will most likely be the status response.
        if ord(responseBytes[1]) == 0x62:
            if len(responseBytes) == 9:  # check for proper length
                if ord(responseBytes[6]) == 0x19 and ord(responseBytes[8]) == 0x06:  # get a light level status
                    self.statusRequest = True

    def _process_StandardX10MessagePLMEcho(self, responseBytes):
        # Just ack / error echo from sending an X10 command
        pass

    def _validResponseMessagesForCommandId(self, commandId):
        self._logger.debug('ValidResponseCheck: ' + hex_dump(commandId))
        if self._insteonCommands.has_key(commandId):
            commandInfo = self._insteonCommands[commandId]
            self._logger.debug('ValidResponseCheck2: ' + str(commandInfo))
            if commandInfo.has_key('validResponseCommands'):
                self._logger.debug('ValidResponseCheck3: ' + str(commandInfo['validResponseCommands']))
                return commandInfo['validResponseCommands']

        return False

    def _process_InboundStandardInsteonMessage(self, responseBytes):

        if len(responseBytes) != 11:
            self._logger.error("responseBytes< " + hex_dump(responseBytes, len(responseBytes)) + "\n")
            self._logger.error("Command incorrect length. Expected 11, Received %s\n" % len(responseBytes))
            return

        (modemCommand, insteonCommand, fromIdHigh, fromIdMid, fromIdLow, toIdHigh, toIdMid, toIdLow, messageFlags, command1, command2) = struct.unpack('BBBBBBBBBBB', responseBytes)
        foundCommandHash = None
        waitEvent = None

        #check to see what kind of message this was (based on message flags)
        isBroadcast = messageFlags & (1 << 7) == (1 << 7)
        isDirect = not isBroadcast
        isAck = messageFlags & (1 << 5) == (1 << 5)
        isNak = isAck and isBroadcast

        insteonCommandCode = "%02X" % command1
        if isBroadcast:
            #standard broadcast
            insteonCommandCode = 'SB' + insteonCommandCode
        else:
            #standard direct
            insteonCommandCode = 'SD' + insteonCommandCode

        if self.statusRequest:
            insteonCommandCode = 'SD19'
            
            #this is a strange special case...
            #lightStatusRequest returns a standard message and overwrites the cmd1 and cmd2 bytes with "data"
            #cmd1 (that we use here to sort out what kind of incoming message we got) contains an 
            #"ALL-Link Database Delta number that increments every time there is a change in the addressee's ALL-Link Database"
            #which makes is super hard to deal with this response (cause cmd1 can likley change)
            #for now my testing has show that its 0 (at least with my dimmer switch - my guess is cause I haven't linked it with anything)
            #so we treat the SD00 message special and pretend its really a SD19 message (and that works fine for now cause we only really
            #care about cmd2 - as it has our light status in it)
#            insteonCommandCode = 'SD19'

        #print insteonCommandCode

        #find our pending command in the list so we can say that we're done (if we are running in syncronous mode - if not well then the caller didn't care)
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
            #since this was a standard insteon message the modem command used to send it was a 0x62 so we check for that
#            if binascii.unhexlify(commandDetails['modemCommand']) == '\x62':
            if commandDetails['modemCommand'] == '\x62':
                originatingCommandId1 = None
                if commandDetails.has_key('commandId1'):
                    originatingCommandId1 = commandDetails['commandId1']

                validResponseMessages = self._validResponseMessagesForCommandId(originatingCommandId1)
                if validResponseMessages and len(validResponseMessages):
                    #Check to see if this received command is one that this pending command is waiting for
                    self._logger.debug('Valid Insteon Command COde: ' + str(insteonCommandCode))
                    if validResponseMessages.count(insteonCommandCode) == 0:
                        #this pending command isn't waiting for a response with this command code...  Move along
                        continue
                else:
                    self._logger.warning("Unable to find a list of valid response messages for command %s" % originatingCommandId1)
                    continue

                #since there could be multiple insteon messages flying out over the wire, check to see if this one is 
                #from the device we sent this command to
                destDeviceId = None
                if commandDetails.has_key('destinationDevice'):
                    destDeviceId = commandDetails['destinationDevice']

                if destDeviceId:
                    if destDeviceId.upper() == _byteIdToStringId(fromIdHigh, fromIdMid, fromIdLow).upper():

                        returnData = {} #{'isBroadcast': isBroadcast, 'isDirect': isDirect, 'isAck': isAck}

                        #try and look up a handler for this command code
                        if self._insteonCommands.has_key(insteonCommandCode):
                            if self._insteonCommands[insteonCommandCode].has_key('callBack'):
                                # Run the callback
                                (requestCycleDone, extraReturnData) = self._insteonCommands[insteonCommandCode]['callBack'](responseBytes)
                                self.statusRequest = False
                                
                                if extraReturnData:
                                    returnData = dict(returnData.items() + extraReturnData.items())

                                if requestCycleDone:
                                    waitEvent = commandDetails['waitEvent']
                            else:
                                self._logger.warning("No callBack for insteon command code %s" % insteonCommandCode)
                                waitEvent = commandDetails['waitEvent']
                        else:
                            self._logger.warning("No insteonCommand lookup defined for insteon command code %s" % insteonCommandCode)

                        if len(returnData):
                            self._commandReturnData[commandHash] = returnData

                        foundCommandHash = commandHash
                        break

        if foundCommandHash == None:
            self._logger.warning("Unhandled packet (couldn't find any pending command to deal with it)")
            self._logger.warning("This could be a status message from a broadcast")
            # very few things cause this certainly a scene on or off will so that's what we assume
            
            self._handle_StandardDirect_LightStatusResponse(responseBytes)

        if waitEvent and foundCommandHash:
            waitEvent.set()
            try:
                del self._pendingCommandDetails[foundCommandHash]
                self._logger.debug("Command %s completed\n" % foundCommandHash)
            except:
                self._logger.error("Command %s couldnt be deleted!\n" % foundCommandHash)

    def _process_InboundExtendedInsteonMessage(self, responseBytes):
        (modemCommand, insteonCommand, fromIdHigh, fromIdMid, fromIdLow, toIdHigh, toIdMid, toIdLow, messageFlags, \
            command1, command2, d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14) = struct.unpack('BBBBBBBBBBBBBBBBBBBBBBBBB', responseBytes)        
        
        print hex_dump(responseBytes)        

        foundCommandHash = None
        waitEvent = None
        
        return
        
        insteonCommandCode = "%02X" % command1
        insteonCommandCode = 'SD' + insteonCommandCode

        #find our pending command in the list so we can say that we're done (if we are running in syncronous mode - if not well then the caller didn't care)
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
            if commandDetails['modemCommand'] == '\x62':
                originatingCommandId1 = None
                if commandDetails.has_key('commandId1'):
                    originatingCommandId1 = commandDetails['commandId1']    #ex: SD03

                validResponseMessages = self._validResponseMessagesForCommandId(originatingCommandId1)
                if validResponseMessages and len(validResponseMessages):
                    #Check to see if this received command is one that this pending command is waiting for
                    if validResponseMessages.count(insteonCommandCode) == 0:
                        #this pending command isn't waiting for a response with this command code...  Move along
                        continue
                else:
                    self._logger.warning("Unable to find a list of valid response messages for command %s" % originatingCommandId1)
                    continue

                #since there could be multiple insteon messages flying out over the wire, check to see if this one is 
                #from the device we sent this command to
                destDeviceId = None
                if commandDetails.has_key('destinationDevice'):
                    destDeviceId = commandDetails['destinationDevice']

                if destDeviceId:
                    if destDeviceId.upper() == _byteIdToStringId(fromIdHigh, fromIdMid, fromIdLow).upper():

                        returnData = {} #{'isBroadcast': isBroadcast, 'isDirect': isDirect, 'isAck': isAck}

                        #try and look up a handler for this command code
                        if self._insteonCommands.has_key(insteonCommandCode):
                            if self._insteonCommands[insteonCommandCode].has_key('callBack'):
                                # Run the callback
                                (requestCycleDone, extraReturnData) = self._insteonCommands[insteonCommandCode]['callBack'](responseBytes)
                                
                                if extraReturnData:
                                    returnData = dict(returnData.items() + extraReturnData.items())

                                if requestCycleDone:
                                    waitEvent = commandDetails['waitEvent']
                            else:
                                self._logger.warning("No callBack for insteon command code %s" % insteonCommandCode)
                                waitEvent = commandDetails['waitEvent']
                        else:
                            self._logger.warning("No insteonCommand lookup defined for insteon command code %s" % insteonCommandCode)

                        if len(returnData):
                            self._commandReturnData[commandHash] = returnData

                        foundCommandHash = commandHash
                        break

        if foundCommandHash == None:
            self._logger.warning("Unhandled packet (couldn't find any pending command to deal with it)")
            self._logger.warning("This could be a status message from a broadcast")

        if waitEvent and foundCommandHash:
            waitEvent.set()
            del self._pendingCommandDetails[foundCommandHash]
            self._logger.debug("Command %s completed\n" % foundCommandHash)
    
 
    
    def _process_InboundX10Message(self, responseBytes):
        "Receive Handler for X10 Data"
        unitCode = None
        commandCode = None
        (byteB, byteC) = struct.unpack('xxBB', responseBytes)        
        self._logger.debug("X10> " + hex_dump(responseBytes, len(responseBytes)))
        houseCode =     (byteB & 0b11110000) >> 4 
        houseCodeDec = self._x10HouseCodes.get_key(houseCode)
	self._logger.debug("X10> HouseCode " + houseCodeDec )
	unitCmd = (byteC & 0b10000000) >> 7
	if unitCmd == 0 :
		unitCode = (byteB & 0b00001111)
		unitCodeDec = self._x10UnitCodes.get_key(unitCode)
		self._logger.debug("X10> UnitCode " + unitCodeDec )
		self.lastUnit = unitCodeDec
	else:
                commandCode = (byteB & 0b00001111)
		commandCodeDec = self._x10Commands.get_key(commandCode)
		self._logger.debug("X10> Command: house: " + houseCodeDec + " unit: " + self.lastUnit + " command: " + commandCodeDec  )
		destDeviceId = houseCodeDec.upper() + self.lastUnit
 	        if self._devices:
			for d in self._devices:
			    if d.address.upper() == destDeviceId:
				# only run the command if the state is different than current
				if (commandCode == 0x03 and d.state != State.OFF):     # Never seen one not go to zero but...
				    self._onCommand(address=destDeviceId, command=State.OFF)
				elif (commandCode == 0x02 and d.state != State.ON):   # some times these don't go to 0xFF
				    self._onCommand(address=destDeviceId, command=State.ON)
		else: # No devices to check state, so send anyway
			if (commandCode == 0x03 ):     # Never seen one not go to zero but...
			    self._onCommand(address=destDeviceId, command=State.OFF)
			elif (commandCode == 0x02):   # some times these don't go to 0xFF
			    self._onCommand(address=destDeviceId, command=State.ON)

    #insteon message handlers
    def _handle_StandardDirect_IgnoreAck(self, messageBytes):
        #just ignore the ack for what ever command triggered us
        #there is most likley more data coming for what ever command we are handling
        return (False, None)

    def _handle_StandardDirect_AckCompletesCommand(self, messageBytes):
        #the ack for our command completes things.  So let the system know so
        return (True, None)

    def _handle_StandardBroadcast_SetButtonPressed(self, messageBytes):
        #02 50 17 C4 4A 01 19 38 8B 01 00
        (idHigh, idMid, idLow, deviceCat, deviceSubCat, deviceRevision) = struct.unpack('xxBBBBBBxxx', messageBytes)
        return (True, {'deviceType': '%02X%02X' % (deviceCat, deviceSubCat), 'deviceRevision':'%02X' % deviceRevision})

    def _handle_StandardDirect_EngineResponse(self, messageBytes):
        #02 50 17 C4 4A 18 BA 62 2B 0D 01
        engineVersionIdentifier = messageBytes[10]
        if engineVersionIdentifier == '\x00':
            return (True, {'engineVersion': 'i1'})
        elif engineVersionIdentifier == '\x01':
            return (True, {'engineVersion': 'i2'})
        elif engineVersionIdentifier == '\x02':
            return (True, {'engineVersion': 'i2cs'})
        else:
            return (True, {'engineVersion': 'FF'})

    def _handle_StandardDirect_LightStatusResponse(self, messageBytes):
        (modemCommand, insteonCommand, fromIdHigh, fromIdMid, fromIdLow, toIdHigh, toIdMid, toIdLow, messageFlags, command1, command2) = struct.unpack('BBBBBBBBBBB', messageBytes)

        destDeviceId = _byteIdToStringId(fromIdHigh, fromIdMid, fromIdLow).upper()
        self._logger.debug('HandleStandDirect')
        isGrpCleanupAck = (messageFlags & 0x60) == 0x60
        isGrpBroadcast = (messageFlags & 0xC0) == 0xC0
        isGrpCleanupDirect = (messageFlags & 0x40) == 0x40
        # If we get an ack from a group command fire off a status request or we'll never know the on level (not off)
        if isGrpCleanupAck | isGrpBroadcast and command1 != 0x13: #| isGrpCleanupDirect: 
            self._logger.debug("Running status request:{0}:{1}:{2}:..........".format(isGrpCleanupAck,
                                                                                     isGrpBroadcast,
                                                                                     isGrpCleanupDirect))
            time.sleep(0.1)
            self.lightStatusRequest(destDeviceId, async=True)
        else:   # direct command
            
            self._logger.debug("Setting status for:{0}:{1}:{2}..........".format(
                                                                                 str(destDeviceId),
                                                                                 str(command1),
                                                                                 str(command2),
                                                                                 ))
            # For now lets just handle on and off until the new state code is ready.
            if self._devices:
                for d in self._devices:
                    if d.address.upper() == destDeviceId:
                        # only run the command if the state is different than current
                        if (command1 == 0x13 or (command2 < 0x02 and not isGrpCleanupDirect )) and d.state != State.OFF:     # Never seen one not go to zero but...
                            self._onCommand(address=destDeviceId, command=State.OFF)
                        elif (command1 == 0x11 or (command2 > 0xFD and not isGrpCleanupDirect)) and d.state != State.ON:   # some times these don't go to 0xFF
                            self._onCommand(address=destDeviceId, command=State.ON)
                        elif d.state != (State.LEVEL, command2):
                            self._onCommand(address=destDeviceId, command=((State.LEVEL, command2)))
            else: # No devices to check state, so send anyway
                if (command1 == 0x13 or (command2 < 0x02 and not isGrpCleanupDirect )):     # Never seen one not go to zero but...
                    self._onCommand(address=destDeviceId, command=State.OFF)
                elif (command1 == 0x11 or (command2 > 0xFD and not isGrpCleanupDirect)):   # some times these don't go to 0xFF
                    self._onCommand(address=destDeviceId, command=State.ON)
                elif d.state != (State.LEVEL, command2):
                    self._onCommand(address=destDeviceId, command=((State.LEVEL, command2)))
                
        self.statusRequest = False            
        return (True,None)
        # Old stuff, don't use this at the moment
        #lightLevelRaw = messageBytes[10]
        #map the lightLevelRaw value to a sane value between 0 and 1
        #normalizedLightLevel = simpleMap(ord(lightLevelRaw), 0, 255, 0, 1)

        #return (True, {'lightStatus': round(normalizedLightLevel, 2) })


   	# _checkCommandQueue is run every iteration of _readInterface. It counts the commands 
    # to find repeating ones.  If a command is repeated too many times it means it never
    # recieved a response so we should delete the original command and delete it from the 
    # queue.  This is a hack and will be dealt with properly in the new driver.
    def _checkCommandQueue(self):
        if self._pendingCommandDetails != {}:
            for (commandHash, commandDetails) in self._pendingCommandDetails.items():
                self.cmdQueueList.append(commandHash)
                
                # If we have an orphaned queue it will show up here, get the details, remove the old command
                # from the queue and re-issue.
                if self.cmdQueueList.count(commandHash) > 50:
                    if commandDetails['modemCommand'] in ['\x60','\x61','\x62']:
                        #print "deleting commandhash ", commandHash
                        #print commandDetails
                        cmd1 = commandDetails['commandId1']  # example SD11
                        cmd2 = commandDetails['commandId2']
                        deviceId = commandDetails['destinationDevice']
                        waitEvent = commandDetails['waitEvent']
                        waitEvent.set()
                        del self._pendingCommandDetails[commandHash]
                        while commandHash in self.cmdQueueList:
                            self.cmdQueueList.remove(commandHash)
                        # Retry the command..Do we really want this?
                        self._sendStandardP2PInsteonCommand(deviceId, cmd1[2:], cmd2)

    def __getattr__(self, name):
        name = name.lower()
        # Support levels of lighting
        if name[0] == 'l' and len(name) == 3:
            level = name[1:3]
            level = int((int(level) / 100.0) * int(0xFF))
            return lambda x, y=None: self.level(x, level, timeout=y ) 



    #---------------------------public methods---------------------------------
    
    def getPLMInfo(self, timeout = None):
        commandExecutionDetails = self._sendInterfaceCommand('60')

        return self._waitForCommandToFinish(commandExecutionDetails, timeout = timeout)

    # This doesn't work and ping in Insteon seems broken as far as I can tell.
    # The ping command 0x0D seems to return an ack from non-existant devices.
    def pingDevice(self, deviceId, timeout = None):
        startTime = time.time()
        commandExecutionDetails = self._sendStandardP2PInsteonCommand(deviceId, '0F', '00')

        #Wait for ping result
        commandReturnCode = self._waitForCommandToFinish(commandExecutionDetails, timeout = timeout)
        endTime = time.time()

        if commandReturnCode:
            return endTime - startTime
        else:
            return False

    def idRequest(self, deviceId, timeout = None):
        if len(deviceId) != 2: #insteon device address
		commandExecutionDetails = self._sendExtendedP2PInsteonCommand(deviceId, '10', '00', '0')
		return self._waitForCommandToFinish(commandExecutionDetails, timeout = timeout)
	return

    def getInsteonEngineVersion(self, deviceId, timeout = None):
        if len(deviceId) != 2: #insteon device address
		commandExecutionDetails = self._sendStandardP2PInsteonCommand(deviceId, '0D', '00')
		return self._waitForCommandToFinish(commandExecutionDetails, timeout = timeout)
	# X10 device,  command not supported,  just return
	return

    def getProductData(self, deviceId, timeout = None):
        if len(deviceId) != 2: #insteon device address
		commandExecutionDetails = self._sendStandardP2PInsteonCommand(deviceId, '03', '00', )
		return self._waitForCommandToFinish(commandExecutionDetails, timeout = timeout)
	# X10 device,  command not supported,  just return
	return

    def lightStatusRequest(self, deviceId, timeout = None, async = False):
        if len(deviceId) != 2: #insteon device address
		commandExecutionDetails = self._sendStandardP2PInsteonCommand(deviceId, '19', '00')
		if not async:
		    return self._waitForCommandToFinish(commandExecutionDetails, timeout = timeout)
		return
	# X10 device,  command not supported,  just return
	return

    def relayStatusRequest(self, deviceId, timeout = None):
        if len(deviceId) != 2: #insteon device address
		commandExecutionDetails = self._sendStandardP2PInsteonCommand(deviceId, '19', '01')
		return self._waitForCommandToFinish(commandExecutionDetails, timeout = timeout)
	# X10 device,  command not supported,  just return
	return

    def command(self, device, command, timeout=None):
        command = command.lower()
        if isinstance(device, InsteonDevice):
            commandExecutionDetails = self._sendStandardP2PInsteonCommand(device.deviceId, "%02x" % (HACommand()[command]['primary']['insteon']), "%02x" % (HACommand()[command]['secondary']['insteon']))
            self._logger.debug("InsteonA" + commandExecutionDetails)
            
        elif isinstance(device, X10Device):
            commandExecutionDetails = self._sendStandardP2PX10Command(device.deviceId,"%02x" % (HACommand()[command]['primary']['x10']))
            self._logger.debug("X10A" + commandExecutionDetails)
        else:
            self._logger.debug("stuffing")
        return self._waitForCommandToFinish(commandExecutionDetails, timeout = timeout)

    def on(self, deviceId, fast=None, timeout = None):
        if fast == 'fast':
            cmd = '12'
        else:
            cmd = '11'
        if len(deviceId) != 2: #insteon device address
            commandExecutionDetails = self._sendStandardP2PInsteonCommand(deviceId, cmd, 'ff')
        else: #X10 device address
            commandExecutionDetails = self._sendStandardP2PX10Command(deviceId,'02')
        return self._waitForCommandToFinish(commandExecutionDetails, timeout = 2.5)

    def off(self, deviceId, fast=None, timeout = None):
        if fast == 'fast':
            cmd = '14'
        else:
            cmd = '13'
        if len(deviceId) != 2: #insteon device address
            commandExecutionDetails = self._sendStandardP2PInsteonCommand(deviceId, cmd, '00')
        else: #X10 device address
            commandExecutionDetails = self._sendStandardP2PX10Command(deviceId,'03')
        return self._waitForCommandToFinish(commandExecutionDetails, timeout = 2.5)
    
      
    # if rate the bits 0-3 is 2 x ramprate +1, bits 4-7 on level + 0x0F
    def level(self, deviceId, level, rate=None, timeout=None):
        if level > 100 or level <0:
            self._logger.error("{name} cannot set light level {level} beyond 1-15".format(
                                                                                    name=self.name,
                                                                                    level=level,
                                                                                     ))
            return
        else:
            if rate == None:
                # make it 0 to 255                                                                                     
                level = int((int(level) / 100.0) * int(0xFF))
                commandExecutionDetails = self._sendStandardP2PInsteonCommand(deviceId, '11', '%02x' % level)
                return self._waitForCommandToFinish(commandExecutionDetails, timeout=timeout)

            else:
                if rate > 15 or rate <1:
                    self._logger.error("{name} cannot set light ramp rate {rate} beyond 1-15".format(
                                                                                    name=self.name,
                                                                                    level=level,
                                                                                     ))
                    return
                else:
                    lev = int(simpleMap(level, 1, 100, 1, 15))                                                                                     
                    levelramp = (int(lev) << 4) + rate
                    commandExecutionDetails = self._sendStandardP2PInsteonCommand(deviceId, '2E', '%02x' % levelramp)
                    return self._waitForCommandToFinish(commandExecutionDetails, timeout=timeout)

    def level_up(self, deviceId, timeout=None):
        if len(deviceId) != 2: #insteon device address
		commandExecutionDetails = self._sendStandardP2PInsteonCommand(deviceId, '15', '00')
		return self._waitForCommandToFinish(commandExecutionDetails, timeout=timeout)
	# X10 device,  command not supported,  just return
	return

    def level_down(self, deviceId, timeout=None):
        if len(deviceId) != 2: #insteon device address
		commandExecutionDetails = self._sendStandardP2PInsteonCommand(deviceId, '16', '00')
		return self._waitForCommandToFinish(commandExecutionDetails, timeout=timeout)
	# X10 device,  command not supported,  just return
	return

    def status(self, deviceId, timeout=None):
        if len(deviceId) != 2: #insteon device address
		return self.lightStatusRequest(deviceId, timeout)
	# X10 device,  command not supported,  just return
	return

    # Activate scene with the address passed
    def active(self, address, timeout=None):
        if len(deviceId) != 2: #insteon device address
		commandExecutionDetails = self._sendStandardAllLinkInsteonCommand(address, '12', 'FF')
		return self._waitForCommandToFinish(commandExecutionDetails, timeout = timeout)
	# X10 device,  command not supported,  just return
	return
        
    def inactive(self, address, timeout=None):
        if len(deviceId) != 2: #insteon device address
		commandExecutionDetails = self._sendStandardAllLinkInsteonCommand(address, '14', '00')
		return self._waitForCommandToFinish(commandExecutionDetails, timeout = timeout)
	# X10 device,  command not supported,  just return
	return

    def update_status(self):
        for d in self._devices:
            if len(d.address) == 8:  # real address not scene
                print "Getting status for ", d.address
                self.lightStatusRequest(d.address)

    def update_scene(self, address, devices):
        # we are passed a scene number to update and a bunch of objects to update
        for device in devices:
            for k, v in device.iteritems():
                print 'This is a device member' + str(k)
        
    def version(self):
        self._logger.info("Insteon Pytomation driver version " + self.VERSION)


#**********************************************************************************************
#
#   Experimental Insteon stuff
#
#-----------------------------------------------------------------------------------------------
    # yeah of course this doesn't work cause Insteon has 5 year olds writing it's software.
    def getAllProductData(self):
        for d in self._devices:
            if len(d.address) == 8:  # real address not scene
                print "Getting product data for ", d.address
                self.RgetProductData(d.address)
                time.sleep(2.0)

    def getAllIdRequest(self):
        for d in self._devices:
            if len(d.address) == 8:  # real address not scene
                print "Getting product data for ", d.address
                self.idRequest(d.address)
                time.sleep(2.0)


        

    def bitstring(self, s):
        return str(s) if s<=1 else self.bitstring(s>>1) + str(s&1)

    def _sendExtendedP2PInsteonCommand(self, destinationDevice, commandId1, commandId2, d1_d14):
        self._logger.debug("Extended Command: %s %s %s %s" % (destinationDevice, commandId1, commandId2, d1_d14))
        self.extendedCommand = True
        return self._sendInterfaceCommand('62', _stringIdToByteIds(destinationDevice) + _buildFlags(self.extendedCommand) + binascii.unhexlify(commandId1) + binascii.unhexlify(commandId2), extraCommandDetails = { 'destinationDevice': destinationDevice, 'commandId1': 'SD' + commandId1, 'commandId2': commandId2})
    
    def _process_InboundAllLinkRecordResponse(self, responseBytes):
        #print hex_dump(responseBytes)
        (modemCommand, insteonCommand, recordFlags, recordGroup, toIdHigh, toIdMid, toIdLow, linkData1, linkData2, linkData3) = struct.unpack('BBBBBBBBBB', responseBytes)
        #keep the prints commented, for example format only
        #print "Device    Group Flags     Data1 Data2 Data3"
        #print "------------------------------------------------"
        print "%02x.%02x.%02x  %02x    %s  %d    %d    %d" % (toIdHigh, toIdMid, toIdLow, recordGroup,self.bitstring(recordFlags),linkData1, linkData2, linkData3)

    def _process_InboundAllLinkCleanupStatusReport(self, responseBytes):
        if responseBytes[2] == '\x06':
            self._logger.debug("All-Link Cleanup completed...")
            foundCommandHash = None
            waitEvent = None
            for (commandHash, commandDetails) in self._pendingCommandDetails.items():
                if commandDetails['modemCommand'] == '\x61':
                    originatingCommandId1 = None
                
                    if commandDetails.has_key('commandId1'):  #example SD11
                        originatingCommandId1 = commandDetails['commandId1']  # = SD11

                    if commandDetails.has_key('commandId2'):  #example FF
                        originatingCommandId2 = commandDetails['commandId2']
                
                    destDeviceId = None
                    if commandDetails.has_key('destinationDevice'):
                        destDeviceId = commandDetails['destinationDevice']
                
                    waitEvent = commandDetails['waitEvent']
                    foundCommandHash = commandHash
                    break

        if foundCommandHash == None:
            self._logger.warning("Unhandled packet (couldn't find any pending command to deal with it)")
            self._logger.warning("This could be an unsolocicited broadcast message")

        if waitEvent and foundCommandHash:
            time.sleep(1.0)  # wait for a bit befor resending the command.
            waitEvent.set()
            del self._pendingCommandDetails[foundCommandHash]
            
        else:
            self._logger.debug("All-Link Cleanup received a NAK...")


    # The group command failed, lets dig out the original command and issue a direct
    # command to the failed device. we will also delete the original command from pendingCommandDetails.
    def _process_InboundAllLinkCleanupFailureReport(self, responseBytes):
        (modemCommand, insteonCommand, deviceGroup, toIdHigh, toIdMid, toIdLow) = struct.unpack('BBBBBB', responseBytes)
        self._logger.debug("All-Link Cleanup Failure, resending command after 1 second...")
        #find our pending command in the list so we can say that we're done (if we are running in syncronous mode - if not well then the caller didn't care)
        foundCommandHash = None
        waitEvent = None
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
            if commandDetails['modemCommand'] == '\x61':
                originatingCommandId1 = None
                
                if commandDetails.has_key('commandId1'):  #example SD11
                    originatingCommandId1 = commandDetails['commandId1']  # = SD11

                if commandDetails.has_key('commandId2'):  #example FF
                    originatingCommandId2 = commandDetails['commandId2']
                
                destDeviceId = _byteIdToStringId(toIdHigh, toIdMid, toIdLow)
                #destDeviceId = None
                #if commandDetails.has_key('destinationDevice'):
                #    destDeviceId = commandDetails['destinationDevice']
                
                waitEvent = commandDetails['waitEvent']
                foundCommandHash = commandHash
                break

        if foundCommandHash == None:
            self._logger.warning("Unhandled packet (couldn't find any pending command to deal with it)")
            self._logger.warning("All Link - This could be an unsolocicited broadcast message")

        if waitEvent and foundCommandHash:
            waitEvent.set()
            del self._pendingCommandDetails[foundCommandHash]
            #self._sendStandardAllLinkInsteonCommand(destDeviceId, originatingCommandId1[2:], originatingCommandId2)
            self._sendStandardP2PInsteonCommand(destDeviceId, originatingCommandId1[2:], originatingCommandId2)
            
        
    
    def print_linked_insteon_devices(self):
        print "Device    Group Flags     Data1 Data2 Data3"
        print "------------------------------------------------"
        self.request_first_all_link_record()
        while self.request_next_all_link_record():
            time.sleep(0.1)
            
    def getkeypad(self):
        destinationDevice='12.BD.CA'
        commandId1='2E'
        commandId2='00'
        d1_d14='0000000000000000000000000000'
        self.extendedCommand = True
        return self._sendInterfaceCommand('62', _stringIdToByteIds(destinationDevice) + '\x1F' + 
                binascii.unhexlify(commandId1) + binascii.unhexlify(commandId2) + binascii.unhexlify(d1_d14), 
                extraCommandDetails = { 'destinationDevice': destinationDevice, 'commandId1': 'SD' + commandId1, 
                'commandId2': commandId2})

        
    def request_first_all_link_record(self, timeout=None):
        commandExecutionDetails = self._sendInterfaceCommand('69')
        #print "Sending Command 0x69..."
        return self._waitForCommandToFinish(commandExecutionDetails, timeout = timeout)


    def request_next_all_link_record(self, timeout=None):
        commandExecutionDetails = self._sendInterfaceCommand('6A')
        #print "Sending Command 0x6A..."
        return self._waitForCommandToFinish(commandExecutionDetails, timeout = timeout)


########NEW FILE########
__FILENAME__ = insteon2
'''
File:
        insteon2.py

Description:
    An Insteon driver for the Pytomation home automation framework.

Author(s): 
         Chris Van Orman

License:
    This free software is licensed under the terms of the GNU public license, Version 1     

Usage:


Example: 

Notes:
    Currently only tested with the 2412S, but should work with similar PLMs.

Created on Mar 11, 2013
'''
from pytomation.interfaces.common import Command
from pytomation.devices import Scene
from pytomation.interfaces.ha_interface import HAInterface
from pytomation.interfaces.insteon_command import InsteonStandardCommand, InsteonExtendedCommand, InsteonAllLinkCommand
from pytomation.interfaces.insteon_message import *
import array
import binascii

# _cleanStringId is for parsing a standard Insteon address such as 1E.2E.3E. It was taken from the original insteon.py.
def _cleanStringId(stringId):
    return stringId[0:2] + stringId[3:5] + stringId[6:8]

# _stringIdToByteIds is for parsing a standard Insteon address such as 1E.2E.3E. It was taken from the original insteon.py.
def _stringIdToByteIds(stringId):
    return binascii.unhexlify(_cleanStringId(stringId))
    
       
class InsteonPLM2(HAInterface):
    
    messages = {
        0x15: lambda : InsteonMessage(0x15, 1),
        0x50: lambda : InsteonStatusMessage(),
        0x51: lambda : InsteonExtendedMessage(),
        0x52: lambda : InsteonMessage(0x52, 4),
        0x53: lambda : InsteonMessage(0x53, 10),
        0x54: lambda : InsteonMessage(0x54, 3),
        0x55: lambda : InsteonMessage(0x55, 2),
        0x56: lambda : InsteonMessage(0x56, 7),
        0x57: lambda : InsteonMessage(0x57, 10),
        0x58: lambda : InsteonMessage(0x58, 3),
        0x59: lambda : InsteonMessage(0x59, 0),
        0x60: lambda : InsteonMessage(0x60, 0),
        0x61: lambda : InsteonMessage(0x61, 6),
        0x62: lambda : InsteonEchoMessage(),
        0x63: lambda : InsteonMessage(0x63, 5),
        0x64: lambda : InsteonMessage(0x64, 5),
        0x65: lambda : InsteonMessage(0x65, 3),
        0x66: lambda : InsteonMessage(0x66, 6),
        0x67: lambda : InsteonMessage(0x67, 3),
        0x68: lambda : InsteonMessage(0x68, 4),
        0x69: lambda : InsteonMessage(0x69, 3),
        0x6a: lambda : InsteonMessage(0x6a, 3),
        0x6b: lambda : InsteonMessage(0x6b, 4),
        0x6c: lambda : InsteonMessage(0x6c, 3),
        0x6d: lambda : InsteonMessage(0x6d, 3),
        0x6e: lambda : InsteonMessage(0x6e, 3),
        0x6f: lambda : InsteonMessage(0x6f, 12),
        0x70: lambda : InsteonMessage(0x70, 4),
        0x71: lambda : InsteonMessage(0x71, 5),
        0x72: lambda : InsteonMessage(0x72, 3),
        0x73: lambda : InsteonMessage(0x73, 6)
    }
    
    commands = {
        Command.ON: lambda : InsteonStandardCommand([0x11, 0xff]),
        Command.LEVEL: lambda : InsteonStandardCommand([0x11,]),
        Command.OFF: lambda : InsteonStandardCommand([0x13, 0x00]),
        Command.STATUS: lambda : InsteonStandardCommand([0x19, 0x00]),
        "ledstatus": lambda : InsteonExtendedCommand([0x2E, 0x00])
    }
    
    sceneCommands = {
        Command.ON: lambda : InsteonAllLinkCommand([0x11, 0x00]),
        Command.OFF: lambda : InsteonAllLinkCommand([0x13, 0x00])
    }
    
    def __init__(self, interface, *args, **kwargs):
        super(InsteonPLM2, self).__init__(interface, *args, **kwargs)

    def _readInterface(self, lastPacketHash):
        # read all data from the underlying interface
        response = array.array('B', self._interface.read())
        if len(response) != 0:
            message = None
            for b in response:
                # If no message found, check for a new one
                # exclude the start of text message 0x02
                if (not message and b != 0x2):
                    message = self.messages[b]()
                    if (b != 0x15):
                        message.appendData(0x2)
                    
                # append the data to the message if it exists                    
                if (message):
                    message.appendData(b)
                
                # if our message is complete, then process it and 
                # start the next one
                if (message and message.isComplete()):
                    self._processMessage(message)
                    message = None

            # if we have a message then the last one was not complete
            if (message):
                self._printByteArray(message.getData(), "Incomplete")

    def _processMessage(self, message):
        self._printByteArray(message.getData())
        response = message.getCommands()
        
        if (response != None):
            command = response['commands']
            self._findPendingCommand(message)
            
            for c in command:
                self._onCommand(command=c['command'], address=c['address'])
    
    def _findPendingCommand(self, message):
        # check if any commands are looking for this message
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
            command = commandDetails['command']
            if (command.isAck(message)):
                self._commandReturnData[commandHash] = True
                waitEvent = commandDetails['waitEvent']
                waitEvent.set()

                del self._pendingCommandDetails[commandHash]
                self._logger.debug("Found pending command details")
                break

    def _printByteArray(self, data, message="Message"):
        s = ' '.join(hex(x) for x in data)
        self._logger.debug(message + ">" + s + " <")	

    def command(self, deviceId, command, timeout=None):
        isScene = False
        level = 100
        
        if isinstance(command, tuple):
            level = command[1]
            command = command[0].lower()
        else:
            command = command.lower()
        
        try:
            device = self._getDevice(deviceId)
        except:
            pass
#        deviceType = 'insteon' if isinstance(device, InsteonDevice) else 'x10'

        if device:
            isScene = isinstance(device, Scene)
            
        commands = self.sceneCommands if isScene else self.commands
            
        try:
            haCommand = commands[command]()
            if command == Command.LEVEL:
                percent_level = int((level / 100 ) * 255)
                haCommand.setSecondaryData([level,])
            # flags = 207 if isScene else 15
        
            haCommand.setAddress(array.array('B', _stringIdToByteIds(deviceId)))
            # haCommand.setFlags(flags)
            commandExecutionDetails = self._sendInterfaceCommand(haCommand.getBytes(),
                extraCommandDetails={'destinationDevice': deviceId, 'command' : haCommand})
            
            return self._waitForCommandToFinish(commandExecutionDetails, timeout=timeout)
        except Exception, ex:
            self._logger.exception('Error executing command: ' + str(ex))
            return None
        
    def on(self, deviceId, fast=None, timeout=None):
        return self.command(deviceId, Command.ON)

    def off(self, deviceId, fast=None, timeout=None):
        return self.command(deviceId, Command.OFF)
    
    def level(self, deviceId, value=100, fast=None, timeout=None):
        return self.command(deviceId, (Command.LEVEL, value))

    def update_status(self):
        for d in self._devices:
            self.command(d, 'status')
                
    def _sendInterfaceCommand(self, modemCommand, commandDataString=None, extraCommandDetails=None):
        return super(InsteonPLM2, self)._sendInterfaceCommand(modemCommand, commandDataString, extraCommandDetails, modemCommandPrefix='\x02')

    def _getDevice(self, address):
        for d in self._devices:
            if (d.address == address): return d
        return None

########NEW FILE########
__FILENAME__ = insteon_command
'''
File:
    insteon_command.py

Description:
    A set of classes supporting Insteon communication

Author(s): 
    Chris Van Orman

License:
    This free software is licensed under the terms of the GNU public license, Version 1     

Usage:

Example: 

Notes:

Created on Mar 11, 2013
'''
class InsteonCommand(object):
    def __init__(self, data, *args, **kwargs):
        self._data = data
        
    def setAddress(self,data):
        pass
        
    def setFlags(self, data):
        pass
    
    def setSecondary(self,data):
        pass 

    def getBytes(self):
        return str(bytearray(self._data))
    
class InsteonStandardCommand(InsteonCommand):
    def __init__(self, data, *args, **kwargs):
        super(InsteonStandardCommand, self).__init__(data, *args, **kwargs)
        self._data = [0x62,0,0,0,0x0F]
        self.setPrimaryData(data)
        self._minAckLength = 10
        self._ackCommand = 0x50

    def _getAddress(self, data):
        return data[1:4]
        
    def setAddress(self,data):
        self._data[1:4] = data
        
    def setFlags(self, data):
        self._data[4] = data
    
    def setPrimaryData(self, data):
        self._data[5:] = data
    
    def setSecondaryData(self,data):
        self._data[6:] = data

    def isAck(self, message):
        data = message.getData()[1:]
        #basically we are just checking that the message is the right length,
        #has the correct address and the command number is correct
        return len(data) >= self._minAckLength and \
            data[0] == self._ackCommand and \
            self._getAddress(data) == self._getAddress(self._data)

class InsteonExtendedCommand(InsteonStandardCommand):
    def __init__(self, data, *args, **kwargs):
        super(InsteonExtendedCommand, self).__init__(data, *args, **kwargs)
        self._data = self._data + [0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        #The extended response is 0x51, but the actual ACK from the device is still 0x50.
        self._ackCommand = 0x50
        self.setFlags(0x1F)
    
class InsteonAllLinkCommand(InsteonStandardCommand):
    def __init__(self, data, *args, **kwargs):
        super(InsteonAllLinkCommand, self).__init__(data, *args, **kwargs)
        self._data = [0x61,0] + data
        self._ackCommand = 0x61
        self._minAckLength = 4

    def _getAddress(self, data):
        return data[1]
        
    def setAddress(self,data):
        self._data[1] = data[2] if len(data) == 3 else data
        
    def setFlags(self, data):
        pass
        
    def setSecondary(self,data):
        self._data[3] = data
        

########NEW FILE########
__FILENAME__ = insteon_message
'''
File:
    insteon_message.py

Description:
    A set of classes for Insteon support.

Author(s): 
    Chris Van Orman

License:
    This free software is licensed under the terms of the GNU public license, Version 1     

Usage:

Example: 

Notes:

Created on Mar 11, 2013
'''
from pytomation.interfaces.common import Command, PytomationObject

def _byteIdToStringId(idHigh, idMid, idLow):
    return '%02X.%02X.%02X' % (idHigh, idMid, idLow)

class InsteonMessage(PytomationObject):
    commands = {
        '0x11': Command.ON,
        '0x13': Command.OFF,
        '0x2e': None
    }

    def __init__(self, code, length):
        super(InsteonMessage, self).__init__()
        self._length = length
        self._data = []

    def appendData(self, value):
        self._data.append(value)

    def getData(self):
        return self._data
                
    def getLength(self):
        return self._length

    def _getCommands(self):
        return []

    def getCommands(self):
        commands = []
        try:
            commands = self._getCommands()
        except Exception as e:
            self._logger.debug("Exception %s" % e)
        
        commands = commands if commands else []
        return { 'data': self._data, 'commands': commands }

    def isComplete(self):
        return self.getLength() == len(self._data)
        
class InsteonEchoMessage(InsteonMessage):
    def __init__(self):
        super(InsteonEchoMessage, self).__init__(0x62, 9)

    def getLength(self):
        isExtended = len(self._data) >= 6 and (self._data[5] & 16 == 16)
        return 23 if isExtended else self._length

class InsteonExtendedMessage(InsteonMessage):
    def __init__(self):
        super(InsteonExtendedMessage, self).__init__(0x51, 25)
        
    def _getCommands(self):
        ledState = self._data[21]
        commands = []
        address = _byteIdToStringId(self._data[2], self._data[3], self._data[4])

        #led status
        for i in range(0,8):
            commands.append({'command': Command.ON if (ledState & (1 << i)) else Command.OFF, 'address': (address + ':%02X' % (i+1))})

        return commands

class InsteonStatusMessage(InsteonMessage):
    def __init__(self):
        super(InsteonStatusMessage, self).__init__(0x50, 11)
        
    def _commandFromLevel(self, level):
        command = Command.ON if level >= 250 else Command.OFF
        command = ((Command.LEVEL, level)) if level > 2 and level < 250 else command
        return command

    def _getCommands(self):
        flags = self._data[8]
        cmd1 = self._data[9]
        cmd2 = self._data[10]

        #Read the flags
        isAck = (flags & 32) == 32
        isGroup = (flags & 64) == 64
        isBroadcast = (flags & 128) == 128
        isDirectAck = isAck and not isGroup and not isBroadcast #ack from direct command (on,off,status,etc)
        isGroupCleanup = isGroup and not isAck and not isBroadcast #manually activated scene
        isGroupBroadcast = not isAck and isGroup and isBroadcast #manually activated scene
        isGroupAck = isAck and isGroup and not isBroadcast #plm activated scene ack of individual device
        
        address = _byteIdToStringId(self._data[2], self._data[3], self._data[4])
        commands = []
        command = None
        #lookup the command if we have it, though this isn't very reliable.
        if (hex(cmd1) in self.commands):
            command = self.commands[hex(self._data[9])]

        if (isDirectAck and cmd1 != 0x2e):
            #Set the on level from cmd2 since cmd1 is not consistent on status messages.
            #We ignore 0x2e here because that is an ACK for extended messages and is always 0.
            command = self._commandFromLevel(cmd2)
        elif (isGroupBroadcast):
            #group 1 means the main load of the switch was turned on.
            if (self._data[7] == 1):
                commands.append({'command': command, 'address': address})

            #This is a scene message, so we should notify the scene.
            address += ':%02X' % self._data[7]
        elif (isGroupCleanup and cmd2 != 0):
            #This is a scene message, so we should notify the scene.
            address += ':%02X' % cmd2
        elif (isGroupAck):
            #This is an All-Link Cleanup.  Notify the scene not the ack'ing device.
            address = '00.00.%02X' % cmd2

        commands.append({'command': command, 'address': address })

        return commands

########NEW FILE########
__FILENAME__ = mh_send
from .ha_interface import HAInterface

class MHSend(HAInterface):
    
#    def _readInterface(self, lastPacketHash):
#        pass
#
#    def _onCommand(self, command=None, address=None):
#        commands = command.split(' ')
#        if commands[0] == 'pl':
#            address = commands[1]
#            command = commands[2][0:len(commands[2])-1]
#        super(Mochad, self)._onCommand(command=command, address=address)
    
    def __getattr__(self, command):
        if command == 'voice':
            return lambda voice_cmd: self._interface.write('run\x0D' + voice_cmd + "\x0D" ) 

########NEW FILE########
__FILENAME__ = mochad
from .common import *
#from pytomation.devices import StateDevice, InterfaceDevice, State
from .ha_interface import HAInterface
from pytomation.devices import State
'''
http://sourceforge.net/apps/mediawiki/mochad/index.php?title=Mochad_Reference

switched pl method for rf as both the cm19a only supports rf while the cm14a supports both pl and rf
'''

class Mochad(HAInterface):
    
    VERSION='0.3.0'
        
    def _init(self, *args, **kwargs):
        self._devicestatus = False
        self._securitystatus = False
        super(Mochad, self)._init(*args, **kwargs)

    def _readInterface(self, lastPacketHash):
        raw_response = self._interface.read()
        
        if len(raw_response) == 0: #if no data leave
            return
        
        response_lines = raw_response.split('\n')
        
        self._logger.debug('Number of Lines '+str(len(response_lines)))
        
        for line in response_lines:
            if line.strip()=='':
                return #leave if empty
            self._logger.debug('line responses> ' + line)
            line_data=line.split(' ')
            if line_data[2]=='Rx' or line_data[2]=='Tx':
                """ Like below
                01/27 23:41:23 Rx RF HouseUnit: A3 Func: Off
                0     1        2  3  4          5  6     7 
                01/27 23:48:23 Rx RF HouseUnit: A1 Func: On
                12/07 20:49:37 Rx RFSEC Addr: C6:1B:00 Func: Motion_alert_MS10A
                0     1        2  3     4     5        6     7
                """
                #date=data[0]
                #time=data[1]
                #direction=data[2]
                #method=data[3]
                #ua=data[4]
                addr=line_data[5]
                func=line_data[7].strip().rsplit('_',1)[0]   #removing _devicemodel
                self._map(func,addr)
                
            """
            command sent > st
            02/01 16:44:23 Device selected
            02/01 16:44:23 House A: 2
            02/01 16:44:23 House B: 1
            02/01 16:44:23 Device status
            02/01 16:44:23 House A: 1=0,2=0,3=0,4=1,5=1,6=1,7=1,8=1,10=0,11=0
            0     1        2     3  4
            02/01 16:44:23 Security sensor status
            02/01 16:44:23 Sensor addr: 000003 Last: 1102:40 Arm_KR10A
            02/01 16:44:23 Sensor addr: 000093 Last: 1066:33 Disarm_SH624
            02/01 16:44:23 Sensor addr: 055780 Last: 1049:59 Contact_alert_max_DS10A
            02/01 16:44:23 Sensor addr: 27B380 Last: 01:42 Motion_normal_MS10A
            02/01 16:44:23 Sensor addr: AF1E00 Last: 238:19 Lights_Off_KR10A
            0     1        2      3     4      5     6      7 
            02/01 16:44:23 End status
            """    
                
            if line_data[2]=='Device':
                if line_data[3]=='status':
                    self._devicestatus = True
                    continue

            if line_data[2]=='Security':
                if line_data[3]=='sensor':
                    self._devicestatus = False
                    self._securitystatus = True
                    continue
                    
            if line_data[2]=='End':
                self._devicestatus = False #shouldn't need to set this false, but why not?
                self._securitystatus = False
                continue
                
            if self._devicestatus:      
                housecode = line_data[3].strip(":")
                    
                for device in line_data[4].split(','):
                    qdevicestatus=device.split('=')
                   
                    if qdevicestatus[1]=='0':
                          self._onCommand(command=Command.OFF,address=str(housecode+qdevicestatus[0]))
                    if qdevicestatus[1]=='1':
                          self._onCommand(command=Command.ON,address=str(housecode+qdevicestatus[0]))
                       
            if self._securitystatus:
                addr=line_data[4]
                func = line_data[7].rsplit('_',1)[0]
                self._logger.debug("Function: "+ func + " Address " + addr[0:2]+":"+addr[2:4]+":"+addr[4:6])
                self._map(func,addr[0:2]+":"+addr[2:4]+":"+addr[4:6]) #adding in COLONs
                       
    def status(self,address):
        self._logger.debug('Querying of last known status all devices including '+address)
        self._interface.write('st'+"\x0D")
        return None 
        
    def update_status(self):
        self._logger.debug('Mochad update status called')
        self.status('')

    def _onCommand(self, command=None, address=None):
        commands = command.split(' ')
        if commands[0] == 'rf':
            address = commands[1]
            command = commands[2][0:len(commands[2])-1]
        self._logger.debug('Command>'+command+' at '+address)
        super(Mochad, self)._onCommand(command=command, address=address)
    
    """ #Causes issues with web interface Disabling this feature.
    def __getattr__(self, command):
        return lambda address: self._interface.write('rf ' + address + ' ' + command + "\x0D" ) 
    """

    def on(self, address):
        self._logger.debug('Command on at '+address)
        self._interface.write('rf ' + address + ' on' + "\x0D")

    def off(self, address):
        self._logger.debug('Command off at '+address)
        self._interface.write('rf ' + address + ' off'+ "\x0D")
        
    def disarm(self, address):
        self._logger.debug('Command disarm at '+address)
        self._interface.write('rfsec ' + address + ' disarm'+ "\x0D")
        
    def arm(self, address):
        self._logger.debug('Command arm at '+address)
        self._interface.write('rfsec ' + address + ' arm'+ "\x0D")

    def version(self):
        self._logger.info("Mochad Pytomation Driver version " + self.VERSION)
        
    def _map(self,func,addr): #mapping output to a valid command
        #print func,addr
        if func=="On":
            self._onCommand(command=Command.ON,address=addr)
        elif func=="Off":
            self._onCommand(command=Command.OFF,address=addr)
        elif func=="Contact_normal_min":
            self._onState(state=State.CLOSED,address=addr)
        elif func=="Contact_alert_min":
            self._onState(state=State.OPEN,address=addr) 
        elif func=="Contact_normal_max":
            self._onState(state=State.CLOSED,address=addr)
        elif func=="Contact_alert_max":
            self._onState(state=State.OPEN,address=addr)
        elif func=="Motion_alert":
            self._onState(state=State.MOTION,address=addr)
        elif func=="Motion_normal":
            self._onState(state=State.STILL,address=addr)
        elif func=="Arm":
            self._onState(state=State.ON,address=addr)
        elif func=="Panic":
            self._onState(state=State.VACATE,address=addr)
        elif func=="Disarm":
            self._onState(state=State.DISARM,address=addr)
        elif func=="Lights_On":
            self._onCommand(command=Command.ON,address=addr)
        elif func=="Lights_Off":
            self._onCommand(command=Command.OFF,address=addr)


########NEW FILE########
__FILENAME__ = named_pipe
import os, tempfile, time

from .common import Interface
from ..common.pytomation_object import PytoLogging

class NamedPipe(Interface):
    def __init__(self, path_name, is_read=True):
        super(NamedPipe, self).__init__()
        self._path_name = path_name
        self._is_read = is_read
        self._logger = PytoLogging(self.__class__.__name__)
        self._create_named_pipe(path_name)

    def _create_named_pipe(self, path_name):
        try:
            os.mkfifo(path_name)
        except OSError, ex:
            self._logger.warning("Failed to create FIFO: %s" % ex)
        except Exception, ex:
            self._logger.critical("Unknown exception: %s" % ex)
            return
        if self._is_read:
# Unintuitive behavior IMO: 
#   http://stackoverflow.com/questions/5782279/python-why-does-a-read-only-open-of-a-named-pipe-block
#            self._pipe = open(path_name, 'r')
            self._pipe = os.open(path_name, os.O_RDONLY|os.O_NONBLOCK)
        else:
#            self._pipe = open(path_name, 'w')
            self._pipe = os.open(path_name, os.O_WRONLY|os.O_NONBLOCK)
            
    def read(self, bufferSize=1024):
        result = ''
        try:
            result = os.read(self._pipe, bufferSize)
        except OSError, ex:
            self._logger.debug('Nothing to read in pipe: %s' % ex)
        except Exception, ex:
            self._logger.error('Error reading pipe %s' % ex)
            raise ex
        return result

    def write(self, bytesToSend):
        return os.write(self._pipe, bytesToSend)

    def close(self):
#        self._pipe.close()
        os.close(self._pipe)
        os.remove(self._path_name)
#        os.rmdir(tmpdir)    

########NEW FILE########
__FILENAME__ = nest_thermostat
"""
Nest Thermostat Pytomation Interface

Author(s):
Jason Sharpee
jason@sharpee.com

Library used from:
Jeffrey C. Ollie
https://github.com/jcollie/pyenest

"""
import json
import re
import time
try:
    from pyjnest import Connection
except Exception, ex:
    pass

from .ha_interface import HAInterface
from .common import *

class NestThermostat(HAInterface):
    VERSION = '1.0.0'
    
    def __init__(self, *args, **kwargs):
        super(NestThermostat, self).__init__(None, *args, **kwargs)
        
    def _init(self, *args, **kwargs):
        super(NestThermostat, self)._init(*args, **kwargs)
        self._last_temp = None
        self._mode = None
        self._hold = None
        self._fan = None
        self._set_point = None
        self._away = None
        
        self._user_name = kwargs.get('username', None)
        self._password = kwargs.get('password', None)
        self._iteration = 0
        self._poll_secs = kwargs.get('poll', 60)
        

        self.interface = Connection(self._user_name, self._password)
        try:
            self.interface.login()
        except Exception, ex:
            self._logger.debug('Could not login: ' + str(ex))
        
        
    def _readInterface(self, lastPacketHash):
        # We need to dial back how often we check the thermostat.. Lets not bombard it!
        if not self._iteration < self._poll_secs:
            self._logger.debug('Retrieving status from thermostat.')
            self._iteration = 0
            #check to see if there is anything we need to read
            try:
                self.interface.update_status()
                for device in self.interface.devices.values():
                    print device
                    c_temp = device.current_temperature
                    temp = int(9.0/5.0 * c_temp + 32)
                    if self._last_temp != temp:
                        self._last_temp = temp
                        self._onCommand((Command.LEVEL, temp), device.device_id)
            except Exception, ex:
                self._logger.error('Could not process data from API: '+ str(ex))

        else:
            self._iteration+=1
            time.sleep(1) # one sec iteration
    
    def circulate(self, address, *args, **kwargs):
        self._fan = True
        try:
            self.interface.devices[address].fan_mode = 'on'
        except Exception, ex:
            self._logger.error('Could not toggle fan' + str(ex))

    def still(self, address, *args, **kwargs):
        self._fan = False
        self.interface.devices[address].fan_mode = 'auto'
    
    def occupy(self, address, *args, **kwargs):
        self._away = False
        for structure in self.interface.structures:
            self.interface.structures[structure].away = False

    def vacate(self, address, *args, **kwargs):
        self._away = True
        for structure in self.interface.structures:
            self.interface.structures[structure].away = True

    def level(self, address, level, timeout=2.0):
        self._set_point = level
        try:
            self.interface.devices[address].change_temperature(level)
        except Exception, ex:
            self._logger.error('Error setting temperature {0} for device= {1},{2}: {3} '.format(
                                                                                        level,
                                                                                        address[0],
                                                                                        address[1],
                                                                                        str(ex)))
        return 
    
    def version(self):
        self._logger.info("HW Thermostat Pytomation driver version " + self.VERSION + '\n')
        

########NEW FILE########
__FILENAME__ = open_zwave
"""
Initial Openzwave support (with Aeon Labs z-stick S2)

by texnofobix@gmail.com

Currently only prints out nodes on network
"""

from .common import *
from .ha_interface import HAInterface

import openzwave
from openzwave.option import ZWaveOption
from openzwave.network import ZWaveNetwork
#from openzwave.node import ZWaveNode
# except: 
#     self._logger.error("Openzwave and/or Python-Openzwave")
    
class Open_zwave(HAInterface):
    VERSION='0.0.1'
    awake=False
    ready=False
    nodesdisplayed=False
    
    def __init__(self, *args, **kwargs):
        self._serialDevicePath = kwargs.get('serialDevicePath', None)
        self._options = ZWaveOption(self._serialDevicePath, \
          config_path="/usr/share/python-openzwave/config", \
          user_path=".", cmd_line="")
        self._options.set_log_file("OZW_Log.log")
        self._options.set_append_log_file(False)
        self._options.set_console_output(True)
        #self._options.set_save_log_level(log)
        self._options.set_save_log_level('Info')
        self._options.set_logging(False)
        self._options.lock()
        self._network = ZWaveNetwork(self._options, log=None)       
        super(Open_zwave, self).__init__(self, *args, **kwargs)
        

    def _init(self, *args, **kwargs):   
        super(Open_zwave, self)._init(self, *args, **kwargs)

    def _readInterface(self, lastPacketHash):
        if self._network.state>=self._network.STATE_AWAKED and not self.awake:
            self.awake = True
            self._logger.info("Network Awaked")
        if self._network.state>=self._network.STATE_READY and not self.ready:
            self.ready = True
            self._logger.info("Network Ready")
        if not self.awake:
            time.sleep(1.0)
            self._logger.debug("Not awaked")
            return
        if self.awake and not self.ready:
            time.sleep(1.0)
            self._logger.debug("Not ready")
            return
        if not nodesdisplayed:           
            for node in self._network.nodes:
                print
                print "------------------------------------------------------------"
                print "%s - Name : %s" % (self._network.nodes[node].node_id,self._network.nodes[node].name)
                print "%s - Manufacturer name / id : %s / %s" % (self._network.nodes[node].node_id,self._network.nodes[node].manufacturer_name, self._network.nodes[node].manufacturer_id)
                print "%s - Product name / id / type : %s / %s / %s" % (self._network.nodes[node].node_id,self._network.nodes[node].product_name, self._network.nodes[node].product_id, self._network.nodes[node].product_type)
                print "%s - Version : %s" % (self._network.nodes[node].node_id, self._network.nodes[node].version)
                print "%s - Command classes : %s" % (self._network.nodes[node].node_id,self._network.nodes[node].command_classes_as_string)
                print "%s - Capabilities : %s" % (self._network.nodes[node].node_id,self._network.nodes[node].capabilities)
                print "%s - Neigbors : %s" % (self._network.nodes[node].node_id,self._network.nodes[node].neighbors)
                print "%s - Can sleep : %s" % (self._network.nodes[node].node_id,self._network.nodes[node].can_wake_up())
            nodesdisplayed=True
    
    def version(self):
        self._logger.info("Open_zwave Pytomation Driver version " + self.VERSION)
        self._logger.info("Use openzwave library : %s" % self._network.controller.ozw_library_version)
        self._logger.info("Use python library : %s" % self._network.controller.python_library_version)
        self._logger.info("Use ZWave library : %s" % self._network.controller.library_description)
        
########NEW FILE########
__FILENAME__ = rpi_input
import RPi.GPIO as GPIO

from pytomation.interfaces.common import Interface
from pytomation.common.pytomation_object import PytoLogging

class RPIInput(Interface):
    def __init__(self, pin):
        super(RPIInput, self).__init__()
        self._pin = pin
        self._state = "unknown"
        self._logger = PytoLogging(self.__class__.__name__)
        GPIO.setup(pin, GPIO.IN)

    def read(self, bufferSize=1024):
        result = "open"

        input_value = GPIO.input(self._pin)

        if (input_value == 1):
            result = "close"

        # return result only if it is different than the last read.
        if (result != self._state):
            self._state = result
        else:
            result = ""

        return result

    def write(self, bytesToSend):
        return None

    def close(self):
        pass

########NEW FILE########
__FILENAME__ = sparkio
"""
Spark IO devices interface driver
https://www.spark.io/

Protocol Docs:
http://docs.sparkdevices.com/

Essentially the Device is a simple REST interface. Kudos to them for making a straightforward and simple API!

Author(s):
Jason Sharpee
jason@sharpee.com

"""
import json
import re
import time
import urllib

from .ha_interface import HAInterface
from .common import *

class SparkIO(HAInterface):
    VERSION = '1.0.0'
    
    def _init(self, *args, **kwargs):
        super(SparkIO, self)._init(*args, **kwargs)
        self._iteration = 0
        self._poll_secs = kwargs.get('poll', 60)

        try:
            self._host = self._interface.host
        except Exception, ex:
            self._logger.debug('Could not find host address: ' + str(ex))
        
    def _readInterface(self, lastPacketHash):
        # We need to dial back how often we check the thermostat.. Lets not bombard it!
        if not self._iteration < self._poll_secs:
            self._iteration = 0
            #check to see if there is anyting we need to read
            responses = self._interface.read('v1/:id/events')
            if len(responses) != 0:
                for response in responses.split():
                    self._logger.debug("[Spark Devices] Response> " + hex_dump(response))
                    self._process_current_temp(response)
                    status = []
                    try:
                        status = json.loads(response)
                    except Exception, ex:
                        self._logger.error('Could not decode status request' + str(ex))
                    self._process_mode(status)
        else:
            self._iteration+=1
            time.sleep(1) # one sec iteration
    
    def version(self):
        self._logger.info("SparkIO Devices Pytomation driver version " + self.VERSION + '\n')
    
    def on(self, address=None, timeout=None, *args, **kwargs):
        return self._set_pin(address, Command.ON, timeout=timeout)
    
    def off(self, address=None, timeout=None, *args, **kwargs):
        return self._set_pin(address, Command.ON, timeout=timeout)

    def _set_pin(self, address, command, timeout=2.0):
        pin_state = {
                     Command.ON: 'HIGH',
                     Command.OFF: 'LOW',
                     }
        url = ('v1/devices/' + address[0])
        attributes = {}
        attributes['pin'] = address[1]
        attributes['level'] = pin_state[command]

#        command = (url, json.dumps(attributes))
        command = (url, urllib.urlencode(attributes))
        
        commandExecutionDetails = self._sendInterfaceCommand(command)
        return True

        #return self._waitForCommandToFinish(commandExecutionDetails, timeout=2.0)
                   
        
########NEW FILE########
__FILENAME__ = stargate
"""
File:
        stargate.py

Description:


Author(s):
         Jason Sharpee <jason@sharpee.com>  http://www.sharpee.com

License:
    This free software is licensed under the terms of the GNU public license, Version 1

Usage:

    see /example_use.py

Example:
    see /example_use.py

Notes:
    Protocol
    http://www.jdstechnologies.com/protocol.html

    2400 Baudrate

Versions and changes:
    Initial version created on May 06 , 2011
    2012/11/14 - 1.1 - Added debug levels and global debug system
    2012/11/19 - 1.2 - Added logging, use pylog instead of print
    2012/11/30 - 1.3 - Unify Command and State magic strings across the system
    2012/12/09 - 1.4 - Bump version number
"""
import threading
import time
from Queue import Queue
from binascii import unhexlify

from .common import *
from .ha_interface import HAInterface

class Stargate(HAInterface):
#    MODEM_PREFIX = '\x12'
    MODEM_PREFIX = ''
    VERSION = '1.4'

    def __init__(self, interface, *args, **kwargs):
        super(Stargate, self).__init__(interface, *args, **kwargs)

    def _init(self, *args, **kwargs):
        super(Stargate, self)._init(*args, **kwargs)

        self.version()
        
        self._last_input_map_low = None
        self._last_input_map_high = None

        self._modemRegisters = ""

        self._modemCommands = {

                               }

        self._modemResponse = {
                               }
        self.d_inverted = [False for x in xrange(16)]
        self.echoMode()
	self._logger.error('Startgggg')

    def _readInterface(self, lastPacketHash):
        #check to see if there is anyting we need to read
        responses = self._interface.read()
        if len(responses) != 0:
            for response in responses.split():
                self._logger.debug("Response>" + hex_dump(response))
                if response[:2] == "!!":  # Echo Mode activity -- !!mm/ddttttttjklm[cr]
                    if self._decode_echo_mode_activity(response)['j'] == 'a' or \
                        self._decode_echo_mode_activity(response)['j'] == 'c':
                        self._processDigitalInput(response, lastPacketHash)
        else:
            #print "Sleeping"
            #X10 is slow.  Need to adjust based on protocol sent.  Or pay attention to NAK and auto adjust
            #time.sleep(0.1)
            time.sleep(0.5)

    def _processDigitalInput(self, response, lastPacketHash):
        offset = 0
        first_time = False
        if self._last_input_map_low == None: #First Time
            self._last_input_map_high = 0
            self._last_input_map_low = 0
            first_time = True

        last_input_map = self._last_input_map_low

        if response[-1] == 'f':
            a=1
        range = self._decode_echo_mode_activity(response)['j']
        io_map = Conversions.ascii_to_int( Conversions.hex_to_ascii(
                self._decode_echo_mode_activity(response)['l'] + \
                self._decode_echo_mode_activity(response)['m']
                ))

        if range == 'c': # High side of 16bit registers
            offset = 8
            last_input_map = self._last_input_map_high 
        

        for i in xrange(8):
            i_value = io_map & (2 ** i)
            i_prev_value = last_input_map & (2 ** i)
            if i_value != i_prev_value or first_time:
                if (not bool(i_value == 0) and not self.d_inverted[i]) or (bool(i_value == 0) and self.d_inverted[i]):
                    state = Command.ON
                else:
                    state = Command.OFF
		self._logger.info("Digital Input #{input} to state {state}".format(
				input=str(offset + i + 1),
				state=state))
                self._onCommand(command=state,
                                address='D' + str(offset + i + 1))

        if range == 'c': # High side of 16bit registers
            self._last_input_map_high = io_map
        else:
            self._last_input_map_low = io_map
	
        self._logger.debug("Process digital input {iomap} {offset} {last_inputl} {last_inputh}".format(
                                             iomap=Conversions.int_to_hex(io_map),
                                             offset=offset,
                                             last_inputl=Conversions.int_to_hex(self._last_input_map_low),
                                             last_inputh=Conversions.int_to_hex(self._last_input_map_high),
                                                                             ))


    def _decode_echo_mode_activity(self, activity):
        decoded = {}
        decoded.update({'month': activity[2:4]})
        decoded.update({'day': activity[5:7]})
        decoded.update({'seconds': activity[7:13]})
        decoded.update({'j': activity[13]})
        decoded.update({'k': activity[14]})
        decoded.update({'l': activity[15]})
        decoded.update({'m': activity[16]})
        return decoded

    def _processRegister(self, response, lastPacketHash):
        foundCommandHash = None

        #find our pending command in the list so we can say that we're done (if we are running in syncronous mode - if not well then the caller didn't care)
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
            if commandDetails['modemCommand'] == self._modemCommands['read_register']:
                #Looks like this is our command.  Lets deal with it
                self._commandReturnData[commandHash] = response[4:]

                waitEvent = commandDetails['waitEvent']
                waitEvent.set()

                foundCommandHash = commandHash
                break

        if foundCommandHash:
            del self._pendingCommandDetails[foundCommandHash]
        else:
            self._logger.warning("Unable to find pending command details for the following packet:")
            self._logger.warning(hex_dump(response))


    def echoMode(self, timeout=None):
        command = '##%1d\r'
        commandExecutionDetails = self._sendInterfaceCommand(
                             command)
#        return self._waitForCommandToFinish(commandExecutionDetails, timeout=timeout)

    def dio_invert(self, channel, value=True):
        self.d_inverted[channel-1] = value

    def version(self):
        self._logger.info("Stargate Pytomation driver version " + self.VERSION)

########NEW FILE########
__FILENAME__ = state_interface
from .ha_interface import HAInterface


class StateInterface(HAInterface):
    pass
########NEW FILE########
__FILENAME__ = tomato
"""
Tomato Router Interface

Author(s):
Jason Sharpee
jason@sharpee.com

"""
import json
import re
import time

from .ha_interface import HAInterface
from .common import *

class TomatoInterface(HAInterface):
    VERSION = '1.0.0'
    
    def _init(self, *args, **kwargs):
        self._user = kwargs.get('user', None)
        self._password = kwargs.get('password', None)
        self._http_id = kwargs.get('http_id', None)
        self._iteration = 0;
        self._poll_secs = 60;

        super(TomatoInterface, self)._init(*args, **kwargs)
        
        try:
            self._host = self._interface.host
        except Exception, ex:
            self._logger.debug('Could not find host address: ' + str(ex))

        
    def _readInterface(self, lastPacketHash):
        # We need to dial back how often we check the thermostat.. Lets not bombard it!
        if not self._iteration < self._poll_secs:
            self._iteration = 0
            #check to see if there is anyting we need to read
#             responses = self._interface.read('tstat')
#             if len(responses) != 0:
#                 for response in responses.split():
#                     self._logger.debug("[HW Thermostat] Response> " + hex_dump(response))
#                     self._process_current_temp(response)
#                     status = []
#                     try:
#                         status = json.loads(response)
#                     except Exception, ex:
#                         self._logger.error('Could not decode status request' + str(ex))
#                     self._process_mode(status)
        else:
            self._iteration+=1
            time.sleep(1) # one sec iteration
    
    def restriction(self, *args, **kwargs):
        """
_nextpage:restrict.asp
_service:restrict-restart
rrule1:1|-1|-1|127|192.168.13.119>192.168.13.202|||0|Roku
f_enabled:on
f_desc:Roku
f_sched_allday:on
f_sched_everyday:on
f_sched_begin:0
f_sched_end:0
f_sched_sun:on
f_sched_mon:on
f_sched_tue:on
f_sched_wed:on
f_sched_thu:on
f_sched_fri:on
f_sched_sat:on
f_type:on
f_comp_all:1
f_block_all:on
f_block_http:
_http_id:
"""
        print str(args) + ":" + str(kwargs)
        fdata = {
                "f_desc": args[0],
                "f_enabled": "On" if args[1] else "Off",
                "_http_id": self._http_id,
                }
#        self._sendInterfaceCommand("tomato.cgi", fdata)
        response = self._interface.write(path="tomato.cgi", data=fdata, verb="POST")
        self._logger.debug("Response:" + str(response))       
    
    def _process_current_temp(self, response):
        temp = None
        try:
            status = json.loads(response)
            temp = status['temp']
        except Exception, ex:
            self._logger.error('HW Thermostat couldnt decode status json: ' + str(ex))
        if temp and temp != self._last_temp:
            self._onCommand(command=(Command.LEVEL, temp),address=self._host)

    def _process_mode(self, response):
        command = Command.ON
        self._onCommand(command=command,address=self._host)
        
    def _send_state(self):
        command = Command.ON
        commandExecutionDetails = self._sendInterfaceCommand(command)
        return True
        #return self._waitForCommandToFinish(commandExecutionDetails, timeout=2.0)
        
########NEW FILE########
__FILENAME__ = upb
"""
File:
        upb.py

Description:


Author(s):
         Jason Sharpee <jason@sharpee.com>  http://www.sharpee.com

License:
    This free software is licensed under the terms of the GNU public license, Version 1

Usage:

    see /example_use.py

Example:
    see /example_use.py

Notes:
    To Program devices initially from factory please use PCS UpStart software:
    http://pulseworx.com/Downloads_.htm


    UPB Serial Interface
    http://pulseworx.com/downloads/Interface/PimComm1.6.pdf
    UPB General Protocol
    http://pulseworx.com/downloads/upb/UPBDescriptionv1.4.pdf

Versions and changes:
    Initial version created on May, 2012
    2012/11/14 - 1.1 - Added debug levels and global debug system
    2012/11/19 - 1.2 - Added logging, use pylog instead of print
    2012/11/30 - 1.3 - Unify Command and State magic strings across the system

"""
import threading
import time
from Queue import Queue
from binascii import unhexlify

from .common import *
from .ha_interface import HAInterface

class UPBMessage(object):
    class LinkType(object):
        direct = 0
        link = 1

    class RepeatType(object):
        none = 0
        low = 1
        med = 2
        high = 3

    class AckRequestFlag(object):
        ack = 0b001
        ackid = 0b010
        msg = 0b100

    class XmitCount(object):
        one = 0
        two = 1
        three = 2
        four = 3

    class MessageIDSet(object):
        upb_core = 0
        device = 1
        upb_report = 4
        extended = 7

    class MessageUPBControl(object):
        retransmit = 0x0d

    class MessageDeviceControl(object):
        activate = 0x20
        deactivate = 0x21
        goto = 0x22
        fade_start = 0x23
        report_state = 0x30
        state_response=0x86
        

    link_type = LinkType.direct
    repeat_request = RepeatType.none
    packet_length = 0
    ack_request = AckRequestFlag.ack  # | AckRequestFlag.ackid | AckRequestFlag.msg
    xmit_count = XmitCount.one
    xmit_seq = XmitCount.one
    network = 49
    destination = 0
    source = 30
#    message_id = MessageIDSet.device
#    message_eid = 0
    message_did = 0
    message_data = None
    checksum = None

    def to_hex(self):
        self.packet_length = 7
        if self.message_data:
            self.packet_length = self.packet_length + len(self.message_data)

#        control1 = ((self.link_type & 0b00000011) << 5) | \
#                ((self.repeat_request & 0b00000011) << 3) | \
#                (self.packet_length & 0b00011111)
        control1 = ((self.link_type & 0b00000001) << 7) | \
                ((self.repeat_request & 0b00000011) << 5) | \
                (self.packet_length & 0b00011111)

        control2 = ((self.ack_request & 0b00000111) << 4) | \
                ((self.xmit_count & 0b00000011) << 2) | \
                (self.xmit_seq & 0b00000011)
#        message_command = ((self.message_id & 0b00000111) << 5) | \
#                            (self.message_eid & 0b00011111)
        message_command = self.message_did
        response = Conversions.int_to_hex(control1) + \
                    Conversions.int_to_hex(control2) + \
                    Conversions.int_to_hex(self.network) + \
                    Conversions.int_to_hex(self.destination) + \
                    Conversions.int_to_hex(self.source) + \
                    Conversions.int_to_hex(message_command)
        if self.message_data != None:
            response = response + Conversions.ascii_to_hex(self.message_data)
        response = response + Conversions.int_to_hex(
                                        Conversions.checksum(
                                        Conversions.hex_to_ascii(response)
                                        )
                                     )
        return response

    def decode(self, message):
        control1 = Conversions.hex_to_int(message[2:4])
        control2 = Conversions.hex_to_int(message[4:6])
        self.link_type = (control1 & 0b10000000) >> 7
        self.repeat_request = (control1 & 0b01100000) >> 5
        self.packet_length = (control1 & 0b00011111)
        self.ack_request = (control2 & 0b01110000) >> 4
        self.xmit_count = (control2 & 0b00001100) >> 2
        self.xmit_seq = (control2 & 0b00000011)
        
        self.network = Conversions.hex_to_int(message[6:8])
        self.destination = Conversions.hex_to_int(message[8:10])
        self.source = Conversions.hex_to_int(message[10:12])
        
        message_header = Conversions.hex_to_int(message[12:14])
 #       self.message_id = (message_header & 0b11100000) >> 5
 #       self.message_eid = (message_header & 0b00011111)
        self.message_did = message_header
        self.message_data = message[14:]

class UPB(HAInterface):
#    MODEM_PREFIX = '\x12'
    MODEM_PREFIX = ''
    VERSION = '1.4'

    def __init__(self, interface, *args, **kwargs):
        super(UPB, self).__init__(interface, *args, **kwargs)

    def _init(self, *args, **kwargs):
        super(UPB, self)._init(*args, **kwargs)
        self.version()
        
        self._modemRegisters = ""

        self._modemCommands = {
                               'send_upb': '\x14',
                               'read_register': '\x12',
                               'write_register': 'x17'
                               }

        self._modemResponse = {'PA': 'send_upb',
                               'PK': 'send_upb',
                               'PB': 'send_upb',
                               'PE': 'send_upb',
                               'PN': 'send_upb',
                               'PR': 'read_register',
                               }

    def get_register(self, start=0, end=255, timeout=None):
#        command = Conversions.hex_to_ascii('120080800D')
#        command = Conversions.hex_to_ascii('1200FF010D')
        command = Conversions.int_to_hex(start) + Conversions.int_to_hex(end)
        command = command + Conversions.int_to_hex(
                               Conversions.checksum(
                                    Conversions.hex_to_ascii(command)
                                    )
                               )
        command = command + Conversions.hex_to_ascii('0D')
        commandExecutionDetails = self._sendInterfaceCommand(
                             self._modemCommands['read_register'], command)
        return self._waitForCommandToFinish(commandExecutionDetails,
                                             timeout=timeout)

    def _readInterface(self, lastPacketHash):
        #check to see if there is anyting we need to read
        responses = self._interface.read()
        if len(responses) != 0:
            self._logger.debug("[UPB] Response>\n" + hex_dump(responses) + "\n")
            for response in responses.splitlines():
                responseCode = response[:2]
                if responseCode == 'PA':  # UPB Packet was received by PIM. No ack yet
                    #pass
                    self._processUBP(response, lastPacketHash)
                elif responseCode == 'PU':  # UPB Unsolicited packet received
                    self._processNewUBP(response)
                elif responseCode == 'PK':  # UPB Packet was acknowledged
                    pass
                elif responseCode == 'PN':  # UPB Packet was not acknowledged
                    pass
#                    self._processUBP(response, lastPacketHash)
                elif responseCode == 'PR':  # Register read response
                    self._processRegister(response, lastPacketHash)
        else:
#            self._logger.debug('Sleeping')
            #time.sleep(0.1)
            time.sleep(0.5)

    def _processUBP(self, response, lastPacketHash):
        foundCommandHash = None

        #find our pending command in the list so we can say that we're done (if we are running in syncronous mode - if not well then the caller didn't care)
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
            if commandDetails['modemCommand'] == self._modemCommands['send_upb']:
                #Looks like this is our command.  Lets deal with it
                self._commandReturnData[commandHash] = True

                waitEvent = commandDetails['waitEvent']
                waitEvent.set()

                foundCommandHash = commandHash
                break

        if foundCommandHash:
            try:
                del self._pendingCommandDetails[foundCommandHash]
                self._logger.debug("Command %s completed\n" % foundCommandHash)
            except:
                self._logger.error("Command %s couldnt be deleted!\n" % foundCommandHash)
        else:
            self._logger.debug("Unable to find pending command details for the following packet:\n")
            self._logger.debug(hex_dump(response, len(response)) + "\n")

    def _processRegister(self, response, lastPacketHash):
        foundCommandHash = None

        #find our pending command in the list so we can say that we're done (if we are running in syncronous mode - if not well then the caller didn't care)
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
            if commandDetails['modemCommand'] == self._modemCommands['read_register']:
                #Looks like this is our command.  Lets deal with it
                self._commandReturnData[commandHash] = response[4:]

                waitEvent = commandDetails['waitEvent']
                waitEvent.set()

                foundCommandHash = commandHash
                break

        if foundCommandHash:
            try:
                del self._pendingCommandDetails[foundCommandHash]
                self._logger.debug("Command %s completed\n" % foundCommandHash)
            except:
                self._logger.error("Command %s couldnt be deleted!\n" % foundCommandHash)
        else:
            self._logger.debug("Unable to find pending command details for the following packet:\n")
            self._logger.debug(hex_dump(response, len(response)) + "\n")

    def _processNewUBP(self, response):
        command = 0x00
        self._logger.debug("Incoming message: " + response)
        incoming = UPBMessage()
        try:
            incoming.decode(response)
        except Exception, ex:
            self._logger.error("UPB Error decoding message -Incoming message: " + response +"=="+ str(ex))
        self._logger.debug('UPBN:' + str(incoming.network) + ":" + str(incoming.source) + ":" + str(incoming.destination) + ":" + Conversions.int_to_hex(incoming.message_did))
        address = (incoming.network, incoming.source)
        if incoming.message_did == UPBMessage.MessageDeviceControl.goto \
            or incoming.message_did == UPBMessage.MessageDeviceControl.fade_start \
            or incoming.message_did == UPBMessage.MessageDeviceControl.state_response:
            if Conversions.hex_to_int(incoming.message_data[1:2]) > 0:
                command = Command.ON
            else:
                command = Command.OFF
        elif incoming.message_did == UPBMessage.MessageDeviceControl.activate:
            address = (incoming.network, incoming.destination, 'L')
            command = Command.ON
        elif incoming.message_did == UPBMessage.MessageDeviceControl.deactivate:
            address = (incoming.network, incoming.destination, 'L')
            command = Command.OFF
        elif incoming.message_did == UPBMessage.MessageDeviceControl.report_state: 
            command = Command.STATUS
        if command:
            self._onCommand(command, address)

    def _device_goto(self, address, level, timeout=None, rate=None):
        message = UPBMessage()
        message.network = address[0]
        message.destination = address[1]
#        message.message_eid = UPBMessage.MessageDeviceControl.goto
        message.message_did = UPBMessage.MessageDeviceControl.goto
        message.message_data = Conversions.int_to_ascii(level)
        if rate != None:
            message.message_data = message.message_data + \
                                    Conversions.int_to_ascii(rate)
        command = message.to_hex()
        command = command + Conversions.hex_to_ascii('0D')
        commandExecutionDetails = self._sendInterfaceCommand(
                             self._modemCommands['send_upb'], command)
        return self._waitForCommandToFinish(commandExecutionDetails, timeout=timeout)

    def _link_activate(self, address, timeout=None):
        message = UPBMessage()
        message.link_type = UPBMessage.LinkType.link
        message.network = address[0]
        message.destination = address[1]
#        message.message_eid = UPBMessage.MessageDeviceControl.goto
        message.message_did = UPBMessage.MessageDeviceControl.activate
        command = message.to_hex()
        command = command + Conversions.hex_to_ascii('0D')
        commandExecutionDetails = self._sendInterfaceCommand(
                             self._modemCommands['send_upb'], command)
        return self._waitForCommandToFinish(commandExecutionDetails, timeout=timeout)        

    def _link_deactivate(self, address, timeout=None):
        message = UPBMessage()
        message.link_type = UPBMessage.LinkType.link
        message.network = address[0]
        message.destination = address[1]
#        message.message_eid = UPBMessage.MessageDeviceControl.goto
        message.message_did = UPBMessage.MessageDeviceControl.deactivate
        command = message.to_hex()
        command = command + Conversions.hex_to_ascii('0D')
        commandExecutionDetails = self._sendInterfaceCommand(
                             self._modemCommands['send_upb'], command)
        return self._waitForCommandToFinish(commandExecutionDetails, timeout=timeout)


    def status(self, address, timeout=None):
        message = UPBMessage()
        message.network = address[0]
        message.destination = address[1]
#        message.message_eid = UPBMessage.MessageDeviceControl.goto
        message.message_did = UPBMessage.MessageDeviceControl.report_state
        command = message.to_hex()
        command = command + Conversions.hex_to_ascii('0D')
        commandExecutionDetails = self._sendInterfaceCommand(
                             self._modemCommands['send_upb'], command)
        return self._waitForCommandToFinish(commandExecutionDetails, timeout=timeout)      

    def on(self, address, timeout=None, rate=None):
        if len(address) <= 2:
            return self._device_goto(address, 0x64, timeout=timeout)
        else: # Device Link
            return self._link_activate(address, timeout=timeout)

    def off(self, address, timeout=None, rate=None):
        if len(address) <= 2:
            return self._device_goto(address, 0x00, timeout=timeout)
        else: # Device Link
            return self._link_deactivate(address, timeout=timeout)
    
    def level(self, address, level, timeout=None, rate=None):
        if len(address) <= 2:
            self._device_goto(address, level, timeout, rate)
        else: # Device Link
            if level >= 50:
                return self._link_activate(address, timeout=timeout)
            else:
                return self._link_deactivate(address, timeout=timeout)
        
    def __getattr__(self, name):
        name = name.lower()
        # Support levels of lighting
        if name[0] == 'l' and len(name) == 3:
            level = name[1:3]
            self._logger.debug("Level->{level}".format(level=level))
            level = int(level)
            return lambda x, y=None: self._device_goto(x, level, timeout=y ) 
        
        
    def version(self):
        self._logger.info("UPB Pytomation driver version " + self.VERSION + "\n")

    def _set_device_state(self, address, state):
        for d in self._devices:
            if d.address == address:
                d.state = state

########NEW FILE########
__FILENAME__ = w800rf32
"""
File:
        w800rf32.py

Description:

This is a driver for the W800RF32 interface.  The W800 family of RF 
receivers are designed to receive X10 RF signals generated from X10 products: 
Palm Pad remotes, key chain remotes, Hawkeye motion detectors, and many, many 
other X10 RF devices.

The W800 then sends these commands directly to your computer's RS232 or 
USB port, depending on the model purchased. This allows your computer to 
receive X10 RF commands from remotes and motion detectors directly, without 
having to broadcast any power line commands, thus minimizing power line 
clutter and improving home automation response times by bypassing the usual 
power line delay.

This driver will re-initialize any of the boards that experience a power on 
reset or brownout without having to restart Pytomation.



Author(s):
         George Farris <farrisg@gmsys.com>
         Copyright (c), 2012
         
         Functions common to Pytomation written by:
         Jason Sharpee <jason@sharpee.com> 
         
License:
    This free software is licensed under the terms of the GNU public 
    license, Version 3

Usage:

    see /example_w800rf32_use.py

Notes:
    For documentation on the W800RF32 please see:
    http://www.wgldesigns.com/w800.html
    
Versions and changes:
    Initial version created on Oct 10 , 2012
    2012/11/14 - 1.1 - Added debug levels and global debug system
    2012/11/18 - 1.2 - Added logging
    2012/11/30 - 1.3 - Unify Command and State magic strings across the system
    2012/12/10 - 1.4 - New logging system
    
"""
import threading
import time
import re
from Queue import Queue
from binascii import unhexlify

from .common import *
from .ha_interface import HAInterface

class W800rf32(HAInterface):
    VERSION = '1.4'
    MODEM_PREFIX = ''
    
    hcodeDict = {
0b0110:'A', 0b1110:'B', 0b0010:'C', 0b1010:'D',
0b0001:'E', 0b1001:'F', 0b0101:'G', 0b1101:'H',
0b0111:'I', 0b1111:'J', 0b0011:'K', 0b1011:'L',
0b0000:'M', 0b1000:'N', 0b0100:'O', 0b1100:'P'}

    houseCode = ""
    unitNunber = 0
    command = ""

    def __init__(self, interface, *args, **kwargs):
        super(W800rf32, self).__init__(interface, *args, **kwargs)
    
    def _init(self, *args, **kwargs):
        super(W800rf32, self)._init(*args, **kwargs)
#        if not debug.has_key('W800'):
#            debug['W800'] = 0
        self.version()        
        self._modemRegisters = ""

        self._modemCommands = {
                               }

        self._modemResponse = {
                               }

    def _readInterface(self, lastPacketHash):
        #check to see if there is anyting we need to read
        responses = self._interface.read()
        if len(responses) >= 4:
            x = "{0:08b}".format(ord(responses[0]))  # format binary string
            b3 = int(x[::-1],2)   # reverse the string and assign to byte 3
            x = "{0:08b}".format(ord(responses[1]))  # format binary string
            b4 = int(x[::-1],2)   # reverse the string and assign to byte 4
            x = "{0:08b}".format(ord(responses[2]))  # format binary string
            b1 = int(x[::-1],2)   # reverse the string and assign to byte 1
            x = "{0:08b}".format(ord(responses[3]))  # format binary string
            b2 = int(x[::-1],2)   # reverse the string and assign to byte 2
#            if debug['W800'] > 0:
#                pylog(self,"[W800RF32] {0:02X} {1:02X} {2:02X} {3:02X}\n".format(b1,b2,b3,b4))
            self._logger.debug("{0:02X} {1:02X} {2:02X} {3:02X}".format(b1,b2,b3,b4))

            # Get the house code
            self.houseCode = self.hcodeDict[b3 & 0x0f]

            # Next find unit number
            x = b1 >> 3
            x1 = (b1 & 0x02) << 1
            y = (b3 & 0x20) >> 2
            self.unitNumber = x + x1 + y + 1
            
            # Find command
            # 0x19 and 0x11 map to dim and bright but we don't support dim  and bright here so 
            # we map it to the illegal unit code "0". 0x11 and 0x19 will not map correctly
            # on all keypads.  4 unit keypads will have units 1 to 3 correct but unit 4 will be
            # 4 for "on" but 5 for "off".  Five unit keypads will be opposite, 5 will be "on" 
            # and 4 will be "off" but we already have a 4 "off".
            if b1 == 0x19:
                self.command = Command.OFF  
                self.unitNumber = 0         
            elif b1 == 0x11:                
                self.command = Command.ON
                self.unitNumber = 0
            elif b1 & 0x05 == 4:
                self.command = Command.OFF
            elif b1 & 0x05 == 0:
                self.command = Command.ON
            
            self.x10 = "%s%d" % (self.houseCode, self.unitNumber)
#            if debug['W800'] > 0:
#                pylog(self, "[W800RF32] Command -> " + self.x10 + " " + self.command + "\n")
            self._logger.debug("Command -> " + self.x10 + " " + self.command )
                
            self._processDigitalInput(self.x10, self.command)
        elif len(responses) < 3 and len(responses) > 0:
            self._logger.error('We didnt expect a shorter packet. Probably should keep track of partial reads: ' + str(responses))
        else:
            time.sleep(0.5)
                
                

    def _processDigitalInput(self, addr, cmd):
        self._onCommand(address=addr, command=cmd)


    def _processRegister(self, response, lastPacketHash):
        foundCommandHash = None

        #find our pending command in the list so we can say that we're done (if we are running in syncronous mode - if not well then the caller didn't care)
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
            if commandDetails['modemCommand'] == self._modemCommands['read_register']:
                #Looks like this is our command.  Lets deal with it
                self._commandReturnData[commandHash] = response[4:]

                waitEvent = commandDetails['waitEvent']
                waitEvent.set()

                foundCommandHash = commandHash
                break

        if foundCommandHash:
            del self._pendingCommandDetails[foundCommandHash]
        else:
#            pylog(self, "[W800RF32] Unable to find pending command details for the following packet:\n")
#            pylog(self, hex_dump(response) + " " + len(response) + "n")
            self._logger.warning("Unable to find pending command details for the following packet:")
            self._logger.warning(hex_dump(response) + " " + len(response))

    def _processNewW800RF32(self, response):
        pass

    def version(self):
#        pylog(self, "W800RF32 Pytomation driver version " + self.VERSION + "\n")
        self._logger.info("W800RF32 Pytomation driver version " + self.VERSION)       

########NEW FILE########
__FILENAME__ = wemo
from pytomation.utility.miranda import upnp
from .ha_interface import HAInterface
from .common import *

"""
sourcE: http://www.scriptforge.org/quick-hack-of-the-belkin-wemo-switch/

from miranda import upnp
conn = upnp()
resp = conn.sendSOAP('10.100.200.41:49153', 'urn:Belkin:service:basicevent:1', 
     'http://10.100.200.41:49153/upnp/control/basicevent1', 
     'SetBinaryState', {'BinaryState': (1, 'Boolean')})

"""

class WeMo(HAInterface):
    def __init__(self, ip, port=None, *args, **kwargs):
        self._ip = ip
        self._port = port
        super(WeMo, self).__init__(None, *args, **kwargs)
    
    def _setstate(self, state):
        conn = upnp()
        #print 'uuuuu - {0}:{1}'.format(self._ip, self._port)
        try:
            resp = conn.sendSOAP('{0}:{1}'.format(self._ip, self._port),
                                'urn:Belkin:service:basicevent:1', 
                                'http://{0}:{1}/upnp/control/basicevent1'.format(self._ip, self._port), 
             'SetBinaryState', {'BinaryState': (state, 'Boolean')})
        except Exception, ex:
            self._logger.error('Error trying to send command: '+ str(ex))
            
        return resp

    def on(self, *args, **kwargs):
        self._setstate(1)
        
    def off(self, *args, **kwargs):
        self._setstate(0)
########NEW FILE########
__FILENAME__ = wtdio
"""
File:
        wtdio.py

Description:

This is a driver for the Weeder WTDIO board.  The WDTIO board is a digital I/O 
board that has 14 I/O channel on it, named A to N.  The Weeder boards can be 
daisy chanined up to 16 boards.  Each board has DIP switch settings for it's 
address and are defined as A to P.

This driver will re-initialize any of the boards that experience a power on 
reset or brownout without having to restart Pytomation.

The the I/O channels on the WTDIO board are set according to the following 
command set.
S = Switch, L = Output, default low

Inputs are set by sending the board data in the following sequence.  
BOARD TYPE CHANNEL
Example:  Board 'A', Type SWITCH, Channel D - 'ASD'
Currently only SWITCH inputs are handled.

Outputs are set as follows: BOARD LEVEL CHANNEL
Example:  Board 'A', Level LOW, Channel 'M', - 'ALM'

It's possible to set the output to a HIGH level when it is initialized but 
this is not supported by this driver.

I'll change this later to make full use of the weeder boards capabilities


Author(s):
         George Farris <farrisg@gmsys.com>
         Copyright (c), 2012

         Functions common to Pytomation written by:
         Jason Sharpee <jason@sharpee.com> 

License:
    This free software is licensed under the terms of the GNU public license, Version 3

Usage:

    see /example_wtdio_use.py

Notes:
    For documentation on the Weeder wtdio please see:
    http://www.weedtech.com/wtdio-m.html

    This driver only supports 16 boards at present A-P

Versions and changes:
    Initial version created on Sept 10 , 2012
    2012/10/20 - 1.1 - Added version number and acknowledgement of Jasons work
                     - Added debug to control printing results
    2012/11/10 - 1.2 - Added debug levels and global debug system
    2012/11/18 - 1.3 - Added logging 
    2012/11/30 - 1.4 - Unify Command and State magic strings
    2012/12/07 - 1.5 - Add invert pin function.
    2012/12/07 - 1.6 - Update to new logging stuff
    2012/12/17 - 1.7 - readModem command now readInterface
    2013/02/15 - 1.8 - Fix output to channel
    
"""
import threading
import time
import re
from Queue import Queue
from binascii import unhexlify

from .common import *
from .ha_interface import HAInterface


class Wtdio(HAInterface):
    VERSION = '1.8'
    MODEM_PREFIX = ''
        
    def __init__(self, interface, *args, **kwargs):
        super(Wtdio, self).__init__(interface, *args, **kwargs)
        
    def _init(self, *args, **kwargs):
        super(Wtdio, self)._init(*args, **kwargs)

        self.version()
        self.boardSettings = []
        self._modemRegisters = ""

        self._modemCommands = {
                               }

        self._modemResponse = {
                               }
        # for inverting the I/O point 
        self.d_inverted = [False for x in xrange(14)]
                
        self.echoMode()	 #set echo off

        		
    def _readInterface(self, lastPacketHash):
        #check to see if there is anyting we need to read
        responses = self._interface.read()
        if len(responses) != 0:
            for response in responses.split():
                self._logger.debug("[WTDIO] Response> " + hex_dump(response))
                p = re.compile('[A-P][A-N][H,L]')
                if p.match(response):
                    self._processDigitalInput(response, lastPacketHash)
                elif response[1] =='!':
                    self._logger.debug("[WTDIO] Board [" + response[0] + "] has been reset or power cycled, reinitializing...\n")
                    for bct in self.boardSettings:
                        if bct[0] == response[0]:
                            self.setChannel(bct)
                elif response[1] == '?':
                    self._logger.debug("[WTDIO] Board [" + response[0] + "] received invalid command or variable...\n")
                    
        else:
            #print "Sleeping"
            #X10 is slow.  Need to adjust based on protocol sent.  Or pay attention to NAK and auto adjust
            #time.sleep(0.1)
            time.sleep(0.5)

    # response[0] = board, resonse[1] = channel, response[2] = L or H    
    def _processDigitalInput(self, response, lastPacketHash):
        if (response[2] == 'L' and not self.d_inverted[ord(response[1]) - 65]):
        #if (response[2] == 'L'):
            contact = Command.OFF
        else:
            contact = Command.ON
        self._onCommand(address=response[:2],command=contact)


    def _processRegister(self, response, lastPacketHash):
        foundCommandHash = None

        #find our pending command in the list so we can say that we're done (if we are running in syncronous mode - if not well then the caller didn't care)
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
            if commandDetails['modemCommand'] == self._modemCommands['read_register']:
                #Looks like this is our command.  Lets deal with it
                self._commandReturnData[commandHash] = response[4:]

                waitEvent = commandDetails['waitEvent']
                waitEvent.set()

                foundCommandHash = commandHash
                break

        if foundCommandHash:
            del self._pendingCommandDetails[foundCommandHash]
        else:
            self._logger.debug("[WTDIO] Unable to find pending command details for the following packet:\n")
            self._logger.debug((hex_dump(response, len(response)) + '\n'))

    def _processNewWTDIO(self, response):
        pass

	# Turn echo mode off on Weeder board
    def echoMode(self, timeout=None):
        command = 'AX0\r'
        commandExecutionDetails = self._sendInterfaceCommand(
                             command)

    # Initialize the Weeder board, input example "ASA"
    def setChannel(self, boardChannelType):
        p = re.compile('[A-P][S,L][A-N]')
        if not p.match(boardChannelType):
            self._logger.debug("[WTDIO] Error malformed command...   " + boardChannelType + '\n')
            return
        # Save the board settings in case we need to re-init
        if not boardChannelType in self.boardSettings:
            self.boardSettings.append(boardChannelType)
                
        command = boardChannelType + '\r'
        commandExecutionDetails = self._sendInterfaceCommand(command)

    def dio_invert(self, channel, value=True):
        self.d_inverted[ord(channel) - 65] = value
                    
    def on(self, address):
        command = address[0] + 'H' + address[1] + '\r'
        commandExecutionDetails = self._sendInterfaceCommand(command)
#        return self._waitForCommandToFinish(commandExecutionDetails, timeout=2.0)

    def off(self, address):
        command = address[0] + 'L' + address[1] + '\r'
        commandExecutionDetails = self._sendInterfaceCommand(command)
#        return self._waitForCommandToFinish(commandExecutionDetails, timeout=2.0)
		
    def listBoards(self):
        self._logger.info(self.boardSettings + '\n')
        
    def version(self):
        self._logger.info("WTDIO Pytomation driver version " + self.VERSION + '\n')


########NEW FILE########
__FILENAME__ = cron_timer
# CronTimer
# Based on code from:
#  Brian @  http://stackoverflow.com/questions/373335/suggestions-for-a-cron-like-scheduler-in-python

# references:
# http://docs.python.org/library/sched.html

import time
from datetime import datetime, timedelta
from threading import Timer, Event

from .periodic_timer import PeriodicTimer

# Some utility classes / functions first
class AllMatch(set):
    """Universal set - match everything"""
    def __contains__(self, item): return True

allMatch = AllMatch()

def conv_to_set(obj):  # Allow single integer to be provided
    if isinstance(obj, (int,long)):
        return set([obj])  # Single item
    if not isinstance(obj, set):
        obj = set(obj)
    return obj

# The actual Event class
class CronTimer(object):
    FREQUENCY = 1

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

        self.secs = None
        self.mins = None
        self.hours = None
        self.days = None
        self.months = None
        self.dow = None

        self.timer = PeriodicTimer(self.FREQUENCY)
        self.timer.action(self._check_for_event)

    def interval(self, secs=allMatch, min=allMatch, hour=allMatch,
                       day=allMatch, month=allMatch, dow=allMatch):
        if secs=='*':
            secs=allMatch
        if min=='*':
            min=allMatch
        if hour=='*':
            hour=allMatch
        if day=='*':
            day=allMatch
        if month=='*':
            month=allMatch
        if dow=='*':
            dow=allMatch
        self.secs = conv_to_set(secs)
        self.mins = conv_to_set(min)
        self.hours = conv_to_set(hour)
        self.days = conv_to_set(day)
        self.months = conv_to_set(month)
        self.dow = conv_to_set(dow)

    def action(self, action, action_args=()):
        self._action = action
        self._action_args = action_args

    def start(self):
        if not self.secs:
            raise Exception('Shouldnt be starting without definition first')
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def matchtime(self, t):
        """Return True if this event should trigger at the specified datetime"""
        return ((t.second     in self.secs) and
                (t.minute     in self.mins) and
                (t.hour       in self.hours) and
                (t.day        in self.days) and
                (t.month      in self.months) and
                (t.isoweekday()  in self.dow))

    def _check_for_event(self, *args, **kwargs):
        if datetime:
            t = datetime(*datetime.now().timetuple()[:6])
    #        print 'Time: ' + str(t) + ":" + str(self.secs)
            if self.matchtime(t):
    #            print 'Run action'
                if len(self._action_args) > 0:
                    self._action(self._action_args)
                else:
                    self._action()
                
    @staticmethod
    def to_cron(string):
        if string == None:
            return None

        date_object = None
        try: # Hours / Minutes
            try:
                date_object = datetime.strptime(string, '%I:%M%p')
            except:
                try:
                    date_object = datetime.strptime(string, '%I:%M %p')
                except:
                        date_object = datetime.strptime(string, '%H:%M')
            return (
                    0,
                    date_object.minute,
                    date_object.hour,
                    allMatch,
                    allMatch,
                    allMatch,
                    )
#            td = timedelta(
#                           years=0,
#                           months=0,
#                           days=0,
#                           hours=date_object.hour, 
#                           minutes=date_object.minute,
#                           seconds=0)
        except Exception, e:
            try: # Hours / Minutes / Seconds
                try:
                    date_object = datetime.strptime(string, '%I:%M:%S%p')
                except:
                    try:
                        date_object = datetime.strptime(string, '%I:%M:%S %p')
                    except:
                        date_object = datetime.strptime(string, '%H:%M:%S')
                return (
                    date_object.second,
                    date_object.minute,
                    date_object.hour,
                    allMatch,
                    allMatch,
                    allMatch,
                    )
            except Exception, ex:
                raise ex
#        date_object = datetime.strptime(string, '%b %d %Y %I:%M%p')
        return None

########NEW FILE########
__FILENAME__ = http_server
import BaseHTTPServer

from SimpleHTTPServer import SimpleHTTPRequestHandler
import pytomation.common.config 
from pytomation.common.pyto_logging import PytoLogging
from pytomation.common.pytomation_api import PytomationAPI

file_path = "/tmp"

class PytomationHandlerClass(SimpleHTTPRequestHandler):
    def __init__(self,req, client_addr, server):
#        self._request = req
#        self._address = client_addr
#        self._server = server
        self._logger = PytoLogging(self.__class__.__name__)
        self._api = PytomationAPI()

        SimpleHTTPRequestHandler.__init__(self, req, client_addr, server)
    
    def translate_path(self, path):
        global file_path
        path = file_path + path
        return path

    def do_GET(self):
        self.route()

    def do_POST(self):
        self.route()

    def do_PUT(self):
        self.route()
        
    def do_DELETE(self):
        self.route()

    def do_ON(self):
        self.route()
        
    def do_OFF(self):
        self.route()

    def route(self):
        p = self.path.split('/')
        method = self.command
#        print "pd:" + self.path + ":" + str(p[1:])
        if p[1].lower() == "api":
            data = None
            if method.lower() == 'post':
                length = int(self.headers.getheader('content-length'))
                data = self.rfile.read(length)
#                print 'rrrrr' + str(length) + ":" + str(data)
                self.rfile.close()
            response = self._api.get_response(method=method, path="/".join(p[2:]), type=None, data=data)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-length", len(response))
            self.end_headers()
            self.wfile.write(response)
            self.finish()
        else:
            getattr(SimpleHTTPRequestHandler, "do_" + self.command.upper())(self)

class PytomationHTTPServer(object):
    def __init__(self, address="127.0.0.1", port=8080, path="/tmp", *args, **kwargs):
        global file_path
        self._address = address
        self._port = port
        self._protocol = "HTTP/1.0"
        self._path = path
        file_path = path
        
    def start(self):
        server_address = (self._address, self._port)
        
        PytomationHandlerClass.protocol_version = self._protocol
        httpd = BaseHTTPServer.HTTPServer(server_address, PytomationHandlerClass)
        
        sa = httpd.socket.getsockname()
        print "Serving HTTP files at ", self._path, " on", sa[0], "port", sa[1], "..."
        httpd.serve_forever()
        #BaseHTTPServer.test(HandlerClass, ServerClass, protocol)


########NEW FILE########
__FILENAME__ = manhole
import re
##################### TELNET MANHOLE ##########################
from twisted.internet import reactor
from twisted.manhole import telnet

from pytomation.common.pytomation_system import *

class Manhole(object):
    """
    Create a telnet server that allows you to reference your pytomation objects
    directly.  All objects names will be converted to lowercase and spaces will
    be converted to underscore _ .
    """    
    def createShellServer(self, user='pyto', password='mation', port=2000, instances={}):
        print 'Creating shell server instance'
        factory = telnet.ShellFactory()
        listen_port = reactor.listenTCP( port, factory)
#        for instance_id, instance_detail in get_instances_detail().iteritems():
        for instance_id, instance_detail in instances.iteritems():
            name = re.sub('[\s]','_', instance_detail['name'].lower())
            factory.namespace.update(
                {
                    name: instance_detail['instance'],
                    instance_id: instance_detail['instance']
                }
                )
        factory.username = user
        factory.password = password
        print 'Listening on port '  + str(port)
        return listen_port

    def start(self, user='pyto', password='mation', port=2000, instances={}):
        reactor.callWhenRunning( self.createShellServer, user, password, port, instances)
        reactor.run()

########NEW FILE########
__FILENAME__ = miranda
#!/usr/bin/env python
################################
# Interactive UPNP application #
# Craig Heffner                #
# www.sourcesec.com            #
# 07/16/2008                   #
#
# Notes from Issac:
# http://code.google.com/p/miranda-upnp/
# Marks this file as GPL3 licensed by the author
# I have made minor modificatinos to get it to work with the wemo
#
################################

try:
	import sys,os
	from socket import *
	from urllib2 import URLError, HTTPError
	from platform import system as thisSystem
	import xml.dom.minidom as minidom
	import IN,urllib,urllib2
	import readline,time
	import pickle
	import struct
	import base64
	import re
	import getopt
except Exception,e:
	print 'Unmet dependency:',e
	sys.exit(1)

#Most of the cmdCompleter class was originally written by John Kenyan
#It serves to tab-complete commands inside the program's shell
class cmdCompleter:
    def __init__(self,commands):
        self.commands = commands

    #Traverses the list of available commands
    def traverse(self,tokens,tree):
	retVal = []

	#If there are no commands, or no user input, return null
	if tree is None or len(tokens) == 0:
            return []
	#If there is only one word, only auto-complete the primary commands
        elif len(tokens) == 1:
            retVal = [x+' ' for x in tree if x.startswith(tokens[0])]
	#Else auto-complete for the sub-commands
        elif tokens[0] in tree.keys():
                retVal = self.traverse(tokens[1:],tree[tokens[0]])
	return retVal

    #Returns a list of possible commands that match the partial command that the user has entered
    def complete(self,text,state):
        try:
            tokens = readline.get_line_buffer().split()
            if not tokens or readline.get_line_buffer()[-1] == ' ':
                tokens.append('')
            results = self.traverse(tokens,self.commands) + [None]
            return results[state]
        except:
            return

#UPNP class for getting, sending and parsing SSDP/SOAP XML data (among other things...)
class upnp:
	ip = False
	port = False
	completer = False
	msearchHeaders = {
		'MAN' : '"ssdp:discover"',
		'MX'  : '2'
	}
	DEFAULT_IP = "239.255.255.250"
	DEFAULT_PORT = 1900
	UPNP_VERSION = '1.0'
	MAX_RECV = 8192
	HTTP_HEADERS = []
	ENUM_HOSTS = {}
	VERBOSE = False
	UNIQ = False
	DEBUG = False
	LOG_FILE = False
	IFACE = None
	STARS = '****************************************************************'
	csock = False
	ssock = False

	def __init__(self, ip=False, port=False, iface=None, appCommands=[]):
		if appCommands:
			self.completer = cmdCompleter(appCommands)
		if self.initSockets(ip, port, iface) == False:
			print 'UPNP class initialization failed!'
			print 'Bye!'
			sys.exit(1)
		else:
			self.soapEnd = re.compile('<\/.*:envelope>')

	#Initialize default sockets
	def initSockets(self, ip, port, iface):
		if self.csock:
			self.csock.close()
		if self.ssock:
			self.ssock.close()

		if iface != None:
			self.IFACE = iface
		if not ip:
			ip = self.DEFAULT_IP
			if not port:
				port = self.DEFAULT_PORT
			self.port = port
			self.ip = ip

		try:
			#This is needed to join a multicast group
			self.mreq = struct.pack("4sl",inet_aton(ip),INADDR_ANY)

			#Set up client socket
			self.csock = socket(AF_INET,SOCK_DGRAM)
			self.csock.setsockopt(IPPROTO_IP,IP_MULTICAST_TTL,2)

			#Set up server socket
			self.ssock = socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP)
			self.ssock.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)

			#Only bind to this interface
			if self.IFACE != None:
				print '\nBinding to interface',self.IFACE,'...\n'
				self.ssock.setsockopt(SOL_SOCKET,IN.SO_BINDTODEVICE,struct.pack("%ds" % (len(self.IFACE)+1,), self.IFACE))
				self.csock.setsockopt(SOL_SOCKET,IN.SO_BINDTODEVICE,struct.pack("%ds" % (len(self.IFACE)+1,), self.IFACE))

			try:
				self.ssock.bind(('',self.port))
			except Exception, e:
				print "WARNING: Failed to bind %s:%d: %s" , (self.ip,self.port,e)
			try:
				self.ssock.setsockopt(IPPROTO_IP,IP_ADD_MEMBERSHIP,self.mreq)
			except Exception, e:
				print 'WARNING: Failed to join multicast group:',e
		except Exception, e:
			print "Failed to initialize UPNP sockets:",e
			return False
		return True

	#Clean up file/socket descriptors
	def cleanup(self):
		if self.LOG_FILE != False:
			self.LOG_FILE.close()
		self.csock.close()
		self.ssock.close()

	#Send network data
	def send(self,data,socket):
		#By default, use the client socket that's part of this class
		if socket == False:
			socket = self.csock
		try:
			socket.sendto(data,(self.ip,self.port))
			return True
		except Exception, e:
			print "SendTo method failed for %s:%d : %s" % (self.ip,self.port,e)
			return False

	#Listen for network data
	def listen(self,size,socket):
		if socket == False:
			socket = self.ssock

		try:
			return socket.recv(size)
		except:
			return False

	#Create new UDP socket on ip, bound to port
	def createNewListener(self,ip=gethostbyname(gethostname()),port=1900):
		try:
			newsock = socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP)
			newsock.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
			newsock.bind((ip,port))
			return newsock
		except:
			return False

	#Return the class's primary server socket
	def listener(self):
		return self.ssock

	#Return the class's primary client socket
	def sender(self):
		return self.csock

	#Parse a URL, return the host and the page
	def parseURL(self,url):
		delim = '://'
		host = False
		page = False

		#Split the host and page
		try:
			(host,page) = url.split(delim)[1].split('/',1)
			page = '/' + page
		except:
			#If '://' is not in the url, then it's not a full URL, so assume that it's just a relative path
			page = url

		return (host,page)

	#Pull the name of the device type from a device type string
	#The device type string looks like: 'urn:schemas-upnp-org:device:WANDevice:1'
	def parseDeviceTypeName(self,string):
		delim1 = 'device:'
		delim2 = ':'

		if delim1 in string and not string.endswith(delim1):
			return string.split(delim1)[1].split(delim2,1)[0]
		return False

	#Pull the name of the service type from a service type string
	#The service type string looks like: 'urn:schemas-upnp-org:service:Layer3Forwarding:1'
	def parseServiceTypeName(self,string):
		delim1 = 'service:'
		delim2 = ':'

		if delim1 in string and not string.endswith(delim1):
			return string.split(delim1)[1].split(delim2,1)[0]
		return False

	#Pull the header info for the specified HTTP header - case insensitive
	def parseHeader(self,data,header):
		delimiter = "%s:" % header
		defaultRet = False

		lowerDelim = delimiter.lower()
		dataArray = data.split("\r\n")

		#Loop through each line of the headers
		for line in dataArray:
			lowerLine = line.lower()
			#Does this line start with the header we're looking for?
			if lowerLine.startswith(lowerDelim):
				try:
					return line.split(':',1)[1].strip()
				except:
					print "Failure parsing header data for %s" % header
		return defaultRet

	#Extract the contents of a single XML tag from the data
	def extractSingleTag(self,data,tag):
		startTag = "<%s" % tag
		endTag = "</%s>" % tag

		try:
			tmp = data.split(startTag)[1]
			index = tmp.find('>')
			if index != -1:
				index += 1
				return tmp[index:].split(endTag)[0].strip()
		except:
			pass
		return None

	#Parses SSDP notify and reply packets, and populates the ENUM_HOSTS dict
	def parseSSDPInfo(self,data,showUniq,verbose):
		hostFound = False
		messageType = False
		xmlFile = False
		host = False
		page = False
		upnpType = None
		knownHeaders = {
			'NOTIFY' : 'notification',
			'HTTP/1.1 200 OK' : 'reply'
		}

		#Use the class defaults if these aren't specified
		if showUniq == False:
			showUniq = self.UNIQ
		if verbose == False:
			verbose = self.VERBOSE

		#Is the SSDP packet a notification, a reply, or neither?
		for text,messageType in knownHeaders.iteritems():
			if data.upper().startswith(text):
				break
			else:
				messageType = False

		#If this is a notification or a reply message...
		if messageType != False:
			#Get the host name and location of it's main UPNP XML file
			xmlFile = self.parseHeader(data,"LOCATION")
			upnpType = self.parseHeader(data,"SERVER")
			(host,page) = self.parseURL(xmlFile)

			#Sanity check to make sure we got all the info we need
			if xmlFile == False or host == False or page == False:
				print 'ERROR parsing recieved header:'
				print self.STARS
				print data
				print self.STARS
				print ''
				return False

			#Get the protocol in use (i.e., http, https, etc)
			protocol = xmlFile.split('://')[0]+'://'

			#Check if we've seen this host before; add to the list of hosts if:
			#	1. This is a new host
			#	2. We've already seen this host, but the uniq hosts setting is disabled
			for hostID,hostInfo in self.ENUM_HOSTS.iteritems():
				if hostInfo['name'] == host:
					hostFound = True
					if self.UNIQ:
						return False

			if (hostFound and not self.UNIQ) or not hostFound:
				#Get the new host's index number and create an entry in ENUM_HOSTS
				index = len(self.ENUM_HOSTS)
				self.ENUM_HOSTS[index] = {
					'name' : host,
					'dataComplete' : False,
					'proto' : protocol,
					'xmlFile' : xmlFile,
					'serverType' : None,
					'upnpServer' : upnpType,
					'deviceList' : {}
				}
				#Be sure to update the command completer so we can tab complete through this host's data structure
				self.updateCmdCompleter(self.ENUM_HOSTS)

			#Print out some basic device info
			print self.STARS
			print "SSDP %s message from %s" % (messageType,host)

			if xmlFile:
				print "XML file is located at %s" % xmlFile

			if upnpType:
				print "Device is running %s"% upnpType

			print self.STARS
			print ''

	#Send GET request for a UPNP XML file
	def getXML(self, url):

		headers = {
			'USER-AGENT':'uPNP/'+self.UPNP_VERSION,
			'CONTENT-TYPE':'text/xml; charset="utf-8"'
		}

		try:
			#Use urllib2 for the request, it's awesome
			req = urllib2.Request(url, None, headers)
			response = urllib2.urlopen(req)
			output = response.read()
			headers = response.info()
			return (headers,output)
		except Exception, e:
			print "Request for '%s' failed: %s" % (url,e)
			return (False,False)

	#Send SOAP request
	def sendSOAP(self, hostName, serviceType, controlURL, actionName, actionArguments):
		argList = ''
		soapResponse = ''

		if '://' in controlURL:
			urlArray = controlURL.split('/',3)
			if len(urlArray) < 4:
				controlURL = '/'
			else:
				controlURL = '/' + urlArray[3]


		soapRequest = 'POST %s HTTP/1.1\r\n' % controlURL

		#Check if a port number was specified in the host name; default is port 80
		if ':' in hostName:
			hostNameArray = hostName.split(':')
			host = hostNameArray[0]
			try:
				port = int(hostNameArray[1])
			except:
				print 'Invalid port specified for host connection:',hostName[1]
				return False
		else:
			host = hostName
			port = 80

		#Create a string containing all of the SOAP action's arguments and values
		for arg,(val,dt) in actionArguments.iteritems():
			argList += '<%s>%s</%s>' % (arg,val,arg)

		#Create the SOAP request
		soapBody = 	"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
 <s:Body>
  <u:%s xmlns:u="%s">
   %s
  </u:%s>
 </s:Body>
</s:Envelope>
""" % (actionName, serviceType, argList, actionName)

		#Specify the headers to send with the request
		headers = 	{
			'Content-Type':'text/xml; charset="utf-8"',
			'SOAPACTION':'"%s#%s"' % (serviceType,actionName),
			'Content-Length': len(soapBody),
			'HOST':hostName,
			'User-Agent': 'CyberGarage-HTTP/1.0',
		}

		#Generate the final payload
		for head,value in headers.iteritems():
			soapRequest += '%s: %s\r\n' % (head,value)
		soapRequest += '\r\n%s' % soapBody

		#Send data and go into recieve loop
		try:
			sock = socket(AF_INET,SOCK_STREAM)
			sock.connect((host,port))
			sock.send(soapRequest)
			while True:
				data = sock.recv(self.MAX_RECV)
				if not data:
					break
				else:
					soapResponse += data
					if self.soapEnd.search(soapResponse.lower()) != None:
						break
			sock.close()

			(header,body) = soapResponse.split('\r\n\r\n',1)
			if not header.upper().startswith('HTTP/1.1 200'):
				print 'SOAP request failed with error code:',header.split('\r\n')[0].split(' ',1)[1]
				errorMsg = self.extractSingleTag(body,'errorDescription')
				if errorMsg:
					print 'SOAP error message:',errorMsg
				return False
			else:
				return body
		except Exception, e:
			print 'Caught socket exception:',e
			sock.close()
			return False
		except KeyboardInterrupt:
			sock.close()
		return False

	#Display all info for a given host
	def showCompleteHostInfo(self,index,fp):
		serviceKeys = ['controlURL','eventSubURL','serviceId','SCPDURL','fullName']
		if fp == False:
			fp = sys.stdout

		if index < 0 or index >= len(self.ENUM_HOSTS):
			fp.write('Specified host does not exist...\n')
			return
		try:
			hostInfo = self.ENUM_HOSTS[index]
			if hostInfo['dataComplete'] == False:
				print "Cannot show all host info because we don't have it all yet. Try running 'host info %d' first...\n" % index
			fp.write('Host name:         %s\n' % hostInfo['name'])
			fp.write('UPNP XML File:     %s\n\n' % hostInfo['xmlFile'])

			fp.write('\nDevice information:\n')
			for deviceName,deviceStruct in hostInfo['deviceList'].iteritems():
				fp.write('\tDevice Name: %s\n' % deviceName)
				for serviceName,serviceStruct in deviceStruct['services'].iteritems():
					fp.write('\t\tService Name: %s\n' % serviceName)
					for key in serviceKeys:
						fp.write('\t\t\t%s: %s\n' % (key,serviceStruct[key]))
					fp.write('\t\t\tServiceActions:\n')
					for actionName,actionStruct in serviceStruct['actions'].iteritems():
						fp.write('\t\t\t\t%s\n' % actionName)
						for argName,argStruct in actionStruct['arguments'].iteritems():
							fp.write('\t\t\t\t\t%s \n' % argName)
							for key,val in argStruct.iteritems():
								try:
									if key == 'relatedStateVariable':
										fp.write('\t\t\t\t\t\t%s:\n' % val)
										for k,v in serviceStruct['serviceStateVariables'][val].iteritems():
											fp.write('\t\t\t\t\t\t\t%s: %s\n' % (k,v))
									else:
										fp.write('\t\t\t\t\t\t%s: %s\n' % (key,val))
								except:
									pass

		except Exception, e:
			print 'Caught exception while showing host info:',e

	#Wrapper function...
	def getHostInfo(self, xmlData, xmlHeaders, index):
		if self.ENUM_HOSTS[index]['dataComplete'] == True:
			return

		if index >= 0 and index < len(self.ENUM_HOSTS):
			try:
				xmlRoot = minidom.parseString(xmlData)
				self.parseDeviceInfo(xmlRoot,index)
				self.ENUM_HOSTS[index]['serverType'] = xmlHeaders.getheader('Server')
				self.ENUM_HOSTS[index]['dataComplete'] = True
				return True
			except Exception, e:
				print 'Caught exception while getting host info:',e
		return False

	#Parse device info from the retrieved XML file
	def parseDeviceInfo(self,xmlRoot,index):
		deviceEntryPointer = False
		devTag = "device"
		deviceType = "deviceType"
		deviceListEntries = "deviceList"
		deviceTags = ["friendlyName","modelDescription","modelName","modelNumber","modelURL","presentationURL","UDN","UPC","manufacturer","manufacturerURL"]

		#Find all device entries listed in the XML file
		for device in xmlRoot.getElementsByTagName(devTag):
			try:
				#Get the deviceType string
				deviceTypeName = str(device.getElementsByTagName(deviceType)[0].childNodes[0].data)
			except:
				continue

			#Pull out the action device name from the deviceType string
			deviceDisplayName = self.parseDeviceTypeName(deviceTypeName)
			if not deviceDisplayName:
				continue

			#Create a new device entry for this host in the ENUM_HOSTS structure
			deviceEntryPointer = self.ENUM_HOSTS[index][deviceListEntries][deviceDisplayName] = {}
			deviceEntryPointer['fullName'] = deviceTypeName

			#Parse out all the device tags for that device
			for tag in deviceTags:
				try:
					deviceEntryPointer[tag] = str(device.getElementsByTagName(tag)[0].childNodes[0].data)
				except Exception:
					if self.VERBOSE:
						print 'Device',deviceEntryPointer['fullName'],'does not have a',tag
					continue
			#Get a list of all services for this device listing
			self.parseServiceList(device,deviceEntryPointer,index)

	#Parse the list of services specified in the XML file
	def parseServiceList(self,xmlRoot,device,index):
		serviceEntryPointer = False
		dictName = "services"
		serviceListTag = "serviceList"
		serviceTag = "service"
		serviceNameTag = "serviceType"
		serviceTags = ["serviceId","controlURL","eventSubURL","SCPDURL"]

		try:
			device[dictName] = {}
			#Get a list of all services offered by this device
			for service in xmlRoot.getElementsByTagName(serviceListTag)[0].getElementsByTagName(serviceTag):
				#Get the full service descriptor
				serviceName = str(service.getElementsByTagName(serviceNameTag)[0].childNodes[0].data)

				#Get the service name from the service descriptor string
				serviceDisplayName = self.parseServiceTypeName(serviceName)
				if not serviceDisplayName:
					continue

				#Create new service entry for the device in ENUM_HOSTS
				serviceEntryPointer = device[dictName][serviceDisplayName] = {}
				serviceEntryPointer['fullName'] = serviceName

				#Get all of the required service info and add it to ENUM_HOSTS
				for tag in serviceTags:
					serviceEntryPointer[tag] = str(service.getElementsByTagName(tag)[0].childNodes[0].data)

				#Get specific service info about this service
				self.parseServiceInfo(serviceEntryPointer,index)
		except Exception, e:
			print 'Caught exception while parsing device service list:',e

	#Parse details about each service (arguements, variables, etc)
	def parseServiceInfo(self,service,index):
		argIndex = 0
		argTags = ['direction','relatedStateVariable']
		actionList = 'actionList'
		actionTag = 'action'
		nameTag = 'name'
		argumentList = 'argumentList'
		argumentTag = 'argument'

		#Get the full path to the service's XML file
		xmlFile = self.ENUM_HOSTS[index]['proto'] + self.ENUM_HOSTS[index]['name']
		if not xmlFile.endswith('/') and not service['SCPDURL'].startswith('/'):
			xmlFile += '/'
		if self.ENUM_HOSTS[index]['proto'] in service['SCPDURL']:
			xmlFile = service['SCPDURL']
		else:
			xmlFile += service['SCPDURL']
		service['actions'] = {}

		#Get the XML file that describes this service
		(xmlHeaders,xmlData) = self.getXML(xmlFile)
		if not xmlData:
			print 'Failed to retrieve service descriptor located at:',xmlFile
			return False

		try:
			xmlRoot = minidom.parseString(xmlData)

			#Get a list of actions for this service
			try:
				actionList = xmlRoot.getElementsByTagName(actionList)[0]
			except:
				print 'Failed to retrieve action list for service %s!' % service['fullName']
				return False
			actions = actionList.getElementsByTagName(actionTag)
			if actions == []:
				print 'Failed to retrieve actions from service actions list for service %s!' % service['fullName']
				return False

			#Parse all actions in the service's action list
			for action in actions:
				#Get the action's name
				try:
					actionName = str(action.getElementsByTagName(nameTag)[0].childNodes[0].data).strip()
				except:
					print 'Failed to obtain service action name (%s)!' % service['fullName']
					continue

				#Add the action to the ENUM_HOSTS dictonary
				service['actions'][actionName] = {}
				service['actions'][actionName]['arguments'] = {}

				#Parse all of the action's arguments
				try:
					argList = action.getElementsByTagName(argumentList)[0]
				except:
					#Some actions may take no arguments, so continue without raising an error here...
					continue

				#Get all the arguments in this action's argument list
				arguments = argList.getElementsByTagName(argumentTag)
				if arguments == []:
					if self.VERBOSE:
						print 'Action',actionName,'has no arguments!'
					continue

				#Loop through the action's arguments, appending them to the ENUM_HOSTS dictionary
				for argument in arguments:
					try:
						argName = str(argument.getElementsByTagName(nameTag)[0].childNodes[0].data)
					except:
						print 'Failed to get argument name for',actionName
						continue
					service['actions'][actionName]['arguments'][argName] = {}

					#Get each required argument tag value and add them to ENUM_HOSTS
					for tag in argTags:
						try:
							service['actions'][actionName]['arguments'][argName][tag] = str(argument.getElementsByTagName(tag)[0].childNodes[0].data)
						except:
							print 'Failed to find tag %s for argument %s!' % (tag,argName)
							continue

			#Parse all of the state variables for this service
			self.parseServiceStateVars(xmlRoot,service)

		except Exception, e:
			print 'Caught exception while parsing Service info for service %s: %s' % (service['fullName'],str(e))
			return False

		return True

	#Get info about a service's state variables
	def parseServiceStateVars(self,xmlRoot,servicePointer):

		na = 'N/A'
		varVals = ['sendEvents','dataType','defaultValue','allowedValues']
		serviceStateTable = 'serviceStateTable'
		stateVariable = 'stateVariable'
		nameTag = 'name'
		dataType = 'dataType'
		sendEvents = 'sendEvents'
		allowedValueList = 'allowedValueList'
		allowedValue = 'allowedValue'
		allowedValueRange = 'allowedValueRange'
		minimum = 'minimum'
		maximum = 'maximum'

		#Create the serviceStateVariables entry for this service in ENUM_HOSTS
		servicePointer['serviceStateVariables'] = {}

		#Get a list of all state variables associated with this service
		try:
			stateVars = xmlRoot.getElementsByTagName(serviceStateTable)[0].getElementsByTagName(stateVariable)
		except:
			#Don't necessarily want to throw an error here, as there may be no service state variables
			return False

		#Loop through all state variables
		for var in stateVars:
			for tag in varVals:
				#Get variable name
				try:
					varName = str(var.getElementsByTagName(nameTag)[0].childNodes[0].data)
				except:
					print 'Failed to get service state variable name for service %s!' % servicePointer['fullName']
					continue

				servicePointer['serviceStateVariables'][varName] = {}
				try:
					servicePointer['serviceStateVariables'][varName]['dataType'] = str(var.getElementsByTagName(dataType)[0].childNodes[0].data)
				except:
					servicePointer['serviceStateVariables'][varName]['dataType'] = na
				try:
					servicePointer['serviceStateVariables'][varName]['sendEvents'] = str(var.getElementsByTagName(sendEvents)[0].childNodes[0].data)
				except:
					servicePointer['serviceStateVariables'][varName]['sendEvents'] = na

				servicePointer['serviceStateVariables'][varName][allowedValueList] = []

				#Get a list of allowed values for this variable
				try:
					vals = var.getElementsByTagName(allowedValueList)[0].getElementsByTagName(allowedValue)
				except:
					pass
				else:
					#Add the list of allowed values to the ENUM_HOSTS dictionary
					for val in vals:
						servicePointer['serviceStateVariables'][varName][allowedValueList].append(str(val.childNodes[0].data))

				#Get allowed value range for this variable
				try:
					valList = var.getElementsByTagName(allowedValueRange)[0]
				except:
					pass
				else:
					#Add the max and min values to the ENUM_HOSTS dictionary
					servicePointer['serviceStateVariables'][varName][allowedValueRange] = []
					try:
						servicePointer['serviceStateVariables'][varName][allowedValueRange].append(str(valList.getElementsByTagName(minimum)[0].childNodes[0].data))
						servicePointer['serviceStateVariables'][varName][allowedValueRange].append(str(valList.getElementsByTagName(maximum)[0].childNodes[0].data))
					except:
						pass
		return True

	#Update the command completer
	def updateCmdCompleter(self,struct):
		indexOnlyList = {
				'host' : ['get','details','summary'],
				'save' : ['info']
		}
		hostCommand = 'host'
		subCommandList = ['info']
		sendCommand = 'send'

		try:
			structPtr = {}
			topLevelKeys = {}
			for key,val in struct.iteritems():
				structPtr[str(key)] = val
				topLevelKeys[str(key)] = None

			#Update the subCommandList
			for subcmd in subCommandList:
				self.completer.commands[hostCommand][subcmd] = None
				self.completer.commands[hostCommand][subcmd] = structPtr

			#Update the indexOnlyList
			for cmd,data in indexOnlyList.iteritems():
				for subcmd in data:
					self.completer.commands[cmd][subcmd] = topLevelKeys

			#This is for updating the sendCommand key
			structPtr = {}
			for hostIndex,hostData in struct.iteritems():
				host = str(hostIndex)
				structPtr[host] = {}
				if hostData.has_key('deviceList'):
					for device,deviceData in hostData['deviceList'].iteritems():
						structPtr[host][device] = {}
						if deviceData.has_key('services'):
							for service,serviceData in deviceData['services'].iteritems():
								structPtr[host][device][service] = {}
								if serviceData.has_key('actions'):
									for action,actionData in serviceData['actions'].iteritems():
										structPtr[host][device][service][action] = None
			self.completer.commands[hostCommand][sendCommand] = structPtr
		except Exception:
			print "Error updating command completer structure; some command completion features might not work..."
		return




################## Action Functions ######################
#These functions handle user commands from the shell

#Actively search for UPNP devices
def msearch(argc, argv, hp, cycles=99999999):
	defaultST = "upnp:rootdevice"
	st = "schemas-upnp-org"
	myip = gethostbyname(gethostname())
	lport = hp.port

	if argc >= 3:
		if argc == 4:
			st = argv[1]
			searchType = argv[2]
			searchName = argv[3]
		else:
			searchType = argv[1]
			searchName = argv[2]
		st = "urn:%s:%s:%s:%s" % (st,searchType,searchName,hp.UPNP_VERSION.split('.')[0])
	else:
		st = defaultST

	#Build the request
	request = 	"M-SEARCH * HTTP/1.1\r\n"\
			"HOST:%s:%d\r\n"\
			"ST:%s\r\n" % (hp.ip,hp.port,st)
	for header,value in hp.msearchHeaders.iteritems():
			request += header + ':' + value + "\r\n"
	request += "\r\n"

	print "Entering discovery mode for '%s', Ctl+C to stop..." % st
	print ''

	#Have to create a new socket since replies will be sent directly to our IP, not the multicast IP
	server = hp.createNewListener(myip,lport)
	if server == False:
		print 'Failed to bind port %d' % lport
		return

	hp.send(request,server)
	while True:
		try:
			hp.parseSSDPInfo(hp.listen(1024,server),False,False)
		except Exception:
			print 'Discover mode halted...'
			server.close()
			break
		cycles -= 1
		if cycles == 0:
			print 'Discover mode halted...'
			server.close()
			break

#Passively listen for UPNP NOTIFY packets
def pcap(argc,argv,hp):
	print 'Entering passive mode, Ctl+C to stop...'
	print ''
	while True:
		try:
			hp.parseSSDPInfo(hp.listen(1024,False),False,False)
		except Exception:
			print "Passive mode halted..."
			break

#Manipulate M-SEARCH header values
def head(argc,argv,hp):
	if argc >= 2:
		action = argv[1]
		#Show current headers
		if action == 'show':
			for header,value in hp.msearchHeaders.iteritems():
				print header,':',value
			return
		#Delete the specified header
		elif action == 'del':
			if argc == 3:
				header = argv[2]
				if hp.msearchHeaders.has_key(header):
					del hp.msearchHeaders[header]
					print '%s removed from header list' % header
					return
				else:
					print '%s is not in the current header list' % header
					return
		#Create/set a headers
		elif action == 'set':
			if argc == 4:
				header = argv[2]
				value = argv[3]
				hp.msearchHeaders[header] = value
				print "Added header: '%s:%s" % (header,value)
				return

	showHelp(argv[0])

#Manipulate application settings
def seti(argc,argv,hp):
	if argc >= 2:
		action = argv[1]
		if action == 'uniq':
			hp.UNIQ = toggleVal(hp.UNIQ)
			print "Show unique hosts set to: %s" % hp.UNIQ
			return
		elif action == 'debug':
			hp.DEBUG = toggleVal(hp.DEBUG)
			print "Debug mode set to: %s" % hp.DEBUG
			return
		elif action == 'verbose':
			hp.VERBOSE = toggleVal(hp.VERBOSE)
			print "Verbose mode set to: %s" % hp.VERBOSE
			return
		elif action == 'version':
			if argc == 3:
				hp.UPNP_VERSION = argv[2]
				print 'UPNP version set to: %s' % hp.UPNP_VERSION
			else:
				showHelp(argv[0])
			return
		elif action == 'iface':
			if argc == 3:
				hp.IFACE = argv[2]
				print 'Interface set to %s, re-binding sockets...' % hp.IFACE
				if hp.initSockets(hp.ip,hp.port,hp.IFACE):
					print 'Interface change successful!'
				else:
					print 'Failed to bind new interface - are you sure you have root privilages??'
					hp.IFACE = None
				return
		elif action == 'socket':
			if argc == 3:
				try:
					(ip,port) = argv[2].split(':')
					port = int(port)
					hp.ip = ip
					hp.port = port
					hp.cleanup()
					if hp.initSockets(ip,port,hp.IFACE) == False:
						print "Setting new socket %s:%d failed!" % (ip,port)
					else:
						print "Using new socket: %s:%d" % (ip,port)
				except Exception, e:
					print 'Caught exception setting new socket:',e
				return
		elif action == 'show':
			print 'Multicast IP:          ',hp.ip
			print 'Multicast Port:        ',hp.port
			print 'Network Interface:     ',hp.IFACE
			print 'Number of known hosts: ',len(hp.ENUM_HOSTS)
			print 'UPNP Version:          ',hp.UPNP_VERSION
			print 'Debug mode:            ',hp.DEBUG
			print 'Verbose mode:          ',hp.VERBOSE
			print 'Show only unique hosts:',hp.UNIQ
			print 'Using log file:        ',hp.LOG_FILE
			return

	showHelp(argv[0])
	return

#Host command. It's kind of big.
def host(argc,argv,hp):

	indexList = []
	indexError = "Host index out of range. Try the 'host list' command to get a list of known hosts"
	if argc >= 2:
		action = argv[1]
		if action == 'list':
			if len(hp.ENUM_HOSTS) == 0:
				print "No known hosts - try running the 'msearch' or 'pcap' commands"
				return
			for index,hostInfo in hp.ENUM_HOSTS.iteritems():
				print "\t[%d] %s" % (index,hostInfo['name'])
			return
		elif action == 'details':
			hostInfo = False
			if argc == 3:
				try:
					index = int(argv[2])
				except Exception, e:
					print indexError
					return

				if index < 0 or index >= len(hp.ENUM_HOSTS):
					print indexError
					return
				hostInfo = hp.ENUM_HOSTS[index]

				try:
					#If this host data is already complete, just display it
					if hostInfo['dataComplete'] == True:
						hp.showCompleteHostInfo(index,False)
					else:
						print "Can't show host info because I don't have it. Please run 'host get %d'" % index
				except KeyboardInterrupt, e:
					pass
				return

		elif action == 'summary':
			if argc == 3:

				try:
					index = int(argv[2])
					hostInfo = hp.ENUM_HOSTS[index]
				except:
					print indexError
					return

				print 'Host:',hostInfo['name']
				print 'XML File:',hostInfo['xmlFile']
				for deviceName,deviceData in hostInfo['deviceList'].iteritems():
					print deviceName
					for k,v in deviceData.iteritems():
						try:
							v.has_key(False)
						except:
							print "\t%s: %s" % (k,v)
				print ''
				return

		elif action == 'info':
			output = hp.ENUM_HOSTS
			dataStructs = []
			for arg in argv[2:]:
				try:
					arg = int(arg)
				except:
					pass
				output = output[arg]
			try:
				for k,v in output.iteritems():
					try:
						v.has_key(False)
						dataStructs.append(k)
					except:
						print k,':',v
						continue
			except:
				print output

			for struct in dataStructs:
				print struct,': {}'
			return

		elif action == 'get':
			hostInfo = False
			if argc == 3:
				try:
					index = int(argv[2])
				except:
					print indexError
					return
				if index < 0 or index >= len(hp.ENUM_HOSTS):
						print "Host index out of range. Try the 'host list' command to get a list of known hosts"
						return
				else:
					hostInfo = hp.ENUM_HOSTS[index]

					#If this host data is already complete, just display it
					if hostInfo['dataComplete'] == True:
						print 'Data for this host has already been enumerated!'
						return

					try:
						#Get extended device and service information
						if hostInfo != False:
							print "Requesting device and service info for %s (this could take a few seconds)..." % hostInfo['name']
							print ''
							if hostInfo['dataComplete'] == False:
								(xmlHeaders,xmlData) = hp.getXML(hostInfo['xmlFile'])
								if xmlData == False:
									print 'Failed to request host XML file:',hostInfo['xmlFile']
									return
								if hp.getHostInfo(xmlData,xmlHeaders,index) == False:
									print "Failed to get device/service info for %s..." % hostInfo['name']
									return
							print 'Host data enumeration complete!'
							hp.updateCmdCompleter(hp.ENUM_HOSTS)
							return
					except KeyboardInterrupt, e:
						return

		elif action == 'send':
			#Send SOAP requests
			index = False
			inArgCounter = 0

			if argc != 6:
				showHelp(argv[0])
				return
			else:
				try:
					index = int(argv[2])
				except:
					print indexError
					return
				deviceName = argv[3]
				serviceName = argv[4]
				actionName = argv[5]
				hostInfo = hp.ENUM_HOSTS[index]
				actionArgs = False
				sendArgs = {}
				retTags = []
				controlURL = False
				fullServiceName = False

				#Get the service control URL and full service name
				try:
					controlURL = hostInfo['proto'] + hostInfo['name']
					controlURL2 = hostInfo['deviceList'][deviceName]['services'][serviceName]['controlURL']
					if not controlURL.endswith('/') and not controlURL2.startswith('/'):
						controlURL += '/'
					controlURL += controlURL2
				except Exception,e:
					print 'Caught exception:',e
					print "Are you sure you've run 'host get %d' and specified the correct service name?" % index
					return False

				#Get action info
				try:
					actionArgs = hostInfo['deviceList'][deviceName]['services'][serviceName]['actions'][actionName]['arguments']
					fullServiceName = hostInfo['deviceList'][deviceName]['services'][serviceName]['fullName']
				except Exception,e:
					print 'Caught exception:',e
					print "Are you sure you've specified the correct action?"
					return False

				for argName,argVals in actionArgs.iteritems():
					actionStateVar = argVals['relatedStateVariable']
					stateVar = hostInfo['deviceList'][deviceName]['services'][serviceName]['serviceStateVariables'][actionStateVar]

					if argVals['direction'].lower() == 'in':
						print "Required argument:"
						print "\tArgument Name: ",argName
						print "\tData Type:     ",stateVar['dataType']
						if stateVar.has_key('allowedValueList'):
							print "\tAllowed Values:",stateVar['allowedValueList']
						if stateVar.has_key('allowedValueRange'):
							print "\tValue Min:     ",stateVar['allowedValueRange'][0]
							print "\tValue Max:     ",stateVar['allowedValueRange'][1]
						if stateVar.has_key('defaultValue'):
							print "\tDefault Value: ",stateVar['defaultValue']
						prompt = "\tSet %s value to: " % argName
						try:
							#Get user input for the argument value
							(argc,argv) = getUserInput(hp,prompt)
							if argv == None:
								print 'Stopping send request...'
								return
							uInput = ''

							if argc > 0:
								inArgCounter += 1

							for val in argv:
								uInput += val + ' '

							uInput = uInput.strip()
							if stateVar['dataType'] == 'bin.base64' and uInput:
								uInput = base64.encodestring(uInput)

							sendArgs[argName] = (uInput.strip(),stateVar['dataType'])
						except KeyboardInterrupt:
							return
						print ''
					else:
						retTags.append((argName,stateVar['dataType']))

				#Remove the above inputs from the command history
				while inArgCounter:
					readline.remove_history_item(readline.get_current_history_length()-1)
					inArgCounter -= 1

				#print 'Requesting',controlURL
				soapResponse = hp.sendSOAP(hostInfo['name'],fullServiceName,controlURL,actionName,sendArgs)
				if soapResponse != False:
					#It's easier to just parse this ourselves...
					for (tag,dataType) in retTags:
						tagValue = hp.extractSingleTag(soapResponse,tag)
						if dataType == 'bin.base64' and tagValue != None:
							tagValue = base64.decodestring(tagValue)
						print tag,':',tagValue
			return


	showHelp(argv[0])
	return

#Save data
def save(argc,argv,hp):
	suffix = '%s_%s.mir'
	uniqName = ''
	saveType = ''
	fnameIndex = 3

	if argc >= 2:
		if argv[1] == 'help':
			showHelp(argv[0])
			return
		elif argv[1] == 'data':
			saveType = 'struct'
			if argc == 3:
				index = argv[2]
			else:
				index = 'data'
		elif argv[1] == 'info':
			saveType = 'info'
			fnameIndex = 4
			if argc >= 3:
				try:
					index = int(argv[2])
				except Exception, e:
					print 'Host index is not a number!'
					showHelp(argv[0])
					return
			else:
				showHelp(argv[0])
				return

		if argc == fnameIndex:
			uniqName = argv[fnameIndex-1]
		else:
			uniqName = index
	else:
		showHelp(argv[0])
		return

	fileName = suffix % (saveType,uniqName)
	if os.path.exists(fileName):
		print "File '%s' already exists! Please try again..." % fileName
		return
	if saveType == 'struct':
		try:
			fp = open(fileName,'w')
			pickle.dump(hp.ENUM_HOSTS,fp)
			fp.close()
			print "Host data saved to '%s'" % fileName
		except Exception, e:
			print 'Caught exception saving host data:',e
	elif saveType == 'info':
		try:
			fp = open(fileName,'w')
			hp.showCompleteHostInfo(index,fp)
			fp.close()
			print "Host info for '%s' saved to '%s'" % (hp.ENUM_HOSTS[index]['name'],fileName)
		except Exception, e:
			print 'Failed to save host info:',e
			return
	else:
		showHelp(argv[0])

	return

#Load data
def load(argc,argv,hp):
	if argc == 2 and argv[1] != 'help':
		loadFile = argv[1]

		try:
			fp = open(loadFile,'r')
			hp.ENUM_HOSTS = {}
			hp.ENUM_HOSTS = pickle.load(fp)
			fp.close()
			hp.updateCmdCompleter(hp.ENUM_HOSTS)
			print 'Host data restored:'
			print ''
			host(2,['host','list'],hp)
			return
		except Exception, e:
			print 'Caught exception while restoring host data:',e

	showHelp(argv[0])

#Open log file
def log(argc,argv,hp):
	if argc == 2:
		logFile = argv[1]
		try:
			fp = open(logFile,'a')
		except Exception, e:
			print 'Failed to open %s for logging: %s' % (logFile,e)
			return
		try:
			hp.LOG_FILE = fp
			ts = []
			for x in time.localtime():
				ts.append(x)
			theTime = "%d-%d-%d, %d:%d:%d" % (ts[0],ts[1],ts[2],ts[3],ts[4],ts[5])
			hp.LOG_FILE.write("\n### Logging started at: %s ###\n" % theTime)
		except Exception, e:
			print "Cannot write to file '%s': %s" % (logFile,e)
			hp.LOG_FILE = False
			return
		print "Commands will be logged to: '%s'" % logFile
		return
	showHelp(argv[0])

#Show help
def help(argc,argv,hp):
	showHelp(False)

#Debug, disabled by default
def debug(argc,argv,hp):
	command = ''
	if hp.DEBUG == False:
		print 'Debug is disabled! To enable, try the seti command...'
		return
	if argc == 1:
		showHelp(argv[0])
	else:
		for cmd in argv[1:]:
			command += cmd + ' '
		command = command.strip()
		print eval(command)
	return
#Quit!
def exit(argc,argv,hp):
	quit(argc,argv,hp)

#Quit!
def quit(argc,argv,hp):
	if argc == 2 and argv[1] == 'help':
		showHelp(argv[0])
		return
	print 'Bye!'
	print ''
	hp.cleanup()
	sys.exit(0)

################ End Action Functions ######################

#Show command help
def showHelp(command):
	#Detailed help info for each command
	helpInfo = {
			'help' : {
					'longListing':
						'Description:\n'\
							'\tLists available commands and command descriptions\n\n'\
						'Usage:\n'\
							'\t%s\n'\
							'\t<command> help',
					'quickView':
						'Show program help'
				},
			'quit' : {
					'longListing' :
						'Description:\n'\
							'\tQuits the interactive shell\n\n'\
						'Usage:\n'\
							'\t%s',
					'quickView' :
						'Exit this shell'
				},
			'exit' : {

					'longListing' :
						'Description:\n'\
							'\tExits the interactive shell\n\n'\
						'Usage:\n'\
							'\t%s',
					'quickView' :
						'Exit this shell'
				},
			'save' : {
					'longListing' :
						'Description:\n'\
							'\tSaves current host information to disk.\n\n'\
						'Usage:\n'\
							'\t%s <data | info <host#>> [file prefix]\n'\
							"\tSpecifying 'data' will save the raw host data to a file suitable for importing later via 'load'\n"\
							"\tSpecifying 'info' will save data for the specified host in a human-readable format\n"\
							"\tSpecifying a file prefix will save files in for format of 'struct_[prefix].mir' and info_[prefix].mir\n\n"\
						'Example:\n'\
							'\t> save data wrt54g\n'\
							'\t> save info 0 wrt54g\n\n'\
						'Notes:\n'\
							"\to Data files are saved as 'struct_[prefix].mir'; info files are saved as 'info_[prefix].mir.'\n"\
							"\to If no prefix is specified, the host index number will be used for the prefix.\n"\
							"\to The data saved by the 'save info' command is the same as the output of the 'host details' command.",
					'quickView' :
						'Save current host data to file'
				},
			'seti' : {
					'longListing' :
						'Description:\n'\
							'\tAllows you  to view and edit application settings.\n\n'\
						'Usage:\n'\
							'\t%s <show | uniq | debug | verbose | version <version #> | iface <interface> | socket <ip:port> >\n'\
							"\t'show' displays the current program settings\n"\
							"\t'uniq' toggles the show-only-uniq-hosts setting when discovering UPNP devices\n"\
							"\t'debug' toggles debug mode\n"\
							"\t'verbose' toggles verbose mode\n"\
							"\t'version' changes the UPNP version used\n"\
							"\t'iface' changes the network interface in use\n"\
							"\t'socket' re-sets the multicast IP address and port number used for UPNP discovery\n\n"\
						'Example:\n'\
							'\t> seti socket 239.255.255.250:1900\n'\
							'\t> seti uniq\n\n'\
						'Notes:\n'\
							"\tIf given no options, 'seti' will display the current application settings",
					'quickView' :
						'Show/define application settings'
				},
			'head' : {
					'longListing' :
						'Description:\n'\
							'\tAllows you to view, set, add and delete the SSDP header values used in SSDP transactions\n\n'\
						'Usage:\n'\
							'\t%s <show | del <header> | set <header>  <value>>\n'\
							"\t'set' allows you to set SSDP headers used when sending M-SEARCH queries with the 'msearch' command\n"\
							"\t'del' deletes a current header from the list\n"\
							"\t'show' displays all current header info\n\n"\
						'Example:\n'\
							'\t> head show\n'\
							'\t> head set MX 3',
					'quickView' :
						'Show/define SSDP headers'
				},
			'host' : {
					'longListing' :
						'Description:\n'\
							"\tAllows you to query host information and iteract with a host's actions/services.\n\n"\
						'Usage:\n'\
							'\t%s <list | get | info | summary | details | send> [host index #]\n'\
							"\t'list' displays an index of all known UPNP hosts along with their respective index numbers\n"\
							"\t'get' gets detailed information about the specified host\n"\
							"\t'details' gets and displays detailed information about the specified host\n"\
							"\t'summary' displays a short summary describing the specified host\n"\
							"\t'info' allows you to enumerate all elements of the hosts object\n"\
							"\t'send' allows you to send SOAP requests to devices and services *\n\n"\
						'Example:\n'\
							'\t> host list\n'\
							'\t> host get 0\n'\
							'\t> host summary 0\n'\
							'\t> host info 0 deviceList\n'\
							'\t> host send 0 <device name> <service name> <action name>\n\n'\
						'Notes:\n'\
							"\to All host commands support full tab completion of enumerated arguments\n"\
							"\to All host commands EXCEPT for the 'host send', 'host info' and 'host list' commands take only one argument: the host index number.\n"\
							"\to The host index number can be obtained by running 'host list', which takes no futher arguments.\n"\
							"\to The 'host send' command requires that you also specify the host's device name, service name, and action name that you wish to send,\n\t  in that order (see the last example in the Example section of this output). This information can be obtained by viewing the\n\t  'host details' listing, or by querying the host information via the 'host info' command.\n"\
							"\to The 'host info' command allows you to selectively enumerate the host information data structure. All data elements and their\n\t  corresponding values are displayed; a value of '{}' indicates that the element is a sub-structure that can be further enumerated\n\t  (see the 'host info' example in the Example section of this output).",
					'quickView' :
						'View and send host list and host information'
				},
			'pcap' : {
					'longListing' :
						'Description:\n'\
							'\tPassively listens for SSDP NOTIFY messages from UPNP devices\n\n'\
						'Usage:\n'\
							'\t%s',
					'quickView' :
						'Passively listen for UPNP hosts'
				},
			'msearch' : {
					'longListing' :
						'Description:\n'\
							'\tActively searches for UPNP hosts using M-SEARCH queries\n\n'\
						'Usage:\n'\
							"\t%s [device | service] [<device name> | <service name>]\n"\
							"\tIf no arguments are specified, 'msearch' searches for upnp:rootdevices\n"\
							"\tSpecific device/services types can be searched for using the 'device' or 'service' arguments\n\n"\
						'Example:\n'\
							'\t> msearch\n'\
							'\t> msearch service WANIPConnection\n'\
							'\t> msearch device InternetGatewayDevice',
					'quickView' :
						'Actively locate UPNP hosts'
				},
			'load' : {
					'longListing' :
						'Description:\n'\
							"\tLoads host data from a struct file previously saved with the 'save data' command\n\n"\
						'Usage:\n'\
							'\t%s <file name>',
					'quickView' :
						'Restore previous host data from file'
				},
			'log'  : {
					'longListing' :
						'Description:\n'\
							'\tLogs user-supplied commands to a log file\n\n'\
						'Usage:\n'\
							'\t%s <log file name>',
					'quickView' :
						'Logs user-supplied commands to a log file'
				}
	}


	try:
		print helpInfo[command]['longListing'] % command
	except:
		for command,cmdHelp in helpInfo.iteritems():
			print "%s\t\t%s" % (command,cmdHelp['quickView'])

#Display usage
def usage():
	print '''
Command line usage: %s [OPTIONS]

	-s <struct file>	Load previous host data from struct file
	-l <log file>		Log user-supplied commands to log file
	-i <interface>		Specify the name of the interface to use (Linux only, requires root)
	-u			Disable show-uniq-hosts-only option
	-d			Enable debug mode
	-v			Enable verbose mode
	-h 			Show help
''' % sys.argv[0]
	sys.exit(1)

#Check command line options
def parseCliOpts(argc,argv,hp):
	try:
		opts,args = getopt.getopt(argv[1:],'s:l:i:udvh')
	except getopt.GetoptError, e:
		print 'Usage Error:',e
		usage()
	else:
		for (opt,arg) in opts:
			if opt == '-s':
				print ''
				load(2,['load',arg],hp)
				print ''
			elif opt == '-l':
				print ''
				log(2,['log',arg],hp)
				print ''
			elif opt == '-u':
				hp.UNIQ = toggleVal(hp.UNIQ)
			elif opt == '-d':
				hp.DEBUG = toggleVal(hp.DEBUG)
				print 'Debug mode enabled!'
			elif opt == '-v':
				hp.VERBOSE = toggleVal(hp.VERBOSE)
				print 'Verbose mode enabled!'
			elif opt == '-h':
				usage()
			elif opt == '-i':
				networkInterfaces = []
				requestedInterface = arg
				interfaceName = None
				found = False

				#Get a list of network interfaces. This only works on unix boxes.
				try:
					if thisSystem() != 'Windows':
						fp = open('/proc/net/dev','r')
						for line in fp.readlines():
							if ':' in line:
								interfaceName = line.split(':')[0].strip()
								if interfaceName == requestedInterface:
									found = True
									break
								else:
									networkInterfaces.append(line.split(':')[0].strip())
						fp.close()
					else:
						networkInterfaces.append('Run ipconfig to get a list of available network interfaces!')
				except Exception,e:
					print 'Error opening file:',e
					print "If you aren't running Linux, this file may not exist!"

				if not found and len(networkInterfaces) > 0:
					print "Failed to find interface '%s'; try one of these:\n" % requestedInterface
					for iface in networkInterfaces:
						print iface
					print ''
					sys.exit(1)
				else:
					if not hp.initSockets(False,False,interfaceName):
						print 'Binding to interface %s failed; are you sure you have root privilages??' % interfaceName

#Toggle boolean values
def toggleVal(val):
	if val:
		return False
	else:
		return True

#Prompt for user input
def getUserInput(hp,shellPrompt):
	defaultShellPrompt = 'upnp> '
	if shellPrompt == False:
		shellPrompt = defaultShellPrompt

	try:
		uInput = raw_input(shellPrompt).strip()
		argv = uInput.split()
		argc = len(argv)
	except KeyboardInterrupt, e:
		print '\n'
		if shellPrompt == defaultShellPrompt:
			quit(0,[],hp)
		return (0,None)
	if hp.LOG_FILE != False:
		try:
			hp.LOG_FILE.write("%s\n" % uInput)
		except:
			print 'Failed to log data to log file!'

	return (argc,argv)

#Main
def main(argc,argv):
	#Table of valid commands - all primary commands must have an associated function
	appCommands = {
			'help' : {
				'help' : None
				},
			'quit' : {
				'help' : None
				},
			'exit' : {
				'help' : None
				},
			'save' : {
				'data' : None,
				'info' : None,
				'help' : None
				},
			'load' : {
				'help' : None
				},
			'seti' : {
				'uniq' : None,
				'socket' : None,
				'show' : None,
				'iface' : None,
				'debug' : None,
				'version' : None,
				'verbose' : None,
				'help' : None
				},
			'head' : {
				'set' : None,
				'show' : None,
				'del' : None,
				'help': None
				},
			'host' : {
				'list' : None,
				'info' : None,
				'get'  : None,
				'details' : None,
				'send' : None,
				'summary' : None,
				'help' : None
				},
			'pcap' : {
				'help' : None
				},
			'msearch' : {
				'device' : None,
				'service' : None,
				'help' : None
				},
			'log'  : {
				'help' : None
				},
			'debug': {
				'command' : None,
				'help'    : None
				}
	}

	#The load command should auto complete on the contents of the current directory
        for file in os.listdir(os.getcwd()):
                appCommands['load'][file] = None

	#Initialize upnp class
	hp = upnp(False, False, None, appCommands);

	#Set up tab completion and command history
	readline.parse_and_bind("tab: complete")
	readline.set_completer(hp.completer.complete)

	#Set some default values
	hp.UNIQ = True
	hp.VERBOSE = False
	action = False
	funPtr = False

	#Check command line options
	parseCliOpts(argc,argv,hp)

	#Main loop
	while True:
		#Drop user into shell
		(argc,argv) = getUserInput(hp,False)
		if argc == 0:
			continue
		action = argv[0]
		funcPtr = False

		print ''
		#Parse actions
		try:
			if appCommands.has_key(action):
				funcPtr = eval(action)
		except:
			funcPtr = False
			action = False

		if callable(funcPtr):
			if argc == 2 and argv[1] == 'help':
				showHelp(argv[0])
			else:
				try:
					funcPtr(argc,argv,hp)
				except KeyboardInterrupt:
					print 'Action interrupted by user...'
			print ''
			continue
		print 'Invalid command. Valid commands are:'
		print ''
		showHelp(False)
		print ''


if __name__ == "__main__":
	try:
		main(len(sys.argv),sys.argv)
	except Exception, e:
		print 'Caught main exception:',e
		sys.exit(1)


########NEW FILE########
__FILENAME__ = periodic_timer
import time
from datetime import datetime, timedelta
from threading import Event
from apscheduler.scheduler import Scheduler


# The actual Event class
class PeriodicTimer(object):
    sched = None
    
    def __init__(self, frequency=60, *args, **kwargs):
        # Start the scheduler
        self.frequency = frequency

        self.scheduler_start()
        
        self._job = None
        self.is_stopped = Event()
        self.is_stopped.clear()

#         self.interval = frequency
#         self._timer = Timer(self.frequency, self._check_for_event, ())
        self.interval = frequency    

    def scheduler_start(self):
        if not PeriodicTimer.sched:
            PeriodicTimer.sched = Scheduler()
        if not PeriodicTimer.sched.running:
            PeriodicTimer.sched.start()

    @property
    def interval(self):
        return self.frequency

    @interval.setter
    def interval(self, frequency):
        self.frequency = frequency
        self.start()
        return self.frequency

    def action(self, action, *action_args, **kwargs):
        self._action = action
        self._action_args = action_args
        self._action_kwargs = kwargs

    def start(self):
#        if self._sched.running:
#            self._sched.shutdown()
        if not PeriodicTimer.sched:
            return

        self.stop()

        self._job = PeriodicTimer.sched.add_interval_job(self._check_for_event, seconds = self.frequency, max_instances=10, misfire_grace_time=10, coalesce=False)
        self.is_stopped.clear()

    def stop(self):
        if self._job:
            PeriodicTimer.sched.unschedule_job(self._job)
        self.is_stopped.set()        

    def _check_for_event(self):
        if self.is_stopped.isSet():
            return
        if self._action:
            self._action(*self._action_args, **self._action_kwargs)
        else:
            self.stop()
########NEW FILE########
__FILENAME__ = timer
import time
from datetime import datetime, timedelta
from threading import Timer as PTimer, Event


# The actual Event class
class Timer(object):

    def __init__(self, secs=60, *args, **kwargs):
        self._timer = None
        self._secs = secs
        self._action = None
        
    def _get_timer(self, secs):
        timer = PTimer(secs, self._run_action, ())
        timer.daemon = True
        return timer

    @property
    def interval(self):
        return self._secs

    @interval.setter
    def interval(self, secs):
        self.stop()
        self._secs = secs
        return secs

    def action(self, action, action_args, **kwargs):
        self._action = action
        self._action_args = action_args
        self._action_kwargs = kwargs
    
    def _run_action(self):
        if self._action:
            if isinstance(self._action_args, tuple):
                self._action(*self._action_args, **self._action_kwargs)
            else:
                self._action(self._action_args, **self._action_kwargs)
        else:
            self.stop()

    def start(self):
        self.stop()
        self._timer = self._get_timer(self._secs)
        self._timer.start()
            
    def stop(self):
        if self._timer and self._timer.isAlive():
            self._timer.cancel()
        if self._timer:
            del(self._timer)
        self._timer = None
        
    def restart(self):
        self.stop()
        self.start()

    def isAlive(self):
        return self._timer.isAlive() if self._timer else False
########NEW FILE########
__FILENAME__ = time_funcs
from datetime import datetime, timedelta

def crontime_in_range(item, start, end):
    startDt = datetime.strptime("{2}:{1}:{0}".format(*start[0:3]), '%H:%M:%S')
    endDt = datetime.strptime("{2}:{1}:{0}".format(*end[0:3]), '%H:%M:%S')
    itemDt = datetime.strptime("{2}:{1}:{0}".format(*item[0:3]), '%H:%M:%S')

    if startDt > endDt:
        endDt=endDt + timedelta(days=1)
        if itemDt < startDt:
            itemDt = itemDt + timedelta(days=1)

    if startDt <= itemDt <= endDt:
        #should technically check dates in cron as well.. for another day
        return True

    return False
########NEW FILE########
__FILENAME__ = pytomation
import os
from pytomation.common import config, pytomation_system

INSTANCES_DIR = './instances'


if __name__ == "__main__":
    print 'Pytomation'
    scripts = []
    script_names = os.listdir(INSTANCES_DIR)
    for script_name in script_names:
        if script_name.lower()[-3:]==".py" and script_name.lower() != "__init__.py":
            try:
                module = "instances.%s" % script_name[0:len(script_name)-3]
                print "Found Instance Script: " + module
                scripts.append( __import__(module, fromlist=['instances']))
            except ImportError, ex:
                print 'Error' + str(ex)
    print "Total Scripts: " + str(len(scripts))

    if len(scripts) > 0:
        # Start the whole system.  pytomation.common.system.start()
        try:
            loop_action=scripts[0].MainLoop
        except AttributeError, ex:
            loop_action=None

        pytomation_system.start(
            loop_action=loop_action,
            loop_time=config.loop_time, # Loop every 1 sec
            admin_user=config.admin_user,
            admin_password=config.admin_password,
            telnet_port=config.telnet_port,
            http_address=config.http_address,
            http_port=config.http_port,
            http_path=config.http_path,
        )
    else:
        print "No Scripts found. Exiting"

########NEW FILE########
__FILENAME__ = settings
# Django settings for pytomation_django project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '7g6)nfi2^rr_7_9(b=fwz*d!$42g*+vejho0mz_&amp;)+fu=-8e$='

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'pytomation_django.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'pytomation_django.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'pytomation_django.views.home', name='home'),
    # url(r'^pytomation_django/', include('pytomation_django.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for pytomation_django project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pytomation_django.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = MockInterface
from pytomation.interfaces import HAInterface

class MockInterface(object):
    _written = None
    _responses = {}
    _response_q = None

    def __init__(self, *args, **kwargs):
        pass

    def write(self, data=None):
        self._written = data
        self._response_q = self._get_response(data)

    def read(self, count=None):
        response = ""
        if self._response_q:
            if not count:
                count = len(self._response_q)
            response = self._response_q[:count]

            if count >= len(self._response_q):
                self._response_q = None
            else:
                self._response_q = self._response_q[count:]
        return response

    def _get_response(self, written):
        try:
            return self._responses[self._written]
        except:
            return None

    def add_response(self, response_set):
        self._responses.update(response_set)
        return True
    
    def immediate_response(self, response):
        self._response_q = response
########NEW FILE########
__FILENAME__ = mock_interface
import Queue
from pytomation.interfaces import Conversions
from pytomation.interfaces.common import *

class Mock_Interface(object):
    def __init__(self, *args, **kwargs):
        super(Mock_Interface, self).__init__(*args, **kwargs)
        self._read_data = ""
        self._write_data = []
        self._disabled = False
        
    def read(self, count=None):
        #print 'Reading for {0} bytes'.format(count)
        if count:
            data = self._read_data[:count]
            self._read_data = self._read_data[count:]
        else:
            data = self._read_data
            self._read_data = ""
            
        #print 'Returning data hhhh:' + hex_dump(data) + ":"
        return data

    def write(self, data=None, **kwargs):
        #print 'kkkkk' + str(kwargs)
        self._write_data.append(data)
        return True
    
    def put_read_data(self, data):
        print 'Adding data: ' + hex_dump(data) + ":"
        self._read_data += data
    
    def query_write_data(self):
        return self._write_data

    def clear_write_data(self):
        self._write_data = []
        
    @property
    def disabled(self):
        return self._disabled
    
    @disabled.setter
    def disabled(self, value):
        self._disabled = value
########NEW FILE########
__FILENAME__ = pytomation_api
from unittest import TestCase

from pytomation.common.pytomation_api import PytomationAPI
from pytomation.devices import StateDevice, State, Light
from pytomation.interfaces import Command

class PytomationAPITests(TestCase):
    def setUp(self):
        self.api = PytomationAPI()
    
    def test_instantiation(self):
        self.assertIsNotNone(self.api)
        
    def test_device_invalid(self):
        response = self.api.get_response(method='GET', path="junk/test")
        self.assertEqual(response, 'null')
        
    def test_device_list(self):
        d=StateDevice(name='device_test_1')
        d.on()
        response = self.api.get_response(method='GET', path="devices")
        self.assertTrue('"name": "device_test_1"' in response)
    
    def test_device_get(self):
        d=StateDevice(name='device_test_1')
        d.on()
        response = self.api.get_response(method='GET', path="device/" + str(d.type_id))
        self.assertTrue('"name": "device_test_1"' in response)
        
    def test_device_on(self):
        d=StateDevice(name='device_test_1')
        d.off()
        self.assertEqual(d.state, State.OFF)
        response = self.api.get_response(method='POST', path="device/" + str(d.type_id), data=['command=on'])
        self.assertEqual(d.state, State.ON)
        self.assertTrue('"name": "device_test_1"' in response)
        
    def test_device_level_encoded(self):
        d=Light(name='device_test_1')
        d.off()
        self.assertEqual(d.state, State.OFF)
        response = self.api.get_response(method='POST', path="device/" + str(d.type_id), data=['command=level%2C72'])
        self.assertEqual(d.state, (State.LEVEL, 72))
        self.assertTrue('"name": "device_test_1"' in response)
########NEW FILE########
__FILENAME__ = pytomation_object
from unittest import TestCase, main
from mock import Mock

from pytomation.devices import StateDevice
from pytomation.interfaces import UPB

class PytomationObjectTests(TestCase):
    def test_interface_name(self):
        name = "Main UPB"
        interface = Mock()
        interface.read.return_value = ""
        upb = UPB(interface, name=name)
        self.assertEqual(upb.name, name)
        
    def test_device_name(self):
        name = "Front Outlet"
        device = StateDevice(name=name)
        self.assertEqual(device.name, name)

    def test_type_id(self):
        
        device = StateDevice(name='Test')
        self.assertIsNotNone(device.type_id)
        
    def test_device_type_name(self):
        name = "Test"
        device = StateDevice(name=name)
        self.assertEqual(device.type_name, "StateDevice")
########NEW FILE########
__FILENAME__ = pytomation_system
from unittest import TestCase, main
from mock import Mock

from pytomation.common.pytomation_system import *
from pytomation.interfaces import HAInterface
from pytomation.devices import StateDevice


class SystemTests(TestCase):
    def test_get_instances(self):
        mint = Mock()
        mint.read.return_value = ''
        before = get_instances()
        int = HAInterface(mint, name='Int1')
        dev = StateDevice(name='Dev1')
        a = get_instances()
        self.assertIsNotNone(a)
        self.assertEqual(len(a), len(before))
        
    def test_get_instances_detail(self):
        l = len(get_instances())
        mint = Mock()
        mint.read.return_value = ''
        int = HAInterface(mint, name='Int1')
        dev = StateDevice(name='Dev1')
        a = get_instances_detail()
        self.assertIsNotNone(a)
#        self.assertEqual(len(a), l+2)
        self.assertEqual(a[dev.type_id]['name'], 'Dev1')
        self.assertEqual(a[dev.type_id]['type_name'], 'StateDevice')
        

########NEW FILE########
__FILENAME__ = pyto_logging
from unittest import TestCase, main

from pytomation.common import PytoLogging

class LoggingTests(TestCase):
    def test_log(self):
        logger = PytoLogging(__name__)
        logger.debug('This is a debug statement')
        logger.info('This is an info statement')
        logger.warning('This is a warning statement')
        logger.error('This is an error statement')
        logger.critical('This is a critical statement')
        self.assertTrue(True)
########NEW FILE########
__FILENAME__ = common
class DelegateTester(object):
    _args = []
    _kwargs = {}

    def delegate(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def get_delegate_params(self):
        return (self._args, self._kwargs)


########NEW FILE########
__FILENAME__ = attributes
from unittest import TestCase

from pytomation.interfaces import Command
from pytomation.devices import Attributes, State

class AttributesTest(TestCase):
    def test_instance(self):
        a = Attributes()
        self.assertIsNotNone(a)

    def test_attriubte(self):
        a = Attributes(
                       command=Command.OFF
                       )
        self.assertEqual(a.command, Command.OFF)
        
########NEW FILE########
__FILENAME__ = door

from unittest import TestCase, main
from mock import Mock

from pytomation.devices import Door, State
from pytomation.interfaces import Command

class DoorTests(TestCase):
    
    def setUp(self):
        self.interface = Mock()
        self.interface.state = State.UNKNOWN
        self.device = Door('D1', self.interface)

    def test_instantiation(self):
        self.assertIsNotNone(self.device,
                             'Door Device could not be instantiated')

    def test_door_open(self):
        self.assertEqual(self.device.state, State.UNKNOWN)
        self.device.command(Command.ON)
        self.assertEqual(self.device.state, State.OPEN)
        
    def test_door_closed(self):
        door = Door('D1', devices=(self.interface))
#        self.device._on_command('D1', State.ON, self.interface)
        self.device.command(Command.ON)
        self.assertEqual(self.device.state, State.OPEN)
#        self.device._on_command('D1', State.OFF, self.interface)
        self.device.command(Command.OFF)
        self.assertEqual(self.device.state, State.CLOSED)

if __name__ == '__main__':
    main() 
########NEW FILE########
__FILENAME__ = generic
from unittest import TestCase

from pytomation.devices import Generic, State


class GenericTests(TestCase):
    def setUp(self):
        self.device = Generic('asd')

    def test_instantiation(self):
        self.assertIsNotNone(self.device)

    def test_on(self):
        self.assertEqual(self.device.state, State.UNKNOWN)
        self.device.on()
        self.assertEqual(self.device.state, State.ON)
    
    def test_still(self):
        self.assertEqual(self.device.state, State.UNKNOWN)
        self.device.still()
        self.assertEqual(self.device.state, State.STILL)
        
    def test_open(self):
        self.assertEqual(self.device.state, State.UNKNOWN)
        self.device.open()
        self.assertEqual(self.device.state, State.OPEN)
        
        
########NEW FILE########
__FILENAME__ = google_voice
from unittest import TestCase, main
from mock import Mock

from pytomation.devices import State, Google_Voice, StateDevice
from pytomation.interfaces import Command

class Google_VoiceTests(TestCase):
    def setUp(self):
        self.gv = Google_Voice(user='jason@sharpee.com', password='password')
    
    def test_instantiation(self):
        self.assertIsInstance(self.gv, Google_Voice)

    def test_send(self):
        self.gv.command((Command.MESSAGE, '7777777777', 'This is the test'))

########NEW FILE########
__FILENAME__ = interface
import time
from unittest import TestCase, main
from mock import Mock, PropertyMock, MagicMock
from datetime import datetime

from pytomation.utility.timer import Timer as CTimer
from pytomation.devices import InterfaceDevice, State, StateDevice, Attribute
from pytomation.interfaces import Command, HAInterface

class InterfaceDevice_Tests(TestCase):
    
    def setUp(self):
        self.interface = Mock()
        p = PropertyMock(side_effect=ValueError)
        type(self.interface).state = p
        self.device = InterfaceDevice('D1', self.interface)
        
    def test_instantiation(self):
        self.assertIsNotNone(self.device,
                             'HADevice could not be instantiated')
        
    def test_no_param_init(self):
        d = InterfaceDevice()
        self.assertIsNotNone(d)

    def test_on(self):
        self.device.on()
        self.interface.on.assert_called_with('D1')
        
    def test_level(self):
        self.device.level(80)
        self.interface.level.assert_called_with('D1',80)
        
    def test_substate(self):    
        self.device.command((State.LEVEL, 80))
        self.interface.level.assert_called_with('D1', 80)
    
    def test_read_only(self):
        self.device.read_only(True)
        self.device.on()
        self.assertFalse(self.interface.on.called)

    def test_controlled_devices_no_delay_default(self):
        i = Mock()
        d1 = StateDevice()
        d2 = InterfaceDevice(
                             devices=(i,d1),
                             delay={
                                    Attribute.COMMAND: Command.OFF,
                                    Attribute.SECS: 3
                                    },
                             initial=State.ON,
                             )
        d1.off()
        self.assertEqual(d2.state, State.ON)
        d2.command(command=Command.OFF, source=i)
        self.assertEqual(d2.state, State.OFF)

    def test_time_on(self):
        now = datetime.now()
        hours, mins, secs = now.timetuple()[3:6]
        secs = (secs + 2) % 60
        mins += (secs + 2) / 60
        trigger_time = '{h}:{m}:{s}'.format(
                                             h=hours,
                                             m=mins,
                                             s=secs,
                                                 )
        self.device.time(time=trigger_time, command=Command.ON)
        time.sleep(3)
        self.assertTrue( self.interface.on.called)

    def test_random_sync(self):
        # Should randomly sync state with the objects
        # Usually for X10 devices that do not have an acknowledgement
        self.device.sync = True
        
        device = InterfaceDevice(address='asdf', 
                                 sync=True)
        self.assertIsNotNone(device)
        self.assertTrue(device.sync)
    
    def test_initial(self):
        interface = Mock()
        p = PropertyMock(side_effect=ValueError)
        type(interface).state = p
        device = InterfaceDevice(address='asdf',
                                 devices=interface,
                                 initial=State.ON
                                 )
        interface.on.assert_called_with('asdf')
#        interface.initial.assert_called_with('asdf')
        
        device1 = StateDevice()
        device1.on()
        interface2 = Mock()
        type(interface2).state = p
        device = InterfaceDevice(address='asdf',
                                 devices=interface2,
                                 initial=State.ON
                                 )
        interface2.on.assert_called_with('asdf')
        
    def test_incoming(self):
        i = MagicMock()
        hi = HAInterface(i)
        d = InterfaceDevice(address='asdf',
                             devices=hi)
        hi._onCommand(Command.ON, 'asdf')
        time.sleep(1)
        self.assertEqual(d.state, State.ON)
        
    def test_loop_prevention(self):
        d = InterfaceDevice(
                             devices=(self.interface),
                             delay={Attribute.COMMAND: Command.OFF,
                                    Attribute.SECS: 2}
                             )
        d.on();
        self.interface.on.assert_called_once_with(None)
        d.command(command=Command.OFF, source=self.interface)
        time.sleep(3)
        self.assertFalse(self.interface.off.called)

    def test_no_repeat(self):
        #if the state is already set then dont send the command again
        self.device.off()
        self.assertEqual(self.device.state, State.OFF)
        self.device.on()
        self.assertEqual(self.device.state, State.ON)
        self.interface.on.assert_called_once_with('D1')
        self.interface.on.reset_mock()
        self.device.on()
        self.assertEqual(self.device.state, State.ON)
        self.assertFalse(self.interface.on.called)
        
    def test_interface_interface_source(self):
        pass

if __name__ == '__main__':
    main() 
########NEW FILE########
__FILENAME__ = light
import time

from datetime import datetime
from unittest import TestCase, main
from mock import Mock

from pytomation.devices import Light, Door, Location, State, Motion, \
                                Photocell, Attribute, StateDevice
from pytomation.interfaces import Command

class LightTests(TestCase):

    def setUp(self):
        self.interface = Mock()
        self.interface.state = State.UNKNOWN
        self.device = Light('D1', self.interface)

    def test_instantiation(self):
        self.assertIsNotNone(self.device,
                             'Light Device could not be instantiated')

    def test_on(self):
        self.assertEqual(self.device.state, State.UNKNOWN)
        self.device.on()
        self.assertEqual(self.device.state, State.ON)
        self.assertTrue(self.interface.on.called)

    def test_on_time(self):
        pass
    
    def test_door_triggered(self):
        door = Door()
        self.assertIsNotNone(door)
        self.device = Light('D1', devices=(self.interface, door))
        door.open()
        self.assertTrue(self.interface.on.called)
        
    def test_door_closed(self):
        door = Door()
        self.assertIsNotNone(door)
        door.open()
        self.device = Light('D1', devices=(self.interface, door))
#        self.assertTrue(self.interface.initial.called)
        self.assertFalse(self.interface.off.called)
        door.close()
        self.assertTrue(self.interface.off.called)
#        self.interface.on.assert_called_once_with('')
        door.open()
        self.assertTrue(self.interface.on.called)
        
    def test_location_triggered(self):
        home = Location('35.2269', '-80.8433')
        home.local_time = datetime(2012,6,1,12,0,0)
        light = Light('D1', home)
        self.assertEqual(light.state, State.OFF)
        home.local_time = datetime(2012,6,1,0,0,0)
        self.assertEqual(home.state, State.DARK)
        self.assertEqual(light.state, State.ON)
        
    def test_motion_triggered(self):
        motion = Motion('D1', initial=State.STILL)
        self.assertEqual(motion.state, State.STILL)
        light = Light('D1', devices=motion)
        self.assertEqual(light.state, State.OFF)
        motion.motion()
        self.assertEqual(light.state, State.ON)

    def test_photocell_triggered(self):
        photo = Photocell('D1', initial=State.LIGHT)
        light = Light('D1', devices=photo)
        self.assertEquals(light.state, State.OFF)
        photo.dark()
        self.assertEquals(light.state, State.ON)
        
        
    def test_light_restricted(self):
        photo = Photocell('D1', initial=State.LIGHT)
        self.assertEqual(photo.state, State.LIGHT)
        motion = Motion('D1', initial=State.STILL)
        light = Light('D2', devices=(motion, photo),
                       initial=photo)
        self.assertEqual(light.state, State.OFF)
        motion.motion()
        self.assertEqual(light.state, State.OFF)
        photo.dark()
        self.assertEqual(light.state, State.ON)
        light.off()
        self.assertEqual(light.state, State.OFF)
        motion.motion()
        self.assertEqual(light.state, State.ON)

    def test_light_unrestricted(self):
        photo = Photocell('D1', initial=State.LIGHT)
        self.assertEqual(photo.state, State.LIGHT)
        motion = Motion('D1', initial=State.STILL)
        light = Light('D2', devices=(motion, photo),
                       initial=photo)
        self.assertEqual(light.state, State.OFF)
        motion.motion()
        self.assertEqual(light.state, State.OFF)
        motion.unrestricted = True
        motion.motion()
        self.assertEqual(light.state, State.ON)
        
#         photo.dark()
#         self.assertEqual(light.state, State.ON)
#         light.off()
#         self.assertEqual(light.state, State.OFF)
#         motion.motion()
#         self.assertEqual(light.state, State.ON)
        

    def test_delay_normal(self):
        # Door Open events retrigger delay
        # Instead of turning off in 2 secs should be 4
        door = Door()
        self.assertIsNotNone(door)
        light = Light(address='D1', 
                      devices=(self.interface, door),
                      delay={
                             Attribute.COMMAND: Command.OFF,
                             Attribute.SECS: 3,
                             Attribute.SOURCE: door}
                       )
        door.open()
        self.assertEqual(light.state, State.ON)
        door.close()
        self.assertEqual(light.state, State.ON)
        time.sleep(2)
        self.assertEqual(light.state, State.ON)
        time.sleep(2)
        self.assertEqual(light.state, State.OFF)

        # Check to see if we can immediately and directly still turn off
        light.off()
        door.open()
        self.assertEqual(light.state, State.ON)
        light.off()
        self.assertEqual(light.state, State.OFF)

    def test_delay_light_specific(self):
        # motion.off and Photocell.Light events do not retrigger
        motion = Motion()
        light = Light(address='D1', 
                      devices=(self.interface, motion),
                      trigger={
                             Attribute.COMMAND: Command.ON,
                             Attribute.MAPPED: Command.OFF,
                             Attribute.SECS: 3,
                             },
                       ignore={
                               Attribute.COMMAND: Command.STILL,
                               Attribute.SOURCE: motion,
                               }
                       )
        motion.motion()
        self.assertEqual(light.state, State.ON)
        time.sleep(2)
        motion.still()
        self.assertEqual(light.state, State.ON)
        time.sleep(1)
        self.assertEqual(light.state, State.OFF)

    def test_light_photocell_intial(self):
        motion = Motion()
        motion.still()
        photo = Photocell(address='asdf')
        photo.dark()
        light = Light(address='e3',
                      devices=(photo, motion),
                      initial=photo,
                      )
        self.assertEqual(light.state, State.ON)
        
    def test_light_photocell_delay(self):
        ## Dont like this behavior anymore
        # Delay off should not trigger when photocell tells us to go dark.
        # Do it immediately
#        photo = Photocell()
#        photo.dark()
#        light = Light(address='e3',
#                      devices=photo,
#                      delay={
#                             'command': Command.OFF,
#                             'secs': 3
#                             })
#        self.assertEqual(light.state, State.ON)
#        photo.light()
#        self.assertEqual(light.state, State.OFF)
        pass
    
    def test_level(self):
        self.device.command((Command.LEVEL, 40))
        self.interface.level.assert_called_with('D1', 40)
        
    def test_level_direct(self):
        self.device.level(50)
        self.interface.level.assert_called_with('D1', 50)
        
    def test_level_ramp(self):
        self.device.command((Command.LEVEL, 40, 20))
        self.interface.level.assert_called_with('D1', 40, 20)


    def test_time_cron(self):
        light = Light('a2',
                      time={
                            Attribute.COMMAND: Command.OFF,
                            Attribute.TIME:(0, 30, range(0,5), 0, 0)
                            })
        self.assertIsNotNone(light)
        
    def test_time_cron2(self):
        ttime = datetime.now().timetuple()[3:7]
        l = Light(address='12.03.BB',
                    time={
                    Attribute.TIME: (ttime[2]+2,ttime[1], ttime[0], '*','*','*'),
                    Attribute.COMMAND: Command.OFF
                    },
                    name='test')
        l.on()
        self.assertEqual(l.state, State.ON)
        time.sleep(2)
        self.assertEqual(l.state, State.OFF)
        
        
        
    def test_light_scenario1(self):
        m = Motion()
        l = Light(
                address=(49, 6), 
                devices=m,
                mapped={
                        Attribute.COMMAND: Command.MOTION,
                        Attribute.SECS: 30*60
                        },
                ignore=({
                        Attribute.COMMAND: Command.STILL
                        },
                        {
                        Attribute.COMMAND: Command.DARK
                        },
                    ),
                name='Lamp',
                )
        self.assertEqual(l.state, State.UNKNOWN)
        m.command(command=State.ON, source=None)
        self.assertEqual(l.state, State.UNKNOWN)
    
    def test_light_scenario_g1(self):
        d = Door()
        p = Photocell()
        p.light()
        l =  Light(address='xx.xx.xx', 
            devices=(d, p),
            mapped={
               Attribute.COMMAND: (Command.CLOSE),
               Attribute.MAPPED: Command.OFF,
               Attribute.SECS: 2,
            },
            ignore=({Attribute.COMMAND: Command.DARK}),
            name="Hallway Lights",)
        l.on()
        self.assertEqual(l.state, State.ON)
        d.close()
        self.assertEqual(l.state, State.ON)
        time.sleep(3)
        self.assertEqual(l.state, State.OFF)
        d.open()
        self.assertEqual(l.state, State.OFF)
        
        
    def test_light_scenario_2(self):
        m = Motion()
        l = Light(
                address=(49, 3),
                devices=(m),
                 ignore=({
                         Attribute.COMMAND: Command.DARK,
                         },
                         {
                          Attribute.COMMAND: Command.STILL}
                         ),
                 time={
                       Attribute.TIME: '11:59pm',
                       Attribute.COMMAND: Command.OFF
                       },
                 mapped={
                         Attribute.COMMAND: (
                                             Command.MOTION, Command.OPEN,
                                              Command.CLOSE, Command.LIGHT,
                                              ),
                         Attribute.MAPPED: Command.OFF,
                         Attribute.SECS: 2,
                         },
         name='Foyer Light',
                )
        l.off()
        self.assertEqual(l.state, State.OFF)
        m.motion()
        self.assertEqual(l.state, State.OFF)
        time.sleep(3)
        self.assertEqual(l.state, State.OFF)
        
    def test_scenario_g2(self):
        d = StateDevice()
        l = Light(address='1E.39.5C', 
               devices=(d),
               delay={
                   Attribute.COMMAND: Command.OFF,
                   Attribute.SECS: 2
                   },
               name='Stair Lights up')
        self.assertEqual(l.state, State.UNKNOWN)
        l.off()
        time.sleep(3)
        self.assertEqual(l.state, State.OFF)
        l.on()
        self.assertEqual(l.state, State.ON)
    
    def test_delay_non_native_command(self):
        m = Motion()
        l = Light(
                  devices=m,
                  delay={
                         Attribute.COMMAND: Command.STILL,
                         Attribute.SECS: 2,
                         },
                  initial=State.ON
                  )
        self.assertEqual(l.state, State.ON)
        m.still()
        self.assertEqual(l.state, State.ON)
        time.sleep(3)
        self.assertEqual(l.state, State.OFF)
        
    def test_light_scenario_g3(self):
        m1 = Motion()
        m2 = Motion()
        interface = Mock()
        l = Light(
                devices=(interface, m1, m2),
                    ignore={
                          Attribute.COMMAND: Command.STILL,
                          },
                    trigger=(
                           {
                           Attribute.COMMAND: Command.ON,
                           Attribute.MAPPED: Command.OFF,
                           Attribute.SOURCE: m2,
                           Attribute.SECS: 2
                            },
                         {
                           Attribute.COMMAND: Command.ON,
                           Attribute.MAPPED: Command.OFF,
                           Attribute.SOURCE: m1,
                           Attribute.SECS: 10
                           },
                         ),
                  initial=State.OFF,
                  )
        self.assertEqual(l.state, State.OFF)
        m1.motion()
        self.assertEqual(l.state, State.ON)
        # Interface updates us on the status
        l.command(command=Command.ON, source=interface)
        # call still just to add some noise. Should be ignored
        m1.still()
        self.assertEqual(l.state, State.ON)
        time.sleep(2)
        # Light should still be on < 10 secs
        self.assertEqual(l.state, State.ON)
        
        m2.motion()
        self.assertEqual(l.state, State.ON)
        # more noise to try and force an issue. Should be ignored
        m2.still()
        m1.still()
        self.assertEqual(l.state, State.ON)
        time.sleep(3)
        # total of 5 secs have elapsed since m1 and 3 since m2
        # Light should be off as m2 set the new time to only 2 secs
        self.assertEqual(l.state, State.OFF)
        
    def test_light_restriction_idle(self):
        ph = Photocell()
        m = Motion()
        ph.dark()
        l = Light(
                  devices=(ph, m),
                  idle={Attribute.MAPPED: (Command.LEVEL, 30),
                        Attribute.SECS: 2,
                        }
                  )
        m.motion()
        self.assertEqual(l.state, State.ON)
        ph.light()
        self.assertEqual(l.state, State.OFF)
        m.motion()
        self.assertEqual(l.state, State.OFF)
        time.sleep(3)
        self.assertEqual(l.state, State.OFF)

    def test_light_idle(self):
        m = Motion()
        m.still()
        l = Light(
                  devices=(m),
                  idle={Attribute.MAPPED: (Command.LEVEL, 30),
                        Attribute.SECS: 2,
                        }
                  )
        l.on()
        self.assertEqual(l.state, State.ON)
        time.sleep(3)
        self.assertEqual(l.state, (State.LEVEL, 30))
        #Light shouldnt idle if it is off
        l.off()
        self.assertEqual(l.state, State.OFF)
        time.sleep(3)
        self.assertEqual(l.state, State.OFF)
        
    def test_trigger_in_range_gc(self):
        (s_h, s_m, s_s) = datetime.now().timetuple()[3:6]
        e_h = s_h
        e_m = s_m
        e_s = s_s + 2
        d1 = StateDevice()
        d2 = Light(
                   devices=d1,
                   trigger={
                            Attribute.COMMAND: Command.ON,
                            Attribute.MAPPED: Command.OFF,
                            Attribute.SECS: 2,
                            Attribute.START: '{h}:{m}:{s}'.format(
                                                                 h=s_h,
                                                                 m=s_m,
                                                                 s=s_s,
                                                                 ),
                            Attribute.END: '{h}:{m}:{s}'.format(
                                                                 h=e_h,
                                                                 m=e_m,
                                                                 s=e_s,
                                                                 ),
                            }
                   )
        self.assertEqual(d2.state, State.UNKNOWN)
        d1.on()
        self.assertEqual(d2.state, State.ON)
        time.sleep(3)
        self.assertEqual(d2.state, State.OFF)
 
        #Out range
        d2.off()
        self.assertEqual(d2.state, State.OFF)
        d1.on()
        self.assertEqual(d2.state, State.ON)
        time.sleep(3)
        self.assertEqual(d2.state, State.ON)

    def test_trigger_out_range_gc(self):
        (s_h, s_m, s_s) = datetime.now().timetuple()[3:6]
        e_h = s_h
        e_m = s_m
        e_s = s_s + 2
        d1 = StateDevice()
        d2 = Light(
                   devices=d1,
                   trigger={
                            Attribute.COMMAND: Command.ON,
                            Attribute.MAPPED: Command.OFF,
                            Attribute.SECS: 2,
                            Attribute.START: '{h}:{m}:{s}'.format(
                                                                 h=s_h,
                                                                 m=s_m,
                                                                 s=s_s,
                                                                 ),
                            Attribute.END: '{h}:{m}:{s}'.format(
                                                                 h=e_h,
                                                                 m=e_m,
                                                                 s=e_s,
                                                                 ),
                            }
                   )

        time.sleep(3)
        self.assertEqual(d2.state, State.UNKNOWN)
        d1.on()
        self.assertEqual(d2.state, State.ON)
        time.sleep(3)
        self.assertEqual(d2.state, State.ON)

    def test_ignore_subcommand_wildcard(self):
        s1 = Light()
        s2 = Light(devices = s1,
                          ignore={
                                  Attribute.COMMAND: Command.LEVEL,
                                  },
                          )
        s1.on()
        self.assertEqual(s2.state, State.ON)
        s1.off()
        self.assertEqual(s2.state, State.OFF)
        s1.level(80)
        self.assertEqual(s2.state, State.OFF)

        
        
if __name__ == '__main__':
	main() 
########NEW FILE########
__FILENAME__ = location
import time

from datetime import datetime

from unittest import TestCase, main
from mock import Mock, patch

from pytomation.devices import Location, State, Light, Command, Attribute


class LocationTests(TestCase):
    def setUp(self):
        self.loc = Location('35.2269', '-80.8433')

    def test_sunset(self):
        self.loc.local_time = datetime(2012,6,1,0,0,0)
#        MockDateTime.now = classmethod(lambda x: datetime(2012,6,1,0,0,0))
        self.assertEqual(self.loc.state, State.DARK)
#        MockDateTime.now = classmethod(lambda x: datetime(2012,6,1,12,0,0))
        self.loc.local_time = datetime(2012,6,1,12,0,0)
        self.assertEqual(self.loc.state, State.LIGHT)
        
    def test_civil(self):
        ph_standard = Location('35.2269', '-80.8433', 
                       tz='US/Eastern', 
                       mode=Location.MODE.CIVIL, 
                       is_dst=True,
                       local_time=datetime(2012,11,26,17,15,0))
        self.assertIsNotNone(ph_standard)
        
    def test_delegate(self):
        self.loc.local_time = datetime(2012,6,1,1,0,0)
        self.assertEqual(self.loc.state, State.DARK)
        l = Light(devices=self.loc)
        self.assertEqual(l.state, State.ON)
        self.assertEqual(self.loc.state, State.DARK)

        self.loc.local_time = datetime(2012,6,1,12,0,0)
        self.assertEqual(self.loc.state, State.LIGHT)
        self.assertEqual(l.state, State.OFF)
        
    def test_read_only(self):
        self.loc.local_time = datetime(2012,6,1,0,0,0)
        self.assertEqual(self.loc.state, State.DARK)
        l2 = Light()
        l = Light(devices=(self.loc, l2))
        self.assertEqual(self.loc.state, State.DARK)
        l.on()
        self.assertEqual(l.state, State.ON)
        self.assertEqual(self.loc.state, State.DARK)
        l.off()
        self.assertEqual(self.loc.state, State.DARK)
        l2.off()
        self.assertEqual(self.loc.state, State.DARK)
        l2.on()
        self.assertEqual(self.loc.state, State.DARK)

    def test_gc_1(self):
        twilight_standard = Location( '42.2671389', '-71.8756111', 
                               tz='US/Eastern', 
                               mode=Location.MODE.STANDARD, 
                               is_dst=True,
                               name='Standard Twilight')
        
        twilight_standard.local_time = datetime(2012,6,1,0,0,0)
        self.assertEqual(twilight_standard.state, State.DARK)

        _back_porch = Light(address='21.03.24',
              devices=(twilight_standard),
              initial=twilight_standard,
#              command=(   {  Attribute.COMMAND: (Command.DARK),   Attribute.MAPPED: (Command.ON),   Attribute.SOURCE: (twilight_standard),  },
#                                   { Attribute.COMMAND: (Command.LIGHT),  Attribute.MAPPED: (Command.OFF),  Attribute.SOURCE: (twilight_standard), }, ),
              map=(   {  Attribute.COMMAND: (Command.DARK),   Attribute.MAPPED: (Command.ON),   Attribute.SOURCE: (twilight_standard),  },
                                   { Attribute.COMMAND: (Command.LIGHT),  Attribute.MAPPED: (Command.OFF),  Attribute.SOURCE: (twilight_standard), }, ),

              ignore=(  {   Attribute.COMMAND: Command.OFF,   Attribute.SOURCE: twilight_standard, }, ),
              time=(  { Attribute.COMMAND:(Command.LEVEL, 30),  Attribute.TIME: '11:15pm',    }, ),
              name="Back porch light")
        
        self.assertEqual(twilight_standard.state, State.DARK)
        self.assertEqual(_back_porch.state, State.ON)
        
        

########NEW FILE########
__FILENAME__ = motion

from unittest import TestCase, main
from mock import Mock, MagicMock
import time

from pytomation.devices import Motion, State, Attribute, StateDevice, Light
from pytomation.interfaces import Command

class MotionTests(TestCase):
    
    def setUp(self):
        self.interface = Mock()
        self.interface.state = State.UNKNOWN
        self.device = Motion('D1', self.interface)

    def test_instantiation(self):
        self.assertIsNotNone(self.device,
                             'Motion Device could not be instantiated')

    def test_motion_motion(self):
        self.assertEqual(self.device.state, State.UNKNOWN)
        self.device.command(Command.MOTION, source=self.interface)
#        self.device._on_command('D1', State.ON)
        self.assertEqual(self.device.state, State.MOTION)
#        self.device._on_command('D1', State.OFF)
        self.device.command(Command.STILL, source=self.interface)
        self.assertEqual(self.device.state, State.STILL)

    def test_motion_ignore(self):
        self.device = Motion('D1', devices=(self.interface), ignore={
                                                                      'command': Command.STILL,
                                                                      },
                              )
        self.device.command(Command.MOTION, source=self.interface)
#        self.device._on_command('D1', State.ON, self.interface)
        self.assertEqual(self.device.state, State.MOTION)
        self.device.command(Command.MOTION, source=self.interface)
#        self.device._on_command('D1', State.OFF, self.interface)
        self.assertEqual(self.device.state, State.MOTION)
        
    def test_motion_on(self):
        m = Motion()
        m.command(command=Command.ON, source=None)
        self.assertEqual(m.state, State.MOTION)        

    def test_motion_delay_from_interface(self):
        i = Mock()
        m = Motion(devices=i,
                   delay={
                          Attribute.COMMAND: Command.STILL,
                          Attribute.SECS: 2,
                          })
        m.command(command=Command.MOTION, source=i)
        self.assertEqual(m.state, State.MOTION)
        m.command(command=Command.STILL, source=i)
        self.assertEqual(m.state, State.MOTION)
        time.sleep(3)
        self.assertEqual(m.state, State.STILL)

    def test_motion_retrigger(self):
        i = Mock()
        m = Motion(devices=i,
                   retrigger_delay={
                                    Attribute.SECS: 2,
                                    },
                   )
        s = Light(devices=m)
        s.off()
        self.assertEqual(s.state, State.OFF)
        m.command(command=Command.ON, source=i)
        self.assertEqual(s.state, State.ON)
        s.off()
        self.assertEqual(s.state, State.OFF)
        m.command(command=Command.ON, source=i)
        self.assertEqual(s.state, State.OFF)
        time.sleep(3)
        m.command(command=Command.ON, source=i)
        self.assertEqual(s.state, State.ON)
        

if __name__ == '__main__':
    main() 
########NEW FILE########
__FILENAME__ = photocell

from unittest import TestCase, main
from mock import Mock

from pytomation.devices import Photocell, State
from pytomation.interfaces import Command

class PhotocellTests(TestCase):
    
    def setUp(self):
        self.interface = Mock()
        self.interface.state = State.UNKNOWN
        self.device = Photocell('D1', self.interface)

    def test_instantiation(self):
        self.assertIsNotNone(self.device,
                             'Photocell Device could not be instantiated')

    def test_photocell_state(self):
        self.assertEqual(self.device.state, State.UNKNOWN)
        self.device.command(Command.DARK)
        self.assertEqual(self.device.state, State.DARK)
        self.device.command(Command.LIGHT)
        self.assertEqual(self.device.state, State.LIGHT)


if __name__ == '__main__':
    main() 
########NEW FILE########
__FILENAME__ = room
from unittest import TestCase

from pytomation.devices import Room, Motion, Light, StateDevice, State

class RoomTests(TestCase):
    def setUp(self):
        pass
    
    def test_init(self):
        r = Room()
        self.assertIsNotNone(r)
        
    def test_room_occupied(self):
        m = Motion()
        r = Room(devices=m)
        r.vacate()
        self.assertEqual(r.state, State.VACANT)
        m.motion()
        self.assertEqual(r.state, State.OCCUPIED)
        
    def test_room_to_room_vacate(self):
        m1 = Motion(name='m1')
        m2 = Motion(name='m2')
        m3 = Motion(name='m3')
        r1 = Room(name='r1', devices=m1)
        r2 = Room(name='r2', devices=(m2, r1))
        r3 = Room(name='r3', devices=(m3, r2))
        r1.add_device(r2)
        r2.add_device(r3)

        m1.motion()
        self.assertEqual(r1.state, State.OCCUPIED)
        self.assertEqual(r2.state, State.VACANT)
        self.assertEqual(r3.state, State.UNKNOWN)
        m2.motion()
        self.assertEqual(r1.state, State.VACANT)
        self.assertEqual(r2.state, State.OCCUPIED)
        self.assertEqual(r3.state, State.VACANT)
        m3.motion()
        self.assertEqual(r1.state, State.VACANT)
        self.assertEqual(r2.state, State.VACANT)
        self.assertEqual(r3.state, State.OCCUPIED)
        m1.motion()
        self.assertEqual(r1.state, State.OCCUPIED)
        self.assertEqual(r2.state, State.VACANT)
        self.assertEqual(r3.state, State.OCCUPIED)
        m2.motion()
        self.assertEqual(r1.state, State.VACANT)
        self.assertEqual(r2.state, State.OCCUPIED)
        self.assertEqual(r3.state, State.VACANT)
        
        
########NEW FILE########
__FILENAME__ = scene
from mock import Mock
from unittest import TestCase

from pytomation.devices import Scene, InterfaceDevice, StateDevice, State

class SceneDeviceTests(TestCase):
    def test_instantiation(self):
        scene = Scene()
        self.assertIsNotNone(scene)
        
    def test_scene_activate(self):
        interface = Mock()
        interface.onCommand.return_value = True
        
        d1 = InterfaceDevice('d1', interface)
        d2 = InterfaceDevice('d2', interface)

        scene = Scene(
                      address='s1',
                      devices= (interface,
                                {d1: {
                                     'state': State.ON,
                                     'rate': 10,
                                     },
                                d2: {
                                     'state': (State.LEVEL, 30),
                                     'rate': 10,
                                     },
                                }),
                      update=True,
                      )
        self.assertIsNotNone(scene)
        #scene.activate()
        scene.on()
        
        #self.assertTrue(interface.update_scene.called)
        #self.assertTrue(interface.activate.called)
        
#         interface.update_scene.assert_called_with(
#                                                            's1',
#                                                           devices= {d1: {
#                                                                          'state': State.ON,
#                                                                          'rate': 10,
#                                                                          },
#                                                                     d2: {
#                                                                          'state': (State.LEVEL, 30),
#                                                                          'rate': 10,
#                                                                          },
#                                                                     },
#                                                            )

########NEW FILE########
__FILENAME__ = state
import time

from unittest import TestCase
from datetime import datetime

from pytomation.devices import StateDevice, State, Attribute, Attributes
from pytomation.interfaces import Command

class StateTests(TestCase):
    def test_instance(self):
        self.assertIsNotNone(StateDevice())

    def test_unknown_initial(self):
        self.assertEqual(StateDevice().state, State.UNKNOWN)

    def test_initial(self):
        device = StateDevice(
                        initial=State.ON
                        )
        self.assertEqual(device.state, State.ON)
        self.assertEqual(device.last_command, Command.ON)
    
    def test_initial_from_device(self):
        d1 = StateDevice(
                          )
        self.assertEqual(d1.state, State.UNKNOWN)
        d1.on()
        self.assertEqual(d1.state, State.ON)
        d2 = StateDevice(devices=d1)
        self.assertEqual(d2.state, State.ON)
    
    def test_initial_delegate(self):
        d1 = StateDevice()
        d1.on()
        d2 = StateDevice(devices=(d1),
                          initial=d1)
        self.assertEqual(d2.state, State.ON)
        
    def test_command_on(self):
        device = StateDevice()
        self.assertEqual(device.state, State.UNKNOWN)
        device.on()
        self.assertEqual(device.state, State.ON)

    def test_command_subcommand(self):
        device = StateDevice()
        self.assertEqual(device.state, State.UNKNOWN)
        device.level(80)
        self.assertEqual(device.state, (State.LEVEL, 80))
        
    def test_time_off(self):
        now = datetime.now()
        hours, mins, secs = now.timetuple()[3:6]
        secs = (secs + 2) % 60
        mins += (secs + 2) / 60
        trigger_time1 = '{h}:{m}:{s}'.format(
                                             h=hours,
                                             m=mins,
                                             s=secs,
                                                 )
        print 'Trigger Time' + trigger_time1
        secs = (secs + 2) % 60
        mins += (secs + 2) / 60
        trigger_time2 = '{h}:{m}:{s}'.format(
                                             h=hours,
                                             m=mins,
                                             s=secs,
                                                 )
        print 'Trigger Time' + trigger_time2
        device = StateDevice(
                              time={
                                    
                                    Attribute.COMMAND: Command.OFF,
                                    Attribute.TIME: (trigger_time1, trigger_time2),
                                    }
                              )
        self.assertEqual(device.state, State.UNKNOWN)
        time.sleep(3)
        print datetime.now()
        self.assertEqual(device.state, State.OFF)
        device.on()
        time.sleep(3)
        print datetime.now()
        print device._times
        self.assertEqual(device.state, State.OFF)
        
    def test_time_cron_off(self):
        now = datetime.now()
        hours, mins, secs = now.timetuple()[3:6]
        secs = (secs + 2) % 60
        mins += (secs + 2) / 60
        ctime = (secs, mins, hours)
        
        s = StateDevice(
                       time={
                             Attribute.COMMAND: Command.OFF,
                             Attribute.TIME: ctime,
                             }
                       )
        s.on()
        self.assertEqual(s.state, Command.ON)
        time.sleep(3)
        self.assertEqual(s.state, Command.OFF)

    def test_binding(self):
        d1 = StateDevice()
        d1.off()
        self.assertEqual(d1.state, State.OFF)
        d2 = StateDevice(devices=d1)
        self.assertEqual(d2.state, State.OFF)
        d1.on()
        self.assertEqual(d2.state, State.ON)
        
    def test_binding_default(self):
        d1 = StateDevice()
        d1.off()
        d2 = StateDevice(d1)
        self.assertEqual(d2.state, State.OFF)
        d1.on()
        self.assertEqual(d2.state, State.ON)

        
    def test_map(self):
        d1 = StateDevice()
        d2 = StateDevice()
        d3 = StateDevice(devices=(d1, d2),
                          mapped={Attribute.COMMAND: Command.ON,
                                   Attribute.MAPPED: Command.OFF,
                                   Attribute.SOURCE: d2}
                          )
        self.assertEqual(d3.state, State.UNKNOWN)
        d1.on()
        self.assertEqual(d3.state, State.ON)
        d2.on()
        self.assertEqual(d3.state, State.OFF)
        
    def test_delay(self):
        d1 = StateDevice()
        d2 = StateDevice(devices=d1,
                          delay={Attribute.COMMAND: Command.OFF,
                                 Attribute.MAPPED: (Command.LEVEL, 80),
                                 Attribute.SOURCE: d1,
                                 Attribute.SECS: 2,
                                 })
        self.assertEqual(d2.state, State.UNKNOWN)
        d1.on()
        self.assertEqual(d2.state, State.ON)
        d1.off()
        self.assertEqual(d2.state, State.ON)
        time.sleep(3)
#        time.sleep(2000)
        self.assertEqual(d2.state, (State.LEVEL, 80))
        
    def test_delay_zero_secs(self):
        d1 = StateDevice()
        d2 = StateDevice()
        d3 = StateDevice(
                         devices=(d1, d2),
                         delay=({
                                Attribute.COMMAND: Command.OFF,
                                Attribute.SECS: 2
                                },
                                {
                                 Attribute.COMMAND: Command.OFF,
                                 Attribute.SECS: 0,
                                 Attribute.SOURCE: d2,
                                 }
                                ),
                         initial=State.ON,
                         )    
        self.assertEqual(d3.state, State.ON)
        d1.off()
        self.assertEqual(d3.state, State.ON)
        time.sleep(3)
        self.assertEqual(d3.state, State.OFF)
        d3.on()
        self.assertEqual(d3.state, State.ON)
        d2.off()
        self.assertEqual(d3.state, State.OFF)
        
        
    def test_delay_no_retrigger(self):
        d1 = StateDevice(trigger={
                                 Attribute.COMMAND: Command.ON,
                                 Attribute.MAPPED: Command.OFF,
                                 Attribute.SECS: 3},
                          delay={
                                 Attribute.COMMAND: Command.OFF,
                                 Attribute.SECS: 3},
                          )
        d1.on()
        self.assertEqual(d1.state, State.ON)
        d1.off()
        self.assertEqual(d1.state, State.ON)
        time.sleep(2)
        d1.off()
        time.sleep(1)
        self.assertEqual(d1.state, State.OFF)
        
                
    def test_delay_single(self):
        d1 = StateDevice(
                          delay={Attribute.COMMAND: Command.OFF,
                                 Attribute.SECS: 2,
                                 }
                          )
        self.assertEqual(d1.state, State.UNKNOWN)
        d1.on()
        self.assertEqual(d1.state, State.ON)
        d1.off()
        self.assertEqual(d1.state, State.ON)
        time.sleep(3)
#        time.sleep(20000)
        self.assertEqual(d1.state, State.OFF)

    def test_delay_multiple(self):
        d1 = StateDevice()
        d2 = StateDevice()
        d3 = StateDevice(
                          devices=(d1, d2),
                          delay=(
                                     {Attribute.COMMAND: (Command.OFF),
                                     Attribute.SOURCE: (d1),
                                     Attribute.SECS: 2,
                                     },
                                     {Attribute.COMMAND: Command.OFF,
                                     Attribute.SOURCE: d2,
                                     Attribute.SECS: 4,
                                     },
                                 )
                          )
        self.assertEqual(d3.state, State.UNKNOWN)
        d3.on()
        self.assertEqual(d3.state, State.ON)
        d1.off()
        self.assertEqual(d3.state, State.ON)
        time.sleep(3)
        self.assertEqual(d3.state, State.OFF)
        
        #d2
        d3.on()
        self.assertEqual(d3.state, State.ON)
        d2.off()
        self.assertEqual(d3.state, State.ON)
        time.sleep(3)
        self.assertEqual(d3.state, State.ON)
        time.sleep(1)
        self.assertEqual(d3.state, State.OFF)
        
    def test_delay_priority(self):
        d1 = StateDevice()
        d2 = StateDevice()
        d3 = StateDevice(
                         devices=(d1,d2),
                         delay=({
                                Attribute.COMMAND: Command.OFF,
                                Attribute.SOURCE: d1,
                                Attribute.SECS: 4,
                                },
                                {
                                 Attribute.COMMAND: Command.OFF,
                                 Attribute.SECS: 2
                                 },
                                ),
                         initial=State.ON,
                         )
        self.assertEqual(d3.state, State.ON)
        d1.off()
        self.assertEqual(d3.state, State.ON)
        time.sleep(2)
        self.assertEqual(d3.state, State.ON)
        time.sleep(2)
        self.assertEqual(d3.state, State.OFF)
        
        
    def test_idle_time_property(self):
        d = StateDevice()
        d.on()
        time.sleep(2)
        self.assertTrue(d.idle_time >= 2)
        
    def test_idle_timer(self):
        s1 = StateDevice()
        s2 = StateDevice(devices=s1,
                         idle={
                               Attribute.MAPPED: State.OFF,
                               Attribute.SECS: 2,
                               }
                         )
        s1.on()
        self.assertEqual(s2.state, State.ON)
        time.sleep(3)
        self.assertEqual(s2.state, State.OFF)
        s1.on()
        self.assertEqual(s2.state, State.ON)

    def test_idle_timer_then_trigger(self):
        s1 = StateDevice()
        s2 = StateDevice(devices=s1,
                         trigger={
                                Attribute.COMMAND: State.ON,
                                Attribute.MAPPED: State.OFF,
                                Attribute.SECS: 4,
                                },
                         idle={
                               Attribute.MAPPED: State.UNKNOWN,
                               Attribute.SECS: 2,
                               }
                         )
        s1.on()
        self.assertEqual(s2.state, State.ON)
        time.sleep(3)
        self.assertEqual(s2.state, State.UNKNOWN)
        time.sleep(5)
        self.assertEqual(s2.state, State.OFF)
#         s1.on()
#         self.assertEqual(s2.state, State.ON)


        
    def test_idle_source(self):
        s1 = StateDevice()
        s2 = StateDevice()
        s1.off()
        s2.off()
        s3 = StateDevice(devices=(s1, s2),
                          idle={
                                Attribute.MAPPED: State.OFF,
                                Attribute.SECS: 2,
                                Attribute.SOURCE: s2
                                }
                          )
        s1.on()
        self.assertEqual(s3.state, State.ON)
        time.sleep(3)
        self.assertEqual(s3.state, State.ON)
        s2.on()
        self.assertEqual(s3.state, State.ON)
        time.sleep(3)
        self.assertEqual(s3.state, State.OFF)
        

    def test_ignore_state(self):
        s1 = StateDevice()
        s2 = StateDevice(devices = s1,
                          ignore={
                                  Attribute.COMMAND: Command.ON,
                                  Attribute.SOURCE: s1,
                                  },
                          )
        s1.on()
        self.assertEqual(s2.state, State.UNKNOWN)
        s1.off()
        self.assertEqual(s2.state, State.OFF)
        s1.on()
        self.assertEqual(s2.state, State.OFF)

    def test_ignore_multiple_state(self):
        s1 = StateDevice()
        s2 = StateDevice(devices = s1,
                          ignore=({
                                  Attribute.COMMAND: Command.ON,
                                  },
                                  {
                                   Attribute.COMMAND: Command.OFF,
                                   }
                                  ),
                          )
        self.assertEqual(s2.state, State.UNKNOWN)
        s1.on()
        self.assertEqual(s2.state, State.UNKNOWN)
        s1.off()
        self.assertEqual(s2.state, State.UNKNOWN)
        s1.on()
        self.assertEqual(s2.state, State.UNKNOWN)

    def test_ignore_multiples_state(self):
        s1 = StateDevice()
        s2 = StateDevice(devices = s1,
                          ignore={
                                  Attribute.COMMAND: (Command.ON, Command.OFF)
                                  },
                          )
        self.assertEqual(s2.state, State.UNKNOWN)
        s1.on()
        self.assertEqual(s2.state, State.UNKNOWN)
        s1.off()
        self.assertEqual(s2.state, State.UNKNOWN)
        s1.on()
        self.assertEqual(s2.state, State.UNKNOWN)

    def test_ignore_device(self):
        s1 = StateDevice()
        s2 = StateDevice(devices=s1,
                         ignore={
                                 Attribute.SOURCE: s1
                                 }
                         )
        self.assertEqual(s2.state, State.UNKNOWN)
        s1.on()
        self.assertEqual(s2.state, State.UNKNOWN)
        

    def test_last_command(self):
        s1 = StateDevice()
        s1.on()
        self.assertEqual(s1.state, State.ON)
        s1.off()
        self.assertEqual(s1.state, State.OFF)
        self.assertEqual(s1.last_command, Command.OFF)

    def test_previous_state_command(self):
        s1 = StateDevice()
        s1.on()
        self.assertEqual(s1.state, State.ON)
        s1.off()
        self.assertEqual(s1.state, State.OFF)
        s1.previous()
        self.assertEqual(s1.state, State.ON)

    def test_previous_state_twice_command(self):
        s1 = StateDevice()
        s2 = StateDevice(devices=s1)
        s1.off()
        self.assertEqual(s1.state, State.OFF)
        s1.on()
        self.assertEqual(s1.state, State.ON)
        s1.on()
        self.assertEqual(s1.state, State.ON)
        s1.previous()
        self.assertEqual(s1.state, State.OFF)
        
        
        
        
    def test_toggle_state(self):
        s1 = StateDevice()
        s1.on()
        self.assertEqual(s1.state, State.ON)
        s1.toggle()
        self.assertEqual(s1.state, State.OFF)
        s1.toggle()
        self.assertEqual(s1.state, State.ON)
        
    def test_trigger(self):
        s1 = StateDevice(
                          trigger={
                                   Attribute.COMMAND: Command.ON,
                                   Attribute.MAPPED: Command.OFF,
                                   Attribute.SECS: 2
                                   }
                          )
        s1.on();
        self.assertEqual(s1.state, State.ON)
        time.sleep(3)
        self.assertEqual(s1.state, State.OFF)

    def test_trigger_time_range(self):
        (s_h, s_m, s_s) = datetime.now().timetuple()[3:6]
        e_h = s_h
        e_m = s_m
        e_s = s_s + 2
        s = StateDevice()
        s2 = StateDevice(devices=s,
                         trigger={
                                Attribute.COMMAND: Command.ON,
                                Attribute.MAPPED: Command.OFF,
                                Attribute.SECS: 1,
                                 Attribute.START: '{h}:{m}:{s}'.format(
                                                                      h=s_h,
                                                                      m=s_m,
                                                                      s=s_s,
                                                                      ),
                                 Attribute.END: '{h}:{m}:{s}'.format(
                                                                      h=e_h,
                                                                      m=e_m,
                                                                      s=e_s,
                                                                      ),
                                 },
                         
                         )
        self.assertEqual(s2.state, State.UNKNOWN)
        s.on()
        self.assertEqual(s2.state, State.ON)
        time.sleep(3)
        self.assertEqual(s2.state, State.OFF)
        ##
        time.sleep(2)
        s.on()
        time.sleep(3)
        self.assertEqual(s2.state, State.ON)
      
    def test_initial_attribute(self):
        d = StateDevice(
                         name='pie'
                         )
        self.assertEqual(d.name, 'pie')
        
    def test_delay_multiple_source(self):
        d1 = StateDevice()
        d2 = StateDevice()
        d3 = StateDevice()
        d4 = StateDevice(
                          devices=(d1, d2, d3),
                          delay={
                                 Attribute.COMMAND: Command.OFF,
                                 Attribute.SOURCE: (d1, d2),
                                 Attribute.SECS: 2,
                                },
                          )
        d1.on()
        self.assertEqual(d4.state, State.ON)
        d1.off()
        self.assertEqual(d4.state, State.ON)
        time.sleep(3)
        self.assertEqual(d4.state, State.OFF)

        d3.on()
        self.assertEqual(d4.state, State.ON)
        d3.off()
        self.assertEqual(d4.state, State.OFF)
        
    def test_override_default_maps(self):
        d = StateDevice(
                         mapped={
                                 Attribute.COMMAND: Command.ON,
                                 Attribute.MAPPED: Command.OFF,
                                 }
                         )
        d.on()
        self.assertEqual(d.state, State.OFF)
        
        
    def test_map_delay(self):
        d = StateDevice(
                         mapped={
                                 Attribute.COMMAND: Command.ON,
                                 Attribute.MAPPED: Command.OFF,
                                 Attribute.SECS: 2,
                                 },
                         )
        self.assertEqual(d.state, State.UNKNOWN)
        d.on()
        self.assertEqual(d.state, State.UNKNOWN)
        time.sleep(3)
        self.assertEqual(d.state, Command.OFF)
        
    def test_map_sources(self):
        d1 = StateDevice()
        d2 = StateDevice()
        d3 = StateDevice()
        d4 = StateDevice(
                          devices=(d1, d2, d3),
                          mapped={
                                  Attribute.COMMAND: Command.ON,
                                  Attribute.SOURCE: (d1, d2),
                                  Attribute.MAPPED: Command.OFF,
                                  }
                          )
        self.assertEqual(d4.state, State.UNKNOWN)
        d3.on()
        self.assertEqual(d4.state, State.ON)
        d2.on()
        self.assertEqual(d4.state, State.OFF)
        
    def test_delay_cancel_on_other_state(self):
        d1 = StateDevice()
        d2 = StateDevice(devices=d1,
                         initial=State.OFF,
                         delay={
                                Attribute.COMMAND: Command.OFF,
                                Attribute.SECS: 2,
                                },
                         )
        self.assertEqual(d2.state, State.UNKNOWN)
        d1.on()
        self.assertEqual(d2.state, State.ON)
        d1.off()
        self.assertEqual(d2.state, State.ON)
        d1.on()
        self.assertEqual(d2.state, State.ON)
        time.sleep(3)
        self.assertEqual(d2.state, State.ON)
        
        
    def test_manual_state(self):
        d1 = StateDevice()
        d2 = StateDevice(devices=d1,
                         delay={
                                Attribute.COMMAND: Command.OFF,
                                Attribute.SECS: 2
                                },
                         )
        d2.on()
        self.assertEqual(d2.state, State.ON)
        d2.manual()
        d2.off()
        self.assertEqual(d2.state, State.OFF)
        d2.on()
        d2.automatic()
        d2.off()
        self.assertEqual(d2.state, State.ON)
        time.sleep(3)
        self.assertEqual(d2.state, State.OFF)
                
    def test_changes_only(self):
        d1 = StateDevice()
        d2 = StateDevice(devices=d1,
                         changes_only=True,
                         name='tested')
        d3 = StateDevice(devices=d2)
        d1.off()
        self.assertEqual(d1.state, State.OFF)
        self.assertEqual(d2.state, State.OFF)
        self.assertEqual(d3.state, State.OFF)
        d1.on()
        self.assertEqual(d1.state, State.ON)
        self.assertEqual(d2.state, State.ON)
        self.assertEqual(d3.state, State.ON)
        d3.off()
        self.assertEqual(d3.state, State.OFF)
        # set on again, this time no delegation
        d1.on()
        self.assertEqual(d3.state, State.OFF)

        # after x amount of time still prevent dupes
        time.sleep(3)
        d1.on()
        self.assertEqual(d3.state, State.OFF)
        
    def test_retrigger_delay(self):
        d1 = StateDevice()
        d2 = StateDevice(devices=d1,
                         retrigger_delay={
                                   Attribute.SECS: 2
                                   },
                         name='tested')
        d3 = StateDevice(devices=d2)
        d1.off()
        self.assertEqual(d1.state, State.OFF)
        self.assertEqual(d2.state, State.OFF)
        self.assertEqual(d3.state, State.OFF)
        d1.on()
        self.assertEqual(d1.state, State.ON)
        self.assertEqual(d2.state, State.ON)
        self.assertEqual(d3.state, State.ON)
        d3.off()
        self.assertEqual(d3.state, State.OFF)
        # set on again, this time no delegation
        d1.on()
        self.assertEqual(d3.state, State.OFF)
        
        # after x amount of time allow dupes
        time.sleep(3)
        d1.on()
        self.assertEqual(d3.state, State.ON)
        
    def test_loop_prevention(self):
        s1 = StateDevice()
        s2 = StateDevice()
        s1.devices(s2)
        s2.devices(s1)
        s1.on()
        pass
    
    def test_state_remove_device(self):
        s1 = StateDevice()
        s2 = StateDevice(devices=s1)
        s1.on()
        self.assertEqual(s2.state, State.ON)
        s2.off()
        self.assertEqual(s2.state, State.OFF)        
        r=s2.remove_device(s1)
        self.assertTrue(r)
        self.assertEqual(s2.state, State.OFF)        
        s1.on()
        self.assertEqual(s2.state, State.OFF)     
        # remove again and not error
        r = s2.remove_device(s1)
        self.assertFalse(r)
        
    def test_state_ignore_range(self):
        (s_h, s_m, s_s) = datetime.now().timetuple()[3:6]
        e_h = s_h
        e_m = s_m
        e_s = s_s + 2
        s = StateDevice()
        s2 = StateDevice(devices=s,
                         ignore={
                                 Attribute.SOURCE: s,
                                 Attribute.START: '{h}:{m}:{s}'.format(
                                                                      h=s_h,
                                                                      m=s_m,
                                                                      s=s_s,
                                                                      ),
                                 Attribute.END: '{h}:{m}:{s}'.format(
                                                                      h=e_h,
                                                                      m=e_m,
                                                                      s=e_s,
                                                                      ),
                                 },
                         
                         )
        self.assertEqual(s2.state, State.UNKNOWN)
        s.on()
        self.assertEqual(s2.state, State.UNKNOWN)
        time.sleep(3)
        s.on()
        self.assertEqual(s2.state, State.ON)
        
    def test_ignore_multi_command(self):
        s1 = StateDevice()
        s2 = StateDevice(devices=s1,
                         ignore={
                                 Attribute.COMMAND: (Command.ON, Command.OFF,)
                                 },
                         )
        self.assertEqual(s2.state, State.UNKNOWN)
        s1.on()
        self.assertEqual(s2.state, State.UNKNOWN)
        s1.off()
        self.assertEqual(s2.state, State.UNKNOWN)
        
        
    def test_status_command(self):
        s = StateDevice()
        s.status()
        self.assertTrue(True)
        
    def test_invalid_constructor_keyword(self):
        s1 = StateDevice()
        s2 = StateDevice(device=s1) #invalid keyword device
        #If I had implemented a DI framework I could automatically test for an error debug statement.
        # alas I do not.  Need to manually verify this one
        self.assertTrue(True)
        
#     def test_invert_commands(self):
#         s = StateDevice(invert=True)
#         s.on()
#         self.assertEqual(s.state, State.OFF)
#         s.off()
#         self.assertEqual(s.state, State.ON)
#         s.invert(False)
#         s.on()
#         self.assertEqual(s.state, State.ON)

    def test_time_range_invalid(self):
        try:
            s1 = StateDevice(
                             ignore={
                                     Attribute.COMMAND: Command.ON,
                                     Attribute.START: '10:56 am',
                                     Attribute.END: '11.02 am',
                                     }
                             )
            self.assertTrue(False)
        except AssertionError, ex:
            raise ex
        except Exception, ex:
            pass
        

    def test_restriction(self):
        sr = StateDevice()
        s1 = StateDevice()
        s2 = StateDevice(
                         devices=(s1),
                         restriction={
                                      Attribute.SOURCE: sr,
                                      Attribute.STATE: State.ON,
                                      }
                                      
                         )
        self.assertEqual(State.UNKNOWN, s2.state)
        s1.on()
        self.assertEqual(State.ON, s2.state)
        s1.off()
        self.assertEqual(State.OFF, s2.state)
        # Restrict
        sr.on()
        s1.on()
        self.assertEqual(State.OFF, s2.state)
        s1.off()
        sr.off()
        s1.on()
        self.assertEqual(State.ON, s2.state)
        
    def test_restriction_specific_state(self):
        # Dark = ON
        # light = OFF
        sr = StateDevice()
        s2 = StateDevice(
                         devices=(sr),
                         restriction={
                                      Attribute.SOURCE: sr,
                                      Attribute.STATE: State.OFF,
                                      Attribute.TARGET: Command.ON,
                                      }
                         )
                                      
        # Restrict
        sr.on()
        self.assertEqual(State.ON, s2.state)
        sr.off()
        self.assertEqual(State.OFF, s2.state)        
        
        

########NEW FILE########
__FILENAME__ = thermostat
from unittest import TestCase

from mock import Mock
from pytomation.interfaces import HAInterface
from pytomation.devices import Thermostat, State
from pytomation.interfaces.common import *


class ThermostatTests(TestCase):
    def setUp(self):
        self.interface = Mock()
        self.device = Thermostat('192.168.1.3', self.interface)

    def test_instantiation(self):
        self.assertIsNotNone(self.device)

    def test_cool(self):
        self.assertEqual(self.device.state, State.UNKNOWN)
        self.device.cool()
        self.assertEqual(self.device.state, State.COOL)
        self.interface.cool.assert_called_with('192.168.1.3')

    def test_heat(self):
        self.assertEqual(self.device.state, State.UNKNOWN)
        self.device.heat()
        self.assertEqual(self.device.state, State.HEAT)
        self.interface.heat.assert_called_with('192.168.1.3')

    def test_off(self):
        self.assertEqual(self.device.state, State.UNKNOWN)
        self.device.off()
        self.assertEqual(self.device.state, State.OFF)
        self.interface.off.assert_called_with('192.168.1.3')

    def test_level(self):
        self.assertEqual(self.device.state, State.UNKNOWN)
        self.device.level(72)
        self.assertEqual(self.device.state, (State.LEVEL, 72))
        self.interface.level.assert_called_with('192.168.1.3', 72)
        
    def test_circulate(self):
        self.assertEqual(self.device.state, State.UNKNOWN)
        self.device.circulate()
        self.assertEqual(self.device.state, State.CIRCULATE)
        self.interface.circulate.assert_called_with('192.168.1.3')
        
    def test_automatic_mode_for_device_that_does_not(self):
        #Oddly enough the homewerks thermostat doesnt have an auto mode
        self.interface.automatic = None
        self.device.command((Command.LEVEL, 72))
        self.device.command(Command.AUTOMATIC)
        self.device.command(command=(Command.LEVEL, 76), source=self.interface, address='192.168.1.3')
        self.interface.cool.assert_called_with('192.168.1.3')
        self.interface.level.assert_called_with('192.168.1.3', 72)
        assert not self.interface.heat.called
        self.interface.heat.reset_mock()
        self.interface.level.reset_mock()
        self.device.command(command=(Command.LEVEL, 54), source=self.interface, address='192.168.1.3')
        self.interface.heat.assert_called_with('192.168.1.3')
        assert not self.interface.level.called
        # Test that it does not repeat mode setting unnecessarily
        self.interface.heat.reset_mock()
        self.interface.level.reset_mock()
        self.device.command(command=(Command.LEVEL, 58), source=self.interface, address='192.168.1.3')
        assert not self.interface.heat.called
        assert not self.interface.level.called
        self.interface.heat.reset_mock()
        self.interface.cool.reset_mock()
        self.interface.level.reset_mock()
        self.device.command(command=(Command.LEVEL, 98), source=self.interface, address='192.168.1.3')
        self.interface.cool.assert_called_with('192.168.1.3')
        assert not self.interface.heat.called
        assert not self.interface.level.called
        # Test the delta setting
        self.device.automatic_delta(1)
        self.interface.heat.reset_mock()
        self.interface.cool.reset_mock()
        self.interface.level.reset_mock()
        self.device.command(command=(Command.LEVEL, 71), source=self.interface, address='192.168.1.3')
        assert not self.interface.heat.called
        assert not self.interface.level.called
        self.device.command(command=(Command.LEVEL, 70), source=self.interface, address='192.168.1.3')
        self.interface.heat.assert_called_with('192.168.1.3')
        
    def test_automatic_delta(self):
        self.device = Thermostat(
                       address='192.168.1.3',
                       devices=self.interface,
                       automatic_delta=2
                       )
        self.interface.automatic = None
        self.device.command((Command.LEVEL, 72))
        self.interface.level.assert_called_with('192.168.1.3', 72)
        self.interface.level.reset_mock()
        self.device.command(Command.AUTOMATIC)
        self.device.command(command=(Command.LEVEL, 76), source=self.interface, address='192.168.1.3')
        self.interface.cool.assert_called_with('192.168.1.3')
        assert not self.interface.heat.called
        self.interface.heat.reset_mock()
        self.interface.cool.reset_mock()
        self.interface.level.reset_mock()
        self.device.command(command=(Command.LEVEL, 71), source=self.interface, address='192.168.1.3')
        assert not self.interface.heat.called
        
        
    def test_automatic_delta_setpoint_switchover(self):
        self.device = Thermostat(
                       address='a',
                       devices=self.interface,
                       automatic_delta=2
                       )
        self.interface.automatic = None
        self.device.command(command=(Command.LEVEL, 76), source=self.interface, address='a')
        self.device.command((Command.LEVEL, 70))
        # we are not in automatic mode yet
        assert not self.interface.cool.called
        self.device.command(Command.AUTOMATIC)
        self.device.command(command=(Command.LEVEL, 76), source=self.interface, address='a')
        self.interface.cool.assert_called_with('a')
        self.device.command(command=(Command.LEVEL, 71), source=self.interface, address='a')
        self.interface.heat.reset_mock()
        self.interface.cool.reset_mock()
        self.interface.level.reset_mock()
        # reset set point within delta
        self.device.command((Command.LEVEL, 72))
        assert not self.interface.heat.called
        self.device.command(command=(Command.LEVEL, 69), source=self.interface, address='a')
        self.interface.heat.assert_called_with('a')

    def test_hold(self):
        assert not self.interface.hold.called
        self.device.command(Command.HOLD)
        self.interface.hold.assert_called_with('192.168.1.3')
        
    def test_away_mode(self):
        self.device = Thermostat(
                       address='a',
                       devices=self.interface,
                       automatic_delta=2,
                       away_delta=10,
                       )
        self.interface.automatic = None
        self.device.command((Command.LEVEL, 72))
        self.device.command(Command.AUTOMATIC)
        self.device.command(Command.VACATE)
#        time.sleep(2)
        self.interface.vacate.assert_called_with('a')
        self.device.command(command=(Command.LEVEL, 76), source=self.interface, address='a')
        assert not self.interface.cool.called
        self.device.command(command=(Command.LEVEL, 83), source=self.interface, address='a')
        self.interface.cool.assert_called_with('a')

        self.device.command(command=(Command.LEVEL, 67), source=self.interface, address='a')
        assert not self.interface.heat.called
        self.device.command(command=(Command.LEVEL, 61), source=self.interface, address='a')
        self.interface.heat.assert_called_with('a')

                
        self.interface.heat.reset_mock()
        self.interface.cool.reset_mock()
        self.device.command(command=(Command.LEVEL, 68), source=self.interface, address='a')
        assert not self.interface.heat.called
        self.device.command(Command.OCCUPY)
        self.device.command(command=(Command.LEVEL, 68), source=self.interface, address='a')
        self.interface.occupy.assert_called_with('a')
        self.interface.heat.assert_called_with('a')

        
        
        
        
        

########NEW FILE########
__FILENAME__ = xmpp_client
from unittest import TestCase, main
from mock import Mock

from pytomation.devices import State, XMPP_Client, StateDevice
from pytomation.interfaces import Command

class XMPP_ClientTests(TestCase):
    def setUp(self):
        self.xmpp = XMPP_Client(id='pytomation@sharpee.com', password='password', server='talk.google.com', port=5222)
    
    def test_instantiation(self):
        self.assertIsInstance(self.xmpp, XMPP_Client)

    def test_send(self):
        self.xmpp.command((Command.MESSAGE, 'jason@sharpee.com', 'This is the test'))

########NEW FILE########
__FILENAME__ = experiment-threading
"""
from Queue import Queue
from threading import Thread

num_worker_threads = 5
source = [12, 34, 55, 234,234,344,4323,43,234,234,2,234,234,23,23,23,423,5,55,2,22,3,34,4,4,2,3,42,34,]

def worker(id):
    while True:
	item = ""
	for i in range(3):
		print "id" + str(id) + " i->" + str(i)
		pass
	try:
	        item = q.get(True)
	except:
		pass
#        do_work(item)
	print "ThreadID #" + str(id) + " Item->" + str(item)
        q.task_done()

q = Queue()
for i in range(num_worker_threads):
     t = Thread(target=worker, args=(i, ))
     print "Thread started" + str(i)
     t.daemon = True
     t.start()

for item in source:
    q.put(item)

q.join()       # block until all tasks are done

"""
########NEW FILE########
__FILENAME__ = harmony_hub
import time

from unittest import TestCase

from pytomation.interfaces import HarmonyHub

class HarmonyHubTests(TestCase):
    def setUp(self):
        self.interface = HarmonyHub(address='192.168.13.134', 
                                    port='5222',
                                    user='jason@sharpee.com',
                                    password='password'
                                    )

    def test_instantiation(self):
        self.assertIsInstance(self.interface, HarmonyHub)
    
    def test_on(self):
        result = self.interface.on('Watch Roku')
        self.assertEqual(result, None)
        
    def test_off(self):
        result = self.interface.off('Doesnt matter')
        
    def test_get_config(self):
        print str(self.interface.get_config())
        
########NEW FILE########
__FILENAME__ = ha_interface

from unittest import TestCase, main

from pytomation.interfaces import HAInterface
from pytomation.devices import StateDevice, InterfaceDevice, State
from mock import Mock

class HAInterfaceTests(TestCase):
    def setUp(self):
        di = Mock()
        self.interface = HAInterface(di)
        
    def test_instances(self):
        prev = len(self.interface.instances)
        interface = HAInterface(Mock())
        self.assertTrue(len(interface.instances) > prev)
        
    def test_update_status(self):
        device = Mock()
        device.address.return_value = 'a1'
        self.interface.onCommand(device=device)
#        self.interface.status = Mock()
#        self.interface.status.return_value = lambda x: x
        self.interface.update_status()
#        self.interface.status.assert_called_with(address='a1')
        
    def test_on_state(self):
        s = InterfaceDevice(address='D3', devices=self.interface)
        s.off()
        self.assertEqual(s.state, State.OFF)
        self.interface._onState(State.ON, 'D3')
        self.assertEqual(s.state, State.ON)
        
        
########NEW FILE########
__FILENAME__ = http
import os, time

from unittest import TestCase

from pytomation.interfaces import HTTP

class HTTPTests(TestCase):
    def setUp(self):
        self.interface = HTTP
        self._protocol = 'http'
        self._host = "www.google.com"
        
        self.interface = HTTP(protocol=self._protocol, host=self._host)
            
    def test_instance(self):
        self.assertIsNotNone(self.interface)
        
    def test_read(self):
        response = self.interface.read()
        self.assertIn("google", response)
        
    def test_write(self):
        response = self.interface.write("", None, "POST")
        self.assertIn("google", response)
        
    def test_write_tuple(self):
        command = 'path', 'data',
        self.interface.write(command)

########NEW FILE########
__FILENAME__ = hw_thermostat
import time

from unittest import TestCase

from tests.common import MockInterface, Mock_Interface
from pytomation.interfaces import HTTP, HW_Thermostat, HTTP

class HW_ThermostatInterfaceTests(TestCase):
    def setUp(self):
        self.host = '192.168.13.211'
#        self.i = HTTP('http', self.host)
        self.i = Mock_Interface()
        self.interface = HW_Thermostat(self.i, self.host)

    def test_instantiation(self):
        self.assertIsInstance(self.interface, HW_Thermostat)
        
    def test_circulate(self):
        self.interface.off(self.host)
        time.sleep(2)
#        self.interface.still(self.host)
        self.interface.circulate(self.host)
        time.sleep(2)
    
    def test_setpoint(self):
        #no prior mode, then default to heat
        self.interface.level(address=self.host, level=72)
        time.sleep(2)
        self.assertIn(('tstat', '{"t_heat": 72}',), self.i.query_write_data())
        self.i.clear_write_data()
        self.interface.cool()
        time.sleep(2)
        self.assertIn(('tstat', '{"tmode": 2, "t_cool": 72}', ), self.i.query_write_data())
        
    def test_cool(self):
        self.interface.cool()
        time.sleep(2)
        self.assertIn(('tstat', '{"tmode": 2}', ), self.i.query_write_data())
        
########NEW FILE########
__FILENAME__ = insteon
import select
import time

from binascii import unhexlify
from unittest import TestCase, main
from mock import Mock

from tests.common import MockInterface, Mock_Interface, Command
from pytomation.interfaces import InsteonPLM, Serial, HACommand, \
                                    TCP, Conversions
from pytomation.devices import Door, Light, State

class InsteonInterfaceTests(TestCase):
    useMock = True

    def setUp(self):
        self.ms = Mock_Interface()
        self.insteon = InsteonPLM(self.ms)

# If we are running live, the insteon interface doesnt like to be bombarded with requests
#            time.sleep(3)
#            self.serial = Serial('/dev/ttyUSB0', 4800)
#            self.insteon = InsteonPLM(self.serial)
#            self.tcp = TCP('192.168.13.146', 9761)
#            self.insteon = InsteonPLM2(self.tcp)

        #self.insteon.start()

    def tearDown(self):
        self.insteon.shutdown()
        self.serial = None
        try:
            self.tcp.shutdown()
            self.tcp = None
        except:
            pass

    def test_instantiation(self):
        self.assertIsNotNone(self.insteon,
                             'Insteon interface could not be instantiated')

    def test_device_on(self):
        """
        Transmit>
        0000   02 62 19 05 7B 0F 11 FF    .b..{...
        <  0000   02 62 19 05 7B 0F 11 FF 06    .b..{....
        <  0000   02 50 19 05 7B 16 F9 EC 2B 11 FF    .P..{...+..
        """
#        self.ms.add_response({Conversions.hex_to_ascii('026219057B0F11FF'):
#                              Conversions.hex_to_ascii('026219057B0F11FF06') + \
#                              Conversions.hex_to_ascii('025019057B16F9EC2B11FF')})
        response = self.insteon.on('19.05.7b')
        self.assertIn(Conversions.hex_to_ascii('026219057B0F11FF'), self.ms.query_write_data())
        self.ms.put_read_data(Conversions.hex_to_ascii('026219057B0F11FF06'))
        self.ms.put_read_data(Conversions.hex_to_ascii('025019057B16F9EC2B11FF'))
        time.sleep(2)
        self.assertEqual(response, True)
        
    def test_insteon_level2(self):
        self.ms.disabled = False
        
        self.insteon.level('12.20.B0', 50)
        #todo: figure out how to really deal with this race condition
        time.sleep(3)
        self.assertIn(unhexlify('02621220b00f117f'), self.ms.query_write_data())
#        self.ms.write.assert_called_with(unhexlify('02621220b00f117f'))

    def test_insteon_receive_status(self):
        """
[2013/10/09 19:56:54] [DEBUG] [InsteonPLM] Receive< 0000   02 50 23 D2 BE 00 00 01 CB 11 00    .P#........
d395e51a11bb096e20f9ae84b47f8884

[2013/10/09 19:56:54] [WARNING] [InsteonPLM] Unhandled packet (couldn't find any pending command to deal with it)
[2013/10/09 19:56:54] [WARNING] [InsteonPLM] This could be a status message from a broadcast
[2013/10/09 19:56:54] [DEBUG] [InsteonPLM] HandleStandDirect
[2013/10/09 19:56:54] [DEBUG] [InsteonPLM] Running status request:False:True:True:..........
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Command: 23.D2.BE 19 00
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Queued bff1ddfd362ac6ef71555d959edbb90a
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Transmit>026223d2be0f1900
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] TransmitResult>8
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Receive< 0000   02 50 23 D2 BE 22 FF 5B 41 11 01    .P#..".[A..
4996cf7dd3a4b4722f120dc9c0fe5b17

[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] ValidResponseCheck: 0000   53 44 31 39                SD19

[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] ValidResponseCheck2: {'callBack': <bound method InsteonPLM._handle_StandardDirect_LightSta$
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] ValidResponseCheck3: ['SD19']
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Valid Insteon Command COde: SD11
[2013/10/09 19:56:55] [WARNING] [InsteonPLM] Unhandled packet (couldn't find any pending command to deal with it)
[2013/10/09 19:56:55] [WARNING] [InsteonPLM] This could be a status message from a broadcast
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] HandleStandDirect
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Setting status for:23.D2.BE:17:1..........
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Received Command:23.D2.BE:on
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Delegates for Command: []
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Devices for Command: []
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Received Command:23.D2.BE:on
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Delegates for Command: []
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Devices for Command: []
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Received a Modem NAK! Resending command, loop time 0.400000
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Queued bff1ddfd362ac6ef71555d959edbb90a
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Received a Modem NAK! Resending command, loop time 0.600000
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Transmit>026223d2be0f1900
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] TransmitResult>8
[2013/10/09 19:56:55] [DEBUG] [InsteonPLM] Receive< 0000   02 50 23 D2 BE 11 01 01 CB 06 00    .P#........
0e3a2974df58ef76268f23a48ec650a9

        """
        global logging_default_level
        ## Default logging level
        #logging_default_level = "DEBUG"
        self._result = False
        self.insteon.onCommand(self._insteon_receive_status_callback, '23.D2.BE')
        self.ms.put_read_data(Conversions.hex_to_ascii('025023D2BE000001CB1100'))
        time.sleep(1)
        # Transmits: 026223d2be0f1900
        self.ms.put_read_data(Conversions.hex_to_ascii('025023D2BE22FF5B411101'))
        time.sleep(3)
        self.assertEqual(self._result, Command.ON)

    def _insteon_receive_status_callback(self, *args, **kwargs):
        command = kwargs.get('command', None)
        print 'command:' + command
        self._result = command

    def test_insteon_status(self):
        response = self.insteon.status('44.33.22')
        self.assertEqual(response, True)
        
    def test_insteon_receive_status2(self):
        """
Receive Broadcast OFF command from a remote device
[2013/10/07 20:37:42] [DEBUG] [InsteonPLM] Receive< 0000   02 50 23 D2 BE 00 00 01 CB 13 00    .P#........
Message Flags = CB = 1100 1011
b1 = broadcast
b2 = group
b3 = ack
b4 = extended
b56 = hops left
b78 = max hops
[2013/10/07 20:37:40] [DEBUG] [InsteonPLM] Running status request:False:True:True:..........
[2013/10/07 20:37:40] [DEBUG] [InsteonPLM] Command: 23.D2.BE 19 00
[2013/10/07 20:37:42] [DEBUG] [InsteonPLM] Transmit>026223d2be0f1900
[2013/10/07 20:37:42] [DEBUG] [InsteonPLM] Receive< 0000   02 50 23 D2 BE 22 FF 5B 41 13 01    .P#..".[A..
1079120c278d439fdc0c998fe6af970e

[2013/10/07 20:37:42] [DEBUG] [InsteonPLM] ValidResponseCheck: 0000   53 44 31 39                SD19
[2013/10/07 20:37:42] [DEBUG] [InsteonPLM] Setting status for:23.D2.BE:19:1..........
[2013/10/07 20:37:42] [DEBUG] [InsteonPLM] Received Command:23.D2.BE:off

        """
        self._result = None
        self.insteon.onCommand(self._insteon_receive_status_callback, '23.D2.BE')
        self.ms.put_read_data(Conversions.hex_to_ascii('025023D2BE000001CB1300'))
        time.sleep(1)
        # Transmits: 026223d2be0f1900
        self.assertEqual(self._result, Command.OFF)

    def test_door_light_delgate_caseinsensitive(self):
        d = Door(address='23.d2.bE', 
                 devices=self.insteon)
        d.close()
        self.ms.put_read_data(Conversions.hex_to_ascii('025023D2BE000001CB1100'))
        time.sleep(3)
        self.ms.put_read_data(Conversions.hex_to_ascii('025023D2BE22FF5B411101'))
        time.sleep(3)
        self.assertEqual(d.state, State.OPEN)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = insteon2
import select
import time

from binascii import unhexlify
from unittest import TestCase, main
from mock import Mock

from tests.common import MockInterface, Mock_Interface, Command
from pytomation.interfaces import InsteonPLM2, Serial, HACommand, \
                                    TCP, Conversions


class InsteonInterface2Tests(TestCase):
    useMock = True

    def setUp(self):
        self.ms = Mock_Interface()
        self.insteon = InsteonPLM2(self.ms)

# If we are running live, the insteon interface doesnt like to be bombarded with requests
#            time.sleep(3)
#            self.serial = Serial('/dev/ttyUSB0', 4800)
#            self.insteon = InsteonPLM(self.serial)
#            self.tcp = TCP('192.168.13.146', 9761)
#            self.insteon = InsteonPLM2(self.tcp)

        #self.insteon.start()

    def tearDown(self):
        self.insteon.shutdown()
        self.serial = None
        try:
            self.tcp.shutdown()
            self.tcp = None
        except:
            pass

    def test_instantiation(self):
        self.assertIsNotNone(self.insteon,
                             'Insteon interface could not be instantiated')

    def test_device_on(self):
        """
        Transmit>
        0000   02 62 19 05 7B 0F 11 FF    .b..{...
        <  0000   02 62 19 05 7B 0F 11 FF 06    .b..{....
        <  0000   02 50 19 05 7B 16 F9 EC 2B 11 FF    .P..{...+..
        """
#        self.ms.add_response({Conversions.hex_to_ascii('026219057B0F11FF'):
#                              Conversions.hex_to_ascii('026219057B0F11FF06') + \
#                              Conversions.hex_to_ascii('025019057B16F9EC2B11FF')})
        response = self.insteon.on('19.05.7b')
        self.assertIn(Conversions.hex_to_ascii('026219057B0F11FF'), self.ms.query_write_data())
        self.ms.put_read_data(Conversions.hex_to_ascii('026219057B0F11FF06'))
        self.ms.put_read_data(Conversions.hex_to_ascii('025019057B16F9EC2B11FF'))
        #time.sleep(2)
        #self.assertEqual(response, True)
        
    def test_insteon_level2(self):
        self.ms.disabled = False
        
        self.insteon.level('12.20.B0', 50)
        #todo: figure out how to really deal with this race condition
        time.sleep(3)
        self.assertIn(unhexlify('02621220b00f117f'), self.ms.query_write_data())
#        self.ms.write.assert_called_with(unhexlify('02621220b00f117f'))

    def test_insteon_receive_status(self):
        """
        [2013/09/07 15:24:51] [DEBUG] [InsteonPLM] Receive< 0000   02 50 23 D2 BE 00 00 01 CB 11 00    .P#........
        d395e51a11bb096e20f9ae84b47f8884
        
        [2013/09/07 15:24:51] [WARNING] [InsteonPLM] Unhandled packet (couldn't find any pending command to deal with it) 
        [2013/09/07 15:24:51] [WARNING] [InsteonPLM] This could be a status message from a broadcast
        [2013/09/07 15:24:51] [DEBUG] [InsteonPLM] Running status request..........
        [2013/09/07 15:24:51] [DEBUG] [InsteonPLM] Command: 23.D2.BE 19 00
        [2013/09/07 15:24:51] [DEBUG] [InsteonPLM] Queued bff1ddfd362ac6ef71555d959edbb90a
        [2013/09/07 15:24:53] [DEBUG] [InsteonPLM] Timed out for bff1ddfd362ac6ef71555d959edbb90a - Requeueing (already had 0 retries)
        [2013/09/07 15:24:53] [DEBUG] [InsteonPLM] Interesting.  timed out for bff1ddfd362ac6ef71555d959edbb90a, but there are no pending com$
        [2013/09/07 15:24:53] [DEBUG] [InsteonPLM] Removing Lock <thread.lock object at 0x1a7f030>
        [2013/09/07 15:24:53] [DEBUG] [InsteonPLM] Transmit>026223d2be0f1900
        [2013/09/07 15:24:53] [DEBUG] [InsteonPLM] Receive< 0000   02 50 23 D2 BE 22 FF 5B 41 11 01    .P#..".[A..
        4996cf7dd3a4b4722f120dc9c0fe5b17
        
        [2013/09/07 15:24:53] [WARNING] [InsteonPLM] Unhandled packet (couldn't find any pending command to deal with it)
        [2013/09/07 15:24:53] [WARNING] [InsteonPLM] This could be a status message from a broadcast
        [2013/09/07 15:24:53] [DEBUG] [InsteonPLM] Running status request..........
        [2013/09/07 15:24:53] [DEBUG] [InsteonPLM] Command: 23.D2.BE 19 00
        
        """
        global logging_default_level
        ## Default logging level
        #logging_default_level = "DEBUG"
        self._result = False
        self.insteon.onCommand(self._insteon_receive_status_callback, '23.D2.BE')
        self.ms.put_read_data(Conversions.hex_to_ascii('025023D2BE000001CB1100'))
        time.sleep(1)
        # Transmits: 026223d2be0f1900
        self.ms.put_read_data(Conversions.hex_to_ascii('025023D2BE22FF5B411101'))
        time.sleep(3)
        self.assertEqual(self._result, True)

    def _insteon_receive_status_callback(self, *args, **kwargs):
        command = kwargs.get('command', None)
        print 'command:' + command
        if command == Command.ON:
            self._result = True

    def test_insteon_status(self):
        response = self.insteon.status('44.33.22')
        self.assertEqual(response, True)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = mh_send
import time

from unittest import TestCase
from mock import Mock
from pytomation.interfaces import TCP, MHSend


class MHSendTests(TestCase):
    
    def setUp(self):
#        self.tcp = TCP('127.0.0.1', 8044)
        self.tcp = Mock()
        self.mh = MHSend(self.tcp)
        self.assertIsNotNone(self.mh)

    def test_send_voice_command(self):
        self.mh.voice('turn family lamp on')
        self.tcp.write.assert_called_with('run\x0Dturn family lamp on\x0D')

########NEW FILE########
__FILENAME__ = mochad
import time

from unittest import TestCase
from mock import Mock
from pytomation.interfaces import TCP, Mochad


class MochadTests(TestCase):
    
    def setUp(self):
#        self.tcp = TCP('127.0.0.1', 1099)
#        self.tcp = TCP('www.yahoo.com', 80)
        self.tcp = Mock()
        self.mochad = Mochad(self.tcp)
        self.assertIsNotNone(self.mochad)

    def test_on(self):
        self.mochad.on('a1')
        self.tcp.write.assert_called_with('rf a1 on\x0D')
        
    def test_receive_off(self):
        interface = Mock()
        interface.callback.return_value = True
        interface.read.return_value = ''
        m = Mochad(interface)
        m.onCommand(address='a1', callback=interface.callback)
        interface.read.return_value = "rf a1 off\x0D"
        time.sleep(2)
        interface.read.return_value = ''
        interface.callback.assert_called_with(address='a1', command='off', source=m)  
       
        
########NEW FILE########
__FILENAME__ = named_pipe
import os, time

from unittest import TestCase

from pytomation.interfaces import NamedPipe, StateInterface
from pytomation.devices import StateDevice, State, Light

class NamedPipeTests(TestCase):
    def setUp(self):
        self._path_name = "/tmp/named_pipe_test"
        self.interface = NamedPipe(self._path_name)
            
    def test_instance(self):
        self.assertIsNotNone(self.interface)
    
    def test_pipe_read(self):
        test_message = 'Test'
        pipe = os.open(self._path_name, os.O_WRONLY)
        os.write(pipe, test_message)
        response = self.interface.read()
        self.assertEqual(test_message, response)
        
    def test_pipe_interface_read(self):
        path = '/tmp/named_pipe_test2'
        pi = StateInterface(NamedPipe(path))
        #pi.onCommand(self.test_pipe_interface_read_callback)
        d1 = Light(address=None, devices=pi)
        self.assertEqual(d1.state, State.UNKNOWN)

        pipe = os.open(path, os.O_WRONLY)
        os.write(pipe, State.ON)
        time.sleep(2)
        self.assertEqual(d1.state, State.ON)
        
    def test_pipe_interface_read_callback(self, *args, **kwargs):
        pass
        
        
    def tearDown(self):
        self.interface.close()
        
########NEW FILE########
__FILENAME__ = nest_thermostat
import time

from unittest import TestCase

from tests.common import MockInterface, Mock_Interface
from pytomation.interfaces import NestThermostat
from pytomation.devices import Thermostat

class NestThermostatTests(TestCase):
    def setUp(self):
        self.host = '192.168.13.210'
#        self.i = HTTP('http', self.host)
        self.i = Mock_Interface()
#        self.interface = Nest(self.i, self.host)
        self.interface = NestThermostat(username='user@email.com', password='password')
    
    def test_instantiation(self):
        self.assertIsInstance(self.interface, NestThermostat)
        
    def test_setpoint(self):
        #Address = (Structure ID, Device ID)
        address = (123, 34)
        self.interface.level(address, 74)
        
        
    def test_circulate(self):
        #Address = (Structure ID, Device ID)
        address = (123, 34)
        self.interface.circulate(address)
        
    def test_thermostat_setpoint(self):
        d = Thermostat(address=(123,123), devices=self.interface, name='Thermo1')
        d.level(74)

        
########NEW FILE########
__FILENAME__ = sparkio
import time

from unittest import TestCase

from tests.common import MockInterface, Mock_Interface
from pytomation.interfaces import HTTP, SparkIO

class SparkIOTests(TestCase):
    def setUp(self):
        self.host = 'api.sprk.io'
        self.i = HTTP('https', self.host)
#        self.i = Mock_Interface()
        self.interface = SparkIO(self.i, self.host)

    def test_instantiation(self):
        self.assertIsInstance(self.interface, SparkIO)

    def test_on(self):
        # Address = (:id, pin)
        result = self.interface.on(('elroy', 'D0'))
        self.assertEqual(result, True)
        time.sleep(5)
        
"""
## Initially this was working
jason@x120:~/projects/pytomation$ curl https://api.sprk.io/v1/devices/elroy -d pin=D0 -d level=HIGH
{
  "ok": true
}
## However, now the API is giving me an auth error now!  Not sure what is going on over there
jason@x120:~/projects/pytomation$ curl https://api.sprk.io/v1/devices/elroy -d pin=D0 -d level=HIGH
{
  "code": 400,
  "error": "invalid_request",
  "error_description": "The access token was not found"
}
"""
        #         
#     def test_circulate(self):
#         self.interface.off(self.host)
#         time.sleep(2)
#         self.interface.circulate(self.host)
#     
#     def test_setpoint(self):
#         #no prior mode, then default to heat
#         self.interface.level(address=self.host, level=72)
#         time.sleep(2)
#         self.assertIn(('tstat', '{"t_heat": 72}'), self.i.query_write_data())
#         self.i.clear_write_data()
#         self.interface.cool()
#         time.sleep(2)
#         self.assertIn(('tstat', '{"tmode": 2, "t_cool": 72}'), self.i.query_write_data())
#         
#     def test_cool(self):
#         self.interface.cool()
#         time.sleep(2)
#         self.assertIn(('tstat', '{"tmode": 2}'), self.i.query_write_data())
#         
########NEW FILE########
__FILENAME__ = stargate_interface
import select
import time

from unittest import TestCase, main

from tests.common import MockInterface
from pytomation.interfaces import Stargate, Serial, HACommand


class StargateInterfaceTests(TestCase):
    useMock = True

    def setUp(self):
        self.ms = MockInterface()
        if self.useMock:  # Use Mock Serial Port
            self.sg = Stargate(self.ms)
        else:
            self.serial = Serial('/dev/ttyUSB0', 2400)
            self.sg = Stargate(self.serial)

        #self.sg.start()

    def tearDown(self):
        self.sg.shutdown()
        self.serial = None

    def test_instantiation(self):
        self.assertIsNotNone(self.sg,
                             'SG interface could not be instantiated')

    def test_digital_input(self):
        """
        digital input #1 ON
        !!07/01083237a0fe
        digital input #1 OFF
        !!07/01083239a0ff
        """
        """
0000   21 21 30 38 2F 30 31 30    !!08/010
0008   38 31 39 33 30 61 30 66    81930a0f
0010   65                         e
"""
        # What will be written / what should we get back
        self.ms.add_response({'##%1d\r': '!!07/01083237a001\r\n'})

        # Register delegate
        self.sg.onCommand(callback=self._digital_input_callback, address='D1')
        # resend EchoMode to trigger response
        self.sg.echoMode()
        time.sleep(3)
        self.assertEqual(self.__digital_input_params['kwargs']['address'].upper(), 'D8')

    def test_digital_input_multiple(self):
        """
0000   21 21 30 38 2F 30 31 30    !!08/010
0008   37 38 38 30 37 61 30 66    78807a0f
0010   65 0D 0A 21 21 30 38 2F    e..!!08/
0018   30 31 30 37 38 38 30 37    01078807
0020   34 30 30 31 0D 0A 21 21    4001..!!
0028   30 38 2F 30 31 30 37 38    08/01078
0030   38 30 37 34 31 30 30 0D    8074100.
0038   0A                         .

"""
        # What will be written / what should we get back
        self.ms.add_response({'##%1d\r': '!!07/01083237a001\r\n!!07/01083237a000\r\n'})

        # Register delegate
        self.sg.onCommand(callback=self._digital_input_callback, address='D1')
        # resend EchoMode to trigger response
        self.sg.echoMode()
        time.sleep(1.5)
        self.assertEqual(self.__digital_input_params['kwargs']['address'].upper(), 'D1')


    def _digital_input_callback(self, *args, **kwargs):
        print "Args:" + str(args) + " Kwargs:" + str(kwargs)
        self.__digital_input_params = {'args': args, 'kwargs': kwargs}

        #response = self.sg.get_register(2, 2)
        #self.assertEqual(response, '1234')
#        if self.useMock:
#            self.assertEqual(self.ms._written, '\x120202FC\x0D')
        #sit and spin, let the magic happen
        #select.select([], [], [])

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = state_interface
import time

from unittest import TestCase
from mock import Mock

from pytomation.interfaces import StateInterface
from pytomation.devices import InterfaceDevice, State

class StateIntefaceTests(TestCase):
    def setUp(self):
        self._response = None

    def test_receive_state(self):
        mi = Mock()
        mi.read = self.response
        interface = StateInterface(mi)
        device = InterfaceDevice(address=None,
                                 devices=interface, 
                                 initial_state=State.UNKNOWN)
        self.assertEqual(device.state, State.UNKNOWN)
        self._response = State.ON
        time.sleep(2)
        self.assertEqual(device.state, State.ON)
        
        
    def response(self, *args, **kwargs):
        if self._response:
            resp = self._response
            self._response = None
            return resp
        else:
            return ''
        
########NEW FILE########
__FILENAME__ = tomato
import time

from unittest import TestCase

from tests.common import MockInterface, Mock_Interface
from pytomation.interfaces import HTTP, TomatoInterface, HTTP

class TomatoInterfaceTests(TestCase):
    def setUp(self):
        self.host = '192.168.13.1'
#        self.i = HTTP('http', self.host, username='root', password='password')
        self.i = Mock_Interface()
        self.interface = TomatoInterface(self.i, self.host, http_id='asdfaadsfasdf234')

    def test_instantiation(self):
        self.assertIsInstance(self.interface, TomatoInterface)

    def test_restriction(self):
        """
        _nextpage:restrict.asp
_service:restrict-restart
rrule1:1|-1|-1|127|192.168.13.119>192.168.13.202|||0|Roku
f_enabled:on
f_desc:Roku
f_sched_allday:on
f_sched_everyday:on
f_sched_begin:0
f_sched_end:0
f_sched_sun:on
f_sched_mon:on
f_sched_tue:on
f_sched_wed:on
f_sched_thu:on
f_sched_fri:on
f_sched_sat:on
f_type:on
f_comp_all:1
f_block_all:on
f_block_http:
_http_id:
"""
        self.interface.restriction('Roku', True)
        
        time.sleep(2)
        #data = self.i.query_write_data()
        #self.assertIn(("f_desc", "Roku"), data[0].items())
        self.i.clear_write_data()
        

########NEW FILE########
__FILENAME__ = upb_interface
import select
import time

from unittest import TestCase, main
from mock import Mock
from tests.common import MockInterface
from pytomation.interfaces import UPB, Serial, HACommand
from pytomation.devices import State

class UPBInterfaceTests(TestCase):
    useMock = True

    def setUp(self):
        self.ms = MockInterface()
        if self.useMock:  # Use Mock Serial Port
            self.upb = UPB(self.ms)
        else:
            self.serial = Serial('/dev/ttyUSB0', 4800)
            self.upb = UPB(self.serial)

        #self.upb.start()

    def tearDown(self):
        self.upb.shutdown()
        self.serial = None

    def test_instantiation(self):
        self.assertIsNotNone(self.upb,
                             'UPB interface could not be instantiated')

    def test_get_firmware_version(self):
        # What will be written / what should we get back
        self.ms.add_response({'\x120202FC\x0D': 'PR021234\x0D'})

        response = self.upb.get_register(2, 2)
        self.assertEqual(response, '1234')
#        if self.useMock:
#            self.assertEqual(self.ms._written, '\x120202FC\x0D')
        #sit and spin, let the magic happen
        #select.select([], [], [])

    def test_device_on(self):
        """
        UPBPIM, myPIM, 49, 0x1B08, 30
        UPBD,   upb_foyer,      myPIM,  49, 3
        Response>  Foyer Light On
        0000   50 55 30 38 31 30 33 31    PU081031
        0008   30 33 31 45 32 32 36 34    031E2264
        0010   31 30 0D                   10.
        """
        self.ms.add_response({'\x14081031031E226410\x0D': 'PA\x0D'})
        # Network / Device ID
        response = self.upb.on((49, 3))
        self.assertTrue(response)

    def test_device_status(self):
        """
        UPBPIM, myPIM, 49, 0x1B08, 30
        UPBD,   upb_foyer,      myPIM,  49, 3
        Response>  Foyer Light On
        0000   50 55 30 38 31 30 33 31    PU081031
        0008   30 33 31 45 32 32 36 34    031E2264
        0010   31 30 0D                   10.
        """
        #071031031E3067
        self.ms.add_response({'\x14071031031E3067\x0D': 'PA\x0D'})
        # Network / Device ID
        response = self.upb.status((49, 3))
        self.assertTrue(response)

    def test_update_status(self):
        device = Mock()
        device.address.return_value ='a1'
        self.upb.update_status();


    def test_multiple_commands_at_same_time(self):
        """
        Response>
        0000   50 55 30 38 31 30 33 31    PU081031
        0008   31 32 31 45 32 32 30 30    121E2200
        0010   36 35 0D 50 55 30 38 31    65.PU081
        0018   30 33 31 31 32 31 45 32    031121E2
        0020   32 30 30 36 35 0D          20065.
        """
        
    def test_incoming_on(self):
        """
        UBP New: PU0804310006860037:0000   50 55 30 38 30 34 33 31    PU080431
        0008   30 30 30 36 38 36 30 30    00068600
        0010   33 37                      37
        
        UBP New: PU0805310006860036:0000   50 55 30 38 30 35 33 31    PU080531
        0008   30 30 30 36 38 36 30 30    00068600
        0010   33 36                      36
        """
        m_interface = Mock()
        m_interface.read.return_value = ''
        upb = UPB(m_interface)
        m_interface.callback.return_value = True
        upb.onCommand(address=(49,6), callback=m_interface.callback)
        m_interface.read.return_value = 'PU0805310006860036'
#        time.sleep(4000)
        time.sleep(2)
        m_interface.callback.assert_called_with(address=(49,6), command=State.OFF, source=upb)  
        m_interface.read.return_value = ''

    def test_incoming_link(self):
        """
        UBP New Response: PU8A0431260F20FFFFFFEF
        UPBN:49:15:38:20
        """
        m_interface = Mock()
        m_interface.callback.return_value = True
        m_interface.read.return_value = ''
        upb = UPB(m_interface)
        upb.onCommand(address=(49,38,'L'), callback=m_interface.callback)
        m_interface.read.return_value = 'PU8A0431260F20FFFFFFEF'
#        time.sleep(4000)
        time.sleep(2)
        m_interface.callback.assert_called_with(address=(49,38,'L'), command=State.ON, source=upb)  
        m_interface.read.return_value = ''
        
    def test_incoming_k(self):
        """
0000   50 55 30 37 31 34 31 36    PU071416
0008   31 30 46 46 33 30 39 30    10FF3090
0010   0D 50 55 30 37 31 35 31    .PU07151
0018   36 31 30 46 46 33 30 38    610FF308
0020   46 0D                      F.
        """
        m_interface = Mock()
        m_interface.callback.return_value = True
        m_interface.read.return_value = ''
        upb = UPB(m_interface)
        upb.onCommand(address=(22,255), callback=m_interface.callback)
        m_interface.read.return_value = "PU07141610FF3090\x0DPU07151610FF308F\x0D"
#        time.sleep(4000)
        time.sleep(2)
        m_interface.callback.assert_called_with(address=(22,255), command='status', source=upb)  
        m_interface.read.return_value = ''
            
        
    def test_level(self):
        response = self.upb.l40((39, 4))
        self.assertTrue(True)
        
    def test_level2(self):
        response = self.upb.level((39, 4), 40)
        self.assertTrue(True)

    def test_link_activate(self):
        """
        """#        self.ms.add_response({'\x14081031031E226410\x0D': 'PA\x0D'})
        self.ms.add_response({'\x14871031031E20F7\x0D': 'PA\x0D'})
        # Network / Device ID 
        response = self.upb.on((49, 3, "L"))
        self.assertTrue(response)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = wemo
import time

from unittest import TestCase
from tests.common import MockInterface

from pytomation.interfaces import WeMo

class WeMoTests(TestCase):
    def setUp(self):
#        self.interface = WeMo( '192.168.13.141', '49153')
        self.interface = WeMo(MockInterface())
        
    def test_instantiation(self):
        self.assertIsInstance(self.interface, WeMo)
    
    def test_on(self):
        result = self.interface.on()
        self.assertEqual(result, None)
########NEW FILE########
__FILENAME__ = cron_timer
import time

from unittest import TestCase, main
from mock import Mock
from datetime import datetime, timedelta

from pytomation.utility import CronTimer, AllMatch


class CronTimerTests(TestCase):
    def setUp(self):
        self.called = False
        self.ct = CronTimer()

    def test_2_sec_callback(self):
        m = Mock()
        
        t = datetime.now().timetuple()[5]
        t += 2
        self.ct.interval(secs=t)
        self.ct.action(m.action, ())
        self.ct.start()
        time.sleep(4)
        self.ct.stop()

        self.assertEqual(m.action.called, True, "Callback was not called")

    def test_2_sec_intervals(self):
        self.called = False
        t = datetime.now().timetuple()[5]
        self.ct.interval(secs=(t + 2 % 60, t + 4 % 60))
        self.ct.action(self.callback, ())
        self.ct.start()
        time.sleep(3)
        self.assertEqual(self.called, True, "Callback was not called - 1st iteration")
        self.called = False
        time.sleep(3)
        self.assertEqual(self.called, True, "Callback was not called - 2nd iteration")
        self.ct.stop()

    def test_datetime_to_cron(self):
        cron = CronTimer.to_cron('5:34pm')
        self.assertEqual(cron[0], 0)
        self.assertEqual(cron[1], 34)
        self.assertEqual(cron[2], 17)
        self.assertEqual(cron[4], AllMatch())

        cron = CronTimer.to_cron('6:52 pm')
        self.assertEqual(cron[0], 0)
        self.assertEqual(cron[1], 52)
        self.assertEqual(cron[2], 18)
        self.assertEqual(cron[4], AllMatch())

        cron = CronTimer.to_cron('5:13 AM')
        self.assertEqual(cron[0], 0)
        self.assertEqual(cron[1], 13)
        self.assertEqual(cron[2], 5)
        self.assertEqual(cron[4], AllMatch())

        cron = CronTimer.to_cron('5:13:34 AM')
        self.assertEqual(cron[0], 34)
        self.assertEqual(cron[1], 13)
        self.assertEqual(cron[2], 5)
        self.assertEqual(cron[4], AllMatch())

        cron = CronTimer.to_cron('3:14')
        self.assertEqual(cron[0], 0)
        self.assertEqual(cron[1], 14)
        self.assertEqual(cron[2], 3)
        self.assertEqual(cron[4], AllMatch())

        cron = CronTimer.to_cron('18:42')
        self.assertEqual(cron[0], 0)
        self.assertEqual(cron[1], 42)
        self.assertEqual(cron[2], 18)
        self.assertEqual(cron[4], AllMatch())

    def callback(self):
        self.called = True

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = periodic_timer
import time

from unittest import TestCase, main
from datetime import datetime, timedelta

from pytomation.utility import PeriodicTimer

class PeriodicTimerTests(TestCase):
    def setUp(self):
        self.called = False

    def test_no_sec_callback(self):
        rt = PeriodicTimer()
        rt.interval = 60
        rt.action(self.callback, ())
        rt.start()
        time.sleep(3)
        rt.stop()
        self.assertEqual(self.called, False, "Callback was not called")

    def test_1_sec_callback(self):
        rt = PeriodicTimer()
        rt.interval = 1
        rt.action(self.callback, ())
        rt.start()
        time.sleep(3)
        rt.stop()
        self.assertEqual(self.called, True, "Callback was not called")
    
    def test_2_sec_repeated(self):
        rt = PeriodicTimer()
        rt.interval = 2
        rt.action(self.callback, ())
        rt.start()
        time.sleep(3)
        self.assertEqual(self.called, True, "Callback was not called 1st time")
        self.called = False
        time.sleep(3)
        self.assertEqual(self.called, True, "Callback was not called 2nd time")
                
    def callback(self, *args, **kwargs):
        self.called = True

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = timer
import time

from mock import Mock
from unittest import TestCase, main
from datetime import datetime, timedelta

from pytomation.utility.timer import Timer as CTimer


class TimerTests(TestCase):
    def setUp(self):
        pass

    def test_no_sec_callback(self):
        callback = Mock()
        callback.test.return_value = True
        rt = CTimer()
        rt.interval = 60
        rt.action(callback.test, ())
        rt.start()
        time.sleep(3)
        rt.stop()
        self.assertFalse(callback.test.called)

    def test_3_sec_callback(self):
        callback = Mock()
        callback.test.return_value = True
        rt = CTimer(3)
        rt.action(callback.test, ())
        rt.start()
        self.assertFalse(callback.test.called)
        time.sleep(4)
        self.assertTrue(callback.test.called)

    def test_double_timer_bug(self):
        callback = Mock()
        callback.test.return_value = True
        rt = CTimer(3)
        rt.action(callback.test, ())
        rt.start()
        rt.start()
        rt.stop()
        self.assertFalse(callback.test.called)
        time.sleep(4)
        self.assertFalse(callback.test.called)
        
    def test_isAlive(self):
        rt = CTimer()
        rt.interval = 2
        rt.start()
        self.assertTrue(rt.isAlive())
        time.sleep(3)
        self.assertFalse(rt.isAlive())        

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = time_funcs
from unittest import TestCase
from pytomation.utility import CronTimer
from pytomation.utility.time_funcs import *

class TimeFuncsTests(TestCase):
    def setUp(self):
        pass
        
    def test_timefuncs_in_range(self):
        start = CronTimer.to_cron("4:52pm")
        end = CronTimer.to_cron("4:55pm")
        now = CronTimer.to_cron("4:54pm")
        self.assertTrue(crontime_in_range(now, start, end))
        
    def test_timefuncs_out_range(self):
        start = CronTimer.to_cron("4:52pm")
        end = CronTimer.to_cron("4:55pm")
        now = CronTimer.to_cron("5:54pm")
        self.assertFalse(crontime_in_range(now, start, end))

    def test_timefuncs_out_range2(self):
        start = CronTimer.to_cron("12:01am")
        end = CronTimer.to_cron("8:00am")
        now = CronTimer.to_cron("5:54pm")
        self.assertFalse(crontime_in_range(now, start, end))
    
    def test_timefuncs_in_range_flip(self):
        start = CronTimer.to_cron("10:03pm")
        end = CronTimer.to_cron("4:55am")
        now = CronTimer.to_cron("2:54am")
        self.assertTrue(crontime_in_range(now, start, end))
        
    def test_timefuncs_out_range_flip(self):
        start = CronTimer.to_cron("10:03pm")
        end = CronTimer.to_cron("4:55am")
        now = CronTimer.to_cron("2:54pm")
        self.assertFalse(crontime_in_range(now, start, end))
        



########NEW FILE########
