__FILENAME__ = actions

class Action(object):
    def __init__(self, code, length):
        self._code = code
        self._length = length
    
    @property
    def code(self):
        return self._code
    
    @property   
    def length(self):
        return self._length;
    
    @property
    def version(self):
        return 3
        
    def parse(self, data):
        # Do nothing. Many Actions don't have a payload. 
        # For the ones that have one we override this method.
        pass
    
    def tostring(self, indent=0):
        return "[Action] Code: 0x%x, Length: %d" % (self._code, self._length)

class ActionUnknown(Action):
    ''' Dummy class to read unknown actions '''
    def __init__(self, code, length):
        super(ActionUnknown, self).__init__(code, length)
    
    def parse(self, data):
        if self._length > 0:
            #print "skipping %d bytes..." % self._length
            data.skip_bytes(self._length)
    
    def tostring(self, indent=0):
        return "[ActionUnknown] Code: 0x%x, Length: %d" % (self._code, self._length)
        
class Action4(Action):
    ''' Base class for SWF 4 actions '''
    def __init__(self, code, length):
        super(Action4, self).__init__(code, length)
    
    @property
    def version(self):
        return 4

class Action5(Action):
    ''' Base class for SWF 5 actions '''
    def __init__(self, code, length):
        super(Action5, self).__init__(code, length)

    @property
    def version(self):
        return 5
        
class Action6(Action):
    ''' Base class for SWF 6 actions '''
    def __init__(self, code, length):
        super(Action6, self).__init__(code, length)

    @property
    def version(self):
        return 6
        
class Action7(Action):
    ''' Base class for SWF 7 actions '''
    def __init__(self, code, length):
        super(Action7, self).__init__(code, length)

    @property
    def version(self):
        return 7
                
# ========================================================= 
# SWF 3 actions
# =========================================================
class ActionGetURL(Action):
    CODE = 0x83
    def __init__(self, code, length):
        self.urlString = None
        self.targetString = None
        super(ActionGetURL, self).__init__(code, length)
        
    def parse(self, data):
        self.urlString = data.readString()
        self.targetString = data.readString()
        
class ActionGotoFrame(Action):
    CODE = 0x81
    def __init__(self, code, length):
        self.frame = 0
        super(ActionGotoFrame, self).__init__(code, length)

    def parse(self, data): 
        self.frame = data.readUI16()
        
class ActionGotoLabel(Action):
    CODE = 0x8c
    def __init__(self, code, length):
        self.label = None
        super(ActionGotoLabel, self).__init__(code, length)

    def parse(self, data): 
        self.label = data.readString()
        
class ActionNextFrame(Action):
    CODE = 0x04
    def __init__(self, code, length):
        super(ActionNextFrame, self).__init__(code, length)

class ActionPlay(Action):
    CODE = 0x06
    def __init__(self, code, length):
        super(ActionPlay, self).__init__(code, length)
    
    def tostring(self, indent=0):
        return "[ActionPlay] Code: 0x%x, Length: %d" % (self._code, self._length)
            
class ActionPreviousFrame(Action):
    CODE = 0x05
    def __init__(self, code, length):
        super(ActionPreviousFrame, self).__init__(code, length)
                
class ActionSetTarget(Action):
    CODE = 0x8b
    def __init__(self, code, length):
        self.targetName = None
        super(ActionSetTarget, self).__init__(code, length)

    def parse(self, data):
        self.targetName = data.readString()      
        
class ActionStop(Action):
    CODE = 0x07
    def __init__(self, code, length):
        super(ActionStop, self).__init__(code, length)
    
    def tostring(self, indent=0):
        return "[ActionStop] Code: 0x%x, Length: %d" % (self._code, self._length)
             
class ActionStopSounds(Action):
    CODE = 0x09
    def __init__(self, code, length):
        super(ActionStopSounds, self).__init__(code, length)   
        
class ActionToggleQuality(Action):
    CODE = 0x08
    def __init__(self, code, length):
        super(ActionToggleQuality, self).__init__(code, length)
        
class ActionWaitForFrame(Action):
    CODE = 0x8a
    def __init__(self, code, length):
        self.frame = 0
        self.skipCount = 0
        super(ActionWaitForFrame, self).__init__(code, length)

    def parse(self, data):
        self.frame = data.readUI16()
        self.skipCount = data.readUI8()
                              
# ========================================================= 
# SWF 4 actions
# =========================================================
class ActionAdd(Action4):
    CODE = 0x0a
    def __init__(self, code, length):
        super(ActionAdd, self).__init__(code, length)

class ActionAnd(Action4):
    CODE = 0x10
    def __init__(self, code, length):
        super(ActionAnd, self).__init__(code, length)
                       
# urgh! some 100 to go...


class SWFActionFactory(object):
    @classmethod
    def create(cls, code, length):
        if code == ActionPlay.CODE: return ActionPlay(code, length)
        if code == ActionStop.CODE: return ActionStop(code, length)
        else: return ActionUnknown(code, length)
        
########NEW FILE########
__FILENAME__ = consts

class BitmapFormat(object):
    BIT_8 = 3
    BIT_15 = 4
    BIT_24 = 5

    @classmethod
    def tostring(cls, type):
        if type == BitmapFormat.BIT_8: return "BIT_8"
        elif type == BitmapFormat.BIT_15: return "BIT_15"
        elif type == BitmapFormat.BIT_24: return "BIT_24"
        else: return "unknown"

class BitmapType(object):
    JPEG = 1  
    GIF89A = 2
    PNG = 3
    
    @classmethod
    def tostring(cls, type):
        if type == BitmapType.JPEG: return "JPEG"
        elif type == BitmapType.GIF89A: return "GIF89A"
        elif type == BitmapType.PNG: return "PNG"
        else: return "unknown"

class GradientSpreadMode(object):
    PAD = 0 
    REFLECT = 1
    REPEAT = 2

    @classmethod
    def tostring(cls, type):
        if type == GradientSpreadMode.PAD: return "pad"
        elif type == GradientSpreadMode.REFLECT: return "reflect"
        elif type == GradientSpreadMode.REPEAT: return "repeat"
        else: return "unknown"

class GradientType(object):
    LINEAR = 1
    RADIAL = 2

    @classmethod
    def tostring(cls, type):
        if type == GradientType.LINEAR: return "LINEAR"
        elif type == GradientType.RADIAL: return "RADIAL"
        else: return "unknown"
                
class LineScaleMode(object):
    NONE = 0
    HORIZONTAL = 1 
    NORMAL = 2
    VERTICAL = 3
    @classmethod
    def tostring(cls, type):
        if type == LineScaleMode.HORIZONTAL: return "horizontal"
        elif type == LineScaleMode.NORMAL: return "normal"
        elif type == LineScaleMode.VERTICAL: return "vertical"
        elif type == LineScaleMode.NONE: return "none"
        else: return "unknown"
                        
class SpreadMethod(object):
    PAD = 0 
    REFLECT = 1
    REPEAT = 2

    @classmethod
    def tostring(cls, type):
        if type == SpreadMethod.PAD: return "pad"
        elif type == SpreadMethod.REFLECT: return "reflect"
        elif type == SpreadMethod.REPEAT: return "repeat"
        else: return "unknown"
                
class InterpolationMethod(object):
    RGB = 0
    LINEAR_RGB = 1
    @classmethod
    def tostring(cls, type):
        if type == InterpolationMethod.LINEAR_RGB: return "LINEAR_RGB"
        elif type == InterpolationMethod.RGB: return "RGB"
        else: return "unknown"
                        
class LineJointStyle(object):
    ROUND = 0
    BEVEL = 1
    MITER = 2
    
    @classmethod
    def tostring(cls, type):
        if type == LineJointStyle.ROUND: return "ROUND"
        elif type == LineJointStyle.BEVEL: return "BEVEL"
        elif type == LineJointStyle.MITER: return "MITER"
        else: return "unknown"
        
class LineCapsStyle(object):
    ROUND = 0
    NO = 1
    SQUARE = 2
    
    @classmethod    
    def tostring(cls, type):
        if type == LineCapsStyle.ROUND: return "ROUND"
        elif type == LineCapsStyle.NO: return "NO"
        elif type == LineCapsStyle.SQUARE: return "SQUARE"
        else: return "unknown"
        
    
########NEW FILE########
__FILENAME__ = data
from consts import *
from utils import *

class SWFRawTag(object):
    def __init__(self, s=None):
        if not s is None:
            self.parse(s)

    def parse(self, s):
        pos = s.tell()
        self.header = s.readtag_header()
        self.pos_content = s.tell()
        s.f.seek(pos)
        #self.bytes = s.f.read(self.header.tag_length())
        #s.f.seek(self.pos_content)

class SWFStraightEdge(object):
    def __init__(self, start, to, line_style_idx, fill_style_idx):
        self.start = start
        self.to = to
        self.line_style_idx = line_style_idx
        self.fill_style_idx = fill_style_idx
    
    def reverse_with_new_fillstyle(self, new_fill_idx):
        return SWFStraightEdge(self.to, self.start, self.line_style_idx, new_fill_idx)
        
class SWFCurvedEdge(SWFStraightEdge):
    def __init__(self, start, control, to, line_style_idx, fill_style_idx):
        super(SWFCurvedEdge, self).__init__(start, to, line_style_idx, fill_style_idx)
        self.control = control
        
    def reverse_with_new_fillstyle(self, new_fill_idx):
        return SWFCurvedEdge(self.to, self.control, self.start, self.line_style_idx, new_fill_idx)
     
class SWFShape(object):
    def __init__(self, data=None, level=1, unit_divisor=20.0):
        self._records = []
        self._fillStyles = []
        self._lineStyles = []
        self._postLineStyles = {}
        self._edgeMapsCreated = False
        self.unit_divisor = unit_divisor
        self.fill_edge_maps = []
        self.line_edge_maps = []
        self.current_fill_edge_map = {}
        self.current_line_edge_map = {}
        self.num_groups = 0
        self.coord_map = {}
        if not data is None:
            self.parse(data, level)
            
    def parse(self, data, level=1):
        data.reset_bits_pending()
        fillbits = data.readUB(4)
        linebits = data.readUB(4)
        self.read_shape_records(data, fillbits, linebits, level)
    
    def export(self, handler=None):
        self._create_edge_maps()
        if handler is None:
            handler = SVGShapeExporter()
        handler.begin_shape()
        for i in range(0, self.num_groups):
            self._export_fill_path(handler, i)
            self._export_line_path(handler, i)
        handler.end_shape()
        
    @property
    def records(self):
        return self._records
        
    def read_shape_records(self, data, fill_bits, line_bits, level=1):
        shape_record = None
        record_id = 0
        while type(shape_record) != SWFShapeRecordEnd:
            # The SWF10 spec says that shape records are byte aligned.
            # In reality they seem not to be?
            # bitsPending = 0;
            edge_record = (data.readUB(1) == 1)
            if edge_record:
                straight_flag = (data.readUB(1) == 1)
                num_bits = data.readUB(4) + 2
                if straight_flag:
                    shape_record = data.readSTRAIGHTEDGERECORD(num_bits)
                else:
                    shape_record = data.readCURVEDEDGERECORD(num_bits)
            else:
                states= data.readUB(5)
                if states == 0:
                    shape_record = SWFShapeRecordEnd()
                else:
                    style_change_record = data.readSTYLECHANGERECORD(states, fill_bits, line_bits, level)
                    if style_change_record.state_new_styles:
                        fill_bits = style_change_record.num_fillbits
                        line_bits = style_change_record.num_linebits
                    shape_record = style_change_record
            shape_record.record_id = record_id
            self._records.append(shape_record)
            record_id += 1
            #print shape_record.tostring()
        
    def _create_edge_maps(self):
        if self._edgeMapsCreated:
            return
        xPos = 0
        yPos = 0
        sub_path = []
        fs_offset = 0
        ls_offset = 0
        curr_fs_idx0 = 0
        curr_fs_idx1 = 0
        curr_ls_idx = 0
        
        self.fill_edge_maps = []
        self.line_edge_maps = []
        self.current_fill_edge_map = {}
        self.current_line_edge_map = {}
        self.num_groups = 0
        
        for i in range(0, len(self._records)):
            rec = self._records[i]
            if rec.type == SWFShapeRecord.TYPE_STYLECHANGE:
                if rec.state_line_style or rec.state_fill_style0 or rec.state_fill_style1:
                    if len(sub_path):
                        self._process_sub_path(sub_path, curr_ls_idx, curr_fs_idx0, curr_fs_idx1, rec.record_id)
                    sub_path = []

                if rec.state_new_styles:
                    fs_offset = len(self._fillStyles)
                    ls_offset = len(self._lineStyles)
                    self._append_to(self._fillStyles, rec.fill_styles)
                    self._append_to(self._lineStyles, rec.line_styles)
                
                if rec.state_line_style and rec.state_fill_style0 and rec.state_fill_style1 and \
                    rec.line_style == 0 and rec.fill_style0 == 0 and rec.fill_style1 == 0:
                    # new group (probably)
                    self._clean_edge_map(self.current_fill_edge_map)
                    self._clean_edge_map(self.current_line_edge_map)
                    self.fill_edge_maps.append(self.current_fill_edge_map)
                    self.line_edge_maps.append(self.current_line_edge_map)
                    self.current_fill_edge_map = {}
                    self.current_line_edge_map = {}
                    self.num_groups += 1
                    curr_fs_idx0 = 0
                    curr_fs_idx1 = 0
                    curr_ls_idx = 0
                else:
                    if rec.state_line_style:
                        curr_ls_idx = rec.line_style
                        if curr_ls_idx > 0:
                            curr_ls_idx += ls_offset
                    if rec.state_fill_style0:
                        curr_fs_idx0 = rec.fill_style0
                        if curr_fs_idx0 > 0:
                            curr_fs_idx0 += fs_offset
                    if rec.state_fill_style1:
                        curr_fs_idx1 = rec.fill_style1
                        if curr_fs_idx1 > 0:
                            curr_fs_idx1 += fs_offset
  
                if rec.state_moveto:
                    xPos = rec.move_deltaX
                    yPos = rec.move_deltaY
            elif rec.type == SWFShapeRecord.TYPE_STRAIGHTEDGE:
                start = [NumberUtils.round_pixels_400(xPos), NumberUtils.round_pixels_400(yPos)]
                if rec.general_line_flag:
                    xPos += rec.deltaX
                    yPos += rec.deltaY
                else:
                    if rec.vert_line_flag:
                        yPos += rec.deltaY
                    else:
                        xPos += rec.deltaX
                to = [NumberUtils.round_pixels_400(xPos), NumberUtils.round_pixels_400(yPos)]
                sub_path.append(SWFStraightEdge(start, to, curr_ls_idx, curr_fs_idx1))
            elif rec.type == SWFShapeRecord.TYPE_CURVEDEDGE:
                start = [NumberUtils.round_pixels_400(xPos), NumberUtils.round_pixels_400(yPos)]
                xPosControl = xPos + rec.control_deltaX
                yPosControl = yPos + rec.control_deltaY
                xPos = xPosControl + rec.anchor_deltaX
                yPos = yPosControl + rec.anchor_deltaY
                control = [xPosControl, yPosControl]
                to = [NumberUtils.round_pixels_400(xPos), NumberUtils.round_pixels_400(yPos)]
                sub_path.append(SWFCurvedEdge(start, control, to, curr_ls_idx, curr_fs_idx1))
            elif rec.type == SWFShapeRecord.TYPE_END:
                # We're done. Process the last subpath, if any
                if len(sub_path) > 0:
                    self._process_sub_path(sub_path, curr_ls_idx, curr_fs_idx0, curr_fs_idx1, rec.record_id)
                    self._clean_edge_map(self.current_fill_edge_map)
                    self._clean_edge_map(self.current_line_edge_map)
                    self.fill_edge_maps.append(self.current_fill_edge_map)
                    self.line_edge_maps.append(self.current_line_edge_map)
                    self.current_fill_edge_map = {}
                    self.current_line_edge_map = {}
                    self.num_groups += 1
                curr_fs_idx0 = 0
                curr_fs_idx1 = 0
                curr_ls_idx = 0
    
        self._edgeMapsCreated = True
    
    def _process_sub_path(self, sub_path, linestyle_idx, fillstyle_idx0, fillstyle_idx1, record_id=-1):
        path = None
        if fillstyle_idx0 != 0:
            if not fillstyle_idx0 in self.current_fill_edge_map:
                path = self.current_fill_edge_map[fillstyle_idx0] = []
            else:
                path = self.current_fill_edge_map[fillstyle_idx0]
            for j in range(len(sub_path) - 1, -1, -1):
                path.append(sub_path[j].reverse_with_new_fillstyle(fillstyle_idx0))
                                      
        if fillstyle_idx1 != 0:
            if not fillstyle_idx1 in self.current_fill_edge_map:
                path = self.current_fill_edge_map[fillstyle_idx1] = []
            else:
                path = self.current_fill_edge_map[fillstyle_idx1]
            self._append_to(path, sub_path)
                    
        if linestyle_idx != 0:
            if not linestyle_idx in self.current_line_edge_map:
                path = self.current_line_edge_map[linestyle_idx] = []
            else:
                path = self.current_line_edge_map[linestyle_idx]
            self._append_to(path, sub_path)
             
    def _clean_edge_map(self, edge_map):
        for style_idx in edge_map:
            sub_path = edge_map[style_idx] if style_idx in edge_map else None
            if sub_path is not None and len(sub_path) > 0:
                tmp_path = []
                prev_edge = None
                self._create_coord_map(sub_path)
                while len(sub_path) > 0:
                    idx = 0
                    while idx < len(sub_path):
                        if prev_edge is None or self._equal_point(prev_edge.to, sub_path[idx].start):
                            edge = sub_path[idx]
                            del sub_path[idx]
                            tmp_path.append(edge)
                            self._remove_edge_from_coord_map(edge)
                            prev_edge = edge
                        else:
                            edge = self._find_next_edge_in_coord_map(prev_edge)
                            if not edge is None:
                                idx = sub_path.index(edge)
                            else:
                                idx = 0
                                prev_edge = None
                edge_map[style_idx] = tmp_path
  
    def _equal_point(self, a, b, tol=0.001):
        return (a[0] > b[0]-tol and a[0] < b[0]+tol and a[1] > b[1]-tol and a[1] < b[1]+tol)
    
    def _find_next_edge_in_coord_map(self, edge):
        key = "%0.4f_%0.4f" % (edge.to[0], edge.to[1])
        if key in self.coord_map and len(self.coord_map[key]) > 0:
            return self.coord_map[key][0]
        else:
            return None
             
    def _create_coord_map(self, path):
        self.coord_map = {}
        for i in range(0, len(path)):
            start = path[i].start
            key = "%0.4f_%0.4f" % (start[0], start[1])
            coord_map_array = self.coord_map[key] if key in self.coord_map else None
            if coord_map_array is None:
                self.coord_map[key] = [path[i]]
            else:
                self.coord_map[key].append(path[i])
                
    def _remove_edge_from_coord_map(self, edge):
        key = "%0.4f_%0.4f" % (edge.start[0], edge.start[1])
        if key in self.coord_map:
            coord_map_array = self.coord_map[key]
            if len(coord_map_array) == 1:
                del self.coord_map[key]
            else:
                try:
                    idx = coord_map_array.index(edge)
                    del coord_map_array[idx]
                except:
                    pass
                    
    def _create_path_from_edge_map(self, edge_map):
        new_path = []
        style_ids = []
        for style_id in edge_map:
            style_ids.append(int(style_id))
        style_ids = sorted(style_ids)
        for i in range(0, len(style_ids)):
            self._append_to(new_path, edge_map[style_ids[i]])
        return new_path
        
    def _export_fill_path(self, handler, group_index):
        path = self._create_path_from_edge_map(self.fill_edge_maps[group_index])

        pos = [100000000, 100000000]
        u = 1.0 / self.unit_divisor
        fill_style_idx = 10000000

        if len(path) < 1:
            return
        handler.begin_fills()
        for i in range(0, len(path)):
            e = path[i]
            if fill_style_idx != e.fill_style_idx:
                fill_style_idx = e.fill_style_idx
                pos = [100000000, 100000000]
                try:
                    fill_style = self._fillStyles[fill_style_idx - 1] if fill_style_idx > 0 else None
                    if fill_style.type == 0x0:
                        # solid fill
                        handler.begin_fill(
                            ColorUtils.rgb(fill_style.rgb), 
                            ColorUtils.alpha(fill_style.rgb))
                    elif fill_style.type in [0x10, 0x12, 0x13]:
                        # gradient fill
                        colors = []
                        ratios = []
                        alphas = []
                        for j in range(0, len(fill_style.gradient.records)):
                            gr = fill_style.gradient.records[j]
                            colors.append(ColorUtils.rgb(gr.color))
                            ratios.append(gr.ratio)
                            alphas.append(ColorUtils.alpha(gr.color))
                        handler.begin_gradient_fill(
                            GradientType.LINEAR if fill_style.type == 0x10 else GradientType.RADIAL,
                            colors, alphas, ratios,
                            fill_style.gradient_matrix,
                            fill_style.gradient.spreadmethod,
                            fill_style.gradient.interpolation_mode,
                            fill_style.gradient.focal_point
                            )
                    elif fill_style.type in [0x40, 0x41, 0x42, 0x43]:
                        # bitmap fill
                        handler.begin_bitmap_fill(
                            fill_style.bitmap_id,
                            fill_style.bitmap_matrix,
                            (fill_style.type == 0x40 or fill_style.type == 0x42),
                            (fill_style.type == 0x40 or fill_style.type == 0x41)
                            )
                        pass
                except:
                    # Font shapes define no fillstyles per se, but do reference fillstyle index 1,
                    # which represents the font color. We just report solid black in this case.
                    handler.begin_fill(0)
                        
            if not self._equal_point(pos, e.start):
                handler.move_to(e.start[0] * u, e.start[1] * u)

            if type(e) is SWFCurvedEdge:
                handler.curve_to(e.control[0] * u, e.control[1] * u, e.to[0] * u, e.to[1] * u)
            else:
                handler.line_to(e.to[0] * u, e.to[1] * u)
                
            pos = e.to
  
        handler.end_fill()
        handler.end_fills()
            
    def _export_line_path(self, handler, group_index):
        
        path = self._create_path_from_edge_map(self.line_edge_maps[group_index])
        pos = [100000000, 100000000]
        u = 1.0 / self.unit_divisor
        line_style_idx = 10000000
        line_style = None
        if len(path) < 1:
            return

        handler.begin_lines()
        for i in range(0, len(path)):
            e = path[i]

            if line_style_idx != e.line_style_idx:
                line_style_idx = e.line_style_idx
                pos = [100000000, 100000000]
                try:
                    line_style = self._lineStyles[line_style_idx - 1]
                except:
                    line_style = None
                if line_style is not None:
                    scale_mode = LineScaleMode.NORMAL
                    if line_style.no_hscale_flag and line_style.no_vscale_flag:
                        scale_mode = LineScaleMode.NONE
                    elif line_style.no_hscale_flag:
                        scale_mode = LineScaleMode.HORIZONTAL
                    elif line_style.no_hscale_flag:
                        scale_mode = LineScaleMode.VERTICAL
                    
                    if not line_style.has_fill_flag:
                        handler.line_style(
                            line_style.width / 20.0, 
                            ColorUtils.rgb(line_style.color), 
                            ColorUtils.alpha(line_style.color), 
                            line_style.pixelhinting_flag,
                            scale_mode,
                            line_style.start_caps_style,
                            line_style.end_caps_style,
                            line_style.joint_style,
                            line_style.miter_limit_factor)
                    else:
                        fill_style = line_style.fill_type
                        
                        if fill_style.type in [0x10, 0x12, 0x13]:
                            # gradient fill
                            colors = []
                            ratios = []
                            alphas = []
                            for j in range(0, len(fill_style.gradient.records)):
                                gr = fill_style.gradient.records[j]
                                colors.append(ColorUtils.rgb(gr.color))
                                ratios.append(gr.ratio)
                                alphas.append(ColorUtils.alpha(gr.color))

                            handler.line_gradient_style(
                                line_style.width / 20.0, 
                                line_style.pixelhinting_flag,
                                scale_mode,
                                line_style.start_caps_style,
                                line_style.end_caps_style,
                                line_style.joint_style,
                                line_style.miter_limit_factor,
                                GradientType.LINEAR if fill_style.type == 0x10 else GradientType.RADIAL,
                                colors, alphas, ratios,
                                fill_style.gradient_matrix,
                                fill_style.gradient.spreadmethod,
                                fill_style.gradient.interpolation_mode,
                                fill_style.gradient.focal_point
                                )
                        elif fill_style.type in [0x40, 0x41, 0x42]:
                            handler.line_bitmap_style(
                                line_style.width / 20.0, 
                                line_style.pixelhinting_flag,
                                scale_mode,
                                line_style.start_caps_style,
                                line_style.end_caps_style,
                                line_style.joint_style,
                                line_style.miter_limit_factor,
                                fill_style.bitmap_id, fill_style.bitmap_matrix,
                                (fill_style.type == 0x40 or fill_style.type == 0x42),
                                (fill_style.type == 0x40 or fill_style.type == 0x41)
                                )
                else:
                    # we should never get here
                    handler.line_style(0)
            if not self._equal_point(pos, e.start):
                handler.move_to(e.start[0] * u, e.start[1] * u)
            if type(e) is SWFCurvedEdge:
                handler.curve_to(e.control[0] * u, e.control[1] * u, e.to[0] * u, e.to[1] * u)
            else:
                handler.line_to(e.to[0] * u, e.to[1] * u)
            pos = e.to
        handler.end_lines()
                    
    def _append_to(self, v1, v2):
        for i in range(0, len(v2)):
            v1.append(v2[i])
    
    def __str__(self):
        return "[SWFShape]"
            
class SWFShapeWithStyle(SWFShape):
    def __init__(self, data, level, unit_divisor):
        self._initialFillStyles = []
        self._initialLineStyles = []
        super(SWFShapeWithStyle, self).__init__(data, level, unit_divisor)
    
    def export(self, handler=None):
        self._fillStyles.extend(self._initialFillStyles)
        self._lineStyles.extend(self._initialLineStyles)
        super(SWFShapeWithStyle, self).export(handler)
        
    def parse(self, data, level=1):
        
        data.reset_bits_pending()
        num_fillstyles = self.readstyle_array_length(data, level)
        for i in range(0, num_fillstyles):
            self._initialFillStyles.append(data.readFILLSTYLE(level))
        num_linestyles = self.readstyle_array_length(data, level)
        for i in range(0, num_linestyles):
            if level <= 3:
                self._initialLineStyles.append(data.readLINESTYLE(level))
            else:
                self._initialLineStyles.append(data.readLINESTYLE2(level))
        num_fillbits = data.readUB(4)
        num_linebits = data.readUB(4)
        data.reset_bits_pending()
        self.read_shape_records(data, num_fillbits, num_linebits, level)

    def readstyle_array_length(self, data, level=1):
        length = data.readUI8()
        if level >= 2 and length == 0xff:
            length = data.readUI16()
        return length
    
    def __str__(self):
        s = "    FillStyles:\n" if len(self._fillStyles) > 0 else ""
        for i in range(0, len(self._initialFillStyles)):
            s += "        %d:%s\n" % (i+1, self._initialFillStyles[i].__str__())
        if len(self._initialLineStyles) > 0:
            s += "    LineStyles:\n"
            for i in range(0, len(self._initialLineStyles)):
                s += "        %d:%s\n" % (i+1, self._initialLineStyles[i].__str__())
        for record in self._records:
            s += record.__str__() + '\n'
        return s.rstrip() + super(SWFShapeWithStyle, self).__str__()
              
class SWFShapeRecord(object):
    
    TYPE_UNKNOWN = 0
    TYPE_END = 1
    TYPE_STYLECHANGE = 2
    TYPE_STRAIGHTEDGE = 3
    TYPE_CURVEDEDGE = 4
    
    record_id = -1
    
    def __init__(self, data=None, level=1):
        if not data is None:
            self.parse(data, level)
            
    @property
    def is_edge_record(self):
        return (self.type == SWFShapeRecord.TYPE_STRAIGHTEDGE or 
            self.type == SWFShapeRecord.TYPE_CURVEDEDGE)
            
    def parse(self, data, level=1):
        pass
    
    @property
    def type(self):
        return SWFShapeRecord.TYPE_UNKNOWN
        
    def __str__(self):
        return "    [SWFShapeRecord]"
      			
class SWFShapeRecordStraightEdge(SWFShapeRecord):
    def __init__(self, data, num_bits=0, level=1):
        self.num_bits = num_bits
        super(SWFShapeRecordStraightEdge, self).__init__(data, level)

    def parse(self, data, level=1):
        self.general_line_flag = (data.readUB(1) == 1)
        self.vert_line_flag = False if self.general_line_flag else (data.readUB(1) == 1)
        self.deltaX = data.readSB(self.num_bits) \
            if self.general_line_flag or not self.vert_line_flag \
            else 0.0
        self.deltaY = data.readSB(self.num_bits) \
            if self.general_line_flag or self.vert_line_flag \
            else 0.0
            
    @property
    def type(self):
        return SWFShapeRecord.TYPE_STRAIGHTEDGE

    def __str__(self):
        s = "    [SWFShapeRecordStraightEdge]"
        if self.general_line_flag:
            s += " General: %d %d" % (self.deltaX, self.deltaY)
        else:
            if self.vert_line_flag:
                s += " Vertical: %d" % self.deltaY
            else:
                s += " Horizontal: %d" % self.deltaX
        return s
        
class SWFShapeRecordCurvedEdge(SWFShapeRecord):
    def __init__(self, data, num_bits=0, level=1):
        self.num_bits = num_bits
        super(SWFShapeRecordCurvedEdge, self).__init__(data, level)

    def parse(self, data, level=1):
        self.control_deltaX = data.readSB(self.num_bits)
        self.control_deltaY = data.readSB(self.num_bits)
        self.anchor_deltaX = data.readSB(self.num_bits)
        self.anchor_deltaY = data.readSB(self.num_bits)
        
    @property
    def type(self):
        return SWFShapeRecord.TYPE_CURVEDEDGE

    def __str__(self):
        return "    [SWFShapeRecordCurvedEdge]" + \
            " ControlDelta: %d, %d" % (self.control_deltaX, self.control_deltaY) + \
            " AnchorDelta: %d, %d" % (self.anchor_deltaX, self.anchor_deltaY)
     
class SWFShapeRecordStyleChange(SWFShapeRecord):
    def __init__(self, data, states=0, fill_bits=0, line_bits=0, level=1):
        self.fill_styles = []
        self.line_styles = []
        self.state_new_styles = ((states & 0x10) != 0)
        self.state_line_style = ((states & 0x08) != 0)
        self.state_fill_style1 = ((states & 0x4) != 0)
        self.state_fill_style0 = ((states & 0x2) != 0)
        self.state_moveto = ((states & 0x1) != 0)
        self.num_fillbits = fill_bits
        self.num_linebits = line_bits
        self.move_deltaX = 0.0
        self.move_deltaY = 0.0
        self.fill_style0 = 0
        self.fill_style1 = 0
        self.line_style = 0
        super(SWFShapeRecordStyleChange, self).__init__(data, level)

    def parse(self, data, level=1):
        
        if self.state_moveto:
            movebits = data.readUB(5)
            self.move_deltaX = data.readSB(movebits)
            self.move_deltaY = data.readSB(movebits)
        self.fill_style0 = data.readUB(self.num_fillbits) if self.state_fill_style0 else 0
        self.fill_style1 = data.readUB(self.num_fillbits) if self.state_fill_style1 else 0
        self.line_style = data.readUB(self.num_linebits) if self.state_line_style else 0
        if self.state_new_styles:
            data.reset_bits_pending();
            num_fillstyles = self.readstyle_array_length(data, level)
            for i in range(0, num_fillstyles):
                self.fill_styles.append(data.readFILLSTYLE(level))
            num_linestyles = self.readstyle_array_length(data, level)
            for i in range(0, num_linestyles):
                if level <= 3:
                    self.line_styles.append(data.readLINESTYLE(level))
                else:
                    self.line_styles.append(data.readLINESTYLE2(level))
            self.num_fillbits = data.readUB(4)
            self.num_linebits = data.readUB(4)
            
    @property
    def type(self):
        return SWFShapeRecord.TYPE_STYLECHANGE
    
    def readstyle_array_length(self, data, level=1):
        length = data.readUI8()
        if level >= 2 and length == 0xff:
            length = data.readUI16()
        return length
            
    def __str__(self):
        return "    [SWFShapeRecordStyleChange]" + \
            " moveTo: %d %d" % (self.move_deltaX, self.move_deltaY) + \
            " fs0: %d" % self.fill_style0 + \
            " fs1: %d" % self.fill_style1 + \
            " linestyle: %d" % self.line_style + \
            " flags: %d %d %d" % (self.state_fill_style0, self.state_fill_style1, self.state_line_style)
                                   
class SWFShapeRecordEnd(SWFShapeRecord):
    def __init__(self):
        super(SWFShapeRecordEnd, self).__init__(None)
        
    def parse(self, data, level=1):
        pass

    @property
    def type(self):
        return SWFShapeRecord.TYPE_END

    def __str__(self):
        return "    [SWFShapeRecordEnd]"
                
class SWFMatrix(object):
    def __init__(self, data):
        self.scaleX = 1.0
        self.scaleY = 1.0
        self.rotateSkew0 = 0.0
        self.rotateSkew1 = 0.0
        self.translateX = 0.0
        self.translateY = 0.0
        if not data is None:
            self.parse(data)
            
    def parse(self, data):
        data.reset_bits_pending();
        self.scaleX = 1.0
        self.scaleY = 1.0
        if data.readUB(1) == 1:
            scaleBits = data.readUB(5)
            self.scaleX = data.readFB(scaleBits)
            self.scaleY = data.readFB(scaleBits)
        self.rotateSkew0 = 0.0
        self.rotateSkew1 = 0.0
        if data.readUB(1) == 1:
            rotateBits = data.readUB(5)
            self.rotateSkew0 = data.readFB(rotateBits)
            self.rotateSkew1 = data.readFB(rotateBits)
        translateBits = data.readUB(5)
        self.translateX = data.readSB(translateBits)
        self.translateY = data.readSB(translateBits)
    
    def to_array(self):
        return [
            self.scaleX, self.rotateSkew0, 
            self.rotateSkew1, self.scaleY, 
            self.translateX, self.translateY
        ]
    
    def __str__(self):
        def fmt(s):
            return "%0.2f" % s
            
        return "[%s]" % ",".join(map(fmt, self.to_array()))
        
class SWFGradientRecord(object):
    def __init__(self, data=None, level=1):
        self._records = []
        if not data is None:
            self.parse(data, level)

    def parse(self, data, level=1):  
        self.ratio = data.readUI8()
        self.color = data.readRGB() if level <= 2 else data.readRGBA()
    
    def __str__(self):
        return "[SWFGradientRecord] Color: %s, Ratio: %d" % (ColorUtils.to_rgb_string(self.color), self.ratio)
        
class SWFGradient(object):
    def __init__(self, data=None, level=1):
        self._records = []
        self.focal_point = 0.0
        if not data is None:
            self.parse(data, level)
    
    @property
    def records(self):
        return self._records
        
    def parse(self, data, level=1):  
        data.reset_bits_pending();
        self.spreadmethod = data.readUB(2)
        self.interpolation_mode = data.readUB(2)
        num_gradients = data.readUB(4)
        for i in range(0, num_gradients):
            self._records.append(data.readGRADIENTRECORD(level))
    
    def __str__(self):
        s = "[SWFGadient]"
        for record in self._records:
            s += "\n  " + record.__str__()
        return s
        
class SWFFocalGradient(SWFGradient):
    def __init__(self, data=None, level=1):
        super(SWFFocalGradient, self).__init__(data, level)

    def parse(self, data, level=1):  
        super(SWFFocalGradient, self).parse(data, level)
        self.focal_point = data.readFIXED8()
    
    def __str__(self):
        return "[SWFFocalGradient] Color: %s, Ratio: %d, Focal: %0.2f" % \
            (ColorUtils.to_rgb_string(self.color), self.ratio, self.focal_point)
                                      
class SWFFillStyle(object):
    def __init__(self, data=None, level=1):
        if not data is None:
            self.parse(data, level)
            
    def parse(self, data, level=1):
        self.type = data.readUI8()
        if self.type == 0x0:
            self.rgb = data.readRGB() if level <= 2 else data.readRGBA()
        elif self.type in [0x10, 0x12, 0x13]:
            self.gradient_matrix = data.readMATRIX()
            self.gradient = data.readFOCALGRADIENT(level) if self.type == 0x13 else data.readGRADIENT(level)
        elif self.type in [0x40, 0x41, 0x42, 0x43]:
            self.bitmap_id = data.readUI16()
            self.bitmap_matrix = data.readMATRIX()
        else:
            raise Exception("Unknown fill style type: 0x%x" % self.type, level)
    
    def __str__(self):
        s = "[SWFFillStyle] "
        if self.type == 0x0:
            s += "Color: %s" % ColorUtils.to_rgb_string(self.rgb)
        elif self.type in [0x10, 0x12, 0x13]:
            s += "Gradient: %s" % self.gradient_matrix
        elif self.type in [0x40, 0x41, 0x42, 0x43]:
            s += "BitmapID: %d" % (self.bitmap_id)
        return s
        
class SWFLineStyle(object):
    def __init__(self, data=None, level=1):
        # forward declarations for SWFLineStyle2
        self.start_caps_style = LineCapsStyle.ROUND
        self.end_caps_style = LineCapsStyle.ROUND
        self.joint_style = LineJointStyle.ROUND
        self.has_fill_flag = False
        self.no_hscale_flag = False
        self.no_vscale_flag = False
        self.pixelhinting_flag = False
        self.no_close = False
        self.miter_limit_factor = 3.0
        self.fill_type = None
        self.width = 1
        self.color = 0
        if not data is None:
            self.parse(data, level)

    def parse(self, data, level=1):
        self.width = data.readUI16()
        self.color = data.readRGB() if level <= 2 else data.readRGBA()
    
    def __str__(self):
        s = "[SWFLineStyle] "
        s += "Color: %s, Width: %d" % (ColorUtils.to_rgb_string(self.color), self.width)
        return s
                          
class SWFLineStyle2(SWFLineStyle):
    def __init__(self, data=None, level=1):
        super(SWFLineStyle2, self).__init__(data, level)

    def parse(self, data, level=1):
        self.width = data.readUI16()
        self.start_caps_style = data.readUB(2)
        self.joint_style = data.readUB(2)
        self.has_fill_flag = (data.readUB(1) == 1)
        self.no_hscale_flag = (data.readUB(1) == 1)
        self.no_vscale_flag = (data.readUB(1) == 1)
        self.pixelhinting_flag = (data.readUB(1) == 1)
        data.readUB(5)
        self.no_close = (data.readUB(1) == 1)
        self.end_caps_style = data.readUB(2)
        if self.joint_style == LineJointStyle.MITER:
            self.miter_limit_factor = data.readFIXED8()
        if self.has_fill_flag:
            self.fill_type = data.readFILLSTYLE(level)
        else:
            self.color = data.readRGBA()

    def __str__(self):
        s = "[SWFLineStyle2] "
        s += "Width: %d, " % self.width
        s += "StartCapsStyle: %d, " % self.start_caps_style
        s += "JointStyle: %d, " % self.joint_style
        s += "HasFillFlag: %d, " % self.has_fill_flag
        s += "NoHscaleFlag: %d, " % self.no_hscale_flag
        s += "NoVscaleFlag: %d, " % self.no_vscale_flag
        s += "PixelhintingFlag: %d, " % self.pixelhinting_flag
        s += "NoClose: %d, " % self.no_close
        
        if self.joint_style:
            s += "MiterLimitFactor: %d" % self.miter_limit_factor
        if self.has_fill_flag:
            s += "FillType: %s, " % self.fill_type
        else:
            s += "Color: %s" % ColorUtils.to_rgb_string(self.color)
        
        return s

class SWFMorphGradientRecord(object):
    def __init__(self, data):
        if not data is None:
            self.parse(data)
            
    def parse(self, data):
        self.startRatio = data.readUI8()
        self.startColor = data.readRGBA()
        self.endRatio = data.readUI8()
        self.endColor = data.readRGBA()

class SWFMorphGradient(object):
    def __init__(self, data, level=1):
        self.records = []
        if not data is None:
            self.parse(data, level)
            
    def parse(self, data, level=1):
        self.records = []
        numGradients = data.readUI8()
        for i in range(0, numGradients):
            self.records.append(data.readMORPHGRADIENTRECORD())
            
class SWFMorphFillStyle(object):
    def __init__(self, data, level=1):
        if not data is None:
            self.parse(data, level)
            
    def parse(self, data, level=1):
        type = data.readUI8()
        if type == 0x0:
            self.startColor = data.readRGBA()
            self.endColor = data.readRGBA()
        elif type in [0x10, 0x12]:
            self.startGradientMatrix = data.readMATRIX()
            self.endGradientMatrix = data.readMATRIX()
            self.gradient = data.readMORPHGRADIENT(level)
        elif type in [0x40, 0x41, 0x42, 0x43]:
            self.bitmapId = data.readUI16()
            self.startBitmapMatrix = data.readMATRIX()
            self.endBitmapMatrix = data.readMATRIX()

class SWFMorphLineStyle(object):
    def __init__(self, data, level=1):
        # Forward declaration of SWFMorphLineStyle2 properties
        self.startCapsStyle = LineCapsStyle.ROUND
        self.endCapsStyle = LineCapsStyle.ROUND
        self.jointStyle = LineJointStyle.ROUND
        self.hasFillFlag = False
        self.noHScaleFlag = False
        self.noVScaleFlag = False
        self.pixelHintingFlag = False
        self.noClose = False
        self.miterLimitFactor = 3
        self.fillType = None
        if not data is None:
            self.parse(data, level)

    def parse(self, data, level=1):
        self.startWidth = data.readUI16()
        self.endWidth = data.readUI16()
        self.startColor = data.readRGBA()
        self.endColor = data.readRGBA()

class SWFMorphLineStyle2(SWFMorphLineStyle):
    def __init__(self, data, level=1):
        super(SWFMorphLineStyle2, self).__init__(data, level)

    def parse(self, data, level=1):
        self.startWidth = data.readUI16()
        self.endWidth = data.readUI16()
        self.startCapsStyle = data.readUB(2)
        self.jointStyle = data.readUB(2)
        self.hasFillFlag = (data.readUB(1) == 1)
        self.noHScaleFlag = (data.readUB(1) == 1)
        self.noVScaleFlag = (data.readUB(1) == 1)
        self.pixelHintingFlag = (data.readUB(1) == 1)
        reserved = data.readUB(5);
        self.noClose = (data.readUB(1) == 1)
        self.endCapsStyle = data.readUB(2)
        if self.jointStyle == LineJointStyle.MITER:
            self.miterLimitFactor = data.readFIXED8()
        if self.hasFillFlag:
            self.fillType = data.readMORPHFILLSTYLE(level)
        else:
            self.startColor = data.readRGBA()
            self.endColor = data.readRGBA()

class SWFRecordHeader(object):
    def __init__(self, type, content_length, header_length):
        self.type = type
        self.content_length = content_length
        self.header_length = header_length

    @property
    def tag_length(self):
        return self.header_length + self.content_length

class SWFRectangle(object):
    def __init__(self):
        self.xmin = self.xmax = self.ymin = self.ymax = 0

    def parse(self, s):
        s.reset_bits_pending()
        bits = s.readUB(5)
        self.xmin = s.readSB(bits)
        self.xmax = s.readSB(bits)
        self.ymin = s.readSB(bits)
        self.ymax = s.readSB(bits)

    def __str__(self):
        return "[xmin: %d xmax: %d ymin: %d ymax: %d]" % (self.xmin/20, self.xmax/20, self.ymin/20, self.ymax/20)
        
class SWFColorTransform(object):
    def __init__(self, data=None):
        if not data is None:
            self.parse(data)
    
    def parse(self, data):
        data.reset_bits_pending()
        self.hasAddTerms = (data.readUB(1) == 1)
        self.hasMultTerms = (data.readUB(1) == 1)
        bits = data.readUB(4)
        self.rMult = 1
        self.gMult = 1
        self.bMult = 1
        if self.hasMultTerms:
            self.rMult = data.readSB(bits)
            self.gMult = data.readSB(bits)
            self.bMult = data.readSB(bits)
        self.rAdd = 0
        self.gAdd = 0
        self.bAdd = 0
        if self.hasAddTerms:
            self.rAdd = data.readSB(bits)
            self.gAdd = data.readSB(bits)
            self.bAdd = data.readSB(bits)
    
    @property
    def matrix(self):
        return [
            self.rMult / 256.0, 0.0, 0.0, 0.0, self.rAdd / 256.0,
            0.0, self.gMult / 256.0, 0.0, 0.0, self.gAdd / 256.0,
            0.0, 0.0, self.bMult / 256.0, 0.0, self.bAdd / 256.0,
            0.0, 0.0, 0.0, 1.0, 1.0
        ]
        
    def __str__(self):
        return "[%d %d %d %d %d %d]" % \
            (self.rMult, self.gMult, self.bMult, self.rAdd, self.gAdd, self.bAdd)
        
class SWFColorTransformWithAlpha(SWFColorTransform):
    def __init__(self, data=None):
        super(SWFColorTransformWithAlpha, self).__init__(data)

    def parse(self, data):
        data.reset_bits_pending()
        self.hasAddTerms = (data.readUB(1) == 1)
        self.hasMultTerms = (data.readUB(1) == 1)
        bits = data.readUB(4)
        self.rMult = 1
        self.gMult = 1
        self.bMult = 1
        self.aMult = 1
        if self.hasMultTerms:
            self.rMult = data.readSB(bits)
            self.gMult = data.readSB(bits)
            self.bMult = data.readSB(bits)
            self.aMult = data.readSB(bits)     
        self.rAdd = 0
        self.gAdd = 0
        self.bAdd = 0
        self.aAdd = 0
        if self.hasAddTerms:
            self.rAdd = data.readSB(bits)
            self.gAdd = data.readSB(bits)
            self.bAdd = data.readSB(bits)
            self.aAdd = data.readSB(bits)
    
    @property
    def matrix(self):
        '''
        Gets the matrix as a 20 item list
        '''
        return [
            self.rMult / 256.0, 0.0, 0.0, 0.0, self.rAdd / 256.0,
            0.0, self.gMult / 256.0, 0.0, 0.0, self.gAdd / 256.0,
            0.0, 0.0, self.bMult / 256.0, 0.0, self.bAdd / 256.0,
            0.0, 0.0, 0.0, self.aMult / 256.0, self.aAdd / 256.0
        ]
                
    def __str__(self):
        return "[%d %d %d %d %d %d %d %d]" % \
            (self.rMult, self.gMult, self.bMult, self.aMult, self.rAdd, self.gAdd, self.bAdd, self.aAdd)
 
class SWFFrameLabel(object):
    def __init__(self, frameNumber, name):
        self.frameNumber = frameNumber
        self.name = name

    def __str__(self):
        return "Frame: %d, Name: %s" % (self.frameNumber, self.name)
                               
class SWFScene(object):
    def __init__(self, offset, name):
        self.offset = offset
        self.name = name
        
    def __str__(self):
        return "Scene: %d, Name: '%s'" % (self.offset, self.name)
        
class SWFSymbol(object):
    def __init__(self, data=None):
        if not data is None:
            self.parse(data)
        
    def parse(self, data):
        self.tagId = data.readUI16()
        self.name = data.readString()

    def __str__(self):
        return "ID %d, Name: %s" % (self.tagId, self.name)
        
class SWFGlyphEntry(object):
    def __init__(self, data=None, glyphBits=0, advanceBits=0):
        if not data is None:
            self.parse(data, glyphBits, advanceBits)
        
    def parse(self, data, glyphBits, advanceBits):
        # GLYPHENTRYs are not byte aligned
        self.index = data.readUB(glyphBits)
        self.advance = data.readSB(advanceBits)
    
    def __str__(self):
        return "Index: %d, Advance: %d" % (self.index, self.advance)
        
class SWFKerningRecord(object):
    def __init__(self, data=None, wideCodes=False):
        if not data is None:
            self.parse(data, wideCodes)
        
    def parse(self, data, wideCodes):
        self.code1 = data.readUI16() if wideCodes else data.readUI8()
        self.code2 = data.readUI16() if wideCodes else data.readUI8()
        self.adjustment = data.readSI16()
    
    def __str__(self):
        return "Code1: %d, Code2: %d, Adjustement: %d" % (self.code1, self.code2, self.adjustment)
        
class SWFTextRecord(object):
    def __init__(self, data=None, glyphBits=0, advanceBits=0, previousRecord=None, level=1):
        self.hasFont = False
        self.hasColor = False
        self.hasYOffset = False
        self.hasXOffset = False
        self.fontId = -1
        self.textColor = 0
        self.xOffset = 0
        self.yOffset = 0
        self.textHeight = 12
        self.glyphEntries = []
        if not data is None:
            self.parse(data, glyphBits, advanceBits, previousRecord, level)

    def parse(self, data, glyphBits, advanceBits, previousRecord=None, level=1):
        self.glyphEntries = []
        styles = data.readUI8()
        self.type = styles >> 7
        self.hasFont = ((styles & 0x08) != 0)
        self.hasColor = ((styles & 0x04) != 0)
        self.hasYOffset = ((styles & 0x02) != 0)
        self.hasXOffset = ((styles & 0x01) != 0)
        
        if self.hasFont:
            self.fontId = data.readUI16()
        elif not previousRecord is None:
            self.fontId = previousRecord.fontId
        
        if self.hasColor:
            self.textColor = data.readRGB() if level < 2 else data.readRGBA()
        elif not previousRecord is None:
            self.textColor = previousRecord.textColor
        
        if self.hasXOffset:
            self.xOffset = data.readSI16();
        elif not previousRecord is None:
            self.xOffset = previousRecord.xOffset
        
        if self.hasYOffset:
            self.yOffset = data.readSI16();
        elif not previousRecord is None:
            self.yOffset = previousRecord.yOffset
        
        if self.hasFont:
            self.textHeight = data.readUI16()
        elif not previousRecord is None:
            self.textHeight = previousRecord.textHeight
        
        glyphCount = data.readUI8()
        for i in range(0, glyphCount):
            self.glyphEntries.append(data.readGLYPHENTRY(glyphBits, advanceBits))
    
    def __str__(self):
        return "[SWFTextRecord]"
        
class SWFClipActions(object):
    def __init__(self, data=None, version=0):
        self.eventFlags = None
        self.records = []
        if not data is None:
            self.parse(data, version)

    def parse(self, data, version):
        data.readUI16() # reserved, always 0
        self.eventFlags = data.readCLIPEVENTFLAGS(version)
        self.records = []
        record = data.readCLIPACTIONRECORD(version)
        while not record is None:
            self.records.append(record)
            record = data.readCLIPACTIONRECORD(version)

    def __str__(self):
        return "[SWFClipActions]"
                         
class SWFClipActionRecord(object):
    def __init__(self, data=None, version=0):
        self.eventFlags = None
        self.keyCode = 0
        self.actions = []
        if not data is None:
            self.parse(data, version)

    def parse(self, data, version):
        self.actions = []
        self.eventFlags = data.readCLIPEVENTFLAGS(version)
        data.readUI32() # actionRecordSize, not needed here
        if self.eventFlags.keyPressEvent:
            self.keyCode = data.readUI8()
        action = data.readACTIONRECORD()
        while not action is None:
            self.actions.append(action)
            action = data.readACTIONRECORD()

    def __str__(self):
        return "[SWFClipActionRecord]"
                           
class SWFClipEventFlags(object):
    keyUpEvent = False
    keyDownEvent = False
    mouseUpEvent = False
    mouseDownEvent = False
    mouseMoveEvent = False
    unloadEvent = False
    enterFrameEvent = False
    loadEvent = False
    dragOverEvent = False # SWF6
    rollOutEvent = False # SWF6
    rollOverEvent = False # SWF6
    releaseOutsideEvent = False # SWF6
    releaseEvent = False # SWF6
    pressEvent = False # SWF6
    initializeEvent = False # SWF6
    dataEvent = False
    constructEvent = False # SWF7
    keyPressEvent = False # SWF6
    dragOutEvent = False # SWF6
    
    def __init__(self, data=None, version=0):
        if not data is None:
            self.parse(data, version)
            
    def parse(self, data, version):
        flags1 = data.readUI8();
        self.keyUpEvent = ((flags1 & 0x80) != 0)
        self.keyDownEvent = ((flags1 & 0x40) != 0)
        self.mouseUpEvent = ((flags1 & 0x20) != 0)
        self.mouseDownEvent = ((flags1 & 0x10) != 0)
        self.mouseMoveEvent = ((flags1 & 0x08) != 0)
        self.unloadEvent = ((flags1 & 0x04) != 0)
        self.enterFrameEvent = ((flags1 & 0x02) != 0)
        self.loadEvent = ((flags1 & 0x01) != 0)
        flags2 = data.readUI8()
        self.dragOverEvent = ((flags2 & 0x80) != 0)
        self.rollOutEvent = ((flags2 & 0x40) != 0)
        self.rollOverEvent = ((flags2 & 0x20) != 0)
        self.releaseOutsideEvent = ((flags2 & 0x10) != 0)
        self.releaseEvent = ((flags2 & 0x08) != 0)
        self.pressEvent = ((flags2 & 0x04) != 0)
        self.initializeEvent = ((flags2 & 0x02) != 0)
        self.dataEvent = ((flags2 & 0x01) != 0)
        if version >= 6:
            flags3 = data.readUI8()
            self.constructEvent = ((flags3 & 0x04) != 0)
            self.keyPressEvent = ((flags3 & 0x02) != 0)
            self.dragOutEvent = ((flags3 & 0x01) != 0)
            data.readUI8() # reserved, always 0
    
    def __str__(self):
        return "[SWFClipEventFlags]"
                       
class SWFZoneData(object):
    def __init__(self, data=None):
        if not data is None:
            self.parse(data)

    def parse(self, data):
        self.alignmentCoordinate = data.readFLOAT16()
        self.zoneRange = data.readFLOAT16()

    def __str__(self):
        return "[SWFZoneData]"
                                 
class SWFZoneRecord(object):
    def __init__(self, data=None):
        if not data is None:
            self.parse(data)

    def parse(self, data):
        self.zoneData = []
        numZoneData = data.readUI8()
        for i in range(0, numZoneData):
            self.zoneData.append(data.readZONEDATA())
        mask = data.readUI8()
        self.maskX = ((mask & 0x01) != 0)
        self.maskY = ((mask & 0x02) != 0)

    def __str__(self):
        return "[SWFZoneRecord]"
                    

########NEW FILE########
__FILENAME__ = export
"""
This module defines exporters for the SWF fileformat.
"""
from consts import *
from geom import *
from utils import *
from data import *
from tag import *
from filters import *
from lxml import objectify
from lxml import etree
import base64
from PIL import Image
from StringIO import StringIO
import math
import re
import copy

SVG_VERSION = "1.1"
SVG_NS      = "http://www.w3.org/2000/svg"
XLINK_NS    = "http://www.w3.org/1999/xlink"
XLINK_HREF  = "{%s}href" % XLINK_NS
NS = {"svg" : SVG_NS, "xlink" : XLINK_NS}

MINIMUM_STROKE_WIDTH = 1.0

CAPS_STYLE = {
    0 : 'round',
    1 : 'butt',
    2 : 'square'
}

JOIN_STYLE = {
    0 : 'round',
    1 : 'bevel',
    2 : 'miter'
}

class DefaultShapeExporter(object):
    """
    The default (abstract) Shape exporter class.
    All shape exporters should extend this class.


    """
    def __init__(self, swf=None, debug=False, force_stroke=False):
        self.swf = None
        self.debug = debug
        self.force_stroke = force_stroke

    def begin_bitmap_fill(self, bitmap_id, matrix=None, repeat=False, smooth=False):
        pass
    def begin_fill(self, color, alpha=1.0):
        pass
    def begin_gradient_fill(self, type, colors, alphas, ratios,
                            matrix=None,
                            spreadMethod=SpreadMethod.PAD,
                            interpolationMethod=InterpolationMethod.RGB,
                            focalPointRatio=0.0):
        pass
    def line_style(self,
                    thickness=float('nan'), color=0, alpha=1.0,
                    pixelHinting=False,
                    scaleMode=LineScaleMode.NORMAL,
                    startCaps=None, endCaps=None,
                    joints=None, miterLimit=3.0):
        pass
    def line_gradient_style(self,
                    thickness=float('nan'), color=0, alpha=1.0,
                    pixelHinting=False,
                    scaleMode=LineScaleMode.NORMAL,
                    startCaps=None, endCaps=None,
                    joints=None, miterLimit=3.0,
                    type = 1, colors = [], alphas = [], ratios = [],
                    matrix=None,
                    spreadMethod=SpreadMethod.PAD,
                    interpolationMethod=InterpolationMethod.RGB,
                    focalPointRatio=0.0):
        pass
    def line_bitmap_style(self,
                    thickness=float('nan'),
                    pixelHinting=False,
                    scaleMode=LineScaleMode.NORMAL,
                    startCaps=None, endCaps=None,
                    joints=None, miterLimit = 3.0,
                    bitmap_id=None, matrix=None, repeat=False, smooth=False):
        pass
    def end_fill(self):
        pass

    def begin_fills(self):
        pass
    def end_fills(self):
        pass
    def begin_lines(self):
        pass
    def end_lines(self):
        pass

    def begin_shape(self):
        pass
    def end_shape(self):
        pass

    def move_to(self, x, y):
        #print "move_to", x, y
        pass
    def line_to(self, x, y):
        #print "line_to", x, y
        pass
    def curve_to(self, cx, cy, ax, ay):
        #print "curve_to", cx, cy, ax, ay
        pass

class DefaultSVGShapeExporter(DefaultShapeExporter):
    def __init__(self, defs=None):
        self.defs = defs
        self.current_draw_command = ""
        self.path_data = ""
        self._e = objectify.ElementMaker(annotate=False,
                        namespace=SVG_NS, nsmap={None : SVG_NS, "xlink" : XLINK_NS})
        super(DefaultSVGShapeExporter, self).__init__()

    def move_to(self, x, y):
        self.current_draw_command = ""
        self.path_data += "M" + \
            str(NumberUtils.round_pixels_20(x)) + " " + \
            str(NumberUtils.round_pixels_20(y)) + " "

    def line_to(self, x, y):
        if self.current_draw_command != "L":
            self.current_draw_command = "L"
            self.path_data += "L"
        self.path_data += "" + \
            str(NumberUtils.round_pixels_20(x)) + " " + \
            str(NumberUtils.round_pixels_20(y)) + " "

    def curve_to(self, cx, cy, ax, ay):
        if self.current_draw_command != "Q":
            self.current_draw_command = "Q"
            self.path_data += "Q"
        self.path_data += "" + \
            str(NumberUtils.round_pixels_20(cx)) + " " + \
            str(NumberUtils.round_pixels_20(cy)) + " " + \
            str(NumberUtils.round_pixels_20(ax)) + " " + \
            str(NumberUtils.round_pixels_20(ay)) + " "

    def begin_bitmap_fill(self, bitmap_id, matrix=None, repeat=False, smooth=False):
        self.finalize_path()

    def begin_fill(self, color, alpha=1.0):
        self.finalize_path()

    def end_fill(self):
        pass
        #self.finalize_path()

    def begin_fills(self):
        pass
    def end_fills(self):
        self.finalize_path()

    def begin_gradient_fill(self, type, colors, alphas, ratios,
                            matrix=None,
                            spreadMethod=SpreadMethod.PAD,
                            interpolationMethod=InterpolationMethod.RGB,
                            focalPointRatio=0.0):
        self.finalize_path()

    def line_style(self,
                    thickness=float('nan'), color=0, alpha=1.0,
                    pixelHinting=False,
                    scaleMode=LineScaleMode.NORMAL,
                    startCaps=None, endCaps=None,
                    joints=None, miterLimit=3.0):
        self.finalize_path()

    def end_lines(self):
        self.finalize_path()

    def end_shape(self):
        self.finalize_path()

    def finalize_path(self):
        self.current_draw_command = ""
        self.path_data = ""

class SVGShapeExporter(DefaultSVGShapeExporter):
    def __init__(self):
        self.path = None
        self.num_patterns = 0
        self.num_gradients = 0
        self._gradients = {}
        self._gradient_ids = {}
        self.paths = {}
        self.fills_ended = False
        super(SVGShapeExporter, self).__init__()

    def begin_shape(self):
        self.g = self._e.g()

    def begin_fill(self, color, alpha=1.0):
        self.finalize_path()
        self.path.set("fill", ColorUtils.to_rgb_string(color))
        if alpha < 1.0:
            self.path.set("fill-opacity", str(alpha))
        elif self.force_stroke:
            self.path.set("stroke", ColorUtils.to_rgb_string(color))
            self.path.set("stroke-width", "1")
        else:
            self.path.set("stroke", "none")

    def begin_gradient_fill(self, type, colors, alphas, ratios,
                            matrix=None,
                            spreadMethod=SpreadMethod.PAD,
                            interpolationMethod=InterpolationMethod.RGB,
                            focalPointRatio=0.0):
        self.finalize_path()
        gradient_id = self.export_gradient(type, colors, alphas, ratios, matrix, spreadMethod, interpolationMethod, focalPointRatio)
        self.path.set("stroke", "none")
        self.path.set("fill", "url(#%s)" % gradient_id)

    def export_gradient(self, type, colors, alphas, ratios,
                        matrix=None,
                        spreadMethod=SpreadMethod.PAD,
                        interpolationMethod=InterpolationMethod.RGB,
                        focalPointRatio=0.0):
        self.num_gradients += 1
        gradient_id = "gradient%d" % self.num_gradients
        gradient = self._e.linearGradient() if type == GradientType.LINEAR \
            else self._e.radialGradient()
        gradient.set("gradientUnits", "userSpaceOnUse")

        if type == GradientType.LINEAR:
            gradient.set("x1", "-819.2")
            gradient.set("x2", "819.2")
        else:
            gradient.set("r", "819.2")
            gradient.set("cx", "0")
            gradient.set("cy", "0")
            if focalPointRatio < 0.0 or focalPointRatio > 0.0:
                gradient.set("fx", str(819.2 * focalPointRatio))
                gradient.set("fy", "0")

        if spreadMethod == SpreadMethod.PAD:
            gradient.set("spreadMethod", "pad")
        elif spreadMethod == SpreadMethod.REFLECT:
            gradient.set("spreadMethod", "reflect")
        elif spreadMethod == SpreadMethod.REPEAT:
            gradient.set("spreadMethod", "repeat")

        if interpolationMethod == InterpolationMethod.LINEAR_RGB:
            gradient.set("color-interpolation", "linearRGB")

        if matrix is not None:
            sm = _swf_matrix_to_svg_matrix(matrix)
            gradient.set("gradientTransform", sm);

        for i in range(0, len(colors)):
            entry = self._e.stop()
            offset = ratios[i] / 255.0
            entry.set("offset", str(offset))
            if colors[i] != 0.0:
                entry.set("stop-color", ColorUtils.to_rgb_string(colors[i]))
            if alphas[i] != 1.0:
                entry.set("stop-opacity", str(alphas[i]))
            gradient.append(entry)

        # prevent same gradient in <defs />
        key = etree.tostring(gradient)
        if key in self._gradients:
            gradient_id = self._gradient_ids[key]
        else:
            self._gradients[key] = copy.copy(gradient)
            self._gradient_ids[key] = gradient_id
            gradient.set("id", gradient_id)
            self.defs.append(gradient)

        return gradient_id

    def export_pattern(self, bitmap_id, matrix, repeat=False, smooth=False):
        self.num_patterns += 1
        bitmap_id = "c%d" % bitmap_id
        e = self.defs.xpath("./svg:image[@id='%s']" % bitmap_id, namespaces=NS)
        if len(e) < 1:
            raise Exception("SVGShapeExporter::begin_bitmap_fill Could not find bitmap!")
        image = e[0]
        pattern_id = "pat%d" % (self.num_patterns)
        pattern = self._e.pattern()
        pattern.set("id", pattern_id)
        pattern.set("width", image.get("width"))
        pattern.set("height", image.get("height"))
        pattern.set("patternUnits", "userSpaceOnUse")
        #pattern.set("patternContentUnits", "objectBoundingBox")
        if matrix is not None:
            pattern.set("patternTransform", _swf_matrix_to_svg_matrix(matrix, True, True, True))
            pass
        use = self._e.use()
        use.set(XLINK_HREF, "#%s" % bitmap_id)
        pattern.append(use)
        self.defs.append(pattern)

        return pattern_id

    def begin_bitmap_fill(self, bitmap_id, matrix=None, repeat=False, smooth=False):
        self.finalize_path()
        pattern_id = self.export_pattern(bitmap_id, matrix, repeat, smooth)
        self.path.set("stroke", "none")
        self.path.set("fill", "url(#%s)" % pattern_id)

    def line_style(self,
                    thickness=float('nan'), color=0, alpha=1.0,
                    pixelHinting=False,
                    scaleMode=LineScaleMode.NORMAL,
                    startCaps=None, endCaps=None,
                    joints=None, miterLimit=3.0):
        self.finalize_path()
        self.path.set("fill", "none")
        self.path.set("stroke", ColorUtils.to_rgb_string(color))
        thickness = 1 if math.isnan(thickness) else thickness
        thickness = MINIMUM_STROKE_WIDTH if thickness < MINIMUM_STROKE_WIDTH else thickness
        self.path.set("stroke-width", str(thickness))
        if alpha < 1.0:
            self.path.set("stroke-opacity", str(alpha))

    def line_gradient_style(self,
                    thickness=float('nan'),
                    pixelHinting = False,
                    scaleMode=LineScaleMode.NORMAL,
                    startCaps=0, endCaps=0,
                    joints=0, miterLimit=3.0,
                    type = 1,
                    colors = [],
                    alphas = [],
                    ratios = [],
                    matrix=None,
                    spreadMethod=SpreadMethod.PAD,
                    interpolationMethod=InterpolationMethod.RGB,
                    focalPointRatio=0.0):
        self.finalize_path()
        gradient_id = self.export_gradient(type, colors, alphas, ratios, matrix, spreadMethod, interpolationMethod, focalPointRatio)
        self.path.set("fill", "none")
        self.path.set("stroke-linejoin", JOIN_STYLE[joints])
        self.path.set("stroke-linecap", CAPS_STYLE[startCaps])
        self.path.set("stroke", "url(#%s)" % gradient_id)
        thickness = 1 if math.isnan(thickness) else thickness
        thickness = MINIMUM_STROKE_WIDTH if thickness < MINIMUM_STROKE_WIDTH else thickness
        self.path.set("stroke-width", str(thickness))

    def line_bitmap_style(self,
                    thickness=float('nan'),
                    pixelHinting=False,
                    scaleMode=LineScaleMode.NORMAL,
                    startCaps=None, endCaps=None,
                    joints=None, miterLimit = 3.0,
                    bitmap_id=None, matrix=None, repeat=False, smooth=False):
        self.finalize_path()
        pattern_id = self.export_pattern(bitmap_id, matrix, repeat, smooth)
        self.path.set("fill", "none")
        self.path.set("stroke", "url(#%s)" % pattern_id)
        self.path.set("stroke-linejoin", JOIN_STYLE[joints])
        self.path.set("stroke-linecap", CAPS_STYLE[startCaps])
        thickness = 1 if math.isnan(thickness) else thickness
        thickness = MINIMUM_STROKE_WIDTH if thickness < MINIMUM_STROKE_WIDTH else thickness
        self.path.set("stroke-width", str(thickness))

    def begin_fills(self):
        self.fills_ended = False
    def end_fills(self):
        self.finalize_path()
        self.fills_ended = True

    def finalize_path(self):
        if self.path is not None and len(self.path_data) > 0:
            self.path_data = self.path_data.rstrip()
            self.path.set("d", self.path_data)
            self.g.append(self.path)
        self.path = self._e.path()
        super(SVGShapeExporter, self).finalize_path()


class BaseExporter(object):
    def __init__(self, swf=None, shape_exporter=None, force_stroke=False):
        self.shape_exporter = SVGShapeExporter() if shape_exporter is None else shape_exporter
        self.clip_depth = 0
        self.mask_id = None
        self.jpegTables = None
        self.force_stroke = force_stroke
        if swf is not None:
            self.export(swf)

    def export(self, swf, force_stroke=False):
        self.force_stroke = force_stroke
        self.export_define_shapes(swf.tags)
        self.export_display_list(self.get_display_tags(swf.tags))

    def export_define_bits(self, tag):
        png_buffer = StringIO()
        image = None
        if isinstance(tag, TagDefineBitsJPEG3):

            tag.bitmapData.seek(0)
            tag.bitmapAlphaData.seek(0, 2)
            num_alpha = tag.bitmapAlphaData.tell()
            tag.bitmapAlphaData.seek(0)
            image = Image.open(tag.bitmapData)
            if num_alpha > 0:
                image_width = image.size[0]
                image_height = image.size[1]
                image_data = image.getdata()
                image_data_len = len(image_data)
                if num_alpha == image_data_len:
                    buff = ""
                    for i in range(0, num_alpha):
                        alpha = ord(tag.bitmapAlphaData.read(1))
                        rgb = list(image_data[i])
                        buff += struct.pack("BBBB", rgb[0], rgb[1], rgb[2], alpha)
                    image = Image.fromstring("RGBA", (image_width, image_height), buff)
        elif isinstance(tag, TagDefineBitsJPEG2):
            tag.bitmapData.seek(0)
            image = Image.open(tag.bitmapData)
        else:
            tag.bitmapData.seek(0)
            if self.jpegTables is not None:
                buff = StringIO()
                self.jpegTables.seek(0)
                buff.write(self.jpegTables.read())
                buff.write(tag.bitmapData.read())
                buff.seek(0)
                image = Image.open(buff)
            else:
                image = Image.open(tag.bitmapData)

        self.export_image(tag, image)

    def export_define_bits_lossless(self, tag):
        image = Image.open(tag.bitmapData)
        self.export_image(tag, image)

    def export_define_sprite(self, tag, parent=None):
        display_tags = self.get_display_tags(tag.tags)
        self.export_display_list(display_tags, parent)

    def export_define_shape(self, tag):
        self.shape_exporter.debug = isinstance(tag, TagDefineShape4)
        tag.shapes.export(self.shape_exporter)

    def export_define_shapes(self, tags):
        for tag in tags:
            if isinstance(tag, SWFTimelineContainer):
                self.export_define_sprite(tag)
                self.export_define_shapes(tag.tags)
            elif isinstance(tag, TagDefineShape):
                self.export_define_shape(tag)
            elif isinstance(tag, TagJPEGTables):
                if tag.length > 0:
                    self.jpegTables = tag.jpegTables
            elif isinstance(tag, TagDefineBits):
                self.export_define_bits(tag)
            elif isinstance(tag, TagDefineBitsLossless):
                self.export_define_bits_lossless(tag)

    def export_display_list(self, tags, parent=None):
        self.clip_depth = 0
        for tag in tags:
            self.export_display_list_item(tag, parent)

    def export_display_list_item(self, tag, parent=None):
        pass

    def export_image(self, tag, image=None):
        pass

    def get_display_tags(self, tags, z_sorted=True):
        dp_tuples = []
        for tag in tags:
            if isinstance(tag, TagPlaceObject):
                dp_tuples.append((tag, tag.depth))
            elif isinstance(tag, TagShowFrame):
                break
        if z_sorted:
            dp_tuples = sorted(dp_tuples, key=lambda tag_info: tag_info[1])
        display_tags = []
        for item in dp_tuples:
            display_tags.append(item[0])
        return display_tags

    def serialize(self):
        return None

class SVGExporter(BaseExporter):
    def __init__(self, swf=None, margin=0):
        self._e = objectify.ElementMaker(annotate=False,
                        namespace=SVG_NS, nsmap={None : SVG_NS, "xlink" : XLINK_NS})
        self._margin = margin
        super(SVGExporter, self).__init__(swf)

    def export(self, swf, force_stroke=False):
        """ Exports the specified SWF to SVG.

        @param swf  The SWF.
        @param force_stroke Whether to force strokes on non-stroked fills.
        """
        self.svg = self._e.svg(version=SVG_VERSION)
        self.force_stroke = force_stroke
        self.defs = self._e.defs()
        self.root = self._e.g()
        self.svg.append(self.defs)
        self.svg.append(self.root)
        self.shape_exporter.defs = self.defs
        self._num_filters = 0

        # GO!
        super(SVGExporter, self).export(swf, force_stroke)

        # Setup svg @width, @height and @viewBox
        # and add the optional margin
        self.bounds = SVGBounds(self.svg)
        self.svg.set("width", "%dpx" % round(self.bounds.width))
        self.svg.set("height", "%dpx" % round(self.bounds.height))
        if self._margin > 0:
            self.bounds.grow(self._margin)
        vb = [self.bounds.minx, self.bounds.miny,
              self.bounds.width, self.bounds.height]
        self.svg.set("viewBox", "%s" % " ".join(map(str,vb)))

        # Return the SVG as StringIO
        return self._serialize()

    def _serialize(self):
        return StringIO(etree.tostring(self.svg,
                encoding="UTF-8", xml_declaration=True))

    def export_define_sprite(self, tag, parent=None):
        id = "c%d"%tag.characterId
        g = self._e.g(id=id)
        self.defs.append(g)
        self.clip_depth = 0
        super(SVGExporter, self).export_define_sprite(tag, g)

    def export_define_shape(self, tag):
        self.shape_exporter.force_stroke = self.force_stroke
        super(SVGExporter, self).export_define_shape(tag)
        shape = self.shape_exporter.g
        shape.set("id", "c%d" % tag.characterId)
        self.defs.append(shape)

    def export_display_list_item(self, tag, parent=None):
        g = self._e.g()
        use = self._e.use()
        is_mask = False

        if tag.hasMatrix:
            use.set("transform", _swf_matrix_to_svg_matrix(tag.matrix))
        if tag.hasClipDepth:
            self.mask_id = "mask%d" % tag.characterId
            self.clip_depth = tag.clipDepth
            g = self._e.mask(id=self.mask_id)
            # make sure the mask is completely filled white
            paths = self.defs.xpath("./svg:g[@id='c%d']/svg:path" % tag.characterId, namespaces=NS)
            for path in paths:
                path.set("fill", "#ffffff")
            is_mask = True
        elif tag.depth <= self.clip_depth:
            g.set("mask", "url(#%s)" % self.mask_id)

        filters = []
        filter_cxform = None
        self._num_filters += 1
        filter_id = "filter%d" % self._num_filters
        svg_filter = self._e.filter(id=filter_id)

        if tag.hasColorTransform:
            filter_cxform = self.export_color_transform(tag.colorTransform, svg_filter)
            filters.append(filter_cxform)
        if tag.hasFilterList and len(tag.filters) > 0:
            cxform = "color-xform" if tag.hasColorTransform else None
            f = self.export_filters(tag, svg_filter, cxform)
            if len(f) > 0:
                filters.extend(f)
        if tag.hasColorTransform or (tag.hasFilterList and len(filters) > 0):
            self.defs.append(svg_filter)
            use.set("filter", "url(#%s)" % filter_id)

        use.set(XLINK_HREF, "#c%s" % tag.characterId)
        g.append(use)

        if is_mask:
            self.defs.append(g)
        else:
            if parent is not None:
                parent.append(g)
            else:
                self.root.append(g)
        return use

    def export_color_transform(self, cxform, svg_filter, result='color-xform'):
        fe_cxform = self._e.feColorMatrix()
        fe_cxform.set("in", "SourceGraphic")
        fe_cxform.set("type", "matrix")
        fe_cxform.set("values", " ".join(map(str, cxform.matrix)))
        fe_cxform.set("result", "cxform")

        fe_composite = self._e.feComposite(operator="in")
        fe_composite.set("in2", "SourceGraphic")
        fe_composite.set("result", result)

        svg_filter.append(fe_cxform)
        svg_filter.append(fe_composite)
        return result

    def export_filters(self, tag, svg_filter, cxform=None):
        num_filters = len(tag.filters)
        elements = []
        attr_in = None
        for i in range(0, num_filters):
            swf_filter = tag.filters[i]
            #print swf_filter
            if isinstance(swf_filter, FilterDropShadow):
                elements.append(self.export_filter_dropshadow(swf_filter, svg_filter, cxform))
                #print swf_filter.strength
                pass
            elif isinstance(swf_filter, FilterBlur):
                pass
            elif isinstance(swf_filter, FilterGlow):
                #attr_in = SVGFilterFactory.export_glow_filter(self._e, svg_filter, attr_in=attr_in)
                #elements.append(attr_in)
                pass
            elif isinstance(swf_filter, FilterBevel):
                pass
            elif isinstance(swf_filter, FilterGradientGlow):
                pass
            elif isinstance(swf_filter, FilterConvolution):
                pass
            elif isinstance(swf_filter, FilterColorMatrix):
                attr_in = SVGFilterFactory.export_color_matrix_filter(self._e, svg_filter, swf_filter.colorMatrix, svg_filter, attr_in=attr_in)
                elements.append(attr_in)
                pass
            elif isinstance(swf_filter, FilterGradientBevel):
                pass
            else:
                raise Exception("unknown filter: ", swf_filter)
        return elements

#   <filter id="test-filter" x="-50%" y="-50%" width="200%" height="200%">
#		<feGaussianBlur in="SourceAlpha" stdDeviation="6" result="blur"/>
#		<feOffset dy="0" dx="0"/>
#		<feComposite in2="SourceAlpha" operator="arithmetic"
#			k2="-1" k3="1" result="shadowDiff"/>
#		<feFlood flood-color="black" flood-opacity="1"/>
#		<feComposite in2="shadowDiff" operator="in"/>
#	</filter>;

    def export_filter_dropshadow(self, swf_filter, svg_filter, blend_in=None, result="offsetBlur"):
        gauss = self._e.feGaussianBlur()
        gauss.set("in", "SourceAlpha")
        gauss.set("stdDeviation", "6")
        gauss.set("result", "blur")
        if swf_filter.knockout:
            composite0 = self._e.feComposite(
                in2="SourceAlpha", operator="arithmetic",
                k2="-1", k3="1", result="shadowDiff")
            flood = self._e.feFlood()
            flood.set("flood-color", "black")
            flood.set("flood-opacity", "1")
            composite1 = self._e.feComposite(
                in2="shadowDiff", operator="in", result=result)
            svg_filter.append(gauss)
            svg_filter.append(composite0)
            svg_filter.append(flood)
            svg_filter.append(composite1)
        else:
            SVGFilterFactory.create_drop_shadow_filter(self._e, svg_filter,
                None,
                swf_filter.blurX/20.0,
                swf_filter.blurY/20.0,
                blend_in,
                result)
        #print etree.tostring(svg_filter, pretty_print=True)
        return result

    def export_image(self, tag, image=None):
        if image is not None:
            buff = StringIO()
            image.save(buff, "PNG")
            buff.seek(0)
            data_url = _encode_png(buff.read())
            img = self._e.image()
            img.set("id", "c%s" % tag.characterId)
            img.set("x", "0")
            img.set("y", "0 ")
            img.set("width", "%s" % str(image.size[0]))
            img.set("height", "%s" % str(image.size[1]))
            img.set(XLINK_HREF, "%s" % data_url)
            self.defs.append(img)

class SVGFilterFactory(object):
    # http://commons.oreilly.com/wiki/index.php/SVG_Essentials/Filters
    # http://dev.opera.com/articles/view/svg-evolution-3-applying-polish/

    @classmethod
    def create_drop_shadow_filter(cls, e, filter, attr_in=None, blurX=0, blurY=0, blend_in=None, result=None):
        gaussianBlur = SVGFilterFactory.create_gaussian_blur(e, attr_deviaton="1", result="blur-out")
        offset = SVGFilterFactory.create_offset(e, "blur-out", blurX, blurY, "the-shadow")
        blend = SVGFilterFactory.create_blend(e, blend_in, attr_in2="the-shadow", result=result)
        filter.append(gaussianBlur)
        filter.append(offset)
        filter.append(blend)
        return result

    @classmethod
    def export_color_matrix_filter(cls, e, filter, matrix, svg_filter, attr_in=None, result='color-matrix'):
        attr_in = "SourceGraphic" if attr_in is None else attr_in
        fe_cxform = e.feColorMatrix()
        fe_cxform.set("in", attr_in)
        fe_cxform.set("type", "matrix")
        fe_cxform.set("values", " ".join(map(str, matrix)))
        fe_cxform.set("result", result)
        filter.append(fe_cxform)
        #print etree.tostring(filter, pretty_print=True)
        return result

    @classmethod
    def export_glow_filter(cls, e, filter, attr_in=None, result="glow-out"):
        attr_in = "SourceGraphic" if attr_in is None else attr_in
        gaussianBlur = SVGFilterFactory.create_gaussian_blur(e, attr_in=attr_in, attr_deviaton="1", result=result)
        filter.append(gaussianBlur)
        return result

    @classmethod
    def create_blend(cls, e, attr_in=None, attr_in2="BackgroundImage", mode="normal", result=None):
        blend = e.feBlend()
        attr_in = "SourceGraphic" if attr_in is None else attr_in
        blend.set("in", attr_in)
        blend.set("in2", attr_in2)
        blend.set("mode", mode)
        if result is not None:
            blend.set("result", result)
        return blend

    @classmethod
    def create_gaussian_blur(cls, e, attr_in="SourceAlpha", attr_deviaton="3", result=None):
        gaussianBlur = e.feGaussianBlur()
        gaussianBlur.set("in", attr_in)
        gaussianBlur.set("stdDeviation", attr_deviaton)
        if result is not None:
            gaussianBlur.set("result", result)
        return gaussianBlur

    @classmethod
    def create_offset(cls, e, attr_in=None, dx=0, dy=0, result=None):
        offset = e.feOffset()
        if attr_in is not None:
            offset.set("in", attr_in)
        offset.set("dx", "%d" % round(dx))
        offset.set("dy", "%d" % round(dy))
        if result is not None:
            offset.set("result", result)
        return offset

class SVGBounds(object):
    def __init__(self, svg=None):
        self.minx = 1000000.0
        self.miny = 1000000.0
        self.maxx = -self.minx
        self.maxy = -self.miny
        self._stack = []
        self._matrix = self._calc_combined_matrix()
        if svg is not None:
            self._svg = svg;
            self._parse(svg)

    def add_point(self, x, y):
        self.minx = x if x < self.minx else self.minx
        self.miny = y if y < self.miny else self.miny
        self.maxx = x if x > self.maxx else self.maxx
        self.maxy = y if y > self.maxy else self.maxy

    def set(self, minx, miny, maxx, maxy):
        self.minx = minx
        self.miny = miny
        self.maxx = maxx
        self.maxy = maxy

    def grow(self, margin):
        self.minx -= margin
        self.miny -= margin
        self.maxx += margin
        self.maxy += margin

    @property
    def height(self):
        return self.maxy - self.miny

    def merge(self, other):
        self.minx = other.minx if other.minx < self.minx else self.minx
        self.miny = other.miny if other.miny < self.miny else self.miny
        self.maxx = other.maxx if other.maxx > self.maxx else self.maxx
        self.maxy = other.maxy if other.maxy > self.maxy else self.maxy

    def shrink(self, margin):
        self.minx += margin
        self.miny += margin
        self.maxx -= margin
        self.maxy -= margin

    @property
    def width(self):
        return self.maxx - self.minx

    def _parse(self, element):

        if element.get("transform") and element.get("transform").find("matrix") < 0:
            pass

        if element.get("transform") and element.get("transform").find("matrix") >= 0:
            self._push_transform(element.get("transform"))

        if element.tag == "{%s}path" % SVG_NS:
            self._handle_path_data(str(element.get("d")))
        elif element.tag == "{%s}use" % SVG_NS:
            href = element.get(XLINK_HREF)
            href = href.replace("#", "")
            els = self._svg.xpath("./svg:defs//svg:g[@id='%s']" % href,
                    namespaces=NS)
            if len(els) > 0:
                self._parse(els[0])

        for child in element.getchildren():
            if child.tag == "{%s}defs" % SVG_NS: continue
            self._parse(child)

        if element.get("transform") and element.get("transform").find("matrix") >= 0:
            self._pop_transform()

    def _build_matrix(self, transform):
        if transform.find("matrix") >= 0:
            raw = str(transform).replace("matrix(", "").replace(")", "")
            f = map(float, re.split("\s+|,", raw))
            return Matrix2(f[0], f[1], f[2], f[3], f[4], f[5])

    def _calc_combined_matrix(self):
        m = Matrix2()
        for mat in self._stack:
            m.append_matrix(mat)
        return m

    def _handle_path_data(self, d):
        parts = re.split("[\s]+", d)
        for i in range(0, len(parts), 2):
            try:
                p0 = parts[i]
                p1 = parts[i+1]
                p0 = p0.replace("M", "").replace("L", "").replace("Q", "")
                p1 = p1.replace("M", "").replace("L", "").replace("Q", "")

                v = [float(p0), float(p1)]
                w = self._matrix.multiply_point(v)
                self.minx = w[0] if w[0] < self.minx else self.minx
                self.miny = w[1] if w[1] < self.miny else self.miny
                self.maxx = w[0] if w[0] > self.maxx else self.maxx
                self.maxy = w[1] if w[1] > self.maxy else self.maxy
            except:
                continue

    def _pop_transform(self):
        m = self._stack.pop()
        self._matrix = self._calc_combined_matrix()
        return m

    def _push_transform(self, transform):
        self._stack.append(self._build_matrix(transform))
        self._matrix = self._calc_combined_matrix()

def _encode_jpeg(data):
    return "data:image/jpeg;base64," + base64.encodestring(data)[:-1]

def _encode_png(data):
    return "data:image/png;base64," + base64.encodestring(data)[:-1]

def _swf_matrix_to_matrix(swf_matrix=None, need_scale=False, need_translate=True, need_rotation=False, unit_div=20.0):

    if swf_matrix is None:
        values = [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
    else:
        values = swf_matrix.to_array()
        if need_rotation:
            values[1] /= unit_div
            values[2] /= unit_div
        if need_scale:
            values[0] /= unit_div
            values[3] /= unit_div
        if need_translate:
            values[4] /= unit_div
            values[5] /= unit_div

    return values

def _swf_matrix_to_svg_matrix(swf_matrix=None, need_scale=False, need_translate=True, need_rotation=False, unit_div=20.0):
    values = _swf_matrix_to_matrix(swf_matrix, need_scale, need_translate, need_rotation, unit_div)
    str_values = ",".join(map(str, values))
    return "matrix(%s)" % str_values


########NEW FILE########
__FILENAME__ = filters
from utils import ColorUtils

class Filter(object):
    """
    Base Filter class
    """
    def __init__(self, id):
        self._id = id
    
    @property
    def id(self):
        """ Return filter ID """
        return self._id
        
    def parse(self, data):
        '''
        Parses the filter
        '''
        pass
        
class FilterDropShadow(Filter):
    """
    Drop Shadow Filter
    """
    def __init__(self, id):
        super(FilterDropShadow, self).__init__(id)
    
    def parse(self, data):
        self.dropShadowColor = data.readRGBA()
        self.blurX = data.readFIXED()
        self.blurY = data.readFIXED()
        self.angle = data.readFIXED()
        self.distance = data.readFIXED()
        self.strength = data.readFIXED8()
        flags = data.readUI8()
        self.innerShadow = ((flags & 0x80) != 0)
        self.knockout = ((flags & 0x40) != 0)
        self.compositeSource = ((flags & 0x20) != 0)
        self.passes = flags & 0x1f
    
    def __str__(self):
        s = "[DropShadowFilter] " + \
            "DropShadowColor: %s" % ColorUtils.to_rgb_string(self.dropShadowColor) + ", " + \
            "BlurX: %0.2f" % self.blurX + ", " + \
            "BlurY: %0.2f" % self.blurY + ", " + \
            "Angle: %0.2f" % self.angle + ", " + \
            "Distance: %0.2f" % self.distance + ", " + \
            "Strength: %0.2f" % self.strength + ", " + \
            "Passes: %d" % self.passes + ", " + \
            "InnerShadow: %d" % self.innerShadow + ", " + \
            "Knockout: %d" % self.knockout + ", " + \
            "CompositeSource: %d" % self.compositeSource
        return s
        
class FilterBlur(Filter):
    """
    Blur Filter
    """
    def __init__(self, id):
        super(FilterBlur, self).__init__(id)

    def parse(self, data):
        self.blurX = data.readFIXED()
        self.blurY = data.readFIXED()
        self.passes = data.readUI8() >> 3
    
    def __str__(self):
        s = "[FilterBlur] " + \
            "BlurX: %0.2f" % self.blurX + ", " + \
            "BlurY: %0.2f" % self.blurY + ", " + \
            "Passes: %d" % self.passes
        return s
        
class FilterGlow(Filter):
    """
    Glow Filter
    """
    def __init__(self, id):
        super(FilterGlow, self).__init__(id)

    def parse(self, data):
        self.glowColor = data.readRGBA()
        self.blurX = data.readFIXED()
        self.blurY = data.readFIXED()
        self.strength = data.readFIXED8()
        flags = data.readUI8()
        self.innerGlow = ((flags & 0x80) != 0)
        self.knockout = ((flags & 0x40) != 0)
        self.compositeSource = ((flags & 0x20) != 0)
        self.passes = flags & 0x1f
        
    def __str__(self):
        s = "[FilterGlow] " + \
            "glowColor: %s" % ColorUtils.to_rgb_string(self.glowColor) + ", " + \
            "BlurX: %0.2f" % self.blurX + ", " + \
            "BlurY: %0.2f" % self.blurY + ", " + \
            "Strength: %0.2f" % self.strength + ", " + \
            "Passes: %d" % self.passes + ", " + \
            "InnerGlow: %d" % self.innerGlow + ", " + \
            "Knockout: %d" % self.knockout
        return s
            
class FilterBevel(Filter):
    """
    Bevel Filter
    """
    def __init__(self, id):
        super(FilterBevel, self).__init__(id)

    def parse(self, data):
        self.shadowColor = data.readRGBA()
        self.highlightColor = data.readRGBA()
        self.blurX = data.readFIXED()
        self.blurY = data.readFIXED()
        self.angle = data.readFIXED()
        self.distance = data.readFIXED()
        self.strength = data.readFIXED8()
        flags = data.readUI8()
        self.innerShadow = ((flags & 0x80) != 0)
        self.knockout = ((flags & 0x40) != 0)
        self.compositeSource = ((flags & 0x20) != 0)
        self.onTop = ((flags & 0x10) != 0)
        self.passes = flags & 0x0f
        
    def __str__(self):
        s = "[FilterBevel] " + \
            "ShadowColor: %s" % ColorUtils.to_rgb_string(self.shadowColor) + ", " + \
            "HighlightColor: %s" % ColorUtils.to_rgb_string(self.highlightColor) + ", " + \
            "BlurX: %0.2f" % self.blurX + ", " + \
            "BlurY: %0.2f" % self.blurY + ", " + \
            "Angle: %0.2f" % self.angle + ", " + \
            "Passes: %d" % self.passes + ", " + \
            "Knockout: %d" % self.knockout
        return s
          
class FilterGradientGlow(Filter):
    """
    Gradient Glow Filter
    """
    def __init__(self, id):
        self.gradientColors = []
        self.gradientRatios = []
        super(FilterGradientGlow, self).__init__(id)

    def parse(self, data):
        self.gradientColors = []
        self.gradientRatios = []
        self.numColors = data.readUI8()
        for i in range(0, self.numColors):
            self.gradientColors.append(data.readRGBA())
        for i in range(0, self.numColors):
            self.gradientRatios.append(data.readUI8())
        self.blurX = data.readFIXED()
        self.blurY = data.readFIXED()
        self.strength = data.readFIXED8()
        flags = data.readUI8()
        self.innerShadow = ((flags & 0x80) != 0)
        self.knockout = ((flags & 0x40) != 0)
        self.compositeSource = ((flags & 0x20) != 0)
        self.onTop = ((flags & 0x20) != 0)
        self.passes = flags & 0x0f

class FilterConvolution(Filter):
    """
    Convolution Filter
    """
    def __init__(self, id):
        self.matrix = []
        super(FilterConvolution, self).__init__(id)

    def parse(self, data):
        self.matrix = []
        self.matrixX = data.readUI8()
        self.matrixY = data.readUI8()
        self.divisor = data.readFLOAT()
        self.bias = data.readFLOAT()
        length = matrixX * matrixY
        for i in range(0, length):
            self.matrix.append(data.readFLOAT())
        self.defaultColor = data.readRGBA()
        flags = data.readUI8()
        self.clamp = ((flags & 0x02) != 0)
        self.preserveAlpha = ((flags & 0x01) != 0)

class FilterColorMatrix(Filter):
    """
    ColorMatrix Filter
    """
    def __init__(self, id):
        self.colorMatrix = []
        super(FilterColorMatrix, self).__init__(id)

    def parse(self, data):
        self.colorMatrix = []
        for i in range(0, 20):
            self.colorMatrix.append(data.readFLOAT())
        for i in range(4, 20, 5):
            self.colorMatrix[i] /= 256.0
            
    def tostring(self):
        s = "[FilterColorMatrix] " + \
            " ".join(map(str, self.colorMatrix))
        return s
                
class FilterGradientBevel(FilterGradientGlow):
    """
    Gradient Bevel Filter
    """
    def __init__(self, id):
        super(FilterGradientBevel, self).__init__(id)
                                  
class SWFFilterFactory(object):
    """
    Filter factory
    """
    @classmethod
    def create(cls, type):
        """ Return the specified Filter """
        if type == 0: return FilterDropShadow(id)
        elif type == 1: return FilterBlur(id)
        elif type == 2: return FilterGlow(id)
        elif type == 3: return FilterBevel(id)
        elif type == 4: return FilterGradientGlow(id)
        elif type == 5: return FilterConvolution(id)
        elif type == 6: return FilterColorMatrix(id)
        elif type == 7: return FilterGradientBevel(id)
        else:
            raise Exception("Unknown filter type: %d" % type)


########NEW FILE########
__FILENAME__ = geom
import math

SNAP = 0.001

class Vector2(object):
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y
        
class Vector3(object):
    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z
    
    def clone(self):
        return Vector3(self.x, self.y, self.z)
    
    def cross(self, v1, v2):
        self.x = v1.y * v2.z - v1.z * v2.y
        self.y = v1.z * v2.x - v1.x * v2.z
        self.z = v1.x * v2.y - v1.y * v2.x
        return self
    
    def distance(self, v):
        dx = self.x - v.x
        dy = self.y - v.y
        dz = self.z - v.z
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def distanceSq(self, v):
        dx = self.x - v.x
        dy = self.y - v.y
        dz = self.z - v.z
        return (dx*dx + dy*dy + dz*dz)
    
    def dot(self, v):
        return self.x * v.x + self.y * v.y + self.z * v.z
    
    def length(self):
        return math.sqrt(self.x*self.x + self.y*self.y + self.z * self.z)
    
    def lengthSq(self):
        return (self.x*self.x + self.y*self.y + self.z * self.z)
    
    def addScalar(self, s):
        self.x += s
        self.y += s
        self.z += s
        return self
    
    def divScalar(self, s):
        self.x /= s
        self.y /= s
        self.z /= s
        return self
    
    def multScalar(self, s):
        self.x *= s
        self.y *= s
        self.z *= s
        return self
    
    def sub(self, a, b):
        self.x = a.x - b.x
        self.y = a.y - b.y
        self.z = a.z - b.z
        return self
    
    def subScalar(self, s):
        self.x -= s
        self.y -= s
        self.z -= s
        return self
    
    def equals(self, v, e=None):
        e = SNAP if e is None else e
        if v.x > self.x-e and v.x < self.x+e and \
           v.y > self.y-e and v.y < self.y+e and \
           v.z > self.z-e and v.z < self.z+e:
            return True
        else:
            return False
        
    def normalize(self):
        len = self.length()
        if len > 0.0:
            self.multScalar(1.0 / len)
        return self
    
    def set(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def tostring(self):
        return "%0.3f %0.3f %0.3f" % (self.x, self.y, self.z)
        
class Matrix2(object):
    """
    Matrix2
    """
    def __init__(self, a=1.0, b=0.0, c=0.0, d=1.0, tx=0.0, ty=0.0):
        self.a = a
        self.b = b
        self.c = c 
        self.d = d
        self.tx = tx
        self.ty = ty
        
    def append(self, a, b, c, d, tx, ty):
        a1 = self.a
        b1 = self.b
        c1 = self.c
        d1 = self.d

        self.a  = a*a1+b*c1
        self.b  = a*b1+b*d1
        self.c  = c*a1+d*c1
        self.d  = c*b1+d*d1
        self.tx = tx*a1+ty*c1+self.tx
        self.ty = tx*b1+ty*d1+self.ty
     
    def append_matrix(self, m):
        self.append(m.a, m.b, m.c, m.d, m.tx, m.ty)
    
    def multiply_point(self, vec):
        return [
            self.a*vec[0] + self.c*vec[1] + self.tx,
            self.b*vec[0] + self.d*vec[1] + self.ty
        ]
        
    def prepend(self, a, b, c, d, tx, ty):
        tx1 = self.tx
        if (a != 1.0 or b != 0.0 or c != 0.0 or d != 1.0):
            a1 = self.a
            c1 = self.c
            self.a  = a1*a+self.b*c
            self.b  = a1*b+self.b*d
            self.c  = c1*a+self.d*c
            self.d  = c1*b+self.d*d
        self.tx = tx1*a+self.ty*c+tx
        self.ty = tx1*b+self.ty*d+ty
        
    def prepend_matrix(self, m):
        self.prepend(m.a, m.b, m.c, m.d, m.tx, m.ty)
        
    def rotate(self, angle):
        cos = math.cos(angle)
        sin = math.sin(angle)
        a1 = self.a
        c1 = self.c
        tx1 = self.tx
        self.a = a1*cos-self.b*sin
        self.b = a1*sin+self.b*cos
        self.c = c1*cos-self.d*sin
        self.d = c1*sin+self.d*cos
        self.tx = tx1*cos-self.ty*sin
        self.ty = tx1*sin+self.ty*cos
    
    def scale(self, x, y):
        self.a *= x;
        self.d *= y;
        self.tx *= x;
        self.ty *= y;
     
    def translate(self, x, y):   
        self.tx += x;
        self.ty += y;
              
class Matrix4(object):
    """
    Matrix4
    """
    def __init__(self, data=None):
        if not data is None and len(data) == 16:
            self.n11 = data[0]; self.n12 = data[1]; self.n13 = data[2]; self.n14 = data[3]
            self.n21 = data[4]; self.n22 = data[5]; self.n23 = data[6]; self.n24 = data[7]
            self.n31 = data[8]; self.n32 = data[9]; self.n33 = data[10]; self.n34 = data[11]
            self.n41 = data[12]; self.n42 = data[13]; self.n43 = data[14]; self.n44 = data[15]
        else:
            self.n11 = 1.0; self.n12 = 0.0; self.n13 = 0.0; self.n14 = 0.0
            self.n21 = 0.0; self.n22 = 1.0; self.n23 = 0.0; self.n24 = 0.0
            self.n31 = 0.0; self.n32 = 0.0; self.n33 = 1.0; self.n34 = 0.0
            self.n41 = 0.0; self.n42 = 0.0; self.n43 = 0.0; self.n44 = 1.0
    
    def clone(self):
        return Matrix4(self.flatten())
    
    def flatten(self):
        return [self.n11, self.n12, self.n13, self.n14, \
                self.n21, self.n22, self.n23, self.n24, \
                self.n31, self.n32, self.n33, self.n34, \
                self.n41, self.n42, self.n43, self.n44]
         
    def identity(self):
        self.n11 = 1.0; self.n12 = 0.0; self.n13 = 0.0; self.n14 = 0.0
        self.n21 = 0.0; self.n22 = 1.0; self.n23 = 0.0; self.n24 = 0.0
        self.n31 = 0.0; self.n32 = 0.0; self.n33 = 1.0; self.n34 = 0.0
        self.n41 = 0.0; self.n42 = 0.0; self.n43 = 0.0; self.n44 = 1.0
        return self
    
    def multiply(self, a, b):
        a11 = a.n11; a12 = a.n12; a13 = a.n13; a14 = a.n14
        a21 = a.n21; a22 = a.n22; a23 = a.n23; a24 = a.n24
        a31 = a.n31; a32 = a.n32; a33 = a.n33; a34 = a.n34
        a41 = a.n41; a42 = a.n42; a43 = a.n43; a44 = a.n44
        b11 = b.n11; b12 = b.n12; b13 = b.n13; b14 = b.n14
        b21 = b.n21; b22 = b.n22; b23 = b.n23; b24 = b.n24
        b31 = b.n31; b32 = b.n32; b33 = b.n33; b34 = b.n34
        b41 = b.n41; b42 = b.n42; b43 = b.n43; b44 = b.n44

        self.n11 = a11 * b11 + a12 * b21 + a13 * b31 + a14 * b41
        self.n12 = a11 * b12 + a12 * b22 + a13 * b32 + a14 * b42
        self.n13 = a11 * b13 + a12 * b23 + a13 * b33 + a14 * b43
        self.n14 = a11 * b14 + a12 * b24 + a13 * b34 + a14 * b44

        self.n21 = a21 * b11 + a22 * b21 + a23 * b31 + a24 * b41
        self.n22 = a21 * b12 + a22 * b22 + a23 * b32 + a24 * b42
        self.n23 = a21 * b13 + a22 * b23 + a23 * b33 + a24 * b43
        self.n24 = a21 * b14 + a22 * b24 + a23 * b34 + a24 * b44

        self.n31 = a31 * b11 + a32 * b21 + a33 * b31 + a34 * b41
        self.n32 = a31 * b12 + a32 * b22 + a33 * b32 + a34 * b42
        self.n33 = a31 * b13 + a32 * b23 + a33 * b33 + a34 * b43
        self.n34 = a31 * b14 + a32 * b24 + a33 * b34 + a34 * b44

        self.n41 = a41 * b11 + a42 * b21 + a43 * b31 + a44 * b41
        self.n42 = a41 * b12 + a42 * b22 + a43 * b32 + a44 * b42
        self.n43 = a41 * b13 + a42 * b23 + a43 * b33 + a44 * b43
        self.n44 = a41 * b14 + a42 * b24 + a43 * b34 + a44 * b44
        return self
    
    def multiplyVector3(self, vec):
        vx = vec[0]
        vy = vec[1]
        vz = vec[2]
        d = 1.0 / (self.n41 * vx + self.n42 * vy + self.n43 * vz + self.n44)
        x = (self.n11 * vx + self.n12 * vy + self.n13 * vz + self.n14) * d
        y = (self.n21 * vx + self.n22 * vy + self.n23 * vz + self.n24) * d
        z = (self.n31 * vx + self.n32 * vy + self.n33 * vz + self.n34) * d
        return [x, y, z]
    
    def multiplyVec3(self, vec):
        vx = vec.x 
        vy = vec.y
        vz = vec.z
        d = 1.0 / (self.n41 * vx + self.n42 * vy + self.n43 * vz + self.n44)
        x = (self.n11 * vx + self.n12 * vy + self.n13 * vz + self.n14) * d
        y = (self.n21 * vx + self.n22 * vy + self.n23 * vz + self.n24) * d
        z = (self.n31 * vx + self.n32 * vy + self.n33 * vz + self.n34) * d
        return Vector3(x, y, z)
    
    def multiplyVector4(self, v):
        vx = v[0]; vy = v[1]; vz = v[2]; vw = v[3];

        x = self.n11 * vx + self.n12 * vy + self.n13 * vz + self.n14 * vw;
        y = self.n21 * vx + self.n22 * vy + self.n23 * vz + self.n24 * vw;
        z = self.n31 * vx + self.n32 * vy + self.n33 * vz + self.n34 * vw;
        w = self.n41 * vx + self.n42 * vy + self.n43 * vz + self.n44 * vw;

        return [x, y, z, w];
    
    def det(self):
        #( based on http://www.euclideanspace.com/maths/algebra/matrix/functions/inverse/fourD/index.htm )
        return (
            self.n14 * self.n23 * self.n32 * self.n41-
            self.n13 * self.n24 * self.n32 * self.n41-
            self.n14 * self.n22 * self.n33 * self.n41+
            self.n12 * self.n24 * self.n33 * self.n41+

            self.n13 * self.n22 * self.n34 * self.n41-
            self.n12 * self.n23 * self.n34 * self.n41-
            self.n14 * self.n23 * self.n31 * self.n42+
            self.n13 * self.n24 * self.n31 * self.n42+

            self.n14 * self.n21 * self.n33 * self.n42-
            self.n11 * self.n24 * self.n33 * self.n42-
            self.n13 * self.n21 * self.n34 * self.n42+
            self.n11 * self.n23 * self.n34 * self.n42+

            self.n14 * self.n22 * self.n31 * self.n43-
            self.n12 * self.n24 * self.n31 * self.n43-
            self.n14 * self.n21 * self.n32 * self.n43+
            self.n11 * self.n24 * self.n32 * self.n43+

            self.n12 * self.n21 * self.n34 * self.n43-
            self.n11 * self.n22 * self.n34 * self.n43-
            self.n13 * self.n22 * self.n31 * self.n44+
            self.n12 * self.n23 * self.n31 * self.n44+

            self.n13 * self.n21 * self.n32 * self.n44-
            self.n11 * self.n23 * self.n32 * self.n44-
            self.n12 * self.n21 * self.n33 * self.n44+
            self.n11 * self.n22 * self.n33 * self.n44)
        
    def lookAt(self, eye, center, up):
        x = Vector3(); y = Vector3(); z = Vector3();
        z.sub(eye, center).normalize();
        x.cross(up, z).normalize();
        y.cross(z, x).normalize();
        #eye.normalize()
        self.n11 = x.x; self.n12 = x.y; self.n13 = x.z; self.n14 = -x.dot(eye);
        self.n21 = y.x; self.n22 = y.y; self.n23 = y.z; self.n24 = -y.dot(eye);
        self.n31 = z.x; self.n32 = z.y; self.n33 = z.z; self.n34 = -z.dot(eye);
        self.n41 = 0.0; self.n42 = 0.0; self.n43 = 0.0; self.n44 = 1.0;
        return self;
    
    def multiplyScalar(self, s):
        self.n11 *= s; self.n12 *= s; self.n13 *= s; self.n14 *= s;
        self.n21 *= s; self.n22 *= s; self.n23 *= s; self.n24 *= s;
        self.n31 *= s; self.n32 *= s; self.n33 *= s; self.n34 *= s;
        self.n41 *= s; self.n42 *= s; self.n43 *= s; self.n44 *= s;
        return self
    
    @classmethod
    def inverse(cls, m1):
        # TODO: make this more efficient
        #( based on http://www.euclideanspace.com/maths/algebra/matrix/functions/inverse/fourD/index.htm )
        m2 = Matrix4();
        m2.n11 = m1.n23*m1.n34*m1.n42 - m1.n24*m1.n33*m1.n42 + m1.n24*m1.n32*m1.n43 - m1.n22*m1.n34*m1.n43 - m1.n23*m1.n32*m1.n44 + m1.n22*m1.n33*m1.n44;
        m2.n12 = m1.n14*m1.n33*m1.n42 - m1.n13*m1.n34*m1.n42 - m1.n14*m1.n32*m1.n43 + m1.n12*m1.n34*m1.n43 + m1.n13*m1.n32*m1.n44 - m1.n12*m1.n33*m1.n44;
        m2.n13 = m1.n13*m1.n24*m1.n42 - m1.n14*m1.n23*m1.n42 + m1.n14*m1.n22*m1.n43 - m1.n12*m1.n24*m1.n43 - m1.n13*m1.n22*m1.n44 + m1.n12*m1.n23*m1.n44;
        m2.n14 = m1.n14*m1.n23*m1.n32 - m1.n13*m1.n24*m1.n32 - m1.n14*m1.n22*m1.n33 + m1.n12*m1.n24*m1.n33 + m1.n13*m1.n22*m1.n34 - m1.n12*m1.n23*m1.n34;
        m2.n21 = m1.n24*m1.n33*m1.n41 - m1.n23*m1.n34*m1.n41 - m1.n24*m1.n31*m1.n43 + m1.n21*m1.n34*m1.n43 + m1.n23*m1.n31*m1.n44 - m1.n21*m1.n33*m1.n44;
        m2.n22 = m1.n13*m1.n34*m1.n41 - m1.n14*m1.n33*m1.n41 + m1.n14*m1.n31*m1.n43 - m1.n11*m1.n34*m1.n43 - m1.n13*m1.n31*m1.n44 + m1.n11*m1.n33*m1.n44;
        m2.n23 = m1.n14*m1.n23*m1.n41 - m1.n13*m1.n24*m1.n41 - m1.n14*m1.n21*m1.n43 + m1.n11*m1.n24*m1.n43 + m1.n13*m1.n21*m1.n44 - m1.n11*m1.n23*m1.n44;
        m2.n24 = m1.n13*m1.n24*m1.n31 - m1.n14*m1.n23*m1.n31 + m1.n14*m1.n21*m1.n33 - m1.n11*m1.n24*m1.n33 - m1.n13*m1.n21*m1.n34 + m1.n11*m1.n23*m1.n34;
        m2.n31 = m1.n22*m1.n34*m1.n41 - m1.n24*m1.n32*m1.n41 + m1.n24*m1.n31*m1.n42 - m1.n21*m1.n34*m1.n42 - m1.n22*m1.n31*m1.n44 + m1.n21*m1.n32*m1.n44;
        m2.n32 = m1.n14*m1.n32*m1.n41 - m1.n12*m1.n34*m1.n41 - m1.n14*m1.n31*m1.n42 + m1.n11*m1.n34*m1.n42 + m1.n12*m1.n31*m1.n44 - m1.n11*m1.n32*m1.n44;
        m2.n33 = m1.n13*m1.n24*m1.n41 - m1.n14*m1.n22*m1.n41 + m1.n14*m1.n21*m1.n42 - m1.n11*m1.n24*m1.n42 - m1.n12*m1.n21*m1.n44 + m1.n11*m1.n22*m1.n44;
        m2.n34 = m1.n14*m1.n22*m1.n31 - m1.n12*m1.n24*m1.n31 - m1.n14*m1.n21*m1.n32 + m1.n11*m1.n24*m1.n32 + m1.n12*m1.n21*m1.n34 - m1.n11*m1.n22*m1.n34;
        m2.n41 = m1.n23*m1.n32*m1.n41 - m1.n22*m1.n33*m1.n41 - m1.n23*m1.n31*m1.n42 + m1.n21*m1.n33*m1.n42 + m1.n22*m1.n31*m1.n43 - m1.n21*m1.n32*m1.n43;
        m2.n42 = m1.n12*m1.n33*m1.n41 - m1.n13*m1.n32*m1.n41 + m1.n13*m1.n31*m1.n42 - m1.n11*m1.n33*m1.n42 - m1.n12*m1.n31*m1.n43 + m1.n11*m1.n32*m1.n43;
        m2.n43 = m1.n13*m1.n22*m1.n41 - m1.n12*m1.n23*m1.n41 - m1.n13*m1.n21*m1.n42 + m1.n11*m1.n23*m1.n42 + m1.n12*m1.n21*m1.n43 - m1.n11*m1.n22*m1.n43;
        m2.n44 = m1.n12*m1.n23*m1.n31 - m1.n13*m1.n22*m1.n31 + m1.n13*m1.n21*m1.n32 - m1.n11*m1.n23*m1.n32 - m1.n12*m1.n21*m1.n33 + m1.n11*m1.n22*m1.n33;
        m2.multiplyScalar(1.0 / m1.det());
        return m2;
    
    @classmethod
    def rotationMatrix(cls, x, y, z, angle):
        rot = Matrix4()
        c = math.cos(angle)
        s = math.sin(angle)
        t = 1 - c
        rot.n11 = t * x * x + c
        rot.n12 = t * x * y - s * z
        rot.n13 = t * x * z + s * y
        rot.n21 = t * x * y + s * z
        rot.n22 = t * y * y + c
        rot.n23 = t * y * z - s * x
        rot.n31 = t * x * z - s * y
        rot.n32 = t * y * z + s * x
        rot.n33 = t * z * z + c
        return rot
    
    @classmethod
    def scaleMatrix(cls, x, y, z):
        m = Matrix4()
        m.n11 = x
        m.n22 = y
        m.n33 = z
        return m
    
    @classmethod
    def translationMatrix(cls, x, y, z):
        m = Matrix4()
        m.n14 = x
        m.n24 = y
        m.n34 = z
        return m

########NEW FILE########
__FILENAME__ = movie
"""
SWF
"""
from tag import SWFTimelineContainer
from stream import SWFStream
from export import SVGExporter
import StringIO

class SWFHeaderException(Exception):
    """ Exception raised in case of an invalid SWFHeader """
    def __init__(self, message):
         super(SWFHeaderException, self).__init__(message)

class SWFHeader(object):
    """ SWF header """
    def __init__(self, stream):
        a = stream.readUI8()
        b = stream.readUI8()
        c = stream.readUI8()
        if not a in [0x43, 0x46] or b != 0x57 or c != 0x53:
            # Invalid signature! ('FWS' or 'CWS')
            raise SWFHeaderException("not a SWF file! (invalid signature)")

        self._compressed = (a == 0x43)
        self._version = stream.readUI8()
        self._file_length = stream.readUI32()
        if not self._compressed:
            self._frame_size = stream.readRECT()
            self._frame_rate = stream.readFIXED8()
            self._frame_count = stream.readUI16()

    @property
    def frame_size(self):
        """ Return frame size as a SWFRectangle """
        return self._frame_size

    @property
    def frame_rate(self):
        """ Return frame rate """
        return self._frame_rate

    @property
    def frame_count(self):
        """ Return number of frames """
        return self._frame_count
                
    @property
    def file_length(self):
        """ Return uncompressed file length """
        return self._file_length
                    
    @property
    def version(self):
        """ Return SWF version """
        return self._version
                
    @property
    def compressed(self):
        """ Whether the SWF is compressed using ZLIB """
        return self._compressed
        
    def __str__(self):
        return "   [SWFHeader]\n" + \
            "       Version: %d\n" % self.version + \
            "       FileLength: %d\n" % self.file_length + \
            "       FrameSize: %s\n" % self.frame_size.__str__() + \
            "       FrameRate: %d\n" % self.frame_rate + \
            "       FrameCount: %d\n" % self.frame_count

class SWF(SWFTimelineContainer):
    """
    SWF class
    
    The SWF (pronounced 'swiff') file format delivers vector graphics, text, 
    video, and sound over the Internet and is supported by Adobe Flash
    Player software. The SWF file format is designed to be an efficient 
    delivery format, not a format for exchanging graphics between graphics 
    editors.
    
    @param file: a file object with read(), seek(), tell() methods.
    """
    def __init__(self, file=None):
        super(SWF, self).__init__()
        self._data = None if file is None else SWFStream(file)
        self._header = None
        if self._data is not None:
            self.parse(self._data)
    
    @property
    def data(self):
        """
        Return the SWFStream object (READ ONLY)
        """
        return self._data
    
    @property
    def header(self):
        """ Return the SWFHeader """
        return self._header
        
    def export(self, exporter=None, force_stroke=False):
        """
        Export this SWF using the specified exporter. 
        When no exporter is passed in the default exporter used 
        is swf.export.SVGExporter.
        
        Exporters should extend the swf.export.BaseExporter class.
        
        @param exporter : the exporter to use
        @param force_stroke : set to true to force strokes on fills,
                              useful for some edge cases.
        """
        exporter = SVGExporter() if exporter is None else exporter
        if self._data is None:
            raise Exception("This SWF was not loaded! (no data)")
        if len(self.tags) == 0:
            raise Exception("This SWF doesn't contain any tags!")
        return exporter.export(self, force_stroke)
            
    def parse_file(self, filename):
        """ Parses the SWF from a filename """
        self.parse(open(filename, 'rb'))
        
    def parse(self, data):
        """ 
        Parses the SWF.
        
        The @data parameter can be a file object or a SWFStream
        """
        self._data = data = data if isinstance(data, SWFStream) else SWFStream(data)
        self._header = SWFHeader(self._data)
        if self._header.compressed:
            import zlib
            data = data.f.read()
            zip = zlib.decompressobj()
            temp = StringIO.StringIO()
            temp.write(zip.decompress(data))
            temp.seek(0)
            data = SWFStream(temp)
            self._header._frame_size = data.readRECT()
            self._header._frame_rate = data.readFIXED8()
            self._header._frame_count = data.readUI16()
        self.parse_tags(data)
        
        
    def __str__(self):
        s = "[SWF]\n"
        s += self._header.__str__()
        for tag in self.tags:
            s += tag.__str__() + "\n"
        return s
        
########NEW FILE########
__FILENAME__ = stream
import struct, math
from data import *
from actions import *
from filters import SWFFilterFactory

class SWFStream(object):
    """
    SWF File stream
    """
    FLOAT16_EXPONENT_BASE = 15
    
    def __init__(self, file):
        """ Initialize with a file object """
        self.f = file
        self._bit_pending = 0
        
    def bin(self, s):
        """ Return a value as a binary string """
        return str(s) if s<=1 else bin(s>>1) + str(s&1)
        
    def calc_max_bits(self, signed, values):
        """ Calculates the maximim needed bits to represent a value """
        b = 0
        vmax = -10000000
        
        for val in values:
            if signed:
                b = b | val if val >= 0 else b | ~val << 1
                vmax = val if vmax < val else vmax
            else:
                b |= val;
        bits = 0
        if b > 0:
            bits = len(self.bin(b)) - 2
            if signed and vmax > 0 and len(self.bin(vmax)) - 2 >= bits:
                bits += 1
        return bits
    
    def close(self):
        """ Closes the stream """
        if self.f:
            self.f.close()
            
    def readbits(self, bits, bit_buffer=0):
        """ Read the specified number of bits from the stream """
        if bits == 0: return bit_buffer
        
        if self._bits_pending > 0:
            self.f.seek(self.f.tell() - 1)
            byte = ord(self.f.read(1)) & (0xff >> (8 - self._bits_pending))
            consumed = min(self._bits_pending, bits)
            self._bits_pending -= consumed
            partial = byte >> self._bits_pending
        else:
            consumed = min(8, bits);
            self._bits_pending = 8 - consumed
            partial = ord(self.f.read(1)) >> self._bits_pending
            
        bits -= consumed;
        bit_buffer = (bit_buffer << consumed) | partial
        return self.readbits(bits, bit_buffer) if bits > 0 else bit_buffer
     
    def readFB(self, bits):
        """ Read a float using the specified number of bits """
        return float(self.readSB(bits)) / 65536.0
          
    def readSB(self, bits):
        """ Read a signed int using the specified number of bits """
        shift = 32 - bits
        return int32(self.readbits(bits) << shift) >> shift
        
    def readUB(self, bits):
        """ Read a unsigned int using the specified number of bits """
        return self.readbits(bits)
            
    def readSI8(self):
        """ Read a signed byte """
        self.reset_bits_pending();
        return struct.unpack('b', self.f.read(1))[0]
            
    def readUI8(self):
        """ Read a unsigned byte """
        self.reset_bits_pending();
        return struct.unpack('B', self.f.read(1))[0]
        
    def readSI16(self):
        """ Read a signed short """
        self.reset_bits_pending();
        return struct.unpack('h', self.f.read(2))[0]

    def readUI16(self):
        """ Read a unsigned short """
        self.reset_bits_pending();
        return struct.unpack('H', self.f.read(2))[0]    

    def readSI32(self):
        """ Read a signed int """
        self.reset_bits_pending();
        return struct.unpack('<i', self.f.read(4))[0]

    def readUI32(self):
        """ Read a unsigned int """
        self.reset_bits_pending();
        return struct.unpack('<I', self.f.read(4))[0]
    
    def readEncodedU32(self):
        """ Read a encoded unsigned int """
        self.reset_bits_pending();
        result = self.readUI8();
        if result & 0x80 != 0:
            result = (result & 0x7f) | (self.readUI8() << 7)
            if result & 0x4000 != 0:
                result = (result & 0x3fff) | (self.readUI8() << 14)
                if result & 0x200000 != 0:
                    result = (result & 0x1fffff) | (self.readUI8() << 21)
                    if result & 0x10000000 != 0:
                        result = (result & 0xfffffff) | (self.readUI8() << 28)
        return result
  
    def readFLOAT(self):
        """ Read a float """
        self.reset_bits_pending();
        return struct.unpack('f', self.f.read(4))[0]
    
    def readFLOAT16(self):
        """ Read a 2 byte float """
        self.reset_bits_pending()
        word = self.readUI16()
        sign = -1 if ((word & 0x8000) != 0) else 1
        exponent = (word >> 10) & 0x1f
        significand = word & 0x3ff
        if exponent == 0:
            if significand == 0:
                return 0.0
            else:
                return sign * math.pow(2, 1 - SWFStream.FLOAT16_EXPONENT_BASE) * (significand / 1024.0)
        if exponent == 31:
            if significand == 0:
                return float('-inf') if sign < 0 else float('inf')
            else:
                return float('nan')
        # normal number
        return sign * math.pow(2, exponent - SWFStream.FLOAT16_EXPONENT_BASE) * (1 + significand / 1024.0)
        
    def readFIXED(self):
        """ Read a 16.16 fixed value """
        self.reset_bits_pending()
        return self.readSI32() / 65536.0

    def readFIXED8(self):
        """ Read a 8.8 fixed value """
        self.reset_bits_pending()
        return self.readSI16() / 256.0

    def readCXFORM(self):
        """ Read a SWFColorTransform """
        return SWFColorTransform(self)
    
    def readCXFORMWITHALPHA(self):
        """ Read a SWFColorTransformWithAlpha """
        return SWFColorTransformWithAlpha(self)
    
    def readGLYPHENTRY(self, glyphBits, advanceBits):
        """ Read a SWFGlyphEntry """
        return SWFGlyphEntry(self, glyphBits, advanceBits)
        
    def readGRADIENT(self, level=1):
        """ Read a SWFGradient """
        return SWFGradient(self, level)
                
    def readFOCALGRADIENT(self, level=1):
        """ Read a SWFFocalGradient """
        return SWFFocalGradient(self, level)
            
    def readGRADIENTRECORD(self, level=1):
        """ Read a SWFColorTransformWithAlpha """
        return SWFGradientRecord(self, level)
    
    def readKERNINGRECORD(self, wideCodes):
        """ Read a SWFKerningRecord """
        return SWFKerningRecord(self, wideCodes)
        
    def readLANGCODE(self):
        """ Read a language code """
        self.reset_bits_pending()
        return self.readUI8()
        
    def readMATRIX(self):
        """ Read a SWFMatrix """
        return SWFMatrix(self)
        
    def readRECT(self):
        """ Read a SWFMatrix """
        r = SWFRectangle()
        r.parse(self)
        return r
    
    def readSHAPE(self, unit_divisor=20):
        """ Read a SWFShape """
        return SWFShape(self, 1, unit_divisor)
        
    def readSHAPEWITHSTYLE(self, level=1, unit_divisor=20):
        """ Read a SWFShapeWithStyle """
        return SWFShapeWithStyle(self, level, unit_divisor)
    
    def readCURVEDEDGERECORD(self, num_bits):
        """ Read a SWFShapeRecordCurvedEdge """
        return SWFShapeRecordCurvedEdge(self, num_bits)
            
    def readSTRAIGHTEDGERECORD(self, num_bits):
        """ Read a SWFShapeRecordStraightEdge """
        return SWFShapeRecordStraightEdge(self, num_bits)
    
    def readSTYLECHANGERECORD(self, states, fill_bits, line_bits, level = 1):
        """ Read a SWFShapeRecordStyleChange """
        return SWFShapeRecordStyleChange(self, states, fill_bits, line_bits, level)
        
    def readFILLSTYLE(self, level=1):
        """ Read a SWFFillStyle """
        return SWFFillStyle(self, level)
    
    def readTEXTRECORD(self, glyphBits, advanceBits, previousRecord=None, level=1):
        """ Read a SWFTextRecord """
        if self.readUI8() == 0:
            return None
        else:
            self.seek(self.tell() - 1)
            return SWFTextRecord(self, glyphBits, advanceBits, previousRecord, level)
            
    def readLINESTYLE(self, level=1):
        """ Read a SWFLineStyle """
        return SWFLineStyle(self, level)
    
    def readLINESTYLE2(self, level=1):
        """ Read a SWFLineStyle2 """
        return SWFLineStyle2(self, level)
    
    def readMORPHFILLSTYLE(self, level=1):
        """ Read a SWFMorphFillStyle """
        return SWFMorphFillStyle(self, level)
    
    def readMORPHLINESTYLE(self, level=1):
        """ Read a SWFMorphLineStyle """
        return SWFMorphLineStyle(self, level)
        
    def readMORPHGRADIENT(self, level=1):
        """ Read a SWFTextRecord """
        return SWFMorphGradient(self, level)
     
    def readMORPHGRADIENTRECORD(self):
        """ Read a SWFTextRecord """
        return SWFMorphGradientRecord(self)
    
    def readACTIONRECORD(self):
        """ Read a SWFActionRecord """
        action = None
        actionCode = self.readUI8()
        if actionCode != 0:
            actionLength = self.readUI16() if actionCode >= 0x80 else 0
            #print "0x%x"%actionCode, actionLength
            action = SWFActionFactory.create(actionCode, actionLength)
            action.parse(self)
        return action
        
    def readCLIPACTIONS(self, version):
        """ Read a SWFClipActions """
        return SWFClipActions(self, version)
    
    def readCLIPACTIONRECORD(self, version):
        """ Read a SWFClipActionRecord """
        pos = self.tell()
        flags = self.readUI32() if version >= 6 else self.readUI16()
        if flags == 0:
            return None
        else:
            self.seek(pos)
            return SWFClipActionRecord(self, version)
            
    def readCLIPEVENTFLAGS(self, version):
        """ Read a SWFClipEventFlags """
        return SWFClipEventFlags(self, version)
        
    def readRGB(self):
        """ Read a RGB color """
        self.reset_bits_pending();
        r = self.readUI8()
        g = self.readUI8()
        b = self.readUI8()
        return (0xff << 24) | (r << 16) | (g << 8) | b
        
    def readRGBA(self):
        """ Read a RGBA color """
        self.reset_bits_pending();
        r = self.readUI8()
        g = self.readUI8()
        b = self.readUI8()
        a = self.readUI8()
        return (a << 24) | (r << 16) | (g << 8) | b
    
    def readSYMBOL(self):
        """ Read a SWFSymbol """
        return SWFSymbol(self)
        
    def readString(self):
        """ Read a string """
        s = self.f.read(1)
        string = ""
        while ord(s) > 0:
            string += s
            s = self.f.read(1)
        return string
    
    def readFILTER(self):
        """ Read a SWFFilter """
        filterId = self.readUI8()
        filter = SWFFilterFactory.create(filterId)
        filter.parse(self)
        return filter
    
    def readZONEDATA(self):
        """ Read a SWFZoneData """
        return SWFZoneData(self)
        
    def readZONERECORD(self):
        """ Read a SWFZoneRecord """
        return SWFZoneRecord(self)
        
    def readraw_tag(self):
        """ Read a SWFRawTag """
        return SWFRawTag(self)
    
    def readtag_header(self):
        """ Read a tag header """
        pos = self.tell()
        tag_type_and_length = self.readUI16()
        tag_length = tag_type_and_length & 0x003f
        if tag_length == 0x3f:
            # The SWF10 spec sez that this is a signed int.
            # Shouldn't it be an unsigned int?
            tag_length = self.readSI32();
        return SWFRecordHeader(tag_type_and_length >> 6, tag_length, self.tell() - pos)
    
    def skip_bytes(self, length):
        """ Skip over the specified number of bytes """
        self.f.seek(self.tell() + length)
              
    def reset_bits_pending(self):
        """ Reset the bit array """
        self._bits_pending = 0
    
    def read(self, count=0):
        """ Read """
        return self.f.read(count) if count > 0 else self.f.read()
        
    def seek(self, pos, whence=0):
        """ Seek """
        self.f.seek(pos, whence)
        
    def tell(self):
        """ Tell """
        return self.f.tell()
        
def int32(x):
    """ Return a signed or unsigned int """
    if x>0xFFFFFFFF:
        raise OverflowError
    if x>0x7FFFFFFF:
        x=int(0x100000000-x)
        if x<2147483648:
            return -x
        else:
            return -2147483648
    return x
########NEW FILE########
__FILENAME__ = tag
from consts import *
from data import *
from utils import *
from stream import *
from PIL import Image
import struct
import StringIO

class TagFactory(object):
    @classmethod
    def create(cls, type):
        """ Return the created tag by specifiying an integer """
        if type == 0: return TagEnd()
        elif type == 1: return TagShowFrame()
        elif type == 2: return TagDefineShape()
        elif type == 4: return TagPlaceObject()
        elif type == 5: return TagRemoveObject()
        elif type == 6: return TagDefineBits()
        elif type == 8: return TagJPEGTables()
        elif type == 9: return TagSetBackgroundColor()
        elif type == 10: return TagDefineFont()
        elif type == 11: return TagDefineText()
        elif type == 12: return TagDoAction()
        elif type == 13: return TagDefineFontInfo()
        elif type == 20: return TagDefineBitsLossless()
        elif type == 21: return TagDefineBitsJPEG2()
        elif type == 22: return TagDefineShape2()
        elif type == 26: return TagPlaceObject2()
        elif type == 28: return TagRemoveObject2()
        elif type == 32: return TagDefineShape3()
        elif type == 33: return TagDefineText2()
        elif type == 35: return TagDefineBitsJPEG3()
        elif type == 36: return TagDefineBitsLossless2()
        elif type == 39: return TagDefineSprite()
        elif type == 43: return TagFrameLabel()
        elif type == 46: return TagDefineMorphShape()
        elif type == 48: return TagDefineFont2()
        elif type == 69: return TagFileAttributes()
        elif type == 70: return TagPlaceObject3()
        elif type == 73: return TagDefineFontAlignZones()
        elif type == 74: return TagCSMTextSettings()
        elif type == 75: return TagDefineFont3()
        elif type == 76: return TagSymbolClass()
        elif type == 77: return TagMetadata()
        elif type == 82: return TagDoABC()
        elif type == 83: return TagDefineShape4()
        elif type == 86: return TagDefineSceneAndFrameLabelData()
        elif type == 88: return TagDefineFontName()
        else: return None

class Tag(object):
    def __init__(self):
        pass

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 1

    @property
    def name(self):
        """ The tag name """
        return ""

    def parse(self, data, length, version=1):
        """ Parses this tag """
        pass

    def __str__(self):
        return "[%02d:%s]" % (self.type, self.name)

class DefinitionTag(Tag):

    def __init__(self):
        super(DefinitionTag, self).__init__()
        self._characterId = -1

    @property
    def characterId(self):
        """ Return the character ID """
        return self._characterId

    @characterId.setter
    def characterId(self, value):
        """ Sets the character ID """
        self._characterId = value

    def parse(self, data, length, version=1):
        pass

class DisplayListTag(Tag):
    characterId = -1
    def __init__(self):
        super(DisplayListTag, self).__init__()

    def parse(self, data, length, version=1):
        pass

class SWFTimelineContainer(DefinitionTag):
    def __init__(self):
        self.tags = []
        super(SWFTimelineContainer, self).__init__()

    def parse_tags(self, data, version=1):
        pos = data.tell()
        self.file_length = self._get_file_length(data, pos)
        tag = None
        while type(tag) != TagEnd:
            tag = self.parse_tag(data)
            if tag:
                #print tag.name
                self.tags.append(tag)

    def parse_tag(self, data):
        pos = data.tell()
        eof = (pos > self.file_length)
        if eof:
            print "WARNING: end of file encountered, no end tag."
            return TagEnd()
        raw_tag = data.readraw_tag()
        tag_type = raw_tag.header.type
        tag = TagFactory.create(tag_type)
        if tag is not None:
            #print tag.name
            data.seek(raw_tag.pos_content)
            data.reset_bits_pending()
            tag.parse(data, raw_tag.header.content_length, tag.version)
            #except:
            #    print "=> tag_error", tag.name
            data.seek(pos + raw_tag.header.tag_length)
        else:
            #if tag_type != 12 and tag_type != 34:
            #    print "[WARNING] unhandled tag %d" % tag_type
            data.skip_bytes(raw_tag.header.tag_length)
        data.seek(pos + raw_tag.header.tag_length)
        return tag

    def _get_file_length(self, data, pos):
        data.f.seek(0, 2)
        length = data.tell()
        data.f.seek(pos)
        return length

class TagEnd(Tag):
    """
    The End tag marks the end of a file. This must always be the last tag in a file.
    The End tag is also required to end a sprite definition.
    The minimum file format version is SWF 1.
    """
    TYPE = 0
    def __init__(self):
        super(TagEnd, self).__init__()

    @property
    def name(self):
        """ The tag name """
        return "End"

    @property
    def type(self):
        return TagEnd.TYPE

    def __str__(self):
        return "[%02d:%s]" % (self.type, self.name)

class TagShowFrame(Tag):
    """
    The ShowFrame tag instructs Flash Player to display the contents of the
    display list. The file is paused for the duration of a single frame.
    The minimum file format version is SWF 1.
    """
    TYPE = 1
    def __init__(self):
        super(TagShowFrame, self).__init__()

    @property
    def name(self):
        return "ShowFrame"

    @property
    def type(self):
        return TagShowFrame.TYPE

    def __str__(self):
        return "[%02d:%s]" % (self.type, self.name)

class TagDefineShape(DefinitionTag):
    """
    The DefineShape tag defines a shape for later use by control tags such as
    PlaceObject. The ShapeId uniquely identifies this shape as 'character' in
    the Dictionary. The ShapeBounds field is the rectangle that completely
    encloses the shape. The SHAPEWITHSTYLE structure includes all the paths,
    fill styles and line styles that make up the shape.
    The minimum file format version is SWF 1.
    """
    TYPE = 2

    def __init__(self):
        self._shapes = []
        self._shape_bounds = None
        super(TagDefineShape, self).__init__()

    @property
    def name(self):
        return "DefineShape"

    @property
    def type(self):
        return TagDefineShape.TYPE

    @property
    def shapes(self):
        """ Return list of SWFShape """
        return self._shapes

    @property
    def shape_bounds(self):
        """ Return the bounds of this tag as a SWFRectangle """
        return self._shape_bounds

    def export(self, handler=None):
        """ Export this tag """
        self.shapes.export(handler)

    def parse(self, data, length, version=1):
        self.characterId = data.readUI16()
        self._shape_bounds = data.readRECT()
        self._shapes = data.readSHAPEWITHSTYLE(self.level)

    def __str__(self):
        s = super(TagDefineShape, self).__str__( ) + " " + \
            "ID: %d" % self.characterId + ", " + \
            "Bounds: " + self._shape_bounds.__str__()
        s += "\n%s" % self._shapes.__str__()
        return s

class TagPlaceObject(DisplayListTag):
    """
    The PlaceObject tag adds a character to the display list. The CharacterId
    identifies the character to be added. The Depth field specifies the
    stacking order of the character. The Matrix field species the position,
    scale, and rotation of the character. If the size of the PlaceObject tag
    exceeds the end of the transformation matrix, it is assumed that a
    ColorTransform field is appended to the record. The ColorTransform field
    specifies a color effect (such as transparency) that is applied to the character.
    The same character can be added more than once to the display list with
    a different depth and transformation matrix.
    """
    TYPE = 4
    hasClipActions = False
    hasClipDepth = False
    hasName = False
    hasRatio = False
    hasColorTransform = False
    hasMatrix = False
    hasCharacter = False
    hasMove = False
    hasImage = False
    hasClassName = False
    hasCacheAsBitmap = False
    hasBlendMode = False
    hasFilterList = False
    depth = 0
    matrix = None
    colorTransform = None
    # Forward declarations for TagPlaceObject2
    ratio = 0
    instanceName = None
    clipDepth = 0
    clipActions = None
    # Forward declarations for TagPlaceObject3
    className = None
    blendMode = 0
    bitmapCache = 0

    def __init__(self):
        self._surfaceFilterList = []
        super(TagPlaceObject, self).__init__()

    def parse(self, data, length, version=1):
        """ Parses this tag """
        pos = data.tell()
        self.characterId = data.readUI16()
        self.depth = data.readUI16();
        self.matrix = data.readMATRIX();
        self.hasCharacter = True;
        self.hasMatrix = True;
        if data.tell() - pos < length:
            colorTransform = data.readCXFORM()
            self.hasColorTransform = True

    @property
    def filters(self):
        """ Returns a list of filter """
        return self._surfaceFilterList

    @property
    def name(self):
        return "PlaceObject"

    @property
    def type(self):
        return TagPlaceObject.TYPE

    def __str__(self):
        s = super(TagPlaceObject, self).__str__() + " " + \
            "Depth: %d, " % self.depth + \
            "CharacterID: %d" % self.characterId
        if self.hasName:
            s+= ", InstanceName: %s" % self.instanceName
        if self.hasMatrix:
            s += ", Matrix: %s" % self.matrix.__str__()
        if self.hasClipDepth:
            s += ", ClipDepth: %d" % self.clipDepth
        if self.hasColorTransform:
            s += ", ColorTransform: %s" % self.colorTransform.__str__()
        if self.hasFilterList:
            s += ", Filters: %d" % len(self.filters)
        if self.hasBlendMode:
            s += ", Blendmode: %d" % self.blendMode
        return s

class TagRemoveObject(DisplayListTag):
    """
    The RemoveObject tag removes the specified character (at the specified depth)
    from the display list.
    The minimum file format version is SWF 1.
    """
    TYPE = 5
    depth = 0
    def __init__(self):
        super(TagRemoveObject, self).__init__()

    @property
    def name(self):
        return "RemoveObject"

    @property
    def type(self):
        return TagRemoveObject.TYPE

    def parse(self, data, length, version=1):
        """ Parses this tag """
        self.characterId = data.readUI16()
        self.depth = data.readUI16()

class TagDefineBits(DefinitionTag):
    """
    This tag defines a bitmap character with JPEG compression. It contains only
    the JPEG compressed image data (from the Frame Header onward). A separate
    JPEGTables tag contains the JPEG encoding data used to encode this image
    (the Tables/Misc segment).
    NOTE:
        Only one JPEGTables tag is allowed in a SWF file, and thus all bitmaps
        defined with DefineBits must share common encoding tables.
    The data in this tag begins with the JPEG SOI marker 0xFF, 0xD8 and ends
    with the EOI marker 0xFF, 0xD9. Before version 8 of the SWF file format,
    SWF files could contain an erroneous header of 0xFF, 0xD9, 0xFF, 0xD8 before
    the JPEG SOI marker.
    """
    TYPE = 6
    bitmapData = None
    def __init__(self):
        self.bitmapData = StringIO.StringIO()
        super(TagDefineBits, self).__init__()

    @property
    def name(self):
        return "DefineBits"

    @property
    def type(self):
        return TagDefineBits.TYPE

    def parse(self, data, length, version=1):
        self.bitmapData = StringIO.StringIO()
        self.characterId = data.readUI16()
        if length > 2:
            self.bitmapData.write(data.f.read(length - 2))
            self.bitmapData.seek(0)

class TagJPEGTables(DefinitionTag):
    """
    This tag defines the JPEG encoding table (the Tables/Misc segment) for all
    JPEG images defined using the DefineBits tag. There may only be one
    JPEGTables tag in a SWF file.
    The data in this tag begins with the JPEG SOI marker 0xFF, 0xD8 and ends
    with the EOI marker 0xFF, 0xD9. Before version 8 of the SWF file format,
    SWF files could contain an erroneous header of 0xFF, 0xD9, 0xFF, 0xD8 before
    the JPEG SOI marker.
    The minimum file format version for this tag is SWF 1.
    """
    TYPE = 8
    jpegTables = None
    length = 0

    def __init__(self):
        super(TagJPEGTables, self).__init__()
        self.jpegTables = StringIO.StringIO()

    @property
    def name(self):
        return "JPEGTables"

    @property
    def type(self):
        return TagJPEGTables.TYPE

    def parse(self, data, length, version=1):
        self.length = length
        if length > 0:
            self.jpegTables.write(data.f.read(length))
            self.jpegTables.seek(0)

    def __str__(self):
        s = super(TagJPEGTables, self).__str__()
        s += " Length: %d" % self.length
        return s

class TagSetBackgroundColor(Tag):
    """
    The SetBackgroundColor tag sets the background color of the display.
    The minimum file format version is SWF 1.
    """
    TYPE = 9
    color = 0
    def __init__(self):
        super(TagSetBackgroundColor, self).__init__()

    def parse(self, data, length, version=1):
        self.color = data.readRGB()

    @property
    def name(self):
        return "SetBackgroundColor"

    @property
    def type(self):
        return TagSetBackgroundColor.TYPE

    def __str__(self):
        s = super(TagSetBackgroundColor, self).__str__()
        s += " Color: " + ColorUtils.to_rgb_string(self.color)
        return s

class TagDefineFont(DefinitionTag):
    """
    The DefineFont tag defines the shape outlines of each glyph used in a
    particular font. Only the glyphs that are used by subsequent DefineText
    tags are actually defined.
    DefineFont tags cannot be used for dynamic text. Dynamic text requires
    the DefineFont2 tag.
    The minimum file format version is SWF 1.
    """
    TYPE= 10
    glyphShapeTable = []
    def __init__(self):
        super(TagDefineFont, self).__init__()

    @property
    def name(self):
        return "DefineFont"

    @property
    def type(self):
        return TagDefineFont.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 1

    @property
    def unitDivisor(self):
        return 1

    def parse(self, data, length, version=1):
        self.glyphShapeTable = []
        self.characterId = data.readUI16()
        # Because the glyph shape table immediately follows the offset table,
        # the number of entries in each table (the number of glyphs in the font) can be inferred by
        # dividing the first entry in the offset table by two.
        numGlyphs = data.readUI16() >> 1
        # Skip offsets. We don't need them here.
        data.skip_bytes((numGlyphs - 1) << 1)
        # Read glyph shape table
        for i in range(0, numGlyphs):
            self.glyphShapeTable.append(data.readSHAPE(self.unitDivisor))

class TagDefineText(DefinitionTag):
    """
    The DefineText tag defines a block of static text. It describes the font,
    size, color, and exact position of every character in the text object.
    The minimum file format version is SWF 1.
    """
    TYPE = 11
    textBounds = None
    textMatrix = None

    def __init__(self):
        self._records = []
        super(TagDefineText, self).__init__()

    @property
    def name(self):
        return "TagDefineText"

    @property
    def type(self):
        return TagDefineText.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 1

    @property
    def records(self):
        """ Return list of SWFTextRecord """
        return self._records

    def parse(self, data, length, version=1):
        self._records = []
        self.characterId = data.readUI16()
        self.textBounds = data.readRECT()
        self.textMatrix = data.readMATRIX()
        glyphBits = data.readUI8()
        advanceBits = data.readUI8()
        record = None
        record = data.readTEXTRECORD(glyphBits, advanceBits, record, self.level)
        while not record is None:
            self._records.append(record)
            record = data.readTEXTRECORD(glyphBits, advanceBits, record, self.level)

class TagDoAction(Tag):
    """
    DoAction instructs Flash Player to perform a list of actions when the
    current frame is complete. The actions are performed when the ShowFrame
    tag is encountered, regardless of where in the frame the DoAction tag appears.
    Starting with SWF 9, if the ActionScript3 field of the FileAttributes tag is 1,
    the contents of the DoAction tag will be ignored.
    """
    TYPE = 12
    def __init__(self):
        self._actions = []
        super(TagDoAction, self).__init__()

    @property
    def name(self):
        return "DoAction"

    @property
    def type(self):
        """ Return the SWF tag type """
        return TagDoAction.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        """ Return the minimum SWF version """
        return 9

    @property
    def actions(self):
        """ Return list of SWFActionRecord """
        return self._actions

    def parse(self, data, length, version=1):
        self._actions = []
        action = data.readACTIONRECORD()
        while not action is None:
            #print action.tostring()
            self._actions.append(action)
            action = data.readACTIONRECORD()

class TagDefineFontInfo(Tag):
    """
    The DefineFontInfo tag defines a mapping from a glyph font (defined with DefineFont) to a
    device font. It provides a font name and style to pass to the playback platform's text engine,
    and a table of character codes that identifies the character represented by each glyph in the
    corresponding DefineFont tag, allowing the glyph indices of a DefineText tag to be converted
    to character strings.
    The presence of a DefineFontInfo tag does not force a glyph font to become a device font; it
    merely makes the option available. The actual choice between glyph and device usage is made
    according to the value of devicefont (see the introduction) or the value of UseOutlines in a
    DefineEditText tag. If a device font is unavailable on a playback platform, Flash Player will
    fall back to glyph text.
    """
    TYPE = 13
    def __init__(self):
        super(TagDefineFontInfo, self).__init__()

    @property
    def name(self):
        return "DefineFontInfo"

    @property
    def type(self):
        return TagDefineFontInfo.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 1

    @property
    def unitDivisor(self):
        return 1

    def parse(self, data, length, version=1):
        self.codeTable = []

        self.characterId = data.readUI16()

        fontNameLen = data.readUI8()
        fontNameRaw = StringIO.StringIO()
        fontNameRaw.write(data.f.read(fontNameLen))
        fontNameRaw.seek(0)

        self.fontName = fontNameRaw.read()

        flags = data.readUI8()

        self.smallText = ((flags & 0x20) != 0)
        self.shiftJIS = ((flags & 0x10) != 0)
        self.ansi  = ((flags & 0x08) != 0)
        self.italic = ((flags & 0x04) != 0)
        self.bold = ((flags & 0x02) != 0)
        self.wideCodes = ((flags & 0x01) != 0)

        if self.wideCodes:
            numGlyphs = (length - 2 - 1 - fontNameLen - 1) / 2
        else:
            numGlyphs = length - 2 - 1 - fontNameLen - 1

        for i in range(0, numGlyphs):
            self.codeTable.append(data.readUI16() if self.wideCodes else data.readUI8())

class TagDefineBitsLossless(DefinitionTag):
    """
    Defines a lossless bitmap character that contains RGB bitmap data compressed
    with ZLIB. The data format used by the ZLIB library is described by
    Request for Comments (RFCs) documents 1950 to 1952.
    Two kinds of bitmaps are supported. Colormapped images define a colormap of
    up to 256 colors, each represented by a 24-bit RGB value, and then use
    8-bit pixel values to index into the colormap. Direct images store actual
    pixel color values using 15 bits (32,768 colors) or 24 bits (about 17 million colors).
    The minimum file format version for this tag is SWF 2.
    """
    TYPE = 20
    bitmapData = None
    image_buffer = ""
    bitmap_format = 0
    bitmap_width = 0
    bitmap_height = 0
    bitmap_color_size = 0
    zlib_bitmap_data = None
    padded_width = 0
    def __init__(self):
        super(TagDefineBitsLossless, self).__init__()

    def parse(self, data, length, version=1):
        import zlib
        self.image_buffer = ""
        self.characterId = data.readUI16()
        self.bitmap_format = data.readUI8()
        self.bitmap_width = data.readUI16()
        self.bitmap_height = data.readUI16()
        if self.bitmap_format == BitmapFormat.BIT_8:
            self.bitmap_color_size = data.readUI8()
            self.zlib_bitmap_data = data.f.read(length-8)
        else:
            self.zlib_bitmap_data = data.f.read(length-7)

        # decompress zlib encoded bytes
        compressed_length = len(self.zlib_bitmap_data)
        zip = zlib.decompressobj()
        temp = StringIO.StringIO()
        temp.write(zip.decompress(self.zlib_bitmap_data))
        temp.seek(0, 2)
        uncompressed_length = temp.tell()
        temp.seek(0)

        # padding : should be aligned to 32 bit boundary
        self.padded_width = self.bitmap_width
        while self.padded_width % 4 != 0:
            self.padded_width += 1
        t = self.padded_width * self.bitmap_height

        is_lossless2 = (type(self) == TagDefineBitsLossless2)
        im = None
        self.bitmapData = StringIO.StringIO()

        indexed_colors = []
        if self.bitmap_format == BitmapFormat.BIT_8:
            for i in range(0, self.bitmap_color_size + 1):
                r = ord(temp.read(1))
                g = ord(temp.read(1))
                b = ord(temp.read(1))
                a = ord(temp.read(1)) if is_lossless2 else 0xff
                indexed_colors.append(struct.pack("BBBB", r, g, b, a))

            # create the image buffer
            s = StringIO.StringIO()
            for i in xrange(t):
                s.write(indexed_colors[ord(temp.read(1))])
            self.image_buffer = s.getvalue()
            s.close()

            im = Image.fromstring("RGBA", (self.padded_width, self.bitmap_height), self.image_buffer)
            im = im.crop((0, 0, self.bitmap_width, self.bitmap_height))

        elif self.bitmap_format == BitmapFormat.BIT_15:
            raise Exception("DefineBitsLossless: BIT_15 not yet implemented")
        elif self.bitmap_format == BitmapFormat.BIT_24:
            t = self.bitmap_width * self.bitmap_height if is_lossless2 else t
            # read PIX24's
            for i in range(0, t):
                if not is_lossless2:
                    temp.read(1) # reserved, always 0
                a = ord(temp.read(1)) if is_lossless2 else 0xff
                r = ord(temp.read(1))
                g = ord(temp.read(1))
                b = ord(temp.read(1))
                self.image_buffer += struct.pack("BBBB", r, g, b, a)
            if is_lossless2:
                im = Image.fromstring("RGBA", (self.bitmap_width, self.bitmap_height), self.image_buffer)
            else:
                im = Image.fromstring("RGBA", (self.padded_width, self.bitmap_height), self.image_buffer)
        else:
            raise Exception("unhandled bitmap format! %s %d" % (BitmapFormat.tostring(self.bitmap_format), self.bitmap_format))

        if not im is None:
            im.save(self.bitmapData, "PNG")
            self.bitmapData.seek(0)

    @property
    def name(self):
        return "DefineBitsLossless"

    @property
    def type(self):
        return TagDefineBitsLossless.TYPE

class TagDefineBitsJPEG2(TagDefineBits):
    """
    This tag defines a bitmap character with JPEG compression. It differs from
    DefineBits in that it contains both the JPEG encoding table and the JPEG
    image data. This tag allows multiple JPEG images with differing encoding
    tables to be defined within a single SWF file.
    The data in this tag begins with the JPEG SOI marker 0xFF, 0xD8 and ends
    with the EOI marker 0xFF, 0xD9. Before version 8 of the SWF file format,
    SWF files could contain an erroneous header of 0xFF, 0xD9, 0xFF, 0xD8
    before the JPEG SOI marker.
    In addition to specifying JPEG data, DefineBitsJPEG2 can also contain PNG
    image data and non-animated GIF89a image data.

    - If ImageData begins with the eight bytes 0x89 0x50 0x4E 0x47 0x0D 0x0A 0x1A 0x0A,
      the ImageData contains PNG data.
    - If ImageData begins with the six bytes 0x47 0x49 0x46 0x38 0x39 0x61, the ImageData
      contains GIF89a data.

    The minimum file format version for this tag is SWF 2. The minimum file format
    version for embedding PNG of GIF89a data is SWF 8.
    """
    TYPE = 21
    bitmapType = 0

    def __init__(self):
        super(TagDefineBitsJPEG2, self).__init__()

    @property
    def name(self):
        return "DefineBitsJPEG2"

    @property
    def type(self):
        return TagDefineBitsJPEG2.TYPE

    @property
    def version(self):
        return 2 if self.bitmapType == BitmapType.JPEG else 8

    @property
    def level(self):
        return 2

    def parse(self, data, length, version=1):
        super(TagDefineBitsJPEG2, self).parse(data, length, version)
        self.bitmapType = ImageUtils.get_image_type(self.bitmapData)

class TagDefineShape2(TagDefineShape):
    """
    DefineShape2 extends the capabilities of DefineShape with the ability
    to support more than 255 styles in the style list and multiple style
    lists in a single shape.
    The minimum file format version is SWF 2.
    """
    TYPE = 22

    def __init__(self):
        super(TagDefineShape2, self).__init__()

    @property
    def name(self):
        return "DefineShape2"

    @property
    def type(self):
        return TagDefineShape2.TYPE

    @property
    def level(self):
        return 2

    @property
    def version(self):
        return 2

class TagPlaceObject2(TagPlaceObject):
    """
    The PlaceObject2 tag extends the functionality of the PlaceObject tag.
    The PlaceObject2 tag can both add a character to the display list, and
    modify the attributes of a character that is already on the display list.
    The PlaceObject2 tag changed slightly from SWF 4 to SWF 5. In SWF 5,
    clip actions were added.
    The tag begins with a group of flags that indicate which fields are
    present in the tag. The optional fields are CharacterId, Matrix,
    ColorTransform, Ratio, ClipDepth, Name, and ClipActions.
    The Depth field is the only field that is always required.
    The depth value determines the stacking order of the character.
    Characters with lower depth values are displayed underneath characters
    with higher depth values. A depth value of 1 means the character is
    displayed at the bottom of the stack. Any given depth can have only one
    character. This means a character that is already on the display list can
    be identified by its depth alone (that is, a CharacterId is not required).
    The PlaceFlagMove and PlaceFlagHasCharacter tags indicate whether a new
    character is being added to the display list, or a character already on the
    display list is being modified. The meaning of the flags is as follows:

    - PlaceFlagMove = 0 and PlaceFlagHasCharacter = 1 A new character
      (with ID of CharacterId) is placed on the display list at the specified
      depth. Other fields set the attributes of this new character.
    - PlaceFlagMove = 1 and PlaceFlagHasCharacter = 0
      The character at the specified depth is modified. Other fields modify the
      attributes of this character. Because any given depth can have only one
      character, no CharacterId is required.
    - PlaceFlagMove = 1 and PlaceFlagHasCharacter = 1
      The character at the specified Depth is removed, and a new character
      (with ID of CharacterId) is placed at that depth. Other fields set the
      attributes of this new character.
      For example, a character that is moved over a series of frames has
      PlaceFlagHasCharacter set in the first frame, and PlaceFlagMove set in
      subsequent frames. The first frame places the new character at the desired
      depth, and sets the initial transformation matrix. Subsequent frames replace
      the transformation matrix of the character at the desired depth.

    The optional fields in PlaceObject2 have the following meaning:
    - The CharacterId field specifies the character to be added to the display list.
      CharacterId is used only when a new character is being added. If a character
      that is already on the display list is being modified, the CharacterId field is absent.
    - The Matrix field specifies the position, scale and rotation of the character
      being added or modified.
    - The ColorTransform field specifies the color effect applied to the character
      being added or modified.
    - The Ratio field specifies a morph ratio for the character being added or modified.
      This field applies only to characters defined with DefineMorphShape, and controls
      how far the morph has progressed. A ratio of zero displays the character at the start
      of the morph. A ratio of 65535 displays the character at the end of the morph.
      For values between zero and 65535 Flash Player interpolates between the start and end
      shapes, and displays an in- between shape.
    - The ClipDepth field specifies the top-most depth that will be masked by the character
      being added. A ClipDepth of zero indicates that this is not a clipping character.
    - The Name field specifies a name for the character being added or modified. This field
      is typically used with sprite characters, and is used to identify the sprite for
      SetTarget actions. It allows the main file (or other sprites) to perform actions
      inside the sprite (see 'Sprites and Movie Clips' on page 231).
    - The ClipActions field, which is valid only for placing sprite characters, defines
      one or more event handlers to be invoked when certain events occur.
    """
    TYPE = 26
    def __init__(self):
        super(TagPlaceObject2, self).__init__()

    def parse(self, data, length, version=1):
        flags = data.readUI8()
        self.hasClipActions = (flags & 0x80) != 0
        self.hasClipDepth = (flags & 0x40) != 0
        self.hasName = (flags & 0x20) != 0
        self.hasRatio = (flags & 0x10) != 0
        self.hasColorTransform = (flags & 0x08) != 0
        self.hasMatrix = (flags & 0x04) != 0
        self.hasCharacter = (flags & 0x02) != 0
        self.hasMove = (flags & 0x01) != 0
        self.depth = data.readUI16()
        if self.hasCharacter:
            self.characterId = data.readUI16()
        if self.hasMatrix:
            self.matrix = data.readMATRIX()
        if self.hasColorTransform:
            self.colorTransform = data.readCXFORMWITHALPHA()
        if self.hasRatio:
            self.ratio = data.readUI16()
        if self.hasName:
            self.instanceName = data.readString()
        if self.hasClipDepth:
            self.clipDepth = data.readUI16()
        if self.hasClipActions:
            self.clipActions = data.readCLIPACTIONS(version);
            #raise Exception("PlaceObject2: ClipActions not yet implemented!")

    @property
    def name(self):
        return "PlaceObject2"

    @property
    def type(self):
        return TagPlaceObject2.TYPE

    @property
    def level(self):
        return 2

    @property
    def version(self):
        return 3

class TagRemoveObject2(TagRemoveObject):
    """
    The RemoveObject2 tag removes the character at the specified depth
    from the display list.
    The minimum file format version is SWF 3.
    """
    TYPE = 28

    def __init__(self):
        super(TagRemoveObject2, self).__init__()

    @property
    def name(self):
        return "RemoveObject2"

    @property
    def type(self):
        return TagRemoveObject2.TYPE

    @property
    def level(self):
        return 2

    @property
    def version(self):
        return 3

    def parse(self, data, length, version=1):
        self.depth = data.readUI16()

class TagDefineShape3(TagDefineShape2):
    """
    DefineShape3 extends the capabilities of DefineShape2 by extending
    all of the RGB color fields to support RGBA with opacity information.
    The minimum file format version is SWF 3.
    """
    TYPE = 32
    def __init__(self):
        super(TagDefineShape3, self).__init__()

    @property
    def name(self):
        return "DefineShape3"

    @property
    def type(self):
        return TagDefineShape3.TYPE

    @property
    def level(self):
        return 3

    @property
    def version(self):
        return 3

class TagDefineText2(TagDefineText):
    """
    The DefineText tag defines a block of static text. It describes the font,
    size, color, and exact position of every character in the text object.
    The minimum file format version is SWF 3.
    """
    TYPE = 33
    def __init__(self):
        super(TagDefineText2, self).__init__()

    @property
    def name(self):
        return "DefineText2"

    @property
    def type(self):
        return TagDefineText2.TYPE

    @property
    def level(self):
        return 2

    @property
    def version(self):
        return 3

class TagDefineBitsJPEG3(TagDefineBitsJPEG2):
    """
    This tag defines a bitmap character with JPEG compression. This tag
    extends DefineBitsJPEG2, adding alpha channel (opacity) data.
    Opacity/transparency information is not a standard feature in JPEG images,
    so the alpha channel information is encoded separately from the JPEG data,
    and compressed using the ZLIB standard for compression. The data format
    used by the ZLIB library is described by Request for Comments (RFCs)
    documents 1950 to 1952.
    The data in this tag begins with the JPEG SOI marker 0xFF, 0xD8 and ends
    with the EOI marker 0xFF, 0xD9. Before version 8 of the SWF file format,
    SWF files could contain an erroneous header of 0xFF, 0xD9, 0xFF, 0xD8
    before the JPEG SOI marker.
    In addition to specifying JPEG data, DefineBitsJPEG2 can also contain
    PNG image data and non-animated GIF89a image data.
    - If ImageData begins with the eight bytes 0x89 0x50 0x4E 0x47 0x0D 0x0A 0x1A 0x0A,
      the ImageData contains PNG data.
    - If ImageData begins with the six bytes 0x47 0x49 0x46 0x38 0x39 0x61,
      the ImageData contains GIF89a data.
    If ImageData contains PNG or GIF89a data, the optional BitmapAlphaData is
    not supported.
    The minimum file format version for this tag is SWF 3. The minimum file
    format version for embedding PNG of GIF89a data is SWF 8.
    """
    TYPE = 35
    def __init__(self):
        self.bitmapAlphaData = StringIO.StringIO()
        super(TagDefineBitsJPEG3, self).__init__()

    @property
    def name(self):
        return "DefineBitsJPEG3"

    @property
    def type(self):
        return TagDefineBitsJPEG3.TYPE

    @property
    def version(self):
        return 3 if self.bitmapType == BitmapType.JPEG else 8

    @property
    def level(self):
        return 3

    def parse(self, data, length, version=1):
        import zlib
        self.characterId = data.readUI16()
        alphaOffset = data.readUI32()
        self.bitmapAlphaData = StringIO.StringIO()
        self.bitmapData = StringIO.StringIO()
        self.bitmapData.write(data.f.read(alphaOffset))
        self.bitmapData.seek(0)
        self.bitmapType = ImageUtils.get_image_type(self.bitmapData)
        alphaDataSize = length - alphaOffset - 6
        if alphaDataSize > 0:
            self.bitmapAlphaData.write(data.f.read(alphaDataSize))
            self.bitmapAlphaData.seek(0)
            # decompress zlib encoded bytes
            zip = zlib.decompressobj()
            temp = StringIO.StringIO()
            temp.write(zip.decompress(self.bitmapAlphaData.read()))
            temp.seek(0)
            self.bitmapAlphaData = temp

class TagDefineBitsLossless2(TagDefineBitsLossless):
    """
    DefineBitsLossless2 extends DefineBitsLossless with support for
    opacity (alpha values). The colormap colors in colormapped images
    are defined using RGBA values, and direct images store 32-bit
    ARGB colors for each pixel. The intermediate 15-bit color depth
    is not available in DefineBitsLossless2.
    The minimum file format version for this tag is SWF 3.
    """
    TYPE = 36
    def __init__(self):
        super(TagDefineBitsLossless2, self).__init__()

    @property
    def name(self):
        return "DefineBitsLossless2"

    @property
    def type(self):
        return TagDefineBitsLossless2.TYPE

    @property
    def level(self):
        return 2

    @property
    def version(self):
        return 3

class TagDefineSprite(SWFTimelineContainer):
    """
    The DefineSprite tag defines a sprite character. It consists of
    a character ID and a frame count, followed by a series of control
    tags. The sprite is terminated with an End tag.
    The length specified in the Header reflects the length of the
    entire DefineSprite tag, including the ControlTags field.
    Definition tags (such as DefineShape) are not allowed in the
    DefineSprite tag. All of the characters that control tags refer to
    in the sprite must be defined in the main body of the file before
    the sprite is defined.
    The minimum file format version is SWF 3.
    """
    TYPE = 39
    frameCount = 0
    def __init__(self):
        super(TagDefineSprite, self).__init__()

    def parse(self, data, length, version=1):
        self.characterId = data.readUI16()
        self.frameCount = data.readUI16()
        self.parse_tags(data, version)

    @property
    def name(self):
        return "DefineSprite"

    @property
    def type(self):
        return TagDefineSprite.TYPE

    def __str__(self):
        s = super(TagDefineSprite, self).__str__() + " " + \
            "ID: %d" % self.characterId
        return s

class TagFrameLabel(Tag):
    """
    The FrameLabel tag gives the specified Name to the current frame.
    ActionGoToLabel uses this name to identify the frame.
    The minimum file format version is SWF 3.
    """
    TYPE = 43
    frameName = ""
    namedAnchorFlag = False
    def __init__(self):
        super(TagFrameLabel, self).__init__()

    @property
    def name(self):
        return "FrameLabel"

    @property
    def type(self):
        return TagFrameLabel.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 3

    def parse(self, data, length, version=1):
        start = data.tell()
        self.frameName = data.readString()
        if (data.tell() - start) < length:
            data.readUI8() # Named anchor flag, always 1
            self.namedAnchorFlag = True

class TagDefineMorphShape(DefinitionTag):
    """
    The DefineMorphShape tag defines the start and end states of a morph
    sequence. A morph object should be displayed with the PlaceObject2 tag,
    where the ratio field specifies how far the morph has progressed.
    The minimum file format version is SWF 3.
    """
    TYPE = 46
    def __init__(self):
        self._morphFillStyles = []
        self._morphLineStyles = []
        super(TagDefineMorphShape, self).__init__()

    @property
    def name(self):
        return "DefineMorphShape"

    @property
    def type(self):
        return TagDefineMorphShape.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 3

    @property
    def morph_fill_styles(self):
        """ Return list of SWFMorphFillStyle """
        return self._morphFillStyles

    @property
    def morph_line_styles(self):
        """ Return list of SWFMorphLineStyle """
        return self._morphLineStyles

    def parse(self, data, length, version=1):
        self._morphFillStyles = []
        self._morphLineStyles = []
        self.characterId = data.readUI16()
        self.startBounds = data.readRECT()
        self.endBounds = data.readRECT()
        offset = data.readUI32()
        # MorphFillStyleArray
        fillStyleCount = data.readUI8()
        if fillStyleCount == 0xff:
            fillStyleCount = data.readUI16()
        for i in range(0, fillStyleCount):
            self._morphFillStyles.append(data.readMORPHFILLSTYLE())

        # MorphLineStyleArray
        lineStyleCount = data.readUI8()
        if lineStyleCount == 0xff:
            lineStyleCount = data.readUI16()
        for i in range(0, lineStyleCount):
            self._morphLineStyles.append(data.readMORPHLINESTYLE());

        self.startEdges = data.readSHAPE();
        self.endEdges = data.readSHAPE();

class TagDefineFont2(TagDefineFont):
    TYPE= 48
    def __init__(self):
        self.glyphShapeTable = []
        super(TagDefineFont2, self).__init__()

    @property
    def name(self):
        return "DefineFont2"

    @property
    def type(self):
        return TagDefineFont2.TYPE

    @property
    def level(self):
        return 2

    @property
    def version(self):
        return 3

    @property
    def unitDivisor(self):
        return 20

    def parse(self, data, length, version=1):
        self.glyphShapeTable = []
        self.codeTable = []
        self.fontAdvanceTable = []
        self.fontBoundsTable = []
        self.fontKerningTable = []

        self.characterId = data.readUI16()

        flags = data.readUI8()

        self.hasLayout = ((flags & 0x80) != 0)
        self.shiftJIS = ((flags & 0x40) != 0)
        self.smallText = ((flags & 0x20) != 0)
        self.ansi = ((flags & 0x10) != 0)
        self.wideOffsets = ((flags & 0x08) != 0)
        self.wideCodes = ((flags & 0x04) != 0)
        self.italic = ((flags & 0x02) != 0)
        self.bold = ((flags & 0x01) != 0)
        self.languageCode = data.readLANGCODE()

        fontNameLen = data.readUI8()
        fontNameRaw = StringIO.StringIO()
        fontNameRaw.write(data.f.read(fontNameLen))
        fontNameRaw.seek(0)
        self.fontName = fontNameRaw.read()

        numGlyphs = data.readUI16()
        numSkip = 2 if self.wideOffsets else 1
        # Skip offsets. We don't need them.
        data.skip_bytes(numGlyphs << numSkip)

        codeTableOffset = data.readUI32() if self.wideOffsets else data.readUI16()
        for i in range(0, numGlyphs):
            self.glyphShapeTable.append(data.readSHAPE(self.unitDivisor))
        for i in range(0, numGlyphs):
            self.codeTable.append(data.readUI16() if self.wideCodes else data.readUI8())

        if self.hasLayout:
            self.ascent = data.readSI16()
            self.descent = data.readSI16()
            self.leading = data.readSI16()
            for i in range(0, numGlyphs):
                self.fontAdvanceTable.append(data.readSI16())
            for i in range(0, numGlyphs):
                self.fontBoundsTable.append(data.readRECT())
            kerningCount = data.readUI16()
            for i in range(0, kerningCount):
                self.fontKerningTable.append(data.readKERNINGRECORD(self.wideCodes))

class TagFileAttributes(Tag):
    """
    The FileAttributes tag defines characteristics of the SWF file. This tag
    is required for SWF 8 and later and must be the first tag in the SWF file.
    Additionally, the FileAttributes tag can optionally be included in all SWF
    file versions.
    The HasMetadata flag identifies whether the SWF file contains the Metadata
    tag. Flash Player does not care about this bit field or the related tag but
    it is useful for search engines.
    The UseNetwork flag signifies whether Flash Player should grant the SWF file
    local or network file access if the SWF file is loaded locally. The default
    behavior is to allow local SWF files to interact with local files only, and
    not with the network. However, by setting the UseNetwork flag, the local SWF
    can forfeit its local file system access in exchange for access to the
    network. Any version of SWF can use the UseNetwork flag to set the file
    access for locally loaded SWF files that are running in Flash Player 8 or later.
    """
    TYPE = 69
    def __init__(self):
        super(TagFileAttributes, self).__init__()

    @property
    def name(self):
        return "FileAttributes"

    @property
    def type(self):
        return TagFileAttributes.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 8

    def parse(self, data, length, version=1):
        flags = data.readUI8()
        self.useDirectBlit = ((flags & 0x40) != 0)
        self.useGPU = ((flags & 0x20) != 0)
        self.hasMetadata = ((flags & 0x10) != 0)
        self.actionscript3 = ((flags & 0x08) != 0)
        self.useNetwork = ((flags & 0x01) != 0)
        data.skip_bytes(3)

    def __str__(self):
        s = super(TagFileAttributes, self).__str__() + \
            " useDirectBlit: %d, " % self.useDirectBlit + \
            "useGPU: %d, " % self.useGPU + \
            "hasMetadata: %d, " % self.hasMetadata + \
            "actionscript3: %d, " % self.actionscript3 + \
            "useNetwork: %d" % self.useNetwork
        return s

class TagPlaceObject3(TagPlaceObject2):
    TYPE = 70
    def __init__(self):
        super(TagPlaceObject3, self).__init__()

    def parse(self, data, length, version=1):
        flags = data.readUI8()
        self.hasClipActions = ((flags & 0x80) != 0)
        self.hasClipDepth = ((flags & 0x40) != 0)
        self.hasName = ((flags & 0x20) != 0)
        self.hasRatio = ((flags & 0x10) != 0)
        self.hasColorTransform = ((flags & 0x08) != 0)
        self.hasMatrix = ((flags & 0x04) != 0)
        self.hasCharacter = ((flags & 0x02) != 0)
        self.hasMove = ((flags & 0x01) != 0)
        flags2 = data.readUI8();
        self.hasImage = ((flags2 & 0x10) != 0)
        self.hasClassName = ((flags2 & 0x08) != 0)
        self.hasCacheAsBitmap = ((flags2 & 0x04) != 0)
        self.hasBlendMode = ((flags2 & 0x2) != 0)
        self.hasFilterList = ((flags2 & 0x1) != 0)
        self.depth = data.readUI16()

        if self.hasClassName:
            self.className = data.readString()
        if self.hasCharacter:
            self.characterId = data.readUI16()
        if self.hasMatrix:
            self.matrix = data.readMATRIX()
        if self.hasColorTransform:
            self.colorTransform = data.readCXFORMWITHALPHA()
        if self.hasRatio:
            self.ratio = data.readUI16()
        if self.hasName:
            self.instanceName = data.readString()
        if self.hasClipDepth:
            self.clipDepth = data.readUI16();
        if self.hasFilterList:
            numberOfFilters = data.readUI8()
            for i in range(0, numberOfFilters):
                self._surfaceFilterList.append(data.readFILTER())
        if self.hasBlendMode:
            self.blendMode = data.readUI8()
        if self.hasCacheAsBitmap:
            self.bitmapCache = data.readUI8()
        if self.hasClipActions:
            self.clipActions = data.readCLIPACTIONS(version)
            #raise Exception("PlaceObject3: ClipActions not yet implemented!")

    @property
    def name(self):
        return "PlaceObject3"

    @property
    def type(self):
        return TagPlaceObject3.TYPE

class TagDefineFontAlignZones(Tag):
    TYPE = 73
    def __init__(self):
        super(TagDefineFontAlignZones, self).__init__()

    @property
    def name(self):
        return "DefineFontAlignZones"

    @property
    def type(self):
        return TagDefineFontAlignZones.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 8

    def parse(self, data, length, version=1):
        self.zoneTable = []

        self.fontId = data.readUI16()
        self.csmTableHint = (data.readUI8() >> 6)

        recordsEndPos = data.tell() + length - 3;
        while data.tell() < recordsEndPos:
            self.zoneTable.append(data.readZONERECORD())

class TagCSMTextSettings(Tag):
    TYPE = 74
    def __init__(self):
        super(TagCSMTextSettings, self).__init__()

    @property
    def name(self):
        return "CSMTextSettings"

    @property
    def type(self):
        return TagCSMTextSettings.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 8

    def parse(self, data, length, version=1):
        self.textId = data.readUI16()
        self.useFlashType = data.readUB(2)
        self.gridFit = data.readUB(3);
        data.readUB(3) # reserved, always 0
        self.thickness = data.readFIXED()
        self.sharpness = data.readFIXED()
        data.readUI8() # reserved, always 0

class TagDefineFont3(TagDefineFont2):
    TYPE = 75
    def __init__(self):
        super(TagDefineFont3, self).__init__()

    @property
    def name(self):
        return "DefineFont3"

    @property
    def type(self):
        return TagDefineFont3.TYPE

    @property
    def level(self):
        return 2

    @property
    def version(self):
        return 8

class TagSymbolClass(Tag):
    TYPE = 76
    def __init__(self):
        self.symbols = []
        super(TagSymbolClass, self).__init__()

    @property
    def name(self):
        return "SymbolClass"

    @property
    def type(self):
        return TagSymbolClass.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 9 # educated guess (not specified in SWF10 spec)

    def parse(self, data, length, version=1):
        self.symbols = []
        numSymbols = data.readUI16()
        for i in range(0, numSymbols):
            self.symbols.append(data.readSYMBOL())

class TagMetadata(Tag):
    TYPE = 77
    def __init__(self):
        super(TagMetadata, self).__init__()

    @property
    def name(self):
        return "Metadata"

    @property
    def type(self):
        return TagMetadata.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 1

    def parse(self, data, length, version=1):
        self.xmlString = data.readString()

class TagDoABC(Tag):
    TYPE = 82
    def __init__(self):
        super(TagDoABC, self).__init__()

    @property
    def name(self):
        return "DoABC"

    @property
    def type(self):
        return TagDoABC.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 9

    def parse(self, data, length, version=1):
        pos = data.tell()
        flags = data.readUI32()
        self.lazyInitializeFlag = ((flags & 0x01) != 0)
        self.abcName = data.readString()
        self.bytes = data.f.read(length - (data.tell() - pos))

class TagDefineShape4(TagDefineShape3):
    TYPE = 83
    def __init__(self):
        super(TagDefineShape4, self).__init__()

    @property
    def name(self):
        return "DefineShape4"

    @property
    def type(self):
        return TagDefineShape4.TYPE

    @property
    def level(self):
        return 4

    @property
    def version(self):
        return 8

    def parse(self, data, length, version=1):
        self.characterId = data.readUI16()
        self._shape_bounds = data.readRECT()
        self.edge_bounds = data.readRECT()
        flags = data.readUI8()
        self.uses_fillwinding_rule = ((flags & 0x04) != 0)
        self.uses_non_scaling_strokes = ((flags & 0x02) != 0)
        self.uses_scaling_strokes = ((flags & 0x01) != 0)
        self._shapes = data.readSHAPEWITHSTYLE(self.level)

class TagDefineSceneAndFrameLabelData(Tag):
    TYPE = 86
    def __init__(self):
        self.scenes = []
        self.frameLabels = []
        super(TagDefineSceneAndFrameLabelData, self).__init__()

    @property
    def name(self):
        return "DefineSceneAndFrameLabelData"

    @property
    def type(self):
        return TagDefineSceneAndFrameLabelData.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 9

    def parse(self, data, length, version=1):
        self.sceneCount = data.readEncodedU32()

        if self.sceneCount >= 0x80000000:
            print "WARNING: Negative sceneCount value: %x found!. SWF file exploiting CVE-2007-0071?" % self.sceneCount
            return

        self.scenes = []
        self.frameLabels = []
        for i in range(0, self.sceneCount):
            sceneOffset = data.readEncodedU32()
            sceneName = data.readString()
            self.scenes.append(SWFScene(sceneOffset, sceneName))

        frameLabelCount = data.readEncodedU32()
        for i in range(0, frameLabelCount):
            frameNumber = data.readEncodedU32();
            frameLabel = data.readString();
            self.frameLabels.append(SWFFrameLabel(frameNumber, frameLabel))

class TagDefineFontName(Tag):
    TYPE = 88
    def __init__(self):
        super(TagDefineFontName, self).__init__()

    @property
    def name(self):
        return "DefineFontName"

    @property
    def type(self):
        return TagDefineFontName.TYPE

    @property
    def level(self):
        return 1

    @property
    def version(self):
        return 9

    def parse(self, data, length, version=1):
        self.fontId = data.readUI16()
        self.fontName = data.readString()
        self.fontCopyright = data.readString()



########NEW FILE########
__FILENAME__ = utils
from consts import BitmapType
import math

class NumberUtils(object):
    @classmethod
    def round_pixels_20(cls, pixels):
        return round(pixels * 100) / 100
    @classmethod
    def round_pixels_400(cls, pixels):
        return round(pixels * 10000) / 10000
 
class ColorUtils(object):
    @classmethod
    def alpha(cls, color):
        return int(color >> 24) / 255.0
    
    @classmethod
    def rgb(cls, color):
        return (color & 0xffffff)
    
    @classmethod
    def to_rgb_string(cls, color):
        c = "%x" % color
        while len(c) < 6: c = "0" + c
        return "#"+c
        
class ImageUtils(object):
    @classmethod
    def get_image_size(cls, data):
        pass
        
    @classmethod
    def get_image_type(cls, data):
        pos = data.tell()
        image_type = 0
        data.seek(0, 2) # moves file pointer to final position
        if data.tell() > 8:
            data.seek(0)
            b0 = ord(data.read(1))
            b1 = ord(data.read(1))
            b2 = ord(data.read(1))
            b3 = ord(data.read(1))
            b4 = ord(data.read(1))
            b5 = ord(data.read(1))
            b6 = ord(data.read(1))
            b7 = ord(data.read(1))
            if b0 == 0xff and (b1 == 0xd8 or 1 == 0xd9):
                image_type = BitmapType.JPEG
            elif b0 == 0x89 and b1 == 0x50 and b2 == 0x4e and b3 == 0x47 and \
                b4 == 0x0d and b5 == 0x0a and b6 == 0x1a and b7 == 0x0a:
                image_type = BitmapType.PNG
            elif b0 == 0x47 and b1 == 0x49 and b2 == 0x46 and b3 == 0x38 and b4 == 0x39 and b5 == 0x61:
                image_type = BitmapType.GIF89A
        data.seek(pos)
        return image_type
########NEW FILE########
