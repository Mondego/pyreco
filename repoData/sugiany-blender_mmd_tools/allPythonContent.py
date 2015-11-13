__FILENAME__ = bpyutils
# -*- coding: utf-8 -*-

import bpy


class __EditMode:
    def __init__(self, obj):
        if not isinstance(obj, bpy.types.Object):
            raise ValueError
        self.__prevMode = obj.mode
        select_object(obj)
        if obj.mode != 'EIDT':
            bpy.ops.object.mode_set(mode='EDIT')

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        bpy.ops.object.mode_set(mode=self.__prevMode)
    

def select_object(obj):
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.scene.objects.active = obj
    obj.select=True


def edit_object(obj):
    """ Set the object interaction mode to 'EDIT'

    It is recommended to use 'edit_object' with 'with' statement like the following code.
    @code{.py}
    with edit_object:
        some functions...
    @endcode
    """
    return __EditMode(obj)

########NEW FILE########
__FILENAME__ = cycles_converter
# -*- coding: utf-8 -*-
import bpy
import mathutils

def __exposeNodeTreeInput(in_socket, name, default_value, node_input, shader):
    t = len(node_input.outputs)-1
    i = node_input.outputs[t]
    shader.links.new(in_socket, i)
    if default_value is not None:
        shader.inputs[t].default_value = default_value
    shader.inputs[t].name = name

def __exposeNodeTreeOutput(out_socket, name, node_output, shader):
    t = len(node_output.inputs)-1
    i = node_output.inputs[t]
    shader.links.new(i, out_socket)
    shader.outputs[t].name = name

def create_MMDAlphaShader():
    bpy.context.scene.render.engine = 'CYCLES'

    if 'MMDAlphaShader' in bpy.data.node_groups:
        return bpy.data.node_groups['MMDAlphaShader']

    shader = bpy.data.node_groups.new(name='MMDAlphaShader', type='ShaderNodeTree')

    node_input = shader.nodes.new('NodeGroupInput')
    node_output = shader.nodes.new('NodeGroupOutput')

    trans = shader.nodes.new('ShaderNodeBsdfTransparent')
    mix = shader.nodes.new('ShaderNodeMixShader')

    shader.links.new(mix.inputs[1], trans.outputs['BSDF'])

    __exposeNodeTreeInput(mix.inputs[2], 'Shader', None, node_input, shader)
    __exposeNodeTreeInput(mix.inputs['Fac'], 'Alpha', 1.0, node_input, shader)
    __exposeNodeTreeOutput(mix.outputs['Shader'], 'Shader', node_output, shader)

    return shader


def create_MMDBasicShader():
    bpy.context.scene.render.engine = 'CYCLES'

    if 'MMDBasicShader' in bpy.data.node_groups:
        return bpy.data.node_groups['MMDBasicShader']

    shader = bpy.data.node_groups.new(name='MMDBasicShader', type='ShaderNodeTree')

    node_input = shader.nodes.new('NodeGroupInput')
    node_output = shader.nodes.new('NodeGroupOutput')

    dif = shader.nodes.new('ShaderNodeBsdfDiffuse')
    glo = shader.nodes.new('ShaderNodeBsdfGlossy')
    mix = shader.nodes.new('ShaderNodeMixShader')

    shader.links.new(mix.inputs[1], dif.outputs['BSDF'])
    shader.links.new(mix.inputs[2], glo.outputs['BSDF'])

    __exposeNodeTreeInput(dif.inputs['Color'], 'diffuse', [1.0, 1.0, 1.0, 1.0], node_input, shader)
    __exposeNodeTreeInput(glo.inputs['Color'], 'glossy', [1.0, 1.0, 1.0, 1.0], node_input, shader)
    __exposeNodeTreeInput(glo.inputs['Roughness'], 'glossy_rough', 0.0, node_input, shader)
    __exposeNodeTreeInput(mix.inputs['Fac'], 'reflection', 0.02, node_input, shader)
    __exposeNodeTreeOutput(mix.outputs['Shader'], 'shader', node_output, shader)

    return shader

def convertToCyclesShader(obj):
    mmd_basic_shader_grp = create_MMDBasicShader()
    mmd_alpha_shader_grp = create_MMDAlphaShader()

    for i in obj.material_slots:
        if i.material.use_nodes:
            continue

        i.material.use_nodes = True

        for j in i.material.node_tree.nodes:
            print(j)
        if any(filter(lambda x: isinstance(x, bpy.types.ShaderNodeGroup) and  x.node_tree.name in ['MMDBasicShader', 'MMDAlphaShader'], i.material.node_tree.nodes)):
            continue


        i.material.node_tree.links.clear()
        shader = i.material.node_tree.nodes.new('ShaderNodeGroup')
        shader.node_tree = mmd_basic_shader_grp
        texture = None
        outplug = shader.outputs[0]

        for j in i.material.texture_slots:
            if j is not None and isinstance(j.texture, bpy.types.ImageTexture) and j.use:
                if j.texture_coords == 'UV':  # don't use sphere maps for now
                    texture = i.material.node_tree.nodes.new('ShaderNodeTexImage')
                    texture.image = j.texture.image

        if texture is not None or i.material.alpha < 1.0:
            alpha_shader = i.material.node_tree.nodes.new('ShaderNodeGroup')
            alpha_shader.node_tree = mmd_alpha_shader_grp
            i.material.node_tree.links.new(alpha_shader.inputs[0], outplug)
            outplug = alpha_shader.outputs[0]

        if texture is not None:
            if i.material.diffuse_color == mathutils.Color((1.0, 1.0, 1.0)):
                i.material.node_tree.links.new(shader.inputs[0], texture.outputs['Color'])
            else:
                mix_rgb = i.material.node_tree.nodes.new('ShaderNodeMixRGB')
                mix_rgb.blend_type = 'MULTIPLY'
                mix_rgb.inputs[0].default_value = 1.0
                mix_rgb.inputs[1].default_value = list(i.material.diffuse_color) + [1.0]
                i.material.node_tree.links.new(mix_rgb.inputs[2], texture.outputs['Color'])
                i.material.node_tree.links.new(shader.inputs[0], mix_rgb.outputs['Color'])
            if i.material.alpha == 1.0:
                i.material.node_tree.links.new(alpha_shader.inputs[1], texture.outputs['Alpha'])
            else:
                mix_alpha = i.material.node_tree.nodes.new('ShaderNodeMath')
                mix_alpha.operation = 'MULTIPLY'
                mix_alpha.inputs[0].default_value = i.material.alpha
                i.material.node_tree.links.new(mix_alpha.inputs[1], texture.outputs['Alpha'])
                i.material.node_tree.links.new(alpha_shader.inputs[1], mix_alpha.outputs['Value'])
        else:
            shader.inputs[0].default_value = list(i.material.diffuse_color) + [1.0]
            if i.material.alpha < 1.0:
                alpha_shader.inputs[1].default_value = i.material.alpha

        i.material.node_tree.links.new(i.material.node_tree.nodes['Material Output'].inputs['Surface'], outplug)

########NEW FILE########
__FILENAME__ = export_pmx
# -*- coding: utf-8 -*-
from . import pmx
from . import utils

import collections

import mathutils
import bpy
import bmesh
import copy


class PmxExporter:
    TO_PMX_MATRIX = mathutils.Matrix([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]])

    def __init__(self):
        self.__model = None
        self.__targetMesh = None

    @staticmethod
    def flipUV_V(uv):
        u, v = uv
        return [u, 1.0-v]

    @staticmethod
    def __getVerticesTable(mesh):
        r = []
        for bv in mesh.vertices:
            pv = pmx.Vertex()
            pv.co = bv.co
            pv.normal = bv.normal
            pv.uv = None

            weight = pmx.BoneWeight()
            weight.type = pmx.BoneWeight.BDEF1
            weight.bones = [-1]
            pv.weight = weight
            r.append(pv)
        return r

    @staticmethod
    def __getFaceTable(mesh):
        verticesTable = PmxExporter.__getVerticesTable(mesh)
        r = []
        for f, uv in zip(mesh.tessfaces, mesh.tessface_uv_textures.active.data):
            if len(f.vertices) != 3:
                raise Exception
            t = []
            for i in f.vertices:
                t.append(verticesTable[i])
            r.append((f, uv, t))
        return r

    @staticmethod
    def __convertFaceUVToVertexUV(vertex, uv, cloneVertexMap):
        if vertex.uv is None:
            vertex.uv = uv
        elif (vertex.uv[0] - uv[0])**2 + (vertex.uv[1] - uv[1])**2 > 0.0001:
            for i in cloneVertexMap[vertex]:
                if (i.uv[0] - uv[0])**2 + (i.uv[1] - uv[1])**2 < 0.0001:
                    return i
            n = copy.deepcopy(vertex)
            n.uv = uv
            cloneVertexMap[vertex].append(n)
            return n
        return vertex

    def __exportFaces(self):
        self.__materialIndexDict = collections.defaultdict(list)
        cloneVertexMap = collections.defaultdict(list)
        mesh = self.__targetMesh

        faceTable = self.__getFaceTable(mesh)
        for f, uv, vertices in faceTable:
            vertices[0] = self.__convertFaceUVToVertexUV(vertices[0], self.flipUV_V(uv.uv1), cloneVertexMap)
            vertices[1] = self.__convertFaceUVToVertexUV(vertices[1], self.flipUV_V(uv.uv2), cloneVertexMap)
            vertices[2] = self.__convertFaceUVToVertexUV(vertices[2], self.flipUV_V(uv.uv3), cloneVertexMap)

        verticesSet = set()
        for f, uv, vertices in faceTable:
            verticesSet.update(set(vertices))

        self.__model.vertices = list(verticesSet)
        for f, uv, vertices in faceTable:
            v1 = self.__model.vertices.index(vertices[0])
            v2 = self.__model.vertices.index(vertices[1])
            v3 = self.__model.vertices.index(vertices[2])
            self.__materialIndexDict[f.material_index].append([v1, v2, v3])

        for i in sorted(self.__materialIndexDict.keys()):
            self.__model.faces.extend(self.__materialIndexDict[i])

    def __exportTexture(self, texture):
        if not isinstance(texture, bpy.types.ImageTexture):
            return -1
        t = pmx.Texture()
        t.path = texture.image.filepath
        self.__model.textures.append(t)
        return len(self.__model.textures) - 1

    def __exportMaterials(self):
        mesh = self.__targetMesh
        textureList = []
        for m_index, i in enumerate(mesh.materials):
            num_faces = len(self.__materialIndexDict[m_index])
            if num_faces == 0:
                continue
            p_mat = pmx.Material()
            p_mat.name = i.name
            p_mat.name_e = i.name
            p_mat.diffuse = list(i.diffuse_color) + [i.alpha]
            p_mat.ambient = i.ambient_color or [0.5, 0.5, 0.5]
            p_mat.specular = list(i.specular_color) + [i.specular_alpha]
            p_mat.edge_color = [0.25, 0.3, 0.5, 0.5]
            p_mat.vertex_count = num_faces * 3
            if len(i.texture_slots) > 0:
                tex = i.texture_slots[0].texture
                index = -1
                if tex not in textureList:
                    index = self.__exportTexture(tex)
                    textureList.append(tex)
                else:
                    index = textureList.index(tex)
                p_mat.texture = index
            self.__model.materials.append(p_mat)

    def __exportBones(self):
        arm = self.__armature
        utils.enterEditMode(arm)
        boneMap = {}
        pmx_bones = []
        pose_bones = arm.pose.bones
        for bone in arm.data.edit_bones:
            pmx_bone = pmx.Bone()
            p_bone = pose_bones[bone.name]
            if p_bone.mmd_bone_name_j != '':
                pmx_bone.name = p_bone.mmd_bone_name_j
            else:
                pmx_bone.name = bone.name
            pmx_bone_e = p_bone.mmd_bone_name_e or ''
            pmx_bone.location = mathutils.Vector(bone.head) * self.__scale * self.TO_PMX_MATRIX
            pmx_bone.parent = bone.parent
            pmx_bones.append(pmx_bone)
            boneMap[bone] = pmx_bone

            if len(bone.children) == 0 and not p_bone.is_mmd_tip_bone:
                pmx_tip_bone = pmx.Bone()
                pmx_tip_bone.name = 'tip_' + bone.name
                pmx_tip_bone.location =  mathutils.Vector(bone.tail) * self.__scale * self.TO_PMX_MATRIX
                pmx_tip_bone.parent = bone
                pmx_bones.append(pmx_tip_bone)
                pmx_bone.displayConnection = pmx_tip_bone
            elif len(bone.children) > 0:
                pmx_bone.displayConnection = sorted(bone.children, key=lambda x: 1 if pose_bones[x.name].is_mmd_tip_bone else 0)[0]

        for i in pmx_bones:
            if i.parent is not None:
                i.parent = pmx_bones.index(boneMap[i.parent])
            if isinstance(i.displayConnection, pmx.Bone):
                i.displayConnection = pmx_bones.index(i.displayConnection)
            elif isinstance(i.displayConnection, bpy.types.EditBone):
                i.displayConnection = pmx_bones.index(boneMap[i.displayConnection])

        self.__model.bones = pmx_bones
        bpy.ops.object.mode_set(mode='OBJECT')


    @staticmethod
    def __triangulate(mesh):
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()

    def execute(self, **args):
        self.__model = pmx.Model()
        self.__model.name = 'test'
        self.__model.name_e = 'test eng'

        self.__model.comment = 'exported by mmd_tools'

        target = args['mesh']
        self.__armature = args['armature']
        self.__scale = 1.0/float(args.get('scale', 1.0))


        mesh = target.to_mesh(bpy.context.scene, True, 'PREVIEW', False)
        mesh.transform(self.TO_PMX_MATRIX*self.__scale)
        self.__triangulate(mesh)
        mesh.update(calc_tessface=True)

        self.__targetMesh = mesh
        outpath = args['path']


        self.__exportFaces()
        self.__exportMaterials()
        self.__exportBones()
        pmx.save(outpath, self.__model)

########NEW FILE########
__FILENAME__ = import_pmd
# -*- coding: utf-8 -*-

from . import import_pmx
from . import pmd
from . import pmx

import mathutils

import os
import re
import copy
import logging


def import_pmd(**kwargs):
    """ Import pmd file
    """
    target_path = kwargs['filepath']
    pmd_model = pmd.load(target_path)


    logging.info('')
    logging.info('****************************************')
    logging.info(' mmd_tools.import_pmd module')
    logging.info('----------------------------------------')
    logging.info(' Start to convert pmx data into pmd data')
    logging.info('              by the mmd_tools.pmd modlue.')
    logging.info('')

    pmx_model = pmx.Model()

    pmx_model.name = pmd_model.name
    pmd_model.name_e = pmd_model.name_e
    pmx_model.comment = pmd_model.comment
    pmd_model.comment_e = pmd_model.comment_e

    pmx_model.vertices = []

    # convert vertices
    logging.info('')
    logging.info('------------------------------')
    logging.info(' Convert Vertices')
    logging.info('------------------------------')
    for v in pmd_model.vertices:
        pmx_v = pmx.Vertex()
        pmx_v.co = v.position
        pmx_v.normal = v.normal
        pmx_v.uv = v.uv
        pmx_v.additional_uvs= []
        pmx_v.edge_scale = 1

        weight = pmx.BoneWeight()
        if v.bones[0] != v.bones[1]:
            weight.type = pmx.BoneWeight.BDEF2
            weight.bones = v.bones
            weight.weights = [float(v.weight)/100.0]
        else:
            weight.type = pmx.BoneWeight.BDEF1
            weight.bones = [v.bones[0]]
            weight.weights = [float(v.weight)/100.0]

        pmx_v.weight = weight

        pmx_model.vertices.append(pmx_v)
    logging.info('----- Converted %d vertices', len(pmx_model.vertices))

    logging.info('')
    logging.info('------------------------------')
    logging.info(' Convert Faces')
    logging.info('------------------------------')
    for f in pmd_model.faces:
        pmx_model.faces.append(f)
    logging.info('----- Converted %d faces', len(pmx_model.faces))

    knee_bones = []

    logging.info('')
    logging.info('------------------------------')
    logging.info(' Convert Bones')
    logging.info('------------------------------')
    for i, bone in enumerate(pmd_model.bones):
        pmx_bone = pmx.Bone()
        pmx_bone.name = bone.name
        pmx_bone.location = bone.position
        pmx_bone.parent = bone.parent
        if bone.type != 9:
            pmx_bone.displayConnection = bone.tail_bone
        else:
            pmx_bone.displayConnection = -1
        if pmx_bone.displayConnection <= 0:
            pmx_bone.displayConnection = [0.0, 0.0, 0.0]
        pmx_bone.isIK = False
        if bone.type == 0:
            pmx_bone.isMovable = False
        elif bone.type == 1:
            pass
        elif bone.type == 2:
            pmx_bone.transform_order = 1
        elif bone.type == 4:
            pmx_bone.isMovable = False
        elif bone.type == 5:
            pmx_bone.hasAdditionalRotate = True
            pmx_bone.additionalTransform = (bone.ik_bone, 1.0)
        elif bone.type == 7:
            pmx_bone.visible = False
        elif bone.type == 9:
            pmx_bone.hasAdditionalRotate = True
            pmx_bone.additionalTransform = (bone.tail_bone, float(bone.ik_bone)/100.0)

        if bone.type >= 4:
            pmx_bone.transform_order = 2

        pmx_model.bones.append(pmx_bone)

        if re.search(u'ひざ$', pmx_bone.name):
            knee_bones.append(i)

    for i in pmx_model.bones:
        if i.parent != -1 and pmd_model.bones[i.parent].type == 2:
            i.transform_order = 1
    logging.info('----- Converted %d boness', len(pmx_model.bones))

    logging.info('')
    logging.info('------------------------------')
    logging.info(' Convert IKs')
    logging.info('------------------------------')
    applied_ik_bones = []
    for ik in pmd_model.iks:
        if ik.bone in applied_ik_bones:
            logging.info('The bone %s is targeted by two or more IK bones.', pmx_model.bones[ik.bone].name)
            b = pmx_model.bones[ik.bone]
            t = copy.deepcopy(b)
            t.name += '+'
            t.parent = ik.bone
            t.ik_links = []
            pmx_model.bones.append(t)
            ik.bone = len(pmx_model.bones) - 1
            logging.info('Duplicate the bone: %s -> %s', b.name, t.name)
        pmx_bone = pmx_model.bones[ik.bone]
        logging.debug('Add IK settings to the bone %s', pmx_bone.name)
        pmx_bone.isIK = True
        pmx_bone.target = ik.target_bone
        pmx_bone.loopCount = ik.ik_chain
        for i in ik.ik_child_bones:
            ik_link = pmx.IKLink()
            ik_link.target = i
            if i in knee_bones:
                ik_link.maximumAngle = [-0.5, 0.0, 0.0]
                ik_link.minimumAngle = [-180.0, 0.0, 0.0]
                logging.info('  Add knee constraints to %s', i)
            logging.debug('  IKLink: %s(index: %d)', pmx_model.bones[i].name, i)
            pmx_bone.ik_links.append(ik_link)
        applied_ik_bones.append(ik.bone)
    logging.info('----- Converted %d bones', len(pmd_model.iks))

    texture_map = {}
    logging.info('')
    logging.info('------------------------------')
    logging.info(' Convert Materials')
    logging.info('------------------------------')
    for i, mat in enumerate(pmd_model.materials):
        pmx_mat = pmx.Material()
        pmx_mat.name = 'Material%d'%i
        pmx_mat.diffuse = mat.diffuse
        pmx_mat.specular = mat.specular + [mat.specular_intensity]
        pmx_mat.ambient = mat.ambient
        pmx_mat.enabled_self_shadow = True # pmd doesn't support this
        pmx_mat.enabled_self_shadow_map = abs(mat.diffuse[3] - 0.98) > 1e-7 # consider precision error
        pmx_mat.vertex_count = mat.vertex_count
        if len(mat.texture_path) > 0:
            tex_path = mat.texture_path
            if tex_path not in texture_map:
                logging.info('  Create pmx.Texture %s', tex_path)
                tex = pmx.Texture()
                tex.path = os.path.normpath(os.path.join(os.path.dirname(target_path), tex_path))
                pmx_model.textures.append(tex)
                texture_map[tex_path] = len(pmx_model.textures) - 1
            pmx_mat.texture = texture_map[tex_path]
        if len(mat.sphere_path) > 0:
            tex_path = mat.sphere_path
            if tex_path not in texture_map:
                logging.info('  Create pmx.Texture %s', tex_path)
                tex = pmx.Texture()
                tex.path = os.path.normpath(os.path.join(os.path.dirname(target_path), tex_path))
                pmx_model.textures.append(tex)
                texture_map[tex_path] = len(pmx_model.textures) - 1
            pmx_mat.sphere_texture = texture_map[tex_path]
            pmx_mat.sphere_texture_mode = mat.sphere_mode
        pmx_model.materials.append(pmx_mat)
    logging.info('----- Converted %d materials', len(pmx_model.materials))

    logging.info('')
    logging.info('------------------------------')
    logging.info(' Convert Morphs')
    logging.info('------------------------------')
    t = list(filter(lambda x: x.type == 0, pmd_model.morphs))
    if len(t) == 0:
        logging.error('Not found the base morph')
        logging.error('Skip converting vertex morphs.')
    else:
        if len(t) > 1:
            logging.warning('Found two or more base morphs.')
        vertex_map = []
        for i in t[0].data:
            vertex_map.append(i.index)

        for morph in pmd_model.morphs:
            logging.debug('Vertex Morph: %s', morph.name)
            if morph.type == 0:
                continue
            pmx_morph = pmx.VertexMorph(morph.name, '', morph.type)
            for i in morph.data:
                mo = pmx.VertexMorphOffset()
                mo.index = vertex_map[i.index]
                mo.offset = i.offset
                pmx_morph.offsets.append(mo)
            pmx_model.morphs.append(pmx_morph)
    logging.info('----- Converted %d morphs', len(pmx_model.morphs))

    logging.info('')
    logging.info('------------------------------')
    logging.info(' Convert Rigid bodies')
    logging.info('------------------------------')
    for rigid in pmd_model.rigid_bodies:
        pmx_rigid = pmx.Rigid()

        pmx_rigid.name = rigid.name

        pmx_rigid.bone = rigid.bone
        pmx_rigid.collision_group_number = rigid.collision_group_number
        pmx_rigid.collision_group_mask = rigid.collision_group_mask
        pmx_rigid.type = rigid.type

        pmx_rigid.size = rigid.size

        # a location parameter of pmd.RigidBody is the offset from the relational bone or the center bone.
        if rigid.bone == -1:
            t = 0
        else:
            t = rigid.bone
        pmx_rigid.location = mathutils.Vector(pmx_model.bones[t].location) + mathutils.Vector(rigid.location)
        pmx_rigid.rotation = rigid.rotation

        pmx_rigid.mass = rigid.mass
        pmx_rigid.velocity_attenuation = rigid.velocity_attenuation
        pmx_rigid.rotation_attenuation = rigid.rotation_attenuation
        pmx_rigid.bounce = rigid.bounce
        pmx_rigid.friction = rigid.friction
        pmx_rigid.mode = rigid.mode

        pmx_model.rigids.append(pmx_rigid)
    logging.info('----- Converted %d rigid bodies', len(pmx_model.rigids))

    logging.info('')
    logging.info('------------------------------')
    logging.info(' Convert Joints')
    logging.info('------------------------------')
    for joint in pmd_model.joints:
        pmx_joint = pmx.Joint()

        pmx_joint.name = joint.name
        pmx_joint.src_rigid = joint.src_rigid
        pmx_joint.dest_rigid = joint.dest_rigid

        pmx_joint.location = joint.location
        pmx_joint.rotation = joint.rotation

        pmx_joint.maximum_location = joint.minimum_location
        pmx_joint.minimum_location = joint.maximum_location
        pmx_joint.maximum_rotation = joint.minimum_rotation
        pmx_joint.minimum_rotation = joint.maximum_rotation

        pmx_joint.spring_constant = joint.spring_constant
        pmx_joint.spring_rotation_constant = joint.spring_rotation_constant

        pmx_model.joints.append(pmx_joint)
    logging.info('----- Converted %d joints', len(pmx_model.joints))

    logging.info(' Finish converting pmd into pmx.')
    logging.info('----------------------------------------')
    logging.info(' mmd_tools.import_pmd module')
    logging.info('****************************************')

    importer = import_pmx.PMXImporter()
    kwargs['pmx'] = pmx_model
    importer.execute(**kwargs)

########NEW FILE########
__FILENAME__ = import_pmx
# -*- coding: utf-8 -*-
from . import pmx
from . import utils
from . import bpyutils

import math

import bpy
import os
import mathutils
import collections
import logging
import time

class PMXImporter:
    TO_BLE_MATRIX = mathutils.Matrix([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]])

    def __init__(self):
        self.__model = None
        self.__targetScene = bpy.context.scene

        self.__scale = None

        self.__root = None
        self.__armObj = None
        self.__meshObj = None

        self.__vertexTable = None
        self.__vertexGroupTable = None
        self.__textureTable = None

        self.__boneTable = []
        self.__rigidTable = []
        self.__nonCollisionJointTable = None
        self.__jointTable = []

        self.__materialFaceCountTable = None
        self.__nonCollisionConstraints = []

        # object groups
        self.__allObjGroup = None    # a group which contains all objects created for the target model by mmd_tools.
        self.__mainObjGroup = None    # a group which contains armature and mesh objects.
        self.__rigidObjGroup = None  # a group which contains objects of rigid bodies imported from a pmx model.
        self.__jointObjGroup = None  # a group which contains objects of joints imported from a pmx model.
        self.__tempObjGroup = None   # a group which contains temporary objects.

    @staticmethod
    def flipUV_V(uv):
        u, v = uv
        return [u, 1.0-v]

    def __getMaterialIndexFromFaceIndex(self, face_index):
        count = 0
        for i, c in enumerate(self.__materialFaceCountTable):
            if face_index < count + c:
                return i
            count += c
        raise Exception('invalid face index.')

    def __createObjects(self):
        """ Create main objects and link them to scene.
        """
        pmxModel = self.__model

        self.__root = bpy.data.objects.new(name=pmxModel.name, object_data=None)
        self.__targetScene.objects.link(self.__root)

        mesh = bpy.data.meshes.new(name=pmxModel.name)
        self.__meshObj = bpy.data.objects.new(name=pmxModel.name+'_mesh', object_data=mesh)

        arm = bpy.data.armatures.new(name=pmxModel.name)
        self.__armObj = bpy.data.objects.new(name=pmxModel.name+'_arm', object_data=arm)
        self.__meshObj.parent = self.__armObj

        self.__targetScene.objects.link(self.__meshObj)
        self.__targetScene.objects.link(self.__armObj)

        self.__armObj.parent = self.__root

        self.__allObjGroup.objects.link(self.__root)
        self.__allObjGroup.objects.link(self.__armObj)
        self.__allObjGroup.objects.link(self.__meshObj)
        self.__mainObjGroup.objects.link(self.__armObj)
        self.__mainObjGroup.objects.link(self.__meshObj)

    def __createGroups(self):
        pmxModel = self.__model
        self.__mainObjGroup = bpy.data.groups.new(name='mmd_tools.' + pmxModel.name)
        logging.debug('Create main group: %s', self.__mainObjGroup.name)
        self.__allObjGroup = bpy.data.groups.new(name='mmd_tools.' + pmxModel.name + '_all')
        logging.debug('Create all group: %s', self.__allObjGroup.name)
        self.__rigidObjGroup = bpy.data.groups.new(name='mmd_tools.' + pmxModel.name + '_rigids')
        logging.debug('Create rigid group: %s', self.__rigidObjGroup.name)
        self.__jointObjGroup = bpy.data.groups.new(name='mmd_tools.' + pmxModel.name + '_joints')
        logging.debug('Create joint group: %s', self.__jointObjGroup.name)
        self.__tempObjGroup = bpy.data.groups.new(name='mmd_tools.' + pmxModel.name + '_temp')
        logging.debug('Create temporary group: %s', self.__tempObjGroup.name)

    def __importVertexGroup(self):
        self.__vertexGroupTable = []
        for i in self.__model.bones:
            self.__vertexGroupTable.append(self.__meshObj.vertex_groups.new(name=i.name))

    def __importVertices(self):
        self.__importVertexGroup()

        pmxModel = self.__model
        mesh = self.__meshObj.data

        mesh.vertices.add(count=len(self.__model.vertices))
        for i, pv in enumerate(pmxModel.vertices):
            bv = mesh.vertices[i]

            bv.co = mathutils.Vector(pv.co) * self.TO_BLE_MATRIX * self.__scale
            bv.normal = pv.normal

            if isinstance(pv.weight.weights, pmx.BoneWeightSDEF):
                self.__vertexGroupTable[pv.weight.bones[0]].add(index=[i], weight=pv.weight.weights.weight, type='REPLACE')
                self.__vertexGroupTable[pv.weight.bones[1]].add(index=[i], weight=1.0-pv.weight.weights.weight, type='REPLACE')
            elif len(pv.weight.bones) == 1:
                self.__vertexGroupTable[pv.weight.bones[0]].add(index=[i], weight=1.0, type='REPLACE')
            elif len(pv.weight.bones) == 2:
                self.__vertexGroupTable[pv.weight.bones[0]].add(index=[i], weight=pv.weight.weights[0], type='REPLACE')
                self.__vertexGroupTable[pv.weight.bones[1]].add(index=[i], weight=1.0-pv.weight.weights[0], type='REPLACE')
            elif len(pv.weight.bones) == 4:
                self.__vertexGroupTable[pv.weight.bones[0]].add(index=[i], weight=pv.weight.weights[0], type='REPLACE')
                self.__vertexGroupTable[pv.weight.bones[1]].add(index=[i], weight=pv.weight.weights[1], type='REPLACE')
                self.__vertexGroupTable[pv.weight.bones[2]].add(index=[i], weight=pv.weight.weights[2], type='REPLACE')
                self.__vertexGroupTable[pv.weight.bones[3]].add(index=[i], weight=pv.weight.weights[3], type='REPLACE')
            else:
                raise Exception('unkown bone weight type.')

    def __importTextures(self):
        pmxModel = self.__model

        self.__textureTable = []
        for i in pmxModel.textures:
            name = os.path.basename(i.path.replace('\\', os.path.sep)).split('.')[0]
            tex = bpy.data.textures.new(name=name, type='IMAGE')
            try:
                tex.image = bpy.data.images.load(filepath=bpy.path.resolve_ncase(path=i.path))
            except Exception:
                logging.warning('failed to load %s', str(i.path))
            self.__textureTable.append(tex)

    def __createEditBones(self, obj, pmx_bones):
        """ create EditBones from pmx file data.
        @return the list of bone names which can be accessed by the bone index of pmx data.
        """
        editBoneTable = []
        nameTable = []
        dependency_cycle_ik_bones = []
        for i, p_bone in enumerate(pmx_bones):
            if p_bone.isIK:
                if p_bone.target != -1:
                    t = pmx_bones[p_bone.target]
                    if p_bone.parent == t.parent:
                        dependency_cycle_ik_bones.append(i)

        with bpyutils.edit_object(obj):
            for i in pmx_bones:
                bone = obj.data.edit_bones.new(name=i.name)
                loc = mathutils.Vector(i.location) * self.__scale * self.TO_BLE_MATRIX
                bone.head = loc
                editBoneTable.append(bone)
                nameTable.append(bone.name)

            for i, (b_bone, m_bone) in enumerate(zip(editBoneTable, pmx_bones)):
                if m_bone.parent != -1:
                    if i not in dependency_cycle_ik_bones:
                        b_bone.parent = editBoneTable[m_bone.parent]
                    else:
                        b_bone.parent = editBoneTable[m_bone.parent].parent

            for b_bone, m_bone in zip(editBoneTable, pmx_bones):
                if isinstance(m_bone.displayConnection, int):
                    if m_bone.displayConnection != -1:
                        b_bone.tail = editBoneTable[m_bone.displayConnection].head
                    else:
                        b_bone.tail = b_bone.head
                else:
                    loc = mathutils.Vector(m_bone.displayConnection) * self.TO_BLE_MATRIX * self.__scale
                    b_bone.tail = b_bone.head + loc

            for b_bone in editBoneTable:
                # Set the length of too short bones to 1 because Blender delete them.
                if b_bone.length  < 0.001:
                    loc = mathutils.Vector([0, 0, 1]) * self.__scale
                    b_bone.tail = b_bone.head + loc

            for b_bone, m_bone in zip(editBoneTable, pmx_bones):
                if b_bone.parent is not None and b_bone.parent.tail == b_bone.head:
                    if not m_bone.isMovable:
                        b_bone.use_connect = True

        return nameTable

    def __sortPoseBonesByBoneIndex(self, pose_bones, bone_names):
        r = []
        for i in bone_names:
            r.append(pose_bones[i])
        return r

    def __applyIk(self, index, pmx_bone, pose_bones):
        """ create a IK bone constraint
         If the IK bone and the target bone is separated, a dummy IK target bone is created as a child of the IK bone.
         @param index the bone index
         @param pmx_bone pmx.Bone
         @param pose_bones the list of PoseBones sorted by the bone index
        """

        ik_bone = pose_bones[pmx_bone.target].parent
        target_bone = pose_bones[index]

        if (mathutils.Vector(ik_bone.tail) - mathutils.Vector(target_bone.head)).length > 0.001:
            logging.info('Found a seperated IK constraint: IK: %s, Target: %s', ik_bone.name, target_bone.name)
            with bpyutils.edit_object(self.__armObj):
                s_bone = self.__armObj.data.edit_bones.new(name='shadow')
                logging.info('  Create a proxy bone: %s', s_bone.name)
                s_bone.head = ik_bone.tail
                s_bone.tail = s_bone.head + mathutils.Vector([0, 0, 1])
                s_bone.layers = (False, False, False, False, False, False, False, False, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False)
                s_bone.parent = self.__armObj.data.edit_bones[target_bone.name]
                logging.info('  Set parent: %s -> %s', target_bone.name, s_bone.name)
                # Must not access to EditBones from outside of the 'with' section.
                s_bone_name = s_bone.name

            logging.info('  Use %s as IK target bone instead of %s', s_bone_name, target_bone.name)
            target_bone = self.__armObj.pose.bones[s_bone_name]
            target_bone.is_mmd_shadow_bone = True

        ikConst = ik_bone.constraints.new('IK')
        ikConst.chain_count = len(pmx_bone.ik_links)
        ikConst.target = self.__armObj
        ikConst.subtarget = target_bone.name
        if pmx_bone.isRotatable and not pmx_bone.isMovable :
            ikConst.use_location = pmx_bone.isMovable
            ikConst.use_rotation = pmx_bone.isRotatable
        for i in pmx_bone.ik_links:
            if i.maximumAngle is not None:
                bone = pose_bones[i.target]
                bone.use_ik_limit_x = True
                bone.use_ik_limit_y = True
                bone.use_ik_limit_z = True
                bone.ik_max_x = -i.minimumAngle[0]
                bone.ik_max_y = i.maximumAngle[1]
                bone.ik_max_z = i.maximumAngle[2]
                bone.ik_min_x = -i.maximumAngle[0]
                bone.ik_min_y = i.minimumAngle[1]
                bone.ik_min_z = i.minimumAngle[2]

    @staticmethod
    def __findNoneAdditionalBone(target, pose_bones, visited_bones=None):
        if visited_bones is None:
            visited_bones = []
        if target in visited_bones:
            raise ValueError('Detected cyclic dependency.')
        for i in filter(lambda x: x.type == 'CHILD_OF', target.constraints):
            if i.subtarget != target.parent.name:
                return PMXImporter.__findNoneAdditionalBone(pose_bones[i.subtarget], pose_bones, visited_bones)
        return target

    def __applyAdditionalTransform(self, obj, src, dest, influence, pose_bones, rotation=False, location=False):
        """ apply additional transform to the bone.
         @param obj the object of the target armature
         @param src the PoseBone that apply the transform to another bone.
         @param dest the PoseBone that another bone apply the transform to.
        """
        if not rotation and not location:
            return
        bone_name = None

        # If src has been applied the additional transform by another bone,
        # copy the constraint of it to dest.
        src = self.__findNoneAdditionalBone(src, pose_bones)

        with bpyutils.edit_object(obj):
            src_bone = obj.data.edit_bones[src.name]
            s_bone = obj.data.edit_bones.new(name='shadow')
            s_bone.head = src_bone.head
            s_bone.tail = src_bone.tail
            s_bone.parent = src_bone.parent
            #s_bone.use_connect = src_bone.use_connect
            s_bone.layers = (False, False, False, False, False, False, False, False, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False)
            s_bone.use_inherit_rotation = False
            s_bone.use_local_location = True
            s_bone.use_inherit_scale = False
            bone_name = s_bone.name

            dest_bone = obj.data.edit_bones[dest.name]
            dest_bone.use_inherit_rotation = not rotation
            dest_bone.use_local_location = not location

        p_bone = obj.pose.bones[bone_name]
        p_bone.is_mmd_shadow_bone = True

        if rotation:
            c = p_bone.constraints.new('COPY_ROTATION')
            c.target = obj
            c.subtarget = src.name
            c.target_space = 'LOCAL'
            c.owner_space = 'LOCAL'

            if influence > 0:
                c.influence = influence
            else:
                c.influence = -influence
                c.invert_x = True
                c.invert_y = True
                c.invert_z = True

        if location:
            c = p_bone.constraints.new('COPY_LOCATION')
            c.target = obj
            c.subtarget = src.name
            c.target_space = 'LOCAL'
            c.owner_space = 'LOCAL'

            if influence > 0:
                c.influence = influence
            else:
                c.influence = -influence
                c.invert_x = True
                c.invert_y = True
                c.invert_z = True

        c = dest.constraints.new('CHILD_OF')

        c.target = obj
        c.subtarget = p_bone.name
        c.use_location_x = location
        c.use_location_y = location
        c.use_location_z = location
        c.use_rotation_x = rotation
        c.use_rotation_y = rotation
        c.use_rotation_z = rotation
        c.use_scale_x = False
        c.use_scale_y = False
        c.use_scale_z = False
        c.inverse_matrix = mathutils.Matrix(src.matrix).inverted()

        if dest.parent is not None:
            parent = dest.parent
            c = dest.constraints.new('CHILD_OF')
            c.target = obj
            c.subtarget = parent.name
            c.use_location_x = False
            c.use_location_y = False
            c.use_location_z = False
            c.use_scale_x = False
            c.use_scale_y = False
            c.use_scale_z = False
            c.inverse_matrix = mathutils.Matrix(parent.matrix).inverted()

    def __importBones(self):
        pmxModel = self.__model

        boneNameTable = self.__createEditBones(self.__armObj, pmxModel.bones)
        pose_bones = self.__sortPoseBonesByBoneIndex(self.__armObj.pose.bones, boneNameTable)
        self.__boneTable = pose_bones
        for i, p_bone in sorted(enumerate(pmxModel.bones), key=lambda x: x[1].transform_order):
            b_bone = pose_bones[i]
            b_bone.mmd_bone_name_e = p_bone.name_e

            if not p_bone.isRotatable:
                b_bone.lock_rotation = [True, True, True]

            if not p_bone.isMovable:
                b_bone.lock_location =[True, True, True]

            if p_bone.isIK:
                if p_bone.target != -1:
                    self.__applyIk(i, p_bone, pose_bones)

            if p_bone.hasAdditionalRotate or p_bone.hasAdditionalLocation:
                bone_index, influ = p_bone.additionalTransform
                src_bone = pmxModel.bones[bone_index]
                self.__applyAdditionalTransform(
                    self.__armObj,
                    pose_bones[bone_index],
                    b_bone,
                    influ,
                    self.__armObj.pose.bones,
                    p_bone.hasAdditionalRotate,
                    p_bone.hasAdditionalLocation
                    )

            if p_bone.localCoordinate is not None:
                b_bone.mmd_enabled_local_axis = True
                b_bone.mmd_local_axis_x = p_bone.localCoordinate.x_axis
                b_bone.mmd_local_axis_z = p_bone.localCoordinate.z_axis

            if len(b_bone.children) == 0:
                b_bone.is_mmd_tip_bone = True
                b_bone.lock_rotation = [True, True, True]
                b_bone.lock_location = [True, True, True]
                b_bone.lock_scale = [True, True, True]
                b_bone.bone.hide = True

    def __importRigids(self):
        self.__rigidTable = []
        self.__nonCollisionJointTable = {}
        start_time = time.time()
        collisionGroups = []
        for i in range(16):
            collisionGroups.append([])
        for rigid in self.__model.rigids:
            if self.__onlyCollisions and rigid.mode != pmx.Rigid.MODE_STATIC:
                continue

            loc = mathutils.Vector(rigid.location) * self.TO_BLE_MATRIX * self.__scale
            rot = mathutils.Vector(rigid.rotation) * self.TO_BLE_MATRIX * -1
            rigid_type = None
            if rigid.type == pmx.Rigid.TYPE_SPHERE:
                bpy.ops.mesh.primitive_uv_sphere_add(
                    segments=16,
                    ring_count=8,
                    size=1,
                    view_align=False,
                    enter_editmode=False
                    )
                size = mathutils.Vector([1,1,1]) * rigid.size[0]
                rigid_type = 'SPHERE'
                bpy.ops.object.shade_smooth()
            elif rigid.type == pmx.Rigid.TYPE_BOX:
                bpy.ops.mesh.primitive_cube_add(
                    view_align=False,
                    enter_editmode=False
                    )
                size = mathutils.Vector(rigid.size) * self.TO_BLE_MATRIX
                rigid_type = 'BOX'
            elif rigid.type == pmx.Rigid.TYPE_CAPSULE:
                obj = utils.makeCapsule(radius=rigid.size[0], height=rigid.size[1])
                size = mathutils.Vector([1,1,1])
                rigid_type = 'CAPSULE'
                bpy.ops.object.shade_smooth()
            else:
                raise Exception('Invalid rigid type')

            if rigid.type != pmx.Rigid.TYPE_CAPSULE:
                obj = bpy.context.selected_objects[0]
            obj.name = rigid.name
            obj.scale = size * self.__scale
            obj.hide_render = True
            obj.draw_type = 'WIRE'
            obj.is_mmd_rigid = True
            self.__rigidObjGroup.objects.link(obj)
            utils.selectAObject(obj)
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            obj.location = loc
            obj.rotation_euler = rot
            bpy.ops.rigidbody.object_add(type='ACTIVE')
            if rigid.mode == pmx.Rigid.MODE_STATIC and rigid.bone is not None:
                bpy.ops.object.modifier_add(type='COLLISION')
                utils.setParentToBone(obj, self.__armObj, self.__boneTable[rigid.bone].name)
            elif rigid.bone is not None:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select = True
                bpy.context.scene.objects.active = self.__root
                bpy.ops.object.parent_set(type='OBJECT', xmirror=False, keep_transform=True)

                target_bone = self.__boneTable[rigid.bone]
                empty = bpy.data.objects.new(
                    'mmd_bonetrack',
                    None)
                bpy.context.scene.objects.link(empty)
                empty.location = target_bone.tail
                empty.empty_draw_size = 0.5 * self.__scale
                empty.empty_draw_type = 'ARROWS'
                empty.is_mmd_rigid_track_target = True
                self.__tempObjGroup.objects.link(empty)

                utils.selectAObject(empty)
                bpy.context.scene.objects.active = obj
                bpy.ops.object.parent_set(type='OBJECT', xmirror=False, keep_transform=False)

                empty.hide = True


                for i in target_bone.constraints:
                    if i.type == 'IK':
                        i.influence = 0
                const = target_bone.constraints.new('DAMPED_TRACK')
                const.target = empty
            else:
                obj.parent = self.__armObj
                bpy.ops.object.select_all(action='DESELECT')
                obj.select = True

            obj.rigid_body.collision_shape = rigid_type
            group_flags = []
            rb = obj.rigid_body
            rb.friction = rigid.friction
            rb.mass = rigid.mass
            rb.angular_damping = rigid.rotation_attenuation
            rb.linear_damping = rigid.velocity_attenuation
            rb.restitution = rigid.bounce
            if rigid.mode == pmx.Rigid.MODE_STATIC:
                rb.kinematic = True

            for i in range(16):
                if rigid.collision_group_mask & (1<<i) == 0:
                    for j in collisionGroups[i]:
                        s = time.time()
                        self.__makeNonCollisionConstraint(obj, j)

            collisionGroups[rigid.collision_group_number].append(obj)
            self.__rigidTable.append(obj)
        logging.debug('Finished importing rigid bodies in %f seconds.', time.time() - start_time)


    def __getRigidRange(self, obj):
        return (mathutils.Vector(obj.bound_box[0]) - mathutils.Vector(obj.bound_box[6])).length

    def __makeNonCollisionConstraint(self, obj_a, obj_b):
        if (mathutils.Vector(obj_a.location) - mathutils.Vector(obj_b.location)).length > self.__distance_of_ignore_collisions * (self.__getRigidRange(obj_a) + self.__getRigidRange(obj_b)):
            return
        t = bpy.data.objects.new(
            'ncc.%d'%len(self.__nonCollisionConstraints),
            None)
        bpy.context.scene.objects.link(t)
        t.location = [0, 0, 0]
        t.empty_draw_size = 0.5 * self.__scale
        t.empty_draw_type = 'ARROWS'
        t.is_mmd_non_collision_constraint = True
        t.hide_render = True
        t.parent = self.__root
        utils.selectAObject(t)
        bpy.ops.rigidbody.constraint_add(type='GENERIC')
        rb = t.rigid_body_constraint
        rb.disable_collisions = True
        rb.object1 = obj_a
        rb.object2 = obj_b
        self.__nonCollisionConstraints.append(t)
        self.__nonCollisionJointTable[frozenset((obj_a, obj_b))] = t
        self.__tempObjGroup.objects.link(t)

    def __makeSpring(self, target, base_obj, spring_stiffness):
        utils.selectAObject(target)
        bpy.ops.object.duplicate()
        spring_target = bpy.context.scene.objects.active
        spring_target.is_mmd_spring_goal = True
        spring_target.rigid_body.kinematic = True
        spring_target.rigid_body.collision_groups = (False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True)
        bpy.context.scene.objects.active = base_obj
        bpy.ops.object.parent_set(type='OBJECT', xmirror=False, keep_transform=True)
        self.__rigidObjGroup.objects.unlink(spring_target)
        self.__tempObjGroup.objects.link(spring_target)

        obj = bpy.data.objects.new(
            'S.'+target.name,
            None)
        bpy.context.scene.objects.link(obj)
        obj.location = target.location
        obj.empty_draw_size = 0.5 * self.__scale
        obj.empty_draw_type = 'ARROWS'
        obj.hide_render = True
        obj.is_mmd_spring_joint = True
        obj.parent = self.__root
        self.__tempObjGroup.objects.link(obj)
        utils.selectAObject(obj)
        bpy.ops.rigidbody.constraint_add(type='GENERIC_SPRING')
        rbc = obj.rigid_body_constraint
        rbc.object1 = target
        rbc.object2 = spring_target

        rbc.use_spring_x = True
        rbc.use_spring_y = True
        rbc.use_spring_z = True

        rbc.spring_stiffness_x = spring_stiffness[0]
        rbc.spring_stiffness_y = spring_stiffness[1]
        rbc.spring_stiffness_z = spring_stiffness[2]

    def __importJoints(self):
        if self.__onlyCollisions:
            return
        self.__jointTable = []
        for joint in self.__model.joints:
            loc = mathutils.Vector(joint.location) * self.TO_BLE_MATRIX * self.__scale
            rot = mathutils.Vector(joint.rotation) * self.TO_BLE_MATRIX * -1
            obj = bpy.data.objects.new(
                'J.'+joint.name,
                None)
            bpy.context.scene.objects.link(obj)
            obj.location = loc
            obj.rotation_euler = rot
            obj.empty_draw_size = 0.5 * self.__scale
            obj.empty_draw_type = 'ARROWS'
            obj.hide_render = True
            obj.is_mmd_joint = True
            obj.parent = self.__root
            self.__jointObjGroup.objects.link(obj)

            utils.selectAObject(obj)
            bpy.ops.rigidbody.constraint_add(type='GENERIC_SPRING')
            rbc = obj.rigid_body_constraint

            rigid1 = self.__rigidTable[joint.src_rigid]
            rigid2 = self.__rigidTable[joint.dest_rigid]
            rbc.object1 = rigid1
            rbc.object2 = rigid2

            if not self.__ignoreNonCollisionGroups:
                non_collision_joint = self.__nonCollisionJointTable.get(frozenset((rigid1, rigid2)), None)
                if non_collision_joint is None:
                    rbc.disable_collisions = False
                else:
                    utils.selectAObject(non_collision_joint)
                    bpy.ops.object.delete(use_global=False)
                    rbc.disable_collisions = True
            elif rigid1.rigid_body.kinematic and not rigid2.rigid_body.kinematic or not rigid1.rigid_body.kinematic and rigid2.rigid_body.kinematic:
                rbc.disable_collisions = False

            rbc.use_limit_ang_x = True
            rbc.use_limit_ang_y = True
            rbc.use_limit_ang_z = True
            rbc.use_limit_lin_x = True
            rbc.use_limit_lin_y = True
            rbc.use_limit_lin_z = True
            rbc.use_spring_x = True
            rbc.use_spring_y = True
            rbc.use_spring_z = True

            max_loc = mathutils.Vector(joint.maximum_location) * self.TO_BLE_MATRIX * self.__scale
            min_loc = mathutils.Vector(joint.minimum_location) * self.TO_BLE_MATRIX * self.__scale
            rbc.limit_lin_x_upper = max_loc[0]
            rbc.limit_lin_y_upper = max_loc[1]
            rbc.limit_lin_z_upper = max_loc[2]

            rbc.limit_lin_x_lower = min_loc[0]
            rbc.limit_lin_y_lower = min_loc[1]
            rbc.limit_lin_z_lower = min_loc[2]

            max_rot = mathutils.Vector(joint.maximum_rotation) * self.TO_BLE_MATRIX
            min_rot = mathutils.Vector(joint.minimum_rotation) * self.TO_BLE_MATRIX
            rbc.limit_ang_x_upper = -min_rot[0]
            rbc.limit_ang_y_upper = -min_rot[1]
            rbc.limit_ang_z_upper = -min_rot[2]

            rbc.limit_ang_x_lower = -max_rot[0]
            rbc.limit_ang_y_lower = -max_rot[1]
            rbc.limit_ang_z_lower = -max_rot[2]

            # spring_damp = mathutils.Vector(joint.spring_constant) * self.TO_BLE_MATRIX
            # rbc.spring_damping_x = spring_damp[0]
            # rbc.spring_damping_y = spring_damp[1]
            # rbc.spring_damping_z = spring_damp[2]

            self.__jointTable.append(obj)
            bpy.ops.object.select_all(action='DESELECT')
            obj.select = True
            bpy.context.scene.objects.active = self.__armObj
            bpy.ops.object.parent_set(type='OBJECT', xmirror=False, keep_transform=True)

            # spring_stiff = mathutils.Vector()
            # rbc.spring_stiffness_x = spring_stiff[0]
            # rbc.spring_stiffness_y = spring_stiff[1]
            # rbc.spring_stiffness_z = spring_stiff[2]

            if rigid1.rigid_body.kinematic:
                self.__makeSpring(rigid2, rigid1, mathutils.Vector(joint.spring_rotation_constant) * self.TO_BLE_MATRIX)
            if rigid2.rigid_body.kinematic:
                self.__makeSpring(rigid1, rigid2, mathutils.Vector(joint.spring_rotation_constant) * self.TO_BLE_MATRIX)





    def __importMaterials(self):
        self.__importTextures()
        bpy.types.Material.ambient_color = bpy.props.FloatVectorProperty(name='ambient color')

        pmxModel = self.__model

        self.__materialTable = []
        self.__materialFaceCountTable = []
        for i in pmxModel.materials:
            mat = bpy.data.materials.new(name=i.name)
            mat.diffuse_color = i.diffuse[0:3]
            mat.alpha = i.diffuse[3]
            mat.ambient_color = i.ambient
            mat.specular_color = i.specular[0:3]
            mat.specular_alpha = i.specular[3]
            mat.use_shadows = i.enabled_self_shadow
            mat.use_transparent_shadows = i.enabled_self_shadow
            mat.use_cast_buffer_shadows = i.enabled_self_shadow_map # only buffer shadows
            if hasattr(mat, 'use_cast_shadows'):
                # "use_cast_shadows" is not supported in older Blender (< 2.71),
                # so we still use "use_cast_buffer_shadows".
                mat.use_cast_shadows = i.enabled_self_shadow_map
            if mat.alpha < 1.0 or mat.specular_alpha < 1.0 or i.texture != -1:
                mat.use_transparency = True
                mat.transparency_method = 'Z_TRANSPARENCY'
            self.__materialFaceCountTable.append(int(i.vertex_count/3))
            self.__meshObj.data.materials.append(mat)
            if i.texture != -1:
                texture_slot = mat.texture_slots.add()
                texture_slot.use_map_alpha = True
                texture_slot.texture = self.__textureTable[i.texture]
                texture_slot.texture.use_mipmap = self.__use_mipmap
                texture_slot.texture_coords = 'UV'
                texture_slot.blend_type = 'MULTIPLY'
            if i.sphere_texture_mode == 2:
                amount = self.__spa_blend_factor
                blend = 'ADD'
            else:
                amount = self.__sph_blend_factor
                blend = 'MULTIPLY'
            if i.sphere_texture != -1 and amount != 0.0:
                texture_slot = mat.texture_slots.add()
                texture_slot.texture = self.__textureTable[i.sphere_texture]
                if isinstance(texture_slot.texture.image, bpy.types.Image):
                    texture_slot.texture.image.use_alpha = False
                texture_slot.texture_coords = 'NORMAL'
                texture_slot.diffuse_color_factor = amount
                texture_slot.blend_type = blend

    def __importFaces(self):
        pmxModel = self.__model
        mesh = self.__meshObj.data

        mesh.tessfaces.add(len(pmxModel.faces))
        uvLayer = mesh.tessface_uv_textures.new()
        for i, f in enumerate(pmxModel.faces):
            bf = mesh.tessfaces[i]
            bf.vertices_raw = list(f) + [0]
            bf.use_smooth = True
            face_count = 0
            uv = uvLayer.data[i]
            uv.uv1 = self.flipUV_V(pmxModel.vertices[f[0]].uv)
            uv.uv2 = self.flipUV_V(pmxModel.vertices[f[1]].uv)
            uv.uv3 = self.flipUV_V(pmxModel.vertices[f[2]].uv)

            bf.material_index = self.__getMaterialIndexFromFaceIndex(i)

    def __importVertexMorphs(self):
        pmxModel = self.__model

        utils.selectAObject(self.__meshObj)
        bpy.ops.object.shape_key_add()

        for morph in filter(lambda x: isinstance(x, pmx.VertexMorph), pmxModel.morphs):
            shapeKey = self.__meshObj.shape_key_add(morph.name)
            for md in morph.offsets:
                shapeKeyPoint = shapeKey.data[md.index]
                offset = mathutils.Vector(md.offset) * self.TO_BLE_MATRIX
                shapeKeyPoint.co = shapeKeyPoint.co + offset * self.__scale

    def __hideRigidsAndJoints(self, obj):
        if obj.is_mmd_rigid or obj.is_mmd_joint or obj.is_mmd_non_collision_constraint or obj.is_mmd_spring_joint or obj.is_mmd_spring_goal:
            obj.hide = True

        for i in obj.children:
            self.__hideRigidsAndJoints(i)

    def __addArmatureModifier(self, meshObj, armObj):
        armModifier = meshObj.modifiers.new(name='Armature', type='ARMATURE')
        armModifier.object = armObj
        armModifier.use_vertex_groups = True

    def __renameLRBones(self):
        pose_bones = self.__armObj.pose.bones
        for i in pose_bones:
            if i.is_mmd_shadow_bone:
                continue
            i.mmd_bone_name_j = i.name
            i.name = utils.convertNameToLR(i.name)
            self.__meshObj.vertex_groups[i.mmd_bone_name_j].name = i.name

    def execute(self, **args):
        if 'pmx' in args:
            self.__model = args['pmx']
        else:
            self.__model = pmx.load(args['filepath'])

        self.__scale = args.get('scale', 1.0)
        renameLRBones = args.get('rename_LR_bones', False)
        self.__onlyCollisions = args.get('only_collisions', False)
        self.__ignoreNonCollisionGroups = args.get('ignore_non_collision_groups', True)
        self.__distance_of_ignore_collisions = args.get('distance_of_ignore_collisions', 1) # 衝突を考慮しない距離（非衝突グループ設定を無視する距離）
        self.__distance_of_ignore_collisions /= 2
        self.__use_mipmap = args.get('use_mipmap', True)
        self.__sph_blend_factor = args.get('sph_blend_factor', 1.0)
        self.__spa_blend_factor = args.get('spa_blend_factor', 1.0)

        logging.info('****************************************')
        logging.info(' mmd_tools.import_pmx module')
        logging.info('----------------------------------------')
        logging.info(' Start to load model data form a pmx file')
        logging.info('            by the mmd_tools.pmx modlue.')
        logging.info('')

        start_time = time.time()

        self.__createGroups()
        self.__createObjects()

        self.__importVertices()
        self.__importBones()
        self.__importMaterials()
        self.__importFaces()
        self.__importRigids()
        self.__importJoints()

        self.__importVertexMorphs()

        if renameLRBones:
            self.__renameLRBones()

        self.__addArmatureModifier(self.__meshObj, self.__armObj)
        self.__meshObj.data.update()

        bpy.types.Object.pmx_import_scale = bpy.props.FloatProperty(name='pmx_import_scale')
        if args.get('hide_rigids', False):
            self.__hideRigidsAndJoints(self.__root)
        self.__armObj.pmx_import_scale = self.__scale

        for i in [self.__rigidObjGroup.objects, self.__jointObjGroup.objects, self.__tempObjGroup.objects]:
            for j in i:
                self.__allObjGroup.objects.link(j)

        bpy.context.scene.gravity[2] = -9.81 * 10 * self.__scale

        logging.info(' Finished importing the model in %f seconds.', time.time() - start_time)
        logging.info('----------------------------------------')
        logging.info(' mmd_tools.import_pmx module')
        logging.info('****************************************')

########NEW FILE########
__FILENAME__ = import_vmd
# -*- coding: utf-8 -*-
import struct
import collections
import mathutils
import bpy
import math
import re
import os

from . import vmd
from . import mmd_camera
from . import mmd_lamp
from . import utils

class VMDImporter:
    def __init__(self, filepath, scale=1.0, use_pmx_bonename=True, convert_mmd_camera=True, convert_mmd_lamp=True, frame_margin=5):
        self.__vmdFile = vmd.File()
        self.__vmdFile.load(filepath=filepath)
        self.__scale = scale
        self.__convert_mmd_camera = convert_mmd_camera
        self.__convert_mmd_lamp = convert_mmd_lamp
        self.__use_pmx_bonename = use_pmx_bonename
        self.__frame_margin = frame_margin + 1


    @staticmethod
    def makeVMDBoneLocationToBlenderMatrix(blender_bone):
        mat = mathutils.Matrix([
                [blender_bone.x_axis.x, blender_bone.x_axis.y, blender_bone.x_axis.z, 0.0],
                [blender_bone.y_axis.x, blender_bone.y_axis.y, blender_bone.y_axis.z, 0.0],
                [blender_bone.z_axis.x, blender_bone.z_axis.y, blender_bone.z_axis.z, 0.0],
                [0.0, 0.0, 0.0, 1.0]
                ])
        mat2 = mathutils.Matrix([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]])
        return mat * mat2

    @staticmethod
    def convertVMDBoneRotationToBlender(blender_bone, rotation):
        if not isinstance(rotation, mathutils.Quaternion):
            rot = mathutils.Quaternion()
            rot.x, rot.y, rot.z, rot.w = rotation
            rotation = rot
        mat = mathutils.Matrix()
        mat[0][0], mat[1][0], mat[2][0] = blender_bone.x_axis.x, blender_bone.y_axis.x, blender_bone.z_axis.x
        mat[0][1], mat[1][1], mat[2][1] = blender_bone.x_axis.y, blender_bone.y_axis.y, blender_bone.z_axis.y
        mat[0][2], mat[1][2], mat[2][2] = blender_bone.x_axis.z, blender_bone.y_axis.z, blender_bone.z_axis.z
        (vec, angle) = rotation.to_axis_angle()
        v = mathutils.Vector((-vec.x, -vec.z, -vec.y))
        return mathutils.Quaternion(mat*v, angle).normalized()

    @staticmethod
    def __fixRotations(rotation_ary):
        rotation_ary = list(rotation_ary)
        if len(rotation_ary) == 0:
            return rotation_ary

        pq = rotation_ary.pop(0)
        res = [pq]
        for q in rotation_ary:
            nq = q.copy()
            nq.negate()
            t1 = (pq.w-q.w)**2+(pq.x-q.x)**2+(pq.y-q.y)**2+(pq.z-q.z)**2
            t2 = (pq.w-nq.w)**2+(pq.x-nq.x)**2+(pq.y-nq.y)**2+(pq.z-nq.z)**2
            # t1 = pq.axis.dot(q.axis)
            # t2 = pq.axis.dot(nq.axis)
            if t2 < t1:
                res.append(nq)
                pq = nq
            else:
                res.append(q)
                pq = q
        return res

    @staticmethod
    def __setInterpolation(bezier, kp0, kp1):
        if bezier[0] == bezier[1] and bezier[2] == bezier[3]:
            kp0.interpolation = 'LINEAR'
        else:
            kp0.interpolation = 'BEZIER'
            kp0.handle_right_type = 'FREE'
            kp1.handle_left_type = 'FREE'
            d = (kp1.co - kp0.co) / 127.0
            kp0.handle_right = kp0.co + mathutils.Vector((d.x * bezier[0], d.y * bezier[1]))
            kp1.handle_left = kp0.co + mathutils.Vector((d.x * bezier[2], d.y * bezier[3]))

    def __assignToArmature(self, armObj, action_name=None):
        if action_name is not None:
            act = bpy.data.actions.new(name=action_name)
            a = armObj.animation_data_create()
            a.action = act

        if self.__frame_margin > 1:
            utils.selectAObject(armObj)
            bpy.context.scene.frame_current = 1
            bpy.ops.object.mode_set(mode='POSE')
            hiddenBones = []
            for i in armObj.data.bones:
                if i.hide:
                    hiddenBones.append(i)
                    i.hide = False
                i.select = True
            bpy.ops.pose.transforms_clear()
            bpy.ops.anim.keyframe_insert_menu(type='LocRotScale', confirm_success=False, always_prompt=False)
            bpy.ops.object.mode_set(mode='OBJECT')
            for i in hiddenBones:
                i.hide = True
            
        boneAnim = self.__vmdFile.boneAnimation

        pose_bones = armObj.pose.bones
        if self.__use_pmx_bonename:
            pose_bones = utils.makePmxBoneMap(armObj)
        for name, keyFrames in boneAnim.items():
            if name not in pose_bones:
                print("WARNING: not found bone %s"%str(name))
                continue

            keyFrames.sort(key=lambda x:x.frame_number)
            bone = pose_bones[name]
            frameNumbers = map(lambda x: x.frame_number, keyFrames)
            mat = self.makeVMDBoneLocationToBlenderMatrix(bone)
            locations = map(lambda x: mat * mathutils.Vector(x.location) * self.__scale, keyFrames)
            rotations = map(lambda x: self.convertVMDBoneRotationToBlender(bone, x.rotation), keyFrames)
            rotations = self.__fixRotations(rotations)

            for frame, location, rotation in zip(frameNumbers, locations, rotations):
                bone.location = location
                bone.rotation_quaternion = rotation
                bone.keyframe_insert(data_path='location',
                                     group=name,
                                     frame=frame+self.__frame_margin)
                bone.keyframe_insert(data_path='rotation_quaternion',
                                     group=name,
                                     frame=frame+self.__frame_margin)

        rePath = re.compile('^pose\.bones\["(.+)"\]\.([a-z_]+)$')
        for fcurve in act.fcurves:
            m = rePath.match(fcurve.data_path)
            if m and m.group(2) in ['location', 'rotation_quaternion']:
                bone = armObj.pose.bones[m.group(1)]
                keyFrames = boneAnim[bone.get('name_j', bone.name)]
                if m.group(2) == 'location':
                    idx = [0, 2, 1][fcurve.array_index]
                else:
                    idx = 3
                frames = list(fcurve.keyframe_points)
                frames.sort(key=lambda kp:kp.co.x)
                if self.__frame_margin > 1:
                    del frames[0]
                for i in range(1, len(keyFrames)):
                    self.__setInterpolation(keyFrames[i].interp[idx:16:4], frames[i - 1], frames[i])

    def __assignToMesh(self, meshObj, action_name=None):
        if action_name is not None:
            act = bpy.data.actions.new(name=action_name)
            a = meshObj.data.shape_keys.animation_data_create()
            a.action = act

        shapeKeyAnim = self.__vmdFile.shapeKeyAnimation

        shapeKeyDict = {}
        for i in meshObj.data.shape_keys.key_blocks:
            shapeKeyDict[i.name] = i

        for name, keyFrames in shapeKeyAnim.items():
            if name not in shapeKeyDict:
                print("WARNING: not found shape key %s"%str(name))
                continue
            shapeKey = shapeKeyDict[name]
            for i in keyFrames:
                shapeKey.value = i.weight
                shapeKey.keyframe_insert(data_path='value',
                                         group=name,
                                         frame=i.frame_number+self.__frame_margin)

    @staticmethod
    def detectCameraChange(fcurve, threshold=10.0):
        frames = list(fcurve.keyframe_points)
        frameCount = len(frames)
        frames.sort(key=lambda x:x.co[0])
        for i, f in enumerate(frames):
            if i+1 < frameCount:
                n = frames[i+1]
                if n.co[0] - f.co[0] <= 1.0 and abs(f.co[1] - n.co[1]) > threshold:
                    f.interpolation = 'CONSTANT'

    def __assignToCamera(self, cameraObj, action_name=None):
        mmdCamera = mmd_camera.MMDCamera.convertToMMDCamera(cameraObj).object()
        if action_name is not None:
            act = bpy.data.actions.new(name=action_name)
            a = mmdCamera.animation_data_create()
            a.action = act

        cameraAnim = self.__vmdFile.cameraAnimation
        cameraAnim.sort(key=lambda x:x.frame_number)
        for keyFrame in cameraAnim:
            mmdCamera.mmd_camera_angle = keyFrame.angle
            mmdCamera.mmd_camera_distance = -keyFrame.distance * self.__scale
            mmdCamera.location = mathutils.Vector((keyFrame.location[0], keyFrame.location[2], keyFrame.location[1])) * self.__scale
            mmdCamera.rotation_euler = mathutils.Vector((keyFrame.rotation[0], keyFrame.rotation[2], keyFrame.rotation[1]))
            mmdCamera.keyframe_insert(data_path='mmd_camera_angle',
                                           frame=keyFrame.frame_number+self.__frame_margin)
            mmdCamera.keyframe_insert(data_path='mmd_camera_distance',
                                      frame=keyFrame.frame_number+self.__frame_margin)
            mmdCamera.keyframe_insert(data_path='location',
                                      frame=keyFrame.frame_number+self.__frame_margin)
            mmdCamera.keyframe_insert(data_path='rotation_euler',
                                      frame=keyFrame.frame_number+self.__frame_margin)

        paths = ['rotation_euler', 'mmd_camera_distance', 'mmd_camera_angle', 'location']
        for fcurve in act.fcurves:
            if fcurve.data_path in paths:
                if fcurve.data_path =='location':
                    idx = [0, 2, 1][fcurve.array_index] * 4
                else:
                    idx = (paths.index(fcurve.data_path) + 3) * 4
                frames = list(fcurve.keyframe_points)
                frames.sort(key=lambda kp:kp.co.x)
                for i in range(1, len(cameraAnim)):
                    interp = cameraAnim[i].interp
                    self.__setInterpolation([interp[idx + j] for j in [0, 2, 1, 3]], frames[i - 1], frames[i])

        for fcurve in mmdCamera.animation_data.action.fcurves:
            if fcurve.data_path == 'rotation_euler':
                self.detectCameraChange(fcurve)

    @staticmethod
    def detectLampChange(fcurve, threshold=0.1):
        frames = list(fcurve.keyframe_points)
        frameCount = len(frames)
        frames.sort(key=lambda x:x.co[0])
        for i, f in enumerate(frames):
            if i+1 < frameCount:
                n = frames[i+1]
                if n.co[0] - f.co[0] <= 1.0 and abs(f.co[1] - n.co[1]) > threshold:
                    f.interpolation = 'CONSTANT'

    def __assignToLamp(self, lampObj, action_name=None):
        mmdLamp = mmd_lamp.MMDLamp.convertToMMDLamp(lampObj).object()
        mmdLamp.scale = mathutils.Vector((self.__scale, self.__scale, self.__scale)) * 4.0
        for obj in mmdLamp.children:
            if obj.type == 'LAMP':
                lamp = obj
            elif obj.type == 'ARMATURE':
                armature = obj
                bone = armature.pose.bones[0]
                bone_data_path = 'pose.bones["' + bone.name + '"].location'

        if action_name is not None:
            act = bpy.data.actions.new(name=action_name + '_color')
            a = lamp.data.animation_data_create()
            a.action = act
            act = bpy.data.actions.new(name=action_name + '_location')
            a = armature.animation_data_create()
            a.action = act

        lampAnim = self.__vmdFile.lampAnimation
        for keyFrame in lampAnim:
            lamp.data.color = mathutils.Vector(keyFrame.color)
            bone.location = -(mathutils.Vector((keyFrame.direction[0], keyFrame.direction[2], keyFrame.direction[1])))
            lamp.data.keyframe_insert(data_path='color',
                                      frame=keyFrame.frame_number+self.__frame_margin)
            bone.keyframe_insert(data_path='location',
                                 frame=keyFrame.frame_number+self.__frame_margin)

        for fcurve in armature.animation_data.action.fcurves:
            if fcurve.data_path == bone_data_path:
                self.detectLampChange(fcurve)



    def assign(self, obj, action_name=None):
        if action_name is None:
            action_name = os.path.splitext(os.path.basename(self.__vmdFile.filepath))[0]

        if mmd_camera.MMDCamera.isMMDCamera(obj):
            self.__assignToCamera(obj, action_name+'_camera')
        elif mmd_lamp.MMDLamp.isMMDLamp(obj):
            self.__assignToLamp(obj, action_name+'_lamp')
        elif obj.type == 'MESH':
            self.__assignToMesh(obj, action_name+'_facial')
        elif obj.type == 'ARMATURE':
            self.__assignToArmature(obj, action_name+'_bone')
        elif obj.type == 'CAMERA' and self.__convert_mmd_camera:
            obj = mmd_camera.MMDCamera.convertToMMDCamera(obj)
            self.__assignToCamera(obj.object(), action_name+'_camera')
        elif obj.type == 'LAMP' and self.__convert_mmd_lamp:
            obj = mmd_lamp.MMDLamp.convertToMMDLamp(obj)
            self.__assignToLamp(obj.object(), action_name+'_lamp')
        else:
            pass


########NEW FILE########
__FILENAME__ = mmd_camera
import bpy
import mathutils
import math

class MMDCamera:
    def __init__(self, obj):
        if obj.type != 'EMPTY':
            if obj.parent is None or obj.type != 'CAMERA':
                raise ValueError('%s is not MMDCamera'%str(obj))
            obj = obj.parent
        if obj.type == 'EMPTY' and obj.get('is_mmd_camera', False):
            self.__emptyObj = obj
        else:
            raise ValueError('%s is not MMDCamera'%str(obj))


    @staticmethod
    def isMMDCamera(obj):
        if obj.type != 'EMPTY':
            if obj.parent is None or obj.type != 'CAMERA':
                return False
            obj = obj.parent
        return obj.type == 'EMPTY' and obj.get('is_mmd_camera', False)


    @staticmethod
    def __setDrivers(empty, camera):
        driver = camera.driver_add('location', 1).driver
        driverVar = driver.variables.new()
        driverVar.name = 'mmd_distance'
        driverVar.type = 'SINGLE_PROP'
        driverVar.targets[0].id_type = 'OBJECT'
        driverVar.targets[0].id = empty
        driverVar.targets[0].data_path = 'mmd_camera_distance'
        driver.type = 'SCRIPTED'
        driver.expression = '-%s'%driverVar.name

        driver = camera.data.driver_add('lens').driver
        angle = driver.variables.new()
        angle.name = 'mmd_distance'
        angle.type = 'SINGLE_PROP'
        angle.targets[0].id_type = 'OBJECT'
        angle.targets[0].id = empty
        angle.targets[0].data_path = 'mmd_camera_angle'

        sensorHeight = driver.variables.new()
        sensorHeight.name = 'sensor_height'
        sensorHeight.type = 'SINGLE_PROP'
        sensorHeight.targets[0].id_type = 'OBJECT'
        sensorHeight.targets[0].id = camera
        sensorHeight.targets[0].data_path = 'data.sensor_height'

        driver.type = 'SCRIPTED'
        driver.expression = '%s/(2*tan(radians(%s)/2))'%(sensorHeight.name, angle.name)


    @staticmethod
    def convertToMMDCamera(cameraObj):
        import bpy
        import mathutils
        if MMDCamera.isMMDCamera(cameraObj):
            return MMDCamera(cameraObj)

        empty = bpy.data.objects.new(name='MMD_Camera', object_data=None)
        bpy.context.scene.objects.link(empty)

        empty.rotation_mode = 'YXZ'
        empty.is_mmd_camera = True
        empty.mmd_camera_distance = 0.0
        empty.mmd_camera_angle = 45
        empty.mmd_camera_persp = True
        cameraObj.parent = empty
        cameraObj.data.sensor_fit = 'VERTICAL'
        cameraObj.location = mathutils.Vector((0,0,0))
        cameraObj.rotation_mode = 'XYZ'
        cameraObj.rotation_euler = mathutils.Vector((math.radians(90.0),0,0))
        cameraObj.lock_location = (True, False, True)
        cameraObj.lock_rotation = (True, True, True)
        cameraObj.lock_scale = (True, True, True)

        MMDCamera.__setDrivers(empty, cameraObj)

        return MMDCamera(empty)

    def object(self):
        return self.__emptyObj

########NEW FILE########
__FILENAME__ = mmd_lamp
import bpy
import mathutils
import math

from . import utils

class MMDLamp:
    def __init__(self, obj):
        if obj.type != 'EMPTY':
            if obj.parent is None or not obj.type in ['LAMP', 'ARMATURE']:
                raise ValueError('%s is not MMDLamp'%str(obj))
            obj = obj.parent
        if obj.type == 'EMPTY' and obj.get('is_mmd_lamp', False):
            self.__emptyObj = obj
        else:
            raise ValueError('%s is not MMDLamp'%str(obj))


    @staticmethod
    def isMMDLamp(obj):
        if obj.type != 'EMPTY':
            if obj.parent is None or not obj.type in ['LAMP', 'ARMATURE']:
                return False
            obj = obj.parent
        return obj.type == 'EMPTY' and obj.get('is_mmd_lamp', False)


    @staticmethod
    def __setConstraints(empty, armature, poseBone, lamp):
        constraints = lamp.constraints

        constraint = constraints.new(type='COPY_LOCATION')
        constraint.name = 'mmd_lamp_location'
        constraint.target = armature
        constraint.subtarget = poseBone.name

        constraint = constraints.new(type='TRACK_TO')
        constraint.name = 'mmd_lamp_track'
        constraint.target = empty
        constraint.track_axis = 'TRACK_NEGATIVE_Z'
        constraint.up_axis = 'UP_Y'

        constraints = poseBone.constraints

        constraint = constraints.new(type='TRACK_TO')
        constraint.name = 'mmd_lamp_track'
        constraint.target = empty
        constraint.track_axis = 'TRACK_NEGATIVE_Y'
        constraint.up_axis = 'UP_Z'


    @staticmethod
    def convertToMMDLamp(lampObj):
        import bpy
        import mathutils
        if MMDLamp.isMMDLamp(lampObj):
            return MMDLamp(lampObj)

        name = 'MMD_' + lampObj.name + '_target'
        empty = bpy.data.objects.new(name=name, object_data=None)
        bpy.context.scene.objects.link(empty)

        name = 'MMD_' + lampObj.name + '_source'
        armature = bpy.data.armatures.new(name=name)
        armatureObj = bpy.data.objects.new(name=name, object_data=armature)
        bpy.context.scene.objects.link(armatureObj)

        utils.enterEditMode(armatureObj)
        bone = armature.edit_bones.new(name='handle')
        bone.head = mathutils.Vector((0,0,0))
        bone.tail = mathutils.Vector((0,0.2,0))
        bpy.ops.object.mode_set(mode='POSE')

        empty.rotation_mode = 'XYZ'
        empty.is_mmd_lamp = True

        armatureObj.parent = empty
        armatureObj.location = mathutils.Vector((0,0,0))
        armatureObj.rotation_mode = 'XYZ'
        armatureObj.rotation_euler = mathutils.Vector((0,0,0))
        armatureObj.scale = mathutils.Vector((4.0, 4.0, 4.0))
        armatureObj.lock_location = (True, True, True)
        armatureObj.lock_rotation = (True, True, True)
        armatureObj.lock_scale = (False, False, False)
        armatureObj.draw_type = 'WIRE'
        armature.draw_type = 'BBONE'

        poseBone = armatureObj.pose.bones[0]
        poseBone.location =  mathutils.Vector((0,0,0))
        poseBone.rotation_mode = 'QUATERNION'
        poseBone.rotation_quaternion = mathutils.Quaternion((1,0,0,0))
        poseBone.scale =  mathutils.Vector((0.2,1.0,0.2))
        poseBone.lock_location = (False, False, False)
        poseBone.lock_rotation = (True, True, True)
        poseBone.lock_rotations_4d = False
        poseBone.lock_scale = (False, False, False)

        lampObj.parent = empty
        lampObj.location = mathutils.Vector((0,0,0))
        lampObj.rotation_mode = 'XYZ'
        lampObj.rotation_euler = mathutils.Vector((0,0,0))

        MMDLamp.__setConstraints(empty, armatureObj, poseBone, lampObj)

        return MMDLamp(empty)

    def object(self):
        return self.__emptyObj


########NEW FILE########
__FILENAME__ = pmd
# -*- coding: utf-8 -*-
import struct
import os
import re
import logging
import collections

class InvalidFileError(Exception):
    pass
class UnsupportedVersionError(Exception):
    pass

class FileStream:
    def __init__(self, path, file_obj):
        self.__path = path
        self.__file_obj = file_obj

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def path(self):
        return self.__path

    def header(self):
        if self.__header is None:
            raise Exception
        return self.__header

    def setHeader(self, pmx_header):
        self.__header = pmx_header

    def close(self):
        if self.__file_obj is not None:
            logging.debug('close the file("%s")', self.__path)
            self.__file_obj.close()
            self.__file_obj = None


class  FileReadStream(FileStream):
    def __init__(self, path, pmx_header=None):
        self.__fin = open(path, 'rb')
        FileStream.__init__(self, path, self.__fin)


    # READ / WRITE methods for general types
    def readInt(self):
        v, = struct.unpack('<i', self.__fin.read(4))
        return v

    def readUnsignedInt(self):
        v, = struct.unpack('<I', self.__fin.read(4))
        return v

    def readShort(self):
        v, = struct.unpack('<h', self.__fin.read(2))
        return v

    def readUnsignedShort(self):
        v, = struct.unpack('<H', self.__fin.read(2))
        return v

    def readStr(self, size):
        buf = self.__fin.read(size)
        try:
            index = buf.index(b'\x00')
            t = buf[:index]
            return t.decode('shift-jis')
        except ValueError:
            if buf[0] == b'\xfd':
                return ''
            try:
                return buf.decode('shift-jis')
            except UnicodeDecodeError:
                logging.warning('found a invalid shift-jis string.')
                return ''

    def readFloat(self):
        v, = struct.unpack('<f', self.__fin.read(4))
        return v

    def readVector(self, size):
        fmt = '<'
        for i in range(size):
            fmt += 'f'
        return list(struct.unpack(fmt, self.__fin.read(4*size)))

    def readByte(self):
        v, = struct.unpack('<B', self.__fin.read(1))
        return v

    def readBytes(self, length):
        return self.__fin.read(length)

    def readSignedByte(self):
        v, = struct.unpack('<b', self.__fin.read(1))
        return v


class Header:
    PMD_SIGN = b'Pmd'
    VERSION = 1.0

    def __init__(self):
        self.sign = self.PMD_SIGN
        self.version = self.VERSION
        self.model_name = ''
        self.comment = ''

    def load(self, fs):
        sign = fs.readBytes(3)
        if sign != self.PMD_SIGN:
            raise InvalidFileError('Not PMD file')
        version = fs.readFloat()
        if version != self.version:
            raise InvalidFileError('Not suppored version')

        self.model_name = fs.readStr(20)
        self.comment = fs.readStr(256)

class Vertex:
    def __init__(self):
        self.position = [0.0, 0.0, 0.0]
        self.normal = [1.0, 0.0, 0.0]
        self.uv = [0.0, 0.0]
        self.bones = [-1, -1]
        self.weight = 0 # min:0, max:100
        self.enable_edge = 0 # 0: on, 1: off

    def load(self, fs):
        self.position = fs.readVector(3)
        self.normal = fs.readVector(3)
        self.uv = fs.readVector(2)
        self.bones[0] = fs.readUnsignedShort()
        self.bones[1] = fs.readUnsignedShort()
        self.weight = fs.readByte()
        self.enable_edge = fs.readByte()

class Material:
    def __init__(self):
        self.diffuse = []
        self.specular_intensity = 0.5
        self.specular = []
        self.ambient = []
        self.toon_index = 0
        self.edge_flag = 0
        self.vertex_count = 0
        self.texture_path = ''
        self.sphere_path = ''
        self.sphere_mode = 1

    def load(self, fs):
        self.diffuse = fs.readVector(4)
        self.specular_intensity = fs.readFloat()
        self.specular = fs.readVector(3)
        self.ambient = fs.readVector(3)
        self.toon_index = fs.readByte()
        self.edge_flag = fs.readByte()
        self.vertex_count = fs.readUnsignedInt()
        tex_path = fs.readStr(20)
        t = tex_path.split('*')
        if not re.search('\.sp([ha])$', t[0], flags=re.I):
            self.texture_path = t.pop(0)
        if len(t) > 0:
            self.sphere_path = t.pop(0)
            if 'aA'.find(self.sphere_path[-1]) != -1:
                self.sphere_mode = 2

class Bone:
    def __init__(self):
        self.name = ''
        self.name_e = ''
        self.parent = 0xffff
        self.tail_bone = 0xffff
        self.type = 1
        self.ik_bone = 0
        self.position = []

    def load(self, fs):
        self.name = fs.readStr(20)
        self.parent = fs.readUnsignedShort()
        if self.parent == 0xffff:
            self.parent = -1
        self.tail_bone = fs.readUnsignedShort()
        if self.tail_bone == 0xffff:
            self.tail_bone = -1
        self.type = fs.readByte()
        self.ik_bone = fs.readUnsignedShort()
        self.position = fs.readVector(3)

class IK:
    def __init__(self):
        self.bone = 0
        self.target_bone = 0
        self.ik_chain = 0
        self.iterations = 0
        self.control_weight = 0.0
        self.ik_child_bones = []

    def __str__(self):
        return '<IK bone: %d, target: %d, chain: %s, iter: %d, weight: %f, ik_children: %s'%(
            self.bone,
            self.target_bone,
            self.ik_chain,
            self.iterations,
            self.control_weight,
            self.ik_child_bones)

    def load(self, fs):
        self.bone = fs.readUnsignedShort()
        self.target_bone = fs.readUnsignedShort()
        self.ik_chain = fs.readByte()
        self.iterations = fs.readUnsignedShort()
        self.control_weight = fs.readFloat()
        self.ik_child_bones = []
        for i in range(self.ik_chain):
            self.ik_child_bones.append(fs.readUnsignedShort())

class MorphData:
    def __init__(self):
        self.index = 0
        self.offset = []

    def load(self, fs):
        self.index = fs.readUnsignedInt()
        self.offset = fs.readVector(3)

class VertexMorph:
    def __init__(self):
        self.name = ''
        self.type = 0
        self.data = []

    def load(self, fs):
        self.name = fs.readStr(20)
        data_size = fs.readUnsignedInt()
        self.type = fs.readByte()
        for i in range(data_size):
            t = MorphData()
            t.load(fs)
            self.data.append(t)

class RigidBody:
    def __init__(self):
        self.name = ''
        self.bone = -1
        self.collision_group_number = 0
        self.collision_group_mask = 0
        self.type = 0
        self.size = []
        self.location = []
        self.rotation = []
        self.mass = 0.0
        self.velocity_attenuation = 0.0
        self.rotation_attenuation = 0.0
        self.friction = 0.0
        self.bounce = 0.0
        self.mode = 0

    def load(self, fs):
        self.name = fs.readStr(20)
        self.bone = fs.readUnsignedShort()
        if self.bone == 0xffff:
            self.bone = -1
        self.collision_group_number = fs.readByte()
        self.collision_group_mask = fs.readUnsignedShort()
        self.type = fs.readByte()
        self.size = fs.readVector(3)
        self.location = fs.readVector(3)
        self.rotation = fs.readVector(3)
        self.mass = fs.readFloat()
        self.velocity_attenuation = fs.readFloat()
        self.rotation_attenuation = fs.readFloat()
        self.bounce = fs.readFloat()
        self.friction = fs.readFloat()
        self.mode = fs.readByte()

class Joint:
    def __init__(self):
        self.name = ''
        self.src_rigid = 0
        self.dest_rigid = 0

        self.location = []
        self.rotation = []

        self.maximum_location = []
        self.minimum_location = []
        self.maximum_rotation = []
        self.minimum_rotation = []

        self.spring_constant = []
        self.spring_rotation_constant = []

    def load(self, fs):
        self.name = fs.readStr(20)

        self.src_rigid = fs.readUnsignedInt()
        self.dest_rigid = fs.readUnsignedInt()

        self.location = fs.readVector(3)
        self.rotation = fs.readVector(3)

        self.maximum_location = fs.readVector(3)
        self.minimum_location = fs.readVector(3)
        self.maximum_rotation = fs.readVector(3)
        self.minimum_rotation = fs.readVector(3)

        self.spring_constant = fs.readVector(3)
        self.spring_rotation_constant = fs.readVector(3)

class Model:
    def __init__(self):
        self.header = None
        self.vertices = []
        self.faces = []
        self.materials = []
        self.iks = []
        self.morphs = []
        self.facial_disp_names = []
        self.bone_disp_names = []
        self.bone_disp_lists = {}
        self.name = ''
        self.comment = ''
        self.name_e = ''
        self.comment_e = ''
        self.toon_textures = []
        self.rigid_bodies = []
        self.joints = []


    def load(self, fs):
        logging.info('importing pmd model from %s...', fs.path())

        header = Header()
        header.load(fs)

        self.name = header.model_name
        self.comment = header.comment

        logging.info('Model name: %s', self.name)
        logging.info('Comment: %s', self.comment)

        logging.info('')
        logging.info('------------------------------')
        logging.info('Load Vertices')
        logging.info('------------------------------')
        self.vertices = []
        vert_count = fs.readUnsignedInt()
        for i in range(vert_count):
            v = Vertex()
            v.load(fs)
            self.vertices.append(v)
        logging.info('the number of vetices: %d', len(self.vertices))
        logging.info('finished importing vertices.')

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Faces')
        logging.info('------------------------------')
        self.faces = []
        face_vert_count = fs.readUnsignedInt()
        for i in range(int(face_vert_count/3)):
            f1 = fs.readUnsignedShort()
            f2 = fs.readUnsignedShort()
            f3 = fs.readUnsignedShort()
            self.faces.append((f3, f2, f1))
        logging.info('the number of faces: %d', len(self.faces))
        logging.info('finished importing faces.')

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Materials')
        logging.info('------------------------------')
        self.materials = []
        material_count = fs.readUnsignedInt()
        for i in range(material_count):
            mat = Material()
            mat.load(fs)
            self.materials.append(mat)

            logging.info('Material %d', i)
            logging.debug('  Vertex Count: %d', mat.vertex_count)
            logging.debug('  Diffuse: (%.2f, %.2f, %.2f, %.2f)', *mat.diffuse)
            logging.debug('  Specular: (%.2f, %.2f, %.2f)', *mat.specular)
            logging.debug('  Specular Intensity: %f', mat.specular_intensity)
            logging.debug('  Ambient: (%.2f, %.2f, %.2f)', *mat.ambient)
            logging.debug('  Toon Index: %d', mat.toon_index)
            logging.debug('  Edge Type: %d', mat.edge_flag)
            logging.debug('  Texture Path: %s', str(mat.texture_path))
            logging.debug('  Sphere Texture Path: %s', str(mat.sphere_path))
            logging.debug('')
        logging.info('Loaded %d materials', len(self.materials))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Bones')
        logging.info('------------------------------')
        self.bones = []
        bone_count = fs.readUnsignedShort()
        for i in range(bone_count):
            bone = Bone()
            bone.load(fs)
            self.bones.append(bone)

            logging.info('Bone %d: %s', i, bone.name)
            logging.debug('  Name(english): %s', bone.name_e)
            logging.debug('  Location: (%f, %f, %f)', *bone.position)
            logging.debug('  Parent: %s', str(bone.parent))
            logging.debug('  Related Bone: %s', str(bone.tail_bone))
            logging.debug('  Type: %s', bone.type)
            logging.debug('  IK bone: %s', str(bone.ik_bone))
            logging.debug('')
        logging.info('----- Loaded %d bones', len(self.bones))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load IKs')
        logging.info('------------------------------')
        self.iks = []
        ik_count = fs.readUnsignedShort()
        for i in range(ik_count):
            ik = IK()
            ik.load(fs)
            self.iks.append(ik)

            logging.info('IK %d', i)
            logging.debug('  Bone: %s(index: %d)', self.bones[ik.bone].name, ik.bone)
            logging.debug('  Target Bone: %s(index: %d)', self.bones[ik.target_bone].name, ik.target_bone)
            logging.debug('  IK Chain: %d', ik.ik_chain)
            logging.debug('  IK Iterations: %d', ik.iterations)
            logging.debug('  Wegiht: %d', ik.control_weight)
            for j, c in enumerate(ik.ik_child_bones):
                logging.debug('    Bone %d: %s(index: %d)', j, self.bones[c].name, c)
            logging.debug('')
        logging.info('----- Loaded %d IKs', len(self.iks))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Morphs')
        logging.info('------------------------------')
        self.morphs = []
        morph_count = fs.readUnsignedShort()
        for i in range(morph_count):
            morph = VertexMorph()
            morph.load(fs)
            self.morphs.append(morph)
            logging.info('Vertex Morph %d: %s', i, morph.name)
        logging.info('----- Loaded %d materials', len(self.morphs))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Display Items')
        logging.info('------------------------------')
        self.facial_disp_morphs = []
        t = fs.readByte()
        for i in range(t):
            u = fs.readUnsignedShort()
            self.facial_disp_morphs.append(u)
            logging.info('Facial %d: %s', i, self.morphs[u].name)

        self.bone_disp_lists = collections.OrderedDict()
        bone_disps = []
        t = fs.readByte()
        for i in range(t):
            name = fs.readStr(50)
            self.bone_disp_lists[name] = []
            bone_disps.append(name)

        t = fs.readUnsignedInt()
        for i in range(t):
            bone_index = fs.readUnsignedShort()
            disp_index = fs.readByte()
            self.bone_disp_lists[bone_disps[disp_index-1]].append(bone_index)

        for i, (k, items) in enumerate(self.bone_disp_lists.items()):
            logging.info('  Frame %d: %s', i, k.rstrip())
            for j, b in enumerate(items):
                logging.info('    Bone %d: %s(index: %d)', j, self.bones[b].name, b)
        logging.info('----- Loaded display items')

        logging.info('')
        logging.info('===============================')
        logging.info(' Load Display Items')
        logging.info('   try to load extended data sections...')
        logging.info('')

        # try to load extended data sections.
        try:
            eng_flag = fs.readByte()
        except e:
            logging.info('found no extended data sections')
            logging.info('===============================')
            return
        logging.info('===============================')

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load a extended data for english')
        logging.info('------------------------------')
        if eng_flag:
            logging.info('found a extended data for english.')
            self.name_e = fs.readStr(20)
            self.comment_e = fs.readStr(256)
            for i in range(len(self.bones)):
                self.bones[i].name_e = fs.readStr(20)

            for i in range(1, len(self.morphs)):
                self.morphs[i].name_e = fs.readStr(20)

            logging.info(' Name(english): %s', self.name_e)
            logging.info(' Comment(english): %s', self.comment_e)

            bone_disps_e = []
            for i in range(len(bone_disps)):
                t = fs.readStr(50)
                bone_disps_e.append(t)
                logging.info(' Bone name(english) %d: %s', i, t)
        logging.info('----- Loaded english data.')

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load toon textures')
        logging.info('------------------------------')
        self.toon_textures = []
        for i in range(10):
            t = fs.readStr(100)
            self.toon_textures.append(t)
            logging.info('Toon Texture %d: %s', i, t)
        logging.info('----- Loaded %d textures', len(self.toon_textures))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Rigid Bodies')
        logging.info('------------------------------')
        rigid_count = fs.readUnsignedInt()
        self.rigid_bodies = []
        rigid_types = {0: 'Sphere', 1: 'Box', 2: 'Capsule'}
        rigid_modes = {0: 'Static', 1: 'Dynamic', 2: 'Dynamic(track to bone)'}
        for i in range(rigid_count):
            rigid = RigidBody()
            rigid.load(fs)
            self.rigid_bodies.append(rigid)
            logging.info('Rigid Body %d: %s', i, rigid.name)
            logging.debug('  Bone: %s', rigid.bone)
            logging.debug('  Collision group: %d', rigid.collision_group_number)
            logging.debug('  Collision group mask: 0x%x', rigid.collision_group_mask)
            logging.debug('  Size: (%f, %f, %f)', *rigid.size)
            logging.debug('  Location: (%f, %f, %f)', *rigid.location)
            logging.debug('  Rotation: (%f, %f, %f)', *rigid.rotation)
            logging.debug('  Mass: %f', rigid.mass)
            logging.debug('  Bounce: %f', rigid.bounce)
            logging.debug('  Friction: %f', rigid.friction)
            logging.debug('')
        logging.info('----- Loaded %d rigid bodies', len(self.rigid_bodies))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Joints')
        logging.info('------------------------------')
        joint_count = fs.readUnsignedInt()
        self.joints = []
        for i in range(joint_count):
            joint = Joint()
            joint.load(fs)
            self.joints.append(joint)
            logging.info('Joint %d: %s', i, joint.name)
            logging.debug('  Rigid A: %s (index: %d)', self.rigid_bodies[joint.src_rigid].name, joint.src_rigid)
            logging.debug('  Rigid B: %s (index: %d)', self.rigid_bodies[joint.dest_rigid].name, joint.dest_rigid)
            logging.debug('  Location: (%f, %f, %f)', *joint.location)
            logging.debug('  Rotation: (%f, %f, %f)', *joint.rotation)
            logging.debug('  Location Limit: (%f, %f, %f) - (%f, %f, %f)', *(joint.minimum_location + joint.maximum_location))
            logging.debug('  Rotation Limit: (%f, %f, %f) - (%f, %f, %f)', *(joint.minimum_rotation + joint.maximum_rotation))
            logging.debug('  Spring: (%f, %f, %f)', *joint.spring_constant)
            logging.debug('  Spring(rotation): (%f, %f, %f)', *joint.spring_rotation_constant)
            logging.debug('')
        logging.info('----- Loaded %d joints', len(self.joints))

        logging.info('finished importing the model.')

def load(path):
    with FileReadStream(path) as fs:
        logging.info('****************************************')
        logging.info(' mmd_tools.pmd module')
        logging.info('----------------------------------------')
        logging.info(' Start load model data form a pmd file')
        logging.info('            by the mmd_tools.pmd modlue.')
        logging.info('')

        model = Model()
        model.load(fs)

        logging.info(' Finish loading.')
        logging.info('----------------------------------------')
        logging.info(' mmd_tools.pmd module')
        logging.info('****************************************')
        return model

########NEW FILE########
__FILENAME__ = pmx
# -*- coding: utf-8 -*-
import struct
import os
import logging

class InvalidFileError(Exception):
    pass
class UnsupportedVersionError(Exception):
    pass

class FileStream:
    def __init__(self, path, file_obj, pmx_header):
        self.__path = path
        self.__file_obj = file_obj
        self.__header = pmx_header

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def path(self):
        return self.__path

    def header(self):
        if self.__header is None:
            raise Exception
        return self.__header

    def setHeader(self, pmx_header):
        self.__header = pmx_header

    def close(self):
        if self.__file_obj is not None:
            logging.debug('close the file("%s")', self.__path)
            self.__file_obj.close()
            self.__file_obj = None

class FileReadStream(FileStream):
    def __init__(self, path, pmx_header=None):
        self.__fin = open(path, 'rb')
        FileStream.__init__(self, path, self.__fin, pmx_header)

    def __readIndex(self, size, typedict):
        index = None
        if size in typedict :
            index, = struct.unpack(typedict[size], self.__fin.read(size))
        else:
            raise ValueError('invalid data size %s'%str(size))
        return index

    def __readSignedIndex(self, size):
        return self.__readIndex(size, { 1 :"<b", 2 :"<h", 4 :"<i"})

    def __readUnsignedIndex(self, size):
        return self.__readIndex(size, { 1 :"<B", 2 :"<H", 4 :"<I"})


    # READ methods for indexes
    def readVertexIndex(self):
        return self.__readUnsignedIndex(self.header().vertex_index_size)

    def readBoneIndex(self):
        return self.__readSignedIndex(self.header().bone_index_size)

    def readTextureIndex(self):
        return self.__readSignedIndex(self.header().texture_index_size)

    def readMorphIndex(self):
        return self.__readSignedIndex(self.header().morph_index_size)

    def readRigidIndex(self):
        return self.__readSignedIndex(self.header().rigid_index_size)

    def readMaterialIndex(self):
        return self.__readSignedIndex(self.header().material_index_size)

    # READ / WRITE methods for general types
    def readInt(self):
        v, = struct.unpack('<i', self.__fin.read(4))
        return v

    def readShort(self):
        v, = struct.unpack('<h', self.__fin.read(2))
        return v

    def readUnsignedShort(self):
        v, = struct.unpack('<H', self.__fin.read(2))
        return v

    def readStr(self):
        length = self.readInt()
        fmt = '<' + str(length) + 's'
        buf, = struct.unpack(fmt, self.__fin.read(length))
        return str(buf, self.header().encoding.charset)

    def readFloat(self):
        v, = struct.unpack('<f', self.__fin.read(4))
        return v

    def readVector(self, size):
        fmt = '<'
        for i in range(size):
            fmt += 'f'
        return list(struct.unpack(fmt, self.__fin.read(4*size)))

    def readByte(self):
        v, = struct.unpack('<B', self.__fin.read(1))
        return v

    def readBytes(self, length):
        return self.__fin.read(length)

    def readSignedByte(self):
        v, = struct.unpack('<b', self.__fin.read(1))
        return v

class FileWriteStream(FileStream):
    def __init__(self, path, pmx_header=None):
        self.__fout = open(path, 'wb')
        FileStream.__init__(self, path, self.__fout, pmx_header)

    def __writeIndex(self, index, size, typedict):
        if size in typedict :
            self.__fout.write(struct.pack(typedict[size], int(index)))
        else:
            raise ValueError('invalid data size %s'%str(size))
        return

    def __writeSignedIndex(self, index, size):
        return self.__writeIndex(index, size, { 1 :"<b", 2 :"<h", 4 :"<i"})

    def __writeUnsignedIndex(self, index, size):
        return self.__writeIndex(index, size, { 1 :"<B", 2 :"<H", 4 :"<I"})

    # WRITE methods for indexes
    def writeVertexIndex(self, index):
        return self.__writeUnsignedIndex(index, self.header().vertex_index_size)

    def writeBoneIndex(self, index):
        return self.__writeSignedIndex(index, self.header().bone_index_size)

    def writeTextureIndex(self, index):
        return self.__writeSignedIndex(index, self.header().texture_index_size)

    def writeMorphIndex(self, index):
        return self.__writeSignedIndex(index, self.header().morph_index_size)

    def writeRigidIndex(self, index):
        return self.__writeSignedIndex(index, self.header().rigid_index_size)

    def writeMaterialIndex(self, index):
        return self.__writeSignedIndex(index, self.header().material_index_size)


    def writeInt(self, v):
        self.__fout.write(struct.pack('<i', int(v)))

    def writeShort(self, v):
        self.__fout.write(struct.pack('<h', int(v)))

    def writeUnsignedShort(self, v):
        self.__fout.write(struct.pack('<H', int(v)))

    def writeStr(self, v):
        data = v.encode(self.header().encoding.charset)
        self.writeInt(len(data))
        self.__fout.write(data)

    def writeFloat(self, v):
        self.__fout.write(struct.pack('<f', float(v)))

    def writeVector(self, v):
        l = len(v)
        fmt = '<'
        for i in range(l):
            fmt += 'f'
        self.__fout.write(struct.pack(fmt, *v))

    def writeByte(self, v):
        self.__fout.write(struct.pack('<B', int(v)))

    def writeBytes(self, v):
        self.__fout.write(v)

    def writeSignedByte(self, v):
        self.__fout.write(struct.pack('<b', int(v)))

class Encoding:
    _MAP = [
        (0, 'utf-16-le'),
        (1, 'utf-8'),
        ]

    def __init__(self, arg):
        self.index = 0
        self.charset = ''
        t = None
        if isinstance(arg, str):
            t = list(filter(lambda x: x[1]==arg, self._MAP))
            if len(t) == 0:
                raise ValueError('invalid charset %s'%arg)
        elif isinstance(arg, int):
            t = list(filter(lambda x: x[0]==arg, self._MAP))
            if len(t) == 0:
                raise ValueError('invalid index %d'%arg)
        else:
            raise ValueError('invalid argument type')
        t = t[0]
        self.index = t[0]
        self.charset  = t[1]

    def __repr__(self):
        return '<Encoding charset %s>'%self.charset

class Coordinate:
    """ """
    def __init__(self, xAxis, zAxis):
        self.x_axis = xAxis
        self.z_axis = zAxis

class Header:
    PMX_SIGN = b'PMX '
    VERSION = 2.0
    def __init__(self, model=None):
        self.sign = self.PMX_SIGN
        self.version = 0

        self.encoding = Encoding('utf-16-le')
        self.additional_uvs = 0

        self.vertex_index_size = 1
        self.vertex_index_size = 1
        self.material_index_size = 1
        self.bone_index_size = 1
        self.morph_index_size = 1
        self.rigid_index_size = 1

        if model is not None:
            self.updateIndexSizes(model)

    def updateIndexSizes(self, model):
        self.vertex_index_size = self.__getIndexSize(len(model.vertices), False)
        self.texture_index_size = self.__getIndexSize(len(model.textures), True)
        self.material_index_size = self.__getIndexSize(len(model.materials), True)
        self.bone_index_size = self.__getIndexSize(len(model.bones), True)
        self.morph_index_size = self.__getIndexSize(len(model.morphs), True)
        self.rigid_index_size = self.__getIndexSize(len(model.rigids), True)

    @staticmethod
    def __getIndexSize(num, signed):
        s = 1
        if signed:
            s = 2
        if (1<<8)/s > num:
            return 1
        elif (1<<16)/s > num:
            return 2
        else:
            return 4

    def load(self, fs):
        logging.info('loading pmx header information...')
        self.sign = fs.readBytes(4)
        logging.debug('File signature is %s', self.sign)
        if self.sign != self.PMX_SIGN:
            logging.info('File signature is invalid')
            logging.error('This file is unsupported format, or corrupt file.')
            raise InvalidFileError('File signature is invalid.')
        self.version = fs.readFloat()
        logging.info('pmx format version: %f', self.version)
        if self.version != self.VERSION:
            logging.error('PMX version %.1f is unsupported', self.version)
            raise UnsupportedVersionError('unsupported PMX version: %.1f'%self.version)
        if fs.readByte() != 8:
            raise InvalidFileError
        self.encoding = Encoding(fs.readByte())
        self.additional_uvs = fs.readByte()
        self.vertex_index_size = fs.readByte()
        self.texture_index_size = fs.readByte()
        self.material_index_size = fs.readByte()
        self.bone_index_size = fs.readByte()
        self.morph_index_size = fs.readByte()
        self.rigid_index_size = fs.readByte()

        logging.info('----------------------------')
        logging.info('pmx header information')
        logging.info('----------------------------')
        logging.info('pmx version: %.1f', self.version)
        logging.info('encoding: %s', str(self.encoding))
        logging.info('number of uvs: %d', self.additional_uvs)
        logging.info('vertex index size: %d byte(s)', self.vertex_index_size)
        logging.info('texture index: %d byte(s)', self.texture_index_size)
        logging.info('material index: %d byte(s)', self.material_index_size)
        logging.info('bone index: %d byte(s)', self.bone_index_size)
        logging.info('morph index: %d byte(s)', self.morph_index_size)
        logging.info('rigid index: %d byte(s)', self.rigid_index_size)
        logging.info('----------------------------')

    def save(self, fs):
        fs.writeBytes(self.PMX_SIGN)
        fs.writeFloat(self.VERSION)
        fs.writeByte(8)
        fs.writeByte(self.encoding.index)
        fs.writeByte(self.additional_uvs)
        fs.writeByte(self.vertex_index_size)
        fs.writeByte(self.texture_index_size)
        fs.writeByte(self.material_index_size)
        fs.writeByte(self.bone_index_size)
        fs.writeByte(self.morph_index_size)
        fs.writeByte(self.rigid_index_size)

    def __repr__(self):
        return '<Header encoding %s, uvs %d, vtx %d, tex %d, mat %d, bone %d, morph %d, rigid %d>'%(
            str(self.encoding),
            self.additional_uvs,
            self.vertex_index_size,
            self.texture_index_size,
            self.material_index_size,
            self.bone_index_size,
            self.morph_index_size,
            self.rigid_index_size,
            )

class Model:
    def __init__(self):
        self.header = None

        self.name = ''
        self.name_e = ''
        self.comment = ''
        self.comment_e = ''

        self.vertices = []
        self.faces = []
        self.textures = []
        self.materials = []
        self.bones = []
        self.morphs = []

        self.display = []
        dsp_root = Display()
        dsp_root.isSpecial = True
        dsp_root.name = 'Root'
        dsp_root.name_e = 'Root'
        self.display.append(dsp_root)
        dsp_face = Display()
        dsp_face.isSpecial = True
        dsp_face.name = '表情'
        dsp_face.name_e = ''
        self.display.append(dsp_face)

        self.rigids = []
        self.joints = []

    def load(self, fs):
        self.name = fs.readStr()
        self.name_e = fs.readStr()

        self.comment = fs.readStr()
        self.comment_e = fs.readStr()

        logging.info('Model name: %s', self.name)
        logging.info('Model name(english): %s', self.name_e)
        logging.info('Comment:%s', self.comment)
        logging.info('Comment(english):%s', self.comment_e)

        logging.info('')
        logging.info('------------------------------')
        logging.info('Load Vertices')
        logging.info('------------------------------')
        num_vertices = fs.readInt()
        self.vertices = []
        for i in range(num_vertices):
            v = Vertex()
            v.load(fs)
            self.vertices.append(v)
        logging.info('----- Loaded %d vertices', len(self.vertices))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Faces')
        logging.info('------------------------------')
        num_faces = fs.readInt()
        self.faces = []
        for i in range(int(num_faces/3)):
            f1 = fs.readVertexIndex()
            f2 = fs.readVertexIndex()
            f3 = fs.readVertexIndex()
            self.faces.append((f3, f2, f1))
        logging.info(' Load %d faces', len(self.faces))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Textures')
        logging.info('------------------------------')
        num_textures = fs.readInt()
        self.textures = []
        for i in range(num_textures):
            t = Texture()
            t.load(fs)
            self.textures.append(t)
            logging.info('Texture %d: %s', i, t.path)
        logging.info(' ----- Loaded %d textures', len(self.textures))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Materials')
        logging.info('------------------------------')
        num_materials = fs.readInt()
        self.materials = []
        for i in range(num_materials):
            m = Material()
            m.load(fs)
            self.materials.append(m)

            logging.info('Material %d: %s', i, m.name)
            logging.debug('  Name(english): %s', m.name_e)
            logging.debug('  Comment: %s', m.comment)
            logging.debug('  Vertex Count: %d', m.vertex_count)
            logging.debug('  Diffuse: (%.2f, %.2f, %.2f, %.2f)', *m.diffuse)
            logging.debug('  Specular: (%.2f, %.2f, %.2f, %.2f)', *m.specular)
            logging.debug('  Ambient: (%.2f, %.2f, %.2f)', *m.ambient)
            logging.debug('  Double Sided: %s', str(m.is_double_sided))
            logging.debug('  Drop Shadow: %s', str(m.enabled_drop_shadow))
            logging.debug('  Self Shadow: %s', str(m.enabled_self_shadow))
            logging.debug('  Self Shadow Map: %s', str(m.enabled_self_shadow_map))
            logging.debug('  Edge: %s', str(m.enabled_toon_edge))
            logging.debug('  Edge Color: (%.2f, %.2f, %.2f, %.2f)', *m.edge_color)
            logging.debug('  Edge Size: %.2f', m.edge_size)
            if m.texture != -1:
                logging.debug('  Texture Index: %d', m.texture)
            else:
                logging.debug('  Texture: None')
            if m.sphere_texture != -1:
                logging.debug('  Sphere Texture Index: %d', m.sphere_texture)
                logging.debug('  Sphere Texture Mode: %d', m.sphere_texture_mode)
            else:
                logging.debug('  Sphere Texture: None')
            logging.debug('')

        logging.info('----- Loaded %d  materials.', len(self.materials))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Bones')
        logging.info('------------------------------')
        num_bones = fs.readInt()
        self.bones = []
        for i in range(num_bones):
            b = Bone()
            b.load(fs)
            self.bones.append(b)

            logging.info('Bone %d: %s', i, b.name)
            logging.debug('  Name(english): %s', b.name_e)
            logging.debug('  Location: (%f, %f, %f)', *b.location)
            logging.debug('  Parent: %s', str(b.parent))
            logging.debug('  Transform Order: %s', str(b.transform_order))
            logging.debug('  Rotatable: %s', str(b.isRotatable))
            logging.debug('  Movable: %s', str(b.isMovable))
            logging.debug('  Visible: %s', str(b.visible))
            logging.debug('  Controllable: %s', str(b.isControllable))
            logging.debug('  Edge: %s', str(m.enabled_toon_edge))
            logging.debug('  Additional Location: %s', str(b.hasAdditionalRotate))
            logging.debug('  Additional Rotation: %s', str(b.hasAdditionalRotate))
            if b.additionalTransform is not None:
                logging.debug('  Additional Transform: Bone:%d, influence: %f', *b.additionalTransform)
            logging.debug('  IK: %s', str(b.isIK))
            if b.isIK:
                for j, link in enumerate(b.ik_links):
                    if isinstance(link.minimumAngle, list) and len(link.minimumAngle) == 3:
                        min_str = '(%f, %f, %f)'%tuple(link.minimumAngle)
                    else:
                        min_str = '(None, None, None)'
                    if isinstance(link.maximumAngle, list) and len(link.maximumAngle) == 3:
                        max_str = '(%f, %f, %f)'%tuple(link.maximumAngle)
                    else:
                        max_str = '(None, None, None)'
                    logging.debug('    IK Link %d: %d, %s - %s', j, link.target, min_str, max_str)
            logging.debug('')
        logging.info('----- Loaded %d bones.', len(self.bones))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Morphs')
        logging.info('------------------------------')
        num_morph = fs.readInt()
        self.morphs = []
        display_categories = {0: 'System', 1: 'Eyebrow', 2: 'Eye', 3: 'Mouth', 4: 'Other'}
        for i in range(num_morph):
            m = Morph.create(fs)
            self.morphs.append(m)

            logging.info('%s %d: %s', m.__class__.__name__, i, m.name)
            logging.debug('  Name(english): %s', m.name_e)
            logging.debug('  Category: %s', display_categories[m.category])
            logging.debug('')
        logging.info('----- Loaded %d morphs.', len(self.morphs))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Display Items')
        logging.info('------------------------------')
        num_disp = fs.readInt()
        self.display = []
        for i in range(num_disp):
            d = Display()
            d.load(fs)
            self.display.append(d)

            logging.info('Display Item %d: %s', i, d.name)
            logging.debug('  Name(english): %s', d.name_e)
            logging.debug('')
        logging.info('----- Loaded %d display items.', len(self.display))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Rigid Bodies')
        logging.info('------------------------------')
        num_rigid = fs.readInt()
        self.rigids = []
        rigid_types = {0: 'Sphere', 1: 'Box', 2: 'Capsule'}
        rigid_modes = {0: 'Static', 1: 'Dynamic', 2: 'Dynamic(track to bone)'}
        for i in range(num_rigid):
            r = Rigid()
            r.load(fs)
            self.rigids.append(r)
            logging.info('Rigid Body %d: %s', i, r.name)
            logging.debug('  Name(english): %s', r.name_e)
            logging.debug('  Type: %s', rigid_types[r.type])
            logging.debug('  Mode: %s', rigid_modes[r.mode])
            if r.bone is not None:
                logging.debug('  Related bone: %s (index: %d)', self.bones[r.bone].name, r.bone)
            logging.debug('  Collision group: %d', r.collision_group_number)
            logging.debug('  Collision group mask: 0x%x', r.collision_group_mask)
            logging.debug('  Size: (%f, %f, %f)', *r.size)
            logging.debug('  Location: (%f, %f, %f)', *r.location)
            logging.debug('  Rotation: (%f, %f, %f)', *r.rotation)
            logging.debug('  Mass: %f', r.mass)
            logging.debug('  Bounce: %f', r.bounce)
            logging.debug('  Friction: %f', r.friction)
            logging.debug('')

        logging.info('----- Loaded %d rigid bodies.', len(self.rigids))

        logging.info('')
        logging.info('------------------------------')
        logging.info(' Load Joints')
        logging.info('------------------------------')
        num_joints = fs.readInt()
        self.joints = []
        for i in range(num_joints):
            j = Joint()
            j.load(fs)
            self.joints.append(j)

            logging.info('Joint %d: %s', i, j.name)
            logging.debug('  Name(english): %s', j.name_e)
            logging.debug('  Rigid A: %s (index: %d)', self.rigids[j.src_rigid].name, j.src_rigid)
            logging.debug('  Rigid B: %s (index: %d)', self.rigids[j.dest_rigid].name, j.dest_rigid)
            logging.debug('  Location: (%f, %f, %f)', *j.location)
            logging.debug('  Rotation: (%f, %f, %f)', *j.rotation)
            logging.debug('  Location Limit: (%f, %f, %f) - (%f, %f, %f)', *(j.minimum_location + j.maximum_location))
            logging.debug('  Rotation Limit: (%f, %f, %f) - (%f, %f, %f)', *(j.minimum_rotation + j.maximum_rotation))
            logging.debug('  Spring: (%f, %f, %f)', *j.spring_constant)
            logging.debug('  Spring(rotation): (%f, %f, %f)', *j.spring_rotation_constant)
            logging.debug('')

        logging.info('----- Loaded %d joints.', len(self.joints))

    def save(self, fs):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)

        fs.writeStr(self.comment)
        fs.writeStr(self.comment_e)

        logging.info('''exportings pmx model data...
name: %s
name(english): %s
comment:
%s
comment(english):
%s
''', self.name, self.name_e, self.comment, self.comment_e)

        logging.info('exporting vertices...')
        fs.writeInt(len(self.vertices))
        for i in self.vertices:
            i.save(fs)
        logging.info('the number of vetices: %d', len(self.vertices))
        logging.info('finished exporting vertices.')

        logging.info('exporting faces...')
        fs.writeInt(len(self.faces)*3)
        for f3, f2, f1 in self.faces:
            fs.writeVertexIndex(f1)
            fs.writeVertexIndex(f2)
            fs.writeVertexIndex(f3)
        logging.info('the number of faces: %d', len(self.faces))
        logging.info('finished exporting faces.')

        logging.info('exporting textures...')
        fs.writeInt(len(self.textures))
        for i in self.textures:
            i.save(fs)
        logging.info('the number of textures: %d', len(self.textures))
        logging.info('finished exporting textures.')

        logging.info('exporting materials...')
        fs.writeInt(len(self.materials))
        for i in self.materials:
            i.save(fs)
        logging.info('the number of materials: %d', len(self.materials))
        logging.info('finished exporting materials.')

        logging.info('exporting bones...')
        fs.writeInt(len(self.bones))
        for i in self.bones:
            i.save(fs)
        logging.info('the number of bones: %d', len(self.bones))
        logging.info('finished exporting bones.')

        logging.info('exporting morphs...')
        fs.writeInt(len(self.morphs))
        for i in self.morphs:
            i.save(fs)
        logging.info('the number of morphs: %d', len(self.morphs))
        logging.info('finished exporting morphs.')

        logging.info('exporting display items...')
        fs.writeInt(len(self.display))
        for i in self.display:
            i.save(fs)
        logging.info('the number of display items: %d', len(self.display))
        logging.info('finished exporting display items.')

        logging.info('exporting rigid bodies...')
        fs.writeInt(len(self.rigids))
        for i in self.rigids:
            i.save(fs)
        logging.info('the number of rigid bodies: %d', len(self.display))
        logging.info('finished exporting rigid bodies.')

        logging.info('exporting joints...')
        fs.writeInt(len(self.joints))
        for i in self.joints:
            i.save(fs)
        logging.info('the number of joints: %d', len(self.display))
        logging.info('finished exporting joints.')
        logging.info('finished exporting the model.')


    def __repr__(self):
        return '<Model name %s, name_e %s, comment %s, comment_e %s, textures %s>'%(
            self.name,
            self.name_e,
            self.comment,
            self.comment_e,
            str(self.textures),
            )

class Vertex:
    def __init__(self):
        self.co = [0.0, 0.0, 0.0]
        self.normal = [0.0, 0.0, 0.0]
        self.uv = [0.0, 0.0]
        self.additional_uvs = []
        self.weight = None
        self.edge_scale = 1

    def __repr__(self):
        return '<Vertex co %s, normal %s, uv %s, additional_uvs %s, weight %s, edge_scale %s>'%(
            str(self.co),
            str(self.normal),
            str(self.uv),
            str(self.additional_uvs),
            str(self.weight),
            str(self.edge_scale),
            )

    def load(self, fs):
        self.co = fs.readVector(3)
        self.normal = fs.readVector(3)
        self.uv = fs.readVector(2)
        self.additional_uvs = []
        for i in range(fs.header().additional_uvs):
            self.additional_uvs.append(fs.readVector(4))
        self.weight = BoneWeight()
        self.weight.load(fs)
        self.edge_scale = fs.readFloat()

    def save(self, fs):
        fs.writeVector(self.co)
        fs.writeVector(self.normal)
        fs.writeVector(self.uv)
        for i in self.additional_uvs:
            fs.writeVector(i)
        self.weight.save(fs)
        fs.writeFloat(self.edge_scale)

class BoneWeightSDEF:
    def __init__(self, weight=0, c=None, r0=None, r1=None):
        self.weight = weight
        self.c = c
        self.r0 = r0
        self.r1 = r1

class BoneWeight:
    BDEF1 = 0
    BDEF2 = 1
    BDEF4 = 2
    SDEF  = 3

    TYPES = [
        (BDEF1, 'BDEF1'),
        (BDEF2, 'BDEF2'),
        (BDEF4, 'BDEF4'),
        (SDEF, 'SDEF'),
        ]

    def __init__(self):
        self.bones = []
        self.weights = []

    def convertIdToName(self, type_id):
        t = list(filter(lambda x: x[0]==type_id, TYPES))
        if len(t) > 0:
            return t[0][1]
        else:
            return None

    def convertNameToId(self, type_name):
        t = list(filter(lambda x: x[1]==type_name, TYPES))
        if len(t) > 0:
            return t[0][0]
        else:
            return None

    def load(self, fs):
        self.type = fs.readByte()
        self.bones = []
        self.weights = []

        if self.type == self.BDEF1:
            self.bones.append(fs.readBoneIndex())
        elif self.type == self.BDEF2:
            self.bones.append(fs.readBoneIndex())
            self.bones.append(fs.readBoneIndex())
            self.weights.append(fs.readFloat())
        elif self.type == self.BDEF4:
            self.bones.append(fs.readBoneIndex())
            self.bones.append(fs.readBoneIndex())
            self.bones.append(fs.readBoneIndex())
            self.bones.append(fs.readBoneIndex())
            self.weights = fs.readVector(4)
        elif self.type == self.SDEF:
            self.bones.append(fs.readBoneIndex())
            self.bones.append(fs.readBoneIndex())
            self.weights = BoneWeightSDEF()
            self.weights.weight = fs.readFloat()
            self.weights.c = fs.readVector(3)
            self.weights.r0 = fs.readVector(3)
            self.weights.r1 = fs.readVector(3)
        else:
            raise ValueError('invalid weight type %s'%str(self.type))

    def save(self, fs):
        fs.writeByte(self.type)
        if self.type == self.BDEF1:
            fs.writeBoneIndex(self.bones[0])
        elif self.type == self.BDEF2:
            for i in range(2):
                fs.writeBoneIndex(self.bones[i])
            fs.writeFloat(self.weights[0])
        elif self.type == self.BDEF4:
            for i in range(4):
                fs.writeBoneIndex(self.bones[i])
            fs.writeFloat(self.weights[0])
        elif self.type == self.SDEF:
            for i in range(2):
                fs.writeBoneIndex(self.bones[i])
            if not isinstance(self.weights, BoneWeightSDEF):
                raise ValueError
            fs.writeFloat(self.weights.weight)
            fs.writeVector(self.weight.c)
            fs.writeVector(self.weight.r0)
            fs.writeVector(self.weight.r1)
        else:
            raise ValueError('invalid weight type %s'%str(self.type))


class Texture:
    def __init__(self):
        self.path = ''

    def __repr__(self):
        return '<Texture path %s>'%str(self.path)

    def load(self, fs):
        self.path = fs.readStr()
        if not os.path.isabs(self.path):
            self.path = os.path.normpath(os.path.join(os.path.dirname(fs.path()), self.path))

    def save(self, fs):
        fs.writeStr(self.path)

class SharedTexture(Texture):
    def __init__(self):
        self.number = 0
        self.prefix = ''

class Material:
    SPHERE_MODE_OFF = 0
    SPHERE_MODE_MULT = 1
    SPHERE_MODE_ADD = 2
    SPHERE_MODE_SUB = 3

    def __init__(self):
        self.name = ''
        self.name_e = ''

        self.diffuse = []
        self.specular = []
        self.ambient = []

        self.is_double_sided = False
        self.enabled_drop_shadow = False
        self.enabled_self_shadow_map = False
        self.enabled_self_shadow = False
        self.enabled_toon_edge = False

        self.edge_color = []
        self.edge_size = 1

        self.texture = -1
        self.sphere_texture = -1
        self.sphere_texture_mode = 0
        self.is_shared_toon_texture = True
        self.toon_texture = 0

        self.comment = ''
        self.vertex_count = 0

    def __repr__(self):
        return '<Material name %s, name_e %s, diffuse %s, specular %s, ambient %s, double_side %s, drop_shadow %s, self_shadow_map %s, self_shadow %s, toon_edge %s, edge_color %s, edge_size %s, toon_texture %s, comment %s>'%(
            self.name,
            self.name_e,
            str(self.diffuse),
            str(self.specular),
            str(self.ambient),
            str(self.is_double_sided),
            str(self.enabled_drop_shadow),
            str(self.enabled_self_shadow_map),
            str(self.enabled_self_shadow),
            str(self.enabled_toon_edge),
            str(self.edge_color),
            str(self.edge_size),
            str(self.texture),
            str(self.sphere_texture),
            str(self.toon_texture),
            str(self.comment),)

    def load(self, fs):
        self.name = fs.readStr()
        self.name_e = fs.readStr()

        self.diffuse = fs.readVector(4)
        self.specular = fs.readVector(4)
        self.ambient = fs.readVector(3)

        flags = fs.readByte()
        self.is_double_sided = bool(flags & 1)
        self.enabled_drop_shadow = bool(flags & 2)
        self.enabled_self_shadow_map = bool(flags & 4)
        self.enabled_self_shadow = bool(flags & 8)
        self.enabled_toon_edge = bool(flags & 16)

        self.edge_color = fs.readVector(4)
        self.edge_size = fs.readFloat()

        self.texture = fs.readTextureIndex()
        self.sphere_texture = fs.readTextureIndex()
        self.sphere_texture_mode = fs.readSignedByte()

        self.is_shared_toon_texture = fs.readSignedByte()
        self.is_shared_toon_texture = (self.is_shared_toon_texture == 1)
        if self.is_shared_toon_texture:
            self.toon_texture = fs.readSignedByte()
        else:
            self.toon_texture = fs.readTextureIndex()

        self.comment = fs.readStr()
        self.vertex_count = fs.readInt()

    def save(self, fs):
        fs.writeStr(self.name)
        fs.writeStr(self.name)

        fs.writeVector(self.diffuse)
        fs.writeVector(self.specular)
        fs.writeVector(self.ambient)

        flags = 0
        flags |= int(self.is_double_sided)
        flags |= int(self.enabled_drop_shadow) << 1
        flags |= int(self.enabled_self_shadow_map) << 2
        flags |= int(self.enabled_self_shadow) << 3
        flags |= int(self.enabled_toon_edge) << 4
        fs.writeByte(flags)

        fs.writeVector(self.edge_color)
        fs.writeFloat(self.edge_size)

        fs.writeTextureIndex(self.texture)
        fs.writeTextureIndex(self.sphere_texture)
        fs.writeSignedByte(self.sphere_texture_mode)

        fs.writeSignedByte(int(self.is_shared_toon_texture))
        if self.is_shared_toon_texture:
            fs.writeSignedByte(self.toon_texture)
        else:
            fs.writeTextureIndex(self.toon_texture)

        fs.writeStr(self.comment)
        fs.writeInt(self.vertex_count)


class Bone:
    def __init__(self):
        self.name = ''
        self.name_e = ''

        self.location = []
        self.parent = None
        self.transform_order = 0

        # 接続先表示方法
        # 座標オフセット(float3)または、boneIndex(int)
        self.displayConnection = -1

        self.isRotatable = True
        self.isMovable = True
        self.visible = True
        self.isControllable = True

        self.isIK = False

        # 回転付与
        self.hasAdditionalRotate = False

        # 移動付与
        self.hasAdditionalLocation = False

        # 回転付与および移動付与の付与量
        self.additionalTransform = None

        # 軸固定
        # 軸ベクトルfloat3
        self.axis = None

        # ローカル軸
        self.localCoordinate = None

        self.transAfterPhis = False

        # 外部親変形
        self.externalTransKey = None

        # 以下IKボーンのみ有効な変数
        self.target = None
        self.loopCount = 0
        # IKループ計三時の1回あたりの制限角度(ラジアン)
        self.rotationConstraint = 0

        # IKLinkオブジェクトの配列
        self.ik_links = []

    def __repr__(self):
        return '<Bone name %s, name_e %s>'%(
            self.name,
            self.name_e,)

    def load(self, fs):
        self.name = fs.readStr()
        self.name_e = fs.readStr()

        self.location = fs.readVector(3)
        self.parent = fs.readBoneIndex()
        self.transform_order = fs.readInt()

        flags = fs.readShort()
        if flags & 0x0001:
            self.displayConnection = fs.readBoneIndex()
        else:
            self.displayConnection = fs.readVector(3)

        self.isRotatable    = ((flags & 0x0002) != 0)
        self.isMovable      = ((flags & 0x0004) != 0)
        self.visible        = ((flags & 0x0008) != 0)
        self.isControllable = ((flags & 0x0010) != 0)

        self.isIK           = ((flags & 0x0020) != 0)

        self.hasAdditionalRotate = ((flags & 0x0100) != 0)
        self.hasAdditionalLocation = ((flags & 0x0200) != 0)
        if self.hasAdditionalRotate or self.hasAdditionalLocation:
            t = fs.readBoneIndex()
            v = fs.readFloat()
            self.additionalTransform = (t, v)
        else:
            self.additionalTransform = None


        if flags & 0x0400:
            self.axis = fs.readVector(3)
        else:
            self.axis = None

        if flags & 0x0800:
            xaxis = fs.readVector(3)
            zaxis = fs.readVector(3)
            self.localCoordinate = Coordinate(xaxis, zaxis)
        else:
            self.localCoordinate = None

        self.transAfterPhis = ((flags & 0x1000) != 0)

        if flags & 0x2000:
            self.externalTransKey = fs.readInt()
        else:
            self.externalTransKey = None

        if self.isIK:
            self.target = fs.readBoneIndex()
            self.loopCount = fs.readInt()
            self.rotationConstraint = fs.readFloat()

            iklink_num = fs.readInt()
            self.ik_links = []
            for i in range(iklink_num):
                link = IKLink()
                link.load(fs)
                self.ik_links.append(link)

    def save(self, fs):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)

        fs.writeVector(self.location)
        fs.writeBoneIndex(self.parent or -1)
        fs.writeInt(self.transform_order)

        flags = 0
        flags |= int(isinstance(self.displayConnection, int))
        flags |= int(self.isRotatable) << 1
        flags |= int(self.isMovable) << 2
        flags |= int(self.visible) << 3
        flags |= int(self.isControllable) << 4
        flags |= int(self.isIK) << 5

        flags |= int(self.hasAdditionalRotate) << 8
        flags |= int(self.hasAdditionalLocation) << 9
        flags |= int(self.axis is not None) << 10
        flags |= int(self.localCoordinate is not None) << 11

        flags |= int(self.externalTransKey is not None) << 13

        fs.writeShort(flags)

        if flags & 0x0001:
            fs.writeBoneIndex(self.displayConnection)
        else:
            fs.writeVector(self.displayConnection)

        if self.hasAdditionalRotate or self.hasAdditionalLocation:
            fs.writeBoneIndex(self.additionalTransform[0])
            fs.writeFloat(self.additionalTransform[1])

        if flags & 0x0400:
            fs.writeVector(self.axis)

        if flags & 0x0800:
            fs.writeVector(self.localCoordinate.x_axis)
            fs.writeVector(self.localCoordinate.z_axis)

        if flags & 0x2000:
            fs.writeInt(self.externalTransKey)

        if self.isIK:
            fs.writeBoneIndex(self.target)
            fs.writeInt(self.loopCount)
            fs.writeFloat(self.rotationConstraint)

            fs.writeInt(len(self.ik_links))
            for i in self.ik_links:
                i.save(fs)


class IKLink:
    def __init__(self):
        self.target = None
        self.maximumAngle = None
        self.minimumAngle = None

    def __repr__(self):
        return '<IKLink target %s>'%(str(self.target))

    def load(self, fs):
        self.target = fs.readBoneIndex()
        flag = fs.readByte()
        if flag == 1:
            self.minimumAngle = fs.readVector(3)
            self.maximumAngle = fs.readVector(3)
        else:
            self.minimumAngle = None
            self.maximumAngle = None

    def save(self, fs):
        fs.writeBoneIndex(self.target)
        if isinstance(self.minimumAngle, list) and isinstance(self.maximumAngle, list):
            fs.writeByte(1)
            fs.writeVector(self.minimumAngle)
            fs.writeVector(self.maximumAngle)
        else:
            fs.writeByte(0)

class Morph:
    CATEGORY_SYSTEM = 0
    CATEGORY_EYEBROW = 1
    CATEGORY_EYE = 2
    CATEGORY_MOUTH = 3
    CATEGORY_OHTER = 4

    def __init__(self, name, name_e, category, **kwargs):
        self.offsets = []
        self.name = name
        self.name_e = name_e
        self.category = category

    def __repr__(self):
        return '<Morph name %s, name_e %s>'%(self.name, self.name_e)

    @staticmethod
    def create(fs):
        _CLASSES = {
            0: GroupMorph,
            1: VertexMorph,
            2: BoneMorph,
            3: UVMorph,
            4: UVMorph,
            5: UVMorph,
            6: UVMorph,
            7: UVMorph,
            8: MaterialMorph,
            }

        name = fs.readStr()
        name_e = fs.readStr()
        logging.debug('morph: %s', name)
        category = fs.readSignedByte()
        typeIndex = fs.readSignedByte()
        ret = _CLASSES[typeIndex](name, name_e, category, type_index = typeIndex)
        ret.load(fs)
        return ret

    def load(self, fs):
        """ Implement for loading morph data.
        """
        raise NotImplementedError

    def save(self, fs):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)
        fs.writeSignedByte(self.category)
        fs.writeSignedByte(self.type_index())
        fs.writeInt(len(self.offsets))
        for i in self.offsets:
            i.save(fs)

class VertexMorph(Morph):
    def __init__(self, *args, **kwargs):
        Morph.__init__(self, *args, **kwargs)

    def type_index(self):
        return 1

    def load(self, fs):
        num = fs.readInt()
        for i in range(num):
            t = VertexMorphOffset()
            t.load(fs)
            self.offsets.append(t)

class VertexMorphOffset:
    def __init__(self):
        self.index = 0
        self.offset = []

    def load(self, fs):
        self.index = fs.readVertexIndex()
        self.offset = fs.readVector(3)

    def save(self, fs):
        fs.writeVertexIndex(self.index)
        fs.writeVector(self.offset)

class UVMorph(Morph):
    def __init__(self, *args, **kwargs):
        self.uv_index = kwargs.get('type_index', 3) - 3
        Morph.__init__(self, *args, **kwargs)

    def type_index(self):
        return self.uv_index + 3

    def load(self, fs):
        self.offsets = []
        num = fs.readInt()
        for i in range(num):
            t = UVMorphOffset()
            t.load(fs)
            self.offsets.append(t)

class UVMorphOffset:
    def __init__(self):
        self.index = 0
        self.offset = []

    def load(self, fs):
        self.index = fs.readVertexIndex()
        self.offset = fs.readVector(4)

    def save(self, fs):
        fs.writeVertexIndex(self.index)
        fs.writeVector(self.offset)

class BoneMorph(Morph):
    def __init__(self, *args, **kwargs):
        Morph.__init__(self, *args, **kwargs)

    def type_index(self):
        return 2

    def load(self, fs):
        self.offsets = []
        num = fs.readInt()
        for i in range(num):
            t = BoneMorphOffset()
            t.load(fs)
            self.offsets.append(t)

class BoneMorphOffset:
    def __init__(self):
        self.index = None
        self.location_offset = []
        self.rotation_offset = []

    def load(self, fs):
        self.index = fs.readBoneIndex()
        self.location_offset = fs.readVector(3)
        self.rotation_offset = fs.readVector(4)

    def save(self, fs):
        fs.writeBoneIndex(self.index)
        fs.writeVector(self.location_offset)
        fs.writeVector(self.rotation_offset)

class MaterialMorph:
    def __init__(self, *args, **kwargs):
        Morph.__init__(self, *args, **kwargs)

    def type_index(self):
        return 8

    def load(self, fs):
        self.offsets = []
        num = fs.readInt()
        for i in range(num):
            t = MaterialMorphOffset()
            t.load(fs)
            self.offsets.append(t)

class MaterialMorphOffset:
    TYPE_MULT = 0
    TYPE_ADD = 1

    def __init__(self):
        self.index = 0
        self.offset_type = 0
        self.diffuse_offset = []
        self.specular_offset = []
        self.ambient_offset = []
        self.edge_color_offset = []
        self.edge_size_offset = []
        self.texture_factor = []
        self.sphere_texture_factor = []
        self.toon_texture_factor = []

    def load(self, fs):
        self.index = fs.readMaterialIndex()
        self.offset_type = fs.readSignedByte()
        self.diffuse_offset = fs.readVector(4)
        self.specular_offset = fs.readVector(4)
        self.ambient_offset = fs.readVector(3)
        self.edge_color_offset = fs.readVector(4)
        self.edge_size_offset = fs.readFloat()
        self.texture_factor = fs.readVector(4)
        self.sphere_texture_factor = fs.readVector(4)
        self.toon_texture_factor = fs.readVector(4)

    def save(self, fs):
        fs.writeMaterialIndex(self.index)
        fs.writeSignedByte(self.offset_type)
        fs.writeVector(self.diffuse_offset)
        fs.writeVector(self.specular_offset)
        fs.writeVector(self.ambient_offset)
        fs.writeVector(self.edge_color_offset)
        fs.writeFloat(self.edge_size_offset)
        fs.writeVector(self.texture_factor)
        fs.writeVector(self.sphere_texture_factor)
        fs.writeVector(self.toon_texture_factor)

class GroupMorph(Morph):
    def __init__(self, *args, **kwargs):
        Morph.__init__(self, *args, **kwargs)

    def type_index(self):
        return 0

    def load(self, fs):
        self.offsets = []
        num = fs.readInt()
        for i in range(num):
            t = GroupMorphOffset()
            t.load(fs)
            self.offsets.append(t)

class GroupMorphOffset:
    def __init__(self):
        self.morph = None
        self.factor = 0.0

    def load(self, fs):
        self.morph = fs.readMorphIndex()
        self.factor = fs.readFloat()

    def save(self, fs):
        fs.writeMorphIndex(self.morph)
        fs.writeFloat(self.factor)


class Display:
    def __init__(self):
        self.name = ''
        self.name_e = ''

        self.isSpecial = False

        self.data = []

    def __repr__(self):
        return '<Display name %s, name_e %s>'%(
            self.name,
            self.name_e,
            )

    def load(self, fs):
        self.name = fs.readStr()
        self.name_e = fs.readStr()

        self.isSpecial = (fs.readByte() == 1)
        num = fs.readInt()
        self.data = []
        for i in range(num):
            disp_type = fs.readByte()
            index = None
            if disp_type == 0:
                index = fs.readBoneIndex()
            elif disp_type == 1:
                index = fs.readMorphIndex()
            else:
                raise Exception('invalid value.')
            self.data.append((disp_type, index))
        logging.debug('the number of display elements: %d', len(self.data))

    def save(self, fs):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)

        fs.writeByte(int(self.isSpecial))
        fs.writeInt(len(self.data))

        for disp_type, index in self.data:
            fs.writeByte(disp_type)
            if disp_type == 0:
                fs.writeBoneIndex(index)
            elif disp_type == 1:
                fs.writeMorphIndex(index)
            else:
                raise Exception('invalid value.')

class Rigid:
    TYPE_SPHERE = 0
    TYPE_BOX = 1
    TYPE_CAPSULE = 2

    MODE_STATIC = 0
    MODE_DYNAMIC = 1
    MODE_DYNAMIC_BONE = 2
    def __init__(self):
        self.name = ''
        self.name_e = ''

        self.bone = None
        self.collision_group_number = 0
        self.collision_group_mask = 0

        self.type = 0
        self.size = []

        self.location = []
        self.rotation = []

        self.mass = 1
        self.velocity_attenuation = []
        self.rotation_attenuation = []
        self.bounce = []
        self.friction = []

        self.mode = 0

    def __repr__(self):
        return '<Rigid name %s, name_e %s>'%(
            self.name,
            self.name_e,
            )

    def load(self, fs):
        self.name = fs.readStr()
        self.name_e = fs.readStr()

        boneIndex = fs.readBoneIndex()
        if boneIndex != -1:
            self.bone = boneIndex
        else:
            self.bone = None

        self.collision_group_number = fs.readSignedByte()
        self.collision_group_mask = fs.readUnsignedShort()

        self.type = fs.readSignedByte()
        self.size = fs.readVector(3)

        self.location = fs.readVector(3)
        self.rotation = fs.readVector(3)

        self.mass = fs.readFloat()
        self.velocity_attenuation = fs.readFloat()
        self.rotation_attenuation = fs.readFloat()
        self.bounce = fs.readFloat()
        self.friction = fs.readFloat()

        self.mode = fs.readSignedByte()

    def save(self, fs):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)

        if self.bone is None:
            fs.writeBoneIndex(-1)
        else:
            fs.writeBoneIndex(self.bone)

        fs.writeSignedByte(self.collision_group_number)
        fs.writeUnsignedShort(self.collision_group_mask)

        fs.writeSignedByte(self.type)
        fs.writeVector(self.size)

        fs.writeVector(self.location)
        fs.writeVector(self.rotation)

        fs.writeFloat(self.mass)
        fs.writeFloat(self.velocity_attenuation)
        fs.writeFloat(self.rotation_attenuation)
        fs.writeFloat(self.bounce)
        fs.writeFloat(self.friction)

        fs.writeSignedByte(self.mode)

class Joint:
    MODE_SPRING6DOF = 0
    def __init__(self):
        self.name = ''
        self.name_e = ''

        self.mode = 0

        self.src_rigid = None
        self.dest_rigid = None

        self.location = []
        self.rotation = []

        self.maximum_location = []
        self.minimum_location = []
        self.maximum_rotation = []
        self.minimum_rotation = []

        self.spring_constant = []
        self.spring_rotation_constant = []

    def load(self, fs):
        self.name = fs.readStr()
        self.name_e = fs.readStr()

        self.mode = fs.readSignedByte()

        self.src_rigid = fs.readRigidIndex()
        self.dest_rigid = fs.readRigidIndex()
        if self.src_rigid == -1:
            self.src_rigid = None
        if self.dest_rigid == -1:
            self.dest_rigid = None

        self.location = fs.readVector(3)
        self.rotation = fs.readVector(3)

        self.minimum_location = fs.readVector(3)
        self.maximum_location = fs.readVector(3)
        self.minimum_rotation = fs.readVector(3)
        self.maximum_rotation = fs.readVector(3)

        self.spring_constant = fs.readVector(3)
        self.spring_rotation_constant = fs.readVector(3)

    def save(self, fs):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)

        fs.writeSignedByte(self.mode)

        if self.src_rigid is not None:
            fs.writeRigidIndex(self.src_rigid)
        else:
            fs.writeRigidIndex(-1)
        if self.dest_rigid is not None:
            fs.writeRigidIndex(self.dest_rigid)
        else:
            fs.writeRigidIndex(-1)

        fs.writeVector(self.location)
        fs.writeVector(self.rotation)

        fs.writeVector(self.minimum_location)
        fs.writeVector(self.maximum_location)
        fs.writeVector(self.minimum_rotation)
        fs.writeVector(self.maximum_rotation)

        fs.writeVector(self.spring_constant)
        fs.writeVector(self.spring_rotation_constant)



def load(path):
    with FileReadStream(path) as fs:
        logging.info('****************************************')
        logging.info(' mmd_tools.pmx module')
        logging.info('----------------------------------------')
        logging.info(' Start to load model data form a pmx file')
        logging.info('            by the mmd_tools.pmx modlue.')
        logging.info('')
        header = Header()
        header.load(fs)
        fs.setHeader(header)
        model = Model()
        model.load(fs)
        logging.info(' Finished loading.')
        logging.info('----------------------------------------')
        logging.info(' mmd_tools.pmx module')
        logging.info('****************************************')
        return model

def save(path, model):
    with FileWriteStream(path) as fs:
        header = Header(model)
        header.save(fs)
        fs.setHeader(header)
        model.save(fs)

########NEW FILE########
__FILENAME__ = rigging
# -*- coding: utf-8 -*-

import bpy

import re

def isRigidBodyObject(obj):
    return obj.is_mmd_rigid and not (obj.is_mmd_rigid_track_target or obj.is_mmd_spring_goal or obj.is_mmd_spring_joint)

def isJointObject(obj):
    return obj.is_mmd_joint

def isTemporaryObject(obj):
    return obj.is_mmd_rigid_track_target or obj.is_mmd_spring_goal or obj.is_mmd_spring_joint or obj.is_mmd_non_collision_constraint

def findRididBodyObjects():
    return filter(isRigidBodyObject, bpy.context.scene.objects)

def findJointObjects():
    return filter(isJointObject, bpy.context.scene.objects)

def findTemporaryObjects():
    return filter(isTemporaryObject, bpy.context.scene.objects)



########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
import re
import math

## 指定したオブジェクトのみを選択状態かつアクティブにする
def selectAObject(obj):
    import bpy
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.scene.objects.active = obj
    obj.select=True

## 現在のモードを指定したオブジェクトのEdit Modeに変更する
def enterEditMode(obj):
    import bpy
    selectAObject(obj)
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

def setParentToBone(obj, parent, bone_name):
    import bpy
    selectAObject(parent)
    bpy.ops.object.mode_set(mode='POSE')
    selectAObject(obj)
    bpy.context.scene.objects.active = parent
    parent.select = True
    bpy.ops.object.mode_set(mode='POSE')
    parent.data.bones.active = parent.data.bones[bone_name]
    bpy.ops.object.parent_set(type='BONE', xmirror=False, keep_transform=False)
    bpy.ops.object.mode_set(mode='OBJECT')


__CONVERT_NAME_TO_L_REGEXP = re.compile('^(.*)左(.*)$')
__CONVERT_NAME_TO_R_REGEXP = re.compile('^(.*)右(.*)$')
## 日本語で左右を命名されている名前をblender方式のL(R)に変更する
def convertNameToLR(name):
    m = __CONVERT_NAME_TO_L_REGEXP.match(name)
    if m:
        name = m.group(1) + m.group(2) + '.L'
    m = __CONVERT_NAME_TO_R_REGEXP.match(name)
    if m:
        name = m.group(1) + m.group(2) + '.R'
    return name

## src_vertex_groupのWeightをdest_vertex_groupにaddする
def mergeVertexGroup(meshObj, src_vertex_group_name, dest_vertex_group_name):
    mesh = meshObj.data
    src_vertex_group = meshObj.vertex_groups[src_vertex_group_name]
    dest_vertex_group = meshObj.vertex_groups[dest_vertex_group_name]

    vtxIndex = src_vertex_group.index
    for v in mesh.vertices:
        try:
            gi = [i.group for i in v.groups].index(vtxIndex)
            dest_vertex_group.add([v.index], v.groups[gi].weight, 'ADD')
        except ValueError:
            pass

def separateByMaterials(meshObj):
    import bpy
    prev_parent = meshObj.parent
    dummy_parent = bpy.data.objects.new(name='tmp', object_data=None)
    meshObj.parent = dummy_parent

    enterEditMode(meshObj)
    try:
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='MATERIAL')
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    for i in dummy_parent.children:
        mesh = i.data
        if len(mesh.polygons) > 0:
            mat_index = mesh.polygons[0].material_index
            mat = mesh.materials[mat_index]
            for k in mesh.materials:
                mesh.materials.pop(index=0, update_data=True)
            mesh.materials.append(mat)
            for po in mesh.polygons:
                po.material_index = 0
            i.name = mat.name
            i.parent = prev_parent


## Boneのカスタムプロパティにname_jが存在する場合、name_jの値を
# それ以外の場合は通常のbone名をキーとしたpose_boneへの辞書を作成
def makePmxBoneMap(armObj):
    boneMap = {}
    for i in armObj.pose.bones:
        boneMap[i.get('mmd_bone_name_j', i.get('name_j', i.name))] = i
    return boneMap


def makeCapsule(segment=16, ring_count=8, radius=1.0, height=1.0, target_scene=None):
    import bpy
    if target_scene is None:
        target_scene = bpy.context.scene
    mesh = bpy.data.meshes.new(name='Capsule')
    meshObj = bpy.data.objects.new(name='Capsule', object_data=mesh)
    vertices = []
    top = (0, 0, height/2+radius)
    vertices.append(top)

    f = lambda i: radius*i/ring_count
    for i in range(ring_count, 0, -1):
        z = f(i-1)
        t = math.sqrt(radius**2 - z**2)
        for j in range(segment):
            theta = 2*math.pi/segment*j
            x = t * math.sin(-theta)
            y = t * math.cos(-theta)
            vertices.append((x,y,z+height/2))

    for i in range(ring_count):
        z = -f(i)
        t = math.sqrt(radius**2 - z**2)
        for j in range(segment):
            theta = 2*math.pi/segment*j
            x = t * math.sin(-theta)
            y = t * math.cos(-theta)
            vertices.append((x,y,z-height/2))

    bottom = (0, 0, -(height/2+radius))
    vertices.append(bottom)

    faces = []
    for i in range(1, segment):
        faces.append([0, i, i+1])
    faces.append([0, segment, 1])
    offset = segment + 1
    for i in range(ring_count*2-1):
        for j in range(segment-1):
            t = offset + j
            faces.append([t-segment, t, t+1, t-segment+1])
        faces.append([offset-1, offset+segment-1, offset, offset-segment])
        offset += segment
    for i in range(segment-1):
        t = offset + i
        faces.append([t-segment, offset, t-segment+1])
    faces.append([offset-1, offset, offset-segment])

    mesh.from_pydata(vertices, [], faces)
    target_scene.objects.link(meshObj)
    return meshObj

########NEW FILE########
__FILENAME__ = vmd
# -*- coding: utf-8 -*-
import struct
import collections


## vmd仕様の文字列をstringに変換
def _toShiftJisString(byteString):
    byteString = byteString.split(b"\x00")[0]
    try:
        return byteString.decode("shift_jis")
    except UnicodeDecodeError:
        # discard truncated sjis char
        return byteString[:-1].decode("shift_jis")


class Header:
    def __init__(self):
        self.signature = None
        self.model_name = ''

    def load(self, fin):
        self.signature, = struct.unpack('<30s', fin.read(30))
        self.model_name = _toShiftJisString(struct.unpack('<20s', fin.read(20))[0])

    def __repr__(self):
        return '<Header model_name %s>'%(self.model_name)


class BoneFrameKey:
    def __init__(self):
        self.frame_number = 0
        self.location = []
        self.rotation = []
        self.interp = []

    def load(self, fin):
        self.frame_number, = struct.unpack('<L', fin.read(4))
        self.location = list(struct.unpack('<fff', fin.read(4*3)))
        self.rotation = list(struct.unpack('<ffff', fin.read(4*4)))
        self.interp = list(struct.unpack('<64b', fin.read(64)))

    def __repr__(self):
        return '<BoneFrameKey frame %s, loa %s, rot %s>'%(
            str(self.frame_number),
            str(self.location),
            str(self.rotation),
            )


class ShapeKeyFrameKey:
    def __init__(self):
        self.frame_number = 0
        self.weight = 0.0

    def load(self, fin):
        self.frame_number, = struct.unpack('<L', fin.read(4))
        self.weight, = struct.unpack('<f', fin.read(4))

    def __repr__(self):
        return '<ShapeKeyFrameKey frame %s, weight %s>'%(
            str(self.frame_number),
            str(self.weight),
            )


class CameraKeyFrameKey:
    def __init__(self):
        self.frame_number = 0
        self.distance = 0.0
        self.location = []
        self.rotation = []
        self.interp = []
        self.angle = 0.0
        self.persp = True

    def load(self, fin):
        self.frame_number, = struct.unpack('<L', fin.read(4))
        self.distance, = struct.unpack('<f', fin.read(4))
        self.location = list(struct.unpack('<fff', fin.read(4*3)))
        self.rotation = list(struct.unpack('<fff', fin.read(4*3)))
        self.interp = list(struct.unpack('<24b', fin.read(24)))
        self.angle, = struct.unpack('<L', fin.read(4))
        self.persp, = struct.unpack('<b', fin.read(1))
        self.persp = (self.persp == 1)

    def __repr__(self):
        return '<CameraKeyFrameKey frame %s, distance %s, loc %s, rot %s, angle %s, persp %s>'%(
            str(self.frame_number),
            str(self.distance),
            str(self.location),
            str(self.rotation),
            str(self.angle),
            str(self.persp),
            )


class LampKeyFrameKey:
    def __init__(self):
        self.frame_number = 0
        self.color = []
        self.direction = []

    def load(self, fin):
        self.frame_number, = struct.unpack('<L', fin.read(4))
        self.color = list(struct.unpack('<fff', fin.read(4*3)))
        self.direction = list(struct.unpack('<fff', fin.read(4*3)))

    def __repr__(self):
        return '<LampKeyFrameKey frame %s, color %s, direction %s>'%(
            str(self.frame_number),
            str(self.color),
            str(self.direction),
            )


class _AnimationBase(collections.defaultdict):
    def __init__(self):
        collections.defaultdict.__init__(self, list)

    def load(self, fin):
        count, = struct.unpack('<L', fin.read(4))
        for i in range(count):
            name = _toShiftJisString(struct.unpack('<15s', fin.read(15))[0])
            cls = self.frameClass()
            frameKey = cls()
            frameKey.load(fin)
            self[name].append(frameKey)

            
class BoneAnimation(_AnimationBase):
    def __init__(self):
        _AnimationBase.__init__(self)

    @staticmethod
    def frameClass():
        return BoneFrameKey
        

class ShapeKeyAnimation(_AnimationBase):
    def __init__(self):
        _AnimationBase.__init__(self)

    @staticmethod
    def frameClass():
        return ShapeKeyFrameKey


class CameraAnimation(list):
    def __init__(self):
        list.__init__(self)
        self = []

    @staticmethod
    def frameClass():
        return CameraKeyFrameKey

    def load(self, fin):
        count, = struct.unpack('<L', fin.read(4))
        for i in range(count):
            cls = self.frameClass()
            frameKey = cls()
            frameKey.load(fin)
            self.append(frameKey)


class LampAnimation(list):
    def __init__(self):
        list.__init__(self)
        self = []

    @staticmethod
    def frameClass():
        return LampKeyFrameKey

    def load(self, fin):
        count, = struct.unpack('<L', fin.read(4))
        for i in range(count):
            cls = self.frameClass()
            frameKey = cls()
            frameKey.load(fin)
            self.append(frameKey)


class File:
    def __init__(self):
        self.filepath = None
        self.header = None
        self.boneAnimation = None
        self.shapeKeyAnimation = None
        self.cameraAnimation = None
        self.lampAnimation = None

    def load(self, **args):
        path = args['filepath']

        with open(path, 'rb') as fin:
            self.filepath = path
            self.header = Header()
            self.boneAnimation = BoneAnimation()
            self.shapeKeyAnimation = ShapeKeyAnimation()
            self.cameraAnimation = CameraAnimation()
            self.lampAnimation = LampAnimation()

            self.header.load(fin)
            self.boneAnimation.load(fin)
            self.shapeKeyAnimation.load(fin)
            try:
                self.cameraAnimation.load(fin)
                self.lampAnimation.load(fin)
            except struct.error:
                pass # no valid camera/lamp data

########NEW FILE########
