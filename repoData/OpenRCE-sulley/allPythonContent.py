__FILENAME__ = fuzz_trend_control_manager_20901
#!c:\\python\\python.exe

#
# pedram amini <pamini@tippingpoint.com>
#
# this was a really half assed fuzz. someone should take it further, see my notes in the requests file for more info.
#

from sulley   import *
from requests import trend

########################################################################################################################
sess = sessions.session(session_filename="audits/trend_server_protect_20901.session", sleep_time=.25, log_level=10)
sess.add_target(sessions.target("192.168.181.2", 20901))

sess.connect(s_get("20901"))
sess.fuzz()

########NEW FILE########
__FILENAME__ = fuzz_trend_server_protect_5168
#!c:\\python\\python.exe

#
# pedram amini <pamini@tippingpoint.com>
#
# on vmware:
#     cd shared\sulley\branches\pedram
#     process_monitor.py -c audits\trend_server_protect_5168.crashbin -p SpntSvc.exe
#     network_monitor.py -d 1 -f "src or dst port 5168" -p audits\trend_server_protect_5168
#
# on localhost:
#     vmcontrol.py -r "c:\Progra~1\VMware\VMware~1\vmrun.exe" -x "v:\vmfarm\images\windows\2000\win_2000_pro-clones\TrendM~1\win_2000_pro.vmx" --snapshot "sulley ready and waiting"
#
# this key gets written which fucks trend service even on reboot.
# HKEY_LOCAL_MACHINE\SOFTWARE\TrendMicro\ServerProtect\CurrentVersion\Engine
#
# uncomment the req/num to do a single test case.
#

import time

from sulley   import *
from requests import trend

req = num = None
#req = "5168: op-3"
#num = "\x04"

def rpc_bind (sock):
    bind = utils.dcerpc.bind("25288888-bd5b-11d1-9d53-0080c83a5c2c", "1.0")
    sock.send(bind)

    utils.dcerpc.bind_ack(sock.recv(1000))


def do_single (req, num):
    import socket

    # connect to the server.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("192.168.181.133", 5168))

    # send rpc bind.
    rpc_bind(s)

    request = s_get(req)

    while 1:
        if request.names["subs"].value == num:
            break

        s_mutate()

    print "xmitting single test case"
    s.send(s_render())
    print "done."


def do_fuzz ():
    sess   = sessions.session(session_filename="audits/trend_server_protect_5168.session")
    target = sessions.target("192.168.181.133", 5168)

    target.netmon    = pedrpc.client("192.168.181.133", 26001)
    target.procmon   = pedrpc.client("192.168.181.133", 26002)
    target.vmcontrol = pedrpc.client("127.0.0.1",       26003)

    target.procmon_options = \
    {
        "proc_name"      : "SpntSvc.exe",
        "stop_commands"  : ['net stop "trend serverprotect"'],
        "start_commands" : ['net start "trend serverprotect"'],
    }

    # start up the target.
    target.vmcontrol.restart_target()

    print "virtual machine up and running"

    sess.add_target(target)
    sess.pre_send = rpc_bind
    sess.connect(s_get("5168: op-1"))
    sess.connect(s_get("5168: op-2"))
    sess.connect(s_get("5168: op-3"))
    sess.connect(s_get("5168: op-5"))
    sess.connect(s_get("5168: op-a"))
    sess.connect(s_get("5168: op-1f"))
    sess.fuzz()

    print "done fuzzing. web interface still running."


if not req or not num:
    do_fuzz()
else:
    do_single(req, num)
########NEW FILE########
__FILENAME__ = fuzz_trillian_jabber
#!c:\\python\\python.exe

#
# pedram amini <pamini@tippingpoint.com>
#
# on vmware:
#     cd shared\sulley\branches\pedram
#     network_monitor.py -d 1 -f "src or dst port 5298" -p audits\trillian_jabber
#     process_monitor.py -c audits\trillian_jabber.crashbin -p trillian.exe
#
# on localhost:
#     vmcontrol.py -r "c:\Progra~1\VMware\VMware~1\vmrun.exe" -x "v:\vmfarm\images\windows\xp\win_xp_pro-clones\allsor~1\win_xp_pro.vmx" --snapshot "sulley ready and waiting"
#
# note:
#     you MUST register the IP address of the fuzzer as a valid MDNS "presence" host. to do so, simply install and
#     launch trillian on the fuzz box with rendezvous enabled. otherwise the target will drop the connection.
#

from sulley   import *
from requests import jabber

def init_message (sock):
    init  = '<?xml version="1.0" encoding="UTF-8" ?>\n'
    init += '<stream:stream to="152.67.137.126" xmlns="jabber:client" xmlns:stream="http://etherx.jabber.org/streams">'

    sock.send(init)
    sock.recv(1024)

sess                   = sessions.session(session_filename="audits/trillian.session")
target                 = sessions.target("152.67.137.126", 5298)
target.netmon          = pedrpc.client("152.67.137.126", 26001)
target.procmon         = pedrpc.client("152.67.137.126", 26002)
target.vmcontrol       = pedrpc.client("127.0.0.1",      26003)
target.procmon_options = { "proc_name" : "trillian.exe" }

# start up the target.
target.vmcontrol.restart_target()
print "virtual machine up and running"

sess.add_target(target)
sess.pre_send = init_message
sess.connect(sess.root, s_get("chat message"))
sess.fuzz()

########NEW FILE########
__FILENAME__ = mdns
#!/usr/bin/python

# A partial MDNS fuzzer.  Could be made to be a DNS fuzzer trivially
# Charlie Miller <cmiller@securityevaluators.com>

from sulley   import *
from binascii import *
from struct import *

def insert_questions (sess, node, edge, sock):
	node.names['Questions'].value = 1+node.names['queries'].current_reps
        node.names['Authority'].value = 1+node.names['auth_nameservers'].current_reps

s_initialize("query")
s_word(0, name="TransactionID")
s_word(0, name="Flags")
s_word(1, name="Questions", endian='>')
s_word(0, name="Answer", endian='>')
s_word(1, name="Authority", endian='>')
s_word(0, name="Additional", endian='>')

######### Queries ################
if s_block_start("query"):
	if s_block_start("name_chunk"): 
		s_size("string", length=1)
		if s_block_start("string"):
			s_string("A"*10)
		s_block_end()
	s_block_end()
	s_repeat("name_chunk", min_reps=2, max_reps=4, step=1, fuzzable=True, name="aName")

	s_group("end", values=["\x00", "\xc0\xb0"])   # very limited pointer fuzzing
	s_word(0xc, name="Type", endian='>')
	s_word(0x8001, name="Class", endian='>')
s_block_end()
s_repeat("query", 0, 1000, 40, name="queries")


######## Authorities ############
if s_block_start("auth_nameserver"):
	if s_block_start("name_chunk_auth"):
	        s_size("string_auth", length=1)
	        if s_block_start("string_auth"):
	                s_string("A"*10)
	        s_block_end()
	s_block_end()
	s_repeat("name_chunk_auth", min_reps=2, max_reps=4, step=1, fuzzable=True, name="aName_auth")
	s_group("end_auth", values=["\x00", "\xc0\xb0"])   # very limited pointer fuzzing

	s_word(0xc, name="Type_auth", endian='>')
	s_word(0x8001, name="Class_auth", endian='>')
	s_dword(0x78, name="TTL_auth", endian='>')
	s_size("data_length", length=2, endian='>')
	if s_block_start("data_length"):
		s_binary("00 00 00 00 00 16 c0 b0")      # This should be fuzzed according to the type, but I'm too lazy atm
	s_block_end()
s_block_end()
s_repeat("auth_nameserver", 0, 1000, 40, name="auth_nameservers")

s_word(0)

sess                   = sessions.session(proto="udp")
target                 = sessions.target("224.0.0.251", 5353)
sess.add_target(target)
sess.connect(s_get("query"), callback=insert_questions )

sess.fuzz()


########NEW FILE########
__FILENAME__ = network_monitor
#!c:\\python\\python.exe

import threading
import getopt
import time
import sys
import os

from sulley import pedrpc

import pcapy
import impacket
import impacket.ImpactDecoder

PORT  = 26001
IFS   = []
ERR   = lambda msg: sys.stderr.write("ERR> " + msg + "\n") or sys.exit(1)
USAGE = "USAGE: network_monitor.py"                                                                \
        "\n    <-d|--device DEVICE #>    device to sniff on (see list below)"                      \
        "\n    [-f|--filter PCAP FILTER] BPF filter string"                                        \
        "\n    [-P|--log_path PATH]      log directory to store pcaps to"                          \
        "\n    [-l|--log_level LEVEL]    log level (default 1), increase for more verbosity"       \
        "\n    [--port PORT]             TCP port to bind this agent to"                           \
        "\n\nNetwork Device List:\n"

# add the device list to the usage string.
i = 0
for dev in pcapy.findalldevs():
    IFS.append(dev)

    # if we are on windows, try and resolve the device UUID into an IP address.
    if sys.platform.startswith("win"):
        import _winreg

        try:
            # extract the device UUID and open the TCP/IP parameters key for it.
            dev    = dev[dev.index("{"):dev.index("}")+1]
            subkey = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\%s" % dev
            key    = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, subkey)

            # if there is a DHCP address snag that, otherwise fall back to the IP address.
            try:    ip = _winreg.QueryValueEx(key, "DhcpIPAddress")[0]
            except: ip = _winreg.QueryValueEx(key, "IPAddress")[0][0]

            dev = dev + "\t" + ip
        except:
            pass

    USAGE += "    [%d] %s\n" % (i, dev)
    i += 1


########################################################################################################################
class pcap_thread (threading.Thread):
    def __init__ (self, network_monitor, pcap, pcap_save_path):
        self.network_monitor = network_monitor
        self.pcap            = pcap

        self.decoder         = None
        self.dumper          = self.pcap.dump_open(pcap_save_path)
        self.active          = True
        self.data_bytes      = 0

        # register the appropriate decoder.
        if pcap.datalink() == pcapy.DLT_EN10MB:
            self.decoder = impacket.ImpactDecoder.EthDecoder()
        elif pcap.datalink() == pcapy.DLT_LINUX_SLL:
            self.decoder = impacket.ImpactDecoder.LinuxSLLDecoder()
        else:
            raise Exception

        threading.Thread.__init__(self)


    def packet_handler (self, header, data):
        # add the captured data to the PCAP.
        self.dumper.dump(header, data)

        # increment the captured byte count.
        self.data_bytes += len(data)

        # log the decoded data at the appropriate log level.
        self.network_monitor.log(self.decoder.decode(data), 15)


    def run (self):
        # process packets while the active flag is raised.
        while self.active:
            self.pcap.dispatch(0, self.packet_handler)


########################################################################################################################
class network_monitor_pedrpc_server (pedrpc.server):
    def __init__ (self, host, port, device, filter="", log_path="./", log_level=1):
        '''
        @type  host:        String
        @param host:        Hostname or IP address to bind server to
        @type  port:        Integer
        @param port:        Port to bind server to
        @type  device:      String
        @param device:      Name of device to capture packets on
        @type  ignore_pid:  Integer
        @param ignore_pid:  (Optional, def=None) Ignore this PID when searching for the target process
        @type  log_path:    String
        @param log_path:    (Optional, def="./") Path to save recorded PCAPs to
        @type  log_level:   Integer
        @param log_level:   (Optional, def=1) Log output level, increase for more verbosity
        '''

        # initialize the PED-RPC server.
        pedrpc.server.__init__(self, host, port)

        self.device      = device
        self.filter      = filter
        self.log_path    = log_path
        self.log_level   = log_level

        self.pcap        = None
        self.pcap_thread = None

        # ensure the log path is valid.
        if not os.access(self.log_path, os.X_OK):
            self.log("invalid log path: %s" % self.log_path)
            raise Exception

        self.log("Network Monitor PED-RPC server initialized:")
        self.log("\t device:    %s" % self.device)
        self.log("\t filter:    %s" % self.filter)
        self.log("\t log path:  %s" % self.log_path)
        self.log("\t log_level: %d" % self.log_level)
        self.log("Awaiting requests...")


    def __stop (self):
        '''
        Kill the PCAP thread.
        '''

        if self.pcap_thread:
            self.log("stopping active packet capture thread.", 10)

            self.pcap_thread.active = False
            self.pcap_thread        = None


    def alive (self):
        '''
        Returns True. Useful for PED-RPC clients who want to see if the PED-RPC connection is still alive.
        '''

        return True


    def post_send (self):
        '''
        This routine is called after the fuzzer transmits a test case and returns the number of bytes captured by the
        PCAP thread.

        @rtype:  Integer
        @return: Number of bytes captured in PCAP thread.
        '''

        # grab the number of recorded bytes.
        data_bytes = self.pcap_thread.data_bytes

        # stop the packet capture thread.
        self.__stop()

        self.log("stopped PCAP thread, snagged %d bytes of data" % data_bytes)
        return data_bytes


    def pre_send (self, test_number):
        '''
        This routine is called before the fuzzer transmits a test case and spin off a packet capture thread.
        '''

        self.log("initializing capture for test case #%d" % test_number)

        # open the capture device and set the BPF filter.
        self.pcap = pcapy.open_live(self.device, -1, 1, 100)
        self.pcap.setfilter(self.filter)

        # instantiate the capture thread.
        pcap_log_path = "%s/%d.pcap" % (self.log_path, test_number)
        self.pcap_thread = pcap_thread(self, self.pcap, pcap_log_path)
        self.pcap_thread.start()


    def log (self, msg="", level=1):
        '''
        If the supplied message falls under the current log level, print the specified message to screen.

        @type  msg: String
        @param msg: Message to log
        '''

        if self.log_level >= level:
            print "[%s] %s" % (time.strftime("%I:%M.%S"), msg)


    def retrieve (self, test_number):
        '''
        Return the raw binary contents of the PCAP saved for the specified test case number.

        @type  test_number: Integer
        @param test_number: Test number to retrieve PCAP for.
        '''

        self.log("retrieving PCAP for test case #%d" % test_number)

        pcap_log_path = "%s/%d.pcap" % (self.log_path, test_number)
        fh            = open(pcap_log_path, "rb")
        data          = fh.read()
        fh.close()

        return data


    def set_filter (self, filter):
        self.log("updating PCAP filter to '%s'" % filter)

        self.filter = filter


    def set_log_path (self, log_path):
        self.log("updating log path to '%s'" % log_path)

        self.log_path = log_path


########################################################################################################################

if __name__ == "__main__":
    # parse command line options.
    try:
        opts, args = getopt.getopt(sys.argv[1:], "d:f:P:l:", ["device=", "filter=", "log_path=", "log_level=", "port="])
    except getopt.GetoptError:
        ERR(USAGE)

    device    = None
    filter    = ""
    log_path  = "./"
    log_level = 1

    for opt, arg in opts:
        if opt in ("-d", "--device"):     device    = IFS[int(arg)]
        if opt in ("-f", "--filter"):     filter    = arg
        if opt in ("-P", "--log_path"):   log_path  = arg
        if opt in ("-l", "--log_level"):  log_level = int(arg)
        if opt in ("--port"):             PORT      = int(arg)

    if not device:
        ERR(USAGE)

    try:
        servlet = network_monitor_pedrpc_server("0.0.0.0", PORT, device, filter, log_path, log_level)
        servlet.serve_forever()
    except:
        pass

########NEW FILE########
__FILENAME__ = process_monitor
#!c:\\python\\python.exe

import subprocess
import threading
import getopt
import time
import sys
import os

from sulley import pedrpc

sys.path.append(r"..\..\paimei")

from pydbg         import *
from pydbg.defines import *

import utils

PORT  = 26002
ERR   = lambda msg: sys.stderr.write("ERR> " + msg + "\n") or sys.exit(1)
USAGE = "USAGE: process_monitor.py"\
        "\n    <-c|--crash_bin FILENAME> filename to serialize crash bin class to"\
        "\n    [-p|--proc_name NAME]     process name to search for and attach to"\
        "\n    [-i|--ignore_pid PID]     ignore this PID when searching for the target process"\
        "\n    [-l|--log_level LEVEL]    log level (default 1), increase for more verbosity"\
        "\n    [--port PORT]             TCP port to bind this agent to"


########################################################################################################################
class debugger_thread (threading.Thread):
    def __init__ (self, process_monitor, proc_name, ignore_pid=None):
        '''
        Instantiate a new PyDbg instance and register user and access violation callbacks.
        '''

        threading.Thread.__init__(self)

        self.process_monitor  = process_monitor
        self.proc_name        = proc_name
        self.ignore_pid       = ignore_pid

        self.access_violation = False
        self.active           = True
        self.dbg              = pydbg()
        self.pid              = None

        # give this thread a unique name.
        self.setName("%d" % time.time())

        self.process_monitor.log("debugger thread initialized with UID: %s" % self.getName(), 5)

        # set the user callback which is response for checking if this thread has been killed.
        self.dbg.set_callback(USER_CALLBACK_DEBUG_EVENT,  self.dbg_callback_user)
        self.dbg.set_callback(EXCEPTION_ACCESS_VIOLATION, self.dbg_callback_access_violation)


    def dbg_callback_access_violation (self, dbg):
        '''
        Ignore first chance exceptions. Record all unhandled exceptions to the process monitor crash bin and kill
        the target process.
        '''

        # ignore first chance exceptions.
        if dbg.dbg.u.Exception.dwFirstChance:
            return DBG_EXCEPTION_NOT_HANDLED

        # raise the access violaton flag.
        self.access_violation = True

        # record the crash to the process monitor crash bin.
        # include the test case number in the "extra" information block.
        self.process_monitor.crash_bin.record_crash(dbg, self.process_monitor.test_number)

        # save the the crash synopsis.
        self.process_monitor.last_synopsis = self.process_monitor.crash_bin.crash_synopsis()
        first_line                         = self.process_monitor.last_synopsis.split("\n")[0]

        self.process_monitor.log("debugger thread-%s caught access violation: '%s'" % (self.getName(), first_line))

        # this instance of pydbg should no longer be accessed, i want to know if it is.
        self.process_monitor.crash_bin.pydbg = None

        # kill the process.
        dbg.terminate_process()
        return DBG_CONTINUE


    def dbg_callback_user (self, dbg):
        '''
        The user callback is run roughly every 100 milliseconds (WaitForDebugEvent() timeout from pydbg_core.py). Simply
        check if the active flag was lowered and if so detach from the target process. The thread should then exit.
        '''

        if not self.active:
            self.process_monitor.log("debugger thread-%s detaching" % self.getName(), 5)
            dbg.detach()

        return DBG_CONTINUE


    def run (self):
        '''
        Main thread routine, called on thread.start(). Thread exits when this routine returns.
        '''

        self.process_monitor.log("debugger thread-%s looking for process name: %s" % (self.getName(), self.proc_name))

        # watch for and try attaching to the process.
        try:
            self.watch()
            self.dbg.attach(self.pid)
            self.dbg.run()
            self.process_monitor.log("debugger thread-%s exiting" % self.getName())
        except:
            pass

        # XXX - removing the following line appears to cause some concurrency issues.
        del(self.dbg)


    def watch (self):
        '''
        Continuously loop, watching for the target process. This routine "blocks" until the target process is found.
        Update self.pid when found and return.
        '''

        while not self.pid:
            for (pid, name) in self.dbg.enumerate_processes():
                # ignore the optionally specified PID.
                if pid == self.ignore_pid:
                    continue

                if name.lower() == self.proc_name.lower():
                    self.pid = pid
                    break

        self.process_monitor.log("debugger thread-%s found match on pid %d" % (self.getName(), self.pid))


########################################################################################################################
class process_monitor_pedrpc_server (pedrpc.server):
    def __init__ (self, host, port, crash_filename, proc_name=None, ignore_pid=None, log_level=1):
        '''
        @type  host:           String
        @param host:           Hostname or IP address
        @type  port:           Integer
        @param port:           Port to bind server to
        @type  crash_filename: String
        @param crash_filename: Name of file to (un)serialize crash bin to/from
        @type  proc_name:      String
        @param proc_name:      (Optional, def=None) Process name to search for and attach to
        @type  ignore_pid:     Integer
        @param ignore_pid:     (Optional, def=None) Ignore this PID when searching for the target process
        @type  log_level:      Integer
        @param log_level:      (Optional, def=1) Log output level, increase for more verbosity
        '''

        # initialize the PED-RPC server.
        pedrpc.server.__init__(self, host, port)

        self.crash_filename   = crash_filename
        self.proc_name        = proc_name
        self.ignore_pid       = ignore_pid
        self.log_level        = log_level

        self.stop_commands    = []
        self.start_commands   = []
        self.test_number      = None
        self.debugger_thread  = None
        self.crash_bin        = utils.crash_binning.crash_binning()

        self.last_synopsis    = ""

        if not os.access(os.path.dirname(self.crash_filename), os.X_OK):
            self.log("invalid path specified for crash bin: %s" % self.crash_filename)
            raise Exception

        # restore any previously recorded crashes.
        try:
            self.crash_bin.import_file(self.crash_filename)
        except:
            pass

        self.log("Process Monitor PED-RPC server initialized:")
        self.log("\t crash file:  %s" % self.crash_filename)
        self.log("\t # records:   %d" % len(self.crash_bin.bins))
        self.log("\t proc name:   %s" % self.proc_name)
        self.log("\t log level:   %d" % self.log_level)
        self.log("awaiting requests...")


    def alive (self):
        '''
        Returns True. Useful for PED-RPC clients who want to see if the PED-RPC connection is still alive.
        '''

        return True


    def get_crash_synopsis (self):
        '''
        Return the last recorded crash synopsis.

        @rtype:  String
        @return: Synopsis of last recorded crash.
        '''

        return self.last_synopsis


    def get_bin_keys (self):
        '''
        Return the crash bin keys, ie: the unique list of exception addresses.

        @rtype:  List
        @return: List of crash bin exception addresses (keys).
        '''

        return self.crash_bin.bins.keys()


    def get_bin (self, bin):
        '''
        Return the crash entries from the specified bin or False if the bin key is invalid.

        @type  bin: Integer (DWORD)
        @param bin: Crash bin key (ie: exception address)

        @rtype:  List
        @return: List of crashes in specified bin.
        '''

        if not self.crash_bin.bins.has_key(bin):
            return False

        return self.crash_bin.bins[bin]


    def log (self, msg="", level=1):
        '''
        If the supplied message falls under the current log level, print the specified message to screen.

        @type  msg: String
        @param msg: Message to log
        '''

        if self.log_level >= level:
            print "[%s] %s" % (time.strftime("%I:%M.%S"), msg)


    def post_send (self):
        '''
        This routine is called after the fuzzer transmits a test case and returns the status of the target.

        @rtype:  Boolean
        @return: Return True if the target is still active, False otherwise.
        '''

        av = self.debugger_thread.access_violation

        # if there was an access violation, wait for the debugger thread to finish then kill thread handle.
        # it is important to wait for the debugger thread to finish because it could be taking its sweet ass time
        # uncovering the details of the access violation.
        if av:
            while self.debugger_thread.isAlive():
                time.sleep(1)

            self.debugger_thread = None

        # serialize the crash bin to disk.
        self.crash_bin.export_file(self.crash_filename)

        bins    = len(self.crash_bin.bins)
        crashes = 0

        for bin in self.crash_bin.bins.keys():
            crashes += len(self.crash_bin.bins[bin])

        return not av


    def pre_send (self, test_number):
        '''
        This routine is called before the fuzzer transmits a test case and ensure the debugger thread is operational.

        @type  test_number: Integer
        @param test_number: Test number to retrieve PCAP for.
        '''

        self.log("pre_send(%d)" % test_number, 10)
        self.test_number = test_number

        # unserialize the crash bin from disk. this ensures we have the latest copy (ie: vmware image is cycling).
        try:
            self.crash_bin.import_file(self.crash_filename)
        except:
            pass

        # if we don't already have a debugger thread, instantiate and start one now.
        if not self.debugger_thread or not self.debugger_thread.isAlive():
            self.log("creating debugger thread", 5)
            self.debugger_thread = debugger_thread(self, self.proc_name, self.ignore_pid)
            self.debugger_thread.start()
            self.log("giving debugger thread 2 seconds to settle in", 5)
            time.sleep(2)


    def start_target (self):
        '''
        Start up the target process by issuing the commands in self.start_commands.
        '''

        self.log("starting target process")

        for command in self.start_commands:
            subprocess.Popen(command)

        self.log("done. target up and running, giving it 5 seconds to settle in.")
        time.sleep(5)


    def stop_target (self):
        '''
        Kill the current debugger thread and stop the target process by issuing the commands in self.stop_commands.
        '''

        # give the debugger thread a chance to exit.
        time.sleep(1)

        self.log("stopping target process")

        for command in self.stop_commands:
            if command == "TERMINATE_PID":
                dbg = pydbg()
                for (pid, name) in dbg.enumerate_processes():
                    if name.lower() == self.proc_name.lower():
                        os.system("taskkill /pid %d" % pid)
                        break
            else:
                os.system(command)


    def set_proc_name (self, proc_name):
        self.log("updating target process name to '%s'" % proc_name)

        self.proc_name = proc_name


    def set_start_commands (self, start_commands):
        self.log("updating start commands to: %s" % start_commands)

        self.start_commands = start_commands


    def set_stop_commands (self, stop_commands):
        self.log("updating stop commands to: %s" % stop_commands)

        self.stop_commands = stop_commands


########################################################################################################################

if __name__ == "__main__":
    # parse command line options.
    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:i:l:p:", ["crash_bin=", "ignore_pid=", "log_level=", "proc_name=", "port="])
    except getopt.GetoptError:
        ERR(USAGE)

    crash_bin = ignore_pid = proc_name = None
    log_level = 1

    for opt, arg in opts:
        if opt in ("-c", "--crash_bin"):   crash_bin  = arg
        if opt in ("-i", "--ignore_pid"):  ignore_pid = int(arg)
        if opt in ("-l", "--log_level"):   log_level  = int(arg)
        if opt in ("-p", "--proc_Name"):   proc_name  = arg
        if opt in ("-P", "--port"):        PORT       = int(arg)

    if not crash_bin:
        ERR(USAGE)

    # spawn the PED-RPC servlet.
    try:
        servlet = process_monitor_pedrpc_server("0.0.0.0", PORT, crash_bin, proc_name, ignore_pid, log_level)
        servlet.serve_forever()
    except Exception,e:
	# XXX: Add servlet.shutdown
	# XXX: Add KeyboardInterrupt
	ERR("Error starting RPC server!\n\t%s" % e)

########NEW FILE########
__FILENAME__ = process_monitor_unix
import os
import sys
import getopt
import signal
import time
import threading

from sulley import pedrpc

'''
By nnp
http://www.unprotectedhex.com

This intended as a basic replacement for Sulley's process_monitor.py on *nix.
The below options are accepted. Crash details are limited to the signal that
caused the death and whatever operating system supported mechanism is in place (i.e
core dumps)

Replicated methods:
    - alive
    - log
    - post_send
    - pre_send
    _ start_target
    - stop_target
    - set_start_commands
    - set_stop_commands

Limitations
    - Cannot attach to an already running process
    - Currently only accepts one start_command
    - Limited 'crash binning'. Relies on the availability of core dumps. These
      should be created in the same directory the process is ran from on Linux
      and in the (hidden) /cores directory on OS X. On OS X you have to add 
      the option COREDUMPS=-YES- to /etc/hostconfig and then `ulimit -c
      unlimited` as far as I know. A restart may be required. The file
      specified by crash_bin will any other available details such as the test
      that caused the crash and the signal received by the program
'''

USAGE = "USAGE: process_monitor_unix.py"\
        "\n    -c|--crash_bin             File to record crash info too" \
        "\n    [-P|--port PORT]             TCP port to bind this agent too"\
        "\n    [-l|--log_level LEVEL]       log level (default 1), increase for more verbosity"

ERR   = lambda msg: sys.stderr.write("ERR> " + msg + "\n") or sys.exit(1)


class debugger_thread:
    def __init__(self, start_command):
        '''
        This class isn't actually ran as a thread, only the start_monitoring
        method is. It can spawn/stop a process, wait for it to exit and report on
        the exit status/code.
        '''
        
        self.start_command = start_command
        self.tokens = start_command.split(' ')
        self.cmd_args = []
        self.pid = None
        self.exit_status = None
        self.alive = False

    def spawn_target(self):
        print self.tokens
        self.pid = os.spawnv(os.P_NOWAIT, self.tokens[0], self.tokens)
        self.alive = True
        
    def start_monitoring(self):
        '''
        self.exit_status = os.waitpid(self.pid, os.WNOHANG | os.WUNTRACED)
        while self.exit_status == (0, 0):                    
            self.exit_status = os.waitpid(self.pid, os.WNOHANG | os.WUNTRACED)
        '''
        
        self.exit_status = os.waitpid(self.pid, 0)
        # [0] is the pid
        self.exit_status = self.exit_status[1]
            
        self.alive = False

    def get_exit_status(self):
        return self.exit_status

    def stop_target(self):
        os.kill(self.pid, signal.SIGKILL)
        self.alive = False

    def isAlive(self):
        return self.alive

########################################################################################################################

class nix_process_monitor_pedrpc_server(pedrpc.server):
    def __init__(self, host, port, crash_bin, log_level=1):
        '''
        @type host: String
        @param host: Hostname or IP address
        @type port: Integer
        @param port: Port to bind server to
        @type crash_bin: String
        @param crash_bin: Where to save monitored process crashes for analysis
        
        '''
        
        pedrpc.server.__init__(self, host, port)
        self.crash_bin = crash_bin
        self.log_level = log_level
        self.dbg = None
        self.log("Process Monitor PED-RPC server initialized:")
        self.log("Listening on %s:%s" % (host, port))
        self.log("awaiting requests...")

    def alive (self):
        '''
        Returns True. Useful for PED-RPC clients who want to see if the PED-RPC connection is still alive.
        '''

        return True

    def log (self, msg="", level=1):
        '''
        If the supplied message falls under the current log level, print the specified message to screen.

        @type  msg: String
        @param msg: Message to log
        '''

        if self.log_level >= level:
            print "[%s] %s" % (time.strftime("%I:%M.%S"), msg)

    def post_send (self):
        '''
        This routine is called after the fuzzer transmits a test case and returns the status of the target.

        @rtype:  Boolean
        @return: Return True if the target is still active, False otherwise.
        '''

        if not self.dbg.isAlive():
            exit_status = self.dbg.get_exit_status()
            rec_file = open(self.crash_bin, 'a')
            if os.WCOREDUMP(exit_status):
                reason = 'Segmentation fault'
            elif os.WIFSTOPPED(exit_status):
                reason = 'Stopped with signal ' + str(os.WTERMSIG(exit_status))
            elif os.WIFSIGNALED(exit_status):
                reason = 'Terminated with signal ' + str(os.WTERMSIG(exit_status))
            elif os.WIFEXITED(exit_status):
                reason = 'Exit with code - ' + str(os.WEXITSTATUS(exit_status))
            else:
                reason = 'Process died for unknown reason'
                
            self.last_synopsis = '[%s] Crash : Test - %d Reason - %s\n' % (time.strftime("%I:%M.%S"), self.test_number, reason)
            rec_file.write(self.last_synopsis)
            rec_file.close()

        return self.dbg.isAlive()

    def pre_send (self, test_number):
        '''
        This routine is called before the fuzzer transmits a test case and ensure the debugger thread is operational.
        (In this implementation do nothing for now)

        @type  test_number: Integer
        @param test_number: Test number to retrieve PCAP for.
        '''
        if self.dbg == None:
            self.start_target()
            
        self.log("pre_send(%d)" % test_number, 10)
        self.test_number = test_number

    def start_target (self):
        '''
        Start up the target process by issuing the commands in self.start_commands.
        '''

        self.log("starting target process")
        
        self.dbg = debugger_thread(self.start_commands[0])
        self.dbg.spawn_target()
        # prevent blocking by spawning off another thread to waitpid
        threading.Thread(target=self.dbg.start_monitoring).start()
        self.log("done. target up and running, giving it 5 seconds to settle in.")
        time.sleep(5)

    def stop_target (self):
        '''
        Kill the current debugger thread and stop the target process by issuing the commands in self.stop_commands.
        '''

        # give the debugger thread a chance to exit.
        time.sleep(1)

        self.log("stopping target process")

        for command in self.stop_commands:
            if command == "TERMINATE_PID":
                self.dbg.stop_target()
            else:
                os.system(command)

    def set_start_commands (self, start_commands):
        '''
        We expect start_commands to be a list with one element for example
        ['/usr/bin/program arg1 arg2 arg3']
        '''

        if len(start_commands) > 1:
            self.log("This process monitor does not accept > 1 start command")
            return

        self.log("updating start commands to: %s" % start_commands)
        self.start_commands = start_commands


    def set_stop_commands (self, stop_commands):
        self.log("updating stop commands to: %s" % stop_commands)

        self.stop_commands = stop_commands

    def set_proc_name (self, proc_name):
        self.log("updating target process name to '%s'" % proc_name)

        self.proc_name = proc_name

    def get_crash_synopsis (self):
        '''
        Return the last recorded crash synopsis.

        @rtype:  String
        @return: Synopsis of last recorded crash.
        '''

        return self.last_synopsis
    
########################################################################################################################

if __name__ == "__main__":
    # parse command line options.
    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:P:l:", ["crash_bin=","port=","log_level=",])
    except getopt.GetoptError:
        ERR(USAGE)

    log_level = 1
    PORT = None
    crash_bin = None
    for opt, arg in opts:
        if opt in ("-c", "--crash_bin"):   crash_bin  = arg
        if opt in ("-P", "--port"): PORT = int(arg)
        if opt in ("-l", "--log_level"):   log_level  = int(arg)

    if not crash_bin: ERR(USAGE)
    
    if PORT == None:
        PORT = 26002
    
    # spawn the PED-RPC servlet.

    servlet = nix_process_monitor_pedrpc_server("0.0.0.0", PORT, crash_bin, log_level)
    servlet.serve_forever()


########NEW FILE########
__FILENAME__ = hp
from sulley import *

from struct import *


########################################################################################################################
def unicode_ftw(val):
    """
    Simple unicode slicer
    """

    val_list = []
    for char in val:
        val_list.append("\x00")
        val_list.append(pack('B', ord(char)))

    ret = ""
    for char in val_list:
        ret += char

    return ret

########################################################################################################################
s_initialize("omni")
"""
    Hewlett Packard OpenView Data Protector OmniInet.exe
"""


if s_block_start("packet_1"):
    s_size("packet_2", endian=">", length=4)
s_block_end()

if s_block_start("packet_2"):

    # unicode byte order marker
    s_static("\xfe\xff")

    # unicode magic
    if s_block_start("unicode_magic", encoder=unicode_ftw):
        s_int(267, format="ascii")
    s_block_end()
    s_static("\x00\x00")

    # random 2 bytes
    s_string("AA", size=2)

    # unicode value to pass calls to wtoi()
    if s_block_start("unicode_100_1", encoder=unicode_ftw):
        s_int(100, format="ascii")
    s_block_end()
    s_static("\x00\x00")

    # random 2 bytes
    s_string("BB", size=2)

    # unicode value to pass calls to wtoi()
    if s_block_start("unicode_100_2", encoder=unicode_ftw):
        s_int(100, format="ascii")
    s_block_end()
    s_static("\x00\x00")

    # random 2 bytes
    s_string("CC", size=2)

    # unicode value to pass calls to wtoi()
    if s_block_start("unicode_100_3", encoder=unicode_ftw):
        s_int(100, format="ascii")
    s_block_end()
    s_static("\x00\x00")

    # random buffer
    s_string("D"*32, size=32)

    # barhost cookie
    s_dword(0x7cde7bab, endian="<", fuzzable=False)

    # random buffer
    s_string("FOO")

s_block_end()

########NEW FILE########
__FILENAME__ = http
from sulley import *
########################################################################################################################
# Old http.py request primitives, http_* does all of these and many more (AFAIK)
########################################################################################################################
# List of all blocks defined here (for easy copy/paste)
"""
sess.connect(s_get("HTTP VERBS"))
sess.connect(s_get("HTTP VERBS BASIC"))
sess.connect(s_get("HTTP VERBS POST"))
sess.connect(s_get("HTTP HEADERS"))
sess.connect(s_get("HTTP COOKIE"))
"""

s_initialize("HTTP VERBS")
s_group("verbs", values=["GET", "HEAD", "POST", "OPTIONS", "TRACE", "PUT", "DELETE", "PROPFIND"])
if s_block_start("body", group="verbs"):
    s_delim(" ")
    s_delim("/")
    s_string("index.html")
    s_delim(" ")
    s_string("HTTP")
    s_delim("/")
    s_string("1")
    s_delim(".")
    s_string("1")
    s_static("\r\n\r\n")
s_block_end()


########################################################################################################################
s_initialize("HTTP VERBS BASIC")
s_group("verbs", values=["GET", "HEAD"])
if s_block_start("body", group="verbs"):
    s_delim(" ")
    s_delim("/")
    s_string("index.html")
    s_delim(" ")
    s_string("HTTP")
    s_delim("/")
    s_string("1")
    s_delim(".")
    s_string("1")
    s_static("\r\n\r\n")
s_block_end()


########################################################################################################################
s_initialize("HTTP VERBS POST")
s_static("POST / HTTP/1.1\r\n")
s_static("Content-Type: ")
s_string("application/x-www-form-urlencoded")
s_static("\r\n")
s_static("Content-Length: ")
s_size("post blob", format="ascii", signed=True, fuzzable=True)
s_static("\r\n\r\n")

if s_block_start("post blob"):
    s_string("A"*100 + "=" + "B"*100)
s_block_end()


########################################################################################################################
s_initialize("HTTP HEADERS")
s_static("GET / HTTP/1.1\r\n")

# let's fuzz random headers with malformed delimiters.
s_string("Host")
s_delim(":")
s_delim(" ")
s_string("localhost")
s_delim("\r\n")

# let's fuzz the value portion of some popular headers.
s_static("User-Agent: ")
s_string("Mozilla/5.0 (Windows; U)")
s_static("\r\n")

s_static("Accept-Language: ")
s_string("en-us")
s_delim(",")
s_string("en;q=0.5")
s_static("\r\n")

s_static("Keep-Alive: ")
s_string("300")
s_static("\r\n")

s_static("Connection: ")
s_string("keep-alive")
s_static("\r\n")

s_static("Referer: ")
s_string("http://dvlabs.tippingpoint.com")
s_static("\r\n")
s_static("\r\n")


########################################################################################################################
s_initialize("HTTP COOKIE")
s_static("GET / HTTP/1.1\r\n")

if s_block_start("cookie"):
    s_static("Cookie: ")
    s_string("auth")
    s_delim("=")
    s_string("1234567890")
    s_static("\r\n")
    s_block_end()

s_repeat("cookie", max_reps=5000, step=500)
s_static("\r\n")
########NEW FILE########
__FILENAME__ = http_get
from sulley import *
########################################################################################################################
# All HTTP requests that I could think of/find
########################################################################################################################
# List of all blocks defined here (for easy copy/paste)
"""
sess.connect(s_get("HTTP VERBS"))
sess.connect(s_get("HTTP METHOD"))
sess.connect(s_get("HTTP REQ"))
"""

########################################################################################################################
# Fuzz all the publicly avalible methods known for HTTP Servers
########################################################################################################################
s_initialize("HTTP VERBS")
s_group("verbs", values=["GET", "HEAD", "POST", "OPTIONS", "TRACE", "PUT", "DELETE", "PROPFIND","CONNECT","PROPPATCH",
                         "MKCOL","COPY","MOVE","LOCK","UNLOCK","VERSION-CONTROL","REPORT","CHECKOUT","CHECKIN","UNCHECKOUT",
                         "MKWORKSPACE","UPDATE","LABEL","MERGE","BASELINE-CONTROL","MKACTIVITY","ORDERPATCH","ACL","PATCH","SEARCH","CAT"])
if s_block_start("body", group="verbs"):
    s_delim(" ")
    s_delim("/")
    s_string("index.html")
    s_delim(" ")
    s_string("HTTP")
    s_delim("/")
    s_int(1,format="ascii")
    s_delim(".")
    s_int(1,format="ascii")
    s_static("\r\n\r\n")
s_block_end()

########################################################################################################################
# Fuzz the HTTP Method itself
########################################################################################################################
s_initialize("HTTP METHOD")
s_string("FUZZ")
s_static(" /index.html HTTP/1.1")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz this standard multi-header HTTP request
# GET / HTTP/1.1
# Host: www.google.com
# Connection: keep-alive
# User-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.83 Safari/537.1
# Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
# Accept-Encoding: gzip,deflate,sdch
# Accept-Language: en-US,en;q=0.8
# Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.3
########################################################################################################################
s_initialize("HTTP REQ")
s_static("GET / HTTP/1.1\r\n")
# Host: www.google.com
s_static("Host")
s_delim(":")
s_delim(" ")
s_string("www.google.com")
s_static("\r\n")
# Connection: keep-alive
s_static("Connection")
s_delim(":")
s_delim(" ")
s_string("Keep-Alive")
# User-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.83 Safari/537.1
s_static("User-Agent")
s_delim(":")
s_delim(" ")
s_string("Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.83 Safari/537.1")
s_static("\r\n")
# Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
s_static("Accept")
s_delim(":")
s_delim(" ")
s_string("text")
s_delim("/")
s_string("html")
s_delim(",")
s_string("application")
s_delim("/")
s_string("xhtml")
s_delim("+")
s_string("xml")
s_delim(",")
s_string("application")
s_delim("/")
s_string("xml")
s_delim(";")
s_string("q")
s_delim("=")
s_int(0,format="ascii")
s_delim(".")
s_int(9,format="ascii")
s_delim(",")
s_string("*")
s_delim("/")
s_string("*")
s_delim(";")
s_string("q")
s_delim("=")
s_int(0,format="ascii")
s_delim(".")
s_int(8,format="ascii")
s_static("\r\n")
# Accept-Encoding: gzip,deflate,sdch
s_static("Accept-Encoding")
s_delim(":")
s_delim(" ")
s_string("gzip")
s_delim(",")
s_string("deflate")
s_delim(",")
s_string("sdch")
s_static("\r\n")
# Accept-Language: en-US,en;q=0.8
s_static("Accept-Language")
s_delim(":")
s_delim(" ")
s_string("en-US")
s_delim(",")
s_string("en")
s_delim(";")
s_string("q")
s_delim("=")
s_string("0.8")
s_static("\r\n")
# Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.3
s_static("Accept-Charset")
s_delim(":")
s_delim(" ")
s_string("ISO")
s_delim("-")
s_int(8859,format="ascii")
s_delim("-")
s_int(1,format="ascii")
s_delim(",")
s_string("utf-8")
s_delim(";")
s_string("q")
s_delim("=")
s_int(0,format="ascii")
s_delim(".")
s_int(7,format="ascii")
s_delim(",")
s_string("*")
s_delim(";")
s_string("q")
s_delim("=")
s_int(0,format="ascii")
s_delim(".")
s_int(3,format="ascii")
s_static("\r\n\r\n")

########NEW FILE########
__FILENAME__ = http_header
from sulley import *
########################################################################################################################
# List of all HTTP Headers I could find
########################################################################################################################
# List of all blocks defined here (for easy copy/paste)
"""
sess.connect(s_get("HTTP HEADER ACCEPT"))
sess.connect(s_get("HTTP HEADER ACCEPTCHARSET"))
sess.connect(s_get("HTTP HEADER ACCEPTDATETIME"))
sess.connect(s_get("HTTP HEADER ACCEPTENCODING"))
sess.connect(s_get("HTTP HEADER ACCEPTLANGUAGE"))
sess.connect(s_get("HTTP HEADER AUTHORIZATION"))
sess.connect(s_get("HTTP HEADER CACHECONTROL"))
sess.connect(s_get("HTTP HEADER CLOSE"))
sess.connect(s_get("HTTP HEADER CONTENTLENGTH"))
sess.connect(s_get("HTTP HEADER CONTENTMD5"))
sess.connect(s_get("HTTP HEADER COOKIE"))
sess.connect(s_get("HTTP HEADER DATE"))
sess.connect(s_get("HTTP HEADER DNT"))
sess.connect(s_get("HTTP HEADER EXPECT"))
sess.connect(s_get("HTTP HEADER FROM"))
sess.connect(s_get("HTTP HEADER HOST"))
sess.connect(s_get("HTTP HEADER IFMATCH"))
sess.connect(s_get("HTTP HEADER IFMODIFIEDSINCE"))
sess.connect(s_get("HTTP HEADER IFNONEMATCH"))
sess.connect(s_get("HTTP HEADER IFRANGE"))
sess.connect(s_get("HTTP HEADER IFUNMODIFIEDSINCE"))
sess.connect(s_get("HTTP HEADER KEEPALIVE"))
sess.connect(s_get("HTTP HEADER MAXFORWARDS"))
sess.connect(s_get("HTTP HEADER PRAGMA"))
sess.connect(s_get("HTTP HEADER PROXYAUTHORIZATION"))
sess.connect(s_get("HTTP HEADER RANGE"))
sess.connect(s_get("HTTP HEADER REFERER"))
sess.connect(s_get("HTTP HEADER TE"))
sess.connect(s_get("HTTP HEADER UPGRADE"))
sess.connect(s_get("HTTP HEADER USERAGENT"))
sess.connect(s_get("HTTP HEADER VIA"))
sess.connect(s_get("HTTP HEADER WARNING"))
sess.connect(s_get("HTTP HEADER XATTDEVICEID"))
sess.connect(s_get("HTTP HEADER XDONOTTRACK"))
sess.connect(s_get("HTTP HEADER XFORWARDEDFOR"))
sess.connect(s_get("HTTP HEADER XREQUESTEDWITH"))
sess.connect(s_get("HTTP HEADER XWAPPROFILE"))
"""

########################################################################################################################
# Fuzz Accept header
# Accept: text/*;q=0.3, text/html;q=0.7, text/html;level=1, text/html;level=2;q=0.4, */*;q=0.5
########################################################################################################################
s_initialize("HTTP HEADER ACCEPT")
s_static("GET / HTTP/1.1\r\n")
s_static("Accept")
s_delim(":")
s_delim(" ")
s_string("text")
s_delim("/")
s_string("*")
s_delim(";")
s_string("q")
s_delim("=")
s_int(0,format="ascii")
s_delim(".")
s_int(3,format="ascii")
s_delim(",")
s_delim(" ")
s_string("text")
s_delim("/")
s_string("html")
s_delim(";")
s_string("q")
s_delim("=")
s_int(0,format="ascii")
s_delim(".")
s_int(7,format="ascii")
s_delim(",")
s_delim(" ")
s_string("text")
s_delim("/")
s_string("html")
s_delim(";")
s_string("level")
s_delim("=")
s_string("1")
s_delim(",")
s_delim(" ")
s_string("text")
s_delim("/")
s_string("html")
s_delim(";")
s_string("level")
s_delim("=")
s_int(2,format="ascii")
s_delim(";")
s_string("q")
s_delim("=")
s_int(0,format="ascii")
s_delim(".")
s_int(4,format="ascii")
s_delim(",")
s_delim(" ")
s_string("*")
s_delim("/")
s_string("*")
s_delim(";")
s_string("q")
s_delim("=")
s_int(0,format="ascii")
s_delim(".")
s_int(5,format="ascii")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Accept-Charset header
# Accept-Charset: utf-8, unicode-1-1;q=0.8
########################################################################################################################
s_initialize("HTTP HEADER ACCEPTCHARSET")
s_static("GET / HTTP/1.1\r\n")
s_static("Accept-Charset")
s_delim(":")
s_delim(" ")
s_string("utf")
s_delim("-")
s_int(8,format="ascii")
s_delim(",")
s_delim(" ")
s_string("unicode")
s_delim("-")
s_int(1,format="ascii")
s_delim("-")
s_int(1,format="ascii")
s_delim(";")
s_string("q")
s_delim("=")
s_int(0,format="ascii")
s_delim(".")
s_int(8,format="ascii")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Accept-Datetime header
# Accept-Datetime: Thu, 31 May 2007 20:35:00 GMT
########################################################################################################################
s_initialize("HTTP HEADER ACCEPTDATETIME")
s_static("GET / HTTP/1.1\r\n")
s_static("Accept-Datetime")
s_delim(":")
s_delim(" ")
s_string("Thu")
s_delim(",")
s_delim(" ")
s_string("31")
s_delim(" ")
s_string("May")
s_delim(" ")
s_string("2007")
s_delim(" ")
s_string("20")
s_delim(":")
s_string("35")
s_delim(":")
s_string("00")
s_delim(" ")
s_string("GMT")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Accept-Encoding header
# Accept-Encoding: gzip, deflate
########################################################################################################################
s_initialize("HTTP HEADER ACCEPTENCODING")
s_static("GET / HTTP/1.1\r\n")
s_static("Accept-Encoding")
s_delim(":")
s_delim(" ")
s_string("gzip")
s_delim(", ")
s_string("deflate")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Accept-Language header
# Accept-Language: en-us, en;q=0.5
########################################################################################################################
s_initialize("HTTP HEADER ACCEPTLANGUAGE")
s_static("GET / HTTP/1.1\r\n")
s_static("Accept-Language")
s_delim(":")
s_delim(" ")
s_string("en-us")
s_delim(",")
s_string("en")
s_delim(";")
s_string("q")
s_delim("=")
s_string("0.5")
s_static("\r\n\r\n")


########################################################################################################################
# Fuzz Authorization header
# Authorization: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==
########################################################################################################################
s_initialize("HTTP HEADER AUTHORIZATION")
s_static("GET / HTTP/1.1\r\n")
s_static("Authorization")
s_delim(":")
s_delim(" ")
s_string("Basic")
s_delim(" ")
s_string("QWxhZGRpbjpvcGVuIHNlc2FtZQ==")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Cache-Control header
# Cache-Control: no-cache
########################################################################################################################
s_initialize("HTTP HEADER CACHECONTROL")
s_static("GET / HTTP/1.1\r\n")
s_static("Cache-Control")
s_delim(":")
s_delim(" ")
s_string("no")
s_delim("-")
s_string("cache")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Connection header
# Connection: close
########################################################################################################################
s_initialize("HTTP HEADER CLOSE")
s_static("GET / HTTP/1.1\r\n")
s_static("Connection")
s_delim(":")
s_delim(" ")
s_string("close")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Content Length header
# Content-Length: 348
########################################################################################################################
s_initialize("HTTP HEADER CONTENTLENGTH")
s_static("GET / HTTP/1.1\r\n")
s_static("Content-Length")
s_delim(":")
s_delim(" ")
s_string("348")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Content MD5 header
# Content-MD5: Q2hlY2sgSW50ZWdyaXR5IQ==
########################################################################################################################
s_initialize("HTTP HEADER CONTENTMD5")
s_static("GET / HTTP/1.1\r\n")
s_static("Content-MD5")
s_delim(":")
s_delim(" ")
s_string("Q2hlY2sgSW50ZWdyaXR5IQ==")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz COOKIE header
# Cookie: PHPSESSIONID=hLKQPySBvyTRq5K5RJmcTHQVtQycmwZG3Qvr0tSy2w9mQGmbJbJn;
########################################################################################################################
s_initialize("HTTP HEADER COOKIE")
s_static("GET / HTTP/1.1\r\n")

if s_block_start("cookie"):
    s_static("Cookie")
    s_delim(":")
    s_delim(" ")
    s_string("PHPSESSIONID")
    s_delim("=")
    s_string("hLKQPySBvyTRq5K5RJmcTHQVtQycmwZG3Qvr0tSy2w9mQGmbJbJn")
    s_static(";")
    s_static("\r\n")
    s_block_end()

s_repeat("cookie", max_reps=5000, step=500)
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Date header
# Date: Tue, 15 Nov 2012 08:12:31 EST
########################################################################################################################
s_initialize("HTTP HEADER DATE")
s_static("GET / HTTP/1.1\r\n")
s_static("Date")
s_delim(":")
s_delim(" ")
s_string("Tue")
s_delim(",")
s_delim(" ")
s_string("15")
s_delim(" ")
s_string("Nov")
s_delim(" ")
s_string("2012")
s_delim(" ")
s_string("08")
s_delim(":")
s_string("12")
s_delim(":")
s_string("31")
s_delim(" ")
s_string("EST")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz DNT header -> May be same as X-Do-Not-Track?
# DNT: 1
########################################################################################################################
s_initialize("HTTP HEADER DNT")
s_static("GET / HTTP/1.1\r\n")
s_static("DNT")
s_delim(":")
s_delim(" ")
s_string("1")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Expect header
# Expect: 100-continue
########################################################################################################################
s_initialize("HTTP HEADER EXPECT")
s_static("GET / HTTP/1.1\r\n")
s_static("Expect")
s_delim(":")
s_delim(" ")
s_string("100")
s_delim("-")
s_string("continue")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz From header
# From: derp@derp.com
########################################################################################################################
s_initialize("HTTP HEADER FROM")
s_static("GET / HTTP/1.1\r\n")
s_static("From")
s_delim(":")
s_delim(" ")
s_string("derp")
s_delim("@")
s_string("derp")
s_delim(".")
s_string("com")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Host header
# Host: 127.0.0.1
########################################################################################################################
s_initialize("HTTP HEADER HOST")
s_static("GET / HTTP/1.1\r\n")
s_static("Host")
s_delim(":")
s_delim(" ")
s_string("127.0.0.1")
s_static("\r\n")
s_string("Connection")
s_delim(":")
s_delim(" ")
s_string("Keep-Alive")
s_static("\r\n\r\n")


########################################################################################################################
# Fuzz If-Match header
# If-Match: "737060cd8c284d8af7ad3082f209582d"
########################################################################################################################
s_initialize("HTTP HEADER IFMATCH")
s_static("GET / HTTP/1.1\r\n")
s_static("If-Match")
s_delim(":")
s_delim(" ")
s_static("\"")
s_string("737060cd8c284d8af7ad3082f209582d")
s_static("\"")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz If-Modified-Since header
# If-Modified-Since: Sat, 29 Oct 2012 19:43:31 ESTc
########################################################################################################################
s_initialize("HTTP HEADER IFMODIFIEDSINCE")
s_static("GET / HTTP/1.1\r\n")
s_static("If-Modified-Since")
s_delim(":")
s_delim(" ")
s_string("Sat")
s_delim(",")
s_delim(" ")
s_string("29")
s_delim(" ")
s_string("Oct")
s_delim(" ")
s_string("2012")
s_delim(" ")
s_string("08")
s_delim(":")
s_string("12")
s_delim(":")
s_string("31")
s_delim(" ")
s_string("EST")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz If-None-Match header
# If-None-Match: "737060cd8c284d8af7ad3082f209582d"
########################################################################################################################
s_initialize("HTTP HEADER IFNONEMATCH")
s_static("GET / HTTP/1.1\r\n")
s_static("If-None-Match")
s_delim(":")
s_delim(" ")
s_static("\"")
s_string("737060cd8c284d8af7ad3082f209582d")
s_static("\"")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz If-Range header
# If-Range: "737060cd8c284d8af7ad3082f209582d"
########################################################################################################################
s_initialize("HTTP HEADER IFRANGE")
s_static("GET / HTTP/1.1\r\n")
s_static("If-Range")
s_delim(":")
s_delim(" ")
s_static("\"")
s_string("737060cd8c284d8af7ad3082f209582d")
s_static("\"")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz If-Unmodified-Since header
# If-Unmodified-Since: Sat, 29 Oct 2012 19:43:31 EST
########################################################################################################################
s_initialize("HTTP HEADER IFUNMODIFIEDSINCE")
s_static("GET / HTTP/1.1\r\n")
s_static("If-Unmodified-Since")
s_delim(":")
s_delim(" ")
s_string("Sat")
s_delim(",")
s_delim(" ")
s_string("29")
s_delim(" ")
s_string("Oct")
s_delim(" ")
s_string("2012")
s_delim(" ")
s_string("08")
s_delim(":")
s_string("12")
s_delim(":")
s_string("31")
s_delim(" ")
s_string("EST")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz KeepAlive header
# Keep-Alive: 300
########################################################################################################################
s_initialize("HTTP HEADER KEEPALIVE")
s_static("GET / HTTP/1.1\r\n")
s_static("Keep-Alive")
s_delim(":")
s_delim(" ")
s_string("300")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Max-Fowards header
# Max-Forwards: 80
########################################################################################################################
s_initialize("HTTP HEADER MAXFORWARDS")
s_static("GET / HTTP/1.1\r\n")
s_static("Max-Forwards")
s_delim(":")
s_delim(" ")
s_string("80")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Pragma header
# Pragma: no-cache
########################################################################################################################
s_initialize("HTTP HEADER PRAGMA")
s_static("GET / HTTP/1.1\r\n")
s_static("Pragma")
s_delim(":")
s_delim(" ")
s_string("no-cache")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Proxy-Authorization header
# Proxy-Authorization: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==
########################################################################################################################
s_initialize("HTTP HEADER PROXYAUTHORIZATION")
s_static("GET / HTTP/1.1\r\n")
s_static("Proxy-Authorization")
s_delim(":")
s_delim(" ")
s_string("Basic")
s_delim(" ")
s_string("QWxhZGRpbjpvcGVuIHNlc2FtZQ==")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Range header
# Range: bytes=500-999
########################################################################################################################
s_initialize("HTTP HEADER RANGE")
s_static("GET / HTTP/1.1\r\n")
s_static("Range")
s_delim(":")
s_delim(" ")
s_string("bytes")
s_delim("=")
s_string("500")
s_delim("-")
s_string("999")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Referer header
# Referer: http://www.google.com
########################################################################################################################
s_initialize("HTTP HEADER REFERER")
s_static("GET / HTTP/1.1\r\n")
s_static("Referer")
s_delim(":")
s_delim(" ")
s_string("http://www.google.com")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz TE header
# TE: trailers, deflate
########################################################################################################################
s_initialize("HTTP HEADER TE")
s_static("GET / HTTP/1.1\r\n")
s_static("TE")
s_delim(":")
s_delim(" ")
s_string("trailers")
s_delim(",")
s_delim(" ")
s_string("deflate")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Upgrade header
# Upgrade: HTTP/2.0, SHTTP/1.3, IRC/6.9, RTA/x11
########################################################################################################################
s_initialize("HTTP HEADER UPGRADE")
s_static("GET / HTTP/1.1\r\n")
s_static("Upgrade")
s_delim(":")
s_delim(" ")
s_string("HTTP")
s_delim("/")
s_string("2")
s_delim(".")
s_string("0")
s_delim(",")
s_delim(" ")
s_string("SHTTP")
s_delim("/")
s_string("1")
s_delim(".")
s_string("3")
s_delim(",")
s_delim(" ")
s_string("IRC")
s_delim("/")
s_string("6")
s_delim(".")
s_string("9")
s_delim(",")
s_delim(" ")
s_string("RTA")
s_delim("/")
s_string("x11")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz User Agent header
# User-Agent: Mozilla/5.0 (Windows; U)
########################################################################################################################
s_initialize("HTTP HEADER USERAGENT")
s_static("GET / HTTP/1.1\r\n")
s_static("User-Agent")
s_delim(":")
s_delim(" ")
s_string("Mozilla/5.0 (Windows; U)")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Via header
# Via: 1.0 derp, 1.1 derp.com (Apache/1.1)
########################################################################################################################
s_initialize("HTTP HEADER VIA")
s_static("GET / HTTP/1.1\r\n")
s_static("Via")
s_delim(":")
s_delim(" ")
s_string("1")
s_delim(".")
s_string("0")
s_delim(" ")
s_string("derp")
s_delim(",")
s_delim(" ")
s_string("1")
s_delim(".")
s_string("1")
s_delim(" ")
s_string("derp.com")
s_delim(" ")
s_delim("(")
s_string("Apache")
s_delim("/")
s_string("1")
s_delim(".")
s_string("1")
s_delim(")")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz Warning header
# Warning: 4141 Sulley Rocks!
########################################################################################################################
s_initialize("HTTP HEADER WARNING")
s_static("GET / HTTP/1.1\r\n")
s_static("Warning")
s_delim(":")
s_delim(" ")
s_string("4141")
s_delim(" ")
s_string("Sulley Rocks!")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz X-att-deviceid header
# x-att-deviceid: DerpPhone/Rev2309
########################################################################################################################
s_initialize("HTTP HEADER XATTDEVICEID")
s_static("GET / HTTP/1.1\r\n")
s_static("x-att-deviceid")
s_delim(":")
s_delim(" ")
s_string("DerpPhone")
s_delim("/")
s_string("Rev2309")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz X-Do-Not-Track header
# X-Do-Not-Track: 1
########################################################################################################################
s_initialize("HTTP HEADER XDONOTTRACK")
s_static("GET / HTTP/1.1\r\n")
s_static("X-Do-Not-Track")
s_delim(":")
s_delim(" ")
s_string("1")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz X-Forwarded-For header
# X-Forwarded-For: client1, proxy1, proxy2
########################################################################################################################
s_initialize("HTTP HEADER XFORWARDEDFOR")
s_static("GET / HTTP/1.1\r\n")
s_static("X-Forwarded-For")
s_delim(":")
s_delim(" ")
s_string("client1")
s_delim(",")
s_delim(" ")
s_string("proxy2")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz X-Requested-With header
# X-Requested-With: XMLHttpRequest
########################################################################################################################
s_initialize("HTTP HEADER XREQUESTEDWITH")
s_static("GET / HTTP/1.1\r\n")
s_static("X-Requested-With")
s_delim(":")
s_delim(" ")
s_string("XMLHttpRequest")
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz X-WAP-Profile header
# x-wap-profile: http://wap.samsungmobile.com/uaprof/SGH-I777.xml
########################################################################################################################
s_initialize("HTTP HEADER XWAPPROFILE")
s_static("GET / HTTP/1.1\r\n")
s_static("x-wap-profile")
s_delim(":")
s_delim(" ")
s_string("http")
s_delim(":")
s_delim("/")
s_delim("/")
s_string("wap.samsungmobile.com/uaprof/SGH-I777")
s_static(".xml")
s_static("\r\n\r\n")
########NEW FILE########
__FILENAME__ = http_post
from sulley import *
########################################################################################################################
# All POST mimetypes that I could think of/find
########################################################################################################################
# List of all blocks defined here (for easy copy/paste)
"""
sess.connect(s_get("HTTP VERBS POST"))
sess.connect(s_get("HTTP VERBS POST ALL"))
sess.connect(s_get("HTTP VERBS POST REQ"))
"""

########################################################################################################################
# Fuzz POST requests with most MIMETypes known
########################################################################################################################
s_initialize("HTTP VERBS POST ALL")
s_static("POST / HTTP/1.1\r\n")
s_static("Content-Type: ")
s_group("mimetypes",values=["audio/basic","audio/x-mpeg","drawing/x-dwf","graphics/x-inventor","image/x-portable-bitmap",
                   "message/external-body","message/http","message/news","message/partial","message/rfc822",
                   "multipart/alternative","multipart/appledouble","multipart/digest","multipart/form-data",
                   "multipart/header-set","multipart/mixed","multipart/parallel","multipart/related","multipart/report",
                   "multipart/voice-message","multipart/x-mixed-replace","text/css","text/enriched","text/html",
                   "text/javascript","text/plain","text/richtext","text/sgml","text/tab-separated-values","text/vbscript",
                   "video/x-msvideo","video/x-sgi-movie","workbook/formulaone","x-conference/x-cooltalk","x-form/x-openscape",
                   "x-music/x-midi","x-script/x-wfxclient","x-world/x-3dmf"])
if s_block_start("mime", group="mimetypes"):
    s_static("\r\n")
    s_static("Content-Length: ")
    s_size("post blob", format="ascii", signed=True, fuzzable=True)
    s_static("\r\n\r\n")
s_block_end()

if s_block_start("post blob"):
    s_string("A"*100 + "=" + "B"*100)
s_block_end()
s_static("\r\n\r\n")

########################################################################################################################
# Basic fuzz of post payloads
########################################################################################################################
s_initialize("HTTP VERBS POST")
s_static("POST / HTTP/1.1\r\n")
s_static("Content-Type: ")
s_string("application/x-www-form-urlencoded")
s_static("\r\n")
s_static("Content-Length: ")
s_size("post blob", format="ascii", signed=True, fuzzable=True)
s_static("\r\n")
if s_block_start("post blob"):
    s_string("A"*100 + "=" + "B"*100)
s_block_end()
s_static("\r\n\r\n")

########################################################################################################################
# Fuzz POST request MIMETypes
########################################################################################################################
s_initialize("HTTP VERBS POST REQ")
s_static("POST / HTTP/1.1\r\n")
s_static("Content-Type: ")
s_string("application")
s_delim("/")
s_string("x")
s_delim("-")
s_string("www")
s_delim("-")
s_string("form")
s_delim("-")
s_string("urlencoded")
s_static("\r\n")
s_static("Content-Length: ")
s_size("post blob", format="ascii", signed=True, fuzzable=True)
s_static("\r\n")
if s_block_start("post blob"):
    s_string("A"*100 + "=" + "B"*100)
s_block_end()
s_static("\r\n\r\n")
########NEW FILE########
__FILENAME__ = jabber
from sulley import *


########################################################################################################################
s_initialize("chat init")

"""
<?xml version="1.0" encoding="UTF-8" ?>
<stream:stream to="192.168.200.17" xmlns="jabber:client" xmlns:stream="http://etherx.jabber.org/streams">
"""

# i'll fuzz these bitches later.
# xxx - still need to figure out how to incorporate dynamic IPs
s_static('<?xml version="1.0" encoding="UTF-8" ?>')
s_static('<stream:stream to="152.67.137.126" xmlns="jabber:client" xmlns:stream="http://etherx.jabber.org/streams">')


########################################################################################################################
s_initialize("chat message")
s_static('<message to="TSR@GIZMO" type="chat">\n')
s_static('<body></body>\n')
s_static('<html xmlns="http://www.w3.org/1999/xhtml"><body></body></html><x xmlns="jabber:x:event">\n')
s_static('<composing/>\n')
s_static('<id></id>\n')
s_static('</x>\n')
s_static('</message>\n')

# s_static('<message to="TSR@GIZMO" type="chat">\n')
s_delim("<")
s_string("message")
s_delim(" ")
s_string("to")
s_delim("=")
s_delim('"')
s_string("TSR@GIZMO")
s_delim('"')
s_static(' type="chat"')
s_delim(">")
s_delim("\n")

# s_static('<body>hello from python!</body>\n')
s_static("<body>")
s_string("hello from python!")
s_static("</body>\n")

# s_static('<html xmlns="http://www.w3.org/1999/xhtml"><body><font face="Helvetica" ABSZ="12" color="#000000">hello from python</font></body></html><x xmlns="jabber:x:event">\n')
s_static('<html xmlns="http://www.w3.org/1999/xhtml"><body>')
s_static("<")
s_string("font")
s_static(' face="')
s_string("Helvetica")
s_string('" ABSZ="')
s_word(12, format="ascii", signed=True)
s_static('" color="')
s_string("#000000")
s_static('">')
s_string("hello from python")
s_static('</font></body></html><x xmlns="jabber:x:event">\n')

s_static('<composing/>\n')
s_static('</x>\n')
s_static('</message>\n')

########NEW FILE########
__FILENAME__ = ldap
from sulley import *

"""
Application number	Application
0	BindRequest
1	BindResponse
2	UnbindRequest
3	SearchRequest
4	SearchResponse
5	ModifyRequest
6	ModifyResponse
7	AddRequest
8	AddResponse
9	DelRequest
10	DelResponse
11	ModifyRDNRequest
12	ModifyRDNResponse
13	CompareRequest
14	CompareResponse
15	AbandonRequest
"""

########################################################################################################################
s_initialize("anonymous bind")

# all ldap messages start with this.
s_static("\x30")

# length of entire envelope.
s_static("\x84")
s_sizer("envelope", endian=">")

if s_block_start("envelope"):
    s_static("\x02\x01\x01")        # message id (always one)
    s_static("\x60")                # bind request (0)

    s_static("\x84")
    s_sizer("bind request", endian=">")

    if s_block_start("bind request"):
        s_static("\x02\x01\x03")    # version

        s_lego("ber_string", "anonymous")
        s_lego("ber_string", "foobar", options={"prefix":"\x80"})   # 0x80 is "simple" authentication
    s_block_end()
s_block_end()


########################################################################################################################
s_initialize("search request")

# all ldap messages start with this.
s_static("\x30")

# length of entire envelope.
s_static("\x84")
s_sizer("envelope", endian=">", fuzzable=True)

if s_block_start("envelope"):
    s_static("\x02\x01\x02")        # message id (always one)
    s_static("\x63")                # search request (3)

    s_static("\x84")
    s_sizer("searchRequest", endian=">", fuzzable=True)

    if s_block_start("searchRequest"):
        s_static("\x04\x00")        # static empty string ... why?
        s_static("\x0a\x01\x00")    # scope: baseOjbect (0)
        s_static("\x0a\x01\x00")    # deref: never (0)
        s_lego("ber_integer", 1000) # size limit
        s_lego("ber_integer", 30)   # time limit
        s_static("\x01\x01\x00")    # typesonly: false
        s_lego("ber_string", "objectClass", options={"prefix":"\x87"})
        s_static("\x30")

        s_static("\x84")
        s_sizer("attributes", endian=">")

        if s_block_start("attributes"):
            s_lego("ber_string", "1.1")
        s_block_end("attributes")

    s_block_end("searchRequest")
s_block_end("envelope")
########NEW FILE########
__FILENAME__ = mcafee
from sulley import *

from struct import *

# stupid one byte XOR
def mcafee_epo_xor (buf, poly=0xAA):
    l = len(buf)
    new_buf = ""

    for char in buf:
        new_buf += chr(ord(char) ^ poly)

    return new_buf

########################################################################################################################
s_initialize("mcafee_epo_framework_tcp")
"""
    McAfee FrameworkService.exe TCP port 8081
"""

s_static("POST", name="post_verb")
s_delim(" ")
s_group("paths", ["/spipe/pkg", "/spipe/file", "default.htm"])
s_delim("?")
s_string("URL")
s_delim("=")
s_string("TESTFILE")
s_delim("\r\n")

s_static("Content-Length:")
s_delim(" ")
s_size("payload", format="ascii")
s_delim("\r\n\r\n")

if s_block_start("payload"):
    s_string("TESTCONTENTS")
    s_delim("\r\n")
s_block_end()


########################################################################################################################
s_initialize("mcafee_epo_framework_udp")
"""
    McAfee FrameworkService.exe UDP port 8082
"""

s_static('Type=\"AgentWakeup\"', name="agent_wakeup")
s_static('\"DataSize=\"')
s_size("data", format="ascii") # must be over 234

if s_block_start("data", encoder=mcafee_epo_xor):
    s_static("\x50\x4f", name="signature")
    s_group(values=[pack('<L', 0x40000001), pack('<L', 0x30000001), pack('<L', 0x20000001)], name="opcode")
    s_size("data", length=4) #XXX: needs to be size of data - 1 !!!

    s_string("size", size=210)
    s_static("EPO\x00")
    s_dword(1, name="other_opcode")

s_block_end()

########################################################################################################################
s_initialize("network_agent_udp")
"""
    McAfee Network Agent UDP/TCP port 6646
"""

s_size("kit_and_kaboodle", endian='>', fuzzable=True)

if s_block_start("kit_and_kaboodle"):
    # xxx - command? might want to fuzz this later.
    s_static("\x00\x00\x00\x02")
    
    # dunno what this is.
    s_static("\x00\x00\x00\x00")
    
    # here comes the first tag.
    s_static("\x00\x00\x00\x01")

    s_size("first_tag", endian='>', fuzzable=True)
    if s_block_start("first_tag"):
        s_string("McNAUniqueId", encoding="utf-16-le")
    s_block_end()

    # here comes the second tag.
    s_static("\x0b\x00\x00\x00")
    
    s_size("second_tag", fuzzable=True)
    if s_block_start("second_tag"):
        s_string("babee6e9-1cba-45be-9c81-05a3fb486ed7")
    s_block_end()
s_block_end()
########NEW FILE########
__FILENAME__ = ndmp
from sulley import *

import struct
import time

ndmp_messages = \
[
            # Connect Interface
    0x900,  # NDMP_CONNECT_OPEN
    0x901,  # NDMP_CONECT_CLIENT_AUTH
    0x902,  # NDMP_CONNECT_CLOSE
    0x903,  # NDMP_CONECT_SERVER_AUTH

            # Config Interface
    0x100,  # NDMP_CONFIG_GET_HOST_INFO
    0x102,  # NDMP_CONFIG_GET_CONNECTION_TYPE
    0x103,  # NDMP_CONFIG_GET_AUTH_ATTR
    0x104,  # NDMP_CONFIG_GET_BUTYPE_INFO
    0x105,  # NDMP_CONFIG_GET_FS_INFO
    0x106,  # NDMP_CONFIG_GET_TAPE_INFO
    0x107,  # NDMP_CONFIG_GET_SCSI_INFO
    0x108,  # NDMP_CONFIG_GET_SERVER_INFO

            # SCSI Interface
    0x200,  # NDMP_SCSI_OPEN
    0x201,  # NDMP_SCSI_CLOSE
    0x202,  # NDMP_SCSI_GET_STATE
    0x203,  # NDMP_SCSI_SET_TARGET
    0x204,  # NDMP_SCSI_RESET_DEVICE
    0x205,  # NDMP_SCSI_RESET_BUS
    0x206,  # NDMP_SCSI_EXECUTE_CDB

            # Tape Interface
    0x300,  # NDMP_TAPE_OPEN
    0x301,  # NDMP_TAPE_CLOSE
    0x302,  # NDMP_TAPE_GET_STATE
    0x303,  # NDMP_TAPE_MTIO
    0x304,  # NDMP_TAPE_WRITE
    0x305,  # NDMP_TAPE_READ
    0x307,  # NDMP_TAPE_EXECUTE_CDB

            # Data Interface
    0x400,  # NDMP_DATA_GET_STATE
    0x401,  # NDMP_DATA_START_BACKUP
    0x402,  # NDMP_DATA_START_RECOVER
    0x403,  # NDMP_DATA_ABORT
    0x404,  # NDMP_DATA_GET_ENV
    0x407,  # NDMP_DATA_STOP
    0x409,  # NDMP_DATA_LISTEN
    0x40a,  # NDMP_DATA_CONNECT

            # Notify Interface
    0x501,  # NDMP_NOTIFY_DATA_HALTED
    0x502,  # NDMP_NOTIFY_CONNECTED
    0x503,  # NDMP_NOTIFY_MOVER_HALTED
    0x504,  # NDMP_NOTIFY_MOVER_PAUSED
    0x505,  # NDMP_NOTIFY_DATA_READ

            # Log Interface
    0x602,  # NDMP_LOG_FILES
    0x603,  # NDMP_LOG_MESSAGE

            # File History Interface
    0x703,  # NDMP_FH_ADD_FILE
    0x704,  # NDMP_FH_ADD_DIR
    0x705,  # NDMP_FH_ADD_NODE

            # Mover Interface
    0xa00,  # NDMP_MOVER_GET_STATE
    0xa01,  # NDMP_MOVER_LISTEN
    0xa02,  # NDMP_MOVER_CONTINUE
    0xa03,  # NDMP_MOVER_ABORT
    0xa04,  # NDMP_MOVER_STOP
    0xa05,  # NDMP_MOVER_SET_WINDOW
    0xa06,  # NDMP_MOVER_READ
    0xa07,  # NDMP_MOVER_CLOSE
    0xa08,  # NDMP_MOVER_SET_RECORD_SIZE
    0xa09,  # NDMP_MOVER_CONNECT

            # Reserved for the vendor specific usage (from 0xf000 to 0xffff)
    0xf000, # NDMP_VENDORS_BASE

            # Reserved for Prototyping (from 0xff00 to 0xffff)
    0xff00, # NDMP_RESERVED_BASE
]


########################################################################################################################
s_initialize("Veritas NDMP_CONECT_CLIENT_AUTH")

# the first bit is the last frag flag, we'll always set it and truncate our size to 3 bytes.
# 3 bytes of size gives us a max 16mb ndmp message, plenty of space.
s_static("\x80")
s_size("request", length=3, endian=">")

if s_block_start("request"):
    if s_block_start("ndmp header"):
        s_static(struct.pack(">L", 1),           name="sequence")
        s_static(struct.pack(">L", time.time()), name="timestamp")
        s_static(struct.pack(">L", 0),           name="message type")    # request (0)
        s_static(struct.pack(">L", 0x901),       name="NDMP_CONECT_CLIENT_AUTH")
        s_static(struct.pack(">L", 1),           name="reply sequence")
        s_static(struct.pack(">L", 0),           name="error")
    s_block_end("ndmp header")

    s_group("auth types", values=[struct.pack(">L", 190), struct.pack(">L", 5), struct.pack(">L", 4)])

    if s_block_start("body", group="auth types"):
        # do random data.
        s_random(0, min_length=1000, max_length=50000, num_mutations=500)

        # random valid XDR string.
        #s_lego("xdr_string", "pedram")
    s_block_end("body")
s_block_end("request")


########################################################################################################################
s_initialize("Veritas Proprietary Message Types")

# the first bit is the last frag flag, we'll always set it and truncate our size to 3 bytes.
# 3 bytes of size gives us a max 16mb ndmp message, plenty of space.
s_static("\x80")
s_size("request", length=3, endian=">")

if s_block_start("request"):
    if s_block_start("ndmp header"):
        s_static(struct.pack(">L", 1),           name="sequence")
        s_static(struct.pack(">L", time.time()), name="timestamp")
        s_static(struct.pack(">L", 0),           name="message type")    # request (0)

        s_group("prop ops", values = \
            [
                struct.pack(">L", 0xf315),      # file list?
                struct.pack(">L", 0xf316),
                struct.pack(">L", 0xf317),
                struct.pack(">L", 0xf200),      #
                struct.pack(">L", 0xf201),
                struct.pack(">L", 0xf202),
                struct.pack(">L", 0xf31b),
                struct.pack(">L", 0xf270),      # send strings like NDMP_PROP_PEER_PROTOCOL_VERSION
                struct.pack(">L", 0xf271),
                struct.pack(">L", 0xf33b),
                struct.pack(">L", 0xf33c),
            ])

        s_static(struct.pack(">L", 1),           name="reply sequence")
        s_static(struct.pack(">L", 0),           name="error")
    s_block_end("ndmp header")

    if s_block_start("body", group="prop ops"):
        s_random("\x00\x00\x00\x00", min_length=1000, max_length=50000, num_mutations=100)
    s_block_end("body")
s_block_end("request")
########NEW FILE########
__FILENAME__ = rendezvous
from sulley import *

########################################################################################################################
s_initialize("trillian 1")

s_static("\x00\x00")                        # transaction ID
s_static("\x00\x00")                        # flags (standard query)
s_word(1, endian=">")                       # number of questions
s_word(0, endian=">", fuzzable=False)       # answer RRs
s_word(0, endian=">", fuzzable=False)       # authority RRs
s_word(0, endian=">", fuzzable=False)       # additional RRs

# queries
s_lego("dns_hostname", "_presence._tcp.local")
s_word(0x000c, endian=">")                  # type  = pointer
s_word(0x8001, endian=">")                  # class = flush


########################################################################################################################
s_initialize("trillian 2")

if s_block_start("pamini.local"):
    if s_block_start("header"):
        s_static("\x00\x00")                        # transaction ID
        s_static("\x00\x00")                        # flags (standard query)
        s_word(2, endian=">")                       # number of questions
        s_word(0, endian=">", fuzzable=False)       # answer RRs
        s_word(2, endian=">", fuzzable=False)       # authority RRs
        s_word(0, endian=">", fuzzable=False)       # additional RRs
    s_block_end()

    # queries
    s_lego("dns_hostname", "pamini.local")
    s_word(0x00ff, endian=">")                      # type  = any
    s_word(0x8001, endian=">")                      # class = flush
s_block_end()

s_lego("dns_hostname", "pedram@PAMINI._presence._tcp")
s_word(0x00ff, endian=">")                          # type  = any
s_word(0x8001, endian=">")                          # class = flush


# authoritative nameservers
s_static("\xc0")                                    # offset specifier
s_size("header", length=1)                          # offset to pamini.local
s_static("\x00\x01")                                # type  = A (host address)
s_static("\x00\x01")                                # class = in
s_static("\x00\x00\x00\xf0")                        # ttl 4 minutes
s_static("\x00\x04")                                # data length
s_static(chr(152) + chr(67) + chr(137) + chr(53))   # ip address

s_static("\xc0")                                    # offset specifier
s_size("pamini.local", length=1)                    # offset to pedram@PAMINI...
s_static("\x00\x21")                                # type  = SRV (service location)
s_static("\x00\x01")                                # class = in
s_static("\x00\x00\x00\xf0")                        # ttl 4 minutes
s_static("\x00\x08")                                # data length
s_static("\x00\x00")                                # priority
s_static("\x00\x00")                                # weight
s_static("\x14\xb2")                                # port
s_static("\xc0")                                    # offset specifier
s_size("header", length=1)                          # offset to pamini.local


########################################################################################################################
s_initialize("trillian 3")

if s_block_start("pamini.local"):
    if s_block_start("header"):
        s_static("\x00\x00")                        # transaction ID
        s_static("\x00\x00")                        # flags (standard query)
        s_word(2, endian=">")                       # number of questions
        s_word(0, endian=">", fuzzable=False)       # answer RRs
        s_word(2, endian=">", fuzzable=False)       # authority RRs
        s_word(0, endian=">", fuzzable=False)       # additional RRs
    s_block_end()

    # queries
    s_lego("dns_hostname", "pamini.local")
    s_word(0x00ff, endian=">")                      # type  = any
    s_word(0x0001, endian=">")                      # class = in
s_block_end()

s_lego("dns_hostname", "pedram@PAMINI._presence._tcp")
s_word(0x00ff, endian=">")                          # type  = any
s_word(0x0001, endian=">")                          # class = in


# authoritative nameservers
s_static("\xc0")                                    # offset specifier
s_size("header", length=1)                          # offset to pamini.local
s_static("\x00\x01")                                # type  = A (host address)
s_static("\x00\x01")                                # class = in
s_static("\x00\x00\x00\xf0")                        # ttl 4 minutes
s_static("\x00\x04")                                # data length
s_static(chr(152) + chr(67) + chr(137) + chr(53))   # ip address

s_static("\xc0")                                    # offset specifier
s_size("pamini.local", length=1)                    # offset to pedram@PAMINI...
s_static("\x00\x21")                                # type  = SRV (service location)
s_static("\x00\x01")                                # class = in
s_static("\x00\x00\x00\xf0")                        # ttl 4 minutes
s_static("\x00\x08")                                # data length
s_static("\x00\x00")                                # priority
s_static("\x00\x00")                                # weight
s_static("\x14\xb2")                                # port
s_static("\xc0")                                    # offset specifier
s_size("header", length=1)                          # offset to pamini.local
########NEW FILE########
__FILENAME__ = stun
"""
STUN: Simple Traversal of UDP through NAT
Gizmo binds this service on UDP port 5004 / 5005
http://www.vovida.org/
"""

from sulley import *

########################################################################################################################
s_initialize("binding request")

# message type 0x0001: binding request.
s_static("\x00\x01")

# message length.
s_sizer("attributes", length=2, endian=">", name="message length", fuzzable=True)

# message transaction id.
s_static("\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd\xee\xff")

if s_block_start("attributes"):
    # attribute type
    #   0x0001: mapped address
    #   0x0003: change request
    #   0x0004: source address
    #   0x0005: changed address
    #   0x8020: xor mapped address
    #   0x8022: server
    s_word(0x0003, endian=">")

    s_sizer("attribute", length=2, endian=">", name="attribute length", fuzzable=True)

    if s_block_start("attribute"):
        # default valid null block
        s_string("\x00\x00\x00\x00")
    s_block_end()

s_block_end()

# toss out some large strings when the lengths are anything but valid.
if s_block_start("fuzz block 1", dep="attribute length", dep_value=4, dep_compare="!="):
    s_static("A"*5000)
s_block_end()

# toss out some large strings when the lengths are anything but valid.
if s_block_start("fuzz block 2", dep="message length", dep_value=8, dep_compare="!="):
    s_static("B"*5000)
s_block_end()


########################################################################################################################
s_initialize("binding response")

# message type 0x0101: binding response
########NEW FILE########
__FILENAME__ = trend
from sulley import *

import struct

# crap ass trend xor "encryption" routine for control manager (20901)
def trend_xor_encode (str):
    '''
    Simple bidirectional XOR "encryption" routine used by this service.
    '''
    key = 0xA8534344
    ret = ""

    # pad to 4 byte boundary.
    pad = 4 - (len(str) % 4)

    if pad == 4:
        pad = 0

    str += "\x00" * pad

    while str:
        dword  = struct.unpack("<L", str[:4])[0]
        str    = str[4:]
        dword ^= key
        ret   += struct.pack("<L", dword)
        key    = dword

    return ret


# crap ass trend xor "encryption" routine for control manager (20901)
def trend_xor_decode (str):
    key = 0xA8534344
    ret = ""

    while str:
        dword = struct.unpack("<L", str[:4])[0]
        str   = str[4:]
        tmp   = dword
        tmp  ^= key
        ret  += struct.pack("<L", tmp)
        key   = dword

    return ret


# dce rpc request encoder used for trend server protect 5168 RPC service.
# opnum is always zero.
def rpc_request_encoder (data):
    return utils.dcerpc.request(0, data)


########################################################################################################################
s_initialize("20901")
"""
    Trend Micro Control Manager (DcsProcessor.exe)
    http://bakemono/mediawiki/index.php/Trend_Micro:Control_Manager

    This fuzz found nothing! need to uncover more protocol details. See also: pedram's pwned notebook page 3, 4.
"""

# dword 1, error: 0x10000001, do something:0x10000002, 0x10000003 (>0x10000002)
s_group("magic", values=["\x02\x00\x00\x10", "\x03\x00\x00\x10"])

# dword 2, size of body
s_size("body")

# dword 3, crc32(block) (copy from eax at 0041EE8B)
# XXX - CRC is non standard, nop out jmp at 0041EE99 and use bogus value:
#s_checksum("body", algorithm="crc32")
s_static("\xff\xff\xff\xff")

# the body of the trend request contains a variable number of (2-byte) TLVs
if s_block_start("body", encoder=trend_xor_encode):
    s_word(0x0000, full_range=True)     # completely fuzz the type
    s_size("string1", length=2)         # valid length
    if s_block_start("string1"):        # fuzz string
        s_string("A"*1000)
        s_block_end()

    s_random("\x00\x00", 2, 2)          # random type
    s_size("string2", length=2)         # valid length
    if s_block_start("string2"):        # fuzz string
        s_string("B"*10)
    s_block_end()

    # try a table overflow.
    if s_block_start("repeat me"):
        s_random("\x00\x00", 2, 2)      # random type
        s_size("string3", length=2)     # valid length
        if s_block_start("string3"):    # fuzz string
            s_string("C"*10)
            s_block_end()
    s_block_end()

    # repeat string3 a bunch of times.
    s_repeat("repeat me", min_reps=100, max_reps=1000, step=50)
s_block_end("body")


########################################################################################################################
"""
    Trend Micro Server Protect (SpNTsvc.exe)

    This fuzz uncovered a bunch of DoS and code exec bugs. The obvious code exec bugs were documented and released to
    the vendor. See also: pedram's pwned notebook page 1, 2.

    // opcode: 0x00, address: 0x65741030
    // uuid: 25288888-bd5b-11d1-9d53-0080c83a5c2c
    // version: 1.0

    error_status_t rpc_opnum_0 (
    [in] handle_t arg_1,                          // not sent on wire
    [in] long trend_req_num,
    [in][size_is(arg_4)] byte overflow_str[],
    [in] long arg_4,
    [out][size_is(arg_6)] byte arg_5[],           // not sent on wire
    [in] long arg_6
    );
"""

for op, submax in [(0x1, 22), (0x2, 19), (0x3, 85), (0x5, 25), (0xa, 49), (0x1f, 25)]:
    s_initialize("5168: op-%x" % op)
    if s_block_start("everything", encoder=rpc_request_encoder):
        # [in] long trend_req_num,
        s_group("subs", values=map(chr, range(1, submax)))
        s_static("\x00")                 # subs is actually a little endian word
        s_static(struct.pack("<H", op))  # opcode

        # [in][size_is(arg_4)] byte overflow_str[],
        s_size("the string")
        if s_block_start("the string", group="subs"):
            s_static("A" * 0x5000, name="arg3")
        s_block_end()

        # [in] long arg_4,
        s_size("the string")

        # [in] long arg_6
        s_static(struct.pack("<L", 0x5000)) # output buffer size
    s_block_end()


########################################################################################################################
s_initialize("5005")
"""
    Trend Micro Server Protect (EarthAgent.exe)
    
    Some custom protocol listening on TCP port 5005
"""

s_static("\x21\x43\x65\x87")      # magic
# command
s_static("\x00\x00\x00\x00")  # dunno
s_static("\x01\x00\x00\x00")  # dunno, but observed static
# length
s_static("\xe8\x03\x00\x00")  # dunno, but observed static
s_static("\x00\x00\x00\x00")  # dunno, but observed static

########NEW FILE########
__FILENAME__ = xbox
"""
mediaconnect port 2869
"""

from sulley import *

########################################################################################################################
s_initialize("mediaconnect: get album list")

# POST /upnphost/udhisapi.dll?control=uuid:848a20cc-91bc-4a02-8180-187baa537527+urn:microsoft-com:serviceId:MSContentDirectory HTTP/1.1
s_group("verbs", values=["GET", "POST"])
s_delim(" ")
s_delim("/")
s_string("upnphost/udhisapi.dll")
s_delim("?")
s_string("control")
s_delim("=")
s_string("uuid")
s_delim(":")
s_string("848a20cc-91bc-4a02-8180-187baa537527")
s_delim("+")
s_static("urn")
s_delim(":")
s_string("microsoft-com:serviceId:MSContentDirectory")
s_static(" HTTP/1.1\r\n")

# User-Agent: Xbox/2.0.4552.0 UPnP/1.0 Xbox/2.0.4552.0
# we take this opportunity to fuzz headers in general.
s_string("User-Agent")
s_delim(":")
s_delim(" ")
s_string("Xbox")
s_delim("/")
s_string("2.0.4552.0 UPnP/1.0 Xbox/2.0.4552.0")
s_static("\r\n")

# Connection: Keep-alive
s_static("Connection: ")
s_string("Keep-alive")
s_static("\r\n")

# Host:10.10.20.111
s_static("Host: 10.10.20.111")
s_static("\r\n")

# SOAPACTION: "urn:schemas-microsoft-com:service:MSContentDirectory:1#Search"
s_static("SOAPACTION: ")
s_delim("\"")
s_static("urn")
s_delim(":")
s_string("schemas-microsoft-com")
s_static(":")
s_string("service")
s_static(":")
s_string("MSContentDirectory")
s_static(":")
s_string("1")
s_delim("#")
s_string("Search")
s_delim("\"")
s_static("\r\n")

# CONTENT-TYPE: text/xml; charset="utf-8"
s_static("CONTENT-TYPE: text/xml; charset=\"utf-8\"")
s_static("\r\n")

# Content-Length: 547
s_static("Content-Length: ")
s_sizer("content", format="ascii", signed=True, fuzzable=True)
s_static("\r\n\r\n")

if s_block_start("content"):
    # <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    s_delim("<")
    s_string("s")
    s_delim(":")
    s_string("Envelope")
    s_static(" xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\" ")
    s_static("s:")
    s_string("encodingStyle")
    s_delim("=")
    s_string("\"http://schemas.xmlsoap.org/soap/encoding/\"")
    s_delim(">")

    s_static("<s:Body>")
    s_static("<u:Search xmlns:u=\"urn:schemas-microsoft-com:service:MSContentDirectory:1\">")

    # <ContainerID>7</ContainerID>
    s_static("<ContainerID>")
    s_dword(7, format="ascii", signed=True)
    s_static("</ContainerID>")

    # <SearchCriteria>(upnp:class = &quot;object.container.album.musicAlbum&quot;)</SearchCriteria>
    s_static("<SearchCriteria>(upnp:class = &quot;")
    s_string("object.container.album.musicAlbum")
    s_static("&quot;)</SearchCriteria>")

    # <Filter>dc:title,upnp:artist</Filter>
    s_static("<Filter>")
    s_delim("dc")
    s_delim(":")
    s_string("title")
    s_delim(",")
    s_string("upnp")
    s_delim(":")
    s_string("artist")
    s_static("</Filter>")

    # <StartingIndex>0</StartingIndex>
    s_static("<StartingIndex>")
    s_dword(0, format="ascii", signed=True)
    s_static("</StartingIndex>")

    # <RequestedCount>1000</RequestedCount>
    s_static("<RequestedCount>")
    s_dword(1000, format="ascii", signed=True)
    s_static("</RequestedCount>")

    s_static("<SortCriteria>+dc:title</SortCriteria>")
    s_static("</u:Search>")
    s_static("</s:Body>")

    # </s:Envelope>
    s_delim("<")
    s_delim("/")
    s_delim("s")
    s_delim(":")
    s_string("Envelope")
    s_delim(">")

s_block_end()
########NEW FILE########
__FILENAME__ = blocks
import pgraph
import primitives
import sex

import zlib
import hashlib
import struct

REQUESTS = {}
CURRENT  = None

########################################################################################################################
class request (pgraph.node):
    def __init__ (self, name):
        '''
        Top level container instantiated by s_initialize(). Can hold any block structure or primitive. This can
        essentially be thought of as a super-block, root-block, daddy-block or whatever other alias you prefer.

        @type  name: String
        @param name: Name of this request
        '''

        self.name          = name

        self.label         = name    # node label for graph rendering.
        self.stack         = []      # the request stack.
        self.block_stack   = []      # list of open blocks, -1 is last open block.
        self.closed_blocks = {}      # dictionary of closed blocks.
        self.callbacks     = {}      # dictionary of list of sizers / checksums that were unable to complete rendering.
        self.names         = {}      # dictionary of directly accessible primitives.
        self.rendered      = ""      # rendered block structure.
        self.mutant_index  = 0       # current mutation index.
        self.mutant        = None    # current primitive being mutated.


    def mutate (self):
        mutated = False

        for item in self.stack:
            if item.fuzzable and item.mutate():
                mutated = True

                if not isinstance(item, block):
                    self.mutant = item

                break

        if mutated:
            self.mutant_index += 1

        return mutated


    def num_mutations (self):
        '''
        Determine the number of repetitions we will be making.

        @rtype:  Integer
        @return: Number of mutated forms this primitive can take.
        '''

        num_mutations = 0

        for item in self.stack:
            if item.fuzzable:
                num_mutations += item.num_mutations()

        return num_mutations


    def pop (self):
        '''
        The last open block was closed, so pop it off of the block stack.
        '''

        if not self.block_stack:
            raise sex.error("BLOCK STACK OUT OF SYNC")

        self.block_stack.pop()


    def push (self, item):
        '''
        Push an item into the block structure. If no block is open, the item goes onto the request stack. otherwise,
        the item goes onto the last open blocks stack.
        '''

        # if the item has a name, add it to the internal dictionary of names.
        if hasattr(item, "name") and item.name:
            # ensure the name doesn't already exist.
            if item.name in self.names.keys():
                raise sex.error("BLOCK NAME ALREADY EXISTS: %s" % item.name)

            self.names[item.name] = item

        # if there are no open blocks, the item gets pushed onto the request stack.
        # otherwise, the pushed item goes onto the stack of the last opened block.
        if not self.block_stack:
            self.stack.append(item)
        else:
            self.block_stack[-1].push(item)

        # add the opened block to the block stack.
        if isinstance(item, block):
            self.block_stack.append(item)


    def render (self):
        # ensure there are no open blocks lingering.
        if self.block_stack:
            raise sex.error("UNCLOSED BLOCK: %s" % self.block_stack[-1].name)

        # render every item in the stack.
        for item in self.stack:
            item.render()

        # process remaining callbacks.
        for key in self.callbacks.keys():
            for item in self.callbacks[key]:
                item.render()

        def update_size(stack, name):
            # walk recursively through each block to update its size
            blocks = []

            for item in stack:
                if isinstance(item, size):
                    item.render()
                elif isinstance(item, block):
                    blocks += [item]

            for b in blocks:
                update_size(b.stack, b.name)
                b.render()

        # call update_size on each block of the request
        for item in self.stack:
            if isinstance(item, block):
                update_size(item.stack, item.name)
                item.render()

        # now collect, merge and return the rendered items.
        self.rendered = ""

        for item in self.stack:
            self.rendered += item.rendered

        return self.rendered


    def reset (self):
        '''
        Reset every block and primitives mutant state under this request.
        '''

        self.mutant_index  = 1
        self.closed_blocks = {}

        for item in self.stack:
            if item.fuzzable:
                item.reset()


    def walk (self, stack=None):
        '''
        Recursively walk through and yield every primitive and block on the request stack.

        @rtype:  Sulley Primitives
        @return: Sulley Primitives
        '''

        if not stack:
            stack = self.stack

        for item in stack:
            # if the item is a block, step into it and continue looping.
            if isinstance(item, block):
                for item in self.walk(item.stack):
                    yield item
            else:
                yield item


########################################################################################################################
class block:
    def __init__ (self, name, request, group=None, encoder=None, dep=None, dep_value=None, dep_values=[], dep_compare="=="):
        '''
        The basic building block. Can contain primitives, sizers, checksums or other blocks.

        @type  name:        String
        @param name:        Name of the new block
        @type  request:     s_request
        @param request:     Request this block belongs to
        @type  group:       String
        @param group:       (Optional, def=None) Name of group to associate this block with
        @type  encoder:     Function Pointer
        @param encoder:     (Optional, def=None) Optional pointer to a function to pass rendered data to prior to return
        @type  dep:         String
        @param dep:         (Optional, def=None) Optional primitive whose specific value this block is dependant on
        @type  dep_value:   Mixed
        @param dep_value:   (Optional, def=None) Value that field "dep" must contain for block to be rendered
        @type  dep_values:  List of Mixed Types
        @param dep_values:  (Optional, def=[]) Values that field "dep" may contain for block to be rendered
        @type  dep_compare: String
        @param dep_compare: (Optional, def="==") Comparison method to apply to dependency (==, !=, >, >=, <, <=)
        '''

        self.name          = name
        self.request       = request
        self.group         = group
        self.encoder       = encoder
        self.dep           = dep
        self.dep_value     = dep_value
        self.dep_values    = dep_values
        self.dep_compare   = dep_compare

        self.stack         = []     # block item stack.
        self.rendered      = ""     # rendered block contents.
        self.fuzzable      = True   # blocks are always fuzzable because they may contain fuzzable items.
        self.group_idx     = 0      # if this block is tied to a group, the index within that group.
        self.fuzz_complete = False  # whether or not we are done fuzzing this block.
        self.mutant_index  = 0      # current mutation index.


    def mutate (self):
        mutated = False

        # are we done with this block?
        if self.fuzz_complete:
            return False

        #
        # mutate every item on the stack for every possible group value.
        #

        if self.group:
            group_count = self.request.names[self.group].num_mutations()

            # update the group value to that at the current index.
            self.request.names[self.group].value = self.request.names[self.group].values[self.group_idx]

            # mutate every item on the stack at the current group value.
            for item in self.stack:
                if item.fuzzable and item.mutate():
                    mutated = True

                    if not isinstance(item, block):
                        self.request.mutant = item

                    break

            # if the possible mutations for the stack are exhausted.
            if not mutated:
                # increment the group value index.
                self.group_idx += 1

                # if the group values are exhausted, we are done with this block.
                if self.group_idx == group_count:
                    # restore the original group value.
                    self.request.names[self.group].value = self.request.names[self.group].original_value

                # otherwise continue mutating this group/block.
                else:
                    # update the group value to that at the current index.
                    self.request.names[self.group].value = self.request.names[self.group].values[self.group_idx]

                    # this the mutate state for every item in this blocks stack.
                    # NOT THE BLOCK ITSELF THOUGH! (hence why we didn't call self.reset())
                    for item in self.stack:
                        if item.fuzzable:
                            item.reset()

                    # now mutate the first field in this block before continuing.
                    # (we repeat a test case if we don't mutate something)
                    for item in self.stack:
                        if item.fuzzable and item.mutate():
                            mutated = True

                            if not isinstance(item, block):
                                self.request.mutant = item

                            break

        #
        # no grouping, mutate every item on the stack once.
        #

        else:
            for item in self.stack:
                if item.fuzzable and item.mutate():
                    mutated = True

                    if not isinstance(item, block):
                        self.request.mutant = item

                    break

        # if this block is dependant on another field, then manually update that fields value appropriately while we
        # mutate this block. we'll restore the original value of the field prior to continuing.
        if mutated and self.dep:
            # if a list of values was specified, use the first item in the list.
            if self.dep_values:
                self.request.names[self.dep].value = self.dep_values[0]

            # if a list of values was not specified, assume a single value is present.
            else:
                self.request.names[self.dep].value = self.dep_value


        # we are done mutating this block.
        if not mutated:
            self.fuzz_complete = True

            # if we had a dependancy, make sure we restore the original value.
            if self.dep:
                self.request.names[self.dep].value = self.request.names[self.dep].original_value

        if mutated:
            if not isinstance(item, block):
                self.request.mutant = item

        return mutated


    def num_mutations (self):
        '''
        Determine the number of repetitions we will be making.

        @rtype:  Integer
        @return: Number of mutated forms this primitive can take.
        '''

        num_mutations = 0

        for item in self.stack:
            if item.fuzzable:
                num_mutations += item.num_mutations()

        # if this block is associated with a group, then multiply out the number of possible mutations.
        if self.group:
            num_mutations *= len(self.request.names[self.group].values)

        return num_mutations


    def push (self, item):
        '''
        Push an arbitrary item onto this blocks stack.
        '''

        self.stack.append(item)


    def render (self):
        '''
        Step through every item on this blocks stack and render it. Subsequent blocks recursively render their stacks.
        '''

        # add the completed block to the request dictionary.
        self.request.closed_blocks[self.name] = self

        #
        # if this block is dependant on another field and the value is not met, render nothing.
        #

        if self.dep:
            if self.dep_compare == "==":
                if self.dep_values and self.request.names[self.dep].value not in self.dep_values:
                    self.rendered = ""
                    return

                elif not self.dep_values and self.request.names[self.dep].value != self.dep_value:
                    self.rendered = ""
                    return

            if self.dep_compare == "!=":
                if self.dep_values and self.request.names[self.dep].value in self.dep_values:
                    self.rendered = ""
                    return

                elif self.request.names[self.dep].value == self.dep_value:
                    self.rendered = ""
                    return

            if self.dep_compare == ">" and self.dep_value <= self.request.names[self.dep].value:
                self.rendered = ""
                return

            if self.dep_compare == ">=" and self.dep_value < self.request.names[self.dep].value:
                self.rendered = ""
                return

            if self.dep_compare == "<" and self.dep_value >= self.request.names[self.dep].value:
                self.rendered = ""
                return

            if self.dep_compare == "<=" and self.dep_value > self.request.names[self.dep].value:
                self.rendered = ""
                return

        #
        # otherwise, render and encode as usual.
        #

        # recursively render the items on the stack.
        for item in self.stack:
            item.render()

        # now collect and merge the rendered items.
        self.rendered = ""

        for item in self.stack:
            self.rendered += item.rendered

        # if an encoder was attached to this block, call it.
        if self.encoder:
            self.rendered = self.encoder(self.rendered)

        # the block is now closed, clear out all the entries from the request back splice dictionary.
        if self.request.callbacks.has_key(self.name):
            for item in self.request.callbacks[self.name]:
                item.render()


    def reset (self):
        '''
        Reset the primitives on this blocks stack to the starting mutation state.
        '''

        self.fuzz_complete = False
        self.group_idx     = 0

        for item in self.stack:
            if item.fuzzable:
                item.reset()


########################################################################################################################
class checksum:
    checksum_lengths = {"crc32":4, "adler32":4, "md5":16, "sha1":20}

    def __init__(self, block_name, request, algorithm="crc32", length=0, endian="<", name=None):
        '''
        Create a checksum block bound to the block with the specified name. You *can not* create a checksm for any
        currently open blocks.

        @type  block_name: String
        @param block_name: Name of block to apply sizer to
        @type  request:    s_request
        @param request:    Request this block belongs to
        @type  algorithm:  String
        @param algorithm:  (Optional, def=crc32) Checksum algorithm to use. (crc32, adler32, md5, sha1)
        @type  length:     Integer
        @param length:     (Optional, def=0) Length of checksum, specify 0 to auto-calculate
        @type  endian:     Character
        @param endian:     (Optional, def=LITTLE_ENDIAN) Endianess of the bit field (LITTLE_ENDIAN: <, BIG_ENDIAN: >)
        @type  name:       String
        @param name:       Name of this checksum field
        '''

        self.block_name = block_name
        self.request    = request
        self.algorithm  = algorithm
        self.length     = length
        self.endian     = endian
        self.name       = name

        self.rendered   = ""
        self.fuzzable   = False

        if not self.length and self.checksum_lengths.has_key(self.algorithm):
            self.length = self.checksum_lengths[self.algorithm]


    def checksum (self, data):
        '''
        Calculate and return the checksum (in raw bytes) over the supplied data.

        @type  data: Raw
        @param data: Rendered block data to calculate checksum over.

        @rtype:  Raw
        @return: Checksum.
        '''

        if type(self.algorithm) is str:
            if self.algorithm == "crc32":
                return struct.pack(self.endian+"L", zlib.crc32(data))

            elif self.algorithm == "adler32":
                return struct.pack(self.endian+"L", zlib.adler32(data))

            elif self.algorithm == "md5":
                digest = hashlib.md5(data).digest()

                # XXX - is this right?
                if self.endian == ">":
                    (a, b, c, d) = struct.unpack("<LLLL", digest)
                    digest       = struct.pack(">LLLL", a, b, c, d)

                return digest

            elif self.algorithm == "sha1":
                digest = hashlib.sha1(data).digest()

                # XXX - is this right?
                if self.endian == ">":
                    (a, b, c, d, e) = struct.unpack("<LLLLL", digest)
                    digest          = struct.pack(">LLLLL", a, b, c, d, e)

                return digest

            else:
                raise sex.error("INVALID CHECKSUM ALGORITHM SPECIFIED: %s" % self.algorithm)
        else:
            return self.algorithm(data)


    def render (self):
        '''
        Calculate the checksum of the specified block using the specified algorithm.
        '''

        self.rendered = ""

        # if the target block for this sizer is already closed, render the checksum.
        if self.block_name in self.request.closed_blocks:
            block_data    = self.request.closed_blocks[self.block_name].rendered
            self.rendered = self.checksum(block_data)

        # otherwise, add this checksum block to the requests callback list.
        else:
            if not self.request.callbacks.has_key(self.block_name):
                self.request.callbacks[self.block_name] = []

            self.request.callbacks[self.block_name].append(self)


########################################################################################################################
class repeat:
    '''
    This block type is kind of special in that it is a hybrid between a block and a primitive (it can be fuzzed). The
    user does not need to be wary of this fact.
    '''

    def __init__ (self, block_name, request, min_reps=0, max_reps=None, step=1, variable=None, fuzzable=True, name=None):
        '''
        Repeat the rendered contents of the specified block cycling from min_reps to max_reps counting by step. By
        default renders to nothing. This block modifier is useful for fuzzing overflows in table entries. This block
        modifier MUST come after the block it is being applied to.

        @type  block_name: String
        @param block_name: Name of block to apply sizer to
        @type  request:    s_request
        @param request:    Request this block belongs to
        @type  min_reps:   Integer
        @param min_reps:   (Optional, def=0) Minimum number of block repetitions
        @type  max_reps:   Integer
        @param max_reps:   (Optional, def=None) Maximum number of block repetitions
        @type  step:       Integer
        @param step:       (Optional, def=1) Step count between min and max reps
        @type  variable:   Sulley Integer Primitive
        @param variable:   (Optional, def=None) Repititions will be derived from this variable, disables fuzzing
        @type  fuzzable:   Boolean
        @param fuzzable:   (Optional, def=True) Enable/disable fuzzing of this primitive
        @type  name:       String
        @param name:       (Optional, def=None) Specifying a name gives you direct access to a primitive
        '''

        self.block_name    = block_name
        self.request       = request
        self.variable      = variable
        self.min_reps      = min_reps
        self.max_reps      = max_reps
        self.step          = step
        self.fuzzable      = fuzzable
        self.name          = name

        self.value         = self.original_value = ""   # default to nothing!
        self.rendered      = ""                         # rendered value
        self.fuzz_complete = False                      # flag if this primitive has been completely fuzzed
        self.fuzz_library  = []                         # library of static fuzz heuristics to cycle through.
        self.mutant_index  = 0                          # current mutation number
        self.current_reps  = min_reps                   # current number of repetitions

        # ensure the target block exists.
        if self.block_name not in self.request.names:
            raise sex.error("CAN NOT ADD REPEATER FOR NON-EXISTANT BLOCK: %s" % self.block_name)

        # ensure the user specified either a variable to tie this repeater to or a min/max val.
        if self.variable == None and self.max_reps == None:
            raise sex.error("REPEATER FOR BLOCK %s DOES NOT HAVE A MIN/MAX OR VARIABLE BINDING" % self.block_name)

        # if a variable is specified, ensure it is an integer type.
        if self.variable and not isinstance(self.variable, primitives.bit_field):
            print self.variable
            raise sex.error("ATTEMPT TO BIND THE REPEATER FOR BLOCK %s TO A NON INTEGER PRIMITIVE" % self.block_name)

        # if not binding variable was specified, propogate the fuzz library with the repetition counts.
        if not self.variable:
            self.fuzz_library = range(self.min_reps, self.max_reps + 1, self.step)
        # otherwise, disable fuzzing as the repitition count is determined by the variable.
        else:
            self.fuzzable = False


    def mutate (self):
        '''
        Mutate the primitive by stepping through the fuzz library, return False on completion. If variable-bounding is
        specified then fuzzing is implicitly disabled. Instead, the render() routine will properly calculate the
        correct repitition and return the appropriate data.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        '''

        # render the contents of the block we are repeating.
        self.request.names[self.block_name].render()

        # if the target block for this sizer is not closed, raise an exception.
        if self.block_name not in self.request.closed_blocks:
            raise sex.error("CAN NOT APPLY REPEATER TO UNCLOSED BLOCK: %s" % self.block_name)

        # if we've run out of mutations, raise the completion flag.
        if self.mutant_index == self.num_mutations():
            self.fuzz_complete = True

        # if fuzzing was disabled or complete, and mutate() is called, ensure the original value is restored.
        if not self.fuzzable or self.fuzz_complete:
            self.value        = self.original_value
            self.current_reps = self.min_reps
            return False

        if self.variable:
            self.current_reps = self.variable.value
        else:
            self.current_reps = self.fuzz_library[self.mutant_index]

        # set the current value as a multiple of the rendered block based on the current fuzz library count.
        block      = self.request.closed_blocks[self.block_name]
        self.value = block.rendered * self.fuzz_library[self.mutant_index]

        # increment the mutation count.
        self.mutant_index += 1

        return True


    def num_mutations (self):
        '''
        Determine the number of repetitions we will be making.

        @rtype:  Integer
        @return: Number of mutated forms this primitive can take.
        '''

        return len(self.fuzz_library)


    def render (self):
        '''
        Nothing fancy on render, simply return the value.
        '''

        # if the target block for this sizer is not closed, raise an exception.
        if self.block_name not in self.request.closed_blocks:
            raise sex.error("CAN NOT APPLY REPEATER TO UNCLOSED BLOCK: %s" % self.block_name)

        # if a variable-bounding was specified then set the value appropriately.
        if self.variable:
            block      = self.request.closed_blocks[self.block_name]
            self.value = block.rendered * self.variable.value

        self.rendered = self.value
        return self.rendered


    def reset (self):
        '''
        Reset the fuzz state of this primitive.
        '''

        self.fuzz_complete  = False
        self.mutant_index   = 0
        self.value          = self.original_value


########################################################################################################################
class size:
    '''
    This block type is kind of special in that it is a hybrid between a block and a primitive (it can be fuzzed). The
    user does not need to be wary of this fact.
    '''

    def __init__ (self, block_name, request, length=4, endian="<", format="binary", inclusive=False, signed=False, math=None, fuzzable=False, name=None):
        '''
        Create a sizer block bound to the block with the specified name. You *can not* create a sizer for any
        currently open blocks.

        @type  block_name: String
        @param block_name: Name of block to apply sizer to
        @type  request:    s_request
        @param request:    Request this block belongs to
        @type  length:     Integer
        @param length:     (Optional, def=4) Length of sizer
        @type  endian:     Character
        @param endian:     (Optional, def=LITTLE_ENDIAN) Endianess of the bit field (LITTLE_ENDIAN: <, BIG_ENDIAN: >)
        @type  format:     String
        @param format:     (Optional, def=binary) Output format, "binary" or "ascii"
        @type  inclusive:  Boolean
        @param inclusive:  (Optional, def=False) Should the sizer count its own length?
        @type  signed:     Boolean
        @param signed:     (Optional, def=False) Make size signed vs. unsigned (applicable only with format="ascii")
        @type  math:       Function
        @param math:       (Optional, def=None) Apply the mathematical operations defined in this function to the size
        @type  fuzzable:   Boolean
        @param fuzzable:   (Optional, def=False) Enable/disable fuzzing of this sizer
        @type  name:       String
        @param name:       Name of this sizer field
        '''

        self.block_name    = block_name
        self.request       = request
        self.length        = length
        self.endian        = endian
        self.format        = format
        self.inclusive     = inclusive
        self.signed        = signed
        self.math          = math
        self.fuzzable      = fuzzable
        self.name          = name

        self.original_value = "N/A"    # for get_primitive
        self.s_type         = "size"   # for ease of object identification
        self.bit_field      = primitives.bit_field(0, self.length*8, endian=self.endian, format=self.format, signed=self.signed)
        self.rendered       = ""
        self.fuzz_complete  = self.bit_field.fuzz_complete
        self.fuzz_library   = self.bit_field.fuzz_library
        self.mutant_index   = self.bit_field.mutant_index
        self.value          = self.bit_field.value

        if self.math == None:
            self.math = lambda (x): x


    def exhaust (self):
        '''
        Exhaust the possible mutations for this primitive.

        @rtype:  Integer
        @return: The number of mutations to reach exhaustion
        '''

        num = self.num_mutations() - self.mutant_index

        self.fuzz_complete          = True
        self.mutant_index           = self.num_mutations()
        self.bit_field.mutant_index = self.num_mutations()
        self.value                  = self.original_value

        return num


    def mutate (self):
        '''
        Wrap the mutation routine of the internal bit_field primitive.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        '''

        if self.mutant_index == self.num_mutations():
            self.fuzz_complete = True

        self.mutant_index += 1

        return self.bit_field.mutate()


    def num_mutations (self):
        '''
        Wrap the num_mutations routine of the internal bit_field primitive.

        @rtype:  Integer
        @return: Number of mutated forms this primitive can take.
        '''

        return self.bit_field.num_mutations()


    def render (self):
        '''
        Render the sizer.
        '''

        self.rendered = ""

        # if the sizer is fuzzable and we have not yet exhausted the the possible bit field values, use the fuzz value.
        if self.fuzzable and self.bit_field.mutant_index and not self.bit_field.fuzz_complete:
            self.rendered = self.bit_field.render()

        # if the target block for this sizer is already closed, render the size.
        elif self.block_name in self.request.closed_blocks:
            if self.inclusive: self_size = self.length
            else:              self_size = 0

            block                = self.request.closed_blocks[self.block_name]
            self.bit_field.value = self.math(len(block.rendered) + self_size)
            self.rendered        = self.bit_field.render()

        # otherwise, add this sizer block to the requests callback list.
        else:
            if not self.request.callbacks.has_key(self.block_name):
                self.request.callbacks[self.block_name] = []

            self.request.callbacks[self.block_name].append(self)


    def reset (self):
        '''
        Wrap the reset routine of the internal bit_field primitive.
        '''

        self.bit_field.reset()

########NEW FILE########
__FILENAME__ = instrumentation
class external:
    '''
    External instrumentation class
    Monitor a target which doesn't support a debugger, allowing external
    commands to be called
    '''

    def __init__(self, pre=None, post=None, start=None, stop=None):
        '''
        @type  pre:   Function
        @param pre:   Callback called before each test case
        @type  post:  Function
        @param post:  Callback called after each test case for instrumentation. Must return True if the target is still active, False otherwise.
        @type  start: Function
        @param start: Callback called to start the target
        @type  stop:  Function
        @param stop:  Callback called to stop the target
        '''

        self.pre        = pre
        self.post       = post
        self.start      = start
        self.stop       = stop
        self.__dbg_flag = False


    def alive(self):
        '''
        Check if this script is alive. Always True.
        '''

        return True


    def debug(self, msg):
        '''
        Print a debug mesage.
        '''

        if self.__dbg_flag:
            print "EXT-INSTR> %s" % msg


    def pre_send(self, test_number):
        '''
        This routine is called before the fuzzer transmits a test case and ensure the target is alive.

        @type  test_number: Integer
        @param test_number: Test number.
        '''

        if self.pre:
            self.pre()


    def post_send(self):
        '''
        This routine is called after the fuzzer transmits a test case and returns the status of the target.

        @rtype:  Boolean
        @return: Return True if the target is still active, False otherwise.
        '''

        if self.post:
            return self.post()
        else:
            return True


    def start_target(self):
        '''
        Start up the target. Called when post_send failed.
        Returns success of failure of the action
        If no method defined, false is returned
        '''

        if self.start:
            return self.start()
        else:
            return False


    def stop_target(self):
        '''
        Stop the target.
        '''

        if self.stop:
            self.stop()


    def get_crash_synopsis(self):
        '''
        Return the last recorded crash synopsis.

        @rtype:  String
        @return: Synopsis of last recorded crash.
        '''

        return 'External instrumentation detects a crash...\n'

########NEW FILE########
__FILENAME__ = ber
########################################################################################################################
### ASN.1 / BER TYPES (http://luca.ntop.org/Teaching/Appunti/asn1.html)
########################################################################################################################

import struct
from sulley import blocks, primitives, sex


########################################################################################################################
class string (blocks.block):
    '''
    [0x04][0x84][dword length][string]

    Where:

        0x04 = string
        0x84 = length is 4 bytes
    '''

    def __init__ (self, name, request, value, options={}):
        blocks.block.__init__(self, name, request, None, None, None, None)

        self.value   = value
        self.options = options
        self.prefix  = options.get("prefix", "\x04")

        if not self.value:
            raise sex.error("MISSING LEGO.ber_string DEFAULT VALUE")

        str_block = blocks.block(name + "_STR", request)
        str_block.push(primitives.string(self.value))

        self.push(blocks.size(name + "_STR", request, endian=">", fuzzable=True))
        self.push(str_block)


    def render (self):
        # let the parent do the initial render.
        blocks.block.render(self)

        self.rendered = self.prefix + "\x84" + self.rendered

        return self.rendered


########################################################################################################################
class integer (blocks.block):
    '''
    [0x02][0x04][dword]

    Where:

        0x02 = integer
        0x04 = integer length is 4 bytes
    '''

    def __init__ (self, name, request, value, options={}):
        blocks.block.__init__(self, name, request, None, None, None, None)

        self.value   = value
        self.options = options

        if not self.value:
            raise sex.error("MISSING LEGO.ber_integer DEFAULT VALUE")

        self.push(primitives.dword(self.value, endian=">"))


    def render (self):
        # let the parent do the initial render.
        blocks.block.render(self)

        self.rendered = "\x02\x04" + self.rendered
        return self.rendered
########NEW FILE########
__FILENAME__ = dcerpc
########################################################################################################################
### MSRPC NDR TYPES
########################################################################################################################

import struct
from sulley import blocks, primitives, sex


########################################################################################################################
def ndr_pad (string):
    return "\x00" * ((4 - (len(string) & 3)) & 3)


########################################################################################################################
class ndr_conformant_array (blocks.block):
    '''
    Note: this is not for fuzzing the RPC protocol but rather just representing an NDR string for fuzzing the actual
    client.
    '''

    def __init__ (self, name, request, value, options={}):
        blocks.block.__init__(self, name, request, None, None, None, None)

        self.value   = value
        self.options = options

        if not self.value:
            raise sex.error("MISSING LEGO.ndr_conformant_array DEFAULT VALUE")

        self.push(primitives.string(self.value))


    def render (self):
        '''
        We overload and extend the render routine in order to properly pad and prefix the string.

        [dword length][array][pad]
        '''

        # let the parent do the initial render.
        blocks.block.render(self)

        # encode the empty string correctly:
        if self.rendered == "":
            self.rendered = "\x00\x00\x00\x00"
        else:
            self.rendered = struct.pack("<L", len(self.rendered)) + self.rendered + ndr_pad(self.rendered)

        return self.rendered


########################################################################################################################
class ndr_string (blocks.block):
    '''
    Note: this is not for fuzzing the RPC protocol but rather just representing an NDR string for fuzzing the actual
    client.
    '''

    def __init__ (self, name, request, value, options={}):
        blocks.block.__init__(self, name, request, None, None, None, None)

        self.value   = value
        self.options = options

        if not self.value:
            raise sex.error("MISSING LEGO.tag DEFAULT VALUE")

        self.push(primitives.string(self.value))


    def render (self):
        '''
        We overload and extend the render routine in order to properly pad and prefix the string.

        [dword length][dword offset][dword passed size][string][pad]
        '''

        # let the parent do the initial render.
        blocks.block.render(self)

        # encode the empty string correctly:
        if self.rendered == "":
            self.rendered = "\x00\x00\x00\x00"
        else:
            # ensure null termination.
            self.rendered += "\x00"

            # format accordingly.
            length        = len(self.rendered)
            self.rendered = struct.pack("<L", length) \
                          + struct.pack("<L", 0)      \
                          + struct.pack("<L", length) \
                          + self.rendered             \
                          + ndr_pad(self.rendered)

        return self.rendered


########################################################################################################################
class ndr_wstring (blocks.block):
    '''
    Note: this is not for fuzzing the RPC protocol but rather just representing an NDR string for fuzzing the actual
    client.
    '''

    def __init__ (self, name, request, value, options={}):
        blocks.block.__init__(self, name, request, None, None, None, None)

        self.value   = value
        self.options = options

        if not self.value:
            raise sex.error("MISSING LEGO.tag DEFAULT VALUE")

        self.push(primitives.string(self.value))


    def render (self):
        '''
        We overload and extend the render routine in order to properly pad and prefix the string.

        [dword length][dword offset][dword passed size][string][pad]
        '''

        # let the parent do the initial render.
        blocks.block.render(self)

        # encode the empty string correctly:
        if self.rendered == "":
            self.rendered = "\x00\x00\x00\x00"
        else:
            # unicode encode and null terminate.
            self.rendered = self.rendered.encode("utf-16le") + "\x00"

            # format accordingly.
            length        = len(self.rendered)
            self.rendered = struct.pack("<L", length) \
                          + struct.pack("<L", 0)      \
                          + struct.pack("<L", length) \
                          + self.rendered             \
                          + ndr_pad(self.rendered)

        return self.rendered
########NEW FILE########
__FILENAME__ = misc
import struct
from sulley import blocks, primitives, sex


########################################################################################################################
class dns_hostname (blocks.block):
    def __init__ (self, name, request, value, options={}):
        blocks.block.__init__(self, name, request, None, None, None, None)

        self.value   = value
        self.options = options

        if not self.value:
            raise sex.error("MISSING LEGO.tag DEFAULT VALUE")

        self.push(primitives.string(self.value))


    def render (self):
        '''
        We overload and extend the render routine in order to properly insert substring lengths.
        '''

        # let the parent do the initial render.
        blocks.block.render(self)

        new_str = ""

        # replace dots (.) with the substring length.
        for part in self.rendered.split("."):
            new_str += str(len(part)) + part

        # be sure to null terminate too.
        self.rendered = new_str + "\x00"

        return self.rendered


########################################################################################################################
class tag (blocks.block):
    def __init__ (self, name, request, value, options={}):
        blocks.block.__init__(self, name, request, None, None, None, None)

        self.value   = value
        self.options = options

        if not self.value:
            raise sex.error("MISSING LEGO.tag DEFAULT VALUE")

        # <example>
        # [delim][string][delim]

        self.push(primitives.delim("<"))
        self.push(primitives.string(self.value))
        self.push(primitives.delim(">"))
########NEW FILE########
__FILENAME__ = xdr
########################################################################################################################
### XDR TYPES (http://www.freesoft.org/CIE/RFC/1832/index.htm)
########################################################################################################################

import struct
from sulley import blocks, primitives, sex


########################################################################################################################
def xdr_pad (string):
    return "\x00" * ((4 - (len(string) & 3)) & 3)


########################################################################################################################
class string (blocks.block):
    '''
    Note: this is not for fuzzing the XDR protocol but rather just representing an XDR string for fuzzing the actual
    client.
    '''

    def __init__ (self, name, request, value, options={}):
        blocks.block.__init__(self, name, request, None, None, None, None)

        self.value   = value
        self.options = options

        if not self.value:
            raise sex.error("MISSING LEGO.xdr_string DEFAULT VALUE")

        self.push(primitives.string(self.value))


    def render (self):
        '''
        We overload and extend the render routine in order to properly pad and prefix the string.

        [dword length][array][pad]
        '''

        # let the parent do the initial render.
        blocks.block.render(self)

        # encode the empty string correctly:
        if self.rendered == "":
            self.rendered = "\x00\x00\x00\x00"
        else:
            self.rendered = struct.pack(">L", len(self.rendered)) + self.rendered + xdr_pad(self.rendered)

        return self.rendered

########NEW FILE########
__FILENAME__ = pedrpc
import sys
import struct
import time
import socket
import cPickle

########################################################################################################################
class client:
    def __init__ (self, host, port):
        self.__host           = host
        self.__port           = port
        self.__dbg_flag       = False
        self.__server_sock    = None
        self.__retry          = 0
        self.NOLINGER         = struct.pack('ii', 1, 0)


    ####################################################################################################################
    def __getattr__ (self, method_name):
        '''
        This routine is called by default when a requested attribute (or method) is accessed that has no definition.
        Unfortunately __getattr__ only passes the requested method name and not the arguments. So we extend the
        functionality with a little lambda magic to the routine method_missing(). Which is actually how Ruby handles
        missing methods by default ... with arguments. Now we are just as cool as Ruby.

        @type  method_name: String
        @param method_name: The name of the requested and undefined attribute (or method in our case).

        @rtype:  Lambda
        @return: Lambda magic passing control (and in turn the arguments we want) to self.method_missing().
        '''

        return lambda *args, **kwargs: self.__method_missing(method_name, *args, **kwargs)


    ####################################################################################################################
    def __connect (self):
        '''
        Connect to the PED-RPC server.
        '''

        # if we have a pre-existing server socket, ensure it's closed.
        self.__disconnect()

        # connect to the server, timeout on failure.
        try:
            self.__server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__server_sock.settimeout(3.0)
            self.__server_sock.connect((self.__host, self.__port))
        except:
            if self.__retry != 5:
                self.__retry += 1
                time.sleep(5)
                self.__connect()
            else:
                sys.stderr.write("PED-RPC> unable to connect to server %s:%d\n" % (self.__host, self.__port))
                raise Exception            
        # disable timeouts and lingering.
        self.__server_sock.settimeout(None)
        self.__server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, self.NOLINGER)


    ####################################################################################################################
    def __disconnect (self):
        '''
        Ensure the socket is torn down.
        '''

        if self.__server_sock != None:
            self.__debug("closing server socket")
            self.__server_sock.close()
            self.__server_sock = None


    ####################################################################################################################
    def __debug (self, msg):
        if self.__dbg_flag:
            print "PED-RPC> %s" % msg


    ####################################################################################################################
    def __method_missing (self, method_name, *args, **kwargs):
        '''
        See the notes for __getattr__ for related notes. This method is called, in the Ruby fashion, with the method
        name and arguments for any requested but undefined class method.

        @type  method_name: String
        @param method_name: The name of the requested and undefined attribute (or method in our case).
        @type  *args:       Tuple
        @param *args:       Tuple of arguments.
        @type  **kwargs     Dictionary
        @param **kwargs:    Dictioanry of arguments.

        @rtype:  Mixed
        @return: Return value of the mirrored method.
        '''

        # return a value so lines of code like the following work:
        #     x = pedrpc.client(host, port)
        #     if x:
        #         x.do_something()
        if method_name == "__nonzero__":
            return 1

        # ignore all other attempts to access a private member.
        if method_name.startswith("__"):
            return

        # connect to the PED-RPC server.
        self.__connect()

        # transmit the method name and arguments.
        while 1:
            try:
                self.__pickle_send((method_name, (args, kwargs)))
                break
            except:
                # re-connect to the PED-RPC server if the sock died.
                self.__connect()

        # snag the return value.
        ret = self.__pickle_recv()

        # close the sock and return.
        self.__disconnect()
        return ret


    ####################################################################################################################
    def __pickle_recv (self):
        '''
        This routine is used for marshaling arbitrary data from the PyDbg server. We can send pretty much anything here.
        For example a tuple containing integers, strings, arbitrary objects and structures. Our "protocol" is a simple
        length-value protocol where each datagram is prefixed by a 4-byte length of the data to be received.

        @raise pdx: An exception is raised if the connection was severed.
        @rtype:     Mixed
        @return:    Whatever is received over the socket.
        '''

        try:
            # XXX - this should NEVER fail, but alas, it does and for the time being i can't figure out why.
            #       it gets worse. you would think that simply returning here would break things, but it doesn't.
            #       gotta track this down at some point.
            length = struct.unpack("<L", self.__server_sock.recv(4))[0]
        except:
            return

        try:
            received = ""

            while length:
                chunk     = self.__server_sock.recv(length)
                received += chunk
                length   -= len(chunk)
        except:
            sys.stderr.write("PED-RPC> connection to server severed during recv()\n")
            raise Exception

        return cPickle.loads(received)


    ####################################################################################################################
    def __pickle_send (self, data):
        '''
        This routine is used for marshaling arbitrary data to the PyDbg server. We can send pretty much anything here.
        For example a tuple containing integers, strings, arbitrary objects and structures. Our "protocol" is a simple
        length-value protocol where each datagram is prefixed by a 4-byte length of the data to be received.

        @type  data: Mixed
        @param data: Data to marshal and transmit. Data can *pretty much* contain anything you throw at it.

        @raise pdx: An exception is raised if the connection was severed.
        '''

        data = cPickle.dumps(data, protocol=2)
        self.__debug("sending %d bytes" % len(data))

        try:
            self.__server_sock.send(struct.pack("<L", len(data)))
            self.__server_sock.send(data)
        except:
            sys.stderr.write("PED-RPC> connection to server severed during send()\n")
            raise Exception


########################################################################################################################
class server:
    def __init__ (self, host, port):
        self.__host           = host
        self.__port           = port
        self.__dbg_flag       = False
        self.__client_sock    = None
        self.__client_address = None

        try:
            # create a socket and bind to the specified port.
            self.__server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__server.settimeout(None)
            self.__server.bind((host, port))
            self.__server.listen(1)
        except:
            sys.stderr.write("unable to bind to %s:%d\n" % (host, port))
            sys.exit(1)


    ####################################################################################################################
    def __disconnect (self):
        '''
        Ensure the socket is torn down.
        '''

        if self.__client_sock != None:
            self.__debug("closing client socket")
            self.__client_sock.close()
            self.__client_sock = None


    ####################################################################################################################
    def __debug (self, msg):
        if self.__dbg_flag:
            print "PED-RPC> %s" % msg


    ####################################################################################################################
    def __pickle_recv (self):
        '''
        This routine is used for marshaling arbitrary data from the PyDbg server. We can send pretty much anything here.
        For example a tuple containing integers, strings, arbitrary objects and structures. Our "protocol" is a simple
        length-value protocol where each datagram is prefixed by a 4-byte length of the data to be received.

        @raise pdx: An exception is raised if the connection was severed.
        @rtype:     Mixed
        @return:    Whatever is received over the socket.
        '''

        try:
            length   = struct.unpack("<L", self.__client_sock.recv(4))[0]
            received = ""

            while length:
                chunk     = self.__client_sock.recv(length)
                received += chunk
                length   -= len(chunk)
        except:
            sys.stderr.write("PED-RPC> connection client severed during recv()\n")
            raise Exception

        return cPickle.loads(received)


    ####################################################################################################################
    def __pickle_send (self, data):
        '''
        This routine is used for marshaling arbitrary data to the PyDbg server. We can send pretty much anything here.
        For example a tuple containing integers, strings, arbitrary objects and structures. Our "protocol" is a simple
        length-value protocol where each datagram is prefixed by a 4-byte length of the data to be received.

        @type  data: Mixed
        @param data: Data to marshal and transmit. Data can *pretty much* contain anything you throw at it.

        @raise pdx: An exception is raised if the connection was severed.
        '''

        data = cPickle.dumps(data, protocol=2)
        self.__debug("sending %d bytes" % len(data))

        try:
            self.__client_sock.send(struct.pack("<L", len(data)))
            self.__client_sock.send(data)
        except:
            sys.stderr.write("PED-RPC> connection to client severed during send()\n")
            raise Exception


    ####################################################################################################################
    def serve_forever (self):
        self.__debug("serving up a storm")

        while 1:
            # close any pre-existing socket.
            self.__disconnect()

            # accept a client connection.
            (self.__client_sock, self.__client_address) = self.__server.accept()

            self.__debug("accepted connection from %s:%d" % (self.__client_address[0], self.__client_address[1]))

            # recieve the method name and arguments, continue on socket disconnect.
            try:
                (method_name, (args, kwargs)) = self.__pickle_recv()
                self.__debug("%s(args=%s, kwargs=%s)" % (method_name, args, kwargs))
            except:
                continue

            try:
                # resolve a pointer to the requested method and call it.
                exec("method_pointer = self.%s" % method_name)
                ret = method_pointer(*args, **kwargs)
            except AttributeError:
                # if the method can't be found notify the user and raise an error
                sys.stderr.write("PED-RPC> remote method %s cannot be found\n" % method_name)
                continue

            # transmit the return value to the client, continue on socket disconnect.
            try:
                self.__pickle_send(ret)
            except:
                continue

########NEW FILE########
__FILENAME__ = cluster
#
# pGRAPH
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import node

class cluster (object):
    '''
    '''

    id    = None
    nodes = []

    ####################################################################################################################
    def __init__ (self, id=None):
        '''
        Class constructor.
        '''

        self.id    = id
        self.nodes = []


   ####################################################################################################################
    def add_node (self, node):
        '''
        Add a node to the cluster.

        @type  node: pGRAPH Node
        @param node: Node to add to cluster
        '''

        self.nodes.append(node)

        return self


    ####################################################################################################################
    def del_node (self, node_id):
        '''
        Remove a node from the cluster.

        @type  node: pGRAPH Node
        @param node: Node to remove from cluster
        '''

        for node in self.nodes:
            if node.id == node_id:
                self.nodes.remove(node)
                break

        return self


    ####################################################################################################################
    def find_node (self, attribute, value):
        '''
        Find and return the node with the specified attribute / value pair.

        @type  attribute: String
        @param attribute: Attribute name we are looking for
        @type  value:     Mixed
        @param value:     Value of attribute we are looking for

        @rtype:  Mixed
        @return: Node, if attribute / value pair is matched. None otherwise.
        '''

        for node in self.nodes:
            if hasattr(node, attribute):
                if getattr(node, attribute) == value:
                    return node

        return None


    ####################################################################################################################
    def render (self):
        pass
########NEW FILE########
__FILENAME__ = edge
#
# pGRAPH
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

class edge (object):
    '''
    '''

    id    = None
    src   = None
    dst   = None

    # general graph attributes.
    color = 0x000000
    label = ""

    # gml relevant attributes.
    gml_arrow       = "none"
    gml_stipple     = 1
    gml_line_width  = 1.0

    ####################################################################################################################
    def __init__ (self, src, dst):
        '''
        Class constructor.

        @type  src: Mixed
        @param src: Edge source
        @type  dst: Mixed
        @param dst: Edge destination
        '''

        # the unique id for any edge (provided that duplicates are not allowed) is the combination of the source and
        # the destination stored as a long long.
        self.id  = (src << 32) + dst
        self.src = src
        self.dst = dst

        # general graph attributes.
        self.color = 0x000000
        self.label = ""

        # gml relevant attributes.
        self.gml_arrow       = "none"
        self.gml_stipple     = 1
        self.gml_line_width  = 1.0


    ####################################################################################################################
    def render_edge_gml (self, graph):
        '''
        Render an edge description suitable for use in a GML file using the set internal attributes.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current edge

        @rtype:  String
        @return: GML edge description
        '''

        src = graph.find_node("id", self.src)
        dst = graph.find_node("id", self.dst)

        # ensure nodes exist at the source and destination of this edge.
        if not src or not dst:
            return ""

        edge  = '  edge [\n'
        edge += '    source %d\n'          % src.number
        edge += '    target %d\n'          % dst.number
        edge += '    generalization 0\n'
        edge += '    graphics [\n'
        edge += '      type "line"\n'
        edge += '      arrow "%s"\n'       % self.gml_arrow
        edge += '      stipple %d\n'       % self.gml_stipple
        edge += '      lineWidth %f\n'     % self.gml_line_width
        edge += '      fill "#%06x"\n'     % self.color
        edge += '    ]\n'
        edge += '  ]\n'

        return edge


    ####################################################################################################################
    def render_edge_graphviz (self, graph):
        '''
        Render an edge suitable for use in a Pydot graph using the set internal attributes.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current edge

        @rtype:  pydot.Edge()
        @return: Pydot object representing edge
        '''

        import pydot

        # no need to validate if nodes exist for src/dst. graphviz takes care of that for us transparently.

        dot_edge = pydot.Edge(self.src, self.dst)

        if self.label:
            dot_edge.label = self.label

        dot_edge.color = "#%06x" % self.color

        return dot_edge


    ####################################################################################################################
    def render_edge_udraw (self, graph):
        '''
        Render an edge description suitable for use in a GML file using the set internal attributes.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current edge

        @rtype:  String
        @return: GML edge description
        '''

        src = graph.find_node("id", self.src)
        dst = graph.find_node("id", self.dst)

        # ensure nodes exist at the source and destination of this edge.
        if not src or not dst:
            return ""

        # translate newlines for uDraw.
        self.label = self.label.replace("\n", "\\n")

        udraw  = 'l("%08x->%08x",'                  % (self.src, self.dst)
        udraw +=   'e("",'                          # open edge
        udraw +=     '['                            # open attributes
        udraw +=       'a("EDGECOLOR","#%06x"),'    % self.color
        udraw +=       'a("OBJECT","%s")'           % self.label
        udraw +=     '],'                           # close attributes
        udraw +=     'r("%08x")'                    % self.dst
        udraw +=   ')'                              # close edge
        udraw += ')'                                # close element

        return udraw


    ####################################################################################################################
    def render_edge_udraw_update (self):
        '''
        Render an edge update description suitable for use in a GML file using the set internal attributes.

        @rtype:  String
        @return: GML edge update description
        '''

        # translate newlines for uDraw.
        self.label = self.label.replace("\n", "\\n")

        udraw  = 'new_edge("%08x->%08x","",'      % (self.src, self.dst)
        udraw +=   '['
        udraw +=     'a("EDGECOLOR","#%06x"),'    % self.color
        udraw +=       'a("OBJECT","%s")'         % self.label
        udraw +=   '],'
        udraw +=   '"%08x","%08x"'                % (self.src, self.dst)
        udraw += ')'

        return udraw
########NEW FILE########
__FILENAME__ = graph
#
# pGRAPH
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import node
import edge
import cluster

import copy

class graph (object):
    '''
    @todo: Add support for clusters
    @todo: Potentially swap node list with a node dictionary for increased performance
    '''

    id       = None
    clusters = []
    edges    = {}
    nodes    = {}

    ####################################################################################################################
    def __init__ (self, id=None):
        '''
        '''

        self.id       = id
        self.clusters = []
        self.edges    = {}
        self.nodes    = {}


    ####################################################################################################################
    def add_cluster (self, cluster):
        '''
        Add a pgraph cluster to the graph.

        @type  cluster: pGRAPH Cluster
        @param cluster: Cluster to add to graph
        '''

        self.clusters.append(cluster)

        return self


    ####################################################################################################################
    def add_edge (self, edge, prevent_dups=True):
        '''
        Add a pgraph edge to the graph. Ensures a node exists for both the source and destination of the edge.

        @type  edge:         pGRAPH Edge
        @param edge:         Edge to add to graph
        @type  prevent_dups: Boolean
        @param prevent_dups: (Optional, Def=True) Flag controlling whether or not the addition of duplicate edges is ok
        '''

        if prevent_dups:
            if self.edges.has_key(edge.id):
                return self

        # ensure the source and destination nodes exist.
        if self.find_node("id", edge.src) and self.find_node("id", edge.dst):
            self.edges[edge.id] = edge

        return self


    ####################################################################################################################
    def add_graph (self, other_graph):
        '''
        Alias of graph_cat(). Concatenate the other graph into the current one.

        @todo: Add support for clusters
        @see:  graph_cat()

        @type  other_graph: pgraph.graph
        @param other_graph: Graph to concatenate into this one.
        '''

        return self.graph_cat(other_graph)


    ####################################################################################################################
    def add_node (self, node):
        '''
        Add a pgraph node to the graph. Ensures a node with the same id does not already exist in the graph.

        @type  node: pGRAPH Node
        @param node: Node to add to graph
        '''

        node.number = len(self.nodes)

        if not self.nodes.has_key(node.id):
            self.nodes[node.id] = node

        return self


    ####################################################################################################################
    def del_cluster (self, id):
        '''
        Remove a cluster from the graph.

        @type  id: Mixed
        @param id: Identifier of cluster to remove from graph
        '''

        for cluster in self.clusters:
            if cluster.id == id:
                self.clusters.remove(cluster)
                break

        return self


    ####################################################################################################################
    def del_edge (self, id=None, src=None, dst=None):
        '''
        Remove an edge from the graph. There are two ways to call this routine, with an edge id::

            graph.del_edge(id)

        or by specifying the edge source and destination::

            graph.del_edge(src=source, dst=destination)

        @type  id:  Mixed
        @param id:  (Optional) Identifier of edge to remove from graph
        @type  src: Mixed
        @param src: (Optional) Source of edge to remove from graph
        @type  dst: Mixed
        @param dst: (Optional) Destination of edge to remove from graph
        '''

        if not id:
            id = (src << 32) + dst

        if self.edges.has_key(id):
            del self.edges[id]

        return self


    ####################################################################################################################
    def del_graph (self, other_graph):
        '''
        Alias of graph_sub(). Remove the elements shared between the current graph and other graph from the current
        graph.

        @todo: Add support for clusters
        @see:  graph_sub()

        @type  other_graph: pgraph.graph
        @param other_graph: Graph to diff/remove against
        '''

        return self.graph_sub(other_graph)


    ####################################################################################################################
    def del_node (self, id):
        '''
        Remove a node from the graph.

        @type  node_id: Mixed
        @param node_id: Identifier of node to remove from graph
        '''

        if self.nodes.has_key(id):
            del self.nodes[id]

        return self


    ####################################################################################################################
    def edges_from (self, id):
        '''
        Enumerate the edges from the specified node.

        @type  id: Mixed
        @param id: Identifier of node to enumerate edges from

        @rtype:  List
        @return: List of edges from the specified node
        '''

        return [edge for edge in self.edges.values() if edge.src == id]


    ####################################################################################################################
    def edges_to (self, id):
        '''
        Enumerate the edges to the specified node.

        @type  id: Mixed
        @param id: Identifier of node to enumerate edges to

        @rtype:  List
        @return: List of edges to the specified node
        '''

        return [edge for edge in self.edges.values() if edge.dst == id]


    ####################################################################################################################
    def find_cluster (self, attribute, value):
        '''
        Find and return the cluster with the specified attribute / value pair.

        @type  attribute: String
        @param attribute: Attribute name we are looking for
        @type  value:     Mixed
        @param value:     Value of attribute we are looking for

        @rtype:  Mixed
        @return: Cluster, if attribute / value pair is matched. None otherwise.
        '''

        for cluster in self.clusters:
            if hasattr(cluster, attribute):
                if getattr(cluster, attribute) == value:
                    return cluster

        return None


    ####################################################################################################################
    def find_cluster_by_node (self, attribute, value):
        '''
        Find and return the cluster that contains the node with the specified attribute / value pair.

        @type  attribute: String
        @param attribute: Attribute name we are looking for
        @type  value:     Mixed
        @param value:     Value of attribute we are looking for

        @rtype:  Mixed
        @return: Cluster, if node with attribute / value pair is matched. None otherwise.
        '''

        for cluster in self.clusters:
            for node in cluster:
                if hasattr(node, attribute):
                    if getattr(node, attribute) == value:
                        return cluster

        return None


    ####################################################################################################################
    def find_edge (self, attribute, value):
        '''
        Find and return the edge with the specified attribute / value pair.

        @type  attribute: String
        @param attribute: Attribute name we are looking for
        @type  value:     Mixed
        @param value:     Value of attribute we are looking for

        @rtype:  Mixed
        @return: Edge, if attribute / value pair is matched. None otherwise.
        '''

        # if the attribute to search for is the id, simply return the edge from the internal hash.
        if attribute == "id" and self.edges.has_key(value):
            return self.edges[value]

        # step through all the edges looking for the given attribute/value pair.
        else:
            for edges in self.edges.values():
                if hasattr(edge, attribute):
                    if getattr(edge, attribute) == value:
                        return edge

        return None


    ####################################################################################################################
    def find_node (self, attribute, value):
        '''
        Find and return the node with the specified attribute / value pair.

        @type  attribute: String
        @param attribute: Attribute name we are looking for
        @type  value:     Mixed
        @param value:     Value of attribute we are looking for

        @rtype:  Mixed
        @return: Node, if attribute / value pair is matched. None otherwise.
        '''

        # if the attribute to search for is the id, simply return the node from the internal hash.
        if attribute == "id" and self.nodes.has_key(value):
            return self.nodes[value]

        # step through all the nodes looking for the given attribute/value pair.
        else:
            for node in self.nodes.values():
                if hasattr(node, attribute):
                    if getattr(node, attribute) == value:
                        return node

        return None


    ####################################################################################################################
    def graph_cat (self, other_graph):
        '''
        Concatenate the other graph into the current one.

        @todo: Add support for clusters

        @type  other_graph: pgraph.graph
        @param other_graph: Graph to concatenate into this one.
        '''

        for other_node in other_graph.nodes.values():
            self.add_node(other_node)

        for other_edge in other_graph.edges.values():
            self.add_edge(other_edge)

        return self


    ####################################################################################################################
    def graph_down (self, from_node_id, max_depth=-1):
        '''
        Create a new graph, looking down, from the specified node id to the specified depth.

        @type  from_node_id: pgraph.node
        @param from_node_id: Node to use as start of down graph
        @type  max_depth:    Integer
        @param max_depth:    (Optional, Def=-1) Number of levels to include in down graph (-1 for infinite)

        @rtype:  pgraph.graph
        @return: Down graph around specified node.
        '''

        down_graph = graph()
        from_node  = self.find_node("id", from_node_id)

        if not from_node:
            print "unable to resolve node %08x" % from_node_id
            raise Exception

        levels_to_process = []
        current_depth     = 1

        levels_to_process.append([from_node])

        for level in levels_to_process:
            next_level = []

            if current_depth > max_depth and max_depth != -1:
                break

            for node in level:
                down_graph.add_node(copy.copy(node))

                for edge in self.edges_from(node.id):
                    to_add = self.find_node("id", edge.dst)

                    if not down_graph.find_node("id", edge.dst):
                        next_level.append(to_add)

                    down_graph.add_node(copy.copy(to_add))
                    down_graph.add_edge(copy.copy(edge))

            if next_level:
                levels_to_process.append(next_level)

            current_depth += 1

        return down_graph


    ####################################################################################################################
    def graph_intersect (self, other_graph):
        '''
        Remove all elements from the current graph that do not exist in the other graph.

        @todo: Add support for clusters

        @type  other_graph: pgraph.graph
        @param other_graph: Graph to intersect with
        '''

        for node in self.nodes.values():
            if not other_graph.find_node("id", node.id):
                self.del_node(node.id)

        for edge in self.edges.values():
            if not other_graph.find_edge("id", edge.id):
                self.del_edge(edge.id)

        return self


    ####################################################################################################################
    def graph_proximity (self, center_node_id, max_depth_up=2, max_depth_down=2):
        '''
        Create a proximity graph centered around the specified node.

        @type  center_node_id: pgraph.node
        @param center_node_id: Node to use as center of proximity graph
        @type  max_depth_up:   Integer
        @param max_depth_up:   (Optional, Def=2) Number of upward levels to include in proximity graph
        @type  max_depth_down: Integer
        @param max_depth_down: (Optional, Def=2) Number of downward levels to include in proximity graph

        @rtype:  pgraph.graph
        @return: Proximity graph around specified node.
        '''

        prox_graph = self.graph_down(center_node_id, max_depth_down)
        prox_graph.add_graph(self.graph_up(center_node_id, max_depth_up))

        return prox_graph


    ####################################################################################################################
    def graph_sub (self, other_graph):
        '''
        Remove the elements shared between the current graph and other graph from the current
        graph.

        @todo: Add support for clusters

        @type  other_graph: pgraph.graph
        @param other_graph: Graph to diff/remove against
        '''

        for other_node in other_graph.nodes.values():
            self.del_node(other_node.id)

        for other_edge in other_graph.edges.values():
            self.del_edge(None, other_edge.src, other_edge.dst)

        return self


    ####################################################################################################################
    def graph_up (self, from_node_id, max_depth=-1):
        '''
        Create a new graph, looking up, from the specified node id to the specified depth.

        @type  from_node_id: pgraph.node
        @param from_node_id: Node to use as start of up graph
        @type  max_depth:    Integer
        @param max_depth:    (Optional, Def=-1) Number of levels to include in up graph (-1 for infinite)

        @rtype:  pgraph.graph
        @return: Up graph to the specified node.
        '''

        up_graph  = graph()
        from_node = self.find_node("id", from_node_id)

        levels_to_process = []
        current_depth     = 1

        levels_to_process.append([from_node])

        for level in levels_to_process:
            next_level = []

            if current_depth > max_depth and max_depth != -1:
                break

            for node in level:
                up_graph.add_node(copy.copy(node))

                for edge in self.edges_to(node.id):
                    to_add = self.find_node("id", edge.src)

                    if not up_graph.find_node("id", edge.src):
                        next_level.append(to_add)

                    up_graph.add_node(copy.copy(to_add))
                    up_graph.add_edge(copy.copy(edge))

            if next_level:
                levels_to_process.append(next_level)

            current_depth += 1

        return up_graph


    ####################################################################################################################
    def render_graph_gml (self):
        '''
        Render the GML graph description.

        @rtype:  String
        @return: GML graph description.
        '''

        gml  = 'Creator "pGRAPH - Pedram Amini <pedram.amini@gmail.com>"\n'
        gml += 'directed 1\n'

        # open the graph tag.
        gml += 'graph [\n'

        # add the nodes to the GML definition.
        for node in self.nodes.values():
            gml += node.render_node_gml(self)

        # add the edges to the GML definition.
        for edge in self.edges.values():
            gml += edge.render_edge_gml(self)

        # close the graph tag.
        gml += ']\n'

        """
        XXX - TODO: Complete cluster rendering
        # if clusters exist.
        if len(self.clusters):
            # open the rootcluster tag.
            gml += 'rootcluster [\n'

            # add the clusters to the GML definition.
            for cluster in self.clusters:
                gml += cluster.render()

            # add the clusterless nodes to the GML definition.
            for node in self.nodes:
                if not self.find_cluster_by_node("id", node.id):
                    gml += '    vertex "%d"\n' % node.id

            # close the rootcluster tag.
            gml += ']\n'
        """

        return gml


    ####################################################################################################################
    def render_graph_graphviz (self):
        '''
        Render the graphviz graph structure.

        @rtype:  pydot.Dot
        @return: Pydot object representing entire graph
        '''

        import pydot

        dot_graph = pydot.Dot()

        for node in self.nodes.values():
            dot_graph.add_node(node.render_node_graphviz(self))

        for edge in self.edges.values():
            dot_graph.add_edge(edge.render_edge_graphviz(self))

        return dot_graph


    ####################################################################################################################
    def render_graph_udraw (self):
        '''
        Render the uDraw graph description.

        @rtype:  String
        @return: uDraw graph description.
        '''

        udraw = '['

        # render each of the nodes in the graph.
        # the individual nodes will handle their own edge rendering.
        for node in self.nodes.values():
            udraw += node.render_node_udraw(self)
            udraw += ','

        # trim the extraneous comment and close the graph.
        udraw = udraw[0:-1] + ']'

        return udraw


    ####################################################################################################################
    def render_graph_udraw_update (self):
        '''
        Render the uDraw graph update description.

        @rtype:  String
        @return: uDraw graph description.
        '''

        udraw = '['

        for node in self.nodes.values():
            udraw += node.render_node_udraw_update()
            udraw += ','

        for edge in self.edges.values():
            udraw += edge.render_edge_udraw_update()
            udraw += ','

        # trim the extraneous comment and close the graph.
        udraw = udraw[0:-1] + ']'

        return udraw


    ####################################################################################################################
    def update_node_id (self, current_id, new_id):
        '''
        Simply updating the id attribute of a node will sever the edges to / from the given node. This routine will
        correctly update the edges as well.

        @type  current_id: Long
        @param current_id: Current ID of node whose ID we want to update
        @type  new_id:     Long
        @param new_id:     New ID to update to.
        '''

        if not self.nodes.has_key(current_id):
            return

        # update the node.
        node = self.nodes[current_id]
        del self.nodes[current_id]
        node.id = new_id
        self.nodes[node.id] = node

        # update the edges.
        for edge in [edge for edge in self.edges.values() if current_id in (edge.src, edge.dst)]:
            del self.edges[edge.id]

            if edge.src == current_id:
                edge.src = new_id
            if edge.dst == current_id:
                edge.dst = new_id

            edge.id = (edge.src << 32) + edge.dst

            self.edges[edge.id] = edge


    ####################################################################################################################
    def sorted_nodes (self):
        '''
        Return a list of the nodes within the graph, sorted by id.

        @rtype:  List
        @return: List of nodes, sorted by id.
        '''

        node_keys = self.nodes.keys()
        node_keys.sort()

        return [self.nodes[key] for key in node_keys]
########NEW FILE########
__FILENAME__ = node
#
# pGRAPH
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

class node (object):
    '''
    '''

    id     = 0
    number = 0

    # general graph attributes
    color        = 0xEEF7FF
    border_color = 0xEEEEEE
    label        = ""
    shape        = "box"

    # gml relevant attributes.
    gml_width       = 0.0
    gml_height      = 0.0
    gml_pattern     = "1"
    gml_stipple     = 1
    gml_line_width  = 1.0
    gml_type        = "rectangle"
    gml_width_shape = 1.0

    # udraw relevant attributes.
    udraw_image     = None
    udraw_info      = ""

    ####################################################################################################################
    def __init__ (self, id=None):
        '''
        '''

        self.id     = id
        self.number = 0

        # general graph attributes
        self.color        = 0xEEF7FF
        self.border_color = 0xEEEEEE
        self.label        = ""
        self.shape        = "box"

        # gml relevant attributes.
        self.gml_width       = 0.0
        self.gml_height      = 0.0
        self.gml_pattern     = "1"
        self.gml_stipple     = 1
        self.gml_line_width  = 1.0
        self.gml_type        = "rectangle"
        self.gml_width_shape = 1.0


    ####################################################################################################################
    def render_node_gml (self, graph):
        '''
        Render a node description suitable for use in a GML file using the set internal attributes.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current node

        @rtype:  String
        @return: GML node description.
        '''

        # GDE does not like lines longer then approx 250 bytes. within their their own GML files you won't find lines
        # longer then approx 210 bytes. wo we are forced to break long lines into chunks.
        chunked_label = ""
        cursor        = 0

        while cursor < len(self.label):
            amount = 200

            # if the end of the current chunk contains a backslash or double-quote, back off some.
            if cursor + amount < len(self.label):
                while self.label[cursor+amount] == '\\' or self.label[cursor+amount] == '"':
                    amount -= 1

            chunked_label += self.label[cursor:cursor+amount] + "\\\n"
            cursor        += amount

        # if node width and height were not explicitly specified, make a best effort guess to create something nice.
        if not self.gml_width:
            self.gml_width = len(self.label) * 10

        if not self.gml_height:
            self.gml_height = len(self.label.split()) * 20

        # construct the node definition.
        node  = '  node [\n'
        node += '    id %d\n'                       % self.number
        node += '    template "oreas:std:rect"\n'
        node += '    label "'
        node += '<!--%08x-->\\\n'                   % self.id
        node += chunked_label + '"\n'
        node += '    graphics [\n'
        node += '      w %f\n'                      % self.gml_width
        node += '      h %f\n'                      % self.gml_height
        node += '      fill "#%06x"\n'              % self.color
        node += '      line "#%06x"\n'              % self.border_color
        node += '      pattern "%s"\n'              % self.gml_pattern
        node += '      stipple %d\n'                % self.gml_stipple
        node += '      lineWidth %f\n'              % self.gml_line_width
        node += '      type "%s"\n'                 % self.gml_type
        node += '      width %f\n'                  % self.gml_width_shape
        node += '    ]\n'
        node += '  ]\n'

        return node


    ####################################################################################################################
    def render_node_graphviz (self, graph):
        '''
        Render a node suitable for use in a Pydot graph using the set internal attributes.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current node

        @rtype:  pydot.Node
        @return: Pydot object representing node
        '''

        import pydot

        dot_node = pydot.Node(self.id)

        dot_node.label     = '<<font face="lucida console">%s</font>>' % self.label.rstrip("\r\n")
        dot_node.label     = dot_node.label.replace("\\n", '<br/>')
        dot_node.shape     = self.shape
        dot_node.color     = "#%06x" % self.color
        dot_node.fillcolor = "#%06x" % self.color

        return dot_node


    ####################################################################################################################
    def render_node_udraw (self, graph):
        '''
        Render a node description suitable for use in a uDraw file using the set internal attributes.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current node

        @rtype:  String
        @return: uDraw node description.
        '''

        # translate newlines for uDraw.
        self.label = self.label.replace("\n", "\\n")

        # if an image was specified for this node, update the shape and include the image tag.
        if self.udraw_image:
            self.shape  = "image"
            udraw_image = 'a("IMAGE","%s"),' % self.udraw_image
        else:
            udraw_image = ""

        udraw  = 'l("%08x",'                            % self.id
        udraw +=   'n("",'                              # open node
        udraw +=     '['                                # open attributes
        udraw +=       udraw_image
        udraw +=       'a("_GO","%s"),'                 % self.shape
        udraw +=       'a("COLOR","#%06x"),'            % self.color
        udraw +=       'a("OBJECT","%s"),'              % self.label
        udraw +=       'a("FONTFAMILY","courier"),'
        udraw +=       'a("INFO","%s"),'                % self.udraw_info
        udraw +=       'a("BORDER","none")'
        udraw +=     '],'                               # close attributes
        udraw +=     '['                                # open edges

        edges = graph.edges_from(self.id)

        for edge in edges:
            udraw += edge.render_edge_udraw(graph)
            udraw += ','

        if edges:
            udraw = udraw[0:-1]

        udraw += ']))'

        return udraw


    ####################################################################################################################
    def render_node_udraw_update (self):
        '''
        Render a node update description suitable for use in a uDraw file using the set internal attributes.

        @rtype:  String
        @return: uDraw node update description.
        '''

        # translate newlines for uDraw.
        self.label = self.label.replace("\n", "\\n")

        # if an image was specified for this node, update the shape and include the image tag.
        if self.udraw_image:
            self.shape  = "image"
            udraw_image = 'a("IMAGE","%s"),' % self.udraw_image
        else:
            udraw_image = ""

        udraw  = 'new_node("%08x","",'                % self.id
        udraw +=   '['
        udraw +=     udraw_image
        udraw +=     'a("_GO","%s"),'                 % self.shape
        udraw +=     'a("COLOR","#%06x"),'            % self.color
        udraw +=     'a("OBJECT","%s"),'              % self.label
        udraw +=     'a("FONTFAMILY","courier"),'
        udraw +=     'a("INFO","%s"),'                % self.udraw_info
        udraw +=     'a("BORDER","none")'
        udraw +=   ']'
        udraw += ')'

        return udraw
########NEW FILE########
__FILENAME__ = primitives
import random
import struct

########################################################################################################################
class base_primitive (object):
    '''
    The primitive base class implements common functionality shared across most primitives.
    '''

    def __init__ (self):
        self.fuzz_complete  = False     # this flag is raised when the mutations are exhausted.
        self.fuzz_library   = []        # library of static fuzz heuristics to cycle through.
        self.fuzzable       = True      # flag controlling whether or not the given primitive is to be fuzzed.
        self.mutant_index   = 0         # current mutation index into the fuzz library.
        self.original_value = None      # original value of primitive.
        self.rendered       = ""        # rendered value of primitive.
        self.value          = None      # current value of primitive.


    def exhaust (self):
        '''
        Exhaust the possible mutations for this primitive.

        @rtype:  Integer
        @return: The number of mutations to reach exhaustion
        '''

        num = self.num_mutations() - self.mutant_index

        self.fuzz_complete  = True
        self.mutant_index   = self.num_mutations()
        self.value          = self.original_value

        return num


    def mutate (self):
        '''
        Mutate the primitive by stepping through the fuzz library, return False on completion.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        '''

        # if we've ran out of mutations, raise the completion flag.
        if self.mutant_index == self.num_mutations():
            self.fuzz_complete = True

        # if fuzzing was disabled or complete, and mutate() is called, ensure the original value is restored.
        if not self.fuzzable or self.fuzz_complete:
            self.value = self.original_value
            return False

        # update the current value from the fuzz library.
        self.value = self.fuzz_library[self.mutant_index]

        # increment the mutation count.
        self.mutant_index += 1

        return True


    def num_mutations (self):
        '''
        Calculate and return the total number of mutations for this individual primitive.

        @rtype:  Integer
        @return: Number of mutated forms this primitive can take
        '''

        return len(self.fuzz_library)


    def render (self):
        '''
        Nothing fancy on render, simply return the value.
        '''

        self.rendered = self.value
        return self.rendered


    def reset (self):
        '''
        Reset this primitive to the starting mutation state.
        '''

        self.fuzz_complete  = False
        self.mutant_index   = 0
        self.value          = self.original_value


########################################################################################################################
class delim (base_primitive):
    def __init__ (self, value, fuzzable=True, name=None):
        '''
        Represent a delimiter such as :,\r,\n, ,=,>,< etc... Mutations include repetition, substitution and exclusion.

        @type  value:    Character
        @param value:    Original value
        @type  fuzzable: Boolean
        @param fuzzable: (Optional, def=True) Enable/disable fuzzing of this primitive
        @type  name:     String
        @param name:     (Optional, def=None) Specifying a name gives you direct access to a primitive
        '''

        self.value         = self.original_value = value
        self.fuzzable      = fuzzable
        self.name          = name

        self.s_type        = "delim"   # for ease of object identification
        self.rendered      = ""        # rendered value
        self.fuzz_complete = False     # flag if this primitive has been completely fuzzed
        self.fuzz_library  = []        # library of fuzz heuristics
        self.mutant_index  = 0         # current mutation number

        #
        # build the library of fuzz heuristics.
        #

        # if the default delim is not blank, repeat it a bunch of times.
        if self.value:
            self.fuzz_library.append(self.value * 2)
            self.fuzz_library.append(self.value * 5)
            self.fuzz_library.append(self.value * 10)
            self.fuzz_library.append(self.value * 25)
            self.fuzz_library.append(self.value * 100)
            self.fuzz_library.append(self.value * 500)
            self.fuzz_library.append(self.value * 1000)

        # try ommitting the delimiter.
        self.fuzz_library.append("")

        # if the delimiter is a space, try throwing out some tabs.
        if self.value == " ":
            self.fuzz_library.append("\t")
            self.fuzz_library.append("\t" * 2)
            self.fuzz_library.append("\t" * 100)

        # toss in some other common delimiters:
        self.fuzz_library.append(" ")
        self.fuzz_library.append("\t")
        self.fuzz_library.append("\t " * 100)
        self.fuzz_library.append("\t\r\n" * 100)
        self.fuzz_library.append("!")
        self.fuzz_library.append("@")
        self.fuzz_library.append("#")
        self.fuzz_library.append("$")
        self.fuzz_library.append("%")
        self.fuzz_library.append("^")
        self.fuzz_library.append("&")
        self.fuzz_library.append("*")
        self.fuzz_library.append("(")
        self.fuzz_library.append(")")
        self.fuzz_library.append("-")
        self.fuzz_library.append("_")
        self.fuzz_library.append("+")
        self.fuzz_library.append("=")
        self.fuzz_library.append(":")
        self.fuzz_library.append(": " * 100)
        self.fuzz_library.append(":7" * 100)
        self.fuzz_library.append(";")
        self.fuzz_library.append("'")
        self.fuzz_library.append("\"")
        self.fuzz_library.append("/")
        self.fuzz_library.append("\\")
        self.fuzz_library.append("?")
        self.fuzz_library.append("<")
        self.fuzz_library.append(">")
        self.fuzz_library.append(".")
        self.fuzz_library.append(",")
        self.fuzz_library.append("\r")
        self.fuzz_library.append("\n")
        self.fuzz_library.append("\r\n" * 64)
        self.fuzz_library.append("\r\n" * 128)
        self.fuzz_library.append("\r\n" * 512)


########################################################################################################################
class group (base_primitive):
    def __init__ (self, name, values):
        '''
        This primitive represents a list of static values, stepping through each one on mutation. You can tie a block
        to a group primitive to specify that the block should cycle through all possible mutations for *each* value
        within the group. The group primitive is useful for example for representing a list of valid opcodes.

        @type  name:   String
        @param name:   Name of group
        @type  values: List or raw data
        @param values: List of possible raw values this group can take.
        '''

        self.name           = name
        self.values         = values
        self.fuzzable       = True

        self.s_type         = "group"
        self.value          = self.values[0]
        self.original_value = self.values[0]
        self.rendered       = ""
        self.fuzz_complete  = False
        self.mutant_index   = 0

        # sanity check that values list only contains strings (or raw data)
        if self.values != []:
            for val in self.values:
                assert type(val) is str, "Value list may only contain strings or raw data"


    def mutate (self):
        '''
        Move to the next item in the values list.

        @rtype:  False
        @return: False
        '''

        if self.mutant_index == self.num_mutations():
            self.fuzz_complete = True

        # if fuzzing was disabled or complete, and mutate() is called, ensure the original value is restored.
        if not self.fuzzable or self.fuzz_complete:
            self.value = self.values[0]
            return False

        # step through the value list.
        self.value = self.values[self.mutant_index]

        # increment the mutation count.
        self.mutant_index += 1

        return True


    def num_mutations (self):
        '''
        Number of values in this primitive.

        @rtype:  Integer
        @return: Number of values in this primitive.
        '''

        return len(self.values)


########################################################################################################################
class random_data (base_primitive):
    def __init__ (self, value, min_length, max_length, max_mutations=25, fuzzable=True, step=None, name=None):
        '''
        Generate a random chunk of data while maintaining a copy of the original. A random length range can be specified.
        For a static length, set min/max length to be the same.

        @type  value:         Raw
        @param value:         Original value
        @type  min_length:    Integer
        @param min_length:    Minimum length of random block
        @type  max_length:    Integer
        @param max_length:    Maximum length of random block
        @type  max_mutations: Integer
        @param max_mutations: (Optional, def=25) Number of mutations to make before reverting to default
        @type  fuzzable:      Boolean
        @param fuzzable:      (Optional, def=True) Enable/disable fuzzing of this primitive
        @type  step:          Integer
        @param step:          (Optional, def=None) If not null, step count between min and max reps, otherwise random
        @type  name:          String
        @param name:          (Optional, def=None) Specifying a name gives you direct access to a primitive
        '''

        self.value         = self.original_value = str(value)
        self.min_length    = min_length
        self.max_length    = max_length
        self.max_mutations = max_mutations
        self.fuzzable      = fuzzable
        self.step          = step
        self.name          = name

        self.s_type        = "random_data"  # for ease of object identification
        self.rendered      = ""             # rendered value
        self.fuzz_complete = False          # flag if this primitive has been completely fuzzed
        self.mutant_index  = 0              # current mutation number

        if self.step:
            self.max_mutations = (self.max_length - self.min_length) / self.step + 1


    def mutate (self):
        '''
        Mutate the primitive value returning False on completion.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        '''

        # if we've ran out of mutations, raise the completion flag.
        if self.mutant_index == self.num_mutations():
            self.fuzz_complete = True

        # if fuzzing was disabled or complete, and mutate() is called, ensure the original value is restored.
        if not self.fuzzable or self.fuzz_complete:
            self.value = self.original_value
            return False

        # select a random length for this string.
        if not self.step:
            length = random.randint(self.min_length, self.max_length)
        # select a length function of the mutant index and the step.
        else:
            length = self.min_length + self.mutant_index * self.step

        # reset the value and generate a random string of the determined length.
        self.value = ""
        for i in xrange(length):
            self.value += chr(random.randint(0, 255))

        # increment the mutation count.
        self.mutant_index += 1

        return True


    def num_mutations (self):
        '''
        Calculate and return the total number of mutations for this individual primitive.

        @rtype:  Integer
        @return: Number of mutated forms this primitive can take
        '''

        return self.max_mutations


########################################################################################################################
class static (base_primitive):
    def __init__ (self, value, name=None):
        '''
        Primitive that contains static content.

        @type  value: Raw
        @param value: Raw static data
        @type  name:  String
        @param name:  (Optional, def=None) Specifying a name gives you direct access to a primitive
        '''

        self.value         = self.original_value = value
        self.name          = name
        self.fuzzable      = False       # every primitive needs this attribute.
        self.mutant_index  = 0
        self.s_type        = "static"    # for ease of object identification
        self.rendered      = ""
        self.fuzz_complete = True


    def mutate (self):
        '''
        Do nothing.

        @rtype:  False
        @return: False
        '''

        return False


    def num_mutations (self):
        '''
        Return 0.

        @rtype:  0
        @return: 0
        '''

        return 0


########################################################################################################################
class string (base_primitive):
    # store fuzz_library as a class variable to avoid copying the ~70MB structure across each instantiated primitive.
    fuzz_library = []

    def __init__ (self, value, size=-1, padding="\x00", encoding="ascii", fuzzable=True, max_len=0, name=None):
        '''
        Primitive that cycles through a library of "bad" strings. The class variable 'fuzz_library' contains a list of
        smart fuzz values global across all instances. The 'this_library' variable contains fuzz values specific to
        the instantiated primitive. This allows us to avoid copying the near ~70MB fuzz_library data structure across
        each instantiated primitive.

        @type  value:    String
        @param value:    Default string value
        @type  size:     Integer
        @param size:     (Optional, def=-1) Static size of this field, leave -1 for dynamic.
        @type  padding:  Character
        @param padding:  (Optional, def="\\x00") Value to use as padding to fill static field size.
        @type  encoding: String
        @param encoding: (Optonal, def="ascii") String encoding, ex: utf_16_le for Microsoft Unicode.
        @type  fuzzable: Boolean
        @param fuzzable: (Optional, def=True) Enable/disable fuzzing of this primitive
        @type  max_len:  Integer
        @param max_len:  (Optional, def=0) Maximum string length
        @type  name:     String
        @param name:     (Optional, def=None) Specifying a name gives you direct access to a primitive
        '''

        self.value         = self.original_value = value
        self.size          = size
        self.padding       = padding
        self.encoding      = encoding
        self.fuzzable      = fuzzable
        self.name          = name

        self.s_type        = "string"  # for ease of object identification
        self.rendered      = ""        # rendered value
        self.fuzz_complete = False     # flag if this primitive has been completely fuzzed
        self.mutant_index  = 0         # current mutation number

        # add this specific primitives repitition values to the unique fuzz library.
        self.this_library = \
        [
            self.value * 2,
            self.value * 10,
            self.value * 100,

            # UTF-8
            self.value * 2   + "\xfe",
            self.value * 10  + "\xfe",
            self.value * 100 + "\xfe",
        ]

        # if the fuzz library has not yet been initialized, do so with all the global values.
        if not self.fuzz_library:
            string.fuzz_library  = \
            [
                # omission.
                "",

                # strings ripped from spike (and some others I added)
                "/.:/"  + "A"*5000 + "\x00\x00",
                "/.../" + "A"*5000 + "\x00\x00",
                "/.../.../.../.../.../.../.../.../.../.../",
                "/../../../../../../../../../../../../etc/passwd",
                "/../../../../../../../../../../../../boot.ini",
                "..:..:..:..:..:..:..:..:..:..:..:..:..:",
                "\\\\*",
                "\\\\?\\",
                "/\\" * 5000,
                "/." * 5000,
                "!@#$%%^#$%#$@#$%$$@#$%^^**(()",
                "%01%02%03%04%0a%0d%0aADSF",
                "%01%02%03@%04%0a%0d%0aADSF",
                "/%00/",
                "%00/",
                "%00",
                "%u0000",
                "%\xfe\xf0%\x00\xff",
                "%\xfe\xf0%\x01\xff" * 20,

                # format strings.
                "%n"     * 100,
                "%n"     * 500,
                "\"%n\"" * 500,
                "%s"     * 100,
                "%s"     * 500,
                "\"%s\"" * 500,

                # command injection.
                "|touch /tmp/SULLEY",
                ";touch /tmp/SULLEY;",
                "|notepad",
                ";notepad;",
                "\nnotepad\n",

                # SQL injection.
                "1;SELECT%20*",
                "'sqlattempt1",
                "(sqlattempt2)",
                "OR%201=1",

                # some binary strings.
                "\xde\xad\xbe\xef",
                "\xde\xad\xbe\xef" * 10,
                "\xde\xad\xbe\xef" * 100,
                "\xde\xad\xbe\xef" * 1000,
                "\xde\xad\xbe\xef" * 10000,
                "\x00"             * 1000,

                # miscellaneous.
                "\r\n" * 100,
                "<>" * 500,         # sendmail crackaddr (http://lsd-pl.net/other/sendmail.txt)
            ]

            # add some long strings.
            self.add_long_strings("A")
            self.add_long_strings("B")
            self.add_long_strings("1")
            self.add_long_strings("2")
            self.add_long_strings("3")
            self.add_long_strings("<")
            self.add_long_strings(">")
            self.add_long_strings("'")
            self.add_long_strings("\"")
            self.add_long_strings("/")
            self.add_long_strings("\\")
            self.add_long_strings("?")
            self.add_long_strings("=")
            self.add_long_strings("a=")
            self.add_long_strings("&")
            self.add_long_strings(".")
            self.add_long_strings(",")
            self.add_long_strings("(")
            self.add_long_strings(")")
            self.add_long_strings("]")
            self.add_long_strings("[")
            self.add_long_strings("%")
            self.add_long_strings("*")
            self.add_long_strings("-")
            self.add_long_strings("+")
            self.add_long_strings("{")
            self.add_long_strings("}")
            self.add_long_strings("\x14")
            self.add_long_strings("\xFE")   # expands to 4 characters under utf16
            self.add_long_strings("\xFF")   # expands to 4 characters under utf16

            # add some long strings with null bytes thrown in the middle of it.
            for length in [128, 256, 1024, 2048, 4096, 32767, 0xFFFF]:
                s = "B" * length
                s = s[:len(s)/2] + "\x00" + s[len(s)/2:]
                string.fuzz_library.append(s)

            # if the optional file '.fuzz_strings' is found, parse each line as a new entry for the fuzz library.
            try:
                fh = open(".fuzz_strings", "r")

                for fuzz_string in fh.readlines():
                    fuzz_string = fuzz_string.rstrip("\r\n")

                    if fuzz_string != "":
                        string.fuzz_library.append(fuzz_string)

                fh.close()
            except:
                pass

        # delete strings which length is greater than max_len.
        if max_len > 0:
            if any(len(s) > max_len for s in self.this_library):
                self.this_library = list(set([s[:max_len] for s in self.this_library]))

            if any(len(s) > max_len for s in self.fuzz_library):
                self.fuzz_library = list(set([s[:max_len] for s in self.fuzz_library]))


    def add_long_strings (self, sequence):
        '''
        Given a sequence, generate a number of selectively chosen strings lengths of the given sequence and add to the
        string heuristic library.

        @type  sequence: String
        @param sequence: Sequence to repeat for creation of fuzz strings.
        '''

        for length in [128, 255, 256, 257, 511, 512, 513, 1023, 1024, 2048, 2049, 4095, 4096, 4097, 5000, 10000, 20000,
                       32762, 32763, 32764, 32765, 32766, 32767, 32768, 32769, 0xFFFF-2, 0xFFFF-1, 0xFFFF, 0xFFFF+1,
                       0xFFFF+2, 99999, 100000, 500000, 1000000]:

            long_string = sequence * length
            string.fuzz_library.append(long_string)


    def mutate (self):
        '''
        Mutate the primitive by stepping through the fuzz library extended with the "this" library, return False on
        completion.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        '''

        # loop through the fuzz library until a suitable match is found.
        while 1:
            # if we've ran out of mutations, raise the completion flag.
            if self.mutant_index == self.num_mutations():
                self.fuzz_complete = True

            # if fuzzing was disabled or complete, and mutate() is called, ensure the original value is restored.
            if not self.fuzzable or self.fuzz_complete:
                self.value = self.original_value
                return False

            # update the current value from the fuzz library.
            self.value = (self.fuzz_library + self.this_library)[self.mutant_index]

            # increment the mutation count.
            self.mutant_index += 1

            # if the size parameter is disabled, break out of the loop right now.
            if self.size == -1:
                break

            # ignore library items greather then user-supplied length.
            # XXX - might want to make this smarter.
            if len(self.value) > self.size:
                continue

            # pad undersized library items.
            if len(self.value) < self.size:
                self.value = self.value + self.padding * (self.size - len(self.value))
                break

        return True


    def num_mutations (self):
        '''
        Calculate and return the total number of mutations for this individual primitive.

        @rtype:  Integer
        @return: Number of mutated forms this primitive can take
        '''

        return len(self.fuzz_library) + len(self.this_library)


    def render (self):
        '''
        Render the primitive, encode the string according to the specified encoding.
        '''

        # try to encode the string properly and fall back to the default value on failure.
        try:
            self.rendered = str(self.value).encode(self.encoding)
        except:
            self.rendered = self.value

        return self.rendered


########################################################################################################################
class bit_field (base_primitive):
    def __init__ (self, value, width, max_num=None, endian="<", format="binary", signed=False, full_range=False, fuzzable=True, name=None):
        '''
        The bit field primitive represents a number of variable length and is used to define all other integer types.

        @type  value:      Integer
        @param value:      Default integer value
        @type  width:      Integer
        @param width:      Width of bit fields
        @type  endian:     Character
        @param endian:     (Optional, def=LITTLE_ENDIAN) Endianess of the bit field (LITTLE_ENDIAN: <, BIG_ENDIAN: >)
        @type  format:     String
        @param format:     (Optional, def=binary) Output format, "binary" or "ascii"
        @type  signed:     Boolean
        @param signed:     (Optional, def=False) Make size signed vs. unsigned (applicable only with format="ascii")
        @type  full_range: Boolean
        @param full_range: (Optional, def=False) If enabled the field mutates through *all* possible values.
        @type  fuzzable:   Boolean
        @param fuzzable:   (Optional, def=True) Enable/disable fuzzing of this primitive
        @type  name:       String
        @param name:       (Optional, def=None) Specifying a name gives you direct access to a primitive
        '''

        assert(type(value) is int or type(value) is long)
        assert(type(width) is int or type(value) is long)


        self.value         = self.original_value = value
        self.width         = width
        self.max_num       = max_num
        self.endian        = endian
        self.format        = format
        self.signed        = signed
        self.full_range    = full_range
        self.fuzzable      = fuzzable
        self.name          = name

        self.rendered      = ""        # rendered value
        self.fuzz_complete = False     # flag if this primitive has been completely fuzzed
        self.fuzz_library  = []        # library of fuzz heuristics
        self.mutant_index  = 0         # current mutation number

        if self.max_num == None:
            self.max_num = self.to_decimal("1" * width)

        assert(type(self.max_num) is int or type(self.max_num) is long)

        # build the fuzz library.
        if self.full_range:
            # add all possible values.
            for i in xrange(0, self.max_num):
                self.fuzz_library.append(i)
        else:
            # try only "smart" values.
            self.add_integer_boundaries(0)
            self.add_integer_boundaries(self.max_num / 2)
            self.add_integer_boundaries(self.max_num / 3)
            self.add_integer_boundaries(self.max_num / 4)
            self.add_integer_boundaries(self.max_num / 8)
            self.add_integer_boundaries(self.max_num / 16)
            self.add_integer_boundaries(self.max_num / 32)
            self.add_integer_boundaries(self.max_num)

        # if the optional file '.fuzz_ints' is found, parse each line as a new entry for the fuzz library.
        try:
            fh = open(".fuzz_ints", "r")

            for fuzz_int in fh.readlines():
                # convert the line into an integer, continue on failure.
                try:
                    fuzz_int = long(fuzz_int, 16)
                except:
                    continue

                if fuzz_int <= self.max_num:
                    self.fuzz_library.append(fuzz_int)

            fh.close()
        except:
            pass


    def add_integer_boundaries (self, integer):
        '''
        Add the supplied integer and border cases to the integer fuzz heuristics library.

        @type  integer: Int
        @param integer: Integer to append to fuzz heuristics
        '''

        for i in xrange(-10, 10):
            case = integer + i

            # ensure the border case falls within the valid range for this field.
            if 0 <= case <= self.max_num:
                if case not in self.fuzz_library:
                    self.fuzz_library.append(case)


    def render (self):
        '''
        Render the primitive.
        '''

        #
        # binary formatting.
        #

        if self.format == "binary":
            bit_stream = ""
            rendered   = ""

            # pad the bit stream to the next byte boundary.
            if self.width % 8 == 0:
                bit_stream += self.to_binary()
            else:
                bit_stream  = "0" * (8 - (self.width % 8))
                bit_stream += self.to_binary()

            # convert the bit stream from a string of bits into raw bytes.
            for i in xrange(len(bit_stream) / 8):
                chunk = bit_stream[8*i:8*i+8]
                rendered += struct.pack("B", self.to_decimal(chunk))

            # if necessary, convert the endianess of the raw bytes.
            if self.endian == "<":
                rendered = list(rendered)
                rendered.reverse()
                rendered = "".join(rendered)

            self.rendered = rendered

        #
        # ascii formatting.
        #

        else:
            # if the sign flag is raised and we are dealing with a signed integer (first bit is 1).
            if self.signed and self.to_binary()[0] == "1":
                max_num = self.to_decimal("0" + "1" * (self.width - 1))
                # chop off the sign bit.
                val = self.value & max_num

                # account for the fact that the negative scale works backwards.
                val = max_num - val

                # toss in the negative sign.
                self.rendered = "%d" % ~val

            # unsigned integer or positive signed integer.
            else:
                self.rendered = "%d" % self.value

        return self.rendered


    def to_binary (self, number=None, bit_count=None):
        '''
        Convert a number to a binary string.

        @type  number:    Integer
        @param number:    (Optional, def=self.value) Number to convert
        @type  bit_count: Integer
        @param bit_count: (Optional, def=self.width) Width of bit string

        @rtype:  String
        @return: Bit string
        '''

        if number == None:
            number = self.value

        if bit_count == None:
            bit_count = self.width

        return "".join(map(lambda x:str((number >> x) & 1), range(bit_count -1, -1, -1)))


    def to_decimal (self, binary):
        '''
        Convert a binary string to a decimal number.

        @type  binary: String
        @param binary: Binary string

        @rtype:  Integer
        @return: Converted bit string
        '''

        return int(binary, 2)


########################################################################################################################
class byte (bit_field):
    def __init__ (self, value, endian="<", format="binary", signed=False, full_range=False, fuzzable=True, name=None):
        self.s_type  = "byte"
        if type(value) not in [int, long]:
            value       = struct.unpack(endian + "B", value)[0]

        bit_field.__init__(self, value, 8, None, endian, format, signed, full_range, fuzzable, name)


########################################################################################################################
class word (bit_field):
    def __init__ (self, value, endian="<", format="binary", signed=False, full_range=False, fuzzable=True, name=None):
        self.s_type  = "word"
        if type(value) not in [int, long]:
            value = struct.unpack(endian + "H", value)[0]

        bit_field.__init__(self, value, 16, None, endian, format, signed, full_range, fuzzable, name)


########################################################################################################################
class dword (bit_field):
    def __init__ (self, value, endian="<", format="binary", signed=False, full_range=False, fuzzable=True, name=None):
        self.s_type  = "dword"
        if type(value) not in [int, long]:
            value = struct.unpack(endian + "L", value)[0]

        bit_field.__init__(self, value, 32, None, endian, format, signed, full_range, fuzzable, name)


########################################################################################################################
class qword (bit_field):
    def __init__ (self, value, endian="<", format="binary", signed=False, full_range=False, fuzzable=True, name=None):
        self.s_type  = "qword"
        if type(value) not in [int, long]:
            value = struct.unpack(endian + "Q", value)[0]

        bit_field.__init__(self, value, 64, None, endian, format, signed, full_range, fuzzable, name)

########NEW FILE########
__FILENAME__ = sessions
import os
import re
import sys
import zlib
import time
import socket
import httplib
import cPickle
import threading
import BaseHTTPServer
import httplib
import logging

import blocks
import pedrpc
import pgraph
import sex
import primitives


########################################################################################################################
class target:
    '''
    Target descriptor container.
    '''

    def __init__ (self, host, port, **kwargs):
        '''
        @type  host: String
        @param host: Hostname or IP address of target system
        @type  port: Integer
        @param port: Port of target service
        '''

        self.host      = host
        self.port      = port

        # set these manually once target is instantiated.
        self.netmon            = None
        self.procmon           = None
        self.vmcontrol         = None
        self.netmon_options    = {}
        self.procmon_options   = {}
        self.vmcontrol_options = {}


    def pedrpc_connect (self):
        '''
        Pass specified target parameters to the PED-RPC server.
        '''

        # If the process monitor is alive, set it's options
        if self.procmon:
            while 1:
                try:
                    if self.procmon.alive():
                        break
                except:
                    pass

                time.sleep(1)

            # connection established.
            for key in self.procmon_options.keys():
                eval('self.procmon.set_%s(self.procmon_options["%s"])' % (key, key))

        # If the network monitor is alive, set it's options
        if self.netmon:
            while 1:
                try:
                    if self.netmon.alive():
                        break
                except:
                    pass

                time.sleep(1)

            # connection established.
            for key in self.netmon_options.keys():
                eval('self.netmon.set_%s(self.netmon_options["%s"])' % (key, key))


########################################################################################################################
class connection (pgraph.edge.edge):
    def __init__ (self, src, dst, callback=None):
        '''
        Extends pgraph.edge with a callback option. This allows us to register a function to call between node
        transmissions to implement functionality such as challenge response systems. The callback method must follow
        this prototype::

            def callback(session, node, edge, sock)

        Where node is the node about to be sent, edge is the last edge along the current fuzz path to "node", session
        is a pointer to the session instance which is useful for snagging data such as sesson.last_recv which contains
        the data returned from the last socket transmission and sock is the live socket. A callback is also useful in
        situations where, for example, the size of the next packet is specified in the first packet.

        @type  src:      Integer
        @param src:      Edge source ID
        @type  dst:      Integer
        @param dst:      Edge destination ID
        @type  callback: Function
        @param callback: (Optional, def=None) Callback function to pass received data to between node xmits
        '''

        # run the parent classes initialization routine first.
        pgraph.edge.edge.__init__(self, src, dst)

        self.callback = callback


########################################################################################################################
class session (pgraph.graph):
    def __init__(
                  self,
                  session_filename=None,
                  skip=0,
                  sleep_time=1.0,
                  log_level=30,
                  logfile=None,
                  logfile_level=10,
                  proto="tcp",
                  bind=None,
                  restart_interval=0,
                  timeout=5.0,
                  web_port=26000,
                  crash_threshold=3,
                  restart_sleep_time=300
                ):
        '''
        Extends pgraph.graph and provides a container for architecting protocol dialogs.

        @type  session_filename:   String
        @kwarg session_filename:   (Optional, def=None) Filename to serialize persistant data to
        @type  skip:               Integer
        @kwarg skip:               (Optional, def=0) Number of test cases to skip
        @type  sleep_time:         Float
        @kwarg sleep_time:         (Optional, def=1.0) Time to sleep in between tests
        @type  log_level:          Integer
        @kwarg log_level:          (Optional, def=30) Set the log level (CRITICAL : 50 / ERROR : 40 / WARNING : 30 / INFO : 20 / DEBUG : 10)
        @type  logfile:            String
        @kwarg logfile:            (Optional, def=None) Name of log file
        @type  logfile_level:      Integer
        @kwarg logfile_level:      (Optional, def=10) Log level for log file, default is debug
        @type  proto:              String
        @kwarg proto:              (Optional, def="tcp") Communication protocol ("tcp", "udp", "ssl")
        @type  bind:               Tuple (host, port)
        @kwarg bind:               (Optional, def=random) Socket bind address and port
        @type  timeout:            Float
        @kwarg timeout:            (Optional, def=5.0) Seconds to wait for a send/recv prior to timing out
        @type  restart_interval:   Integer
        @kwarg restart_interval    (Optional, def=0) Restart the target after n test cases, disable by setting to 0
        @type  crash_threshold:    Integer
        @kwarg crash_threshold     (Optional, def=3) Maximum number of crashes allowed before a node is exhaust
        @type  restart_sleep_time: Integer
        @kwarg restart_sleep_time: Optional, def=300) Time in seconds to sleep when target can't be restarted
        '''

        # run the parent classes initialization routine first.
        pgraph.graph.__init__(self)

        self.session_filename    = session_filename
        self.skip                = skip
        self.sleep_time          = sleep_time
        self.proto               = proto.lower()
        self.bind                = bind
        self.ssl                 = False
        self.restart_interval    = restart_interval
        self.timeout             = timeout
        self.web_port            = web_port
        self.crash_threshold     = crash_threshold
        self.restart_sleep_time  = restart_sleep_time

        # Initialize logger
        self.logger = logging.getLogger("Sulley_logger")
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] -> %(message)s')

        if logfile != None:
            filehandler = logging.FileHandler(logfile)
            filehandler.setLevel(logfile_level)
            filehandler.setFormatter(formatter)
            self.logger.addHandler(filehandler)

        consolehandler = logging.StreamHandler()
        consolehandler.setFormatter(formatter)
        consolehandler.setLevel(log_level)
        self.logger.addHandler(consolehandler)

        self.total_num_mutations = 0
        self.total_mutant_index  = 0
        self.fuzz_node           = None
        self.targets             = []
        self.netmon_results      = {}
        self.procmon_results     = {}
        self.protmon_results     = {}
        self.pause_flag          = False
        self.crashing_primitives = {}

        if self.proto == "tcp":
            self.proto = socket.SOCK_STREAM

        elif self.proto == "ssl":
            self.proto = socket.SOCK_STREAM
            self.ssl   = True

        elif self.proto == "udp":
            self.proto = socket.SOCK_DGRAM

        else:
            raise sex.error("INVALID PROTOCOL SPECIFIED: %s" % self.proto)

        # import settings if they exist.
        self.import_file()

        # create a root node. we do this because we need to start fuzzing from a single point and the user may want
        # to specify a number of initial requests.
        self.root       = pgraph.node()
        self.root.name  = "__ROOT_NODE__"
        self.root.label = self.root.name
        self.last_recv  = None

        self.add_node(self.root)


    ####################################################################################################################
    def add_node (self, node):
        '''
        Add a pgraph node to the graph. We overload this routine to automatically generate and assign an ID whenever a
        node is added.

        @type  node: pGRAPH Node
        @param node: Node to add to session graph
        '''

        node.number = len(self.nodes)
        node.id     = len(self.nodes)

        if not self.nodes.has_key(node.id):
            self.nodes[node.id] = node

        return self


    ####################################################################################################################
    def add_target (self, target):
        '''
        Add a target to the session. Multiple targets can be added for parallel fuzzing.

        @type  target: session.target
        @param target: Target to add to session
        '''

        # pass specified target parameters to the PED-RPC server.
        target.pedrpc_connect()

        # add target to internal list.
        self.targets.append(target)


    ####################################################################################################################
    def connect (self, src, dst=None, callback=None):
        '''
        Create a connection between the two requests (nodes) and register an optional callback to process in between
        transmissions of the source and destination request. Leverage this functionality to handle situations such as
        challenge response systems. The session class maintains a top level node that all initial requests must be
        connected to. Example::

            sess = sessions.session()
            sess.connect(sess.root, s_get("HTTP"))

        If given only a single parameter, sess.connect() will default to attaching the supplied node to the root node.
        This is a convenient alias and is identical to the second line from the above example::

            sess.connect(s_get("HTTP"))

        If you register callback method, it must follow this prototype::

            def callback(session, node, edge, sock)

        Where node is the node about to be sent, edge is the last edge along the current fuzz path to "node", session
        is a pointer to the session instance which is useful for snagging data such as sesson.last_recv which contains
        the data returned from the last socket transmission and sock is the live socket. A callback is also useful in
        situations where, for example, the size of the next packet is specified in the first packet. As another
        example, if you need to fill in the dynamic IP address of the target register a callback that snags the IP
        from sock.getpeername()[0].

        @type  src:      String or Request (Node)
        @param src:      Source request name or request node
        @type  dst:      String or Request (Node)
        @param dst:      Destination request name or request node
        @type  callback: Function
        @param callback: (Optional, def=None) Callback function to pass received data to between node xmits

        @rtype:  pgraph.edge
        @return: The edge between the src and dst.
        '''

        # if only a source was provided, then make it the destination and set the source to the root node.
        if not dst:
            dst = src
            src = self.root

        # if source or destination is a name, resolve the actual node.
        if type(src) is str:
            src = self.find_node("name", src)

        if type(dst) is str:
            dst = self.find_node("name", dst)

        # if source or destination is not in the graph, add it.
        if src != self.root and not self.find_node("name", src.name):
            self.add_node(src)

        if not self.find_node("name", dst.name):
            self.add_node(dst)

        # create an edge between the two nodes and add it to the graph.
        edge = connection(src.id, dst.id, callback)
        self.add_edge(edge)

        return edge


    ####################################################################################################################
    def export_file (self):
        '''
        Dump various object values to disk.

        @see: import_file()
        '''

        if not self.session_filename:
            return

        data = {}
        data["session_filename"]    = self.session_filename
        data["skip"]                = self.total_mutant_index
        data["sleep_time"]          = self.sleep_time
        data["restart_sleep_time"]  = self.restart_sleep_time
        data["proto"]               = self.proto
        data["restart_interval"]    = self.restart_interval
        data["timeout"]             = self.timeout
        data["web_port"]            = self.web_port
        data["crash_threshold"]     = self.crash_threshold
        data["total_num_mutations"] = self.total_num_mutations
        data["total_mutant_index"]  = self.total_mutant_index
        data["netmon_results"]      = self.netmon_results
        data["procmon_results"]     = self.procmon_results
        data['protmon_results']     = self.protmon_results
        data["pause_flag"]          = self.pause_flag

        fh = open(self.session_filename, "wb+")
        fh.write(zlib.compress(cPickle.dumps(data, protocol=2)))
        fh.close()


    ####################################################################################################################
    def fuzz (self, this_node=None, path=[]):
        '''
        Call this routine to get the ball rolling. No arguments are necessary as they are both utilized internally
        during the recursive traversal of the session graph.

        @type  this_node: request (node)
        @param this_node: (Optional, def=None) Current node that is being fuzzed.
        @type  path:      List
        @param path:      (Optional, def=[]) Nodes along the path to the current one being fuzzed.
        '''

        # if no node is specified, then we start from the root node and initialize the session.
        if not this_node:
            # we can't fuzz if we don't have at least one target and one request.
            if not self.targets:
                raise sex.error("NO TARGETS SPECIFIED IN SESSION")

            if not self.edges_from(self.root.id):
                raise sex.error("NO REQUESTS SPECIFIED IN SESSION")

            this_node = self.root

            try:    self.server_init()
            except: return

        # XXX - TODO - complete parallel fuzzing, will likely have to thread out each target
        target = self.targets[0]

        # step through every edge from the current node.
        for edge in self.edges_from(this_node.id):
            # the destination node is the one actually being fuzzed.
            self.fuzz_node = self.nodes[edge.dst]
            num_mutations  = self.fuzz_node.num_mutations()

            # keep track of the path as we fuzz through it, don't count the root node.
            # we keep track of edges as opposed to nodes because if there is more then one path through a set of
            # given nodes we don't want any ambiguity.
            path.append(edge)

            current_path  = " -> ".join([self.nodes[e.src].name for e in path[1:]])
            current_path += " -> %s" % self.fuzz_node.name

            self.logger.error("current fuzz path: %s" % current_path)
            self.logger.error("fuzzed %d of %d total cases" % (self.total_mutant_index, self.total_num_mutations))

            done_with_fuzz_node = False
            crash_count         = 0

            # loop through all possible mutations of the fuzz node.
            while not done_with_fuzz_node:
                # if we need to pause, do so.
                self.pause()

                # if we have exhausted the mutations of the fuzz node, break out of the while(1).
                # note: when mutate() returns False, the node has been reverted to the default (valid) state.
                if not self.fuzz_node.mutate():
                    self.logger.error("all possible mutations for current fuzz node exhausted")
                    done_with_fuzz_node = True
                    continue

                # make a record in the session that a mutation was made.
                self.total_mutant_index += 1

                # if we've hit the restart interval, restart the target.
                if self.restart_interval and self.total_mutant_index % self.restart_interval == 0:
                    self.logger.error("restart interval of %d reached" % self.restart_interval)
                    self.restart_target(target)

                # exception error handling routine, print log message and restart target.
                def error_handler (e, msg, target, sock=None):
                    if sock:
                        sock.close()

                    msg += "\nException caught: %s" % repr(e)
                    msg += "\nRestarting target and trying again"

                    self.logger.critical(msg)
                    self.restart_target(target)

                # if we don't need to skip the current test case.
                if self.total_mutant_index > self.skip:
                    self.logger.error("fuzzing %d of %d" % (self.fuzz_node.mutant_index, num_mutations))

                    # attempt to complete a fuzz transmission. keep trying until we are successful, whenever a failure
                    # occurs, restart the target.
                    while 1:
                        # instruct the debugger/sniffer that we are about to send a new fuzz.
                        if target.procmon:
                            try:
                                target.procmon.pre_send(self.total_mutant_index)
                            except Exception, e:
                                error_handler(e, "failed on procmon.pre_send()", target)
                                continue

                        if target.netmon:
                            try:
                                target.netmon.pre_send(self.total_mutant_index)
                            except Exception, e:
                                error_handler(e, "failed on netmon.pre_send()", target)
                                continue

                        try:
                            # establish a connection to the target.
                            sock = socket.socket(socket.AF_INET, self.proto)
                        except Exception, e:
                            error_handler(e, "failed creating socket", target)
                            continue

                        if self.bind:
                            try:
                                sock.bind(self.bind)
                            except Exception, e:
                                error_handler(e, "failed binding on socket", target, sock)
                                continue

                        try:
                            sock.settimeout(self.timeout)
                            # Connect is needed only for TCP stream
                            if self.proto == socket.SOCK_STREAM:
                                sock.connect((target.host, target.port))
                        except Exception, e:
                            error_handler(e, "failed connecting on socket", target, sock)
                            continue

                        # if SSL is requested, then enable it.
                        if self.ssl:
                            try:
                                ssl  = socket.ssl(sock)
                                sock = httplib.FakeSocket(sock, ssl)
                            except Exception, e:
                                error_handler(e, "failed ssl setup", target, sock)
                                continue

                        # if the user registered a pre-send function, pass it the sock and let it do the deed.
                        try:
                            self.pre_send(sock)
                        except Exception, e:
                            error_handler(e, "pre_send() failed", target, sock)
                            continue

                        # send out valid requests for each node in the current path up to the node we are fuzzing.
                        try:
                            for e in path[:-1]:
                                node = self.nodes[e.dst]
                                self.transmit(sock, node, e, target)
                        except Exception, e:
                            error_handler(e, "failed transmitting a node up the path", target, sock)
                            continue

                        # now send the current node we are fuzzing.
                        try:
                            self.transmit(sock, self.fuzz_node, edge, target)
                        except Exception, e:
                            error_handler(e, "failed transmitting fuzz node", target, sock)
                            continue

                        # if we reach this point the send was successful for break out of the while(1).
                        break

                    # if the user registered a post-send function, pass it the sock and let it do the deed.
                    # we do this outside the try/except loop because if our fuzz causes a crash then the post_send()
                    # will likely fail and we don't want to sit in an endless loop.
                    try:
                        self.post_send(sock)
                    except Exception, e:
                        error_handler(e, "post_send() failed", target, sock)

                    # done with the socket.
                    sock.close()

                    # delay in between test cases.
                    self.logger.warning("sleeping for %f seconds" % self.sleep_time)
                    time.sleep(self.sleep_time)

                    # poll the PED-RPC endpoints (netmon, procmon etc...) for the target.
                    self.poll_pedrpc(target)

                    # serialize the current session state to disk.
                    self.export_file()

            # recursively fuzz the remainder of the nodes in the session graph.
            self.fuzz(self.fuzz_node, path)

        # finished with the last node on the path, pop it off the path stack.
        if path:
            path.pop()

        # loop to keep the main thread running and be able to receive signals
        if self.signal_module:
            # wait for a signal only if fuzzing is finished (this function is recursive)
            # if fuzzing is not finished, web interface thread will catch it
            if self.total_mutant_index == self.total_num_mutations:
                import signal
                while True:
                    signal.pause()


    ####################################################################################################################
    def import_file (self):
        '''
        Load varous object values from disk.

        @see: export_file()
        '''

        try:
            fh   = open(self.session_filename, "rb")
            data = cPickle.loads(zlib.decompress(fh.read()))
            fh.close()
        except:
            return

        # update the skip variable to pick up fuzzing from last test case.
        self.skip                = data["total_mutant_index"]

        self.session_filename    = data["session_filename"]
        self.sleep_time          = data["sleep_time"]
        self.restart_sleep_time  = data["restart_sleep_time"]
        self.proto               = data["proto"]
        self.restart_interval    = data["restart_interval"]
        self.timeout             = data["timeout"]
        self.web_port            = data["web_port"]
        self.crash_threshold     = data["crash_threshold"]
        self.total_num_mutations = data["total_num_mutations"]
        self.total_mutant_index  = data["total_mutant_index"]
        self.netmon_results      = data["netmon_results"]
        self.procmon_results     = data["procmon_results"]
        self.protmon_results     = data["protmon_results"]
        self.pause_flag          = data["pause_flag"]


    ####################################################################################################################
    #def log (self, msg, level=1):
        '''
        If the supplied message falls under the current log level, print the specified message to screen.

        @type  msg: String
        @param msg: Message to log
        '''
#
        #if self.log_level >= level:
            #print "[%s] %s" % (time.strftime("%I:%M.%S"), msg)


    ####################################################################################################################
    def num_mutations (self, this_node=None, path=[]):
        '''
        Number of total mutations in the graph. The logic of this routine is identical to that of fuzz(). See fuzz()
        for inline comments. The member varialbe self.total_num_mutations is updated appropriately by this routine.

        @type  this_node: request (node)
        @param this_node: (Optional, def=None) Current node that is being fuzzed.
        @type  path:      List
        @param path:      (Optional, def=[]) Nodes along the path to the current one being fuzzed.

        @rtype:  Integer
        @return: Total number of mutations in this session.
        '''

        if not this_node:
            this_node                = self.root
            self.total_num_mutations = 0

        for edge in self.edges_from(this_node.id):
            next_node                 = self.nodes[edge.dst]
            self.total_num_mutations += next_node.num_mutations()

            if edge.src != self.root.id:
                path.append(edge)

            self.num_mutations(next_node, path)

        # finished with the last node on the path, pop it off the path stack.
        if path:
            path.pop()

        return self.total_num_mutations


    ####################################################################################################################
    def pause (self):
        '''
        If thet pause flag is raised, enter an endless loop until it is lowered.
        '''

        while 1:
            if self.pause_flag:
                time.sleep(1)
            else:
                break


    ####################################################################################################################
    def poll_pedrpc (self, target):
        '''
        Poll the PED-RPC endpoints (netmon, procmon etc...) for the target.

        @type  target: session.target
        @param target: Session target whose PED-RPC services we are polling
        '''

        # kill the pcap thread and see how many bytes the sniffer recorded.
        if target.netmon:
            bytes = target.netmon.post_send()
            self.logger.error("netmon captured %d bytes for test case #%d" % (bytes, self.total_mutant_index))
            self.netmon_results[self.total_mutant_index] = bytes

        # check if our fuzz crashed the target. procmon.post_send() returns False if the target access violated.
        if target.procmon and not target.procmon.post_send():
            self.logger.error("procmon detected access violation on test case #%d" % self.total_mutant_index)

            # retrieve the primitive that caused the crash and increment it's individual crash count.
            self.crashing_primitives[self.fuzz_node.mutant] = self.crashing_primitives.get(self.fuzz_node.mutant, 0) + 1

            # notify with as much information as possible.
            if not self.fuzz_node.mutant.name: msg = "primitive lacks a name, "
            else:                              msg = "primitive name: %s, " % self.fuzz_node.mutant.name

            msg += "type: %s, default value: %s" % (self.fuzz_node.mutant.s_type, self.fuzz_node.mutant.original_value)
            self.logger.error(msg)

            # print crash synopsis
            self.procmon_results[self.total_mutant_index] = target.procmon.get_crash_synopsis()
            self.logger.error(self.procmon_results[self.total_mutant_index].split("\n")[0])

            # if the user-supplied crash threshold is reached, exhaust this node.
            if self.crashing_primitives[self.fuzz_node.mutant] >= self.crash_threshold:
                # as long as we're not a group and not a repeat.
                if not isinstance(self.fuzz_node.mutant, primitives.group):
                    if not isinstance(self.fuzz_node.mutant, blocks.repeat):
                        skipped = self.fuzz_node.mutant.exhaust()
                        self.logger.warning("crash threshold reached for this primitive, exhausting %d mutants." % skipped)
                        self.total_mutant_index += skipped
                        self.fuzz_node.mutant_index += skipped

            # start the target back up.
            # If it returns False, stop the test
            if self.restart_target(target, stop_first=False) == False:
                self.logger.critical("Restarting the target failed, exiting.")
                self.export_file()
                try:
                    self.thread.join()
                except:
                    self.logger.debug( "No server launched")
                sys.exit(0)



    ####################################################################################################################
    def post_send (self, sock):
        '''
        Overload or replace this routine to specify actions to run after to each fuzz request. The order of events is
        as follows::

            pre_send() - req - callback ... req - callback - post_send()

        When fuzzing RPC for example, register this method to tear down the RPC request.

        @see: pre_send()

        @type  sock: Socket
        @param sock: Connected socket to target
        '''

        # default to doing nothing.
        pass


    ####################################################################################################################
    def pre_send (self, sock):
        '''
        Overload or replace this routine to specify actions to run prior to each fuzz request. The order of events is
        as follows::

            pre_send() - req - callback ... req - callback - post_send()

        When fuzzing RPC for example, register this method to establish the RPC bind.

        @see: pre_send()

        @type  sock: Socket
        @param sock: Connected socket to target
        '''

        # default to doing nothing.
        pass


    ####################################################################################################################
    def restart_target (self, target, stop_first=True):
        '''
        Restart the fuzz target. If a VMControl is available revert the snapshot, if a process monitor is available
        restart the target process. Otherwise, do nothing.

        @type  target: session.target
        @param target: Target we are restarting
        '''

        # vm restarting is the preferred method so try that first.
        if target.vmcontrol:
            self.logger.warning("restarting target virtual machine")
            target.vmcontrol.restart_target()

        # if we have a connected process monitor, restart the target process.
        elif target.procmon:
            self.logger.warning("restarting target process")
            if stop_first:
                target.procmon.stop_target()

            if not target.procmon.start_target():
                return False

            # give the process a few seconds to settle in.
            time.sleep(3)

        # otherwise all we can do is wait a while for the target to recover on its own.
        else:
            self.logger.error("no vmcontrol or procmon channel available ... sleeping for %d seconds" % self.restart_sleep_time)
            time.sleep(self.restart_sleep_time)
            # XXX : should be good to relaunch test for crash before returning False
            return False

        # pass specified target parameters to the PED-RPC server to re-establish connections.
        target.pedrpc_connect()


    ####################################################################################################################
    def server_init (self):
        '''
        Called by fuzz() on first run (not on recursive re-entry) to initialize variables, web interface, etc...
        '''

        self.total_mutant_index  = 0
        self.total_num_mutations = self.num_mutations()

        # web interface thread doesn't catch KeyboardInterrupt
        # add a signal handler, and exit on SIGINT
        # XXX - should wait for the end of the ongoing test case, and stop gracefully netmon and procmon
        #     - doesn't work on OS where the signal module isn't available
        try:
            import signal
            self.signal_module = True
        except:
            self.signal_module = False
        if self.signal_module:
            def exit_abruptly(signal, frame):
                '''Save current settings (just in case) and exit'''
                self.export_file()
                self.logger.critical("SIGINT received ... exiting")
                try:
                    self.thread.join()
                except:
                    self.logger.debug( "No server launched")

                sys.exit(0)
            signal.signal(signal.SIGINT, exit_abruptly)

        # spawn the web interface.
        self.thread = web_interface_thread(self)
        self.thread.start()


    ####################################################################################################################
    def transmit (self, sock, node, edge, target):
        '''
        Render and transmit a node, process callbacks accordingly.

        @type  sock:   Socket
        @param sock:   Socket to transmit node on
        @type  node:   Request (Node)
        @param node:   Request/Node to transmit
        @type  edge:   Connection (pgraph.edge)
        @param edge:   Edge along the current fuzz path from "node" to next node.
        @type  target: session.target
        @param target: Target we are transmitting to
        '''

        data = None

        # if the edge has a callback, process it. the callback has the option to render the node, modify it and return.
        if edge.callback:
            data = edge.callback(self, node, edge, sock)

        self.logger.error("xmitting: [%d.%d]" % (node.id, self.total_mutant_index))

        # if no data was returned by the callback, render the node here.
        if not data:
            data = node.render()

        # if data length is > 65507 and proto is UDP, truncate it.
        # XXX - this logic does not prevent duplicate test cases, need to address this in the future.
        if self.proto == socket.SOCK_DGRAM:
            # max UDP packet size.
            # XXX - anyone know how to determine this value smarter?
            MAX_UDP = 65507

            if os.name != "nt" and os.uname()[0] == "Darwin":
                MAX_UDP = 9216

            if len(data) > MAX_UDP:
                self.logger.debug("Too much data for UDP, truncating to %d bytes" % MAX_UDP)
                data = data[:MAX_UDP]

        try:
            if self.proto == socket.SOCK_STREAM:
                sock.send(data)
            else:
                sock.sendto(data, (self.targets[0].host, self.targets[0].port))
            self.logger.debug("Packet sent : " + repr(data))
        except Exception, inst:
            self.logger.error("Socket error, send: %s" % inst)

        if self.proto == (socket.SOCK_STREAM or socket.SOCK_DGRAM):
            # XXX - might have a need to increase this at some point. (possibly make it a class parameter)
            try:
                self.last_recv = sock.recv(10000)
            except Exception, e:
                self.last_recv = ""
        else:
            self.last_recv = ""

        if len(self.last_recv) > 0:
            self.logger.debug("received: [%d] %s" % (len(self.last_recv), repr(self.last_recv)))
        else:
            self.logger.warning("Nothing received on socket.")
            # Increment individual crash count
            self.crashing_primitives[self.fuzz_node.mutant] = self.crashing_primitives.get(self.fuzz_node.mutant,0) +1
            # Note crash information
            self.protmon_results[self.total_mutant_index] = data ;
            #print self.protmon_results



########################################################################################################################
class web_interface_handler (BaseHTTPServer.BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        self.session = None


    def commify (self, number):
        number     = str(number)
        processing = 1
        regex      = re.compile(r"^(-?\d+)(\d{3})")

        while processing:
            (number, processing) = regex.subn(r"\1,\2",number)

        return number


    def do_GET (self):
        self.do_everything()


    def do_HEAD (self):
        self.do_everything()


    def do_POST (self):
        self.do_everything()


    def do_everything (self):
        if "pause" in self.path:
            self.session.pause_flag = True

        if "resume" in self.path:
            self.session.pause_flag = False

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        if "view_crash" in self.path:
            response = self.view_crash(self.path)
        elif "view_pcap" in self.path:
            response = self.view_pcap(self.path)
        else:
            response = self.view_index()

        self.wfile.write(response)


    def log_error (self, *args, **kwargs):
        pass


    def log_message (self, *args, **kwargs):
        pass


    def version_string (self):
        return "Sulley Fuzz Session"


    def view_crash (self, path):
        test_number = int(path.split("/")[-1])
        return "<html><pre>%s</pre></html>" % self.session.procmon_results[test_number]


    def view_pcap (self, path):
        return path


    def view_index (self):
        response = """
                    <html>
                    <head>
                    <meta http-equiv="refresh" content="5">
                        <title>Sulley Fuzz Control</title>
                        <style>
                            a:link    {color: #FF8200; text-decoration: none;}
                            a:visited {color: #FF8200; text-decoration: none;}
                            a:hover   {color: #C5C5C5; text-decoration: none;}

                            body
                            {
                                background-color: #000000;
                                font-family:      Arial, Helvetica, sans-serif;
                                font-size:        12px;
                                color:            #FFFFFF;
                            }

                            td
                            {
                                font-family:      Arial, Helvetica, sans-serif;
                                font-size:        12px;
                                color:            #A0B0B0;
                            }

                            .fixed
                            {
                                font-family:      Courier New;
                                font-size:        12px;
                                color:            #A0B0B0;
                            }

                            .input
                            {
                                font-family:      Arial, Helvetica, sans-serif;
                                font-size:        11px;
                                color:            #FFFFFF;
                                background-color: #333333;
                                border:           thin none;
                                height:           20px;
                            }
                        </style>
                    </head>
                    <body>
                    <center>
                    <table border=0 cellpadding=5 cellspacing=0 width=750><tr><td>
                    <!-- begin bounding table -->

                    <table border=0 cellpadding=5 cellspacing=0 width="100%%">
                    <tr bgcolor="#333333">
                        <td><div style="font-size: 20px;">Sulley Fuzz Control</div></td>
                        <td align=right><div style="font-weight: bold; font-size: 20px;">%(status)s</div></td>
                    </tr>
                    <tr bgcolor="#111111">
                        <td colspan=2 align="center">
                            <table border=0 cellpadding=0 cellspacing=5>
                                <tr bgcolor="#111111">
                                    <td><b>Total:</b></td>
                                    <td>%(total_mutant_index)s</td>
                                    <td>of</td>
                                    <td>%(total_num_mutations)s</td>
                                    <td class="fixed">%(progress_total_bar)s</td>
                                    <td>%(progress_total)s</td>
                                </tr>
                                <tr bgcolor="#111111">
                                    <td><b>%(current_name)s:</b></td>
                                    <td>%(current_mutant_index)s</td>
                                    <td>of</td>
                                    <td>%(current_num_mutations)s</td>
                                    <td class="fixed">%(progress_current_bar)s</td>
                                    <td>%(progress_current)s</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            <form method=get action="/pause">
                                <input class="input" type="submit" value="Pause">
                            </form>
                        </td>
                        <td align=right>
                            <form method=get action="/resume">
                                <input class="input" type="submit" value="Resume">
                            </form>
                        </td>
                    </tr>
                    </table>

                    <!-- begin procmon results -->
                    <table border=0 cellpadding=5 cellspacing=0 width="100%%">
                        <tr bgcolor="#333333">
                            <td nowrap>Test Case #</td>
                            <td>Crash Synopsis</td>
                            <td nowrap>Captured Bytes</td>
                        </tr>
                    """

        keys = self.session.procmon_results.keys()
        keys.sort()
        for key in keys:
            val   = self.session.procmon_results[key]
            bytes = "&nbsp;"

            if self.session.netmon_results.has_key(key):
                bytes = self.commify(self.session.netmon_results[key])

            response += '<tr><td class="fixed"><a href="/view_crash/%d">%06d</a></td><td>%s</td><td align=right>%s</td></tr>' % (key, key, val.split("\n")[0], bytes)

        response += """
                    <!-- end procmon results -->
                    </table>

                    <!-- end bounding table -->
                    </td></tr></table>
                    </center>
                    </body>
                    </html>
                   """

        # what is the fuzzing status.
        if self.session.pause_flag:
            status = "<font color=red>PAUSED</font>"
        else:
            status = "<font color=green>RUNNING</font>"

        # if there is a current fuzz node.
        if self.session.fuzz_node:
            # which node (request) are we currently fuzzing.
            if self.session.fuzz_node.name:
                current_name = self.session.fuzz_node.name
            else:
                current_name = "[N/A]"

            # render sweet progress bars.
            progress_current     = float(self.session.fuzz_node.mutant_index) / float(self.session.fuzz_node.num_mutations())
            num_bars             = int(progress_current * 50)
            progress_current_bar = "[" + "=" * num_bars + "&nbsp;" * (50 - num_bars) + "]"
            progress_current     = "%.3f%%" % (progress_current * 100)

            progress_total       = float(self.session.total_mutant_index) / float(self.session.total_num_mutations)
            num_bars             = int(progress_total * 50)
            progress_total_bar   = "[" + "=" * num_bars + "&nbsp;" * (50 - num_bars) + "]"
            progress_total       = "%.3f%%" % (progress_total * 100)

            response %= \
            {
                "current_mutant_index"  : self.commify(self.session.fuzz_node.mutant_index),
                "current_name"          : current_name,
                "current_num_mutations" : self.commify(self.session.fuzz_node.num_mutations()),
                "progress_current"      : progress_current,
                "progress_current_bar"  : progress_current_bar,
                "progress_total"        : progress_total,
                "progress_total_bar"    : progress_total_bar,
                "status"                : status,
                "total_mutant_index"    : self.commify(self.session.total_mutant_index),
                "total_num_mutations"   : self.commify(self.session.total_num_mutations),
            }
        else:
            response %= \
            {
                "current_mutant_index"  : "",
                "current_name"          : "",
                "current_num_mutations" : "",
                "progress_current"      : "",
                "progress_current_bar"  : "",
                "progress_total"        : "",
                "progress_total_bar"    : "",
                "status"                : "<font color=yellow>UNAVAILABLE</font>",
                "total_mutant_index"    : "",
                "total_num_mutations"   : "",
            }

        return response


########################################################################################################################
class web_interface_server (BaseHTTPServer.HTTPServer):
    '''
    http://docs.python.org/lib/module-BaseHTTPServer.html
    '''

    def __init__(self, server_address, RequestHandlerClass, session):
        BaseHTTPServer.HTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.RequestHandlerClass.session = session


########################################################################################################################
class web_interface_thread (threading.Thread):
    def __init__ (self, session):
        threading.Thread.__init__(self, name="SulleyWebServer")

        self._stopevent = threading.Event()
        self.session = session
        self.server  = None


    def run (self):
        self.server = web_interface_server(('', self.session.web_port), web_interface_handler, self.session)
        while not self._stopevent.isSet():
            self.server.handle_request()

    def join(self, timeout=None):
        # A little dirty but no other solution afaik
        self._stopevent.set()
        conn = httplib.HTTPConnection("localhost:%d" % self.session.web_port)
        conn.request("GET", "/")
        conn.getresponse()

########NEW FILE########
__FILENAME__ = sex
# Sulley EXception Class

class error (Exception):
    def __init__ (self, message):
        self.message = message

    def __str__ (self):
        return self.message
########NEW FILE########
__FILENAME__ = dcerpc
import math
import struct
import misc

########################################################################################################################
def bind (uuid, version):
    '''
    Generate the data necessary to bind to the specified interface.
    '''

    major, minor = version.split(".")

    major = struct.pack("<H", int(major))
    minor = struct.pack("<H", int(minor))

    bind  = "\x05\x00"                      # version 5.0
    bind += "\x0b"                          # packet type = bind (11)
    bind += "\x03"                          # packet flags = last/first flag set
    bind += "\x10\x00\x00\x00"              # data representation
    bind += "\x48\x00"                      # frag length: 72
    bind += "\x00\x00"                      # auth length
    bind += "\x00\x00\x00\x00"              # call id
    bind += "\xb8\x10"                      # max xmit frag (4280)
    bind += "\xb8\x10"                      # max recv frag (4280)
    bind += "\x00\x00\x00\x00"              # assoc group
    bind += "\x01"                          # number of ctx items (1)
    bind += "\x00\x00\x00"                  # padding
    bind += "\x00\x00"                      # context id (0)
    bind += "\x01"                          # number of trans items (1)
    bind += "\x00"                          # padding
    bind += misc.uuid_str_to_bin(uuid)      # abstract syntax
    bind += major                           # interface version
    bind += minor                           # interface version minor

    # transfer syntax 8a885d04-1ceb-11c9-9fe8-08002b104860 v2.0
    bind += "\x04\x5d\x88\x8a\xeb\x1c\xc9\x11\x9f\xe8\x08\x00\x2b\x10\x48\x60"
    bind += "\x02\x00\x00\x00"

    return bind


########################################################################################################################
def bind_ack (data):
    '''
    Ensure the data is a bind ack and that the
    '''

    # packet type == bind ack (12)?
    if data[2] != "\x0c":
        return False

    # ack result == acceptance?
    if data[36:38] != "\x00\x00":
        return False

    return True


########################################################################################################################
def request (opnum, data):
    '''
    Return a list of packets broken into 5k fragmented chunks necessary to make the RPC request.
    '''

    frag_size = 1000     # max frag size = 5840?
    frags     = []

    num_frags = int(math.ceil(float(len(data)) / float(frag_size)))

    for i in xrange(num_frags):
        chunk       = data[i * frag_size:(i+1) * frag_size]
        frag_length = struct.pack("<H", len(chunk) + 24)
        alloc_hint  = struct.pack("<L", len(chunk))

        flags = 0
        if i == 0:              flags |= 0x1    # first frag
        if i == num_frags - 1:  flags |= 0x2    # last frag

        request  = "\x05\x00"                   # version 5.0
        request += "\x00"                       # packet type = request (0)
        request += struct.pack("B", flags)      # packet flags
        request += "\x10\x00\x00\x00"           # data representation
        request += frag_length                  # frag length
        request += "\x00\x00"                   # auth length
        request += "\x00\x00\x00\x00"           # call id
        request += alloc_hint                   # alloc hint
        request += "\x00\x00"                   # context id (0)
        request += struct.pack("<H", opnum)     # opnum
        request += chunk

        frags.append(request)

    # you don't have to send chunks out individually. so make life easier for the user and send them all at once.
    return "".join(frags)
########NEW FILE########
__FILENAME__ = misc
import re
import struct


########################################################################################################################
def crc16 (string, value=0):
    '''
    CRC-16 poly: p(x) = x**16 + x**15 + x**2 + 1
    '''

    crc16_table = []

    for byte in range(256):
         crc = 0

         for bit in range(8):
             if (byte ^ crc) & 1: crc = (crc >> 1) ^ 0xa001  # polly
             else:                crc >>= 1

             byte >>= 1

         crc16_table.append(crc)

    for ch in string:
        value = crc16_table[ord(ch) ^ (value & 0xff)] ^ (value >> 8)

    return value


########################################################################################################################
def uuid_bin_to_str (uuid):
    '''
    Convert a binary UUID to human readable string.
    '''

    (block1, block2, block3) = struct.unpack("<LHH", uuid[:8])
    (block4, block5, block6) = struct.unpack(">HHL", uuid[8:16])

    return "%08x-%04x-%04x-%04x-%04x%08x" % (block1, block2, block3, block4, block5, block6)


########################################################################################################################
def uuid_str_to_bin (uuid):
    '''
    Ripped from Core Impacket. Converts a UUID string to binary form.
    '''

    matches = re.match('([\dA-Fa-f]{8})-([\dA-Fa-f]{4})-([\dA-Fa-f]{4})-([\dA-Fa-f]{4})-([\dA-Fa-f]{4})([\dA-Fa-f]{8})', uuid)

    (uuid1, uuid2, uuid3, uuid4, uuid5, uuid6) = map(lambda x: long(x, 16), matches.groups())

    uuid  = struct.pack('<LHH', uuid1, uuid2, uuid3)
    uuid += struct.pack('>HHL', uuid4, uuid5, uuid6)

    return uuid

########NEW FILE########
__FILENAME__ = scada
import math
import struct


########################################################################################################################
def dnp3 (data, control_code="\x44", src="\x00\x00", dst="\x00\x00"):
    num_packets = int(math.ceil(float(len(data)) / 250.0))
    packets     = []

    for i in xrange(num_packets):
        slice = data[i*250 : (i+1)*250]

        p  = "\x05\x64"
        p += chr(len(slice))
        p += control_code
        p += dst
        p += src

        chksum = struct.pack("<H", crc16(p))

        p += chksum

        num_chunks = int(math.ceil(float(len(slice) / 16.0)))

        # insert the fragmentation flags / sequence number.
        # first frag: 0x40, last frag: 0x80

        frag_number = i

        if i == 0:
            frag_number |= 0x40

        if i == num_packets - 1:
            frag_number |= 0x80

        p += chr(frag_number)

        for x in xrange(num_chunks):
            chunk   = slice[i*16 : (i+1)*16]
            chksum  = struct.pack("<H", crc16(chunk))
            p      += chksum + chunk

        packets.append(p)

    return packets

########NEW FILE########
__FILENAME__ = unit_test
#!c:\\python\\python.exe

import unit_tests

unit_tests.blocks.run()
unit_tests.legos.run()
unit_tests.primitives.run()
########NEW FILE########
__FILENAME__ = blocks
from sulley import *

def run ():
    groups_and_num_test_cases()
    dependencies()
    repeaters()
    return_current_mutant()
    exhaustion()

    # clear out the requests.
    blocks.REQUESTS = {}
    blocks.CURRENT  = None


########################################################################################################################
def groups_and_num_test_cases ():
    s_initialize("UNIT TEST 1")
    s_size("BLOCK", length=4, name="sizer")
    s_group("group", values=["\x01", "\x05", "\x0a", "\xff"])
    if s_block_start("BLOCK"):
        s_delim(">", name="delim")
        s_string("pedram", name="string")
        s_byte(0xde, name="byte")
        s_word(0xdead, name="word")
        s_dword(0xdeadbeef, name="dword")
        s_qword(0xdeadbeefdeadbeef, name="qword")
        s_random(0, 5, 10, 100, name="random")
        s_block_end()


    # count how many mutations we get per primitive type.
    req1 = s_get("UNIT TEST 1")
    print "PRIMITIVE MUTATION COUNTS (SIZES):"
    print "\tdelim:  %d\t(%s)" % (req1.names["delim"].num_mutations(),  sum(map(len, req1.names["delim"].fuzz_library)))
    print "\tstring: %d\t(%s)" % (req1.names["string"].num_mutations(), sum(map(len, req1.names["string"].fuzz_library)))
    print "\tbyte:   %d"      %  req1.names["byte"].num_mutations()
    print "\tword:   %d"      %  req1.names["word"].num_mutations()
    print "\tdword:  %d"      %  req1.names["dword"].num_mutations()
    print "\tqword:  %d"      %  req1.names["qword"].num_mutations()
    print "\tsizer:  %d"      %  req1.names["sizer"].num_mutations()

    # we specify the number of mutations in a random field, so ensure that matches.
    assert(req1.names["random"].num_mutations() == 100)

    # we specify the number of values in a group field, so ensure that matches.
    assert(req1.names["group"].num_mutations() == 4)

    # assert that the number of block mutations equals the sum of the number of mutations of its components.
    assert(req1.names["BLOCK"].num_mutations() == req1.names["delim"].num_mutations()  + \
                                                  req1.names["string"].num_mutations() + \
                                                  req1.names["byte"].num_mutations()   + \
                                                  req1.names["word"].num_mutations()   + \
                                                  req1.names["dword"].num_mutations()  + \
                                                  req1.names["qword"].num_mutations()  + \
                                                  req1.names["random"].num_mutations())

    s_initialize("UNIT TEST 2")
    s_group("group", values=["\x01", "\x05", "\x0a", "\xff"])
    if s_block_start("BLOCK", group="group"):
        s_delim(">", name="delim")
        s_string("pedram", name="string")
        s_byte(0xde, name="byte")
        s_word(0xdead, name="word")
        s_dword(0xdeadbeef, name="dword")
        s_qword(0xdeadbeefdeadbeef, name="qword")
        s_random(0, 5, 10, 100, name="random")
        s_block_end()

    # assert that the number of block mutations in request 2 is len(group.values) (4) times that of request 1.
    req2 = s_get("UNIT TEST 2")
    assert(req2.names["BLOCK"].num_mutations() == req1.names["BLOCK"].num_mutations() * 4)


########################################################################################################################
def dependencies ():
    s_initialize("DEP TEST 1")
    s_group("group", values=["1", "2"])

    if s_block_start("ONE", dep="group", dep_values=["1"]):
        s_static("ONE" * 100)
        s_block_end()

    if s_block_start("TWO", dep="group", dep_values=["2"]):
        s_static("TWO" * 100)
        s_block_end()

    assert(s_render().find("TWO") == -1)
    s_mutate()
    assert(s_render().find("ONE") == -1)


########################################################################################################################
def repeaters ():
    s_initialize("REP TEST 1")
    if s_block_start("BLOCK"):
        s_delim(">", name="delim", fuzzable=False)
        s_string("pedram", name="string", fuzzable=False)
        s_byte(0xde, name="byte", fuzzable=False)
        s_word(0xdead, name="word", fuzzable=False)
        s_dword(0xdeadbeef, name="dword", fuzzable=False)
        s_qword(0xdeadbeefdeadbeef, name="qword", fuzzable=False)
        s_random(0, 5, 10, 100, name="random", fuzzable=False)
        s_block_end()
    s_repeat("BLOCK", min_reps=5, max_reps=15, step=5)

    data   = s_render()
    length = len(data)

    s_mutate()
    data = s_render()
    assert(len(data) == length + length * 5)

    s_mutate()
    data = s_render()
    assert(len(data) == length + length * 10)

    s_mutate()
    data = s_render()
    assert(len(data) == length + length * 15)

    s_mutate()
    data = s_render()
    assert(len(data) == length)


########################################################################################################################
def return_current_mutant ():
    s_initialize("RETURN CURRENT MUTANT TEST 1")

    s_dword(0xdeadbeef, name="boss hog")
    s_string("bloodhound gang", name="vagina")

    if s_block_start("BLOCK1"):
        s_string("foo", name="foo")
        s_string("bar", name="bar")
        s_dword(0x20)
    s_block_end()

    s_dword(0xdead)
    s_dword(0x0fed)

    s_string("sucka free at 2 in morning 7/18", name="uhntiss")

    req1 = s_get("RETURN CURRENT MUTANT TEST 1")

    # calculate the length of the mutation libraries dynamically since they may change with time.
    num_str_mutations = req1.names["foo"].num_mutations()
    num_int_mutations = req1.names["boss hog"].num_mutations()

    for i in xrange(1, num_str_mutations + num_int_mutations - 10 + 1):
        req1.mutate()

    assert(req1.mutant.name == "vagina")
    req1.reset()

    for i in xrange(1, num_int_mutations + num_str_mutations + 1 + 1):
        req1.mutate()
    assert(req1.mutant.name == "foo")
    req1.reset()

    for i in xrange(num_str_mutations * 2 + num_int_mutations + 1):
        req1.mutate()
    assert(req1.mutant.name == "bar")
    req1.reset()

    for i in xrange(num_str_mutations * 3 + num_int_mutations * 4 + 1):
        req1.mutate()
    assert(req1.mutant.name == "uhntiss")
    req1.reset()


########################################################################################################################
def exhaustion ():

    s_initialize("EXHAUSTION 1")

    s_string("just wont eat", name="VIP")
    s_dword(0x4141, name="eggos_rule")
    s_dword(0x4242, name="danny_glover_is_the_man")


    req1 = s_get("EXHAUSTION 1")

    num_str_mutations = req1.names["VIP"].num_mutations()

    # if we mutate string halfway, then exhaust, then mutate one time, we should be in the 2nd primitive
    for i in xrange(num_str_mutations/2):
        req1.mutate()
    req1.mutant.exhaust()

    req1.mutate()
    assert(req1.mutant.name == "eggos_rule")
    req1.reset()

    # if we mutate through the first primitive, then exhaust the 2nd, we should be in the 3rd
    for i in xrange(num_str_mutations + 2):
        req1.mutate()
    req1.mutant.exhaust()

    req1.mutate()
    assert(req1.mutant.name == "danny_glover_is_the_man")
    req1.reset()

    # if we exhaust the first two primitives, we should be in the third
    req1.mutant.exhaust()
    req1.mutant.exhaust()
    assert(req1.mutant.name == "danny_glover_is_the_man")


########NEW FILE########
__FILENAME__ = legos
from sulley import *

def run ():
    tag()
    ndr_string()
    ber()

    # clear out the requests.
    blocks.REQUESTS = {}
    blocks.CURRENT  = None


########################################################################################################################
def tag ():
    s_initialize("UNIT TEST TAG 1")
    s_lego("tag", value="pedram")

    req = s_get("UNIT TEST TAG 1")

    print "LEGO MUTATION COUNTS:"
    print "\ttag:    %d" % req.num_mutations()


########################################################################################################################
def ndr_string ():
    s_initialize("UNIT TEST NDR 1")
    s_lego("ndr_string", value="pedram")

    req = s_get("UNIT TEST NDR 1")
    # XXX - unfinished!
    #print req.render()


########################################################################################################################
def ber ():
    s_initialize("UNIT TEST BER 1")
    s_lego("ber_string", value="pedram")
    req = s_get("UNIT TEST BER 1")
    assert(s_render() == "\x04\x84\x00\x00\x00\x06\x70\x65\x64\x72\x61\x6d")
    s_mutate()
    assert(s_render() == "\x04\x84\x00\x00\x00\x00\x70\x65\x64\x72\x61\x6d")

    s_initialize("UNIT TEST BER 2")
    s_lego("ber_integer", value=0xdeadbeef)
    req = s_get("UNIT TEST BER 2")
    assert(s_render() == "\x02\x04\xde\xad\xbe\xef")
    s_mutate()
    assert(s_render() == "\x02\x04\x00\x00\x00\x00")
    s_mutate()
    assert(s_render() == "\x02\x04\x00\x00\x00\x01")
########NEW FILE########
__FILENAME__ = primitives
from sulley import *

def run ():
    signed_tests()
    string_tests()
    fuzz_extension_tests()

    # clear out the requests.
    blocks.REQUESTS = {}
    blocks.CURRENT  = None


########################################################################################################################
def signed_tests ():
    s_initialize("UNIT TEST 1")
    s_byte(0,        format="ascii", signed=True, name="byte_1")
    s_byte(0xff/2,   format="ascii", signed=True, name="byte_2")
    s_byte(0xff/2+1, format="ascii", signed=True, name="byte_3")
    s_byte(0xff,     format="ascii", signed=True, name="byte_4")

    s_word(0,          format="ascii", signed=True, name="word_1")
    s_word(0xffff/2,   format="ascii", signed=True, name="word_2")
    s_word(0xffff/2+1, format="ascii", signed=True, name="word_3")
    s_word(0xffff,     format="ascii", signed=True, name="word_4")

    s_dword(0,              format="ascii", signed=True, name="dword_1")
    s_dword(0xffffffff/2,   format="ascii", signed=True, name="dword_2")
    s_dword(0xffffffff/2+1, format="ascii", signed=True, name="dword_3")
    s_dword(0xffffffff,     format="ascii", signed=True, name="dword_4")

    s_qword(0,                      format="ascii", signed=True, name="qword_1")
    s_qword(0xffffffffffffffff/2,   format="ascii", signed=True, name="qword_2")
    s_qword(0xffffffffffffffff/2+1, format="ascii", signed=True, name="qword_3")
    s_qword(0xffffffffffffffff,     format="ascii", signed=True, name="qword_4")

    req = s_get("UNIT TEST 1")

    assert(req.names["byte_1"].render()  == "0")
    assert(req.names["byte_2"].render()  == "127")
    assert(req.names["byte_3"].render()  == "-128")
    assert(req.names["byte_4"].render()  == "-1")
    assert(req.names["word_1"].render()  == "0")
    assert(req.names["word_2"].render()  == "32767")
    assert(req.names["word_3"].render()  == "-32768")
    assert(req.names["word_4"].render()  == "-1")
    assert(req.names["dword_1"].render() == "0")
    assert(req.names["dword_2"].render() == "2147483647")
    assert(req.names["dword_3"].render() == "-2147483648")
    assert(req.names["dword_4"].render() == "-1")
    assert(req.names["qword_1"].render() == "0")
    assert(req.names["qword_2"].render() == "9223372036854775807")
    assert(req.names["qword_3"].render() == "-9223372036854775808")
    assert(req.names["qword_4"].render() == "-1")


########################################################################################################################
def string_tests ():
    s_initialize("STRING UNIT TEST 1")
    s_string("foo", size=200, name="sized_string")

    req = s_get("STRING UNIT TEST 1")

    assert(len(req.names["sized_string"].render()) == 3)

    # check that string padding and truncation are working correctly.
    for i in xrange(0, 50):
        s_mutate()
        assert(len(req.names["sized_string"].render()) == 200)


########################################################################################################################
def fuzz_extension_tests ():
    import shutil

    # backup existing fuzz extension libraries.
    try:
        shutil.move(".fuzz_strings", ".fuzz_strings_backup")
        shutil.move(".fuzz_ints",    ".fuzz_ints_backup")
    except:
        pass

    # create extension libraries for unit test.
    fh = open(".fuzz_strings", "w+")
    fh.write("pedram\n")
    fh.write("amini\n")
    fh.close()

    fh = open(".fuzz_ints", "w+")
    fh.write("deadbeef\n")
    fh.write("0xc0cac01a\n")
    fh.close()

    s_initialize("EXTENSION TEST")

    s_string("foo", name="string")
    s_int(200,      name="int")
    s_char("A",     name="char")

    req = s_get("EXTENSION TEST")

    # these should be here now.
    assert(0xdeadbeef in req.names["int"].fuzz_library)
    assert(0xc0cac01a in req.names["int"].fuzz_library)

    # these should not as a char is too small to store them.
    assert(0xdeadbeef not in req.names["char"].fuzz_library)
    assert(0xc0cac01a not in req.names["char"].fuzz_library)

    # these should be here now.
    assert("pedram" in req.names["string"].fuzz_library)
    assert("amini" in req.names["string"].fuzz_library)

    # restore existing fuzz extension libraries.
    try:
        shutil.move(".fuzz_strings_backup", ".fuzz_strings")
        shutil.move(".fuzz_ints_backup",    ".fuzz_ints")
    except:
        pass
########NEW FILE########
__FILENAME__ = crashbin_explorer
#!c:\\python\\python.exe

import getopt
import sys
sys.path.append(r"../../../paimei")

import utils
import pgraph

USAGE = "\nUSAGE: crashbin_explorer.py <xxx.crashbin>"                                      \
        "\n    [-t|--test #]     dump the crash synopsis for a specific test case number"   \
        "\n    [-g|--graph name] generate a graph of all crash paths, save to 'name'.udg\n"

#
# parse command line options.
#

try:
    if len(sys.argv) < 2:
        raise Exception

    opts, args = getopt.getopt(sys.argv[2:], "t:g:", ["test=", "graph="])
except:
    print USAGE
    sys.exit(1)

test_number = graph_name = graph = None

for opt, arg in opts:
    if opt in ("-t", "--test"):  test_number = int(arg)
    if opt in ("-g", "--graph"): graph_name  = arg

try:
    crashbin = utils.crash_binning.crash_binning()
    crashbin.import_file(sys.argv[1])
except:
    print "unable to open crashbin: '%s'." % sys.argv[1]
    sys.exit(1)

#
# display the full crash dump of a specific test case
#

if test_number:
    for bin, crashes in crashbin.bins.iteritems():
        for crash in crashes:
            if test_number == crash.extra:
                print crashbin.crash_synopsis(crash)
                sys.exit(0)

#
# display an overview of all recorded crashes.
#

if graph_name:
    graph = pgraph.graph()

for bin, crashes in crashbin.bins.iteritems():
    synopsis = crashbin.crash_synopsis(crashes[0]).split("\n")[0]

    if graph:
        crash_node       = pgraph.node(crashes[0].exception_address)
        crash_node.count = len(crashes)
        crash_node.label = "[%d] %s.%08x" % (crash_node.count, crashes[0].exception_module, crash_node.id)
        graph.add_node(crash_node)

    print "[%d] %s" % (len(crashes), synopsis)
    print "\t",

    for crash in crashes:
        if graph:
            last = crash_node.id
            for entry in crash.stack_unwind:
                address = long(entry.split(":")[1], 16)
                n = graph.find_node("id", address)

                if not n:
                    n       = pgraph.node(address)
                    n.count = 1
                    n.label = "[%d] %s" % (n.count, entry)
                    graph.add_node(n)
                else:
                    n.count += 1
                    n.label = "[%d] %s" % (n.count, entry)

                edge = pgraph.edge(n.id, last)
                graph.add_edge(edge)
                last = n.id
        print "%d," % crash.extra,

    print "\n"

if graph:
    fh = open("%s.udg" % graph_name, "w+")
    fh.write(graph.render_graph_udraw())
    fh.close()
########NEW FILE########
__FILENAME__ = crash_binning
#
# Crash Binning
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: crash_binning.py 193 2007-04-05 13:30:01Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import sys
import zlib
import cPickle

class __crash_bin_struct__:
    exception_module    = None
    exception_address   = 0
    write_violation     = 0
    violation_address   = 0
    violation_thread_id = 0
    context             = None
    context_dump        = None
    disasm              = None
    disasm_around       = []
    stack_unwind        = []
    seh_unwind          = []
    extra               = None


class crash_binning:
    '''
    @todo: Add MySQL import/export.
    '''

    bins       = {}
    last_crash = None
    pydbg      = None

    ####################################################################################################################
    def __init__ (self):
        '''
        '''

        self.bins       = {}
        self.last_crash = None
        self.pydbg      = None


    ####################################################################################################################
    def record_crash (self, pydbg, extra=None):
        '''
        Given a PyDbg instantiation that at the current time is assumed to have "crashed" (access violation for example)
        record various details such as the disassemly around the violating address, the ID of the offending thread, the
        call stack and the SEH unwind. Store the recorded data in an internal dictionary, binning them by the exception
        address.

        @type  pydbg: pydbg
        @param pydbg: Instance of pydbg
        @type  extra: Mixed
        @param extra: (Optional, Def=None) Whatever extra data you want to store with this bin
        '''

        self.pydbg = pydbg
        crash = __crash_bin_struct__()

        # add module name to the exception address.
        exception_module = pydbg.addr_to_module(pydbg.dbg.u.Exception.ExceptionRecord.ExceptionAddress)

        if exception_module:
            exception_module = exception_module.szModule
        else:
            exception_module = "[INVALID]"

        crash.exception_module    = exception_module
        crash.exception_address   = pydbg.dbg.u.Exception.ExceptionRecord.ExceptionAddress
        crash.write_violation     = pydbg.dbg.u.Exception.ExceptionRecord.ExceptionInformation[0]
        crash.violation_address   = pydbg.dbg.u.Exception.ExceptionRecord.ExceptionInformation[1]
        crash.violation_thread_id = pydbg.dbg.dwThreadId
        crash.context             = pydbg.context
        crash.context_dump        = pydbg.dump_context(pydbg.context, print_dots=False)
        crash.disasm              = pydbg.disasm(crash.exception_address)
        crash.disasm_around       = pydbg.disasm_around(crash.exception_address, 10)
        crash.stack_unwind        = pydbg.stack_unwind()
        crash.seh_unwind          = pydbg.seh_unwind()
        crash.extra               = extra

        # add module names to the stack unwind.
        for i in xrange(len(crash.stack_unwind)):
            addr   = crash.stack_unwind[i]
            module = pydbg.addr_to_module(addr)

            if module:
                module = module.szModule
            else:
                module = "[INVALID]"

            crash.stack_unwind[i] = "%s:%08x" % (module, addr)


        # add module names to the SEH unwind.
        for i in xrange(len(crash.seh_unwind)):
            (addr, handler) = crash.seh_unwind[i]

            module = pydbg.addr_to_module(handler)

            if module:
                module = module.szModule
            else:
                module = "[INVALID]"

            crash.seh_unwind[i] = (addr, handler, "%s:%08x" % (module, handler))

        if not self.bins.has_key(crash.exception_address):
            self.bins[crash.exception_address] = []

        self.bins[crash.exception_address].append(crash)
        self.last_crash = crash


    ####################################################################################################################
    def crash_synopsis (self, crash=None):
        '''
        For the supplied crash, generate and return a report containing the disassemly around the violating address,
        the ID of the offending thread, the call stack and the SEH unwind. If not crash is specified, then call through
        to last_crash_synopsis() which returns the same information for the last recorded crash.

        @see: crash_synopsis()

        @type  crash: __crash_bin_struct__
        @param crash: (Optional, def=None) Crash object to generate report on

        @rtype:  String
        @return: Crash report
        '''

        if not crash:
            return self.last_crash_synopsis()

        if crash.write_violation:
            direction = "write to"
        else:
            direction = "read from"

        synopsis = "%s:%08x %s from thread %d caused access violation\nwhen attempting to %s 0x%08x\n\n" % \
            (
                crash.exception_module,       \
                crash.exception_address,      \
                crash.disasm,                 \
                crash.violation_thread_id,    \
                direction,                    \
                crash.violation_address       \
            )

        synopsis += crash.context_dump

        synopsis += "\ndisasm around:\n"
        for (ea, inst) in crash.disasm_around:
            synopsis += "\t0x%08x %s\n" % (ea, inst)

        if len(crash.stack_unwind):
            synopsis += "\nstack unwind:\n"
            for entry in crash.stack_unwind:
                synopsis += "\t%s\n" % entry

        if len(crash.seh_unwind):
            synopsis += "\nSEH unwind:\n"
            for (addr, handler, handler_str) in crash.seh_unwind:
                synopsis +=  "\t%08x -> %s\n" % (addr, handler_str)

        return synopsis + "\n"


    ####################################################################################################################
    def export_file (self, file_name):
        '''
        Dump the entire object structure to disk.

        @see: import_file()

        @type  file_name:   String
        @param file_name:   File name to export to

        @rtype:             crash_binning
        @return:            self
        '''

        # null out what we don't serialize but save copies to restore after dumping to disk.
        last_crash = self.last_crash
        pydbg      = self.pydbg

        self.last_crash = self.pydbg = None

        fh = open(file_name, "wb+")
        fh.write(zlib.compress(cPickle.dumps(self, protocol=2)))
        fh.close()

        self.last_crash = last_crash
        self.pydbg      = pydbg

        return self


    ####################################################################################################################
    def import_file (self, file_name):
        '''
        Load the entire object structure from disk.

        @see: export_file()

        @type  file_name:   String
        @param file_name:   File name to import from

        @rtype:             crash_binning
        @return:            self
        '''

        fh  = open(file_name, "rb")
        tmp = cPickle.loads(zlib.decompress(fh.read()))
        fh.close()

        self.bins = tmp.bins

        return self


    ####################################################################################################################
    def last_crash_synopsis (self):
        '''
        For the last recorded crash, generate and return a report containing the disassemly around the violating
        address, the ID of the offending thread, the call stack and the SEH unwind.

        @see: crash_synopsis()

        @rtype:  String
        @return: Crash report
        '''

        if self.last_crash.write_violation:
            direction = "write to"
        else:
            direction = "read from"

        synopsis = "%s:%08x %s from thread %d caused access violation\nwhen attempting to %s 0x%08x\n\n" % \
            (
                self.last_crash.exception_module,       \
                self.last_crash.exception_address,      \
                self.last_crash.disasm,                 \
                self.last_crash.violation_thread_id,    \
                direction,                              \
                self.last_crash.violation_address       \
            )

        synopsis += self.last_crash.context_dump

        synopsis += "\ndisasm around:\n"
        for (ea, inst) in self.last_crash.disasm_around:
            synopsis += "\t0x%08x %s\n" % (ea, inst)

        if len(self.last_crash.stack_unwind):
            synopsis += "\nstack unwind:\n"
            for entry in self.last_crash.stack_unwind:
                synopsis += "\t%s\n" % entry

        if len(self.last_crash.seh_unwind):
            synopsis += "\nSEH unwind:\n"
            for (addr, handler, handler_str) in self.last_crash.seh_unwind:
                try:
                    disasm = self.pydbg.disasm(handler)
                except:
                    disasm = "[INVALID]"

                synopsis +=  "\t%08x -> %s %s\n" % (addr, handler_str, disasm)

        return synopsis + "\n"
########NEW FILE########
__FILENAME__ = ida_fuzz_library_extender
#!c:\python\python.exe
#
# Aaron Portnoy
# TippingPoint Security Research Team
# (C) 2007
#

########################################################################################################################
def get_string( ea):
    str_type = GetStringType(ea)

    if str_type == 0:
        string_buf = ""
        while Byte(ea) != 0x00:
            string_buf += "%c" % Byte(ea)
            ea += 1
        return string_buf
    elif str_type == 3:
        string_buf = ""
        while Word(ea) != 0x0000:
            string_buf += "%c%c" % (Byte(ea), Byte(ea+1))
            ea += 2
        return string_buf
    else:
        pass


########################################################################################################################
def get_arguments(ea):
    xref_ea = ea
    args    = 0
    found   = None

    if GetMnem(xref_ea) != "call":
        return False

    cur_ea = PrevHead(ea, xref_ea - 32)
    while (cur_ea < xref_ea - 32) or (args <= 6):
        cur_mnem = GetMnem(cur_ea);
        if cur_mnem == "push":
            args += 1
            op_type = GetOpType(cur_ea, 0)

            if Comment(cur_ea):
                pass
                #print(" %s = %s," % (Comment(cur_ea), GetOpnd(cur_ea, 0)))
            else:
                if op_type == 1:
                    pass
                    #print(" %s" % GetOpnd(cur_ea, 0))
                elif op_type == 5:
                    found = get_string(GetOperandValue(cur_ea, 0))

        elif cur_mnem == "call" or "j" in cur_mnem:
            break;

        cur_ea = PrevHead(cur_ea, xref_ea - 32)

    if found: return found


########################################################################################################################
def find_ints (start_address):
    constants     = []

    # loop heads
    for head in Heads(start_address, SegEnd(start_address)):

        # if it's code, check for cmp instruction
        if isCode(GetFlags(head)):
            mnem = GetMnem(head)
            op1 = int(GetOperandValue(head, 1))

            # if it's a cmp and it's immediate value is unique, add it to the list
            if "cmp" in mnem and op1 not in constants:
                constants.append(op1)

    print "Found %d constant values used in compares." % len(constants)
    print "-----------------------------------------------------"
    for i in xrange(0, len(constants), 20):
        print constants[i:i+20]

    return constants


########################################################################################################################
def find_strings (start_address):
    strings    = []
    string_arg = None

    # do import checking
    import_ea = start_address

    while import_ea < SegEnd(start_address):
        import_name = Name(import_ea)

        if len(import_name) > 1 and "cmp" in import_name:
            xref_start = import_ea
            xref_cur   = DfirstB(xref_start)
            while xref_cur != BADADDR:

                #print "Found call to ", import_name
                string_arg = get_arguments(xref_cur)        
                
                if string_arg and string_arg not in strings:
                    strings.append(string_arg)

                xref_cur = DnextB(xref_start, xref_cur)

        import_ea += 4


    # now do FLIRT checking
    for function_ea in Functions(SegByName(".text"), SegEnd(start_address)):
        flags = GetFunctionFlags(function_ea)

        if flags & FUNC_LIB:
            lib_name = GetFunctionName(function_ea)

            if len(lib_name) > 1 and "cmp" in lib_name:

                # found one, now find xrefs to it and grab arguments
                xref_start = function_ea
                xref_cur   = RfirstB(xref_start)

                while xref_cur != BADADDR:
                    string_arg = get_arguments(xref_cur)

                    if string_arg and string_arg not in strings:
                        strings.append(string_arg)

                    xref_cur = RnextB(xref_start, xref_cur)

    print "Found %d string values used in compares." % len(strings)
    print "-----------------------------------------------------"
    for i in xrange(0, len(strings), 5):
        print strings[i:i+5]

    return strings


########################################################################################################################

# get file names to save to
constants_file = AskFile(1, ".fuzz_ints", "Enter filename for saving the discovered integers: ")
strings_file   = AskFile(1, ".fuzz_strings", "Enter filename for saving the discovered strings: ")

# get integers
start_address = SegByName(".text")
constants = find_ints(start_address)
constants = map(lambda x: "0x%x" % x, constants)

print

# get strings
start_address = SegByName(".idata")
strings = find_strings(start_address)

# write integers
fh = open(constants_file, 'w+')
for c in constants:
    fh.write(c + "\n")
fh.close()

# write strings
fh = open(strings_file, 'w+')
for s in strings:
    fh.write(s + "\n")
fh.close()

print "Done."

########NEW FILE########
__FILENAME__ = pcap_cleaner
#!c:\\python\\python.exe

import os
import sys
sys.path.append(r"..\..\..\paimei")

import utils

USAGE = "\nUSAGE: pcap_cleaner.py <xxx.crashbin> <path to pcaps>\n"

if len(sys.argv) != 3:
    print USAGE
    sys.exit(1)


#
# generate a list of all test cases that triggered a crash.
#

try:
    crashbin = utils.crash_binning.crash_binning()
    crashbin.import_file(sys.argv[1])
except:
    print "unable to open crashbin: '%s'." % sys.argv[1]
    sys.exit(1)

test_cases = []
for bin, crashes in crashbin.bins.iteritems():
    for crash in crashes:
        test_cases.append("%d.pcap" % crash.extra)

#
# step through the pcap directory and erase all files not pertaining to a crash.
#

for filename in os.listdir(sys.argv[2]):
    if filename not in test_cases:
        os.unlink("%s/%s" % (sys.argv[2], filename))

########NEW FILE########
__FILENAME__ = pdml_parser
#!c:\python\python.exe

import sys

from xml.sax import make_parser
from xml.sax import ContentHandler
from xml.sax.handler import feature_namespaces


########################################################################################################################
class ParsePDML (ContentHandler):
    
    def __init__ (self):
        self.current       = None
        self.start_parsing = False
        self.sulley        = ""
    
    
    def startElement (self, name, attributes):
        if name == "proto":
            self.current = attributes["name"]
            
        # if parsing flag is set, we're past tcp
        if self.start_parsing:
            
            if not name == "field":
                print "Found payload with name %s" % attributes["name"]
            elif name == "field":
                if "value" in attributes.keys():
                    val_string = self.get_string(attributes["value"])
                    
                    if val_string:
                        self.sulley += "s_string(\"%s\")\n" % (val_string)
                        print self.sulley
                        #print "\tFound value: %s" % val_string
                    else:
                        # not string
                        pass
            else:
                raise "WTFException"
        
        
    def characters (self, data):
        pass
        
        
    def endElement (self, name):
        # if we're closing a packet
        if name == "packet":
            self.start_parsing = False
        
        # if we're closing a proto tag
        if name == "proto":
            # and that proto is tcp, set parsing flag
            if self.current == "tcp":
                #print "Setting parsing flag to TRUE"
                self.start_parsing = True
    
            else:
                self.start_parsing = False
    
    
    def get_string(self, parsed):
        
        parsed = parsed.replace("\t",  "")
        parsed = parsed.replace("\r",  "")
        parsed = parsed.replace("\n",  "")
        parsed = parsed.replace(",",   "")
        parsed = parsed.replace("0x",  "")
        parsed = parsed.replace("\\x", "")
        
        value = ""
        while parsed:
            pair   = parsed[:2]
            parsed = parsed[2:]
            
            hex = int(pair, 16)
            if hex > 0x7f:
                return False
                
            value += chr(hex)
        
        
        value = value.replace("\t",  "")
        value = value.replace("\r",  "")
        value = value.replace("\n",  "")
        value = value.replace(",",   "")
        value = value.replace("0x",  "")
        value = value.replace("\\x", "")
        
        return value
    
    def error (self, exception):
        print "Oh shitz: ", exception
        sys.exit(1)

########################################################################################################################
if __name__ == '__main__':

    # create the parser object
    parser = make_parser()
    
    # dont care about xml namespace
    parser.setFeature(feature_namespaces, 0)

    # make the document handler
    handler = ParsePDML()
    
    # point parser to handler
    parser.setContentHandler(handler)

    # parse 
    parser.parse(sys.argv[1])



########NEW FILE########
__FILENAME__ = print_session
#! /usr/bin/python

import os
import sys
import zlib
import cPickle

USAGE = "\nUSAGE: print_session.py <session file>\n"

if len(sys.argv) != 2:
    print USAGE
    sys.exit(1)

fh = open(sys.argv[1], "rb")
data = cPickle.loads(zlib.decompress(fh.read()))
fh.close()


#print data
for key in data.keys():
    print key + " -> " + str(data[key])


########NEW FILE########
__FILENAME__ = vmcontrol
#!/usr/bin/python
#!c:\\python\\python.exe

import os
import sys
import time
import getopt

try:
    from win32api import GetShortPathName
    from win32com.shell import shell
except:
    if os.name == "nt":
        print "[!] Failed to import win32api/win32com modules, please install these! Bailing..."
        sys.exit(1)


from sulley import pedrpc

PORT  = 26003
ERR   = lambda msg: sys.stderr.write("ERR> " + msg + "\n") or sys.exit(1)
USAGE = "USAGE: vmcontrol.py"                                                             \
        "\n    <-x|--vmx FILENAME|NAME> path to VMX to control or name of VirtualBox image" \
        "\n    <-r|--vmrun FILENAME>    path to vmrun.exe or VBoxManage"                    \
        "\n    [-s|--snapshot NAME>     set the snapshot name"                              \
        "\n    [-l|--log_level LEVEL]   log level (default 1), increase for more verbosity" \
        "\n    [-i|--interactive]       Interactive mode, prompts for input values"         \
        "\n    [--port PORT]            TCP port to bind this agent to"                      \
        "\n    [--vbox]                 control an Oracle VirtualBox VM"

########################################################################################################################
class vmcontrol_pedrpc_server (pedrpc.server):
    def __init__ (self, host, port, vmrun, vmx, snap_name=None, log_level=1, interactive=False):
        '''
        @type  host:         String
        @param host:         Hostname or IP address to bind server to
        @type  port:         Integer
        @param port:         Port to bind server to
        @type  vmrun:        String
        @param vmrun:        Path to VMWare vmrun.exe
        @type  vmx:          String
        @param vmx:          Path to VMX file
        @type  snap_name:    String
        @param snap_name:    (Optional, def=None) Snapshot name to revert to on restart
        @type  log_level:    Integer
        @param log_level:    (Optional, def=1) Log output level, increase for more verbosity
        @type  interactive:  Boolean
        @param interactive:  (Option, def=False) Interactive mode, prompts for input values
        '''

        # initialize the PED-RPC server.
        pedrpc.server.__init__(self, host, port)

        self.host        = host
        self.port        = port

        self.interactive = interactive

        if interactive:
            print "[*] Entering interactive mode..."

            # get vmrun path
            try:
                while 1:
                    print "[*] Please browse to the folder containing vmrun.exe..."
                    pidl, disp, imglist = shell.SHBrowseForFolder(0, None, "Please browse to the folder containing vmrun.exe:")
                    fullpath = shell.SHGetPathFromIDList(pidl)
                    file_list = os.listdir(fullpath)
                    if "vmrun.exe" not in file_list:
                        print "[!] vmrun.exe not found in selected folder, please try again"
                    else:
                        vmrun = fullpath + "\\vmrun.exe"
                        print "[*] Using %s" % vmrun
                        break
            except:
                print "[!] Error while trying to find vmrun.exe. Try again without -I."
                sys.exit(1)

            # get vmx path
            try:
                while 1:
                    print "[*] Please browse to the folder containing the .vmx file..."
                    pidl, disp, imglist = shell.SHBrowseForFolder(0, None, "Please browse to the folder containing the .vmx file:")
                    fullpath = shell.SHGetPathFromIDList(pidl)
                    file_list = os.listdir(fullpath)

                    exists = False
                    for file in file_list:
                        idx = file.find(".vmx")
                        if idx == len(file) - 4:
                            exists = True
                            vmx = fullpath + "\\" + file
                            print "[*] Using %s" % vmx

                    if exists:
                        break
                    else:
                        print "[!] No .vmx file found in the selected folder, please try again"
            except:
                raise
                print "[!] Error while trying to find the .vmx file. Try again without -I."
                sys.exit(1)

        # Grab snapshot name and log level if we're in interactive mode
        if interactive:
            snap_name = raw_input("[*] Please enter the snapshot name: ")
            log_level = raw_input("[*] Please enter the log level (default 1): ")

            if log_level:
                log_level = int(log_level)
            else:
                log_level = 1

        # if we're on windows, get the DOS path names
        if os.name == "nt":
            self.vmrun = GetShortPathName(r"%s" % vmrun)
            self.vmx   = GetShortPathName(r"%s" % vmx)
        else:
            self.vmrun = vmrun
            self.vmx   = vmx

        self.snap_name   = snap_name
        self.log_level   = log_level
        self.interactive = interactive

        self.log("VMControl PED-RPC server initialized:")
        self.log("\t vmrun:     %s" % self.vmrun)
        self.log("\t vmx:       %s" % self.vmx)
        self.log("\t snap name: %s" % self.snap_name)
        self.log("\t log level: %d" % self.log_level)
        self.log("Awaiting requests...")


    def alive (self):
        '''
        Returns True. Useful for PED-RPC clients who want to see if the PED-RPC connection is still alive.
        '''

        return True


    def log (self, msg="", level=1):
        '''
        If the supplied message falls under the current log level, print the specified message to screen.

        @type  msg: String
        @param msg: Message to log
        '''

        if self.log_level >= level:
            print "[%s] %s" % (time.strftime("%I:%M.%S"), msg)


    def set_vmrun (self, vmrun):
        self.log("setting vmrun to %s" % vmrun, 2)
        self.vmrun = vmrun


    def set_vmx (self, vmx):
        self.log("setting vmx to %s" % vmx, 2)
        self.vmx = vmx


    def set_snap_name (self, snap_name):
        self.log("setting snap_name to %s" % snap_name, 2)
        self.snap_name = snap_name


    def vmcommand (self, command):
        '''
        Execute the specified command, keep trying in the event of a failure.

        @type  command: String
        @param command: VMRun command to execute
        '''

        while 1:
            self.log("executing: %s" % command, 5)

            pipe = os.popen(command)
            out  = pipe.readlines()

            try:
                pipe.close()
            except IOError:
                self.log("IOError trying to close pipe")

            if not out:
                break
            elif not out[0].lower().startswith("close failed"):
                break

            self.log("failed executing command '%s' (%s). will try again." % (command, out))
            time.sleep(1)

        return "".join(out)


    ###
    ### VMRUN COMMAND WRAPPERS
    ###


    def delete_snapshot (self, snap_name=None):
        if not snap_name:
            snap_name = self.snap_name

        self.log("deleting snapshot: %s" % snap_name, 2)

        command = self.vmrun + " deleteSnapshot " + self.vmx + " " + '"' + snap_name + '"'
        return self.vmcommand(command)


    def list (self):
        self.log("listing running images", 2)

        command = self.vmrun + " list"
        return self.vmcommand(command)


    def list_snapshots (self):
        self.log("listing snapshots", 2)

        command = self.vmrun + " listSnapshots " + self.vmx
        return self.vmcommand(command)


    def reset (self):
        self.log("resetting image", 2)

        command = self.vmrun + " reset " + self.vmx
        return self.vmcommand(command)


    def revert_to_snapshot (self, snap_name=None):
        if not snap_name:
            snap_name = self.snap_name

        self.log("reverting to snapshot: %s" % snap_name, 2)

        command = self.vmrun + " revertToSnapshot " + self.vmx + " " + '"' + snap_name + '"'
        return self.vmcommand(command)


    def snapshot (self, snap_name=None):
        if not snap_name:
            snap_name = self.snap_name

        self.log("taking snapshot: %s" % snap_name, 2)

        command = self.vmrun + " snapshot " + self.vmx + " " + '"' + snap_name + '"'

        return self.vmcommand(command)


    def start (self):
        self.log("starting image", 2)

        command = self.vmrun + " start " + self.vmx
        return self.vmcommand(command)


    def stop (self):
        self.log("stopping image", 2)

        command = self.vmrun + " stop " + self.vmx
        return self.vmcommand(command)


    def suspend (self):
        self.log("suspending image", 2)

        command = self.vmrun + " suspend " + self.vmx
        return self.vmcommand(command)


    ###
    ### EXTENDED COMMANDS
    ###


    def restart_target (self):
        self.log("restarting virtual machine...")

        # revert to the specified snapshot and start the image.
        self.revert_to_snapshot()
        self.start()

        # wait for the snapshot to come alive.
        self.wait()


    def is_target_running (self):
        # sometimes vmrun reports that the VM is up while it's still reverting.
        time.sleep(10)

        for line in self.list().lower().split('\n'):
            if os.name == "nt":
                try:
                    line = GetShortPathName(line)
                # skip invalid paths.
                except:
                    continue

            if self.vmx.lower() == line.lower():
                return True

        return False


    def wait (self):
        self.log("waiting for vmx to come up: %s" % self.vmx)
        while 1:
            if self.is_target_running():
                break


########################################################################################################################

########################################################################################################################
class vboxcontrol_pedrpc_server (vmcontrol_pedrpc_server):
    def __init__ (self, host, port, vmrun, vmx, snap_name=None, log_level=1, interactive=False):
        '''
        Controls an Oracle VirtualBox Virtual Machine
        
        @type  host:         String
        @param host:         Hostname or IP address to bind server to
        @type  port:         Integer
        @param port:         Port to bind server to
        @type  vmrun:        String
        @param vmrun:        Path to VBoxManage
        @type  vmx:          String
        @param vmx:          Name of the virtualbox VM to control (no quotes)
        @type  snap_name:    String
        @param snap_name:    (Optional, def=None) Snapshot name to revert to on restart
        @type  log_level:    Integer
        @param log_level:    (Optional, def=1) Log output level, increase for more verbosity
        @type  interactive:  Boolean
        @param interactive:  (Option, def=False) Interactive mode, prompts for input values
        '''

        # initialize the PED-RPC server.
        pedrpc.server.__init__(self, host, port)

        self.host        = host
        self.port        = port

        self.interactive = interactive
 

    
        if interactive:
            print "[*] Entering interactive mode..."

            # get vmrun path
            try:
                while 1:
                    print "[*] Please browse to the folder containing VBoxManage.exe..."
                    pidl, disp, imglist = shell.SHBrowseForFolder(0, None, "Please browse to the folder containing VBoxManage.exe")
                    fullpath = shell.SHGetPathFromIDList(pidl)
                    file_list = os.listdir(fullpath)
                    if "VBoxManage.exe" not in file_list:
                        print "[!] VBoxManage.exe not found in selected folder, please try again"
                    else:
                        vmrun = fullpath + "\\VBoxManage.exe"
                        print "[*] Using %s" % vmrun
                        break
            except:
                print "[!] Error while trying to find VBoxManage.exe. Try again without -I."
                sys.exit(1)



        # Grab vmx, snapshot name and log level if we're in interactive mode

        if interactive:
            vmx = raw_input("[*] Please enter the VirtualBox virtual machine name: ")
            snap_name = raw_input("[*] Please enter the snapshot name: ")
            log_level = raw_input("[*] Please enter the log level (default 1): ")
    

        if log_level:
            log_level = int(log_level)
        else:
            log_level = 1


        # if we're on windows, get the DOS path names

        if os.name == "nt":
            self.vmrun = GetShortPathName(r"%s" % vmrun)
            self.vmx   = GetShortPathName(r"%s" % vmx)
        else:
    
            self.vmrun = vmrun
            self.vmx   = vmx

        self.snap_name   = snap_name
        self.log_level   = log_level
        self.interactive = interactive

        self.log("VirtualBox PED-RPC server initialized:")
        self.log("\t vboxmanage:     %s" % self.vmrun)
        self.log("\t machine name:       %s" % self.vmx)
        self.log("\t snap name: %s" % self.snap_name)
        self.log("\t log level: %d" % self.log_level)
        self.log("Awaiting requests...")

    ###
    ### VBOXMANAGE COMMAND WRAPPERS
    ###


    def delete_snapshot (self, snap_name=None):
        if not snap_name:
            snap_name = self.snap_name

        self.log("deleting snapshot: %s" % snap_name, 2)

        command = self.vmrun + " snapshot " + self.vmx + " delete " + snap_name + '"'
        return self.vmcommand(command)


    def list (self):
        self.log("listing running images", 2)

        command = self.vmrun + " list runningvms"
        return self.vmcommand(command)


    def list_snapshots (self):
        self.log("listing snapshots", 2)

        command = self.vmrun + " snapshot " + self.vmx + " list"
        return self.vmcommand(command)


    def reset (self):
        self.log("resetting image", 2)

        command = self.vmrun + " controlvm " + self.vmx + " reset"
        return self.vmcommand(command)

    def pause (self):
        self.log("pausing image", 2)

        command = self.vmrun + " controlvm " + self.vmx + " pause"
        return self.vmcommand(command)
    
    def resume (self):
        self.log("resuming image", 2)

        command = self.vmrun + " controlvm " + self.vmx + " resume"
        return self.vmcommand(command)

    def revert_to_snapshot (self, snap_name=None):
        if not snap_name:
            snap_name = self.snap_name

        #VirtualBox flips out if you try to do this with a running VM
        if self.is_target_running():
            self.stop()



        self.log("reverting to snapshot: %s" % snap_name, 2)

        command = self.vmrun + " snapshot " + self.vmx + " restore " + snap_name 
        return self.vmcommand(command)


    def snapshot (self, snap_name=None):
        if not snap_name:
            snap_name = self.snap_name

        #VirtualBox flips out if you try to do this with a running VM
        if self.is_target_running():
               self.pause()


        self.log("taking snapshot: %s" % snap_name, 2)

        command = self.vmrun + " snapshot " + self.vmx + " take " + snap_name

        return self.vmcommand(command)


    def start (self):
        self.log("starting image", 2)

        command = self.vmrun + " startvm " + self.vmx 
        # XXX we may want to do more here with headless, gui, etc...
        return self.vmcommand(command)


    def stop (self):
        self.log("stopping image", 2)

        command = self.vmrun + " controlvm " + self.vmx + " poweroff"
        return self.vmcommand(command)


    def suspend (self):
        self.log("suspending image", 2)

        command = self.vmrun + " controlvm " + self.vmx + " pause"
        return self.vmcommand(command)


    ###
    ### EXTENDED COMMANDS
    ###

#added a function here to get vminfo... useful for parsing stuff out later
    def get_vminfo(self):

           self.log("getting vminfo", 2)

           command = self.vmrun + " showvminfo " + self.vmx + " --machinereadable"
           return self.vmcommand(command)


    def restart_target (self):
        self.log("restarting virtual machine...")
    
        #VirtualBox flips out if you try to do this with a running VM
        if self.is_target_running():
            self.stop()

        # revert to the specified snapshot and start the image.
        self.revert_to_snapshot()
        self.start()

        # wait for the snapshot to come alive.
        self.wait()


    def is_target_running (self):
        # sometimes vmrun reports that the VM is up while it's still reverting.
        time.sleep(10)

        for line in self.get_vminfo().split('\n'):
            if line == 'VMState="running"':
                return True

        return False
    
    def is_target_paused (self):
        time.sleep(10)
        
        for line in self.get_vminfo().split('\n'):
            if line == 'VMState="paused"':
                return True

        return False


########################################################################################################################

if __name__ == "__main__":
    # parse command line options.
    try:
        opts, args = getopt.getopt(sys.argv[1:], "x:r:s:l:i", ["vmx=", "vmrun=", "snapshot=", "log_level=", "interactive", "port=", "vbox"])
    except getopt.GetoptError:
        ERR(USAGE)

    vmrun       = r"C:\progra~1\vmware\vmware~1\vmrun.exe"
    vmx         = None
    snap_name   = None
    log_level   = 1
    interactive = False
    virtualbox  = False
    
    for opt, arg in opts:
        if opt in ("-x", "--vmx"):         vmx         = arg
        if opt in ("-r", "--vmrun"):       vmrun       = arg
        if opt in ("-s", "--snapshot"):    snap_name   = arg
        if opt in ("-l", "--log_level"):   log_level   = int(arg)
        if opt in ("-i", "--interactive"): interactive = True
        if opt in ("--port"):              PORT        = int(arg)
        if opt in ("--vbox"):              virtualbox  = True
        
    # OS check
    if interactive and not os.name == "nt":
        print "[!] Interactive mode currently only works on Windows operating systems."
        ERR(USAGE)

    if not vmx and not interactive:
        ERR(USAGE)
    
    if not virtualbox:
        servlet = vmcontrol_pedrpc_server("0.0.0.0", PORT, vmrun, vmx, snap_name, log_level, interactive)
    elif virtualbox:
        servlet = vboxcontrol_pedrpc_server("0.0.0.0", PORT, vmrun, vmx, snap_name, log_level, interactive)
    
    servlet.serve_forever()

########NEW FILE########
