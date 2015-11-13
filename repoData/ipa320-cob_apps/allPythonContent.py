__FILENAME__ = base_test
#!/usr/bin/env python
import roslib; roslib.load_manifest('cob_component_test')
import sys
import time
import unittest
import rospy
import rostest
import actionlib
import time

from simple_script_server import *
from geometry_msgs.msg import *
from actionlib_msgs.msg import *
from move_base_msgs import *
from tf.transformations import *

NAME = 'cobbase_unit'
class UnitTest(unittest.TestCase):
    def __init__(self, *args):
        super(UnitTest, self).__init__(*args)
        rospy.init_node(NAME)
        self.sss=simple_script_server()
    #def setUp(self):
    #    self.errors = []
    def test_unit(self):
        # fetch parameters
        try:
            # time of test
            test_duration = float(rospy.get_param('~test_duration'))
            # x
            x = float(rospy.get_param('~x_value'))      
            # y
            y = float(rospy.get_param('~y_value'))      
            # theta
            theta = float(rospy.get_param('~theta_value'))      
        except KeyError, e:
            self.fail('cobunit not initialized properly')
        print """
              X: %s
              Y: %s
              Theta: %s
              Test duration:%s"""%(x, y, theta, test_duration)
        self._test_base(x, y, theta, test_duration)
        
    def _test_base(self, x, y, theta, test_duration): 
        self.assert_(test_duration > 0.0, "bad parameter (test_duration)")
        rospy.sleep(5.0)
        self.sss.init("arm")
        self.sss.move("arm","folded")
        #print "hello world"
        client = actionlib.SimpleActionClient('/move_base',MoveBaseAction)
        client_goal = MoveBaseGoal()
        pose = PoseStamped()
        pose.header.stamp = rospy.Time.now()
        pose.header.frame_id = "/map"
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = 0.0
        q = quaternion_from_euler(0, 0, theta)
        pose.pose.orientation.x = q[0]
        pose.pose.orientation.y = q[1]
        pose.pose.orientation.z = q[2]
        pose.pose.orientation.w = q[3]
        client_goal.target_pose = pose
        client.wait_for_server()
        client.send_goal(client_goal)
        while client.get_state() != 3:
        	rospy.sleep(1.0)
        	if client.get_state() == 0:
        		client.send_goal(client_goal)
         
if __name__ == '__main__':
    try:
        rostest.run('rostest', NAME, UnitTest, sys.argv)
    except KeyboardInterrupt, e:
        pass
    print "exiting"


########NEW FILE########
__FILENAME__ = grasp_test
#!/usr/bin/env python
import roslib
roslib.load_manifest('cob_component_test')

import sys
import time
import unittest
import rospy
import rostest
import actionlib
import tf

from simple_script_server import *
from gazebo.msg import *
from geometry_msgs.msg import *

from math import *

class UnitTest(unittest.TestCase):
    def __init__(self, *args):
        super(UnitTest, self).__init__(*args)
        rospy.init_node('grasp_test')
        self.message_received = False
        self.sss=simple_script_server()
        
    def setUp(self):
        self.errors = []
        
    def test_grasp(self):
        # get parameters
        # more can be included later
        try:
            # test duration
            if not rospy.has_param('~test_duration'):
                self.fail('Parameter test_duration does not exist on ROS Parameter Server')
            test_duration = rospy.get_param('~test_duration')
            
            # model name of object to grasp
            if not rospy.has_param('~grasp_object'):
                self.fail('Parameter grasp_object does not exist on ROS Parameter Server')
            grasp_object = rospy.get_param('~grasp_object')
        
        except KeyError, e:
            self.fail('Parameters not set properly')
        
        print """
            Test duration: %s
            Object to grasp: %s"""%(test_duration, grasp_object)
            
        # init subscribers
        sub_model_states = rospy.Subscriber("/gazebo/model_states", ModelStates, self.cb_model_states)
        sub_link_states = rospy.Subscriber("/gazebo/link_states", LinkStates, self.cb_link_states)
                
        # transformation handle        
        self.listener = tf.TransformListener(True, rospy.Duration(10.0))
        
        # check if grasp_object was spawned correctly
        self.sss.sleep(1)
        if grasp_object not in self.model_states.name:
            self.fail(grasp_object + " not spawned correctly")       
        
        # init components and check initialization
        components_to_init = ['arm', 'tray', 'sdh', 'torso', 'base'] 
        for component in components_to_init:
            init_component = self.sss.init(component)
            if init_component.get_error_code() != 0:
                error_msg = 'Could not initialize ' + component
                self.fail(error_msg)
                
        # move robot in position to grasp object
        handle_base = self.sss.move('base', 'kitchen', False)
        self.sss.move('tray', 'down', False)
        self.sss.move('arm', 'pregrasp', False)
        self.sss.move('sdh', 'cylopen', False)
        handle_base.wait()
        
        #TODO replace with object detection
        # get index of grasp_object in topic
        obj_index = self.model_states.name.index(grasp_object)
        
        # get index of arm_7_link in topic
        self.arm_7_link_index = self.link_states.name.index("arm_7_link")
        
        # transform object coordinates 
        grasp_obj = self.trans_into_arm_7_link(self.model_states.pose[obj_index].position)

        # TODO replace with controlles arm navigation
        # move to object
        self.sss.move_cart_rel("arm", [[0.0, 0.0, 0.2], [0.0, 0.0, 0.0]])
        # grasp object
        self.sss.move("sdh", "cylclosed")
        # lift object
        self.sss.move_cart_rel("arm", [[0.2, -0.1, -0.2], [0.0, 0.0, 0.0]])
               
        # check object position + status message
        self.check_pos(self.link_states.pose[self.arm_7_link_index].position, self.model_states.pose[obj_index].position, 0.5, "sdh in kitchen")

        # move arm over tray
        handle_arm = self.sss.move("arm", "grasp-to-tray", False)        
        # tray up
        self.sss.move("tray", "up")
        handle_arm.wait()

        # check object position + status message
        self.check_pos(self.link_states.pose[self.arm_7_link_index].position, self.model_states.pose[obj_index].position, 0.5, "sdh over tray")
        
		# put object onto tray
        self.sss.move_cart_rel("arm", [[-0.05, 0.0, 0.0], [0, 0, 0]])
        self.sss.move("sdh", "cylopen")
        
        # move base to table
        self.sss.move('base', [0, -0.5, 0])
        
        # check object position + status message
        des_pos_world = Point()
        des_pos_world.x = 0.3
        des_pos_world.y = -0.4
        des_pos_world.z = 0.885
        self.check_pos(des_pos_world, self.model_states.pose[obj_index].position, 0.5, "tray")
        
        # grasp objekt on tray
        self.sss.move("sdh", "cylclosed")
        
        # put object to final position
        self.sss.move("arm", "overtray")
        self.sss.move_cart_rel("arm", [[0.0, 0.0, -0.2], [0, 0, 0]])
        self.sss.move("arm", [[1.4272207239645427, -0.86918345596744029, -2.6785592907972724, -0.83566556448023821, 0.93072293274776374, 1.2925104647818602, -2.3042322384962883]])
        des_pos_world.x = 0.0
        des_pos_world.y = -1.2
        des_pos_world.z = 0.56  
        des_pos_arm_7_link = self.trans_into_arm_7_link(des_pos_world)
        # calculate the distance between object bottom and arm_7_link 
        x_dist_obj_arm_7_link = self.trans_into_arm_7_link(self.model_states.pose[obj_index].position).point.x
        self.sss.move_cart_rel("arm", [[(des_pos_arm_7_link.point.x - x_dist_obj_arm_7_link + 0.01), des_pos_arm_7_link.point.y, des_pos_arm_7_link.point.z], [0.0, 0.0, 0.0]])
        self.sss.move("sdh", "cylopen")
        
        # check object position + status message
        des_pos_world.z = 0.55
        self.check_pos(des_pos_world, self.model_states.pose[obj_index].position, 0.2, "table")
        
        self.sss.move_cart_rel("arm", [[0.5, 0.0, 0.0], [0.0, 0.0, 0.0]])
        self.sss.move("arm", "folded")
     
        
        
    # callback functions
    def cb_model_states(self, msg):
        self.model_states = msg
        
    def cb_link_states(self, msg):
        self.link_states = msg
        
    def check_pos(self, des_pos, act_pos, tolerance, pos_name):
        # function to check if object is at desired position
        distance = self.calc_dist(des_pos, act_pos)
        print >> sys.stderr, "Distance to '", pos_name, "': ", distance
        if distance >= tolerance:
            error_msg = "Object not at desired position '" + pos_name + "'"
            self.fail(error_msg)
        else:
            print >> sys.stderr, "Object in/on '", pos_name, "'"
        
    def calc_dist(self, des_pos, act_pos):
        # function to calculate distance between actual and desired object position
        distance = sqrt((des_pos.x - act_pos.x)**2 + (des_pos.y - act_pos.y)**2 + (des_pos.z - act_pos.z)**2)
        return distance
        
        
    def trans_into_arm_7_link(self, coord_world):
        # function to transform given coordinates into arm_7_link coordinates
        coord_arm_7_link = PointStamped()
        coord_arm_7_link.header.stamp = rospy.Time.now()
        coord_arm_7_link.header.frame_id = "/map"
        coord_arm_7_link.point = coord_world
        self.sss.sleep(2) # wait for transform to be calculated
        
        if not self.sss.parse:
            coord_arm_7_link = self.listener.transformPoint('/arm_7_link', coord_arm_7_link)
            # transform grasp point to sdh center
#            coord_arm_7_link.point.z = coord_arm_7_link.point.z - 0.2
        return coord_arm_7_link
            
        
if __name__ == '__main__':
    try:
        rostest.run('rostest', 'grasp_test', UnitTest, sys.argv)
    except KeyboardInterrupt, e:
        pass
    print "exiting"

########NEW FILE########
__FILENAME__ = grasp_test2
#!/usr/bin/env python
import roslib
roslib.load_manifest('cob_component_test')

import sys
import time
import unittest
import rospy
import rostest
import actionlib
import tf

from simple_script_server import *
from gazebo.msg import *
from geometry_msgs.msg import *

from math import *

class UnitTest(unittest.TestCase):
    def __init__(self, *args):
        super(UnitTest, self).__init__(*args)
        rospy.init_node('grasp_test')
        self.message_received = False
        self.sss=simple_script_server()

    def setUp(self):
        self.errors = []

    def test_grasp(self):
        # get parameters
        # more can be included later
        try:
            # test duration
            if not rospy.has_param('~test_duration'):
                self.fail('Parameter test_duration does not exist on ROS Parameter Server')
            test_duration = rospy.get_param('~test_duration')

            # model name of object to grasp
            if not rospy.has_param('~grasp_object'):
                self.fail('Parameter grasp_object does not exist on ROS Parameter Server')
            grasp_object = rospy.get_param('~grasp_object')

        except KeyError, e:
            self.fail('Parameters not set properly')

        print """
            Test duration: %s
            Object to grasp: %s"""%(test_duration, grasp_object)

        # init subscribers
        sub_model_states = rospy.Subscriber("/gazebo/model_states", ModelStates, self.cb_model_states)
        sub_link_states = rospy.Subscriber("/gazebo/link_states", LinkStates, self.cb_link_states)

        # transformation handle        
        self.listener = tf.TransformListener(True, rospy.Duration(10.0))

        # check if grasp_object was spawned correctly
        self.sss.sleep(1)
        if grasp_object not in self.model_states.name:
            self.fail(grasp_object + " not spawned correctly")

        # init components and check initialization
        components = ['arm', 'tray', 'sdh', 'torso', 'base'] 
        for comp in components:
            init_comp = self.sss.init(comp)
            if init_comp.get_error_code() != 0:
                error_msg = self.get_error_msg(init_comp)
                self.fail(error_msg) 

        # move robot in position to grasp object
        handle_base = self.sss.move('base', 'kitchen', False)
        handle_tray = self.sss.move('tray', 'down', False)
        handle_arm = self.sss.move('arm', 'pregrasp', False)
        handle_sdh = self.sss.move('sdh', 'cylopen', False)
        handle_torso = self.sss.move('torso', 'home', False)
        handle_base.wait()
        
        # check position 
#        commented out till problems with causeless errors are solved
#        for handle in [handle_base, handle_tray, handle_arm, handle_sdh, handle_torso]:
#            if handle.get_error_code() != 0:
#                error_msg = "Cob didn't reach initial position in kitchen" + "\n" + self.get_error_msg(handle)
#                self.fail(error_msg)

        # TODO replace with object detection
#        handel_detect = self.sss.detect(grasp_object)
#        detected_object_pose = self.sss.get_object_pose(grasp_object)
#        grasp_obj = self.trans_into_arm_7_link(detected_object_pose)

#------------------------------------------------------------------------------
        # get index of grasp_object in topic
        obj_index = self.model_states.name.index(grasp_object)

        # get index of arm_7_link in topic
        self.arm_7_link_index = self.link_states.name.index("arm_7_link")

        # transform object coordinates 
        grasp_obj = self.trans_into_arm_7_link(self.model_states.pose[obj_index].position)
#------------------------------------------------------------------------------

        # transform grasp point to sdh center
        grasp_obj.point.z = grasp_obj.point.z - 0.17

        # TODO replace with controlled arm navigation
        # move in front of object
        handle_arm1 = self.sss.move_cart_rel("arm", [[grasp_obj.point.x + 0.05, grasp_obj.point.y, grasp_obj.point.z - 0.2], [0.0, 0.0, 0.0]])
        # move to object
        handle_arm2 = self.sss.move_cart_rel("arm", [[0.0, 0.0, 0.2], [0.0, 0.0, 0.0]])
        # grasp object
        handle_sdh = self.sss.move("sdh", "cylclosed")
        # lift object
        handle_arm3 = self.sss.move_cart_rel("arm", [[0.2, -0.1, -0.3], [0.0, 0.0, 0.0]])

        # check object position
        if not self.at_des_pos(self.link_states.pose[self.arm_7_link_index].position, self.model_states.pose[obj_index].position, 0.5, "sdh in kitchen"):
            err_msgs = self.gen_error_msgs("sdh in kitchen", handle_arm1, handle_arm2, handle_sdh, handle_arm3)
            self.fail(err_msgs)

        # move arm over tray
        handle_arm = self.sss.move("arm", "grasp-to-tray", False)        
        # tray up
        handle_tray = self.sss.move("tray", "up")
        handle_arm.wait()

        # check object position
        if not self.at_des_pos(self.link_states.pose[self.arm_7_link_index].position, self.model_states.pose[obj_index].position, 0.5, "sdh over tray"):
            err_msgs = self.gen_error_msgs("sdh over tray", handle_arm, handle_tray)
            self.fail(err_msgs)

        # put object onto tray
        # calculate distance to move down (current height - tray height - 1/2 milkbox height - offset)
        dist_to_tray = self.model_states.pose[obj_index].position.z - 0.84 - 0.1 - 0.03 
        handle_arm = self.sss.move_cart_rel("arm", [[-dist_to_tray, 0.0, 0.0], [0, 0, 0]])
        handle_sdh = self.sss.move("sdh", "cylopen")

        # move base to table
        handle_base = self.sss.move('base', [0, -0.5, 0])

        # check object position
        des_pos_world = Point()
        des_pos_world.x = 0.3
        des_pos_world.y = -0.4
        des_pos_world.z = 0.84 + 0.1 # tray height + 1/2 milkbox height
        if not self.at_des_pos(des_pos_world, self.model_states.pose[obj_index].position, 0.5, "tray"):
            err_msgs = self.gen_error_msgs("tray", handle_arm, handle_sdh, handle_base)
            self.fail(err_msgs)

        # grasp objekt on tray
        # transform object coordinates 
        grasp_obj = self.trans_into_arm_7_link(self.model_states.pose[obj_index].position)
        # transform grasp point to sdh center
        grasp_obj.point.z = grasp_obj.point.z - 0.17
        handle_arm = self.sss.move_cart_rel("arm", [[grasp_obj.point.x, grasp_obj.point.y, grasp_obj.point.z], [0, 0, 0]])
        handle_sdh = self.sss.move("sdh", "cylclosed")
        
        # check object position
        if not self.at_des_pos(self.link_states.pose[self.arm_7_link_index].position, self.model_states.pose[obj_index].position, 0.5, "sdh over tray"):
            err_msgs = self.gen_error_msgs("sdh over tray", handle_arm, handle_sdh)
            self.fail(err_msgs)

        # put object to final position
        # TODO replace with controlled arm navigation
        handle_arm1 = self.sss.move("arm", "overtray")
        handle_arm2 = self.sss.move_cart_rel("arm", [[0.0, 0.0, -0.2], [0, 0, 0]])
        handle_arm3 = self.sss.move("arm", [[1.5620375327333056, -0.59331108071630467, -2.9678321245253576, -0.96655272071376164, 1.2160753390569674, 1.4414846837499029, -2.2174714029417704]])
        des_pos_world.x = 0.0
        des_pos_world.y = -1.2
        des_pos_world.z = 0.56 + 0.1
        des_pos_arm_7_link = self.trans_into_arm_7_link(des_pos_world)
        # calculate the distance between object origin and arm_7_link 
        x_dist_obj_arm_7_link = self.trans_into_arm_7_link(self.model_states.pose[obj_index].position).point.x
        handle_arm4 = self.sss.move_cart_rel("arm", [[(des_pos_arm_7_link.point.x - x_dist_obj_arm_7_link + 0.03), des_pos_arm_7_link.point.y, des_pos_arm_7_link.point.z], [0.0, 0.0, 0.0]])
        handle_sdh = self.sss.move("sdh", "cylopen")
        
        # check object position
        des_pos_world.z = 0.55
        if not self.at_des_pos(des_pos_world, self.model_states.pose[obj_index].position, 0.3, "table"):
            err_msgs = self.gen_error_msgs("table", handle_arm1, handle_arm2, handle_arm3, handle_sdh, handle_arm4)
            self.fail(err_msgs)
        
        self.sss.move_cart_rel("arm", [[0.5, 0.0, 0.0], [0.0, 0.0, 0.0]])
        self.sss.move("arm", "folded")


    # callback functions
    def cb_model_states(self, msg):
        self.model_states = msg
        
    def cb_link_states(self, msg):
        self.link_states = msg
        
    def at_des_pos(self, des_pos, act_pos, tolerance, pos_name):
        # function to check if object is at desired position
        distance = self.calc_dist(des_pos, act_pos)
        print >> sys.stdout, "Distance to '", pos_name, "': ", distance
        if distance >= tolerance:
            return False
        else:
            return True

    def calc_dist(self, des_pos, act_pos):
        # function to calculate distance between actual and desired object position
        distance = sqrt((des_pos.x - act_pos.x)**2 + (des_pos.y - act_pos.y)**2 + (des_pos.z - act_pos.z)**2)
        return distance


    def trans_into_arm_7_link(self, coord_world):
        # function to transform given coordinates into arm_7_link coordinates
        coord_arm_7_link = PointStamped()
        coord_arm_7_link.header.stamp = rospy.Time.now()
        coord_arm_7_link.header.frame_id = "/map"
        coord_arm_7_link.point = coord_world
        self.sss.sleep(2) # wait for transform to be calculated

        if not self.sss.parse:
            coord_arm_7_link = self.listener.transformPoint('/arm_7_link', coord_arm_7_link)
        return coord_arm_7_link
        
    def gen_error_msgs(self, des_pos, *handles):
        # function to generate a error message consisting all error messages of the given handles
        error_msgs = "Object not at desired position: " + des_pos
        for handle in handles:
            if self.get_error_msg(handle) != "worked":
                error_msgs = error_msgs + "\n" + self.get_error_msg(handle)
        return error_msgs 

    def get_error_msg(self, handle):
        # function to get error message depending on error code
        err_code = handle.get_error_code()
        if err_code == 0:
            error_msg = "worked"
        else:
            error_msg = "Error: could not " + handle.function_name + " " + handle.component_name 
            if err_code == 1:
                error_msg = error_msg + "\n" + "service call failed"
            elif err_code == 2:
                error_msg = error_msg + "\n" + "parameters are not on parameter server"
            elif err_code == 3:
                error_msg = error_msg + "\n" + "parameter type or dimension is wrong"
            elif err_code == 4:
                error_msg = error_msg + "\n" + "server or service is not available"
            elif err_code == 10:
                error_msg = error_msg + "\n" + "exceeded timeout"
            elif err_code == 11:
                error_msg = error_msg + "\n" + "didn't reach goal position"
            elif err_code == 12:
                error_msg = error_msg + "\n" + "no object detected"
        return error_msg

if __name__ == '__main__':
    try:
        rostest.run('rostest', 'grasp_test', UnitTest, sys.argv)
    except KeyboardInterrupt, e:
        pass
    print "exiting"

########NEW FILE########
__FILENAME__ = grasp_test_obj_detect
#!/usr/bin/env python
import roslib
roslib.load_manifest('cob_component_test')
#roslib.load_manifest('cob_script_server')

import sys
import time
import unittest
import rospy
import rostest
import actionlib
import tf
#import cob_gazebo

from simple_script_server import *
from gazebo.msg import *
from geometry_msgs.msg import *

from math import *

class UnitTest(unittest.TestCase):
    def __init__(self, *args):
        super(UnitTest, self).__init__(*args)
        rospy.init_node('grasp_test')
        self.message_received = False
        self.sss=simple_script_server()
        
    def setUp(self):
        self.errors = []
        
    def test_grasp(self):
        # get parameters
        # more can be included later
        try:
            # test duration
            if not rospy.has_param('~test_duration'):
                self.fail('Parameter test_duration does not exist on ROS Parameter Server')
            test_duration = rospy.get_param('~test_duration')
            
            # model name of object to grasp
            if not rospy.has_param('~grasp_object'):
                self.fail('Parameter grasp_object does not exist on ROS Parameter Server')
            grasp_object = rospy.get_param('~grasp_object')
        
        except KeyError, e:
            self.fail('Parameters not set properly')
        
        print """
            Test duration: %s
            Object to grasp: %s"""%(test_duration, grasp_object)
            
        # init subscribers
        sub_model_states = rospy.Subscriber("/gazebo/model_states", ModelStates, self.cb_model_states)
        sub_link_states = rospy.Subscriber("/gazebo/link_states", LinkStates, self.cb_link_states)
                
        # transformation handle        
        self.listener = tf.TransformListener(True, rospy.Duration(10.0))
        
        # init components and check initialization
        components_to_init = ['arm', 'tray', 'sdh', 'torso', 'base'] 
        for component in components_to_init:
            init_component = self.sss.init(component)
            if init_component.get_error_code() != 0:
                error_msg = 'Could not initialize ' + component
                self.fail(error_msg)
         
        # check if grasp_object was spawned correctly
        if grasp_object not in self.model_states.name:
            self.fail(grasp_object + " not spawned correctly")
            
#        # get index of grasp_object in topic
#        obj_index = self.model_states.name.index(grasp_object)
        
        # get index of arm_7_link in topic
        self.arm_7_link_index = self.link_states.name.index("arm_7_link")
             
        # move robot in position to grasp object
        handle_base = self.sss.move('base', 'kitchen', False)
        self.sss.move('tray', 'down', False)
        self.sss.move('arm', 'pregrasp', False)
        self.sss.move('sdh', 'cylopen', False)
        handle_base.wait()
        
        # detect object
        self.sss.detect('milk')
        milk_box = PoseStamped()
        milk_box = self.sss.get_object_pose('milk')
        
        # transform object coordinates 
        self.sss.sleep(2)
        grasp_obj = self.trans_into_arm_7_link(self.model_states.pose[obj_index].position)
        
        # move in front of object
        pregrasp_distance = 0.03
        grasp_offset = 0.17 # offset between arm_7_link and sdh_grasp_link
#        self.sss.move_cart_rel("arm", [[0.03, grasp_obj.point.y - 0.02, (grasp_obj.point.z - grasp_offset - 0.4)], [0.0, 0.0, 0.0]])
        # move to object
#        self.sss.move_cart_rel("arm", [[0.0, 0.0, 0.22], [0.0, 0.0, 0.0]])
        self.sss.move_cart_rel("arm", [[0.0, 0.0, 0.2], [0.0, 0.0, 0.0]])
        
        # grasp object
        self.sss.move("sdh", "cylclose")
        # lift object
        self.sss.move_cart_rel("arm", [[0.2, -0.1, -0.2], [0.0, 0.0, 0.0]])
               
        # check object position + status message
        self.check_pos(self.link_states.pose[self.arm_7_link_index].position, self.model_states.pose[obj_index].position, 0.5, "sdh in kitchen")

        # move arm over tray
        handle_arm = self.sss.move("arm", "grasp-to-tray", False)        
        # tray up
        self.sss.move("tray", "up")
        handle_arm.wait()

        # check object position + status message
        self.check_pos(self.link_states.pose[self.arm_7_link_index].position, self.model_states.pose[obj_index].position, 0.5, "sdh over tray")
        
		# put object onto tray
        self.sss.move_cart_rel("arm", [[-0.05, 0.0, 0.0], [0, 0, 0]])
        self.sss.move("sdh", "cylopen")
        
        # base kitchen
        self.sss.move('base', [0, -0.5, 0])
        
        # check object position + status message
        des_pos_world = Point()
        des_pos_world.x = 0.3
        des_pos_world.y = -0.4
        des_pos_world.z = 0.885
        self.check_pos(des_pos_world, self.model_states.pose[obj_index].position, 0.5, "tray")
        
        # grasp objekt on tray
        self.sss.move("sdh", "cylclose")
        
        # put object to final position
        self.sss.move("arm", "overtray")
        self.sss.move_cart_rel("arm", [[0.0, 0.0, -0.2], [0, 0, 0]])
        self.sss.move("arm", [[1.4272207239645427, -0.86918345596744029, -2.6785592907972724, -0.83566556448023821, 0.93072293274776374, 1.2925104647818602, -2.3042322384962883]])
        des_pos_world.x = 0.0
        des_pos_world.y = -1.2
        des_pos_world.z = 0.56  
        des_pos_arm_7_link = self.trans_into_arm_7_link(des_pos_world)
        # calculate the distance between object bottom and arm_7_link 
        x_dist_obj_arm_7_link = self.trans_into_arm_7_link(self.model_states.pose[obj_index].position).point.x
        self.sss.move_cart_rel("arm", [[(des_pos_arm_7_link.point.x - x_dist_obj_arm_7_link + 0.01), des_pos_arm_7_link.point.y, des_pos_arm_7_link.point.z], [0.0, 0.0, 0.0]])
        self.sss.move("sdh", "cylopen")
        
        # check object position + status message
        des_pos_world.z = 0.55
        self.check_pos(des_pos_world, self.model_states.pose[obj_index].position, 0.2, "table")
        
        self.sss.move_cart_rel("arm", [[0.5, 0.0, 0.0], [0.0, 0.0, 0.0]])
        self.sss.move("arm", "folded")
     
        
        
    # callback functions
    def cb_model_states(self, msg):
        self.model_states = msg
        
    def cb_link_states(self, msg):
        self.link_states = msg
        
    def check_pos(self, des_pos, act_pos, tolerance, pos_name):
        # function to check if object is at desired position
        distance = self.calc_dist(des_pos, act_pos)
        if distance >= tolerance:
            error_msg = "Object not at desired position '" + pos_name + "'"
            self.fail(error_msg)
        else:
            print >> sys.stderr, "Object in/on '", pos_name, "'"
        print >> sys.stderr, "Distance to '", pos_name, "': ", distance
        
    def calc_dist(self, des_pos, act_pos):
        # function to calculate distance between actual and desired object position
        distance = sqrt((des_pos.x - act_pos.x)**2 + (des_pos.y - act_pos.y)**2 + (des_pos.z - act_pos.z)**2)
        return distance
        
        
    def trans_into_arm_7_link(self, coord_world):
        # function to transform given coordinates into arm_7_link coordinates
        coord_arm_7_link = PointStamped()
        coord_arm_7_link.header.stamp = rospy.Time.now()
        coord_arm_7_link.header.frame_id = "/map"
        coord_arm_7_link.point = coord_world
        self.sss.sleep(2) # wait for transform to be calculated
        
        if not self.sss.parse:
            coord_arm_7_link = self.listener.transformPoint('/arm_7_link', coord_arm_7_link)
            # transform grasp point to sdh center
#            coord_arm_7_link.point.z = coord_arm_7_link.point.z - 0.2
        return coord_arm_7_link
            
        
if __name__ == '__main__':
    try:
        rostest.run('rostest', 'grasp_test', UnitTest, sys.argv)
    except KeyboardInterrupt, e:
        pass
    print "exiting"

########NEW FILE########
__FILENAME__ = trajectory_test
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
from pr2_controllers_msgs.msg import *

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
        
#       following if-clause is commented out due to problems occuring while using test in gazebo          
#        if move_handle.get_error_code() != 0:
#            error_msg = 'Could not move ' + component
#            self.fail(error_msg + "; errorCode: " + str(move_handle.get_error_code()))
        
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
