__FILENAME__ = idpy-arm-helper
# IDA Helper for ARM / iOS binary files
#  - from Analyse.py (https://www.assembla.com/code/ks360/subversion/nodes/utils/Analyze.py)
#
# (c) pod2g 02/2013

from idaapi import *
from idc import *

# Iterate over all segments
for i in Segments():
	start = i
	end = GetSegmentAttr(start, SEGATTR_END)

	# Discover exception vectors (boot loaders)
	if Dword(start) == 0xea00000e :
		for i in range (start, start + 0x20, 4):
			SetReg(i, "T", 0);
			MakeCode(i);

	# Search for ARM PUSH
	addr = start
	while (addr != BADADDR):
		addr = FindBinary  (addr, SEARCH_DOWN, '2D E9', 16)
		if(addr != BADADDR ):
			addr = addr - 2
			if (addr % 4) == 0 and getFlags(addr) < 0x200 :
				# addr is DWORD aligned, 2nd word is 2D E9 and unexplored
                                print "ARM: 0x%X" % addr;
				for i in range (addr, addr + 0x8):
					SetReg(i, "T", 0);
                                MakeFunction(addr);
			addr = addr + 4
	# Search for THUMB PUSH
	addr = start
	while (addr != BADADDR):
		addr = FindBinary  (addr, SEARCH_DOWN, 'B5', 16)
		if(addr != BADADDR ):
			addr = addr - 1
			if (addr % 4) == 0 and getFlags(addr) < 0x200 :
				# addr is DWORD aligned, 2nd byte is B5 and unexplored
                                print "TMB: 0x%X" % addr;
				for i in range (addr, addr + 0x8):
					SetReg(i, "T", 1);
                                MakeFunction(addr);
	
			addr = addr + 2


# Force IDA analysis
for i in Segments():
        start = i
        end = GetSegmentAttr(start, SEGATTR_END)
        AnalyzeArea(start, end)

########NEW FILE########
__FILENAME__ = idpy-ios-kernel-fix-thumb-segments
# idpy-ios-kernel-fix-thumb-segments.py ~pod2g 2013

from idaapi import *
from idc import *

for seg in Segments():
	start = seg
	if Word(start) & 0xff00 == 0xb500 and GetReg(seg, "T") == 0:
                print "Switching from ARM to THUMB for segment: 0x%X" % seg;
		MakeUnkn(start, 1);
		for i in range (seg, seg + 0x40):
			SetReg(i, "T", 1);
		MakeCode(start);


########NEW FILE########
__FILENAME__ = iokit
from idaapi import *
from idc import *
import idautils


def old_do_pointers():
	for seg_ea in Segments():
		name = SegName(seg_ea)
		if not name.endswith("__const"):
			continue
		print name
		seg_end = SegEnd(seg_ea)
		print name,seg_end
		i = seg_ea
		while i < seg_end:
			dw = Dword(i)
			if dw & 0x80000000 == 0x80000000:
				if SegName(dw):
					OpOffset(i, 0)
			i += 4

#good enough for ios6 kernel
def backtrack(ea, reg):
	track = reg
	while ea!=BADADDR:
		if GetDisasm(ea).startswith("PUSH"):
			break
		mnem = idc.GetMnem(ea)
		op0 = idc.GetOperandValue(ea,0)
		op1 = idc.GetOperandValue(ea,1)
		if op0 == track:
			xrefs = list(DataRefsFrom(ea))
			if len(xrefs):
				return xrefs[0]
			if idc.GetOpType(ea,1) == o_reg: #1=register
				track= op1
			else:
				return op1
		ea=PrevHead(ea)
	return None
	
def find_args(ea):
	r0 = backtrack(ea, 0)
	r1 = backtrack(ea, 1)
	r2 = backtrack(ea, 2)
	r3 = backtrack(ea, 3)

	if not None in [r0, r1, r2, r3]:
		name = GetString(r1)
		parent_meta = r2
		if r2 != 0 and SegName(r2).endswith("__nl_symbol_ptr"):
			#print "deref for class %s" % name
			parent_meta = Dword(r2)
		current_meta = r0
		if r0 != 0 and SegName(r0).endswith("__nl_symbol_ptr"):
			#print "xxderef for class %s" % name
			current_meta = Dword(r0)
		return name, parent_meta, r3, current_meta
	return None, None, None, None

class IOKitInspector(object):
	def __init__(self):
		self.classes = {}
		
	def find_class_by_name(self, name):
		for c in self.classes.values():
			if c["name"] == name:
				return c

	def print_inheritance(self, name):
		print " => ".join(self.get_parents(name))

	def is_userclient(self, name):
		return "IOUserClient" in self.get_parents(name)

	def get_parents(self, name):
		parents = []
		c = self.find_class_by_name(name)
		while c:
			parents.append(c["name"])
			c = self.classes.get(c["parentMeta"])
		return parents

	def doStuff(self, xref):
		name, parent, sz, current = find_args(xref)

		if not name or current == 0x0 or parent == -1:
			return
		if self.classes.has_key(current):
			print "duplicate %s" % name
			return
		c = {"name": name, "meta": current, "parentMeta": parent, "size": sz}
		#print c
		self.classes[current] = c

	def find_vtable(self, name):
		c = self.find_class_by_name(name)
		for xref in DataRefsTo(c["meta"]):
			disas = GetDisasm(xref)
			if not disas.split()[1].replace(",","") == "R0":
				continue
			next= GetDisasm(NextHead(xref))
			if next.startswith("BX              LR"):
				refs = list(DataRefsTo(xref-2))#hax ios 6thumb
				#print refs, "%x" % xref
				if len(refs) != 1:
					return
				vtable = refs[0] - 7*4
				print "%s_getMetaClass %x" % (name, xref-2)
				print "%s vtable %x" % (name, vtable)
				return vtable
				
	def searchClasses(self):
		self.classes = {}

		OSMetaClassConstructor = LocByName("__ZN11OSMetaClassC2EPKcPKS_j")

		for xref in CodeRefsTo(OSMetaClassConstructor, 0):
			self.doStuff(xref)
		
		for dxref in DataRefsTo(OSMetaClassConstructor):
			for stub_xref in DataRefsTo(dxref):
				f = GetFunctionName(stub_xref)
				#-10=hax based on stub instruction size
				for xref in CodeRefsTo(stub_xref-10, 0):
					self.doStuff(xref)

		print "%d classes found" % len(self.classes)
		return
		for c in self.classes.values():
			self.print_inheritance(c["name"])
			self.fix_vtable(c["name"])
			#vtable = find_vtable(meta)
			#print name,  "%x" % xref, "%x" % meta#, "%x" % vtable
			#fix_vtable(name, meta)

	def fix_vtable(self, classname):
		parents = self.get_parents(classname)
		last_vtable = None
		last_class = None
		names = {}
		for cn in reversed(parents):
			print cn
			vtable = self.find_vtable(cn)
			if not vtable:
				print "Vtable fail %s" % cn
				continue
			print "%x" % vtable
			vt = get_null_terminated_array(vtable)
			if last_vtable and len(last_vtable) > len(vt):
				print "wut %d %d" % (len(last_vtable) , len(vt))
			for i in xrange(len(vt)):
				fname = GetFunctionName(vt[i])
				if not fname.startswith("sub_"):
					continue
				if last_vtable and i < len(last_vtable):
					if last_vtable[i] != vt[i]:
						parent_fname = GetFunctionName(last_vtable[i])
						demangled = Demangle(parent_fname, GetLongPrm(INF_LONG_DN))
						if demangled:
							proto = demangled_to_proto(demangled, cn)
							print fname, " => ", proto
							print SetType(vt[i] & ~1, proto)
							newname = proto.split("(")[0].split()[1]
							names[newname] = names.get(newname, -1) + 1
							newname += "_" * names[newname]
							MakeName(vt[i] & ~1, newname)
						else:
							print parent_fname, fname
			last_vtable = vt
			last_class = cn

	def make_vtable_struct(self, c):
		vtable = self.find_vtable(c["name"])
		vt = get_null_terminated_array(vtable)
		x = []
		names = {}
		for fptr in vt:
			fname = get_function_name(fptr)
			zz = fname.split(")(")[0]
			names[zz] = names.get(zz, -1) + 1
			z = zz + "_" * names[zz]
			fname = fname.replace(zz, z)
			x.append(("uint32_t", fname))
		s = print_struct("%s_vtable" % c["name"], x)
		print s
		idc.ParseTypes(s, 0)
		
	def make_structs(self, classname):
		parents = self.get_parents(classname)
		parent_size = 4
		parent_name = None
		for cn in reversed(parents):
			c = self.find_class_by_name(cn)
			s1 = "_%s" % cn
			s2 = "%s" % cn
			sz = c["size"] - parent_size
			m1 = [("uint32_t", "var%d" % i) for i in xrange(sz/4)]
			if parent_name:
				m1 = [("_%s" % parent_name, parent_name.lower())] + m1

			ss1 = print_struct(s1, m1)
			idc.ParseTypes(ss1, 0)
			print ss1
			m2 = [("%s_vtable*" % cn, "vtable")]
			m2.append((s1, "m"))
			print "//sizeof=%d" % c["size"]
			ss2 = print_struct(s2, m2)
			idc.ParseTypes(ss2, 0)
			print ss2
			parent_size = c["size"]
			parent_name = cn
		
	def make_forward(self):
		stuff = ["OSMetaClassBase",
				"IOPMPowerState",
				"semaphore",
				"ipc_port",
				"task",
				"upl_page_info",
				"IOInterruptVector"]
		txt = "\n".join(map(lambda x:"struct %s;"%x, stuff))
		for c in self.classes.values():
			txt += "struct %s;\n" % c["name"]
		idc.ParseTypes(txt, 0)
		print txt

	def do_class(self, name):
		c = self.find_class_by_name(name)
		self.make_vtable_struct(c)
		self.make_structs(c["name"])
		self.fix_vtable(c["name"])
		
def sanitize_function_name(x):
	return x.replace("const", "").replace("~", "destructor_")
	
def get_function_name(ea):
	fname = GetFunctionName(ea)
	demangled = Demangle(fname, GetLongPrm(INF_LONG_DN))
	if demangled:
		x = demangled.split("::")[1]
		z = "(*%s)(%s" % (x.split("(",1)[0], x.split("(",1)[1])
		return sanitize_function_name(z)
	return fname
	
def demangled_to_proto(demangled, classname):
	p = demangled.split("::")[1]
	method, params = p.split("(", 1)
	p = "%s*" % classname
	if params.split(")")[0].strip() != "":
		p += ", %s" % params
	else:
		p += ")"
	res = "uint32_t %s__%s(%s;" % (classname, method, p)
	return sanitize_function_name(res)
	
def print_struct(name, members):
	txt = "typedef struct %s{\n" % name
	for t,n in members:
		txt += "\t%s %s;\n" % (t,n)
	txt += "} %s;\n\n" % name
	return txt
		
def get_null_terminated_array(ea):
	r = []
	while True:
		x = Dword(ea)
		if x == 0:
			break
		r.append(x)
		ea += 4
	return r

def func_name_to_label(f):
	z = f.split("::")
	return "%s_%s" % (z[0], z[1].split("(")[0])

iok = IOKitInspector()
iok.searchClasses()

#iok.print_inheritance("AppleIOPFMI")
#iok.print_inheritance("IOFlashControllerUserClient")
#iok.print_inheritance("AppleMultitouchSPIUserClient")
#iok.make_forward()

########NEW FILE########
__FILENAME__ = rename_stubs
from idaapi import *
from idc import *
import idautils

for seg_ea in Segments():
	name = SegName(seg_ea)
	if name.endswith("__nl_symbol_ptr"):
		
		s = get_segm_by_name(name)
		#https://www.hex-rays.com/products/decompiler/manual/tricks.shtml#02
		set_segm_class(s, "CODE")
		
		seg_end = SegEnd(seg_ea)
		i = seg_ea
		while i < seg_end:
			name = GetFunctionName(Dword(i))
			if name != "":
				print name
				for xref in list(DataRefsTo(i))[:1]:
					MakeName(xref, "_%s_stub_%x" % (name, i))
			i+=4
	

########NEW FILE########
__FILENAME__ = sandbox_mac_policy_ops
from idaapi import *
from idc import *
import idautils

def register_mac_policy():
	macpolicy = """
struct mac_policy_ops {
	int		*mpo_audit_check_postselect;
	int		*mpo_audit_check_preselect;
	int		*mpo_bpfdesc_label_associate;
	int		*mpo_bpfdesc_label_destroy;
	int		*mpo_bpfdesc_label_init;
	int		*mpo_bpfdesc_check_receive;
	int		*mpo_cred_check_label_update_execve;
	int		*mpo_cred_check_label_update;
	int		*mpo_cred_check_visible;
	int		*mpo_cred_label_associate_fork;
	int		*mpo_cred_label_associate_kernel;
	int		*mpo_cred_label_associate;
	int		*mpo_cred_label_associate_user;
	int		*mpo_cred_label_destroy;
	int		*mpo_cred_label_externalize_audit;
	int		*mpo_cred_label_externalize;
	int		*mpo_cred_label_init;
	int		*mpo_cred_label_internalize;
	int		*mpo_cred_label_update_execve;
	int		*mpo_cred_label_update;
	int		*mpo_devfs_label_associate_device;
	int		*mpo_devfs_label_associate_directory;
	int		*mpo_devfs_label_copy;
	int		*mpo_devfs_label_destroy;
	int		*mpo_devfs_label_init;
	int		*mpo_devfs_label_update;
	int		*mpo_file_check_change_offset;
	int		*mpo_file_check_create;
	int		*mpo_file_check_dup;
	int		*mpo_file_check_fcntl;
	int		*mpo_file_check_get_offset;
	int		*mpo_file_check_get;
	int		*mpo_file_check_inherit;
	int		*mpo_file_check_ioctl;
	int		*mpo_file_check_lock;
	int		*mpo_file_check_mmap_downgrade;
	int		*mpo_file_check_mmap;
	int		*mpo_file_check_receive;
	int		*mpo_file_check_set;
	int		*mpo_file_label_init;
	int		*mpo_file_label_destroy;
	int		*mpo_file_label_associate;
	int		*mpo_ifnet_check_label_update;
	int		*mpo_ifnet_check_transmit;
	int		*mpo_ifnet_label_associate;
	int		*mpo_ifnet_label_copy;
	int		*mpo_ifnet_label_destroy;
	int		*mpo_ifnet_label_externalize;
	int		*mpo_ifnet_label_init;
	int		*mpo_ifnet_label_internalize;
	int		*mpo_ifnet_label_update;
	int		*mpo_ifnet_label_recycle;
	int		*mpo_inpcb_check_deliver;
	int		*mpo_inpcb_label_associate;
	int		*mpo_inpcb_label_destroy;
	int		*mpo_inpcb_label_init;
	int		*mpo_inpcb_label_recycle;
	int		*mpo_inpcb_label_update;
	int		*mpo_iokit_check_device;
	int		*mpo_ipq_label_associate;
	int		*mpo_ipq_label_compare;
	int		*mpo_ipq_label_destroy;
	int		*mpo_ipq_label_init;
	int		*mpo_ipq_label_update;
	int		*mpo_lctx_check_label_update;
	int		*mpo_lctx_label_destroy;
	int		*mpo_lctx_label_externalize;
	int		*mpo_lctx_label_init;
	int		*mpo_lctx_label_internalize;
	int		*mpo_lctx_label_update;
	int		*mpo_lctx_notify_create;
	int		*mpo_lctx_notify_join;
	int		*mpo_lctx_notify_leave;
	int		*mpo_mbuf_label_associate_bpfdesc;
	int		*mpo_mbuf_label_associate_ifnet;
	int		*mpo_mbuf_label_associate_inpcb;
	int		*mpo_mbuf_label_associate_ipq;
	int		*mpo_mbuf_label_associate_linklayer;
	int 	*mpo_mbuf_label_associate_multicast_encap;
	int		*mpo_mbuf_label_associate_netlayer;
	int		*mpo_mbuf_label_associate_socket;
	int		*mpo_mbuf_label_copy;
	int		*mpo_mbuf_label_destroy;
	int		*mpo_mbuf_label_init;
	int		*mpo_mount_check_fsctl;
	int		*mpo_mount_check_getattr;
	int		*mpo_mount_check_label_update;
	int		*mpo_mount_check_mount;
	int		*mpo_mount_check_remount;
	int		*mpo_mount_check_setattr;
	int		*mpo_mount_check_stat;
	int		*mpo_mount_check_umount;
	int		*mpo_mount_label_associate;
	int		*mpo_mount_label_destroy;
	int		*mpo_mount_label_externalize;
	int		*mpo_mount_label_init;
	int		*mpo_mount_label_internalize;
	int		*mpo_netinet_fragment;
	int		*mpo_netinet_icmp_reply;
	int		*mpo_netinet_tcp_reply;
	int		*mpo_pipe_check_ioctl;
	int		*mpo_pipe_check_kqfilter;
	int		*mpo_pipe_check_label_update;
	int		*mpo_pipe_check_read;
	int		*mpo_pipe_check_select;
	int		*mpo_pipe_check_stat;
	int		*mpo_pipe_check_write;
	int		*mpo_pipe_label_associate;
	int		*mpo_pipe_label_copy;
	int		*mpo_pipe_label_destroy;
	int		*mpo_pipe_label_externalize;
	int		*mpo_pipe_label_init;
	int		*mpo_pipe_label_internalize;
	int		*mpo_pipe_label_update;
	int		*mpo_policy_destroy;
	int		*mpo_policy_init;
	int		*mpo_policy_initbsd;
	int		*mpo_policy_syscall;
	int		*mpo_port_check_copy_send;
	int		*mpo_port_check_hold_receive;
	int		*mpo_port_check_hold_send_once;
	int		*mpo_port_check_hold_send;
	int		*mpo_port_check_label_update;
	int		*mpo_port_check_make_send_once;
	int		*mpo_port_check_make_send;
	int		*mpo_port_check_method;
	int		*mpo_port_check_move_receive;
	int		*mpo_port_check_move_send_once;
	int		*mpo_port_check_move_send;
	int		*mpo_port_check_receive;
	int		*mpo_port_check_send;
	int		*mpo_port_check_service;
	int		*mpo_port_label_associate_kernel;
	int		*mpo_port_label_associate;
	int		*mpo_port_label_compute;
	int		*mpo_port_label_copy;
	int		*mpo_port_label_destroy;
	int		*mpo_port_label_init;
	int		*mpo_port_label_update_cred;
	int		*mpo_port_label_update_kobject;
	int		*mpo_posixsem_check_create;
	int		*mpo_posixsem_check_open;
	int		*mpo_posixsem_check_post;
	int		*mpo_posixsem_check_unlink;
	int		*mpo_posixsem_check_wait;
	int		*mpo_posixsem_label_associate;
	int		*mpo_posixsem_label_destroy;
	int		*mpo_posixsem_label_init;
	int		*mpo_posixshm_check_create;
	int		*mpo_posixshm_check_mmap;
	int		*mpo_posixshm_check_open;
	int		*mpo_posixshm_check_stat;
	int		*mpo_posixshm_check_truncate;
	int		*mpo_posixshm_check_unlink;
	int		*mpo_posixshm_label_associate;
	int		*mpo_posixshm_label_destroy;
	int		*mpo_posixshm_label_init;
	int		*mpo_proc_check_debug;
	int		*mpo_proc_check_fork;
	int		*mpo_proc_check_get_task_name;
	int		*mpo_proc_check_get_task;
	int		*mpo_proc_check_getaudit;
	int		*mpo_proc_check_getauid;
	int		*mpo_proc_check_getlcid;
	int		*mpo_proc_check_mprotect;
	int		*mpo_proc_check_sched;
	int		*mpo_proc_check_setaudit;
	int		*mpo_proc_check_setauid;
	int		*mpo_proc_check_setlcid;
	int		*mpo_proc_check_signal;
	int		*mpo_proc_check_wait;
	int		*mpo_proc_label_destroy;
	int		*mpo_proc_label_init;
	int		*mpo_socket_check_accept;
	int		*mpo_socket_check_accepted;
	int		*mpo_socket_check_bind;
	int		*mpo_socket_check_connect;
	int		*mpo_socket_check_create;
	int		*mpo_socket_check_deliver;
	int		*mpo_socket_check_kqfilter;
	int		*mpo_socket_check_label_update;
	int		*mpo_socket_check_listen;
	int		*mpo_socket_check_receive;
	int		*mpo_socket_check_received;
	int		*mpo_socket_check_select;
	int		*mpo_socket_check_send;
	int		*mpo_socket_check_stat;
	int		*mpo_socket_check_setsockopt;
	int		*mpo_socket_check_getsockopt;
	int		*mpo_socket_label_associate_accept;
	int		*mpo_socket_label_associate;
	int		*mpo_socket_label_copy;
	int		*mpo_socket_label_destroy;
	int		*mpo_socket_label_externalize;
	int		*mpo_socket_label_init;
	int		*mpo_socket_label_internalize;
	int		*mpo_socket_label_update;
	int		*mpo_socketpeer_label_associate_mbuf;
	int		*mpo_socketpeer_label_associate_socket;
	int		*mpo_socketpeer_label_destroy;
	int		*mpo_socketpeer_label_externalize;
	int		*mpo_socketpeer_label_init;
	int		*mpo_system_check_acct;
	int		*mpo_system_check_audit;
	int		*mpo_system_check_auditctl;
	int		*mpo_system_check_auditon;
	int		*mpo_system_check_host_priv;
	int		*mpo_system_check_nfsd;
	int		*mpo_system_check_reboot;
	int		*mpo_system_check_settime;
	int		*mpo_system_check_swapoff;
	int		*mpo_system_check_swapon;
	int		*mpo_system_check_sysctl;
	int		*mpo_sysvmsg_label_associate;
	int		*mpo_sysvmsg_label_destroy;
	int		*mpo_sysvmsg_label_init;
	int		*mpo_sysvmsg_label_recycle;
	int		*mpo_sysvmsq_check_enqueue;
	int		*mpo_sysvmsq_check_msgrcv;
	int		*mpo_sysvmsq_check_msgrmid;
	int		*mpo_sysvmsq_check_msqctl;
	int		*mpo_sysvmsq_check_msqget;
	int		*mpo_sysvmsq_check_msqrcv;
	int		*mpo_sysvmsq_check_msqsnd;
	int		*mpo_sysvmsq_label_associate;
	int		*mpo_sysvmsq_label_destroy;
	int		*mpo_sysvmsq_label_init;
	int		*mpo_sysvmsq_label_recycle;
	int		*mpo_sysvsem_check_semctl;
	int		*mpo_sysvsem_check_semget;
	int		*mpo_sysvsem_check_semop;
	int		*mpo_sysvsem_label_associate;
	int		*mpo_sysvsem_label_destroy;
	int		*mpo_sysvsem_label_init;
	int		*mpo_sysvsem_label_recycle;
	int		*mpo_sysvshm_check_shmat;
	int		*mpo_sysvshm_check_shmctl;
	int		*mpo_sysvshm_check_shmdt;
	int		*mpo_sysvshm_check_shmget;
	int		*mpo_sysvshm_label_associate;
	int		*mpo_sysvshm_label_destroy;
	int		*mpo_sysvshm_label_init;
	int		*mpo_sysvshm_label_recycle;
	int		*mpo_task_label_associate_kernel;
	int		*mpo_task_label_associate;
	int		*mpo_task_label_copy;
	int		*mpo_task_label_destroy;
	int		*mpo_task_label_externalize;
	int		*mpo_task_label_init;
	int		*mpo_task_label_internalize;
	int		*mpo_task_label_update;
	int		*mpo_iokit_check_hid_control;
	int		*mpo_vnode_check_access;
	int		*mpo_vnode_check_chdir;
	int		*mpo_vnode_check_chroot;
	int		*mpo_vnode_check_create;
	int		*mpo_vnode_check_deleteextattr;
	int		*mpo_vnode_check_exchangedata;
	int		*mpo_vnode_check_exec;
	int		*mpo_vnode_check_getattrlist;
	int		*mpo_vnode_check_getextattr;
	int		*mpo_vnode_check_ioctl;
	int		*mpo_vnode_check_kqfilter;
	int		*mpo_vnode_check_label_update;
	int		*mpo_vnode_check_link;
	int		*mpo_vnode_check_listextattr;
	int		*mpo_vnode_check_lookup;
	int		*mpo_vnode_check_open;
	int		*mpo_vnode_check_read;
	int		*mpo_vnode_check_readdir;
	int		*mpo_vnode_check_readlink;
	int		*mpo_vnode_check_rename_from;
	int		*mpo_vnode_check_rename_to;
	int		*mpo_vnode_check_revoke;
	int		*mpo_vnode_check_select;
	int		*mpo_vnode_check_setattrlist;
	int		*mpo_vnode_check_setextattr;
	int		*mpo_vnode_check_setflags;
	int		*mpo_vnode_check_setmode;
	int		*mpo_vnode_check_setowner;
	int		*mpo_vnode_check_setutimes;
	int		*mpo_vnode_check_stat;
	int		*mpo_vnode_check_truncate;
	int		*mpo_vnode_check_unlink;
	int		*mpo_vnode_check_write;
	int		*mpo_vnode_label_associate_devfs;
	int		*mpo_vnode_label_associate_extattr;
	int		*mpo_vnode_label_associate_file;
	int		*mpo_vnode_label_associate_pipe;
	int		*mpo_vnode_label_associate_posixsem;
	int		*mpo_vnode_label_associate_posixshm;
	int		*mpo_vnode_label_associate_singlelabel;
	int		*mpo_vnode_label_associate_socket;
	int		*mpo_vnode_label_copy;
	int		*mpo_vnode_label_destroy;
	int		*mpo_vnode_label_externalize_audit;
	int		*mpo_vnode_label_externalize;
	int		*mpo_vnode_label_init;
	int		*mpo_vnode_label_internalize;
	int		*mpo_vnode_label_recycle;
	int		*mpo_vnode_label_store;
	int		*mpo_vnode_label_update_extattr;
	int		*mpo_vnode_label_update;
	int		*mpo_vnode_notify_create;
	int		*mpo_vnode_check_signature;
	int		*mpo_vnode_check_uipc_bind;
	int		*mpo_vnode_check_uipc_connect;
	int		*mpo_proc_check_run_cs_invalid;
	int		*mpo_proc_check_suspend_resume;
	int		*mpo_thread_userret;
	int		*mpo_iokit_check_set_properties;
	int		*mpo_system_check_chud;
	int		*mpo_vnode_check_searchfs;
	int		*mpo_priv_check;
	int		*mpo_priv_grant;
	int		*mpo_proc_check_map_anon;
	int		*mpo_vnode_check_fsgetpath;
	int		*mpo_iokit_check_open;
 	int		*mpo_proc_check_ledger;
	int		*mpo_vnode_notify_rename;
	int		*mpo_thread_label_init;
	int		*mpo_thread_label_destroy;
	int		*mpo_system_check_kas_info;
	int		*mpo_reserved18;
	int		*mpo_reserved19;
	int		*mpo_reserved20;
	int		*mpo_reserved21;
	int		*mpo_reserved22;
	int		*mpo_reserved23;
	int		*mpo_reserved24;
	int		*mpo_reserved25;
	int		*mpo_reserved26;
	int		*mpo_reserved27;
	int		*mpo_reserved28;
	int		*mpo_reserved29;
};

struct mac_policy_conf {
   const char *mpc_name; /** policy name */
   const char *mpc_fullname; /** full name */
   const char **mpc_labelnames; /** managed label namespaces */
   unsigned int mpc_labelname_count; /** number of managed label namespaces
   */
   struct mac_policy_ops *mpc_ops; /** operation vector */
   int mpc_loadtime_flags; /** load time flags */
   int *mpc_field_off; /** label slot */
   int mpc_runtime_flags; /** run time flags */
   void* mpc_list; /** List reference */
   void *mpc_data; /** module data */
};

int mac_policy_register(
   struct mac_policy_conf *mpc,
   void *handlep,
   void *xd);
   
"""
	idc.ParseTypes(macpolicy, 0)
	
def fix_policy_ops_names(struct_addr, nameprefix):
	idx, sid, name = [x for x in Structs() if x[2] == "mac_policy_ops"][0]

	for offset, field_name, sz in StructMembers(sid):
		d = Dword(struct_addr+offset)
		if d != 0:
			n = Name(d & ~1)
			if n.startswith("sub_") or n.startswith("loc_"):
				newname = "%s_%s" % (nameprefix, field_name)
				print "Renaming %s to %s" % (n, newname)
				MakeName(d & ~1, newname)

mac_policy_ops = GetStrucIdByName("mac_policy_ops")
if mac_policy_ops == 0xffffffff:
	register_mac_policy()

for seg_ea in Segments():
	name = SegName(seg_ea)
	if name == "com.apple.security.sandbox:__data":
		seg_end = SegEnd(seg_ea)
		i = seg_ea
		while i < seg_end:
			x = GetString(Dword(i))
			if x == "Seatbelt sandbox policy":
				mpc_ops = Dword(i+12)
				print "Found sandbox mpc_ops at 0x%x" % mpc_ops
				MakeStructEx(mpc_ops, -1, "mac_policy_ops")
				fix_policy_ops_names(mpc_ops, "sb")
			i+=4
	

########NEW FILE########
