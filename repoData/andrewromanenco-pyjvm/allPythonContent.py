__FILENAME__ = java
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""pyjvm starting point

Run as 'python java.py -h' to get help info.
Most common use case:
    python java.py -cp CLASSPATH main.class.Name

JAVA_HOME must be set (in case you have jdk7 at you computer) or run
get_rt.py in rt folder to download dependencies.

See README.md for details
"""

import argparse
import logging
import os
import pickle

from pyjvm.class_path import read_class_path
from pyjvm.jvmo import JArray
from pyjvm.vm import vm_factory

SERIALIZATION_ID = 2  # inc for each VM init process update

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(
    prog='python pvm.py',
    description='Java Virtual Machine implemented in pure python')
parser.add_argument('-cp', nargs=1, default='.',
                    help='class path, jars and folders separated by semicolon')
parser.add_argument('-novmcache', dest='no_vm_cache',
                    action='store_const', const=True, default=False,
                    help='do not use vm caching(longer init time)')
parser.add_argument('clazz', nargs=1,
                    help='main class, e.g. some.package.MyClass')
parser.add_argument('param', nargs='*', help='argument for class')
program_args = parser.parse_args()


def main(args):
    '''Init VM and run requested java application'''
    logging.basicConfig(filename='pyjvm.log', filemode='w',
                        level=logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    main_class = args.clazz[0]
    class_path = args.cp[0]
    params = args.param
    use_vm_cache = not args.no_vm_cache

    vm = None
    if use_vm_cache:
        vm = load_cached_vm(SERIALIZATION_ID)
    if vm is None:
        vm = vm_factory(class_path)
        vm.serialization_id = SERIALIZATION_ID
        if use_vm_cache:
            cache_vm(vm)
    else:
        vm.class_path = read_class_path(class_path)

    # lookup starter class & main method
    class_name = main_class.replace(".", "/")
    logger.debug("Starting with class %s", str(class_name))
    java_class = vm.get_class(class_name)
    main_method = java_class.find_method("main", "([Ljava/lang/String;)V")

    if main_method is None:
        raise Exception("main method not found")

    logger.debug("Executing main")

    # create array of strings from command line parameters
    m_args = [''] * main_method[1]
    c_args = []
    for param in params:
        ref = vm.make_heap_string(param)
        c_args.append(ref)

    heap_array = ("refarr", "java/lang/String", c_args)
    ref_arr = vm.add_to_heap(heap_array)

    array_class = vm.get_class("[Ljava/lang/String;")
    heap_item = JArray(array_class, vm)
    heap_item.values = c_args
    ref = vm.add_to_heap(heap_item)
    m_args[0] = ref

    # run main
    vm.run_vm(java_class, main_method, m_args)

    logger.debug("*** VM DONE ***")


def load_cached_vm(serialization_id):
    '''Load from serialized file'''
    path = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(path, "vm-cache.bin")
    if os.path.isfile(path):
        cache_file = open(path, "r")
        vm = pickle.load(cache_file)
        cache_file.close()
        if hasattr(vm, 'serialization_id'):
            if vm.serialization_id == serialization_id:
                logger.debug("VM is loaded from cache")
                return vm
            else:
                logger.debug("Cached vm has different sid: %i",
                             vm.serialization_id)
        else:
            logger.debug("Cached vm has no sid")
    else:
        logger.debug("No cached vm file found")
    return None


def cache_vm(vm):
    '''Serialize vm to speed up startup time'''
    try:
        path = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(path, "vm-cache.bin")
        cache_file = open(path, "w")
        pickle.dump(vm, cache_file)
        cache_file.close()
        logger.debug("VM cached with %i", vm.serialization_id)
    except Exception as exc:
        logger.error("Error caching vm: %s", str(exc))

if __name__ == '__main__':
    main(program_args)

########NEW FILE########
__FILENAME__ = bytecode
BYTECODE = {}


def bytecode(code):
    def cl(func):
        BYTECODE[hex(code)] = func
        return func

    return cl


def get_operation(code):
    return BYTECODE.get(code)


def get_operation_name(code):
    if code in BYTECODE:
        return BYTECODE[code].__name__
    return ""

########NEW FILE########
__FILENAME__ = checkcast
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Major definitions for classes and instances"""

from pyjvm.prim import PRIMITIVES


def checkcast(s, t, vm):
    '''Check if a is instance of b
    both are classes from vm.get_class(...) - JavaClass
    '''
    if s.is_array:
        if t.is_array:
            s_name = s.this_name
            assert s_name[0] == '['
            t_name = t.this_name
            assert t_name[0] == '['
            s_name = s_name[1:]
            t_name = t_name[1:]
            if s_name[0] == 'L':
                s_name = s_name[1:-1]
            else:
                s_name = PRIMITIVES[s_name]
            if t_name[0] == 'L':
                t_name = t_name[1:-1]
            else:
                t_name = PRIMITIVES[t_name]
            sc = vm.get_class(s_name)
            tc = vm.get_class(t_name)
            if sc.is_primitive and tc.is_primitive:
                if sc == tc:
                    return True
                else:
                    return False
            return checkcast(sc, tc, vm)
        elif t.is_interface:
            for i in s.interfaces:
                if i == t.this_name:
                    return True
            return False
        else:
            if t.this_name == 'java/lang/Object':
                return True
            else:
                return False
    if s.is_interface:
        if t.is_interface:
            while s is not None:
                if t == s:
                    return True
                s = s.super_class
            return False
        if t.this_name == 'java/lang/Object':
            return True
        else:
            return False
    # S is object class
    if t.is_interface:
        while s is not None:
            for i in s.interfaces:
                i_c = vm.get_class(i)
                while i_c is not None:
                    if t == i_c:
                        return True
                    assert len(i_c.interfaces) < 2
                    if len(i_c.interfaces) == 1:
                        i_c = vm.get_class(i_c.interfaces[0])
                    else:
                        i_c = None
            s = s.super_class
        return False
    while s is not None:
        if t == s:
            return True
        s = s.super_class
    return False

########NEW FILE########
__FILENAME__ = class_loader
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Class loader. Binary to python representation'''

import logging
import os
import struct
import zipfile

from pyjvm.jvmo import JavaClass

logger = logging.getLogger(__name__)


def class_loader(class_name, (lookup_paths, jars, rt)):
    '''Get JavaClass from class file.
    Order of lookup: rt.jar, other jars from class path, folders
    from class path
    '''
    logger.debug("Loading class {0}".format(class_name))
    assert class_name[0] != '['  # no arrays
    file_path = class_name + ".class"
    f = None
    zip_file = None
    if file_path in rt:
        path = rt[file_path]
        zip_file = zipfile.ZipFile(path, "r")
        f = zip_file.open(file_path)
        logger.debug("Loading %s from %s", file_path, path)
    elif file_path in jars:
        path = jars[file_path]
        zip_file = zipfile.ZipFile(path, "r")
        f = zip_file.open(file_path)
        logger.debug("Loading %s from %s", file_path, path)
    else:
        for directory in lookup_paths:
            path = os.path.join(directory, file_path)
            if os.path.exists(path) and not os.path.isdir(path):
                f = open(path, "rb")
                break
            logger.debug("Loading from file %s", path)
    if f is None:
        raise Exception("Class not found " + class_name)

    # file discovered, read step by step
    try:
        cafebabe(f)
        jdk7(f)
        constant_pool = read_constant_pool(f)
        class_flags = access_flags(f)
        (this_name, super_name) = this_super(f)
        all_interfaces = interfaces(f)
        all_fields = fields(f)
        all_methods = methods(f)
    except Exception:
        raise
    finally:
        if zip_file is not None:
            zip_file.close()
        f.close()
    return make_class(this_name, super_name, constant_pool, all_fields,
                      all_methods, all_interfaces, class_flags)


# EXACTLY THE SAME RESULTS COME FROM PYTHON's struct MODULE
# Here both approaches are used to make real reading process cleaner

def getU1(f):
    '''Single byte'''
    byte1 = f.read(1)
    return ord(byte1)


def getU2(f):
    '''Two bytes'''
    byte1 = f.read(1)
    byte2 = f.read(1)
    return (ord(byte1) << 8) + ord(byte2)


def getU4(f):
    '''4 bytes'''
    byte1 = f.read(1)
    byte2 = f.read(1)
    byte3 = f.read(1)
    byte4 = f.read(1)
    return (ord(byte1) << 24) + (ord(byte2) << 16) + (ord(byte3) << 8) \
        + ord(byte4)


def getUV(f, length):
    '''variable length'''
    data = f.read(length)
    return data


def cafebabe(f):
    '''Make sure this is java'''
    cb = [0xCA, 0xFE, 0xBA, 0xBE]
    index = 0
    while index < 4:
        byte = getU1(f)
        if byte != cb[index]:
            raise Exception("No CAFEBABE")
        index += 1


def jdk7(f):
    '''Make sure this is java 7 class'''
    getU2(f)
    major = getU2(f)
    if major != 0x33:  # 52 - jdk7
        raise Exception("Not a jdk7 class")


def read_constant_pool(f):
    '''Constant pools starts with index 1'''
    pool = ["ZERO"]
    cp_size = getU2(f)
    count = 1
    while count < cp_size:
        cp_type = getU1(f)
        if cp_type == 10:  # CONSTANT_Methodref
            pool.append([10, getU2(f), getU2(f)])
        elif cp_type == 11:  # CONSTANT_InterfaceMethodref
            pool.append([11, getU2(f), getU2(f)])
        elif cp_type == 9:  # CONSTANT_Fieldref
            pool.append([9, getU2(f), getU2(f)])
        elif cp_type == 8:  # CONSTANT_String
            pool.append([8, getU2(f)])
        elif cp_type == 7:  # CONSTANT_Class
            pool.append([7, getU2(f)])
        elif cp_type == 6:  # CONSTANT_Double
            value = struct.unpack('>d', f.read(8))[0]
            pool.append([6, value])
            count += 1  # double space in cp
            pool.append("EMPTY_SPOT")
        elif cp_type == 1:  # CONSTANT_Utf8
            length = getU2(f)
            data = getUV(f, length)
            value = unicode("")
            index = 0
            while index < length:
                c = struct.unpack(">B", data[index])[0]
                if (c >> 7) == 0:
                    value += unichr(c)
                    index += 1
                elif (c >> 5) == 0b110:
                    b = ord(data[index + 1])
                    assert b & 0x80
                    c = ((c & 0x1f) << 6) + (b & 0x3f)
                    value += unichr(c)
                    index += 2
                elif (c >> 4) == 0b1110:
                    y = ord(data[index + 1])
                    z = ord(data[index + 2])
                    c = ((c & 0xf) << 12) + ((y & 0x3f) << 6) + (z & 0x3f)
                    value += unichr(c)
                    index += 3
                elif c == 0b11101101:
                    v = ord(data[index + 1])
                    w = ord(data[index + 2])
                    # x = ord(data[index + 3]) No need this is marker
                    y = ord(data[index + 4])
                    z = ord(data[index + 5])
                    c = 0x10000 + ((v & 0x0f) << 16) + ((w & 0x3f) << 10) \
                        + ((y & 0x0f) << 6) + (z & 0x3f)
                    value += unichr(c)
                    index += 6
                else:
                    raise Exception("UTF8 is not fully implemented {0:b}"
                                    .format(c))
            pool.append([1, value])
        elif cp_type == 4:  # CONSTANT_Float
            value = struct.unpack('>f', f.read(4))[0]
            pool.append([4, value])
        elif cp_type == 12:  # CONSTANT_NameAndType
            pool.append([12, getU2(f), getU2(f)])
        elif cp_type == 3:  # CONSTANT_Int
            data = f.read(4)
            value = struct.unpack('>i', data)[0]
            # pool.append([3, getU4(f)])
            pool.append([3, value])
        elif cp_type == 5:  # CONSTANT_Long
            value = struct.unpack('>q', f.read(8))[0]
            pool.append([5, value])
            count += 1  # double space in cp
            pool.append("EMPTY_SPOT")
        else:
            raise Exception("Not implemented constant pool entry tag: %s",
                            str(cp_type))
        count += 1
    return pool


def access_flags(f):
    '''Read flags'''
    flags = getU2(f)
    return flags


def this_super(f):
    '''Constant pool indexes for this/super names.
    Resolve later to unicode/class
    '''
    this_name = getU2(f)
    super_class = getU2(f)
    return (this_name, super_class)


def interfaces(f):
    '''Not really used at runtime, other than casts'''
    data = []
    int_count = getU2(f)
    for i in range(int_count):
        index = getU2(f)
        data.append(index)
    return data


def fields(f):
    '''Read all fields from .class'''
    fields_count = getU2(f)
    data = []
    for i in range(fields_count):
        flags = access_flags(f)
        name = getU2(f)
        desc = getU2(f)
        attributes_count = getU2(f)
        attrs = []
        for k in range(attributes_count):
            attr_name = getU2(f)
            attr_len = getU4(f)
            attr_data = getUV(f, attr_len)
            attrs.append((attr_name, attr_data))
        # flags, name and description, attrs
        data.append((flags, name, desc, attrs))
    return data


def methods(f):
    '''Read all methods from .class'''
    methods_count = getU2(f)
    data = []
    for i in range(methods_count):
        flag = getU2(f)
        name = getU2(f)
        desc = getU2(f)
        attr_count = getU2(f)
        attrs = []
        for k in range(attr_count):
            attr_name = getU2(f)
            attr_len = getU4(f)
            attr_data = getUV(f, attr_len)
            attrs.append((attr_name, attr_data))
        data.append((flag, name, desc, attrs))
    return data


def make_class(this_name, super_name, constant_pool, all_fields, all_methods,
               all_interfaces, class_flags):
    '''Actually construct java class from data read earlier'''
    jc = JavaClass()
    jc.flags = class_flags
    if class_flags & 0x0200:  # is interface
        jc.is_interface = True
    jc.constant_pool = constant_pool
    jc.this_name = resolve_to_string(constant_pool, this_name)
    if super_name != 0:
        jc.super_class = resolve_to_string(constant_pool, super_name)
    add_fields(jc, constant_pool, all_fields)
    add_methods(jc, constant_pool, all_methods)
    add_interfaces(jc, constant_pool, all_interfaces)
    return jc


def resolve_to_string(constant_pool, index):
    '''Unicode string for constant pool entry'''
    data = constant_pool[index]
    if data[0] == 1:
        return unicode(data[1])
    elif data[0] == 7:
        return resolve_to_string(constant_pool, data[1])
    elif data[0] == 12:
        return resolve_to_string(constant_pool, data[1])
    else:
        raise Exception("Not supported string resolution step: {0}".
                        format(data[0]))


def add_fields(jc, constant_pool, data):  # list of (flag, name, desc)
    '''Both static and instance fields'''
    for field in data:
        static = True if field[0] & 0x0008 > 0 else False
        name = resolve_to_string(constant_pool, field[1])
        desc = resolve_to_string(constant_pool, field[2])
        if static:
            default_value = default_for_type(desc)
            jc.static_fields[name] = [desc, default_value]
        else:
            jc.member_fields[name] = desc


def default_for_type(desc):
    '''Default values for primiteves and refs'''
    if desc == "I":
        return 0
    elif desc == "J":  # long
        return ("long", 0)
    elif desc[0] == "[":  # array
        return None
    elif desc[0] == 'L':  # object
        return None
    elif desc == 'Z':  # boolean
        return 0
    elif desc == 'D':  # double
        return ('double', 0.0)
    elif desc == 'F':  # float
        return ('float', 0.0)
    elif desc == 'C':  # float
        return 0
    elif desc == 'B':  # byte
        return 0
    elif desc == 'S':  # short
        return 0
    raise Exception("Default value not yet supported for " + str(desc))


def parse_code(code, constant_pool):
    '''Each non abstract/native method has this struc'''
    nargs = (ord(code[2]) << 8) + ord(code[3])
    code_len = (ord(code[4]) << 24) + (ord(code[5]) << 16) + \
        (ord(code[6]) << 8) + ord(code[7])
    ex_len = (ord(code[8 + code_len]) << 8) + ord(code[8 + code_len + 1])
    ex_base = 8 + code_len + 2
    extable = []
    for i in range(ex_len):
        data = code[ex_base + i*8:ex_base + i*8 + 8]
        start_pc = struct.unpack('>H', data[0:2])[0]
        end_pc = struct.unpack('>H', data[2:4])[0]
        handler_pc = struct.unpack('>H', data[4:6])[0]
        catch_type = struct.unpack('>H', data[6:8])[0]
        type_name = None
        if catch_type > 0:
            cp_item = constant_pool[catch_type]
            assert cp_item[0] == 7
            type_name = constant_pool[cp_item[1]][1]
        e = (start_pc, end_pc, handler_pc, catch_type, type_name)
        extable.append(e)
    return (code[8:8+code_len], nargs, extable)


def parse_exceptions(data, constant_pool):
    '''See jvm 7 spec for details'''
    count = (ord(data[0]) << 8) + ord(data[1])
    exceptions = []
    for i in range(count):
        index = struct.unpack('>H', data[i*2 + 2:i*2+4])[0]
        cp_item = constant_pool[index]
        assert cp_item[0] == 7
        ex = constant_pool[cp_item[1]][1]
        exceptions.append(ex)
    return exceptions


def add_methods(jc, constant_pool, data):
    '''Add methods information'''
    # data is a list list of flag, name, desc, attrs; attr list of name/data
    for method in data:
        flags = method[0]
        name = resolve_to_string(constant_pool, method[1])
        desc = resolve_to_string(constant_pool, method[2])
        code = None
        exceptions = []
        for attr in method[3]:
            attr_name = resolve_to_string(constant_pool, attr[0])
            if attr_name == "Code":
                code = attr[1]
            elif attr_name == "Exceptions":
                exception = parse_exceptions(attr[1], constant_pool)
                # ignore
            elif attr_name in ("Signature", "Deprecated",
                               "RuntimeVisibleAnnotations"):
                pass
            else:
                raise Exception("Unsupported attr {0} in {1}".format(attr_name,
                                name))
        if code is None and (flags & (0x0100 + 0x0400)) == 0:
            raise Exception("No code attr in {0}".format(name))
        if name not in jc.methods:
            jc.methods[name] = {}
        m = jc.methods[name]
        if code is not None:
            code = parse_code(code, constant_pool)
        else:
            code = ("<NATIVE>", 0, [])
        m[desc] = (flags, code[1], code[0], code[2], exceptions)


def add_interfaces(jc, constant_pool, all_interfaces):
    for i in all_interfaces:
        name = resolve_to_string(constant_pool, i)
        jc.interfaces.append(name)

########NEW FILE########
__FILENAME__ = class_path
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Class path for jar files and directories. Cache all jars content.
JAVA_HOME must be set.

Class path is list of jar files and folders for classes lookup.
Separator ":", (";", ",") are also supported

See START.txt for details
'''

import os
import zipfile


def read_class_path(class_path):
    '''Cache content of all jars.
    Begin with rt.jar
    '''

    # folders for lookup for class files
    lookup_paths = []
    # content of all jars (name->path to jar)
    jars = {}
    # content of rt.jar
    rt = {}

    # first check local rt.jar
    local_path = os.path.dirname(os.path.realpath(__file__))
    RT_JAR = os.path.join(local_path, "../rt/rt.jar")
    if not os.path.isfile(RT_JAR):
        JAVA_HOME = os.environ.get('JAVA_HOME')
        if JAVA_HOME is None:
            raise Exception("JAVA_HOME is not set")
        if not os.path.isdir(JAVA_HOME):
            raise Exception("JAVA_HOME must be a folder: %s" % JAVA_HOME)

        RT_JAR = os.path.join(JAVA_HOME, "lib/rt.jar")
        if not os.path.exists(RT_JAR) or os.path.isdir(RT_JAR):
            RT_JAR = os.path.join(JAVA_HOME, "jre/lib/rt.jar")
            if not os.path.exists(RT_JAR) or os.path.isdir(RT_JAR):
                raise Exception("rt.jar not found")

    if not zipfile.is_zipfile(RT_JAR):
        raise Exception("rt.jar is not a zip: %s" % RT_JAR)

    read_from_jar(RT_JAR, rt)

    current = os.getcwd()

    splitter = None
    if ":" in class_path:
        splitter = ":"
    elif ";" in class_path:
        splitter = ";"
    elif "," in class_path:
        splitter = ","
    else:
        splitter = ":"
    cpaths = class_path.split(splitter)
    for p in cpaths:
        p = p.strip()
        path = os.path.join(current, p)
        if not os.path.exists(path):
            raise Exception("Wrong class path entry: %s (path not found %s)",
                            p, path)
        if os.path.isdir(path):
            lookup_paths.append(path)
        else:
            if zipfile.is_zipfile(path):
                read_from_jar(path, jars)
            else:
                raise Exception("Class path entry %s is not a jar file" % path)

    return (lookup_paths, jars, rt)


def read_from_jar(jar, dict_data):
    '''Read file list from a jar'''
    if not zipfile.is_zipfile(jar):
        raise Exception("Not a jar file: %s" % jar)
    with zipfile.ZipFile(jar, "r") as j:
        for name in j.namelist():
            if name.endswith(".class"):  # at some point save all files
                dict_data[name] = jar

########NEW FILE########
__FILENAME__ = frame
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Major execution component.

Created for every method execution and placed to thread's stack
'''

f_counter = 1  # make it easy to debug


class Frame(object):
    '''Frame is created for every method invokation'''

    def __init__(self, _thread, _this_class, _method, _args=[], _desc=""):
        self.thread = _thread
        if _thread is not None:
            self.vm = _thread.vm
        self.this_class = _this_class
        self.pc = 0  # Always points to byte code to be executed
        self.method = _method
        self.code = _method[2]  # method body (bytecode)
        self.stack = []
        self.args = _args
        self.ret = None  # return value for non void
        self.has_result = False  # flag if return value is set
        self.desc = _desc
        global f_counter
        self.id = f_counter
        # to support multithreaded environment
        self.cpc = 0
        self.monitor = None
        f_counter += 1

########NEW FILE########
__FILENAME__ = jassert
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java related asserts'''

from pyjvm.jvmo import JArray


def jassert_float(value):
    assert type(value) is tuple and value[0] == "float"


def jassert_double(value):
    assert type(value) is tuple and value[0] == "double"


def jassert_int(value):
    assert type(value) is int or type(value) is long
    assert -2147483648 <= value <= 2147483647


def jassert_long(value):
    assert type(value) is tuple and value[0] == "long"
    assert -9223372036854775808 <= value[1] <= 9223372036854775807


def jassert_ref(ref):
    assert ref is None or (type(ref) is tuple and ref[0] in ("ref", "vm_ref"))


def jassert_array(array):
    assert array is None or isinstance(array, JArray)

########NEW FILE########
__FILENAME__ = jvmo
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Major definitions for classes and instances"""

import logging

from pyjvm.prim import PRIMITIVES
from pyjvm.utils import default_for_type

logger = logging.getLogger(__name__)


class JavaClass(object):
    '''Java class representation inside python.
    Is loaded from .class by class loader
    '''

    def __init__(self):
        '''Init major components.
        See models.txt in docs.
        '''
        self.constant_pool = []
        # each field is name -> (desc, value)
        self.static_fields = {}
        # each field is name -> desc
        self.member_fields = {}
        self.methods = {}  # name-> desc-> (flags, nargs, code)
        self.interfaces = []  # names

        self.this_name = None
        self.super_class = None
        self.flags = 0
        self.is_interface = False
        self.is_primitive = False
        self.is_array = False

        # Reference to java.lang.Class
        self.heap_ref = None

    def print_constant_pool(self):
        '''Debug only purpose'''
        index = 0
        for record in self.constant_pool:
            print str(index) + ":\t" + str(record)
            index += 1

    def static_contructor(self):
        '''Find static constructor among class methods'''
        if "<clinit>" in self.methods:
            return self.methods["<clinit>"]["()V"]
        return None

    def find_method(self, name, signature):
        '''Find method by name and signature in current class or super'''
        if name in self.methods:
            if signature in self.methods[name]:
                return self.methods[name][signature]
        if self.super_class is not None:
            return self.super_class.find_method(name, signature)
        return None

    def get_instance(self, vm):
        '''Make class instance to be used in java heap'''
        logger.debug("Creating instance of " + str(self.this_name))
        return JavaObject(self, vm)

    def __str__(self):
        s = "JavaClass: "
        s += str(self.this_name) + "\n"
        if self.super_class is None:
            pass
        elif type(self.super_class) is unicode:
            s += "Super: *" + self.super_class + "\n"
        else:
            s += "Super: " + self.super_class.this_name + "\n"
        s += "Static fields: "
        for k in self.static_fields:
            s += "{0}{1} ".format(k, self.static_fields[k])
        s += "\n"
        s += "Member fields: "
        for k in self.member_fields:
            s += "{0}:{1} ".format(k, self.member_fields[k])
        s += "\n"
        s += "Methods:\n"
        for k in self.methods:
            s += "\t" + k + ": "
            for t in self.methods[k]:
                s += t + "::" + str(self.methods[k][t][1]) + ", "
            s += "\n"
        return s


class JavaObject(object):
    '''Java class instance.
    Piece of memory with all instance fields.
    Is created in heap.
    '''

    def __init__(self, jc, vm):
        self.java_class = jc
        self.fields = {}
        self.fill_fields(jc, vm)
        self.waiting_list = []  # wait/notify/notifyall

    def fill_fields(self, jc, vm):
        '''Init all fields with default values'''
        if jc is None:
            return
        for name in jc.member_fields:
            tp = jc.member_fields[name]
            if tp[0] == 'L':
                #vm.get_class(tp[1:-1])
                pass
            self.fields[name] = default_for_type(jc.member_fields[name])
        self.fill_fields(jc.super_class, vm)

    def __str__(self):
        return "Instance of {0}: {1}".format(self.java_class.this_name,
                                             self.fields)

    def __repr__(self):
        return self.__str__()


class JArray(object):
    '''Java array

    Lives in heap and has corresponding java_class
    '''
    def __init__(self, jc, vm):
        self.java_class = jc
        self.fields = {}
        self.values = []


def array_class_factory(vm, name):
    assert name[0] == '['
    name = name[1:]
    if name[0] == 'L':
        name = name[1:-1]
        vm.get_class(name)  # make sure it's in
        jc = JavaClass()
        jc.is_array = True
        jc.this_name = "[L" + name + ";"
        jc.super_class = vm.get_class("java/lang/Object")
        jc.interfaces = ["java/lang/Cloneable", "java/io/Serializable"]
        return jc
    if name[0] == '[':
        jc = JavaClass()
        jc.is_array = True
        jc.this_name = "[" + name
        jc.super_class = vm.get_class("java/lang/Object")
        jc.interfaces = ["java/lang/Cloneable", "java/io/Serializable"]
        return jc
    assert name in PRIMITIVES

    vm.get_class(PRIMITIVES[name])  # make sure class is in

    jc = JavaClass()
    jc.is_array = True
    jc.interfaces = ["java/lang/Cloneable", "java/io/Serializable"]
    jc.this_name = "[" + name
    jc.super_class = vm.get_class("java/lang/Object")
    return jc

########NEW FILE########
__FILENAME__ = natives
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Natives methods handler '''

import logging

from pyjvm.platform.java.lang.clazz import *
from pyjvm.platform.java.lang.double import *
from pyjvm.platform.java.lang.float import *
from pyjvm.platform.java.lang.object import *
from pyjvm.platform.java.lang.runtime import *
from pyjvm.platform.java.lang.string import *
from pyjvm.platform.java.lang.system import *
from pyjvm.platform.java.lang.thread import *
from pyjvm.platform.java.lang.throwable import *
from pyjvm.platform.java.io.filedescriptor import *
from pyjvm.platform.java.io.fileinputstream import *
from pyjvm.platform.java.io.fileoutputstream import *
from pyjvm.platform.java.io.filesystem import *
from pyjvm.platform.java.security.accesscontroller import *
from pyjvm.platform.sun.misc.unsafe import *
from pyjvm.platform.sun.misc.vm import *
from pyjvm.platform.sun.reflect.nativeconstructoraccessorimpl import *
from pyjvm.platform.sun.reflect.reflection import *

logger = logging.getLogger(__name__)


def exec_native(frame, args, klass, method_name, method_signature):
    '''Handle calls to java's native methods.
    Create function name from class and method names and call that
    implementation.
    See native.txt in documentation.
    '''
    if method_name == "registerNatives" and method_signature == "()V":
        logger.debug("No need to call native registerNatives()V for class: %s",
                     klass.this_name)
        return
    lookup_name = "%s_%s_%s" % (klass.this_name, method_name, method_signature)
    lookup_name = lookup_name.replace("/", "_")
    lookup_name = lookup_name.replace("(", "_")
    lookup_name = lookup_name.replace(")", "_")
    lookup_name = lookup_name.replace("[", "_")
    lookup_name = lookup_name.replace(";", "_")
    lookup_name = lookup_name.replace(".", "_")
    if lookup_name not in globals():
        logger.error("Native not yet ready: %s:%s in %s", method_name,
                     method_signature, klass.this_name)
        raise Exception("Op ({0}) is not yet supported in natives".format(
                        lookup_name))
    logger.debug("Call native: %s", lookup_name)
    globals()[lookup_name](frame, args)

########NEW FILE########
__FILENAME__ = ops_arrays
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import logging

from pyjvm.bytecode import bytecode
from pyjvm.jassert import jassert_array
from pyjvm.jassert import jassert_float
from pyjvm.jassert import jassert_double
from pyjvm.jassert import jassert_int
from pyjvm.jassert import jassert_long
from pyjvm.jassert import jassert_ref
from pyjvm.jvmo import JArray

logger = logging.getLogger(__name__)


@bytecode(code=0x2e)
def iaload(frame):
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    frame.stack.append(values[index])


@bytecode(code=0x2f)
def laload(frame):
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    frame.stack.append(values[index])


@bytecode(code=0x30)
def faload(frame):
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    frame.stack.append(values[index])


@bytecode(code=0x31)
def daload(frame):
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    frame.stack.append(values[index])


@bytecode(code=0x32)
def aaload(frame):
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    frame.stack.append(values[index])


@bytecode(code=0x33)
def baload(frame):
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    frame.stack.append(values[index])


@bytecode(code=0x34)
def caload(frame):
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    frame.stack.append(values[index])


@bytecode(code=0x35)
def saload(frame):
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    frame.stack.append(values[index])


@bytecode(code=0x4f)
def iastore(frame):
    value = frame.stack.pop()
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_int(value)
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    values[index] = value


@bytecode(code=0x50)
def lastore(frame):
    value = frame.stack.pop()
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_long(value)
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    values[index] = value


@bytecode(code=0x51)
def fastore(frame):
    value = frame.stack.pop()
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_float(value)
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    values[index] = value


@bytecode(code=0x52)
def dastore(frame):
    value = frame.stack.pop()
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_double(value)
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    values[index] = value


@bytecode(code=0x53)
def aastore(frame):
    # TODO ArrayStoreException
    value = frame.stack.pop()
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_ref(value)
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    values[index] = value


@bytecode(code=0x54)
def bastore(frame):
    value = frame.stack.pop()
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_int(value)
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    values[index] = value


@bytecode(code=0x55)
def castore(frame):
    value = frame.stack.pop()
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_int(value)
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    values[index] = value


@bytecode(code=0x56)
def sastore(frame):
    value = frame.stack.pop()
    index = frame.stack.pop()
    ref = frame.stack.pop()
    jassert_int(value)
    jassert_int(index)
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    values = array.values
    if index < 0 or index >= len(values):
        frame.vm.raise_exception(frame,
                                 "java/lang/ArrayIndexOutOfBoundsException")
        return
    values[index] = value


@bytecode(code=0xbc)
def newarray(frame):
    atype = ord(frame.code[frame.pc])
    frame.pc += 1
    count = frame.stack.pop()
    jassert_int(count)
    if count < 0:
        frame.vm.raise_exception(frame, "java/lang/NegativeArraySizeException")
        return
    values = None
    if atype in [10, 5, 8, 9, 4]:  # int, char, byte, short, boolean
        values = [0]*count
    elif atype == 7:  # double
        values = [("double", 0.0)] * count
    elif atype == 6:  # float
        values = [("float", 0.0)] * count
    elif atype == 11:  # long
        values = [("long", 0)] * count
    else:
        raise Exception("Array creation for ATYPE {0} not yet supported"
                        .format(atype))
    prims = {4: "[Z", 5: "[C", 6: "[F", 7: "[D", 8: "[B", 9: "[S",
             10: "[I", 11: "[J"}
    array_class = frame.vm.get_class(prims[atype])
    jarray = JArray(array_class, frame.vm)
    jarray.values = values
    ref = frame.vm.add_to_heap(jarray)
    frame.stack.append(ref)


@bytecode(code=0xbd)
def anewarray(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    cp_item = frame.this_class.constant_pool[index]
    assert cp_item[0] == 7  # CONSTANT_Class
    klass_name = frame.this_class.constant_pool[cp_item[1]][1]
    assert type(klass_name) is unicode
    frame.vm.get_class(klass_name)  # make sure it is loaded

    count = frame.stack.pop()
    jassert_int(count)
    if count < 0:
        frame.vm.raise_exception(frame, "java/lang/NegativeArraySizeException")
        return

    values = [None] * count
    array_class = frame.vm.get_class("[L" + klass_name + ";")
    jarray = JArray(array_class, frame.vm)
    jarray.values = values
    ref = frame.vm.add_to_heap(jarray)
    frame.stack.append(ref)


@bytecode(code=0xbe)
def arraylength(frame):
    ref = frame.stack.pop()
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    assert ref[0] == "ref"
    array = frame.vm.heap[ref[1]]
    jassert_array(array)
    length = len(array.values)
    frame.stack.append(length)


@bytecode(code=0xc5)
def multianewarray(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    dims = ord(frame.code[frame.pc])
    frame.pc += 1
    if dims < 1:
        frame.vm.raise_exception(frame, "java/lang/NegativeArraySizeException")
        return

    cp_item = frame.this_class.constant_pool[index]
    if cp_item[0] != 7:
        raise Exception("This use case is not yet supported in mdim-array")
    klass_name = frame.this_class.constant_pool[cp_item[1]][1]
    while klass_name[0] == '[':
        klass_name = klass_name[1:]

    counts = []
    for i in range(dims):
        counts.insert(0, frame.stack.pop())

    def mla(counts, klass_name):
        if len(counts) == 1:
            if klass_name in ('B', 'C', 'I', 'S', 'Z'):
                default = 0
            elif klass_name == 'D':
                default = ('double', 0.0)
            elif klass_name == 'F':
                default = ('float', 0.0)
            elif klass_name == 'J':
                default = ('long', 0)
            elif klass_name[0] == 'L':
                default = None
            array_class = frame.vm.get_class('[' + klass_name)
            array = JArray(array_class, frame.vm)
            values = [default] * counts[0]
            array.values = values
            ref = frame.vm.add_to_heap(array)
            return ref
        else:
            name = '[' * len(counts)
            name += klass_name
            array_class = frame.vm.get_class(name)
            array = JArray(array_class, frame.vm)
            values = [None] * counts[0]
            for i in range(counts[0]):
                values[i] = mla(counts[1:], klass_name)
            array.values = values
            ref = frame.vm.add_to_heap(array)
            return ref

    ref = mla(counts, klass_name)
    frame.stack.append(ref)

########NEW FILE########
__FILENAME__ = ops_calc
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import logging
import struct

from pyjvm.bytecode import bytecode
from pyjvm.jassert import jassert_double
from pyjvm.jassert import jassert_float
from pyjvm.jassert import jassert_int
from pyjvm.jassert import jassert_long

logger = logging.getLogger(__name__)

FLAG32 = 1 << 31
FLAG64 = 1 << 63


def cut_to_int(value):
    if -2147483648 <= value <= 2147483647:
        return int(value)
    if value & FLAG32:
        value &= 0xFFFFFFFF
        value ^= 0xFFFFFFFF
        value += 1
        value *= -1
    else:
        value &= 0xFFFFFFFF
    jassert_int(value)
    return int(value)


def cut_to_long(value):
    if -9223372036854775808 <= value <= 9223372036854775807:
        return long(value)
    if value & FLAG64:
        value &= 0xFFFFFFFFFFFFFFFF
        value ^= 0xFFFFFFFFFFFFFFFF
        value += 1
        value *= -1
    else:
        value &= 0xFFFFFFFFFFFFFFFF
    jassert_long(("long", value))
    return long(value)


@bytecode(code=0x60)
def iadd(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    result = value1 + value2
    result = cut_to_int(result)
    jassert_int(result)
    frame.stack.append(result)


@bytecode(code=0x61)
def ladd(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    result = value1[1] + value2[1]
    result = cut_to_long(result)
    frame.stack.append(("long", result))


@bytecode(code=0x62)
def fadd(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_float(value1)
    jassert_float(value2)
    result = value1[1] + value2[1]
    frame.stack.append(("float", result))


@bytecode(code=0x63)
def dadd(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_double(value1)
    jassert_double(value2)
    result = value1[1] + value2[1]
    frame.stack.append(("double", result))


@bytecode(code=0x64)
def isub(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    result = value1 - value2
    result = cut_to_int(result)
    frame.stack.append(result)


@bytecode(code=0x65)
def lsub(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    result = value1[1] - value2[1]
    result = cut_to_long(result)
    frame.stack.append(("long", result))


@bytecode(code=0x66)
def fsub(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_float(value1)
    jassert_float(value2)
    result = value1[1] - value2[1]
    frame.stack.append(("float", result))


@bytecode(code=0x67)
def dsub(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_double(value1)
    jassert_double(value2)
    result = value1[1] - value2[1]
    frame.stack.append(("double", result))


@bytecode(code=0x68)
def imul(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    result = value1 * value2
    result = cut_to_int(result)
    frame.stack.append(result)


@bytecode(code=0x69)
def lmul(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    result = value1[1] * value2[1]
    result = cut_to_long(result)
    frame.stack.append(("long", result))


@bytecode(code=0x6a)
def fmul(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_float(value1)
    jassert_float(value2)
    result = value1[1] * value2[1]
    #result = numpy.float32(result)
    frame.stack.append(("float", result))


@bytecode(code=0x6b)
def dmul(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_double(value1)
    jassert_double(value2)
    result = value1[1] * value2[1]
    frame.stack.append(("double", result))


@bytecode(code=0x6c)
def idiv(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    if value2 == 0:
        frame.vm.raise_exception(frame, "java/lang/ArithmeticException")
        return
    result = int(float(value1) / value2)
    result = cut_to_int(result)
    frame.stack.append(result)


@bytecode(code=0x6d)
def ldiv(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_long(value1)
    jassert_long(value2)
    if value2[1] == 0:
        frame.vm.raise_exception(frame, "java/lang/ArithmeticException")
        return
    result = abs(value1[1]) / abs(value2[1])
    if (value1[1] < 0 and value2[1] > 0) or (value1[1] > 0 and value2[1] < 0):
        result *= -1
    #result = long(float(value1[1]) / value2[1]) - this will overflow
    result = cut_to_long(result)
    frame.stack.append(("long", long(result)))


@bytecode(code=0x6e)
def fdiv(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_float(value1)
    jassert_float(value2)
    if value2[1] == 0:
        frame.stack.append(("float", float("inf")))
        return
    result = value1[1] / value2[1]
    frame.stack.append(("float", result))


@bytecode(code=0x6f)
def ddiv(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_double(value1)
    jassert_double(value2)
    if value2[1] == 0:
        frame.stack.append(("double", float("inf")))
        return
    result = value1[1] / value2[1]
    frame.stack.append(("double", result))


@bytecode(code=0x70)
def irem(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    if value2 == 0:
        frame.vm.raise_exception(frame, "java/lang/ArithmeticException")
        return
    result = value1 % value2
    result = cut_to_int(result)
    frame.stack.append(result)


@bytecode(code=0x71)
def lrem(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_long(value1)
    jassert_long(value2)
    if value2[1] == 0:
        frame.vm.raise_exception(frame, "java/lang/ArithmeticException")
        return
    result = value1[1] % value2[1]
    result = cut_to_long(result)
    frame.stack.append(("long", result))


@bytecode(code=0x72)
def frem(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    frame.stack.append(0)  # hardcoded for now


@bytecode(code=0x73)
def drem(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    frame.stack.append(0)  # hardcoded for now


@bytecode(code=0x74)
def ineg(frame):
    value = frame.stack.pop()
    result = value * -1
    result = cut_to_int(result)
    frame.stack.append(result)


@bytecode(code=0x75)
def lneg(frame):
    value = frame.stack.pop()
    jassert_long(value)
    result = value[1] * -1
    result = cut_to_long(result)
    frame.stack.append(("long", long(result)))


@bytecode(code=0x76)
def fneg(frame):
    value = frame.stack.pop()
    jassert_double(value)
    result = value[1] * -1
    frame.stack.append(("float", result))


@bytecode(code=0x77)
def dneg(frame):
    value = frame.stack.pop()
    jassert_double(value)
    result = value[1] * -1
    frame.stack.append(("double", result))


@bytecode(code=0x83)
def lxor(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_long(value1)
    jassert_long(value2)
    result = value1[1] ^ value2[1]
    result = cut_to_long(result)
    frame.stack.append(("long", result))


@bytecode(code=0x84)
def iinc(frame):
    index = ord(frame.code[frame.pc])
    frame.pc += 1
    vconst = struct.unpack('b', frame.code[frame.pc])[0]
    frame.pc += 1
    result = frame.args[index] + vconst
    result = cut_to_int(result)
    frame.args[index] = result

########NEW FILE########
__FILENAME__ = ops_cond
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import struct

from pyjvm.bytecode import bytecode
from pyjvm.checkcast import checkcast
from pyjvm.jassert import jassert_float
from pyjvm.jassert import jassert_double
from pyjvm.jassert import jassert_int
from pyjvm.jassert import jassert_long
from pyjvm.jassert import jassert_ref
from pyjvm.jvmo import JavaObject
from pyjvm.vmo import vmo_check_cast, VM_CLASS_NAMES


@bytecode(code=0x94)
def lcmpl(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_long(value1)
    jassert_long(value2)
    if value1[1] > value2[1]:
        frame.stack.append(1)
    elif value1[1] == value2[1]:
        frame.stack.append(0)
    else:
        frame.stack.append(-1)


@bytecode(code=0x95)
def fcmpl(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_float(value1)
    jassert_float(value2)
    if value1[1] > value2[1]:
        frame.stack.append(1)
    elif value1 == value2:
        frame.stack.append(0)
    else:
        frame.stack.append(-1)


@bytecode(code=0x96)
def fcmpg(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_float(value1)
    jassert_float(value2)
    if value1[1] > value2[1]:
        frame.stack.append(1)
    elif value1 == value2:
        frame.stack.append(0)
    else:
        frame.stack.append(-1)


@bytecode(code=0x97)
def dcmpl(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_double(value1)
    jassert_double(value2)
    if value1[1] > value2[1]:
        frame.stack.append(1)
    elif value1 == value2:
        frame.stack.append(0)
    else:
        frame.stack.append(-1)


@bytecode(code=0x98)
def dcmpl(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_double(value1)
    jassert_double(value2)
    if value1[1] > value2[1]:
        frame.stack.append(1)
    elif value1 == value2:
        frame.stack.append(0)
    else:
        frame.stack.append(-1)


@bytecode(code=0x99)
def if_eq(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value = frame.stack.pop()
    jassert_int(value)
    if value == 0:
        frame.pc += offset - 2 - 1


@bytecode(code=0x9a)
def ifne(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value = frame.stack.pop()
    jassert_int(value)
    if value != 0:
        frame.pc += offset - 2 - 1


@bytecode(code=0x9b)
def iflt(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value = frame.stack.pop()
    jassert_int(value)
    if value < 0:
        frame.pc += offset - 2 - 1


@bytecode(code=0x9c)
def ifge(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value = frame.stack.pop()
    jassert_int(value)
    if value >= 0:
        frame.pc += offset - 2 - 1


@bytecode(code=0x9d)
def ifgt(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value = frame.stack.pop()
    jassert_int(value)
    if value > 0:
        frame.pc += offset - 2 - 1


@bytecode(code=0x9e)
def ifle(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value = frame.stack.pop()
    jassert_int(value)
    if value <= 0:
        frame.pc += offset - 2 - 1


@bytecode(code=0x9f)
def if_icmpeq(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value1)
    jassert_int(value2)
    if value1 == value2:
        frame.pc += offset - 2 - 1


@bytecode(code=0xa0)
def if_icmpne(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value1)
    jassert_int(value2)
    if value1 != value2:
        frame.pc += offset - 2 - 1


@bytecode(code=0xa1)
def if_icmplt(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value1)
    jassert_int(value2)
    if value1 < value2:
        frame.pc += offset - 2 - 1


@bytecode(code=0xa2)
def if_icmpge(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value1)
    jassert_int(value2)
    if value1 >= value2:
        frame.pc += offset - 2 - 1


@bytecode(code=0xa3)
def if_icmpgt(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value1)
    jassert_int(value2)
    if value1 > value2:
        frame.pc += offset - 2 - 1


@bytecode(code=0xa4)
def if_icmple(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value1)
    jassert_int(value2)
    if value1 <= value2:
        frame.pc += offset - 2 - 1


@bytecode(code=0xa5)
def if_acmpeq(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_ref(value1)
    jassert_ref(value2)
    if value1 == value2:
        frame.pc += offset - 2 - 1


@bytecode(code=0xa6)
def if_acmpne(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_ref(value1)
    jassert_ref(value2)
    if value1 != value2:
        frame.pc += offset - 2 - 1


@bytecode(code=0xa7)
def goto(frame):
    data = frame.code[frame.pc:frame.pc + 2]
    frame.pc += 2
    offset = struct.unpack(">h", data)[0]
    frame.pc += offset - 2 - 1


@bytecode(code=0xa8)
def jsr(frame):
    frame.stack.append(frame.pc + 2)
    data = frame.code[frame.pc:frame.pc + 2]
    frame.pc += 2
    offset = struct.unpack(">h", data)[0]
    frame.pc += offset - 2 - 1


@bytecode(code=0xaa)
def tableswitch(frame):
    index = frame.stack.pop()
    jassert_int(index)
    last_pc = frame.pc - 1
    while frame.pc % 4 != 0:
        frame.pc += 1
    default = struct.unpack(">i", frame.code[frame.pc:frame.pc + 4])[0]
    frame.pc += 4
    low = struct.unpack(">i", frame.code[frame.pc:frame.pc + 4])[0]
    frame.pc += 4
    high = struct.unpack(">i", frame.code[frame.pc:frame.pc + 4])[0]
    frame.pc += 4
    if index < low or index > high:
        frame.pc = last_pc + default
        return
    count = high - low + 1
    offsets = []
    for i in range(count):
        offsets.append(struct.unpack(">i",
                                     frame.code[frame.pc:frame.pc + 4])[0])
        frame.pc += 4
    frame.pc = last_pc + offsets[index - low]


@bytecode(code=0xab)
def lookupswitch(frame):
    key = frame.stack.pop()
    last_pc = frame.pc - 1
    while frame.pc % 4 != 0:
        frame.pc += 1
    default = struct.unpack(">i", frame.code[frame.pc:frame.pc + 4])[0]
    frame.pc += 4
    npairs = struct.unpack(">i", frame.code[frame.pc:frame.pc + 4])[0]
    frame.pc += 4
    matches = []
    offsets = []
    for i in range(npairs):
        matches.append(struct.unpack(">i",
                                     frame.code[frame.pc:frame.pc + 4])[0])
        frame.pc += 4
        offsets.append(struct.unpack(">i",
                                     frame.code[frame.pc:frame.pc + 4])[0])
        frame.pc += 4
    for i in range(len(matches)):
        if matches[i] == key:
            frame.pc = last_pc + offsets[i]
            return
    frame.pc = last_pc + default


@bytecode(code=0xc6)
def ifnull(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value = frame.stack.pop()
    jassert_ref(value)
    if value is None:
        frame.pc += offset - 2 - 1


@bytecode(code=0xc7)
def ifnonnull(frame):
    byte1 = ord(frame.code[frame.pc])
    byte2 = ord(frame.code[frame.pc + 1])
    frame.pc += 2
    offset = struct.unpack(">h", chr(byte1) + chr(byte2))[0]
    value = frame.stack.pop()
    jassert_ref(value)
    if value is not None:
        frame.pc += offset - 2 - 1


@bytecode(code=0xc0)
def checkcast_(frame):   # FIXME: rename pyjvm.checkcast and rename this func to checkcast 
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    ref = frame.stack.pop()
    if ref is None:
        frame.stack.append(ref)
        return
    cp_item = frame.this_class.constant_pool[index]
    assert cp_item[0] == 7  # CONSTANT_Class_info
    klass_name = frame.this_class.constant_pool[cp_item[1]][1]
    klass = frame.vm.get_class(klass_name)
    object_klass = None
    if ref[1] > 0:  # regular ref
        o = frame.vm.heap[ref[1]]
        object_klass = o.java_class
    else:  # vmo
        object_klass = frame.vm.get_class(VM_CLASS_NAMES[ref[1]])

    if checkcast(object_klass, klass, frame.vm):
        frame.stack.append(ref)
    else:
        frame.vm.raise_exception(frame, "java/lang/ClassCastException")


@bytecode(code=0xc1)
def instanceof(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    ref = frame.stack.pop()
    if ref is None:
        frame.stack.append(0)
        return
    cp_item = frame.this_class.constant_pool[index]
    assert cp_item[0] == 7  # CONSTANT_Class_info
    klass_name = frame.this_class.constant_pool[cp_item[1]][1]
    klass = frame.vm.get_class(klass_name)
    o = frame.vm.heap[ref[1]]
    object_klass = None
    if ref[1] > 0:  # regular ref
        o = frame.vm.heap[ref[1]]
        object_klass = o.java_class
    else:  # vmo
        object_klass = frame.vm.get_class(VM_CLASS_NAMES[ref[1]])

    if checkcast(object_klass, klass, frame.vm):
        frame.stack.append(1)
    else:
        frame.stack.append(0)


@bytecode(code=0xc8)
def goto_w(frame):
    data = frame.code[frame.pc:frame.pc + 4]
    frame.pc += 4
    offset = struct.unpack(">i", data)[0]
    frame.pc += offset - 4 - 1


@bytecode(code=0xc9)
def jsr_w(frame):
    frame.stack.append(frame.pc + 4)
    data = frame.code[frame.pc:frame.pc + 4]
    frame.pc += 4
    offset = struct.unpack(">i", data)[0]
    frame.pc += offset - 4 - 1

########NEW FILE########
__FILENAME__ = ops_convert
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import math
import struct

from pyjvm.bytecode import bytecode
from pyjvm.jassert import jassert_float
from pyjvm.jassert import jassert_double
from pyjvm.jassert import jassert_int
from pyjvm.jassert import jassert_long


@bytecode(code=0x85)
def i2l(frame):
    value = frame.stack.pop()
    jassert_int(value)
    value = long(value)  # no real need
    frame.stack.append(("long", value))


@bytecode(code=0x86)
def i2f(frame):
    value = frame.stack.pop()
    jassert_int(value)
    frame.stack.append(("float", float(value)))


@bytecode(code=0x87)
def i2d(frame):
    value = frame.stack.pop()
    jassert_int(value)
    frame.stack.append(("double", float(value)))


@bytecode(code=0x88)
def l2i(frame):
    value = frame.stack.pop()
    jassert_long(value)
    data = struct.pack(">q", value[1])
    data = data[4:]
    result = struct.unpack(">i", data)[0]
    jassert_int(result)
    frame.stack.append(result)


@bytecode(code=0x89)
def l2f(frame):
    value = frame.stack.pop()
    jassert_long(value)
    result = ("float", float(value[1]))
    frame.stack.append(result)


@bytecode(code=0x8a)
def l2d(frame):
    value = frame.stack.pop()
    jassert_long(value)
    result = ("double", float(value[1]))
    frame.stack.append(result)


@bytecode(code=0x8b)
def f2i(frame):
    value = frame.stack.pop()
    jassert_float(value)
    if value[1] is None:
        frame.stack.append(0)
    else:
        if value[1] < -2147483648:  # -1 * math.pow(2, 31)
            result = -2147483648
        elif value[1] > 2147483647:  # math.pow(2, 31) - 1
            result = 2147483647
        else:
            result = int(value[1])
        jassert_int(result)
        frame.stack.append(result)


@bytecode(code=0x8c)
def f2l(frame):
    value = frame.stack.pop()
    jassert_float(value)
    if value[1] is None:
        frame.stack.append(("long", 0))
    else:
        min_value = long(-1 * math.pow(2, 63))
        max_value = long(math.pow(2, 63) - 1)
        if value[1] < min_value:
            result = min_value
        elif value[1] > max_value:
            result = max_value
        else:
            result = long(value[1])
        jassert_long(("long", result))
        frame.stack.append(("long", result))


@bytecode(code=0x8d)
def f2d(frame):
    value = frame.stack.pop()
    jassert_float(value)
    frame.stack.append(("double", value[1]))


@bytecode(code=0x8e)
def d2i(frame):
    value = frame.stack.pop()
    jassert_double(value)
    if value[1] is None:
        frame.stack.append(0)
    else:
        if value[1] < -2147483648:  # -1 * math.pow(2, 31)
            result = -2147483648
        elif value[1] > 2147483647:  # math.pow(2, 31) - 1
            result = 2147483647
        else:
            result = int(value[1])
        jassert_int(result)
        frame.stack.append(result)


@bytecode(code=0x8f)
def d2l(frame):
    value = frame.stack.pop()
    jassert_double(value)
    if value[1] is None:
        frame.stack.append(("long", 0))
    else:
        min_value = long(-1 * math.pow(2, 63))
        max_value = long(math.pow(2, 63) - 1)
        if value[1] < min_value:
            result = min_value
        elif value[1] > max_value:
            result = max_value
        else:
            result = long(value[1])
        jassert_long(("long", result))
        frame.stack.append(("long", result))


@bytecode(code=0x90)
def d2f(frame):
    value = frame.stack.pop()
    jassert_double(value)
    frame.stack.append(("float", value[1]))


@bytecode(code=0x91)
def i2b(frame):
    value = frame.stack.pop()
    jassert_int(value)
    data = struct.pack(">i", value)
    data = data[3]
    result = struct.unpack(">b", data)[0]
    frame.stack.append(result)


@bytecode(code=0x92)
def i2c(frame):
    value = frame.stack.pop()
    jassert_int(value)
    data = struct.pack(">i", value)
    data = data[2:]
    result = struct.unpack(">H", data)[0]
    assert type(result) is int
    assert 0 <= result <= int(math.pow(2, 16))
    frame.stack.append(result)


@bytecode(code=0x93)
def i2s(frame):
    value = frame.stack.pop()
    jassert_int(value)
    data = struct.pack(">i", value)
    data = data[2:]
    result = struct.unpack(">h", data)[0]
    assert type(result) is int
    frame.stack.append(result)

########NEW FILE########
__FILENAME__ = ops_fields
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import logging

from pyjvm.bytecode import bytecode
from pyjvm.jassert import jassert_ref

logger = logging.getLogger(__name__)


@bytecode(code=0xb2)
def getstatic(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    cp_fieldref = frame.this_class.constant_pool[index]
    assert cp_fieldref[0] == 9  # CONSTANT_Fieldref
    klass_info = frame.this_class.constant_pool[cp_fieldref[1]]
    assert klass_info[0] == 7  # CONSTANT_Class_info
    name_and_type = frame.this_class.constant_pool[cp_fieldref[2]]
    assert name_and_type[0] == 12  # CONSTANT_NameAndType_info
    klass_name = frame.this_class.constant_pool[klass_info[1]][1]
    field_name = frame.this_class.constant_pool[name_and_type[1]][1]

    logger.debug("getstatic %s %s", klass_name, field_name)
    klass = frame.vm.get_class(klass_name)

    while klass is not None and field_name not in klass.static_fields:
        klass = klass.super_class
    assert klass is not None

    value = klass.static_fields[field_name][1]
    frame.stack.append(value)


@bytecode(code=0xb3)
def putstatic(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    cp_fieldref = frame.this_class.constant_pool[index]
    assert cp_fieldref[0] == 9  # CONSTANT_Fieldref
    klass_info = frame.this_class.constant_pool[cp_fieldref[1]]
    assert klass_info[0] == 7  # CONSTANT_Class_info
    name_and_type = frame.this_class.constant_pool[cp_fieldref[2]]
    assert name_and_type[0] == 12  # CONSTANT_NameAndType_info
    klass_name = frame.this_class.constant_pool[klass_info[1]][1]
    field_name = frame.this_class.constant_pool[name_and_type[1]][1]

    logger.debug("putstatic %s %s", klass_name, field_name)
    klass = frame.vm.get_class(klass_name)

    while klass is not None and field_name not in klass.static_fields:
        klass = klass.super_class
    assert klass is not None

    value = frame.stack.pop()
    klass.static_fields[field_name][1] = value


@bytecode(code=0xb4)
def getfield(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    cp_fieldref = frame.this_class.constant_pool[index]
    assert cp_fieldref[0] == 9  # CONSTANT_Fieldref
    klass_info = frame.this_class.constant_pool[cp_fieldref[1]]
    assert klass_info[0] == 7  # CONSTANT_Class_info
    name_and_type = frame.this_class.constant_pool[cp_fieldref[2]]
    assert name_and_type[0] == 12  # CONSTANT_NameAndType_info
    klass_name = frame.this_class.constant_pool[klass_info[1]][1]
    field_name = frame.this_class.constant_pool[name_and_type[1]][1]

    logger.debug("getfield %s %s", klass_name, field_name)
    klass = frame.vm.get_class(klass_name)
    # At some point make sure object has right class
    assert klass is not None

    ref = frame.stack.pop()
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)

    if ref[0] == "vm_ref":
        raise Exception("Special handling required, see vmo.txt")

    instance = frame.vm.heap[ref[1]]
    assert field_name in instance.fields
    frame.stack.append(instance.fields[field_name])


@bytecode(code=0xb5)
def putfield(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    cp_fieldref = frame.this_class.constant_pool[index]
    assert cp_fieldref[0] == 9  # CONSTANT_Fieldref
    klass_info = frame.this_class.constant_pool[cp_fieldref[1]]
    assert klass_info[0] == 7  # CONSTANT_Class_info
    name_and_type = frame.this_class.constant_pool[cp_fieldref[2]]
    assert name_and_type[0] == 12  # CONSTANT_NameAndType_info
    klass_name = frame.this_class.constant_pool[klass_info[1]][1]
    field_name = frame.this_class.constant_pool[name_and_type[1]][1]

    logger.debug("putfield %s %s", field_name, klass_name)
    klass = frame.vm.get_class(klass_name)
    assert klass is not None

    value = frame.stack.pop()
    ref = frame.stack.pop()
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)

    if ref[0] == "vm_ref":
        raise Exception("Special handling required, see vmo.txt")

    instance = frame.vm.heap[ref[1]]
    assert field_name in instance.fields
    instance.fields[field_name] = value


@bytecode(code=0xbb)
def new_(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    cp_item = frame.this_class.constant_pool[index]
    assert cp_item[0] == 7  # CONSTANT_Class
    klass_name = frame.this_class.constant_pool[cp_item[1]][1]
    assert type(klass_name) is unicode
    klass = frame.vm.get_class(klass_name)  # make sure it is loaded

    instance = klass.get_instance(frame.vm)
    ref = frame.vm.add_to_heap(instance)
    frame.stack.append(ref)

########NEW FILE########
__FILENAME__ = ops_invokeinterface
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import logging

from pyjvm.bytecode import bytecode
from pyjvm.frame import Frame
from pyjvm.jassert import jassert_ref
from pyjvm.natives import exec_native
from pyjvm.thread import SkipThreadCycle
from pyjvm.utils import args_count
from pyjvm.vmo import vm_obj_call

logger = logging.getLogger(__name__)


@bytecode(code=0xb9)
def invokeinterface(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    count = ord(frame.code[frame.pc])
    assert count > 0
    frame.pc += 1
    zero = ord(frame.code[frame.pc])
    assert zero == 0
    frame.pc += 1
    cp_item = frame.this_class.constant_pool[index]
    assert cp_item[0] == 11  # CONSTANT_Methodref
    klass_info = frame.this_class.constant_pool[cp_item[1]]
    assert klass_info[0] == 7  # CONSTANT_Class_info
    name_and_type = frame.this_class.constant_pool[cp_item[2]]
    assert name_and_type[0] == 12  # name_and_type_index
    klass_name = frame.this_class.constant_pool[klass_info[1]][1]
    method_name = frame.this_class.constant_pool[name_and_type[1]][1]
    method_signature = frame.this_class.constant_pool[name_and_type[2]][1]

    logger.debug("%s %s %s", klass_name, method_name, method_signature)

    frame.vm.get_class(klass_name)

    nargs = args_count(method_signature) + 1
    args = [None] * nargs
    while nargs > 0:
        value = frame.stack.pop()
        if type(value) is tuple and value[0] in ('long', 'double'):
            nargs -= 1
        args[nargs - 1] = value
        nargs -= 1

    logger.debug(args)
    logger.debug(method_signature)
    assert len(args[0]) > 0
    jassert_ref(args[0])

    if args[0] is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return

    if args[0][0] == "vm_ref":  # vm owned object call
        vm_obj_call(frame, args, method_name, method_signature)
        return

    # ignore signute polimorphic method
    instance = frame.vm.heap[args[0][1]]
    klass = instance.java_class
    method = None
    while method is None and klass is not None:
        if method_name in klass.methods:
            if method_signature in klass.methods[method_name]:
                method = klass.methods[method_name][method_signature]
                break
        klass = klass.super_class

    assert method is not None

    if method[0] & 0x0100 > 0:  # is native?
        exec_native(frame, args, klass, method_name, method_signature)
        return

    obj_mon = None
    if method[0] & 0x0020 > 0:  # is sync
        obj_mon = frame.vm.heap[args[0][1]]
        if "@monitor" in obj_mon.fields:
            if obj_mon.fields["@monitor"] == frame.thread:
                obj_mon.fields["@monitor_count"] += 1
            else:
                index = 0
                while index < len(args):
                    a = args[index]
                    if type(a) is tuple and a[0] in ('long', 'double'):
                        index += 1
                    else:
                        frame.stack.append(a)
                    index += 1
                raise SkipThreadCycle()
        else:
            obj_mon.fields["@monitor"] = frame.thread
            obj_mon.fields["@monitor_count"] = 1

    m_args = [''] * method[1]
    m_args[0:len(args)] = args[0:len(args)]

    sub = Frame(frame.thread, klass, method, m_args,
                "InvInt: %s %s in %s" % (method_name, method_signature,
                                         instance.java_class.this_name))
    if obj_mon is not None:
        sub.monitor = obj_mon
    frame.thread.frame_stack.append(sub)
    return

########NEW FILE########
__FILENAME__ = ops_invokespecial
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import logging

from pyjvm.bytecode import bytecode
from pyjvm.frame import Frame
from pyjvm.jassert import jassert_ref
from pyjvm.natives import exec_native
from pyjvm.thread import SkipThreadCycle
from pyjvm.utils import args_count

logger = logging.getLogger(__name__)


@bytecode(code=0xb7)
def invokespecial(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    cp_item = frame.this_class.constant_pool[index]
    assert cp_item[0] == 10  # CONSTANT_Methodref
    klass_info = frame.this_class.constant_pool[cp_item[1]]
    assert klass_info[0] == 7  # CONSTANT_Class_info
    name_and_type = frame.this_class.constant_pool[cp_item[2]]
    assert name_and_type[0] == 12  # name_and_type_index
    klass_name = frame.this_class.constant_pool[klass_info[1]][1]
    klass = frame.vm.get_class(klass_name)
    method_name = frame.this_class.constant_pool[name_and_type[1]][1]
    method_signature = frame.this_class.constant_pool[name_and_type[2]][1]
    method = klass.find_method(method_name, method_signature)

    logger.debug(klass_name)
    logger.debug(method_name)
    logger.debug(method_signature)
    logger.debug(frame.stack)

    if is_spec_lookup(frame.this_class, klass, method_name):
        method = None
        c = frame.this_class.super_class
        while method is None:
            if c is None:
                break
            if (method_name in c.methods and
                    method_signature in c.methods[method_name]):
                method = c.methods[method_name][method_signature]
                klass = c
                break
            c = c.super_class

    assert method is not None

    nargs = args_count(method_signature) + 1
    args = [None] * nargs
    while nargs > 0:
        value = frame.stack.pop()
        if type(value) is tuple and value[0] in ('long', 'double'):
            nargs -= 1
        args[nargs - 1] = value
        nargs -= 1

    assert len(args[0]) > 0
    jassert_ref(args[0])

    if args[0] is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return

    if method[0] & 0x0100 > 0:  # is native?
        exec_native(frame, args, klass, method_name, method_signature)
        return

    obj_mon = None
    if method[0] & 0x0020 > 0:  # is sync
        obj_mon = frame.vm.heap[args[0][1]]
        if "@monitor" in obj_mon.fields:
            if obj_mon.fields["@monitor"] == frame.thread:
                obj_mon.fields["@monitor_count"] += 1
            else:
                index = 0
                while index < len(args):
                    a = args[index]
                    if type(a) is tuple and a[0] in ('long', 'double'):
                        index += 1
                    else:
                        frame.stack.append(a)
                    index += 1
                raise SkipThreadCycle()
        else:
            obj_mon.fields["@monitor"] = frame.thread
            obj_mon.fields["@monitor_count"] = 1

    m_args = [''] * method[1]
    m_args[0:len(args)] = args[0:len(args)]

    instance = frame.vm.heap[args[0][1]]
    logger.debug("InvokeSpec: %s:%s %s", method_name, method_signature,
                 instance)
    sub = Frame(frame.thread, klass, method, m_args,
                "%s:%s %s" % (method_name, method_signature, instance))
    if obj_mon is not None:
        sub.monitor = obj_mon
    frame.thread.frame_stack.append(sub)


def is_spec_lookup(this_class, lookedup_class, method_name):
    if this_class.flags & 0x0020 == 0:
        return False
    if method_name == "<init>":
        return False
    if is_super_class(this_class, lookedup_class.this_name):
        return True
    else:
        return False


def is_super_class(this_class, super_name):
    if this_class.super_class is not None:
        if this_class.super_class.this_name == super_name:
            return True
        else:
            return is_super_class(this_class.super_class, super_name)
    return False

########NEW FILE########
__FILENAME__ = ops_invokestatic
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import logging

from pyjvm.bytecode import bytecode
from pyjvm.frame import Frame
from pyjvm.natives import exec_native
from pyjvm.thread import SkipThreadCycle
from pyjvm.utils import args_count
from pyjvm.vmo import VM_OBJECTS

logger = logging.getLogger(__name__)


@bytecode(code=0xb8)
def invokestatic(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    cp_methodref = frame.this_class.constant_pool[index]
    assert cp_methodref[0] == 10  # CONSTANT_Methodref
    klass_info = frame.this_class.constant_pool[cp_methodref[1]]
    assert klass_info[0] == 7  # CONSTANT_Class_info
    name_and_type = frame.this_class.constant_pool[cp_methodref[2]]
    assert name_and_type[0] == 12  # name_and_type_index
    klass_name = frame.this_class.constant_pool[klass_info[1]][1]
    method_name = frame.this_class.constant_pool[name_and_type[1]][1]
    method_signature = frame.this_class.constant_pool[name_and_type[2]][1]
    assert klass_name is not None
    assert method_name is not None
    assert method_signature is not None

    if klass_name == "sun/misc/VM" and method_name == "isBooted":
        # shortcut, to be remvoed
        frame.stack.append(1)
        return

    if (klass_name == "sun/reflect/Reflection" and
            method_name == "registerMethodsToFilter"):
        logger.debug("Ignoring registerMethodsToFilter")
        frame.stack.pop()
        frame.stack.pop()
        return

    if (klass_name == "sun/misc/SharedSecrets" and
            method_name == "getJavaLangAccess"):
        # use vm owned object instead of constructing real one
        frame.vm.get_class("sun/misc/JavaLangAccess")
        frame.stack.append(("vm_ref", VM_OBJECTS["JavaLangAccess"]))
        return

    logger.debug("%s %s %s", klass_name, method_name, method_signature)

    klass = frame.vm.get_class(klass_name)
    method = klass.find_method(method_name, method_signature)
    assert method is not None
    assert method[0] & 0x0008 > 0  # make sure this is static method

    obj_mon = None
    if method[0] & 0x0020:
        obj_mon = frame.vm.heap[klass.heap_ref[1]]
        if "@monitor" in obj_mon.fields:
            if obj_mon.fields["@monitor"] == frame.thread:
                obj_mon.fields["@monitor_count"] += 1
            else:
                raise SkipThreadCycle()
        else:
            obj_mon.fields["@monitor"] = frame.thread
            obj_mon.fields["@monitor_count"] = 1

    nargs = args_count(method_signature)
    args = [None] * nargs
    while nargs > 0:
        value = frame.stack.pop()
        if type(value) is tuple and value[0] in ('long', 'double'):
            nargs -= 1
        args[nargs - 1] = value
        nargs -= 1

    if method[0] & 0x0100 > 0:  # is native?
        exec_native(frame, args, klass, method_name, method_signature)
        return

    m_args = [''] * method[1]
    m_args[0:len(args)] = args[0:len(args)]

    logger.debug("InvStatic: %s %s in %s", method_name, method_signature,
                 klass_name)
    if method_name == "countBits":
        frame.stack.append(5)
        return

    sub = Frame(frame.thread, klass, method, m_args,
                "InvStatic: %s %s in %s" % (method_name, method_signature,
                                            klass_name))
    if obj_mon is not None:
        sub.monitor = obj_mon
    frame.thread.frame_stack.append(sub)

########NEW FILE########
__FILENAME__ = ops_invokevirtual
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import logging

from pyjvm.bytecode import bytecode
from pyjvm.frame import Frame
from pyjvm.jassert import jassert_ref
from pyjvm.natives import exec_native
from pyjvm.thread import SkipThreadCycle
from pyjvm.utils import args_count
from pyjvm.vmo import vm_obj_call

logger = logging.getLogger(__name__)


@bytecode(code=0xb6)
def invokevirtual(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    cp_item = frame.this_class.constant_pool[index]
    assert cp_item[0] == 10  # CONSTANT_Methodref
    klass_info = frame.this_class.constant_pool[cp_item[1]]
    assert klass_info[0] == 7  # CONSTANT_Class_info
    name_and_type = frame.this_class.constant_pool[cp_item[2]]
    assert name_and_type[0] == 12  # name_and_type_index
    klass_name = frame.this_class.constant_pool[klass_info[1]][1]
    method_name = frame.this_class.constant_pool[name_and_type[1]][1]
    method_signature = frame.this_class.constant_pool[name_and_type[2]][1]

    logger.debug("%s %s %s", klass_name, method_name, method_signature)

    klass = frame.vm.get_class(klass_name)
    method = klass.find_method(method_name, method_signature)

    nargs = args_count(method_signature) + 1
    args = [None] * nargs
    while nargs > 0:
        value = frame.stack.pop()
        if type(value) is tuple and value[0] in ('long', 'double'):
            nargs -= 1
        args[nargs - 1] = value
        nargs -= 1

    logger.debug(frame.id)
    logger.debug(args)
    logger.debug(method_signature)
    jassert_ref(args[0])

    if args[0] is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return

    if args[0][0] == "vm_ref":  # vm owned object call
        vm_obj_call(frame, args, method_name, method_signature)
        return

    # ignore signute polimorphic method
    instance = frame.vm.heap[args[0][1]]
    klass = instance.java_class
    method = None
    while method is None and klass is not None:
        if method_name in klass.methods:
            if method_signature in klass.methods[method_name]:
                method = klass.methods[method_name][method_signature]
                break
        klass = klass.super_class

    assert method is not None
    assert klass is not None

    if method[0] & 0x0100 > 0:  # is native?
        exec_native(frame, args, klass, method_name, method_signature)
        return

    obj_mon = None
    if method[0] & 0x0020 > 0:  # is sync
        obj_mon = frame.vm.heap[args[0][1]]
        if "@monitor" in obj_mon.fields:
            if obj_mon.fields["@monitor"] == frame.thread:
                obj_mon.fields["@monitor_count"] += 1
            else:
                index = 0
                while index < len(args):
                    a = args[index]
                    if type(a) is tuple and a[0] in ('long', 'double'):
                        index += 1
                    else:
                        frame.stack.append(a)
                    index += 1
                raise SkipThreadCycle()
        else:
            obj_mon.fields["@monitor"] = frame.thread
            obj_mon.fields["@monitor_count"] = 1

    m_args = [''] * method[1]
    m_args[0:len(args)] = args[0:len(args)]

    sub = Frame(frame.thread, klass, method, m_args,
                "InvVirt: %s %s in %s" % (method_name, method_signature,
                                          instance.java_class.this_name))
    if obj_mon is not None:
        sub.monitor = obj_mon
    frame.thread.frame_stack.append(sub)

########NEW FILE########
__FILENAME__ = ops_misc
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import struct

from pyjvm.bytecode import bytecode
from pyjvm.jassert import jassert_ref
from pyjvm.thread import SkipThreadCycle
from pyjvm.utils import category_type


@bytecode(code=0x57)
def pop(frame):
    value = frame.stack.pop()
    assert category_type(value) == 1


@bytecode(code=0x58)
def pop2(frame):
    value = frame.stack.pop()
    if category_type(value) == 2:
        pass
    else:
        value = frame.stack.pop()
        assert category_type(value) == 1


@bytecode(code=0x59)
def dup(frame):
    value = frame.stack.pop()
    assert category_type(value) == 1
    frame.stack.append(value)
    frame.stack.append(value)


@bytecode(code=0x5a)
def dup_x1(frame):
    value1 = frame.stack.pop()
    value2 = frame.stack.pop()
    assert category_type(value1) == 1
    assert category_type(value2) == 1
    frame.stack.append(value1)
    frame.stack.append(value2)
    frame.stack.append(value1)


@bytecode(code=0x5b)
def dup_x2(frame):
    value1 = frame.stack.pop()
    value2 = frame.stack.pop()
    if category_type(value1) == 1 and category_type(value2) == 2:
        # form2
        frame.stack.append(value1)
        frame.stack.append(value2)
        frame.stack.append(value1)
        return
    value3 = frame.stack.pop()
    if (category_type(value1) == 1 and category_type(value2) == 1 and
            category_type(value3 == 1)):
        # form 1
        frame.stack.append(value1)
        frame.stack.append(value3)
        frame.stack.append(value2)
        frame.stack.append(value1)
        return
    assert False  # should never get here


@bytecode(code=0x5c)
def dup2(frame):
    value1 = frame.stack.pop()
    if category_type(value1) == 2:
        # form 2
        frame.stack.append(value1)
        frame.stack.append(value1)
        return
    value2 = frame.stack.pop()
    if category_type(value1) == 1 and category_type(value2) == 1:
        # form 1
        frame.stack.append(value2)
        frame.stack.append(value1)
        frame.stack.append(value2)
        frame.stack.append(value1)
        return
    assert False  # should never get here


@bytecode(code=0x5d)
def dup2_x1(frame):
    value1 = frame.stack.pop()
    value2 = frame.stack.pop()
    if category_type(value1) == 2 and category_type(value2) == 1:
        # form 2
        frame.stack.append(value1)
        frame.stack.append(value2)
        frame.stack.append(value1)
        return
    value3 = frame.stack.pop()
    if (category_type(value1) == 1 and category_type(value2) == 1 and
            category_type(value3) == 1):
        # form 1
        frame.stack.append(value2)
        frame.stack.append(value1)
        frame.stack.append(value3)
        frame.stack.append(value2)
        frame.stack.append(value1)
        return
    assert False  # should never get here


@bytecode(code=0x5e)
def dup2_x2(frame):
    value1 = frame.stack.pop()
    value2 = frame.stack.pop()
    if category_type(value1) == 2 and category_type(value2) == 2:
        # form 4
        frame.stack.append(value1)
        frame.stack.append(value2)
        frame.stack.append(value1)
        return
    value3 = frame.stack.pop()
    if (category_type(value1) == 1 and category_type(value2) == 1 and
            category_type(value3) == 2):
        # form 3
        frame.stack.append(value2)
        frame.stack.append(value1)
        frame.stack.append(value3)
        frame.stack.append(value2)
        frame.stack.append(value1)
        return
    if (category_type(value1) == 2 and category_type(value2) == 1 and
            category_type(value3) == 1):
        # form 2
        frame.stack.append(value1)
        frame.stack.append(value3)
        frame.stack.append(value2)
        frame.stack.append(value1)
        return
    value4 = frame.stack.pop()
    if (category_type(value1) == 1 and category_type(value2) == 1 and
            category_type(value3) == 1 and category_type(value4) == 1):
        # form 1
        frame.stack.append(value2)
        frame.stack.append(value1)
        frame.stack.append(value4)
        frame.stack.append(value3)
        frame.stack.append(value2)
        frame.stack.append(value1)
        return
    assert False  # should never get here


@bytecode(code=0x5f)
def swap(frame):
    value1 = frame.stack.pop()
    value2 = frame.stack.pop()
    frame.stack.append(value2)
    frame.stack.append(value1)


@bytecode(code=0xa9)
def ret(frame):
    index = struct.unpack(">B", frame.code[frame.pc])[0]
    frame.pc = frame.args[index]


@bytecode(code=0xba)
def invokedynamic(frame):
    raise Exception("Method handlers are not supported")


@bytecode(code=0xca)
def breakpoint(frame):
    raise Exception("This op code (fe) should not present in class file")


@bytecode(code=0xc2)
def monitorenter(frame):
    ref = frame.stack.pop()
    jassert_ref(ref)
    o = frame.vm.heap[ref[1]]
    if "@monitor" in o.fields:
        if o.fields["@monitor"] == frame.thread:
            o.fields["@monitor_count"] += 1
        else:
            frame.stack.append(ref)
            raise SkipThreadCycle()
    else:
        o.fields["@monitor"] = frame.thread
        o.fields["@monitor_count"] = 1


@bytecode(code=0xc3)
def monitorexit(frame):
    ref = frame.stack.pop()
    jassert_ref(ref)
    o = frame.vm.heap[ref[1]]
    if o.fields["@monitor_count"] == 1:
        del o.fields["@monitor"]
        del o.fields["@monitor_count"]
    else:
        o.fields["@monitor_count"] -= 1


@bytecode(code=0xc4)
def wide(frame):
    op_code = ord(frame.code[frame.pc])
    frame.pc += 1
    data = frame.code[frame.pc:frame.pc + 2]
    index = struct.unpack(">H", data)[0]
    frame.pc += 2
    if op_code == 132:  # x84 iinc
        data = frame.code[frame.pc:frame.pc + 2]
        value = struct.unpack(">h", data)[0]
        frame.pc += 2
        assert type(frame.args[index]) is int
        frame.args[index] += value
        return
    if op_code in (0x15, 0x16, 0x17, 0x18, 0x19):
        # *load
        frame.stack.append(frame.args[index])
        return
    if op_code in (0x36, 0x37, 0x38, 0x39, 0x3a):
        # *store
        frame.stack.append(frame.args[index])
        return
    if op_code == 0xa9:
        # ret
        frame.pc = frame.args[index]
        return
    assert False  # should never get here


@bytecode(code=0xfe)
def impdep1(frame):
    raise Exception("This op code (fe) should not present in class file")


@bytecode(code=0xff)
def impdep2(frame):
    raise Exception("This op code (ff) should not present in class file")

########NEW FILE########
__FILENAME__ = ops_names
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

ops_name = {}

ops_name["op_0x1"] = "aconst_null"
ops_name["op_0x2"] = "iconst_m1"
ops_name["op_0x3"] = "iconst_0"
ops_name["op_0x4"] = "iconst_1"
ops_name["op_0x5"] = "iconst_2"
ops_name["op_0x6"] = "iconst_3"
ops_name["op_0x7"] = "iconst_4"
ops_name["op_0x8"] = "iconst_5"
ops_name["op_0x9"] = "lconst_0"
ops_name["op_0xa"] = "lconst_1"
ops_name["op_0xb"] = "fconst_0"
ops_name["op_0xc"] = "fconst_1"
ops_name["op_0xd"] = "fconst_2"
ops_name["op_0xe"] = "dconst_0"
ops_name["op_0xf"] = "dconst_1"
ops_name["op_0x10"] = "bipush"
ops_name["op_0x11"] = "sipush"
ops_name["op_0x12"] = "ldc"
ops_name["op_0x13"] = "ldc_w"
ops_name["op_0x14"] = "ldc2_w"
ops_name["op_0x15"] = "iload"
ops_name["op_0x16"] = "lload"
ops_name["op_0x17"] = "fload"
ops_name["op_0x18"] = "dload"
ops_name["op_0x19"] = "aload"
ops_name["op_0x1a"] = "iload_0"
ops_name["op_0x1b"] = "iload_1"
ops_name["op_0x1c"] = "iload_2"
ops_name["op_0x1d"] = "iload_3"
ops_name["op_0x1e"] = "lload_0"
ops_name["op_0x1f"] = "lload_1"
ops_name["op_0x20"] = "lload_2"
ops_name["op_0x21"] = "lload_3"
ops_name["op_0x22"] = "fload_0"
ops_name["op_0x23"] = "fload_1"
ops_name["op_0x24"] = "fload_2"
ops_name["op_0x25"] = "fload_3"
ops_name["op_0x26"] = "dload_0"
ops_name["op_0x27"] = "dload_1"
ops_name["op_0x28"] = "dload_2"
ops_name["op_0x29"] = "dload_3"
ops_name["op_0x2a"] = "aload_0"
ops_name["op_0x2b"] = "aload_1"
ops_name["op_0x2c"] = "aload_2"
ops_name["op_0x2d"] = "aload_3"
ops_name["op_0x2e"] = "iaload"
ops_name["op_0x2f"] = "laload"
ops_name["op_0x30"] = "faload"
ops_name["op_0x31"] = "daload"
ops_name["op_0x32"] = "aaload"
ops_name["op_0x33"] = "baload"
ops_name["op_0x34"] = "caload"
ops_name["op_0x35"] = "saload"
ops_name["op_0x36"] = "istore"
ops_name["op_0x37"] = "lstore"
ops_name["op_0x38"] = "fstore"
ops_name["op_0x39"] = "dstore"
ops_name["op_0x3a"] = "astore"
ops_name["op_0x3b"] = "istore_0"
ops_name["op_0x3c"] = "istore_1"
ops_name["op_0x3d"] = "istore_2"
ops_name["op_0x3e"] = "istore_3"
ops_name["op_0x3f"] = "lstore_0"
ops_name["op_0x40"] = "lstore_1"
ops_name["op_0x41"] = "lstore_2"
ops_name["op_0x42"] = "lstore_3"
ops_name["op_0x43"] = "fstore_0"
ops_name["op_0x44"] = "fstore_1"
ops_name["op_0x45"] = "fstore_2"
ops_name["op_0x46"] = "fstore_3"
ops_name["op_0x47"] = "dstore_0"
ops_name["op_0x48"] = "dstore_1"
ops_name["op_0x49"] = "dstore_2"
ops_name["op_0x4a"] = "dstore_3"
ops_name["op_0x4b"] = "astore_0"
ops_name["op_0x4c"] = "astore_1"
ops_name["op_0x4d"] = "astore_2"
ops_name["op_0x4e"] = "astore_3"
ops_name["op_0x4f"] = "iastore"
ops_name["op_0x50"] = "lastore"
ops_name["op_0x51"] = "fastore"
ops_name["op_0x52"] = "dastore"
ops_name["op_0x53"] = "aastore"
ops_name["op_0x54"] = "bastore"
ops_name["op_0x55"] = "castore"
ops_name["op_0x56"] = "sastore"
ops_name["op_0x57"] = "pop"
ops_name["op_0x58"] = "pop2"
ops_name["op_0x59"] = "dup"
ops_name["op_0x5a"] = "dup_x1"
ops_name["op_0x5b"] = "dup_x2"
ops_name["op_0x5c"] = "dup2"
ops_name["op_0x5d"] = "dup2_x1"
ops_name["op_0x5e"] = "dup2_x2"
ops_name["op_0x5f"] = "swap"
ops_name["op_0x60"] = "iadd"
ops_name["op_0x61"] = "ladd"
ops_name["op_0x62"] = "fadd"
ops_name["op_0x63"] = "dadd"
ops_name["op_0x64"] = "isub"
ops_name["op_0x65"] = "lsub"
ops_name["op_0x66"] = "fsub"
ops_name["op_0x67"] = "dsub"
ops_name["op_0x68"] = "imul"
ops_name["op_0x69"] = "lmul"
ops_name["op_0x6a"] = "fmul"
ops_name["op_0x6b"] = "dmul"
ops_name["op_0x6c"] = "idiv"
ops_name["op_0x6d"] = "ldiv"
ops_name["op_0x6e"] = "fdiv"
ops_name["op_0x6f"] = "ddiv"
ops_name["op_0x70"] = "irem"
ops_name["op_0x71"] = "lrem"
ops_name["op_0x72"] = "frem"
ops_name["op_0x73"] = "drem"
ops_name["op_0x74"] = "ineg"
ops_name["op_0x75"] = "lneg"
ops_name["op_0x76"] = "fneg"
ops_name["op_0x77"] = "dneg"
ops_name["op_0x78"] = "ishl"
ops_name["op_0x79"] = "lshl"
ops_name["op_0x7a"] = "ishr"
ops_name["op_0x7b"] = "lshr"
ops_name["op_0x7c"] = "iushr"
ops_name["op_0x7d"] = "lushr"
ops_name["op_0x7e"] = "iand"
ops_name["op_0x7f"] = "land"
ops_name["op_0x80"] = "ior"
ops_name["op_0x81"] = "lor"
ops_name["op_0x82"] = "ixor"
ops_name["op_0x83"] = "lxor"
ops_name["op_0x84"] = "iinc"
ops_name["op_0x85"] = "i2l"
ops_name["op_0x86"] = "i2f"
ops_name["op_0x87"] = "i2d"
ops_name["op_0x88"] = "l2i"
ops_name["op_0x89"] = "l2f"
ops_name["op_0x8a"] = "l2d"
ops_name["op_0x8b"] = "f2i"
ops_name["op_0x8c"] = "f2l"
ops_name["op_0x8d"] = "f2d"
ops_name["op_0x8e"] = "d2i"
ops_name["op_0x8f"] = "d2l"
ops_name["op_0x90"] = "d2f"
ops_name["op_0x91"] = "i2b"
ops_name["op_0x92"] = "i2c"
ops_name["op_0x93"] = "i2s"
ops_name["op_0x94"] = "lcmp"
ops_name["op_0x95"] = "fcmpl"
ops_name["op_0x96"] = "fcmpg"
ops_name["op_0x97"] = "dcmpl"
ops_name["op_0x98"] = "dcmpg"
ops_name["op_0x99"] = "ifeq"
ops_name["op_0x9a"] = "ifne"
ops_name["op_0x9b"] = "iflt"
ops_name["op_0x9c"] = "ifge"
ops_name["op_0x9d"] = "ifgt"
ops_name["op_0x9e"] = "ifle"
ops_name["op_0x9f"] = "if_icmpeq"
ops_name["op_0xa0"] = "if_icmpne"
ops_name["op_0xa1"] = "if_icmplt"
ops_name["op_0xa2"] = "if_icmpge"
ops_name["op_0xa3"] = "if_icmpgt"
ops_name["op_0xa4"] = "if_icmple"
ops_name["op_0xa5"] = "if_acmpeq"
ops_name["op_0xa6"] = "if_acmpne"
ops_name["op_0xa7"] = "goto"
ops_name["op_0xa8"] = "jsr"
ops_name["op_0xa9"] = "ret"
ops_name["op_0xaa"] = "tableswitch"
ops_name["op_0xab"] = "lookupswitch"
ops_name["op_0xac"] = "ireturn"
ops_name["op_0xad"] = "lreturn"
ops_name["op_0xae"] = "freturn"
ops_name["op_0xaf"] = "dreturn"
ops_name["op_0xb0"] = "areturn"
ops_name["op_0xb1"] = "return"
ops_name["op_0xb2"] = "getstatic"
ops_name["op_0xb3"] = "putstatic"
ops_name["op_0xb4"] = "getfield"
ops_name["op_0xb5"] = "putfield"
ops_name["op_0xb6"] = "invokevirtual"
ops_name["op_0xb7"] = "invokespecial"
ops_name["op_0xb8"] = "invokestatic"
ops_name["op_0xb9"] = "invokeinterface"
ops_name["op_0xba"] = "invokedynamic"
ops_name["op_0xbb"] = "new"
ops_name["op_0xbc"] = "newarray"
ops_name["op_0xbd"] = "anewarray"
ops_name["op_0xbe"] = "arraylength"
ops_name["op_0xbf"] = "athrow"
ops_name["op_0xc0"] = "checkcast"
ops_name["op_0xc1"] = "instanceof"
ops_name["op_0xc2"] = "monitorenter"
ops_name["op_0xc3"] = "monitorexit"
ops_name["op_0xc4"] = "wide"
ops_name["op_0xc5"] = "multianewarray"
ops_name["op_0xc6"] = "ifnull"
ops_name["op_0xc7"] = "ifnonnull"
ops_name["op_0xc8"] = "goto_w"
ops_name["op_0xc9"] = "jsr_w"
ops_name["op_0xca"] = "breakpoint"
ops_name["op_0xfe"] = "impdep1"
ops_name["op_0xff"] = "impdep2"

########NEW FILE########
__FILENAME__ = ops_ret
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import logging

from pyjvm.bytecode import bytecode
from pyjvm.jassert import jassert_float
from pyjvm.jassert import jassert_double
from pyjvm.jassert import jassert_int
from pyjvm.jassert import jassert_long
from pyjvm.jassert import jassert_ref
from pyjvm.throw import JavaException

logger = logging.getLogger(__name__)


@bytecode(code=0xac)
def ireturn(frame):
    value = frame.stack.pop()
    logger.debug("To be returned {0}".format(value))
    jassert_int(value)
    frame.ret = value
    frame.has_result = True
    frame.pc = len(frame.code) + 1


@bytecode(code=0xad)
def lreturn(frame):
    value = frame.stack.pop()
    logger.debug("To be returned {0}".format(value))
    jassert_long(value)
    frame.ret = value
    frame.has_result = True
    frame.pc = len(frame.code) + 1


@bytecode(code=0xae)
def freturn(frame):
    value = frame.stack.pop()
    logger.debug("To be returned {0}".format(value))
    jassert_float(value)
    frame.ret = value
    frame.has_result = True
    frame.pc = len(frame.code) + 1


@bytecode(code=0xaf)
def dreturn(frame):
    value = frame.stack.pop()
    logger.debug("To be returned {0}".format(value))
    jassert_double(value)
    frame.ret = value
    frame.has_result = True
    frame.pc = len(frame.code) + 1


@bytecode(code=0xb0)
def areturn(frame):
    value = frame.stack.pop()
    jassert_ref(value)
    frame.ret = value
    frame.has_result = True
    frame.pc = len(frame.code) + 1


@bytecode(code=0xb1)
def return_(frame):
    frame.pc = len(frame.code) + 1


@bytecode(code=0xbf)
def athrow(frame):
    ref = frame.stack.pop()
    if ref is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    jassert_ref(ref)
    frame.stack[:] = []  # empty stack
    frame.stack.append(ref)
    je = JavaException(frame.vm, ref)
    raise je

########NEW FILE########
__FILENAME__ = ops_setget
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import logging
import struct

from pyjvm.bytecode import bytecode
from pyjvm.jassert import jassert_float
from pyjvm.jassert import jassert_double
from pyjvm.jassert import jassert_int
from pyjvm.jassert import jassert_long
from pyjvm.jassert import jassert_ref

logger = logging.getLogger(__name__)


@bytecode(code=0x0)
def nop(frame):
    # BEST OP CODE, yes - it asks to do nothing
    pass


@bytecode(code=0x1)
def aconst_null(frame):
    frame.stack.append(None)


@bytecode(code=0x2)
def iconst_m1(frame):
    frame.stack.append(-1)


@bytecode(code=0x3)
def iconst_0(frame):
    frame.stack.append(0)


@bytecode(code=0x4)
def iconst_1(frame):
    frame.stack.append(1)


@bytecode(code=0x5)
def iconst_2(frame):
    frame.stack.append(2)


@bytecode(code=0x6)
def iconst_3(frame):
    frame.stack.append(3)


@bytecode(code=0x7)
def iconst_4(frame):
    frame.stack.append(4)


@bytecode(code=0x8)
def iconst_5(frame):
    frame.stack.append(5)


@bytecode(code=0x9)
def lconst_0(frame):
    frame.stack.append(("long", 0))


@bytecode(code=0xa)
def lconst_1(frame):
    frame.stack.append(("long", 1))


@bytecode(code=0xb)
def fconst_0(frame):
    frame.stack.append(("float", 0.0))


@bytecode(code=0xc)
def fconst_1(frame):
    frame.stack.append(("float", 1.0))


@bytecode(code=0xd)
def fconst_2(frame):
    frame.stack.append(("float", 2.0))


@bytecode(code=0xe)
def dconst_0(frame):
    frame.stack.append(("double", 0.0))


@bytecode(code=0xf)
def dconst_1(frame):
    frame.stack.append(("double", 1.0))


@bytecode(code=0x10)
def bipush(frame):
    byte = frame.code[frame.pc]
    frame.pc += 1
    value = struct.unpack(">b", byte)[0]
    frame.stack.append(value)


@bytecode(code=0x11)
def sipush(frame):
    short = struct.unpack(">h", frame.code[frame.pc]
                          + frame.code[frame.pc + 1])[0]
    frame.pc += 2
    frame.stack.append(short)


@bytecode(code=0x12)
def ldc(frame):
    index = ord(frame.code[frame.pc])
    frame.pc += 1
    cp_item = frame.this_class.constant_pool[index]
    if cp_item[0] == 8:  # CONSTANT_String
        value = frame.this_class.constant_pool[cp_item[1]][1]
        ref = frame.vm.make_heap_string(value)
        frame.stack.append(ref)
        return
    elif cp_item[0] == 3:  # CONSTANT_Int
        frame.stack.append(cp_item[1])
        return
    elif cp_item[0] == 4:  # CONSTANT_Float
        frame.stack.append(("float", cp_item[1]))
        return
    elif cp_item[0] == 7:  # CONSTANT_Class
        klass_name = frame.this_class.constant_pool[cp_item[1]][1]
        logger.debug(klass_name)
        klass = frame.vm.get_class(klass_name)
        frame.stack.append(klass.heap_ref)
        return
    else:
        # No support for method ref
        raise Exception("0x12 not yet supported cp item type: %d" % cp_item[0])


@bytecode(code=0x13)
def ldc_w(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    cp_item = frame.this_class.constant_pool[index]
    if cp_item[0] == 7:  # CONSTANT_Class
        klass_name = frame.this_class.constant_pool[cp_item[1]][1]
        logger.debug(klass_name)
        klass = frame.vm.get_class(klass_name)
        frame.stack.append(klass.heap_ref)
        return
    elif cp_item[0] == 8:  # CONSTANT_String
        value = frame.this_class.constant_pool[cp_item[1]][1]
        ref = frame.vm.make_heap_string(value)
        frame.stack.append(ref)
        return
    elif cp_item[0] == 4:  # CONSTANT_Float
        frame.stack.append(("float", cp_item[1]))
        return
    elif cp_item[0] == 3:  # CONSTANT_Int
        frame.stack.append(cp_item[1])
        return
    else:
        # No support for method ref yet
        raise Exception("0x13 not yet supported cp item type: %d" % cp_item[0])


@bytecode(code=0x14)
def ldc2_w(frame):
    index = (ord(frame.code[frame.pc]) << 8) + ord(frame.code[frame.pc + 1])
    frame.pc += 2
    cp_item = frame.this_class.constant_pool[index]
    if cp_item[0] == 6:  # double
        frame.stack.append(("double", cp_item[1]))
    elif cp_item[0] == 5:  # long
        frame.stack.append(("long", cp_item[1]))
    else:
        # This should never happen
        raise Exception(cp_item)


@bytecode(code=0x15)
def iload(frame):
    index = ord(frame.code[frame.pc])
    frame.pc += 1
    value = frame.args[index]
    jassert_int(value)
    frame.stack.append(value)


@bytecode(code=0x16)
def lload(frame):
    index = ord(frame.code[frame.pc])
    frame.pc += 1
    value = frame.args[index]
    jassert_long(value)
    frame.stack.append(value)


@bytecode(code=0x17)
def fload(frame):
    index = ord(frame.code[frame.pc])
    frame.pc += 1
    value = frame.args[index]
    jassert_float(value)
    frame.stack.append(value)


@bytecode(code=0x18)
def dload(frame):
    index = ord(frame.code[frame.pc])
    frame.pc += 1
    value = frame.args[index]
    jassert_double(value)
    frame.stack.append(value)


@bytecode(code=0x19)
def aload(frame):
    index = ord(frame.code[frame.pc])
    frame.pc += 1
    value = frame.args[index]
    jassert_ref(value)
    frame.stack.append(value)


@bytecode(code=0x1a)
def iload_0(frame):
    value = frame.args[0]
    jassert_int(value)
    frame.stack.append(value)


@bytecode(code=0x1b)
def iload_1(frame):
    value = frame.args[1]
    jassert_int(value)
    frame.stack.append(value)


@bytecode(code=0x1c)
def iload_2(frame):
    value = frame.args[2]
    jassert_int(value)
    frame.stack.append(value)


@bytecode(code=0x1d)
def iload_3(frame):
    value = frame.args[3]
    jassert_int(value)
    frame.stack.append(value)


@bytecode(code=0x1e)
def lload_0(frame):
    value = frame.args[0]
    jassert_long(value)
    frame.stack.append(value)


@bytecode(code=0x1f)
def lload_1(frame):
    value = frame.args[1]
    jassert_long(value)
    frame.stack.append(value)


@bytecode(code=0x20)
def lload_2(frame):
    value = frame.args[2]
    jassert_long(value)
    frame.stack.append(value)


@bytecode(code=0x21)
def lload_3(frame):
    value = frame.args[3]
    jassert_long(value)
    frame.stack.append(value)


@bytecode(code=0x22)
def fload_0(frame):
    value = frame.args[0]
    jassert_float(value)
    frame.stack.append(value)


@bytecode(code=0x23)
def fload_1(frame):
    value = frame.args[1]
    jassert_float(value)
    frame.stack.append(value)


@bytecode(code=0x24)
def fload_2(frame):
    value = frame.args[2]
    jassert_float(value)
    frame.stack.append(value)


@bytecode(code=0x25)
def fload_3(frame):
    value = frame.args[3]
    jassert_float(value)
    frame.stack.append(value)


@bytecode(code=0x26)
def dload_0(frame):
    value = frame.args[0]
    jassert_double(value)
    frame.stack.append(value)


@bytecode(code=0x27)
def dload_1(frame):
    value = frame.args[1]
    jassert_double(value)
    frame.stack.append(value)


@bytecode(code=0x28)
def dload_2(frame):
    value = frame.args[2]
    jassert_double(value)
    frame.stack.append(value)


@bytecode(code=0x29)
def dload_3(frame):
    value = frame.args[3]
    jassert_double(value)
    frame.stack.append(value)


@bytecode(code=0x2a)
def aload_0(frame):
    value = frame.args[0]
    jassert_ref(value)
    frame.stack.append(value)


@bytecode(code=0x2b)
def aload_1(frame):
    value = frame.args[1]
    jassert_ref(value)
    frame.stack.append(value)


@bytecode(code=0x2c)
def aload_2(frame):
    value = frame.args[2]
    jassert_ref(value)
    frame.stack.append(value)


@bytecode(code=0x2d)
def aload_3(frame):
    value = frame.args[3]
    jassert_ref(value)
    frame.stack.append(value)


@bytecode(code=0x36)
def istore(frame):
    index = ord(frame.code[frame.pc])
    frame.pc += 1
    value = frame.stack.pop()
    jassert_int(value)
    frame.args[index] = value


@bytecode(code=0x37)
def lstore(frame):
    index = ord(frame.code[frame.pc])
    frame.pc += 1
    value = frame.stack.pop()
    jassert_long(value)
    frame.args[index] = value


@bytecode(code=0x38)
def fstore(frame):
    index = ord(frame.code[frame.pc])
    frame.pc += 1
    value = frame.stack.pop()
    jassert_float(value)
    frame.args[index] = value


@bytecode(code=0x39)
def dstore(frame):
    index = ord(frame.code[frame.pc])
    frame.pc += 1
    value = frame.stack.pop()
    jassert_double(value)
    frame.args[index] = value


@bytecode(code=0x3a)
def astore(frame):
    index = ord(frame.code[frame.pc])
    frame.pc += 1
    value = frame.stack.pop()
    jassert_ref(value)
    frame.args[index] = value


@bytecode(code=0x3b)
def istore_0(frame):
    value = frame.stack.pop()
    jassert_int(value)
    frame.args[0] = value


@bytecode(code=0x3c)
def istore_1(frame):
    value = frame.stack.pop()
    jassert_int(value)
    frame.args[1] = value


@bytecode(code=0x3d)
def istore_2(frame):
    value = frame.stack.pop()
    jassert_int(value)
    frame.args[2] = value


@bytecode(code=0x3e)
def istore_3(frame):
    value = frame.stack.pop()
    jassert_int(value)
    frame.args[3] = value


@bytecode(code=0x3f)
def lstore_0(frame):
    value = frame.stack.pop()
    jassert_long(value)
    frame.args[0] = value


@bytecode(code=0x40)
def lstore_1(frame):
    value = frame.stack.pop()
    jassert_long(value)
    frame.args[1] = value


@bytecode(code=0x41)
def lstore_2(frame):
    value = frame.stack.pop()
    jassert_long(value)
    frame.args[2] = value


@bytecode(code=0x42)
def lstore_3(frame):
    value = frame.stack.pop()
    jassert_long(value)
    frame.args[3] = value


@bytecode(code=0x43)
def fstore_0(frame):
    value = frame.stack.pop()
    jassert_float(value)
    frame.args[0] = value


@bytecode(code=0x44)
def fstore_1(frame):
    value = frame.stack.pop()
    jassert_float(value)
    frame.args[1] = value


@bytecode(code=0x45)
def fstore_2(frame):
    value = frame.stack.pop()
    jassert_float(value)
    frame.args[2] = value


@bytecode(code=0x46)
def fstore_3(frame):
    value = frame.stack.pop()
    jassert_float(value)
    frame.args[3] = value


@bytecode(code=0x47)
def dstore_0(frame):
    value = frame.stack.pop()
    jassert_double(value)
    frame.args[0] = value


@bytecode(code=0x48)
def dstore_1(frame):
    value = frame.stack.pop()
    jassert_double(value)
    frame.args[1] = value


@bytecode(code=0x49)
def dstore_2(frame):
    value = frame.stack.pop()
    jassert_double(value)
    frame.args[2] = value


@bytecode(code=0x4a)
def dstore_3(frame):
    value = frame.stack.pop()
    jassert_double(value)
    frame.args[3] = value


@bytecode(code=0x4b)
def astore_0(frame):
    value = frame.stack.pop()
    jassert_ref(value)
    frame.args[0] = value


@bytecode(code=0x4c)
def astore_1(frame):
    value = frame.stack.pop()
    jassert_ref(value)
    frame.args[1] = value


@bytecode(code=0x4d)
def astore_2(frame):
    value = frame.stack.pop()
    jassert_ref(value)
    frame.args[2] = value


@bytecode(code=0x4e)
def astore_3(frame):
    value = frame.stack.pop()
    jassert_ref(value)
    frame.args[3] = value

########NEW FILE########
__FILENAME__ = ops_shift
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java bytecode implementation'''

import struct

from pyjvm.bytecode import bytecode
from pyjvm.jassert import jassert_int
from pyjvm.jassert import jassert_long
from pyjvm.ops.ops_calc import cut_to_int
from pyjvm.ops.ops_calc import cut_to_long


def rshift(val, n):
    return (val % 0x100000000) >> n


@bytecode(code=0x78)
def ishl(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value2)
    jassert_int(value1)
    value2 &= 0b11111
    result = value1 << value2
    result = cut_to_int(result)
    jassert_int(result)
    frame.stack.append(result)


@bytecode(code=0x79)
def lshl(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value2)
    jassert_long(value1)
    value2 &= 0b111111
    result = value1[1] << value2
    result = ("long", cut_to_long(result))
    jassert_long(result)
    frame.stack.append(result)


@bytecode(code=0x7a)
def ishr(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value2)
    jassert_int(value1)
    value2 &= 0b11111
    result = value1 >> value2
    result = cut_to_int(result)
    jassert_int(result)
    frame.stack.append(result)


@bytecode(code=0x7b)
def lshr(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value2)
    jassert_long(value1)
    value2 &= 0b111111
    result = value1[1] >> value2
    result = ("long", cut_to_long(result))
    jassert_long(result)
    frame.stack.append(result)


@bytecode(code=0x7c)
def iushr(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value2)
    jassert_int(value1)
    value2 &= 0b11111
    data = struct.pack(">i", value1)
    result = struct.unpack(">I", data)[0]
    result >>= value2
    data = struct.pack(">I", result)
    result = struct.unpack(">i", data)[0]
    jassert_int(value1)
    frame.stack.append(result)


@bytecode(code=0x7d)
def lushr(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_long(value1)
    jassert_int(value2)
    value2 &= 0b111111
    data = struct.pack(">q", value1[1])
    result = struct.unpack(">Q", data)[0]
    result >>= value2
    data = struct.pack(">Q", result)
    result = struct.unpack(">q", data)[0]
    result = ("long", cut_to_long(result))
    jassert_long(result)
    frame.stack.append(result)


@bytecode(code=0x7e)
def iand(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value2)
    jassert_int(value1)
    result = value1 & value2
    result = cut_to_int(result)
    jassert_int(result)
    frame.stack.append(result)


@bytecode(code=0x7f)
def land(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_long(value2)
    jassert_long(value1)
    result = value1[1] & value2[1]
    result = ("long", cut_to_int(result))
    jassert_long(result)
    frame.stack.append(result)


@bytecode(code=0x80)
def ior(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value2)
    jassert_int(value1)
    result = value1 | value2
    result = cut_to_int(result)
    jassert_int(result)
    frame.stack.append(result)


@bytecode(code=0x81)
def lor(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_long(value2)
    jassert_long(value1)
    result = value1[1] | value2[1]
    result = ("long", cut_to_int(result))
    jassert_long(result)
    frame.stack.append(result)


@bytecode(code=0x82)
def ixor(frame):
    value2 = frame.stack.pop()
    value1 = frame.stack.pop()
    jassert_int(value2)
    jassert_int(value1)
    result = value1 ^ value2
    result = cut_to_int(result)
    jassert_int(result)
    frame.stack.append(result)

########NEW FILE########
__FILENAME__ = filedescriptor
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''


def java_io_FileDescriptor_initIDs___V(frame, args):
    # do nothing
    pass


def java_io_FileDescriptor_set__I_J(frame, args):
    value = args[0]
    frame.stack.append(('long', value))

########NEW FILE########
__FILENAME__ = fileinputstream
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

import os

from pyjvm.utils import str_to_string


def java_io_FileInputStream_initIDs___V(frame, args):
    # do nothing
    pass


def java_io_FileInputStream_open__Ljava_lang_String__V(frame, args):
    if args[1] is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    fis = frame.vm.heap[args[0][1]]
    ref = args[1]
    file_name = str_to_string(frame.vm, ref)
    if not os.path.isfile(file_name):
        frame.vm.raise_exception(frame, "java/io/FileNotFoundException")
        return
    size = os.path.getsize(file_name)
    f = open(file_name, 'rb')
    fis.fields["@file"] = f
    fis.fields["@available_bytes"] = size


def java_io_FileInputStream_readBytes___BII_I(frame, args):
    fis = frame.vm.heap[args[0][1]]
    if fis.fields["@available_bytes"] == 0:
        frame.stack.append(-1)
        return
    buf = frame.vm.heap[args[1][1]]
    offset = args[2]
    length = args[3]
    f = fis.fields["@file"]
    data = f.read(length)
    for c in data:
        buf.values[offset] = ord(c)
        offset += 1
    fis.fields["@available_bytes"] -= len(data)
    frame.stack.append(int(len(data)))


def java_io_FileInputStream_available___I(frame, args):
    fis = frame.vm.heap[args[0][1]]
    if "@available_bytes" in fis.fields:
        frame.stack.append(fis.fields["@available_bytes"])
    else:
        frame.stack.append(0)


def java_io_FileInputStream_close0___V(frame, args):
    fis = frame.vm.heap[args[0][1]]
    f = fis.fields["@file"]
    f.close()

########NEW FILE########
__FILENAME__ = fileoutputstream
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

import os

from pyjvm.utils import str_to_string


def java_io_FileOutputStream_initIDs___V(frame, args):
    # do nothing
    pass


def java_io_FileOutputStream_open__Ljava_lang_String_Z_V(frame, args):
    if args[1] is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    fis = frame.vm.heap[args[0][1]]
    ref = args[1]
    file_name = str_to_string(frame.vm, ref)
    append_flag = args[2]
    assert append_flag == 0, "File append is not yet here"
    if not os.path.isfile(file_name):
        frame.vm.raise_exception(frame, "java/io/FileNotFoundException")
        return
    size = os.path.getsize(file_name)
    f = open(file_name, 'wb')
    fis.fields["@file"] = f
    fis.fields["@available_bytes"] = size


def java_io_FileOutputStream_writeBytes___BIIZ_V(frame, args):
    if args[1] is None:
        frame.vm.raise_exception(frame, "java/lang/NullPointerException")
        return
    fos = frame.vm.heap[args[0][1]]
    buf = frame.vm.heap[args[1][1]]
    offset = args[2]
    length = args[3]
    append_flag = args[4]
    assert append_flag == 0, "File append is not yet here"
    f = fos.fields["@file"]
    f.write(bytearray(buf.values[offset:length]))


def java_io_FileOutputStream_close0___V(frame, args):
    fos = frame.vm.heap[args[0][1]]
    f = fos.fields["@file"]
    f.close()

########NEW FILE########
__FILENAME__ = filesystem
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

from pyjvm.vmo import VM_OBJECTS


def java_io_FileSystem_getFileSystem___Ljava_io_FileSystem_(frame, args):
    '''Return VMO object reference'''
    frame.stack.append(('vm_ref', VM_OBJECTS['FileSystem']))

########NEW FILE########
__FILENAME__ = clazz
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

#
# NOT FULLY IMPLEMENTED!!!!
# JUST ENOUGHT TO MAKE IT WORK
#
# Constructor paremeters always empty
#

import logging

from pyjvm.jvmo import JArray
from pyjvm.jvmo import JavaClass
from pyjvm.prim import PRIMITIVES
from pyjvm.utils import arr_to_string, str_to_string

from pyjvm.ops.ops_cond import checkcast

logger = logging.getLogger(__name__)


def java_lang_Class_getName0___Ljava_lang_String_(frame, args):
    ref = args[0]
    assert type(ref) is tuple
    klass_klass = frame.vm.heap[ref[1]]
    klass_name = klass_klass.fields["@CLASS_NAME"]
    assert klass_name is not None
    klass_name = klass_name.replace("/", ".")
    result = frame.vm.make_heap_string(klass_name)
    frame.stack.append(result)


def java_lang_Class_getClassLoader0___Ljava_lang_ClassLoader_(frame, args):
    ref = args[0]
    assert type(ref) is tuple
    frame.stack.append(None)  # always bootstrap


def java_lang_Class_desiredAssertionStatus0__Ljava_lang_Class__Z(frame, args):
    frame.stack.append(0)


def java_lang_Class_getPrimitiveClass__Ljava_lang_String__Ljava_lang_Class_(frame, args):
    ref = args[0]
    assert type(ref) is tuple and ref[0] == "ref"
    instance = frame.vm.heap[ref[1]]
    assert instance.java_class.this_name == "java/lang/String"
    value_ref = instance.fields["value"]
    value = arr_to_string(frame.vm.heap[value_ref[1]].values)
    jc = frame.vm.get_class(value)
    frame.stack.append(jc.heap_ref)


def java_lang_Class_isInterface___Z(frame, args):
    ref = args[0]
    assert type(ref) is tuple and ref[0] == "ref"
    o = frame.vm.heap[ref[1]]
    klass_name = o.fields["@CLASS_NAME"]
    klass = frame.vm.get_class(klass_name)
    if klass.is_interface:
        frame.stack.append(1)
    else:
        frame.stack.append(0)


def java_lang_Class_isPrimitive___Z(frame, args):
    ref = args[0]
    assert type(ref) is tuple and ref[0] == "ref"
    o = frame.vm.heap[ref[1]]
    klass_name = o.fields["@CLASS_NAME"]
    klass = frame.vm.get_class(klass_name)
    if klass.is_primitive:
        frame.stack.append(1)
    else:
        frame.stack.append(0)


def java_lang_Class_getModifiers___I(frame, args):
    flag = 0x0001
    frame.stack.append(flag)


def java_lang_Class_getSuperclass___Ljava_lang_Class_(frame, args):
    ref = args[0]
    assert type(ref) is tuple and ref[0] == "ref"
    o = frame.vm.heap[ref[1]]
    klass_name = o.fields["@CLASS_NAME"]
    klass = frame.vm.get_class(klass_name)
    if klass.this_name == "java/lang/Object":
        frame.stack.append(None)
        return
    s_klass = klass.super_class
    frame.stack.append(s_klass.heap_ref)


def java_lang_Class_getDeclaredConstructors0__Z__Ljava_lang_reflect_Constructor_(frame, args):
    ref = args[0]
    assert type(ref) is tuple and ref[0] == "ref"
    o = frame.vm.heap[ref[1]]
    klass_name = o.fields["@CLASS_NAME"]
    klass = frame.vm.get_class(klass_name)
    c_klass = frame.vm.get_class("java/lang/reflect/Constructor")
    cons = []

    if "<init>" in klass.methods:
        for m in klass.methods["<init>"]:
            c = c_klass.get_instance(frame.vm)
            c.fields["clazz"] = klass.heap_ref
            sign_ref = frame.vm.make_heap_string(m)
            c.fields["signature"] = sign_ref
            cref = frame.vm.add_to_heap(c)
            array_class = frame.vm.get_class("[Ljava/lang/Class;")
            params = JArray(array_class, frame.vm)
            params_ref = frame.vm.add_to_heap(params)
            c.fields["parameterTypes"] = params_ref
            cons.append(cref)
    array_class = frame.vm.get_class("[Ljava/lang/reflect/Constructor;")
    heap_item = JArray(array_class, frame.vm)
    heap_item.values = cons
    ref = frame.vm.add_to_heap(heap_item)
    frame.stack.append(ref)


def java_lang_Class_isArray___Z(frame, args):
    ref = args[0]
    assert type(ref) is tuple and ref[0] == "ref"
    o = frame.vm.heap[ref[1]]
    klass_name = o.fields["@CLASS_NAME"]
    klass = frame.vm.get_class(klass_name)
    if klass.is_array:
        frame.stack.append(1)
    else:
        frame.stack.append(0)


def java_lang_Class_forName0__Ljava_lang_String_ZLjava_lang_ClassLoader__Ljava_lang_Class_(frame, args):
    ref = args[0]
    assert type(ref) is tuple and ref[0] == "ref"
    name = str_to_string(frame.vm, ref)
    name = name.replace(".", "/")
    klass = frame.vm.get_class(name)
    ref = frame.vm.get_class_class(klass)
    frame.stack.append(ref)


def java_lang_Class_getDeclaredFields0__Z__Ljava_lang_reflect_Field_(frame, args):
    ref = args[0]
    assert type(ref) is tuple and ref[0] == "ref"
    o = frame.vm.heap[ref[1]]
    klass_name = o.fields["@CLASS_NAME"]
    klass = frame.vm.get_class(klass_name)
    field_klass = frame.vm.get_class("java/lang/reflect/Field")
    fields = []
    for field_name in klass.member_fields:
        field = field_klass.get_instance(frame.vm)
        name_ref = frame.vm.make_heap_string(field_name)
        field.fields["name"] = name_ref
        field.fields["clazz"] = klass.heap_ref
        field._name = field_name
        fref = frame.vm.add_to_heap(field)
        fields.append(fref)
    array_class = frame.vm.get_class("[Ljava/lang/reflect/Field;")
    heap_item = JArray(array_class, frame.vm)
    heap_item.values = fields
    ref = frame.vm.add_to_heap(heap_item)
    frame.stack.append(ref)


def java_lang_Class_isAssignableFrom__Ljava_lang_Class__Z(frame, args):
    # TODO NPE
    ref_o = args[0]
    ref_x = args[1]
    o = frame.vm.heap[ref_o[1]]
    o_klass = frame.vm.get_class(o.fields["@CLASS_NAME"])
    x = frame.vm.heap[ref_x[1]]
    x_klass = frame.vm.get_class(x.fields["@CLASS_NAME"])
    if checkcast(x_klass, o_klass, frame.vm):
        frame.stack.append(1)
    else:
        frame.stack.append(0)


def java_lang_Class_getComponentType___Ljava_lang_Class_(frame, args):
    o = frame.vm.heap[args[0][1]]
    c_name = o.fields["@CLASS_NAME"]
    assert c_name[0] == "["
    c_name = c_name[1:]
    if c_name in PRIMITIVES:
        c_name = PRIMITIVES[c_name]
    klass = frame.vm.get_class(c_name)
    frame.stack.append(klass.heap_ref)

########NEW FILE########
__FILENAME__ = double
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

import struct


def java_lang_Double_doubleToRawLongBits__D_J(frame, args):
    value = args[0]
    assert type(value) is tuple
    assert value[0] == "double"
    packed = struct.pack('>d', value[1])
    packed = struct.unpack('>q', packed)[0]  # IEEE 754 floating-point
    frame.stack.append(("long", packed))


def java_lang_Double_longBitsToDouble__J_D(frame, args):
    value = args[0]
    assert type(value) is tuple
    assert value[0] == "long"
    packed = struct.pack('>q', value[1])
    packed = struct.unpack('>d', packed)[0]  # IEEE 754 floating-point
    frame.stack.append(("double", packed))

########NEW FILE########
__FILENAME__ = float
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

import struct


def java_lang_Float_floatToRawIntBits__F_I(frame, args):
    value = args[0]
    assert type(value) is tuple
    assert value[0] == "float"
    packed = struct.pack('>f', value[1])
    packed = struct.unpack('>i', packed)[0]  # IEEE 754 floating-point
    frame.stack.append(packed)

########NEW FILE########
__FILENAME__ = object
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

from pyjvm.jvmo import JArray
from pyjvm.thread import SkipThreadCycle


def java_lang_Object_getClass___Ljava_lang_Class_(frame, args):
    assert len(args) > 0
    assert type(args[0]) is tuple
    assert args[0][0] == "ref" and args[0][1] > 0
    o = frame.vm.heap[args[0][1]]
    klass = o.java_class
    ref = frame.vm.get_class_class(klass)
    frame.stack.append(ref)


def java_lang_Object_hashCode___I(frame, args):
    assert type(args[0]) is tuple
    frame.stack.append(args[0][1])  # address in heap is object's hash


def java_lang_Object_wait__J_V(frame, args):
    ref = args[0]
    waiting_time = args[1]
    assert ref is not None
    # NPE
    o = frame.vm.heap[ref[1]]
    assert o is not None
    t = frame.thread

    if t.is_notified:
        t.waiting_notify = False
        if "@monitor" in o.fields:
            frame.stack.append(ref)
            frame.stack.append(waiting_time)
            raise SkipThreadCycle()
        else:
            o.waiting_list.remove(t)
            o.fields["@monitor"] = t
            o.fields["@monitor_count"] = t.monitor_count_cache
            t.is_notified = False
            return

    if t.waiting_notify:
        if t.sleep_until > 0:
            now = int(time.time()) * 1000
            if now <= t.sleep_until:
                if "@monitor" in o.fields:
                    frame.stack.append(ref)
                    frame.stack.append(waiting_time)
                    raise SkipThreadCycle()
                else:
                    o.waiting_list.remove(t)
                    o.fields["@monitor"] = t
                    o.fields["@monitor_count"] = t.monitor_count_cache
                    t.is_notified = False
                    t.waiting_notify = False
                    return
        frame.stack.append(ref)
        frame.stack.append(waiting_time)
        raise SkipThreadCycle()
    else:
        assert "@monitor" in o.fields
        assert o.fields["@monitor"] == frame.thread
        o.waiting_list.append(t)
        t.waiting_notify = True
        if waiting_time[1] > 0:
            now = int(time.time()) * 1000
            t.sleep_until = now + waiting_time[1]
        t.monitor_count_cache = o.fields["@monitor_count"]
        del o.fields["@monitor"]
        del o.fields["@monitor_count"]
        frame.stack.append(ref)
        frame.stack.append(waiting_time)
        raise SkipThreadCycle()


def java_lang_Object_clone___Ljava_lang_Object_(frame, args):
    # TODO NPE
    o = frame.vm.heap[args[0][1]]
    if o.java_class.is_array:
        clone = JArray(o.java_class, frame.vm)
        clone.values = o.values[:]
        ref = frame.vm.add_to_heap(clone)
        frame.stack.append(ref)
    else:
        clone = o.java_class.get_instance(frame.vm)
        clone.fields = o.fields.copy()
        ref = frame.vm.add_to_heap(clone)
        frame.stack.append(ref)

########NEW FILE########
__FILENAME__ = runtime
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''


def java_lang_Runtime_freeMemory___J(frame, args):
    frame.stack.append(("long", 1024*1024))


def java_lang_Runtime_availableProcessors___I(frame, args):
    frame.stack.append(1)

########NEW FILE########
__FILENAME__ = string
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

from pyjvm.utils import arr_to_string


def java_lang_String_intern___Ljava_lang_String_(frame, args):
    ref = args[0]
    assert type(ref) is tuple and ref[0] == "ref"
    o = frame.vm.heap[ref[1]]
    ref = o.fields["value"]
    o = frame.vm.heap[ref[1]]  # this is JArray
    s = arr_to_string(o.values)
    ref = frame.vm.make_heap_string(s)
    frame.stack.append(ref)

########NEW FILE########
__FILENAME__ = system
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

import time
import logging

from pyjvm.frame import Frame
from pyjvm.jassert import jassert_array
from pyjvm.thread import Thread

logger = logging.getLogger(__name__)


def java_lang_System_nanoTime___J(frame, args):
    nano = long(time.time()) * 1000
    logger.debug("System.nanoTime: " + str(nano))
    frame.stack.append(("long", nano))


def java_lang_System_currentTimeMillis___J(frame, args):
    currentTime = long(time.time()) * 1000
    logger.debug("System.currentTimeMillis: " + str(currentTime))
    frame.stack.append(("long", currentTime))


def java_lang_System_identityHashCode__Ljava_lang_Object__I(frame, args):
    ref = args[0]
    if ref is None:
        frame.stack.append(0)
        return
    assert type(ref) is tuple
    assert ref[0] == "ref"

    o = frame.vm.heap[ref[1]]
    klass = o.java_class
    method = klass.find_method("hashCode", "()I")

    if method[0] & 0x0100 > 0:
        # assuming native call to object's hashCode, get heap id
        frame.stack.append(ref[1])
        return

    pvm_thread = Thread(frame.vm, frame.vm.top_thread_ref)
    pvm_thread.is_alive = True
    m_args = [None]*method[1]
    m_args[0] = ref
    sub = Frame(pvm_thread, klass, method, m_args,
                "call get hashCode")
    pvm_thread.frame_stack.append(sub)
    frame.vm.run_thread(pvm_thread)
    assert sub.has_result
    frame.stack.append(sub.ret)


def java_lang_System_arraycopy__Ljava_lang_Object_ILjava_lang_Object_II_V(frame, args):
    #ref1, index1, ref2, index2, length
    count = args[4]
    index2 = args[3]
    ref2 = args[2]
    index1 = args[1]
    ref1 = args[0]
    assert type(count) is int
    assert type(index1) is int
    assert type(index2) is int
    assert type(ref1) is tuple and ref1[0] == "ref"
    assert type(ref2) is tuple and ref2[0] == "ref"
    arr1 = frame.vm.heap[ref1[1]]
    arr2 = frame.vm.heap[ref2[1]]
    jassert_array(arr1)
    jassert_array(arr2)
    # TODO NPE
    arr2.values[index2:index2 + count] = arr1.values[index1:index1 + count]

########NEW FILE########
__FILENAME__ = thread
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

import time

from pyjvm.frame import Frame
from pyjvm.thread import SkipThreadCycle
from pyjvm.thread import Thread


def java_lang_Thread_currentThread___Ljava_lang_Thread_(frame, args):
    ref = frame.thread.java_thread
    frame.stack.append(ref)


def java_lang_Thread_setPriority0__I_V(frame, args):
    pass  # just ignore


def java_lang_Thread_isAlive___Z(frame, args):
    ref = args[0]
    t = frame.vm.heap[ref[1]]
    if "@pvm_thread" in t.fields:
        if t.fields["@pvm_thread"].is_alive:
            frame.stack.append(1)
            return
    frame.stack.append(0)


def java_lang_Thread_start0___V(frame, args):
    '''Create new thread with one's void run()
    see thread.txt for details
    '''
    t_ref = args[0]
    o = frame.vm.heap[t_ref[1]]
    run = o.java_class.find_method("run", "()V")
    assert run is not None

    pvm_thread = Thread(frame.vm, t_ref)
    pvm_thread.is_alive = True
    m_args = [None] * run[1]
    m_args[0] = t_ref
    sub = Frame(pvm_thread, o.java_class, run, m_args, "Thread")
    pvm_thread.frame_stack.append(sub)
    frame.vm.add_thread(pvm_thread)


def java_lang_Thread_sleep__J_V(frame, args):
    '''Sleep until certain time'''
    if frame.thread.sleep_until == 0:
        now = int(time.time()) * 1000
        sleepMillis = args[0][1]
        threshold = now + sleepMillis
        frame.thread.sleep_until = threshold
        frame.pc -= 3  # no need !!!!!!!!!!!!!!!!!!!!!!!!!
        frame.stack.append(args[0])
        raise SkipThreadCycle()
    else:
        now = int(time.time()) * 1000
        if frame.thread.sleep_until > now:
            frame.pc -= 3  # no need !!!!!!!!!!!!!!!!!!!!!!!!!
            frame.stack.append(args[0])
            raise SkipThreadCycle()
        else:
            frame.thread.sleep_until = 0
            pass

########NEW FILE########
__FILENAME__ = throwable
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''


def java_lang_Throwable_fillInStackTrace__I_Ljava_lang_Throwable_(frame, args):
    ref = args[0]
    assert type(ref) is tuple and ref[0] == "ref"
    #todo real job
    frame.stack.append(ref)

########NEW FILE########
__FILENAME__ = accesscontroller
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

from pyjvm.frame import Frame


def java_security_AccessController_getStackAccessControlContext___Ljava_security_AccessControlContext_(frame, args):
    frame.stack.append(None)


def java_security_AccessController_doPrivileged__Ljava_security_PrivilegedAction__Ljava_lang_Object_(frame, args):
    ref = args[0]
    assert type(ref) is tuple and ref[0] == "ref"
    o = frame.vm.heap[ref[1]]
    klass = o.java_class
    method = klass.find_method("run", "()Ljava/lang/Object;")
    args = [None]*method[1]
    args[0] = ref
    sub = Frame(frame.thread, klass, method, args,
                "RUN call in java_security_AccessController_doPrivileged")
    frame.thread.frame_stack.append(sub)


def java_security_AccessController_doPrivileged__Ljava_security_PrivilegedExceptionAction__Ljava_lang_Object_(frame, args):
    ref = args[0]
    assert type(ref) is tuple and ref[0] == "ref"
    o = frame.vm.heap[ref[1]]
    klass = o.java_class
    method = klass.find_method("run", "()Ljava/lang/Object;")
    assert method is not None
    args = [None]*method[1]
    args[0] = ref
    sub = Frame(frame.thread, klass, method, args,
                "RUN call in java_security_AccessController_doPrivileged")
    frame.thread.frame_stack.append(sub)

########NEW FILE########
__FILENAME__ = unsafe
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

import struct

from pyjvm.utils import str_to_string


def sun_misc_Unsafe_arrayBaseOffset__Ljava_lang_Class__I(frame, args):
    frame.stack.append(0)


def sun_misc_Unsafe_arrayIndexScale__Ljava_lang_Class__I(frame, args):
    frame.stack.append(1)


def sun_misc_Unsafe_addressSize___I(frame, args):
    frame.stack.append(4)


def java_util_concurrent_atomic_AtomicLong_VMSupportsCS8___Z(frame, args):
    frame.stack.append(1)


def sun_misc_Unsafe_objectFieldOffset__Ljava_lang_reflect_Field__J(frame, args):
    ref = args[1]
    assert type(ref) is tuple and ref[0] == "ref"
    field = frame.vm.heap[ref[1]]
    name = str_to_string(frame.vm, field.fields["name"])
    k_ref = field.fields["clazz"]
    klass_object = frame.vm.heap[k_ref[1]]
    klass = frame.vm.get_class(klass_object.fields["@CLASS_NAME"])
    o = klass.get_instance(frame.vm)
    index = 0
    for key in o.fields:
        if key == name:
            frame.stack.append(("long", index))
            return
        index += 1
    assert False  # should never get here


def sun_misc_Unsafe_compareAndSwapLong__Ljava_lang_Object_JJJ_Z(frame, args):
    ref = args[1]
    offset = args[2]
    expected = args[4]
    x = args[6]
    assert type(ref) is tuple and ref[0] == "ref"
    assert type(offset) is tuple and offset[0] == "long"
    assert type(expected) is tuple and expected[0] == "long"
    assert type(x) is tuple and x[0] == "long"
    o = frame.vm.heap[ref[1]]
    index = 0
    name = None
    for field in o.fields:
        if index == offset[1]:
            name = field
        index += 1
    assert name is not None
    if o.fields[name] == expected:
        o.fields[name] = x
        frame.stack.append(1)
    else:
        frame.stack.append(0)


def sun_misc_Unsafe_compareAndSwapInt__Ljava_lang_Object_JII_Z(frame, args):
    ref = args[1]
    offset = args[2]
    expected = args[4]
    x = args[5]
    assert type(ref) is tuple and ref[0] == "ref"
    assert type(offset) is tuple and offset[0] == "long"
    assert type(expected) is int
    assert type(x) is int
    o = frame.vm.heap[ref[1]]
    index = 0
    name = None
    for field in o.fields:
        if index == offset[1]:
            name = field
        index += 1
    assert name is not None
    if o.fields[name] == expected:
        o.fields[name] = x
        frame.stack.append(1)
    else:
        frame.stack.append(0)


memory = {}


def sun_misc_Unsafe_allocateMemory__J_J(frame, args):
    global memory
    l = args[1]
    assert type(l) is tuple and l[0] == "long"
    chunk = [0]*l[1]
    index = 1  # bad
    while index in memory:
        index += 1
    memory[index] = chunk
    frame.stack.append(("long", index))


def sun_misc_Unsafe_putLong__JJ_V(frame, args):
    global memory
    address = args[1]
    value = args[3]
    assert type(address) is tuple and address[0] == "long"
    assert type(value) is tuple and value[0] == "long"
    chunk = memory[address[1]]
    bytes = struct.pack(">q", value[1])
    chunk[0:8] = bytes[0:8]


def sun_misc_Unsafe_getByte__J_B(frame, args):
    global memory
    address = args[1]
    assert type(address) is tuple and address[0] == "long"
    chunk = memory[address[1]]
    b = struct.unpack(">b", chunk[0])[0]
    frame.stack.append(b)


def sun_misc_Unsafe_freeMemory__J_V(frame, args):
    global memory
    address = args[1]
    assert type(address) is tuple and address[0] == "long"
    del memory[address[1]]


def sun_misc_Unsafe_putOrderedObject__Ljava_lang_Object_JLjava_lang_Object__V(frame, args):
    ref_o = args[1]
    index = args[2][1]  # from long
    ref_x = args[4]
    o = frame.vm.heap[ref_o[1]]
    if o.java_class.is_array:
        o.values[index] = ref_x
    else:
        for field in o.fields:
            if index == 0:
                name = field
            index -= 1
        assert name is not None
        o.fields[name] = ref_x


def sun_misc_Unsafe_getObject__Ljava_lang_Object_J_Ljava_lang_Object_(frame, args):
    ref_o = args[1]
    index = args[2][1]  # from long
    o = frame.vm.heap[ref_o[1]]
    assert o.java_class.is_array
    frame.stack.append(o.values[index])


def sun_misc_Unsafe_getObjectVolatile__Ljava_lang_Object_J_Ljava_lang_Object_(frame, args):
    ref_o = args[1]
    index = args[2][1]  # from long
    o = frame.vm.heap[ref_o[1]]
    assert o.java_class.is_array
    frame.stack.append(o.values[index])


def sun_misc_Unsafe_compareAndSwapObject__Ljava_lang_Object_JLjava_lang_Object_Ljava_lang_Object__Z(frame, args):
    ref_o = args[1]
    offset = args[2][1]  # long value
    ref_expected = args[4]
    ref_x = args[5]
    o = frame.vm.heap[ref_o[1]]
    assert o.java_class.is_array
    if o.values[offset] == ref_expected:
        o.values[offset] = ref_x
        frame.stack.append(1)
    else:
        frame.stack.append(0)

########NEW FILE########
__FILENAME__ = vm
def sun_misc_VM_initialize___V(frame, args):
    pass

########NEW FILE########
__FILENAME__ = nativeconstructoraccessorimpl
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''

from pyjvm.frame import Frame
from pyjvm.thread import Thread
from pyjvm.utils import str_to_string


def sun_reflect_NativeConstructorAccessorImpl_newInstance0__Ljava_lang_reflect_Constructor__Ljava_lang_Object__Ljava_lang_Object_(frame, args):
    '''Create instance of a class, with constructor call'''
    ref = args[0]
    params = args[1]
    assert type(ref) is tuple and ref[0] == "ref"
    assert params is None or len(params) == 0
    o = frame.vm.heap[ref[1]]
    klass_klass = frame.vm.heap[o.fields["clazz"][1]]
    clazz = frame.vm.get_class(klass_klass.fields["@CLASS_NAME"])
    signature = str_to_string(frame.vm, o.fields["signature"])
    assert signature == "()V"
    instance = clazz.get_instance(frame.vm)
    iref = frame.vm.add_to_heap(instance)
    frame.stack.append(iref)
    method = clazz.find_method("<init>", signature)

    # actully running constructor in exclusive mode
    pvm_thread = Thread(frame.vm, frame.vm.top_thread_ref)
    pvm_thread.is_alive = True
    m_args = [None]*method[1]
    m_args[0] = iref
    sub = Frame(pvm_thread, clazz, method, m_args, "nativ instance0")
    pvm_thread.frame_stack.append(sub)
    frame.vm.run_thread(pvm_thread)

########NEW FILE########
__FILENAME__ = reflection
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''See natives.txt in documentation'''


def sun_reflect_Reflection_getCallerClass___Ljava_lang_Class_(frame, args):
    caller_frame = frame.thread.frame_stack[
        len(frame.thread.frame_stack) - 2]
    klass = caller_frame.this_class
    ref = frame.vm.get_class_class(klass)
    frame.stack.append(ref)


def sun_reflect_Reflection_getClassAccessFlags__Ljava_lang_Class__I(frame, args):
    flag = 0x0001
    frame.stack.append(flag)

########NEW FILE########
__FILENAME__ = prim
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Mapping between JDK type id and class name"""


PRIMITIVES = {'B': 'byte', 'C': 'char', 'D': 'double',
              'F': 'float', 'I': 'int', 'J': 'long', 'S': 'short',
              'Z': 'boolean'}

########NEW FILE########
__FILENAME__ = thread
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''JMV threads'''


class Thread(object):
    '''JMV thread.
    See threads.txt in documentation for details.
    '''

    def __init__(self, _vm, _java_thread):
        '''Init pyjvm thread
        _vm reference to current vm
        _java_thread reference to java's Thread instance in heap
        '''
        # One frame per method invocation
        self.frame_stack = []
        self.vm = _vm
        # Support looping for multi-threaded apps
        self.next_thread = None
        self.prev_thread = None
        # Reference to java's Thread instances
        self.java_thread = _java_thread
        self.is_alive = False
        self.waiting_notify = False
        self.is_notified = False
        self.monitor_count_cache = 0
        # For sleep(long) support
        self.sleep_until = 0
        if _java_thread is not None:
            obj = _vm.heap[_java_thread[1]]
            obj.fields["@pvm_thread"] = self


class SkipThreadCycle(Exception):
    '''Thread may skip his execution quota in case when a monitor
    is busy or sleep was called
    '''
    pass

########NEW FILE########
__FILENAME__ = throw
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java Exception'''


class JavaException(Exception):
    '''PY excpetion.

    Real heap reference is stored in ref
    '''

    def __init__(self, _vm, _ref):
        self.vm = _vm
        self.ref = _ref
        self.stack = []

    def __str__(self):
        ex = self.vm.heap[self.ref[1]]
        return str(ex)

########NEW FILE########
__FILENAME__ = utils
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Common utils"""


def arr_to_string(str_arr):
    '''Convert string's array to real unicode string'''
    result_string = ""
    for char_ in str_arr:
        result_string += str(unichr(char_))
    return result_string


def str_to_string(vm, ref):
    '''Convert java string reference to unicode'''
    if ref is None:
        return "NULL"
    heap_string = vm.heap[ref[1]]
    value_ref = heap_string.fields["value"]
    value = vm.heap[value_ref[1]]  # this is array of chars
    return arr_to_string(value.values)


def args_count(desc):
    '''Get arguments count from method signature string
    e.g. ()V - 0; (II)V - 2 (two int params)
    '''
    count = _args_count(desc[1:])
    return count


def _args_count(desc):
    '''Recursive parsing for method signuture'''
    char_ = desc[0]
    if char_ == ")":
        return 0
    if char_ in ["B", "C", "F", "I", "S", "Z"]:
        return 1 + _args_count(desc[1:])
    if char_ in ["J", "D"]:
        return 2 + _args_count(desc[1:])
    if char_ == "L":
        return 1 + _args_count(desc[desc.index(";") + 1:])
    if char_ == "[":
        return _args_count(desc[1:])
    raise Exception("Unknown type def %s", str(char_))


def default_for_type(desc):
    '''Get default value for specific type'''
    if desc == "I":
        return 0
    elif desc == "J":  # long
        return ("long", 0)
    elif desc[0] == "[":  # array
        return None
    elif desc[0] == 'L':  # object
        return None
    elif desc == 'Z':  # boolean
        return 0
    elif desc == 'D':  # double
        return ("double", 0.0)
    elif desc == 'F':  # float
        return ("float", 0.0)
    elif desc == 'C':  # char
        return 0
    elif desc == 'B':  # boolean
        return 0
    raise Exception("Default value not yet supported for " + desc)


def category_type(value):
    '''Get category type of a variable according to jdk specs

    long, double are 2, others are 1'''
    if type(value) is tuple and value[0] in ('long', 'double'):
        return 2
    else:
        return 1

########NEW FILE########
__FILENAME__ = vm
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Java Virtual Machine.
Initialization, threads, frame management.
'''

import logging
from collections import deque

from pyjvm.bytecode import get_operation, get_operation_name
from pyjvm.class_loader import class_loader
from pyjvm.class_path import read_class_path
from pyjvm.frame import Frame
from pyjvm.jvmo import array_class_factory
from pyjvm.jvmo import JArray
from pyjvm.jvmo import JavaClass
from pyjvm.thread import Thread
from pyjvm.thread import SkipThreadCycle

from pyjvm.throw import JavaException

from pyjvm.vmo import VM_OBJECTS

from pyjvm.ops.ops_names import ops_name
from pyjvm.ops.ops_arrays import *
from pyjvm.ops.ops_calc import *
from pyjvm.ops.ops_cond import *
from pyjvm.ops.ops_convert import *
from pyjvm.ops.ops_fields import *
from pyjvm.ops.ops_invokespecial import *
from pyjvm.ops.ops_invokestatic import *
from pyjvm.ops.ops_invokevirtual import *
from pyjvm.ops.ops_invokeinterface import *
from pyjvm.ops.ops_misc import *
from pyjvm.ops.ops_ret import *
from pyjvm.ops.ops_setget import *
from pyjvm.ops.ops_shift import *

logger = logging.getLogger(__name__)


def vm_factory(class_path="."):
    '''Create JVM with specific class path'''
    return VM(class_path)


class VM(object):
    '''JVM implementation.
    See vm.txt in docs
    '''

    # Mark for vm caching
    serialization_id = 0
    initialized = False

    def __init__(self, _class_path="."):
        logger.debug("Creating VM")

        # Major memory structures
        self.perm_gen = {}
        self.heap = {}
        self.heap_next_id = 1
        #todo clean up self.cache_klass_klass = {}
        self.global_strings = {}

        # Handle for linked list of threads
        self.threads_queue = deque()
        self.non_daemons = 0

        self.top_group = None
        self.top_thread = None
        self.top_group_ref = None
        self.top_thread_ref = None

        self.class_path = read_class_path(_class_path)

        self.init_default_thread()

        # Load System and init major fields
        system_class = self.get_class("java/lang/System")

        # Set System.props to vm owned object
        system_class.static_fields["props"][1] = ("vm_ref",
                                                  VM_OBJECTS[
                                                      "System.Properties"])

        # STDout initialization using vm owned object
        ps_class = self.get_class("java/io/PrintStream")
        ps_object = ps_class.get_instance(self)
        ps_ref = self.add_to_heap(ps_object)
        method = ps_class.find_method("<init>", "(Ljava/io/OutputStream;)V")
        std_out_ref = ("vm_ref", VM_OBJECTS["Stdout.OutputStream"])
        thread = Thread(self, None)
        frame = Frame(thread, ps_class, method, [ps_ref, std_out_ref],
                      "PrintStream init")
        thread.frame_stack.append(frame)

        logger.debug("Run PrintStream init")
        self.run_thread(thread)  # Run exclusive thread
        system_class.static_fields["out"][1] = ps_ref

        system_class.static_fields["in"][1] = \
            ("vm_ref", VM_OBJECTS["Stdin.InputputStream"])

        # Additional parameters
        system_class.static_fields["lineSeparator"][1] = \
            self.make_heap_string("\n")

        # Load additional classes to speed up booting
        self.touch_classes()

        self.initialized = True

        logger.debug("VM created")

    def init_default_thread(self):
        '''Create initial thread group and thread.
        Both are java's objects
        '''
        tg_klass = self.get_class("java/lang/ThreadGroup")
        t_klass = self.get_class("java/lang/Thread")
        tg = tg_klass.get_instance(self)
        t = t_klass.get_instance(self)

        tg.fields["name"] = self.make_heap_string("system")
        tg.fields["maxPriority"] = 10
        t.fields["priority"] = 5
        t.fields["name"] = self.make_heap_string("system-main")
        t.fields["blockerLock"] = self.add_to_heap(
            self.get_class("java/lang/Object").get_instance(self))

        tg_ref = self.add_to_heap(tg)
        t_ref = self.add_to_heap(t)
        t.fields["group"] = tg_ref

        # Add thread to threadgroup; call byte code of void add(Thread)
        pvm_thread = Thread(self, t_ref)
        pvm_thread.is_alive = True
        method = tg_klass.find_method("add", "(Ljava/lang/Thread;)V")
        args = [None]*method[1]
        args[0] = tg_ref
        args[1] = t_ref
        frame = Frame(pvm_thread, tg_klass, method, args, "system tg init")
        pvm_thread.frame_stack.append(frame)
        self.run_thread(pvm_thread)

        self.top_group = tg
        self.top_thread = t
        self.top_group_ref = tg_ref
        self.top_thread_ref = t_ref

    def run_vm(self, main_klass, method, m_args):
        '''Run initialized vm with specific method of a class.
        This is class entered from command line. Method is looked up
        void main(String args[]).
        For more details see methods.txt in docs.
        '''
        t_klass = self.get_class("java/lang/Thread")
        t = t_klass.get_instance(self)
        t.fields["priority"] = 5
        t.fields["name"] = self.make_heap_string("main")
        t.fields["blockerLock"] = self.add_to_heap(
            self.get_class("java/lang/Object").get_instance(self))
        t_ref = self.add_to_heap(t)
        t.fields["group"] = self.top_group_ref

        pvm_thread = Thread(self, t_ref)
        pvm_thread.is_alive = True
        frame = Frame(pvm_thread, main_klass, method, m_args, "main")
        pvm_thread.frame_stack.append(frame)

        self.add_thread(pvm_thread)
        logger.debug("run thread pool")
        self.run_thread_pool()

    def get_class(self, class_name):
        '''Returns initialized class from pool (perm_gen) or loads
        it with class loader (and running static constructor).
        Getting a class might result in loading it's super first.
        '''
        if class_name is None:
            return  # this is look up for Object's super, which is  None
        if class_name in self.perm_gen:
            return self.perm_gen[class_name]
        if class_name[0] == '[':  # special treatment for arrays
            java_class = array_class_factory(self, class_name)
            lang_clazz = self.get_class("java/lang/Class")
            clazz_object = lang_clazz.get_instance(self)
            clazz_object.fields["@CLASS_NAME"] = class_name
            ref = self.add_to_heap(clazz_object)
            java_class.heap_ref = ref
            self.perm_gen[class_name] = java_class
            return java_class
        if class_name in ['byte', 'char', 'double', 'float', 'int', 'long',
                          'short', 'boolean']:
            java_class = JavaClass()
            self.perm_gen[class_name] = java_class
            java_class.is_primitive = True
            java_class.this_name = class_name
            lang_clazz = self.get_class("java/lang/Class")
            clazz_object = lang_clazz.get_instance(self)
            clazz_object.fields["@CLASS_NAME"] = class_name
            ref = self.add_to_heap(clazz_object)
            java_class.heap_ref = ref
            return java_class
        logger.debug("Class {0} not yet ready".format(class_name))
        java_class = class_loader(class_name, self.class_path)
        super_class = java_class.super_class
        if type(super_class) is unicode:  # lame check
            super_class = self.get_class(super_class)
            java_class.super_class = super_class
        logger.debug("Loaded class def\n{0}".format(java_class))
        self.perm_gen[class_name] = java_class
        # create actual java.lang.Class instance
        lang_clazz = self.get_class("java/lang/Class")
        clazz_object = lang_clazz.get_instance(self)
        clazz_object.fields["@CLASS_NAME"] = class_name
        ref = self.add_to_heap(clazz_object)
        java_class.heap_ref = ref
        self.run_static_constructor(java_class)
        return java_class

    def get_class_class(self, klass):
        '''Get class of class.
        Basically this is heap owned version of java.lang.Class
        '''
        return klass.heap_ref

    def run_static_constructor(self, java_class):
        '''Static constructor is run for every class loaded by class loader.
        It is executed in thread exclusive mode.
        '''
        logger.debug("Running static constructor for %s",
                     java_class.this_name)
        method = java_class.static_contructor()
        if method is None:
            logger.debug("No static constructor for %s",
                         java_class.this_name)
            return
        pvm_thread = Thread(self, self.top_thread_ref)
        pvm_thread.is_alive = True
        frame = Frame(pvm_thread, java_class, method, [None]*method[1],
                      "<clinit:{0}>".format(java_class.this_name))
        pvm_thread.frame_stack.append(frame)
        self.run_thread(pvm_thread)

        logger.debug("Finished with static constructor for %s",
                     java_class.this_name)

    def object_of_klass(self, o, klass_name):
        '''instanceOf implementation'''
        if o is None:
            return False
        if klass_name is None:
            return True
        klass = o.java_class
        while klass is not None:
            if klass_name == klass.this_name:
                return True
            klass = klass.super_class
        return False

    def add_to_heap(self, item):
        '''Put an item to java heap returning reference.
        Reference is in format ("ref", number)
        '''
        ref = self.heap_next_id
        self.heap[ref] = item
        self.heap_next_id += 1
        return ("ref", ref)

    def make_heap_string(self, value):
        '''Take python string and put java.lang.String instance to heap.
        String is represented by char array in background.
        Reference in heap is returned.
        Global caching is supported for all strings (same string always has
        same reference in heap)
        '''
        if value in self.global_strings:
            return self.global_strings[value]
        values = []
        for c in value:
            values.append(ord(c))
        array_class = self.get_class("[C")
        array = JArray(array_class, self)
        array.values = values
        arr_ref = self.add_to_heap(array)
        c = self.get_class("java/lang/String")
        o = c.get_instance(self)
        o.fields["value"] = arr_ref
        ref = self.add_to_heap(o)
        self.global_strings[value] = ref
        return ref

    def touch_classes(self):
        '''Touch some useful classes to speed up booting for cached vm'''
        self.get_class("java/lang/String")
        self.get_class("java/lang/Class")
        self.get_class("java/nio/CharBuffer")
        self.get_class("java/nio/HeapCharBuffer")
        self.get_class("java/nio/charset/CoderResult")
        self.get_class("java/nio/charset/CoderResult$1")
        self.get_class("java/nio/charset/CoderResult$Cache")
        self.get_class("java/nio/charset/CoderResult$2")

        thread_klass = self.get_class("java/lang/Thread")
        thread_klass.static_fields["MIN_PRIORITY"][1] = 1
        thread_klass.static_fields["NORM_PRIORITY"][1] = 5
        thread_klass.static_fields["MAX_PRIORITY"][1] = 10

    def add_thread(self, thread):
        '''Add py thread to pool'''
        self.threads_queue.append(thread)
        assert thread.java_thread is not None
        java_thread = self.heap[thread.java_thread[1]]
        if java_thread.fields["daemon"] == 0:
            self.non_daemons += 1

    def run_thread_pool(self):
        '''Run all threads.
        Threads are run one-by-one according to quota'''
        while len(self.threads_queue) > 0:
            thread = self.threads_queue.popleft()
            self.run_thread(thread, 100)
            if len(thread.frame_stack) == 0:
                thread.is_alive = False
                j_thread = self.heap[thread.java_thread[1]]
                assert j_thread is not None
                for o in j_thread.waiting_list:
                    o.is_notified = True
                java_thread = self.heap[thread.java_thread[1]]
                if java_thread.fields["daemon"] == 0:
                    self.non_daemons -= 1
                    if self.non_daemons == 0:
                        break
            else:
                self.threads_queue.append(thread)

    def run_thread(self, thread, quota=-1):
        '''Run single thread according to quota.
        Quota is number of byte codes to be executed.
        Quota -1 runs entire thread in exclusive mode.

        For each byte code specific operation function is called.
        Operation can throw exception.
        Thread may be busy (e.g. monitor is not available).
        Returns from syncronized methods are handled.
        '''
        frame_stack = thread.frame_stack
        while len(frame_stack) > 0:
            frame = frame_stack[-1]  # get current
            if frame.pc < len(frame.code):
                op = frame.code[frame.pc]
                frame.cpc = frame.pc
                frame.pc += 1
                # Make function name to be called
                op_call = hex(ord(op))

                logger.debug("About to execute {2}: op_{0} ({3}) in {1}".format(
                    op_call, frame.id, frame.pc - 1, get_operation_name(op_call)))
                
                opt = get_operation(op_call)
                if opt is None:
                    raise Exception("Op ({0}) is not yet supported".format(
                        op_call))
                try:
                    try:
                        opt(frame)
                        logger.debug("Stack:" + str(frame.stack))
                    except SkipThreadCycle:
                        # Thread is busy, call the same operation later
                        frame.pc = frame.cpc
                        break
                except JavaException as jexc:
                    # Exception handling
                    ref = jexc.ref
                    exc = self.heap[ref[1]]
                    handled = False
                    while not handled:
                        for (start_pc, end_pc, handler_pc, catch_type,
                             type_name) in frame.method[3]:
                            if start_pc <= frame.cpc < end_pc and \
                                    self.object_of_klass(exc, type_name):
                                frame.pc = handler_pc
                                frame.stack.append(ref)
                                handled = True
                                break
                        if handled:
                            break
                        frame_stack.pop()
                        if len(frame_stack) == 0:
                            raise
                        frame = frame_stack[-1]

            else:
                # Frame is done
                frame_stack.pop()
                if frame.monitor is not None:
                    assert frame.monitor.fields["@monitor"] == frame.thread
                    frame.monitor.fields["@monitor_count"] -= 1
                    if frame.monitor.fields["@monitor_count"] == 0:
                        del frame.monitor.fields["@monitor"]
                        del frame.monitor.fields["@monitor_count"]
                        frame.monitor = None
                # handle possible return VALUE
                if frame.has_result:
                    if len(frame_stack) > 0:
                        frame_stack[-1].stack.append(frame.ret)

            if quota != -1:
                quota -= 1
                if quota == 0:
                    break

    def raise_exception(self, frame, name):
        '''Util method to raise an exception based on name.
        e.g. java.lang.NullPointerException

        Exception is created on heap and throw op is called
        '''
        ex_klass = self.get_class(name)
        ex = ex_klass.get_instance(self)
        ref = self.add_to_heap(ex)

        method = ex_klass.find_method("<init>", "()V")
        m_args = [None]*method[1]
        m_args[0] = ref

        pvm_thread = Thread(self, None)
        pvm_thread.is_alive = True
        sub = Frame(pvm_thread, ex_klass, method, m_args, "exinit")
        pvm_thread.frame_stack.append(sub)
        self.run_thread(pvm_thread)

        frame.stack.append(ref)
        get_operation('0xbf')(frame)

########NEW FILE########
__FILENAME__ = vmo
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""VMO Virtual Machine owned objects.
These are instances of java classes handled by VM code instead of byte
code. These objects do not reside in heap. Their reference is
("vm_ref", x), where x < 0; versus normal heap owned objects:
("ref", y), y > 0
When a method is called on these vm owned instances, python code is
executed. This is different from handling native methods.

Example of vm owned object is STDOUT (print something on the screen).
"""

import os
import logging
import sys

from pyjvm.jassert import jassert_array
from pyjvm.utils import str_to_string

logger = logging.getLogger(__name__)

VM_OBJECTS = {
    "Stdout.OutputStream": -1,
    "System.Properties": -2,
    "JavaLangAccess": -3,
    "Stdin.InputputStream": -4,
    "FileSystem": -5
    }

VM_CLASS_NAMES = {
    -1: "java/io/OutputStream",
    -2: "java/util/Properties",
    -3: "sun/misc/JavaLangAccess",
    -4: "java/io/InputStream",
    -5: "java/io/FileSystem"
}


def vm_obj_call(frame, args, method_name, method_signature):
    '''Called by invoke method operations when instance ref is ("vm_ref", x).
    This methods converts call to function name defined in this file. It is
    executed (python code) instead of original byte code.
    '''
    ref = args[0]
    assert type(ref) is tuple
    assert ref[0] == "vm_ref"
    assert ref[1] < 0
    logger.debug("VM owned obj call: %s", ref[1])
    lookup_name = "vmo%s_%s_%s" % (ref[1] * -1, method_name, method_signature)
    lookup_name = lookup_name.replace("/", "_")
    lookup_name = lookup_name.replace("(", "_")
    lookup_name = lookup_name.replace(")", "_")
    lookup_name = lookup_name.replace("[", "_")
    lookup_name = lookup_name.replace(";", "_")
    lookup_name = lookup_name.replace(".", "_")
    if lookup_name not in globals():
        logger.error("VMOcall not implemented: %s:%s for %d", method_name,
                     method_signature, ref[1])
        raise Exception("Op ({0}) is not yet supported in vmo".format(
            lookup_name))
    globals()[lookup_name](frame, args)


def vmo_check_cast(vm, vmo_id, klass):
    '''check cast for specific vmo object

    vmo_id is less than zero, klass is JavaClass
    True if vmo is subclass of klass or implements interface klass
    '''
    this_klass = VM_CLASS_NAMES[vmo_id]
    klass_name = klass.this_name
    while klass is not None:
        if klass.this_name == this_klass:
            return True
        else:
            klass = klass.super_class
    vmo_klass = vm.get_class(this_klass)
    for i in vmo_klass.interfaces:
        if i == klass_name:
            return True
    return False


def vmo1_write___BII_V(frame, args):
    '''java.io.OutputStream
    void write(byte[] b, int off, int len)
    '''
    buf = args[1]
    offset = args[2]
    length = args[3]
    arr = frame.vm.heap[buf[1]]
    jassert_array(arr)
    chars = arr.values
    for index in range(offset, offset + length):
        sys.stdout.write(chr(chars[index]))


def vmo2_getProperty__Ljava_lang_String__Ljava_lang_String_(frame, args):
    '''java.lang.System
    public static String getProperty(String key)
    This is call to java.util.Properties object
    '''
    s_ref = args[1]
    value = str_to_string(frame.vm, s_ref)
    # refactor this code someday
    # ok for now, as all refs are cached
    props = {}
    props["file.encoding"] = frame.vm.make_heap_string("utf8")
    props["line.separator"] = frame.vm.make_heap_string("\n")
    if value in props:
        ref = props[value]
        assert type(ref) is tuple and ref[0] == "ref"
        frame.stack.append(ref)
        return
    frame.stack.append(None)


def vmo4_read___BII_I(frame, args):
    '''In will be truncated at 8k'''
    # TODO all exception checks
    ref = args[1]
    offset = args[2]
    length = args[3]
    o = frame.vm.heap[ref[1]]
    array = o.values

    c = sys.stdin.read(1)
    if c == '':
        frame.stack.append(-1)
    array[offset] = ord(c)
    if ord(c) == 10:
        frame.stack.append(1)
        return
    i = 1
    while i < length:
        c = sys.stdin.read(1)
        if c == '':
            break
        array[offset + i] = ord(c)
        i += 1
        if ord(c) == 10:
            break
    frame.stack.append(i)


def vmo4_available___I(frame, args):
    '''This is always zero. No support for buffering'''
    frame.stack.append(0)


def vmo4_read___I(frame, args):
    '''Read single byte'''
    c = sys.stdin.read(1)
    if c == '':
        frame.stack.append(-1)
    else:
        frame.stack.append(ord(c))


def vmo5_getSeparator___C(frame, args):
    '''Always slash'''
    frame.stack.append(ord('/'))


def vmo5_getPathSeparator___C(frame, args):
    '''Do not check operating system'''
    frame.stack.append(ord(':'))


def vmo5_normalize__Ljava_lang_String__Ljava_lang_String_(frame, args):
    '''Normalize according api rules'''
    s_ref = args[1]
    value = str_to_string(frame.vm, s_ref)
    norm = os.path.normpath(value)
    if value != norm:
        s_ref = frame.vm.make_heap_string(norm)
    frame.stack.append(s_ref)


def vmo5_prefixLength__Ljava_lang_String__I(frame, args):
    '''This is shortcut'''
    # s_ref = args[1]
    # value = str_to_string(frame.vm, s_ref)
    frame.stack.append(0)  # for now


def vmo5_getBooleanAttributes__Ljava_io_File__I(frame, args):
    '''See javadoc for details. Subset of all attributes is supported'''
    ref = args[1]
    assert ref is not None  # NPE
    o = frame.vm.heap[ref[1]]
    path_ref = o.fields['path']
    path = str_to_string(frame.vm, path_ref)
    result = 0
    if os.path.exists(path):
        result |= 0x01
        if not os.path.isfile(path):
            result |= 0x04
    frame.stack.append(result)

########NEW FILE########
__FILENAME__ = get_rt
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''rt.jar downloader.
For systems without java installed.
'''

import urllib2

# Dropbox content, this is rt.jar from JDK7
url = 'https://dl.dropboxusercontent.com/s/9wiumk3xvigqndi/rt.jar'

print "rt.jar from Java 7 is being downloaded"

u = urllib2.urlopen(url)
f = open('rt.jar', 'wb')
meta_info = u.info()
file_size = int(meta_info.getheaders("Content-Length")[0])
print "Total: %s mb" % (file_size/1024/1024)

downloaded = 0
block = 8192
print " [" + ("="*50) + "]"
while True:
    data = u.read(block)
    if not data:
        break

    downloaded += len(data)
    f.write(data)
    completed = downloaded * 100.0 / file_size
    arrow = "=" * int(completed/2.0)
    status = r"[%s] %3.0f%%" % (arrow, completed)
    status = status + chr(8)*(len(status)+1)
    print status,

f.close()

########NEW FILE########
__FILENAME__ = test_report
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Test results checker

Read text file created as a result of test_runner.py run
"""

import sys

if len(sys.argv) < 2:
    print "Run as:"
    print "test_report.py <REPORT_FILE>"
    print
    print "REPORT_FILE is result of running:"
    print "test_runner.py > <REPORT_FILE>"
    print
    sys.exit()

report_file = sys.argv[1]
report = None
with open(report_file, 'r') as report:
    data = report.read()

assert data is not None

TARGET_SCORE = 9
SCORE = 0


def verify(value, test_name):
    global SCORE
    global data
    if value in data:
        print test_name,
        print "\tOK"
        SCORE += 1
    else:
        print "***",
        print test_name,
        print "\tFAIL"


verify("[ARRAYSTEST:36/36]", "bytecode.ArraysTest")
verify("[CALCSTEST:29/29]", "bytecode.CalcsTest")
verify("[HASHES:2/2]", "langfeatures.Hashes")
verify("[INNERCLAZZ:1/1]", "langfeatures.InnerClazz")
verify("From 1000 daemon 9", "langfeatures.ThreadsDaemons")
verify("first base: 109 =*10: 1090", "langfeatures.ThreadsSync")
verify("second base: -93 =*10: -930", "langfeatures.ThreadsSync")
verify("[1, 2, 3, 4, 5]", "sorts.HeapSort")
verify("[FILEREADER.OK]", "io.FilePrint")

print
if SCORE == TARGET_SCORE:
    print "\t*** ALL TESTS ARE OK ***"
else:
    print "\t*** FAIL ***\t"
print

########NEW FILE########
__FILENAME__ = test_runner
# PyJVM (pyjvm.org) Java Virtual Machine implemented in pure Python
# Copyright (C) 2014 Andrew Romanenco (andrew@romanenco.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Run pyjvm test cases

    test_runnet.py > output.txt

then use test_report.py to verify results

Test runner creates VM instance in memory. For every test case VM is cloned.
Test cases are regular java classes, compiled for java 7.
"""

import copy
import logging
import os
import platform
import sys

logging.disable(logging.INFO)

sys.path.append('../.')

from pyjvm.vm import vm_factory

print
print "PyVJM test runner"
print

print "System information:"
print platform.platform()
print platform.version()
print

JAVA_HOME = os.environ.get('JAVA_HOME')
LOCAL_RT = os.path.isfile('../rt/rt.jar')
if JAVA_HOME is None and not LOCAL_RT:
    print "*** CAN NOT RUN TESTS ***"
    print "Set JAVA_HOME or init rt: see START.md for details"
    sys.exit()
print "Initializing Java Virtual Machine"
vm = vm_factory('../testcases/bin/')
print "VM is initialized"


def run(vm, klass_name):
    klass_name = klass_name.replace(".", "/")
    klass = vm.get_class(klass_name)
    main_method = klass.find_method("main", "([Ljava/lang/String;)V")
    m_args = [''] * main_method[1]
    vm.run_vm(klass, main_method, m_args)


print "TestCase1.Begin"
testcase = copy.deepcopy(vm)
run(testcase, "bytecode.CalcsTest")
print "TestCase1.End"
print

print "TestCase2.Begin"
testcase = copy.deepcopy(vm)
run(testcase, "bytecode.ArraysTest")
print "TestCase2.End"
print

print "TestCase3.Begin"
testcase = copy.deepcopy(vm)
run(testcase, "langfeatures.Hashes")
print "TestCase3.End"
print

print "TestCase4.Begin"
testcase = copy.deepcopy(vm)
run(testcase, "langfeatures.InnerClazz")
print "TestCase4.End"
print

print "TestCase5.Begin"
testcase = copy.deepcopy(vm)
run(testcase, "langfeatures.PrintOut")
print "TestCase5.End"
print

print "TestCase6.Begin"
testcase = copy.deepcopy(vm)
run(testcase, "langfeatures.ThreadsDaemons")
print "TestCase6.End"
print

print "TestCase7.Begin"
testcase = copy.deepcopy(vm)
run(testcase, "langfeatures.ThreadsSync")
print "TestCase7.End"
print

print "TestCase8.Begin"
testcase = copy.deepcopy(vm)
run(testcase, "sorts.HeapSort")
print "TestCase8.End"
print

print "TestCase9.Begin"
testcase = copy.deepcopy(vm)
run(testcase, "io.FilePrint")
print "TestCase9.End"
print


########NEW FILE########
