__FILENAME__ = codatify
# IDA plugin that converts all data in data segments to defined data types, and all data in code segments to code.
#
# Use by going to Options->Define data and code, or use the Alt+3 hotkey.
#
# Craig Heffner
# Tactical Network Solutions

import idc
import idaapi
import idautils

class Codatify(object):

    CODE = 2
    DATA = 3
    SEARCH_DEPTH = 25

    def __init__(self):
        pass

    # Get the start of the specified segment type (2 == code, 3 == data)
    def get_start_ea(self, attr):
        ea = idc.BADADDR
        seg = idc.FirstSeg()

        while seg != idc.BADADDR:
            if idc.GetSegmentAttr(seg, idc.SEGATTR_TYPE) == attr:
                ea = seg
                break
            else:
                seg = idc.NextSeg(seg)
    
        return ea

    # Creates ASCII strings
    def stringify(self):
        n = 0
        ea = self.get_start_ea(self.DATA)

        if ea == idc.BADADDR:
            ea = idc.FirstSeg()

        print ("Looking for possible strings starting at: %s:0x%X..." % (idc.SegName(ea), ea)),

        for s in idautils.Strings():
            if s.ea > ea:
                if not idc.isASCII(idc.GetFlags(s.ea)) and idc.MakeStr(s.ea, idc.BADADDR):
                    n += 1

        print "created %d new ASCII strings" % n

    # Converts remaining data into DWORDS.
    def datify(self):
        ea = self.get_start_ea(self.DATA)
        if ea == idc.BADADDR:
            ea = idc.FirstSeg()
        
        print "Converting remaining data to DWORDs...",
    
        while ea != idc.BADADDR:
            flags = idc.GetFlags(ea)
                    
            if idc.isUnknown(flags) or idc.isByte(flags):
                idc.MakeDword(ea)
                idc.OpOff(ea, 0, 0)

            ea = idc.NextAddr(ea)

        print "done."

    def pointify(self):
        counter = 0

        print "Renaming pointers...",

        for (name_ea, name) in idautils.Names():
            for xref in idautils.XrefsTo(name_ea):
                xref_name = idc.Name(xref.frm)
                if xref_name and xref_name.startswith("off_"):
                    i = 0
                    new_name = name + "_ptr"
                    while idc.LocByName(new_name) != idc.BADADDR:
                        new_name = name + "_ptr%d" % i
                        i += 1

                    if idc.MakeName(xref.frm, new_name):
                        counter += 1
                    #else:
                    #    print "Failed to create name '%s'!" % new_name

        print "renamed %d pointers" % counter

    # Creates functions and code blocks
    def codeify(self, ea=idc.BADADDR):
        func_count = 0
        code_count = 0

        if ea == idc.BADADDR:
            ea = self.get_start_ea(self.CODE)
            if ea == idc.BADADDR:
                ea = idc.FirstSeg()

        print "\nLooking for undefined code starting at: %s:0x%X" % (idc.SegName(ea), ea)

        if self.get_start_ea(self.DATA) == idc.BADADDR:
            print "WARNING: No data segments defined! I don't know where the code segment ends and the data segment begins."
    

        while ea != idc.BADADDR:
            try:
                if idc.GetSegmentAttr(ea, idc.SEGATTR_TYPE) == self.CODE:
                    if idc.GetFunctionName(ea) != '':
                        ea = idc.FindFuncEnd(ea)
                        continue
                    else:
                        if idc.MakeFunction(ea):
                            func_count += 1
                        elif idc.MakeCode(ea):
                            code_count += 1
            except:
                pass
            
            ea = idc.NextAddr(ea)
    
        print "Created %d new functions and %d new code blocks\n" % (func_count, code_count)



class codatify_t(idaapi.plugin_t):
    flags = 0
    comment = ""
    help = ""
    wanted_name = "Define all data and code"
    wanted_hotkey = ""

    def init(self):
        self.menu_context = idaapi.add_menu_item("Options/", "Fixup code", "Alt-3", 0, self.fix_code, (None,))
        self.menu_context = idaapi.add_menu_item("Options/", "Fixup data", "Alt-4", 0, self.fix_data, (None,))
        return idaapi.PLUGIN_KEEP

    def term(self):
        idaapi.del_menu_item(self.menu_context)
        return None

    def run(self, arg):
        pass

    def fix_code(self, arg):
        cd = Codatify()
        cd.codeify()

    def fix_data(self, arg):
        cd = Codatify()
        cd.stringify()
        cd.datify()
        cd.pointify()

def PLUGIN_ENTRY():
    return codatify_t()


########NEW FILE########
__FILENAME__ = fuzz
import idc

class _FuzzHelper(object):
    
    def __init__(self, idasim):
        self.idasim = idasim

    def sanitize(self, data):
        try:
            return data.replace('"', '\\"')
        except:
            return data

    def display(self, message):
        print "%-25s %s" % (idc.GetFuncOffset(self.idasim.cpu.ReturnAddress()), message)
    
class Fuzz(object):

    def __init__(self, idasim):
        self.helper = _FuzzHelper(idasim)
        self.idasim = idasim

    def strcpy(self, dst, src=''):
        self.helper.display('strcpy(0x%X, "%s")' % (dst, self.helper.sanitize(src)))
        return None

    def strcat(self, dst='', src=''):
        self.helper.display('strcat("%s", "%s")' % (self.helper.sanitize(dst), self.helper.sanitize(src)))
        return None

    def sprintf(self, dst, fmt=''):
        string = self.idasim.vsprintf(fmt, 2)
        self.helper.display('sprintf(0x%X, "%s")' % (dst, self.helper.sanitize(string)))
        return None

    def system(self, cmd=''):
        self.helper.display('system("%s")' % self.helper.sanitize(cmd))
        return None

    def popen(self, cmd='', attrib=''):
        self.helper.display('popen("%s", "%s")' % (self.helper.sanitize(cmd), self.helper.sanitize(attrib)))
        return None

    def strncpy(self, dst, src='', n=0):
        if len(src) >= n:
            self.helper.display('strncpy(0x%X, "%s", %d)' % (dst, self.helper.sanitize(src), n))
        return None

    def strncat(self, dst='', src='', n=0):
        self.helper.display('strncat("%s", "%s", %d)' % (self.helper.sanitize(dst), self.helper.sanitize(src), n))

    def snprintf(self, dst, size, fmt=''):
        string = self.idasim.vsprintf(fmt, 3)
        if len(string) >= size:
            self.helper.display('snprintf(0x%X, %d, "%s")' % (dst, size, self.helper.sanitize(string)))
        return None

    def printf(self, fmt=''):
        if '%' not in fmt:
            self.helper.display('printf("%s")' % self.helper.sanitize(fmt))
        return None

    def fprintf(self, fd, fmt=''):
        if '%' not in fmt:
            self.helper.display('fprintf(%d, "%s")' % (fd, self.helper.sanitize(fmt)))
        return None


########NEW FILE########
__FILENAME__ = libc
import os
import time
import idc
import idaapi
import idautils

class LibC(object):
    '''
    Class containing simulators for various common libc functions.
    '''

    __IDASIM_DEFAULT_HANDLER_CLASS__ = True

    def __init__(self, idasim=None):
        '''
        Class constructor.
        '''
        self.idasim = idasim

    def sleep(self, t):
        time.sleep(t)
        return 0

    def atoi(self, string=''):
        return int(string)

    def atol(self, string=''):
        return self.atoi(string)

    def atoll(self, string=''):
        return self.atoi(string)

    def atoq(self, string=''):
        return self.atoi(string)

    def strlen(self, string=''):
        return len(string)

    def getenv(self, envar=''):
        return os.getenv(envar) + "\x00"

    def malloc(self, n):
        return "\x00" * n

    def memset(self, buf, c, n):
        idc.DbgWrite(buf, (chr(c) * n))
        return buf

    def memcpy(self, dst, src, n):
        idc.DbgWrite(dst, idc.GetManyBytes(src, n, use_dbg=False))
        return dst

    def strcpy(self, dst, src=''):
        '''
        Monitors, reports and simulates the strcpy function.
        '''
        print 'strcpy(0x%X, "%s")' % (dst, src)
        idc.DbgWrite(dst, src + "\x00")
        return dst

    def strcat(self, dst, src=''):
        '''
        Monitors, reports and simulates the strcat function.
        '''
        print 'strcat(0x%X, "%s")' % (dst, src)
        addr = dst + len(idc.GetString(dst))
        idc.DbgWrite(addr, src + "\x00")
        return dst

    def strncpy(self, dst, src='', n=0):
        idc.DbgWrite(dst, src + "\x00", length=n)
        return dst

    def strncat(self, dst, src='', n=0):
        addr = dst + len(idc.GetString(dst))
        idc.DbgWrite(addr, src + "\x00", length=n)
        return dst

    def strdup(self, string=''):
        return string + "\x00"

    def strcmp(self, s1='', s2=''):
        if s1 == s2:
            return 0
        else:
            return 1

    def strncmp(self, s1='', s2='', n=0):
        if s1[:n] == s2[:n]:
            return 0
        else:
            return 1

    def memcmp(self, dp1, dp2, n):
        d1 = idc.DbgRead(dp1, n)
        d2 = idc.DbgRead(dp2, n)
    
        if d1 == d2:
            return 0
        else:
            return 1

    def memchr(self, dp, c, n):
        c = chr(c)
        data = idc.DbgRead(dp, n)
        
        offset = data.find(c)

        if offset == -1:
            return 0
        else:
            return dp + offset

    def system(self, command=''):
        '''
        Displays the system() command, does not execute.
        '''
        print '0x%X : system("%s");' % (self.idasim.cpu.ReturnAddress(), command)
        return 0

    def strstr(self, hayptr, needle=''):
        haystack = idc.GetString(hayptr)
        offset = haystack.find(needle)
        
        if offset == -1:
            return 0
        else:
            return hayptr + offset

    def strchr(self, hayptr, needle):
        haystack = idc.GetString(hayptr)
        needle = chr(needle)
        offset = haystack.find(needle)
        
        if offset == -1:
            return 0
        else:
            return hayptr + offset

    def daemon(self):
        '''
        Fakes a daemon(), returns 0.
        '''
        return 0

    def fork(self):
        '''
        Fakes a fork(), always returns 0.
        '''
        return 0
    
    def free(self, address):
        '''
        Frees heap data not allocated by IDASimulator.
        '''
        if self.idasim.mmu.allocated_addresses.has_key(address):
            return 0
        else:
            return None

    def strtol(self, string='', base=0):
        return int(string, base)

    def strtoul(self, string='', base=0):
        return self.strtol(string, base)
    
    def strtod(self, string='', base=0):
        return self.strtod(string, base)

    def strcasecmp(self, s1='', s2=''):
        if s1.lower() == s2.lower():
            return 0
        else:
            return 1

    def strncasecmp(self, s1='', s2='', n=0):
        if s1[:n].lower() == s2[:n].lower():
            return 0
        else:
            return 1
    
    def exit(self, code):
        '''
        Prints exit code and stops debugger.
        '''
        print "Exit code:", code
        idc.StopDebugger()

    def setgroups(self):
        '''
        Fakes setgroups(), returns 0.
        '''
        return 0


########NEW FILE########
__FILENAME__ = libcsman
import idc

class LibCSMAN(object):

    _CONFIG = "/tmp/nvram.cfg"

    __IDASIM_DEFAULT_HANDLER_CLASS__ = True

    def __init__(self, idasim):
        self.idasim = idasim

        self.config = {}

        try:
            for line in open(self._CONFIG_FILE).readlines():
                if '=' in line:
                    kv = line.strip().split('=')
                    name = kv[0]
                    key = int(kv[1], 16)
                    if len(kv) == 3:
                        value = kv[2].decode('string_escape')
                    else:
                        value = "\x00"

                    if not self.config.has_key(key):
                        self.config[key] = {
                                'name'    : name,
                                'value'    : value
                        }
        except:
            pass

    def open_csman(self):
        return 128

    def close_csman(self):
        return 0

    def write_csman(self, fd, key, buf, size, default):
        return 0

    def read_csman(self, fd, key, value, size, default):
        if self.config.has_key(key):
            print "read_csman(%s)" % self.config[key]['name']
            idc.DbgWrite(value, self.config[key]['value'])
        else:
            print "UNKNOWN CSID: 0x%.8X called from 0x%.8X" % (key, self.idasim.cpu.ReturnAddress())

        return 0


########NEW FILE########
__FILENAME__ = libnvram
import idc

class LibNVRAM(object):

    _CONFIG_FILE = "/tmp/nvram.cfg"

    __IDASIM_DEFAULT_HANDLER_CLASS__ = True

    def __init__(self, idasim):
        self.idasim = idasim

        self.config = {}

        try:
            for line in open(self._CONFIG_FILE).readlines():
                if '=' in line:
                    kv = line.strip().split('=')
                    if not self.config.has_key(kv[0]):
                        self.config[kv[0]] = kv[1]
        except:
            pass

    def nvram_init(self):
        return 0

    def nvram_get(self, zero, key=''):
        return self.nvram_bufget(zero, key)

    def nvram_bufget(self, zero, key=''):
        try:
            value = self.config[key]
        except:
            value = ''

        print "nvram_get: {'%s' : '%s'}" % (key, value)
        return value + "\x00"

    def nvram_bufset(self, zero, key='', value=''):
        self.config[key] = value
        print "nvram_set: {'%s' : '%s'}" % (key, value)
        return 0

    def nvram_get_ex(self, key='', dst=0, size=0):
        idc.DbgWrite(dst, self.nvram_bufget(0, key)[:size])
        return 0

    def nvram_match(self, key='', match=''):
        if self.nvram_bufget(0, key)[:-1] == match:
            return 1
        return 0

    def nvram_invmatch(self, key='', match=''):
        if self.nvram_match(key, match):
            return 0
        return 1


########NEW FILE########
__FILENAME__ = pthread

class PThread(object):

    __IDASIM_DEFAULT_HANDLER_CLASS__ = True

    def __init__(self, idasim):
        self.idasim = idasim

    def pthread_create(self, thread, attr, start_routine, arg):
        '''
        Calls the start_routine, does not create a thread.
        '''
        self.idasim.app.Call(start_routine, arguments=[arg], block_until_return=False)
        return None

########NEW FILE########
__FILENAME__ = stdio
import os
import sys
import idc

class Stdio(object):
    '''
    Class containing simulators for common stdio functions.
    '''

    __IDASIM_DEFAULT_HANDLER_CLASS__ = True

    def __init__(self, sim=None):
        '''
        Class constructor.
        '''
        if sim is not None:
            self.mmu = sim.mmu
            self.cpu = sim.cpu
            self.sim = sim

        self.file_descriptors = {
                0 : sys.stdin,
                1 : sys.stdout,
                2 : sys.stderr,
        }

    def _next_fd(self):
        i = 0
        while self.file_descriptors.has_key(i):
            i += 1
        return i

    def _add_fd(self, fp):
        fd = self._next_fd()
        self.file_descriptors[fd] = fp
        return fd

    def _close(self, fd):
        if self.file_descriptors.has_key(fd):
            self.file_descriptors[fd].close()
            del self.file_descriptors[fd]

    def _open(self, fname, mode="rwb"):
        try:
            fp = open(fname, mode)
            fd = self._add_fd(fp)
        except:
            fd = -1

        return fd

    def _read(self, fd, size):
        data = ""
        if self.file_descriptors.has_key(fd):
            data = self.file_descriptors[fd].read(size)
        return data

    def _write(self, fd, data):
        if self.file_descriptors.has_key(fd):
            self.file_descriptors[fd].write(data)
        return len(data)

    def puts(self, string=''):
        print string
        return 0

    def printf(self, fmt=''):
        print self.sim.vsprintf(fmt, 1),
        return 0

    def syslog(self, i, fmt=''):
        print self.sim.vsprintf(fmt, 2)
        return 0

    def fprintf(self, fd, fmt=''):
        formatted_string = self.sim.vsprintf(fmt, 2)

        if self.file_descriptors.has_key(fd) and fd != 0:
            self._write(fd, formatted_string)
        else:
            print formatted_string,
        return 0

    def sprintf(self, dst, fmt=''):
        '''
        Monitors, reports and simulates sprintf.
        '''
        data = self.sim.vsprintf(ftm, 2)
        print 'sprintf(0x%X, "%s")' % (dst, data)
        idc.DbgWrite(dst, data + "\x00")
        return len(data)

    def snprintf(self, dst, n, fmt=''):
        idc.DbgWrite(dst, self.sim.vsprintf(fmt, 3)[:n] + "\x00")
        return dst

    def popen(self, command='', mode=''):
        '''
        Displays the popen() command, does not execute.
        '''
        print '0x%X : popen("%s", "%s");' % (self.cpu.ReturnAddress(), command, mode)
        #fp = os.popen(command, mode)
        #return self._add_fd(fp)
        return 0

    def pclose(self, fd):
        self._close(fd)
        return 0

    def fopen(self, fname='', modes=''):
        fd = self._open(fname, modes)
        if fd > -1:
            return fd
        else:
            return 0
    
    def fclose(self, fd):
        self._close(fd)
        return 0

    def fread(self, ptr, size, nmemb, fd):
        data = self._read(fd, (size * nmemb))
        idc.DbgWrite(ptr, data)
        return len(data)

    def fwrite(self, ptr, size, nmemb, fd):
        data = idc.DbgRead(ptr, (size * nmemb))
        self._write(fd, data)
        return len(data)

    def fflush(self, fd):
        if self.file_descriptors.has_key(fd):
            self.file_descriptors[fd].flush()
        return 0

    def fgets(self, dst, size, fd):
        if self.file_descriptors.has_key(fd):
            while not data.endswith('\n') and len(data) < (size-1):
                data += self._read(fd, 1)

            data += "\x00"
            idc.DbgWrite(dst, data, len(data))

        return dst

    def fseek(self, fd, offset, whence):
        if self.file_descriptors.has_key(fd):
            self.file_descriptors[fd].seek(offset, whence)
            return self.file_descriptors[fd].tell()
        return -1

    def rewind(self, fd):
        if self.file_descriptors.has_key(fd):
            self.file_descriptors[fd].seek(0, 0)
        return 0

    def ftell(self, fd):
        if self.file_descriptors.has_key(fd):
            return self.file_descriptors[fd].tell()
        return -1



########NEW FILE########
__FILENAME__ = idasimulator
import os
import pickle
import inspect
import idaapi
import idautils
import idc
import idasim

IDASIM = None

class IDASimConfiguration:
    '''
    Responsible for loading, saving and cleaning the idasimulator configuration file.
    Configuration data is a dictionary stored in pickle format:

        cfg = {
            '/path/to/database.idb' : {
                        'handlers'   : [enabled handlers],
                        'startup'    : 'startup script',
                        'startname'  : named location to set breakpoint for setting startup values,
                        'membase'    : membase value
            }
        }
    '''
    CONFIG_FILE = 'idasimulator.cfg'

    def __init__(self, sim):
        '''
        Class constructor.

        @sim - idasimulator_t class instance.

        Returns None.
        '''
        self.cfg = None
        self.sim = sim
        self.idb = idc.GetIdbPath()
        self.confile = os.path.join(idaapi.get_user_idadir(), self.CONFIG_FILE)

    def _load_config_file(self):
        '''
        Loads the entire configuration file, cleaning out stale config entries in the process.

        Returns the entire configuration dictionary.
        '''
        cfg = {}
        stale = []

        try:
            cfg = pickle.load(open(self.confile, "rb"))

            # The IDB path is used as the configuration key. If a IDB no longer exists, its config data is useless.
            # Mark any IDB's that no longer exist.
            for (idb, config) in cfg.iteritems():
                if not os.path.exists(idb):
                    stale.append(idb)

            # Delete any stale config entries and save the data back to the config file.
            if len(stale) > 0:
                for idb in stale:
                    del cfg[idb]
                self._save_config_file(cfg)
        except Exception, e:
            pass

        return cfg

    def _save_config_file(self, fdata):
        '''
        Saves data to the config file, in pickle format.
        
        @fdata - Configuration file dictionary.

        Returns None.
        '''
        try:
            pickle.dump(fdata, open(self.confile, "wb"))
        except Exception, e:
            print "Failed to save %s: %s" % (self.confile, str(e))

    def _load_config_data(self, idb_path):
        '''
        Loads configuration data for this IDB from the config file.

        Returns this IDB's configuration data.
        '''
        data = {}

        if os.path.exists(self.confile):
            cfgdata = self._load_config_file()
            if cfgdata.has_key(idb_path):
                data = cfgdata[idb_path]
        return data

    def _populate_config_data(self, data):
        '''
        Populates the current running configuration from data.
        
        @data - Configuration dictionary.

        Returns None.
        '''
        for name in data['handlers']:
            self.sim.EnableHandler(name)

        self.sim.SetInitValues(data['startname'], data['startup'])
        self.sim.idasim.mmu.base(data['membase'])

    def _save_config_data(self, idb_path, fdata):
        '''
        Saves the current running configuration to disk.

        @idb_path - Path to the IDB file.
        @fdata    - Configuration file dictionary.

        Returns None.
        '''
        fdata[idb_path] = {}
        fdata[idb_path]['handlers'] = self.sim.EnabledHandlers()
        fdata[idb_path]['membase'] = self.sim.idasim.mmu.base()

        (start_name, start_script) = self.sim.GetInitValues()
        fdata[idb_path]['startname'] = start_name
        fdata[idb_path]['startup'] = start_script

        self._save_config_file(fdata)

    def Load(self):
        '''
        Loads the saved configuration data into the running configuration.

        Returns None.
        '''
        data = self._load_config_data(self.idb)
        if data:
            self._populate_config_data(data)

    def Save(self):
        '''
        Saves the running configuration to disk.
    
        Returns None.
        '''
        fdata = self._load_config_file()
        self._save_config_data(self.idb, fdata)


class IDASimFunctionChooser(idaapi.Choose2):
    '''
    Primary IDASimulator UI.
    '''

    def __init__(self, sim):
        idaapi.Choose2.__init__(self, "IDA Simulator", [     
                                    ["Handler", 20 | Choose2.CHCOL_PLAIN], 
                                    ["Name", 15 | Choose2.CHCOL_PLAIN], 
                                    ["Description", 30 | Choose2.CHCOL_PLAIN], 
                                    ["Status", 10 | Choose2.CHCOL_PLAIN], 
                                ])
        self.icon = 41
        self.sim = sim
        self.save_cmd = None
        self.quit_cmd = None
        self.goto_cmd = None
        self.reset_cmd = None
        self.mbase_cmd = None
        self.toggle_cmd = None
        self.config_cmd = None
        self.enable_all_cmd = None
        self.disable_all_cmd = None

        self.PopulateItems()

    def PopulateItems(self):
        '''
        Populates the chooser window with named locations that have registered handlers.
        '''
        self.items = []

        for (name, info) in self.sim.functions.iteritems():
            addr = idc.LocByName(info['function'])

            if addr != idc.BADADDR:
                if self.sim.IsSimulated(name):
                    status = "Enabled"
                else:
                    status = "Disabled"
                
                self.items.append([name, info['function'], self.sim.GetHandlerDesc(name), status, addr])

    def OnSelectLine(self, n):
        '''
        Invoked when the user double-clicks on a selection in the chooser.
        '''
        self.sim.ToggleHandler(self.items[n][0])
        # Not sure why, but the displayed items aren't refreshed if PopulateItems isn't called here.
        # Interestingly, this is NOT required when OnSelectLine is invoked via the OnCommand method.
        self.PopulateItems()
        self.Refresh()

    def OnGetLine(self, n):
        return self.items[n]

    def OnGetSize(self):
        return len(self.items)

    def OnDeleteLine(self, n):
        '''
        Invoked when a user deletes a selection from the chooser.
        '''
        return n

    def OnRefresh(self, n):
        '''
        Refreshes the display.
        '''
        self.sim.Refresh()
        self.PopulateItems()
        return n

    def OnCommand(self, n, cmd_id):
        '''
        Handles custom right-click commands.
        '''
        if self.sim.idasim is not None:
            if cmd_id == self.reset_cmd:
                self.reset()
            elif cmd_id == self.goto_cmd:
                idc.Jump(self.items[n][-1])
            elif cmd_id == self.toggle_cmd:
                self.OnSelectLine(n)
            elif cmd_id == self.enable_all_cmd:
                self.enable_all()
            elif cmd_id == self.disable_all_cmd:
                self.disable_all()
            elif cmd_id == self.mbase_cmd:
                self.set_mbase()
            elif cmd_id == self.config_cmd:
                self.configure_form()
            elif cmd_id == self.save_cmd:
                self.sim.config.Save()
            elif cmd_id == self.quit_cmd:
                self.quit_idasim()
        return 1

    def OnClose(self):
        '''
        Save the current settings when the chooser window is closed.
        '''
        if self.sim.idasim is not None:
            self.sim.config.Save()
        return None

    def quit_idasim(self):
        '''
        Quits IDASimulator, disabling everything.
        '''
        self.sim.config.Save()
        self.sim.Cleanup(closegui=False)

    def set_mbase(self):
        '''
        Sets the memory base address for the IDASimMMU instance.
        '''
        mbase = AskAddr(self.sim.idasim.mmu.base(), "Configure base memory allocation address")
        if mbase != idc.BADADDR:
            if mbase == 0:
                mbase = idc.BADADDR
            self.sim.idasim.mmu.base(mbase)

    def configure_form(self):
        '''
        Displays the configuration form for setting up startup register values.
        '''
        script_file = AskFile(0, '*.py', 'Select a script to run on process init/attach.')
        if script_file:
            self.sim.SetInitValues(None, open(script_file, 'rb').read())

    def enable_all(self):
        '''
        Enables all handlers.
        '''
        for i in range(0, len(self.items)):
            self.sim.EnableHandler(self.items[i][0])
        self.Refresh()

    def disable_all(self):
        '''
        Disable all handlers.
        '''
        for i in range(0, len(self.items)):
            self.sim.DisableHandler(self.items[i][0])
        self.Refresh()

    def reset(self):
        '''
        Resets all settings to the defaults.
        '''
        if idc.AskYN(0, "Are you sure you want to undo all changes and reset?") == 1:
            self.sim.Reset()
            self.Refresh()

    def show(self):
        '''
        Displays the chooser, initializes the custom right-click options.
        '''
        if self.Show(modal=False) < 0:
            return False
    
        self.toggle_cmd = self.AddCommand("Enable / disable selected handler")
        self.enable_all_cmd = self.AddCommand("Enable all handlers")
        self.disable_all_cmd = self.AddCommand("Disable all handlers")
        self.config_cmd = self.AddCommand("Load startup script")
        self.mbase_cmd = self.AddCommand("Set MMU base address")
        self.reset_cmd = self.AddCommand("Reset to defaults")
        self.goto_cmd = self.AddCommand("Jump to selected name")
        self.save_cmd = self.AddCommand("Save settings")
        self.quit_cmd = self.AddCommand("Quit")
        return True


class idasimulator_t(idaapi.plugin_t):
    '''
    Primary IDASimulator plugin class.
    '''

    flags = 0
    comment = "IDA Simulator Plugin"
    help = "Simulate excutable logic in Python"
    wanted_name = "IDA Simulator"
    wanted_hotkey = ""

    def init(self):
        '''
        Initialize some default values for class variables.
        '''
        self.gui = None
        self.idasim = None
        self.config = None
        self.functions = {}
        self.startup_script = ''
        self.startup_name = None
        self.stubs = True
        self.menu_context = idaapi.add_menu_item("Options/", "Simulate functions and code blocks...", "Alt-0", 0, self.run, (None,))
        return idaapi.PLUGIN_KEEP

    def term(self):
        '''
        Cleanup IDASimulator and breakpoints when terminated.
        '''
        self.Cleanup()
        idaapi.del_menu_item(self.menu_context)
        return None

    def run(self, arg):
        '''
        Initialize IDASimulator and chooser GUI, if not already initialized.
        '''
        global IDASIM

        if IDASIM is None:
            IDASIM = idasim.IDASim()
            print "%s enabled." % self.wanted_name
        
        self.idasim = IDASIM
        
        self.__parse_libraries()
    
        self.config = IDASimConfiguration(self)
        self.config.Load()
            
        self.gui = IDASimFunctionChooser(self)
        self.gui.show()

    def GetInitValues(self):
        '''
        Returns the named initialization location and the array of startup Python statements.
        '''
        return (self.startup_name, self.startup_script)

    def SetInitValues(self, name=None, script=''):
        '''
        Sets the named initialization location and the array of startup Python statements.

        @name  - Named location.
        @lines - Array of tuples (register name, Python statement).

        Returns the named initialization location and the array of startup Python statements.
        '''
        self.idasim.ExecuteOnStart(None, None, disable=True)

        if not name:
            disable = True
        else:
            disable = False
        
        self.startup_name = name
        self.startup_script = script
        self.idasim.ExecuteOnStart(self.startup_script, self.startup_name, disable=disable)
        
        return (self.startup_name, self.startup_script)

    def IsSimulated(self, name):
        '''
        Checks if a named location has an active IDASimulator handler.

        @name - Named location.

        Returns True if a handler is active, False if not.
        '''
        if self.functions.has_key(name):
            return self.functions[name]['enabled']
        else:
            return False

    def GetHandlerDesc(self, name):
        '''
        Get a handler description for a given named location.

        @name - Handler name.

        Returns the handler description, if it exists. Else, returns None.
        '''
        if name == self.startup_name:
            return 'Initialization handler.'
        else:
            return self.functions[name]['description']

    def ToggleHandler(self, name):
        '''
        Enables/disables the handler for the named location.

        @name - Named location.

        Returns None.
        '''
        if self.IsSimulated(name):
            self.DisableHandler(name)
        else:
            self.EnableHandler(name)

    def EnableHandler(self, name):
        '''
        Enables the handler for the named location.

        @name - Named location.

        Returns None.
        '''
        existing_handler = self.idasim.FunctionHandler.GetHandler(self.functions[name]['function'])
        if existing_handler:
            self.DisableHandler(self.__get_handler_name(existing_handler.im_class.__name__, existing_handler.__name__))

        self.idasim.FunctionHandler.RegisterHandler(self.functions[name]['function'], self.functions[name]['handler'], self.stubs)
        self.functions[name]['enabled'] = True
    
    def EnabledHandlers(self):
        '''
        Returns a list of all named locations that have an active handler.
        '''
        return [name for (name, info) in self.functions.iteritems() if info['enabled']]

    def DisableHandler(self, name):
        '''
        Disables the handler for the named location.

        @name - Named location.
        
        Returns None.
        '''
        self.idasim.FunctionHandler.UnregisterHandler(self.functions[name]['function'], self.stubs)
        self.functions[name]['enabled'] = False

    def Refresh(self):
        '''
        Refreshes the internal list of supported handlers.
        '''
        if self.idasim is not None:
            self.__parse_libraries()
        
            for name in self.EnabledHandlers():
                if name != self.startup_name:
                    self.idasim.FunctionHandler.RegisterHandler(self.functions[name]['function'], self.functions[name]['handler'], self.stubs)    
                    
    def Reset(self):
        '''
        Resets all IDASimulator settings to the defaults.
        '''
        self.SetInitValues(None, None)
        self.idasim.Cleanup()
        self.idasim.mmu.base(idc.BADADDR)
        self.__parse_libraries()

    def Cleanup(self, closegui=True):
        '''
        Cleans up all IDASimulator changes and disables the plugin.
        '''
        global IDASIM

        try:
            if closegui and self.gui is not None:
                self.gui.Close()
        except:
            pass

        try:
            if self.idasim is not None:
                self.idasim.Cleanup()
        except:
            pass

        IDASIM = None
        self.gui = None
        self.idasim = None
        self.functions = {}
        print "%s disabled." % self.wanted_name

    def __get_handler_name(self, class_name, method_name):
        '''
        Builds a handler key name from the class and method names.
        '''
        return class_name + '.' + method_name

    def __generate_handler_entry(self, instance, method, name=None):
        '''
        Creates a single handler dictionary entry for the provided class instance and method.
        '''
        if not name:
            name = method

        handler = getattr(instance, method)
        class_name = instance.__class__.__name__
        handler_name = self.__get_handler_name(class_name, method)

        entry = {}
        entry[handler_name] = {}

        entry[handler_name]['class'] = class_name
        entry[handler_name]['handler'] = handler
        entry[handler_name]['function'] = name
        entry[handler_name]['enabled'] = False

        existing_handler = self.idasim.FunctionHandler.GetHandler(name)
        if existing_handler:
            if self.__get_handler_name(existing_handler.im_class.__name__, existing_handler.__name__) == handler_name:
                entry[handler_name]['enabled'] = True
        try:
            entry[handler_name]['description'] = handler.__doc__.strip().split('\n')[0].strip()
        except:
            entry[handler_name]['description'] = 'Simulates the ' + name + ' function.'

        return entry

    def __parse_library(self, lib):
        '''
        Parses a loaded library for all handlers.

        @lib - Class instance.
        
        Returns a dictionary of handlers.
        '''
        ignore = ['__init__', '__del__', '__enter__', '__exit__']
        handlers = {}
        instance = lib(IDASIM)

        for (name, obj) in inspect.getmembers(lib, inspect.ismethod):
            if name not in ignore:
                handlers.update(self.__generate_handler_entry(instance, name))
        
        self.functions.update(handlers)
        return handlers

    def __parse_libraries(self):
        '''
        Loads/reloads and parses all IDASimulator handlers.
        '''
        import idasimlib
        reload(idasimlib)
        self.functions = {}

        for module_name in dir(idasimlib):
            # Don't process modules whose file names begin with a double underscore
            if not module_name.startswith('__'):
                try:
                    module = getattr(idasimlib, module_name)
                    reload(module)
                    for (class_name, class_obj) in inspect.getmembers(module, inspect.isclass):
                        # Don't process classes whose names begin with an underscore
                        if not class_name.startswith('_'):
                            self.__parse_library(getattr(module, class_name))
                except Exception, e:
                    print "WARNING: Failed to load %s: %s" % (module_name, str(e))
                    continue

def PLUGIN_ENTRY():
    return idasimulator_t()


########NEW FILE########
__FILENAME__ = application
__all__ = ['Application']

import idc
from architecture import Architecture

class Application(object):
    '''
    Class for invoking functions in the target process.
    '''

    def __init__(self):
        '''
        Class constructor.
        '''
        self.cpu = Architecture()

    def Call(self, function, arguments=[], retaddr=0, block_until_return=True):
        '''
        Call a given function. Arguments must already be configured.
        This should not be used to call functions hooked with IDASimulator or it likely won't work.

        @function           - The name or address of the function to call.
        @arguments          - A list of function arguments.
        @retaddr            - The address to return to.
        @block_until_return - If set to True, this method will not return until the function does.
                              If set to False, this method will return immediately after calling the function.

        Returns the return value of the function on success.
        Returns None on failure, or if block_until_return is False.
        '''
        retval = None

        # Process should already be paused, but just in case...
        idc.PauseProcess()

        # If a function name was specified, get its address
        if isinstance(function, type('')):
            function = idc.LocByName('.' + function)

            if function == idc.BADADDR:
                function = idc.LocByName(function)

        if function != idc.BADADDR:
            if not retaddr:
                retaddr = self.cpu.ProgramCounter()

            # Set the specified function arguments
            self.cpu.SetArguments(arguments)

            # Do any arch-specific initialization before the function call
            self.cpu.PreFunctionCall(function)
    
            # Set up the return address and point the program counter to the start of the target function    
            self.cpu.ReturnAddress(value=retaddr)
            self.cpu.ProgramCounter(value=function)
            idc.Jump(function)

            if block_until_return:
                # Resume process and wait for the target function to return
                idc.StepUntilRet()
                idc.GetDebuggerEvent(idc.WFNE_CONT|idc.WFNE_SUSP, -1)
                idc.Jump(retaddr)
                retval = self.cpu.ReturnValue()
            else:
                idc.ResumeProcess()

        return retval

########NEW FILE########
__FILENAME__ = architecture
__all__ = ['Architecture']

import idc

class Architecture(object):
    '''
    Abstraction class for accessing CPU-specific registers and data.
    '''

    BIG = 'big'
    LITTLE = 'little'

    ARCH = {
        'mips'    : {
                'spoffset'  : 0x10,
                'argreg'    : ['a0', 'a1', 'a2', 'a3'],
                'retval'    : ['v0', 'v1'],
                'sp'        : 'sp',
                'ra'        : 'ra',
                'pc'        : 'pc',
                # Common calling convention for MIPS GCC is to place the address of the function
                # into $t9 and then jalr $t9. The callee then expects $t9 to point to the beginning
                # of itself, so $t9 is used to calculate the relative offset to the global pointer.
                # If $t9 is not set appropriately, any data/code xrefs that rely on $gp will fail.
                'callreg'   : 't9'
        },
        'arm'    : {
                'spoffset'  : 0x10,
                'argreg'    : ['R0', 'R1', 'R2', 'R3'],
                'retval'    : ['R0', 'R1'],
                'sp'        : 'SP',    
                'ra'        : 'LR',
                'pc'        : 'PC',
        },
        'ppc'    : {
                'spoffset'  : 8,
                'argreg'    : ['R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10'],
                'retval'    : ['R3'],
                'sp'        : 'R1',
                'ra'        : 'LR',
                'pc'        : 'PC',
                # GDB stubs for PPC are special...
                'bpt_size'  : 1,
                'bpt_type'  : idc.BPT_EXEC
        },
        'ia32'    : {
                'spoffset'  : 4,
                'argreg'    : [],
                'retval'    : ['EAX'],
                'sp'        : 'ESP',
                'ra'        : '*ESP',
                'pc'        : 'EIP',
        },
        'ia64'    : {
                'spoffset'  : 8,
                'argreg'    : ['RDI', 'RSI', 'RDX', 'RCX', 'R8', 'R9'],
                'retval'    : ['RAX'],
                'sp'        : 'RSP',
                'ra'        : '*RSP',
                'pc'        : 'RIP',
        },
        'win64'    : {
                'spoffset'  : 8,
                'argreg'    : ['RDX', 'RCX', 'R8', 'R9'],
                'retval'    : ['RAX'],
                'sp'        : 'RSP',
                'ra'        : '*RSP',
                'pc'        : 'RIP',
        }
    }
    
    PROCESSORS = {
        'mipsl'    : [{
                'architecture'  : 'mips',
                'endianess'     : LITTLE,
                'bits'          : 32,
        }],
        'mipsb'    : [{
                'architecture'    : 'mips',
                'endianess'    : BIG,
                'bits'        : 32,
        }],
        'arm'    : [{
                'architecture'    : 'arm',
                'endianess'    : LITTLE,
                'bits'        : 32,
        }],
        'armb'    : [{
                'architecture'    : 'arm',
                'endianess'    : BIG,
                'bits'        : 32,
        }],
        'ppc'    : [{
                'architecture'    : 'ppc',
                'endianess'    : BIG,
                'bits'        : 32,
        }],
        'metapc': [{
                'architecture'    : 'ia32',
                'endianess'    : LITTLE,
                'bits'        : 32,
               },
               {
                'architecture'    : 'win64',
                'endianess'    : LITTLE,
                'bits'        : 64,
                # Windows passes args differently in x86_64
                'file_types'    : [idc.FT_PE, idc.FT_EXE]
               },
               {
                'architecture'    : 'ia64',
                'endianess'    : LITTLE,
                'bits'        : 64,
               }
        ],
                
    }

    def __init__(self):
        '''
        Class constructor.
        
        Returns None.
        '''
        self.cpu = None
        self.cpu_name = None
        self.architecture = None
        self.bits64 = False
        self.bits = 0
        self.bsize = 0    

        self.__cpu_id()

        if self.cpu == None:
            if self.bits64:
                bits = '64'
            else:
                # This is an assumption, but it's only for the error message.
                # TODO: How to determine if a target is 16/32 bit from IDA's API?
                bits = '32'

            raise Exception("Unsupported cpu type: %s.%s" % (self.cpu_name, bits))

    def __stack_dword(self, n, value=None):
        addr = self.StackPointer() + self.cpu['spoffset'] + (n * self.bsize)

        if value is not None:
            sval = self.ToString(value, size=self.bsize)
            idc.DbgWrite(addr, sval)

        return idc.DbgDword(addr)

    def __reg_value(self, reg, value=None):
        if value is not None:
            if reg.startswith('*'):
                idc.DbgWrite(idc.GetRegValue(reg[1:]), self.ToString(value))
            else:
                idc.SetRegValue(value, reg)
        
        if reg.startswith('*'):
            return idc.DbgDword(idc.GetRegValue(reg[1:]))
        else:
            return idc.GetRegValue(reg)

    def __cpu_id(self):
        self.cpu_name = idc.GetShortPrm(idc.INF_PROCNAME).lower()
        
        if (idc.GetShortPrm(idc.INF_LFLAGS) & idc.LFLG_64BIT) == idc.LFLG_64BIT:
            self.bits64 = True
        else:
            self.bits64 = False

        for (processor, architectures) in self.PROCESSORS.iteritems():
            if self.cpu_name == processor:
                for arch in architectures:
                    # Only use 64-bit processor modules for a 64 bit binary
                    if (self.bits64 and arch['bits'] != 64) or (not self.bits64 and arch['bits'] == 64):
                        continue

                    # If specific file types were specified for this processor module, make sure the target file is in that list
                    if arch.has_key('file_types') and idc.GetShortPrm(idc.INF_FILETYPE) not in arch['file_types']:
                        continue

                    self.cpu = self.ARCH[arch['architecture']]
                    self.architecture = arch['architecture']
                    self.endianess = arch['endianess']
                    self.bits = arch['bits']
                    self.bsize = self.bits / 8
                    break

                if self.cpu:
                    break
        return None

    def ToString(self, value, size=None):
        '''
        Converts an integer value of size bytes into a raw string of bytes.

        @value - Integer value to be represented as a raw string.
        @size  - Size of the integer value, in bytes.

        Returns a raw string containing the integer value in string form, and in the appropriate endianess.
        '''
        data = ""

        if size is None:
            size = self.bsize

        for i in range(0, size):
            data += chr((value >> (8*i)) & 0xFF)

        if self.endianess != self.LITTLE:
            data = data[::-1]

        return data

    def FromString(self, data, size=None):
        '''
        Converts raw string data into an integer value, with appropriate endianess.

        @data - Raw string data.
        @size - Number of bytes to convert.

        Returns an integer value.
        '''
        i = 0
        value = 0

        if size is None:
            size = len(data)

        if self.endianess != self.LITTLE:
            data = data[::-1]

        for c in data[:size]:
            value += (ord(c) << (8*i))
            i += 1

        return value

    def GetArguments(self, index, n):
        '''
        Get a list of function arguments. Any valid string pointers will be converted to strings.

        @index - First argument index, 0-indexed.
        @n     - The number of arguments to retrieve.

        Returns a list of n arguments.
        '''
        args = []

        for j in range(index, n+index):
            arg = self.Argument(j)
            try:
                sval = idc.GetString(arg)
            except:
                sval = None

            if sval is not None:
                args.append(sval)
            else:
                args.append(arg)

        return args

    def SetArguments(self, arguments):
        '''
        Sets a list of function arguments.

        @arguments - List of function arguments.

        Returns None.
        '''
        for i in range(0, len(arguments)):
            self.Argument(i, value=arguments[i])

    def Argument(self, n, value=None):
        '''
        Read/write function arguments.

        @n     - Argument index number, 0-indexed.
        @value - If specified, the argument will be set to this value.

        Returns the current argument value.
        '''
        regn = len(self.cpu['argreg'])

        if value is not None:
            if n < regn:
                self.__reg_value(self.cpu['argreg'][n], value)
            else:
                self.__stack_dword(n-regn, value)
            
        if n < regn:
            return self.__reg_value(self.cpu['argreg'][n])
        else:
            return self.__stack_dword(n-regn)

    def StackPointer(self, value=None):
        '''
        Read/write the stack pointer register.

        @value - If specified, the stack pointer register will be set to this value.

        Returns the current stack pointer register value.
        '''
        return self.__reg_value(self.cpu['sp'], value)

    def ReturnValue(self, value=None, n=0):
        '''
        Read/write the function return register value.

        @value - If specified, the return register will be set to this value.
        @n     - Return register index number, for those architectures with multiple return registers.

        Returns the current return register value.
        '''
        return self.__reg_value(self.cpu['retval'][n], value)

    def ProgramCounter(self, value=None):
        '''
        Read/write the program counter register.

        @value - If specified, the program counter register will be set to this value.

        Returns the current value of the program counter register.
        '''
        return self.__reg_value(self.cpu['pc'], value)

    def ReturnAddress(self, value=None):
        '''
        Read/write the return address.

        @value - If specified, the return address will be set to this value.

        Returns the current return address value.
        '''
        return self.__reg_value(self.cpu['ra'], value)

    def StackCleanup(self):
        '''
        Cleans up values automatically pushed onto the stack by some architectures (return address in x86 for example).
        '''
        if self.cpu['ra'].startswith('*') and self.cpu['ra'][1:] == self.cpu['sp']:
            self.StackPointer(self.StackPointer() + self.bsize)

    def SetBreakpoint(self, address):
        '''
        Some GDB stubs for various architectures require different breakpoint settings.
        This method sets the appropriate breakpoint for the selected architecture.

        @address - The breakpoint address.

        Returns True on success, False on failure.
        '''
        bpt_size = 0
        bpt_type = idc.BPT_SOFT

        if self.cpu.has_key('bpt_size'):
            bpt_size = self.cpu['bpt_size']
        if self.cpu.has_key('bpt_type'):
            bpt_type = self.cpu['bpt_type']

        return idc.AddBptEx(address, bpt_size, bpt_type)

    def PreFunctionCall(self, function):
        '''
        Configure architecture-specific pre-requisites before calling a function.
        Called internally by Application.Call.

        @function - The address of the function to call.

        Returns None.
        '''
        if self.cpu.has_key('callreg'):
            idc.SetRegValue(function, self.cpu['callreg'])

########NEW FILE########
__FILENAME__ = exceptions
class JumpTo(Exception):
    pass

class GoTo(Exception):
    pass

########NEW FILE########
__FILENAME__ = handler
__all__ = ['IDASimFunctionHandler']

import idc
import idaapi
import inspect
import traceback
from exceptions import *
from architecture import Architecture

class IDASimFunctionHandler(object):
    '''
    Registers and manages function simulators.
    '''
    FUNCTION_HANDLERS = {}
    DEFAULT_HANDLER = None
    BPT_CND = '%s.Handler()'
    STUB_NAMING_CONVENTION = '.%s'

    def __init__(self, idbm, name=None, verbose=False):
        '''
        Class constructor.

        @idbm    - Instance of IDASimMMU.
        @name    - Name that will be assigned to the class instance.
        @verbose - Enable verbose mode.

        Returns None.
        '''
        self.idbm = idbm
        self.name = name
        self.verbose = verbose
        self.cpu = Architecture()

        if self.name == None:
            self.name = self.__get_my_name()

        self.bpt_cnd = self.BPT_CND % self.name

        self.UnregisterHandlers()

        # Eval this IDC expression to ensure that Python is set as the
        # preferred external scripting language. This is necessary for the
        # Python function handler to operate correctly.
        idc.Eval('RunPlugin("python", 3)')

    def cleanup(self):
        idc.Eval('RunPlugin("python", 4)')

    def __del__(self):
        self.cleanup()

    def __get_my_name(self):
        '''
        This is a hack to get the name of the class instance variable. For internal use only.
        '''
        i = -3
        (filename, line_number, function_name, text) = traceback.extract_stack()[i]
        name = text[:text.find('=')].strip()
        while 'self' in name:
            i -= 1
            (filename, line_number, function_name, text) = traceback.extract_stack()[i]
            name = name.replace('self', text[:text.find('=')].strip())
        return name

    def SetHandlerBreakpoint(self, address):
        '''
        Sets a handler breakpoint on the specified address.

        @address - Address to set the breakpoint at.

        Returns True on success, False on failure.
        '''
        # Some remote debugger stubs have special needs for different architectures (e.g., gdb).
        # Thus, setting breakpoints should be done through the architecture abstraction class, 
        # rather than directly through AddBpt/AddBptEx.
        self.cpu.SetBreakpoint(address)

        # A bug in versions of IDAPython shipped with IDA prior to 6.4sp1 improperly interpreted 
        # the is_lowcnd value set via SetBptCnd/SetBptCndEx. Do this directly through idaapi
        # ourselves in order to support older versions.
        bpt = idaapi.bpt_t()
        idaapi.get_bpt(address, bpt)
        bpt.condition = self.bpt_cnd
        bpt.flags &= ~idc.BPT_LOWCND
        return idaapi.update_bpt(bpt)

    def __register_internal_handler(self, name, handler):
        '''
        Internal handler registration function. For internal use only.
        '''
        if type(name) == type(""):
            address = idc.LocByName(name)
        else:
            address = name

        if address != idc.BADADDR:
            bpt_result = self.SetHandlerBreakpoint(address)

            if bpt_result:
                self.FUNCTION_HANDLERS[name] = {}
                self.FUNCTION_HANDLERS[name]["handler"] = handler
                self.FUNCTION_HANDLERS[name]["address"] = address

            return bpt_result
        else:
            return False

    def Handler(self):
        '''
        Breakpoint condition handler, called by IDA to evaluate conditional brekpoints. It in turn calls the 
        appropriate function handler, populates the return value and puts execution back at the return address. 
    
        This is a (slight) abuse of IDA's conditional breakpoints; this function always returns 0, indicating that
        the breakpoint condition has not been met. However, it does ensure that every call to a given function
        can be intercepted and simulated, regardless of whether the process is running freely, or the function has 
        been stepped over, stepped into, etc.
        '''
        retval = 0
        retaddr = None

        if self.verbose:
            print self.FUNCTION_HANDLERS

        for (name, properties) in self.FUNCTION_HANDLERS.iteritems():
            if self.cpu.ProgramCounter() == properties["address"]:
                handler = properties["handler"]
                break

        # If no explicit handler was found, use the default handler
        if not handler and self.DEFAULT_HANDLER:
            handler = self.DEFAULT_HANDLER

        if handler:
            if self.verbose:
                print "Using function handler:", handler.__name__

            parameters = {}
        
            # Enumerate the arguments and default values for the handler    
            args, varargs, keywords, defaults = inspect.getargspec(handler)
            try:
                defaults = dict(zip(reversed(args), reversed(defaults)))
            except:
                defaults = {}

            # Build the handler parameters
            try:
                i = 0
                for arg in args:
                    if arg != 'self':
                        parameters[arg] = self.cpu.Argument(i)
                        
                        if defaults.has_key(arg):
                            # If default value is of type string, get the string automatically
                            if type(defaults[arg]) == type(''):
                                parameters[arg] = idc.GetString(parameters[arg])
                            # If default value is of type list, get an array of bytes
                            elif type(defaults[arg]) == type([]) and len(defaults[arg]) == 1:
                                parameters[arg] = [c for c in idc.DbgRead(parameters[arg], defaults[arg][0])]
                        i += 1
            except Exception, e:
                print "WARNING: Failed to parse handler parameters:", str(e)
                parameters = {}

            try:
                retval = handler(**parameters)
            except JumpTo, offset:
                retaddr = self.cpu.ReturnAddress() + offset.message
            except GoTo, addr:
                retaddr = addr.message
            except Exception, e:
                print "WARNING: Failed to simulate function '%s': %s" % (handler.__name__, str(e))
                retval = 0

            if retval is not None:
                if retaddr is None:
                    retaddr = self.cpu.ReturnAddress()

                # If a string type was returned by the handler, place the string in memory and return a pointer
                if type(retval) == type(""):
                    retval = self.idbm.malloc(retval)
                # Map python's True and False to 1 and 0 repsectively
                elif retval == True:
                    retval = 1
                elif retval == False:
                    retval = 0

                self.cpu.ReturnValue(retval)
                self.cpu.ProgramCounter(retaddr)
                self.cpu.StackCleanup()
    
                # Since the PC register is manually manipulated, a breakpoint set on the return
                # address won't be triggered. In this case, make sure we pause the process manually.
                if idc.CheckBpt(self.cpu.ProgramCounter()) > 0:
                    idc.PauseProcess()
            
        return 0

    def RegisterDefaultHandler(self, handler):
        '''
        Register a default "catch-all" handler.

        @handler - Method/function handler.

        Returns None.
        '''
        self.DEFAULT_HANDLER = handler

    def UnregisterDefaultHandler(self):
        '''
        Unregister a default "catch-all" handler.
        
        Returns None.
        '''
        self.DEFAULT_HANDLER = None

    def RegisterHandler(self, name, handler, stubs=True):
        '''
        Registers a given function handler for a given function name.
    
        @name    - Name of the function.
        @handler - The function handler to call.
        @stubs   - If True, handle calls to both extern and stub addresses.

        Returns True on success, False on failure.
        '''

        retval = self.__register_internal_handler(name, handler)

        if retval and stubs and type(name) == type(""):
            stub_name = self.STUB_NAMING_CONVENTION % name
            retval = self.__register_internal_handler(stub_name, handler)
            
        return retval

    def RegisterHandlers(self, handlers, stubs=True):
        '''
        Registers a set of function handlers.

        @handlers - A dictionary consisting of 'name':handler pairs.
        @stubs    - If True, handle calls to both extern and stub addresses.
        
        Returns the number of handlers successfully registered.
        '''
        count = 0

        for (name, handler) in handlers.iteritems():
            if self.RegisterHandler(name, handler, stubs):
                count += 1

        return count

    def UnregisterHandler(self, name, stubs=True):
        '''
        Removes a function handler by name.

        @name  - The name of the function handler to be removed.
        @stubs - If True, corresponding function stub handlers that were automatically created by RegisterHandler will also be removed.

        Returns None.
        '''
        addr = None
        stub_name = None
        stub_addr = None

        if name is not None:
            try:
                stub_name = self.STUB_NAMING_CONVENTION % name
            except:
                pass

            if self.FUNCTION_HANDLERS.has_key(name):
                addr = self.FUNCTION_HANDLERS[name]['address']

            if self.FUNCTION_HANDLERS.has_key(stub_name):
                stub_addr = self.FUNCTION_HANDLERS[stub_name]['address']

        if addr is not None and name is not None:
            idc.DelBpt(addr)
            del self.FUNCTION_HANDLERS[name]

        if stubs and stub_addr is not None and stub_name is not None:
            idc.DelBpt(stub_addr)
            del self.FUNCTION_HANDLERS[stub_name]

    def UnregisterHandlers(self, purge=False):
        '''
        Deletes breakpoints for all registered handlers.

        @purge - Removes all handlers for all instances of IDBFunctionHandler.

        Returns None.
        '''
        self.UnregisterDefaultHandler()
    
        if not purge:
            # Only remove this instance's handlers
            for (name, info) in self.FUNCTION_HANDLERS.iteritems():
                condition = idc.GetBptAttr(info['address'], idc.BPTATTR_COND)

                if condition == self.bpt_cnd:
                    idc.DelBpt(info['address'])
        else:
            # Try to remove ALL instance's handlers (this could remove other conditional breakpoints...)
            for i in range(0, idc.GetBptQty()):
                ea = idc.GetBptEA(i)
                condition = idc.GetBptAttr(ea, idc.BPTATTR_COND)
                if condition.endswith(self.BPT_CND % ''):
                    idc.DelBpt(ea)
        
        self.FUNCTION_HANDLERS = {}

    def GetHandler(self, name):
        '''
        Returns the current handler for the named location.

        @name - Function/location name.

        Returns the handler instance.
        '''
        if self.FUNCTION_HANDLERS.has_key(name):
            return self.FUNCTION_HANDLERS[name]["handler"]
        else:
            return None


########NEW FILE########
__FILENAME__ = idasim
__all__ = ['IDASim']

import idc
import idaapi
import idautils
from mmu import *
from handler import *
from exceptions import *
from application import *
from architecture import *

class IDASimDbgHook(idaapi.DBG_Hooks):
    '''
    Resets the IDASimMMU base address (MP) whenever the debugger is started/stopped.
    Executes startup code when the debugger is started, if specified.
    Only used internally by the IDASim class.
    '''
    def dbg_init(self, idasim):
        self.debugging = False
        self.sim = idasim
        self.hook()

    def dbg_process_start(self, pid, tid, ea, name, base, size):
        self.sim.mmu.reset()
        if not self.debugging:
            self.debugging = True
            self.sim.InitHandler(init=True)

    def dbg_process_exit(self, pid, tid, ea, code):
        self.debugging = False
        self.sim.mmu.reset()

    def dbg_process_attach(self, pid, tid, ea, name, base, size):
        self.sim.mmu.reset()
        if not self.debugging:
            self.debugging = True
            self.sim.InitHandler(init=True)

    def dbg_process_detatch(self, pid, tid, ea):
        self.debugging = False
        self.sim.mmu.reset()

class IDASim(object):
    '''
    Class for easily simulating library function calls and initializing memory/registers when debugging emulated code in IDA. 
    '''

    def __init__(self, handlers={}, debug=False, attach=False, membase=None):
        '''
        Class constructor.

        @handlers  - A dictionary of function names/addresses to simulate and their corresponding handlers.
        @debug     - Set to True to automatically start debugging.
        @attach    - Set to True to attach to a process, rather than directly running the debugger.
        @membase   - Specify the base address to start at when allocating memory.

        Returns None.
        '''
        self.user_handlers = handlers
        self.script = None
        self.script_name = None

        self.cpu = Architecture()
        self.mmu = IDASimMMU()
        self.app = Application()
        self.FunctionHandler = IDASimFunctionHandler(self.mmu)
        self.dbg_hook = IDASimDbgHook()
        self.dbg_hook.dbg_init(self)

        self.__register_handlers()
        
        if attach:
            self.AttachDebugger()
        elif debug:
            self.StartDebugger()

        if membase is not None:
            self.mmu.base(membase)

    def __register_handlers(self):
        '''
        Registers function names and handlers with the IDB function handler.
        For internal use only.
        '''
        for (name, handler) in self.user_handlers.iteritems():
            self.FunctionHandler.RegisterHandler(name, handler)

    def __get_instance_methods(self, instance):
        methods = {}

        for name in dir(instance):
            if not name.startswith('_'):
                obj = getattr(instance, name)
                if 'method' in type(obj).__name__:
                    methods[name] = obj

        return methods

    def InitHandler(self, init=False):
        if self.script is not None:
            if (self.script_name is not None and not init) or (self.script_name is None and init):
                script_globals = {
                        'IDASIM'     : self,
                        'idc'        : idc,
                        'idaapi'    : idaapi,
                        'idautils'    : idautils,
                }

                script_globals.update(self.__get_instance_methods(self))
                script_globals.update(self.__get_instance_methods(self.cpu))

                try:
                    exec(self.script, script_globals)
                except Exception, e:
                    print "Failed to exec startup script:", str(e)
                    print "################"
                    print self.script
                    print "################"
        return None

    def ExecuteOnStart(self, script=None, name=None, disable=False):
        '''
        Specify a Python string to be evaluated when the debugger is started/attahced.

        @script - Python string to be evaluated. If None, this feature will be disabled.

        Returns None.
        '''
        self.script = script

        if disable:
            self.FunctionHandler.UnregisterHandler(self.script_name)
            self.script_name = None
        elif name is not None and script is not None:
            self.FunctionHandler.RegisterHandler(name, self.InitHandler)
            
        self.script_name = name
        
    def vsprintf(self, fmt, index):
        '''
        Builds a string from a format string and format arguments.
                
        @fmt   - The format string.
        @index - The function argument number at which the format string arguments start (0-indexed).

        Returns a formatted string.
        '''
        n = 0
        for i in range(0, len(fmt)-1):
            if fmt[i] == '%' and fmt[i+1] != '%':
                n += 1

        return fmt % tuple(self.cpu.GetArguments(index, n))

    def WaitForDebugger(self):
        '''
        Waits for the debugger event (WFNE_CONT | WFNE_SUSP).
        Called internally by StartDebugger and AttachDebugger.

        Returns None.
        '''
        idc.GetDebuggerEvent(idc.WFNE_CONT | idc.WFNE_SUSP, -1)

    def StartDebugger(self):
        '''
        Starts the debugger (equivalent of pressing F9).

        Returns None.
        '''
        idc.StartDebugger('', '', '')
        self.WaitForDebugger()

    def AttachDebugger(self, pid=-1):
        '''
        Attaches the debugger to a running process.

        @pid - The PID of the process to attach to (user will be prompted if not specified).

        Returns None.
        '''
        idc.AttachProcess(pid, -1)
        self.WaitForDebugger()

    def Malloc(self, data=None, size=0):
        '''
        Allocates space in the debugger's memory.

        @data - Fill the allocated space with this data.
        @size - If data is None, allocate and zero out size bytes of memory.

        Returns the address of the allocated memory.
        '''
        return self.mmu.malloc(data, size)

    def String(self, string, raw=False):
        '''
        Creates a NULL-terminated string in the debugger's memory.

        @string - The string, or list of strings, to place into memory.
        @raw    - If set to True, the string will not be NULL terminated.

        Returns the address, or list of addresses, of the string(s) in memory.
        '''
        addrs = []

        if type(string) == type(""):
            array = [string]
        else:
            array = string

        for s in array:
            if not raw:
                s = s + "\x00"
            addrs.append(self.Malloc(s))

        if type(string) == type(""):
            addrs = addrs[0]

        return addrs

    def Int(self, value, size):
        '''
        Creates an integer value of size bytes in the debugger's memory.

        @value - The integer value, or list of values, to place into memory.
        @size  - The size of the interger value(s), in bytes.

        Returns the address, or a list of addresses, of the integer(s) in memory.
        '''
        data = []

        if type(value) != type([]):
            value = [value]

        for d in value:
            data.append(self.cpu.ToString(d, size))

        return self.String(data, raw=True)

    def DoubleWord(self, dword):
        '''
        Places a double word integer into the debugger's memory.
        
        @dword - The value, or list of values, to place into memory.

        Returns the address, or a list of addresses, of the dword(s) in memory.
        '''
        return self.Int(dword, self.cpu.bsize*2)

    def Word(self, word):
        '''
        Places a word-sized integer into the debugger's memory.

        @word - The four byte integer value, or list of values, to place into memory.

        Returns the address, or a list of addresses, of the word(s) in memory.
        '''
        return self.Int(word, self.cpu.bsize)

    def HalfWord(self, hword):
        '''
        Places a half-word sized integer into the debugger's memory.

        @hword - The two byte value, or list of values, to place into memory.

        Returns the address, or a list of addresses, of the half word(s) in memory.
        '''
        return self.Int(hword, self.cpu.bsize/2)

    def Byte(self, byte):
        '''
        Places one byte of data into the debugger's memory.
        
        @byte - The byte value, or list of values, to place into memory.
        
        Returns the address, or a list of addresses, of the byte(s) in memory.
        '''
        return self.Int(byte, 1)

    def ARGV(self, argv):
        '''
        Allocates space for an argv data structure.

        @argv - A list of argv strings.

        Returns the address of the argv array of pointers.
        '''
        return self.Word(self.String(argv))[0]

    def Cleanup(self):
        '''
        Removes all registered function simulation hooks.

        Returns None.
        '''
        self.FunctionHandler.UnregisterHandlers()


########NEW FILE########
__FILENAME__ = mmu
__all__  = ['IDASimMMU']

import idc
import idaapi
from application import Application
from architecture import Architecture

class IDASimMMU(object):
    '''
    Manages the allocation of memory while running in the debugger.
    The term 'manage' is used very loosely here; it really only allocates memory.
    '''
    ALIGN = 4
    DEFAULT_MP = 0x100000
    SEGNAME = 'MMU'
    LAST_SEGNAME = ['MEMORY', 'RAM']

    def __init__(self, base=None):
        '''
        Class constructor.
        '''
        # Disable this for now, it doesn't work.
        self.use_native_malloc = False
        self.allocated_addresses = {}

        self.app = Application()
        self.cpu = Architecture()

        if base is not None:
            self.MP = self.BASE_MP = base
        else:
            self.MP = self.BASE_MP = idc.BADADDR

    def _detect_membase(self):
        '''
        Attempts to locate a section of memory for IDBMMU's internal memory allocation.
        For internal use only.
        '''
        if self.BASE_MP == idc.BADADDR:

            # Look for the MMU segment
            ea = idc.SegByName(self.SEGNAME)

            # No MMU segment?
            if ea == idc.BADADDR:
                ea = 0

                # Find the very last defined segment
                while True:
                    segea = idc.NextSeg(ea)
                    
                    if segea == idc.BADADDR:
                        break
                    else:
                        ea = segea

                # Is it not a memory segment?
                if idc.SegName(ea) not in self.LAST_SEGNAME:
                    try:
                        # Find the start of the stack
                        ea = idc.SegStart(self.cpu.StackPointer())

                        # Still nothing? Use the default.
                        if ea == idc.BADADDR:
                            ea = self.DEFAULT_MP
                    except:
                        if not self.use_native_malloc:
                            raise Exception("No available segments for memory allocation! Try defining segment %s." % self.SEGNAME)
            self.BASE_MP = ea

        if self.MP == idc.BADADDR:
            self.MP = self.BASE_MP

        return self.BASE_MP

    def reset(self):
        '''
        Resets the current allocation address.
        '''
        self.MP = idc.BADADDR
        self.allocated_addresses = {}

    def base(self, base=None):
        '''
        Set the base address at which to start allocating memory. Default: 0x100000.

        @base - The base address. If specified BASE_MP will be set to this value.

        Returns the current BASE_MP value.
        '''
        if base is not None:
            self.MP = self.BASE_MP = base
        return self.BASE_MP

    def malloc(self, data=None, size=0):
        '''
        Allocates space for data in the debugger's memory and populates it.
    
        @data - Data to place into memory. If None, NULL bytes will be used.
        @size - Size of memory to allocate. If 0, len(data) bytes will be allocated.
    
        Returns the address of the allocated memory.
        '''
        if size == 0 and data is not None:
            size = len(data)
    
        if data is None:
            data = "\x00" * size

        if self.use_native_malloc:
            addr = self.app.Call('malloc', arguments=[size], retaddr=self.cpu.ReturnAddress())
        else:
            self._detect_membase()
    
            addr = self.MP
            self.MP += size
            # This ensures memory addresses are 4-byte aligned. This is important for some architectures.
            if (self.MP % self.ALIGN) > 0:
                self.MP += (self.ALIGN - (self.MP % self.ALIGN))

            # Keep a dictionary of allocated addresses and their sizes
            self.allocated_addresses[addr] = size
    
        idc.DbgWrite(addr, data)
    
        return addr


########NEW FILE########
__FILENAME__ = localxrefs
# IDA Plugin to search for cross references only within the current defined function.
#
# Useful, for example, to find instructions that use a particular register, or that reference a literal value.
#
# Invoke by highlighting the desired text in IDA, then going to Jump->List local xrefs, or by pressing Alt+8.
# Highlighting is also supported; once xrefs are found, type the following in the Python command window:
#
#	Python> localxrefs.highlight()       <-- Highlight all xrefs
#	Python> localxrefs.highlight(False)  <-- Un-highlight all xrefs
#
# Craig Heffner
# Tactical Network Solutions

import idc
import idaapi

localxrefs = None

class LocalXrefs(object):

	UP   = 'Up  '
	DOWN = 'Down'
	THIS = '-   '

	READ    = 'r'
	WRITE   = 'w'

	OPND_WRITE_FLAGS = {
			0	: idaapi.CF_CHG1,
			1	: idaapi.CF_CHG2,
			2	: idaapi.CF_CHG3,
			3	: idaapi.CF_CHG4,
			4	: idaapi.CF_CHG5,
			5	: idaapi.CF_CHG6,
	}

	def __init__(self):
		self.xrefs = {}
		self.function = ''
		self._profile_function()

	def _profile_function(self):
		current_ea = ScreenEA()
		current_function = idc.GetFunctionName(current_ea)
		current_function_ea = idc.LocByName(current_function)

		if current_function:
			self.function = current_function

		ea = start_ea = idc.GetFunctionAttr(current_function_ea,  idc.FUNCATTR_START)
		end_ea = idc.GetFunctionAttr(current_function_ea, idc.FUNCATTR_END)

		self.highlighted = idaapi.get_highlighted_identifier()

		while ea < end_ea and ea != idc.BADADDR and self.highlighted:

			i = 0
			match = False
			optype = self.READ
			comment = None

			idaapi.decode_insn(ea)
			
			mnem = idc.GetMnem(ea)

			if self.highlighted in mnem:
				match = True
			elif idaapi.is_call_insn(ea):
				for xref in idautils.XrefsFrom(ea):
					if xref.type != 21:
						name = idc.Name(xref.to)
						if name and self.highlighted in name:
							match = True
							break
			else:	
				while True:
					opnd = idc.GetOpnd(ea, i)
					if opnd:
						if self.highlighted in opnd:
							match = True
							if (idaapi.insn_t_get_canon_feature(idaapi.cmd.itype) & self.OPND_WRITE_FLAGS[i]):
								optype = self.WRITE
						i += 1
					else:
						break

			if not match:
				comment = idc.GetCommentEx(ea, 0)
				if comment and self.highlighted in comment:
					match = True
				else:
					comment = idc.GetCommentEx(ea, 1)
					if comment and self.highlighted in comment:
						match = True
					else:
						comment = None

			if match:
				if ea > current_ea:
					direction = self.DOWN
				elif ea < current_ea:
					direction = self.UP
				else:
					direction = self.THIS

				self.xrefs[ea] = {
					'offset' 	: idc.GetFuncOffset(ea),
					'mnem'	 	: mnem,
					'type'		: optype,
					'direction'	: direction,
					'text'		: idc.GetDisasm(ea),
				}

			ea += idaapi.cmd.size

	def highlight(self, highlight=True, mnem=None, optype=None, direction=None, text=None):
		for (ea, info) in self.xrefs.iteritems():
			if mnem and info['mnem'] != mnem:
				highlight = False
			elif optype and info['optype'] != optype:
				highlight = False
			elif direction and info['direction'] != direction:
				highlight = False
			elif text and info['text'] != text:
				highlight = False

			if highlight:
				color = 0x00ff00
			else:
				color = idc.DEFCOLOR

			idc.SetColor(ea, idc.CIC_ITEM, color)

	def unhighlight(self):
		self.highlight(False)
		
	
class localizedxrefs_t(idaapi.plugin_t):
	flags = 0
	comment = "IDA Localized Xrefs"
	help = ""
	wanted_name = "Localized Xrefs"
	wanted_hotkey = ""

	DELIM = '-' * 86
	HEADER = '\nXrefs to %s from %s:'

	def init(self):
		self.menu_context = idaapi.add_menu_item("Jump/", "List local xrefs", "Alt-8", 0, self.run, (None,))
		return idaapi.PLUGIN_KEEP

	def term(self):
		idaapi.del_menu_item(self.menu_context)
		return None

	def run(self, arg):
		global localxrefs
		fmt = ''

		r = LocalXrefs()
		localxrefs = r

		offsets = r.xrefs.keys()
		offsets.sort()

		if r.highlighted:
			print self.HEADER % (r.highlighted, r.function)
			print self.DELIM
			
			for ea in offsets:
				info = r.xrefs[ea]
	
				if not fmt:
					fmt = "%%s   %%s   %%-%ds   %%s" % (len(info['offset']) + 15)

				print fmt % (info['direction'], info['type'], info['offset'], info['text'])
	
			print self.DELIM

def PLUGIN_ENTRY():
	return localizedxrefs_t()


########NEW FILE########
__FILENAME__ = mipslocalvars
# IDA plugin to name stack variables that are simply used to store register values until a function returns ($ra, $s0-$s7, $fp, $gp).
#
# Invoke by going to Options->Name saved registers, or by using the Alt+4 hotkey.
#
# Craig Heffner
# Tactical Network Solutions

import idc
import idaapi
import idautils

class NameMIPSSavedRegisters(object):

	INSIZE = 4
	SEARCH_DEPTH = 25

	ARCH = {
			'arguments'	: ['$a0', '$a1', '$a2', '$a3'],
			'savedregs'	: ['$s0', '$s1', '$s2', '$s3', '$s4', '$s5', '$s6', '$s7', '$fp', '$gp', '$ra'],
	}

	def __init__(self):
		print "Naming saved register locations...",

		for ea in idautils.Functions():
			mea = ea
			named_regs = []
			last_iteration = False

			while mea < (ea + (self.INSIZE * self.SEARCH_DEPTH)):
				mnem = idc.GetMnem(mea)

				if mnem in ['sw', 'sd']:
					reg = idc.GetOpnd(mea, 0)
					dst = idc.GetOpnd(mea, 1)
	
					if reg in self.ARCH['savedregs'] and reg not in named_regs and dst.endswith('($sp)') and 'var_' in dst:
						offset = int(dst.split('var_')[1].split('(')[0], 16)
						idc.MakeLocal(ea, idc.FindFuncEnd(ea), "[sp-%d]" % offset, "saved_%s" % reg[1:])
						named_regs.append(reg)
				
				if last_iteration:
					break
				elif mnem.startswith('j') or mnem.startswith('b'):
					last_iteration = True

				mea += self.INSIZE

		print "done."


class mips_saved_registers_t(idaapi.plugin_t):
	flags = 0
	comment = ""
	help = ""
	wanted_name = "Names MIPS registers saved on the stack"
	wanted_hotkey = ""

	def init(self):
		self.menu_context = idaapi.add_menu_item("Options/", "Name saved registers", "Alt-4", 0, self.name_saved_registers, (None,))
		return idaapi.PLUGIN_KEEP

	def term(self):
		idaapi.del_menu_item(self.menu_context)
		return None

	def run(self, arg):
		pass

	def name_saved_registers(self, arg):
		NameMIPSSavedRegisters()

def PLUGIN_ENTRY():
	return mips_saved_registers_t()


########NEW FILE########
__FILENAME__ = mipsrop
# IDA plugin for identifying ROP gadgets in Linux MIPS binaries.
#
# Return Oriented Programming in Linux MIPS is more like Jump Oriented Programming; the idea is to
# control enough of the stack/registers in order to control various jumps. Since all instructions
# in MIPS must be 4-byte aligned, you cannot "create" new instructions by returning into the middle
# of existing instructions, as is possible with some other architectures.
#
# In any given MIPS function, various registers are saved onto the stack by necessity:
#
#	o $s0 - $s7
#	o $fp
#	o $ra
#
# These values are restored from the stack before the function returns, thus, during a stack overflow
# one can control some or all of these register values. The subroutine registers ($s*) are of particular
# interest, as they are commonly used by the compiler to store function pointers. By convention, gcc will
# move function pointers into the $t9 register, then call the function using jalr:
#
# 	move $t9, $s0  <-- If we control $s0, we control where the jump is taken
#	jalr $t9
#
# While there are other jumps that are of use, and which this plugin searches for, the premise is the same:
# control the stack/registers, and you control various jumps allowing you to chain various blocks of code
# together.
#
# With a list of controllable jumps such as these, we then just need to search the surrounding instructions
# to see if they perform some operation which may be useful. For example, let's say we need to load the
# value 1 into the $a0 register; in this case, we would want to look for a controllable jump such as this:
#
#	move $t9, $s1
#	jalr $t9
#	li $a0, 1    <-- Remember MIPS has jump delay slots, so this instruction is executed with the jump
#
# If we return to this piece of code (and if we control $s1), we can pre-load $s1 with the address of the
# next ROP gadget; thus, $a0 will be loaded with the value 1 and we can chain this block of code with other
# gadgets in order to perform more complex operations.
#
# This plugin finds all potentially controllable jumps, and then allows you to search for desired instructions
# surrounding these controllable jumps. Example:
#
#	Python> mipsrop.find("li $a0, 1")
#	----------------------------------------------------------------------------------------------------
#	|  Address     |  Action                                              |  Control Jump              |
#	----------------------------------------------------------------------------------------------------
#	|  0x0002F0F8  |  li $a0,1                                            |  jalr  $s4                 |
#	|  0x00057E50  |  li $a0,1                                            |  jalr  $s1                 |
#	----------------------------------------------------------------------------------------------------
#
# The output shows the offset of each ROP gadget, the instruction within the gadget that your search matched,
# and the effective register that is jumped to after that instruction is executed.
#
# The specified instruction can be a full instruction, such as the example above, or a partial instruction.
# Regex is supported for any of the instruction mnemonics or operands; for convenience, the dollar signs in 
# front of register names are automatically escaped.
#
# Craig Heffner
# Tactical Network Solutions

import re
import idc
import idaapi
import idautils

# Global instance of MIPSROPFinder
mipsrop = None

class MIPSInstruction(object):
	'''
	Class for storing info about a specific instruction.
	'''

	def __init__(self, mnem, opnd0=None, opnd1=None, opnd2=None, ea=idc.BADADDR):
		self.mnem = mnem
		self.operands = [opnd0, opnd1, opnd2]
		self.opnd0 = opnd0
		self.opnd1 = opnd1
		self.opnd2 = opnd2
		self.ea = ea

	def __str__(self):
		string = self.mnem + " "

		for op in self.operands:
			if op:
				string += "%s," % op
			else:
				break

		return string[:-1]

class ROPGadget(object):
	'''
	Class for storing information about a specific ROP gadget.
	'''
	
	def __init__(self, control, jump, operation=None, description="ROP gaget"):
		self.h = '-' * 112
		self.control = control
		self.exit = jump
		self.operation = operation
		self.description = description
		
		if self.control.opnd1:
			self.control.register = self.control.opnd1
		else:
			self.control.register = self.control.opnd0

		if self.exit.opnd1:
			self.exit.register = self.exit.opnd1
		else:
			self.exit.register = self.exit.opnd0
		
		if self.operation:
			if self.operation.ea < self.control.ea:
				self.entry = self.operation
			else:
				self.entry = self.control
		else:
			self.operation = self.control
			self.entry = self.control


	def header(self):
		return self.h + "\n|  Address     |  Action                                              |  Control Jump                          |\n" + self.h

	def footer(self):
		return self.h

	def __str__(self):
		return "|  0x%.8X  |  %-50s  |  %-5s %-30s  |" % (self.entry.ea, str(self.operation), self.exit.mnem, self.control.register)

class BowcasterBuilder(object):
	'''
	Class to generate bowcaster code from a list of selected ROP gadgets. WIP.
	'''

	INSIZE = 4
	SEARCH_DEPTH = 25

	def __init__(self, gadgets):
		self.code = []
		self.gadgets = gadgets

	def build_code(self):
		keys = self.gadgets.keys()
		keys.sort()
	
		for key in keys[::-1]:
			last_instruction = False
			ea = self.gadgets[key]
			end_ea = ea + self.SEARCH_DEPTH

			while ea <= end_ea:
				mnem = idc.GetMnem(ea)
				if mnem in ['jr', 'jalr']:
					last_instruction = True
				ea += self.INSIZE

	def print_code(self):
		for line in self.code:
			print line

class MIPSROPFinder(object):
	'''
	Primary ROP finder class.
	'''

	CODE = 2
        DATA = 3
	INSIZE = 4
        SEARCH_DEPTH = 25
	
	def __init__(self):
		self.start = idc.BADADDR
		self.end = idc.BADADDR
		self.system_calls = []
		self.double_jumps = []
		self.controllable_jumps = []
		start = 0
		end = 0

		for (start, end) in self._get_segments(self.CODE):
			self.controllable_jumps += self._find_controllable_jumps(start, end)
			self.system_calls += self._find_system_calls(start, end)
			self.double_jumps += self._find_double_jumps(start, end)
			if self.start == idc.BADADDR:
				self.start = start
		self.end = end
	
		if self.controllable_jumps or self.system_calls:
			print "MIPS ROP Finder activated, found %d controllable jumps between 0x%.8X and 0x%.8X" % (len(self.controllable_jumps), self.start, self.end)
		
	def _get_segments(self, attr):
		segments = []
		start = idc.BADADDR
		end = idc.BADADDR
		seg = idc.FirstSeg()

		while seg != idc.BADADDR:
			if idc.GetSegmentAttr(seg, idc.SEGATTR_TYPE) == attr:
				start = idc.SegStart(seg)
				end = idc.SegEnd(seg)
				segments.append((start, end))
			seg = idc.NextSeg(seg)

		return segments

	def _get_instruction(self, ea):
		return MIPSInstruction(idc.GetMnem(ea), idc.GetOpnd(ea, 0), idc.GetOpnd(ea, 1), idc.GetOpnd(ea, 2), ea)

	def _does_instruction_match(self, ea, instruction, regex=False):
		i = 0
		op_cnt = 0
		op_ok_cnt = 0
		match = False
		ins_size = idaapi.decode_insn(ea)
		mnem = GetMnem(ea)

		if (not instruction.mnem) or (instruction.mnem == mnem) or (regex and re.match(instruction.mnem, mnem)):
			for operand in instruction.operands:
				if operand:
					op_cnt += 1
					op = idc.GetOpnd(ea, i)

					if regex:
						if re.match(operand, op):
							op_ok_cnt += 1
					elif operand == op:
						op_ok_cnt += 1
				i += 1

			if op_cnt == op_ok_cnt:
				match = True

		return match

	def _is_bad_instruction(self, ea, bad_instructions=['j', 'b'], no_clobber=[]):
		bad = False
		mnem = GetMnem(ea)

		if mnem and mnem[0] in bad_instructions:
			bad = True
		else:
			for register in no_clobber:
				if (idaapi.insn_t_get_canon_feature(idaapi.cmd.itype) & idaapi.CF_CHG1) == idaapi.CF_CHG1:
					if idc.GetOpnd(ea, 0) == register:
						bad = True

		return bad

	def _contains_bad_instruction(self, start_ea, end_ea, bad_instructions=['j', 'b'], no_clobber=[]):
		ea = start_ea

		while ea <= end_ea:
			if self._is_bad_instruction(ea, bad_instructions, no_clobber):
				return True
			else:
				ea += self.INSIZE

		return False
		
	def _find_prev_instruction_ea(self, start_ea, instruction, end_ea=0, no_baddies=True, regex=False, dont_overwrite=[]):
		instruction_ea = idc.BADADDR
		ea = start_ea
		baddies = ['j', 'b']

		while ea >= end_ea:
			if self._does_instruction_match(ea, instruction, regex):
				instruction_ea = ea
				break
			elif no_baddies and self._is_bad_instruction(ea, no_clobber=dont_overwrite):
				break

			ea -= self.INSIZE

		return instruction_ea

	def _find_next_instruction_ea(self, start_ea, instruction, end_ea=idc.BADADDR, no_baddies=False, regex=False, dont_overwrite=[]):
		instruction_ea = idc.BADADDR
		ea = start_ea

		while ea <= end_ea:
			if self._does_instruction_match(ea, instruction, regex):
				instruction_ea = ea
				break
			elif no_baddies and self._is_bad_instruction(ea, no_clobber=dont_overwrite):
				break

			ea += self.INSIZE

		return instruction_ea

	def _find_controllable_jumps(self, start_ea, end_ea):
		controllable_jumps = []
		t9_controls = [
			MIPSInstruction("move", "\$t9"),
			MIPSInstruction("addiu", "\$t9", "^\$"),
		]
		t9_jumps = [
			MIPSInstruction("jalr", "\$t9"),
			MIPSInstruction("jr", "\$t9"),
		]
		ra_controls = [
			MIPSInstruction("lw", "\$ra"),
		]
		ra_jumps = [
			# TODO: Search for jumps to registers other than $ra.
			MIPSInstruction("jr", "\$ra"),
		]
		t9_musnt_clobber = ["$t9"]
		ra_musnt_clobber = ["$ra"]

		for possible_control_instruction in t9_controls+ra_controls:
			ea = start_ea
			found = 0

			if possible_control_instruction in t9_controls:
				jumps = t9_jumps
				musnt_clobber = t9_musnt_clobber
			else:
				jumps = ra_jumps
				musnt_clobber = ra_musnt_clobber

			while ea <= end_ea:

				ea = self._find_next_instruction_ea(ea, possible_control_instruction, end_ea, regex=True)
				if ea != idc.BADADDR:
					ins_size = idaapi.decode_insn(ea)

					control_instruction = self._get_instruction(ea)
					control_register = control_instruction.operands[1]
					
					if control_register:
						for jump in jumps:
							jump_ea = self._find_next_instruction_ea(ea+ins_size, jump, end_ea, no_baddies=True, regex=True, dont_overwrite=musnt_clobber)
							if jump_ea != idc.BADADDR:
								jump_instruction = self._get_instruction(jump_ea)
								controllable_jumps.append(ROPGadget(control_instruction, jump_instruction, description="Controllable Jump"))
								ea = jump_ea
					
					ea += ins_size

		return controllable_jumps

	def _find_system_calls(self, start_ea, end_ea):
		system_calls = []
		system_load = MIPSInstruction("la", "$t9", "system")
		stack_arg_zero = MIPSInstruction("addiu", "$a0", "$sp")

		for xref in idautils.XrefsTo(idc.LocByName('system')):
			ea = xref.frm
			if ea >= start_ea and ea <= end_ea and idc.GetMnem(ea)[0] in ['j', 'b']:
				a0_ea = self._find_next_instruction_ea(ea+self.INSIZE, stack_arg_zero, ea+self.INSIZE)
				if a0_ea == idc.BADADDR:
					a0_ea = self._find_prev_instruction_ea(ea, stack_arg_zero, ea-(self.SEARCH_DEPTH*self.INSIZE))
				
				if a0_ea != idc.BADADDR:
					control_ea = self._find_prev_instruction_ea(ea-self.INSIZE, system_load, ea-(self.SEARCH_DEPTH*self.INSIZE))
					if control_ea != idc.BADADDR:
						system_calls.append(ROPGadget(self._get_instruction(control_ea), self._get_instruction(ea), self._get_instruction(a0_ea), description="System call"))

				ea += self.INSIZE
			else:
				break

		return system_calls

	def _find_double_jumps(self, start_ea, end_ea):
		double_jumps = []
		
		for i in range(0, len(self.controllable_jumps)):
			g1 = self.controllable_jumps[i]
			if g1.exit.mnem != 'jalr':
				continue

			for j in range(i+1, len(self.controllable_jumps)):
				g2 = self.controllable_jumps[j]
				distance = (g2.entry.ea - g1.exit.ea)

				if distance > 0 and distance <= (self.SEARCH_DEPTH * self.INSIZE):
					if g1.control.register != g2.control.register:
						if not self._contains_bad_instruction(g1.exit.ea+self.INSIZE, g2.control.ea-self.INSIZE, no_clobber=[g2.control.register]):
							double_jumps.append(g1)
							break

		return double_jumps

	def _find_rop_gadgets(self, gadget):
		gadget_list = []

		for controllable_jump in self.controllable_jumps:
			gadget_ea = idc.BADADDR

			ea = self._find_next_instruction_ea(controllable_jump.entry.ea, gadget, controllable_jump.exit.ea+self.INSIZE, regex=True)
			if ea != idc.BADADDR:
				gadget_ea = ea
			else:
				ea = self._find_prev_instruction_ea(controllable_jump.entry.ea, gadget, controllable_jump.entry.ea-(self.SEARCH_DEPTH*self.INSIZE), no_baddies=True, regex=True, dont_overwrite=[controllable_jump.entry.opnd1])
				if ea != idc.BADADDR:
					gadget_ea = ea
		
			if gadget_ea != idc.BADADDR:
				gadget_list.append(ROPGadget(controllable_jump.entry, controllable_jump.exit, self._get_instruction(gadget_ea)))

		return gadget_list

	def _print_gadgets(self, gadgets):
		if gadgets:
			print gadgets[0].header()

		for gadget in gadgets:
			print str(gadget)

		if gadgets:
			print gadgets[0].footer()
		
		print "Found %d matching gadgets" % (len(gadgets))

	def _get_marked_gadgets(self):
		rop_gadgets = {}

		for i in range(1, 1024):
			marked_pos = idc.GetMarkedPos(i)
			if marked_pos != idc.BADADDR:
				marked_comment = idc.GetMarkComment(i)
				if marked_comment and marked_comment.lower().startswith("rop"):
					rop_gadgets[marked_comment] = marked_pos
			else:
				break

		return rop_gadgets

	def double(self):
		self.doubles()

	def doubles(self):
		'''
		Prints a list of all "double jump" gadgets (useful for function calls).
		'''
		self._print_gadgets(self.double_jumps)

	def stackfinder(self):
		self.stackfinders()

	def stackfinders(self):
		'''
		Prints a list of all gadgets that put a stack address into a register.
		'''
		self.find("addiu .*, $sp")

	def lia0(self):
		'''
		Prints a list of all gadgets that load an immediate value number into $a0 (useful for setting up the argument to sleep).
		'''
		self.find("li $a0")

	def tail(self):
		return self.tails()

	def tails(self):
		'''
		Prints a lits of all tail call gadgets (useful for function calls).
		'''
		return self.iret()

	def iret(self):
		'''
		Prints a lits of all tail gadgets (useful for function calls).
		'''
		tail_gadgets = []

		for gadget in self._find_rop_gadgets(MIPSInstruction("move", "\$t9")):
			if gadget.exit.mnem == 'jr' and gadget.exit.register == '$t9':
				tail_gadgets.append(gadget)

		self._print_gadgets(tail_gadgets)

	def system(self):
		'''
		Prints a list of gadgets that may be used to call system().
		'''
		sys_gadgets = self.system_calls + self._find_rop_gadgets(MIPSInstruction("addiu", "\$a0", "\$sp"))
		self._print_gadgets(sys_gadgets)

	def find(self, instruction_string=""):
		'''
		Locates all potential ROP gadgets that contain the specified instruction.

		@instruction_string - The instruction you need executed. This can be either a:

					o Full instruction    - "li $a0, 1"
					o Partial instruction - "li $a0"
					o Regex instruction   - "li $a0, .*"
		'''
		registers = ['$v', '$s', '$a', '$t', '$k', '$pc', '$fp', '$ra', '$gp', '$at', '$zero']

		comma_split = instruction_string.split(',')
		instruction_parts = comma_split[0].split()
		if len(comma_split) > 1:
			instruction_parts += comma_split[1:]

		for i in range(0, 4):
			if i > len(instruction_parts) - 1:
				instruction_parts.append(None)
			else:
				instruction_parts[i] = instruction_parts[i].strip().strip(',').strip()
				for reg in registers:
					instruction_parts[i] = instruction_parts[i].replace(reg, "\\%s" % reg)

		instruction = MIPSInstruction(instruction_parts[0], instruction_parts[1], instruction_parts[2], instruction_parts[3])
		gadgets = self._find_rop_gadgets(instruction)
		if gadgets:
			self._print_gadgets(gadgets)
		else:
			print "No ROP gadgets found!"

	def summary(self):
		'''
		Prints a summary of your currently marked ROP gadgets, in alphabetical order by the marked name.
		To mark a location as a ROP gadget, simply mark the position in IDA (Alt+M) with any name that starts with "ROP".
		'''
		rop_gadgets = self._get_marked_gadgets()
		summaries = []
		delim_char = "-"
		headings = {
			'name' 		: "Gadget Name",
			'offset'	: "Gadget Offset",
			'summary'	: "Gadget Summary"
		}
		lengths = {
			'name'		: len(headings['name']),
			'offset'	: len(headings['offset']),
			'summary'	: len(headings['summary']),
		}
		total_length = (3 * len(headings)) + 1

		if rop_gadgets:
			gadget_keys = rop_gadgets.keys()
			gadget_keys.sort()

			for marked_comment in gadget_keys:
				if len(marked_comment) > lengths['name']:
					lengths['name'] = len(marked_comment)

				summary = []
				ea = rop_gadgets[marked_comment]
				end_ea = ea + (self.SEARCH_DEPTH * self.INSIZE)

				while ea <= end_ea:
					summary.append(idc.GetDisasm(ea))
					mnem = idc.GetMnem(ea)
					if mnem[0].lower() in ['j', 'b']:
						summary.append(idc.GetDisasm(ea+self.INSIZE))
						break

					ea += self.INSIZE

				if len(summary) == 0:
					summary.append('')

				for line in summary:
					if len(line) > lengths['summary']:
						lengths['summary'] = len(line)

				summaries.append(summary)

			for (heading, size) in lengths.iteritems():
				total_length += size

			delim = delim_char * total_length
			line_fmt = "| %%-%ds | %%-%ds | %%-%ds |" % (lengths['name'], lengths['offset'], lengths['summary'])

			print delim
			print line_fmt % (headings['name'], headings['offset'], headings['summary'])
			print delim
			
			for i in range(0, len(gadget_keys)):
				line_count = 0
				marked_comment = gadget_keys[i]
				offset = "0x%.8X" % rop_gadgets[marked_comment]
				summary = summaries[i]
				
				for line in summary:
					if line_count == 0:
						print line_fmt % (marked_comment, offset, line)
					else:
						print line_fmt % ('', '', line)

					line_count += 1

				print delim

	def build(self):
		'''
		WIP.
		'''
		gadgets = self._get_marked_gadgets()
		bc = BowcasterBuilder(gadgets)
		bc.build_code()

	def help(self):
		'''
		Show help info.
		'''
		delim = "---------------------------------------------------------------------" * 2
		
		print ""
		print "mipsrop.find(instruction_string)"
		print delim
		print self.find.__doc__

		print ""
		print "mipsrop.system()"
		print delim
		print self.system.__doc__

		print ""
		print "mipsrop.doubles()"
		print delim
		print self.doubles.__doc__

		print ""
		print "mipsrop.stackfinders()"
		print delim
		print self.stackfinders.__doc__

		print ""
		print "mipsrop.tails()"
		print delim
		print self.tails.__doc__

		print ""
		print "mipsrop.summary()"
		print delim
		print self.summary.__doc__


class mipsropfinder_t(idaapi.plugin_t):
	flags = 0
	comment = "MIPS ROP Finder"
	help = ""
	wanted_name = "MIPS ROP Finder"
	wanted_hotkey = ""

	def init(self):
		self.menu_context = idaapi.add_menu_item("Search/", "mips rop gadgets", "Alt-1", 0, self.run, (None,))
		return idaapi.PLUGIN_KEEP

	def term(self):
		idaapi.del_menu_item(self.menu_context)
		return None

	def run(self, arg):
		global mipsrop
		mipsrop = MIPSROPFinder()
                
def PLUGIN_ENTRY():
        return mipsropfinder_t()

# DEBUG
#if __name__ == '__main__':
#	mipsrop = MIPSROPFinder()


########NEW FILE########
__FILENAME__ = idapathfinder
import idc
import idaapi
import idautils
import pathfinder
import time

class idapathfinder_t(idaapi.plugin_t):

    flags = 0
    comment = ''
    help = ''
    wanted_name = 'PathFinder'
    wanted_hotkey = ''

    def init(self):
        ui_path = "View/Graphs/"
        self.menu_contexts = []
        self.graph = None

        #self.menu_contexts.append(idaapi.add_menu_item(ui_path,
        #                        "Find code paths to the current function block",
        #                        "Alt-7",
        #                        0,
        #                        self.FindBlockPaths,
        #                        (None,)))
        self.menu_contexts.append(idaapi.add_menu_item(ui_path,
                                "Find function path(s) to here",
                                "Alt-6",
                                0,
                                self.FindPathsFromMany,
                                (None,)))
        #self.menu_contexts.append(idaapi.add_menu_item(ui_path,
        #                        "Find paths to here from a single function",
        #                        "Alt-7",
        #                        0,
        #                        self.FindPathsFromSingle,
        #                        (None,)))
        self.menu_contexts.append(idaapi.add_menu_item(ui_path, 
                                "Find function path(s) from here", 
                                "Alt-5", 
                                0, 
                                self.FindPathsToMany, 
                                (None,)))
        #self.menu_contexts.append(idaapi.add_menu_item(ui_path, 
        #                        "Find paths from here to a single function", 
        #                        "Alt-5", 
        #                        0, 
        #                        self.FindPathsToSingle, 
        #                        (None,)))
        self.menu_contexts.append(idaapi.add_menu_item(ui_path,
                                  "Find paths to the current function block",
                                  "Alt-7",
                                  0,
                                  self.FindBlockPaths,
                                  (None,)))
        
        return idaapi.PLUGIN_KEEP

    def term(self):
        for context in self.menu_contexts:
            idaapi.del_menu_item(context)
        return None
    
    def run(self, arg):
        self.FindPathsToSingle()

    def _current_function(self):
        return idaapi.get_func(ScreenEA()).startEA

    def _find_and_plot_paths(self, sources, targets, pfc=pathfinder.FunctionPathFinder):
        results = []

        for target in targets:
            pf = pfc(target)
            for source in sources:
                s = time.time()
                r = pf.paths_from(source)
                e = time.time()
                #print "paths_from took %f seconds." % (e-s)

                if r:
                    results += r
                else:
                    name = idc.Name(target)
                    if not name:
                        name = "0x%X" % target
                    print "No paths found to", name

        if results:
            # Be sure to close any previous graph before creating a new one.
            # Failure to do so may crash IDA.
            try:
                self.graph.Close()
            except:
                pass

            self.graph = pathfinder.PathFinderGraph(results, 'Path Graph')
            self.graph.Show()

    def _get_user_selected_functions(self, many=False):
        functions = []
        ea = idc.ScreenEA()
        try:
            current_function = idc.GetFunctionAttr(ea, idc.FUNCATTR_START)
        except:
            current_function = None

        while True:
            function = idc.ChooseFunction("Select a function and click 'OK' until all functions have been selected. When finished, click 'Cancel' to display the graph.")
            # ChooseFunction automatically jumps to the selected function
            # if the enter key is pressed instead of clicking 'OK'. Annoying.
            if idc.ScreenEA() != ea:
                idc.Jump(ea)

            if not function or function == idc.BADADDR or function == current_function:
                break
            elif function not in functions:
                functions.append(function)

            if not many:
                break

        return functions
            
    def FindPathsToSingle(self, arg):
        source = self._current_function()

        if source:
            targets = self._get_user_selected_functions()
            if targets:
                print source, targets
                self._find_and_plot_paths([source], targets)

    def FindPathsToMany(self, arg):
        source = self._current_function()

        if source:
            targets = self._get_user_selected_functions(many=True)
            if targets:
                self._find_and_plot_paths([source], targets)

    def FindPathsFromSingle(self, arg):
        target = self._current_function()

        if target:
            sources = self._get_user_selected_functions()
            if sources:
                self._find_and_plot_paths(sources, [target])

    def FindPathsFromMany(self, arg):
        target = self._current_function()

        if target:
            sources = self._get_user_selected_functions(many=True)
            if sources:
                self._find_and_plot_paths(sources, [target])

    def FindBlockPaths(self, arg):
        target = idc.ScreenEA()
        source = idaapi.get_func(idc.ScreenEA())

        if source:
            self._find_and_plot_paths([source.startEA], [target], pfc=pathfinder.BlockPathFinder)
        else:
            print "Block graph error: The location must be part of a function!"

def PLUGIN_ENTRY():
    return idapathfinder_t()

########NEW FILE########
__FILENAME__ = install
#!/usr/bin/env python
# Simple installer script to drop the files where they need to be.

import sys
import shutil
import os.path

try:
	ida_dir = sys.argv[1]
except:
	print "Usage: %s <path to IDA install directory>" % sys.argv[0]
	sys.exit(1)

if os.path.exists(ida_dir):
	shutil.copyfile('pathfinder.py', os.path.join(ida_dir, 'python', 'pathfinder.py'))
	shutil.copyfile('idapathfinder.py', os.path.join(ida_dir, 'plugins', 'idapathfinder.py'))
	print "PathFinder installed to '%s'." % ida_dir
else:
	print "Install failed, '%s' does not exist!" % ida_dir
	sys.exit(1)

########NEW FILE########
__FILENAME__ = pathfinder
import idc
import idaapi
import idautils
import time

class History(object):
    '''
    Manages include/exclude graph history.
    '''

    INCLUDE_ACTION = 0
    EXCLUDE_ACTION = 1

    def __init__(self):
        self.reset()

    def reset(self):
        self.history = []
        self.includes = []
        self.excludes = []
        self.history_index = 0
        self.include_index = 0
        self.exclude_index = 0

    def update_history(self, action):
        if self.excludes and len(self.history)-1 != self.history_index:
            self.history = self.history[0:self.history_index+1]
        self.history.append(action)
        self.history_index = len(self.history)-1

    def add_include(self, obj):
        if self.includes and len(self.includes)-1 != self.include_index:
            self.includes = self.includes[0:self.include_index+1]
        self.includes.append(obj)
        self.include_index = len(self.includes)-1
        self.update_history(self.INCLUDE_ACTION)

    def add_exclude(self, obj):
        if len(self.excludes)-1 != self.exclude_index:
            self.excludes = self.excludes[0:self.exclude_index+1]
        self.excludes.append(obj)
        self.exclude_index  = len(self.excludes)-1
        self.update_history(self.EXCLUDE_ACTION)

    def get_includes(self):
        return set(self.includes[0:self.include_index+1])

    def get_excludes(self):
        return set(self.excludes[0:self.exclude_index+1])

    def undo(self):
        if self.history:
            if self.history[self.history_index] == self.INCLUDE_ACTION:
                if self.include_index >= 0:
                    self.include_index -= 1
            elif self.history[self.history_index] == self.EXCLUDE_ACTION:
                if self.exclude_index >= 0:
                    self.exclude_index -= 1

            self.history_index -= 1
            if self.history_index < 0:
                self.history_index = 0

    def redo(self):
        self.history_index += 1
        if self.history_index >= len(self.history):
            self.history_index = len(self.history)-1

        if self.history[self.history_index] == self.INCLUDE_ACTION:
            if self.include_index < len(self.includes)-1:
                self.include_index += 1
        elif self.history[self.history_index] == self.EXCLUDE_ACTION:
            if self.exclude_index < len(self.excludes)-1:
                self.exclude_index += 1

class PathFinderGraph(idaapi.GraphViewer):
    '''
    Displays the graph and manages graph actions.
    '''

    def __init__(self, results, title="PathFinder Graph"):
        idaapi.GraphViewer.__init__(self, title)
        self.results = results

        self.nodes_ea2id = {}
        self.nodes_id2ea = {}
        self.edges = {}
        self.end_nodes = []
        self.edge_nodes = []
        self.start_nodes = []

        self.history = History()
        self.include_on_click = False
        self.exclude_on_click = False

    def Show(self):
        '''
        Display the graph.

        Returns True on success, False on failure.
        '''
        if not idaapi.GraphViewer.Show(self):
            return False
        else:
            self.cmd_undo = self.AddCommand("Undo", "U")
            self.cmd_redo = self.AddCommand("Redo", "R")
            self.cmd_reset = self.AddCommand("Reset graph", "G")
            self.cmd_exclude = self.AddCommand("Exclude node", "X")
            self.cmd_include = self.AddCommand("Include node", "I")
            return True

    def OnRefresh(self):
        # Clear the graph before refreshing
        self.Clear()
        self.nodes_ea2id = {}
        self.nodes_id2ea = {}
        self.edges = {}
        self.end_nodes = []
        self.edge_nodes = []
        self.start_nodes = []

        includes = self.history.get_includes()
        excludes = self.history.get_excludes()
        
        for path in self.results:
            parent_node = None

            # Check to see if this path contains all nodes marked for explicit inclusion
            if (set(path) & includes) != includes:
                continue

            # Check to see if this path contains any nodes marked for explicit exclusion
            if (set(path) & excludes) != set():
                continue

            for ea in path:
                # If this node already exists, use its existing node ID
                if self.nodes_ea2id.has_key(ea):
                    this_node = self.nodes_ea2id[ea]
                # Else, add this node to the graph
                else:
                    this_node = self.AddNode(self.get_name_by_ea(ea))
                    self.nodes_ea2id[ea] = this_node
                    self.nodes_id2ea[this_node] = ea

                # If there is a parent node, add an edge between the parent node and this one
                if parent_node is not None:
                    self.AddEdge(parent_node, this_node)
                    if this_node not in self.edges[parent_node]:
                        self.edges[parent_node].append(this_node)
                
                # Update the parent node for the next loop
                parent_node = this_node
                if not self.edges.has_key(parent_node):
                    self.edges[parent_node] = []

            try:
                # Track the first, last, and next to last nodes in each path for
                # proper colorization in self.OnGetText.
                self.start_nodes.append(self.nodes_ea2id[path[0]])
                self.end_nodes.append(self.nodes_ea2id[path[-1]])
                self.edge_nodes.append(self.nodes_ea2id[path[-2]])
            except:
                pass

        return True

    def OnGetText(self, node_id):
        color = idc.DEFCOLOR

        if node_id in self.edge_nodes:
            color = 0x00ffff
        elif node_id in self.start_nodes:
            color = 0x00ff00
        elif node_id in self.end_nodes:
            color = 0x0000ff

        return (self[node_id], color)

    def OnHint(self, node_id):
        hint = ""

        try:
            for edge_node in self.edges[node_id]:
                hint += "%s\n" % self[edge_node]
        except Exception as e:
            pass

        return hint

    def OnCommand(self, cmd_id):
        if self.cmd_undo == cmd_id:
            if self.include_on_click or self.exclude_on_click:
                self.include_on_click = False
                self.exclude_on_click = False
            else:
                self.history.undo()
            self.Refresh()
        elif self.cmd_redo == cmd_id:
            self.history.redo()
            self.Refresh()
        elif self.cmd_include == cmd_id:
            self.include_on_click = True
        elif self.cmd_exclude == cmd_id:
            self.exclude_on_click = True
        elif self.cmd_reset == cmd_id:
            self.include_on_click = False
            self.exclude_on_click = False
            self.history.reset()
            self.Refresh()

    def OnClick(self, node_id):
        if self.include_on_click:
            self.history.add_include(self.nodes_id2ea[node_id])
            self.include_on_click = False
        elif self.exclude_on_click:
            self.history.add_exclude(self.nodes_id2ea[node_id])
            self.exclude_on_click = False
        self.Refresh()

    def OnDblClick(self, node_id):
        xref_locations = []
        node_ea = self.get_ea_by_name(self[node_id])

        if self.edges.has_key(node_id):
            for edge_node_id in self.edges[node_id]:

                edge_node_name = self[edge_node_id]
                edge_node_ea = self.get_ea_by_name(edge_node_name)

                if edge_node_ea != idc.BADADDR:
                    for xref in idautils.XrefsTo(edge_node_ea):
                        # Is the specified node_id the source of this xref?
                        if self.match_xref_source(xref, node_ea):
                            xref_locations.append((xref.frm, edge_node_ea))

        if xref_locations:
            xref_locations.sort()

            print ""
            print "Path Xrefs from %s:" % self[node_id]
            print "-" * 100
            for (xref_ea, dst_ea) in xref_locations:
                print "%-50s  =>  %s" % (self.get_name_by_ea(xref_ea), self.get_name_by_ea(dst_ea))
            print "-" * 100
            print ""
            
            idc.Jump(xref_locations[0][0])
        else:
            idc.Jump(node_ea)

    def match_xref_source(self, xref, source):
        # TODO: This must be modified if support for graphing function blocks is added.
        return ((xref.type != idc.fl_F) and (idc.GetFunctionAttr(xref.frm, idc.FUNCATTR_START) == source))

    def get_ea_by_name(self, name):
        '''
        Get the address of a location by name.

        @name - Location name

        Returns the address of the named location, or idc.BADADDR on failure.
        '''
        # This allows support of the function offset style names (e.g., main+0C)
        # TODO: Is there something in the IDA API that does this already??
        if '+' in name:
            (func_name, offset) = name.split('+')
            base_ea = idc.LocByName(func_name)
            if base_ea != idc.BADADDR:
                try:
                    ea = base_ea + int(offset, 16)
                except:
                    ea = idc.BADADDR
        else:
            ea = idc.LocByName(name)
            if ea == idc.BADADDR:
                try:
                    ea = int(name, 0)
                except:
                    ea = idc.BADADDR

        return ea

    def get_name_by_ea(self, ea):
        '''
        Get the name of the specified address.

        @ea - Address.

        Returns a name for the address, one of idc.Name, idc.GetFuncOffset or 0xXXXXXXXX.
        '''
        name = idc.Name(ea)
        if not name:
            name = idc.GetFuncOffset(ea)
            if not name:
                name = "0x%X" % ea
        return name

class PathFinder(object):
    '''
    Base class for finding the path between two addresses.
    '''

    # Limit the max recursion depth
    MAX_DEPTH = 500

    def __init__(self, destination):
        '''
        Class constructor.

        @destination - The end node ea.

        Returns None.
        '''
        self.tree = {}
        self.nodes = {}
        self.depth = 0
        self.last_depth = 0
        self.full_paths = []
        self.current_path = []
        self.destination = self._name2ea(destination)
        self.build_call_tree(self.destination)

    def __enter__(self):
        return self
        
    def __exit__(self, t, v, traceback):
        return

    def _name2ea(self, nea):
        if isinstance(nea, type('')):
            return idc.LocByName(nea)
        return nea

    def paths_from(self, source, exclude=[], include=[], xrefs=[], noxrefs=[]):
        '''
        Find paths from a source node to a destination node.

        @source  - The source node ea to start the search from.
        @exclude - A list of ea's to exclude from paths.
        @include - A list of ea's to include in paths.
        @xrefs   - A list of ea's that must be referenced from at least one of the path nodes.
        @noxrefs - A list of ea's that must not be referenced from any of the path nodes.

        Returns a list of path lists.
        '''
        paths = []
        good_xrefs = []
        bad_xrefs = []

        source = self._name2ea(source)

        # If all the paths from the destination node have not already
        # been calculated, find them first before doing anything else.
        if not self.full_paths:
            s = time.time()
            self.find_paths(self.destination, source)
            e = time.time()

        for xref in xrefs:
            xref = self._name2ea(xref)

            for x in idautils.XrefsTo(xref):
                f = idaapi.get_func(x.frm)
                if f:
                    good_xrefs.append(f.startEA)

        for xref in noxrefs:
            bad_xrefs.append(self._name2ea(xref))
            xref = self._name2ea(xref)

            for x in idautils.XrefsTo(xref):
                f = idaapi.get_func(x.frm)
                if f:
                    bad_xrefs.append(f.startEA)

        for p in self.full_paths:
            try:
                index = p.index(source)

                if exclude:
                    for ex in excludes:
                        if ex in p:
                            index = -1
                            break
                
                if include:
                    orig_index = index
                    index = -1

                    for inc in include:
                        if inc in p:
                            index = orig_index
                            break

                if good_xrefs:
                    orig_index = index
                    index = -1
                    
                    for xref in good_xrefs:
                        if xref in p:
                            index = orig_index

                    if index == -1:
                        print "Sorry, couldn't find", good_xrefs, "in", p

                if bad_xrefs:
                    for xref in bad_xrefs:
                        if xref in p:
                            index = -1
                            break

                # Be sure to include the destinatin and source nodes in the final path
                p = [self.destination] + p[:index+1]
                # The path is in reverse order (destination -> source), so flip it
                p = p[::-1]
                # Ignore any potential duplicate paths
                if p not in paths:
                    paths.append(p)
            except:
                pass

        return paths

    def find_paths(self, ea, source=None, i=0):
        '''
        Performs a depth-first (aka, recursive) search to determine all possible call paths originating from the specified location.
        Called internally by self.paths_from.

        @ea - The start node to find a path from.
        @i  - Used to specify the recursion depth; for internal use only.

        Returns None.
        '''
        # Increment recursion depth counter by 1
        i += 1
        # Get the current call graph depth
        this_depth = self.depth

        # If this is the first level of recursion and the call
        # tree has not been built, then build it.
        if i == 1 and not self.tree:
            self.build_call_tree(ea)

        # Don't recurse past MAX_DEPTH    
        if i >= self.MAX_DEPTH:
            return

        # Loop through all the nodes in the call tree, starting at the specified location
        for (reference, children) in self.nodes[ea].iteritems():
            # Does this node have a reference that isn't already listed in our current call path?
            if reference and reference not in self.current_path:
                    # Increase the call depth by 1
                    self.depth += 1
                    # Add the reference to the current path
                    self.current_path.append(reference)
                    # Find all paths from this new reference
                    self.find_paths(reference, source, i)

        # If we didn't find any additional references to append to the current call path (i.e., this_depth == call depth)
        # then we have reached the limit of this call path.
        if self.depth == this_depth:
            # If the current call depth is not the same as the last recursive call, and if our list of paths
            # does not already contain the current path, then append a copy of the current path to the list of paths
            if self.last_depth != self.depth and self.current_path and self.current_path not in self.full_paths:
                self.full_paths.append(list(self.current_path))
            # Decrement the call path depth by 1 and pop the latest node out of the current call path
            self.depth -= 1
            if self.current_path:
                self.current_path.pop(-1)

        # Track the last call depth
        self.last_depth = self.depth    

    def build_call_tree(self, ea):
        '''
        Performs a breadth first (aka, iterative) search to build a call tree to the specified address.

        @ea - The node to generate a tree for.

        Returns None.
        '''
        self.tree[ea] = {}
        self.nodes[ea] = self.tree[ea]
        nodes = [ea]

        while nodes:
            new_nodes = []

            for node in nodes:
                if node and node != idc.BADADDR:
                    node_ptr = self.nodes[node]

                    for reference in self.node_xrefs(node):
                        if reference not in self.nodes:
                            node_ptr[reference] = {}
                            self.nodes[reference] = node_ptr[reference]
                            new_nodes.append(reference)
                        elif not node_ptr.has_key(reference):
                            node_ptr[reference] = self.nodes[reference]
            
            nodes = new_nodes

    def node_xrefs(self, node):
        '''
        This must be overidden by a subclass to provide a list of xrefs.

        @node - The EA of the node that we need xrefs for.

        Returns a list of xrefs to the specified node.
        '''
        return []

class FunctionPathFinder(PathFinder):
    '''
    Subclass to generate paths between functions.
    '''

    def __init__(self, destination):
        # IDA 6.4 needs the extra import here, else idaapi is type None
        import idaapi
        func = idaapi.get_func(self._name2ea(destination))
        super(FunctionPathFinder, self).__init__(func.startEA)

    def node_xrefs(self, node):
        '''
        Return a list of function EA's that reference the given node.
        '''
        xrefs = []

        for x in idautils.XrefsTo(node):
            if x.type != idaapi.fl_F:
                f = idaapi.get_func(x.frm)
                if f and f.startEA not in xrefs:
                    xrefs.append(f.startEA)
        return xrefs
    
class BlockPathFinder(PathFinder):
    '''
    Subclass to generate paths between code blocks inside a function.
    '''

    def __init__(self, destination):
        func = idaapi.get_func(destination)
        self.blocks = idaapi.FlowChart(f=func)
        self.block_table = {}

        for block in self.blocks:
            self.block_table[block.startEA] = block
            self.block_table[block.endEA] = block

        self.source_ea = func.startEA
        dst_block = self.LookupBlock(destination)

        if dst_block:
            super(BlockPathFinder, self).__init__(dst_block.startEA)

    def LookupBlock(self, ea):
        try:
            return self.block_table[ea]
        except:
            for block in self.blocks:
                if ea >= block.startEA and ea < block.endEA:
                    return block
        return None
        
    def node_xrefs(self, node):
        '''
        Return a list of blocks that reference the provided block.
        '''
        xrefs = []

        block = self.LookupBlock(node)
        if block:
            for xref in idautils.XrefsTo(block.startEA):
                xref_block = self.LookupBlock(xref.frm)
                if xref_block and xref_block.startEA not in xrefs:
                    xrefs.append(xref_block.startEA)

        return xrefs

class Find(object):

    def __init__(self, start=[], end=[], include=[], exclude=[], xrefs=[], noxrefs=[]):
        self.start = self._obj2list(start)
        self.end = self._obj2list(end)
        self.include = self._obj2list(include)
        self.exclude = self._obj2list(exclude)
        self.xrefs = self._obj2list(xrefs)
        self.noxrefs = self._obj2list(noxrefs)

        if len(self.start) > 0:
            first_ea = self._obj2ea(self.start[0])
            func = idaapi.get_func(self.start[0])
            if func:
                results = []

                end_func = idaapi.get_func(self.end[0])
                if end_func and end_func.startEA == self.end[0]:
                    pfclass = FunctionPathFinder
                else:
                    pfclass = BlockPathFinder
                print pfclass
                
                for destination in self.end:
                    pf = pfclass(destination)
                    for source in self.start:
                        results += pf.paths_from(source, exclude=self.exclude, include=self.include, xrefs=self.xrefs, noxrefs=self.noxrefs)
                    del pf

                print "RESULTS:", results
                if results:
                    pg = PathFinderGraph(results)
                    pg.Show()
                    del pg

    def _obj2list(self, obj):
        '''
        Converts the supplied object to a list, if it is not already a list.

        @obj - The object.
    
        Returns a list.
        '''
        l = []

        if not isinstance(obj, type([])):
            l.append(self._obj2ea(obj))
        else:
            for o in obj:
                l.append(self._obj2ea(o))
        return l

    def _obj2ea(self, ea):
        if isinstance(ea, type('')):
            return idc.LocByName(ea)
        return ea

#if __name__ == "__main__":
    #Find(['main'], ['strcpy'])
    #Find('execute_other_requests', 'loc_408E80')


########NEW FILE########
