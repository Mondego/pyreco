__FILENAME__ = const
DHOSTS = ['156.154.70.1', # remote dns server address list
         '8.8.8.8',
         '8.8.4.4',
         '156.154.71.1',
         #'208.67.222.222',
         #'208.67.220.220',
         #'198.153.192.1',
         #'198.153.194.1',
         #'74.207.247.4',
         #'209.244.0.3',
         #'8.26.56.26'
         ]
DPORT = 53                # default dns port 53
TIMEOUT = 20              # set timeout 5 second

fakeip = {
    "4.36.66.178" ,
    "8.7.198.45" ,
    "37.61.54.158" ,
    "46.82.174.68" ,
    "59.24.3.173" ,
    "64.33.88.161" ,
    "64.33.99.47" ,
    "64.66.163.251" ,
    "65.104.202.252" ,
    "65.160.219.113" ,
    "66.45.252.237" ,
    "72.14.205.104" ,
    "72.14.205.99" ,
    "78.16.49.15" ,
    "93.46.8.89" ,
    "128.121.126.139" ,
    "159.106.121.75" ,
    "169.132.13.103" ,
    "192.67.198.6" ,
    "202.106.1.2" ,
    "202.181.7.85" ,
    "203.161.230.171" ,
    "207.12.88.98" ,
    "208.56.31.43" ,
    "209.145.54.50" ,
    "209.220.30.174" ,
    "209.36.73.33" ,
    "211.94.66.147" ,
    "213.169.251.35" ,
#THIS PART MAY BE NOT RIGHT
    "216.221.188.182",
    "216.234.179.13",
    "243.185.187.39"
}

########NEW FILE########
__FILENAME__ = daemon
# -*- coding: utf-8 -*-
# FileName: PureDNSDeamon.py
# Author  : xiaoyao9933
# Email   : me@chao.lu
# Date    : 2013-02-15
# Vesion  : 1.0
'''
Name was changed to: daemon.py
Last updated: 2013-02-28
Updated by  : Ming
'''
import sys, os, time, atexit, signal
import threading
from subprocess import Popen
try:
    from signal import SIGTERM, SIGQUIT,SIGINT,SIGKILL
except:
    pass
class Daemon:
    """
    A generic daemon class.
    
    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile = '/tmp/test.pid', stdin = '/dev/null', stdout = '/dev/null', stderr = '/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced 
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
       # os.chdir("~/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'w')
        se = file(self.stderr, 'w', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile, 'w+').write("%s\n" % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def getstate(self):
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        if pid:
            return True
        else:
            return False
    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "Daemon is already running\n"
            sys.stderr.write(message)
            sys.exit(1)

        # Start the daemon
        sys.stdout.write('Start Success\n')
        self.daemonize()
        signal.signal(signal.SIGQUIT, self.terminate)
        #signal.signal(signal.SIGKILL, self.terminate)
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "Daemon is not running\n"
            sys.stderr.write(message)
            return # not an error in a restart
        # Try killing the daemon process    
        try:
            while True:
                os.kill(pid, SIGQUIT)
                sys.stdout.write('Stop Success\n')
                time.sleep(1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)
                
    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    '''
    def run(self):
        self.run = True
        signal.signal(signal.SIGQUIT, self.terminate)
        #signal.signal(signal.SIGKILL, self.terminate)
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)
        self.dnscfg=DNSCfg.DNSCfg()
        self.tcpdns=tcpdns.tcpdns()
        self.tcpdns.start()
        self.dnscfg.ModifyDns('127.0.0.1')
        while self.run:
            time.sleep(1)
    def terminate(self, signal, param):
        self.run = False
        self.tcpdns.force_close()
        self.dnscfg.RestoreDns()
        os._exit(0)
    '''

########NEW FILE########
__FILENAME__ = darwin_dnscfg
from linux_dnscfg import LinuxDNSCfg
import json
import os
import subprocess

class DarwinDNSCfg(LinuxDNSCfg):


    def backup(self):
        '''
            Didn't consider the case when some other force remove the backupfile
        '''
        LinuxDNSCfg.backup(self)
        backupfile = None
        if 'puredns_darwin.conf' in os.listdir("/etc"):
            return
        try:
            backupfile = open('/etc/puredns_darwin.conf', 'w+')
            conf = {}
            services = self.getallnetworkservices()
            
            for service in services:
                servers = self.getdnsservers(service)
                conf[service] = servers

            jsonconf = json.dumps(conf)
            backupfile.write(jsonconf)
        except Exception as e:
            print e
        finally:
            if backupfile: backupfile.close()
               

    def modify(self, dns):
        LinuxDNSCfg.modify(self, dns)
        services = self.getallnetworkservices()
        for service in services:
            self.setdnsservers(service, [dns])
        '''
        try:
            subprocess.check_output(["killall", "-HUP", "mDNSResponder"])
        except:
            pass
        '''
        print ">> Darwin modified"

    def restore(self):
        LinuxDNSCfg.restore(self)
        backupfile = None
        backupfilelocation = "/etc/puredns_darwin.conf"
        try: 
            backupfile = open(backupfilelocation, "r")
            backup = backupfile.read()
            conf = json.loads(backup)
            for key in conf:
                self.setdnsservers(key, conf[key])
        finally:
            if backupfile:
                backupfile.close()
                os.remove(backupfilelocation)
        print ">> Darwin restored"

    def printinfo(self):
        pass

    def getallnetworkservices(self):
        try: 
            ret = subprocess.check_output(["networksetup", "-listallnetworkservices"])
            ret = ret.split("\n")
            ret.remove('')
            ret.remove('An asterisk (*) denotes that a network service is disabled.')
            return ret
        except subprocess.CalledProcessError as e:
            print "getallnetworkservices failed: ", e
        return []

    def getdnsservers(self, service):
        try:
            ret = subprocess.check_output(["networksetup", "-getdnsservers", service])
            ret = ret.split("\n")
            ret.remove('')
            if len(ret) > 0 and "There aren't any " in ret[0]:
                return []
            return ret
        except subprocess.CalledProcessError as e:
            print "getdnsservers failed: ", e
        return ret

    def setdnsservers(self, service, dnsservers):
        try:
            init = ["networksetup", "-setdnsservers", service] + dnsservers
            ret = subprocess.check_output(init)
        except subprocess.CalledProcessError as e:
            print "setdnsservers failed: ", e


    

########NEW FILE########
__FILENAME__ = linux_dnscfg
# -*- coding: utf-8 -*-
# FileName: DNSCfg.py
# Author  : xiaoyao9933
# Email   : me@chao.lu
# Date    : 2013-02-14
# Vesion  : 1.2
import os
from dnscfg import DNSCfg

class LinuxDNSCfg(DNSCfg):
    #----------------------------------------------------------------------
    # Get the Adapter who has mac from wmi 
    #----------------------------------------------------------------------
    def backup(self):
        dnsfile = backupfile = None
        try:
            dnsfile = open('/etc/resolv.conf','r+')
            backupfile = open('/etc/puredns.conf','w+')
            self.backup = backupfile.read()
            self.conf = dnsfile.read()
            dnsfile.seek(0)
            backupfile.seek(0)
            '''
            This part is for auto fixing 
            '''
            if '# Auto generated by puredns' in self.conf: # When resolv.conf file already be modified
                if 'nameserver' in self.backup: # backup file is fine
                    dnsfile.write(self.backup)
                else: # backupfile got lost
                    backupfile.writelines(['nameserver 8.8.8.8\n','nameserver 8.8.8.4\n'])
            else:
                backupfile.write(self.conf)
        except Exception as e:
            print 'fileread error', e
        finally:
            if dnsfile: dnsfile.close()
            if backupfile: backupfile.close()
    #----------------------------------------------------------------------
    # Modify DNS
    #----------------------------------------------------------------------
    def modify(self, dns):
        try:
            dnsfile = open('/etc/resolv.conf','w')
            dnsfile.writelines(['# Auto generated by puredns (DO NOT DELETE THIS LINE)\n']) # Mark lol
            dnsfile.writelines(['nameserver '+dns+'\n'])
            print '>> Modified'
        finally:
            dnsfile.close()
    #----------------------------------------------------------------------
    # Restore DNS
    #----------------------------------------------------------------------
    def restore(self):
        try:
            dnsfile = open('/etc/resolv.conf','w')
            backupfile = open('/etc/puredns.conf','r')
            self.backup = backupfile.read()
            dnsfile.write(self.backup)
            print '>> Restored!'
        finally:
            dnsfile.close()
            backupfile.close()

def printinfo():
    print 'None'

########NEW FILE########
__FILENAME__ = windows_dnscfg
# -*- coding: utf-8 -*-
# FileName: DNSCfg.py
# Author  : xiaoyao9933
# Email   : me@chao.lu
# Date    : 2013-02-14
# Vesion  : 1.2
import wmi
import _winreg
import os
from ctypes import *

class WindowsDNSCfg:
	def __init__(self):
		self.wmiService = wmi.WMI()
		self.netCfgBackup={}
		self.notadmin = self.backup()
	#----------------------------------------------------------------------
	# Get the Adapter who has mac from wmi 
	#----------------------------------------------------------------------
	def backup(self):
		flag = False
		try:
			hkey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,r'System\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces\\',0,_winreg.KEY_ALL_ACCESS)
		except:
			return True
		keyInfo = _winreg.QueryInfoKey(hkey)
		for index in range(keyInfo[0]):
				hSubKeyName = _winreg.EnumKey(hkey, index)
				hSubKey = _winreg.OpenKey(hkey, hSubKeyName,0,_winreg.KEY_ALL_ACCESS)
				try:
					_winreg.QueryValueEx(hSubKey, 'T1')
					self.netCfgBackup[hSubKeyName]=_winreg.QueryValueEx(hSubKey, 'NameServer')[0]
					if '127.0.0.1' in self.netCfgBackup[hSubKeyName]:
						try:
							self.netCfgBackup[hSubKeyName]=_winreg.QueryValueEx(hSubKey, 'LastNameServer')[0]
						except:
							self.netCfgBackup[hSubKeyName]=u'8.8.8.8,8.8.4.4'
						flag = True
						print '>> Not normal closed last time , set dns to backup or 8.8.8.8.'
					else:
						_winreg.SetValueEx(hSubKey,'LastNameServer',None,_winreg.REG_SZ,self.netCfgBackup[hSubKeyName])					
				except:
					pass
		if flag:
			self.restore()
		return False
	#----------------------------------------------------------------------
	# Modify DNS
	#----------------------------------------------------------------------
	def modify(self,dns):
		for id in self.netCfgBackup:
			self.RegModifyDns(id,dns)
		self.colNicConfigs = self.wmiService.Win32_NetworkAdapterConfiguration(IPEnabled = True)
		for i in range(len(self.colNicConfigs)):
			if self.colNicConfigs[i].SetDNSServerSearchOrder(DNSServerSearchOrder = dns.split(','))[0] == 0:
				print '>> Modify Success!'
		return 0
	#----------------------------------------------------------------------
	# Restore DNS
	#----------------------------------------------------------------------
	def restore(self):
		flag = True
		for id in self.netCfgBackup:
			self.RegModifyDns(id,self.netCfgBackup[id])
			self.colNicConfigs = self.wmiService.Win32_NetworkAdapterConfiguration(SettingID = id, IPEnabled = True)
			for i in range(len(self.colNicConfigs)):
				if '.' in self.netCfgBackup[id]:
					tmp = self.netCfgBackup[id].split(',')
				else:
					tmp = []
				if self.colNicConfigs[i].SetDNSServerSearchOrder(DNSServerSearchOrder = tmp)[0] == 0:
					print '>> Restore Success!'
					flag = False
		if flag:
			DhcpNotifyConfigChange = windll.dhcpcsvc.DhcpNotifyConfigChange
			result = True
			for id in self.netCfgBackup:
				try:
					tmp = DhcpNotifyConfigChange(None, \
								id, \
								False, \
								0, \
								0, \
								0, \
								0)
					if tmp == 0:
						result =False
				except:
					pass
			if result:
				self.colNicConfigs = self.wmiService.Win32_NetworkAdapterConfiguration(IPEnabled = True)
				for i in range(len(self.colNicConfigs)):
					self.colNicConfigs[i].SetDNSServerSearchOrder(DNSServerSearchOrder = ['8.8.8.8','8.8.4.4'])
		return 0
	#----------------------------------------------------------------------
	# ModifyDns in Registry
	#----------------------------------------------------------------------
	def RegModifyDns(self,id,dns):
		print id,dns
		hkey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,r'System\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces\\',0,_winreg.KEY_ALL_ACCESS)
	
		hSubKey = _winreg.OpenKey(hkey, id,0,_winreg.KEY_ALL_ACCESS)
		print _winreg.SetValueEx(hSubKey,'NameServer',None,_winreg.REG_SZ,dns)
	
		#pass
		
def printinfo():
	print 'version 1.2 modified'
	print 'Registry Info:'
	hkey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,r'System\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces\\')
	keyInfo = _winreg.QueryInfoKey(hkey)
	for index in range(keyInfo[0]):
			hSubKeyName = _winreg.EnumKey(hkey, index)
				
			print hSubKeyName
			hSubKey = _winreg.OpenKey(hkey, hSubKeyName)
			try:
				print _winreg.QueryValueEx(hSubKey, 'NameServer')
			except:
				pass
	print 'WMI Info'
	wmiService = wmi.WMI()
	colNicConfigs = wmiService.Win32_NetworkAdapterConfiguration()
	for i in range(len(colNicConfigs)):
		print 'IPEnabled'
		print colNicConfigs[i].IPEnabled
		print 'SettingID' 
		print colNicConfigs[i].SettingID 
		print 'DNS' 
		print colNicConfigs[i].DNSServerSearchOrder

########NEW FILE########
__FILENAME__ = windows_netsh_dnscfg
#! /usr/bin/python
# -*- coding: utf-8 -*-
# FileName: windows_netsh_dnscfg.py
# Author  : davidaq
# Email   : aq@num16.com
# Date    : 2013-03-07
from dnscfg import DNSCfg
import os
import subprocess
import re
########################################################################
class WindowsNetshDNSCfg(DNSCfg):
    def __init__(self):
        self.backupfile = os.path.expanduser('~') + os.path.sep + 'puredns_backup.log'
        self.backup_data = {}
        self.notadmin = not self.backup()
        
    def backup(self):
        backup_file = None
        # check for previous saved backup
        try:
            backup_file = open(self.backupfile, 'r')
            print '>> Not normally closed last time, will set dns to backup.'
            self.backup_data = eval(backup_file.read())
            return True
        except:
            pass
        finally:
            if backup_file != None:
                backup_file.close()
                backup_file = None
        # get the current primary dns settings fro all connected interfaces and make backup
        try:
            raw_result = subprocess.check_output('netsh interface ip show dns')
            ip = re.compile(r'\d+\.\d+\.\d+\.\d+')
            result = {}
            for interface in self.interfaces():
                pos = raw_result.find('"' + interface + '"')
                pos = raw_result.find('\n', pos) + 1
                end = raw_result.find('\n', pos)
                line = raw_result[pos:end]
                result[interface] = 'auto'
                if 'DHCP' not in line and 'dhcp' not in line:
                    match = ip.search(line)
                    if match != None:
                        result[interface] = match.group()
            self.backup_data = result
            backup_file = open(self.backupfile, 'w')
            backup_data_json = repr(self.backup_data)
            backup_file.write(backup_data_json)
            return True
        except:
            print 'failed to backup'
            return False
        finally:
            if backup_file != None:
                backup_file.close()

    def modify(self, dns):
        cmd = ['pushd interface ip']
        for interface in self.backup_data.keys():
            cmd.append('set dns "' + interface + '" source=static addr=' + dns + ' register=PRIMARY')
        cmd.append('popd\n')
        process = subprocess.Popen('netsh', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        process.communicate('\n'.join(cmd))

    def restore(self):
        cmd = ['pushd interface ip']
        for interface in self.backup_data.keys():
            if self.backup_data[interface] == 'auto':
                cmd.append('set dns "' + interface + '" source=dhcp register=PRIMARY')
            else:
                cmd.append('set dns "' + interface + '" source=static addr=' + self.backup_data[interface] + ' register=PRIMARY')
        cmd.append('popd\n')
        process = subprocess.Popen('netsh', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        process.communicate('\n'.join(cmd))
        try:
            os.unlink(self.backupfile)
        except:
            pass    # just ignore if the backup file doesn't exist

    def interfaces(self):
        raw_result = subprocess.check_output('netsh interface ip show interfaces')
        result = []
        token = ' connected'
        for line in raw_result.split('\n'):
            pos = line.find(token)
            if pos > -1:
                item = line[pos + len(token):].strip()
                result.append(item)
        return result

def printinfo():
    print 'None'

########NEW FILE########
__FILENAME__ = _base
import platform

class DNSCfg(object):

    def __init__(self):
        pass

    def backup(self):
        pass

    def modify(self, dns):
        pass

    def restore(self):
        pass

    def printinfo(self):
        pass


def create_dnscfg():
    s = platform.system()
    if s == "Darwin":
        from dnscfg.darwin_dnscfg import DarwinDNSCfg
        return DarwinDNSCfg()
    elif s == "Linux":
        from dnscfg.linux_dnscfg import LinuxDNSCfg
        return LinuxDNSCfg()
    elif s == "Windows":
        try:
            from dnscfg.windows_dnscfg import WindowsDNSCfg
            return WindowsDNSCfg()
        except:
            print 'wmi method not working try netsh'
            from dnscfg.windows_netsh_dnscfg import WindowsNetshDNSCfg
            return WindowsNetshDNSCfg()
    else:
        print "Unsuppoerted os"
        

########NEW FILE########
__FILENAME__ = linux_loader
import sys,os
from subprocess import Popen
from server.tcpdns import TCPDNS
from server.udpdns import UDPDNS
from daemon import Daemon

def load(cfg):
    if os.geteuid() !=0:
        print '>> Please run this service as root.'
        os._exit(1)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            dns = TCPDNS(cfg) 
            dns.start()
        elif 'stop' == sys.argv[1]:
            dns = Daemon()
            dns.stop()
        elif 'restart' == sys.argv[1]:
            dns = TCPDNS(cfg) 
            dns.restart()
        elif 'censor' == sys.argv[1]:
            dns = UDPDNS(cfg)
            dns.start()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        dns = Daemon()
        tmp = dns.getstate()
        print "usage: %s start|stop|restart" % sys.argv[0]
        print "special usage: %s double-recv" % sys.argv[0]
        print '-------------------------------------'
        if tmp:
            print 'The daemon is running'
        else:
            print 'The daemon is stopped'
        sys.exit(2)

########NEW FILE########
__FILENAME__ = windows_loader
﻿# -*- coding: utf-8 -*-
#! /usr/bin/python
# FileName: PureDNS.py
# Author  : xiaoyao9933
# Email   : me@chao.lu
# Date    : 2013-03-09
# Vesion  : 1.4
import wx
import webbrowser
import time
import _winreg
from server.tcpdns import TCPDNS
import os,sys,traceback 
import signal 
########################################################################
class Icon(wx.TaskBarIcon):
    TBMENU_SERVICE = wx.NewId()
    TBMENU_CLOSE   = wx.NewId()
    TBMENU_ABOUT  = wx.NewId()
    state=False
    version = '1.4'
    #----------------------------------------------------------------------
    def __init__(self,serv,dnscfg):
        wx.TaskBarIcon.__init__(self)
        self.menu = wx.Menu()
        self.menu.Append(self.TBMENU_SERVICE, "NULL")
        self.menu.Append(self.TBMENU_ABOUT, u"关于 PureDNS" + self.version)
        self.menu.AppendSeparator()
        self.menu.Append(self.TBMENU_CLOSE, u"退出程序")
        self.tbIcon = wx.EmptyIcon()
        self.tbIcon.LoadFile(resource_path("PureDNS.ico"),wx.BITMAP_TYPE_ICO) 
        self.SetIcon(self.tbIcon, "PureDNS")
        # bind some events
        self.Bind(wx.EVT_MENU, self.OnClose, id=self.TBMENU_CLOSE)
        self.Bind(wx.EVT_MENU, self.OnTaskBarSevice, id=self.TBMENU_SERVICE)
        self.Bind(wx.EVT_MENU, self.OnTaskBarAbout, id=self.TBMENU_ABOUT)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.OnTaskBarClick)
        self.Bind(wx.EVT_TASKBAR_RIGHT_DOWN, self.OnTaskBarClick)
        self.serv = serv
        print 'there1'
        self.serv.run()
        self.dnscfg = dnscfg
        time.sleep(1)
        print 'there'
        if self.serv.server:
            self.state = True
            self.dnscfg.modify('127.0.0.1')
            self.menu.SetLabel(self.TBMENU_SERVICE,u'停用DNS代理')
        else:
            self.state = False
            wx.MessageDialog(None,u'端口号53已经被占用',u'错误',wx.OK).ShowModal()
            self.menu.SetLabel(self.TBMENU_SERVICE,u'启动DNS代理') 

    #----------------------------------------------------------------------
    def OnTaskBarSevice(self,evt):
        if self.state is False:
            self.dnscfg.modify('127.0.0.1')
            self.state=True
            self.menu.SetLabel(self.TBMENU_SERVICE,u'停用DNS代理')
        else:
            self.dnscfg.restore()
            self.state=False
            self.menu.SetLabel(self.TBMENU_SERVICE,u'启动DNS代理')         
 
    #----------------------------------------------------------------------
    def OnTaskBarActivateD(self, evt):
        """"""
        pass
 
    #----------------------------------------------------------------------

    def OnClose(self, evt): 
        self.RemoveIcon()
        self.menu.Destroy()
        self.Destroy()
        wx.Exit()
        print '>> Destoryted'
        
    #----------------------------------------------------------------------
    def OnTaskBarClick(self, evt):
        """
        Create the click menu
        """
        self.PopupMenu(self.menu)
    #def CreatePopupMenu(self):
  #      return self.menu
    def OnTaskBarAbout(self, evt):
        """
        Create the about dialog
        """
        webbrowser.open('http://xiaoyao9933.github.com/puredns/')
class Frame(wx.Frame):
    def __init__(self, *args, **kwargs): 
        super(Frame, self).__init__(*args, **kwargs) 
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.tbIcon = Icon(wx.GetApp().htcpdns, wx.GetApp().hdnscfg)
    def onClose(self,evt):
        print '>> OnClose()'
        logfile.flush()
        wx.GetApp().OnExit()

        
class App(wx.App):
    def __init__(self, logfile,notadmin,cfg,redirect=False, filename=None):
        self.logfile=logfile
        self.notadmin = notadmin
        self.hdnscfg = cfg
        wx.App.__init__(self, redirect, filename)

    def OnInit(self):
        if False:
            wx.MessageDialog(None,u'请以管理员权限运行本程序',u'错误',wx.OK).ShowModal()
            self.ExitMainLoop()
            return True
        self.htcpdns = TCPDNS(self.hdnscfg)
        if self.hdnscfg.notadmin:
            wx.MessageDialog(None,u'请以管理员权限运行本程序',u'错误',wx.OK).ShowModal()
            self.htcpdns.force_close()
            self.ExitMainLoop()
            return True
        self.frame = Frame(None)
        #.Bind(wx.EVT_CLOSE,self.OnExit)
        #self.Bind(wx.EVT_END_SESSION,self.OnExit)
        return True
    def OnExit(self):
        self.hdnscfg.restore()
        self.htcpdns.force_close()
        print '>> OnExit()'
        logfile.flush()
        self.ExitMainLoop()
        
########################################################################
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
#----------------------------------------------------------------------
# Run the program
def load(cfg):
    firstrun=False
    notadmin=False
    global logfile

    try:
        hkey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\\xiaoyao9933')
        firstrun = False
    except:
        try:
            hkey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\\',0,_winreg.KEY_ALL_ACCESS)
            _winreg.CreateKey(hkey, 'xiaoyao9933')
        except:
            notadmin=True
        firstrun = True
    if firstrun:
        webbrowser.open('http://xiaoyao9933.github.com/puredns/')
    try:
        logfile=open('log.txt','w')
        sys.stdout = logfile
        sys.stderr = logfile
        try:
            app = App(logfile, notadmin, cfg)
            app.MainLoop()
        except:
            traceback.print_exc()
            #DNSCfg.PrintInfo()
            logfile.flush()
            wx.MessageDialog(None,u'遇到致命错误，请将同目录下的log.txt发送到puredns@chao.lu,多谢!',u'错误',wx.OK).ShowModal()
            
    finally:
        sys.stdout = logfile
        sys.stderr = logfile
        print '>> Finally closed'
        try:
            logfile.close()
        except:
            pass
        os._exit(0)
    


########NEW FILE########
__FILENAME__ = _base
import platform

def create_loader():
    s = platform.system()
    if s == "Darwin":
        from loader.linux_loader import load
        return load
    elif s == "Linux":
        from loader.linux_loader import load
        return load
    elif s == "Windows":
        from loader.windows_loader import load
        return load
    else:
        print "Unsuppoerted os"
        

########NEW FILE########
__FILENAME__ = puredns
#! /usr/bin/python
import dnscfg
import loader

if __name__ == "__main__":

    cfg = dnscfg.create_dnscfg()
    load = loader.create_loader()
    
    # Start loading app
    load(cfg)

########NEW FILE########
__FILENAME__ = tcpdns
#! /usr/bin/python
# -*- coding: utf-8 -*-
# cody by zhouzhenster@gmail.com modified by xiaoyao9933(me@chao.lu)

# ver: 0.2 update 2011-10-23
#           use SocketServer to run a multithread udp server
# update:
# 2012-04-16, add more public dns servers support tcp dns query
#  8.8.8.8        google
#  8.8.4.4        google
#  156.154.70.1   Dnsadvantage
#  156.154.71.1   Dnsadvantage
#  208.67.222.222 OpenDNS
#  208.67.220.220 OpenDNS
#  198.153.192.1  Norton
#  198.153.194.1  Norton
'''
Last updated: 2013-3-3
By: Ming
Email: mjzshd@gmail.com
'''
import os, sys
import socket
import struct
import threading
import SocketServer
import traceback
import random
import platform
from const import *
from server._base import *
from daemon import *


class RequestHandlerToTCP(ThreadedDNSRequestHandler):

    '''
    query remote tcp server
    follow rfc1035
    '''
    def queryremote(self, server, port, querydata):
        # RFC1035 section-4.2.2
        Buflen = struct.pack('!h', len(querydata))
        sendbuf = Buflen + querydata
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(TIMEOUT) # set socket timeout
            s.connect((server, int(port)))
            s.send(sendbuf)
            data = s.recv(2048)
        except:
            print traceback.print_exc(sys.stdout)
            print "Trouble happened when using dns server: ", server
            if s: s.close()
            return
        if s: s.close()
        return data[2:]


class TCPDNS(Daemon):

    server = None

    def __init__(self, cfg):
        if platform.system() !='Windows':  
            Daemon.__init__(self, '/tmp/test.pid', '/dev/null', 'stdout.log', 'stderr.log')
        self.dnscfg = cfg

    def force_close(self):
        self.run = False
        #FIXME: What the dummy request for?
        self.create_dummy_request()
        if platform.system() =='Windows': 
            self.server.shutdown()
        
    def create_dummy_request(self):
        address = ('127.0.0.1', 53)
        sockudp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sockudp.sendto('fake data fake datafake datafake datafake datafake datafake datafake data',address)
        print '>> Send dummy'
	
    def run(self):
        self.run = True
        '''
        signal.signal(signal.SIGQUIT, self.terminate)
        #signal.signal(signal.SIGKILL, self.terminate)
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)
        '''
        self.dnscfg.backup()
        self.dnscfg.modify('127.0.0.1')
        print '>> Please wait program init....'
        print '>> Init finished!'
        self.server = ThreadedUDPServer(('127.0.0.1', 53), RequestHandlerToTCP)
        self.server_thread = threading.Thread(target = self.server.serve_forever)
        #self.server_thread.daemon = True
        self.server_thread.start()
        print 'here'
        print platform.system()
        if platform.system() !='Windows': 
            while self.run:
                time.sleep(1)
            self.server.shutdown()
            print '>> close server ,success'
        

    def terminate(self, signal, param):
        self.run = False
        self.force_close()
        self.dnscfg.restore()
        os._exit(0)


########NEW FILE########
__FILENAME__ = udpdns
'''
This module is still under development
Last updated: 2013-3-6
By: Ming
Email: mjzshd@gmail.com
'''
import os, sys
import socket
import struct
import threading
import SocketServer
import traceback
import random
import select
from signal import SIGTERM, SIGQUIT,SIGINT,SIGKILL

from const import *
from server._base import *
from daemon import *

'''
This module provide a udp interceptor which can cencor all data received from dns server.
'''


class RequestHandlerToUDP(ThreadedDNSRequestHandler):


    '''
    Chech if the response contains fake ip
    Resolve the dns response according to rfc 1035
    '''
    def censor(self, data):
        rcode = (struct.unpack("!B", data[3])[0] & 15)
        aabit = (struct.unpack("!B", data[2])[0] & 4)
        if rcode != 0: # We only censor the successful response
            return True
        querycnt = struct.unpack("!H", data[4:6])[0]
        anscnt = struct.unpack("!H", data[6:8])[0]
        if anscnt == 0: return True
        anchor = 12
        for i in xrange(querycnt):
            anchor += domainlength(data[anchor:])
            anchor += 4
        for i in xrange(anscnt):
            namelen = 2
            if aabit:
                namelen = domainlength(data[anchor:])
            anchor += namelen
            tp = struct.unpack("!H", data[anchor : anchor + 2])[0]
            if tp != 1: # Only check type A response
                return True
            cls = struct.unpack("!H", data[anchor + 2 : anchor + 4])[0]
            if cls != 1: # Only check class IN response
                return True
            # Move forward anchor
            anchor += 10
            addr = '.'.join(str(j) for j in struct.unpack("!BBBB", data[anchor : anchor + 4]))
            if addr in fakeip: # Core!!
                return False
            anchor += 4
        return True


    '''
    still testing
    '''
    def queryremote(self, server, port, querydata):
        # RFC1035 section-4.2.2
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(3) # set socket timeout
            remote = (server, int(port))
            s.sendto(querydata, remote)
            expiration = time.time() + 60
            poll = select.poll()    
            poll.register(s.fileno(), select.POLLIN)
            #ret = poll.poll(1000000)
            while time.time() < expiration:
                # Wait read here
                pollret = poll.poll(60000)
                pollret = [i[0] for i in pollret]
                if s.fileno() in pollret:
                    (data, addr) = s.recvfrom(65535)
                    if addr[0] == server and self.censor(data):
                        return data
        except:
            print traceback.print_exc(sys.stdout)
            print "Trouble happened when using dns server: ", server
            if s: s.close()
            return
        if s: s.close()
        return data


class UDPDNS(Daemon):

    stopped = threading.Event()
    server = None

    def __init__(self, cfg):
        Daemon.__init__(self, '/tmp/test.pid', '/dev/null', 'stdout.log', 'stderr.log')
        self.dnscfg = cfg

    def force_close(self):
        self.stopped.set()
        #FIXME: What the dummy request for?
        self.create_dummy_request()
        
    def create_dummy_request(self):
        address = ('127.0.0.1', 53)
        sockudp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sockudp.sendto('fake data fake datafake datafake datafake datafake datafake datafake data',address)
        print '>> Send dummy'
	
    def run(self):
        self.run = True
        self.dnscfg.backup()
        self.dnscfg.modify('127.0.0.1')
        print '>> Please wait program init....'
        print '>> Init finished!'
        self.server = ThreadedUDPServer(('127.0.0.1', 53), RequestHandlerToUDP)
        self.server_thread = threading.Thread(target = self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        while self.run:
            time.sleep(1)
        self.server.shutdown()
        print '>> close server ,success'

    def terminate(self, signal, param):
        self.run = False
        self.force_close()
        self.dnscfg.restore()
        os._exit(0)


########NEW FILE########
__FILENAME__ = _base
import os, sys
import socket
import struct
import threading
import SocketServer
import traceback
import random

from const import *

#-------------------------------------------------------------
# Hexdump Cool :)
# default width 16
#--------------------------------------------------------------
def hexdump( src, width=16 ):
    FILTER=''.join([(len(repr(chr(x)))==3) and chr(x) or '.' for x in range(256)])
    result=[]
    for i in xrange(0, len(src), width):
        s = src[i:i+width]
        hexa = ' '.join(["%02X"%ord(x) for x in s])
        printable = s.translate(FILTER)
        result.append("%04X   %s   %s\n" % (i, hexa, printable))
    return ''.join(result)


#---------------------------------------------------------------
# bytetodomain
# 03www06google02cn00 => www.google.cn
#--------------------------------------------------------------
def bytetodomain(s):
    domain = ''
    i = 0
    length = struct.unpack('!B', s[0:1])[0]
  
    while length != 0 :
        i += 1
        domain += s[i:i+length]
        i += length
        length = struct.unpack('!B', s[i:i+1])[0]
        if length != 0 :
            domain += '.'
  
    return domain

def domainlength(s):
    tmp = struct.unpack('!B', s[0:1])[0]
    length = 0
    while tmp != 0:
        length = length + 1 + tmp
        tmp = struct.unpack('!B', s[length:length+1])[0]
    return length + 1
        

def resolve_request(querydata):
    domain = bytetodomain(querydata[12:-4])
    qtype = struct.unpack('!h', querydata[-4:-2])[0]
    return (domain, qtype)


class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    pass


class ThreadedDNSRequestHandler(SocketServer.BaseRequestHandler):
    # Ctrl-C will cleanly kill all spawned threads
    daemon_threads = True
    # much faster rebinding
    allow_reuse_address = True

    #-----------------------------------------------------
    # send udp dns respones back to client program
    #----------------------------------------------------
    def transfer(self, querydata, addr, server):
        if not querydata: return
        (domain, qtype) = resolve_request(querydata)
        """
        print 'domain:%s, qtype:%x, thread:%d' % \
             (domain, qtype, threading.activeCount())
        """
        sys.stdout.flush()
        choose = random.sample(xrange(len(DHOSTS)), 1)[0]
        DHOST = DHOSTS[choose]
        response = self.queryremote(DHOST, DPORT, querydata)
        if response:
            # udp dns packet no length
            server.sendto(response, addr)

    def handle(self):
        data = self.request[0]
        socket = self.request[1]
        addr = self.client_address
        try:
            self.transfer(data, addr, socket)
        except:
            pass

########NEW FILE########
