__FILENAME__ = cat
# TODO check include/define dependencies

import sys
import argparse
import traceback

def main(argv):
    
    stdout_lock = {}
    
    # TODO process config
    # setprogramname(argv[0])
    # setlocale(LC_ALL, '')
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-b',action='store_true',
                        help='number nonblank output lines')
    parser.add_argument('-e',action='store_true',
                        help='-e implies -v')
    parser.add_argument('-f',action='store_true',
                        help='?..')
    parser.add_argument('-l',action='store_true',
                        help='?..')
    parser.add_argument('-n',action='store_true',
                        help='number all output lines')
    parser.add_argument('-s',action='store_true',
                        help='never more than one single blank line')
    parser.add_argument('-t',action='store_true',
                        help='-t implies -v')
    parser.add_argument('-v',action='store_true',
                        help='use ^ and M- notation, except for LFD and TAB')
    parser.add_argument('files', nargs=argparse.REMAINDER)
    
    argv = parser.parse_args()
    
    if argv.b:
        argv.n = True
    
    if argv.e:
        argv.v = True
        
    if argv.t:
        argv.v = True
        
        
    if not argv.files or (len(argv.files) == 1 and '-' in argv.files):
        try:
            # Behaves like CAT without files #
            while True:
                stdin_aux = input()
                print(stdin_aux)
        except KeyboardInterrupt:
            # Hide traceback from end-user # 
            print()
            traceback.format_exc()

    # Prints files passed #
    
    elif len(argv.files) > 0:
        try:
            for i in argv.files:
                with open(i, 'r') as j:
                    if argv.n:
                        xline = 1
                        if argv.b:
                            for line in j.readlines(): 
                                if line.strip():
                                    fline = '{} {}'.format(xline,line)
                                    print(fline,end='')
                                xline += 1
                        else:
                            for line in j.readlines(): 
                                fline = '{} {}'.format(xline,line)
                                print(fline,end='')
                                xline += 1
                    else:
                        for line in j.readlines(): 
                            print(line,end='')
                print('')                          
                        
        except IOError:
            traceback.format_exc()

            
if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = echo
# Echo program, print stuffs in stdout
import sys

def main(argv):
  
    # TODO Find and implement setprogname,setlocale, probably in process part
    # check <sys.cdefs.h>
  
    # setprogname(argv[0])
    # setlocale(LC_ALL, '')
    
    if len(argv) < 2:
         print("usage: echo [-n] [text ...]")     
         exit(0)
         
    if argv[1] == '-n':
        nflag = 1
        end = ''
    else:
        nflag = 0
        end = '\n'
  
    try:
        print(' '.join(argv[nflag+1:]),end=end)
    except IOError:
        exit(1)
        
    exit(0)


if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = pwd
# PWD - Print Working Directory - prints global path to current directory
# TODO: Remove use of 'os' module
import os

print(os.getcwd())

########NEW FILE########
__FILENAME__ = rm
# rm: simple program to delete files and directories
# TODO: Remove use of 'os' module

import sys
import os
import argparse

def remove(files, force=False, interactive=False, recursive=False):
    if recursive and interactive:
        for i in files:
            if os.path.isdir(i) and not i.endswith('/'):
                i += '/'
            if os.path.isfile(i):
                answer = input('rm: remove common file "{0}"? '.format(i))
                if answer.upper() == 'Y':
                    os.remove(i)
            elif os.path.isdir(i) and len(os.listdir(i)) > 0:
                answer = input('rm: descent into directory "{0}"? '.format(i))
                if answer.upper() == 'Y':
                    subdir = [''.join([i,x]) for x in os.listdir(i)]
                    remove(subdir, force=force,
                           interactive=interactive, recursive=recursive)
                    answer = input('rm: remove directory "{0}"? '.format(i))
                    if answer.upper() == 'Y':
                        os.rmdir(i)
            else:
                answer = input('rm: remove directory "{0}"? '.format(i))
                os.rmdir(i)
    elif recursive:
        for i in files:
            if os.path.isdir(i) and not i.endswith('/'):
                i += '/'
            if os.path.isfile(i):
                os.remove(i)
            elif os.path.isdir(i) and len(os.listdir(i)) > 0:
                subdir = [''.join([i,x]) for x in os.listdir(i)]
                remove(subdir, force=force,
                       interactive=interactive, recursive=recursive)
                os.rmdir(i)
            else:
                os.rmdir(i)

def main(argv):

    # Initialize parser #
    parser = argparse.ArgumentParser()

    # Add options #
    parser.add_argument('-i', action='store_true',
                        help='Ask for confirmation before removing')
    parser.add_argument('-f', action='store_true',
                        help='Do not ask for confirmation before\
                              removing')
    parser.add_argument('-r', action='store_true',
                        help='Remove recursively')
    # Same as -r #
    parser.add_argument('-R', action='store_true',
                        help='Remove recursively')

    parser.add_argument('files', nargs=argparse.REMAINDER)

    argv = parser.parse_args()

    # If -R is passed, then -r is set to True #
    if argv.R:
        argv.r = True


    if len(argv.files) == 0:
        print('Usage: rm [OPTIONS] FILES')

    remove(argv.files, force=argv.f, interactive=argv.i, recursive=argv.r)

if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = hboard
# TODO implement all the header

def get_board_id_by_name(name):
	for board in board_id2name:
		if board:
			return board
	return 0
########NEW FILE########
__FILENAME__ = hcom
GET_KINFO = 0
########NEW FILE########
__FILENAME__ = hconst
# TODO implement all library
class CONST():
	BOARDVARNAME = "board"
	def __init__(self):
		pass
		
########NEW FILE########
__FILENAME__ = hsyslib
#TODO implement all the library
def sys_getinfo(request, val_ptr,val_len,val_ptr2,val_len2):
	# TODO check syscall implementation
	pass

def sys_getkinfo(dst):
	sys_getinfo(GET_KINFO,dst,0,0,0)
########NEW FILE########
__FILENAME__ = cpulocals
class Cpulocals:
    # TODO Check SMP override
    def get_cpu_var(self, name, cpu=0):
        return CPULOCAL_STRUCT[cpu][name]

    def get_cpulocal_var(self, name):
        # TODO  check how cpuid is created
        return get_cpu_var(name, cpuid)

    # MXCM #
    # FIXME - padd the structure so that items in the array do not share
    # cacheline with other CPUS
########NEW FILE########
__FILENAME__ = hglo
# MXCM #
'''	Global variables used in the kernel. This file contains the declarations;
 	storage space for the variables is allocated in table.c, because EXTERN is
 	defined as extern unless the _TABLE definition is seen. We rely on the 
 	compiler's default initialization (0) for several global variables. '''

# TODO check imports
# TODO chech all extern definitions are ini'ed in another place

# Kernel Information Structures
class Global():
	kinfo = {} # Kenel info for users
	machine = {} # machine info for users
	kmessages = {} # diagnostic msgs in kernel
	loadinfo = {} # status of load average
	minix_kerninfo = {}
	# TODO check extern =/= EXTERN
	krandom = {} # gather kernel random info WTF ?!
	# TODO check vir_bytes
	minix_kerninfo_user = {}

	# TODO check necessity for binding and remove later
	kmess = kmessages
	kloadinfo = loadinfo

	# Process scheduling information and kernel reentry count
	vmrequest = {} # first process on vmrequest queue
	lost_ticks = 0	 # clock ticks counted outside clock task
	# TODO check ipc_call_names, global to anything
	# ipc_call_names[IPCNO_HIGHTEST+1] = '' # human-read call names
	kbill_kcall = {} # process that made kernel call
	kbill_ipc = {} # process that invoked ipc

	# Interrupt related variables
	# TODO check irq_hook	
	# irq_hook[NR_IRQ_HOOKS] = {} # hooks for general use
	# irq_actids[NR_IRQ_VECTORS] = 0 # IRQ ID bits active
	irq_use = 0 # map of all in-use irq's
	system_hz = 0 # HZ value TODO check u22_t type

	# Misc
	import time
	boottime = time.ctime() # TODO check ctime implementation
	verboseboot = 0 # verbose boot, init'ed in cstart

	# TODO Check globals constant
	DEBUG_TRACE = USE_APIC = 0
	DEBUG_TRACE
	if DEBUG_TRACE:
		verboseflags = 0

	if USE_APIC: 
		config_no_apic # extern
		config_apic_timer_x # extern

	# TODO check u64_t
	# cpu_hz[CONFIG_MAX_CPUS]
	def cpu_set_freq(cpu, freq):
		cpu_hz[pcu] = freq

	def cpu_get_freq(cpu):
		return cpu_hz[cpu]

	# TODO implement SMP flag
	# config_no_smp = 1

	# VM
	vm_running = 0
	catch_pagefaults = 0
	kernel_may_alloc = 0

	# TODO CHECK IMAGE ; Variables thar are init'ed elsewhere are just extern here
	# image[NR_BOOT_PROCS] = {} # system image process
	# TODO check how python implement volatile var
	serial_debug_active = 0
	# cpu_info[CONFIG_MAX_CPUS] = {}



	# BKL stats
	# TODO u64_t again, next 2 lines
	#kernel_ticks[CONFIG_MAX_CPUS] = 0
	#bkl_ticks[CONFIG_MAX_CPUS] = 0
	# TODO check Unsigned, 2 lines
	#bkl_tries[CONFIG_MAX_CPUS] = 0
	#bkl_succ[CONFIG_MAX_CPUS] = 0
########NEW FILE########
__FILENAME__ = main
''' This file contains the main program of PYTHONIX as well as its shutdown
    code. The routine main() initializes the system and starts the ball
    rolling by setting up the process table, interrupt vectors, and scheduling
    each task to run to initialize itself.
    The routine shutdown() does the opposite and brings down PYTHONIX.
    The entries into this file are:
    kmain: PYTHONIX main program
    prepare_shutdown:	prepare to take PYTHONIX down'''

# TODO check dependencies
import include.pythonix.hboard
import include.pythonix.hconst

def bsp_finish_booting():
    if SPOFILE:
        sprofiling = 0
    cprof_procs_no = 0

    cpu_identify()
    vm_running = 0
    # TODO check krandom struct
    krandom['random_sources'] = RANDOM_SOURCES
    krandom['random_elements'] = RANDOM_ELEMENTS

    # PYTHONIX is now ready. All boot image processes are on the ready queue.
    # Return to the assembly code to start running the current process.

    # TODO check WTF is this
    # get_cpulocal_var(proc_ptr) = get_cpulocal_var_ptr(idle_proc)
    # get_cpulocal_var(bill_ptr) = get_cpulocal_var_ptr(idle_proc)
    announce()

    # we have access to the cpu local run queue
    # only now schedule the processes.
    # We ignore the slots for the former kernel tasks
    for i in range(NR_BOOT_PROCS - NR_TASKS):
        RTS_UNSET(proc_addr(i), RTS_PROC_STOP)

    # enable timer interrupts and clock task on the boot CPU

    if(boot_cpu_init_timer(system_hz)):
        panic('''FATAL : failed to initialize timer interrupts,
                cannot continue without any clock source!''')

    fpu_init()

    # TODO check sanity checks
    '''
    if DEBUG_SCHED_CHECK:
        fixme("DEBUG_SCHED_CHECK enabled");

    if DEBUG_VMASSERT:
        fixme("DEBUG_VMASSERT enabled");

    if DEBUG_PROC_CHECK:
        fixme("PROC check enabled");
    '''

    debugextra('cycles_accounting_init()... ')
    cycles_accounting_init()
    debugextra('done')

    '''if CONFIG_SMP:
        cpu_set_flag(bsp_cpu_id, CPU_IS_READY)
        machine['processors_count'] = ncpus
        machine['bsp_id'] = bsp_cpu_id
    else:'''
    machine['processors_count'] = 1
    machine['bsp_id'] = 0

    kernel_may_alloc = 0

    switch_to_user()

# TODO Remove hard code cbi
def kmain(local_cbi={}):
    # TODO check if this is really necessary
    kernel.hglo.kinfo = local_cbi
    kmess = kinfo['kmess']

    machine['board_id'] =  include.pythonix.hboard.get_board_id_by_name(env_get(include.pythonix.hconst.CONST.BOARDVARNAME))

    if __arm__:
        arch_ser_init()

    # printing UP
    print('PYTHONIX booting')

    kernel_may_alloc = 1

    assert(len(kinfo['boot_procs'] == len(image)))
    kinfo['boot_procs'] = image

    cstart()
    BKL_LOCK()
    DEBUGEXTRA('main()')
    proc_init()

    if(NR_BOOT_MODULES != kinfo['mbi']['mods_count']):
        panic('expecting {} boot processes/modules, found {}'.format(
            NR_BOOT_MODULES, kinfo['mbi']['mods_count']))

    # Setting up proc table entries for proc in boot image
    for i in range(NR_BOOT_PROCS):
        ip = image[i]
        debugextra('initializing {}'.format(ip['proc_name']))
        rp = proc_addr(ip['proc_nr'])
        ip['endpoint'] = rp['p_endpoint']
        rp['p_cpu_time_left'] = 0
        if(i < NR_TASKS):
            rp['p_name'] = ip['proc_name']
        else:
            mb_mod = kinfo['module_list'][i - NR_TASKS]
            ip['start_addr'] = mb_mod['mod_start']
            # TODO check if this can be done with len()
            ip['len'] = mb_mod['mob_end'] - mb_mod['mb_start']

    reset_proc_accounting(rp)

    ''' See if this process is immediately schedulable.
    In that case, set its privileges now and allow it to run.
    Only kernel tasks and the root system process get to run immediately.
    All the other system processes are inhibited from running by the
    RTS_NO_PRIV flag. They can only be scheduled once the root system
    process has set their privileges.'''

    proc_nr = proc_nr(rp)
    
    schedulable_proc = iskernelln(proc_nr) or \
                        isrootsysn(proc_nr) or \
                        proc_nr == VM_PROC_NR

    if(schedulable_proc):
        get_priv(rp, static_priv_id(proc_nr))
        # Privileges for kernel tasks
        if(proc_nr == VM_PROC_NR):
            # TODO Check this priv(rp)
            # priv(rp)->s_flags = VM_F
            # priv(rp)->s_trap_mask = SRV_T
            # priv(rp)-> s_sig)mgr = SELF
            ipc_to_m = SRV_M
            kcall = SRV_KC
            rp['p_priority'] = SRV_Q
            rp['p_quantum_size_ms'] = SRV_QT
        elif(iskernelln(proc_nr)):
            # TODO Check this priv(rp)
            # priv(rp)->s_flags = (IDL_F if proc_nr == IDLE else TSK_F)
            # priv(rp)->s_trap_mask = CSK_T if proc_nr == CLOCK \
            #   proc_nr == SYSTEM else TSK_T
            ipc_to_m = TSK_M  # Allowed targets
            kcalls = TSK_KC  # Allowed kernel calls
        else:
            assert(isrootsysn(proc_nr))
            # TODO Check this priv(rp)
            # priv(rp)['sflags'] = RSYS_F       # priv flags
            # priv(rp)['s_trap_mask'] = SRV_T   # allowed traps
            ipc_to_m = SRV_M                    # allowed targets
            kcalls = SRV_KC                     # allowed kcalls
            # priv(rp)['s_sig_mgr'] = SRV_SM    # sign manager
            rp['p_priority'] = SRV_Q            # priority queue
            rp['p_quantum_size_ms'] = SRV_QT    # quantum size

        # TODO check the entire next block
        '''map = '0'*len(map)
        if(ipc_to_m == ALL_M):
            for j in range(NR_SYS_PROCS):
                set_sys_bit(map,j)

        fill_sendto_mask(rp,map)
        for j in range(SYS_CALL_MASK_SIZE):
            # WTF this line
            priv(rp)['s_k_call_mask']['j'] = 0 if kcall == NO_C else (~0)

        '''
    else:
        # Block process from running
        RTS_SET(rp, RTS_NO_PRIV | RTS_NO_QUANTUM)

    # Arch specific state initialization
    arch_boot_proc(ip, rp)

    # scheduing functions depend on proc_ptr pointing somewhere
    if not get_cpulocal_var(proc_ptr):
        # TODO Check SMP stuffs
        CPULOCAL_STRUCT[0][name] = rp

    # process isn't scheduled until VM has set up a pagetable for it
    if rp['p_nr'] != VM_PROC_NR and rp['p_nr'] >= 0:
        rp['p_rts_flags'] |= RTS_VMINHIBIT
        rp['p_rts_flags'] |= RTS_BOOTINHIBIT

    rp['p_rts_flags'] |= RTS_PROC_STOP
    rp['p_rts_flags'] &= ~RTS_SLOT_FREE
    DEBUGEXTRA('done')

    kinfo['boot_procs'] = image

    for n in [SEND, RECEIVE, SENDREC, NOTIFY, SENDNB, SENDA]:
        assert(n >= 0 and n <= IPCNO_HIGHEST)
        assert(not ipc_call_names[n])
        # TODO check # operator
        # ipc_call_names[n] = #n

    # System and processes initialization
    memory_init()
    DEBUGEXTRA('system_init()...')
    system_init()
    DEBUGEXTRA('done')

    # The bootstrap phase is over, so we can add the physical
    # memory used for ir to the free list
    # TODO Check this
    # kinfo = add_memmap()

    '''if CONFIG_SMP:
        if config_no_apic:
            BOOT_VERBOSE(
                print('APIC disabled, disables SMP, using legact PIC'))
            smp_single_cpu_fallback()
        elif config_no_smp:
            BOOT_VERBOSE(print('SMP disabled, using legacy'))
            smp_single_cpu_fallback
        else:
            smp_init()
            bsp_finish_booting()
    else:'''
    ''' if configured for a single CPU, we are already
        on the kernel stack which we are going to use
        everytime we execute kernel code. We finish
        booting and we never return here'''
    bsp_finish_booting()

    return local_cbi


def _announce():
    print('''
    PYTHONIX
    Join us to make Pythonix better...
    https://github.com/vhpanisa/pythonix'''
          )


def prepare_shutdown(how):
    print('PYTHONIX will now shutdown...')
    # TODO Check tmr_arg functions
    # tmr_arg(&shutdown_timer)->ta_int = how;
    shutdown_timer = set_timer(shutdown_timer,
                               get_monotonic() + system_hz, pythonix_shutdown)


def pythonix_shutdown(tp):
    '''This function is called from prepare_shutdown or stop_sequence to bring
    down PYTHONIX. How to shutdown is in the argument: RBT_HALT (return to the
    monitor), RBT_RESET (hard reset).
    '''
    '''if CONFIG_SMP:'''
        # MXCM #
    '''FIXME:
        we will need to stop timers on all cpus if SMP is
        enabled and put them in such a state that we can
        perform the whole boot process once restarted from
        monitor again
        if ncpus > 1:
            smp_shutdown_aps()'''

    hw_intr_disable_all()
    stop_local_timer()
    # TODO check tmr_arg AGAIN
    # how = tmr_arg(tp)['ta_int'] if tp else RBT_PANIC

    direct_cls()
    if how == RBT_HALT:
        direct_print('PYTHONIX has halted, you could turn off your computer')
    elif how == RBT_POWEROFF:
        direct_print('PYTHONIX has halted and will now power off.')
    else:
        direct_print('PYTHONIX will now reset.')

    arch_shutdown(how)

    return tp


def cstart():
    '''Perform system initializations prior to calling main().
    Most settings are determined with help of the environment
    strings passed by PYTHONIX loader.
    '''

    # low_level initialization
    prot_init()

    # determine verbosity
    if value == env_get(VERBOSEBOOTVARNAME):
        verboseboot = int(value)

    # Get clock tick frequency
    value = env_get('hz')
    if value:
        system_hz = str(value)
    if not value or system_hz < 2 or system_hz > 50000:  # sanity check
        system_hz = DEFAULT_HZ

    DEBUGEXTRA('cstart')

    # Record misc info for u-space server proc
    kinfo['nr_procs'] = NR_PROCS
    kinfo['nr_tasks'] = NR_TASKS
    kinfo['release'] = OS_RELEASE
    kinfo['version'] = OS_VERSION

    # Load average data initialization
    kloadinfo['proc_last_load'] = 0
    for h in range(_LOAD_HISTORY):
        kloadinfo['proc_load_history'][h] = 0

    if USE_APIC:
        value = env_get('no_apic')
        if(value):
            config_no_apic = int(value)
        else:
            config_no_apic = 1

        value = env_get('apic_timer_x')
        if(value):
            config_apic_timer_x = int(value)
        else:
            config_apic_timer_x = 1

    if USE_WATCHDOG:
        value = env_get(watchdog)
        if value:
            watchdog_enabled = int(value)

    '''if CONFIG_SMP:
        if(config_no_apic):
            config_no_smp = 1
        value = env_get('no_smp')
        if(value):
            config_no_smp = int(value)
        else:
            config_no_smp = 0
    '''
    intr_init(0)
    arch_init()


def get_value(params, name):
    # TODO write this function when boot monitor params are ready
    # Get environment value - kernel version of
    # getenv to avoid setting up the usual environment array.
    return None


def env_get(name):
    return get_value(kinfo['param_buf'], name)


def cpu_print_freq(cpu):
    freq = cpu_get_freq(cpu)
    # TODO check div64u
    print('CPU {} freq {} MHz'.format(cpu, freq))


def is_fpu():
    return get_cpulocal_var(fpu_presence)

if __name__ == '__main__':
    kmain()
########NEW FILE########
__FILENAME__ = proc
# TODO: Check dependencies #


def _set_idle_name(name, n):

    p_z = False

    if n > 999:
        n = 999

    name = 'idle'

    i = 4
    c = 100
    while c > 0:
        digit = n // c
        n -= digit * c
        if p_z or digit != 0 or c == 1:
            p_z = True
            name = ''.join([name, chr(ord('0') + digit)])
            i += 1
        c = c // 10

    return name

PICK_ANY = 1
PICK_HIGHERONLY = 2


def BuildNotifyMessage(m_ptr, src, dst_ptr):
    m_ptr['m_type'] = NOTIFY_MESSAGE
    m_ptr['NOTIFY_TIMESTAMP'] = get_monotonic()
    # TODO: Check priv function
    if src == HARDWARE:
        m_ptr['NOTIFY_TAG'] = dst_ptr['s_int_pending']
        dst_ptr['s_int_pending'] = 0
    elif src == SYSTEM:
        m_ptr['NOTIFY_TAG'] = dst_ptr['s_sig_pending']
        dst_ptr['s_sig_pending'] = 0


def proc_init():

    rp = BEG_PROC_ADDR + 1
    i = -NR_TASKS + 1
    while rp < END_PROC_ADDR:
        rp['p_rts_flags'] = RTS_SLOT_FREE
        rp['p_magic'] = PMAGIC
        rp['p_nr'] = i
        rp['p_endpoint'] = _ENDPOINT(0, rp['p_nr'])
        rp['p_scheduler'] = None
        rp['p_priority'] = 0
        rp['p_quantum_size_ms'] = 0
        arch_proc_reset(rp)
        rp += 1
        i += 1

    sp = BEG_PRIV_ADDR + 1
    i = 1
    while sp < END_PRIV_ADDR:
        # TODO: Check Minix NONE value.
        sp['s_proc_nr'] = NONE
        # TODO: Check if this casting is needed #
        sp['s_id'] = sys_id_t(i)
        ppriv_addr[i] = sp
        sp['s_sig_mrg'] = NONE
        sp['s_bak_sig_mgr'] = NONE
        sp += 1
        i += 1

    idle_priv.s_flags = IDL_F

    # Initialize IDLE dicts for every CPU #
    for i in range(CONFIG_MAX_CPUS):
        ip = get_cpu_var_ptr(i, idle_proc)
        ip['p_endpoint'] = IDLE
        ip['p_priv'] = idle_priv
        # Idle must never be scheduled #
        ip['p_rts_flags'] |= RTS_PROC_STOP
        _set_idle_name(ip['p_name'], i)


def _switch_address_space_idle():
    # MXCM #
    ''' Currently we bet that VM is always alive and its pages available so
    when the CPU wakes up the kernel is mapped and no surprises happen.
    This is only a problem if more than 1 cpus are available.'''

    '''
    if CONFIG_SMP:
        switch_address_space(proc_addr(VM_PROC_NR))
    '''


def _idle():
    # MXCM #
    ''' This function is called whenever there is no work to do.
    Halt the CPU, and measure how many timestamp counter ticks are
    spent not doing anything. This allows test setups to measure
    the CPU utilization of certain workloads with high precision.'''

    # TODO: Check how to handle this in python
    # p = get_cpulocal_var(proc_ptr) = get_cpulocal_var_ptr(idle_proc)

    if priv(p)['s_flags'] & BILLABLE:
        # TODO check SMP stuff
        CPULOCAL_STRUCT[0][bill_ptr] = p

    _switch_address_space_idle()


    # TODO Check this if necessary
    restart_local_timer()
    '''if CONFIG_SMP:
        CPULOCAL_STRUCT[0][cpu_is_idle] = 1
        if (cpuid != bsp_cpu_id):
            stop_local_timer()
        else:
            restart_local_timer()
    '''

    # Start accounting for the idle time #
    context_stop(proc_addr(KERNEL))
    if not SPROFILE:
        halt_cpu()
    else:
        if not sprofiling:
            halt_cpu()
        else:
            v = get_cpulocal_var_ptr(idle_interrupted)
            interrupts_enable()
            while not v:
                arch_pause()
            interrupts_disable()
            v = 0
    ''' End of accounting for the idle task does not happen here, the kernel
    is handling stuff for quite a while before it gets back here!'''


# TODO: Translate switch_to_user() #
def switch_to_user():
    pass


# Handler for all synchronous IPC calls #
def _do_sync_ipc(caller_ptr, call_nr, src_dst_e, m_ptr):
    # MXCM #
    '''Check destination. RECEIVE is the only call that accepts ANY (in
    addition to a real endpoint). The other calls (SEND, SENDREC, and NOTIFY)
    require an endpoint to corresponds to a process. In addition, it is
    necessary to check whether a process is allowed to send to a given
    destination.'''

    if (
        call_nr < 0 or
        call_nr > IPCNO_HIGHEST or
        call_nr >= 32 or
        callname != ipc_call_names[call_nr]
    ):
        if DEBUG_ENABLE_IPC_WARNINGS:
            print('sys_call: trap {} not_allowed, caller {}, src_dst {}'
                  .format(call_nr, proc_nr(caller_ptr), src_dst_e))
        return ETRAPDENIED

    if src_dst_e == ANY:
        if call_nr != RECEIVE:
            return EINVAL
        src_dst_p = int(src_dst_e)
    else:
        if not isokendpt(src_dst_e, src_dst_p):
            return EDEADSRCDST

        # MXCM #
        ''' If the call is to send to a process, i.e., for SEND, SENDNB,
        SENDREC or NOTIFY, verify that the caller is allowed to send to
        the given destination.'''
        if call_nr != RECEIVE:
            if not may_send_to(caller_ptr, src_dst_p):
                if DEBUG_ENABLE_IPC_WARNINGS:
                    print('sys_call: ipc mask denied {} from {} to {}'
                          .format(callname, caller_ptr['p_endpoint'],
                                  src_dst_e))
                return ECALLDENIED

    # MXCM #
    ''' Check if the process has privileges for the requested call.
    Calls to the kernel may only be SENDREC, because tasks always
    reply and may not block if the caller doesn't do receive().'''

    if not priv(caller_ptr)['s_trap_mask'] & (1 << call_nr):
        if DEBUG_ENABLE_IPC_WARNINGS:
            print('sys_call: ipc mask denied {} from {} to {}'
                  .format(callname, caller_ptr['p_endpoint'], src_dst_e))
        return ETRAPDENIED

    if call_nr != SENDREC and call_nr != RECEIVE and iskerneln(src_dst_p):
        if DEBUG_ENABLE_IPC_WARNINGS:
            print('sys_call: ipc mask denied {} from {} to {}'
                  .format(callname, caller_ptr['p_endpoint'], src_dst_e))
        return ETRAPDENIED

    if call_nr == SENDREC:
        caller_ptr['p_misc_flags'] |= MF_REPLY_PEND
        # TODO tweak logic to swcase fall
    elif call_nr == SEND:
        result = mini_send(caller_ptr, src_dst_e, m_ptr, 0)
        if call_nr == SEND or result != OK:
            pass
        # TODO tweak logic to swcase break
        # TODO tweak logic to swcase fall
    elif call_nr == RECEIVE:
        # TODO tweak logic to swcase recheck
        caller_ptr['p_misc_flags'] &= ~MF_REPLY_PEND
        IPC_STATUS_CLEAR(caller_ptr)
        result = mini_receive(caller_ptr, src_dst_e, m_ptr, 0)
    elif call_nr == NOTIFY:
        result = mini_notify(caller_ptr, src_dst_e)
    elif call_nr == SENDNB:
        result = mini_send(caller_ptr, src_dst_e, m_ptr, NON_BLOCKING)
    else:
        result = EBADCALL

    # Return the result of system call to the caller #
    return result


def do_ipc(r1, r2, r3):
    # TODO: Check if this way of translating pointer is right
    caller_ptr = get_cpulocal_var(proc_ptr)
    call_nr = r1

    assert(not RTS_ISSET(caller_ptr, RTS_SLOT_FREE))

    # MXCM #
    # Bill kernel time to this process
    kbill_ipc = caller_ptr

    # MXCM #
    # If this process is subset to system call tracing,
    # handle that first

    if caller_ptr['p_misc_flags'] & (MF_SC_TRACE | MR_SC_DEFER):
        # MXCM #
        # Are we tracing this process, and is it the
        # first sys_call entry?

        if (
            (caller_ptr['p_misc_flags'] & (MF_SC_TRACE | MR_SC_DEFER)) ==
            MF_SC_TRACE
        ):
            # MXCM #
            '''We must notify the tracer before processing the actual
            system call. If we don't, the tracer could not obtain the
            input message. Postpone the entire system call.'''

            caller_ptr['p_misc_flags'] &= ~MF_SC_TRACE
            assert(not caller_ptr['p_misc_flags'] & MR_SC_DEFER)
            caller_ptr['p_misc_flags'] |= MF_SC_DEFER
            caller_ptr['p_defer']['r1'] = r1
            caller_ptr['p_defer']['r2'] = r2
            caller_ptr['p_defer']['r3'] = r3

            # Signal the "enter system call" event. Block the process.
            cause_sig(proc_nr(caller_ptr), SIGTRAP)

            # Preserve the return registrer's value.
            return caller_ptr['p_reg']['retreg']

        # If the MF_SC_DEFER flag is set, the syscall is now being resumed.
        caller_ptr['p_misc_flags'] &= ~MF_SC_DEFER
        assert(not caller_ptr['p_misc_flags'] & MF_SC_ACTIVE)

        # Set a flag to allow reliable tracing of leaving the system call.
        caller_ptr['p_misc_flags'] |= MF_SC_ACTIVE

    if caller['p_misc_flags'] & MF_DELIVERMSG:
        panic('sys_call: MF_DELIVERMSG on for {} / {}'
              .format(caller_ptr['p_name'], caller_ptr['p_endpoint']))

    # MXCM #
    '''Now check if the call is known and try to perform the request. The only
    system calls that exist in MINIX are sending and receiving messages.
    - SENDREC: combines SEND and RECEIVE in a single system call
    - SEND:    sender blocks until its message has been delivered
    - RECEIVE: receiver blocks until an acceptable message has arrived
    - NOTIFY:  asynchronous call; deliver notification or mark pending
    - SENDA:   list of asynchronous send requests'''

    if call_nr in [SENDREC, SEND, RECEIVE, NOTIFY, SENDNB]:
        # Process accounting for scheduling
        # TODO: Check castings here
        return _do_sync_ipc(caller_ptr, call_nr, r2, r3)

    elif call_nr == SENDA:
        # Get and check the size of the arguments in bytes
        # TODO: Check if len() get the needed size from r2
        msg_size = len(r2)

        # Process accounting for scheduling
        caller_ptr['p_accounting']['ipc_async'] += 1

        # Limit size to something reasonable. An arbitrary choice is 16
        # times the number of process table entries
        if msg_size > 16 * (NR_TASKS + NR_PROCS):
            return EDOM
        # TODO: Check castings here
        return mini_senda(caller_ptr, r3, msg_size)

    elif call_nr == PYTHONIX_KERNINFO:
        # It may not be initialized yet
        if not pythonix_kerninfo_user:
            return EBADCALL

        arch_set_secondary_ipc_return(caller_ptr, pythonix_kerninfo_user)
        return OK

    else:
        # Illegal system call
        return EBADCALL


# TODO: Check this function I was not sure how to translate it to python
def _deadlock(function, cp, src_dst_e):
    # MXCM #
    ''' Check for deadlock. This can happen if 'caller_ptr' and
    'src_dst' have a cyclic dependency of blocking send and
    receive calls. The only cyclic dependency that is not fatal
    is if the caller and target directly SEND(REC) and RECEIVE
    to each other. If a deadlock is found, the group size is
    returned. Otherwise zero is returned.'''
    pass


def _has_pending(map_, src_p, asynm):
    # MXCM #
    # Check to see if there is a pending message from
    # the desired source available.

    id_ = NULL_PRIV_ID

    '''
    if CONFIG_SMP:
        p = {}
    '''

    # MXCM #
    '''Either check a specific bit in the mask map, or find the first
    bit set in it (if any), depending on whether the receive was
    called on a specific source endpoint.'''

    if src_p != ANY:
        src_id = nr_to_id(src_p)

        if get_sys_bit(map_, src_id):
            # This if does nothig while CONFIG_SMP is not implemented
            pass
            # TODO Implement SMP
            '''
            if CONFIG_SMP:
                p = proc_addr(id_to_nr(src_id))

                if asynm and RTS_ISSET(p, RTS_VMINHIBIT):
                    p['p_misc_flags'] |= MF_SENDA_VM_MISS
                else:
                    id_ = src_id
            '''
    else:
        # Find a source with a pending message

        aux = True
        for src_id in range(0, NR_SYS_PROCS, BITCHUNCK_BITS):
            if get_sys_bits(_map, src_id) != 0:
                # TODO Implement SMP
                '''
                if CONFIG_SMP:
                    while src_id < NR_SYS_PROCS and aux:
                        while not get_sys_bit(map_, src_id) and aux:
                            if src_id == NR_SYS_PROCS:
                                aux = False
                                break
                            src_id += 1
                        if not aux:
                            break
                        p = proc_addr(id_to_nr(src_id))
                        # MXCM #
                        """ We must not let kernel fiddle with pages of a
                        process which are currently being changed by
                        VM.  It is dangerous! So do not report such a
                        process as having pending async messages.
                        Skip it."""
                        if asynm and RTS_ISSET(p, RTS_VMINHIBIT):
                            p['p_misc_flags'] |= MF_SENDA_VM_MISS
                            src_id += 1
                        else:
                            aux = False
                            break
                '''
                if aux:
                    # TODO: Change this if to elif when CONFIG_SMP is
                    # implemented
                    while not get_sys_bit(map_, src_id):
                        src_id += 1
                    aux = False
                    break

        if src_id < NR_SYS_PROCS:
            # Founf one
            id_ = src_id
    return id_


def has_pending_notify(caller, src_p):
    _map = priv(caller)['s_notify_pending']
    return _has_pending(_map, src_p, 0)


def has_pending_asend(caller, src_p):
    _map = priv(caller)['s_asyn_pending']
    return _has_pending(_map, src_p, 1)


def unset_notify_pending(caller, src_p):
    _map = priv(caller)['s_notify_pending']
    unset_sys_bit(_map, src_p)


def mini_send(caller_ptr, dst_e, m_ptr, flags):
    dst_p = ENDPOINT(dst_e)
    dst_ptr = proc_addr(dst_p)

    if RTS_ISSET(dst_ptr, RTS_NO_ENDPOINT):
        return EDEADSRCDST

    # MXCM #
    '''Check if 'dst' is blocked waiting for this message. The
    destination's RTS_SENDING flag may be set when its SENDREC
    call blocked while sending'''

    if WILLRECEIVE(dst_ptr, caller_ptr['p_endpoint']):
        # Destination is indeed waiting for this message.
        assert(not (dst_ptr['p_misc_flags'] & MF_DELIVERMSG))

        if not (flags & FROM_KERNEL):
            if copy_msg_from_user(m_ptr, dst_ptr['p_delivermsg']):
                return EFAULT
        else:
            dst_ptr['p_delivermsg'] = m_ptr
            IPC_STATUS_ADD_FLAGS(dst_ptr, IPC_FLG_MSG_FROM_KERNEL)

        dst_ptr['p_delivermsg']['m_source'] = caller_ptr['p_endpoint']
        dst_ptr['p_misc_flags'] |= MF_DELIVERMSG

        if caller_ptr['p_misc_flags'] & MF_REPLY_PEND:
            call = SENDREC
        else:
            if flags & NON_BLOCKING:
                call = SENDNB
            else:
                call = SEND

        IPC_STATUS_ADD_CALL(dst_ptr, call)

        if dst_ptr['p_misc_flags'] & MF_REPLY_PEND:
            dst_ptr['p_misc_flags'] &= ~MF_REPLY_PEND

        RTS_UNSET(dst_ptr, RTS_RECEIVING)

        if DEBUG_IPC_HOOK:
            hook_ipc_msgsend(dst_ptr['p_delivermsg'], caller_ptr, dst_ptr)
            hook_ipc_msgrecv(dst_ptr['p_delivermsg'], caller_ptr, dst_ptr)

    else:
        if flags & NON_BLOCKING:
            return ENOTREADY

        # Check for a possible deadlock before actually blocking
        if deadlock(send, caler_ptr, dst_e):
            return ELOCKED

        # Destination is not waiting. Block and dequeue caller
        if not (flags & FROM_KERNEL):
            if copy_msg_from_user(m_ptr, caller_ptr['p_sendmsg']):
                return EFAULT
        else:
            caller_ptr['p_sendmsg'] = m_ptr

            # MXCM #
            '''We need to remember that this message is from kernel
            so we can set the delivery status flags when the message
            is actually delivered'''

            caller_ptr['p_misc_flags'] |= MF_SENDING_FROM_KERNEL

        RTS_SET(caller_ptr, RTS_SENDING)
        caller_ptr['p_sendto_e'] = dst_e

        # Process is now blocked. Put in on destination's queue
        assert(caller_ptr['p_q_link'] == None)

        # TODO: Check how to do this
        '''
        while (*xpp) xpp = &(*xpp)->p_q_link;
	*xpp = caller_ptr;
        '''

        if DEBUG_IPC_HOOK:
            hook_ipc_msgsend(caller_ptr['p_sendmsg'], caller_ptr, dst_ptr)

    return OK


def _mini_receive(caller_ptr, src_e, m_buff_usr, flags):

    def receive_done(caller_ptr):
        # Function to help get rid of goto
        if caller_ptr['p_misc_flags'] & MF_REPLY_PEND:
            caller_ptr['p_misc_flags'] &= ~MR_REPLY_PEND
        return OK

    # MXCM #
    '''A process or task wants to get a message.  If a message is
    already queued, acquire it and deblock the sender.  If no message
    from the desired source is available block the caller.'''

    assert(not (caller_ptr['p_misc_flags'] & MF_ELIVERMSG))

    # This is where we want our message #
    caller_ptr['p_delivermsg_vir'] = m_buff_usr

    if src_e == ANY:
        src_p = ANY
    else:
        okendpt(src_e, src_p)
        if RTS_ISSET(proc_addr(src_p), RTS_NO_ENDPOINT):
            return EDEADSRCDST

    # MXCM #
    '''Check to see if a message from desired source is already available.  The
    caller's RTS_SENDING flag may be set if SENDREC couldn't send. If it is
    set, the process should be blocked.'''

    if not RTS_ISSET(caller_ptr, RTS_SENDING):

        # Check if there are pending notifications, except for SENDREC
        if not (caller_ptr['p_misc_flags'] & MF_REPLY_PEND):

            # TODO: check if there's an error on minix code here
            src_id = has_pending_notify(caller_ptr, src_p)
            if src_id != NULL_PRIV_ID:

                src_proc_nr = id_to_nr(src_id)
                if DEBUG_ENABLE_IPC_WARNINGS:
                    print('mini_receive: sending notify from ', src_proc_nr)

                assert(src_proc_nr != NONE)
                unset_notify_pending(caller_ptr, src_id)

                # Found a suitable source, deliver the
                # notification message
                hisep = proc_addr(src_proc_nr)['p_endpoint']
                assert(not (caller_ptr['p_misc_flags'] & MF_DELIVERMSG))
                assert(src_e == ANY or hisep == src_e)

                # Assemble the message
                BuildNotifyMessage(caller_ptr['p_delivermsg'],
                                   src_proc_nr,
                                   caller_ptr)
                caller_ptr['p_delivermsg']['m_source'] = hisep
                caller_ptr['p_misc_flags'] |= MF_DELIVERMSG

                IPC_STATUS_ADD_CALL(caller_ptr, NOTIFY)

                return receive_done(caller_ptr)

        # Check for pending asynchronous messages
        if has_pending_asend(caller_ptr, src_p) != NULL_PRIV_ID:

            if src_p != ANY:
                r = try_one(proc_addr(src_p), caller_ptr)
            else:
                r = try_async(caller_ptr)

            if r == OK:
                IPC_STATUS_ADD_CALL(caller_ptr, SENDA)
                return receive_done

        # Check caller queue.
        # TODO: Check the possibility to use id() when variable address
        # is used in minix code

        '''This xpp, is a list implementation with a null terminator,
        the '\0' character, many points in system use this, but
        depending on the situation it'll be tweaked in a different way.
        This message communication interface it's very probably to be
        replaced for a class with a dict of lists, where each entry of
        dict is a proc_id and each entry of list is a message for the
        owner process for that key in dict, this only can be solved
        when the code is almost finished, to realize what can be
        replaced or not'''

        # FIXME: Implement the class described above for use in the
        # commented code below
        """
        xpp = caller_ptr['p_caller_q']

        while xpp:

            sender = xpp
            if src_e == ANY or src_p == proc_nr(sender):
                assert(not RTS_ISSET(sender, RTS_SLOT_FREE))
                assert(not RTS_ISSET(sender, RTS_NO_ENDPOINT))

                # Found acceptable message. Copy it and update status
                assert(not(caller_ptr['p_misc_flags'] & MF_DELIVERMSG))
                caller_ptr['p_delivermsg'] = sender['p_sendmsg']
                caller_ptr['p_delivermsg']['m_source'] = sender['p_endpoint']
                caller_ptr['p_misc_flags'] |= MF_DELIVERMSG
                RTS_UNSET(sender, RTS_SENDING)

                if sender['p_misc_flags'] & MF_SENDING_FROM_KERNEL:
                    call = SENDREC

                else:
                    call = SEND

                IPC_STATUS_ADD_CALL(caller_ptr, call)

                # MXCM #
                '''if the message is originally from the kernel on
                behalf of this process, we must send the status
                flags accordingly'''

                if sender['p_misc_flags'] & MF_SENDING_FROM_KERNEL:
                    IPC_STATUS_ADD_FLAGS(caller_ptr, IPC_FLG_MSG_FROM_KERNEL)
                    # we can clean the flag now, not need anymore
                    sender['p_misc_flags'] &= ~MF_SENDING_FROM_KERNEL

                if sender['p_misc_flags'] & MF_SIG_DELAY:
                    sig_delay_done(sender)

                if DEBUG_IPC_HOOK:
                    hook_ipc_msgrecv(caller_ptr['p_delivermsg'], xpp,
                                     caller_ptr)

                xpp = sender['p_q_link']
                sender['p_q_link'] = None
                return receive_done(caller_ptr)
            xpp = sender['p_q_link']
        """

    # MXCM #
    ''' No suitable message is available or the caller couldn't send in
    SENDREC.Block the process trying to receive, unless the flags tell
    otherwise.'''

    if not(flags & NON_BLOCKING):
        # Check for a possible deadlock before actually blocking.
        if _deadlock(RECEIVE, caller_ptr, src_e):
            return ELOCKED

        caller_ptr['p_getfrom_e'] = src_e
        RTS_SET(caller_tr, RTS_RECEIVING)
        return OK
    else:
        return ENOTREADY

    return receive_done(caller_ptr)

########NEW FILE########
__FILENAME__ = system
'''This task handles the interface between the kernel and user-level servers.
System services can be accessed by doing a system call. System calls are 
transformed into request messages, which are handled by this task. By 
convention, a sys_call() is transformed in a SYS_CALL request message that
is handled in a function named do_call(). 

A private call vector is used to map all system calls to the functions that
handle them. The actual handler functions are contained in separate files
to keep this file clean. The call vector is used in the system task's main
loop to handle all incoming requests.  

In addition to the main sys_task() entry point, which starts the main loop,
there are several other minor entry points:
get_priv:		assign privilege structure to user or system process
set_sendto_bit:	allow a process to send messages to a new target
unset_sendto_bit:	disallow a process from sending messages to a target
fill_sendto_mask:	fill the target mask of a given process
send_sig:		send a signal directly to a system process
cause_sig:		take action to cause a signal to occur via a signal mgr
sig_delay_done:	tell PM that a process is not sending
get_randomness:	accumulate randomness in a buffer
clear_endpoint:	remove a process' ability to send and receive messages
sched_proc:	schedule a process

Changes:
Nov 22, 2009   get_priv supports static priv ids (Cristiano Giuffrida)
Aug 04, 2005   check if system call is allowed  (Jorrit N. Herder)
Jul 20, 2005   send signal to services with message  (Jorrit N. Herder) 
Jan 15, 2005   new, generalized virtual copy function  (Jorrit N. Herder)
Oct 10, 2004   dispatch system calls from call vector  (Jorrit N. Herder)
Sep 30, 2004   source code documentation updated  (Jorrit N. Herder)'''

# TODO check imports

'''Declaration of the call vector that defines the mapping of system calls
to handler functions. The vector is initialized in sys_init() with map(), 
which makes sure the system call numbers are ok. No space is allocated, 
because the dummy is declared extern. If an illegal call is given, the 
array size will be negative and this won't compile.'''


def map_(call_nr, handler):
    call_index = call_nr - KERNEL_CALL
    assert(call_index >= 0 and call_index < NR_SYS_CALLS)
    # TODO check WTF is call_vec
    call_vec[call_index] = handler


def kernel_call_finish(caller, msg, result):
    if result == VMSUSPEND:
        '''Special case: message has to be saved for handling
        until VM tells us it's allowed. VM has been notified
        and we must wait for its reply to restart the call.'''
        assert(RTS_ISSET(caller, RTS_VMREQUEST))
        # TODO check caller struct
        assert(caller['p_vmrequest']['type'] == VMSTYPE_KERNELCALL)
        caller['p_vmrequest']['saved']['reqmsg'] = msg
        caller['p_misc_flags'] |= MF_KCALL_RESUME
    else:
        ''' call is finished, we could have been suspended because
        of VM, remove the request message'''
        caller['p_vmrequest']['saved']['reqmsg']['m_source'] = None
        if result != EDONTREPLY:
            # Copy the result as a message to the original user buffer
            msg['m_source'] = SYSTEM
            msg['m_type'] = result
            if DEBUG_IPC_HOOK:
                hook_ipc_msgkresult(msg, caller)
            if copy_msg_to_user(msg, caller['p_delivermsg_vir']):
                print('WARNING wrong user pointer {} from process {} /\
					{}'.format(caller['p_delivermsg_vir'], caller['p_name'],
                    caller['p_endpoint']
                )
                )
                cause_sig(proc_nr(caller), SIGSEGV)


def kernel_call_dispatch(caller, msg):
    result = OK
    if DEBUG_IPC_HOOK:
        hook_ipc_msgkresult(msg, caller)
    call_nr = msg['m_type'] - KERNEL_CALL

    # See if the caller made a valid request and try to handle it
    if call_nr < 0 or call_nr >= NR_SYS_CALLS:
        result = EBADREQUEST
    elif not GET_BIT(priv(caller)['s_k_call_mask'], call_nr):
        result = ECALLDENIED
    else:  # handle the system call
        if call_vec[call_nr]:
            result = call_vec[call_nr](caller, msg)  # TODO check WTF
        else:
            print("Unused kernel call {} from {}".format(
                call_nr, caller['p_endpoint'])
            )

    if result in [EBADREQUEST, ECALLDENIED]:
        print('SYSTEM: illegal request {} from {}'.format(
            call_nr, msg['m_source'])
        )

    return result


def kernel_call(m_user, caller):
    ''' Check the basic syscall parameters and if accepted
    dispatches its handling to the right handler'''
    result = OK
    msg = {}

    # TODO check vir_bytes casting
    caller['p_delivermsg_vir'] = m_user

    ''' the ldt and cr3 of the caller process is loaded because	it just've
	trapped into the kernel or was already set in switch_to_user() before we
	resume execution of an interrupted kernel call'''
    if not copy_msg_from_user(m_user, msg):
        msg['m_source'] = caller['p_endpoint']
        result = kernel_call_dispatch(caller, msg)
    else:
        print('WARNING wrong user pointer {} from process {} / {}'.format(
            m_user, caller['p_name'], caller['p_endpoint'])
        )

    kbill_kcall = caller
    kernel_call_finish(caller, msg, result)


def initialize():
        # TODO implement
    pass


def get_priv(rc, priv_id):
    ''' Allocate a new privilege structure for a system process.
    Privilege ids can be assigned either statically or dynamically.'''
    # TODO check sp loop
    if priv_id == NULL_PRIV_ID:  # allocate slot dynamically
        for sp in range(BEG_DYN_PRIV_ADDR + 1, END_DYN_PRIV_ADDR):
            if sp['s_proc_nr'] == None:
                break
        if sp >= END_DYN_PRIV_ADDR return ENOSPC
    else:  # allocate slot from id
        if not is_static_priv_id(priv_id):
            return EINVAL  # invalid id
        if priv[priv_id].s_proc_nr != None:
            return EBUSY  # slot in use
        sp = priv['priv_id']

    rc['p_priv'] = sp  # assign new slow
    rc['p_priv']['s_proc_nr'] = proc_nr(rc)  # set association

    return OK


def set_sendto_bit(rp, _id):
    ''' Allow a process to send messages to the process(es) associated
    with the system privilege structure with the given id.'''

    ''' Disallow the process from sending to a process privilege structure
	with no associated process, and disallow the process from sending to
	itself.'''
    if id_to_nr(_id) == None or priv_id(rp) == _id:
        unset_sys_bit(priv(rp)['s_ipc_to'], _id)
        return

    set_sys_bit(priv(rp)['s_ipc_to'], _id)

    ''' The process that this process can now send to, must be able to reply
	(or	vice versa). Therefore, its send mask should be updated as well.
	Ignore receivers that don't support traps other than RECEIVE, they can't
	reply or send messages anyway.'''

    if priv_addr(_id)['s_trap_mask'] & ~(1 << RECEIVE):
        set_sys_bit(priv_addr(_id)['s_ipc_to'], priv_id(rp))


def unset_sendto_bit(rp, _id):
    ''' Prevent a process from sending to another process. Retain the send
    mask symmetry by also unsetting the bit for the other direction.'''
    unset_sys_bit(priv(rp)['s_ipc_to'], _id)
    unset_sys_bit(priv_addr(_id)['s_ipc_to'], priv_id(rp))


def fill_sendto_mask(rp, _map):
    for i in range(len(NR_SYS_PROCS)):
        if get_sys_bit(_map, i):
            set_sendto_bit(rp, i)
        else:
            unset_sendto_bit(rp, i)


def send_sig(ep, sig_nr):
    ''' Notify a system process about a signal. This is straightforward. Simply
    set the signal that is to be delivered in the pending signals map and
    send a notification with source SYSTEM. '''
    if not isokendpt(ep, proc_nr) or isemptyn(proc_nr):
        return EINVAL

    rp = proc_addr(proc_nr)
    priv = priv(rp)
    if not priv:
        return ENOENT
    sigaddset(priv['s_sig_pending'], sig_nr)
    increase_proc_signals(rp)
    mini_notify(proc_addr(SYSTEM), rp['p_endpoint'])

    return OK


def cause_sig(proc_nr, sig_nr):
    '''A system process wants to send a signal to a process.  Examples are:
    - HARDWARE wanting to cause a SIGSEGV after a CPU exception
    - TTY wanting to cause SIGINT upon getting a DEL
    - FS wanting to cause SIGPIPE for a broken pipe

    Signals are handled by sending a message to the signal manager assigned to
    the process. This function handles the signals and makes sure the signal
    manager gets them by sending a notification. The process being signaled
    is blocked while the signal manager has not finished all signals for it.
    Race conditions between calls to this function and the system calls that
    process pending kernel signals cannot exist. Signal related functions are
    only called when a user process causes a CPU exception and from the kernel
    process level, which runs to completion.'''

    # Lookup signal manager
    rp = proc_addr(proc_nr)
    sig_mgr = priv(rp)['s_sig_mgr']
    # TODO check self definition
    if sig_mgr == SELF:
        sig_mgr = rp['p_endpoint']

    # If the target is the signaol manager of itself
    # send the signal directly
    if rp['p_endpoint'] == sig_nr:
        if SIGS_IS_LETHAL(sig_nr):
            # If sig is lethal, see if a backup sig manager exists
            sig_mgr = priv(rp)['s_bak_sig_mgr']
            if sig_mgr != None and isokendpt(sig_mgr, sig_mgr_proc_nr):
                priv(rp)['s_sig_mgr'] = sig_mgr
                priv(rp)['s_bak_sig_mgr'] = None
                sig_mgr_rp = proc_addr(sig_mgr_proc_nr)
                RTS_UNSET(sig_mgr_rp, RTS_NO_PRIV)
                cause_sig(proc_nr, sig_nr)  # try again with new sig mgr
                return
            # no luck, time to panic
            proc_stacktrace(rp)
            panic("cause_sig: sig manager {} gets lethal signal {} for itself".format(
                rp['p_endpoint'], sig_nr))
        sigaddset(priv(rp)['s_sig_pending'], sig_nr)
        if send_sig(rp['p_endpoint'], SIGKSIGSM):
            panic('send_sig failed')
        return

    # Check if the signal is already pending. Process it otherwise
    if not sigismember(rp['p_pending'], sig_nr):
        sigaddset(rp['p_pending'], sig_nr)
        increase_proc_signals(rp)
        if not RTS_ISSET(rp, RTS_SIGNALED):
            RTS_SET(rp, RTS_SIGNALED | RTS_SIG_PENDING)
            if send_sig(sig_mgr, SIGKSIG) != OK:
                panic('send_sig failed')


def sig_delay_done(rp):
    '''A process is now known not to send any direct messages.
       Tell PM that the stop delay has ended, by sending a signal to the
       process. Used for actual signal delivery.'''
        rp['p_misc_flags'] &= ~MF_SIG_DELAY
        cause_sig(proc_nr(rp), SIGSNDELAY)


def _clear_ipc(rc):
        # TODO implement
    pass


def clear_endpoint(rc):
    if isemptyp(rc):
        panic('clear_proc: empty process {}'.format(rc['p_endpoint']))

    if DEBUG_IPC_HOOK:
        hook_ipc_clear(rc)

    # Make sure that the exiting proc is no longer scheduled
    RTS_SET(rc, RTS_NO_ENDPOINT)
    if priv(rc)['s_flags'] & SYS_PROC:
        priv(rc)['s_asynsize'] = 0

    # If the process happens to be queued trying to send a
    # message, then it must be removed from the message queues.

    _clear_ipc(rc)

    # Likewise, if another process was sending or receive a message to or from
    # the exiting process, it must be alerted that process no longer is alive.
    # Check all process

    clear_ipc_refs(rc, EDEADSRCDST)


def clear_ipc_refs(rc, caller_ret):
    # Clear IPC references for a given process slot

    # Tell processes that sent asynchronous messages to 'rc'
    # they are not going to be delivered
    src_id = has_pending_asend(rc, ANY)
    while src_id != NULL_PRIV_ID:
        cancel_async(proc_addr(id_to_nr), rc)
        src_id = has_pending_asend(rc, ANY)

    # TODO check this
    for rp in (BEG_PROC_ADDR, END_PROC_ADDR):
        if (isemptyp(rp)):
            continue
        # Unset pending notification bits
        unset_sys_bit(priv(rp)['s_notify_pending'], priv(rc)['s_id'])

        # Unset pending asynchronous messages
        unset_sys_bit(priv(rp)['s_asyn_pending'], priv(rc)['s_id'])

        # Check if process depends on given process.
        if P_BLOCKEDON(rp) == rc['p_endpoint']:
            rp['p_reg']['retreg'] = caller_ret

        clear_ipc(rp)


def kernel_call_resume(caller):
    assert(not RTS_ISSET(caller, RTS_SLOT_FREE))
    assert(not RTS_ISSET(caller, RTS_VMREQUEST))

    asset(caller['p_vmrequest']['saved']['reqmsg']
          ['m_source'] == caller['p_endpoint'])

	# re-execute the kernel call, with MF_KCALL_RESUME still set so
	# the call knows this is a retry.

	result = kernel_call_dispatch(caller, caller['p_vmrequest']['saved']['reqmsg'])

	# we are resuming the kernel call so we have to remove this flag so it
	# can be set again

	caller['p_misc_flags'] &= ~MF_KCALL_RESUME
	kernel_call_finish(caller, caller['p_vmrequest']['saved']['reqmsg'], result)

def sched(p, priority, quantum, cpu):
	# Make sure the values given are within the allowed range.*/
	if priority > NR_SCHED_QUEUES or (priority < TASK_Q and priority != -1):
		return EINVAL

	if quantum < 1 and quantum != -1:
		return EINVAL

    # TODO implement smp
	'''if CONFIG_SMP:
		if (cpu < 0 and cpu != -1) or (cpu > 0 and cpu >= ncpus)
			return EINVAL
		if cpu != -1 and not cpu_is_ready(cpu):
			return EBADCPU
    '''

	'''In some cases, we might be rescheduling a runnable process. In such
	a case (i.e. if we are updating the priority) we set the NO_QUANTUM
	flag before the generic unset to dequeue/enqueue the process'''

	# FIXME this preempts the process, do we really want to do that
	# FIXME this is a problem for SMP if the processes currently runs on a
	# different CPU

	if proc_is_runnable(p):
        pass
        # TODO implement SMP
		'''if CONFIG_SMP:
			if p->p_cpu != cpuid and cpu != -1 and cpu != p->p_cpu:
				smp_schedule_migrate_proc(p, cpu)'''
		RTS_SET(p, RTS_NO_QUANTUM)

	# TODO check, pro cis runnable again ?
	if proc_is_runnable(p):
		RTS_SET(p, RTS_NO_QUANTUM)

	if priority != -1:
		p['p_priority'] = priority
	if quantum != -1:
		p['p_quantum_size_ms'] = quantum
		p['p_cpu_time_left'] = ms_2_cpu_time(quantum)

    # TODO implement SMP
	'''if CONFIG_SMP:
		if cpu != -1:
			p['p_cpu'] = cpu
            '''

	# Clear the scheduling bit and enqueue the process
	RTS_UNSET(p, RTS_NO_QUANTUM)
	
	return OK
}
########NEW FILE########
__FILENAME__ = table
'''The object file of "table.c" contains most kernel data. Variables that are
declared in the *.h files appear with EXTERN in front of them, as in

EXTERN int x;

Normally EXTERN is defined as extern, so when they are included in
another file, no storage is allocated.  If EXTERN were not present,
but just say,

int x;

then including this file in several source files would cause 'x' to be
declared several times.  While some linkers accept this, others do not,
so they are declared extern when included normally.  However, it must
be declared for real somewhere.  That is done here, by redefining
EXTERN as the null string, so that inclusion of all .h files in table.c
actually generates storage for them.

Various variables could not be declared EXTERN, but are declared PUBLIC
or PRIVATE. The reason for this is that extern variables cannot have a
default initialization. If such variables are shared, they must also be
declared in one of the .h files without the initialization. Examples
include 'boot_image' (this file) and 'idt' and 'gdt' (protect.c). 

Changes:
Nov 22, 2009   rewrite of privilege management (Cristiano Giuffrida)
Aug 02, 2005   set privileges and minimal boot image (Jorrit N. Herder)
Oct 17, 2004   updated above and tasktab comments  (Jorrit N. Herder)
May 01, 2004   changed struct for system image  (Jorrit N. Herder)

The system image table lists all programs that are part of the boot image.
The order of the entries here MUST agree with the order of the programs
in the boot image and all kernel tasks must come first. The order of the
entries here matches the priority NOTIFY messages are delivered to a given
process. NOTIFY messages are always delivered with the highest priority.
DS must be the first system process in the list to allow reliable
asynchronous publishing of system events. RS comes right after to
prioritize ping messages periodically delivered to system processes.'''

image[NR_BOOT_PROCS] = 
# process nr, flags, stack size, name ??? WTF
{
'ASYNCM':        'asyncm',
'IDLE':          'idle'  ,
'CLOCK':         'clock' ,
'SYSTEM':        'system',
'HARDWARE':      'kernel',
                      
'DS_PROC_NR':    'ds'    ,
'RS_PROC_NR':    'rs'    ,
                      
'PM_PROC_NR':    'pm'    ,
'SCHED_PROC_NR': 'sched' ,
'VFS_PROC_NR':   'vfs'   ,
'MEM_PROC_NR':   'memory',
'LOG_PROC_NR':   'log'   ,
'TTY_PROC_NR':   'tty'   ,
'MFS_PROC_NR':   'mfs'   ,
'VM_PROC_NR':    'vm'    ,
'PFS_PROC_NR':   'pfs'   ,
'INIT_PROC_NR':  'init'  ,
}

########NEW FILE########
