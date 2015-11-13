__FILENAME__ = Builtins
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from rpython.rlib import debug, jit, objectmodel, rarithmetic, rweakref
from rpython.rtyper.lltypesystem import lltype, rffi

NUM_BUILTINS = 41

from Core import *
import Bytecode, Target, VM




BUILTIN_NULL_OBJ = 0
BUILTIN_FAIL_OBJ = 1

# Core atom defs

BUILTIN_ATOM_DEF_OBJECT = 2
BUILTIN_SLOTS_ATOM_DEF_OBJECT = 3
BUILTIN_CLASS_ATOM_DEF_OBJECT = 4
BUILTIN_VM_ATOM_DEF_OBJECT = 5
BUILTIN_THREAD_ATOM_DEF_OBJECT = 6
BUILTIN_FUNC_ATOM_DEF_OBJECT = 7
BUILTIN_STRING_ATOM_DEF_OBJECT = 8
BUILTIN_CON_STACK_ATOM_DEF_OBJECT = 9
BUILTIN_LIST_ATOM_DEF_OBJECT = 10
BUILTIN_DICT_ATOM_DEF_OBJECT = 11
BUILTIN_MODULE_ATOM_DEF_OBJECT = 12
BUILTIN_INT_ATOM_DEF_OBJECT = 13
BUILTIN_UNIQUE_ATOM_DEF_OBJECT = 14
BUILTIN_CLOSURE_ATOM_DEF_OBJECT = 15
BUILTIN_PARTIAL_APPLICATION_ATOM_DEF_OBJECT = 16
BUILTIN_EXCEPTION_ATOM_DEF_OBJECT = 17
BUILTIN_SET_ATOM_DEF_OBJECT = 18

# Core classes

BUILTIN_OBJECT_CLASS = 19
BUILTIN_CLASS_CLASS = 20
BUILTIN_VM_CLASS = 21
BUILTIN_THREAD_CLASS = 22
BUILTIN_FUNC_CLASS = 23
BUILTIN_STRING_CLASS = 24
BUILTIN_CON_STACK_CLASS = 25
BUILTIN_LIST_CLASS = 26
BUILTIN_DICT_CLASS = 27
BUILTIN_MODULE_CLASS = 28
BUILTIN_INT_CLASS = 29
BUILTIN_CLOSURE_CLASS = 30
BUILTIN_PARTIAL_APPLICATION_CLASS = 31
BUILTIN_EXCEPTION_CLASS = 32
BUILTIN_SET_CLASS = 33
BUILTIN_NUMBER_CLASS = 34

BUILTIN_BUILTINS_MODULE = 35
BUILTIN_C_FILE_MODULE = 36
BUILTIN_EXCEPTIONS_MODULE = 37
BUILTIN_SYS_MODULE = 38

# Floats

BUILTIN_FLOAT_ATOM_DEF_OBJECT = 39
BUILTIN_FLOAT_CLASS = 40




################################################################################
# Con_Object
#

class Con_Object(Con_Thingy):
    __slots__ = ()


class Version(object):
    pass



# This map class is inspired by:
#   http://morepypy.blogspot.com/2011/03/controlling-tracing-of-interpreter-with_21.html

class _Con_Map(object):
    __slots__ = ("index_map", "other_maps")
    _immutable_fields_ = ("index_map", "other_maps")


    def __init__(self):
        self.index_map = {}
        self.other_maps = {}


    @jit.elidable
    def find(self, n):
        return self.index_map.get(n, -1)


    @jit.elidable
    def extend(self, n):
        if n not in self.other_maps:
            nm = _Con_Map()
            nm.index_map.update(self.index_map)
            nm.index_map[n] = len(self.index_map)
            self.other_maps[n] = nm
        return self.other_maps[n]



_EMPTY_MAP = _Con_Map()



class Con_Boxed_Object(Con_Object):
    __slots__ = ("instance_of", "slots_map", "slots")


    def __init__(self, vm, instance_of=None):
        if instance_of is None:
            self.instance_of = vm.get_builtin(BUILTIN_OBJECT_CLASS)
        else:
            self.instance_of = instance_of
        self.slots_map = _EMPTY_MAP
        self.slots = None


    def has_slot(self, vm, n):
        if self.slots is not None:
            m = jit.promote(self.slots_map)
            i = m.find(n)
            if i != -1:
                return True

        return False


    def find_slot(self, vm, n):
        o = None
        if self.slots is not None:
            m = jit.promote(self.slots_map)
            i = m.find(n)
            if i != -1:
                o = self.slots[i]
    
        if o is None:
            o = self.instance_of.find_field(vm, n)
            if o is None:
                if n == "instance_of":
                    o = self.instance_of
                if o is None:
                    return o

        if isinstance(o, Con_Func) and o.is_bound:
            return Con_Partial_Application(vm, o, [self])
        
        return o


    def get_slot(self, vm, n):
        o = None
        if self.slots is not None:
            m = jit.promote(self.slots_map)
            i = m.find(n)
            if i != -1:
                o = self.slots[i]
    
        if o is None:
            o = self.instance_of.find_field(vm, n)
            if o is None:
                if n == "instance_of":
                    o = self.instance_of
                if o is None:
                    vm.raise_helper("Slot_Exception", [Con_String(vm, n), self])

        if isinstance(o, Con_Func) and o.is_bound:
            return Con_Partial_Application(vm, o, [self])
        
        return o



    def set_slot(self, vm, n, o):
        assert o is not None
        m = jit.promote(self.slots_map)
        if self.slots is not None:
            i = m.find(n)
            if i == -1:
                self.slots_map = m.extend(n)
                self.slots.append(o)
            else:
                self.slots[i] = o
        else:
            self.slots_map = m.extend(n)
            self.slots = [o]


    def is_(self, o):
        return self is o


    def add(self, vm, o):
        return vm.get_slot_apply(self, "+", [o])


    def subtract(self, vm, o):
        return vm.get_slot_apply(self, "-", [o])


    def eq(self, vm, o):
        if vm.get_slot_apply(self, "==", [o], allow_fail=True):
            return True
        else:
            return False


    def neq(self, vm, o):
        if vm.get_slot_apply(self, "!=", [o], allow_fail=True):
            return True
        else:
            return False


    def le(self, vm, o):
        if vm.get_slot_apply(self, "<", [o], allow_fail=True):
            return True
        else:
            return False


    def le_eq(self, vm, o):
        if vm.get_slot_apply(self, "<=", [o], allow_fail=True):
            return True
        else:
            return False


    def gr_eq(self, vm, o):
        if vm.get_slot_apply(self, ">=", [o], allow_fail=True):
            return True
        else:
            return False


    def gt(self, vm, o):
        if vm.get_slot_apply(self, ">", [o], allow_fail=True):
            return True
        else:
            return False


@con_object_proc
def _new_func_Con_Object(vm):
    (c,), vargs = vm.decode_args("O", vargs=True)
    o = Con_Boxed_Object(vm, c)
    vm.apply(o.get_slot(vm, "init"), vargs)
    return o


@con_object_proc
def _Con_Object_find_slot(vm):
    (self, sn_o),_ = vm.decode_args("OS")
    assert isinstance(sn_o, Con_String)

    v = self.find_slot(vm, sn_o.v)
    if not v:
        v = vm.get_builtin(BUILTIN_FAIL_OBJ)
    return v


@con_object_proc
def _Con_Object_get_slot(vm):
    (self, sn_o),_ = vm.decode_args("OS")
    assert isinstance(sn_o, Con_String)

    return self.get_slot(vm, sn_o.v)


@con_object_proc
def _Con_Object_init(vm):
    (self,), vargs = vm.decode_args("O", vargs=True)
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_Object_is(vm):
    (self, o),_ = vm.decode_args("OO")
    if self.is_(o):
        return vm.get_builtin(BUILTIN_NULL_OBJ)
    else:
        return vm.get_builtin(BUILTIN_FAIL_OBJ)


@con_object_proc
def _Con_Object_to_str(vm):
    (self,),_ = vm.decode_args("O")
    return Con_String(vm, "<Object@%x>" % objectmodel.current_object_addr_as_int(self))


def bootstrap_con_object(vm):
    # This is where the hardcore bootstrapping stuff happens. Many things here are done in a very
    # specific order - changing something can easily cause lots of later things to break.
    
    object_class_nm = Con_String(vm, "Object")
    object_class = Con_Class(vm, object_class_nm, [], None)
    vm.set_builtin(BUILTIN_OBJECT_CLASS, object_class)
    class_class_nm = Con_String(vm, "Class")
    class_class = Con_Class(vm, class_class_nm, [object_class], None)
    vm.set_builtin(BUILTIN_CLASS_CLASS, class_class)
    object_class.instance_of = class_class
    class_class.instance_of = class_class

    string_class_nm = Con_String(vm, "String")
    string_class = Con_Class(vm, string_class_nm, [object_class], None)
    vm.set_builtin(BUILTIN_STRING_CLASS, string_class)
    object_class_nm.instance_of = string_class
    class_class_nm.instance_of = string_class
    string_class_nm.instance_of = string_class
    
    vm.set_builtin(BUILTIN_NULL_OBJ, Con_Boxed_Object(vm))
    vm.set_builtin(BUILTIN_FAIL_OBJ, Con_Boxed_Object(vm))

    module_class = Con_Class(vm, Con_String(vm, "Module"), [object_class], None)
    vm.set_builtin(BUILTIN_MODULE_CLASS, module_class)
    
    # In order that later objects can refer to the Builtins module, we have to create it now.
    builtins_module = new_c_con_module(vm, "Builtins", "Builtins", __file__, None, \
      ["Object", "Class", "Func", "Partial_Application", "String", "Module", "Number", "Int",
       "Float", "List", "Set", "Dict", "Exception"])
    # We effectively initialize the Builtins module through the bootstrapping process, so it doesn't
    # need a separate initialization function.
    builtins_module.initialized = True
    vm.set_builtin(BUILTIN_BUILTINS_MODULE, builtins_module)
    vm.set_mod(builtins_module)
    
    object_class.set_slot(vm, "container", builtins_module)
    class_class.set_slot(vm, "container", builtins_module)
    string_class.set_slot(vm, "container", builtins_module)
    module_class.set_slot(vm, "container", builtins_module)
    builtins_module.set_defn(vm, "Object", object_class)
    builtins_module.set_defn(vm, "Class", class_class)
    builtins_module.set_defn(vm, "String", string_class)
    builtins_module.set_defn(vm, "Module", module_class)

    func_class = Con_Class(vm, Con_String(vm, "Func"), [object_class], builtins_module)
    vm.set_builtin(BUILTIN_FUNC_CLASS, func_class)
    builtins_module.set_defn(vm, "Func", func_class)
    partial_application_class = Con_Class(vm, Con_String(vm, "Partial_Application"), \
      [object_class], builtins_module)
    vm.set_builtin(BUILTIN_PARTIAL_APPLICATION_CLASS, partial_application_class)
    builtins_module.set_defn(vm, "Partial_Application", partial_application_class)
    number_class = Con_Class(vm, Con_String(vm, "Number"), [object_class], builtins_module)
    vm.set_builtin(BUILTIN_NUMBER_CLASS, number_class)
    builtins_module.set_defn(vm, "Number", number_class)
    int_class = Con_Class(vm, Con_String(vm, "Int"), [object_class], builtins_module)
    vm.set_builtin(BUILTIN_INT_CLASS, int_class)
    builtins_module.set_defn(vm, "Int", int_class)
    float_class = Con_Class(vm, Con_String(vm, "Float"), [object_class], builtins_module)
    vm.set_builtin(BUILTIN_FLOAT_CLASS, float_class)
    builtins_module.set_defn(vm, "Float", float_class)
    list_class = Con_Class(vm, Con_String(vm, "List"), [object_class], builtins_module)
    vm.set_builtin(BUILTIN_LIST_CLASS, list_class)
    builtins_module.set_defn(vm, "List", list_class)
    set_class = Con_Class(vm, Con_String(vm, "Set"), [object_class], builtins_module)
    vm.set_builtin(BUILTIN_SET_CLASS, set_class)
    builtins_module.set_defn(vm, "Set", set_class)
    dict_class = Con_Class(vm, Con_String(vm, "Dict"), [object_class], builtins_module)
    vm.set_builtin(BUILTIN_DICT_CLASS, dict_class)
    builtins_module.set_defn(vm, "Dict", dict_class)
    exception_class = Con_Class(vm, Con_String(vm, "Exception"), [object_class], builtins_module)
    vm.set_builtin(BUILTIN_EXCEPTION_CLASS, exception_class)
    builtins_module.set_defn(vm, "Exception", exception_class)

    object_class.new_func = \
      new_c_con_func(vm, Con_String(vm, "new_Object"), False, _new_func_Con_Object, \
        builtins_module)

    new_c_con_func_for_class(vm, "find_slot", _Con_Object_find_slot, object_class)
    new_c_con_func_for_class(vm, "get_slot", _Con_Object_get_slot, object_class)
    new_c_con_func_for_class(vm, "init", _Con_Object_init, object_class)
    new_c_con_func_for_class(vm, "is", _Con_Object_is, object_class)
    new_c_con_func_for_class(vm, "to_str", _Con_Object_to_str, object_class)




################################################################################
# Con_Class
#

class Con_Class(Con_Boxed_Object):
    __slots__ = ("supers", "fields_map", "fields", "new_func", "version", "dependents")
    _immutable_fields = ("supers", "fields", "dependents")


    def __init__(self, vm, name, supers, container, instance_of=None, new_func=None):
        if instance_of is None:
            instance_of = vm.get_builtin(BUILTIN_CLASS_CLASS)
        Con_Boxed_Object.__init__(self, vm, instance_of)
        
        if new_func is None:
            # A new object function hasn't been supplied so we need to search for one.
            # See http://tratt.net/laurie/tech_articles/articles/more_meta_matters for
            # more details about this algorithm.
            for sc in supers:
                assert isinstance(sc, Con_Class)
                if new_func is None:
                    new_func = sc.new_func
                elif new_func is not sc.new_func:
                    new_func = sc.new_func
                    object_class = vm.get_builtin(BUILTIN_OBJECT_CLASS)
                    assert isinstance(object_class, Con_Class)
                    object_class.new_func
                    if new_func is object_class.new_func:
                        new_func = sc.new_func
                    else:
                        # There's a clash between superclass's metaclasses.
                        raise Exception("XXX")
        self.new_func = new_func
        
        self.supers = supers
        self.fields_map = _EMPTY_MAP
        self.fields = []
        
        # To optimise slot lookups, we need to be a little more cunning. We make a (reasonable)
        # assumption that classes rarely change their fields (most classes never change their fields
        # after their initial creation at all), so that in general we can simply elide field
        # lookups entirely. When a field is changed, all subsequent field lookups on that class and
        # its subclasses need to be regenerated. To force this, every class a "version" which is
        # incremented whenever its fields are changed. As well as changing the class itself, all
        # subclasses must be changed too. We maintain a list of all subclasses (even indirect ones!)
        # to do this.
        
        self.version = Version()
        self.dependents = []
        sc_stack = supers[:]
        while len(sc_stack) > 0:
            sc = type_check_class(vm, sc_stack.pop())
            sc.dependents.append(rweakref.ref(sc))
            sc_stack.extend(sc.supers)

        self.set_slot(vm, "name", name)
        if container:
            self.set_slot(vm, "container", container)


    @jit.elidable_promote("0")
    def _get_field_i(self, vm, n, version):
        m = jit.promote(self.fields_map)
        i = m.find(n)
        if i != -1:
            return self.fields[i]

        for s in self.supers:
            assert isinstance(s, Con_Class)
            o = s.find_field(vm, n)
            if o is not None:
                return o

        return None


    def find_field(self, vm, n):
        return self._get_field_i(vm, n, jit.promote(self.version))


    def get_field(self, vm, n):
        o = self._get_field_i(vm, n, jit.promote(self.version))
        if o is None:
            vm.raise_helper("Field_Exception", [Con_String(vm, n), self])
        return o


    def set_field(self, vm, n, o):
        assert o is not None
        m = jit.promote(self.fields_map)
        i = m.find(n)
        if i == -1:
            self.fields_map = m.extend(n)
            self.fields.append(o)
        else:
            self.fields[i] = o
        self.version = Version()
        
        j = 0
        while j < len(self.dependents):
            dep = self.dependents[j]()
            if dep is None:
                del self.dependents[j]
                continue
            dep.version = Version()
            j += 1


@con_object_proc
def _new_func_Con_Class(vm):
    (c, name, supers, container), vargs = vm.decode_args("CSLO", vargs=True)
    assert isinstance(c, Con_Class)
    assert isinstance(name, Con_String)
    assert isinstance(supers, Con_List)
    o = Con_Class(vm, name, supers.l[:], container, c)
    vm.apply(o.get_slot(vm, "init"), vargs)
    return o


@con_object_proc
def _Con_Class_new(vm):
    _, v = vm.decode_args(vargs=True)
    c = type_check_class(vm, v[0])
    if c.new_func is None:
        p = type_check_string(vm, vm.get_slot_apply(c, "path")).v
        msg = "Instance of %s has no new_func." % p
        vm.raise_helper("VM_Exception", [Con_String(vm, msg)])
    return vm.apply(c.new_func, v)


@con_object_proc
def _Con_Class_get_field(vm):
    (self, n),_ = vm.decode_args("CS")
    assert isinstance(self, Con_Class)
    assert isinstance(n, Con_String)

    o = self.find_field(vm, n.v)
    if o is None:
        vm.raise_helper("Field_Exception", [n, self])

    return o


@con_object_proc
def _Con_Class_set_field(vm):
    (self, n, o),_ = vm.decode_args("CSO")
    assert isinstance(self, Con_Class)
    assert isinstance(n, Con_String)
    self.set_field(vm, n.v, o)

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_Class_path(vm):
    (self, stop_at),_ = vm.decode_args("C", opt="o")
    assert isinstance(self, Con_Class)
    
    name = type_check_string(vm, self.get_slot(vm, "name"))
    if name.v == "":
        name = Con_String(vm, "<anon>")

    container = self.get_slot(vm, "container")
    if container is vm.get_builtin(BUILTIN_NULL_OBJ) or container is stop_at:
        return name
    else:
        if stop_at is None:
            stop_at = vm.get_builtin(BUILTIN_NULL_OBJ)
        rtn = type_check_string(vm, vm.get_slot_apply(container, "path", [stop_at]))
        if isinstance(container, Con_Module):
            sep = "::"
        else:
            sep = "."
        return Con_String(vm, "%s%s%s" % (rtn.v, sep, name.v))


@con_object_proc
def _Con_Class_to_str(vm):
    (self,),_ = vm.decode_args("C")
    assert isinstance(self, Con_Class)

    nm = type_check_string(vm, self.get_slot(vm, "name"))
    return Con_String(vm, "<Class %s>" % nm.v)


@con_object_proc
def _Con_Class_conformed_by(vm):
    (self, o),_ = vm.decode_args("CO")
    assert isinstance(self, Con_Class)
    assert isinstance(o, Con_Boxed_Object)

    if o.instance_of is self:
        # We optimise the easy case.
        return vm.get_builtin(BUILTIN_NULL_OBJ)
    else:
        stack = [self]
        while len(stack) > 0:
            cnd = stack.pop()
            assert isinstance(cnd, Con_Class)
            for f in cnd.fields_map.index_map.keys():
                if not o.has_slot(vm, f):
                    return vm.get_builtin(BUILTIN_FAIL_OBJ)
            stack.extend(cnd.supers)  

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_Class_instantiated(vm):
    (self, o),_ = vm.decode_args("CO")
    assert isinstance(self, Con_Class)
    assert isinstance(o, Con_Boxed_Object)

    if o.instance_of is self:
        # We optimise the easy case.
        return vm.get_builtin(BUILTIN_NULL_OBJ)
    else:
		# What we do now is to put 'instance_of' onto a stack; if the current class on the stack
		# does not match 'self', we push all the class's superclasses onto the stack.
		#
		# If we run off the end of the stack then there is no match.
        stack = [o.instance_of]
        while len(stack) > 0:
            cnd = stack.pop()
            assert isinstance(cnd, Con_Class)
            if cnd is self:
                return vm.get_builtin(BUILTIN_NULL_OBJ)
            stack.extend(cnd.supers)

    return vm.get_builtin(BUILTIN_FAIL_OBJ)


def bootstrap_con_class(vm):
    class_class = vm.get_builtin(BUILTIN_CLASS_CLASS)
    assert isinstance(class_class, Con_Class)
    class_class.new_func = \
      new_c_con_func(vm, Con_String(vm, "new_Class"), False, _new_func_Con_Class, \
        vm.get_builtin(BUILTIN_BUILTINS_MODULE))

    new_c_con_func_for_class(vm, "conformed_by", _Con_Class_conformed_by, class_class)
    new_c_con_func_for_class(vm, "instantiated", _Con_Class_instantiated, class_class)
    new_c_con_func_for_class(vm, "new", _Con_Class_new, class_class)
    new_c_con_func_for_class(vm, "get_field", _Con_Class_get_field, class_class)
    new_c_con_func_for_class(vm, "set_field", _Con_Class_set_field, class_class)
    new_c_con_func_for_class(vm, "path", _Con_Class_path, class_class)
    new_c_con_func_for_class(vm, "to_str", _Con_Class_to_str, class_class)



################################################################################
# Con_Module
#

class Con_Module(Con_Boxed_Object):
    __slots__ = ("is_bc", "bc", "id_", "src_path", "imps", "tlvars_map", "consts",
      "init_func", "values", "closure", "initialized")
    _immutable_fields_ = ("is_bc", "bc", "name", "id_", "src_path", "imps", "tlvars_map",
      "init_func", "consts")


    def __init__(self, vm, is_bc, bc, name, id_, src_path, imps, tlvars_map, num_consts, init_func, \
      instance_of=None):
        if instance_of is None:
            instance_of = vm.get_builtin(BUILTIN_MODULE_CLASS)
        Con_Boxed_Object.__init__(self, vm, instance_of)

        self.is_bc = is_bc # True for bytecode modules; False for RPython modules
        self.bc = bc
        self.id_ = id_
        self.src_path = src_path
        self.imps = imps
        self.tlvars_map = tlvars_map
        self.consts = [None] * num_consts
        debug.make_sure_not_resized(self.consts)
        self.init_func = init_func
        
        self.values = []
        if is_bc:
            self.closure = None
        else:
            self.closure = VM.Closure(None, len(tlvars_map))

        self.set_slot(vm, "name", name)
        self.set_slot(vm, "src_path", Con_String(vm, src_path))
        self.set_slot(vm, "mod_id", Con_String(vm, id_))
        self.set_slot(vm, "container", vm.get_builtin(BUILTIN_NULL_OBJ))

        self.initialized = False


    def import_(self, vm):
        if self.initialized:
            return
        
        if self.is_bc:
            # Bytecode modules use the old "push a Con_Int onto the stack to signify how many
            # parameters are being passed" hack. To add insult injury, they simply pop this object
            # off without using it. So we pass null as a 'magic' parameter (since it will be popped
            # first, it's actually the second parameter), knowing that it won't actually be used for
            # anything.
            v, self.closure = vm.apply_closure(self.init_func, \
              [self, vm.get_builtin(BUILTIN_NULL_OBJ)])
        else:
            vm.apply(self.init_func, [self])
        self.initialized = True
        return


    @jit.elidable_promote("0")
    def get_closure_i(self, vm, n):
        return self.tlvars_map.get(n, -1)


    def get_defn(self, vm, n):
        i = self.get_closure_i(vm, n)
        if i == -1:
            name = type_check_string(vm, self.get_slot(vm, "name")).v
            vm.raise_helper("Mod_Defn_Exception", \
              [Builtins.Con_String(vm, "No such definition '%s' in '%s'." % (n, name))])
        o = self.closure.vars[i]
        if o is None:
            name = type_check_string(vm, self.get_slot(vm, "name")).v
            vm.raise_helper("Mod_Defn_Exception", \
              [Builtins.Con_String(vm, "Definition '%s' unassigned in '%s'." % (n, name))])

        return o


    @jit.elidable_promote("0")
    def has_defn(self, vm, n):
        if self.get_closure_i(vm, n) == -1:
            return False
        return True


    def set_defn(self, vm, n, o):
        i = self.get_closure_i(vm, n)
        if i == -1:
            name = type_check_string(vm, self.get_slot(vm, "name")).v
            vm.raise_helper("Mod_Defn_Exception", \
              [Builtins.Con_String(vm, "No such definition '%s' in '%s'." % (n, name))])
        self.closure.vars[i] = o


    @jit.elidable_promote("0")
    def get_const(self, vm, i):
        v = self.consts[i]
        if v is not None:
            return v
        consts_offs = Target.read_word(self.bc, Target.BC_MOD_CONSTANTS_OFFSETS)
        const_off = Target.read_word(self.bc, Target.BC_MOD_CONSTANTS) \
          + Target.read_word(self.bc, consts_offs + i * Target.INTSIZE)
        type = Target.read_word(self.bc, const_off)
        if type == Target.CONST_INT:
            v = Con_Int(vm, Target.read_word(self.bc, const_off + Target.INTSIZE))
        elif type == Target.CONST_FLOAT:
            v = Con_Float(vm, Target.read_float(self.bc, const_off + Target.INTSIZE))
        else:
            assert type == Target.CONST_STRING
            s = Target.extract_str(self.bc,
              const_off + Target.INTSIZE + Target.INTSIZE,
              Target.read_word(self.bc, const_off + Target.INTSIZE))
            v = Con_String(vm, s)
        self.consts[i] = v
        return v


    def bc_off_to_src_infos(self, vm, bc_off):
        bc = self.bc
        cur_bc_off = Target.read_word(bc, Target.BC_MOD_INSTRUCTIONS)
        instr_i = 0
        while cur_bc_off < bc_off:
            instr = Target.read_word(bc, cur_bc_off)
            it = Target.get_instr(instr)
            if it == Target.CON_INSTR_EXBI:
                start, size = Target.unpack_exbi(instr)
                cur_bc_off += Target.align(start + size)
            elif it == Target.CON_INSTR_IS_ASSIGNED:
                cur_bc_off += Target.INTSIZE + Target.INTSIZE
            elif it == Target.CON_INSTR_SLOT_LOOKUP or it == Target.CON_INSTR_PRE_SLOT_LOOKUP_APPLY:
                start, size = Target.unpack_slot_lookup(instr)
                cur_bc_off += Target.align(start + size)
            elif it == Target.CON_INSTR_ASSIGN_SLOT:
                start, size = Target.unpack_assign_slot(instr)
                cur_bc_off += Target.align(start + size)
            elif it == Target.CON_INSTR_UNPACK_ARGS:
                num_args, has_vargs = Target.unpack_unpack_args(instr)
                cur_bc_off += Target.INTSIZE + num_args * Target.INTSIZE
                if has_vargs:
                    cur_bc_off += Target.INTSIZE
            elif it == Target.CON_INSTR_MODULE_LOOKUP:
                start, size = Target.unpack_mod_lookup(instr)
                cur_bc_off += Target.align(start + size)
            elif it == Target.CON_INSTR_VAR_LOOKUP \
              or it == Target.CON_INSTR_VAR_ASSIGN \
              or it == Target.CON_INSTR_ADD_FAILURE_FRAME \
              or it == Target.CON_INSTR_ADD_FAIL_UP_FRAME \
              or it == Target.CON_INSTR_REMOVE_FAILURE_FRAME \
              or it == Target.CON_INSTR_IS \
              or it == Target.CON_INSTR_FAIL_NOW \
              or it == Target.CON_INSTR_POP \
              or it == Target.CON_INSTR_IMPORT \
              or it == Target.CON_INSTR_LIST \
              or it == Target.CON_INSTR_APPLY \
              or it == Target.CON_INSTR_FUNC_DEFN \
              or it == Target.CON_INSTR_RETURN \
              or it == Target.CON_INSTR_BRANCH \
              or it == Target.CON_INSTR_YIELD \
              or it == Target.CON_INSTR_DICT \
              or it == Target.CON_INSTR_DUP \
              or it == Target.CON_INSTR_PULL \
              or it == Target.CON_INSTR_BUILTIN_LOOKUP \
              or it == Target.CON_INSTR_EYIELD \
              or it == Target.CON_INSTR_ADD_EXCEPTION_FRAME \
              or it == Target.CON_INSTR_REMOVE_EXCEPTION_FRAME \
              or it == Target.CON_INSTR_RAISE \
              or it == Target.CON_INSTR_SET \
              or it == Target.CON_INSTR_BRANCH_IF_NOT_FAIL \
              or it == Target.CON_INSTR_BRANCH_IF_FAIL \
              or it == Target.CON_INSTR_CONST_GET \
              or it == Target.CON_INSTR_UNPACK_ASSIGN \
              or it == Target.CON_INSTR_EQ \
              or it == Target.CON_INSTR_NEQ \
              or it == Target.CON_INSTR_GT \
              or it == Target.CON_INSTR_LE \
              or it == Target.CON_INSTR_LE_EQ \
              or it == Target.CON_INSTR_GR_EQ \
              or it == Target.CON_INSTR_ADD \
              or it == Target.CON_INSTR_SUBTRACT:
                cur_bc_off += Target.INTSIZE
            else:
                print it
                raise Exception("XXX")
        
            instr_i += 1

        assert cur_bc_off == bc_off
        
        src_info_pos = src_info_num = 0
        src_infos_off = Target.read_word(bc, Target.BC_MOD_SRC_POSITIONS)
        while 1:
            src_info1 = Target.read_uint32_word(bc, src_infos_off + src_info_pos * 4)
            if src_info_num + (src_info1 & ((1 << 4) - 1)) > instr_i:
                break
            src_info_num += src_info1 & ((1 << 4) - 1)
            while src_info1 & (1 << 4):
                src_info_pos += 2
                src_info1 = Target.read_uint32_word(bc, src_infos_off + src_info_pos * 4)
            src_info_pos += 2

        src_infos = []
        while 1:
            src_info1 = Target.read_uint32_word(bc, src_infos_off + src_info_pos * 4)
            src_info2 = Target.read_uint32_word(bc, src_infos_off + (src_info_pos + 1) * 4)

            if src_info2 & ((1 << 12) - 1) == ((1 << 12) - 1):
                mod_id = self.id_
            else:
                mod_id = self.imps[src_info2 & ((1 << 12) - 1)]

            src_off = (src_info1 >> 5) & ((1 << (31 - 5)) - 1)
            src_len = src_info2 >> 12
            src_info = Con_List(vm, \
              [Con_String(vm, mod_id), Con_Int(vm, src_off), Con_Int(vm, src_len)])
            src_infos.append(src_info)

            if not (src_info1 & (1 << 4)):
                break

            src_info_pos += 2
        
        return Con_List(vm, src_infos)


@con_object_proc
def _new_func_Con_Module(vm):
    (class_, bc_o), vargs = vm.decode_args("CS", vargs=True)
    assert isinstance(bc_o, Con_String)
    
    bc = rffi.str2charp(bc_o.v)
    mod = Bytecode.mk_mod(vm, bc, 0)
    return mod


@con_object_proc
def _Con_Module_get_defn(vm):
    (self, n),_ = vm.decode_args("MS")
    assert isinstance(self, Con_Module)
    assert isinstance(n, Con_String)

    return self.get_defn(vm, n.v)


@con_object_proc
def _Con_Module_has_defn(vm):
    (self, n),_ = vm.decode_args("MS")
    assert isinstance(self, Con_Module)
    assert isinstance(n, Con_String)

    if self.has_defn(vm, n.v):
        r_o = vm.get_builtin(BUILTIN_NULL_OBJ)
    else:
        r_o = vm.get_builtin(BUILTIN_FAIL_OBJ)

    return r_o


@con_object_proc
def _Con_Module_set_defn(vm):
    (self, n, o),_ = vm.decode_args("MSO")
    assert isinstance(self, Con_Module)
    assert isinstance(n, Con_String)

    self.set_defn(vm, n.v, o)
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_gen
def _Con_Module_iter_defns(vm):
    (self,),_ = vm.decode_args("M")
    assert isinstance(self, Con_Module)

    for d in self.tlvars_map.keys():
        yield Con_List(vm, [Con_String(vm, d), self.get_defn(vm, d)])


@con_object_gen
def _Con_Module_iter_newlines(vm):
    (self,),_ = vm.decode_args("M")
    assert isinstance(self, Con_Module)

    bc = self.bc
    newlines_off = Target.read_word(bc, Target.BC_MOD_NEWLINES)
    for i in range(Target.read_word(bc, Target.BC_MOD_NUM_NEWLINES)):
        yield Con_Int(vm, Target.read_word(bc, newlines_off + i * Target.INTSIZE))


@con_object_proc
def _Con_Module_path(vm):
    (self, stop_at),_ = vm.decode_args("M", opt="o")
    assert isinstance(self, Con_Module)
    
    if self is stop_at:
        return Con_String(vm, "")
    
    name = type_check_string(vm, self.get_slot(vm, "name"))
    container = self.get_slot(vm, "container")
    if container is vm.get_builtin(BUILTIN_NULL_OBJ) or container is stop_at:
        return name
    else:
        if stop_at is None:
            stop_at = vm.get_builtin(BUILTIN_NULL_OBJ)
        rtn = type_check_string(vm, vm.get_slot_apply(container, "path", [stop_at]))
        if isinstance(container, Con_Module):
            sep = "::"
        else:
            sep = "."
        return Con_String(vm, "%s%s%s" % (rtn.v, sep, name.v))


@con_object_proc
def _Con_Module_src_offset_to_line_column(vm):
    (self, off_o),_ = vm.decode_args("MI")
    assert isinstance(self, Con_Module)
    assert isinstance(off_o, Con_Int)

    off = off_o.v
    if off < 0:
        raise Exception("XXX")

    bc = self.bc
    newlines_off = Target.read_word(bc, Target.BC_MOD_NEWLINES)
    for i in range(Target.read_word(bc, Target.BC_MOD_NUM_NEWLINES)):
        if off < Target.read_word(bc, newlines_off + i * Target.INTSIZE):
            return Con_List(vm, [Con_Int(vm, i), Con_Int(vm, off - \
              Target.read_word(bc, newlines_off + (i - 1) * Target.INTSIZE))])
    
    raise Exception("XXX")
    


def bootstrap_con_module(vm):
    module_class = vm.get_builtin(BUILTIN_MODULE_CLASS)
    assert isinstance(module_class, Con_Class)
    module_class.new_func = \
      new_c_con_func(vm, Con_String(vm, "new_Module"), False, \
        _new_func_Con_Module, vm.get_builtin(BUILTIN_BUILTINS_MODULE))


    new_c_con_func_for_class(vm, "get_defn", _Con_Module_get_defn, module_class)
    new_c_con_func_for_class(vm, "has_defn", _Con_Module_has_defn, module_class)
    new_c_con_func_for_class(vm, "iter_defns", _Con_Module_iter_defns, module_class)
    new_c_con_func_for_class(vm, "iter_newlines", _Con_Module_iter_newlines, module_class)
    new_c_con_func_for_class(vm, "path", _Con_Module_path, module_class)
    new_c_con_func_for_class(vm, "set_defn", _Con_Module_set_defn, module_class)
    new_c_con_func_for_class(vm, "src_offset_to_line_column", _Con_Module_src_offset_to_line_column, module_class)


def new_c_con_module(vm, name, id_, src_path, import_func, names):
    tlvars_map = {}
    i = 0
    for j in names:
        assert j not in tlvars_map
        tlvars_map[j] = i
        i += 1
    mod = Con_Module(vm, False, lltype.nullptr(rffi.CCHARP.TO), Con_String(vm, name), id_, \
      src_path, [], tlvars_map, 0, None)
    mod.init_func = new_c_con_func(vm, Con_String(vm, "$$init$$"), False, import_func, mod)
    
    return mod


def new_bc_con_module(vm, bc, name, id_, src_path, imps, tlvars_map, num_consts):
    return Con_Module(vm, True, bc, Con_String(vm, name), id_, src_path, imps, tlvars_map, \
      num_consts, None)



################################################################################
# Con_Func
#

class Con_Func(Con_Boxed_Object):
    __slots__ = ("name", "is_bound", "pc", "max_stack_size", "num_vars", "container_closure")
    _immutable_fields_ = ("name", "is_bound", "pc", "max_stack_size", "num_vars", "container_closure")


    def __init__(self, vm, name, is_bound, pc, max_stack_size, num_params, num_vars, container, \
      container_closure, instance_of=None):
        if instance_of is None:
            instance_of = vm.get_builtin(BUILTIN_FUNC_CLASS)
        Con_Boxed_Object.__init__(self, vm, instance_of)
    
        self.name = name
        self.is_bound = is_bound
        self.pc = pc
        self.max_stack_size = max_stack_size
        self.num_vars = num_vars
        self.container_closure = container_closure
        
        self.set_slot(vm, "container", container)
        self.set_slot(vm, "name", name)
        self.set_slot(vm, "num_params", Con_Int(vm, num_params))


    def __repr__(self):
        return "<Func %s>" % self.name.v


@con_object_proc
def _Con_Func_path(vm):
    (self, stop_at),_ = vm.decode_args("Fo")
    assert isinstance(self, Con_Func)
    
    if self is stop_at:
        return Con_String(vm, "")
    
    container = self.get_slot(vm, "container")
    if container is vm.get_builtin(BUILTIN_NULL_OBJ) or container is stop_at:
        return self.name
    else:
        rtn = type_check_string(vm, vm.get_slot_apply(container, "path", [stop_at]))
        if isinstance(container, Con_Module):
            sep = "::"
        else:
            sep = "."
        name = self.name
        assert isinstance(name, Con_String)
        return Con_String(vm, "%s%s%s" % (rtn.v, sep, name.v))


def bootstrap_con_func(vm):
    func_class = vm.get_builtin(BUILTIN_FUNC_CLASS)
    assert isinstance(func_class, Con_Class)
    
    builtins_module = vm.get_builtin(BUILTIN_BUILTINS_MODULE)
    builtins_module.set_defn(vm, "Func", func_class)
    
    new_c_con_func_for_class(vm, "path", _Con_Func_path, func_class)


def new_c_con_func(vm, name, is_bound, func, container):
    cnd = container
    while not (isinstance(cnd, Con_Module)):
        cnd = cnd.get_slot(vm, "container")
    return Con_Func(vm, name, is_bound, VM.Py_PC(cnd, func), 0, -1, 0, container, None)


def new_c_con_func_for_class(vm, name, func, class_):
    f = new_c_con_func(vm, Con_String(vm, name), True, func, class_)
    class_.set_field(vm, name, f)


def new_c_con_func_for_mod(vm, name, func, mod):
    f = new_c_con_func(vm, Con_String(vm, name), False, func, mod)
    mod.set_defn(vm, name, f)



################################################################################
# Con_Partial_Application
#

class Con_Partial_Application(Con_Boxed_Object):
    __slots__ = ("f", "args")
    _immutable_fields_ = ("f", "args")


    def __init__(self, vm, f, args, instance_of=None):
        if instance_of is None:
            instance_of = vm.get_builtin(BUILTIN_PARTIAL_APPLICATION_CLASS)
        Con_Boxed_Object.__init__(self, vm, instance_of)
        self.f = f
        self.args = args


    def __repr__(self):
        return "<Partial_Application %s>" % self.f.name.v



@con_object_proc
def _new_func_Con_Partial_Application(vm):
    (class_, func_o, args_o),_ = vm.decode_args("CFL")
    assert isinstance(args_o, Con_List)

    o = Con_Partial_Application(vm, func_o, args_o.l)
    vm.apply(o.get_slot(vm, "init"), [func_o] + args_o.l)
    return o


@con_object_gen
def _Con_Partial_Application_apply(vm):
    (self, args_o),_ = vm.decode_args("!L", self_of=Con_Partial_Application)
    assert isinstance(self, Con_Partial_Application)
    assert isinstance(args_o, Con_List)
    
    vm.pre_apply_pump(self.f, self.args + args_o.l)
    while 1:
        e_o = vm.apply_pump()
        if not e_o:
            break
        yield e_o


def bootstrap_con_partial_application(vm):
    partial_application_class = vm.get_builtin(BUILTIN_PARTIAL_APPLICATION_CLASS)
    assert isinstance(partial_application_class, Con_Class)
    partial_application_class.new_func = \
      new_c_con_func(vm, Con_String(vm, "new_Partial_Application"), False, \
        _new_func_Con_Partial_Application, vm.get_builtin(BUILTIN_BUILTINS_MODULE))

    new_c_con_func_for_class(vm, "apply", _Con_Partial_Application_apply, partial_application_class)



################################################################################
# Con_Number
#

class Con_Number(Con_Boxed_Object):
    __slots__ = ()

    def as_int(self):
        raise Exception("XXX")


    def as_float(self):
        raise Exception("XXX")



################################################################################
# Con_Int
#

class Con_Int(Con_Number):
    __slots__ = ("v",)
    _immutable_fields_ = ("v",)


    def __init__(self, vm, v, instance_of=None):
        if instance_of is None:
            instance_of = vm.get_builtin(BUILTIN_INT_CLASS)
        Con_Number.__init__(self, vm, instance_of)
        assert v is not None
        self.v = rffi.cast(lltype.Signed, v)


    def as_int(self):
        return self.v


    def as_float(self):
        return float(self.v)


    def is_(self, o):
        if isinstance(o, Con_Int):
            return self.v == o.v
        else:
            return self is o


    def add(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return Con_Int(vm, self.v + o.v)
        else:
            assert isinstance(o, Con_Float)
            return Con_Float(vm, self.as_float() + o.v)


    def subtract(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return Con_Int(vm, self.v - o.v)
        else:
            assert isinstance(o, Con_Float)
            return Con_Float(vm, self.as_float() - o.v)


    def div(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            if self.v % o.v == 0:
                return Con_Int(vm, self.v / o.v)
            return Con_Float(vm, self.as_float() / o.v)
        else:
            assert isinstance(o, Con_Float)
            return Con_Float(vm, self.as_float() / o.v)


    def idiv(self, vm, o):
        o = type_check_number(vm, o)
        return Con_Int(vm, self.v // o.as_int())


    def mod(self, vm, o):
        o = type_check_number(vm, o)
        return Con_Int(vm, self.v % o.as_int())


    def mul(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return Con_Int(vm, self.v * o.v)
        else:
            assert isinstance(o, Con_Float)
            return Con_Float(vm, self.as_float() * o.v)


    def pow(self, vm, o):
        o = type_check_int(vm, o)
        p = 1
        x = self.v
        y = o.v
        while y > 0:
            p *= x
            y -= 1
        return Con_Int(vm, p)


    def eq(self, vm, o):
        if isinstance(o, Con_Int):
            return self.v == o.v
        elif isinstance(o, Con_Float):
            return self.as_float() == o.v
        return False


    def neq(self, vm, o):
        if isinstance(o, Con_Int):
            return self.v != o.v
        elif isinstance(o, Con_Float):
            return self.as_float() != o.v
        return True


    def le(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return self.v < o.v
        else:
            assert isinstance(o, Con_Float)
            return self.as_float() < o.v


    def le_eq(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return self.v <= o.v
        else:
            assert isinstance(o, Con_Float)
            return self.as_float() <= o.v


    def gr_eq(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return self.v >= o.v
        else:
            assert isinstance(o, Con_Float)
            return self.as_float() >= o.v


    def gt(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return self.v > o.v
        else:
            assert isinstance(o, Con_Float)
            return self.as_float() > o.v


@con_object_proc
def _new_func_Con_Int(vm):
    (class_, o_o), vargs = vm.decode_args("CO", vargs=True)
    if isinstance(o_o, Con_Int):
        return o_o
    elif isinstance(o_o, Con_String):
        v = None
        try:
            if o_o.v.startswith("0x") or o_o.v.startswith("0X"):
                v = int(o_o.v[2:], 16)
            else:
                v = int(o_o.v)
        except ValueError:
            vm.raise_helper("Number_Exception", [o_o])
        return Con_Int(vm, v)
    elif isinstance(o_o, Con_Float):
        return Con_Int(vm, o_o.v)
    else:
        vm.raise_helper("Type_Exception", [Con_String(vm, "Number | String"), o_o])


@con_object_proc
def _Con_Int_add(vm):
    (self, o_o),_ = vm.decode_args("IN")
    assert isinstance(self, Con_Int)
    assert isinstance(o_o, Con_Int)

    return self.add(vm, o_o)


@con_object_proc
def _Con_Int_and(vm):
    (self, o_o),_ = vm.decode_args("II")
    assert isinstance(self, Con_Int)
    assert isinstance(o_o, Con_Int)

    return Con_Int(vm, self.v & o_o.v)


@con_object_proc
def _Con_Int_div(vm):
    (self, o_o),_ = vm.decode_args("IN")
    assert isinstance(self, Con_Int)
    assert isinstance(o_o, Con_Number)

    return self.div(vm, o_o)


@con_object_proc
def _Con_Int_eq(vm):
    (self, o_o),_ = vm.decode_args("IO")
    assert isinstance(self, Con_Int)
    assert isinstance(o_o, Con_Object)
    
    if self.eq(vm, o_o):
        return vm.get_builtin(BUILTIN_NULL_OBJ)
    else:
        return vm.get_builtin(BUILTIN_FAIL_OBJ)


@con_object_proc
def _Con_Int_gt(vm):
    (self, o_o),_ = vm.decode_args("IN")
    assert isinstance(self, Con_Int)
    assert isinstance(o_o, Con_Number)

    if self.gt(vm, o_o):
        return vm.get_builtin(BUILTIN_NULL_OBJ)
    else:
        return vm.get_builtin(BUILTIN_FAIL_OBJ)


@con_object_proc
def _Con_Int_gtq(vm):
    (self, o_o),_ = vm.decode_args("IN")
    assert isinstance(self, Con_Int)
    assert isinstance(o_o, Con_Number)

    if self.gr_eq(vm, o_o):
        return vm.get_builtin(BUILTIN_NULL_OBJ)
    else:
        return vm.get_builtin(BUILTIN_FAIL_OBJ)


@con_object_proc
def _Con_Int_hash(vm):
    (self,),_ = vm.decode_args("I")
    assert isinstance(self, Con_Int)

    return Con_Int(vm, objectmodel.compute_hash(self.v))


@con_object_proc
def _Con_Int_idiv(vm):
    (self, o_o),_ = vm.decode_args("IN")
    assert isinstance(self, Con_Int)
    assert isinstance(o_o, Con_Number)

    return self.idiv(vm, o_o)


@con_object_proc
def _Con_Int_inv(vm):
    (self,),_ = vm.decode_args("I")
    assert isinstance(self, Con_Int)

    return Con_Int(vm, ~self.v)


@con_object_gen
def _Con_Int_iter_to(vm):
    (self, to_o, step_o),_ = vm.decode_args("II", opt="I")
    assert isinstance(self, Con_Int)
    assert isinstance(to_o, Con_Int)
    
    if step_o is None:
        step = 1
    else:
        assert isinstance(step_o, Con_Int)
        step = step_o.v

    for i in range(self.v, to_o.v, step):
        yield Con_Int(vm, i)


@con_object_proc
def _Con_Int_le(vm):
    (self, o_o),_ = vm.decode_args("IN")
    assert isinstance(self, Con_Int)
    assert isinstance(o_o, Con_Number)

    if self.le(vm, o_o):
        return vm.get_builtin(BUILTIN_NULL_OBJ)
    else:
        return vm.get_builtin(BUILTIN_FAIL_OBJ)


@con_object_proc
def _Con_Int_leq(vm):
    (self, o_o),_ = vm.decode_args("IN")
    assert isinstance(self, Con_Int)
    assert isinstance(o_o, Con_Number)

    if self.le_eq(vm, o_o):
        return vm.get_builtin(BUILTIN_NULL_OBJ)
    else:
        return vm.get_builtin(BUILTIN_FAIL_OBJ)


@con_object_proc
def _Con_Int_lsl(vm):
    (self, o),_ = vm.decode_args("II")
    assert isinstance(self, Con_Int)
    assert isinstance(o, Con_Int)

    return Con_Int(vm, self.v << o.v)


@con_object_proc
def _Con_Int_lsr(vm):
    (self, o),_ = vm.decode_args("II")
    assert isinstance(self, Con_Int)
    assert isinstance(o, Con_Int)

    return Con_Int(vm, self.v >> o.v)


@con_object_proc
def _Con_Int_mod(vm):
    (self, o_o),_ = vm.decode_args("IN")
    assert isinstance(self, Con_Int)

    return self.mod(vm, o_o)


@con_object_proc
def _Con_Int_mul(vm):
    (self, o_o),_ = vm.decode_args("IN")
    assert isinstance(self, Con_Int)

    return self.mul(vm, o_o)


@con_object_proc
def _Con_Int_or(vm):
    (self, o_o),_ = vm.decode_args("II")
    assert isinstance(self, Con_Int)
    assert isinstance(o_o, Con_Int)

    return Con_Int(vm, self.v | o_o.v)


@con_object_proc
def _Con_Int_pow(vm):
    (self, o_o),_ = vm.decode_args("IN")
    assert isinstance(self, Con_Int)

    return self.pow(vm, o_o)



@con_object_proc
def _Con_Int_sub(vm):
    (self, o_o),_ = vm.decode_args("IN")
    assert isinstance(self, Con_Int)
    assert isinstance(o_o, Con_Number)

    return self.subtract(vm, o_o)


@con_object_proc
def _Con_Int_str_val(vm):
    (self,),_ = vm.decode_args("I")
    assert isinstance(self, Con_Int)

    v = self.v
    if v < 0 or v > 255:
        vm.raise_helper("Number_Exception", [Con_String(vm, "'%d' out of ASCII range." % v)])

    return Con_String(vm, chr(v))


@con_object_proc
def _Con_Int_to_str(vm):
    (self,),_ = vm.decode_args("I")
    assert isinstance(self, Con_Int)

    return Con_String(vm, str(self.v))


@con_object_proc
def _Con_Int_xor(vm):
    (self, o_o),_ = vm.decode_args("II")
    assert isinstance(self, Con_Int)
    assert isinstance(o_o, Con_Int)

    return Con_Int(vm, self.v ^ o_o.v)


def bootstrap_con_int(vm):
    int_class = vm.get_builtin(BUILTIN_INT_CLASS)
    assert isinstance(int_class, Con_Class)
    int_class.new_func = \
      new_c_con_func(vm, Con_String(vm, "new_Int"), False, _new_func_Con_Int, \
        vm.get_builtin(BUILTIN_BUILTINS_MODULE))

    new_c_con_func_for_class(vm, "+", _Con_Int_add, int_class)
    new_c_con_func_for_class(vm, "and", _Con_Int_and, int_class)
    new_c_con_func_for_class(vm, "/", _Con_Int_div, int_class)
    new_c_con_func_for_class(vm, "==", _Con_Int_eq, int_class)
    new_c_con_func_for_class(vm, ">", _Con_Int_gt, int_class)
    new_c_con_func_for_class(vm, ">=", _Con_Int_gtq, int_class)
    new_c_con_func_for_class(vm, "hash", _Con_Int_hash, int_class)
    new_c_con_func_for_class(vm, "idiv", _Con_Int_idiv, int_class)
    new_c_con_func_for_class(vm, "inv", _Con_Int_inv, int_class)
    new_c_con_func_for_class(vm, "iter_to", _Con_Int_iter_to, int_class)
    new_c_con_func_for_class(vm, "<", _Con_Int_le, int_class)
    new_c_con_func_for_class(vm, "<=", _Con_Int_leq, int_class)
    new_c_con_func_for_class(vm, "lsl", _Con_Int_lsl, int_class)
    new_c_con_func_for_class(vm, "lsr", _Con_Int_lsr, int_class)
    new_c_con_func_for_class(vm, "%", _Con_Int_mod, int_class)
    new_c_con_func_for_class(vm, "*", _Con_Int_mul, int_class)
    new_c_con_func_for_class(vm, "or", _Con_Int_or, int_class)
    new_c_con_func_for_class(vm, "pow", _Con_Int_pow, int_class)
    new_c_con_func_for_class(vm, "str_val", _Con_Int_str_val, int_class)
    new_c_con_func_for_class(vm, "-", _Con_Int_sub, int_class)
    new_c_con_func_for_class(vm, "to_str", _Con_Int_to_str, int_class)
    new_c_con_func_for_class(vm, "xor", _Con_Int_xor, int_class)



################################################################################
# Con_Float
#

class Con_Float(Con_Number):
    __slots__ = ("v",)
    _immutable_fields_ = ("v",)


    def __init__(self, vm, v, instance_of=None):
        if instance_of is None:
            instance_of = vm.get_builtin(BUILTIN_FLOAT_CLASS)
        Con_Number.__init__(self, vm, instance_of)
        assert v is not None
        self.v = v


    def as_int(self):
        return int(self.v)


    def as_float(self):
        return self.v


    def add(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return Con_Float(vm, self.v + o.v)
        else:
            assert isinstance(o, Con_Float)
            return Con_Float(vm, self.v + o.v)


    def subtract(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return Con_Float(vm, self.v - o.v)
        else:
            assert isinstance(o, Con_Float)
            return Con_Float(vm, self.v - o.v)


    def div(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return Con_Float(vm, self.v / o.v)
        else:
            assert isinstance(o, Con_Float)
            return Con_Float(vm, self.v / o.v)


    def idiv(self, vm, o):
        o = type_check_number(vm, o)
        return Con_Int(vm, self.v // o.as_int())


    def mod(self, vm, o):
        o = type_check_number(vm, o)
        return Con_Int(vm, self.v % o.as_int())


    def mul(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return Con_Int(vm, self.v * o.v)
        else:
            assert isinstance(o, Con_Float)
            return Con_Float(vm, self.v * o.v)


    def eq(self, vm, o):
        if isinstance(o, Con_Int):
            return self.v == o.v
        elif isinstance(o, Con_Float):
            return self.v == o.v
        return False


    def neq(self, vm, o):
        if isinstance(o, Con_Int):
            return self.v != o.v
        elif isinstance(o, Con_Float):
            return self.v != o.v
        return True


    def le(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return self.as_int() < o.v
        else:
            assert isinstance(o, Con_Float)
            return self.v < o.v


    def le_eq(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return self.as_int() <= o.v
        else:
            assert isinstance(o, Con_Float)
            return self.v <= o.v


    def gr_eq(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return self.as_int() >= o.v
        else:
            assert isinstance(o, Con_Float)
            return self.v >= o.v


    def gt(self, vm, o):
        o = type_check_number(vm, o)
        if isinstance(o, Con_Int):
            return self.as_int() > o.v
        else:
            assert isinstance(o, Con_Float)
            return self.v > o.v


@con_object_proc
def _new_func_Con_Float(vm):
    (class_, o_o), vargs = vm.decode_args("CO", vargs=True)
    if isinstance(o_o, Con_Int):
        return Con_Float(vm, float(o_o.v))
    elif isinstance(o_o, Con_Float):
        return o_o
    elif isinstance(o_o, Con_String):
        v = None
        try:
            v = float(o_o.v)
        except ValueError:
            vm.raise_helper("Number_Exception", [o_o])
        return Con_Float(vm, v)


@con_object_proc
def _Con_Float_div(vm):
    (self, o_o),_ = vm.decode_args("!N", self_of=Con_Float)
    assert isinstance(self, Con_Float)
    assert isinstance(o_o, Con_Number)
    
    return Con_Float(vm, self.v / o_o.as_float())


@con_object_proc
def _Con_Float_mul(vm):
    (self, o_o),_ = vm.decode_args("!N", self_of=Con_Float)
    assert isinstance(self, Con_Float)
    assert isinstance(o_o, Con_Number)
    
    return Con_Float(vm, self.v * o_o.as_float())


@con_object_proc
def _Con_Float_to_str(vm):
    (self,),_ = vm.decode_args("!", self_of=Con_Float)
    assert isinstance(self, Con_Float)

    return Con_String(vm, str(self.v))


def bootstrap_con_float(vm):
    float_class = vm.get_builtin(BUILTIN_FLOAT_CLASS)
    assert isinstance(float_class, Con_Class)
    float_class.new_func = \
      new_c_con_func(vm, Con_String(vm, "new_Float"), False, _new_func_Con_Float, \
        vm.get_builtin(BUILTIN_BUILTINS_MODULE))

    new_c_con_func_for_class(vm, "/", _Con_Float_div, float_class)
    new_c_con_func_for_class(vm, "*", _Con_Float_mul, float_class)
    new_c_con_func_for_class(vm, "to_str", _Con_Float_to_str, float_class)




################################################################################
# Con_String
#

class Con_String(Con_Boxed_Object):
    __slots__ = ("v",)
    _immutable_fields_ = ("v",)


    def __init__(self, vm, v):
        Con_Boxed_Object.__init__(self, vm, vm.get_builtin(BUILTIN_STRING_CLASS))
        assert v is not None
        self.v = v


    def add(self, vm, o):
        o = type_check_string(vm, o)
        return Con_String(vm, self.v + o.v)


    def eq(self, vm, o):
        if isinstance(o, Con_String):
            return self.v == o.v
        return False


    def neq(self, vm, o):
        if isinstance(o, Con_String):
            return self.v != o.v
        return True


    def le(self, vm, o):
        o = type_check_string(vm, o)
        return self.v < o.v


    def le_eq(self, vm, o):
        o = type_check_string(vm, o)
        return self.v <= o.v


    def gr_eq(self, vm, o):
        o = type_check_string(vm, o)
        return self.v >= o.v


    def gt(self, vm, o):
        o = type_check_string(vm, o)
        return self.v > o.v


    @jit.elidable
    def get_slice(self, vm, i, j):
        i, j = translate_slice_idxs(vm, i, j, len(self.v))
        return Con_String(vm, self.v[i:j])


@con_object_proc
def _Con_String_add(vm):
    (self, o_o),_ = vm.decode_args("SS")
    assert isinstance(self, Con_String)
    assert isinstance(o_o, Con_String)
    
    return Con_String(vm, self.v + o_o.v)


@con_object_proc
def _Con_String_eq(vm):
    (self, o_o),_ = vm.decode_args("SO")
    assert isinstance(self, Con_String)
    
    if isinstance(o_o, Con_String):
        if self.v == o_o.v:
            return vm.get_builtin(BUILTIN_NULL_OBJ)
    return vm.get_builtin(BUILTIN_FAIL_OBJ)


@con_object_gen
def _Con_String_find(vm):
    (self, o_o),_ = vm.decode_args("SS")
    assert isinstance(self, Con_String)
    assert isinstance(o_o, Con_String)

    v = self.v
    o = o_o.v
    o_len = len(o)
    for i in range(0, len(v) - o_len + 1):
        if v[i:i+o_len] == o:
            yield o_o


@con_object_gen
def _Con_String_find_index(vm):
    (self, o_o),_ = vm.decode_args("SS")
    assert isinstance(self, Con_String)
    assert isinstance(o_o, Con_String)

    v = self.v
    o = o_o.v
    o_len = len(o)
    for i in range(0, len(v) - o_len + 1):
        if v[i:i+o_len] == o:
            yield Con_Int(vm, i)


@con_object_proc
def _Con_String_get(vm):
    (self, i_o),_ = vm.decode_args("SI")
    assert isinstance(self, Con_String)
    assert isinstance(i_o, Con_Int)

    return Con_String(vm, self.v[i_o.v])


@con_object_proc
def _Con_String_get_slice(vm):
    (self, i_o, j_o),_ = vm.decode_args("S", opt="ii")
    assert isinstance(self, Con_String)

    i, j = translate_slice_idx_objs(vm, i_o, j_o, len(self.v))

    return Con_String(vm, self.v[i:j])


@con_object_proc
def _Con_String_hash(vm):
    (self,),_ = vm.decode_args("S")
    assert isinstance(self, Con_String)

    return Con_Int(vm, objectmodel.compute_hash(self.v))


@con_object_proc
def _Con_String_int_val(vm):
    (self, i_o),_ = vm.decode_args("S", opt="I")
    assert isinstance(self, Con_String)

    if i_o is not None:
        assert isinstance(i_o, Con_Int)
        i = translate_idx(vm, i_o.v, len(self.v))
    else:
        i = translate_idx(vm, 0, len(self.v))

    return Con_Int(vm, ord(self.v[i]))


@con_object_gen
def _Con_String_iter(vm):
    (self, i_o, j_o),_ = vm.decode_args("S", opt="ii")
    assert isinstance(self, Con_String)
    
    i, j = translate_slice_idx_objs(vm, i_o, j_o, len(self.v))
    while i < j:
        yield Con_String(vm, self.v[i])
        i += 1


@con_object_proc
def _Con_String_len(vm):
    (self,),_ = vm.decode_args("S")
    assert isinstance(self, Con_String)

    return Con_Int(vm, len(self.v))


@con_object_proc
def _Con_String_lower_cased(vm):
    (self,),_ = vm.decode_args("S")
    assert isinstance(self, Con_String)
    
    return Con_String(vm, self.v.lower())


@con_object_proc
def _Con_String_lstripped(vm):
    (self,),_ = vm.decode_args("S")
    assert isinstance(self, Con_String)
    
    v = self.v
    v_len = len(v)
    i = 0
    while i < v_len:
        if v[i] not in " \t\n\r":
            break
        i += 1

    return Con_String(vm, self.v[i:])


@con_object_proc
def _Con_String_mul(vm):
    (self, i_o),_ = vm.decode_args("SI")
    assert isinstance(self, Con_String)
    assert isinstance(i_o, Con_Int)
    
    return Con_String(vm, self.v * i_o.v)


@con_object_proc
def _Con_String_neq(vm):
    (self, o_o),_ = vm.decode_args("SO")
    assert isinstance(self, Con_String)

    if isinstance(o_o, Con_String):
        if self.v != o_o.v:
            return vm.get_builtin(BUILTIN_NULL_OBJ)
        else:
            return vm.get_builtin(BUILTIN_FAIL_OBJ)
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_String_prefixed_by(vm):
    (self, o_o, i_o),_ = vm.decode_args("SS", opt="I")
    assert isinstance(self, Con_String)
    assert isinstance(o_o, Con_String)

    i = translate_slice_idx_obj(vm, i_o, len(self.v))

    if self.v[i:].startswith(o_o.v):
        return vm.get_builtin(BUILTIN_NULL_OBJ)
    else:
        return vm.get_builtin(BUILTIN_FAIL_OBJ)


@con_object_gen
def _Con_String_rfind_index(vm):
    (self, o_o),_ = vm.decode_args("SS")
    assert isinstance(self, Con_String)
    assert isinstance(o_o, Con_String)

    v = self.v
    o = o_o.v
    o_len = len(o)
    for i in range(len(v) - o_len, -1, -1):
        if v[i:i+o_len] == o:
            yield Con_Int(vm, i)


@con_object_proc
def _Con_String_replaced(vm):
    (self, old_o, new_o),_ = vm.decode_args("SSS")
    assert isinstance(self, Con_String)
    assert isinstance(old_o, Con_String)
    assert isinstance(new_o, Con_String)

    v = self.v
    v_len = len(v)
    old = old_o.v
    old_len = len(old)
    new = new_o.v
    out = []
    i = 0
    while i < v_len:
        j = v.find(old, i)
        if j == -1:
            break
        assert j >= i
        out.append(v[i:j])
        out.append(new)
        i = j + old_len
    if i < v_len:
        out.append(v[i:])

    return Con_String(vm, "".join(out))


@con_object_proc
def _Con_String_split(vm):
    (self, o_o),_ = vm.decode_args("SS")
    assert isinstance(self, Con_String)
    assert isinstance(o_o, Con_String)

    return Con_List(vm, [Con_String(vm, x) for x in self.v.split(o_o.v)])


@con_object_proc
def _Con_String_stripped(vm):
    (self,),_ = vm.decode_args("S")
    assert isinstance(self, Con_String)

    v = self.v
    v_len = len(v)
    i = 0
    while i < v_len:
        if v[i] not in " \t\n\r":
            break
        i += 1
    j = v_len - 1
    while j >= i:
        if v[j] not in " \t\n\r":
            break
        j -= 1
    j += 1

    assert j >= i
    return Con_String(vm, self.v[i:j])


@con_object_proc
def _Con_String_suffixed_by(vm):
    (self, o_o, i_o),_ = vm.decode_args("SS", opt="I")
    assert isinstance(self, Con_String)
    assert isinstance(o_o, Con_String)

    if i_o is None:
        i = len(self.v)
    else:
        i = translate_slice_idx_obj(vm, i_o, len(self.v))

    if self.v[:i].endswith(o_o.v):
        return vm.get_builtin(BUILTIN_NULL_OBJ)
    else:
        return vm.get_builtin(BUILTIN_FAIL_OBJ)


@con_object_proc
def _Con_String_to_str(vm):
    (self,),_ = vm.decode_args("S")
    assert isinstance(self, Con_String)

    return Con_String(vm, '"%s"' % self.v)


@con_object_proc
def _Con_String_upper_cased(vm):
    (self,),_ = vm.decode_args("S")
    assert isinstance(self, Con_String)
    
    return Con_String(vm, self.v.upper())


def bootstrap_con_string(vm):
    string_class = vm.get_builtin(BUILTIN_STRING_CLASS)
    assert isinstance(string_class, Con_Class)

    new_c_con_func_for_class(vm, "+", _Con_String_add, string_class)
    new_c_con_func_for_class(vm, "==", _Con_String_eq, string_class)
    new_c_con_func_for_class(vm, "find", _Con_String_find, string_class)
    new_c_con_func_for_class(vm, "find_index", _Con_String_find_index, string_class)
    new_c_con_func_for_class(vm, "get", _Con_String_get, string_class)
    new_c_con_func_for_class(vm, "get_slice", _Con_String_get_slice, string_class)
    new_c_con_func_for_class(vm, "hash", _Con_String_hash, string_class)
    new_c_con_func_for_class(vm, "int_val", _Con_String_int_val, string_class)
    new_c_con_func_for_class(vm, "iter", _Con_String_iter, string_class)
    new_c_con_func_for_class(vm, "len", _Con_String_len, string_class)
    new_c_con_func_for_class(vm, "lower_cased", _Con_String_lower_cased, string_class)
    new_c_con_func_for_class(vm, "lstripped", _Con_String_lstripped, string_class)
    new_c_con_func_for_class(vm, "*", _Con_String_mul, string_class)
    new_c_con_func_for_class(vm, "!=", _Con_String_neq, string_class)
    new_c_con_func_for_class(vm, "prefixed_by", _Con_String_prefixed_by, string_class)
    new_c_con_func_for_class(vm, "replaced", _Con_String_replaced, string_class)
    new_c_con_func_for_class(vm, "rfind_index", _Con_String_rfind_index, string_class)
    new_c_con_func_for_class(vm, "split", _Con_String_split, string_class)
    new_c_con_func_for_class(vm, "stripped", _Con_String_stripped, string_class)
    new_c_con_func_for_class(vm, "suffixed_by", _Con_String_suffixed_by, string_class)
    new_c_con_func_for_class(vm, "to_str", _Con_String_to_str, string_class)
    new_c_con_func_for_class(vm, "upper_cased", _Con_String_upper_cased, string_class)



################################################################################
# Con_List
#

class Con_List(Con_Boxed_Object):
    __slots__ = ("l",)
    _immutable_fields_ = ("l",)

    def __init__(self, vm, l, instance_of=None):
        assert None not in l
        if instance_of is None:
            instance_of = vm.get_builtin(BUILTIN_LIST_CLASS)
        Con_Boxed_Object.__init__(self, vm, instance_of)
        self.l = l


@con_object_proc
def _new_func_Con_List(vm):
    (class_,), vargs = vm.decode_args("C", vargs=True)
    
    o = Con_List(vm, [], class_)
    vm.apply(o.get_slot(vm, "init"), vargs)
    return o


@con_object_proc
def _Con_List_init(vm):
    (self, o_o,), _ = vm.decode_args("L", opt="O")
    assert isinstance(self, Con_List)
    
    if isinstance(o_o, Con_List):
        self.l = o_o.l[:]
    elif o_o:
        vm.pre_get_slot_apply_pump(o_o, "iter")
        while 1:
            e_o = vm.apply_pump()
            if not e_o:
                break
            self.l.append(e_o)

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_List_add(vm):
    (self, o_o),_ = vm.decode_args("LO")
    assert isinstance(self, Con_List)
    
    if isinstance(o_o, Con_List):
        new_l = self.l + o_o.l
    else:
        new_l = self.l[:]
        vm.pre_get_slot_apply_pump(o_o, "iter")
        while 1:
            e_o = vm.apply_pump()
            if not e_o:
                break
            new_l.append(e_o)
    return Con_List(vm, new_l)


@con_object_proc
def _Con_List_append(vm):
    (self, o),_ = vm.decode_args("LO")
    assert isinstance(self, Con_List)
    
    self.l.append(o)
    return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_List_del(vm):
    (self, i_o),_ = vm.decode_args("LI")
    assert isinstance(self, Con_List)
    assert isinstance(i_o, Con_Int)

    del self.l[translate_idx(vm, i_o.v, len(self.l))]

    return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_List_del_slice(vm):
    (self, i_o, j_o),_ = vm.decode_args("L", opt="ii")
    assert isinstance(self, Con_List)
    assert isinstance(i_o, Con_Int)

    i, j = translate_slice_idx_objs(vm, i_o, j_o, len(self.l))
    del self.l[i:j]

    return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_List_extend(vm):
    (self, o_o),_ = vm.decode_args("LO")
    assert isinstance(self, Con_List)
    
    if isinstance(o_o, Con_List):
        self.l.extend(o_o.l)
    else:
        vm.pre_get_slot_apply_pump(o_o, "iter")
        while 1:
            e_o = vm.apply_pump()
            if not e_o:
                break
            self.l.append(e_o)
    return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_List_eq(vm):
    (self, o_o),_ = vm.decode_args("LO")
    assert isinstance(self, Con_List)
    
    if isinstance(o_o, Con_List):
        self_len = len(self.l)
        if self_len != len(o_o.l):
            return vm.get_builtin(Builtins.BUILTIN_FAIL_OBJ)

        self_l = self.l
        o_l = o_o.l
        for i in range(0, self_len):
            if not self_l[i].eq(vm, o_l[i]):
                return vm.get_builtin(Builtins.BUILTIN_FAIL_OBJ)
        return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)

    return vm.get_builtin(Builtins.BUILTIN_FAIL_OBJ)


@con_object_gen
def _Con_List_find(vm):
    (self, o),_ = vm.decode_args("LO")
    assert isinstance(self, Con_List)
    
    for e in self.l:
        if o.eq(vm, e):
            yield vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_gen
def _Con_List_find_index(vm):
    (self, o),_ = vm.decode_args("LO")
    assert isinstance(self, Con_List)
    
    i = 0
    for e in self.l:
        if e.eq(vm, o):
            yield Con_Int(vm, i)
        i += 1


@con_object_proc
def _Con_List_flattened(vm):
    (self,),_ = vm.decode_args("L")
    assert isinstance(self, Con_List)
    
    f = []
    for e in self.l:
        if isinstance(e, Con_List):
            f.extend(type_check_list(vm, vm.get_slot_apply(e, "flattened")).l)
        else:
            f.append(e)
    
    return Con_List(vm, f)


@con_object_proc
def _Con_List_get(vm):
    (self, i_o),_ = vm.decode_args("LI")
    assert isinstance(self, Con_List)
    assert isinstance(i_o, Con_Int)

    i = translate_idx(vm, i_o.v, len(self.l))
    
    return self.l[i]


@con_object_proc
def _Con_List_get_slice(vm):
    (self, i_o, j_o),_ = vm.decode_args("L", opt="ii")
    assert isinstance(self, Con_List)

    i, j = translate_slice_idx_objs(vm, i_o, j_o, len(self.l))

    return Con_List(vm, self.l[i:j])


@con_object_proc
def _Con_List_insert(vm):
    (self, i_o, o_o),_ = vm.decode_args("LIO")
    assert isinstance(self, Con_List)
    assert isinstance(i_o, Con_Int)
    
    self.l.insert(translate_slice_idx(vm, i_o.v, len(self.l)), o_o)

    return vm.get_builtin(BUILTIN_FAIL_OBJ)


@con_object_gen
def _Con_List_iter(vm):
    (self, i_o, j_o),_ = vm.decode_args("L", opt="ii")
    assert isinstance(self, Con_List)
    
    i, j = translate_slice_idx_objs(vm, i_o, j_o, len(self.l))
    while i < j:
        yield self.l[i]
        i += 1


@con_object_proc
def _Con_List_len(vm):
    (self,),_ = vm.decode_args("L")
    assert isinstance(self, Con_List)
    
    return Con_Int(vm, len(self.l))


@con_object_proc
def _Con_List_mult(vm):
    (self, i_o),_ = vm.decode_args("LI")
    assert isinstance(self, Con_List)
    assert isinstance(i_o, Con_Int)

    return Con_List(vm, self.l * i_o.v)


@con_object_proc
def _Con_List_neq(vm):
    (self, o_o),_ = vm.decode_args("LL")
    assert isinstance(self, Con_List)
    
    if isinstance(o_o, Con_List):
        self_len = len(self.l)
        if self_len != len(o_o.l):
            return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)

        self_l = self.l
        o_l = o_o.l
        for i in range(0, self_len):
            if not self_l[i].neq(vm, o_l[i]):
                return vm.get_builtin(Builtins.BUILTIN_FAIL_OBJ)
        return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)
    else:
        return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_List_pop(vm):
    (self,),_ = vm.decode_args("L")
    assert isinstance(self, Con_List)
    
    translate_slice_idx(vm, -1, len(self.l))

    return self.l.pop()


@con_object_gen
def _Con_List_remove(vm):
    (self, o_o),_ = vm.decode_args("LO")
    assert isinstance(self, Con_List)

    i = 0
    l = self.l
    while i < len(l):
        e = l[i]
        if o_o.eq(vm, e):
            del l[i]
            yield e
        else:
            i += 1


@con_object_gen
def _Con_List_riter(vm):
    (self, i_o, j_o),_ = vm.decode_args("L", opt="ii")
    assert isinstance(self, Con_List)
    
    i, j = translate_slice_idx_objs(vm, i_o, j_o, len(self.l))
    j -= 1
    while j >= i:
        yield self.l[j]
        j -= 1


@con_object_proc
def _Con_List_set(vm):
    (self, i, o),_ = vm.decode_args("LIO")
    assert isinstance(self, Con_List)
    assert isinstance(i, Con_Int)
    self.l[i.v] = o
    return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_List_set_slice(vm):
    (self, i_o, j_o, o_o),_ = vm.decode_args("LiiL")
    assert isinstance(self, Con_List)
    assert isinstance(o_o, Con_List)

    i, j = translate_slice_idx_objs(vm, i_o, j_o, len(self.l))
    # Setting slices in RPython is currently broken.
    # self.l[i:j] = o_o.l
    # For the time, use a slow but simple work around.
    del self.l[i:j]
    for e in o_o.l:
        self.l.insert(i, e)
        i += 1

    return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_List_to_str(vm):
    (self,),_ = vm.decode_args("L")
    assert isinstance(self, Con_List)
    
    es = []
    for e in self.l:
        s = type_check_string(vm, vm.get_slot_apply(e, "to_str"))
        es.append(s.v)

    return Con_String(vm, "[%s]" % ", ".join(es))


def bootstrap_con_list(vm):
    list_class = vm.get_builtin(BUILTIN_LIST_CLASS)
    assert isinstance(list_class, Con_Class)
    list_class.new_func = \
      new_c_con_func(vm, Con_String(vm, "new_List"), False, _new_func_Con_List, \
        vm.get_builtin(BUILTIN_BUILTINS_MODULE))

    new_c_con_func_for_class(vm, "init", _Con_List_init, list_class)
    new_c_con_func_for_class(vm, "+", _Con_List_add, list_class)
    new_c_con_func_for_class(vm, "append", _Con_List_append, list_class)
    new_c_con_func_for_class(vm, "del", _Con_List_del, list_class)
    new_c_con_func_for_class(vm, "del_slice", _Con_List_del_slice, list_class)
    new_c_con_func_for_class(vm, "extend", _Con_List_extend, list_class)
    new_c_con_func_for_class(vm, "==", _Con_List_eq, list_class)
    new_c_con_func_for_class(vm, "find", _Con_List_find, list_class)
    new_c_con_func_for_class(vm, "find_index", _Con_List_find_index, list_class)
    new_c_con_func_for_class(vm, "flattened", _Con_List_flattened, list_class)
    new_c_con_func_for_class(vm, "get", _Con_List_get, list_class)
    new_c_con_func_for_class(vm, "get_slice", _Con_List_get_slice, list_class)
    new_c_con_func_for_class(vm, "insert", _Con_List_insert, list_class)
    new_c_con_func_for_class(vm, "iter", _Con_List_iter, list_class)
    new_c_con_func_for_class(vm, "len", _Con_List_len, list_class)
    new_c_con_func_for_class(vm, "*", _Con_List_mult, list_class)
    new_c_con_func_for_class(vm, "!=", _Con_List_neq, list_class)
    new_c_con_func_for_class(vm, "pop", _Con_List_pop, list_class)
    new_c_con_func_for_class(vm, "remove", _Con_List_remove, list_class)
    new_c_con_func_for_class(vm, "riter", _Con_List_riter, list_class)
    new_c_con_func_for_class(vm, "set", _Con_List_set, list_class)
    new_c_con_func_for_class(vm, "set_slice", _Con_List_set_slice, list_class)
    new_c_con_func_for_class(vm, "to_str", _Con_List_to_str, list_class)



################################################################################
# Con_Set
#

class Con_Set(Con_Boxed_Object):
    __slots__ = ("s", "vm")
    _immutable_fields_ = ("s",)


    def __init__(self, vm, l, instance_of=None):
        if instance_of is None:
            instance_of = vm.get_builtin(BUILTIN_SET_CLASS)
        Con_Boxed_Object.__init__(self, vm, instance_of)
        # RPython doesn't have sets, so we use dictionaries for the time being
        self.s = objectmodel.r_dict(_dict_key_eq, _dict_key_hash)
        for e in l:
            self.s[e] = None


@con_object_proc
def _Con_Set_add(vm):
    (self, o),_ = vm.decode_args("WO")
    assert isinstance(self, Con_Set)
    
    self.s[o] = None

    return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_Set_add_plus(vm):
    (self, o_o),_ = vm.decode_args("WO")
    assert isinstance(self, Con_Set)
    
    n_o = Con_Set(vm, self.s.keys())
    vm.get_slot_apply(n_o, "extend", [o_o])

    return n_o


@con_object_proc
def _Con_Set_complement(vm):
    (self, o_o),_ = vm.decode_args("WO")
    assert isinstance(self, Con_Set)

    n_s = []
    for k in self.s.keys():
        if isinstance(o_o, Con_Set):
            if k not in o_o.s:
                n_s.append(k)
        else:
            raise Exception("XXX")
    
    return Con_Set(vm, n_s)


@con_object_proc
def _Con_Set_extend(vm):
    (self, o_o),_ = vm.decode_args("WO")
    assert isinstance(self, Con_Set)

    if isinstance(o_o, Con_Set):
        for k in o_o.s.keys():
            self.s[k] = None
    else:
        vm.pre_get_slot_apply_pump(o_o, "iter")
        while 1:
            e_o = vm.apply_pump()
            if not e_o:
                break
            self.s[e_o] = None

    return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)


@con_object_gen
def _Con_Set_find(vm):
    (self, o),_ = vm.decode_args("WO")
    assert isinstance(self, Con_Set)
    
    if o in self.s:
        yield o


@con_object_gen
def _Con_Set_iter(vm):
    (self,),_ = vm.decode_args("W")
    assert isinstance(self, Con_Set)
    
    for k in self.s.keys():
        yield k


@con_object_proc
def _Con_Set_len(vm):
    (self,),_ = vm.decode_args("W")
    assert isinstance(self, Con_Set)
    
    return Con_Int(vm, len(self.s))


@con_object_proc
def _Con_Set_scopy(vm):
    (self,),_ = vm.decode_args("W")
    assert isinstance(self, Con_Set)
    
    return Con_Set(vm, self.s.keys())


@con_object_proc
def _Con_Set_to_str(vm):
    (self,),_ = vm.decode_args("W")
    assert isinstance(self, Con_Set)
    
    es = []
    for e in self.s.keys():
        s = type_check_string(vm, vm.get_slot_apply(e, "to_str"))
        es.append(s.v)

    return Con_String(vm, "Set{%s}" % ", ".join(es))


def bootstrap_con_set(vm):
    set_class = vm.get_builtin(BUILTIN_SET_CLASS)
    assert isinstance(set_class, Con_Class)

    new_c_con_func_for_class(vm, "add", _Con_Set_add, set_class)
    new_c_con_func_for_class(vm, "+", _Con_Set_add_plus, set_class)
    new_c_con_func_for_class(vm, "complement", _Con_Set_complement, set_class)
    new_c_con_func_for_class(vm, "extend", _Con_Set_extend, set_class)
    new_c_con_func_for_class(vm, "find", _Con_Set_find, set_class)
    new_c_con_func_for_class(vm, "iter", _Con_Set_iter, set_class)
    new_c_con_func_for_class(vm, "len", _Con_Set_len, set_class)
    new_c_con_func_for_class(vm, "scopy", _Con_Set_scopy, set_class)
    new_c_con_func_for_class(vm, "to_str", _Con_Set_to_str, set_class)



################################################################################
# Con_Dict
#

class Con_Dict(Con_Boxed_Object):
    __slots__ = ("d",)
    _immutable_fields_ = ("d",)


    def __init__(self, vm, l, instance_of=None):
        if instance_of is None:
            instance_of = vm.get_builtin(BUILTIN_DICT_CLASS)
        Con_Boxed_Object.__init__(self, vm, instance_of)
        self.d = objectmodel.r_dict(_dict_key_eq, _dict_key_hash)
        i = 0
        while i < len(l):
            self.d[l[i]] = l[i + 1]
            i += 2


def _dict_key_hash(k):
    vm = VM.global_vm # XXX Offensively gross hack!
    return int(Builtins.type_check_int(vm, vm.get_slot_apply(k, "hash")).v)


def _dict_key_eq(k1, k2):
    vm = VM.global_vm # XXX Offensively gross hack!
    if vm.get_slot_apply(k1, "==", [k2], allow_fail=True):
        return True
    else:
        return False


@con_object_proc
def _Con_Dict_find(vm):
    (self, k),_ = vm.decode_args("DO")
    assert isinstance(self, Con_Dict)
    
    r = self.d.get(k, None)
    if r is None:
        return vm.get_builtin(BUILTIN_FAIL_OBJ)
    
    return r


@con_object_proc
def _Con_Dict_extend(vm):
    (self, o),_ = vm.decode_args("DD")
    assert isinstance(self, Con_Dict)
    assert isinstance(o, Con_Dict)
    
    for k, v in o.d.items():
        self.d[k] = v
    
    return vm.get_builtin(BUILTIN_FAIL_OBJ)


@con_object_proc
def _Con_Dict_get(vm):
    (self, k),_ = vm.decode_args("DO")
    assert isinstance(self, Con_Dict)
    
    r = self.d.get(k, None)
    if r is None:
        vm.raise_helper("Key_Exception", [k])
    
    return r


@con_object_gen
def _Con_Dict_iter(vm):
    (self,),_ = vm.decode_args("D")
    assert isinstance(self, Con_Dict)

    for k, v in self.d.items():
        yield Con_List(vm, [k, v])


@con_object_gen
def _Con_Dict_iter_keys(vm):
    (self,),_ = vm.decode_args("D")
    assert isinstance(self, Con_Dict)

    for v in self.d.keys():
        yield v


@con_object_gen
def _Con_Dict_iter_vals(vm):
    (self,),_ = vm.decode_args("D")
    assert isinstance(self, Con_Dict)

    for v in self.d.values():
        yield v


@con_object_proc
def _Con_Dict_len(vm):
    (self,),_ = vm.decode_args("D")
    assert isinstance(self, Con_Dict)
    
    return Con_Int(vm, len(self.d))


@con_object_proc
def _Con_Dict_set(vm):
    (self, k, v),_ = vm.decode_args("DOO")
    assert isinstance(self, Con_Dict)
    
    self.d[k] = v
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Con_Dict_scopy(vm):
    (self,),_ = vm.decode_args("D")
    assert isinstance(self, Con_Dict)

    n_o = Con_Dict(vm, [])
    for k, v in self.d.items():
        n_o.d[k] = v

    return n_o


@con_object_proc
def _Con_Dict_to_str(vm):
    (self,),_ = vm.decode_args("D")
    assert isinstance(self, Con_Dict)
    
    es = []
    for k, v in self.d.items():
        ks = type_check_string(vm, vm.get_slot_apply(k, "to_str"))
        vs = type_check_string(vm, vm.get_slot_apply(v, "to_str"))
        es.append("%s : %s" % (ks.v, vs.v))

    return Con_String(vm, "Dict{%s}" % ", ".join(es))


def bootstrap_con_dict(vm):
    dict_class = vm.get_builtin(BUILTIN_DICT_CLASS)
    assert isinstance(dict_class, Con_Class)

    new_c_con_func_for_class(vm, "extend", _Con_Dict_extend, dict_class)
    new_c_con_func_for_class(vm, "find", _Con_Dict_find, dict_class)
    new_c_con_func_for_class(vm, "get", _Con_Dict_get, dict_class)
    new_c_con_func_for_class(vm, "iter", _Con_Dict_iter, dict_class)
    new_c_con_func_for_class(vm, "iter_keys", _Con_Dict_iter_keys, dict_class)
    new_c_con_func_for_class(vm, "iter_vals", _Con_Dict_iter_vals, dict_class)
    new_c_con_func_for_class(vm, "len", _Con_Dict_len, dict_class)
    new_c_con_func_for_class(vm, "scopy", _Con_Dict_scopy, dict_class)
    new_c_con_func_for_class(vm, "set", _Con_Dict_set, dict_class)
    new_c_con_func_for_class(vm, "to_str", _Con_Dict_to_str, dict_class)



################################################################################
# Con_Exception
#

class Con_Exception(Con_Boxed_Object):
    __slots__ = ("call_chain",)
    _immutable_fields_ = ()


    def __init__(self, vm, instance_of=None):
        if instance_of is None:
            instance_of = vm.get_builtin(BUILTIN_EXCEPTION_CLASS)
        Con_Boxed_Object.__init__(self, vm, instance_of)
        self.call_chain = None


@con_object_proc
def _new_func_Con_Exception(vm):
    (class_, ), vargs = vm.decode_args("C", vargs=True)
    o = Con_Exception(vm, class_)
    vm.apply(o.get_slot(vm, "init"), vargs)
    return o


@con_object_proc
def _Con_Exception_init(vm):
    (self, msg),_ = vm.decode_args("O", opt="O")
    if msg is None:
        self.set_slot(vm, "msg", Con_String(vm, ""))
    else:
        self.set_slot(vm, "msg", msg)
    return vm.get_builtin(Builtins.BUILTIN_NULL_OBJ)


@con_object_gen
def _Con_Exception_iter_call_chain(vm):
    (self,),_ = vm.decode_args("E")
    assert isinstance(self, Con_Exception)

    for pc, func, bc_off in self.call_chain:
        if isinstance(pc, BC_PC):
            src_infos = pc.mod.bc_off_to_src_infos(vm, bc_off)
        else:
            assert isinstance(pc, Py_PC)
            src_infos = vm.get_builtin(BUILTIN_NULL_OBJ)
        yield Con_List(vm, [func, src_infos])


@con_object_proc
def _Con_Exception_to_str(vm):
    (self,),_ = vm.decode_args("E")
    ex_name = type_check_string(vm, self.get_slot(vm, "instance_of").get_slot(vm, "name"))
    msg = type_check_string(vm, self.get_slot(vm, "msg"))
    return Con_String(vm, "%s: %s" % (ex_name.v, msg.v))


def bootstrap_con_exception(vm):
    exception_class = vm.get_builtin(BUILTIN_EXCEPTION_CLASS)
    assert isinstance(exception_class, Con_Class)
    exception_class.new_func = \
      new_c_con_func(vm, Con_String(vm, "new_Exception"), False, _new_func_Con_Exception, \
        vm.get_builtin(BUILTIN_BUILTINS_MODULE))

    new_c_con_func_for_class(vm, "init", _Con_Exception_init, exception_class)
    new_c_con_func_for_class(vm, "iter_call_chain", _Con_Exception_iter_call_chain, exception_class)
    new_c_con_func_for_class(vm, "to_str", _Con_Exception_to_str, exception_class)



################################################################################
# Convenience type checking functions
#

# Note that the returning of the object passed for type-checking is just about convenience -
# calling functions can safely ignore the return value if that's easier for them. However,
# if ignored, RPython doesn't infer that the object pointed to by o is of the correct type,
# so generally one wants to write:
#
#   o = type_check_X(vm, z)


def type_check_class(vm, o):
    if not isinstance(o, Con_Class):
        vm.raise_helper("Type_Exception", [vm.get_builtin(BUILTIN_CLASS_CLASS), o])
    return o


def type_check_dict(vm, o):
    if not isinstance(o, Con_Dict):
        vm.raise_helper("Type_Exception", [Con_String(vm, "Dict"), o])
    return o


def type_check_exception(vm, o):
    if not isinstance(o, Con_Exception):
        vm.raise_helper("Type_Exception", [Con_String(vm, "Exception"), o])
    return o


def type_check_number(vm, o):
    if not (isinstance(o, Con_Int) or isinstance(o, Con_Float)):
        vm.raise_helper("Type_Exception", [Con_String(vm, "Number"), o])
    return o


def type_check_int(vm, o):
    if not isinstance(o, Con_Int):
        vm.raise_helper("Type_Exception", [Con_String(vm, "Int"), o])
    return o


def type_check_func(vm, o):
    if not isinstance(o, Con_Func):
        vm.raise_helper("Type_Exception", [Con_String(vm, "Func"), o])
    return o


def type_check_list(vm, o):
    if not isinstance(o, Con_List):
        vm.raise_helper("Type_Exception", [Con_String(vm, "List"), o])
    return o


def type_check_module(vm, o):
    if not isinstance(o, Con_Module):
        vm.raise_helper("Type_Exception", [Con_String(vm, "Module"), o])
    return o


def type_check_set(vm, o):
    if not isinstance(o, Con_Set):
        vm.raise_helper("Type_Exception", [Con_String(vm, "Set"), o])
    return o


def type_check_string(vm, o):
    if not isinstance(o, Con_String):
        vm.raise_helper("Type_Exception", [Con_String(vm, "String"), o])
    return o

########NEW FILE########
__FILENAME__ = Bytecode
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from rpython.rlib import jit
from rpython.rtyper.lltypesystem import lltype, rffi

from Target import *
from VM import *
import Builtins





@jit.elidable_promote()
def _extract_sstr(bc, soff, ssize):
    off = read_word(bc, soff)
    size = read_word(bc, ssize)
    return Target.extract_str(bc, off, size)


def add_exec(vm, bc):
    main_mod_id = None
    for i in range(read_word(bc, BC_HD_NUM_MODULES)):
        mod_off = read_word(bc, BC_HD_MODULES + i * INTSIZE)
        mod = mk_mod(vm, bc, mod_off)
        vm.set_mod(mod)
        if main_mod_id is None:
            main_mod_id = mod.id_

    return main_mod_id


#
# XXX This is intended to be a part of a poor mans dynamic linker. It is very limited; in particular
# it doesn't handle packages properly.
#

def add_lib(vm, bc):
    for i in range(read_word(bc, BC_LIB_HD_NUM_MODULES)):
        mod_off = read_word(bc, BC_LIB_HD_MODULES + i * INTSIZE)
        
        if extract_str(bc, mod_off, 8) == "CONVPACK":
            # XXX we simply skip packages currently. This needs more thought.
            continue
        
        mod_bc = rffi.ptradd(bc, mod_off)
        id_ = _extract_sstr(mod_bc, BC_MOD_ID, BC_MOD_ID_SIZE)
        if not vm.has_mod(id_):
            vm.set_mod(mk_mod(vm, bc, mod_off))


def mk_mod(vm, bc, mod_off):
    mod_size = read_word(bc, mod_off + BC_MOD_SIZE)
    assert mod_off >= 0 and mod_size >= 0

    mod_bc = rffi.ptradd(bc, mod_off)

    name = _extract_sstr(mod_bc, BC_MOD_NAME, BC_MOD_NAME_SIZE)
    id_ = _extract_sstr(mod_bc, BC_MOD_ID, BC_MOD_ID_SIZE)
    src_path = _extract_sstr(mod_bc, BC_MOD_SRC_PATH, BC_MOD_SRC_PATH_SIZE)

    imps = []
    j = read_word(mod_bc, BC_MOD_IMPORTS)
    for k in range(read_word(mod_bc, BC_MOD_NUM_IMPORTS)):
        assert j > 0
        imp_size = read_word(mod_bc, j)
        assert imp_size > 0
        j += INTSIZE
        imps.append(rffi.charpsize2str(rffi.ptradd(mod_bc, j), imp_size))
        j += align(imp_size)
        j += INTSIZE + align(read_word(mod_bc, j))

    num_vars = read_word(mod_bc, BC_MOD_NUM_TL_VARS_MAP)
    tlvars_map = {}
    j = read_word(mod_bc, BC_MOD_TL_VARS_MAP)
    for k in range(num_vars):
        assert j > 0
        var_num = read_word(mod_bc, j)
        j += INTSIZE
        tlvar_size = read_word(mod_bc, j)
        assert tlvar_size > 0
        j += INTSIZE
        n = rffi.charpsize2str(rffi.ptradd(mod_bc, j), tlvar_size)
        tlvars_map[n] = var_num
        j += align(tlvar_size)

    num_consts = read_word(mod_bc, BC_MOD_NUM_CONSTANTS)

    mod = Builtins.new_bc_con_module(vm, mod_bc, name, id_, src_path, imps, tlvars_map, num_consts)
    init_func_off = read_word(mod_bc, BC_MOD_INSTRUCTIONS)
    pc = BC_PC(mod, init_func_off)
    max_stack_size = 512 # XXX!
    mod.init_func = Builtins.Con_Func(vm, Builtins.Con_String(vm, "$$init$$"), False, pc, \
      max_stack_size, 0, num_vars, mod, None)
    
    return mod


def exec_upto_date(vm, bc, mtime):
    for i in range(read_word(bc, BC_HD_NUM_MODULES)):
        mod_off = read_word(bc, BC_HD_MODULES + i * INTSIZE)
        mod_bc = rffi.ptradd(bc, mod_off)
        src_path = _extract_sstr(mod_bc, BC_MOD_SRC_PATH, BC_MOD_SRC_PATH_SIZE)
        
        try:
            st = os.stat(src_path)
        except OSError:
            continue
        if st.st_mtime > mtime:
            return False

    return True
########NEW FILE########
__FILENAME__ = Core
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import inspect, sys
import Builtins





################################################################################
# Configuration
#

if sys.platform.startswith("win"):
    CASE_SENSITIVE_FILENAMES = 0
else:
    CASE_SENSITIVE_FILENAMES = 1

if sys.byteorder == "big":
    ENDIANNESS = "BIG_ENDIAN"
else:
    ENDIANNESS = "LITTLE_ENDIAN"




################################################################################
# The root object
#

class Con_Thingy(object):
    __slots__ = ()



################################################################################
# PC objects
#

class PC(object):
    __slots__ = ("mod")
    _immutable_fields_ = ("mod",)


class BC_PC(PC):
    __slots__ = ("off")
    _immutable_fields_ = ("mod", "off")
    
    def __init__(self, mod, off):
        assert isinstance(mod, Builtins.Con_Module)
        self.mod = mod
        self.off = off


class Py_PC(PC):
    __slots__ = ("f")
    _immutable_fields_ = ("mod", "f")

    def __init__(self, mod, f):
        assert isinstance(mod, Builtins.Con_Module)
        self.mod = mod
        self.f = f



################################################################################
# Generator support
#

class Con_Gen_Proc:
    _immutable_ = True
    def __init__(self):
        pass
    def next(self):
        raise NotImplementedError


class Class_Con_Gen(Con_Gen_Proc):
    _immutable_ = True


class Class_Con_Proc(Con_Gen_Proc):
    _immutable_ = True


def con_object_gen(pyfunc):
    assert inspect.isgeneratorfunction(pyfunc)
    class _Tmp_Gen(Class_Con_Gen):
        _immutable_ = True
        def __init__(self, *args):
            self._gen = pyfunc(*args)
        def next(self):
            return self._gen.next()
    _Tmp_Gen.__name__ = "gen__%s__%s" % (pyfunc.__module__.replace(".", "_"), pyfunc.__name__)
    return _Tmp_Gen


def con_object_proc(pyfunc):
    assert inspect.isfunction(pyfunc) and not inspect.isgeneratorfunction(pyfunc)
    class _Tmp_Proc(Class_Con_Proc):
        _immutable_ = True
        def __init__(self, *args):
            self._args = args
        def next(self):
            return pyfunc(*self._args)
    _Tmp_Proc.__name__ = "proc__%s__%s" % (pyfunc.__module__.replace(".", "_"), pyfunc.__name__)
    return _Tmp_Proc



################################################################################
# Index translation
#

def translate_idx(vm, i, upper):
    if i < 0:
        i = upper + i
    
    if i < 0 or i >= upper:
        vm.raise_helper("Bounds_Exception", \
          [Builtins.Con_Int(vm, i), Builtins.Con_Int(vm, upper)])

    return i


def translate_idx_obj(vm, i_o, upper):
    if i_o is None:
        i = 0
    else:
        assert isinstance(i_o, Builtins.Con_Int)
        i = i_o.v
    return translate_idx(vm, i, upper)


def translate_slice_idx(vm, i, upper):
    if i < 0:
        i = upper + i
    
    if i < 0 or i > upper:
        vm.raise_helper("Bounds_Exception", \
          [Builtins.Con_Int(vm, i), Builtins.Con_Int(vm, upper)])

    return i


def translate_slice_idx_obj(vm, i_o, upper):
    if i_o is None:
        i = 0
    else:
        assert isinstance(i_o, Builtins.Con_Int)
        i = i_o.v
    return translate_slice_idx(vm, i, upper)


def translate_slice_idxs(vm, i, j, upper):
    i = translate_slice_idx(vm, i, upper)
    j = translate_slice_idx(vm, j, upper)
    if j < i:
        vm.raise_helper("Indices_Exception", \
          [Builtins.Con_Int(vm, i), Builtins.Con_Int(vm, j)])

    return i, j


def translate_slice_idx_objs(vm, i_o, j_o, upper):
    if i_o is None:
        i = 0
    else:
        assert isinstance(i_o, Builtins.Con_Int)
        i = i_o.v
    if j_o is None: 
        j = upper
    else:
        assert isinstance(j_o, Builtins.Con_Int)
        j = j_o.v

    return translate_slice_idxs(vm, i, j, upper)

########NEW FILE########
__FILENAME__ = main
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import os, sys
sys.path.append(os.getenv("PYPY_SRC"))
print sys.path
try:
    import pypy
except:
    sys.setrecursionlimit(20000)
    
from rpython.rlib import rarithmetic, rposix
from rpython.rlib.jit import *
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform as platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo
import os, os.path, sys
import Builtins, Bytecode, Config, Stdlib_Modules, VM



eci         = ExternalCompilationInfo(includes=["limits.h", "stdlib.h", "string.h"])

class CConfig:
    _compilation_info_ = eci
    BUFSIZ             = platform.DefinedConstantInteger("BUFSIZ")
    PATH_MAX           = platform.DefinedConstantInteger("PATH_MAX")

cconfig  = platform.configure(CConfig)

BUFSIZ   = cconfig["BUFSIZ"]
PATH_MAX = cconfig["PATH_MAX"]
getenv   = rffi.llexternal("getenv", [rffi.CCHARP], rffi.CCHARP, compilation_info=eci)
realpath = rffi.llexternal("realpath", [rffi.CCHARP, rffi.CCHARP], rffi.CCHARP, compilation_info=eci)
strlen   = rffi.llexternal("strlen", [rffi.CCHARP], rffi.SIZE_T, compilation_info=eci)



STDLIB_DIRS = ["../lib/converge-%s/" % Config.CON_VERSION, "../lib/"]
COMPILER_DIRS = ["../lib/converge-%s/" % Config.CON_VERSION, "../compiler/"]


def entry_point(argv):
    vm_path = _get_vm_path(argv)
    
    verbosity = 0
    mk_fresh = False
    i = 1
    for i in range(1, len(argv)):
        arg = argv[i]
        if len(arg) == 0 or (len(arg) == 1 and arg[0] == "-"):
            _usage(vm_path)
            return 1
        if arg[0] == "-":
            for c in arg[1:]:
                if c == "v":
                    verbosity += 1
                elif c == "f":
                    mk_fresh = True
                else:
                    _usage(vm_path)
                    return 1
        else:
            break
    if i < len(argv):
        filename = argv[i]
        if i + 1 < len(argv):
            args = argv[i + 1 : ]
        else:
            args = []
    else:
        filename = None
        args = []

    if filename is None:
        convergeip = _find_con_exec(vm_path, "convergei")
        if convergeip is None:
            return 1
        filename = convergeip

    progp = _canon_path(filename)
    bc, start = _read_bc(progp, "CONVEXEC")
    if len(bc) == 0:
        _error(vm_path, "No such file '%s'." % filename)
        return 1
    
    if start == -1:
        bc, start, rtn = _make_mode(vm_path, progp, bc, verbosity, mk_fresh)
        if rtn != 0:
            return rtn

    if start == -1:
        _error(vm_path, "No valid bytecode to run.")
        return 1

    assert start >= 0
    useful_bc = rffi.str2charp(bc[start:])
    vm = VM.new_vm(vm_path, args)
    _import_lib(vm, "Stdlib.cvl", vm_path, STDLIB_DIRS)
    _import_lib(vm, "Compiler.cvl", vm_path, COMPILER_DIRS)
    try:
        main_mod_id = Bytecode.add_exec(vm, useful_bc)
        mod = vm.get_mod(main_mod_id)
        mod.import_(vm)
        vm.apply(mod.get_defn(vm, "main"))
    except VM.Con_Raise_Exception, e:
        ex_mod = vm.get_builtin(Builtins.BUILTIN_EXCEPTIONS_MODULE)
        sys_ex_class = ex_mod.get_defn(vm, "System_Exit_Exception")
        if vm.get_slot_apply(sys_ex_class, "instantiated", [e.ex_obj], allow_fail=True) is not None:
            code = Builtins.type_check_int(vm, e.ex_obj.get_slot(vm, "code"))
            return int(code.v)
        else:
            pb = vm.import_stdlib_mod(Stdlib_Modules.STDLIB_BACKTRACE).get_defn(vm, "print_best")
            vm.apply(pb, [e.ex_obj])
            return 1
    
    return 0


def _get_vm_path(argv):
    if os.path.exists(argv[0]):
        # argv[0] points to a real file - job done.
        return _canon_path(argv[0])

    # We fall back on searching through $PATH (if it's available) to see if we can find an
    # executable of the name argv[0]
    raw_PATH = getenv("PATH")
    if raw_PATH:
        PATH = rffi.charp2str(raw_PATH)
        for d in PATH.split(":"):
            d = d.strip(" ")
            cnd = os.path.join(d, argv[0])
            if os.path.exists(cnd):
                return _canon_path(cnd)

    # At this point, everything we've tried has failed
    return ""


def _read_bc(path, id_):
    try:
        s = os.stat(path).st_size
        f = os.open(path, os.O_RDONLY, 0777)
        bc = ""
        i = 0
        while i < s:
            d = os.read(f, 64 * 1024)
            bc += d
            i += len(d)
        os.close(f)

        i = 0
        s = os.stat(path).st_size
        i = bc.find(id_)
    except OSError:
        return "", -1

    return bc, i


def _import_lib(vm, leaf, vm_path, cnd_dirs):
    vm_dir = _dirname(vm_path)
    for d in cnd_dirs:
        path = "%s/%s/%s" % (vm_dir, d, leaf)
        if os.path.exists(path):
            break
    else:
        _warning(vm_path, "Warning: Can't find %s." % leaf)
        return

    bc, start = _read_bc(path, "CONVLIBR")
    if start != 0:
        raise Exception("XXX")
    Bytecode.add_lib(vm, rffi.str2charp(bc))


def _make_mode(vm_path, path, bc, verbosity, mk_fresh):
    # Try to work out a plausible cached path name.
    dp = path.rfind(os.extsep)
    if dp >= 0 and os.sep not in path[dp:]:
        cp = path[:dp]
    else:
        cp = None
    
    if not cp or mk_fresh:
        return _do_make_mode(vm_path, path, None, verbosity, mk_fresh)
    else:
		# There is a cached path, so now we try and load it and see if it is upto date. If any part
		# of this fails, we simply go straight to full make mode.
        try:
            st = os.stat(cp)
        except OSError:
            return _do_make_mode(vm_path, path, cp, verbosity, mk_fresh)
        
        cbc, start = _read_bc(cp, "CONVEXEC")
        if start == -1:
            return _do_make_mode(vm_path, path, cp, verbosity, mk_fresh)
        
        assert start >= 0
        useful_bc = cbc[start:]
        if Bytecode.exec_upto_date(None, rffi.str2charp(useful_bc), st.st_mtime):
            return cbc, start, 0
        
        return _do_make_mode(vm_path, path, cp, verbosity, mk_fresh)


def _do_make_mode(vm_path, path, cp, verbosity, mk_fresh):
	# Fire up convergec -m on progpath. We do this by creating a pipe, forking, getting the child
    # to output to the pipe (although note that we leave stdin and stdout unmolested on the child
	# process, as user programs might want to print stuff to screen) and reading from that pipe
	# to get the necessary bytecode.

    convergecp = _find_con_exec(vm_path, "convergec")
    if convergecp is None:
        return None, 0, 1
    
    rfd, wfd = os.pipe()
    pid = os.fork()
    if pid == -1:
        raise Exception("XXX")
    elif pid == 0:
        # Child process.
        fdp = "/dev/fd/%d" % wfd
        
        args = [vm_path, convergecp, "-m", "-o", fdp]
        while verbosity > 0:
            args.append("-v")
            verbosity -= 1
        if mk_fresh:
            args.append("-f")
        
        args.append(path)
        os.execv(vm_path, args)
        _error(vm_path, "Couldn't execv convergec.")
        return None, -1, 1
    
    # Parent process
    
    os.close(wfd)
    
    # Read in the output from the child process.
    
    bc = ""
    while 1:
        try:
            r = os.read(rfd, BUFSIZ)
        except OSError:
            # Reading from a pipe seems to throw an exception when finished, which isn't the
            # documented behaviour...
            break
        if r == "":
            break
        bc += r

	# Now we've read all the data from the child convergec, we check its return status; if it
	# returned something other than 0 then we return that value and do not continue.

    _, status = os.waitpid(pid, 0)
    if os.WIFEXITED(status):
        rtn = os.WEXITSTATUS(status)
        if rtn != 0:
            return None, -1, rtn

    start = bc.find("CONVEXEC")
    if start == -1:
        _error(vm_path, "convergec failed to produce valid output.")
        return None, -1, 1

    if cp:
        # Try and write the file to its cached equivalent. Since this isn't strictly necessary, if
        # at any point anything fails, we simply give up without reporting an error.
        s = -1
        try:
            s = os.stat(cp).st_size
        except OSError:
            pass

        if s > 0:
            try:
                f = os.open(cp, os.O_RDONLY, 0777)
                d = os.read(f, 512)
                os.close(f)
            except OSError:
                return bc, start, 0

            if d.find("CONVEXEC") == -1:
                return bc, start, 0

        try:
            f = os.open(cp, os.O_WRONLY | os.O_CREAT, 0777)
            os.write(f, bc)
            os.close(f)
        except OSError:
            try:
                os.unlink(cp)
            except OSError:
                pass

    return bc, start, 0


def _find_con_exec(vm_path, leaf):
    cnds = [_dirname(vm_path), os.path.join(_dirname(_dirname(vm_path)), "compiler")]
    for cl in cnds:
        cp = os.path.join(cl, leaf)
        if os.path.exists(cp):
            return cp
    _error(vm_path, "Unable to locate %s." % leaf)
    return None


def _dirname(path): # An RPython compatible version since that in os.path currently isn't...
    i = path.rfind('/') + 1
    assert i > 0
    head = path[:i]
    if head and head != '/' * len(head):
        head = head.rstrip('/')
    return head


def _leafname(path):
    i = path.rfind('/') + 1
    assert i > 0
    return path[i:]


# Attempt to canonicalise path 'p'; at the very worst, 'p' is returned unchanged.

def _canon_path(path):
    with lltype.scoped_alloc(rffi.CCHARP.TO, PATH_MAX) as rp:
        r = realpath(path, rp)
        if not r:
            return path
        return rffi.charpsize2str(rp, rarithmetic.intmask(strlen(rp)))


def _error(vm_path, msg):
    print "%s: %s" % (_leafname(vm_path), msg)


def _warning(vm_path, msg):
    print "%s: %s" % (_leafname(vm_path), msg)


def _usage(vm_path):
    print "Usage: %s [-vf] [source file | executable file]" % _leafname(vm_path)


def target(driver, args):
    VM.global_vm.pypy_config = driver.config
    return entry_point, None


def jitpolicy(driver):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()

if __name__ == "__main__":
    entry_point(sys.argv)
########NEW FILE########
__FILENAME__ = Con_Array
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import sys
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform as platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from Builtins import *
from Core import *



DEFAULT_ENTRIES_ALLOC = 256


eci         = ExternalCompilationInfo(includes=["string.h"])
memmove     = rffi.llexternal("memmove", [rffi.CCHARP, rffi.CCHARP, rffi.SIZE_T], rffi.CCHARP, compilation_info=eci)
class CConfig:
    _compilation_info_ = eci
cconfig = platform.configure(CConfig)



def init(vm):
    return new_c_con_module(vm, "Array", "Array", __file__, import_, \
      ["Array_Exception", "Array"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")

    class_class = vm.get_builtin(BUILTIN_CLASS_CLASS)
    user_exception_class = vm.get_builtin(BUILTIN_EXCEPTIONS_MODULE). \
      get_defn(vm, "User_Exception")
    array_exception = vm.get_slot_apply(class_class, "new", \
      [Con_String(vm, "Array_Exception"), Con_List(vm, [user_exception_class]), mod])
    mod.set_defn(vm, "Array_Exception", array_exception)

    bootstrap_array_class(vm, mod)

    return vm.get_builtin(BUILTIN_NULL_OBJ)



################################################################################
# class Array
#

TYPE_I32 = 0
TYPE_I64 = 1
TYPE_F   = 2

class Array(Con_Boxed_Object):
    __slots__ = ("type_name", "type", "type_size", "big_endian", "data", "num_entries",
      "entries_alloc")
    _immutable_fields_ = ("type_name", "type", "big_endian")


    def __init__(self, vm, instance_of, type_name, data_o):
        Con_Boxed_Object.__init__(self, vm, instance_of)
        self.type_name = type_name
        if type_name == "i":
            if Target.INTSIZE == 4:
                self.type = TYPE_I32
                self.type_size = 4
            else:
                assert Target.INTSIZE == 8
                self.type = TYPE_I64
                self.type_size = 8
            self._auto_endian()
        elif type_name == "i32":
            self.type = TYPE_I32
            self.type_size = 4
            self._auto_endian()
        elif type_name == "i32be":
            self.type = TYPE_I32
            self.type_size = 4
            self.big_endian = True
        elif type_name == "i32le":
            self.type = TYPE_I32
            self.type_size = 4
            self.big_endian = False
        elif type_name == "i64":
            self.type = TYPE_I64
            self.type_size = 8
            self._auto_endian()
        elif type_name == "i64be":
            self.type = TYPE_I64
            self.type_size = 8
            self.big_endian = True
        elif type_name == "i64le":
            self.type = TYPE_I64
            self.type_size = 8
            self.big_endian = False
        elif type_name == "f":
            self.type = TYPE_F
            self.type_size = 8
            self.big_endian = False # irrelevant for floats
        else:
            mod = vm.get_funcs_mod()
            aex_class = mod.get_defn(vm, "Array_Exception")
            vm.raise_(vm.get_slot_apply(aex_class, "new", \
              [Con_String(vm, "Unknown array type '%s'." % type)]))

        if data_o is not None:
            if isinstance(data_o, Con_String):
                data = data_o.v
                i = len(data)
                self._alignment_check(vm, i)
                self.num_entries = self.entries_alloc = i // self.type_size
                self.data = lltype.malloc(rffi.CCHARP.TO, i, flavor="raw")
                i -= 1
                while i >= 0:
                    self.data[i] = data[i]
                    i -= 1
            else:
                self.num_entries = 0
                self.entries_alloc = type_check_int(vm, vm.get_slot_apply(data_o, "len")).v
                self.data = lltype.malloc(rffi.CCHARP.TO, self.entries_alloc * self.type_size, flavor="raw")
                vm.get_slot_apply(self, "extend", [data_o])
        else:
            self.num_entries = 0
            self.entries_alloc = DEFAULT_ENTRIES_ALLOC
            self.data = lltype.malloc(rffi.CCHARP.TO, self.entries_alloc * self.type_size, flavor="raw")


    def __del__(self):
        lltype.free(self.data, flavor="raw")


    def _auto_endian(self):
        if ENDIANNESS == "BIG_ENDIAN":
            self.big_endian = True
        else:
            assert ENDIANNESS == "LITTLE_ENDIAN"
            self.big_endian = False


    def _alignment_check(self, vm, i):
        if i % self.type_size == 0:
            return

        mod = vm.get_funcs_mod()
        aex_class = mod.get_defn(vm, "Array_Exception")
        vm.raise_(vm.get_slot_apply(aex_class, "new", \
          [Con_String(vm, "Data of len %d not aligned to a multiple of %d." % (i, self.type_size))]))


@con_object_proc
def _new_func_Array(vm):
    (class_, type_o, data_o),_ = vm.decode_args("CS", opt="O")
    assert isinstance(type_o, Con_String)

    a_o = Array(vm, class_, type_o.v, data_o)
    if data_o is None:
        data_o = vm.get_builtin(BUILTIN_NULL_OBJ)
    vm.get_slot_apply(a_o, "init", [type_o, data_o])

    return a_o


@con_object_proc
def Array_append(vm):
    (self, o_o),_ = vm.decode_args("!O", self_of=Array)
    assert isinstance(self, Array)

    _append(vm, self, o_o)
    objectmodel.keepalive_until_here(self)
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def Array_extend(vm):
    (self, o_o),_ = vm.decode_args("!O", self_of=Array)
    assert isinstance(self, Array)

    if isinstance(o_o, Array) and self.type_size == o_o.type_size:
        _check_room(vm, self, o_o.num_entries)
        memmove(rffi.ptradd(self.data, self.num_entries * self.type_size), \
          o_o.data, o_o.num_entries * o_o.type_size)
        self.num_entries += o_o.num_entries
    else:
        vm.pre_get_slot_apply_pump(o_o, "iter")
        while 1:
            e_o = vm.apply_pump()
            if not e_o:
                break
            _append(vm, self, e_o)
    objectmodel.keepalive_until_here(self)

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def Array_extend_from_string(vm):
    (self, s_o),_ = vm.decode_args("!S", self_of=Array)
    assert isinstance(self, Array)
    assert isinstance(s_o, Con_String)

    s = s_o.v
    i = len(s)
    self._alignment_check(vm, i)
    _check_room(vm, self, i // self.type_size)
    i -= 1
    p = self.num_entries * self.type_size
    while i >= 0:
        self.data[p + i] = s[i]
        i -= 1
    self.num_entries += len(s) // self.type_size
    objectmodel.keepalive_until_here(self)

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def Array_get(vm):
    (self, i_o),_ = vm.decode_args("!I", self_of=Array)
    assert isinstance(self, Array)
    assert isinstance(i_o, Con_Int)

    i = translate_idx(vm, i_o.v, self.num_entries)
    o = _get_obj(vm, self, i)
    objectmodel.keepalive_until_here(self)
    return o


@con_object_proc
def Array_get_slice(vm):
    mod = vm.get_funcs_mod()
    (self, i_o, j_o),_ = vm.decode_args("!", opt="ii", self_of=Array)
    assert isinstance(self, Array)

    i, j = translate_slice_idx_objs(vm, i_o, j_o, self.num_entries)
    # This does a double allocation, so isn't very efficient. It is pleasingly simple though.
    data = rffi.charpsize2str(rffi.ptradd(self.data, i * self.type_size), int((j - i) * self.type_size))
    objectmodel.keepalive_until_here(self)
    return Array(vm, mod.get_defn(vm, "Array"), self.type_name, Con_String(vm, data))


@con_object_gen
def Array_iter(vm):
    (self, i_o, j_o),_ = vm.decode_args("!", opt="ii", self_of=Array)
    assert isinstance(self, Array)

    i, j = translate_slice_idx_objs(vm, i_o, j_o, self.num_entries)
    for k in range(i, j):
        yield _get_obj(vm, self, k)
    objectmodel.keepalive_until_here(self)


@con_object_proc
def Array_len(vm):
    (self,),_ = vm.decode_args("!", self_of=Array)
    assert isinstance(self, Array)

    return Con_Int(vm, self.num_entries)


@con_object_proc
def Array_len_bytes(vm):
    (self,),_ = vm.decode_args("!", self_of=Array)
    assert isinstance(self, Array)

    return Con_Int(vm, self.num_entries * self.type_size)


@con_object_proc
def Array_serialize(vm):
    (self,),_ = vm.decode_args("!", self_of=Array)
    assert isinstance(self, Array)

    data = rffi.charpsize2str(self.data, self.num_entries * self.type_size)
    objectmodel.keepalive_until_here(self) # XXX I don't really understand why this is needed
    return Con_String(vm, data)


@con_object_proc
def Array_set(vm):
    (self, i_o, o_o),_ = vm.decode_args("!IO", self_of=Array)
    assert isinstance(self, Array)
    assert isinstance(i_o, Con_Int)

    i = translate_idx(vm, i_o.v, self.num_entries)
    _set_obj(vm, self, i, o_o)
    objectmodel.keepalive_until_here(self)
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def Array_to_str(vm):
    (self,),_ = vm.decode_args("!", self_of=Array)
    assert isinstance(self, Array)

    data = rffi.charpsize2str(self.data, self.num_entries * self.type_size)
    objectmodel.keepalive_until_here(self)
    return Con_String(vm, data)


def _append(vm, self, o):
    _check_room(vm, self, 1)
    _set_obj(vm, self, self.num_entries, o)
    self.num_entries += 1


def _check_room(vm, self, i):
    if self.num_entries + i < self.entries_alloc:
        return
    o_data = self.data
    self.entries_alloc = int((self.entries_alloc + i + 1) * 1.25)
    assert self.entries_alloc > self.num_entries + i
    self.data = lltype.malloc(rffi.CCHARP.TO, self.entries_alloc * self.type_size, flavor="raw")
    memmove(self.data, o_data, self.num_entries * self.type_size)
    lltype.free(o_data, flavor="raw")


def _get_obj(vm, self, i):
    if self.type == TYPE_I64:
        return Con_Int(vm, rffi.cast(rffi.LONGP, self.data)[i])
    elif self.type == TYPE_I32:
        return Con_Int(vm, rffi.cast(rffi.LONG, rffi.cast(rffi.INTP, self.data)[i]))
    elif self.type == TYPE_F:
        return Con_Float(vm, rffi.cast(rffi.DOUBLE, rffi.cast(rffi.DOUBLEP, self.data)[i]))
    else:
        raise Exception("XXX")


def _set_obj(vm, self, i, o):
    if self.type == TYPE_I64:
        rffi.cast(rffi.LONGP, self.data)[i] = rffi.cast(rffi.LONG, type_check_number(vm, o).as_int())
    elif self.type == TYPE_I32:
        rffi.cast(rffi.INTP, self.data)[i] = rffi.cast(rffi.INT, type_check_number(vm, o).as_int())
    elif self.type == TYPE_F:
        rffi.cast(rffi.DOUBLEP, self.data)[i] = rffi.cast(rffi.DOUBLE, type_check_number(vm, o).as_float())
    else:
        raise Exception("XXX")


def bootstrap_array_class(vm, mod):
    array_class = Con_Class(vm, Con_String(vm, "Array"), [vm.get_builtin(BUILTIN_OBJECT_CLASS)], mod)
    mod.set_defn(vm, "Array", array_class)
    array_class.new_func = new_c_con_func(vm, Con_String(vm, "new_Array"), False, _new_func_Array, mod)

    new_c_con_func_for_class(vm, "append", Array_append, array_class)
    new_c_con_func_for_class(vm, "extend", Array_extend, array_class)
    new_c_con_func_for_class(vm, "extend_from_string", Array_extend_from_string, array_class)
    new_c_con_func_for_class(vm, "get", Array_get, array_class)
    new_c_con_func_for_class(vm, "get_slice", Array_get_slice, array_class)
    new_c_con_func_for_class(vm, "iter", Array_iter, array_class)
    new_c_con_func_for_class(vm, "len", Array_len, array_class)
    new_c_con_func_for_class(vm, "len_bytes", Array_len_bytes, array_class)
    new_c_con_func_for_class(vm, "serialize", Array_serialize, array_class)
    new_c_con_func_for_class(vm, "set", Array_set, array_class)
    new_c_con_func_for_class(vm, "to_str", Array_to_str, array_class)
########NEW FILE########
__FILENAME__ = Con_Curses
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import sys
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform as platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from Builtins import *



eci             = ExternalCompilationInfo(includes=["curses.h", "term.h", "unistd.h"], \
                    libraries=["curses"])


if platform.has("setupterm", "#include <curses.h>\n#include <term.h>"):
    HAVE_CURSES = True
    setupterm   = rffi.llexternal("setupterm", [rffi.CCHARP, rffi.INT, rffi.INTP], rffi.INT, \
                    compilation_info=eci)
    tigetstr    = rffi.llexternal("tigetstr", [rffi.CCHARP], rffi.CCHARP, compilation_info=eci)
else:
    HAVE_CURSES = False

class CConfig:
    _compilation_info_ = eci
    OK                 = platform.DefinedConstantInteger("OK")
    STDOUT_FILENO      = platform.DefinedConstantInteger("STDOUT_FILENO")

cconfig = platform.configure(CConfig)

OK                     = cconfig["OK"]
STDOUT_FILENO          = cconfig["STDOUT_FILENO"]



def init(vm):
    return new_c_con_module(vm, "Curses", "Curses", __file__, import_, \
      ["Curses_Exception", "setupterm", "tigetstr"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")
    
    class_class = vm.get_builtin(BUILTIN_CLASS_CLASS)
    user_exception_class = vm.get_builtin(BUILTIN_EXCEPTIONS_MODULE). \
      get_defn(vm, "User_Exception")
    curses_exception = vm.get_slot_apply(class_class, "new", \
      [Con_String(vm, "Curses_Exception"), Con_List(vm, [user_exception_class]), mod])
    mod.set_defn(vm, "Curses_Exception", curses_exception)
    new_c_con_func_for_mod(vm, "setupterm", setupterm_func, mod)
    new_c_con_func_for_mod(vm, "tigetstr", tigetstr_func, mod)

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def setupterm_func(vm):
    mod = vm.get_funcs_mod()
    (term_o, file_o), _ = vm.decode_args(opt="sO")
    
    if HAVE_CURSES:
        if term_o:
            assert isinstance(term_o, Con_String)
            raise Exception("XXX")
        else:
            term = None

        if file_o:
            fd = type_check_int(vm, vm.get_slot_apply(file_o, "fileno")).v
        else:
            fd = STDOUT_FILENO

        with lltype.scoped_alloc(rffi.INTP.TO, 1) as erret:
            if setupterm(term, fd, erret) != OK:
                ec = int(erret[0])
                if ec == -1:
                    msg = "Can't find terminfo database."
                elif ec == 0:
                    msg = "Terminal not found or not enough information known about it."
                elif ec == 1:
                    msg = "Terminal is hardcopy."
                else:
                    raise Exception("XXX")

                cex_class = mod.get_defn(vm, "Curses_Exception")
                vm.raise_(vm.get_slot_apply(cex_class, "new", [Con_String(vm, msg)]))
    else:
        raise Exception("XXX")
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def tigetstr_func(vm):
    mod = vm.get_funcs_mod()
    (capname_o,), _ = vm.decode_args("S")
    assert isinstance(capname_o, Con_String)

    if HAVE_CURSES:
        r = tigetstr(capname_o.v)
        if rffi.cast(rffi.LONG, r) == -1 or rffi.cast(rffi.LONG, r) == -1:
            msg = "'%s' not found or absent." % capname_o.v
            cex_class = mod.get_defn(vm, "Curses_Exception")
            vm.raise_(vm.get_slot_apply(cex_class, "new", [Con_String(vm, msg)]))
        return Con_String(vm, rffi.charp2str(r))
    else:
        raise Exception("XXX")

########NEW FILE########
__FILENAME__ = Con_C_Earley_Parser
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import Stdlib_Modules, Target
from Builtins import *




def init(vm):
    return new_c_con_module(vm, "C_Earley_Parser", "C_Earley_Parser", __file__, import_, \
      ["Parser"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")

    bootstrap_parser_class(vm, mod)

    return vm.get_builtin(BUILTIN_NULL_OBJ)


################################################################################
# class Parser
#

_COMPILED_OFFSET_TO_PRODUCTIONS = 0
_COMPILED_OFFSET_TO_ALTERNATIVES_MAP = 1
_COMPILED_OFFSET_TO_RECOGNISER_BRACKETS_MAPS = 2
_COMPILED_OFFSET_TO_PARSER_BRACKETS_MAPS = 3

_COMPILED_PRODUCTIONS_NUM = 0
_COMPILED_PRODUCTIONS_OFFSETS = 1

_COMPILED_PRODUCTION_PRECEDENCE = 0
_COMPILED_PRODUCTION_PARENT_RULE = 1
_COMPILED_PRODUCTION_NUM_SYMBOLS = 2
_COMPILED_PRODUCTION_SYMBOLS = 3

_SYMBOL_RULE_REF = 0
_SYMBOL_TOKEN = 1
_SYMBOL_OPEN_KLEENE_STAR_GROUP = 2
_SYMBOL_CLOSE_KLEENE_STAR_GROUP = 3
_SYMBOL_OPEN_OPTIONAL_GROUP = 4
_SYMBOL_CLOSE_OPTIONAL_GROUP = 5

_COMPILED_ALTERNATIVES_MAP_NUM = 0
_COMPILED_ALTERNATIVES_MAP_OFFSETS = 1

_ALTERNATIVE_MAP_IS_NULLABLE = 0
_ALTERNATIVE_MAP_NUM_ENTRIES = 1
_ALTERNATIVE_MAP_ENTRIES = 2

_COMPILED_BRACKETS_MAPS_NUM_ENTRIES = 0
_COMPILED_BRACKETS_MAPS_ENTRIES = 1

_BRACKET_MAP_NUM_ENTRIES = 0
_BRACKET_MAP_ENTRIES = 1


class Parser:
    __slots__ = ("grm", "toks", "items")
    _immutable_fields_ = ("grm", "toks", "items")

    def __init__(self, grm, toks):
        self.grm = grm
        self.toks = toks
        self.items = []


class Alt:
    __slots__ = ("parent_rule", "precedence", "syms")
    _immutable_fields_ = ("parent_rule", "precedence", "syms")
    
    def __init__(self, parent_rule, precedence, syms):
        self.parent_rule = parent_rule
        self.precedence = precedence
        self.syms = syms


class Item:
    __slots__ = ("s", "d", "j", "w")
    # s is the rule number
    # d is the position of the Earley "dot" within the rule we've currently reached
    # j is the position in the token input we've currently reached
    # w is the SPPF tree being built
    _immutable_fields_ = ("s", "d", "j", "w")
    
    def __init__(self, s, d, j, w):
        self.s = s
        self.d = d
        self.j = j
        self.w = w

    def __eq__(self, o):
        if o.s == self.s and o.d == self.d and o.j == self.j and o.w == self.w:
            return 0
        else:
            return -1

    def __repr__(self):
        return "Item(%s, %s, %s, %s)" % (self.s, self.d, self.j, self.w)



class Tree:
    __slots__ = ()


class Tree_Non_Term(Tree):
    __slots__ = ("s", "complete", "j", "i", "precedences", "families", "flattened")
    _immutable_fields_ = ("t", "complete", "j", "i")

    def __init__(self, s, complete, j, i):
        self.s = s
        self.complete = complete
        self.j = j
        self.i = i
        self.precedences = None
        self.families = None
        self.flattened = None


    def __eq__(self, o):
        raise Exception("XXX")


    def pp(self, indent=0, names=None, alts=None):
        out = ["%sNT: %s%s %d %d\n" % (" " * indent, names[alts[self.s].parent_rule], self.s, self.j, self.i)]

        for k in self.flattened:
            out.append(k.pp(indent + 1, names, alts))

        return "".join(out)


    def _seen(self, seen, n):
        for cnd in seen:
            if cnd is n:
                return True
        return False


class Tree_Term(Tree):
    __slots__ = ("t", "j", "i")
    _immutable_fields_ = ("t", "j", "i")

    def __init__(self, t, j, i):
        self.t = t
        self.j = j
        self.i = i


    def pp(self, indent=0, names=None, alts=None):
        return "%sT: %d %d %d\n" % (" " * indent, self.t, self.j, self.i)


@con_object_proc
def Parser_parse(vm):
    (self, grm_o, rns_o, toksmap_o, toks_o),_ = vm.decode_args("OSOOO")
    assert isinstance(grm_o, Con_String)
    
    toks = [-1] # Tokens: list(int)
    tok_os = [None]
    vm.pre_get_slot_apply_pump(toks_o, "iter")
    while 1:
        e_o = vm.apply_pump()
        if not e_o:
            break
        tok_o = vm.get_slot_apply(toksmap_o, "get", [e_o.get_slot(vm, "type")])
        tok_os.append(e_o)
        toks.append(type_check_int(vm, tok_o).v)

    rn_os = [] # Rule names: list(Con_String)
    vm.pre_get_slot_apply_pump(rns_o, "iter")
    while 1:
        e_o = vm.apply_pump()
        if not e_o:
            break
        rn_os.append(e_o)

    grm = []
    grm_s = grm_o.v
    if len(grm_s) % Target.INTSIZE != 0:
        raise Exception("XXX")
    for i in range(0, len(grm_s), Target.INTSIZE):
        if Target.INTSIZE == 8:
            w = ord(grm_s[i]) + (ord(grm_s[i + 1]) << 8) + (ord(grm_s[i + 2]) << 16) \
                  + (ord(grm_s[i + 3]) << 24) + (ord(grm_s[i + 4]) << 32) + \
                  + (ord(grm_s[i + 5]) << 40) + (ord(grm_s[i + 6]) << 48) + \
                  (ord(grm_s[i + 7]) << 56)
        else:
            w = ord(grm_s[i]) + (ord(grm_s[i + 1]) << 8) + (ord(grm_s[i + 2]) << 16) \
                  + (ord(grm_s[i + 3]) << 24)
        grm.append(w)

    alts_off = grm[_COMPILED_OFFSET_TO_PRODUCTIONS]
    num_alts = grm[alts_off + _COMPILED_PRODUCTIONS_NUM] - 1
    alts = [None] * num_alts
    for i in range(num_alts):
        alt_off = grm[alts_off + _COMPILED_PRODUCTIONS_OFFSETS + i]
        assert alt_off >= 0
        alt_num_syms = grm[alt_off + _COMPILED_PRODUCTION_NUM_SYMBOLS]
        assert alt_num_syms >= 0
        syms = grm[alt_off + _COMPILED_PRODUCTION_SYMBOLS : \
          alt_off + _COMPILED_PRODUCTION_SYMBOLS + alt_num_syms]
        alt = Alt(grm[alt_off + _COMPILED_PRODUCTION_PARENT_RULE], \
          grm[alt_off + _COMPILED_PRODUCTION_PRECEDENCE], syms)
        alts[i] = alt

    b_maps_off = grm[_COMPILED_OFFSET_TO_RECOGNISER_BRACKETS_MAPS]
    num_b_maps = grm[b_maps_off + _COMPILED_BRACKETS_MAPS_NUM_ENTRIES]
    b_maps = [None] * num_b_maps
    for i in range(num_b_maps):
        b_map_off = grm[b_maps_off + _COMPILED_BRACKETS_MAPS_ENTRIES + i]
        assert b_map_off >= 0
        b_map_len = grm[b_map_off + _BRACKET_MAP_NUM_ENTRIES]
        assert b_map_len >= 0
        b_map = grm[b_map_off + _BRACKET_MAP_ENTRIES : b_map_off + _BRACKET_MAP_ENTRIES + b_map_len]
        b_maps[i] = b_map
    
    E = _parse(vm, self, toks, alts, b_maps)

    for k, v in E[len(toks) - 1].items():
        for T in v:
            T_alt = alts[T.s]
            if T.s == 0 and T.d == len(T_alt.syms) and T.j == 0:
                c = T.w
                assert isinstance(c, Tree_Non_Term)
                _resolve_ambiguities(vm, alts, tok_os, rn_os, c)
                int_tree = c.families[0][0]
                src_infos = tok_os[1].get_slot(vm, "src_infos")
                first_src_info = vm.get_slot_apply(src_infos, "get", [Con_Int(vm, 0)])
                src_file = vm.get_slot_apply(first_src_info, "get", [Con_Int(vm, 0)])
                src_off = type_check_int(vm, vm.get_slot_apply(first_src_info, "get", [Con_Int(vm, 1)])).v
                #rn_ss = [type_check_string(vm, x).v for x in rn_os]
                #print int_tree.pp(0, names=rn_ss, alts=alts)
                n, _, _ = _int_tree_to_ptree(vm, alts, tok_os, rn_os, int_tree, src_file, src_off)
                return n

    for i in range(len(tok_os) - 1, -1, -1):
        if len(E[i]) > 0:
            vm.get_slot_apply(self, "error", [tok_os[i]])


#
# This is an extension of the Earley parsing algorithm described in:
#   Recognition is not parsing - SPPF-style parsing from cubic recognisers
#   Elizabeth Scott, Adrian Johnstone
#   Science of Computer Programming 75 (2010) 55-70
# In particular we extend this with the Kleene star ()* and optional ()? operators.
#
# "line X" is a reference to the line numbered X (starting from 1) in the Scott / Johnstone
# algorithm.
#

def _parse(vm, self, toks, alts, b_maps):
    E = [{} for x in range(len(toks))]
    _add_to_e_set(E[0], Item(0, 0, 0, None))
    Qd = {}
    V = {}
    for i in range(0, len(toks)):
        H = {}
        R = _clone_e_set(E[i])
        Q = Qd
        Qd = {}
        while len(R) > 0:
            Lam = _pop_e_set(R)
            B_alt = alts[Lam.s]
            if Lam.d < len(B_alt.syms) and B_alt.syms[Lam.d] == _SYMBOL_RULE_REF: # line 9
                C = B_alt.syms[Lam.d + 1]
                for C_cnd in range(len(alts)): # line 10
                    C_cnd_alt = alts[C_cnd]
                    if C_cnd_alt.parent_rule != C: # line 10
                        continue
                    for p in _get_all_pos(alts, b_maps, C_cnd, 0):
                        e = Item(C_cnd, p, i, None)
                        if _sigma_d_at(alts, toks, C_cnd, p):
                            # line 11
                            if not _is_in_e_set(E[i], e):
                                _add_to_e_set(E[i], e)
                                _add_to_e_set(R, e)
                        elif _tok_match(alts, toks, C_cnd, p, i + 1):
                            _add_to_e_set(Q, Item(C_cnd, p, i, None))
                if C in H:
                    for p in _get_all_pos(alts, b_maps, Lam.s, Lam.d + 2):
                        y = _make_node(alts, toks, b_maps, Lam.s, p, Lam.j, i, Lam.w, H[C], V) # line 15
                        e = Item(Lam.s, p, Lam.j, y)
                        if _sigma_d_at(alts, toks, Lam.s, p):
                            # line 16
                            if not _is_in_e_set(E[i], e):
                                _add_to_e_set(E[i], e)
                                _add_to_e_set(R, e)
                        elif _tok_match(alts, toks, Lam.s, p, i + 1):
                            _add_to_e_set(Q, e)
            elif Lam.d == len(B_alt.syms): # line 19
                w = Lam.w
                if w is None: # line 20
                    D = (B_alt.parent_rule, -1, i, i)
                    w = V.get(D, None)
                    if w is None:
                        # line 21
                        w = Tree_Non_Term(Lam.s, True, i, i)
                        V[D] = w
                if Lam.j == i: # line 24
                    H[Lam.s] = w
                for es in E[Lam.j].values(): # line 25
                    for A in es:
                        A_alt = alts[A.s]
                        if A.d == len(A_alt.syms) or A_alt.syms[A.d] != _SYMBOL_RULE_REF \
                          or A_alt.syms[A.d + 1] != B_alt.parent_rule:
                            continue
                        for p in _get_all_pos(alts, b_maps, A.s, A.d + 2):
                            y = _make_node(alts, toks, b_maps, A.s, p, A.j, i, A.w, w, V) # line 26
                            # line 27
                            if _sigma_d_at(alts, toks, A.s, p):
                                e = Item(A.s, p, A.j, y)
                                if not _is_in_e_set(E[i], e):
                                    _add_to_e_set(E[i], e)
                                    _add_to_e_set(R, e)
                            elif _tok_match(alts, toks, A.s, p, i + 1): # line 29
                                _add_to_e_set(Q, Item(A.s, p, A.j, y))

        V = {}
        if i < len(toks) - 1:
            v = Tree_Term(toks[i + 1], i, i + 1)
            while len(Q) > 0:
                Lam = _pop_e_set(Q)
                B_alt = alts[Lam.s]
                assert Lam.d < len(B_alt.syms) and B_alt.syms[Lam.d] == _SYMBOL_TOKEN \
                  and B_alt.syms[Lam.d + 1] == toks[i + 1]
                for p in _get_all_pos(alts, b_maps, Lam.s, Lam.d + 2):
                    y = _make_node(alts, toks, b_maps, Lam.s, p, Lam.j, i + 1, Lam.w, v, V)
                    e = Item(Lam.s, p, Lam.j, y)
                    if _sigma_d_at(alts, toks, Lam.s, p):
                        # line 36
                        _add_to_e_set(E[i + 1], e)
                    elif _tok_match(alts, toks, Lam.s, p, i + 2):
                        # line 37
                        _add_to_e_set(Qd, e)

    return E


def _sigma_d_at(alts, toks, s, d):
    alt = alts[s]
    if d == len(alt.syms) or alt.syms[d] == _SYMBOL_RULE_REF:
        return True
    return False


def _tok_match(alts, toks, s, d, tok_i):
    alt = alts[s]
    if tok_i < len(toks) and d < len(alt.syms) and alt.syms[d] == _SYMBOL_TOKEN \
      and alt.syms[d + 1] == toks[tok_i]:
        return True
    return False


def _get_all_pos(alts, b_maps, s, d):
    alt = alts[s]
    if d < len(alt.syms) and alt.syms[d] in \
      (_SYMBOL_OPEN_KLEENE_STAR_GROUP, _SYMBOL_CLOSE_KLEENE_STAR_GROUP, \
      _SYMBOL_OPEN_OPTIONAL_GROUP, _SYMBOL_CLOSE_OPTIONAL_GROUP):
        return b_maps[alt.syms[d + 1]]
    else:
        return [d]


def _is_in_e_set(s, e):
    cnds = s.get((e.s, e.d, e.j), None)
    if cnds is None:
        return False
    for cnd_e in cnds:
        if e.w is cnd_e.w:
            return True
    return False


def _add_to_e_set(s, e):
    lab = (e.s, e.d, e.j)
    cnds = s.get(lab, None)
    if cnds is None:
        s[lab] = [e]
    else:
        for cnd_e in cnds:
            if e.w is cnd_e.w:
                return
        else:
            cnds.append(e)


def _clone_e_set(s):
    n = {}
    for k, v in s.items():
        n[k] = v[:]
    return n


def _pop_e_set(s):
    assert len(s) > 0
    for k, v in s.items():
        e = v.pop()
        if len(v) == 0:
            del s[k]
        return e
    raise Exception("Shouldn't get here")


def _make_node(alts, toks, b_maps, B, d, j, i, w, v, V):
    B_alt = alts[B]
    if d == len(B_alt.syms):
        lab = (B_alt.parent_rule, -1, j, i)
    else:
        lab = (B, d, j, i)

    # The Kleene star and optional brackets complicate the case presented in line 46
    # since we have no obvious \alpha to compare to the empty string. What we note is that if
    # this label has not previously been seen, we can search leftwards in the alternative to
    # see if a rule / token must have been found (in other words, we skip over brackets, which
    # we can't be sure of either way); if it has, we know \alpha \neq \epsilon, and can move
    # on accordingly.
    y = V.get(lab, None)
    if y is None:
        if d < len(B_alt.syms):
            p = d
            found = False
            while p >= 0:
                if B_alt.syms[p] in (_SYMBOL_RULE_REF, _SYMBOL_TOKEN):
                    found = True
                elif B_alt.syms[p] in (_SYMBOL_CLOSE_KLEENE_STAR_GROUP, _SYMBOL_CLOSE_OPTIONAL_GROUP):
                    p -= 2
                    while B_alt.syms[p] not in (_SYMBOL_OPEN_KLEENE_STAR_GROUP, _SYMBOL_CLOSE_KLEENE_STAR_GROUP):
                        p -= 2
                p -= 2
            if not found:
                return v
        if lab[1] == -1:
            y = Tree_Non_Term(B, True, j, i)
        else:
            y = Tree_Non_Term(B, False, j, i)
        V[lab] = y

    if w is None:
        kids = [v]
    else:
        kids = [w, v]

    if y.families is None:
        y.families = [kids]
        y.precedences = [B_alt.precedence]
    else:
        for cnd_kids in y.families:
            if len(kids) != len(cnd_kids) or kids[0] is not cnd_kids[0]:
                continue
            if len(kids) == 2 and kids[1] is not cnd_kids[1]:
                continue
            break
        else:
            y.families.append(kids)
            y.precedences.append(B_alt.precedence)

    return y


def _resolve_ambiguities(vm, alts, tok_os, rn_os, n):
    # This is a fairly lazy ambiguity resolution scheme - it only looks 2 levels deep. That's enough
    # for current purposes.
    if isinstance(n, Tree_Term):
        return
    assert isinstance(n, Tree_Non_Term)
    if n.families is not None:
        # The basic approach is to resolve all ambiguities in children first, before trying to
        # resolve ambiguity in 'n' itself.
        
        for kids in n.families:
            for c in kids:
                _resolve_ambiguities(vm, alts, tok_os, rn_os, c)

        if len(n.families) == 1:
            n.flattened = _flatten_kids(n.families[0])
            return
        
        if 0 not in n.precedences:
            lp = hp = n.precedences[0]
            for p in n.precedences:
                lp = min(lp, p)
                hp = max(hp, p)
            if lp != hp:
                j = 0
                while j < len(n.families):
                    if n.precedences[j] != lp:
                        del n.precedences[j]
                        del n.families[j]
                    else:
                        j += 1
                if len(n.families) == 1:
                    n.flattened = _flatten_kids(n.families[0])
                    return

        ffamilies = [_flatten_kids(k) for k in n.families]
        for fkids in ffamilies:
            if len(fkids) != len(ffamilies[0]):
                break
        
        if len(ffamilies) > 1:
            # We still have ambiguities left, so, as a sensible default, we prefer
            # left-associative parses.
            i = 0
            while i < len(ffamilies) - 1:
                len1 = len(ffamilies[i])
                len2 = len(ffamilies[i + 1])
                if len1 < len2:
                    del ffamilies[i]
                elif len2 < len1:
                    del ffamilies[i + 1]
                else:
                    i += 1
            if len(ffamilies) > 1:
                for i in range(len(ffamilies[0])):
                    j = 0
                    while j < len(ffamilies) - 1:
                        len1 = _max_depth(ffamilies[j][i])
                        len2 = _max_depth(ffamilies[j + 1][i])
                        if len1 < len2:
                            del ffamilies[j]
                        elif len2 < len1:
                            del ffamilies[j + 1]
                        else:
                            i += 1
                    if len(ffamilies) == 1:
                        break
                
        n.flattened = ffamilies[0]
    else:
        n.flattened = []


def _int_tree_to_ptree(vm, alts, tok_os, rn_os, n, src_file, src_off):
    if isinstance(n, Tree_Non_Term):
        tree_mod = vm.import_stdlib_mod(Stdlib_Modules.STDLIB_CPK_TREE)
        non_term_class = tree_mod.get_defn(vm, "Non_Term")

        name = rn_os[alts[n.s].parent_rule]
        kids, new_src_off, new_src_len = _int_tree_to_ptree_kids(vm, alts, tok_os, rn_os, n, src_file, src_off)
        
        src_infos = Con_List(vm, [Con_List(vm, [src_file, Con_Int(vm, new_src_off), Con_Int(vm, new_src_len)])])
        rn = vm.get_slot_apply(non_term_class, "new", [name, Con_List(vm, kids), src_infos])
    else:
        assert isinstance(n, Tree_Term)
        rn = tok_os[n.j + 1]
        new_src_off, new_src_len = _term_off_len(vm, rn)

    return rn, new_src_off, new_src_len


def _int_tree_to_ptree_kids(vm, alts, tok_os, rn_os, n, src_file, src_off):
    kids = []
    new_src_off = cur_src_off = src_off
    new_src_len = 0
    i = 0
    for c in n.flattened:
        if isinstance(c, Tree_Non_Term):
            c, newer_src_off, newer_src_len = \
              _int_tree_to_ptree(vm, alts, tok_os, rn_os, c, src_file, cur_src_off)
            kids.append(c)
        else:
            assert isinstance(c, Tree_Term)
            tok_o = tok_os[c.j + 1]
            newer_src_off, newer_src_len = _term_off_len(vm, tok_o)
            src_end = new_src_off + new_src_len
            kids.append(tok_o)

        if i == 0:
            new_src_off = newer_src_off
        i += 1
        cur_src_off = newer_src_off + newer_src_len
        new_src_len = (newer_src_off - new_src_off) + newer_src_len

    return kids, new_src_off, new_src_len


def _term_off_len(vm, n):
    src_infos = n.get_slot(vm, "src_infos")
    first_src_info = vm.get_slot_apply(src_infos, "get", [Con_Int(vm, 0)])
    src_off = type_check_int(vm, vm.get_slot_apply(first_src_info, "get", [Con_Int(vm, 1)])).v
    src_len = type_check_int(vm, vm.get_slot_apply(first_src_info, "get", [Con_Int(vm, 2)])).v
    return src_off, src_len


def _max_depth(n):
    if isinstance(n, Tree_Term):
        return 0
    assert isinstance(n, Tree_Non_Term)
    md = 0
    for c in n.flattened:
        md = max(md, 1 + _max_depth(c))
    return md


def _flatten_kids(kids):
    fkids = []
    for c in kids:
        if isinstance(c, Tree_Non_Term):
            _flatten_non_term(c)
            if c.complete:
                fkids.append(c)
            elif len(c.flattened) > 0:
                fkids.extend(c.flattened)
        else:
            assert isinstance(c, Tree_Term)
            fkids.append(c)
    return fkids


def _flatten_non_term(n):
    if n.flattened is not None:
        return
    if n.families is None:
        n.flattened = []
        return
    fkids = []
    for c in n.families[0]:
        if isinstance(c, Tree_Non_Term):
            _flatten_non_term(c)
            if c.complete:
                fkids.append(c)
            elif len(c.flattened) > 0:
                fkids.extend(c.flattened)
        else:
            assert isinstance(c, Tree_Term)
            fkids.append(c)
    n.flattened = fkids


def bootstrap_parser_class(vm, mod):
    parser_class = Con_Class(vm, Con_String(vm, "Parser"), \
      [vm.get_builtin(BUILTIN_OBJECT_CLASS)], mod)
    mod.set_defn(vm, "Parser", parser_class)

    new_c_con_func_for_class(vm, "parse", Parser_parse, parser_class)

########NEW FILE########
__FILENAME__ = Con_C_Platform_Env
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


from Builtins import *




def init(vm):
    return new_c_con_module(vm, "C_Platform_Env", "C_Platform_Env", __file__, import_, \
      ["find_var", "get_var", "set_var"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)

########NEW FILE########
__FILENAME__ = Con_C_Platform_Exec
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rlib import rarithmetic, rposix
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from Builtins import *



eci    = ExternalCompilationInfo(includes=["stdlib.h"])

system = rffi.llexternal("system", [rffi.CCHARP], rffi.INT, compilation_info=eci)

class CConfig:
    _compilation_info_ = eci

cconfig = platform.configure(CConfig)



def init(vm):
    return new_c_con_module(vm, "C_Platform_Exec", "C_Platform_Exec", __file__, import_, \
      ["sh_cmd"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")
    
    new_c_con_func_for_mod(vm, "sh_cmd", sh_cmd, mod)
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def sh_cmd(vm):
    (cmd_o,),_ = vm.decode_args("S")
    assert isinstance(cmd_o, Con_String)

    r = system(cmd_o.v)
    if r == -1:
        vm.raise_helper("Exception", [Con_String(vm, os.strerror(rposix.get_errno()))])

    return Con_Int(vm, os.WEXITSTATUS(r))

########NEW FILE########
__FILENAME__ = Con_C_Platform_Host
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


from rpython.rlib import rsocket
from Builtins import *




def init(vm):
    return new_c_con_module(vm, "C_Platform_Host", "C_Platform_Host", __file__, import_, \
      ["get_hostname"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")
    
    new_c_con_func_for_mod(vm, "get_hostname", get_hostname, mod)
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def get_hostname(vm):
    _,_ = vm.decode_args()

    return Con_String(vm, rsocket.gethostname())

########NEW FILE########
__FILENAME__ = Con_C_Platform_Properties
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import os, sys
import Config
from Builtins import *
from Core import *





def init(vm):
    return new_c_con_module(vm, "C_Platform_Properties", "C_Platform_Properties", __file__, \
      import_, \
      ["word_bits", "LITTLE_ENDIAN", "BIG_ENDIAN", "endianness", "osname", \
        "case_sensitive_filenames"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")

    mod.set_defn(vm, "word_bits", Con_Int(vm, Target.INTSIZE * 8))
    mod.set_defn(vm, "LITTLE_ENDIAN", Con_String(vm, "LITTLE_ENDIAN"))
    mod.set_defn(vm, "BIG_ENDIAN", Con_String(vm, "BIG_ENDIAN"))
    mod.set_defn(vm, "endianness", Con_String(vm, ENDIANNESS))
    mod.set_defn(vm, "osname", Con_String(vm, Config.PLATFORM))
    mod.set_defn(vm, "case_sensitive_filenames", Con_Int(vm, CASE_SENSITIVE_FILENAMES))
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)

########NEW FILE########
__FILENAME__ = Con_C_Strings
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


from Builtins import *




def init(vm):
    return new_c_con_module(vm, "C_Strings", "C_Strings", __file__, import_, \
      ["join"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")
    
    new_c_con_func_for_mod(vm, "join", join, mod)
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def join(vm):
    (list_o, sep_o),_ = vm.decode_args("OS")
    assert isinstance(sep_o, Con_String)
    
    out = []
    vm.pre_get_slot_apply_pump(list_o, "iter")
    while 1:
        e_o = vm.apply_pump()
        if not e_o:
            break
        out.append(type_check_string(vm, e_o).v)

    return Con_String(vm, sep_o.v.join(out))

########NEW FILE########
__FILENAME__ = Con_C_Time
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


from rpython.rlib import rarithmetic
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform as platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from Builtins import *



eci             = ExternalCompilationInfo(includes=["time.h", "sys/time.h"])

class CConfig:
    _compilation_info_ = eci
    TIMEVAL            = platform.Struct("struct timeval", [("tv_sec", rffi.LONG), ("tv_usec", rffi.LONG)])
    TIMEZONE           = platform.Struct("struct timezone", [])
    TIMESPEC           = platform.Struct("struct timespec", [("tv_sec", rffi.TIME_T), ("tv_nsec", rffi.LONG)])
    CLOCK_MONOTONIC    = platform.DefinedConstantInteger("CLOCK_MONOTONIC")

cconfig         = platform.configure(CConfig)

TIMEVAL         = cconfig["TIMEVAL"]
TIMEVALP        = lltype.Ptr(TIMEVAL)
TIMEZONE        = cconfig["TIMEZONE"]
TIMEZONEP       = lltype.Ptr(TIMEZONE)
TIMESPEC        = cconfig["TIMESPEC"]
TIMESPECP       = lltype.Ptr(TIMESPEC)
CLOCK_MONOTONIC = cconfig["CLOCK_MONOTONIC"]

gettimeofday    = rffi.llexternal('gettimeofday', [TIMEVALP, TIMEZONEP], rffi.INT, compilation_info=eci)
if platform.has("clock_gettime", "#include <sys/time.h>"):
    HAS_CLOCK_GETTIME = True
    clock_gettime   = rffi.llexternal('clock_gettime', [rffi.INT, TIMESPECP], rffi.INT, compilation_info=eci)
else:
    HAS_CLOCK_GETTIME = False


def init(vm):
    return new_c_con_module(vm, "C_Time", "C_Time", __file__, import_, \
      ["current", "current_mono"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")
    
    new_c_con_func_for_mod(vm, "current", current, mod)
    if HAS_CLOCK_GETTIME:
        new_c_con_func_for_mod(vm, "current_mono", current_mono, mod)
    else:
        # OS X, and maybe other OSs, doesn't have clock_gettime, so we fall back on a less accurate
        # timing method as being better than nothing.
        new_c_con_func_for_mod(vm, "current_mono", current, mod)

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def current(vm):
    _,_ = vm.decode_args()

    with lltype.scoped_alloc(TIMEVAL) as tp:
        if gettimeofday(tp, lltype.nullptr(TIMEZONEP.TO)) != 0:
            raise Exception("XXX")
        sec = rarithmetic.r_int(tp.c_tv_sec)
        usec = rarithmetic.r_int(tp.c_tv_usec)

    return Con_List(vm, [Con_Int(vm, sec), Con_Int(vm, usec * 1000)])


@con_object_proc
def current_mono(vm):
    _,_ = vm.decode_args()

    with lltype.scoped_alloc(TIMESPEC) as ts:
        if clock_gettime(CLOCK_MONOTONIC, ts) != 0:
            raise Exception("XXX")
        sec = rarithmetic.r_int(ts.c_tv_sec)
        nsec = rarithmetic.r_int(ts.c_tv_nsec)

    return Con_List(vm, [Con_Int(vm, sec), Con_Int(vm, nsec)])

########NEW FILE########
__FILENAME__ = Con_Exceptions
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import sys
from Builtins import *




def init(vm):
    mod = new_c_con_module(vm, "Exceptions", "Exceptions", __file__, import_, \
      ["Exception",
       "Internal_Exception",
         "VM_Exception", "System_Exit_Exception",
       "User_Exception",
         "Apply_Exception", "Assert_Exception", "Bounds_Exception", "Field_Exception",
         "Import_Exception", "Indices_Exception", "Key_Exception", "Mod_Defn_Exception",
         "NDIf_Exception", "Number_Exception", "Parameters_Exception", "Slot_Exception",
         "Type_Exception", "Unassigned_Var_Exception", "Unpack_Exception",
       "IO_Exception",
         "File_Exception"])
    vm.set_builtin(BUILTIN_EXCEPTIONS_MODULE, mod)
    
    return mod


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")

    mod.set_defn(vm, "Exception", vm.get_builtin(BUILTIN_EXCEPTION_CLASS))

    internal_exception = _mk_simple_exception(vm, mod, "Internal_Exception", \
      superclass=vm.get_builtin(BUILTIN_EXCEPTION_CLASS))
    _mk_simple_exception(vm, mod, "System_Exit_Exception", \
      init_func=_System_Exit_Exception_init_func, superclass=internal_exception)
    _mk_simple_exception(vm, mod, "VM_Exception", superclass=internal_exception)

    _mk_simple_exception(vm, mod, "User_Exception", superclass=vm.get_builtin(BUILTIN_EXCEPTION_CLASS))
    _mk_simple_exception(vm, mod, "Apply_Exception", init_func=_Apply_Exception_init_func)
    _mk_simple_exception(vm, mod, "Assert_Exception")
    _mk_simple_exception(vm, mod, "Bounds_Exception", init_func=_Bounds_Exception_init_func)
    _mk_simple_exception(vm, mod, "Field_Exception", init_func=_Field_Exception_init_func)
    _mk_simple_exception(vm, mod, "Import_Exception", init_func=_Import_Exception_init_func)
    _mk_simple_exception(vm, mod, "Indices_Exception", init_func=_Indices_Exception_init_func)
    _mk_simple_exception(vm, mod, "Key_Exception", init_func=_Key_Exception_init_func)
    _mk_simple_exception(vm, mod, "Mod_Defn_Exception")
    _mk_simple_exception(vm, mod, "NDIf_Exception")
    _mk_simple_exception(vm, mod, "Number_Exception", init_func=_Number_Exception_init_func)
    _mk_simple_exception(vm, mod, "Parameters_Exception")
    _mk_simple_exception(vm, mod, "Slot_Exception", init_func=_Slot_Exception_init_func)
    _mk_simple_exception(vm, mod, "Type_Exception", init_func=_Type_Exception_init_func)
    _mk_simple_exception(vm, mod, "Unassigned_Var_Exception")
    _mk_simple_exception(vm, mod, "Unpack_Exception", init_func=_Unpack_Exception_init_func)

    io_exception = _mk_simple_exception(vm, mod, "IO_Exception")
    _mk_simple_exception(vm, mod, "File_Exception", superclass=io_exception)

    return vm.get_builtin(BUILTIN_NULL_OBJ)


def _mk_simple_exception(vm, mod, n, init_func=None, superclass=None):
    class_class = vm.get_builtin(BUILTIN_CLASS_CLASS)

    if superclass is None:
        superclass = mod.get_defn(vm, "Internal_Exception")
    assert isinstance(superclass, Con_Class)
    ex = vm.get_slot_apply(class_class, "new", [Con_String(vm, n), Con_List(vm, [superclass]), mod])
    if init_func is not None:
        ex.set_field(vm, "init", new_c_con_func(vm, Con_String(vm, "init"), True, init_func, ex))
    mod.set_defn(vm, n, ex)
    return ex


@con_object_proc
def _Apply_Exception_init_func(vm):
    (self, o_o),_ = vm.decode_args("OO")
    p = type_check_string(vm, vm.get_slot_apply(o_o.get_slot(vm, "instance_of"), "path")).v
    self.set_slot(vm, "msg", Con_String(vm, "Do not know how to apply instance of '%s'." % p))
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Bounds_Exception_init_func(vm):
    (self, idx_o, upper_o),_ = vm.decode_args("OII")
    assert isinstance(idx_o, Con_Int)
    assert isinstance(upper_o, Con_Int)
    if idx_o.v < 0:
        msg = "%d below lower bound 0." % idx_o.v
    else:
        msg = "%d exceeds upper bound %d." % (idx_o.v, upper_o.v)
    self.set_slot(vm, "msg", Con_String(vm, msg))
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Field_Exception_init_func(vm):
    (self, n_o, class_o),_ = vm.decode_args("OSO")
    assert isinstance(n_o, Con_String)
    classp = type_check_string(vm, vm.get_slot_apply(class_o, "path")).v
    msg = "No such field '%s' in class '%s'." % (n_o.v, classp)
    self.set_slot(vm, "msg", Con_String(vm, msg))
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Import_Exception_init_func(vm):
    (self, mod_id),_ = vm.decode_args("OS")
    assert isinstance(mod_id, Con_String)
    self.set_slot(vm, "msg", Con_String(vm, "Unable to import '%s'." % mod_id.v))
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Indices_Exception_init_func(vm):
    (self, lower_o, upper_o),_ = vm.decode_args("OII")
    assert isinstance(lower_o, Con_Int)
    assert isinstance(upper_o, Con_Int)
    msg = "Lower bound %d exceeds upper bound %d" % (lower_o.v, upper_o.v)
    self.set_slot(vm, "msg", Con_String(vm, msg))
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Key_Exception_init_func(vm):
    (self, k),_ = vm.decode_args("OO")
    k_s = type_check_string(vm, vm.get_slot_apply(k, "to_str"))
    self.set_slot(vm, "msg", Con_String(vm, "Key '%s' not found." % k_s.v))
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Number_Exception_init_func(vm):
    (self, o),_ = vm.decode_args("OO")
    o_s = type_check_string(vm, vm.get_slot_apply(o, "to_str"))
    self.set_slot(vm, "msg", Con_String(vm, "Number '%s' not valid." % o_s.v))
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Slot_Exception_init_func(vm):
    (self, n, o),_ = vm.decode_args("OSO")
    assert isinstance(n, Con_String)
    name = type_check_string(vm, o.get_slot(vm, "instance_of").get_slot(vm, "name"))
    msg = "No such slot '%s' in instance of '%s'." % (n.v, name.v)
    self.set_slot(vm, "msg", Con_String(vm, msg))
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _System_Exit_Exception_init_func(vm):
    (self, code),_ = vm.decode_args("OO")
    self.set_slot(vm, "code", code)
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def _Type_Exception_init_func(vm):
    (self, should_be, o, extra),_ = vm.decode_args(mand="OSO", opt="O")
    assert isinstance(should_be, Con_String)
    if extra is not None:
        msg = "Expected '%s' to be conformant to " % \
          type_check_string(vm, extra).v
    else:
        msg = "Expected to be conformant to "
    msg += should_be.v
    o_path = type_check_string(vm, vm.get_slot_apply(o.get_slot(vm, "instance_of"), "path"))
    msg += ", but got instance of %s." % o_path.v
    self.set_slot(vm, "msg", Con_String(vm, msg))
    return vm.get_builtin(BUILTIN_NULL_OBJ)

@con_object_proc
def _Unpack_Exception_init_func(vm):
    (self, expected_o, got_o),_ = vm.decode_args("OII")
    assert isinstance(expected_o, Con_Int)
    assert isinstance(got_o, Con_Int)
    msg = "Unpack of %d elements failed, as %d elements present" % (expected_o.v, got_o.v)
    self.set_slot(vm, "msg", Con_String(vm, msg))
    return vm.get_builtin(BUILTIN_NULL_OBJ)

########NEW FILE########
__FILENAME__ = Con_PCRE
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rlib.rsre import rsre_re
from rpython.translator.tool.cbuild import ExternalCompilationInfo
import Config
from Builtins import *
from Core import *


eci                        = ExternalCompilationInfo(includes=["pcre.h"], \
                               include_dirs=Config.LIBPCRE_INCLUDE_DIRS, \
                               library_dirs=Config.LIBPCRE_LIBRARY_DIRS, \
                               libraries=Config.LIBPCRE_LIBRARIES, \
                               link_extra=Config.LIBPCRE_LINK_FLAGS, \
                               link_files=[Config.LIBPCRE_A])

class CConfig:
    _compilation_info_     = eci
    PCRE_DOTALL            = platform.DefinedConstantInteger("PCRE_DOTALL")
    PCRE_MULTILINE         = platform.DefinedConstantInteger("PCRE_MULTILINE")
    PCRE_INFO_CAPTURECOUNT = platform.DefinedConstantInteger("PCRE_INFO_CAPTURECOUNT")
    PCRE_ANCHORED          = platform.DefinedConstantInteger("PCRE_ANCHORED")
    PCRE_ERROR_NOMATCH     = platform.DefinedConstantInteger("PCRE_ERROR_NOMATCH")

cconfig = platform.configure(CConfig)

PCREP                  = rffi.COpaquePtr("pcre")
PCRE_DOTALL            = cconfig["PCRE_DOTALL"]
PCRE_MULTILINE         = cconfig["PCRE_MULTILINE"]
PCRE_INFO_CAPTURECOUNT = cconfig["PCRE_INFO_CAPTURECOUNT"]
PCRE_ANCHORED          = cconfig["PCRE_ANCHORED"]
PCRE_ERROR_NOMATCH     = cconfig["PCRE_ERROR_NOMATCH"]

pcre_compile = rffi.llexternal("pcre_compile", \
  [rffi.CCHARP, rffi.INT, rffi.CCHARPP, rffi.INTP, rffi.VOIDP], PCREP, compilation_info=eci)
pcre_fullinfo = rffi.llexternal("pcre_fullinfo", \
  [PCREP, rffi.VOIDP, rffi.INT, rffi.INTP], rffi.INT, compilation_info=eci)
pcre_exec = rffi.llexternal("pcre_exec", \
  [PCREP, rffi.VOIDP, rffi.CCHARP, rffi.INT, rffi.INT, rffi.INT, rffi.INTP, rffi.INT], \
  rffi.INT, compilation_info=eci)



def init(vm):
    return new_c_con_module(vm, "PCRE", "PCRE", __file__, import_, \
      ["PCRE_Exception", "Pattern", "Match", "compile"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")

    bootstrap_pattern_class(vm, mod)
    bootstrap_match_class(vm, mod)
    new_c_con_func_for_mod(vm, "compile", compile, mod)
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)



################################################################################
# class PCRE
#

class Pattern(Con_Boxed_Object):
    __slots__ = ("cp", "num_caps")
    _immutable_fields_ = ("cp", "num_caps")


    def __init__(self, vm, instance_of, cp, num_caps):
        Con_Boxed_Object.__init__(self, vm, instance_of)
        self.cp = cp
        self.num_caps = num_caps


@con_object_proc
def Pattern_match(vm):
    return _Pattern_match_search(vm, True)


@con_object_proc
def Pattern_search(vm):
    return _Pattern_match_search(vm, False)


def _Pattern_match_search(vm, anchored):
    mod = vm.get_funcs_mod()
    (self, s_o, sp_o),_ = vm.decode_args(mand="!S", opt="I", self_of=Pattern)
    assert isinstance(self, Pattern)
    assert isinstance(s_o, Con_String)
    
    ovect_size = (1 + self.num_caps) * 3
    ovect = lltype.malloc(rffi.INTP.TO, ovect_size, flavor="raw")
    if anchored:
        flags = PCRE_ANCHORED
    else:
        flags = 0
    sp = translate_idx_obj(vm, sp_o, len(s_o.v))
    rs = rffi.get_nonmovingbuffer(s_o.v)
    r = int(pcre_exec(self.cp, None, rs, len(s_o.v), sp, flags, ovect, ovect_size))
    rffi.free_nonmovingbuffer(s_o.v, rs)
    if r < 0:
        if r == PCRE_ERROR_NOMATCH:
            lltype.free(ovect, flavor="raw")
            return vm.get_builtin(BUILTIN_FAIL_OBJ)
        else:
            raise Exception("XXX")
            
    return Match(vm, mod.get_defn(vm, "Match"), ovect, self.num_caps, s_o)


def bootstrap_pattern_class(vm, mod):
    pattern_class = Con_Class(vm, Con_String(vm, "Pattern"), [vm.get_builtin(BUILTIN_OBJECT_CLASS)], mod)
    mod.set_defn(vm, "Pattern", pattern_class)

    new_c_con_func_for_class(vm, "match", Pattern_match, pattern_class)
    new_c_con_func_for_class(vm, "search", Pattern_search, pattern_class)



#
# func compile(s)
#
# This is defined here because it's tightly coupled to the Pattern class.
#

@con_object_proc
def compile(vm):
    mod = vm.get_funcs_mod()
    (pat,),_ = vm.decode_args("S")
    assert isinstance(pat, Con_String)
    
    errptr = lltype.malloc(rffi.CCHARPP.TO, 1, flavor="raw")
    erroff = lltype.malloc(rffi.INTP.TO, 1, flavor="raw")
    try:
        cp = pcre_compile(pat.v, PCRE_DOTALL | PCRE_MULTILINE, errptr, erroff, None)
        if cp is None:
            raise Exception("XXX")
    finally:
        lltype.free(errptr, flavor="raw")
        lltype.free(erroff, flavor="raw")

    with lltype.scoped_alloc(rffi.INTP.TO, 1) as num_capsp:
        r = int(pcre_fullinfo(cp, None, PCRE_INFO_CAPTURECOUNT, num_capsp))
        if r != 0:
            raise Exception("XXX")
        num_caps = int(num_capsp[0])

    return Pattern(vm, mod.get_defn(vm, "Pattern"), cp, num_caps)



################################################################################
# class Match
#

class Match(Con_Boxed_Object):
    __slots__ = ("ovect", "num_caps", "s")
    _immutable_fields_ = ("ovect", "num_caps", "s")


    def __init__(self, vm, instance_of, ovect, num_caps, s):
        Con_Boxed_Object.__init__(self, vm, instance_of)
        self.ovect = ovect
        self.num_caps = num_caps
        self.s = s


    def __del__(self):
        lltype.free(self.ovect, flavor="raw")


@con_object_proc
def Match_get(vm):
    (self, i_o),_ = vm.decode_args(mand="!I", self_of=Match)
    assert isinstance(self, Match)
    assert isinstance(i_o, Con_Int)
    
    # Group 0 in the match is the entire match, so when translating indices, we need to add 1 onto
	# num_captures.
    i = translate_idx(vm, i_o.v, 1 + self.num_caps)
    
    o = self.s.get_slice(vm, int(self.ovect[i * 2]), int(self.ovect[i * 2 + 1]))
    objectmodel.keepalive_until_here(self)
    return o


@con_object_proc
def Match_get_indexes(vm):
    (self, i_o),_ = vm.decode_args(mand="!I", self_of=Match)
    assert isinstance(self, Match)
    assert isinstance(i_o, Con_Int)
    
    i = translate_idx(vm, i_o.v, 1 + self.num_caps)
    
    o = Con_List(vm, [Con_Int(vm, int(self.ovect[i * 2])), Con_Int(vm, int(self.ovect[i * 2 + 1]))])
    objectmodel.keepalive_until_here(self)
    return o


def bootstrap_match_class(vm, mod):
    match_class = Con_Class(vm, Con_String(vm, "Match"), [vm.get_builtin(BUILTIN_OBJECT_CLASS)], mod)
    mod.set_defn(vm, "Match", match_class)

    new_c_con_func_for_class(vm, "get", Match_get, match_class)
    new_c_con_func_for_class(vm, "get_indexes", Match_get_indexes, match_class)

########NEW FILE########
__FILENAME__ = Con_POSIX_File
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rlib import rarithmetic, rposix
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from Builtins import *
import Stdlib_Modules



if not platform.has("fgetln", "#include <stdio.h>"):
    # This should use separate_module_files, but that appears to be broken, hence
    # this horrible hack.
    f = open(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../platform/fgetln.c"))
    d = f.read()
    separate_module_sources = [d]
    extra_includes = [os.path.join(os.path.split(os.path.abspath(__file__))[0], "../platform/fgetln.h")]
else:
    separate_module_sources = []
    extra_includes = []

eci         = ExternalCompilationInfo(includes=["limits.h", "stdio.h", "stdlib.h", "string.h",
                "unistd.h"] + extra_includes, separate_module_sources=separate_module_sources)

FILEP       = rffi.COpaquePtr("FILE")
fclose      = rffi.llexternal("fclose", [FILEP], rffi.INT, compilation_info=eci)
fdopen      = rffi.llexternal("fdopen", [rffi.INT, rffi.CCHARP], FILEP, compilation_info=eci)
feof        = rffi.llexternal("feof", [FILEP], rffi.INT, compilation_info=eci)
ferror      = rffi.llexternal("ferror", [FILEP], rffi.INT, compilation_info=eci)
fflush      = rffi.llexternal("fflush", [FILEP], rffi.INT, compilation_info=eci)
fgetln      = rffi.llexternal("fgetln", [FILEP, rffi.SIZE_TP], rffi.CCHARP, compilation_info=eci)
fileno      = rffi.llexternal("fileno", [FILEP], rffi.INT, compilation_info=eci)
flockfile   = rffi.llexternal("flockfile", [FILEP], lltype.Void, compilation_info=eci)
fopen       = rffi.llexternal("fopen", [rffi.CCHARP, rffi.CCHARP], FILEP, compilation_info=eci)
fread       = rffi.llexternal("fread", [rffi.CCHARP, rffi.SIZE_T, rffi.SIZE_T, FILEP], rffi.SIZE_T, \
                compilation_info=eci)
fseek       = rffi.llexternal("fseek", [FILEP, rffi.INT, rffi.INT], rffi.INT, compilation_info=eci)
funlockfile = rffi.llexternal("funlockfile", [FILEP], lltype.Void, compilation_info=eci)
fwrite      = rffi.llexternal("fwrite", [rffi.CCHARP, rffi.SIZE_T, rffi.SIZE_T, FILEP], rffi.SIZE_T, \
                compilation_info=eci)

if platform.has("mkstemp", "#include <stdlib.h>"):
    HAS_MKSTEMP = True
    mkstemp = rffi.llexternal("mkstemp", [rffi.CCHARP], rffi.INT, compilation_info=eci)
else:
    HAS_MKSTEMP = False
    tmpnam  = rffi.llexternal("tmpnam", [rffi.CCHARP], rffi.CCHARP, compilation_info=eci)
realpath    = rffi.llexternal("realpath", \
                [rffi.CCHARP, rffi.CCHARP], rffi.CCHARP, compilation_info=eci)

strlen      = rffi.llexternal("strlen", [rffi.CCHARP], rffi.SIZE_T, compilation_info=eci)

class CConfig:
    _compilation_info_ = eci
    PATH_MAX           = platform.DefinedConstantInteger("PATH_MAX")
    SEEK_SET           = platform.DefinedConstantInteger("SEEK_SET")

cconfig = platform.configure(CConfig)

PATH_MAX = cconfig["PATH_MAX"]
SEEK_SET = cconfig["SEEK_SET"]



def init(vm):
    return new_c_con_module(vm, "POSIX_File", "POSIX_File", __file__, import_, \
      ["DIR_SEP", "EXT_SEP", "NULL_DEV", "File_Atom_Def", "File", "canon_path", "exists", "is_dir",
       "is_file", "chmod", "iter_dir_entries", "mtime", "rm", "temp_file"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")

    mod.set_defn(vm, "DIR_SEP", Con_String(vm, os.sep))
    mod.set_defn(vm, "EXT_SEP", Con_String(vm, os.extsep))
    mod.set_defn(vm, "NULL_DEV", Con_String(vm, "/dev/null"))

    bootstrap_file_class(vm, mod)

    new_c_con_func_for_mod(vm, "canon_path", canon_path, mod)
    new_c_con_func_for_mod(vm, "chmod", chmod, mod)
    new_c_con_func_for_mod(vm, "exists", exists, mod)
    new_c_con_func_for_mod(vm, "is_dir", is_dir, mod)
    new_c_con_func_for_mod(vm, "is_file", is_file, mod)
    new_c_con_func_for_mod(vm, "iter_dir_entries", iter_dir_entries, mod)
    new_c_con_func_for_mod(vm, "mtime", mtime, mod)
    new_c_con_func_for_mod(vm, "rm", rm, mod)
    new_c_con_func_for_mod(vm, "temp_file", temp_file, mod)
    
    vm.set_builtin(BUILTIN_C_FILE_MODULE, mod)
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)


def _errno_raise(vm, path):
    if isinstance(path, Con_String):
        msg = "File '%s': %s." % (path.v, os.strerror(rposix.get_errno()))
    else:
        msg = os.strerror(rposix.get_errno())
    vm.raise_helper("File_Exception", [Con_String(vm, msg)])


################################################################################
# class File
#

class File(Con_Boxed_Object):
    __slots__ = ("filep", "closed")
    _immutable_fields_ = ("file")


    def __init__(self, vm, instance_of, path, filep):
        Con_Boxed_Object.__init__(self, vm, instance_of)
        self.filep = filep
        self.closed = False
        
        self.set_slot(vm, "path", path)


    def __del__(self):
        if not self.closed:
		    # If the file is still open, we now close it to prevent a memory leak, as well as return
            # resources to the OS. Errors from fclose are ignored as there's nothing sensible we can
            # do with them at this point.
            fclose(self.filep)


@con_object_proc
def _new_func_File(vm):
    (class_, path_o, mode_o), vargs = vm.decode_args("COS")
    assert isinstance(mode_o, Con_String)

    f = path_s = None
    if isinstance(path_o, Con_String):
        path_s = path_o.v
        f = fopen(path_s, mode_o.v)
    elif isinstance(path_o, Con_Int):
        path_s = None
        f = fdopen(path_o.v, mode_o.v)
    else:
        vm.raise_helper("Type_Exception", [Con_String(vm, "[String, Int]"), path_o])

    if not f:
        _errno_raise(vm, path_o)

    f_o = File(vm, class_, path_o, f)
    vm.get_slot_apply(f_o, "init", [path_o, mode_o])

    return f_o


@con_object_proc
def File_close(vm):
    (self,),_ = vm.decode_args("!", self_of=File)
    assert isinstance(self, File)
    _check_open(vm, self)

    if fclose(self.filep) != 0:
        _errno_raise(vm, self.get_slot(vm, "path"))
    self.closed = True

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def File_fileno(vm):
    (self,),_ = vm.decode_args("!", self_of=File)
    assert isinstance(self, File)
    _check_open(vm, self)

    return Con_Int(vm, int(fileno(self.filep)))


@con_object_proc
def File_flush(vm):
    (self,),_ = vm.decode_args("!", self_of=File)
    assert isinstance(self, File)
    _check_open(vm, self)
    
    if fflush(self.filep) != 0:
        _errno_raise(vm, self.get_slot(vm, "path"))

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def File_read(vm):
    (self, rsize_o),_ = vm.decode_args(mand="!", opt="I", self_of=File)
    assert isinstance(self, File)
    _check_open(vm, self)
    
    flockfile(self.filep)
    fsize = os.fstat(fileno(self.filep)).st_size
    if rsize_o is None:
        rsize = fsize
    else:
        assert isinstance(rsize_o, Con_Int)
        rsize = rsize_o.v
        if rsize < 0:
            vm.raise_helper("File_Exception", \
              [Con_String(vm, "Can not read less than 0 bytes from file.")])
        elif rsize > fsize:
            rsize = fsize

    if objectmodel.we_are_translated():
        with lltype.scoped_alloc(rffi.CCHARP.TO, rsize) as buf:
            r = fread(buf, 1, rsize, self.filep)
            if r < rffi.r_size_t(rsize) and ferror(self.filep) != 0:
                vm.raise_helper("File_Exception", [Con_String(vm, "Read error.")])
            s = rffi.charpsize2str(buf, rarithmetic.intmask(r))
    else:
        # rffi.charpsize2str is so slow (taking minutes for big strings) that it's worth bypassing
        # it when things are run untranslated.
        s = os.read(fileno(self.filep), rsize)
    funlockfile(self.filep)

    return Con_String(vm, s)


@con_object_gen
def File_readln(vm):
    (self,),_ = vm.decode_args(mand="!", self_of=File)
    assert isinstance(self, File)
    _check_open(vm, self)
    
    while 1:
        with lltype.scoped_alloc(rffi.SIZE_TP.TO, 1) as lenp:
            l = fgetln(self.filep, lenp)
            if not l:
                if feof(self.filep) != 0:
                    break
                _errno_raise(vm, self.get_slot(vm, "path"))
            l_o = Con_String(vm, rffi.charpsize2str(l, rarithmetic.intmask(lenp[0])))
            yield l_o


@con_object_proc
def File_seek(vm):
    (self, off_o),_ = vm.decode_args(mand="!I", self_of=File)
    assert isinstance(self, File)
    assert isinstance(off_o, Con_Int)
    _check_open(vm, self)

    if fseek(self.filep, off_o.v, SEEK_SET) != 0:
        _errno_raise(vm, self.get_slot(vm, "path"))

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def File_write(vm):
    (self, s_o),_ = vm.decode_args(mand="!S", self_of=File)
    assert isinstance(self, File)
    assert isinstance(s_o, Con_String)
    _check_open(vm, self)
    
    s = s_o.v
    if len(s) > 0 and fwrite(s, len(s), 1, self.filep) < 1:
        vm.raise_helper("File_Exception", [Con_String(vm, "Write error.")])

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def File_writeln(vm):
    (self, s_o),_ = vm.decode_args(mand="!S", self_of=File)
    assert isinstance(self, File)
    assert isinstance(s_o, Con_String)
    _check_open(vm, self)
    
    s = s_o.v + "\n"
    if fwrite(s, len(s), 1, self.filep) < 1:
        vm.raise_helper("File_Exception", [Con_String(vm, "Write error.")])

    return vm.get_builtin(BUILTIN_NULL_OBJ)


def _check_open(vm, file):
    if file.closed:
        vm.raise_helper("File_Exception", [Con_String(vm, "File previously closed.")])


def bootstrap_file_class(vm, mod):
    file_class = Con_Class(vm, Con_String(vm, "File"), [vm.get_builtin(BUILTIN_OBJECT_CLASS)], mod)
    mod.set_defn(vm, "File", file_class)
    file_class.new_func = new_c_con_func(vm, Con_String(vm, "new_File"), False, _new_func_File, mod)

    new_c_con_func_for_class(vm, "close", File_close, file_class)
    new_c_con_func_for_class(vm, "fileno", File_fileno, file_class)
    new_c_con_func_for_class(vm, "flush", File_flush, file_class)
    new_c_con_func_for_class(vm, "read", File_read, file_class)
    new_c_con_func_for_class(vm, "readln", File_readln, file_class)
    new_c_con_func_for_class(vm, "seek", File_seek, file_class)
    new_c_con_func_for_class(vm, "write", File_write, file_class)
    new_c_con_func_for_class(vm, "writeln", File_writeln, file_class)



################################################################################
# Other module-level functions
#

@con_object_proc
def canon_path(vm):
    (p_o,),_ = vm.decode_args("S")
    assert isinstance(p_o, Con_String)

    with lltype.scoped_alloc(rffi.CCHARP.TO, PATH_MAX) as resolved:
        r = realpath(p_o.v, resolved)
        if not r:
            _errno_raise(vm, p_o)
        rp = rffi.charpsize2str(resolved, rarithmetic.intmask(strlen(resolved)))

    return Con_String(vm, rp)


@con_object_proc
def chmod(vm):
    (p_o, mode_o),_ = vm.decode_args("SI")
    assert isinstance(p_o, Con_String)
    assert isinstance(mode_o, Con_Int)
    
    try:
        os.chmod(p_o.v, int(mode_o.v))
    except OSError, e:
        _errno_raise(vm, p_o)

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def exists(vm):
    (p_o,),_ = vm.decode_args("S")
    assert isinstance(p_o, Con_String)
    
    try:
        if os.path.exists(p_o.v):
            return vm.get_builtin(BUILTIN_NULL_OBJ)
        else:
            return vm.get_builtin(BUILTIN_FAIL_OBJ)
    except OSError, e:
        _errno_raise(vm, p_o)


@con_object_proc
def is_dir(vm):
    (p_o,),_ = vm.decode_args("S")
    assert isinstance(p_o, Con_String)
    
    try:
        if os.path.isdir(p_o.v):
            return vm.get_builtin(BUILTIN_NULL_OBJ)
        else:
            return vm.get_builtin(BUILTIN_FAIL_OBJ)
    except OSError, e:
        _errno_raise(vm, p_o)


@con_object_proc
def is_file(vm):
    (p_o,),_ = vm.decode_args("S")
    assert isinstance(p_o, Con_String)
    
    try:
        if os.path.isfile(p_o.v):
            return vm.get_builtin(BUILTIN_NULL_OBJ)
        else:
            return vm.get_builtin(BUILTIN_FAIL_OBJ)
    except OSError, e:
        _errno_raise(vm, p_o)


@con_object_gen
def iter_dir_entries(vm):
    (dp_o,),_ = vm.decode_args("S")
    assert isinstance(dp_o, Con_String)
    
    try:
        for p in os.listdir(dp_o.v):
            yield Con_String(vm, p)
    except OSError, e:
        _errno_raise(vm, dp_o)


@con_object_proc
def mtime(vm):
    (p_o,),_ = vm.decode_args("S")
    assert isinstance(p_o, Con_String)
    
    time_mod = vm.import_stdlib_mod(Stdlib_Modules.STDLIB_TIME)
    mk_timespec = time_mod.get_defn(vm, "mk_timespec")

    # XXX Ideally we'd use our own stat implementation here, but it's a cross-platform nightmare, so
    # this is a reasonable substitute. We might lose a bit of accuracy because floating point
    # numbers won't be a totally accurate representation of nanoseconds, but the difference
    # probably isn't enough to worry about.

    mtime = 0
    try:
        mtime = os.stat(p_o.v).st_mtime
    except OSError, e:
        _errno_raise(vm, p_o)
    
    sec = int(mtime)
    nsec = int((mtime - int(mtime)) * 1E9)
    
    return vm.apply(mk_timespec, [Con_Int(vm, sec), Con_Int(vm, nsec)])


@con_object_proc
def rm(vm):
    (p_o,),_ = vm.decode_args("S")
    assert isinstance(p_o, Con_String)
    
    st = [p_o.v]
    i = 0
    while len(st) > 0:
        p = st[i]
        try:
            if os.path.isdir(p):
                leafs = os.listdir(p)
                if len(leafs) == 0:
                    os.rmdir(p)
                    del st[i]
                else:
                    i += 1
                    st.extend([os.path.join(p, l) for l in leafs])
            else:
                os.unlink(p)
                del st[i]
        except OSError, e:
            _errno_raise(vm, Con_String(vm, p))

        if i == len(st):
            i -= 1

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def temp_file(vm):
    mod = vm.get_funcs_mod()
    file_class = type_check_class(vm, mod.get_defn(vm, "File"))
    vm.decode_args()
    
    if HAS_MKSTEMP:
        #tmpdir = None
        #if os.environ.has_key("TMPDIR"):
        #    tmpdir = os.environ["TMPDIR"]
        #if tmpdir is None:
        #    tmpdir = "/tmp"
        tmpp = "/tmp/tmp.XXXXXXXXXX"
        with rffi.scoped_str2charp(tmpp) as buf:
            fd = mkstemp(buf)
            tmpp = rffi.charp2str(buf)
           
        if fd == -1:
            _errno_raise(vm, Con_String(vm, tmpp))
        
        f = fdopen(fd, "w+")
        if not f:
            _errno_raise(vm, Con_String(vm, tmpp))
        
        return File(vm, file_class, Con_String(vm, tmpp), f)
    else:
        raise Exception("XXX")

########NEW FILE########
__FILENAME__ = Con_Random
# Copyright (c) 2012 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import sys
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform as platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo
import Config
from Builtins import *



eci            = ExternalCompilationInfo(includes=["stdlib.h", "time.h", "sys/time.h"])

class CConfig:
    _compilation_info_ = eci
    TIMEVAL            = platform.Struct("struct timeval", [("tv_sec", rffi.LONG), ("tv_usec", rffi.LONG)])
    TIMEZONE           = platform.Struct("struct timezone", [])

cconfig        = platform.configure(CConfig)

TIMEVAL        = cconfig["TIMEVAL"]
TIMEVALP       = lltype.Ptr(TIMEVAL)
TIMEZONE       = cconfig["TIMEZONE"]
TIMEZONEP      = lltype.Ptr(TIMEZONE)

gettimeofday   = rffi.llexternal('gettimeofday', [TIMEVALP, TIMEZONEP], rffi.INT, compilation_info=eci)
if platform.has("random", "#include <stdlib.h>"):
    HAS_RANDOM = True
    random     = rffi.llexternal("random", [], rffi.LONG, compilation_info=eci)
    srandom    = rffi.llexternal("srandom", [rffi.INT], lltype.Void, compilation_info=eci)
else:
    HAS_RANDOM = False
    rand       = rffi.llexternal("rand", [], rffi.LONG, compilation_info=eci)
    srand      = rffi.llexternal("srand", [rffi.INT], lltype.Void, compilation_info=eci)

if platform.has("srandomdev", "#include <stdlib.h>"):
    HAS_SRANDOMDEV = True
    srandomdev = rffi.llexternal("srandomdev", [], lltype.Void, compilation_info=eci)
else:
    HAS_SRANDOMDEV = False



def init(vm):
    mod = new_c_con_module(vm, "Random", "Random", __file__, import_, \
      ["pluck", "random", "shuffle"])
    vm.set_builtin(BUILTIN_SYS_MODULE, mod)
        
    return mod


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")

    if HAS_SRANDOMDEV and HAS_RANDOM:
        srandomdev()
    else:
        with lltype.scoped_alloc(TIMEVAL) as tp:
            if gettimeofday(tp, lltype.nullptr(TIMEZONEP.TO)) != 0:
                raise Exception("XXX")
            seed = rarithmetic.r_int(tp.c_tv_sec) ^ rarithmetic.r_int(tp.c_tv_usec)
        
        if HAS_RANDOM:
            srandom(seed)
        else:
            srand(seed)

    new_c_con_func_for_mod(vm, "pluck", pluck, mod)
    new_c_con_func_for_mod(vm, "random", random_func, mod)
    new_c_con_func_for_mod(vm, "shuffle", shuffle, mod)
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_gen
def pluck(vm):
    (col_o,),_ = vm.decode_args(opt="O")

    num_elems = Builtins.type_check_int(vm, vm.get_slot_apply(col_o, "len")).v
    while 1:
        if HAS_RANDOM:
            i = random() % num_elems
        else:
            i = rand() % num_elems
    
        yield vm.get_slot_apply(col_o, "get", [Con_Int(vm, i)])


@con_object_proc
def random_func(vm):
    _,_ = vm.decode_args()

    if HAS_RANDOM:
        return Con_Int(vm, random())
    else:
        return Con_Int(vm, rand())


@con_object_proc
def shuffle(vm):
    (col_o,),_ = vm.decode_args(opt="O")

    num_elems = Builtins.type_check_int(vm, vm.get_slot_apply(col_o, "len")).v
    for i in range(num_elems - 1, 0, -1):
        if HAS_RANDOM:
            j = random() % (i + 1)
        else:
            j = rand() % (i + 1)
        
        i_o = Con_Int(vm, i)
        j_o = Con_Int(vm, j)
        ith = vm.get_slot_apply(col_o, "get", [i_o])
        jth = vm.get_slot_apply(col_o, "get", [j_o])
        vm.get_slot_apply(col_o, "set", [i_o, jth])
        vm.get_slot_apply(col_o, "set", [j_o, ith])
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)
########NEW FILE########
__FILENAME__ = Con_Sys
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import sys
import Config
from Builtins import *




def init(vm):
    mod = new_c_con_module(vm, "Sys", "Sys", __file__, import_, \
      ["print", "println", "stdin", "stdout", "stderr", "vm_path", "program_path", "argv", \
       "version", "version_date", "exit"])
    vm.set_builtin(BUILTIN_SYS_MODULE, mod)
        
    return mod


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")

    mod.set_defn(vm, "vm_path", Con_String(vm, vm.vm_path))
    mod.set_defn(vm, "argv", Con_List(vm, [Con_String(vm, x) for x in vm.argv]))

    new_c_con_func_for_mod(vm, "exit", exit, mod)
    new_c_con_func_for_mod(vm, "print", print_, mod)
    new_c_con_func_for_mod(vm, "println", println, mod)
    
    # Setup stdin, stderr, and stout
    
    file_mod = vm.get_builtin(BUILTIN_C_FILE_MODULE)
    file_class = file_mod.get_defn(vm, "File")
    mod.set_defn(vm, "stdin", \
      vm.get_slot_apply(file_class, "new", [Con_Int(vm, 0), Con_String(vm, "r")]))
    mod.set_defn(vm, "stdout", \
      vm.get_slot_apply(file_class, "new", [Con_Int(vm, 1), Con_String(vm, "w")]))
    mod.set_defn(vm, "stderr", \
      vm.get_slot_apply(file_class, "new", [Con_Int(vm, 2), Con_String(vm, "w")]))
    
    # Version info
    
    mod.set_defn(vm, "version", Con_String(vm, Config.CON_VERSION))
    mod.set_defn(vm, "version_date", Con_String(vm, Config.CON_DATE))
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def exit(vm):
    (c_o,),_ = vm.decode_args(opt="I")

    if c_o is None:
        c_o = Con_Int(vm, 0)
    
    raise vm.raise_helper("System_Exit_Exception", [c_o])


@con_object_proc
def print_(vm):
    mod = vm.get_funcs_mod()
    _,vargs = vm.decode_args(vargs=True)
    stdout = mod.get_defn(vm, "stdout")

    for o in vargs:
        if isinstance(o, Con_String):
            vm.get_slot_apply(stdout, "write", [o])
        else:
            vm.get_slot_apply(stdout, "write", [vm.get_slot_apply(o, "to_str")])

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def println(vm):
    mod = vm.get_funcs_mod()
    _,vargs = vm.decode_args(vargs=True)
    stdout = mod.get_defn(vm, "stdout")

    for o in vargs:
        if isinstance(o, Con_String):
            vm.get_slot_apply(stdout, "write", [o])
        else:
            vm.get_slot_apply(stdout, "write", [vm.get_slot_apply(o, "to_str")])
    vm.get_slot_apply(stdout, "write", [Con_String(vm, "\n")])

    return vm.get_builtin(BUILTIN_NULL_OBJ)

########NEW FILE########
__FILENAME__ = Con_Thread
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


from Builtins import *




def init(vm):
    return new_c_con_module(vm, "Thread", "Thread", __file__, import_, \
      ["get_continuation_src_infos"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")
    
    new_c_con_func_for_mod(vm, "get_continuation_src_infos", get_continuation_src_infos, mod)
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def get_continuation_src_infos(vm):
    (levs_o,),_ = vm.decode_args("I")
    assert isinstance(levs_o, Con_Int)

    mod, bc_off = vm.get_mod_and_bc_off(levs_o.v)
    if bc_off > -1:
        src_infos = mod.bc_off_to_src_infos(vm, bc_off)
    else:
        src_infos = vm.get_builtin(BUILTIN_NULL_OBJ)

    return src_infos

########NEW FILE########
__FILENAME__ = Con_VM
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


from Builtins import *




def init(vm):
    return new_c_con_module(vm, "VM", "VM", __file__, \
      import_, \
      ["add_modules", "del_mod", "find_module", "import_module", "iter_mods"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")

    new_c_con_func_for_mod(vm, "add_modules", add_modules, mod)
    new_c_con_func_for_mod(vm, "del_mod", del_mod, mod)
    new_c_con_func_for_mod(vm, "find_module", find_module, mod)
    new_c_con_func_for_mod(vm, "import_module", import_module, mod)
    new_c_con_func_for_mod(vm, "iter_mods", iter_mods, mod)
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def add_modules(vm):
    (mods_o,),_ = vm.decode_args("O")

    vm.pre_get_slot_apply_pump(mods_o, "iter")
    while 1:
        e_o = vm.apply_pump()
        if not e_o:
            break
        e_o = type_check_module(vm, e_o)
        vm.mods[e_o.id_] = e_o
    
    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def del_mod(vm):
    (mod_id_o,),_ = vm.decode_args("S")
    assert isinstance(mod_id_o, Con_String)

    if mod_id_o.v not in vm.mods:
        vm.raise_helper("Key_Exception", [mod_id_o])

    del vm.mods[mod_id_o.v]

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def find_module(vm):
    (mod_id_o,),_ = vm.decode_args("S")
    assert isinstance(mod_id_o, Con_String)
    
    m_o = vm.find_mod(mod_id_o.v)
    if m_o is None:
        m_o = vm.get_builtin(BUILTIN_FAIL_OBJ)
    
    return m_o


@con_object_proc
def import_module(vm):
    (mod_o,),_ = vm.decode_args("M")
    assert isinstance(mod_o, Con_Module)

    mod_o.import_(vm)
    return mod_o


@con_object_gen
def iter_mods(vm):
    _,_ = vm.decode_args("")
    
    for mod in vm.mods.values():
        yield mod

########NEW FILE########
__FILENAME__ = libXML2
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


from rpython.rlib import rarithmetic, objectmodel
from rpython.rtyper.lltypesystem import llmemory, lltype, rffi
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rtyper.annlowlevel import llhelper
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from Builtins import *
from Core import *
import Config, Target


eci                        = ExternalCompilationInfo(includes=["libxml/parser.h"], \
                               include_dirs=Config.LIBXML2_INCLUDE_DIRS, \
                               library_dirs=Config.LIBXML2_LIBRARY_DIRS, \
                               libraries=Config.LIBXML2_LIBRARIES, \
                               link_extra=Config.LIBXML2_LINK_FLAGS, \
                               link_files=[Config.LIBXML2_A])
xmlCharP                   = lltype.Ptr(lltype.Array(rffi.UCHAR, hints={'nolength': True}))
xmlCharPP                  = lltype.Ptr(lltype.Array(xmlCharP, hints={'nolength': True}))
charactersSAXFunc          = lltype.FuncType((rffi.VOIDP, xmlCharP, rffi.INT), lltype.Void)
charactersSAXFuncP         = lltype.Ptr(charactersSAXFunc)
startElementNsSAX2Func     = lltype.FuncType((rffi.VOIDP, xmlCharP, xmlCharP, xmlCharP, rffi.INT, \
                               xmlCharPP, rffi.INT, rffi.INT, xmlCharPP), lltype.Void)
startElementNsSAX2FuncP    = lltype.Ptr(startElementNsSAX2Func)
endElementNsSAX2Func       = lltype.FuncType((rffi.VOIDP, xmlCharP, xmlCharP, xmlCharP), lltype.Void)
endElementNsSAX2FuncP      = lltype.Ptr(endElementNsSAX2Func)

class CConfig:
    _compilation_info_     = eci
    xmlSAXHandler          = platform.Struct("struct _xmlSAXHandler", \
                               [("characters", charactersSAXFuncP), ("initialized", rffi.UINT), \
                               ("startElementNs", startElementNsSAX2FuncP), \
                               ("endElementNs", endElementNsSAX2FuncP)])
    XML_SAX2_MAGIC         = platform.DefinedConstantInteger("XML_SAX2_MAGIC")

cconfig = platform.configure(CConfig)
XML_SAX2_MAGIC             = cconfig["XML_SAX2_MAGIC"]
xmlSAXHandler              = cconfig["xmlSAXHandler"]
xmlSAXHandlerP             = lltype.Ptr(xmlSAXHandler)
xmlSAXUserParseMemory      = rffi.llexternal("xmlSAXUserParseMemory", \
                               [xmlSAXHandlerP, rffi.VOIDP, rffi.CCHARP, rffi.INT], rffi.INT, \
                               compilation_info=eci)




def init(vm):
    return new_c_con_module(vm, "libXML2", "libXML2", __file__, import_, \
      ["XML_Exception", "parse"])


@con_object_proc
def import_(vm):
    (mod,),_ = vm.decode_args("O")

    class_class = vm.get_builtin(BUILTIN_CLASS_CLASS)
    user_exception_class = vm.get_builtin(BUILTIN_EXCEPTIONS_MODULE). \
      get_defn(vm, "User_Exception")
    xml_exception = vm.get_slot_apply(class_class, "new", \
      [Con_String(vm, "XML_Exception"), Con_List(vm, [user_exception_class]), mod])
    mod.set_defn(vm, "XML_Exception", xml_exception)

    new_c_con_func_for_mod(vm, "parse", parse, mod)

    return vm.get_builtin(BUILTIN_NULL_OBJ)


@con_object_proc
def parse(vm):
    (xml_o, nodes_mod),_ = vm.decode_args("SM")
    assert isinstance(xml_o, Con_String)
    
    with lltype.scoped_alloc(xmlSAXHandler, zero=True) as h:
        h.c_initialized = rffi.r_uint(XML_SAX2_MAGIC)
        h.c_characters = llhelper(charactersSAXFuncP, _characters)
        h.c_startElementNs = llhelper(startElementNsSAX2FuncP, _start_element)
        h.c_endElementNs = llhelper(endElementNsSAX2FuncP, _end_element)
        docs_eo = Con_List(vm, [])
        _storage_hack.push(_Store(vm, [docs_eo], nodes_mod))
        r = xmlSAXUserParseMemory(h, lltype.nullptr(rffi.VOIDP.TO), xml_o.v, len(xml_o.v))
    if r < 0 or len(_storage_hack.peek().elems_stack) != 1:
        raise Exception("XXX")
    _storage_hack.pop()
    doc_o = vm.get_slot_apply(nodes_mod.get_defn(vm, "Doc"), "new", [docs_eo])
    
    return doc_o


class _Store:
    __slots__ = ("vm", "elems_stack", "nodes_mod")
    _immutable_slots_ = ("vm", "elems_stack", "nodes_mod")

    def __init__(self, vm, elems_stack, nodes_mod):
        self.vm = vm
        self.elems_stack = elems_stack
        self.nodes_mod = nodes_mod


# A global storage to be able to recover W_CallbackPtr object out of number
class _Storage_Hack:
    def __init__(self):
        self._stores = []

    def push(self, store):
        self._stores.append(store)

    def peek(self):
        return self._stores[-1]

    def pop(self):
        self._stores.pop()

_storage_hack = _Storage_Hack()


def _characters(ctx, chrs, chrs_len):
    st = _storage_hack.peek()
    vm = st.vm
    s_o = Con_String(vm, \
      rffi.charpsize2str(rffi.cast(rffi.CCHARP, chrs), rarithmetic.intmask(chrs_len)))
    vm.get_slot_apply(st.elems_stack[-1], "append", [s_o])


def _start_element(ctx, localname, prefix, URI, nb_namespaces, namespaces, nb_attributes, nb_defaulted, attributes):
    st = _storage_hack.peek()
    vm = st.vm
    nodes_mod = st.nodes_mod

    name_o = Con_String(vm, rffi.charp2str(rffi.cast(rffi.CCHARP, localname)))
    if prefix:
        prefix_o = Con_String(vm, rffi.charp2str(rffi.cast(rffi.CCHARP, prefix)))
        namespace_o = Con_String(vm, rffi.charp2str(rffi.cast(rffi.CCHARP, URI)))
    else:
        prefix_o = namespace_o = Con_String(vm, "")

    attributes_l = []
    current_attr = attributes
    for i in range(int(nb_attributes) + int(nb_defaulted)):
        attr_name_o = Con_String(vm, rffi.charp2str(rffi.cast(rffi.CCHARP, current_attr[0])))
        attr_len = rffi.cast(lltype.Unsigned, \
          current_attr[4]) - rffi.cast(lltype.Unsigned, current_attr[3])
        attr_val_o = Con_String(vm, \
          rffi.charpsize2str(rffi.cast(rffi.CCHARP, current_attr[3]), rarithmetic.intmask(attr_len)))
            
        if current_attr[1]:
            attr_prefix_o = Con_String(vm, rffi.charp2str(rffi.cast(rffi.CCHARP, current_attr[1])))
            attr_namespace_o = Con_String(vm, rffi.charp2str(rffi.cast(rffi.CCHARP, current_attr[2])))
        else:
            attr_prefix_o = attr_namespace_o = Con_String(vm, "")
        
        attr_o = vm.get_slot_apply(nodes_mod.get_defn(vm, "Attr"), "new", \
          [attr_name_o, attr_val_o, attr_prefix_o, attr_namespace_o])
        attributes_l.append(attr_o)
        
        current_attr = rffi.ptradd(current_attr, 5)
    attributes_o = Con_Set(vm, attributes_l)
    elem_o = vm.get_slot_apply(nodes_mod.get_defn(vm, "Elem"), "new", \
      [name_o, attributes_o, prefix_o, namespace_o])
    vm.get_slot_apply(st.elems_stack[-1], "append", [elem_o])
    st.elems_stack.append(elem_o)


def _end_element(ctx, localname, prefix, URI):
    st = _storage_hack.peek()
    st.elems_stack.pop()
########NEW FILE########
__FILENAME__ = Stdlib_Modules
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


STDLIB_ARRAY = "Array"
STDLIB_BUILTINS = "Builtins"
STDLIB_CURSES = "Curses"
STDLIB_C_EARLEY_PARSER = "C_Earley_Parser"
STDLIB_C_PLATFORM_ENV = "C_Platform_Env"
STDLIB_C_PLATFORM_EXEC = "C_Platform_Exec"
STDLIB_C_PLATFORM_HOST = "C_Platform_Host"
STDLIB_C_PLATFORM_PROPERTIES = "C_Platform_Properties"
STDLIB_C_STRINGS = "C_Strings"
STDLIB_C_TIME = "C_Time"
STDLIB_EXCEPTIONS = "Exceptions"
STDLIB_LIBXML2 = "libXML2"
STDLIB_PCRE = "PCRE"
STDLIB_POSIX_FILE = "POSIX_File"
STDLIB_RANDOM = "Random"
STDLIB_SYS = "Sys"
STDLIB_THREAD = "Thread"
STDLIB_VM = "VM"
STDLIB_CPK_EARLEY_DSL = "/Stdlib/CPK/Earley/DSL.cv"
STDLIB_CPK_EARLEY_GRAMMAR = "/Stdlib/CPK/Earley/Grammar.cv"
STDLIB_CPK_EARLEY_PARSER = "/Stdlib/CPK/Earley/Parser.cv"
STDLIB_CPK_TOKEN = "/Stdlib/CPK/Token.cv"
STDLIB_CPK_TOKENS = "/Stdlib/CPK/Tokens.cv"
STDLIB_CPK_TRAVERSER = "/Stdlib/CPK/Traverser.cv"
STDLIB_CPK_TREE = "/Stdlib/CPK/Tree.cv"
STDLIB_PLATFORM_ENV = "/Stdlib/Platform/Env.cv"
STDLIB_PLATFORM_EXEC = "/Stdlib/Platform/Exec.cv"
STDLIB_PLATFORM_HOST = "/Stdlib/Platform/Host.cv"
STDLIB_PLATFORM_PROPERTIES = "/Stdlib/Platform/Properties.cv"
STDLIB_XML_NODES = "/Stdlib/XML/Nodes.cv"
STDLIB_XML_XDM = "/Stdlib/XML/XDM.cv"
STDLIB_XML_XHTML = "/Stdlib/XML/XHTML.cv"
STDLIB_BACKTRACE = "/Stdlib/Backtrace.cv"
STDLIB_CEI = "/Stdlib/CEI.cv"
STDLIB_FILE = "/Stdlib/File.cv"
STDLIB_FUNCTIONAL = "/Stdlib/Functional.cv"
STDLIB_MATHS = "/Stdlib/Maths.cv"
STDLIB_NUMBERS = "/Stdlib/Numbers.cv"
STDLIB_PARSE_ARGS = "/Stdlib/Parse_Args.cv"
STDLIB_SORT = "/Stdlib/Sort.cv"
STDLIB_STRINGS = "/Stdlib/Strings.cv"
STDLIB_TIME = "/Stdlib/Time.cv"

########NEW FILE########
__FILENAME__ = Target
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


from rpython.rlib.jit import *
from rpython.rtyper.lltypesystem import lltype, rffi

import sys




if sys.maxsize > 2**32:
    INTSIZE = 8
    FLOATSIZE = 8
else:
    INTSIZE = 4
    FLOATSIZE = 8

INSTR_NAMES = [None, "EXBI", "VAR_LOOKUP", "VAR_ASSIGN", None, "ADD_FAILURE_FRAME", "ADD_FAIL_UP_FRAME", "REMOVE_FAILURE_FRAME", "IS_ASSIGNED", "IS", "FAIL_NOW", "POP", "LIST", "SLOT_LOOKUP", "APPLY", "FUNC_DEFN", "RETURN", "BRANCH", "YIELD", None, "IMPORT", "DICT", "DUP", "PULL", "CHANGE_FAIL_POINT", None, "BUILTIN_LOOKUP", "ASSIGN_SLOT", "EYIELD", "ADD_EXCEPTION_FRAME", None, "INSTANCE_OF", "REMOVE_EXCEPTION_FRAME", "RAISE", "SET_ITEM", "UNPACK_ARGS", "SET", "BRANCH_IF_NOT_FAIL", "BRANCH_IF_FAIL", "CONST_GET", None, "PRE_SLOT_LOOKUP_APPLY", "UNPACK_ASSIGN", "EQ", "LE", "ADD", "SUBTRACT", "NEQ", "LE_EQ", "GR_EQ", "GT", "MODULE_LOOKUP"]

CONST_STRING = 0
CONST_INT = 1
CONST_FLOAT = 2

if INTSIZE == 8:
    BC_HD_HEADER = 0 * 8
    BC_HD_VERSION = 1 * 8
    BC_HD_NUM_MODULES = 2 * 8
    BC_HD_MODULES = 3 * 8

    BC_MOD_HEADER = 0 * 8
    BC_MOD_VERSION = 1 * 8
    BC_MOD_NAME = 2 * 8
    BC_MOD_NAME_SIZE = 3 * 8
    BC_MOD_ID = 4 * 8
    BC_MOD_ID_SIZE = 5 * 8
    BC_MOD_SRC_PATH = 6 * 8
    BC_MOD_SRC_PATH_SIZE = 7 * 8
    BC_MOD_INSTRUCTIONS = 8 * 8
    BC_MOD_INSTRUCTIONS_SIZE = 9 * 8
    BC_MOD_IMPORTS = 10 * 8
    BC_MOD_IMPORTS_SIZE = 11 * 8
    BC_MOD_NUM_IMPORTS = 12 * 8
    BC_MOD_SRC_POSITIONS = 13 * 8
    BC_MOD_SRC_POSITIONS_SIZE = 14 * 8
    BC_MOD_NEWLINES = 15 * 8
    BC_MOD_NUM_NEWLINES = 16 * 8
    BC_MOD_TL_VARS_MAP = 17 * 8
    BC_MOD_TL_VARS_MAP_SIZE = 18 * 8
    BC_MOD_NUM_TL_VARS_MAP = 19 * 8
    BC_MOD_NUM_CONSTANTS = 20 * 8
    BC_MOD_CONSTANTS_OFFSETS = 21 * 8
    BC_MOD_CONSTANTS = 22 * 8
    BC_MOD_CONSTANTS_SIZE = 23 * 8
    BC_MOD_MOD_LOOKUPS = 24 * 8
    BC_MOD_MOD_LOOKUPS_SIZE = 25 * 8
    BC_MOD_NUM_MOD_LOOKUPS = 26 * 8
    BC_MOD_IMPORT_DEFNS = 27 * 8
    BC_MOD_NUM_IMPORT_DEFNS = 28 * 8
    BC_MOD_SIZE = 29 * 8
    
    # Libraries

    BC_LIB_HD_HEADER = 0 * 8
    BC_LIB_HD_FORMAT_VERSION = 1 * 8
    BC_LIB_HD_NUM_MODULES = 2 * 8
    BC_LIB_HD_MODULES = 3 * 8
    
    CON_INSTR_EXBI = 1                    # bits 0-7 1, bits 8-31 size of field name, bits 32-.. field name
    CON_INSTR_VAR_LOOKUP = 2              # bits 0-7 2, bits 8-19 closures offset, bits 20-31 var number
    CON_INSTR_VAR_ASSIGN = 3              # bits 0-7 3, bits 8-19 closures offset, bits 20-31 var number
    CON_INSTR_ADD_FAILURE_FRAME = 5       # bits 0-7 5, bits 8-30 pc offset, bit 31 offset sign
    CON_INSTR_ADD_FAIL_UP_FRAME = 6       # bits 0-7 6
    CON_INSTR_REMOVE_FAILURE_FRAME = 7    # bits 0-7 7
    CON_INSTR_IS_ASSIGNED = 8             # Stored as two words
                                          #   Word 1: bits 0-7 8, bits 8-19 closures offset, bits 20-31 var number
                                          #   Word 2: bits bits 8-30 pc offset, bit 31 offset sign
    CON_INSTR_IS = 9                      # bits 0-7 9
    CON_INSTR_FAIL_NOW = 10               # bits 0-7 10
    CON_INSTR_POP = 11                    # bits 0-7 11
    CON_INSTR_LIST = 12                   # bits 0-7 12, bits 8-31 number of list elements
    CON_INSTR_SLOT_LOOKUP = 13            # bits 0-7 13, bits 8-31 size of slot name, bits 32-.. slot name
    CON_INSTR_APPLY = 14                  # bits 0-7 14, bits 8-31 number of args
    CON_INSTR_FUNC_DEFN = 15              # bits 0-7 15, bits 8-9 is_bound
    CON_INSTR_RETURN = 16                 # bits 0-7 16
    CON_INSTR_BRANCH = 17                 # bits 0-7 17, bits 8-30 pc offset, bit 31 offset sign (0 = positive, 1 = negative)
    CON_INSTR_YIELD = 18                  # bits 0-7 18
    CON_INSTR_IMPORT = 20                 # bits 0-7 20, bits 8-31 module number
    CON_INSTR_DICT = 21                   # bits 0-7 21, bits 8-31 number of dictionary elements
    CON_INSTR_DUP = 22                    # bits 0-7 22
    CON_INSTR_PULL = 23                   # bits 0-7 23, bits 8-31 := number of entries back in the stack to pull the value from
    CON_INSTR_BUILTIN_LOOKUP = 26         # bits 0-7 26, bits 8-15 builtin number
    CON_INSTR_ASSIGN_SLOT = 27            # bits 0-7 13, bits 8-31 size of slot name, bits 32-.. slot name
    CON_INSTR_EYIELD = 28                 # bits 0-7 28
    CON_INSTR_ADD_EXCEPTION_FRAME = 29    # bits 0-7 5, bits 8-30 pc offset, bit 31 offset sign
    CON_INSTR_INSTANCE_OF = 31            # bits 0-7 31
    CON_INSTR_REMOVE_EXCEPTION_FRAME = 32 # bits 0-7 32
    CON_INSTR_RAISE = 33                  # bits 0-7 33
    CON_INSTR_SET_ITEM = 34               # bits 0-7 34
    CON_INSTR_UNPACK_ARGS = 35            # bits 0-7 := 35, bits 8-15 := num normal args, bit 16 := has var args
                                          #  each variable is then a subsequent word:
                                          #  word 1: 0-11 := var number, bit 12 := is mandatory arg
    CON_INSTR_SET = 36                    # bits 0-7 36, bits 8-31 number of set elements
    CON_INSTR_BRANCH_IF_NOT_FAIL = 37     # bits 0-7 37, bits 8-30 pc offset, bit 31 offset sign
    CON_INSTR_BRANCH_IF_FAIL = 38         # bits 0-7 38, bits 8-30 pc offset, bit 31 offset sign
    CON_INSTR_CONST_GET = 39              # bits 0-7 39, bits 8-30 constant num
    CON_INSTR_PRE_SLOT_LOOKUP_APPLY = 41  # bits 0-7 41, bits 8-31 size of slot name, bits 32-.. slot name
    CON_INSTR_UNPACK_ASSIGN = 42          # bits 0-7 42, bits 8-31 number of elements to unpack
    CON_INSTR_EQ = 43                     # bits 0-7 43
    CON_INSTR_LE = 44                     # bits 0-7 44
    CON_INSTR_ADD = 45                    # bits 0-7 45
    CON_INSTR_SUBTRACT = 46               # bits 0-7 46
    CON_INSTR_NEQ = 47                    # bits 0-7 47
    CON_INSTR_LE_EQ = 48                  # bits 0-7 48
    CON_INSTR_GR_EQ = 49                  # bits 0-7 49
    CON_INSTR_GT = 50                     # bits 0-7 50
    CON_INSTR_MODULE_LOOKUP = 51          # bits 0-7 51, bits 8-31 := size of definition name, bits 32-.. := definition name

    @elidable_promote()
    def extract_str(bc, off, size):
        assert off > 0 and size >= 0
        return rffi.charpsize2str(rffi.ptradd(bc, off), size)

    @elidable_promote("1")
    def read_word(bc, i):
        return rffi.cast(lltype.Signed, rffi.cast(rffi.LONGP, bc)[i / 8])

    @elidable_promote("1")
    def read_uint32_word(bc, i):
        return rffi.cast(lltype.Signed, rffi.cast(rffi.UINTP, bc)[i / 4])

    @elidable_promote("1")
    def read_float(bc, i):
        return rffi.cast(lltype.Float, rffi.cast(rffi.DOUBLEP, bc)[i / 8])

    @elidable_promote()
    def align(i):
        return (i + 7) & ~7

    @elidable_promote()
    def unpack_exbi(instr):
        return (4, (instr & 0xFFFFFF00) >> 8)

    @elidable_promote()
    def get_instr(instr):
        return instr & 0xFF

    @elidable_promote()
    def unpack_var_lookup(instr):
        return ((instr & 0x000FFF00) >> 8, (instr & 0xFFF00000) >> 20)

    @elidable_promote()
    def unpack_var_assign(instr):
        return ((instr & 0x000FFF00) >> 8, (instr & 0xFFF00000) >> 20)

    @elidable_promote()
    def unpack_int(instr):
        x = 63
        if (instr & (1 << x)) >> 8:
            return -((instr & ((1 << x) - 256)) >> 8)
        else:
            return (instr & ((1 << x) - 256)) >> 8

    @elidable_promote()
    def unpack_add_failure_frame(instr):
        if (instr & 0x80000000) >> 8:
            return -((instr & 0x7FFFFF00) >> 8)
        else:
            return (instr & 0x7FFFFF00) >> 8

    @elidable_promote()
    def unpack_is_assigned(instr2):
        if (instr2 & 0x80000000) >> 8:
            return -((instr2 & 0x7FFFFF00) >> 8)
        else:
            return (instr2 & 0x7FFFFF00) >> 8

    @elidable_promote()
    def unpack_func_defn(instr):
        return ((instr & 0x00000100) >> 8, (instr & 0x7ffffe00) >> 9)

    @elidable_promote()
    def unpack_list(instr):
        return (instr & 0xFFFFFF00) >> 8

    @elidable_promote()
    def unpack_slot_lookup(instr):
        return (4, (instr & 0xFFFFFF00) >> 8)

    @elidable_promote()
    def unpack_apply(instr):
        return (instr & 0xFFFFFF00) >> 8
    
    @elidable_promote()
    def unpack_branch(instr):
        if (instr & 0x80000000) >> 8:
            return -((instr & 0x7FFFFF00) >> 8)
        else:
            return (instr & 0x7FFFFF00) >> 8

    @elidable_promote()
    def unpack_pull(instr):
        return (instr & 0xFFFFFF00) >> 8

    @elidable_promote()
    def unpack_import(instr):
        return (instr & 0xFFFFFF00) >> 8

    @elidable_promote()
    def unpack_dict(instr):
        return (instr & 0xFFFFFF00) >> 8

    @elidable_promote()
    def unpack_string(instr):
        return (4, (instr & 0xFFFFFF00) >> 8)

    @elidable_promote()
    def unpack_builtin_lookup(instr):
        return (instr & 0xFFFFFF00) >> 8

    @elidable_promote()
    def unpack_assign_slot(instr):
        return (4, (instr & 0xFFFFFF00) >> 8)

    @elidable_promote()
    def unpack_add_exception_frame(instr):
        if (instr & 0x80000000) >> 8:
            return -((instr & 0x7FFFFF00) >> 8)
        else:
            return (instr & 0x7FFFFF00) >> 8

    @elidable_promote()
    def unpack_unpack_args(instr):
        return ((instr & 0x0000FF00) >> 8, (instr & 0x00010000) >> 16)

    @elidable_promote()
    def unpack_set(instr):
        return (instr & 0xFFFFFF00) >> 8

    @elidable_promote()
    def unpack_unpack_args_is_mandatory(arg_info):
        return (arg_info & 0x00000100) >> 8

    @elidable_promote()
    def unpack_unpack_args_arg_num(arg_info):
        return arg_info & 0x000000FF

    @elidable_promote()
    def unpack_constant_get(instr):
        return (instr & 0xFFFFFF00) >> 8

    @elidable_promote()
    def unpack_unpack_assign(instr):
        return (instr & 0xFFFFFF00) >> 8

    @elidable_promote()
    def unpack_branch_if_not_fail(instr):
        if (instr & 0x80000000) >> 8:
            return -((instr & 0x7FFFFF00) >> 8)
        else:
            return (instr & 0x7FFFFF00) >> 8

    @elidable_promote()
    def unpack_mod_lookup(instr):
        return (4, (instr & 0xFFFFFF00) >> 8)
else:
    assert INTSIZE == 4
    BC_HD_HEADER = 0 * 4
    BC_HD_VERSION = 2 * 4
    BC_HD_NUM_MODULES = 3 * 4
    BC_HD_MODULES = 4 * 4

    BC_MOD_HEADER = 0 * 4
    BC_MOD_VERSION = 2 * 4
    BC_MOD_NAME = 3 * 4
    BC_MOD_NAME_SIZE = 4 * 4
    BC_MOD_ID = 5 * 4
    BC_MOD_ID_SIZE = 6 * 4
    BC_MOD_SRC_PATH = 7 * 4
    BC_MOD_SRC_PATH_SIZE = 8 * 4
    BC_MOD_INSTRUCTIONS = 9 * 4
    BC_MOD_INSTRUCTIONS_SIZE = 10 * 4
    BC_MOD_IMPORTS = 11 * 4
    BC_MOD_IMPORTS_SIZE = 12 * 4
    BC_MOD_NUM_IMPORTS = 13 * 4
    BC_MOD_SRC_POSITIONS = 14 * 4
    BC_MOD_SRC_POSITIONS_SIZE = 15 * 4
    BC_MOD_NEWLINES = 16 * 4
    BC_MOD_NUM_NEWLINES = 17 * 4
    BC_MOD_TL_VARS_MAP = 18 * 4
    BC_MOD_TL_VARS_MAP_SIZE = 19 * 4
    BC_MOD_NUM_TL_VARS_MAP = 20 * 4
    BC_MOD_NUM_CONSTANTS = 21 * 4
    BC_MOD_CONSTANTS_OFFSETS = 22 * 4
    BC_MOD_CONSTANTS = 23 * 4
    BC_MOD_CONSTANTS_SIZE = 24 * 4
    BC_MOD_MOD_LOOKUPS = 25 * 4
    BC_MOD_MOD_LOOKUPS_SIZE = 26 * 4
    BC_MOD_NUM_MOD_LOOKUPS = 27 * 4
    BC_MOD_IMPORT_DEFNS = 28 * 4
    BC_MOD_NUM_IMPORT_DEFNS = 29 * 4
    BC_MOD_SIZE = 30 * 4
    
    # Libraries

    BC_LIB_HD_HEADER = 0 * 4
    BC_LIB_HD_FORMAT_VERSION = 2 * 4
    BC_LIB_HD_NUM_MODULES = 3 * 4
    BC_LIB_HD_MODULES = 4 * 4

    CON_INSTR_EXBI = 1                    # bits 0-7 1, bits 8-31 size of field name, bits 32-.. field name
    CON_INSTR_VAR_LOOKUP = 2              # bits 0-7 2, bits 8-19 closures offset, bits 20-31 var number
    CON_INSTR_VAR_ASSIGN = 3              # bits 0-7 3, bits 8-19 closures offset, bits 20-31 var number
    CON_INSTR_ADD_FAILURE_FRAME = 5       # bits 0-7 5, bits 8-30 pc offset, bit 31 offset sign
    CON_INSTR_ADD_FAIL_UP_FRAME = 6       # bits 0-7 6
    CON_INSTR_REMOVE_FAILURE_FRAME = 7    # bits 0-7 7
    CON_INSTR_IS_ASSIGNED = 8             # Stored as two words
                                          #   Word 1: bits 0-7 8, bits 8-19 closures offset, bits 20-31 var number
                                          #   Word 2: bits bits 8-30 pc offset, bit 31 offset sign
    CON_INSTR_IS = 9                      # bits 0-7 9
    CON_INSTR_FAIL_NOW = 10               # bits 0-7 10
    CON_INSTR_POP = 11                    # bits 0-7 11
    CON_INSTR_LIST = 12                   # bits 0-7 12, bits 8-31 number of list elements
    CON_INSTR_SLOT_LOOKUP = 13            # bits 0-7 13, bits 8-31 size of slot name, bits 32-.. slot name
    CON_INSTR_APPLY = 14                  # bits 0-7 14, bits 8-31 number of args
    CON_INSTR_FUNC_DEFN = 15              # bits 0-7 15, bits 8-9 is_bound
    CON_INSTR_RETURN = 16                 # bits 0-7 16
    CON_INSTR_BRANCH = 17                 # bits 0-7 17, bits 8-30 pc offset, bit 31 offset sign (0 = positive, 1 = negative)
    CON_INSTR_YIELD = 18                  # bits 0-7 18
    CON_INSTR_IMPORT = 20                 # bits 0-7 20, bits 8-31 module number
    CON_INSTR_DICT = 21                   # bits 0-7 21, bits 8-31 number of dictionary elements
    CON_INSTR_DUP = 22                    # bits 0-7 22
    CON_INSTR_PULL = 23                   # bits 0-7 23, bits 8-31 := number of entries back in the stack to pull the value from
    CON_INSTR_BUILTIN_LOOKUP = 26         # bits 0-7 26, bits 8-15 builtin number
    CON_INSTR_ASSIGN_SLOT = 27            # bits 0-7 13, bits 8-31 size of slot name, bits 32-.. slot name
    CON_INSTR_EYIELD = 28                 # bits 0-7 28
    CON_INSTR_ADD_EXCEPTION_FRAME = 29    # bits 0-7 5, bits 8-30 pc offset, bit 31 offset sign
    CON_INSTR_INSTANCE_OF = 31            # bits 0-7 31
    CON_INSTR_REMOVE_EXCEPTION_FRAME = 32 # bits 0-7 32
    CON_INSTR_RAISE = 33                  # bits 0-7 33
    CON_INSTR_SET_ITEM = 34               # bits 0-7 34
    CON_INSTR_UNPACK_ARGS = 35            # bits 0-7 := 35, bits 8-15 := num normal args, bit 16 := has var args
                                          #  each variable is then a subsequent word:
                                          #  word 1: 0-11 := var number, bit 12 := is mandatory arg
    CON_INSTR_SET = 36                    # bits 0-7 36, bits 8-31 number of set elements
    CON_INSTR_BRANCH_IF_NOT_FAIL = 37     # bits 0-7 37, bits 8-30 pc offset, bit 31 offset sign
    CON_INSTR_BRANCH_IF_FAIL = 38         # bits 0-7 38, bits 8-30 pc offset, bit 31 offset sign
    CON_INSTR_CONST_GET = 39              # bits 0-7 39, bits 8-30 constant num
    CON_INSTR_PRE_SLOT_LOOKUP_APPLY = 41  # bits 0-7 41, bits 8-31 size of slot name, bits 32-.. slot name
    CON_INSTR_UNPACK_ASSIGN = 42          # bits 0-7 42, bits 8-31 number of elements to unpack
    CON_INSTR_EQ = 43                     # bits 0-7 43
    CON_INSTR_LE = 44                     # bits 0-7 44
    CON_INSTR_ADD = 45                    # bits 0-7 45
    CON_INSTR_SUBTRACT = 46               # bits 0-7 46
    CON_INSTR_NEQ = 47                    # bits 0-7 47
    CON_INSTR_LE_EQ = 48                  # bits 0-7 48
    CON_INSTR_GR_EQ = 49                  # bits 0-7 49
    CON_INSTR_GT = 50                     # bits 0-7 50
    CON_INSTR_MODULE_LOOKUP = 51          # bits 0-7 51, bits 8-31 := size of definition name, bits 32-.. := definition name

    @elidable_promote()
    def extract_str(bc, off, size):
        assert off > 0 and size >= 0
        return rffi.charpsize2str(rffi.ptradd(bc, off), size)

    @elidable_promote("1")
    def read_word(bc, i):
        return rffi.cast(lltype.Signed, rffi.cast(rffi.INTP, bc)[i / 4])

    @elidable_promote("1")
    def read_uint32_word(bc, i):
        return rffi.cast(lltype.Signed, rffi.cast(rffi.UINTP, bc)[i / 4])

    @elidable_promote("1")
    def read_float(bc, i):
        return rffi.cast(lltype.Float, rffi.cast(rffi.DOUBLEP, bc)[i / 8])

    @elidable_promote()
    def align(i):
        return (i + 3) & ~3

    @elidable_promote()
    def unpack_exbi(instr):
        x = 0xFFFFFF
        return (4, (instr & (x << 8)) >> 8)

    @elidable_promote()
    def get_instr(instr):
        return instr & 0xFF

    @elidable_promote()
    def unpack_var_lookup(instr):
        x = 0xFFF
        return ((instr & (x << 8)) >> 8, (instr & (x << 20)) >> 20)

    @elidable_promote()
    def unpack_var_assign(instr):
        x = 0xFFF
        return ((instr & (x << 8)) >> 8, (instr & (x << 20)) >> 20)

    @elidable_promote()
    def unpack_int(instr):
        x = 31
        if (instr & (1 << x)) >> 8:
            return -((instr & ((1 << x) - 256)) >> 8)
        else:
            return (instr & ((1 << x) - 256)) >> 8

    @elidable_promote()
    def unpack_add_failure_frame(instr):
        x = 0x8
        y = 0x7FFFFF
        if (instr & (x << 28)) >> 8:
            return -((instr & (y << 8)) >> 8)
        else:
            return (instr & (y << 8)) >> 8

    @elidable_promote()
    def unpack_is_assigned(instr2):
        x = 0x8
        y = 0x7FFFFF
        if (instr2 & (x << 28)) >> 8:
            return -((instr2 & (y << 8)) >> 8)
        else:
            return (instr2 & (y << 8)) >> 8

    @elidable_promote()
    def unpack_func_defn(instr):
        x = 0x7ffffe
        return ((instr & 0x00000100) >> 8, (instr & (x << 8)) >> 9)

    @elidable_promote()
    def unpack_list(instr):
        x = 0xFFFFFF
        return (instr & (x << 8)) >> 8

    @elidable_promote()
    def unpack_slot_lookup(instr):
        x = 0xFFFFFF
        return (4, (instr & (x << 8)) >> 8)

    @elidable_promote()
    def unpack_apply(instr):
        x = 0xFFFFFF
        return (instr & (x << 8)) >> 8
    
    @elidable_promote()
    def unpack_branch(instr):
        x = 0x8
        y = 0x7FFFFF
        if (instr & (x << 28)) >> 8:
            return -((instr & (y << 8)) >> 8)
        else:
            return (instr & (y << 8)) >> 8

    @elidable_promote()
    def unpack_pull(instr):
        x = 0xFFFFFF
        return (instr & (x << 8)) >> 8

    @elidable_promote()
    def unpack_import(instr):
        x = 0xFFFFFF
        return (instr & (x << 8)) >> 8

    @elidable_promote()
    def unpack_dict(instr):
        x = 0xFFFFFF
        return (instr & (x << 8)) >> 8

    @elidable_promote()
    def unpack_string(instr):
        x = 0xFFFFFF
        return (4, (instr & (x << 8)) >> 8)

    @elidable_promote()
    def unpack_builtin_lookup(instr):
        x = 0xFFFFFF
        return (instr & (x << 8)) >> 8

    @elidable_promote()
    def unpack_assign_slot(instr):
        x = 0xFFFFFF
        return (4, (instr & (x << 8)) >> 8)

    @elidable_promote()
    def unpack_add_exception_frame(instr):
        x = 0x8
        y = 0x7FFFFF
        if (instr & (x << 28)) >> 8:
            return -((instr & (y << 8)) >> 8)
        else:
            return (instr & (y << 8)) >> 8

    @elidable_promote()
    def unpack_unpack_args(instr):
        return ((instr & 0x0000FF00) >> 8, (instr & 0x00010000) >> 16)

    @elidable_promote()
    def unpack_set(instr):
        x = 0xFFFFFF
        return (instr & (x << 8)) >> 8

    @elidable_promote()
    def unpack_unpack_args_is_mandatory(arg_info):
        return (arg_info & 0x00000100) >> 8

    @elidable_promote()
    def unpack_unpack_args_arg_num(arg_info):
        return arg_info & 0x000000FF

    @elidable_promote()
    def unpack_constant_get(instr):
        x = 0xFFFFFF
        return (instr & (x << 8)) >> 8

    @elidable_promote()
    def unpack_unpack_assign(instr):
        x = 0xFFFFFF
        return (instr & (x << 8)) >> 8

    @elidable_promote()
    def unpack_branch_if_not_fail(instr):
        x = 0x8
        y = 0x7FFFFF
        if (instr & (x << 28)) >> 8:
            return -((instr & (y << 8)) >> 8)
        else:
            return (instr & (y << 8)) >> 8

    @elidable_promote()
    def unpack_mod_lookup(instr):
        x = 0xFFFFFF
        return (4, (instr & (x << 8)) >> 8)

########NEW FILE########
__FILENAME__ = VM
# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import os, sys

from pypy.config.pypyoption import get_pypy_config
from rpython.rlib import debug, jit, objectmodel
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi

from Core import *
import Builtins, Target




DEBUG = False



def get_printable_location(bc_off, mod_bc, pc, self):
    assert isinstance(pc, BC_PC)
    instr = Target.read_word(mod_bc, bc_off)
    it = Target.get_instr(instr)
    return "%s:%s at offset %s. bytecode: %s" % (pc.mod, pc.off, bc_off, Target.INSTR_NAMES[it])

jitdriver = jit.JitDriver(greens=["bc_off", "mod_bc", "pc", "self"],
                          reds=["prev_bc_off", "cf"],
                          virtualizables=["cf"],
                          get_printable_location=get_printable_location)


class VM(object):
    __slots__ = ("argv", "builtins", "cur_cf", "mods", "pypy_config", "vm_path")
    _immutable_fields = ("argv", "builtins", "cur_cf", "mods", "vm_path")

    def __init__(self): 
        self.builtins = [None] * Builtins.NUM_BUILTINS
        self.mods = {}
        self.cur_cf = None # Current continuation frame
        self.pypy_config = None


    def init(self, vm_path,argv):
        self.vm_path = vm_path
        self.argv = argv
        
        Builtins.bootstrap_con_object(self)
        Builtins.bootstrap_con_class(self)
        Builtins.bootstrap_con_dict(self)
        Builtins.bootstrap_con_func(self)
        Builtins.bootstrap_con_int(self)
        Builtins.bootstrap_con_float(self)
        Builtins.bootstrap_con_list(self)
        Builtins.bootstrap_con_module(self)
        Builtins.bootstrap_con_partial_application(self)
        Builtins.bootstrap_con_set(self)
        Builtins.bootstrap_con_string(self)
        Builtins.bootstrap_con_exception(self)

        import Modules
        for init_func in Modules.BUILTIN_MODULES:
            self.set_mod(init_func(self))

        self.get_mod("Exceptions").import_(self)
        self.get_mod("POSIX_File").import_(self)
        self.get_mod("Sys").import_(self)


    ################################################################################################
    # Generic helper functions
    #


    @jit.elidable
    def get_builtin(self, i):
        if DEBUG:
            assert self.builtins[i] is not None # Builtins can not be read before they are set
        return self.builtins[i]


    def set_builtin(self, i, o):
        if DEBUG:
            assert self.builtins[i] is None # Once set, a builtin can never change
        self.builtins[i] = o


    def set_mod(self, mod):
        self.mods[mod.id_] = mod


    def find_mod(self, mod_id):
        return self.mods.get(mod_id, None)


    def get_mod(self, mod_id):
        m = self.find_mod(mod_id)
        if m is None:
            self.raise_helper("Import_Exception", [Builtins.Con_String(self, mod_id)])
        return m


    def import_stdlib_mod(self, ptl_mod_id):
        if not ptl_mod_id.startswith(os.sep):
            return self.get_mod(ptl_mod_id)
        
        for cnd_mod_id in self.mods.keys():
            bt_cnd_mod_id = cnd_mod_id

            # XXX. The next two operations are pure evil and are basically a poor-man's
            # bootstrapping. They're intended to convert between module IDs across different
            # platforms. The potential problems with the below are fairly obvious, although
            # unlikely to actually manifest themselves in real life.
            if CASE_SENSITIVE_FILENAMES == 0:
                bt_cnd_mod_id = bt_cnd_mod_id.lower()

            if os.sep == "/":
                bt_cnd_mod_id = bt_cnd_mod_id.replace("\\", "/")
            elif os.sep == "\\":
                bt_cnd_mod_id = bt_cnd_mod_id.replace("/", "\\")
            else:
                self.raise_helper("VM_Exception", [Con_String(vm, "Unknown separator %s." % os.sep)])

            if bt_cnd_mod_id.endswith(ptl_mod_id):
                mod = self.get_mod(cnd_mod_id)
                mod.import_(self)
                return mod

        self.raise_helper("Import_Exception", [Builtins.Con_String(self, ptl_mod_id)])


    def has_mod(self, mod_id):
        return mod_id in self.mods



    ################################################################################################
    # Core VM functions
    #

    def apply(self, func, args=None, allow_fail=False):
        o, _ = self.apply_closure(func, args, allow_fail=allow_fail)
        return o


    def get_slot_apply(self, o, n, args=None, allow_fail=False):
        return self.apply(o.get_slot(self, n), args, allow_fail=allow_fail)


    def apply_closure(self, func, args=None, allow_fail=False):
        if not args:
            nargs = 0
        else:
            nargs = len(args)
        
        if isinstance(func, Builtins.Con_Partial_Application):
            cf = self._add_continuation_frame(func.f, nargs + 1)
            cf.stack_extend(func.args)
        else: 
            cf = self._add_continuation_frame(func, nargs)

        if args:
            cf.stack_extend(list(args))

        o = self.execute_proc(cf)
        self._remove_continuation_frame()
        
        if o is self.get_builtin(Builtins.BUILTIN_FAIL_OBJ):
            o = None
        if not allow_fail and o is None:
            self.raise_helper("VM_Exception", [Builtins.Con_String(self, \
              "Function attempting to return fail, but caller can not handle failure.")])

        return o, cf.closure


    def pre_get_slot_apply_pump(self, o, n, args=None):
        return self.pre_apply_pump(o.get_slot(self, n), args)


    def pre_apply_pump(self, func, args=None):
        if not args:
            nargs = 0
        else:
            nargs = len(args)

        cf = self.cur_cf
        gf = Stack_Generator_Frame(cf.gfp, -1)
        cf.gfp = cf.stackpe
        cf.stack_push(gf)
        if isinstance(func, Builtins.Con_Partial_Application):
            new_cf = self._add_continuation_frame(func.f, nargs + 1)
            new_cf.stack_extend(func.args)
        else: 
            new_cf = self._add_continuation_frame(func, nargs)

        if args:
            new_cf.stack_extend(list(args))


    def apply_pump(self, remove_generator_frames=False):
        # At this point, we're in one of two situations:
        #
        #   1) A generator frame has been added but not yet used. So the con stacks look like:
        #        calling function: [..., <generator frame>]
        #        callee function:  [<argument objects>]
        #
        #   2) We need to resume a previous generator. The con stack looks like:
        #        [..., <generator frame>, <random objects>]
        #
        # Fortunately there's an easy way to distinguish the two: if the current continuation on the
        # stack has a generator frame we're in situation #2, otherwise we're in situation #1.

        cf = self.cur_cf
        if cf.gfp == -1:
            # We're in case 1) from above.
            gen = self.execute_gen(cf)
            cf = self.cur_cf
        else:
            # We're in case 2) from above.
            cf.stack_del_from(cf.gfp + 1)
            gf = cf.stack_get(cf.gfp)
            assert isinstance(gf, Stack_Generator_Frame)
            if gf.returned:
                return None
            cf = gf.saved_cf
            assert cf.parent is self.cur_cf
            self.cur_cf = cf
            gen = gf.gen

        try:
            o = gen.next()
            assert o is not None
        except StopIteration:
            cf.returned = True
            o = None

        if cf.returned or o is None:
            self._remove_continuation_frame()
            cf = self.cur_cf
            gf = cf.stack_get(cf.gfp)
            assert isinstance(gf, Stack_Generator_Frame)
            self._remove_generator_frame(cf)
        else:
            saved_cf = self.cur_cf
            self.cur_cf = cf = saved_cf.parent

            # At this point cf.stack looks like:
            #   [..., <gen obj 1>, ..., <gen obj n>, <generator frame>]

            gf = cf.stack_get(cf.gfp)
            assert isinstance(gf, Stack_Generator_Frame)
            gf.gen = gen
            gf.saved_cf = saved_cf
            if gf.prev_gfp > cf.ffp:
                i = gf.prev_gfp + 1
            else:
                i = cf.ffp + 1
            j = cf.gfp
            assert i >= 0 and j >= i
            cf.stack_extend(cf.stack_get_slice(i, j))

            # At this point cf.stack looks like:
            #   [..., <gen obj 1>, ..., <gen obj n>, <generator frame>, <gen obj 1>, ...,
            #     <gen obj n>]
        
        if o is self.get_builtin(Builtins.BUILTIN_FAIL_OBJ):
            # Currently the failure of a function is signalled in the bytecode by returning the
            # FAIL object.
            o = None

        return o


    @jit.unroll_safe
    def decode_args(self, mand="", opt="", vargs=False, self_of=None):
        cf = self.cur_cf
        nargs = cf.nargs # Number of arguments passed
        
        mand = jit.promote_string(mand)
        opt = jit.promote_string(opt)
        self_of = jit.promote(self_of)

        if nargs < len(mand):
            if vargs:
                self.raise_helper("Parameters_Exception", [Builtins.Con_String(self, \
                  "Too few parameters (%d passed, but at least %d needed)." % (nargs, len(mand)))])
            else:
                self.raise_helper("Parameters_Exception", [Builtins.Con_String(self, \
                  "Too few parameters (%d passed, but %d needed)." % (nargs, len(mand)))])
        elif nargs > (len(mand) + len(opt)) and not vargs:
            raise Exception("XXX")

        if nargs == 0:
            if vargs:
                return (None, [])
            else:
                return (None, None)
        
        nrmp = [None] * (len(mand) + len(opt)) # Normal params
        i = 0
        while i < (len(mand) + len(opt)):
            if i >= nargs:
                for j in range(i, nargs):
                    nrmp[j] = None
                break

            if i < len(mand):
                t = mand[i]
            else:
                t = opt[i - len(mand)]
        
            o = cf.stack_get(cf.stackpe - nargs + i)
            
            if t == "!":
                assert self_of is not None
                if not isinstance(o, self_of):
                    raise Exception("XXX")
                nrmp[i] = o
                i += 1
                continue
            
            if t >= "a":
                if o is self.get_builtin(Builtins.BUILTIN_NULL_OBJ):
                    nrmp[i] = None
                    i += 1
                    continue
                t = chr(ord("A") + ord(t) - ord("a"))
        
            if t == "O":
                nrmp[i] = o
            else:
                if t == "C":
                    Builtins.type_check_class(self, o)
                elif t == "D":
                    Builtins.type_check_dict(self, o)
                elif t == "E":
                    Builtins.type_check_exception(self, o)
                elif t == "F":
                    Builtins.type_check_func(self, o)
                elif t == "I":
                    Builtins.type_check_int(self, o)
                elif t == "L":
                    Builtins.type_check_list(self, o)
                elif t == "M":
                    Builtins.type_check_module(self, o)
                elif t == "N":
                    Builtins.type_check_number(self, o)
                elif t == "S":
                    Builtins.type_check_string(self, o)
                elif t == "W":
                    Builtins.type_check_set(self, o)
                else:
                    print t
                    raise Exception("XXX")
                nrmp[i] = o
            
            i += 1

        if vargs:
            vap = [None] * (nargs - i)
            for j in range(i, nargs):
                vap[j - i] = cf.stack_get(cf.stackpe - nargs + j)
        else:
            vap = None

        cf.stack_del_from(cf.stackpe - nargs)
        
        return (nrmp, vap)


    def get_funcs_mod(self):
        cf = self.cur_cf
        return cf.pc.mod


    def get_mod_and_bc_off(self, i):
        cf = self.cur_cf
        while i >= 0:
            cf = cf.parent
            i -= 1
        mod = cf.pc.mod
        if mod.is_bc:
            return mod, cf.bc_off
        return mod, -1


    def raise_(self, ex):
        ex = Builtins.type_check_exception(self, ex)
        if ex.call_chain is None:
            cc = [] # Call chain
            cf = self.cur_cf
            while cf is not None:
                cc.append((cf.pc, cf.func, cf.bc_off))
                cf = cf.parent
            ex.call_chain = cc
        raise Con_Raise_Exception(ex)


    def raise_helper(self, ex_name, args=None):
        if args is None:
            args = []

        ex_mod = self.get_builtin(Builtins.BUILTIN_EXCEPTIONS_MODULE)
        assert isinstance(ex_mod, Builtins.Con_Module)
        ex = self.get_slot_apply(ex_mod.get_defn(self, ex_name), "new", args)
        self.raise_(ex)


    ################################################################################################
    # The interepreter
    #

    def execute_proc(self, cf):
        pc = cf.pc
        if isinstance(pc, Py_PC):
            f = pc.f(self)
            if isinstance(f, Class_Con_Proc):
                try:
                    o = f.next()
                    assert o is not None
                    cf.returned = True
                    return o
                except Con_Raise_Exception, e:
                    if cf.xfp == -1:
                        # There is no exception handler, so kill this continuation frame and propagate
                        # the exception
                        self._remove_continuation_frame()
                        raise
                    raise Exception("XXX")
            assert isinstance(f, Class_Con_Gen)
            try:
                o = f.next()
                assert o is not None
            except StopIteration:
                cf.returned = True
                return
            except Con_Raise_Exception, e:
                if cf.xfp == -1:
                    # There is no exception handler, so kill this continuation frame and propagate
                    # the exception
                    self._remove_continuation_frame()
                    raise
                raise Exception("XXX")
            assert not cf.returned or o is not None
            return o
        else:
            assert isinstance(pc, BC_PC)
            cf.bc_off = pc.off
            return self.bc_loop(cf)


    def execute_gen(self, cf):
        pc = cf.pc
        if isinstance(pc, Py_PC):
            f = pc.f(self)
            if isinstance(f, Class_Con_Proc):
                try:
                    o = f.next()
                    assert o is not None
                    cf.returned = True
                    yield o
                except Con_Raise_Exception, e:
                    if cf.xfp == -1:
                        # There is no exception handler, so kill this continuation frame and propagate
                        # the exception
                        self._remove_continuation_frame()
                        raise
                    raise Exception("XXX")
            assert isinstance(f, Class_Con_Gen)
            while 1:
                assert not cf.returned
                try:
                    o = f.next()
                    assert o is not None
                except StopIteration:
                    cf.returned = True
                    return
                except Con_Raise_Exception, e:
                    if cf.xfp == -1:
                        # There is no exception handler, so kill this continuation frame and propagate
                        # the exception
                        self._remove_continuation_frame()
                        raise
                    raise Exception("XXX")
                assert not cf.returned or o is not None
                yield o
        else:
            assert isinstance(pc, BC_PC)
            cf.bc_off = pc.off
            while 1:
                assert not cf.returned
                yield self.bc_loop(cf)


    def bc_loop(self, cf):
        pc = cf.pc
        mod_bc = pc.mod.bc
        prev_bc_off = -1
        while 1:
            bc_off = cf.bc_off
            if prev_bc_off != -1 and prev_bc_off > bc_off:
                jitdriver.can_enter_jit(bc_off=bc_off, mod_bc=mod_bc, cf=cf, prev_bc_off=prev_bc_off, pc=pc, self=self)
            jitdriver.jit_merge_point(bc_off=bc_off, mod_bc=mod_bc, cf=cf, prev_bc_off=prev_bc_off, pc=pc, self=self)
            assert cf is self.cur_cf
            prev_bc_off = bc_off
            instr = Target.read_word(mod_bc, bc_off)
            it = Target.get_instr(instr)

            try:
                #x = cf.stackpe; assert x >= 0; print "%s %s %d [stackpe:%d ffp:%d gfp:%d xfp:%d]" % (Target.INSTR_NAMES[instr & 0xFF], str(cf.stack[:x]), bc_off, cf.stackpe, cf.ffp, cf.gfp, cf.xfp)
                if it == Target.CON_INSTR_EXBI:
                    self._instr_exbi(instr, cf)
                elif it == Target.CON_INSTR_VAR_LOOKUP:
                    self._instr_var_lookup(instr, cf)
                elif it == Target.CON_INSTR_VAR_ASSIGN:
                    self._instr_var_assign(instr, cf)
                elif it == Target.CON_INSTR_ADD_FAILURE_FRAME:
                    self._instr_add_failure_frame(instr, cf)
                elif it == Target.CON_INSTR_ADD_FAIL_UP_FRAME:
                    self._instr_add_fail_up_frame(instr, cf)
                elif it == Target.CON_INSTR_REMOVE_FAILURE_FRAME:
                    self._instr_remove_failure_frame(instr, cf)
                elif it == Target.CON_INSTR_IS_ASSIGNED:
                    self._instr_is_assigned(instr, cf)
                elif it == Target.CON_INSTR_IS:
                    self._instr_is(instr, cf)
                elif it == Target.CON_INSTR_FAIL_NOW:
                    self._instr_fail_now(instr, cf)
                elif it == Target.CON_INSTR_POP:
                    self._instr_pop(instr, cf)
                elif it == Target.CON_INSTR_LIST:
                    self._instr_list(instr, cf)
                elif it == Target.CON_INSTR_SLOT_LOOKUP:
                    self._instr_slot_lookup(instr, cf)
                elif it == Target.CON_INSTR_APPLY:
                    self._instr_apply(instr, cf)
                elif it == Target.CON_INSTR_FUNC_DEFN:
                    self._instr_func_defn(instr, cf)
                elif it == Target.CON_INSTR_RETURN:
                    cf.returned = True
                    return cf.stack_pop()
                elif it == Target.CON_INSTR_BRANCH:
                    self._instr_branch(instr, cf)
                elif it == Target.CON_INSTR_YIELD:
                    cf.bc_off += Target.INTSIZE
                    return cf.stack_get(cf.stackpe - 1)
                elif it == Target.CON_INSTR_IMPORT:
                    self._instr_import(instr, cf)
                elif it == Target.CON_INSTR_DICT:
                    self._instr_dict(instr, cf)
                elif it == Target.CON_INSTR_DUP:
                    self._instr_dup(instr, cf)
                elif it == Target.CON_INSTR_PULL:
                    self._instr_pull(instr, cf)
                elif it == Target.CON_INSTR_BUILTIN_LOOKUP:
                    self._instr_builtin_lookup(instr, cf)
                elif it == Target.CON_INSTR_ASSIGN_SLOT:
                    self._instr_assign_slot(instr, cf)
                elif it == Target.CON_INSTR_EYIELD:
                    self._instr_eyield(instr, cf)
                elif it == Target.CON_INSTR_ADD_EXCEPTION_FRAME:
                    self._instr_add_exception_frame(instr, cf)
                elif it == Target.CON_INSTR_REMOVE_EXCEPTION_FRAME:
                    self._instr_remove_exception_frame(instr, cf)
                elif it == Target.CON_INSTR_RAISE:
                    self._instr_raise(instr, cf)
                elif it == Target.CON_INSTR_UNPACK_ARGS:
                    self._instr_unpack_args(instr, cf)
                elif it == Target.CON_INSTR_SET:
                    self._instr_set(instr, cf)
                elif it == Target.CON_INSTR_CONST_GET:
                    self._instr_const_get(instr, cf)
                elif it == Target.CON_INSTR_PRE_SLOT_LOOKUP_APPLY:
                    # In the C Converge VM, this instruction is used to avoid a very expensive path
                    # through the VM; it's currently unclear whether this VM will suffer from the
                    # same problem. Until we are more sure, we simply use the normal slot lookup
                    # function, which has the correct semantics, but may perhaps not be fully
                    # optimised.
                    self._instr_slot_lookup(instr, cf)
                elif it == Target.CON_INSTR_UNPACK_ASSIGN:
                    self._instr_unpack_assign(instr, cf)
                elif it == Target.CON_INSTR_BRANCH_IF_NOT_FAIL:
                    self._instr_branch_if_not_fail(instr, cf)
                elif it == Target.CON_INSTR_BRANCH_IF_FAIL:
                    self._instr_branch_if_fail(instr, cf)
                elif it == Target.CON_INSTR_EQ or it == Target.CON_INSTR_LE \
                  or it == Target.CON_INSTR_NEQ or it == Target.CON_INSTR_LE_EQ \
                  or it == Target.CON_INSTR_GR_EQ or it == Target.CON_INSTR_GT:
                    self._instr_cmp(instr, cf)
                elif it == Target.CON_INSTR_ADD or it == Target.CON_INSTR_SUBTRACT:
                    self._instr_calc(instr, cf)
                elif it == Target.CON_INSTR_MODULE_LOOKUP:
                    self._instr_module_lookup(instr, cf)
                else:
                    #print it, cf.stack
                    raise Exception("XXX")
            except Con_Raise_Exception, e:
                # An exception has been raised and is working its way up the call chain. Each bc_loop
                # catches the Con_Raise_Exception and either a) kills its continuation and passes the
                # exception up a level b) deals with it.
                if cf.xfp == -1:
                    # There is no exception handler, so kill this continuation frame and propagate
                    # the exception
                    self._remove_continuation_frame()
                    raise
                # We have an exception handler, so deal with it.
                ef = cf.stack_get(cf.xfp)
                assert isinstance(ef, Stack_Exception_Frame)
                self._remove_exception_frame(cf)
                cf.stack_push(e.ex_obj)
                cf.bc_off = ef.bc_off


    def _instr_exbi(self, instr, cf):
        class_ = Builtins.type_check_class(self, cf.stack_pop())
        bind_o = cf.stack_pop()
        nm_start, nm_size = Target.unpack_exbi(instr)
        nm = Target.extract_str(cf.pc.mod.bc, nm_start + cf.bc_off, nm_size)
        pa = Builtins.Con_Partial_Application(self, class_.get_field(self, nm), [bind_o])
        cf.stack_push(pa)
        cf.bc_off += Target.align(nm_start + nm_size)


    @jit.unroll_safe
    def _instr_var_lookup(self, instr, cf):
        closure_off, var_num = Target.unpack_var_lookup(instr)
        closure = cf.closure
        while closure_off > 0:
            closure = closure.parent
            closure_off -= 1
        v = closure.vars[var_num]
        if not v:
            self.raise_helper("Unassigned_Var_Exception")
        cf.stack_push(v)
        cf.bc_off += Target.INTSIZE


    @jit.unroll_safe
    def _instr_var_assign(self, instr, cf):
        closure_off, var_num = Target.unpack_var_assign(instr)
        closure = cf.closure
        while closure_off > 0:
            closure = closure.parent
            closure_off -= 1
        closure.vars[var_num] = cf.stack_get(cf.stackpe - 1)
        cf.bc_off += Target.INTSIZE


    def _instr_add_failure_frame(self, instr, cf):
        off = Target.unpack_add_failure_frame(instr)
        self._add_failure_frame(cf, False, cf.bc_off + off)
        cf.bc_off += Target.INTSIZE


    def _instr_add_fail_up_frame(self, instr, cf):
        self._add_failure_frame(cf, True)
        cf.bc_off += Target.INTSIZE


    def _instr_remove_failure_frame(self, instr, cf):
        self._remove_failure_frame(cf)
        cf.bc_off += Target.INTSIZE


    @jit.unroll_safe
    def _instr_is_assigned(self, instr, cf):
        closure_off, var_num = Target.unpack_var_lookup(instr)
        closure = cf.closure
        while closure_off > 0:
            closure = closure.parent
            closure_off -= 1
        v = closure.vars[var_num]
        if closure.vars[var_num] is not None:
            pc = cf.pc
            assert isinstance(pc, BC_PC)
            mod_bc = pc.mod.bc
            instr2 = Target.read_word(mod_bc, cf.bc_off + Target.INTSIZE)
            cf.bc_off += Target.unpack_is_assigned(instr2)
        else:
            cf.bc_off += Target.INTSIZE + Target.INTSIZE


    def _instr_is(self, instr, cf):
        o1 = cf.stack_pop()
        o2 = cf.stack_pop()
        if not o1.is_(o2):
            self._fail_now(cf)
            return
        cf.stack_push(o2)
        cf.bc_off += Target.INTSIZE


    def _instr_pop(self, instr, cf):
        cf.stack_pop()
        cf.bc_off += Target.INTSIZE


    def _instr_list(self, instr, cf):
        ne = Target.unpack_list(instr)
        l = cf.stack_get_slice_del(cf.stackpe - ne)
        cf.stack_push(Builtins.Con_List(self, l))
        cf.bc_off += Target.INTSIZE


    def _instr_slot_lookup(self, instr, cf):
        o = cf.stack_pop()
        nm_start, nm_size = Target.unpack_slot_lookup(instr)
        nm = Target.extract_str(cf.pc.mod.bc, nm_start + cf.bc_off, nm_size)
        cf.stack_push(o.get_slot(self, nm))
        cf.bc_off += Target.align(nm_start + nm_size)


    @jit.unroll_safe
    def _instr_apply(self, instr, cf):
        ff = cf.stack_get(cf.ffp)
        assert isinstance(ff, Stack_Failure_Frame)
        num_args = Target.unpack_apply(instr)
        fp = cf.stackpe - num_args - 1
        func = cf.stack_get(fp)

        if isinstance(func, Builtins.Con_Partial_Application):
            new_cf = self._add_continuation_frame(func.f, num_args + 1)
            new_cf.stack_extend(func.args)
            i = 1
        else:
            new_cf = self._add_continuation_frame(func, num_args)
            i = 0

        for j in range(0, num_args):
            k = i + num_args - j - 1
            assert k >= 0
            new_cf.stack[k] = cf.stack_pop()
        new_cf.stackpe = i + num_args

        if ff.is_fail_up:
            gf = Stack_Generator_Frame(cf.gfp, cf.bc_off + Target.INTSIZE)
            cf.stack_set(fp, gf)
            cf.gfp = fp
            o = self.apply_pump()
        else:
            cf.stack_pop() # Function pointer
            o = self.execute_proc(new_cf)
            self._remove_continuation_frame()
            
            if o is self.get_builtin(Builtins.BUILTIN_FAIL_OBJ):
                o = None

        if o is None:
            self._fail_now(cf)
            return
        cf.stack_push(o)
        cf.bc_off += Target.INTSIZE


    def _instr_fail_now(self, instr, cf):
        self._fail_now(cf)


    def _instr_func_defn(self, instr, cf):
        is_bound, max_stack_size = Target.unpack_func_defn(instr)
        np_o = cf.stack_pop()
        assert isinstance(np_o, Builtins.Con_Int)
        nv_o = cf.stack_pop()
        assert isinstance(nv_o, Builtins.Con_Int)
        name = cf.stack_pop()
        new_pc = BC_PC(cf.pc.mod, cf.bc_off + 2 * Target.INTSIZE)
        container = cf.func.get_slot(self, "container")
        f = Builtins.Con_Func(self, name, is_bound, new_pc, max_stack_size, np_o.v, nv_o.v, \
          container, cf.closure)
        cf.stack_push(f)
        cf.bc_off += Target.INTSIZE


    def _instr_branch(self, instr, cf):
        cf.bc_off += Target.unpack_branch(instr)


    def _instr_import(self, instr, cf):
        mod = self.get_mod(cf.pc.mod.imps[Target.unpack_import(instr)])
        mod.import_(self)
        cf.stack_push(mod)
        cf.bc_off += Target.INTSIZE


    def _instr_dict(self, instr, cf):
        ne = Target.unpack_dict(instr)
        l = cf.stack_get_slice_del(cf.stackpe - ne * 2)
        cf.stack_push(Builtins.Con_Dict(self, l))
        cf.bc_off += Target.INTSIZE


    def _instr_dup(self, instr, cf):
        cf.stack_push(cf.stack_get(cf.stackpe - 1))
        cf.bc_off += Target.INTSIZE


    def _instr_pull(self, instr, cf):
        i = Target.unpack_pull(instr)
        cf.stack_push(cf.stack_pop_n(i))
        cf.bc_off += Target.INTSIZE


    def _instr_builtin_lookup(self, instr, cf):
        bl = Target.unpack_builtin_lookup(instr)
        cf.stack_push(self.get_builtin(bl))
        cf.bc_off += Target.INTSIZE


    def _instr_assign_slot(self, instr, cf):
        o = cf.stack_pop()
        v = cf.stack_get(cf.stackpe - 1)
        nm_start, nm_size = Target.unpack_assign_slot(instr)
        nm = Target.extract_str(cf.pc.mod.bc, nm_start + cf.bc_off, nm_size)
        o.set_slot(self, nm, v)
        cf.bc_off += Target.align(nm_start + nm_size)


    def _instr_eyield(self, instr, cf):
        o = cf.stack_pop()
        is_fail_up, resume_bc_off = self._read_failure_frame(cf)
        self._remove_failure_frame(cf)
        prev_gfp = cf.gfp
        egf = Stack_Generator_EYield_Frame(prev_gfp, resume_bc_off)
        cf.gfp = cf.stackpe
        cf.stack_push(egf)
        # At this point the Con_Stack looks like:
        #   [..., <gen obj 1>, ..., <gen obj n>, <eyield frame>]
        gen_objs_s = prev_gfp + 1 # start of generator objects
        if cf.ffp > gen_objs_s:
            gen_objs_s = cf.ffp + 1
        gen_objs_e = cf.stackpe - 1
        assert gen_objs_s >= 0
        assert gen_objs_e >= gen_objs_s
        cf.stack_extend(cf.stack_get_slice(gen_objs_s, gen_objs_e))
        cf.stack_push(o)
        cf.bc_off += Target.INTSIZE


    def _instr_add_exception_frame(self, instr, cf):
        j = Target.unpack_add_exception_frame(instr)
        self._add_exception_frame(cf, cf.bc_off + j)
        cf.bc_off += Target.INTSIZE


    def _instr_remove_exception_frame(self, instr, cf):
        self._remove_exception_frame(cf)
        cf.bc_off += Target.INTSIZE


    def _instr_raise(self, instr, cf):
        self.raise_(cf.stack_pop())


    @jit.unroll_safe
    def _instr_unpack_args(self, instr, cf):
        num_fargs, has_vargs = Target.unpack_unpack_args(instr)
        num_fargs = jit.promote(num_fargs)
        has_vargs = jit.promote(has_vargs)
        if not has_vargs:
            nargs = jit.promote(cf.nargs)
        else:
            nargs = cf.nargs
        if nargs > num_fargs and not has_vargs:
            msg = "Too many parameters (%d passed, but a maximum of %d allowed)." % \
              (nargs, num_fargs)
            self.raise_helper("Parameters_Exception", [Builtins.Con_String(self, msg)])

        if num_fargs > 0:
            arg_offset = cf.bc_off + Target.INTSIZE + num_fargs * Target.INTSIZE
            for i in range(num_fargs - 1, -1, -1):
                arg_offset -= Target.INTSIZE
                arg_info = Target.read_word(cf.pc.mod.bc, arg_offset)
                if i >= nargs:
                    if not Target.unpack_unpack_args_is_mandatory(arg_info):
                        msg = "No value passed for parameter %d." % (i + 1)
                        self.raise_helper("Parameters_Exception", [Builtins.Con_String(self, msg)])
                else:
                    if nargs > num_fargs:
                        o = cf.stack_pop_n(nargs - num_fargs)
                    else:
                        o = cf.stack_pop()
                    assert isinstance(o, Builtins.Con_Object)
                    cf.closure.vars[Target.unpack_unpack_args_arg_num(arg_info)] = o

        if has_vargs:
            arg_offset = cf.bc_off + Target.INTSIZE + num_fargs * Target.INTSIZE
            arg_info = Target.read_word(cf.pc.mod.bc, arg_offset)
            if nargs <= num_fargs:
                l = []
            else:
                j = cf.stackpe
                i = j - (nargs - num_fargs)
                assert i >= 0 and j >= 0
                l = cf.stack_get_slice(i, j)
                cf.stackpe = i + 1
            cf.closure.vars[Target.unpack_unpack_args_arg_num(arg_info)] = Builtins.Con_List(self, l)
            cf.bc_off += Target.INTSIZE + (num_fargs + 1) * Target.INTSIZE
        else:
            cf.bc_off += Target.INTSIZE + num_fargs * Target.INTSIZE


    def _instr_set(self, instr, cf):
        ne = Target.unpack_set(instr)
        l = cf.stack_get_slice_del(cf.stackpe - ne)
        cf.stack_push(Builtins.Con_Set(self, l))
        cf.bc_off += Target.INTSIZE


    def _instr_const_get(self, instr, cf):
        const_num = Target.unpack_constant_get(instr)
        cf.stack_push(cf.pc.mod.get_const(self, const_num))
        cf.bc_off += Target.INTSIZE


    @jit.unroll_safe
    def _instr_unpack_assign(self, instr, cf):
        o = cf.stack_get(cf.stackpe - 1)
        o = Builtins.type_check_list(self, o)
        ne = len(o.l)
        if ne != Target.unpack_unpack_assign(instr):
            self.raise_helper("Unpack_Exception", \
              [Builtins.Con_Int(self, Target.unpack_unpack_assign(instr)), \
               Builtins.Con_Int(self, ne)])
        for i in range(ne - 1, -1, -1):
            cf.stack_push(o.l[i])
        cf.bc_off += Target.INTSIZE


    def _instr_branch_if_not_fail(self, instr, cf):
        if cf.stack_pop() is self.get_builtin(Builtins.BUILTIN_FAIL_OBJ):
            cf.bc_off += Target.INTSIZE
        else:
            j = Target.unpack_branch_if_not_fail(instr)
            cf.bc_off += j


    def _instr_branch_if_fail(self, instr, cf):
        if cf.stack_pop() is not self.get_builtin(Builtins.BUILTIN_FAIL_OBJ):
            cf.bc_off += Target.INTSIZE
        else:
            j = Target.unpack_branch_if_not_fail(instr)
            cf.bc_off += j


    def _instr_cmp(self, instr, cf):
        rhs = cf.stack_pop()
        lhs = cf.stack_pop()
        
        it = Target.get_instr(instr)
        if it == Target.CON_INSTR_EQ:
            r = lhs.eq(self, rhs)
        elif it == Target.CON_INSTR_LE:
            r = lhs.le(self, rhs)
        elif it == Target.CON_INSTR_NEQ:
            r = lhs.neq(self, rhs)
        elif it == Target.CON_INSTR_LE_EQ:
            r = lhs.le_eq(self, rhs)
        elif it == Target.CON_INSTR_GR_EQ:
            r = lhs.gr_eq(self, rhs)
        elif it == Target.CON_INSTR_GT:
            r = lhs.gt(self, rhs)
        else:
            raise Exception("XXX")
        
        if r:
            cf.stack_push(rhs)
            cf.bc_off += Target.INTSIZE
        else:
            self._fail_now(cf)


    def _instr_calc(self, instr, cf):
        rhs = cf.stack_pop()
        lhs = cf.stack_pop()
        
        it = Target.get_instr(instr)
        if it == Target.CON_INSTR_ADD:
            r = lhs.add(self, rhs)
        else:
            assert it == Target.CON_INSTR_SUBTRACT
            r = lhs.subtract(self, rhs)

        cf.stack_push(r)
        cf.bc_off += Target.INTSIZE


    def _instr_module_lookup(self, instr, cf):
        o = cf.stack_pop()
        nm_start, nm_size = Target.unpack_mod_lookup(instr)
        nm = Target.extract_str(cf.pc.mod.bc, cf.bc_off + nm_start, nm_size)
        if isinstance(o, Builtins.Con_Module):
            v = o.get_defn(self, nm)
        else:
            v = self.get_slot_apply(o, "get_defn", [Builtins.Con_String(self, nm)])
        cf.stack_push(v)
        cf.bc_off += Target.align(nm_start + nm_size)


    ################################################################################################
    # Frame operations
    #
    
    def _add_continuation_frame(self, func, nargs):
        if not isinstance(func, Builtins.Con_Func):
            self.raise_helper("Apply_Exception", [func])
        func = jit.promote(func) # XXX this will promote lambdas, which will be inefficient

        pc = func.pc
        if isinstance(pc, BC_PC):
            bc_off = pc.off
        else:
            bc_off = -1 

        closure = Closure(func.container_closure, func.num_vars)

        if func.max_stack_size > nargs:
            max_stack_size = func.max_stack_size
        elif nargs == 0:
            # We make the stack size at least 1 so that RPython functions have room for 1 generator
            # frame. If they need more than that, they'll have to be clever.
            max_stack_size = 1
        else:
            max_stack_size = nargs

        cf = Stack_Continuation_Frame(self.cur_cf, func, pc, max_stack_size, nargs, bc_off,
          closure)
        self.cur_cf = cf
        
        return cf


    def _remove_continuation_frame(self):
        self.cur_cf = self.cur_cf.parent


    def _remove_generator_frame(self, cf):
        gf = cf.stack_get(cf.gfp)
        cf.stack_del_from(cf.gfp)
        if isinstance(gf, Stack_Generator_Frame):
            cf.gfp = gf.prev_gfp
        else:
            assert isinstance(gf, Stack_Generator_EYield_Frame)
            cf.gfp = gf.prev_gfp


    def _add_failure_frame(self, cf, is_fail_up, new_off=-1):
        ff = Stack_Failure_Frame()

        ff.is_fail_up = is_fail_up
        ff.prev_ffp = cf.ffp
        ff.prev_gfp = cf.gfp
        ff.fail_to_off = new_off

        cf.gfp = -1
        cf.ffp = cf.stackpe
        cf.stack_push(ff)
        

    @jit.unroll_safe
    def _remove_failure_frame(self, cf):
        ffp = cf.ffp
        ff = cf.stack_get(ffp)
        assert isinstance(ff, Stack_Failure_Frame)
        cf.stack_del_from(ffp)
        cf.ffp = ff.prev_ffp
        cf.gfp = ff.prev_gfp


    def _read_failure_frame(self, cf):
        assert cf.ffp >= 0
        ff = cf.stack_get(cf.ffp)
        assert isinstance(ff, Stack_Failure_Frame)

        return (ff.is_fail_up, ff.fail_to_off)


    @jit.unroll_safe
    def _fail_now(self, cf):
        while 1:
            is_fail_up, fail_to_off = self._read_failure_frame(cf)
            if is_fail_up:
                if cf.gfp == -1:
                    self._remove_failure_frame(cf)
                    continue
                has_rg = False
                gf = cf.stack_get(cf.gfp)
                if isinstance(gf, Stack_Generator_EYield_Frame):
                    self._remove_generator_frame(cf)
                    cf.bc_off = gf.resume_bc_off
                    return
                else:
                    assert isinstance(gf, Stack_Generator_Frame)
                    o = self.apply_pump(True)
                    if o is not None:
                        cf = self.cur_cf
                        cf.stack_push(o)
                        cf.bc_off = gf.resume_bc_off
                        return
            else:
                cf.bc_off = fail_to_off
                self._remove_failure_frame(cf)
                return


    def _add_exception_frame(self, cf, bc_off):
        ef = Stack_Exception_Frame(bc_off, cf.ffp, cf.gfp, cf.xfp)
        cf.xfp = cf.stackpe
        cf.stack_push(ef)


    def _remove_exception_frame(self, cf):
        ef = cf.stack_get(cf.xfp)
        cf.stack_del_from(cf.xfp)
        assert isinstance(ef, Stack_Exception_Frame)
        cf.ffp = ef.prev_ffp
        cf.gfp = ef.prev_gfp
        cf.xfp = ef.prev_xfp



####################################################################################################
# Stack frame classes
#

class Stack_Continuation_Frame(Con_Thingy):
    __slots__ = ("parent", "stack", "stackpe", "func", "pc", "nargs", "bc_off", "closure", "ffp",
      "gfp", "xfp", "returned")
    _immutable_fields_ = ("parent", "stack", "ff_cache", "func", "closure", "pc", "nargs")
    _virtualizable_ = ("parent", "bc_off", "stack[*]", "closure", "stackpe", "ffp", "gfp")

    def __init__(self, parent, func, pc, max_stack_size, nargs, bc_off, closure):
        self = jit.hint(self, access_directly=True, fresh_virtualizable=True)
        self.parent = parent
        self.stack = [None] * max_stack_size
        debug.make_sure_not_resized(self.stack)
        self.func = func
        self.pc = pc
        self.nargs = nargs # Number of arguments passed to this continuation
        self.bc_off = bc_off # -1 for Py modules
        self.closure = closure
        self.returned = False

        # stackpe always points to the element *after* the end of the stack (this makes a lot of
        # stack-based operations quicker)
        self.stackpe = 0
        # ffp, gfp, and xfp all point *to* the frame they refer to
        self.ffp = self.gfp = self.xfp = -1


    def stack_get(self, i):
        assert i >= 0
        return self.stack[i]


    @jit.unroll_safe
    def stack_get_slice(self, i, j):
        assert i >= 0 and j >= i
        l = [None] * (j - i)
        a = 0
        for k in range(i, j):
            l[a] = self.stack[k]
            a += 1
        return l


    @jit.unroll_safe
    def stack_get_slice_del(self, i):
        assert i >= 0
        l = [None] * (self.stackpe - i)
        a = 0
        for k in range(i, self.stackpe):
            l[a] = self.stack[k]
            self.stack[k] = None
            a += 1
        self.stackpe = i
        return l


    def stack_set(self, i, o):
        assert i >= 0
        self.stack[i] = o


    @jit.unroll_safe
    def stack_extend(self, l):
        for x in l:
            self.stack_set(self.stackpe, x)
            self.stackpe += 1


    def stack_push(self, x):
        assert self.stackpe < len(self.stack)
        self.stack_set(self.stackpe, x)
        self.stackpe += 1


    def stack_pop(self):
        assert self.stackpe > 0
        self.stackpe -= 1
        o = self.stack_get(self.stackpe)
        self.stack_set(self.stackpe, None)
        return o


    # Pop an item n items from the end of self.stack.

    @jit.unroll_safe
    def stack_pop_n(self, n):
        assert n < self.stackpe
        i = self.stackpe - 1 - n
        o = self.stack_get(i)
        # Shuffle the stack down
        self.stackpe -= 1
        for j in range(i, self.stackpe):
            self.stack_set(j, self.stack_get(j + 1))
        self.stack_set(self.stackpe, None)
        # If the frame pointers come after the popped item, they need to be rewritten
        if self.ffp > i:
            self.ffp -= 1
        if self.gfp > i:
            self.gfp -= 1
        if self.xfp > i:
            self.xfp -= 1

        return o


    @jit.unroll_safe
    def stack_del_from(self, i):
        for j in range(i, self.stackpe):
            self.stack_set(j, None)
        self.stackpe = i



class Stack_Failure_Frame(Con_Thingy):
    __slots__ = ("is_fail_up", "prev_ffp", "prev_gfp", "fail_to_off")
    # Because failure frames can be reused, they have no immutable fields.

    def __repr__(self):
        if self.is_fail_up:
            return "<Fail up frame>"
        else:
            return "<Failure frame>"


class Stack_Generator_Frame(Con_Thingy):
    __slots__ = ("prev_gfp", "resume_bc_off", "returned", "gen", "saved_cf")
    _immutable_fields_ = ("prev_gfp", "resume_bc_off")
    
    def __init__(self, prev_gfp, resume_bc_off):
        self.prev_gfp = prev_gfp
        self.resume_bc_off = resume_bc_off
        self.returned = False


class Stack_Generator_EYield_Frame(Con_Thingy):
    __slots__ = ("prev_gfp", "resume_bc_off")
    _immutable_fields_ = ("prev_gfp", "resume_bc_off")
    
    def __init__(self, prev_gfp, resume_bc_off):
        self.prev_gfp = prev_gfp
        self.resume_bc_off = resume_bc_off


class Stack_Exception_Frame(Con_Thingy):
    __slots__ = ("bc_off", "prev_ffp", "prev_gfp", "prev_xfp")
    _immutable_fields_ = ("bc_off", "prev_ffp", "prev_gfp", "prev_xfp")
    
    def __init__(self, bc_off, prev_ffp, prev_gfp, prev_xfp):
        self.bc_off = bc_off
        self.prev_ffp = prev_ffp
        self.prev_gfp = prev_gfp
        self.prev_xfp = prev_xfp



####################################################################################################
# Misc
#

class Closure:
    __slots__ = ("parent", "vars")
    _immutable_fields = ("parent", "vars")

    def __init__(self, parent, num_vars):
        self.parent = parent
        self.vars = [None] * num_vars
        debug.make_sure_not_resized(self.vars)


class Con_Raise_Exception(Exception):
    _immutable_ = True

    def __init__(self, ex_obj):
        self.ex_obj = ex_obj


global_vm = VM()

def new_vm(vm_path, argv):
    global_vm.init(vm_path, argv)
    return global_vm

########NEW FILE########
