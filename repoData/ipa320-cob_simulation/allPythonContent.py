__FILENAME__ = remove_object
#!/usr/bin/python
#################################################################
##\file
#
# \note
# Copyright (c) 2010 \n
# Fraunhofer Institute for Manufacturing Engineering
# and Automation (IPA) \n\n
#
#################################################################
#
# \note
# Project name: Care-O-bot Research
# \note
# ROS stack name: cob_environments
# \note
# ROS package name: cob_gazebo_objects
#
# \author
# Author: Florian Weisshardt, email:florian.weisshardt@ipa.fhg.de
# \author
# Supervised by: Florian Weisshardt, email:florian.weisshardt@ipa.fhg.de
#
# \date Date of creation: Feb 2012
#
# \brief
# Implements script server functionalities.
#
#################################################################
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer. \n
# - Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution. \n
# - Neither the name of the Fraunhofer Institute for Manufacturing
# Engineering and Automation (IPA) nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission. \n
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
# If not, see < http://www.gnu.org/licenses/>.
#
#################################################################
import sys
import roslib
roslib.load_manifest('cob_bringup_sim')

import rospy
import os

from gazebo.srv import *
from geometry_msgs.msg import *
import tf.transformations as tft

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print '[remove_object.py] Please specify the names of the objects to be removed'
		sys.exit()
	
	rospy.init_node("object_remover")

	# check for all objects on parameter server
	if not rospy.has_param("/objects"):
		rospy.logerr("No objects uploaded to /objects")
		all_object_names = []
	else:
		all_object_names = rospy.get_param("/objects").keys()

	# if keyword all is in list of object names we'll load all models uploaded to parameter server
	if "all" in sys.argv:
		object_names = all_object_names
	else:
		object_names = sys.argv
		object_names.pop(0) # remove first element of sys.argv which is file name

	rospy.loginfo("Trying to remove %s",object_names)
	
	for name in object_names:
		# check if object is already spawned
		srv_delete_model = rospy.ServiceProxy('gazebo/delete_model', DeleteModel)
		req = DeleteModelRequest()
		req.model_name = name
		exists = True
		try:
			res = srv_delete_model(name)
		except rospy.ServiceException, e:
			exists = False
			rospy.logdebug("Model %s does not exist in gazebo.", name)

		if exists:
			rospy.loginfo("Model %s removed.", name)
		else:
			rospy.logerr("Model %s not found in gazebo.", name)

########NEW FILE########
__FILENAME__ = spawn_object
#!/usr/bin/python
#################################################################
##\file
#
# \note
# Copyright (c) 2010 \n
# Fraunhofer Institute for Manufacturing Engineering
# and Automation (IPA) \n\n
#
#################################################################
#
# \note
# Project name: Care-O-bot Research
# \note
# ROS stack name: cob_environments
# \note
# ROS package name: cob_gazebo_objects
#
# \author
# Author: Florian Weisshardt, email:florian.weisshardt@ipa.fhg.de
# \author
# Supervised by: Florian Weisshardt, email:florian.weisshardt@ipa.fhg.de
#
# \date Date of creation: Feb 2012
#
# \brief
# Implements script server functionalities.
#
#################################################################
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer. \n
# - Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution. \n
# - Neither the name of the Fraunhofer Institute for Manufacturing
# Engineering and Automation (IPA) nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission. \n
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
# If not, see < http://www.gnu.org/licenses/>.
#
#################################################################
import sys
import roslib
roslib.load_manifest('cob_bringup_sim')

import rospy
import os

from gazebo_msgs.srv import *
from geometry_msgs.msg import *
import tf.transformations as tft

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print '[spawn_object.py] Please specify the names of the objects to be loaded'
		sys.exit()
	
	rospy.init_node("object_spawner")

	# check for all objects on parameter server
	if not rospy.has_param("/objects"):
		rospy.logerr("No objects uploaded to /objects")
		sys.exit()
	all_object_names = rospy.get_param("/objects").keys()

	# if keyword all is in list of object names we'll load all models uploaded to parameter server
	if "all" in sys.argv:
		object_names = all_object_names
	else:
		object_names = sys.argv
		object_names.pop(0) # remove first element of sys.argv which is file name

	rospy.loginfo("Trying to spawn %s",object_names)
	
	for name in object_names:
		# check for object on parameter server
		if not rospy.has_param("/objects/%s" % name):
			rospy.logerr("No description for " + name + " found at /objects/" + name)
			continue
		
		# check for model
		if not rospy.has_param("/objects/%s/model" % name):
			rospy.logerr("No model for " + name + " found at /objects/" + name + "/model")
			continue
		model = rospy.get_param("/objects/%s/model" % name)
		
		# check for model_type
		if not rospy.has_param("/objects/%s/model_type" % name):
			rospy.logerr("No model_type for " + name + " found at /objects/" + name + "/model_type")
			continue
		model_type = rospy.get_param("/objects/%s/model_type" % name)
		
		# check for position
		if not rospy.has_param("/objects/%s/position" % name):
			rospy.logerr("No position for " + name + " found at /objects/" + name + "/position")
			continue
		position = rospy.get_param("/objects/%s/position" % name)

		# check for orientation
		if not rospy.has_param("/objects/%s/orientation" % name):
			rospy.logerr("No orientation for " + name + " found at /objects/" + name + "/orientation")
			continue
		# convert rpy to quaternion for Pose message
		orientation = rospy.get_param("/objects/%s/orientation" % name)
		quaternion = tft.quaternion_from_euler(orientation[0], orientation[1], orientation[2])
		object_pose = Pose()
		object_pose.position.x = float(position[0])
		object_pose.position.y = float(position[1])
		object_pose.position.z = float(position[2])
		object_pose.orientation.x = quaternion[0]
		object_pose.orientation.y = quaternion[1]
		object_pose.orientation.z = quaternion[2]
		object_pose.orientation.w = quaternion[3]

		try:
			file_localition = roslib.packages.get_pkg_dir('cob_gazebo_objects') + '/objects/' + model + '.' + model_type
		except:
			print "File not found: cob_gazebo_objects" + "/objects/" + model + "." + model_type
			continue

		# call gazebo service to spawn model (see http://ros.org/wiki/gazebo)
		if model_type == "urdf":
			srv_spawn_model = rospy.ServiceProxy('/gazebo/spawn_urdf_model', SpawnModel)
			file_xml = open(file_localition)
			xml_string=file_xml.read()

		elif model_type == "urdf.xacro":
			p = os.popen("rosrun xacro xacro.py " + file_localition)
			xml_string = p.read()
			p.close()
			srv_spawn_model = rospy.ServiceProxy('/gazebo/spawn_urdf_model', SpawnModel)

		elif model_type == "model":
			srv_spawn_model = rospy.ServiceProxy('/gazebo/spawn_gazebo_model', SpawnModel)
			file_xml = open(file_localition)
			xml_string=file_xml.read()
		else:
			rospy.logerr('Model type not know. model_type = ' + model_type)
			continue


		# check if object is already spawned
		srv_delete_model = rospy.ServiceProxy('gazebo/delete_model', DeleteModel)
		req = DeleteModelRequest()
		req.model_name = name
		exists = True
		try:
			rospy.wait_for_service('/gazebo/delete_model')
			res = srv_delete_model(name)
		except rospy.ServiceException, e:
			exists = False
			rospy.logdebug("Model %s does not exist in gazebo.", name)

		if exists:
			rospy.loginfo("Model %s already exists in gazebo. Model will be updated.", name)

		# spawn new model
		req = SpawnModelRequest()
		req.model_name = name # model name from command line input
		req.model_xml = xml_string
		req.initial_pose = object_pose

		res = srv_spawn_model(req)
	
		# evaluate response
		if res.success == True:
			rospy.loginfo(res.status_message + " " + name)
		else:
			print "Error: model %s not spawn. error message = "% name + res.status_message


########NEW FILE########
__FILENAME__ = component_test
#!/usr/bin/env python
import roslib
roslib.load_manifest('cob_gazebo')
roslib.load_manifest('cob_script_server')

import sys
import time
import unittest

import rospy
import rostest
from trajectory_msgs.msg import *
from simple_script_server import *
from control_msgs.msg import *

class UnitTest(unittest.TestCase):
    def __init__(self, *args):
        super(UnitTest, self).__init__(*args)
        rospy.init_node('component_test')
        self.message_received = False
        self.sss=simple_script_server()
        
    def setUp(self):
        self.errors = []

    def test_component(self):
        # get parameters
        try:
            # component
            if not rospy.has_param('~component'):
                self.fail('Parameter component does not exist on ROS Parameter Server')
            component = rospy.get_param('~component')

            # movement command
            if not rospy.has_param('~target'):
                self.fail('Parameter target does not exist on ROS Parameter Server')
            target = rospy.get_param('~target')

            # time to wait before
            wait_time = rospy.get_param('~wait_time',5)

            # error range
            if not rospy.has_param('~error_range'):
                self.fail('Parameter error_range does not exist on ROS Parameter Server')
            error_range = rospy.get_param('~error_range')

        except KeyError, e:
            self.fail('Parameters not set properly')

        print """
              Component: %s  
              Target: %s
              Wait Time: %s
              Error Range: %s"""%(component, target, wait_time, error_range)
        
        # check parameters
        # \todo do more parameter tests
        if error_range < 0.0:
            error_msg = "Parameter error_range should be positive, but is " + error_range
            self.fail(error_msg)
        if wait_time < 0.0:
            error_msg = "Parameter wait_time should be positive, but is " + wait_time
            self.fail(error_msg)
        
        # init subscribers
        command_topic = "/" + component + "_controller/command"
        state_topic = "/" + component + "_controller/state"
        sub_command_topic = rospy.Subscriber(command_topic, JointTrajectory, self.cb_command) 
        sub_state_topic = rospy.Subscriber(state_topic, JointTrajectoryControllerState, self.cb_state) 
        
        # init component
        init_handle = self.sss.init(component)
        if init_handle.get_error_code() != 0:
            error_msg = 'Could not initialize ' + component
            self.fail(error_msg)
        
        # start actual test
        print "Waiting for messages"
        # give the topics some seconds to receive messages
        wallclock_timeout_t = time.time() + wait_time
        while not self.message_received and time.time() < wallclock_timeout_t:
            #print "###debug here###" 
            time.sleep(0.1)
        if not self.message_received:
            self.fail('No state message received within wait_time')
          
        # send commands to component
        move_handle = self.sss.move(component,target)
        # move_handle = self.sss.move("arm","folded")
        if move_handle.get_error_code() != 0:
            error_msg = 'Could not move ' + component
            self.fail(error_msg + "; errorCode: " + str(move_handle.get_error_code()))
        
        # get last point out of trajectory
        traj_endpoint = self.command_traj.points[len(self.command_traj.points)-1]
             
        # Start evaluation
        timeout_t = traj_endpoint.time_from_start.to_sec()*0.5 # movement should already be finished, but let wait with an additional buffer of 50% times the desired time
        rospy.sleep(timeout_t)
        print "Done waiting, validating results"
        actual_pos = self.actual_pos # fix current position configuration for later evaluation
        
        # checking if target position is realy reached
        for i in range(len(traj_endpoint.positions)):
            self.assert_(((traj_endpoint.positions[i] - actual_pos[i]) < error_range), "Target position out of error_range")
            
    # callback functions
    def cb_state(self, msg):
        self.message_received = True
        self.actual_pos = msg.actual.positions
    def cb_command(self, msg):
        self.command_traj = msg
         
if __name__ == '__main__':
    try:
        rostest.run('rostest', 'component_test', UnitTest, sys.argv)
    except KeyboardInterrupt, e:
        pass
    print "exiting"


########NEW FILE########
__FILENAME__ = elevator
#!/usr/bin/python
#################################################################
##\file
#
# \note
# Copyright (c) 2012 \n
# Fraunhofer Institute for Manufacturing Engineering
# and Automation (IPA) \n\n
#
#################################################################
#
# \note
# Project name: Care-O-bot
# \note
# ROS stack name: cob_environments
# \note
# ROS package name: cob_gazebo_worlds
#
# \author
# Author: Nadia Hammoudeh Garcia
# \author
# Supervised by: Nadia Hammoudeh Garcia
#
# \date Date of creation: 26.06.2012
#
#
#################################################################
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer. \n
# - Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution. \n
# - Neither the name of the Fraunhofer Institute for Manufacturing
# Engineering and Automation (IPA) nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission. \n
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

import time
import sys
import roslib
roslib.load_manifest('cob_gazebo_worlds')
import rospy
import random
from math import *

#from gazebo.srv import *
from gazebo_msgs.srv import *
from gazebo_msgs.msg import *


apply_effort_service = rospy.ServiceProxy('/gazebo/apply_joint_effort', ApplyJointEffort)
door_closed = True



def callback(ContactsState):

	if door_closed:
		if (ContactsState.states != []):
			rospy.loginfo("button pressed")	
			rand = (random.randint(0,1))
			if rand == 0:
				move_door("left")
			else:
				move_door("right")
		else:
			rospy.logdebug("button not pressed")
	else:
		rospy.loginfo("Door Opened")



def listener():
    
    rospy.init_node('listener', anonymous=True)
    rospy.Subscriber("/elevator_button1_bumper/state", ContactsState, callback, queue_size=1)
    rospy.spin()

def move_door(side):

	door_closed = False
	req = ApplyJointEffortRequest()
	req.joint_name = 'joint_elevator_'+side
	req.start_time.secs = 0
	req.duration.secs = -10
	req.effort = 500
	rospy.loginfo("door is opening")
	res = apply_effort_service(req)

	rospy.sleep(10)
	req.effort = -1000
	rospy.loginfo("door is closing")
	res = apply_effort_service(req)

	rospy.sleep(10)
	req.effort = 500
	res = apply_effort_service(req)
	door_closed = True


if __name__ == '__main__':
    listener()




########NEW FILE########
__FILENAME__ = tf_publisher
#!/usr/bin/python
#################################################################
##\file
#
# \note
# Copyright (c) 2010 \n
# Fraunhofer Institute for Manufacturing Engineering
# and Automation (IPA) \n\n
#
#################################################################
#
# \note
# Project name: Care-O-bot Research
# \note
# ROS stack name: cob_environments
# \note
# ROS package name: cob_gazebo_worlds
#
# \author
# Author: Nadia Hammoudeh Garcia, email:nadia.hammoudeh-garcia@ipa.fhg.de
# \author
# Supervised by: Nadia Hammoudeh Garcia, email:nadia.hammoudeh-garcia@ipa.fhg.de
#
# \date Date of creation: Nov 2012
#
# \brief
# 
#
#################################################################
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer. \n
# - Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution. \n
# - Neither the name of the Fraunhofer Institute for Manufacturing
# Engineering and Automation (IPA) nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission. \n
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
# If not, see < http://www.gnu.org/licenses/>.
#
#################################################################  
import roslib
roslib.load_manifest('cob_gazebo_worlds')

import rospy
import tf
import math

if __name__ == '__main__':
    rospy.init_node('my_tf_broadcaster')
    br = tf.TransformBroadcaster()
    rate = rospy.Rate(10.0)
    while not rospy.is_shutdown():
        t = rospy.Time.now().to_sec()
        br.sendTransform((0,0,0.01),
                         (0.0, 0.0, 0.0, 1.0),
                         rospy.Time.now(),
                         "map",
                         "dummy_link")
        rate.sleep()

########NEW FILE########
