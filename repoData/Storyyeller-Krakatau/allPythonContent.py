__FILENAME__ = assemble
import os.path

import Krakatau
from Krakatau.assembler import tokenize, parse, assembler
from Krakatau import script_util

def assembleClass(filename, makeLineNumbers, jasmode, debug=0):
    basename = os.path.basename(filename)
    assembly = open(filename, 'rb').read()
    if assembly.startswith('\xca\xfe') or assembly.startswith('\x50\x4b\x03\x04'):
        print 'Error: You appear to have passed a jar or classfile instead of an assembly file'
        print 'Perhaps you meant to invoke the disassembler instead?'
        return []

    assembly = '\n'+assembly+'\n' #parser expects newlines at beginning and end
    lexer = tokenize.makeLexer(debug=debug)
    parser = parse.makeParser(debug=debug)
    parse_trees = parser.parse(assembly, lexer=lexer)
    return parse_trees and [assembler.assemble(tree, makeLineNumbers, jasmode, basename) for tree in parse_trees]

if __name__== "__main__":
    print script_util.copyright

    import argparse
    parser = argparse.ArgumentParser(description='Krakatau bytecode assembler')
    parser.add_argument('-out',help='Path to generate files in')
    parser.add_argument('-g', action='store_true', help="Add line number information to the generated class")
    parser.add_argument('-jas', action='store_true', help="Enable Jasmin compatibility mode")
    parser.add_argument('-r', action='store_true', help="Process all files in the directory target and subdirectories")
    parser.add_argument('target',help='Name of file to assemble')
    args = parser.parse_args()

    targets = script_util.findFiles(args.target, args.r, '.j')
    writeout = script_util.fileDirOut(args.out, '.class')

    for i, target in enumerate(targets):
        print 'Processing file {}, {}/{} remaining'.format(target, len(targets)-i, len(targets))
        pairs = assembleClass(target, args.g, args.jas)

        # if pairs is None:
        #     print 'Assembly of ', target, 'failed!'
        #     continue

        for name, data in pairs:
            filename = writeout(name, data)
            print 'Class written to', filename
########NEW FILE########
__FILENAME__ = decompile
import os.path
import time, random

import Krakatau
import Krakatau.ssa
from Krakatau.error import ClassLoaderError
from Krakatau.environment import Environment
from Krakatau.java import javaclass
from Krakatau.verifier.inference_verifier import verifyBytecode
from Krakatau import script_util

def findJRE():
    try:
        home = os.environ['JAVA_HOME']
        path = os.path.join(home, 'jre', 'lib', 'rt.jar')
        if os.path.isfile(path):
            return path

        #For macs
        path = os.path.join(home, 'bundle', 'Classes', 'classes.jar')
        if os.path.isfile(path):
            return path
    except Exception as e:
        pass

def _stats(s):
    bc = len(s.blocks)
    vc = sum(len(b.unaryConstraints) for b in s.blocks)
    return '{} blocks, {} variables'.format(bc,vc)

def _print(s):
    from Krakatau.ssa.printer import SSAPrinter
    return SSAPrinter(s).print_()

def makeGraph(m):
    v = verifyBytecode(m.code)
    s = Krakatau.ssa.ssaFromVerified(m.code, v)

    if s.procs:
        # s.mergeSingleSuccessorBlocks()
        # s.removeUnusedVariables()
        s.inlineSubprocs()

    # print _stats(s)
    s.condenseBlocks()
    s.mergeSingleSuccessorBlocks()
    s.removeUnusedVariables()
    # print _stats(s)
    s.constraintPropagation()
    s.disconnectConstantVariables()
    s.simplifyJumps()
    s.mergeSingleSuccessorBlocks()
    s.removeUnusedVariables()
    # print _stats(s)
    return s

def deleteUnusued(cls):
    #Delete attributes we aren't going to use
    #pretty hackish, but it does help when decompiling large jars
    for e in cls.fields + cls.methods:
        del e.class_, e.attributes, e.static
    for m in cls.methods:
        del m.native, m.abstract, m.isConstructor
        del m.code
    del cls.version, cls.this, cls.super, cls.env
    del cls.interfaces_raw, cls.cpool
    del cls.attributes

def decompileClass(path=[], targets=None, outpath=None, skipMissing=False):
    writeout = script_util.fileDirOut(outpath, '.java')

    e = Environment()
    for part in path:
        e.addToPath(part)

    start_time = time.time()
    # random.shuffle(targets)
    with e: #keep jars open
        for i,target in enumerate(targets):
            print 'processing target {}, {} remaining'.format(target, len(targets)-i)

            try:
                c = e.getClass(target)
                source = javaclass.generateAST(c, makeGraph).print_()
            except ClassLoaderError as err:
                if skipMissing:
                    print 'failed to decompile {} due to missing or invalid class {}'.format(target, err.data)
                    continue
                else:
                    raise

            #The single class decompiler doesn't add package declaration currently so we add it here
            if '/' in target:
                package = 'package {};\n\n'.format(target.replace('/','.').rpartition('.')[0])
                source = package + source

            filename = writeout(c.name, source)
            print 'Class written to', filename
            print time.time() - start_time, ' seconds elapsed'
            deleteUnusued(c)

if __name__== "__main__":
    print script_util.copyright

    import argparse
    parser = argparse.ArgumentParser(description='Krakatau decompiler and bytecode analysis tool')
    parser.add_argument('-path',action='append',help='Semicolon seperated paths or jars to search when loading classes')
    parser.add_argument('-out',help='Path to generate source files in')
    parser.add_argument('-nauto', action='store_true', help="Don't attempt to automatically locate the Java standard library. If enabled, you must specify the path explicitly.")
    parser.add_argument('-r', action='store_true', help="Process all files in the directory target and subdirectories")
    parser.add_argument('-skip', action='store_true', help="Skip classes when an error occurs due to missing dependencies")
    parser.add_argument('target',help='Name of class or jar file to decompile')
    args = parser.parse_args()

    path = []
    if not args.nauto:
        print 'Attempting to automatically locate the standard library...'
        found = findJRE()
        if found:
            print 'Found at ', found
            path.append(found)
        else:
            print 'Unable to find the standard library'

    if args.path:
        for part in args.path:
            path.extend(part.split(';'))

    if args.target.endswith('.jar'):
        path.append(args.target)

    targets = script_util.findFiles(args.target, args.r, '.class')
    targets = map(script_util.normalizeClassname, targets)
    decompileClass(path, targets, args.out, args.skip)
########NEW FILE########
__FILENAME__ = disassemble
import os.path
import time, zipfile

import Krakatau
import Krakatau.binUnpacker
from Krakatau.classfile import ClassFile
import Krakatau.assembler.disassembler

from Krakatau import script_util

def readFile(filename):
    with open(filename, 'rb') as f:
        return f.read()

def disassembleClass(readTarget, targets=None, outpath=None):
    writeout = script_util.fileDirOut(outpath, '.j')

    # targets = targets[::-1]
    start_time = time.time()
    # __import__('random').shuffle(targets)
    for i,target in enumerate(targets):
        print 'processing target {}, {}/{} remaining'.format(target, len(targets)-i, len(targets))

        data = readTarget(target)
        stream = Krakatau.binUnpacker.binUnpacker(data=data)
        class_ = ClassFile(stream)
        class_.loadElements(keepRaw=True)

        source = Krakatau.assembler.disassembler.disassemble(class_)
        filename = writeout(class_.name, source)
        print 'Class written to', filename
        print time.time() - start_time, ' seconds elapsed'

if __name__== "__main__":
    print script_util.copyright

    import argparse
    parser = argparse.ArgumentParser(description='Krakatau decompiler and bytecode analysis tool')
    parser.add_argument('-out',help='Path to generate files in')
    parser.add_argument('-r', action='store_true', help="Process all files in the directory target and subdirectories")
    parser.add_argument('-path',help='Jar to look for class in')
    parser.add_argument('target',help='Name of class or jar file to decompile')
    args = parser.parse_args()

    targets = script_util.findFiles(args.target, args.r, '.class')

    jar = args.path
    if jar is None and args.target.endswith('.jar'):
        jar = args.target

    #allow reading files from a jar if target is specified as a jar
    if jar:
        def readArchive(name):
            with zipfile.ZipFile(jar, 'r') as archive:
                return archive.open(name).read()
        readTarget = readArchive
    else:
        readTarget = readFile

    disassembleClass(readTarget, targets, args.out)
########NEW FILE########
__FILENAME__ = assembler
import collections
import struct, operator

from . import instructions, codes
from .. import constant_pool
from ..classfile import ClassFile
from ..method import Method
from ..field import Field

class AssemblerError(Exception):
    def __init__(self, message, data=None):
        super(AssemblerError, self).__init__(message)
        self.data = data

def error(msg):
    raise AssemblerError(msg)

class PoolRef(object):
    def __init__(self, *args, **kwargs):
        self.index = kwargs.get('index')
        self.lbl = kwargs.get('lbl')
        self.args = args

    def toIndex(self, pool, forbidden=(), **kwargs):
        if self.index is not None:
            return self.index
        if self.lbl:
            self.index = pool.getLabel(self.lbl, forbidden, **kwargs)
        else:
            self.args = [(x.toIndex(pool) if isinstance(x, PoolRef) else x) for x in self.args]
            self.index = pool.getItem(*self.args, **kwargs)
        return self.index

class PoolInfo(object):
    def __init__(self):
        self.pool = constant_pool.ConstPool()
        self.lbls = {}
        self.fixed = {} # constant pool entries in a specific slot
        self.bootstrap = [] #entries for the BootstrapMethods attribute if any

    def getLabel(self, lbl, forbidden=(), **kwargs):
        if lbl in forbidden:
            error('Circular constant pool reference: ' + ', '.join(forbidden))
        forbidden = forbidden + (lbl,)
        return self.lbls[lbl].toIndex(self, forbidden, **kwargs)

    def getItem(self, type_, *args, **kwargs):
        if type_ == 'InvokeDynamic':
            self.bootstrap.append(args[:-1])
            args = len(self.bootstrap)-1, args[-1]    
        return self.pool.addItem((type_, tuple(args)), **kwargs)

    def Utf8(self, s):
        return self.getItem('Utf8', s)

    def assignFixedSlots(self):
        self.pool.reserved.update(self.fixed)
        for i,v in self.fixed.items():
            if v.args and v.args[0] in ('Double','Long'):
                self.pool.reserved.add(i+1)
                
        #TODO - order these in terms of dependencies?
        for index, value in self.fixed.items():
            used = value.toIndex(self, index=index)
            if used != index: #we need to copy an existing item
                self.pool.copyItem(used, index)

_format_ops = collections.defaultdict(tuple)
_format_ops[''] = instructions.instrs_noarg
_format_ops['>B'] = 'iload', 'lload', 'fload', 'dload', 'aload', 'istore', 'lstore', 'fstore', 'dstore', 'astore', 'ret'
_format_ops['>h'] = 'ifeq', 'ifne', 'iflt', 'ifge', 'ifgt', 'ifle', 'if_icmpeq', 'if_icmpne', 'if_icmplt', 'if_icmpge', 'if_icmpgt', 'if_icmple', 'if_acmpeq', 'if_acmpne', 'goto', 'jsr', 'ifnull', 'ifnonnull'
_format_ops['>H'] = 'ldc_w', 'ldc2_w', 'getstatic', 'putstatic', 'getfield', 'putfield', 'invokevirtual', 'invokespecial', 'invokestatic', 'new', 'anewarray', 'checkcast', 'instanceof'

_format_ops['>b'] += 'bipush', 
_format_ops['>Bb'] += 'iinc', 
_format_ops['>h'] += 'sipush', 
_format_ops['>HB'] += 'multianewarray',
_format_ops['>HBB'] += 'invokeinterface',
_format_ops['>HH'] += 'invokedynamic',
_format_ops['>B'] += 'ldc', 'newarray'
_format_ops['>i'] += 'goto_w', 'jsr_w'

op_structs = {}
for fmt, ops in _format_ops.items():
    _s = struct.Struct(fmt)
    for _op in ops:
        op_structs[_op] = _s

def getPadding(pos):
    return (3-pos) % 4

def getInstrLen(instr, pos):
    op = instr[0]
    if op in op_structs:
        return 1 + op_structs[op].size
    elif op == 'wide':
        return 2 + 2 * len(instr[1][1])
    else:
        padding = getPadding(pos)
        count = len(instr[1][1])
        if op == 'tableswitch':
            return 13 + padding + 4*count
        else:
            return 9 + padding + 8*count 

def assembleInstruction(instr, labels, pos, pool):
    def lbl2Off(lbl):
        if lbl not in labels:
            del labels[None]
            error('Undefined label: {}\nDefined labels for current method are: {}'.format(lbl, ', '.join(sorted(labels))))
        return labels[lbl] - pos

    op = instr[0]
    first = chr(instructions.allinstructions.index(op))

    instr = [(x.toIndex(pool) if isinstance(x, PoolRef) else x) for x in instr[1:]]
    if op in instructions.instrs_lbl:
        instr[0] = lbl2Off(instr[0])
    if op in op_structs:
        rest = op_structs[op].pack(*instr)
        return first+rest
    elif op == 'wide':
        subop, args = instr[0]
        prefix = chr(instructions.allinstructions.index(subop))
        fmt = '>Hh' if len(args) > 1 else '>H'
        rest = struct.pack(fmt, *args)
        return first + prefix + rest
    else:
        padding = getPadding(pos)
        param, jumps, default = instr[0]
        default = lbl2Off(default)

        if op == 'tableswitch':
            jumps = map(lbl2Off, jumps)
            low, high = param, param + len(jumps)-1
            temp = struct.Struct('>i')
            part1 = first + '\0'*padding + struct.pack('>iii', default, low, high)
            return part1 + ''.join(map(temp.pack, jumps))
        elif op == 'lookupswitch':
            jumps = {k:lbl2Off(lbl) for k,lbl in jumps}
            jumps = sorted(jumps.items())
            temp = struct.Struct('>ii')
            part1 = first + '\0'*padding + struct.pack('>ii', default, len(jumps))
            part2 = ''.join(map(temp.pack, *zip(*jumps))) if jumps else ''
            return part1 + part2

def groupList(pairs):
    d = collections.defaultdict(list)
    for k,v in pairs:
        d[k].append(v)
    return d

def splitList(pairs):
    d = groupList(pairs)
    return d[False], d[True]
       
def assembleCodeAttr(statements, pool, version, addLineNumbers, jasmode):
    directives, lines = splitList(statements)
    dir_offsets = collections.defaultdict(list)

    offsets = []
    labels = {}
    pos = 0
    #first run through to calculate bytecode offsets
    #this is greatly complicated due to the need to
    #handle Jasmine line number directives
    for t, statement in statements:
        if t:
            lbl, instr = statement
            labels[lbl] = pos
            if instr is not None:
                offsets.append(pos)
                pos += getInstrLen(instr, pos)
        #some directives require us to keep track of the corresponding bytecode offset
        elif statement[0] in ('.line','.stackmap'):
            dir_offsets[statement[0]].append(pos)
    code_len = pos

    code_bytes = ''
    for lbl, instr in lines:
        if instr is not None:
            code_bytes += assembleInstruction(instr, labels, len(code_bytes), pool)
    assert(len(code_bytes) == code_len)

    directive_dict = groupList(directives)
    limits = groupList(directive_dict['.limit'])

    stack = min(limits['stack'] + [65535]) 
    locals_ = min(limits['locals'] + [65535]) 

    excepts = []
    for name, start, end, target in directive_dict['.catch']:
        #Hack for compatibility with Jasmin
        if jasmode and name.args and (name.args[1].args == ('Utf8','all')):
            name.index = 0
        vals = labels[start], labels[end], labels[target], name.toIndex(pool)
        excepts.append(struct.pack('>HHHH',*vals))
    
    attributes = []

    #StackMapTable
    def pack_vt(vt):
        s = chr(codes.vt_codes[vt[0]])
        if vt[0] == 'Object':
            s += struct.pack('>H', vt[1].toIndex(pool))        
        elif vt[0] == 'Uninitialized':
            s += struct.pack('>H', labels[vt[1]])
        return s

    if directive_dict['.stackmap']:
        frames = []
        last_pos = -1

        for pos, info in zip(dir_offsets['.stackmap'], directive_dict['.stackmap']):
            offset = pos - last_pos - 1
            last_pos = pos
            assert(offset >= 0)

            tag = info[0]
            if tag == 'same':
                if offset >= 64:
                    error('Max offset on a same frame is 63.')
                frames.append(chr(offset))            
            elif tag == 'same_locals_1_stack_item':
                if offset >= 64:
                    error('Max offset on a same_locals_1_stack_item frame is 63.')
                frames.append(chr(64 + offset) + pack_vt(info[2][0]))            
            elif tag == 'same_locals_1_stack_item_extended':
                frames.append(struct.pack('>BH', 247, offset) + pack_vt(info[2][0]))            
            elif tag == 'chop':
                if not (1 <= info[1] <= 3):
                    error('Chop frame can only remove 1-3 locals')
                frames.append(struct.pack('>BH', 251-info[1], offset))
            elif tag == 'same_extended':
                frames.append(struct.pack('>BH', 251, offset))
            elif tag == 'append':
                local_vts = map(pack_vt, info[2])
                if not (1 <= len(local_vts) <= 3):
                    error('Append frame can only add 1-3 locals')
                frames.append(struct.pack('>BH', 251+len(local_vts), offset) + ''.join(local_vts))
            elif tag == 'full':
                local_vts = map(pack_vt, info[2])
                stack_vts = map(pack_vt, info[3])
                frame = struct.pack('>BH', 255, offset)
                frame += struct.pack('>H', len(local_vts)) + ''.join(local_vts)
                frame += struct.pack('>H', len(stack_vts)) + ''.join(stack_vts)
                frames.append(frame)

        sm_body = ''.join(frames)
        sm_attr = struct.pack('>HIH', pool.Utf8("StackMapTable"), len(sm_body)+2, len(frames)) + sm_body
        attributes.append(sm_attr)

    #line number attribute
    if addLineNumbers and not directive_dict['line']:
        dir_offsets['line'] = directive_dict['line'] = offsets
    if directive_dict['line']:
        lntable = [struct.pack('>HH',x,y) for x,y in zip(dir_offsets['line'], directive_dict['line'])]
        ln_attr = struct.pack('>HIH', pool.Utf8("LineNumberTable"), 2+4*len(lntable), len(lntable)) + ''.join(lntable)        
        attributes.append(ln_attr)

    if directive_dict['.var']:
        sfunc = struct.Struct('>HHHHH').pack
        vartable = []
        for index, name, desc, start, end in directive_dict['.var']:
            start, end = labels[start], labels[end]
            name, desc = name.toIndex(pool), desc.toIndex(pool)
            vartable.append(sfunc(start, end-start, name, desc, index))
        var_attr = struct.pack('>HIH', pool.Utf8("LocalVariableTable"), 2+10*len(vartable), len(vartable)) + ''.join(vartable)        
        attributes.append(var_attr)

    if not code_len:
        return None

    for attrname, data in directive_dict['.codeattribute']:
        attr = struct.pack('>HI', attrname.toIndex(pool), len(data)) + data
        attributes.append(attr)        


    #Old versions use shorter fields for stack, locals, and code length
    header_fmt = '>HHI' if version > (45,2) else '>BBH'

    name_ind = pool.Utf8("Code")
    attr_len = struct.calcsize(header_fmt) + 4 + len(code_bytes) + 8*len(excepts) + sum(map(len, attributes))
    
    assembled_bytes = struct.pack('>HI', name_ind, attr_len)
    assembled_bytes += struct.pack(header_fmt, stack, locals_, len(code_bytes))
    assembled_bytes += code_bytes
    assembled_bytes += struct.pack('>H', len(excepts)) + ''.join(excepts)
    assembled_bytes += struct.pack('>H', len(attributes)) + ''.join(attributes)
    return assembled_bytes

def _assembleEVorAnnotationSub(pool, init_args, isAnnot):
    #call types
    C_ANNOT, C_ANNOT2, C_EV = range(3)
    init_callt = C_ANNOT if isAnnot else C_EV

    stack = [(init_callt, init_args)]
    parts = []
    add = parts.append

    while stack:
        callt, args = stack.pop()

        if callt == C_ANNOT:
            typeref, keylines = args
            add(struct.pack('>HH', typeref.toIndex(pool), len(keylines)))
            for pair in reversed(keylines):
                stack.append((C_ANNOT2, pair))

        elif callt == C_ANNOT2:
            name, val = args
            add(struct.pack('>H', name.toIndex(pool)))
            stack.append((C_EV, val))

        elif callt == C_EV:
            tag, data = args
            assert(tag in codes.et_rtags)
            add(tag)

            if tag in 'BCDFIJSZsc':
                add(struct.pack('>H', data[0].toIndex(pool)))
            elif tag == 'e':
                add(struct.pack('>HH', data[0].toIndex(pool), data[1].toIndex(pool)))
            elif tag == '@':
                stack.append((C_ANNOT, data[0]))
            elif tag == '[':
                add(struct.pack('>H', len(data[1])))
                for arrval in reversed(data[1]):
                    stack.append((C_EV, arrval))
    return ''.join(parts)

def assembleElementValue(val, pool):
    return  _assembleEVorAnnotationSub(pool, val, False)

def assembleAnnotation(annotation, pool):
    return  _assembleEVorAnnotationSub(pool, annotation, True)

def assembleMethod(header, statements, pool, version, addLineNumbers, jasmode):
    mflags, (name, desc) = header
    name = name.toIndex(pool)
    desc = desc.toIndex(pool)

    flagbits = map(Method.flagVals.get, mflags)
    flagbits = reduce(operator.__or__, flagbits, 0)

    meth_statements, code_statements = splitList(statements)

    method_attributes = []
    code_attr = assembleCodeAttr(code_statements, pool, version, addLineNumbers, jasmode)
    if code_attr is not None:
        method_attributes.append(code_attr)

    directive_dict = groupList(meth_statements)
    if directive_dict['.throws']:
        t_inds = [struct.pack('>H', x.toIndex(pool)) for x in directive_dict['.throws']]
        throw_attr = struct.pack('>HIH', pool.Utf8("Exceptions"), 2+2*len(t_inds), len(t_inds)) + ''.join(t_inds)        
        method_attributes.append(throw_attr)

    #Runtime annotations
    for vis in ('Invisible','Visible'):
        paramd = groupList(directive_dict['.runtime'+vis.lower()])

        if None in paramd:
            del paramd[None]

        if paramd:
            parts = []
            for i in range(max(paramd)):
                annotations = [assembleAnnotation(a, pool) for a in paramd[i]]
                part = struct.pack('>H', len(annotations)) + ''.join(annotations)
                parts.append(part)
            attrlen = 1+sum(map(len, parts))
            attr = struct.pack('>HIB', pool.Utf8("Runtime{}ParameterAnnotations".format(vis)), attrlen, len(parts)) + ''.join(parts)
            method_attributes.append(attr)

    if '.annotationdefault' in directive_dict:
        val = directive_dict['.annotationdefault'][0]
        data = assembleElementValue(val, pool)
        attr = struct.pack('>HI', pool.Utf8("AnnotationDefault"), len(data)) + data        
        method_attributes.append(attr)

    assembleClassFieldMethodAttributes(method_attributes.append, directive_dict, pool)
    return struct.pack('>HHHH', flagbits, name, desc, len(method_attributes)) + ''.join(method_attributes)

def getLdcRefs(statements):
    lines = [x[1][1] for x in statements if x[0] and x[1][0]]
    instructions = [x[1] for x in lines if x[1] is not None]

    for instr in instructions:
        op = instr[0]
        if op == 'ldc':
            yield instr[1]
 
def addLdcRefs(methods, pool):
    def getRealRef(ref, forbidden=()):
        '''Get the root PoolRef associated with a given PoolRef, following labels'''
        if ref.index is None and ref.lbl:
            if ref.lbl in forbidden:
                error('Circular constant pool reference: ' + ', '.join(forbidden))
            forbidden = forbidden + (ref.lbl,)
            return getRealRef(pool.lbls[ref.lbl], forbidden) #recursive call
        return ref

    #We attempt to estimate how many slots are needed after merging identical entries
    #So we can reserve the correct number of slots without leaving unused gaps
    #However, in complex cases, such as string/class/mt referring to an explicit
    #reference, we may overestimate
    ldc_refs = collections.defaultdict(set)

    for header, statements in methods:
        for ref in getLdcRefs(statements):
            ref = getRealRef(ref)
            if ref.index is not None:
                continue

            type_ = ref.args[0]
            if type_ in ('Int','Float'):
                key = ref.args[1]
            elif type_ in ('String','Class','MethodType'): 
                uref = getRealRef(ref.args[1])
                key = uref.index, uref.args[1:]
            else: #for MethodHandles, don't even bother trying to estimate merging
                key = ref.args[1:] 
            ldc_refs[type_].add(key)    

    #TODO - make this a little cleaner so we don't have to mess with the ConstantPool internals
    num = sum(map(len, ldc_refs.values()))
    slots = [pool.pool.getAvailableIndex() for _ in range(num)]
    pool.pool.reserved.update(slots)

    for type_ in ('Int','Float'):
        for arg in ldc_refs[type_]:
            pool.getItem(type_, arg, index=slots.pop())
    for type_ in ('String','Class','MethodType'):
        for ind,args in ldc_refs[type_]:
            arg = ind if ind is not None else pool.Utf8(*args)
            pool.getItem(type_, arg, index=slots.pop())
    for type_ in ('MethodHandle',):
        for code, ref in ldc_refs[type_]:
            pool.getItem(type_, code, ref.toIndex(pool), index=slots.pop())
    assert(not slots)
    assert(not pool.pool.reserved)

def assembleClassFieldMethodAttributes(addcb, directive_dict, pool):
    for vis in ('Invisible','Visible'):
        paramd = groupList(directive_dict['.runtime'+vis.lower()])
        if None in paramd:
            annotations = [assembleAnnotation(a, pool) for a in paramd[None]]
            attrlen = 2+sum(map(len, annotations))
            attr = struct.pack('>HIH', pool.Utf8("Runtime{}Annotations".format(vis)), attrlen, len(annotations)) + ''.join(annotations)
            addcb(attr)

    for name in directive_dict['.signature']:
        attr = struct.pack('>HIH', pool.Utf8("Signature"), 2, name.toIndex(pool))
        addcb(attr)

    #.innerlength directive overrides the normal attribute length calculation
    hasoverride = len(directive_dict['.innerlength']) > 0

    for name, data in directive_dict['.attribute']:    
        name_ind = name.toIndex(pool)

        if hasoverride and pool.pool.getArgsCheck('Utf8', name_ind) == 'InnerClasses':
            attrlen = directive_dict['.innerlength'][0]
        else:
            attrlen = len(data)

        attr = struct.pack('>HI', name_ind, attrlen) + data
        addcb(attr)

def assembleClassAttributes(addcb, directive_dict, pool, addLineNumbers, jasmode, filename):

    sourcefile = directive_dict.get('.source',[None])[0] #PoolRef or None
    if jasmode and not sourcefile:
        sourcefile = pool.Utf8(filename)
    elif addLineNumbers and not sourcefile:
        sourcefile = pool.Utf8("SourceFile")
    if sourcefile:
        attr = struct.pack('>HIH', pool.Utf8("SourceFile"), 2, sourcefile.toIndex(pool))
        addcb(attr)

    if '.inner' in directive_dict:
        parts = []
        for inner, outer, name, flags in directive_dict['.inner']:
            flagbits = map(ClassFile.flagVals.get, flags)
            flagbits = reduce(operator.__or__, flagbits, 0)
            part = struct.pack('>HHHH', inner.toIndex(pool), outer.toIndex(pool), name.toIndex(pool), flagbits)
            parts.append(part)

        #.innerlength directive overrides the normal attribute length calculation
        innerlen = 2+8*len(parts) if '.innerlength' not in directive_dict else directive_dict['.innerlength'][0]
        attr = struct.pack('>HIH', pool.Utf8("InnerClasses"), innerlen, len(parts)) + ''.join(parts)
        addcb(attr)

    if '.enclosing' in directive_dict:
        class_, nat = directive_dict['.enclosing'][0]
        attr = struct.pack('>HIHH', pool.Utf8("EnclosingMethod"), 4, class_.toIndex(pool), nat.toIndex(pool))
        addcb(attr)

    assembleClassFieldMethodAttributes(addcb, directive_dict, pool)


def assemble(tree, addLineNumbers, jasmode, filename):
    pool = PoolInfo()
    version, cattrs1, classdec, superdec, interface_decs, cattrs2, topitems = tree
    if not version: #default to version 49.0 except in Jasmin compatibility mode
        version = (45,3) if jasmode else (49,0)

    #scan topitems, plus statements in each method to get cpool directives
    interfaces = []
    fields = []
    methods = []
    attributes = []

    directive_dict = groupList(cattrs1 + cattrs2)
    top_d = groupList(topitems)

    for slot, value in top_d['const']:
        if slot.index is not None:
            pool.fixed[slot.index] = value
        else:
            pool.lbls[slot.lbl] = value
    pool.assignFixedSlots()

    #Now find all cp references used in an ldc instruction
    #Since they must be <=255, we give them priority in assigning slots
    #to maximize the chance of a successful assembly
    addLdcRefs(top_d['method'], pool)

    for flags, name, desc, const, field_directives in top_d['field']:
        flagbits = map(Field.flagVals.get, flags)
        flagbits = reduce(operator.__or__, flagbits, 0)
        name = name.toIndex(pool)
        desc = desc.toIndex(pool)

        fattrs = []
        if const is not None:
            attr = struct.pack('>HIH', pool.Utf8("ConstantValue"), 2, const.toIndex(pool))
            fattrs.append(attr)

        assembleClassFieldMethodAttributes(fattrs.append, groupList(field_directives), pool)

        field_code = struct.pack('>HHHH', flagbits, name, desc, len(fattrs)) + ''.join(fattrs)
        fields.append(field_code)

    for header, statements in top_d['method']:
        methods.append(assembleMethod(header, statements, pool, version, addLineNumbers, jasmode))

    if pool.bootstrap:
        entries = [struct.pack('>H' + 'H'*len(bsargs), bsargs[0], len(bsargs)-1, *bsargs[1:]) for bsargs in pool.bootstrap]   
        attrbody = ''.join(entries)
        attrhead = struct.pack('>HIH', pool.Utf8("BootstrapMethods"), 2+len(attrbody), len(entries))
        attributes.append(attrhead + attrbody)

    #Explicit class attributes
    assembleClassAttributes(attributes.append, directive_dict, pool, addLineNumbers, jasmode, filename)

    interfaces = [struct.pack('>H', x.toIndex(pool)) for x in interface_decs]
    intf, cflags, this = classdec
    cflags = set(cflags)
    if intf:
        cflags.add('INTERFACE')
    if jasmode:
        cflags.add('SUPER')

    flagbits = map(ClassFile.flagVals.get, cflags)
    flagbits = reduce(operator.__or__, flagbits, 0)
    this = this.toIndex(pool)
    super_ = superdec.toIndex(pool)

    major, minor = version
    class_code = '\xCA\xFE\xBA\xBE' + struct.pack('>HH', minor, major)
    class_code += pool.pool.bytes()
    class_code += struct.pack('>HHH', flagbits, this, super_)
    for stuff in (interfaces, fields, methods, attributes):
        bytes_ = struct.pack('>H', len(stuff)) + ''.join(stuff)
        class_code += bytes_

    name = pool.pool.getArgs(this)[0]
    return name, class_code
########NEW FILE########
__FILENAME__ = codes
_handle_types = 'getField getStatic putField putStatic invokeVirtual invokeStatic invokeSpecial newInvokeSpecial invokeInterface'.split()
handle_codes = dict(zip(_handle_types, range(1,10)))

newarr_codes = dict(zip('boolean char float double byte short int long'.split(), range(4,12)))

vt_keywords = ['Top','Integer','Float','Double','Long','Null','UninitializedThis','Object','Uninitialized']
vt_codes = {k:i for i,k in enumerate(vt_keywords)}


et_rtags = dict(zip('BCDFIJSZsce@[', 'byte char double int float long short boolean string class enum annotation array'.split()))
et_tags = {v:k for k,v in et_rtags.items()}
########NEW FILE########
__FILENAME__ = disassembler
import collections
import re

from . import instructions, tokenize, parse, assembler, codes
from ..binUnpacker import binUnpacker
from ..classfile import ClassFile

MAX_INLINE_LENGTH = 50

rhandle_codes = {v:k for k,v in codes.handle_codes.items()}
rnewarr_codes = {v:k for k,v in codes.newarr_codes.items()}

not_word_regex = '(?:{}|{}|{}|;)'.format(tokenize.int_base, tokenize.float_base, tokenize.t_CPINDEX)
not_word_regex = re.compile(not_word_regex, re.VERBOSE)
is_word_regex = re.compile(tokenize.t_WORD.__doc__+'$')
assert(is_word_regex.match("''") is None)

def isWord(s):
    '''Determine if s can be used as an inline word'''
    if s in parse.badwords or (not_word_regex.match(s) is not None):
        return False
    #eliminate unprintable characters below 32
    #also, don't allow characters above 127 to keep things simpler
    return (is_word_regex.match(s) is not None) and min(s) > ' ' and max(s) <= '\x7f'

def rstring(s, allowWord=True):
    '''Returns a representation of the string. If allowWord is true, it will be unquoted if possible'''
    if allowWord and isWord(s):
        return s
    try:
        if s.encode('ascii') == s:
            return repr(str(s))
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return repr(s)

class PoolManager(object):
    def __init__(self, pool):
        self.const_pool = pool #keep this around for the float conversion function
        self.pool = pool.pool
        self.bootstrap_methods = [] #filled in externally
        self.used = set() #which cp entries are used non inline and so must be printed

        #For each type, store the function needed to generate the rhs of a constant pool specifier
        temp1 = lambda ind: rstring(self.cparg1(ind))
        temp2 = lambda ind: self.utfref(self.cparg1(ind))

        self.cpref_table = {
            "Utf8": temp1,

            "Class": temp2,
            "String": temp2,
            "MethodType": temp2,

            "NameAndType": self.multiref,
            "Field": self.multiref,
            "Method": self.multiref,
            "InterfaceMethod": self.multiref,

            "Int": self.ldc,
            "Long": self.ldc,
            "Float": self.ldc,
            "Double": self.ldc,

            "MethodHandle": self.methodhandle_notref,
            "InvokeDynamic": self.invokedynamic_notref,
            }

    def cparg1(self, ind):
        return self.pool[ind][1][0]

    def inlineutf(self, ind, allowWord=True):
        '''Returns the word if it's short enough to inline, else None'''
        arg = self.cparg1(ind)
        rstr = rstring(arg, allowWord=allowWord)
        if len(rstr) <= MAX_INLINE_LENGTH:
            return rstr
        return None

    def ref(self, ind):
        self.used.add(ind)
        return '[_{}]'.format(ind)

    def utfref(self, ind):
        if ind == 0:
            return '[0]'
        inline = self.inlineutf(ind)
        return inline if inline is not None else self.ref(ind)

    #Also works for Strings and MethodTypes
    def classref(self, ind):
        if ind == 0:
            return '[0]'
        inline = self.inlineutf(self.cparg1(ind))
        return inline if inline is not None else self.ref(ind)

    #For Field, Method, IMethod, and NameAndType. Effectively notref
    def multiref(self, ind):
        if ind == 0:
            return '[0]'
        typen, args = self.pool[ind]
        if typen == "Utf8":
            return self.utfref(ind)
        elif typen == "Class":
            return self.classref(ind)
        return ' '.join(map(self.multiref, args))

    #Special case for instruction fieldrefs as a workaround for Jasmin's awful syntax
    def notjasref(self, ind):
        typen, args = self.pool[ind]
        cind = self.cparg1(ind)
        inline = self.inlineutf(self.cparg1(cind))
        if inline is None:
            return self.ref(ind)
        return inline + ' ' + self.multiref(args[1])

    def ldc(self, ind):
        typen, args = self.pool[ind]
        arg = args[0]

        if typen == 'String':
            inline = self.inlineutf(arg, allowWord=False)
            return inline if inline is not None else self.ref(ind)
        elif typen in ('Int','Long','Float','Double'):
            if typen == "Float" or typen == "Double":
                arg = self.const_pool.getArgs(ind)[0]

            rstr = repr(arg).rstrip("Ll")
            if typen == "Float" or typen == "Long":
                rstr += typen[0]
            return rstr
        else:
            return self.ref(ind)

    def methodhandle_notref(self, ind):
        typen, args = self.pool[ind]
        code = rhandle_codes[args[0]]
        return code + ' ' + self.ref(args[1])

    def invokedynamic_notref(self, ind):
        typen, args = self.pool[ind]
        bs_args = self.bootstrap_methods[args[0]]

        parts = [self.methodhandle_notref(bs_args[0])]
        parts += map(self.ref, bs_args[1:])
        parts += [':', self.multiref(args[1])]
        return ' '.join(parts)

    def printConstDefs(self, add):
        defs = {}

        while self.used:
            temp, self.used = self.used, set()
            for ind in temp:
                if ind in defs:
                    continue
                typen = self.pool[ind][0]
                defs[ind] = self.cpref_table[typen](ind)

        for ind in sorted(defs):
            add('.const [_{}] = {} {}'.format(ind, self.pool[ind][0], defs[ind]))

def getAttributeTriples(obj): #name_ind, name, data
    return [(name_ind, name, data1) for (name_ind, data1), (name, data2) in zip(obj.attributes_raw, obj.attributes)]

def getAttributesDict(obj):
    d = collections.defaultdict(list)
    for ind, name, attr in getAttributeTriples(obj):
        d[name].append((ind, attr))
    return d

fmt_lookup = {k:v.format for k,v in assembler.op_structs.items()}
def getInstruction(b, getlbl, poolm):
    pos = b.off
    op = b.get('B')

    name = instructions.allinstructions[op]
    if name == 'wide':
        name2 = instructions.allinstructions[b.get('B')]
        if name2 == 'iinc':
            args = list(b.get('>Hh'))
        else:
            args = [b.get('>H')]

        parts = [name, name2] + map(str, args)
        return '\t' + ' '.join(parts)
    elif name == 'tableswitch' or name == 'lookupswitch':
        padding = assembler.getPadding(pos)
        b.getRaw(padding)

        default = getlbl(b.get('>i')+pos)

        if name == 'lookupswitch':
            num = b.get('>I')
            entries = ['\t'+name]
            entries += ['\t\t{} : {}'.format(b.get('>i'), getlbl(b.get('>i')+pos)) for _ in range(num)]
        else:
            low, high = b.get('>ii')
            num = high-low+1
            entries = ['\t{} {}'.format(name, low)]
            entries += ['\t\t{}'.format(getlbl(b.get('>i')+pos)) for _ in range(num)]
        entries += ['\t\tdefault : {}'.format(default)]
        return '\n'.join(entries)
    else:
        args = list(b.get(fmt_lookup[name], forceTuple=True))
        #remove extra padding 0
        if name in ('invokeinterface','invokedynamic'):
            args = args[:-1]

        funcs = {
                'OP_CLASS': poolm.classref,
                'OP_CLASS_INT': poolm.classref,
                'OP_FIELD': poolm.notjasref, #this is a special case due to the jasmin thing
                'OP_METHOD': poolm.multiref,
                'OP_METHOD_INT': poolm.multiref,
                'OP_DYNAMIC': poolm.ref,
                'OP_LDC1': poolm.ldc,
                'OP_LDC2': poolm.ldc,
                'OP_NEWARR': rnewarr_codes.get,
            }

        token_t = tokenize.wordget[name]
        if token_t == 'OP_LBL':
            assert(len(args) == 1)
            args[0] = getlbl(args[0]+pos)
        elif token_t in funcs:
            args[0] = funcs[token_t](args[0])

        parts = [name] + map(str, args)
        return '\t' + ' '.join(parts)

def disMethodCode(code, add, poolm):
    if code is None:
        return
    add('\t; method code size: {} bytes'.format(code.codelen))
    add('\t.limit stack {}'.format(code.stack))
    add('\t.limit locals {}'.format(code.locals))

    lbls = set()
    def getlbl(x):
        lbls.add(x)
        return 'L'+str(x)

    for e in code.except_raw:
        parts = poolm.classref(e.type_ind), getlbl(e.start), getlbl(e.end), getlbl(e.handler)
        add('\t.catch {} from {} to {} using {}'.format(*parts))

    code_attributes = getAttributesDict(code)
    frames = getStackMapTable(code_attributes, poolm, getlbl)

    instrs = []
    b = binUnpacker(code.bytecode_raw)
    while b.size():
        instrs.append((b.off, getInstruction(b, getlbl, poolm)))
    instrs.append((b.off, None))

    for off, instr in instrs:
        if off in lbls:
            add('L{}:'.format(off))
        if off in frames:
            add(frames[off])
        if instr:
            add(instr)

    #Generic code attributes
    for name in code_attributes:
        #We can't disassemble these because Jasmin's format for these attributes
        #is overly cumbersome and not easy to disassemble into, but we can't just
        #leave them as binary blobs either as they are verified by the JVM and the
        #later two contain constant pool references which won't be preserved even
        #if the bytecode isn't changed. For now, we just ommit them entirely.
        #TODO - find a better solution
        if name in ("LineNumberTable","LocalVariableTable","LocalVariableTypeTable"):
            continue

        for name_ind, attr in code_attributes[name]:
            add('.codeattribute {} {!r}'.format(poolm.utfref(name_ind), attr))

def getVerificationType(bytes_, poolm, getLbl):
    s = codes.vt_keywords[bytes_.get('>B')]
    if s == 'Object':
        s += ' ' + poolm.classref(bytes_.get('>H'))
    elif s == 'Uninitialized':
        s += ' ' + getLbl(bytes_.get('>H'))
    return s

def getStackMapTable(code_attributes, poolm, getLbl):
    smt_attrs = code_attributes['StackMapTable']

    frames = {}
    offset = 0

    if smt_attrs:
        assert(len(smt_attrs) == 1)
        bytes_ = binUnpacker(smt_attrs.pop()[1])
        count = bytes_.get('>H')
        getVT = lambda: getVerificationType(bytes_, poolm, getLbl)

        for _ in range(count):
            tag = bytes_.get('>B')
            header, contents = None, []

            if 0 <= tag <= 63:
                offset += tag
                header = 'same'
            elif 64 <= tag <= 127:
                offset += tag - 64
                header = 'same_locals_1_stack_item'
                contents.append('\tstack ' + getVT())
            elif tag == 247:
                offset += bytes_.get('>H')
                header = 'same_locals_1_stack_item_extended'
                contents.append('\tstack ' + getVT())
            elif 248 <= tag <= 250:
                offset += bytes_.get('>H')
                header = 'chop ' + str(251-tag)
            elif tag == 251:
                offset += bytes_.get('>H')
                header = 'same_extended'
            elif 252 <= tag <= 254:
                offset += bytes_.get('>H')
                header = 'append'
                contents.append('\tlocals ' + ' '.join(getVT() for _ in range(tag-251)))
            elif tag == 255:
                offset += bytes_.get('>H')
                header = 'full'
                local_count = bytes_.get('>H')
                contents.append('\tlocals ' + ' '.join(getVT() for _ in range(local_count)))
                stack_count = bytes_.get('>H')
                contents.append('\tstack ' + ' '.join(getVT() for _ in range(stack_count)))

            if contents:
                contents.append('.end stack')
            contents = ['.stack ' + header] + contents
            frame = '\n'.join(contents)
            frames[offset] = frame
            offset += 1 #frames after the first have an offset one larger than the listed offset
    return frames

def disCFMAttribute(name_ind, name, bytes_, add, poolm):
    for vis in ('Visible', 'Invisible'):
        if name == 'Runtime{}Annotations'.format(vis):
            count = bytes_.get('>H')
            for _ in range(count):
                disAnnotation(bytes_, '.runtime{} '.format(vis.lower()), add, poolm, '')
            if count: #otherwise we'll create an empty generic attribute
                return

    if name == "Signature":
        add('.signature {}'.format(poolm.utfref(bytes_.get('>H'))))
        return
    #Create generic attribute if it can't be represented by a standard directive
    add('.attribute {} {!r}'.format(poolm.utfref(name_ind), bytes_.getRaw(bytes_.size())))

def disMethodAttribute(name_ind, name, bytes_, add, poolm):
    if name == 'Code':
        return
    elif name == 'AnnotationDefault':
        disElementValue(bytes_, '.annotationdefault ', add, poolm, '')
        return
    elif name == 'Exceptions':
        count = bytes_.get('>H')
        for _ in range(count):
            add('.throws ' + poolm.classref(bytes_.get('>H')))
        if count: #otherwise we'll create an empty generic attribute
            return

    for vis in ('Visible', 'Invisible'):
        if name == 'Runtime{}ParameterAnnotations'.format(vis):
            for i in range(bytes_.get('>B')):
                for _ in range(bytes_.get('>H')):
                    disAnnotation(bytes_, '.runtime{} parameter {} '.format(vis.lower(), i), add, poolm, '')
            return #generic fallback on empty list not yet supported

    disCFMAttribute(name_ind, name, bytes_, add, poolm)

def disMethod(method, add, poolm):
    mflags = ' '.join(map(str.lower, method.flags))
    add('.method {} {} : {}'.format(mflags, poolm.utfref(method.name_id), poolm.utfref(method.desc_id)))

    for name_ind, name, attr in getAttributeTriples(method):
        disMethodAttribute(name_ind, name, binUnpacker(attr), add, poolm)

    disMethodCode(method.code, add, poolm)
    add('.end method')

def _disEVorAnnotationSub(bytes_, add, poolm, isAnnot, init_prefix, init_indent):
    C_ANNOT, C_ANNOT2, C_ANNOT3, C_EV, C_EV2 = range(5)
    init_callt = C_ANNOT if isAnnot else C_EV

    stack = [(init_callt, init_prefix, init_indent)]
    while stack:
        callt, prefix, indent = stack.pop()

        if callt == C_ANNOT:
            add(indent + prefix + 'annotation ' + poolm.utfref(bytes_.get('>H')))
            #ones we want to happen last should be first on the stack. Annot3 is the final call which ends the annotation
            stack.append((C_ANNOT3, None, indent))
            stack.extend([(C_ANNOT2, None, indent)] * bytes_.get('>H'))

        elif callt == C_ANNOT2:
            key = poolm.utfref(bytes_.get('>H'))
            stack.append((C_EV, key + ' = ', indent+'\t'))

        elif callt == C_ANNOT3:
            add(indent + '.end annotation')

        elif callt == C_EV:
            tag = codes.et_rtags[bytes_.getRaw(1)]
            if tag == 'annotation':
                stack.append((C_ANNOT, prefix, indent + '\t'))
            else:
                if tag in ('byte','char','double','int','float','long','short','boolean','string'):
                    val = poolm.ldc(bytes_.get('>H'))
                elif tag == 'class':
                    val = poolm.utfref(bytes_.get('>H'))
                elif tag == 'enum':
                    val = poolm.utfref(bytes_.get('>H')) + ' ' + poolm.utfref(bytes_.get('>H'))
                elif tag == 'array':
                    val = ''

                add(indent + '{} {} {}'.format(prefix, tag, val))
                if tag == 'array':
                    for _ in range(bytes_.get('>H')):
                        stack.append((C_EV, '', indent+'\t'))
                    stack.append((C_EV2, None, indent))

        elif callt == C_EV2:
            add(indent + '.end array')

def disElementValue(bytes_, prefix, add, poolm, indent):
    _disEVorAnnotationSub(bytes_, add, poolm, False, prefix, indent)

def disAnnotation(bytes_, prefix, add, poolm, indent):
    _disEVorAnnotationSub(bytes_, add, poolm, True, prefix, indent)

#Todo - make fields automatically unpack this themselves
def getConstValue(field):
    if not field.static:
        return None
    const_attrs = [attr for attr in field.attributes if attr[0] == 'ConstantValue']
    if const_attrs:
        assert(len(const_attrs) == 1)
        bytes_ = binUnpacker(const_attrs[0][1])
        return bytes_.get('>H')

_classflags = [(v,k.lower()) for k,v in ClassFile.flagVals.items()]
def disInnerClassesAttribute(name_ind, length, bytes_, add, poolm):
    count = bytes_.get('>H')

    if length != 2+8*count:
        add('.innerlength {}'.format(length))

    for _ in range(count):
        inner, outer, innername, flagbits = bytes_.get('>HHHH')

        flags = [v for k,v in _classflags if k&flagbits]
        inner = poolm.classref(inner)
        outer = poolm.classref(outer)
        innername = poolm.utfref(innername)

        add('.inner {} {} {} {}'.format(' '.join(flags), innername, inner, outer))

    if not count:
        add('.attribute InnerClasses "\\0\\0"')

def disOtherClassAttribute(name_ind, name, bytes_, add, poolm):
    assert(name != 'InnerClasses')
    if name == 'EnclosingMethod':
        cls, nat = bytes_.get('>HH')
        add('.enclosing method {} {}'.format(poolm.classref(cls), poolm.multiref(nat)))
        return
    disCFMAttribute(name_ind, name, bytes_, add, poolm)

def disassemble(cls):
    lines = []
    add = lines.append
    poolm = PoolManager(cls.cpool)

    # def add(s): print s
    add('.version {0[0]} {0[1]}'.format(cls.version))

    class_attributes = getAttributesDict(cls)
    if 'SourceFile' in class_attributes:
        bytes_ = binUnpacker(class_attributes['SourceFile'].pop()[1])
        val_ind = bytes_.get('>H')
        add('.source {}'.format(poolm.utfref(val_ind)))

    if 'BootstrapMethods' in class_attributes:
        bytes_ = binUnpacker(class_attributes['BootstrapMethods'].pop()[1])
        count = bytes_.get('>H')
        for _ in range(count):
            arg1, argc = bytes_.get('>HH')
            args = (arg1,) + bytes_.get('>'+'H'*argc, forceTuple=True)
            poolm.bootstrap_methods.append(args)

    cflags = ' '.join(map(str.lower, cls.flags))
    add('.class {} {}'.format(cflags, poolm.classref(cls.this)))
    add('.super {}'.format(poolm.classref(cls.super)))
    for ii in cls.interfaces_raw:
        add('.implements {}'.format(poolm.classref(ii)))

    for name in class_attributes:
        if name == "InnerClasses":
            assert(len(class_attributes[name]) == 1)
            for name_ind, (length, attr) in class_attributes[name]:
                disInnerClassesAttribute(name_ind, length, binUnpacker(attr), add, poolm)
        else:
            for name_ind, attr in class_attributes[name]:
                disOtherClassAttribute(name_ind, name, binUnpacker(attr), add, poolm)

    add('')
    for field in cls.fields:
        fflags = ' '.join(map(str.lower, field.flags))
        const = getConstValue(field)

        if const is not None:
            add('.field {} {} {} = {}'.format(fflags, poolm.utfref(field.name_id), poolm.utfref(field.desc_id), poolm.ldc(const)))
        else:
            add('.field {} {} {}'.format(fflags, poolm.utfref(field.name_id), poolm.utfref(field.desc_id)))

        facount = 0
        for name_ind, name, attr in getAttributeTriples(field):
            if name == 'ConstantValue' and field.static:
                continue
            disMethodAttribute(name_ind, name, binUnpacker(attr), add, poolm)
            facount += 1
        if facount > 0:
            add('.end field')
            add('')

    add('')

    for method in cls.methods:
        disMethod(method, add, poolm)
        add('')

    poolm.printConstDefs(add)
    return '\n'.join(lines)
########NEW FILE########
__FILENAME__ = instructions
instrs_noarg = ('nop', 'aconst_null', 'iconst_m1', 'iconst_0', 'iconst_1', 'iconst_2', 'iconst_3', 'iconst_4', 'iconst_5', 'lconst_0', 'lconst_1', 'fconst_0', 'fconst_1', 'fconst_2', 'dconst_0', 'dconst_1', 'iload_0', 'iload_1', 'iload_2', 'iload_3', 'lload_0', 'lload_1', 'lload_2', 'lload_3', 'fload_0', 'fload_1', 'fload_2', 'fload_3', 'dload_0', 'dload_1', 'dload_2', 'dload_3', 'aload_0', 'aload_1', 'aload_2', 'aload_3', 'iaload', 'laload', 'faload', 'daload', 'aaload', 'baload', 'caload', 'saload', 'istore_0', 'istore_1', 'istore_2', 'istore_3', 'lstore_0', 'lstore_1', 'lstore_2', 'lstore_3', 'fstore_0', 'fstore_1', 'fstore_2', 'fstore_3', 'dstore_0', 'dstore_1', 'dstore_2', 'dstore_3', 'astore_0', 'astore_1', 'astore_2', 'astore_3', 'iastore', 'lastore', 'fastore', 'dastore', 'aastore', 'bastore', 'castore', 'sastore', 'pop', 'pop2', 'dup', 'dup_x1', 'dup_x2', 'dup2', 'dup2_x1', 'dup2_x2', 'swap', 'iadd', 'ladd', 'fadd', 'dadd', 'isub', 'lsub', 'fsub', 'dsub', 'imul', 'lmul', 'fmul', 'dmul', 'idiv', 'ldiv', 'fdiv', 'ddiv', 'irem', 'lrem', 'frem', 'drem', 'ineg', 'lneg', 'fneg', 'dneg', 'ishl', 'lshl', 'ishr', 'lshr', 'iushr', 'lushr', 'iand', 'land', 'ior', 'lor', 'ixor', 'lxor', 'i2l', 'i2f', 'i2d', 'l2i', 'l2f', 'l2d', 'f2i', 'f2l', 'f2d', 'd2i', 'd2l', 'd2f', 'i2b', 'i2c', 'i2s', 'lcmp', 'fcmpl', 'fcmpg', 'dcmpl', 'dcmpg', 'ireturn', 'lreturn', 'freturn', 'dreturn', 'areturn', 'return', 'arraylength', 'athrow', 'monitorenter', 'monitorexit')

instrs_int = ('bipush', 'sipush', 'iload', 'lload', 'fload', 'dload', 'aload', 'istore', 'lstore', 'fstore', 'dstore', 'astore', 'ret')

instrs_lbl = ('ifeq', 'ifne', 'iflt', 'ifge', 'ifgt', 'ifle', 'if_icmpeq', 'if_icmpne', 'if_icmplt', 'if_icmpge', 'if_icmpgt', 'if_icmple', 'if_acmpeq', 'if_acmpne', 'goto', 'jsr', 'ifnull', 'ifnonnull', 'goto_w', 'jsr_w')

instrs_cp = ('ldc', 'ldc_w', 'ldc2_w', 'getstatic', 'putstatic', 'getfield', 'putfield', 'invokevirtual', 'invokespecial', 'invokestatic', 'invokedynamic', 'new', 'anewarray', 'checkcast', 'instanceof')

instrs_other = ('iinc', 'tableswitch', 'lookupswitch', 'invokeinterface', 'newarray', 'wide', 'multianewarray')

allinstructions = ('nop', 'aconst_null', 'iconst_m1', 'iconst_0', 'iconst_1', 'iconst_2', 'iconst_3', 'iconst_4', 'iconst_5', 'lconst_0', 'lconst_1', 'fconst_0', 'fconst_1', 'fconst_2', 'dconst_0', 'dconst_1', 'bipush', 'sipush', 'ldc', 'ldc_w', 'ldc2_w', 'iload', 'lload', 'fload', 'dload', 'aload', 'iload_0', 'iload_1', 'iload_2', 'iload_3', 'lload_0', 'lload_1', 'lload_2', 'lload_3', 'fload_0', 'fload_1', 'fload_2', 'fload_3', 'dload_0', 'dload_1', 'dload_2', 'dload_3', 'aload_0', 'aload_1', 'aload_2', 'aload_3', 'iaload', 'laload', 'faload', 'daload', 'aaload', 'baload', 'caload', 'saload', 'istore', 'lstore', 'fstore', 'dstore', 'astore', 'istore_0', 'istore_1', 'istore_2', 'istore_3', 'lstore_0', 'lstore_1', 'lstore_2', 'lstore_3', 'fstore_0', 'fstore_1', 'fstore_2', 'fstore_3', 'dstore_0', 'dstore_1', 'dstore_2', 'dstore_3', 'astore_0', 'astore_1', 'astore_2', 'astore_3', 'iastore', 'lastore', 'fastore', 'dastore', 'aastore', 'bastore', 'castore', 'sastore', 'pop', 'pop2', 'dup', 'dup_x1', 'dup_x2', 'dup2', 'dup2_x1', 'dup2_x2', 'swap', 'iadd', 'ladd', 'fadd', 'dadd', 'isub', 'lsub', 'fsub', 'dsub', 'imul', 'lmul', 'fmul', 'dmul', 'idiv', 'ldiv', 'fdiv', 'ddiv', 'irem', 'lrem', 'frem', 'drem', 'ineg', 'lneg', 'fneg', 'dneg', 'ishl', 'lshl', 'ishr', 'lshr', 'iushr', 'lushr', 'iand', 'land', 'ior', 'lor', 'ixor', 'lxor', 'iinc', 'i2l', 'i2f', 'i2d', 'l2i', 'l2f', 'l2d', 'f2i', 'f2l', 'f2d', 'd2i', 'd2l', 'd2f', 'i2b', 'i2c', 'i2s', 'lcmp', 'fcmpl', 'fcmpg', 'dcmpl', 'dcmpg', 'ifeq', 'ifne', 'iflt', 'ifge', 'ifgt', 'ifle', 'if_icmpeq', 'if_icmpne', 'if_icmplt', 'if_icmpge', 'if_icmpgt', 'if_icmple', 'if_acmpeq', 'if_acmpne', 'goto', 'jsr', 'ret', 'tableswitch', 'lookupswitch', 'ireturn', 'lreturn', 'freturn', 'dreturn', 'areturn', 'return', 'getstatic', 'putstatic', 'getfield', 'putfield', 'invokevirtual', 'invokespecial','invokestatic', 'invokeinterface', 'invokedynamic', 'new', 'newarray', 'anewarray', 'arraylength', 'athrow', 'checkcast', 'instanceof', 'monitorenter', 'monitorexit', 'wide', 'multianewarray', 'ifnull', 'ifnonnull', 'goto_w', 'jsr_w')
########NEW FILE########
__FILENAME__ = parse
import ast, struct
import itertools

from ..classfile import ClassFile
from ..method import Method
from ..field import Field

#Important to import tokens here even though it appears unused, as ply uses it
from .tokenize import tokens, wordget, flags
from .assembler import PoolRef

#Specify the starting symbol
start = 'top'

###############################################################################
name_counter = itertools.count()
def addRule(func, name, *rhs_rules):
    def _inner(p):
        func(p)
    _inner.__doc__ = name + ' : ' + '\n| '.join(rhs_rules)
    fname = 'p_{}'.format(next(name_counter))
    globals()[fname] = _inner

def list_sub(p):p[0] = p[1] + p[2:]
def listRule(name): #returns a list
    name2 = name + 's'
    addRule(list_sub, name2, '{} {}'.format(name2, name), 'empty')    

def nothing(p):pass
def assign1(p):p[0] = p[1]
def assign2(p):p[0] = p[2]
def upper1(p): p[0] = p[1].upper()

# Common Rules ################################################################
addRule(nothing, 'sep', 'sep NEWLINE', 'NEWLINE')

def p_empty(p):
    'empty :'
    p[0] = []

def p_intl(p):
    '''intl : INT_LITERAL'''
    p[0] = ast.literal_eval(p[1])

def p_longl(p):
    '''longl : LONG_LITERAL'''
    p[0] = ast.literal_eval(p[1][:-1])

#Todo - find a better way of handling floats
def parseFloat(s):
    s = s[:-1]
    if s.strip('-')[:2].lower() == '0x':
        f = float.fromhex(s)
    else:
        f = float(s)
    return struct.unpack('>i', struct.pack('>f', f))[0]

def parseDouble(s):
    if s.strip('-')[:2].lower() == '0x':
        f = float.fromhex(s)
    else:
        f = float(s)
    return struct.unpack('>q', struct.pack('>d', f))[0]

def p_floatl(p):
    '''floatl : FLOAT_LITERAL'''
    p[0] = parseFloat(p[1])
def p_doublel(p):
    '''doublel : DOUBLE_LITERAL'''
    p[0] = parseDouble(p[1])

#We can allow keywords as inline classnames as long as they aren't flag names
#which would be ambiguous. We don't allow directives to simplfy the grammar
#rules, since they wouldn't be valid identifiers anyway.
badwords = frozenset(map(str.lower, flags))
badwords |= frozenset(k for k in wordget if '.' in k) 
oktokens = frozenset(v for k,v in wordget.items() if k not in badwords)
addRule(assign1, 'notflag', 'WORD', 'STRING_LITERAL', *oktokens)

def p_ref(p):
    '''ref : CPINDEX'''
    s = p[1][1:-1]
    try:
        i = int(s)
        if 0 <= i <= 0xFFFF:
            p[0] = PoolRef(index=i)
        else:
            p[0] = PoolRef(lbl=s)    
    except ValueError:
        p[0] = PoolRef(lbl=s)

def p_utf8_notref(p):
    '''utf8_notref : notflag'''
    p[0] = PoolRef('Utf8', p[1])

def p_class_notref(p):
    '''class_notref : utf8_notref'''
    p[0] = PoolRef('Class', p[1])

def p_string_notref(p):
    '''string_notref : utf8_notref'''
    p[0] = PoolRef('String', p[1])

def p_nat_notref(p):
    '''nameandtype_notref : utf8ref utf8ref'''
    p[0] = PoolRef('NameAndType', p[1], p[2])

def p_field_notref(p):
    '''field_notref : classref nameandtyperef'''
    p[0] = PoolRef('Field', p[1], p[2])

def p_method_notref(p):
    '''method_notref : classref nameandtyperef'''
    p[0] = PoolRef('Method', p[1], p[2])

def p_imethod_notref(p):
    '''interfacemethod_notref : classref nameandtyperef'''
    p[0] = PoolRef('InterfaceMethod', p[1], p[2])

#constant pool types related to InvokeDynamic handled later

for _name in ('utf8','class', 'nameandtype', 'method', 'interfacemethod', 'methodhandle'):
    addRule(assign1, '{}ref'.format(_name), '{}_notref'.format(_name), 'ref')

###############################################################################
def p_classnoend(p):
    '''classnoend : version_opt class_directive_lines classdec superdec interfacedecs class_directive_lines topitems'''
    p[0] = tuple(p[1:])

addRule(assign1, 'classwithend', 'classnoend D_END CLASS sep')
listRule('classwithend')

def p_top(p):
    '''top : sep classwithends classnoend'''
    p[0] = p[2] + [p[3]]
#case where all classes have an end
addRule(assign2, 'top', 'sep classwithends')

def p_version(p):
    '''version_opt : D_VERSION intl intl sep'''
    p[0] = p[2], p[3]
addRule(assign1, 'version_opt', 'empty')

###############################################################################
for c, type_ in zip('cmf', (ClassFile, Method, Field)):
    _name = "{}flag".format(c)
    addRule(upper1, _name, *list(type_.flagVals))
    listRule(_name)

def p_classdec(p):
    '''classdec : D_CLASS cflags classref sep 
                | D_INTERFACE cflags classref sep'''
    #if interface, add interface to flags
    p[0] = (p[1] == '.interface'), p[2], p[3]

addRule(assign2, 'superdec', 'D_SUPER classref sep')
addRule(assign2, 'interfacedec', 'D_IMPLEMENTS classref sep')
listRule('interfacedec')

addRule(assign1, 'class_directive', 'classattribute', 'innerlength_dir')
addRule(assign1, 'class_directive_line', 'class_directive sep')
listRule('class_directive_line')

def p_topitem_c(p):
    '''topitem : const_spec'''
    p[0] = 'const', p[1]
def p_topitem_f(p):
    '''topitem : field_spec'''
    p[0] = 'field', p[1]
def p_topitem_m(p):
    '''topitem : method_spec'''
    p[0] = 'method', p[1]
listRule('topitem')

###############################################################################
#invoke dynamic stuff
from .codes import handle_codes
_handle_token_types = set(wordget.get(x, 'WORD') for x in handle_codes)
def p_handle(p):
    p[0] = handle_codes[p[1]]
p_handle.__doc__ = "handlecode : " + '\n| '.join(_handle_token_types)

#The second argument's type depends on the code, so we require an explicit reference for simplicity
def p_methodhandle_notref(p):
    '''methodhandle_notref : handlecode ref'''
    p[0] = PoolRef('MethodHandle', p[1], p[2])

def p_methodtype_notref(p):
    '''methodtype_notref : utf8_notref'''
    p[0] = PoolRef('Methodtype', p[1])

addRule(assign1, 'bootstrap_arg', 'ref') #TODO - allow inline constants and strings?
listRule('bootstrap_arg')

def p_invokedynamic_notref(p):
    '''invokedynamic_notref : methodhandleref bootstrap_args COLON nameandtyperef'''
    args = [p[1]] + p[2] + [p[4]]
    p[0] = PoolRef('InvokeDynamic', *args)

###############################################################################
def p_const_spec(p):
    '''const_spec : D_CONST ref EQUALS const_rhs sep'''
    p[0] = p[2], p[4]

def assignPoolSingle(typen):
    def inner(p):
        p[0] = PoolRef(typen, p[2])
    return inner

addRule(assign1, 'const_rhs', 'ref')
for tt in ['UTF8', 'CLASS','STRING','NAMEANDTYPE','FIELD','METHOD','INTERFACEMETHOD',
            'METHODHANDLE','METHODTYPE','INVOKEDYNAMIC']:
    addRule(assign2, 'const_rhs', '{} {}_notref'.format(tt, tt.lower()))

#these are special cases, since they take a single argument
#and the notref version can't have a ref as its argument due to ambiguity
for ptype in ('Class','String','MethodType'):
    addRule(assignPoolSingle(ptype), 'const_rhs', ptype.upper() + ' ref')

for ptype in ('Int','Float','Long','Double'):
    addRule(assignPoolSingle(ptype), 'const_rhs', '{} {}l'.format(ptype.upper(), ptype.lower()))
###############################################################################


def p_field_spec(p):
    '''field_spec : D_FIELD fflags utf8ref utf8ref field_constval fieldattribute_list'''
    p[0] = p[2:7]

addRule(nothing, 'field_constval', 'empty')
addRule(assign2, 'field_constval', 'EQUALS ref', 
                                    'EQUALS ldc1_notref', 
                                    'EQUALS ldc2_notref')

#Sadly, we must only allow .end field when at least one attribute is specified
#in order to avoid grammatical ambiguity. JasminXT does not share this problem
#because it lacks the .end class syntax which causes the conflict
def p_field_attrlist1(p):
    '''field_al_nonempty : fieldattribute sep field_al_nonempty'''
    p[0] = [p[1]]+ p[3]
def p_field_attrlist2(p):
    '''field_al_nonempty : fieldattribute sep D_END FIELD sep'''
    p[0] = [p[1]]

addRule(assign2, 'fieldattribute_list', 'sep field_al_nonempty', 'sep empty')


def p_method_spec(p):
    '''method_spec : defmethod statements endmethod'''
    p[0] = p[1],p[2]

def p_defmethod_0(p):
    '''defmethod : D_METHOD mflags jas_meth_namedesc sep'''
    p[0] = p[2],p[3] 
def p_defmethod_1(p):
    '''defmethod : D_METHOD mflags utf8ref COLON utf8ref sep'''
    p[0] = p[2],(p[3], p[5]) 

def p_jas_meth_namedesc(p):
    '''jas_meth_namedesc : WORD'''
    name, paren, desc = p[1].rpartition('(')
    name = PoolRef('Utf8', name)
    desc = PoolRef('Utf8', paren+desc)
    p[0] = name, desc
addRule(nothing, 'endmethod', 'D_END METHOD sep')

def p_statement_0(p):
    '''statement : method_directive sep'''
    p[0] = False, p[1]
def p_statement_1(p):
    '''statement : code_directive sep'''
    p[0] = True, (False, p[1])
def p_statement_2(p):
    '''statement : empty instruction sep 
                | lbldec instruction sep
                | lbldec sep'''
    p[0] = True, (True, ((p[1] or None), p[2]))
listRule('statement')

addRule(assign1, 'lbldec', 'lbl COLON')
addRule(assign1, 'method_directive', 'methodattribute')
addRule(assign1, 'code_directive', 'limit_dir', 'except_dir','localvar_dir','linenumber_dir','stack_dir', 'generic_codeattribute_dir')

def p_limit_dir(p):
    '''limit_dir : D_LIMIT LOCALS intl 
                | D_LIMIT STACK intl'''
    p[0] = p[1], (p[2], p[3])

def p_except_dir(p):
    '''except_dir : D_CATCH classref FROM lbl TO lbl USING lbl'''
    p[0] = p[1], (p[2], p[4], p[6], p[8])

def p_linenumber_dir(p):
    '''linenumber_dir : D_LINE intl'''
    p[0] = p[1], p[2]

def p_localvar_dir(p):
    '''localvar_dir : D_VAR intl IS utf8ref utf8ref FROM lbl TO lbl'''
    p[0] = p[1], (p[2], p[4], p[5], p[7], p[9])

def p_instruction(p):
    '''instruction : OP_NONE
                    | OP_INT intl
                    | OP_INT_INT intl intl
                    | OP_LBL lbl
                    | OP_FIELD fieldref_or_jas
                    | OP_METHOD methodref_or_jas
                    | OP_METHOD_INT imethodref_or_jas intl
                    | OP_DYNAMIC ref
                    | OP_CLASS classref
                    | OP_CLASS_INT classref intl
                    | OP_LDC1 ldc1_ref
                    | OP_LDC2 ldc2_ref
                    | OP_NEWARR nacode
                    | OP_LOOKUPSWITCH luswitch
                    | OP_TABLESWITCH tblswitch
                    | OP_WIDE wide_instr
                    '''
    if p[1] == 'invokenonvirtual':
        p[1] = 'invokespecial'
    p[0] = tuple(p[1:])
    #these instructions have 0 padding at the end
    #this is kind of an ungly hack, but the best way I could think of
    if p[1] in ('invokeinterface','invokedynamic'):
        p[0] += (0,)

addRule(assign1, 'lbl', 'WORD')
addRule(assign1, 'fieldref_or_jas', 'jas_fieldref', 'ref', 'inline_fieldref')
def p_jas_fieldref(p):
    '''jas_fieldref : WORD WORD'''
    class_, sep, name = p[1].replace('.','/').rpartition('/')

    desc = PoolRef('Utf8', p[2])
    class_ = PoolRef('Class', PoolRef('Utf8', class_))
    name = PoolRef('Utf8', name)
    nt = PoolRef('NameAndType', name, desc)
    p[0] = PoolRef('Field', class_, nt)

#This is an ugly hack to work around the fact that Jasmin syntax would otherwise be impossible to 
#handle with a LALR(1) parser
def p_inline_fieldref_1(p):
    '''inline_fieldref : WORD nameandtyperef
                        | STRING_LITERAL nameandtyperef'''
    class_ = PoolRef('Class', PoolRef('Utf8', p[1]))
    p[0] = PoolRef('Field', class_, p[2])
def p_inline_fieldref_2(p):
    '''inline_fieldref : ref nameandtyperef'''
    p[0] = PoolRef('Field', p[1], p[2])


def p_jas_meth_classnamedesc(p):
    '''jas_methodref : WORD'''
    name, paren, desc = p[1].rpartition('(')
    class_, sep, name = name.replace('.','/').rpartition('/')
    desc = paren + desc

    class_ = PoolRef('Class', PoolRef('Utf8', class_))
    nt = PoolRef('NameAndType', PoolRef('Utf8', name), PoolRef('Utf8', desc))
    p[0] = class_, nt

addRule(assign1, 'methodref_or_jas', 'methodref')
def p_methodref_or_jas(p):
    '''methodref_or_jas : jas_methodref'''
    p[0] = PoolRef('Method', *p[1])

addRule(assign1, 'imethodref_or_jas', 'interfacemethodref')
def p_imethodref_or_jas(p):
    '''imethodref_or_jas : jas_methodref'''
    p[0] = PoolRef('InterfaceMethod', *p[1])


from .codes import newarr_codes
_newarr_token_types = set(wordget.get(x, 'WORD') for x in newarr_codes)
def p_nacode(p):
    p[0] = newarr_codes[p[1]]
p_nacode.__doc__ = "nacode : " + '\n| '.join(_newarr_token_types)

addRule(assign1, 'ldc1_ref', 'ldc1_notref', 'ref')
def p_ldc1_notref_string(p):
    '''ldc1_notref : STRING_LITERAL'''
    p[0] = PoolRef('String', PoolRef('Utf8', p[1]))
def p_ldc1_notref_int(p):
    '''ldc1_notref : intl'''
    p[0] = PoolRef('Int', p[1])
def p_ldc1_notref_float(p):
    '''ldc1_notref : floatl'''
    p[0] = PoolRef('Float', p[1])

addRule(assign1, 'ldc2_ref', 'ldc2_notref', 'ref')
def p_ldc2_notref_long(p):
    '''ldc2_notref : longl'''
    p[0] = PoolRef('Long', p[1])
def p_ldc2_notref_double(p):
    '''ldc2_notref : doublel'''
    p[0] = PoolRef('Double', p[1])

def p_defaultentry(p):
    '''defaultentry : DEFAULT COLON lbl'''
    p[0] = p[3]

def p_luentry(p):
    '''luentry : intl COLON lbl sep'''
    p[0] = p[1], p[3]
listRule('luentry')

addRule(assign1, 'tblentry', 'lbl sep')
listRule('tblentry')

def p_lookupswitch(p):
    '''luswitch : empty sep luentrys defaultentry'''
    p[0] = p[1], p[3], p[4]

def p_tableswitch(p):
    '''tblswitch : intl sep tblentrys defaultentry'''
    p[0] = p[1], p[3], p[4]

def p_wide_instr(p):
    '''wide_instr : OP_INT intl
                | OP_INT_INT intl intl'''
    p[0] = p[1], tuple(p[2:])

#######################################################################
# Explicit Attributes
addRule(assign1, 'cfmattribute', 'annotation_dir', 'signature_dir', 'generic_attribute_dir')
addRule(assign1, 'classattribute', 'cfmattribute', 'sourcefile_dir', 'inner_dir', 'enclosing_dir')
addRule(assign1, 'fieldattribute', 'cfmattribute')
addRule(assign1, 'methodattribute', 'cfmattribute', 'throws_dir', 'annotation_param_dir', 'annotation_def_dir')

#Class, field, method
def p_annotation_dir(p):
    '''annotation_dir : D_RUNTIMEVISIBLE annotation
                    | D_RUNTIMEINVISIBLE annotation'''
    p[0] = p[1], (None, p[2])

def p_signature_dir(p):
    '''signature_dir : D_SIGNATURE utf8ref'''
    p[0] = p[1], p[2]

#Class only
def p_sourcefile_dir(p):
    '''sourcefile_dir : D_SOURCE utf8ref'''
    p[0] = p[1], p[2]

def p_inner_dir(p): 
    '''inner_dir : D_INNER cflags utf8ref classref classref'''
    p[0] = p[1], (p[4],p[5],p[3],p[2]) #use JasminXT's (flags, name, inner, outer) order but switch internally to correct order

def p_enclosing_dir(p): 
    '''enclosing_dir : D_ENCLOSING METHOD classref nameandtyperef'''
    p[0] = p[1], (p[3], p[4])

#This is included here even though strictly speaking, it's not an attribute. Rather it's a directive that affects the assembly
#of the InnerClasses attribute
def p_innerlength_dir(p): 
    '''innerlength_dir : D_INNERLENGTH intl'''
    p[0] = p[1], p[2]


#Method only
def p_throws_dir(p):
    '''throws_dir : D_THROWS classref'''
    p[0] = p[1], p[2]

def p_annotation_param_dir(p):
    '''annotation_param_dir : D_RUNTIMEVISIBLE PARAMETER intl annotation
                           | D_RUNTIMEINVISIBLE PARAMETER intl annotation'''
    p[0] = p[1], (p[3], p[4])
def p_annotation_def_dir(p):
    '''annotation_def_dir : D_ANNOTATIONDEFAULT element_value'''
    p[0] = p[1], p[2]

#Generic
def p_generic_attribute_dir(p): 
    '''generic_attribute_dir : D_ATTRIBUTE utf8ref STRING_LITERAL'''
    p[0] = p[1], (p[2], p[3])

def p_generic_codeattribute_dir(p): 
    '''generic_codeattribute_dir : D_CODEATTRIBUTE utf8ref STRING_LITERAL'''
    p[0] = p[1], (p[2], p[3])

#######################################################################
#Stack map stuff
addRule(nothing, 'endstack', 'D_END STACK') #directives are not expected to end with a sep

def assign1All(p):p[0] = tuple(p[1:])
addRule(assign1All, 'verification_type', 'TOP', 'INTEGER', 'FLOAT', 'DOUBLE', 'LONG', 'NULL', 'UNINITIALIZEDTHIS',
                                        'OBJECT classref', 'UNINITIALIZED lbl')
listRule('verification_type')
addRule(assign2, 'locals_vtlist', 'LOCALS verification_types sep')
addRule(assign2, 'stack_vtlist', 'STACK verification_types sep')

def p_stack_dir(p):
    '''stack_dir_rest : SAME 
                    | SAME_EXTENDED
                    | CHOP intl 
                    | SAME_LOCALS_1_STACK_ITEM sep stack_vtlist endstack
                    | SAME_LOCALS_1_STACK_ITEM_EXTENDED sep stack_vtlist endstack
                    | APPEND sep locals_vtlist endstack
                    | FULL sep locals_vtlist stack_vtlist endstack'''
    p[0] = '.stackmap', tuple(p[1:])
addRule(assign2, 'stack_dir', 'D_STACK stack_dir_rest')
#######################################################################
#Annotation stuff
from .codes import et_tags
primtags = set(wordget.get(x, 'WORD') for x in 'byte char double int float long short boolean string'.split())
addRule(assign1, 'primtag', *primtags)
addRule(assign1, 'ldc_any', 'ldc1_notref', 'ldc2_notref', 'ref')

def p_element_value_0(p):
    '''element_value : primtag ldc_any
                    | CLASS utf8ref
                    | ENUM utf8ref utf8ref
                    | ARRAY sep element_array'''
    p[0] = et_tags[p[1]], tuple(p[2:])
def p_element_value_1(p):
    '''element_value : annotation'''
    p[0] = '@', (p[1],)

addRule(assign1, 'element_value_line', 'element_value sep')
listRule('element_value_line')
addRule(assign1, 'element_array', 'element_value_lines D_END ARRAY')

def p_key_ev_line(p):
    '''key_ev_line : utf8ref EQUALS element_value_line'''
    p[0] = p[1], p[3]
listRule('key_ev_line')

def p_annotation(p):
    '''annotation : ANNOTATION utf8ref sep key_ev_lines D_END ANNOTATION'''
    p[0] = p[2], p[4]
#######################################################################

def p_error(p):
    if p is None:
        print "Syntax error: unexpected EOF"
    else: #remember to subtract 1 from line number since we had a newline at the start of the file
        print "Syntax error at line {}: unexpected token {!r}".format(p.lineno-1, p.value)
    
    #Ugly hack since Ply doesn't provide any useful error information
    import inspect
    frame = inspect.currentframe()
    cvars = frame.f_back.f_locals
    print 'Expected:', ', '.join(cvars['actions'][cvars['state']].keys())
    print 'Found:', cvars['ltype']
    print 'Current stack:', cvars['symstack']

    #Discard the rest of the input so that Ply doesn't attempt error recovery
    from ply import yacc
    tok = yacc.token()
    while tok is not None:
        tok = yacc.token()

def makeParser(**kwargs):
    from ply import yacc
    return yacc.yacc(**kwargs)
########NEW FILE########
__FILENAME__ = tokenize
import ast

from ..classfile import ClassFile
from ..method import Method
from ..field import Field
from .. import constant_pool
from . import instructions as ins
from . import codes

directives = 'CLASS','INTERFACE','SUPER','IMPLEMENTS','CONST','FIELD','METHOD','END','LIMIT','CATCH','SOURCE','LINE','VAR','THROWS',
directives += 'VERSION', 'STACK', 'RUNTIMEVISIBLE', 'RUNTIMEINVISIBLE', 'ANNOTATIONDEFAULT', 'INNER', 'ENCLOSING', 'SIGNATURE', 
directives += 'ATTRIBUTE', 'CODEATTRIBUTE', 'INNERLENGTH'
keywords = ['CLASS','METHOD','FIELD','LOCALS','STACK','FROM','TO','USING','DEFAULT','IS']
keywords += ['SAME','SAME_LOCALS_1_STACK_ITEM','SAME_LOCALS_1_STACK_ITEM_EXTENDED','CHOP','SAME_EXTENDED','APPEND','FULL']
keywords += ['ANNOTATION','ARRAY','PARAMETER']
flags = ClassFile.flagVals.keys() + Method.flagVals.keys() + Field.flagVals.keys()

lowwords = set().union(keywords, flags)
casewords = set().union(codes.vt_keywords, constant_pool.name2Type.keys())

wordget = {}
wordget.update({w.lower():w.upper() for w in lowwords})
wordget.update({w:w.upper() for w in casewords})
wordget.update({'.'+w.lower():'D_'+w for w in directives})

assert(set(wordget).isdisjoint(ins.allinstructions))
for op in ins.instrs_noarg:
    wordget[op] = 'OP_NONE'
for op in ins.instrs_int:
    wordget[op] = 'OP_INT'
for op in ins.instrs_lbl:
    wordget[op] = 'OP_LBL'
for op in ('getstatic', 'putstatic', 'getfield', 'putfield'):
    wordget[op] = 'OP_FIELD'
#support invokenonvirtual for backwards compatibility with Jasmin
for op in ('invokevirtual', 'invokespecial', 'invokestatic', 'invokenonvirtual'): 
    wordget[op] = 'OP_METHOD'
for op in ('new', 'anewarray', 'checkcast', 'instanceof'):
    wordget[op] = 'OP_CLASS'
for op in ('wide','lookupswitch','tableswitch'):
    wordget[op] = 'OP_' + op.upper()

wordget['ldc'] = 'OP_LDC1'
wordget['ldc_w'] = 'OP_LDC1'
wordget['ldc2_w'] = 'OP_LDC2'
wordget['iinc'] = 'OP_INT_INT'
wordget['newarray'] = 'OP_NEWARR'
wordget['multianewarray'] = 'OP_CLASS_INT'
wordget['invokeinterface'] = 'OP_METHOD_INT'
wordget['invokedynamic'] = 'OP_DYNAMIC'

for op in ins.allinstructions:
    wordget.setdefault(op,op.upper())

#special PLY value
tokens = ('NEWLINE', 'COLON', 'EQUALS', 'WORD', 'CPINDEX', 
    'STRING_LITERAL', 'INT_LITERAL', 'LONG_LITERAL', 'FLOAT_LITERAL', 'DOUBLE_LITERAL') + tuple(set(wordget.values()))

def t_ignore_COMMENT(t):
    r';.*'

# Define a rule so we can track line numbers
def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    return t

def t_STRING_LITERAL(t):
    # See http://stackoverflow.com/questions/430759/regex-for-managing-escaped-characters-for-items-like-string-literals/5455705#5455705
    r'''[uUbB]?[rR]?(?:
        """[^"\\]*              # any number of unescaped characters
            (?:\\.[^"\\]*       # escaped followed by 0 or more unescaped
                |"[^"\\]+       # single quote followed by at least one unescaped
                |""[^"\\]+      # two quotes followed by at least one unescaped
            )*"""
        |"[^"\n\\]*              # any number of unescaped characters
            (?:\\.[^"\n\\]*      # escaped followed by 0 or more unescaped
            )*"
    '''r"""                     # concatenated string literals
        |'''[^'\\]*              # any number of unescaped characters
            (?:\\.[^'\\]*       # escaped followed by 0 or more unescaped
                |'[^'\\]+       # single quote followed by at least one unescaped
                |''[^'\\]+      # two quotes followed by at least one unescaped
            )*'''
        |'[^'\n\\]*              # any number of unescaped characters
            (?:\\.[^'\n\\]*      # escaped followed by 0 or more unescaped
            )*'
        )"""

    t.value = ast.literal_eval(t.value)
    return t

#careful here: | is not greedy so hex must come first
int_base = r'[+-]?(?:0[xX][0-9a-fA-F]+|[0-9]+)'
float_base = r'''(?:
    [Nn][Aa][Nn]|                                       #Nan
    [-+]?(?:                                            #Inf and normal both use sign
        [Ii][Nn][Ff]|                                   #Inf
        \d+\.\d*(?:[eE][+-]?\d+)?|                         #decimal float
        \d+[eE][+-]?\d+|                                   #decimal float with no fraction (exponent mandatory)
        0[xX][0-9a-fA-F]*\.[0-9a-fA-F]+[pP][+-]?\d+        #hexidecimal float
        )
    )
'''

#Sadly there's no nice way to define these even with reflection hacks
#Hopefully we can get Ply patched some day or fork it or something so 
#it's not so much of a pain

#These are matched in order of appearence (specifically, f.func_code.co_firstlineno)
#So anything that can be a prefix of another must go last
def t_FLOAT_LITERAL(t): return t
t_FLOAT_LITERAL.__doc__ = float_base + r'[fF]'
def t_DOUBLE_LITERAL(t): return t
t_DOUBLE_LITERAL.__doc__ = float_base
def t_LONG_LITERAL(t): return t
t_LONG_LITERAL.__doc__ = int_base + r'[lL]'
def t_INT_LITERAL(t): return t
t_INT_LITERAL.__doc__ = int_base

def t_CPINDEX(t): return t
t_CPINDEX.__doc__ = r'\[[0-9a-z_]+\]'


def t_WORD(t):
    r'''[^\s:="']+'''
    t.type = wordget.get(t.value, 'WORD')
    return t

t_COLON = r':'
t_EQUALS = r'='
t_ignore = ' \t\r'

def t_error(t):
    print 'Parser error on line {} at {}'.format(t.lexer.lineno, t.lexer.lexpos)
    print t.value[:79]

def makeLexer(**kwargs):
    from ply import lex
    return lex.lex(**kwargs)
########NEW FILE########
__FILENAME__ = attributes_raw
def get_attribute_raw(bytestream, ic_indices):
    name_ind, length = bytestream.get('>HL')

    #Hotspot does not actually check the attribute length of InnerClasses prior to 49.0
    #so this case requires special handling. We will keep the purported length of the 
    #attribute so that it can be displayed in the disassembly. For InnerClass attributes
    #data is actually a (length, bytes) tuple, rather than storing the bytes directly
    if name_ind in ic_indices:
        count = bytestream.get('>H', peek=True)
        data = length, bytestream.getRaw(2+8*count)
    else:
        data = bytestream.getRaw(length)
    
    return name_ind,data

def get_attributes_raw(bytestream, ic_indices=()):
    attribute_count = bytestream.get('>H')
    return [get_attribute_raw(bytestream, ic_indices) for _ in range(attribute_count)]

def fixAttributeNames(attributes_raw, cpool):
    return [(cpool.getArgsCheck('Utf8', name_ind), data) for name_ind, data in attributes_raw]

########NEW FILE########
__FILENAME__ = binUnpacker
import struct

class binUnpacker(object):
    def __init__(self, data="", fileName=""):
        if fileName:
            self.bytes = open(fileName,'rb').read()
        else:
            self.bytes = data
        self.off = 0

    def get(self, fmt, forceTuple=False, peek=False):       
        val = struct.unpack_from(fmt, self.bytes, self.off)
        
        if not peek:
            self.off += struct.calcsize(fmt)
        if not forceTuple and len(val) == 1:
            val = val[0]
        return val

    def getRaw(self, num):
        val = self.bytes[self.off:self.off+num]
        self.off += num
        return val

    def size(self):
        return len(self.bytes) - self.off

########NEW FILE########
__FILENAME__ = bytecode
from __future__ import division
from Krakatau import opnames

def parseInstructions(bytestream, isConstructor):
    data = bytestream
    assert(data.off == 0)
    
    instructions = {}
    while data.size() > 0:
        address = data.off
        inst = getNextInstruction(data, address)

        #replace constructor invocations with synthetic op invokeinit to simplfy things later
        if inst[0] == opnames.INVOKESPECIAL and isConstructor(inst[1]):
            inst = (opnames.INVOKEINIT,) + inst[1:]

        instructions[address] = inst
    assert(data.size() == 0)    
    return instructions

simpleOps = {0x00:opnames.NOP, 0x01:opnames.CONSTNULL, 0x94:opnames.LCMP,
             0xbe:opnames.ARRLEN, 0xbf:opnames.THROW, 0xc2:opnames.MONENTER, 
             0xc3:opnames.MONEXIT, 0x57:opnames.POP, 0x58:opnames.POP2, 0x59:opnames.DUP, 
             0x5a:opnames.DUPX1, 0x5b:opnames.DUPX2, 0x5c:opnames.DUP2,
             0x5d:opnames.DUP2X1, 0x5e:opnames.DUP2X2, 0x5f:opnames.SWAP}

singleIndexOps = {0xb2:opnames.GETSTATIC,0xb3:opnames.PUTSTATIC,0xb4:opnames.GETFIELD,
            0xb5:opnames.PUTFIELD,0xb6:opnames.INVOKEVIRTUAL,0xb7:opnames.INVOKESPECIAL,
            0xb8:opnames.INVOKESTATIC, 0xbb:opnames.NEW,0xbd:opnames.ANEWARRAY,
            0xc0:opnames.CHECKCAST,0xc1:opnames.INSTANCEOF}

def getNextInstruction(data, address):
    byte = data.get('>B')

    #typecode - B,C,S, and Bool are only used for array types and sign extension
    A,B,C,D,F,I,L,S = "ABCDFIJS"
    Bool = "Z"

    if byte in simpleOps:
        inst = (simpleOps[byte],)
    elif byte in singleIndexOps:
        inst = (singleIndexOps[byte], data.get('>H'))
    elif byte <= 0x11:
        op = opnames.CONST
        if byte <= 0x08:
            t, val = I, byte - 0x03
        elif byte <= 0x0a:
            t, val = L, byte - 0x09
        elif byte <= 0x0d:
            t, val = F, float(byte - 0x0b)
        elif byte <= 0x0f:
            t, val = D, float(byte - 0x0e)
        elif byte == 0x10:
            t, val = I, data.get('>b')
        else:
            t, val = I, data.get('>h')
        inst = op, t, val
    elif byte == 0x12:
        inst = opnames.LDC, data.get('>B'), 1
    elif byte == 0x13:
        inst = opnames.LDC, data.get('>H'), 1
    elif byte == 0x14:
        inst = opnames.LDC, data.get('>H'), 2
    elif byte <= 0x2d:
        op = opnames.LOAD
        if byte <= 0x19:
            t = [I,L,F,D,A][byte - 0x15]
            val = data.get('>B')
        else:
            temp = byte - 0x1a
            t = [I,L,F,D,A][temp // 4]
            val = temp % 4
        inst = op, t, val
    elif byte <= 0x35:
        op = opnames.ARRLOAD
        t = [I,L,F,D,A,B,C,S][byte - 0x2e]
        inst = (op, t) if t != A else (opnames.ARRLOAD_OBJ,) #split object case into seperate op name to simplify things later
    elif byte <= 0x4e:
        op = opnames.STORE
        if byte <= 0x3a:
            t = [I,L,F,D,A][byte - 0x36]
            val = data.get('>B')
        else:
            temp = byte - 0x3b
            t = [I,L,F,D,A][temp // 4]
            val = temp % 4
        inst = op, t, val
    elif byte <= 0x56:
        op = opnames.ARRSTORE
        t = [I,L,F,D,A,B,C,S][byte - 0x4f]
        inst = (op, t) if t != A else (opnames.ARRSTORE_OBJ,) #split object case into seperate op name to simplify things later
    elif byte <= 0x77:
        temp = byte - 0x60
        opt = (opnames.ADD,opnames.SUB,opnames.MUL,opnames.DIV,opnames.REM,opnames.NEG)[temp//4]
        t = (I,L,F,D)[temp % 4]
        inst = opt, t
    elif byte <= 0x83:
        temp = byte - 0x78
        opt = (opnames.SHL,opnames.SHR,opnames.USHR,opnames.AND,opnames.OR,opnames.XOR)[temp//2]
        t = (I,L)[temp % 2]
        inst = opt, t        
    elif byte == 0x84:
        inst = opnames.IINC, data.get('>B'), data.get('>b')
    elif byte <= 0x90:
        op = opnames.CONVERT
        pairs = ((I,L),(I,F),(I,D),(L,I),(L,F),(L,D),(F,I),(F,L),(F,D),
                (D,I),(D,L),(D,F))
        src_t, dest_t = pairs[byte - 0x85]
        inst = op, src_t, dest_t
    elif byte <= 0x93:
        op = opnames.TRUNCATE
        dest_t = [B,C,S][byte - 0x91]
        inst = op, dest_t
    elif byte <= 0x98:
        op = opnames.FCMP
        temp = byte - 0x95
        t = (F,D)[temp//2]
        NaN_val = (-1,1)[temp % 2]
        inst = op, t, NaN_val
    elif byte <= 0x9e:
        op = opnames.IF_I
        cmp_t = ('eq','ne','lt','ge','gt','le')[byte - 0x99]
        jumptarget = data.get('>h') + address
        inst = op, cmp_t, jumptarget
    elif byte <= 0xa4:
        op = opnames.IF_ICMP
        cmp_t = ('eq','ne','lt','ge','gt','le')[byte - 0x9f]
        jumptarget = data.get('>h') + address
        inst = op, cmp_t, jumptarget
    elif byte <= 0xa6:
        op = opnames.IF_ACMP
        cmp_t = ('eq','ne')[byte - 0xa5]
        jumptarget = data.get('>h') + address
        inst = op, cmp_t, jumptarget
    elif byte == 0xa7:
        inst = opnames.GOTO, data.get('>h') + address
    elif byte == 0xa8:
        inst = opnames.JSR, data.get('>h') + address
    elif byte == 0xa9:
        inst = opnames.RET, data.get('>B')
    elif byte == 0xaa: #Table Switch
        padding = (3-address) % 4
        padding = data.getRaw(padding)
        #OpenJDK requires padding to be 0
        default = data.get('>i') + address
        low = data.get('>i')
        high = data.get('>i')
        assert(high >= low)
        numpairs = high - low + 1
        offsets = [data.get('>i') + address for _ in range(numpairs)]
        jumps = zip(range(low, high+1), offsets)
        inst = opnames.SWITCH, default, jumps, padding
    elif byte == 0xab: #Lookup Switch
        padding = (3-address) % 4
        padding = data.getRaw(padding)
        #OpenJDK requires padding to be 0
        default = data.get('>i') + address
        numpairs = data.get('>i')
        assert(numpairs >= 0)
        pairs = [data.get('>ii') for _ in range(numpairs)]
        keys = [k for k,v in pairs]
        jumps = [(x,(y + address)) for x,y in pairs]
        inst = opnames.SWITCH, default, jumps, padding
    elif byte <= 0xb1:
        op = opnames.RETURN
        t = (I,L,F,D,A,None)[byte - 0xac]
        inst = op, t 
    elif byte == 0xb9:
        op = opnames.INVOKEINTERFACE
        index = data.get('>H')
        count, zero = data.get('>B'), data.get('>B')
        inst = op, index, count, zero
    elif byte == 0xba:
        op = opnames.INVOKEDYNAMIC
        index = data.get('>H')
        zero = data.get('>H')
        inst = op, index, zero
    elif byte == 0xbc:
        typecode = data.get('>b')
        types = {4:Bool, 5:C, 6:F, 7:D, 8:B, 9:S, 10:I, 11:L}
        t = types.get(typecode)
        inst = opnames.NEWARRAY, t
    elif byte == 0xc4: #wide
        realbyte = data.get('>B')
        if realbyte >= 0x15 and realbyte < 0x1a:
            t = [I,L,F,D,A][realbyte - 0x15]
            inst = opnames.LOAD, t, data.get('>H')
        elif realbyte >= 0x36 and realbyte < 0x3b:
            t = [I,L,F,D,A][realbyte - 0x36]
            inst = opnames.STORE, t, data.get('>H')            
        elif realbyte == 0xa9:
            inst = opnames.RET, data.get('>H')
        elif realbyte == 0x84:
            inst = opnames.IINC, data.get('>H'), data.get('>h')
        else:
            assert(0)                
    elif byte == 0xc5:
        op = opnames.MULTINEWARRAY
        index = data.get('>H')
        dim = data.get('>B')
        inst = op, index, dim
    elif byte <= 0xc7:
        op = opnames.IF_A
        cmp_t = ('eq','ne')[byte - 0xc6]
        jumptarget = data.get('>h') + address
        inst = op, cmp_t, jumptarget 
    elif byte == 0xc8:
        inst = opnames.GOTO, data.get('>i') + address
    elif byte == 0xc9:
        inst = opnames.JSR, data.get('>i') + address
    else:
        assert(0)
    return inst

def printInstruction(instr):
    if len(instr) == 1:
        return instr[0]
    elif len(instr) == 2:
        return '{}({})'.format(*instr)
    else:
        return '{}{}'.format(instr[0], instr[1:])
########NEW FILE########
__FILENAME__ = classfile
from . import constant_pool, method, field
from .attributes_raw import get_attributes_raw, fixAttributeNames

cp_structFmts = {3: '>i',
                4: '>i',    #floats and doubles internally represented as integers with same bit pattern
                5: '>q',
                6: '>q',
                7: '>H',
                8: '>H',
                9: '>HH',
                10: '>HH',
                11: '>HH',
                12: '>HH',
                15: '>BH',
                16: '>H',
                18: '>HH'}

def get_cp_raw(bytestream):
    const_count = bytestream.get('>H')
    assert(const_count > 1)

    placeholder = None,None
    pool = [placeholder]

    while len(pool) < const_count:
        tag = bytestream.get('B')
        if tag == 1: #utf8
            length = bytestream.get('>H')
            data = bytestream.getRaw(length)
            val = tag, (data,)
        else:
            val = tag,bytestream.get(cp_structFmts[tag], True)
        pool.append(val)
        #Longs and Doubles take up two spaces in the pool
        if tag == 5 or tag == 6:
            pool.append(placeholder)
    assert(len(pool) == const_count)
    return pool

def get_field_raw(bytestream):
    flags, name, desc = bytestream.get('>HHH')
    attributes = get_attributes_raw(bytestream)
    return flags, name, desc, attributes

def get_fields_raw(bytestream):
    count = bytestream.get('>H')
    return [get_field_raw(bytestream) for _ in range(count)]

#fields and methods have same raw format
get_method_raw = get_field_raw
get_methods_raw = get_fields_raw

class ClassFile(object):
    flagVals = {'PUBLIC':0x0001,
                'FINAL':0x0010,
                'SUPER':0x0020,
                'INTERFACE':0x0200,
                'ABSTRACT':0x0400,
                'SYNTHETIC':0x1000,
                'ANNOTATION':0x2000,
                'ENUM':0x4000,

                # These flags are only used for InnerClasses attributes
                'PRIVATE':0x0002,
                'PROTECTED':0x0004,
                'STATIC':0x0008,
                }

    def __init__(self, bytestream):
        magic, minor, major = bytestream.get('>LHH')
        assert(magic == 0xCAFEBABE)
        self.version = major,minor

        const_pool_raw = get_cp_raw(bytestream)
        flags, self.this, self.super = bytestream.get('>HHH')

        interface_count = bytestream.get('>H')
        self.interfaces_raw = [bytestream.get('>H') for _ in range(interface_count)]

        self.fields_raw = get_fields_raw(bytestream)
        self.methods_raw = get_methods_raw(bytestream)

        ic_indices = [i for i,x in enumerate(const_pool_raw) if x == (1, ("InnerClasses",))]
        self.attributes_raw = get_attributes_raw(bytestream, ic_indices)
        assert(bytestream.size() == 0)

        self.flags = set(name for name,mask in ClassFile.flagVals.items() if (mask & flags))
        self.cpool = constant_pool.ConstPool(const_pool_raw)
        self.name = self.cpool.getArgsCheck('Class', self.this)
        self.elementsLoaded = False

    def loadSupers(self, env, name, subclasses):
        self.env = env
        assert(self.name == name)

        if self.super:
            self.supername = self.cpool.getArgsCheck('Class', self.super)
            # if superclass is cached, we can assume it is free from circular inheritance
            # since it must have been loaded successfully on a previous run
            if not self.env.isCached(self.supername):
                self.env.getClass(self.supername, subclasses + (name,), partial=True)
            self.hierarchy = self.env.getSupers(self.supername) + (self.name,)
        else:
            assert(name == 'java/lang/Object')
            self.supername = None
            self.hierarchy = (self.name,)

    def loadElements(self, keepRaw=False):
        if self.elementsLoaded:
            return
        self.fields = [field.Field(m, self, keepRaw) for m in self.fields_raw]
        self.methods = [method.Method(m, self, keepRaw) for m in self.methods_raw]
        self.attributes = fixAttributeNames(self.attributes_raw, self.cpool)
        del self.fields_raw
        del self.methods_raw
        if not keepRaw:
            del self.attributes_raw
        self.elementsLoaded = True

    def getSuperclassHierarchy(self):
        return self.hierarchy
########NEW FILE########
__FILENAME__ = constant_pool
import struct, collections

#ConstantPool stores strings as strings or unicodes. They are automatically
#converted to and from modified Utf16 when reading and writing to binary

#Floats and Doubles are internally stored as integers with the same bit pattern
#Since using raw floats breaks equality testing for signed zeroes and NaNs
#cpool.getArgs/getArgsCheck will automatically convert them into Python floats

def decodeStr((s,)):
    return s.replace('\xc0\x80','\0').decode('utf8'),
def encodeStr((u,)):
    return u.encode('utf8').replace('\0','\xc0\x80'),
def strToBytes(args):
    s = encodeStr(args)[0]
    return struct.pack('>H',len(s)) + s

def decodeFloat(i):
    return struct.unpack('>f', struct.pack('>i', i)) #Note: returns tuple
def decodeDouble(i):
    return struct.unpack('>d', struct.pack('>q', i))

cpoolInfo_t = collections.namedtuple('cpoolInfo_t',
                                     ['name','tag','recoverArgs','toBytes'])

Utf8 = cpoolInfo_t('Utf8',1,
                  (lambda self,(s,):(s,)),
                  strToBytes)

Class = cpoolInfo_t('Class',7,
                    (lambda self,(n_id,):self.getArgs(n_id)),
                    (lambda (n_id,): struct.pack('>H',n_id)))

NameAndType = cpoolInfo_t('NameAndType',12,
                (lambda self,(n,d):self.getArgs(n) + self.getArgs(d)),
                (lambda (n,d): struct.pack('>HH',n,d)))

Field = cpoolInfo_t('Field',9,
                (lambda self,(c_id, nat_id):self.getArgs(c_id) + self.getArgs(nat_id)),
                (lambda (n,d): struct.pack('>HH',n,d)))

Method = cpoolInfo_t('Method',10,
                (lambda self,(c_id, nat_id):self.getArgs(c_id) + self.getArgs(nat_id)),
                (lambda (n,d): struct.pack('>HH',n,d)))

InterfaceMethod = cpoolInfo_t('InterfaceMethod',11,
                (lambda self,(c_id, nat_id):self.getArgs(c_id) + self.getArgs(nat_id)),
                (lambda (n,d): struct.pack('>HH',n,d)))

String = cpoolInfo_t('String',8,
                (lambda self,(n_id,):self.getArgs(n_id)),
                (lambda (n_id,): struct.pack('>H',n_id)))

Int = cpoolInfo_t('Int',3,
                  (lambda self,(s,):(s,)),
                  (lambda (val,): struct.pack('>i',val)))

Long = cpoolInfo_t('Long',5,
                  (lambda self,(s,):(s,)),
                  (lambda (val,): struct.pack('>q',val)))

Float = cpoolInfo_t('Float',4,
                  (lambda self,(s,):decodeFloat(s)),
                  (lambda (val,): struct.pack('>i',val)))

Double = cpoolInfo_t('Double',6,
                  (lambda self,(s,):decodeDouble(s)),
                  (lambda (val,): struct.pack('>q',val)))

MethodHandle = cpoolInfo_t('MethodHandle',15,
                (lambda self,(t, n_id):(t,)+self.getArgs(n_id)),
                (lambda (t, n_id): struct.pack('>BH',t, n_id)))

MethodType = cpoolInfo_t('MethodType',16,
                (lambda self,(n_id,):self.getArgs(n_id)),
                (lambda (n_id,): struct.pack('>H',n_id)))

InvokeDynamic = cpoolInfo_t('InvokeDynamic',18,
                (lambda self,(bs_id, nat_id):(bs_id,) + self.getArgs(nat_id)),
                (lambda (n,d): struct.pack('>HH',n,d)))

cpoolTypes = [Utf8, Class, NameAndType, Field, Method, InterfaceMethod,
              String, Int, Long, Float, Double, 
              MethodHandle, MethodType, InvokeDynamic]
name2Type = {t.name:t for t in cpoolTypes}
tag2Type = {t.tag:t for t in cpoolTypes}

class ConstPool(object):
    def __init__(self, initialData=((None,None),)):
        self.pool = []
        self.reserved = set()
        self.available = set()

        for tag, val in initialData:
            if tag is None:
                self.addEmptySlot()
            else:
                t = tag2Type[tag]
                if t.name == 'Utf8':
                    val = decodeStr(val)
                self.pool.append((t.name, val))

    def size(self): #Number of slots including gaps, not number of entries
        return len(self.pool)
    def getPoolIter(self):
        return (x for x in self.pool if x[0] is not None)
    def getEnumeratePoolIter(self):
        return ((i,x) for i,x in enumerate(self.pool) if x[0] is not None)

    def addEmptySlot(self):
        self.pool.append((None, None))

    def getAvailableIndex(self):
        if self.available:
            return self.available.pop()
        while len(self.pool) in self.reserved:
            self.addEmptySlot()
        self.addEmptySlot()
        return len(self.pool)-1    

    def getAvailableIndex2(self):
        for i in self.available:
            if i+1 in self.available:
                self.available.remove(i)
                self.available.remove(i+1)
                return i

        while len(self.pool) in self.reserved or len(self.pool)+1 in self.reserved:
            self.addEmptySlot()
        self.addEmptySlot()
        self.addEmptySlot()
        return len(self.pool)-2

    # Special function for assembler
    def addItem(self, item, index=None):
        if index is None and item in self.pool:
            return self.pool.index(item)

        if item[0] == 'Utf8':
            assert(isinstance(item[1][0], basestring))
        cat2 = item[0] in ('Long','Double')

        if index is None:
            index = self.getAvailableIndex2() if cat2 else self.getAvailableIndex()
        else:
            temp = len(self.pool)
            if index >= temp:
                #If desired slot is past the end of current range, add a bunch of placeholder slots
                self.pool += [(None,None)] * (index+1-temp)
                self.available.update(range(temp,index))
                self.available -= self.reserved

            self.reserved.remove(index)
            if cat2:
                self.reserved.remove(index+1)
                self.addEmptySlot()

        assert(index not in self.reserved)
        self.pool[index] = item
        return index

    def copyItem(self, src, index):
        return self.addItem(self.pool[src], index=index)

    # Accessors ######################################################################
    def getArgs(self, i):
        if not (i >= 0 and i<len(self.pool)):
            raise IndexError('Constant pool index {} out of range'.format(i))        
        if self.pool[i][0] is None:
            raise IndexError('Constant pool index {} invalid'.format(i))
        
        name, val = self.pool[i]
        t = name2Type[name]
        return t.recoverArgs(self, val)

    def getArgsCheck(self, typen, index):
        if (self.pool[index][0] != typen):
            raise KeyError('Constant pool index {} has incorrect type {}'.format(index, typen))
        val = self.getArgs(index)
        return val if len(val) > 1 else val[0]

    def getType(self, index): return self.pool[index][0]

    ##################################################################################
    def fillPlaceholders(self):
        #fill in all the placeholder slots with a dummy reference. Class and String items
        #have the smallest size (3 bytes). There should always be an existing class item
        #we can copy
        dummy = next(item for item in self.pool if item[0] == 'Class')
        for i in self.available:
            self.pool[i] = dummy

    def bytes(self):
        parts = []
        pool = self.pool

        assert(not self.reserved)
        self.fillPlaceholders()

        assert(len(pool) <= 65535)
        parts.append(struct.pack('>H',len(pool)))
        
        for name, vals in self.getPoolIter():
            t = name2Type[name]
            parts.append(struct.pack('>B',t.tag))
            parts.append(t.toBytes(vals))
        return ''.join(parts)
########NEW FILE########
__FILENAME__ = environment
import zipfile
import os.path

from Krakatau import binUnpacker
from Krakatau import stdcache
from Krakatau.classfile import ClassFile
from Krakatau.error import ClassLoaderError

class Environment(object):
    def __init__(self):
        self.classes = {}
        self.path = []
        #Cache inheritance hierchies of standard lib classes so we don't have to load them to do subclass testing
        self.cache = stdcache.Cache(self, 'cache.txt')
        self._open = {}

    def addToPath(self, path):
        self.path.append(path)

    def getClass(self, name, subclasses=tuple(), partial=False):
        if name in subclasses:
            raise ClassLoaderError('ClassCircularityError', (name, subclasses))
        try:
            result = self.classes[name]
        except KeyError:
            result = self._loadClass(name, subclasses)
        if not partial:
            result.loadElements()
        return result

    def isSubclass(self, name1, name2):
        return name1 == name2 or (name2 in self.cache.superClasses(name1))
    def getFlags(self, name): return self.cache.flags(name)
    def getSupers(self, name): return self.cache.superClasses(name)
    def isCached(self, name): return self.cache.isCached(name)

    def _searchForFile(self, name):
        name += '.class'
        for place in self.path:
            try:
                archive = self._open[place]
            except KeyError: #plain folder
                try:
                    path = os.path.join(place, name)
                    with open(path, 'rb') as file_:
                        return file_.read()
                except IOError:
                    print 'failed to open', path.encode('utf8')
            else: #zip archive
                try:
                    return archive.read(name)
                except KeyError:
                    pass

    def _loadClass(self, name, subclasses):
        print "Loading", name.encode('utf8')[:70]
        data = self._searchForFile(name)

        if data is None:
            raise ClassLoaderError('ClassNotFoundException', name)

        stream = binUnpacker.binUnpacker(data=data)
        new = ClassFile(stream)
        new.loadSupers(self, name, subclasses)
        self.classes[new.name] = new
        return new

    #Context Manager methods to manager our zipfiles
    def __enter__(self):
        assert(not self._open)
        for place in self.path:
            if place.endswith('.jar') or place.endswith('.zip'):
                self._open[place] = zipfile.ZipFile(place, 'r').__enter__()
        return self

    def __exit__(self, type_, value, traceback):
        for place in reversed(self.path):
            if place in self._open:
                self._open[place].__exit__(type_, value, traceback)
                del self._open[place]
########NEW FILE########
__FILENAME__ = error
class ClassLoaderError(Exception):
    def __init__(self, typen=None, data=""):
        self.type = typen
        self.data = data

        message = u"\n{}: {}".format(typen, data) if typen else unicode(data)
        super(ClassLoaderError, self).__init__(message)

class VerificationError(Exception):
    def __init__(self, message, data=None):
        super(VerificationError, self).__init__(message)
        self.data = data

########NEW FILE########
__FILENAME__ = field
from .attributes_raw import fixAttributeNames

class Field(object):
    flagVals = {'PUBLIC':0x0001,
                'PRIVATE':0x0002,
                'PROTECTED':0x0004,
                'STATIC':0x0008,
                'FINAL':0x0010,
                'VOLATILE':0x0040,
                'TRANSIENT':0x0080,
                'SYNTHETIC':0x1000, 
                'ENUM':0x4000,
                }

    def __init__(self, data, classFile, keepRaw):
        self.class_ = classFile
        cpool = self.class_.cpool
        
        flags, name_id, desc_id, attributes_raw = data

        self.name = cpool.getArgsCheck('Utf8', name_id)
        self.descriptor = cpool.getArgsCheck('Utf8', desc_id)
        self.attributes = fixAttributeNames(attributes_raw, cpool)

        self.flags = set(name for name,mask in Field.flagVals.items() if (mask & flags))
        self.static = 'STATIC' in self.flags
        if keepRaw:
            self.attributes_raw = attributes_raw
            self.name_id, self.desc_id = name_id, desc_id
########NEW FILE########
__FILENAME__ = floatutil
import math
INF_MAG = 1, None
ZERO_MAG = 0, None

#Numbers are represented as (sign, (mantissa, exponent))
#For finite nonzero values, the float value is sign * mantissa * 2 ^ (exponent - mbits - 1)
#Mantissa is normalized to always be within (2 ^ mbits) <= m < (2 ^ mbits + 1) even for subnormal numbers
NAN = None,(None,None)
INF = 1,INF_MAG
NINF = -1,INF_MAG
ZERO = 1,ZERO_MAG
NZERO = -1,ZERO_MAG

#Key suitable for sorting finite (normalized) nonzero values
sortkey = lambda (s,(m,e)):(s,s*e,s*m)

#Size info for type - mantissa bits, min exponent, max exponent
FLOAT_SIZE = 23,-126,127
DOUBLE_SIZE = 52,-1022,1023

def flog(x):
    '''returns f such that 2**f <= x < 2**(f+1)'''
    assert(x > 0)
    return len(bin(x))-3

def roundMag(size, mag):
    '''Round (unnormalized) magnitude to nearest representable magnitude with ties going to 0 lsb'''
    mbits, emin, emax = size
    m, e = mag
    assert(m >= 1)
    f = flog(m)

    if e+f < emin: #subnormal
        dnmin = emin - mbits
        if e+f < (dnmin - 1):
            return ZERO_MAG
        if e > dnmin:
            m = m << (e - dnmin)
            f += (e - dnmin)
            e = dnmin
        s = dnmin - e
        i = m >> s
        r = (m - (i << s)) * 2
        h = 1 << s
        if r > h or r == h and (i&1):
            i += 1
        return i, e+s-mbits-1
    else:
        if f < mbits:
            m = m << (mbits - f)
            f = mbits
        s = f - mbits
        if (e+f) > emax:
            return INF_MAG
        i = m >> s
        r = (m - (i << s)) * 2
        h = 1 << s
        if r > h or r == h and (i&1):
            i += 1
            if i == (1<<mbits):
                i = i >> 1
                e += 1
                if e > emax:
                    return INF_MAG
        return i, e+s-mbits-1

def fromRawFloat(size, x):
    if math.isnan(x):
        return NAN
    sign = int(math.copysign(1, x))
    x = math.copysign(x, 1)
    
    if math.isinf(x):
        return sign, INF_MAG
    elif x == 0.0:
        return sign, ZERO_MAG
    else: 
        m, e = math.frexp(x)
        m = int(m * (1<<(size[0]+1)))
        return sign, roundMag(size, (m, e))

def toRawFloat(val):
    s,(m,e) = val
    if e is None:
        if val == NAN:
            return float('NaN')
        x = float('inf') if m else 0.0
    else:
        x = math.ldexp(m,e)
    return math.copysign(x, s)
########NEW FILE########
__FILENAME__ = graph_util
import itertools

def tarjanSCC(roots, getChildren):
    """Return a list of strongly connected components in a graph. If getParents is passed instead of getChildren, the result will be topologically sorted.

    roots - list of root nodes to search from
    getChildren - function which returns children of a given node
    """

    sccs = []
    indexCounter = itertools.count()
    index = {}
    lowlink = {}
    removed = set()
    subtree = []

    #Use iterative version to avoid stack limits for large datasets
    stack = [(node, 0) for node in roots]
    while stack:
        current, state = stack.pop()
        if state == 0: #before recursing
            if current not in index: #if it's in index, it was already visited (possibly earlier on the current search stack)
                lowlink[current] = index[current] = next(indexCounter)
                subtree.append(current)

                stack.append((current, 1))
                stack.extend((child, 0) for child in getChildren(current) if child not in removed)
        else: #after recursing
            children = [child for child in getChildren(current) if child not in removed]
            for child in children:
                if index[child] <= index[current]: #backedge (or selfedge)
                    lowlink[current] = min(lowlink[current], index[child])
                else:
                    lowlink[current] = min(lowlink[current], lowlink[child])
                assert(lowlink[current] <= index[current])

            if index[current] == lowlink[current]:
                scc = []
                while not scc or scc[-1] != current:
                    scc.append(subtree.pop())

                sccs.append(tuple(scc))
                removed.update(scc)
    return sccs

def topologicalSort(roots, getParents):
    """Return a topological sorting of nodes in a graph.

    roots - list of root nodes to search from
    getParents - function which returns the parents of a given node
    """

    results = []
    visited = set()

    #Use iterative version to avoid stack limits for large datasets
    stack = [(node,0) for node in roots]
    while stack:
        current, state = stack.pop()
        if state == 0: #before recursing
            if current not in visited:
                visited.add(current)
                stack.append((current,1))
                stack.extend((parent,0) for parent in getParents(current))
        else: #after recursing
            assert(current in visited)
            results.append(current)
    return results
########NEW FILE########
__FILENAME__ = ast
import itertools, math

from ..ssa import objtypes
from .stringescape import escapeString
# from ..ssa.constraints import ValueType

class VariableDeclarator(object):
    def __init__(self, typename, identifier): self.typename = typename; self.local = identifier

    def print_(self):
        return '{} {}'.format(self.typename.print_(), self.local.print_())

#############################################################################################################################################

class JavaStatement(object):
    expr = None #provide default for subclasses that don't have an expression
    def getScopes(self): return ()

    def addCastsAndParens(self, env):
        if self.expr is not None:
            self.expr.addCasts(env)
            self.expr.addParens()

class ExpressionStatement(JavaStatement):
    def __init__(self, expr):
        self.expr = expr

    def print_(self): return self.expr.print_() + ';'

class LocalDeclarationStatement(JavaStatement):
    def __init__(self, decl, expr=None):
        self.decl = decl
        self.expr = expr

    def print_(self):
        if self.expr is not None:
            return '{} = {};'.format(self.decl.print_(), self.expr.print_())
        return self.decl.print_() + ';'

    def addCastsAndParens(self, env):
        if self.expr is not None:
            self.expr.addCasts(env)

            if not isJavaAssignable(env, self.expr.dtype, self.decl.typename.tt):
                self.expr = makeCastExpr(self.decl.typename.tt, self.expr, fixEnv=env)
            self.expr.addParens()

class ReturnStatement(JavaStatement):
    def __init__(self, expr=None, tt=None):
        self.expr = expr
        self.tt = tt

    def print_(self): return 'return {};'.format(self.expr.print_()) if self.expr is not None else 'return;'

    def addCastsAndParens(self, env):
        if self.expr is not None:
            self.expr.addCasts(env)
            if not isJavaAssignable(env, self.expr.dtype, self.tt):
                self.expr = makeCastExpr(self.tt, self.expr, fixEnv=env)
            self.expr.addParens()

class ThrowStatement(JavaStatement):
    def __init__(self, expr):
        self.expr = expr
    def print_(self): return 'throw {};'.format(self.expr.print_())

class JumpStatement(JavaStatement):
    def __init__(self, target, isFront):
        keyword = 'continue' if isFront else 'break'
        label = (' ' + target.getLabel()) if target is not None else ''
        self.str = keyword + label + ';'

    def print_(self): return self.str

#Compound Statements
sbcount = itertools.count()
class LazyLabelBase(JavaStatement):
    # Jumps are represented by arbitrary 'keys', currently just the key of the
    # original proxy node. Each item has a continueKey and a breakKey representing
    # the beginning and the point just past the end respectively. breakKey may be
    # None if this item appears at the end of the function and there is nothing after it.
    # Statement blocks have a jump key representing where it jumps to if any. This
    # may be None if the jump is unreachable (such as if there is a throw or return)
    def __init__(self, labelfunc, begink, endk):
        self.label, self.func = None, labelfunc
        self.continueKey = begink
        self.breakKey = endk
        # self.id = next(sbcount) #For debugging purposes

    def getLabel(self):
        if self.label is None:
            self.label = self.func() #Not a bound function!
        return self.label

    def getLabelPrefix(self): return '' if self.label is None else self.label + ': '
    # def getLabelPrefix(self): return self.getLabel() + ': '

    #For debugging
    def __str__(self):
        if isinstance(self, StatementBlock):
            return 'Sb'+str(self.id)
        return type(self).__name__[:3]+str(self.id)
    __repr__ = __str__

class TryStatement(LazyLabelBase):
    def __init__(self, labelfunc, begink, endk, tryb, pairs):
        super(TryStatement, self).__init__(labelfunc, begink, endk)
        self.tryb, self.pairs = tryb, pairs

    def getScopes(self): return (self.tryb,) + zip(*self.pairs)[1]

    def print_(self):
        tryb = self.tryb.print_()
        parts = ['catch({})\n{}'.format(x.print_(), y.print_()) for x,y in self.pairs]
        return '{}try\n{}\n{}'.format(self.getLabelPrefix(), tryb, '\n'.join(parts))

class IfStatement(LazyLabelBase):
    def __init__(self, labelfunc, begink, endk, expr, scopes):
        super(IfStatement, self).__init__(labelfunc, begink, endk)
        self.expr = expr #don't rename without changing how var replacement works!
        self.scopes = scopes
        # assert(len(self.scopes) == 1 or len(self.scopes) == 2)

    def getScopes(self): return self.scopes

    def print_(self):
        lbl = self.getLabelPrefix()
        parts = [self.expr] + list(self.scopes)

        if len(self.scopes) == 1:
            parts = [x.print_() for x in parts]
            return '{}if({})\n{}'.format(lbl, *parts)

        # Special case handling for 'else if'
        sep = '\n' #else seperator depends on if we have else if
        fblock = self.scopes[1]
        if len(fblock.statements) == 1:
            stmt = fblock.statements[-1]
            if isinstance(stmt, IfStatement) and stmt.label is None:
                sep, parts[-1] = ' ', stmt
        parts = [x.print_() for x in parts]
        return '{}if({})\n{}\nelse{sep}{}'.format(lbl, *parts, sep=sep)

class SwitchStatement(LazyLabelBase):
    def __init__(self, labelfunc, begink, endk, expr, pairs):
        super(SwitchStatement, self).__init__(labelfunc, begink, endk)
        self.expr = expr #don't rename without changing how var replacement works!
        self.pairs = pairs

    def getScopes(self): return zip(*self.pairs)[1]
    def hasDefault(self): return None in zip(*self.pairs)[0]

    def print_(self):
        expr = self.expr.print_()

        def printCase(keys):
            if keys is None:
                return 'default: '
            return ''.join(map('case {}: '.format, sorted(keys)))

        bodies = [(printCase(keys) + scope.print_()) for keys, scope in self.pairs]
        if self.pairs[-1][0] is None and len(self.pairs[-1][1].statements) == 0:
            bodies.pop()

        contents = '\n'.join(bodies)
        indented = ['    '+line for line in contents.splitlines()]
        lines = ['{'] + indented + ['}']
        return '{}switch({}){}'.format(self.getLabelPrefix(), expr, '\n'.join(lines))

class WhileStatement(LazyLabelBase):
    def __init__(self, labelfunc, begink, endk, parts):
        super(WhileStatement, self).__init__(labelfunc, begink, endk)
        self.expr = Literal.TRUE
        self.parts = parts
        assert(len(self.parts) == 1)

    def getScopes(self): return self.parts

    def print_(self):
        parts = self.expr.print_(), self.parts[0].print_()
        return '{}while({})\n{}'.format(self.getLabelPrefix(), *parts)

class StatementBlock(LazyLabelBase):
    def __init__(self, labelfunc, begink, endk, statements, jumpk, labelable=True):
        super(StatementBlock, self).__init__(labelfunc, begink, endk)
        self.parent = None #should be assigned later
        self.statements = statements
        self.jumpKey = jumpk
        self.labelable = labelable

    def doesFallthrough(self): return self.jumpKey is None or self.jumpKey == self.breakKey

    def getScopes(self): return self,

    def print_(self):
        assert(self.labelable or self.label is None)
        contents = '\n'.join(x.print_() for x in self.statements)
        indented = ['    '+line for line in contents.splitlines()]
        # indented[:0] = ['    //{}{}'.format(self,x) for x in (self.breakKey, self.continueKey, self.jumpKey)]
        lines = [self.getLabelPrefix() + '{'] + indented + ['}']
        return '\n'.join(lines)

    @staticmethod
    def join(*scopes):
        blists = [s.bases for s in scopes if s is not None] #allow None to represent the universe (top element)
        if not blists:
            return None
        common = [x for x in zip(*blists) if len(set(x)) == 1]
        return common[-1][0]

#Temporary hack
class StringStatement(JavaStatement):
    def __init__(self, s):
        self.s = s
    def print_(self): return self.s

#############################################################################################################################################
_assignable_sprims = '.byte','.short','.char'
_assignable_lprims = '.int','.long','.float','.double'

def isObject(tt):
    return tt == objtypes.NullTT or tt[1] > 0 or not tt[0][0].startswith('.')

def isPrimativeAssignable(fromt, to):
    x, y = fromt[0], to[0]
    if x == y or (x in _assignable_sprims and y in _assignable_lprims):
        return True
    elif (x in _assignable_lprims and y in _assignable_lprims):
        return _assignable_lprims.index(x) <= _assignable_lprims.index(y)
    else:
        return x == '.byte' and y == '.short'

def isJavaAssignable(env, fromt, to):
    if fromt is None or to is None: #this should never happen, except during debugging
        return True

    if isObject(to):
        assert(isObject(fromt))
        #todo - make it check interfaces too
        return objtypes.isSubtype(env, fromt, to)
    else: #allowed if numeric conversion is widening
        return isPrimativeAssignable(fromt, to)

_int_tts = objtypes.LongTT, objtypes.IntTT, objtypes.ShortTT, objtypes.CharTT, objtypes.ByteTT
def makeCastExpr(newtt, expr, fixEnv=None):
    if newtt == expr.dtype:
        return expr

    if isinstance(expr, Literal) and newtt in (objtypes.IntTT, objtypes.BoolTT):
        return Literal(newtt, expr.val)

    if newtt == objtypes.IntTT and expr.dtype == objtypes.BoolTT:
        return Ternary(expr, Literal.ONE, Literal.ZERO)
    elif newtt == objtypes.BoolTT and expr.dtype == objtypes.IntTT:
        return BinaryInfix('!=', (expr, Literal.ZERO), objtypes.BoolTT)

    ret = Cast(TypeName(newtt), expr)
    if fixEnv is not None:
        ret = ret.fix(fixEnv)
    return ret
#############################################################################################################################################
#Precedence:
#    0 - pseudoprimary
#    5 - pseudounary
#    10-19 binary infix
#    20 - ternary
#    21 - assignment
# Associativity: L = Left, R = Right, A = Full

class JavaExpression(object):
    precedence = 0 #Default precedence
    params = () #for subclasses that don't have params

    def complexity(self): return 1 + max(e.complexity() for e in self.params) if self.params else 0

    def postFlatIter(self):
        return itertools.chain([self], *[expr.postFlatIter() for expr in self.params])

    def print_(self):
        return self.fmt.format(*[expr.print_() for expr in self.params])

    def replaceSubExprs(self, rdict):
        if self in rdict:
            return rdict[self]
        self.params = [param.replaceSubExprs(rdict) for param in self.params]
        return self

    def addCasts(self, env):
        for param in self.params:
            param.addCasts(env)
        self.addCasts_sub(env)

    def addCasts_sub(self, env): pass

    def addParens(self):
        for param in self.params:
            param.addParens()
        self.params = list(self.params) #make it easy for children to edit
        self.addParens_sub()

    def addParens_sub(self): pass

    def isLocalAssign(self): return isinstance(self, Assignment) and isinstance(self.params[0], Local)

    def __repr__(self):
        return type(self).__name__.rpartition('.')[-1] + ' ' + self.print_()
    __str__ = __repr__

class ArrayAccess(JavaExpression):
    def __init__(self, *params):
        if params[0].dtype == objtypes.NullTT:
            #Unfortunately, Java doesn't really support array access on null constants
            #So we'll just cast it to Object[] as a hack
            param = makeCastExpr(('java/lang/Object',1), params[0])
            params = param, params[1]

        self.params = params
        self.fmt = '{}[{}]'

    @property
    def dtype(self):
        base, dim = self.params[0].dtype
        assert(dim>0)
        return base, dim-1

    def addParens_sub(self):
        p0 = self.params[0]
        if p0.precedence > 0 or isinstance(p0, ArrayCreation):
            self.params[0] = Parenthesis(p0)

class ArrayCreation(JavaExpression):
    def __init__(self, tt, *sizeargs):
        base, dim = tt
        self.params = (TypeName((base,0)),) + sizeargs
        self.dtype = tt
        assert(dim >= len(sizeargs) > 0)
        self.fmt = 'new {}' + '[{}]'*len(sizeargs) + '[]'*(dim-len(sizeargs))

class Assignment(JavaExpression):
    precedence = 21
    def __init__(self, *params):
        self.params = params
        self.fmt = '{} = {}'

    @property
    def dtype(self): return self.params[0].dtype

    def addCasts_sub(self, env):
        left, right = self.params
        if not isJavaAssignable(env, right.dtype, left.dtype):
            expr = makeCastExpr(left.dtype, right, fixEnv=env)
            self.params = left, expr

_binary_ptable = ['* / %', '+ -', '<< >> >>>',
    '< > <= >= instanceof', '== !=',
    '&', '^', '|', '&&', '||']

binary_precedences = {}
for _ops, _val in zip(_binary_ptable, range(10,20)):
    for _op in _ops.split():
        binary_precedences[_op] = _val

class BinaryInfix(JavaExpression):
    def __init__(self, opstr, params, dtype=None):
        assert(len(params) == 2)
        self.params = params
        self.opstr = opstr
        self.fmt = '{{}} {} {{}}'.format(opstr)
        self._dtype = dtype
        self.precedence = binary_precedences[opstr]

    @property
    def dtype(self): return self.params[0].dtype if self._dtype is None else self._dtype

    def addParens_sub(self):
        myprec = self.precedence
        associative = myprec >= 15 #for now we treat +, *, etc as nonassociative due to floats

        for i, p in enumerate(self.params):
            if p.precedence > myprec:
                self.params[i] = Parenthesis(p)
            elif p.precedence == myprec and i > 0 and not associative:
                self.params[i] = Parenthesis(p)

class Cast(JavaExpression):
    precedence = 5
    def __init__(self, *params):
        self.dtype = params[0].tt
        self.params = params
        self.fmt = '({}){}'

    def fix(self, env):
        tt, expr = self.dtype, self.params[1]
        # "Impossible" casts are a compile error in Java.
        # This can be fixed with an intermediate cast to Object
        if isObject(tt):
            if not isJavaAssignable(env, tt, expr.dtype):
                if not isJavaAssignable(env, expr.dtype, tt):
                    expr = makeCastExpr(objtypes.ObjectTT, expr)
                    self.params = self.params[0], expr
        return self

    def addCasts_sub(self, env): self.fix(env)
    def addParens_sub(self):
        p1 = self.params[1]
        if p1.precedence > 5 or (isinstance(p1, UnaryPrefix) and p1.opstr[0] in '-+'):
            self.params[1] = Parenthesis(p1)

class ClassInstanceCreation(JavaExpression):
    def __init__(self, typename, tts, arguments):
        self.typename, self.tts, self.params = typename, tts, arguments
        self.dtype = typename.tt

    def print_(self):
        return 'new {}({})'.format(self.typename.print_(), ', '.join(x.print_() for x in self.params))

    def addCasts_sub(self, env):
        newparams = []
        for tt, expr in zip(self.tts, self.params):
            if expr.dtype != tt:
                expr = makeCastExpr(tt, expr, fixEnv=env)
            newparams.append(expr)
        self.params = newparams

class FieldAccess(JavaExpression):
    def __init__(self, primary, name, dtype, printLeft=True):
        self.dtype = dtype
        self.params, self.name = [primary], escapeString(name)
        self.fmt = ('{}.' if printLeft else '') + self.name

    def addParens_sub(self):
        p0 = self.params[0]
        if p0.precedence > 0:
            self.params[0] = Parenthesis(p0)

def printFloat(x, isSingle):
    #TODO make this less hackish. We only really need the parens if it's preceded by unary minus
    #note: NaN may have arbitrary sign
    if math.copysign(1.0, x) == -1.0 and not math.isnan(x):
        return '(-{})'.format(printFloat(math.copysign(x, 1.0), isSingle))

    suffix = 'f' if isSingle else ''
    if math.isnan(x):
        return '(0.0{0}/0.0{0})'.format(suffix)
    elif math.isinf(x):
        return '(1.0{0}/0.0{0})'.format(suffix)

    if isSingle and x > 0.0:
        #Try to find more compract representation for floats, since repr treats everything as doubles
        m, e = math.frexp(x)
        half_ulp2 = math.ldexp(1.0, max(e - 25, -150)) #don't bother doubling when near the upper range of a given e value
        half_ulp1 = (half_ulp2/2) if m == 0.5 and e >= -125 else half_ulp2
        lbound, ubound = x-half_ulp1, x+half_ulp2
        assert(lbound < x < ubound)
        s = '{:g}'.format(x).replace('+','')
        if lbound < float(s) < ubound: #strict ineq to avoid potential double rounding issues
            return s + suffix
    return repr(x) + suffix

class Literal(JavaExpression):
    def __init__(self, vartype, val):
        self.dtype = vartype
        self.val = val

        self.str = None
        if vartype == objtypes.StringTT:
            self.str = '"' + escapeString(val) + '"'
        elif vartype == objtypes.IntTT:
            self.str = repr(int(val))
            assert('L' not in self.str) #if it did we were passed an invalid value anyway
        elif vartype == objtypes.LongTT:
            self.str = repr(long(val))
            assert('L' in self.str)
        elif vartype == objtypes.FloatTT or vartype == objtypes.DoubleTT:
            assert(type(val) == float)
            self.str = printFloat(val, vartype == objtypes.FloatTT)
        elif vartype == objtypes.NullTT:
            self.str = 'null'
        elif vartype == objtypes.ClassTT:
            self.params = [TypeName(val)]
            self.fmt = '{}.class'
        elif vartype == objtypes.BoolTT:
            self.str = 'true' if val else 'false'
        else:
            assert(0)

    def print_(self):
        if self.str is None:
            #for printing class literals
            return self.fmt.format(self.params[0].print_())
        return self.str

    def _key(self): return self.dtype, self.val
    def __eq__(self, other): return type(self) == type(other) and self._key() == other._key()
    def __ne__(self, other): return type(self) != type(other) or self._key() != other._key()
    def __hash__(self): return hash(self._key())
Literal.FALSE = Literal(objtypes.BoolTT, 0)
Literal.TRUE = Literal(objtypes.BoolTT, 1)
Literal.N_ONE = Literal(objtypes.IntTT, -1)
Literal.ZERO = Literal(objtypes.IntTT, 0)
Literal.ONE = Literal(objtypes.IntTT, 1)

Literal.LZERO = Literal(objtypes.LongTT, 0)
Literal.FZERO = Literal(objtypes.FloatTT, 0.0)
Literal.DZERO = Literal(objtypes.DoubleTT, 0.0)
Literal.NULL = Literal(objtypes.NullTT, None)

class Local(JavaExpression):
    def __init__(self, vartype, namefunc):
        self.dtype = vartype
        self.name = None
        self.func = namefunc

    def print_(self):
        if self.name is None:
            self.name = self.func(self)
        return self.name

class MethodInvocation(JavaExpression):
    def __init__(self, left, name, tts, arguments, op, dtype):
        if left is None:
            self.params = arguments
        else:
            self.params = [left] + arguments
        self.hasLeft = (left is not None)
        self.dtype = dtype
        self.name = escapeString(name)
        self.tts = tts
        self.op = op #keep around for future reference and new merging

    def print_(self):
        if self.hasLeft:
            left, arguments = self.params[0], self.params[1:]
            return '{}.{}({})'.format(left.print_(), self.name, ', '.join(x.print_() for x in arguments))
        else:
            arguments = self.params
            return '{}({})'.format(self.name, ', '.join(x.print_() for x in arguments))

    def addCasts_sub(self, env):
        newparams = []
        for tt, expr in zip(self.tts, self.params):
            if expr.dtype != tt:
                expr = makeCastExpr(tt, expr, fixEnv=env)
            newparams.append(expr)
        self.params = newparams

    def addParens_sub(self):
        if self.hasLeft:
            p0 = self.params[0]
            if p0.precedence > 0:
                self.params[0] = Parenthesis(p0)

class Parenthesis(JavaExpression):
    def __init__(self, param):
        self.params = param,
        self.fmt = '({})'

    @property
    def dtype(self): return self.params[0].dtype

class Ternary(JavaExpression):
    precedence = 20
    def __init__(self, *params):
        self.params = params
        self.fmt = '{} ? {} : {}'

    @property
    def dtype(self): return self.params[1].dtype

    def addParens_sub(self):
        #Add unecessary parenthesis to complex conditions for readability
        if self.params[0].precedence >= 20 or self.params[0].complexity() > 0:
            self.params[0] = Parenthesis(self.params[0])
        if self.params[2].precedence > 20:
            self.params[2] = Parenthesis(self.params[2])

class TypeName(JavaExpression):
    def __init__(self, tt):
        self.dtype = None
        self.tt = tt
        name, dim = tt
        if name[0] == '.': #primative type:
            name = name[1:]
        else:
            name = escapeString(name.replace('/','.'))
        s = name + '[]'*dim
        if s.rpartition('.')[0] == 'java.lang':
            s = s.rpartition('.')[2]
        self.str = s

    def print_(self): return self.str
    def complexity(self): return -1 #exprs which have this as a param won't be bumped up to 1 uncessarily

class CatchTypeNames(JavaExpression): #Used for caught exceptions, which can have multiple types specified
    def __init__(self, env, tts):
        assert(tts and not any(zip(*tts)[1])) #at least one type, no array types
        self.tnames = map(TypeName, tts)
        self.dtype = objtypes.commonSupertype(env, tts)

    def print_(self):
        return ' | '.join(tn.print_() for tn in self.tnames)

class UnaryPrefix(JavaExpression):
    precedence = 5
    def __init__(self, opstr, param, dtype=None):
        self.params = [param]
        self.opstr = opstr
        self.fmt = opstr + '{}'
        self._dtype = dtype

    @property
    def dtype(self): return self.params[0].dtype if self._dtype is None else self._dtype

    def addParens_sub(self):
        p0 = self.params[0]
        if p0.precedence > 5 or (isinstance(p0, UnaryPrefix) and p0.opstr[0] == self.opstr[0]):
            self.params[0] = Parenthesis(p0)


class Dummy(JavaExpression):
    def __init__(self, fmt, params, isNew=False):
        self.params = params
        self.fmt = fmt
        self.isNew = isNew
        self.dtype = None
########NEW FILE########
__FILENAME__ = ast2
from . import ast
from .stringescape import escapeString as escape

class MethodDef(object):
    def __init__(self, class_, flags, name, retType, paramDecls, body):
        self.flagstr = flags + ' ' if flags else ''
        self.retType, self.paramDecls = retType, paramDecls
        self.body = body
        self.comment = None

        if name == '<clinit>':
            self.isStaticInit, self.isConstructor = True, False
        elif name == '<init>':
            self.isStaticInit, self.isConstructor = False, True
            self.name = ast.TypeName((class_.name, 0))
        else:
            self.isStaticInit, self.isConstructor = False, False
            self.name = escape(name)

    def print_(self):
        argstr = ', '.join(decl.print_() for decl in self.paramDecls)
        if self.isStaticInit:
            header = 'static'
        elif self.isConstructor:
            name = self.name.print_().rpartition('.')[-1]
            header = '{}{}({})'.format(self.flagstr, name, argstr)
        else:
            header = '{}{} {}({})'.format(self.flagstr, self.retType.print_(), self.name, argstr)

        if self.comment:
            header = '//{}\n{}'.format(self.comment, header)

        if self.body is None:
            return header + ';\n'
        else:
            return header + '\n' + self.body.print_()

class FieldDef(object):
    def __init__(self, flags, type_, name, expr=None):
        self.flagstr = flags + ' ' if flags else ''
        self.type_ = type_
        self.name = escape(name)
        self.expr = None if expr is None else ast.makeCastExpr(type_.tt, expr) 

    def print_(self):
        if self.expr is not None:
            return '{}{} {} = {};'.format(self.flagstr, self.type_.print_(), self.name, self.expr.print_()) 
        return '{}{} {};'.format(self.flagstr, self.type_.print_(), self.name)

class ClassDef(object):
    def __init__(self, flags, isInterface, name, superc, interfaces, fields, methods):
        self.flagstr = flags + ' ' if flags else ''
        self.isInterface = isInterface
        self.name = ast.TypeName((name,0))
        self.super = ast.TypeName((superc,0)) if superc is not None else None
        self.interfaces = [ast.TypeName((iname,0)) for iname in interfaces]
        self.fields = fields
        self.methods = methods
        if superc == 'java/lang/Object':
            self.super = None

    def print_(self):
        contents = ''
        if self.fields:
            contents = '\n'.join(x.print_() for x in self.fields)
        if self.methods:
            if contents:
                contents += '\n\n' #extra line to divide fields and methods
            contents += '\n\n'.join(x.print_() for x in self.methods)

        indented = ['    '+line for line in contents.splitlines()]
        name = self.name.print_().rpartition('.')[-1]
        defname = 'interface' if self.isInterface else 'class'
        header = '{}{} {}'.format(self.flagstr, defname, name)

        if self.super:
            header += ' extends ' + self.super.print_()
        if self.interfaces:
            if self.isInterface:
                assert(self.super is None)
                header += ' extends ' + ', '.join(x.print_() for x in self.interfaces)
            else:
                header += ' implements ' + ', '.join(x.print_() for x in self.interfaces)

        lines = [header + ' {'] + indented + ['}']
        return '\n'.join(lines)
########NEW FILE########
__FILENAME__ = astgen
from . import ast
from . import variablemerge
from .setree import SEBlockItem, SEScope, SEIf, SESwitch, SETry, SEWhile
from ..ssa import ssa_types, ssa_ops, ssa_jumps
from ..ssa import objtypes
from ..namegen import LabelGen
from ..verifier.descriptors import parseFieldDescriptor, parseMethodDescriptor
from .. import opnames

#prefixes for name generation
_prefix_map = {objtypes.IntTT:'i', objtypes.LongTT:'j',
            objtypes.FloatTT:'f', objtypes.DoubleTT:'d',
            objtypes.BoolTT:'b', objtypes.StringTT:'s'}

_ssaToTT = {ssa_types.SSA_INT:objtypes.IntTT, ssa_types.SSA_LONG:objtypes.LongTT,
            ssa_types.SSA_FLOAT:objtypes.FloatTT, ssa_types.SSA_DOUBLE:objtypes.DoubleTT}
class VarInfo(object):
    def __init__(self, method, blocks, namegen, replace):
        self.env = method.class_.env
        self.labelgen = LabelGen().next

        returnTypes = parseMethodDescriptor(method.descriptor, unsynthesize=False)[-1]
        self.return_tt = objtypes.verifierToSynthetic(returnTypes[0]) if returnTypes else None
        self.clsname = method.class_.name
        self._namegen = namegen
        self._replace = replace

        self._vars = {}
        self._tts = {}
        for block in blocks:
            for var, uc in block.unaryConstraints.items():
                if var.type == ssa_types.SSA_MONAD:
                    continue

                if var.type == ssa_types.SSA_OBJECT:
                    tt = uc.getSingleTType() #temp hack
                    if uc.types.isBoolOrByteArray():
                        tt = '.bexpr', tt[1]+1
                else:
                    tt = _ssaToTT[var.type]
                self._tts[var] = tt

    def _nameCallback(self, expr):
        prefix = _prefix_map.get(expr.dtype, 'a')
        return self._namegen.getPrefix(prefix)

    def _newVar(self, var, num):
        tt = self._tts[var]
        if var.const is not None:
            return ast.Literal(tt, var.const)
        else:
            if var.name:
                #important to not add num when it is 0, since we currently
                #use var names to force 'this'
                temp = '{}_{}'.format(var.name, num) if num else var.name
                namefunc = lambda expr:temp
            else:
                namefunc = self._nameCallback
            return ast.Local(tt, namefunc)

    def var(self, node, var, isCast=False):
        assert(var.type != ssa_types.SSA_MONAD)
        key = node, var, isCast
        key = self._replace.get(key,key)
        try:
            return self._vars[key]
        except KeyError:
            new = self._newVar(key[1], key[0].num)
            self._vars[key] = new
            return new

    def customVar(self, tt, prefix): #for use with ignored exceptions
        namefunc = lambda expr: self._namegen.getPrefix(prefix)
        return ast.Local(tt, namefunc)

#########################################################################################
_math_types = (ssa_ops.IAdd, ssa_ops.IDiv, ssa_ops.IMul, ssa_ops.IRem, ssa_ops.ISub)
_math_types += (ssa_ops.IAnd, ssa_ops.IOr, ssa_ops.IShl, ssa_ops.IShr, ssa_ops.IUshr, ssa_ops.IXor)
_math_types += (ssa_ops.FAdd, ssa_ops.FDiv, ssa_ops.FMul, ssa_ops.FRem, ssa_ops.FSub)
_math_symbols = dict(zip(_math_types, '+ / * % - & | << >> >>> ^ + / * % -'.split()))
def _convertJExpr(op, getExpr, clsname):
    params = [getExpr(var) for var in op.params if var.type != ssa_types.SSA_MONAD]
    assert(None not in params)
    expr = None

    #Have to do this one seperately since it isn't an expression statement
    if isinstance(op, ssa_ops.Throw):
        return ast.ThrowStatement(params[0])

    if isinstance(op, _math_types):
        opdict = _math_symbols
        expr = ast.BinaryInfix(opdict[type(op)], params)
    elif isinstance(op, ssa_ops.ArrLength):
        expr = ast.FieldAccess(params[0], 'length', objtypes.IntTT)
    elif isinstance(op, ssa_ops.ArrLoad):
        expr = ast.ArrayAccess(*params)
    elif isinstance(op, ssa_ops.ArrStore):
        expr = ast.ArrayAccess(params[0], params[1])
        expr = ast.Assignment(expr, params[2])
    elif isinstance(op, ssa_ops.CheckCast):
        expr = ast.Cast(ast.TypeName(op.target_tt), params[0])
    elif isinstance(op, ssa_ops.Convert):
        typecode = {ssa_types.SSA_INT:'.int', ssa_types.SSA_LONG:'.long', ssa_types.SSA_FLOAT:'.float',
            ssa_types.SSA_DOUBLE:'.double'}[op.target]
        tt = typecode, 0
        expr = ast.Cast(ast.TypeName(tt), params[0])
    elif isinstance(op, (ssa_ops.FCmp, ssa_ops.ICmp)):
        boolt = objtypes.BoolTT
        cn1, c0, c1 = ast.Literal.N_ONE, ast.Literal.ZERO, ast.Literal.ONE

        ascend = isinstance(op, ssa_ops.ICmp) or op.NaN_val == 1
        if ascend:
            expr = ast.Ternary(ast.BinaryInfix('<',params,boolt), cn1, ast.Ternary(ast.BinaryInfix('==',params,boolt), c0, c1))
        else:
            assert(op.NaN_val == -1)
            expr = ast.Ternary(ast.BinaryInfix('>',params,boolt), c1, ast.Ternary(ast.BinaryInfix('==',params,boolt), c0, cn1))
    elif isinstance(op, ssa_ops.FieldAccess):
        dtype = objtypes.verifierToSynthetic(parseFieldDescriptor(op.desc, unsynthesize=False)[0])

        if op.instruction[0] in (opnames.GETSTATIC, opnames.PUTSTATIC):
            printLeft = (op.target != clsname) #Don't print classname if it is a static field in current class
            tt = op.target, 0
            expr = ast.FieldAccess(ast.TypeName(tt), op.name, dtype, printLeft=printLeft)
        else:
            expr = ast.FieldAccess(params[0], op.name, dtype)

        if op.instruction[0] in (opnames.PUTFIELD, opnames.PUTSTATIC):
            expr = ast.Assignment(expr, params[-1])

    elif isinstance(op, ssa_ops.FNeg):
        expr = ast.UnaryPrefix('-', params[0])
    elif isinstance(op, ssa_ops.InstanceOf):
        args = params[0], ast.TypeName(op.target_tt)
        expr = ast.BinaryInfix('instanceof', args, dtype=objtypes.BoolTT)
    elif isinstance(op, ssa_ops.Invoke):
        vtypes, rettypes = parseMethodDescriptor(op.desc, unsynthesize=False)
        tt_types = objtypes.verifierToSynthetic_seq(vtypes)
        ret_type = objtypes.verifierToSynthetic(rettypes[0]) if rettypes else None

        if op.instruction[0] == opnames.INVOKEINIT and op.isThisCtor:
            name = 'this' if (op.target == clsname) else 'super'
            expr = ast.MethodInvocation(None, name, tt_types, params[1:], op, ret_type)
        elif op.instruction[0] == opnames.INVOKESTATIC: #TODO - fix this for special super calls
            tt = op.target, 0
            expr = ast.MethodInvocation(ast.TypeName(tt), op.name, [None]+tt_types, params, op, ret_type)
        else:
            expr = ast.MethodInvocation(params[0], op.name, [(op.target,0)]+tt_types, params[1:], op, ret_type)
    elif isinstance(op, ssa_ops.Monitor):
        fmt = '//monexit({})' if op.exit else '//monenter({})'
        expr = ast.Dummy(fmt, params)
    elif isinstance(op, ssa_ops.MultiNewArray):
        expr = ast.ArrayCreation(op.tt, *params)
    elif isinstance(op, ssa_ops.New):
        expr = ast.Dummy('//<unmerged new> {}', [ast.TypeName(op.tt)], isNew=True)
    elif isinstance(op, ssa_ops.NewArray):
        base, dim = op.baset
        expr = ast.ArrayCreation((base, dim+1), params[0])
    elif isinstance(op, ssa_ops.Truncate):
        typecode = {(True,16):'.short', (False,16):'.char', (True,8):'.byte'}[op.signed, op.width]
        tt = typecode, 0
        expr = ast.Cast(ast.TypeName(tt), params[0])
    if op.rval is not None and expr:
        expr = ast.Assignment(getExpr(op.rval), expr)

    if expr is None: #Temporary hack to show what's missing
        if isinstance(op, ssa_ops.TryReturn):
            return None #Don't print out anything
        else:
            return ast.StringStatement('//' + type(op).__name__)
    return ast.ExpressionStatement(expr)

#########################################################################################
def _createASTBlock(info, endk, node):
    getExpr = lambda var: info.var(node, var)
    op2expr = lambda op: _convertJExpr(op, getExpr, info.clsname)

    block = node.block
    lines = map(op2expr, block.lines) if block is not None else []
    lines = [x for x in lines if x is not None]

    # Kind of hackish: If the block ends in a cast and hence it is not known to always
    # succeed, assign the results of the cast rather than passing through the variable
    # unchanged
    outreplace = {}
    if lines and isinstance(block.lines[-1], ssa_ops.CheckCast):
        assert(isinstance(lines[-1].expr, ast.Cast))
        var = block.lines[-1].params[0]
        cexpr = lines[-1].expr
        lines[-1].expr = ast.Assignment(info.var(node, var, True), cexpr)
        nvar = outreplace[var] = lines[-1].expr.params[0]
        nvar.dtype = cexpr.dtype

    eassigns = []
    nassigns = []
    for n2 in node.successors:
        assert((n2 in node.outvars) != (n2 in node.eassigns))
        if n2 in node.eassigns:
            for outv, inv in zip(node.eassigns[n2], n2.invars):
                if outv is None: #this is how we mark the thrown exception, which
                    #obviously doesn't get an explicit assignment statement
                    continue
                expr = ast.Assignment(info.var(n2, inv), info.var(node, outv))
                if expr.params[0] != expr.params[1]:
                    eassigns.append(ast.ExpressionStatement(expr))
        else:
            for outv, inv in zip(node.outvars[n2], n2.invars):
                right = outreplace.get(outv, info.var(node, outv))
                expr = ast.Assignment(info.var(n2, inv), right)
                if expr.params[0] != expr.params[1]:
                    nassigns.append(ast.ExpressionStatement(expr))

    #Need to put exception assignments before last statement, which might throw
    #While normal assignments must come last as they may depend on it
    statements = lines[:-1] + eassigns + lines[-1:] + nassigns

    norm_successors = node.normalSuccessors()
    jump = None if block is None else block.jump
    jumpKey = None
    if isinstance(jump, (ssa_jumps.Rethrow, ssa_jumps.Return)):
        assert(not norm_successors)
        if isinstance(jump, ssa_jumps.Rethrow):
            param = info.var(node, jump.params[-1])
            statements.append(ast.ThrowStatement(param))
        else:
            if len(jump.params)>1: #even void returns have a monad param
                param = info.var(node, jump.params[-1])
                statements.append(ast.ReturnStatement(param, info.return_tt))
            else:
                statements.append(ast.ReturnStatement())
    elif len(norm_successors) == 1: #normal successors
        jumpKey = norm_successors[0]._key
    #case of if and switch jumps handled in parent scope

    new = ast.StatementBlock(info.labelgen, node._key, endk, statements, jumpKey)
    assert(None not in statements)
    return new

_cmp_strs = dict(zip(('eq','ne','lt','ge','gt','le'), "== != < >= > <=".split()))
def _createASTSub(info, current, ftitem, forceUnlabled=False):
    begink = current.entryBlock._key
    endk = ftitem.entryBlock._key if ftitem is not None else None

    if isinstance(current, SEBlockItem):
        return _createASTBlock(info, endk, current.node)
    elif isinstance(current, SEScope):
        ftitems = current.items[1:] + [ftitem]
        parts = [_createASTSub(info, item, newft) for item, newft in zip(current.items, ftitems)]
        return ast.StatementBlock(info.labelgen, begink, endk, parts, endk, labelable=(not forceUnlabled))
    elif isinstance(current, SEWhile):
        parts = [_createASTSub(info, scope, current, True) for scope in current.getScopes()]
        return ast.WhileStatement(info.labelgen, begink, endk, tuple(parts))
    elif isinstance(current, SETry):
        parts = [_createASTSub(info, scope, ftitem, True) for scope in current.getScopes()]
        catchnode = current.getScopes()[-1].entryBlock
        declt = ast.CatchTypeNames(info.env, current.toptts)

        if current.catchvar is None: #exception is ignored and hence not referred to by the graph, so we need to make our own
            catchvar = info.customVar(declt, 'ignoredException')
        else:
            catchvar = info.var(catchnode, current.catchvar)
        decl = ast.VariableDeclarator(declt, catchvar)
        pairs = [(decl, parts[1])]
        return ast.TryStatement(info.labelgen, begink, endk, parts[0], pairs)

    #Create a fake key to represent the beginning of the conditional statement itself
    #doesn't matter what it is as long as it's unique
    midk = begink + (-1,)
    node = current.head.node
    jump = node.block.jump

    if isinstance(current, SEIf):
        parts = [_createASTSub(info, scope, ftitem, True) for scope in current.getScopes()]
        cmp_str = _cmp_strs[jump.cmp]
        exprs = [info.var(node, var) for var in jump.params]
        ifexpr = ast.BinaryInfix(cmp_str, exprs, objtypes.BoolTT)
        new = ast.IfStatement(info.labelgen, midk, endk, ifexpr, tuple(parts))

    elif isinstance(current, SESwitch):
        ftitems = current.ordered[1:] + [ftitem]
        parts = [_createASTSub(info, item, newft, True) for item, newft in zip(current.ordered, ftitems)]
        for part in parts:
            part.breakKey = endk #createSub will assume break should be ft, which isn't the case with switch statements

        expr = info.var(node, jump.params[0])
        pairs = zip(current.ordered_keysets, parts)
        new = ast.SwitchStatement(info.labelgen, midk, endk, expr, pairs)

    #bundle head and if together so we can return as single statement
    headscope = _createASTBlock(info, midk, node)
    assert(headscope.jumpKey is None)
    headscope.jumpKey = midk
    return ast.StatementBlock(info.labelgen, begink, endk, [headscope, new], endk)

def createAST(method, ssagraph, seroot, namegen):
    replace = variablemerge.mergeVariables(seroot)
    info = VarInfo(method, ssagraph.blocks, namegen, replace)
    astroot = _createASTSub(info, seroot, None)
    return astroot, info
########NEW FILE########
__FILENAME__ = boolize
import collections

from ..ssa.objtypes import IntTT, ShortTT, CharTT, ByteTT, BoolTT
from . import ast
from .. import graph_util

#Class union-find data structure except that we don't bother with weighting trees and singletons are implicit
#Also, booleans are forced to be seperate roots
FORCED_ROOTS = True, False
class UnionFind(object):
    def __init__(self):
        self.d = {}

    def find(self, x):
        if x not in self.d:
            return x
        path = [x]
        while path[-1] in self.d:
            path.append(self.d[path[-1]])
        root = path.pop()
        for y in path:
            self.d[y] = root
        return root

    def union(self, x, x2):
        if x is None or x2 is None:
            return
        root1, root2 = self.find(x), self.find(x2)
        if root2 in FORCED_ROOTS:
            root1, root2 = root2, root1
        if root1 != root2 and root2 not in FORCED_ROOTS:
        # if root1 != root2:
        #     assert(root2 not in FORCED_ROOTS)
            self.d[root2] = root1

##############################################################
def visitExprs(scope, callback):
    for item in scope.statements:
        for sub in item.getScopes():
            visitExprs(sub, callback)
        if item.expr is not None:
            callback(item, item.expr)

int_tts = IntTT, ShortTT, CharTT, ByteTT, BoolTT
def fixArrays(root, arg_vars):
    varlist = []
    sets = UnionFind()

    for expr in arg_vars:
        forced_val = (expr.dtype[0] == BoolTT[0])
        sets.union(forced_val, expr)

    def visitExprArray(expr):
        #see if we have to merge
        if isinstance(expr, ast.Assignment) or isinstance(expr, ast.BinaryInfix) and expr.opstr in ('==','!='):
            subs = [visitExprArray(param) for param in expr.params]
            sets.union(*subs)

        if isinstance(expr, ast.Local):
            if expr.dtype[1] == 0:
                return None
            if expr.dtype[0] == '.bexpr' and expr.dtype[1] > 0:
                varlist.append(expr)
            return sets.find(expr)
        elif isinstance(expr, ast.Literal):
            return None
        elif isinstance(expr, (ast.ArrayAccess, ast.Parenthesis, ast.UnaryPrefix)):
            return visitExprArray(expr.params[0])
        elif expr.dtype is not None and expr.dtype[0] != '.bexpr':
            return expr.dtype[0] == BoolTT[0]
        return None

    def addSourceArray(item, expr):
        root = visitExprArray(expr)
        if isinstance(item, ast.ReturnStatement):
            forced_val = (item.tt[0] == BoolTT[0])
            sets.union(forced_val, root)

    visitExprs(root, addSourceArray)
    bases = {True:BoolTT[0], False:ByteTT[0]}
    for var in set(varlist):
        assert(var.dtype[0] == '.bexpr' and var.dtype[1] > 0)
        var.dtype = bases[sets.find(var)], var.dtype[1]

def fixScalars(root, arg_vars):
    varlist = []
    sets = UnionFind()

    for expr in arg_vars:
        forced_val = (expr.dtype[0] == BoolTT[0])
        sets.union(forced_val, expr)

    def visitExprScalar(expr):
        #see if we have to merge
        if isinstance(expr, ast.Assignment) or isinstance(expr, ast.BinaryInfix) and expr.opstr in ('==','!=','&','|','^'):
            subs = [visitExprScalar(param) for param in expr.params]
            sets.union(*subs)
            if isinstance(expr, ast.Assignment) or expr.opstr in ('&','|','^'):
                return subs[0]
        elif isinstance(expr, ast.BinaryInfix) and expr.opstr in ('* / % + - << >> >>>'):
            sets.union(False, visitExprScalar(expr.params[0]))
            sets.union(False, visitExprScalar(expr.params[1]))

        if isinstance(expr, ast.Local):
            if expr.dtype in int_tts:
                varlist.append(expr)
            return sets.find(expr)
        elif isinstance(expr, ast.Literal):
            if expr.dtype == IntTT and expr.val not in (0,1):
                return False
            return None
        elif isinstance(expr, (ast.ArrayAccess, ast.Parenthesis, ast.UnaryPrefix)):
            return visitExprScalar(expr.params[0])
        elif expr.dtype is not None and expr.dtype[0] != '.bexpr':
            return expr.dtype[0] == BoolTT[0]
        return None

    def addSourceScalar(item, expr):
        root = visitExprScalar(expr)
        if isinstance(item, ast.ReturnStatement):
            forced_val = (item.tt[0] == BoolTT[0])
            sets.union(forced_val, root)

    visitExprs(root, addSourceScalar)

    #Fix the propagated types
    for var in set(varlist):
        assert(var.dtype in int_tts)
        if sets.find(var) != False:
            var.dtype = BoolTT

    #Fix everything else back up
    def fixExpr(item, expr):
        for param in expr.params:
            fixExpr(None, param)

        if isinstance(expr, ast.Assignment):
            left, right = expr.params
            if left.dtype in int_tts:
                if not ast.isPrimativeAssignable(right.dtype, left.dtype):
                    expr.params = left, ast.makeCastExpr(left.dtype, right)
        elif isinstance(expr, ast.BinaryInfix):
            a,b = expr.params
            if expr.opstr in '== != & | ^' and a.dtype == BoolTT or b.dtype == BoolTT:
                # assert(expr.opstr in '== != & | ^')
                expr.params = [ast.makeCastExpr(BoolTT, v) for v in expr.params]
    visitExprs(root, fixExpr)

def boolizeVars(root, arg_vars):
    arg_vars = frozenset(arg_vars)
    fixArrays(root, arg_vars)
    fixScalars(root, arg_vars)
########NEW FILE########
__FILENAME__ = graphproxy
import collections, itertools
ddict = collections.defaultdict

from ..ssa import ssa_types
def unique(seq): return len(set(seq)) == len(seq)

# This module provides a view of the ssa graph that can be modified without
# touching the underlying graph. This proxy is tailored towards the need of
# cfg structuring, so it allows easy duplication and indirection of nodes,
# but assumes that the underlying variables and statements are immutable

class BlockProxy(object):
    def __init__(self, key, counter, block=None):
        self.bkey = key
        self.num = next(counter)
        self.counter = counter
        self.block = block

        self.predecessors = []
        self.successors = []
        self.outvars = {}
        self.eassigns = {} #exception edge assignments, used after try constraint creation
        #invars, blockdict
        self._key = self.bkey, self.num

    def replaceSuccessors(self, rmap):
        update = lambda k:rmap.get(k,k)

        self.successors = map(update, self.successors)
        self.outvars = {update(k):v for k,v in self.outvars.items()}
        if self.block is not None:
            d1 = self.blockdict
            self.blockdict = {(b.key,t):update(d1[b.key,t]) for (b,t) in self.block.jump.getSuccessorPairs()}

    def newIndirect(self): #for use during graph creation
        new = BlockProxy(self.bkey, self.counter)
        new.invars = self.invars
        new.outvars = {self:new.invars}
        new.blockdict = None
        new.successors = [self]
        self.predecessors.append(new)
        return new

    def newDuplicate(self): #for use by duplicateNodes
        new = BlockProxy(self.bkey, self.counter, self.block)
        new.invars = self.invars
        new.outvars = self.outvars.copy()
        new.blockdict = self.blockdict
        new.successors = self.successors[:]
        return new

    def indirectEdges(self, edges):
        #Should only be called once graph is completely set up. newIndirect is used during graph creation
        new = self.newIndirect()
        for parent in edges:
            self.predecessors.remove(parent)
            new.predecessors.append(parent)
            parent.replaceSuccessors({self:new})
        return new

    def normalSuccessors(self): #only works once try constraints have been created
        return [x for x in self.successors if x in self.outvars]

    def __str__(self):
        fmt = 'PB {}x{}' if self.num else 'PB {0}'
        return fmt.format(self.bkey, self.num)
    __repr__ = __str__

def duplicateNodes(reachable, scc_set):
    nodes = reachable[:]
    assert(nodes and unique(nodes))
    assert(scc_set.issuperset(nodes))
    dups = [(n, n.newDuplicate()) for n in nodes]
    dupmap = dict(dups)

    temp = scc_set.copy()
    innodes = itertools.chain.from_iterable(n.predecessors for n in nodes)
    innodes = [x for x in innodes if not x in temp and not temp.add(x)]

    for n in innodes:
        n.replaceSuccessors(dupmap)

    S = set(innodes)
    for old, new in dups:
        for p in old.predecessors[:]:
            if p in S:
                old.predecessors.remove(p)
                new.predecessors.append(p)
        new.replaceSuccessors(dupmap)
        for c in new.successors:
            c.predecessors.append(new)

    return zip(*dups)[1]

def createGraphProxy(ssagraph):
    assert(not ssagraph.procs) #should have already been inlined

    nodes = [BlockProxy(b.key, itertools.count(), block=b) for b in ssagraph.blocks]
    allnodes = nodes[:] #will also contain indirected nodes

    entryNode = None
    intypes = ddict(set)
    for n in nodes:
        invars = [phi.rval for phi in n.block.phis]
        for b, t in n.block.jump.getSuccessorPairs():
            intypes[b.key].add(t)

        if n.bkey == ssagraph.entryKey:
            assert(not entryNode and not invars)
            entryNode = n
            invars = ssagraph.inputArgs #store them in the node so we don't have to keep track seperately
            invars = [x for x in invars if x is not None] #will have None placeholders for Long and Double arguments
        n.invars = [v for v in invars if v.type != ssa_types.SSA_MONAD]

    lookup = {}
    for n in nodes:
        if len(intypes[n.bkey]) == 2: #both normal and exceptional inedges
            n2 = n.newIndirect()
            allnodes.append(n2)
        else:
            n2 = n

        if False in intypes[n.bkey]:
            lookup[n.bkey, False] = n
        if True in intypes[n.bkey]:
            lookup[n2.bkey, True] = n2
    assert(lookup and unique(lookup.values()))

    for n in nodes:
        if n.block is None:
            n.blockdict = None
            continue

        n.blockdict = lookup
        block = n.block
        for (block2, t) in block.jump.getSuccessorPairs():
            out = [phi.get((block, t)) for phi in block2.phis]
            out = [v for v in out if v.type != ssa_types.SSA_MONAD]

            n2 = lookup[block2.key, t]
            n.outvars[n2] = out
            n.successors.append(n2)
            n2.predecessors.append(n)

    #sanity check
    for n in allnodes:
        assert((n.block is not None) == (n.num == 0))
        assert((n is entryNode) == (len(n.predecessors) == 0))
        assert(unique(n.predecessors))
        assert(unique(n.successors))
        for pn in n.predecessors:
            assert(n in pn.successors)
        assert(set(n.outvars) == set(n.successors))
        for sn in n.successors:
            assert(n in sn.predecessors)
            assert(len(n.outvars[sn]) == len(sn.invars))

    return entryNode, allnodes
########NEW FILE########
__FILENAME__ = javaclass
import struct

from ..ssa import objtypes
from ..verifier.descriptors import parseFieldDescriptor

from . import ast, ast2, javamethod
from .reserved import reserved_identifiers

IGNORE_EXCEPTIONS = 0

def loadConstValue(cpool, index):
    entry_type = cpool.pool[index][0]
    args = cpool.getArgs(index)

    #Note: field constant values cannot be class literals
    tt = {'Int':objtypes.IntTT, 'Long':objtypes.LongTT,
        'Float':objtypes.FloatTT, 'Double':objtypes.DoubleTT,
        'String':objtypes.StringTT}[entry_type]
    return ast.Literal(tt, args[0])

def _getField(field):
    flags = [x.lower() for x in sorted(field.flags) if x not in ('SYNTHETIC','ENUM')]
    desc = field.descriptor
    dtype = objtypes.verifierToSynthetic(parseFieldDescriptor(desc, unsynthesize=False)[0])

    initexpr = None
    if field.static:
        cpool = field.class_.cpool
        const_attrs = [data for name,data in field.attributes if name == 'ConstantValue']
        if const_attrs:
            assert(len(const_attrs) == 1)
            data = const_attrs[0]
            index = struct.unpack('>h', data)[0]
            initexpr = loadConstValue(cpool, index)
    return ast2.FieldDef(' '.join(flags), ast.TypeName(dtype), field.name, initexpr)

def _getMethod(method, cb, forbidden_identifiers):
    try:
        graph = cb(method) if method.code is not None else None
        print 'Decompiling method', method.name.encode('utf8'), method.descriptor.encode('utf8')
        code_ast = javamethod.generateAST(method, graph, forbidden_identifiers)
        return code_ast
    except Exception as e:
        if not IGNORE_EXCEPTIONS:
            raise
        if e.__class__.__name__ == 'DecompilationError':
            print 'Unable to decompile ' + method.class_.name
        else:
            print 'Decompiling {} failed!'.format(method.class_.name)
        code_ast = javamethod.generateAST(method, None, forbidden_identifiers)
        code_ast.comment = ' {0!r}: {0!s}'.format(e)
        return code_ast

def generateAST(cls, cb, method=None):
    methods = cls.methods if method is None else [cls.methods[method]]
    fi = set(reserved_identifiers)
    for field in cls.fields:
        fi.add(field.name)
    forbidden_identifiers = frozenset(fi)


    myflags = [x.lower() for x in sorted(cls.flags) if x not in ('INTERFACE','SUPER','SYNTHETIC','ANNOTATION','ENUM')]
    isInterface = 'INTERFACE' in cls.flags

    superc = cls.supername
    interfaces = [cls.cpool.getArgsCheck('Class', index) for index in cls.interfaces_raw] #todo - change when class actually loads interfaces

    field_defs = [_getField(f) for f in cls.fields]
    method_defs = [_getMethod(m, cb, forbidden_identifiers) for m in methods]
    return ast2.ClassDef(' '.join(myflags), isInterface, cls.name, superc, interfaces, field_defs, method_defs)
########NEW FILE########
__FILENAME__ = javamethod
import collections
import operator
from functools import partial

from ..ssa import objtypes
from .. import graph_util
from ..namegen import NameGen, LabelGen
from ..verifier.descriptors import parseMethodDescriptor

from . import ast, ast2, boolize
from . import graphproxy, structuring, astgen

class DeclInfo(object):
    __slots__ = "declScope scope defs".split()
    def __init__(self):
        self.declScope = self.scope = None
        self.defs = []

def findVarDeclInfo(root, predeclared):
    info = collections.OrderedDict()
    def visit(scope, expr):
        for param in expr.params:
            visit(scope, param)

        if expr.isLocalAssign():
            left, right = expr.params
            info[left].defs.append(right)
        elif isinstance(expr, (ast.Local, ast.Literal)):
            #this would be so much nicer if we had Ordered defaultdicts
            info.setdefault(expr, DeclInfo())
            info[expr].scope = ast.StatementBlock.join(info[expr].scope, scope)

    def visitDeclExpr(scope, expr):
        info.setdefault(expr, DeclInfo())
        assert(scope is not None and info[expr].declScope is None)
        info[expr].declScope = scope

    for expr in predeclared:
        visitDeclExpr(root, expr)

    stack = [(root,root)]
    while stack:
        scope, stmt = stack.pop()
        if isinstance(stmt, ast.StatementBlock):
            stack.extend((stmt,sub) for sub in stmt.statements)
        else:
            stack.extend((subscope,subscope) for subscope in stmt.getScopes())
            #temp hack
            if stmt.expr is not None:
                visit(scope, stmt.expr)
            if isinstance(stmt, ast.TryStatement):
                for catchdecl, body in stmt.pairs:
                    visitDeclExpr(body, catchdecl.local)
    return info

def reverseBoolExpr(expr):
    assert(expr.dtype == objtypes.BoolTT)
    if isinstance(expr, ast.BinaryInfix):
        symbols = "== != < >= > <=".split()
        floatts = (objtypes.FloatTT, objtypes.DoubleTT)
        if expr.opstr in symbols:
            sym2 = symbols[symbols.index(expr.opstr) ^ 1]
            left, right = expr.params
            #be sure not to reverse floating point comparisons since it's not equivalent for NaN
            if expr.opstr in symbols[:2] or (left.dtype not in floatts and right.dtype not in floatts):
                return ast.BinaryInfix(sym2, (left,right), objtypes.BoolTT)
    elif isinstance(expr, ast.UnaryPrefix) and expr.opstr == '!':
        return expr.params[0]
    return ast.UnaryPrefix('!', expr)

def getSubscopeIter(root):
    stack = [root]
    while stack:
        scope = stack.pop()
        if isinstance(scope, ast.StatementBlock):
            stack.extend(scope.statements)
            yield scope
        else:
            stack.extend(scope.getScopes())

def mayBreakTo(root, forbidden):
    assert(None not in forbidden)
    for scope in getSubscopeIter(root):
        if scope.jumpKey in forbidden:
            #We return true if scope has forbidden jump and is reachable
            #We assume there is no unreachable code, so in order for a scope
            #jump to be unreachable, it must end in a return, throw, or a
            #compound statement, all of which are not reachable or do not
            #break out of the statement. We omit adding last.breakKey to
            #forbidden since it should always match scope.jumpKey anyway
            if not scope.statements:
                return True
            last = scope.statements[-1]
            if not last.getScopes():
                if not isinstance(last, (ast.ReturnStatement, ast.ThrowStatement)):
                    return True
            else:
                #If and switch statements may allow fallthrough
                #A while statement with condition may break implicitly
                if isinstance(last, ast.IfStatement) and len(last.getScopes()) == 1:
                    return True
                if isinstance(last, ast.SwitchStatement) and not last.hasDefault():
                    return True
                if isinstance(last, ast.WhileStatement) and last.expr != ast.Literal.TRUE:
                    return True

                if not isinstance(last, ast.WhileStatement):
                    for sub in last.getScopes():
                        assert(sub.breakKey == last.breakKey == scope.jumpKey)
    return False

def replaceKeys(top, replace):
    assert(None not in replace)
    get = lambda k:replace.get(k,k)

    if top.getScopes():
        if isinstance(top, ast.StatementBlock) and get(top.breakKey) is None:
            #breakkey can be None with non-None jumpkey when we're a scope in a switch statement that falls through
            #and the end of the switch statement is unreachable
            assert(get(top.jumpKey) is None or not top.labelable)

        top.breakKey = get(top.breakKey)
        if isinstance(top, ast.StatementBlock):
            top.jumpKey = get(top.jumpKey)
            for item in top.statements:
                replaceKeys(item, replace)
        else:
            for scope in top.getScopes():
                replaceKeys(scope, replace)

NONE_SET = frozenset([None])
def _preorder(scope, func):
    newitems = []
    for i, item in enumerate(scope.statements):
        for sub in item.getScopes():
            _preorder(sub, func)

        val = func(scope, item)
        vals = [item] if val is None else val
        newitems.extend(vals)
    scope.statements = newitems

def _fixObjectCreations(scope, item):
    '''Combines new/invokeinit pairs into Java constructor calls'''

    #Thanks to the copy propagation pass prior to AST generation, as well as the fact that
    #uninitialized types never merge, we can safely assume there are no copies to worry about
    expr = item.expr
    if isinstance(expr, ast.Assignment):
        left, right = expr.params
        if isinstance(right, ast.Dummy) and right.isNew:
            return [] #remove item
    elif isinstance(expr, ast.MethodInvocation) and expr.name == '<init>':
        left = expr.params[0]
        newexpr = ast.ClassInstanceCreation(ast.TypeName(left.dtype), expr.tts[1:], expr.params[1:])
        item.expr = ast.Assignment(left, newexpr)

def _pruneRethrow_cb(item):
    '''Convert try{A} catch(T t) {throw t;} to {A}'''
    while item.pairs:
        decl, body = item.pairs[-1]
        caught, lines = decl.local, body.statements

        if len(lines) == 1:
            line = lines[0]
            if isinstance(line, ast.ThrowStatement) and line.expr == caught:
                item.pairs = item.pairs[:-1]
                continue
        break
    if not item.pairs:
        new = item.tryb
        assert(new.breakKey == item.breakKey)
        assert(new.continueKey == item.continueKey)
        assert(not new.labelable)
        new.labelable = True
        return new
    return item

def _pruneIfElse_cb(item):
    '''Convert if(A) {B} else {} to if(A) {B}'''
    if len(item.scopes) > 1:
        tblock, fblock = item.scopes

        #if true block is empty, swap it with false so we can remove it
        if not tblock.statements and tblock.doesFallthrough():
            item.expr = reverseBoolExpr(item.expr)
            tblock, fblock = fblock, tblock
            item.scopes = tblock, fblock

        if not fblock.statements and fblock.doesFallthrough():
            item.scopes = tblock,
        # If cond is !(x), reverse it back to simplify cond
        elif isinstance(item.expr, ast.UnaryPrefix) and item.expr.opstr == '!':
            item.expr = reverseBoolExpr(item.expr)
            item.scopes = fblock, tblock

    # if(A) {if(B) {C}} -> if(A && B) {C}
    tblock = item.scopes[0]
    if len(item.scopes) == 1 and len(tblock.statements) == 1 and tblock.doesFallthrough():
        first = tblock.statements[0]
        if isinstance(first, ast.IfStatement) and len(first.scopes) == 1:
            item.expr = ast.BinaryInfix('&&',[item.expr, first.expr], objtypes.BoolTT)
            item.scopes = first.scopes
    return item

def _whileCondition_cb(item):
    '''Convert while(true) {if(A) {B break;} else {C} D} to while(!A) {{C} D} {B}'''
    failure = [], item #what to return if we didn't inline
    body = item.getScopes()[0]
    if not body.statements or not isinstance(body.statements[0], ast.IfStatement):
        return failure

    head = body.statements[0]
    cond = head.expr
    trueb, falseb = (head.getScopes() + (None,))[:2]

    #Make sure it doesn't continue the loop or break out of the if statement
    badjumps1 = frozenset([head.breakKey, item.continueKey]) - NONE_SET
    if mayBreakTo(trueb, badjumps1):
        if falseb is not None and not mayBreakTo(falseb, badjumps1):
            cond = reverseBoolExpr(cond)
            trueb, falseb = falseb, trueb
        else:
            return failure
    assert(not mayBreakTo(trueb, badjumps1))


    trivial = not trueb.statements and trueb.jumpKey == item.breakKey
    #If we already have a condition, only a simple break is allowed
    if not trivial and item.expr != ast.Literal.TRUE:
        return failure

    #If break body is nontrival, we can't insert this after the end of the loop unless
    #We're sure that nothing else in the loop breaks out
    badjumps2 = frozenset([item.breakKey]) - NONE_SET
    if not trivial:
        restloop = [falseb] if falseb is not None else []
        restloop += body.statements[1:]
        if body.jumpKey == item.breakKey or any(mayBreakTo(s, badjumps2) for s in restloop):
            return failure

    #Now inline everything
    item.expr = _simplifyExpressions(ast.BinaryInfix('&&', [item.expr, reverseBoolExpr(cond)]))
    if falseb is None:
        body.statements.pop(0)
    else:
        body.statements[0] = falseb
        falseb.labelable = True
    trueb.labelable = True

    if item.breakKey is None: #Make sure to maintain invariant that bkey=None -> jkey=None
        assert(trueb.doesFallthrough())
        trueb.jumpKey = trueb.breakKey = None
    trueb.breakKey = item.breakKey
    assert(trueb.continueKey is not None)
    if not trivial:
        item.breakKey = trueb.continueKey

    #Trueb doesn't break to head.bkey but there might be unreacahble jumps, so we replace
    #it too. We don't replace item.ckey because it should never appear, even as an
    #unreachable jump
    replaceKeys(trueb, {head.breakKey:trueb.breakKey, item.breakKey:trueb.breakKey})
    return [item], trueb

def _simplifyBlocksSub(scope, item, isLast):
    rest = []
    if isinstance(item, ast.TryStatement):
        item = _pruneRethrow_cb(item)
    elif isinstance(item, ast.IfStatement):
        item = _pruneIfElse_cb(item)
    elif isinstance(item, ast.WhileStatement):
        rest, item = _whileCondition_cb(item)

    if isinstance(item, ast.StatementBlock):
        assert(item.breakKey is not None or item.jumpKey is None)
        #If bkey is None, it can't be broken to
        #If contents can also break to enclosing scope, it's always safe to inline
        bkey = item.breakKey
        if bkey is None or (bkey == scope.breakKey and scope.labelable):
            rest, item.statements = rest + item.statements, []

        for sub in item.statements[:]:
            if sub.getScopes() and sub.breakKey != bkey and mayBreakTo(sub, frozenset([bkey])):
                break
            rest.append(item.statements.pop(0))

        if not item.statements:
            if item.jumpKey != bkey:
                assert(isLast)
                scope.jumpKey = item.jumpKey
                assert(scope.breakKey is not None or scope.jumpKey is None)
            return rest
    return rest + [item]

def _simplifyBlocks(scope):
    newitems = []
    for item in reversed(scope.statements):
        isLast = not newitems #may be true if all subsequent items pruned
        if isLast and item.getScopes():
            if item.breakKey != scope.jumpKey:# and item.breakKey is not None:
                # print 'sib replace', scope, item, item.breakKey, scope.jumpKey
                replaceKeys(item, {item.breakKey: scope.jumpKey})

        for sub in reversed(item.getScopes()):
            _simplifyBlocks(sub)
        vals = _simplifyBlocksSub(scope, item, isLast)
        newitems += reversed(vals)
    scope.statements = newitems[::-1]

_op2bits = {'==':2, '!=':13, '<':1, '<=':3, '>':4, '>=':6}
_bit2ops_float = {v:k for k,v in _op2bits.items()}
_bit2ops = {(v & 7):k for k,v in _op2bits.items()}

def _getBitfield(expr):
    if isinstance(expr, ast.BinaryInfix):
        if expr.opstr in ('==','!=','<','<=','>','>='):
            # We don't want to merge expressions if they could have side effects
            # so only allow literals and locals
            if all(isinstance(p, (ast.Literal, ast.Local)) for p in expr.params):
                return _op2bits[expr.opstr], tuple(expr.params)
        elif expr.opstr in ('&','&&','|','||'):
            bits1, args1 = _getBitfield(expr.params[0])
            bits2, args2 = _getBitfield(expr.params[1])
            if args1 == args2:
                bits = (bits1 & bits2) if '&' in expr.opstr else (bits1 | bits2)
                return bits, args1
    elif isinstance(expr, ast.UnaryPrefix) and expr.opstr == '!':
        bits, args = _getBitfield(expr.params[0])
        return ~bits, args
    return 0, None

def _mergeComparisons(expr):
    # a <= b && a != b -> a < b, etc.
    bits, args = _getBitfield(expr)
    if args is None:
        return expr

    assert(not hasSideEffects(args[0]) and not hasSideEffects(args[1]))
    if args[0].dtype in (objtypes.FloatTT, objtypes.DoubleTT):
        mask, d = 15, _bit2ops_float
    else:
        mask, d = 7, _bit2ops

    bits &= mask
    notbits = (~bits) & mask

    if bits == 0:
        return ast.Literal.TRUE
    elif notbits == 0:
        return ast.Literal.FALSE
    elif bits in d:
        return ast.BinaryInfix(d[bits], args, objtypes.BoolTT)
    elif notbits in d:
        return ast.UnaryPrefix('!', ast.BinaryInfix(d[notbits], args, objtypes.BoolTT))
    return expr

def _simplifyExpressions(expr):
    TRUE, FALSE = ast.Literal.TRUE, ast.Literal.FALSE
    bools = {True:TRUE, False:FALSE}
    opfuncs = {'<': operator.lt, '<=': operator.le, '>': operator.gt, '>=': operator.ge}

    simplify = _simplifyExpressions
    expr.params = map(simplify, expr.params)

    if isinstance(expr, ast.BinaryInfix):
        left, right = expr.params
        op = expr.opstr
        if op in ('==','!=','<','<=','>','>=') and isinstance(right, ast.Literal):
            # la cmp lb -> result (i.e. constant propagation on literal comparisons)
            if isinstance(left, ast.Literal):
                if op in ('==','!='):
                    #these could be string or class literals, but those are always nonnull so it still works
                    res = (left == right) == (op == '==')
                else:
                    assert(left.dtype == right.dtype)
                    res = opfuncs[op](left.val, right.val)
                expr = bools[res]
            # (a ? lb : c) cmp ld -> a ? (lb cmp ld) : (c cmp ld)
            elif isinstance(left, ast.Ternary) and isinstance(left.params[1], ast.Literal):
                left.params[1] = simplify(ast.BinaryInfix(op, [left.params[1], right], expr._dtype))
                left.params[2] = simplify(ast.BinaryInfix(op, [left.params[2], right], expr._dtype))
                expr = left

    # a ? true : b -> a || b
    # a ? false : b -> !a && b
    if isinstance(expr, ast.Ternary) and expr.dtype == objtypes.BoolTT:
        cond, val1, val2 = expr.params
        if not isinstance(val1, ast.Literal): #try to get bool literal to the front
            cond, val1, val2 = reverseBoolExpr(cond), val2, val1

        if val1 == TRUE:
            expr = ast.BinaryInfix('||', [cond, val2], objtypes.BoolTT)
        elif val1 == FALSE:
            expr = ast.BinaryInfix('&&', [reverseBoolExpr(cond), val2], objtypes.BoolTT)

    # true && a -> a, etc.
    if isinstance(expr, ast.BinaryInfix) and expr.opstr in ('&&','||'):
        left, right = expr.params
        if expr.opstr == '&&':
            if left == TRUE or (right == FALSE and not hasSideEffects(left)):
                expr = right
            elif left == FALSE or right == TRUE:
                expr = left
        else:
            if left == TRUE or right == FALSE:
                expr = left
            elif left == FALSE or (right == TRUE and not hasSideEffects(left)):
                expr = right
        # a > b || a == b -> a >= b, etc.
        expr = _mergeComparisons(expr)

    # a == true -> a
    # a == false -> !a
    if isinstance(expr, ast.BinaryInfix) and expr.opstr in ('==, !=') and expr.params[0].dtype == objtypes.BoolTT:
        left, right = expr.params
        if not isinstance(left, ast.Literal): #try to get bool literal to the front
            left, right = right, left
        if isinstance(left, ast.Literal):
            flip = (left == TRUE) != (expr.opstr == '==')
            expr = reverseBoolExpr(right) if flip else right

    # !a ? b : c -> a ? c : b
    if isinstance(expr, ast.Ternary) and isinstance(expr.params[0], ast.UnaryPrefix):
        cond, val1, val2 = expr.params
        if cond.opstr == '!':
            expr.params = [reverseBoolExpr(cond), val2, val1]

    # 0 - a -> -a
    if isinstance(expr, ast.BinaryInfix) and expr.opstr == '-':
        if expr.params[0] == ast.Literal.LZERO:
            expr = ast.UnaryPrefix('-', expr.params[1])

    return expr

def _setScopeParents(scope):
    for item in scope.statements:
        for sub in item.getScopes():
            sub.bases = scope.bases + (sub,)
            _setScopeParents(sub)

def _replaceExpressions(scope, item, rdict):
    #Must be done before local declarations are created since it doesn't touch/remove them
    if item.expr is not None:
        item.expr = item.expr.replaceSubExprs(rdict)
    #remove redundant assignments i.e. x=x;
    if isinstance(item.expr, ast.Assignment):
        assert(isinstance(item, ast.ExpressionStatement))
        left, right = item.expr.params
        if left == right:
            return []
    return [item]

def _mergeVariables(root, predeclared):
    _setScopeParents(root)
    info = findVarDeclInfo(root, predeclared)

    lvars = [expr for expr in info if isinstance(expr, ast.Local)]
    forbidden = set()
    #If var has any defs which aren't a literal or local, mark it as a leaf node (it can't be merged into something)
    for var in lvars:
        if not all(isinstance(expr, (ast.Local, ast.Literal)) for expr in info[var].defs):
            forbidden.add(var)
        elif info[var].declScope is not None:
            forbidden.add(var)

    sccs = graph_util.tarjanSCC(lvars, lambda var:([] if var in forbidden else info[var].defs))
    #the sccs will be in topolgical order
    varmap = {}
    for scc in sccs:
        if forbidden.isdisjoint(scc):
            alldefs = []
            for expr in scc:
                for def_ in info[expr].defs:
                    if def_ not in scc:
                        alldefs.append(varmap[def_])
            if len(set(alldefs)) == 1:
                target = alldefs[0]
                if all(var.dtype == target.dtype for var in scc):
                    scope = ast.StatementBlock.join(*(info[var].scope for var in scc))
                    scope = ast.StatementBlock.join(scope, info[target].declScope) #scope is unchanged if declScope is none like usual
                    if info[target].declScope is None or info[target].declScope == scope:
                        for var in scc:
                            varmap[var] = target
                        info[target].scope = ast.StatementBlock.join(scope, info[target].scope)
                        continue
        #fallthrough if merging is impossible
        for var in scc:
            varmap[var] = var
            if len(info[var].defs) > 1:
                forbidden.add(var)
    _preorder(root, partial(_replaceExpressions, rdict=varmap))

_oktypes = ast.BinaryInfix, ast.Local, ast.Literal, ast.Parenthesis, ast.Ternary, ast.TypeName, ast.UnaryPrefix
def hasSideEffects(expr):
    if not isinstance(expr, _oktypes):
        return True
    #check for division by 0. If it's a float or dividing by nonzero literal, it's ok
    elif isinstance(expr, ast.BinaryInfix) and expr.opstr in ('/','%'):
        if expr.dtype not in (objtypes.FloatTT, objtypes.DoubleTT):
            divisor = expr.params[-1]
            if not isinstance(divisor, ast.Literal) or divisor.val == 0:
                return True
    return False

def _inlineVariables(root):
    #first find all variables with a single def and use
    defs = collections.defaultdict(list)
    uses = collections.defaultdict(int)

    def visitExprFindDefs(expr):
        if expr.isLocalAssign():
            defs[expr.params[0]].append(expr)
        elif isinstance(expr, ast.Local):
            uses[expr] += 1

    def visitFindDefs(scope, item):
        if item.expr is not None:
            stack = [item.expr]
            while stack:
                expr = stack.pop()
                visitExprFindDefs(expr)
                stack.extend(expr.params)

    _preorder(root, visitFindDefs)
    #These should have 2 uses since the initial assignment also counts
    replacevars = {k for k,v in defs.items() if len(v)==1 and uses[k]==2 and k.dtype == v[0].params[1].dtype}
    def doReplacement(item, pairs):
        old, new = item.expr.params
        assert(isinstance(old, ast.Local) and old.dtype == new.dtype)
        stack = [(True, (True, item2, expr)) for item2, expr in reversed(pairs) if expr is not None]
        while stack:
            recurse, args = stack.pop()

            if recurse:
                canReplace, parent, expr = args
                stack.append((False, expr))

                #For ternaries, we don't want to replace into the conditionally
                #evaluated part, but we still need to check those parts for
                #barriers. For both ternaries and short circuit operators, the
                #first param is always evaluated, so it is safe
                if isinstance(expr, ast.Ternary) or isinstance(expr, ast.BinaryInfix) and expr.opstr in ('&&','||'):
                    for param in reversed(expr.params[1:]):
                        stack.append((True, (False, expr, param)))
                    stack.append((True, (canReplace, expr, expr.params[0])))
                #For assignments, we unroll the LHS arguments, because if assigning
                #to an array or field, we don't want that to serve as a barrier
                elif isinstance(expr, ast.Assignment):
                    left, right = expr.params
                    stack.append((True, (canReplace, expr, right)))
                    if isinstance(left, (ast.ArrayAccess, ast.FieldAccess)):
                        for param in reversed(left.params):
                            stack.append((True, (canReplace, left, param)))
                    else:
                        assert(isinstance(left, ast.Local))
                else:
                    for param in reversed(expr.params):
                        stack.append((True, (canReplace, expr, param)))

                if expr == old:
                    if canReplace:
                        if isinstance(parent, ast.JavaExpression):
                            params = parent.params = list(parent.params)
                            params[params.index(old)] = new
                        else: #replacing in a top level statement
                            assert(parent.expr == old)
                            parent.expr = new
                    return canReplace
            else:
                expr = args
                if hasSideEffects(expr):
                    return False
        return False

    def visitReplace(scope):
        newstatements = []
        for item in reversed(scope.statements):
            for sub in item.getScopes():
                visitReplace(sub)

            if isinstance(item.expr, ast.Assignment) and item.expr.params[0] in replacevars:
                expr_roots = []
                for item2 in newstatements:
                    #Don't inline into a while condition as it may be evaluated more than once
                    if not isinstance(item2, ast.WhileStatement):
                        expr_roots.append((item2, item2.expr))
                    if item2.getScopes():
                        break
                success = doReplacement(item, expr_roots)
                if success:
                    continue
            newstatements.insert(0, item)
        scope.statements = newstatements
    visitReplace(root)

def _createDeclarations(root, predeclared):
    _setScopeParents(root)
    info = findVarDeclInfo(root, predeclared)
    localdefs = collections.defaultdict(list)
    newvars = [var for var in info if isinstance(var, ast.Local) and info[var].declScope is None]
    remaining = set(newvars)

    #The compiler treats statements as if they can throw any exception at any time, so
    #it may think variables are not definitely assigned even when they really are.
    #Therefore, we give an unused initial value to every variable declaration
    #TODO - find a better way to handle this
    _init_d = {objtypes.BoolTT: ast.Literal.FALSE,
            objtypes.IntTT: ast.Literal.ZERO,
            objtypes.FloatTT: ast.Literal.FZERO,
            objtypes.DoubleTT: ast.Literal.DZERO}
    def mdVisitVarUse(var):
        decl = ast.VariableDeclarator(ast.TypeName(var.dtype), var)
        right = _init_d.get(var.dtype, ast.Literal.NULL)
        localdefs[info[var].scope].append( ast.LocalDeclarationStatement(decl, right) )
        remaining.remove(var)

    def mdVisitScope(scope):
        if isinstance(scope, ast.StatementBlock):
            for i,stmt in enumerate(scope.statements):
                if isinstance(stmt, ast.ExpressionStatement):
                    if isinstance(stmt.expr, ast.Assignment):
                        var, right = stmt.expr.params
                        if var in remaining and scope == info[var].scope:
                            decl = ast.VariableDeclarator(ast.TypeName(var.dtype), var)
                            new = ast.LocalDeclarationStatement(decl, right)
                            scope.statements[i] = new
                            remaining.remove(var)
                if stmt.expr is not None:
                    top = stmt.expr
                    for expr in top.postFlatIter():
                        if expr in remaining:
                            mdVisitVarUse(expr)
                for sub in stmt.getScopes():
                    mdVisitScope(sub)

    mdVisitScope(root)
    # print remaining
    assert(not remaining)
    assert(None not in localdefs)
    for scope, ldefs in localdefs.items():
        scope.statements = ldefs + scope.statements

def _createTernaries(scope, item):
    if isinstance(item, ast.IfStatement) and len(item.getScopes()) == 2:
        block1, block2 = item.getScopes()

        if (len(block1.statements) == len(block2.statements) == 1) and block1.jumpKey == block2.jumpKey:
            s1, s2 = block1.statements[0], block2.statements[0]
            e1, e2 = s1.expr, s2.expr

            if isinstance(s1, ast.ReturnStatement) and isinstance(s2, ast.ReturnStatement):
                expr = None if e1 is None else ast.Ternary(item.expr, e1, e2)
                item = ast.ReturnStatement(expr, s1.tt)
            if isinstance(s1, ast.ExpressionStatement) and isinstance(s2, ast.ExpressionStatement):
                if isinstance(e1, ast.Assignment) and isinstance(e2, ast.Assignment):
                    # if e1.params[0] == e2.params[0] and max(e1.params[1].complexity(), e2.params[1].complexity()) <= 1:
                    if e1.params[0] == e2.params[0]:
                        expr = ast.Ternary(item.expr, e1.params[1], e2.params[1])
                        temp = ast.ExpressionStatement(ast.Assignment(e1.params[0], expr))

                        if not block1.doesFallthrough():
                            assert(not block2.doesFallthrough())
                            item = ast.StatementBlock(item.func, item.continueKey, item.breakKey, [temp], block1.jumpKey)
                        else:
                            item = temp
    if item.expr is not None:
        item.expr = _simplifyExpressions(item.expr)
    return [item]

def _fixExprStatements(scope, item, namegen):
    if isinstance(item, ast.ExpressionStatement):
        if not isinstance(item.expr, (ast.Assignment, ast.ClassInstanceCreation, ast.MethodInvocation, ast.Dummy)):
            right = item.expr
            left = ast.Local(right.dtype, lambda expr:namegen.getPrefix('dummy'))
            decl = ast.VariableDeclarator(ast.TypeName(left.dtype), left)
            item = ast.LocalDeclarationStatement(decl, right)
    return [item]

def _addCastsAndParens(scope, item, env):
    item.addCastsAndParens(env)

def _chooseJump(choices):
    for b, t in choices:
        if b is None:
            return b, t
    for b, t in choices:
        if b.label is not None:
            return b, t
    return choices[0]

def _generateJumps(scope, targets=collections.OrderedDict(), fallthroughs=NONE_SET, dryRun=False):
    assert(None in fallthroughs)
    #breakkey can be None with non-None jumpkey when we're a scope in a switch statement that falls through
    #and the end of the switch statement is unreachable
    assert(scope.breakKey is not None or scope.jumpKey is None or not scope.labelable)
    if scope.jumpKey not in fallthroughs:
        assert(not scope.statements or not isinstance(scope.statements[-1], (ast.ReturnStatement, ast.ThrowStatement)))
        vals = [k for k,v in targets.items() if v == scope.jumpKey]
        assert(vals)
        jump = _chooseJump(vals)
        if not dryRun:
            scope.statements.append(ast.JumpStatement(*jump))

    for item in reversed(scope.statements):
        if not item.getScopes():
            fallthroughs = NONE_SET
            continue

        if isinstance(item, ast.WhileStatement):
            fallthroughs = frozenset([None, item.continueKey])
        else:
            fallthroughs |= frozenset([item.breakKey])

        newtargets = targets.copy()
        if isinstance(item, ast.WhileStatement):
            newtargets[None, True] = item.continueKey
            newtargets[item, True] = item.continueKey
        if isinstance(item, (ast.WhileStatement, ast.SwitchStatement)):
            newtargets[None, False] = item.breakKey
        newtargets[item, False] = item.breakKey

        for subscope in reversed(item.getScopes()):
            _generateJumps(subscope, newtargets, fallthroughs, dryRun=dryRun)
            if isinstance(item, ast.SwitchStatement):
                fallthroughs = frozenset([None, subscope.continueKey])
        fallthroughs = frozenset([None, item.continueKey])

def _pruneVoidReturn(scope):
    if scope.statements:
        last = scope.statements[-1]
        if isinstance(last, ast.ReturnStatement) and last.expr is None:
            scope.statements.pop()

def generateAST(method, graph, forbidden_identifiers):
    env = method.class_.env
    namegen = NameGen(forbidden_identifiers)
    class_ = method.class_
    inputTypes = parseMethodDescriptor(method.descriptor, unsynthesize=False)[0]
    tts = objtypes.verifierToSynthetic_seq(inputTypes)

    if graph is not None:
        entryNode, nodes = graphproxy.createGraphProxy(graph)
        if not method.static:
            entryNode.invars[0].name = 'this'

        setree = structuring.structure(entryNode, nodes, (method.name == '<clinit>'))
        ast_root, varinfo = astgen.createAST(method, graph, setree, namegen)

        argsources = [varinfo.var(entryNode, var) for var in entryNode.invars]
        disp_args = argsources if method.static else argsources[1:]
        for expr, tt in zip(disp_args, tts):
            expr.dtype = tt

        decls = [ast.VariableDeclarator(ast.TypeName(expr.dtype), expr) for expr in disp_args]
        ################################################################################################
        ast_root.bases = (ast_root,) #needed for our setScopeParents later

        # print ast_root.print_()
        assert(_generateJumps(ast_root, dryRun=True) is None)
        _preorder(ast_root, _fixObjectCreations)
        boolize.boolizeVars(ast_root, argsources)
        _simplifyBlocks(ast_root)
        assert(_generateJumps(ast_root, dryRun=True) is None)

        _mergeVariables(ast_root, argsources)
        _preorder(ast_root, _createTernaries)
        _inlineVariables(ast_root)
        _simplifyBlocks(ast_root)
        _preorder(ast_root, _createTernaries)
        _inlineVariables(ast_root)
        _simplifyBlocks(ast_root)

        _createDeclarations(ast_root, argsources)
        _preorder(ast_root, partial(_fixExprStatements, namegen=namegen))
        _preorder(ast_root, partial(_addCastsAndParens, env=env))
        _generateJumps(ast_root)
        _pruneVoidReturn(ast_root)
    else: #abstract or native method
        ast_root = None
        argsources = [ast.Local(tt, lambda expr:namegen.getPrefix('arg')) for tt in tts]
        decls = [ast.VariableDeclarator(ast.TypeName(expr.dtype), expr) for expr in argsources]

    flags = method.flags - set(['BRIDGE','SYNTHETIC','VARARGS'])
    if method.name == '<init>': #More arbtirary restrictions. Yay!
        flags = flags - set(['ABSTRACT','STATIC','FINAL','NATIVE','STRICTFP','SYNCHRONIZED'])

    flagstr = ' '.join(map(str.lower, sorted(flags)))
    inputTypes, returnTypes = parseMethodDescriptor(method.descriptor, unsynthesize=False)
    ret_tt = objtypes.verifierToSynthetic(returnTypes[0]) if returnTypes else ('.void',0)
    return ast2.MethodDef(class_, flagstr, method.name, ast.TypeName(ret_tt), decls, ast_root)

########NEW FILE########
__FILENAME__ = reserved
reserved_identifiers = '''
abstract
assert
boolean
break
byte
case
catch
char
class
const
continue
default
do
double
else
enum
extends
false
final
finally
float
for
goto
if
implements
import
instanceof
int
interface
long
native
new
null
package
private
protected
public
return
short
static
strictfp
super
switch
synchronized
this
throw
throws
transient
true
try
void
volatile
while
'''.split()
########NEW FILE########
__FILENAME__ = setree
import itertools

def update(self, items):
    self.entryBlock = items[0].entryBlock
    self.nodes = frozenset.union(*(i.nodes for i in items))
    temp = set(self.nodes)
    siter = itertools.chain.from_iterable(i.successors for i in items) 
    self.successors = [n for n in siter if not n in temp and not temp.add(n)]

class SEBlockItem(object):
    def __init__(self, node):
        self.successors = node.norm_suc_nl #don't include backedges or exceptional edges
        self.node = node 
        self.nodes = frozenset([node])
        self.entryBlock = node
    
    def getScopes(self): return ()    

class SEScope(object):
    def __init__(self, items):
        self.items = items
        update(self, items)

    def getScopes(self): return ()    

class SEWhile(object):
    def __init__(self, scope):
        self.body = scope
        update(self, [scope])

    def getScopes(self): return self.body,    

class SETry(object):
    def __init__(self, tryscope, catchscope, toptts, catchvar):
        self.scopes = tryscope, catchscope
        self.toptts = toptts
        self.catchvar = catchvar #none if ignored
        update(self, self.scopes)

    def getScopes(self): return self.scopes

class SEIf(object):
    def __init__(self, head, newscopes):
        assert(len(newscopes) == 2)
        self.scopes = newscopes
        self.head = head
        update(self, [head] + newscopes)

    def getScopes(self): return self.scopes

class SESwitch(object):
    def __init__(self, head, newscopes):
        self.scopes = newscopes
        self.head = head
        self.ordered = newscopes
        update(self, [head] + newscopes)

        jump = head.node.block.jump
        keysets = {head.node.blockdict[b.key,False]:jump.reverse.get(b) for b in jump.getNormalSuccessors()}
        assert(keysets.values().count(None) == 1)
        self.ordered_keysets = [keysets[item.entryBlock] for item in newscopes]

    def getScopes(self): return self.scopes

########NEW FILE########
__FILENAME__ = stringescape
#double quote, backslash, and newlines are forbidden
ok_chars =  " !#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~"
ok_chars = frozenset(ok_chars)

#these characters cannot use unicode escape codes due to the way Java escaping works
late_escape = {u'\u0009':r'\t', u'\u000a':r'\n', u'\u000d':r'\r', u'\u0022':r'\"', u'\u005c':r'\\'}

def escapeString(u):
    if set(u) <= ok_chars:
        return u 

    escaped = []
    for c in u:
        if c in ok_chars:
            escaped.append(c)
        elif c in late_escape:
            escaped.append(late_escape[c])
        else:
            i = ord(c)
            if i <= 0xFFFF:
                escaped.append(r'\u{0:04x}'.format(i))
            else:
                i -= 0x10000
                high = 0xD800 + (i>>10)
                low = 0xDC00 + (i & 0x3FF)
                escaped.append(r'\u{0:04x}\u{1:04x}'.format(high,low))
    return ''.join(escaped)
########NEW FILE########
__FILENAME__ = structuring
import collections, itertools, functools
ddict = collections.defaultdict

from .. import graph_util
from . import graphproxy

from ..ssa import ssa_jumps
from ..ssa.exceptionset import ExceptionSet
from .setree import SEBlockItem, SEScope, SEIf, SESwitch, SETry, SEWhile

# This module is responsible for transforming an arbitrary control flow graph into a tree
# of nested structures corresponding to Java control flow statements. This occurs in
# several main steps
#
# Preprocessing - create graph view and ensure that there are no self loops and every node
#   has only one incoming edge type
# Structure loops - ensure every loop has a single entry point. This may result in
#   exponential code duplication in pathological cases
# Structure exceptions - create dummy nodes for every throw exception type for every node
# Structure conditionals - order switch targets consistent with fallthrough and create
#   dummy nodes where necessary
# Create constraints - sets up the constraints used to represent nested statements
# Merge exceptions - try to merge as any try constraints as possible. This is done by
#   extending one until it covers the cases that another one handles, allowing the second
#   to be removed
# Parallelize exceptions - freeze try constraints and turn them into multicatch blocks
#   where possible (not implemented yet)
# Complete scopes - expand scopes to try to reduce the number of successors
# Add break scopes - add extra scope statements so extra successors can be represented as
#   labeled breaks

#########################################################################################
class DominatorInfo(object):
    def __init__(self, root):
        self._doms = doms = {root:frozenset([root])}
        stack = [root]
        while stack:
            cur = stack.pop()
            assert(cur not in stack)
            for child in cur.successors:
                new = doms[cur] | frozenset([child])
                old = doms.get(child)
                if new != old:
                    new = new if old is None else (old & new)
                    assert(child in new)
                if old is not None:
                    assert(new == old or len(new) < len(old))
                if new != old:
                    doms[child] = new
                    if child not in stack:
                        stack.append(child)
        self.nodeset = set(self._doms)
        self.root = root

    def dominators(self, node):
        return self._doms[node]

    def ordered(self, node): #for debugging
        return sorted(self._doms[node], key=lambda n:len(self._doms[n]))

    def dominator(self, *nodes):
        '''Get the common dominator of nodes'''
        doms = reduce(frozenset.intersection, map(self._doms.get, nodes))
        return max(doms, key=lambda n:len(self._doms[n]))

    def set_extend(self, dom, nodes):
        nodes = list(nodes) + [dom]
        if hasattr(dom, 'predecessors_nl'):
            pred_nl_func = lambda x:x.predecessors_nl if x is not dom else []
        else: #slower fallback for if we're called before the _noloop information is generated
            pred_nl_func = lambda x:[y for y in x.predecessors if x is not dom and x not in self._doms[y]]
        return frozenset(graph_util.topologicalSort(nodes, pred_nl_func))

    def area(self, node): return ClosedSet([k for k,v in self._doms.items() if node in v], node, self)
    def extend(self, dom, nodes): return ClosedSet(self.set_extend(dom, nodes), dom, self)
    def extend2(self, nodes): return self.extend(self.dominator(*nodes), nodes)
    def single(self, head): return ClosedSet([head], head, self)

#Immutable class representing a dominator closed set of nodes
#TODO clean up usage (remove copy() calls, etc.)
class ClosedSet(object):
    __slots__ = "nodes", "head", "info"

    def __init__(self, nodes, head, info):
        self.nodes = frozenset(nodes)
        self.head = head
        self.info = info
        if nodes:
            assert(head in nodes)
            assert(info.dominator(*nodes) == head)

    def touches(self, other): return not self.nodes.isdisjoint(other.nodes)
    def isdisjoint(self, other): return self.nodes.isdisjoint(other.nodes)
    def issuperset(self, other): return self.nodes.issuperset(other.nodes)
    def issubset(self, other): return self.nodes.issubset(other.nodes)

    def __or__(self, other):
        assert(type(self) == type(other))

        if not other.nodes or self is other:
            return self
        elif not self.nodes:
            return other
        assert(self.head is not None and other.head is not None)
        assert(self.info is other.info)

        if self.head in other.nodes:
            self, other = other, self

        nodes, head, info = self.nodes, self.head, self.info
        nodes |= other.nodes
        if other.head not in self.nodes:
            head = info.dominator(head, other.head)
            nodes = info.set_extend(head, nodes)
        return ClosedSet(nodes, head, info)

    def __and__(self, other):
        assert(type(self) == type(other))

        nodes = self.nodes & other.nodes
        if not nodes:
            return ClosedSet.EMPTY

        if self.head in other.nodes:
            self, other = other, self
        if other.head in self.nodes:
            head = other.head
        else:
            head = self.info.dominator(*nodes)
        return ClosedSet(nodes, head, self.info)

    @staticmethod
    def union(*sets):
        return reduce(ClosedSet.__or__, sets, ClosedSet.EMPTY)

    def __str__(self): # for debugging
        return 'set{} ({} nodes)'.format(self.head, len(self.nodes))
    __repr__ = __str__

    def __lt__(self, other): return self.nodes < other.nodes
    def __le__(self, other): return self.nodes <= other.nodes
    def __gt__(self, other): return self.nodes > other.nodes
    def __ge__(self, other): return self.nodes >= other.nodes
ClosedSet.EMPTY = ClosedSet(frozenset(), None, None)

#########################################################################################
class ScopeConstraint(object):
    def __init__(self, lbound, ubound):
        self.lbound = lbound
        self.ubound = ubound

_count = itertools.count()
_gcon_tags = 'while','try','switch','if','scope'
class CompoundConstraint(object):
    def __init__(self, tag, head, scopes):
        assert(tag in _gcon_tags)
        self.id = next(_count) #for debugging purposes
        self.tag = tag
        self.scopes = scopes
        self.head = head
        # self.heads = frozenset([head]) if head is not None else frozenset()
        #only used by try constraints, but we leave dummy sets for the rest
        self.forcedup = self.forceddown = frozenset()

        self.lbound = ClosedSet.union(*[scope.lbound for scope in self.scopes])
        self.ubound = ClosedSet.union(*[scope.ubound for scope in self.scopes])
        if head is not None:
            assert(head in self.lbound.nodes and head in self.ubound.nodes)
        assert(self.ubound >= self.lbound)

    def __str__(self): return self.tag+str(self.id)
    __repr__ = __str__

def WhileCon(dom, head):
    ubound = dom.area(head)
    lbound = dom.extend(head, [n2 for n2 in head.predecessors if head in dom.dominators(n2)])
    return CompoundConstraint('while', None, [ScopeConstraint(lbound, ubound)])

def TryCon(dom, trynode, target, cset, catchvar):
    trybound = dom.single(trynode)
    tryscope = ScopeConstraint(trybound, trybound)

    #Catch scopes are added later, once all the merging is finished
    new = CompoundConstraint('try', None, [tryscope])
    new.forcedup = set()
    new.forceddown = set()
    new.target = target
    new.cset = cset
    new.catchvar = catchvar

    assert(len(new.target.successors) == 1)
    new.orig_target = new.target.successors[0]
    return new

def FixedScopeCon(lbound):
    return CompoundConstraint('scope', None, [ScopeConstraint(lbound, lbound)])
#########################################################################################

def structureLoops(nodes):
    todo = nodes
    while_heads = []
    while todo:
        newtodo = []
        temp = set(todo)
        sccs = graph_util.tarjanSCC(todo, lambda block:[x for x in block.predecessors if x in temp])

        for scc in sccs:
            if len(scc) <= 1:
                continue

            scc_set = set(scc)
            entries = [n for n in scc if not scc_set.issuperset(n.predecessors)]

            if len(entries) <= 1:
                head = entries[0]
            else:
                #if more than one entry point into the loop, we have to choose one as the head and duplicate the rest
                print 'Warning, multiple entry point loop detected. Generated code may be extremely large',
                print '({} entry points, {} blocks)'.format(len(entries), len(scc))

                def loopSuccessors(head, block):
                    if block == head:
                        return []
                    return [x for x in block.successors if x in scc_set]

                reaches = [(n, graph_util.topologicalSort(entries, functools.partial(loopSuccessors, n))) for n in scc]
                for head, reachable in reaches:
                    reachable.remove(head)

                head, reachable = min(reaches, key=lambda t:(len(t[1]), -len(t[0].predecessors)))
                assert(head not in reachable)
                print 'Duplicating {} nodes'.format(len(reachable))
                newnodes = graphproxy.duplicateNodes(reachable, scc_set)
                newtodo += newnodes
                nodes += newnodes

            newtodo.extend(scc)
            newtodo.remove(head)
            while_heads.append(head)
        todo = newtodo
    return while_heads

def structureExceptions(nodes):
    thrownodes = [n for n in nodes if n.block and isinstance(n.block.jump, ssa_jumps.OnException)]

    newinfos = []
    for n in thrownodes:
        manager = n.block.jump.cs
        thrownvar = n.block.jump.params[0]

        mycsets = {}
        mytryinfos = []
        newinfos.append((n, manager.mask, mycsets, mytryinfos))

        temp = ExceptionSet.EMPTY
        for cset in manager.sets.values():
            assert(not temp & cset)
            temp |= cset
        assert(temp == manager.mask)

        for handler, cset in manager.sets.items():
            en = n.blockdict[handler.key, True]
            mycsets[en] = cset

            en.predecessors.remove(n)
            n.successors.remove(en)

            caughtvars = [v2 for (v1,v2) in zip(n.outvars[en], en.invars) if v1 == thrownvar]
            assert(len(caughtvars) <= 1)
            caughtvar = caughtvars.pop() if caughtvars else None

            outvars = [(None if v == thrownvar else v) for v in n.outvars[en]]
            del n.outvars[en]

            for tt in cset.getTopTTs():
                top = ExceptionSet.fromTops(cset.env, tt[0])
                new = en.indirectEdges([])
                new.predecessors.append(n)
                n.successors.append(new)
                n.eassigns[new] = outvars #should be safe to avoid copy as we'll never modify it
                nodes.append(new)
                mytryinfos.append((top, new, caughtvar))

    return newinfos

def structureConditionals(entryNode, nodes):
    dom = DominatorInfo(entryNode)
    switchnodes = [n for n in nodes if n.block and isinstance(n.block.jump, ssa_jumps.Switch)]
    ifnodes = [n for n in nodes if n.block and isinstance(n.block.jump, ssa_jumps.If)]

    #For switch statements, we can't just blithely indirect all targets as that interferes with fallthrough behavior
    switchinfos = []
    for n in switchnodes:
        targets = n.successors
        #a proper switch block must be dominated by its entry point
        #and all other nonloop predecessors must be dominated by a single other target
        #keep track of remaining good targets, bad ones will be found later by elimination
        target_set = frozenset(targets)
        good = []
        parents = {}
        for target in targets:
            if n not in dom.dominators(target):
                continue

            preds = [x for x in target.predecessors if x != n and target not in dom.dominators(x)]
            for pred in preds:
                choices = dom.dominators(pred) & target_set
                if len(choices) != 1:
                    break
                choice = min(choices)
                if parents.setdefault(target, choice) != choice:
                    break
            else:
                #passed all the tests for now, target appears valid
                good.append(target)

        while 1:
            size = len(parents), len(good)
            #prune bad parents and children from dict
            for k,v in parents.items():
                if k not in good:
                    del parents[k]
                elif v not in good:
                    del parents[k]
                    good.remove(k)

            #make sure all parents are unique. In case they're not, choose one arbitrarily
            chosen = {}
            for target in good:
                if target in parents and chosen.setdefault(parents[target], target) != target:
                    del parents[target]
                    good.remove(target)

            if size == (len(parents), len(good)): #nothing changed this iteration
                break

        #Now we need an ordering of the good blocks consistent with fallthrough
        #regular topoSort can't be used since we require chains to be immediately contiguous
        #which a topological sort doesn't garuentee
        children = {v:k for k,v in parents.items()}
        leaves = [x for x in good if x not in children]
        ordered = []
        for leaf in leaves:
            cur = leaf
            while cur is not None:
                ordered.append(cur)
                cur = parents.get(cur)
        ordered = ordered[::-1]
        assert(len(ordered) == len(good))

        #now handle the bad targets
        for x in targets:
            if x not in good:
                new = x.indirectEdges([n])
                nodes.append(new)
                ordered.append(new)
        assert(len(ordered) == len(targets))
        switchinfos.append((n, ordered))

        #if we added new nodes, update dom info
        if len(good) < len(targets):
            dom = DominatorInfo(entryNode)

    #Now handle if statements. This is much simpler since we can just indirect everything
    ifinfos = []
    for n in ifnodes:
        targets = [x.indirectEdges([n]) for x in n.successors[:]]
        nodes.extend(targets)
        ifinfos.append((n, targets))
    return switchinfos, ifinfos

def createConstraints(dom, while_heads, newtryinfos, switchinfos, ifinfos):
    constraints = []
    for head in while_heads:
        constraints.append(WhileCon(dom, head))

    masks = {n:mask for n, mask, _, _ in newtryinfos}
    forbid_dicts = ddict(lambda:masks.copy())
    for n, mask, csets, tryinfos in newtryinfos:
        for ot, cset in csets.items():
            forbid_dicts[ot][n] -= cset
    for forbid in forbid_dicts.values():
        for k in forbid.keys():
            if not forbid[k]:
                del forbid[k]

    for n, mask, csets, tryinfos in newtryinfos:
        cons = [TryCon(dom, n, target, top, caughtvar) for top, target, caughtvar in tryinfos]

        for con, con2 in itertools.product(cons, repeat=2):
            if con is con2:
                continue
            if not (con.cset - con2.cset): #cset1 is subset of cset2
                assert(con2.cset - con.cset)
                con.forcedup.add(con2)
                con2.forceddown.add(con)

        for con in cons:
            con.forbidden = forbid_dicts[con.orig_target].copy()

            if n in con.forbidden:
                for con2 in con.forceddown:
                    con.forbidden[n] -= con2.cset
                assert(con.cset.isdisjoint(con.forbidden[n]))
                if not con.forbidden[n]:
                    del con.forbidden[n]
            assert(all(con.forbidden.values()))
        constraints.extend(cons)

    for n, ordered in switchinfos:
        last = []
        scopes = []
        for target in reversed(ordered):
            #find all nodes which fallthrough to the next switch block
            #these must be included in the current switch block
            fallthroughs = [x for x in last if target in dom.dominators(x)]
            assert(n not in fallthroughs)
            assert(len(last) - len(fallthroughs) <= 1) #every predecessor should be accounted for except n itself
            last = [x for x in target.predecessors if target not in dom.dominators(x)] #make sure not to include backedges

            lbound = dom.extend(target, fallthroughs)
            ubound = dom.area(target)
            assert(lbound <= ubound and n not in ubound.nodes)
            scopes.append(ScopeConstraint(lbound, ubound))
        con = CompoundConstraint('switch', n, list(reversed(scopes)))
        constraints.append(con)

    for n, targets in ifinfos:
        scopes = []
        for target in targets:
            lbound = dom.single(target)
            ubound = dom.area(target)
            scopes.append(ScopeConstraint(lbound, ubound))
        con = CompoundConstraint('if', n, scopes)
        constraints.append(con)

    return constraints

def orderConstraints(dom, constraints, nodes):
    DummyParent = None #dummy root
    children = ddict(list)
    frozen = set()

    node_set = ClosedSet(nodes, dom.root, dom)
    assert(set(dom._doms) == node_set.nodes)
    for item in constraints:
        assert(item.lbound <= node_set)
        assert(item.ubound <= node_set)
        for scope in item.scopes:
            assert(scope.lbound <= node_set)
            assert(scope.ubound <= node_set)

    todo = constraints[:]
    while todo:
        items = []
        queue = [todo[0]]
        iset = set(queue) #set of items to skip when expanding connected component
        nset = ClosedSet.EMPTY
        parents = set() #items that must be above the entire component

        #Find a connected component of non frozen constraints based on intersecting lbounds
        while queue:
            item = queue.pop()
            if item in frozen:
                parents.add(item)
                continue

            items.append(item)
            #list comprehension adds to iset as well to ensure uniqueness
            queue += [i2 for i2 in item.forcedup if not i2 in iset and not iset.add(i2)]
            queue += [i2 for i2 in item.forceddown if not i2 in iset and not iset.add(i2)]

            if not item.lbound.issubset(nset):
                nset |= item.lbound
                hits = [i2 for i2 in constraints if nset.touches(i2.lbound)]
                queue += [i2 for i2 in hits if not i2 in iset and not iset.add(i2)]
        assert(nset <= node_set and nset.nodes)

        #Find candidates for the new root of the connected component.
        #It must have a big enough ubound and also can't have nonfrozen forced parents
        candidates = [i for i in items if i.ubound.issuperset(nset)]
        candidates = [i for i in candidates if i.forcedup.issubset(frozen)]

        #make sure for each candidate that all of the nested items fall within a single scope
        cscope_assigns = []
        for cnode in candidates:
            svals = ddict(lambda:ClosedSet.EMPTY)
            bad = False
            for item in items:
                if item is cnode:
                    continue

                scopes = [s for s in cnode.scopes if item.lbound.touches(s.ubound)]
                if len(scopes) != 1 or not scopes[0].ubound.issuperset(item.lbound):
                    bad = True
                    break
                svals[scopes[0]] |= item.lbound

            if not bad:
                cscope_assigns.append((cnode, svals))

        cnode, svals = cscope_assigns.pop() #choose candidate arbitrarily if more than 1
        assert(len(svals) <= len(cnode.scopes))
        for scope, ext in svals.items():
            scope.lbound |= ext
            assert(scope.lbound <= scope.ubound)

        cnode.lbound |= nset #should be extended too
        assert(cnode.lbound <= cnode.ubound)
        # assert(cnode.lbound == (cnode.heads.union(*[s.lbound for s in cnode.scopes]))) TODO

        #find lowest parent
        parent = DummyParent
        while not parents.isdisjoint(children[parent]):
            temp = parents.intersection(children[parent])
            assert(len(temp) == 1)
            parent = temp.pop()

        if parent is not None:
            assert(cnode.lbound <= parent.lbound)

        children[parent].append(cnode)
        todo.remove(cnode)
        frozen.add(cnode)

    #make sure items are nested
    for k, v in children.items():
        temp = set()
        for child in v:
            assert(temp.isdisjoint(child.lbound.nodes))
            temp |= child.lbound.nodes
        assert(k is None or temp <= k.lbound.nodes)

    #Add a root so it is a tree, not a forest
    croot = FixedScopeCon(node_set)
    children[croot] = children[None]
    del children[None]
    return croot, children

def mergeExceptions(dom, children, constraints, nodes):
    parents = {} # con -> parent, parentscope
    for k, cs in children.items():
        for child in cs:
            scopes = [s for s in k.scopes if s.lbound.touches(child.lbound)]
            assert(child not in parents and len(scopes) == 1)
            parents[child] = k, scopes[0]
    assert(set(parents) == set(constraints))

    def removeFromTree(con):
        parent, pscope = parents[con]
        children[parent] += children[con]
        for x in children[con]:
            scopes = [s for s in parent.scopes if s.lbound.touches(x.lbound)]
            parents[x] = parent, scopes[0]
        children[parent].remove(con)
        del children[con]
        del parents[con]

    def insertInTree(con, parent):
        scopes = [s for s in parent.scopes if s.lbound.touches(con.lbound)]
        parents[con] = parent, scopes[0]
        children[con] = []

        for scope in con.scopes:
            hits = [c for c in children[parent] if c.lbound.touches(scope.lbound)]
            for child in hits:
                assert(parents[child][0] == parent)
                parents[child] = con, scope
                children[con].append(child)
                children[parent].remove(child)
        children[parent].append(con)

    def unforbid(forbidden, newdown):
        for n in newdown.lbound.nodes:
            if n in forbidden:
                forbidden[n] -= newdown.cset
                if not forbidden[n]:
                    del forbidden[n]

    def tryExtend(con, newblocks, xCSet, xUps, xDowns, removed):
        forcedup = con.forcedup | xUps
        forceddown = con.forceddown | xDowns
        assert(con not in forceddown)
        forcedup.discard(con)
        if forcedup & forceddown:
            return False

        body = con.lbound | newblocks
        ubound = con.ubound
        for tcon in forcedup:
            ubound &= tcon.lbound

        while 1:
            done = True
            parent, pscope = parents[con]
            #Ugly hack to work around the fact that try bodies are temporarily stored
            #in the main constraint, not its scopes
            while not body <= (parent if parent.tag == 'try' else pscope).lbound:
                #Try to extend parent rather than just failing
                if parent.tag == 'try' and parent in forcedup:
                    #Note this call may mutate the parent
                    done = not tryExtend(parent, body, ExceptionSet.EMPTY, set(), set(), removed)
                    #Since the tree may have been updated, start over and rewalk the tree
                    if not done:
                        break

                body |= parent.lbound
                if parent in forcedup or not body <= ubound:
                    return False
                parent, pscope = parents[parent]
            if done:
                break

        for child in children[parent]:
            if child.lbound.touches(body):
                body |= child.lbound
        if not body <= ubound:
            return False

        cset = con.cset | xCSet
        forbidden = con.forbidden.copy()
        for newdown in (forceddown - con.forceddown):
            unforbid(forbidden, newdown)
        assert(all(forbidden.values()))

        for node in body.nodes:
            if node in forbidden and (cset & forbidden[node]):
                #The current cset is not compatible with the current partial order
                #Try to find some cons to force down in order to fix this
                bad = cset & forbidden[node]
                candidates = [c for c in trycons if c not in removed]
                candidates = [c for c in candidates if node in c.lbound.nodes and c.lbound.issubset(body)]
                candidates = [c for c in candidates if (c.cset & bad)]
                candidates = [c for c in candidates if c not in forcedup and c is not con]

                for topnd in candidates:
                    if topnd in forceddown:
                        continue

                    temp = topnd.forceddown - forceddown - removed
                    temp.add(topnd)
                    for newdown in temp:
                        unforbid(forbidden, newdown)

                    assert(con not in temp)
                    forceddown |= temp
                    bad = cset & forbidden.get(node, ExceptionSet.EMPTY)
                    if not bad:
                        break
                if bad:
                    assert(node not in con.lbound.nodes or cset - con.cset)
                    return False
        assert(forceddown.isdisjoint(forcedup))
        assert(all(forbidden.values()))
        for tcon in forceddown:
            assert(tcon.lbound <= body)

        #At this point, everything should be all right, so we need to update con and the tree
        con.lbound = body
        con.cset = cset
        con.forbidden = forbidden
        con.forcedup = forcedup
        con.forceddown = forceddown
        con.scopes[0].lbound = body
        con.scopes[0].ubound = ubound

        for new in con.forceddown:
            new.forcedup.add(con)
            new.forcedup |= forcedup

        for new in con.forcedup:
            unforbid(new.forbidden, con)
            for new2 in forceddown - new.forceddown:
                unforbid(new.forbidden, new2)
            new.forceddown.add(con)
            new.forceddown |= forceddown

        #Move con into it's new position in the tree
        removeFromTree(con)
        insertInTree(con, parent)
        return True

    trycons = [con for con in constraints if con.tag == 'try']
    # print 'Merging exceptions ({1}/{0}) trys'.format(len(constraints), len(trycons))
    topoorder = graph_util.topologicalSort(constraints, lambda cn:([parents[cn]] if cn in parents else []))
    trycons = sorted(trycons, key=topoorder.index)
    #note that the tree may be changed while iterating, but constraints should only move up

    removed = set()
    for con in trycons:
        if con in removed:
            continue

        #First find the actual upper bound for the try scope, since it's only the one node on creation
        #However, for now we set ubound to be all nodes not reachable from catch, instead of only those
        #dominated by the try node. That way we can expand and merge it. We'll fix it up once we're done
        assert(len(con.lbound.nodes) == 1)
        tryhead = con.lbound.head
        backnodes = dom.dominators(tryhead)
        catchreach = graph_util.topologicalSort([con.target], lambda node:[x for x in node.successors if x not in backnodes])
        ubound_s = set(nodes) - set(catchreach)
        con.ubound = ClosedSet(ubound_s, dom.root, dom)

        #Now find which cons we can try to merge with
        candidates = [c for c in trycons if c not in removed and c.orig_target == con.orig_target]
        candidates = [c for c in candidates if c.lbound.issubset(con.ubound)]
        candidates = [c for c in candidates if c not in con.forcedup]
        candidates.remove(con)

        success = {}
        for con2 in candidates:
            success[con2] = tryExtend(con, con2.lbound, con2.cset, con2.forcedup, con2.forceddown, removed)

        #Now find which ones can be removed
        def removeable(con2):
            okdiff = set([con,con2])
            if con2.lbound <= (con.lbound):
                if con2.forceddown <= (con.forceddown | okdiff):
                    if con2.forcedup <= (con.forcedup | okdiff):
                        if not con2.cset - con.cset:
                            return True
            return False

        for con2 in candidates:
            #Note that since our tryExtend is somewhat conservative, in rare cases we
            #may find that we can remove a constraint even if tryExtend failed on it
            #but the reverse should obviously never happen
            if not removeable(con2):
                assert(not success[con2])
                continue

            removed.add(con2)
            for tcon in trycons:
                if tcon not in removed and tcon is not con:
                    assert(con in tcon.forceddown or con2 not in tcon.forceddown)
                    assert(con in tcon.forcedup or con2 not in tcon.forcedup)
                tcon.forcedup.discard(con2)
                tcon.forceddown.discard(con2)

            assert(con not in removed)
            removeFromTree(con2)

    #Cleanup
    removed_nodes = frozenset(c.target for c in removed)
    constraints = [c for c in constraints if c not in removed]
    trycons = [c for c in trycons if c not in removed]

    for con in trycons:
        assert(not con.forcedup & removed)
        assert(not con.forceddown & removed)

        #For convienence, we were previously storing the try scope bounds in the main constraint bounds
        assert(len(con.scopes)==1)
        tryscope = con.scopes[0]
        tryscope.lbound = con.lbound
        tryscope.ubound = con.ubound
    # print 'Merging done'
    # print dict(collections.Counter(con.tag for con in constraints))

    #Now fix up the nodes. This is a little tricky.
    #Note, the _nl lists are also invalidated. They're fixed below once we create the new dom info
    nodes = [n for n in nodes if n not in removed_nodes]
    for node in nodes:
        node.predecessors = [x for x in node.predecessors if x not in removed_nodes]

        #start with normal successors and add exceptions back in
        node.successors = [x for x in node.successors if x in node.outvars]
        if node.eassigns:
            temp = {k.successors[0]:v for k,v in node.eassigns.items()}
            node.eassigns = ea = {}

            for con in trycons:
                if node in con.lbound.nodes and con.orig_target in temp:
                    ea[con.target] = temp[con.orig_target]
                    if node not in con.target.predecessors:
                        con.target.predecessors.append(node)
                    node.successors.append(con.target)
            assert(len(ea) >= len(temp))
        assert(removed_nodes.isdisjoint(node.successors))
    assert(dom.root not in removed_nodes)

    #Regenerate dominator info to take removed nodes into account
    node_set = set(nodes)
    dom = DominatorInfo(dom.root)
    assert(set(dom._doms) == node_set)
    calcNoLoopNeighbors(dom, nodes)

    def fixBounds(item):
        #note, we have to recalculate heads here too due to the altered graph
        oldl, oldu = item.lbound, item.ubound
        item.lbound = dom.extend2(item.lbound.nodes - removed_nodes)
        item.ubound = _dominatorUBoundClosure(dom, item.ubound.nodes - removed_nodes, item.ubound.head)
        assert(item.lbound.nodes <= oldl.nodes and item.ubound.nodes <= oldu.nodes)

    for con in constraints:
        fixBounds(con)
        for scope in con.scopes:
            fixBounds(scope)
    return dom, constraints, nodes

def fixTryConstraints(dom, constraints):
    #Add catchscopes and freeze other relations
    for con in constraints:
        if con.tag != 'try':
            continue

        lbound = dom.single(con.target)
        ubound = dom.area(con.target)
        cscope = ScopeConstraint(lbound, ubound)
        con.scopes.append(cscope)

        #After this point, forced relations and cset are frozen
        #So if a node is forbbiden, we can't expand to it at all
        cset = con.cset
        tscope = con.scopes[0]

        empty = ExceptionSet.EMPTY
        ubound_s = set(x for x in tscope.ubound.nodes if not (cset & con.forbidden.get(x, empty)))
        #Note, we use lbound head, not ubound head! The part dominated by lbound is what we actually care about
        tscope.ubound = _dominatorUBoundClosure(dom, ubound_s, tscope.lbound.head)
        del con.forbidden

        con.lbound = tscope.lbound | cscope.lbound
        con.ubound = tscope.ubound | cscope.ubound
        assert(tscope.lbound.issubset(tscope.ubound))
        assert(tscope.ubound.isdisjoint(cscope.ubound))

def _dominatorUBoundClosure(dom, ubound_s, head):
    #Make sure ubound is dominator closed by removing nodes
    ubound_s = set(x for x in ubound_s if head in dom.dominators(x))
    assert(head in ubound_s)
    done = len(ubound_s) <= 1
    while not done:
        done = True
        for x in list(ubound_s):
            xpreds_nl = [y for y in x.predecessors if x not in dom.dominators(y)] #pred nl list may not have been created yet
            if x != head and not ubound_s.issuperset(xpreds_nl):
                done = False
                ubound_s.remove(x)
                break
    assert(ubound_s == dom.extend(head, ubound_s).nodes)
    return ClosedSet(ubound_s, head, dom)

def _augmentingPath(startnodes, startset, endset, used, backedge, bound):
    #Find augmenting path via BFS
    #To make sure each node is used only once we treat it as if it were two nodes connected
    #by an internal edge of capacity 1. However, to save time we don't explicitly model this
    #instead it is encoded by the used set and rules on when we can go forward and backwards
    queue = collections.deque([(n,True,(n,)) for n in startnodes if n not in used])

    seen = set((n,True) for n in startnodes)
    while queue:
        pos, lastfw, path = queue.popleft()

        canfwd = not lastfw or pos not in used
        canback = pos in used and pos not in startset

        if canfwd:
            if pos in endset: #success!
                return path, None
            successors = [x for x in pos.norm_suc_nl if x in bound]
            for pos2 in successors:
                if (pos2, True) not in seen:
                    seen.add((pos2, True))
                    queue.append((pos2, True, path+(pos2,)))
        if canback:
            pos2 = backedge[pos]
            if (pos2, False) not in seen:
                seen.add((pos2, False))
                queue.append((pos2, False, path+(pos2,)))
    else: #queue is empty but we didn't find anything
        return None, set(x for x,front in seen if front)

def _mincut(startnodes, endnodes, bound):
    startset = frozenset(startnodes)
    endset = frozenset(endnodes)
    bound = bound | endset
    used = set()
    backedge = {}

    while 1:
        oldlen = len(used)
        path, lastseen = _augmentingPath(startnodes, startset, endset, used, backedge, bound)
        if path is None:
            return lastseen | (startset & used)

        assert(path[0] in startset and path[-1] in endset)
        assert(path[0] not in used)

        for pos, last in zip(path, (None,)+path):
            #In the case of a backward edge, there's nothing to do since it was already part of a used path
            used.add(pos)
            if last is not None and pos in last.norm_suc_nl: #normal forward edge
                backedge[pos] = last

        assert(len(used) > oldlen)
        assert(set(backedge) == (used - startset))

def completeScopes(dom, croot, children, isClinit):
    parentscope = {}
    for k, v in children.items():
        for child in v:
            pscopes = [scope for scope in k.scopes if child.lbound.issubset(scope.lbound)]
            assert(len(pscopes)==1)
            parentscope[child] = pscopes[0]

    nodeorder = graph_util.topologicalSort([dom.root], lambda n:n.successors_nl)
    nodeorder = {n:-i for i,n in enumerate(nodeorder)}

    stack = [croot]
    while stack:
        parent = stack.pop()

        #The problem is that when processing one child, we may want to extend it to include another child
        #We solve this by freezing already processed children and ordering them heuristically
        # TODO - find a better way to handle this
        revorder = sorted(children[parent], key=lambda cnode:(-nodeorder[cnode.lbound.head], len(cnode.ubound.nodes)))
        frozen_nodes = set()

        while revorder:
            cnode = revorder.pop()
            if cnode not in children[parent]: #may have been made a child of a previously processed child
                continue

            scopes = [s for s in parent.scopes if s.lbound.touches(cnode.lbound)]
            assert(len(scopes)==1)

            ubound = cnode.ubound & scopes[0].lbound
            ubound_s = ubound.nodes - frozen_nodes
            for other in revorder:
                if not ubound_s.issuperset(other.lbound.nodes):
                    ubound_s -= other.lbound.nodes
            if isClinit:
                # Avoid inlining return block so that it's always at the end and can be pruned later
                ubound_s = set(n for n in ubound_s if n.block is None or not isinstance(n.block.jump, ssa_jumps.Return))

            ubound = _dominatorUBoundClosure(dom, ubound_s, cnode.lbound.head)
            assert(ubound.issuperset(cnode.lbound))
            body = cnode.lbound

            #Be careful to make sure the order is deterministic
            temp = set(body.nodes)
            parts = [n.norm_suc_nl for n in sorted(body.nodes, key=nodeorder.get)]
            startnodes = [n for n in itertools.chain(*parts) if not n in temp and not temp.add(n)]

            temp = set(ubound.nodes)
            parts = [n.norm_suc_nl for n in sorted(ubound.nodes, key=nodeorder.get)]
            endnodes = [n for n in itertools.chain(*parts) if not n in temp and not temp.add(n)]

            #Now use Edmonds-Karp, modified to find min vertex cut
            lastseen = _mincut(startnodes, endnodes, ubound.nodes)

            #Now we have the max flow, try to find the min cut
            #Just use the set of nodes visited during the final BFS
            interior = [x for x in (lastseen & ubound.nodes) if lastseen.issuperset(x.norm_suc_nl)]

            #TODO - figure out a cleaner way to do this
            if interior:
                body |= dom.extend(dom.dominator(*interior), interior)
            assert(body.issubset(ubound))
            #The new cut may get messed up by the inclusion of extra children. But this seems unlikely
            newchildren = []
            for child in revorder:
                if child.lbound.touches(body):
                    body |= child.lbound
                    newchildren.append(child)

            assert(body.issubset(ubound))
            cnode.lbound = body
            for scope in cnode.scopes:
                scope.lbound |= (body & scope.ubound)

            children[cnode].extend(newchildren)
            children[parent] = [c for c in children[parent] if c not in newchildren]
            frozen_nodes |= body.nodes

        #Note this is only the immediate children, after some may have been moved down the tree during previous processing
        stack.extend(children[parent])

#Class used for the trees created internally while deciding where to create scopes
class _mnode(object):
    def __init__(self, head):
        self.head = head
        self.nodes = set()
        self.items = []
        #externally set fields: children top selected subtree depth
    # def __str__(self): return 'M'+str(self.head)[3:]
    # __repr__ = __str__

def _addBreak_sub(dom, rno_get, body, childcons):
    # Create dom* tree
    # This is a subset of dominators that dominate all nodes reachable from themselves
    # These "super dominators" are the places where it is possible to create a break scope

    domC = {n:dom.dominators(n) for n in body}
    for n in sorted(body, key=rno_get): #reverse topo order
        for n2 in n.successors_nl:
            if n2 not in body:
                continue
            domC[n] &= domC[n2]
            assert(domC[n])

    heads = set(n for n in body if n in domC[n]) #find the super dominators
    depths = {n:len(v) for n,v in domC.items()}
    parentC = {n:max(v & heads, key=depths.get) for n,v in domC.items()} #find the last dom* parent
    assert(all((n == parentC[n]) == (n in heads) for n in body))

    #Make sure this is deterministicly ordered
    mdata = collections.OrderedDict((k,_mnode(k)) for k in sorted(heads, key=rno_get))
    for n in body:
        mdata[parentC[n]].nodes.add(n)
    for item in childcons:
        head = parentC[item.lbound.head]
        mdata[head].items.append(item)
        mdata[head].nodes |= item.lbound.nodes
        assert(mdata[head].nodes <= body)
    assert(set(mdata) <= heads)

    # Now merge nodes until they no longer cross item boundaries, i.e. they don't intersect
    for h in heads:
        if h not in mdata:
            continue

        hits = mdata[h].nodes.intersection(mdata)
        while len(hits) > 1:
            hits.remove(h)
            for h2 in hits:
                assert(h in domC[h2] and h2 not in domC[h])
                mdata[h].nodes |= mdata[h2].nodes
                mdata[h].items += mdata[h2].items
                del mdata[h2]
            hits = mdata[h].nodes.intersection(mdata)
        assert(hits == set([h]))

    #Now that we have the final set of heads, fill in the tree data
    #for each mnode, we need to find its immediate parent
    ancestors = {h:domC[h].intersection(mdata) for h in mdata}
    mparents = {h:(sorted(v,key=depths.get)[-2] if len(v) > 1 else None) for h,v in ancestors.items()}

    for h, mnode in mdata.items():
        mnode.top = True
        mnode.selected = [mnode]
        mnode.subtree = [mnode]
        #Note, this is max nesting depth, NOT depth in the tree
        mnode.depth = 1 if mnode.items else 0
        if any(item.tag == 'switch' for item in mnode.items):
            mnode.depth = 2
        mnode.tiebreak = rno_get(h)

        assert(h in mnode.nodes and len(mnode.nodes) >= len(mnode.items))
        mnode.children = [mnode2 for h2, mnode2 in mdata.items() if mparents[h2] == h]

    revorder = graph_util.topologicalSort(mdata.values(), lambda mn:mn.children)
    assert(len(revorder) == len(mdata))
    assert(sum(len(mn.children) for mn in revorder) == len(revorder)-1)

    #Now partition tree into subtrees, trying to minimize max nesting
    for mnode in revorder:
        if mnode.children:
            successor = max(mnode.children, key=lambda mn:(mn.depth, len(mn.subtree), mn.tiebreak))

            depths = sorted(mn.depth for mn in mnode.children)
            temp = max(d-i for i,d in enumerate(depths))
            mnode.depth = max(mnode.depth, temp+len(mnode.children)-1)

            for other in mnode.children:
                if other is successor:
                    continue
                other.top = False
                mnode.selected += other.subtree
            mnode.subtree = mnode.selected + successor.subtree
            for subnode in mnode.selected[1:]:
                subnode.top = False
        assert(mnode.top)
        assert(len(set(mnode.subtree)) == len(mnode.subtree))

    results = []
    for root in revorder:
        if not root.top:
            continue
        nodes, items = set(), []
        for mnode in root.selected:
            nodes |= mnode.nodes
            items += mnode.items
        results.append((nodes, items))

    temp = list(itertools.chain.from_iterable(zip(*results)[1]))
    assert(len(temp) == len(childcons) and set(temp) == set(childcons))
    return results

def addBreakScopes(dom, croot, constraints, children):
    nodeorder = graph_util.topologicalSort([dom.root], lambda n:n.successors_nl)
    nodeorder = {n:i for i,n in enumerate(nodeorder)}
    rno_get = nodeorder.get #key for sorting nodes in rev. topo order

    stack = [croot]
    while stack:
        cnode = stack.pop()
        oldchildren = children[cnode][:]
        newchildren = children[cnode] = []

        for scope in cnode.scopes:
            subcons = [c for c in oldchildren if c.lbound <= scope.lbound]

            results = _addBreak_sub(dom, rno_get, scope.lbound.nodes, subcons)
            results = [t for t in results if len(t[0]) > 1]

            for nodes, items in results:
                if len(items) == 1 and items[0].lbound.nodes == nodes:
                    new = items[0] #no point wrapping it in a scope if it already has identical body
                else:
                    head = dom.dominator(*nodes)
                    body = dom.extend(head, nodes)
                    assert(body.nodes == nodes)

                    new = FixedScopeCon(body)
                    constraints.append(new)
                    children[new] = items
                newchildren.append(new)
                stack.append(new)
        _checkNested(children)

def constraintsToSETree(dom, croot, children, nodes):
    seitems = {n:SEBlockItem(n) for n in nodes} #maps entryblock -> item

    #iterate over tree in reverse topological order (bottom up)
    revorder = graph_util.topologicalSort([croot], lambda cn:children[cn])
    for cnode in revorder:
        sescopes = []
        for scope in cnode.scopes:
            pos, body = scope.lbound.head, scope.lbound.nodes
            items = []
            while pos is not None:
                item = seitems[pos]
                del seitems[pos]
                items.append(item)
                suc = [n for n in item.successors if n in body]
                assert(len(suc) <= 1)
                pos = suc[0] if suc else None

            newscope = SEScope(items)
            sescopes.append(newscope)
            assert(newscope.nodes == frozenset(body))

        if cnode.tag in ('if','switch'):
            head = seitems[cnode.head]
            assert(isinstance(head, SEBlockItem))
            del seitems[cnode.head]

        new = None
        if cnode.tag == 'while':
            new = SEWhile(sescopes[0])
        elif cnode.tag == 'if':
            #ssa_jump stores false branch first, but ast gen assumes true branch first
            sescopes = [sescopes[1], sescopes[0]]
            new = SEIf(head, sescopes)
        elif cnode.tag == 'switch':
            #Switch fallthrough can only be done implicitly, but we may need to jump to it
            #from arbitrary points in the scope, so we add an extra scope so we have a
            #labeled break. If unnecessary, it should be removed later on anyway
            sescopes = [SEScope([sescope]) for sescope in sescopes]
            new = SESwitch(head, sescopes)
        elif cnode.tag == 'try':
            catchtts = cnode.cset.getTopTTs()
            catchvar = cnode.catchvar
            new = SETry(sescopes[0], sescopes[1], catchtts, catchvar)
        elif cnode.tag == 'scope':
            new = sescopes[0]

        assert(new.nodes == cnode.lbound.nodes)
        assert(new.entryBlock not in seitems)
        seitems[new.entryBlock] = new

    assert(len(seitems) == 1)
    assert(isinstance(seitems.values()[0], SEScope))
    return seitems.values()[0]

def _checkNested(ctree_children):
    #Check tree for proper nesting
    for k, children in ctree_children.items():
        for child in children:
            assert(child.lbound <= k.lbound)
            assert(child.lbound <= child.ubound)
            scopes = [s for s in k.scopes if s.ubound.touches(child.lbound)]
            assert(len(scopes) == 1)

            for c1, c2 in itertools.combinations(child.scopes, 2):
                assert(c1.lbound.isdisjoint(c2.lbound))
                assert(c1.ubound.isdisjoint(c2.ubound))

        for c1, c2 in itertools.combinations(children, 2):
            assert(c1.lbound.isdisjoint(c2.lbound))

def _debug_draw(nodes, outn=''):
    import pygraphviz as pgv
    G=pgv.AGraph(directed=True)
    G.add_nodes_from(nodes)
    for n in nodes:
        for n2 in n.successors:
            color = 'black'
            if isinstance(n.block.jump, ssa_jumps.OnException):
                if any(b.key == n2.bkey for b in n.block.jump.getExceptSuccessors()):
                    color = 'grey'
            # color = 'black' if n2 in n.outvars else 'gray'
            G.add_edge(n, n2, color=color)
    G.layout(prog='dot')
    G.draw('file{}.png'.format(outn))

def calcNoLoopNeighbors(dom, nodes):
    for n in nodes:
        n.successors_nl = [x for x in n.successors if x not in dom.dominators(n)]
        n.predecessors_nl = [x for x in n.predecessors if n not in dom.dominators(x)]
        n.norm_suc_nl = [x for x in n.successors_nl if x in n.outvars]
    for n in nodes:
        for n2 in n.successors_nl:
            assert(n in n2.predecessors_nl)
        for n2 in n.predecessors_nl:
            assert(n in n2.successors_nl)

def structure(entryNode, nodes, isClinit):
    # print 'structuring'
    #eliminate self loops
    for n in nodes[:]:
        if n in n.successors:
            nodes.append(n.indirectEdges([n]))

    #inline returns if possible
    retblocks = [n for n in nodes if n.block and isinstance(n.block.jump, ssa_jumps.Return)]
    if retblocks and not isClinit:
        assert(len(retblocks) == 1)
        ret = retblocks[0]
        for pred in ret.predecessors[1:]:
            new = ret.newDuplicate()
            new.predecessors = [pred]
            pred.replaceSuccessors({ret:new})
            nodes.append(new)
        ret.predecessors = ret.predecessors[:1]

    for n in nodes:
        for x in n.predecessors:
            assert(n in x.successors)
        for x in n.successors:
            assert(n in x.predecessors)
        assert(set(n.successors) == (set(n.outvars) | set(n.eassigns)))

    #note, these add new nodes (list passed by ref)
    while_heads = structureLoops(nodes)
    newtryinfos = structureExceptions(nodes)
    switchinfos, ifinfos = structureConditionals(entryNode, nodes)

    #At this point graph modification is largely done so we can calculate and store dominator info
    #this will be invalidated and recalculated near the end of mergeExceptions
    dom = DominatorInfo(entryNode)
    calcNoLoopNeighbors(dom, nodes)

    constraints = createConstraints(dom, while_heads, newtryinfos, switchinfos, ifinfos)
    croot, ctree_children = orderConstraints(dom, constraints, nodes)

    # print 'exception merging'
    #May remove nodes (and update dominator info)
    dom, constraints, nodes = mergeExceptions(dom, ctree_children, constraints, nodes)

    #TODO - parallelize exceptions
    fixTryConstraints(dom, constraints)

    #After freezing the try constraints we need to regenerate the tree
    croot, ctree_children = orderConstraints(dom, constraints, nodes)

    # print 'completing scopes'
    _checkNested(ctree_children)
    completeScopes(dom, croot, ctree_children, isClinit)

    # print 'adding breaks'
    _checkNested(ctree_children)
    addBreakScopes(dom, croot, constraints, ctree_children)
    _checkNested(ctree_children)

    return constraintsToSETree(dom, croot, ctree_children, nodes)
########NEW FILE########
__FILENAME__ = variablemerge
import collections

from .setree import SEBlockItem, SEScope, SEIf, SESwitch, SETry, SEWhile
from .. import graph_util
from ..ssa import ssa_ops, ssa_jumps

def visitItem(current, nodes, cdict, catches=()):
    if isinstance(current, SEBlockItem):
        node = current.node
        nodes.append(node)
        for cs in catches:
            cs.add(node)
    elif isinstance(current, SEScope):
        for item in current.items:
            visitItem(item, nodes, cdict, catches)
    elif isinstance(current, SETry):
        visitItem(current.scopes[0], nodes, cdict, catches)
        if current.catchvar is not None:
            cvar = current.scopes[1].entryBlock, current.catchvar, False
            catches += cdict[cvar],
        visitItem(current.scopes[1], nodes, cdict, catches)
    else:
        if isinstance(current, (SEIf, SESwitch)):
            visitItem(current.head, nodes, cdict, catches)
        for scope in current.getScopes():
            visitItem(scope, nodes, cdict, catches)

def mergeVariables(setree):
    nodes = []    
    catch_regions = collections.defaultdict(set)
    visitItem(setree, nodes, catch_regions)

    assigns = collections.defaultdict(set)
    for node in nodes:
        block = node.block
        cast_repl = {}
        if block is not None and block.lines:
            if isinstance(block.lines[-1], ssa_ops.CheckCast) and isinstance(block.jump, ssa_jumps.OnException):
                var = block.lines[-1].params[0]
                cast_repl[node, var, False] = node, var, True

        for n2 in node.successors:
            assert((n2 in node.outvars) != (n2 in node.eassigns))
            if n2 in node.eassigns:
                for outv, inv in zip(node.eassigns[n2], n2.invars):
                    if outv is None: #this is how we mark the thrown exception, which 
                        #obviously doesn't get an explicit assignment statement
                        continue
                    assigns[n2, inv, False].add((node, outv, False))
            else:
                for outv, inv in zip(node.outvars[n2], n2.invars):
                    key = node, outv, False
                    assigns[n2, inv, False].add(cast_repl.get(key,key))

    #Handle use of caught exception outside its defining scope   
    roots = {} 
    for k, defs in assigns.items():
        for v in defs:
            if v in catch_regions and k[0] not in catch_regions[v]:
                roots[k] = k
                break

    while 1:
        #Note this is nondeterministic
        remain = [v for v in assigns if v not in roots]
        sccs = graph_util.tarjanSCC(remain, lambda svar:[v for v in assigns[svar] if v not in roots])
        for scc in sccs:
            defs = set().union(*(assigns[svar] for svar in scc))
            defs -= set(scc)

            if not defs:
                assert(len(scc)==1)
                roots[scc[0]] = scc[0]
            else:
                defroots = set(roots[x] for x in defs)
                if len(defroots) == 1:
                    root = defroots.pop()
                    for svar in scc: 
                        roots[svar] = root                       
                else:
                    for svar in scc: 
                        if not assigns[svar].issubset(scc):
                            roots[svar] = svar
                    break #we have new roots, so restart the loop
        else: #iterated through all sccs without a break so we're done
            break  

    for k,v in roots.items():
        if k is not v:
            assert(isinstance(k[1].origin, ssa_ops.Phi))
    return roots
########NEW FILE########
__FILENAME__ = method
import collections

from . import binUnpacker, bytecode
from .attributes_raw import get_attributes_raw, fixAttributeNames

exceptionHandlerRaw = collections.namedtuple("exceptionHandlerRaw",
                                             ["start","end","handler","type_ind"])

class Code(object):
    def __init__(self, method, bytestream, keepRaw):
        self.method = method
        self.class_ = method.class_
        
        #Old versions use shorter fields for stack, locals, and code length
        field_fmt = ">HHL" if self.class_.version > (45,2) else ">BBH"
        self.stack, self.locals, codelen = bytestream.get(field_fmt)
        assert(codelen > 0 and codelen < 65536)
        self.bytecode_raw = bytestream.getRaw(codelen)
        self.codelen = codelen

        except_cnt = bytestream.get('>H')
        self.except_raw = [bytestream.get('>HHHH') for _ in range(except_cnt)]
        self.except_raw = [exceptionHandlerRaw(*t) for t in self.except_raw]
        attributes_raw = get_attributes_raw(bytestream)
        assert(bytestream.size() == 0)

        if self.except_raw:
            assert(self.stack >= 1)

        # print 'Parsing code for', method.name, method.descriptor, method.flags
        codestream = binUnpacker.binUnpacker(data = self.bytecode_raw)
        self.bytecode = bytecode.parseInstructions(codestream, self.isIdConstructor)
        self.attributes = fixAttributeNames(attributes_raw, self.class_.cpool)

        for e in self.except_raw:
            assert(e.start in self.bytecode)
            assert(e.end == codelen or e.end in self.bytecode)
            assert(e.handler in self.bytecode)
        if keepRaw:
            self.attributes_raw = attributes_raw

    #This is a callback passed to the bytecode parser to determine if a given method id represents a constructor                        
    def isIdConstructor(self, methId):
        args = self.class_.cpool.getArgsCheck('Method', methId) 
        return args[1] == '<init>'


    def __str__(self):
        lines = ['Stack: {}, Locals {}'.format(self.stack, self.locals)]
        
        instructions = self.bytecode
        lines += ['{}: {}'.format(i, bytecode.printInstruction(instructions[i])) for i in sorted(instructions)]
        if self.except_raw:
            lines += ['Exception Handlers:']
            lines += map(str, self.except_raw)
        return '\n'.join(lines)

class Method(object):
    flagVals = {'PUBLIC':0x0001,
                'PRIVATE':0x0002,
                'PROTECTED':0x0004,
                'STATIC':0x0008,
                'FINAL':0x0010,
                'SYNCHRONIZED':0x0020,
                'BRIDGE':0x0040,
                'VARARGS':0x0080,
                'NATIVE':0x0100,
                'ABSTRACT':0x0400,
                'STRICTFP':0x0800,
                'SYNTHETIC':0x1000, 
                }

    def __init__(self, data, classFile, keepRaw):
        self.class_ = classFile
        cpool = self.class_.cpool
        
        flags, name_id, desc_id, attributes_raw = data

        self.name = cpool.getArgsCheck('Utf8', name_id)
        self.descriptor = cpool.getArgsCheck('Utf8', desc_id)
        # print 'Loading method ', self.name, self.descriptor
        self.attributes = fixAttributeNames(attributes_raw, cpool)

        self.flags = set(name for name,mask in Method.flagVals.items() if (mask & flags))
        self._checkFlags()
        self.static = 'STATIC' in self.flags
        self.native = 'NATIVE' in self.flags
        self.abstract = 'ABSTRACT' in self.flags
        self.isConstructor = (self.name == '<init>')
        
        #Prior to version 51.0, <clinit> is still valid even if it isn't marked static
        if self.class_.version < (51,0) and self.name == '<clinit>' and self.descriptor == '()V':
            self.static = True
        self._loadCode(keepRaw)
        if keepRaw:
            self.attributes_raw = attributes_raw
            self.name_id, self.desc_id = name_id, desc_id

    def _checkFlags(self):
        assert(len(self.flags & set(('PRIVATE','PROTECTED','PUBLIC'))) <= 1)
        if 'ABSTRACT' in self.flags: 
            assert(not self.flags & set(['SYNCHRONIZED', 'PRIVATE', 'FINAL', 'STRICT', 'STATIC', 'NATIVE']))

    def _loadCode(self, keepRaw):
        cpool = self.class_.cpool
        code_attrs = [a for a in self.attributes if a[0] == 'Code']
        if self.native or self.abstract:
            assert(not code_attrs)
            self.code = None
        else:
            assert(len(code_attrs) == 1)
            code_raw = code_attrs[0][1]
            bytestream = binUnpacker.binUnpacker(code_raw)
            self.code = Code(self, bytestream, keepRaw)
########NEW FILE########
__FILENAME__ = namegen
import itertools, collections

class NameGen(object):
    def __init__(self, reserved=frozenset()):
        self.counters = collections.defaultdict(itertools.count)
        self.names = set(reserved)

    def getPrefix(self, prefix, sep=''):
        newname = prefix
        while newname in self.names:
            newname = prefix + sep + str(next(self.counters[prefix]))        
        self.names.add(newname)
        return newname

def LabelGen(prefix='label'):
    for i in itertools.count():
        yield prefix + str(i)
########NEW FILE########
__FILENAME__ = opnames
ADD = 'add'
AND = 'and'
ANEWARRAY = 'anewarray'
ARRLEN = 'arrlen'
ARRLOAD = 'arrload'
ARRLOAD_OBJ = 'arrload_obj'
ARRSTORE = 'arrstore'
ARRSTORE_OBJ = 'arrstore_obj'
CHECKCAST = 'checkcast'
CONST = 'const'
CONSTNULL = 'constnull'
CONVERT = 'convert'
DIV = 'div'
DUP = 'dup'
DUP2 = 'dup2'
DUP2X1 = 'dup2x1'
DUP2X2 = 'dup2x2'
DUPX1 = 'dupx1'
DUPX2 = 'dupx2'
FCMP = 'fcmp'
GETFIELD = 'getfield'
GETSTATIC = 'getstatic'
GOTO = 'goto'
IF_A = 'if_a'
IF_ACMP = 'if_acmp'
IF_I = 'if_i'
IF_ICMP = 'if_icmp'
IINC = 'iinc'
INSTANCEOF = 'instanceof'
INVOKEDYNAMIC = 'invokedynamic'
INVOKEINIT = 'invokeinit'
INVOKEINTERFACE = 'invokeinterface'
INVOKESPECIAL = 'invokespecial'
INVOKESTATIC = 'invokestatic'
INVOKEVIRTUAL = 'invokevirtual'
JSR = 'jsr'
LCMP = 'lcmp'
LDC = 'ldc'
LOAD = 'load'
MONENTER = 'monenter'
MONEXIT = 'monexit'
MUL = 'mul'
MULTINEWARRAY = 'multinewarray'
NEG = 'neg'
NEW = 'new'
NEWARRAY = 'newarray'
NOP = 'nop'
OR = 'or'
POP = 'pop'
POP2 = 'pop2'
PUTFIELD = 'putfield'
PUTSTATIC = 'putstatic'
REM = 'rem'
RET = 'ret'
RETURN = 'return'
SHL = 'shl'
SHR = 'shr'
STORE = 'store'
SUB = 'sub'
SWAP = 'swap'
SWITCH = 'switch'
THROW = 'throw'
TRUNCATE = 'truncate'
USHR = 'ushr'
XOR = 'xor'
########NEW FILE########
__FILENAME__ = script_util
import platform, os, os.path, zipfile
import collections, hashlib
from functools import partial

#Various utility functions for the top level scripts (decompile.py, assemble.py, disassemble.py)

copyright = '''Krakatau  Copyright (C) 2012-14  Robert Grosse
This program is provided as open source under the GNU General Public License.
See LICENSE.TXT for more details.
'''

def findFiles(target, recursive, prefix):
    if target.endswith('.jar'):
        with zipfile.ZipFile(target, 'r') as archive:
            targets = [name for name in archive.namelist() if name.endswith(prefix)]
    else:
        if recursive:
            assert(os.path.isdir(target))
            targets = []

            for root, dirs, files in os.walk(target):
                targets += [os.path.join(root, fname) for fname in files if fname.endswith(prefix)]
        else:
            return [target]
    return targets

def normalizeClassname(name):
    if name.endswith('.class'):
        name = name[:-6]
    # Replacing backslashes is ugly since they can be in valid classnames too, but this seems the best option
    return name.replace('\\','/').replace('.','/')

#Windows stuff
illegal_win_chars = frozenset('<>;:|?*\\/"')
pref_disp_chars = frozenset('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_$0123456789')

#Prevent creating filename parts matching the legacy device filenames. While Krakatau can create these files
#just fine thanks to using \\?\ paths, the resulting files are impossible to open or delete in Windows Explorer
#or with similar tools, so they are a huge pain to deal with. Therefore, we don't generate them at all.
illegal_parts = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8',
    'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']

def isPartOk(s, prev):
    if not 1 <= len(s) <= 200:
        return False
    if s.upper() in illegal_parts:
        return False
    if s.lower() in prev:
        return prev[s.lower()] == s
    #avoid collision with hashed parts
    if len(s) >= 34 and s[-34:-32] == '__':
        return False

    if min(s) <= '\x1f' or max(s) >= '\x7f':
        return False
    return illegal_win_chars.isdisjoint(s)

def isPathOk(s, prevs):
    if len(s) > 32000:
        return False
    parts = s.split('/')
    return 0 < len(parts) < 750

def sanitizePart(s, suffix, prev):
    #make sure that suffix is never in any parts so we don't get a collision after adding it
    if isPartOk(s, prev) and suffix not in s:
        return s
    ok = ''.join(c for c in s if c in pref_disp_chars)
    return ok[:8] + '__' + hashlib.md5(s).hexdigest()

def winSanitizePath(base, suffix, prevs, s):
    if isPathOk(s, prevs):
        parts = s.split('/')
        sparts = [sanitizePart(p, suffix, prevs[i]) for i,p in enumerate(parts)]
        for i, sp in enumerate(sparts):
            prevs[i][sp.lower()] = sp
        path = '\\'.join(sparts)
    else:
        path = '__' + hashlib.md5(s).hexdigest()
        prevs[0][path.lower()] = path
    return '\\\\?\\{}\\{}{}'.format(base, path, suffix)

def otherMakePath(base, suffix, s):
    return os.path.join(base, *s.split('/')) + suffix

def fileDirOut(base_path, suffix):
    if base_path is None:
        base_path = os.getcwdu()
    else:
        base_path = base_path.decode('utf8')
        base_path = os.path.abspath(base_path)

    osname = platform.system().lower()
    if 'win' in osname and 'darwin' not in osname:
        prevs = collections.defaultdict(dict) #keep track of previous paths to detect case-insensitive collisions
        makepath = partial(winSanitizePath, base_path, suffix, prevs)
    else:
        makepath = partial(otherMakePath, base_path, suffix)

    def write(cname, data):
        out = makepath(cname)
        dirpath = os.path.dirname(out)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath)

        with open(out,'wb') as f:
            f.write(data)
        return out
    return write
########NEW FILE########
__FILENAME__ = blockmaker
import collections

from . import ssa_ops, ssa_jumps, objtypes, subproc
from .. import opnames as vops
from ..verifier import verifier_types
from ..verifier.descriptors import parseMethodDescriptor, parseFieldDescriptor
from .ssa_types import SSA_INT, SSA_LONG, SSA_FLOAT, SSA_DOUBLE, SSA_OBJECT, SSA_MONAD
from .ssa_types import slots_t, BasicBlock

_charToSSAType = {'D':SSA_DOUBLE, 'F':SSA_FLOAT, 'I':SSA_INT, 'J':SSA_LONG,
                'B':SSA_INT, 'C':SSA_INT, 'S':SSA_INT}
def getCategory(c): return 2 if c in 'JD' else 1


class ResultDict(object):
    def __init__(self, line=None, jump=None, newstack=None, newlocals=None):
        self.line = line
        self.jump = jump
        self.newstack = newstack
        self.newlocals = newlocals

##############################################################################
def makeConstVar(parent, type_, val):
    var = parent.makeVariable(type_)
    var.const = val
    return var

def parseArrOrClassName(desc):
    if desc[0] == '[':
        vtypes = parseFieldDescriptor(desc, unsynthesize=False)
        tt = objtypes.verifierToSynthetic(vtypes[0])
    else:
        tt = desc, 0
    return tt

def _genericStackOperation(op, stack):
    num, replaceCodes = genericStackCodes[op]

    vals = stack[-num:]
    newvals = [vals[num-i-1] for i in replaceCodes]
    newstack = stack[:-num] + newvals
    return ResultDict(newstack=newstack)

def _floatOrIntMath(fop, iop):
    def math1(parent, input_, iNode):
        cat = getCategory(iNode.instruction[1])
        isfloat = (iNode.instruction[1] in 'DF')
        op = fop if isfloat else iop

        args = input_.stack[-cat*2::cat]
        line = op(parent, args)

        newstack = input_.stack[:-2*cat] + [line.rval] + [None]*(cat-1)
        return ResultDict(line=line, newstack=newstack)
    return math1

def _intMath(op, isShift):
    def math2(parent, input_, iNode):
        cat = getCategory(iNode.instruction[1])
        #some ops (i.e. shifts) always take int as second argument
        size = cat+1 if isShift else cat+cat
        args = input_.stack[-size::cat]
        line = op(parent, args)
        newstack = input_.stack[:-size] + [line.rval] + [None]*(cat-1)
        return ResultDict(line=line, newstack=newstack)
    return math2
##############################################################################

def _anewarray(parent, input_, iNode):
    name = parent.getConstPoolArgs(iNode.instruction[1])[0]
    tt = parseArrOrClassName(name)
    line = ssa_ops.NewArray(parent, input_.stack[-1], tt, input_.monad)
    newstack = input_.stack[:-1] + [line.rval]
    return ResultDict(line=line, newstack=newstack)

def _arrlen(parent, input_, iNode):
    line = ssa_ops.ArrLength(parent, input_.stack[-1:])
    newstack = input_.stack[:-1] + [line.rval]
    return ResultDict(line=line, newstack=newstack)

def _arrload(parent, input_, iNode):
    type_ = _charToSSAType[iNode.instruction[1]]
    cat = getCategory(iNode.instruction[1])

    line = ssa_ops.ArrLoad(parent, input_.stack[-2:], type_, monad=input_.monad)
    newstack = input_.stack[:-2] + [line.rval] + [None]*(cat-1)
    return ResultDict(line=line, newstack=newstack)

def _arrload_obj(parent, input_, iNode):
    line = ssa_ops.ArrLoad(parent, input_.stack[-2:], SSA_OBJECT, monad=input_.monad)
    newstack = input_.stack[:-2] + [line.rval]
    return ResultDict(line=line, newstack=newstack)

def _arrstore(parent, input_, iNode):
    if getCategory(iNode.instruction[1]) > 1:
        newstack, args = input_.stack[:-4], input_.stack[-4:-1]
    else:
        newstack, args = input_.stack[:-3], input_.stack[-3:]
    line = ssa_ops.ArrStore(parent, args, monad=input_.monad)
    return ResultDict(line=line, newstack=newstack)

def _arrstore_obj(parent, input_, iNode):
    line = ssa_ops.ArrStore(parent, input_.stack[-3:], monad=input_.monad)
    newstack = input_.stack[:-3]
    return ResultDict(line=line, newstack=newstack)

def _checkcast(parent, input_, iNode):
    index = iNode.instruction[1]
    desc = parent.getConstPoolArgs(index)[0]
    tt = parseArrOrClassName(desc)
    line = ssa_ops.CheckCast(parent, tt, input_.stack[-1:])
    return ResultDict(line=line)

def _const(parent, input_, iNode):
    ctype, val = iNode.instruction[1:]
    cat = getCategory(ctype)
    type_ = _charToSSAType[ctype]
    var = makeConstVar(parent, type_, val)
    newstack = input_.stack + [var] + [None]*(cat-1)
    return ResultDict(newstack=newstack)

def _constnull(parent, input_, iNode):
    var = makeConstVar(parent, SSA_OBJECT, 'null')
    var.decltype = objtypes.NullTT
    newstack = input_.stack + [var]
    return ResultDict(newstack=newstack)

def _convert(parent, input_, iNode):
    src_c, dest_c = iNode.instruction[1:]
    src_cat, dest_cat = getCategory(src_c), getCategory(dest_c)

    stack, arg =  input_.stack[:-src_cat], input_.stack[-src_cat]
    line = ssa_ops.Convert(parent, arg, _charToSSAType[src_c], _charToSSAType[dest_c])

    newstack = stack + [line.rval] + [None]*(dest_cat-1)
    return ResultDict(line=line, newstack=newstack)

def _fcmp(parent, input_, iNode):
    op, c, NaN_val = iNode.instruction
    cat = getCategory(c)

    args = input_.stack[-cat*2::cat]
    line = ssa_ops.FCmp(parent, args, NaN_val)
    newstack = input_.stack[:-cat*2] + [line.rval]
    return ResultDict(line=line, newstack=newstack)

def _field_access(parent, input_, iNode):
    index = iNode.instruction[1]
    target, name, desc = parent.getConstPoolArgs(index)
    cat = len(parseFieldDescriptor(desc))

    argcnt = cat if 'put' in iNode.instruction[0] else 0
    if not 'static' in iNode.instruction[0]:
        argcnt += 1
    splitInd = len(input_.stack) - argcnt

    args = [x for x in input_.stack[splitInd:] if x is not None]
    line = ssa_ops.FieldAccess(parent, iNode.instruction, (target, name, desc), args=args, monad=input_.monad)
    newstack = input_.stack[:splitInd] + line.returned
    return ResultDict(line=line, newstack=newstack)

def _if_a(parent, input_, iNode):
    null = makeConstVar(parent, SSA_OBJECT, 'null')
    null.decltype = objtypes.NullTT
    jump = ssa_jumps.If(parent, iNode.instruction[1], iNode.successors, (input_.stack[-1], null))
    newstack = input_.stack[:-1]
    return ResultDict(jump=jump, newstack=newstack)

def _if_i(parent, input_, iNode):
    zero = makeConstVar(parent, SSA_INT, 0)
    jump = ssa_jumps.If(parent, iNode.instruction[1], iNode.successors, (input_.stack[-1], zero))
    newstack = input_.stack[:-1]
    return ResultDict(jump=jump, newstack=newstack)

def _if_icmp(parent, input_, iNode):
    jump = ssa_jumps.If(parent, iNode.instruction[1], iNode.successors, input_.stack[-2:])
    newstack = input_.stack[:-2]
    return ResultDict(jump=jump, newstack=newstack)

def _iinc(parent, input_, iNode):
    junk, index, amount = iNode.instruction

    oldval = input_.locals[index]
    constval = makeConstVar(parent, SSA_INT, amount)
    line = ssa_ops.IAdd(parent, (oldval, constval))

    newlocals = list(input_.locals)
    newlocals[index] = line.rval
    return ResultDict(line=line, newlocals=newlocals)

def _instanceof(parent, input_, iNode):
    index = iNode.instruction[1]
    desc = parent.getConstPoolArgs(index)[0]
    tt = parseArrOrClassName(desc)
    line = ssa_ops.InstanceOf(parent, tt, input_.stack[-1:])
    newstack = input_.stack[:-1] + [line.rval]
    return ResultDict(line=line, newstack=newstack)

def _invoke(parent, input_, iNode):
    index = iNode.instruction[1]
    target, name, desc = parent.getConstPoolArgs(index)

    argcnt = len(parseMethodDescriptor(desc)[0])
    if not 'static' in iNode.instruction[0]:
        argcnt += 1
    splitInd = len(input_.stack) - argcnt

    #If we are an initializer, store a copy of the uninitialized verifier type so the Java decompiler can patch things up later
    isThisCtor = iNode.isThisCtor if iNode.op == vops.INVOKEINIT else False

    args = [x for x in input_.stack[splitInd:] if x is not None]
    line = ssa_ops.Invoke(parent, iNode.instruction, (target, name, desc), args=args, monad=input_.monad, isThisCtor=isThisCtor)
    newstack = input_.stack[:splitInd] + line.returned
    return ResultDict(line=line, newstack=newstack)

def _jsr(parent, input_, iNode):
    newstack = input_.stack + [None]

    if iNode.returnedFrom is None:
        return ResultDict(newstack=newstack)
    else:
        #Simply store the data for now and fix things up once all the blocks are created
        jump = subproc.ProcCallOp(input_, iNode)
        return ResultDict(jump=jump, newstack=newstack)

def _lcmp(parent, input_, iNode):
    args = input_.stack[-4::2]
    line = ssa_ops.ICmp(parent, args)
    newstack = input_.stack[:-4] + [line.rval]
    return ResultDict(line=line, newstack=newstack)

def _ldc(parent, input_, iNode):
    index, cat = iNode.instruction[1:]
    entry_type = parent.getConstPoolType(index)
    args = parent.getConstPoolArgs(index)

    var = None
    if entry_type == 'String':
        var = makeConstVar(parent, SSA_OBJECT, args[0])
        var.decltype = objtypes.StringTT
    elif entry_type == 'Int':
        var = makeConstVar(parent, SSA_INT, args[0])
    elif entry_type == 'Long':
        var = makeConstVar(parent, SSA_LONG, args[0])
    elif entry_type == 'Float':
        var = makeConstVar(parent, SSA_FLOAT, args[0])
    elif entry_type == 'Double':
        var = makeConstVar(parent, SSA_DOUBLE, args[0])
    elif entry_type == 'Class':
        tt = args[0], 0 #todo - make this handle arrays and primatives
        var = makeConstVar(parent, SSA_OBJECT, tt)
        var.decltype = objtypes.ClassTT
    #Todo - handle MethodTypes and MethodHandles?

    assert(var)
    newstack = input_.stack + [var] + [None]*(cat-1)
    return ResultDict(newstack=newstack)

def _load(parent, input_, iNode):
    cat = getCategory(iNode.instruction[1])
    index = iNode.instruction[2]
    newstack = input_.stack + input_.locals[index:index+cat]
    return ResultDict(newstack=newstack)

def _monitor(parent, input_, iNode):
    isExit = 'exit' in iNode.instruction[0]
    line = ssa_ops.Monitor(parent, input_.stack[-1:], input_.monad, isExit)
    newstack = input_.stack[:-1]
    return ResultDict(line=line, newstack=newstack)

def _multinewarray(parent, input_, iNode):
    op, index, dim = iNode.instruction
    name = parent.getConstPoolArgs(index)[0]
    tt = parseArrOrClassName(name)
    assert(tt[1] >= dim)

    line = ssa_ops.MultiNewArray(parent, input_.stack[-dim:], tt, input_.monad)
    newstack = input_.stack[:-dim] + [line.rval]
    return ResultDict(line=line, newstack=newstack)

def _neg(parent, input_, iNode):
    cat = getCategory(iNode.instruction[1])
    arg = input_.stack[-cat:][0]

    if (iNode.instruction[1] in 'DF'):
        line = ssa_ops.FNeg(parent, [arg])
    else: #for integers, we can just write -x as 0 - x
        zero = makeConstVar(parent, arg.type, 0)
        line = ssa_ops.ISub(parent, [zero,arg])

    newstack = input_.stack[:-cat] + [line.rval] + [None]*(cat-1)
    return ResultDict(line=line, newstack=newstack)

def _new(parent, input_, iNode):
    index = iNode.instruction[1]
    classname = parent.getConstPoolArgs(index)[0]

    line = ssa_ops.New(parent, classname, input_.monad)
    newstack = input_.stack + [line.rval]
    return ResultDict(line=line, newstack=newstack)

def _newarray(parent, input_, iNode):
    vtypes = parseFieldDescriptor(iNode.instruction[1], unsynthesize=False)
    tt = objtypes.verifierToSynthetic(vtypes[0])

    line = ssa_ops.NewArray(parent, input_.stack[-1], tt, input_.monad)
    newstack = input_.stack[:-1] + [line.rval]
    return ResultDict(line=line, newstack=newstack)

def _nop(parent, input_, iNode):
    return ResultDict()

def _ret(parent, input_, iNode):
    jump = subproc.DummyRet(input_, iNode)
    return ResultDict(jump=jump)

def _return(parent, input_, iNode):
    line = ssa_ops.TryReturn(parent, input_.monad)

    #Our special return block expects only the return values on the stack
    rtype = iNode.instruction[1]
    if rtype is None:
        newstack = []
    else:
        newstack = input_.stack[-getCategory(rtype):]
    return ResultDict(line=line, newstack=newstack)

def _store(parent, input_, iNode):
    cat = getCategory(iNode.instruction[1])
    index = iNode.instruction[2]

    newlocals = list(input_.locals)
    if len(newlocals) < index+cat:
        newlocals += [None] * (index+cat - len(newlocals))

    newlocals[index:index+cat] = input_.stack[-cat:]
    newstack = input_.stack[:-cat]
    return ResultDict(newstack=newstack, newlocals=newlocals)

def _switch(parent, input_, iNode):
    default, table = iNode.instruction[1:3]
    jump = ssa_jumps.Switch(parent, default, table, input_.stack[-1:])
    newstack = input_.stack[:-1]
    return ResultDict(jump=jump, newstack=newstack)

def _throw(parent, input_, iNode):
    line = ssa_ops.Throw(parent, input_.stack[-1:])
    return ResultDict(line=line, newstack=[])

def _truncate(parent, input_, iNode):
    dest_c = iNode.instruction[1]
    signed, width = {'B':(True,8), 'C':(False,16), 'S':(True, 16)}[dest_c]

    line = ssa_ops.Truncate(parent, input_.stack[-1], signed=signed, width=width)
    newstack = input_.stack[:-1] + [line.rval]
    return ResultDict(line=line, newstack=newstack)

_instructionHandlers = {
                        vops.ADD: _floatOrIntMath(ssa_ops.FAdd, ssa_ops.IAdd),
                        vops.AND: _intMath(ssa_ops.IAnd, isShift=False),
                        vops.ANEWARRAY: _anewarray,
                        vops.ARRLEN: _arrlen,
                        vops.ARRLOAD: _arrload,
                        vops.ARRLOAD_OBJ: _arrload_obj,
                        vops.ARRSTORE: _arrstore,
                        vops.ARRSTORE_OBJ: _arrstore_obj,
                        vops.CHECKCAST: _checkcast,
                        vops.CONST: _const,
                        vops.CONSTNULL: _constnull,
                        vops.CONVERT: _convert,
                        vops.DIV: _floatOrIntMath(ssa_ops.FDiv, ssa_ops.IDiv),
                        vops.FCMP: _fcmp,
                        vops.GETSTATIC: _field_access,
                        vops.GETFIELD: _field_access,
                        vops.GOTO: _nop, #since gotos are added by default, this is a nop
                        vops.IF_A: _if_a,
                        vops.IF_ACMP: _if_icmp, #icmp works on objs too
                        vops.IF_I: _if_i,
                        vops.IF_ICMP: _if_icmp,
                        vops.IINC: _iinc,
                        vops.INSTANCEOF: _instanceof,
                        vops.INVOKEINIT: _invoke,
                        vops.INVOKEINTERFACE: _invoke,
                        vops.INVOKESPECIAL: _invoke,
                        vops.INVOKESTATIC: _invoke,
                        vops.INVOKEVIRTUAL: _invoke,
                        vops.JSR: _jsr,
                        vops.LCMP: _lcmp,
                        vops.LDC: _ldc,
                        vops.LOAD: _load,
                        vops.MONENTER: _monitor,
                        vops.MONEXIT: _monitor,
                        vops.MULTINEWARRAY: _multinewarray,
                        vops.MUL: _floatOrIntMath(ssa_ops.FMul, ssa_ops.IMul),
                        vops.NEG: _neg,
                        vops.NEW: _new,
                        vops.NEWARRAY: _newarray,
                        vops.NOP: _nop,
                        vops.OR: _intMath(ssa_ops.IOr, isShift=False),
                        vops.PUTSTATIC: _field_access,
                        vops.PUTFIELD: _field_access,
                        vops.REM: _floatOrIntMath(ssa_ops.FRem, ssa_ops.IRem),
                        vops.RET: _ret,
                        vops.RETURN: _return,
                        vops.SHL: _intMath(ssa_ops.IShl, isShift=True),
                        vops.SHR: _intMath(ssa_ops.IShr, isShift=True),
                        vops.STORE: _store,
                        vops.SUB: _floatOrIntMath(ssa_ops.FSub, ssa_ops.ISub),
                        vops.SWITCH: _switch,
                        vops.THROW: _throw,
                        vops.TRUNCATE: _truncate,
                        vops.USHR: _intMath(ssa_ops.IUshr, isShift=True),
                        vops.XOR: _intMath(ssa_ops.IXor, isShift=False),
                        }

def genericStackUpdate(parent, input_, iNode):
    b = iNode.before.replace('+','')
    a = iNode.after
    assert(b and set(b+a) <= set('1234'))

    replace = {c:v for c,v in zip(b, input_.stack[-len(b):])}
    newstack = input_.stack[:-len(b)]
    newstack += [replace[c] for c in a]
    return ResultDict(newstack=newstack)

def getOnNoExceptionTarget(parent, iNode):
    vop = iNode.instruction[0]
    if vop == vops.RETURN:
        return parent.returnKey
    elif vop not in (vops.RET,vops.THROW,vops.RETURN):
        return iNode.successors[0]
    return None

def processArrayInfo(newarray_info, iNode, vals):
    #There is an unfortunate tendency among Java programmers to hardcode large arrays
    #resulting in the generation of thousands of instructions simply initializing an array
    #With naive analysis, all of the stores can throw and so won't be merged until later
    #Optimize for this case by keeping track of all arrays created in the block with a
    #statically known size and type so we can mark all related instructions as nothrow and
    #hence don't have to end the block prematurely
    op = iNode.instruction[0]

    if op == vops.NEWARRAY or op == vops.ANEWARRAY:
        line = vals.line
        lenvar = line.params[1]
        assert(lenvar.type == SSA_INT)

        if lenvar.const is not None and lenvar.const >= 0:
            #has known, positive dim
            newarray_info[line.rval] = lenvar.const, line.baset
            line.outException = None

    elif op == vops.ARRSTORE or op == vops.ARRSTORE_OBJ:
        line = vals.line
        m, a, i, x = line.params
        if a not in newarray_info:
            return
        arrlen, baset = newarray_info[a]
        if i.const is None or not 0 <= i.const < arrlen:
            return
        #array element type test. For objects we check an exact match on decltype
        #which is highly conservative but should be enough to handle string literals
        if '.' not in baset[0] and baset != x.decltype:
            return
        line.outException = None

def fromInstruction(parent, block, newarray_info, iNode, initMap):
    assert(iNode.visited)
    instr = iNode.instruction

    if block is None:
        #create new partially constructed block (jump is none)
        block = BasicBlock(iNode.key, [], None)

        #now make inslots for the block
        monad = parent.makeVariable(SSA_MONAD)
        stack = [parent.makeVarFromVtype(vt, initMap) for vt in iNode.stack]
        locals_ = [parent.makeVarFromVtype(vt, initMap) for vt in iNode.locals]
        inslots = block.inslots = slots_t(monad=monad, locals=locals_, stack=stack)
    else:
        skey, inslots = block.successorStates[0]
        assert(skey == (iNode.key, False) and len(block.successorStates) == 1)
        block.successorStates = None #make sure we don't accidently access stale data
        #have to keep track of internal keys for predecessor tracking later
        block.keys.append(iNode.key)



    if iNode.before is not None and '1' in iNode.before:
        func = genericStackUpdate
    else:
        func = _instructionHandlers[instr[0]]

    vals = func(parent, inslots, iNode)
    processArrayInfo(newarray_info, iNode, vals)


    line, jump = vals.line, vals.jump
    newstack = vals.newstack if vals.newstack is not None else inslots.stack
    newlocals = vals.newlocals if vals.newlocals is not None else inslots.locals
    newmonad = line.outMonad if (line and line.outMonad) else inslots.monad
    outslot_norm = slots_t(monad=newmonad, locals=newlocals, stack=newstack)

    if line is not None:
        block.lines.append(line)
    block.successorStates = [((nodekey, False), outslot_norm) for nodekey in iNode.successors]

    #Return iNodes obviously don't have our synethetic return node as a normal successor
    if instr[0] == vops.RETURN:
        block.successorStates.append(((parent.returnKey, False), outslot_norm))

    if line and line.outException:
        assert(not jump)
        fallthrough = getOnNoExceptionTarget(parent, iNode)

        jump = ssa_jumps.OnException(parent, iNode.key, line, parent.rawExceptionHandlers(), fallthrough)
        outslot_except = slots_t(monad=newmonad, locals=newlocals, stack=[line.outException])
        block.successorStates += [((nodekey, True), outslot_except) for nodekey in jump.getExceptSuccessors()]

    if not jump:
        assert(instr[0] == vops.RETURN or len(iNode.successors) == 1)
        jump = ssa_jumps.Goto(parent, getOnNoExceptionTarget(parent, iNode))
    block.jump = jump

    block.tempvars.extend(newstack + newlocals + [newmonad])
    return block

_jump_instrs = frozenset([vops.GOTO, vops.IF_A, vops.IF_ACMP, vops.IF_I, vops.IF_ICMP, vops.JSR, vops.SWITCH])
def makeBlocks(parent, iNodes, myclsname):
    iNodes = [n for n in iNodes if n.visited]

    #create map of uninitialized -> initialized types so we can convert them
    initMap = {}
    for node in iNodes:
        if node.op == vops.NEW:
            initMap[node.push_type] = node.target_type
    initMap[verifier_types.T_UNINIT_THIS] = verifier_types.T_OBJECT(myclsname)

    #The purpose of this function is to create blocks containing multiple instructions
    #of linear code where possible. Blocks for invidual instructions will get merged
    #by later analysis anyway but it's a lot faster to merge them during creation
    jump_targets = set()
    for node in iNodes:
        if node.instruction[0] in _jump_instrs:
            jump_targets.update(node.successors)

    newarray_info = {} #store info about newly created arrays in current block
    blocks = []
    curblock = None
    for node in iNodes:
        #check if we need to start a new block
        if curblock is not None:
            keep = node.key not in jump_targets
            keep = keep and isinstance(curblock.jump, ssa_jumps.Goto)
            keep = keep and node.key == curblock.jump.getNormalSuccessors()[0]
            #for simplicity, keep jsr stuff in individual instruction blocks.
            #Note that subproc.py will need to be modified if this is changed
            keep = keep and node.instruction[0] not in (vops.JSR, vops.RET)

            if not keep:
                blocks.append(curblock)
                curblock = None
                newarray_info = {}

        curblock = fromInstruction(parent, curblock, newarray_info, node, initMap)
        assert(curblock.jump)
    blocks.append(curblock)

    for block in blocks:
        block.successorStates = collections.OrderedDict(block.successorStates)
        block.tempvars = [t for t in block.tempvars if t is not None]
    return blocks
########NEW FILE########
__FILENAME__ = float_c
from ..mixin import ValueType
from ... import floatutil as fu

SPECIALS = frozenset((fu.NAN, fu.INF, fu.NINF, fu.ZERO, fu.NZERO))

def botRange(size):
    mbits, emin, emax = size 
    mag = (1<<(mbits+1))-1, emax-mbits    
    return (-1,mag), (1,mag)

class FloatConstraint(ValueType):
    def __init__(self, size, finite, special):
        self.size = size
        self.finite = finite
        self.spec = special

        self.isBot = (special == SPECIALS) and (finite == botRange(size)) 

    @staticmethod
    def const(size, val):
        if val in SPECIALS:
            return FloatConstraint(size, (None, None), frozenset([val]))
        return FloatConstraint(size, (val, val), frozenset())

    @staticmethod
    def bot(size):
        finite = botRange(size)
        return FloatConstraint(size, finite, SPECIALS)

    @staticmethod
    def fromValues(size, vals):
        vals = set(vals)
        specs = vals & SPECIALS
        vals -= SPECIALS
        if not specs and not vals:
            return None

        if vals:
            xmin = max(vals, key=fu.sortkey)
            xmax = min(vals, key=fu.sortkey) 
        else:
            finite = None, None       
        return FloatConstraint(size, finite, specs)

    def print_(self, varstr):
        specs = map(fu.toRawFloat, self.spec)
        specs = ', '.join(map(str, specs))

        if self.finite[0]:
            fmin, fmax = map(fu.toRawFloat, self.finite)
            if fmin == fmax:
                s = '{} = {!r}'.format(varstr, fmin)
            else:
                s = '{!r} <= {} <= {!r}'.format(fmin, varstr, fmax)
            
            if specs:
                s = s + ' or ' + specs
        else:
            s = varstr + ' = ' + specs
        return s

    def _key(self): return self.finite, self.spec

    def join(*cons): #more precise (intersection)
        spec = frozenset.intersection(*[c.spec for c in cons])
        ranges = [c.finite for c in cons]

        if (None, None) in ranges:
            xmin = xmax = None
        else:
            mins, maxs = zip(*ranges)
            xmin = max(mins, key=fu.sortkey)
            xmax = min(maxs, key=fu.sortkey)
            if fu.sortkey(xmax) < fu.sortkey(xmin):
                xmin = xmax = None
        if not xmin and not spec:
            return None
        return FloatConstraint(cons[0].size, (xmin, xmax), spec)

    def meet(*cons):
        spec = frozenset.union(*[c.spec for c in cons])
        ranges = [c.finite for c in cons if c.finite != (None,None)]
        
        if ranges:
            mins, maxs = zip(*ranges)
            xmin = min(mins, key=fu.sortkey)
            xmax = max(maxs, key=fu.sortkey)
        else:
            xmin = xmax = None
        return FloatConstraint(cons[0].size, (xmin, xmax), spec)

    def __str__(self): return self.print_('?')
    def __repr__(self): return self.print_('?')
########NEW FILE########
__FILENAME__ = int_c
from ..mixin import ValueType

class IntConstraint(ValueType):
    __slots__ = "width min max".split()

    def __init__(self, width, min_, max_):
        self.width = width
        self.min = min_
        self.max = max_
        # self.isBot = (-min_ == max_+1 == (1<<width)//2)

    @staticmethod
    def range(width, min_, max_):
        if min_ > max_:
            return None
        return IntConstraint(width, min_, max_)

    @staticmethod
    def const(width, val):
        return IntConstraint(width, val, val)

    @staticmethod
    def bot(width):
        return IntConstraint(width, -1<<(width-1), (1<<(width-1))-1)

    def print_(self, varstr):
        if self.min == self.max:
            return '{} == {}'.format(varstr, self.max)
        return '{} <= {} <= {}'.format(self.min, varstr, self.max)

    def _key(self): return self.min, self.max

    def join(*cons):
        xmin = max(c.min for c in cons)
        xmax = min(c.max for c in cons)
        if xmin > xmax:
            return None
        res = IntConstraint(cons[0].width, xmin, xmax)
        return cons[0] if cons[0] == res else res

    def meet(*cons):
        xmin = min(c.min for c in cons)
        xmax = max(c.max for c in cons)
        return IntConstraint(cons[0].width, xmin, xmax)

    def __str__(self): return self.print_('?')
    def __repr__(self): return self.print_('?')
########NEW FILE########
__FILENAME__ = mixin
class ValueType(object):
    '''Define _key() and inherit from this class to implement comparison and hashing'''
    # def __init__(self, *args, **kwargs): super(ValueType, self).__init__(*args, **kwargs)
    def __eq__(self, other): return type(self) == type(other) and self._key() == other._key()
    def __ne__(self, other): return type(self) != type(other) or self._key() != other._key()
    def __hash__(self): return hash(self._key())   
########NEW FILE########
__FILENAME__ = monad_c
class MonadConstraint(object):
    def __init__(self):
        self.isBot = True

    def join(*cons): return cons[0]
    def meet(*cons): return cons[0]
########NEW FILE########
__FILENAME__ = obj_c
import itertools
from ..mixin import ValueType
from .int_c import IntConstraint
from .. import objtypes

#Possible array lengths
nonnegative = IntConstraint.range(32, 0, (1<<31)-1)
array_supers = 'java/lang/Object','java/lang/Cloneable','java/io/Serializable'
obj_fset = frozenset([objtypes.ObjectTT])

def isAnySubtype(env, x, seq):
    return any(objtypes.isSubtype(env,x,y) for y in seq)

class TypeConstraint(ValueType):
    __slots__ = "env supers exact isBot".split()
    def __init__(self, env, supers, exact):
        self.env, self.supers, self.exact = env, frozenset(supers), frozenset(exact)
        self.isBot = objtypes.ObjectTT in supers

        temp = self.supers | self.exact
        assert(not temp or min(zip(*temp)[1]) >= 0)
        assert(objtypes.NullTT not in temp)

    @staticmethod
    def fromTops(*args):
        return TypeConstraint(*args)

    def _key(self): return self.supers, self.exact
    def __nonzero__(self): return bool(self.supers or self.exact)

    def print_(self, varstr):
        supernames = ', '.join(name+'[]'*dim for name,dim in sorted(self.supers))
        exactnames = ', '.join(name+'[]'*dim for name,dim in sorted(self.exact))
        if not exactnames:
            return '{} extends {}'.format(varstr, supernames)
        elif not supernames:
            return '{} is {}'.format(varstr, exactnames)
        else:
            return '{} extends {} or is {}'.format(varstr, supernames, exactnames)

    def getSingleTType(self):
        #comSuper doesn't care about order so we can freely pass in nondeterministic order
        return objtypes.commonSupertype(self.env, list(self.supers) + list(self.exact))

    def isBoolOrByteArray(self):
        if self.supers or len(self.exact) != 2:
            return False
        bases, dims = zip(*self.exact)
        return dims[0] == dims[1] and sorted(bases) == ['.boolean','.byte']

    @staticmethod
    def reduce(env, supers, exact):
        newsupers = []
        for x in supers:
            if not isAnySubtype(env, x, newsupers):
                newsupers = [y for y in newsupers if not objtypes.isSubtype(env, y,x)]
                newsupers.append(x)

        newexact = [x for x in exact if not isAnySubtype(env, x, newsupers)]
        return TypeConstraint(env, newsupers, newexact)

    def join(*cons):
        assert(len(set(map(type, cons))) == 1)
        env = cons[0].env

        #optimize for the common case of joining with itself or with bot
        cons = set(c for c in cons if not c.isBot)
        if not cons:
            return TypeConstraint(env, obj_fset, [])
        elif len(cons) == 1:
            return cons.pop()
        assert(len(cons) == 2) #joining more than 2 not currently supported

        supers_l, exact_l = zip(*(c._key() for c in cons))

        newsupers = set()
        for t1,t2 in itertools.product(*supers_l):
            if objtypes.isSubtype(env, t1, t2):
                newsupers.add(t1)
            elif objtypes.isSubtype(env, t2, t1):
                newsupers.add(t2)
            else: #TODO: need to add special handling for interfaces here
                pass

        newexact = frozenset.union(*exact_l)
        for c in cons:
            newexact = [x for x in newexact if x in c.exact or isAnySubtype(env, x, c.supers)]
        result = TypeConstraint.reduce(cons.pop().env, newsupers, newexact)

        return result

    def meet(*cons):
        supers = frozenset.union(*(c.supers for c in cons))
        exact = frozenset.union(*(c.exact for c in cons))
        return TypeConstraint.reduce(cons[0].env, supers, exact)

class ObjectConstraint(ValueType):
    __slots__ = "null types arrlen isBot".split()
    def __init__(self, null, types, arrlen):
        self.null, self.types = null, types
        self.arrlen = arrlen
        self.isBot = null and types.isBot and arrlen == nonnegative

    @staticmethod
    def constNull(env):
        return ObjectConstraint(True, TypeConstraint(env, [], []), None)

    @staticmethod
    def fromTops(env, supers, exact, nonnull=False, arrlen=Ellipsis): #can't use None as default since it may be passed
        types = TypeConstraint(env, supers, exact)
        if nonnull and not types:
            return None
        isarray = any((t,0) in supers for t in array_supers)
        isarray = isarray or (supers and any(zip(*supers)[1]))
        isarray = isarray or (exact and any(zip(*exact)[1]))
        if arrlen is Ellipsis:
            arrlen = nonnegative if isarray else None
        else:
            assert(arrlen is None or isarray)
        return ObjectConstraint(not nonnull, types, arrlen)

    def _key(self): return self.null, self.types, self.arrlen

    def print_(self, varstr):
        s = ''
        if not self.null:
            s = 'nonnull '
        if self.types:
            s += self.types.print_(varstr)
        else:
            s += varstr + ' is null'
        return s

    def isConstNull(self): return self.null and not self.types

    def getSingleTType(self):
        return self.types.getSingleTType() if self.types else objtypes.NullTT

    def join(*cons):
        null = all(c.null for c in cons)
        types = TypeConstraint.join(*(c.types for c in cons))
        if not null and not types:
            return None

        arrlens = [c.arrlen for c in cons]
        arrlen = None if None in arrlens else IntConstraint.join(*arrlens)
        res = ObjectConstraint(null, types, arrlen)
        return cons[0] if cons[0] == res else res

    def meet(*cons):
        null = any(c.null for c in cons)
        types = TypeConstraint.meet(*(c.types for c in cons))
        arrlens = [c.arrlen for c in cons if c.arrlen is not None]
        arrlen = IntConstraint.meet(*arrlens) if arrlens else None
        return  ObjectConstraint(null, types, arrlen)

########NEW FILE########
__FILENAME__ = exceptionset
import collections, itertools
from . import objtypes
from .mixin import ValueType

class CatchSetManager(object):
    def __init__(self, env, chpairs, attributes=None):
        if attributes is not None:
            self.env, self.sets, self.mask = attributes
        else:
            self.env = env
            self.sets = collections.OrderedDict() #make this ordered since OnException relies on it

            sofar = empty = ExceptionSet.EMPTY
            for catchtype, handler in chpairs:
                old = self.sets.get(handler, empty)
                new = ExceptionSet.fromTops(env, catchtype)
                self.sets[handler] = old | (new - sofar)
                sofar = sofar | new
            self.mask = sofar
            self.pruneKeys()
        assert(not self._conscheck())

    def newMask(self, mask):
        for k in self.sets:
            self.sets[k] &= mask
        self.mask &= mask
        assert(not self._conscheck())

    def pruneKeys(self):
        for handler, catchset in list(self.sets.items()):
            if not catchset:
                del self.sets[handler]

    def copy(self):
        return CatchSetManager(0,0,(self.env, self.sets.copy(), self.mask))

    def replaceKey(self, old, new):
        assert(old in self.sets and new not in self.sets)
        self.sets[new] = self.sets[old]
        del self.sets[old]

    def replaceKeys(self, replace):
        self.sets = collections.OrderedDict((replace.get(key,key), val) for key, val in self.sets.items())

    def _conscheck(self):
        temp = ExceptionSet.EMPTY
        for v in self.sets.values():
            assert(not v & temp)
            temp |= v
        assert(temp == self.mask)

class ExceptionSet(ValueType):
    __slots__ = "env pairs".split()
    def __init__(self, env, pairs): #assumes arguments are in reduced form
        self.env = env
        self.pairs = frozenset([(x,frozenset(y)) for x,y in pairs])
        assert(not pairs or '.null' not in zip(*pairs)[0])
        #We allow env to be None for the empty set so we can construct empty sets easily
        #Any operation resulting in a nonempty set will get its env from the nonempty argument
        assert(self.empty() or self.env is not None)

        #make sure set is fully reduced
        parts = []
        for t, holes in pairs:
            parts.append(t)
            parts.extend(holes)
        assert(len(set(parts)) == len(parts))

    @staticmethod #factory
    def fromTops(env, *tops):
        return ExceptionSet(env, [(x, frozenset()) for x in tops])

    def _key(self): return self.pairs
    def empty(self): return not self.pairs
    def __nonzero__(self): return bool(self.pairs)

    def getSingleTType(self): #todo - update SSA printer
        #comSuper doesn't care about order so we can freely pass in nondeterministic order
        return objtypes.commonSupertype(self.env, [(top,0) for (top,holes) in self.pairs])

    def getTopTTs(self): return sorted([(top,0) for (top,holes) in self.pairs])

    def __sub__(self, other):
        assert(type(self) == type(other))
        if self.empty() or other.empty():
            return self
        if self == other:
            return ExceptionSet.EMPTY

        subtest = self.env.isSubclass
        pairs = self.pairs

        for pair2 in other.pairs:
            #Warning, due to a bug in Python, TypeErrors raised inside the gen expr will give an incorect error message
            #TypeError: type object argument after * must be a sequence, not generator
            #This can be worked around by using a list comprehension instead of a genexpr after the *
            pairs = itertools.chain(*[ExceptionSet.diffPair(subtest, pair1, pair2) for pair1 in pairs])
        return ExceptionSet.reduce(self.env, pairs)

    def __or__(self, other):
        assert(type(self) == type(other))
        if other.empty() or self == other:
            return self
        if self.empty():
            return other
        return ExceptionSet.reduce(self.env, self.pairs | other.pairs)

    def __and__(self, other):
        assert(type(self) == type(other))
        new = self - (self - other)
        return new

    def isdisjoint(self, other):
        return (self-other) == self

    def __str__(self):
        parts = [('{} - [{}]'.format(top, ', '.join(sorted(holes))) if holes else top) for top, holes in self.pairs]
        return 'ES[{}]'.format(', '.join(parts))
    __repr__ = __str__

    @staticmethod
    def diffPair(subtest, pair1, pair2): #subtract pair2 from pair1. Returns a list of new pairs
        #todo - find way to make this less ugly
        t1, holes1 = pair1
        t2, holes2 = pair2
        if subtest(t1,t2): #t2 >= t1
            if any(subtest(t1, h) for h in holes2):
                return pair1,
            else:
                newpairs = []
                holes2 = [h for h in holes2 if subtest(h, t1) and not any(subtest(h,h2) for h2 in holes1)]

                for h in holes2:
                    newholes = [h2 for h2 in holes1 if subtest(h2, h)]
                    newpairs.append((h, newholes))
                return newpairs
        elif subtest(t2,t1): #t2 < t1
            if any(subtest(t2, h) for h in holes1):
                return pair1,
            else:
                newpairs = [(t1,ExceptionSet.reduceHoles(subtest, list(holes1)+[t2]))]
                holes2 = [h for h in holes2 if not any(subtest(h,h2) for h2 in holes1)]

                for h in holes2:
                    newholes = [h2 for h2 in holes1 if subtest(h2, h)]
                    newpairs.append((h, newholes))
                return newpairs
        else:
            return pair1,

    @staticmethod
    def mergePair(subtest, pair1, pair2): #merge pair2 into pair1 and return the union
        t1, holes1 = pair1
        t2, holes2 = pair2
        assert(subtest(t2,t1))

        if t2 in holes1:
            holes1 = list(holes1)
            holes1.remove(t2)
            return t1, holes1 + list(holes2)

        #TODO - this can probably be made more efficient
        holes1a = set(h for h in holes1 if not subtest(h, t2))
        holes1b = [h for h in holes1 if h not in holes1a]

        merged_holes = set()
        for h1, h2 in itertools.product(holes1b, holes2):
            if subtest(h2, h1):
                merged_holes.add(h1)
            elif subtest(h1, h2):
                merged_holes.add(h2)
        merged_holes = ExceptionSet.reduceHoles(subtest, merged_holes)
        assert(len(merged_holes) <= len(holes1b) + len(holes2))
        return t1, (list(holes1a) + merged_holes)

    @staticmethod
    def reduceHoles(subtest, holes):
        newholes = []
        for hole in holes:
            for ehole in newholes:
                if subtest(hole, ehole):
                    break
            else:
                newholes = [hole] + [h for h in newholes if not subtest(h, hole)]
        return newholes

    @staticmethod
    def reduce(env, pairs):
        subtest = env.isSubclass
        pairs = [pair for pair in pairs if pair[0] not in pair[1]] #remove all degenerate pairs

        newpairs = []
        while pairs:
            top, holes = pair = pairs.pop()

            #look for an existing top to merge into
            for epair in newpairs[:]:
                etop, eholes = epair
                #new pair can be merged into existing pair
                if subtest(top, etop) and (top in eholes or not any(subtest(top, ehole) for ehole in eholes)):
                    new = ExceptionSet.mergePair(subtest, epair, pair)
                    newpairs, pairs = [new], [p for p in newpairs if p is not epair] + pairs
                    break
                #existing pair can be merged into new pair
                elif subtest(etop, top) and (etop in holes or not any(subtest(etop, hole) for hole in holes)):
                    new = ExceptionSet.mergePair(subtest, pair, epair)
                    newpairs, pairs = [new], [p for p in newpairs if p is not epair] + pairs
                    break
            #pair is incomparable to all existing pairs
            else:
                holes = ExceptionSet.reduceHoles(subtest, holes)
                newpairs.append((top,holes))
        return ExceptionSet(env, newpairs)

ExceptionSet.EMPTY = ExceptionSet(None, [])
########NEW FILE########
__FILENAME__ = excepttypes
#common exception types
ArrayOOB = 'java/lang/ArrayIndexOutOfBoundsException', 0
ArrayStore = 'java/lang/ArrayStoreException', 0
ClassCast = 'java/lang/ClassCastException', 0
MonState = 'java/lang/IllegalMonitorStateException', 0
NegArrSize = 'java/lang/NegativeArraySizeException', 0
NullPtr = 'java/lang/NullPointerException', 0
OOM = 'java/lang/OutOfMemoryError', 0
########NEW FILE########
__FILENAME__ = functionbase
class SSAFunctionBase(object):
    def __init__(self, parent, arguments):
        self.parent = parent
        self.params = list(arguments)

    def replaceVars(self, rdict):
        self.params = [rdict.get(x,x) for x in self.params]
########NEW FILE########
__FILENAME__ = graph
import itertools, collections, copy
ODict = collections.OrderedDict

from . import blockmaker,constraints, variablegraph, objtypes, subproc
from . import ssa_jumps, ssa_ops
from ..verifier.descriptors import parseUnboundMethodDescriptor
from .. import graph_util

from .. import opnames
from ..verifier import verifier_types
from .ssa_types import SSA_OBJECT, SSA_MONAD
from .ssa_types import slots_t, BasicBlock, verifierToSSAType

class SSA_Variable(object):
    __slots__ = 'type','origin','name','const','decltype'

    def __init__(self, type_, origin=None, name=""):
        self.type = type_
        self.origin = origin
        self.name = name
        self.const = None
        self.decltype = None #for objects, the inferred type from the verifier if any

    #for debugging
    def __str__(self):
        return self.name if self.name else super(Variable, self).__str__()

    def __repr__(self):
        name =  self.name if self.name else "@" + hex(id(self))
        return "Var {}".format(name)

#This class is the main IR for bytecode level methods. It consists of a control
#flow graph (CFG) in static single assignment form (SSA). Each node in the
#graph is a BasicBlock. This consists of a list of phi statements representing
#inputs, a list of operations, and a jump statement. Exceptions are represented
#explicitly in the graph with the OnException jump. Each block also keeps track
#of the unary constraints on the variables in that block.

#Handling of subprocedures is rather annoying. Each complete subproc has an associated
#ProcInfo while jsrs and rets are represented by ProcCallOp and DummyRet respectively.
#The callblock has the target and fallthrough as successors, while the fallthrough has
#the callblock as predecessor, but not the retblock. Control flow paths where the proc
#never returns are represented by ordinary jumps from blocks in the procedure to outside
#Successful completion of the proc is represented by the fallthrough edge. The fallthrough
#block gets its variables from callblock, including skip vars which don't depend on the
#proc, and variables from callop.out which represent what would have been returned
#Every proc has a reachable retblock. Jsrs with no associated ret are simply turned
#into gotos.

class SSA_Graph(object):
    entryKey, returnKey, rethrowKey = -1,-2,-3

    def __init__(self, code):
        self._interns = {} #used during initial graph creation to intern variable types
        self.code = code
        self.class_ = code.class_
        self.env = self.class_.env

        method = code.method
        inputTypes, returnTypes = parseUnboundMethodDescriptor(method.descriptor, self.class_.name, method.static)

        #entry point
        funcArgs = [self.makeVarFromVtype(vt, {}) for vt in inputTypes]
        funcInMonad = self.makeVariable(SSA_MONAD)
        entryslots = slots_t(monad=funcInMonad, locals=funcArgs, stack=[])
        self.inputArgs = [funcInMonad] + funcArgs

        entryb = BasicBlock(self.entryKey, lines=[], jump=ssa_jumps.Goto(self, 0))
        entryb.successorStates = ODict([((0, False), entryslots)])
        entryb.tempvars = [x for x in self.inputArgs if x is not None]
        del entryb.sourceStates

        #return
        newmonad = self.makeVariable(SSA_MONAD)
        newstack = [self.makeVarFromVtype(vt, {}) for vt in returnTypes[:1]] #make sure not to include dummy if returning double/long
        returnb = BasicBlock(self.returnKey, lines=[], jump=ssa_jumps.Return(self, [newmonad] + newstack))
        returnb.inslots = slots_t(monad=newmonad, locals=[], stack=newstack)
        returnb.tempvars = []

        #rethrow
        newmonad, newstack = self.makeVariable(SSA_MONAD), [self.makeVariable(SSA_OBJECT)]
        rethrowb = BasicBlock(self.rethrowKey, lines=[], jump=ssa_jumps.Rethrow(self, [newmonad] + newstack))
        rethrowb.inslots = slots_t(monad=newmonad, locals=[], stack=newstack)
        rethrowb.tempvars = []

        self.entryBlock, self.returnBlock, self.rethrowBlock = entryb, returnb, rethrowb
        self.blocks = None
        # self.procs = '' #used to store information on subprocedues (from the JSR instructions)

    def condenseBlocks(self):
        old = self.blocks
        #Can't do a consistency check on entry as the graph may be in an inconsistent state at this point
        #Since the purpose of this function is to prune unreachable blocks from self.blocks

        sccs = graph_util.tarjanSCC([self.entryBlock], lambda block:block.jump.getSuccessors())
        sccs = list(reversed(sccs))
        self.blocks = list(itertools.chain.from_iterable(map(reversed, sccs)))

        assert(set(self.blocks) <= set(old))
        if len(self.blocks) < len(old):
            kept = set(self.blocks)

            for block in self.blocks:
                for pair in block.predecessors[:]:
                    if pair[0] not in kept:
                        block.removePredPair(pair)

            if self.returnBlock not in kept:
                self.returnBlock = None
            if self.rethrowBlock not in kept:
                self.rethrowBlock = None

            for proc in self.procs:
                proc.callops = ODict((op,block) for op,block in proc.callops.items() if block not in kept)
                if proc.callops:
                    assert(proc.target in kept)
                if proc.retblock not in kept:
                    for block in proc.callops.values():
                        block.jump = ssa_jumps.Goto(self, proc.target)
                    proc.callops = None
            self.procs = [proc for proc in self.procs if proc.callops]

    def removeUnusedVariables(self):
        assert(not self.procs)
        roots = [x for x in self.inputArgs if x is not None]
        for block in self.blocks:
            roots += block.jump.params
        reachable = graph_util.topologicalSort(roots, lambda var:(var.origin.params if var.origin else []))

        keepset = set(reachable)
        assert(None not in keepset)
        def filterOps(oldops):
            newops = []
            for op in oldops:
                #if any of the params is being removed due to being unreachable, we can assume the whole function can be removed
                keep = keepset.issuperset(op.params) and not keepset.isdisjoint(op.getOutputs())
                if keep:
                    newops.append(op)
                    for v in op.getOutputs():
                        if v and v not in keepset:
                            op.removeOutput(v)
                else:
                    assert(keepset.isdisjoint(op.getOutputs()))
            return newops

        for block in self.blocks:
            block.phis = filterOps(block.phis)
            block.lines = filterOps(block.lines)
            block.filterVarConstraints(keepset)

    def _getSources(self):
        sources = collections.defaultdict(set)
        for block in self.blocks:
            for child in block.getSuccessors():
                sources[child].add(block)
        return sources

    def mergeSingleSuccessorBlocks(self):
        assert(not self.procs) # Make sure that all single jsr procs are inlined first

        replace = {}
        removed = set()
        sources = self._getSources()
        for block in self.blocks:
            if block in removed:
                continue
            while 1:
                successors = set(block.jump.getSuccessorPairs()) #Warning - make sure not to merge if we have a single successor with a double edge
                if len(successors) != 1:
                    break
                #Even if an exception thrown has single target, don't merge because we need a way to actually access the thrown exception
                if isinstance(block.jump, ssa_jumps.OnException):
                    break

                #We don't bother modifying sources upon merging since the only property we care about is number of successors, which will be unchanged
                child, jtype = successors.pop()
                if len(sources[child]) != 1:
                    break

                #We've decided to merge the blocks, now do it
                block.unaryConstraints.update(child.unaryConstraints)
                for phi in child.phis:
                    assert(len(phi.dict) == 1)
                    old, new = phi.rval, phi.get((block, jtype))
                    new = replace.get(new,new)
                    replace[old] = new

                    uc1 = block.unaryConstraints[old]
                    uc2 = block.unaryConstraints[new]
                    block.unaryConstraints[new] = constraints.join(uc1, uc2)
                    del block.unaryConstraints[old]

                block.lines += child.lines
                block.jump = child.jump

                self.returnBlock = block if child == self.returnBlock else self.returnBlock
                self.rethrowBlock = block if child == self.rethrowBlock else self.rethrowBlock
                for proc in self.procs:
                    proc.retblock = block if child == proc.retblock else proc.retblock
                    #callop values and target obviously cannot be child
                    proc.callops = ODict((op, (block if old==child else old)) for op, old in proc.callops.items())

                #remember to update phis of blocks referring to old child!
                for successor,t in block.jump.getSuccessorPairs():
                    successor.replacePredPair((child,t), (block,t))
                removed.add(child)
        self.blocks = [b for b in self.blocks if b not in removed]
        #Fix up replace dict so it can handle multiple chained replacements
        for old in replace.keys()[:]:
            while replace[old] in replace:
                replace[old] = replace[replace[old]]
        if replace:
            for block in self.blocks:
                for op in block.phis + block.lines:
                    op.replaceVars(replace)
                block.jump.replaceVars(replace)

    def disconnectConstantVariables(self):
        for block in self.blocks:
            for var, uc in block.unaryConstraints.items():
                if var.origin is not None:
                    newval = None
                    if var.type[0] == 'int':
                        if uc.min == uc.max:
                            newval = uc.min
                    elif var.type[0] == 'obj':
                        if uc.isConstNull():
                            newval = 'null'

                    if newval is not None:
                        var.origin.removeOutput(var)
                        var.origin = None
                        var.const = newval
            block.phis = [phi for phi in block.phis if phi.rval is not None]
        self._conscheck()

    def _conscheck(self):
        '''Sanity check'''
        sources = self._getSources()
        for block in self.blocks:
            assert(sources[block] == {k for k,t in block.predecessors})
            for phi in block.phis:
                assert(phi.rval is None or phi.rval in block.unaryConstraints)
                for k,v in phi.dict.items():
                    assert((v.origin is None or v in k[0].unaryConstraints))
        for proc in self.procs:
            for callop in proc.callops:
                assert(set(proc.retop.input) == set(callop.out))

    def constraintPropagation(self):
        #Propagates unary constraints (range, type, etc.) pessimistically and optimistically
        #Assumes there are no subprocedues and this has not been called yet
        assert(not self.procs)

        graph = variablegraph.makeGraph(self.env, self.blocks)
        variablegraph.processGraph(graph)
        for block in self.blocks:
            for var, oldUC in block.unaryConstraints.items():
                newUC = graph[var].output[0]
                # var.name = makename(var)
                if newUC is None:
                    # This variable is overconstrainted, meaning it must be unreachable
                    del block.unaryConstraints[var]

                    if var.origin is not None:
                        var.origin.removeOutput(var)
                        var.origin = None
                    var.name = "UNREACHABLE" #for debug printing
                    # var.name += '-'
                else:
                    newUC = constraints.join(oldUC, newUC)
                    block.unaryConstraints[var] = newUC
        self._conscheck()

    def simplifyJumps(self):
        self._conscheck()

        # Also remove blocks which use a variable detected as unreachable
        def usesInvalidVar(block):
            for op in block.lines:
                for param in op.params:
                    if param not in block.unaryConstraints:
                        return True
            return False

        for block in self.blocks:
            if usesInvalidVar(block):
                for (child,t) in block.jump.getSuccessorPairs():
                    child.removePredPair((block,t))
                block.jump = None

        #Determine if any jumps are impossible based on known constraints of params: if(0 == 0) etc
        for block in self.blocks:
            if hasattr(block.jump, 'constrainJumps'):
                assert(block.jump.params)
                oldEdges = block.jump.getSuccessorPairs()
                UCs = map(block.unaryConstraints.get, block.jump.params)
                block.jump = block.jump.constrainJumps(*UCs)

                if block.jump is None:
                    #This block has no valid successors, meaning it must be unreachable
                    #It _should_ be removed automatically in the call to condenseBlocks()
                    continue

                newEdges = block.jump.getSuccessorPairs()
                if newEdges != oldEdges:
                    pruned = [x for x in oldEdges if x not in newEdges]
                    for (child,t) in pruned:
                        child.removePredPair((block,t))

        #Unreachable blocks may not automatically be removed by jump.constrainJumps
        #Because it only looks at its own params
        badblocks = set(block for block in self.blocks if block.jump is None)
        newbad = set()
        while badblocks:
            for block in self.blocks:
                if block.jump is None:
                    continue

                badpairs = [(child,t) for child,t in block.jump.getSuccessorPairs() if child in badblocks]
                block.jump = block.jump.reduceSuccessors(badpairs)
                if block.jump is None:
                    newbad.add(block)
            badblocks, newbad = newbad, set()

        self.condenseBlocks()
        self._conscheck()

    # Subprocedure stuff #####################################################
    def _copyVar(self, var): return copy.copy(var)

    def _splitSubProc(self, proc):
        #Splits a proc into two, with one callsite using the new proc instead
        #this involved duplicating the body of the procedure
        assert(len(proc.callops) > 1)
        callop, callblock = proc.callops.items()[0]
        retblock, retop = proc.retblock, proc.retop
        target = proc.target
        ftblock = callop.fallthrough

        getpreds = lambda block:(zip(*block.predecessors)[0] if block.predecessors and block != target else [])
        region = graph_util.topologicalSort([retblock], getpreds)
        assert(target in region and retblock in region and callblock not in region and ftblock not in region)
        assert(self.entryBlock not in region)

        varmap = {}
        blockmap = {}
        for block in region:
            newb = BasicBlock(key=(block.key, callblock.key), lines=[], jump=None)
            del newb.sourceStates
            blockmap[block] = newb
            self.blocks.append(newb)

            for var, UC in block.unaryConstraints.items():
                varmap[var] = self._copyVar(var)
            newb.unaryConstraints = ODict((varmap[var],UC) for var,UC in block.unaryConstraints.items())

        #fix up successors for edges that jump outside the subproc (absconding)
        for block in region:
            newb = blockmap[block]
            for block2, t in block.jump.getSuccessorPairs():
                if block2 not in blockmap:
                    block2.predecessors.append((newb, t))
                    for phi in block2.phis:
                        phi.dict[newb, t] = varmap[phi.dict[block, t]]

        for block in region:
            newb = blockmap[block]
            newb.predecessors = [(blockmap.get(sb,sb),t) for sb,t in block.predecessors]

            newb.phis = []
            for phi in block.phis:
                vals = {(blockmap.get(sb,sb),t):varmap.get(var,var) for (sb,t),var in phi.dict.items()}
                rval = varmap[phi.rval] #origin fixed later
                rval.origin = new = ssa_ops.Phi(self, newb, vals, rval)
                newb.phis.append(new)

            for op in block.lines:
                new = copy.copy(op)
                new.replaceVars(varmap)
                new.replaceOutVars(varmap)
                newb.lines.append(new)
                for outVar in new.getOutputs():
                    if outVar is not None:
                        outVar.origin = new

            assert(not isinstance(block.jump, subproc.ProcCallOp))
            new = block.jump.clone()
            new.replaceVars(varmap)
            #jump.replaceBlocks expects to have a valid mapping for every existing block
            #quick hack, create temp dictionary
            tempmap = {b:b for b in new.getSuccessors()}
            tempmap.update(blockmap)
            new.replaceBlocks(tempmap)
            newb.jump = new

            for var in newb.unaryConstraints:
                assert(var.origin is None or var.origin in (newb.lines + newb.phis))

        #Fix up callop and ft
        target.removePredPair((callblock, False))
        for pair in target.predecessors:
            blockmap[target].removePredPair(pair)

        blockmap[retblock].target = callop.target = blockmap[target]
        del proc.callops[callop]
        proc2 = subproc.ProcInfo(blockmap[retblock], callop.target)
        proc2.callops[callop] = callblock
        self.procs.append(proc2)
        assert(len(self.blocks) == len({b.key for b in self.blocks}))

    def _inlineSubProc(self, proc):
        #Inline a proc with single callsite in place
        assert(len(proc.callops) == 1)
        callop, callblock = proc.callops.items()[0]
        retblock, retop = proc.retblock, proc.retop
        target = proc.target
        ftblock = callop.fallthrough

        getpreds = lambda block:(zip(*block.predecessors)[0] if block.predecessors and block != target else [])
        region = graph_util.topologicalSort([retblock], getpreds)
        assert(target in region and retblock in region and callblock not in region and ftblock not in region)
        assert(self.entryBlock not in region)

        #first we find any vars that bypass the proc since we have to pass them through the new blocks
        skipvars = [phi.get((callblock,False)) for phi in callop.fallthrough.phis]
        skipvars = [var for var in skipvars if var.origin is not callop]

        svarcopy = {(var, block):self._copyVar(var) for var, block in itertools.product(skipvars, region)}
        for var, block in itertools.product(skipvars, region):
            if block == target:
                assert(block.predecessors == [(callblock, False)])
                vals = {k:var for k in block.predecessors}
            else:
                vals = {k:svarcopy[var, k[0]] for k in block.predecessors}
            rval = svarcopy[var, block]
            rval.origin = phi = ssa_ops.Phi(self, block, vals, rval)
            block.phis.append(phi)
            block.unaryConstraints[rval] = callblock.unaryConstraints[var]

        outreplace = {v:svarcopy[v, retblock] for v in skipvars}
        for k, v in callop.out.items():
            outreplace[v] = retop.input[k]
            del callblock.unaryConstraints[v]

        callblock.jump = ssa_jumps.Goto(self, target)
        retblock.jump = ssa_jumps.Goto(self, ftblock)

        ftblock.replacePredPair((callblock, False), (retblock, False))
        for phi in ftblock.phis:
            phi.replaceVars(outreplace)

    def inlineSubprocs(self):
        self._conscheck()
        if not self.procs:
            return

        #establish DAG of subproc callstacks if we're doing nontrivial inlining, since we can only inline leaf procs
        sources = self._getSources()
        regions = {}
        for proc in self.procs:
            region = graph_util.topologicalSort([proc.retblock], lambda block:([] if block == proc.target else sources[block]))
            assert(self.entryBlock not in region)
            regions[proc] = frozenset(region)

        parents = {proc:[] for proc in self.procs}
        for x,y in itertools.product(self.procs, repeat=2):
            # if regions[x] < regions[y]:
            if not regions[y].isdisjoint(x.callops.values()):
                parents[x].append(y)
        print 'parents', parents

        self.procs = graph_util.topologicalSort(self.procs, parents.get)
        if any(parents.values()):
            print 'Warning, nesting subprocedures detected! This method may take forever to decompile.'

        #now inline the procs
        while self.procs:
            proc = self.procs.pop()
            while len(proc.callops) > 1:
                print 'splitting', proc
                self._splitSubProc(proc)
            print 'inlining', proc
            self._inlineSubProc(proc)
        self._conscheck()
    ##########################################################################

    #assign variable names for debugging
    varnum = collections.defaultdict(itertools.count)
    def makeVariable(self, *args, **kwargs):
        var = SSA_Variable(*args, **kwargs)
        pref = args[0][0][0]
        # var.name = pref + str(next(self.varnum[pref]))
        return var

    def makeVarFromVtype(self, vtype, initMap):
        vtype = initMap.get(vtype, vtype)
        type_ = verifierToSSAType(vtype)
        if type_ is not None:
            var = self.makeVariable(type_)
            if type_ == SSA_OBJECT:
                # Intern the variable object types to save a little memory
                # in the case of excessively long methods with large numbers
                # of identical variables, such as sun/util/resources/TimeZoneNames_*
                tt = objtypes.verifierToSynthetic(vtype)
                var.decltype = self._interned(tt)
            return var
        return None

    def _interned(self, x):
        try:
            return self._interns[x]
        except KeyError:
            if len(self._interns) < 256: #arbitrary limit
                self._interns[x] = x
            return x

    def getConstPoolArgs(self, index):
        return self.class_.cpool.getArgs(index)

    def getConstPoolType(self, index):
        return self.class_.cpool.getType(index)

    def rawExceptionHandlers(self):
        rethrow_handler = (0, self.code.codelen, self.rethrowKey, 0)
        return self.code.except_raw + [rethrow_handler]

def makePhiFromODict(parent, block, outvar, d, getter):
    pairs = {k:getter(v) for k,v in d.items()}
    return ssa_ops.Phi(parent, block, pairs, outvar)

def isTerminal(parent, block):
    return block is parent.returnBlock or block is parent.rethrowBlock

def ssaFromVerified(code, iNodes):
    parent = SSA_Graph(code)

    blocks = blockmaker.makeBlocks(parent, iNodes, code.class_.name)
    blocks = [parent.entryBlock] + blocks + [parent.returnBlock, parent.rethrowBlock]

    #each block can correspond to multiple instructions. We want all the keys of the contained instructions to refer to that block
    blockDict = {}
    for b in blocks:
        for k in b.keys:
            blockDict[k] = b


    #fixup proc info
    jsrs = [block for block in blocks if isinstance(block.jump, subproc.ProcCallOp)]
    procs = ODict((block.jump.target, subproc.ProcInfo(block)) for block in blocks if isinstance(block.jump, subproc.DummyRet))
    for block in jsrs:
        target = blockDict[block.jump.iNode.successors[0]]
        callop = block.jump
        retblock = blockDict[block.jump.iNode.returnedFrom]
        retop = retblock.jump
        assert(isinstance(callop, subproc.ProcCallOp))
        assert(isinstance(retop, subproc.DummyRet))

        #merge states from inodes to create out
        jsrslots = block.successorStates[target.key, False]

        retslots = retblock.successorStates[callop.iNode.next_instruction, False]
        del retblock.successorStates[callop.iNode.next_instruction, False]

        #Create new variables (will have origin set to callop in registerOuts)
        #Even for skip vars, we temporarily create a variable coming from the ret
        #But it won't be used, and will be later pruned anyway
        newstack = map(parent._copyVar, retslots.stack)
        newlocals = map(parent._copyVar, retslots.locals)
        newmonad = parent._copyVar(retslots.monad)
        newslots = slots_t(monad=newmonad, locals=newlocals, stack=newstack)
        callop.registerOuts(newslots)
        block.tempvars += callop.out.values()

        #The successor state uses the merged locals so it gets skipvars
        zipped = itertools.izip_longest(newlocals, jsrslots.locals, fillvalue=None)
        mask = [mask for entry,mask in retop.iNode.masks if entry == target.key][0]
        merged = [(x if i in mask else y) for i,(x,y) in enumerate(zipped)]
        merged_slots = slots_t(monad=newmonad, locals=merged, stack=newstack)

        block.successorStates[callop.iNode.next_instruction, False] = merged_slots

        proc = procs[target.key]
        proc.callops[callop] = block
        assert(proc.target == target.key and proc.retblock == retblock and proc.retop == retop)
        del callop.iNode
    #Now delete references to iNodes and fix extra input variables
    procs = procs.values()
    for proc in procs:
        del proc.retop.iNode
        assert(not proc.retblock.successorStates)
        proc.target = blockDict[proc.target]

        ops = proc.callops
        keys = set.intersection(*(set(op.input.keys()) for op in ops))
        for op in ops:
            op.input = ODict((k,v) for k,v in op.input.items() if k in keys)
    parent.procs = procs

    #Propagate successor info
    for block in blocks:
        if isTerminal(parent, block):
            continue

        assert(set(block.jump.getNormalSuccessors()) == set([k for (k,t),o in block.successorStates.items() if not t]))
        assert(set(block.jump.getExceptSuccessors()) == set([k for (k,t),o in block.successorStates.items() if t]))

        #replace the placeholder keys with actual blocks now
        block.jump.replaceBlocks(blockDict)
        for (key, exc), outstate in block.successorStates.items():
            dest = blockDict[key]
            assert(dest.sourceStates.get((block,exc), outstate) == outstate)
            dest.sourceStates[block,exc] = outstate
        del block.successorStates

    #create phi functions for input variables
    for block in blocks:
        if block is parent.entryBlock:
            block.phis = []
            block.predecessors = []
            continue
        block.predecessors = block.sourceStates.keys()
        ins = block.inslots

        ins.monad.origin = makePhiFromODict(parent, block, ins.monad, block.sourceStates, (lambda i: i.monad))
        for k, v in enumerate(ins.stack):
            if v is not None:
                v.origin = makePhiFromODict(parent, block, v, block.sourceStates, (lambda i: i.stack[k]))
        for k, v in enumerate(ins.locals):
            if v is not None:
                v.origin = makePhiFromODict(parent, block, v, block.sourceStates, (lambda i: i.locals[k]))
                assert(v.origin.rval is v)

        del block.sourceStates, block.inslots
        phivars = [ins.monad] + ins.stack + ins.locals
        block.phis = [var.origin for var in phivars if var is not None]

        for phi in block.phis:
            types = [var.type for var in phi.params]
            assert(not types or set(types) == set([phi.rval.type]))

    #Important to intern constraints to save memory on aforementioned excessively long methods
    def makeConstraint(var, _cache={}):
        key = var.type, var.const, var.decltype
        try:
            return _cache[key]
        except KeyError:
            _cache[key] = temp = constraints.fromVariable(parent.env, var)
            return temp

    #create unary constraints for each variable
    for block in blocks:
        bvars = list(block.tempvars)
        del block.tempvars
        assert(None not in bvars)

        bvars += [phi.rval for phi in block.phis]
        for op in block.lines:
            bvars += op.params
            bvars += [x for x in op.getOutputs() if x is not None]
        bvars += block.jump.params

        for var in set(bvars):
            block.unaryConstraints[var] = makeConstraint(var)

    #Make sure that branch targets are distinct, since this is assumed everywhere
    #Only necessary for if statements as the other jumps merge targets automatically
    for block in blocks:
        block.jump = block.jump.reduceSuccessors([])
    parent.blocks = blocks

    del parent._interns #no new variables should be created from vtypes after this point. Might as well free it
    parent._conscheck()
    return parent
########NEW FILE########
__FILENAME__ = mixin
class ValueType(object):
    '''Define _key() and inherit from this class to implement comparison and hashing'''
    # def __init__(self, *args, **kwargs): super(ValueType, self).__init__(*args, **kwargs)
    def __eq__(self, other): return type(self) == type(other) and self._key() == other._key()
    def __ne__(self, other): return type(self) != type(other) or self._key() != other._key()
    def __hash__(self): return hash(self._key())   
########NEW FILE########
__FILENAME__ = objtypes
from ..verifier import verifier_types as vtypes
from ..error import ClassLoaderError

#types are represented by classname, dimension
#primative types are .int, etc since these cannot be valid classnames since periods are forbidden
NullTT = '.null', 0
ObjectTT = 'java/lang/Object', 0
StringTT = 'java/lang/String', 0
ThrowableTT = 'java/lang/Throwable', 0
ClassTT = 'java/lang/Class', 0

BoolTT = '.boolean', 0
IntTT = '.int', 0
LongTT = '.long', 0
FloatTT = '.float', 0
DoubleTT = '.double', 0

ByteTT = '.byte', 0
CharTT = '.char', 0
ShortTT = '.short', 0

def isSubtype(env, x, y):
    if x == y or y == ObjectTT or x == NullTT:
        return True
    elif y == NullTT:
        return False
    xname, xdim = x
    yname, ydim = y

    if ydim > xdim:
        return False
    elif xdim > ydim: #TODO - these constants should be defined in one place to reduce risk of typos
        return yname in ('java/lang/Object','java/lang/Cloneable','java/io/Serializable')
    else:
        return xname[0] != '.' and yname[0] != '.' and env.isSubclass(xname, yname)

#Will not return interface unless all inputs are same interface or null
def commonSupertype(env, tts):
    assert(hasattr(env, 'getClass')) #catch common errors where we forget the env argument

    tts = set(tts)
    tts.discard(NullTT)

    if len(tts) == 1:
        return tts.pop()
    elif not tts:
        return NullTT

    bases, dims = zip(*tts)
    dim = min(dims)
    if max(dims) > dim or 'java/lang/Object' in bases:
        return 'java/lang/Object', dim
    #all have same dim, find common superclass
    if any(base[0] == '.' for base in bases):
        return 'java/lang/Object', dim-1

    baselists = [env.getSupers(name) for name in bases]
    common = [x for x in zip(*baselists) if len(set(x)) == 1]
    return common[-1][0], dim

######################################################################################################
_verifierConvert = {vtypes.T_INT:IntTT, vtypes.T_FLOAT:FloatTT, vtypes.T_LONG:LongTT,
        vtypes.T_DOUBLE:DoubleTT, vtypes.T_SHORT:ShortTT, vtypes.T_CHAR:CharTT,
        vtypes.T_BYTE:ByteTT, vtypes.T_BOOL:BoolTT, vtypes.T_NULL:NullTT,
        vtypes.OBJECT_INFO:ObjectTT}

def verifierToSynthetic_seq(vtypes):
    return [verifierToSynthetic(vtype) for vtype in vtypes if not (vtype.tag and vtype.tag.endswith('2'))]

def verifierToSynthetic(vtype):
    assert(vtype.tag not in (None, '.address', '.double2', '.long2', '.new', '.init'))

    if vtype in _verifierConvert:
        return _verifierConvert[vtype]

    base = vtypes.withNoDimension(vtype)
    if base in _verifierConvert:
        return _verifierConvert[base][0], vtype.dim

    return vtype.extra, vtype.dim

#returns supers, exacts
def declTypeToActual(env, decltype):
    name, dim = decltype

    #Verifier treats bool[]s and byte[]s as interchangeable, so it could really be either
    if dim and (name == ByteTT[0] or name == BoolTT[0]):
        return [], [(ByteTT[0], dim), (BoolTT[0], dim)]
    elif name[0] == '.': #primative types can't be subclassed anyway
        return [], [decltype]

    try:
        flags = env.getFlags(name)
    except ClassLoaderError: #assume the worst if we can't find the class
        flags = set(['INTERFACE'])

    #Verifier doesn't fully verify interfaces so they could be anything
    if 'INTERFACE' in flags:
        return [(ObjectTT[0],dim)], []
    else:
        exact = 'FINAL' in flags
        if exact:
            return [], [decltype]
        else:
            return [decltype], []



########NEW FILE########
__FILENAME__ = base
from ..functionbase import SSAFunctionBase
import copy

class BaseJump(SSAFunctionBase):
    def __init__(self, parent, arguments=()):
        super(BaseJump, self).__init__(parent,arguments)

    def replaceBlocks(self, blockDict):
        assert(not self.getSuccessors())

    def getNormalSuccessors(self): return []
    def getExceptSuccessors(self): return []
    def getSuccessors(self): return self.getNormalSuccessors() + self.getExceptSuccessors()
    def getSuccessorPairs(self): return [(x,False) for x in self.getNormalSuccessors()] + [(x,True) for x in self.getExceptSuccessors()]
    def reduceSuccessors(self, pairsToRemove): return self

    def clone(self): return copy.copy(self) #overriden by classes which need to do a deep copy
########NEW FILE########
__FILENAME__ = exit
from .base import BaseJump

class Return(BaseJump):
    def __init__(self, parent, arguments):
        super(Return, self).__init__(parent, arguments)

class Rethrow(BaseJump):
    def __init__(self, parent, arguments):
        super(Rethrow, self).__init__(parent, arguments)
########NEW FILE########
__FILENAME__ = goto
from .base import BaseJump

class Goto(BaseJump):
    def __init__(self, parent, target):
        super(Goto, self).__init__(parent, [])
        self.successors = [target]

    def replaceBlocks(self, blockDict):
        self.successors = [blockDict[key] for key in self.successors]

    def getNormalSuccessors(self):
        return self.successors

    def reduceSuccessors(self, pairsToRemove):
        if (self.successors[0], False) in pairsToRemove:
            return None
        return self

########NEW FILE########
__FILENAME__ = ifcmp
from .base import BaseJump
from .. import ssa_types
from ..constraints import IntConstraint, ObjectConstraint
from .goto import Goto

class If(BaseJump):
    opposites = {'eq':'ne', 'ne':'eq', 'lt':'ge', 'ge':'lt', 'gt':'le', 'le':'gt'}

    def __init__(self, parent, cmp, successors, arguments):
        super(If, self).__init__(parent, arguments)
        assert(cmp in ('eq','ne','lt','ge','gt','le'))
        self.cmp = cmp
        self.successors = successors
        self.isObj = (arguments[0].type == ssa_types.SSA_OBJECT)

    def replaceBlocks(self, blockDict):
        self.successors = [blockDict.get(key,key) for key in self.successors]

    def getNormalSuccessors(self):
        return self.successors

    def reduceSuccessors(self, pairsToRemove):
        temp = set(self.successors)
        for (child, t) in pairsToRemove:
            temp.remove(child)

        if len(temp) == 0:
            return None
        elif len(temp) == 1:
            return Goto(self.parent, temp.pop())
        return self

    ###############################################################################
    def constrainJumps(self, x, y):
        impossible = []
        for child in self.successors:
            func = self.getSuccessorConstraints((child,False))

            results = func(x,y)
            if None in results:
                assert(results == (None,None))
                impossible.append((child,False))
        return self.reduceSuccessors(impossible)

    def getSuccessorConstraints(self, (block, t)):
        assert(t is False)
        cmp_t = If.opposites[self.cmp] if block == self.successors[0] else self.cmp

        if self.isObj:
            def propagateConstraints_obj(x, y):
                if x is None or y is None:
                    return None, None
                if cmp_t == 'eq':
                    z = x.join(y)
                    return z,z
                else:
                    x2, y2 = x, y
                    if x.isConstNull():
                        yt = y.types
                        y2 = ObjectConstraint.fromTops(yt.env, yt.supers, yt.exact, nonnull=True)                   
                    if y.isConstNull():
                        xt = x.types
                        x2 = ObjectConstraint.fromTops(xt.env, xt.supers, xt.exact, nonnull=True)
                    return x2, y2
            return propagateConstraints_obj
        else:
            def propagateConstraints_int(x, y):
                if x is None or y is None:
                    return None, None
                x1, x2, y1, y2 = x.min, x.max, y.min, y.max
                if cmp_t == 'ge' or cmp_t == 'gt':
                    x1, x2, y1, y2 = y1, y2, x1, x2 

                #treat greater like less than swap before and afterwards
                if cmp_t == 'lt' or cmp_t == 'gt':
                    x2 = min(x2, y2-1)
                    y1 = max(x1+1, y1)
                elif cmp_t == 'le' or cmp_t == 'ge':
                    x2 = min(x2, y2)
                    y1 = max(x1, y1)
                elif cmp_t == 'eq':
                    x1 = y1 = max(x1, y1)
                    x2 = y2 = min(x2, y2)
                elif cmp_t == 'ne':
                    if x1 == x2 == y1 == y2:
                        return None, None
                    if x1 == x2:
                        y1 = y1 if y1 != x1 else y1+1
                        y2 = y2 if y2 != x2 else y2-1               
                    if y1 == y2:
                        x1 = x1 if x1 != y1 else x1+1
                        x2 = x2 if x2 != y2 else x2-1

                if cmp_t == 'ge' or cmp_t == 'gt':
                    x1, x2, y1, y2 = y1, y2, x1, x2 
                con1 = IntConstraint.range(x.width, x1, x2) if x1 <= x2 else None   
                con2 = IntConstraint.range(y.width, y1, y2) if y1 <= y2 else None   
                return con1, con2
            return propagateConstraints_int
########NEW FILE########
__FILENAME__ = onexception
from .base import BaseJump
from .goto import Goto
from ..exceptionset import  CatchSetManager, ExceptionSet
from ..constraints import ObjectConstraint

class OnException(BaseJump):
    def __init__(self, parent, key, line, rawExceptionHandlers, fallthrough=None):
        super(OnException, self).__init__(parent, [line.outException])
        self.default = fallthrough

        chpairs = []
        for (start, end, handler, index) in rawExceptionHandlers:
            if start <= key < end:
                catchtype = parent.getConstPoolArgs(index)[0] if index else 'java/lang/Throwable'
                chpairs.append((catchtype, handler))
        self.cs = CatchSetManager(parent.env, chpairs)
        self.cs.pruneKeys()

    def replaceExceptTarget(self, old, new):
        self.cs.replaceKeys({old:new})

    def replaceNormalTarget(self, old, new):
        self.default = new if self.default == old else self.default

    def replaceBlocks(self, blockDict):
        self.cs.replaceKeys(blockDict)
        if self.default is not None and self.default in blockDict:
            self.default = blockDict[self.default]

    def reduceSuccessors(self, pairsToRemove):
        for (child, t) in pairsToRemove:
            if t:
                self.cs.mask -= self.cs.sets[child]
                del self.cs.sets[child]
            else:
                self.replaceNormalTarget(child, None)
                
        self.cs.pruneKeys()
        if not self.cs.sets:
            if not self.default:
                return None
            return Goto(self.parent, self.default)
        return self

    def getNormalSuccessors(self):
        return [self.default] if self.default is not None else []

    def getExceptSuccessors(self):
        return self.cs.sets.keys()

    def clone(self): 
        new = super(OnException, self).clone()
        new.cs = self.cs.copy()
        return new

    ###############################################################################
    def constrainJumps(self, x):
        if x is None:
            mask = ExceptionSet.EMPTY
        else:
            mask = ExceptionSet(x.types.env, [(name,()) for name,dim in x.types.supers | x.types.exact])
        self.cs.newMask(mask)
        return self.reduceSuccessors([])

    def getSuccessorConstraints(self, (block, t)):
        if t:
            def propagateConstraints(x):
                if x is None:
                    return None
                t = x.types 
                top_tts = t.supers | t.exact
                tops = [tt[0] for tt in top_tts]
                if 'java/lang/Object' in tops:
                    tops = 'java/lang/Throwable',
                mask = ExceptionSet.fromTops(t.env, *tops)

                eset = self.cs.sets[block] & mask
                if not eset:
                    return None,
                else:
                    ntops = zip(*eset.pairs)[0]
                    return ObjectConstraint.fromTops(t.env, [(base,0) for base in ntops], [], nonnull=True),
            return propagateConstraints
        else:
            #In fallthrough case, no exception so always return invalid
            assert(block == self.default)
            return lambda arg:[None]


            
########NEW FILE########
__FILENAME__ = placeholder
from .base import BaseJump

class Placeholder(BaseJump):
    def __init__(self, parent, *args, **kwargs):
        super(Placeholder, self).__init__(parent)
########NEW FILE########
__FILENAME__ = switch
from .base import BaseJump
from ..constraints import IntConstraint
from .goto import Goto
import collections

class Switch(BaseJump):
    def __init__(self, parent, default, table, arguments):
        super(Switch, self).__init__(parent, arguments)

        #get ordered successors since our map will be unordered. Default is always first successor
        if not table:
            ordered = [default]
        else:
            tset = set()
            ordered = [x for x in (default,) + zip(*table)[1] if not x in tset and not tset.add(x)]

        self.successors = ordered
        self.reverse = collections.defaultdict(set)
        for k,v in table:
            if v != default:
                self.reverse[v].add(k)

    def getNormalSuccessors(self):
        return self.successors

    def replaceBlocks(self, blockDict):
        self.successors = [blockDict.get(key,key) for key in self.successors]
        self.reverse = {blockDict.get(k,k):v for k,v in self.reverse.items()}

    def reduceSuccessors(self, pairsToRemove):
        temp = list(self.successors)
        for (child, t) in pairsToRemove:
            temp.remove(child)

        if len(temp) == 0:
            return None
        elif len(temp) == 1:
            return Goto(self.parent, temp.pop())
        elif len(temp) < len(self.successors):
            self.successors = temp
            self.reverse = {v:self.reverse[v] for v in temp[1:]}
        return self

    #TODO - implement constrainJumps and getSuccessorConstraints

########NEW FILE########
__FILENAME__ = array
from .base import BaseOp
from ..ssa_types import SSA_INT

from .. import excepttypes
from ..constraints import IntConstraint, FloatConstraint, ObjectConstraint, DUMMY

class ArrLoad(BaseOp):
    def __init__(self, parent, args, ssatype, monad):
        super(ArrLoad, self).__init__(parent, [monad]+args, makeException=True)
        self.env = parent.env
        self.rval = parent.makeVariable(ssatype, origin=self)
        self.ssatype = ssatype

    def propagateConstraints(self, m, a, i):
        etypes = ()
        if a.null:
            etypes += (excepttypes.NullPtr,)
            if a.isConstNull():
                return None, ObjectConstraint.fromTops(self.env, [], etypes, nonnull=True), None

        if a.arrlen is None or (i.min >= a.arrlen.max) or i.max < 0:
            etypes += (excepttypes.ArrayOOB,)
            eout = ObjectConstraint.fromTops(self.env, [], etypes, nonnull=True)
            return None, eout, None
        elif (i.max >= a.arrlen.min) or i.min < 0:
            etypes += (excepttypes.ArrayOOB,)

        if self.ssatype[0] == 'int':
            rout = IntConstraint.bot(self.ssatype[1])
        elif self.ssatype[0] == 'float':
            rout = FloatConstraint.bot(self.ssatype[1])
        elif self.ssatype[0] == 'obj':
            supers = [(base,dim-1) for base,dim in a.types.supers]
            exact = [(base,dim-1) for base,dim in a.types.exact]
            rout = ObjectConstraint.fromTops(a.types.env, supers, exact)

        eout = ObjectConstraint.fromTops(self.env, [], etypes, nonnull=True)
        return rout, eout, None

class ArrStore(BaseOp):
    def __init__(self, parent, args, monad):
        super(ArrStore, self).__init__(parent, [monad]+args, makeException=True, makeMonad=True)
        self.env = parent.env

    def propagateConstraints(self, m, a, i, x):
        etypes = ()
        if a.null:
            etypes += (excepttypes.NullPtr,)
            if a.isConstNull():
                return None, ObjectConstraint.fromTops(self.env, [], etypes, nonnull=True), m

        if a.arrlen is None or (i.min >= a.arrlen.max) or i.max < 0:
            etypes += (excepttypes.ArrayOOB,)
            eout = ObjectConstraint.fromTops(self.env, [], etypes, nonnull=True)
            return None, eout, m
        elif (i.max >= a.arrlen.min) or i.min < 0:
            etypes += (excepttypes.ArrayOOB,)

        if isinstance(x, ObjectConstraint):
            exact = [(base,dim-1) for base,dim in a.types.exact]
            allowed = ObjectConstraint.fromTops(a.types.env, exact, [])
            if allowed.meet(x) != allowed:
                etypes += (excepttypes.ArrayStore,)

        eout = ObjectConstraint.fromTops(self.env, [], etypes, nonnull=True)
        return None, eout, DUMMY

class ArrLength(BaseOp):
    def __init__(self, parent, args):
        super(ArrLength, self).__init__(parent, args, makeException=True)
        self.env = parent.env
        self.rval = parent.makeVariable(SSA_INT, origin=self)
        self.outExceptionCons = ObjectConstraint.fromTops(parent.env, [], (excepttypes.NullPtr,), nonnull=True)

    def propagateConstraints(self, x):
        etypes = ()
        if x.null:
            etypes += (excepttypes.NullPtr,)
            if x.isConstNull():
                return None, ObjectConstraint.fromTops(self.env, [], etypes, nonnull=True), None

        excons = eout = ObjectConstraint.fromTops(self.env, [], etypes, nonnull=True)
        return x.arrlen, excons, None
########NEW FILE########
__FILENAME__ = base
from ..functionbase import SSAFunctionBase
from ..ssa_types import SSA_OBJECT, SSA_MONAD

class BaseOp(SSAFunctionBase):
    def __init__(self, parent, arguments, makeException=False, makeMonad=False):
        super(BaseOp, self).__init__(parent,arguments)

        self.rval = None
        self.outException = None
        self.outMonad = None

        if makeException:
            self.outException = parent.makeVariable(SSA_OBJECT, origin=self)
        if makeMonad:
            self.outMonad = parent.makeVariable(SSA_MONAD, origin=self)

    def getOutputs(self):
        return self.rval, self.outException, self.outMonad

    def removeOutput(self, var):
        outs = self.rval, self.outException, self.outMonad
        assert(var is not None and var in outs)
        self.rval, self.outException, self.outMonad = [(x if x != var else None) for x in outs]

    def replaceOutVars(self, vardict):
        self.rval, self.outException, self.outMonad = map(vardict.get, (self.rval, self.outException, self.outMonad))

    # Given input constraints, return constraints on outputs. Output is (rval, exception, monad)
    # With None returned for unused or impossible values. This should only be defined if it is
    # actually implemented.
    # def propagateConstraints(self, *cons):
########NEW FILE########
__FILENAME__ = bitwise_util
from ..constraints import IntConstraint
import itertools, operator

def split_pow2ranges(x,y):
    '''split given range into power of two ranges of form [x, x+2^k)'''
    out = []
    while x<=y:
        #The largest power of two range of the form x,k 
        #has k min of number of zeros at end of x
        #and the largest power of two that fits in y-x
        bx = bin(x)
        numzeroes = float('inf') if x==0 else (len(bx)-bx.rindex('1')-1) 
        k = min(numzeroes, (y-x+1).bit_length()-1)
        out.append((x,k))
        x += 1<<k
    assert(x == y+1)
    return out

def propagateBitwise(arg1, arg2, op, usemin, usemax):
    ranges1 = split_pow2ranges(arg1.min, arg1.max)
    ranges2 = split_pow2ranges(arg2.min, arg2.max)

    vals = []
    for (s1,k1),(s2,k2) in itertools.product(ranges1, ranges2):
        # there are three parts. The high bits fixed in both arguments,
        # the middle bits fixed in one but not the other, and the 
        # lowest bits which can be chosen freely for both arguments
        # high = op(h1,h2) and low goes from 0 to 1... but the range of
        # the middle depends on the particular operation
        # 0-x, x-1 and 0-1 for and, or, and xor respectively
        if k1 > k2:
            (s1,k1),(s2,k2) = (s2,k2),(s1,k1)

        mask1 = (1<<k1) - 1
        mask2 = (1<<k2) - 1 - mask1

        high = op(s1, s2) & ~(mask1 | mask2)
        midmin = (s1 & mask2) if usemin else 0
        midmax = (s1 & mask2) if usemax else mask2

        vals.append(high | midmin)
        vals.append(high | midmax | mask1)
    return IntConstraint.range(arg1.width, min(vals), max(vals))

def propagateAnd(x, y):
        return propagateBitwise(x, y, operator.__and__, False, True)

def propagateOr(x, y):
        return propagateBitwise(x, y, operator.__or__, True, False)

def propagateXor( x, y):
        return propagateBitwise(x, y, operator.__xor__, False, False)
########NEW FILE########
__FILENAME__ = checkcast
from .base import BaseOp
from .. import objtypes, excepttypes, ssa_types
from ..constraints import ObjectConstraint, IntConstraint

class CheckCast(BaseOp):
    def __init__(self, parent, target, args):
        super(CheckCast, self).__init__(parent,args, makeException=True)
        self.env = parent.env
        self.target_tt = target
        self.outExceptionCons = ObjectConstraint.fromTops(parent.env, [], (excepttypes.ClassCast,), nonnull=True)

    def propagateConstraints(self, x):
        for top in x.types.supers | x.types.exact:
            if not objtypes.isSubtype(self.env, top, self.target_tt):
                assert(not x.isConstNull())
                return None, self.outExceptionCons, None
        return None, None, None

class InstanceOf(BaseOp):
    def __init__(self, parent, target, args):
        super(InstanceOf, self).__init__(parent,args)
        self.env = parent.env
        self.target_tt = target
        self.rval = parent.makeVariable(ssa_types.SSA_INT, origin=self)

    def propagateConstraints(self, x):
        rvalcons = IntConstraint.range(32, 0, 1)
        return rvalcons, None, None
########NEW FILE########
__FILENAME__ = convert
from .base import BaseOp
from ..constraints import IntConstraint, FloatConstraint
from . import bitwise_util

class Convert(BaseOp):
    def __init__(self, parent, arg, source_ssa, target_ssa):
        super(Convert, self).__init__(parent, [arg])
        self.source = source_ssa
        self.target = target_ssa
        self.rval = parent.makeVariable(target_ssa, origin=self)
########NEW FILE########
__FILENAME__ = fieldaccess
from .base import BaseOp
from ...verifier.descriptors import parseFieldDescriptor
from ..ssa_types import verifierToSSAType, SSA_OBJECT, SSA_INT

from .. import objtypes, constraints
from ..constraints import IntConstraint, ObjectConstraint

# Empirically, Hotspot does enfore size restrictions on short fields
# Except that bool is still a byte
_short_constraints = {
        objtypes.ByteTT: IntConstraint.range(32, -128, 127),
        objtypes.CharTT: IntConstraint.range(32, 0, 65535),
        objtypes.ShortTT: IntConstraint.range(32, -32768, 32767),
        objtypes.IntTT: IntConstraint.bot(32)
    }
_short_constraints[objtypes.BoolTT] = _short_constraints[objtypes.ByteTT]

class FieldAccess(BaseOp):
    def __init__(self, parent, instr, info, args, monad):
        super(FieldAccess, self).__init__(parent, [monad]+args, makeException=True, makeMonad=True)

        self.instruction = instr
        self.target, self.name, self.desc = info

        dtype = None
        if 'get' in instr[0]:
            vtypes = parseFieldDescriptor(self.desc)
            stype = verifierToSSAType(vtypes[0])
            dtype = objtypes.verifierToSynthetic(vtypes[0]) #todo, find way to merge this with Invoke code?
            cat = len(vtypes)

            self.rval = parent.makeVariable(stype, origin=self)
            self.returned = [self.rval] + [None]*(cat-1)
        else:
            self.returned = []

        #just use a fixed constraint until we can do interprocedural analysis
        #output order is rval, exception, monad, defined by BaseOp.getOutputs
        env = parent.env
        self.mout = constraints.DUMMY
        self.eout = ObjectConstraint.fromTops(env, [objtypes.ThrowableTT], [])
        if self.rval is not None:
            if self.rval.type == SSA_OBJECT:
                supers, exact = objtypes.declTypeToActual(env, dtype)
                self.rout = ObjectConstraint.fromTops(env, supers, exact)
            elif self.rval.type == SSA_INT:
                self.rout = _short_constraints[dtype]
            else:
                self.rout = constraints.fromVariable(env, self.rval)

    def propagateConstraints(self, *incons):
        if self.rval is None:
            return None, self.eout, self.mout
        return self.rout, self.eout, self.mout
########NEW FILE########
__FILENAME__ = fmath
from .base import BaseOp
from ..constraints import IntConstraint

class FAdd(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)
class FDiv(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)
class FMul(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)
class FRem(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)
class FSub(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)

#Unary, unlike the others
class FNeg(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)

from .. import ssa_types
class FCmp(BaseOp):
    def __init__(self, parent, args, NaN_val):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(ssa_types.SSA_INT, origin=self)
        self.NaN_val = NaN_val

    def propagateConstraints(self, x, y):
        rvalcons = IntConstraint.range(32, -1, 1)
        return rvalcons, None, None
########NEW FILE########
__FILENAME__ = imath
from .base import BaseOp
from .. import ssa_types
from ..constraints import IntConstraint, ObjectConstraint
from . import bitwise_util

import itertools

def getNewRange(w, zmin, zmax):
    HN = 1 << w-1
    zmin = zmin + HN
    zmax = zmax + HN
    split = (zmin>>w != zmax>>w)

    if split:
        return IntConstraint.range(w, -HN, HN-1), None, None
    else:
        N = 1<<w
        return IntConstraint.range(w, (zmin % N)-HN, (zmax % N)-HN), None, None

class IAdd(BaseOp):
    def __init__(self, parent, args):
        super(IAdd, self).__init__(parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)

    def propagateConstraints(self, x, y):
        return getNewRange(x.width, x.min+y.min, x.max+y.max)

class IMul(BaseOp):
    def __init__(self, parent, args):
        super(IMul, self).__init__(parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)

    def propagateConstraints(self, x, y):
        vals = x.min*y.min, x.min*y.max, x.max*y.min, x.max*y.max
        return getNewRange(x.width, min(vals), max(vals))

class ISub(BaseOp):
    def __init__(self, parent, args):
        super(ISub, self).__init__(parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)

    def propagateConstraints(self, x, y):
        return getNewRange(x.width, x.min-y.max, x.max-y.min)

#############################################################################################
class IAnd(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)

    def propagateConstraints(self, x, y):
        return bitwise_util.propagateAnd(x,y), None, None

class IOr(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)

    def propagateConstraints(self, x, y):
        return bitwise_util.propagateOr(x,y), None, None

class IXor(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)

    def propagateConstraints(self, x, y):
        return bitwise_util.propagateXor(x,y), None, None

#############################################################################################
# Shifts currently only propogate ranges in the case where the shift is a known constant
# TODO - make this handle the general case
def getMaskedRange(x, bits):
    assert(bits < x.width)
    y = IntConstraint.const(x.width, (1<<bits) - 1)
    x = bitwise_util.propagateAnd(x,y)

    H = 1<<(bits-1)
    M = 1<<bits

    m1 = x.min if (x.max <= H-1) else -H
    m2 = x.max if (x.min >= -H) else H-1
    return m1, m2

class IShl(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)

    def propagateConstraints(self, x, y):
        if y.min < y.max:
            return IntConstraint.bot(x.width), None, None
        shift = y.min % x.width
        if not shift:
            return x, None, None
        m1, m2 = getMaskedRange(x, x.width - shift)
        return IntConstraint.range(x.width, m1<<shift, m2<<shift), None, None

class IShr(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)

    def propagateConstraints(self, x, y):
        if y.min < y.max:
            return IntConstraint.range(x.width, min(x.min, 0), max(x.max, 0)), None, None
        shift = y.min % x.width
        if not shift:
            return x, None, None
        m1, m2 = x.min, x.max
        return IntConstraint.range(x.width, m1>>shift, m2>>shift), None, None

class IUshr(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(args[0].type, origin=self)

    def propagateConstraints(self, x, y):
        M = 1<<x.width
        if y.min < y.max:
            intmax = (M//2)-1
            return IntConstraint.range(x.width, min(x.min, 0), max(x.max, intmax)), None, None
        shift = y.min % x.width
        if not shift:
            return x, None, None

        parts = [x.min, x.max]
        if x.min <= -1 <= x.max:
            parts.append(-1)        
        if x.min <= 0 <= x.max:
            parts.append(0)
        parts = [p % M for p in parts]
        m1, m2 = min(parts), max(parts)

        return IntConstraint.range(x.width, m1>>shift, m2>>shift), None, None

#############################################################################################
exec_tts = ('java/lang/ArithmeticException', 0),
class IDiv(BaseOp):
    def __init__(self, parent, args):
        super(IDiv, self).__init__(parent, args, makeException=True)
        self.rval = parent.makeVariable(args[0].type, origin=self)
        self.outExceptionCons = ObjectConstraint.fromTops(parent.env, [], exec_tts, nonnull=True)

    def propagateConstraints(self, x, y):
        excons = self.outExceptionCons if (y.min <= 0 <= y.max) else None
        if y.min == 0 == y.max:
            return None, excons, None

        #Calculate possible extremes for division, taking into account special case of intmin/-1
        intmin = -1<<(x.width - 1)
        xvals = set([x.min, x.max])
        yvals = set([y.min, y.max])

        for val in (intmin+1, 0):
            if x.min <= val <= x.max:
                xvals.add(val)
        for val in (-2,-1,1):
            if y.min <= val <= y.max:
                yvals.add(val)
        yvals.discard(0)

        vals = set()
        for xv, yv in itertools.product(xvals, yvals):
            if xv == intmin and yv == -1:
                vals.add(intmin)
            elif xv*yv < 0: #Unlike Python, Java rounds to 0 so opposite sign case must be handled specially
                vals.add(-(-xv//yv))                
            else:
                vals.add(xv//yv)

        rvalcons = IntConstraint.range(x.width, min(vals), max(vals))
        return rvalcons, excons, None

class IRem(BaseOp):
    def __init__(self, parent, args):
        super(IRem, self).__init__(parent, args, makeException=True)
        self.rval = parent.makeVariable(args[0].type, origin=self)
        self.outExceptionCons = ObjectConstraint.fromTops(parent.env, [], exec_tts, nonnull=True)

    def propagateConstraints(self, x, y):
        excons = self.outExceptionCons if (y.min <= 0 <= y.max) else None
        if y.min == 0 == y.max:
            return None, excons, None
        #only do an exact result if both values are constants, and otherwise
        #just approximate the range as -(y-1) to (y-1) (or 0 to y-1 if it's positive)
        if x.min == x.max and y.min == y.max:
            val = abs(x.min) % abs(y.min) 
            val = val if x.min >= 0 else -val
            return IntConstraint.range(x.width, val, val), None, None

        mag = max(abs(y.min), abs(y.max)) - 1
        rmin = -min(mag, abs(x.min)) if x.min < 0 else 0
        rmax = min(mag, abs(x.max)) if x.max > 0 else 0

        rvalcons = IntConstraint.range(x.width, rmin, rmax)
        return rvalcons, excons, None

###############################################################################
class ICmp(BaseOp):
    def __init__(self, parent, args):
        BaseOp.__init__(self, parent, args)
        self.rval = parent.makeVariable(ssa_types.SSA_INT, origin=self)

    def propagateConstraints(self, x, y):
        rvalcons = IntConstraint.range(32, -1, 1)
        return rvalcons, None, None
########NEW FILE########
__FILENAME__ = invoke
from .base import BaseOp
from ...verifier.descriptors import parseMethodDescriptor
from ..ssa_types import verifierToSSAType, SSA_OBJECT

from .. import objtypes, constraints
from ..constraints import ObjectConstraint

class Invoke(BaseOp):
    def __init__(self, parent, instr, info, args, monad, isThisCtor):
        super(Invoke, self).__init__(parent, [monad]+args, makeException=True, makeMonad=True)

        self.instruction = instr
        self.target, self.name, self.desc = info
        self.isThisCtor = isThisCtor #whether this is a ctor call for the current class
        vtypes = parseMethodDescriptor(self.desc)[1]

        dtype = None
        if vtypes:
            stype = verifierToSSAType(vtypes[0])
            dtype = objtypes.verifierToSynthetic(vtypes[0])
            cat = len(vtypes)

            self.rval = parent.makeVariable(stype, origin=self)
            self.returned = [self.rval] + [None]*(cat-1)
        else:
            self.rval, self.returned = None, []

        # just use a fixed constraint until we can do interprocedural analysis
        # output order is rval, exception, monad, defined by BaseOp.getOutputs
        env = parent.env

        self.mout = constraints.DUMMY
        self.eout = ObjectConstraint.fromTops(env, [objtypes.ThrowableTT], [])
        if self.rval is not None:
            if self.rval.type == SSA_OBJECT:
                supers, exact = objtypes.declTypeToActual(env, dtype)
                self.rout = ObjectConstraint.fromTops(env, supers, exact)
            else:
                self.rout = constraints.fromVariable(env, self.rval)

    def propagateConstraints(self, *incons):
        if self.rval is None:
            return None, self.eout, self.mout
        return self.rout, self.eout, self.mout
########NEW FILE########
__FILENAME__ = monitor
from .base import BaseOp
from .. import excepttypes
from ..constraints import ObjectConstraint, DUMMY

class Monitor(BaseOp):
    def __init__(self, parent, args, monad, isExit):
        BaseOp.__init__(self, parent, [monad]+args, makeException=True, makeMonad=True)
        self.exit = isExit
        self.env = parent.env

    def propagateConstraints(self, m, x):
        etypes = ()
        if x.null:
            etypes += (excepttypes.NullPtr,)
        if self.exit and not x.isConstNull():
            etypes += (excepttypes.MonState,)
        eout = ObjectConstraint.fromTops(self.env, [], etypes, nonnull=True)
        mout = m if x.isConstNull() else DUMMY
        return None, eout, mout
########NEW FILE########
__FILENAME__ = new
from .base import BaseOp
from ..ssa_types import SSA_OBJECT

from .. import excepttypes
from ..constraints import ObjectConstraint, IntConstraint, DUMMY

class New(BaseOp):
    def __init__(self, parent, name, monad):
        super(New, self).__init__(parent, [monad], makeException=True, makeMonad=True)
        self.tt = name,0
        self.rval = parent.makeVariable(SSA_OBJECT, origin=self)
        self.env = parent.env

    def propagateConstraints(self, m):
        eout = ObjectConstraint.fromTops(self.env, [], (excepttypes.OOM,), nonnull=True)
        rout = ObjectConstraint.fromTops(self.env, [], [self.tt], nonnull=True)
        return rout, eout, DUMMY

class NewArray(BaseOp):
    def __init__(self, parent, param, baset, monad):
        super(NewArray, self).__init__(parent, [monad, param], makeException=True, makeMonad=True)
        self.baset = baset
        self.rval = parent.makeVariable(SSA_OBJECT, origin=self)

        base, dim = baset
        self.tt = base, dim+1
        self.env = parent.env

    def propagateConstraints(self, m, i):
        if i.max < 0:
            eout = ObjectConstraint.fromTops(self.env, [], (excepttypes.NegArrSize,), nonnull=True)
            return None, eout, m

        etypes = (excepttypes.OOM,)
        if i.min < 0:
            etypes += (excepttypes.NegArrSize,)

        arrlen = IntConstraint.range(i.width, max(i.min, 0), i.max)
        eout = ObjectConstraint.fromTops(self.env, [], etypes, nonnull=True)
        rout = ObjectConstraint.fromTops(self.env, [], [self.tt], nonnull=True, arrlen=arrlen)
        return rout, eout, DUMMY

class MultiNewArray(BaseOp):
    def __init__(self, parent, params, type_, monad):
        super(MultiNewArray, self).__init__(parent, [monad] + params, makeException=True, makeMonad=True)
        self.tt = type_
        self.rval = parent.makeVariable(SSA_OBJECT, origin=self)
        self.env = parent.env

    def propagateConstraints(self, m, *dims):
        for i in dims:
            if i.max < 0: #ignore possibility of OOM here
                eout = ObjectConstraint.fromTops(self.env, [], (excepttypes.NegArrSize,), nonnull=True)
                return None, eout, m

        etypes = (excepttypes.OOM,)
        for i in dims:
            if i.min < 0:
                etypes += (excepttypes.NegArrSize,)
                break

        arrlen = IntConstraint.range(i.width, max(dims[0].min, 0), dims[0].max)
        eout = ObjectConstraint.fromTops(self.env, [], etypes, nonnull=True)
        rout = ObjectConstraint.fromTops(self.env, [], [self.tt], nonnull=True, arrlen=arrlen)
        return rout, eout, DUMMY
########NEW FILE########
__FILENAME__ = phi
import collections

class Phi(object):
    __slots__ = 'block dict rval'.split()

    def __init__(self, parent, block, vals, rval):
        self.block = block #used in constraint propagation
        self.dict = vals
        self.rval = rval
        assert(rval is not None)

    @property
    def params(self): return [self.dict[k] for k in self.block.predecessors]

    def get(self, key): return self.dict[key]

    #Copy these over from BaseOp so we don't need to inherit
    def replaceVars(self, rdict):
        for k in self.dict:
            self.dict[k] = rdict.get(self.dict[k], self.dict[k])

    def getOutputs(self):
        return self.rval, None, None

    def removeOutput(self, var):
        assert(var == self.rval)
        self.rval = None

    def replaceOutVars(self, vardict):
        self.rval = vardict.get(self.rval)

########NEW FILE########
__FILENAME__ = placeholder
from .base import BaseOp

class Placeholder(BaseOp):
    def __init__(self, parent, *args, **kwargs):
        super(Placeholder, self).__init__(parent, [])

        self.returned = []
        self.rval = None
########NEW FILE########
__FILENAME__ = throw
from .base import BaseOp
from .. import excepttypes
from ..constraints import ObjectConstraint

class Throw(BaseOp):
    def __init__(self, parent, args):
        super(Throw, self).__init__(parent, args, makeException=True)
        self.env = parent.env

    def propagateConstraints(self, x):
        if x.null:
            t = x.types
            exact = list(t.exact) + [excepttypes.NullPtr]
            return None, ObjectConstraint.fromTops(t.env, t.supers, exact, nonnull=True), None
        return None, x, None
########NEW FILE########
__FILENAME__ = truncate
from .base import BaseOp
from ..constraints import IntConstraint
from . import bitwise_util

class Truncate(BaseOp):
    def __init__(self, parent, arg, signed, width):
        super(Truncate, self).__init__(parent, [arg])

        self.signed, self.width = signed, width
        self.rval = parent.makeVariable(arg.type, origin=self)

    def propagateConstraints(self, x):
        #get range of target type
        w = self.width
        intw = x.width
        assert(w < intw)
        M = 1<<w

        mask = IntConstraint.const(intw, M-1)
        x = bitwise_util.propagateAnd(x,mask)

        #We have the mods in the range [0,M-1], but we want it in the range
        # [-M/2, M/2-1] so we need to find the new min and max
        if self.signed:
            HM = M>>1

            parts = [(i-M if i>=HM else i) for i in (x.min, x.max)]
            if x.min <= HM-1 <= x.max:
                parts.append(HM-1)
            if x.min <= HM <= x.max:
                parts.append(-HM)

            assert(-HM <= min(parts) <= max(parts) <= HM-1)
            return IntConstraint.range(intw, min(parts), max(parts)), None, None
        else:
            return x, None, None
########NEW FILE########
__FILENAME__ = tryreturn
from .base import BaseOp
from .. import excepttypes
from ..constraints import ObjectConstraint

class TryReturn(BaseOp):
    def __init__(self, parent, monad):
        super(TryReturn, self).__init__(parent, [monad], makeException=True)
        self.outExceptionCons = ObjectConstraint.fromTops(parent.env, [], (excepttypes.MonState,), nonnull=True)

    def propagateConstraints(self, x):
        return None, self.outExceptionCons, None
########NEW FILE########
__FILENAME__ = ssa_types
import collections

from .. import floatutil as fu
from ..verifier import verifier_types as vtypes

nt = collections.namedtuple
slots_t = nt('slots_t', ('monad', 'locals', 'stack'))

#types
SSA_INT = 'int', 32
SSA_LONG = 'int', 64
SSA_FLOAT = 'float', fu.FLOAT_SIZE
SSA_DOUBLE = 'float', fu.DOUBLE_SIZE
SSA_OBJECT = 'obj',

#internal types
SSA_MONAD = 'monad',

def verifierToSSAType(vtype):
    vtype_dict = {vtypes.T_INT:SSA_INT,
                vtypes.T_LONG:SSA_LONG,
                vtypes.T_FLOAT:SSA_FLOAT,
                vtypes.T_DOUBLE:SSA_DOUBLE}
    #These should never be passed in here
    assert(vtype.tag not in ('.new','.init'))
    if vtypes.objOrArray(vtype):
        return SSA_OBJECT
    elif vtype in vtype_dict:
        return vtype_dict[vtype]
    return None

class BasicBlock(object):
    def __init__(self, key, lines, jump):
        self.key = key
        # The list of phi statements merging incoming variables
        self.phis = None #to be filled in later
        # List of operations in the block
        self.lines = lines
        # The exit point (if, goto, etc)
        self.jump = jump
        # Holds constraints (range and type information) for each variable in the block.
        # If the value is None, this variable cannot be reached
        self.unaryConstraints = collections.OrderedDict()
        # List of predecessor pairs in deterministic order
        self.predecessors = None

        #temp vars used during graph creation
        self.sourceStates = collections.OrderedDict()
        self.successorStates = None
        self.tempvars = []
        self.inslots = None
        self.keys = [key]

    def getOps(self):
        return self.phis + self.lines

    def getSuccessors(self):
        return self.jump.getSuccessors()

    def filterVarConstraints(self, keepvars):
        pairs = [t for t in self.unaryConstraints.items() if t[0] in keepvars]
        self.unaryConstraints = collections.OrderedDict(pairs)

    def removePredPair(self, pair):
        self.predecessors.remove(pair)
        for phi in self.phis:
            del phi.dict[pair]

    def replacePredPair(self, oldp, newp):
        self.predecessors[self.predecessors.index(oldp)] = newp
        for phi in self.phis:
            phi.dict[newp] = phi.dict[oldp]
            del phi.dict[oldp]

    def __str__(self):
        return 'Block ' + str(self.key)
    __repr__ = __str__
########NEW FILE########
__FILENAME__ = subproc
import collections, copy
ODict = collections.OrderedDict

def slotsToDict(inslots):
    inputs = ODict({'m':inslots.monad})
    for i,v in enumerate(inslots.locals):
        if v is not None:
            inputs['r'+str(i)] = v
    for i,v in enumerate(inslots.stack):
        if v is not None:
            inputs['s'+str(i)] = v
    return inputs

class ProcInfo(object):
    def __init__(self, retblock, target=None):
        self.callops = ODict()
        self.retblock = retblock
        self.retop = retblock.jump
        if target is None: #if explicit target passed in, we are during proc splitting and no iNode refs are left
            target = retblock.jump.iNode.jsrTarget #just key for now, to be replaced later
        self.target = target

    def __str__(self): return 'Proc{}<{}>'.format(self.target.key, ', '.join(str(b.key) for b in self.callops.values()))
    __repr__ = __str__

###########################################################################################
class ProcJumpBase(object):
    @property
    def params(self): return self.input.values()

    def getExceptSuccessors(self): return ()
    def getSuccessors(self): return self.getNormalSuccessors()
    def getSuccessorPairs(self): return [(x,False) for x in self.getNormalSuccessors()]
    def reduceSuccessors(self, pairsToRemove): return self

class ProcCallOp(ProcJumpBase):
    def __init__(self, inslots, iNode):
        self.input = slotsToDict(inslots)
        self.iNode = iNode

        self.fallthrough = iNode.next_instruction
        self.target = iNode.successors[0]
        #self.out

    def registerOuts(self, outslots):
        self.out = slotsToDict(outslots)
        for var in self.out.values():
            assert(var.origin is None)
            var.origin = self

    def replaceBlocks(self, blockDict):
        self.fallthrough = blockDict.get(self.fallthrough, self.fallthrough)
        self.target = blockDict.get(self.target, self.target)

    def replaceVars(self, varDict):
        self.input = ODict((k,varDict.get(v,v)) for k,v in self.input.items())
        self.out = ODict((k,varDict.get(v,v)) for k,v in self.out.items())

    def getNormalSuccessors(self): return self.fallthrough, self.target

class DummyRet(ProcJumpBase):
    def __init__(self, inslots, iNode):
        self.input = slotsToDict(inslots)
        self.iNode = iNode

        self.target = iNode.jsrTarget

    def replaceBlocks(self, blockDict):
        self.target = blockDict.get(self.target, self.target)

    def replaceVars(self, varDict):
        self.input = ODict((k,varDict.get(v,v)) for k,v in self.input.items())

    def getNormalSuccessors(self): return ()

    def clone(self): return copy.copy(self) #input copied on modification anyway
########NEW FILE########
__FILENAME__ = variablegraph
import collections, itertools

from .constraints import join, meet
from .. import graph_util
#UC = unary constraints

class BaseNode(object):
    def __init__(self, processfunc, isphi, filterNone=True):
        assert(processfunc is not None)
        self.sources = []
        self.uses = []
        self.process = processfunc
        self.iters = 0
        self.propagateInvalid = not isphi
        self.filterNone = filterNone
        self.output = None #to be filled in later
        self.lastInput = []

        self.root = None #for debugging purposes, store the SSA object this node corresponds to

    def _propagate(self, inputs):
        if self.propagateInvalid and None in inputs:
            new = (None,)*len(self.output)
        else:
            if self.filterNone:
                inputs = [x for x in inputs if x is not None]
            new = self.process(*inputs)
            assert(len(self.output)==len(new))
            new = tuple(join(oldv, newv) for oldv, newv in zip(self.output, new))
        return new

    def update(self, iterlimit):
        if not self.sources:
            return False

        changed = False
        if self.iters < iterlimit:
            old, self.lastInput = self.lastInput, [node.output[key] for node,key in self.sources]
            if old != self.lastInput:
                new = self._propagate(self.lastInput)
                if new != self.output:
                    self.output = new
                    self.iters += 1
                    changed = True
        return changed

def registerUses(use, sources):
    for node,index in sources:
        node.uses.append(use)

def getJumpNode(pair, source, var, getVarNode, jumplookup):
    if (source, pair, var) in jumplookup:
        return jumplookup[(source, pair, var)]

    jump = source.jump
    if var in jump.params:
        if hasattr(jump, 'getSuccessorConstraints'):
            n = BaseNode(jump.getSuccessorConstraints(pair), False)
            n.sources = [(getVarNode(param),0) for param in jump.params]
            registerUses(n, n.sources)

            n.output = tuple(t[0].output[0] for t in n.sources)
            n.root = jump

            for i, param in enumerate(jump.params):
                jumplookup[(source, pair, param)] = n, i
            return jumplookup[(source, pair, var)]

    return getVarNode(var), 0

def makeGraph(env, blocks):
    lookup = collections.OrderedDict()
    jumplookup = {}

    variables = itertools.chain.from_iterable(block.unaryConstraints.items() for block in blocks)
    phis = itertools.chain.from_iterable(block.phis for block in blocks)
    ops = itertools.chain.from_iterable(block.lines for block in blocks)

    #We'll be using these a lot so might as well just store one copy
    varlamb = lambda *x:x
    philamb = lambda *x:[meet(*x) if x else None]

    for var, curUC in variables:
        n = BaseNode(varlamb, False)
        #sources and uses will be reassigned upon opnode creation
        n.output = (curUC,)
        lookup[var] = n
        n.root = var

    for phi in phis:
        n = BaseNode(philamb, True)
        block = phi.block
        for (source, exc) in block.predecessors:
            n.sources.append(getJumpNode((block, exc), source, phi.get((source, exc)), lookup.get, jumplookup))
        registerUses(n, n.sources)

        outnode = lookup[phi.rval]
        n.output = (outnode.output[0],)
        outnode.sources = [(n,0)]
        n.uses.append(outnode)
        n.root = phi

    for op in ops:
        if hasattr(op, 'propagateConstraints'):
            n = BaseNode(op.propagateConstraints, False)
            n.sources = [(lookup[var],0) for var in op.params]
            registerUses(n, n.sources)
        else:
            #Quick hack - if no processing function is defined, just leave sources empty so it will never be updated
            n = BaseNode(42, False)
        output = []
        for i,var in enumerate(op.getOutputs()):
            if var is None:
                output.append(None)
            else:
                vnode = lookup[var]
                output.append(vnode.output[0])
                n.uses.append(vnode)
                vnode.sources = [(n,i)]
        n.output = tuple(output)
        n.root = op
        assert(len(output) == 3)

    vnodes = lookup.values()

    #sanity check
    for node in vnodes:
        if node.sources:
            for source in zip(*node.sources)[0]:
                assert(node in source.uses)
        for use in node.uses:
            assert(node in zip(*use.sources)[0])
    return lookup

def processGraph(graph, iterlimit=5):
    sccs = graph_util.tarjanSCC(graph.values(), lambda node:[t[0] for t in node.sources])
    #iterate over sccs in topological order to improve convergence

    for scc in sccs:
        worklist = list(scc)
        scc_s = set(scc)

        while worklist:
            node = worklist.pop(0)
            changed = node.update(iterlimit)
            if changed:
                worklist.extend(use for use in node.uses if use in scc_s and use not in worklist)

########NEW FILE########
__FILENAME__ = stdcache
def shouldCache(name):
    return name.startswith('java/') or name.startswith('javax/')

class Cache(object):
    def __init__(self, env, filename):
        self.env = env
        self.filename = filename

        try:
            with open(self.filename, 'rb') as f:
                fdata = f.read()
        except IOError:
            fdata = ''

        #Note, we assume \n will never appear in a class name. This should be true for classes in the Java package,
        #but isn't necessarily true for user defined classes (Which we don't cache anyway)
        lines = fdata.split('\n')[:-1] 
        data = [[part.split(',') for part in line.split(';')] for line in lines]
        data = tuple(map(tuple, x) for x in data)
        self.data = {s[0][-1]:s for s in data}

    def _cache_info(self, class_):
        assert(class_.name not in self.data)
        newvals = class_.getSuperclassHierarchy(), class_.flags 
        self.data[class_.name] = newvals 
        writedata = ';'.join(','.join(x) for x in newvals)
        with open(self.filename, 'ab') as f:
            f.write(writedata + '\n')
        print class_.name, 'cached'

    def isCached(self, name): return name in self.data

    def superClasses(self, name):
        if name in self.data:
            return self.data[name][0]

        class_ = self.env.getClass(name, partial=True)
        if shouldCache(name):
            self._cache_info(class_)
        return class_.getSuperclassHierarchy()

    def flags(self, name):
        if name in self.data:
            return self.data[name][1]

        class_ = self.env.getClass(name, partial=True)
        if shouldCache(name):
            self._cache_info(class_)
        return class_.flags
########NEW FILE########
__FILENAME__ = descriptors
from .verifier_types import *

def parseFieldDescriptors(desc_str, unsynthesize=True):
    baseTypes = {'B':T_BYTE, 'C':T_CHAR, 'D':T_DOUBLE, 'F':T_FLOAT,
                 'I':T_INT, 'J':T_LONG, 'S':T_SHORT, 'Z':T_BOOL}

    fields = []
    while desc_str:
        oldlen = len(desc_str)
        desc_str = desc_str.lstrip('[')
        dim = oldlen - len(desc_str)
        if dim > 255:
            raise ValueError('Dimension {} > 255 in descriptor'.format(dim))
        if not desc_str:
            raise ValueError('Descriptor contains [s at end of string')

        if desc_str[0] == 'L':
            end = desc_str.find(';')
            if end == -1:
                raise ValueError('Unmatched L in descriptor')

            name = desc_str[1:end]
            desc_str = desc_str[end+1:]
            baset = T_OBJECT(name)
        else:
            if desc_str[0] not in baseTypes:
                raise ValueError('Unrecognized code {} in descriptor'.format(desc_str[0]))
            baset = baseTypes[desc_str[0]]
            desc_str = desc_str[1:]

        if dim:
            #Hotspot considers byte[] and bool[] identical for type checking purposes
            if unsynthesize and baset == T_BOOL:
                baset = T_BYTE
            baset = T_ARRAY(baset, dim)
        elif unsynthesize:
            #synthetics are only meaningful as basetype of an array
            #if they are by themselves, convert to int.
            baset = unSynthesizeType(baset)
        
        fields.append(baset)
        if baset in cat2tops:
            fields.append(cat2tops[baset])
    return fields

#get a single descriptor
def parseFieldDescriptor(desc_str, unsynthesize=True):
    rval = parseFieldDescriptors(desc_str, unsynthesize)
    
    cat = 2 if (rval and rval[0] in cat2tops) else 1
    if len(rval) != cat:
        raise ValueError('Incorrect number of fields in descriptor, expected {} but found {}'.format(cat, len(rval)))
    return rval

#Parse a string to get a Java Method Descriptor
def parseMethodDescriptor(desc_str, unsynthesize=True):
    if not desc_str.startswith('('):
        raise ValueError('Method descriptor does not start with (')

    #we need to split apart the argument list and return value
    #this is greatly complicated by the fact that ) is a legal
    #character that can appear in class names

    lp_pos = desc_str.rfind(')') #this case will work if return type is not an object
    if desc_str.endswith(';'):
        lbound = max(desc_str.rfind(';', 1, -1), 1)
        lp_pos = desc_str.find(')', lbound, -1)
    if lp_pos < 0 or desc_str[lp_pos] != ')':
        raise ValueError('Unable to split method descriptor into arguments and return type')

    arg_str = desc_str[1:lp_pos]    
    rval_str = desc_str[lp_pos+1:]

    args = parseFieldDescriptors(arg_str, unsynthesize)
    rval = [] if rval_str == 'V' else parseFieldDescriptor(rval_str, unsynthesize)
    return args, rval

#Adds self argument for nonstatic. Constructors must be handled seperately
def parseUnboundMethodDescriptor(desc_str, target, isstatic):
    args, rval = parseMethodDescriptor(desc_str)
    if not isstatic:
        args = [T_OBJECT(target)] + args
    return args, rval
########NEW FILE########
__FILENAME__ = inference_verifier
import itertools

from .. import error as error_types
from .. import opnames
from .. import bytecode
from .verifier_types import *
from .descriptors import *

#This verifier is intended to closely replicate the behavior of Hotspot's inference verifier
#http://hg.openjdk.java.net/jdk7/jdk7/jdk/file/tip/src/share/native/common/check_code.c

stackCharPatterns = {opnames.NOP:'-',
                    opnames.CONSTNULL:'-A', opnames.CONST:'-{0}',
                    opnames.LDC:'-?',
                    opnames.LOAD:'-{0}', opnames.STORE:'{0}-',
                    # opnames.ARRLOAD:'[{0}]I-{1}', opnames.ARRSTORE:'[{0}]I{1}-',
                    opnames.ARRLOAD_OBJ:'[A]I-A', opnames.ARRSTORE_OBJ:'[A]IA-',
                    opnames.IINC:'-',

                    #Stack manip handled elsewhere
                    opnames.POP:'1-', opnames.POP2:'2+1-',
                    opnames.DUP:'1-11', opnames.DUPX1:'21-121', opnames.DUPX2:'3+21-1321',
                    opnames.DUP2:'2+1-2121', opnames.DUP2X1:'32+1-21321', opnames.DUP2X2:'4+32+1-214321',
                    opnames.SWAP:'12-21',

                    opnames.ADD:'{0}{0}-{0}', opnames.SUB:'{0}{0}-{0}',
                    opnames.MUL:'{0}{0}-{0}', opnames.DIV:'{0}{0}-{0}',
                    opnames.REM:'{0}{0}-{0}', opnames.XOR:'{0}{0}-{0}',
                    opnames.AND:'{0}{0}-{0}', opnames.OR:'{0}{0}-{0}',
                    opnames.SHL:'{0}I-{0}', opnames.SHR:'{0}I-{0}',
                    opnames.USHR:'{0}I-{0}', opnames.NEG:'{0}-{0}',

                    opnames.CONVERT:'{0}-{1}',opnames.TRUNCATE:'I-I',
                    opnames.LCMP:'JJ-I', opnames.FCMP:'{0}{0}-I',
                    opnames.IF_I:'I-', opnames.IF_ICMP:'II-',
                    opnames.IF_A:'A-', opnames.IF_ACMP:'AA-', #under standard ordering, if_a comes much later

                    opnames.GOTO:'-', opnames.JSR:'-R', opnames.RET:'-',
                    opnames.SWITCH:'I-',
                    #return
                    #field, invoke

                    opnames.NEW:'-A', opnames.NEWARRAY:'I-A', opnames.ANEWARRAY:'I-A',
                    opnames.ARRLEN:'[?]-I',
                    opnames.THROW:'A-', #Hotspot uses special code 'O', but it doesn't actually matter
                    opnames.CHECKCAST:'A-A', opnames.INSTANCEOF:'A-I',
                    opnames.MONENTER:'A-',opnames.MONEXIT:'A-',
                    #multinewarray
                }

_invoke_ops = (opnames.INVOKESPECIAL,opnames.INVOKESTATIC,opnames.INVOKEVIRTUAL,opnames.INVOKEINTERFACE,opnames.INVOKEINIT,opnames.INVOKEDYNAMIC)

def getSpecificStackCode(code, instr):
    op = instr[0]
    cpool = code.class_.cpool

    #special cases, which either don't have a before or an after
    if op in (opnames.PUTSTATIC,opnames.GETSTATIC,opnames.PUTFIELD,opnames.GETFIELD,opnames.MULTINEWARRAY) + _invoke_ops:
        before = {opnames.GETSTATIC:'', opnames.GETFIELD:'A'}.get(op)
        after = {opnames.PUTSTATIC:'', opnames.PUTFIELD:'', opnames.MULTINEWARRAY:'A'}.get(op)
        #before, after may be None if unused
    elif op == opnames.ARRSTORE or op == opnames.ARRLOAD:
        typen = instr[1]
        type2 = 'I' if typen in 'BCS' else typen
        assert(typen in 'IFJDABCS')
        arrpart = '[{}]I'.format(typen)

        if op == opnames.ARRSTORE:
            before, after = arrpart+type2, ''
        else:
            before, after = arrpart, type2
    elif op == opnames.RETURN:
        typen = instr[1]
        before = '' if typen is None else typen
        after = ''
    else: #normal instruction which uses hardcoded template string
        s = stackCharPatterns[op]
        s = s.format(*instr[1:])
        before, sep, after = s.partition('-')
    return before, after

def _loadFieldDesc(cpool, ind):
    try:
        target, name, desc = cpool.getArgsCheck('Field', ind)
    except (IndexError, KeyError) as e: #TODO: find a way to make sure we aren't catching unexpected exceptions
        return None
    try:
        return parseFieldDescriptor(desc)
    except ValueError as e:
        return None

def _loadMethodDesc(cpool, ind):
    try:
        if cpool.getType(ind) not in ('Method','InterfaceMethod'):
            return None
        target, name, desc = cpool.getArgs(ind)
    except (IndexError, KeyError) as e: #TODO: find a way to make sure we aren't catching unexpected exceptions
        return None
    try:
        return parseMethodDescriptor(desc)
    except ValueError as e:
        return None

def _indexToCFMInfo(cpool, ind, typen):
    actual = cpool.getType(ind)
    #JVM_GetCPMethodClassNameUTF accepts both
    assert(actual == typen or actual == 'InterfaceMethod' and typen == 'Method')

    cname = cpool.getArgs(ind)[0]
    if cname.startswith('['):
        try:
            return parseFieldDescriptor(cname)[0]
        except ValueError as e:
            return T_INVALID
    else:
        return T_OBJECT(cname)

_vtypeMap = {T_INT:'I',T_FLOAT:'F',T_LONG:'J',T_DOUBLE:'D',T_LONG2:'',T_DOUBLE2:''}
def vtype2Char(fi):
    return _vtypeMap.get(fi, 'A')

class InstructionNode(object):
    #Difference from Hotspot: We use seperate variable for REACHED and change and flag CONSTRUCTED to or flag NOT_CONSTRUCTED
    NO_RETURN = 1<<0
    NEED_CONSTRUCTOR = 1<<1
    NOT_CONSTRUCTED = 1<<2

    #These are used only in __str__ for display purposes
    _flag_vals = {1<<0:'NO_RETURN', 1<<1:'NEED_CONSTRUCTOR',
        1<<2:'NOT_CONSTRUCTED'}

    def __init__(self, code, offsetList, key):
        self.key = key
        assert(self.key is not None) #if it is this will cause problems with origin tracking

        self.code = code
        self.env = code.class_.env
        self.class_ = code.class_
        self.cpool = self.class_.cpool

        self.instruction = code.bytecode[key]
        self.op = self.instruction[0]

        self.visited, self.changed = False, False
        self.offsetList = offsetList #store for usage calculating JSRs and the like
        self._verifyOpcodeOperands()
        self._precomputeValues()

        #Field correspondences
        # invoke*: op2.fi -> target_type
        # new, checkcast, newarray, anewarray, multinewarray, instanceof:
        #   op.fi -> push_type
        # new: op2.fi -> target_type

    def _verifyOpcodeOperands(self):

        def isTargetLegal(addr):
            return addr is not None and addr in self.offsetList
        def verifyCPType(ind, types):
            if ind < 0 or ind >= self.cpool.size():
                self.error('Invalid constant pool index {}', ind)
            t = self.cpool.getType(ind)
            if t not in types:
                self.error('Invalid constant pool type at {}.\nFound {} but expected {}', ind, t, types)

        op = self.op
        major = self.class_.version[0]

        if op == opnames.JSR:
            self.returnedFrom = None #keep track of which rets can return here - There Can Only Be One!

        if op in (opnames.IF_A, opnames.IF_I, opnames.IF_ICMP, opnames.IF_ACMP, opnames.JSR, opnames.GOTO):
            if not isTargetLegal(self.instruction[-1]):
                self.error('Illegal jump target')
        elif op == opnames.SWITCH:
            default, jumps, padding = self.instruction[1:]
            if padding != '\0'*len(padding):
                self.error('Padding must be 0 in switch instruction')

            keys, targets = zip(*jumps) if jumps else ([],[])
            if list(keys) != sorted(keys):
                self.error('Lookupswitch keys must be in sorted order')
            if not all(isTargetLegal(x) for x in targets):
                self.error('Illegal jump target')

        elif op == opnames.LDC:
            ind, cat = self.instruction[1:]
            if cat == 1:
                types = 'Int','Float','String'
                if major >= 49:
                    types += 'Class',
                if major >= 51:
                    types += 'MethodHandle','MethodType'
            else:
                types = 'Long','Double'
            verifyCPType(ind, types)

        elif op in (opnames.PUTFIELD, opnames.PUTSTATIC, opnames.GETFIELD, opnames.GETSTATIC):
            ind = self.instruction[1]
            verifyCPType(ind, ['Field'])
            if op in (opnames.PUTFIELD, opnames.GETFIELD):
                self._setProtected(True)
        elif op in _invoke_ops:
            ind = self.instruction[1]
            expected = {opnames.INVOKEINTERFACE:'InterfaceMethod', opnames.INVOKEDYNAMIC:'NameAndType'}.get(op, 'Method')
            verifyCPType(ind, [expected])

            target, name, desc = self.cpool.getArgs(ind)
            isctor = (name == '<init>')
            isinternal = name.startswith('<')

            classz = _indexToCFMInfo(self.cpool, ind, 'Method') if op != opnames.INVOKEDYNAMIC else OBJECT_INFO
            self.target_type = classz

            if isctor:
                if op != opnames.INVOKEINIT:
                    assert(op != opnames.INVOKESPECIAL) #should have been converted already
                    self.error('Initializers must be called with invokespecial')
            else:
                if isinternal: #I don't think this is actually reachable in Hotspot due to earlier checks
                    self.error('Attempt to call internal method')
                if op == opnames.INVOKESPECIAL:
                    if classz.extra not in self.class_.getSuperclassHierarchy():
                        self.error('Illegal use of invokespecial on nonsuperclass')
            if op == opnames.INVOKEINTERFACE:
                parsed_desc = _loadMethodDesc(self.cpool, ind)[0]
                if parsed_desc is None or len(parsed_desc)+1 != self.instruction[2]:
                    self.error('Argument count mismatch in invokeinterface')
            if op in (opnames.INVOKEINTERFACE, opnames.INVOKEDYNAMIC):
                if self.instruction[3] != 0:
                    self.error('Final bytes must be zero in {}', op)
            elif op in (opnames.INVOKEVIRTUAL, opnames.INVOKESPECIAL, opnames.INVOKEINIT):
                self._setProtected(False)

        elif op in (opnames.INSTANCEOF, opnames.CHECKCAST, opnames.NEW, opnames.ANEWARRAY, opnames.MULTINEWARRAY):
            ind = self.instruction[1]
            verifyCPType(ind, ['Class'])
            target = _indexToCFMInfo(self.cpool, ind, 'Class')
            if target == T_INVALID:
                self.error('Invalid class entry', op)

            self.push_type = target
            if op == opnames.ANEWARRAY:
                if target.dim >= 256:
                    self.error('Too many array dimensions')
                self.push_type = T_ARRAY(target)
            elif op == opnames.NEW:
                if target.tag != '.obj' or target.dim > 0:
                    self.error('New can only create nonarrays')
                self.push_type = T_UNINIT_OBJECT(self.key)
                self.target_type = target
            elif op == opnames.MULTINEWARRAY:
                count = self.instruction[2]
                if count > target.dim or count <= 0:
                    self.error('Illegal dimensions in multinewarray')

        elif op == opnames.NEWARRAY:
            target = parseFieldDescriptor('[' + self.instruction[1])[0]
            if target is None:
                self.error('Bad typecode for newarray')
            self.push_type = target

        elif op in (opnames.STORE, opnames.LOAD, opnames.IINC, opnames.RET):
            if op in (opnames.IINC, opnames.RET):
                ind = self.instruction[1]
            else:
                t, ind = self.instruction[1:]
                if t in 'JD':
                    ind += 1
            if ind >= self.code.locals:
                self.error('Local index {} exceeds max local count for method ({})', ind, self.code.locals)

    def _precomputeValues(self):
        #local_tag, local_ind, parsed_desc, successors
        off_i = self.offsetList.index(self.key)
        self.next_instruction = self.offsetList[off_i+1] #None if end of code

        #cache these, since they're not state dependent  and don't produce errors anyway
        self.before, self.after = getSpecificStackCode(self.code, self.instruction)
        op = self.op
        if op == opnames.LOAD:
            self.local_tag = {'I':'.int','F':'.float','J':'.long','D':'.double','A':'.obj'}[self.instruction[1]]
            self.local_ind = self.instruction[2]
        elif op == opnames.IINC:
            self.local_tag = '.int'
            self.local_ind = self.instruction[1]
        elif op == opnames.RET:
            self.local_tag = '.address'
            self.local_ind = self.instruction[1]
        elif op in (opnames.PUTFIELD, opnames.PUTSTATIC):
            self.parsed_desc = _loadFieldDesc(self.cpool, self.instruction[1])
            if self.parsed_desc is not None:
                prefix = 'A' if op == opnames.PUTFIELD else ''
                self.before = prefix + ''.join(map(vtype2Char, self.parsed_desc))
        elif op in (opnames.GETFIELD, opnames.GETSTATIC):
            self.parsed_desc = _loadFieldDesc(self.cpool, self.instruction[1])
            if self.parsed_desc is not None:
                self.after = ''.join(map(vtype2Char, self.parsed_desc))
        elif op in _invoke_ops:
            self.parsed_desc = _loadMethodDesc(self.cpool, self.instruction[1])
            if self.parsed_desc is not None:
                prefix = ''
                if op == opnames.INVOKEINIT:
                    prefix = '@'
                elif op in (opnames.INVOKEINTERFACE, opnames.INVOKEVIRTUAL, opnames.INVOKESPECIAL):
                    prefix = 'A'
                self.before = prefix + ''.join(map(vtype2Char, self.parsed_desc[0]))
                self.after = ''.join(map(vtype2Char, self.parsed_desc[1]))

        elif op == opnames.MULTINEWARRAY:
            self.before = 'I' * self.instruction[2]

        #Now get successors
        next_ = self.next_instruction

        if op in (opnames.IF_A, opnames.IF_I, opnames.IF_ICMP, opnames.IF_ACMP):
            self.successors = next_, self.instruction[2]
        elif op in (opnames.JSR, opnames.GOTO):
            self.successors = self.instruction[1],
        elif op in (opnames.RETURN, opnames.THROW):
            self.successors = ()
        elif op == opnames.RET:
            self.successors = None #calculate it when the node is reached
        elif op == opnames.SWITCH:
            opname, default, jumps, padding = self.instruction
            targets = (default,)
            if jumps:
                targets += zip(*jumps)[1]
            self.successors = targets
        else:
            self.successors = next_,

    def _setProtected(self, isfield):
        self.protected = False
        target, name, desc = self.cpool.getArgsCheck(('Field' if isfield else 'Method'), self.instruction[1])

        # Not sure what Hotspot actually does here, but this is hopefully close enough
        if '[' in target:
            return
        cname = target
        if cname in self.class_.getSuperclassHierarchy():
            while cname is not None:
                cls = self.env.getClass(cname)
                members = cls.fields if isfield else cls.methods
                for m in members:
                    if m.name == name and m.descriptor == desc:
                        if 'PROTECTED' in m.flags:
                            #Unfortunately, we have no way to tell if the classes are in the same runtime package
                            #We can be conservative and accept if they have the same static package though
                            pack1 = self.class_.name.rpartition('/')[0]
                            pack2 = cname.rpartition('/')[0]
                            self.protected = (pack1 != pack2)
                        return
                cname = cls.supername

    def _checkLocals(self):
        if self.op not in (opnames.LOAD, opnames.IINC, opnames.RET):
            return

        t,i = self.local_tag, self.local_ind
        cat2 = t in ('.long','.double')

        locs = self.locals
        if i >= len(locs) or cat2 and i >= len(locs)-1:
            self.error("Read from unintialized local {}", i)

        reg = locs[i]
        if not (reg.tag == t and reg.dim == 0):
            if t == '.obj':
                if objOrArray(reg) or reg == T_UNINIT_THIS:
                    return
                #Return address case will fallthrough and error anyway
                elif reg.tag == '.new' and reg.dim == 0:
                    return
            self.error("Invalid local at {}, expected {}", i, t)

        if cat2:
            reg = locs[i+1]
            if reg.tag != t+'2':
                self.error("Invalid local top at {}, expected {}", i+1, t)

    def _checkFlags(self):
        if self.op == opnames.RETURN:
            inc = InstructionNode
            #Hotspot only checks this for void return as it only occurs in ctors
            if (self.flags & inc.NEED_CONSTRUCTOR) and (self.flags & inc.NOT_CONSTRUCTED):
                self.error('Invalid flags at return')
            if (self.flags & (inc.NO_RETURN)):
                self.error('Invalid flags at return')

    def _popStack(self, iNodes):
        #part1, get the stack code
        #Normally, put*, multinewarray, and invoke* would be calculated at this point
        #but we precompute them
        op = self.op
        scode = self.before
        curclass_fi = T_OBJECT(self.class_.name)

        if op in _invoke_ops:
            if self.parsed_desc is None:
                self.error('Invalid method descriptor at index {}', self.instruction[1])
            elif len(self.before) >= 256:
                self.error('Method has too many arguments (max 255)')
        elif op in (opnames.PUTFIELD, opnames.PUTSTATIC):
            if self.parsed_desc is None: #Todo - make this more like what Hotspot does
                self.error('Invalid field descriptor at index {}', self.instruction[1])
        assert(scode is not None)

        #part2, check stack code
        stack = self.stack
        swap = {} #used for dup, pop, etc.
        si = len(stack)
        ci = len(scode)
        while ci > 0:
            if si <= 0:
                self.error('Cannot pop off empty stack')

            si -= 1
            ci -= 1
            top = stack[si]
            char = scode[ci]

            if char in 'IF':
                et = T_FLOAT if char == 'F' else T_INT
                if et != top:
                    self.error('Expecting {} on stack', et.tag)
            elif char in 'JD':
                et = T_DOUBLE if char == 'D' else T_LONG
                et2 = T_DOUBLE2 if char == 'D' else T_LONG2
                if stack[si-1:si+1] != (et,et2):
                    self.error('Expecting {} on stack', et.tag)
                si -= 1
            elif char == 'A':
                if not objOrArray(top):
                    #check for special exceptions
                    if top.tag == '.address' and op == opnames.STORE:
                        continue
                    #can it use uninitialized objects? Note that if_acmp is NOT included
                    uninitops = (opnames.STORE, opnames.LOAD, opnames.IF_A)
                    if top.tag in ('.new','.init') and op in uninitops:
                        continue
                    if top.tag == '.init' and op == opnames.PUTFIELD:
                        #If the index were invalid, we would have raised an error in part 1
                        ind = self.instruction[1]
                        target, name, desc = self.cpool.getArgsCheck('Field', ind)
                        for field in self.class_.fields:
                            if field.name == name and field.descriptor == desc:
                                stack = stack[:si] + (curclass_fi,) + stack[si+1:]
                                continue
            elif char == '@':
                if top.tag not in ('.new','.init'):
                    self.error('Expecting an uninitialized or new object')
            #'O' and 'a' cases omitted as unecessary
            elif char == ']':
                if top != T_NULL:
                    char2 = scode[ci-1]
                    tempMap = {'B':T_BYTE, 'C':T_CHAR, 'D':T_DOUBLE, 'F':T_FLOAT,
                                'I':T_INT, 'J':T_LONG, 'S':T_SHORT}
                    if char2 in tempMap:
                        if top != T_ARRAY(tempMap[char2]):
                            self.error('Expecting an array of {}s on stack', tempMap[char2].tag[1:])
                    elif char2 == 'A':
                        if top.dim <= 0 or (top.dim == 1 and top.tag != '.obj'):
                            self.error('Expecting an array of objects on stack')
                    elif char2 == '?':
                        if top.dim <= 0:
                            self.error('Expecting an array on stack')
                ci -= 2 #skip past [x part
            elif char in '1234':
                if top.tag in ('.double2','.long2'):
                    if ci and scode[ci-1] == '+':
                        swap[char] = top
                        swap[scode[ci-2]] = stack[si-1]
                        ci -= 2 #skip + and bottom half
                        si -= 1
                    else:
                        self.error('Attempting to split double or long on the stack')
                else:
                    swap[char] = top
                    if ci and scode[ci-1] == '+':
                        ci -= 1 #skip +

        #part3, check objects
        assert(si == 0 or stack[:si] == self.stack[:si]) #popped may differ due to putfield on uninit's editing of the stack
        stack, popped = stack[:si], stack[si:]

        if op == opnames.ARRSTORE_OBJ:
            arrt, objt = popped[0], popped[2]
            target = decrementDim(arrt)
            if not objOrArray(objt) or not objOrArray(target):
                self.error('Non array or object in aastore')
        elif op in (opnames.PUTFIELD, opnames.PUTSTATIC, opnames.GETFIELD):
            if op != opnames.PUTSTATIC: # *field
                #target: class field is defined in, and hence what the implicit object arg must be
                target = _indexToCFMInfo(self.cpool, self.instruction[1], 'Field')
                if not isAssignable(self.env, popped[0], target):
                    self.error('Accessing field on object of the incorrect type')
                elif self.protected and not isAssignable(self.env, popped[0], curclass_fi):
                    self.error('Illegal access to protected field')
            if op != opnames.GETFIELD: # put*
                if not isAssignable(self.env, popped[-1], self.parsed_desc[-1]): #Note, will only check second half for cat2
                    self.error('Storing invalid object type into field')
        elif op == opnames.THROW:
            if not isAssignable(self.env, popped[0], T_OBJECT('java/lang/Throwable')):
                self.error('Thrown object not subclass of Throwable')
        elif op == opnames.ARRLOAD_OBJ: #store array type for push_stack
            swap[op] = decrementDim(popped[0])
        elif op in _invoke_ops:
            offset = 1
            if op == opnames.INVOKEINIT:
                swap[False] = objt = popped[0]

                #Store this for use with blockmaker later on
                self.isThisCtor = (objt.tag == '.init')

                if objt.tag == '.new':
                    new_inode = iNodes[objt.extra]
                    swap[True] = target = new_inode.target_type
                    if target != self.target_type:
                        self.error('Call to constructor for wrong class')
                    if self.protected and self.class_.version >= (50,0):
                        if not isAssignable(self.env, objt, curclass_fi):
                            self.error('Illegal call to protected constructor')
                else: # .init
                    if self.target_type not in (curclass_fi, T_OBJECT(self.class_.supername)):
                        self.error('Must call current or immediate superclass constructor')
                    swap[True] = curclass_fi
            elif op in (opnames.INVOKEVIRTUAL, opnames.INVOKEINTERFACE, opnames.INVOKESPECIAL):
                objt = popped[0]
                if not isAssignable(self.env, objt, self.target_type):
                    self.error('Calling method on object of incorrect type')
                if op == opnames.INVOKESPECIAL and not isAssignable(self.env, objt, curclass_fi):
                    self.error('Calling private or super method on different class')
                # Note: this will never happen under our current implementation, but Hotspot
                # contains code for it. TODO: figure out what exactly it's doing
                # if self.protected and not isAssignable(self.env, objt, curclass_fi):
                #     #special exception for arrays pretending to implement clone()
            else:
                offset = 0 #no this for static or dynamic

            for act, expected in zip(popped[offset:], self.parsed_desc[0]):
                #Hotspot only checks for 'A' codes, but primatives should match anyway
                if not isAssignable(self.env, act, expected):
                    self.error('Incompatible argument to method call')
        elif op == opnames.RETURN:
            rvals = parseMethodDescriptor(self.code.method.descriptor)[1]
            if len(popped) != len(rvals):
                self.error('Incorrect return type')
            elif popped and not isAssignable(self.env, popped[0], rvals[0]):
                self.error('Incorrect return type')
        elif op == opnames.NEW:
            if self.push_type in stack:
                self.error('Stale uninitialized object at new instruction')
            swap[False] = self.push_type
            swap[True] = T_INVALID

        #Sanity check on swap keys
        assert(not swap or swap.keys() == [op] or set(swap.keys()) == set([False,True]) or set(swap.keys()) <= set('1234'))
        return stack, swap

    def _updateLocals(self, swap):
        op = self.op
        newlocs = list(self.locals) #mutable copies
        newmasks = list(self.masks)

        # Hotspot does things a bit strangely due to optimizations, which
        # we don't really care about. So we save all the new bits and
        # apply them at the end
        newbits = set()
        if op in (opnames.STORE, opnames.LOAD):
            cat = 2 if self.instruction[1] in 'JD' else 1
            ind = self.instruction[2]
            newbits.update(range(ind,ind+cat))

            if op == opnames.STORE:
                newlocs += [T_INVALID] * (ind+cat-len(newlocs))
                #Get the values off the old stack, since they've been popped
                newlocs[ind:ind+cat] = self.stack[-cat:]
        elif op in (opnames.IINC, opnames.RET):
            newbits.add(self.instruction[1])
        elif op == opnames.JSR:
            target = self.instruction[1]
            if newmasks and target in zip(*newmasks)[0]:
                self.error('Recursive call to JSR')
            newmasks.append((target, frozenset()))

        elif op in (opnames.INVOKEINIT, opnames.NEW):
            old, replace = swap[False], swap[True]

            for i, val in enumerate(newlocs[:]):
                if val == old:
                    newlocs[i] = replace
                    newbits.add(i)

        newmasks = [(addr,bits | newbits) for addr,bits in newmasks]
        locals_ = tuple(newlocs) if newbits else self.locals
        return locals_, tuple(newmasks)

    def _updateFlags(self, swap):
        flags = self.flags
        if self.op == opnames.INVOKEINIT and swap[False] == T_UNINIT_THIS:
            flags = flags & ~InstructionNode.NOT_CONSTRUCTED
        return flags

    def _pushStack(self, stack, swap):
        op = self.op
        curclass_fi = T_OBJECT(self.class_.name)

        scode = self.after
        new_fi = T_INVALID

        if op == opnames.LDC:
            #Hotspot appears to precompute this
            ind, cat = self.instruction[1:]
            cp_typen = self.cpool.getType(ind)
            scode = {'Int':'I','Long':'J','Double':'D','Float':'F'}.get(cp_typen, 'A')
            if scode == 'A':
                if cp_typen == 'String':
                    new_fi = T_OBJECT('java/lang/String')
                elif cp_typen == 'Class':
                    assert(self.class_.version >= (49,0)) #presuambly, this stuff should be verified during parsing
                    new_fi = T_OBJECT('java/lang/Class')
                elif cp_typen == 'MethodType':
                    assert(self.class_.version >= (51,0))
                    new_fi = T_OBJECT('java/lang/invoke/MethodType')
                elif cp_typen == 'MethodHandle':
                    assert(self.class_.version >= (51,0))
                    new_fi = T_OBJECT('java/lang/invoke/MethodHandle')
                else:
                    assert(0)
        elif op in (opnames.GETFIELD, opnames.GETSTATIC):
            if self.parsed_desc is None: #Todo - make this more like what Hotspot does
                self.error('Invalid field descriptor at index {}', self.instruction[1])
            new_fi = self.parsed_desc[0] if scode else T_INVALID
        elif op in _invoke_ops:
            if self.parsed_desc is None:
                self.error('Invalid method descriptor at index {}', self.instruction[1])
            new_fi = self.parsed_desc[-1][0] if scode else T_INVALID
        elif op == opnames.CONSTNULL:
            new_fi = T_NULL
        #Hotspot precomputes this
        elif op in (opnames.NEW, opnames.CHECKCAST, opnames.ANEWARRAY, opnames.MULTINEWARRAY, opnames.NEWARRAY):
            new_fi = self.push_type
        elif op == opnames.ARRLOAD_OBJ:
            new_fi = swap[op]
        elif op == opnames.LOAD and self.instruction[1] == 'A':
            new_fi = self.locals[self.instruction[2]]

        for char in scode:
            if char in 'IF':
                et = T_FLOAT if char == 'F' else T_INT
                stack += et,
            elif char in 'JD':
                et = T_DOUBLE if char == 'D' else T_LONG
                et2 = T_DOUBLE2 if char == 'D' else T_LONG2
                stack += et, et2
            elif char == 'R': #JSR
                et = T_ADDRESS(self.instruction[1])
                stack += et,
            elif char in '1234':
                stack += swap[char],
            elif char == 'A':
                stack += new_fi,
            else:
                assert(0)

        if op == opnames.INVOKEINIT:
            old, replace = swap[False], swap[True]
            stack = tuple((replace if x == old else x) for x in stack)

        return stack

    def _getNewState(self, iNodes):
        self._checkLocals()
        self._checkFlags()
        stack, swap = self._popStack(iNodes)
        locals_, masks = self._updateLocals(swap)
        flags = self._updateFlags(swap)
        stack = self._pushStack(stack, swap)

        assert(all(isinstance(vt, fullinfo_t) for vt in stack))
        assert(all(isinstance(vt, fullinfo_t) for vt in locals_))
        return (stack, locals_, masks, flags), swap

    def _mergeSingleSuccessor(self, other, newstate, iNodes, isException):
        newstack, newlocals, newmasks, newflags = newstate
        if self.op in (opnames.RET, opnames.JSR):
            # Note: In most cases, this will cause an error later
            # as INVALID is not allowed on the stack after merging
            # but if the stack is never merged afterwards, it's ok
            newstack = tuple((T_INVALID if x.tag == '.new' else x) for x in newstack)
            newlocals = tuple((T_INVALID if x.tag == '.new' else x) for x in newlocals)

        if self.op == opnames.RET and not isException:
            #Get the instruction before other
            off_i = self.offsetList.index(other.key)
            jsrnode = iNodes[self.offsetList[off_i-1]]

            if jsrnode.returnedFrom is not None and jsrnode.returnedFrom != self.key:
                jsrnode.error('Multiple returns to jsr')
            jsrnode.returnedFrom = self.key

            if jsrnode.visited: #if not, skip for later
                called = jsrnode.instruction[1]
                newmasks = list(newmasks)
                while newmasks and newmasks[-1][0] != called:
                    newmasks.pop()
                if not newmasks:
                    self.error('Returning to jsr not in current call stack')
                mask = newmasks.pop()[1]

                #merge locals using mask
                zipped = itertools.izip_longest(newlocals, jsrnode.locals, fillvalue=T_INVALID)
                newlocals = tuple((x if i in mask else y) for i,(x,y) in enumerate(zipped))
                newmasks = tuple(newmasks)
            else:
                return

        if not other.visited:
            other.stack, other.locals, other.masks, other.flags = newstack, newlocals, newmasks, newflags
            other.visited = other.changed = True
        else:
            #Merge stack
            oldstack = other.stack
            if len(oldstack) != len(newstack):
                other.error('Inconsistent stack height {} != {}', len(oldstack), len(newstack))
            if any(not isAssignable(self.env, new, old) for new,old in zip(newstack, oldstack)):
                other.changed = True
                other.stack = tuple(mergeTypes(self.env, new, old) for new,old in zip(newstack, oldstack))
                if T_INVALID in other.stack:
                    other.error('Incompatible types in merged stack')

            #Merge locals
            if len(newlocals) < len(other.locals):
                other.locals = other.locals[:len(newlocals)]
                other.changed = True

            zipped = list(itertools.izip_longest(newlocals, other.locals, fillvalue=T_INVALID))
            okcount = 0
            for x,y in zipped:
                if isAssignable(self.env, x, y):
                    okcount += 1
                else:
                    break

            if okcount < len(other.locals):
                merged = list(other.locals[:okcount])
                merged += [mergeTypes(self.env, new, old) for new,old in zipped[okcount:]]
                while merged and merged[-1] == T_INVALID:
                    merged.pop()
                other.locals = tuple(merged)
                other.changed = True

            #Merge Masks
            last_match = -1
            mergedmasks = []
            for entry1, mask1 in other.masks:
                for j,(entry2,mask2) in enumerate(newmasks):
                    if j>last_match and entry1 == entry2:
                        item = entry1, (mask1 | mask2)
                        mergedmasks.append(item)
                        last_match = j
            newmasks = tuple(mergedmasks)
            if other.masks != newmasks:
                other.masks = newmasks
                other.changed = True

            #Merge flags
            if other.flags != newflags:
                other.flags = newflags
                other.changed = True

    ###################################################################
    def error(self, msg, *args):
        msg = msg.format(*args, self=self)
        msg = msg + '\n\n' + str(self)
        raise error_types.VerificationError(msg)

    def update(self, iNodes, exceptions):
        assert(self.visited)
        self.changed = False

        newstate, swap = self._getNewState(iNodes)
        newstack, newlocals, newmasks, newflags = newstate

        successors = self.successors
        if self.op == opnames.JSR:
            if self.returnedFrom is not None:
                iNodes[self.returnedFrom].changed = True
        if successors is None:
            assert(self.op == opnames.RET)
            called = self.locals[self.instruction[1]].extra
            temp = [n.next_instruction for n in iNodes.values() if (n.op == opnames.JSR and n.instruction[1] == called)]
            successors = self.successors = tuple(temp)
            self.jsrTarget = called #store for later use in ssa creation

        #Merge into exception handlers first
        for (start,end),(handler,execStack) in exceptions:
            if start <= self.key < end:
                if self.op != opnames.INVOKEINIT:
                    self._mergeSingleSuccessor(handler, (execStack, newlocals, newmasks, newflags), iNodes, True)
                else: #two cases since the ctor may suceed or fail before throwing
                    #If ctor is being invoked on this, update flags appropriately
                    tempflags = newflags
                    if swap[False] == T_UNINIT_THIS:
                        tempflags |= InstructionNode.NO_RETURN

                    self._mergeSingleSuccessor(handler, (execStack, self.locals, self.masks, self.flags), iNodes, True)
                    self._mergeSingleSuccessor(handler, (execStack, newlocals, newmasks, tempflags), iNodes, True)

        #Now regular successors
        for k in self.successors:
            self._mergeSingleSuccessor(iNodes[k], (newstack, newlocals, newmasks, newflags), iNodes, False)

    def __str__(self):
        lines = ['{}: {}'.format(self.key, bytecode.printInstruction(self.instruction))]
        if self.visited:
            flags = [v for k,v in InstructionNode._flag_vals.items() if k & self.flags]
            if flags:
                lines.append('Flags: ' + ', '.join(flags))
            lines.append('Stack: ' + ', '.join(map(str, self.stack)))
            lines.append('Locals: ' + ', '.join(map(str, self.locals)))
            if self.masks:
                lines.append('Masks:')
                lines += ['\t{}: {}'.format(entry, sorted(cset)) for entry,cset in self.masks]
        else:
            lines.append('\tunvisited')
        return '\n'.join(lines) + '\n'

def verifyBytecode(code):
    method, class_ = code.method, code.class_
    args, rval = parseUnboundMethodDescriptor(method.descriptor, class_.name, method.static)
    env = class_.env

    startFlags = 0
    #Object has no superclass to construct, so it doesn't get an uninit this
    if method.isConstructor and class_.name != 'java/lang/Object':
        assert(args[0] == T_OBJECT(class_.name))
        args[0] = T_UNINIT_THIS
        startFlags |= InstructionNode.NEED_CONSTRUCTOR
        startFlags |= InstructionNode.NOT_CONSTRUCTED
    assert(len(args) <= 255)
    args = tuple(args)

    maxstack, maxlocals = code.stack, code.locals
    assert(len(args) <= maxlocals)

    offsets = tuple(sorted(code.bytecode.keys())) + (None,) #sentinel at end as invalid index
    iNodes = [InstructionNode(code, offsets, key) for key in offsets[:-1]]
    iNodeLookup = {n.key:n for n in iNodes}

    keys = frozenset(iNodeLookup)
    for raw in code.except_raw:
        if not ((0 <= raw.start < raw.end) and (raw.start in keys) and
            (raw.handler in keys) and (raw.end in keys or raw.end == code.codelen)):

            keylist = sorted(keys) + [code.codelen]
            msg = "Illegal exception handler: {}\nValid offsets are: {}".format(raw, ', '.join(map(str, keylist)))
            raise error_types.VerificationError(msg)

    def makeException(rawdata):
        if rawdata.type_ind:
            typen = class_.cpool.getArgsCheck('Class', rawdata.type_ind)
        else:
            typen = 'java/lang/Throwable'
        t = T_OBJECT(typen)
        if not (isAssignable(env, t, T_OBJECT('java/lang/Throwable'))):
            error_types.VerificationError('Invalid exception handler type: ' + typen)
        return (rawdata.start, rawdata.end), (iNodeLookup[rawdata.handler], (t,))
    exceptions = map(makeException, code.except_raw)

    start = iNodes[0]
    start.stack, start.locals, start.masks, start.flags = (), args, (), startFlags
    start.visited, start.changed = True, True

    done = False
    while not done:
        done = True
        for node in iNodes:
            if node.changed:
                node.update(iNodeLookup, exceptions)
                done = False
    return iNodes
########NEW FILE########
__FILENAME__ = verifier_types
import collections

#Define types for Inference
nt = collections.namedtuple
fullinfo_t = nt('fullinfo_t', ['tag','dim','extra'])

#Differences from Hotspot with our tags:
#BOGUS changed to None. Array omitted as it is unused. Void omitted as unecessary. Boolean added
valid_tags = ['.'+x for x in 'int float double double2 long long2 obj new init address byte short char boolean'.split()]
valid_tags = frozenset([None] + valid_tags)

def _makeinfo(tag, dim=0, extra=None):
    assert(tag in valid_tags)
    return fullinfo_t(tag, dim, extra)


T_INVALID = _makeinfo(None)
T_INT = _makeinfo('.int')
T_FLOAT = _makeinfo('.float')
T_DOUBLE = _makeinfo('.double')
T_DOUBLE2 = _makeinfo('.double2') #Hotspot only uses these in locals, but we use them on the stack too to simplify things
T_LONG = _makeinfo('.long')
T_LONG2 = _makeinfo('.long2')

T_NULL = _makeinfo('.obj')
T_UNINIT_THIS = _makeinfo('.init')

T_BYTE = _makeinfo('.byte')
T_SHORT = _makeinfo('.short')
T_CHAR = _makeinfo('.char')
T_BOOL = _makeinfo('.boolean') #Hotspot doesn't have a bool type, but we can use this elsewhere

cat2tops = {T_LONG:T_LONG2, T_DOUBLE:T_DOUBLE2}

#types with arguments
def T_ADDRESS(entry):
    return _makeinfo('.address', extra=entry)

def T_OBJECT(name):
    return _makeinfo('.obj', extra=name)

def T_ARRAY(baset, newDimensions=1):
    assert(0 <= baset.dim <= 255-newDimensions)
    return _makeinfo(baset.tag, baset.dim+newDimensions, baset.extra)

def T_UNINIT_OBJECT(origin):
    return _makeinfo('.new', extra=origin)

OBJECT_INFO = T_OBJECT('java/lang/Object')
CLONE_INFO = T_OBJECT('java/lang/Cloneable')
SERIAL_INFO = T_OBJECT('java/io/Serializable')

def objOrArray(fi): #False on uninitialized
    return fi.tag == '.obj' or fi.dim > 0

def unSynthesizeType(t):
    if t in (T_BOOL, T_BYTE, T_CHAR, T_SHORT):
        return T_INT
    return t

def decrementDim(fi):
    if fi == T_NULL:
        return T_NULL
    assert(fi.dim)
    
    tag = unSynthesizeType(fi).tag if fi.dim <= 1 else fi.tag
    return _makeinfo(tag, fi.dim-1, fi.extra)

def withNoDimension(fi):
    return _makeinfo(fi.tag, 0, fi.extra)

def _decToObjArray(fi):
    return fi if fi.tag == '.obj' else T_ARRAY(OBJECT_INFO, fi.dim-1)

def _arrbase(fi):
    return _makeinfo(fi.tag, 0, fi.extra)

def mergeTypes(env, t1, t2, forAssignment=False):
    #Note: This function is intended to have the same results as the equivalent function in Hotspot's old inference verifier
    if t1 == t2:
        return t1
    #non objects must match exactly
    if not objOrArray(t1) or not objOrArray(t2):
        return T_INVALID

    if t1 == T_NULL:
        return t2
    elif t2 == T_NULL:
        return t1

    if t1 == OBJECT_INFO or t2 == OBJECT_INFO:
        if forAssignment and t2.dim == 0 and 'INTERFACE' in env.getFlags(t2.extra):
            return t2 #Hack for interface assignment
        return OBJECT_INFO

    if t1.dim or t2.dim:
        for x in (t1,t2):
            if x in (CLONE_INFO,SERIAL_INFO):
                return x
        t1 = _decToObjArray(t1)
        t2 = _decToObjArray(t2)

        if t1.dim > t2.dim:
            t1, t2 = t2, t1

        if t1.dim == t2.dim:
            res = mergeTypes(env, _arrbase(t1), _arrbase(t2), forAssignment)
            return res if res == T_INVALID else _makeinfo('.obj', t1.dim, res.extra)
        else: #t1.dim < t2.dim
            return t1 if _arrbase(t1) in (CLONE_INFO,SERIAL_INFO) else T_ARRAY(OBJECT_INFO, t1.dim)
    else: #neither is array 
        if 'INTERFACE' in env.getFlags(t2.extra):
            return t2 if forAssignment else OBJECT_INFO

        hierarchy1 = env.getSupers(t1.extra)
        hierarchy2 = env.getSupers(t2.extra)
        matches = [x for x,y in zip(hierarchy1,hierarchy2) if x==y]
        assert(matches[0] == 'java/lang/Object') #internal assertion
        return T_OBJECT(matches[-1])        

def isAssignable(env, t1, t2):
    return mergeTypes(env, t1, t2, True) == t2

#Make verifier types printable for easy debugging
def vt_toStr(self):
    if self == T_INVALID:
        return '.none'
    elif self == T_NULL:
        return '.null'
    if self.tag == '.obj':
        base = self.extra
    elif self.extra is not None:
        base = '{}<{}>'.format(self.tag, self.extra)
    else:
        base = self.tag
    return base + '[]'*self.dim
fullinfo_t.__str__ = fullinfo_t.__repr__ = vt_toStr
########NEW FILE########
__FILENAME__ = runtests
'''Script for testing the decompiler.

On the first run tests/*.test files will be created with expected results for each test.

To generate a test's result file, run with `--create-only`.
To add a new test, add the relevant classfile and an entry in tests.registry.
'''
import os, shutil, tempfile
import subprocess
import cPickle as pickle
import optparse

import decompile
import tests

# Note: If this script is moved, be sure to update this path.
krakatau_root = os.path.dirname(os.path.abspath(__file__))
test_location = os.path.join(krakatau_root, 'tests')
class_location = os.path.join(test_location, 'classes')

def execute(args, cwd):
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    return process.communicate()

def createTest(target):
    print 'Generating {}.test'.format(target)
    results = [execute(['java', target] + arg_list, cwd=class_location)
               for arg_list in tests.registry[target]]
    testfile = os.path.join(test_location, target) + '.test'
    with open(testfile, 'wb') as f:
        pickle.dump(results, f, -1)
    return results

def loadTest(name):
    with open(os.path.join(test_location, name) + '.test', 'rb') as f:
        return pickle.load(f)

def performTest(target, expected_results, tempbase=tempfile.gettempdir()):
    temppath = os.path.join(tempbase, target)

    cpath = [decompile.findJRE(), class_location]
    if None in cpath:
        raise RuntimeError('Unable to locate rt.jar')

    # Clear any pre-existing files and create directory if necessary
    # try:
    #     shutil.rmtree(temppath)
    # except OSError as e:
    #     print e
    try:
        os.mkdir(temppath)
    except OSError as e:
        print e
    assert(os.path.isdir(temppath))

    decompile.decompileClass(cpath, targets=[target], outpath=temppath)
    # out, err = execute(['java',  '-jar', 'procyon-decompiler-0.5.24.jar', os.path.join(class_location, target+'.class')], '.')
    # if err:
    #     print 'Decompile errors:', err
    #     return False
    # with open(os.path.join(temppath, target+'.java'), 'wb') as f:
    #     f.write(out)

    print 'Attempting to compile'
    _, stderr = execute(['javac', target+'.java', '-g:none'], cwd=temppath)
    if stderr:
        print 'Compile failed:'
        print stderr
        return False

    cases = tests.registry[target]
    for args, expected in zip(cases, expected_results):
        print 'Executing {} w/ args {}'.format(target, args)
        result = execute(['java', target] + list(args), cwd=temppath)
        if result != expected:
            print 'Failed test {} w/ args {}:'.format(target, args)
            if result[0] != expected[0]:
                print '  expected stdout:', repr(expected[0])
                print '  actual stdout  :', repr(result[0])
            if result[1] != expected[1]:
                print '  expected stderr:', repr(expected[1])
                print '  actual stderr  :', repr(result[1])
            return False
    return True

if __name__ == '__main__':
    op = optparse.OptionParser(usage='Usage: %prog [options] [testfile(s)]',
                               description=__doc__)
    op.add_option('-c', '--create-only', action='store_true',
                  help='Generate cache of expected results')
    opts, args = op.parse_args()

    # Set up the tests list.
    targets = args if args else sorted(tests.registry)

    results = {}
    for test in targets:
        print 'Doing test {}...'.format(test)
        try:
            expected_results = loadTest(test)
        except IOError:
            expected_results = createTest(test)

        if not opts.create_only:
            results[test] = performTest(test, expected_results)

    print '\nTest results:'
    for test in targets:
        print '  {}: {}'.format(test, 'Pass' if results[test] else 'Fail')
    print '{}/{} tests passed'.format(sum(results.itervalues()), len(results))
########NEW FILE########
