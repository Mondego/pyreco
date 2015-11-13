__FILENAME__ = cob_controller_adapter_gazebo
#!/usr/bin/env python
import roslib; roslib.load_manifest('cob_controller_configuration_gazebo')

import rospy
from std_msgs.msg import Float64
from brics_actuator.msg import JointVelocities, JointPositions
from controller_manager_msgs.srv import *

class cob_controller_adapter_gazebo():

  def __init__(self):
    self.joint_names = rospy.get_param("joint_names", [])
    
    self.vel_controller_pubs = []
    self.vel_controller_names = []
    self.pos_controller_pubs = []
    self.pos_controller_names = []
    
    for i in range(len(self.joint_names)):
        pub = rospy.Publisher('/'+self.joint_names[i]+'_velocity_controller/command', Float64)
        self.vel_controller_pubs.append(pub)
        self.vel_controller_names.append(self.joint_names[i]+'_velocity_controller')
    for i in range(len(self.joint_names)):
        pub = rospy.Publisher('/'+self.joint_names[i]+'_position_controller/command', Float64)
        self.pos_controller_pubs.append(pub)
        self.pos_controller_names.append(self.joint_names[i]+'_position_controller')
    
    rospy.logwarn("Waiting for load_controller service...")
    rospy.wait_for_service('/controller_manager/load_controller')
    rospy.loginfo("...load_controller service available!")
    
    self.load_client = rospy.ServiceProxy('/controller_manager/load_controller', LoadController)

    rospy.logwarn("Waiting for switch_controller service...")
    rospy.wait_for_service('/controller_manager/switch_controller')
    rospy.loginfo("...switch_controller service available!")
    
    self.switch_client = rospy.ServiceProxy('/controller_manager/switch_controller', SwitchController)
    
    for controller in self.vel_controller_names:
        res = self.load_client(controller)
    for controller in self.pos_controller_names:
        res = self.load_client(controller)
    
    self.switch_controller(self.pos_controller_names, [])
    self.current_control_mode = "position"
    
    self.update_rate = rospy.get_param("update_rate", 33.0)
    self.max_vel_command_silence = rospy.get_param("max_vel_command_silence", 0.5)
    self.last_vel_command = rospy.get_time()
    
    self.cmd_vel_sub = rospy.Subscriber("command_vel", JointVelocities, self.cmd_vel_cb)
    self.cmd_pos_sub = rospy.Subscriber("command_pos", JointPositions, self.cmd_pos_cb)

    rospy.sleep(0.5)


  def run(self):
    r = rospy.Rate(self.update_rate)
    while not rospy.is_shutdown():
        if (rospy.get_time() - self.last_vel_command >= self.max_vel_command_silence) and (self.current_control_mode != "position"):
            rospy.loginfo("Have not heard a vel command for %f seconds. Switch to position_controllers", (rospy.get_time()-self.last_vel_command))
            self.switch_controller(self.pos_controller_names, self.vel_controller_names)
            self.current_control_mode = "position"
        r.sleep()
  
  
  def switch_controller(self, start_controllers, stop_controllers):
    rospy.loginfo("Switching controllers")
    
    req = SwitchControllerRequest()
    req.strictness = 2
    for i in range(len(start_controllers)):
        req.start_controllers.append(start_controllers[i])
    for i in range(len(stop_controllers)):
        req.stop_controllers.append(stop_controllers[i])
    
    try:
        res = self.switch_client(req)
    except rospy.ServiceException, e:
        rospy.logerr("Service call failed: %s", e)
    
    print res
    return res.ok
    
    

  def cmd_vel_cb(self, data):
    if (self.current_control_mode != "velocity"):
        rospy.logwarn("Have to switch to velocity_controllers")
        self.switch_controller(self.vel_controller_names, self.pos_controller_names)
        self.current_control_mode = "velocity"
    self.last_vel_command = rospy.get_time()
    #print data
    if(len(self.joint_names) != len(data.velocities)):
        rospy.logerr("DOF do not match")
        return
    for i in range(len(self.joint_names)):
        self.vel_controller_pubs[i].publish(Float64(data.velocities[i].value))
    
    
  def cmd_pos_cb(self, data):
    if (self.current_control_mode != "position"):
        rospy.logwarn("Have to switch to position_controllers")
        self.switch_controller(self.pos_controller_names, self.vel_controller_names)
        self.current_control_mode = "position"
    #print data
    if(len(self.joint_names) != len(data.positions)):
        rospy.logerr("DOF do not match")
        return
    for i in range(len(self.joint_names)):
        self.pos_controller_pubs[i].publish(Float64(data.positions[i].value))




if __name__ == "__main__":
  rospy.init_node('cob_controller_adapter_gazebo_node')
  cctm = cob_controller_adapter_gazebo()
  rospy.loginfo("cob_controller_adapter_gazebo running")
  cctm.run()

########NEW FILE########
__FILENAME__ = fake_diagnostics
#!/usr/bin/env python
import roslib; roslib.load_manifest('cob_controller_configuration_gazebo')

import sys
import rospy
from diagnostic_msgs.msg import DiagnosticArray,DiagnosticStatus

global last_received_

def callback(msg):
	global last_received_
	last_received_ = rospy.Time.now()

if __name__ == "__main__":
	rospy.init_node('fake_diagnostics')

	if not rospy.has_param("~diagnostics_name"):
		rospy.logerr("parameter diagnostics_name not found, shutting down " + rospy.get_name())
		sys.exit()
	diagnostics_name = rospy.get_param("~diagnostics_name")

	if not rospy.has_param("~topic_name"):
		rospy.logwarn("parameter topic_name not found. Not listening to any topic for " + rospy.get_name())
	topic_name = rospy.get_param("~topic_name",None)

	global last_received_
	last_received_ = rospy.Time.now()

	# subscribe to topics
	if topic_name != None:
		rospy.Subscriber(topic_name, rospy.AnyMsg, callback)

	pub_diagnostics = rospy.Publisher('/diagnostics', DiagnosticArray)

	rospy.loginfo("fake diagnostics for %s running listening to %s",diagnostics_name, topic_name)
	rate = rospy.Rate(1)
	while not rospy.is_shutdown():
		# if no topic_name is set, we assume that we received a 
		if topic_name == None:
			last_received_ = rospy.Time.now()

		# only publish ok if message received recently
		if rospy.Time.now() - last_received_ <= rospy.Duration(10.0):
			status = DiagnosticStatus()
			status.level = 0
			status.name = diagnostics_name
			status.message = diagnostics_name + " running"
			diagnostics = DiagnosticArray()
			diagnostics.status.append(status)
		else:
			status = DiagnosticStatus()
			status.level = 2
			status.name = diagnostics_name
			status.message = "no message received on " + topic_name
			diagnostics = DiagnosticArray()
			diagnostics.status.append(status)
		pub_diagnostics.publish(diagnostics)
		rate.sleep()

########NEW FILE########
__FILENAME__ = gazebo_services
#!/usr/bin/env python
import roslib; roslib.load_manifest('cob_controller_configuration_gazebo')

import rospy
import actionlib

from control_msgs.msg import FollowJointTrajectoryAction

# care-o-bot includes
from cob_srvs.srv import *

class gazebo_services():

	def __init__(self):
		self.action_client = actionlib.SimpleActionClient('follow_joint_trajectory', FollowJointTrajectoryAction)
		self.init_srv = rospy.Service('init', Trigger, self.init_cb)
		self.stop_srv = rospy.Service('stop', Trigger, self.stop_cb)
		self.recover_srv = rospy.Service('recover', Trigger, self.recover_cb)
		self.set_operation_mode_srv = rospy.Service('set_operation_mode', SetOperationMode, self.set_operation_mode_cb)

	def init_cb(self, req):
		resp = TriggerResponse()
		resp.success.data = True
		return resp
	
	def stop_cb(self, req):
		self.action_client.cancel_all_goals()
		resp = TriggerResponse()
		resp.success.data = True
		return resp

	def recover_cb(self, req):
		resp = TriggerResponse()
		resp.success.data = True
		return resp
	
	def set_operation_mode_cb(self, req):
		resp = SetOperationModeResponse()
		resp.success.data = True
		return resp


if __name__ == "__main__":
   rospy.init_node('gazebo_services')
   gazebo_services()
   rospy.loginfo("gazebo_services running")
   rospy.spin()


########NEW FILE########
__FILENAME__ = gazebo_services_base
#!/usr/bin/env python
import roslib; roslib.load_manifest('cob_controller_configuration_gazebo')

import rospy
import actionlib

from move_base_msgs.msg import MoveBaseAction

# care-o-bot includes
from cob_srvs.srv import *

class gazebo_services_base():

	def __init__(self):
		# base
		self.base_client = actionlib.SimpleActionClient('/move_base', MoveBaseAction)
		#self.base_init_srv = rospy.Service('/base_controller/init', Trigger, self.base_init_cb)
		self.base_stop_srv = rospy.Service('/base_controller/stop', Trigger, self.base_stop_cb)
		#self.base_recover_srv = rospy.Service('/base_controller/recover', Trigger, self.base_recover_cb)
		#self.base_set_operation_mode_srv = rospy.Service('/base_controller/set_operation_mode', SetOperationMode, self.base_set_operation_mode_cb)

	# base
	def base_init_cb(self, req):
		resp = TriggerResponse()
		resp.success.data = True
		return resp
	
	def base_stop_cb(self, req):
		self.base_client.cancel_all_goals()
		resp = TriggerResponse()
		resp.success.data = True
		return resp

	def base_recover_cb(self, req):
		resp = TriggerResponse()
		resp.success.data = True
		return resp
	
	def base_set_operation_mode_cb(self, req):
		resp = SetOperationModeResponse()
		resp.success.data = True
		return resp


if __name__ == "__main__":
   rospy.init_node('gazebo_services_base')
   gazebo_services_base()
   rospy.loginfo("gazebo_services_base running")
   rospy.spin()


########NEW FILE########
__FILENAME__ = gazebo_topics
#!/usr/bin/env python
import roslib; roslib.load_manifest('cob_controller_configuration_gazebo')

import rospy


# care-o-bot includes
from std_msgs.msg import Empty

class gazebo_topics():

	def __init__(self):
		#fake_diagnostics
		self.joy_usage_pub = rospy.Publisher("/joy_usage", Empty)
		self.pc1_usage_pub = rospy.Publisher("/pc1_usage", Empty)
		self.pc2_usage_pub = rospy.Publisher("/pc2_usage", Empty)
		self.pc3_usage_pub = rospy.Publisher("/pc3_usage", Empty)
		self.wifi_status_pub = rospy.Publisher("/wifi_status", Empty)
		
		rospy.sleep(0.5)


if __name__ == "__main__":
	rospy.init_node('gazebo_topics')
	gt = gazebo_topics()
	rospy.loginfo("gazebo_topics running")
	
	rate = rospy.Rate(1)
	while not rospy.is_shutdown():
		msg = Empty()
		gt.joy_usage_pub.publish(msg)
		gt.pc1_usage_pub.publish(msg)
		gt.pc2_usage_pub.publish(msg)
		gt.pc3_usage_pub.publish(msg)
		gt.wifi_status_pub.publish(msg)
		rate.sleep()


########NEW FILE########
__FILENAME__ = battery_monitor
#!/usr/bin/python
#################################################################
##\file
#
# \note
#   Copyright (c) 2012 \n
#   Fraunhofer Institute for Manufacturing Engineering
#   and Automation (IPA) \n\n
#
#################################################################
#
# \note
#   Project name: care-o-bot
# \note
#   ROS stack name: cob_robots
# \note
#   ROS package name: cob_monitoring
#
# \author
#   Author: Florian Weisshardt
# \author
#   Supervised by: 
#
# \date Date of creation: Dec 2012
#
# \brief
#   Monitors the battery level and announces warnings and reminders to recharge.
#
#################################################################
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     - Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer. \n
#     - Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution. \n
#     - Neither the name of the Fraunhofer Institute for Manufacturing
#       Engineering and Automation (IPA) nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission. \n
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License LGPL as 
# published by the Free Software Foundation, either version 3 of the 
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License LGPL for more details.
# 
# You should have received a copy of the GNU Lesser General Public 
# License LGPL along with this program. 
# If not, see <http://www.gnu.org/licenses/>.
#
#################################################################

import roslib
roslib.load_manifest('cob_monitoring')
import rospy

from pr2_msgs.msg import *

from simple_script_server import *
sss = simple_script_server()

class battery_monitor():
	def __init__(self):
		rospy.Subscriber("/power_state", PowerState, self.power_state_callback)
		self.rate = rospy.Rate(1/10.0) # check every 10 sec
		self.warn_announce_time  = rospy.Duration(300.0)
		self.error_announce_time = rospy.Duration(120.0)
		self.last_announced_time = rospy.Time.now()

	## Battery monitoring
	### TODO: make values parametrized through yaml file (depending on env ROBOT)
	def power_state_callback(self,msg):
		if msg.relative_capacity <= 10.0:
			rospy.logerr("Battery empty, recharge now! Battery state is at " + str(msg.relative_capacity) + "%.")
			#TODO: print "start flashing red fast --> action call to lightmode"
			if rospy.Time.now() - self.last_announced_time >= self.error_announce_time:
				sss.say(["My battery is empty, please recharge now."])
				self.last_announced_time = rospy.Time.now()
		elif msg.relative_capacity <= 30.0:			
			rospy.logwarn("Battery nearly empty, consider recharging. Battery state is at " + str(msg.relative_capacity) + "%.") 
			#TODO: "start flashing yellow slowly --> action call to lightmode"
			if rospy.Time.now() - self.last_announced_time >= self.warn_announce_time:
				sss.say(["My battery is nearly empty, please consider recharging."])
				self.last_announced_time = rospy.Time.now()
		else:
			rospy.logdebug("Battery level ok.")	
		
		# sleep
		self.rate.sleep()

if __name__ == "__main__":
	rospy.init_node("battery_monitor")
	battery_monitor()
	rospy.spin()

########NEW FILE########
__FILENAME__ = emergency_stop_monitor
#!/usr/bin/python

import roslib
roslib.load_manifest('cob_monitoring')
import rospy

from geometry_msgs.msg import Twist
from diagnostic_msgs.msg import DiagnosticArray

from cob_relayboard.msg import *

from simple_script_server import *
sss = simple_script_server()

##################
### TODO: add diagnostics for em_stop (probably better to be implemented in relayboard) --> then create a diagnostics_monitor.py with sets leds and sound from diagnostics information (for arm, base, torso, ...)
### which color and flashing code assign to diagnostics?
##################

class emergency_stop_monitor():
	def __init__(self):
		self.color = "None"
		self.sound_enabled = rospy.get_param("~sound_enabled", True)
		self.led_enabled = rospy.get_param("~led_enabled", True)
		if(self.led_enabled):
			rospy.wait_for_service("/light_controller/mode")
			self.diagnotics_enabled = rospy.get_param("~diagnostics_based", False)
			if(self.diagnotics_enabled):
				rospy.Subscriber("/diagnostics", DiagnosticArray, self.new_diagnostics)
				self.on = False
        			self.diag_err = False
				self.last_led = rospy.get_rostime()
			else:
				rospy.Subscriber("/emergency_stop_state", EmergencyStopState, self.emergency_callback)	
				self.em_status = EmergencyStopState()
				self.first_time = True

			self.motion_sensing = rospy.get_param("~motion_sensing", False)
			if(self.motion_sensing):
				rospy.Subscriber("/base_controller/command_direct", Twist, self.new_velcommand)
				self.last_vel = rospy.get_rostime()

	## Diagnostics monitoring
	def new_diagnostics(self, diag):
        	for status in diag.status:
            		if(status.name == "//base_controller"):
                		if(status.level != 0):## && self.last_base_diag == 0):
                    			self.diag_err = True
                		elif(status.level == 0):## && self.last_base_diag == 1):
                    			self.diag_err = False
		if((rospy.get_rostime() - self.last_led).to_sec() > 0.5):
			self.last_led = rospy.get_rostime()
		        #Trigger LEDS
	    		if(self.diag_err):
				if(self.color != "red"):
		    			sss.set_light("red")	
					self.color = "red"
	    		else:
        			if ((rospy.get_rostime() - self.last_vel).to_sec() > 1.0):
					if(self.color != "green"):
		            			sss.set_light("green")
						self.color = "green"
	    	    		else:
        		    		if(self.on):
            		    			self.on = False
						if(self.color != "yellow"):
	            	    				sss.set_light("yellow")
							self.color = "yellow"
	 		           	else:
        	        			self.on = True
						if(self.color != "led_off"):
				                	sss.set_light("led_off")
							self.color = "led_off"
		

	## Velocity Monitoring
	def new_velcommand(self, twist):
	        if twist.linear.x != 0 or twist.linear.y != 0 or twist.angular.z != 0:
        		self.last_vel = rospy.get_rostime()

	## Emergency stop monitoring
	def emergency_callback(self,msg):
		# skip first message to avoid speach output on startup
		if self.first_time:
			self.first_time = False
			self.em_status = msg
			return
	
		if self.em_status.emergency_state != msg.emergency_state:
			self.em_status = msg
			rospy.loginfo("Emergency change to "+ str(self.em_status.emergency_state))
		
			if self.em_status.emergency_state == 0: # ready
				sss.set_light("green")
			elif self.em_status.emergency_state == 1: # em stop
				sss.set_light("red")
				if self.em_status.scanner_stop and not self.em_status.emergency_button_stop:
					if(self.sound_enabled):
						sss.say(["laser emergency stop issued"])
				elif not self.em_status.scanner_stop and self.em_status.emergency_button_stop:
					if(self.sound_enabled):
						sss.say(["emergency stop button pressed"])
				else:
					if(self.sound_enabled):
						sss.say(["emergency stop issued"])
			elif self.em_status.emergency_state == 2: # release
				sss.set_light("yellow")
				if(self.sound_enabled):
					sss.say(["emergency stop released"])

if __name__ == "__main__":
	rospy.init_node("emergency_stop_monitor")
	emergency_stop_monitor()
	rospy.spin()

########NEW FILE########
