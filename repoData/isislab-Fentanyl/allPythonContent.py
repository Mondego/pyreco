__FILENAME__ = AssembleForm
"""
AssembleForm.py

Form for assembling into the IDB with Fentanyl. 

"""
import idaapi

class AssembleForm(object):
    """ Form elements for Fentanyl """
    def __init__(self):
        """ Initialize form elements """
        self.ui_cntls = {
            'inp':idaapi.Form.MultiLineTextControl('', idaapi.textctrl_info_t.TXTF_FIXEDFONT),
            'opt_chk':idaapi.Form.ChkGroupControl(('fixup', 'nopout')),
            'form_cb':idaapi.Form.FormChangeCb(self._form_cb),
        }
        self.ui_form = idaapi.Form("""STARTITEM {id:inp}
BUTTON YES* Assemble
BUTTON NO NONE
BUTTON CANCEL Cancel
Fentanyl Assembler

{form_cb}
<:{inp}>
<Name fixups:{fixup}>
<Fill with NOPs:{nopout}>{opt_chk}>"""
        , self.ui_cntls)
        self.values = None
        self.ui_form.Compile()
        self.ui_form.opt_chk.value = 3

    def __del__(self):
        """ Clean up """
        for i in self.ui_cntls.values(): i.free()
        self.ui_form.Free()

    def _getvalue(self, cntl):
        """ Get value of the control """
        val = self.ui_form.GetControlValue(cntl)

        #Checkboxes get turned into a dict()
        if isinstance(cntl, idaapi.Form.ChkGroupControl):
            names = cntl.children_names
            opts = {}
            for i in range(len(names)):
                opts[names[i]] = val & (2**i)
            val = opts
        else:
            #MultiLineText controls require an extra step to get the text
            if isinstance(cntl, idaapi.Form.MultiLineTextControl):
                val = val.value
        return val

    def _form_cb(self, fid):
        """ Handle callbacks and grab control values """
        #Only continue if Assemble (OK) pressed
        if fid != -2: return

        self.values = dict([
            (k, self._getvalue(v))
            for k, v in self.ui_cntls.items()
            #Exclude the callback, it isn't a control
            if not isinstance(v, idaapi.Form.FormChangeCb)
        ])
        return True

    def process(self):
        """ Execute the form and return values """
        if not self.ui_form.Execute():
            self.values = None
        return self.values


########NEW FILE########
__FILENAME__ = CodeCaveFinder
try:
    from PySide import QtGui, QtCore
except ImportError:
    print "PySide unavailable, no CodeCaveFinder"
    QtCore = None
    QtGui = None
import idaapi, idc

class CodeCaveWindow(idaapi.PluginForm):
    def findCodeCavez(self, segment=".text"):
        start = idc.SegByBase(idc.SegByName(segment))
        if start == idc.BADADDR:
            print "Can't find segment %s" % (segment)
            return

        end = idc.SegEnd(start)

        curr_addr = start
        curr_size = 0
        biggest_addr = idc.BADADDR
        biggest_size = 0
        results = []
        while start < end:
            new_addr = idc.FindText(start + curr_size, idc.SEARCH_DOWN, 0, 0, "align")
            if start == new_addr:
                break
            curr_size = idc.ItemSize(new_addr)
            if curr_size > biggest_size:
                biggest_addr = new_addr
                biggest_size = curr_size
            start = new_addr
            results.append((new_addr, curr_size))

        return results
        return biggest_addr, biggest_size

    def addEntryToTree(self, segment, address, size):
        entry = QtGui.QTreeWidgetItem(self.tree)
        entry.setText(0, segment)
        entry.setText(1, "0x%x"%(address))
        entry.setText(2, ("%d"%(size)).zfill(10))
        # print dir(entry)

    def PopulateTree(self):
        self.tree.clear()
        executable_segments = [(idc.SegName(idaapi.getnseg(x).startEA), 0!=(idaapi.getnseg(x).perm & idaapi.SEGPERM_EXEC)) for x in range(idaapi.get_segm_qty())]
        for segment in executable_segments:
            if not segment[1]:
                continue
            caves = self.findCodeCavez(segment[0])
            for cave in caves:
                self.addEntryToTree(segment[0], cave[0], cave[1])

    def OnCreate(self, form):
        self.parent = self.FormToPySideWidget(form)
        self.tree = QtGui.QTreeWidget()
        self.tree.setHeaderLabels(("Segment","Address","Size"))
        self.tree.setColumnWidth(0, 100)
        self.tree.setSortingEnabled(True)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.tree)

        jump = QtGui.QPushButton("Jump To")
        jump.clicked.connect(self.jump)
        layout.addWidget(jump)

        search_again = QtGui.QPushButton("Go Spelunking")
        search_again.clicked.connect(self.PopulateTree)
        layout.addWidget(search_again)

        # self.PopulateTree()
        self.parent.setLayout(layout)

    def jump(self):
        current_item = self.tree.currentItem()
        if current_item:
            idc.Jump(int(current_item.text(1)[2:], 16))

########NEW FILE########
__FILENAME__ = Fentanyl
"""
Fentanyl.py

Main Fentanyl class.

"""

import idaapi
import idautils
import idc
import re
from Util import *

__all__ = ['Fentanyl']

#Generate a mapping between each set of jumps
_JUMPS = [
    ('jnb', 'jb'), ('jna', 'ja'),
    ('jnl', 'jl'), ('jng', 'jg'),
    ('jnbe', 'jbe'), ('jnae', 'jae'),
    ('jnle', 'jle'), ('jnge', 'jge'),
    ('jns', 'js'),
    ('jnp', 'jp'),
    ('jnz', 'jz'),
    ('jnc', 'jc'),
    ('jne', 'je'),
    ('jno', 'jo'),
]
#Generate the opposite mapping as well
_JUMPS = dict(_JUMPS + [i[::-1] for i in _JUMPS])

class Fentanyl(object):
    """ Manages assembling into an IDB and keeping track of undo/redo stacks """
    JUMPS = _JUMPS
    PART_RE = re.compile(r'(\W+)')
    def __init__(self):
        """ Initialize our data """
        self.undo_buffer = []
        self.redo_buffer = []

    def _pushundo(self, entries):
        """ Insert one state into the undo stack """
        self.undo_buffer.append(entries)

    def _pushredo(self, entries):
        """ Insert one state into the redo stack """
        self.redo_buffer.append(entries)

    def _popundo(self):
        """ Pop one state into the undo stack """
        return self.undo_buffer.pop() if self.undo_buffer else None

    def _popredo(self):
        """ Pop one state into the redo stack """
        return self.redo_buffer.pop() if self.redo_buffer else None

    def _statedo(self, n, rd_f, wr_f):
        entries = None
        for i in range(n):
            entries = rd_f()
            if not entries: return
            buf = []
            for data in entries:
                buf.append(
                    (data[0], read_data(data[0], len(data[1])))
                )
                write_data(data[0], data[1])
            #Apply to the other stack in reverse order
            wr_f(buf[::-1])

        #Jump to the first entry if an operation was performed
        if entries:
            idaapi.jumpto(entries[0][0])

        return entries

    def _getregvars(self, ea):
        """ Return all the regvar mappings as a dict """
        func = idaapi.get_func(ea)
        regvars = {}

        #XXX: Broken in idapython
        #mapping = {rv.user: rv.canon for rv in func.regvars}

        #Check if each regvar exists and add it to the dict
        regs = ['eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'esp', 'ebp']
        for r in regs:
            rv = idaapi.find_regvar(func, ea, r)
            if not rv: continue
            regvars[rv.user] = rv.canon

        return regvars

    def _fixup(self, parts, regvars):
        """ Fixup an instruction """
        nparts = []
        for i in parts:
            #Fixup regvars
            if i in regvars: nparts.append(regvars[i])
            #Fixup .got.plt entries (IDA turns '.' into '_')
            elif i and i[0] == '_':
                nparts.append(i.replace('_', '.', 1))
            #Default case
            else: nparts.append(i)

        return ''.join(nparts)

    def assemble(self, ea, asm, save_state=True, opt_fix=True, opt_nop=True):
        """ Assemble into memory """
        #Fixup the assemble
        if opt_fix:
            regvars = self._getregvars(ea)
            parts_arr = [self.PART_RE.split(i) for i in asm]
            asm = []
            for parts in parts_arr:
                asm.append(self._fixup(parts, regvars))

        #Assemble to a string
        success, data = idautils.Assemble(ea, asm)
        if not success:
            return success, data
        blob = ''.join(data)

        if len(blob) > instr_size(ea):
            if idaapi.askyn_c(0, "The assembled instruction is bigger than the current instruction. This will clobber following instructions. Continue?") != 1:
                return


        #Pad the blob with nops
        if opt_nop:
            nsuccess, nop_instr = idautils.Assemble(ea, 'nop')
            if not nsuccess:
                return nsuccess, nop_instr

            i = ea
            while i < ea + len(blob):
                i += instr_size(i)
            #Only pad if we trashed the next instruction
            sz_diff = (i - (ea + len(blob))) / len(nop_instr)
            blob += nop_instr * sz_diff

        #Write out the data
        old = read_data(ea, len(blob))
        if save_state:
            self._pushundo(
                [(ea, old)]
            )
            self.redo_buffer = []
        write_data(ea, blob)
        return success, old

    def nopout(self, ea, sz):
        """ NOP out a section of memory """
        nsuccess, nop_instr = idautils.Assemble(ea, 'nop')
        if not nsuccess:
            return nsuccess, nop_instr
        return self.assemble(ea, ['nop'] * (sz / len(nop_instr)))

    def nopxrefs(self, ea):
        """ Nop out all xrefs to a function """
        nsuccess, nop_instr = idautils.Assemble(ea, 'nop')
        if not nsuccess:
            return nsuccess, nop_instr

        xrefs = idautils.XrefsTo(ea)
        buf = []
        for i in xrefs:
            success, old = self.assemble(i.frm, ['nop'], False)
            if not success: continue

            buf.append((ea, old))
        self._pushundo(buf)
        self.redo_buffer = []

    def togglejump(self, ea):
        """ Toggle jump condition """
        inst = idautils.DecodeInstruction(ea)
        mnem = inst.get_canon_mnem()
        if mnem not in self.JUMPS: return False
        return self.assemble(ea, [idc.GetDisasm(ea).replace(mnem, self.JUMPS[mnem])])

    def uncondjump(self, ea):
        """ Make a jump unconditional """
        inst = idautils.DecodeInstruction(ea)
        mnem = inst.get_canon_mnem()
        if mnem not in self.JUMPS: return False
        return self.assemble(ea, [idc.GetDisasm(ea).replace(mnem, 'jmp')])

    def undo(self, n=1):
        """ Undo modifications """
        return self._statedo(n, self._popundo, self._pushredo);

    def redo(self, n=1):
        """ Redo modifications """
        return self._statedo(n, self._popredo, self._pushundo);

    def clear(self):
        """ Clear our state """
        self.redo_buffer = []
        self.undo_buffer = []

#print DecodeInstruction

########NEW FILE########
__FILENAME__ = FtlHooks
"""
FtlHooks.py

Hooks to process various events.

"""

import idaapi

class FtlHooks(idaapi.UI_Hooks):
    def __init__(self):
        super(FtlHooks, self).__init__()
        self.hooks = {}
        self.cmd = None

    def preprocess(self, name):
        self.cmd = name
        return 0

    def postprocess(self):
        if self.cmd in self.hooks:
            self.hooks[self.cmd]()
        return 0

    def register(self, name, func):
        self.hooks[name] = func

########NEW FILE########
__FILENAME__ = main
"""
main.py

IDAPython script to patch binaries. 

IDAPython: https://code.google.com/p/idapython/
Helfpul if you want to run scripts on startup: https://code.google.com/p/idapython/source/browse/trunk/examples/idapythonrc.py

Alt F7 to load scripts

File > Produce file > Create DIF file
Edit > Patch program > Apply patches to input file

Keybindings:
    Shift-N: Convert instruction to nops
    Shift-X: Nop all xrefs to this function
    Shift-J: Invert conditional jump
    Shift-U: Make jump unconditional
    Shift-P: Patch instruction
    Shift-Z: Undo modification (Won't always work. Should still be careful editing.)
    Shift-Y: Redo modification (Won't always work. Should still be careful editing.)

"""

import os
import idaapi
import idc
import re

import Fentanyl
import AssembleForm
import FtlHooks
import CodeCaveFinder
import Util
import Neuter


try:
    from PySide import QtGui
    from PySide import QtCore
except ImportError:
    print "PySide unavailable, no GUI"
    QtCore = None
    QtGui = None


""" Main """
ftl_path = os.path.dirname(__file__)

ftl = Fentanyl.Fentanyl()
asf = AssembleForm.AssembleForm()
ftlh = FtlHooks.FtlHooks()
ftln = Neuter.Neuter(ftl)
ftlh.hook()

#XXX: Store the parents of the QWidgets. Otherwise, some get GCed.
hack = []

#Interfaces to the methods in ftl
def nopout():
    start, end = Util.get_pos()
    ftl.nopout(start, end - start)

import traceback
def assemble():
    try: assemble_()
    except e:
        print traceback.format_exc()

def assemble_():
    success = False
    while not success:
        v = asf.process()
        if not v or not v['inp'].strip(): return

        start, end = Util.get_pos()
        lines = [i.strip() for i in v['inp'].replace(';', '\n').strip().split('\n')]
        success, data = ftl.assemble(start, lines, v['opt_chk']['fixup'], v['opt_chk']['nopout'])

        if not success:
            print data

def togglejump():
    start, end = Util.get_pos()
    ftl.togglejump(start)

def uncondjump():
    start, end = Util.get_pos()
    ftl.uncondjump(start)

def nopxrefs():
    start, end = Util.get_pos()
    func = idaapi.get_func(start)
    if func:
        ftl.nopxrefs(func.startEA)

def undo():
    if ftl.undo() is None:
        print "Nothing to undo"

def redo():
    if ftl.redo() is None:
        print "Nothing to redo"

def savefile():
    output_file = AskFile(1, "*", "Output File")
    if not output_file:
        return
    Util.save_file(output_file)

#Interface to spelunky
def openspelunky():
    window = CodeCaveFinder.CodeCaveWindow()
    window.Show("Spelunky")

def neuter():
    ftl.neuter()

#Helper functions
def bind_ctx_menus():
    #Find all the menus we need to modify
    menus = []
    for wid in qta.allWidgets():
        if not isinstance(wid, QtGui.QMenu):
            continue

        parent = wid.parent()
        if  parent.__class__ != QtGui.QWidget:
            continue

        #Find Hex/IDA Views
        if  'Hex View' in parent.windowTitle() or \
            len(parent.windowTitle()) == 1 \
        :
            hack.append(parent)
            menus.append(wid)

    #Filter out menus with actions
    menus = [i for i in menus if not i.actions()]

    print 'Bound entries to %s' % menus

    #Insert each entry into the context menu
    for i in range(len(menus)):
        menu = menus[i]
        menu.addSeparator()

        for qact in qdata:
            menu.addAction(qact)


#Hotkey definitions
hotkeys = [
    ('Replace with nops', True , ['Alt', 'N'], 'nopout.png', nopout),
    ('Nops all Xrefs'   , True , ['Alt', 'X'], 'nopxrefs.png', nopxrefs),
    ('Assemble'         , True , ['Alt', 'P'], 'assemble.png', assemble),
    ('Toggle jump'      , True , ['Alt', 'J'], 'togglejump.png', togglejump),
    ('Force jump'       , True , ['Ctrl', 'Alt', 'F'], 'uncondjump.png', uncondjump),
    ('Undo Patch'       , False, ['Alt', 'Z'], None, undo),
    ('Redo Patch'       , False, ['Alt', 'Y'], None, redo),
    ('Save File'        , False, ['Alt', 'S'], None, savefile),
    ('Find Code Caves'  , False, ['Alt', 'C'], None, openspelunky),
    ('Neuter Binary'    , False, ['Ctrl', 'Alt', 'N'], None, neuter)
]


#Register hotkeys
for name, in_menu, keys, icon, func in hotkeys:
    idaapi.add_hotkey('-'.join(keys), func)


#Register menu items
if QtCore:
    qta = QtCore.QCoreApplication.instance()

    qdata = []
    for name, in_menu, keys, icon, func in (i for i in hotkeys if i[1]):
        qact = QtGui.QAction(QtGui.QIcon(os.path.join(ftl_path, 'icons', icon)), name, qta)
        qact.triggered.connect(func)

        qks = QtGui.QKeySequence('+'.join(keys))
        qact.setShortcut(qks)
        qdata.append(qact)

    bind_ctx_menus()


#Rebind on new db
ftlh.register('LoadFile', bind_ctx_menus)
#Rebind on new IDA View
ftlh.register('WindowOpen', bind_ctx_menus)
ftlh.register('GraphNewProximityView', bind_ctx_menus)
#Rebind on new Hex View
ftlh.register('ToggleDump', bind_ctx_menus)
#Reset on IDB close
ftlh.register('CloseBase', ftl.clear)

########NEW FILE########
__FILENAME__ = Neuter
import idaapi
import idautils
import idc
import re
from Util import *

class Neuter(object):
    def __init__(self, ftl):
        self.ftl = ftl
        self.functions = {}
        for x in idautils.Functions():
            self.functions[idc.GetFunctionName(x)] = x

    def nop_xrefs(self, *funcs):
        """Nop out any xref to a function. """
        for x in funcs:
            self.ftl.nopxrefs(self.functions[x])

    def replace_with(self, func, replace):
        """Replace an instruction"""
        if type(func) == int or type(func) == long:
            return self.ftl.assemble(func, replace)
        xrefs = idautils.XrefsTo(self.functions[func])
        for x in xrefs:
            return self.ftl.assemble(x.frm, replace)

    def find_funcs(self, *funcs):
        """Find functions that call all funcs"""
        results = []
        for func in funcs:
            xrefs = idautils.XrefsTo(self.functions[func])
            for xref in xrefs:
                results.append(idaapi.get_func(xref.frm).startEA)
        results = list(set(results))
        return results

    def in_func(self, func, addr):
        """Check if an instruction is within a function"""
        func = idaapi.get_func(func)
        if addr >= func.startEA and addr <= func.endEA:
            return True
        return False

    def auto(self):
        """Automatically patch out annoying functions"""
        self.nop_xrefs('.alarm')
        self.replace_with('.fork', ['xor eax,eax', 'nop', 'nop', 'nop'])
        
        setuids = self.find_funcs('.setuid') #get funcs containing calls to setuid

        for setuid in setuids:
            getpwnams = [self.replace_with(x.frm, ['mov eax, 1']) for x in idautils.XrefsTo(self.functions['.getpwnam']) if self.in_func(setuid, x.frm)]
            setgroups = [self.replace_with(x.frm, ['xor eax,eax', 'nop', 'nop', 'nop']) for x in idautils.XrefsTo(self.functions['.setgroups']) if self.in_func(setuid, x.frm)]
            setgids = [self.replace_with(x.frm, ['xor eax,eax', 'nop', 'nop', 'nop']) for x in idautils.XrefsTo(self.functions['.setgid']) if self.in_func(setuid, x.frm)]
            setuids = [self.replace_with(x.frm, ['xor eax,eax', 'nop', 'nop', 'nop']) for x in idautils.XrefsTo(self.functions['.setuid']) if self.in_func(setuid, x.frm)]
            chdirs = [self.replace_with(x.frm, ['xor eax,eax', 'nop', 'nop', 'nop']) for x in idautils.XrefsTo(self.functions['.chdir']) if self.in_func(setuid, x.frm)]
########NEW FILE########
__FILENAME__ = Util
"""
Util.py

Various helper functions

"""

import re
import idc
import idautils
import idaapi

def instr_size(ea):
    """ Get the size of the instr at ea or 1 """
    instr = idautils.DecodeInstruction(ea)
    #If invalid, return 1 to consume this byte
    #XXX: Fixed-width instr sets should add instr size
    return instr.size if instr else 1

def get_pos():
    """ Get the selected area """
    start, end = idc.SelStart(), idc.SelEnd()
    if start == idc.BADADDR:
        start = idc.ScreenEA()
        end = idc.ScreenEA() + instr_size(start)
    return start, end

def read_data(ea, sz):
    """ Read bytes from idb """
    return idaapi.get_many_bytes(ea, sz)

def write_data(ea, blob, reanalyze=True):
    """ Write bytes to idb """
    if reanalyze: idc.MakeUnknown(ea, len(blob), 0)
    idaapi.patch_many_bytes(ea, blob)
    if reanalyze: idc.MakeCode(ea)

def save_file(output_file):
    """ Save the patched file """
    DIFF_RE = re.compile(r'([A-F0-9]+): ([A-F0-9]+) ([A-F0-9]+)')

    idc.GenerateFile(idaapi.OFILE_DIF, output_file, 0, idc.MaxEA(), 0)
    diff_file = open(output_file, "rb").read()
    orig_file = open(idc.GetInputFilePath(), "rb").read()
    print "OK"
    diff_file = diff_file.split("\n")
    total = 0
    success = 0
    for line in diff_file:
        match = DIFF_RE.match(line)
        if match:
            groups = match.groups()
            total += 1
            offset = int(groups[0], 16)
            orig_byte = groups[1].decode('hex')
            new_byte = groups[2].decode('hex')
            if orig_file[offset] == orig_byte:
                orig_file = orig_file[:offset] + new_byte + orig_file[offset + 1:]
                success += 1
            else:
                print "Error matching %02x at offset %x..." % (groups[1], offset)

    new_file = open(output_file, 'wb')
    new_file.write(orig_file)
    new_file.close()
    print "%i/%i patches applied" % (success, total)

########NEW FILE########
