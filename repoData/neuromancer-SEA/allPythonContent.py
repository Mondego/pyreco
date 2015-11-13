__FILENAME__ = SEA
#!/usr/bin/python2

"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

import sys
import argparse

from src.Prelude            import mkTrace
from src.Common             import getPathConditions
from src.JumpConditions     import getJumpConditions
from src.PathGeneration     import generatePaths
from src.Lifting            import mkPath, mkProgram

parser = argparse.ArgumentParser(description='Symbolic Exploit Assistant.')
parser.add_argument('trace_filename', metavar='trace', type=str,
                    help='a sequence of REIL instruction in a trace')

parser.add_argument('-first', dest='first', action='store', type=str,
                   default=str(0), help='first instruction to process')

parser.add_argument('-last', dest='last', action='store', type=str,
                   default=str(sys.maxint-1), help='last instruction to process')

parser.add_argument('-type', dest='type', action='store', type=str,
                   default="debug", help='exploit type')

parser.add_argument('-address', dest='address', action='store', type=str,
                   default=None, help='which address to jump in jump mode')

parser.add_argument('iconditions', metavar='operator,value', type=str, nargs='*',
                   help='initial conditions for the trace')

args = parser.parse_args()

mode  = args.type
valid_modes = ["jump", "path", "debug", "selection", "generation"]

if not (mode in valid_modes):
  print "\""+mode+"\" is an invalid type of operation for SEA"
  exit(1)  

if (mode == 'debug'):
  
  first = int(args.first)
  last  = int(args.last) 
  path = mkPath(args.trace_filename, first, last)
  trace = mkTrace(path, args.iconditions, debug = True)
  
if (mode == "jump"):
  
  first = int(args.first)
  last  = int(args.last) 
  
  address = args.address
  path = mkPath(args.trace_filename, first, last)

  trace = mkTrace(path, args.iconditions, debug = True)

  if (address == None):
    print "An address to jump to should be specified!"
  else:
    (fvars, sol) = getJumpConditions(trace, address)

    if sol <> None:
      print "SAT!"
      for var in fvars:
        print "sol["+str(var)+"] =", sol[var]
    else:
      print "UNSAT!"


elif (mode == 'path'): 

  first = int(args.first)
  last  = int(args.last) 
  
  address = args.address
  path = mkPath(args.trace_filename, first, last)
  trace = mkTrace(path, args.iconditions, debug = True)
  fvars, sol = getPathConditions(trace, False)

  if sol <> None:
    print "SAT!"
    for var in fvars:
      print "sol["+str(var)+"] =", sol[var]
  else:
    print "UNSAT!"
      
elif (mode == 'generation'):
  program = mkProgram(args.trace_filename) 
  generatePaths(program,args.first, args.last, 2000)
    


########NEW FILE########
__FILENAME__ = Allocation
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

class Allocation:
  buffers  = dict()
  dfrees   = []
  overflows= [] 
  uaf      = []
  
  def __init__(self):
    self.buffers = dict()
    
  def alloc(self, address, counter, size):
    self.buffers["h.0x"+str(address)+"."+str(counter)] = size
    
  def free(self, buf, counter):
    if (buf in self.buffers):
      del self.buffers[buf]
    else:
      self.dfrees.append((buf, counter))
      
  def check(self, memaccess, counter):
    
    mem_source = memaccess["source"]
    mem_offset = memaccess["offset"]
    
    if ("h." in mem_source):
      if (not (mem_source in self.buffers.keys())):
        self.uaf.append((mem_source, counter))
      else:
        size = self.buffers[mem_source]
        
        if (mem_offset >= size):
          self.overflows.append((mem_source, mem_offset, counter))
  
  def report(self):
    
    if (len(self.buffers) > 0):
      print "Live buffers:"
      print self.buffers
    #else: 
    #  print "No live buffers."
      
    if (self.overflows <> []):
      print "Heap overflow detected!"
      for (s,o,c) in self.overflows:
        print s, "("+str(o)+")", "at", c 

    if (self.uaf <> []):
      print "Use-after-free detected!"
      for (s,c) in self.uaf:
        print s, "at", c
        
    if (self.dfrees <> []):
      print "Double frees detected!"
      for (s,c) in self.dfrees:
        print s, "at", c

########NEW FILE########
__FILENAME__ = Callstack
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""


from core import *

from SSA import SSA
from Condition   import *
from SMT         import SMT

def getValueFromCode(inss, initial_values, op):
  assert(len(inss) > 0)
  
  # code should be copied and reversed
  inss.reverse()
  
  ssa = SSA()
  smt_conds  = SMT()
 
  # we will track op
  mvars = set([op])    
  ssa.getMap(mvars, set(), set())

  for ins in inss:

    #counter = ins.getCounter() 
    ins_write_vars = set(ins.getWriteVarOperands())
    ins_read_vars = set(ins.getReadVarOperands())

    if len(ins_write_vars.intersection(mvars)) > 0: 
      
      ssa_map = ssa.getMap(ins_read_vars.difference(mvars), ins_write_vars, ins_read_vars.intersection(mvars))

      cons = conds.get(ins.instruction, Condition)
      condition = cons(ins, ssa_map)
     
      mvars = mvars.difference(ins_write_vars) 
      mvars = ins_read_vars.union(mvars)
      mvars = set(filter(lambda o: o.name <> "ebp", mvars))
   
      smt_conds.add(condition.getEq())
      
  for iop in initial_values.keys():
    if not (iop in ssa):
      del initial_values[iop]
    
  ssa_map = ssa.getMap(set(), set(), set(initial_values.keys()))
  eq = Eq(None, None)
    
  for iop in initial_values:
    smt_conds.add(eq.getEq(ssa_map[iop.name],initial_values[iop]))
    
  #op.name = op.name+"_0"
  smt_conds.solve()
  
  renamed_name = op.getName()+"_0"
  renamed_size = op.getSizeInBits()
  renamed_offset = op.getOffset()
  renamed_op = op.__class__(renamed_name, renamed_size, renamed_offset)
    
  return smt_conds.getValue(renamed_op)


class Callstack:
  def __init__(self, reil_code):
    
    # The first instruction should be a call
    self.callstack = [None]
    self.stack_diff = []
    
    self.index = 0
    
    # aditional information need to compute the callstack
    self.calls = [None]
    self.esp_diffs = [None]
    self.reil_code = reil_code
    reil_size = len(reil_code)
    start = 0  
  
    for (end,ins) in enumerate(self.reil_code):
      if (ins.isCall() and ins.called_function == None) or ins.isRet():
        self.__getStackDiff__(ins, reil_code[start:end])
        start = end
        
    if (start <> reil_size-1):
      ins = reil_code[start]
      self.__getStackDiff__(ins, reil_code[start:reil_size-1])
      
    self.index = len(self.callstack) - 1
  
  def __str__(self):
    ret = ""
    for (addr, sdiff) in zip(self.callstack, self.stack_diff):
      if (addr <> None):
        ret = ret + " " + hex(addr) + "[" +str(sdiff)+"]"
    
    return ret
  
  def reset(self):
    self.index = 0
  
  def nextInstruction(self, ins):
    if (ins.isCall() and ins.called_function == None) or ins.isRet():
      self.index = self.index + 1
  
  
  def prevInstruction(self, ins):
    if (ins.isCall() and ins.called_function == None) or ins.isRet():
      self.index = self.index - 1
  
  def currentCall(self):
    return self.callstack[self.index]
    
  def currentStackDiff(self):
    return self.stack_diff[self.index]
  
  def currentCounter(self):
    return 1 # TODO!
  
  def firstCall(self):
    return self.index == 1
  
  #def convertStackMemLoc(self, loc):
    #self.index = self.index - 1
    
    #if self.index == 1:
      #index = (loc.index)+self.currentStackDiff()-4
    #else:
      #index = (loc.index)+self.currentStackDiff()
    
    #new_loc = MemLoc(loc.name,index)  
    
    #einfo = dict()
    #einfo["source.name"] = self.currentCall()
    #new_loc.type = Type(loc.type.name, loc.type.index, loc.type.getInfo())
    
    #print loc.type.getInfo()
    #assert(0)
    #new_loc.type = Type(loc.type.name, loc.type.index, loc.type.getInfo())
    
    ##mem_source =  "s."+hex(self.currentCall())+"."+str(self.currentCounter())
    ##if self.index == 1:
    ##  mem_offset = (op.mem_offset)+self.currentStackDiff()-4#+16
    ##else:
    ##  mem_offset = (op.mem_offset)+self.currentStackDiff()#+16
    ##name = mem_source+"@"+str(mem_offset)
    
    #self.index = self.index + 1
    #return new_loc
    
    #return Operand(name,"BYTE", mem_source, mem_offset)
  
  
  def convertStackMemOp(self, op):
    self.index = self.index - 1
    
    mem_source =  "s."+hex(self.currentCall())+"."+str(self.currentCounter())
    if self.index == 1:
      mem_offset = (op.mem_offset)+self.currentStackDiff()-4#+16
    else:
      mem_offset = (op.mem_offset)+self.currentStackDiff()#+16
    name = mem_source+"@"+str(mem_offset)
    
    self.index = self.index + 1
    
    return Operand(name,"BYTE", mem_source, mem_offset)
  
  def __getStackDiff__(self, ins, reil_code):
    addr = ins.address
    if ins.isCall():
      call = int(addr, 16)
      esp_diff = self.__getESPdifference__(reil_code, 0) 
        
      self.calls.append(call)
      self.callstack.append(call)
        
      self.stack_diff.append(esp_diff)
      self.esp_diffs.append(esp_diff)
      
    elif ins.isRet():
        
      if (reil_code[0].isCall()):
        self.stack_diff.append(self.__getESPdifference__(reil_code, 0))
      else:
        self.calls.pop()
        self.esp_diffs.pop()
          
        call = self.calls[-1]
        esp_diff = self.esp_diffs[-1]
          
        self.stack_diff.append(self.__getESPdifference__(reil_code, esp_diff)) 
        self.callstack.append(call)
    else:
      assert(False)
  
  def __getESPdifference__(self, reil_code, initial_esp):
    if len(reil_code) == 0:
      return initial_esp
    esp_op = RegOp("esp","DWORD")
    initial_values = dict([ (esp_op, ImmOp(str(0), "DWORD"))])
    return getValueFromCode(reil_code, initial_values, esp_op)+ initial_esp

########NEW FILE########
__FILENAME__ = Common
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

from core        import *

from SSA         import SSA
from Function    import *
from Condition   import *
from SMT         import SMT, Solution
from Typing      import *

concatSet = lambda l: reduce(set.union, l, set())

def getValueFromCode(inss, callstack, initial_values, memory, op, debug = False):
  
  # Initialization
  
  # we reverse the code order
  inss.reverse()
  
  # we reset the used memory variables
  Memvars.reset()
  
  # we save the current callstack
  last_index = callstack.index  # TODO: create a better interface
  
  # we set the instruction counter
  #counter = len(inss)-1
  
  # ssa and smt objects
  ssa = SSA()
  smt_conds  = SMT()
  
  mvars = set()
  mlocs = set()
 
  if (op |iss| ImmOp or op |iss| AddrOp):
    return op.getValue()
  
  mvars.add(op)
  mlocs = set(op.getLocations())
  
  # we start without free variables
  fvars = set()
  
  ssa.getMap(mvars, set(), set())

  for ins in inss:
    
    counter = ins.getCounter()
    
    if debug:
      print str(counter) + ":", ins.instruction

    if memory.getAccess(counter) <> None:
      ins.setMemoryAccess(memory.getAccess(counter))
  
    ins_write_vars = set(ins.getWriteVarOperands())
    ins_read_vars = set(ins.getReadVarOperands())
    
    write_locs = concatSet(map(lambda op: set(op.getLocations()), ins.getWriteVarOperands()))
    read_locs  = concatSet(map(lambda op: set(op.getLocations()), ins.getReadVarOperands() ))
    
    if len(write_locs.intersection(mlocs)) > 0: 
    #if len(ins_write_vars.intersection(mvars)) > 0: 
      
      ssa_map = ssa.getMap(ins_read_vars.difference(mvars), ins_write_vars, ins_read_vars.intersection(mvars))

      cons = conds.get(ins.instruction, Condition)
      condition = cons(ins, ssa_map)
      
      mlocs = mlocs.difference(write_locs) 
      mlocs = read_locs.union(mlocs) 
       
      mvars = mvars.difference(ins_write_vars) 
      mvars = ins_read_vars.union(mvars)
   
      smt_conds.add(condition.getEq())

    
    # additional conditions
    mvars = addAditionalConditions(mvars, mlocs, ins, ssa, callstack, smt_conds)

    # we update the current call for next instruction
    callstack.prevInstruction(ins) 
    
  for v in mvars:
    if not (v in initial_values):
      print "#Warning__", str(v), "is free!" 
  
  #setInitialConditions(ssa, initial_values, smt_conds)
  smt_conds.solve(debug)
  
  renamed_name = op.getName()+"_0"
  renamed_size = op.getSizeInBits()
  renamed_offset = op.getOffset()
  renamed_op = op.__class__(renamed_name, renamed_size, renamed_offset)
    
  callstack.index = last_index  # TODO: create a better interface
  return smt_conds.getValue(renamed_op)

      
def getPathConditions(trace, debug = False):
  
  # Initialization
  inss = trace["code"]
  callstack = trace["callstack"]
  
  memory = trace["mem_access"]
  parameters = trace["func_parameters"]
 
  # we reverse the code order
  inss.reverse()
  #print inss[0]
  # we reset the used memory variables
  Memvars.reset()
  
  # we save the current callstack
  last_index = callstack.index  # TODO: create a better interface
  
  # ssa and smt objects
  ssa = SSA()
  smt_conds  = SMT()
  
  mvars = set()
  mlocs = set()

  for op in trace["final_conditions"]:
    mvars.add(op)
    mlocs = mlocs.union(op.getLocations())
  
  # we start without free variables
  fvars = set()
  
  ssa.getMap(mvars, set(), set())
  setInitialConditions(ssa, trace["final_conditions"],smt_conds)
  
  #for c in smt_conds:
  #  print c
  #assert(0)   

  for ins in inss:
    
    
    counter = ins.getCounter()
    func_cons = funcs.get(ins.called_function, Function)

    if memory.getAccess(counter) <> None:
      ins.setMemoryAccess(memory.getAccess(counter))

    ins.clearMemRegs() 
    func = func_cons(None, parameters.getParameters(counter))

    if debug:
      print "(%.4d)" % counter, ins
      for v in mvars:
        print v, v.getSizeInBytes(), "--",
      print ""
     
      for l in mlocs:
        print l, "--",
      print ""
  
    ins_write_vars = set(ins.getWriteVarOperands())
    ins_read_vars = set(ins.getReadVarOperands())
   
    func_write_vars = set(func.getWriteVarOperands())
    func_read_vars = set(func.getReadVarOperands())

    ins_write_locs = concatSet(map(lambda op: set(op.getLocations()), ins.getWriteVarOperands()))
    ins_read_locs  = concatSet(map(lambda op: set(op.getLocations()), ins.getReadVarOperands()))
    
    func_write_locs = concatSet(map(lambda op: set(op.getLocations()), func.getWriteVarOperands()))
    func_read_locs  = concatSet(map(lambda op: set(op.getLocations()), func.getReadVarOperands()))
    
    #if (func_write_vars <> set()):
    #  x =  func_write_vars.pop()
    #  print x, x.getLocations()
    #  assert(0)
    #print func, parameters.getParameters(counter), func_write_vars, func_write_locs 

    if (not ins.isCall()) and (ins.isJmp() or ins.isCJmp() or len(ins_write_locs.intersection(mlocs)) > 0): 
      
      ssa_map = ssa.getMap(ins_read_vars.difference(mvars), ins_write_vars, ins_read_vars.intersection(mvars))

      cons = conds.get(ins.instruction, Condition)
      condition = cons(ins, ssa_map)
      
      mlocs = mlocs.difference(ins_write_locs) 
      mlocs = ins_read_locs.union(mlocs) 
       
      mvars = mvars.difference(ins_write_vars) 
      mvars = ins_read_vars.union(mvars)
   
      smt_conds.add(condition.getEq())
      
    elif (len(func_write_locs.intersection(mlocs)) > 0):
      # TODO: clean-up here!
      #ssa_map = ssa.getMap(func_read_vars.difference(mvars), func_write_vars, func_read_vars.intersection(mvars))
        
      cons = conds.get(ins.called_function, Condition)
      condition = cons(func, None)
        
      c = condition.getEq(func_write_locs.intersection(mlocs))
      
      mlocs = mlocs.difference(func_write_locs) 
      mlocs = func_read_locs.union(mlocs) 
  
      mvars = mvars.difference(func_write_vars) 
      mvars = func_read_vars.union(mvars)

      smt_conds.add(c)
      #print c
      #assert(0)

    
    # additional conditions
    #mvars = addAditionalConditions(mvars, mlocs, ins, ssa, callstack, smt_conds)

    # we update the current call for next instruction
    callstack.prevInstruction(ins) 
  
  fvars = set()
  ssa_map = ssa.getMap(set(), set(), mvars)

  for var in mvars:
    #print v, "--",
    #if not (v in initial_values):
    print "#Warning__", str(var), "is free!" 
    
    if (var |iss| InputOp):
      fvars.add(var)
    elif var |iss| MemOp:
      f_op = var.copy()
      f_op.name = Memvars.read(var)
      fvars.add(f_op) 
    else:
      f_op = var.copy()
      f_op.name = f_op.name+"_0"
      fvars.add(f_op)
    #else:
      #fvars.add(ssa_map[str(var)])
      # perform SSA
      #assert(0)
  
  #setInitialConditions(ssa, initial_values, smt_conds)
  #smt_conds.solve(debug)
  
  callstack.index = last_index  # TODO: create a better interface
  smt_conds.write_smtlib_file("exp.smt2")  
  smt_conds.write_sol_file("exp.sol")
  smt_conds.solve(debug)  

  if (smt_conds.is_sat()):
    #smt_conds.solve(debug)
    return (fvars, Solution(smt_conds.m))
  else: # unsat :(
    return (set(), None)

########NEW FILE########
__FILENAME__ = Condition
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

import sys

try:

  sys.path.append("z3py/build/")
  import z3

except:
  sys.exit("You should run bootstrap.sh to download and compile z3 support") 

from core import *
from MemVars import Memvars

def mkArray(name):
  return z3.Array(name, z3.BitVecSort(16), z3.BitVecSort(8))

def mkByteList(op):
  locs = op.getLocations()
  
  if (len(locs) > 1):
    return map(lambda b: z3.BitVec(str(b),8), locs)
  else:
    return [z3.BitVec(str(locs[0]),8)]


def mkByteListVar(op):
  locs = op.getLocations()
  
  if (len(locs) > 1):
    return (map(lambda b: z3.BitVec(str(b),8), locs))
  else:
    return [z3.BitVec(str(locs[0]),8)]

def mkByteVar(op):
  locs = op.getLocations()
  
  if (len(locs) > 1):
    return z3.Concat(map(lambda b: z3.BitVec(str(b),8), locs))
  else:
    return z3.BitVec(str(locs[0]),8)

def mkByteListConst(imm):
  locs = imm.getLocations()
  
  if (len(locs) > 1):
    return (map(lambda b: z3.BitVecVal(str(b),8), locs))
  else:
    return [ z3.BitVecVal(str(locs[0]),8)]

#def mkByteConst(imm):
#  locs = imm.getLocations()
  
#  if (len(locs) > 1):
#    return z3.Concat(map(lambda b: z3.BitVecVal(str(b),8), locs))
#  else:
#    return z3.BitVecVal(str(locs[0]),8)

def mkConst(imm):
  return z3.BitVecVal(imm.getValue(),imm.size)

class Condition:

  def __apply_ssa(self, op):
    if op |iss| RegOp:
      return self.ssa_map[str(op)]
    return op

  def __init__(self, ins, ssa_map):
    self.ins = ins
    
    rreg = self.ins.getReadRegOperands()
    wreg = self.ins.getWriteRegOperands()
    
    self.read_operands = self.ins.getReadOperands()
    self.write_operands = self.ins.getWriteOperands()
    
    self.ssa_map = ssa_map    
    self.read_operands = map(lambda o: self.__apply_ssa(o), self.read_operands)
    self.write_operands = map(lambda o: self.__apply_ssa(o), self.write_operands)
  
  def getEq(self):
    assert(0)
    return []

  def getOperands(self, ops, concat = True):
   
    rops = [] 
    
    for op in ops:
      #print op
      if (op.isVar()):
        rops.append(mkByteVar(op))
      else:
        rops.append(mkConst(op))
    #for r in rops:
    #  print r, 

    return rops

class Call_Cond(Condition):
  def getEq(self):
    assert(0)
    return []
 
class  Jcc_Cond(Condition):
  def getEq(self):
    src = self.getOperands(self.read_operands)[0]
    
    if (self.ins.getBranchTaken() == "0"): # hack to know which branch was taken!
      return [(src == 0)] # False branch
    else: 
      return [(src <> 0)] # True branch
 
class  Str_Cond(Condition):
 def getEq(self):

   src = self.getOperands(self.read_operands)[0]
   dst = self.getOperands(self.write_operands)[0]
   
   return [(src == dst)]

class  Add_Cond(Condition):
 def getEq(self):

   src1,src2 = self.getOperands(self.read_operands)
   dst = self.getOperands(self.write_operands)[0]
   
   return [(src1 + src2 == dst)]


class  Sub_Cond(Condition):
 def getEq(self):
   
   src1,src2 = self.getOperands(self.read_operands)
   dst = self.getOperands(self.write_operands)[0]
   
   return [(src1 - src2 == dst)]


class  Mul_Cond(Condition):
 def getEq(self):
   
   src1,src2 = self.getOperands(self.read_operands)
   dst = self.getOperands(self.write_operands)[0]
   
   return [(src1 * src2 == dst)]

class  And_Cond(Condition):
 def getEq(self):

   src1,src2 = self.getOperands(self.read_operands)
   dst = self.getOperands(self.write_operands)[0]
   
   #print "src1:", src1
   #print "src2:", src2
   
   return [(src1 & src2 == dst)]

class  Or_Cond(Condition):
 def getEq(self):
  
   src1,src2 = self.getOperands(self.read_operands)
   dst = self.getOperands(self.write_operands)[0]
   
   return [(src1 | src2 == dst)]


class  Xor_Cond(Condition):
 def getEq(self):

   src1,src2 = self.getOperands(self.read_operands)
   dst = self.getOperands(self.write_operands)[0]
   
   return [(src1 ^ src2 == dst)]

class  Shift_Cond(Condition):
 def getEq(self):
   #print self.read_operands[1] 
   sdir = ""
   
   src1,src2 = self.getOperands(self.read_operands)
   dst = self.getOperands(self.write_operands)[0]
   n =  self.read_operands[1].getValue()

   if n > 0:
     sdir = "left"
   elif n < 0:
     sdir = "right"
     #self.read_operands[1].name = self.read_operands[1].name.replace("-","") #ugly hack!
   else:
     sdir = "null"
   
   #print self.read_operands[1].name
  

   #print sdir, src2.as_long()
   if sdir == "right": 
     return [(z3.Extract(self.write_operands[0].getSizeInBits()-1, 0,z3.LShR(src1,-n)) == dst)]
   elif sdir == "left":
     return [(z3.Extract(self.write_operands[0].getSizeInBits()-1, 0,(src1 << n)) == dst)]
   elif sdir == "null":
     return [(src1 == dst)]
   else:
     assert(False)

class  Bisz_Cond(Condition):
 def getEq(self):
   src = self.getOperands(self.read_operands)[0]
   dst = self.getOperands(self.write_operands)[0]
   
   return [z3.If(src == 0, dst == 1, dst == 0)]

class  Ldm_Cond(Condition):
  def getEq(self):
    
    conds = []
    
    src = self.ins.getReadMemOperands()[0]
    srcs = src.getLocations()
    
    dst = (self.write_operands)[0]
    if dst.isVar():
      dsts = mkByteListVar(dst)    
    else:
      dsts = mkByteListConst(dst)
    
    #endianness
    dsts.reverse()

    for (src,dst) in zip(srcs, dsts):
      sname = Memvars.read(src)
      array = mkArray(sname)
      conds.append(array[src.getIndex()] == dst)
    
    return conds
    
class  Stm_Cond(Condition):
  def getEq(self):
    
    src = self.read_operands[0]
    
    if src.isVar():
      srcs = mkByteListVar(src)    
    else:
      srcs = mkByteListConst(src)
    
    #endianness
    srcs.reverse()

    dst = self.write_operands[0]
    dsts = dst.getLocations()
    
    conds = []
    
    old_sname, new_sname = Memvars.write(dsts[0])

    #array = mkArray(old_sname)
    #new_array = mkArray(new_sname)

    old_array = mkArray(old_sname)
    array = mkArray(new_sname)

    for (src,dst) in zip(srcs, dsts):
      array = z3.Store(array, dst.getIndex(), src)
      
    conds = [(old_array == array)]

    return conds


## exploit conditions

#class  Write_with_stm(Condition):
#  def getEq(self, value, address):
#    op_val,op_addr = self.getOperands(self.read_operands)
#    print [op_val == value, op_addr == address]
#    return [op_val == value, op_addr == address]
  
# generic conditions  
  
class  Eq(Condition):
  def __init__(self, pins, ssa):
    pass
  def getEq(self, x, y):
    
    assert(x.getSizeInBytes() == y.getSizeInBytes())
    
    conds = []
    
    if x.isMem() and y.isMem():
      
      srcs = x.getLocations()
      dsts = y.getLocations()
      
      for (src,dst) in zip(srcs, dsts):
        sname = Memvars.read(src)
        src_array = mkArray(sname)
        
        sname = Memvars.read(dst)
        dst_array = mkArray(sname)
        
        conds.append(src_array[src.getIndex()] == dst_array[dst.getIndex()])
      
      return conds
    
    elif x.isMem() and y |iss| ImmOp:
      #assert(0)
      srcs = x.getLocations()
      dsts = mkByteListConst(y)

      #endiannes
      dsts.reverse()
    
      for (src,dst) in zip(srcs, dsts):
        #print str(x)
        sname = Memvars.read(src)
        src_array = mkArray(sname)
        conds.append(src_array[src.getIndex()] == dst)
    
      return conds
    else:

      src, dst = self.getOperands([x,y])      
      return [src == dst]  


# Func conditions
class  Call_Gets_Cond(Condition):
  def __init__(self, funcs, ssa):
    self.dst = funcs.write_operands[0]
    self.size = funcs.internal_size
  
  def getEq(self, mlocs):
    
    src = InputOp("stdin", 1)
    src.size_in_bytes = self.size

    srcs = mkByteListVar(src)    
       
    dst = self.dst #self.func.write_operands[0]
    dsts = dst.getLocations()
    
    conds = []
    
    old_sname, new_sname = Memvars.write(dsts[0])

    #array = mkArray(old_sname)
    #new_array = mkArray(new_sname)

    old_array = mkArray(old_sname)
    array = mkArray(new_sname)

    for (src,dst) in zip(srcs, dsts):
      if dst in mlocs:
        array = z3.Store(array, dst.getIndex(), src)
      
      conds.append(src <> 10)
      conds.append(src <> 0)
 
    conds.append((old_array == array))
    return conds
    #r = []

    #old_sname, new_sname, offset = Memvars.write(self.dst)
      
    #old_array = mkArray(old_sname)
    #array = mkArray(new_sname)

    #for i in range(self.size):
      
      #op = Operand(self.dst.mem_source+"@"+str(offset+i), "BYTE")
      
      #if (op in mvars):
      #  array = z3.Store(array, offset+i, z3.BitVec("stdin:"+str(i)+"(0)",8))
        
      #r.append(z3.BitVec("stdin:"+str(i)+"(0)",8) <> 10)
      #r.append(z3.BitVec("stdin:"+str(i)+"(0)",8) <> 0)
      
    #r.append((old_array == array))

    #return r

"""
class  Call_Strlen_Cond(Condition):
  def __init__(self, funcs, ssa):
  
  
    self.ssa_map = ssa_map    
    self.read_operands = map(lambda o: self.__apply_ssa(o), self.read_operands)
    self.write_operands = map(lambda o: self.__apply_ssa(o), self.write_operands)
    
    self.src    = self.read_operands[0]
    self.retreg = self.write_operands[0]
    self.size = funcs.internal_size
    
  
  def getEq(self, mvars):
    
    retreg = self.getOperands([self.retreg])
    return retreg == self.size
"""

class  Call_Strcpy_Cond(Condition):
  def __init__(self, funcs, ssa):
    self.src =  funcs.read_operands[0]#funcs.parameter_vals[1]
    self.dst =  funcs.write_operands[0]#funcs.parameter_vals[0]
    self.size = funcs.internal_size
  
  def getEq(self, mlocs):
    #assert(0)
    #for loc in mlocs:
    #  print loc, "--",
    #print ""
    r = []
    src = self.src
    srcs = src.getLocations()
    sname = Memvars.read(srcs[0])

    read_array = mkArray(sname)

    dst = self.dst 
    dsts = dst.getLocations()
    
    old_sname, new_sname = Memvars.write(dsts[0])
    
    old_array = mkArray(old_sname)
    array = mkArray(new_sname)

    for (src_loc,dst_loc) in zip(srcs, dsts):

      read_val = z3.Select(read_array, src_loc.getIndex()) 
      if dst_loc in mlocs:
        array = z3.Store(array, dst_loc.getIndex(), read_val)
      
      r.append(read_val <> 0)
 
    r.append((old_array == array))
    #print r
    #assert(0)
    return r


    #print self.src, self.dst
    
    #if (self.src.isReg()):
    #  src = self.src.name
    #  self.src.size = self.size
    #  srcs = self.getOperands([self.src])
    #  print srcs
    #else:
    #  assert(0)
  
    #old_sname, new_sname, offset = Memvars.write(self.dst)
      
    #old_array = mkArray(old_sname)
    #array = mkArray(new_sname)
    
    #for i in range(self.size):
      
    #  dst_op = Operand(self.dst.mem_source+"@"+str(offset+i), "BYTE")
    #  src_var = z3.BitVec(src+":"+str(i)+"(0)",8)
      
    #  if (dst_op in mvars):
    #    array = z3.Store(array, offset+i, src_var)

    #  r.append(src_var <> 0)
      
    #r.append((old_array == array))

    return r


conds = {
    "call" : Call_Cond,
    
    "gets" : Call_Gets_Cond,
    "strcpy" : Call_Strcpy_Cond,
    
    "jcc": Jcc_Cond,
    "str": Str_Cond,
    "and": And_Cond,
    "or": Or_Cond,
    "xor": Xor_Cond,
    "bsh": Shift_Cond,
    "add": Add_Cond,
    "sub": Sub_Cond,
    "mul": Mul_Cond,
    "bisz": Bisz_Cond,
    
    "ldm": Ldm_Cond,
    "stm": Stm_Cond,
    }

########NEW FILE########
__FILENAME__ = Bap
"""
   Copyright (c) 2013 neuromancer
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
   3. The name of the author may not be used to endorse or promote products
      derived from this software without specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
   IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
   OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
   IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
   NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
   THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from json import *
from Operand import *
from Instruction import *

class BinOp:
  def __init__(self, name, op1, op2):
    self.name = name
    self.op1 = op1
    self.op2 = op2
  
  def __str__(self):
    return str(self.name)+"("+str(self.op1)+","+str(self.op2)+")"


class BapInstruction(Instruction):
  
  def __readAttributes__(self, d):
    if 'attributes' in d:
      atts = d['attributes']
      for att in atts:
        if 'strattr' in att:
          self.isCallV = ('call' == att['strattr'])
        if 'strattr' in att:
          self.isRetV = ('ret' == att['strattr'])
  
  def __getBinOp__(self, d):
    
    name = d["binop_type"]
    op1  = self.__getExp__(d["lexp"])
    op2  = self.__getExp__(d["rexp"])
    
    return BinOp(name, op1, op2)
  
  def __getStore__(self, d):
    address = self.__getExp__(d['address'])
    value = self.__getExp__(d['value'])
 
    print address, "->", value
    endian = d['endian']
    assert(0)


  def __getExp__(self, d):
    
    if 'var' in d:
      return self.__getVar__(d['var'])
    if 'inte' in d:
      return self.__getInt__(d['inte'])
    elif 'binop' in d:
      return self.__getBinOp__(d['binop'])
    elif 'store' in d:
      return self.__getStore__(d['store'])
    else:
      #pass
      print "exp:"
      print d
      assert(0)
  
  def __getInt__(self, d):
    return int(d['int'])

  def __getVar__(self, d):
    
    if ('reg' in d['typ']):
      return RegOp(d['name'], d['typ'])
    else:
      #pass
      print d['name'], d['typ']
      assert(False)

  def __getLoad__(self, d):
    return self.__getInt__(d['address']['inte'])

  def __getBranch__(self, d):
    size = "DWORD"
    if 'inte' in d:
      name = hex(self.__getInt__(d['inte']))
      return AddrOp(name, size)
    elif 'lab' in d:
      name = d['lab']
      return AddrOp(name, size)
    elif 'load' in d:
      name = hex(self.__getLoad__(d['load']))
      return pAddrOp(name, size)
    elif 'var' in d:
      return self.__getVar__(d['var'])
    else:
      print d
      assert(False)
      
  def __init__(self, dins):
    
    self.read_operands = []
    self.write_operands = []
    self.branchs = []
    # self.address = pins.address
    # self.instruction = pins.instruction
    # self.operands = []
    
    # # for memory instructions
    # self.mem_reg = None
    
    # # for call instructions
    self.called_function = None
    self.instruction = None
    self.raw = str(dins)
    self.isCallV = False
    self.isRetV  = False
    #self.isJmp = False
    
    if ('label_stmt' in dins):
      assert(False)
    elif ('move' in dins):
        #pass
        self.instruction = 'move'
        
        print "moving to:", self.__getVar__(dins['move']['var']) 
        
        exp = self.__getExp__(dins['move']['exp'])
        
        self.read_operands = [exp]
        
        self.write_operands = [self.__getVar__(dins['move']['var'])]
        
        #print self.write_operands[0], "=", self.read_operands[0]
        #var = dins['move']['var']
        #exp = dins['move']['exp']
        #print 'dst', var['name']
        #print 'src', exp
    elif ('jmp' in dins):
        self.instruction = 'jmp'
        #self.isJmp = True
        self.__readAttributes__(dins['jmp'])
        
        if 'exp' in dins['jmp']:
          self.branchs = [self.__getBranch__(dins['jmp']['exp'])]
            
        #print 'jmp:', dins['jmp']
    elif ('cjmp' in dins):
        self.instruction = 'cjmp'
        #self.isJmp = True
        self.__readAttributes__(dins['cjmp'])
        
        if 'iftrue' in dins['cjmp']:
          d = dins['cjmp']['iftrue']
          self.branchs = [self.__getBranch__(d)]
        
        if 'iffalse' in dins['cjmp']:
          d = dins['cjmp']['iffalse']
          self.branchs.append(self.__getBranch__(d))
                  
         
    else:
        self.instruction = "xxx"
        #assert(False)
        
        
  def isCall(self):
    return self.isCallV
  def isRet(self):
    return self.isRetV
    
  def isJmp(self):
    return self.instruction == "jmp"
    
  def isCJmp(self):
    return self.instruction == "cjmp"
    

def BapParser(filename):
    openf = open(filename)
    size = "DWORD" #size of address
    r = []
    
    for dins in load(openf):
      if ('label_stmt' in dins):
        if 'label' in dins['label_stmt']:
          label = dins['label_stmt']['label']
          if 'name' in label:
            r.append(AddrOp(label['name'], size))
          else:
            r.append(AddrOp(hex(int(label['addr'])), size))
      else:
        r.append(BapInstruction(dins))
        
    return r
    

########NEW FILE########
__FILENAME__ = Instruction
"""
   Copyright (c) 2013 neuromancer
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
   3. The name of the author may not be used to endorse or promote products
      derived from this software without specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
   IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
   OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
   IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
   NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
   THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from Operand import *
from copy    import copy

class Instruction:
  """An abstract instruction class"""

  def __init__(self, raw_ins):
    """Creates a new instruction from raw data"""
    pass
  
  def setMemoryAccess(self, mem_access):
    """Set the memory address accessed by the instruction updating its read/write operands"""
    pass

  def setBranchTaken(self, branch):
    """Set the branch taken in a jmp instruction"""  
    pass

  def getBranchTaken(self):
    """Get the branch taken in a jmp instruction"""  
    pass
 
  def getCounter(self):
    """Returns the counter set by an instruction path"""
    return self.counter

  def setCounter(self, counter):
    """Sets the instructions counter in a path"""
    self.counter = counter

  def getOperands(self):
    """Returns the list of all operands"""
    return list(self.read_operands + self.write_operands)
  
  def getReadOperands(self):
    """Returns the list of read operands"""
    return list(self.read_operands)

  def getWriteOperands(self):
    """Returns the list of written operands"""
    return list(self.write_operands)

  def getReadRegOperands(self):
    """Returns the list of operand that are read registers"""
    return filter(lambda o: o |iss| RegOp, self.read_operands)

  def getWriteRegOperands(self):
    """Returns the list of operands that are written registers"""
    return filter(lambda o: o |iss| RegOp, self.write_operands)
  
  def getReadVarOperands(self):
    """Returns the list of read operands that are not constant"""
    return filter(lambda o: o.isVar(), self.read_operands)

  def getWriteVarOperands(self):
    """Returns the list of written operand that are not constants""" 
    return filter(lambda o: o.isVar(), self.write_operands)
  
  def getReadMemOperands(self):
    return filter(lambda o: o.isMem(), self.read_operands)

  def getWriteMemOperands(self):
    return filter(lambda o: o.isMem(), self.write_operands)
  
  def getMemReg(self):
    """Returns the register operand used for memory addressing (or None)"""
    return self.mem_reg 
  
  def isReadWrite(self):
    """Returns if the instruction is reading or writting the memory"""
    return self.mem_reg <> None  
  
  def isCall(self):
    """Returns if the instruction is a call"""
    pass
  def isRet(self):
    """Returns if the instruction is a ret"""
    pass
    
  def isJmp(self):
    """Returns if the instruction is an unconditional jmp"""
    pass
    
  def isCJmp(self):
    """Returns if the instruction is a conditional jmp"""
    pass

  def copy(self):
    """Returns a copy of current instance of Instruction"""
    return copy(self)


########NEW FILE########
__FILENAME__ = Lattice
"""
   Copyright (c) 2013 neuromancer
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
   3. The name of the author may not be used to endorse or promote products
      derived from this software without specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
   IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
   OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
   IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
   NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
   THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from __init__ import *

gs = [("Data32","Num32"), ("Data32","Ptr32"), ("Data32","HPtr32"), ("Data32","SPtr32"), ("Data32","GPtr32"),
      ("Num32", "Ptr32"), ("Num32","HPtr32"), ("Num32","SPtr32"), ("Num32","GPtr32"),
      ("Ptr32", "SPtr32"),  ("Ptr32", "HPtr32"), ("Ptr32", "GPtr32")]

mlattice = dict()

for t in ptypes:
    mlattice[t.name, t.name] = 0
for (pt1, pt2) in gs:
    mlattice[pt1, pt2] = 1
    mlattice[pt2, pt1] = -1
    
def propagateInfo(pt1_info, pt2_info):
  if (pt1_info == pt2_info):
    return pt1_info
  
  if (pt1_info == None):
    return pt2_info
  
  if (pt2_info == None):
    return pt1_info

def join(pt1, pt2):
  """ 
     Select the supremum of two primitive types
     combining their addition information
  """
  p = (pt1.name, pt2.name)
    
  einfo = propagateInfo(pt1.einfo, pt2.einfo)
    
  if p in mlattice and pt1.index == pt2.index:
    if mlattice[p] >= 0:
      pt2.setInfo(einfo)
      return pt2
          
    if mlattice[p] < 0:
      pt1.setInfo(einfo)
      return pt1
  else:
    return Type("Bot32", None)
      
def joinset(s):
  """ Perform join of all the elements in a set """ 
  assert(len(s) > 0)
  
  for pt in s:
  
    if (not isinstance(pt,Type)):
      for e in s:
        if (not isinstance(e,Type)):
          print e.__class__, "--",
        else:
	  
          print e, "--",
      assert(0)
  
  r = s.pop()
  
  for pt in s:
    r = join(r, pt)
  
  
  return r

########NEW FILE########
__FILENAME__ = Location
"""
   Copyright (c) 2013 neuromancer
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
   3. The name of the author may not be used to endorse or promote products
      derived from this software without specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
   IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
   OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
   IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
   NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
   THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

class Location:

  def __init__(self, name, index):
    self.type = None
    self.name = str(name)
    self.index = index

  def getType(self):
    return self.type
    
  def getIndex(self):
    return self.index

  def __str__(self):
    assert(False)

  def __cmp__(self, op):
    #return cmp(self.name,op.name) * cmp(self.index,op.index)
    return cmp(str(self), str(op))
  
  def __hash__(self):
    return hash(self.__str__())
    
  def __int__(self, base=10):
    assert(False)

class ImmLoc(Location):
  def __str__(self):
    return str(self.__int__(self.name))
  
  def __int__(self, base=10):
  
    if ("0x" in self.name):    
      return int(self.name.replace("0x",""),16)
    else:
      return int(self.name,10)

class AddrLoc(Location):
  def __str__(self):
    return self.name+"("+str(self.index)+")"

class pAddrLoc(Location):
  pass

class RegLoc(Location):
  def __str__(self):
    return self.name+"("+str(self.index)+")"


class InputLoc(Location):
  def __str__(self):
    return self.name+"("+str(self.index)+")"

class pRegLoc(Location):
  pass

class MemLoc(Location):
  def __str__(self):
    return self.name+"("+str(self.index)+")"

class NoLoc(Location):
  pass


########NEW FILE########
__FILENAME__ = Operand
"""
   Copyright (c) 2013 neuromancer
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
   3. The name of the author may not be used to endorse or promote products
      derived from this software without specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
   IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
   OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
   IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
   NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
   THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from Location import *
from copy     import copy
import sys
  
size_in_bits = {
    "BYTE"  : 8,
    "WORD"  : 16,
    "DWORD" : 32,
    "QWORD" : 64,
    "1"     : 1,
    "8"     : 8,
    "16"    : 16,
    "32"    : 32,
    "64"    : 64,
    1       : 1,
    8       : 8,
    16      : 16,
    32      : 32,
    64      : 64,
}

class Operand:
  """ Abstract class of an operand used in the abstract instructions """
  def __init__(self, name, size, offset = 0):
    """ Creates a new operand with name, size and offset """
    self.type = None
    self.name = str(name)
    self.offset = offset
    self.value  = None
    
    self.resize(size)
  
  def resize(self, new_size):
    """ Change the size of an operand"""

    self.size_in_bits = size_in_bits.get(str(new_size), 0)
    
    if (self.size_in_bits % 8 == 0):
      self.size_in_bytes = self.size_in_bits / 8
    else:
      self.size_in_bytes = () # bottom

    self.size = self.size_in_bits
  
  def getName(self):
    """ The name of an operand """
    return str(self.name)

  def getSizeInBytes(self):
    """ The size of an operand in bytes """
    return self.size_in_bytes
  
  def getSizeInBits(self):
    """ The size of an operand in bits """
    return self.size_in_bits
    
  def getOffset(self):
    """ The offset of where an operand starts"""
    return self.offset

  def getType(self):
    """ The type of an operand """
    return self.type
 
  def setType(self, t):
    """ Sets the type of an operand """
    self.type = t
    
  def getLocations(self):
    """ Returns the list of locations of an operand """
    sys.exit("ERROR: getLocations not implemented!")
    
  def getTypedLocations(self, type):
    sys.exit("ERROR: getTypedLocations not implemented!")
    
  def setValue(self, value):
    sys.exit("ERROR: setValue not implemented!")
  
  def getValue(self):
    sys.exit("ERROR: getValue not implemented!")
  
  def isVar(self):
    """ True if the operand is variable, otherwise, False """
    print self.name, self.__class__
    sys.exit("ERROR: isVar not implemented!")
    
  def isMem(self):
    """ True if the operand is m"""
    print self.name, self.__class__
    sys.exit("ERROR: isMem not implemented!")
    
  def isStackMem(self):
    print self.name, self.__class__
    sys.exit("ERROR: isStackMem not implemented!")
  
  def __str__(self):
    return self.name

  def __cmp__(self, op):
    
    if op == None:
      #print op
      return -1
    
    return cmp(str(self),str(op)) 
  
  def __hash__(self):
    return hash(self.name)
    
  def copy(self):
    return copy(self)
    
class ImmOp(Operand):
  """ A value coded in the instruction itself """
  def getLocations(self):
    
    r = []
    fmt = "%0."+str(2*self.size_in_bytes)+"x"
    
    if ("0x" in self.name):
      hx = fmt % int(self.name,16)
    else:
      hx = fmt % int(self.name,10)
    
    for i in range(0,2*self.size_in_bytes,2):
      r.append(ImmLoc("0x"+hx[i:i+2],i/2))
    
    return r

  def getValue(self):
    if ("0x" in self.name):
      return int(self.name,16)
    else:
      return int(self.name,10)
      
  def isVar(self):
    return False
    
  def isMem(self):
    return False
    
  def isStackMem(self):
    return False
      
  def __str__(self):
    fmt = "0x%0."+str(2*self.size_in_bytes)+"x"
    #print fmt
    if ("0x" in self.name):   
      return "imm:"+(fmt % (int(self.name,16)))
    else:
      return "imm:"+(fmt % (int(self.name,10)))
      

class AddrOp(Operand): # same as immediate
  """ A value coded in the instruction itself which is known to be an address """
  def __str__(self):
    return str(self.name)
      
  def isVar(self):
    return False
    
  def isMem(self):
    return False
  
  def isStackMem(self):
    return False
  
  def getLocations(self):
    
    r = []   
    for i in range(0,self.size_in_bytes):
      r.append(AddrLoc(self.name,i))
       
    return r
  
  def getValue(self):
    if ("0x" in self.name):
      return int(self.name,16)
    else:
      return int(self.name,10)


class pAddrOp(Operand):
  def __str__(self):
    fmt = "0x%0."+str(2*self.size_in_bytes)+"x)"
    #print fmt
    if ("0x" in self.name):   
      return "*(imm:"+(fmt % (int(self.name,16)))
    else:
      return "*(imm:"+(fmt % (int(self.name,10)))
      
  def isVar(self):
    return True
    
  def isMem(self):
    return True

class MemOp(Operand):
  """ """
  def isVar(self):
    return True
    
  def isMem(self):
    return True
    
  def getLocations(self):
    
    r = []
    
    for i in range(0,self.size_in_bytes):
      loc = MemLoc(self.name,self.offset+i)
      
      if (self.type <> None):
        loc.type = self.type.copy()
        loc.type.index = i
      
      #print self.name, "->", loc.type
      
      r.append(loc)
       
    return r

  def __str__(self):
    #return "reg:"+self.name
    return str(self.name)+"("+str(self.offset)+")"
    
  def setValue(self, value):
    self.value = value
    
  def getValue(self):
    assert(self.value <> None)
    return self.value
    
class RegOp(Operand):
  """ An abstract register"""
  def isVar(self):
    return True
    
  def isMem(self):
    return False
    
  def getLocations(self):
    
    r = []
    
    for i in range(0,self.size_in_bytes):
      r.append(RegLoc(self.name,i))
       
    return r

  def __str__(self):
    #return "reg:"+self.name
    return str(self.name)
    
  def setValue(self, value):
    self.value = value
    
  def getValue(self):
    assert(self.value <> None)
    return self.value

class pRegOp(Operand):

  def isVar(self):
    return True
    
  def isMem(self):
    return True

  def __str__(self):
    return "*(reg:"+self.name+")"

class NoOp(Operand):
  def __init__(self, name = None, size = None):
    self.name = ""
    self.size = 0
    
  def isVar(self):
    return False
    
  def isMem(self):
    sys.exit("Oh no!")

class InputOp(Operand):
  """ A operand flagged as input"""
  def isVar(self):
    return True
    
  def isMem(self):
    return False
    
  def getLocations(self):
    
    r = []
    
    for i in range(0,self.size_in_bytes):
      r.append(InputLoc(self.name,i))
       
    return r

  def __str__(self):
    return str(self.name)
    
  def setValue(self, value):
    self.value = value
    
  def getValue(self):
    assert(self.value <> None)
    return self.value

# taken from http://code.activestate.com/recipes/384122/
# definition of an Infix operator class
# this recipe also works in jython
# calling sequence for the infix is either:
#  x |op| y
# or:
# x <<op>> y

class Infix:
    def __init__(self, function):
        self.function = function
    def __ror__(self, other):
        return Infix(lambda x, self=self, other=other: self.function(other, x))
    def __or__(self, other):
        return self.function(other)
    def __rlshift__(self, other):
        return Infix(lambda x, self=self, other=other: self.function(other, x))
    def __rshift__(self, other):
        return self.function(other)
    def __call__(self, value1, value2):
        return self.function(value1, value2)

iss=Infix(isinstance)


########NEW FILE########
__FILENAME__ = Path
"""
   Copyright (c) 2013 neuromancer
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
   3. The name of the author may not be used to endorse or promote products
      derived from this software without specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
   IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
   OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
   IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
   NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
   THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from Instruction import *

class Path:
  """An abstract path class"""
  def __init__(self, first, last, code = None, filename = None, parser = None, is_reversed = False):
        
    if (filename <> None and parser <> None):
        
      self.init_type = "file"
      self.filename = filename
      self.parser   = parser
      self.code = self.parser(self.filename)
        
    elif (code <> None):
      self.init_type = "code"
      self.code = list(code)
        
    self.code = filter(lambda i: i |iss| Instruction, self.code)
    self.first = first
    if last <> first:
      self.last = min(first + len(self.code), last) - 1
    else:
      self.last = last

    assert(self.last >= self.first)
    self.len = self.last - self.first 

    self.is_reversed = is_reversed
    
    if (self.is_reversed):
      self.current = self.last
    else:
      self.current = first

  def __iter__(self):
    """Returns the iterator of the path"""
    return self
    
  def __len__(self):
    """Returns the size of the path"""
    return self.len

  def next(self):
    """Returns the next instruction or the previous, depending if the path is reversed"""

    #print self.current, self.is_reversed, self.len
    if (self.is_reversed):
      if self.current < self.first:
        raise StopIteration
      else:
        ins = self.code[self.current]
        ins.setCounter(self.current)
          
        self.current -= 1
        return ins
    else:
       if self.current >= self.last:
         raise StopIteration
       else:
         ins = self.code[self.current]
         ins.setCounter(self.current)
          
         self.current += 1
         return ins        
    
  def reverse(self):
    """Reverse the path, changing the order of the instructions"""

    self.is_reversed = not (self.is_reversed)
    if (self.is_reversed):
      self.current = self.last
    else:
      self.current = self.first
        
  def reset(self):
    """Resets the path to the first or the last instruction, depending if the path is reversed"""

    if (self.is_reversed):
      self.current = self.last
    else:
      self.current = self.first
        
  def __getitem__(self, i):
    """Returns an instruction of the path or an slice of the path"""
        
    if (type(i) == slice):
     (first, last, stride) = i.indices(self.len)
          
     if self.init_type == "file":    
       # slice of reversed path not supported!
       assert(not self.is_reversed)		    
       return Path(first, last, filename = self.filename, parser = self.parser, is_reversed = self.is_reversed) 

     elif self.init_type == "code":
       return Path(first, last, code = self.code)

    else: 
      if (i<0):
        i = self.last + 1 + i
      return self.code[i]

########NEW FILE########
__FILENAME__ = PathGenerator
"""
   Copyright (c) 2013 neuromancer
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
   3. The name of the author may not be used to endorse or promote products
      derived from this software without specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
   IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
   OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
   IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
   NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
   THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from __init__ import *

class PathInfo:
  def __init__(self, ilabels):
    pass

class PathGenerator:
  def __init__(program, start, ends, max_count):
    pass
  
  def __iter__(self):
    return self 
    
  def next(self):
    pass
  
  
import random  

class RandomPathGenerator(PathGenerator):
  
  def __init__(self, program, start, ends, max_count = 1000):
    self.program = program
    self.start = start
    self.ends = ends
    self.max_count = max_count
  
  def next(self):
  
    self.program.reset(self.start)
    branches_taken = []
    code = []
    count = 0
    for ins in self.program:
      #print str(ins.ins_raw)
      #print ins.address
      code.append(ins)
      if count == self.max_count:
        break
      
      #if branches_taken <> []:
      #  if branches_taken[-1] in self.ends:
      #    break
         #print "last:", branches_taken[-1]
  
      if ins.isJmp():
	#print ins.branchs[0]
        pass
        #if str(ins.branchs[0]) == "0x8048890":
          #branches_taken.append("exit")
          #break
      
        #if str(ins.branchs[0]) == "0x8048800":
          #branches_taken.append("__stack_chk_fail")
          #break
    
      elif ins.isCJmp():
        count = count + 1
        i = bool(random.randint(0,1))
        #print ins.branchs[0], ins.branchs[1]  
        if i == False:
          branches_taken.append(self.program.selectFalseBranch())
          ins.setBranchTaken(0)
        elif i == True:
          branches_taken.append(self.program.selectTrueBranch())
          ins.setBranchTaken(1)

    
    path = AbsPath(0, len(code), code)

    return (path, branches_taken)

import sys

class ManualPathGenerator(PathGenerator):
  def __init__(self, program, start, ends, max_count = 1000):
    self.program = program
    self.start = start
    self.max_count = max_count
    
  def __help_path__(self):
   print "To select interactively a path in this program use:"
   print "t to continue with the true branch."
   print "f to continue with the false branch."
   print "i to step in."
   print "o to step out."
   print "e to finish recording a path."
  
  def __ask__(self, values):
  
    i = None
    prompt = ",".join(values)+">"
    
    try:
      while (not (i in values)):
        if i <> None:
          print "Invalid selection"
        i = raw_input(prompt)
    except EOFError:
      print ""
      sys.exit(0)
      

  
    return i
 

  def next(self):
  
    self.program.reset(self.start)
    branches_taken = []
    code = []
    counter = 0
    self.__help_path__()
    for ins in self.program:
      
      code.append(ins)
      print "(%.4d)" % counter, ins
      counter = counter + 1
      if counter == self.max_count:
        break
      
      #if ins.isCall() and False:
      #  print "call detected! (", ins.branchs[0], ")"
      #  i = ask(["i", "o", "e"])
      
      #  if (i == "e"):
      #    break
      #  elif (i == "i"):
      #    self.program.stepIn()
      #  elif (i == "o"):
      #    pass


      #elif ins.isJmp():
      #  pass
    
      if ins.isCJmp():
        i = self.__ask__(["t","f","e"])#bool(random.randint(0,1))
        if i == "f":
          branches_taken.append(self.program.selectFalseBranch())
          ins.setBranchTaken(0)
        elif i == "t":
          branches_taken.append(self.program.selectTrueBranch())
          ins.setBranchTaken(1)
        elif i == "e":
          code.pop()
          break
      else:
        pass
	#i = self.__ask__(["s","e"])
	#if i == "s":
	#  pass
	#elif i == "e":
	#  code.pop()
	#  break

    
    path = AbsPath(0, len(code), code)
    return (path, branches_taken)

class MarkovianPathGenerator(PathGenerator):
  def __init__(self, program, start, ends, train_labels, max_count = 1000):
    pass
    
    




########NEW FILE########
__FILENAME__ = Program
"""
   Copyright (c) 2013 neuromancer
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
   3. The name of the author may not be used to endorse or promote products
      derived from this software without specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
   IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
   OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
   IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
   NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
   THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from Operand  import * 
from Instruction import Instruction

class Program:
    def __init__(self, filename, parser):
        
        self.filename = filename
        self.parser   = parser
        self.current  = 0
        
        self.labels   = dict()
        self.labels['0'] = 0

        self.all = self.parser(self.filename)
        self.code = []
        self.callstack = []
        
        for e in self.all:
          if (e |iss| AddrOp):
            self.labels[str(e)] = self.current
          elif (e |iss| Instruction):
            self.code.append(e)
            self.current = self.current + 1
          else:
            assert(False)
        #print self.labels 
        self.current = 0
        #self.code = map(cons, self.code)
        
        self.len = len(self.code)
        
        self.first = 0
        self.last = self.len

    def __iter__(self):
        return self
    
    def __len__(self):
        return self.len

    def stepIn(self):
      
      assert(not (self.prev_ins == None))
      assert(self.prev_ins.isCall())
      
      branchs = self.prev_ins.branchs
      taken = branchs[0]
      
      if not (taken |iss| AddrOp):
         print "Impossible to step into this call"
         assert(False)
      
      if str(taken) in self.labels:
        print taken, "call"
        # TODO: check if this is the last instruction!
        self.callstack.append(self.current)
        self.current = self.labels[str(taken)]
      else:
	assert(False)
        
    def selectTrueBranch(self):
        #ins = self.code[self.current-1]
        #print "true"
        assert(not (self.prev_ins == None))
        branchs = self.prev_ins.branchs
        
        if (len(branchs) == 0):
            print "This instruction is not a jmp/call"
            assert(False)
        else:
            taken = branchs[0]
            
            if not (taken |iss| AddrOp):
              print "Impossible to follow jmp"
              assert(False)
            
            if str(taken) in self.labels:
              #print taken, "taken!"
              self.current = self.labels[str(taken)]#[0]
              self.selected = True
            else:
              print "Unresolved jmp to", str(taken)
              assert(False)
              
        self.prev_ins = None
        return str(taken) 
        
    def selectFalseBranch(self):
        #print "false"
        #ins = self.code[self.current-1]
        assert(not (self.prev_ins == None))
        branchs = self.prev_ins.branchs
        
        if (len(branchs) == 0):
            print "This instruction is not a jmp/call"
            assert(False)
        else:
            taken = branchs[-1]
            
            if not (taken |iss| AddrOp):
              print "Impossible to follow jmp"
              assert(False)
            
            if str(taken) in self.labels:
              self.current = self.labels[str(taken)]
            else:
              print "Unresolved jmp to", str(taken)
              assert(False)
              
        self.prev_ins = None
        return str(taken)
            
    
    def next(self):

      if (self.current == None):
	raise BranchUnselected
    
      if self.current >= self.len:
        raise StopIteration
      else:
	
	(addr, ins) = (self.current, self.code[self.current])
	
	if (ins.isCJmp()):
	  self.current = None
	  self.prev_ins = ins
	elif (ins.isJmp()):
	  if (ins.isCall()):
	      self.prev_ins = None
	      self.current = self.current + 1
	      #pass # fixme
	  elif (ins.isRet()):
	    # next instruction is on the return address
	    
	    if self.callstack <> []:
	      self.current = self.callstack.pop()
	    else:
	      raise StopIteration
	    
	    return self.next()
	  else:
	    # next instruction is the only possible branch
	    
	    taken = ins.branchs[0]
	    
	    if not (taken |iss| AddrOp):
              print "Impossible to follow jmp"
              assert(False)
	    
	    self.current = self.labels[str(taken)]
	else:
	  # next instruction is the following 
	  self.current = self.current + 1
	
	return ins.copy()
        
    def reset(self, start = None):
      if (start <> None):
        self.current = self.labels[str(start)]
      else:
	self.current = 0
      
      self.prev_ins = None
      self.callstack = []
      
        
    def __getitem__(self, i):
        
        if (type(i) == slice):
          raise NoSlice
        else:
          return self.code[i]

########NEW FILE########
__FILENAME__ = Reil
"""
   Copyright (c) 2013 neuromancer
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
   3. The name of the author may not be used to endorse or promote products
      derived from this software without specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
   IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
   OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
   IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
   NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
   THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from pkgs.pyparsing import Word, Literal, alphas, alphanums, delimitedList
from Types import *
from Operand import *
from Instruction import Instruction

address         = Word( alphanums).setResultsName("address")
colon           = Literal( ":" )
instruction     = Word( alphas ).setResultsName("instruction")
left_sbracket   = Literal("[")
right_sbracket  = Literal("]")
operand         = Word( alphanums+"-_" ).setResultsName("operand")
size            = Word( alphas ).setResultsName("size")
no_operand      = Literal( "EMPTY" ).setResultsName("operand") 

aug_operand = (size + operand) | no_operand

comma           = Literal(",")
body            = aug_operand + comma + aug_operand + comma + aug_operand
body            = body.setResultsName("augmented_operands")

reil = address + colon + instruction + left_sbracket + body + right_sbracket

# Quick detection of operand
def RegImmNoOp((name,size)):
  
  if name == "EMPTY":
    return NoOp(name,size)
  
  try:
    y = int(name)
    return ImmOp(name,size)
  except ValueError:
    return RegOp(name,size)

class REILInstruction(Instruction):
  def __init__(self, raw_ins):
    
    pins = reil.parseString(raw_ins)
    self.address = pins.address
    self.instruction = pins.instruction
    self.branchs = []
    self.branch_taken = None
    self.counter = None
    self.operands = []
    
    # for memory instructions
    self.mem_reg = None
    
    # for call instructions
    self.called_function = None
    
    aopers = pins.augmented_operands
    for (i,x) in enumerate(aopers):
       if x == ",":
        self.operands.append((aopers[i-1], aopers[i-2]))
    self.operands.append((aopers[-1], aopers[-2]))
    
    self.read_operands = []
    self.write_operands = []
    
    # ldm: op_2 = [op_0]
    if (pins.instruction == "ldm"):
      
      
      self.write_operands = [RegImmNoOp(self.operands[2])]
      
      name, size = self.operands[0]
      t = RegImmNoOp((name,size))
      
      if (t |iss| ImmOp):
        self.mem_reg = AddrOp(name, size)
        #self.read_operands = [pAddrOp(name, size)]
      elif (t |iss| RegOp):
        self.mem_reg = RegOp(name, size)
        #self.read_operands = [pRegOp(name, size)]
      else:
        assert(False)
      
      #self.operands = map(RegImmNoOp, self.operands)
      
    # stm: [op_2] = op_0
    elif (pins.instruction == "stm"):
      
      self.read_operands.append(RegImmNoOp(self.operands[0]))
      name, size = self.operands[2]
      t = RegImmNoOp((name,size))
      
      if (t |iss| ImmOp):
        self.mem_reg = AddrOp(name, size)
        #self.write_operands = [pAddrOp(name, size)]
      elif (t |iss| RegOp):
        self.mem_reg = RegOp(name, size)
        #self.write_operands = [pRegOp(name, size)]
      else:
        assert(False)

      
    elif (pins.instruction == "jcc"):
      
      
      #pass
      self.operands = map(RegImmNoOp, self.operands)
      self.read_operands  = filter(lambda o: not (o |iss| NoOp), self.operands[0:3])
      addr_size = "DWORD"      
      #print self.address, self.read_operands[0], self.read_operands[0].__class__ 
      
      if ( self.read_operands[-1] |iss| ImmOp): # jmp to a constant address

        self.branchs = [self.__mkReilAddr__(self.read_operands[-1])]

        #if (self.read_operands[0] |iss| ImmOp):
        #  pass

      self.write_operands = []

      if len(self.read_operands) == 3:
        self.setBranchTaken(self.read_operands[1].getValue())
	return
      
    elif (pins.instruction == "call"):
      
      if (self.operands[0][0] <> "EMPTY"):
         self.called_function = self.operands[0][0]
      
    else:
      
      self.operands = map(RegImmNoOp, self.operands)
      
      self.read_operands  = filter(lambda o: not (o |iss| NoOp), self.operands[0:2])
      self.write_operands = filter(lambda o: not (o |iss| NoOp), self.operands[2:3])
      
    
    if self.instruction in ["call", "ret", "bisz", "bsh", "stm", "ldm", "jcc"]:
      pass
    else:
      self.fixOperandSizes()
      
  def fixOperandSizes(self):
    
    #print self.instruction 
    write_sizes = map(lambda o: o.size, self.write_operands)
    read_sizes = map(lambda o: o.size, self.read_operands)
    
    size = min(min(write_sizes), min(read_sizes))
    assert(size > 0)
    
    #print "corrected size:", size
    
    for o in self.write_operands:
      o.resize(size)
   
    for o in self.read_operands:
      o.resize(size)
   
  def setMemoryAccess(self, mem_access):
    assert(mem_access <> None)
    
    ptype, offset = mem_access["access"]
    sname = getMemInfo(ptype)#, ptype.einfo["offset"]
    
    # ldm: op_2 = [op_0]
    if (self.instruction == "ldm"):

      write_operand = RegImmNoOp(self.operands[2])
      
      assert(write_operand |iss| RegOp)
      
      name = sname#+"@"+str(offset)
      op = MemOp(name, write_operand.getSizeInBits(), offset=offset)
      op.type = ptype
      #print "hola:", str(ptype)
      
      self.read_operands = [op]
      
    # stm: [op_2] = op_0
    elif (self.instruction == "stm"):

      read_operand = RegImmNoOp(self.operands[0])
      
      name = sname#+"@"+str(offset)
      op = MemOp(name, read_operand.getSizeInBits(), offset=offset)
      op.type = ptype
      
      #print "hola:", str(ptype)
      
      self.write_operands = [op]
      
    else:
      assert(False)

  def setBranchTaken(self, branch):
    assert(self.isCJmp())
    self.branch_taken = str(branch)

  def getBranchTaken(self):
    return str(self.branch_taken)        

  def __mkReilAddr__(self, op):
    addr_size = "DWORD"
    name = hex(op.getValue())+"00"
    return AddrOp(name,addr_size)

  def clearMemRegs(self):
    self.read_operands = filter(lambda op: op <> self.mem_reg, self.read_operands)
    #self.write_operands = filter(lambda op: op <> mem_reg, self.read_operads)
  
  def isCall(self):
    return self.instruction == "call"
  def isRet(self):
    return self.instruction == "ret"
    
  def __str__(self):

    if self.isCall() and self.called_function <> None:
      r = self.instruction + " "+ self.called_function
      return r


    r = self.instruction + "-> "
    for op in self.read_operands:
      r = r + str(op) + ", "
    
    r = r + "| "
    
    for op in self.write_operands:
      r = r + str(op) + ", "
    
    return r
  
  def isJmp(self):
    return self.instruction == "jcc" and (self.read_operands[0] |iss| ImmOp)
    
  def isCJmp(self):
    return self.instruction == "jcc" and not (self.read_operands[0] |iss| ImmOp)
 
def ReilParser(filename):
    openf = open(filename)
    r = []
    for raw_ins in openf.readlines():
      if not (raw_ins[0] == "#"):
        # TODO: create REILLabel class
        pins = reil.parseString(raw_ins)
        label = hex(int(pins.address,16)).replace("L","")
        addr_op = AddrOp(label, size)
      
        if (r <> []):
          if r[-1].isCJmp(): # if last was conditional jmp
            assert(r[-1].branchs <> [])
            r[-1].branchs.append(addr_op) # next instruction is the missing label in branchs

        r.append(addr_op)
        r.append(REILInstruction(raw_ins))
    
    return r

########NEW FILE########
__FILENAME__ = Types
"""
   Copyright (c) 2013 neuromancer
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
   3. The name of the author may not be used to endorse or promote products
      derived from this software without specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
   IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
   OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
   IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
   NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
   THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import copy

class Type:
  def __init__(self, name, index, einfo = None):
    self.name = str(name)
    self.index = index
    self.setInfo(einfo)
    
  def __str__(self):
    
    r = str(self.name)
    
    if (self.index <> None):
      r = r +"("+str(self.index)+")"
      
    if (self.einfo <> None):
      r = r + " with "
      for k in self.einfo:
        r = r + str(k)+"="+str(self.einfo[k])+", "
    
    return r
  
  def getInfo(self):
    return copy.copy(einfo)
    
  def setInfo(self, einfo):
    self.einfo = copy.copy(einfo)
  
  def addTag(self, tag, value):
    if self.einfo == None:
      self.einfo = dict()
    
    self.einfo[tag] = value
    
  def copy(self):
    return copy.copy(self)
    
    
def getMemInfo(ptype):
    
  name = str(ptype.einfo["source.name"])+"."+str(ptype.einfo["source.index"])
  return name

ptypes = [Type("Data32", None), 
          Type("Num32", None) , 
          Type("Ptr32", None) , 
          Type("SPtr32", None), 
          Type("HPtr32", None), 
          Type("GPtr32", None), 
          Type("Bot32", None) ]


########NEW FILE########
__FILENAME__ = Function
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""
from core import *

class Function:
  """An abstract function class"""
  parameter_typs = []
  parameter_locs = []
  parameter_vals = []
  read_operands  = []
  write_operands = []
  return_type    = None
  
  def __init__(self, pbase = None, pars = None):
    self.parameter_typs = []
    self.parameter_locs = []
    self.parameter_vals = []
    self.read_operands  = []
    self.write_operands = []
  
  def getParameters(self):
    return self.parameter_vals

  def getParameterLocations(self):
    return self.parameter_locs
  
  def getReadVarOperands(self):
    return filter(lambda o: o.isVar(), self.read_operands)
  
  def getWriteVarOperands(self):
    return filter(lambda o: o.isVar(), self.write_operands)
  
  def getEq(self):
    return []
  
  def __loadParameters__(self, pars):
    self.parameter_locs = []
    self.parameter_vals = []
    #print pars
    for (loc, ptype, offset) in pars:
      
      self.parameter_locs.append(loc)
      self.parameter_vals.append((ptype,offset))
    
  
  def __locateParameter__(self, disp, size):
    ptype, offset = self.pbase
    
    op = MemOp(getMemInfo(ptype), size, offset=offset+disp)
    op.type = ptype
    
    return op
  
class Skip_Func(Function):
  pass

class Gets_Func(Function):
  parameter_typs = [(Type("Ptr32",None), "DWORD", 0, True)]
  return_type    = "void"
  
  def __init__(self, pbase = None, pars = None):
    
    self.internal_size = 84
    
    if (type(pbase) <> type(None)):
      self.pbase = pbase
      for (ptype, size, disp, needed) in self.parameter_typs:
        self.parameter_locs.append((ptype, self.__locateParameter__(disp, size), needed))
    else:
      self.__loadParameters__(pars)
      # populate read operands
      
      #self.read_operands.append(self.parameter_locs[0])
      
      ptype,offset = self.parameter_vals[0]
      op = MemOp(getMemInfo(ptype), 1, offset)
      op.size_in_bytes = self.internal_size
      op.setType(ptype)

      # populate write operands
      self.write_operands = [op]
     
      # populate read operands
     
      op = InputOp("stdin", 1)
      op.size_in_bytes = self.internal_size

      self.read_operands = [op]
 

class Strlen_Func(Function):
  parameter_typs = [(Type("Ptr32",None), "DWORD", 0, True)]
  return_type    = Type("Num32",None)
  
  def __init__(self, pbase = None, pars = None):
    
    self.internal_size = 10
    
    if (pbase <> None):
      self.pbase = pbase
      for (ptype, size, disp, needed) in self.parameter_typs:
        self.parameter_locs.append((ptype, self.__locateParameter__(disp, size), needed))
    else:
      self.__loadParameters__(pars)
      
      # populate read operands
      
      self.read_operands.append(self.parameter_locs[0])
        
      # return value
      self.write_operands.append(RegOp("eax", "DWORD")) 

class Strcpy_Func(Function):
  parameter_typs = [(Type("Ptr32",None), "DWORD", 0, True), (Type("Ptr32",None), "DWORD", 4, True)]
  return_type    = "void"
  
  def __init__(self, pbase = None, pars = None):
    
    self.internal_size = 256+4
    
    if (type(pbase) <> type(None)):
      self.pbase = pbase
      for (ptype, size, disp, needed) in self.parameter_typs:
        self.parameter_locs.append((ptype, self.__locateParameter__(disp, size), needed))
    else:
      self.__loadParameters__(pars)
      
      # populate read operands
      ptype,offset = self.parameter_vals[0]
      op = MemOp(getMemInfo(ptype), 1, offset)
      op.size_in_bytes = self.internal_size
      op.setType(ptype)

      # populate write operands
      self.write_operands = [op]

      ptype,offset = self.parameter_vals[1]
      op = MemOp(getMemInfo(ptype), 1, offset)
      op.size_in_bytes = self.internal_size
      op.setType(ptype)

      # populate write operands
      self.read_operands = [op]

class Alloc_Func(Function):
  parameter_typs = [(Type("Num32",None), "DWORD", 0, True)]
  return_type    = "void *"
  
  def __init__(self, pbase = None, pars = None):
    
    self.parameter_locs = []
    self.parameter_vals = []
    self.read_operands  = []
    self.write_operands = []
    
    if (type(pbase) <> type(None)):
      self.pbase = pbase
      for (ptype, size, disp, needed) in self.parameter_typs:
        self.parameter_locs.append((ptype, self.__locateParameter__(disp, size), needed))
    else:
      self.__loadParameters__(pars)

class Free_Func(Function):
  parameter_typs = [(Type("Ptr32",None), "DWORD", 0, True)]
  return_type    = "void"
  
  def __init__(self, pbase = None, pars = None):
    
    self.parameter_locs = []
    self.parameter_vals = []
    self.read_operands  = []
    self.write_operands = []
    
    if (type(pbase) <> type(None)):
      self.pbase = pbase
      for (ptype, size, disp, needed) in self.parameter_typs:
        self.parameter_locs.append((ptype, self.__locateParameter__(disp, size), needed))
    else:
      self.__loadParameters__(pars)
      

funcs = {
    "printf" : Skip_Func,
    "puts"   : Skip_Func,
    "gets"   : Gets_Func,
    "malloc" : Alloc_Func,
    "free"   : Free_Func,
    "strcpy" : Strcpy_Func,
    "strlen" : Strlen_Func,
}

########NEW FILE########
__FILENAME__ = Inputs
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

from core import *

def parse_inputs(inputs):
  
  r = dict()  
    
  for s in inputs:
    #print s
    s = s.strip("(").strip(")")
    (rop, rval) = s.split(",")
    ropsize, rop  = rop.split(" ")
    rvalsize, rval = rval.split(" ")
    
    mem_source = None
    mem_offset = None
    
    
    
    if ('arg[' in rop):
      pass  
    
    elif ('@' in rop):
      mem_source, mem_offset = rop.split('@')
      mem_offset = int(mem_offset)
    
    
    if (ropsize == rvalsize and rvalsize == "VAR"):
      for i,c in enumerate(rval):
        # TODO: this is only for inputs!
        r[Operand(rop+str(i), "BYTE", mem_source, mem_offset)] =  Operand(str(ord(c)), "BYTE")
    else:
      r[Operand(rop, ropsize, mem_source, mem_offset)] =  Operand(rval, rvalsize)
  
  return r

########NEW FILE########
__FILENAME__ = JumpConditions
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

from sys         import exit

from core        import *
from Common      import getPathConditions

#input_vars = ["stdin:", "arg[0]@0:", "arg[1]@0:", "arg[2]@0:"]

def getJumpConditions(trace, addr):
  last_ins = (trace["code"][-1])
  addr = int(addr, 16)
  pos = trace["code"].last - 1
  
  if (last_ins.isJmp() or last_ins.isCJmp()):
    jmp_op = last_ins.operands[2]
    
    if (jmp_op.isVar()):
      
      #print addr  
      trace["final_conditions"] = dict([( jmp_op , ImmOp(str(addr), "DWORD"))])
      (fvars, sol) = getPathConditions(trace, False)
      
      #print sol 
      return (fvars, sol)

    else:
      print "Jump operand (", jmp_op ,") in last instruction (", last_ins.instruction, ") is not variable!" 
      return (set(), None)
    
  else:
    exit("Last instruction ( "+ str(last_ins)+ " ) is not a jmp")

########NEW FILE########
__FILENAME__ = Lifting
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

from src.core import *

def mkPath(pathf, first, last):
  if (".reil" in pathf):
    return ReilPath(pathf, first, last)
  else:
    print "I don't know how to read "+pathf+"."
    assert(0)

def mkProgram(pathf):
  if (".reil" in pathf):
     return ReilProgram(pathf)
  elif (".json" in pathf):
    return BapProgram(pathf)
  else:
    print "I don't know how to lift "+pathf+"."
    assert(0)



########NEW FILE########
__FILENAME__ = Memory
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

from core        import *
from Common      import getValueFromCode
from TypeSlicer  import getTypedValue
  
class MemAccess:
  def __init__(self):
    self.access = dict()
  
  def __str__(self):
    
    counters = self.access.keys()
    counters.sort()
    
    ret = "Memory accesses detected:\n"
    
    for c in counters:
      pt, offset = self.access[c]["access"]
      ret = ret + str(c) + " -> " + str(self.access[c]["type"]) + " : " 
      ret = ret + str(pt) + "@" + str(offset) + "\n"
    
    return ret
  
  def getAccess(self, counter):
    
    if counter in self.access:
      return self.access[counter]
    
    return None

  def detectMemAccess(self, reil_code, callstack, inputs, counter):
    #print reil_code.first, reil_code.last
    ins = reil_code[-1]
    
    assert(ins.isReadWrite()) 
    addr_op = ins.getMemReg()
    #pt = getType(reil_code, callstack, self, addr_op, Type("Ptr32", None)) 
    
    #if str(pt) == "Ptr32":
    #  pt = Type("GPtr32", None)
    #  pt.addTag("source.name","0x00000000")
    #  pt.addTag("source.index",0)
    
    # we reset the path
    #reil_code.reverse()
    #reil_code.reset()
    
    (val,pt) = getTypedValue(reil_code, callstack, self, addr_op, Type("Ptr32", None))
    
    self.access[counter] = self.__mkMemAccess__(ins, pt, val)
      
  def __mkMemAccess__(self, ins, ptype, offset):

    mem_access = dict()
    mem_access["type"]    = ins.instruction
    mem_access["address"] = ins.address
    mem_access["access"]   = (ptype, offset)
    
    return mem_access

########NEW FILE########
__FILENAME__ = MemVars
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

from core import *

class MemVars:

  def __init__(self):
    self.sources = dict()
    
  def reset(self):
    self.sources = dict()

  def createSource(self, src):
    
    if not (src in self.sources):
      self.sources[src] = 0
    else:
      self.sources[src] += 1
    

  def write(self, mem_op):
    
    #sname, offset = getMemInfo(mem_op.type)
    sname = getMemInfo(mem_op.type)
    #sname = mem_op.mem_source
    #offset = mem_op.mem_offset

    if not sname in self.sources:
      self.createSource(sname)

    old_sname = sname + "_" +str(self.sources[sname])
    self.createSource(sname)
    
    new_sname = sname + "_" +str(self.sources[sname])
    #return (old_sname, new_sname, offset)
    return (old_sname, new_sname)

  def read(self, mem_op):
  
    #sname, offset = getMemInfo(mem_op.type)
    sname = getMemInfo(mem_op.type)
    
    #sname = mem_op.mem_source
    #offset = mem_op.mem_offset

    if not sname in self.sources:
      self.createSource(sname)
    
    sname = sname + "_" +str(self.sources[sname])
    return sname
  
  #def getOffset(self, mem_op):
  #  return mem_op.mem_offset
  
Memvars = MemVars()

########NEW FILE########
__FILENAME__ = Parameters
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

from core import *

from Function    import *
#from Common      import getValueFromCode
from TypeSlicer   import getTypedValue

class FuncParameters:
  def __init__(self):
    self.parameters = dict()
    
  def __str__(self):
    
    counters = self.parameters.keys()
    counters.sort()
    
    ret = "Parameters detected:"
    
    for c in counters:
      ret = ret + "\n" + str(c) + " -> "
      param_info = self.parameters[c]
      fname = param_info["function"]
      ret = ret + fname + "("
      
      for (l,t,p) in param_info["parameters"]:
        #print self.parameters[c]#["function"]
        ret = ret  + " " +  str(l) + " := " + str(t)+"@" + str(p) + ","
      ret = ret + ")"
    
    return ret
  
  def getParameters(self, counter):
    
    if counter in self.parameters:
      return self.parameters[counter]["parameters"]
    
    return None
    
  def detectFuncParameters(self, reil_code, memaccess, callstack, inputs, counter):
    
    ins = reil_code[-1]
    
    assert(ins.isCall() and ins.called_function <> None)
    
    # first we locate the stack pointer to know where the parameters are located
    esp_op = RegOp("esp","DWORD")
    (val,ptbase) = getTypedValue(reil_code, callstack, memaccess, esp_op, Type("Ptr32", None))
 
    #ptbase = getType(reil_code, callstack, memaccess, esp_op, Type("Ptr32", None)) 
    
    # we reset the path
    #reil_code.reverse()
    #reil_code.reset()
    
    #val = getValueFromCode(reil_code, callstack, inputs, memaccess, esp_op)
    #ptbase.addTag("offset", val)
    
    #if str(ptbase) == "Ptr32":
    #  print "Unable to detect arguments for", ins.called_function
    #  return
    
    func_cons = funcs.get(ins.called_function, Function)
    func = func_cons(pbase = (ptbase, val))
    #assert(0)
    parameters = []
    
    for (par_pt, memop, needed) in func.getParameterLocations():
      if needed:
      
        reil_code.reverse()
        reil_code.reset()
        
        (val,pt) = getTypedValue(reil_code, callstack, memaccess, memop, par_pt)

        #pt = getType(reil_code, callstack, memaccess, memop, par_pt)
        
        #reil_code.reverse()
        #reil_code.reset()
        
        #val = getValueFromCode(reil_code, callstack, inputs, memaccess, memop)
        #print  "parameter of",ins.called_function, "at", str(location) , "has value:", val.name
        parameters.append((memop, pt, val))
      else:
        parameters.append((None, None, None))
    
    if parameters <> []:
      self.parameters[counter] = self.__getParameters__(ins, parameters)
    

  def __getParameters__(self, ins, raw_parameters):
    parameters = dict()
    parameters["function"] = ins.called_function
    parameters["parameters"] = list(raw_parameters)
    parameters["address"]   = ins.address
    
    return parameters

########NEW FILE########
__FILENAME__ = PathGeneration
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

import random
import csv

from core import *

from Lifting import *
from Prelude import *
from Common import getPathConditions

"""
class PathInfo:
  def __init__(self, ilabels):
    self.E_viw = dict()
    
    self.vi = dict()
    labels = list(ilabels)
    labels.insert(0,"start")
    labels.append("end")
    
    for label in labels:
      self.vi[label] = 0
    
    for (i, label) in enumerate(labels[:-1]):
      self.vi[label] = self.vi[label] + 1 
      self.E_viw[(label, self.vi[label], labels[i+1])] = True
      
  def E(self, v,i, w, j):
    
    return ((v, i, w) in self.E_viw) and j <= self.vi[w] 


class EXISTPathGenerator(PathGenerator):
  
  def __init__(self, program, start, ends, epsilon):
    self.program = program
    self.start = start
    self.epsilon = epsilon
    
    ## for all possible labels
    #self.max_counts = dict()
    
    ## label population
    #for (s, y) in self.epsilon:
      #for label in s:
        #self.max_counts[label] = 0
        
    self.train()
    
  def count(self, seq, labels):
    pass
    #res = dict()
    
    #for label in labels:
      #res[label] = seq.count(label)
	
    #return res
  
  def train(self):
    
    self.pathinfos = []
    
    for (i, (labels, y)) in enumerate(self.epsilon):
      if y:
	pi = PathInfo(labels)
	self.pathinfos.append(pi)
	#print pi.E_viw
  
  def prob(self, v,i, w,j):
    
    count = 0
    for pi in self.pathinfos:
      
      if pi.E(v,i, w, j):
        count = count + 1
    
    if count == 0:
      return 1.0
    
    return float(count)/float(len(self.pathinfos))
    #if self.max_counts[k] == 0: 
      #return 0
    #return float(self.max_counts[k] - res[k])/float(self.max_counts[k])
  
  def select(self, seq, states):
    
    v = seq[-1]
    
    probs = map(lambda w: self.prob(v, seq.count(v) ,w , seq.count(w)+1), states) 
    m = max(probs)
    
    #if (m == 0.0):
    #  return None
    
    indexes = [i for i, j in enumerate(probs) if j == m]
    
    return random.choice(indexes)
    
  
  def next(self):
    self.program.reset(self.start)
    seq = ["start"]
    count = 0
    max_count = 20
    
    for ins in self.program:
      ##print str(ins.raw)
      ##print ins.ins
      if count == max_count:
        break
      
      ##if branches_taken <> []:
        ##print "last:", branches_taken[-1]
  
      if ins.isCall():
	pass
        ##if str(ins.branchs[0]) == "0x8048890":
          ##branches_taken.append("exit")
          ##break
      
        ##if str(ins.branchs[0]) == "0x8048800":
          ##branches_taken.append("__stack_chk_fail")
          ##break
    
      elif ins.isCJmp():
        count = count + 1
        i = self.select(seq, map(str, ins.branchs))
        
        #print i,
        
        if i == None:
	  return seq
        
        if i == 0:
          seq.append(str(self.program.selectFalseBranch()))
        elif i == 1:
          seq.append(str(self.program.selectTrueBranch()))
        else:
	  assert(False)
	
	if seq[-1] == "end":
	  break
        
    
    return seq
    #return branches_taken
"""


def generatePaths(program, start, end, n):

  random_paths = ManualPathGenerator(program, start, set([end]))
  epsilon = dict()#list()
  rand_count = 0
  gen_count = 0
  path_set = set()
  #csv_writer = csv.writer(open('loop_bad_impos.csv', 'wb'))

  for (i,(path, labels)) in enumerate(random_paths):
    
    path.reset()
    trace = mkTrace(path, [], False)
    path.reset()
    fvars, sol = getPathConditions(trace, False)

    if sol <> None:
      print "SAT!"
      for var in fvars:
        print "sol["+str(var)+"] =", sol[var]
    else:
      print "UNSAT!"
      #if not (str(labels) in path_set):
      #  path_set.add(str(labels))
      #  csv_writer.writerow(labels)
      #  print labels
        
    #if (i==1000):
    #  break
  """
  assert(0) 
  print float(rand_count)/10000
  
  #print epsilon
  
  gen_paths = EXISTPathGenerator(program, start, set(), epsilon.values())
  paths = []
  
  
  
  for (i,path) in enumerate(gen_paths):
    
    
    (x,y,z) = detectFeasible(path)
    
    
    #paths.append((path,(x > 0 and 2*x == y and z == 1)))
    
    
    if ((x > 0 and 2*x == y and z == 1)):
      gen_count = gen_count + 1
    
    #print paths[-1]
    #if :
      
    
    
    if (i==10000):
      break
  
  #print paths
  print float(gen_count)/10000
  """
      


########NEW FILE########
__FILENAME__ = Prelude
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

from core        import *
from Inputs      import parse_inputs
from Memory      import MemAccess
from Parameters  import FuncParameters
from Callstack   import Callstack
from Allocation  import Allocation
from Lifting     import *


def mkTrace(path, raw_inputs, debug = False):
    
    if debug:
      print "Loading trace.."
    
    inputs = parse_inputs(raw_inputs)
    
    #if (raw_inputs <> []):
    #  print "Using these inputs.."
    
    #  for op in Inputs:
    #    print op,"=", Inputs[op]
    if debug:
      print "Detecting callstack layout..."
    callstack = Callstack(path)#, Inputs) #TODO: it should recieve inputs also!
    
    if debug:
      print callstack
    
    allocationLog = Allocation()
    memAccess = MemAccess()
    funcParameters = FuncParameters()
    
    path_size = len(path)
    
    # we reset path iterator and callstack
    path.reset()
    callstack.reset()
    
    #print "Detecting memory accesses and function parameters.."
  
    for ins in path:
      
      counter = ins.getCounter()
      callstack.nextInstruction(ins)
      #print ins,counter
      if ins.isReadWrite():
        memAccess.detectMemAccess(path[0:counter+1], callstack, inputs, counter)
        #AllocationLog.check(MemAccess.getAccess(end), end)
        
      elif ins.isCall() and ins.called_function <> None:
        funcParameters.detectFuncParameters(path[0:counter+1], memAccess, callstack, inputs, counter)
        #if (ins.called_function == "malloc"):
          
          #try:
            #size = int(FuncParameters.getParameters(end)[0][1].name)
          #except ValueError:
            #size = None
          #AllocationLog.alloc(ins.address, end, size)
        #elif (ins.called_function == "free"):
          #ptr = (FuncParameters.getParameters(end)[0][1].mem_source)
          #AllocationLog.free(ptr, end)
    
    if debug:      
      print memAccess
      print funcParameters
      allocationLog.report()
    
    callstack.reset()
    path.reset()
    
    # trace definition
    trace = dict()
    trace["code"] = path
    trace["initial_conditions"] = inputs
    trace["final_conditions"] = dict()
    trace["callstack"] = callstack
    trace["mem_access"] = memAccess
    trace["func_parameters"] = funcParameters
    
    return trace

    

########NEW FILE########
__FILENAME__ = SMT
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

from src.core import *
import z3

class SMT:

  def __init__(self):
    self.solver = z3.Solver()
    self.solver.set(unsat_core=True)
    self.m = None
  
  def add(self, cs):
    for c in cs:
      c = z3.simplify(c)
      #print c
      #if (self.c <= self.max_c):
      self.solver.assert_and_track(c, str(c))
      #self.solver.add(c)

      #self.c = self.c + 1

  def solve(self, debug = False):

    #if debug:
    #  print self.solver
    
    if (self.solver.check() == z3.sat):
      self.m = self.solver.model()
    elif debug:
      print "unsat core:"
      print self.solver.unsat_core()
  
  def is_sat(self):

    #if not (self.solver.check() == z3.sat):
    #  print self.solver.unsat_core()

    return (self.solver.check() == z3.sat)
      
  def getValue(self, op):
    assert(self.m <> None)
    
    if (op |iss| RegOp):
      var = map(lambda b: z3.BitVec(str(b),8), op.getLocations())
      var = map(lambda b: self.m[b], var)
      if (len(var) > 1):
        return z3.simplify(z3.Concat(var)).as_signed_long()
      else:
        return z3.simplify(var[0]).as_signed_long()
    elif (op.isMem()):
      array = z3.Array(op.name, z3.BitVecSort(16), z3.BitVecSort(8))
      f = self.m[array]
      
      #print self.m
      
      es = f.as_list()[:-1]

      var = []
      
      for loc in op.getLocations():
        byte = None
        for entry in es:
          #print entry
          if loc.getIndex() == entry[0].as_signed_long():
            byte = entry[1]#.as_signed_long()
            break
        
        if (byte == None):
          byte = f.else_value()
          
        var.append(byte)
        
      var.reverse()
      
      if (len(var) > 1):  
        return z3.simplify(z3.Concat(var)).as_signed_long()
      else:
        return z3.simplify(var[0]).as_signed_long()
    else:
      assert(0)


  def write_sol_file(self,filename):
    solf = open(filename, 'w')
    if (self.solver.check() == z3.sat):
      self.m = self.solver.model()
      for d in self.m.decls():
        solf.write("%s = %s\n" % (d.name(), self.m[d])) 
    else:
      solf.write("unsat")
      uc = self.solver.unsat_core()
      for c in uc:
        solf.write(c.sexpr())
      
    solf.close()

  def write_smtlib_file(self,filename):
    smtlibf = open(filename, 'w')
    smtlibf.write(self.solver.sexpr())
    smtlibf.close()
    
    
class Solution:
  def __init__(self, model):
    self.m = model
    #self.vars = dict()
    #self.fvars = set(fvars)
    #for d in self.m.decls():
    #  self.vars[d.name()] = d

  def __getitem__(self, op):
    
    if (op |iss| InputOp):
      r = ""
      for loc in op.getLocations():
        var = z3.BitVec(str(loc),8)
        var = self.m[var]
	r = r +("\\x%.2x" % var.as_long())
      return r

    if (op |iss| RegOp):
      var = map(lambda b: z3.BitVec(str(b),8), op.getLocations())
      var = map(lambda b: self.m[b], var)
      if (len(var) > 1):
        return z3.simplify(z3.Concat(var)).as_signed_long()
      else:
        return z3.simplify(var[0]).as_signed_long()
    elif (op.isMem()):
      array = z3.Array(op.name, z3.BitVecSort(16), z3.BitVecSort(8))
      f = self.m[array]
      
      #print self.m
      
      es = f.as_list()[:-1]

      var = []
      
      for loc in op.getLocations():
        byte = None
        for entry in es:
          #print entry
          if loc.getIndex() == entry[0].as_signed_long():
            byte = entry[1]#.as_signed_long()
            break
        
        if (byte == None):
          byte = f.else_value()
          
        var.append(byte)
      r = "" 
      for v in var:
	r = r +("\\x%.2x" % v.as_long())

      return r


      #var.reverse()
      
      #if (len(var) > 1):  
      #  return z3.simplify(z3.Concat(var)).as_signed_long()
      #else:
      #  return z3.simplify(var[0]).as_signed_long()
    else:
      assert(0)



    r = []
    for loc in i.getLocations():
      r.append(self.vars[str(loc)])
    return r
  """
  def __contains__(self, var):
    #print var
    #print filter(lambda v: var in v, self.vars.keys())
    return filter(lambda v: var in v, self.vars.keys()) <> []
  
  def getString(self, var, escape = False):
    
    if ":" in var:
      r = ""
      i = 0
      while ((var + str(i)+"(0)") in self.vars.keys()):
        d = self.vars[var + str(i)+"(0)"]
        if (escape):
          r = r+"\\"+str(int(self.m[d].as_long()))
        else:
          r = r+chr(int(self.m[d].as_long()))
        i = i + 1
      return r
    
  def dump(self, name, input_vars):
    dumped = []
    for var in input_vars:
      if var in self:
        filename = (var+"."+name+".out").replace(":", "")
        out = open(filename, 'w')
        out.write(self.getString(var))
        dumped.append(filename)
    return dumped
  """

########NEW FILE########
__FILENAME__ = SSA
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""
from core import *

class SSA:
  def __init__(self):
    self.regs = dict()
    
  def __contains__(self, op):
    return str(op) in self.regs
  
  def getMap(self, read_ops, write_ops, other_ops):
    d = dict()
    
    read_ops  = filter(lambda o: not o.isMem(), read_ops)
    write_ops = filter(lambda o: not o.isMem(), write_ops)
    other_ops = filter(lambda o: not o.isMem(), other_ops)

    #print self.regs

    for op in read_ops:
      d[str(op)] = self.renameReadOperand(op)

    for op in write_ops:
      d[str(op)] = self.renameWriteOperand(op)

    for op in other_ops:
      if (str(op) in self.regs):
        d[str(op)] = self.renameWriteOperand(op)
      else:
        op_ren = op.copy()
        op_ren.name = op_ren.name+"_0"
        d[str(op)] = op_ren
        

    #print regs
    #print d
  
    return d
  
  def renameReadOperand(self, op):
  
    #if not op.is_reg:
    #  return op.copy()  
  
    if not (str(op) in self.regs):
      self.regs[str(op)] = -1
  
    self.regs[str(op)] = self.regs[str(op)] + 1
    op_ren = op.copy()
    op_ren.name = str(op)+"_"+str(self.regs[str(op)]) 

    return op_ren


  def renameWriteOperand(self, op):
  
    #if not op.is_reg:
    #  return op.copy()    
  
    op_ren = op.copy()
    op_ren.name = str(op)+"_"+str(self.regs[str(op)]) 

    return op_ren

########NEW FILE########
__FILENAME__ = TypeSlicer
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

concatSet = lambda l: reduce(set.union, l, set())
concatList = lambda l: reduce(lambda a,b: a+b, l, [])

from core        import *
from Common      import getValueFromCode


def typeLocs(ins, callstack, tlocs):
  
  def detectStackChange(loc, sloc):
    
    i = ins.getCounter()
    
    print loc,loc.type
    
    #if (loc.type <> None):
    #  print loc.type.index
   
    if i > 0 and ins.instruction == "call" and ins.called_function == None and \
       ("SPtr32" in str(loc.type)) and loc.index >= 8:
      #assert(0)
      callstack.prevInstruction(ins)
      
      einfo = dict()
      einfo["source.name"] = hex(callstack.currentCall())
      einfo["source.index"] = callstack.currentCounter()
      
      index = (loc.index)+callstack.currentStackDiff()
      cloc = MemLoc(loc.name,index) 
      cloc.type = Type("SPtr32", loc.type.index, einfo)
      
      sloc.discard(loc)
      sloc.add(cloc)
      
      callstack.nextInstruction(ins)
      
  def detectMainParameters(loc, sloc):
    
    #i = ins.getCounter()
    #if i > 0:
    #  return
    


    if ("argv" in str(loc)):
      #print "ENTRE", str(loc)
      #assert(0) 
      #einfo = dict()
      #einfo["source.name"] = "argc"
      #einfo["source.index"] = 0
      sloc.discard(loc)
      sloc.add(loc.getType())

    #elif ("SPtr32" in str(loc.type)) and \
    #   loc.index >= 12 and loc.index < 16:
      
    #  einfo = dict()
    #  einfo["source.name"] = "argv[]"
    #  einfo["source.index"] = 0
    #  sloc.discard(loc)
    #  sloc.add(Type("Ptr32", loc.index-12, einfo))

    #elif ("Ptr32" in str(loc.type)) and \
    #   "argv[]" in str(loc):
      
      #print loc
      #print loc.index % 4
      #assert(0)

    #  einfo = dict()
    #  einfo["source.name"] = "argv[" +str(loc.index / 4)+"]"
    #  einfo["source.index"] = 0
    #  sloc.discard(loc)
    #  sloc.add(Type("Ptr32", loc.index % 4, einfo))

      #print "ENTRE:", Type("Ptr32", loc.index-12, einfo)

  
  def detectStackPtr(loc, sloc):
    
    if loc.name in ["esp","ebp"] and \
       ins.instruction == "call" and ins.called_function == None:
      
      einfo = dict()
      einfo["source.name"] = hex(callstack.currentCall())
      einfo["source.index"] = callstack.currentCounter()
      sloc.discard(loc)
      sloc.add(Type("SPtr32", loc.index, einfo))
  
  def detectHeapPtr(loc, sloc):
    #print loc.name
    if loc.name in ["eax"] and \
       ins.instruction == "call" and ins.called_function == "malloc":
     
      #assert(0)
      einfo = dict()
      einfo["source.name"] = ins.address
      einfo["source.index"] = ins.getCounter()
      sloc.discard(loc)
      sloc.add(Type("HPtr32", loc.index, einfo))
  
  
  def detectImm(loc, sloc):
    
    if loc |iss| ImmLoc:
      sloc.discard(loc)
      sloc.add(Type("Data32", loc.index))
    
  
  for sloc in tlocs:
    
    for loc in list(sloc):
      
      if (loc |iss| Location):
        
        detectMainParameters(loc, sloc)
        detectImm(loc, sloc)
        #detectStackChange(loc, sloc)
        detectStackPtr(loc, sloc)
        detectHeapPtr(loc, sloc)
         
def checkType(tlocs):
  pt_name = tlocs[0].name
  einfo  = tlocs[0].einfo
  
  #FIXME: improve type detection
  if (all(map(lambda pt: pt.name == pt_name, tlocs))):
    return Type(pt_name, None, einfo)
    
  assert(False)
    
  
def trackLocs(ins, tlocs, read_ops, write_ops):
  
  if len(write_ops) > 1:
    assert(0)
  else:
    write_locs = write_ops[0].getLocations()
  
  for sloc in tlocs:
    
    for (i,wloc) in enumerate(write_locs):
      if (wloc in sloc):
	sloc.discard(wloc)
	
	for op in read_ops:  
	  read_locs = op.getLocations()
	  sloc.add(read_locs[i])

def getType(inss, callstack, memory, op, initial_type):
  
  #print inss.first, inss.last
  #print inss[-2] 
  #print "-----------------------------------------------------------"
  assert(len(inss) > 0)
  
  if (op |iss| ImmOp):
    return Type("Data32", None)
  
  if (op |iss| AddrOp):
    return Type("Ptr32", None)
  
  #print "hola"
  # code should be copied and reversed
  inss.reverse()
  
  index = callstack.index

  # we will track op
  mlocs = set(op.getLocations())
  
  tlocs = range(op.getSizeInBytes())
  for (i,loc) in enumerate(op.getLocations()):
    
    pt = Type(initial_type.name, i)
    tlocs[i] = set([loc, pt])
  
  for ins in inss:
       
    counter = ins.getCounter()
    
    if memory.getAccess(counter) <> None:
      ins.setMemoryAccess(memory.getAccess(counter))

    #print ins.getCounter(), str(ins)

    ins_write_vars = map(lambda op: set(op.getLocations()), ins.getWriteVarOperands())
    write_locs = concatSet(ins_write_vars)
    
    ins_read_vars  = map(lambda op: set(op.getLocations()), ins.getReadVarOperands())
    read_locs  = concatSet(ins_read_vars)
    
    #for loc in mlocs:
    #  print loc, "::", loc.type, "--",
    
    #if (len(mlocs) > 0):
    #  print "\n"
    
     
    #for loc in write_locs:
    #  print loc, "::", loc.type, "--",
    
    #if (len(mlocs) > 0):
    #  print "\n"
 
    typeLocs(ins, callstack, tlocs)
    
    if len(write_locs.intersection(mlocs)) > 0: 
      
      trackLocs(ins, tlocs, ins.getReadOperands(), ins.getWriteOperands())
      
      
      mlocs = mlocs.difference(write_locs) 
      mlocs = read_locs.union(mlocs)
    
    callstack.prevInstruction(ins)
  
  callstack.index = index
  #print "finally:"
  for (i,s) in enumerate(tlocs):
    
    #for loc in tlocs[i]:
    #  print loc, "-",
    #print "xxx"
    tlocs[i] = joinset(s)
    
  return checkType(tlocs)

def getTypedValue(inss, callstack, memory, op, initial_type):
  
  rtype = getType(inss, callstack, memory, op, initial_type)
  
  # we reset the path
  inss.reverse()
  inss.reset()
    
  val = getValueFromCode(inss, callstack, dict(), memory, op)

  if ("SPtr32" in str(rtype)) and val >= 12:
   
    einfo = dict()
    einfo["source.name"] = "argv[]"
    einfo["source.index"] = 0
    rtype.setInfo(einfo)
    val = val - 12

  elif ("argv[]" in str(rtype)):
    
    einfo = dict()
    einfo["source.name"] = "argv["+str(val/4)+"]"
    einfo["source.index"] = 0
    rtype.setInfo(einfo)
    val = val % 4

  elif "Ptr32" == str(rtype):
    rtype = Type("GPtr32", None)
    
    einfo = dict()
    einfo["source.name"] = "0x00000000"
    einfo["source.index"] = 0
    rtype.setInfo(einfo)

  return (val, rtype)


########NEW FILE########
__FILENAME__ = Typing
"""
    This file is part of SEA.

    SEA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SEA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SEA.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 by neuromancer
"""

from core import *
from Condition   import *

def getInitialConditionsArgs(callstack):
  
  initial_values_at_call = dict()
  
  name = hex(callstack.currentCall())
  
  einfo = dict() 
  einfo["source.name"]=name
  einfo["source.index"]=callstack.currentCounter()
  
  arg_v = MemOp(name,"DWORD", offset=12)
  arg_v.type = Type("Ptr32",None, einfo=einfo)
  
  initial_values_at_call[arg_v] = ImmOp(str(0), "DWORD")
  
  einfo = dict() 
  einfo["source.name"]="argv[]"
  einfo["source.index"]=0
  
  arg_v = MemOp(name,"DWORD")
  arg_v.type = Type("SPtr32",None, einfo=einfo)
  
  initial_values_at_call[arg_v] = ImmOp(str(0), "DWORD")

  
  return initial_values_at_call


def getInitialConditionsCall(callstack):
  
  initial_values_at_call = dict()
  
  if callstack.index == 1:
    esp_val = 4
    
    #for i in range(0,40):
      #arg_i = Operand("argv[]@"+str(i),"BYTE", mem_source = "argv[]", mem_offset=i)
      #initial_values_at_call[arg_i] = Operand(str(0), "BYTE")
    
    #print ""
  else:
    esp_val = 8
 
  ebp_val = 0
  
  esp_op = RegOp("esp","DWORD")
  ebp_op = RegOp("ebp","DWORD")
  
  
  initial_values_at_call[esp_op] = ImmOp(str(esp_val), "DWORD")
  initial_values_at_call[ebp_op] = ImmOp(str(ebp_val), "DWORD")
  
  return initial_values_at_call

def getInitialConditionsAlloc():
  ret_op = RegOp("eax","DWORD")
  ret_val = 0
  initial_values_at_alloc = dict()
  initial_values_at_alloc[ret_op] = ImmOp(str(ret_val), "DWORD")
  
  return initial_values_at_alloc

def setInitialConditions(ssa, initial_values, smt_conds):
  ssa_map = ssa.getMap(set(), set(), set(initial_values.keys()))
  eq = Eq(None, None)
  
  for iop in initial_values:
    
    #if ":" in iop.name:
    #  smt_conds.add(eq.getEq(iop,initial_values[iop]))
    if (iop |iss| RegOp):
      #assert(0)
      #print eq.getEq(ssa_map[iop.name],initial_values[iop]), "-"
      smt_conds.add(eq.getEq(ssa_map[iop.name],initial_values[iop]))
    elif (iop.isMem()):
      smt_conds.add(eq.getEq(iop,initial_values[iop]))
    else:
      assert(False)

#def detectType(mvars, ins, counter, callstack):
  
  #if (len(mvars) == 0):
    #return None
  
  ## dection of parameters of main
  
  #name = "s."+hex(callstack.callstack[1])+".1"
  
  ## argv
  #argv_bytes = []
  
  #for i in range(12,16):
    #argv_bytes.append(Operand(name+"@"+str(i),"BYTE"))
  
  #argv_bytes = set(argv_bytes) 
  
  
  #if argv_bytes.issubset(mvars):
    #return "argv[]"
  
  ### argc
  ##argc_bytes = []
  ##
  ##for i in range(8,12):
  ##  argc_bytes.append(Operand(name+"@"+str(i),"BYTE"))
  ##
  ##argc_bytes = set(argv_bytes) 
  ##
  ##if argc_bytes.issubset(mvars):
  ##  return "argc"
  
  ## argv[0], argv[1], ... argv[10]
  #for i in range(0,40,4):
    #op = Operand("argv[]@"+str(i),"BYTE")
    #if op in mvars:
      #return "arg["+str(i / 4)+"]"
  
  #if ins.isCall() and ins.called_function == "malloc":
    
    ## heap pointers
    #if set([Operand("eax","DWORD")]).issubset(mvars):
      #return "h."+"0x"+ins.address+"."+str(counter)
  
  #elif ins.isCall() and ins.called_function == None:
    
    ## stack pointers
    #if mvars.issubset(set([Operand("esp", "DWORD"), Operand("ebp", "DWORD")])):
      #return "s."+hex(callstack.currentCall())+"."+str(callstack.currentCounter())

  ## No type deduced
  #return None 

#def mkVal(val_type,val):
  #if val_type == "imm":
    #return Operand(str(val), "")
  #elif "s." in val_type or "h." in val_type or "arg" in val_type:
    #return Operand(val_type+"@"+str(val), "", mem_source = val_type, mem_offset=val)
  #else:
    #assert(0)

def removeTrack(ops, mvars, mlocs):

  for op in ops:
    mvars.remove(op)
  
    for loc in op.getLocations():
      mlocs.remove(loc)
    
def addAditionalConditions(mvars, mlocs, ins, ssa, callstack, smt_conds):
  
  if len(mvars) == 0:
    return mvars
  
  # auxiliary eq condition
  eq = Eq(None, None)
  
 
    #name = hex(callstack.currentCall())
    #for i in range(12,16):
      
      #argv_bytes.append(MemOp(name+"@"+str(i),"BYTE"))
  
  # if the instruction was a call
  if ins.isCall() and ins.called_function == "malloc":

    if (RegOp("eax","DWORD") in mvars):
      initial_values_at_alloc = getInitialConditionsAlloc()
      setInitialConditions(ssa, initial_values_at_alloc, smt_conds)
      removeTrack([RegOp("eax","DWORD")], mvars, mlocs)
      #mvars.remove(RegOp("eax","DWORD"))
      
  elif ins.isCall() and ins.called_function == None:
    initial_values_at_call = getInitialConditionsCall(callstack)
      
    
    for iop in initial_values_at_call.keys():
      #print "iop:",iop
      if not (iop in mvars):  
        del initial_values_at_call[iop]
      
      
    setInitialConditions(ssa, initial_values_at_call, smt_conds)
    removeTrack(initial_values_at_call.keys(), mvars, mlocs)
    
    if (ins.getCounter() == 0):
    
      initial_values = getInitialConditionsArgs(callstack)
      setInitialConditions(ssa, initial_values, smt_conds)
    
    #mvars = set(filter(lambda o: not (o in initial_values_at_call.keys()), mvars))
    
    
      
    #new_mvars = set()
    #for v in mvars:
      ## we convert stack memory variables from one frame to the previous one
      #if callstack.currentCounter()>1 and v.isStackMem() and v.mem_offset >= 4: 
        #eop = callstack.convertStackMemOp(v)
        #smt_conds.add(eq.getEq(v,eop))
        #new_mvars.add(eop)
      #else:
        #new_mvars.add(v)
      
    #mvars = set(filter(lambda o: not (o.isStackMem() and o.mem_offset >= 4), mvars))
    #mvars = mvars.union(new_mvars)
  
  return mvars
  

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/python
import os
import sys
import cgi
import Cookie
import applogic
import traceback

## Parse the query string, cookie
query = cgi.parse()
cookie = Cookie.SimpleCookie()
if not (os.getenv("HTTP_COOKIE") is None):
    cookie.load(os.getenv("HTTP_COOKIE"))

try:
    body = applogic.run(query, cookie)
except:
    body = "<H1>Exception</H1>\n" + \
	   "<PRE>\n" + \
	   traceback.format_exc() + \
	   "</PRE>\n";

## Use sys.stdout.write to ensure correct CRLF endings
sys.stdout.write("HTTP 200 OK\r\n")
cookiestr = cookie.output()
if cookiestr != "":
    sys.stdout.write(cookiestr + "\r\n")

sys.stdout.write("Content-Type: text/html\r\n")
sys.stdout.write("\r\n")
sys.stdout.write(body)


########NEW FILE########
__FILENAME__ = applogic
import sys
import os
import datetime

def run(query, cookie):
    return """\
		<H1>Hello world.</H1>
		This is a trivial web application.
		"""


########NEW FILE########
__FILENAME__ = exploit-template
#!/usr/bin/python
import sys
import socket
import traceback

####

def build_exploit(shellcode):
    req =   "GET / HTTP/1.0\r\n" + \
	    "\r\n"
    return req

####

def send_req(host, port, req):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Connecting to %s:%d..." % (host, port))
    sock.connect((host, port))

    print("Connected, sending request...")
    sock.send(req)

    print("Request sent, waiting for reply...")
    rbuf = sock.recv(1024)
    resp = ""
    while len(rbuf):
	resp = resp + rbuf
	rbuf = sock.recv(1024)

    print("Received reply.")
    sock.close()
    return resp

####

if len(sys.argv) != 3:
    print("Usage: " + sys.argv[0] + " host port")
    exit()

try:
    shellfile = open("shellcode.bin", "r")
    shellcode = shellfile.read()
    req = build_exploit(shellcode)
    print("HTTP request:")
    print(req)

    resp = send_req(sys.argv[1], int(sys.argv[2]), req)
    print("HTTP response:")
    print(resp)
except:
    print("Exception:")
    print(traceback.format_exc())


########NEW FILE########
__FILENAME__ = loop_bad
#!/usr/bin/gdb -x

import sys
import gdb
import random

#def parse_jmp_addr(raw_ins):
#  jmp = raw_ins.split("\n")[1].split("\t")[1].split("<")[0]
#  addr = jmp.split(" ")[-2]

#  return addr

def getRandomData(values, size):
  data = ""
  value_size = len(values)
  for i in range(size):
    data = data + values[random.randint(0,value_size-1)]

  return data

def setData(data, data_addr, size, size_addr):

  assert(len(data) == size)
  gdb.execute("set *(int*) ("+size_addr+") = (int) "+str(size)) #

  for i in range(size):
    #print "set *(char*) ("+data_addr+"+"+str(i)+") = (char) "+str(ord(data[i]))
    gdb.execute("set *(char*) ("+data_addr+"+"+str(i)+") = (char) "+str(ord(data[i])))


def getPath(data, size):
  
  was_jmp = False
  r = []
  gdb.execute("start", to_string=True)  

  # set initial conditions

  for i in range(0,10): # wait for 10 instructions
    gdb.execute("si", to_string=True)

  setData(data,"$ebp-29", size, "$ebp-48")
  while (True):
  
    gdb.execute("si", to_string=True)
    addr = str(gdb.parse_and_eval("$eip")).split(" ")[0]
    #addr = gdb.parse_and_eval("$eip")

    raw_ins = gdb.execute("disassemble $eip,+1", to_string=True)
    raw_ins = str(raw_ins)
 
    if was_jmp:
      #print "hola!"
      r.append(addr)#, addr == jmp_addr
      was_jmp = False

    #print str(raw_ins)
    if ("j" in raw_ins) and not ("jmp" in raw_ins):
      was_jmp = True
      #jmp_addr = parse_jmp_addr(raw_ins)
    elif ("call" in str(raw_ins)):
      break
    elif ("ret" in str(raw_ins)):
      break

  return r

import csv
import random

with open('loop_bad.csv', 'wb') as csvfile:
  pathwriter = csv.writer(csvfile)
  path_set = set()
  for i in range(100): 
    for size in range(2,11):
      #print "size:", i
      path = getPath(getRandomData([".","\n"], size), size)
      path_str = str(path)

      if not (path_str in path_set):
        pathwriter.writerow(path)
        path_set.add(path_str)
      

gdb.execute("quit", to_string=True)

########NEW FILE########
