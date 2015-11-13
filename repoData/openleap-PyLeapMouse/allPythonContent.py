__FILENAME__ = FingerControl
#William Yager
#Leap Python mouse controller POC
#This file is for pointer-finger-based control (--finger and default)


import math
import sys
from leap import Leap, Mouse
from MiscFunctions import *


class Finger_Control_Listener(Leap.Listener):  #The Listener that we attach to the controller. This listener is for pointer finger movement
    def __init__(self, mouse, smooth_aggressiveness=8, smooth_falloff=1.3):
        super(Finger_Control_Listener, self).__init__()  #Initialize like a normal listener
        #Initialize a bunch of stuff specific to this implementation
        self.screen = None
        self.screen_resolution = (1920,1080)
        self.cursor = mouse.absolute_cursor()  #The cursor object that lets us control mice cross-platform
        self.mouse_position_smoother = mouse_position_smoother(smooth_aggressiveness, smooth_falloff) #Keeps the cursor from fidgeting
        self.mouse_button_debouncer = debouncer(5)  #A signal debouncer that ensures a reliable, non-jumpy click
        self.most_recent_pointer_finger_id = None  #This holds the ID of the most recently used pointing finger, to prevent annoying switching

    def on_init(self, controller):
        print "Initialized"

    def on_connect(self, controller):
        print "Connected"

    def on_disconnect(self, controller):
        print "Disconnected"

    def on_exit(self, controller):
        print "Exited"

    def on_frame(self, controller):
        frame = controller.frame()  #Grab the latest 3D data
        finger = frame.fingers.frontmost
        stabilizedPosition = finger.stabilized_tip_position
        interactionBox = frame.interaction_box
        normalizedPosition = interactionBox.normalize_point(stabilizedPosition)
        if finger.touch_zone > 0:
            finger_count = len(frame.fingers)
            if finger.touch_zone == 1:
                self.cursor.set_left_button_pressed(False)
                if finger_count < 5:
                    self.cursor.move(normalizedPosition.x * self.screen_resolution[0], self.screen_resolution[1] - normalizedPosition.y * self.screen_resolution[1])
                elif finger_count == 5:
                    finger_velocity = finger.tip_velocity
                    x_scroll = self.velocity_to_scroll_amount(finger_velocity.x)
                    y_scroll = self.velocity_to_scroll_amount(finger_velocity.y)
                    self.cursor.scroll(x_scroll, y_scroll)
                else:
                    print "Finger count: %s" % finger_count
            elif finger.touch_zone == 2:
                if finger_count == 1:
                    self.cursor.set_left_button_pressed(True)
                elif finger_count == 2:
                    self.cursor.set_left_button_pressed(True)
                    self.cursor.move(normalizedPosition.x * self.screen_resolution[0], self.screen_resolution[1] - normalizedPosition.y * self.screen_resolution[1])
        #if(finger.touch_distance > -0.3 and finger.touch_zone != Leap.Pointable.ZONE_NONE):
	    #self.cursor.set_left_button_pressed(False)
	    #self.cursor.move(normalizedPosition.x * self.screen_resolution[0], self.screen_resolution[1] - normalizedPosition.y * self.screen_resolution[1])
        #elif(finger.touch_distance <= -0.4):
            #self.cursor.set_left_button_pressed(True)
        #    print finger.touch_distance

    def do_scroll_stuff(self, hand):  #Take a hand and use it as a scroller
        fingers = hand.fingers  #The list of fingers on said hand
        if not fingers.is_empty:  #Make sure we have some fingers to work with
            sorted_fingers = sort_fingers_by_distance_from_screen(fingers)  #Prioritize fingers by distance from screen
            finger_velocity = sorted_fingers[0].tip_velocity  #Get the velocity of the forwardmost finger
            x_scroll = self.velocity_to_scroll_amount(finger_velocity.x)
            y_scroll = self.velocity_to_scroll_amount(finger_velocity.y)
            self.cursor.scroll(x_scroll, y_scroll)

    def velocity_to_scroll_amount(self, velocity):  #Converts a finger velocity to a scroll velocity
        #The following algorithm was designed to reflect what I think is a comfortable
        #Scrolling behavior.
        vel = velocity  #Save to a shorter variable
        vel = vel + math.copysign(300, vel)  #Add/subtract 300 to velocity
        vel = vel / 150
        vel = vel ** 3  #Cube vel
        vel = vel / 8
        vel = vel * -1  #Negate direction, depending on how you like to scroll
        return vel

    def do_mouse_stuff(self, hand):  #Take a hand and use it as a mouse
        fingers = hand.fingers  #The list of fingers on said hand
        if not fingers.is_empty:  #Make sure we have some fingers to work with
            pointer_finger = self.select_pointer_finger(fingers)  #Determine which finger to use
            
            try:
                intersection = self.screen.intersect(pointer_finger, True)  #Where the finger projection intersects with the screen
                if not math.isnan(intersection.x) and not math.isnan(intersection.y):  #If the finger intersects with the screen
                    x_coord = intersection.x * self.screen_resolution[0]  #x pixel of intersection
                    y_coord = (1.0 - intersection.y) * self.screen_resolution[1]  #y pixel of intersection
                    x_coord,y_coord = self.mouse_position_smoother.update((x_coord,y_coord)) #Smooth movement
                    self.cursor.move(x_coord,y_coord)  #Move the cursor
                    if has_thumb(hand):  #We've found a thumb!
                        self.mouse_button_debouncer.signal(True)  #We have detected a possible click. The debouncer ensures that we don't have click jitter
                    else:
                        self.mouse_button_debouncer.signal(False)  #Same idea as above (but opposite)

                    if self.cursor.left_button_pressed != self.mouse_button_debouncer.state:  #We need to push/unpush the cursor's button
                        self.cursor.set_left_button_pressed(self.mouse_button_debouncer.state)  #Set the cursor to click/not click
            except Exception as e:
                print e

    def select_pointer_finger(self, possible_fingers):  #Choose the best pointer finger
        sorted_fingers = sort_fingers_by_distance_from_screen(possible_fingers)  #Prioritize fingers by distance from screen
        if self.most_recent_pointer_finger_id != None:  #If we have a previous pointer finger in memory
             for finger in sorted_fingers:  #Look at all the fingers
                if finger.id == self.most_recent_pointer_finger_id:  #The previously used pointer finger is still in frame
                    return finger  #Keep using it
        #If we got this far, it means we don't have any previous pointer fingers OR we didn't find the most recently used pointer finger in the frame
        self.most_recent_pointer_finger_id = sorted_fingers[0].id  #This is the new pointer finger
        return sorted_fingers[0]

########NEW FILE########
__FILENAME__ = Geometry
#William Yager
#Leap Python mouse controller POC


import math
from leap import Leap


def to_vector(leap_vector):
    return vector(leap_vector.x, leap_vector.y, leap_vector.z)


class vector(object):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
    def __add__(self, other):
        return vector(self.x + other.x, self.y+other.y, self.z+other.z)
    def __sub__(self, other):
        return vector(self.x - other.x, self.y - other.y, self.z - other.z)
    def __mul__(self, other):  #The * operator is dot product
        return self.dot(other)
    def dot(self, other):
        return self.x*other.x + self.y*other.y+self.z*other.z
    def __pow__(self, other):  #The ** operator allows us to multiply a vector by a scalar
        return self.scalar_mult(other)
    def scalar_mult(self, other):
        return vector(self.x * other, self.y*other, self.z*other)
    def cross(self, other):
        x = self.y * other.z - other.y * self.z
        y = -(self.x * other.z - other.x * self.z)
        z = self.x * other.y - other.x * self.y
        return vector(x,y,z)
    def __mod__(self, other):  #The % operator is cross product
        return self.cross(other)
    def norm(self):  #Length of self
        return math.sqrt(1.0*self.dot(self))
    def distance(self, other):
        return (self-other).norm()  #Find difference and then the length of it
    def unit_vector(self):
        magnitude = self.norm()
        return vector(1.0*self.x/magnitude, 1.0*self.y/magnitude, 1.0*self.z/magnitude)
    def to_leap(self):
        return Leap.Vector(self.x, self.y, self.z)
    def pitch(self):
        return math.atan(1.0*self.z/self.y)
    def roll(self):
        return math.atan(1.0*self.x/self.y)
    def yaw(self):
        return math.atan(1.0*self.x/self.z)


class segment(object):
    def __init__(self, point1, point2):
        self.point1 = point1
        self.point2 = point2
    #Shortest distance code based off of http://geomalgorithms.com/a07-_distance.html
    def min_distance_infinite(self, other):  #Return shortest distance between two lines
        u = self.point2 - self.point1
        v = other.point2 - other.point1
        w = self.point1 - other.point1
        a = u * u
        b = u * v
        c = v * v
        d = u * w
        e = v * w
        D = a * c - b * b
        sc = 0.0
        tc = 0.0
        basically_zero = .000000001
        if D < basically_zero:
            sc = 0.0
            if b > c:
                tc = d/b
            else:
                tc = e/c
        else:
            sc = (b * e - c * d) / D
            tc = (a * e - b * d) / D
        dP = w + u**sc - v**tc
        return dP.norm()
    def min_distance_finite(self, other):  #Return shortest distance between two segments
        u = self.point2 - self.point1
        v = other.point2 - other.point1
        w = self.point1 - other.point1
        a = u * u  #* here is cross product
        b = u * v
        c = v * v
        d = u * w
        e = v * w
        D = a * c - b * b
        sc = 0.0
        sN = 0.0
        sD = D
        tc = 0.0
        tN = 0.0
        tD = D
        basically_zero = .000000001
        if D < basically_zero:
            sN = 0.0
            sD = 1.0
            tN = e
            tD = c
        else:
            sN = (b*e - c*d)
            tN = (a*e - b*d)
            if sN < 0.0:
                sN = 0.0
                tN = e
                tD = c
            elif sN > sD:
                sN = sD
                tN = e + b
                tD = c
        if(tN < 0.0):
            tN = 0.0
            if(-d < 0.0):
                sN = 0.0
            elif (-d > a):
                sN = sD
            else:
                sN = -d
                sD = a
        elif tN > tD:
            tN = tD
            if (-d + b) < 0.0:
                sN = 0
            elif (-d + b) > a:
                sN = sD
            else:
                sN = (-d + b)
                sD = a
        if abs(sN) < basically_zero:
            sc = 0
        else:
            sc = sN / sD
        if abs(tN) < basically_zero:
            tc = 0.0
        else:
            tc = tN / tD
        dP = w + u**sc - v**tc  #I'm pretty sure dP is the actual vector linking the lines
        return dP.norm()


class line(segment):
    def __init__(self, point1, direction_vector):
        self.point1 = point1
        self.direction = direction_vector.unit_vector()
        self.point2 = point1 + self.direction


def angle_between_vectors(vector1, vector2):
    #cos(theta)=dot product / (|a|*|b|)
    top = vector1 * vector2  #* is dot product
    bottom = vector1.norm() * vector2.norm()
    angle = math.acos(top/bottom)
    return angle  #In radians

########NEW FILE########
__FILENAME__ = leap
import sys
if sys.platform == "darwin":
    import OSX.Leap as Leap
    import OSX.Mouse as Mouse
    from OSX.Leap import CircleGesture, KeyTapGesture, ScreenTapGesture, SwipeGesture
elif 'linux' in sys.platform:
    import Linux.Leap as Leap
    import Linux.Mouse as Mouse
    from Linux.Leap import CircleGesture, KeyTapGesture, ScreenTapGesture, SwipeGesture
else:
    import Windows.Leap as Leap
    import Windows.Mouse as Mouse
    from Windows.Leap import CircleGesture, KeyTapGesture, ScreenTapGesture, SwipeGesture

########NEW FILE########
__FILENAME__ = Mouse
from pymouse import PyMouse
mouse = PyMouse()

def AbsoluteMouseMove(posx,posy):
    print 'move to', posx, posy
    mouse.move(int(posx), int(posy))

def AbsoluteMouseClick(posx,posy):
    print 'click on ', posx, posy
    mouse.click(posx, posy)

def AbsoluteMouseClickDown(posx, posy):
    print 'left button down'
    mouse.press(posx, posy)

def AbsoluteMouseClickUp(posx, posy):
    print 'left button up'
    mouse.release(posx, posy)

def AbsoluteMouseDrag(posx, posy):  #Only relevant in OS X(?)
    mouse.move(posx, posy)

def AbsoluteMouseRightClick(posx,posy):
    mouse.click(posx, posy, button=2)

def AbsoluteMouseScroll(posx, posy, up=True):  #PyUserInput doesn't appear to support relative scrolling
    if up is True:
        mouse.click(posx, posy, button=4)
    elif up is False:
        mouse.click(posx, posy, button=5)
    #When PyUserInput > 0.1.5 is released, the following will work:
    #mouse.scroll(posx, posy, up)

def GetDisplayWidth():
    return mouse.screen_size()[0]

def GetDisplayHeight():
    return mouse.screen_size()[1]


#A cursor that does commands based on absolute position (good for finger pointing)
class absolute_cursor(object):
    def __init__(self):
        self.x_max = GetDisplayWidth() - 1
        self.y_max = GetDisplayHeight() - 1
        self.left_button_pressed = False
        self.x = 0
        self.y = 0

    def move(self, posx, posy):  #Move to coordinates
        self.x = posx
        self.y = posy
        if self.x > self.x_max:
            self.x = self.x_max
        if self.y > self.y_max:
            self.y = self.y_max
        if self.x < 0.0:
            self.x = 0.0
        if self.y < 0.0:
            self.y = 0.0
        if self.left_button_pressed:  #We are dragging
            AbsoluteMouseDrag(self.x, self.y)
        else:  #We are not dragging
            AbsoluteMouseMove(self.x, self.y)

    def click(self, posx=None, posy=None):  #Click at coordinates (current coordinates by default)
        if posx == None:
            posx = self.x
        if posy == None:
            posy = self.y
        AbsoluteMouseClick(posx, posy)

    def set_left_button_pressed(self, boolean_button):  #Set the state of the left button
        if boolean_button == True:  #Pressed
            self.click_down()
        else:  #Not pressed
            self.click_up()

    def click_down(self, posx=None, posy=None):
        if posx == None:
            posx = self.x
        if posy == None:
            posy = self.y
        AbsoluteMouseClickDown(posx, posy)
        self.left_button_pressed = True

    def click_up(self, posx=None, posy=None):
        if posx == None:
            posx = self.x
        if posy == None:
            posy = self.y
        AbsoluteMouseClickUp(posx, posy)
        self.left_button_pressed = False

    def rightClick(self, posx=None, posy=None):
        if posx == None:
            posx = self.x
        if posy == None:
            posy = self.y
        AbsoluteMouseRightClick(posx, posy)

    def scroll(self, x_movement, y_movement):
        posx = self.x
        posy = self.y
        up = False
        if y_movement < 0:
            up = True
        AbsoluteMouseScroll(posx, posy, up)


#Allows for relative movement instead of absolute movement. This implementation is not a "true" relative mouse,
#but is really just a relative wrapper for an absolute mouse. Not the best way to do it, but I need to
#figure out how to send raw "mouse moved _this amount_" events. This class is (as of writing) untested.
#It's only here in case someone else wants to figure out how to do this properly on OS X.
#I will be "actually" implementing this on Windows shortly. OSX TBD.
class relative_cursor(absolute_cursor):
    def __init__(self):
        absolute_cursor.__init__(self)

    def move(self, x_amt, y_amt):
        self.x = self.x + x_amt
        self.y = self.y + y_amt
        if self.x > self.x_max:
            self.x = self.x_max
        if self.y > self.y_max:
            self.y = self.y_max
        if self.x < 0.0:
            self.x = 0.0
        if self.y < 0.0:
            self.y = 0.0
        if self.left_button_pressed:  #We are dragging
            AbsoluteMouseDrag(self.x, self.y)
        else:  #We are not dragging
            AbsoluteMouseMove(self.x, self.y)

########NEW FILE########
__FILENAME__ = MiscFunctions
#William Yager
#Leap Python mouse controller POC
#This file contains miscellaneous functions that are not interface-specific


import math
from leap import Leap
import Geometry

#Smooths the mouse's position
class mouse_position_smoother(object):
    def __init__(self, smooth_aggressiveness, smooth_falloff):
        #Input validation
        if smooth_aggressiveness < 1:
            raise Exception("Smooth aggressiveness must be greater than 1.")
        if smooth_falloff < 1:
            raise Exception("Smooth falloff must be greater than 1.0.")
        self.previous_positions = []
        self.smooth_falloff = smooth_falloff
        self.smooth_aggressiveness = int(smooth_aggressiveness)
    def update(self, (x,y)):
        self.previous_positions.append((x,y))
        if len(self.previous_positions) > self.smooth_aggressiveness:
            del self.previous_positions[0]
        return self.get_current_smooth_value()
    def get_current_smooth_value(self):
        smooth_x = 0
        smooth_y = 0
        total_weight = 0
        num_positions = len(self.previous_positions)
        for position in range(0, num_positions):
            weight = 1 / (self.smooth_falloff ** (num_positions - position))
            total_weight += weight
            smooth_x += self.previous_positions[position][0] * weight
            smooth_y += self.previous_positions[position][1] * weight
        smooth_x /= total_weight
        smooth_y /= total_weight
        return smooth_x, smooth_y

class debouncer(object):  #Takes a binary "signal" and debounces it.
    def __init__(self, debounce_time):  #Takes as an argument the number of opposite samples it needs to debounce.
        self.opposite_counter = 0  #Number of contrary samples vs agreeing samples.
        self.state = False  #Default state.
        self.debounce_time = debounce_time  #Number of samples to change states (debouncing threshold).

    def signal(self, value):  #Update the signal.
        if value != self.state:  #We are receiving a different signal than what we have been.
            self.opposite_counter = self.opposite_counter + 1
        else:  #We are recieving the same signal that we have been
            self.opposite_counter = self.opposite_counter - 1

        if self.opposite_counter < 0: self.opposite_counter = 0
        if self.opposite_counter > self.debounce_time: self.opposite_counter = self.debounce_time
        #No sense building up negative or huge numbers of agreeing/contrary samples

        if self.opposite_counter >= self.debounce_time:  #We have seen a lot of evidence that our internal state is wrong
            self.state = not self.state  #Change internal state
            self.opposite_counter = 0  #We reset the number of contrary samples
        return self.state  #Return the debounced signal (may help keep code cleaner)


class n_state_debouncer(object):  #A signal debouncer that has `number_of_states` states
    def __init__(self, debounce_time, number_of_states):
        self.state_counters = [0]*number_of_states  #One counter for every state
        self.state = 0  #Default state
        self.debounce_time = debounce_time

    def signal(self, signal_value):
        if signal_value < 0 or signal_value >= len(self.state_counters):  #Check for invalid state
            raise Exception("Invalid state. Out of bounds.")
            return
        self.state_counters[signal_value] = self.state_counters[signal_value] + 1  #Increment signalled state
        for i in range(0,len(self.state_counters)):
            if i is not signal_value: self.state_counters[i] = self.state_counters[i] - 1  #Decrement all others
        for i in range(0,len(self.state_counters)):  #Fix bounds and check for a confirmed state change
            if self.state_counters[i] < 0: self.state_counters[i] = 0
            if self.state_counters[i] >= self.debounce_time:  #Confirmed new state at index i
                self.state_counters[i] = self.debounce_time
                for x in range(0,len(self.state_counters)):
                    if x is not i: self.state_counters[x] = 0  #Zero out all other state counters
                self.state = i  #Save the new state
        return self.state


def sort_fingers_by_distance_from_screen(fingers):
    new_finger_list = [finger for finger in fingers]  #Copy the list of fingers
    new_finger_list.sort(key=lambda x: x.tip_position.z)  #Sort by increasing z
    return new_finger_list  #Lower indices = closer to screen


def has_thumb(hand):  #The level of accuracy with this function is surprisingly high
    if hand.fingers.empty:  #We assume no thumbs
        return False
    distances = []
    palm_position = Geometry.to_vector(hand.palm_position)
    for finger in hand.fingers:  #Make a list of all distances from the center of the palm
        finger_position = Geometry.to_vector(finger.tip_position)
        difference = finger_position - palm_position
        distances.append(difference.norm())  #Record the distance from the palm to the fingertip
    average = sum(distances)/len(distances)
    minimum = min(distances)
    if average - minimum > 20:  #Check if the finger closest to the palm is more than 20mm closer than the average distance
        #Note: I have recieved feedback that a smaller value may work better. I do have big hands, however
        return True
    else:
        return False


def has_two_pointer_fingers(hand):  #Checks if we are using two pointer fingers
    if len(hand.fingers) < 2:  #Obviously not
        return False
    sorted_fingers = sort_fingers_by_distance_from_screen(hand.fingers)
    finger1_pos = Geometry.to_vector(sorted_fingers[0].tip_position)
    finger2_pos = Geometry.to_vector(sorted_fingers[1].tip_position)
    difference = finger1_pos - finger2_pos
    if difference.norm() < 40:  #Check if the fingertips are close together
        return True
    else:
        return False


#Check if the vectors of length 'vector_length' shooting out of a pair of fingers intersect within tolerance 'tolerance'
def finger_vectors_intersect(finger1, finger2, vector_length, tolerance):
    #Take Leap Finger objects and produce two line segment objects
    finger_1_location = Geometry.to_vector(finger1.tip_position)
    finger_1_direction = Geometry.to_vector(finger1.direction)
    finger_1_vector = finger_1_direction.unit_vector() ** vector_length;  #** is scalar mult
    finger_1_endpoint = finger_1_vector + finger_1_location
    finger_1_segment = Geometry.segment(finger_1_location, finger_1_endpoint)

    finger_2_location = Geometry.to_vector(finger2.tip_position)
    finger_2_direction = Geometry.to_vector(finger2.direction)
    finger_2_vector = finger_2_direction.unit_vector() ** vector_length;  #** is scalar mult
    finger_2_endpoint = finger_2_vector + finger_2_location
    finger_2_segment = Geometry.segment(finger_2_location, finger_2_endpoint)

    minimum_distance = finger_1_segment.min_distance_finite(finger_2_segment)

    if minimum_distance <= tolerance:
        return True
    return False

########NEW FILE########
__FILENAME__ = MotionControl
import sys, os, ConfigParser
from leap import Leap, CircleGesture, KeyTapGesture, ScreenTapGesture, SwipeGesture

class Motion_Control_Listener(Leap.Listener):  #The Listener that we attach to the controller. This listener is for motion control
    def __init__(self, mouse):
        super(Motion_Control_Listener, self).__init__()  #Initialize like a normal listener

    def on_init(self, controller):
        self.read_config() #Read the config file
        self.init_list_of_commands() #Initialize the list of recognized commands

        print "Initialized"

    def read_config(self):
        self.config = ConfigParser.ConfigParser()
        self.config.read("./commands.ini")

    def init_list_of_commands(self):
        #Initialize all commands an put it in an array
        self.commands = [
                ScreentapCommand(),
                SwiperightCommand(),
                SwipeleftCommand(),
                CounterclockwiseCommand(),
                ClockwiseCommand(),
                KeytapCommand()
        ]

    def on_connect(self, controller):
        #Enable all gestures
        controller.enable_gesture(Leap.Gesture.TYPE_CIRCLE);
        controller.enable_gesture(Leap.Gesture.TYPE_KEY_TAP);
        controller.enable_gesture(Leap.Gesture.TYPE_SCREEN_TAP);
        controller.enable_gesture(Leap.Gesture.TYPE_SWIPE);

        print "Connected"

    def on_disconnect(self, controller):
        print "Disconnected"

    def on_exit(self, controller):
        print "Exited"

    def on_frame(self, controller):
        frame = controller.frame()  #Grab the latest 3D data
        if not frame.hands.is_empty:  #Make sure we have some hands to work with
            for command in self.commands: #Loop all enabled commands
                if(command.applicable(frame)): #If the motion associated to the command is triggered
                    self.execute(frame, command.name) #Execute the command

    def execute(self, frame, command_name):
        number_for_fingers = self.get_fingers_code(frame) #Get a text correspond to the number of fingers
        if(self.config.has_option(command_name, number_for_fingers)): #If the command if finded in the config file
            syscommand = self.config.get(command_name, number_for_fingers) #Prepare the command
            print(syscommand)
            os.system(syscommand) #Execute the command

    def get_fingers_code(self, frame):
        return "%dfinger" % len(frame.fingers)


class ScreentapCommand():
    def __init__(self):
        self.name = "screentap"
        #The name of the command in the config file

    #Return true if the command is applicable
    def applicable(self, frame):
        return(frame.gestures()[0].type == Leap.Gesture.TYPE_SCREEN_TAP)

class KeytapCommand():
    def __init__(self):
        self.name = "keytap" #The name of the command in the config file

    #Return true if the command is applicable
    def applicable(self, frame):
        return(frame.gestures()[0].type == Leap.Gesture.TYPE_KEY_TAP)

class SwiperightCommand():
    def __init__(self):
        self.name = "swiperight" #The name of the command in the config file

    #Return true if the command is applicable
    def applicable(self, frame):
        swipe = SwipeGesture(frame.gestures()[0])
        return(swipe.state == Leap.Gesture.STATE_STOP
                and swipe.type == Leap.Gesture.TYPE_SWIPE
                and swipe.direction[0] < 0)

class SwipeleftCommand():
    def __init__(self):
        self.name = "swipeleft" #The name of the command in the config file

    #Return true if the command is applicable
    def applicable(self, frame):
        swipe = SwipeGesture(frame.gestures()[0])
        return(swipe.state == Leap.Gesture.STATE_STOP
                and swipe.type == Leap.Gesture.TYPE_SWIPE
                and swipe.direction[0] > 0)

class ClockwiseCommand():
    def __init__(self):
        self.name = "clockwise" #The name of the command in the config file

    #Return true if the command is applicable
    def applicable(self, frame):
        circle = CircleGesture(frame.gestures()[0])
        return(circle.state == Leap.Gesture.STATE_STOP and
                circle.type == Leap.Gesture.TYPE_CIRCLE and
                circle.pointable.direction.angle_to(circle.normal) <= Leap.PI/4)

class CounterclockwiseCommand():
    def __init__(self):
        self.name = "counterclockwise" #The name of the command in the config file

    #Return true if the command is applicable
    def applicable(self, frame):
        circle = CircleGesture(frame.gestures()[0])
        return(circle.state == Leap.Gesture.STATE_STOP and
                circle.type == Leap.Gesture.TYPE_CIRCLE and
                circle.pointable.direction.angle_to(circle.normal) > Leap.PI/4)

########NEW FILE########
__FILENAME__ = Leap
# This file was automatically generated by SWIG (http://www.swig.org).
# Version 2.0.9
#
# Do not make changes to this file unless you know what you are doing--modify
# the SWIG interface file instead.



from sys import version_info
if version_info >= (2,6,0):
    def swig_import_helper():
        from os.path import dirname
        import imp
        fp = None
        try:
            fp, pathname, description = imp.find_module('LeapPython', [dirname(__file__)])
        except ImportError:
            import LeapPython
            return LeapPython
        if fp is not None:
            try:
                _mod = imp.load_module('LeapPython', fp, pathname, description)
            finally:
                fp.close()
            return _mod
    LeapPython = swig_import_helper()
    del swig_import_helper
else:
    import LeapPython
del version_info
try:
    _swig_property = property
except NameError:
    pass # Python < 2.2 doesn't have 'property'.
def _swig_setattr_nondynamic(self,class_type,name,value,static=1):
    if (name == "thisown"): return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'SwigPyObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name,None)
    if method: return method(self,value)
    if (not static):
        self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)

def _swig_setattr(self,class_type,name,value):
    return _swig_setattr_nondynamic(self,class_type,name,value,0)

def _swig_getattr(self,class_type,name):
    if (name == "thisown"): return self.this.own()
    method = class_type.__swig_getmethods__.get(name,None)
    if method: return method(self)
    raise AttributeError(name)

def _swig_repr(self):
    try: strthis = "proxy of " + self.this.__repr__()
    except: strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

try:
    _object = object
    _newclass = 1
except AttributeError:
    class _object : pass
    _newclass = 0


try:
    import weakref
    weakref_proxy = weakref.proxy
except:
    weakref_proxy = lambda x: x


class SwigPyIterator(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, SwigPyIterator, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, SwigPyIterator, name)
    def __init__(self, *args, **kwargs): raise AttributeError("No constructor defined - class is abstract")
    __repr__ = _swig_repr
    __swig_destroy__ = LeapPython.delete_SwigPyIterator
    __del__ = lambda self : None;
    def value(self): return LeapPython.SwigPyIterator_value(self)
    def incr(self, n=1): return LeapPython.SwigPyIterator_incr(self, n)
    def decr(self, n=1): return LeapPython.SwigPyIterator_decr(self, n)
    def distance(self, *args): return LeapPython.SwigPyIterator_distance(self, *args)
    def equal(self, *args): return LeapPython.SwigPyIterator_equal(self, *args)
    def copy(self): return LeapPython.SwigPyIterator_copy(self)
    def next(self): return LeapPython.SwigPyIterator_next(self)
    def __next__(self): return LeapPython.SwigPyIterator___next__(self)
    def previous(self): return LeapPython.SwigPyIterator_previous(self)
    def advance(self, *args): return LeapPython.SwigPyIterator_advance(self, *args)
    def __eq__(self, *args): return LeapPython.SwigPyIterator___eq__(self, *args)
    def __ne__(self, *args): return LeapPython.SwigPyIterator___ne__(self, *args)
    def __iadd__(self, *args): return LeapPython.SwigPyIterator___iadd__(self, *args)
    def __isub__(self, *args): return LeapPython.SwigPyIterator___isub__(self, *args)
    def __add__(self, *args): return LeapPython.SwigPyIterator___add__(self, *args)
    def __sub__(self, *args): return LeapPython.SwigPyIterator___sub__(self, *args)
    def __iter__(self): return self
SwigPyIterator_swigregister = LeapPython.SwigPyIterator_swigregister
SwigPyIterator_swigregister(SwigPyIterator)

class BoolArray(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, BoolArray, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, BoolArray, name)
    __repr__ = _swig_repr
    def iterator(self): return LeapPython.BoolArray_iterator(self)
    def __iter__(self): return self.iterator()
    def __nonzero__(self): return LeapPython.BoolArray___nonzero__(self)
    def __bool__(self): return LeapPython.BoolArray___bool__(self)
    def __len__(self): return LeapPython.BoolArray___len__(self)
    def pop(self): return LeapPython.BoolArray_pop(self)
    def __getslice__(self, *args): return LeapPython.BoolArray___getslice__(self, *args)
    def __setslice__(self, *args): return LeapPython.BoolArray___setslice__(self, *args)
    def __delslice__(self, *args): return LeapPython.BoolArray___delslice__(self, *args)
    def __delitem__(self, *args): return LeapPython.BoolArray___delitem__(self, *args)
    def __getitem__(self, *args): return LeapPython.BoolArray___getitem__(self, *args)
    def __setitem__(self, *args): return LeapPython.BoolArray___setitem__(self, *args)
    def append(self, *args): return LeapPython.BoolArray_append(self, *args)
    def empty(self): return LeapPython.BoolArray_empty(self)
    def size(self): return LeapPython.BoolArray_size(self)
    def clear(self): return LeapPython.BoolArray_clear(self)
    def swap(self, *args): return LeapPython.BoolArray_swap(self, *args)
    def get_allocator(self): return LeapPython.BoolArray_get_allocator(self)
    def begin(self): return LeapPython.BoolArray_begin(self)
    def end(self): return LeapPython.BoolArray_end(self)
    def rbegin(self): return LeapPython.BoolArray_rbegin(self)
    def rend(self): return LeapPython.BoolArray_rend(self)
    def pop_back(self): return LeapPython.BoolArray_pop_back(self)
    def erase(self, *args): return LeapPython.BoolArray_erase(self, *args)
    def __init__(self, *args): 
        this = LeapPython.new_BoolArray(*args)
        try: self.this.append(this)
        except: self.this = this
    def push_back(self, *args): return LeapPython.BoolArray_push_back(self, *args)
    def front(self): return LeapPython.BoolArray_front(self)
    def back(self): return LeapPython.BoolArray_back(self)
    def assign(self, *args): return LeapPython.BoolArray_assign(self, *args)
    def resize(self, *args): return LeapPython.BoolArray_resize(self, *args)
    def insert(self, *args): return LeapPython.BoolArray_insert(self, *args)
    def reserve(self, *args): return LeapPython.BoolArray_reserve(self, *args)
    def capacity(self): return LeapPython.BoolArray_capacity(self)
    __swig_destroy__ = LeapPython.delete_BoolArray
    __del__ = lambda self : None;
BoolArray_swigregister = LeapPython.BoolArray_swigregister
BoolArray_swigregister(BoolArray)

class Int32Array(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Int32Array, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Int32Array, name)
    __repr__ = _swig_repr
    def iterator(self): return LeapPython.Int32Array_iterator(self)
    def __iter__(self): return self.iterator()
    def __nonzero__(self): return LeapPython.Int32Array___nonzero__(self)
    def __bool__(self): return LeapPython.Int32Array___bool__(self)
    def __len__(self): return LeapPython.Int32Array___len__(self)
    def pop(self): return LeapPython.Int32Array_pop(self)
    def __getslice__(self, *args): return LeapPython.Int32Array___getslice__(self, *args)
    def __setslice__(self, *args): return LeapPython.Int32Array___setslice__(self, *args)
    def __delslice__(self, *args): return LeapPython.Int32Array___delslice__(self, *args)
    def __delitem__(self, *args): return LeapPython.Int32Array___delitem__(self, *args)
    def __getitem__(self, *args): return LeapPython.Int32Array___getitem__(self, *args)
    def __setitem__(self, *args): return LeapPython.Int32Array___setitem__(self, *args)
    def append(self, *args): return LeapPython.Int32Array_append(self, *args)
    def empty(self): return LeapPython.Int32Array_empty(self)
    def size(self): return LeapPython.Int32Array_size(self)
    def clear(self): return LeapPython.Int32Array_clear(self)
    def swap(self, *args): return LeapPython.Int32Array_swap(self, *args)
    def get_allocator(self): return LeapPython.Int32Array_get_allocator(self)
    def begin(self): return LeapPython.Int32Array_begin(self)
    def end(self): return LeapPython.Int32Array_end(self)
    def rbegin(self): return LeapPython.Int32Array_rbegin(self)
    def rend(self): return LeapPython.Int32Array_rend(self)
    def pop_back(self): return LeapPython.Int32Array_pop_back(self)
    def erase(self, *args): return LeapPython.Int32Array_erase(self, *args)
    def __init__(self, *args): 
        this = LeapPython.new_Int32Array(*args)
        try: self.this.append(this)
        except: self.this = this
    def push_back(self, *args): return LeapPython.Int32Array_push_back(self, *args)
    def front(self): return LeapPython.Int32Array_front(self)
    def back(self): return LeapPython.Int32Array_back(self)
    def assign(self, *args): return LeapPython.Int32Array_assign(self, *args)
    def resize(self, *args): return LeapPython.Int32Array_resize(self, *args)
    def insert(self, *args): return LeapPython.Int32Array_insert(self, *args)
    def reserve(self, *args): return LeapPython.Int32Array_reserve(self, *args)
    def capacity(self): return LeapPython.Int32Array_capacity(self)
    __swig_destroy__ = LeapPython.delete_Int32Array
    __del__ = lambda self : None;
Int32Array_swigregister = LeapPython.Int32Array_swigregister
Int32Array_swigregister(Int32Array)

class UInt32Array(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, UInt32Array, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, UInt32Array, name)
    __repr__ = _swig_repr
    def iterator(self): return LeapPython.UInt32Array_iterator(self)
    def __iter__(self): return self.iterator()
    def __nonzero__(self): return LeapPython.UInt32Array___nonzero__(self)
    def __bool__(self): return LeapPython.UInt32Array___bool__(self)
    def __len__(self): return LeapPython.UInt32Array___len__(self)
    def pop(self): return LeapPython.UInt32Array_pop(self)
    def __getslice__(self, *args): return LeapPython.UInt32Array___getslice__(self, *args)
    def __setslice__(self, *args): return LeapPython.UInt32Array___setslice__(self, *args)
    def __delslice__(self, *args): return LeapPython.UInt32Array___delslice__(self, *args)
    def __delitem__(self, *args): return LeapPython.UInt32Array___delitem__(self, *args)
    def __getitem__(self, *args): return LeapPython.UInt32Array___getitem__(self, *args)
    def __setitem__(self, *args): return LeapPython.UInt32Array___setitem__(self, *args)
    def append(self, *args): return LeapPython.UInt32Array_append(self, *args)
    def empty(self): return LeapPython.UInt32Array_empty(self)
    def size(self): return LeapPython.UInt32Array_size(self)
    def clear(self): return LeapPython.UInt32Array_clear(self)
    def swap(self, *args): return LeapPython.UInt32Array_swap(self, *args)
    def get_allocator(self): return LeapPython.UInt32Array_get_allocator(self)
    def begin(self): return LeapPython.UInt32Array_begin(self)
    def end(self): return LeapPython.UInt32Array_end(self)
    def rbegin(self): return LeapPython.UInt32Array_rbegin(self)
    def rend(self): return LeapPython.UInt32Array_rend(self)
    def pop_back(self): return LeapPython.UInt32Array_pop_back(self)
    def erase(self, *args): return LeapPython.UInt32Array_erase(self, *args)
    def __init__(self, *args): 
        this = LeapPython.new_UInt32Array(*args)
        try: self.this.append(this)
        except: self.this = this
    def push_back(self, *args): return LeapPython.UInt32Array_push_back(self, *args)
    def front(self): return LeapPython.UInt32Array_front(self)
    def back(self): return LeapPython.UInt32Array_back(self)
    def assign(self, *args): return LeapPython.UInt32Array_assign(self, *args)
    def resize(self, *args): return LeapPython.UInt32Array_resize(self, *args)
    def insert(self, *args): return LeapPython.UInt32Array_insert(self, *args)
    def reserve(self, *args): return LeapPython.UInt32Array_reserve(self, *args)
    def capacity(self): return LeapPython.UInt32Array_capacity(self)
    __swig_destroy__ = LeapPython.delete_UInt32Array
    __del__ = lambda self : None;
UInt32Array_swigregister = LeapPython.UInt32Array_swigregister
UInt32Array_swigregister(UInt32Array)

class FloatArray(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, FloatArray, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, FloatArray, name)
    __repr__ = _swig_repr
    def iterator(self): return LeapPython.FloatArray_iterator(self)
    def __iter__(self): return self.iterator()
    def __nonzero__(self): return LeapPython.FloatArray___nonzero__(self)
    def __bool__(self): return LeapPython.FloatArray___bool__(self)
    def __len__(self): return LeapPython.FloatArray___len__(self)
    def pop(self): return LeapPython.FloatArray_pop(self)
    def __getslice__(self, *args): return LeapPython.FloatArray___getslice__(self, *args)
    def __setslice__(self, *args): return LeapPython.FloatArray___setslice__(self, *args)
    def __delslice__(self, *args): return LeapPython.FloatArray___delslice__(self, *args)
    def __delitem__(self, *args): return LeapPython.FloatArray___delitem__(self, *args)
    def __getitem__(self, *args): return LeapPython.FloatArray___getitem__(self, *args)
    def __setitem__(self, *args): return LeapPython.FloatArray___setitem__(self, *args)
    def append(self, *args): return LeapPython.FloatArray_append(self, *args)
    def empty(self): return LeapPython.FloatArray_empty(self)
    def size(self): return LeapPython.FloatArray_size(self)
    def clear(self): return LeapPython.FloatArray_clear(self)
    def swap(self, *args): return LeapPython.FloatArray_swap(self, *args)
    def get_allocator(self): return LeapPython.FloatArray_get_allocator(self)
    def begin(self): return LeapPython.FloatArray_begin(self)
    def end(self): return LeapPython.FloatArray_end(self)
    def rbegin(self): return LeapPython.FloatArray_rbegin(self)
    def rend(self): return LeapPython.FloatArray_rend(self)
    def pop_back(self): return LeapPython.FloatArray_pop_back(self)
    def erase(self, *args): return LeapPython.FloatArray_erase(self, *args)
    def __init__(self, *args): 
        this = LeapPython.new_FloatArray(*args)
        try: self.this.append(this)
        except: self.this = this
    def push_back(self, *args): return LeapPython.FloatArray_push_back(self, *args)
    def front(self): return LeapPython.FloatArray_front(self)
    def back(self): return LeapPython.FloatArray_back(self)
    def assign(self, *args): return LeapPython.FloatArray_assign(self, *args)
    def resize(self, *args): return LeapPython.FloatArray_resize(self, *args)
    def insert(self, *args): return LeapPython.FloatArray_insert(self, *args)
    def reserve(self, *args): return LeapPython.FloatArray_reserve(self, *args)
    def capacity(self): return LeapPython.FloatArray_capacity(self)
    __swig_destroy__ = LeapPython.delete_FloatArray
    __del__ = lambda self : None;
FloatArray_swigregister = LeapPython.FloatArray_swigregister
FloatArray_swigregister(FloatArray)

class DoubleArray(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, DoubleArray, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, DoubleArray, name)
    __repr__ = _swig_repr
    def iterator(self): return LeapPython.DoubleArray_iterator(self)
    def __iter__(self): return self.iterator()
    def __nonzero__(self): return LeapPython.DoubleArray___nonzero__(self)
    def __bool__(self): return LeapPython.DoubleArray___bool__(self)
    def __len__(self): return LeapPython.DoubleArray___len__(self)
    def pop(self): return LeapPython.DoubleArray_pop(self)
    def __getslice__(self, *args): return LeapPython.DoubleArray___getslice__(self, *args)
    def __setslice__(self, *args): return LeapPython.DoubleArray___setslice__(self, *args)
    def __delslice__(self, *args): return LeapPython.DoubleArray___delslice__(self, *args)
    def __delitem__(self, *args): return LeapPython.DoubleArray___delitem__(self, *args)
    def __getitem__(self, *args): return LeapPython.DoubleArray___getitem__(self, *args)
    def __setitem__(self, *args): return LeapPython.DoubleArray___setitem__(self, *args)
    def append(self, *args): return LeapPython.DoubleArray_append(self, *args)
    def empty(self): return LeapPython.DoubleArray_empty(self)
    def size(self): return LeapPython.DoubleArray_size(self)
    def clear(self): return LeapPython.DoubleArray_clear(self)
    def swap(self, *args): return LeapPython.DoubleArray_swap(self, *args)
    def get_allocator(self): return LeapPython.DoubleArray_get_allocator(self)
    def begin(self): return LeapPython.DoubleArray_begin(self)
    def end(self): return LeapPython.DoubleArray_end(self)
    def rbegin(self): return LeapPython.DoubleArray_rbegin(self)
    def rend(self): return LeapPython.DoubleArray_rend(self)
    def pop_back(self): return LeapPython.DoubleArray_pop_back(self)
    def erase(self, *args): return LeapPython.DoubleArray_erase(self, *args)
    def __init__(self, *args): 
        this = LeapPython.new_DoubleArray(*args)
        try: self.this.append(this)
        except: self.this = this
    def push_back(self, *args): return LeapPython.DoubleArray_push_back(self, *args)
    def front(self): return LeapPython.DoubleArray_front(self)
    def back(self): return LeapPython.DoubleArray_back(self)
    def assign(self, *args): return LeapPython.DoubleArray_assign(self, *args)
    def resize(self, *args): return LeapPython.DoubleArray_resize(self, *args)
    def insert(self, *args): return LeapPython.DoubleArray_insert(self, *args)
    def reserve(self, *args): return LeapPython.DoubleArray_reserve(self, *args)
    def capacity(self): return LeapPython.DoubleArray_capacity(self)
    __swig_destroy__ = LeapPython.delete_DoubleArray
    __del__ = lambda self : None;
DoubleArray_swigregister = LeapPython.DoubleArray_swigregister
DoubleArray_swigregister(DoubleArray)

class StringArray(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, StringArray, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, StringArray, name)
    __repr__ = _swig_repr
    def iterator(self): return LeapPython.StringArray_iterator(self)
    def __iter__(self): return self.iterator()
    def __nonzero__(self): return LeapPython.StringArray___nonzero__(self)
    def __bool__(self): return LeapPython.StringArray___bool__(self)
    def __len__(self): return LeapPython.StringArray___len__(self)
    def pop(self): return LeapPython.StringArray_pop(self)
    def __getslice__(self, *args): return LeapPython.StringArray___getslice__(self, *args)
    def __setslice__(self, *args): return LeapPython.StringArray___setslice__(self, *args)
    def __delslice__(self, *args): return LeapPython.StringArray___delslice__(self, *args)
    def __delitem__(self, *args): return LeapPython.StringArray___delitem__(self, *args)
    def __getitem__(self, *args): return LeapPython.StringArray___getitem__(self, *args)
    def __setitem__(self, *args): return LeapPython.StringArray___setitem__(self, *args)
    def append(self, *args): return LeapPython.StringArray_append(self, *args)
    def empty(self): return LeapPython.StringArray_empty(self)
    def size(self): return LeapPython.StringArray_size(self)
    def clear(self): return LeapPython.StringArray_clear(self)
    def swap(self, *args): return LeapPython.StringArray_swap(self, *args)
    def get_allocator(self): return LeapPython.StringArray_get_allocator(self)
    def begin(self): return LeapPython.StringArray_begin(self)
    def end(self): return LeapPython.StringArray_end(self)
    def rbegin(self): return LeapPython.StringArray_rbegin(self)
    def rend(self): return LeapPython.StringArray_rend(self)
    def pop_back(self): return LeapPython.StringArray_pop_back(self)
    def erase(self, *args): return LeapPython.StringArray_erase(self, *args)
    def __init__(self, *args): 
        this = LeapPython.new_StringArray(*args)
        try: self.this.append(this)
        except: self.this = this
    def push_back(self, *args): return LeapPython.StringArray_push_back(self, *args)
    def front(self): return LeapPython.StringArray_front(self)
    def back(self): return LeapPython.StringArray_back(self)
    def assign(self, *args): return LeapPython.StringArray_assign(self, *args)
    def resize(self, *args): return LeapPython.StringArray_resize(self, *args)
    def insert(self, *args): return LeapPython.StringArray_insert(self, *args)
    def reserve(self, *args): return LeapPython.StringArray_reserve(self, *args)
    def capacity(self): return LeapPython.StringArray_capacity(self)
    __swig_destroy__ = LeapPython.delete_StringArray
    __del__ = lambda self : None;
StringArray_swigregister = LeapPython.StringArray_swigregister
StringArray_swigregister(StringArray)

class Vector(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Vector, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Vector, name)
    __repr__ = _swig_repr
    def __init__(self, *args): 
        this = LeapPython.new_Vector(*args)
        try: self.this.append(this)
        except: self.this = this
    def distance_to(self, *args): return LeapPython.Vector_distance_to(self, *args)
    def angle_to(self, *args): return LeapPython.Vector_angle_to(self, *args)
    def dot(self, *args): return LeapPython.Vector_dot(self, *args)
    def cross(self, *args): return LeapPython.Vector_cross(self, *args)
    def __neg__(self): return LeapPython.Vector___neg__(self)
    def __add__(self, *args): return LeapPython.Vector___add__(self, *args)
    def __sub__(self, *args): return LeapPython.Vector___sub__(self, *args)
    def __mul__(self, *args): return LeapPython.Vector___mul__(self, *args)
    def __div__(self, *args): return LeapPython.Vector___div__(self, *args)
    def __iadd__(self, *args): return LeapPython.Vector___iadd__(self, *args)
    def __isub__(self, *args): return LeapPython.Vector___isub__(self, *args)
    def __imul__(self, *args): return LeapPython.Vector___imul__(self, *args)
    def __idiv__(self, *args): return LeapPython.Vector___idiv__(self, *args)
    def __str__(self): return LeapPython.Vector___str__(self)
    def __eq__(self, *args): return LeapPython.Vector___eq__(self, *args)
    def __ne__(self, *args): return LeapPython.Vector___ne__(self, *args)
    def is_valid(self): return LeapPython.Vector_is_valid(self)
    def __getitem__(self, *args): return LeapPython.Vector___getitem__(self, *args)
    __swig_setmethods__["x"] = LeapPython.Vector_x_set
    __swig_getmethods__["x"] = LeapPython.Vector_x_get
    if _newclass:x = _swig_property(LeapPython.Vector_x_get, LeapPython.Vector_x_set)
    __swig_setmethods__["y"] = LeapPython.Vector_y_set
    __swig_getmethods__["y"] = LeapPython.Vector_y_get
    if _newclass:y = _swig_property(LeapPython.Vector_y_get, LeapPython.Vector_y_set)
    __swig_setmethods__["z"] = LeapPython.Vector_z_set
    __swig_getmethods__["z"] = LeapPython.Vector_z_get
    if _newclass:z = _swig_property(LeapPython.Vector_z_get, LeapPython.Vector_z_set)
    __swig_getmethods__["magnitude"] = LeapPython.Vector_magnitude_get
    if _newclass:magnitude = _swig_property(LeapPython.Vector_magnitude_get)
    __swig_getmethods__["magnitude_squared"] = LeapPython.Vector_magnitude_squared_get
    if _newclass:magnitude_squared = _swig_property(LeapPython.Vector_magnitude_squared_get)
    __swig_getmethods__["pitch"] = LeapPython.Vector_pitch_get
    if _newclass:pitch = _swig_property(LeapPython.Vector_pitch_get)
    __swig_getmethods__["roll"] = LeapPython.Vector_roll_get
    if _newclass:roll = _swig_property(LeapPython.Vector_roll_get)
    __swig_getmethods__["yaw"] = LeapPython.Vector_yaw_get
    if _newclass:yaw = _swig_property(LeapPython.Vector_yaw_get)
    __swig_getmethods__["normalized"] = LeapPython.Vector_normalized_get
    if _newclass:normalized = _swig_property(LeapPython.Vector_normalized_get)
    def to_float_array(self): return [self.x, self.y, self.z]
    def to_tuple(self): return (self.x, self.y, self.z)

    __swig_destroy__ = LeapPython.delete_Vector
    __del__ = lambda self : None;
Vector_swigregister = LeapPython.Vector_swigregister
Vector_swigregister(Vector)
cvar = LeapPython.cvar
PI = cvar.PI
DEG_TO_RAD = cvar.DEG_TO_RAD
RAD_TO_DEG = cvar.RAD_TO_DEG
Vector.zero = LeapPython.cvar.Vector_zero
Vector.x_axis = LeapPython.cvar.Vector_x_axis
Vector.y_axis = LeapPython.cvar.Vector_y_axis
Vector.z_axis = LeapPython.cvar.Vector_z_axis
Vector.forward = LeapPython.cvar.Vector_forward
Vector.backward = LeapPython.cvar.Vector_backward
Vector.left = LeapPython.cvar.Vector_left
Vector.right = LeapPython.cvar.Vector_right
Vector.up = LeapPython.cvar.Vector_up
Vector.down = LeapPython.cvar.Vector_down

class Matrix(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Matrix, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Matrix, name)
    __repr__ = _swig_repr
    def __init__(self, *args): 
        this = LeapPython.new_Matrix(*args)
        try: self.this.append(this)
        except: self.this = this
    def set_rotation(self, *args): return LeapPython.Matrix_set_rotation(self, *args)
    def transform_point(self, *args): return LeapPython.Matrix_transform_point(self, *args)
    def transform_direction(self, *args): return LeapPython.Matrix_transform_direction(self, *args)
    def rigid_inverse(self): return LeapPython.Matrix_rigid_inverse(self)
    def __mul__(self, *args): return LeapPython.Matrix___mul__(self, *args)
    def __imul__(self, *args): return LeapPython.Matrix___imul__(self, *args)
    def __eq__(self, *args): return LeapPython.Matrix___eq__(self, *args)
    def __ne__(self, *args): return LeapPython.Matrix___ne__(self, *args)
    def __str__(self): return LeapPython.Matrix___str__(self)
    __swig_setmethods__["x_basis"] = LeapPython.Matrix_x_basis_set
    __swig_getmethods__["x_basis"] = LeapPython.Matrix_x_basis_get
    if _newclass:x_basis = _swig_property(LeapPython.Matrix_x_basis_get, LeapPython.Matrix_x_basis_set)
    __swig_setmethods__["y_basis"] = LeapPython.Matrix_y_basis_set
    __swig_getmethods__["y_basis"] = LeapPython.Matrix_y_basis_get
    if _newclass:y_basis = _swig_property(LeapPython.Matrix_y_basis_get, LeapPython.Matrix_y_basis_set)
    __swig_setmethods__["z_basis"] = LeapPython.Matrix_z_basis_set
    __swig_getmethods__["z_basis"] = LeapPython.Matrix_z_basis_get
    if _newclass:z_basis = _swig_property(LeapPython.Matrix_z_basis_get, LeapPython.Matrix_z_basis_set)
    __swig_setmethods__["origin"] = LeapPython.Matrix_origin_set
    __swig_getmethods__["origin"] = LeapPython.Matrix_origin_get
    if _newclass:origin = _swig_property(LeapPython.Matrix_origin_get, LeapPython.Matrix_origin_set)
    def to_array_3x3(self, output = None):
        if output is None:
            output = [0]*9
        output[0], output[1], output[2] = self.x_basis.x, self.x_basis.y, self.x_basis.z
        output[3], output[4], output[5] = self.y_basis.x, self.y_basis.y, self.y_basis.z
        output[6], output[7], output[8] = self.z_basis.x, self.z_basis.y, self.z_basis.z
        return output
    def to_array_4x4(self, output = None):
        if output is None:
            output = [0]*16
        output[0],  output[1],  output[2],  output[3]  = self.x_basis.x, self.x_basis.y, self.x_basis.z, 0.0
        output[4],  output[5],  output[6],  output[7]  = self.y_basis.x, self.y_basis.y, self.y_basis.z, 0.0
        output[8],  output[9],  output[10], output[11] = self.z_basis.x, self.z_basis.y, self.z_basis.z, 0.0
        output[12], output[13], output[14], output[15] = self.origin.x,  self.origin.y,  self.origin.z,  1.0
        return output

    __swig_destroy__ = LeapPython.delete_Matrix
    __del__ = lambda self : None;
Matrix_swigregister = LeapPython.Matrix_swigregister
Matrix_swigregister(Matrix)
Matrix.identity = LeapPython.cvar.Matrix_identity

class Interface(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Interface, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Interface, name)
    def __init__(self, *args, **kwargs): raise AttributeError("No constructor defined")
    __repr__ = _swig_repr
Interface_swigregister = LeapPython.Interface_swigregister
Interface_swigregister(Interface)

class Pointable(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, Pointable, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, Pointable, name)
    __repr__ = _swig_repr
    def __init__(self): 
        this = LeapPython.new_Pointable()
        try: self.this.append(this)
        except: self.this = this
    def __eq__(self, *args): return LeapPython.Pointable___eq__(self, *args)
    def __ne__(self, *args): return LeapPython.Pointable___ne__(self, *args)
    def __str__(self): return LeapPython.Pointable___str__(self)
    __swig_getmethods__["id"] = LeapPython.Pointable_id_get
    if _newclass:id = _swig_property(LeapPython.Pointable_id_get)
    __swig_getmethods__["hand"] = LeapPython.Pointable_hand_get
    if _newclass:hand = _swig_property(LeapPython.Pointable_hand_get)
    __swig_getmethods__["tip_position"] = LeapPython.Pointable_tip_position_get
    if _newclass:tip_position = _swig_property(LeapPython.Pointable_tip_position_get)
    __swig_getmethods__["tip_velocity"] = LeapPython.Pointable_tip_velocity_get
    if _newclass:tip_velocity = _swig_property(LeapPython.Pointable_tip_velocity_get)
    __swig_getmethods__["direction"] = LeapPython.Pointable_direction_get
    if _newclass:direction = _swig_property(LeapPython.Pointable_direction_get)
    __swig_getmethods__["width"] = LeapPython.Pointable_width_get
    if _newclass:width = _swig_property(LeapPython.Pointable_width_get)
    __swig_getmethods__["length"] = LeapPython.Pointable_length_get
    if _newclass:length = _swig_property(LeapPython.Pointable_length_get)
    __swig_getmethods__["is_tool"] = LeapPython.Pointable_is_tool_get
    if _newclass:is_tool = _swig_property(LeapPython.Pointable_is_tool_get)
    __swig_getmethods__["is_finger"] = LeapPython.Pointable_is_finger_get
    if _newclass:is_finger = _swig_property(LeapPython.Pointable_is_finger_get)
    __swig_getmethods__["is_valid"] = LeapPython.Pointable_is_valid_get
    if _newclass:is_valid = _swig_property(LeapPython.Pointable_is_valid_get)
    __swig_getmethods__["frame"] = LeapPython.Pointable_frame_get
    if _newclass:frame = _swig_property(LeapPython.Pointable_frame_get)
    __swig_destroy__ = LeapPython.delete_Pointable
    __del__ = lambda self : None;
Pointable_swigregister = LeapPython.Pointable_swigregister
Pointable_swigregister(Pointable)
Pointable.invalid = LeapPython.cvar.Pointable_invalid

class Finger(Pointable):
    __swig_setmethods__ = {}
    for _s in [Pointable]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, Finger, name, value)
    __swig_getmethods__ = {}
    for _s in [Pointable]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, Finger, name)
    __repr__ = _swig_repr
    def __init__(self, *args): 
        this = LeapPython.new_Finger(*args)
        try: self.this.append(this)
        except: self.this = this
    def __str__(self): return LeapPython.Finger___str__(self)
    __swig_destroy__ = LeapPython.delete_Finger
    __del__ = lambda self : None;
Finger_swigregister = LeapPython.Finger_swigregister
Finger_swigregister(Finger)
Finger.invalid = LeapPython.cvar.Finger_invalid

class Tool(Pointable):
    __swig_setmethods__ = {}
    for _s in [Pointable]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, Tool, name, value)
    __swig_getmethods__ = {}
    for _s in [Pointable]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, Tool, name)
    __repr__ = _swig_repr
    def __init__(self, *args): 
        this = LeapPython.new_Tool(*args)
        try: self.this.append(this)
        except: self.this = this
    def __str__(self): return LeapPython.Tool___str__(self)
    __swig_destroy__ = LeapPython.delete_Tool
    __del__ = lambda self : None;
Tool_swigregister = LeapPython.Tool_swigregister
Tool_swigregister(Tool)
Tool.invalid = LeapPython.cvar.Tool_invalid

class Hand(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, Hand, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, Hand, name)
    __repr__ = _swig_repr
    def __init__(self): 
        this = LeapPython.new_Hand()
        try: self.this.append(this)
        except: self.this = this
    def pointable(self, *args): return LeapPython.Hand_pointable(self, *args)
    def finger(self, *args): return LeapPython.Hand_finger(self, *args)
    def tool(self, *args): return LeapPython.Hand_tool(self, *args)
    def translation(self, *args): return LeapPython.Hand_translation(self, *args)
    def rotation_axis(self, *args): return LeapPython.Hand_rotation_axis(self, *args)
    def rotation_angle(self, *args): return LeapPython.Hand_rotation_angle(self, *args)
    def rotation_matrix(self, *args): return LeapPython.Hand_rotation_matrix(self, *args)
    def scale_factor(self, *args): return LeapPython.Hand_scale_factor(self, *args)
    def __eq__(self, *args): return LeapPython.Hand___eq__(self, *args)
    def __ne__(self, *args): return LeapPython.Hand___ne__(self, *args)
    def __str__(self): return LeapPython.Hand___str__(self)
    __swig_getmethods__["id"] = LeapPython.Hand_id_get
    if _newclass:id = _swig_property(LeapPython.Hand_id_get)
    __swig_getmethods__["pointables"] = LeapPython.Hand_pointables_get
    if _newclass:pointables = _swig_property(LeapPython.Hand_pointables_get)
    __swig_getmethods__["fingers"] = LeapPython.Hand_fingers_get
    if _newclass:fingers = _swig_property(LeapPython.Hand_fingers_get)
    __swig_getmethods__["tools"] = LeapPython.Hand_tools_get
    if _newclass:tools = _swig_property(LeapPython.Hand_tools_get)
    __swig_getmethods__["palm_position"] = LeapPython.Hand_palm_position_get
    if _newclass:palm_position = _swig_property(LeapPython.Hand_palm_position_get)
    __swig_getmethods__["palm_velocity"] = LeapPython.Hand_palm_velocity_get
    if _newclass:palm_velocity = _swig_property(LeapPython.Hand_palm_velocity_get)
    __swig_getmethods__["palm_normal"] = LeapPython.Hand_palm_normal_get
    if _newclass:palm_normal = _swig_property(LeapPython.Hand_palm_normal_get)
    __swig_getmethods__["direction"] = LeapPython.Hand_direction_get
    if _newclass:direction = _swig_property(LeapPython.Hand_direction_get)
    __swig_getmethods__["is_valid"] = LeapPython.Hand_is_valid_get
    if _newclass:is_valid = _swig_property(LeapPython.Hand_is_valid_get)
    __swig_getmethods__["sphere_center"] = LeapPython.Hand_sphere_center_get
    if _newclass:sphere_center = _swig_property(LeapPython.Hand_sphere_center_get)
    __swig_getmethods__["sphere_radius"] = LeapPython.Hand_sphere_radius_get
    if _newclass:sphere_radius = _swig_property(LeapPython.Hand_sphere_radius_get)
    __swig_getmethods__["frame"] = LeapPython.Hand_frame_get
    if _newclass:frame = _swig_property(LeapPython.Hand_frame_get)
    __swig_destroy__ = LeapPython.delete_Hand
    __del__ = lambda self : None;
Hand_swigregister = LeapPython.Hand_swigregister
Hand_swigregister(Hand)
Hand.invalid = LeapPython.cvar.Hand_invalid

class Gesture(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, Gesture, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, Gesture, name)
    __repr__ = _swig_repr
    TYPE_INVALID = LeapPython.Gesture_TYPE_INVALID
    TYPE_SWIPE = LeapPython.Gesture_TYPE_SWIPE
    TYPE_CIRCLE = LeapPython.Gesture_TYPE_CIRCLE
    TYPE_SCREEN_TAP = LeapPython.Gesture_TYPE_SCREEN_TAP
    TYPE_KEY_TAP = LeapPython.Gesture_TYPE_KEY_TAP
    STATE_INVALID = LeapPython.Gesture_STATE_INVALID
    STATE_START = LeapPython.Gesture_STATE_START
    STATE_UPDATE = LeapPython.Gesture_STATE_UPDATE
    STATE_STOP = LeapPython.Gesture_STATE_STOP
    def __init__(self, *args): 
        this = LeapPython.new_Gesture(*args)
        try: self.this.append(this)
        except: self.this = this
    def __eq__(self, *args): return LeapPython.Gesture___eq__(self, *args)
    def __ne__(self, *args): return LeapPython.Gesture___ne__(self, *args)
    def __str__(self): return LeapPython.Gesture___str__(self)
    __swig_getmethods__["type"] = LeapPython.Gesture_type_get
    if _newclass:type = _swig_property(LeapPython.Gesture_type_get)
    __swig_getmethods__["state"] = LeapPython.Gesture_state_get
    if _newclass:state = _swig_property(LeapPython.Gesture_state_get)
    __swig_getmethods__["id"] = LeapPython.Gesture_id_get
    if _newclass:id = _swig_property(LeapPython.Gesture_id_get)
    __swig_getmethods__["duration"] = LeapPython.Gesture_duration_get
    if _newclass:duration = _swig_property(LeapPython.Gesture_duration_get)
    __swig_getmethods__["duration_seconds"] = LeapPython.Gesture_duration_seconds_get
    if _newclass:duration_seconds = _swig_property(LeapPython.Gesture_duration_seconds_get)
    __swig_getmethods__["frame"] = LeapPython.Gesture_frame_get
    if _newclass:frame = _swig_property(LeapPython.Gesture_frame_get)
    __swig_getmethods__["hands"] = LeapPython.Gesture_hands_get
    if _newclass:hands = _swig_property(LeapPython.Gesture_hands_get)
    __swig_getmethods__["pointables"] = LeapPython.Gesture_pointables_get
    if _newclass:pointables = _swig_property(LeapPython.Gesture_pointables_get)
    __swig_getmethods__["is_valid"] = LeapPython.Gesture_is_valid_get
    if _newclass:is_valid = _swig_property(LeapPython.Gesture_is_valid_get)
    __swig_destroy__ = LeapPython.delete_Gesture
    __del__ = lambda self : None;
Gesture_swigregister = LeapPython.Gesture_swigregister
Gesture_swigregister(Gesture)
Gesture.invalid = LeapPython.cvar.Gesture_invalid

class SwipeGesture(Gesture):
    __swig_setmethods__ = {}
    for _s in [Gesture]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, SwipeGesture, name, value)
    __swig_getmethods__ = {}
    for _s in [Gesture]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, SwipeGesture, name)
    __repr__ = _swig_repr
    __swig_getmethods__["class_type"] = lambda x: LeapPython.SwipeGesture_class_type
    if _newclass:class_type = staticmethod(LeapPython.SwipeGesture_class_type)
    def __init__(self, *args): 
        this = LeapPython.new_SwipeGesture(*args)
        try: self.this.append(this)
        except: self.this = this
    __swig_getmethods__["start_position"] = LeapPython.SwipeGesture_start_position_get
    if _newclass:start_position = _swig_property(LeapPython.SwipeGesture_start_position_get)
    __swig_getmethods__["position"] = LeapPython.SwipeGesture_position_get
    if _newclass:position = _swig_property(LeapPython.SwipeGesture_position_get)
    __swig_getmethods__["direction"] = LeapPython.SwipeGesture_direction_get
    if _newclass:direction = _swig_property(LeapPython.SwipeGesture_direction_get)
    __swig_getmethods__["speed"] = LeapPython.SwipeGesture_speed_get
    if _newclass:speed = _swig_property(LeapPython.SwipeGesture_speed_get)
    __swig_getmethods__["pointable"] = LeapPython.SwipeGesture_pointable_get
    if _newclass:pointable = _swig_property(LeapPython.SwipeGesture_pointable_get)
    __swig_destroy__ = LeapPython.delete_SwipeGesture
    __del__ = lambda self : None;
SwipeGesture_swigregister = LeapPython.SwipeGesture_swigregister
SwipeGesture_swigregister(SwipeGesture)

def SwipeGesture_class_type():
  return LeapPython.SwipeGesture_class_type()
SwipeGesture_class_type = LeapPython.SwipeGesture_class_type

class CircleGesture(Gesture):
    __swig_setmethods__ = {}
    for _s in [Gesture]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, CircleGesture, name, value)
    __swig_getmethods__ = {}
    for _s in [Gesture]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, CircleGesture, name)
    __repr__ = _swig_repr
    __swig_getmethods__["class_type"] = lambda x: LeapPython.CircleGesture_class_type
    if _newclass:class_type = staticmethod(LeapPython.CircleGesture_class_type)
    def __init__(self, *args): 
        this = LeapPython.new_CircleGesture(*args)
        try: self.this.append(this)
        except: self.this = this
    __swig_getmethods__["center"] = LeapPython.CircleGesture_center_get
    if _newclass:center = _swig_property(LeapPython.CircleGesture_center_get)
    __swig_getmethods__["normal"] = LeapPython.CircleGesture_normal_get
    if _newclass:normal = _swig_property(LeapPython.CircleGesture_normal_get)
    __swig_getmethods__["progress"] = LeapPython.CircleGesture_progress_get
    if _newclass:progress = _swig_property(LeapPython.CircleGesture_progress_get)
    __swig_getmethods__["radius"] = LeapPython.CircleGesture_radius_get
    if _newclass:radius = _swig_property(LeapPython.CircleGesture_radius_get)
    __swig_getmethods__["pointable"] = LeapPython.CircleGesture_pointable_get
    if _newclass:pointable = _swig_property(LeapPython.CircleGesture_pointable_get)
    __swig_destroy__ = LeapPython.delete_CircleGesture
    __del__ = lambda self : None;
CircleGesture_swigregister = LeapPython.CircleGesture_swigregister
CircleGesture_swigregister(CircleGesture)

def CircleGesture_class_type():
  return LeapPython.CircleGesture_class_type()
CircleGesture_class_type = LeapPython.CircleGesture_class_type

class ScreenTapGesture(Gesture):
    __swig_setmethods__ = {}
    for _s in [Gesture]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, ScreenTapGesture, name, value)
    __swig_getmethods__ = {}
    for _s in [Gesture]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, ScreenTapGesture, name)
    __repr__ = _swig_repr
    __swig_getmethods__["class_type"] = lambda x: LeapPython.ScreenTapGesture_class_type
    if _newclass:class_type = staticmethod(LeapPython.ScreenTapGesture_class_type)
    def __init__(self, *args): 
        this = LeapPython.new_ScreenTapGesture(*args)
        try: self.this.append(this)
        except: self.this = this
    __swig_getmethods__["position"] = LeapPython.ScreenTapGesture_position_get
    if _newclass:position = _swig_property(LeapPython.ScreenTapGesture_position_get)
    __swig_getmethods__["direction"] = LeapPython.ScreenTapGesture_direction_get
    if _newclass:direction = _swig_property(LeapPython.ScreenTapGesture_direction_get)
    __swig_getmethods__["progress"] = LeapPython.ScreenTapGesture_progress_get
    if _newclass:progress = _swig_property(LeapPython.ScreenTapGesture_progress_get)
    __swig_getmethods__["pointable"] = LeapPython.ScreenTapGesture_pointable_get
    if _newclass:pointable = _swig_property(LeapPython.ScreenTapGesture_pointable_get)
    __swig_destroy__ = LeapPython.delete_ScreenTapGesture
    __del__ = lambda self : None;
ScreenTapGesture_swigregister = LeapPython.ScreenTapGesture_swigregister
ScreenTapGesture_swigregister(ScreenTapGesture)

def ScreenTapGesture_class_type():
  return LeapPython.ScreenTapGesture_class_type()
ScreenTapGesture_class_type = LeapPython.ScreenTapGesture_class_type

class KeyTapGesture(Gesture):
    __swig_setmethods__ = {}
    for _s in [Gesture]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, KeyTapGesture, name, value)
    __swig_getmethods__ = {}
    for _s in [Gesture]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, KeyTapGesture, name)
    __repr__ = _swig_repr
    __swig_getmethods__["class_type"] = lambda x: LeapPython.KeyTapGesture_class_type
    if _newclass:class_type = staticmethod(LeapPython.KeyTapGesture_class_type)
    def __init__(self, *args): 
        this = LeapPython.new_KeyTapGesture(*args)
        try: self.this.append(this)
        except: self.this = this
    __swig_getmethods__["position"] = LeapPython.KeyTapGesture_position_get
    if _newclass:position = _swig_property(LeapPython.KeyTapGesture_position_get)
    __swig_getmethods__["direction"] = LeapPython.KeyTapGesture_direction_get
    if _newclass:direction = _swig_property(LeapPython.KeyTapGesture_direction_get)
    __swig_getmethods__["progress"] = LeapPython.KeyTapGesture_progress_get
    if _newclass:progress = _swig_property(LeapPython.KeyTapGesture_progress_get)
    __swig_getmethods__["pointable"] = LeapPython.KeyTapGesture_pointable_get
    if _newclass:pointable = _swig_property(LeapPython.KeyTapGesture_pointable_get)
    __swig_destroy__ = LeapPython.delete_KeyTapGesture
    __del__ = lambda self : None;
KeyTapGesture_swigregister = LeapPython.KeyTapGesture_swigregister
KeyTapGesture_swigregister(KeyTapGesture)

def KeyTapGesture_class_type():
  return LeapPython.KeyTapGesture_class_type()
KeyTapGesture_class_type = LeapPython.KeyTapGesture_class_type

class Screen(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, Screen, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, Screen, name)
    __repr__ = _swig_repr
    def __init__(self): 
        this = LeapPython.new_Screen()
        try: self.this.append(this)
        except: self.this = this
    def intersect(self, *args): return LeapPython.Screen_intersect(self, *args)
    def normal(self): return LeapPython.Screen_normal(self)
    def distance_to_point(self, *args): return LeapPython.Screen_distance_to_point(self, *args)
    def __eq__(self, *args): return LeapPython.Screen___eq__(self, *args)
    def __ne__(self, *args): return LeapPython.Screen___ne__(self, *args)
    def __str__(self): return LeapPython.Screen___str__(self)
    __swig_getmethods__["id"] = LeapPython.Screen_id_get
    if _newclass:id = _swig_property(LeapPython.Screen_id_get)
    __swig_getmethods__["horizontal_axis"] = LeapPython.Screen_horizontal_axis_get
    if _newclass:horizontal_axis = _swig_property(LeapPython.Screen_horizontal_axis_get)
    __swig_getmethods__["vertical_axis"] = LeapPython.Screen_vertical_axis_get
    if _newclass:vertical_axis = _swig_property(LeapPython.Screen_vertical_axis_get)
    __swig_getmethods__["bottom_left_corner"] = LeapPython.Screen_bottom_left_corner_get
    if _newclass:bottom_left_corner = _swig_property(LeapPython.Screen_bottom_left_corner_get)
    __swig_getmethods__["width_pixels"] = LeapPython.Screen_width_pixels_get
    if _newclass:width_pixels = _swig_property(LeapPython.Screen_width_pixels_get)
    __swig_getmethods__["height_pixels"] = LeapPython.Screen_height_pixels_get
    if _newclass:height_pixels = _swig_property(LeapPython.Screen_height_pixels_get)
    __swig_getmethods__["is_valid"] = LeapPython.Screen_is_valid_get
    if _newclass:is_valid = _swig_property(LeapPython.Screen_is_valid_get)
    __swig_destroy__ = LeapPython.delete_Screen
    __del__ = lambda self : None;
Screen_swigregister = LeapPython.Screen_swigregister
Screen_swigregister(Screen)
Screen.invalid = LeapPython.cvar.Screen_invalid

class PointableList(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, PointableList, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, PointableList, name)
    __repr__ = _swig_repr
    def __init__(self): 
        this = LeapPython.new_PointableList()
        try: self.this.append(this)
        except: self.this = this
    def __len__(self): return LeapPython.PointableList___len__(self)
    def __getitem__(self, *args): return LeapPython.PointableList___getitem__(self, *args)
    def append(self, *args): return LeapPython.PointableList_append(self, *args)
    __swig_getmethods__["empty"] = LeapPython.PointableList_empty_get
    if _newclass:empty = _swig_property(LeapPython.PointableList_empty_get)
    def __iter__(self):
      _pos = 0
      while _pos < len(self):
        yield self[_pos]
        _pos += 1

    __swig_destroy__ = LeapPython.delete_PointableList
    __del__ = lambda self : None;
PointableList_swigregister = LeapPython.PointableList_swigregister
PointableList_swigregister(PointableList)

class FingerList(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, FingerList, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, FingerList, name)
    __repr__ = _swig_repr
    def __init__(self): 
        this = LeapPython.new_FingerList()
        try: self.this.append(this)
        except: self.this = this
    def __len__(self): return LeapPython.FingerList___len__(self)
    def __getitem__(self, *args): return LeapPython.FingerList___getitem__(self, *args)
    def append(self, *args): return LeapPython.FingerList_append(self, *args)
    __swig_getmethods__["empty"] = LeapPython.FingerList_empty_get
    if _newclass:empty = _swig_property(LeapPython.FingerList_empty_get)
    def __iter__(self):
      _pos = 0
      while _pos < len(self):
        yield self[_pos]
        _pos += 1

    __swig_destroy__ = LeapPython.delete_FingerList
    __del__ = lambda self : None;
FingerList_swigregister = LeapPython.FingerList_swigregister
FingerList_swigregister(FingerList)

class ToolList(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, ToolList, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, ToolList, name)
    __repr__ = _swig_repr
    def __init__(self): 
        this = LeapPython.new_ToolList()
        try: self.this.append(this)
        except: self.this = this
    def __len__(self): return LeapPython.ToolList___len__(self)
    def __getitem__(self, *args): return LeapPython.ToolList___getitem__(self, *args)
    def append(self, *args): return LeapPython.ToolList_append(self, *args)
    __swig_getmethods__["empty"] = LeapPython.ToolList_empty_get
    if _newclass:empty = _swig_property(LeapPython.ToolList_empty_get)
    def __iter__(self):
      _pos = 0
      while _pos < len(self):
        yield self[_pos]
        _pos += 1

    __swig_destroy__ = LeapPython.delete_ToolList
    __del__ = lambda self : None;
ToolList_swigregister = LeapPython.ToolList_swigregister
ToolList_swigregister(ToolList)

class HandList(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, HandList, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, HandList, name)
    __repr__ = _swig_repr
    def __init__(self): 
        this = LeapPython.new_HandList()
        try: self.this.append(this)
        except: self.this = this
    def __len__(self): return LeapPython.HandList___len__(self)
    def __getitem__(self, *args): return LeapPython.HandList___getitem__(self, *args)
    def append(self, *args): return LeapPython.HandList_append(self, *args)
    __swig_getmethods__["empty"] = LeapPython.HandList_empty_get
    if _newclass:empty = _swig_property(LeapPython.HandList_empty_get)
    def __iter__(self):
      _pos = 0
      while _pos < len(self):
        yield self[_pos]
        _pos += 1

    __swig_destroy__ = LeapPython.delete_HandList
    __del__ = lambda self : None;
HandList_swigregister = LeapPython.HandList_swigregister
HandList_swigregister(HandList)

class GestureList(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, GestureList, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, GestureList, name)
    __repr__ = _swig_repr
    def __init__(self): 
        this = LeapPython.new_GestureList()
        try: self.this.append(this)
        except: self.this = this
    def __len__(self): return LeapPython.GestureList___len__(self)
    def __getitem__(self, *args): return LeapPython.GestureList___getitem__(self, *args)
    def append(self, *args): return LeapPython.GestureList_append(self, *args)
    __swig_getmethods__["empty"] = LeapPython.GestureList_empty_get
    if _newclass:empty = _swig_property(LeapPython.GestureList_empty_get)
    def __iter__(self):
      _pos = 0
      while _pos < len(self):
        yield self[_pos]
        _pos += 1

    __swig_destroy__ = LeapPython.delete_GestureList
    __del__ = lambda self : None;
GestureList_swigregister = LeapPython.GestureList_swigregister
GestureList_swigregister(GestureList)

class ScreenList(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, ScreenList, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, ScreenList, name)
    __repr__ = _swig_repr
    def __init__(self): 
        this = LeapPython.new_ScreenList()
        try: self.this.append(this)
        except: self.this = this
    def __len__(self): return LeapPython.ScreenList___len__(self)
    def __getitem__(self, *args): return LeapPython.ScreenList___getitem__(self, *args)
    def closest_screen_hit(self, *args): return LeapPython.ScreenList_closest_screen_hit(self, *args)
    __swig_getmethods__["empty"] = LeapPython.ScreenList_empty_get
    if _newclass:empty = _swig_property(LeapPython.ScreenList_empty_get)
    def __iter__(self):
      _pos = 0
      while _pos < len(self):
        yield self[_pos]
        _pos += 1

    __swig_destroy__ = LeapPython.delete_ScreenList
    __del__ = lambda self : None;
ScreenList_swigregister = LeapPython.ScreenList_swigregister
ScreenList_swigregister(ScreenList)

class Frame(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, Frame, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, Frame, name)
    __repr__ = _swig_repr
    def __init__(self): 
        this = LeapPython.new_Frame()
        try: self.this.append(this)
        except: self.this = this
    def hand(self, *args): return LeapPython.Frame_hand(self, *args)
    def pointable(self, *args): return LeapPython.Frame_pointable(self, *args)
    def finger(self, *args): return LeapPython.Frame_finger(self, *args)
    def tool(self, *args): return LeapPython.Frame_tool(self, *args)
    def gesture(self, *args): return LeapPython.Frame_gesture(self, *args)
    def gestures(self, *args): return LeapPython.Frame_gestures(self, *args)
    def translation(self, *args): return LeapPython.Frame_translation(self, *args)
    def rotation_axis(self, *args): return LeapPython.Frame_rotation_axis(self, *args)
    def rotation_angle(self, *args): return LeapPython.Frame_rotation_angle(self, *args)
    def rotation_matrix(self, *args): return LeapPython.Frame_rotation_matrix(self, *args)
    def scale_factor(self, *args): return LeapPython.Frame_scale_factor(self, *args)
    def __eq__(self, *args): return LeapPython.Frame___eq__(self, *args)
    def __ne__(self, *args): return LeapPython.Frame___ne__(self, *args)
    def __str__(self): return LeapPython.Frame___str__(self)
    __swig_getmethods__["id"] = LeapPython.Frame_id_get
    if _newclass:id = _swig_property(LeapPython.Frame_id_get)
    __swig_getmethods__["timestamp"] = LeapPython.Frame_timestamp_get
    if _newclass:timestamp = _swig_property(LeapPython.Frame_timestamp_get)
    __swig_getmethods__["hands"] = LeapPython.Frame_hands_get
    if _newclass:hands = _swig_property(LeapPython.Frame_hands_get)
    __swig_getmethods__["pointables"] = LeapPython.Frame_pointables_get
    if _newclass:pointables = _swig_property(LeapPython.Frame_pointables_get)
    __swig_getmethods__["fingers"] = LeapPython.Frame_fingers_get
    if _newclass:fingers = _swig_property(LeapPython.Frame_fingers_get)
    __swig_getmethods__["tools"] = LeapPython.Frame_tools_get
    if _newclass:tools = _swig_property(LeapPython.Frame_tools_get)
    __swig_getmethods__["is_valid"] = LeapPython.Frame_is_valid_get
    if _newclass:is_valid = _swig_property(LeapPython.Frame_is_valid_get)
    __swig_destroy__ = LeapPython.delete_Frame
    __del__ = lambda self : None;
Frame_swigregister = LeapPython.Frame_swigregister
Frame_swigregister(Frame)
Frame.invalid = LeapPython.cvar.Frame_invalid

class Config(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, Config, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, Config, name)
    __repr__ = _swig_repr
    def __init__(self): 
        this = LeapPython.new_Config()
        try: self.this.append(this)
        except: self.this = this
    TYPE_UNKNOWN = LeapPython.Config_TYPE_UNKNOWN
    TYPE_BOOLEAN = LeapPython.Config_TYPE_BOOLEAN
    TYPE_INT32 = LeapPython.Config_TYPE_INT32
    TYPE_INT64 = LeapPython.Config_TYPE_INT64
    TYPE_UINT32 = LeapPython.Config_TYPE_UINT32
    TYPE_UINT64 = LeapPython.Config_TYPE_UINT64
    TYPE_FLOAT = LeapPython.Config_TYPE_FLOAT
    TYPE_DOUBLE = LeapPython.Config_TYPE_DOUBLE
    TYPE_STRING = LeapPython.Config_TYPE_STRING
















    def get(self, *args):
      type = LeapPython.Config_type(self, *args)
      if LeapPython.Config_is_array(self, *args):
        if type == LeapPython.Config_TYPE_BOOLEAN:
          return LeapPython.Config_get_bool_array(self, *args)
        elif type == LeapPython.Config_TYPE_INT32:
          return LeapPython.Config_get_int_32array(self, *args)
        elif type == LeapPython.Config_TYPE_INT64:
          return LeapPython.Config_get_int_32array(self, *args)
        elif type == LeapPython.Config_TYPE_UINT32:
          return LeapPython.Config_get_uint_32array(self, *args)
        elif type == LeapPython.Config_TYPE_UINT64:
          return LeapPython.Config_get_uint_32array(self, *args)
        elif type == LeapPython.Config_TYPE_FLOAT:
          return LeapPython.Config_get_float_array(self, *args)
        elif type == LeapPython.Config_TYPE_DOUBLE:
          return LeapPython.Config_get_double_array(self, *args)
        elif type == LeapPython.Config_TYPE_STRING:
          return LeapPython.Config_get_string_array(self, *args)
      else:
        if type == LeapPython.Config_TYPE_BOOLEAN:
          return LeapPython.Config_get_bool(self, *args)
        elif type == LeapPython.Config_TYPE_INT32:
          return LeapPython.Config_get_int_32(self, *args)
        elif type == LeapPython.Config_TYPE_INT64:
          return LeapPython.Config_get_int_64(self, *args)
        elif type == LeapPython.Config_TYPE_UINT32:
          return LeapPython.Config_get_uint_32(self, *args)
        elif type == LeapPython.Config_TYPE_UINT64:
          return LeapPython.Config_get_uint_64(self, *args)
        elif type == LeapPython.Config_TYPE_FLOAT:
          return LeapPython.Config_get_float(self, *args)
        elif type == LeapPython.Config_TYPE_DOUBLE:
          return LeapPython.Config_get_double(self, *args)
        elif type == LeapPython.Config_TYPE_STRING:
          return LeapPython.Config_get_string(self, *args)
      return None

    __swig_destroy__ = LeapPython.delete_Config
    __del__ = lambda self : None;
Config_swigregister = LeapPython.Config_swigregister
Config_swigregister(Config)

class Controller(Interface):
    __swig_setmethods__ = {}
    for _s in [Interface]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
    __setattr__ = lambda self, name, value: _swig_setattr(self, Controller, name, value)
    __swig_getmethods__ = {}
    for _s in [Interface]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
    __getattr__ = lambda self, name: _swig_getattr(self, Controller, name)
    __repr__ = _swig_repr
    __swig_destroy__ = LeapPython.delete_Controller
    __del__ = lambda self : None;
    def __init__(self, *args): 
        this = LeapPython.new_Controller(*args)
        try: self.this.append(this)
        except: self.this = this
    def add_listener(self, *args): return LeapPython.Controller_add_listener(self, *args)
    def remove_listener(self, *args): return LeapPython.Controller_remove_listener(self, *args)
    def frame(self, history=0): return LeapPython.Controller_frame(self, history)
    def enable_gesture(self, *args): return LeapPython.Controller_enable_gesture(self, *args)
    def is_gesture_enabled(self, *args): return LeapPython.Controller_is_gesture_enabled(self, *args)
    __swig_getmethods__["is_connected"] = LeapPython.Controller_is_connected_get
    if _newclass:is_connected = _swig_property(LeapPython.Controller_is_connected_get)
    __swig_getmethods__["config"] = LeapPython.Controller_config_get
    if _newclass:config = _swig_property(LeapPython.Controller_config_get)
    __swig_getmethods__["calibrated_screens"] = LeapPython.Controller_calibrated_screens_get
    if _newclass:calibrated_screens = _swig_property(LeapPython.Controller_calibrated_screens_get)
Controller_swigregister = LeapPython.Controller_swigregister
Controller_swigregister(Controller)

class Listener(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Listener, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Listener, name)
    __repr__ = _swig_repr
    def __init__(self): 
        if self.__class__ == Listener:
            _self = None
        else:
            _self = self
        this = LeapPython.new_Listener(_self, )
        try: self.this.append(this)
        except: self.this = this
    __swig_destroy__ = LeapPython.delete_Listener
    __del__ = lambda self : None;
    def on_init(self, *args): return LeapPython.Listener_on_init(self, *args)
    def on_connect(self, *args): return LeapPython.Listener_on_connect(self, *args)
    def on_disconnect(self, *args): return LeapPython.Listener_on_disconnect(self, *args)
    def on_exit(self, *args): return LeapPython.Listener_on_exit(self, *args)
    def on_frame(self, *args): return LeapPython.Listener_on_frame(self, *args)
    def __disown__(self):
        self.this.disown()
        LeapPython.disown_Listener(self)
        return weakref_proxy(self)
Listener_swigregister = LeapPython.Listener_swigregister
Listener_swigregister(Listener)

# This file is compatible with both classic and new-style classes.



########NEW FILE########
__FILENAME__ = Mouse
#William Yager
#Leap Python mouse controller POC


#Mouse functions in OS X
from Quartz.CoreGraphics import (CGEventCreateMouseEvent,CGEventPost,CGDisplayBounds,
    CGEventCreateScrollWheelEvent,CGEventSourceCreate,kCGScrollEventUnitPixel,
    kCGScrollEventUnitLine,kCGEventMouseMoved,kCGEventLeftMouseDragged,
    kCGEventLeftMouseDown,kCGEventLeftMouseUp,kCGMouseButtonLeft,kCGEventRightMouseDown,
    kCGEventRightMouseDown,kCGEventRightMouseUp,kCGMouseButtonRight,kCGHIDEventTap)


#OS X specific: We use CGEventCreateMouseEvent(source, mouse[Event]Type, mouseCursorPosition, mouseButton)
#to make our events, and we post them with CGEventPost(tapLocation, event).
#We can usually/always set "source" to None (Null) and mouseButton to 0 (as the button is implied in the event type)
Event = CGEventCreateMouseEvent  #Easier to type. Alias "Event()" to "CGEventCreateMouseEvent()"

def Post(event):  #Posts the event. I don't want to type "CGEventPost(kCGHIDEventTap," every time.
    CGEventPost(kCGHIDEventTap, event)

def AbsoluteMouseMove(posx,posy):
    event = Event(None, kCGEventMouseMoved, (posx, posy), 0)
    Post(event)

def AbsoluteMouseClick(posx,posy):
    AbsoluteMouseClickDown(posx,posy)
    AbsoluteMouseClickUp(posx,posy)

def AbsoluteMouseClickDown(posx, posy):
    event = Event(None, kCGEventLeftMouseDown, (posx, posy), 0)
    Post(event)

def AbsoluteMouseClickUp(posx, posy):
    event = Event(None, kCGEventLeftMouseUp, (posx, posy), 0)
    Post(event)

def AbsoluteMouseDrag(posx, posy):  #A Drag is a Move where the mouse key is held down
    event = Event(None, kCGEventLeftMouseDragged, (posx, posy), 0)
    Post(event)

def AbsoluteMouseRightClick(posx,posy):
    event = Event(None, kCGEventRightMouseDown, (posx, posy), 0)
    Post(event)
    event = Event(None, kCGEventRightMouseUp, (posx, posy), 0)
    Post(event)

def RelativeMouseScroll(x_movement, y_movement):  #Movements should be no larger than +- 10
    scrollWheelEvent = CGEventCreateScrollWheelEvent(
            None,  #No source
            kCGScrollEventUnitPixel,  #We are using pixel units
            2,  #Number of wheels(dimensions)
            y_movement,
            x_movement)
    CGEventPost(kCGHIDEventTap, scrollWheelEvent)


def GetDisplayWidth():
    return CGDisplayBounds(0).size.width

def GetDisplayHeight():
    return CGDisplayBounds(0).size.height


#A cursor that does commands based on absolute position (good for finger pointing)
class absolute_cursor(object):
    def __init__(self):
        self.x_max = GetDisplayWidth() - 1
        self.y_max = GetDisplayHeight() - 1
        self.left_button_pressed = False
        self.x = 0
        self.y = 0

    def move(self, posx, posy):  #Move to coordinates
        self.x = posx
        self.y = posy
        if self.x > self.x_max: 
            self.x = self.x_max
        if self.y > self.y_max: 
            self.y = self.y_max
        if self.x < 0.0: 
            self.x = 0.0
        if self.y < 0.0: 
            self.y = 0.0
        if self.left_button_pressed:  #We are dragging
            AbsoluteMouseDrag(self.x, self.y)
        else:  #We are not dragging
            AbsoluteMouseMove(self.x, self.y)

    def click(self, posx=None, posy=None):  #Click at coordinates (current coordinates by default)
        if posx == None:
            posx = self.x
        if posy == None:
            posy = self.y
        AbsoluteMouseClick(posx, posy)
    
    def set_left_button_pressed(self, boolean_button):  #Set the state of the left button
        if boolean_button == True:  #Pressed
            self.click_down()
        else:  #Not pressed
            self.click_up()
        
    def click_down(self, posx=None, posy=None):
        if posx == None:
            posx = self.x
        if posy == None:
            posy = self.y
        AbsoluteMouseClickDown(posx, posy)
        self.left_button_pressed = True

    def click_up(self, posx=None, posy=None):
        if posx == None:
            posx = self.x
        if posy == None:
            posy = self.y
        AbsoluteMouseClickUp(posx, posy)
        self.left_button_pressed = False

    def rightClick(self, posx=None, posy=None):
        if posx == None:
            posx = self.x
        if posy == None:
            posy = self.y
        AbsoluteMouseRightClick(posx, posy)

    def scroll(self, x_movement, y_movement):
        RelativeMouseScroll(x_movement, y_movement)


#Allows for relative movement instead of absolute movement. This implementation is not a "true" relative mouse,
#but is really just a relative wrapper for an absolute mouse. Not the best way to do it, but I need to 
#figure out how to send raw "mouse moved _this amount_" events. This class is (as of writing) untested.
#It's only here in case someone else wants to figure out how to do this properly on OS X.
#It's pretty easy on windows. There is a win32 API function for sending raw mouse data that can do this.
class relative_cursor(absolute_cursor):
    def __init__(self):
        absolute_cursor.__init__(self)

    def move(self, x_amt, y_amt):
        self.x = self.x + x_amt
        self.y = self.y + y_amt
        if self.x > self.x_max: 
            self.x = self.x_max
        if self.y > self.y_max: 
            self.y = self.y_max
        if self.x < 0.0: 
            self.x = 0.0
        if self.y < 0.0: 
            self.y = 0.0
        if self.left_button_pressed:  #We are dragging
            AbsoluteMouseDrag(self.x, self.y)
        else:  #We are not dragging
            AbsoluteMouseMove(self.x, self.y)
########NEW FILE########
__FILENAME__ = PalmControl
#William Yager
#Leap Python mouse controller POC
#This file is for palm-tilt and gesture-based control (--palm)


import math
from leap import Leap, Mouse
import Geometry
from MiscFunctions import *


class Palm_Control_Listener(Leap.Listener):  #The Listener that we attach to the controller. This listener is for palm tilt movement
    def __init__(self, mouse):
        super(Palm_Control_Listener, self).__init__()  #Initialize like a normal listener
        #Initialize a bunch of stuff specific to this implementation
        self.cursor = mouse.relative_cursor()  #The cursor object that lets us control mice cross-platform
        self.gesture_debouncer = n_state_debouncer(5,3)  #A signal debouncer that ensures a reliable, non-jumpy gesture detection

    def on_init(self, controller):
        print "Initialized"

    def on_connect(self, controller):
        print "Connected"

    def on_disconnect(self, controller):
        print "Disconnected"

    def on_exit(self, controller):
        print "Exited"

    def on_frame(self, controller):
        frame = controller.frame()  #Grab the latest 3D data
        if not frame.hands.is_empty:  #Make sure we have some hands to work with
            rightmost_hand = None  #We always have at least one "right hand"
            if len(frame.hands) < 2:  #Just one hand
                self.do_mouse_stuff(frame.hands[0])  #If there's only one hand, we assume it's to be used for mouse control
            else:  #Multiple hands. We have a right AND a left
                rightmost_hand = max(frame.hands, key=lambda hand: hand.palm_position.x)  #Get rightmost hand
                leftmost_hand = min(frame.hands, key=lambda hand: hand.palm_position.x)  #Get leftmost hand
                self.do_gesture_recognition(leftmost_hand, rightmost_hand)  #This will run with >1 hands in frame

    def do_mouse_stuff(self, hand):  #Take a hand and use it as a mouse
         hand_normal_direction = Geometry.to_vector(hand.palm_normal)
         hand_direction = Geometry.to_vector(hand.direction)
         roll = hand_normal_direction.roll()
         pitch = hand_normal_direction.pitch()
         mouse_velocity = self.convert_angles_to_mouse_velocity(roll, pitch)
         self.cursor.move(mouse_velocity[0], mouse_velocity[1])

    #The gesture hand signals what action to do,
    #The mouse hand gives extra data (if applicable)
    #Like scroll speed/direction
    def do_gesture_recognition(self, gesture_hand, mouse_hand):
        if len(gesture_hand.fingers) == 2:  #Two open fingers on gesture hand (scroll mode)
            self.gesture_debouncer.signal(2)  #Tell the debouncer we've seen this gesture
        elif len(gesture_hand.fingers) == 1:  #One open finger on gesture hand (click down)
            self.gesture_debouncer.signal(1)
        else:  #No open fingers or 3+ open fingers (click up/no action)
            self.gesture_debouncer.signal(0)
        #Now that we've told the debouncer what we *think* the current gesture is, we must act
        #On what the debouncer thinks the gesture is
        if self.gesture_debouncer.state == 2:  #Scroll mode
            y_scroll_amount = self.velocity_to_scroll_amount(mouse_hand.palm_velocity.y)  #Mouse hand controls scroll amount
            x_scroll_amount = self.velocity_to_scroll_amount(mouse_hand.palm_velocity.x)
            self.cursor.scroll(x_scroll_amount, y_scroll_amount)
        elif self.gesture_debouncer.state == 1:  #Click/drag mode
            if not self.cursor.left_button_pressed: self.cursor.click_down()  #Click down (if needed)
            self.do_mouse_stuff(mouse_hand)  #We may want to click and drag
        elif self.gesture_debouncer.state == 0:  #Move cursor mode
            if self.cursor.left_button_pressed: self.cursor.click_up()  #Click up (if needed)
            self.do_mouse_stuff(mouse_hand)

    def velocity_to_scroll_amount(self, velocity):  #Converts a finger velocity to a scroll velocity
        #The following algorithm was designed to reflect what I think is a comfortable
        #Scrolling behavior.
        vel = velocity  #Save to a shorter variable
        vel = vel + math.copysign(300, vel)  #Add/subtract 300 to velocity
        vel = vel / 150
        vel = vel ** 3  #Cube vel
        vel = vel / 8
        vel = vel * -1  #Negate direction, depending on how you like to scroll
        return vel

    def convert_angles_to_mouse_velocity(self, roll, pitch):  #Angles are in radians
        x_movement = 5.0*math.copysign((4.0*math.sin(roll) + 2.0*roll)*math.sin(roll), roll)
        y_movement = 5.0*math.copysign((4.0*math.sin(pitch) + 2.0*pitch)*math.sin(pitch), pitch)
        return (x_movement, y_movement)

########NEW FILE########
__FILENAME__ = PyLeapMouse
#William Yager
#Leap Python mouse controller POC
import sys
from leap import Leap, Mouse
from PalmControl import Palm_Control_Listener  #For palm-tilt based control
from FingerControl import Finger_Control_Listener  #For finger-pointing control
from MotionControl import Motion_Control_Listener  #For motion control

def show_help():
    print "----------------------------------PyLeapMouse----------------------------------"
    print "Use --finger (or blank) for pointer finger control, and --palm for palm control."
    print "Set smooth aggressiveness (# samples) with \"--smooth-aggressiveness [# samples]\""
    print "Set smooth falloff with \"--smooth-falloff [% per sample]\""
    print "Read README.md for even more info.\n"

def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        show_help()
        return

    print "----------------------------------PyLeapMouse----------------------------------"
    print "Use --finger (or blank) for pointer finger control, and --palm for palm control."
    print "Use -h or --help for more info.\n"

    #Default
    finger_mode = True
    palm_mode = False
    motion_mode = False
    smooth_aggressiveness = 8
    smooth_falloff = 1.3

    for i in range(0,len(sys.argv)):
        arg = sys.argv[i].lower()
        if "--palm" in arg:
            finger_mode = False
            palm_mode = True
            motion_mode = False
        if "--motion" in arg:
            finger_mode = False
            palm_mode = False
            motion_mode = True
        if "--smooth-falloff" in arg:
            smooth_falloff = float(sys.argv[i+1])
        if "--smooth-aggressiveness" in arg:
            smooth_aggressiveness = int(sys.argv[i+1])

    listener = None;  #I'm tired and can't think of a way to organize this segment nicely

    #Create a custom listener object which controls the mouse
    if finger_mode:  #Finger pointer mode
        listener = Finger_Control_Listener(Mouse, smooth_aggressiveness=smooth_aggressiveness, smooth_falloff=smooth_falloff)
        print "Using finger mode..."
    elif palm_mode:  #Palm control mode
        listener = Palm_Control_Listener(Mouse)
        print "Using palm mode..."
    elif motion_mode:  #Motion control mode
        listener = Motion_Control_Listener(Mouse)
        print "Using motion mode..."


    controller = Leap.Controller()  #Get a Leap controller
    controller.set_policy_flags(Leap.Controller.POLICY_BACKGROUND_FRAMES)
    print "Adding Listener."
    controller.add_listener(listener)  #Attach the listener

    #Keep this process running until Enter is pressed
    print "Press Enter to quit..."
    sys.stdin.readline()
    #Remove the sample listener when done
    controller.remove_listener(listener)

main()

########NEW FILE########
__FILENAME__ = Mouse
#William Yager
#Leap Python mouse controller POC


#Mouse functions in Windows
import ctypes
win32 = ctypes.windll.user32

def AbsoluteMouseMove(posx,posy):
    win32.SetCursorPos(int(posx),int(posy))
    #According to some guy on stackoverflow, it might be wise to replace
    #this with
    #win32.mouse_event(win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE,
    #    int(x/SCREEN_WIDTH*65535.0), int(y/SCREEN_HEIGHT*65535.0))
    #but I have not tested this.

def AbsoluteMouseClick(posx,posy):
    #posx,posy ignored
    AbsoluteMouseClickDown(posx,posy)
    AbsoluteMouseClickUp(posx,posy)

def AbsoluteMouseClickDown(posx, posy):
    #posx,posy ignored
    win32.mouse_event(0x02,0,0,0,0)

def AbsoluteMouseClickUp(posx, posy):
    #posx,posy ignored
    win32.mouse_event(0x04,0,0,0,0)

def AbsoluteMouseDrag(posx, posy):  #Only relevant in OS X(?)
    AbsoluteMouseMove(posx, posy)

def AbsoluteMouseRightClick(posx,posy):
    #posx,posy ignored
    win32.mouse_event(0x08,0,0,0,0)
    win32.mouse_event(0x10,0,0,0,0)

def RelativeMouseScroll(x_movement, y_movement):  #Movements should be no larger than +- 10
    #Windows evidently doesn't really support sideways scrolling. 
    win32.mouse_event(0x0800,0,0,int(y_movement),0)

def GetDisplayWidth():
    return win32.GetSystemMetrics(0)

def GetDisplayHeight():
    return win32.GetSystemMetrics(1)


#A cursor that does commands based on absolute position (good for finger pointing)
class absolute_cursor(object):
    def __init__(self):
        self.x_max = GetDisplayWidth() - 1
        self.y_max = GetDisplayHeight() - 1
        self.left_button_pressed = False
        self.x = 0
        self.y = 0

    def move(self, posx, posy):  #Move to coordinates
        self.x = posx
        self.y = posy
        if self.x > self.x_max: 
            self.x = self.x_max
        if self.y > self.y_max: 
            self.y = self.y_max
        if self.x < 0.0: 
            self.x = 0.0
        if self.y < 0.0: 
            self.y = 0.0
        if self.left_button_pressed:  #We are dragging
            AbsoluteMouseDrag(self.x, self.y)
        else:  #We are not dragging
            AbsoluteMouseMove(self.x, self.y)

    def click(self, posx=None, posy=None):  #Click at coordinates (current coordinates by default)
        if posx == None:
            posx = self.x
        if posy == None:
            posy = self.y
        AbsoluteMouseClick(posx, posy)
    
    def set_left_button_pressed(self, boolean_button):  #Set the state of the left button
        if boolean_button == True:  #Pressed
            self.click_down()
        else:  #Not pressed
            self.click_up()
        
    def click_down(self, posx=None, posy=None):
        if posx == None:
            posx = self.x
        if posy == None:
            posy = self.y
        AbsoluteMouseClickDown(posx, posy)
        self.left_button_pressed = True

    def click_up(self, posx=None, posy=None):
        if posx == None:
            posx = self.x
        if posy == None:
            posy = self.y
        AbsoluteMouseClickUp(posx, posy)
        self.left_button_pressed = False

    def rightClick(self, posx=None, posy=None):
        if posx == None:
            posx = self.x
        if posy == None:
            posy = self.y
        AbsoluteMouseRightClick(posx, posy)

    def scroll(self, x_movement, y_movement):
        RelativeMouseScroll(x_movement, y_movement)


#Allows for relative movement instead of absolute movement. This implementation is not a "true" relative mouse,
#but is really just a relative wrapper for an absolute mouse. Not the best way to do it, but I need to 
#figure out how to send raw "mouse moved _this amount_" events. This class is (as of writing) untested.
#It's only here in case someone else wants to figure out how to do this properly on OS X.
#I will be "actually" implementing this on Windows shortly. OSX TBD.
class relative_cursor(absolute_cursor):
    def __init__(self):
        absolute_cursor.__init__(self)

    def move(self, x_amt, y_amt):
        self.x = self.x + x_amt
        self.y = self.y + y_amt
        if self.x > self.x_max: 
            self.x = self.x_max
        if self.y > self.y_max: 
            self.y = self.y_max
        if self.x < 0.0: 
            self.x = 0.0
        if self.y < 0.0: 
            self.y = 0.0
        if self.left_button_pressed:  #We are dragging
            AbsoluteMouseDrag(self.x, self.y)
        else:  #We are not dragging
            AbsoluteMouseMove(self.x, self.y)
########NEW FILE########
