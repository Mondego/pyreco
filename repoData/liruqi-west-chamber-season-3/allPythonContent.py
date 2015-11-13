__FILENAME__ = dos
#!/usr/bin/python
#using scapy to inject ack
#but scapy lock resource, buggy

import socket,sys,random,errno,os,threading
import config

sending = 0
class sendSYN(threading.Thread):
    dstIP = ""
    def __init__(self, dst):
        global sending
        threading.Thread.__init__(self)
        print "sending ack " + dst +" " + str(sending)
        sending += 1
        self.dstIP = dst

    def run(self):
        from scapy.all import *
        global sending
        conf.iface='en0';#network card XD

        t = TCP()
        t.sport = random.randint(1,65535)
        t.dport = 80
        t.flags = 'A'
        t.payload = "GET / HTTP/1.1\r\nHost: twitter.com\r\n\r\n"

        sendp(Ether(type=0x800) / IP(dst=self.dstIP) / t, verbose=0)
        sending -= 1
        print "sent ack " + self.dstIP

def connectip(ip):
    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    remote.settimeout(6)
    remote.connect((oip, 80))
    #host = random.choice(config.gConfig["BLOCKED_DOMAINS_LIST"])
    host = "twitter.com"
    remote.send("GET / HTTP/1.1\r\nHost: "+host+"\r\n\r\n")
    remote.recv(1024*64)
    print oip, "good"
    remote.close()

refusedipset = {}
badipset = {}

rf = open("status/timedout-ip.list", "r")
blockedIpString = rf.read()
rf.close()

for ip in blockedIpString.split("\n"):
    if len(ip) >= 7:
        badipset[ip]=1

rf = open("status/refused-ip.list", "r")
resetIpString = rf.read()
rf.close()

for ip in resetIpString.split("\n"):
    if len(ip) >= 7: 
        refusedipset[ip]=1

timeoutf = 0
resetf = 0

try:
    class option:
        def __init__(self): 
            self.action = ''
            self.verbose = 0
    gOptions = option()
    if len(sys.argv) >= 2:
        gOptions.action = sys.argv[1]
    if len(sys.argv) >= 3:
        gOptions.verbose = sys.argv[2]
except:
    print "usage: ./dos.py <action> <verbose>"
    
if gOptions.action == "c": #check
    timeoutf = open("status/timedout-ip-checked.list", "r")
    timeoutString = timeoutf.read()
    timeoutf.close()

    timeoutList = timeoutString.split("\n")
    
    timeoutf = open("status/timedout-ip-checked.list", "a")
    for oip in badipset:
        oip = oip.split(" ")[0]
        if oip in timeoutList:
            print "ignore ", oip
            continue

        print "connect to", oip
        try:
            connectip(oip)
        except socket.timeout:
            print "timed out", oip
            timeoutf.write(oip+"\n")
            timeoutf.flush()
        except:
            print "connected to", oip
    timeoutf.close()
    exit(0)

verbose = gOptions.verbose
pid = os.getpid()
if gOptions.action == "a": #append
    timeoutf = open("status/timedout-ip.list"+".pid"+str(pid), "a")
    resetf = open("status/refused-ip.list", "a")
    goodf = open("status/good-ip.list", "a")
    verbose = 1

ipm24set = {}
for ip in config.gConfig["BLOCKED_IPS"]:
    ipm24 = ".".join(ip.split(".")[:3])
    ipm24set[ipm24]=1
for ip in config.gConfig["BLOCKED_IPS_M24"]:
    ipm24set[ip] = 1
    if verbose: print "M24: " + ip

for ip in config.gConfig["BLOCKED_IPS_M16"]:
    for ip3 in range(256):
        ipm24 = ip + "." + str(ip3)
        ipm24set[ipm24]=1
        if verbose: print "M16: " + ipm24

resetcnt = 0

while 1:
    ipm24list = ipm24set.keys()
    random.shuffle(ipm24list)

    for ipm24 in ipm24list:
        for last in range(1,256):
            oip = ipm24 + "." + str(last)
            if oip in badipset:
                #if sending < 8: sendSYN(oip).start()
                continue
            if oip in refusedipset:
                #if sending < 8: sendSYN(oip).start()
                continue

            try:
                if verbose: print "connect to", oip
                connectip(oip)
                goodf.write(oip+"\n")
                goodf.flush()
            except socket.timeout:
                #if sending < 8: sendSYN(oip).start()
                if timeoutf:
                    timeoutf.write(oip+"\n")
                    timeoutf.flush()
            except socket.error, e:
                if verbose: print oip, "socket.error", e

                if e[0] == errno.ECONNRESET:
                    resetcnt += 1
                    goodf.write(oip+"\n")
                    goodf.flush()
                    #print "*" resetcnt, "resets"
                    if resetcnt % 100 == 0:
                        print pid, resetcnt, "resets"
                        continue
                if e[0] == errno.ECONNREFUSED:
                    #print "* refused", oip
                    refusedipset[oip]=1
                    if resetf:
                        resetf.write(oip+"\n")
                        resetf.flush()

    if gOptions.action == "a": #append
        break

if timeoutf: timeoutf.close()
if resetf: resetf.close()
if goodf: goodf.close()

########NEW FILE########
__FILENAME__ = iprange
# copied from: http://code.google.com/p/chnroutes/source/browse/trunk/chnroutes.py

import re
import urllib2
import sys
import argparse
import math
import json

def fetch_ip_data():
    #fetch data from apnic
    print "Fetching data from apnic.net, it might take a few minutes, please wait..."
    url=r'http://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest'
    data=urllib2.urlopen(url).read()
    
    cnregex=re.compile(r'apnic\|cn\|ipv4\|[0-9\.]+\|[0-9]+\|[0-9]+\|a.*',re.IGNORECASE)
    cndata=cnregex.findall(data)
    
    results=[]

    for item in cndata:
        unit_items=item.split('|')
        starting_ip=unit_items[3]
        num_ip=int(unit_items[4])
        
        imask=0xffffffff^(num_ip-1)
        #convert to string
        imask=hex(imask)[2:]
        mask=[0]*4
        mask[0]=imask[0:2]
        mask[1]=imask[2:4]
        mask[2]=imask[4:6]
        mask[3]=imask[6:8]
        
        #convert str to int
        mask=[ int(i,16 ) for i in mask]
        mask="%d.%d.%d.%d"%tuple(mask)
        
        #mask in *nix format
        mask2=32-int(math.log(num_ip,2))
        
        results.append((starting_ip + "/%d")%mask2)
         
    return results

if __name__=='__main__':
    r = fetch_ip_data();
    s = json.dumps(r).replace(" ", "");
    print s

    open("exclude-ip.json", "w").write(s)



########NEW FILE########
__FILENAME__ = multi-thread-socket
# -*- coding: utf-8 -*-
# author: liruqi@gmail.com

import asyncore, socket, sys, urlparse, threading, time, random, urllib2
from httplib import HTTPResponse

#收到data最大長度
MAX_RECV = 4096
gConfig = {}

#等待server傳送訊息的thread
class send_server_thread(threading.Thread):
    def __init__(self,ip,port):
        print "init " + ip
        #self.client = client(ip,port)
        self.ip = ip
        self.port = port
        self.error = 0
        self.status = 0
        self.clientSendData = ""
        self.clientRecvData = ""
        threading.Thread.__init__ ( self )
        
    def run(self):
        try:
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.connect((self.ip, int(port)))
            remote.send(self.clientSendData)
            response = HTTPResponse(remote)
            response.begin()
            for hh, vv in response.getheaders():
                if hh.upper()!='TRANSFER-ENCODING':
                    self.clientRecvData += hh + ': ' + vv + '\r\n'

            self.clientRecvData += "\r\n"
            self.status = response.status
            print (self.ip + " response: %d"%(response.status))
            while True:
                d = remote.recv(MAX_RECV)
                if (len(d)==0): break
                self.clientRecvData += d
            
        except:
            exc_type, self.error, exc_traceback = sys.exc_info()
            print (self.ip+":"+self.port + " error: " , exc_type , self.error)
            sys.stdout.flush()


#主程式
if __name__ == "__main__":
    s = urllib2.urlopen("http://ipgeo.info/httpproxy/text.php")
    gConfig["HTTP_PROXY_SERVERS"] = []
    threads = []
    socket.setdefaulttimeout(6)
    url = "http://twitter.com/"
    if len(sys.argv) > 1: url=sys.argv[1]
        
    (scm, netloc, path, params, query, _) = urlparse.urlparse(url)
    if path=="": path="/"

    lines = s.readlines()
    s.close()
    for line in lines:
        line = line.strip()
        if len(line) <= 0: continue

        ip, port = line.split(':')
        client_thread = send_server_thread(ip, port)
        gConfig["HTTP_PROXY_SERVERS"].append((ip,(int)(port)))

        if random.randint(0,len(lines)/256) != 0: continue
 
        print (scm, netloc, path, params, query)
        #client_thread.client.SendData = (" ".join(("GET", path, "1.1")) + "\r\n") + "Host: " + netloc + "\r\n" + "\r\n"
        client_thread.clientSendData = (" ".join(("GET", path, "1.1")) + "\r\n") + "Host: " + netloc + "\r\n" + "\r\n"
        
        client_thread.start()
        threads.append(client_thread)

    time.sleep(6)
    print ("Check recv data.")
    recvset = {}
    
    ef = open(netloc+".log", "w")
    for thread in threads:
        if len(thread.clientRecvData) > 0:
            if thread.status == 200:
                ef.write ("200: " + thread.ip + thread.clientRecvData)
                continue
            if thread.clientRecvData in recvset:
                recvset[thread.clientRecvData] += 1
            else:
                recvset[thread.clientRecvData] = 1
            #thread.exit()

    recvmax = ""
    recvmaxcnt = 0
    for data in recvset:
        if recvset[data] > recvmaxcnt:
            recvmaxcnt = recvset[data] 
            recvmax = data

    ef.write("Error: " + recvmax)
    ef.close()
    exit(1)


########NEW FILE########
