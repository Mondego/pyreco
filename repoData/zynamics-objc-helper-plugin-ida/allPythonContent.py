__FILENAME__ = fixObjectiveCx86
import idaapi, idc, idautils
import re
import time

var_re = re.compile(', \[es?b?p.*[\+-](?P<varname>\w+)\]')


def track_param(ea, min_ea, op_type, op_val):
  '''
  trace_param: ea, min_ea, op_type, op_val

  Taking ea as start, this function does basic backtrace of
  an operand (defined by op_type and op_val) until it finds
  a data reference which we consider the "source". It stops
  when ea < min_ea (usually the function start).

  It does not support arithmetic or complex modifications of
  the source. This will be improved on future versions.
  '''
  global msgsend, var_re

  ea_call = ea
  while ea != idc.BADADDR and ea != min_ea:
    ea = idc.PrevHead(ea, min_ea)

    if idc.GetMnem(ea) not in ['lea', 'mov']:
      continue

    if idc.GetOpType(ea, 0) == op_type and idc.GetOperandValue(ea, 0) == op_val:
      if idc.GetOpType(ea, 1) == idc.o_displ:
        if ', [esp' in idc.GetDisasm(ea) or ', [ebp' in idc.GetDisasm(ea):
          if 'arg_' in idc.GetDisasm(ea):
          # We don't track function arguments
            return None

          # We only track stack variables
          try:
            var_name = var_re.search(idc.GetDisasm(ea)).group('varname')
            op_type = idc.GetOpType(ea, 1)
          except:
            print '%08x: Unable to recognize variable' % ea
            return None

          while ea != idc.BADADDR and ea > min_ea:
            if idc.GetMnem(ea) == 'mov' or idc.GetMnem(ea) == 'lea' and var_name in idc.GetDisasm(ea):
              # New reg to track
              op_val = idc.GetOperandValue(ea, 0)
              break
            ea = idc.PrevHead(ea, min_ea)

      elif idc.GetOpType(ea, 1) == idc.o_mem:
        # Got the final reference
        refs = list(idautils.DataRefsFrom(ea))
        if not refs:
          local_ref = idc.GetOperandValue(ea, 1)
          far_ref = idc.Dword(local_ref)
        else:
          while len(refs) > 0:
            far_ref = refs[0]
            refs = list(idautils.DataRefsFrom(refs[0]))
        return far_ref

      elif idc.GetOpType(ea, 1) == idc.o_reg:
        # Direct reg-reg assignment
        op_val = idc.GetOperandValue(ea, 1)
        op_type =  idc.GetOpType(ea, 1)
      else:
        # We don't track o_phrase or other complex source operands :(
        return None

  return None



def fix_callgraph(msgsend, segname, class_param, sel_param):
  '''
  fix_callgraph: msgsend, segname, class_param, sel_param

  Given the msgsend flavour address as a parameter, looks
  for the parameters (class and selector, identified by
  class_param and sel_param) and creates a new segment where
  it places a set of dummy calls named as classname_methodname
  (we use method instead of selector most of the time).
  '''

  t1 = time.time()
  if not msgsend:
    print 'ERROR: msgSend not found'
    return

  total = 0
  resolved = 0
  call_table = dict()


  for xref in idautils.XrefsTo(msgsend, idaapi.XREF_ALL):
    total += 1
    ea_call = xref.frm
    func_start = idc.GetFunctionAttr(ea_call, idc.FUNCATTR_START)
    if not func_start or func_start == idc.BADADDR:
      continue
    ea = ea_call

    method_name_ea = track_param(ea, func_start, idc.o_displ, sel_param)
    if method_name_ea:
      method_name = idc.GetString(method_name_ea, -1, idc.ASCSTR_C)
      if not method_name:
        method_name = ''
    else:
      method_name = ''

    class_name_ea = track_param(ea, func_start, idc.o_phrase, class_param)
    if class_name_ea:
      class_name = idc.GetString(class_name_ea, -1, idc.ASCSTR_C)
      if not class_name:
        class_name = ''
    else:
      class_name = ''

    if not method_name and not class_name:
      continue

    # Using this name convention, if the class and method
    # are identified by IDA, the patched call will point to
    # the REAL call and not one of our dummy functions
    #
    class_name = class_name.replace('_objc_class_name_', '')

    new_name = '_[' + class_name + '_' + method_name + ']'
    call_table[ea_call] = new_name
    resolved += 1

  print '\nFinal stats:\n\t%d total calls, %d resolved' % (total, resolved)
  print '\tAnalysis took %.2f seconds' % (time.time() - t1)

  if resolved == 0:
    print 'Nothing to patch.'
    return

  print 'Adding new segment to store new nullsubs'

  # segment size = opcode ret (4 bytes) * num_calls
  seg_size = resolved * 4
  seg_start = idc.MaxEA() + 4
  idaapi.add_segm(0, seg_start, seg_start + seg_size, segname, 'CODE')

  print 'Patching database...'
  seg_ptr = seg_start
  for ea, new_name in call_table.items():
    if idc.LocByName(new_name) != idc.BADADDR:
      offset = (idc.LocByName(new_name) - ea) & idc.BADADDR
    else:
      # create code and name it
      idc.PatchDword(seg_ptr, 0x90) # nop
      idc.MakeName(seg_ptr, new_name)
      idc.MakeCode(seg_ptr)
      idc.MakeFunction(seg_ptr, seg_ptr + 4)
      idc.MakeRptCmt(seg_ptr, new_name)
      offset = seg_ptr - ea
      seg_ptr += 4

    dw = offset - 5
    idc.PatchByte(ea, 0xE8)
    idc.PatchDword(ea + 1, dw)


def make_offsets(segname):
  segea = idc.SegByBase(idc.SegByName(segname))
  segend = idc.SegEnd(segea)

  while segea < segend:
    idc.OpOffset(segea, 0)
    ptr = idc.Dword(segea)
    idc.OpOffset(ptr, 0)
    segea += 4

if __name__ == '__main__':
  make_offsets('__cls_refs')
  make_offsets('__message_refs')
  idaapi.analyze_area(idc.MinEA(), idc.MaxEA())
  fix_callgraph(idc.LocByName('_objc_msgSend'), 'msgSend', 4, 4)
  fix_callgraph(idc.LocByName('_objc_msgSendSuper'), 'msgSendSuper', 4, 4)
  idaapi.analyze_area(idc.MinEA(), idc.MaxEA())
  print 'Done.'

########NEW FILE########
__FILENAME__ = objc_class

import idaapi, idautils, idc
import re

encoded_types = {
  'c':'char',
  'i':'int',
  's':'short',
  'l':'long',
  'q':'long long',
  'C':'unsigned char',
  'I':'unsigned int',
  'S':'unsigned short',
  'L':'unsigned long',
  'Q':'unsigned long long',
  'f':'float',
  'd':'double',
  'B':'bool',
  'v':'void',
  '*':'char *',
  '@':'id',
  '#':'class',
  '?':'unknown',
  ':':'SEL',
  '^':'ptr'}

class ObjcProperties:
    def __init__(self, ea):
        self.property_list = list()

#        print '%08x: Parsing properties' % ea
        entry_size = idc.Dword(ea)
        num_entries = idc.Dword(ea + 4)

        ea = ea + 8
        for i in range(num_entries):
            var_name = idc.GetString(idc.Dword(ea), -1, idc.ASCSTR_C)
            var_type = idc.GetString(idc.Dword(ea + 4), -1, idc.ASCSTR_C)
            self.property_list.append({'name':var_name, 'type':var_type})
            ea = ea + entry_size
        return

    def __len__(self):
        return len(self.property_list)

    def __repr__(self):
        dump = ''
        for entry in self.property_list:
            dump += '%s: %s\n' % (entry['name'], entry['type'])
        return dump


class ObjcIvars:
    def __init__(self, ea):
        self.ivar_list = list()

#        print '%08x: Parsing ivars' % ea
        entry_size = idc.Dword(ea)
        num_entries = idc.Dword(ea + 4)

        ea = ea + 8
        for i in range(num_entries):
            ivar_offset = idc.Dword(idc.Dword(ea))
            ivar_name = idc.GetString(idc.Dword(ea + 4), -1, idc.ASCSTR_C)
            ivar_type = idc.GetString(idc.Dword(ea + 8), -1, idc.ASCSTR_C)
            self.ivar_list.append({'name':ivar_name, 'type':ivar_type, 'offset':ivar_offset})
            ea = ea + entry_size
        return

    def __len__(self):
        return len(self.ivar_list)

    def __repr__(self):
        dump = ''
        for entry in self.ivar_list:
            dump += '%s (%d): %s\n' % (entry['name'], entry['offset'], encoded_types.get(entry['type'], entry['type']))
        return dump


class ObjcMethods:
    def __init__(self, ea):
        self.method_list = list()

#        print '%08x: Parsing methods' % ea
        entry_size = idc.Dword(ea)
        num_entries = idc.Dword(ea + 4)

        ea = ea + 8
        for i in range(num_entries):
            method_name = idc.GetString(idc.Dword(ea), -1, idc.ASCSTR_C)
            method_type = idc.GetString(idc.Dword(ea + 4), -1, idc.ASCSTR_C)
            method_ea = idc.Dword(ea + 8)
            self.method_list.append({'name': method_name, 'type':method_type, 'addr':method_ea})
            ea = ea + entry_size
        return

    def __len__(self):
        return len(self.method_list)

    def __repr__(self):
        dump = ''
        for entry in self.method_list:
            dump += '%08x: %s\n' % (entry['addr'], decode_type(entry['name'], entry['type']))
        return dump


class ObjcProtocols:
    def __init__(self, ea):
        self.protocol_list = list()

#        print '%08x: Parsing protocols' % ea
        num_main_structs = idc.Dword(ea)
        ea = ea + 4

        for i in range(num_main_structs):
            struct_off = idc.Dword(ea)
            protocol_name = idc.GetString(idc.Dword(struct_off + 4), -1, idc.ASCSTR_C)
            protocol_list = idc.Dword(struct_off + 8)
            instance_methods = idc.Dword(struct_off + 0xC)
            class_methods = idc.Dword(struct_off + 0x14)

            if instance_methods:
                _inst = ObjcMethods(instance_methods)
            else:
                _inst = None

            if class_methods:
                _class = ObjcMethods(class_methods)
            else:
                _class = None

            if protocol_list:
                _meta = ObjcProtocols(protocol_list)
            else:
                _meta = None

            self.protocol_list.append({
                'name': protocol_name,
                'instance_methods': _inst,
                'class_methods': _class,
                'meta_protocols': _meta})
            ea = ea + 4
        return

    def __len__(self):
        return len(self.protocol_list)

    def __repr__(self):
        dump = ''
        for entry in self.protocol_list:
            dump += 'Protocol %s:\n' % entry['name']
            if entry['instance_methods'] and len(entry['instance_methods']):
                dump += '  Instance Methods:\n    '
                dump += repr(entry['instance_methods']).replace('\n', '\n    ')

            if entry['class_methods'] and len(entry['class_methods']):
                dump += '  Class Methods:\n    '
                dump += repr(entry['class_methods']).replace('\n', '\n    ')

            if entry['meta_protocols'] and len(entry['meta_protocols']):
                dump += '  Protocol list:\n    '
                dump += repr(entry['meta_protocols']).replace('\n', '\n    ')

        return dump


class ObjcClass:
    def __init__(self, ea):
        self.class_info = dict()

        objc_const_seg = idc.SegByBase(idc.SegByName('__objc_const'))
        objc_const_end = idc.SegEnd(objc_const_seg)

        self.class_info['meta_class'] = idc.Dword(ea)
        self.class_info['super_class'] = idc.Dword(ea + 4)
        self.class_info['cache'] = idc.Dword(ea + 8)
        self.class_info['vtable'] = idc.Dword(ea + 0xC)
        _class_def = idc.Dword(ea + 0x10)

        if _class_def < objc_const_seg or _class_def > objc_const_end:
            return

        self.class_info['top_class'] = idc.Dword(_class_def)
        self.class_info['instance_size'] = idc.Dword(_class_def + 8)

        name_off = idc.Dword(_class_def + 0x10)
        class_name = idc.GetString(name_off, -1, idc.ASCSTR_C)
        if not class_name:
            class_name = '[UNKNOWN]'
        self.class_info['name'] = class_name

        self.class_info['methods'] = list()
        self.class_info['protocols'] = list()
        self.class_info['ivars'] = list()
        self.class_info['properties'] = list()

        if idc.Dword(_class_def + 0x14):
            self.class_info['methods'] = ObjcMethods(idc.Dword(_class_def + 0x14))

        if idc.Dword(_class_def + 0x18):
            self.class_info['protocols'] = ObjcProtocols(idc.Dword(_class_def + 0x18))

        if idc.Dword(_class_def + 0x1C):
            self.class_info['ivars'] = ObjcIvars(idc.Dword(_class_def + 0x1C))

        if idc.Dword(_class_def + 0x24):
            self.class_info['properties'] = ObjcProperties(idc.Dword(_class_def + 0x24))

        return

    def dump(self):
        if not self.class_info.has_key('name'):
            return
        print 'Class: %s' % self.class_info['name']
        print 'Attributes:'
        print '  IsTopClass: %d' % self.class_info['top_class']
        print '  Instance Size: %d' % self.class_info['instance_size']
        print '  Methods: %d' % len(self.class_info['methods'])
        print '  Protocols: %d' % len(self.class_info['protocols'])
        print '  Instance Vars: %d' % len(self.class_info['ivars'])
        print '  properties: %d' % len(self.class_info['properties'])

        if len(self.class_info['methods']):
            print 'Method list:\n  %s' % repr(self.class_info['methods']).replace('\n', '\n  ')

        if len(self.class_info['protocols']):
            print 'Protocols:\n  %s' % repr(self.class_info['protocols']).replace('\n', '\n  ')

        if len(self.class_info['ivars']):
            print 'Instance variables:\n  %s' % repr(self.class_info['ivars']).replace('\n', '\n  ')

        if len(self.class_info['properties']):
            print 'properties:\n  %s' % repr(self.class_info['properties']).replace('\n', '\n  ')


def main():
    objc_data_seg = idc.SegByBase(idc.SegByName('__objc_data'))
    if objc_data_seg == idc.BADADDR:
        print 'Cannot locate objc_data segment'
        return

    ea = objc_data_seg
    while ea < idc.SegEnd(objc_data_seg):
        objc_class = ObjcClass(ea)
        objc_class.dump()
        ea = ea + 0x14

def decode_type(name, type):
    global encoded_types

    list_types = re.split('\d+', type)
    if list_types[0][0] in '{[(':
        proto = list_types[0]
    else:
        proto = encoded_types.get(list_types[0], 'unknown ' + list_types[0])

    proto += ' ' + name + '('
    for t in list_types[3:]:
        if not t:
            continue
        if len(t) > 1 and t[0] in '{[(':
            proto += t + ', '
        else:
            proto += encoded_types.get(t, 'unknown ' + t) + ', '
    proto = proto.rstrip(' ,') + ')'
    return proto

if __name__ == '__main__':
    main()
    print 'Done.'

########NEW FILE########
__FILENAME__ = objc_helper
import idaapi, idc, idautils
import re
import time

displ_re = re.compile('\[R(?P<regnum>\d+)')
var_re = re.compile(', \[SP,#0x.*\+(?P<varname>\w+)\]')

def trace_param(ea, min_ea, op_type, op_val):
    '''
    trace_param: ea, min_ea, op_type, op_val

    Taking ea as start, this function does basic backtrace of
    an operand (defined by op_type and op_val) until it finds
    a data reference which we consider the "source". It stops
    when ea < min_ea (usually the function start).

    It does not support arithmetic or complex modifications of
    the source. This will be improved on future versions.
    '''
    global displ_re, msgsend, var_re

    ea_call = ea
    while ea != idc.BADADDR and ea != min_ea:
        ea = idc.PrevHead(ea, min_ea)

        if op_type == idaapi.o_reg and op_val == 0 and idaapi.is_call_insn(ea):
            # We have a BL/BLX that will modify the R0
            # we're tracking
            #
            return None

        if idc.GetMnem(ea) in ['LDR', 'MOV']:
            src_op = 1
            dest_op = 0
        elif idc.GetMnem(ea) == 'STR':
            src_op = 0
            dest_op = 1
        else:
            continue


        if idc.GetOpType(ea, dest_op) == op_type and idc.GetOperandValue(ea, dest_op) == op_val:
            # Found, see where it comes from
            if idc.GetOpType(ea, src_op) == idc.o_mem:
                # Got the final reference
                refs = list(idautils.DataRefsFrom(ea))
                if not refs:
                    local_ref = idc.GetOperandValue(ea, src_op)
                    far_ref = idc.Dword(local_ref)
                else:
                    while len(refs) > 0:
                        far_ref = refs[0]
                        refs = list(idautils.DataRefsFrom(refs[0]))
                return far_ref
            elif idc.GetOpType(ea, src_op) == idc.o_displ:
                if ', [SP' in idc.GetDisasm(ea):
                    if 'arg_' in idc.GetDisasm(ea):
                        # We don't track function arguments
                        return None

                    # We're tracking an stack variable
                    try:
                        var_name = var_re.search(idc.GetDisasm(ea)).group('varname')
                    except:
                        print '%08x: Unable to recognize variable' % ea
                        return None

                    while ea != idc.BADADDR and ea > min_ea:
                        if idc.GetMnem(ea) == 'STR' and var_name in idc.GetDisasm(ea):
                            # New reg to track
                            op_val = idc.GetOperandValue(ea, dest_op)
                            break
                        ea = idc.PrevHead(ea, min_ea)
                else:
                    # New reg to track
                    if '[LR]' in idc.GetDisasm(ea):
                        # Optimizations use LR as general reg
                        op_val = 14
                    else:
                        try:
                            op_val = int(displ_re.search(idc.GetDisasm(ea)).group('regnum'))
                        except:
                            print '%08x: Unable to recognize register' % ea
                            return None
            elif idc.GetOpType(ea, src_op) == idc.o_reg:
                # Direct reg-reg assignment
                op_val = idc.GetOperandValue(ea, src_op)
            else:
                # We don't track o_phrase or other complex source operands :(
                return None
    return None



def fix_callgraph(msgsend, segname, class_param, sel_param):
    '''
    fix_callgraph: msgsend, segname, class_param, sel_param

    Given the msgsend flavour address as a parameter, looks
    for the parameters (class and selector, identified by
    class_param and sel_param) and creates a new segment where
    it places a set of dummy calls named as classname_methodname
    (we use method instead of selector most of the time).
    '''

    t1 = time.time()
    if not msgsend:
        print 'ERROR: msgSend not found'
        return

    total = 0
    resolved = 0
    call_table = dict()

    for xref in idautils.XrefsTo(msgsend, idaapi.XREF_ALL):
        total += 1
        ea_call = xref.frm
        func_start = idc.GetFunctionAttr(ea_call, idc.FUNCATTR_START)
        if not func_start or func_start == idc.BADADDR:
            continue
        ea = ea_call
        method_name_ea = trace_param(ea, func_start, idc.o_reg, sel_param)
        if method_name_ea and idc.isASCII(idc.GetFlags(method_name_ea)):
            method_name = idc.GetString(method_name_ea, -1, idc.ASCSTR_C)
            if not method_name:
                method_name = '_unk_method'
        else:
            method_name = '_unk_method'

        class_name_ea = trace_param(ea, func_start, idc.o_reg, class_param)
        if class_name_ea:
            class_name = idc.Name(class_name_ea)
            if not class_name:
                class_name = '_unk_class'
        else:
            class_name = '_unk_class'

        if method_name == '_unk_method' and class_name == '_unk_class':
            continue

        # Using this name convention, if the class and method
        # are identified by IDA, the patched call will point to
        # the REAL call and not one of our dummy functions
        #
        class_name = class_name.replace('_OBJC_CLASS_$_', '')
        class_name = class_name.replace('_OBJC_METACLASS_$_', '')
        new_name = '_[' + class_name + '_' + method_name + ']'
        print '%08x: %s' % (ea_call, new_name)
        call_table[ea_call] = new_name
        resolved += 1

    print '\nFinal stats:\n\t%d total calls, %d resolved' % (total, resolved)
    print '\tAnalysis took %.2f seconds' % (time.time() - t1)

    if resolved == 0:
        print 'Nothing to patch.'
        return

    print 'Adding new segment to store new nullsubs'

    # segment size = opcode ret (4 bytes) * num_calls
    seg_size = resolved * 4
    seg_start = idc.MaxEA() + 4
    idaapi.add_segm(0, seg_start, seg_start + seg_size, segname, 'CODE')

    print 'Patching database...'
    seg_ptr = seg_start
    for ea, new_name in call_table.items():
        if idc.LocByName(new_name) != idc.BADADDR:
            offset = idc.LocByName(new_name) - ea
        else:
            # create code and name it
            idc.PatchDword(seg_ptr, 0xE12FFF1E) # BX LR
            idc.MakeName(seg_ptr, new_name)
            idc.MakeCode(seg_ptr)
            idc.MakeFunction(seg_ptr, seg_ptr + 4)
            idc.MakeRptCmt(seg_ptr, new_name)
            offset = seg_ptr - ea
            seg_ptr += 4

        # patch the msgsend call
        if idc.GetReg(ea, "T") == 1:
            if offset > 0 and offset & 0xFF800000:
                print 'Offset too far for Thumb (%08x) Stopping [%08x]' % (offset, ea)
                return

            off1 = (offset & 0x7FF000) >> 12
            off2 = (offset & 0xFFF) / 2
            w1 = (0xF000 | off1)
            w2 = (0xE800 | off2) - 1
            idc.PatchWord(ea, w1)
            idc.PatchWord(ea + 2, w2)
        else:
            if offset > 0 and offset & 0xFF000000:
                print 'Offset too far (%08x) Stopping [%08x]' % (offset, ea)
            dw = (0xFA000000 | (offset - 8 >> 2))
            if dw < 0:
                dw = dw & 0xFAFFFFFF
            idc.PatchDword(ea, dw)


def make_offsets(segname):
    segea = idc.SegByBase(idc.SegByName(segname))
    segend = idc.SegEnd(segea)

    while segea < segend:
        idc.OpOffset(segea, 0)
        ptr = idc.Dword(segea)
        idc.OpOffset(ptr, 0)
        segea += 4

if __name__ == '__main__':
    print 'Preparing class references segments'
    make_offsets('__objc_classrefs')
    make_offsets('__objc_superrefs')
    idaapi.analyze_area(idc.MinEA(), idc.MaxEA())
    print 'Fixing callgraph'
    fix_callgraph(idc.LocByName('_objc_msgSend'), 'msgSend', 0, 1)
    fix_callgraph(idc.LocByName('_objc_msgSendSuper2'), 'msgSendSuper', 3, 1)
    idaapi.analyze_area(idc.MinEA(), idc.MaxEA())
    print 'Done.'

########NEW FILE########
