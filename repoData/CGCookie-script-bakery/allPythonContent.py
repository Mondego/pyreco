__FILENAME__ = add-mesh_polysphere
bl_info = {
    "name": "Add Poly Sphere",
    "location": "View3D > Add > Mesh > Add Poly Sphere",
    "description": "Adds a poly cube to the scene via Add > Mesh > Poly Sphere",
    "author": "Jonathan Williamson",
    "version": (0,3),
    "blender": (2, 6, 5),
    "category": "Add Mesh",
    }

import bpy

#Create the operator for adding a poly sphere
class addPolySphere(bpy.types.Operator):
    """Add a poly sphere to the scene"""
    bl_idname = "mesh.sphere_poly_add"
    bl_label = "Add Poly Sphere"
    bl_options = {'REGISTER', 'UNDO'}    
    
    #Add the subsurf modifier, apply it, and spherify the mesh
    def execute(self, context):
        obj = context.active_object
        
        #Add a cube starting point
        bpy.ops.mesh.primitive_cube_add(view_align=False)
        
        #Add a subsurf modifier to the cube
        bpy.ops.object.modifier_add(type='SUBSURF')
                
        #Find the current selection
        obj = context.active_object
        
        #Find modifiers added to current selection
        activeMod = obj.modifiers
        
        #Change settings on the modifier
        for mod in obj.modifiers:
            if mod.type == 'SUBSURF':
                activeMod[mod.name].show_only_control_edges = True
                activeMod[mod.name].levels = 2
                
                #Apply the subsurf modifier
                bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mod.name)
        
        #Switch to Edit Mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        #Sphereize the mesh
        bpy.ops.transform.tosphere(value=1)
        
        #Switch back to Object Mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
    
        return {'FINISHED'}
 


#Create the Menu entry
def menu_func(self, context):
    self.layout.operator(addPolySphere.bl_idname, icon='MOD_SUBSURF')
                
def register():
    bpy.utils.register_class(addPolySphere)
    
    #Add the menu entry to the Add menu
    bpy.types.INFO_MT_mesh_add.append(menu_func)
    
def unregister():
    bpy.utils.unregister_class(addPolySphere)
    
    #remove the menu entry from the Add menu
    bpy.types.INFO_MT_mesh_add.remove(menu_func)
    
if __name__ == "__main__":
    register()
########NEW FILE########
__FILENAME__ = add-mesh_skin-object
bl_info = {
    "name": "Add Skin Object",
    "location": "View3D > Add > Mesh > Add Skin Object",
    "description": "Adds a single edge object with a Skin modifier",
    "author": "Jonathan Williamson",
    "version": (0,1),
    "blender": (2, 6, 6),
    "category": "Add Mesh",
    }

import bpy

class addSkin(bpy.types.Operator):
    """Add a Skin Object"""
    bl_idname = "object.skin_add"
    bl_label = "Add Skin Object"
    bl_options = {'REGISTER', 'UNDO'}    
    
    def execute(self, context):
    
        scene = bpy.context.scene
        
        verts = [(0, 0, 0), (0, 0, 2)]
        edges = [(0, 1)]
        
        # create the skin mesh data and object
        skin_mesh = bpy.data.meshes.new("skin")
        skin_object = bpy.data.objects.new("Skin Object", skin_mesh)
        
        # place the skin object at the 3D Cursor
        skin_object.location = bpy.context.scene.cursor_location
        bpy.context.scene.objects.link(skin_object)
        
        skin_mesh.from_pydata(verts, edges, [])
        
        skin_object.select = True
        scene.objects.active = skin_object

######## Old Hack ############
        
#        bpy.ops.transform.resize(value=(0   , 1, 1))
#        bpy.ops.object.transform_apply(scale=True)
#        
#        bpy.ops.object.editmode_toggle()
#        bpy.ops.mesh.remove_doubles(threshold=0.0001, use_unselected=True)
#        bpy.ops.object.editmode_toggle()

##############################
        
        # add a mirror modifier
        bpy.ops.object.modifier_add(type='MIRROR')
        #bpy.context.active_object.modifiers["Mirror"].use_clip = True
        
        # add a skin modifier
        bpy.ops.object.modifier_add(type='SKIN')
        
        # add a subsurf modifier
        bpy.ops.object.modifier_add(type='SUBSURF')
        
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(addSkin.bl_idname, icon='MOD_SKIN')
            
def register():
    bpy.utils.register_class(addSkin)
    bpy.types.INFO_MT_mesh_add.append(menu_func)
    
def unregister():
    bpy.utils.unregister_class(addSkin)
    bpy.types.INFO_MT_mesh_add.remove(menu_func)
    
if __name__ == "__main__":
    register()
########NEW FILE########
__FILENAME__ = contour_classes
'''
Copyright (C) 2013 CG Cookie
http://cgcookie.com
hello@cgcookie.com

Created by Patrick Moore

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

####class definitions####

import bpy
import math
import time
from mathutils import Vector, Quaternion
from mathutils.geometry import intersect_point_line, intersect_line_plane
import contour_utilities
from bpy_extras.view3d_utils import location_3d_to_region_2d
from bpy_extras.view3d_utils import region_2d_to_vector_3d
from bpy_extras.view3d_utils import region_2d_to_location_3d
import blf
#from development.contour_tools import contour_utilities

class ContourControlPoint(object):
    
    def __init__(self, parent, x, y, color = (1,0,0,1), size = 2, mouse_radius=10):
        self.desc = 'CONTROL_POINT'
        self.x = x
        self.y = y
        self.world_position = None #to be updated later
        self.color = color
        self.size = size
        self.mouse_rad = mouse_radius
        self.parent = parent
        
    def mouse_over(self,x,y):
        dist = (self.x -x)**2 + (self.y - y)**2
        #print(dist < 100)
        if dist < 100:
            return True
        else:
            return False
        
    def screen_from_world(self,context):
        point = location_3d_to_region_2d(context.region, context.space_data.region_3d,self.world_position)
        self.x = point[0]
        self.y = point[1]
        
    def screen_to_world(self,context):
        region = context.region  
        rv3d = context.space_data.region_3d
        if self.world_position:
            self.world_position = region_2d_to_location_3d(region, rv3d, (self.x, self.y),self.world_position)

class ExistingVertList(object):
    def __init__(self, verts, edges, mx):
        self.desc = 'EXISTING_VERT_LIST'
        
        edge_keys = [[ed.verts[0].index, ed.verts[1].index] for ed in edges]
        remaining_keys = [i for i in range(1,len(edge_keys))]
        
        vert_inds_unsorted = [vert.index for vert in verts]
        vert_inds_sorted = [edge_keys[0][0], edge_keys[0][1]]
        
        iterations = 0
        max_iters = math.factorial(len(remaining_keys))
        while len(remaining_keys) > 0 and iterations < max_iters:
            print(remaining_keys)
            iterations += 1
            for key_index in remaining_keys:
                l = len(vert_inds_sorted) -1
                key_set = set(edge_keys[key_index])
                last_v = {vert_inds_sorted[l]}
                if  key_set & last_v:
                    vert_inds_sorted.append(int(list(key_set - last_v)[0]))
                    remaining_keys.remove(key_index)
                    break
        
        if vert_inds_sorted[0] == vert_inds_sorted[-1]:
            cyclic = True
            vert_inds_sorted.pop()
        else:
            cyclic = False
            
        self.eds_simple = [[i,i+1] for i in range(0,len(vert_inds_sorted)-1)]
        if cyclic:
            self.eds_simple.append([len(vert_inds_sorted)-1,0])
            
        self.verts_simple = []
        for i in vert_inds_sorted:
            v = verts[vert_inds_unsorted.index(i)]
            self.verts_simple.append(mx * v.co)
            
        
    def connectivity_analysis(self,other):
        
        
        COM_self = contour_utilities.get_com(self.verts_simple)
        COM_other = contour_utilities.get_com(other.verts_simple)
        delta_com_vect = COM_self - COM_other  #final - initial :: self - other
        delta_com_vect.normalize()
        

        
        ideal_to_com = 0
        for i, v in enumerate(self.verts_simple):
            connector = v - other.verts_simple[i]  #continue convention of final - initial :: self - other
            connector.normalize()
            align = connector.dot(delta_com_vect)
            #this shouldnt happen but it appears to be...shrug
            if align < 0:
                align *= -1    
            ideal_to_com += align
        
        ideal_to_com = 1/len(self.verts_simple) * ideal_to_com
        
        return ideal_to_com
        
        
    def align_to_other(self,other, auto_align = True):
        
        '''
        Modifies vert order of self to  provide best
        bridge between self verts and other loop
        '''
        verts_1 = other.verts_simple
        
        eds_1 = other.eds_simple
        
        print('testing alignment')
        if 0 in eds_1[-1]:
            cyclic = True
            print('cyclic vert chain')
        else:
            cyclic = False
        
        if len(verts_1) != len(self.verts_simple):
            #print(len(verts_1))
            #print(len(self.verts_simple))
            print('non uniform loops, stopping until your developer gets smarter')
            return
            
        if cyclic:

            V1_0 = verts_1[1] - verts_1[0]
            V1_1 = verts_1[2] - verts_1[1]
            
            V2_0 = self.verts_simple[1] - self.verts_simple[0]
            V2_1 = self.verts_simple[2] - self.verts_simple[1]
            
            no_1 = V1_0.cross(V1_1)
            no_1.normalize()
            no_2 = V2_0.cross(V2_1)
            no_2.normalize()
            
            if no_1.dot(no_2) < 0:
                no_2 = -1 * no_2
            
            #average the two directions    
            ideal_direction = no_1.lerp(no_1,.5)
        
            curl_1 = contour_utilities.discrete_curl(verts_1, ideal_direction)
            curl_2 = contour_utilities.discrete_curl(self.verts_simple, ideal_direction)
            
            if curl_1 * curl_2 < 0:
                self.verts_simple.reverse()
                

            edge_len_dict = {}
            for i in range(0,len(verts_1)):
                for n in range(0,len(self.verts_simple)):
                    edge = (i,n)
                    vect = self.verts_simple[n] - verts_1[i]
                    edge_len_dict[edge] = vect.length
            
            shift_lengths = []
            #shift_cross = []
            for shift in range(0,len(self.verts_simple)):
                tmp_len = 0
                #tmp_cross = 0
                for i in range(0, len(self.verts_simple)):
                    shift_mod = int(math.fmod(i+shift, len(self.verts_simple)))
                    tmp_len += edge_len_dict[(i,shift_mod)]
                shift_lengths.append(tmp_len)
                   
            final_shift = shift_lengths.index(min(shift_lengths))
            if final_shift != 0:
                print('pre rough shift alignment % f' % self.connectivity_analysis(other))
                print("rough shifting verts by %i segments" % final_shift)
                self.int_shift = final_shift
                self.verts_simple = contour_utilities.list_shift(self.verts_simple, final_shift)
                print('post rough shift alignment % f' % self.connectivity_analysis(other))    
                
        
        else:
            #if the segement is not cyclic
            #all we have to do is compare the endpoints
            Vtotal_1 = verts_1[-1] - verts_1[0]
            Vtotal_2 = self.verts_simple[-1] - self.verts_simple[0]
    
            if Vtotal_1.dot(Vtotal_2) < 0:
                print('reversing path 2')
                self.verts_simple.reverse()
                      

class PolySkecthLine(object):
    
    def __init__(self, raw_points,
                 cull_factor = 5,
                 smooth_factor = 5,
                 feature_factor = 5,
                 color1 = (1,0,0,1),
                 color2 = (0,1,0,1),
                 color3 = (0,0,1,1),
                 color4 = (1,1,0,1)):
        
        ####DATA####
        self.raw_screen = [raw_points[0]]
        
        #toss a bunch of data
        for i, v in enumerate(raw_points):
            if not math.fmod(i, cull_factor):
                self.raw_screen.append(v)
        
        
        
        #culled raw_screen
        #raycast onto object
        self.raw_world = []
        
        #atenuated and smoothed
        self.world_path = []
        
        #this is free data from raycast
        self.path_normals = []
        
        #region 2d version of world path
        self.screen_path = []
        
        #detected features of screen path
        self.knots = []
        
        #locations of perpendicular
        #poly edges
        self.poly_nodes = []
        self.extrudes_u = []
        self.extrudes_d = []
        
        
        ####PROCESSIG CONSTANTS###
        self.cull_factor = cull_factor
        self.smooth_factor = smooth_factor
        self.feature_factor = feature_factor
        
        self.poly_loc = 'CENTERED' #ABOVE, #BELOW
        
        self.segments = 10
        
        ####VISULAIZTION STUFF####
        self.color1 = color1
        self.color2 = color2
        self.color3 = color3
        self.color4 = color4
        

    def active_element(self,context,x,y):
        settings = context.user_preferences.addons['contour_tools'].preferences
        mouse_loc = Vector((x,y))
        
        if len(self.knots):
            for i in self.knots:
                a = location_3d_to_region_2d(context.region, context.space_data.region_3d, self.poly_nodes[i])
                

        if len(self.poly_nodes):
            
            #Check by testing distance to all edges
            active_self = False
            self.color2 = (0,1,0,1)
            for i in range(0,len(self.poly_nodes) -1):
                
                a = location_3d_to_region_2d(context.region, context.space_data.region_3d, self.poly_nodes[i])
                b = location_3d_to_region_2d(context.region, context.space_data.region_3d, self.poly_nodes[i+1])
                intersect = intersect_point_line(mouse_loc, a, b)
        
                dist = (intersect[0] - mouse_loc).length_squared
                bound = intersect[1]
                if (dist < 100) and (bound < 1) and (bound > 0):
                    active_self = True
                    self.color2 = (1,1,0,1)
                    print('found edge %i' % i)
                    break
                
            return active_self
        
    def ray_cast_path(self,context, ob):
        region = context.region  
        rv3d = context.space_data.region_3d
        self.raw_world = []
        for v in self.raw_screen:
            vec = region_2d_to_vector_3d(region, rv3d, v)
            loc = region_2d_to_location_3d(region, rv3d, v, vec)

            a = loc + 3000*vec
            b = loc - 3000*vec

            mx = ob.matrix_world
            imx = mx.inverted()
            hit = ob.ray_cast(imx*a, imx*b)
            
            if hit[2] != -1:
                self.raw_world.append(mx * hit[0])
                
        
    def find_knots(self):
        print('find those knots')
        box_diag = contour_utilities.diagonal_verts(self.raw_world)
        error = 1/self.feature_factor * box_diag
        
        self.knots = contour_utilities.simplify_RDP(self.raw_world, error)
        
        
    def smooth_path(self, ob = None):
        print('              ')

        start_time = time.time()
        print(self.raw_world[1])
        #clear the world path if need be
        self.world_path = []
        
        if ob:
            mx = ob.matrix_world
            imx = mx.inverted()
            
        if len(self.knots) > 2:
            
            #split the raw
            segments = []
            for i in range(0,len(self.knots) - 1):
                segments.append([self.raw_world[m] for m in range(self.knots[i],self.knots[i+1])])
                
        else:
            segments = [[v.copy() for v in self.raw_world]]
        
        for segment in segments:
            for n in range(self.smooth_factor - 1):
                contour_utilities.relax(segment)
                
                #resnap so we don't loose the surface
                if ob:
                    print(segment)
                    for i, vert in enumerate(segment):
                        print(vert)
                        snap = ob.closest_point_on_mesh(imx * vert)
                        segment[i] = mx * snap[0]
                        
            
            self.world_path.extend(segment)
        
        
        end_time = time.time()
        print('smoothed and snapped %r in %f seconds' % (ob != None, end_time - start_time))            
        print('verify')
        print(self.raw_world[1])
        print('              ')
        
        
    
    def create_vert_nodes(self):
        self.poly_nodes = []
        curve_len = contour_utilities.get_path_length(self.world_path)
        desired_density = self.segments/curve_len
            
        if len(self.knots) > 2:
            
            
            segments = []
            for i in range(0,len(self.knots) - 1):
                segments.append(self.world_path[self.knots[i]:self.knots[i+1]+1])
                
            
            
        else:
            segments = [self.world_path]
            
        
        for i, segment in enumerate(segments):
            segment_length = contour_utilities.get_path_length(segment)
            n_segments = round(segment_length * desired_density)
            vs = contour_utilities.space_evenly_on_path(segment, [[0,1],[1,2]], n_segments, 0, debug = False)[0]
            if i > 0:
                self.poly_nodes.extend(vs[1:len(vs)])
            else:
                self.poly_nodes.extend(vs[:len(vs)])
        
        
            
    def generate_quads(self,ob,width):
        mx = ob.matrix_world
        imx = mx.inverted()
        
        self.normals = []
        self.extrudes_u = []
        self.extrudes_d = []
        
        for vert in self.poly_nodes:
            snap = ob.closest_point_on_mesh(imx * vert)
            #this wil be toughy
            self.normals.append(mx.to_3x3() * snap[1])
            
            
        for i, v in enumerate(self.poly_nodes):
            if i == 0:
                v = self.poly_nodes[i+1] - self.poly_nodes[i]
            
            elif i == len(self.poly_nodes) - 1:
                v = self.poly_nodes[i] - self.poly_nodes[i-1]
                
            else:
                v1 = self.poly_nodes[i] - self.poly_nodes[i-1]
                v2 = self.poly_nodes[i+1] - self.poly_nodes[i]
                v = v1.lerp(v2, .5)
                
            ext = self.normals[i].cross(v)
            ext.normalize()
            
            self.extrudes_u.append(self.poly_nodes[i] + .5 * width * ext)
            self.extrudes_d.append(self.poly_nodes[i] - .5 * width * ext)    
            
            
        print('make the quads')
        
        
        
    def draw(self,context):
        
        #if len(self.raw_world) > 2:
            #contour_utilities.draw_polyline_from_3dpoints(context, self.raw_world, self.color1, 1, 'GL_LINES')
            
        #draw the smothed path
        if len(self.world_path) > 2:
            
            contour_utilities.draw_polyline_from_3dpoints(context, self.world_path, self.color2, 1, 'GL_LINE_STIPPLE')
        
        #draw the knots
        if len(self.knots) > 2:
            points = [self.raw_world[i] for i in self.knots]
            contour_utilities.draw_3d_points(context, points, self.color3, 5)
            
        #draw the knots
        if len(self.poly_nodes) > 2 and len(self.extrudes_u) == 0:
            contour_utilities.draw_3d_points(context, self.poly_nodes, self.color4, 3)
            contour_utilities.draw_polyline_from_3dpoints(context, self.poly_nodes, (0,1,0,1), 1, 'GL_LINE_STIPPLE')
        
        if len(self.extrudes_u) > 2:
            contour_utilities.draw_3d_points(context, self.extrudes_u, self.color4, 2)
            contour_utilities.draw_3d_points(context, self.extrudes_d, self.color4, 2)
            contour_utilities.draw_polyline_from_3dpoints(context, self.extrudes_u, (0,1,0,1), 1, 'GL_LINE_STIPPLE')
            contour_utilities.draw_polyline_from_3dpoints(context, self.extrudes_d, (0,1,0,1), 1, 'GL_LINE_STIPPLE')
            
            for i, v in enumerate(self.extrudes_u):
                contour_utilities.draw_polyline_from_3dpoints(context, [self.extrudes_u[i],self.extrudes_d[i]], (0,1,0,1), 1, 'GL_LINE_STIPPLE')
            
        
            
class ContourCutLine(object): 
    
    def __init__(self, x, y, line_width = 3,
                 stroke_color = (0,0,1,1), 
                 handle_color = (1,0,0,1),
                 geom_color = (0,1,0,1),
                 vert_color = (0,.2,1,1)):
        
        self.desc = "CUT_LINE"
        self.select = True
        self.head = ContourControlPoint(self,x,y, color = handle_color)
        self.tail = ContourControlPoint(self,x,y, color = handle_color)
        #self.plane_tan = ContourControlPoint(self,x,y, color = (.8,.8,.8,1))
        #self.view_dir = view_dir
        self.target = None
 
        self.updated = False
        self.plane_pt = None  #this will be a point on an object surface...calced after ray_casting
        self.plane_com = None  #this will be a point in the object interior, calced after cutting a contour
        self.plane_no = None
        
        #these points will define two orthogonal vectors
        #which lie tangent to the plane...which we can use
        #to draw a little widget on the COM
        self.plane_x = None
        self.plane_y = None
        self.plane_z = None
        
        self.vec_x = None
        self.vec_y = None
        #self.vec_z is the plane normal
        
        self.seed_face_index = None
        
        #high res coss section
        #@ resolution of original mesh
        self.verts = []
        self.verts_screen = []
        self.edges = []
        #low res derived contour
        self.verts_simple = []
        self.eds_simple = []
        
        #screen cache for fast selection
        self.verts_simple_screen = []
        
        #variable used to shift loop beginning on high res loop
        self.shift = 0
        self.int_shift = 0
        
        #visual stuff
        self.line_width = line_width
        self.stroke_color = stroke_color
        self.geom_color = geom_color
        self.vert_color = vert_color
        
    def update_screen_coords(self,context):
        self.verts_screen = [location_3d_to_region_2d(context.region, context.space_data.region_3d, loc) for loc in self.verts]
        self.verts_simple_screen = [location_3d_to_region_2d(context.region, context.space_data.region_3d, loc) for loc in self.verts_simple]
        
          
    def draw(self,context, settings, three_dimensional = True, interacting = False):
        '''
        setings are the addon preferences for contour tools
        '''
        
        debug = settings.debug
        #settings = context.user_preferences.addons['contour_tools'].preferences
        
        #this should be moved to only happen if the view changes :-/  I'ts only
        #a few hundred calcs even with a lot of lines. Waste not want not.
        if self.head and self.head.world_position:
            self.head.screen_from_world(context)
        if self.tail and self.tail.world_position:
            self.tail.screen_from_world(context)
        #if self.plane_tan.world_position:
            #self.plane_tan.screen_from_world(context)
            
        if debug > 1:
            if self.plane_com:
                com_2d = location_3d_to_region_2d(context.region, context.space_data.region_3d, self.plane_com)
                
                contour_utilities.draw_3d_points(context, [self.plane_com], (0,1,0,1), 4)
                if self.vec_x:
                    pt_x = location_3d_to_region_2d(context.region, context.space_data.region_3d, self.plane_com + self.vec_x)
                    screen_vec_x = pt_x - com_2d
                    screen_pt_x = com_2d + 40 * screen_vec_x.normalized()
                    contour_utilities.draw_points(context, [pt_x], (1,1,0,1), 6)
                    
                if self.vec_y:
                    pt_y = location_3d_to_region_2d(context.region, context.space_data.region_3d, self.plane_com + self.vec_y)
                    screen_vec_y = pt_y - com_2d
                    screen_pt_y = com_2d + 40 * screen_vec_y.normalized()
                    contour_utilities.draw_points(context, [pt_y], (0,1,1,1), 6)

                if self.plane_no:
                    pt_z = location_3d_to_region_2d(context.region, context.space_data.region_3d, self.plane_com + self.plane_no)
                    screen_vec_z = pt_z - com_2d
                    screen_pt_z = com_2d + 40 * screen_vec_z.normalized()
                    contour_utilities.draw_points(context, [pt_z], (1,0,1,1), 6)
                    
        
        #draw connecting line
        if self.head:
            points = [(self.head.x,self.head.y),(self.tail.x,self.tail.y)]
            
            contour_utilities.draw_polyline_from_points(context, points, self.stroke_color, settings.stroke_thick, "GL_LINE_STIPPLE")
        
            #draw the two handles
            contour_utilities.draw_points(context, points, self.head.color, settings.handle_size)
        
        #draw the current plane point and the handle to change plane orientation
        #if self.plane_pt and settings.draw_widget:
            #point1 = location_3d_to_region_2d(context.region, context.space_data.region_3d, self.plane_pt)
            #point2 = (self.plane_tan.x, self.plane_tan.y)

            #contour_utilities.draw_polyline_from_points(context, [point1,point2], (0,.2,1,1), settings.stroke_thick, "GL_LINE_STIPPLE")
            #contour_utilities.draw_points(context, [point2], self.plane_tan.color, settings.handle_size)
            #contour_utilities.draw_points(context, [point1], self.head.color, settings.handle_size)
        
        #draw the raw contour vertices
        if (self.verts and self.verts_simple == []) or (debug > 0 and settings.show_verts):
            
            if three_dimensional:
                
                contour_utilities.draw_3d_points(context, self.verts, self.vert_color, settings.raw_vert_size)
            else:    
                contour_utilities.draw_points(context, self.verts_screen, self.vert_color, settings.raw_vert_size)
        
        #draw the simplified contour vertices and edges (rings)    
        if self.verts !=[] and self.eds != []:
            if three_dimensional:
                points = self.verts_simple.copy()
            else:
                points = self.verts_simple_screen.copy()
               
            if 0 in self.eds[-1]:
                points.append(points[0])
            #draw the ring
            #draw the points over it
            if settings.show_ring_edges:
                if three_dimensional:
                    contour_utilities.draw_polyline_from_3dpoints(context, points, self.geom_color, settings.line_thick,"GL_LINE_STIPPLE")
                    if not interacting:
                        contour_utilities.draw_3d_points(context, points, self.vert_color, settings.vert_size)
                else:
                    contour_utilities.draw_polyline_from_points(context, points, self.geom_color, settings.line_thick,"GL_LINE_STIPPLE")
                    if not interacting:
                        contour_utilities.draw_points(context,points, self.vert_color, settings.vert_size)
                
            if debug:
                if settings.vert_inds:
                    for i, point in enumerate(self.verts):
                        loc = location_3d_to_region_2d(context.region, context.space_data.region_3d, point)
                        blf.position(0, loc[0], loc[1], 0)
                        blf.draw(0, str(i))
                    
                if settings.simple_vert_inds:    
                    for i, point in enumerate(self.verts_simple):
                        loc = location_3d_to_region_2d(context.region, context.space_data.region_3d, point)
                        blf.position(0, loc[0], loc[1], 0)
                        blf.draw(0, str(i))
    #draw contour points? later    
    def hit_object(self, context, ob, method = 'VIEW'):
        settings = context.user_preferences.addons['contour_tools'].preferences
        region = context.region  
        rv3d = context.space_data.region_3d
        
        pers_mx = rv3d.perspective_matrix  #we need the perspective matrix
        
        #the world direction vectors associated with
        #the view rotations
        view_x = rv3d.view_rotation * Vector((1,0,0))
        view_y = rv3d.view_rotation * Vector((0,1,0))
        view_z = rv3d.view_rotation * Vector((0,0,1))
        
        
        #this only happens on the first time.
        #after which everything is handled by
        #the widget
        if method == 'VIEW':
            #midpoint of the  cutline and world direction of cutline
            screen_coord = (self.head.x + self.tail.x)/2, (self.head.y + self.tail.y)/2
            cut_vec = (self.tail.x - self.head.x)*view_x + (self.tail.y - self.head.y)*view_y
            cut_vec.normalize()
            self.plane_no = cut_vec.cross(view_z).normalized()
            
            #we need to populate the 3 axis vectors
            self.vec_x = -1 * cut_vec.normalized()
            self.vec_y = self.plane_no.cross(self.vec_x)
            

    
            vec = region_2d_to_vector_3d(region, rv3d, screen_coord)
            loc = region_2d_to_location_3d(region, rv3d, screen_coord, vec)
    
            #raycast what I think is the ray onto the object
            #raycast needs to be in ob coordinates.
            a = loc + 3000*vec
            b = loc - 3000*vec

            mx = ob.matrix_world
            imx = mx.inverted()
            hit = ob.ray_cast(imx*a, imx*b)    
    
            if hit[2] != -1:
                self.head.world_position = region_2d_to_location_3d(region, rv3d, (self.head.x, self.head.y), mx * hit[0])
                self.tail.world_position = region_2d_to_location_3d(region, rv3d, (self.tail.x, self.tail.y), mx * hit[0])
                
                self.plane_pt = mx * hit[0]
                self.seed_face_index = hit[2]

                if settings.use_perspective:
                    
                    cut_vec = self.head.world_position - self.tail.world_position
                    cut_vec.normalize()
                    self.plane_no = cut_vec.cross(vec).normalized()
                    self.vec_x = -1 * cut_vec.normalized()
                    self.vec_y = self.plane_no.cross(self.vec_x)
                    

                    
                self.plane_x = self.plane_pt + self.vec_x
                self.plane_y = self.plane_pt + self.vec_y
                self.plane_z = self.plane_pt + self.plane_no
                    
                                #we need to populate the 3 axis vectors
            
            

                #self.plane_tan.world_position = self.plane_pt + self.vec_y
                
                
                
            else:
                self.plane_pt = None
                self.seed_face_index = None
                self.verts = []
                self.verts_simple = []
            
            return self.plane_pt
        
        elif method in {'3_AXIS_COM','3_AXIS_POINT'}:
            mx = ob.matrix_world
            imx = mx.inverted()
            y = self.vec_y
            x = self.vec_x
                  
            if method == '3_AXIS_COM':
                
                if not self.plane_com:
                    print('failed no COM')
                    return
                pt = self.plane_com


                
            else:
                if not self.plane_pt:
                    print('failed no COM')
                    return
                pt = self.plane_pt
                
            hits = [ob.ray_cast(imx * pt, imx * (pt + 5 * y)),
                    ob.ray_cast(imx * pt, imx * (pt + 5 * x)),
                    ob.ray_cast(imx * pt, imx * (pt - 5 * y)),
                    ob.ray_cast(imx * pt, imx * (pt - 5 * x))]
            

            dists = []
            inds = []
            for i, hit in enumerate(hits):
                if hit[2] != -1:
                    R = pt - hit[0]
                    dists.append(R.length)
                    inds.append(i)
            
            #make sure we had some hits!
            if any(dists):
                #pick the best one as the closest one to the pt       
                best_hit = hits[inds[dists.index(min(dists))]]       
                self.plane_pt = mx * best_hit[0]
                self.seed_face_index = best_hit[2]
                
                
            else:
                self.plane_pt = None
                self.seed_face_index = None
                self.verts = []
                self.verts_simple = []
                print('aim better')
                
            return self.plane_pt
            
    def handles_to_screen(self,context):
        
        region = context.region  
        rv3d = context.space_data.region_3d
        
        
        self.head.world_position = region_2d_to_location_3d(region, rv3d, (self.head.x, self.head.y),self.plane_pt)
        self.tail.world_position = region_2d_to_location_3d(region, rv3d, (self.tail.x, self.tail.y),self.plane_pt)
        
          
    def cut_object(self,context, ob, bme):
        
        mx = ob.matrix_world
        pt = self.plane_pt
        pno = self.plane_no
        indx = self.seed_face_index
        if pt and pno:
            cross = contour_utilities.cross_section_seed(bme, mx, pt, pno, indx, debug = True)   
            if cross:
                self.verts = [mx*v for v in cross[0]]
                self.eds = cross[1]
                
        else:
            self.verts = []
            self.eds = []
        
    def simplify_cross(self,segments):
        if self.verts !=[] and self.eds != []:
            [self.verts_simple, self.eds_simple] = contour_utilities.space_evenly_on_path(self.verts, self.eds, segments, self.shift)
            
            if self.int_shift:
                self.verts_simple = contour_utilities.list_shift(self.verts_simple, self.int_shift)
            
    def update_com(self):
        if self.verts_simple != []:
            self.plane_com = contour_utilities.get_com(self.verts_simple)
        else:
            self.plane_com = None
    
    def adjust_cut_to_object_surface(self,ob):
        
        vecs = []
        rot = ob.matrix_world.to_quaternion()
        for v in self.verts_simple:
            closest = ob.closest_point_on_mesh(v)  #this will be in local coords!
            
            s_no = closest[1]
            
            vecs.append(self.plane_com + s_no)
        
        print(self.plane_no)    
        (com, no) = contour_utilities.calculate_best_plane(vecs)
        
        #TODO add some sanity checks
    
        #first sanity check...keep normal in same dir
        if self.plane_no.dot(rot * no) < 0:
            no *= -1
        
        self.plane_no = rot * no
        
        
        
        
    
    def generic_3_axis_from_normal(self):
        
        (self.vec_x, self.vec_y) = contour_utilities.generic_axes_from_plane_normal(self.plane_com, self.plane_no)
        
                       
    def derive_3_axis_control(self, method = 'FROM_VECS', n=0):
        '''
        args
        
        method: text enum in {'VIEW','FROM_VECS','FROM_VERT'}
        '''
        
        if len(self.verts_simple) and self.plane_com:

            
            #y vector
            y_vector = self.verts_simple[n] - self.plane_com
            y_vector.normalize()
            self.vec_y = y_vector
            
            #x vector
            x_vector = y_vector.cross(self.plane_no)
            x_vector.normalize()
            self.vec_x = x_vector
            
            
            #now the 4 points are in world space
            #we could use a vector...but transforming
            #to screen can be tricky with vectors as
            #opposed to locations.
            self.plane_x = self.plane_com + x_vector
            self.plane_y = self.plane_com + y_vector
            self.plane_z = self.plane_com + self.plane_no
            
            
            
        
    def analyze_relationship(self, other,debug = False):
        '''
        runs a series of quantitative assemsents of the spatial relationship
        to another cut line to assist in anticipating the the optimized
        connectivity data
        
        assume the other cutline has already been solidified and the only variation
        which can happen is on this line
        '''
        #requirements
        # both loops must have a verts simple
        
        
        #caclulate the center of mass of each loop using existing
        #verts simple since they are evenly spaced it will be a
        #good example
        COM_other = contour_utilities.get_com(other.verts_simple)
        COM_self = contour_utilities.get_com(self.verts_simple)
        
        #the vector pointing from the COM of the other cutline
        #to this cutline.  This will be our convention for
        #positive direciton
        delta_com_vect = COM_self - COM_other  
        #delta_com_vect.normalize()
        
        #the plane normals
        self_no = self.plane_no.copy()
        other_no = other.plane_no.copy()
        
        #if for some reason they aren't normalized...fix that
        self_no.normalize()
        other_no.normalize()
        
        #make sure the other normal is aligned with
        #the line from other to self for convention
        if other_no.dot(delta_com_vect) < 0:
            other_no = -1 * other_no
            
        #and now finally make the self normal is aligned too    
        if self_no.dot(other_no) < 0:
            self_no = -1 * self_no
        
        #how parallel are the loops?
        parallelism = self_no.dot(other_no)
        if debug > 1:
            print('loop paralellism = %f' % parallelism)
        
        #this may be important.
        avg_no = self_no.lerp(other_no, 0.5)
        
        #are the loops aimed at one another?
        #compare the delta COM vector to each normal
        self_aimed_other = self_no.dot(delta_com_vect.normalized())
        other_aimed_self = other_no.dot(delta_com_vect.normalized())
        
        aiming_difference = self_aimed_other - other_aimed_self
        if debug > 1:
            print('aiming difference = %f' % aiming_difference)
        #do we expect divergence or convergence?
        #remember other -> self is positive so enlarging
        #while traveling in this direction is divergence
        radi_self = contour_utilities.approx_radius(self.verts_simple, COM_self)
        radi_other = contour_utilities.approx_radius(other.verts_simple, COM_other)
        
        #if divergent or convergent....we will want to maximize
        #the opposite phenomenon with respect to the individual
        #connectors and teh delta COM line
        divergent = (radi_self - radi_other) > 0
        divergence = (radi_self - radi_other)**2 / ((radi_self - radi_other)**2 + delta_com_vect.length**2)
        divergence = math.pow(divergence, 0.5)
        if debug > 1:
            print('the loops are divergent: ' + str(divergent) + ' with a divergence of: ' + str(divergence))
        
        return [COM_self, delta_com_vect, divergent, divergence]
        
    def connectivity_analysis(self,other):
        
        
        COM_self = contour_utilities.get_com(self.verts_simple)
        COM_other = contour_utilities.get_com(other.verts_simple)
        delta_com_vect = COM_self - COM_other  #final - initial :: self - other
        delta_com_vect.normalize()
        

        
        ideal_to_com = 0
        for i, v in enumerate(self.verts_simple):
            connector = v - other.verts_simple[i]  #continue convention of final - initial :: self - other
            connector.normalize()
            align = connector.dot(delta_com_vect)
            #this shouldnt happen but it appears to be...shrug
            if align < 0:
                print('damn reverse!')
                print(align)
                align *= -1    
            ideal_to_com += align
        
        ideal_to_com = 1/len(self.verts_simple) * ideal_to_com
        
        return ideal_to_com
        
        
    def align_to_other(self,other, auto_align = True, direction_only = False):
        
        '''
        Modifies vert order of self to  provide best
        bridge between self verts and other loop
        '''
        verts_1 = other.verts_simple
        
        eds_1 = other.eds_simple
        
        print('testing alignment')
        if 0 in eds_1[-1]:
            cyclic = True
            print('cyclic vert chain')
        else:
            cyclic = False
        
        if len(verts_1) != len(self.verts_simple):
            #print(len(verts_1))
            #print(len(self.verts_simple))
            print('non uniform loops, stopping until your developer gets smarter')
            return
        
        
        #turns out, sum of diagonals is > than semi perimeter
        #lets exploit this (only true if quad is pretty much flat)
        #if we have paths reversed...our indices will give us diagonals
        #instead of perimeter
        #D1_O = verts_2[0] - verts_1[0]
        #D2_O = verts_2[-1] - verts_1[-1]
        #D1_R = verts_2[0] - verts_1[-1]
        #D2_R = verts_2[-1] - verts_1[0]
                
        #original_length = D1_O.length + D2_O.length
        #reverse_length = D1_R.length + D2_R.length
        #if reverse_length < original_length:
            #verts_2.reverse()
            #print('reversing')
            
        if cyclic:
            #another test to verify loop direction is to take
            #something reminiscint of the curl
            #since the loops in our case are guaranteed planar
            #(they come from cross sections) we can find a direction
            #from which to take the curl pretty easily.  Apologies to
            #any real mathemeticians reading this becuase I just
            #bastardized all these math terms.
            V1_0 = verts_1[1] - verts_1[0]
            V1_1 = verts_1[2] - verts_1[1]
            
            V2_0 = self.verts_simple[1] - self.verts_simple[0]
            V2_1 = self.verts_simple[2] - self.verts_simple[1]
            
            no_1 = V1_0.cross(V1_1)
            no_1.normalize()
            no_2 = V2_0.cross(V2_1)
            no_2.normalize()
            
            #we have no idea which way we will get
            #so just pick the directions which are
            #pointed in the general same direction
            if no_1.dot(no_2) < 0:
                no_2 = -1 * no_2
            
            #average the two directions    
            ideal_direction = no_1.lerp(no_1,.5)
        
            curl_1 = contour_utilities.discrete_curl(verts_1, ideal_direction)
            curl_2 = contour_utilities.discrete_curl(self.verts_simple, ideal_direction)
            
            if curl_1 * curl_2 < 0:
                print('reversing derived loop direction')
                print('curl1: %f and curl2: %f' % (curl_1,curl_2))
                self.verts_simple.reverse()
                print('reversing the base loop')
                self.verts.reverse()
                self.shift *= -1
                
        
        else:
            #if the segement is not cyclic
            #all we have to do is compare the endpoints
            Vtotal_1 = verts_1[-1] - verts_1[0]
            Vtotal_2 = self.verts_simple[-1] - self.verts_simple[0]
    
            if Vtotal_1.dot(Vtotal_2) < 0:
                print('reversing path 2')
                self.verts_simple.reverse()
                self.verts.reverse()
                
        
        
        if not direction_only:
            #iterate all verts and "handshake problem" them
            #into a dictionary?  That's not very efficient!
            if auto_align:
                self.shift = 0
                self.int_shift = 0
                self.simplify_cross(len(self.eds_simple))
            edge_len_dict = {}
            for i in range(0,len(verts_1)):
                for n in range(0,len(self.verts_simple)):
                    edge = (i,n)
                    vect = self.verts_simple[n] - verts_1[i]
                    edge_len_dict[edge] = vect.length
            
            shift_lengths = []
            #shift_cross = []
            for shift in range(0,len(self.verts_simple)):
                tmp_len = 0
                #tmp_cross = 0
                for i in range(0, len(self.verts_simple)):
                    shift_mod = int(math.fmod(i+shift, len(self.verts_simple)))
                    tmp_len += edge_len_dict[(i,shift_mod)]
                shift_lengths.append(tmp_len)
                   
            final_shift = shift_lengths.index(min(shift_lengths))
            if final_shift != 0:
                print('pre rough shift alignment % f' % self.connectivity_analysis(other))
                print("rough shifting verts by %i segments" % final_shift)
                self.int_shift = final_shift
                self.verts_simple = contour_utilities.list_shift(self.verts_simple, final_shift)
                print('post rough shift alignment % f' % self.connectivity_analysis(other))
            
            if auto_align and cyclic:
                alignment_quality = self.connectivity_analysis(other)
                #pct_change = 1
                left_bound = -1
                right_bound = 1
                iterations = 0
                while iterations < 20:
                    
                    iterations += 1
                    width = right_bound - left_bound
                    
                    self.shift = 0.5 * (left_bound + right_bound)
                    self.simplify_cross(len(self.eds_simple)) #TODO not sure this needs to happen here
                    #self.verts_simple = contour_utilities.list_shift(self.verts_simple, final_shift)
                    alignment_quality = self.connectivity_analysis(other)
                    
                    self.shift = left_bound
                    self.simplify_cross(len(self.eds_simple))
                    #self.verts_simple = contour_utilities.list_shift(self.verts_simple, final_shift)
                    alignment_quality_left = self.connectivity_analysis(other)
                    
                    self.shift = right_bound
                    self.simplify_cross(len(self.eds_simple))
                    #self.verts_simple = contour_utilities.list_shift(self.verts_simple, final_shift)
                    alignment_quality_right = self.connectivity_analysis(other)
                    
                    if alignment_quality_left < alignment_quality and alignment_quality_right < alignment_quality:
                        
                        left_bound += width*1/8
                        right_bound -= width*1/8
                        
                        
                    elif alignment_quality_left > alignment_quality and alignment_quality_right > alignment_quality:
                        
                        if alignment_quality_right > alignment_quality_left:
                            left_bound = right_bound - 0.75 * width
                        else:
                            right_bound = left_bound + 0.75* width
                        
                    elif alignment_quality_left < alignment_quality and alignment_quality_right > alignment_quality:
                        #print('move to the right')
                        #right becomes the new middle
                        left_bound += width * 1/4
                
                    elif alignment_quality_left > alignment_quality and alignment_quality_right < alignment_quality:
                        #print('move to the left')
                        #right becomes the new middle
                        right_bound -= width * 1/4
                        
                        
                    #print('pct change iteration %i was %f' % (iterations, pct_change))
                    #print(alignment_quality)
                    #print(alignment_quality_left)
                    #print(alignment_quality_right)
                print('converged or didnt in %i iterations' % iterations)
                print('final alignment quality is %f' % alignment_quality)
              
    def active_element(self,context,x,y):
        settings = context.user_preferences.addons['contour_tools'].preferences
        
        if self.head: #this makes sure the head and tail haven't been removed
            active_head = self.head.mouse_over(x, y)
            active_tail = self.tail.mouse_over(x, y)
        else:
            active_head = False
            active_tail = False
        #active_tan = self.plane_tan.mouse_over(x, y)
        
        

        if len(self.verts_simple):
            mouse_loc = Vector((x,y))
            #Check by testing distance to all edges
            active_self = False
            for ed in self.eds_simple:
                
                a = self.verts_simple_screen[ed[0]]
                b = self.verts_simple_screen[ed[1]]
                intersect = intersect_point_line(mouse_loc, a, b)
        
                dist = (intersect[0] - mouse_loc).length_squared
                bound = intersect[1]
                if (dist < 100) and (bound < 1) and (bound > 0):
                    active_self = True
                    break
            
        else:
            active_self = False
            '''
            region = context.region  
            rv3d = context.space_data.region_3d
            vec = region_2d_to_vector_3d(region, rv3d, (x,y))
            loc = region_2d_to_location_3d(region, rv3d, (x,y), vec)
            
            line_a = loc
            line_b = loc + vec
            #ray to plane
            hit = intersect_line_plane(line_a, line_b, self.plane_pt, self.plane_no)
            if hit:
                mouse_in_loop = contour_utilities.point_inside_loop_almost3D(hit, self.verts_simple, self.plane_no, p_pt = self.plane_pt, threshold = .01, debug = False)
                if mouse_in_loop:
                    self.geom_color = (.8,0,.8,0.5)
                    self.line_width = 2.5 * settings.line_thick
                else:
                    self.geom_color = (0,1,0,0.5)
                    self.line_width = settings.line_thick
                
            
        mouse_loc = Vector((x,y,0))
        head_loc = Vector((self.head.x, self.head.y, 0))
        tail_loc = Vector((self.tail.x, self.tail.y, 0))
        intersect = intersect_point_line(mouse_loc, head_loc, tail_loc)
        
        dist = (intersect[0] - mouse_loc).length_squared
        bound = intersect[1]
        active_self = (dist < 100) and (bound < 1) and (bound > 0) #TODO:  make this a sensitivity setting
        '''
        #they are all clustered together
        if active_head and active_tail and active_self: 
            
            return self.head
        
        elif active_tail:
            #print('returning tail')
            return self.tail
        
        elif active_head:
            #print('returning head')
            return self.head
        
        #elif active_tan:
            #return self.plane_tan
        
        elif active_self:
            #print('returning line')
            return self
        
        else:
            #print('returning None')
            return None



class CutLineManipulatorWidget(object):
    def __init__(self,context, settings, cut_line,x,y,cut_line_a = None, cut_line_b = None, hotkey = False):
        
        self.desc = 'WIDGET'
        self.cut_line = cut_line
        self.x = x
        self.y = y
        self.hotkey = hotkey
        self.initial_x = None
        self.initial_y = None
        
        #this will get set later by interaction
        self.transform = False
        self.transform_mode = None
        
        if cut_line_a:
            self.a = cut_line_a.plane_com
            self.a_no = cut_line_a.plane_no
        else:
            self.a = None
            self.a_no = None
        
        if cut_line_b:
            self.b = cut_line_b.plane_com
            self.b_no = cut_line_b.plane_no
        else:
            self.b = None
            self.b_no = None
            
        self.color = (settings.widget_color[0], settings.widget_color[1],settings.widget_color[2],1)
        self.color2 = (settings.widget_color2[0], settings.widget_color2[1],settings.widget_color2[2],1)
        self.color3 = (settings.widget_color3[0], settings.widget_color3[1],settings.widget_color3[2],1)
        self.color4 = (settings.widget_color4[0], settings.widget_color4[1],settings.widget_color4[2],1)
        self.color5 = (settings.widget_color5[0], settings.widget_color5[1],settings.widget_color5[2],1)
        
        self.radius = settings.widget_radius
        self.inner_radius = settings.widget_radius_inner
        self.line_width = settings.widget_thickness
        self.line_width2 = settings.widget_thickness2
        self.arrow_size = settings.arrow_size
        
        self.arrow_size2 = settings.arrow_size2
        
        self.arc_radius = .5 * (self.radius + self.inner_radius)
        self.screen_no = None

        self.angle = 0
        
        #intitial conditions for "undo"
        if self.cut_line.plane_com:
            self.initial_com = self.cut_line.plane_com.copy()
        else:
            self.initial_com = None
            
        if self.cut_line.plane_pt:
            self.initial_plane_pt = self.cut_line.plane_pt.copy()
        else:
            self.initial_plane_pt = None
        
        self.vec_x = self.cut_line.vec_x.copy()
        self.vec_y = self.cut_line.vec_y.copy()
        self.initial_plane_no = self.cut_line.plane_no.copy()
        self.initial_seed = self.cut_line.seed_face_index
        self.initial_int_shift = self.cut_line.int_shift
        self.initial_shift = self.cut_line.shift
        
        self.wedge_1 = []
        self.wedge_2 = []
        self.wedge_3 = []
        self.wedge_4 = []
        
        self.arrow_1 = []
        self.arrow_2 = []
        
        self.arc_arrow_1 = []
        self.arc_arrow_2 = []
        

        
    def user_interaction(self, context, mouse_x,mouse_y):
        '''
        analyse mouse coords x,y
        return [type, transform]
        '''
        
        mouse_vec = Vector((mouse_x,mouse_y))
        
        
        #In hotkey mode G, this will be spawned at the mouse
        #essentially being the initial mouse
        widget_screen = Vector((self.x,self.y))
        mouse_wrt_widget = mouse_vec - widget_screen
        com_screen = location_3d_to_region_2d(context.region, context.space_data.region_3d,self.initial_com)
        
        
        region = context.region
        rv3d = context.space_data.region_3d
        world_mouse = region_2d_to_location_3d(region, rv3d, (mouse_x, mouse_y), self.initial_com)
        world_widget = region_2d_to_location_3d(region, rv3d, (self.x, self.y), self.initial_com)
        
        if not self.transform and not self.hotkey:
            #this represents a switch...since by definition we were not transforming to begin with
            if mouse_wrt_widget.length > self.inner_radius:
                self.transform = True
                
                #identify which quadrant we are in
                screen_angle = math.atan2(mouse_wrt_widget[1], mouse_wrt_widget[0])
                loc_angle = screen_angle - self.angle
                loc_angle = math.fmod(loc_angle + 4 * math.pi, 2 * math.pi)  #correct for any negatives
                
                if loc_angle >= 1/4 * math.pi and loc_angle < 3/4 * math.pi:
                    #we are in the  left quadrant...which is perpendicular
                    self.transform_mode = 'EDGE_SLIDE'
                    
                elif loc_angle >= 3/4 * math.pi and loc_angle < 5/4 * math.pi:
                    self.transform_mode = 'ROTATE_VIEW'
                
                elif loc_angle >= 5/4 * math.pi and loc_angle < 7/4 * math.pi:
                    self.transform_mode = 'EDGE_SLIDE'
                
                else:
                    self.transform_mode = 'ROTATE_VIEW_PERPENDICULAR'
                    

                #print(loc_angle)
                print(self.transform_mode)
                
            return {'DO_NOTHING'}  #this tells it whether to recalc things
            
        else:
            #we were transforming but went back in the circle
            if mouse_wrt_widget.length < self.inner_radius and not self.hotkey:
                
                self.cancel_transform()
                self.transform = False
                self.transform_mode = None
                
                
                
                return {'RECUT'}
                
            
            else:
                
                if self.transform_mode == 'EDGE_SLIDE':
                    
                    world_vec = world_mouse - world_widget
                    screen_dist = mouse_wrt_widget.length - self.inner_radius
                    
                    print(screen_dist)
                    
                    if self.hotkey:
                        factor =  1
                    else:
                        factor = screen_dist/mouse_wrt_widget.length
                    
                    
                    if self.a:
                        a_screen = location_3d_to_region_2d(context.region, context.space_data.region_3d,self.a)
                        vec_a_screen = a_screen - com_screen
                        vec_a_screen_norm = vec_a_screen.normalized()
                        
                        vec_a = self.a - self.initial_com
                        vec_a_dir = vec_a.normalized()
                        
                        
                        if mouse_wrt_widget.dot(vec_a_screen_norm) > 0 and factor * mouse_wrt_widget.dot(vec_a_screen_norm) < vec_a_screen.length:
                            translate = factor * mouse_wrt_widget.dot(vec_a_screen_norm)/vec_a_screen.length * vec_a
                            
                            if self.a_no.dot(self.initial_plane_no) < 0:
                                v = -1 * self.a_no
                            else:
                                v = self.a_no
                            
                            scale = factor * mouse_wrt_widget.dot(vec_a_screen_norm)/vec_a_screen.length
                            quat = contour_utilities.rot_between_vecs(self.initial_plane_no, v, factor = scale)
                            inter_no = quat * self.initial_plane_no
                            
                            self.cut_line.plane_com = self.initial_com + translate
                            self.cut_line.plane_no = inter_no
                            
                            self.cut_line.vec_x = quat * self.vec_x.copy()
                            self.cut_line.vec_y = quat * self.vec_y.copy()
                            
                            return {'REHIT','RECUT'}
                        
                        elif not self.b and world_vec.dot(vec_a_dir) < 0:
                            translate = factor * world_vec.dot(self.initial_plane_no) * self.initial_plane_no
                            self.cut_line.plane_com = self.initial_com + translate
                            return {'REHIT','RECUT'}
                        
                        
                    if self.b:
                        b_screen = location_3d_to_region_2d(context.region, context.space_data.region_3d,self.b)
                        vec_b_screen = b_screen - com_screen
                        vec_b_screen_norm = vec_b_screen.normalized()
                        
                        vec_b = self.b - self.initial_com
                        vec_b_dir = vec_b.normalized()
                        
                        
                        if mouse_wrt_widget.dot(vec_b_screen_norm) > 0 and factor * mouse_wrt_widget.dot(vec_b_screen_norm) < vec_b_screen.length:
                            translate = factor * mouse_wrt_widget.dot(vec_b_screen_norm)/vec_b_screen.length * vec_b
                            
                            if self.b_no.dot(self.initial_plane_no) < 0:
                                v = -1 * self.b_no
                            else:
                                v = self.b_no
                            
                            scale = factor * mouse_wrt_widget.dot(vec_b_screen_norm)/vec_b_screen.length
                            quat = contour_utilities.rot_between_vecs(self.initial_plane_no, v, factor = scale)
                            inter_no = quat * self.initial_plane_no
                            
                            self.cut_line.plane_com = self.initial_com + translate
                            self.cut_line.plane_no = inter_no
                            self.cut_line.vec_x = quat * self.vec_x.copy()
                            self.cut_line.vec_y = quat * self.vec_y.copy()
                            return {'REHIT','RECUT'}
                            
                        
                        elif not self.a and world_vec.dot(vec_b_dir) < 0:
                            translate = factor * world_vec.dot(self.initial_plane_no) * self.initial_plane_no
                            self.cut_line.plane_com = self.initial_com + translate
                            
                    if not self.a and not self.b:
                        translate = factor * world_vec.dot(self.initial_plane_no) * self.initial_plane_no
                        self.cut_line.plane_com = self.initial_com + translate
                        return {'REHIT','RECUT'}
                    
                    return {'DO_NOTHING'}

                    
                if self.transform_mode == 'NORMAL_TRANSLATE':
                    print('translating')
                    #the pixel distance used to scale the translation
                    screen_dist = mouse_wrt_widget.length - self.inner_radius
                    
                    world_vec = world_mouse - world_widget
                    translate = screen_dist/mouse_wrt_widget.length * world_vec.dot(self.initial_plane_no) * self.initial_plane_no
                    
                    self.cut_line.plane_com = self.initial_com + translate
                    
                    return {'REHIT','RECUT'}
                
                elif self.transform_mode in {'ROTATE_VIEW_PERPENDICULAR', 'ROTATE_VIEW'}:
                    
                    #establish the transform axes
                    '''
                    screen_com = location_3d_to_region_2d(context.region, context.space_data.region_3d,self.cut_line.plane_com)
                    vertical_screen_vec = Vector((math.cos(self.angle + .5 * math.pi), math.sin(self.angle + .5 * math.pi)))
                    screen_y = screen_com + vertical_screen_vec
                    world_pre_y = region_2d_to_location_3d(region, rv3d, (screen_y[0], screen_y[1]),self.cut_line.plane_com)
                    world_y = world_pre_y - self.cut_line.plane_com
                    world_y_correct = world_y.dot(self.initial_plane_no)
                    world_y = world_y - world_y_correct * self.initial_plane_no
                    world_y.normalize()
                    
                    world_x = self.initial_plane_no.cross(world_y)
                    world_x.normalize()
                    '''
                    
                    axis_1  = rv3d.view_rotation * Vector((0,0,1))
                    axis_1.normalize()
                    
                    axis_2 = self.initial_plane_no.cross(axis_1)
                    axis_2.normalize()
                    
                    #self.cut_line.vec_x = world_x
                    #self.cut_line.vec_y = world_y
                    
                    #self.cut_line.plane_x = self.cut_line.plane_com + 2 * world_x
                    #self.cut_line.plane_y = self.cut_line.plane_com + 2 * world_y
                    #self.cut_line.plane_z = self.cut_line.plane_com + 2 * self.initial_plane_no
                    
                    #identify which quadrant we are in
                    screen_angle = math.atan2(mouse_wrt_widget[1], mouse_wrt_widget[0])
                    
                    if self.transform_mode == 'ROTATE_VIEW':
                        if not self.hotkey:
                            rot_angle = screen_angle - self.angle #+ .5 * math.pi  #Mystery
                            
                        else:
                            init_angle = math.atan2(self.initial_y - self.y, self.initial_x - self.x)
                            init_angle = math.fmod(init_angle + 4 * math.pi, 2 * math.pi)
                            rot_angle = screen_angle - init_angle
                            
                        rot_angle = math.fmod(rot_angle + 4 * math.pi, 2 * math.pi)  #correct for any negatives
                        print('rotating by %f' % rot_angle)
                        sin = math.sin(rot_angle/2)
                        cos = math.cos(rot_angle/2)
                        #quat = Quaternion((cos, sin*world_x[0], sin*world_x[1], sin*world_x[2]))
                        quat = Quaternion((cos, sin*axis_1[0], sin*axis_1[1], sin*axis_1[2]))


                    
                    else:
                        rot_angle = screen_angle - self.angle + math.pi #+ .5 * math.pi  #Mystery
                        rot_angle = math.fmod(rot_angle + 4 * math.pi, 2 * math.pi)  #correct for any negatives
                        print('rotating by %f' % rot_angle)
                        sin = math.sin(rot_angle/2)
                        cos = math.cos(rot_angle/2)
                        #quat = Quaternion((cos, sin*world_y[0], sin*world_y[1], sin*world_y[2]))
                        quat = Quaternion((cos, sin*axis_2[0], sin*axis_2[1], sin*axis_2[2])) 
                        
                        #new_no = self.initial_plane_no.copy() #its not rotated yet
                        #new_no.rotate(quat)
    
                        #rotate around x axis...update y
                        #world_x = world_y.cross(new_no)
                        #new_com = self.initial_com
                        #new_tan = new_com + world_x
                        
                        
                        #self.cut_line.plane_x = self.cut_line.plane_com + 2 * world_x
                        #self.cut_line.plane_y = self.cut_line.plane_com + 2 * world_y
                        #self.cut_line.plane_z = self.cut_line.plane_com + 2 * new_no
                    
               
                    new_no = self.initial_plane_no.copy() #its not rotated yet
                    new_no.rotate(quat)

                    new_x = self.vec_x.copy() #its not rotated yet
                    new_x.rotate(quat)
                   
                    new_y = self.vec_y.copy()
                    new_y.rotate(quat)
                    
                    self.cut_line.vec_x = new_x
                    self.cut_line.vec_y = new_y
                    self.cut_line.plane_no = new_no    
                    return {'RECUT'}
        
        #
        #Tranfsorm mode = NORMAL_TANSLATE
            #get the distance from mouse to self.x,y - inner radius
            
            #get the world distance by projecting both the original x,y- inner radius
            #and the mouse_x,mouse_y to the depth of the COPM
            
            #if "precision divide by 1/10?
            
            #add the translation vector to the
        
        #Transform mode = ROTATE_VIEW
        
        #Transfrom mode = EDGE_PEREPENDICULAR
        

    def derive_screen(self,context):
        rv3d = context.space_data.region_3d
        view_z = rv3d.view_rotation * Vector((0,0,1))
        if view_z.dot(self.initial_plane_no) > -.95 and view_z.dot(self.initial_plane_no) < .95:
            #point_0 = location_3d_to_region_2d(context.region, context.space_data.region_3d,self.cut_line.plane_com)
            #point_1 = location_3d_to_region_2d(context.region, context.space_data.region_3d,self.cut_line.plane_com + self.initial_plane_no.normalized())
            #self.screen_no = point_1 - point_0
            #if self.screen_no.dot(Vector((0,1))) < 0:
                #self.screen_no = point_0 - point_1
            #self.screen_no.normalize()
            
            imx = rv3d.view_matrix.inverted()
            normal_3d = imx.transposed() * self.cut_line.plane_no
            self.screen_no = Vector((normal_3d[0],normal_3d[1]))
            
            self.angle = math.atan2(self.screen_no[1],self.screen_no[0]) - 1/2 * math.pi
        else:
            self.screen_no = None
        
        
        up = self.angle + 1/2 * math.pi
        down = self.angle + 3/2 * math.pi
        left = self.angle + math.pi
        right =  self.angle
        
        deg_45 = .25 * math.pi
        
        self.wedge_1 = contour_utilities.pi_slice(self.x,self.y,self.inner_radius,self.radius,up - deg_45,up + deg_45, 10 ,t_fan = False)
        self.wedge_2 = contour_utilities.pi_slice(self.x,self.y,self.inner_radius,self.radius,left - deg_45,left + deg_45, 10 ,t_fan = False)
        self.wedge_3 = contour_utilities.pi_slice(self.x,self.y,self.inner_radius,self.radius,down - deg_45,down + deg_45, 10 ,t_fan = False)
        self.wedge_4 = contour_utilities.pi_slice(self.x,self.y,self.inner_radius,self.radius,right - deg_45,right + deg_45, 10 ,t_fan = False)
        self.wedge_1.append(self.wedge_1[0])
        self.wedge_2.append(self.wedge_2[0])
        self.wedge_3.append(self.wedge_3[0])
        self.wedge_4.append(self.wedge_4[0])
        
        
        self.arc_arrow_1 = contour_utilities.arc_arrow(self.x, self.y, self.arc_radius, left - deg_45+.2, left + deg_45-.2, 10, self.arrow_size, 2*deg_45, ccw = True)
        self.arc_arrow_2 = contour_utilities.arc_arrow(self.x, self.y, self.arc_radius, right - deg_45+.2, right + deg_45-.2, 10, self.arrow_size,2*deg_45, ccw = True)
  
        self.inner_circle = contour_utilities.simple_circle(self.x, self.y, self.inner_radius, 20)
        
        #New screen coords, leaving old ones until completely transitioned
        self.arc_arrow_rotate_ccw = contour_utilities.arc_arrow(self.x, self.y, self.radius, left - deg_45-.3, left + deg_45+.3, 10, self.arrow_size, 2*deg_45, ccw = True)
        self.arc_arrow_rotate_cw = contour_utilities.arc_arrow(self.x, self.y, self.radius, left - deg_45-.3, left + deg_45+.3, 10, self.arrow_size, 2*deg_45, ccw = False)
        
        self.inner_circle = contour_utilities.simple_circle(self.x, self.y, self.inner_radius, 20)
        self.inner_circle.append(self.inner_circle[0])
        
        self.outer_circle_1 = contour_utilities.arc_arrow(self.x, self.y, self.radius, up, down,10, self.arrow_size,2*deg_45, ccw = True)
        self.outer_circle_2 = contour_utilities.arc_arrow(self.x, self.y, self.radius, down, up,10, self.arrow_size,2*deg_45, ccw = True)
        
        b = self.arrow_size2
        self.trans_arrow_up = contour_utilities.arrow_primitive(self.x +math.cos(up) * self.radius, self.y + math.sin(up)*self.radius, right, b, b, b, b/2)
        self.trans_arrow_down = contour_utilities.arrow_primitive(self.x + math.cos(down) * self.radius, self.y + math.sin(down) * self.radius, left, b, b, b, b/2)
    
    def cancel_transform(self):
        
        self.cut_line = ContourCutLine
        #reset our initial values
        self.cut_line.plane_com = self.initial_com
        self.cut_line.plane_no = self.initial_plane_no
        self.cut_line.plane_pt = self.initial_plane_pt
        self.cut_line.vec_x = self.vec_x
        self.cut_line.vec_y = self.vec_y
        self.cut_line.seed_face_index = self.initial_seed
        
        self.cut_line.int_shift = self.initial_int_shift
        self.cut_line.shift = self.initial_shift
                
                  
    def draw(self, context):
        
        settings = context.user_preferences.addons['contour_tools'].preferences
        
        if self.a:
            contour_utilities.draw_3d_points(context, [self.a], self.color3, 5)
        if self.b:
            contour_utilities.draw_3d_points(context, [self.b], self.color3, 5)
            
            
        if not self.transform and not self.hotkey:
            #draw wedges
            #contour_utilities.draw_polyline_from_points(context, self.wedge_1, self.color, self.line_width, "GL_LINES")
            #contour_utilities.draw_polyline_from_points(context, self.wedge_2, self.color, self.line_width, "GL_LINES")
            #contour_utilities.draw_polyline_from_points(context, self.wedge_3, self.color, self.line_width, "GL_LINES")
            #contour_utilities.draw_polyline_from_points(context, self.wedge_4, self.color, self.line_width, "GL_LINES")
            
            #draw inner circle
            #contour_utilities.draw_polyline_from_points(context, self.inner_circle, (self.color[0],self.color[1],self.color[2],.5), self.line_width, "GL_LINES")
            
            #draw outer circle (two halfs later)
            #contour_utilities.draw_polyline_from_points(context, self.outer_circle_1[0:l-1], (0,.5,.8,1), self.line_width, "GL_LINES")

                
            #draw arc 1
            l = len(self.arc_arrow_1)
            #contour_utilities.draw_polyline_from_points(context, self.arc_arrow_1[:l-1], self.color2, self.line_width, "GL_LINES")

            #draw outer circle half
            contour_utilities.draw_polyline_from_points(context, self.outer_circle_1[0:l-2], self.color4, self.line_width, "GL_LINES")
            contour_utilities.draw_polyline_from_points(context, self.outer_circle_2[0:l-2], self.color4, self.line_width, "GL_LINES")
            
            #draw outer translation arrows
            #contour_utilities.draw_polyline_from_points(context, self.trans_arrow_up, self.color3, self.line_width, "GL_LINES")
            #contour_utilities.draw_polyline_from_points(context, self.trans_arrow_down, self.color3, self.line_width, "GL_LINES")            
            
            
            contour_utilities.draw_outline_or_region("GL_POLYGON", self.trans_arrow_down[:4], self.color3)
            contour_utilities.draw_outline_or_region("GL_POLYGON", self.trans_arrow_up[:4], self.color3)
            contour_utilities.draw_outline_or_region("GL_POLYGON", self.trans_arrow_down[4:], self.color3)
            contour_utilities.draw_outline_or_region("GL_POLYGON", self.trans_arrow_up[4:], self.color3)
            
            #draw a line perpendicular to arc
            #point_1 = Vector((self.x,self.y)) + 2/3 * (self.inner_radius + self.radius) * Vector((math.cos(self.angle), math.sin(self.angle)))
            #point_2 = Vector((self.x,self.y)) + 1/3 * (self.inner_radius + self.radius) * Vector((math.cos(self.angle), math.sin(self.angle)))
            #contour_utilities.draw_polyline_from_points(context, [point_1, point_2], self.color3, self.line_width, "GL_LINES")
            
            
            #try the straight red line
            point_1 = Vector((self.x,self.y)) #+ self.inner_radius * Vector((math.cos(self.angle), math.sin(self.angle)))
            point_2 = Vector((self.x,self.y)) +  self.radius * Vector((math.cos(self.angle), math.sin(self.angle)))
            contour_utilities.draw_polyline_from_points(context, [point_1, point_2], self.color2, self.line_width2 , "GL_LINES")
            
            point_1 = Vector((self.x,self.y))# + -self.inner_radius * Vector((math.cos(self.angle), math.sin(self.angle)))
            point_2 = Vector((self.x,self.y)) +  -self.radius * Vector((math.cos(self.angle), math.sin(self.angle)))
            contour_utilities.draw_polyline_from_points(context, [point_1, point_2], self.color2, self.line_width, "GL_LINES")
            
            #drawa arc 2
            #contour_utilities.draw_polyline_from_points(context, self.arc_arrow_2[:l-1], self.color2, self.line_width, "GL_LINES")
            
            #new rotation thingy
            contour_utilities.draw_polyline_from_points(context, self.arc_arrow_rotate_ccw[:l-1], self.color, self.line_width2, "GL_LINES")
            contour_utilities.draw_polyline_from_points(context, self.arc_arrow_rotate_cw[:l-1], self.color, self.line_width2, "GL_LINES")
            
            #other half the tips
            contour_utilities.draw_polyline_from_points(context, [self.arc_arrow_rotate_ccw[l-1],self.arc_arrow_rotate_ccw[l-3]], (0,0,1,1), self.line_width2, "GL_LINES")
            contour_utilities.draw_polyline_from_points(context, [self.arc_arrow_rotate_cw[l-1],self.arc_arrow_rotate_cw[l-3]], (0,0,1,1), self.line_width2, "GL_LINES")
            
            #draw an up and down arrow
            #point_1 = Vector((self.x,self.y)) + 2/3 * (self.inner_radius + self.radius) * Vector((math.cos(self.angle + .5*math.pi), math.sin(self.angle + .5*math.pi)))
            #point_2 = Vector((self.x,self.y)) + 1/3 * (self.inner_radius + self.radius) * Vector((math.cos(self.angle + .5*math.pi), math.sin(self.angle + .5*math.pi)))
            #contour_utilities.draw_polyline_from_points(context, [point_1, point_2], self.color, self.line_width, "GL_LINES")
            
            #draw little hash
            #point_1 = Vector((self.x,self.y)) + 2/3 * (self.inner_radius + self.radius) * Vector((math.cos(self.angle +  3/2 * math.pi), math.sin(self.angle +  3/2 * math.pi)))
            #point_2 = Vector((self.x,self.y)) + 1/3 * (self.inner_radius + self.radius) * Vector((math.cos(self.angle +  3/2 * math.pi), math.sin(self.angle +  3/2 * math.pi)))
            #contour_utilities.draw_polyline_from_points(context, [point_1, point_2], self.color, self.line_width, "GL_LINES")
        
        elif self.transform_mode:

            #draw a small inner circle
            contour_utilities.draw_polyline_from_points(context, self.inner_circle, self.color, self.line_width, "GL_LINES")
            
            
            if not settings.live_update:
                if self.transform_mode in {"NORMAL_TRANSLATE", "EDGE_SLIDE"}:
                    #draw a line representing the COM translation
                    points = [self.initial_com, self.cut_line.plane_com]
                    contour_utilities.draw_3d_points(context, points, self.color3, 4)
                    contour_utilities.draw_polyline_from_3dpoints(context, points, self.color ,2 , "GL_STIPPLE")
                    
                else:
                    rv3d = context.space_data.region_3d

                    p1 = self.cut_line.plane_com
                    p1_2d =  location_3d_to_region_2d(context.region, context.space_data.region_3d, p1)
                    #p2_2d =  location_3d_to_region_2d(context.region, context.space_data.region_3d, p2)
                    #p3_2d =  location_3d_to_region_2d(context.region, context.space_data.region_3d, p3)
                    
                    
                    imx = rv3d.view_matrix.inverted()
                    vec_screen = imx.transposed() * self.cut_line.plane_no
                    vec_2d = Vector((vec_screen[0],vec_screen[1]))

                    p4_2d = p1_2d + self.radius * vec_2d
                    p6_2d = p1_2d - self.radius * vec_2d
                    
                    print('previewing the rotation')
                    contour_utilities.draw_points(context, [p1_2d, p4_2d, p6_2d], self.color3, 5)
                    contour_utilities.draw_polyline_from_points(context, [p6_2d, p4_2d], self.color ,2 , "GL_STIPPLE")
            
            
            #If self.transform_mode != 
#cut line, a user interactive 2d line which represents a plane in 3d splace
    #head (type conrol point)
    #tail (type control points)
    #target mesh
    #view_direction (crossed with line to make plane normal for slicing)
    
    #draw method
    
    #new control point project method
    
    #mouse hover line calc
    
    
#retopo object, surface
    #colelction of cut lines
    #collection of countours to loft
    
    #n rings (crosses borrowed from looptools)
    #n follows (borrowed from looptools and or bsurfaces)
    
    #method contours from cutlines
    
    #method bridge contours
########NEW FILE########
__FILENAME__ = contour_utilities
'''
Copyright (C) 2013 CG Cookie
http://cgcookie.com
hello@cgcookie.com

Created by Patrick Moore

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import bpy
import bgl
import blf
import bmesh
import time
import math
import random

from collections import deque

from bpy_extras import view3d_utils
from mathutils import Vector, Matrix, Quaternion
from mathutils.geometry import intersect_line_plane, intersect_point_line, distance_point_to_plane, intersect_line_line_2d, intersect_line_line
from bpy_extras.view3d_utils import location_3d_to_region_2d

def callback_register(self, context):
        if str(bpy.app.build_revision)[2:7].lower == "unkno" or eval(str(bpy.app.build_revision)[2:7]) >= 53207:
            self._handle = bpy.types.SpaceView3D.draw_handler_add(self.menu.draw, (self, context), 'WINDOW', 'POST_PIXEL')
        else:
            self._handle = context.region.callback_add(self.menu.draw, (self, context), 'POST_PIXEL')
        return None
            
def callback_cleanup(self, context):
    if str(bpy.app.build_revision)[2:7].lower() == "unkno" or eval(str(bpy.app.build_revision)[2:7]) >= 53207:
        bpy.types.SpaceView3D.draw_handler_remove(self._handle, "WINDOW")
    else:
        context.region.callback_remove(self._handle)
    return None

def draw_points(context, points, color, size):
    '''
    draw a bunch of dots
    args:
        points: a list of tuples representing x,y SCREEN coordinate eg [(10,30),(11,31),...]
        color: tuple (r,g,b,a)
        size: integer? maybe a float
    '''

    bgl.glColor4f(*color)
    bgl.glPointSize(size)
    bgl.glBegin(bgl.GL_POINTS)
    for coord in points:  
        bgl.glVertex2f(*coord)  
    
    bgl.glEnd()   
    return

def edge_loops_from_bmedges(bmesh, bm_edges):
    """
    Edge loops defined by edges

    Takes [mesh edge indices] or a list of edges and returns the edge loops

    return a list of vertex indices.
    [ [1, 6, 7, 2], ...]

    closed loops have matching start and end values.
    """
    line_polys = []
    edges = bm_edges.copy()

    while edges:
        current_edge = bmesh.edges[edges.pop()]
        vert_e, vert_st = current_edge.verts[:]
        vert_end, vert_start = vert_e.index, vert_st.index
        line_poly = [vert_start, vert_end]

        ok = True
        while ok:
            ok = False
            #for i, ed in enumerate(edges):
            i = len(edges)
            while i:
                i -= 1
                ed = bmesh.edges[edges[i]]
                v_1, v_2 = ed.verts
                v1, v2 = v_1.index, v_2.index
                if v1 == vert_end:
                    line_poly.append(v2)
                    vert_end = line_poly[-1]
                    ok = 1
                    del edges[i]
                    # break
                elif v2 == vert_end:
                    line_poly.append(v1)
                    vert_end = line_poly[-1]
                    ok = 1
                    del edges[i]
                    #break
                elif v1 == vert_start:
                    line_poly.insert(0, v2)
                    vert_start = line_poly[0]
                    ok = 1
                    del edges[i]
                    # break
                elif v2 == vert_start:
                    line_poly.insert(0, v1)
                    vert_start = line_poly[0]
                    ok = 1
                    del edges[i]
                    #break
        line_polys.append(line_poly)

    return line_polys

def perp_vector_point_line(pt1, pt2, ptn):
    '''
    Vector bwettn pointn and line between point1
    and point2
    args:
        pt1, and pt1 are Vectors representing line segment
    
    return Vector
    
    pt1 ------------------- pt
            ^
            |
            |
            |<-----this vector
            |
            ptn
    '''
    pt_on_line = intersect_point_line(ptn, pt1, pt2)[0]
    alt_vect = pt_on_line - ptn
    
    return alt_vect


def altitude(point1, point2, pointn):
    edge1 = point2 - point1
    edge2 = pointn - point1
    if edge2.length == 0:
        altitude = 0
        return altitude
    if edge1.length == 0:
        altitude = edge2.length
        return altitude
    alpha = edge1.angle(edge2)
    altitude = math.sin(alpha) * edge2.length
    
    return altitude 
    
# iterate through verts
def iterate(points, newVerts, error,method = 1):
    '''
    args:
    points - list of vectors in order representing locations on a curve
    newVerts - list of indices? (mapping to arg: points) of aready identified "new" verts
    error - distance obove/below chord which makes vert considered a feature
    
    return:
    new -  list of vertex indicies (mappint to arg points) representing identified feature points
    or
    false - no new feature points identified...algorithm is finished.
    '''
    new = []
    for newIndex in range(len(newVerts)-1):
        bigVert = 0
        alti_store = 0
        for i, point in enumerate(points[newVerts[newIndex]+1:newVerts[newIndex+1]]):
            if method == 1:
                alti = perp_vector_point_line(points[newVerts[newIndex]], points[newVerts[newIndex+1]], point).length
            else:
                alti = altitude(points[newVerts[newIndex]], points[newVerts[newIndex+1]], point)
                
            if alti > alti_store:
                alti_store = alti
                if alti_store >= error:
                    bigVert = i+1+newVerts[newIndex]
        if bigVert:
            new.append(bigVert)
    if new == []:
        return False
    return new

#### get SplineVertIndices to keep
def simplify_RDP(splineVerts, error, method = 1):
    '''
    Reduces a curve or polyline based on altitude changes globally and w.r.t. neighbors
    args:
    splineVerts - list of vectors representing locations along the spline/line path
    error - altitude above global/neighbors which allows point to be considered a feature
    return:
    newVerts - a list of indicies of the simplified representation of the curve (in order, mapping to arg-splineVerts)
    '''

    start = time.time()
    
    # set first and last vert
    newVerts = [0, len(splineVerts)-1]

    # iterate through the points
    new = 1
    while new != False:
        new = iterate(splineVerts, newVerts, error, method = method)
        if new:
            newVerts += new
            newVerts.sort()
            
    print('finished simplification with method %i in %f seconds' % (method, time.time() - start))
    return newVerts

        

def relax(verts, factor = .75, in_place = True):
    '''
    verts is a list of Vectors
    first and last vert will not be changes
    
    this should modify the list in place
    however I have it returning verts?
    '''
    
    L = len(verts)
    if L < 4:
        print('not enough verts to relax')
        return verts
    
    
    deltas = [Vector((0,0,0))] * L
    
    for i in range(1,L-1):
        
        d = .5 * (verts[i-1] + verts[i+1]) - verts[i]
        deltas[i] = factor * d
    
    if in_place:
        for i in range(1,L-1):
            verts[i] += deltas[i]
        
        return True
    else:
        new_verts = verts.copy()
        for i in range(1,L-1):
            new_verts[i] += deltas[i]     
        
        return new_verts
        
    
    
def pi_slice(x,y,r1,r2,thta1,thta2,res,t_fan = False):
    '''
    args: 
    x,y - center coordinate
    r1, r2 inner and outer radius
    thta1: beginning of the slice  0 = to the right
    thta2:  end of the slice (ccw direction)
    '''
    points = [[0,0]]*(2*res + 2)  #the two arcs

    for i in range(0,res+1):
        diff = math.fmod(thta2-thta1 + 4*math.pi, 2*math.pi)
        x1 = math.cos(thta1 + i*diff/res) 
        y1 = math.sin(thta1 + i*diff/res)
    
        points[i]=[r1*x1 + x,r1*y1 + y]
        points[(2*res) - i+1] =[x1*r2 + x, y1*r2 + y]
        
    if t_fan: #need to shift order so GL_TRIANGLE_FAN can draw concavity
        new_0 = math.floor(1.5*(2*res+2))
        points = list_shift(points, new_0)
            
    return(points)

def draw_outline_or_region(mode, points, color):
        '''  
        arg: 
        mode - either bgl.GL_POLYGON or bgl.GL_LINE_LOOP
        color - will need to be set beforehand using theme colors. eg
        bgl.glColor4f(self.ri, self.gi, self.bi, self.ai)
        '''
        
        bgl.glColor4f(color[0],color[1],color[2],color[3])
        if mode == 'GL_LINE_LOOP':
            bgl.glBegin(bgl.GL_LINE_LOOP)
        else:
            bgl.glBegin(bgl.GL_POLYGON)
 
        # start with corner right-bottom
        for i in range(0,len(points)):
            bgl.glVertex2f(points[i][0],points[i][1])
 
        bgl.glEnd()

def arrow_primitive(x,y,ang,tail_l, head_l, head_w, tail_w):
    
    #primitive
    #notice the order so that the arrow can be filled
    #in by traingle fan or GL quad arrow[0:4] and arrow [4:]
    prim = [Vector((-tail_w,tail_l)),
            Vector((-tail_w, 0)), 
            Vector((tail_w, 0)), 
            Vector((tail_w, tail_l)),
            Vector((head_w,tail_l)),
            Vector((0,tail_l + head_l)),
            Vector((-head_w,tail_l))]
    
    #rotation
    rmatrix = Matrix.Rotation(ang,2)
    
    #translation
    T = Vector((x,y))
    
    arrow = [[None]] * 7
    for i, loc in enumerate(prim):
        arrow[i] = T + rmatrix * loc
        
    return arrow
    
    
def arc_arrow(x,y,r1,thta1,thta2,res, arrow_size, arrow_angle, ccw = True):
    '''
    args: 
    x,y - center coordinate of cark
    r1 = radius of arc
    thta1: beginning of the arc  0 = to the right
    thta2:  end of the arc (ccw direction)
    arrow_size = length of arrow point
    
    ccw = True draw the arrow
    '''
    points = [Vector((0,0))]*(res +1) #The arc + 2 arrow points

    for i in range(0,res+1):
        #able to accept negative values?
        diff = math.fmod(thta2-thta1 + 2*math.pi, 2*math.pi)
        x1 = math.cos(thta1 + i*diff/res) 
        y1 = math.sin(thta1 + i*diff/res)
    
        points[i]=Vector((r1*x1 + x,r1*y1 + y))

    if not ccw:
        points.reverse()
        
    end_tan = points[-2] - points[-1]
    end_tan.normalize()
    
    #perpendicular vector to tangent
    arrow_perp_1 = Vector((-end_tan[1],end_tan[0]))
    arrow_perp_2 = Vector((end_tan[1],-end_tan[0]))
    
    op_ov_adj = (math.tan(arrow_angle/2))**2
    arrow_side_1 = end_tan + op_ov_adj * arrow_perp_1
    arrow_side_2 = end_tan + op_ov_adj * arrow_perp_2
    
    arrow_side_1.normalize()
    arrow_side_2.normalize()
    
    points.append(points[-1] + arrow_size * arrow_side_1)
    points.append(points[-2] + arrow_size * arrow_side_2) 
           
    return(points)

def simple_circle(x,y,r,res):
    '''
    args: 
    x,y - center coordinate of cark
    r1 = radius of arc
    '''
    points = [Vector((0,0))]*res  #The arc + 2 arrow points

    for i in range(0,res):
        theta = i * 2 * math.pi / res
        x1 = math.cos(theta) 
        y1 = math.sin(theta)
    
        points[i]=Vector((r * x1 + x, r * y1 + y))
           
    return(points)     
    

    


def draw_3d_points(context, points, color, size):
    '''
    draw a bunch of dots
    args:
        points: a list of tuples representing x,y SCREEN coordinate eg [(10,30),(11,31),...]
        color: tuple (r,g,b,a)
        size: integer? maybe a float
    '''
    points_2d = [location_3d_to_region_2d(context.region, context.space_data.region_3d, loc) for loc in points]

    bgl.glColor4f(*color)
    bgl.glPointSize(size)
    bgl.glBegin(bgl.GL_POINTS)
    for coord in points_2d:  
        bgl.glVertex2f(*coord)  
    
    bgl.glEnd()   
    return

def draw_polyline_from_points(context, points, color, thickness, LINE_TYPE):
    '''
    a simple way to draw a line
    args:
        points: a list of tuples representing x,y SCREEN coordinate eg [(10,30),(11,31),...]
        color: tuple (r,g,b,a)
        thickness: integer? maybe a float
        LINE_TYPE:  eg...bgl.GL_LINE_STIPPLE or 
    '''
    
    if LINE_TYPE == "GL_LINE_STIPPLE":  
        bgl.glLineStipple(4, 0x5555)  #play with this later
        bgl.glEnable(bgl.GL_LINE_STIPPLE)  
    
    
    current_width = bgl.GL_LINE_WIDTH
    bgl.glColor4f(*color)
    bgl.glLineWidth(thickness)
    bgl.glBegin(bgl.GL_LINE_STRIP)
    
    for coord in points:  
        bgl.glVertex2f(*coord)  
    
    bgl.glEnd()  
    bgl.glLineWidth(1)  
    if LINE_TYPE == "GL_LINE_STIPPLE":  
        bgl.glDisable(bgl.GL_LINE_STIPPLE)  
        bgl.glEnable(bgl.GL_BLEND)  # back to uninterupted lines  
      
    return


def draw_polyline_from_3dpoints(context, points_3d, color, thickness, LINE_TYPE):
    '''
    a simple way to draw a line
    slow...becuase it must convert to screen every time
    but allows you to pan and zoom around
    
    args:
        points_3d: a list of tuples representing x,y SCREEN coordinate eg [(10,30),(11,31),...]
        color: tuple (r,g,b,a)
        thickness: integer? maybe a float
        LINE_TYPE:  eg...bgl.GL_LINE_STIPPLE or 
    '''
    points = [location_3d_to_region_2d(context.region, context.space_data.region_3d, loc) for loc in points_3d]
    if LINE_TYPE == "GL_LINE_STIPPLE":  
        bgl.glLineStipple(4, 0x5555)  #play with this later
        bgl.glEnable(bgl.GL_LINE_STIPPLE)  
    
    bgl.glColor4f(*color)
    bgl.glLineWidth(thickness)
    bgl.glBegin(bgl.GL_LINE_STRIP)
    for coord in points:  
        bgl.glVertex2f(*coord)  
    
    bgl.glEnd()  
      
    if LINE_TYPE == "GL_LINE_STIPPLE":  
        bgl.glDisable(bgl.GL_LINE_STIPPLE)  
        bgl.glEnable(bgl.GL_BLEND)  # back to uninterupted lines  
      
    return
    

def get_path_length(verts):
    '''
    sum up the length of a string of vertices
    '''
    l_tot = 0
    
    for i in range(0,len(verts)-1):
        d = verts[i+1] - verts[i]
        l_tot += d.length
        
    return l_tot

    
def get_com(verts):
    '''
    args:
        verts- a list of vectors to be included in the calc
        mx- thw world matrix of the object, if empty assumes unity
        
    '''
    COM = Vector((0,0,0))
    l = len(verts)
    for v in verts:
        COM += v  
    COM =(COM/l)

    return COM


def approx_radius(verts, COM):
    '''
    avg distance
    '''
    l = len(verts)
    app_rad = 0
    for v in verts:
        R = COM - v
        app_rad += R.length
        
    app_rad = 1/l * app_rad
    
    return app_rad    


def verts_bbox(verts):
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

def diagonal_verts(verts):
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    
    dx = max(xs) - min(xs)
    dy = max(ys) - min(ys)
    dz = max(zs) - min(zs)
    
    diag = math.pow((dx**2 + dy**2 + dz**2),.5)
    
    return diag

# calculate a best-fit plane to the given vertices
#modified from LoopTools addon
#TODO: CREDIT
#TODO: LINK
def calculate_best_plane(locs):
    
    # calculating the center of masss
    com = Vector()
    for loc in locs:
        com += loc
    com /= len(locs)
    x, y, z = com
    
    
    # creating the covariance matrix
    mat = Matrix(((0.0, 0.0, 0.0),
                  (0.0, 0.0, 0.0),
                  (0.0, 0.0, 0.0),
                 ))
    
    for loc in locs:
        mat[0][0] += (loc[0]-x)**2
        mat[1][0] += (loc[0]-x)*(loc[1]-y)
        mat[2][0] += (loc[0]-x)*(loc[2]-z)
        mat[0][1] += (loc[1]-y)*(loc[0]-x)
        mat[1][1] += (loc[1]-y)**2
        mat[2][1] += (loc[1]-y)*(loc[2]-z)
        mat[0][2] += (loc[2]-z)*(loc[0]-x)
        mat[1][2] += (loc[2]-z)*(loc[1]-y)
        mat[2][2] += (loc[2]-z)**2
    
    # calculating the normal to the plane
    normal = False
    try:
        mat.invert()
    except:
        if sum(mat[0]) == 0.0:
            normal = Vector((1.0, 0.0, 0.0))
        elif sum(mat[1]) == 0.0:
            normal = Vector((0.0, 1.0, 0.0))
        elif sum(mat[2]) == 0.0:
            normal = Vector((0.0, 0.0, 1.0))
    if not normal:
        # warning! this is different from .normalize()
        itermax = 500
        iter = 0
        vec = Vector((1.0, 1.0, 1.0))
        vec2 = (mat * vec)/(mat * vec).length
        while vec != vec2 and iter<itermax:
            iter+=1
            vec = vec2
            vec2 = mat * vec
            if vec2.length != 0:
                vec2 /= vec2.length
        if vec2.length == 0:
            vec2 = Vector((1.0, 1.0, 1.0))
        normal = vec2
    
    return(com, normal)
    
def cross_section(bme, mx, point, normal, debug = True):
    '''
    Takes a mesh and associated world matrix of the object and returns a cross secion in local
    space.
    
    Args:
        mesh: Blender BMesh
        mx:   World matrix (type Mathutils.Matrix)
        point: any point on the cut plane in world coords (type Mathutils.Vector)
        normal:  plane normal direction (type Mathutisl.Vector)
    '''
    
    times = []
    times.append(time.time())
    #bme = bmesh.new()
    #bme.from_mesh(me)
    #bme.normal_update()
    
    #if debug:
        #n = len(times)
        #times.append(time.time())
        #print('succesfully created bmesh in %f sec' % (times[n]-times[n-1]))
    verts =[]
    eds = []
    
    #convert point and normal into local coords
    #in the mesh into world space.This saves 2*(Nverts -1) matrix multiplications
    imx = mx.inverted()
    pt = imx * point
    no = imx.to_3x3() * normal  #local normal
    
    edge_mapping = {}  #perhaps we should use bmesh becaus it stores the great cycles..answer yup
    
    for ed in bme.edges:
        
        A = ed.verts[0].co
        B = ed.verts[1].co
        V = B - A
        
        proj = V.project(no).length
        
        #perp to normal = parallel to plane
        #only calc 2nd projection if necessary
        if proj == 0:
            
            #make sure not coplanar
            p_to_A = A - pt
            a_proj = p_to_A.project(no).length
            
            if a_proj == 0:
               
                edge_mapping[len(verts)] = ed.link_faces
                verts.append(1/2 * (A +B)) #put a midpoing since both are coplanar

        else:
            
            #this handles the one point on plane case
            v = intersect_line_plane(A,B,pt,no)
           
            if v:
                check = intersect_point_line(v,A,B)
                if check[1] >= 0 and check[1] <= 1:
                    
                                             
                    
                    #the vert coord index    =  the face indices it came from
                    edge_mapping[len(verts)] = [f.index for f in ed.link_faces]
                    verts.append(v)
    
    if debug:
        n = len(times)
        times.append(time.time())
        print('calced intersections %f sec' % (times[n]-times[n-1]))
       
    #iterate through smartly to create edge keys          
    for i in range(0,len(verts)):
        a_faces = set(edge_mapping[i])
        for m in range(i,len(verts)):
            if m != i:
                b_faces = set(edge_mapping[m])
                if a_faces & b_faces:
                    eds.append((i,m))
    
    if debug:
        n = len(times)
        times.append(time.time())
        print('calced connectivity %f sec' % (times[n]-times[n-1]))
        
    if len(verts):
        #new_me = bpy.data.meshes.new('Cross Section')
        #new_me.from_pydata(verts,eds,[])
        
    
        #if debug:
            #n = len(times)
            #times.append(time.time())
            #print('Total Time: %f sec' % (times[-1]-times[0]))
            
        return (verts, eds)
    else:
        return None
    

def cross_edge(A,B,pt,no):
    '''
    wrapper of intersect_line_plane that limits intersection
    to within the line segment.
    
    args:
        A - Vector endpoint of line segment
        B - Vector enpoint of line segment
        pt - pt on plane to intersect
        no - normal of plane to intersect
        
    return:
        list [Intersection Type, Intersection Point, Intersection Point2]
        eg... ['CROSS',Vector((0,1,0)), None]
        eg... ['POINT',Vector((0,1,0)), None]
        eg....['COPLANAR', Vector((0,1,0)),Vector((0,2,0))]
        eg....[None,None,None]
    '''
 
    ret_val = [None]*3 #list [intersect type, pt 1, pt 2]
    V = B - A #vect representation of the edge
    proj = V.project(no).length
    
    #perp to normal = parallel to plane
    #worst case is a coplanar issue where the whole face is coplanar..we will get there
    if proj == 0:
        
        #test coplanar
        #don't test both points.  We have already tested once for paralellism
        #simply proving one out of two points is/isn't in the plane will
        #prove/disprove coplanar
        p_to_A = A - pt
        #truly, we could precalc all these projections to save time but use mem.
        #because in the multiple edges coplanar case, we wil be testing
        #their verts over and over again that share edges.  So for a mesh with
        #a lot of n poles, precalcing the vert projections may save time!  
        #Hint to future self, look at  Nfaces vs Nedges vs Nverts
        #may prove to be a good predictor of which method to use.
        a_proj = p_to_A.project(no).length
        
        if a_proj == 0:
            print('special case co planar edge')
            ret_val = ['COPLANAR',A,B]
            
    else:
        
        #this handles the one point on plane case
        v = intersect_line_plane(A,B,pt,no)
       
        if v:
            check = intersect_point_line(v,A,B)
            if check[1] > 0 and check[1] < 1:  #this is the purest cross...no co-points
                #the vert coord index    =  the face indices it came from
                ret_val = ['CROSS',v,None]
                
            elif check[1] == 0 or check[1] == 1:
                print('special case coplanar point')
                #now add all edges that have that point into the already checked list
                #this takes care of poles
                ret_val = ['POINT',v,None]
    
    return ret_val

#adapted from opendentalcad then to pie menus now here
def outside_loop_2d(loop):
    '''
    args:
    loop: list of 
       type-Vector or type-tuple
    returns: 
       outside = a location outside bound of loop 
       type-tuple
    '''
       
    xs = [v[0] for v in loop]
    ys = [v[1] for v in loop]
    
    maxx = max(xs)
    maxy = max(ys)    
    bound = (1.1*maxx, 1.1*maxy)
    return bound

#adapted from opendentalcad then to pie menus now here
def point_inside_loop2d(loop, point):
    '''
    args:
    loop: list of vertices representing loop
        type-tuple or type-Vector
    point: location of point to be tested
        type-tuple or type-Vector
    
    return:
        True if point is inside loop
    '''    
    #test arguments type
    ptype = str(type(point))
    ltype = str(type(loop[0]))
    nverts = len(loop)
           
    if 'Vector' not in ptype:
        point = Vector(point)
        
    if 'Vector' not in ltype:
        for i in range(0,nverts):
            loop[i] = Vector(loop[i])
        
    #find a point outside the loop and count intersections
    out = Vector(outside_loop_2d(loop))
    intersections = 0
    for i in range(0,nverts):
        a = Vector(loop[i-1])
        b = Vector(loop[i])
        if intersect_line_line_2d(point,out,a,b):
            intersections += 1
    
    inside = False
    if math.fmod(intersections,2):
        inside = True
    
    return inside



def generic_axes_from_plane_normal(p_pt, no):
    '''
    will take a point on a plane and normal vector
    and return two orthogonal vectors which create
    a right handed coordinate system with z axist aligned
    to plane normal
    '''
    
    #get the equation of a plane ax + by + cz = D
    #Given point P, normal N ...any point R in plane satisfies
    # Nx * (Rx - Px) + Ny * (Ry - Py) + Nz * (Rz - Pz) = 0
    #now pick any xy, yz or xz and solve for the other point
    
    a = no[0]
    b = no[1]
    c = no[2]
    
    Px = p_pt[0]
    Py = p_pt[1]
    Pz = p_pt[2]
    
    D = a * Px + b * Py + c * Pz
    
    #generate a randomply perturbed R from the known p_pt
    R = p_pt + Vector((random.random(), random.random(), random.random()))
    
    #z = D/c - a/c * x - b/c * y
    if c != 0:
        Rz =  D/c - a/c * R[0] - b/c * R[1]
        R[2] = Rz
       
    #y = D/b - a/b * x - c/b * z 
    elif b!= 0:
        Ry = D/b - a/b * R[0] - c/b * R[2] 
        R[1] = Ry
    #x = D/a - b/a * y - c/a * z
    elif a != 0:
        Rx = D/a - b/a * R[1] - c/a * R[2]
        R[0] = Rz
    else:
        print('undefined plane you wanker!')
        return(False)
    
    #now R represents some other point in the plane
    #we will use this to define an arbitrary local
    #x' y' and z'
    X_prime = R - p_pt
    X_prime.normalize()
    
    Y_prime = no.cross(X_prime)
    Y_prime.normalize()
    
    return (X_prime, Y_prime)

def point_inside_loop_almost3D(pt, verts, no, p_pt = None, threshold = .01, debug = False):
    '''
    http://blenderartists.org/forum/showthread.php?259085-Brainstorming-for-Virtual-Buttons&highlight=point+inside+loop
    args:
       pt - 3d point to test of type Mathutils.Vector
       verts - 3d points representing the loop  
               TODO:  verts[0] == verts[-1] or implied?
               list with elements of type Mathutils.Vector
       no - plane normal
       plane_pt - a point on the plane.
                  if None, COM of verts will be used
       threshold - maximum distance to consider pt "coplanar"
                   default = .01
                   
       debug - Bool, default False.  Will print performance if True
                   
    return: Bool True if point is inside the loop
    '''
    if debug:
        start = time.time()
    #sanity checks
    if len(verts) < 3:
        print('loop must have 3 verts to be a loop and even then its sketchy')
        return False
    
    if no.length == 0:
        print('normal vector must be non zero')
        return False
    
    if not p_pt:
        p_pt = get_com(verts)
    
    if distance_point_to_plane(pt, p_pt, no) > threshold:
        return False
    
    (X_prime, Y_prime) = generic_axes_from_plane_normal(p_pt, no)
    
    verts_prime = []
    
    for v in verts:
        v_trans = v - p_pt
        vx = v_trans.dot(X_prime)
        vy = v_trans.dot(Y_prime)
        verts_prime.append(Vector((vx, vy)))
                           
    #transform the test point into the new plane x,y space
    pt_trans = pt - p_pt
    pt_prime = Vector((pt_trans.dot(X_prime), pt_trans.dot(Y_prime)))
                      
    pt_in_loop = point_inside_loop2d(verts_prime, pt_prime)
    
    return pt_in_loop

def face_cycle(face, pt, no, prev_eds, verts):#, connection):
    '''
    args:
        face - Blender BMFace
        pt - Vector, point on plane
        no - Vector, normal of plane
        
        
        These arguments will be modified
        prev_eds - MUTABLE list of previous edges already tested in the bmesh
        verts - MUTABLE list of Vectors representing vertex coords
        connection - MUTABLE dictionary of vert indices and face connections
        
    return:
        element - either a BMVert or a BMFace depending on what it finds.
    '''
    if len(face.edges) > 4:
        ngon = True
        print('oh sh** an ngon')
    else:
        ngon = False
        
    for ed in face.edges:
        if ed.index not in prev_eds:
            prev_eds.append(ed.index)
            A = ed.verts[0].co
            B = ed.verts[1].co
            result = cross_edge(A, B, pt, no)
                
            if result[0] == 'CROSS':
                
                #connection[len(verts)] = [f.index for f in ed.link_faces]
                verts.append(result[1])
                next_faces = [newf for newf in ed.link_faces if newf.index != face.index]
                if len(next_faces):
                    return next_faces[0]
                else:
                    #guess we got to a non manifold edge
                    print('found end of mesh!')
                    return None
                
            elif result[0] == 'POINT':
                if result[1] == A:
                    co_point = ed.verts[0]
                else:
                    co_point = ed.verts[1]
                    
                #connection[len(verts)] = [f.index for f in co_point.link_faces]  #notice we take the face loop around the point!
                verts.append(result[1])  #store the "intersection"
                    
                return co_point
            
                
def vert_cycle(vert, pt, no, prev_eds, verts):#, connection):
    '''
    args:
        vert - Blender BMVert
        pt - Vector, point on plane
        no - Vector, normal of plane
        
        
        These arguments will be modified
        prev_eds - MUTABLE list of previous edges already tested in the bmesh
        verts - MUTABLE list of Vectors representing vertex coords
        connection - MUTABLE dictionary of vert indices and face connections
        
    return:
        element - either a BMVert or a BMFace depending on what it finds.
    '''                
    
    for f in vert.link_faces:
        for ed in f.edges:
            if ed.index not in prev_eds:
                prev_eds.append(ed.index)
                A = ed.verts[0].co
                B = ed.verts[1].co
                result = cross_edge(A, B, pt, no)
                
                if result[0] == 'CROSS':
                    #connection[len(verts)] = [f.index for f in ed.link_faces]
                    verts.append(result[1])
                    next_faces = [newf for newf in ed.link_faces if newf.index != f.index]
                    if len(next_faces):
                        #return face to try face cycle
                        return next_faces[0]
                    else:
                        #guess we got to a non manifold edge
                        print('found end of mesh!')
                        return None
                    
                elif result[0] == 'COPLANAR':
                    cop_face = 0
                    for face in ed.link_faces:
                        if face.no.cross(no) == 0:
                            cop_face += 1
                            print('found a coplanar face')
    
                    if cop_face == 2:
                        #we have two coplanar faces with a coplanar edge
                        #this makes our cross section fail from a loop perspective
                        print("double coplanar face error, stopping here")
                        return None
                    
                    else:
                        #jump down line to the next vert
                        if ed.verts[0].index == vert.index:
                            element = ed.verts[1]
                            
                        else:
                            element = ed.verts[0]
                        
                        #add the new vert coord into the mix
                        #connection[len(verts)] = [f.index for f in element.link_faces]
                        verts.append(element.co)
                        
                        #return the vert to repeat the vert cycle
                        return element

def space_evenly_on_path(verts, edges, segments, shift = 0, debug = False):  #prev deved for Open Dental CAD
    '''
    Gives evenly spaced location along a string of verts
    Assumes that nverts > nsegments
    Assumes verts are ORDERED along path
    Assumes edges are ordered coherently
    Yes these are lazy assumptions, but the way I build my data
    guarantees these assumptions so deal with it.
    
    args:
        verts - list of vert locations type Mathutils.Vector
        eds - list of index pairs type tuple(integer) eg (3,5).
              should look like this though [(0,1),(1,2),(2,3),(3,4),(4,0)]     
        segments - number of segments to divide path into
        shift - for cyclic verts chains, shifting the verts along 
                the loop can provide better alignment with previous
                loops.  This should be 0 to 1 representing a percentage of segment length.
                Eg, a shift of .5 with 8 segments will shift the verts 1/16th of the loop length
                
    return
        new_verts - list of new Vert Locations type list[Mathutils.Vector]
    '''
    
    if segments >= len(verts):
        print('more segments requested than original verts')
        
     
    #determine if cyclic or not, first vert same as last vert
    if 0 in edges[-1]:
        cyclic = True
        #print('cyclic vert chain...oh well doesnt matter')
    else:
        cyclic = False
        #zero out the shift in case the vert chain insn't cyclic
        if shift != 0: #not PEP but it shows that we want shift = 0
            print('not shifting because this is not a cyclic vert chain')
            shift = 0
   
    #calc_length
    arch_len = 0
    cumulative_lengths = [0]#this is a list of the run sums
    for i in range(0,len(verts)-1):
        v0 = verts[i]
        v1 = verts[i+1]
        V = v1-v0
        arch_len += V.length
        cumulative_lengths.append(arch_len)
        
    if cyclic:
        #print('cyclic check?')
        #print(len(cumulative_lengths))
        #print(len(verts))
        v0 = verts[-1]
        v1 = verts[0]
        V = v1-v0
        arch_len += V.length
        cumulative_lengths.append(arch_len)
        #print(cumulative_lengths)
    
    #identify vert indicies of import
    #this will be the largest vert which lies at
    #no further than the desired fraction of the curve
    
    #initialze new vert array and seal the end points
    if cyclic:
        new_verts = [[None]]*(segments)
        #new_verts[0] = verts[0]
            
    else:
        new_verts = [[None]]*(segments + 1)
        new_verts[0] = verts[0]
        new_verts[-1] = verts[-1]
    
    
    n = 0 #index to save some looping through the cumulative lengths list
          #now we are leaving it 0 becase we may end up needing the beginning of the loop last
          #and if we are subdividing, we may hit the same cumulative lenght several times.
          #for now, use the slow and generic way, later developsomething smarter.
    for i in range(0,segments- 1 + cyclic * 1):
        desired_length_raw = (i + 1 + cyclic * -1)/segments * arch_len + shift * arch_len / segments
        #print('the length we desire for the %i segment is %f compared to the total length which is %f' % (i, desired_length_raw, arch_len))
        #like a mod function, but for non integers?
        if desired_length_raw > arch_len:
            desired_length = desired_length_raw - arch_len       
        elif desired_length_raw < 0:
            desired_length = arch_len + desired_length_raw #this is the end, + a negative number
        else:
            desired_length = desired_length_raw

        #find the original vert with the largets legnth
        #not greater than the desired length
        #I used to set n = J after each iteration
        for j in range(n, len(verts)+1):

            if cumulative_lengths[j] > desired_length:
                #print('found a greater length at vert %i' % j)
                #this was supposed to save us some iterations so that
                #we don't have to start at the beginning each time....
                #if j >= 1:
                    #n = j - 1 #going one back allows us to space multiple verts on one edge
                #else:
                    #n = 0
                break

        extra = desired_length - cumulative_lengths[j-1]
        if j == len(verts):
            new_verts[i + 1 + cyclic * -1] = verts[j-1] + extra * (verts[0]-verts[j-1]).normalized()
        else:
            new_verts[i + 1 + cyclic * -1] = verts[j-1] + extra * (verts[j]-verts[j-1]).normalized()
    
    eds = []
    
    for i in range(0,len(new_verts)-1):
        eds.append((i,i+1))
    if cyclic:
        #close the loop
        eds.append((i+1,0))
    if debug:
        print(cumulative_lengths)
        print(arch_len)
        print(eds)
        
    return new_verts, eds
 
def list_shift(seq, n):
    n = n % len(seq)
    return seq[n:] + seq[:n]


def alignment_quality_perpendicular(verts_1, verts_2, eds_1, eds_2):
    '''
    Calculates a quality measure of the alignment of edge loops.
    Ideally we want any connectors between loops to be as perpendicular
    to the loop as possible. Assume the loops are aligned properly in
    direction around the loop.
    
    args:
        verts_1: list of Vectors
        verts_2: list of Vectors
        
        eds_1: connectivity of the first loop, really just to test loop or line
        eds_2: connectivity of 2nd loops, really just to test for loop or line

    '''

    if 0 in eds_1[-1]:
        cyclic = True
        print('cyclic vert chain')
    else:
        cyclic = False
        
    if len(verts_1) != len(verts_2):
        print(len(verts_1))
        print(len(verts_2))
        print('non uniform loops, stopping until your developer gets smarter')
        return
    
    
    #since the loops in our case are guaranteed planar
    #because they come from cross sections, we can find
    #the plane normal very easily
    V1_0 = verts_1[1] - verts_1[0]
    V1_1 = verts_1[2] - verts_1[1]
    
    V2_0 = verts_2[1] - verts_2[0]
    V2_1 = verts_2[2] - verts_2[1]
    
    no_1 = V1_0.cross(V1_1)
    no_1.normalize()
    no_2 = V2_0.cross(V2_1)
    no_2.normalize()
    
    if no_1.dot(no_2) < 0:
        no_2 = -1 * no_2
    
    #average the two directions    
    ideal_direction = no_1.lerp(no_1,.5)


    
    
def point_in_tri(P, A, B, C):
    '''
    
    '''
    #straight from http://www.blackpawn.com/texts/pointinpoly/
    # Compute vectors        
    v0 = C - A
    v1 = B - A
    v2 = P - A
    
    #Compute dot products
    dot00 = v0.dot(v0)
    dot01 = v0.dot(v1)
    dot02 = v0.dot(v2)
    dot11 = v1.dot(v1)
    dot12 = v1.dot(v2)
    
    #Compute barycentric coordinates
    invDenom = 1 / (dot00 * dot11 - dot01 * dot01)
    u = (dot11 * dot02 - dot01 * dot12) * invDenom
    v = (dot00 * dot12 - dot01 * dot02) * invDenom
    
    #Check if point is in triangle
    return (u >= 0) & (v >= 0) & (u + v < 1)


def com_mid_ray_test(new_cut, established_cut, obj, search_factor = .5):
    '''
    function used to test intial validity of a connection
    between two cuts.
    
    args:
        new_cut:  a ContourCutLine
        existing_cut: ContourCutLine
        obj: The retopo object
        search_factor:  percentage of object bbox diagonal to search
        aim:  False or angle that new cut COM must fall within compared
              to existing plane normal.  Eg...pi/4 would be a 45 degree
              aiming cone
    
    
    returns: Bool
    '''
    
    
    A = established_cut.plane_com  #the COM of the cut loop
    B = new_cut.plane_com #the COM of the other cut loop
    C = .5 * (A + B)  #the midpoint of the line between them
                    
                    
    #pick a vert roughly in the middle
    n = math.floor(len(established_cut.verts_simple)/2)
            
            
    ray = A - established_cut.verts_simple[n]
    
    #just in case the vert IS the center of mass :-(
    if ray.length < .0001 and n != 0:
        ray = A - established_cut.verts_simple[n-1]
            
    ray.normalize()
            
            
    #limit serach to some fraction of the object bbox diagonal
    #search_radius = 1/2 * search_factor * obj.dimensions.length
    search_radius = 100
    imx = obj.matrix_world.inverted()     
            
    hit = obj.ray_cast(imx * (C + search_radius * ray), imx * (C - search_radius * ray))
            
    if hit[2] != -1:
        return True
    else:
        return False
    
    
def com_line_cross_test(com1, com2, pt, no, factor = 2):
    '''
    test used to make sure a cut is reasoably between
    2 other cuts
    
    higher factor requires better aligned cuts
    '''
    
    v = intersect_line_plane(com1,com2,pt,no)
    if v:
        #if the distance between the intersection is less than
        #than 1/factor the distance between the current pair
        #than this pair is invalide because there is a loop
        #in between
        check = intersect_point_line(v,com1,com2)
        invalid_length = (com2 - com1).length/factor  #length beyond which an intersection is invalid
        test_length = (v - pt).length
        
        #this makes sure the plane is between A and B
        #meaning the test plane is between the two COM's
        in_between = check[1] >= 0 and check[1] <= 1
        
        if in_between and test_length < invalid_length:
            return True

    
def discrete_curl(verts, z): #Adapted from Open Dental CAD by Patrick Moore
    '''
    calculates the curl relative to the direction given.
    It should be ~ +2pi or -2pi depending on whether the loop
    progresses clockwise or anticlockwise when viewed in the 
    z direction.  If the loop goes around twice it could be 4pi 6pi etc
    This is useful for making sure loops are indexed in the same direction.
    
    args:
       verts: a list of Vectors representing locations
       z: a vector representing the direction to compare the curl to
       
    '''
    if len(verts) < 3:
        print('not posisble for this to be a loop!')
        return
    
    curl = 0
    
    #just in case the vert chain has the last vert
    #duplicated.  We will need to not double the 
    #last one
    closed = False
    if verts[-1] == verts[0]:
        closed = True
        
    for n in range(0,len(verts) - 1*closed):

        a = int(math.fmod(n - 1, len(verts)))
        b = n
        c = int(math.fmod(n + 1, len(verts)))
        #Vec representation of the two edges
        V0 = (verts[b] - verts[a])
        V1 = (verts[c] - verts[b])
        
        #projection into the plane perpendicular to z
        #eg, the XY plane
        T0 = V0 - V0.project(z)
        T1 = V1 - V1.project(z)
        
        #cross product
        cross = T0.cross(T1)        
        sign = 1
        if cross.dot(z) < 0:
            sign = -1
        
        rot = T0.rotation_difference(T1)  
        ang = rot.angle
        curl = curl + ang*sign
    
    return curl

def rot_between_vecs(v1,v2, factor = 1):
    '''
    args:
    v1 - Vector Init
    v2 - Vector Final
    
    factor - will interpolate between them.  [0,1]
    
    returns the quaternion representing rotation between v1 to v2
    
    v2 = quat * v1
    
    notes: doesn't test for parallel vecs
    '''
    v1.normalize()
    v2.normalize()
    angle = factor * v1.angle(v2)
    axis = v1.cross(v2)
    axis.normalize()
    sin = math.sin(angle/2)
    cos = math.cos(angle/2)
    
    quat = Quaternion((cos, sin*axis[0], sin*axis[1], sin*axis[2]))
    
    return quat

    
    
    
    
def intersect_paths(path1, path2, cyclic1 = False, cyclic2 = False, threshold = .00001):
    '''
    intersects vert paths
    
    returns a list of intersections (verts)
    returns a list of vert index pairs that corresponds to the
    first vert of the edge in path1 and path 2 where the intersection
    occurs
    
    eg...if the 10th of path 1 intersectts with the 5th edge of path 2
    
    return intersect_vert,  [10,5]
    '''
    
    intersections = []
    inds = []
    for i in range(0,len(path1)-1 + 1*cyclic1):
        
        n = int(math.fmod(i+1, len(path1)))
        v1 = path1[n]
        v2 = path1[i]
        
        print([i,n])
        for j in range(0,len(path2)-1 + 1*cyclic2):
            
            m = int(math.fmod(j+1, len(path2)))
            v3 = path2[m]
            v4 = path2[j]
            
            #closes point on path1 edge, closes_point on path 2 edge
            
            intersect = intersect_line_line(v1,v2,v3,v4)
            
            if intersect:
                #make sure the intersection is within the segment
                
                
                
                inter_1 = intersect[0]
                verif1 = intersect_point_line(inter_1, v1,v2)
                
                inter_2 = intersect[1]
                verif2 = intersect_point_line(inter_1, v3,v4)
            
                diff = inter_2 - inter_1
                if diff.length < threshold and verif1[1] > 0 and verif2[1] > 0 and verif1[1] < 1 and verif2[1] < 1:
                    intersections.append(.5 * (inter_1 + inter_2))
                    inds.append([i,j])
    
    return intersections, inds
            
            
            
def  fit_path_to_endpoints(path,v0,v1):
    '''
    will rescale/rotate/tranlsate a path to fit between v0 and v1
    v0 is starting poin corrseponding to path[0]
    v1 is endpoint
    ''' 
    new_path = path.copy()
    
    vi_0 = path[0]
    vi_1 = path[-1]
    
    net_initial = vi_1 - vi_0
    net_final = v1 - v0
        
    scale = net_final.length/net_initial.length
    rot = rot_between_vecs(net_initial,net_final)
    
    
    for i, v in enumerate(new_path):
        new_path[i] = rot * v - vi_0
    
    for i, v in enumerate(new_path):
        new_path[i] = scale * v
            
    trans  = v0 - new_path[0]
    
    for i, v in enumerate(new_path):
        new_path[i] += trans
        
    return new_path
    


def pole_detector(bme):
    
    pole_inds = []
    
    for vert in bme.verts:
        if len(vert.link_edges) in {3,5,6}:
            pole_inds.append(vert.index)
            
    return pole_inds
        
    
def mix_path(path1,path2,pct = .5):
    '''
    will produce a blended path between path1 and 2 by
    interpolating each point along the path.
    
    will interpolate based on index at the moment, not based on  pctg down the curve
    
    pct is weight for path 1.
    '''
    
    if len(path1) != len(path2):
        print('eror until smarter programmer')
        return path1
    
    new_path = [0]*len(path1)
    
    for i, v in enumerate(path1):
        new_path[i] = v + pct * (path2[i] - v)
        
    return new_path
        
        
def align_edge_loops(verts_1, verts_2, eds_1, eds_2):
    '''
    Modifies vert order and edge indices to  provide best
    bridge between edge_loop1 and edge_loop2
    
    args:
        verts_1: list of Vectors
        verts_2: list of Vectors
        
        eds_1: connectivity of the first loop, really just to test loop or line
        eds_2: connectivity of 2nd loops, really just to test for loop or line
        
    return:
        verts_2
    '''
    print('testing alignment')
    if 0 in eds_1[-1]:
        cyclic = True
        print('cyclic vert chain')
    else:
        cyclic = False
    
    if len(verts_1) != len(verts_2):
        print(len(verts_1))
        print(len(verts_2))
        print('non uniform loops, stopping until your developer gets smarter')
        return verts_2
    
    
    #turns out, sum of diagonals is > than semi perimeter
    #lets exploit this (only true if quad is pretty much flat)
    #if we have paths reversed...our indices will give us diagonals
    #instead of perimeter
    #D1_O = verts_2[0] - verts_1[0]
    #D2_O = verts_2[-1] - verts_1[-1]
    #D1_R = verts_2[0] - verts_1[-1]
    #D2_R = verts_2[-1] - verts_1[0]
            
    #original_length = D1_O.length + D2_O.length
    #reverse_length = D1_R.length + D2_R.length
    #if reverse_length < original_length:
        #verts_2.reverse()
        #print('reversing')
        
    if cyclic:
        #another test to verify loop direction is to take
        #something reminiscint of the curl
        #since the loops in our case are guaranteed planar
        #(they come from cross sections) we can find a direction
        #from which to take the curl pretty easily.  Apologies to
        #any real mathemeticians reading this becuase I just
        #bastardized all these math terms.
        V1_0 = verts_1[1] - verts_1[0]
        V1_1 = verts_1[2] - verts_1[1]
        
        V2_0 = verts_2[1] - verts_2[0]
        V2_1 = verts_2[2] - verts_2[1]
        
        no_1 = V1_0.cross(V1_1)
        no_1.normalize()
        no_2 = V2_0.cross(V2_1)
        no_2.normalize()
        
        #we have no idea which way we will get
        #so just pick the directions which are
        #pointed in the general same direction
        if no_1.dot(no_2) < 0:
            no_2 = -1 * no_2
        
        #average the two directions    
        ideal_direction = no_1.lerp(no_1,.5)
    
        curl_1 = discrete_curl(verts_1, ideal_direction)
        curl_2 = discrete_curl(verts_2, ideal_direction)
        
        if curl_1 * curl_2 < 0:
            print('reversing loop 2')
            print('curl1: %f and curl2: %f' % (curl_1,curl_2))
            verts_2.reverse()
    
    else:
        #if the segement is not cyclic
        #all we have to do is compare the endpoints
        Vtotal_1 = verts_1[-1] - verts_1[0]
        Vtotal_2 = verts_2[-1] - verts_2[0]

        if Vtotal_1.dot(Vtotal_2) < 0:
            print('reversing path 2')
            verts_2.reverse()
            
    #iterate all verts and "handshake problem" them
    #into a dictionary?  That's not very effecient!
    edge_len_dict = {}
    for i in range(0,len(verts_1)):
        for n in range(0,len(verts_2)):
            edge = (i,n)
            vect = verts_2[n] - verts_1[i]
            edge_len_dict[edge] = vect.length
    
    shift_lengths = []
    #shift_cross = []
    for shift in range(0,len(verts_2)):
        tmp_len = 0
        #tmp_cross = 0
        for i in range(0, len(verts_2)):
            shift_mod = int(math.fmod(i+shift, len(verts_2)))
            tmp_len += edge_len_dict[(i,shift_mod)]
        shift_lengths.append(tmp_len)
           
    final_shift = shift_lengths.index(min(shift_lengths))
    if final_shift != 0:
        print("shifting verst by %i" % final_shift)
        verts_2 = list_shift(verts_2, final_shift)
    
    
            
    return verts_2
    



def cross_section_2_seeds(bme, mx, point, normal, pt_a, seed_index_a, pt_b, seed_index_b, debug = True):
    '''
    Takes a mesh and associated world matrix of the object and returns a cross secion in local
    space.
    
    Args:
        bme: Blender BMesh
        mx:   World matrix (type Mathutils.Matrix)
        point: any point on the cut plane in world coords (type Mathutils.Vector)
        normal:  plane normal direction (type Mathutisl.Vector)
        seed: face index, typically achieved by raycast
        exclude_edges: list of edge indices (usually already tested from previous iterations)
    '''
    
    times = []
    times.append(time.time())
    
    imx = mx.inverted()
    pt = imx * point
    no = imx.to_3x3() * normal
    
    
    #we will store vert chains here
    #indexed by the face they start with
    #after the initial seed facc
    #___________________
    #|     |     |      |
    #|  1  |init |  2   |
    #|_____|_____|______|
    #
    verts = {}
    
    
    #we need to test all edges of both faces for plane intersection
    #we should get intersections, because we define the plane
    #initially between the two seeds
    
    seeds = []
    prev_eds = []
    
    #the simplest expected result is that we find 2 edges
    for ed in bme.faces[seed_index_a].edges:
        
                  
        prev_eds.append(ed.index)
        
        A = ed.verts[0].co
        B = ed.verts[1].co
        result = cross_edge(A, B, pt, no)
        
        
        if result[0] != 'CROSS':
            print('got an anomoly')
            print(result[0])
            
        #here we are only tesing the good cases
        if result[0] == 'CROSS':
            #create a list to hold the verst we find from this seed
            #start with the a point....go toward b
            
            
            #TODO: CODE REVIEW...this looks like stupid code.
            potential_faces = [face for face in ed.link_faces if face.index != seed_index_a]
            if len(potential_faces):
                f = potential_faces[0]
                seeds.append(f)
                
                #we will keep track of our growing vert chains
                #based on the face they start with
                verts[f.index] = [pt_a]
                verts[f.index].append(result[1])
                
        
    #we now have 1 or two faces on either side of seed_face_a
    #now we walk until we do or dont find seed_face_b
    #this is a brute force, and we make no assumptions about which
    #direction is better to head in first.
    total_tests = 0
    for initial_element in seeds: #this will go both ways if they dont meet up.
        element_tests = 0
        element = initial_element
        stop_test = None
        while element and total_tests < 10000 and stop_test != seed_index_b:
            total_tests += 1
            element_tests += 1
            #first, we know that this face is not coplanar..that's good
            #if new_face.no.cross(no) == 0:
                #print('coplanar face, stopping calcs until your programmer gets smarter')
                #return None
            if type(element) == bmesh.types.BMFace:
                element = face_cycle(element, pt, no, prev_eds, verts[initial_element.index])#, edge_mapping)
                stop_test = element.index
            
            elif type(element) == bmesh.types.BMVert:
                element = vert_cycle(element, pt, no, prev_eds, verts[initial_element.index])#, edge_mapping)
                stop_test = None
        
        if stop_test == seed_index_b:
            print('found the other face!')
            verts[initial_element.index].append(pt_b)
            
        else:
            #trash the vert data...we aren't interested
            #if we want to do other stuff later...we can
            del verts[initial_element.index]
            
        if total_tests-2 > 10000:
            print('maxed out tests')
                   
        print('completed %i tests in this seed search' % element_tests)
        print('%i vertices found so far' % len(verts[initial_element.index]))                
    
    #this iterates the keys in verts
    #i have kept the keys consistent for
    #verts
    if len(verts):
        
        print('picking the shortes path by elements')
        print('later we will return both paths to allow')
        print('sorting by path length or by proximity to view')
        
        chains = [verts[key] for key in verts if len(verts[key]) > 2]
        if len(chains):
            sizes = [len(chain) for chain in chains]
        
            best = min(sizes)
            ind = sizes.index(best)
        
        
            return chains[ind]
        else:
            print('failure no chains > 2 verts')
            return
                    
    else:
        print('failed to find connection in either direction...perhaps points arent coplanar')
        return 
            
            

def cross_section_seed(bme, mx, point, normal, seed_index, debug = True):
    '''
    Takes a mesh and associated world matrix of the object and returns a cross secion in local
    space.
    
    Args:
        bme: Blender BMesh
        mx:   World matrix (type Mathutils.Matrix)
        point: any point on the cut plane in world coords (type Mathutils.Vector)
        normal:  plane normal direction (type Mathutisl.Vector)
        seed: face index, typically achieved by raycast
        exclude_edges: list of edge indices (usually already tested from previous iterations)
    '''
    
    times = []
    times.append(time.time())
    #bme = bmesh.new()
    #bme.from_mesh(me)
    #bme.normal_update()
    
    #if debug:
        #n = len(times)
        #times.append(time.time())
        #print('succesfully created bmesh in %f sec' % (times[n]-times[n-1]))
    verts =[]
    eds = []
    
    #convert point and normal into local coords
    #in the mesh into world space.This saves 2*(Nverts -1) matrix multiplications
    imx = mx.inverted()
    pt = imx * point
    no = imx.to_3x3() * normal  #local normal
    
    #edge_mapping = {}  #perhaps we should use bmesh becaus it stores the great cycles..answer yup
    
    #first initial search around seeded face.
    #if none, we may go back to brute force
    #but prolly not :-)
    seed_edge = None
    seed_search = 0
    prev_eds = []
    seeds =[]
    
    if seed_index > len(bme.faces) - 1:
        print('looks like we hit an Ngon, tentative support')
    
        #perhaps this should be done before we pass bme to this op?
        #we may perhaps need to re raycast the new faces?    
        ngons = []
        for f in bme.faces:
            if len(f.verts) >  4:
                ngons.append(f)
        
        #we should never get to this point because we are pre
        #triangulating the ngons before this function in the
        #final work flow but this leaves not chance and keeps
        #options to reuse this for later.        
        if len(ngons):
            new_geom = bmesh.ops.triangulate(bme, faces = ngons, use_beauty = True)
            new_faces = new_geom['faces']
            
            #now we must find a new seed index since we have added new geometry
            for f in new_faces:
                if point_in_tri(pt, f.verts[0].co, f.verts[1].co, f.verts[2].co):
                    print('found the point inthe tri')
                    if distance_point_to_plane(pt, f.verts[0].co, f.normal) < .001:
                        seed_index = f.index
                        print('found a new index to start with')
                        break
            
            
    #if len(bme.faces[seed_index].edges) > 4:
        #print('no NGon Support for initial seed yet! try again')
        #return None
    
    for ed in bme.faces[seed_index].edges:
        seed_search += 1        
        prev_eds.append(ed.index)
        
        A = ed.verts[0].co
        B = ed.verts[1].co
        result = cross_edge(A, B, pt, no)
        if result[0] == 'CROSS':
            #add the point, add the mapping move forward
            #edge_mapping[len(verts)] = [f.index for f in ed.link_faces]
            verts.append(result[1])
            potential_faces = [face for face in ed.link_faces if face.index != seed_index]
            if len(potential_faces):
                seeds.append(potential_faces[0])
                seed_edge = True
            else:
                seed_edge = False
        
    if not seed_edge:
        print('failed to find a good face to start with, cancelling until your programmer gets smarter')
        return None    
        
    #we have found one edge that crosses, now, baring any terrible disconnections in the mesh,
    #we traverse through the link faces, wandering our way through....removing edges from our list

    total_tests = 0
    
    #by the way we append the verts in the first face...we find A then B then start at A... so there is a little  reverse in teh vert order at the middle.
    verts.reverse()
    for element in seeds: #this will go both ways if they dont meet up.
        element_tests = 0
        while element and total_tests < 10000:
            total_tests += 1
            element_tests += 1
            #first, we know that this face is not coplanar..that's good
            #if new_face.no.cross(no) == 0:
                #print('coplanar face, stopping calcs until your programmer gets smarter')
                #return None
            if type(element) == bmesh.types.BMFace:
                element = face_cycle(element, pt, no, prev_eds, verts)#, edge_mapping)
            
            elif type(element) == bmesh.types.BMVert:
                element = vert_cycle(element, pt, no, prev_eds, verts)#, edge_mapping)
                
        print('completed %i tests in this seed search' % element_tests)
        print('%i vertices found so far' % len(verts))
        
 
    #The following tests for a closed loop
    #if the loop found itself on the first go round, the last test
    #will only get one try, and find no new crosses
    #trivially, mast make sure that the first seed we found wasn't
    #on a non manifold edge, which should never happen
    closed_loop = element_tests == 1 and len(seeds) == 2
    
    print('walked around cross section in %i tests' % total_tests)
    print('found this many vertices: %i' % len(verts))       
                
    if debug:
        n = len(times)
        times.append(time.time())
        print('calced intersections %f sec' % (times[n]-times[n-1]))
       
    #iterate through smartly to create edge keys
    #no longer have to do this...verts are created in order
    
    if closed_loop:        
        for i in range(0,len(verts)-1):
            eds.append((i,i+1))
        
        #the edge loop closure
        eds.append((i+1,0))
        
    else:
        #two more verts found than total tests
        #one vert per element test in the last loop
        
        
        #split the loop into the verts into the first seed and 2nd seed
        seed_1_verts = verts[:len(verts)-(element_tests)] #yikes maybe this index math is right
        seed_2_verts = verts[len(verts)-(element_tests):]
        seed_2_verts.reverse()
        
        seed_2_verts.extend(seed_1_verts)
        
        
        for i in range(0,len(seed_1_verts)-1):
            eds.append((i,i+1))
    
        verts = seed_2_verts
    if debug:
        n = len(times)
        times.append(time.time())
        print('calced connectivity %f sec' % (times[n]-times[n-1]))
        
    if len(verts):
        #new_me = bpy.data.meshes.new('Cross Section')
        #new_me.from_pydata(verts,eds,[])
        
    
        #if debug:
            #n = len(times)
            #times.append(time.time())
            #print('Total Time: %f sec' % (times[-1]-times[0]))
            
        return (verts, eds)
    else:
        return None
########NEW FILE########
__FILENAME__ = help_cgcookie
bl_info = {
    "name": "Add Blender Cookie to the Help menu",
    "location": "Help > Blender Cookie",
    "description": "Adds a link to Blender Cookie Tutorials in the Help menu",
    "author": "Jonathan Williamson",
    "version": (0,1),
    "blender": (2, 6, 6),
    "category": "Help",
    }

import bpy

def menu_func(self, context):
    self.layout.operator("wm.url_open", text="Blender Cookie", icon='HELP').url = "http://cgcookie.com/blender"
            
def register():
    bpy.types.INFO_MT_help.append(menu_func)
    
def unregister():
    bpy.types.INFO_MT_help.remove(menu_func)
    
if __name__ == "__main__":
    register()
########NEW FILE########
__FILENAME__ = tools_cleanup
import bpy
import os
import random
import math

#--------------------------------------------------------------------------
#-----------------------------CLEANUP OPERATORS ---------------------------
#--------------------------------------------------------------------------

 
 
#APPLY MIRROR MODIFIERS
class OBJECT_OT_modApplyMirror(bpy.types.Operator):
    bl_idname = "object.apply_mirror_mods"
    bl_label = "Appy Mirrors"
    bl_description = "Apply existing Mirror modifiers for either selected or all mesh objects"
    
    def execute(self, context):
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        
        if selOb:
            targetOb = selOb
            msg = "Mirror modifiers applied for selected mesh objects"
        else:
            targetOb = scn.objects
            msg = "Mirror modifiers applied for all mesh objects"       
            
        for ob in targetOb:
            if ob.type == "MESH":
                context.scene.objects.active = ob
                for mod in ob.modifiers:
                    if mod.type == "MIRROR":
                        #bpy.ops.object.modifier_move_up(modifier=mod.name)
                        bpy.ops.object.modifier_apply(apply_as='DATA',modifier=mod.name)
                    
        self.report({'INFO'}, msg)           
                                       
        return {'FINISHED'}
    

class OBJECT_OT_modSelectMirror(bpy.types.Operator):
    bl_idname = "object.select_mirror_mods"
    bl_label = "Select Mirrors"
    bl_description = "Select objects with MIRROR modifiers"
    
    def execute(self, context):
        scn = bpy.context.scene
        
        mirrorOb = []
        
        for ob in scn.objects:
            if ob.type == "MESH":
                context.scene.objects.active = ob
                for mod in ob.modifiers:
                    if mod.type == "MIRROR":
                        mirrorOb.append(ob)
                        
        if len(mirrorOb) >= 1:
            for ob in scn.objects:
                if ob in mirrorOb:
                    ob.select = True
                else:
                    ob.select = False    
            scn.objects.active = mirrorOb[0]
            self.report({'INFO'}, str(len(mirrorOb)) + " objects have a MIRROR modifier")
        else:
            self.report({'INFO'}, 'No objects have a MIRROR modifier')                                
                             
        return {'FINISHED'}
    
    
    
#APPLY SOLIDIFY MODIFIERS
class OBJECT_OT_modApplySolidified(bpy.types.Operator):
    bl_idname = "object.apply_solidify_mods"
    bl_label = "Appy Solidified"
    bl_description = "Apply existing Solidify modifiers for either selected or all mesh objects"
    
    def execute(self, context):
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        
        if selOb:
            targetOb = selOb
            msg = "Solidify modifiers applied for selected mesh objects"
        else:
            targetOb = scn.objects
            msg = "Solidify modifiers applied for all mesh objects"       
            
        for ob in targetOb:
            context.scene.objects.active = ob
            for mod in ob.modifiers:
                if mod.type == "SOLIDIFY":
                    #bpy.ops.object.modifier_move_up(modifier=mod.name)
                    bpy.ops.object.modifier_apply(apply_as='DATA',modifier=mod.name)
                    
        self.report({'INFO'}, msg)            
                                       
        return {'FINISHED'}
    
class OBJECT_OT_modSelectSolidify(bpy.types.Operator):
    bl_idname = "object.select_solidify_mods"
    bl_label = "Select Solidified"
    bl_description = "Select objects with SOLIDIFY modifiers"
    
    def execute(self, context):
        scn = bpy.context.scene
        
        solidifyOb = []
        
        for ob in scn.objects:
            if ob.type == "MESH":
                context.scene.objects.active = ob
                for mod in ob.modifiers:
                    if mod.type == "SOLIDIFY":
                        solidifyOb.append(ob)
                        
        if len(solidifyOb) >= 1:
            for ob in scn.objects:
                if ob in solidifyOb:
                    ob.select = True
                else:
                    ob.select = False    
            scn.objects.active = solidifyOb[0]
            self.report({'INFO'}, str(len(solidifyOb)) + " objects have a SOLIDIFY modifier")
        else:
            self.report({'INFO'}, 'No objects have a SOLIDIFY modifier')                                
                             
        return {'FINISHED'}
        

#DELETE UNUSED MATERIALS   
class OBJECT_OT_matDeleteUnused(bpy.types.Operator):
    bl_idname = "mat.delete_unused"
    bl_label = "Delete Unused"
    bl_description = "Delete Materials not linked to any object"
    
    def execute(self, context):
        scn = bpy.context.scene
        kt = bpy.context.window_manager.katietools
        unused = []
        
        for mat in bpy.data.materials:
            if mat.users == 0:
                unused.append(mat)
                bpy.data.materials.remove(mat)
                
        kt.mat_matcaps_exist = False
        self.report({'INFO'}, str(len(unused)) + " unused materials deleted")       
        
        return {'FINISHED'}
       

#NUKE UV MAPS    
class OBJECT_OT_uvNuke(bpy.types.Operator):
    bl_idname = "data.uv_nuke"
    bl_label = "Nuke UV Maps"
    bl_description = "Remove UV maps for all or selected objects"
    
    def execute(self, context):
                
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        
        if selOb:
            targetOb = selOb
            msg = "UV maps deleted from selected mesh objects"
        else:
            targetOb = scn.objects
            msg = "UV maps deleted from all mesh objects"       
            
        for ob in targetOb:
            if ob.type == "MESH":
                scn.objects.active = ob
            
                uv = list(ob.data.uv_textures)
                
                for i in range(len(uv)):
                        ob.data.uv_textures.active_index = i - 1
                        bpy.ops.mesh.uv_texture_remove()
                        
        self.report({'INFO'}, msg)                
        
        return {'FINISHED'}
    
    
class OBJECT_OT_dataUvSelect(bpy.types.Operator):
    bl_idname = "object.select_uv"
    bl_label = "Select UVs"
    bl_description = "Select objects with UV MAPS"
    
    def execute(self, context):
        scn = bpy.context.scene
        
        uvOb = []
        
        for ob in scn.objects:
            if ob.type == "MESH":
                uv = list(ob.data.uv_textures)
                if len(uv) >= 1:
                    uvOb.append(ob)
                        
        if len(uvOb) >= 1:
            for ob in scn.objects:
                if ob in uvOb:
                    ob.select = True
                else:
                    ob.select = False    
            scn.objects.active = uvOb[0]
            self.report({'INFO'}, str(len(uvOb)) + " objects have UV MAPS")
        else:
            self.report({'INFO'}, 'No objects have UV MAPS assigned')                                
                             
        return {'FINISHED'}    
    

#NUKE VERTEX GROUPS    
class OBJECT_OT_vgNuke(bpy.types.Operator):
    bl_idname = "data.vg_nuke"
    bl_label = "Nuke Vertex Groups"
    bl_description = "Delete Materials not linked to any object"
    
    def execute(self, context):    
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        
        if selOb:
            targetOb = selOb
            msg = "Vertex Groups deleted from selected mesh objects"
        else:
            targetOb = scn.objects
            msg = "Vertex Groups deleted from all mesh objects"
            
        for ob in targetOb:
            if ob.type == "MESH":
                scn.objects.active = ob
                bpy.ops.object.vertex_group_remove(all=True)
        self.report({'INFO'}, msg)
        
        return {'FINISHED'}
    
class OBJECT_OT_vgSelect(bpy.types.Operator):
    bl_idname = "object.select_vg"
    bl_label = "Select V Group"
    bl_description = "Select objects with VERTEX GROUPS"
    
    def execute(self, context):
        scn = bpy.context.scene
        
        vgOb = []
        
        for ob in scn.objects:
            if ob.type == "MESH":
                if len(ob.vertex_groups) >= 1:
                    vgOb.append(ob)
                        
        if len(vgOb) >= 1:
            for ob in scn.objects:
                if ob in vgOb:
                    ob.select = True
                else:
                    ob.select = False    
            scn.objects.active = vgOb[0]
            self.report({'INFO'}, str(len(vgOb)) + " objects have VERTEX GROUPS")
        else:
            self.report({'INFO'}, 'No objects have VERTEX GROUPS')                                
                             
        return {'FINISHED'}
    

#NUKE VERTEX COLORS    
class OBJECT_OT_vcNuke(bpy.types.Operator):
    bl_idname = "data.vc_nuke"
    bl_label = "Nuke Vertex Colors"
    bl_description = "Remove Vertex Color Layers for all or selected objects"
    
    def execute(self, context):
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        
        if selOb:
            targetOb = selOb
            msg = "Vertex Colors deleted from selected mesh objects"
        else:
            targetOb = scn.objects
            msg = "Vertex Colors deleted from all mesh objects"
            
        for ob in targetOb:
            if ob.type == "MESH":
                scn.objects.active = ob
            
                vc = list(ob.data.vertex_colors)
                
                for i in range(len(vc)):
                        ob.data.vertex_colors.active_index = i - 1
                        bpy.ops.mesh.vertex_color_remove()
                        
        self.report({'INFO'}, msg)               
        
        return {'FINISHED'}

    
class OBJECT_OT_vcSelect(bpy.types.Operator):
    bl_idname = "object.vc_select"
    bl_label = "Select V Color"
    bl_description = "Select objects with VERTEX COLORS"
    
    def execute(self, context):
        scn = bpy.context.scene
        
        vcOb = []
        
        for ob in scn.objects:
            if ob.type == "MESH":
                vc = list(ob.data.vertex_colors)
                if len(vc) >= 1:
                    vcOb.append(ob)
                        
        if len(vcOb) >= 1:
            for ob in scn.objects:
                if ob in vcOb:
                    ob.select = True
                else:
                    ob.select = False    
            scn.objects.active = vcOb[0]
            self.report({'INFO'}, str(len(vcOb)) + " objects have VERTEX COLORS")
        else:
            self.report({'INFO'}, 'No objects have VERTEX COLORS')                                
                             
        return {'FINISHED'}


def destroyData(key):
    xObjects = []
    xMeshes = []
    xMats = []
    
    
    for ob in bpy.data.objects:
        if key in ob.name and ob.users == 0:
            xObjects.append(ob)
            bpy.data.objects.remove(ob)
            
    for m in bpy.data.meshes:
        if key in m.name and m.users == 0:
            xMeshes.append(m)
            bpy.data.meshes.remove(m)
            
    for mat in bpy.data.materials:
        if key in mat.name and mat.users == 0:
            xMats.append(mat)
            bpy.data.materials.remove(mat)
            
    return ("--------------------------------------" + '\n' +
            str(len(xObjects)) + " Objects destroyed" + '\n' +
            str(len(xMeshes)) + " Meshes decimated" + '\n' + 
            str(len(xMats)) + " Materials extinguished" + '\n' +
            "--------------------------------------")     
                    
                    
    
class OBJECT_OT_cleanData(bpy.types.Operator):
    bl_idname = "data.clean_data"
    bl_label = "Clean Data"
    bl_description = "Destroy all unused data blocks globally or based on key string"
    
    key = bpy.props.StringProperty()
    
    def execute(self, context):
        if self.key == "**KEY**":
            self.report({'INFO'}, "No Key set. 'all' can be used to delete all unused data blocks")
        else:    
            destroy = destroyData(self.key)
            print (destroy)                               
                             
        return {'FINISHED'}

########NEW FILE########
__FILENAME__ = tools_display
import bpy
import os
import random
import math

#--------------------------------------------------------------------------
#----------------------------- DISPLAY OPERATORS -------------------------
#--------------------------------------------------------------------------


#OPENGL LIGHT PRESETS  

class OBJECT_OT_oglAddPreset(bpy.types.Operator):
    bl_idname = "system.ogl_add_preset"
    bl_label = "Add OpenGL Preset"
    bl_description = "Add OpenGL preset according to current settings"
           
    def execute(self, context):
        kt = bpy.context.window_manager.katietools
        system = bpy.context.user_preferences.system
        presets = bpy.context.user_preferences.ogl_presets
        preName = kt.ogl_name
        oglNames = []
        
        lampA = system.solid_lights[0]
        lampB = system.solid_lights[1]
        lampC = system.solid_lights[2]
        
        a_use = lampA.use
        a_dc = list(lampA.diffuse_color) # bizarrely CRUCIAL to list values (?!)
        a_sc = list(lampA.specular_color)
        a_dir = list(lampA.direction)
        b_use = lampB.use
        b_dc = list(lampB.diffuse_color)
        b_sc = list(lampB.specular_color)
        b_dir = list(lampB.direction)
        c_use = lampC.use
        c_dc = list(lampC.diffuse_color)
        c_sc = list(lampC.specular_color)
        c_dir = list(lampC.direction)
        
        presets[preName] = {"a_use":a_use, "a_dc":a_dc, "a_sc":a_sc, "a_dir":a_dir,
                            "b_use":b_use, "b_dc":b_dc, "b_sc":b_sc, "b_dir":b_dir,
                            "c_use":c_use, "c_dc":c_dc, "c_sc":c_sc, "c_dir":c_dir}
                            
        for p in presets:
            oglNames.append((p,p,'OpenGl preset'))
            
        kt.ogl_toggle = False    
            
        def register():  
            bpy.types.KatieToolsProps.ogl_preset_enum = bpy.props.EnumProperty(name='OpenGL Presets',default='Head Light',items=sorted(oglNames, key=lambda p: str(p[0]).lower(), reverse=True))
        register()    
                        
        return {'FINISHED'}
    
    
class OBJECT_OT_oglDeletePreset(bpy.types.Operator):
    bl_idname = "system.ogl_delete_preset"
    bl_label = "Delete OpenGL Preset"
    bl_description = "Delete selected OpenGL preset"
           
    def execute(self, context):
        kt = bpy.context.window_manager.katietools
        presets = bpy.context.user_preferences.ogl_presets
        oglNames = []
        
        del presets[kt.ogl_preset_enum] #delete from presets
                            
        for p in presets: #delete from enumerator
            oglNames.append((p,p,'OpenGl preset'))
            
        def register():  
            bpy.types.KatieToolsProps.ogl_preset_enum = bpy.props.EnumProperty(name='OpenGL Presets',default='Blender Default',items=sorted(oglNames, key=lambda p: str(p[0]).lower(), reverse=True))
        register()    
                        
        return {'FINISHED'}    

    
class OBJECT_OT_oglApplyPreset(bpy.types.Operator):
    bl_idname = "system.ogl_apply_preset"
    bl_label = "Apply OpenGL Preset"
    bl_description = "Apply selected OpenGL Preset"
           
    def execute(self, context):
        kt = bpy.context.window_manager.katietools
        system = bpy.context.user_preferences.system
        presets = bpy.context.user_preferences.ogl_presets
        preName = kt.ogl_preset_enum
        
        if kt.ogl_preset_enum  in presets:
            a_use = presets[kt.ogl_preset_enum]['a_use']
            a_dc = presets[kt.ogl_preset_enum]['a_dc']
            a_sc = presets[kt.ogl_preset_enum]['a_sc']
            a_dir = presets[kt.ogl_preset_enum]['a_dir']
            b_use = presets[kt.ogl_preset_enum]['b_use']
            b_dc = presets[kt.ogl_preset_enum]['b_dc']
            b_sc = presets[kt.ogl_preset_enum]['b_sc']
            b_dir = presets[kt.ogl_preset_enum]['b_dir']
            c_use = presets[kt.ogl_preset_enum]['c_use']
            c_dc = presets[kt.ogl_preset_enum]['c_dc']
            c_sc = presets[kt.ogl_preset_enum]['c_sc']
            c_dir = presets[kt.ogl_preset_enum]['c_dir']
            
            
        lampA = system.solid_lights[0]
        lampB = system.solid_lights[1]
        lampC = system.solid_lights[2]
        
        lampA.use = a_use
        lampA.diffuse_color = a_dc
        lampA.specular_color = a_sc
        lampA.direction = a_dir
        
        lampB.use = b_use
        lampB.diffuse_color = b_dc
        lampB.specular_color = b_sc
        lampB.direction = b_dir
        
        lampC.use = c_use
        lampC.diffuse_color = c_dc
        lampC.specular_color = c_sc
        lampC.direction = c_dir
                                     
        return {'FINISHED'} 


#DOUBLE-SIDED TOGGLE      
class OBJECT_OT_doubleSidedToggle(bpy.types.Operator):
    #connecting this class to the button of the same name
    bl_idname = "object.double_sided_toggle"
    bl_label = "Double-Sided"
    bl_description = "Toggle double-sided lighting in the viewport globally"
           
    #function that's executed when button is pushed
    def execute(self, context):
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        
        if selOb:
            targetOb = selOb
        else:
            targetOb = scn.objects

        newSel = []
        
        for ob in targetOb:
            if ob.type == "MESH":
                newSel.append(ob)
        if newSel[0].data.show_double_sided == True:
            for ob in newSel:
                mesh = ob.data
                mesh.show_double_sided = False
        elif newSel[0].data.show_double_sided == False:
            for ob in newSel:
                mesh = ob.data
                mesh.show_double_sided = True                
                        
        return {'FINISHED'} # operator worked 
        
#ALL EDGES TOGGLE             
class OBJECT_OT_allEdgesToggle(bpy.types.Operator):
    #connecting this class to the button of the same name
    bl_idname = "object.all_edges_toggle"
    bl_label = "All Edges"
    bl_description = "Toggle wireframe-on-shaded for all mesh objects in the viewport"
    
    #function that's executed when button is pushed
    def execute(self, context):
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        
        if selOb:
            targetOb = selOb
        else:
            targetOb = scn.objects     
            
        for ob in targetOb:
            if ob.type == "MESH":
                ob.select = 1
            else:
                ob.select = 0
                
        newSel = list(bpy.context.selected_objects)
            
        if newSel:        
            if newSel[0].show_wire == True:
                toggle = 1
            else:
                toggle = 0
                     
            for ob in newSel:
                if ob.type == "MESH":
                    mesh = ob.data
                    if toggle == 1:
                        ob.show_all_edges = False
                        ob.show_wire = False
                    if toggle == 0:
                        ob.show_all_edges = True
                        ob.show_wire = True
                        scn.objects.active = ob
                        #if bpy.ops.object.mode_set.poll():
                            #bpy.ops.object.mode_set(mode="EDIT")
                            #bpy.ops.object.mode_set(mode="OBJECT")
                            
        if targetOb == scn.objects:
            for ob in scn.objects:
                ob.select = False                    
                
        bpy.context.scene.frame_current = bpy.context.scene.frame_current     
        return {'FINISHED'} # operator worked           


#WIRE ONLY TOGGLE             
class OBJECT_OT_wireOnly(bpy.types.Operator):
    #connecting this class to the button of the same name
    bl_idname = "object.wire_only"
    bl_label = "Wire Only"
    bl_description = "Toggle object draw type to Wire"
           
    #function that's executed when button is pushed
    def execute(self, context):
        allOb = bpy.context.scene.objects
        selOb = bpy.context.selected_objects
        meshes = list(bpy.data.meshes)
        
        if selOb:
            selMeshes = []
            for ob in selOb:
                if ob.type == "MESH":
                    selMeshes.append(ob)
                            
            if selMeshes[0].draw_type == "WIRE":
                toggle = 1
            else:
                toggle = 0
                     
            for ob in selMeshes:
                if toggle == 1:
                    ob.draw_type = "TEXTURED"
                if toggle == 0:
                    ob.draw_type = "WIRE"
                    
        return {'FINISHED'} # operator worked  
    

#ALL NAMES TOGGLE             
class OBJECT_OT_allNamesToggle(bpy.types.Operator):
    #connecting this class to the button of the same name
    bl_idname = "object.all_names_toggle"
    bl_label = "Object Names"
    bl_description = "Toggle object names for all objects in the viewport"
           
    #function that's executed when button is pushed
    def execute(self, context):
        listOb = list(bpy.data.objects)
        if listOb:        
            if listOb[0].show_name == True:
                toggle = 1
            else:
                toggle = 0
                     
            for ob in context.scene.objects:
                if toggle == 1:
                    ob.show_name = False
                if toggle == 0:
                    ob.show_name = True                    
                        
        return {'FINISHED'} # operator worked           
   
#ALL AXIS TOGGLE             
class OBJECT_OT_allAxisToggle(bpy.types.Operator):
    #connecting this class to the button of the same name
    bl_idname = "object.all_axis_toggle"
    bl_label = "Object Axis"
    bl_description = "Toggle local axises for all objects in the viewport"
           
    #function that's executed when button is pushed
    def execute(self, context):
        listOb = list(bpy.data.objects)
        if listOb:        
            if listOb[0].show_axis == True:
                toggle = 1
            else:
                toggle = 0
                     
            for ob in context.scene.objects:
                if toggle == 1:
                    ob.show_axis = False
                if toggle == 0:
                    ob.show_axis = True                    
                        
        return {'FINISHED'} # operator worked 
    
#ALL TRANSPARENCY TOGGLE             
class OBJECT_OT_allTransparencyToggle(bpy.types.Operator):
    #connecting this class to the button of the same name
    bl_idname = "object.all_transparent_toggle"
    bl_label = "Transparency"
    bl_description = "Toggle material transparency in viewport for all objects"
           
    #function that's executed when button is pushed
    def execute(self, context):
        listOb = list(bpy.data.objects)
        if listOb:        
            if listOb[0].show_transparent == True:
                toggle = 1
            else:
                toggle = 0
                     
            for ob in context.scene.objects:
                if toggle == 1:
                    ob.show_transparent = False
                if toggle == 0:
                    ob.show_transparent = True                    
                        
        return {'FINISHED'} # operator worked
    
    
#----------- LIMIT VISIBLE OPERATROS --------------

class OBJECT_OT_fvShowNone(bpy.types.Operator):
    bl_idname = "object.fv_show_none"
    bl_label = "None"
    bl_description = "Uncheck all Types"

    def execute(self, context):
        kt = bpy.context.window_manager.katietools
        
        kt.ob_fvMesh = False
        kt.ob_fvCurve = False
        kt.ob_fvSurf = False
        kt.ob_fvMeta = False
        kt.ob_fvFont = False
        kt.ob_fvArm = False
        kt.ob_fvLat = False
        kt.ob_fvEmpty = False
        kt.ob_fvCam = False
        kt.ob_fvLamp = False
        kt.ob_fvSpeak = False
                        
        return {'FINISHED'} # operator worked
    
    
class OBJECT_OT_fvShowAll(bpy.types.Operator):
    bl_idname = "object.fv_show_all"
    bl_label = "All"
    bl_description = "Check all Types"

    def execute(self, context):
        kt = bpy.context.window_manager.katietools
        
        kt.ob_fvMesh = True
        kt.ob_fvCurve = True
        kt.ob_fvSurf = True
        kt.ob_fvMeta = True
        kt.ob_fvFont = True
        kt.ob_fvArm = True
        kt.ob_fvLat = True
        kt.ob_fvEmpty = True
        kt.ob_fvCam = True
        kt.ob_fvLamp = True
        kt.ob_fvSpeak = True
                        
        return {'FINISHED'} # operator worked

class OBJECT_OT_fvStore(bpy.types.Operator):
    bl_idname = "object.fv_store"
    bl_label = "Store"
    bl_description = "Store currently visible objects"        

    def execute(self, context):
        kt = bpy.context.window_manager.katietools
        allOb = bpy.context.scene.objects
        visOb = []
        
        if len(kt.ob_fvStore) > 0:
            bpy.types.KatieToolsProps.ob_fvStore = []
        else:    
            for ob in allOb:
                if ob.hide == False:
                    visOb.append(ob)
    
            bpy.types.KatieToolsProps.ob_fvStore = visOb
        
        print (kt.ob_fvStore) 
    
        return {'FINISHED'} # operator worked 
                  
class OBJECT_OT_fvToggle(bpy.types.Operator):
    bl_idname = "object.fv_toggle"
    bl_label = "FV Toggle"
    bl_description = "Toggle for Limited Visibility"
    
    fvType = bpy.props.StringProperty()

    def execute(self, context):
        scn = bpy.context.scene
        kt = bpy.context.window_manager.katietools
        visOb = [] 
             
        if len(kt.ob_fvStore) > 0:
            visOb = kt.ob_fvStore
        else:
            visOb = bpy.context.scene.objects
                        
        if self.fvType == "MESH":
            if kt.fvMESH == True:
                kt.fvMESH = False
            else:
                kt.fvMESH = True
            for ob in visOb:
                if ob.type == self.fvType:
                    if kt.fvMESH == True:
                        ob.hide = False
                    else:
                        ob.hide = True            
  
        if self.fvType == "CURVE":
            if kt.fvCURVE == True:
                kt.fvCURVE = False
            else:
                kt.fvCURVE = True
            for ob in visOb:
                if ob.type == self.fvType:
                    if kt.fvCURVE == True:
                        ob.hide = False
                    else:
                        ob.hide = True
                        
        if self.fvType == "SURFACE":
            if kt.fvSURFACE == True:
                kt.fvSURFACE = False
            else:
                kt.fvSURFACE = True
            for ob in visOb:
                if ob.type == self.fvType:
                    if kt.fvSURFACE == True:
                        ob.hide = False
                    else:
                        ob.hide = True
                        
        if self.fvType == "META":
            if kt.fvMETA == True:
                kt.fvMETA = False
            else:
                kt.fvMETA = True
            for ob in visOb:
                if ob.type == self.fvType:
                    if kt.fvMETA == True:
                        ob.hide = False
                    else:
                        ob.hide = True
                        
        if self.fvType == "FONT":
            if kt.fvFONT == True:
                kt.fvFONT = False
            else:
                kt.fvFONT = True
            for ob in visOb:
                if ob.type == self.fvType:
                    if kt.fvFONT == True:
                        ob.hide = False
                    else:
                        ob.hide = True
                        
        if self.fvType == "ARMATURE":
            if kt.fvARMATURE == True:
                kt.fvARMATURE = False
            else:
                kt.fvARMATURE = True
            for ob in visOb:
                if ob.type == self.fvType:
                    if kt.fvARMATURE == True:
                        ob.hide = False
                    else:
                        ob.hide = True
                        
        if self.fvType == "LATTICE":
            if kt.fvLATTICE == True:
                kt.fvLATTICE = False
            else:
                kt.fvLATTICE = True
            for ob in visOb:
                if ob.type == self.fvType:
                    if kt.fvLATTICE == True:
                        ob.hide = False
                    else:
                        ob.hide = True
                        
        if self.fvType == "EMPTY":
            if kt.fvEMPTY == True:
                kt.fvEMPTY = False
            else:
                kt.fvEMPTY = True
            for ob in visOb:
                if ob.type == self.fvType:
                    if kt.fvEMPTY == True:
                        ob.hide = False
                    else:
                        ob.hide = True
                        
        if self.fvType == "CAMERA":
            if kt.fvCAMERA == True:
                kt.fvCAMERA = False
            else:
                kt.fvCAMERA = True
            for ob in visOb:
                if ob.type == self.fvType:
                    if kt.fvCAMERA == True:
                        ob.hide = False
                    else:
                        ob.hide = True
                        
        if self.fvType == "LAMP":
            if kt.fvLAMP == True:
                kt.fvLAMP = False
            else:
                kt.fvLAMP = True
            for ob in visOb:
                if ob.type == self.fvType:
                    if kt.fvLAMP == True:
                        ob.hide = False
                    else:
                        ob.hide = True
                        
        if self.fvType == "SPEAKER":
            if kt.fvSPEAKER == True:
                kt.fvSPEAKER = False
            else:
                kt.fvSPEAKER = True
            for ob in visOb:
                if ob.type == self.fvType:
                    if kt.fvSPEAKER == True:
                        ob.hide = False
                    else:
                        ob.hide = True
                
        return {'FINISHED'} # operator worked       
    

#----------- SMOOTHING OPERATORS --------------

#ADD SUBSURF    
class OBJECT_OT_modAddSubsurf(bpy.types.Operator):
    bl_idname = "object.mod_add_subsurf"
    bl_label = "ON"
    bl_description = "Add a subsurf modifier named 'MySubsurf' to all mesh objects"
    
    def execute(self, context):
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        myModName = "MySubsurf"
        l = len(myModName)
        kt = bpy.context.window_manager.katietools
        hiPoly = []
        unsmoothOb = []
        for ob in scn.objects:
            if ob.unsmoothable == True:
                unsmoothOb.append(ob)
        
        if selOb:
            targetOb = selOb
        else:
            targetOb = scn.objects     
            
        for ob in targetOb:
            if ob.type == "MESH":
                if len(ob.data.polygons) < kt.subD_limit: #CHECK THE POLYCOUNT
                    if ob not in unsmoothOb: #CHECK TO MAKE SURE IT's NOT TAGGED UNSMOOTHABLE
                        if (myModName not in ob.modifiers):
                            m = ob.modifiers.new(myModName,'SUBSURF')
                            m.levels = kt.subD_val
                            m.render_levels = kt.subD_val_ren
                            m.show_on_cage = True
                            m.show_only_control_edges = True
                else:
                    hiPoly.append(ob.name)
        
        if len(hiPoly) != 0 and len(unsmoothOb) != 0:
            self.report({'INFO'}, "Some hi-poly and usnmoothable objects were not smoothed")
        elif len(unsmoothOb) != 0:
            self.report({'INFO'}, "Some usnmoothable objects were not smoothed")
        elif len(hiPoly) != 0:
            self.report({'INFO'}, "Some hi-poly bjects were not smoothed")    
            
            print ("OBJECTS NOT SMOOTHED:  " + str(hiPoly))
                    
        # Silly way to force all windows to refresh
        bpy.context.scene.frame_current = bpy.context.scene.frame_current

        return {'FINISHED'}

#REMOVE SUBSURF
class OBJECT_OT_modRemoveSubsurf(bpy.types.Operator):
    bl_idname = "object.mod_remove_subsurf"
    bl_label = "OFF"
    bl_description = "Remove the 'MySubsurf' from all mesh objects"
    
    def execute(self, context):
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        myModName = "MySubsurf"
        l = len (myModName)
        
        if selOb:
            targetOb = selOb
        else:
            targetOb = scn.objects     
            
        for ob in targetOb:
            if ob.type == "MESH":
                for mod in ob.modifiers:
                    if myModName == mod.name[:l]:
                        ob.modifiers.remove(mod)

        bpy.context.scene.frame_current = bpy.context.scene.frame_current
        
        return {'FINISHED'}


#TAG UNSMOOTHABLE
class OBJECT_OT_tagUnsmoothable(bpy.types.Operator):
    bl_idname = "object.tag_unsmooth"
    bl_label = "Tag Unsmoothable"
    bl_description = "Tag selected objects as not smoothable"
    
    #NOTE: Currently the 'unsmoothable' tag is remembered in window manager.
    #Might be smart to add this to 'scene' instead
    
    def execute(self, context):
        selOb = bpy.context.selected_objects
        
        if selOb:
            for ob in selOb:
                ob.unsmoothable = True  
        
        return {'FINISHED'}
    
class OBJECT_OT_selectUnsmoothable(bpy.types.Operator):
    bl_idname = "object.select_unsmooth"
    bl_label = "Select Unsmoothable"
    bl_description = "Select objects tagged as not smoothable"
    
    def execute(self, context):
        scn = bpy.context.scene
        unsmoothOb = []
        
        for ob in scn.objects:
            if ob.unsmoothable == True:
                unsmoothOb.append(ob)
                
        if len(unsmoothOb) == 0:
            self.report({'INFO'}, "No objects tagged as non smoothable")
        else:
            for ob in scn.objects:
                if ob in unsmoothOb:
                    ob.select = True
                else:
                    ob.select = False
                    
            scn.objects.active = unsmoothOb[0]              
            
        
        return {'FINISHED'}
    
class OBJECT_OT_clearUnsmoothable(bpy.types.Operator):
    bl_idname = "object.clear_unsmooth"
    bl_label = "Clear Unsmoothable"
    bl_description = "Clear unsmoothable tag from all or selected objects"
    
    def execute(self, context):
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        unsmoothOb = []
        
        for ob in scn.objects:
            if ob.unsmoothable == True:
                unsmoothOb.append(ob)
        
        if selOb:
            for ob in selOb:
                if ob in unsmoothOb:
                    ob.unsmoothable = False
        else:
            for ob in scn.objects:
                if ob in unsmoothOb:
                    ob.unsmoothable = False
        
        return {'FINISHED'}
########NEW FILE########
__FILENAME__ = tools_materials
import bpy
import os
import random
import math

#--------------------------------------------------------------------------
#-----------------------------MATERIAL OPERATORS --------------------------
#--------------------------------------------------------------------------

class OBJECT_OT_createColorMats(bpy.types.Operator):
    bl_idname = "material.create_color_mats"
    bl_label = "Create Colors"
    bl_description = "Create basic color materials"
    
    def execute (self, context):
        kt = bpy.context.window_manager.katietools
        mats = bpy.data.materials
            
        #red
        if ("KTc_RED" not in mats):
            red = bpy.data.materials.new('KTc_RED')
            red.diffuse_color = (1, .25, .25)
            red.specular_intensity = 0
            red.use_fake_user = True
        else:
            print ("RED exists")    
        
        #orange
        if ("KTc_ORANGE" not in mats):
            orange = bpy.data.materials.new('KTc_ORANGE')
            orange.diffuse_color = (1, .375, .155)
            orange.specular_intensity = 0
            orange.use_fake_user = True
        else:
            print ("ORANGE exists")    
        
        #yellow
        if ("KTc_YELLOW" not in mats):
            yellow = bpy.data.materials.new('KTc_YELLOW')
            yellow.diffuse_color = (1, 1, .25)
            yellow.specular_intensity = 0
            yellow.use_fake_user = True
        else:
            print ("YELLOW exists")     
        
        #green
        if ("KTc_GREEN" not in mats):
            green = bpy.data.materials.new('KTc_GREEN')
            green.diffuse_color = (0.25, 1, 0.25)
            green.specular_intensity = 0
            green.use_fake_user = True
        else:
            print ("GREEN exists")    
        
        #cyan
        if ("KTc_CYAN" not in mats):
            cyan = bpy.data.materials.new('KTc_CYAN')
            cyan.diffuse_color = (0.25, 1, 1)
            cyan.specular_intensity = 0
            cyan.use_fake_user = True
        else:
            print ("CYAN exists")
        
        #blue
        if ("KTc_BLUE" not in mats):
            blue = bpy.data.materials.new('KTc_BLUE')
            blue.diffuse_color = (0.25, .25, 1)
            blue.specular_intensity = 0
            blue.use_fake_user = True
        else:
            print ("BLUE exists")
        
        #purple
        if ("KTc_PURPLE" not in mats):
            purple = bpy.data.materials.new('KTc_PURPLE')
            purple.diffuse_color = (0.65, .25, 1)
            purple.specular_intensity = 0
            purple.use_fake_user = True
        else:
            print ("PURPLE exists")
        
        #brown
        if ("KTc_BROWN" not in mats):
            brown = bpy.data.materials.new('KTc_BROWN')
            brown.diffuse_color = (0.16, .1, .06)
            brown.specular_intensity = 0
            brown.use_fake_user = True
        else:
            print ("BROWN exists")
        
        #black
        if ("KTc_BLACK" not in mats):
            black = bpy.data.materials.new('KTc_BLACK')
            black.diffuse_color = (.05, .05, .05)
            black.specular_intensity = 0
            black.use_fake_user = True
        else:
            print ("BLACK exists")
        
        #white
        if ("KTc_WHITE" not in mats):
            white = bpy.data.materials.new('KTc_WHITE')
            white.diffuse_color = (.9, .9, .9)
            white.specular_intensity = 0
            white.use_fake_user = True
        else:
            print ("WHITE exists")
        
        #skin
        if ("KTc_SKIN" not in mats):
            skin = bpy.data.materials.new('KTc_SKIN')
            skin.diffuse_color = (1, .55, .435)
            skin.specular_intensity = 0
            skin.use_fake_user = True        
        else:
            print ("SKIN exists")
        
        #grey
        if ("KTc_GREY" not in mats):
            grey = bpy.data.materials.new('KTc_GREY')
            grey.diffuse_color = (.8, .8, .8)
            grey.specular_intensity = 0
            grey.use_fake_user = True
        else:
            print ("GREY exists")
        
        kt.mat_colors_exist = True
        
        return {'FINISHED'} 
  
    
class OBJECT_OT_matAssigner(bpy.types.Operator):
    bl_idname = "material.assign_mat"
    bl_label = "Assign Color"
    bl_description = "Assign color material to selected objects"

    def execute(self, context):
        kt = bpy.context.window_manager.katietools
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        
        for ob in selOb:
            if kt.mat_color != 'RANDOM':
                ob.active_material_index = 0
                ob.active_material = bpy.data.materials['KTc_' + kt.mat_color]
            elif kt.mat_color == 'RANDOM':
                ran = random.randint(0, 10)
                colors = ['KTc_RED',
                          'KTc_ORANGE',
                          'KTc_YELLOW',
                          'KTc_GREEN',
                          'KTc_CYAN',
                          'KTc_BLUE',
                          'KTc_PURPLE',
                          'KTc_BROWN',
                          'KTc_BLACK',
                          'KTc_WHITE',
                          'KTc_SKIN']
       
                ranColor = colors[ran]
                ob.active_material = bpy.data.materials[ranColor] 
            
        scn.render.engine = 'BLENDER_RENDER'
        scn.game_settings.material_mode = 'MULTITEXTURE'
        
        areas = bpy.context.screen.areas
        for area in areas:
            if area.type == 'VIEW_3D':
                if area.spaces.active.viewport_shade != 'SOLID':
                    area.spaces.active.viewport_shade='SOLID'
                        
           
        return {'FINISHED'} 
    
                      
class OBJECT_OT_matSpecToggle(bpy.types.Operator):
    bl_idname = "object.mat_spec_toggle"
    bl_label = "Specular"
    bl_description = "Toggle specular value for basic color materials"
    
    def execute(self, context):
        materials = bpy.data.materials
        if ('KTc_RED' in materials):
            if materials['KTc_RED'].specular_intensity == 0:
                sToggle = 0
            else:
                sToggle = 1
                    
            if sToggle == 0:
                materials['KTc_RED'].specular_intensity = 0.5
                materials['KTc_ORANGE'].specular_intensity = 0.5
                materials['KTc_YELLOW'].specular_intensity = 0.5
                materials['KTc_GREEN'].specular_intensity = 0.5
                materials['KTc_CYAN'].specular_intensity = 0.5
                materials['KTc_BLUE'].specular_intensity = 0.5
                materials['KTc_PURPLE'].specular_intensity = 0.5
                materials['KTc_BROWN'].specular_intensity = 0.5
                materials['KTc_BLACK'].specular_intensity = 0.5
                materials['KTc_WHITE'].specular_intensity = 0.5
                materials['KTc_GREY'].specular_intensity = 0.5
                materials['KTc_SKIN'].specular_intensity = 0.5
                
            elif sToggle == 1:
                materials['KTc_RED'].specular_intensity = 0
                materials['KTc_ORANGE'].specular_intensity = 0
                materials['KTc_YELLOW'].specular_intensity = 0
                materials['KTc_GREEN'].specular_intensity = 0
                materials['KTc_CYAN'].specular_intensity = 0
                materials['KTc_BLUE'].specular_intensity = 0
                materials['KTc_PURPLE'].specular_intensity = 0
                materials['KTc_BROWN'].specular_intensity = 0
                materials['KTc_BLACK'].specular_intensity = 0
                materials['KTc_WHITE'].specular_intensity = 0
                materials['KTc_GREY'].specular_intensity = 0
                materials['KTc_SKIN'].specular_intensity = 0 
        else:
            self.report({'INFO'}, "Color materials have not been created yet")           
        
        return {'FINISHED'}
    

    
def importMatcapImages(context):
    
    ext_list = ['jpg','bmp','iris','png','jpeg','targa','tga']
        
    kt = bpy.context.window_manager.katietools
    path = bpy.utils.script_paths('addons/katietools/matcap_img')
    pathStr = ''.join(path) #convert list object to string
    files = list(os.listdir(pathStr))
    
    imported = []
    
    for file in files:
        
        if file.split('.')[-1].lower() in ext_list:
            
            #import image files in dir as blender images
            texName = 'KTmc_' + file.split('.')[0]
            imgPath = pathStr + "\\" + file
            base = file.split('.')[0]
            enumItems = (base, base,'MatCap name')
            
            if (texName not in bpy.data.materials):
                                           
                newTex = bpy.data.textures.new(texName, 'IMAGE')
                
                image = bpy.data.images.load(imgPath)
                image.source = "FILE"
                image.filepath = imgPath
                bpy.data.textures[newTex.name].image = image
                
                #create matcaps
                matName = texName       
                mat = bpy.data.materials.new(matName)
                mat.use_nodes = True
                mat.use_fake_user = True
                
                tree = bpy.data.materials[matName].node_tree
                links = tree.links
                
                geo = tree.nodes.new('GEOMETRY')
                geo.name = 'KTmc_Geometry'
                geo.location = -200,0
                
                map = tree.nodes.new('MAPPING')
                map.name = 'KTmc_Mapping'
                map.scale = (1.0,-1.0,1.0)
                links.new(geo.outputs[5],map.inputs[0])
                
                tex = tree.nodes.new('TEXTURE')
                tex.name = 'KTmc_Texture'
                tex.location = 300,0
                tex.texture = bpy.data.textures[texName]
                links.new(map.outputs[0],tex.inputs[0])
                
                '''curve = tree.nodes.new('CURVE_RGB') #RGB Curve node for texture color space 'correction'
                curve.name = 'KTmc_CurveRGB'
                curve.location = 500,0
                cCurve = curve.mapping.curves[3] #the 'C' curve is first in the UI but last in the code
                cCurve.points.new(position=1, value=0.5) #what are the 'position' and 'value' parameters?!
                cCurve.points.new(position=2, value=0.5)
                cCurve.points[1].location = [0.2, 0.06]
                cCurve.points[2].location = [0.8, 0.9]
                cCurve.points[3].location = [1, 1]
                links.new(tex.outputs[1],curve.inputs[1])'''
                
                out = tree.nodes['Output'] #note this node already exists; different syntax
                out.name = 'KTmc_Output'
                out.location = 800,0
                links.new(tex.outputs[1],out.inputs[0])
                
                matNode = tree.nodes['Material']
                tree.nodes.remove(matNode)
                
                kt.mat_matcaps_exist = True
                
            else:
                kt.mat_matcaps_exist = True
                print ('MatCap ' + texName + ' already created')
                
            imported.append(enumItems)               

    def register():
        bpy.types.KatieToolsProps.mat_matcap = bpy.props.EnumProperty(name='Matcap',items=imported)
    
    register()
    
    
class OBJECT_OT_createMatCaps(bpy.types.Operator):
    bl_idname = "object.create_matcaps"
    bl_label = "Create MatCaps"
    bl_description = "Creates MatCap materials based on preset images" 
       
    def execute(self, context):
        scn = bpy.context.scene
        engine = scn.render.engine
        
        if engine !="BLENDER_RENDER":
            bpy.context.scene.render.engine = "BLENDER_RENDER"
          
        importMatcapImages(context)
        
        scn.render.engine = engine     
        
        return {'FINISHED'}
    
class OBJECT_OT_refreshMatCap(bpy.types.Operator):
    bl_idname = "object.refresh_matcap"
    bl_label = "Refresh Matcaps"
    bl_description = "Refresh Matcap list"
    
    def execute(self, context): 
          
        importMatcapImages(context)        
        
        return {'FINISHED'}   
    
    
class OBJECT_OT_matCapAssigner(bpy.types.Operator):
    bl_idname = "object.assign_matcap"
    bl_label = "Assign Matcap"
    bl_description = "Assign MatCap material to selected objects"
    
    def execute(self, context):
        selOb = bpy.context.selected_objects
        scn = bpy.context.scene
        kt = bpy.context.window_manager.katietools
        game = bpy.types.SceneGameData
        view = bpy.types.SpaceView3D
        selMatCap = kt.mat_matcap
        
        for ob in selOb:
            ob.active_material_index = 0
            ob.active_material = bpy.data.materials['KTmc_' + selMatCap]
            
        scn.render.engine = 'BLENDER_RENDER'
        scn.game_settings.material_mode = 'GLSL'
        
        areas = bpy.context.screen.areas
        for area in areas:
            if area.type == 'VIEW_3D':
                if area.spaces.active.viewport_shade != 'TEXTURED':
                    area.spaces.active.viewport_shade='TEXTURED'
        
        return {'FINISHED'}
    

    
class OBJECT_OT_selectByMat(bpy.types.Operator):
    bl_idname = "object.select_by_mat"
    bl_label = "Select By Mat"
    bl_description = "Select objects with the same active material as the as active object"
    
    def execute(self, context):
        actOb = bpy.context.active_object
        scnOb = bpy.context.scene.objects
        actMat = actOb.active_material
        
        for ob in scnOb:
            if ob.active_material == actMat:
                ob.select = True                         
                
        return {'FINISHED'}
        
    
    
class OBJECT_OT_matClear(bpy.types.Operator):
    bl_idname = "object.clear_mats"
    bl_label = "Clear Created"
    bl_description = "Clear materials created here"
    
    def clearMats(self):
        allOb = bpy.data.objects
        scn = bpy.context.scene
        game = bpy.types.SceneGameData
        view = bpy.types.SpaceView3D
        
        for ob in allOb:
            if ob.type == 'MESH':
                scn.objects.active = ob
                matSlots = list(ob.material_slots)
                msNames = []
                for ms in matSlots:
                    msNames.append(ms.name)
                mi = (i for i,x in enumerate(msNames) if ('KTc' in x) or ('KTmc' in x))
                for i in mi:
                    ob.active_material_index = i
                    bpy.ops.object.material_slot_remove()         
        
        #fix display settings    
        scn.render.engine = 'BLENDER_RENDER'
        scn.game_settings.material_mode = 'MULTITEXTURE'
        
        areas = bpy.context.screen.areas
        for area in areas:
            if area.type == 'VIEW_3D':
                if area.spaces.active.viewport_shade != 'SOLID':
                    area.spaces.active.viewport_shade='SOLID'                               
    
    def execute(self, context):
        mats = bpy.data.materials
        scn = bpy.context.scene
        kt = bpy.context.window_manager.katietools
        
        self.clearMats()
        
        for mat in mats:
            if ("KTmc_" in mat.name) or ("KTc_" in mat.name):
                mat.use_fake_user = False
                bpy.data.materials.remove(mat)
            
        self.report({'INFO'}, "Colors and MatCaps deleted")              
                          
        # Hack: Force update of material slot view
        scn.frame_set(scn.frame_current)
        kt.mat_matcaps_exist = False
        kt.mat_colors_exist = False        
        
        return {'FINISHED'}
    

class OBJECT_OT_matLinkSwitch(bpy.types.Operator):
    bl_idname = "object.mat_link_switch"
    bl_label = "Link Switch"
    bl_description = "Toggle all material slot links from OBJECT DATA to OBJECT, and vice versa"
    
    def execute(self, context):
        selOb = bpy.context.selected_objects
        actOb = bpy.context.active_object
        allOb = bpy.data.objects
        scn = bpy.context.scene
        
        obWithMat = []
        
        for ob in allOb:
            if ob.type == 'MESH' or ob.type == 'CURVE' or ob.type == 'SURFACE' or ob.type == 'META' or ob.type == 'FONT':
                if len(ob.material_slots) >= 1:
                    obWithMat.append(ob)
        
        if len(obWithMat) >= 1:                                 #if there is at least 1 object in array  
            firstObSlots = obWithMat[0].material_slots          #the first object's material slots
            for slot in firstObSlots:
                if slot == firstObSlots[0]:
                    if slot.link == 'DATA':
                        toggle = 0
                    elif slot.link == 'OBJECT':
                        toggle = 1
                        
            for ob in obWithMat:
                scn.objects.active = ob
        
                matSlots = list(ob.material_slots)
                matArray = []
                
                for slot in matSlots:
                    num = matSlots.index(slot)
                    matArray.append(slot.material)
                    
                    if toggle == 0:   
                        slot.link = "OBJECT"
                        self.report({'INFO'}, "All Links set to OBJECT")
                    elif toggle == 1:
                        slot.link = "DATA"
                        self.report({'INFO'}, "All Links set to DATA")
                    elif toggle == None:
                        self.report({'INFO'}, "No Toggle value")    
                            
                    slot.material = matArray[num]            
        else:
            self.report({'INFO'}, "No objects have material slots")
            
        scn.objects.active = actOb                   
        
        return {'FINISHED'}       

########NEW FILE########
__FILENAME__ = tools_mesh
import bpy
import os
import random
import math
import time
from operator import itemgetter

#--------------------------------------------------------------------------
#----------------------------- MESH OPERATORS -----------------------------
#--------------------------------------------------------------------------


class OBJECT_OT_calcTotalEdgeLength(bpy.types.Operator):
    bl_idname = "mesh.calc_total_edge_length"
    bl_label = "Calculate Total Edge Length"
    bl_description = "Calculates the total length of selected edges"
    
    def execute (self, context):
        actOb = bpy.context.active_object  
        edgeLength = 0
        edgeList = []
        
        for e in actOb.data.edges:
            if e.select == True:
                edgeList.append(e)
        
        for edge in edgeList:
            v1 = edge.vertices[0]
            v2 = edge.vertices[1]
            co1 = actOb.data.vertices[v1].co
            co2 = actOb.data.vertices[v2].co
            edgeLength += (co1-co2).length
            
        self.report({'INFO'}, "Total Edge Length:" + str("%.2f" % edgeLength))   
                  
              
        return {'FINISHED'}
    

#----------------------------- COPY VERTEX ORDER BY UVs by NUKEngine -----------------------------
    
#globals:
EPSILON = 0.000001
#EPSILON = 0.0001
#EPSILON = 0.001
isBMesh = False


#handle blender 2.62 and bmesh transparently
def faces(mesh):
    if isBMesh:
        return mesh.polygons
    else:
        return mesh.faces

def uvs(mesh, f, F):
    if isBMesh:
        uv_loops = mesh.uv_layers.active.data
        lstart = lend = F.loop_start
        lend += F.loop_total
        return [uv.uv for uv in uv_loops[lstart:lend]]
    else:
        return mesh.uv_textures.active.data[f].uv

def buildVertToFaceMap(mesh):
    VertexFaces = {}
    for fid, F in enumerate(faces(mesh)):
        for v in F.vertices:
            if not v in VertexFaces :
                VertexFaces[v] = []
            VertexFaces[v].append(fid)
    return VertexFaces

def buildDegreeOccuranceHeap(mesh, VertexFaces):
    degreeMap = {}
    for idx, f in VertexFaces.items():
        degree = len(f)
        if not degree in degreeMap:
            degreeMap[degree] = []
        degreeMap[degree].append(idx)
    occursHeap = []
    for degree, vList in degreeMap.items():
        occursHeap.append((len(vList), degree, vList))
    occursHeap = sorted(occursHeap, key=itemgetter(0,1))
    return occursHeap

    
    
def findMatchingVertsByUv(mesh1, v1, f1, mesh2, v2, f2, uvcache1, uvcache2):
    res = {}
    F1 = faces(mesh1)[f1]
    F2 = faces(mesh2)[f2]
    
    if len(F1.vertices) != len(F2.vertices):
        return {}
    
    if f1 in uvcache1:
        uvs1 = uvcache1[f1]
    else:
        uvs1 = uvs(mesh1, f1, F1)
        uvcache1[f1] = uvs1
        
    if f2 in uvcache2:
        uvs2 = uvcache2[f2]
    else:
        uvs2 = uvs(mesh2, f2, F2)
        uvcache2[f2] = uvs2
    
    if len(uvs1) != len(uvs2):
        return {}
    
    vidx1 = -1
    for idx1, vi1 in enumerate(F1.vertices):
        if v1 == vi1:
            vidx1 = idx1
            break
    vidx2 = -1
    for idx2, vi2 in enumerate(F2.vertices):
        if v2 == vi2:
            vidx2 = idx2
            break
    
    numVerts = len(F1.vertices)
    ok = True
    #print("DEBUG START************************** v: %i vs %i, f: %i vs %i" % (v1,v2, f1, f2))
    for i in range(numVerts):
        newIdx1 = (i + vidx1) % numVerts
        newIdx2 = (i + vidx2) % numVerts
        if abs(uvs1[newIdx1][0] - uvs2[newIdx2][0]) > EPSILON or abs(uvs1[newIdx1][1] - uvs2[newIdx2][1]) > EPSILON:
            ok = False
            #print("DEBUG: no match (newIdx1=%i, newIdx2=%i), conflict [%f, %f] vs. [%f, %f]" %(newIdx1, newIdx2, uvs1[newIdx1][0], uvs1[newIdx1][1], uvs2[newIdx2][0], uvs2[newIdx2][1]))
            # uvs = []
            # for x in mesh2.uv_textures.active.data[f2].uv:
                # uvs.append([x[0], x[1]])
            # print("DEBUG uvs of failed match %i: %s" % (f2, str(uvs)))
            break
        else:
            res[F1.vertices[newIdx1]] = F2.vertices[newIdx2]
            #print("DEBUG: match %i, %i with uvs %f, %f to %f, %f" % (F1.vertices[newIdx1], F2.vertices[newIdx2], uvs1[newIdx1][0], uvs1[newIdx1][1], uvs2[newIdx2][0], uvs2[newIdx2][1]))
    
    #print("DEBUG END  ************************** v1=%i v2=%i : %s" % (v1,v2, str(ok)))    
    if (ok):
        return res
    else:
        return {}
    
    
    
def mapByUv(mesh1, mesh2, vList1, vList2, VertexFaces1, VertexFaces2, uvcache1, uvcache2, mapping, invmapping, newMaps):
        refound = []
        for v1 in vList1:
                for f1 in VertexFaces1[v1]:
                    match = False
                    for v2 in vList2:
                        for f2 in VertexFaces2[v2]:
                            #if mesh1.vertics[v1]. not v1 in mapping
                            submatch = findMatchingVertsByUv(mesh1, v1, f1, mesh2, v2, f2, uvcache1, uvcache2)
                            if submatch:
                                #print("found submatch v1=%i v2=%i: map=%s" % (v1, v2, str(submatch)))
                                #mapping[v1] = v2
                                for v1x, v2x in submatch.items():
                                    if v1x in mapping:
                                        if mapping[v1x] != v2x:
                                            print("ERROR: found different mapping for vertex")
                                            print("original mapping %i,%i, new mapping %i,%i" % (v1x, mapping[v1x], v1x, v2x))
                                            raise Exception("ERROR: found different mapping for vertex")
                                        else:
                                            #print("DEBUG: refound mapping: v: %i,%i,  f: %i,%i" % (v1x, v2x, f1, f2))
                                            #FIXME: check: tricky bug if missing???
                                            #newMaps.append(v1x, v2x, f1, f2)
                                            refound.append((v1x, v2x, f1, f2))
                                    else:
                                        mapping[v1x] = v2x
                                        invmapping[v2x] = v1x
                                        newMaps.append((v1x, v2x, f1, f2))
                                        #print("DEBUG: found mapping: v: %i,%i,  f: %i,%i" % (v1x, v2x, f1, f2))
                                match = True
                    if not match:
                        print("ERROR: no match for face found:", f1)
                        uvsFail = []
                        for x in uvs(mesh1, f1, faces(mesh1)[f1]):
                            uvsFail.append([x[0], x[1]])
                        print("UVs mesh1 of face %i: %s" % (f1, str(uvsFail)))
                        for v2 in vList2:
                            for f2 in VertexFaces2[v2]:
                                uvsFail = []
                                for x in uvs(mesh2, f2, faces(mesh2)[f2]):
                                    uvsFail.append([x[0], x[1]])
                                print("UVs mesh2 of face %i: %s" % (f2, str(uvsFail)))
                        raise Exception("ERROR: no match for face found:", f1)
        #try to reduce data size
        #all faces found if here
        for vnew1, vnew2, f1, f2 in newMaps:
            #fixme: fix code that method is not called in this case
            if f1 in VertexFaces1[vnew1]:
                VertexFaces1[vnew1].remove(f1)
                VertexFaces2[vnew2].remove(f2)
                
        for vnew1, vnew2, f1, f2 in refound:
            #fixme: fix code that method is not called in this case
            if f1 in VertexFaces1[vnew1]:
                VertexFaces1[vnew1].remove(f1)
                VertexFaces2[vnew2].remove(f2)
                

#Algorithm:
#build min-heap of vertex lists by number of occurance of a certain vertex degree in the mesh (degree as number of faces containing a vertex)
#first step of the loop: map verts, candidate set is all unmapped verts with degree X [ aka map(pop(minheap)) ]
#second step of loop: loop: expand mappings found in step one: candidate set is all unmapped verts of all unmapped faces of a vertex that was mapped in step one or two.
def object_copy_indices (self, context):
    startTime = time.time()
    #create a copy of mesh1 (active), but with vertex order of mesh2 (selected)
    obj1 = bpy.context.active_object
    selected_objs = bpy.context.selected_objects[:]
    
    
    if not obj1 or len(selected_objs) != 2 or obj1.type != "MESH":
        raise Exception("Exactly two meshes must be selected. This Addon copies vertex order from mesh1 to copy of mesh2")
    
    selected_objs.remove(obj1)
    obj2 = selected_objs[0]
    
    if obj2.type != "MESH":
        raise Exception("Exactly two meshes must be selected. This Addon copies vertex order from mesh1 to copy of mesh2")
    
    
    mesh1 = obj1.data
    mesh2 = obj2.data
    
    #ugly block, but fast to implement
    global isBMesh
    try:
        face = mesh1.polygons
        print("is BMesh")
        isBMesh = True
    except:
        print("is not BMesh")
        face = mesh1.faces
        isBMesh = False
    if isBMesh:
        # be sure that both are bmesh, otherwise crash (should not be possible or I understand something wrong)
        face = mesh2.polygons
    
    if not mesh1.uv_textures or len(mesh1.uv_textures) == 0 or not mesh2.uv_textures or len(mesh2.uv_textures) == 0:
        raise Exception("Both meshes must have a uv mapping. This operator even assumes matching uv mapping!")
    if len(mesh1.vertices) != len(mesh2.vertices):
        raise Exception("Both meshes must have the same number of vertices. But it is %i:%i" % (len(mesh1.vertices), len(mesh2.vertices)))
    
    #FIXME: faces seem invalid later, or is there another bug? so we use face indices for now and look them up on use
    VertexFaces1 = buildVertToFaceMap(mesh1)
    VertexFaces2 = buildVertToFaceMap(mesh2)
    degreeHeap1 = buildDegreeOccuranceHeap(mesh1, VertexFaces1)
    degreeHeap2 = buildDegreeOccuranceHeap(mesh2, VertexFaces2)

    uvcache1 = {}
    uvcache2 = {}
    
    mapping = {}
    invmapping = {}
    passes = 0
    
    print("Trying to find initial mapping of all vertices with that degree (num faces) that occurs the fewest in the mesh")
    while len(mapping) < len(mesh1.vertices) and len(degreeHeap1) > 0:
        num1, degree1, vList1 = degreeHeap1.pop(0)
        num2, degree2, vList2 = degreeHeap2.pop(0)
        newMaps = []
        if num1 == num2 and degree1 == degree2 and len(vList1) == len(vList2):
            print("DEBUG: Looking at %i verts with degree %i" % (len(vList1), degree1))
            #remove all known from vlists (TODO: optimize)
            tmpList = []
            for vxx in vList1:
                if not vxx in mapping:
                    tmpList.append(vxx)
            vList1 = tmpList
            tmpList = []
            for vxx in vList2:
                if not vxx in invmapping:
                    tmpList.append(vxx)
            vList2 = tmpList
            
            print("DEBUG: relevant of those %i in mesh1 and %i in mesh2" % (len(vList1), len(vList2)))
            #first step of the loop: map verts, candidate set is all verts with degree X (degree as number of faces containing a vertex)
            mapByUv(mesh1, mesh2, vList1, vList2, VertexFaces1, VertexFaces2, uvcache1, uvcache2, mapping, invmapping, newMaps)
            passes += 1
            #expand over all neighbours of newly known vertex mappings
            #second step of loop: loop: expand mappings found in step one (or in this step)
            while len(newMaps) > 0:
                #print("DEBUG: handling newMaps: %s" % str(newMaps))
                newerMaps = []
                for vnew1, vnew2, f1, f2 in newMaps:
                    newFs1 = VertexFaces1[vnew1]
                    newFs2 = VertexFaces2[vnew2]
                    if newFs1 and newFs2:
                        vList1 = []
                        vList2 = []
                        for fx1 in newFs1:
                            for vx1 in faces(mesh1)[fx1].vertices:
                                if not vx1 in mapping:
                                    vList1.append(vx1)
                        for fx2 in newFs2:
                            for vx2 in faces(mesh2)[fx2].vertices:
                                if not vx2 in invmapping:
                                    vList2.append(vx2)
                        if vList1 and vList2:
                            tmpMap = []
                            #print("DEBUG: calling mapByUv to extend known mappings")
                            #candidate set is all verts of all faces (without already mapped faces) of a vertex that was mapped in step one or two
                            mapByUv(mesh1, mesh2, vList1, vList2, VertexFaces1, VertexFaces2, uvcache1, uvcache2, mapping, invmapping, tmpMap)
                            newerMaps = newerMaps + tmpMap
                            passes += 1
                            if passes % 500 == 0:
                                print("after %i extension runs of mapByUv (%s seconds) we have %i mappings." % (passes, str(time.time()-startTime),len(mapping)))
                                print("current newMaps size:", len(newMaps))
                newMaps = newerMaps
        else:
            print("ERROR: the meshes have a different topology.")
            raise Exception("ERROR: the meshes have a different topology.")
        print("DEBUG: ran %i executions of mapByUv to extend mapping" % passes)
        print("DEBUG: mappingsize=%i, verts=%i" % (len(mapping), len(mesh1.vertices)))
        if len(mapping) < 50:
            print("Mapping so far: %s" % (str(mapping)))

    if len(mapping) == len(mesh1.vertices):
        verts_pos=[]
        faces_indices=[]
        print("Found complete mapping")
        for v in mesh2.vertices:
            verts_pos.append(mesh1.vertices[invmapping[v.index]].co)
        
        for f in faces(mesh2):
            vs=[]
            for v in f.vertices:
                vs.append(v)
            faces_indices.append(vs)
        
        #create new mesh
        me=bpy.data.meshes.new("%s_v_order_%s" % (mesh1.name, mesh2.name))
        ob=bpy.data.objects.new("%s_v_order_%s" % (obj1.name, obj2.name) ,me)           
                 
        me.from_pydata(verts_pos, [], faces_indices)
        
        ob.matrix_world = obj1.matrix_world
        
        bpy.context.scene.objects.link(ob)
        me.update()
        print("New Object created. object=%s, mesh=%s in %s seconds" % (ob.name, me.name, str(time.time()-startTime)))
    else:
        print("ERROR: Process failed, did not find a mapping for all vertices")
        raise Exception("ERROR: Process failed, did not find a mapping for all vertices")    


class OBJECT_OT_copyVertIndices(bpy.types.Operator):
    bl_idname = "object.copy_vertex_order_by_uvs"
    bl_label = "Copy Vertex Order by UVs"
    bl_description = "Copy vertex order from mesh1 to a copy of mesh2.  CREDIT to NUKEngine"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        
        object_copy_indices(self, context)
 
        return {'FINISHED'}
    

#--------------------- APPLY SHAPEKEYS ----------------------------------

class OBJECT_OT_shapeKeyApply(bpy.types.Operator):
    bl_idname = "data.shapekey_apply"
    bl_label = "Apply Shapekeys"
    bl_description = "Applies current shape state and removes shapekeys for all or selected mesh objects"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        scn = bpy.context.scene
        scnOb = scn.objects
        selOb = bpy.context.selected_objects
        actObName = bpy.context.active_object.name
        applicables = []
        
        if selOb:
            for ob in selOb:
                if ob.type == "MESH":
                    if ob.data.shape_keys != None:
                        applicables.append(ob.name)
                        scnOb.active = ob
                        name = ob.name
                        shapeKeys = ob.data.shape_keys.key_blocks
                                     
                        bpy.ops.object.select_all(action='DESELECT') # CRUCIAL TO WORKING
                        ob.select = True
                        bpy.ops.object.duplicate()
                        
                        actOb = bpy.context.active_object
                        actOb.name = "TEMP_" + name #duplicated TEMP object
                        actOb.select = True
                        ob.select = True
                        scn.objects.active = ob #original object duplicated and selection setup for join_shapes
                        
                        
                        for i in reversed(range(len(shapeKeys))):
                            ob.active_shape_key_index = i
                            bpy.ops.object.shape_key_remove() #shapekeys removed backwards to Basis on original object
                                        
                        bpy.ops.object.join_shapes()
                        
                        for i in range(len(shapeKeys)):
                            ob.active_shape_key_index = i
                            bpy.ops.object.shape_key_remove() #shapekeys forwards leaving the shape baked into the original object
                            ob.active_shape_key_index = i
                            bpy.ops.object.shape_key_remove() #HAD TO ADD THESE LINES TWICE FOR 2.64 (?!)
                            
                        ob.select = False
                        
                        bpy.ops.object.delete() #delete TEMP object
                    
            for ob in selOb:    
                ob.select = True
                
            scnOb.active = scnOb[actObName]
            
            count = str(len(applicables))
            self.report({'INFO'}, count + " objects with shapekeys have been applied")
        else:        
            self.report({'INFO'}, "No objects selected")      
        
        return {'FINISHED'}
    
    
class OBJECT_OT_skSelect(bpy.types.Operator):
    bl_idname = "object.sk_select"
    bl_label = "Select Shapekey"
    bl_description = "Select objects with SHAPEKEYS"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        scn = bpy.context.scene
        
        skOb = []
        
        for ob in scn.objects:
            if ob.type == "MESH":
                if ob.data.shape_keys != None:
                    sk = list(ob.data.shape_keys.key_blocks)
                    if len(sk) >= 1:
                        skOb.append(ob)
                        
        if len(skOb) >= 1:
            for ob in scn.objects:
                if ob in skOb:
                    ob.select = True
                else:
                    ob.select = False    
            scn.objects.active = skOb[0]
            self.report({'INFO'}, str(len(skOb)) + " objects have SHAPEKEYS")
        else:
            self.report({'INFO'}, 'No objects have SHAPEKEYS')                                
                             
        return {'FINISHED'}

#--------------------- SK SYMMETRIZE ----------------------------------
def vgroupHalves(ob):
    #### select left half of verts and add to new vertex group ####
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action='DESELECT') # deselect all verts
        bpy.ops.object.mode_set(mode="OBJECT")
        
    for v in ob.data.vertices:
        if v.co[0] >= 0:
            v.select = True
    
    bpy.ops.object.vertex_group_add()
    ob.vertex_groups.active.name = "kt_temp_halfL"
    
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.object.vertex_group_assign()
        bpy.ops.mesh.select_all(action='INVERT')
        bpy.ops.object.mode_set(mode="OBJECT")
        
    bpy.ops.object.vertex_group_add()
    ob.vertex_groups.active.name = "kt_temp_halfR"
    
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.object.vertex_group_assign()
        bpy.ops.object.mode_set(mode="OBJECT")  

def skSymmetrize(ob):
    skName = ob.active_shape_key.name
    skVG = ob.active_shape_key.vertex_group
    shapeKeys = ob.data.shape_keys.key_blocks
    
    shapeKeys[skName].vertex_group = "kt_temp_halfL"
    bpy.ops.object.shape_key_add(from_mix=True)
    ob.active_shape_key.name = "kt_temp_mirror"
    bpy.ops.object.shape_key_mirror()
    shapeKeys["kt_temp_mirror"].vertex_group = "kt_temp_halfR"
    shapeKeys["kt_temp_mirror"].value = 1
    bpy.ops.object.shape_key_add(from_mix=True)
    ob.active_shape_key.name = "kt_temp_combo"
    ob.active_shape_key.value = 1    

    for i, sk in enumerate(shapeKeys): #first loop removes trash shapekeys
        if sk.name == "kt_temp_mirror":
            ob.active_shape_key_index = i
            bpy.ops.object.shape_key_remove()
    bpy.ops.object.shape_key_remove() #don't know why I can't do this in the loop!
    
    for i, sk in enumerate(shapeKeys): 
        if sk.name == "kt_temp_combo":
            sk.name = skName
            sk.vertex_group = skVG
            ob.active_shape_key_index = i
            
def vgroupHalvesRemove(ob):
    for vg in ob.vertex_groups:
        if vg.name == "kt_temp_halfR":
            bpy.ops.object.vertex_group_set_active(group=vg.name)
            bpy.ops.object.vertex_group_remove()
    bpy.ops.object.vertex_group_remove()             

class OBJECT_OT_skSymmetrize(bpy.types.Operator):
    bl_idname = "object.sk_symmetrize"
    bl_label = "Symmetrize"
    bl_description = "Mirror vert positions from +X to -X for active shapeKey"
    bl_options = {"UNDO"}
     
    def execute(self, context):
        actOb = bpy.context.active_object
        
        vgroupHalves(actOb)
        skSymmetrize(actOb)
        vgroupHalvesRemove(actOb)
        
        return {'FINISHED'}
    
    
#--------------------- RESET NORMALS ----------------------------------
    
class OBJECT_OT_resetMeshNormals(bpy.types.Operator):
    bl_idname = "object.reset_normals"
    bl_label = "Reset Mesh Normals"
    bl_description = "Reset face normals for all or selected objects"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        
        skOb = []
        
        if selOb:
            targetOb = selOb
        else:
            targetOb = scn.objects
            
        for ob in targetOb:
            if ob.type == 'MESH':
                scn.objects.active = ob
                if bpy.ops.object.mode_set.poll():
                    bpy.ops.object.mode_set(mode="EDIT")
                    
                    #might want to store selected elements
                    
                    bpy.ops.mesh.select_all(action='SELECT') #select all
                    bpy.ops.mesh.normals_make_consistent(inside=False)
                    
                    bpy.ops.object.mode_set(mode="OBJECT")
                                         
        return {'FINISHED'}
        
    
#--------------------- SHAPEKEY SPLIT ----------------------------------

class OBJECT_OT_shapeKeySplit(bpy.types.Operator):
    bl_idname = "data.shapekey_split"
    bl_label = "Split Shapekeys"
    bl_description = "Splits shapekeys of active object into one object per shape"
    
    def execute(self, context):
        scn = bpy.context.scene
        kt = bpy.context.window_manager.katietools
        selOb = bpy.context.selected_objects
        actOb = bpy.context.active_object
        
        fixers = list(kt.cl_skFix.split(','))
        
        if kt.cl_absTrans == False:
            dimX = actOb.dimensions[0] * kt.cl_skTrans
        else:
            dimX = kt.cl_skTrans
           
        skNames = []
        dupCache = []
        trash = []   
        
        if selOb:
            if len(selOb) == 1:
                if actOb.data.shape_keys == None:
                    self.report({'INFO'}, "Active object has no shapekeys")
                else:        
                    shapeKeys = actOb.data.shape_keys.key_blocks
                    
                    for ob in scn.objects:
                        if ob.name in shapeKeys:
                            ob.name = ob.name + "_OLD"
                          
                    for sk in shapeKeys:        
                        skNames.append(sk.name)
                        bpy.ops.object.duplicate(linked=False) #TODO -- search and rename objects with same name as a shapekey
                        bpy.ops.transform.translate(value=(dimX, 0.0, 0.0))
                        dupCache.append(bpy.context.active_object)
                        
                    for ob in scn.objects:    
                        if ob in dupCache:
                            num = dupCache.index(ob)
                            ob.name = skNames[num] #rename duped objects with appropriate shapekey name
                            
                            for sk in ob.data.shape_keys.key_blocks:
                                if sk.name == ob.name or sk.name == "Basis" or sk.name in fixers: #needs the Basis shape to work
                                    sk.mute = False
                                else:
                                    sk.mute = True
                            
                            if ob.name == "Basis" or ob.name in fixers: #single out BASIS and FIX SHAPE objects
                                ob.select = True
                                trash.append(ob)
                                scn.objects.active = ob
                            else:
                                ob.select = False    
                                
                            bpy.ops.object.delete() #delete BASIS and FIX SHAPE objects
                        
                    for ob in scn.objects:        
                        if ob in dupCache:
                            ob.select = True
                            
                    scn.objects.active = bpy.context.selected_objects[0]
                    bpy.ops.data.shapekey_apply()

                    bpy.ops.transform.translate(value=((dimX * -(len(trash))), 0.0, 0.0)) #translate the left over shapes
                     
                    self.report({'INFO'}, "ShapeKeys propagated")
            else:
                self.report({'INFO'}, "One object at a time please!")
        else:
            self.report({'INFO'}, "Nothing selected")
        
        return {'FINISHED'}  
    

########NEW FILE########
__FILENAME__ = tools_names
import bpy
import os
import random
import math

#--------------------------------------------------------------------------
#----------------------------- NAMING OPERATORS ---------------------------
#--------------------------------------------------------------------------



class OBJECT_OT_renameBase(bpy.types.Operator):
    bl_idname = "object.renamer_base"
    bl_label = "Rename"
    bl_description = "Rename selected objects from input Base String"
    
    def execute (self, context):
        
        kt = bpy.context.window_manager.katietools
        selOb = bpy.context.selected_editable_objects
        for ob in selOb:
            ob.name = kt.rename_base + '.000'    
        return {'FINISHED'}    
    
        
class OBJECT_OT_selectByBase(bpy.types.Operator):
    bl_idname = "object.select_by_base"
    bl_label = "Select"
    bl_description = "Select objects with name from input Base String"
    
    def execute (self, context):
        kt = bpy.context.window_manager.katietools
        baseString = kt.rename_base
        
        for ob in context.scene.objects:
            bpy.ops.object.select_pattern(pattern=baseString,case_sensitive=False,extend=False)
              
        return {'FINISHED'}
    
    
class OBJECT_OT_addPrefix(bpy.types.Operator):
    bl_idname = "object.add_prefix"
    bl_label = "Add Prefix"
    bl_description = "Add prefix to selected objects' names"
    
    def execute (self, context):
        kt = bpy.context.window_manager.katietools
        selOb = bpy.context.selected_objects
        
        for ob in selOb:
            ob.name = kt.rename_prefix + ob.name
              
        return {'FINISHED'}
    
    
class OBJECT_OT_addSuffix(bpy.types.Operator):
    bl_idname = "object.add_suffix"
    bl_label = "Add Suffix"
    bl_description = "Add suffix to selected objects' names"
    
    def execute (self, context):
        kt = bpy.context.window_manager.katietools
        selOb = bpy.context.selected_objects
        
        for ob in selOb:
            ob.name = ob.name + kt.rename_suffix
              
        return {'FINISHED'}    
 
    
class OBJECT_OT_copyDataNames(bpy.types.Operator):
    bl_idname = "object.copy_data_names"
    bl_label = "Copy to ObData"
    bl_description = "Copy object name as data name for all or selected mesh objects"
    
    def execute (self, context):
            
        myOb = list(bpy.context.selected_objects)
        allOb = bpy.data.objects
        
        for ob in allOb:
            ob.select = True
            
        selOb = bpy.context.selected_editable_objects  
                    
        for mesh in selOb:
            if mesh.data != None:
                mesh.data.name = mesh.name #+ '_DATA'
                
        for ob in bpy.data.objects:
            ob.select = False
        
        for ob in myOb:
            ob.select = True          
              
        return {'FINISHED'}
########NEW FILE########
__FILENAME__ = tools_relationship
import bpy
import os
import random
import math

#--------------------------------------------------------------------------
#----------------------------- RELATIONSHIP OPERATORS ---------------------
#--------------------------------------------------------------------------

class OBJECT_OT_createKtGroup(bpy.types.Operator):
    bl_idname = "object.create_ktgroup"
    bl_label = "Create ktGroup"
    bl_description = "Parent selected objects to a newly created ktGroup at the cursor's location"

    def execute(self, context):
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        cursorLoc = scn.cursor_location
        
        if selOb:
            if bpy.context.active_object == None:
                bpy.context.scene.objects.active = selOb[0]
                
            actOb = bpy.context.active_object
            father = actOb.parent
            
            bpy.ops.object.add(type='EMPTY', location=cursorLoc) 
            newActOb = bpy.context.active_object
            newActOb.name = "ktGroup.000"
            newActOb.ktgroup = True
            
            for ob in selOb:
                ob.select = True
                
            bpy.ops.object.parent_set()
            
            for ob in selOb:
                ob.select = False

            if actOb.parent != None:
                newActOb.parent = father
                   
            newActOb.select = True            
        else:
            self.report({'INFO'}, "No objects selected")                            
                        
        return {'FINISHED'} # operator worked

    

class OBJECT_OT_ungroupKtGroup(bpy.types.Operator):
    bl_idname = "object.ungroup_ktgroup"
    bl_label = "Ungroup ktGroup"
    bl_description = "Clear parent for children and removes ktGroup"
        
    
    def execute(self, context):
        allOb = bpy.context.scene.objects
        selOb = bpy.context.selected_objects
        actOb = bpy.context.active_object
        
        if selOb:
            if actOb.ktgroup == True and len(actOb.children) > 0:
                father = actOb.parent
                chillin = actOb.children
                
                for ob in allOb: ob.select = False #CLEAR SELECTION
                
                for child in chillin:
                    child.select = True
                    
                bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
                
                if actOb.parent != None:
                    for child in chillin:
                        child.parent = father
                    
                for ob in allOb: ob.select = False #CLEAR SELECTION   

                actOb.select = True
                bpy.ops.object.delete()
                
                for child in chillin:
                    child.select = True
                
                allOb.active = chillin[0]
            else:
                self.report({'INFO'}, "Active Object is not a ktGroup with children")                           
                        
        return {'FINISHED'} # operator worked
    

'''class OBJECT_OT_centerToChildren(bpy.types.Operator):
    bl_idname = "object.center_to_children"
    bl_label = "Center to Children"
    bl_description = "Center parent empty to the center of it's children"

    def execute(self, context):
        allOb = bpy.context.scene.objects
        selOb = bpy.context.selected_objects
        actOb = bpy.context.active_object
        
        if selOb:
            if actOb.ktgroup == True and len(actOb.children) > 0:
                name = actOb.name
                bpy.ops.object.select_grouped()
                children = bpy.context.selected_objects
                bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
                bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")
                bpy.ops.view3D.snap_cursor_to_selected()
                actOb = bpy.context.scene.objects[name]
                for ob in allOb:
                    ob.select = False
                    actOb.select = True
                bpy.ops.view3D.snap_selected_to_cursor()
                for ob in children:
                    ob.select = True
                actOb.select = True    
                bpy.ops.object.parent_set()
                for ob in allOb:
                    ob.select = False
                    actOb.select = True
                    
            else:
                self.report({'INFO'}, "Active Object is not a ktGroup with Children")                              
                        
        return {'FINISHED'} # operator worked'''  
 
    
class OBJECT_OT_centerToCursor(bpy.types.Operator):
    bl_idname = "object.center_ktgroup"
    bl_label = "Center ktGroup to Cursor"
    bl_description = "Set ktGroup origin at the cursor's location"
    
    def execute(self, context):
        scn = bpy.context.scene
        selOb = bpy.context.selected_objects
        actOb = bpy.context.active_object
        name = actOb.name
        
        if selOb:
            if actOb.ktgroup == True:
                if actOb.parent !=None:
                    self.report({'INFO'}, "Active Object is a child")
                else:     
                    bpy.ops.object.select_grouped(type="CHILDREN")
                    children = bpy.context.selected_objects
                    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
                    
                    bpy.ops.object.create_ktgroup() #create new ktgroup with empty at cursor
                    
                    for ob in scn.objects:
                        if ob.name == name:
                            ob.select = True
                        else:
                            ob.select = False
                            
                    bpy.ops.object.delete() #delete original empty
                    scn.objects.active.name = name #rename newly created ktGroup with original name
                    
                    for ob in scn.objects:
                        if ob.name == name:
                            ob.select = True
                        else:
                            ob.select = False
                            
                    scn.objects.active = scn.objects[name]        

            else:
                self.report({'INFO'}, "Active Object is not a ktGroup")                          
                        
        return {'FINISHED'} # operator worked
        

class OBJECT_OT_duplicateKtGroup(bpy.types.Operator):
    bl_idname = "object.duplicate_ktgroup"
    bl_label = "Duplicate ktGroup"
    bl_description = "Duplicate ktGroup and children"
    
    def execute(self, context):
        allOb = bpy.context.scene.objects
        selOb = bpy.context.selected_objects
        actOb = bpy.context.active_object
        
        if selOb:
            if actOb.ktgroup == True and len(actOb.children) > 0:
                bpy.ops.object.select_grouped(extend=True,type="CHILDREN_RECURSIVE")
                newSel = bpy.context.selected_objects
                bpy.ops.object.duplicate(linked=False)
                
                actOb = bpy.context.active_object

                for ob in bpy.context.scene.objects:
                    if actOb.name != ob.name:
                        ob.select = False 
            else:
                self.report({'INFO'}, "Active Object is not a ktGroup with Children")                           
                        
        return {'FINISHED'} # operator worked


class OBJECT_OT_mergeKtGroup(bpy.types.Operator):
    bl_idname = "object.merge_ktgroup"
    bl_label = "Merge"
    bl_description = "Merge ktGroup's children into single object and remove ktGroup"
    
    def execute(self, context):
        allOb = bpy.context.scene.objects
        selOb = bpy.context.selected_objects
        actOb = bpy.context.active_object
        
        if selOb:
            if actOb.ktgroup == True and len(actOb.children) > 0:
                
                name = actOb.name
                invisOb = []
                for ob in allOb:
                    if ob.hide == True:
                        invisOb.append(ob) #add hidden objects to invisOb array
                    ob.hide = False #unhide all ohjects
                
                bpy.ops.object.select_grouped(extend=True,type="CHILDREN_RECURSIVE")
                selChildren = bpy.context.selected_objects
                
                bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
                
                meshes = []
                for child in selChildren:
                    if child.type != "MESH":
                        child.select = True
                    else:
                        child.select = False
                        meshes.append(child)
                        
                bpy.ops.object.delete()
                    
                for mesh in meshes:
                    mesh.select = True
                    
                bpy.context.scene.objects.active = meshes[0]
                bpy.ops.object.join()
                bpy.context.active_object.name = name
                bpy.context.active_object.hide = False  
                
                for ob in invisOb:
                    if ob.name != name:
                        ob.hide = True #re-hide objects previously hidden 
                  
            else:
                self.report({'INFO'}, "Active Object is not a ktGroup with Children")                           
                        
        return {'FINISHED'} # operator worked 

    
class OBJECT_OT_deleteKtGroup(bpy.types.Operator):
    bl_idname = "object.delete_ktgroup"
    bl_label = "Delete ktGroup"
    bl_description = "Delete ktGroup and its children"
    
    def execute(self, context):
        allOb = bpy.context.scene.objects
        selOb = bpy.context.selected_objects
        actOb = bpy.context.active_object
        
        if selOb:
            if actOb.ktgroup == True and len(actOb.children) > 0:
                invisOb = []
                for ob in allOb:
                    if ob.hide == True:
                        invisOb.append(ob) #add hidden objects to invisOb array
                    ob.hide = False #unhide all ohjects
                    
                bpy.ops.object.select_grouped(extend=True,type="CHILDREN_RECURSIVE")
                bpy.ops.object.delete()
                
                for ob in invisOb:
                    ob.hide = True #re-hide objects previously hidden   
            else:
                self.report({'INFO'}, "Active Object is not a ktGroup with Children")                           
                        
        return {'FINISHED'} # operator worked      



#---------- BUDDY MESHES ------- # 
       
class OBJECT_OT_combineMeshes(bpy.types.Operator):
    bl_idname = "object.combine_meshes"
    bl_label = "Combine"
    bl_description = "Joins selected mesh objects and stores originally selected meshes as vertex groups"
      
        
    def execute(self, context):
        selOb = bpy.context.selected_objects
        scn = bpy.context.scene
        
        if selOb:
            if len(selOb) > 1:
                bmOb = []
                for ob in selOb:
                    if ("-BM_" in ob.name):
                        bmOb.append(ob)
                if len(bmOb) > 0:
                    self.report({'INFO'}, "Can't combine with other Buddy Meshes")
                else:        
                    for ob in selOb:
                        if ob.type != "MESH":
                            ob.select = False
                        
                    newSelOb = bpy.context.selected_objects
                    
                    if bpy.context.active_object not in newSelOb:
                        scene.objects.active = newSelOb[0]
                        
                    actOb = scn.objects.active
                    
                    for ob in newSelOb:  
                        scn.objects.active = ob
                        mesh = ob.data
                        vert_list = []
                        
                        for v in mesh.vertices:
                            vert_list.append(v.index)   
                        
                        newVGroup = ob.vertex_groups.new(ob.name)
                        newVGroup.add(vert_list,1.0,'ADD')
                            
                    bpy.ops.object.join()
                    scn.objects.active.name = "-BM_" + actOb.name
                    
                    bmName = scn.objects.active.name
            else:
                self.report({'INFO'}, "Only 1 object selected")        
        else:
            self.report({'INFO'}, "No objects selected")
             
         
        return {'FINISHED'} # operator worked
    

class OBJECT_OT_splitPoseMesh(bpy.types.Operator):
    bl_idname = "object.split_posemesh"
    bl_label = "Split"
    bl_description = "Separates mesh based on its vertex groups"
    
    def execute(self, context):
        selOb = bpy.context.selected_objects
        scn = bpy.context.scene
        kt = bpy.context.window_manager.katietools
        
        if selOb:
            if len(selOb) > 1:
                self.report({'INFO'}, "Only works with one object selected")
            else:
                if ("-BM" in bpy.context.active_object.name):
                    bpy.context.active_object.name = "tempName"
                else:
                    self.report({'INFO'}, "No BM object selected")    
                    
                actOb = bpy.context.active_object    
        
                vgroups = actOb.vertex_groups
                
                for vg in vgroups:
                    if bpy.ops.object.mode_set.poll(): #jump to edit mode
                        bpy.ops.object.mode_set(mode="EDIT")
                        
                    bpy.ops.wm.context_set_value(data_path='tool_settings.mesh_select_mode',value='(True,False,False)')
                    bpy.ops.mesh.select_all(action='DESELECT') #deselect all
                    
                    bpy.ops.object.vertex_group_set_active(group=vg.name)
                    bpy.ops.object.vertex_group_select()
                    bpy.ops.mesh.separate(type="SELECTED")
                    
                if bpy.ops.object.mode_set.poll(): #jump to object mode
                    bpy.ops.object.mode_set(mode="OBJECT")
                
                # Delete blank object    
                for ob in scn.objects:
                    if actOb.name == ob.name:
                        ob.select = True
                    else:
                        ob.select = False
                    bpy.ops.object.delete()
                
                # Rename separated objects based on active vertex group; then remove vertex groups       
                for ob in scn.objects:    
                    if (actOb.name in ob.name):
                        ob.select = True
                    else:
                        ob.select = False      
                    
                    if ob.select == True:
                        scn.objects.active = ob
                        actVG = bpy.context.active_object.vertex_groups.active
                        ob.name = actVG.name
                        bpy.ops.object.vertex_group_remove(all=True)
        else:
            self.report({'INFO'}, "No object selected")
                        
        return {'FINISHED'} # operator worked   
########NEW FILE########
__FILENAME__ = tools_render
import bpy
import os
import random
import math

#-------------------------------------------------------
#-------------- RENDER ---------------------------------
#-------------------------------------------------------

#SNAPSHOT

class OBJECT_OT_ssAddCamera(bpy.types.Operator):
    bl_idname = "render.ss_add_camera"
    bl_label = "Add Camera Object"
    
    def execute(self, context):
        bpy.ops.object.camera_add()
        #maybe change clipping end to 10000 upon creation              
        return {'FINISHED'} 

class OBJECT_OT_ssAngleAdd(bpy.types.Operator):
    bl_idname = "render.ss_angle_add"
    bl_label = "Add Camera Angle"
    bl_description = "Add a new angle preset based on the scene camera's current position"
    
    def execute(self, context):
        scn = bpy.context.scene
        
        if scn.camera == None:
            self.report({'INFO'}, 'No camera in the scene')
        else:
            angle = scn.ss_camAngles.add()
            angNo = len(scn.ss_camAngles)
            angle.name = "ssAng.%.3d" % angNo
            angle.angleName = "Angle.%.3d" % angNo
            angle.camLoc = str(list(scn.camera.location))
            angle.camRot = str(list(scn.camera.rotation_euler))
            angle.camFL = scn.camera.data.lens
                       
        return {'FINISHED'}
    
class OBJECT_OT_ssAngleReset(bpy.types.Operator):
    bl_idname = "render.ss_angle_reset"
    bl_label = "Angle Reset"
    bl_description = "Reset camera angle based on scene camera's current position"
    
    angleN = bpy.props.IntProperty()
    
    def execute(self, context):
        scn = bpy.context.scene
        
        scn.ss_camAngles[self.angleN].camLoc = str(list(scn.camera.location))
        scn.ss_camAngles[self.angleN].camRot = str(list(scn.camera.rotation_euler))
        scn.ss_camAngles[self.angleN].camFL = scn.camera.data.lens
                       
        return {'FINISHED'}    
    
class OBJECT_OT_ssAngleRemove(bpy.types.Operator):
    bl_idname = "render.ss_angle_remove"
    bl_label = "Remove Camera Angle"
    
    angleN = bpy.props.IntProperty()
    
    def execute(self, context):
        scn = bpy.context.scene
        angRemove = scn.ss_camAngles.remove(self.angleN)
        
        #print (angleN)
                       
        return {'FINISHED'}    


class OBJECT_OT_ssAnglePreview(bpy.types.Operator):
    bl_idname = "render.ss_angle_preview"
    bl_label = "Preview Camera Angle"
    
    angleN = bpy.props.IntProperty()
    
    def execute(self, context):
        scn = bpy.context.scene
        
        scn.camera.location = eval(scn.ss_camAngles[self.angleN].camLoc)
        scn.camera.rotation_euler = eval(scn.ss_camAngles[self.angleN].camRot)
        scn.camera.data.lens = scn.ss_camAngles[self.angleN].camFL
        
        view = None
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                view = area.spaces.active.region_3d.view_perspective
                
        if view != 'CAMERA':        
            bpy.ops.view3d.viewnumpad(type='CAMERA')
                       
        return {'FINISHED'}
    
class OBJECT_OT_ssSetScaler(bpy.types.Operator):
    bl_idname = "render.ss_set_scaler"
    bl_label = "Set SS Scaler"
    
    def execute(self, context):
        scn = bpy.context.scene
        ktScn = scn.kt_scene_props

        focusOb = None      
        if len(bpy.context.selected_objects) != 1:
            self.report({'INFO'}, 'Only one object can be the focus object')
        else:    
            for ob in scn.objects:
                if ob.select == True:
                    focusOb = ob
                    
            ktScn.ssScaler = str(focusOb.name)
                       
        return {'FINISHED'}    
    
    
class OBJECT_OT_ssSetSpinners(bpy.types.Operator):
    bl_idname = "render.ss_set_spinners"
    bl_label = "Set SS Spinners"
    
    def execute(self, context):
        scn = bpy.context.scene
        ktScn = scn.kt_scene_props

        spinnerNames = []       
        
        for ob in scn.objects:
            if ob.select == True:
                spinnerNames.append(ob.name)
                
        ktScn.ssSpinners = str(spinnerNames)
                       
        return {'FINISHED'}
    

class OBJECT_OT_guessAssetName(bpy.types.Operator):
    bl_idname = "render.ss_guess_name"
    bl_label = "Guess Asset Name"
    bl_description = "Guess the desired asset's name based on file name"
    
    def execute(self, context):
        scn = bpy.context.scene
        ktScn = scn.kt_scene_props
        
        path = bpy.data.filepath
        fileName = os.path.basename(path)
        name = fileName.split('.')[0]
        
        if "_" in name:
            asset = name.split('_')[0]
        else:
            asset = "assetName"    
        
        ktScn.ssAssetName = asset
                       
        return {'FINISHED'}
    
class OBJECT_OT_guessAssetVersion(bpy.types.Operator):
    bl_idname = "render.ss_guess_version"
    bl_label = "Guess Asset Version"
    bl_description = "Guess the desired asset's version based on file name"
    
    def execute(self, context):
        scn = bpy.context.scene
        ktScn = scn.kt_scene_props
        
        path = bpy.data.filepath
        fileName = os.path.basename(path)
        name = fileName.split('.')[0]
        
        if "_" in name:
            version = name.split('_')[1]
        else:
            version = "v01"    
        
        ktScn.ssAssetVersion = version
                       
        return {'FINISHED'}
    

class OBJECT_OT_ssFrameRatio(bpy.types.Operator):
    bl_idname = "render.ss_frame_ratio"
    bl_label = "Set Render Frame Ratio"
    
    ratio = bpy.props.StringProperty()
    
    def execute(self, context):
        scn = bpy.context.scene
        ktScn = scn.kt_scene_props
        
        if self.ratio == 'WIDE':
            scn.render.resolution_x = 1920
            scn.render.resolution_y = 1080
            
        if self.ratio == 'SQUARE':
            scn.render.resolution_x = 1080
            scn.render.resolution_y = 1080
                       
        return {'FINISHED'}   

def getBoundBoxDimensions(focusOb):
    scn = bpy.context.scene
    selOb = []
    tempNameB = 'kysk'
    bbName = 'ss_boundBox'
    #determine whether the focus object has children or not   
    for ob in scn.objects:
            ob.select = False
    
    '''if len(focusOb.children) == 0:
        dim = max(focusOb.dimensions)
    else:'''
        
    focusOb.select = True
    scn.objects.active = focusOb
    bpy.ops.object.select_grouped(extend=True,type="CHILDREN_RECURSIVE")
    
    for ob in bpy.context.selected_objects:
        selOb.append(ob)

    if selOb == []:
        print ("NO FOCUS OBJECT DESIGNATED")
    else:    
        ###### START BOUND BOX GENERATION
        #duplicate selected objects and convert to mesh to avoid modifier trouble
        scn.objects.active = selOb[0] #make sure a member of selOb is the active object before this starts
        bpy.ops.object.duplicate(linked=False)
        dupSel = bpy.context.selected_objects #define dupSel list
        bpy.ops.object.convert(target='MESH', keep_original=False)
    
        for ob in dupSel: #single out objects WITHOUT dimensions
            if ob.type == 'MESH' or ob.type=='CURVE' or ob.type=='SURFACE' or ob.type=='META' or ob.type=='FONT':
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY',center='BOUNDS')   
                
                cubeA = bpy.ops.mesh.primitive_cube_add()
                actOb = scn.objects.active #redefine active object variable
                actOb.name = tempNameB + ob.name
                actOb.dimensions = ob.dimensions
                actOb.location = ob.location
                
            elif ob.ktgroup == True:
                continue   
                
            else:
                cubeA = bpy.ops.mesh.primitive_cube_add()
                actOb = scn.objects.active #redefine active object variable
                actOb.name = tempNameB + ob.name
                actOb.scale = ob.scale
                actOb.location = ob.location
                
        for ob in scn.objects:
            if tempNameB in ob.name:
                ob.select = True
            else:
                ob.select = False
        if len(bpy.context.selected_objects) > 1:        
            bpy.ops.object.join() #combine duplicates into a temp object
            
        scn.objects.active.name = bbName    
        
        # SINGLE OUT AND REMOVE FIRST SET OF CUBES -----------------
        for ob in scn.objects:
            if ob in dupSel or tempNameB in ob.name:
                ob.select = True
            else:
                ob.select = False
                
        bpy.ops.object.delete() #delete first set of cubes
        
        # ------------------------------------------------------------
        bb = scn.objects[bbName]
        dim = max(bb.dimensions)
        wmtx =  bb.matrix_world
        worldVerts = [(wmtx * vertex.co) for vertex in bb.data.vertices]
        vertsZ = []
        for v in worldVerts:
            vertsZ.append(v[2])
            
        minZ = min(vertsZ)
            
        scn.objects.active = bb
        scn.objects.active.select = True    
        bpy.ops.object.delete()
            
    return dim, minZ


def spinnerSetup(spinnerNames):
    scn = bpy.context.scene
    spinnerOb = []
    
    for ob in scn.objects:
        if ob.name in spinnerNames:
            spinnerOb.append(ob)
        if ob.name == "ss_spinner.001":
            ob.select = True
            scn.objects.active = ob
        else:
            ob.select = False #at this point only the original spinner ctrl is selected and active
                 
    for ob in spinnerOb:
        bpy.ops.object.duplicate(linked=False)
        actOb = scn.objects.active
        actOb.name = "ss_spinner_" + ob.name
        actOb.location = ob.location
        
        ob.select = True
        actOb.select = True
        
        bpy.ops.object.parent_set(type='OBJECT',keep_transform=True)
        
        ob.select = False    

    
class OBJECT_OT_ssAngleDoRender(bpy.types.Operator):
    bl_idname = "render.ss_do_render"
    bl_label = "Render Snapshot"
    bl_description = "Render enabled Snapshot camera angles"
           
    def append(self):
        blend = 'ss_scene_A.blend'
        path = bpy.utils.script_paths('addons/katietools/snapshot')
        pathStr = ''.join(path) #convert list object to string
        filepath = str(pathStr + '/' + blend)
        
        with bpy.data.libraries.load(filepath) as (data_from, data_to):
            data_to.scenes = ["kt_ssSetup"]              
    
    def execute(self, context):
        scn = bpy.context.scene
        kt = bpy.context.window_manager.katietools
        ktScn = scn.kt_scene_props
        
        #-------SPINNER STRING CHECK-------------------------------------------
        if "[" not in ktScn.ssSpinners:
            self.report({'INFO'}, 'Spinners must be a list of objects')
        else:
            spinnerNames = eval(ktScn.ssSpinners)
            
            #make sure all spinner objects are visible lest parenting will fail
            for ob in scn.objects:
                if ob.name in spinnerNames:
                    ob.hide = False
            
            #-------SCALER CHECK-------------------------------------------
            if ktScn.ssScaler not in scn.objects:
                self.report({'INFO'}, 'Scaler is not an object')
            else:  
                spinTest = True
                for s in spinnerNames:
                    if s not in scn.objects:
                        spinTest = False
                
                #-------SPINNER OB CHECK-------------------------------------------        
                if spinTest == False:
                    self.report({'INFO'}, 'One or more spinners are not objects')           
                else:#all spinner objects exist in the scene, therefore continue
                    
                    #-------OUTPUT FORMAT CHECK-------------------------------------------
                    if scn.render.image_settings.file_format != 'JPEG' and scn.render.image_settings.file_format != 'PNG':
                        self.report({'INFO'}, 'Please use JPEG or PNG image format for render output')
                    else:    
                        print ('file format is good to go')
                        #-------FRAME RATIO CHECK-------------------------------------------    
                        scnRatio = scn.render.resolution_x / scn.render.resolution_y
                        if (scnRatio == (16/9)) or (scnRatio == (1)):
                            scalerOb = scn.objects[ktScn.ssScaler]
                            selObToLink = []
                            origScnName = scn.name
                            origScn = bpy.data.scenes[origScnName]
                            scnSS = 'kt_ssSetup'
                            
                            ssDim = getBoundBoxDimensions(scalerOb)
                            #self.report({'INFO'}, str(ssDim))
                            
                            self.append() #APPEND THE SNAPSHOT SCENE ------------------------------------
                            
                            bpy.ops.object.select_all(action='DESELECT')
                                    
                            for s in spinnerNames:
                                scn.objects[s].select = True
                                scn.objects.active = scn.objects[s]
                                bpy.ops.object.select_grouped(extend=True,type="CHILDREN_RECURSIVE")
                            
                            bpy.ops.object.make_links_scene(scene=scnSS)#link selection to ss scene
                            
                            bpy.context.screen.scene = bpy.data.scenes[scnSS] #change 'active' scene to Snapshot Scene
                            
                            scn = bpy.context.scene # REDEFINE 'SCN'
                            ground = scn.objects["ss_groundPlane"]
                            
                            origCamAngles = origScn.ss_camAngles
                            
                            for i, cam in enumerate(origScn.ss_camAngles): #recreate camera angles from original scene
                                angle = scn.ss_camAngles.add()
                                angNo = len(scn.ss_camAngles)
                                angle.name = origCamAngles[i].name
                                angle.angleName = origCamAngles[i].angleName
                                angle.camLoc = origCamAngles[i].camLoc
                                angle.camRot = origCamAngles[i].camRot
                                angle.camFL = origCamAngles[i].camFL 
                              
                            for ob in scn.objects:
                                if 'ss_scaler' in ob.name: #get scaler object from appended scene
                                    scalerOb = ob
                                if 'ss_cam' in ob.name: #get ss camera
                                    ssCam = ob
                                    
                            multV = ssDim[0]/scalerOb.dimensions[0]
                            
                            #------------------COPY A BUNCH OF SETTINGS TO SNAPSHOT SCENE--------------------
                            scalerOb.dimensions = scalerOb.dimensions * multV #match scale
                            scalerOb.location[2] = ssDim[1] #move scaler to the bottom of focus object
                            ssCam.data.clip_start = ssCam.data.clip_start * multV
                            ssCam.data.clip_end = ssCam.data.clip_end * multV
                            ground.scale = ground.scale * multV
                            ground.location[2] = ssDim[1]
                            scn.render.resolution_x = origScn.render.resolution_x
                            scn.render.resolution_y = origScn.render.resolution_y
                            scn.render.resolution_percentage = origScn.render.resolution_percentage
                            scn.frame_current = origScn.frame_current
                            origFF = origScn.render.image_settings.file_format
                            origCM = origScn.render.image_settings.color_mode
                            origQ = origScn.render.image_settings.quality
                            scn.frame_start = 1
                            scn.frame_end = origScn.kt_scene_props.ssAnimRange
                            scn.kt_scene_props.ssRelative = origScn.kt_scene_props.ssRelative
                            
                            if kt.ren_type == "Internal":
                                if scn.render.engine != "BLENDER_RENDER":
                                    scn.render.engine = "BLENDER_RENDER"
                                for ob in scn.objects:
                                    if 'ss_c_' in ob.name:
                                        ob.hide_render = True
                                    if 'ss_bi_' in ob.name:
                                        ob.hide_render = False    
                            elif kt.ren_type == "Cycles":
                                if scn.render.engine != "CYCLES":
                                    scn.render.engine = "CYCLES"
                                for ob in scn.objects:
                                    if 'ss_bi_' in ob.name:
                                        ob.hide_render = True
                                    if 'ss_c_' in ob.name:
                                        ob.hide_render = False
                                        
                            if scnRatio == (1):
                                for ob in scn.objects:
                                    if 'ss_text' in ob.name:
                                        ob.select = True
                                    else:
                                        ob.select = False
                                txtGrpScale = round(scn.objects["ss_text_GRP"].scale[0], 2)
                                zTrans = (-6.55 * txtGrpScale)                  
                                bpy.ops.transform.translate(value=(0,0,zTrans)) #position text overlay objects for square ratio 
                            
                            spinnerSetup(spinnerNames)
                            
                            origFR = origScn.kt_scene_props.ssAnimRange      
                            for ob in scn.objects:
                                if 'ss_spinner' in ob.name:
                                    for f in ob.animation_data.action.fcurves:
                                        for k in f.keyframe_points:
                                            if k.co[0] == 101:
                                                k.co[0] = (origFR + 1)
                                               
                            if ktScn.ssRelative == False:
                                scalerOb.constraints['ss_con_trackTo'].mute = True
                            else:
                                scalerOb.constraints['ss_con_trackTo'].mute = False
                                
                            if ktScn.ssRenType == "Engine" and ktScn.ssGround == True:
                                ground.hide_render = False
                            else:
                                ground.hide_render = True          
                                
                            renders = []
                            
                            #--------------------LOOP THOUGH AND RENDER EACH CAM ANGLE-----------------------------
                            for i, cam in enumerate(scn.ss_camAngles):  #loop through current scene's camAngles
                                cam.toggle_still = origScn.ss_camAngles[i-1].toggle_still
                                cam.toggle_turn = origScn.ss_camAngles[i-1].toggle_turn
                                scn.objects['ss_text_A'].data.body = ktScn.ssAssetName + "_" + ktScn.ssAssetVersion + "_" + "%03d"%ktScn.ssDeviation
                                scn.objects['ss_text_B'].data.body = scn.ss_camAngles[i-1].angleName
                                scn.objects['ss_text_C'].data.body = 'Kent Trammell'
                                bpy.ops.render.ss_angle_preview(angleN=i-1)
                                
                                if cam.toggle_still == True:
                                    scn.frame_current = 1        
                                    scn.render.image_settings.file_format = origFF  
                                    scn.render.image_settings.color_mode = origCM
                                    scn.render.image_settings.quality = origQ
                                    fileName = ktScn.ssAssetName + "_" + ktScn.ssAssetVersion + "_" + "%03d"%ktScn.ssDeviation + "_" + scn.ss_camAngles[i-1].angleName + scn.render.file_extension
                                    filePath = origScn.render.filepath + fileName
                                    scn.render.filepath = filePath
                                    
                                    if ktScn.ssRenType == "OpenGL":
                                        bpy.ops.render.opengl(animation=False, write_still=True)
                                    else:    
                                        bpy.ops.render.render(animation=False, write_still=True)
                                    renders.append(filePath)
                                                                    
                                if cam.toggle_turn == True:
                                    scn.render.image_settings.file_format = "FFMPEG"
                                    scn.render.ffmpeg.format = 'QUICKTIME'
                                    scn.render.ffmpeg.codec = 'H264'
                                    scn.render.ffmpeg.video_bitrate = 9000
                                    scn.render.ffmpeg.minrate = 9000
                                    scn.render.ffmpeg.maxrate = 12000
                                    scn.render.ffmpeg.buffersize = 2500
                                    scn.render.ffmpeg.use_lossless_output = True
                                    fileName = ktScn.ssAssetName + "_" + ktScn.ssAssetVersion + "_" + "%03d"%ktScn.ssDeviation + "_" + scn.ss_camAngles[i-1].angleName + ".mov"
                                    filePath = origScn.render.filepath + fileName
                                    scn.render.filepath = filePath
                                    
                                    if ktScn.ssRenType == "OpenGL":
                                        bpy.ops.render.opengl(animation=True)
                                    else:    
                                        bpy.ops.render.render(animation=True)
                                    renders.append(filePath)                   
                                       
                            bpy.ops.scene.delete()    
                            bpy.context.screen.scene = origScn #change 'active' scene to original
                            bpy.ops.data.clean_data(key='ss_') #clean remaining data from snapshot scene
                            
                            if len(renders) > 0:
                                origScn.kt_scene_props.ssDeviation = origScn.kt_scene_props.ssDeviation + 1    
                                self.report({'INFO'}, str(len(renders)) + ' Snapshot angles finished:  ' + renders[0])
                            else:
                                self.report({'INFO'}, 'No Snapshots angles enabled for rendering')    
                        
                        else:
                            self.report({'INFO'}, 'Please use a wide or square frame radio')  
                            
        return {'FINISHED'}    
    

#INTERNAL TOOLS

class OBJECT_OT_engineSetBI(bpy.types.Operator):
    bl_idname = "render.engine_set_bi"
    bl_label = "Activate Internal"
    bl_description = "Activates BLENDER RENDER renderengine"
    
    def execute(self, context):
        bpy.context.scene.render.engine = "BLENDER_RENDER"
                       
        return {'FINISHED'}


#CYCLES TOOLS
    
class OBJECT_OT_engineSetC(bpy.types.Operator):
    bl_idname = "render.engine_set_c"
    bl_label = "Activate Cycles"
    bl_description = "Activates CYCLES render engine"
    
    def execute(self, context):
        bpy.context.scene.render.engine = "CYCLES"
                       
        return {'FINISHED'}   

    
class OBJECT_OT_cyclesMaterialFoundation(bpy.types.Operator):
    bl_idname = "matlib.c_create_mat"
    bl_label = "Create Material"
    bl_description = "Add material foundation to selected objects"
    
    def execute(self, context):
        selOb = bpy.context.selected_objects
        kt = bpy.context.window_manager.katietools

        matName = "kt" + str(kt.matlib_type)
        
        if kt.matlib_type == "Glossy":
            diffColor = kt.matlib_color
            glossColor = (1,1,1,1)
            mixA_col1 = (0.03,0.03,0.03,1)
            mixA_col2 = (0.7,0.7,0.7,1)
            mixB_col1 = (0.2,0.2,0.2,1)
            mixB_col2 = (0.1,0.1,0.1,1)
            rampPos1 = 0.67
        elif kt.matlib_type == "Chrome":
            diffColor = (0,0,0,1)
            glossColor = kt.matlib_color
            mixA_col1 = (0.5,0.5,0.5,1)
            mixA_col2 = (1,1,1,1)
            mixB_col1 = (.05,.05,.05,1)
            mixB_col2 = (.001,.001,.001,1)
            rampPos1 = 0   
        
        if matName in bpy.data.materials:
            dupMat = bpy.data.materials[matName]
            dupMat.name = matName + ".000"
                
        mat = bpy.data.materials.new(matName)
        mat.use_nodes = True
        
        tree = bpy.data.materials[matName].node_tree
        links = tree.links
        
        output = tree.nodes['Material Output']
        
        diffuse = tree.nodes['Diffuse BSDF']
        diffuse.inputs[0].default_value = diffColor
        diffuse.location = -235,300
        
        glossy = tree.nodes.new('BSDF_GLOSSY')
        glossy.inputs[0].default_value = glossColor
        glossy.location = -235,150
        
        mixShader = tree.nodes.new('MIX_SHADER')
        mixShader.location = 40,340
        
        layWeight = tree.nodes.new('LAYER_WEIGHT')
        layWeight.location = -1080,300
        
        ramp = tree.nodes.new('VALTORGB')
        ramp.location = -800,300
        ramp.color_ramp.interpolation = 'B_SPLINE'
        elements = ramp.color_ramp.elements
        elements[0].position = rampPos1
        
        mixA = tree.nodes.new('MIX_RGB')
        mixA.location = -435,475
        mixA.inputs[1].default_value = mixA_col1
        mixA.inputs[2].default_value = mixA_col2
        
        mixB = tree.nodes.new('MIX_RGB')
        mixB.location = -435,150
        mixB.inputs[1].default_value = mixB_col1
        mixB.inputs[2].default_value = mixB_col2
        
        links.new(layWeight.outputs[1],ramp.inputs[0])
        links.new(ramp.outputs[0],mixA.inputs[0])
        links.new(ramp.outputs[0],mixB.inputs[0])
        links.new(mixA.outputs[0],mixShader.inputs[0])
        links.new(mixB.outputs[0],glossy.inputs[1])
        links.new(diffuse.outputs[0],mixShader.inputs[1])
        links.new(glossy.outputs[0],mixShader.inputs[2])
        links.new(mixShader.outputs[0],output.inputs[0])
        
        for ob in selOb:
            ob.active_material = bpy.data.materials[matName]
            
                       
        return {'FINISHED'}     

class OBJECT_OT_renRvSet(bpy.types.Operator):
    bl_idname = "object.ren_rv_set"
    bl_label = "Set RV"
    bl_description = "Sets ray visibility for selected objects"
    
    def execute(self, context):
        kt = bpy.context.window_manager.katietools
        selOb = bpy.context.selected_objects
        engine = bpy.context.scene.render.engine
        
        if selOb:
            for ob in selOb:
                if kt.rvCam == True:
                    ob.cycles_visibility.camera = True
                else:
                    ob.cycles_visibility.camera = False
                if kt.rvDif == True:
                    ob.cycles_visibility.diffuse = True
                else:
                    ob.cycles_visibility.diffuse = False
                if kt.rvGlo == True:
                    ob.cycles_visibility.glossy = True
                else:
                    ob.cycles_visibility.glossy = False
                if kt.rvTra == True:
                    ob.cycles_visibility.transmission = True
                else:
                    ob.cycles_visibility.transmission = False
                if kt.rvSha == True:
                    ob.cycles_visibility.shadow = True
                else:
                    ob.cycles_visibility.shadow = False
        else:
            self.report({'INFO'}, "Nothing selected")                          
                    
        # Silly way to force all windows to refresh
        bpy.context.scene.frame_current = bpy.context.scene.frame_current             
        
        return {'FINISHED'}
    
class OBJECT_OT_rvSelCam(bpy.types.Operator):
    bl_idname = "object.rv_sel_cam"
    bl_label = "RV Select Camera"
    bl_description = "Select objects with CAMERA ray visibility disabled"
    
    def execute(self, context):
        scnOb = bpy.context.scene.objects
        for ob in scnOb:
            ob.select = False
            if ob.cycles_visibility.camera == False:
                ob.select = True
        if bpy.context.selected_objects:                
            scnOb.active = bpy.context.selected_objects[0]
        self.report({'INFO'}, str(len(bpy.context.selected_objects)) + " objects selected")
        return {'FINISHED'}
    
class OBJECT_OT_rvSelDif(bpy.types.Operator):
    bl_idname = "object.rv_sel_dif"
    bl_label = "RV Select Diffuse"
    bl_description = "Select objects with DIFFUSE ray visibility disabled"
    
    def execute(self, context):
        scnOb = bpy.context.scene.objects
        for ob in scnOb:
            ob.select = False
            if ob.cycles_visibility.diffuse == False:
                ob.select = True
        if bpy.context.selected_objects:              
            scnOb.active = bpy.context.selected_objects[0]
        self.report({'INFO'}, str(len(bpy.context.selected_objects)) + " objects selected")
        return {'FINISHED'}
    
class OBJECT_OT_rvSelGlo(bpy.types.Operator):
    bl_idname = "object.rv_sel_glo"
    bl_label = "RV Select Glossy"
    bl_description = "Select objects with GLOSSY ray visibility disabled"
    
    def execute(self, context):
        scnOb = bpy.context.scene.objects
        for ob in scnOb:
            ob.select = False
            if ob.cycles_visibility.glossy == False:
                ob.select = True
        if bpy.context.selected_objects:              
            scnOb.active = bpy.context.selected_objects[0]
        self.report({'INFO'}, str(len(bpy.context.selected_objects)) + " objects selected")
        return {'FINISHED'}
    
class OBJECT_OT_rvSelTra(bpy.types.Operator):
    bl_idname = "object.rv_sel_tra"
    bl_label = "RV Select Transmission"
    bl_description = "Select objects with TRANSMISSION ray visibility disabled"
    
    def execute(self, context):
        scnOb = bpy.context.scene.objects
        for ob in scnOb:
            ob.select = False
            if ob.cycles_visibility.transmission == False:
                ob.select = True
        if bpy.context.selected_objects:              
            scnOb.active = bpy.context.selected_objects[0]
        self.report({'INFO'}, str(len(bpy.context.selected_objects)) + " objects selected")
        return {'FINISHED'}

class OBJECT_OT_rvSelSha(bpy.types.Operator):
    bl_idname = "object.rv_sel_sha"
    bl_label = "RV Select Shadow"
    bl_description = "Select objects with SHADOW ray visibility disabled"
    
    def execute(self, context):
        scnOb = bpy.context.scene.objects
        for ob in scnOb:
            ob.select = False
            if ob.cycles_visibility.shadow == False:
                ob.select = True
        if bpy.context.selected_objects:              
            scnOb.active = bpy.context.selected_objects[0]
        self.report({'INFO'}, str(len(bpy.context.selected_objects)) + " objects selected")
        return {'FINISHED'}     
########NEW FILE########
__FILENAME__ = tools_sculpt
import bpy
import os
import random
import math

#--------------------------------------------------------------------------
#----------------------------- SCULPT OPERATORS -------------------------
#--------------------------------------------------------------------------

def lockAxis(axis):
    scn = bpy.context.scene
    sculpt = scn.tool_settings.sculpt
    
    if axis == 'x':
        sculpt.lock_x = True
    elif axis == 'y':
        sculpt.lock_y = True
    elif axis == 'z':
        sculpt.lock_z = True     

class SCULPT_lockX(bpy.types.Operator):
    bl_idname = "sculpt.lock_axis_x"
    bl_label = "Lock X Axis"
    bl_description = "Lock manipulation in the X axis"
           
    def execute(self, context):
        lockAxis('x')
                        
        return {'FINISHED'}
    
########NEW FILE########
__FILENAME__ = quick_edit_mode
import bpy
import os
from bpy import context
 

# creates a menu for edit mode tools         
class QuickMeshTools(bpy.types.Menu):
    bl_label = "Quick Mesh Tools"
    bl_idname = "mesh.tools_menu"
       
    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_REGION_WIN'
        
        layout.operator("gpencil.surfsk_add_surface", 'Add BSurface', icon='OUTLINER_OB_SURFACE')
        layout.operator("mesh.bridge_edge_loops")
                
        layout.separator()
        
        layout.operator("mesh.bevel")
        layout.operator("mesh.inset").use_boundary=False
        layout.operator("mesh.subdivide")
        
        layout.separator()
        
        layout.operator("mesh.knife_tool", icon='SCULPTMODE_HLT')
        layout.operator("mesh.vert_connect")
        
        layout.separator()
        
        layout.operator("mesh.vertices_smooth")    
        
        layout.separator()

        layout.operator("mesh.set_object_origin", "Origin to Selection")

        layout.operator("object.mesh_halve", "Halve mesh")

        layout.separator()
        
        layout.operator("object.add_mirror", icon='MOD_MIRROR')  
        layout.operator("object.add_subsurf", 'Add Subsurf', icon='MOD_SUBSURF')




### ------------ New hotkeys and registration ------------ ###

# addon_keymaps = []

def register():
    #register the new menus
    bpy.utils.register_class(QuickMeshTools)
     
    
    # wm = bpy.context.window_manager
    
    # # creatue the edit mode menu hotkey
    # km = wm.keyconfigs.addon.keymaps.new(name='Mesh')
    # kmi = km.keymap_items.new('wm.call_menu', 'Q', 'PRESS')
    # kmi.properties.name = 'mesh.tools_menu'

    # addon_keymaps.append(km)

def unregister():
    #unregister the new menus
    bpy.utils.unregister_class(QuickMeshTools)
        
    
    # # remove keymaps when add-on is deactivated
    # wm = bpy.context.window_manager
    # for km in addon_keymaps:
    #     wm.keyconfigs.addon.keymaps.remove(km)
    # del addon_keymaps[:]


if __name__ == "__main__":
    register()
    
    
       
########NEW FILE########
__FILENAME__ = quick_mode_switch
import bpy 
from bpy import context


# Create the operator that sets the mode
class SetMode(bpy.types.Operator):
    bl_label = "Set Mode"
    bl_idname = "object.working_mode"
    
    setMode = bpy.props.StringProperty()
    
    def execute(self, context):
        bpy.ops.object.mode_set(mode=self.setMode)

        return {"FINISHED"}


# adds a Mode switch menu
class ModeSwitch(bpy.types.Menu):
    bl_label = "Quick Mode Switch Menu"
    bl_idname = "mode.switch_menu"
    
    @classmethod
    def poll(cls, context):
        if len(context.selected_objects) > 0:
            return True
        return False

    def draw(self, context):
        layout = self.layout  

        mode = bpy.context.object.mode
        
        # check the current mode and only display the relavent modes, e.g. don't show current mode              
        if mode == 'EDIT' or mode == 'SCULPT' or mode == 'TEXTURE_PAINT' or mode == 'VERTEX_PAINT' or mode == 'WEIGHT_PAINT':
            objectMode = layout.operator("object.working_mode", "Object Mode", icon="OBJECT_DATAMODE")
            objectMode.setMode = 'OBJECT'  
        
        if mode == 'OBJECT' or mode == 'SCULPT' or mode == 'TEXTURE_PAINT' or mode == 'VERTEX_PAINT' or mode == 'WEIGHT_PAINT':
            editMode = layout.operator("object.working_mode", "Edit Mode", icon="EDITMODE_HLT")
            editMode.setMode = 'EDIT'
        
        if mode == 'EDIT' or mode == 'OBJECT' or mode == 'TEXTURE_PAINT' or mode == 'VERTEX_PAINT' or mode == 'WEIGHT_PAINT':
            sculptMode = layout.operator("object.working_mode", "Sculpt Mode", icon="SCULPTMODE_HLT"    )
            sculptMode.setMode = 'SCULPT'
        
        if mode == 'EDIT' or mode == 'OBJECT' or mode == 'SCULPT' or mode == 'TEXTURE_PAINT' or mode == 'WEIGHT_PAINT':
            sculptMode = layout.operator("object.working_mode", "Vertex Paint", icon="VPAINT_HLT"    )
            sculptMode.setMode = 'VERTEX_PAINT'

        if mode == 'EDIT' or mode == 'OBJECT' or mode == 'SCULPT' or mode == 'TEXTURE_PAINT' or mode == 'VERTEX_PAINT':
            sculptMode = layout.operator("object.working_mode", "Weight Paint", icon="WPAINT_HLT"    )
            sculptMode.setMode = 'WEIGHT_PAINT'

        if mode == 'EDIT' or mode == 'OBJECT' or mode == 'SCULPT' or mode == 'VERTEX_PAINT' or mode == 'WEIGHT_PAINT':
            sculptMode = layout.operator("object.working_mode", "Texture Paint", icon="TPAINT_HLT"    )
            sculptMode.setMode = 'TEXTURE_PAINT'


def register():
    bpy.utils.register_class(ModeSwitch)
    bpy.utils.register_class(SetMode)

    
def unregister():
    bpy.utils.unregister_class(ModeSwitch)
    bpy.utils.unregister_class(SetMode)

    
if __name__ == "__main__":
    register()
########NEW FILE########
__FILENAME__ = quick_object_mode
import bpy
import os
from bpy import context

# adds an object mode menu 
class QuickObjectTools(bpy.types.Menu):
    bl_label = "Quick Object Tools"
    bl_idname = "object.tools_menu"
       
    def draw(self, context):
        layout = self.layout
        
        layout.operator("object.add_subsurf", 'Add Subsurf', icon='MOD_SUBSURF')
        layout.operator("object.apply_subsurf", 'Apply Subsurf')
        
        layout.separator()
        
        layout.menu(SmartModifiers.bl_idname, "Add Smart Modifier", icon='MODIFIER')

        layout.operator_menu_enum("object.modifier_add", "type") 
        layout.operator("object.apply_modifiers")
        layout.operator("object.modifier_remove_all", "Remove All Modifiers")
        
        layout.separator()

        layout.operator("object.mesh_halve", "Halve and Mirror")

        layout.separator() 
                
        layout.operator_menu_enum("object.origin_set", "type")


class SmartModifiers(bpy.types.Menu):
    bl_idname = "object.smart_mod"
    bl_label = "Smart Modifiers"

    def draw (self, context):
        layout = self.layout
        layout.operator("object.empty_add_unactive", "Add Target", icon='CURSOR')

        layout.separator()

        layout.operator("object.add_array", "Array", icon='MOD_ARRAY')
        layout.operator("object.add_boolean", "Boolean", icon='MOD_BOOLEAN')
        layout.operator("object.add_cast", "Cast", icon='MOD_CAST')
        layout.operator("object.add_mirror", "Mirror", icon='MOD_MIRROR')
        layout.operator("object.add_lattice", "Lattice", icon='MOD_LATTICE')
        layout.operator("object.add_screw", "Screw", icon='MOD_SCREW')


class QuickObjectOptions(bpy.types.Menu):
    bl_idname = "object.display_options"
    bl_label = "Quick Object Options"

    def draw(self, context):

        mode = bpy.context.object.mode

        layout = self.layout
        layout.operator("object.double_sided")
        layout.operator("object.all_edges_wire")

        layout.separator()

        if mode == 'OBJECT' or mode == 'SCULPT':
            layout.operator("object.shade_smooth", icon='SOLID')
            layout.operator("object.shade_flat", icon='MESH_UVSPHERE')
        elif mode == 'EDIT':
            layout.operator("mesh.faces_shade_smooth", icon='SOLID')
            layout.operator("mesh.faces_shade_flat", icon='MESH_UVSPHERE')            

class QuickPETObjects(bpy.types.Menu):
    bl_label = "Quick Proportional Editing Tool For Objects"
    bl_idname = "object.quick_pet_menu"

    def draw(self, context):
        layout = self.layout

        pet = context.scene.tool_settings.use_proportional_edit_objects

        if pet:
            layout.operator("object.pet", "Disable PET")
        else:
            layout.oeprator("object.pet", "Enable Pet")

        layout.separator()

        layout.label("Brush Falloff")
        layout.operator("brush.curve_preset", text="Smooth", icon='SMOOTHCURVE').shape = 'SMOOTH'
        layout.operator("brush.curve_preset", text="Round", icon='SPHERECURVE').shape = 'ROUND'
        layout.operator("brush.curve_preset", text="Root", icon='ROOTCURVE').shape = 'ROOT'
        layout.operator("brush.curve_preset", text="Sharp", icon='SHARPCURVE').shape = 'SHARP'
        layout.operator("brush.curve_preset", text="Line", icon='LINCURVE').shape = 'LINE'
        layout.operator("brush.curve_preset", text="Max", icon='NOCURVE').shape = 'MAX'

def register():
    bpy.utils.register_module(__name__)  

def unregister():
    bpy.utils.unregister_module(__name__)
        

if __name__ == "__main__":
    register()   
########NEW FILE########
__FILENAME__ = quick_operators
import bpy
from bpy import ops
from bpy.props import BoolProperty


### ----------------------- Convienence variables ----------------------- ###

applyModifier = ops.object.modifier_apply


### ----------------------- Object Operators ----------------------- ###


################################################### 
# Add empty at cursor, making it inactively selected. Also assign empty to modifiers if necessary.   
################################################### 

class addTarget(bpy.types.Operator):
    """Add an inactive, selected Empty Object as a modifier target"""
    bl_label = "Add an unactive Empty Object"""
    bl_idname = "object.empty_add_unactive"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if len(context.selected_objects) > 0:
            return True
        return False

    def execute(self, context):
        scene = context.scene
        activeObj = context.active_object
        currentObj = activeObj
        selected = context.selected_objects

        
        for obj in selected:
            if obj.type == 'EMPTY':
                break
            elif obj.type != 'EMPTY':
                ops.object.empty_add(type='PLAIN_AXES')
                for obj in selected:
                    obj.select = True
                scene.objects.active = activeObj
                selected = context.selected_objects
           
        for obj in selected:
            for mod in obj.modifiers:
                modifier = mod.type
                assignTarget(modifier)
                if assignTarget(modifier) is True:
                    self.report({'INFO'}, "Assigned target to " + modifier.lower() + " modifier")
    
        return {"FINISHED"}
        

################################################### 
# Assign target empty object to specified modifier   
###################################################

def assignTarget(modifier):

    scene = bpy.context.scene
    activeObj = bpy.context.active_object
    selected = bpy.context.selected_objects
    
    for obj in selected:
        if obj.type == 'EMPTY':
            target = obj

    for obj in selected:
        if modifier == 'ARRAY':
            for mod in obj.modifiers:
                if mod.type == 'ARRAY':
                    mod.use_relative_offset = False
                    mod.use_object_offset = True
                    mod.offset_object == bpy.data.objects[target.name]
                    return True
        elif modifier == 'MIRROR':
            for mod in obj.modifiers:
                if mod.type == 'MIRROR':
                    mod.mirror_object = bpy.data.objects[target.name]
                    return True
        elif modifier == 'SCREW':
            for mod in obj.modifiers:
                if mod.type == 'SCREW':
                    mod.object = bpy.data.objects[target.name]
                    return True
        elif modifier == 'CAST':
            for mod in obj.modifiers:
                if mod.type == 'CAST':
                    mod.object = bpy.data.objects[target.name]
                    return True
        elif modifier == 'SIMPLE_DEFORM':
            for mod in obj.modifiers:
                if mod.type == 'SIMPLE_DEFORM':
                    mod.origin = bpy.data.objects[target.name]
                    return True
        else:
            return False

    return {"FINISHED"}


################################################### 
# Add Modifier function, for use with smart mod classes.  
################################################### 

def addMod(modifier, name):
    #ops.object.modifier_add(type=modifier)
    bpy.context.object.modifiers.new(type=modifier, name=name)
    return {"FINISHED"}


################################################### 
# Add an Array modifier with object offset enabled 
###################################################      

class addArray(bpy.types.Operator):
    """Add a Array modifier with object offset, use 2nd selected object as offset object"""
    bl_label = "Add Array Modifier"
    bl_idname = "object.add_array"
    bl_options = {'REGISTER', 'UNDO'}
       
    
    # Check to see if an object is selected
    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0
    
    # Add the modifier
    def execute(self, context):
        scene = bpy.context.scene
        activeObj = context.active_object
        targetObj = context.selected_objects
        
        # Add a array modifier
        addMod("ARRAY", "SmartArray")
                
        # Store the mesh object
        selectedObj = activeObj        
        
        # Set status of array object usage
        useArrayObj = False
        
        # If a second object is not selected, don't use mirror object
        if len(targetObj) > 1:
            useArrayObj = True

        # Make the targetObj active
        try:
            scene.objects.active = [obj for obj in targetObj if obj != activeObj][0]
        except:
            pass
                
        # Check for active object
        activeObj = context.active_object
        
        # Swap the selected and active objects
        selectedObj, activeObj = activeObj, selectedObj
        
        # Deselect the empty object and select the mesh object again, making it active
        selectedObj.select = False
        activeObj.select = True
        scene.objects.active = activeObj
        
        # Find the added modifier, and check for status of useArrayObj
        if useArrayObj == True:
            for mod in activeObj.modifiers:
                if mod.type == 'ARRAY':
                    mod.use_relative_offset = False
                    mod.use_object_offset = True
                    if useArrayObj:
                        mod.offset_object = bpy.data.objects[selectedObj.name]
                        self.report({'INFO'}, "Assigned target object to modifier")      

        return {"FINISHED"}
            

################################################### 
# Add an Boolean modifier with second object as target 
###################################################      

class addBoolean(bpy.types.Operator):
    """Add a Boolean modifier with 2nd selected object as target object"""
    bl_label = "Add Boolean Modifier"
    bl_idname = "object.add_boolean"
    bl_options = {'REGISTER', 'UNDO'}
       
    
    #Check to see if an object is selected
    @classmethod
    def poll(cls, context):
        if len(context.selected_objects) > 1:
            return True
    
    # Add the modifier
    def execute(self, context):
        scene = bpy.context.scene
        activeObj = context.active_object
        selected = context.selected_objects

        count = 0

        for obj in selected:
            if obj != activeObj:
                target = obj
                count += 1

                addMod("BOOLEAN", "SmartBoolean "+str(count))
                
                for mod in activeObj.modifiers:
                    if mod.name == 'SmartBoolean '+str(count):
                        mod.object = bpy.data.objects[target.name]
                        mod.operation = 'DIFFERENCE'


        self.report({'INFO'}, "Assigned each object to a boolean modifier")  

        return {"FINISHED"}


################################################### 
# Add an Cast modifier with target object assigned if selected 
###################################################      

class addCast(bpy.types.Operator):
    """Add a Cast modifier with, use selected empty as target object"""
    bl_label = "Add Cast Modifier"
    bl_idname = "object.add_cast"
    bl_options = {'REGISTER', 'UNDO'}
       
    
    # Check to see if an object is selected
    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0
    
    # Add the modifier
    def execute(self, context):
        scene = bpy.context.scene
        activeObj = context.active_object
        targetObj = context.selected_objects
        
        # Add a array modifier
        addMod("CAST", "SmartCast")
                
        # Store the mesh object
        selectedObj = activeObj        
        
        # Set status of array object usage
        useCastObj = False
        
        # If a second object is not selected, don't use mirror object
        if len(targetObj) > 1:
            useCastObj = True

        # Make the targetObj active
        try:
            scene.objects.active = [obj for obj in targetObj if obj != activeObj][0]
        except:
            pass
                
        # Check for active object
        activeObj = context.active_object
        
        # Swap the selected and active objects
        selectedObj, activeObj = activeObj, selectedObj
        
        # Deselect the empty object and select the mesh object again, making it active
        selectedObj.select = False
        activeObj.select = True
        scene.objects.active = activeObj
        
        # Find the added modifier, and check for status of useCastObj
        if useCastObj == True:
            for mod in activeObj.modifiers:
                if mod.type == 'CAST':
                    if useCastObj:
                        mod.object = bpy.data.objects[selectedObj.name]
                        self.report({'INFO'}, "Assigned target object to cast modifier")      

        return {"FINISHED"}


################################################### 
# Add a Mirror Modifier with clipping enabled   
################################################### 
    
class addMirror(bpy.types.Operator):
    """Add a Mirror modifier with clipping, use 2nd selected object as Mirror center"""
    bl_label = "Add Mirror Modifier"
    bl_idname = "object.add_mirror"
    bl_options = {'REGISTER', 'UNDO'}
       
    
    # Check to see if an object is selected
    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0
    
    # Add the modifier
    def execute(self, context):
              
        scene = context.scene
        
        # Check for active object
        activeObj = context.active_object
        selected = context.selected_objects
        
        # Store the mesh object
        origActive = activeObj        
        
        # Set status of mirror object usage
        useTarget = False

        # If no Empty is selected, don't use mirror object
        for obj in context.selected_objects:
            if obj.type == 'EMPTY':
                useTarget = True
        
        # Find all selected objects
        for obj in context.selected_objects:
            scene.objects.active = obj
            if obj.type == 'EMPTY':
                targetObj = obj
            elif obj.type == 'MESH' or obj.type == 'CURVE':
                # Add a mirror modifier
                addMod("MIRROR", "SmartMirror")

        #Make the targetObj active
        try:
            scene.objects.active = [obj for obj in targetObj if obj != activeObj][0]
        except:
            pass
                
        # Check for active object
        activeObj = context.active_object
        
        # Swap the selected and active objects
        origActive, activeObj = activeObj, origActive
        
        # Deselect the empty object and select the mesh object again, making it active
        origActive.select = False
        activeObj.select = True
        scene.objects.active = activeObj
        
        
        for obj in selected:
            scene.objects.active = obj
            # Find the added modifier, enable clipping, set the mirror object
            for mod in obj.modifiers:
                if mod.type == 'MIRROR':
                    mod.use_clip = True
                    if useTarget:
                        mod.mirror_object = bpy.data.objects[targetObj.name]
                        self.report({'INFO'}, "Assigned target object to modifier")      

        return {"FINISHED"}
    
################################################### 
# Add a Lattice with auto assigning of the lattice object   
################################################### 


class addLattice(bpy.types.Operator):
    """Add a Lattice Modifier and auto-assign to selected lattice object"""
    bl_idname = "object.add_lattice"
    bl_label = "Add a lattice modifier"
    bl_options = {'REGISTER', 'UNDO'}

   # Check to see if an object is selected
    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    # Add the modifier
    def execute(self, context):

        scene = bpy.context.scene
        activeObj = context.active_object
        targetObj = context.selected_objects
        
        # Add a lattice modifier
        addMod("LATTICE", "SmartLattice")

        # Store the mesh object
        selectedObj = activeObj

        # Set status of lattice object usage
        useLatticeObj = False

        # If an second object is not selected, don't use lattice object
        if len(targetObj) > 1:
            useLatticeObj = True

        # Make the targetObj active
        try:
            scene.objects.active = [obj for obj in targetObj if obj != activeObj][0]
        except:
            pass
                
        # Check for active object
        activeObj = context.active_object
        
        # Swap the selected and active objects
        selectedObj, activeObj = activeObj, selectedObj
        
        # Deselect the empty object and select the mesh object again, making it active
        selectedObj.select = False
        activeObj.select = True
        scene.objects.active = activeObj
        
        # Find the added modifier, set the lattice object
        for mod in activeObj.modifiers:
            if mod.type == 'LATTICE':
                if useLatticeObj == True:
                    mod.object = bpy.data.objects[selectedObj.name]
                    self.report({'INFO'}, "Assigned lattice object to modifier")         

        return {"FINISHED"}


################################################### 
# Add a Screw modifier with an object axis set  
################################################### 

class addScrew(bpy.types.Operator):
    """Add a Screw modifier, use 2nd selected object as object axis"""
    bl_label = "Add Screw Modifier"
    bl_idname = "object.add_screw"
    bl_options = {'REGISTER', 'UNDO'}
       
    
    # Check to see if an object is selected
    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0
    
    # Add the modifier
    def execute(self, context):
              
        scene = context.scene
        
        # Check for active object
        activeObj = context.active_object
        
        # Find all selected objects
        targetObj = context.selected_objects
        
        # Add a screw modifier
        addMod("SCREW", "SmartScrew")
                
        # Store the mesh object
        selectedObj = activeObj        
        
        # Set status of screw object usage
        useScrewObj = False
        
        # If a second object is not selected, don't use screw object
        if len(targetObj) > 1:
            useScrewObj = True

        # Make the targetObj active
        try:
            scene.objects.active = [obj for obj in targetObj if obj != activeObj][0]
        except:
            pass
                
        # Check for active object
        activeObj = context.active_object
        
        # Swap the selected and active objects
        (selectedObj, activeObj) = (activeObj, selectedObj)
        
        # Deselect the empty object and select the mesh object again, making it active
        selectedObj.select = False
        activeObj.select = True
        scene.objects.active = activeObj
        
        # Find the added modifier, enable clipping, set the mirror object
        for mod in activeObj.modifiers:
            if mod.type == 'SCREW':
                if useScrewObj == True:
                    mod.object = bpy.data.objects[selectedObj.name]
                    self.report({'INFO'}, "Assigned target axis object to modifier")      

        return {"FINISHED"}


################################################### 
# Add a Remesh Modifier with Smooth set as the type   
################################################### 

class addRemesh(bpy.types.Operator):
    """Add a Smooth Remesh Modifier"""
    bl_label = "Smooth Remesh"
    bl_idname = "object.smooth_remesh"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        # 
        return not context.sculpt_object.use_dynamic_topology_sculpting

    def execute(self, context):
        AddMod("REMESH", "Remesh")
        context.object.modifiers['Remesh'].mode = 'SMOOTH'
        return {"FINISHED"}


################################################### 
# Apply any remesh modifiers   
################################################### 

class applyRemesh(bpy.types.Operator):
    """Apply only Remesh Modifiers"""
    bl_label = "Apply Only Remesh Modifiers"
    bl_idname = "object.apply_remesh"
    bl_options = {'REGISTER', 'UNDO'}

    # test if it is possible to apply a remesh modifier
    @classmethod    
    def poll(cls, context):

        # get the active object
        obj = context.active_object

        # test if there's an active object
        if obj:
            # find modifiers with "REMESH" type
            for mod in obj.modifiers:
                if mod.type == 'REMESH':
                    return True
        return False

    def execute(self, context):

        #check for active object
        obj = context.active_object

        # If any remesh modifiers exist on object, apply them.
        for mod in obj.modifiers:
            if mod.type == 'REMESH':
                applyModifier(apply_as='DATA', modifier=mod.name)
                self.report({'INFO'}, "Applied remesh modifier(s)")   

        return {"FINISHED"}


################################################### 
# Add a Subsurf Modifier at level 2 and optimal display enabled   
################################################### 

class addSubsurf(bpy.types.Operator):
    """Add a Subsurf modifier at level 2 with Optimal Display"""
    bl_label = "Add a Subsurf Modifier"
    bl_idname = "object.add_subsurf"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):       
        scene = context.scene
        sel = context.selected_objects
        
        for obj in sel:
            scene.objects.active = obj
            ops.object.modifier_add(type='SUBSURF')
            print("Added Subsurf Modifier")
        
            for mod in obj.modifiers:
                if mod.type == 'SUBSURF':
                    mod.show_only_control_edges = True
                    mod.levels = 2
                
        return {"FINISHED"}
      
        
################################################### 
# Apply only subsurf modifiers   
################################################### 

class applySubsurf(bpy.types.Operator):
    """Apply only Subsurf Modifiers"""
    bl_label = "Apply Only Subsurf Modifiers"
    bl_idname = "object.apply_subsurf"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Test if it is possible to apply a subsurf modifier, thanks to Richard Van Der Oost
    @classmethod    
    def poll(cls, context):
        # Get the active object
        obj = context.active_object

        # Test if there's an active object
        if obj:

           # Find modifiers with "SUBSURF" type
           for mod in obj.modifiers:
               if mod.type == 'SUBSURF':
                   return True
        return False
    
    def execute(self, context):

        #check for active object
        obj = context.active_object    

        # If any subsurf modifiers exist on object, apply them.
        for mod in obj.modifiers:
            if mod.type == 'SUBSURF':
                applyModifier(apply_as='DATA', modifier=mod.name)
                self.report({'INFO'}, "Applied Subsurf modifier(s)")   
        
        return {"FINISHED"}


################################################### 
# Apply all modifiers on the active object
################################################### 

class applyModifiers(bpy.types.Operator):
    """Apply all modifiers on selected objects"""
    bl_label = "Apply All Modifiers"
    bl_idname = "object.apply_modifiers"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        # Make sure there's a selected object and that that object has modifiers to apply
        return len(context.selected_objects) > 0 and len(context.active_object.modifiers) > 0
   
    def execute(self, context):

        sel = context.selected_objects
        for obj in sel:
            # set the current object in the loop to active
            context.scene.objects.active = obj
            
            # If any modifiers exist on current object object, apply them.
            for mod in obj.modifiers:
                applyModifier(apply_as='DATA', modifier=mod.name)

            # maybe for debug you might do an 'applied to obj.name' in before
            # iterating to the next
            
        self.report({'INFO'}, "Applied all modifiers on selected objects")   
        return {"FINISHED"} 


################################################### 
# Remove all modifiers on selected objects
###################################################

class removeModifiers(bpy.types.Operator):
    """Remove Modifiers From Selected Objects"""
    bl_idname = "object.modifier_remove_all"
    bl_label = "Remove modifiers on all selected objects"
    bl_options = {'REGISTER', 'UNDO'}    
    
    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        selected = context.selected_objects
        
        for obj in selected:
            context.scene.objects.active = obj
            for mod in obj.modifiers:
                ops.object.modifier_remove(modifier=mod.name)
        self.report({'INFO'}, "Removed all modifiers on selected objects")
        return {'FINISHED'}


################################################### 
# Halve the mesh and add a Mirror modifier   
################################################### 

def select_off_center(self, context):

    obj = context.active_object.data

    for verts in obj.vertices:
        if verts.co.x < -0.001:    
            verts.select = True


class halveMesh(bpy.types.Operator):    
    """Delete all vertices on the -X side of center"""
    bl_idname = "object.mesh_halve"
    bl_label = "Halve and mirror mesh"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):

        if bpy.context.active_object.type == 'MESH':
            return True
        return False

    def execute(self, context):
        
        obj = context.active_object.data
        selected = context.selected_objects
        # Go to edit mode and ensure all vertices are deselected, preventing accidental deletions
        
        if context.object.mode == 'OBJECT':
        
            for obj in selected:
                if obj.type == 'MESH':
                    context.scene.objects.active = obj

                    ops.object.mode_set(mode='EDIT')
                    ops.mesh.select_all(action='DESELECT')
                    ops.object.mode_set(mode='OBJECT')
                    
                    # Find verts left of center and select them
                    select_off_center(self, context)

                    ops.object.mode_set(mode='EDIT')
                    ops.mesh.delete(type='VERT')
                    
                    # Switch back to object mode and add the mirror modifier
                    ops.object.mode_set(mode='OBJECT')
                    addMod("MIRROR", "Mirror")

                    self.report({'INFO'}, "Mesh half removed and Mirror modifier added")
                else:
                    self.report({'INFO'}, "Only works on mesh objects")


        elif bpy.context.object.mode == 'EDIT':
            ops.mesh.select_all(action='DESELECT')
            ops.object.mode_set(mode='OBJECT')
            
            # Find verts left of center and select them
            select_off_center(self, context)
                    
            # Toggle edit mode and delete the selection
            ops.object.mode_set(mode='EDIT')
            ops.mesh.delete(type='VERT')

            self.report({'INFO'}, "Mesh half removed")

        return {'FINISHED'}


################################################### 
# Set object origin to center of current mesh selection in edit mdoe   
################################################### 

class setObjectOrigin(bpy.types.Operator):
    """Set Object Origin To Center Of Current Mesh Selection"""
    bl_idname = "mesh.set_object_origin"
    bl_label = "Set origin to the selection center"
    bl_options = {'REGISTER', 'UNDO'}    
    
    def execute(self, context):
        mode = bpy.context.object.mode
        if mode != 'EDIT':
            # If user is not in object mode, don't run the operator and report reason to the Info header
            self.report({'INFO'}, "Must be run in Edit Mode")
        else:
            # Set the 3D Cursor to the selected mesh and then center the origin
            # in object mode followed by returning to edit mode.
            ops.view3d.snap_cursor_to_selected()
            ops.object.mode_set(mode='OBJECT')
            ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
            ops.object.mode_set(mode='EDIT')
            
        return {"FINISHED"}


################################################### 
# Creating operator for edit PET settings
################################################### 

class petEditSettings(bpy.types.Operator):
    """Toggle Setting For Mesh Proportional Editing Tool"""
    bl_idname = "mesh.pet"
    bl_label = "Toggle Mesh PET"

    setting = bpy.props.StringProperty()

    def execute(self, context):

        setting = self.setting

        if setting == 'use_pressure_size':
            if unified_size:
                value = unified.use_pressure_size
                unified.use_pressure_size = not value 

        return {"FINISHED"}

################################################### 
# Creating operator for object PET settings
################################################### 

class petObjectSettings(bpy.types.Operator):
    """Toggle Setting For Objects Proportional Editing Tool"""
    bl_idname = "object.pet"
    bl_label = "Toggle Object PET "

    def execute(self, context):

        pet = context.scene.tool_settings.use_proportional_edit_objects
        context.scene.tool_settings.use_proportional_edit_objects = not pet

        return {"FINISHED"}

### ----------------------- Sculpt Operators ----------------------- ###

################################################### 
# Creating operator for brush settings
################################################### 

class sculptBrushSetting(bpy.types.Operator):
    """Toggle Setting For Active Brush"""
    bl_idname = "sculpt.brush_setting"
    bl_label = "Toggle Brush Setting"

    setting = bpy.props.StringProperty()

    def execute(self, context):

        setting = self.setting
        brush = context.tool_settings.sculpt.brush

        unified = context.tool_settings.unified_paint_settings
        unified_size = unified.use_unified_size
        unified_strength = unified.use_unified_strength

        if setting == 'use_pressure_size':
            if unified_size:
                value = unified.use_pressure_size
                unified.use_pressure_size = not value 
            else:
                value = brush.use_pressure_size
                brush.use_pressure_size = not value
        elif setting == 'use_pressure_strength':
            if unified_strength:
                value = unified.use_pressure_strength
                unified.use_pressure_strength = not value 
            else:
                value = brush.use_pressure_strength
                brush.use_pressure_strength = not value
        elif setting == 'use_frontface':
            value = brush.use_frontface
            brush.use_frontface = not value
        elif setting == 'use_accumulate':
            value = brush.use_accumulate
            brush.use_accumulate = not value
        return {"FINISHED"}


################################################### 
# Creating operator for toggling Sculpt Symmetry
################################################### 

class sculptSymmetry(bpy.types.Operator):
    """Toggle Symmetry For Sculpting"""
    bl_idname = "sculpt.symmetry"
    bl_label = "Toggle Sculpt Symmetry"

    
    axis = bpy.props.IntProperty(name = "Axis",
                    description = "switch between symmetry axis'",
                    default = 0)

    def execute(self, context):
        if self.axis == -1:
            symmetry_x = context.tool_settings.sculpt.use_symmetry_x
            context.tool_settings.sculpt.use_symmetry_x = not symmetry_x
        if self.axis == 0:
            symmetry_y = context.tool_settings.sculpt.use_symmetry_y
            context.tool_settings.sculpt.use_symmetry_y = not symmetry_y
        if self.axis == 1:
            symmetry_z = context.tool_settings.sculpt.use_symmetry_z
            context.tool_settings.sculpt.use_symmetry_z = not symmetry_z
        return {"FINISHED"}
    

################################################### 
# Creating operator for toggling Axis Locks
################################################### 

class sculptAxisLock(bpy.types.Operator):
    """Toggle Axis Lock In Sculpting"""
    bl_idname = "sculpt.axislock"
    bl_label = "Toggle Axis Lock"


    axis = bpy.props.IntProperty(name = "Axis",
                    description = "switch axis' to lock",
                    default = 0)

    def execute(self, context):
        if self.axis == -1:
            lock_x = context.tool_settings.sculpt.lock_x
            context.tool_settings.sculpt.lock_x = not lock_x
        if self.axis == 0:
            lock_y = context.tool_settings.sculpt.lock_y
            context.tool_settings.sculpt.lock_y = not lock_y
        if self.axis == 1:
            lock_z = context.tool_settings.sculpt.lock_z
            context.tool_settings.sculpt.lock_z = not lock_z
        return {"FINISHED"}


################################################### 
# Creating operator for toggling collapse short edges
################################################### 

class sculptCollapseShortEdges(bpy.types.Operator):
    """"Toggle Collapse Short Edges Option"""
    bl_label = "Toggle Collapse Short Edges"
    bl_idname = "sculpt.collapse_short_edges"
    
    # test if it is possible to toggle short edge collapse
    @classmethod    
    def poll(cls, context):
        # if dyntopo True, returns True, else returns False :)
        return context.sculpt_object.use_dynamic_topology_sculpting
   
    def execute(self, context):
        #invert current state
        shortEdges = context.scene.tool_settings.sculpt.use_edge_collapse
        context.scene.tool_settings.sculpt.use_edge_collapse = not shortEdges
        return {"FINISHED"}


### ----------------------- Display Operators ----------------------- ###

################################################### 
# Operator for toggling double sided on selected objects
################################################### 

class objectDoubleSided(bpy.types.Operator):
    """Toggle Double Sided Option"""
    bl_label = "Toggle Double Sided"
    bl_idname = "object.double_sided"
    bl_description = "Toggle double-sided on all selected objects"

    def execute(self, context):

        scene = context.scene
        selected = context.selected_objects
        origActive = context.active_object
        doubleSided = context.object.data.show_double_sided

        for obj in selected:
            scene.objects.active = obj
            context.object.data.show_double_sided = not doubleSided

        scene.objects.active = origActive
        return {"FINISHED"}

class renderOnly(bpy.types.Operator):
    """Set Display Mode To Show Only Render Results"""
    bl_label = "Toggle Only Render"
    bl_idname = "scene.show_only_render"
    bl_description = "Set viewport display mode to render only"

    def execute(self, context):
        only_render = context.space_data.show_only_render
        context.space_data.show_only_render = not only_render

        return {"FINISHED"}

################################################### 
# Operator for toggling all edges wire on selected objects
################################################### 

class allEdgesWire(bpy.types.Operator):
    """Toggle Wire Display With All Edges"""
    bl_label = "Toggle All Edges Wire"
    bl_idname = "object.all_edges_wire"
    bl_description = "Toggle all-edges wireframe on all selected objects"

    def execute(self, context):

        scene = context.scene
        selected = context.selected_objects
        origActive = context.active_object
        
        allEdges = context.object.show_all_edges
        wire = context.object.show_wire

        for obj in selected:
            scene.objects.active = obj
            context.object.show_all_edges = not allEdges
            context.object.show_wire = not wire

        scene.objects.active = origActive
        return {"FINISHED"}


# boiler plate: register / unregister

def register():
    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)
    
if __name__ == "__main__":
    register()

########NEW FILE########
__FILENAME__ = quick_scene
import bpy

class QuickSceneOptions(bpy.types.Menu):
	bl_idname = "scene.quick_options"
	bl_label = "Quick Scene Settings"

	def draw(self, context):
	    layout = self.layout

	    layout.operator("gpencil.active_frame_delete", "Delete Grease", icon='GREASEPENCIL')

	    only_render = context.space_data.show_only_render
	    if only_render:
		    layout.operator("scene.show_only_render", "Disable Only Render")
	    else:
	    	layout.operator("scene.show_only_render", "Show Only Render")
	    	
def register():
	bpy.utils.register_class(QuickSceneOptions)


def unregister():
	bpy.utils.unregister_class(QuickSceneOptions)


if __name__ == "__main__":
	register()
########NEW FILE########
__FILENAME__ = quick_sculpt_mode
import bpy

### ------------ New Menus ------------ ###        
        
# creates a menu for Sculpt mode tools
class QuickSculptTools(bpy.types.Menu):
    
    bl_label = "Quick Sculpt Tools"
    bl_idname = "sculpt.tools_menu"

    def draw(self, context):
        layout = self.layout
        dyntopo = bpy.context.sculpt_object.use_dynamic_topology_sculpting
        shortEdges = bpy.context.scene.tool_settings.sculpt.use_edge_collapse

        symmetry_x = bpy.context.tool_settings.sculpt.use_symmetry_x
        symmetry_y = bpy.context.tool_settings.sculpt.use_symmetry_y
        symmetry_z = bpy.context.tool_settings.sculpt.use_symmetry_z

        lock_x = bpy.context.tool_settings.sculpt.lock_x
        lock_y = bpy.context.tool_settings.sculpt.lock_y
        lock_z = bpy.context.tool_settings.sculpt.lock_z


        if dyntopo:
            layout.operator("sculpt.dynamic_topology_toggle", 'Disable Dynamic Topology',)
        else:
            layout.operator("sculpt.dynamic_topology_toggle", 'Enable Dynamic Topology')

        if shortEdges:
            layout.operator("sculpt.collapse_short_edges", 'Disable Collapse Short Edges',)
        else:
            layout.operator("sculpt.collapse_short_edges", 'Enable Collpase Short Edges')
        
        layout.separator()
        
        layout.operator("object.add_subsurf", 'Add Subsurf', icon='MOD_SUBSURF')
        layout.operator("object.apply_subsurf", 'Apply Subsurf')
        
        layout.separator()
        
        layout.operator("object.smooth_remesh", 'Remesh Modifier', icon='MOD_REMESH')
        layout.operator("object.apply_remesh", 'Apply Remesh')
        
        layout.separator()
        
        layout.operator("object.apply_modifiers", 'Apply All Modifiers')
        
        layout.separator()
        
        if symmetry_x:
            layout.operator("sculpt.symmetry", 'Disable X Symmetry').axis = -1
        else:
            layout.operator("sculpt.symmetry", 'Enable X Symmetry').axis = -1

        if symmetry_y:
            layout.operator("sculpt.symmetry", 'Disable Y Symmetry').axis = 0
        else:
            layout.operator("sculpt.symmetry", 'Enable Y Symmetry').axis = 0

        if symmetry_z:
            layout.operator("sculpt.symmetry", 'Disable Z Symmetry').axis = 1
        else:
            layout.operator("sculpt.symmetry", 'Enable Z Symmetry').axis = 1

        layout.separator()
        
        if lock_x:
            layout.operator("sculpt.axislock", 'Disable X Lock', icon='MANIPUL').axis = -1
        else:
            layout.operator("sculpt.axislock", 'Enable X Lock', icon='MANIPUL').axis = -1

        if lock_y:
            layout.operator("sculpt.axislock", 'Disable Y Lock').axis = 0
        else:
            layout.operator("sculpt.axislock", 'Enable Y Lock').axis = 0

        if lock_z:
            layout.operator("sculpt.axislock", 'Disable Z Lock').axis = 1
        else:
            layout.operator("sculpt.axislock", 'Enable Z Lock').axis = 1

#Create menu for brush specific settings
class QuickBrushSettings(bpy.types.Menu):
    bl_label = "Quick Brush Settings"
    bl_idname = "sculpt.brush_settings_menu"

    def draw(self, context):
        layout = self.layout

        brush = context.tool_settings.sculpt.brush
        unified = context.tool_settings.unified_paint_settings
        unified_size = unified.use_unified_size
        unified_strength = unified.use_unified_strength
        
        if unified_size:
            if unified.use_pressure_size:
                pressure_size = layout.operator("sculpt.brush_setting", "Disable Size Pressure")
                pressure_size.setting = 'use_pressure_size'
            else:
                pressure_size = layout.operator("sculpt.brush_setting", "Enable Size Pressure")
                pressure_size.setting = 'use_pressure_size'
        else:
            if brush.use_pressure_size:
                pressure_size = layout.operator("sculpt.brush_setting", "Disable Size Pressure")
                pressure_size.setting = 'use_pressure_size'
            else:
                pressure_size = layout.operator("sculpt.brush_setting", "Enable Size Pressure")
                pressure_size.setting = 'use_pressure_size'

        if unified_strength:
            if unified.use_pressure_strength:
                pressure_strength = layout.operator("sculpt.brush_setting", "Disable Strength Pressure")
                pressure_strength.setting = 'use_pressure_strength'
            else:
                pressure_strength = layout.operator("sculpt.brush_setting", "Enable Strength Pressure")
                pressure_strength.setting = 'use_pressure_strength'
        else:
            if brush.use_pressure_strength:
                pressure_strength = layout.operator("sculpt.brush_setting", "Disable Strength Pressure")
                pressure_strength.setting = 'use_pressure_strength'
            else:
                pressure_strength = layout.operator("sculpt.brush_setting", "Enable Strength Pressure")
                pressure_strength.setting = 'use_pressure_strength'
        
        layout.separator()

        frontface = layout.operator("sculpt.brush_setting", "Front Faces Only")
        frontface.setting = 'use_frontface'
        accumulate = layout.operator("sculpt.brush_setting", "Accumulate")
        accumulate.setting = 'use_accumulate'
        

        layout.separator()

        layout.label("Brush Falloff")
        layout.operator("brush.curve_preset", text="Smooth", icon='SMOOTHCURVE').shape = 'SMOOTH'
        layout.operator("brush.curve_preset", text="Round", icon='SPHERECURVE').shape = 'ROUND'
        layout.operator("brush.curve_preset", text="Root", icon='ROOTCURVE').shape = 'ROOT'
        layout.operator("brush.curve_preset", text="Sharp", icon='SHARPCURVE').shape = 'SHARP'
        layout.operator("brush.curve_preset", text="Line", icon='LINCURVE').shape = 'LINE'
        layout.operator("brush.curve_preset", text="Max", icon='NOCURVE').shape = 'MAX'

### ------------ New Hotkeys and registration ------------ ###   

# addon_keymaps = []

def register():
    bpy.utils.register_class(QuickSculptTools)
    bpy.utils.register_class(QuickBrushSettings)
    
   #  wm = bpy.context.window_manager   
   #  # create the Sculpt hotkeys
   #  km = wm.keyconfigs.addon.keymaps.new(name='Sculpt')
   # # km = bpy.context.window_manager.keyconfigs.active.keymaps['Sculpt']
    
   #  kmi = km.keymap_items.new('sculpt.symmetry', 'X', 'PRESS', shift=True)
   #  kmi.properties.axis = -1
   #  kmi = km.keymap_items.new('sculpt.symmetry', 'Y', 'PRESS', shift=True)
   #  kmi.properties.axis = 0
   #  kmi = km.keymap_items.new('sculpt.symmetry', 'Z', 'PRESS', shift=True)
   #  kmi.properties.axis = 1

   #  # create sculpt menu hotkey
   #  kmi = km.keymap_items.new('wm.call_menu', 'Q', 'PRESS')
   #  kmi.properties.name = 'sculpt.tools_menu' 
    
   #  addon_keymaps.append(km)

    
def unregister():

    #unregister the new operators 
    bpy.utils.unregister_class(QuickSculptTools)
    bpy.utils.unregister_class(QuickBrushSettings)
    
    # # remove keymaps when add-on is deactivated
    # wm = bpy.context.window_manager
    # for km in addon_keymaps:
    #     wm.keyconfigs.addon.keymaps.remove(km)
    # del addon_keymaps[:]
    

if __name__ == "__main__":
    register()
    
########NEW FILE########
__FILENAME__ = pref_test
import bpy

class printTest(bpy.types.Operator):
    bl_label = "Print Test"
    bl_idname = "view3d.print_test" 

    def execute(self, context):
        print("Test Print")

        return {"FINISHED"}


def register():
    bpy.utils.register_class(printTest)  

def unregister():
    bpy.utils.unregister_class(printTest)    
########NEW FILE########
__FILENAME__ = addonTemplate
#script template by Alex Telford | www.cgcookie.com
#script by Your name | Your site
#Description:
#Add in a description of your script here
bl_info = {
    "name": "Script Name",
    "author": "Your Name",
    "version": (0, 1),
    "blender": (2, 6, 6),
    "location": "View3D > Toolshelf",
    "description": "Description",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "View3D"}
    
#import modules
import bpy
from bpy.props import *

class myScriptInitialize(bpy.types.Panel):
    bl_label = "Panel Name"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    #mode that the panel will show in, OBJECT, SCULPT or EDIT
#    @classmethod
#    def poll(self, context):
#        return(bpy.context.mode == 'OBJECT')
    #defing props for layout
    def propCalls():
        #create props for layout
        #examples
        #create object  slot for dropdown
        bpy.types.Object.myObject = bpy.props.StringProperty()
        #enum dropdown
        bpy.types.Scene.myEnum = bpy.props.EnumProperty(
        items = [('1', 'visible text', 'hover text'), 
                 ('1', 'visible text', 'hover text')],
        name = "enumName")
        #create float box
        bpy.types.Scene.myFloat = FloatProperty(name = "My Float", description = "My Float", default = 0.0, min = -10, max = 10)
        #check box
        bpy.types.Scene.myCheckBox= BoolProperty(
            name = "My CheckBox", 
            description = "My Check Box",
            default = True)
        
    #define props
    propCalls()
    def draw(self, context):
        obj = context.object
        scn = context.scene
        
        layout = self.layout
        col = layout.column()
        
        #try to layout, otherwise say something else
        try:
            #layout items
            col.label("My Object")
            col.prop_search(obj, "myObject",  scn, "objects", text = '', icon = 'MESH_DATA')

            col.label("My Enum")
            col.prop(scn, "myEnum", text = '')
            
            col.label("My Float")
            col.prop(scn, "myFloat", text = '')
            
            col.label("My Check Box")
            col.prop(scn, "myCheckBox", text = '')
            
            #execute button
            layout.operator("thisismyscript.withonedot")
        except:
            #couldn't fill object list
            col.label("No Objects in Scene")


#run
class OBJECT_OT_myScript(bpy.types.Operator):
    bl_idname = "thisismyscript.withonedot"
    bl_label = "Execute My Script"
    
    def execute(self, context):
        obj = context.object
        scn = context.scene
        
        ###Run Script
        print (obj.myObject)
        print (scn.myEnum)
        print (scn.myFloat)
        print (scn.myCheckBox)
        #warnings use this context if you need them, here we just print the stuff
        self.report({'WARNING'}, "Done!")
        return{'FINISHED'}

def register():
    ###initialize classes
    bpy.utils.register_class(myScriptInitialize)
    bpy.utils.register_class(OBJECT_OT_myScript)
def unregister():
    bpy.utils.unregister_class(myScriptInitialize)
    bpy.utils.register_class(OBJECT_OT_myScript)
########NEW FILE########
__FILENAME__ = applyModifiers
#script by Alex Telford | CG Cookie | www.blendercookie.com
#Description:
#This script will apply all modifiers on selected objects and remove the subsurf and multiresolutions. This is great for exporting models with a lot of modifiers where you do not want the subsurf applied.
#Usage:
#Load into script editor, hit run script.

#import blender python module
import bpy
#load selected objects into a variable
sel = bpy.context.selected_objects
#make all objects their own data users, this is so we can apply modifiers
bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=True, material=False, texture=False, animation=False)
#loop through all objects
for obj in sel:
	#set the active object to the current object in the loop
    bpy.context.scene.objects.active = obj
	#loop through the modifiers
    for mod in obj.modifiers:
		#check if the modifier is a subsurf or multires
        if mod.type == "SUBSURF" or mod.type == "MULTIRES":
			#if so, set the viewport display to 0, this effectively disables the modifier
            mod.show_viewport = 0
    #apply all modifiers
	bpy.ops.object.convert(target='MESH', keep_original=False)
########NEW FILE########
__FILENAME__ = bmesh_grid
import bpy
import bmesh

bm = bmesh.new()

me = bpy.data.meshes.new("myMesh")

bmesh.ops.create_grid(
        bm,
        x_segments = 4,
        y_segments = 4,
        size = 2,)
        
geo_edges = bm.edges[:]
geo_verts = bm.verts[:]
geo_faces = bm.faces[:]

bmesh.ops.extrude_face_region(
        bm,
        geom = geo_faces,
        )
bmesh.ops.translate(
        bm,
        verts = geo_verts,
        vec = (0.0, 0.0, 1.0))
        
bmesh.ops.inset(
        bm,
        faces = geo_faces,
        use_boundary = True,
        use_even_offset = True,
        use_relative_offset = True,
        thickness = 0.5,
        )

bm.to_mesh(me)  
bm.free()

scene = bpy.context.scene
obj = bpy.data.objects.new("Grid", me)
scene.objects.link(obj)

scene.objects.active = obj
obj.select = True



########NEW FILE########
__FILENAME__ = exportMeshProBuilder
#script by Alex Telford | CG Cookie | www.blendercookie.com
#Description:
#This script will export a text file for use in pro builder for unity
#Usage:
#Load as an addon, it will appear in the 3D view tool shelf as a single button. Currently only works with one object at a time.
#version 1.1 - added support for triangles and ngons
#automatically creates quads and tris from nGons
bl_info = {
    "name": "Export Mesh Data for Pro Builder",
    "author": "Alex Telford",
    "version": (1, 1),
    "blender": (2, 6, 4),
    "api": 51026,
    "location": "View3D > Tool Shelf",
    "description": "Exports mesh data for Pro Builder",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"}
#import data modules
import bpy
import os
#create data for panel
class exportData(bpy.types.Operator):
    bl_idname = "export.export_data"
    bl_label = "Export Data"
    #user specified file path for file output
    obV = bpy.context.active_object.data.vertices
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    #actual code for functions
    def execute(self, context):
		#store vertex and face data in variables
        obF = bpy.context.active_object.data.polygons
		#let's fix the model first
        bpy.ops.object.mode_set(mode='EDIT')
		#select nGons
        bpy.ops.mesh.select_by_number_vertices(number=4, type='GREATER')
		#convert nGons to triangles
        bpy.ops.mesh.quads_convert_to_tris(use_beauty=True)
		#convert triangles to quads, not pretty but is better than holes in the mesh.
        bpy.ops.mesh.tris_convert_to_quads(limit=0.698132, uvs=False, vcols=False, sharp=False, materials=False)
		#return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
		#create file to write
        file = open(self.filepath, 'w')
		#loop through each face
        for face in obF:
			#check if it is a triangle
            if len(face.vertices) == 3:
				#order for triangles
                vs = [face.vertices[1],face.vertices[0],face.vertices[2],face.vertices[1]]
            else:
				#order for quads
                vs = [face.vertices[3],face.vertices[0],face.vertices[2],face.vertices[1]]
			#loop through vertices in new face creation order
            for v in vs:
				#grab the vertex location
                crV = obV[v].co
				#output the vertices to probuilder data
                faces = ""
                faces += str(crV[0])
                faces += ","
                faces += str(crV[1])
                faces += ","
                faces += str(crV[2])
                faces += "\n"
				#write that data to the file
                file.write(str(faces))
                
        return {'FINISHED'}
    #the rest of this stuff is just initiating the panel.
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class exportDataPanel(bpy.types.Panel):
    bl_idname = "Export_Data"
    bl_label = "Export Data"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_context = "objectmode"
    
    def draw(self, context):
        layout = self.layout
        layout.operator("export.export_data", text="Export Data")
def register():
    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)
########NEW FILE########
__FILENAME__ = hotKeyBox
import bpy;
#define operations
hotKeyOne = "bpy.ops.mesh.merge(type='LAST', uvs=False)";
hotKeyOneLbl = 'Merge Last';
hotKeyTwo = "bpy.ops.mesh.remove_doubles(mergedist=0.025)";
hotKeyTwoLbl = 'Remove Doubles';
hotKeyThree = "bpy.ops.mesh.merge(uvs=False)";
hotKeyThreeLbl = 'Merge Center';
hotKeyFour = "bpy.ops.mesh.flip_normals()";
hotKeyFourLbl = 'Flip Normals';
hotKeyFive = "bpy.ops.mesh.subdivide()";
hotKeyFiveLbl = 'Subdivide';
hotKeySix = "bpy.ops.sculpt.sculptmode_toggle()";
hotKeySixLbl = 'Sculpt Mode';
hotKeySevenLbl = 'Create Lightmap UVs';
hotKeyEightLbl = 'Hide Linked';
hotKeyNineLbl = 'Disable Double Sided';
hotKeyTenLbl = 'Enable Double Sided';
hotKeyEleven = "bpy.ops.mesh.loop_to_region(select_bigger=False)";
hotKeyElevenLbl = 'Select Loop Inner Region';
hotKeyTwelve = "bpy.ops.mesh.loop_to_region(select_bigger=True)";
hotKeyTwelveLbl = 'Select Loop Outer Region';
hotKeyThirteenLbl = 'Reset UV';
hotKeyFourteenLbl = 'Show Wires';
hotKeyFifteenLbl = 'Hide Wires';

#    hotkey Panel
class hotkeyPanel(bpy.types.Panel):
    bl_label = "HotKey Box"
    bl_idname = "OBJECT_MT_hotKeyBox"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
 
    def draw(self , context):
        layout = self.layout
        layout.operator("hotkeybox.one", text=hotKeyOneLbl)
        layout.operator("hotkeybox.two", text=hotKeyTwoLbl)
        layout.operator("hotkeybox.three", text=hotKeyThreeLbl)
        layout.operator("hotkeybox.four", text=hotKeyFourLbl)
        layout.operator("hotkeybox.five", text=hotKeyFiveLbl)
        layout.operator("hotkeybox.six", text=hotKeySixLbl)
        layout.operator("hotkeybox.seven", text=hotKeySevenLbl)
        layout.operator("hotkeybox.eight", text=hotKeyEightLbl)
        layout.operator("hotkeybox.nine", text=hotKeyNineLbl)
        layout.operator("hotkeybox.ten", text=hotKeyTenLbl)
        layout.operator("hotkeybox.eleven", text=hotKeyElevenLbl)
        layout.operator("hotkeybox.twelve", text=hotKeyTwelveLbl)
        layout.operator("hotkeybox.thirteen", text=hotKeyThirteenLbl)
        layout.operator("hotkeybox.fourteen", text=hotKeyFourteenLbl)
        layout.operator("hotkeybox.fifteen", text=hotKeyFifteenLbl)
        layout.separator()
 
class OBJECT_OT_ButtonOne(bpy.types.Operator):
    bl_idname = "hotkeybox.one"
    bl_label = "Hotkey One"
    def execute(self, context):
        exec(hotKeyOne);
        return{'FINISHED'}
class OBJECT_OT_ButtonTwo(bpy.types.Operator):
    bl_idname = "hotkeybox.two"
    bl_label = "Hotkey Two"
    def execute(self, context):
        exec(hotKeyTwo);
        return{'FINISHED'}
class OBJECT_OT_ButtonThree(bpy.types.Operator):
    bl_idname = "hotkeybox.three"
    bl_label = "Hotkey Three"
    def execute(self, context):
        exec(hotKeyThree);
        return{'FINISHED'}
class OBJECT_OT_ButtonFour(bpy.types.Operator):
    bl_idname = "hotkeybox.four"
    bl_label = "Hotkey Four"
    def execute(self, context):
        exec(hotKeyFour);
        return{'FINISHED'}
class OBJECT_OT_ButtonFive(bpy.types.Operator):
    bl_idname = "hotkeybox.five"
    bl_label = "Hotkey Five"
    def execute(self, context):
        exec(hotKeyFive);
        return{'FINISHED'}
class OBJECT_OT_ButtonSix(bpy.types.Operator):
    bl_idname = "hotkeybox.six"
    bl_label = "Hotkey Six"
    def execute(self, context):
        exec(hotKeySix);
        return{'FINISHED'}

class OBJECT_OT_ButtonSeven(bpy.types.Operator):
    bl_idname = "hotkeybox.seven"
    bl_label = "Hotkey Seven"
    def execute(self, context):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_by_number_vertices(number=4, type='GREATER')
        bpy.ops.mesh.quads_convert_to_tris(use_beauty=True)
        bpy.ops.mesh.uv_texture_add()
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT='ALL_FACES', PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False, PREF_APPLY_IMAGE=False, PREF_IMG_PX_SIZE=1024, PREF_BOX_DIV=48, PREF_MARGIN_DIV=0.1)
        bpy.ops.object.mode_set(mode='OBJECT')
        return{'FINISHED'}
class OBJECT_OT_ButtonEight(bpy.types.Operator):
    bl_idname = "hotkeybox.eight"
    bl_label = "Hotkey eight"
    def execute(self, context):
        bpy.ops.object.select_linked(extend=False, type='OBDATA')
        bpy.ops.object.hide_view_set(unselected=False)
        return{'FINISHED'}
class OBJECT_OT_ButtonNine(bpy.types.Operator):
    bl_idname = "hotkeybox.nine"
    bl_label = "Hotkey nine"
    def execute(self, context):
        for ob in bpy.context.selected_objects:
            if ob.type == 'MESH' :
                ob.data.show_double_sided = 0
        return{'FINISHED'}
class OBJECT_OT_ButtonTen(bpy.types.Operator):
    bl_idname = "hotkeybox.ten"
    bl_label = "Hotkey ten"
    def execute(self, context):
        for ob in bpy.context.selected_objects:
            if ob.type == 'MESH' :
                ob.data.show_double_sided = 1
        return{'FINISHED'}
class OBJECT_OT_ButtonEleven(bpy.types.Operator):
    bl_idname = "hotkeybox.eleven"
    bl_label = "Hotkey Eleven"
    def execute(self, context):
        exec(hotKeyEleven);
        return{'FINISHED'}

class OBJECT_OT_ButtonTwelve(bpy.types.Operator):
    bl_idname = "hotkeybox.twelve"
    bl_label = "Hotkey Twelve"
    def execute(self, context):
        exec(hotKeyTwelve);
        return{'FINISHED'}
class OBJECT_OT_ButtonThirteen(bpy.types.Operator):
    bl_idname = "hotkeybox.thirteen"
    bl_label = "Hotkey thirteen"
    def execute(self, context):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.uv.reset()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.reset()
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_linked(extend=False, type='OBDATA')
        bpy.ops.object.hide_view_set(unselected=False)
        return{'FINISHED'}
class OBJECT_OT_ButtonFourteen(bpy.types.Operator):
    bl_idname = "hotkeybox.fourteen"
    bl_label = "Hotkey fourteen"
    def execute(self, context):
        for ob in bpy.context.selected_objects:
            if ob.type == 'MESH' :
                ob.show_all_edges = True
                ob.show_wire = True
        return{'FINISHED'}
class OBJECT_OT_ButtonFifteen(bpy.types.Operator):
    bl_idname = "hotkeybox.fifteen"
    bl_label = "Hotkey fifteen"
    def execute(self, context):
        for ob in bpy.context.selected_objects:
            if ob.type == 'MESH' :
                ob.show_all_edges = False
                ob.show_wire = False
        return{'FINISHED'}


class hotkeyMenu(bpy.types.Menu):
    bl_label = "HotKey Menu"
    bl_idname = "OBJECT_MT_hotKeyMenu"
    def draw(self , context):
        layout = self.layout
        layout.operator("hotkeybox.one", text=hotKeyOneLbl)
        layout.operator("hotkeybox.two", text=hotKeyTwoLbl)
        layout.operator("hotkeybox.three", text=hotKeyThreeLbl)
        layout.operator("hotkeybox.four", text=hotKeyFourLbl)
        layout.operator("hotkeybox.five", text=hotKeyFiveLbl)
        layout.operator("hotkeybox.six", text=hotKeySixLbl)
        layout.operator("hotkeybox.seven", text=hotKeySevenLbl)
        layout.operator("hotkeybox.eight", text=hotKeyEightLbl)
        layout.operator("hotkeybox.eleven", text=hotKeyElevenLbl)
        layout.operator("hotkeybox.twelve", text=hotKeyTwelveLbl)
        layout.operator("hotkeybox.thirteen", text=hotKeyThirteenLbl)
        layout.separator()

keymap = bpy.context.window_manager.keyconfigs.default.keymaps['3D View']

for keymapi in keymap.keymap_items:
    if keymapi.idname == "wm.call_menu" and keymapi.properties.name == "OBJECT_MT_hotKeyMenu":
        keymap.keymap_items.remove(keymapi)


keymapi = keymap.keymap_items.new('wm.call_menu', 'Z', 'PRESS', shift=True)
keymapi.properties.name = "OBJECT_MT_hotKeyMenu"

# registering and menu integration
bpy.utils.register_class(OBJECT_OT_ButtonOne)
bpy.utils.register_class(OBJECT_OT_ButtonTwo)
bpy.utils.register_class(OBJECT_OT_ButtonThree)
bpy.utils.register_class(OBJECT_OT_ButtonFour)
bpy.utils.register_class(OBJECT_OT_ButtonFive)
bpy.utils.register_class(OBJECT_OT_ButtonSix)
bpy.utils.register_class(OBJECT_OT_ButtonSeven)
bpy.utils.register_class(OBJECT_OT_ButtonEight)
bpy.utils.register_class(OBJECT_OT_ButtonNine)
bpy.utils.register_class(OBJECT_OT_ButtonTen)
bpy.utils.register_class(OBJECT_OT_ButtonEleven)
bpy.utils.register_class(OBJECT_OT_ButtonTwelve)
bpy.utils.register_class(OBJECT_OT_ButtonThirteen)
bpy.utils.register_class(OBJECT_OT_ButtonFourteen)
bpy.utils.register_class(OBJECT_OT_ButtonFifteen)
bpy.utils.register_class(hotkeyMenu)
bpy.utils.register_class(hotkeyPanel)
########NEW FILE########
__FILENAME__ = mesh_ngon-cleanup
import bpy

bpy.ops.object.mode_set(mode = 'EDIT')

bpy.ops.mesh.select_face_by_sides(number = 4, type = 'GREATER', extend = False)

bpy.ops.mesh.extrude_faces_move()

bpy.ops.mesh.edge_collapse()

########NEW FILE########
__FILENAME__ = mesh_select-path
bl_info = {
    "name": "Addon name",
    "location": "View3D > Edit Mode",
    "description": "Add-on description goes here",
    "author": "Jonathan Williamson",
    "version": (0,0),
    "blender": (2, 6, 7),
    "category": "Mesh",
    }
    
import bpy

mesh = bpy.ops.mesh

class SelectPath(bpy.types.Operator):
    """Select a vertex path"""
    bl_idname = "mesh.select_path"
    bl_label = "Select a Path"
    bl_options = {'REGISTER', 'UNDO'}    
    
    '''##############
    
        Add support for Edge loops and face loops by detecting current selection.    
    
    ##############'''
    
    def execute(self, context):
        if bpy.context.mode == 'EDIT_MESH':
            bpy.ops.view3d.select
            mesh.select_vertex_path(type='TOPOLOGICAL')
            return {'FINISHED'}
        
                
addon_keymaps = []
    
def register():
    bpy.utils.register_class(SelectPath)

    wm = bpy.context.window_manager

    km = wm.keyconfigs.addon.keymaps.new(name='Mesh', space_type='EMPTY')
    kmi = km.keymap_items.new('mesh.select_path', 'SELECTMOUSE', 'PRESS', ctrl=True)
    
    addon_keymaps.append(km)
    


def unregister():
    bpy.utils.register_class(SelectPath)
    
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)
    del addon_keymaps[:]
    
if __name__ == "__main__":
    register()
    
########NEW FILE########
__FILENAME__ = rotatePivot
#script by Your Alex Telford | www.blendercookie.com
#Description:
#Rotates the pivot of an object without effecting the object itself, caution: slow on heavy objects.
bl_info = {
    "name": "Rotate Pivot",
    "author": "Alex Telford",
    "version": (0, 3),
    "blender": (2, 6, 6),
    "location": "View3D > Toolshelf",
    "description": "Rotate the pivot of an object",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "View3D"}
    
#import modules
import bpy
from bpy.props import *

class rotatePivotInit(bpy.types.Panel):
    bl_label = "Rotate Pivot"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    #mode that the panel will show in, OBJECT, SCULPT or EDIT
    @classmethod
    def poll(self, context):
       return(bpy.context.mode == 'OBJECT')

    #check box
    bpy.types.Scene.applyRotationFirst= BoolProperty(
        name = "Apply Rotation", 
        description = "Apply Rotation before rotating",
        default = True)
        
    def draw(self, context):
        obj = context.object
        scn = context.scene
        
        layout = self.layout
        col = layout.column()
        #try to layout, otherwise say something else
        try:
            selected = bpy.context.scene.objects.active.name
            failCheck = bpy.context.selected_objects[1]
            #layout items
            col.label("Copy Rotation from active(last selected) to all other selected")
            col.label("Copy Rotation From:")
            col.label('>>'+selected)
            col.label("Copy Rotation To:")
            for ob in bpy.context.selected_objects:
                if ob != bpy.context.scene.objects.active:
                    col.label('>>'+ob.name)
            
            col.label("Apply initial rotation")
            col.prop(scn, "applyRotationFirst", text = '')
            #execute button
            layout.operator("copyrotation.toselected")
        except:
            #couldn't fill object list
            col.label("Select an object")

#run
class OBJECT_OT_rotatePivot(bpy.types.Operator):
    bl_idname = "copyrotation.toselected"
    bl_label = "Rotate"
    
    def execute(self, context):
        obj = context.object
        scn = context.scene
        
        ###Run Script
        #active
        active = bpy.context.scene.objects.active
        selection = bpy.context.selected_objects
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        pivotPoint = context.space_data.pivot_point
        context.space_data.pivot_point = "CURSOR"
        for ob in selection:
            if ob != active:
                print(ob)
                bpy.context.scene.objects.active = ob
                ob.select = True
                if scn.applyRotationFirst == True:
                    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
                rotatePivot(active.rotation_euler)
                bpy.ops.object.select_all(action='DESELECT')
        context.space_data.pivot_point = pivotPoint
        #warnings use this context if you need them, here we just print the stuff
        self.report({'INFO'}, "Done!")
        
        return{'FINISHED'}
    
###functions
def rotatePivot(rotation):
    #rotate selected object based on a vector
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.transform.rotate(value=rotation.x, axis=(1,0,0), constraint_orientation='GLOBAL')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.transform.rotate(value=-rotation.x, axis=(1,0,0), constraint_orientation='GLOBAL')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.transform.rotate(value=rotation.y, axis=(0,1,0), constraint_orientation='GLOBAL')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.transform.rotate(value=-rotation.y, axis=(0,1,0), constraint_orientation='GLOBAL')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.transform.rotate(value=rotation.z, axis=(0,0,1), constraint_orientation='GLOBAL')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.transform.rotate(value=-rotation.z, axis=(0,0,1), constraint_orientation='GLOBAL')
    bpy.ops.object.mode_set(mode='OBJECT')

def register():
    ###initialize classes
    bpy.utils.register_class(rotatePivotInit)
    bpy.utils.register_class(OBJECT_OT_rotatePivot)
def unregister():
    bpy.utils.unregister_class(rotatePivotInit)
    bpy.utils.register_class(OBJECT_OT_rotatePivot)
########NEW FILE########
__FILENAME__ = script-template
bl_info = {
    "name": "Addon name",
    "location": "View3D > Add > Mesh > Add SubD Cube",
    "description": "Add-on description goes here",
    "author": "Jonathan Williamson",
    "version": (0,0),
    "blender": (2, 6, 6),
    "category": "Add Mesh",
    }

import bpy

class addSubDCube(bpy.types.Operator):
    """Add a simple box mesh"""
    bl_idname = "mesh.cube_subd_add"
    bl_label = "Add SubD Cube"
    bl_options = {'REGISTER', 'UNDO'}    
    
    def execute(self, context):
        obj = context.active_object
        
        bpy.ops.mesh.primitive_cube_add(view_align=False)
        bpy.ops.object.modifier_add(type='SUBSURF')
                
        obj = context.active_object
        
        activeMod = obj.modifiers
        
        for mod in obj.modifiers:
            if mod.type == 'SUBSURF':
                mod.show_only_control_edges = True
                mod.levels = 2
        
      
        return {'FINISHED'}
 

def menu_func(self, context):
    self.layout.operator(addSubDCube.bl_idname, icon='MOD_SUBSURF')
            
def register():
    bpy.utils.register_class(addSubDCube)
    bpy.types.INFO_MT_mesh_add.append(menu_func)
    
def unregister():
    bpy.utils.unregister_class(addSubDCube)
    bpy.types.INFO_MT_mesh_add.remove(menu_func)
    
if __name__ == "__main__":
    register()
########NEW FILE########
__FILENAME__ = sculptSymmetry
import bpy
class sculptSymmetry(bpy.types.Operator):
    """Toggle Symmetry For Sculpting"""
    bl_idname = "sculpt.symmetry"
    bl_label = "Toggle Sculpt Symmetry"

    
    axis = bpy.props.IntProperty(name = "Axis",
                    description = "switch between symmetry axis'",
                    default = -1)

    # def execute(self, context):

    #     symmetry = self.axis
    #     self.axis = not symmetry

    def execute(self, context):
        if self.axis == -1:
            symmetry_x = context.tool_settings.sculpt.use_symmetry_x
            context.tool_settings.sculpt.use_symmetry_x = not symmetry_x
        if self.axis == 0:
            symmetry_y = context.tool_settings.sculpt.use_symmetry_y
            context.tool_settings.sculpt.use_symmetry_x = not symmetry_y
        if self.axis == 1:
            symmetry_z = context.tool_settings.sculpt.use_symmetry_z
            context.tool_settings.sculpt.use_symmetry_z = not symmetry_z
        return {"FINISHED"}

def menu_func(self, context):
    self.layout.operator("sculpt.symmetry", "Test X Symmetry").axis = -1
    self.layout.operator("sculpt.symmetry", "Test Y Symmetry").axis = 0
    self.layout.operator("sculpt.symmetry", "Test Z Symmetry").axis = 1


def register():
    bpy.utils.register_module(__name__)
    bpy.types.sculpt_tools_menu.append(menu_func)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.sculpt_tools_menu.remove(menu_func)
        
if __name__ == "__main__":
    register()
########NEW FILE########
__FILENAME__ = stringProp-tool
import bpy

class BrushSettings(bpy.types.Operator):
    """Toggle Setting For Active Brush"""
    bl_idname = "sculpt.brush_setting"
    bl_label = "Toggle Brush Setting"

    setting = bpy.props.StringProperty()

    def execute(self, context):

        setting = self.setting
        brush = context.tool_settings.sculpt.brush
       
        if setting == 'use_accumulate':
            value = brush.use_accumulate
            print(value)
            brush.use_accumulate = not value
        return {"FINISHED"}


class BrushSettingsMenu(bpy.types.Menu):
    bl_label = "Brush Settings"
    bl_idname = "sculpt.brush_settings_menu"

    def draw(self, context):
        layout = self.layout

        accumulate = layout.operator("sculpt.brush_setting", "Accumulate")
        accumulate.setting = 'use_accumulate'

def register():
    bpy.utils.register_class(BrushSettings)
    bpy.utils.register_class(BrushSettingsMenu)
    
def unregister():
    bpy.utils.unregister_class(BrushSettings)
    bpy.utils.unregister_class(BrushSettingsMenu)
   

if __name__ == "__main__":
    register()
    
    bpy.ops.wm.call_menu(name=BrushSettingsMenu.bl_idname)
########NEW FILE########
__FILENAME__ = vertex_count
import bpy

selected = [verts for verts in bpy.context.active_object.data.vertices if verts.selected]
print(len(selected))
########NEW FILE########
__FILENAME__ = object_add-subsurf
import bpy

scene = bpy.context.scene
selected = bpy.context.selected_objects
object = bpy.ops.object

for obj in selected:
    scene.objects.active = obj
    
    object.modifier_add(type="SUBSURF")
    
    for mod in obj.modifiers:
        if mod.type == "SUBSURF":
            bpy.context.object.modifiers[mod.name].levels = 2
            object.modifier_apply(apply_as="DATA", modifier=mod.name)
########NEW FILE########
__FILENAME__ = view3d_custom-menu
bl_info = {
        "name": "My Custom Menu",
        "category": "3D View",
        "author": "Jonathan Williamson"
        }        

import bpy

class customMenu(bpy.types.Menu):
    bl_label = "Custom Menu"
    bl_idname = "view3D.custom_menu"
    
    def draw(self, context):
        layout = self.layout
        
        layout.operator("mesh.primitive_cube_add")
        layout.operator("object.duplicate_move")
    
def register():
    bpy.utils.register_class(customMenu)
#    bpy.ops.wm.call_menu(name=customMenu.bl_idname)
    
def unregister():
    bpy.utils.unregister_class(customMenu)
    
if __name__ == "__main__":
    register()
########NEW FILE########
