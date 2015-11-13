__FILENAME__ = dsvr-webadmin
#!/usr/bin/env python
#
# DSVR (Domain Specific VPN Router)
# Copyright 2013 Darran Boyd
#
# dboyd13 [at @] gmail.com
#
# Licensed under the "Attribution-NonCommercial-ShareAlike" Vizsage
# Public License (the "License"). You may not use this file except
# in compliance with the License. Roughly speaking, non-commercial
# users may share and modify this code, but must give credit and 
# share improvements. However, for proper details please 
# read the full License, available at
#     http://vizsage.com/license/Vizsage-License-BY-NC-SA.html 
# and the handy reference for understanding the full license at 
#     http://vizsage.com/license/Vizsage-Deed-BY-NC-SA.html
#
# Unless required by applicable law or agreed to in writing, any
# software distributed under the License is distributed on an 
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, 
# either express or implied. See the License for the specific 
# language governing permissions and limitations under the License.

import re
import os
import sys
import commands
import configparser
import netifaces
from datetime import timedelta
from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
app = Flask(__name__)

def getdsvrini(filename):
    if "/" not in filename:
        filename = os.path.abspath(os.path.dirname(sys.argv[0])) + "/" + filename
    config = configparser.ConfigParser()
    config.read(filename)
    return config

def writedsvrini(config,filename):
    if "/" not in filename:
        filename = os.path.abspath(os.path.dirname(sys.argv[0])) + "/" + filename
    file = open(filename,"w")
    config.write(file)
    file.close()

def getpeerdata():
    peers = commands.getstatusoutput('ls /etc/ppp/peers/db* -1 | xargs -n1 basename')
    ppppeers_dict = {}
    if peers[0] == 0:

        for peerfile in peers[1].split('\n'):
            contents = []
            filefullpath = "/etc/ppp/peers/" + peerfile
            file = open(filefullpath)
            while 1:
                line = file.readline().rstrip("\r\n")
                if not line:
                    break
                contents.append(line)
            ppppeers_dict[peerfile] = contents
    return ppppeers_dict

def writepeerfile(input_list, peerstr):
    filename = "/etc/ppp/peers/" + peerstr
    for index in input_list:
        if os.path.exists(filename):
            os.remove(filename)
        file = open(filename, 'w+')
        for listitem in input_list:
            file.write(listitem + "\n")
        file.close()
        
def delinitdscript(peerstr):
    filename = "/etc/init.d/" + peerstr
    if os.path.exists(filename):
        os.remove(filename)
        
def createinitdscript(peerstr):
    srcfilename = os.path.abspath(os.path.dirname(sys.argv[0])) + "/scripts/vpninitdtemplate"
    dstfilename = "/etc/init.d/" + peerstr
    if not os.path.exists(dstfilename):
        command = "sudo cp " + srcfilename + " " + dstfilename
        os.system(command)
        command = "sudo chmod +x " + dstfilename
        os.system(command)
        command = "update-rc.d " + peerstr + " defaults"
        os.system(command)

def encodepeerfile(input_dict, peerstr):
    plist = []
    plist.append("#friendlyname" + " " + str(input_dict[peerstr]['friendlyname']))
    plist.append("#interestingdomains" + " " + ",".join(input_dict[peerstr]['interestingdomains']))
    plist.append('pty "pptp ' + str(input_dict[peerstr]['vpnserver']) + ' --nolaunchpppd"')
    plist.append("name" + " " + str(input_dict[peerstr]['username']))
    plist.append("password" + " " + str(input_dict[peerstr]['password']))
    plist.append("unit"+ " " + str(re.findall(r'\d+', str(input_dict[peerstr]['interface']))[0]))
    plist.append("mtu" + " " + str(input_dict[peerstr]['mtu']))
    plist.append("mru" + " " + str(input_dict[peerstr]['mru']))
    plist.append("lcp-echo-failure" + " " + str(input_dict[peerstr]['lcp-echo-failure']))
    plist.append("lcp-echo-interval" + " " + str(input_dict[peerstr]['lcp-echo-interval']))
    plist.append("idle" + " " + str(input_dict[peerstr]['idle']))
    for option in input_dict[peerstr]['options']:
        plist.append(str(option))
    return plist

def parsepeerdata():
    my_dict = getpeerdata()
    peer_index = {}

    #Parse and display Peer Data
    for indexitem in my_dict:
        peer_options = []
        peer_detail = {}
        for listitem in my_dict[indexitem]:
            key = listitem.split(' ',1)
            if "#friendlyname" in key:
                peer_detail['friendlyname'] = listitem.split(' ',2)[1]
            if "#interestingdomains" in key:
                peer_detail['interestingdomains'] = listitem.split(' ',2)[1]
            elif "pty" in key:
                r = re.compile('pptp(.*?)--nolaunchpppd')
                m = r.search(listitem)
                vpnserverstr = m.group(1).strip()
                peer_detail['vpnserver'] = vpnserverstr
            elif "name" in key:
                peer_detail['username'] = listitem.split(' ',2)[1]
            elif "password" in key:
                peer_detail['password'] = listitem.split(' ',2)[1]
            elif "mtu" in key:
                peer_detail['mtu'] = listitem.split(' ',2)[1]
            elif "mru" in key:
                peer_detail['mru'] = listitem.split(' ',2)[1]
            elif "unit" in key:
                peer_detail['interface'] = "ppp" + listitem.split(' ',2)[1]
            elif "lcp-echo-failure" in key:
                peer_detail['lcp-echo-failure'] = listitem.split(' ',2)[1]
            elif "lcp-echo-interval" in key:
                peer_detail['lcp-echo-interval'] = listitem.split(' ',2)[1]
            elif "idle" in key:
                peer_detail['idle'] = listitem.split(' ',2)[1]
            else: #else these are not key value pairs, so must be otions
                peer_options.append(listitem)
        #peer_detail['interestingdomains'] = config[indexitem]['interestingdomains']
        peer_detail['options'] = peer_options
        peer_index[indexitem] = peer_detail
    return peer_index
    
def uptime():
 
     try:
         f = open( "/proc/uptime" )
         contents = f.read().split()
         f.close()
     except:
        return "Cannot open uptime file: /proc/uptime"
 
     total_seconds = float(contents[0])
 
     MINUTE  = 60
     HOUR    = MINUTE * 60
     DAY     = HOUR * 24
 
     days    = int( total_seconds / DAY )
     hours   = int( ( total_seconds % DAY ) / HOUR )
     minutes = int( ( total_seconds % HOUR ) / MINUTE )
     seconds = int( total_seconds % MINUTE )
 
     string = ""
     if days > 0:
         string += str(days) + (days == 1 and "day" or "days" ) + ", "
     if len(string) > 0 or hours > 0:
         string += str(hours) +  "h" + ", "
     if len(string) > 0 or minutes > 0:
         string += str(minutes) + "m" #+ ", "

     return string;

@app.route('/dsvrprocess', methods = ['POST'])
def dsvrprocess():
    if request.method == 'POST':
        allowedactions = ['start','stop','restart']
        action = str(request.form['action'])
        if action in allowedactions:
            command = "/etc/init.d/dsvr " + action + " &"
            os.system(command)
    return redirect(url_for('main')) 

@app.route('/modifypptp',methods = ['POST','GET'])
def modify_pptp():
    if request.method == 'POST':

        peer_file = str(request.form['peer'])
        unit = str(re.findall(r'\d+', request.form['peer']))

        updatepeer_details = {}
        updatepeer_index = {}
        updatepeer_options = []
        updatepeer_domainlist = []
        
        updatepeer_details['friendlyname'] = str(request.form['friendlyname'])
        updatepeer_details['vpnserver'] = str(request.form['vpnserver'])
        updatepeer_details['username'] = str(request.form['username'])
        updatepeer_details['password'] = str(request.form['password'])
        updatepeer_details['interface'] = str("ppp" + str(unit))
        updatepeer_details['mtu'] = str(request.form['mtu'])
        updatepeer_details['mru'] = str(request.form['mru'])
        updatepeer_details['lcp-echo-failure'] = str(request.form['lcp-echo-failure'])
        updatepeer_details['lcp-echo-interval'] = str(request.form['lcp-echo-interval'])
        updatepeer_details['idle'] = str(request.form['idle'])
        updatepeer_details['interestingdomains'] = []
        domainlist = [x.lower() for x in request.form.getlist("domainfield")]
        for domain in domainlist:
            if domain:
                updatepeer_details['interestingdomains'].append(domain)
        updatepeer_details['options'] = defaultpeeroptions
        updatepeer_index[peer_file] = updatepeer_details
        updatepeer_index[peer_file] = encodepeerfile(updatepeer_index, peer_file)
        writepeerfile(updatepeer_index[peer_file],peer_file)
        peer_data = parsepeerdata()
        return render_template('modifypptp.html',peerdata=peer_data,peerfile=peer_file)
    else:
        peer_data = parsepeerdata()
        peer_file = request.args.get('peer')
        return render_template('modifypptp.html',peerdata=peer_data,peerfile=peer_file)
    

@app.route('/delpptp',methods = ['POST','GET'])
def del_pptp(): 

    if request.method == 'POST':
        filename = "/etc/ppp/peers/" + str(request.form['peer'])
        if os.path.exists(filename):
            os.remove(filename)
            delinitdscript(str(request.form['peer']))
        return redirect(url_for('main'))        
    else:
        peer = str(request.args.get('peer'))
        return render_template('delpptp.html',peer=peer)

    
@app.route('/reboot',methods = ['POST','GET'])
def reboot(): 

    if request.method == 'POST':
        os.system('reboot')
        return redirect(url_for('main'))        
    else:
        return render_template('reboot.html')

        
    

@app.route('/addpptp',methods = ['POST','GET'])
def add_pptp():
    
    if request.method == 'POST':
        peer_data = parsepeerdata()

        #Find the first available interface number       
        existingintnum = []
        for index in peer_data:
            existingintnum.append(re.findall(r'\d+', str(peer_data[index]['interface'])))
        
        for num in range (0,10):
            if str(num) not in str(existingintnum):
               unit = num
               break

        #Create a new peer name
        peer_file = "db-ppp" + str(unit)

        newpeer_details = {}
        newpeer_index = {}
        newpeer_options = []
        
        newpeer_details['friendlyname'] = str(request.form['friendlyname'])
        newpeer_details['vpnserver'] = str(request.form['vpnserver'])
        newpeer_details['username'] = str(request.form['username'])
        newpeer_details['password'] = str(request.form['password'])
        newpeer_details['interface'] = str("ppp" + str(unit))
        newpeer_details['mtu'] = str(request.form['mtu'])
        newpeer_details['mru'] = str(request.form['mru'])
        newpeer_details['lcp-echo-failure'] = str(request.form['lcp-echo-failure'])
        newpeer_details['lcp-echo-interval'] = str(request.form['lcp-echo-interval'])
        newpeer_details['idle'] = str(request.form['idle'])
        newpeer_details['interestingdomains'] = []
        for domain in request.form.getlist("domainfield"):
          if domain:
              newpeer_details['interestingdomains'].append(domain)
        newpeer_details['options'] = defaultpeeroptions
        
        newpeer_index[peer_file] = newpeer_details
        newpeer_index[peer_file] = encodepeerfile(newpeer_index, peer_file)
        writepeerfile(newpeer_index[peer_file],peer_file)
        createinitdscript(peer_file)
        peer_data = parsepeerdata()
        return render_template('modifypptp.html',peerdata=peer_data,peerfile=peer_file)
    else:
        #peer_data = parsepeerdata()
        #usedinterfacenumbers = []
    
        #usedinterfacenumbers.append(re.findall(r'\d+', str(peer_data[index]['interface'])))
       
        return render_template('addpptp.html')

@app.route('/')
def main():
    ##Get and parse PPP peer data
    peer_data = parsepeerdata()

    #Get system uptime and format nicely
#    with open('/proc/uptime','r') as f:
#        uptime_seconds = float(f.readline().split()[0])
#        uptime_string = str(timedelta(seconds = uptime_seconds))
#        delay = timedelta(seconds = uptime_seconds)
#        if (delay.days > 0):
#            out = str(delay).replace(" days, ", ":")
#            out = str(delay).replace(" day, ", ":")
#        else:
#            out = "0:" + str(delay)
#        outAr = out.split(':')
#        outAr = ["%02d" % (int(float(x))) for x in outAr]
#        out   = ":".join(outAr)
#        uptime_string = str(out)

    uptime_string = uptime()

    #Testing updates INI file
    config = getdsvrini("dsvr.ini")
    
##    MEMORY
##    ------
##
##    % Available for apps etc - Linux will release mem from disk cache
##    free -m | awk '/Mem:/ { total=$2 } /buffers\/cache/ { used=$3 } END {print used/total*100}'
##
##    Total in MB
##    free -m | awk '/Mem:/ { total=$2 } END {print total}'
##    Used in MB
##    free -m | awk '/buffers\/cache/ { used=$3 } END {print used}'
##    Free in MB
##    free -m | awk '/buffers\/cache/ { free=$4 } END {print free}'
##
##    CPU
##    ---
##
##    CPU Load (5 min average)
##    uptime | awk '{print ($9)*100}'
##
##    CPU Load (15 min average)
##    uptime | awk '{print ($10)*100}'    
    
    #Determine CPU metric
    sysstats = []
    #CPU Load - 5 minute average
    #sysstats.append(commands.getstatusoutput("uptime | awk '{printf \"%.0f\",($9)}'"))
    #CPU Load - 15 minute average    
    #sysstats.append(commands.getstatusoutput("uptime | awk '{printf \"%.0f\",($10)}'"))
    sysstats.append(commands.getstatusoutput("top -n1 | awk '/Cpu\(s\):/ {print $2 + $4}'"))
    #Memory % Used
    sysstats.append(commands.getstatusoutput("free -m | awk '/Mem:/ { total=$2 } /buffers\/cache/ { used=$3 } END {printf \"%.0f\",used/total*100}'"))
    
    #Determine static IP interfaces - note this does check ppp interfaces, have to assume those are DHCP.
    staticints = []
    staticints  = commands.getstatusoutput("cat /etc/network/interfaces | grep 'inet static' | awk '{print $2}'")[1].split("\n")
    
    numofstaticroutes = {}
    
    for index in peer_data:
        unit = re.findall(r'\d+', str(peer_data[index]['interface']))[0]
        tablenum = int(unit) + 1
        numofstaticroutes[index] = commands.getstatusoutput("ip rule | grep 'lookup " + str(tablenum) + "' | wc -l")

    #Determine if the dsvr process is running
    dsvrstatus = 0
    if os.path.exists("/var/run/dsvr.pid"):
        pid = str(commands.getstatusoutput('cat /var/run/dsvr.pid')[1])
        psaxoutput = commands.getstatusoutput('ps ax | grep ' + pid + ' | grep -v grep')
        if 'dsvr' in psaxoutput[1]:
            dsvrstatus = 1

    return render_template('main.html',peerdata=peer_data,uptime=uptime_string,numofstaticroutes=numofstaticroutes,network=netifaces,config=config,dsvrstatus=dsvrstatus,sysstats=sysstats,staticints=staticints)

if __name__ == '__main__':
    defaultpeeroptions = ['lock','nodetach','noauth','refuse-eap','persist','require-mppe-128']
    app.run(host='0.0.0.0',debug=True,port=80)

########NEW FILE########
__FILENAME__ = dsvr
#!/usr/bin/env python
#
# DSVR (Domain Specific VPN Router)
# Copyright 2013 Darran Boyd
#
# dboyd13 [at @] gmail.com
#
# Licensed under the "Attribution-NonCommercial-ShareAlike" Vizsage
# Public License (the "License"). You may not use this file except
# in compliance with the License. Roughly speaking, non-commercial
# users may share and modify this code, but must give credit and 
# share improvements. However, for proper details please 
# read the full License, available at
#     http://vizsage.com/license/Vizsage-License-BY-NC-SA.html 
# and the handy reference for understanding the full license at 
#     http://vizsage.com/license/Vizsage-Deed-BY-NC-SA.html
#
# Unless required by applicable law or agreed to in writing, any
# software distributed under the License is distributed on an 
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, 
# either express or implied. See the License for the specific 
# language governing permissions and limitations under the License.
#
# Portions of code from the work of Peter Kacherginsky's dnschef - http://thesprawl.org/projects/dnschef/:
# iphelix [at] thesprawl.org.
#
# Copyright (C) 2013 Peter Kacherginsky
# All rights reserved.
#

from optparse import OptionParser,OptionGroup
from ConfigParser import ConfigParser
from lib.dnslib import *
from lib.IPy import IP

import threading, random, operator, time
import SocketServer, socket, sys, os, re
import tldextract,commands
import binascii

class DNSHandler():
           
    def parse(self,data):
        response = ""
    
        try:
            # Parse data as DNS        
            d = DNSRecord.parse(data)

        except Exception, e:
            print "[%s] %s: ERROR: %s" % (time.strftime("%H:%M:%S"), self.client_address[0], "invalid DNS request")

        # Proxy the request
        else:  
            extracted = tldextract.extract(str(d.q.qname))
            if 'addinterestingdomain-' in extracted.subdomain:
                addtointerface = extracted.subdomain.split('-',2)[1]
                domaintoadd = extracted.domain + "." + extracted.tld
                if domaintoadd not in interestingdomainsng[addtointerface]:
                    interestingdomainsng[addtointerface].append(domaintoadd)
                    print "[DB-I] Temporary added %s to interesting domains (until reboot/service restart), via %s" % (domaintoadd,addtointerface)
                else:
                    print "[DB-I] Ignoring request to add %s to interesting domains, already exists" % (domaintoadd)
            if isInterestingDomain(interestingdomainsng,str(d.q.qname))[0] == 1:
                nameserver_tuple = random.choice(db_dns_vpn_server).split('#')
            else:                                
                nameserver_tuple = random.choice(self.server.nameservers).split('#')
                
            response = self.proxyrequest(data,*nameserver_tuple)

            d = DNSRecord.parse(response)

            for item in d.rr:
                try: socket.inet_aton(str(item.rdata))
                except: 
                    isInteresting = []
                    isInteresting = isInterestingDomain(interestingdomainsng,str(d.q.qname))
                    if isInteresting[0] == 1:
                        interestingdomainsng[isInteresting[1]].append(str(item.rdata))
                else:
                    isInteresting = []
                    isInteresting = isInterestingDomain(interestingdomainsng,str(d.q.qname))
                    if isInteresting[0] == 1:
                        item.ttl=int(db_ttl_override_value) #TTL overide
                        if str(item.rdata) in existingroutes:
                            if options.verbose:    
                                print "[DB-I] %s | %s | %s | R~" % (str(d.q.qname),item.rdata,item.ttl) #DB Route exists, do nothing ("R~")
                        else:
                            if options.verbose:
                                print "[DB-I] %s | %s | %s | R+" % (str(d.q.qname),item.rdata,item.ttl) #DB Adding route ("R+")
                            interface=str(isInteresting[1])
                            existingroutes.append(str(item.rdata))
                            command = "sudo " + os.path.abspath(os.path.dirname(sys.argv[0])) + "/scripts/addroutetorule.sh " + str(item.rdata) + " " + str(interface)
                            os.system(command)
                    else:
                        if options.verbose:
                            print "[DB] %s | %s | %s | NR" % (str(d.q.qname),item.rdata,item.ttl) #DB No modifications ("NR")
            response = d.pack()

        return response         
    

    # Find appropriate ip address to use for a queried name. The function can 
    def findnametodns(self,qname,nametodns):
    
        # Split and reverse qname into components for matching.
        qnamelist = qname.split('.')
        qnamelist.reverse()
    
        # HACK: It is important to search the nametodns dictionary before iterating it so that
        # global matching ['*.*.*.*.*.*.*.*.*.*'] will match last. Use sorting for that.
        for domain,host in sorted(nametodns.iteritems(), key=operator.itemgetter(1)):
            domain = domain.split('.')
            domain.reverse()
            
            # Compare domains in reverse.
            for a,b in map(None,qnamelist,domain):
                if a != b and b != "*":
                    break
            else:
                # Could be a real IP or False if we are doing reverse matching with 'truedomains'
                return host
        else:
            return False
    
    # Obtain a response from a real DNS server.
    def proxyrequest(self, request, host, port="53"):
        reply = None
        try:
            if self.server.ipv6:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            sock.settimeout(3.0)

            # Send the proxy request to a randomly chosen DNS server
            sock.sendto(request, (host, int(port)))
            reply = sock.recv(1024)
            sock.close()

        except Exception, e:
            print "[!] Could not proxy request: %s" % e
        else:
	 return reply 

# UDP DNS Handler for incoming requests
class UDPHandler(DNSHandler, SocketServer.BaseRequestHandler):

    def handle(self):
        (data,socket) = self.request
        response = self.parse(data)
        
        if response:
            socket.sendto(response, self.client_address)

# TCP DNS Handler for incoming requests            
class TCPHandler(DNSHandler, SocketServer.BaseRequestHandler):

    def handle(self):
        data = self.request.recv(1024)
        
        # Remove the addition "length" parameter used in
        # TCP DNS protocol
        data = data[2:] 
        response = self.parse(data)
        
        if response:
            # Calculate and add the additional "length" parameter
            # used in TCP DNS protocol 
            length = binascii.unhexlify("%04x" % len(response))            
            self.request.sendall(length+response)            

class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):

    # Override SocketServer.UDPServer to add extra parameters
    def __init__(self, server_address, RequestHandlerClass, nametodns, nameservers, ipv6):
        self.nametodns  = nametodns
        self.nameservers = nameservers
        self.ipv6        = ipv6
        self.address_family = socket.AF_INET6 if self.ipv6 else socket.AF_INET

        SocketServer.UDPServer.__init__(self,server_address,RequestHandlerClass) 

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    
    # Override default value
    allow_reuse_address = True

    # Override SocketServer.TCPServer to add extra parameters
    def __init__(self, server_address, RequestHandlerClass, nametodns, nameservers, ipv6):
        self.nametodns  = nametodns
        self.nameservers = nameservers
        self.ipv6        = ipv6
        self.address_family = socket.AF_INET6 if self.ipv6 else socket.AF_INET

        SocketServer.TCPServer.__init__(self,server_address,RequestHandlerClass) 

def isInterestingDomain(input_dict, searchstr):
    for index in input_dict:
        for item in input_dict[index]:
            if item in searchstr:
                list = [1,index]
                return list
    list = [0]
    return list

   
def getpeerdata():
    peers = commands.getstatusoutput('ls /etc/ppp/peers/db* -1 | xargs -n1 basename')
    ppppeers_dict = {}
    if peers[0] == 0:

        for peerfile in peers[1].split('\n'):
            contents = []
            filefullpath = "/etc/ppp/peers/" + peerfile
            file = open(filefullpath)
            while 1:
                line = file.readline().rstrip("\r\n")
                if not line:
                    break
                contents.append(line)
            ppppeers_dict[peerfile] = contents
    return ppppeers_dict
     
# Initialize and start dsvr        
def start_cooking(interface, nametodns, nameservers, tcp=False, ipv6=False, port="53"):
    try:
        if tcp:
            print "[*] dsvr is running in TCP mode"
            server = ThreadedTCPServer((interface, int(port)), TCPHandler, nametodns, nameservers, ipv6)
        else:
            server = ThreadedUDPServer((interface, int(port)), UDPHandler, nametodns, nameservers, ipv6)

        # Start a thread with the server -- that thread will then start one
        # more threads for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        
        # Loop in the main thread
        while True: time.sleep(100)

    except (KeyboardInterrupt, SystemExit):
        server.shutdown()
        print "[*] dsvr is shutting down."
        sys.exit()
    
if __name__ == "__main__":

    header  = "##########################################\n"
    header += "#              dsvr v0.1                 #\n"
    header += "#                  darranboyd.com        #\n"
    header += "##########################################\n"
    

    # Parse command line arguments
    parser = OptionParser(usage = "dsvr.py [options]:\n" + header, description="" )
    
    fakegroup = OptionGroup(parser, "Fake DNS records:")

    fakegroup.add_option('--file', action="store", help="Specify a file containing a list of DOMAIN=IP pairs (one pair per line) used for DNS responses. For example: google.com=1.1.1.1 will force all queries to 'google.com' to be resolved to '1.1.1.1'. IPv6 addresses will be automatically detected. You can be even more specific by combining --file with other arguments. However, data obtained from the file will take precedence over others.")
   
    rungroup = OptionGroup(parser,"Optional runtime parameters.")
    rungroup.add_option("--nameservers", metavar="8.8.8.8#53 or 2001:4860:4860::8888", default='8.8.8.8', action="store", help='A comma separated list of alternative DNS servers to use with proxied requests. Nameservers can have either IP or IP#PORT format. A randomly selected server from the list will be used for proxy requests when provided with multiple servers. By default, the tool uses Google\'s public DNS server 8.8.8.8 when running in IPv4 mode and 2001:4860:4860::8888 when running in IPv6 mode.')
    rungroup.add_option("-i","--interface", metavar="127.0.0.1 or ::1", default="127.0.0.1", action="store", help='Define an interface to use for the DNS listener. By default, the tool uses 127.0.0.1 for IPv4 mode and ::1 for IPv6 mode.')
    rungroup.add_option("-t","--tcp", action="store_true", default=False, help="Use TCP DNS proxy instead of the default UDP.")
    rungroup.add_option("-6","--ipv6", action="store_true", default=False, help="Run in IPv6 mode.")
    rungroup.add_option("-p","--port", action="store", metavar="53", default="53", help='Port number to listen for DNS requests.')
    rungroup.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True, help="Don't show headers.")
    parser.add_option_group(rungroup)

    (options,args) = parser.parse_args()
 
    # Print program header
    if options.verbose:
        print header

    interestingdomains = []
    interestingdomainsng = {} #Dict to hold mapping from VPN int to interesting domains
    existingroutes = []
    db_dns_vpn_server = []
    db_dns_upstream_server = []
    
    # Main storage of domain filters
    # NOTE: RDMAP is a dictionary map of qtype strings to handling classses
    nametodns = dict()
    for qtype in RDMAP.keys():
        nametodns[qtype] = dict()
    
    # Notify user about alternative listening port
    if options.port != "53":
        print "[*] Listening on an alternative port %s" % options.port

    print "[*] dsvr started on interface: %s " % options.interface

    # External file definitions
    if options.file:
        config = ConfigParser()
        if "/" not in options.file:
            options.file = os.path.abspath(os.path.dirname(sys.argv[0])) + "/" + options.file
        config.read(options.file)
        print "[*] Using external config file: %s" % options.file
            
        db_dns_upstream_server.append(config.get('Global','dns-upstream-server'))
        print "[*] Using the following nameservers for un-interesting domains: %s" % ", ".join(db_dns_upstream_server)
        nameservers = db_dns_upstream_server
        db_dns_vpn_server.append(config.get('Global','dns-vpn-server'))
        print "[*] Using the following nameservers for interesting domains: %s" % ", ".join(db_dns_vpn_server)
        db_ttl_override_value = config.get('Global','ttl-override-value')
        print "[*] TTL overide value for interesting domains: %s" % db_ttl_override_value
                
        my_dict = getpeerdata()
                
        for indexitem in my_dict:
            peer_options = []
            peer_detail = {}
            for listitem in my_dict[indexitem]:
                key = listitem.split(' ',1)
                if "#interestingdomains" in key:
                    interestingdomainsng[indexitem] = listitem.split(' ',2)[1].split(",")
                    print "[*] Adding interesting domains to %s: %s" % (indexitem,listitem.split(' ',2)[1])
                
    # Clear existing IP Rules #DB
    for index in interestingdomainsng:
        tablenumstr = re.findall(r'\d+',index)
        tablenumint = int(tablenumstr[0]) + 1
        print "[*] Clearing existing IP Rules (Table %s)" % str(tablenumint)
        command = os.path.abspath(os.path.dirname(sys.argv[0])) + "/scripts/iprule-clear-table.sh " + str(tablenumint)
        os.system(command)
    
    # Add selected DNS servers to route via the VPN
    if interestingdomainsng:
        for interfacename in interestingdomainsng:
            intname = interfacename
            break 
 
        for item in db_dns_vpn_server:
            print "[*] Routing DNS server (%s) via first specificed int (%s)" % (item, intname)
            command = "sudo " + os.path.abspath(os.path.dirname(sys.argv[0])) + "/scripts/addroutetorule.sh " + item + " " + intname #DB
            os.system(command)
    
    # Launch dsvr
    start_cooking(interface=options.interface, nametodns=nametodns, nameservers=nameservers, tcp=options.tcp, ipv6=options.ipv6, port=options.port)


########NEW FILE########
__FILENAME__ = bimap

class Bimap(object):

    """

    A simple bi-directional map which returns either forward or
    reverse lookup of key through explicit 'lookup' method or 
    through __getattr__ or __getitem__. If the key is not found
    in either the forward/reverse dictionaries it is returned.

    >>> m = Bimap({1:'a',2:'b',3:'c'})
    >>> m[1]
    'a'
    >>> m.lookup('a')
    1
    >>> m.a
    1

    """

    def __init__(self,forward):
        self.forward = forward
        self.reverse = dict([(v,k) for (k,v) in forward.items()])

    def lookup(self,k,default=None):
        try:
            try:
                return self.forward[k]
            except KeyError:
                return self.reverse[k]
        except KeyError:
            if default:
                return default
            else:
                raise
    
    def __getitem__(self,k):
        return self.lookup(k,k)

    def __getattr__(self,k):
        return self.lookup(k,k)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = bit

"""
    Some basic bit mainpulation utilities
"""

FILTER=''.join([(len(repr(chr(x)))==3) and chr(x) or '.' for x in range(256)])

def hexdump(src, length=16, prefix=''):
    """
        Print hexdump of string

        >>> print hexdump("abcd\x00" * 4)
        0000  61 62 63 64 00 61 62 63  64 00 61 62 63 64 00 61  abcd.abc d.abcd.a
        0010  62 63 64 00                                       bcd. 
    """
    n = 0
    left = length / 2 
    right = length - left
    result= []
    while src:
        s,src = src[:length],src[length:]
        l,r = s[:left],s[left:]
        hexa = "%-*s" % (left*3,' '.join(["%02x"%ord(x) for x in l]))
        hexb = "%-*s" % (right*3,' '.join(["%02x"%ord(x) for x in r]))
        lf = l.translate(FILTER)
        rf = r.translate(FILTER)
        result.append("%s%04x  %s %s %s %s" % (prefix, n, hexa, hexb, lf, rf))
        n += length
    return "\n".join(result)

def get_bits(data,offset,bits=1):
    """
        Get specified bits from integer

        >>> bin(get_bits(0b0011100,2)
        0b1
        >>> bin(get_bits(0b0011100,0,4))
        0b1100
        
    """
    mask = ((1 << bits) - 1) << offset
    return (data & mask) >> offset 

def set_bits(data,value,offset,bits=1):
    """
        Set specified bits in integer

        >>> bin(set_bits(0,0b1010,0,4))
        0b1010
        >>> bin(set_bits(0,0b1010,3,4))
        0b1010000
    """
    mask = ((1 << bits) - 1) << offset
    clear = 0xffff ^ mask
    data = (data & clear) | ((value << offset) & mask)
    return data

def binary(n,count=16,reverse=False):
    """
        Display n in binary (only difference from built-in `bin` is
        that this function returns a fixed width string and can
        optionally be reversed

        >>> binary(6789)
        0001101010000101
        >>> binary(6789,8)
        10000101
        >>> binary(6789,reverse=True)
        1010000101011000

    """
    bits = [str((n >> y) & 1) for y in range(count-1, -1, -1)]
    if reverse:
        bits.reverse()
    return "".join(bits)


########NEW FILE########
__FILENAME__ = buffer

import struct

class Buffer(object):

    """
    A simple data buffer - supports packing/unpacking in struct format 

    >>> b = Buffer()
    >>> b.pack("!BHI",1,2,3)
    >>> b.offset
    7
    >>> b.append("0123456789")
    >>> b.offset
    17
    >>> b.offset = 0
    >>> b.unpack("!BHI")
    (1, 2, 3)
    >>> b.get(5)
    '01234'
    >>> b.get(5)
    '56789'
    >>> b.update(7,"2s","xx")
    >>> b.offset = 7
    >>> b.get(5)
    'xx234'
    """

    def __init__(self,data=""):
        """
            Initialise Buffer from data
        """
        self.data = data
        self.offset = 0

    def remaining(self):
        """
            Return bytes remaining
        """
        return len(self.data) - self.offset

    def get(self,len):
        """
            Gen len bytes at current offset (& increment offset)
        """
        start = self.offset
        end = self.offset + len
        self.offset += len
        return self.data[start:end]

    def pack(self,fmt,*args):
        """
            Pack data at end of data according to fmt (from struct) & increment
            offset
        """
        self.offset += struct.calcsize(fmt)
        self.data += struct.pack(fmt,*args)

    def append(self,s):
        """
            Append s to end of data & increment offset
        """
        self.offset += len(s)
        self.data += s

    def update(self,ptr,fmt,*args):
        """
            Modify data at offset `ptr` 
        """
        s = struct.pack(fmt,*args)
        self.data = self.data[:ptr] + s + self.data[ptr+len(s):]

    def unpack(self,fmt):
        """
            Unpack data at current offset according to fmt (from struct)
        """
        return struct.unpack(fmt,self.get(struct.calcsize(fmt)))

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = dns
# -*- coding: utf-8 -*-

import random,socket,struct 

from bit import get_bits,set_bits
from bimap import Bimap
from buffer import Buffer
from label import DNSLabel,DNSLabelError,DNSBuffer

QTYPE =  Bimap({1:'A', 2:'NS', 5:'CNAME', 6:'SOA', 12:'PTR', 15:'MX',
                16:'TXT', 17:'RP', 18:'AFSDB', 24:'SIG', 25:'KEY',
                28:'AAAA', 29:'LOC', 33:'SRV', 35:'NAPTR', 36:'KX',
                37:'CERT', 39:'DNAME', 41:'OPT', 42:'APL', 43:'DS',
                44:'SSHFP', 45:'IPSECKEY', 46:'RRSIG', 47:'NSEC',
                48:'DNSKEY', 49:'DHCID', 50:'NSEC3', 51:'NSEC3PARAM',
                55:'HIP', 99:'SPF', 249:'TKEY', 250:'TSIG', 251:'IXFR',
                252:'AXFR', 255:'*', 32768:'TA', 32769:'DLV'})
CLASS =  Bimap({ 1:'IN', 2:'CS', 3:'CH', 4:'Hesiod', 254:'None', 255:'*'})
QR =     Bimap({ 0:'QUERY', 1:'RESPONSE' })
RCODE =  Bimap({ 0:'None', 1:'Format Error', 2:'Server failure', 
                 3:'Name Error', 4:'Not Implemented', 5:'Refused', 6:'YXDOMAIN',
                 7:'YXRRSET', 8:'NXRRSET', 9:'NOTAUTH', 10:'NOTZONE'})
OPCODE = Bimap({ 0:'QUERY', 1:'IQUERY', 2:'STATUS', 5:'UPDATE' })

class DNSError(Exception):
    pass

class DNSRecord(object):

    """
    dnslib
    ------

    A simple library to encode/decode DNS wire-format packets. This was originally
    written for a custom nameserver.

    The key classes are:

        * DNSRecord (contains a DNSHeader and one or more DNSQuestion/DNSRR records)
        * DNSHeader 
        * DNSQuestion
        * RR (resource records)
        * RD (resource data - superclass for TXT,A,AAAA,MX,CNAME,PRT,SOA,NAPTR)
        * DNSLabel (envelope for a DNS label)

    The library has (in theory) very rudimentary support for EDNS0 options
    however this has not been tested due to a lack of data (anyone wanting
    to improve support or provide test data please raise an issue)

    Note: In version 0.3 the library was modified to use the DNSLabel class to
    support arbirary DNS labels (as specified in RFC2181) - and specifically
    to allow embedded '.'s. In most cases this is transparent (DNSLabel will
    automatically convert a domain label presented as a dot separated string &
    convert pack to this format when converted to a string) however to get the
    underlying label data (as a tuple) you need to access the DNSLabel.label
    attribute. To specifiy a label to the DNSRecord classes you can either pass
    a DNSLabel object or pass the elements as a list/tuple.

    To decode a DNS packet:

    >>> packet = 'd5ad818000010005000000000377777706676f6f676c6503636f6d0000010001c00c0005000100000005000803777777016cc010c02c0001000100000005000442f95b68c02c0001000100000005000442f95b63c02c0001000100000005000442f95b67c02c0001000100000005000442f95b93'.decode('hex')
    >>> d = DNSRecord.parse(packet)
    >>> print d
    <DNS Header: id=0xd5ad type=RESPONSE opcode=QUERY flags=RD,RA rcode=None q=1 a=5 ns=0 ar=0>
    <DNS Question: 'www.google.com' qtype=A qclass=IN>
    <DNS RR: 'www.google.com' rtype=CNAME rclass=IN ttl=5 rdata='www.l.google.com'>
    <DNS RR: 'www.l.google.com' rtype=A rclass=IN ttl=5 rdata='66.249.91.104'>
    <DNS RR: 'www.l.google.com' rtype=A rclass=IN ttl=5 rdata='66.249.91.99'>
    <DNS RR: 'www.l.google.com' rtype=A rclass=IN ttl=5 rdata='66.249.91.103'>
    <DNS RR: 'www.l.google.com' rtype=A rclass=IN ttl=5 rdata='66.249.91.147'>

    To create a DNS Request Packet:

    >>> d = DNSRecord(q=DNSQuestion("google.com"))
    >>> print d
    <DNS Header: id=... type=QUERY opcode=QUERY flags=RD rcode=None q=1 a=0 ns=0 ar=0>
    <DNS Question: 'google.com' qtype=A qclass=IN>
    >>> d.pack() 
    '...'

    >>> d = DNSRecord(q=DNSQuestion("google.com",QTYPE.MX))
    >>> print d
    <DNS Header: id=... type=QUERY opcode=QUERY flags=RD rcode=None q=1 a=0 ns=0 ar=0>
    <DNS Question: 'google.com' qtype=MX qclass=IN>
    >>> d.pack()
    '...'

    To create a DNS Response Packet:

    >>> d = DNSRecord(DNSHeader(qr=1,aa=1,ra=1),
    ...               q=DNSQuestion("abc.com"),
    ...               a=RR("abc.com",rdata=A("1.2.3.4")))
    >>> print d
    <DNS Header: id=... type=RESPONSE opcode=QUERY flags=AA,RD,RA rcode=None q=1 a=1 ns=0 ar=0>
    <DNS Question: 'abc.com' qtype=A qclass=IN>
    <DNS RR: 'abc.com' rtype=A rclass=IN ttl=0 rdata='1.2.3.4'>
    >>> d.pack()
    '...'

    To create a skeleton reply to a DNS query:

    >>> q = DNSRecord(q=DNSQuestion("abc.com",QTYPE.CNAME)) 
    >>> a = q.reply(data="xxx.abc.com")
    >>> print a
    <DNS Header: id=... type=RESPONSE opcode=QUERY flags=AA,RD,RA rcode=None q=1 a=1 ns=0 ar=0>
    <DNS Question: 'abc.com' qtype=CNAME qclass=IN>
    <DNS RR: 'abc.com' rtype=CNAME rclass=IN ttl=0 rdata='xxx.abc.com'>
    >>> a.pack()
    '...'

    Add additional RRs:

    >>> a.add_answer(RR('xxx.abc.com',QTYPE.A,rdata=A("1.2.3.4")))
    >>> print a
    <DNS Header: id=... type=RESPONSE opcode=QUERY flags=AA,RD,RA rcode=None q=1 a=2 ns=0 ar=0>
    <DNS Question: 'abc.com' qtype=CNAME qclass=IN>
    <DNS RR: 'abc.com' rtype=CNAME rclass=IN ttl=0 rdata='xxx.abc.com'>
    <DNS RR: 'xxx.abc.com' rtype=A rclass=IN ttl=0 rdata='1.2.3.4'>
    >>> a.pack()
    '...'

    Changelog:

        *   0.1     2010-09-19  Initial Release
        *   0.2     2010-09-22  Minor fixes
        *   0.3     2010-10-02  Add DNSLabel class to support arbitrary labels (embedded '.')
        *   0.4     2012-02-26  Merge with dbslib-circuits
        *   0.5     2012-09-13  Add support for RFC2136 DDNS updates
                                Patch provided by Wesley Shields <wxs@FreeBSD.org> - thanks
        *   0.6     2012-10-20  Basic AAAA support
        *   0.7     2012-10-20  Add initial EDNS0 support (untested)
        *   0.8     2012-11-04  Add support for NAPTR, Authority RR and additional RR
                                Patch provided by Stefan Andersson (https://bitbucket.org/norox) - thanks
        *   0.8.1   2012-11-05  Added NAPTR test case and fixed logic error
                                Patch provided by Stefan Andersson (https://bitbucket.org/norox) - thanks
        *   0.8.2   2012-11-11  Patch to fix IPv6 formatting
                                Patch provided by Torbjörn Lönnemark (https://bitbucket.org/tobbezz) - thanks

    License:

        *   BSD

    Author:

        *   Paul Chakravarti (paul.chakravarti@gmail.com)

    Master Repository/Issues:

        *   https://bitbucket.org/paulc/dnslib

    """

    version = "0.8.2"

    @classmethod
    def parse(cls,packet):
        """
            Parse DNS packet data and return DNSRecord instance
        """
        buffer = DNSBuffer(packet)
        header = DNSHeader.parse(buffer)
        questions = []
        rr = []
        ns = []
        ar = []
        for i in range(header.q):
            questions.append(DNSQuestion.parse(buffer))
        for i in range(header.a):
            rr.append(RR.parse(buffer))
        for i in range(header.ns):
            ns.append(RR.parse(buffer))
        for i in range(header.ar):
            ar.append(RR.parse(buffer))
        return cls(header,questions,rr,ns=ns,ar=ar)

    def __init__(self,header=None,questions=None,rr=None,q=None,a=None,ns=None,ar=None):
        """
            Create DNSRecord
        """
        self.header = header or DNSHeader()
        self.questions = questions or []
        self.rr = rr or []
        self.ns = ns or []
        self.ar = ar or []
        # Shortcuts to add a single Question/Answer
        if q:
            self.questions.append(q)
        if a:
            self.rr.append(a)
        self.set_header_qa()

    def reply(self,data="",ra=1,aa=1):
        answer = RDMAP.get(QTYPE[self.q.qtype],RD)(data)
        return DNSRecord(DNSHeader(id=self.header.id,bitmap=self.header.bitmap,qr=1,ra=ra,aa=aa),
                         q=self.q,
                         a=RR(self.q.qname,self.q.qtype,rdata=answer))


    def add_question(self,q):
        self.questions.append(q)
        self.set_header_qa()

    def add_answer(self,rr):
        self.rr.append(rr)
        self.set_header_qa()

    def add_ns(self,ns):
        self.ns.append(ns)
        self.set_header_qa()

    def add_ar(self,ar):
        self.ar.append(ar)
        self.set_header_qa()

    def set_header_qa(self):
        self.header.q = len(self.questions)
        self.header.a = len(self.rr)
        self.header.ns = len(self.ns)
        self.header.ar = len(self.ar)

    # Shortcut to get first question
    def get_q(self):
        return self.questions[0]
    q = property(get_q)

    # Shortcut to get first answer
    def get_a(self):
        return self.rr[0]
    a = property(get_a)

    def pack(self):
        self.set_header_qa()
        buffer = DNSBuffer()
        self.header.pack(buffer)
        for q in self.questions:
            q.pack(buffer)
        for rr in self.rr:
            rr.pack(buffer)
        for ns in self.ns:
            ns.pack(buffer)
        for ar in self.ar:
            ar.pack(buffer)
        return buffer.data

    def send(self,dest,port=53):
        sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.sendto(self.pack(),(dest,port))
        response,server = sock.recvfrom(8192)
        sock.close()
        return DNSRecord.parse(response)
        
    def __str__(self):
        sections = [ str(self.header) ]
        sections.extend([str(q) for q in self.questions])
        sections.extend([str(rr) for rr in self.rr])
        sections.extend([str(rr) for rr in self.ns])
        sections.extend([str(rr) for rr in self.ar])
        return "\n".join(sections)

class DNSHeader(object):

    @classmethod
    def parse(cls,buffer):
        (id,bitmap,q,a,ns,ar) = buffer.unpack("!HHHHHH")
        return cls(id,bitmap,q,a,ns,ar)

    def __init__(self,id=None,bitmap=None,q=0,a=0,ns=0,ar=0,**args):
        if id is None:
            self.id = random.randint(0,65535)
        else:
            self.id = id 
        if bitmap is None:
            self.bitmap = 0
            self.rd = 1
        else:
            self.bitmap = bitmap
        self.q = q
        self.a = a
        self.ns = ns
        self.ar = ar
        for k,v in args.items():
            if k.lower() == "qr":
                self.qr = v
            elif k.lower() == "opcode":
                self.opcode = v
            elif k.lower() == "aa":
                self.aa = v
            elif k.lower() == "tc":
                self.tc = v
            elif k.lower() == "rd":
                self.rd = v
            elif k.lower() == "ra":
                self.ra = v
            elif k.lower() == "rcode":
                self.rcode = v
    
    def get_qr(self):
        return get_bits(self.bitmap,15)

    def set_qr(self,val):
        self.bitmap = set_bits(self.bitmap,val,15)

    qr = property(get_qr,set_qr)

    def get_opcode(self):
        return get_bits(self.bitmap,11,4)

    def set_opcode(self,val):
        self.bitmap = set_bits(self.bitmap,val,11,4)

    opcode = property(get_opcode,set_opcode)

    def get_aa(self):
        return get_bits(self.bitmap,10)

    def set_aa(self,val):
        self.bitmap = set_bits(self.bitmap,val,10)

    aa = property(get_aa,set_aa)
        
    def get_tc(self):
        return get_bits(self.bitmap,9)

    def set_tc(self,val):
        self.bitmap = set_bits(self.bitmap,val,9)

    tc = property(get_tc,set_tc)
        
    def get_rd(self):
        return get_bits(self.bitmap,8)

    def set_rd(self,val):
        self.bitmap = set_bits(self.bitmap,val,8)

    rd = property(get_rd,set_rd)
        
    def get_ra(self):
        return get_bits(self.bitmap,7)

    def set_ra(self,val):
        self.bitmap = set_bits(self.bitmap,val,7)

    ra = property(get_ra,set_ra)

    def get_rcode(self):
        return get_bits(self.bitmap,0,4)

    def set_rcode(self,val):
        self.bitmap = set_bits(self.bitmap,val,0,4)

    rcode = property(get_rcode,set_rcode)

    def pack(self,buffer):
        buffer.pack("!HHHHHH",self.id,self.bitmap,self.q,self.a,self.ns,self.ar)

    def __str__(self):
        f = [ self.aa and 'AA', 
              self.tc and 'TC', 
              self.rd and 'RD', 
              self.ra and 'RA' ] 
        if OPCODE[self.opcode] == 'UPDATE':
            f1='zo'
            f2='pr'
            f3='up'
            f4='ad'
        else:
            f1='q'
            f2='a'
            f3='ns'
            f4='ar'
        return "<DNS Header: id=0x%x type=%s opcode=%s flags=%s " \
                            "rcode=%s %s=%d %s=%d %s=%d %s=%d>" % ( 
                    self.id,
                    QR[self.qr],
                    OPCODE[self.opcode],
                    ",".join(filter(None,f)),
                    RCODE[self.rcode],
                    f1, self.q, f2, self.a, f3, self.ns, f4, self.ar )

class DNSQuestion(object):
    
    @classmethod
    def parse(cls,buffer):
        qname = buffer.decode_name()
        qtype,qclass = buffer.unpack("!HH")
        return cls(qname,qtype,qclass)

    def __init__(self,qname=[],qtype=1,qclass=1):
        self.qname = qname
        self.qtype = qtype
        self.qclass = qclass

    def set_qname(self,qname):
        if isinstance(qname,DNSLabel):
            self._qname = qname
        else:
            self._qname = DNSLabel(qname)

    def get_qname(self):
        return self._qname

    qname = property(get_qname,set_qname)

    def pack(self,buffer):
        buffer.encode_name(self.qname)
        buffer.pack("!HH",self.qtype,self.qclass)

    def __str__(self):
        return "<DNS Question: %r qtype=%s qclass=%s>" % (
                    self.qname, QTYPE[self.qtype], CLASS[self.qclass])
            
class EDNSOption(object):

    def __init__(self,code,data):
        self.code = code
        self.data = data

    def __str__(self):
        return "<EDNS Option: Code=%d Data=%s>" % (self.code,self.data)

class RR(object):

    @classmethod
    def parse(cls,buffer):
        rname = buffer.decode_name()
        rtype,rclass,ttl,rdlength = buffer.unpack("!HHIH")
        if rtype == QTYPE.OPT:
            options = []
            option_buffer = Buffer(buffer.get(rdlength))
            while option_buffer.remaining() > 4:
                code,length = option_buffer.unpack("!HH")
                data = option_buffer.get(length)
                options.append(EDNSOption(code,data))
            rdata = options
        else:
            rdata = RDMAP.get(QTYPE[rtype],RD).parse(buffer,rdlength)
        return cls(rname,rtype,rclass,ttl,rdata)

    def __init__(self,rname=[],rtype=1,rclass=1,ttl=0,rdata=None):
        self.rname = rname
        self.rtype = rtype
        self.rclass = rclass
        self.ttl = ttl
        self.rdata = rdata

    def set_rname(self,rname):
        if isinstance(rname,DNSLabel):
            self._rname = rname
        else:
            self._rname = DNSLabel(rname)

    def get_rname(self):
        return self._rname

    rname = property(get_rname,set_rname)

    def pack(self,buffer):
        buffer.encode_name(self.rname)
        buffer.pack("!HHI",self.rtype,self.rclass,self.ttl)
        rdlength_ptr = buffer.offset
        buffer.pack("!H",0)
        start = buffer.offset
        self.rdata.pack(buffer)
        end = buffer.offset
        buffer.update(rdlength_ptr,"!H",end-start)

    def __str__(self):
        return "<DNS RR: %r rtype=%s rclass=%s ttl=%d rdata='%s'>" % (
                    self.rname, QTYPE[self.rtype], CLASS[self.rclass], 
                    self.ttl, self.rdata)

class RD(object):

    @classmethod
    def parse(cls,buffer,length):
        data = buffer.get(length)
        return cls(data)

    def __init__(self,data=""):
        self.data = data

    def pack(self,buffer):
        buffer.append(self.data)

    def __str__(self):
        return '%s' % self.data

class TXT(RD):

    @classmethod
    def parse(cls,buffer,length):
        (txtlength,) = buffer.unpack("!B")
        # First byte is TXT length (not in RFC?)
        if txtlength < length:
            data = buffer.get(txtlength)
        else:
            raise DNSError("Invalid TXT record: length (%d) > RD length (%d)" % 
                                    (txtlength,length))
        return cls(data)

    def pack(self,buffer):
        if len(self.data) > 255:
            raise DNSError("TXT record too long: %s" % self.data)
        buffer.pack("!B",len(self.data))
        buffer.append(self.data)

class A(RD):

    @classmethod
    def parse(cls,buffer,length):
        ip = buffer.unpack("!BBBB")
        data = "%d.%d.%d.%d" % ip
        return cls(data)

    def pack(self,buffer):
        buffer.pack("!BBBB",*map(int,self.data.split(".")))

class AAAA(RD):

    """
        Basic support for AAAA record - assumes IPv6 address data is presented
        as a simple tuple of 16 bytes
    """
 
    @classmethod
    def parse(cls,buffer,length):
        data = buffer.unpack("!16B")
        return cls(data)
 
    def pack(self,buffer):
        buffer.pack("!16B",*self.data)

    def __str__(self):
        hexes = map('{:02x}'.format, self.data)
        return ':'.join([''.join(hexes[i:i+2]) for i in xrange(0, len(hexes), 2)])

class MX(RD):

    @classmethod
    def parse(cls,buffer,length):
        (preference,) = buffer.unpack("!H")
        mx = buffer.decode_name()
        return cls(mx,preference)

    def __init__(self,mx=[],preference=10):
        self.mx = mx
        self.preference = preference

    def set_mx(self,mx):
        if isinstance(mx,DNSLabel):
            self._mx = mx
        else:
            self._mx = DNSLabel(mx)

    def get_mx(self):
        return self._mx

    mx = property(get_mx,set_mx)

    def pack(self,buffer):
        buffer.pack("!H",self.preference)
        buffer.encode_name(self.mx)
        
    def __str__(self):
        return "%d:%s" % (self.preference,self.mx)

class CNAME(RD):
        
    @classmethod
    def parse(cls,buffer,length):
        label = buffer.decode_name()
        return cls(label)

    def __init__(self,label=[]):
        self.label = label

    def set_label(self,label):
        if isinstance(label,DNSLabel):
            self._label = label
        else:
            self._label = DNSLabel(label)

    def get_label(self):
        return self._label

    label = property(get_label,set_label)

    def pack(self,buffer):
        buffer.encode_name(self.label)

    def __str__(self):
        return "%s" % (self.label)

class PTR(CNAME):
    pass

class NS(CNAME):
    pass

class SOA(RD):
        
    @classmethod
    def parse(cls,buffer,length):
        mname = buffer.decode_name()
        rname = buffer.decode_name()
        times = buffer.unpack("!IIIII")
        return cls(mname,rname,times)

    def __init__(self,mname=[],rname=[],times=None):
        self.mname = mname
        self.rname = rname
        self.times = times or (0,0,0,0,0)

    def set_mname(self,mname):
        if isinstance(mname,DNSLabel):
            self._mname = mname
        else:
            self._mname = DNSLabel(mname)

    def get_mname(self):
        return self._mname

    mname = property(get_mname,set_mname)

    def set_rname(self,rname):
        if isinstance(rname,DNSLabel):
            self._rname = rname
        else:
            self._rname = DNSLabel(rname)

    def get_rname(self):
        return self._rname

    rname = property(get_rname,set_rname)

    def pack(self,buffer):
        buffer.encode_name(self.mname)
        buffer.encode_name(self.rname)
        buffer.pack("!IIIII", *self.times)

    def __str__(self):
        return "%s:%s:%s" % (self.mname,self.rname,":".join(map(str,self.times)))

class NAPTR(RD):

    def __init__(self,order,preference,flags,service,regexp,replacement=None):
        self.order = order
        self.preference = preference
        self.flags = flags
        self.service = service
        self.regexp = regexp
        self.replacement = replacement or DNSLabel([])

    @classmethod
    def parse(cls, buffer, length):
        order, preference = buffer.unpack('!HH')
        (length,) = buffer.unpack('!B')
        flags = buffer.get(length)
        (length,) = buffer.unpack('!B')
        service = buffer.get(length)
        (length,) = buffer.unpack('!B')
        regexp = buffer.get(length)
        replacement = buffer.decode_name()
        return cls(order, preference, flags, service, regexp, replacement)

    def pack(self, buffer):
        buffer.pack('!HH', self.order, self.preference)
        buffer.pack('!B', len(self.flags))
        buffer.append(self.flags)
        buffer.pack('!B', len(self.service))
        buffer.append(self.service)
        buffer.pack('!B', len(self.regexp))
        buffer.append(self.regexp)
        buffer.encode_name(self.replacement)

    def __str__(self):
        return '%d %d "%s" "%s" "%s" %s' %(
            self.order,self.preference,self.flags,
            self.service,self.regexp,self.replacement or '.'
        )

RDMAP = { 'CNAME':CNAME, 'A':A, 'AAAA':AAAA, 'TXT':TXT, 'MX':MX, 
          'PTR':PTR, 'SOA':SOA, 'NS':NS, 'NAPTR': NAPTR}

def test_unpack(s):
    """
    Test decoding with sample DNS packets captured from Wireshark

    >>> def unpack(s):
    ...     d = DNSRecord.parse(s.decode('hex'))
    ...     print d

    Standard query A www.google.com
        >>> unpack('d5ad010000010000000000000377777706676f6f676c6503636f6d0000010001')
        <DNS Header: id=0xd5ad type=QUERY opcode=QUERY flags=RD rcode=None q=1 a=0 ns=0 ar=0>
        <DNS Question: 'www.google.com' qtype=A qclass=IN>

    Standard query response CNAME www.l.google.com A 66.249.91.104 A 66.249.91.99 A 66.249.91.103 A 66.249.91.147
        >>> unpack('d5ad818000010005000000000377777706676f6f676c6503636f6d0000010001c00c0005000100000005000803777777016cc010c02c0001000100000005000442f95b68c02c0001000100000005000442f95b63c02c0001000100000005000442f95b67c02c0001000100000005000442f95b93')
        <DNS Header: id=0xd5ad type=RESPONSE opcode=QUERY flags=RD,RA rcode=None q=1 a=5 ns=0 ar=0>
        <DNS Question: 'www.google.com' qtype=A qclass=IN>
        <DNS RR: 'www.google.com' rtype=CNAME rclass=IN ttl=5 rdata='www.l.google.com'>
        <DNS RR: 'www.l.google.com' rtype=A rclass=IN ttl=5 rdata='66.249.91.104'>
        <DNS RR: 'www.l.google.com' rtype=A rclass=IN ttl=5 rdata='66.249.91.99'>
        <DNS RR: 'www.l.google.com' rtype=A rclass=IN ttl=5 rdata='66.249.91.103'>
        <DNS RR: 'www.l.google.com' rtype=A rclass=IN ttl=5 rdata='66.249.91.147'>

    Standard query MX google.com
        >>> unpack('95370100000100000000000006676f6f676c6503636f6d00000f0001')
        <DNS Header: id=0x9537 type=QUERY opcode=QUERY flags=RD rcode=None q=1 a=0 ns=0 ar=0>
        <DNS Question: 'google.com' qtype=MX qclass=IN>

    Standard query response MX 10 smtp2.google.com MX 10 smtp3.google.com MX 10 smtp4.google.com MX 10 smtp1.google.com
        >>> unpack('95378180000100040000000006676f6f676c6503636f6d00000f0001c00c000f000100000005000a000a05736d747032c00cc00c000f000100000005000a000a05736d747033c00cc00c000f000100000005000a000a05736d747034c00cc00c000f000100000005000a000a05736d747031c00c')
        <DNS Header: id=0x9537 type=RESPONSE opcode=QUERY flags=RD,RA rcode=None q=1 a=4 ns=0 ar=0>
        <DNS Question: 'google.com' qtype=MX qclass=IN>
        <DNS RR: 'google.com' rtype=MX rclass=IN ttl=5 rdata='10:smtp2.google.com'>
        <DNS RR: 'google.com' rtype=MX rclass=IN ttl=5 rdata='10:smtp3.google.com'>
        <DNS RR: 'google.com' rtype=MX rclass=IN ttl=5 rdata='10:smtp4.google.com'>
        <DNS RR: 'google.com' rtype=MX rclass=IN ttl=5 rdata='10:smtp1.google.com'>

    Standard query PTR 103.91.249.66.in-addr.arpa
        >>> unpack('b38001000001000000000000033130330239310332343902363607696e2d61646472046172706100000c0001')
        <DNS Header: id=0xb380 type=QUERY opcode=QUERY flags=RD rcode=None q=1 a=0 ns=0 ar=0>
        <DNS Question: '103.91.249.66.in-addr.arpa' qtype=PTR qclass=IN>

    Standard query response PTR ik-in-f103.google.com
        >>> unpack('b38081800001000100000000033130330239310332343902363607696e2d61646472046172706100000c0001c00c000c00010000000500170a696b2d696e2d6631303306676f6f676c6503636f6d00')
        <DNS Header: id=0xb380 type=RESPONSE opcode=QUERY flags=RD,RA rcode=None q=1 a=1 ns=0 ar=0>
        <DNS Question: '103.91.249.66.in-addr.arpa' qtype=PTR qclass=IN>
        <DNS RR: '103.91.249.66.in-addr.arpa' rtype=PTR rclass=IN ttl=5 rdata='ik-in-f103.google.com'>

    Standard query TXT google.com

        >>> unpack('c89f0100000100000000000006676f6f676c6503636f6d0000100001')
        <DNS Header: id=0xc89f type=QUERY opcode=QUERY flags=RD rcode=None q=1 a=0 ns=0 ar=0>
        <DNS Question: 'google.com' qtype=TXT qclass=IN>

    Standard query response TXT
        >>> unpack('c89f8180000100010000000006676f6f676c6503636f6d0000100001c00c0010000100000005002a29763d7370663120696e636c7564653a5f6e6574626c6f636b732e676f6f676c652e636f6d207e616c6c')
        <DNS Header: id=0xc89f type=RESPONSE opcode=QUERY flags=RD,RA rcode=None q=1 a=1 ns=0 ar=0>
        <DNS Question: 'google.com' qtype=TXT qclass=IN>
        <DNS RR: 'google.com' rtype=TXT rclass=IN ttl=5 rdata='v=spf1 include:_netblocks.google.com ~all'>

    Standard query SOA google.com
        >>> unpack('28fb0100000100000000000006676f6f676c6503636f6d0000060001')
        <DNS Header: id=0x28fb type=QUERY opcode=QUERY flags=RD rcode=None q=1 a=0 ns=0 ar=0>
        <DNS Question: 'google.com' qtype=SOA qclass=IN>

    Standard query response SOA ns1.google.com
        >>> unpack('28fb8180000100010000000006676f6f676c6503636f6d0000060001c00c00060001000000050026036e7331c00c09646e732d61646d696ec00c77b1566d00001c2000000708001275000000012c')
        <DNS Header: id=0x28fb type=RESPONSE opcode=QUERY flags=RD,RA rcode=None q=1 a=1 ns=0 ar=0>
        <DNS Question: 'google.com' qtype=SOA qclass=IN>
        <DNS RR: 'google.com' rtype=SOA rclass=IN ttl=5 rdata='ns1.google.com:dns-admin.google.com:2008110701:7200:1800:1209600:300'>

    Standard query response NAPTR sip2sip.info
        >>> unpack('740481800001000300000000077369703273697004696e666f0000230001c00c0023000100000c940027001e00640173075349502b44325500045f736970045f756470077369703273697004696e666f00c00c0023000100000c940027000a00640173075349502b44325400045f736970045f746370077369703273697004696e666f00c00c0023000100000c94002900140064017308534950532b44325400055f73697073045f746370077369703273697004696e666f00')
        <DNS Header: id=0x7404 type=RESPONSE opcode=QUERY flags=RD,RA rcode=None q=1 a=3 ns=0 ar=0>
        <DNS Question: 'sip2sip.info' qtype=NAPTR qclass=IN>
        <DNS RR: 'sip2sip.info' rtype=NAPTR rclass=IN ttl=3220 rdata='30 100 "s" "SIP+D2U" "" _sip._udp.sip2sip.info'>
        <DNS RR: 'sip2sip.info' rtype=NAPTR rclass=IN ttl=3220 rdata='10 100 "s" "SIP+D2T" "" _sip._tcp.sip2sip.info'>
        <DNS RR: 'sip2sip.info' rtype=NAPTR rclass=IN ttl=3220 rdata='20 100 "s" "SIPS+D2T" "" _sips._tcp.sip2sip.info'>

    Standard query response NAPTR 0.0.0.0.1.1.1.3.9.3.0.1.8.7.8.e164.org
        >>> unpack('aef0818000010001000000000130013001300130013101310131013301390133013001310138013701380465313634036f72670000230001c00c002300010000a6a300320064000a0175074532552b53495022215e5c2b3f282e2a2924217369703a5c5c31406677642e70756c7665722e636f6d2100')
        <DNS Header: id=0xaef0 type=RESPONSE opcode=QUERY flags=RD,RA rcode=None q=1 a=1 ns=0 ar=0>
        <DNS Question: '0.0.0.0.1.1.1.3.9.3.0.1.8.7.8.e164.org' qtype=NAPTR qclass=IN>
        <DNS RR: '0.0.0.0.1.1.1.3.9.3.0.1.8.7.8.e164.org' rtype=NAPTR rclass=IN ttl=42659 rdata='100 10 "u" "E2U+SIP" "!^\+?(.*)$!sip:\\\\1@fwd.pulver.com!" .'>
    """
    pass


if __name__ == '__main__':
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

########NEW FILE########
__FILENAME__ = label

import types
from bit import get_bits,set_bits
from buffer import Buffer

class DNSLabelError(Exception):
    pass

class DNSLabel(object):

    """
    Container for DNS label supporting arbitary label chars (including '.')

    >>> l1 = DNSLabel("aaa.bbb.ccc")
    >>> l2 = DNSLabel(["aaa","bbb","ccc"])
    >>> l1 == l2
    True
    >>> x = { l1 : 1 }
    >>> x[l1]
    1
    >>> print l1
    aaa.bbb.ccc
    >>> l1
    'aaa.bbb.ccc'

    """
    def __init__(self,label):
        """
            Create label instance from elements in list/tuple. If label
            argument is a string split into components (separated by '.')
        """
        if type(label) in (types.ListType,types.TupleType):
            self.label = tuple(label)
        else:
            self.label = tuple(label.split("."))

    def __str__(self):
        return ".".join(self.label)

    def __repr__(self):
        return "%r" % ".".join(self.label)

    def __hash__(self):
        return hash(self.label)

    def __eq__(self,other):
        return self.label == other.label

    def __len__(self):
        return len(".".join(self.label))

class DNSBuffer(Buffer):

    """
    Extends Buffer to provide DNS name encoding/decoding (with caching)

    >>> b = DNSBuffer()
    >>> b.encode_name("aaa.bbb.ccc")
    >>> b.encode_name("xxx.yyy.zzz")
    >>> b.encode_name("zzz.xxx.bbb.ccc")
    >>> b.encode_name("aaa.xxx.bbb.ccc")
    >>> b.data.encode("hex")
    '036161610362626203636363000378787803797979037a7a7a00037a7a7a03787878c00403616161c01e'
    >>> b.offset = 0
    >>> b.decode_name()
    'aaa.bbb.ccc'
    >>> b.decode_name()
    'xxx.yyy.zzz'
    >>> b.decode_name()
    'zzz.xxx.bbb.ccc'
    >>> b.decode_name()
    'aaa.xxx.bbb.ccc'

    >>> b = DNSBuffer()
    >>> b.encode_name(['a.aa','b.bb','c.cc'])
    >>> b.offset = 0
    >>> len(b.decode_name().label)
    3
    """

    def __init__(self,data=""):
        """
            Add 'names' dict to cache stored labels
        """
        super(DNSBuffer,self).__init__(data)
        self.names = {}

    def decode_name(self):
        """
            Decode label at current offset in buffer (following pointers
            to cached elements where necessary)
        """
        label = []
        done = False
        while not done:
            (len,) = self.unpack("!B")
            if get_bits(len,6,2) == 3:
                # Pointer
                self.offset -= 1
                pointer = get_bits(self.unpack("!H")[0],0,14)
                save = self.offset
                self.offset = pointer
                label.extend(self.decode_name().label)
                self.offset = save
                done = True
            else:
                if len > 0:
                    label.append(self.get(len))
                else:
                    done = True
        return DNSLabel(label)

    def encode_name(self,name):
        """
            Encode label and store at end of buffer (compressing
            cached elements where needed) and store elements
            in 'names' dict
        """
        if not isinstance(name,DNSLabel):
            name = DNSLabel(name)
        if len(name) > 253:
            raise DNSLabelError("Domain label too long: %r" % name)
        name = list(name.label)
        while name:
            if self.names.has_key(tuple(name)):
                # Cached - set pointer
                pointer = self.names[tuple(name)]
                pointer = set_bits(pointer,3,14,2)
                self.pack("!H",pointer)
                return
            else:
                self.names[tuple(name)] = self.offset
                element = name.pop(0)
                if len(element) > 63:
                    raise DNSLabelError("Label component too long: %r" % element)
                self.pack("!B",len(element))
                self.append(element)
        self.append("\x00")

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = IPy
"""
IPy - class and tools for handling of IPv4 and IPv6 addresses and networks.
See README file for learn how to use IPy.

Further Information might be available at:
https://github.com/haypo/python-ipy
"""

__version__ = '0.75'

import sys
import types

# Definition of the Ranges for IPv4 IPs
# this should include www.iana.org/assignments/ipv4-address-space
# and www.iana.org/assignments/multicast-addresses
IPv4ranges = {
    '0':                'PUBLIC',   # fall back
    '00000000':         'PRIVATE',  # 0/8
    '00001010':         'PRIVATE',  # 10/8
    '01111111':         'PRIVATE',  # 127.0/8
    '1':                'PUBLIC',   # fall back
    '1010100111111110': 'PRIVATE',  # 169.254/16
    '101011000001':     'PRIVATE',  # 172.16/12
    '1100000010101000': 'PRIVATE',  # 192.168/16
    '111':              'RESERVED'  # 224/3
    }

# Definition of the Ranges for IPv6 IPs
# http://www.iana.org/assignments/ipv6-address-space/
# http://www.iana.org/assignments/ipv6-unicast-address-assignments/
# http://www.iana.org/assignments/ipv6-multicast-addresses/
IPv6ranges = {
    '00000000'                                      : 'RESERVED',               # ::/8
    '0' * 96                                        : 'RESERVED',               # ::/96 Formerly IPV4COMP [RFC4291]
    '0' * 128                                       : 'UNSPECIFIED',            # ::/128
    '0' * 127 + '1'                                 : 'LOOPBACK',               # ::1/128
    '0' * 80 + '1' * 16                             : 'IPV4MAP',                # ::ffff:0:0/96
    '00000000011001001111111110011011' + '0' * 64   : 'WKP46TRANS',             # 0064:ff9b::/96 Well-Known-Prefix [RFC6052]
    '00000001'                                      : 'UNASSIGNED',             # 0100::/8
    '0000001'                                       : 'RESERVED',               # 0200::/7 Formerly NSAP [RFC4048]
    '0000010'                                       : 'RESERVED',               # 0400::/7 Formerly IPX [RFC3513]
    '0000011'                                       : 'RESERVED',               # 0600::/7
    '00001'                                         : 'RESERVED',               # 0800::/5
    '0001'                                          : 'RESERVED',               # 1000::/4
    '001'                                           : 'GLOBAL-UNICAST',         # 2000::/3 [RFC4291]
    '00100000000000010000000'                       : 'SPECIALPURPOSE',         # 2001::/23 [RFC4773]
    '00100000000000010000000000000000'              : 'TEREDO',                 # 2001::/32 [RFC4380]
    '00100000000000010000000000000010' + '0' * 16   : 'BMWG',                   # 2001:0002::/48 Benchmarking [RFC5180]
    '0010000000000001000000000001'                  : 'ORCHID',                 # 2001:0010::/28 (Temp until 2014-03-21) [RFC4843]
    '00100000000000010000001'                       : 'ALLOCATED APNIC',        # 2001:0200::/23
    '00100000000000010000010'                       : 'ALLOCATED ARIN',         # 2001:0400::/23
    '00100000000000010000011'                       : 'ALLOCATED RIPE NCC',     # 2001:0600::/23
    '00100000000000010000100'                       : 'ALLOCATED RIPE NCC',     # 2001:0800::/23
    '00100000000000010000101'                       : 'ALLOCATED RIPE NCC',     # 2001:0a00::/23
    '00100000000000010000110'                       : 'ALLOCATED APNIC',        # 2001:0c00::/23
    '00100000000000010000110110111000'              : 'DOCUMENTATION',          # 2001:0db8::/32 [RFC3849]
    '00100000000000010000111'                       : 'ALLOCATED APNIC',        # 2001:0e00::/23
    '00100000000000010001001'                       : 'ALLOCATED LACNIC',       # 2001:1200::/23
    '00100000000000010001010'                       : 'ALLOCATED RIPE NCC',     # 2001:1400::/23
    '00100000000000010001011'                       : 'ALLOCATED RIPE NCC',     # 2001:1600::/23
    '00100000000000010001100'                       : 'ALLOCATED ARIN',         # 2001:1800::/23
    '00100000000000010001101'                       : 'ALLOCATED RIPE NCC',     # 2001:1a00::/23
    '0010000000000001000111'                        : 'ALLOCATED RIPE NCC',     # 2001:1c00::/22
    '00100000000000010010'                          : 'ALLOCATED RIPE NCC',     # 2001:2000::/20
    '001000000000000100110'                         : 'ALLOCATED RIPE NCC',     # 2001:3000::/21
    '0010000000000001001110'                        : 'ALLOCATED RIPE NCC',     # 2001:3800::/22
    '0010000000000001001111'                        : 'RESERVED',               # 2001:3c00::/22 Possible future allocation to RIPE NCC
    '00100000000000010100000'                       : 'ALLOCATED RIPE NCC',     # 2001:4000::/23
    '00100000000000010100001'                       : 'ALLOCATED AFRINIC',      # 2001:4200::/23
    '00100000000000010100010'                       : 'ALLOCATED APNIC',        # 2001:4400::/23
    '00100000000000010100011'                       : 'ALLOCATED RIPE NCC',     # 2001:4600::/23
    '00100000000000010100100'                       : 'ALLOCATED ARIN',         # 2001:4800::/23
    '00100000000000010100101'                       : 'ALLOCATED RIPE NCC',     # 2001:4a00::/23
    '00100000000000010100110'                       : 'ALLOCATED RIPE NCC',     # 2001:4c00::/23
    '00100000000000010101'                          : 'ALLOCATED RIPE NCC',     # 2001:5000::/20
    '0010000000000001100'                           : 'ALLOCATED APNIC',        # 2001:8000::/19
    '00100000000000011010'                          : 'ALLOCATED APNIC',        # 2001:a000::/20
    '00100000000000011011'                          : 'ALLOCATED APNIC',        # 2001:b000::/20
    '0010000000000010'                              : '6TO4',                   # 2002::/16 "6to4" [RFC3056]
    '001000000000001100'                            : 'ALLOCATED RIPE NCC',     # 2003::/18
    '001001000000'                                  : 'ALLOCATED APNIC',        # 2400::/12
    '001001100000'                                  : 'ALLOCATED ARIN',         # 2600::/12
    '00100110000100000000000'                       : 'ALLOCATED ARIN',         # 2610::/23
    '00100110001000000000000'                       : 'ALLOCATED ARIN',         # 2620::/23
    '001010000000'                                  : 'ALLOCATED LACNIC',       # 2800::/12
    '001010100000'                                  : 'ALLOCATED RIPE NCC',     # 2a00::/12
    '001011000000'                                  : 'ALLOCATED AFRINIC',      # 2c00::/12
    '00101101'                                      : 'RESERVED',               # 2d00::/8
    '0010111'                                       : 'RESERVED',               # 2e00::/7
    '0011'                                          : 'RESERVED',               # 3000::/4
    '010'                                           : 'RESERVED',               # 4000::/3
    '011'                                           : 'RESERVED',               # 6000::/3
    '100'                                           : 'RESERVED',               # 8000::/3
    '101'                                           : 'RESERVED',               # a000::/3
    '110'                                           : 'RESERVED',               # c000::/3
    '1110'                                          : 'RESERVED',               # e000::/4
    '11110'                                         : 'RESERVED',               # f000::/5
    '111110'                                        : 'RESERVED',               # f800::/6
    '1111110'                                       : 'ULA',                    # fc00::/7 [RFC4193]
    '111111100'                                     : 'RESERVED',               # fe00::/9
    '1111111010'                                    : 'LINKLOCAL',              # fe80::/10
    '1111111011'                                    : 'RESERVED',               # fec0::/10 Formerly SITELOCAL [RFC4291]
    '11111111'                                      : 'MULTICAST',              # ff00::/8
    '1111111100000001'                              : 'NODE-LOCAL MULTICAST',   # ff01::/16
    '1111111100000010'                              : 'LINK-LOCAL MULTICAST',   # ff02::/16
    '1111111100000100'                              : 'ADMIN-LOCAL MULTICAST',  # ff04::/16
    '1111111100000101'                              : 'SITE-LOCAL MULTICAST',   # ff05::/16
    '1111111100001000'                              : 'ORG-LOCAL MULTICAST',    # ff08::/16
    '1111111100001110'                              : 'GLOBAL MULTICAST',       # ff0e::/16
    '1111111100001111'                              : 'RESERVED MULTICAST',     # ff0f::/16
    '111111110011'                                  : 'PREFIX-BASED MULTICAST', # ff30::/12 [RFC3306]
    '111111110111'                                  : 'RP-EMBEDDED MULTICAST',  # ff70::/12 [RFC3956]
    }


class IPint:
    """Handling of IP addresses returning integers.

    Use class IP instead because some features are not implemented for
    IPint."""

    def __init__(self, data, ipversion=0, make_net=0):
        """Create an instance of an IP object.

        Data can be a network specification or a single IP. IP
        addresses can be specified in all forms understood by
        parseAddress(). The size of a network can be specified as

        /prefixlen        a.b.c.0/24               2001:658:22a:cafe::/64
        -lastIP           a.b.c.0-a.b.c.255        2001:658:22a:cafe::-2001:658:22a:cafe:ffff:ffff:ffff:ffff
        /decimal netmask  a.b.c.d/255.255.255.0    not supported for IPv6

        If no size specification is given a size of 1 address (/32 for
        IPv4 and /128 for IPv6) is assumed.

        If make_net is True, an IP address will be transformed into the network
        address by applying the specified netmask.

        >>> print(IP('127.0.0.0/8'))
        127.0.0.0/8
        >>> print(IP('127.0.0.0/255.0.0.0'))
        127.0.0.0/8
        >>> print(IP('127.0.0.0-127.255.255.255'))
        127.0.0.0/8
        >>> print(IP('127.0.0.1/255.0.0.0', make_net=True))
        127.0.0.0/8

        See module documentation for more examples.
        """

        # Print no Prefixlen for /32 and /128
        self.NoPrefixForSingleIp = 1

        # Do we want prefix printed by default? see _printPrefix()
        self.WantPrefixLen = None

        netbits = 0
        prefixlen = -1

        # handling of non string values in constructor
        if isinstance(data, (int, long)):
            self.ip = long(data)
            if ipversion == 0:
                if self.ip < 0x100000000:
                    ipversion = 4
                else:
                    ipversion = 6
            if ipversion == 4:
                if self.ip > 0xffffffff:
                    raise ValueError("IPv4 Addresses can't be larger than 0xffffffffffffffffffffffffffffffff: %x" % self.ip)
                prefixlen = 32
            elif ipversion == 6:
                if self.ip > 0xffffffffffffffffffffffffffffffff:
                    raise ValueError("IPv6 Addresses can't be larger than 0xffffffffffffffffffffffffffffffff: %x" % self.ip)
                prefixlen = 128
            else:
                raise ValueError("only IPv4 and IPv6 supported")
            self._ipversion = ipversion
            self._prefixlen = prefixlen
        # handle IP instance as an parameter
        elif isinstance(data, IPint):
            self._ipversion = data._ipversion
            self._prefixlen = data._prefixlen
            self.ip = data.ip
        elif isinstance(data, (str, unicode)):
            # TODO: refactor me!
            # splitting of a string into IP and prefixlen et. al.
            x = data.split('-')
            if len(x) == 2:
                # a.b.c.0-a.b.c.255 specification ?
                (ip, last) = x
                (self.ip, parsedVersion) = parseAddress(ip)
                if parsedVersion != 4:
                    raise ValueError("first-last notation only allowed for IPv4")
                (last, lastversion) = parseAddress(last)
                if lastversion != 4:
                    raise ValueError("last address should be IPv4, too")
                if last < self.ip:
                    raise ValueError("last address should be larger than first")
                size = last - self.ip
                netbits = _count1Bits(size)
                # make sure the broadcast is the same as the last ip
                # otherwise it will return /16 for something like:
                # 192.168.0.0-192.168.191.255
                if IP('%s/%s' % (ip, 32-netbits)).broadcast().int() != last:
                    raise ValueError("the range %s is not on a network boundary." % data)
            elif len(x) == 1:
                x = data.split('/')
                # if no prefix is given use defaults
                if len(x) == 1:
                    ip = x[0]
                    prefixlen = -1
                elif len(x) > 2:
                    raise ValueError("only one '/' allowed in IP Address")
                else:
                    (ip, prefixlen) = x
                    if prefixlen.find('.') != -1:
                        # check if the user might have used a netmask like
                        # a.b.c.d/255.255.255.0
                        (netmask, vers) = parseAddress(prefixlen)
                        if vers != 4:
                            raise ValueError("netmask must be IPv4")
                        prefixlen = _netmaskToPrefixlen(netmask)
            elif len(x) > 2:
                raise ValueError("only one '-' allowed in IP Address")
            else:
                raise ValueError("can't parse")

            (self.ip, parsedVersion) = parseAddress(ip)
            if ipversion == 0:
                ipversion = parsedVersion
            if prefixlen == -1:
                if ipversion == 4:
                    prefixlen = 32 - netbits
                elif ipversion == 6:
                    prefixlen = 128 - netbits
                else:
                    raise ValueError("only IPv4 and IPv6 supported")
            self._ipversion = ipversion
            self._prefixlen = int(prefixlen)

            if make_net:
                self.ip = self.ip & _prefixlenToNetmask(self._prefixlen, self._ipversion)

            if not _checkNetaddrWorksWithPrefixlen(self.ip,
            self._prefixlen, self._ipversion):
                raise ValueError("%s has invalid prefix length (%s)" % (repr(self), self._prefixlen))
        else:
            raise TypeError("Unsupported data type: %s" % type(data))

    def int(self):
        """Return the first / base / network addess as an (long) integer.

        The same as IP[0].

        >>> "%X" % IP('10.0.0.0/8').int()
        'A000000'
        """
        return self.ip

    def version(self):
        """Return the IP version of this Object.

        >>> IP('10.0.0.0/8').version()
        4
        >>> IP('::1').version()
        6
        """
        return self._ipversion

    def prefixlen(self):
        """Returns Network Prefixlen.

        >>> IP('10.0.0.0/8').prefixlen()
        8
        """
        return self._prefixlen

    def net(self):
        """
        Return the base (first) address of a network as an (long) integer.
        """
        return self.int()

    def broadcast(self):
        """
        Return the broadcast (last) address of a network as an (long) integer.

        The same as IP[-1]."""
        return self.int() + self.len() - 1

    def _printPrefix(self, want):
        """Prints Prefixlen/Netmask.

        Not really. In fact it is our universal Netmask/Prefixlen printer.
        This is considered an internal function.

        want == 0 / None        don't return anything    1.2.3.0
        want == 1               /prefix                  1.2.3.0/24
        want == 2               /netmask                 1.2.3.0/255.255.255.0
        want == 3               -lastip                  1.2.3.0-1.2.3.255
        """

        if (self._ipversion == 4 and self._prefixlen == 32) or \
           (self._ipversion == 6 and self._prefixlen == 128):
            if self.NoPrefixForSingleIp:
                want = 0
        if want == None:
            want = self.WantPrefixLen
            if want == None:
                want = 1
        if want:
            if want == 2:
                # this should work with IP and IPint
                netmask = self.netmask()
                if not isinstance(netmask, (int, long)):
                    netmask = netmask.int()
                return "/%s" % (intToIp(netmask, self._ipversion))
            elif want == 3:
                return "-%s" % (intToIp(self.ip + self.len() - 1, self._ipversion))
            else:
                # default
                return "/%d" % (self._prefixlen)
        else:
            return ''

        # We have different flavours to convert to:
        # strFullsize   127.0.0.1    2001:0658:022a:cafe:0200:c0ff:fe8d:08fa
        # strNormal     127.0.0.1    2001:658:22a:cafe:200:c0ff:fe8d:08fa
        # strCompressed 127.0.0.1    2001:658:22a:cafe::1
        # strHex        0x7F000001   0x20010658022ACAFE0200C0FFFE8D08FA
        # strDec        2130706433   42540616829182469433547974687817795834

    def strBin(self, wantprefixlen = None):
        """Return a string representation as a binary value.

        >>> print(IP('127.0.0.1').strBin())
        01111111000000000000000000000001
        """


        if self._ipversion == 4:
            bits = 32
        elif self._ipversion == 6:
            bits = 128
        else:
            raise ValueError("only IPv4 and IPv6 supported")

        if self.WantPrefixLen == None and wantprefixlen == None:
            wantprefixlen = 0
        ret = _intToBin(self.ip)
        return  '0' * (bits - len(ret)) + ret + self._printPrefix(wantprefixlen)

    def strCompressed(self, wantprefixlen = None):
        """Return a string representation in compressed format using '::' Notation.

        >>> IP('127.0.0.1').strCompressed()
        '127.0.0.1'
        >>> IP('2001:0658:022a:cafe:0200::1').strCompressed()
        '2001:658:22a:cafe:200::1'
        >>> IP('ffff:ffff:ffff:ffff:ffff:f:f:fffc/127').strCompressed()
        'ffff:ffff:ffff:ffff:ffff:f:f:fffc/127'
        """

        if self.WantPrefixLen == None and wantprefixlen == None:
            wantprefixlen = 1

        if self._ipversion == 4:
            return self.strFullsize(wantprefixlen)
        else:
            if self.ip >> 32 == 0xffff:
                ipv4 = intToIp(self.ip & 0xffffffff, 4)
                text = "::ffff:" + ipv4 + self._printPrefix(wantprefixlen)
                return text
            # find the longest sequence of '0'
            hextets = [int(x, 16) for x in self.strFullsize(0).split(':')]
            # every element of followingzeros will contain the number of zeros
            # following the corresponding element of hextets
            followingzeros = [0] * 8
            for i in xrange(len(hextets)):
                followingzeros[i] = _countFollowingZeros(hextets[i:])
            # compressionpos is the position where we can start removing zeros
            compressionpos = followingzeros.index(max(followingzeros))
            if max(followingzeros) > 1:
                # genererate string with the longest number of zeros cut out
                # now we need hextets as strings
                hextets = [x for x in self.strNormal(0).split(':')]
                while compressionpos < len(hextets) and hextets[compressionpos] == '0':
                    del(hextets[compressionpos])
                hextets.insert(compressionpos, '')
                if compressionpos + 1 >= len(hextets):
                    hextets.append('')
                if compressionpos == 0:
                    hextets = [''] + hextets
                return ':'.join(hextets) + self._printPrefix(wantprefixlen)
            else:
                return self.strNormal(0) + self._printPrefix(wantprefixlen)

    def strNormal(self, wantprefixlen = None):
        """Return a string representation in the usual format.

        >>> print(IP('127.0.0.1').strNormal())
        127.0.0.1
        >>> print(IP('2001:0658:022a:cafe:0200::1').strNormal())
        2001:658:22a:cafe:200:0:0:1
        """

        if self.WantPrefixLen == None and wantprefixlen == None:
            wantprefixlen = 1

        if self._ipversion == 4:
            ret = self.strFullsize(0)
        elif self._ipversion == 6:
            ret = ':'.join([hex(x)[2:] for x in [int(x, 16) for x in self.strFullsize(0).split(':')]])
        else:
            raise ValueError("only IPv4 and IPv6 supported")



        return ret + self._printPrefix(wantprefixlen)

    def strFullsize(self, wantprefixlen = None):
        """Return a string representation in the non-mangled format.

        >>> print(IP('127.0.0.1').strFullsize())
        127.0.0.1
        >>> print(IP('2001:0658:022a:cafe:0200::1').strFullsize())
        2001:0658:022a:cafe:0200:0000:0000:0001
        """

        if self.WantPrefixLen == None and wantprefixlen == None:
            wantprefixlen = 1

        return intToIp(self.ip, self._ipversion).lower() + self._printPrefix(wantprefixlen)

    def strHex(self, wantprefixlen = None):
        """Return a string representation in hex format in lower case.

        >>> IP('127.0.0.1').strHex()
        '0x7f000001'
        >>> IP('2001:0658:022a:cafe:0200::1').strHex()
        '0x20010658022acafe0200000000000001'
        """

        if self.WantPrefixLen == None and wantprefixlen == None:
            wantprefixlen = 0

        x = hex(self.ip)
        if x[-1] == 'L':
            x = x[:-1]
        return x.lower() + self._printPrefix(wantprefixlen)

    def strDec(self, wantprefixlen = None):
        """Return a string representation in decimal format.

        >>> print(IP('127.0.0.1').strDec())
        2130706433
        >>> print(IP('2001:0658:022a:cafe:0200::1').strDec())
        42540616829182469433547762482097946625
        """

        if self.WantPrefixLen == None and wantprefixlen == None:
            wantprefixlen = 0

        x =  str(self.ip)
        if x[-1] == 'L':
            x = x[:-1]
        return x + self._printPrefix(wantprefixlen)

    def iptype(self):
        """Return a description of the IP type ('PRIVATE', 'RESERVERD', etc).

        >>> print(IP('127.0.0.1').iptype())
        PRIVATE
        >>> print(IP('192.168.1.1').iptype())
        PRIVATE
        >>> print(IP('195.185.1.2').iptype())
        PUBLIC
        >>> print(IP('::1').iptype())
        LOOPBACK
        >>> print(IP('2001:0658:022a:cafe:0200::1').iptype())
        ALLOCATED RIPE NCC

        The type information for IPv6 is out of sync with reality.
        """

        # this could be greatly improved

        if self._ipversion == 4:
            iprange = IPv4ranges
        elif self._ipversion == 6:
            iprange = IPv6ranges
        else:
            raise ValueError("only IPv4 and IPv6 supported")

        bits = self.strBin()
        for i in xrange(len(bits), 0, -1):
            if bits[:i] in iprange:
                return iprange[bits[:i]]
        return "unknown"


    def netmask(self):
        """Return netmask as an integer.

        >>> "%X" % IP('195.185.0.0/16').netmask().int()
        'FFFF0000'
        """

        # TODO: unify with prefixlenToNetmask?
        if self._ipversion == 4:
            locallen = 32 - self._prefixlen
        elif self._ipversion == 6:
            locallen = 128 - self._prefixlen
        else:
            raise ValueError("only IPv4 and IPv6 supported")

        return ((2 ** self._prefixlen) - 1) << locallen


    def strNetmask(self):
        """Return netmask as an string. Mostly useful for IPv6.

        >>> print(IP('195.185.0.0/16').strNetmask())
        255.255.0.0
        >>> print(IP('2001:0658:022a:cafe::0/64').strNetmask())
        /64
        """

        # TODO: unify with prefixlenToNetmask?
        if self._ipversion == 4:
            locallen = 32 - self._prefixlen
            return intToIp(((2 ** self._prefixlen) - 1) << locallen, 4)
        elif self._ipversion == 6:
            locallen = 128 - self._prefixlen
            return "/%d" % self._prefixlen
        else:
            raise ValueError("only IPv4 and IPv6 supported")

    def len(self):
        """Return the length of a subnet.

        >>> print(IP('195.185.1.0/28').len())
        16
        >>> print(IP('195.185.1.0/24').len())
        256
        """

        if self._ipversion == 4:
            locallen = 32 - self._prefixlen
        elif self._ipversion == 6:
            locallen = 128 - self._prefixlen
        else:
            raise ValueError("only IPv4 and IPv6 supported")

        return 2 ** locallen


    def __nonzero__(self):
        """All IPy objects should evaluate to true in boolean context.
        Ordinarily they do, but if handling a default route expressed as
        0.0.0.0/0, the __len__() of the object becomes 0, which is used
        as the boolean value of the object.
        """
        return True


    def __len__(self):
        """Return the length of a subnet.

        Called to implement the built-in function len().
        It breaks with IPv6 Networks. Anybody knows how to fix this."""

        # Python < 2.2 has this silly restriction which breaks IPv6
        # how about Python >= 2.2 ... ouch - it persists!

        return int(self.len())


    def __getitem__(self, key):
        """Called to implement evaluation of self[key].

        >>> ip=IP('127.0.0.0/30')
        >>> for x in ip:
        ...  print(repr(x))
        ...
        IP('127.0.0.0')
        IP('127.0.0.1')
        IP('127.0.0.2')
        IP('127.0.0.3')
        >>> ip[2]
        IP('127.0.0.2')
        >>> ip[-1]
        IP('127.0.0.3')
        """

        if not isinstance(key, (int, long)):
            raise TypeError
        if key < 0:
            if abs(key) <= self.len():
                key = self.len() - abs(key)
            else:
                raise IndexError
        else:
            if key >= self.len():
                raise IndexError

        return self.ip + long(key)



    def __contains__(self, item):
        """Called to implement membership test operators.

        Should return true if item is in self, false otherwise. Item
        can be other IP-objects, strings or ints.

        >>> IP('195.185.1.1').strHex()
        '0xc3b90101'
        >>> 0xC3B90101 in IP('195.185.1.0/24')
        True
        >>> '127.0.0.1' in IP('127.0.0.0/24')
        True
        >>> IP('127.0.0.0/24') in IP('127.0.0.0/25')
        False
        """

        item = IP(item)
        if item.ip >= self.ip and item.ip < self.ip + self.len() - item.len() + 1:
            return True
        else:
            return False


    def overlaps(self, item):
        """Check if two IP address ranges overlap.

        Returns 0 if the two ranges don't overlap, 1 if the given
        range overlaps at the end and -1 if it does at the beginning.

        >>> IP('192.168.0.0/23').overlaps('192.168.1.0/24')
        1
        >>> IP('192.168.0.0/23').overlaps('192.168.1.255')
        1
        >>> IP('192.168.0.0/23').overlaps('192.168.2.0')
        0
        >>> IP('192.168.1.0/24').overlaps('192.168.0.0/23')
        -1
        """

        item = IP(item)
        if item.ip >= self.ip and item.ip < self.ip + self.len():
            return 1
        elif self.ip >= item.ip and self.ip < item.ip + item.len():
            return -1
        else:
            return 0


    def __str__(self):
        """Dispatch to the prefered String Representation.

        Used to implement str(IP)."""

        return self.strCompressed()


    def __repr__(self):
        """Print a representation of the Object.

        Used to implement repr(IP). Returns a string which evaluates
        to an identical Object (without the wantprefixlen stuff - see
        module docstring.

        >>> print(repr(IP('10.0.0.0/24')))
        IP('10.0.0.0/24')
        """

        return("IPint('%s')" % (self.strCompressed(1)))


    def __cmp__(self, other):
        """Called by comparison operations.

        Should return a negative integer if self < other, zero if self
        == other, a positive integer if self > other.

        Networks with different prefixlen are considered non-equal.
        Networks with the same prefixlen and differing addresses are
        considered non equal but are compared by their base address
        integer value to aid sorting of IP objects.

        The version of Objects is not put into consideration.

        >>> IP('10.0.0.0/24') > IP('10.0.0.0')
        1
        >>> IP('10.0.0.0/24') < IP('10.0.0.0')
        0
        >>> IP('10.0.0.0/24') < IP('12.0.0.0/24')
        1
        >>> IP('10.0.0.0/24') > IP('12.0.0.0/24')
        0

        """

        # Im not really sure if this is "the right thing to do"
        if self._prefixlen < other.prefixlen():
            return (other.prefixlen() - self._prefixlen)
        elif self._prefixlen > other.prefixlen():

            # Fixed bySamuel Krempp <krempp@crans.ens-cachan.fr>:

            # The bug is quite obvious really (as 99% bugs are once
            # spotted, isn't it ? ;-) Because of precedence of
            # multiplication by -1 over the substraction, prefixlen
            # differences were causing the __cmp__ function to always
            # return positive numbers, thus the function was failing
            # the basic assumptions for a __cmp__ function.

            # Namely we could have (a > b AND b > a), when the
            # prefixlen of a and b are different.  (eg let
            # a=IP("1.0.0.0/24"); b=IP("2.0.0.0/16");) thus, anything
            # could happen when launching a sort algorithm..
            # everything's in order with the trivial, attached patch.

            return other.prefixlen() - self._prefixlen
        else:
            if self.ip < other.ip:
                return -1
            elif self.ip > other.ip:
                return 1
            elif self._ipversion != other._ipversion:
                # IP('0.0.0.0'), IP('::/0')
                if self._ipversion < other._ipversion:
                    return -1
                elif self._ipversion > other._ipversion:
                    return 1
                else:
                    return 0
            else:
                return 0

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __hash__(self):
        """Called for the key object for dictionary operations, and by
        the built-in function hash(). Should return a 32-bit integer
        usable as a hash value for dictionary operations. The only
        required property is that objects which compare equal have the
        same hash value

        >>> IP('10.0.0.0/24').__hash__()
        -167772185
        """

        thehash = int(-1)
        ip = self.ip
        while ip > 0:
            thehash = thehash ^ (ip & 0x7fffffff)
            ip = ip >> 32
        thehash = thehash ^ self._prefixlen
        return int(thehash)


class IP(IPint):
    """Class for handling IP addresses and networks."""

    def net(self):
        """Return the base (first) address of a network as an IP object.

        The same as IP[0].

        >>> IP('10.0.0.0/8').net()
        IP('10.0.0.0')
        """
        return IP(IPint.net(self), ipversion=self._ipversion)

    def broadcast(self):
        """Return the broadcast (last) address of a network as an IP object.

        The same as IP[-1].

        >>> IP('10.0.0.0/8').broadcast()
        IP('10.255.255.255')
        """
        return IP(IPint.broadcast(self))

    def netmask(self):
        """Return netmask as an IP object.

        >>> IP('10.0.0.0/8').netmask()
        IP('255.0.0.0')
         """
        return IP(IPint.netmask(self), ipversion=self._ipversion)

    def _getIPv4Map(self):
        if self._ipversion != 6:
            return None
        if (self.ip >> 32) != 0xffff:
            return None
        ipv4 = self.ip & 0xffffffff
        if self._prefixlen != 128:
            ipv4 = '%s/%s' % (ipv4, 32-(128-self._prefixlen))
        return IP(ipv4, ipversion=4)

    def reverseNames(self):
        """Return a list with values forming the reverse lookup.

        >>> IP('213.221.113.87/32').reverseNames()
        ['87.113.221.213.in-addr.arpa.']
        >>> IP('213.221.112.224/30').reverseNames()
        ['224.112.221.213.in-addr.arpa.', '225.112.221.213.in-addr.arpa.', '226.112.221.213.in-addr.arpa.', '227.112.221.213.in-addr.arpa.']
        >>> IP('127.0.0.0/24').reverseNames()
        ['0.0.127.in-addr.arpa.']
        >>> IP('127.0.0.0/23').reverseNames()
        ['0.0.127.in-addr.arpa.', '1.0.127.in-addr.arpa.']
        >>> IP('127.0.0.0/16').reverseNames()
        ['0.127.in-addr.arpa.']
        >>> IP('127.0.0.0/15').reverseNames()
        ['0.127.in-addr.arpa.', '1.127.in-addr.arpa.']
        >>> IP('128.0.0.0/8').reverseNames()
        ['128.in-addr.arpa.']
        >>> IP('128.0.0.0/7').reverseNames()
        ['128.in-addr.arpa.', '129.in-addr.arpa.']
        >>> IP('::1:2').reverseNames()
        ['2.0.0.0.1.ip6.arpa.']
        """

        if self._ipversion == 4:
            ret = []
            # TODO: Refactor. Add support for IPint objects
            if self.len() < 2**8:
                for x in self:
                    ret.append(x.reverseName())
            elif self.len() < 2**16:
                for i in xrange(0, self.len(), 2**8):
                    ret.append(self[i].reverseName()[2:])
            elif self.len() < 2**24:
                for i in xrange(0, self.len(), 2**16):
                    ret.append(self[i].reverseName()[4:])
            else:
                for i in xrange(0, self.len(), 2**24):
                    ret.append(self[i].reverseName()[6:])
            return ret
        elif self._ipversion == 6:
            ipv4 = self._getIPv4Map()
            if ipv4 is not None:
                return ipv4.reverseNames()
            s = hex(self.ip)[2:].lower()
            if s[-1] == 'l':
                s = s[:-1]
            if self._prefixlen % 4 != 0:
                raise NotImplementedError("can't create IPv6 reverse names at sub nibble level")
            s = list(s)
            s.reverse()
            s = '.'.join(s)
            first_nibble_index = int(32 - (self._prefixlen // 4)) * 2
            return ["%s.ip6.arpa." % s[first_nibble_index:]]
        else:
            raise ValueError("only IPv4 and IPv6 supported")

    def reverseName(self):
        """Return the value for reverse lookup/PTR records as RFC 2317 look alike.

        RFC 2317 is an ugly hack which only works for sub-/24 e.g. not
        for /23. Do not use it. Better set up a zone for every
        address. See reverseName for a way to achieve that.

        >>> print(IP('195.185.1.1').reverseName())
        1.1.185.195.in-addr.arpa.
        >>> print(IP('195.185.1.0/28').reverseName())
        0-15.1.185.195.in-addr.arpa.
        >>> IP('::1:2').reverseName()
        '2.0.0.0.1.ip6.arpa.'
        """

        if self._ipversion == 4:
            s = self.strFullsize(0)
            s = s.split('.')
            s.reverse()
            first_byte_index = int(4 - (self._prefixlen // 8))
            if self._prefixlen % 8 != 0:
                nibblepart = "%s-%s" % (s[3-(self._prefixlen // 8)], intToIp(self.ip + self.len() - 1, 4).split('.')[-1])
                if nibblepart[-1] == 'l':
                    nibblepart = nibblepart[:-1]
                nibblepart += '.'
            else:
                nibblepart = ""

            s = '.'.join(s[first_byte_index:])
            return "%s%s.in-addr.arpa." % (nibblepart, s)

        elif self._ipversion == 6:
            ipv4 = self._getIPv4Map()
            if ipv4 is not None:
                return ipv4.reverseName()
            s = hex(self.ip)[2:].lower()
            if s[-1] == 'l':
                s = s[:-1]
            if self._prefixlen % 4 != 0:
                nibblepart = "%s-%s" % (s[self._prefixlen:], hex(self.ip + self.len() - 1)[2:].lower())
                if nibblepart[-1] == 'l':
                    nibblepart = nibblepart[:-1]
                nibblepart += '.'
            else:
                nibblepart = ""
            s = list(s)
            s.reverse()
            s = '.'.join(s)
            first_nibble_index = int(32 - (self._prefixlen // 4)) * 2
            return "%s%s.ip6.arpa." % (nibblepart, s[first_nibble_index:])
        else:
            raise ValueError("only IPv4 and IPv6 supported")

    def make_net(self, netmask):
        """Transform a single IP address into a network specification by
        applying the given netmask.

        Returns a new IP instance.

        >>> print(IP('127.0.0.1').make_net('255.0.0.0'))
        127.0.0.0/8
        """
        if '/' in str(netmask):
            raise ValueError("invalid netmask (%s)" % netmask)
        return IP('%s/%s' % (self, netmask), make_net=True)

    def __getitem__(self, key):
        """Called to implement evaluation of self[key].

        >>> ip=IP('127.0.0.0/30')
        >>> for x in ip:
        ...  print(str(x))
        ...
        127.0.0.0
        127.0.0.1
        127.0.0.2
        127.0.0.3
        >>> print(str(ip[2]))
        127.0.0.2
        >>> print(str(ip[-1]))
        127.0.0.3
        """
        return IP(IPint.__getitem__(self, key))

    def __repr__(self):
        """Print a representation of the Object.

        >>> IP('10.0.0.0/8')
        IP('10.0.0.0/8')
        """

        return("IP('%s')" % (self.strCompressed(1)))

    def __add__(self, other):
        """Emulate numeric objects through network aggregation"""
        if self.prefixlen() != other.prefixlen():
            raise ValueError("Only networks with the same prefixlen can be added.")
        if self.prefixlen() < 1:
            raise ValueError("Networks with a prefixlen longer than /1 can't be added.")
        if self.version() != other.version():
            raise ValueError("Only networks with the same IP version can be added.")
        if self > other:
            # fixed by Skinny Puppy <skin_pup-IPy@happypoo.com>
            return other.__add__(self)
        else:
            ret = IP(self.int())
            ret._prefixlen = self.prefixlen() - 1
            return ret


def _parseAddressIPv6(ipstr):
    """
    Internal function used by parseAddress() to parse IPv6 address with ':'.

    >>> print(_parseAddressIPv6('::'))
    0
    >>> print(_parseAddressIPv6('::1'))
    1
    >>> print(_parseAddressIPv6('0:0:0:0:0:0:0:1'))
    1
    >>> print(_parseAddressIPv6('0:0:0::0:0:1'))
    1
    >>> print(_parseAddressIPv6('0:0:0:0:0:0:0:0'))
    0
    >>> print(_parseAddressIPv6('0:0:0::0:0:0'))
    0

    >>> print(_parseAddressIPv6('FEDC:BA98:7654:3210:FEDC:BA98:7654:3210'))
    338770000845734292534325025077361652240
    >>> print(_parseAddressIPv6('1080:0000:0000:0000:0008:0800:200C:417A'))
    21932261930451111902915077091070067066
    >>> print(_parseAddressIPv6('1080:0:0:0:8:800:200C:417A'))
    21932261930451111902915077091070067066
    >>> print(_parseAddressIPv6('1080:0::8:800:200C:417A'))
    21932261930451111902915077091070067066
    >>> print(_parseAddressIPv6('1080::8:800:200C:417A'))
    21932261930451111902915077091070067066
    >>> print(_parseAddressIPv6('FF01:0:0:0:0:0:0:43'))
    338958331222012082418099330867817087043
    >>> print(_parseAddressIPv6('FF01:0:0::0:0:43'))
    338958331222012082418099330867817087043
    >>> print(_parseAddressIPv6('FF01::43'))
    338958331222012082418099330867817087043
    >>> print(_parseAddressIPv6('0:0:0:0:0:0:13.1.68.3'))
    218186755
    >>> print(_parseAddressIPv6('::13.1.68.3'))
    218186755
    >>> print(_parseAddressIPv6('0:0:0:0:0:FFFF:129.144.52.38'))
    281472855454758
    >>> print(_parseAddressIPv6('::FFFF:129.144.52.38'))
    281472855454758
    >>> print(_parseAddressIPv6('1080:0:0:0:8:800:200C:417A'))
    21932261930451111902915077091070067066
    >>> print(_parseAddressIPv6('1080::8:800:200C:417A'))
    21932261930451111902915077091070067066
    >>> print(_parseAddressIPv6('::1:2:3:4:5:6'))
    1208962713947218704138246
    >>> print(_parseAddressIPv6('1:2:3:4:5:6::'))
    5192455318486707404433266432802816
    """

    # Split string into a list, example:
    #   '1080:200C::417A' => ['1080', '200C', '417A'] and fill_pos=2
    # and fill_pos is the position of '::' in the list
    items = []
    index = 0
    fill_pos = None
    while index < len(ipstr):
        text = ipstr[index:]
        if text.startswith("::"):
            if fill_pos is not None:
                # Invalid IPv6, eg. '1::2::'
                raise ValueError("%r: Invalid IPv6 address: more than one '::'" % ipstr)
            fill_pos = len(items)
            index += 2
            continue
        pos = text.find(':')
        if pos == 0:
            # Invalid IPv6, eg. '1::2:'
            raise ValueError("%r: Invalid IPv6 address" % ipstr)
        if pos != -1:
            items.append(text[:pos])
            if text[pos:pos+2] == "::":
                index += pos
            else:
                index += pos+1

            if index == len(ipstr):
                # Invalid IPv6, eg. '1::2:'
                raise ValueError("%r: Invalid IPv6 address" % ipstr)
        else:
            items.append(text)
            break

    if items and '.' in items[-1]:
        # IPv6 ending with IPv4 like '::ffff:192.168.0.1'
        if (fill_pos is not None) and not (fill_pos <= len(items)-1):
            # Invalid IPv6: 'ffff:192.168.0.1::'
            raise ValueError("%r: Invalid IPv6 address: '::' after IPv4" % ipstr)
        value = parseAddress(items[-1])[0]
        items = items[:-1] + ["%04x" % (value >> 16), "%04x" % (value & 0xffff)]

    # Expand fill_pos to fill with '0'
    # ['1','2'] with fill_pos=1 => ['1', '0', '0', '0', '0', '0', '0', '2']
    if fill_pos is not None:
        diff = 8 - len(items)
        if diff <= 0:
            raise ValueError("%r: Invalid IPv6 address: '::' is not needed" % ipstr)
        items = items[:fill_pos] + ['0']*diff + items[fill_pos:]

    # Here we have a list of 8 strings
    if len(items) != 8:
        # Invalid IPv6, eg. '1:2:3'
        raise ValueError("%r: Invalid IPv6 address: should have 8 hextets" % ipstr)

    # Convert strings to long integer
    value = 0
    index = 0
    for item in items:
        try:
            item = int(item, 16)
            error = not(0 <= item <= 0xFFFF)
        except ValueError:
            error = True
        if error:
            raise ValueError("%r: Invalid IPv6 address: invalid hexlet %r" % (ipstr, item))
        value = (value << 16) + item
        index += 1
    return value

def parseAddress(ipstr):
    """
    Parse a string and return the corresponding IP address (as integer)
    and a guess of the IP version.

    Following address formats are recognized:

    >>> def testParseAddress(address):
    ...     ip, version = parseAddress(address)
    ...     print(("%s (IPv%s)" % (ip, version)))
    ...
    >>> testParseAddress('0x0123456789abcdef')           # IPv4 if <= 0xffffffff else IPv6
    81985529216486895 (IPv6)
    >>> testParseAddress('123.123.123.123')              # IPv4
    2071690107 (IPv4)
    >>> testParseAddress('123.123')                      # 0-padded IPv4
    2071658496 (IPv4)
    >>> testParseAddress('1080:0000:0000:0000:0008:0800:200C:417A')
    21932261930451111902915077091070067066 (IPv6)
    >>> testParseAddress('1080:0:0:0:8:800:200C:417A')
    21932261930451111902915077091070067066 (IPv6)
    >>> testParseAddress('1080:0::8:800:200C:417A')
    21932261930451111902915077091070067066 (IPv6)
    >>> testParseAddress('::1')
    1 (IPv6)
    >>> testParseAddress('::')
    0 (IPv6)
    >>> testParseAddress('0:0:0:0:0:FFFF:129.144.52.38')
    281472855454758 (IPv6)
    >>> testParseAddress('::13.1.68.3')
    218186755 (IPv6)
    >>> testParseAddress('::FFFF:129.144.52.38')
    281472855454758 (IPv6)
    """

    if ipstr.startswith('0x'):
        ret = long(ipstr[2:], 16)
        if ret > 0xffffffffffffffffffffffffffffffff:
            raise ValueError("%r: IP Address can't be bigger than 2^128" % (ipstr))
        if ret < 0x100000000:
            return (ret, 4)
        else:
            return (ret, 6)

    if ipstr.find(':') != -1:
        return (_parseAddressIPv6(ipstr), 6)

    elif len(ipstr) == 32:
        # assume IPv6 in pure hexadecimal notation
        return (long(ipstr, 16), 6)

    elif  ipstr.find('.') != -1 or (len(ipstr) < 4 and int(ipstr) < 256):
        # assume IPv4  ('127' gets interpreted as '127.0.0.0')
        bytes = ipstr.split('.')
        if len(bytes) > 4:
            raise ValueError("IPv4 Address with more than 4 bytes")
        bytes += ['0'] * (4 - len(bytes))
        bytes = [long(x) for x in bytes]
        for x in bytes:
            if x > 255 or x < 0:
                raise ValueError("%r: single byte must be 0 <= byte < 256" % (ipstr))
        return ((bytes[0] << 24) + (bytes[1] << 16) + (bytes[2] << 8) + bytes[3], 4)

    else:
        # we try to interprete it as a decimal digit -
        # this ony works for numbers > 255 ... others
        # will be interpreted as IPv4 first byte
        ret = long(ipstr, 10)
        if ret > 0xffffffffffffffffffffffffffffffff:
            raise ValueError("IP Address can't be bigger than 2^128")
        if ret <= 0xffffffff:
            return (ret, 4)
        else:
            return (ret, 6)


def intToIp(ip, version):
    """Transform an integer string into an IP address."""

    # just to be sure and hoping for Python 2.22
    ip = long(ip)

    if ip < 0:
        raise ValueError("IPs can't be negative: %d" % (ip))

    ret = ''
    if version == 4:
        if ip > 0xffffffff:
            raise ValueError("IPv4 Addresses can't be larger than 0xffffffff: %s" % (hex(ip)))
        for l in xrange(4):
            ret = str(ip & 0xff) + '.' + ret
            ip = ip >> 8
        ret = ret[:-1]
    elif version == 6:
        if ip > 0xffffffffffffffffffffffffffffffff:
            raise ValueError("IPv6 Addresses can't be larger than 0xffffffffffffffffffffffffffffffff: %s" % (hex(ip)))
        if sys.hexversion >= 0x03000000:
            # Remove "0x" prefix
            l = hex(ip)[2:]
        else:
            # Remove "0x" prefix and "L" suffix
            l = hex(ip)[2:-1]
        l = l.zfill(32)
        for x in xrange(1, 33):
            ret = l[-x] + ret
            if x % 4 == 0:
                ret = ':' + ret
        ret = ret[1:]
    else:
        raise ValueError("only IPv4 and IPv6 supported")

    return ret

def _ipVersionToLen(version):
    """Return number of bits in address for a certain IP version.

    >>> _ipVersionToLen(4)
    32
    >>> _ipVersionToLen(6)
    128
    >>> _ipVersionToLen(5)
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
      File "IPy.py", line 1076, in _ipVersionToLen
        raise ValueError("only IPv4 and IPv6 supported")
    ValueError: only IPv4 and IPv6 supported
    """

    if version == 4:
        return 32
    elif version == 6:
        return 128
    else:
        raise ValueError("only IPv4 and IPv6 supported")


def _countFollowingZeros(l):
    """Return number of elements containing 0 at the beginning of the list."""
    if len(l) == 0:
        return 0
    elif l[0] != 0:
        return 0
    else:
        return 1 + _countFollowingZeros(l[1:])


_BitTable = {'0': '0000', '1': '0001', '2': '0010', '3': '0011',
            '4': '0100', '5': '0101', '6': '0110', '7': '0111',
            '8': '1000', '9': '1001', 'a': '1010', 'b': '1011',
            'c': '1100', 'd': '1101', 'e': '1110', 'f': '1111'}

def _intToBin(val):
    """Return the binary representation of an integer as string."""

    if val < 0:
        raise ValueError("Only positive values allowed")
    s = hex(val).lower()
    ret = ''
    if s[-1] == 'l':
        s = s[:-1]
    for x in s[2:]:
        ret += _BitTable[x]
    # remove leading zeros
    while ret[0] == '0' and len(ret) > 1:
        ret = ret[1:]
    return ret

def _count1Bits(num):
    """Find the highest bit set to 1 in an integer."""
    ret = 0
    while num > 0:
        num = num >> 1
        ret += 1
    return ret

def _count0Bits(num):
    """Find the highest bit set to 0 in an integer."""

    # this could be so easy if _count1Bits(~long(num)) would work as excepted
    num = long(num)
    if num < 0:
        raise ValueError("Only positive Numbers please: %s" % (num))
    ret = 0
    while num > 0:
        if num & 1 == 1:
            break
        num = num >> 1
        ret += 1
    return ret


def _checkPrefix(ip, prefixlen, version):
    """Check the validity of a prefix

    Checks if the variant part of a prefix only has 0s, and the length is
    correct.

    >>> _checkPrefix(0x7f000000, 24, 4)
    1
    >>> _checkPrefix(0x7f000001, 24, 4)
    0
    >>> repr(_checkPrefix(0x7f000001, -1, 4))
    'None'
    >>> repr(_checkPrefix(0x7f000001, 33, 4))
    'None'
    """

    # TODO: unify this v4/v6/invalid code in a function
    bits = _ipVersionToLen(version)

    if prefixlen < 0 or prefixlen > bits:
        return None

    if ip == 0:
        zbits = bits + 1
    else:
        zbits = _count0Bits(ip)
    if zbits <  bits - prefixlen:
        return 0
    else:
        return 1


def _checkNetmask(netmask, masklen):
    """Checks if a netmask is expressable as a prefixlen."""

    num = long(netmask)
    bits = masklen

    # remove zero bits at the end
    while (num & 1) == 0 and bits != 0:
        num = num >> 1
        bits -= 1
        if bits == 0:
            break
    # now check if the rest consists only of ones
    while bits > 0:
        if (num & 1) == 0:
            raise ValueError("Netmask %s can't be expressed as an prefix." % (hex(netmask)))
        num = num >> 1
        bits -= 1


def _checkNetaddrWorksWithPrefixlen(net, prefixlen, version):
    """Check if a base addess of a network is compatible with a prefixlen"""
    return (net & _prefixlenToNetmask(prefixlen, version) == net)


def _netmaskToPrefixlen(netmask):
    """Convert an Integer representing a netmask to a prefixlen.

    E.g. 0xffffff00 (255.255.255.0) returns 24
    """

    netlen = _count0Bits(netmask)
    masklen = _count1Bits(netmask)
    _checkNetmask(netmask, masklen)
    return masklen - netlen


def _prefixlenToNetmask(prefixlen, version):
    """Return a mask of n bits as a long integer.

    From 'IP address conversion functions with the builtin socket module'
    by Alex Martelli
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66517
    """
    if prefixlen == 0:
        return 0
    elif prefixlen < 0:
        raise ValueError("Prefixlen must be > 0")
    return ((2<<prefixlen-1)-1) << (_ipVersionToLen(version) - prefixlen)


if __name__ == "__main__":
    import doctest
    failure, nbtest = doctest.testmod()
    if failure:
        import sys
        sys.exit(1)



########NEW FILE########
