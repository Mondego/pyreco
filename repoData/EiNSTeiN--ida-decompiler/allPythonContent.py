__FILENAME__ = callconv
""" Abstracts the logic behind figuring out the arguments to a function call.

http://en.wikipedia.org/wiki/X86_calling_conventions
"""

from expressions import *

class calling_convention(object):
    pass

class systemv_x64_abi(calling_convention):
    """ SystemV AMD64 ABI
    
    The following registers are used to pass arguments: 
        RDI, RSI, RDX, RCX, R8, R9, XMM0-7
    """
    
    def __init__(self):
        
        
        return
    
    def make_call_arguments(self, regs):
        
        if len(regs) == 0:
            return None
        
        regs = regs[:]
        
        arglist = regs.pop(-1)
        while len(regs) > 0:
            arglist = comma_t(regs.pop(-1), arglist)
        
        return arglist
    
    def process(self, flow, block, stmt, call, context):
        
        #~ print 'call', str(call)
        #~ print 'live registers:', repr([str(r) for r, _ in context.context])
        
        # RDI, RSI, RDX, RCX, R8, R9
        which = [7, 6, 2, 1, 8, 9]
        regs = []
        for n in which:
            _pair = context.get_definition(regloc_t(n))
            if not _pair:
                break
            regs.append(_pair[0].copy())
            context.remove_definition(_pair[0])
        
        params = self.make_call_arguments(regs)
        call.params = params
        
        return
    
    def process_stack(self, flow, block, stmt, call, context):
        
        return

class stdcall(calling_convention):
    """ merge the last few stack assignements to function arguments list.
    """
    
    def __init__(self):
        
        return
    
    def make_call_arguments(self, regs):
        
        if len(regs) == 0:
            return None
        
        regs = regs[:]
        
        arglist = regs.pop(-1)
        while len(regs) > 0:
            arglist = comma_t(regs.pop(-1), arglist)
        
        return arglist
    
    def process_stack(self, flow, block, stmt, call, context):
        # `context`: a list of assignment statements
        
        print 'call', str(call)
        #~ print 'live registers:', repr([str(i) for i in context])
        
        for assign in reversed(context):
            expr = assign.expr
            if type(expr) != assign_t:
                continue
            var = expr.op1
            if type(var) != var_t:
                continue
            loc = var.where
            if flow.arch.is_stackvar(loc):
                print str(loc), str(assign)
        
        #~ regs = []
        #~ for n in which:
            #~ _pair = context.get_definition(regloc_t(n))
            #~ if not _pair:
                #~ break
            #~ regs.append(_pair[0].copy())
            #~ context.remove_definition(_pair[0])
        
        #~ params = self.make_call_arguments(regs)
        #~ call.params = params
        
        return
    
    def process(self, flow, block, stmt, call, context):
        
        #~ print 'call', str(call)
        #~ print 'live registers:', repr([str(r[0]) for r in context.map])
        
        #~ regs = []
        #~ for n in which:
            #~ _pair = context.get_definition(regloc_t(n))
            #~ if not _pair:
                #~ break
            #~ regs.append(_pair[0].copy())
            #~ context.remove_definition(_pair[0])
        
        #~ params = self.make_call_arguments(regs)
        #~ call.params = params
        
        return


########NEW FILE########
__FILENAME__ = decompiler

import flow
import ssa

from statements import *
from expressions import *

import filters.simplify_expressions
import callconv

import host, host.dis

class instance_t(object):
    """ an instance of a register (either use or definition). """
    
    def __init__(self, block, stmt, reg):
        
        self.block = block
        self.stmt = stmt
        self.reg = reg
        
        return
    
    def __eq__(self, other):
        return other.block == self.block and other.stmt == self.stmt and \
                other.reg == self.reg

class chain_t(object):
    """ this object holds all instances of a single register. those 
    instances can be definitions or uses. a register is 'defined' 
    when it appears on the left side of an assing_t expression, 
    such as 'eax = 0' except if it is part of another construct, 
    such that '*(eax) = 0' does not constitute a definition of 
    eax but a use of eax.
    """
    
    def __init__(self, flow, defreg):
        
        self.flow = flow
        self.defreg = defreg
        self.instances = []
        
        return
    
    def __repr__(self):
        s = '<chain %s: %s>' % (str(self.defreg), repr([str(i.stmt) for i in self.instances]))
        return s
    
    def new_instance(self, instance):
        #~ if instance in self.instances:
            #~ return
        self.instances.append(instance)
        return
    
    @property
    def defines(self):
        return [instance for instance in self.instances if instance.reg.is_def]
    
    @property
    def uses(self):
        return [instance for instance in self.instances if not instance.reg.is_def]
    
    def all_same_definitions(self):
        """ return True if all definitions of this chain are the exact
            same expression. """
        
        defines = self.defines
        first = defines[0]
        for define in defines[1:]:
            if define.stmt.expr == first.stmt.expr:
                continue
            return False
        return True
    
# what are we collecting now
COLLECT_REGISTERS = 1
COLLECT_FLAGS = 2
COLLECT_ARGUMENTS = 4
COLLECT_VARIABLES = 8
COLLECT_DEREFS = 16
COLLECT_ALL = COLLECT_REGISTERS | COLLECT_FLAGS | COLLECT_ARGUMENTS | \
                COLLECT_VARIABLES | COLLECT_DEREFS

PROPAGATE_ANY = 1 # any expression
PROPAGATE_STACK_LOCATIONS = 2 # only stack locations
PROPAGATE_REGISTERS = 4 # only register locations.
PROPAGATE_FLAGS = 8 # only flagloc_t

# if set, propagate only definitions with a single use. otherwise,
# expressions with multiple uses can be propagated (this is 
# necessary for propagating stack variables, for example)
PROPAGATE_SINGLE_USES = 512

class simplifier(object):
    """ this class is used to make transformations on the code flow, 
    such as replacing uses by their definitions, removing restored
    registers, etc. """
    
    def __init__(self, flow, flags):
        
        self.flow = flow
        self.flags = flags
        
        self.done_blocks = []
        
        self.return_chains = {}
        
        return
    
    def should_collect(self, expr):
        if not isinstance(expr, assignable_t):
            return False
        
        if self.flags & COLLECT_REGISTERS and type(expr) == regloc_t:
            return True
        if self.flags & COLLECT_FLAGS and type(expr) == flagloc_t:
            return True
        if self.flags & COLLECT_ARGUMENTS and type(expr) == arg_t:
            return True
        if self.flags & COLLECT_VARIABLES and type(expr) == var_t:
            return True
        if self.flags & COLLECT_DEREFS and type(expr) == deref_t:
            return True
        
        return False
    
    def find_reg_chain(self, chains, reg):
        """ find the chain that matches this exact register. """
        
        for chain in chains:
            if chain.defreg == reg:
                return chain
        
        return
    
    def get_statement_chains(self, block, stmt, chains):
        """ given a statement, collect all registers that appear 
            in it and stuff them in their respective chains. """
        
        for _stmt in stmt.statements:
            self.get_statement_chains(block, _stmt, chains)
        
        if type(stmt) == goto_t and type(stmt.expr) == value_t:
            
            ea = stmt.expr.value
            _block = self.flow.blocks[ea]
            
            self.get_block_chains(_block, chains)
            return
        
        regs = [reg for reg in stmt.expr.iteroperands() if self.should_collect(reg)]
        
        for reg in regs:
            chain = self.find_reg_chain(chains, reg)
            if not chain:
                chain = chain_t(self.flow, reg)
                chains.append(chain)
            instance = instance_t(block, stmt, reg)
            chain.new_instance(instance)
        
        if type(stmt) == return_t:
            self.return_chains[block] = chains[:]
        
        return
    
    def get_block_chains(self, block, chains):
        """ iterate over a block and build chains. """
        
        if block in self.done_blocks:
            return
        
        self.done_blocks.append(block)
        
        for stmt in list(block.container.statements):
            self.get_statement_chains(block, stmt, chains)
        
        return
    
    def get_chains(self):
        """ return a list of all chains that should be collected 
            according to the 'flags' given. """
        
        self.done_blocks = []
        chains = []
        self.get_block_chains(self.flow.entry_block, chains)
        
        return chains
    
    def can_propagate(self, chain, flags):
        """ return True if this chain can be propagated. """
        
        defines = chain.defines
        uses = chain.uses
        
        # prevent removing anything without uses during propagation. we'll do it later.
        if len(uses) == 0 or len(defines) == 0:
            return False
        
        # no matter what, we cannot propagate if there is more than 
        # one definition for this chain with the exception where all 
        # the definitions are the same.
        if len(defines) > 1 and not chain.all_same_definitions():
            return False
        
        definstance = defines[0]
        stmt = definstance.stmt
        if type(stmt.expr) != assign_t:
            # this is not possible in theory.
            return False
        
        # get the target of the assignement.
        value = stmt.expr.op2
        
        # never propagate function call if it has more than one use...
        if type(value) == call_t and len(uses) > 1:
            return False
        
        # prevent multiplying statements if they have more than one use.
        # this should be the subject of a more elaborate algorithm in order
        # to propagate simple expressions whenever possible but limit
        # expression complexity at the same time.
        
        if type(stmt.expr.op1) == regloc_t:
            return True
        
        if len(uses) > 1 and (flags & PROPAGATE_SINGLE_USES) != 0:
            return False
        
        if (flags & PROPAGATE_ANY):
            return True
        
        if self.flow.arch.is_stackvar(value) and (flags & PROPAGATE_STACK_LOCATIONS):
            return True
        
        if type(value) == regloc_t and (flags & PROPAGATE_REGISTERS):
            return True
        
        if type(value) == flagloc_t and (flags & PROPAGATE_FLAGS):
            return True
        
        return False
    
    def propagate(self, chains, chain):
        """ take all uses and replace them by the right side of the definition.
        returns True if the propagation was successful. """
        
        defines = chain.defines
        
        definstance = defines[0]
        stmt = definstance.stmt
        
        # get the target of the assignement.
        value = stmt.expr.op2
        
        ret = False
        
        for useinstance in list(chain.uses):
            _stmt = useinstance.stmt
            _index = _stmt.index()
            
            # check if the instance can be propagated. the logic is to avoid
            # propagating past a redefinition of anything that is used in this 
            # statement. eg. in the series of statements 'y = x; x = 1; z = y;' 
            # the 'y' assignement cannot be propagated because of the assignement
            # to 'x' later.
            right_uses = [reg for reg in value.iteroperands() if self.should_collect(reg)]
            prevent = False
            for reg in right_uses:
                
                other_chain = self.find_reg_chain(chains, reg)
                if not other_chain:
                        continue
                for inst in other_chain.instances:
                    if not inst.stmt.container:
                        continue
                    #~ if inst.reg.is_def:
                        #~ print 'is def', str(inst.reg)
                    if inst.stmt.index() > _index:
                        continue
                    if inst.reg.is_def and inst.stmt.index() > stmt.index():
                        prevent = True
                        break
            
            if prevent:
                print 'prevent...', str(stmt), 'into', str(_stmt)
                continue
            
            useinstance.reg.replace(value.copy())
            
            chain.instances.remove(useinstance)
            filters.simplify_expressions.run(_stmt.expr, deep=True)
            
            # handle special case where statement is simplified into itself
            if type(_stmt.expr) == assign_t and _stmt.expr.op1 == _stmt.expr.op2:
                _stmt.remove()
            
            ret = True
        
        # if definition was propagated fully, then remove its definition statement
        if len(chain.uses) == 0:
            for define in defines:
                define.stmt.remove()
            chains.remove(chain)
        
        return ret

    def propagate_all(self, flags):
        """ collect all chains in this function flow, then propagate 
            them if possible. """
        
        while True:
            redo = False
            
            chains = self.get_chains()
            
            for chain in chains:
                
                if not self.can_propagate(chain, flags):
                    continue
                
                redo = self.propagate(chains, chain) or redo
            
            if not redo:
                break
        
        return
    
    def remove_unused_definitions(self):
        """ Remove definitions that don't have any uses.
            Do it recursively, because as we remove some, others may becomes
            unused.
        """
        
        while True:
            redo = False
            
            chains = self.get_chains()
            for chain in chains:
                
                if len(chain.uses) > 0:
                    continue
                
                for instance in chain.defines:
                    
                    stmt = instance.stmt
                    
                    if type(stmt.expr) == call_t:
                        # do not eliminate calls
                        continue
                    elif type(stmt.expr) == assign_t and type(stmt.expr.op2) == call_t:
                        # simplify 'reg = call()' form if reg is a register and is no longer used.
                        if type(stmt.expr.op1) == regloc_t:
                            stmt.expr = stmt.expr.op2
                        continue
                    
                    # otherwise remove the statement
                    stmt.remove()
                    
                    redo = True
            
            if not redo:
                break
        
        return
    
    def process_restores(self):
        """ we try to find chains for any 'x' that has a single 
        definition of the style 'x = y' and where all uses are 
        of the style 'y = x' and y is either a stack location 
        or the same register (not taking the index into account).
        
        one further condition is that all definitions of 'y' have
        no uses and be live at the return statement.
        """
        
        #~ print 'at restore'
        chains = self.get_chains()
        
        restored_regs = []
        #~ print repr(chains)
        
        for chain in chains:
            defs = chain.defines
            uses = chain.uses
            
            if len(defs) != 1 or len(uses) == 0:
                continue
            
            defstmt = defs[0].stmt
            if type(defstmt.expr) != assign_t:
                continue
            
            def_chain = self.find_reg_chain(chains, defstmt.expr.op2)
            if not def_chain or len(def_chain.uses) != 1:
                continue
            
            defreg = def_chain.defreg
            
            all_restored = True
            
            for use in uses:
                
                if type(use.stmt.expr) != assign_t:
                    all_restored = False
                    break
                
                usechain = self.find_reg_chain(chains, use.stmt.expr.op1)
                if not usechain or len(usechain.defines) != 1:
                    all_restored = False
                    break
                
                reg = usechain.defines[0].reg
                if type(defreg) != type(reg):
                    all_restored = False
                    break
                
                if type(reg) == regloc_t and (reg.which != defreg.which):
                    all_restored = False
                    break
                    
                if type(reg) != regloc_t and (reg != defreg):
                    all_restored = False
                    break
            
            if all_restored:
                #~ print 'restored', str(defreg)
                
                # pop all statements in which the restored location appears
                for inst in chain.instances:
                    inst.stmt.remove()
                
                reg = defreg.copy()
                reg.index = None
                restored_regs.append(reg)
        
        print 'restored regs', repr([str(r) for r in restored_regs])
        
        return restored_regs
    
    class arg_collector(object):
        
        def __init__(self, flow, conv, chains):
            self.flow = flow
            self.conv = conv
            self.chains = chains
            return
            
        def iter(self, block, container, stmt):
            
            if type(stmt.expr) == call_t:
                call = stmt.expr
            
            elif type(stmt.expr) == assign_t and type(stmt.expr.op2) == call_t:
                call = stmt.expr.op2
            
            else:
                return
            
            live = []
            
            for chain in self.chains:
                for instance in chain.instances:
                    inst_index = instance.stmt.index()
                    if instance.stmt.container != container:
                        continue
                    if inst_index >= stmt.index():
                        continue
                    if instance.reg.is_def:
                        live.append(instance.stmt)
            
            self.conv.process_stack(self.flow, block, stmt, call, live)
            
            return
    
    def collect_argument_calls(self, conv):
        
        chains = self.get_chains()
        c = self.arg_collector(self.flow, conv, chains)
        iter = flow_iterator(self.flow, statement_iterator=c.iter)
        iter.do()
        
        return
    
    def glue_increments_collect(self, block, container):
        """ for a statement, get all registers that appear in it. """
        
        chains = []
        
        for stmt in container.statements:
            regs = [reg for reg in stmt.expr.iteroperands() if self.should_collect(reg)]
            
            for reg in regs:
                chain = self.find_reg_chain(chains, reg)
                if not chain:
                    chain = chain_t(self.flow, reg)
                    chains.append(chain)
                instance = instance_t(block, stmt, reg)
                chain.new_instance(instance)
        
        #~ print 'current', str(block)
        
        while True:
            
            redo = False
            
            # now for each chain, check if they contain increments
            for chain in chains:
                
                continuous = []
                
                i = 0
                while i < len(chain.instances):
                    
                    all = []
                    j = i
                    while True:
                        if j >= len(chain.instances):
                            break
                        
                        next = chain.instances[j]
                        #~ next_index = next.stmt.index()
                        #~ print 'b', str(next.stmt)
                        
                        if len([a for a in all if a.stmt == next.stmt]) > 0:
                            j += 1
                            continue
                        
                        #~ if last_index + 1 != next_index:
                            #~ break
                        
                        if not self.is_increment(chain.defreg, next.stmt.expr) or \
                                not next.reg.is_def:
                            break
                        
                        #~ last_index = next_index
                        all.append(next)
                        j += 1
                    
                    if len(all) == 0:
                        i += 1
                        continue
                    
                    #~ j += 1
                    if j < len(chain.instances):
                        next = chain.instances[j]
                        #~ next_index = next.stmt.index()
                        #~ if last_index + 1 == next_index:
                        all.append(next)
                    
                    if i > 0:
                        this = chain.instances[i-1]
                        if not this.reg.is_def:
                            #~ i = chain.instances.index(this)
                            expr = this.stmt.expr
                            #~ last_index = this.stmt.index()
                            #~ print 'a', str(expr)
                            
                            all.insert(0, this)
                    continuous.append(all)
                    
                    i = j
                
                #~ for array in continuous:
                    #~ print 'continuous statements:'
                    #~ for instance in array:
                        #~ print '->', str(instance.stmt)
                
                # at this point we are guaranteed to have a list with possibly 
                # a statement at the beginning, one or more increments in the 
                # middle, and possibly another statement at the end.
                
                for array in continuous:
                    pre = array.pop(0) if not self.is_increment(chain.defreg, array[0].stmt.expr) else None
                    post = array.pop(-1) if not self.is_increment(chain.defreg, array[-1].stmt.expr) else None
                    
                    if pre:
                        instances = self.get_nonincrements_instances(pre.stmt.expr, chain.defreg)
                        
                        #~ print 'a', repr([str(reg) for reg in instances])
                        while len(instances) > 0 and len(array) > 0:
                            increment = array.pop(0)
                            cls = postinc_t if type(increment.stmt.expr.op2) == add_t else postdec_t
                            instance = instances.pop(-1)
                            #~ pre.stmt.expr = self.merge_increments(pre.stmt.expr, instance, cls)
                            instance.replace(cls(instance.copy()))
                            increment.stmt.remove()
                            chain.instances.remove(increment)
                    
                    if post:
                        instances = self.get_nonincrements_instances(post.stmt.expr, chain.defreg)
                        
                        #~ print 'b', repr([str(reg) for reg in instances])
                        while len(instances) > 0 and len(array) > 0:
                            increment = array.pop(0)
                            cls = preinc_t if type(increment.stmt.expr.op2) == add_t else predec_t
                            instance = instances.pop(-1)
                            #~ post.stmt.expr = self.merge_increments(post.stmt.expr, instance, cls)
                            instance.replace(cls(instance.copy()))
                            increment.stmt.remove()
                            chain.instances.remove(increment)
            
            if not redo:
                break
        
        return
    
    def get_nonincrements_instances(self, expr, defreg):
        """ get instances of 'reg' that are not already surrounded by an increment or decrement """
        
        instances = [reg for reg in expr.iteroperands() if reg == defreg]
        increments = [reg for reg in expr.iteroperands() if type(reg) in (preinc_t, postinc_t, predec_t, postdec_t)]
        
        real_instances = []
        for instance in instances:
            found = False
            for increment in increments:
                if increment.op is instance:
                    found = True
                    break
            if not found:
                real_instances.append(instance)
        
        return real_instances
    
    def is_increment(self, what, expr):
        return (type(expr) == assign_t and type(expr.op2) in (add_t, sub_t) and \
                    type(expr.op2.op2) == value_t and expr.op2.op2.value == 1 and \
                    expr.op1 == expr.op2.op1 and expr.op1 == what)
    
    def glue_increments(self):
        
        iter = flow_iterator(self.flow, container_iterator=self.glue_increments_collect)
        iter.do()
        
        return

class flow_iterator(object):
    """ Helper class for iterating a flow_t object.
    
    The following callbacks can be used:
        block_iterator(block_t)
        container_iterator(block_t, container_t)
        statement_iterator(block_t, container_t, statement_t)
        expression_iterator(block_t, container_t, statement_t, expr_t)
    
    any callback can return False to stop the iteration.
    """
    
    def __init__(self, flow, **kwargs):
        self.flow = flow
        
        self.block_iterator = kwargs.get('block_iterator')
        self.container_iterator = kwargs.get('container_iterator')
        self.statement_iterator = kwargs.get('statement_iterator')
        self.expression_iterator = kwargs.get('expression_iterator')
        
        return
    
    def do_expression(self, block, container, stmt, expr):
        
        r = self.expression_iterator(block, container, stmt, expr)
        if r is False:
            # stop iterating.
            return False
        
        if isinstance(expr, expr_t):
            for i in range(len(expr)):
                r = self.do_expression(block, container, stmt, expr[i])
                if r is False:
                    # stop iterating.
                    return False
        
        return
    
    def do_statement(self, block, container, stmt):
        
        if self.statement_iterator:
            r = self.statement_iterator(block, container, stmt)
            if r is False:
                # stop iterating.
                return
        
        if self.expression_iterator and stmt.expr is not None:
            r = self.do_expression(block, container, stmt, stmt.expr)
            if r is False:
                # stop iterating.
                return False
        
        if type(stmt) == goto_t and type(stmt.expr) == value_t:
            block = self.flow.get_block(stmt)
            self.do_block(block)
            return
        
        for _container in stmt.containers:
            r = self.do_container(block, _container)
            if r is False:
                # stop iterating.
                return False
        
        return
    
    def do_container(self, block, container):
        
        if self.container_iterator:
            r = self.container_iterator(block, container)
            if r is False:
                return
        
        for stmt in container.statements:
            r = self.do_statement(block, container, stmt)
            if r is False:
                # stop iterating.
                return False
        
        return
    
    def do_block(self, block):
        
        if block in self.done_blocks:
            return
        
        self.done_blocks.append(block)
        
        if self.block_iterator:
            r = self.block_iterator(block)
            if r is False:
                # stop iterating.
                return False
        
        r = self.do_container(block, block.container)
        if r is False:
            # stop iterating.
            return False
        
        return
    
    def do(self):
        
        self.done_blocks = []
        block = self.flow.entry_block
        self.do_block(block)
        
        return

RENAME_STACK_LOCATIONS = 1
RENAME_REGISTERS = 2

class renamer(object):
    """ this class takes care of renaming variables. stack locations and 
    registers are wrapped in var_t and arg_t if they are respectively 
    local variables or function arguments.
    """
    
    varn = 0
    argn = 0
    
    def __init__(self, flow, flags):
        self.flow = flow
        self.flags = flags
        
        self.reg_arguments = {}
        self.reg_variables = {}
        #~ self.stack_arguments = {}
        self.stack_variables = {}
        
        return
    
    def stack_variable(self, expr):
        
        assert self.flow.arch.is_stackvar(expr)
        
        if type(expr) == regloc_t and self.flow.arch.is_stackreg(expr):
            index = 0
        else:
            index = -(expr.op2.value)
        
        if index in self.stack_variables:
            return self.stack_variables[index].copy()
        
        var = var_t(expr.copy())
        var.name = 's%u' % (renamer.varn, )
        renamer.varn += 1
        
        self.stack_variables[index] = var
        
        return var
    
    def reg_variable(self, expr):
        
        assert type(expr) == regloc_t
        
        for reg in self.reg_variables:
            if reg == expr:
                return self.reg_variables[reg].copy()
        
        var = var_t(expr)
        self.reg_variables[expr] = var
        
        var.name = 'v%u' % (renamer.varn, )
        renamer.varn += 1
        
        return var
    
    def reg_argument(self, expr):
        
        assert type(expr) == regloc_t
        
        for reg in self.reg_arguments:
            if reg == expr:
                return self.reg_arguments[reg].copy()
        
        arg = arg_t(expr)
        self.reg_arguments[expr] = arg
        
        name = 'a%u' % (renamer.argn, )
        arg.name = name
        renamer.argn += 1
        
        return arg
    
    def rename_variables_callback(self, block, container, stmt, expr):
        
        if self.flags & RENAME_STACK_LOCATIONS:
            # stack variable value
            if type(expr) == deref_t and self.flow.arch.is_stackvar(expr.op):
                var = self.stack_variable(expr.op.copy())
                expr.replace(var)
                return
        
            # stack variable address
            if self.flow.arch.is_stackvar(expr):
                var = self.stack_variable(expr.copy())
                expr.replace(address_t(var))
                return 
        
        if self.flags & RENAME_REGISTERS:
            if type(expr) == regloc_t and expr in self.fct_arguments:
                arg = self.reg_argument(expr.copy())
                expr.replace(arg)
                return
            
            if type(expr) == regloc_t:
                var = self.reg_variable(expr.copy())
                expr.replace(var)
                return
        
        return
    
    def wrap_variables(self):
        iter = flow_iterator(self.flow, expression_iterator = self.rename_variables_callback)
        iter.do()
        return

STEP_NONE = 0                   # flow_t is empty
STEP_BASIC_BLOCKS_FOUND = 1     # flow_t contains only basic block information
STEP_IR_DONE = 2                # flow_t contains the intermediate representation
STEP_SSA_DONE = 3               # flow_t contains the ssa form
STEP_CALLS_DONE = 4             # call information has been applied to function flow
STEP_PROPAGATED = 5             # assignments have been fully propagated
STEP_PRUNED = 6                 # dead code has been pruned
STEP_COMBINED = 7               # basic blocks have been combined together

STEP_DECOMPILED=STEP_COMBINED   # last step

class decompiler_t(object):
    
    def __init__(self, ea):
        self.ea = ea
        self.disasm = host.dis.disassembler_factory()
        self.current_step = None
        return
    
    def step_until(self, stop_step):
        """ decompile until the given step. """
        
        for step in self.step():
            if step >= stop_step:
                break
        
        return
    
    def steps(self):
        """ this is a generator function which yeilds the last decompilation step
            which was performed. the caller can then observe the function flow. """
        
        self.flow = flow.flow_t(self.ea, self.disasm)
        self.current_step = STEP_NONE
        yield self.current_step
        
        self.flow.find_control_flow()
        self.current_step = STEP_BASIC_BLOCKS_FOUND
        yield self.current_step
        
        self.flow.transform_ir()
        self.current_step = STEP_IR_DONE
        yield self.current_step
        
        # tag all registers so that each instance of a register can be uniquely identified.
        t = ssa.ssa_tagger_t(self.flow)
        t.tag()
        self.current_step = STEP_SSA_DONE
        yield self.current_step
        
        
        
        
        #~ yield STEP_CALLS_DONE
        #~ yield STEP_PROPAGATED
        #~ yield STEP_PRUNED
        #~ yield STEP_COMBINED
        
        
        
        
        #~ # After registers are tagged, we can replace their uses by their definitions. this 
        #~ # takes care of eliminating any instances of 'esp' which clears the way for 
        #~ # determining stack variables correctly.
        #~ s = simplifier(f, COLLECT_ALL)
        #~ s.propagate_all(PROPAGATE_STACK_LOCATIONS)
        
        #~ # remove special flags (eflags) definitions that are not used, just for clarity
        #~ s = simplifier(f, COLLECT_FLAGS)
        #~ s.remove_unused_definitions()
        
        #~ s = simplifier(f, COLLECT_REGISTERS)
        #~ s.remove_unused_definitions()
        
        #~ # rename stack variables to differentiate them from other dereferences.
        #~ r = renamer(f, RENAME_STACK_LOCATIONS)
        #~ r.wrap_variables()
        
        #~ # collect function arguments that are passed on the stack
        #~ s = simplifier(f, COLLECT_ALL)
        #~ s.collect_argument_calls(conv)
        
        #~ # This propagates special flags.
        #~ s = simplifier(f, COLLECT_ALL)
        #~ s.propagate_all(PROPAGATE_REGISTERS | PROPAGATE_FLAGS)
        
        #~ # At this point we must take care of removing increments and decrements
        #~ # that are in their own statements and "glue" them to an adjacent use of 
        #~ # that location.
        #~ s = simplifier(f, COLLECT_ALL)
        #~ s.glue_increments()
        
        #~ # re-propagate after gluing pre/post increments
        #~ s = simplifier(f, COLLECT_ALL)
        #~ s.propagate_all(PROPAGATE_REGISTERS | PROPAGATE_FLAGS)
        
        #~ s = simplifier(f, COLLECT_ALL)
        #~ s.propagate_all(PROPAGATE_ANY | PROPAGATE_SINGLE_USES)
        
        #~ # eliminate restored registers. during this pass, the simplifier also collects 
        #~ # stack variables because registers may be preserved on the stack.
        #~ s = simplifier(f, COLLECT_REGISTERS | COLLECT_VARIABLES)
        #~ s.process_restores()
        #~ # ONLY after processing restores can we do this; any variable which is assigned
        #~ # and never used again is removed as dead code.
        #~ s = simplifier(f, COLLECT_REGISTERS)
        #~ s.remove_unused_definitions()
        
        #~ # rename registers to pretty names.
        #~ r = renamer(f, RENAME_REGISTERS)
        #~ r.fct_arguments = t.fct_arguments
        #~ r.wrap_variables()
        
        #~ # after everything is propagated, we can combine blocks!
        #~ f.combine_blocks()
        
        #~ print '----2----'
        #~ print print_function(arch, f)
        #~ print '----2----'
        
        return


########NEW FILE########
__FILENAME__ = decompiler_gui
import host.ui

if __name__ == '__main__':
    
    host.ui.main.show_decompiler()

########NEW FILE########
__FILENAME__ = expressions

class assignable_t(object):
    """ any object that can be assigned.
    
    They include: regloc_t, var_t, arg_t, deref_t.
    """
    
    def __init__(self, index):
        self.index = index
        self.is_def = False
        return

class replaceable_t(object):
    """ abstracts the logic behind tracking an object's parent so the object
        can be replaced without knowing in advance what its parent it, with
        a reference to only the object itself.
        
        an example of replacing an operand:
        
            loc = regloc_t(0) # eax
            e = add_t(value(1), loc) # e contains '1 + eax'
            loc.replace(value(8)) # now e contains '1 + 8'
        
        this doesn't work when comes the time to 'wrap' an operand into another,
        because checks are made to ensure an operand is added to _only_ one 
        parent expression at a time. the operand can be copied, however:
        
            loc = regloc_t(0) # eax
            e = add_t(value(1), loc) # e contains '1 + eax'
            # the following line wouldn't work:
            loc.replace(deref_t(loc))
            # but this one would:
            loc.replace(deref_t(loc.copy()))
        
        """
    
    def __init__(self):
        self.__parent = None
        return
    
    @property
    def parent(self):
        return self.__parent
    
    @parent.setter
    def parent(self, parent):
        assert type(parent) in (tuple, type(None))
        self.__parent = parent
        return
    
    def replace(self, new):
        """ replace this object in the parent's operands list for a new object
            and return the old object (which is a reference to 'self'). """
        assert isinstance(new, replaceable_t), 'new object is not replaceable'
        if self.__parent is None:
            return
        assert self.__parent is not None, 'cannot replace when parent is None in %s by %s' % (repr(self), repr(new))
        k = self.__parent[1]
        old = self.__parent[0][k]
        assert old is self, "parent operand should have been this object ?!"
        self.parent[0][k] = new
        old.parent = None # unlink the old parent to maintain consistency.
        return old

class regloc_t(assignable_t, replaceable_t):
    
    def __init__(self, which, size, name=None, index=None):
        """  Register location
        
        `which`: index of the register
        `size`: size in bits (8, 16, 32, etc...)
        `name`: name of the register (a string that doesn't mean anything except for display)
        `index`: index of the register, assigned after tagging.
        """
        
        assignable_t.__init__(self, index)
        replaceable_t.__init__(self)
        
        self.which = which
        self.size = size
        self.name = name
        
        return
    
    def copy(self):
        return self.__class__(self.which, size=self.size, name=self.name, index=self.index)
    
    def __eq__(self, other):
        return type(other) == type(self) and self.which == other.which and \
                self.index == other.index
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def no_index_eq(self, other):
        return type(other) == type(self) and self.which == other.which
    
    def __repr__(self):
        if self.name:
            name = self.name
        else:
            name = '#%u' % (self.which, )
        
        if self.index is not None:
            name += '@%u' % self.index
        
        return '<reg %s>' % (name, )
    
    def iteroperands(self):
        yield self
        return

class flagloc_t(regloc_t):
    """ a special flag, which can be anything, depending on the 
        architecture. for example the eflags status bits in intel 
        assembly. """
    pass

class value_t(replaceable_t):
    """ any literal value """
    
    def __init__(self, value, size):
        """ A literal value
        
        `value`: a literal value
        `size`: size in bits (8, 16, 32, etc...)
        """
        
        replaceable_t.__init__(self)
        
        self.value = value
        self.size = size
        return
    
    def copy(self):
        return value_t(self.value, self.size)
    
    def __eq__(self, other):
        return type(other) == value_t and self.value == other.value
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __repr__(self):
        return '<value %u>' % self.value
    
    def iteroperands(self):
        yield self
        return

class var_t(assignable_t, replaceable_t):
    """ a local variable to a function """
    
    def __init__(self, where, name=None):
        """  A local variable.
        
        `where`: the location where the value of this variable is stored.
        `name`: the variable name
        """
        
        assignable_t.__init__(self, None)
        replaceable_t.__init__(self)
        
        self.where = where
        #~ self.size = size
        self.name = name or str(self.where)
        return
    
    def copy(self):
        return var_t(self.where.copy(), name=self.name)
    
    def __eq__(self, other):
        return (type(other) == var_t and self.where == other.where)
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __repr__(self):
        return '<var %s>' % self.name
    
    def iteroperands(self):
        yield self
        return

class arg_t(assignable_t, replaceable_t):
    """ a function argument """
    
    def __init__(self, where, name=None):
        """  A local argument.
        
        `where`: the location where the value of this argument is stored.
        `name`: the argument name
        """
        
        assignable_t.__init__(self, None)
        replaceable_t.__init__(self)
        
        self.where = where
        #~ self.size = size
        self.name = name or str(self.where)
        
        return
    
    def copy(self):
        return arg_t(self.where.copy(), self.name)
    
    def __eq__(self, other):
        return (type(other) == arg_t and self.where == other.where)
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __repr__(self):
        return '<arg %s>' % self.name
    
    def iteroperands(self):
        yield self
        return

class expr_t(replaceable_t):
    
    def __init__(self, *operands):
        
        replaceable_t.__init__(self)
        
        self.__operands = [None for i in operands]
        for i in range(len(operands)):
            self[i] = operands[i]
        
        return
    
    def __getitem__(self, key):
        return self.__operands[key]
    
    def __setitem__(self, key, value):
        if value is not None:
            assert isinstance(value, replaceable_t), 'operand is not replaceable'
            assert value.parent is None, 'operand %s already has a parent? tried to assign into #%s of %s' % (value.__class__.__name__, str(key), self.__class__.__name__)
            value.parent = (self, key)
        self.__operands[key] = value
        return
    
    def __len__(self):
        return len(self.__operands)
    
    @property
    def operands(self):
        for op in self.__operands:
            yield op
        return
    
    def iteroperands(self):
        """ iterate over all operands, depth first, left to right """
        
        for o in self.__operands:
            if not o:
                continue
            for _o in o.iteroperands():
                yield _o
        yield self
        return

class call_t(expr_t):
    def __init__(self, fct, params):
        expr_t.__init__(self, fct, params)
        return
    
    @property
    def fct(self): return self[0]
    
    @fct.setter
    def fct(self, value): self[0] = value
    
    @property
    def params(self): return self[1]
    
    @params.setter
    def params(self, value): self[1] = value
    
    def __repr__(self):
        return '<call %s %s>' % (repr(self.fct), repr(self.params))
    
    def copy(self):
        return call_t(self.fct.copy(), self.params.copy() if self.params else None)


# #####
# Unary expressions (two operands)
# #####

class uexpr_t(expr_t):
    """ base class for unary expressions """
    
    def __init__(self, operator, op):
        self.operator = operator
        expr_t.__init__(self, op)
        return
    
    def copy(self):
        return self.__class__(self.op.copy())
    
    @property
    def op(self): return self[0]
    
    @op.setter
    def op(self, value): self[0] = value
    
    def __eq__(self, other):
        return isinstance(other, uexpr_t) and self.operator == other.operator \
            and self.op == other.op
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self.operator, repr(self.op))

class not_t(uexpr_t):
    """ bitwise NOT operator. """
    
    def __init__(self, op):
        uexpr_t.__init__(self, '~', op)
        return

class b_not_t(uexpr_t):
    """ boolean negation of operand. """
    
    def __init__(self, op):
        uexpr_t.__init__(self, '!', op)
        return

class deref_t(uexpr_t, assignable_t):
    """ indicate dereferencing of a pointer to a memory location. """
    
    def __init__(self, op, size, index=None):
        assignable_t.__init__(self, index)
        uexpr_t.__init__(self, '*', op)
        self.size = size
        return
    
    def __eq__(self, other):
        return isinstance(other, uexpr_t) and self.operator == other.operator \
            and self.op == other.op and self.index == other.index
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def copy(self):
        return self.__class__(self.op.copy(), self.size, self.index)
    
    def no_index_eq(self, other):
        return isinstance(other, uexpr_t) and self.operator == other.operator \
            and self.op == other.op

class address_t(uexpr_t):
    """ indicate the address of the given expression (& unary operator). """
    
    def __init__(self, op):
        uexpr_t.__init__(self, '&', op)
        return

class neg_t(uexpr_t):
    """ equivalent to -(op). """
    
    def __init__(self, op):
        uexpr_t.__init__(self, '-', op)
        return

class preinc_t(uexpr_t):
    """ pre-increment (++i). """
    
    def __init__(self, op):
        uexpr_t.__init__(self, '++', op)
        return

class predec_t(uexpr_t):
    """ pre-decrement (--i). """
    
    def __init__(self, op):
        uexpr_t.__init__(self, '--', op)
        return

class postinc_t(uexpr_t):
    """ post-increment (i++). """
    
    def __init__(self, op):
        uexpr_t.__init__(self, '++', op)
        return

class postdec_t(uexpr_t):
    """ post-decrement (i--). """
    
    def __init__(self, op):
        uexpr_t.__init__(self, '--', op)
        return


# #####
# Binary expressions (two operands)
# #####

class bexpr_t(expr_t):
    """ "normal" binary expression. """
    
    def __init__(self, op1, operator, op2):
        self.operator = operator
        expr_t.__init__(self, op1, op2)
        return
    
    @property
    def op1(self): return self[0]
    
    @op1.setter
    def op1(self, value): self[0] = value
    
    @property
    def op2(self): return self[1]
    
    @op2.setter
    def op2(self, value): self[1] = value
    
    def __eq__(self, other):
        return isinstance(other, bexpr_t) and self.operator == other.operator and \
                self.op1 == other.op1 and self.op2 == other.op2
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __repr__(self):
        return '<%s %s %s %s>' % (self.__class__.__name__, repr(self.op1), \
                self.operator, repr(self.op2))

class comma_t(bexpr_t):
    
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, ',', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class assign_t(bexpr_t):
    """ represent the initialization of a location to a particular expression. """
    
    def __init__(self, op1, op2):
        """ op1: the location being initialized. op2: the value it is initialized to. """
        assert isinstance(op1, assignable_t), 'left side of assign_t is not assignable'
        bexpr_t.__init__(self, op1, '=', op2)
        op1.is_def = True
        return
    
    def __setitem__(self, key, value):
        if key == 0:
            assert isinstance(value, assignable_t), 'left side of assign_t is not assignable: %s (to %s)' % (str(value), str(self))
            value.is_def = True
        bexpr_t.__setitem__(self, key, value)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class add_t(bexpr_t):
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '+', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())
    
    def add(self, other):
        if type(other) == value_t:
            self.op2.value += other.value
            return
        
        raise RuntimeError('cannot add %s' % type(other))
    
    def sub(self, other):
        if type(other) == value_t:
            self.op2.value -= other.value
            return
        
        raise RuntimeError('cannot sub %s' % type(other))

class sub_t(bexpr_t):
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '-', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())
    
    def add(self, other):
        if other.__class__ == value_t:
            self.op2.value -= other.value
            return
        
        raise RuntimeError('cannot add %s' % type(other))
    
    def sub(self, other):
        if other.__class__ == value_t:
            self.op2.value += other.value
            return
        
        raise RuntimeError('cannot sub %s' % type(other))

class mul_t(bexpr_t):
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '*', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class div_t(bexpr_t):
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '/', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class shl_t(bexpr_t):
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '<<', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class shr_t(bexpr_t):
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '>>', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class xor_t(bexpr_t):
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '^', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class and_t(bexpr_t):
    """ bitwise and (&) operator """
    
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '&', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class or_t(bexpr_t):
    """ bitwise or (|) operator """
    
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '|', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

# #####
# Boolean equality/inequality operators
# #####

class b_and_t(bexpr_t):
    """ boolean and (&&) operator """
    
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '&&', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class b_or_t(bexpr_t):
    """ boolean and (||) operator """
    
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '||', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class eq_t(bexpr_t):
    
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '==', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class neq_t(bexpr_t):
    
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '!=', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class leq_t(bexpr_t):
    
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '<=', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class aeq_t(bexpr_t):
    
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '>=', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class lower_t(bexpr_t):
    
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '<', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

class above_t(bexpr_t):
    
    def __init__(self, op1, op2):
        bexpr_t.__init__(self, op1, '>', op2)
        return
    
    def copy(self):
        return self.__class__(self.op1.copy(), self.op2.copy())

# #####
# Ternary expressions (three operands)
# #####

class texpr_t(expr_t):
    """ ternary expression. """
    
    def __init__(self, op1, operator1, op2, operator2, op3):
        self.operator1 = operator1
        self.operator2 = operator2
        expr_t.__init__(self, op1, op2, op3)
        return
    
    @property
    def op1(self): return self[0]
    
    @op1.setter
    def op1(self, value): self[0] = value
    
    @property
    def op2(self): return self[1]
    
    @op2.setter
    def op2(self, value): self[1] = value
    
    @property
    def op3(self): return self[2]
    
    @op3.setter
    def op3(self, value): self[2] = value
    
    def __eq__(self, other):
        return isinstance(other, texpr_t) and \
                self.operator1 == other.operator1 and self.operator2 == other.operator2 and \
                self.op1 == other.op1 and self.op2 == other.op2 and self.op3 == other.op3
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __repr__(self):
        return '<%s %s %s %s %s %s>' % (self.__class__.__name__, repr(self.op1), \
                self.operator1, repr(self.op2), self.operator2, repr(self.op3))

class ternary_if_t(texpr_t):
    
    def __init__(self, cond, then, _else):
        texpr_t.__init__(self, cond, '?', then, ':', _else)
        return

# #####
# Special operators that define the value of some of the eflag bits.
# #####

class sign_t(uexpr_t):
    
    def __init__(self, op):
        uexpr_t.__init__(self, '<sign of>', op)
        return

class overflow_t(uexpr_t):
    
    def __init__(self, op):
        uexpr_t.__init__(self, '<overflow of>', op)
        return

class parity_t(uexpr_t):
    
    def __init__(self, op):
        uexpr_t.__init__(self, '<parity>', op)
        return

class adjust_t(uexpr_t):
    
    def __init__(self, op):
        uexpr_t.__init__(self, '<adjust>', op)
        return

class carry_t(uexpr_t):
    
    def __init__(self, op):
        uexpr_t.__init__(self, '<carry>', op)
        return


########NEW FILE########
__FILENAME__ = controlflow
""" Control flow simplification algorithms.

This file contains algorithms for transforming the control flow into the most
readable form possible.

When the run() routine is called, the control flow is mostly flat, and
consist mostly of normal statements, conditional jump statements of the form
'if(...) goto ...' and unconditional jump statements of the form 'goto ...' 
(without preceding condition). Most of the work done here is applying simple
algorithms to eliminate goto statements.
"""

import simplify_expressions

from expressions import *
from statements import *

__block_filters__ = [] # filters that are applied to a flow block
__container_filters__ = [] # filters that are applied to a container (i.e. inside a then-branch of an if_t)

def is_if_block(block):
    """ return True if the last statement in a block is a goto 
        statement and the next-to-last statement is a if_t and 
        the if_t also contains a goto as last statement. """
    
    if len(block.container) < 2:
        return False
    
    stmt = block.container[-2]
    goto = block.container[-1]
    
    if type(stmt) == if_t and type(goto) == goto_t and \
            len(stmt.then_expr) == 1 and not stmt.else_expr and \
            type(stmt.then_expr[0]) == goto_t:
        return True
    
    return False

def invert_goto_condition(block):
    """ invert the goto at the end of a block for the goto in 
        the if_t preceding it """
    
    stmt = block.container[-2]
    stmt.then_expr[0], block.container[-1] = block.container[-1], stmt.then_expr[0]
    
    stmt.expr = b_not_t(stmt.expr.copy())
    simplify_expressions.run(stmt.expr, deep=True)
    
    return

def combine_if_blocks(flow, this, next):
    """ combine two if_t that jump to the same destination into a boolean or expression. """
    
    left = [this.container[-1].expr.value, this.container[-2].then_expr[0].expr.value]
    right = [next.container[-1].expr.value, next.container[-2].then_expr[0].expr.value]
    
    dest = list(set(left).intersection(set(right)))
    
    if len(dest) == 1:
        # both blocks have one jump in common.
        dest = dest[0]
        
        if this.container[-1].expr.value == dest:
            invert_goto_condition(this)
        
        if next.container[-1].expr.value == dest:
            invert_goto_condition(next)
        
        other = flow.blocks[next.container[-1].expr.value]
        
        if other == this:
            cls = b_and_t
        else:
            cls = b_or_t
        
        stmt = this.container[-2]
        stmt.expr = cls(stmt.expr.copy(), next.container[-2].expr.copy())
        simplify_expressions.run(stmt.expr, deep=True)
        
        this.jump_to.remove(next)
        next.jump_from.remove(this)
        flow.blocks[dest].jump_from.remove(next)
        
        other.jump_from.remove(next)
        
        if other != this:
            other.jump_from.append(this)
            this.jump_to.append(other)
        this.container[-1] = next.container[-1]
        
        return True
    
    return False

def combine_conditions(flow, block):
    """ combine two ifs into a boolean or (||) or a boolean and (&&). """
    
    if not is_if_block(block):
        return False
    
    for next in block.jump_to:
        if not is_if_block(next) or len(next.container) != 2:
            continue
        
        if combine_if_blocks(flow, block, next):
            return True
    
    return False
__block_filters__.append(combine_conditions)


class loop_paths_t(object):
    
    def __init__(self, flow, block):
        self.flow = flow
        self.paths = []
        self.origin = block
        self.find_all_recursion_paths(block, [block, ])
        return
    
    def is_recursive(self):
        return len(self.paths) > 0
    
    def all_blocks(self):
        return list(set([b for p in self.paths for b in p]))
    
    def can_jump_to(self, block, dstblock):
        
        container = block.container
        if type(container[-1]) != goto_t:
            return False
        
        if container[-1].expr.value == dstblock.ea:
            return True
        
        if type(container[-2]) == if_t and \
                len(container[-2].then_expr) == 1 and \
                type(container[-2].then_expr[0]) == goto_t and \
                container[-2].then_expr[0].expr.value == dstblock.ea:
            return True
        
        return False
    
    def find_all_recursion_paths(self, block, curpath):
        
        for dest in block.jump_to:
            if not self.can_jump_to(block, dest):
                continue
            
            if self.origin == dest:
                self.paths.append(curpath[:])
                continue
            
            #~ if len(dest.jump_from) > 1:
                #~ good = False
                #~ for src in dest.jump_from:
                    #~ if len([p for p in self.paths if src in p]) > 0:
                        #~ good=True
                #~ if not good:
                #~ continue
            
            if dest in curpath:
                # destination is in current path..
                continue
            
            self.find_all_recursion_paths(dest, curpath[:] + [dest, ])
        
        return
    
    def longest_path(self):
        
        if len(self.paths) == 0:
            return
        
        #~ print 'paths'
        maxlen = len(self.paths[0])
        chosen = None
        
        #~ print 'path', repr([hex(b.ea) for b in chosen])
        for p in self.paths:
            #~ if len([b for b in p if len(b.jump_from) > 1]) != 0:
                #~ continue
            if p[0] == self.origin and (not chosen or len(p) > maxlen):
                maxlen = len(p)
                chosen = p
            #~ print 'path', repr([hex(b.ea) for b in p])
        
        assert chosen and chosen[0] == self.origin
        
        return chosen[:]
    
    def is_same_loop(self, path):
        for _path in self.paths:
            if sorted(path[:]) == sorted(_path[:]):
                return True
        return False
    
    def remove_same_paths(self, other):
        for path in self.paths[:]:
            if other.is_same_loop(path):
                self.paths.remove(path)
        return

def switch_goto_if_needed(block, dstblock):
    """ if the last item at the end of 'block' is a goto to dstblock, do nothing,
        otherwise invert that goto with the one in the if_t in the next-to-last
        position. """
    
    container = block.container
    assert type(container[-1]) == goto_t
    
    if container[-1].expr.value == dstblock.ea:
        return
    
    if len(container) < 2:
        return
    
    assert type(container[-2]) == if_t
    assert len(container[-2].then_expr) == 1
    assert type(container[-2].then_expr[0]) == goto_t
    assert container[-2].then_expr[0].expr.value == dstblock.ea
    
    # invert goto_t destinations
    container[-1].expr.value, container[-2].then_expr[0].expr.value = \
        container[-2].then_expr[0].expr.value, container[-1].expr.value
    
    container[-2].expr = b_not_t(container[-2].expr.copy())
    simplify_expressions.run(container[-2].expr, deep=True)
    
    return

def append_block(flow, block, next):
    
    assert type(block.container[-1]) == goto_t
    
    goto = block.container[-1]
    
    # remove goto
    flow.remove_goto(block, goto)
    
    # fixup references to the block that is going to disapear.
    for src in next.jump_from[:]:
        src.jump_to.remove(next)
        src.jump_to.append(block)
        block.jump_from.append(src)
    
    for dst in next.jump_to[:]:
        dst.jump_from.remove(next)
        dst.jump_from.append(block)
        block.jump_to.append(dst)
    
    # append next block's elements
    block.container[:] = block.container[:] + next.container[:]
    
    return

def change_loop_continues(flow, parent_block, container, first_block, exit_block):
    """ if 'block' ends with a goto_t that leads back to first_block, 
        then change it into a continue_t. """
    
    for stmt in container.statements:
        
        if type(stmt) == goto_t:
            
            if parent_block == first_block and stmt == parent_block.container[-1]:
                continue
            
            if flow.get_block(stmt) == first_block:
                idx = stmt.container.index(stmt)
                container = stmt.container
                flow.remove_goto(parent_block, stmt)
                container.insert(idx, continue_t())
        else:
            change_loop_continues(flow, parent_block, stmt, first_block, exit_block)
    
    return

def make_into_loop(flow, loop_path, all_loop_blocks):
    """ try to make a block into a while(), do-while or for() loop.
    
        'loop_path' is a list of blocks which constitute the
            most likely main path through the loop.
        'all_loop_blocks' is a list of all blocks in the loop, including
            those not on the main path through the loop.
    """
    #~ print 'making into a loop'
    
    exit_block = None
    loop_cls = None
    condition = None
    
    first = loop_path[0]
    last = loop_path[-1]
    
    # if the next to last statement in the main path is a if_t
    # which contains a goto which jumps out of the loop, then 
    # we have a do-while() and the goto destination is the exit
    # block.
    if len(last.container) >= 2 and type(last.container[-1]) == goto_t and \
            type(last.container[-2]) == if_t and \
            type(last.container[-2].then_expr[0]) == goto_t and \
            (flow.get_block(last.container[-1]) == first or \
                flow.get_block(last.container[-2].then_expr[0]) == first) and \
            (flow.get_block(last.container[-1]) not in all_loop_blocks or \
                flow.get_block(last.container[-2].then_expr[0]) not in all_loop_blocks):
        
        left = flow.get_block(last.container[-1])
        right = flow.get_block(last.container[-2].then_expr[0])
        if right == first:
            # the goto_t inside the if_t leads to the beginning 
            # of the loop, then invert both gotos
            
            switch_goto_if_needed(last, right)
            exit_block = left
        else:
            exit_block = right
        
        loop_cls = do_while_t
        condition = last.container[-2]
        condition_block = last
    
    # if the very last block in the main path ends in a goto
    # to the beginning of the loop, then we have a while() loop.
    elif type(last.container[-1]) == goto_t and \
            flow.get_block(last.container[-1]) == first:
        
        loop_cls = while_t
        
        # if the very first statement in the first block in the main
        # path is a if_t which jumps out of the loop, then the 
        # condition in the if_t is the loop condition and the goto
        # destination is the exit block.
        if len(first.container) >= 2 and type(first.container[0]) == if_t and \
            type(first.container[0].then_expr[0]) == goto_t and \
            type(first.container[1]) == goto_t and \
            (flow.get_block(first.container[1]) not in all_loop_blocks or 
                flow.get_block(first.container[0].then_expr[0]) not in all_loop_blocks):
            
            left = flow.get_block(first.container[1])
            right = flow.get_block(first.container[0].then_expr[0])
            
            if left not in all_loop_blocks:
                
                exit_block = left
            elif right not in all_loop_blocks:
                
                exit_block = right
                # make sure 'left' is the goto at the end of the block...
                switch_goto_if_needed(first, left)
            
            condition = first.container[0]
            condition_block = first
        else:
            condition = None
        
        # (TODO):
        # in the presence of a while(), if the last block in the 
        # main path contains a statement which shares an expression 
        # operand with the while() conditional expression (either a 
        # regloc_t or var_t or arg_t), or if the very last block has 
        # multiple  paths leading to it (which may be simplified in 
        # a 'continue'), we upgrade the while() to a for() loop.
    
    else:
        # not a loop...
        return False
    
    if condition:
        condition_expr = condition.expr
        flow.remove_goto(condition_block, condition.then_expr[0])
        condition.container.remove(condition)
    else:
        condition_expr = value_t(1)
    
    if not exit_block:
        # here we should choose the best exit block.
        exit_block = choose_exit_block(flow, all_loop_blocks)
    
    # remove goto to the beginning of the loop
    flow.remove_goto(last, last.container[-1])
    
    # join together all blocks on the main path
    first = loop_path[0]
    for block in loop_path[1:]:
        if len(block.jump_from) > 1:
            break
        switch_goto_if_needed(first, block)
        append_block(flow, first, block)
        all_loop_blocks.remove(block)
    
    # change some gotos into breaks and continues
    for block in all_loop_blocks:
        #~ print 'change block', hex(block.ea)
        change_loop_continues(flow, block, block.container, first, exit_block)
    
    # now make a loop of all this...
    
    container = container_t(first.container[:])
    loop = loop_cls(condition_expr, container)
    first.container[:] = [loop, ]
    
    if exit_block:
        first.container.add(goto_t(value_t(exit_block.ea)))
        first.jump_to.append(exit_block)
        exit_block.jump_from.append(first)
    
    #~ print 'after making loop'
    #~ print str(first)
    
    return True

def choose_exit_block(flow, all_blocks):
    
    contenders = []
    
    for b in all_blocks:
        for dst in b.jump_to:
            if dst not in all_blocks and dst not in contenders:
                contenders.append(dst)
    
    print 'exit block contenders:', repr([hex(b.ea) for b in contenders])
    
    return

def combine_loop_paths(flow, path):
    
    blocks = path.longest_path()
    #~ print 'combining path', repr([hex(b.ea) for b in blocks])
    all_loop_blocks = path.all_blocks()
    #~ print 'all blocks', repr([hex(b.ea) for b in all_loop_blocks])
    
    # try to make this into a loop.
    if make_into_loop(flow, blocks, all_loop_blocks):
        return True
    
    return False

def combine_loops_inner(flow, knowns, current):
    
    all_blocks = list(set([b for p in current.paths for b in p]))
    all_blocks.remove(current.origin)
    
    for block in all_blocks:
        path = loop_paths_t(flow, block)
        for known in knowns:
            path.remove_same_paths(known)
        if not path.is_recursive():
            continue
        if combine_loops_inner(flow, knowns[:] + [path, ], path):
            return True
        
        if combine_loop_paths(flow, path):
            return True
    
    return False

def combine_loops(flow, block):
    path = loop_paths_t(flow, block)
    if not path.is_recursive():
        return False
    
    if combine_loops_inner(flow, [path, ], path):
        return True
    
    return combine_loop_paths(flow, path)
__block_filters__.append(combine_loops)

def convert_break_in_container(flow, block, container, goto):
    
    for stmt in container:
        
        if type(stmt) in (while_t, do_while_t):
            # cannot break from inner while to outer while...
            continue
        
        elif type(stmt) == if_t:
            if convert_break_in_container(flow, block, stmt.then_expr, goto):
                return True
            
            if stmt.else_expr:
                if convert_break_in_container(flow, block, stmt.else_expr, goto):
                    return True
        
        elif type(stmt) == goto_t and stmt.expr == goto.expr:
            
            idx = container.index(stmt)
            flow.remove_goto(block, stmt)
            
            container.insert(idx, break_t())
            
            return True
    
    return False

def convert_break(flow, block, container):
    """ in a while_t followed by a goto_t, we can safely replace any instance
        of the same goto_t from inside the loop by a break_t.
    """
    
    for i in range(len(container)-1):
        stmt = container[i]
        goto = container[i+1]
        
        if type(stmt) in (while_t, do_while_t) and type(goto) == goto_t:
            
            return convert_break_in_container(flow, block, stmt.loop_container, goto)
    
    return False
__container_filters__.append(convert_break)

def combine_noreturns(flow, block, container):
    """ if the last call before a goto_t is a noreturn call, 
        then remove the goto_t (which is incorrect anyway). """
    # TODO: the flow code shouldn't put a goto there in the first place.
    
    if len(container) < 2 or type(container[-1]) != goto_t:
        return False
    
    goto = container[-1]
    if type(goto.expr) != value_t or type(container[-2]) != statement_t:
        return False
    
    dst_block = flow.blocks[goto.expr.value]
    
    if type(container[-2].expr) == call_t:
        call = container[-2].expr
    elif type(container[-2].expr) == assign_t and type(container[-2].expr.op2) == call_t:
        call = container[-2].expr.op2
    else:
        return False
    
    if type(call.fct) != value_t:
        return False
    
    if flow.arch.function_does_return(call.fct.value):
        return False
    
    container.remove(goto)
    block.jump_to.remove(dst_block)
    dst_block.jump_from.remove(block)
    
    return True
__container_filters__.append(combine_noreturns)

def combine_block_tail(flow, block, container):
    """ combine goto's with their destination, if the destination has only one path that reaches it """
    
    if len(container) < 1:
        return False
    
    last_stmt = container[-1]
    
    if type(last_stmt) != goto_t or type(last_stmt.expr) != value_t:
        return False
    
    dst_ea = last_stmt.expr.value
    dst_block = flow.blocks[dst_ea]
    
    # check if there is only one jump destination, with the exception of jumps to itself (loops)
    jump_src = [src for src in dst_block.jump_from]
    if len(jump_src) != 1:
        return False
    
    # pop goto
    container.pop()
    
    # extend cur. container with dest container's content
    container.extend(dst_block.container[:])
    block.jump_to += dst_block.jump_to
    
    if dst_block in block.jump_to:
        block.jump_to.remove(dst_block)
    if block in dst_block.jump_from:
        dst_block.jump_from.remove(block)
    
    for to_block in dst_block.jump_to[:]:
        if dst_block in to_block.jump_from:
            to_block.jump_from.remove(dst_block)
        to_block.jump_from.append(block)
    
    block.items += dst_block.items
    
    return True
__container_filters__.append(combine_block_tail)

def combine_else_tails(flow, block, container):
    """ if a block contains an if_t whose then-side ends with the same 
        goto_t as the block itself, then merge all expressions at the 
        end of the block into the else-side of the if_t.
        
        if (...) {
            ...
            goto foo;
        }
        ...
        goto foo;
        
        becomes
        
        if (...) {
           ...
        }
        else {
           ...
        }
        goto foo;
        
        """
    
    for i in range(len(container)):
        stmt = container[i]
        
        while True:
            if type(stmt) == if_t and len(stmt.then_expr) >= 1 and \
                    type(container[-1]) == goto_t and type(stmt.then_expr[-1]) == goto_t and \
                    container[-1] == stmt.then_expr[-1]:
            
                goto = stmt.then_expr.pop(-1)
                dstblock = flow.blocks[goto.expr.value]
                
                block.jump_to.remove(dstblock)
                
                if block in dstblock.jump_from:
                    dstblock.jump_from.remove(block)
                
                stmts = container[i+1:-1]
                container[i+1:-1] = []
                stmt.else_expr = container_t(stmts)
                
                return True
            
            if type(stmt) == if_t and stmt.else_expr and len(stmt.else_expr) == 1 and \
                    type(stmt.else_expr[0]) == if_t:
                stmt = stmt.else_expr[0]
                continue
            
            break
    
    return False
__container_filters__.append(combine_else_tails)

#~ def combine_increments(flow, block, container):
    #~ """ change statements of the type 'a = a + 1' into increment_t """
    
    #~ for stmt in container:
        
        #~ if type(stmt) == statement_t and type(stmt.expr) == assign_t and \
                #~ type(stmt.expr.op2) in (add_t, sub_t) and (stmt.expr.op1 == stmt.expr.op2.op1 \
                #~ and stmt.expr.op2.op2 == value_t(1)):
            
            #~ idx = container.index(stmt)
            #~ _type = inc_t if type(stmt.expr.op2) == add_t else dec_t
            #~ stmt = _type(stmt.expr.op1.copy())
            #~ container[idx] = stmt
            
            #~ return True
    
    #~ return False
#~ __container_filters__.append(combine_increments)

def combine_ifs(flow, block, container):
    """ process if_t """
    
    for stmt in container:
        
        # invert then and else side if then-side is empty
        if type(stmt) == if_t and stmt.else_expr is not None and len(stmt.then_expr) == 0:
            stmt.then_expr = stmt.else_expr
            stmt.expr = b_not_t(stmt.expr.copy())
            stmt.else_expr = None
            
            simplify_expressions.run(stmt.expr, deep=True)
            
            return True
        
        # remove if altogether if it contains no statements at all
        if type(stmt) == if_t and stmt.else_expr is None and len(stmt.then_expr) == 0:
            container.remove(stmt)
            return True
    
    return False
__container_filters__.append(combine_ifs)

def convert_elseif(flow, block, container):
    """ if we have an if_t as only statement in the then-side of a parent 
        if_t, and the parent if_t has an else-side which doesn't contain 
        an if_t as only statement (to avoid infinite loops), then we can 
        safely invert the two sides of the parent if_t so that it will be 
        displayed in the more natural 'if(...) { } else if(...) {}' form.
    """
    
    for stmt in container:
        
        if type(stmt) == if_t and stmt.else_expr and \
                len(stmt.then_expr) == 1 and type(stmt.then_expr[0]) == if_t and \
                not (len(stmt.else_expr) == 1 and type(stmt.else_expr[0]) == if_t): \
            
            stmt.then_expr, stmt.else_expr = stmt.else_expr, stmt.then_expr
            
            stmt.expr = b_not_t(stmt.expr.copy())
            simplify_expressions.run(stmt.expr, deep=True)
            
            return True
    
    return False
__container_filters__.append(convert_elseif)

def combine_container_run(flow, block, container):
    """ process all possible combinations for all containers. """
    
    # first deal with possible nested containers.
    for stmt in container:
        
        if type(stmt) == if_t:
            if combine_container_run(flow, block, stmt.then_expr):
                return True
            if stmt.else_expr:
                if combine_container_run(flow, block, stmt.else_expr):
                    return True
        
        elif type(stmt) in (while_t, do_while_t):
            if combine_container_run(flow, block, stmt.loop_container):
                return True
    
    # apply filters to this container last.
    for filter in __container_filters__:
        if filter(flow, block, container):
            #~ print '---filter---'
            #~ print str(flow)
            #~ print '---filter---'
            return True
    
    return False

def combine_container(flow, block):
    """ process all possible combinations for the top-level container of a block """
    
    return combine_container_run(flow, block, block.container)
__block_filters__.append(combine_container)

def once(flow):
    """ do one combination pass until a single combination is performed. """
    
    for filter in __block_filters__:
        for block in flow.iterblocks():
            if filter(flow, block):
                return True
    
    return False

def run(flow):
    """ combine until no more combinations can be applied. """
    
    while True:
        if not once(flow):
            break
    
    return

########NEW FILE########
__FILENAME__ = simplify_expressions
""" This module runs an expression through a series of filters.

When a filter matches, a new expression is created from the old one 
and returned to the caller, which should call again until all filters 
are exhausted and no simpler expression can be generated.
"""

from expressions import *

__all__ = []

def flags(expr):
    """ transform flags operations into simpler expressions such as lower-than
        or greater-than.
    
    unsigned stuff:
    CARRY(a - b) becomes a < b
    !CARRY(a - b) becomes a > b
    
    signed stuff:
    SIGN(a - b) != OVERFLOW(a - b) becomes a < b
    SIGN(a - b) == OVERFLOW(a - b) becomes a > b
    
    and for both:
    !(a - b) || a < b becomes a <= b
    (a - b) && a > b becomes a >= b
    
    """
    
    is_less = lambda expr: type(expr) == neq_t and \
            type(expr.op1) == sign_t and type(expr.op2) == overflow_t and \
            expr.op1.op == expr.op2.op #and type(expr.op1.op) == sub_t
    is_greater = lambda expr: type(expr) == eq_t and \
            type(expr.op1) == sign_t and type(expr.op2) == overflow_t and \
            expr.op1.op == expr.op2.op #and type(expr.op1.op) == sub_t
    
    is_lower = lambda expr: type(expr) == carry_t #and type(expr.op) == sub_t
    is_above = lambda expr: type(expr) == b_not_t and is_lower(expr.op)
    
    is_leq = lambda expr: type(expr) == b_or_t and type(expr.op1) == b_not_t and \
                type(expr.op2) == lower_t and expr.op1.op == expr.op2
    is_aeq = lambda expr: type(expr) == b_and_t and \
                type(expr.op2) in (above_t, aeq_t) and expr.op1 == expr.op2.op1
    
    # signed less-than
    if is_less(expr):
        return lower_t(expr.op1.op.copy(), value_t(0, expr.op1.op.size))
    
    # signed greater-than
    if is_greater(expr):
        return above_t(expr.op1.op.copy(), value_t(0, expr.op1.op.size))
    
    # unsigned lower-than
    if is_lower(expr):
        return lower_t(expr.op.copy(), value_t(0, expr.op.size))
    
    # unsigned above-than
    if is_above(expr):
        return above_t(expr.op.op.copy(), value_t(0, expr.op.op.size))
    
    # less-or-equal
    if is_leq(expr):
        return leq_t(expr.op2.copy(), value_t(0, expr.op2.size))
    
    # above-or-equal
    if is_aeq(expr):
        return aeq_t(expr.op1.copy(), value_t(0, expr.op1.size))
    
    return
__all__.append(flags)

def add_sub(expr):
    """ Simplify nested math expressions when the second operand of 
        each expression is a number literal.
    
    (a +/- n1) +/- n2 => (a +/- n3) with n3 = n1 +/- n2
    (a +/- 0) => a
    """
    
    if expr.__class__ == add_t and expr.op1.__class__ in (add_t, sub_t) \
            and expr.op1.op2.__class__ == value_t and expr.op2.__class__ == value_t:
        _expr = expr.op1.copy()
        _expr.add(expr.op2)
        return _expr
    
    if expr.__class__ == sub_t and expr.op1.__class__ in (add_t, sub_t) \
            and expr.op1.op2.__class__ == value_t and expr.op2.__class__ == value_t:
        _expr = expr.op1.copy()
        _expr.sub(expr.op2)
        return _expr
    
    if type(expr) in (sub_t, add_t):
        if type(expr.op2) == value_t and expr.op2.value == 0:
            return expr.op1.copy()
    
    return
__all__.append(add_sub)

def ref_deref(expr):
    """ remove nested deref_t and address_t that cancel each other
    
    &(*(addr)) => addr
    *(&(addr)) => addr
    """
    
    if type(expr) == address_t and type(expr.op) == deref_t:
        return expr.op.op.copy()
    
    if type(expr) == deref_t and type(expr.op) == address_t:
        return expr.op.op.copy()
    
    return
__all__.append(ref_deref)

def equality_with_literals(expr):
    """ Applies commutativity of equality (==) sign
    
    (<1> - n1) == n2 becomes <1> == n3 where n3 = n1 + n2
    """
    
    if type(expr) in (eq_t, neq_t, above_t, lower_t, aeq_t, leq_t) and type(expr.op2) == value_t and \
        type(expr.op1) in (sub_t, add_t) and type(expr.op1.op2) == value_t:
        
        if type(expr.op1) == sub_t:
            _value = value_t(expr.op2.value + expr.op1.op2.value, max(expr.op2.size, expr.op1.op2.size))
        else:
            _value = value_t(expr.op2.value - expr.op1.op2.value, max(expr.op2.size, expr.op1.op2.size))
        return expr.__class__(expr.op1.op1.copy(), _value)
    
    return
__all__.append(equality_with_literals)

def negate(expr):
    """ transform negations into simpler, more readable forms
    
    !(a && b) becomes !a || !b
    !(a || b) becomes !a && !b
    !(a == b) becomes a != b
    !(a != b) becomes a == b
    !(!(expr)) becomes expr
    a == 0 becomes !a
    
    !(a < b) becomes a >= b
    !(a > b) becomes a <= b
    !(a >= b) becomes a < b
    !(a <= b) becomes a > b
    """
    
    if type(expr) == b_not_t and type(expr.op) == b_and_t:
        return b_or_t(b_not_t(expr.op.op1.copy()), b_not_t(expr.op.op2.copy()))
    
    if type(expr) == b_not_t and type(expr.op) == b_or_t:
        return b_and_t(b_not_t(expr.op.op1.copy()), b_not_t(expr.op.op2.copy()))
    
    if type(expr) == b_not_t and type(expr.op) == eq_t:
        return neq_t(expr.op.op1.copy(), expr.op.op2.copy())
    
    if type(expr) == b_not_t and type(expr.op) == neq_t:
        return eq_t(expr.op.op1.copy(), expr.op.op2.copy())
    
    if type(expr) == b_not_t and type(expr.op) == b_not_t:
        return expr.op.op.copy()
    
    if type(expr) == eq_t and type(expr.op2) == value_t and expr.op2.value == 0:
        return b_not_t(expr.op1.copy())
    
    # !(a < b) becomes a >= b
    if type(expr) == b_not_t and type(expr.op) == lower_t:
        return aeq_t(expr.op.op1.copy(), expr.op.op2.copy())
    
    # !(a > b) becomes a <= b
    if type(expr) == b_not_t and type(expr.op) == above_t:
        return leq_t(expr.op.op1.copy(), expr.op.op2.copy())
    
    # !(a >= b) becomes a < b
    if type(expr) == b_not_t and type(expr.op) == aeq_t:
        return lower_t(expr.op.op1.copy(), expr.op.op2.copy())
    
    # !(a <= b) becomes a > b
    if type(expr) == b_not_t and type(expr.op) == leq_t:
        return above_t(expr.op.op1.copy(), expr.op.op2.copy())
    
    return
__all__.append(negate)

def correct_signs(expr):
    """ substitute addition or substraction by its inverse depending on the operand sign
    
    x + -y becomes x - y
    x - -y becomes x + y
    """
    
    if type(expr) == add_t and type(expr.op2) == value_t and expr.op2.value < 0:
        return sub_t(expr.op1.copy(), value_t(abs(expr.op2.value), expr.op2.size))
    
    if type(expr) == sub_t and type(expr.op2) == value_t and expr.op2.value < 0:
        return add_t(expr.op1.copy(), value_t(abs(expr.op2.value), expr.op2.size))
    
    return
__all__.append(correct_signs)

def special_xor(expr):
    """ transform xor_t into a literal 0 if both operands to the xor are the same
    
    x ^ x becomes 0
    """
    
    if type(expr) == xor_t and expr.op1 == expr.op2:
        return value_t(0, expr.op1.size)
    
    return
__all__.append(special_xor)

def special_and(expr):
    """ transform the and (&) operator into a simpler form in the special case
    that both operands are the same
    
    x & x becomes x
    """
    
    if type(expr) == and_t and expr.op1 == expr.op2:
        return expr.op1.copy()
    
    return
__all__.append(special_and)

def once(expr, deep=False):
    """ run all filters and return the first available simplification """
    
    for filter in __all__:
        newexpr = filter(expr)
        if newexpr:
            expr.replace(newexpr)
            return newexpr
    
    if deep and isinstance(expr, expr_t):
        for op in expr.operands:
            newexpr = once(op, deep)
            if newexpr:
                return expr
    
    return

def run(expr, deep=False):
    """ combine expressions until they cannot be combined any more. 
        return the new expression. """
    
    while True:
        newexpr = once(expr, deep=deep)
        if not newexpr:
            break
        expr = newexpr
    
    return

########NEW FILE########
__FILENAME__ = flow

from expressions import *
from statements import *

import filters.simplify_expressions
import filters.controlflow

class flowblock_t(object):
    
    def __init__(self, ea):
        
        self.ea = ea
        
        self.items = []
        self.container = container_t()
        
        self.jump_from = []
        self.jump_to = []
        
        #~ self.branch_expr = None
        
        #~ self.return_expr = None
        self.falls_into = None
        
        return
    
    def __repr__(self):
        return '<flowblock %s>' % (repr(self.container), )
    
    def __str__(self):
        return str(self.container)

class flow_t(object):
    
    def __init__(self, entry_ea, arch, follow_calls=True):
        
        self.entry_ea = entry_ea
        self.follow_calls = follow_calls
        self.arch = arch
        
        self.func_items = self.arch.get_function_items(self.entry_ea)
        
        self.return_blocks = []
        
        self.entry_block = None
        self.blocks = {}
        
        return
    
    def __repr__(self):
        
        lines = []
        
        for block in self.iterblocks():
            lines.append('<loc_%x>' % (block.ea, ))
            
            lines += repr(block.container).split('\n')
            
            lines.append('')
        
        return '\n'.join(lines)
    
    def get_block(self, addr):
        
        if type(addr) == goto_t:
            
            if type(addr.expr) != value_t:
                raise RuntimeError('goto_t.expr is not value_t')
            
            ea = addr.expr.value
        
        elif type(addr) == value_t:
            ea = addr.value
        
        elif type(addr) in (long, int):
            ea = addr
        
        if ea not in self.blocks:
            return None
        
        return self.blocks[ea]
    
    def remove_goto(self, block, stmt):
        """ remove a goto statement, and take care of unlinking the 
            jump_to and jump_from.
            
            'block' is the block which contains the goto.
            'stmt' is the goto statement.
        """
        
        if type(stmt.expr) == value_t:
            dst_ea = stmt.expr.value
            dst_block = self.blocks[dst_ea]
            dst_block.jump_from.remove(block)
            block.jump_to.remove(dst_block)
        
        stmt.container.remove(stmt)
        return
    
    def jump_targets(self):
        """ find each point in the function which is the 
        destination of a jump (conditional or not).
        
        jump destinations are the points that delimit new
        blocks. """
        
        for item in self.func_items:
            if self.arch.has_jump(item):
                for dest in self.arch.jump_branches(item):
                    if type(dest) == value_t and dest.value in self.func_items:
                        ea = dest.value
                        yield ea
        
        return
    
    def find_control_flow(self):
        
        # find all jump targets
        jump_targets = list(set(self.jump_targets()))
        
        # prepare first block
        self.entry_block = flowblock_t(self.entry_ea)
        next_blocks = [self.entry_block, ]
        self.blocks[self.entry_ea] = self.entry_block
        
        # create all empty blocks.
        for target in jump_targets:
            block = flowblock_t(target)
            self.blocks[target] = block
            next_blocks.append(block)
        
        while len(next_blocks) > 0:
            
            # get next block
            block = next_blocks.pop(0)
            ea = block.ea
            
            while True:
                # append current ea to the block's locations array
                block.items.append(ea)
                
                if self.arch.is_return(ea):
                    
                    self.return_blocks.append(block)
                    break
                
                elif self.arch.has_jump(ea):
                    
                    for dest in self.arch.jump_branches(ea):
                        
                        if type(dest) != value_t:
                            print '%x: cannot follow jump to %s' % (ea, repr(dest))
                        else:
                            ea_to = dest.value
                            if ea_to not in self.func_items:
                                print '%x: jumped outside of function to %x' % (ea, ea_to, )
                            else:
                                toblock = self.blocks[ea_to]
                                block.jump_to.append(toblock)
                                toblock.jump_from.append(block)
                    
                    break
                
                next_ea = self.arch.next_instruction_ea(ea)
                
                if next_ea not in self.func_items:
                    print '%x: jumped outside of function: %x' % (ea, next_ea)
                    break
                
                ea = next_ea
                
                # the next instruction is part of another block...
                if ea in jump_targets:
                    toblock = self.blocks[ea]
                    block.jump_to.append(toblock)
                    toblock.jump_from.append(block)
                    
                    block.falls_into = toblock
                    break
        
        return
    
    def iterblocks(self):
        """ iterate over all blocks in the order that they most logically follow each other. """
        
        if not self.entry_block:
            return
        
        done = []
        blocks = [self.entry_block, ]
        
        while len(blocks) > 0:
            
            block = blocks.pop(0)
            
            if block in done:
                continue
            
            done.append(block)
            
            yield block
            
            for block in block.jump_to:
                if block not in done:
                    if block in blocks:
                        # re-add at the end
                        blocks.remove(block)
                    blocks.append(block)
        
        return
    
    def simplify_expressions(self, expr):
        """ combine expressions until it cannot be combined any more. return the new expression. """
        
        return filters.simplify_expressions.run(expr, deep=True)
    
    def simplify_statement(self, stmt):
        """ find any expression present in a statement and simplify them. if the statement
            has other statements nested (as is the case for if-then, while, etc), then 
            sub-statements are also processed. """
        
        # simplify sub-statements
        for _stmt in stmt.statements:
            self.simplify_statement(_stmt)
        
        #~ stmt.expr = self.filter_expression(stmt.expr, self.simplify_expressions)
        filters.simplify_expressions.run(stmt.expr, deep=True)
        
        return stmt
    
    def make_statement(self, item):
        """ always return a statement from an expression or a statement. """
        
        if isinstance(item, statement_t):
            stmt = item
        elif isinstance(item, expr_t):
            stmt = statement_t(item)
        else:
            raise RuntimeError("don't know how to make a statement with %s" % (type(item), ))
        
        return stmt
    
    def transform_ir(self):
        """ transform the program into the intermediate representation. """
        
        for block in self.iterblocks():
            
            # for all item in the block, process each statement.
            for item in block.items:
                for expr in self.arch.generate_statements(item):
                    
                    # upgrade expr to statement if necessary
                    stmt = self.make_statement(expr)
                    
                    # apply simplification rules to all expressions in this statement
                    stmt = self.simplify_statement(stmt)
                    
                    block.container.add(stmt)
            
            # if the block 'falls' without branch instruction into another one, add a goto for clarity
            if block.falls_into:
                block.container.add(goto_t(value_t(block.falls_into.ea, self.arch.address_size)))
        
        return
    
    #~ def filter_expression(self, expr, filter):
        #~ """ recursively call the 'filter' function over all operands of all expressions
            #~ found in 'expr', depth first. """
        
        #~ if type(expr) == assign_t:
            #~ expr.op1 = self.filter_expression(expr.op1, filter)
            #~ expr.op2 = self.filter_expression(expr.op2, filter)
        
        #~ elif isinstance(expr, expr_t):
            
            #~ for i in range(len(expr)):
                #~ op = expr[i]
                #~ if op is None:
                    #~ continue
                
                #~ expr[i] = self.filter_expression(expr[i], filter)
        
        #~ elif type(expr) in (value_t, flagloc_t, regloc_t, var_t, arg_t):
            #~ pass
        
        #~ else:
            #~ raise RuntimeError('cannot iterate over expression of type %s' % (type(expr), ))
        
        #~ expr = filter(expr)
        #~ return expr
    
    def combine_blocks(self):
        
        filters.controlflow.run(self)
        
        return

########NEW FILE########
__FILENAME__ = dis
import traceback

try:
    import idaapi # try importing ida's main module.
    
    print 'Using IDA backend.'
    from .ida.dis import *
except BaseException as e:
    print repr(e)
    traceback.print_exc()

########NEW FILE########
__FILENAME__ = intel
""" support for IDA's intel assembly. """

import idaapi
import idautils
import idc

from expressions import *
from statements import *

class disassembler(object):
    
    def __init__(self):
        return
    
    def get_ea_name(self, ea):
        """ return the name of this location, or None if no name is defined. """
        return idc.Name(ea)
    
    def get_string(self, ea):
        """ return the string starting at 'ea' or None if it is not a string. """
        return idc.GetString(ea)
    
    def function_does_return(self, ea):
        """ return False if the function does not return (ExitThread(), exit(), etc). """
        if idc.GetFunctionFlags(call.fct.value) & idaapi.FUNC_NORET:
            return False
        return True
    
    def get_function_start(self, ea):
        """ return the address of the parent function, given any address inside that function. """
        func = idaapi.get_func(ea)
        if func:
            return func.startEA
        return
    
    def get_function_items(self, ea):
        """ return all addresses that belong to the function at 'ea'. """
        return list(idautils.FuncItems(ea))
    
    def get_mnemonic(self, ea):
        """ return textual mnemonic for the instruction at 'ea'. """
        return idc.GetMnem(ea)
    
    def get_instruction_size(self, ea):
        """ return the instruction size. """
        insn = idautils.DecodeInstruction(ea)
        assert insn.size > 0, '%x: no instruction' % (ea, )
        return insn.size
    
    def as_byte_value(self, value):
        if value < 0:
            return 0x100+value
        return value
    
    def has_sib_byte(self, op):
        # Does the instruction use the SIB byte?
        return self.as_byte_value(op.specflag1) == 1
    
    def get_sib_scale(self, op):
        return (1, 2, 4, 8)[self.as_byte_value(op.specflag2) >> 6]
    
    def get_sib_scaled_index_reg(self, op):
        return (self.as_byte_value(op.specflag2) >> 3) & 0x7
    
    def get_operand_size(self, op):
        
        types = {
            idaapi.dt_byte: 8,
            idaapi.dt_word: 16,
            idaapi.dt_dword: 32,
            idaapi.dt_float: 32,
            idaapi.dt_double: 64,
            idaapi.dt_qword: 64,
            idaapi.dt_byte16: 64,
            idaapi.dt_fword: 48,
            idaapi.dt_3byte: 48,
        }
        
        if op.dtyp not in types:
            raise ValueError("don't know how to get the size of this operand")
        
        return types[op.dtyp]
    
    def get_operand_expression(self, ea, n):
        """ return an expression representing the 'n'-th operand of the instruction at 'ea'. """
        
        insn = idautils.DecodeInstruction(ea)
        op = insn[n]
        
        if op.type == idaapi.o_reg:       #  General Register (al,ax,es,ds...)    reg
            sz = self.get_operand_size(op)
            expr = regloc_t(op.reg, sz)
            
        elif op.type == idaapi.o_mem: #  Direct Memory Reference  (DATA)
            
            addr = self.as_signed(op.addr)
            
            if self.has_sib_byte(op):
                
                reg = self.get_sib_scaled_index_reg(op)
                # *(addr+reg*scale)
                expr = deref_t(add_t(value_t(addr), \
                    mul_t(regloc_t(reg, self.get_register_size(reg)), \
                        value_t(self.get_sib_scale(op), 8))), self.get_operand_size(op))
            else:
                expr = deref_t(value_t(addr, self.address_size), self.get_operand_size(op))
            
        elif op.type == idaapi.o_phrase: #  Memory Ref [Base Reg + Index Reg]
            
            expr = regloc_t(op.reg, self.get_register_size(op.reg))
            expr = deref_t(expr, self.get_operand_size(op))
            
        elif op.type == idaapi.o_displ: #  Memory Reg [Base Reg + Index Reg + Displacement] phrase+addr
            
            addr = self.as_signed(op.addr)
            
            expr = regloc_t(op.reg, self.get_register_size(op.reg))
            
            expr = add_t(expr, value_t(addr, self.address_size))
            expr = deref_t(expr, self.get_operand_size(op))
            
        elif op.type == idaapi.o_imm: #  Immediate Value
            
            _value = self.as_signed(op.value)
            expr = value_t(_value, self.get_operand_size(op))
            
        elif op.type == idaapi.o_near: #  Immediate Far Address  (CODE)
            
            addr = self.as_signed(op.addr)
            expr = value_t(addr, self.get_operand_size(op))
        else:
            #~ print hex(ea), 
            raise RuntimeError('%x: unhandled operand type: %s %s' % (ea, repr(op.type), repr(idc.GetOpnd(ea, 1))))
            return
        
        return expr
    
    def get_call_expression(self, ea):
        """ get an expression representing a function call at this address. """
        
        insn = idautils.DecodeInstruction(ea)
        
        fct = self.get_operand_expression(ea, 0)
        
        if type(fct) == value_t and \
                idc.GetFunctionFlags(fct.value) & idaapi.FUNC_THUNK == idaapi.FUNC_THUNK:
            
            print '%x: call to function thunk %x' % (ea, fct.value)
            
            expr = call_t(fct, None)
            #~ return expr, []
            spoils = []
        
        else:
            #~ if self.follow_calls and type(fct) == value_t:
            if type(fct) == value_t:
                fct_ea = fct.value
                
                #~ try:
                    #~ call_flow = flow_t(fct_ea, follow_calls = False)
                    #~ call_flow.reduce_blocks()
                    
                    #~ params = [p.copy() for p in call_flow.uninitialized_uses]
                    #~ spoils = [p.copy() for p in call_flow.spoils]
                #~ except:
                
                print '%x could not analyse call to %x' % (ea, fct.value)
                params = []
                spoils = []
            else:
                params = []
                spoils = []
            
            # for all uninitialized register uses in the target function, resolve to a value.
            #~ params = [(self.get_value_at(p) or p) for p in params]
            expr = call_t(fct, None)
        
        # check if eax is a spoiled register for the target function.
        # if it is, change the expression into an assignment to eax
        
        if type(fct) != value_t or not (idc.GetFunctionFlags(fct.value) & idaapi.FUNC_NORET):
            expr = assign_t(self.resultreg.copy(), expr)
        
        return expr, spoils
    
########NEW FILE########
__FILENAME__ = browser
""" Browser widget for flow_t object.

"""

import idc

from output import c

try:
    import PySide
    from PySide import QtCore, QtGui
except:
    print 'PySide not available'
    raise

class token_fragment(object):
    
    def __init__(self, fragment, token):
        self.fragment = fragment
        self.token = token
        return

class FlowBrowser(QtGui.QTextEdit):
    
    def __init__(self, parent=None):
        
        QtGui.QTextEdit.__init__(self, parent)
        self.flow = None
        
        self.inserting = False
        self.cursorPositionChanged.connect(self.select_token)
        
        self.__fragments = []
        self.__textmap = {}
        self.__current_highlight = None
        
        return
    
    def select_token(self):
        
        if self.inserting:
            return
        
        cursor = self.textCursor()
        fmt = cursor.charFormat()
        tok = fmt.property(QtGui.QTextFormat.UserProperty)
        
        if self.__current_highlight:
            brush = QtGui.QBrush(QtGui.QColor(0,0,0,0))
            self.set_fragments_bg(self.__current_highlight, brush)
            self.__current_highlight = None
        
        s = str(tok)
        if s in self.__textmap:
            brush = QtGui.QBrush(QtGui.QColor(0xff,0xff,0x00,200))
            self.set_fragments_bg(self.__textmap[s], brush)
            self.__current_highlight = self.__textmap[s]
        
        #~ print '-> %s' % str(tok)
        
        return
    
    def set_fragments_bg(self, token_fragments, brush):
        
        for tf in token_fragments:
            frag = tf.fragment
            #~ print 'frag %s' % repr(frag.text(), )
            fmt = frag.charFormat()
            fmt.setProperty(QtGui.QTextFormat.BackgroundBrush, brush)
            tmpcursor = QtGui.QTextCursor(self.document())
            #~ print frag.position(), frag.length()
            tmpcursor.setPosition(frag.position())
            tmpcursor.setPosition(frag.position() + frag.length(), QtGui.QTextCursor.KeepAnchor)
            tmpcursor.setCharFormat(fmt)
    
    def token_color(self, token):
        
        if type(token) == c.token_global:
            return QtGui.QColor(0x4a,0xa3,0xff,255)
        
        if type(token) == c.token_keyword:
            return QtGui.QColor(0x20,0x2d,0xae,255)
        
        if type(token) == c.token_number:
            return QtGui.QColor(0x00,0xac,0x92,255)
        
        if type(token) == c.token_string:
            return QtGui.QColor(0x00,0x70,0x00,255)
        
        if type(token) == c.token_var:
            return QtGui.QColor(0x87,0x5b,0x4e,255)
        
        return QtGui.QColor(0,0,0,255)
    
    def set_fragment_format(self, frag, fmt):
        tmpcursor = QtGui.QTextCursor(self.document())
        tmpcursor.setPosition(frag.position())
        tmpcursor.setPosition(frag.position() + frag.length(), QtGui.QTextCursor.KeepAnchor)
        tmpcursor.setCharFormat(fmt)
        return
    
    def insert_token(self, token):
        
        cursor = QtGui.QTextCursor(self.document())
        cursor.movePosition(QtGui.QTextCursor.End)
        
        brush = QtGui.QBrush(self.token_color(token))
        fmt = QtGui.QTextFormat(QtGui.QTextFormat.CharFormat)
        fmt.setProperty(QtGui.QTextFormat.ForegroundBrush, brush)
        
        fmt.setProperty(QtGui.QTextFormat.FontStyleHint, QtGui.QFont.Monospace)
        fmt.setProperty(QtGui.QTextFormat.FontWeight, QtGui.QFont.Bold)
        fmt.setProperty(QtGui.QTextFormat.FontFamily, "Liberation Mono")
        
        fmt.setProperty(QtGui.QTextFormat.UserProperty, token)
        
        cursor.insertText(str(token), fmt.toCharFormat())
        
        return
    
    def update(self, flow):
        
        self.flow = flow
        
        t = c.tokenizer(flow)
        tokens = list(t.flow_tokens())
        
        self.clear()
        
        self.inserting = True
        for tok in tokens:
            self.insert_token(tok)
        self.inserting = False
        
        doc = self.document()
        block = doc.begin()
        while block != doc.end():
            
            for it in block:
                frag = it.fragment()
                fmt = frag.charFormat()
                tok = fmt.property(QtGui.QTextFormat.UserProperty)
                
                s = str(tok)
                print 'inserted %s %s' % (frag.text(), s)
                
                tf = token_fragment(frag, tok)
                if s not in self.__textmap:
                    self.__textmap[s] = []
                self.__textmap[s].append(tf)
                
                self.__fragments.append(tf)
            
            block = block.next()
        
        return

########NEW FILE########
__FILENAME__ = decompiler_form
import idautils
import idaapi
import idc

import host
import host.ui

import decompiler

import sys
import traceback

import browser

try:
    import PySide
    from PySide import QtCore, QtGui
except:
    print 'PySide not available'
    raise

sys.modules['__main__'].QtGui = QtGui # goddamit IDA..

decompilation_phase = [
    'Nothing done yet',
    'Basic block information found',
    'Intermediate representation form',
    'Static Single Assignment form',
    'Call information found',
    'Expressions propagated',
    'Dead code pruned',
    'Decompiled',
]

class DecompilerForm(idaapi.PluginForm):
    
    def __init__(self, ea):
        
        idaapi.PluginForm.__init__(self)
        
        self.ea = ea
        
        self.__name = idc.Name(self.ea)
        
        return
    
    def OnCreate(self, form):
        
        # Get parent widget
        try:
            self.parent = self.FormToPySideWidget(form, ctx=sys.modules['__main__'])
        except:
            traceback.print_exc()
        
        self.populate_form()
        
        return
    
    def Show(self):
        idaapi.PluginForm.Show(self, self.__name)
        self.decompile()
        return
    
    def populate_form(self):
        # Create layout
        layout = QtGui.QVBoxLayout()
        
        self.phase_selection = QtGui.QComboBox(self.parent)
        layout.addWidget(self.phase_selection)
        self.editor = browser.FlowBrowser(self.parent)
        layout.addWidget(self.editor)
        
        for phase in decompilation_phase:
            self.phase_selection.addItem(phase)
        
        self.phase_selection.setCurrentIndex(decompiler.STEP_DECOMPILED)
        self.phase_selection.currentIndexChanged.connect(self.phase_selected)
        
        self.parent.setLayout(layout)
        
        return
    
    def phase_selected(self, index):
        self.decompile(index)
        return
    
    def decompile(self, wanted_step=decompiler.STEP_DECOMPILED):
        
        d = decompiler.decompiler_t(self.ea)
        
        for step in d.steps():
            print 'Decompiler step: %u - %s' % (step, decompilation_phase[step])
            if step >= wanted_step:
                break
        
        self.editor.update(d.flow)
        
        return
    
    def OnClose(self, form):
        pass

########NEW FILE########
__FILENAME__ = graph_test
import idautils
import idaapi
import idc

import sys

from decompiler import *

class GraphViewer(idaapi.GraphViewer):
    def __init__(self, func):
        
        self.func = func
        
        title = "Graph of %x" % (func.startEA, )
        idaapi.GraphViewer.__init__(self, title)
        
        self.flow = self.decompile()
        
        self.blkmap = {}
        self.Show()
        
        return
    
    def OnGetText(self, id):
        block = self.idmap[id]
        
        stmts = block.container[:]
        if len(stmts) == 0:
            return ''
        
        if type(stmts[-1]) == goto_t:
            stmts.pop(-1)
        
        if type(stmts[-1]) == if_t:
            _if = stmts.pop(-1)
            s = '\n'.join([idaapi.COLSTR(str(stmt), idaapi.SCOLOR_KEYWORD) for stmt in stmts])
            if len(stmts) > 0:
                s += '\n'
            return s + idaapi.COLSTR('if(' + str(_if.expr) + ')', idaapi.SCOLOR_KEYWORD)
        
        return '\n'.join([idaapi.COLSTR(str(stmt), idaapi.SCOLOR_KEYWORD) for stmt in stmts])
    
    def OnRefresh(self):
        self.Clear()
        self.idmap = {}
        self.blkmap = {}
        
        for block in self.flow.iterblocks():
            id = self.AddNode('loc_%x' % block.ea)
            self.idmap[id] = block
            self.blkmap[block] = id
        
        for block in self.flow.iterblocks():
            src_id = self.blkmap[block]
            for dest in block.jump_to:
                dest_id = self.blkmap[dest]
                self.AddEdge(src_id, dest_id)
            
        return True
    
    def decompile(self):
        
        arch = arch_intel()
        f = flow_t(func.startEA, arch)
        f.prepare_blocks()

        check_stack_alignment(f)

        # tag all registers so that each instance of a register can be uniquely identified.
        # during this process we also take care of matching registers to their respective 
        # function calls.
        #~ conv = callconv.stdcall()
        conv = callconv.systemv_x64_abi()
        t = tagger(f, conv)
        t.tag_all()

        #~ print '1'
        # remove special flags (eflags) definitions that are not used, just for clarity
        s = simplifier(f, COLLECT_FLAGS)
        s.remove_unused_definitions()

        #~ print '2'
        # After registers are tagged, we can replace their uses by their definitions. this 
        # takes care of eliminating any instances of 'esp' which clears the way for 
        # determining stack variables correctly.
        s = simplifier(f, COLLECT_ALL)
        s.propagate_all(PROPAGATE_STACK_LOCATIONS)
        s = simplifier(f, COLLECT_REGISTERS)
        s.remove_unused_definitions()

        #~ print '3'
        # rename stack variables to differenciate them from other dereferences.
        r = renamer(f, RENAME_STACK_LOCATIONS)
        r.wrap_variables()

        # collect function arguments that are passed on the stack
        s = simplifier(f, COLLECT_ALL)
        s.collect_argument_calls(conv)

        #~ print '3.1'
        # This propagates special flags.
        s = simplifier(f, COLLECT_ALL)
        s.propagate_all(PROPAGATE_REGISTERS | PROPAGATE_FLAGS)

        #~ print '4'
        # At this point we must take care of removing increments and decrements
        # that are in their own statements and "glue" them to an adjacent use of 
        # that location.
        s = simplifier(f, COLLECT_ALL)
        s.glue_increments()
        
        # re-propagate after gluing pre/post increments
        s = simplifier(f, COLLECT_ALL)
        s.propagate_all(PROPAGATE_REGISTERS | PROPAGATE_FLAGS)
        
        #~ print '5'
        s = simplifier(f, COLLECT_ALL)
        s.propagate_all(PROPAGATE_ANY | PROPAGATE_SINGLE_USES)

        #~ print '6'
        # eliminate restored registers. during this pass, the simplifier also collects 
        # stack variables because registers may be preserved on the stack.
        s = simplifier(f, COLLECT_REGISTERS | COLLECT_VARIABLES)
        s.process_restores()
        # ONLY after processing restores can we do this; any variable which is assigned
        # and never used again is removed as dead code.
        s = simplifier(f, COLLECT_REGISTERS)
        s.remove_unused_definitions()

        #~ print '7'
        # rename registers to pretty names.
        r = renamer(f, RENAME_REGISTERS)
        r.fct_arguments = t.fct_arguments
        r.wrap_variables()

        return f

print 'decompile:', idc.here()
func = idaapi.get_func(idc.here())
g = GraphViewer(func)

########NEW FILE########
__FILENAME__ = main
import idaapi

def show_decompiler():
    import idc

    import host
    import host.ui

    import traceback
    import sys

    import decompiler_form
    reload(decompiler_form)
    
    try:
        ea = idc.here()
        func = idaapi.get_func(ea)
        
        ea = func.startEA
        print 'Decompiling %x' % (ea, )
        
        form = decompiler_form.DecompilerForm(ea)
        form.Show()
    except:
        traceback.print_exc()
    
    return

def main():
    global hotkey_ctx
    try:
        hotkey_ctx
        if idaapi.del_hotkey(hotkey_ctx):
            print("Hotkey unregistered!")
            del hotkey_ctx
        else:
            print("Failed to delete hotkey!")
    except:
        pass
    hotkey_ctx = idaapi.add_hotkey("F5", show_decompiler)
    if hotkey_ctx is None:
        print("Failed to register hotkey!")
        del hotkey_ctx
    else:
        print("Press F5 to decompile a function.")

########NEW FILE########
__FILENAME__ = ui
import traceback

try:
    import idaapi # try importing ida's main module.
    
    print 'Using IDA backend.'
    from .ida.ui import *
except BaseException as e:
    print repr(e)
    traceback.print_exc()

########NEW FILE########
__FILENAME__ = generic
""" base class for the intermediate representation.

The IR generation relies on a disassembler to parse the binary object. 
Part of the methods below will be provided by the architecture-specific 
IR generator, and another part will be provided by the host-specific 
disassembler, which the arch-specific code relies upon.
"""

class ir_base(object):
    
    ## following functions are typically implemented at the IR level. they are used by
    ## the flow code to determine basic blocks in the control flow.
    
    def is_return(self, ea):
        """ return True if this is a return instruction. """
        raise NotImplemented('base class must override this method')
    
    def has_jump(self, ea):
        """ return true if this instruction is a jump """
        raise NotImplemented('base class must override this method')
    
    def next_instruction_ea(self, ea):
        """ return the address of the next instruction. """
        raise NotImplemented('base class must override this method')
    
    def jump_branches(self, ea):
        """ if this instruction is a jump, yield the destination(s)
            of the jump, of which there may be more than one.
            
            only literal destinations (i.e. addresses without dereferences)
            are yield. """
        raise NotImplemented('base class must override this method')
    
    def generate_statements(self, block, ea):
        """ this is where the magic happens, this method yeilds one or more new
        statement corresponding to the given location. """
        raise NotImplemented('base class must override this method')
    
    
    ## following functions are typically implemented at the host level. they are used mostly to
    ## translate basic block instructions into the intermediate representation.
    
    def get_ea_name(self, ea):
        """ return the name of this location, or None if no name is defined. """
        raise NotImplementedException('must be implemented by host-specific disassembler')
    
    def get_string(self, ea):
        """ return the string starting at 'ea' or None if it is not a string. """
        raise NotImplementedException('must be implemented by host-specific disassembler')
    
    def function_does_return(self, ea):
        """ return False if the function does not return (ExitThread(), exit(), etc). """
        raise NotImplementedException('must be implemented by host-specific disassembler')
    
    def get_function_start(self, ea):
        """ return the address of the parent function, given any address inside that function. """
        raise NotImplementedException('must be implemented by host-specific disassembler')
    
    def get_function_items(self, ea):
        """ return all addresses that belong to the function at 'ea'. """
        raise NotImplementedException('must be implemented by host-specific disassembler')
    
    def get_mnemonic(self, ea):
        """ return textual mnemonic for the instruction at 'ea'. """
        raise NotImplementedException('must be implemented by host-specific disassembler')
    
    def get_instruction_size(self, ea):
        """ return the instruction size. """
        raise NotImplementedException('must be implemented by host-specific disassembler')
    
    def get_operand_expression(self, ea, n):
        """ return an expression representing the 'n'-th operand of the instruction at 'ea'. """
        raise NotImplementedException('must be implemented by host-specific disassembler')
    
    def get_call_expression(self, ea, insn):
        """ get an expression representing a function call at this address. """
        raise NotImplementedException('must be implemented by host-specific disassembler')


########NEW FILE########
__FILENAME__ = intel
""" intel x86 and x64 archs. """

from expressions import *
from statements import *

from generic import ir_base

RAX, RCX, RDX, RBX, RSP, RSI, R8, R9, R10, R11, R12 = range(11)
EAX, ECX, EDX, EBX, ESP, ESI = range(6)

STACK_REG =  ESP

# FLAGS
CF =    1 << 0  # carry flag: Set on high-order bit carry or borrow
PF =    1 << 2  # parity flag: 
AF =    1 << 4  # adjust flag
ZF =    1 << 6  # zero flag: set if expr == 0
SF =    1 << 7  # sign flag
#~ TF =    1 << 8  # trap flag
#~ IF =    1 << 9  # interrupt enable flag
#~ DF =    1 << 10 # direction flag
OF =    1 << 11 # overflow flag: set when the expression would overflow

# EFLAGS
#~ RF =    1 << 16 # resume flags
#~ VM =    1 << 17 # virtual 8086 mode flag
#~ AC =    1 << 18 # alignment check
#~ VIP =   1 << 19 # virtual interrupt flag
#~ VIF =   1 << 20 # virtual interrupt pending
ID =    1 << 21 # able to use CPUID instruction

class ir_intel(ir_base):
    
    def __init__(self):
        
        assert type(self) != ir_intel, 'must use base classes instead'
        
        ir_base.__init__(self)
        
        self.stackreg = regloc_t(STACK_REG, self.address_size)
        self.resultreg = regloc_t(EAX, self.address_size)
        
        self.special_registers = 9000
        
        self.eflags_expr = self.make_special_register('%eflags.expr')
        self.cf = self.make_special_register('%eflags.cf')
        self.pf = self.make_special_register('%eflags.pf')
        self.af = self.make_special_register('%eflags.af')
        self.zf = self.make_special_register('%eflags.zf')
        self.sf = self.make_special_register('%eflags.sf')
        self.of = self.make_special_register('%eflags.of')
        
        self.flow_break = ['retn', ] # instructions that break (terminate) the flow
        self.unconditional_jumps = ['jmp', ] # unconditional jumps (one branch)
        self.conditional_jumps = ['jo', 'jno', 'js', 'jns', 'jz', 'jnz',
                'jb', 'jnb', 'jbe', 'ja', 'jl', 'jge', 'jle', 'jg', 
                'jpe', 'jno'] # conditional jumps (two branches)
        
        return
    
    def get_regname(self, which):
        
        if which <= len(self.registers):
            return self.registers[which]
        
        return '#%u' % (which, )
    
    def make_special_register(self, name):
        reg = flagloc_t(self.special_registers, 1, name)
        self.special_registers += 1
        return reg
    
    def is_stackreg(self, reg):
        """ return True if the register is the stack register """
        return isinstance(reg, regloc_t) and reg.which == self.stackreg.which
    
    def is_stackvar(self, expr):
        return self.is_stackreg(expr) or \
                ((type(expr) == sub_t and \
                self.is_stackreg(expr.op1) and type(expr.op2) == value_t))
    
    def is_conditional_jump(self, ea):
        """ return true if this instruction is a conditional jump. """
        
        mnem = self.get_mnemonic(ea)
        
        if mnem in self.conditional_jumps:
            return True
        
        return False
    
    def is_unconditional_jump(self, ea):
        """ return true if this instruction is a unconditional jump. """
        
        mnem = self.get_mnemonic(ea)
        
        if mnem in self.unconditional_jumps:
            return True
        
        return False
    
    def is_return(self, ea):
        """ return True if this is a return instruction """
        
        mnem = self.get_mnemonic(ea)
        
        if mnem in self.flow_break:
            return True
        
        return False
    
    def has_jump(self, ea):
        """ return true if this instruction is a jump """
        return self.is_conditional_jump(ea) or self.is_unconditional_jump(ea)
    
    def next_instruction_ea(self, ea):
        """ return the address of the next instruction. """
        size = self.get_instruction_size(ea)
        assert size > 0, '%x: no instruction' % (ea, )
        return ea + size
    
    def jump_branches(self, ea):
        
        mnem = self.get_mnemonic(ea)
        
        if mnem in self.unconditional_jumps:
            
            dest = self.get_operand_expression(ea, 0)
            yield dest
        
        elif mnem in self.conditional_jumps:
            dest = self.get_operand_expression(ea, 0)
            yield dest
            dest = self.next_instruction_ea(ea)
            yield dest
        
        return
    
    def as_signed(self, v, size=None):
        
        if size is None:
            size = self.address_size
        
        if v > (1 << size-1):
            return - ((sum([1 << i for i in range(size)]) + 1) - v)
        
        return v
    
    def evaluate_flags(self, expr, flags):
        
        yield assign_t(self.eflags_expr.copy(), expr.copy())
        
        if flags & CF:
            yield assign_t(self.cf.copy(), carry_t(self.eflags_expr.copy()))
        if flags & PF:
            yield assign_t(self.pf.copy(), parity_t(self.eflags_expr.copy()))
        if flags & AF:
            yield assign_t(self.af.copy(), adjust_t(self.eflags_expr.copy()))
        if flags & ZF:
            yield assign_t(self.zf.copy(), eq_t(self.eflags_expr.copy(), value_t(0, 1)))
        if flags & SF:
            yield assign_t(self.sf.copy(), sign_t(self.eflags_expr.copy()))
        if flags & OF:
            yield assign_t(self.of.copy(), overflow_t(self.eflags_expr.copy()))
        
        return
    
    def set_flags(self, flags, value):
        
        if flags & CF:
            yield assign_t(self.cf.copy(), value_t(value))
        if flags & PF:
            yield assign_t(self.pf.copy(), value_t(value))
        if flags & AF:
            yield assign_t(self.af.copy(), value_t(value))
        if flags & ZF:
            yield assign_t(self.zf.copy(), value_t(value))
        if flags & SF:
            yield assign_t(self.sf.copy(), value_t(value))
        if flags & OF:
            yield assign_t(self.of.copy(), value_t(value))
        
        return
    
    def generate_statements(self, ea):
        
        mnem = self.get_mnemonic(ea)
        
        expr = None
        
        if mnem in ('nop', 'hlt'):
            
            pass
        
        elif mnem in ('cdq', 'cdqe'):
            # sign extension... not supported until we do type analysis
            pass
        
        elif mnem == 'push':
            
            op = self.get_operand_expression(ea, 0)
            
            # stack location assignment
            expr = assign_t(deref_t(self.stackreg.copy(), self.address_size), op.copy())
            yield expr
            
            # stack pointer modification
            expr = assign_t(self.stackreg.copy(), sub_t(self.stackreg.copy(), value_t(4, self.address_size)))
            yield expr
            
        elif mnem == 'pop':
            #~ assert insn.Op1.type == 1
            
            # stack pointer modification
            expr = assign_t(self.stackreg.copy(), add_t(self.stackreg.copy(), value_t(4, self.address_size)))
            yield expr
            
            # stack location value
            dst = self.get_operand_expression(ea, 0)
            
            expr = assign_t(dst.copy(), deref_t(self.stackreg.copy(), self.address_size))
            yield expr
            
        elif mnem == 'leave':
            
            # mov esp, ebp
            ebpreg = regloc_t(5, self.address_size)
            expr = assign_t(self.stackreg.copy(), ebpreg.copy())
            yield expr
            
            # stack pointer modification
            expr = assign_t(self.stackreg.copy(), add_t(self.stackreg.copy(), value_t(4, self.address_size)))
            yield expr
            
            # stack location value
            expr = assign_t(ebpreg.copy(), deref_t(self.stackreg.copy(), self.address_size))
            yield expr
            
        elif mnem == 'call':
            # call is a special case: we analyse the target functions's flow to determine
            # the likely parameters.
            
            expr, spoils = self.get_call_expression(ea)
            yield expr
            
        elif mnem == 'lea':
            #~ assert insn.Op1.type == 1
            
            dst = self.get_operand_expression(ea, 0)
            op = self.get_operand_expression(ea, 1)
            
            expr = assign_t(dst, address_t(op))
            yield expr
            
        elif mnem == 'not':
            
            op = self.get_operand_expression(ea, 0)
            
            expr = assign_t(op.copy(), not_t(op))
            yield expr
            
        elif mnem == 'neg':
            
            op = self.get_operand_expression(ea,0)
            
            expr = assign_t(op.copy(), neg_t(op))
            yield expr
            
        elif mnem in ('mov', 'movzx', 'movsxd', 'movsx'):
            
            dst = self.get_operand_expression(ea, 0)
            op = self.get_operand_expression(ea, 1)
            
            expr = assign_t(dst, op)
            yield expr
            
        elif mnem in ('inc', 'dec'):
            choices = {'inc': add_t, 'dec': sub_t}
            
            op1 = self.get_operand_expression(ea, 0)
            op2 = value_t(1, self.address_size)
            
            expr = (choices[mnem])(op1, op2)
            
            # CF is unaffected
            for _expr in self.evaluate_flags(expr, PF | AF | ZF | SF | OF):
                yield _expr
            
            yield assign_t(op1.copy(), expr)
            
        elif mnem in ('add', 'sub'):
            choices = {'add': add_t, 'sub': sub_t}
            
            op1 = self.get_operand_expression(ea, 0)
            op2 = self.get_operand_expression(ea, 1)
            
            expr = (choices[mnem])(op1, op2)
            
            for _expr in self.evaluate_flags(expr, CF | PF | AF | ZF | SF | OF):
                yield _expr
            
            yield assign_t(op1.copy(), expr)
            
        elif mnem in ('imul', ):
            choices = {'imul': mul_t, }
            
            op1 = self.get_operand_expression(ea, 0)
            op2 = self.get_operand_expression(ea, 1)
            
            expr = (choices[mnem])(op1, op2)
            
            #~ # TODO: SF, ZF, AF, PF is undefined
            #~ # TODO: CF, OF is defined..
            
            yield assign_t(op1.copy(), expr)
            
        elif mnem in ('xor', 'or', 'and'):
            choices = {'xor': xor_t, 'or': or_t, 'and': and_t}
            
            op1 = self.get_operand_expression(ea, 0)
            op2 = self.get_operand_expression(ea, 1)
            
            expr = (choices[mnem])(op1, op2)
            
            for _expr in self.set_flags(CF | OF, value=0):
                yield _expr
            # TODO: AF is undefined
            for _expr in self.evaluate_flags(expr, PF | ZF | SF):
                yield _expr
            
            yield assign_t(op1.copy(), expr)
            
        elif mnem in ('shl', 'shr', 'sal', 'sar'):
            choices = {'shr': shr_t, 'shl': shl_t, 'sar': shr_t, 'sal': shl_t}
            
            op1 = self.get_operand_expression(ea, 0)
            op2 = self.get_operand_expression(ea, 1)
            
            expr = (choices[mnem])(op1, op2)
            
            for _expr in self.evaluate_flags(expr, CF | PF | AF | ZF | SF | OF):
                yield _expr
            
            yield assign_t(op1.copy(), expr)
            
        elif mnem == "retn":
            #~ assert insn.Op1.type in (0, 5)
            
            #~ if insn.Op1.type == 5:
                #~ # stack pointer adjusted from return
                #~ op = self.get_operand(ea, insn.Op1)
                #~ expr = assign_t(self.stackreg.copy(), add_t(self.stackreg.copy(), op))
                #~ yield expr
            
            expr = return_t(self.resultreg.copy())
            yield expr
            
        elif mnem == 'cmp':
            # The comparison is performed by subtracting the second operand from 
            # the first operand and then setting the status flags in the same manner 
            # as the SUB instruction.
            
            op1 = self.get_operand_expression(ea, 0)
            op2 = self.get_operand_expression(ea, 1)
            
            for expr in self.evaluate_flags(sub_t(op1, op2), CF | PF | AF | ZF | SF | OF):
                yield expr
            
        elif mnem == 'test':
            
            op1 = self.get_operand_expression(ea, 0)
            op2 = self.get_operand_expression(ea, 1)
            
            for expr in self.set_flags(CF | OF, value=0):
                yield expr
            
            # TODO: AF is undefined..
            
            for expr in self.evaluate_flags(and_t(op1, op2), PF | ZF | SF):
                yield expr
            
        elif mnem == 'jmp':
            # control flow instruction...
            
            dst = self.get_operand_expression(ea, 0)
            
            if type(dst) == value_t and self.get_function_start(dst.value) == dst.value:
                # target of jump is a function.
                # let's assume that this is tail call optimization.
                
                expr = return_t(call_t(dst, None))
                yield expr
                
                #~ block.return_expr = expr
            
            elif type(dst) == value_t:
                expr = goto_t(dst)
                yield expr
            else:
                expr = jmpout_t(dst)
                yield expr
        
        elif mnem in ('cmova', 'cmovae', 'cmovb', 'cmovbe', 'cmovc', 'cmove', 'cmovg',
                        'cmovge', 'cmovl', 'cmovle', 'cmovna', 'cmovnae', 'cmovbe', 
                        'cmovnc', 'cmovne', 'cmovng', 'cmovnge', 'cmovnl', 'cmovnle',
                        'cmovno', 'cmovnp', 'cmovns', 'cmovnz', 'cmovo', 'cmovp', 
                        'cmovpe', 'cmovpo', 'cmovs', 'cmovz'):
            # CMOVcc (conditional mov)
            
            op1 = self.get_operand_expression(ea, 0)
            op2 = self.get_operand_expression(ea, 1)
            
            if mnem == 'cmova':
                cond = b_and_t(b_not_t(self.zf.copy()), b_not_t(self.cf.copy()))
            elif mnem in ('cmovae', 'cmovnb', 'cmovnc'):
                cond = b_not_t(self.cf.copy())
            elif mnem in ('cmovb', 'cmovc', 'cmovnae'):
                cond = self.cf.copy()
            elif mnem == 'cmovbe':
                cond = b_or_t(self.zf.copy(), self.cf.copy())
            elif mnem == 'cmove':
                cond = self.zf.copy()
            elif mnem in ('cmovg', 'cmovnle'):
                cond = b_and_t(b_not_t(self.zf.copy()), eq_t(self.sf.copy(), self.of.copy()))
            elif mnem in ('cmovge', 'cmovnl'):
                cond = eq_t(self.sf.copy(), self.of.copy())
            elif mnem in ('cmovl', 'cmovnge'):
                cond = neq_t(self.sf.copy(), self.of.copy())
            elif mnem in ('cmovle', 'cmovng'):
                cond = b_or_t(self.zf.copy(), neq_t(self.sf.copy(), self.of.copy()))
            elif mnem == 'cmovna':
                cond = b_or_t(self.zf.copy(), self.cf.copy(), )
            elif mnem == 'cmovnbe':
                cond = b_and_t(b_not_t(self.zf.copy()), b_not_t(self.cf.copy()))
            elif mnem in ('cmovnz', 'cmovne'):
                cond = b_not_t(self.zf.copy())
            elif mnem in ('cmovno', ):
                cond = b_not_t(self.of.copy())
            elif mnem in ('cmovnp', 'cmovpo'):
                cond = b_not_t(self.pf.copy())
            elif mnem in ('cmovns', ):
                cond = b_not_t(self.sf.copy())
            elif mnem in ('cmovo', ):
                cond = self.of.copy()
            elif mnem in ('cmovo', ):
                cond = self.of.copy()
            elif mnem in ('cmovp', 'cmovpe'):
                cond = self.pf.copy()
            elif mnem in ('cmovs', ):
                cond = self.sf.copy()
            elif mnem in ('cmovz', ):
                cond = self.zf.copy()
            
            expr = assign_t(op1.copy(), ternary_if_t(cond, op2, op1))
            yield expr
        
        elif mnem in ('seta', 'setae', 'setb', 'setbe', 'setc', 'sete', 'setg',
                        'setge', 'setl', 'setle', 'setna', 'setnae', 'setbe', 
                        'setnc', 'setne', 'setng', 'setnge', 'setnl', 'setnle',
                        'setno', 'setnp', 'setns', 'setnz', 'seto', 'setp', 
                        'setpe', 'setpo', 'sets', 'setz'):
            
            op1 = self.get_operand_expression(ea, 0)
            
            # http://faydoc.tripod.com/cpu/setnz.htm
            if mnem == 'seta':
                cond = b_and_t(b_not_t(self.zf.copy()), b_not_t(self.cf.copy()))
            elif mnem in ('setae', 'setnb', 'setnc'):
                cond = b_not_t(self.cf.copy())
            elif mnem in ('setb', 'setc', 'setnae'):
                cond = self.cf.copy()
            elif mnem == 'setbe':
                cond = b_or_t(self.zf.copy(), self.cf.copy())
            elif mnem == 'sete':
                cond = self.zf.copy()
            elif mnem in ('setg', 'setnle'):
                cond = b_and_t(b_not_t(self.zf.copy()), eq_t(self.sf.copy(), self.of.copy()))
            elif mnem in ('setge', 'setnl'):
                cond = eq_t(self.sf.copy(), self.of.copy())
            elif mnem in ('setl', 'setnge'):
                cond = neq_t(self.sf.copy(), self.of.copy())
            elif mnem in ('setle', 'setng'):
                cond = b_or_t(self.zf.copy(), neq_t(self.sf.copy(), self.of.copy()))
            elif mnem == 'setna':
                cond = b_or_t(self.zf.copy(), self.cf.copy(), )
            elif mnem == 'setnbe':
                cond = b_and_t(b_not_t(self.zf.copy()), b_not_t(self.cf.copy()))
            elif mnem in ('setnz', 'setne'):
                cond = b_not_t(self.zf.copy())
            elif mnem in ('setno', ):
                cond = b_not_t(self.of.copy())
            elif mnem in ('setnp', 'setpo'):
                cond = b_not_t(self.pf.copy())
            elif mnem in ('setns', ):
                cond = b_not_t(self.sf.copy())
            elif mnem in ('seto', ):
                cond = self.of.copy()
            elif mnem in ('seto', ):
                cond = self.of.copy()
            elif mnem in ('setp', 'setpe'):
                cond = self.pf.copy()
            elif mnem in ('sets', ):
                cond = self.sf.copy()
            elif mnem in ('setz', ):
                cond = self.zf.copy()
            
            expr = assign_t(op1, cond)
            yield expr
        
        elif mnem in self.conditional_jumps:
            # we do not distinguish between signed and unsigned comparision here.
            
            if mnem == 'jns':
                # jump if sign bit is clear
                cond = b_not_t(self.sf.copy())
            elif mnem == 'js':
                # jump if sign bit is set
                cond = self.sf.copy()
            elif mnem == 'jnz': # jne
                # jump if zero bit is clear
                cond = b_not_t(self.zf.copy())
            elif mnem == 'jz': # je
                # jump if zero bit is set
                cond = self.zf.copy()
            elif mnem == 'jno':
                # jump if overflow bit is clear
                cond = b_not_t(self.of.copy())
            elif mnem == 'jo':
                # jump if overflow bit is set
                cond = self.of.copy()
            elif mnem == 'jnb': # jae jnc
                # jump if carry bit is clear
                cond = b_not_t(self.cf.copy())
            elif mnem == 'jb': # jnae jc
                # jump if carry bit is set
                cond = self.cf.copy()
            elif mnem == 'jbe': # jna
                # jump if below or equal
                cond = b_or_t(self.zf.copy(), self.cf.copy())
            elif mnem == 'ja': # jnbe
                # jump if above
                cond = b_and_t(b_not_t(self.zf.copy()), b_not_t(self.cf.copy()))
            elif mnem == 'jl': # jnge
                # jump if less
                cond = neq_t(self.sf.copy(), self.of.copy())
            elif mnem == 'jge': # jnl
                # jump if greater or equal
                cond = eq_t(self.sf.copy(), self.of.copy())
            elif mnem == 'jle': # jng
                # jump if less or equal
                cond = b_or_t(self.zf.copy(), neq_t(self.sf.copy(), self.of.copy()))
            elif mnem == 'jg': # jnle
                # jump if greater
                cond = b_and_t(b_not_t(self.zf.copy()), eq_t(self.sf.copy(), self.of.copy()))
            elif mnem == 'jpe': # jp
                # jump if parity even
                cond = self.pf.copy()
            elif mnem == 'jpo': # jnp
                # jump if parity odd
                cond = b_not_t(self.pf.copy())
            else:
                raise RuntimeError('unknown jump mnemonic')
            
            dst = self.get_operand_expression(ea, 0)
            goto = goto_t(dst)
            
            expr = if_t(cond, container_t([goto, ]))
            yield expr
            
            # add goto for false side of condition
            
            dst = value_t(self.next_instruction_ea(ea), self.address_size)
            expr = goto_t(dst)
            yield expr
            
        else:
            raise RuntimeError('%x: not yet handled instruction: %s ' % (ea, mnem))
        
        return

class ir_intel_x86(ir_intel):
    def __init__(self):
        self.address_size = 32
        ir_intel.__init__(self)
        self.registers = ['eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi']
        return
    
    def get_register_size(self, which):
        return 32
    

class ir_intel_x64(ir_intel):
    def __init__(self):
        self.address_size = 64
        ir_intel.__init__(self)
        self.registers = ['rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi', 'r8', 'r9', 'r10', 'r11', 'r12']
        return
    
    def get_register_size(self, which):
        return 64
    

########NEW FILE########
__FILENAME__ = c

from expressions import *
from statements import *

# list of all tokens that can appear in the output. 
CHARACTER = 0       # comma, colon, semicolon, space, etc.
LMATCH = 1          # left matching character (eg. left parenthesis, left bracket, etc)
RMATCH = 2          # right matching character (eg. right parenthesis, right bracket, etc)
KEYWORD = 3         # keywords: if, while, etc.
VAR = 4             # any variable: registers, argument, stack var, function name, etc
STRING = 5          # a zero-terminated C string.
NUMBER = 6          # a number.
GLOBAL = 7          # a location in the database

class token(object):
    """ base class for tokens """
    def __init__(self, id):
        self.id = id
        return

class token_character(token):
    """ character token """
    
    def __init__(self, char):
        token.__init__(self, CHARACTER)
        self.char = char
        return
    
    def __str__(self):
        return self.char

class token_lmatch(token):
    """ matching character token """
    
    def __init__(self, char):
        token.__init__(self, LMATCH)
        self.char = char
        self.rmatch = None
        return
    
    def __str__(self):
        return self.char

class token_rmatch(token):
    """ matching character token """
    
    def __init__(self, char):
        token.__init__(self, RMATCH)
        self.char = char
        self.lmatch = None
        return
    
    def __str__(self):
        return self.char

class token_keyword(token):
    """ keyword token """
    
    def __init__(self, kw):
        token.__init__(self, KEYWORD)
        self.kw = kw
        return
    
    def __str__(self):
        return self.kw

class token_var(token):
    """ variable token """
    
    def __init__(self, name):
        token.__init__(self, VAR)
        self.name = name
        return
    
    def __str__(self):
        return self.name

class token_string(token):
    """ string token """
    
    def __init__(self, value):
        token.__init__(self, STRING)
        self.value = value
        return
    
    def __str__(self):
        return repr(self.value)

class token_number(token):
    """ number token """
    
    def __init__(self, value):
        token.__init__(self, NUMBER)
        self.value = value
        return
    
    def __str__(self):
        return str(self.value)

class token_global(token):
    """ number token """
    
    def __init__(self, value):
        token.__init__(self, GLOBAL)
        self.value = value
        return
    
    def __str__(self):
        return str(self.value)

class tokenizer(object):
    """ Tokenizer class for C.
    
    This class transforms the syntax tree into a flat list of tokens.
    """
    
    def __init__(self, flow):
        self.flow = flow
        self.arch = flow.arch
        return
    
    def flow_tokens(self):
        
        name = self.arch.get_ea_name(self.flow.entry_ea)
        yield token_var(name)
        
        l,r = self.matching('(', ')')
        yield l
        yield r
        yield token_character(' ')
        
        l,r = self.matching('{', '}')
        yield l
        yield token_character('\n')
        
        for block in self.flow.iterblocks():
            
            if block.jump_from:
                yield token_character('\n')
                yield token_global('loc_%x' % (block.ea, ))
                yield token_character(':')
                yield token_character('\n')
            
            for tok in self.statement_tokens(block.container, indent=1):
                yield tok
        
        yield r
        
        return
    
    def regname(self, which):
        """ returns the register name without index """
        return self.arch.get_regname(which)
    
    def matching(self, lchar, rchar):
        ltok = token_lmatch(lchar)
        rtok = token_lmatch(rchar)
        ltok.rmatch = rtok
        rtok.lmatch = ltok
        return ltok, rtok
    
    def parenthesize(self, obj):
        """ parenthesize objects as needed. """
        
        if type(obj) not in (regloc_t, flagloc_t, value_t, var_t, arg_t) or \
                (type(obj) in (regloc_t, flagloc_t) and obj.index is not None):
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj):
                yield tok
            yield r
        else:
            for tok in self.expression_tokens(obj):
                yield tok
        
        return
    
    def expression_tokens(self, obj):
        
        if type(obj) in (regloc_t, flagloc_t):
            if obj.name:
                name = obj.name
            else:
                name = self.regname(obj.which)
            if obj.index is not None:
                name += '@%u' % obj.index
            yield token_var(name)
            return
        
        if type(obj) in (deref_t, ):
            yield token_character(obj.operator)
            for tok in self.parenthesize(obj.op):
                yield tok
            if obj.index is not None:
                yield token_character('@%u' % (obj.index, ))
            return
        
        if type(obj) == value_t:
            
            s = self.arch.get_string(obj.value)
            if s:
                yield token_string(s)
                return
            
            s = self.arch.get_ea_name(obj.value)
            if s:
                yield token_global(s)
                return
            
            yield token_number(obj.value)
            return
        
        if type(obj) == var_t:
            yield token_var(obj.name)
            return
        
        if type(obj) == arg_t:
            name = obj.name
            #if type(obj.where) == regloc_t:
                #name += '<%s>' % (self.to_text(obj.where), )
            yield token_var(name)
            return
        
        if type(obj) == call_t:
            
            if type(obj.fct) == value_t:
                name = self.arch.get_ea_name(obj.fct.value)
                if name:
                    yield token_global(name)
                else:
                    yield token_number(obj.fct.value)
            else:
                for tok in self.parenthesize(obj.fct):
                    yield tok
            
            l, r = self.matching('(', ')')
            yield l
            if obj.params is not None:
                for tok in self.expression_tokens(obj.params):
                    yield tok
            yield r
            
            return
        
        if type(obj) == comma_t: # op1, op2
            for tok in self.expression_tokens(obj.op1):
                yield tok
            yield token_character(',')
            yield token_character(' ')
            for tok in self.expression_tokens(obj.op2):
                yield tok
            return
        
        if type(obj) in (not_t, b_not_t, address_t, neg_t, preinc_t, predec_t):
            yield token_character(obj.operator)
            for tok in self.parenthesize(obj.op):
                yield tok
            return
        
        if type(obj) in (postinc_t, postdec_t):
            for tok in self.parenthesize(obj.op):
                yield tok
            yield token_character(obj.operator)
            return
        
        if type(obj) in (assign_t, add_t, sub_t, mul_t, div_t, shl_t, shr_t, xor_t, and_t, \
                            or_t, b_and_t, b_or_t, eq_t, neq_t, leq_t, aeq_t, lower_t, above_t):
            for tok in self.expression_tokens(obj.op1):
                yield tok
            yield token_character(' ')
            yield token_character(obj.operator)
            yield token_character(' ')
            for tok in self.expression_tokens(obj.op2):
                yield tok
            return
        
        if type(obj) == ternary_if_t:
            
            for tok in self.parenthesize(obj.op1):
                yield tok
            yield token_character(' ')
            yield token_character(obj.operator1)
            yield token_character(' ')
            for tok in self.parenthesize(obj.op2):
                yield tok
            yield token_character(' ')
            yield token_character(obj.operator2)
            yield token_character(' ')
            for tok in self.parenthesize(obj.op3):
                yield tok
            
            return
        
        if type(obj) == sign_t:
            yield token_keyword('SIGN')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.op):
                yield tok
            yield r
            return
        
        if type(obj) == overflow_t:
            yield token_keyword('OVERFLOW')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.op):
                yield tok
            yield r
            return
        
        if type(obj) == parity_t:
            yield token_keyword('PARITY')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.op):
                yield tok
            yield r
            return
    
        if type(obj) == adjust_t:
            yield token_keyword('ADJUST')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.op):
                yield tok
            yield r
            return
        
        if type(obj) == carry_t:
            yield token_keyword('CARRY')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.op):
                yield tok
            yield r
            return
        
        raise ValueError('cannot display object of type %s' % (obj.__class__.__name__, ))
    
    def statement_tokens(self, obj, indent=0):
        
        if type(obj) == statement_t:
            for tok in self.expression_tokens(obj.expr):
                yield tok
            yield token_character(';')
            return
        
        if type(obj) == container_t:
            for stmt in obj:
                yield token_character('   ' * indent)
                for tok in self.statement_tokens(stmt, indent+1):
                    yield tok
                yield token_character('\n')
            return
        
        if type(obj) == if_t:
            yield token_character('   ' * indent)
            yield token_keyword('if')
            yield token_character(' ')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.expr):
                yield tok
            yield r
            yield token_character(' ')
            
            l, r = self.matching('{', '}')
            yield l
            yield token_character('\n')
            for tok in self.statement_tokens(obj.then_expr, indent+1):
                yield tok
            yield token_character('   ' * indent)
            yield r
            
            if obj.else_expr:
                yield token_character('\n')
                yield token_character('   ' * indent)
                yield token_keyword('else')
                yield token_character(' ')
                
                if len(obj.else_expr) == 1 and type(obj.else_expr[0]) == if_t:
                    for tok in self.statement_tokens(obj.else_expr, indent):
                        yield tok
                else:
                    l, r = self.matching('{', '}')
                    yield l
                    yield token_character('\n')
                    for tok in self.statement_tokens(obj.else_expr, indent+1):
                        yield tok
                    yield token_character('   ' * indent)
                    yield r
            
            return
        
        if type(obj) == while_t:
            
            yield token_character('   ' * indent)
            yield token_keyword('while')
            yield token_character(' ')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.expr):
                yield tok
            yield r
            yield token_character(' ')
            
            l, r = self.matching('{', '}')
            yield l
            yield token_character('\n')
            for tok in self.statement_tokens(obj.loop_container, indent+1):
                yield tok
            yield token_character('   ' * indent)
            yield r
            
            return
        
        if type(obj) == do_while_t:
            
            yield token_character('   ' * indent)
            yield token_keyword('do')
            l, r = self.matching('{', '}')
            yield l
            yield token_character('\n')
            for tok in self.statement_tokens(obj.loop_container, indent+1):
                yield tok
            yield token_character('   ' * indent)
            yield r
            
            yield token_character(' ')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.expr):
                yield tok
            yield r
            yield token_character(' ')
            yield token_character(';')
            
            return
        
        if type(obj) == goto_t:
            yield token_keyword('goto')
            yield token_character(' ')
            
            if type(obj.expr) == value_t:
                yield token_global('loc_%x' % (obj.expr.value, ))
            else:
                for tok in self.expression_tokens(obj.expr):
                    yield tok
            
            yield token_character(';')
            return
        
        if type(obj) == return_t:
            yield token_keyword('return')
            if obj.expr:
                yield token_character(' ')
                for tok in self.expression_tokens(obj.expr):
                    yield tok
            yield token_character(';')
            return

        if type(obj) == break_t:
            yield token_keyword('break')
            yield token_character(';')
            return
        
        if type(obj) == continue_t:
            yield token_keyword('continue')
            yield token_character(';')
            return
        
        raise ValueError('cannot display object of type %s' % (obj.__class__.__name__, ))




########NEW FILE########
__FILENAME__ = ssa
""" Transform the program flow in SSA form.

"""

from statements import *
from expressions import *

class tag_context_t(object):
    """ holds a list of registers that are live while the tagger runs """
    
    index = 0
    
    def __init__(self):
        
        self.map = []
        
        return
    
    def copy(self):
        new = tag_context_t()
        new.map = self.map[:]
        return new
    
    def get_definition(self, reg):
        """ get an earlier definition of 'reg'. """
        
        for _reg, _stmt in self.map:
            if _reg.no_index_eq(reg):
                return _reg, _stmt
        
        return
    
    def remove_definition(self, reg):
        
        for _reg, _stmt in self.map:
            if _reg.no_index_eq(reg):
                self.map.remove((_reg, _stmt))
        
        return
    
    def new_definition(self, reg, stmt):
        
        for _reg, _stmt in self.map:
            if _reg.no_index_eq(reg):
                self.map.remove((_reg, _stmt))
        
        reg.index = tag_context_t.index
        tag_context_t.index += 1
        
        self.map.append((reg, stmt))
        
        return

class ssa_tagger_t():
    """ this class follows all paths in the function and tags registers.
    The main task here is to differenciate all memory locations from each
    other, so that each time a register is reassigned it is considered
    different from previous assignments. After doing this, the function flow
    should be in a form somewhat similar to static single assignment
    form, where all locations are defined once and possibly used zero, one or 
    multiple times. What we do differs from SSA form in the following way:
    
    It may happen that a register is defined in multiple paths that merge
    together where it is used without first being reassigned. An example
    of such case:
    
        if(foo)
            eax = 1
        else
            eax = 0
        return eax;
    
    This causes problems because in SSA form, a location must have one
    definition at most. In Van Emmerick's 2007 paper on SSA, this is 
    solved by adding O-functions with which all definitions from previous 
    paths are merged into a single new defintion, like this:
    
        if(foo)
            eax@0 = 1
        else
            eax@1 = 0
        eax@2 = O(eax@0, eax@1)
        return eax@2
    
    The form above respects the SSA form but impacts greatly on code 
    simplicity when it comes to solving O-functions through recursive
    code. What we do is a little bit different, somewhat simpler and
    gives results that are just as 'correct' (or at least they should).
    The tagger will not insert O-functions, but instead, for any register 
    with multiple merging definitions it will insert one intermediate 
    definition in each code path like this:
    
        if(foo)
            eax@0 = 1
            eax@2 = eax@0
        else
            eax@1 = 0
            eax@2 = eax@1
        return eax@2
    
    This makes it very easy to later replace uses of eax@0 and eax@1 
    by their respective definitions, just the way we would for paths 
    without 'merging' registers. This also solves the case of recursive 
    code paths without extra code.
    """
    
    def __init__(self, flow):
        self.flow = flow
        
        # keep track of any block which we have already walked into, because at
        # this stage we may still encounter recursion (gotos that lead backwards).
        self.done_blocks = []
        
        self.tagged_pairs = []
        
        self.fct_arguments = []
        
        return
    
    def get_defs(self, expr):
        return [defreg for defreg in expr.iteroperands() if isinstance(defreg, assignable_t) and defreg.is_def]
    
    def get_uses(self, expr):
        return [defreg for defreg in expr.iteroperands() if isinstance(defreg, assignable_t) and not defreg.is_def]
    
    def get_block_externals(self, block):
        """ return all externals for a single block. at this stage, blocks are very flat, and ifs
        should contain only gotos, so doing this with a simple loop like below should be safe """
        
        externals = []
        context = []
        
        for stmt in block.container.statements:
            
            uses = self.get_uses(stmt.expr)
            for use in uses:
                if use not in context:
                    in_external = False
                    for external, _stmt in externals:
                        if external == use:
                            in_external = True
                            break
                    if not in_external:
                        externals.append((use, stmt))
            
            defs = self.get_defs(stmt.expr)
            for _def in defs:
                context.append(_def)
        
        return externals
    
    #~ def find_call(self, stmt):
        
        #~ if type(stmt.expr) == call_t:
            #~ return stmt.expr
        
        #~ if type(stmt.expr) == assign_t and type(stmt.expr.op2) == call_t:
            #~ return stmt.expr.op2
        
        #~ return
    
    def tag_expression(self, block, container, stmt, expr, context):
        
        if not expr:
            return
        
        defs = self.get_defs(expr)
        uses = self.get_uses(expr)
        
        for use in uses:
            old_def = context.get_definition(use)
            if old_def:
                reg, _ = old_def
                use.index = reg.index
        
        for _def in defs:
            context.new_definition(_def, stmt)
        
        return
    
    def tag_statement(self, block, container, stmt, context):
        
        if type(stmt) == if_t:
            self.tag_expression(block, container, stmt, stmt.expr, context)
            
            self.tag_container(block, stmt.then_expr, context)
            
            assert stmt.else_expr is None, 'at this stage there should be no else-branch'
        
        elif type(stmt) == goto_t:
            ea = stmt.expr.value
            to_block = self.flow.blocks[ea]
            self.tag_block(block, to_block, context.copy())
        
        elif type(stmt) in (statement_t, return_t, jmpout_t):
            self.tag_expression(block, container, stmt, stmt.expr, context)
        
        else:
            raise RuntimeError('unknown statement type: %s' % (repr(stmt), ))
        
        return
    
    def tag_container(self, block, container, context):
        
        for stmt in container[:]:
            self.tag_statement(block, container, stmt, context)
            
        return
    
    def tag_block(self, parent, block, context):
        
        externals = [(reg, stmt) for reg, stmt in self.get_block_externals(block)]
        
        for external, stmt in externals:
            # add assignation to this instance of the register in any earlier block that affects
            # this register in the current contect.
            _earlier_def = context.get_definition(external)
            
            # each register which is used in a block without being first defined
            # becomes its own definition, therefore we need to introduce these 
            # as definitions into the current context.
            if external.index is None:
                self.fct_arguments.append(external)
                context.new_definition(external, stmt)
            
            if not _earlier_def:
                continue
            
            _reg, _stmt = _earlier_def
            
            if _reg == external:
                continue
            
            # prevent inserting the same assignation multiple times
            pair = (external, _reg)
            if pair in self.tagged_pairs:
                continue
            self.tagged_pairs.append(pair)
            
            if type(_stmt) == if_t:
                # the definition is part of the expression in a if_t. this is a special case where
                # we insert the assignment before the if_t.
                expr = assign_t(external.copy(), _reg.copy())
                _stmt.container.insert(_stmt.index(), statement_t(expr))
            else:
                # insert the new assignation
                expr = assign_t(external.copy(), _reg.copy())
                _stmt.container.insert(_stmt.index()+1, statement_t(expr))
        
        if block in self.done_blocks:
            return
        
        self.done_blocks.append(block)
        
        self.tag_container(block, block.container, context.copy())
        
        return
    
    def tag(self):
        
        self.done_blocks = []
        
        context = tag_context_t()
        self.tag_block(None, self.flow.entry_block, context)
        
        return

########NEW FILE########
__FILENAME__ = statements

from expressions import *

class statement_t(object):
    """ defines a statement containing an expression. """
    
    def __init__(self, expr):
        self.expr = expr
        self.container = None
        #~ print repr(self['expr'])
        return
    
    def index(self):
        """ return the statement index inside its parent 
            container, or None if container is None """
        if self.container is None:
            return
        return self.container.index(self)
    
    def remove(self):
        """ removes the statement from its container. return True if 
            container is not None and the removal succeeded. """
        if self.container is None:
            return
        return self.container.remove(self)
    
    @property
    def expr(self):
        return self.__expr
    
    @expr.setter
    def expr(self, value):
        if value is not None:
            assert isinstance(value, replaceable_t), 'expr is not replaceable'
            value.parent = (self, 'expr')
        self.__expr = value
        return
    
    def __getitem__(self, key):
        assert key in ('expr', )
        if key == 'expr':
            return self.expr
        else:
            raise IndexError('key not supported')
        return
    
    def __setitem__(self, key, value):
        assert key in ('expr', )
        if key == 'expr':
            self.expr = value
        else:
            raise IndexError('key not supported')
        return
    
    def __repr__(self):
        return '<statement %s>' % (repr(self.expr), )
    
    @property
    def statements(self):
        """ by default, no statements are present in this one. """
        return []
    
    @property
    def containers(self):
        """ by default, no containers are present in this one. """
        return []

class container_t(object):
    """ a container contains statements. """
    
    def __init__(self, __list=None):
        self.__list = __list or []
        for item in self.__list:
            item.container = self
        return
    
    def __repr__(self):
        return repr(self.__list)
    
    def __len__(self):
        return len(self.__list)
    
    def __getitem__(self, key):
        return self.__list[key]
    
    def __setitem__(self, key, value):
        if type(key) == slice:
            for item in value:
                assert isinstance(item, statement_t), 'cannot set non-statement to container'
                item.container = self
        else:
            assert isinstance(value, statement_t), 'cannot set non-statement to container'
            value.container = self
        self.__list.__setitem__(key, value)
        return
    
    def iteritems(self):
        for i in range(len(self.__list)):
            yield i, self.__list[i]
        return
    
    @property
    def statements(self):
        for item in self.__list:
            yield item
        return
    
    def add(self, stmt):
        assert isinstance(stmt, statement_t), 'cannot add non-statement: %s' % (repr(stmt), )
        self.__list.append(stmt)
        stmt.container = self
        return
    
    def extend(self, _new):
        for stmt in _new:
            assert isinstance(stmt, statement_t), 'cannot add non-statement to container'
            stmt.container = self
            self.__list.append(stmt)
        return
    
    def insert(self, key, _new):
        assert isinstance(_new, statement_t), 'cannot add non-statement: %s' % (repr(stmt), )
        self.__list.insert(key, _new)
        _new.container = self
        return
    
    def pop(self, key=-1):
        stmt = self.__list.pop(key)
        if stmt:
            stmt.container = None
        return stmt
    
    def index(self, stmt):
        return self.__list.index(stmt)
    
    def __iter__(self):
        for item in self.__list:
            yield item
        return
    
    def remove(self, stmt):
        if stmt in self.__list:
            stmt.container = None
        return self.__list.remove(stmt)

class if_t(statement_t):
    """ if_t is a statement containing an expression and a then-side, 
        and optionally an else-side. """
    
    def __init__(self, expr, then):
        statement_t.__init__(self, expr)
        assert isinstance(then, container_t), 'then-side must be container_t'
        self.then_expr = then
        self.else_expr = None
        return
    
    def __repr__(self):
        return '<if %s then %s else %s>' % (repr(self.expr), \
            repr(self.then_expr), repr(self.else_expr))
    
    @property
    def statements(self):
        for stmt in self.then_expr.statements:
            yield stmt
        if self.else_expr:
            for stmt in self.else_expr.statements:
                yield stmt
        return
    
    @property
    def containers(self):
        yield self.then_expr
        if self.else_expr:
            yield self.else_expr
        return

class while_t(statement_t):
    """ a while_t statement of the type 'while(expr) { ... }'. """
    
    def __init__(self, expr, loop_container):
        statement_t.__init__(self, expr)
        assert isinstance(loop_container, container_t), '2nd argument to while_t must be container_t'
        self.loop_container = loop_container
        return
    
    def __repr__(self):
        return '<while %s do %s>' % (repr(self.expr), repr(self.loop_container))
    
    @property
    def statements(self):
        for stmt in self.loop_container:
            yield stmt
        return
    
    @property
    def containers(self):
        yield self.loop_container
        return

class do_while_t(statement_t):
    """ a do_while_t statement of the type 'do { ... } while(expr)'. """
    
    def __init__(self, expr, loop_container):
        statement_t.__init__(self, expr)
        assert isinstance(loop_container, container_t), '2nd argument to while_t must be container_t'
        self.loop_container = loop_container
        return
    
    def __repr__(self):
        return '<do %s while %s>' % (repr(self.loop_container), repr(self.expr), )
    
    @property
    def statements(self):
        for stmt in self.loop_container:
            yield stmt
        return
    
    @property
    def containers(self):
        yield self.loop_container
        return

class goto_t(statement_t):
    
    def __init__(self, dst):
        assert type(dst) == value_t
        statement_t.__init__(self, dst)
        return
    
    def __eq__(self, other):
        return type(other) == goto_t and self.expr == other.expr
    
    def __repr__(self):
        s = hex(self.expr.value) if type(self.expr) == value_t else str(self.expr)
        return '<goto %s>' % (s, )

class jmpout_t(statement_t):
    """ this is a special case of goto where the address is outside the function. """
    
    def __init__(self, dst):
        statement_t.__init__(self, dst)
        return
    
    def __eq__(self, other):
        return type(other) == self.__class__ and self.expr == other.expr
    
    def __repr__(self):
        s = hex(self.expr.value) if type(self.expr) == value_t else str(self.expr)
        return '<jmp out %s>' % (s, )

class return_t(statement_t):
    def __init__(self, expr=None):
        statement_t.__init__(self, expr)
        return
    
    def __repr__(self):
        return '<return %s>' % (repr(self.expr) if self.expr else 'void', )

class break_t(statement_t):
    def __init__(self):
        statement_t.__init__(self, None)
        return
    
    def __repr__(self):
        return '<break>'

class continue_t(statement_t):
    def __init__(self):
        statement_t.__init__(self, None)
        return
    
    def __repr__(self):
        return '<continue>'


########NEW FILE########
