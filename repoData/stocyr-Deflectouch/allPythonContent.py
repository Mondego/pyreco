__FILENAME__ = background
'''
Deflectouch

Copyright (C) 2012  Cyril Stoller

For comments, suggestions or other messages, contact me at:
<cyril.stoller@gmail.com>

This file is part of Deflectouch.

Deflectouch is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Deflectouch is distributed in the hope that it will be fun,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Deflectouch.  If not, see <http://www.gnu.org/licenses/>.
'''

import kivy
kivy.require('1.0.9')

from kivy.uix.image import Image
from kivy.base import EventLoop
from kivy.vector import Vector

from deflector import Deflector


MIN_DEFLECTOR_LENGTH = 100


'''
####################################
##
##   Background Image Class
##
####################################
'''
class Background(Image):
    
    '''
    ####################################
    ##
    ##   On Touch Down
    ##
    ####################################
    '''
    def on_touch_down(self, touch):
        ud = touch.ud
        
        # if a bullet has been fired and is flying now, don't allow ANY change!
        if self.parent.bullet != None:
            return True
        
        for deflector in self.parent.deflector_list:
            if deflector.collide_grab_point(*touch.pos):
                # pass the touch to the deflector scatter
                return super(Background, self).on_touch_down(touch)
        
        # if i didn't wanted to move / scale a deflector and but rather create a new one:
        # search for other 'lonely' touches
              
        for search_touch in EventLoop.touches[:]:
            if 'lonely' in search_touch.ud:
                del search_touch.ud['lonely']
                # so here we have a second touch: try to create a deflector:
                if self.parent.stockbar.new_deflectors_allowed == True:
                    length = Vector(search_touch.pos).distance(touch.pos)
                    # create only a new one if he's not too big and not too small
                    if MIN_DEFLECTOR_LENGTH <= length <= self.parent.stockbar.width:
                        self.create_deflector(search_touch, touch, length)
                    else:
                        self.parent.app.sound['no_deflector'].play()
                else:
                    self.parent.app.sound['no_deflector'].play()
                
                return True
        
        # if no second touch was found: tag the current one as a 'lonely' touch
        ud['lonely'] = True
        
    
    def create_deflector(self, touch_1, touch_2, length):
        self.parent.app.sound['deflector_new'].play()
        deflector = Deflector(touch1=touch_1, touch2=touch_2, length=length)
        self.parent.deflector_list.append(deflector)
        self.add_widget(deflector)
        
        self.parent.stockbar.new_deflector(length)
        
    
    def delete_deflector(self, deflector):
        self.parent.app.sound['deflector_delete'].play()
        self.parent.stockbar.deflector_deleted(deflector.length)
        
        self.remove_widget(deflector)
        self.parent.deflector_list.remove(deflector)
    
    def delete_all_deflectors(self):
        for deflector in self.parent.deflector_list:
            self.remove_widget(deflector)
        self.parent.deflector_list = []
        
        if self.parent.stockbar is not None:        
            self.parent.stockbar.recalculate_stock()

########NEW FILE########
__FILENAME__ = bullet
'''
Deflectouch

Copyright (C) 2012  Cyril Stoller

For comments, suggestions or other messages, contact me at:
<cyril.stoller@gmail.com>

This file is part of Deflectouch.

Deflectouch is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Deflectouch is distributed in the hope that it will be fun,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Deflectouch.  If not, see <http://www.gnu.org/licenses/>.
'''


import kivy
kivy.require('1.0.9')

from kivy.properties import NumericProperty
from kivy.uix.image import Image
from kivy.animation import Animation
from kivy.graphics import Color, Point

from kivy.utils import boundary
from math import tan
from math import sin
from math import pi
from math import radians
from kivy.vector import Vector


class Bullet(Image):
    angle = NumericProperty(0) # in radians!
    animation = None
    
    exploding = False
        
    '''
    ####################################
    ##
    ##   Bullet Behavioral
    ##
    ####################################
    '''
    
    def __init__(self, **kwargs):
        super(Bullet, self).__init__(**kwargs)
        
    def fire(self):
        destination = self.calc_destination(self.angle)
        speed = boundary(self.parent.app.config.getint('GamePlay', 'BulletSpeed'), 1, 10)
        self.animation = self.create_animation(speed, destination)
        
        # start the animation
        self.animation.start(self)
        self.animation.bind(on_complete=self.on_collision_with_edge)
        
        # start to track the position changes
        self.bind(pos=self.callback_pos)
        
    
    def create_animation(self, speed, destination):
        # create the animation
        # t = s/v -> v from 1 to 10 / unit-less
        # NOTE: THE DIFFERENCE BETWEEN TWO RENDERED ANIMATION STEPS
        # MUST *NOT* EXCESS THE RADIUS OF THE BULLET! OTHERWISE I
        # HAVE PROBLEMS DETECTING A COLLISION WITH A DEFLECTOR!!
        time = Vector(self.center).distance(destination) / (speed * 30)
        return Animation(pos=destination, duration=time)
        
    def calc_destination(self, angle):
        # calculate the path until the bullet hits the edge of the screen
        win = self.get_parent_window()
        left = 150.0 * win.width / 1920.0
        right = win.width - 236.0 * win.width / 1920.0
        top = win.height - 50.0 * win.height / 1920.0
        bottom = 96.0 * win.height / 1920.0
        
        bullet_x_to_right = right - self.center_x
        bullet_x_to_left = left - self.center_x
        bullet_y_to_top = top - self.center_y
        bullet_y_to_bottom = bottom - self.center_y
        
        destination_x = 0
        destination_y = 0
        
            
        # this is a little bit ugly, but i couldn't find a nicer way in the hurry
        if 0 <= self.angle < pi/2:
            # 1st quadrant
            if self.angle == 0:
                destination_x = bullet_x_to_right
                destination_y = 0
            else:
                destination_x = boundary(bullet_y_to_top / tan(self.angle), bullet_x_to_left, bullet_x_to_right)
                destination_y = boundary(tan(self.angle) * bullet_x_to_right, bullet_y_to_bottom, bullet_y_to_top)
                
        elif pi/2 <= self.angle < pi:
            # 2nd quadrant
            if self.angle == pi/2:
                destination_x = 0
                destination_y = bullet_y_to_top
            else:
                destination_x = boundary(bullet_y_to_top / tan(self.angle), bullet_x_to_left, bullet_x_to_right)
                destination_y = boundary(tan(self.angle) * bullet_x_to_left, bullet_y_to_bottom, bullet_y_to_top)
                
        elif pi <= self.angle < 3*pi/2:
            # 3rd quadrant
            if self.angle == pi:
                destination_x = bullet_x_to_left
                destination_y = 0
            else:
                destination_x = boundary(bullet_y_to_bottom / tan(self.angle), bullet_x_to_left, bullet_x_to_right)
                destination_y = boundary(tan(self.angle) * bullet_x_to_left, bullet_y_to_bottom, bullet_y_to_top) 
                       
        elif self.angle >= 3*pi/2:
            # 4th quadrant
            if self.angle == 3*pi/2:
                destination_x = 0
                destination_y = bullet_y_to_bottom
            else:
                destination_x = boundary(bullet_y_to_bottom / tan(self.angle), bullet_x_to_left, bullet_x_to_right)
                destination_y = boundary(tan(self.angle) * bullet_x_to_right, bullet_y_to_bottom, bullet_y_to_top)
            
        
        # because all of the calculations above were relative, add the bullet position to it.
        destination_x += self.center_x
        destination_y += self.center_y
        
        return (destination_x, destination_y)
    
    def check_deflector_collision(self, deflector):
        # Here we have a collision Bullet <--> Deflector-bounding-box. But that doesn't mean
        # that there's a collision with the deflector LINE yet. So here's some math stuff
        # for the freaks :) It includes vector calculations, distance problems and trigonometry
        
        # first thing to do is: we need a vector describing the bullet. Length isn't important.
        bullet_position = Vector(self.center)
        bullet_direction = Vector(1, 0).rotate(self.angle * 360 / (2*pi))
        deflector_point1 = Vector(deflector.to_parent(deflector.point1.center[0], deflector.point1.center[1]))
        deflector_point2 = Vector(deflector.to_parent(deflector.point2.center[0], deflector.point2.center[1]))
        
        # then we need a vector describing the deflector line.
        deflector_vector = Vector(deflector_point2 - deflector_point1)
        
        # now we do a line intersection with the deflector line:
        intersection = Vector.line_intersection(bullet_position, bullet_position + bullet_direction, deflector_point1, deflector_point2)
        
        # now we want to proof if the bullet comes from the 'right' side.
        # Because it's possible that the bullet is colliding with the deflectors bounding box but
        # would miss / has already missed the deflector line.
        # We do that by checking if the expected intersection point is BEHIND the bullet position.
        # ('behind' means the bullets direction vector points AWAY from the vector 
        # [bullet -> intersection]. That also means the angle between these two vectors is not 0
        # -> due to some math-engine-internal inaccuracies, i have to check if the angle is greater than one:
        if abs(bullet_direction.angle(intersection - bullet_position)) > 1:
            # if the bullet missed the line already - NO COLLISION
            return False
        
        # now we finally check if the bullet is close enough to the deflector line:
        distance = abs(sin(radians(bullet_direction.angle(deflector_vector)) % (pi/2))) * Vector(intersection - bullet_position).length()
        if distance < (self.width / 2):
            # there is a collision!
            # kill the animation!
            self.animation.unbind(on_complete=self.on_collision_with_edge)
            self.animation.stop(self)
            # call the collision handler
            self.on_collision_with_deflector(deflector, deflector_vector)
            
        
    
    def callback_pos(self, instance, pos):
        # check here if the bullet collides with a deflector, an obstacle or the goal
        # (edge collision detection is irrelevant - the edge is where the bullet animation ends
        # and therefor a callback is raised then)
        
        # first check if there's a collision with deflectors:
        if not len(self.parent.deflector_list) == 0:
            for deflector in self.parent.deflector_list:
                if deflector.collide_widget(self):
                    self.check_deflector_collision(deflector)
                    return
        
        # then check if there's a collision with the goal:
        if not len(self.parent.goal_list) == 0:
            for goal in self.parent.goal_list:
                if self.collide_widget(goal):
                    self.on_collision_with_goal()
                    return
        
        # then check if there's a collision with obstacles:
        if not len(self.parent.obstacle_list) == 0:
            for obstacle in self.parent.obstacle_list:
                if self.collide_widget(obstacle):
                    self.on_collision_with_obstacle()
                    return
    
    def bullet_explode(self):
        if self.exploding == True:
            return
        self.exploding = True
        
        self.unbind(pos=self.callback_pos)
        self.animation.unbind(on_complete=self.on_collision_with_edge)
        self.animation.stop(self)
        
        self.parent.bullet_exploding()
        
    def on_collision_with_edge(self, animation, widget):
        self.bullet_explode()
    
    def on_collision_with_obstacle(self):
        self.bullet_explode()
    
    def on_collision_with_deflector(self, deflector, deflector_vector):
        self.parent.app.sound['deflection'].play()
        
        # flash up the deflector
        Animation.stop_all(deflector.point1, 'color')
        Animation.stop_all(deflector.point2, 'color')
        deflector.point1.color = (1, 1, 1, 1)
        deflector.point2.color = (1, 1, 1, 1)
        animation = Animation(color=(0, 0, 1, 1), duration=3, t='out_expo')
        animation.start(deflector.point1)
        animation.start(deflector.point2)
        
        # calculate deflection angle
        impact_angle = (radians(deflector_vector.angle(Vector(1, 0))) % pi) - (self.angle % pi)
        self.angle = (self.angle + 2*impact_angle) % (2*pi)
        
        destination = self.calc_destination(self.angle)
        speed = boundary(self.parent.app.config.getint('GamePlay', 'BulletSpeed'), 1, 10)
        self.animation = self.create_animation(speed, destination)
        
        # start the animation
        self.animation.start(self)
        self.animation.bind(on_complete=self.on_collision_with_edge)
    
    def on_collision_with_goal(self):
        # i still have some strange exceptions because of multiple function calls:
        if self.parent is None:
            return
        self.parent.level_accomplished()
        
        self.bullet_explode()
        
        
        
        
        
        
        
        
        
        
        
        
########NEW FILE########
__FILENAME__ = deflector
'''
Deflectouch

Copyright (C) 2012  Cyril Stoller

For comments, suggestions or other messages, contact me at:
<cyril.stoller@gmail.com>

This file is part of Deflectouch.

Deflectouch is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Deflectouch is distributed in the hope that it will be fun,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Deflectouch.  If not, see <http://www.gnu.org/licenses/>.
'''


import kivy
kivy.require('1.0.9')

from kivy.graphics import Line, Color
from kivy.properties import ObjectProperty, NumericProperty
from kivy.uix.scatter import Scatter

from kivy.graphics.transformation import Matrix
from math import atan2


MIN_DEFLECTOR_LENGTH = 100
GRAB_RADIUS = 30



class Deflector(Scatter):
    touch1 = ObjectProperty(None)
    touch2 = ObjectProperty(None)
    
    point1 = ObjectProperty(None)
    point2 = ObjectProperty(None)
    
    deflector_line = ObjectProperty(None)
    
    length = NumericProperty(0)
    length_origin = 0
    
    point_pos_origin = []
    
    '''
    ####################################
    ##
    ##   Class Initialisation
    ##
    ####################################
    '''
    def __init__(self, **kwargs):
        super(Deflector, self).__init__(**kwargs)
        
        # DEFLECTOR LINE:
        # Here I rotate and translate the deflector line so that it lays exactly under the two fingers
        # and can be moved and scaled by scatter from now on. Thus I also have to pass the touches to scatter.
        # First i create the line perfectly horizontal but with the correct length. Then i add the two
        # drag points at the beginning and the end.
        
        self.length_origin = self.length
        
        with self.canvas.before:
            Color(.8, .8, .8)
            self.deflector_line = Line(points=(self.touch1.x, self.touch1.y - 1, self.touch1.x + self.length, self.touch1.y - 1))
            self.deflector_line2 = Line(points=(self.touch1.x, self.touch1.y + 1, self.touch1.x + self.length, self.touch1.y + 1))
        
        '''
        self.deflector_line = Image(source='graphics/beta/deflector_blue_beta2.png',
                                    allow_stretch=True,
                                    keep_ratio=False,
                                    size=(self.length, 20),
                                    center_y=(self.touch1.y),
                                    x=self.touch1.x)
        '''
        
        # set the right position for the two points:
        self.point1.center = self.touch1.pos
        self.point2.center = self.touch1.x + self.length, self.touch1.y
        self.point_pos_origin = [self.point1.x, self.point1.y, self.point2.x, self.point2.y]
        
        
        # rotation:
        dx = self.touch2.x - self.touch1.x
        dy = self.touch2.y - self.touch1.y
        angle = atan2(dy, dx)
        
        rotation_matrix = Matrix().rotate(angle, 0, 0, 1)
        self.apply_transform(rotation_matrix, post_multiply=True, anchor=self.to_local(self.touch1.x, self.touch1.y))
        
        # We have to adjust the bounding box of ourself to the dimension of all the canvas objects (Do we have to?)
        #self.size = (abs(self.touch2.x - self.touch1.x), abs(self.touch2.y - self.touch1.y))
        #self.pos = (min(self.touch1.x, self.touch2.x), min(self.touch1.y, self.touch2.y))
        
        # Now we finally add both touches we received to the _touches list of the underlying scatter class structure. 
        self.touch1.grab(self)
        self._touches.append(self.touch1)
        self._last_touch_pos[self.touch1] = self.touch1.pos
        
        self.touch2.grab(self)
        self._touches.append(self.touch2)
        self._last_touch_pos[self.touch2] = self.touch2.pos
        
        self.point1.bind(size=self.size_callback)
    
    def size_callback(self, instance, size):
        # problem: if the points are resized (scatter resized them, kv-rule resized them back),
        # their center isn't on the touch point anymore.
        self.point1.pos = self.point_pos_origin[0] + (40 - size[0])/2, self.point_pos_origin[1] + (40 - size[0])/2
        self.point2.pos = self.point_pos_origin[2] + (40 - size[0])/2, self.point_pos_origin[3] + (40 - size[0])/2
        
        # feedback to the stockbar: reducing of the deflector material stock:
        #self.length = Vector(self.touch1.pos).distance(self.touch2.pos)
        self.length = self.length_origin * self.scale
        try:
            self.parent.parent.stockbar.recalculate_stock()
        except Exception, e:
            return
        # get the current stock from the root widget:
        current_stock = self.parent.parent.stockbar.width
        stock_for_me = current_stock + self.length
        
        # now set the limitation for scaling:
        self.scale_max = stock_for_me / self.length_origin
        
        if self.length < MIN_DEFLECTOR_LENGTH:
            self.point1.color = (1, 0, 0, 1)
            self.point2.color = (1, 0, 0, 1)
        else:
            self.point1.color = (0, 0, 1, 1)
            self.point2.color = (0, 0, 1, 1)
        
        
    
    def collide_widget(self, wid):
        point1_parent = self.to_parent(self.point1.center[0], self.point1.center[1])
        point2_parent = self.to_parent(self.point2.center[0], self.point2.center[1])
        
        if max(point1_parent[0], point2_parent[0]) < wid.x:
            return False
        if min(point1_parent[0], point2_parent[0]) > wid.right:
            return False
        if max(point1_parent[1], point2_parent[1]) < wid.y:
            return False
        if min(point1_parent[1], point2_parent[1]) > wid.top:
            return False
        return True
    
    def collide_point(self, x, y):
        # this function is used exclusively by the underlying scatter functionality.
        # therefor i can control when a touch will be dispatched from here.
        point1_parent = self.to_parent(self.point1.center[0], self.point1.center[1])
        point2_parent = self.to_parent(self.point2.center[0], self.point2.center[1])
        
        return min(point1_parent[0], point2_parent[0]) - GRAB_RADIUS <= x <= max(point1_parent[0], point2_parent[0]) + GRAB_RADIUS \
           and min(point1_parent[1], point2_parent[1]) - GRAB_RADIUS <= y <= max(point1_parent[1], point2_parent[1]) + GRAB_RADIUS
    
    def collide_grab_point(self, x, y):
        point1_parent = self.to_parent(self.point1.center[0], self.point1.center[1])
        point2_parent = self.to_parent(self.point2.center[0], self.point2.center[1])
        
        return point1_parent[0] - GRAB_RADIUS <= x <= point1_parent[0] + GRAB_RADIUS and point1_parent[1] - GRAB_RADIUS <= y <= point1_parent[1] + GRAB_RADIUS \
            or point2_parent[0] - GRAB_RADIUS <= x <= point2_parent[0] + GRAB_RADIUS and point2_parent[1] - GRAB_RADIUS <= y <= point2_parent[1] + GRAB_RADIUS
    
    '''
    ####################################
    ##
    ##   On Touch Down
    ##
    ####################################
    '''
    def on_touch_down(self, touch):
        if self.parent.parent.app.sound['deflector_down'].status != 'play':
            self.parent.parent.app.sound['deflector_down'].play()
        
        return super(Deflector, self).on_touch_down(touch)
    
    '''
    ####################################
    ##
    ##   On Touch Up
    ##
    ####################################
    '''
    def on_touch_up(self, touch):
        # if the deflector want's to be removed (touches too close to each other):
        if self.length < MIN_DEFLECTOR_LENGTH and self.parent != None:
            self.parent.delete_deflector(self)
            return True
        
        if self.parent != None and self.collide_grab_point(*touch.pos):
            if self.parent.parent.app.sound['deflector_up'].status != 'play':
                self.parent.parent.app.sound['deflector_up'].play()
        
        return super(Deflector, self).on_touch_up(touch)



########NEW FILE########
__FILENAME__ = main
'''
Deflectouch

Copyright (C) 2012  Cyril Stoller

For comments, suggestions or other messages, contact me at:
<cyril.stoller@gmail.com>

This file is part of Deflectouch.

Deflectouch is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Deflectouch is distributed in the hope that it will be fun,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Deflectouch.  If not, see <http://www.gnu.org/licenses/>.
'''


import kivy
kivy.require('1.0.9')

from kivy.app import App
from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.factory import Factory
from kivy.utils import boundary
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.audio import SoundLoader

from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from math import sin
from math import cos
from math import radians

from random import randint


from background import Background
from tank import Tank
from bullet import Bullet
from stockbar import Stockbar


'''
####################################
##
##   GLOBAL SETTINGS
##
####################################
'''

VERSION = '1.0'

LEVEL_WIDTH = 16
LEVEL_HEIGHT = 16


'''
####################################
##
##   Setting Dialog Class
##
####################################
'''
class SettingDialog(BoxLayout):
    music_slider = ObjectProperty(None)
    sound_slider = ObjectProperty(None)
    speed_slider = ObjectProperty(None)
    
    root = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super(SettingDialog, self).__init__(**kwargs)
        
        self.music_slider.bind(value=self.update_music_volume)
        self.sound_slider.bind(value=self.update_sound_volume)
        self.speed_slider.bind(value=self.update_speed)
    
    def update_music_volume(self, instance, value):
        # write to app configs
        self.root.app.config.set('General', 'Music', str(int(value)))
        self.root.app.config.write()
        self.root.app.music.volume = value / 100.0
    
    def update_sound_volume(self, instance, value):
        # write to app configs
        self.root.app.config.set('General', 'Sound', str(int(value)))
        self.root.app.config.write()
        for item in self.root.app.sound:
            self.root.app.sound[item].volume = value / 100.0
    
    def update_speed(self, instance, value):
        # write to app configs
        self.root.app.config.set('GamePlay', 'BulletSpeed', str(int(value)))
        self.root.app.config.write()
    
    def display_help_screen(self):
        self.root.setting_popup.dismiss()
        self.root.display_help_screen()
    
    def dismiss_parent(self):
        self.root.setting_popup.dismiss()
    

'''
####################################
##
##   Main Widget Class
##
####################################
'''
class DeflectouchWidget(Widget):
    app = ObjectProperty(None)
    version = StringProperty(VERSION)
    
    level = NumericProperty(1)
    lives = NumericProperty(3)
    
    bullet = None
    setting_popup = None
    stockbar = None
    
    deflector_list = []
    obstacle_list = []
    goal_list = []
    
    max_stock = 0
    
    level_build_index = 0
    
    
    '''
    ####################################
    ##
    ##   GUI Functions
    ##
    ####################################
    '''
    def fire_button_pressed(self):
        if self.bullet:
            # if there is already a bullet existing (which means it's flying around or exploding somewhere)
            # don't fire.
            return
        
        self.app.sound['bullet_start'].play()
        
        # create a bullet, calculate the start position and fire it.
        tower_angle = radians(self.tank.tank_tower_scatter.rotation)
        tower_position = self.tank.pos
        bullet_position = (tower_position[0] + 48 + cos(tower_angle) * 130, tower_position[1] + 70 + sin(tower_angle) * 130)
        self.bullet = Bullet(angle=tower_angle)
        self.bullet.center = bullet_position
        self.add_widget(self.bullet)
        self.bullet.fire()
    
    
    def reset_button_pressed(self):
        self.app.sound['reset'].play()
        
        self.reset_level()
        
    
    def level_button_pressed(self):
        self.app.sound['switch'].play()
        
        # create a popup with all the levels
        grid_layout = GridLayout(cols=8,rows=5,spacing=10, padding=10)
        
        enable_next_row = True
        row_not_complete = False
        for row in range(5):
            for collumn in range(8):
                button = Button(text=str(row*8 + (collumn + 1)),bold=True,font_size=30)
                
                if enable_next_row == True:
                    # if this row is already enabled:
                    button.bind(on_press=self.load_level)
                
                    if self.app.config.get('GamePlay', 'Levels')[row*8 + collumn] == '1':
                        # if level was already done, green button
                        button.background_color = (0, 1, 0, 1)
                    else:
                        # if level not yet done but enabled though, red button
                        button.background_color = (1, 0, 0, 0.5)
                        
                        # and do NOT enable the next row then:
                        row_not_complete = True
                
                else:
                    # if not yet enabled:
                    button.background_color = (0.1, 0.05, 0.05, 1)
                    
                grid_layout.add_widget(button)
            
            if row_not_complete == True:
                enable_next_row = False
        
        popup = Popup(title='Level List (if you finished a row, the next row will get enabled!)',
                      content=grid_layout,
                      size_hint=(0.5, 0.5))
        popup.open()
    
    
    def settings_button_pressed(self):
        self.app.sound['switch'].play()
        
        # the first time the setting dialog is called, initialize its content.
        if self.setting_popup is None:
            
            self.setting_popup = Popup(attach_to=self,
                                       title='DeflecTouch Settings',
                                       size_hint=(0.3, 0.5))
            
            self.setting_dialog = SettingDialog(root=self)
            
            self.setting_popup.content = self.setting_dialog
        
            self.setting_dialog.music_slider.value = boundary(self.app.config.getint('General', 'Music'), 0, 100)
            self.setting_dialog.sound_slider.value = boundary(self.app.config.getint('General', 'Sound'), 0, 100)
            self.setting_dialog.speed_slider.value = boundary(self.app.config.getint('GamePlay', 'BulletSpeed'), 1, 10)
        
        self.setting_popup.open()
        
        
    def display_help_screen(self):
        # display the help screen on a Popup
        image = Image(source='graphics/help_screen.png')
        
        help_screen = Popup(title='Quick Guide through DEFLECTOUCH',
                            attach_to=self,
                            size_hint=(0.98, 0.98),
                            content=image)
        image.bind(on_touch_down=help_screen.dismiss)
        help_screen.open()
    
    
    '''
    ####################################
    ##
    ##   Game Play Functions
    ##
    ####################################
    '''
    
    def bullet_exploding(self):
        self.app.sound['explosion'].play()
        
        # create an animation on the old bullets position:
        # bug: gif isn't transparent
        #old_pos = self.bullet.center
        #self.bullet.anim_delay = 0.1
        #self.bullet.size = 96, 96
        #self.bullet.center = old_pos
        #self.bullet.source = 'graphics/explosion.gif'
        #Clock.schedule_once(self.bullet_exploded, 1)
        
        self.remove_widget(self.bullet)
        self.bullet = None
        # or should i write del self.bullet instead?
        
        self.lives -= 1
        if self.lives == 0:
            self.reset_level()
    
    
    def level_accomplished(self):
        self.app.sound['accomplished'].play()
        
        # store score in config: (i have to convert the string to a list to do specific char writing)
        levels_before = list(self.app.config.get('GamePlay', 'Levels'))
        levels_before[self.level - 1] = '1'
        self.app.config.set('GamePlay', 'Levels', "".join(levels_before))
        self.app.config.write()
        
        # show up a little image with animation: size*2 and out_bounce and the wait 1 sec
        image = Image(source='graphics/accomplished.png', size_hint=(None, None), size=(200, 200))
        image.center=self.center
        animation = Animation(size=(350, 416), duration=1, t='out_bounce')
        animation &= Animation(center=self.center, duration=1, t='out_bounce')
        animation += Animation(size=(350, 416), duration=1) # little hack to sleep for 1 sec
        
        self.add_widget(image)
        animation.start(image)
        animation.bind(on_complete=self.accomplished_animation_complete)
    
    
    def accomplished_animation_complete(self, animation, widget):
        self.remove_widget(widget)
        
        # open the level dialog?
        #self.level_button_pressed()
        
        # no. just open the next level.
        if self.level != 40:
            if self.level % 8 == 0:
                # if it was the last level of one row, another row has been unlocked!
                Popup(title='New levels unlocked!', content=Label(text='Next 8 levels unlocked!', font_size=18), size_hint=(0.3, 0.15)).open()
            
            self.reset_level()
            self.load_level(self.level + 1)
            
        
    def reset_level(self):
        # first kill the bullet
        if self.bullet != None:
            self.bullet.unbind(pos=self.bullet.callback_pos)
            self.bullet.animation.unbind(on_complete=self.bullet.on_collision_with_edge)
            self.bullet.animation.stop(self.bullet)
            self.remove_widget(self.bullet)
            self.bullet = None
        
        # then delete all the deflectors.
        self.background.delete_all_deflectors()
        
        # now the user can begin once again with 3 lives:
        self.lives = 3
    
    
    def load_level(self, level):
        BRICK_WIDTH = self.height / 17.73
        LEVEL_OFFSET = [self.center_x - (LEVEL_WIDTH/2) * BRICK_WIDTH, self.height / 12.5]
        
        # i have to check if the function is called by a level button in the level popup OR with an int as argument:
        if not isinstance(level, int):
            level = int(level.text)
            # and if the function was called by a button, play a sound
            self.app.sound['select'].play()
        
        # try to load the level image
        try:
            level_image = kivy.core.image.Image.load(self.app.directory + '/levels/level%02d.png' % level, keep_data=True)
        except Exception, e:
            error_text = 'Unable to load Level %d!\n\nReason: %s' % (level, e)
            Popup(title='Level loading error:', content=Label(text=error_text, font_size=18), size_hint=(0.3, 0.2)).open()
            return
        
        # First of all, delete the old level:
        self.reset_level()
        
        for obstacle in self.obstacle_list:
            self.background.remove_widget(obstacle)
        self.obstacle_list = []
        
        for goal in self.goal_list:
            self.background.remove_widget(goal)
        self.goal_list = []
        
        if self.stockbar != None:
            self.remove_widget(self.stockbar)
        self.max_stock = 0
        
        # set level inital state
        self.lives = 3
        self.level = level
        
        for y in range(LEVEL_HEIGHT, 0, -1):
            for x in range(LEVEL_WIDTH):
                color = level_image.read_pixel(x, y)
                if len(color) > 3:
                    # if there was transparency stored in the image, cut it.
                    color.pop()
                
                if color == [0, 0, 0]:
                    # create obstacle brick on white pixels
                    image = Image(source=('graphics/brick%d.png' % randint(1, 4)),
                                  x = LEVEL_OFFSET[0] + x * BRICK_WIDTH,
                                  y = LEVEL_OFFSET[1] + (y-1) * BRICK_WIDTH,
                                  size = (BRICK_WIDTH, BRICK_WIDTH),
                                  allow_stretch = True)
                    self.obstacle_list.append(image)
                    # the actual widget adding is done in build_level()
                    #self.background.add_widget(image)
                
                elif color == [0, 0, 1]:
                    # create a goal brick on blue pixels
                    image = Image(source=('graphics/goal%d.png' % randint(1, 4)),
                                  x = LEVEL_OFFSET[0] + x * BRICK_WIDTH,
                                  y = LEVEL_OFFSET[1] + (y-1) * BRICK_WIDTH,
                                  size = (BRICK_WIDTH, BRICK_WIDTH),
                                  allow_stretch = True)
                    self.goal_list.append(image)
                    # the actual widget adding is done in build_level()
                    #self.background.add_widget(image)
                    
        
        # but in the lowermost row there is also stored the value for the maximum stock 
        for x in range(LEVEL_WIDTH):
            color = level_image.read_pixel(x, 0)
            if len(color) > 3:
                # if there was transparency stored in the image, cut it.
                color.pop()
                    
            if color == [1, 0, 0]:
                self.max_stock += 1
        
        # now i set up the stockbar widget:
        self.max_stock = self.max_stock * self.width/1.4/LEVEL_WIDTH
        self.stockbar = Stockbar(max_stock=self.max_stock,
                                 x=self.center_x-self.max_stock/2,
                                 center_y=self.height/16 + 20)
        self.add_widget(self.stockbar)
        
        # now start to build up the level:
        self.level_build_index = 0
        if len(self.obstacle_list) != 0:
            Clock.schedule_interval(self.build_level, 0.01)
        
        
    def build_level(self, instance):
        #if self.level_build_index % int(0.02 / (0.5 / (len(self.obstacle_list) + len(self.goal_list)))) == 0:
            # play a sound every now and then:
        self.app.sound['beep'].play()
        
        if self.level_build_index < len(self.obstacle_list):
            self.background.add_widget(self.obstacle_list[self.level_build_index])
        else:
            if self.level_build_index - len(self.obstacle_list) != len(self.goal_list):
                self.background.add_widget(self.goal_list[self.level_build_index - len(self.obstacle_list)])
            else:
                # we're done. Disable the schedule
                return False
        self.level_build_index += 1

Factory.register("Tank", Tank)
Factory.register("Background", Background)
Factory.register("Stockbar", Stockbar)


'''
####################################
##
##   Main Application Class
##
####################################
'''
class Deflectouch(App):
    title = 'Deflectouch'
    icon = 'icon.png'
    
    sound = {}
    music = None
    
    
    def build(self):
        # print the application informations
        print '\nDeflectouch v%s  Copyright (C) 2012  Cyril Stoller' % VERSION
        print 'This program comes with ABSOLUTELY NO WARRANTY'
        print 'This is free software, and you are welcome to redistribute it'
        print 'under certain conditions; see the source code for details.\n'

        from kivy.base import EventLoop
        EventLoop.ensure_window()
        self.window = EventLoop.window
        
        # create the root widget and give it a reference of the application instance (so it can access the application settings)
        self.deflectouchwidget = DeflectouchWidget(app=self)
        self.root = self.deflectouchwidget
        
        
        # start the background music:
        self.music = SoundLoader.load('sound/deflectouch.ogg')
        self.music.volume = self.config.getint('General', 'Music') / 100.0
        self.music.bind(on_stop=self.sound_replay)
        self.music.play()
        
        # load all other sounds:
        self.sound['switch'] = SoundLoader.load('sound/switch.ogg')
        self.sound['select'] = SoundLoader.load('sound/select.ogg')
        self.sound['reset'] = SoundLoader.load('sound/reset.ogg')
        self.sound['beep'] = SoundLoader.load('sound/beep.ogg')
        
        self.sound['bullet_start'] = SoundLoader.load('sound/bullet_start.ogg')
        self.sound['explosion'] = SoundLoader.load('sound/explosion.ogg')
        self.sound['accomplished'] = SoundLoader.load('sound/accomplished.ogg')
        
        self.sound['no_deflector'] = SoundLoader.load('sound/no_deflector.ogg')
        self.sound['deflector_new'] = SoundLoader.load('sound/deflector_new.ogg')
        self.sound['deflector_down'] = SoundLoader.load('sound/deflector_down.ogg')
        self.sound['deflector_up'] = SoundLoader.load('sound/deflector_up.ogg')
        self.sound['deflector_delete'] = SoundLoader.load('sound/deflector_delete.ogg')
        self.sound['deflection'] = SoundLoader.load('sound/deflection.ogg')
        
        sound_volume = self.config.getint('General', 'Sound') / 100.0
        for item in self.sound:
            self.sound[item].volume = sound_volume
        
        # continue on the last level which wasn't finished
        level_opened = False
        for counter, char  in enumerate(self.config.get('GamePlay', 'Levels')):
            # if I found a level not yet done, continue with that
            if char == '0':
                self.deflectouchwidget.load_level(counter + 1)
                level_opened = True
                break
        
        # if all levels were completed, just open the last one.
        if level_opened == False:
            self.deflectouchwidget.load_level(40)
        
        # if the user started the game the first time, display quick start guide
        if self.config.get('General', 'FirstStartup') == 'Yes':
            
            Clock.schedule_once(self.welcome_screen, 2)
            
            self.config.set('General', 'FirstStartup', 'No')
            self.config.write()
    
   
    def build_config(self, config):
        config.adddefaultsection('General')
        config.setdefault('General', 'Music', '40')
        config.setdefault('General', 'Sound', '100')
        config.setdefault('General', 'FirstStartup', 'Yes')
        
        config.adddefaultsection('GamePlay')
        config.setdefault('GamePlay', 'BulletSpeed', '10')
        config.setdefault('GamePlay', 'Levels', '0000000000000000000000000000000000000000')
    
    def welcome_screen(self, instance):
        self.root.display_help_screen()
    
    def sound_replay(self, instance):
        if self.music.status != 'play':
            self.music.play()


if __name__ in ('__main__', '__android__'):
    Deflectouch().run()
    

########NEW FILE########
__FILENAME__ = stockbar
'''
Deflectouch

Copyright (C) 2012  Cyril Stoller

For comments, suggestions or other messages, contact me at:
<cyril.stoller@gmail.com>

This file is part of Deflectouch.

Deflectouch is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Deflectouch is distributed in the hope that it will be fun,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Deflectouch.  If not, see <http://www.gnu.org/licenses/>.
'''

import kivy
kivy.require('1.0.9')

from kivy.uix.image import Image
from kivy.properties import NumericProperty

MIN_DEFLECTOR_LENGTH = 100


'''
####################################
##
##   Stock Bar Image Class
##
####################################
'''
class Stockbar(Image):
    max_stock = NumericProperty(0)
    
    new_deflectors_allowed = True
    
    
    def recalculate_stock(self):
        # this function is called every time a deflector size is changing
        # first sum up all the deflectors on screen
        length_sum = 0
        
        if not len(self.parent.deflector_list) == 0:
            for deflector in self.parent.deflector_list:
                length_sum += deflector.length
        
        self.width = self.max_stock - length_sum
        
        if self.width < MIN_DEFLECTOR_LENGTH:
            # if the stock material doesn't suffice for a new deflector, disable new deflectors
            self.source = 'graphics/deflector_red.png'
            self.new_deflectors_allowed = False
        elif self.width <= 0:
            # if all the stock material was used up, disable new deflectors
            self.new_deflectors_allowed = False
        else:
            self.source = 'graphics/deflector_blue.png'
            self.new_deflectors_allowed = True
    
    def new_deflector(self, length):
        # is called when a new deflector is created.
        self.width -= length
    
    def deflector_deleted(self, length):
        self.width += length



########NEW FILE########
__FILENAME__ = tank
'''
Deflectouch

Copyright (C) 2012  Cyril Stoller

For comments, suggestions or other messages, contact me at:
<cyril.stoller@gmail.com>

This file is part of Deflectouch.

Deflectouch is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Deflectouch is distributed in the hope that it will be fun,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Deflectouch.  If not, see <http://www.gnu.org/licenses/>.
'''


import kivy
kivy.require('1.0.9')

from kivy.properties import ObjectProperty
from kivy.graphics.transformation import Matrix
from kivy.uix.widget import Widget

from kivy.utils import boundary
from math import radians
from math import atan2
from math import pi

'''
####################################
##
##   Tank Class
##
####################################
'''
class Tank(Widget):
    tank_tower_scatter = ObjectProperty(None)
    
    '''
    ####################################
    ##
    ##   On Touch Down
    ##
    ####################################
    '''
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        else:
            touch.ud['tank_touch'] = True
            return True
            
        
    
    '''
    ####################################
    ##
    ##   On Touch Move
    ##
    ####################################
    '''
    def on_touch_move(self, touch):
        ud = touch.ud
        
        if not 'tank_touch' in ud:
            return False
        
        if 'rotation_mode' in ud:
            # if the current touch is already in the 'rotate' mode, rotate the tower.
            dx = touch.x - self.center_x
            dy = touch.y - self.center_y
            angle = boundary(atan2(dy, dx) * 360 / 2 / pi, -60, 60)
            
            angle_change = self.tank_tower_scatter.rotation - angle
            rotation_matrix = Matrix().rotate(-radians(angle_change), 0, 0, 1)
            self.tank_tower_scatter.apply_transform(rotation_matrix, post_multiply=True, anchor=(105, 15))
        
        elif touch.x > self.right:
            # if the finger moved too far to the right go into rotation mode
            ud['rotation_mode'] = True
        
        else:
            # if the user wants only to drag the tank up and down, let him do it!
            self.y += touch.dy
            pass


########NEW FILE########
