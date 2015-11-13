__FILENAME__ = device_script
import syslog
import sys
import pprint
import socket
from Insieme.Logger import as Logger 

def sampleDevice_logger( f ):
    def wrapper( *args ):
        Logger.log(Logger.INFO,"%s%s" % (f.__name__, args)) 
        f( *args )
    return wrapper

#
# Infra API
#
@sampleDevice_logger
def deviceValidate( device, version ):
    pass

@sampleDevice_logger
def deviceModify( device, interfaces, configuration):
    pass 

@sampleDevice_logger
def deviceAudit( device, interfaces, configuration ):
    pass

@sampleDevice_logger
def deviceHealth( device ):
    pass 

@sampleDevice_logger
def clusterModify( device, configuration ):
    pass

@sampleDevice_logger
def clusterAudit( device, configuration ):
    pass

#
# FunctionGroup API
#
@sampleDevice_logger
def serviceModify( device,
                   configuration ):
    ''' 
    (0, '', 4447): {
          'state': 1,                                                                                                                    
          'transaction': 10000,                                                                                                          
          'value': {
              (1, '', 4384): {
                  'state': 1,                                                                                          
                  'transaction': 10000,                                                                                
                  'value': {
                       (3, 'SLB', 'Node2'): {
                              'state': 1,                                                          
                              'transaction': 10000,                                                
                              'value': {
                                   (2, '', 'inside'): {
                                       'state': 1,                            
                                       'transaction': 10000,                  
                                       'value': {
                                            (9, '', 'ADCCluster1_inside_7697'): {
                                                 'state': 2,                          
                                                 'target': 'ADCCluster1_inside_7697',                                                 
                                                 'transaction': 10000
                                             }
                                        }
                                    },                                                                                                                  
                                    (2, '', 'outside'): {
                                        'state': 1,                           
                                        'transaction': 10000,                 
                                        'value': {
                                            (9, '', 'ADCCluster1_outside_4625'): {
                                                'state': 2,                                             
                                                'target': 'ADCCluster1_outside_4625',                                           
                                                'transaction': 10000
                                            }
                                         }
                                    },                                                                                                              
                                    (4, 'VServer', 'VServer'): {
                                          'connector': '',              
                                          'state': 1,                    
                                          'transaction': 10000,          
                                          'value': {
                                             (5, 'port', 'port'): {
                                                  'connector': '',                                             
                                                  'state': 1,
                                                  'transaction': 10000,                                                    
                                                  'value': '800000'
                                              }
                                           }
                                    }
                               }
                         }
                     }
                 },                                                                                                                          
                (4, 'Network', 'Network'): {
                      'connector': u'',                                                                        
                      'state': 1,                                                                              
                      'transaction': 10000,                                                                    
                      'value': {
                          (4, 'subnetip', 'subnetip'): {
                            'connector': '',                                
                            'state': 1,                                      
                            'transaction': 10000,                            
                            'value': {
                                (5, 'subnetipaddress', 'subnetipaddress'): {
                                    'connector': '',                                                                                                     
                                    'state': 1,                                                                                                         
                                    'transaction': 10000,                                                                                              
                                    'value': ''
                                 }
                              }
                           },                                                                               
                       }
                  }
             }
        }
    # 
    # Example of returning multiple faults 
    #
    (1) The parameter value for subnetipaddress is invalid. Script can raise a fault on this param

    subnetipaddressInstance = [(0, '', 4447), (4, 'Network', 'Network'), (4, 'subnetip', 'subnetip'), (5, 'subnetipaddress', 'subnetipaddress')]
    subnetipaddressFault = "Invalid subnet IP address"
   
    (2) The VServer folder under SLB has invalid port number 

    slbPortInstance = [(0, '', 4447), (1, '', 4384), (3, 'SLB', 'Node2'), (4, 'VServer', 'VServer'), (5, 'port', 'port')]
    slbPortFault = "Invalid SLB Vserver Port value - Acceptable range 1 - 65535"

    #
    # Example of reporting Servicehealth along with ServiceModify
    #
    slbInstance =[(0, '', 4447), (1, '', 4384), (3, 'SLB', 'Node2')]
    slbInstanceHealth = 0

    returnValue =  { 
        'status': True, 
        'faults': [
                    (subnetipaddressInstance, subnetipaddressFault), 
                    (slbPortIntance, slbPortFault)
                  ],
        'health': [
                    (slbInstance, slbInstanceHealth),
                  ] 
    }
    return returnValue 

    '''
    pass

def serviceAudit( device,
                  configuration ):
    pass

#
# EndPoint/Network API
#
@sampleDevice_logger
def attachEndpoint( device,
                    configuration,
                    connector,
                    ep ):
    pass
 
@sampleDevice_logger
def detachEndpoint( device,
                    configuration,
                    connector,
                    ep ):
    pass

@sampleDevice_logger
def attachNetwork( device,
                   connectivity,
                   configuration,
                   connector,
                   nw ):
    pass

@sampleDevice_logger
def detachNetwork( device,
                   connectivity,
                   configuration,
                   connector,
                   nw ):
    pass

@sampleDevice_logger
def serviceHealth( device,
                   name,
                   connectivity,
                   configuration ):
    pass

@sampleDevice_logger
def serviceCounters( device,
                     name,
                     connectivity,
                     configuration,
                     connector ):
    pass



########NEW FILE########
__FILENAME__ = createAppProfile
import sys
sys.path.append('pysdk')
from insieme.mit import access
access.rest()
directory = access.MoDirectory(ip='172.21.128.100', port='8000', user='admin', password='password')
polUni = directory.lookupByDn('uni')
fvTenantMo = directory.create('fv.Tenant', polUni, name='Tenant1')
fvApMo = directory.create('fv.Ap', fvTenantMo, name='WebApp')
d = directory.commit(polUni)

########NEW FILE########
__FILENAME__ = createTenant
import sys
sys.path.append('pysdk')
from insieme.mit import access
access.rest()
directory = access.MoDirectory(ip='172.21.128.100', port='8000', user='admin', password='password')
polUni = directory.lookupByDn('uni')
fvTenantMo = directory.create('fv.Tenant', polUni, name='Tenant1')
d = directory.commit(polUni)

########NEW FILE########
__FILENAME__ = createThreeTierExample
import sys
sys.path.append('pysdk')
from insieme.mit import access
access.rest()
directory = access.MoDirectory(ip='172.21.128.100', port='8000', user='admin', password='password')
polUni = directory.lookupByDn('uni')
fvTenant = directory.create('fv.Tenant', polUni, name='T2')
fvCtx = directory.create('fv.Ctx', fvTenant, name='T2')
fvBD = directory.create('fv.BD', fvTenant, name='BD1')
fvRsCtx = directory.create('fv.RsCtx', fvBD, tnFvCtxName='T2')
fvSubnet = directory.create('fv.Subnet', fvBD, ip='10.0.0.128/24', scope='private')
fvSubnet = directory.create('fv.Subnet', fvBD, ip='10.0.1.128/24', scope='public')
aaaDomainRef = directory.create('aaa.DomainRef', fvTenant, name='T2')
vzFilter = directory.create('vz.Filter', fvTenant, name='rmi')
vzEntry = directory.create('vz.Entry', vzFilter, etherT='ipv4', prot='6', dFromPort='1099', dToPort='1099', name='FilterEntry')
vzFilter = directory.create('vz.Filter', fvTenant, name='http')
vzEntry = directory.create('vz.Entry', vzFilter, etherT='ipv4', prot='6', dFromPort='80', dToPort='80', name='FilterEntry')
vzFilter = directory.create('vz.Filter', fvTenant, name='oracle')
vzEntry = directory.create('vz.Entry', vzFilter, etherT='ipv4', prot='6', dFromPort='1521', dToPort='1521', name='FilterEntry')
vzBrCP = directory.create('vz.BrCP', fvTenant, name='RMI')
vzSubj = directory.create('vz.Subj', vzBrCP, name='rmi')
vzRsSubjFiltAtt = directory.create('vz.RsSubjFiltAtt', vzSubj, tDn='uni/tn-T2/flt-rmi')
vzBrCP = directory.create('vz.BrCP', fvTenant, name='HTTP')
vzSubj = directory.create('vz.Subj', vzBrCP, name='http')
vzRsSubjFiltAtt = directory.create('vz.RsSubjFiltAtt', vzSubj, tDn='uni/tn-T2/flt-http')
vzBrCP = directory.create('vz.BrCP', fvTenant, name='ORACLE')
vzSubj = directory.create('vz.Subj', vzBrCP, name='oracle')
vzRsSubjFiltAtt = directory.create('vz.RsSubjFiltAtt', vzSubj, tDn='uni/tn-T2/flt-oracle')
fvAp = directory.create('fv.Ap', fvTenant, name='www.T2.com')
fvAEPg = directory.create('fv.AEPg', fvAp, name='APP')
fvRsBd = directory.create('fv.RsBd', fvAEPg, tnFvBDName='BD1')
fvRsCons = directory.create('fv.RsCons', fvAEPg, tDn='uni/tn-T2/brc-ORACLE')
fvRsProv = directory.create('fv.RsProv', fvAEPg, tDn='uni/tn-T2/brc-RMI')
fvAEPg = directory.create('fv.AEPg', fvAp, name='WEB')
fvRsBd = directory.create('fv.RsBd', fvAEPg, tnFvBDName='BD1')
fvRsCons = directory.create('fv.RsCons', fvAEPg, tDn='uni/tn-T2/brc-RMI')
fvRsProv = directory.create('fv.RsProv', fvAEPg, tDn='uni/tn-T2/brc-HTTP')
fvAEPg = directory.create('fv.AEPg', fvAp, name='DB')
fvRsBd = directory.create('fv.RsBd', fvAEPg, tnFvBDName='BD1')
fvSubnet = directory.create('fv.Subnet', fvAEPg, ip='100.1.3.1/24')
fvRsProv = directory.create('fv.RsProv', fvAEPg, tDn='uni/tn-T2/brc-ORACLE')
l3extOut = directory.create('l3ext.Out', fvTenant, name='Outside')
l3extInstP = directory.create('l3ext.InstP', l3extOut, name='Outside')
l3extSubnet = directory.create('l3ext.Subnet', l3extInstP, ip='0.0.0.0')
fvRsCons = directory.create('fv.RsCons', l3extInstP, tDn='uni/tn-T2/brc-HTTP')
l3extLNodeP = directory.create('l3ext.LNodeP', l3extOut, name='node18')
l3extRsNodeL3OutAtt = directory.create('l3ext.RsNodeL3OutAtt', l3extLNodeP, tDn='topology/pod-1/node-18', rtrId='1.2.3.4')
bgpPeerP = directory.create('bgp.PeerP', l3extLNodeP, addr='10.10.10.10')
l3extLIfP = directory.create('l3ext.LIfP', l3extLNodeP, name='port18')
l3extRsPathL3OutAtt = directory.create('l3ext.RsPathL3OutAtt', l3extLIfP, ifInstT='l3-port', addr='1.2.3.4', tDn='topology/pod-1/paths-18/pathep-[eth1/31]')
bgpExtP = directory.create('bgp.ExtP', l3extOut)
l3extRsEctx = directory.create('l3ext.RsEctx', l3extOut, tnFvCtxName='T2')
bgpCtxPol = directory.create('bgp.CtxPol', fvTenant, name='bgpCtxPolicy')
bgpPeerPfxPol = directory.create('bgp.PeerPfxPol', fvTenant, name='bgpPeerPolicy')
d = directory.commit(fvTenant)

########NEW FILE########
__FILENAME__ = getObjectDetails
#!/usr/bin/env python

# Copyright (C) 2013 Cisco Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); 
# you may not use this file except in compliance with the License. 
# You may obtain a copy of the License at 
# 
#      http://www.apache.org/licenses/LICENSE-2.0 
# 
# Unless required by applicable law or agreed to in writing, software 
# distributed under the License is distributed on an "AS IS" BASIS, 
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
# See the License for the specific language governing permissions and 
# limitations under the License. 

import os
import sys
from argparse import ArgumentParser

# pysdk should be in the same directory as this script. If not, update this path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pysdk'))

def printInfo(o,d=0):
	# Print some spaces based on depth, and the distinguished name of the object
	print ' ' * (d*4), o.getDn()
	# Print the type of the object
	print ' ' * ((d*4)+1), 'type: %s' % (o.getClass().getName())
	# Print the names and values of the objects properties
	for p in o.getProperties():
		n = p.getName()
		v = o.getPropertyValue(p.getName())
		if v is not '':
			print ' ' * ((d*4)+2), '%s: %s' % (n, v)

def queryObjects(moDir, objects, limit, depth=0):
	for o in objects:
		# Print the details for this object
		printInfo(o,depth)
		# if we haven't reached our depth limit, recurse through the children of this object and print it's details
		if depth < limit:
			moDir.fetchChildren(o)
			queryObjects(moDir, o.getChildren(), limit, depth + 1)

def main():
	parser = ArgumentParser(str(__file__))
	parser.add_argument('-i', '--ip', help='IFC IP Address', default='172.21.197.80')
	parser.add_argument('-p', '--port', help='IFC Port', default='8000')
	parser.add_argument('-U', '--username', help='Username', default='admin')
	parser.add_argument('-P', '--password', help='Password', default='ins3965!')
	parser.add_argument('-o', '--object', help='Object class to query for (e.g., fvTenant, infraInfra)', required=True)
	parser.add_argument('-d', '--depth', help='Query depth: How many levels under the top level object to query', default=2)
	args = parser.parse_args()

	# Import the access library from the insieme python SDK
	from insieme.mit import access
	# Change the access mode to REST
	access.rest()
	# Connect to the IFC REST interface and authenticate using the specified credentials 
	directory = access.MoDirectory(ip=args.ip, port=args.port, user=args.username, password=args.password)
	depth = int(args.depth)

	# Query the IFC for object type passed as argument and print depth specified
	tenants = directory.lookupByClass(args.object)
	queryObjects(directory, tenants, depth)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = createUser
#!/usr/bin/env Python
#
# Sample code to interact with APIC's REST API _without_ the Python SDK
#
# this code simply POSTs XML at the right URL to create a user in the system
# it can easily be adapted to use any of the other XML examples that are in this folder
# 

import urllib2
import base64

handlers = []
hh = urllib2.HTTPHandler()
hh.set_http_debuglevel(0)
handlers.append(hh)

http_header={"User-Agent" : "Chrome/17.0.963.46",
             "Accept" : "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,text/png,*/*;q=0.5",
             "Accept-Language" : "en-us,en;q=0.5",
             "Accept-Charset" : "ISO-8859-1",
             "Content-type": "application/x-www-form-urlencoded"
            }

def createAuthHeader(username,password):
    base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
    return ('Basic %s' % base64string)

def getAPICCookie(ip_addr, authheader, username, password):
    url = 'http://'+ip_addr+':8000/api/aaaLogin.xml'

    # create 'opener' (OpenerDirector instance)
    opener = urllib2.build_opener(*handlers)
    # Install the opener.
    # Now all calls to urllib2.urlopen use our opener.
    urllib2.install_opener(opener)

    http_header["Host"]=ip_addr
    xml_string = "<aaaUser name='%s' pwd='%s'/>" % (username, password)
    req = urllib2.Request(url=url, data=xml_string, headers=http_header)

    try:
      response = urllib2.urlopen(req)
    except urllib2.URLError, e:
      print 'Failed to obtain auth cookie: %s' % (e)
      return 0
    else:
      rawcookie=response.info().getheaders('Set-Cookie')
      return rawcookie[0]

def createUser(ip_addr, cookie, username, password, role):
    url = 'http://'+ip_addr+':8000/api/policymgr/mo/uni/userext.xml'
    opener = urllib2.build_opener(*handlers)
    urllib2.install_opener(opener)
    http_header["Host"]=ip_addr
    http_header["Cookie"]=cookie

    xml_string="<aaaUser name='" + username + "' phone='' pwd='" + password + "'>  \
                 <aaaUserDomain childAction='' descr='' name='all' rn='userdomain-all' status=''> \
                  <aaaUserRole childAction='' descr='' name='" + role + "' privType='writePriv'/>  \
                 </aaaUserDomain> \
                </aaaUser>" 

    req = urllib2.Request(url=url,data=xml_string,headers=http_header)

    try:
     response = urllib2.urlopen(req)
    except urllib2.URLError, e:
     print "URLLIB2 error:\n  %s\n  URL: %s\n  Reason: %s" % (e, e.url, e.reason)
    else:
     return response


#################
#  MAIN MODULE  #
#################

# First things first: credentials. They should be parsed through sys.argv[] ideally ..
ip="<APIC_IP>"
user="admin"
password="password"

basicauth=createAuthHeader(user, password)
cookie=getAPICCookie(ip, basicauth, user, password)
if cookie:
    print "We have a cookie:\n  %s\n" % cookie
    print "Creating user ..\n"
    r=createUser(ip, cookie, "my_user", "my_password", "admin")
    print r.read()

########NEW FILE########
__FILENAME__ = check_cable

# Copyright (C) 2013 Cisco Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); 
# you may not use this file except in compliance with the License. 
# You may obtain a copy of the License at 
# 
#      http://www.apache.org/licenses/LICENSE-2.0 
# 
# Unless required by applicable law or agreed to in writing, software 
# distributed under the License is distributed on an "AS IS" BASIS, 
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
# See the License for the specific language governing permissions and 
# limitations under the License. 

import time

import urllib
import urllib2

import json
import contextlib
import threading
import base64

import sys
import socket

sys.path.append("../utils")

from nxapi_utils import NXAPI

def get_connectivity(url, method="cdp"):
    nxapi = NXAPI()
    nxapi.set_target_url(url)
    nxapi.set_username("admin")
    nxapi.set_password("insieme")
    nxapi.set_msg_type("cli_show")
    nxapi.set_out_format("json")
    nxapi.set_cmd("show switchname")
    headers, resp = nxapi.send_req()
    resp_obj = json.loads(resp)

    switchname = resp_obj["ins_api"]["outputs"]["output"]["body"]["hostname"]
    if method == "cdp":
        nxapi.set_cmd("show cdp neighbor")
        headers, resp = nxapi.send_req()
        resp_obj = json.loads(resp)

        neighbors = resp_obj["ins_api"]["outputs"]["output"]["body"]["TABLE_cdp_neighbor_brief_info"]["ROW_cdp_neighbor_brief_info"]
        connectivity_list = list()
        for i in range (0, len(neighbors)):
            remote_switch = neighbors[i]["device_id"]
            index = remote_switch.find("(")
            if index != -1:
                remote_switch = remote_switch[0:index]
            one_neighbor = '{0};{1};{2};{3}'.format(switchname, 
                                                   neighbors[i]["intf_id"],
                                                   remote_switch,
                                                   neighbors[i]["port_id"])
            connectivity_list.append(one_neighbor)
    else:
        nxapi.set_cmd("show lldp neighbor")
        headers, resp = nxapi.send_req()
        resp_obj = json.loads(resp)

        neighbors = resp_obj["ins_api"]["outputs"]["output"]["body"]["TABLE_nbor"]["ROW_nbor"]
        connectivity_list = list()
        for i in range (0, len(neighbors)):
            remote_switch = neighbors[i]["chassis_id"]
            index = remote_switch.find("(")
            if index != -1:
                remote_switch = remote_switch[0:index]
            one_neighbor = '{0};{1};{2};{3}'.format(switchname, 
                                                   neighbors[i]["l_port_id"],
                                                   remote_switch,
                                                   neighbors[i]["port_id"])
            connectivity_list.append(one_neighbor)
    return connectivity_list


def do_work(switches, blueprint, method):

    connectivities = list()
    for i in range(0, len(switches)):
        connectivities.append(get_connectivity(switches[i], method))

    print "######################## Connectivity BEGIN #############################"
    for i in range(0, len(connectivities)):
        print "******************************************************************"
        for j in range(0, len(connectivities[i])):
            items = connectivities[i][j].split(";")
            print "[" + items[0] + "]:" + items[1] + " ------> [" + items[2] + "]:" + items[3]
    print ""
    print "######################## Bidirection Check Result #######################"
    for i in range(0, len(connectivities)):
        conn1 = connectivities[i]
        for j in range(i + 1, len(connectivities)):
            conn2 = connectivities[j]
            for k in range(0, len(conn1)):
                items1 = conn1[k].split(";")
                for l in range(0, len(conn2)):
                    items2 = conn2[l].split(";")
                    if items1[0] == items2[2] and items1[1] == items2[3]:
                        print "[" + items1[0] + "]:" + items1[1] + " ---> [" + items1[2] + "]:" + items1[3] + " Connected!"
    print ""
    print "######################## DB Conformance Check Result #####################"
    conn_db = ""
    with open(blueprint, 'r') as content_file:
        conn_db = content_file.read()
    conn_obj = json.loads(conn_db)
    conn_db_list = list()
    nes = conn_obj["ne"]
    for i in range(0, len(nes)):
        ne_name = conn_obj["ne"][i]["name"]
        conns = conn_obj["ne"][i]["connectivity"]
        for j in range(0, len(conns)):
            conn = '{0};{1};{2};{3}'.format(ne_name,
                                              conn_obj["ne"][i]["connectivity"][j]["local_ifx"],
                                              conn_obj["ne"][i]["connectivity"][j]["remote_ne"],
                                              conn_obj["ne"][i]["connectivity"][j]["remote_ifx"])
            conn_db_list.append(conn)
    match_set = set()

    for i in range(0, len(conn_db_list)):
        for j in range(0, len(connectivities)):
            for k in range(0, len(connectivities[j])):
                if method == "lldp":
                    conn_db_list[i] = conn_db_list[i].replace("Ethernet", "Eth")
                if conn_db_list[i] == connectivities[j][k]:
                    items = connectivities[j][k].split(";")
                    print "[" + items[0] + "]:" + items[1] + " ------> [" + items[2] + "]:" + items[3] + " Check Done!"
                    match_set.add(i)

    for i in range(0, len(conn_db_list)):
        if i in match_set:
            continue
        items = conn_db_list[i].split(";")
        print "[" + items[0] + "]:" + items[1] + " ------> [" + items[2] + "]:" + items[3] + " Check Failed!"


# Example: python check_cable.py 10.30.14.11 connectivity.json cdp
if __name__ == "__main__":
    switches = list()
    for i in range(1, len(sys.argv)-2):
        switches.append('http://{0}/ins'.format(sys.argv[i]))
    blueprint = sys.argv[len(sys.argv)-2]
    method = sys.argv[len(sys.argv)-1]
    do_work(switches, blueprint, method)
    

########NEW FILE########
__FILENAME__ = nxapi_basics
#!/usr/bin/env python
#
# tested with build n9000-dk9.6.1.2.I1.1.510.bin
#
# Copyright (C) 2013 Cisco Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); 
# you may not use this file except in compliance with the License. 
# You may obtain a copy of the License at 
# 
#      http://www.apache.org/licenses/LICENSE-2.0 
# 
# Unless required by applicable law or agreed to in writing, software 
# distributed under the License is distributed on an "AS IS" BASIS, 
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
# See the License for the specific language governing permissions and 
# limitations under the License. 

import urllib2
from xml.dom import minidom
import base64


handlers = []
hh = urllib2.HTTPHandler()
hh.set_http_debuglevel(0)
handlers.append(hh)

def CreateAuthHeader(username,password):
    base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
    return ("Basic %s" % base64string)

def GetiAPICookie(ip_addr, authheader, username, password):
    global password_mgr
    url = 'http://'+ip_addr+'/ins/'

    # create "opener" (OpenerDirector instance)
    opener = urllib2.build_opener(*handlers)
    opener.addheaders = [('Authorization', authheader),]
    # Install the opener.
    # Now all calls to urllib2.urlopen use our opener.
    urllib2.install_opener(opener)

    xml_string="<?xml version=\"1.0\" encoding=\"ISO-8859-1\"?> \
      <ins_api>                         \
      <version>0.1</version>            \
      <type>cli_show</type>             \
      <chunk>0</chunk>                  \
      <sid>session1</sid>               \
      <input>show clock</input>         \
      <output_format>xml</output_format>\
      </ins_api>"

    # Call iAPI with show clock just to get a response that contains a cookie
    req = urllib2.Request(url=url, data=xml_string,)

    try:
      response = urllib2.urlopen(req)
    except urllib2.URLError, e:
      print e.code
      print e.read()
    else:
      rawcookie=response.info().getheaders('Set-Cookie')
      return rawcookie[0]


def ExecuteiAPICommand(ip_addr, cookie, authheader, cmd_type, cmd):
    url = 'http://'+ip_addr+'/ins/'
    opener = urllib2.build_opener(*handlers)
    opener.addheaders = [('Cookie', cookie),]
    urllib2.install_opener(opener)

    xml_string="<?xml version=\"1.0\" encoding=\"ISO-8859-1\"?> \
     <ins_api>                          \
     <version>0.1</version>             \
     <type>" + cmd_type + "</type>      \
     <chunk>0</chunk>                   \
     <sid>session1</sid>                \
     <input>" + cmd + "</input>         \
     <output_format>xml</output_format> \
     </ins_api>"

    req = urllib2.Request(url=url,
                           data=xml_string,
                           headers={'Authorization': authheader})

    try:
     response = urllib2.urlopen(req)
    except urllib2.URLError, e:
     print e.code
     print e.read()
    else:
     return response

def GetNodeDataDom(dom,nodename):
    # given a XML document, find an element by name and return it as a string
    try:
     node=dom.getElementsByTagName(nodename)
     return (NodeAsText(node))
    except IndexError:
     return "__notFound__"

def NodeAsText(node):
    # convert a XML element to a string
    try:
     nodetext=node[0].firstChild.data.strip()
     return nodetext
    except IndexError:
     return "__na__"   

def getModules(xml):
    modules = xml.getElementsByTagName("ROW_modinfo")

    # build a dictionary of switch modules with key = slot number
    # the format of the dictionary is as follows:
    # mods = {'slot': {modtype: 'foo', ports: 'n', model: 'bar', status: 'ok'}}    
    moddict = {}
    for module in modules:
        modslot =   NodeAsText(module.getElementsByTagName("modinf"))
        modtype =   NodeAsText(module.getElementsByTagName("modtype"))
        modports =  NodeAsText(module.getElementsByTagName("ports"))
        try:
            modmodel =  NodeAsText(module.getElementsByTagName("model"))
        except:
            modmodel = '__na__'
        modstatus = NodeAsText(module.getElementsByTagName("status"))
        moddict[modslot]={'type': modtype, \
                          'ports': modports, \
                          'model': modmodel, \
                          'status': modstatus}
    return moddict

def getCDP(xml):
    neighbors = xml.getElementsByTagName("ROW_cdp_neighbor_detail_info")

    # build a dictionary of CDP neighbors with key = interface
    # the format of the dictionary is as follows:
    # neighbors = {'intf': {neighbor: 'foo', remoteport: 'x/y', model: 'bar'}}    
    cdpdict = {}
    for neighbor in neighbors:
        cdpintf  =  NodeAsText(neighbor.getElementsByTagName("intf_id"))
        cdpneig  =  NodeAsText(neighbor.getElementsByTagName("device_id"))
        cdpport  =  NodeAsText(neighbor.getElementsByTagName("port_id"))
        cdpmodel =  NodeAsText(neighbor.getElementsByTagName("platform_id"))
        cdpipaddr = NodeAsText(neighbor.getElementsByTagName("v4addr"))
        cdpdict[cdpintf]={'neighbor': cdpneig, \
                          'remoteport': cdpport, \
                          'model': cdpmodel,\
                          'ipaddr': cdpipaddr}
    return cdpdict



#################
#  MAIN MODULE  #
#################

# First things first: credentials. They should be parsed through sys.argv[] ideally ..
ip=".."
user=".."
password=".."

basicauth=CreateAuthHeader(user, password)
cookie=GetiAPICookie(ip, basicauth, user, password)

# Example 1: obtain hostname, chassis ID, NXOS version, serial number
dom = minidom.parse(ExecuteiAPICommand(ip, cookie, basicauth, "cli_show", "show version"))
host_name=GetNodeDataDom(dom,"host_name")
chassis_id=GetNodeDataDom(dom,"chassis_id")
kickstart_ver_str=GetNodeDataDom(dom,"kickstart_ver_str")
cpu_name=GetNodeDataDom(dom,"cpu_name")
proc_board_id=GetNodeDataDom(dom,"proc_board_id")
print("System {0} is a {1} running {2}".format(host_name, chassis_id, kickstart_ver_str))
print("Its serial number is {0}".format(proc_board_id))
print("CPU is {0}\n".format(cpu_name))

# Example 2: create 10 new VLANs
vlan=555
while vlan<=564:
    dom = minidom.parse(ExecuteiAPICommand(ip, cookie, basicauth, \
                                   "cli_conf", "vlan " + str(vlan) + " ; name Created_by_NXAPI"))
    if GetNodeDataDom(dom,"msg")=="Success":
        print("Config mode: Vlan %s created" % vlan)
    vlan+=1
    
# Example 3: create a new loopback interface
dom = minidom.parse(ExecuteiAPICommand(ip, cookie, basicauth, "cli_conf", \
                                   "interface loopback 99 ; \
                                    ip addr 9.9.9.9/32 ; \
                                    descr Created by Python iAPI code"))
if GetNodeDataDom(dom,"msg")=="Success":
    print("Config mode: Loopback 99 created")

# Example 4: delete one of the VLANs we created
dom = minidom.parse(ExecuteiAPICommand(ip, cookie, basicauth, \
                                   "cli_conf", "no vlan 444"))
if GetNodeDataDom(dom,"msg")=="Success":
    print("Config mode: Vlan 444 deleted")

# Example 5: iterate over "show modules"
dom = minidom.parse(ExecuteiAPICommand(ip, cookie, basicauth, "cli_show", "show mod"))
moddict=getModules(dom)
print("\nList of modules:\n================")
for module in sorted(moddict.keys()):
    print "Slot {0}: {1}({2}),{3} ports. Status: {4}"\
          .format(module,moddict[module]['type'],\
                         moddict[module]['model'],\
                         moddict[module]['ports'],\
                         moddict[module]['status'])

# Example 6: get CDP neighbors
dom = minidom.parse(ExecuteiAPICommand(ip, cookie, basicauth, "cli_show", "show cdp neighbors detail"))
cdpdict=getCDP(dom)
print("\nCDP Neighbors:\n==============")
for interface in sorted(cdpdict.keys()):
    print "Interface {0} is connected to {1} of {2}({3} @ {4})"\
          .format(interface,cdpdict[interface]['remoteport'],\
                            cdpdict[interface]['neighbor'],\
                            cdpdict[interface]['model'],\
                            cdpdict[interface]['ipaddr'])

########NEW FILE########
__FILENAME__ = nx-api_authhandlers
#
# Copyright (C) 2013 Cisco Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0 
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
""" nx-api_authhandlers.py - a custom authentication handler for Cisco's NX-API
    to handle the nxapi_auth cookie to ensure that the cookie is loaded from a 
    file and sent in a request so that basic authentication is not needed again.
    Must be used in conjunction with a custom response handler that then
    receives the the cookie in the response and saves it to the file.

    This is accomplished by the response handler saving the cookie in a cookie
    file in the (hopefully) platform agnostic way using the tempfile module to
    do a tempfile.gettempdir() to find the directory and the file should be
    specifically named the same as the REST API action configured on the splunk
    server.

    The required custom authentication handler configuration in the Rest API
    action data input is as follows:

        Custom Authentication Handler: NxApiAuthHandler
        Custom Authentication Handler Arguments:
            username=<username>,password=<password>,name=<name>

     Where:

         :param username: The username used to authenticate the user.
         :param password: The password used to authenticate the user.
         :param name: A unique name for the Rest API action configured as a
             data input, the common practice is to set this to the "Rest API
             Input Name" and this must match the name from the "Response
             Handler Arguments" configuration.A

    This custom authentication handler should be merged into:
        rest_ta/bin/authhandlers.py

    Tested with Splunk version 6.0 & Rest API Modular Input v1.3.2
"""
import os
from requests.auth import AuthBase
from base64 import b64encode
import pickle
import tempfile

class NxApiAuthHandler(AuthBase):
    """ The basic framework for NxApiAuthHandler comes straight from the
        Requests module HTTPBasicAuth class.  We add the NX-API specific cookie
        handling.  The basic idea is that this custom authentication handler
        will, try to read the cookie from a temporary file.  If no file is
        found then it simply sends the basic auth.  If a cookie is found, 
        then the request is sent with the basic auth + the cookie in the
        headear as NX-API requires.

        In order for this to work, a custom response handler has to also 
        be added.  On the response, the custom response handler will store
        the nxapi_auth cookie provided by the NX-API enabled switch to the
        file so that the custom authentication handler can do its job.

        :param username: The username to be sent to the NX-API enabled switch
        :param password: The password to be sent to the NX-API enabled switch
        :param name: The name Rest API input name that uniquely identifies
            the REST API input configuration, this must match the name
            parameter on the corresponding custom response handler.

        There has to be a corresponding custom response handler as well.
    """
    COOKIENAME = "nxapi_auth"
    def __init__(self, username, password, name):
        self.username = username
        self.password = password
        self.cookiefilename = self._get_cookiefilename(name)
        self.cookiejar = []
        self._update_cookiejar(name)

    def __call__(self, r):
        """ This gets called when a REST action is called.
            This retrieves the nxapi_auth cookie and adds it to the headers
            along with the authorization cookie.

            :param r: the request object
        """
        auth_str = self._basic_auth_str(self.username, self.password)
        r.headers['Authorization'] = auth_str
        self._update_cookiejar(self.cookiefilename)
        if "nxapi_auth" in self.cookiejar:
            r.headers['Cookie'] = self.COOKIENAME + "={0}".format(
                self.cookiejar[self.COOKIENAME])
        return r

    def _basic_auth_str(self, username, password):
        """ Returns a Basic Auth string, in base64 format. """
        return 'Basic ' + b64encode(('%s:%s' % (username,
            password)).encode('latin1')).strip().decode('latin1')

    def _update_cookiejar(self, cookiefilename):
        """ Updates the cookiejar attribute with the latest cookie from the
            cookiefile

            :param cookiefilename: The unique name for the file that should exist
                in the temporary directory
        """
        self.cookiefilename = self._get_cookiefilename(cookiefilename)
        if self.cookiefilename is not None:
            self.cookiejar = self._load_cookies(self.cookiefilename)
        else:
            self.cookiejar = []

    def _get_cookiefilename(self, cookiefilename):
        """ Obtains the absolute path for the cookie filename.  
            
            :param cookiefile: The unique name for the file that should exist
                in the temporary directory
        """
        temp_dir = tempfile.gettempdir()
        filename = os.path.join(temp_dir, cookiefilename or "")
        if os.path.isfile(filename):
            return filename
        else:
            return None

    def _load_cookies(self, filename):
        """ Load in cookies from a file

            :param filename: The file where the cookie is stored
        """
        with open(filename, 'rb') as f:
            return pickle.load(f)

########NEW FILE########
__FILENAME__ = nx-api_responsehandlers
#
# Copyright (C) 2013 Cisco Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0 
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
""" nx-api_responsehandlers.py - a custom response handler for Cisco's NX-API
    to handle the nxapi_auth cookie to ensure that the cookie is saved from
    the response so it can be persisted to the next request.  Must be used in
    conjunction with a custom authentication handler that then retrieves the
    cookie and sends it.

    This is accomplished by saving the cookie in a cookie file in the
    (hopefully) platform agnostic way using the tempfile module to do a 
    tempfile.gettempdir() then create or overwrite a file in that directory
    that is specifically named the same as the REST API action configured on
    the splunk server.

    The required custom response handler configuration in the Rest API action
    data input is as follows:

        Custom Response Handler: NxApiResponseHandler
        Custom Authentication Handler Arguments:
           name=<name> 

     Where:

         :param name: A unique name for the Rest API action configured as a
             data input, the common practice is to set this to the "Rest API
             Input Name" and this must match the name from the "Custom
             Authentication Handler Arguments" configuration. 

    This response handler should be merged into:
        rest_ta/bin/responsehandlers.py

    Tested with Splunk version 6.0 & Rest API Modular Input v1.3.2

"""
import os
import pickle
import tempfile

class NxApiResponseHandler:
    """ NxApiResponseHandler simply looks for a nxapi_auth cookie in the
        response from nxapi enabled device and overwrites any existing
        file in the temporary directory with the same filename of "name"
        where name is the name of the Rest API action that is running on
        the splunk server.

        In order for this to work completely there has to be a
        corresponding custom authentication handler that then utilizes that
        saved cookie.

        :param name: The name Rest API input name that uniquely identifies
            the REST API input configuration, this must match the name
            parameter on the corresponding custom response handler.
    """
    COOKIENAME = "nxapi_auth"
    def __init__(self, name, **args):
        self.cookiefilename = self._get_cookiefilename(name)

    def __call__(self, response_object, raw_response_output, response_type,
                 req_args, endpoint):
        """ This gets called when the response is received by this Rest API
            input.  It simply looks for the approriate cookie in the response
            and if one is found it unconditionally tries to unlink the old
            cookie file and save the cookie under a new file.
        """
        if self.COOKIENAME in response_object.cookies:
            try: os.unlink(self.cookiefilename)
            except: pass
            self._save_cookie(response_object.cookies)
        print_xml_stream(raw_response_output)

    def _get_cookiefilename(self, cookiefilename):
        """ Obtains the absolute path for the cookie filename.  

            :param cookiefile: The unique name for the file that should exist
                in the temporary directory
        """
        temp_dir = tempfile.gettempdir()
        filename = os.path.join(temp_dir, cookiefilename)
        return filename
        
    def _save_cookie(self, r_cookies):
        """" Write the cookie out to the file """
        with open(self.cookiefilename, "wb") as cookiefile:
            pickle.dump(r_cookies, cookiefile)
            cookiefile.flush()


########NEW FILE########
__FILENAME__ = errors
# Copyright (C) 2013 Cisco Systems Inc.
# All rights reserved
class cli_syntax_error(Exception):
        def __init__(self, value):
                self.value = value
        def __str__(self):
                return repr(self.value)

class cmd_exec_error(Exception):
        def __init__(self, value):
                self.value = value
        def __str__(self):
                return repr(self.value)

class unexpected_error(Exception):
        def __init__(self, value):
                self.value = value
        def __str__(self):
                return repr(self.value)

class structured_output_not_supported_error(Exception):
        def __init__(self, value):
                self.value = value
        def __str__(self):
                return repr(self.value)

class data_type_error(Exception):
        def __init__(self, value):
                self.value = value
        def __str__(self):
                return repr(self.value)

class api_not_supported_error(Exception):
        def __init__(self, value):
                self.value = value
        def __str__(self):
                return repr(self.value)
########NEW FILE########
__FILENAME__ = nxapi_utils
# Copyright (C) 2013 Cisco Systems Inc.
# All rights reserved
import urllib2

import contextlib
import base64

import socket

import httplib
from httplib import HTTPConnection, HTTPS_PORT
import ssl

from lxml import etree
import json
import xmltodict

from errors import *


class HTTPSConnection(HTTPConnection):

    '''This class allows communication via SSL.'''

    default_port = HTTPS_PORT

    def __init__(
        self,
        host,
        port=None,
        key_file=None,
        cert_file=None,
        strict=None,
        timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
        source_address=None,
        ):

        HTTPConnection.__init__(
            self,
            host,
            port,
            strict,
            timeout,
            source_address,
            )
        self.key_file = key_file
        self.cert_file = cert_file

    def connect(self):
        '''Connect to a host on a given (SSL) port.'''

        sock = socket.create_connection((self.host, self.port),
                self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()

        # this is the only line we modified from the httplib.py file
        # we added the ssl_version variable
        self.sock = ssl.wrap_socket(sock, self.key_file,
                                    self.cert_file,
                                    ssl_version=ssl.PROTOCOL_SSLv3)


httplib.HTTPSConnection = HTTPSConnection


class RequestMsg:

    def __init__(
        self,
        msg_type='cli_show',
        ver='0.1',
        sid='1',
        input_cmd='show version',
        out_format='json',
        do_chunk='0',
        ):

        self.msg_type = msg_type
        self.ver = ver
        self.sid = sid
        self.input_cmd = input_cmd
        self.out_format = out_format
        self.do_chunk = do_chunk

    def get_req_msg_str(
        self,
        msg_type='cli_show',
        ver='0.1',
        sid='1',
        input_cmd='show version',
        out_format='json',
        do_chunk='0',
        ):

        req_msg = '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        req_msg += '<ins_api>\n'
        req_msg += '<type>' + msg_type + '</type>\n'
        req_msg += '<version>' + ver + '</version>\n'
        req_msg += '<chunk>' + do_chunk + '</chunk>\n'
        req_msg += '<sid>' + sid + '</sid>\n'
        req_msg += '<input>' + input_cmd + '</input>\n'
        req_msg += '<output_format>' + out_format + '</output_format>\n'
        req_msg += '</ins_api>\n'
        return req_msg


class RespFetcher:

    def __init__(
        self,
        username='admin',
        password='insieme',
        url='http://172.21.128.227/ins',
        ):

        self.username = username
        self.password = password
        self.url = url
        self.base64_str = base64.encodestring('%s:%s' % (username,
                password)).replace('\n', '')

    def get_resp(
        self,
        req_str,
        cookie,
        timeout,
        ):

        req = urllib2.Request(self.url, req_str)
        req.add_header('Authorization', 'Basic %s' % self.base64_str)
        req.add_header('Cookie', '%s' % cookie)
        try:
            with contextlib.closing(urllib2.urlopen(req,
                                    timeout=timeout)) as resp:
                resp_str = resp.read()
                resp_headers = resp.info()
                return (resp_headers, resp_str)
        except socket.timeout, e:
            print 'Req timeout'
            raise


class RespFetcherHttps:

    def __init__(
        self,
        username='admin',
        password='insieme',
        url='https://172.21.128.227/ins',
        ):

        self.username = username
        self.password = password
        self.url = url
        self.base64_str = base64.encodestring('%s:%s' % (username,
                password)).replace('\n', '')

    def get_resp(
        self,
        req_str,
        cookie,
        timeout,
        ):

        req = urllib2.Request(self.url, req_str)
        req.add_header('Authorization', 'Basic %s' % self.base64_str)
        req.add_header('Cookie', '%s' % cookie)
        try:
            with contextlib.closing(urllib2.urlopen(req,
                                    timeout=timeout)) as resp:
                resp_str = resp.read()
                resp_headers = resp.info()
                return (resp_headers, resp_str)
        except socket.timeout, e:
            print 'Req timeout'
            raise


class NXAPITransport:
    '''N9000 Python objects off-the-box transport utilizing NX-API'''
    target_url = ''
    username = ''
    password = ''

    timeout = 10

    out_format = 'xml'
    do_chunk = '0'
    sid = 'sid'
    cookie = 'no-cookie'

    req_obj = RequestMsg()

    @classmethod
    def init(cls, target_url, username, password):
        cls.target_url = target_url
        cls.username = username
        cls.password = password
        cls.req_fetcher = RespFetcher(username=username,
                password=password, url=target_url)

    @classmethod
    def send_cmd_int(cls, cmd, msg_type):
        '''Construct NX-API message. Send commands through NX-API. Only single 
           command for show commands. Internal usage'''
        if msg_type == "cli_show" or msg_type == "cli_show_ascii":
            if " ;" in cmd:
                raise cmd_exec_error("Only single show command supported in internal api")

        req_msg_str = cls.req_obj.get_req_msg_str(msg_type=msg_type,
                input_cmd=cmd, out_format=cls.out_format,
                do_chunk=cls.do_chunk, sid=cls.sid)
        (resp_headers, resp_str) = \
            cls.req_fetcher.get_resp(req_msg_str, cls.cookie,
                cls.timeout)

        if 'Set-Cookie' in resp_headers:
            cls.cookie = resp_headers['Set-Cookie']
        content_type = resp_headers['Content-Type']
        root = etree.fromstring(resp_str)
        body = root.findall('.//body')
        code = root.findall('.//code')
        msg = root.findall('.//msg')

        output = ""
        status = 0
        if len(body) != 0:
            if msg_type == 'cli_show':
                output = etree.tostring(body[0])
            else:
                output = body[0].text

        if output == None:
            output = ""
        if code[0].text == "200":
            status = 0
        else:
            status = int(code[0].text)
        return [output, status, msg[0].text]

    @classmethod
    def send_cmd(cls, cmd, msg_type):
        '''Construct NX-API message. Send commands through NX-API. Multiple 
           commands okay'''
        req_msg_str = cls.req_obj.get_req_msg_str(msg_type=msg_type,
                input_cmd=cmd, out_format=cls.out_format,
                do_chunk=cls.do_chunk, sid=cls.sid)
        (resp_headers, resp_str) = \
            cls.req_fetcher.get_resp(req_msg_str, cls.cookie,
                cls.timeout)
        if 'Set-Cookie' in resp_headers:
            cls.cookie = resp_headers['Set-Cookie']
        content_type = resp_headers['Content-Type']
        root = etree.fromstring(resp_str)
        body = root.findall('.//body')
        code = root.findall('.//code')
        msg = root.findall('.//msg')

        # Any command execution error will result in the entire thing fail
        # This is to align with vsh multiple commands behavior
        if len(code) == 0:
            raise unexpected_error("Unexpected error")
        for i in range(0, len(code)):
            if code[i].text != "200":
                raise cmd_exec_error("Command execution error: {0}".format(msg[i].text))

        output = ""
        if msg_type == 'cli_show':
            for i in range(0, len(body)):
                output += etree.tostring(body[i])
        else:
            for i in range(0, len(body)):
                if body[i].text is None:
                    continue
                else:
                    output += body[i].text

        return output

    @classmethod
    def cli(cls, cmd):
        '''Run cli show command. Return show output'''
        try:
            output = cls.send_cmd(cmd, "cli_show_ascii")
            return output
        except:
            raise

    @classmethod
    def clip(cls, cmd):
        '''Run cli show command. Print show output'''
        try:
            output = cls.send_cmd(cmd, "cli_show_ascii")
            print output
        except:
            raise

    @classmethod
    def clic(cls, cmd):
        '''Run cli configure command. Return configure output'''
        try:
            output = cls.send_cmd(cmd, "cli_conf")
            return output
        except:
            raise

    @classmethod
    def clid(cls, cmd):
        '''Run cli show command. Return JSON output. Only XMLized commands 
           have outputs'''
        if " ;" in cmd:
            raise cmd_exec_error("Only single command is allowed in clid()")
        try:
            output = cls.send_cmd(cmd, "cli_show")
            o = xmltodict.parse(output)
            json_output = json.dumps(o["body"])
            return json_output
        except:
            raise


class NXAPI:
    '''A better NX-API utility'''
    def __init__(self):
        self.target_url = 'http://localhost/ins'
        self.username = 'admin'
        self.password = 'admin'
        self.timeout = 10

        self.ver = '0.1'
        self.msg_type = 'cli_show'
        self.cmd = 'show version'
        self.out_format = 'xml'
        self.do_chunk = '0'
        self.sid = 'sid'
        self.cookie = 'no-cookie'

    def set_target_url(self, target_url='http://localhost/ins'):
        self.target_url = target_url

    def set_username(self, username='admin'):
        self.username = username

    def set_password(self, password='admin'):
        self.password = password

    def set_timeout(self, timeout=0):
        if timeout < 0:
            raise data_type_error('timeout should be greater than 0')
        self.timeout = timeout

    def set_cmd(self, cmd=''):
        self.cmd = cmd

    def set_out_format(self, out_format='xml'):
        if out_format != 'xml' and out_format != 'json':
            raise data_type_error('out_format xml or json')
        self.out_format = out_format

    def set_do_chunk(self, do_chunk='0'):
        if do_chunk != 0 and do_chunk != 1:
            raise data_type_error('do_chunk 0 or 1')
        self.do_chunk = do_chunk

    def set_sid(self, sid='sid'):
        self.sid = sid

    def set_cookie(self, cookie='no-cookie'):
        self.cookie = cookie

    def set_ver(self, ver='0.1'):
        if ver != '0.1':
            raise data_type_error('Only ver 0.1 supported')
        self.ver = ver

    def set_msg_type(self, msg_type='cli_show'):
        if msg_type != 'cli_show' and msg_type != 'cli_show_ascii' \
            and msg_type != 'cli_conf' and msg_type != 'bash':
            raise data_type_error('msg_type incorrect')
        self.msg_type = msg_type

    def get_target_url(self):
        return self.target_url

    def get_username(self):
        return self.username

    def get_password(self):
        return self.username

    def get_timeout(self):
        return self.timeout

    def get_cmd(self):
        return self.cmd

    def get_out_format(self):
        return self.out_format

    def get_do_chunk(self):
        return self.do_chunk

    def get_sid(self):
        return self.sid

    def get_cookie(self):
        return self.cookie

    def req_to_string(self):
        req_msg = '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        req_msg += '<ins_api>\n'
        req_msg += '<type>' + self.msg_type + '</type>\n'
        req_msg += '<version>' + self.ver + '</version>\n'
        req_msg += '<chunk>' + self.do_chunk + '</chunk>\n'
        req_msg += '<sid>' + self.sid + '</sid>\n'
        req_msg += '<input>' + self.cmd + '</input>\n'
        req_msg += '<output_format>' + self.out_format + '</output_format>\n'
        req_msg += '</ins_api>\n'
        return req_msg

    def send_req(self):
         req = RespFetcher(self.username, self.password, self.target_url)
         return req.get_resp(self.req_to_string(), self.cookie, self.timeout)

########NEW FILE########
__FILENAME__ = RoutingTable
#Copyright (C) 2013 Matt Oswalt (http://keepingitclassless.net/) 

from nxapi_utils import *
from collections import OrderedDict
from array import *

#TODO: need to make more dynamic, for VRFs and IPv6 address families. Also need to figure out the various route types and make sure your classes are dynamic enough.

class Prefix:
    '''A class to define a route prefix'''
    def __init__(self):
        self.ipprefix = ''
        self.ucast_nhops = ''
        self.mcast_nhops = ''
        self.attached = False
        self.nexthops = []

    def set_ipprefix(self, ipprefix=''):
        self.ipprefix = ipprefix

    def set_ucast_nhops(self, ucast_nhops=''):
        self.ucast_nhops = ucast_nhops

    def set_mcast_nhops(self, mcast_nhops=''):
        self.mcast_nhops = mcast_nhops

    def set_attached(self, attached=False):
        self.attached = attached

    def set_nexthops(self, nexthops=[]):
        self.nexthops = nexthops


class NextHop:
    '''A class to define a next-hop route. Meant to be used in an array within the Prefix class'''
    #TODO: Looks like the number of fields that comes in varies when it's an OSPF route vs static or direct. need to test with various route types and ensure this data structure is appropriate for all
    def __init__(self):
        self.ipnexthop = ''
        self.ifname = ''
        self.uptime = ''
        self.pref = 0
        self.metric = 0
        self.clientname = ''
        self.hoptype = ''
        self.ubest = True

    def set_ipnexthop(self, ipnexthop=''):
        self.ipnexthop = ipnexthop

    def set_ifname(self, ifname=''):
        self.ifname = ifname

    def set_uptime(self, uptime=''):
        self.uptime = uptime

    def set_pref(self, pref=0):
        self.pref = pref

    def set_metric(self, metric=0):
        self.metric = metric

    def set_clientname(self, clientname=''):
        self.clientname = clientname

    def set_hoptype(self, hoptype=''):
        self.hoptype = hoptype

    def set_ubest(self, ubest=True):
        self.ubest = ubest

def getRoutes(url='',username='',password=''):
    thisNXAPI = NXAPI()
    thisNXAPI.set_target_url(url)
    thisNXAPI.set_username(username)
    thisNXAPI.set_password(password)
    thisNXAPI.set_msg_type('cli_show')
    thisNXAPI.set_cmd('show ip route')
    returnData = thisNXAPI.send_req()
    #print returnData[1]  #Uncomment to print the entire XML return

    doc = xmltodict.parse(returnData[1])

    #TODO: As-is, this would probably disregard any VRF other than "default" and also probably ignore IPv6. Need to go back and rewrite to be a little less static
    for k ,v in doc['ins_api']['outputs']['output']['body']['TABLE_vrf']['ROW_vrf']['TABLE_addrf']['ROW_addrf']['TABLE_prefix'].iteritems():
            docsub = v

    routes = []

    #Commented out but left most of the "print" lines that output dictionary structure. Can uncomment for debugging purpsoes.
    for prefix_row in docsub: #executes once for every prefix
        thisPrefix = Prefix()
        for key in prefix_row.keys():  # a simple display of keys and their values
            item_type=type(prefix_row[key])
            if item_type == OrderedDict:
                #If another OrderedDict, then these are properties of next-hop routes on this prefix and should be iterated through further.
                for t_key in prefix_row[key].keys():
                    if type(prefix_row[key][t_key]) == unicode:
                        print key,"==>",t_key,"==>",prefix_row[key][t_key] #This is here just to be exhaustive. Current output shouldn't give any unicode values here, only another OrderedDict
                    else:   #assuming ordered dictionary
                        #This is a single next-hop. All keys and values below are properties of this next-hop route.
                        thisNextHop = NextHop()
                        for tr_key in prefix_row[key][t_key].keys():
                            if tr_key == 'ipnexthop':
                                thisNextHop.set_ipnexthop(prefix_row[key][t_key][tr_key])
                            if tr_key == 'ifname':
                                thisNextHop.set_ifname(prefix_row[key][t_key][tr_key])
                            if tr_key == 'pref':
                                thisNextHop.set_pref(prefix_row[key][t_key][tr_key])
                            if tr_key == 'metric':
                                thisNextHop.set_metric(prefix_row[key][t_key][tr_key])
                            if tr_key == 'clientname':
                                thisNextHop.set_clientname(prefix_row[key][t_key][tr_key])
                            if tr_key == 'type':
                                thisNextHop.set_hoptype(prefix_row[key][t_key][tr_key])
                            if tr_key == 'ubest':
                                thisNextHop.set_ubest(bool(prefix_row[key][t_key][tr_key]))
                            #print key,"==>",t_key,"==>",tr_key,"==>",prefix_row[key][t_key][tr_key]
                        thisPrefix.nexthops.append(thisNextHop)
            elif item_type == unicode:
                #If unicode, then these are the properties for this entire prefix.
                if key == 'ipprefix':
                    thisPrefix.set_ipprefix(prefix_row[key])
                elif key == 'ucast-nhops':
                    thisPrefix.set_ucast_nhops(prefix_row[key])
                elif key == 'mcast-nhops':
                    thisPrefix.set_mcast_nhops(prefix_row[key])
                elif key == 'attached':
                    thisPrefix.set_attached(bool(prefix_row[key]))
                #print key,"==>",prefix_row[key]
            else:
                print "Warning: Unable to parse item type",item_type
        routes.append(thisPrefix)
    return routes


#And now, the Piece de resistance!!
#Just an example of course, you could do much more with this.

retrievedRoutes = getRoutes('http://10.2.1.8/ins', 'admin', 'Cisco.com')

for route in retrievedRoutes:
    print "The route to ", route.ipprefix, " has ", len(route.nexthops), " next-hop solutions"
    for nexthop in route.nexthops:
        print "via ", nexthop.ipnexthop, "out of", nexthop.ifname
########NEW FILE########
__FILENAME__ = xmltodict
#Copyright (C) 2012 Martin Blech and individual contributors.

#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#!/usr/bin/env python
"Makes working with XML feel like you are working with JSON"

from xml.parsers import expat
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl
try: # pragma no cover
    from cStringIO import StringIO
except ImportError: # pragma no cover
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO
try: # pragma no cover
    from collections import OrderedDict
except ImportError: # pragma no cover
    OrderedDict = dict

try: # pragma no cover
    _basestring = basestring
except NameError: # pragma no cover
    _basestring = str
try: # pragma no cover
    _unicode = unicode
except NameError: # pragma no cover
    _unicode = str

__author__ = 'Martin Blech'
__version__ = '0.5.0'
__license__ = 'MIT'

class ParsingInterrupted(Exception): pass

class _DictSAXHandler(object):
    def __init__(self,
                 item_depth=0,
                 item_callback=lambda *args: True,
                 xml_attribs=True,
                 attr_prefix='@',
                 cdata_key='#text',
                 force_cdata=False,
                 cdata_separator='',
                 postprocessor=None,
                 dict_constructor=OrderedDict,
                 strip_whitespace=True):
        self.path = []
        self.stack = []
        self.data = None
        self.item = None
        self.item_depth = item_depth
        self.xml_attribs = xml_attribs
        self.item_callback = item_callback
        self.attr_prefix = attr_prefix
        self.cdata_key = cdata_key
        self.force_cdata = force_cdata
        self.cdata_separator = cdata_separator
        self.postprocessor = postprocessor
        self.dict_constructor = dict_constructor
        self.strip_whitespace = strip_whitespace

    def startElement(self, name, attrs):
        attrs = self.dict_constructor(zip(attrs[0::2], attrs[1::2]))
        self.path.append((name, attrs or None))
        if len(self.path) > self.item_depth:
            self.stack.append((self.item, self.data))
            if self.xml_attribs:
                attrs = self.dict_constructor(
                    (self.attr_prefix+key, value)
                    for (key, value) in attrs.items())
            else:
                attrs = None
            self.item = attrs or None
            self.data = None

    def endElement(self, name):
        if len(self.path) == self.item_depth:
            item = self.item
            if item is None:
                item = self.data
            should_continue = self.item_callback(self.path, item)
            if not should_continue:
                raise ParsingInterrupted()
        if len(self.stack):
            item, data = self.item, self.data
            self.item, self.data = self.stack.pop()
            if self.strip_whitespace and data is not None:
                data = data.strip() or None
            if data and self.force_cdata and item is None:
                item = self.dict_constructor()
            if item is not None:
                if data:
                    self.push_data(item, self.cdata_key, data)
                self.item = self.push_data(self.item, name, item)
            else:
                self.item = self.push_data(self.item, name, data)
        else:
            self.item = self.data = None
        self.path.pop()

    def characters(self, data):
        if not self.data:
            self.data = data
        else:
            self.data += self.cdata_separator + data

    def push_data(self, item, key, data):
        if self.postprocessor is not None:
            result = self.postprocessor(self.path, key, data)
            if result is None:
                return item
            key, data = result
        if item is None:
            item = self.dict_constructor()
        try:
            value = item[key]
            if isinstance(value, list):
                value.append(data)
            else:
                item[key] = [value, data]
        except KeyError:
            item[key] = data
        return item

def parse(xml_input, encoding='utf-8', expat=expat, *args, **kwargs):
    """Parse the given XML input and convert it into a dictionary.

    `xml_input` can either be a `string` or a file-like object.

    If `xml_attribs` is `True`, element attributes are put in the dictionary
    among regular child elements, using `@` as a prefix to avoid collisions. If
    set to `False`, they are just ignored.

    Simple example::

        >>> doc = xmltodict.parse(\"\"\"
        ... <a prop="x">
        ...   <b>1</b>
        ...   <b>2</b>
        ... </a>
        ... \"\"\")
        >>> doc['a']['@prop']
        u'x'
        >>> doc['a']['b']
        [u'1', u'2']

    If `item_depth` is `0`, the function returns a dictionary for the root
    element (default behavior). Otherwise, it calls `item_callback` every time
    an item at the specified depth is found and returns `None` in the end
    (streaming mode).

    The callback function receives two parameters: the `path` from the document
    root to the item (name-attribs pairs), and the `item` (dict). If the
    callback's return value is false-ish, parsing will be stopped with the
    :class:`ParsingInterrupted` exception.

    Streaming example::

        >>> def handle(path, item):
        ...     print 'path:%s item:%s' % (path, item)
        ...     return True
        ...
        >>> xmltodict.parse(\"\"\"
        ... <a prop="x">
        ...   <b>1</b>
        ...   <b>2</b>
        ... </a>\"\"\", item_depth=2, item_callback=handle)
        path:[(u'a', {u'prop': u'x'}), (u'b', None)] item:1
        path:[(u'a', {u'prop': u'x'}), (u'b', None)] item:2

    The optional argument `postprocessor` is a function that takes `path`, `key`
    and `value` as positional arguments and returns a new `(key, value)` pair
    where both `key` and `value` may have changed. Usage example::

        >>> def postprocessor(path, key, value):
        ...     try:
        ...         return key + ':int', int(value)
        ...     except (ValueError, TypeError):
        ...         return key, value
        >>> xmltodict.parse('<a><b>1</b><b>2</b><b>x</b></a>',
        ...                 postprocessor=postprocessor)
        OrderedDict([(u'a', OrderedDict([(u'b:int', [1, 2]), (u'b', u'x')]))])

    You can pass an alternate version of `expat` (such as `defusedexpat`) by
    using the `expat` parameter. E.g:

        >>> import defusedexpat
        >>> xmltodict.parse('<a>hello</a>', expat=defusedexpat.pyexpat)
        OrderedDict([(u'a', u'hello')])

    """
    handler = _DictSAXHandler(*args, **kwargs)
    parser = expat.ParserCreate()
    parser.ordered_attributes = True
    parser.StartElementHandler = handler.startElement
    parser.EndElementHandler = handler.endElement
    parser.CharacterDataHandler = handler.characters
    try:
        parser.ParseFile(xml_input)
    except (TypeError, AttributeError):
        if isinstance(xml_input, _unicode):
            xml_input = xml_input.encode(encoding)
        parser.Parse(xml_input, True)
    return handler.item

def _emit(key, value, content_handler,
          attr_prefix='@',
          cdata_key='#text',
          root=True,
          preprocessor=None):
    if preprocessor is not None:
        result = preprocessor(key, value)
        if result is None:
            return
        key, value = result
    if not isinstance(value, (list, tuple)):
        value = [value]
    if root and len(value) > 1:
        raise ValueError('document with multiple roots')
    for v in value:
        if v is None:
            v = OrderedDict()
        elif not isinstance(v, dict):
            v = _unicode(v)
        if isinstance(v, _basestring):
            v = OrderedDict(((cdata_key, v),))
        cdata = None
        attrs = OrderedDict()
        children = []
        for ik, iv in v.items():
            if ik == cdata_key:
                cdata = iv
                continue
            if ik.startswith(attr_prefix):
                attrs[ik[len(attr_prefix):]] = iv
                continue
            children.append((ik, iv))
        content_handler.startElement(key, AttributesImpl(attrs))
        for child_key, child_value in children:
            _emit(child_key, child_value, content_handler,
                  attr_prefix, cdata_key, False, preprocessor)
        if cdata is not None:
            content_handler.characters(cdata)
        content_handler.endElement(key)

def unparse(item, output=None, encoding='utf-8', **kwargs):
    ((key, value),) = item.items()
    must_return = False
    if output == None:
        output = StringIO()
        must_return = True
    content_handler = XMLGenerator(output, encoding)
    content_handler.startDocument()
    _emit(key, value, content_handler, **kwargs)
    content_handler.endDocument()
    if must_return:
        value = output.getvalue()
        try: # pragma no cover
            value = value.decode(encoding)
        except AttributeError: # pragma no cover
            pass
        return value

if __name__ == '__main__': # pragma: no cover
    import sys
    import marshal

    (item_depth,) = sys.argv[1:]
    item_depth = int(item_depth)

    def handle_item(path, item):
        marshal.dump((path, item), sys.stdout)
        return True

    try:
        root = parse(sys.stdin,
                     item_depth=item_depth,
                     item_callback=handle_item,
                     dict_constructor=dict)
        if item_depth == 0:
            handle_item([], root)
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = poap
#!/bin/env python
#md5sum=5fddae8efacfc3b6acff9beb2a9e8bf3
# Still needs to be implemented.
# Return Values:
# 0 : Reboot and reapply configuration
# 1 : No reboot, just apply configuration. Customers issue copy file run ; copy
# run start. Do not use scheduled-config since there is no reboot needed. i.e.
# no new image was downloaded
# -1 : Error case. This will cause POAP to restart the DHCP discovery phase. 

# The above is the (embedded) md5sum of this file taken without this line, 
# can be # created this way: 
# f=poap.py ; cat $f | sed '/^#md5sum/d' > $f.md5 ; sed -i "s/^#md5sum=.*/#md5sum=$(md5sum $f.md5 | sed 's/ .*//')/" $f
# This way this script's integrity can be checked in case you do not trust
# tftp's ip checksum. This integrity check is done by /isan/bin/poap.bin).
# The integrity of the files downloaded later (images, config) is checked 
# by downloading the corresponding file with the .md5 extension and is
# done by this script itself.

import os
import time
from cli import *

# **** Here are all variables that parametrize this script **** 
# These parameters should be updated with the real values used 
# in your automation environment

# system and kickstart images, configuration: location on server (src) and target (dst)
n9k_image_version       = "6.1.2"
image_dir_src           = "/tftpb"
ftp_image_dir_src_root  = image_dir_src
tftp_image_dir_src_root = image_dir_src
n9k_system_image_src    = "n9000-dk9.%s.bin" % n9k_image_version
config_file_src         = "/tftpb/poap.cfg" 
image_dir_dst           = "bootflash:poap"
system_image_dst        = n9k_system_image_src
config_file_dst         = "volatile:poap.cfg"
md5sum_ext_src          = "md5"
# Required space on /bootflash (for config and system images)
required_space          = 350000

# copy protocol to download images and config
# options are: scp/http/tftp/ftp/sftp
protocol                = "scp" # protocol to use to download images/config

# Host name and user credentials
username                = "root" # tftp server account
ftp_username            = "anonymous" # ftp server account
password                = "root"
hostname                = "1.1.1.1"

# vrf info
vrf = "management"
if os.environ.has_key('POAP_VRF'):
    vrf=os.environ['POAP_VRF']

# Timeout info (from biggest to smallest image, should be f(image-size, protocol))
system_timeout          = 2100 
config_timeout          = 120 
md5sum_timeout          = 120  

# POAP can use 3 modes to obtain the config file.
# - 'static' - filename is static
# - 'serial_number' - switch serial number is part of the filename
# - 'location' - CDP neighbor of interface on which DHCPDISCOVER arrived
#                is part of filename
# if serial-number is abc, then filename is $config_file_src.abc
# if cdp neighbor's device_id=abc and port_id=111, then filename is config_file_src.abc_111
# Note: the next line can be overwritten by command-line arg processing later
config_file_type        = "static"

# parameters passed through environment:
# TODO: use good old argv[] instead, using env is bad idea.
# pid is used for temp file name: just use getpid() instead!
# serial number should be gotten from "show version" or something!
pid=""
if os.environ.has_key('POAP_PID'):
    pid=os.environ['POAP_PID']
serial_number=None
if os.environ.has_key('POAP_SERIAL'):
    serial_number=os.environ['POAP_SERIAL']
cdp_interface=None
if os.environ.has_key('POAP_INTF'):
    cdp_interface=os.environ['POAP_INTF']

# will append date/timespace into the name later
log_filename = "/bootflash/poap.log"
t=time.localtime()
now="%d_%d_%d" % (t.tm_hour, t.tm_min, t.tm_sec)
#now=None
#now=1 # hardcode timestamp (easier while debugging)

# **** end of parameters **** 
# *************************************************************

# ***** argv parsing and online help (for test through cli) ******
# ****************************************************************

# poap.bin passes args (serial-number/cdp-interface) through env var
# for no seeminly good reason: we allow to overwrite those by passing
# argv, this is usufull when testing the script from vsh (even simple
# script have many cases to test, going through a reboto takes too long)

import sys
import re

cl_cdp_interface=None  # Command Line version of cdp-interface
cl_serial_number=None  # can overwrite the corresp. env var
cl_protocol=None       # can overwride the script's default
cl_download_only=None  # dont write boot variables

def parse_args(argv, help=None):
    global cl_cdp_interface, cl_serial_number, cl_protocol, protocol, cl_download_only
    while argv:
        x = argv.pop(0)
        # not handling duplicate matches...
        if cmp('cdp-interface'[0:len(x)], x) == 0:
          try: cl_cdp_interface = argv.pop(0)
          except: 
             if help: cl_cdp_interface=-1
          if len(x) != len('cdp-interface') and help: cl_cdp_interface=None
          continue
        if cmp('serial-number'[0:len(x)], x) == 0:
          try: cl_serial_number = argv.pop(0)
          except: 
            if help: cl_serial_number=-1
          if len(x) != len('serial-number') and help: cl_serial_number=None
          continue
        if cmp('protocol'[0:len(x)], x) == 0:
          try: cl_protocol = argv.pop(0); 
          except: 
            if help: cl_protocol=-1
          if len(x) != len('protocol') and help: cl_protocol=None
          if cl_protocol: protocol=cl_protocol
          continue
        if cmp('download-only'[0:len(x)], x) == 0:
          cl_download_only = 1
          continue
        print "Syntax Error|invalid token:", x
        exit(-1)
  

########### display online help (if asked for) #################
nb_args = len(sys.argv)
if nb_args > 1:
  m = re.match('__cli_script.*help', sys.argv[1])
  if m:
    # first level help: display script description
    if sys.argv[1] == "__cli_script_help":
      print "loads system/kickstart images and config file for POAP\n"
      exit(0)
    # argument help
    argv = sys.argv[2:]
    # dont count last arg if it was partial help (no-space-question-mark)
    if sys.argv[1] == "__cli_script_args_help_partial":
      argv = argv[:-1]
    parse_args(argv, "help")
    if cl_serial_number==-1:
      print "WORD|Enter the serial number"
      exit(0)
    if cl_cdp_interface==-1:
      print "WORD|Enter the CDP interface instance"
      exit(0)
    if cl_protocol==-1:
      print "tftp|Use tftp for file transfer protocol"
      print "ftp|Use ftp for file transfer protocol"
      print "scp|Use scp for file transfer protocol"
      exit(0)
    if not cl_serial_number:
      print "serial-number|The serial number to use for the config filename"
    if not cl_cdp_interface:
      print "cdp-interface|The CDP interface to use for the config filename"
    if not cl_protocol:
      print "protocol|The file transfer protocol"
    if not cl_download_only:
      print "download-only|stop after download, dont write boot variables"
    print "<CR>|Run it (use static name for config file)"
    # we are done
    exit(0)

# *** now overwrite env vars with command line vars (if any given)
# if we get here it is the real deal (no online help case)

argv = sys.argv[1:]
parse_args(argv)
if cl_serial_number: 
    serial_number=cl_serial_number
    config_file_type = "serial_number"
if cl_cdp_interface: 
    cdp_interface=cl_cdp_interface
    config_file_type = "location"
if cl_protocol: 
    protocol=cl_protocol


# setup log file and associated utils

if now == None:
  now=cli("show clock | sed 's/[ :]/_/g'");
try:
    log_filename = "%s.%s" % (log_filename, now)
except Exception as inst:
    print inst
poap_log_file = open(log_filename, "w+")

def poap_log (info):
    poap_log_file.write(info)
    poap_log_file.write("\n")
    poap_log_file.flush()
    print "poap_py_log:" + info
    sys.stdout.flush()

def poap_log_close ():
    poap_log_file.close()

def abort_cleanup_exit () : 
    poap_log("INFO: cleaning up")
    poap_log_close()
    exit(-1)


# some argument sanity checks:

if config_file_type == "serial_number" and serial_number == None: 
    poap_log("ERR: serial-number required (to derive config name) but none given")
    exit(-1)

if config_file_type == "location" and cdp_interface == None: 
    poap_log("ERR: interface required (to derive config name) but none given")
    exit(-1)

# figure out what kind of box we have (to download the correct image)
try: 
  r=clid("show version")
  m = re.match('Nexus9000', r["chassis_id/1"])
  if m:
    box="n9k"
  else:
    m = re.match('Nexus7000', r["chassis_id"])
    if m: 
      box="n7k"
      m = re.match('.*module-2', r["module_id"])
      if m: box="n7k2"
    else: box="n9k"
except: box="n9k"
print "box is", box

# get final image name based on actual box
system_image_src    = eval("%s_%s" % (box , "system_image_src"), globals())
try: root_path      = eval("%s_%s" % (protocol , "image_dir_src_root"), globals())
except: root_path   = ""
try: username       = eval("%s_%s" % (protocol , "username"), globals())
except: pass

# images are copied to temporary location first (dont want to 
# overwrite good images with bad ones).
system_image_dst_tmp    = "%s%s/%s"     % (image_dir_dst, ".new", system_image_dst)
system_image_dst        = "%s/%s"       % (image_dir_dst, system_image_dst)

system_image_src        = "%s/%s"       % (image_dir_src, system_image_src)

# cleanup stuff from a previous run
# by deleting the tmp destination for image files and then recreating the
# directory
image_dir_dst_u="/%s" % image_dir_dst.replace(":", "/") # unix path: cli's rmdir not working!

import shutil
try: shutil.rmtree("%s.new" % image_dir_dst_u)
except: pass
os.mkdir("%s.new" % image_dir_dst_u)

if not os.path.exists(image_dir_dst_u):
    os.mkdir(image_dir_dst_u)

import signal
import string

# utility functions

def run_cli (cmd):
    poap_log("CLI : %s" % cmd)
    return cli(cmd)

def rm_rf (filename): 
    try: cli("delete %s" % filename)
    except: pass

# signal handling

def sig_handler_no_exit (signum, frame) : 
    poap_log("INFO: SIGTERM Handler while configuring boot variables")

def sigterm_handler (signum, frame): 
    poap_log("INFO: SIGTERM Handler") 
    abort_cleanup_exit()
    exit(1)

signal.signal(signal.SIGTERM, sigterm_handler)

# transfers file, return True on success; on error exits unless 'fatal' is False in which case we return False
def doCopy (protocol = "", host = "", source = "", dest = "", vrf = "management", login_timeout=10, user = "", password = "", fatal=True):
    rm_rf(dest)

    # mess with source paths (tftp does not like full paths)
    global username, root_path
    source = source[len(root_path):]

    cmd = "terminal dont-ask ; terminal password %s ; " % password
    cmd += "copy %s://%s@%s%s %s vrf %s" % (protocol, username, host, source, dest, vrf)

    try: run_cli(cmd)
    except:
        poap_log("WARN: Copy Failed: %s" % str(sys.exc_value).strip('\n\r'))
        if fatal:
            poap_log("ERR : aborting")
            abort_cleanup_exit()
            exit(1)
        return False
    return True


def get_md5sum_src (file_name):
    md5_file_name_src = "%s.%s" % (file_name, md5sum_ext_src)
    md5_file_name_dst = "volatile:%s.poap_md5" % os.path.basename(md5_file_name_src)
    rm_rf(md5_file_name_dst)

    ret=doCopy(protocol, hostname, md5_file_name_src, md5_file_name_dst, vrf, md5sum_timeout, username, password, False)
    if ret == True:
        sum=run_cli("show file %s | grep -v '^#' | head lines 1 | sed 's/ .*$//'" % md5_file_name_dst).strip('\n')
        poap_log("INFO: md5sum %s (.md5 file)" % sum)
        rm_rf(md5_file_name_dst)
        return sum
    return None
    # if no .md5 file, and text file, could try to look for an embedded checksum (see below)


def check_embedded_md5sum (filename):
    # extract the embedded checksum
    sum_emb=run_cli("show file %s | grep '^#md5sum' | head lines 1 | sed 's/.*=//'" % filename).strip('\n')
    if sum_emb == "":
        poap_log("INFO: no embedded checksum")
        return None
    poap_log("INFO: md5sum %s (embedded)" % sum_emb)

    # remove the embedded checksum (create temp file) before we recalculate
    cmd="show file %s exact | sed '/^#md5sum=/d' > volatile:poap_md5" % filename
    run_cli(cmd)
    # calculate checksum (using temp file without md5sum line)
    sum_dst=run_cli("show file volatile:poap_md5 md5sum").strip('\n')
    poap_log("INFO: md5sum %s (recalculated)" % sum_dst)
    try: run_cli("delete volatile:poap_md5")
    except: pass
    if sum_emb != sum_dst:
        poap_log("ERR : MD5 verification failed for %s" % filename)
        abort_cleanup_exit()

    return None

def get_md5sum_dst (filename):
    sum=run_cli("show file %s md5sum" % filename).strip('\n')
    poap_log("INFO: md5sum %s (recalculated)" % sum)
    return sum  

def check_md5sum (filename_src, filename_dst, lname):
    md5sum_src = get_md5sum_src(filename_src)
    if md5sum_src: # we found a .md5 file on the server
        md5sum_dst = get_md5sum_dst(filename_dst)
        if md5sum_dst != md5sum_src:
            poap_log("ERR : MD5 verification failed for %s! (%s)" % (lname, filename_dst))
            abort_cleanup_exit()

def same_images (filename_src, filename_dst):
    if os.path.exists(image_dir_dst_u):
        md5sum_src = get_md5sum_src(filename_src)
        if md5sum_src:
            md5sum_dst = get_md5sum_dst(filename_dst)
            if md5sum_dst == md5sum_src:
                poap_log("INFO: Same source and destination images" ) 
                return True
    poap_log("INFO: Different source and destination images" ) 
    return False

# Will run our CLI command to test MD5 checksum and if files are valid images
# This check is also performed while setting the boot variables, but this is an
# additional check

def get_version (msg):
    lines=msg.split("\n") 
    for line in lines:
        index=line.find("MD5")
        if (index!=-1):
            status=line[index+17:]

        index=line.find("kickstart:")
        if (index!=-1): 
            index=line.find("version")
            ver=line[index:]
            return status,ver

        index=line.find("system:")
        if (index!=-1):
            index=line.find("version")
            ver=line[index:]
            return status,ver
    
def verify_images2 ():
    sys_cmd="show version image %s" % system_image_dst
    sys_msg=cli(sys_cmd)

    sys_s,sys_v=get_version(sys_msg)    
    
    print "Value: %s and %s" % (kick_s, sys_s)
    if (kick_s == "Passed" and sys_s == "Passed"):
        # MD5 verification passed
        if(kick_v != sys_v): 
            poap_log("ERR : Image version mismatch. (kickstart : %s) (system : %s)" % (kick_v, sys_v))
            abort_cleanup_exit()
    else:
        poap_log("ERR : MD5 verification failed!")
        poap_log("%s\n%s" % (kick_msg, sys_msg))
        abort_cleanup_exit()
    poap_log("INFO: Verification passed. (kickstart : %s) (system : %s)" % (kick_v, sys_v))
    return True

def verify_images ():
    print "show version image %s" % system_image_dst
    sys_cmd="show version image %s" % system_image_dst
    sys_msg=cli(sys_cmd)
    sys_v=sys_msg.split()
    print "system image Values: %s " % (sys_v[2])
    print "system image Values v10 is : %s" % (sys_v[10])
    if (sys_v[2] == "Passed"):
        poap_log("INFO: Verification passed. (system : %s)" % (sys_v[10]))
    else:
        poap_log("ERR : MD5 verification failed!")
        poap_log("%s" % (sys_msg))
        abort_cleanup_exit()
    poap_log("INFO: Verification passed.  (system : %s)" % (sys_v[10]))
    return True

# get config file from server
def get_config ():
    doCopy(protocol, hostname, config_file_src, config_file_dst, vrf, config_timeout, username, password)
    poap_log("INFO: Completed Copy of Config File") 
    # get file's md5 from server (if any) and verify it, failure is fatal (exit)
    check_md5sum (config_file_src, config_file_dst, "config file")


# get system image file from server
def get_system_image ():
    if not same_images(system_image_src, system_image_dst):
        doCopy(protocol, hostname, system_image_src, system_image_dst_tmp, vrf, system_timeout, username, password)  
        poap_log("INFO: Completed Copy of System Image" ) 
        # get file's md5 from server (if any) and verify it, failure is fatal (exit)
        check_md5sum(system_image_src, system_image_dst_tmp, "system image")
        run_cli("move %s %s" % (system_image_dst_tmp, system_image_dst))


def wait_box_online ():
    while 1:
        r=int(run_cli("show system internal platform internal info | grep box_online | sed 's/[^0-9]*//g'").strip('\n'))
        if r==1: break
        else: time.sleep(5)
        poap_log("INFO: Waiting for box online...")


# install (make persistent) images and config 
def install_it (): 
    global cl_download_only
    if cl_download_only: exit(0)
    timeout = -1

    # make sure box is online
    wait_box_online()

    poap_log("INFO: Setting the boot variables")
    try: shutil.rmtree("%s.new" % image_dir_dst_u)
    except: pass
    try:
        run_cli("config terminal ; boot nxos %s" % system_image_dst)
        run_cli("copy running-config startup-config")
        run_cli('copy %s scheduled-config' % config_file_dst)
    except:
        poap_log("ERR : setting bootvars or copy run start failed!")
        abort_cleanup_exit()
    # no need to delete config_file_dst, it is in /volatile and we will reboot....
    # do it anyway so we don't have permission issues when testing script and
    # running as different users (log file have timestamp, so fine)
    poap_log("INFO: Configuration successful")

        
# Verify if free space is available to download config, kickstart and system images
def verify_freespace (): 
    freespace = int(cli("dir bootflash: | last 3 | grep free | sed 's/[^0-9]*//g'").strip('\n'))
    freespace = freespace / 1024
    poap_log("INFO: free space is %s kB"  % freespace )

    if required_space > freespace:
        poap_log("ERR : Not enough space to copy the config, kickstart image and system image, aborting!")
        abort_cleanup_exit()


# figure out config filename to download based on serial-number
def set_config_file_src_serial_number (): 
    global config_file_src
    config_file_src = "%s.%s" % (config_file_src, serial_number)
    poap_log("INFO: Selected config filename (serial-nb) : %s" % config_file_src)


if config_file_type == "serial_number": 
    #set source config file based on switch's serial number
    set_config_file_src_serial_number()


# finaly do it

verify_freespace()
get_system_image()
verify_images()
get_config()

# dont let people abort the final stage that concretize everything
# not sure who would send such a signal though!!!! (sysmgr not known to care about vsh)
signal.signal(signal.SIGTERM, sig_handler_no_exit)
install_it()

poap_log_close()
exit(0)


########NEW FILE########
__FILENAME__ = client_example
# Copyright (C) 2013 Cisco Systems Inc.
# All rights reserved
import sys

sys.path.append("./cisco")
sys.path.append("./utils")

from nxapi_utils import NXAPITransport 
from cisco.interface import Interface

################### 
# NXAPI init block
###################
target_url = "http://10.30.14.8/ins"
username = "admin"
password = "admin"
NXAPITransport.init(target_url=target_url, username=username, password=password)
###################

################### 
# cli/clip/clid are changed a bit, but largely the same
###################
print NXAPITransport.cli("show version")

NXAPITransport.clip("show interface brief")

NXAPITransport.clic("conf t ;interface eth4/1 ;no shut")

print NXAPITransport.clid("show version")

################### 
# Below is exactly the same as the usage on the switch. Do whatever you
# are already doing on the switch right now!
###################
print Interface.interfaces()

i = Interface("Ethernet4/1")

print i.show(key="eth_mtu")

i.set_description(d="ifx4/1")




########NEW FILE########
__FILENAME__ = nxapi_utils
# Copyright (C) 2013 Cisco Systems Inc.
# All rights reserved
import urllib2

import contextlib
import base64

import socket

import httplib
from httplib import HTTPConnection, HTTPS_PORT
import ssl

from lxml import etree
import json
import xmltodict

from errors import *


class HTTPSConnection(HTTPConnection):

    '''This class allows communication via SSL.'''

    default_port = HTTPS_PORT

    def __init__(
        self,
        host,
        port=None,
        key_file=None,
        cert_file=None,
        strict=None,
        timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
        source_address=None,
        ):

        HTTPConnection.__init__(
            self,
            host,
            port,
            strict,
            timeout,
            source_address,
            )
        self.key_file = key_file
        self.cert_file = cert_file

    def connect(self):
        '''Connect to a host on a given (SSL) port.'''

        sock = socket.create_connection((self.host, self.port),
                self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()

        # this is the only line we modified from the httplib.py file
        # we added the ssl_version variable
        self.sock = ssl.wrap_socket(sock, self.key_file,
                                    self.cert_file,
                                    ssl_version=ssl.PROTOCOL_SSLv3)


httplib.HTTPSConnection = HTTPSConnection


class RequestMsg:

    def __init__(
        self,
        msg_type='cli_show',
        ver='0.1',
        sid='1',
        input_cmd='show version',
        out_format='json',
        do_chunk='0',
        ):

        self.msg_type = msg_type
        self.ver = ver
        self.sid = sid
        self.input_cmd = input_cmd
        self.out_format = out_format
        self.do_chunk = do_chunk

    def get_req_msg_str(
        self,
        msg_type='cli_show',
        ver='0.1',
        sid='1',
        input_cmd='show version',
        out_format='json',
        do_chunk='0',
        ):

        req_msg = '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        req_msg += '<ins_api>\n'
        req_msg += '<type>' + msg_type + '</type>\n'
        req_msg += '<version>' + ver + '</version>\n'
        req_msg += '<chunk>' + do_chunk + '</chunk>\n'
        req_msg += '<sid>' + sid + '</sid>\n'
        req_msg += '<input>' + input_cmd + '</input>\n'
        req_msg += '<output_format>' + out_format + '</output_format>\n'
        req_msg += '</ins_api>\n'
        return req_msg


class RespFetcher:

    def __init__(
        self,
        username='admin',
        password='insieme',
        url='http://172.21.128.227/ins',
        ):

        self.username = username
        self.password = password
        self.url = url
        self.base64_str = base64.encodestring('%s:%s' % (username,
                password)).replace('\n', '')

    def get_resp(
        self,
        req_str,
        cookie,
        timeout,
        ):

        req = urllib2.Request(self.url, req_str)
        req.add_header('Authorization', 'Basic %s' % self.base64_str)
        req.add_header('Cookie', '%s' % cookie)
        try:
            with contextlib.closing(urllib2.urlopen(req,
                                    timeout=timeout)) as resp:
                resp_str = resp.read()
                resp_headers = resp.info()
                return (resp_headers, resp_str)
        except socket.timeout, e:
            print 'Req timeout'
            raise


class RespFetcherHttps:

    def __init__(
        self,
        username='admin',
        password='insieme',
        url='https://172.21.128.227/ins',
        ):

        self.username = username
        self.password = password
        self.url = url
        self.base64_str = base64.encodestring('%s:%s' % (username,
                password)).replace('\n', '')

    def get_resp(
        self,
        req_str,
        cookie,
        timeout,
        ):

        req = urllib2.Request(self.url, req_str)
        req.add_header('Authorization', 'Basic %s' % self.base64_str)
        req.add_header('Cookie', '%s' % cookie)
        try:
            with contextlib.closing(urllib2.urlopen(req,
                                    timeout=timeout)) as resp:
                resp_str = resp.read()
                resp_headers = resp.info()
                return (resp_headers, resp_str)
        except socket.timeout, e:
            print 'Req timeout'
            raise


class NXAPITransport:
    '''N9000 Python objects off-the-box transport utilizing NX-API'''
    target_url = ''
    username = ''
    password = ''

    timeout = 10

    out_format = 'xml'
    do_chunk = '0'
    sid = 'sid'
    cookie = 'no-cookie'

    req_obj = RequestMsg()

    @classmethod
    def init(cls, target_url, username, password):
        cls.target_url = target_url
        cls.username = username
        cls.password = password
        cls.req_fetcher = RespFetcher(username=username,
                password=password, url=target_url)

    @classmethod
    def send_cmd_int(cls, cmd, msg_type):
        '''Construct NX-API message. Send commands through NX-API. Only single 
           command for show commands. Internal usage'''
        if msg_type == "cli_show" or msg_type == "cli_show_ascii":
            if " ;" in cmd:
                raise cmd_exec_error("Only single show command supported in internal api")

        req_msg_str = cls.req_obj.get_req_msg_str(msg_type=msg_type,
                input_cmd=cmd, out_format=cls.out_format,
                do_chunk=cls.do_chunk, sid=cls.sid)
        (resp_headers, resp_str) = \
            cls.req_fetcher.get_resp(req_msg_str, cls.cookie,
                cls.timeout)

        if 'Set-Cookie' in resp_headers:
            cls.cookie = resp_headers['Set-Cookie']
        content_type = resp_headers['Content-Type']
        root = etree.fromstring(resp_str)
        body = root.findall('.//body')
        code = root.findall('.//code')
        msg = root.findall('.//msg')

        output = ""
        status = 0
        if len(body) != 0:
            if msg_type == 'cli_show':
                output = etree.tostring(body[0])
            else:
                output = body[0].text

        if output == None:
            output = ""
        if code[0].text == "200":
            status = 0
        else:
            status = int(code[0].text)
        return [output, status, msg[0].text]

    @classmethod
    def send_cmd(cls, cmd, msg_type):
        '''Construct NX-API message. Send commands through NX-API. Multiple 
           commands okay'''
        req_msg_str = cls.req_obj.get_req_msg_str(msg_type=msg_type,
                input_cmd=cmd, out_format=cls.out_format,
                do_chunk=cls.do_chunk, sid=cls.sid)
        (resp_headers, resp_str) = \
            cls.req_fetcher.get_resp(req_msg_str, cls.cookie,
                cls.timeout)
        if 'Set-Cookie' in resp_headers:
            cls.cookie = resp_headers['Set-Cookie']
        content_type = resp_headers['Content-Type']
        root = etree.fromstring(resp_str)
        body = root.findall('.//body')
        code = root.findall('.//code')
        msg = root.findall('.//msg')

        # Any command execution error will result in the entire thing fail
        # This is to align with vsh multiple commands behavior
        if len(code) == 0:
            raise unexpected_error("Unexpected error")
        for i in range(0, len(code)):
            if code[i].text != "200":
                raise cmd_exec_error("Command execution error: {0}".format(msg[i].text))

        output = ""
        if msg_type == 'cli_show':
            for i in range(0, len(body)):
                output += etree.tostring(body[i])
        else:
            for i in range(0, len(body)):
                if body[i].text is None:
                    continue
                else:
                    output += body[i].text

        return output

    @classmethod
    def cli(cls, cmd):
        '''Run cli show command. Return show output'''
        try:
            output = cls.send_cmd(cmd, "cli_show_ascii")
            return output
        except:
            raise

    @classmethod
    def clip(cls, cmd):
        '''Run cli show command. Print show output'''
        try:
            output = cls.send_cmd(cmd, "cli_show_ascii")
            print output
        except:
            raise

    @classmethod
    def clic(cls, cmd):
        '''Run cli configure command. Return configure output'''
        try:
            output = cls.send_cmd(cmd, "cli_conf")
            return output
        except:
            raise

    @classmethod
    def clid(cls, cmd):
        '''Run cli show command. Return JSON output. Only XMLized commands 
           have outputs'''
        if " ;" in cmd:
            raise cmd_exec_error("Only single command is allowed in clid()")
        try:
            output = cls.send_cmd(cmd, "cli_show")
            o = xmltodict.parse(output)
            json_output = json.dumps(o["body"])
            return json_output
        except:
            raise


class NXAPI:
    '''A better NX-API utility'''
    def __init__(self):
        self.target_url = 'http://localhost/ins'
        self.username = 'admin'
        self.password = 'admin'
        self.timeout = 10

        self.ver = '0.1'
        self.msg_type = 'cli_show'
        self.cmd = 'show version'
        self.out_format = 'xml'
        self.do_chunk = '0'
        self.sid = 'sid'
        self.cookie = 'no-cookie'

    def set_target_url(self, target_url='http://localhost/ins'):
        self.target_url = target_url

    def set_username(self, username='admin'):
        self.username = username

    def set_password(self, password='admin'):
        self.password = password

    def set_timeout(self, timeout=0):
        if timeout < 0:
            raise data_type_error('timeout should be greater than 0')
        self.timeout = timeout

    def set_cmd(self, cmd=''):
        self.cmd = cmd

    def set_out_format(self, out_format='xml'):
        if out_format != 'xml' and out_format != 'json':
            raise data_type_error('out_format xml or json')
        self.out_format = out_format

    def set_do_chunk(self, do_chunk='0'):
        if do_chunk != 0 and do_chunk != 1:
            raise data_type_error('do_chunk 0 or 1')
        self.do_chunk = do_chunk

    def set_sid(self, sid='sid'):
        self.sid = sid

    def set_cookie(self, cookie='no-cookie'):
        self.cookie = cookie

    def set_ver(self, ver='0.1'):
        if ver != '0.1':
            raise data_type_error('Only ver 0.1 supported')
        self.ver = ver

    def set_msg_type(self, msg_type='cli_show'):
        if msg_type != 'cli_show' and msg_type != 'cli_show_ascii' \
            and msg_type != 'cli_conf' and msg_type != 'bash':
            raise data_type_error('msg_type incorrect')
        self.msg_type = msg_type

    def get_target_url(self):
        return self.target_url

    def get_username(self):
        return self.username

    def get_password(self):
        return self.username

    def get_timeout(self):
        return self.timeout

    def get_cmd(self):
        return self.cmd

    def get_out_format(self):
        return self.out_format

    def get_do_chunk(self):
        return self.do_chunk

    def get_sid(self):
        return self.sid

    def get_cookie(self):
        return self.cookie

    def req_to_string(self):
        req_msg = '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        req_msg += '<ins_api>\n'
        req_msg += '<type>' + self.msg_type + '</type>\n'
        req_msg += '<version>' + self.ver + '</version>\n'
        req_msg += '<chunk>' + self.do_chunk + '</chunk>\n'
        req_msg += '<sid>' + self.sid + '</sid>\n'
        req_msg += '<input>' + self.cmd + '</input>\n'
        req_msg += '<output_format>' + self.out_format + '</output_format>\n'
        req_msg += '</ins_api>\n'
        return req_msg

    def send_req(self):
         req = RespFetcher(self.username, self.password, self.target_url)
         return req.get_resp(self.req_to_string(), self.cookie, self.timeout)

########NEW FILE########
__FILENAME__ = nxos_utils
# Copyright (C) 2013 Cisco Systems Inc.
# All rights reserved
#$Id: eor_utils.py,v 1.427 2013/06/24 23:56:03 venksrin Exp $ 
#ident $Source: /cvsroot/eor/systest/lib/eor_utils.py,v $ $Revision: 1.427 $

# Best Pratices for get() functions:
# 1. Use class rex as much as possible for standard regular expressions
# 2. Use underscore in keys wherever white-space appears in the output header
# 3. Add author name, description of function, sample usage examples and return value
# 4. Use python documentation format for #3 above, so that the documentation for all the functions can be pulled out easily

from nxapi_utils import NXAPITransport

import re                                                       
import collections                               
import string
import subprocess
import shlex
import sys, socket
import datetime
import time

MASKS=['0.0.0.0','128.0.0.0','192.0.0.0','224.0.0.0','240.0.0.0','248.0.0.0','252.0.0.0','254.0.0.0','255.0.0.0','255.128.0.0','255.192.0.0','255.224.0.0','255.240.0.0','255.248.0.0','255.252.0.0', '255.254.0.0', '255.255.0.0', '255.255.128.0', '255.255.192.0', '255.255.224.0', '255.255.240.0', '255.255.248.0', '255.255.252.0', '255.255.254.0', '255.255.255.0', '255.255.255.128', '255.255.255.192', '255.255.255.224', '255.255.255.240', '255.255.255.248', '255.255.255.252', '255.255.255.254', '255.255.255.255']

####################################################################
# Block that hijack on-box cli and convert into NX-API calls
####################################################################
def runNXAPIConf(cmd):
    output,code,msg = NXAPITransport.send_cmd_int(cmd, "cli_conf")
    return output,msg,code

def runNXAPIShow(cmd):
    xml_index = cmd.find("| xml")
    if xml_index == -1:
        output,code,msg = NXAPITransport.send_cmd_int(cmd, "cli_show_ascii")
    else:
        cmd = cmd[:xml_index]
        output,code,msg = NXAPITransport.send_cmd_int(cmd, "cli_show")
    return output

def runVshCmdEx(cmd, _shell = False, _stdout = None):                                
   output,error,status = runNXAPIConf(cmd)
   return output,error,status 

def cli_ex(cmd):
    if "config" in cmd:
      return runNXAPIConf(cmd)
    else:
      return runNXAPIShow(cmd)
####################################################################
    
class rex:
   INTERFACE_TYPE="[Ff]ast[Ee]thernet|[Ff][Ee]th|[Gg]igabit[Ee]thernet|[Gg]ig[Ee]|[Ee]thernet|[Ee]th|[Tt]unnel ?|[Ll]oopback ?|[Pp]ort-channel ?|[Oo]verlay ?|[Nn]ull|[Mm]gmt|[Vv]lan ?|[Pp]o ?|[Ll]o ?|[Oo]vl ?|[Vv][Ll]|[Rr]epl|[Rr]eplicator|[Ff]as|[Ss]up-eth"
   INTERFACE_NUMBER="[0-9]+/[0-9]+/[0-9]+|[0-9]+/[0-9]+|[0-9]+/[0-9]+\.[0-9]+|[0-9]+\.[0-9]+|[0-9]+|[0-9]+/[0-9]+/[0-9]+"
#   INTERFACE_NAME="(?:{0})(?:{1})|[Nn]ull".format(INTERFACE_TYPE,INTERFACE_NUMBER)

   INTERFACE_NAME='(?:(?:{0})(?:{1})|(?:[Nn]ull))'.format(INTERFACE_TYPE,INTERFACE_NUMBER)
   INTERFACE_RANGE='(?:(?:{0}-[0-9]+|{0}-{0}|{0}),?)+'.format(INTERFACE_NAME)
   BCM_FP_INTERFACE='([Xx]e([0-9]+))'
   BCM_FP_INTERFACE_RANGE='[Xx]e([0-9]+)-[Xx]e([0-9]+)'

   PHYSICAL_INTERFACE_TYPE="[Ff]ast[Ee]thernet|[Ff][Ee]th|[Gg]igabit[Ee]thernet|[Gg]ig[Ee]|[Gg]i|[Ee]thernet|[Ee]th"
   PHYSICAL_INTERFACE_NUMBER="[0-9]+/[0-9]+/[0-9]+|[0-9]+/[0-9]+|[0-9]+"
   PHYSICAL_INTERFACE_NAME="(?:{0})(?:{1})".format(PHYSICAL_INTERFACE_TYPE,PHYSICAL_INTERFACE_NUMBER)

   PHYSICAL_INTERFACE_RANGE='(?:(?:{0}-[0-9]+|{0}-{0}|{0}),?)+'.format(PHYSICAL_INTERFACE_NAME)

   DEVICE_TYPE='EOR|sTOR|N7K|N5K|N3K|itgen|fanout|UNKNOWN|NA'
   FEX_MODEL='N2148T|N2232P|N2232TM-E|N2248TP-E|N2248T|NB22FJ|NB22HP'
   FEX_INTERFACE_TYPE='{0}[0-9][0-9][0-9]/[0-9]+/[0-9]+'.format(PHYSICAL_INTERFACE_TYPE)
   SWITCH_NAME = '[0-9A-Za-z_-]+'
   #VLAN_RANGE  = '[0-9]+(?:\-[0-9]+)?'

   HEX="[0-9a-fA-F]+"
   HEX_VAL="[x0-9a-fA-F]+"
   MACDELIMITER="[\.:\-]"
   # Following will match the following combinations
   #  Aa.Bb.Cc.Dd.Ee.Ff
   #  Aa-Bb-Cc-Dd-Ee-Ff
   #  Aa:Bb:Cc:Dd:Ee:Ff
   #  AaBb.CcDd.EeFf
   #  AaBb-CcDd-EeFf
   #  AaBb:CcDd:EeFf
   MACADDR=HEX+HEX+MACDELIMITER+HEX+HEX+MACDELIMITER+HEX+HEX+MACDELIMITER+HEX+HEX+MACDELIMITER+HEX+HEX+MACDELIMITER+HEX+HEX+"|"+HEX+HEX+HEX+HEX+MACDELIMITER+HEX+HEX+HEX+HEX+MACDELIMITER+HEX+HEX+HEX+HEX
   IPv4_ADDR="[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+"
   IPv6_ADDR="[0-9A-Fa-f]+:[0-9A-Fa-f:]+"

   LINK_LOCAL_IPv6_ADDR="fe80::[0-9A-Fa-f]+:[0-9A-Fa-f]+:[0-9A-Fa-f]+:[0-9A-Fa-f]+"
   IP_ADDRESS="(?:(?:{0})|(?:{1}))".format(IPv4_ADDR,IPv6_ADDR)
   NETADDR ='{0}/[0-9]+'.format(IPv4_ADDR)
   NUM="[0-9]+"
   BOOL="[01]"
   DECIMAL_NUM="[0-9\.]+"
   ALPHA="[a-zA-Z]+"
   ALPHAUPPER="[A-Z]+"
   ALPHALOWER="[a-z]+"
   ALPHASPECIAL="[a-zA-Z_\-\.#/]+"
   ALPHANUM="[a-zA-Z0-9]+"
   ALPHANUMSPECIAL="[a-zA-Z0-9\-\._/]+"
   SYSMGR_SERVICE_NAME = "[a-zA-Z0-9\-\._ ]+"
   VRF_NAME="[a-zA-Z0-9_\-#]+"
   ALL="?:[.\s]+"
   #
   # Number and time formats
   #
   VLAN_RANGE='(?:(?:{0}-[0-9]+|{0}-{0}|{0}),?)+'.format(NUM)

   DATE = '[0-9]+\-[0-9]+\-[0-9]+'
   U_TIME="[0-9]+\.[0-9]+"
   CLOCK_TIME="[0-9]+[0-9]+:[0-9]+[0-9]+:[0-9]+[0-9]+"
   HH_MM_SS="[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}"
   TIME="(?:$U_TIME|$CLOCK_TIME)"
   MONTH="Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
   YEAR="[12]+[0-9][0-9][0-9]"
   UPTIME="(?:\d+[dwmy]\d+[hdwm]|\d+:\d+:\d+|\d+\.\d+)"
   XPTIME="(?:\d+:\d+:\d+|\d+\.\d+|never)"

   LC_STATUS='(?:pwr-?denied|err-?pwd-?dn|pwr-?cycle?d|upgrading|powered-?up|powered-?dn|failure|initializing|testing|ok)'
   LC_MODEL='(?:N7K-F2-?48X[PT]-?\d+[E]*| +|Cortina-Test-LC|N9k-X9636PQ)'
   FC_MODEL='(?:N7K-C[0-9]+-FAB-?\d+|N/A| +)'
   LC_MODULE_TYPE='(?:[0-9]+/[0-9]+ Gbps (?:BASE-T )?Ethernet Module|Cortina-Test-LC|Snowbird|Seymour)' 
   FC_MODULE_TYPE='(?:Fabric Module(?: [0-9]+)?|Sierra|Shasta)'
   VLAN_STATUS='active|suspended|act.lshut'
   
   #Verify_list defined for stimuli classes
   VERIFY_LIST=['none','all','traffic','l2_unicast_pi','l3_unicast_pi','l2_multicast_pi','l3_multicast_pi','l2_unicast_pd','l3_unicast_pd','l2_multicast_pd','l3_multicast_pd','system','exception','vpc_consistency']
   TRIGGER_VERIFY_LIST=['traffic','none','all']


# To be depreceated, use strTolist instead
# Usages strtolist('1,2,3')
#        strtolist('1 2 3')
#        strtolist('1, 2, 3')
# All three will return list of ['1',2,'3']
def strtolist(inputstr,retainint=False):
     inputstr=str(inputstr)
     inputstr=inputstr.strip("[]")
     splitbycomma=inputstr.split(",")
     splitbyspace=inputstr.split()
     if len(splitbycomma) >= 2:
         returnlist=[]
         for elem in splitbycomma:
             elem=elem.strip(" '")
             elem=elem.strip('"')
             if elem.isdigit() and retainint:
                 returnlist.append(int(elem))
             else:
                 returnlist.append(elem)
         return returnlist
     returnlist=[]
     for elem in splitbyspace:
         elem=elem.strip(" '")
         elem=elem.strip('"')
         if elem.isdigit() and retainint:
             returnlist.append(int(elem))
         else:
             returnlist.append(elem)
     return returnlist

def normalizeInterfaceName(log, interface):
     in_type=type(interface)
     pattern1='[Ee]thernet|[Ee]th|[Ee]t'
     pattern2='[Vv]lan|[Vv]l'
     pattern3='[Pp]ort-channel|[Pp]ortchannel|[Pp]o'
     pattern4='[Ll]oopback|[Ll]oop-back|[Ll]o'
     if (in_type == str):
         interface=re.sub(r'(?:{0})((?:{1}))'.format(pattern1,rex.INTERFACE_NUMBER),r'Eth\1',interface)
         interface=re.sub(r'(?:{0})((?:{1}))'.format(pattern2,rex.INTERFACE_NUMBER),r'Vlan\1',interface)
         interface=re.sub(r'(?:{0})((?:{1}))'.format(pattern3,rex.INTERFACE_NUMBER),r'Po\1',interface)
         interface=re.sub(r'(?:{0})((?:{1}))'.format(pattern4,rex.INTERFACE_NUMBER),r'Lo\1',interface)
     if (in_type == list):
         for int in interface:
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern1,rex.INTERFACE_NUMBER),r'Eth\1',int)
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern2,rex.INTERFACE_NUMBER),r'Vlan\1',tmp)
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern3,rex.INTERFACE_NUMBER),r'Po\1',tmp)
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern4,rex.INTERFACE_NUMBER),r'Lo\1',tmp)
             interface[interface.index(int)]=tmp
     if (in_type == tuple):
         int_list=list(interface)
         for int in int_list:
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern1,rex.INTERFACE_NUMBER),r'Eth\1',int)
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern2,rex.INTERFACE_NUMBER),r'Vlan\1',tmp)
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern3,rex.INTERFACE_NUMBER),r'Po\1',tmp)
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern4,rex.INTERFACE_NUMBER),r'Lo\1',tmp)
             int_list[int_list.index(int)]=tmp
         interface=tuple(int_list)
     if (in_type == dict):
         dct={}
         for key in interface.keys():
             int=re.sub(r'(?:{0})((?:{1}))'.format(pattern1,rex.INTERFACE_NUMBER),r'Eth\1',key)
             int=re.sub(r'(?:{0})((?:{1}))'.format(pattern2,rex.INTERFACE_NUMBER),r'Vlan\1',int)
             int=re.sub(r'(?:{0})((?:{1}))'.format(pattern3,rex.INTERFACE_NUMBER),r'Po\1',int)
             int=re.sub(r'(?:{0})((?:{1}))'.format(pattern4,rex.INTERFACE_NUMBER),r'Lo\1',int)
             tmp={int:interface[key]}
             dct.update(tmp)
         interface=dct

     return interface
def convertListToDict(table,columns=[],keys=None,keytype="tuple"):

    # Returns dictionary based on given list & columns
    # If it is a list, each column is a key
    # If it is a list of lists, then first level keys are passed keys argument
    # and columns is second level key

    returnDict = collections.OrderedDict()
    if keys: 
        keyIndexes = []
        if "split" in dir(keys):
            keys=keys.split()
        for key in keys:
            keyIndexes.append(columns.index(key))

        valueIndex=-1
        if len(columns) - len(keys) == 1:
            for i in range(len(columns)):
                if not i in keyIndexes:
                   valueIndex=i
                   break

        for row in table:
            key=""
            keyitems=[]
            initial=True
            for keyIndex in keyIndexes:
               interface=""
               temp=re.match(rex.INTERFACE_NAME,row[keyIndex])
               if temp and temp.group(0) == row[keyIndex]:
                   interface=normalizeInterfaceName("",row[keyIndex]) 
               if initial:
                   if interface == "": 
                       key = key + row[keyIndex]
                   else:
                       key = key + interface
                   initial=False
               else:
                   if interface == "": 
                       key = key + " " + row[keyIndex]
                   else:
                       key = key + " " + interface
               if interface == "":
                   keyitems.append(row[keyIndex])
               else:
                   keyitems.append(interface)
            if keytype == "tuple" and len(keys) > 1:
                key=tuple(keyitems)
            returnDict[key] = collections.OrderedDict()
            if valueIndex == -1:
                for i in range(len(columns)):
                    if not i in keyIndexes:
                       temp=re.match(rex.INTERFACE_NAME,row[i].strip())
                       if temp and temp.group(0) == row[i].strip():
                          returnDict[key][columns[i]]=normalizeInterfaceName("",row[i].strip()) 
                       else:
                           returnDict[key][columns[i]] = row[i].strip()
            else:
               temp=re.match(rex.INTERFACE_NAME,row[valueIndex].strip())
               if temp and temp.group(0) == row[valueIndex].strip():
                   returnDict[key]=normalizeInterfaceName("",row[valueIndex].strip()) 
               else:
                   returnDict[key] = row[valueIndex]
    else:
        #Single level dictionary need to handle 6 different use cases
        #eor_utils.convertListToDict(['x','y','z'],['a','b','c'])
        #eor_utils.convertListToDict([],['a','b','c'])
        #eor_utils.convertListToDict(['x','y'],['a','b','c'])
        #eor_utils.convertListToDict([('x','y','z')],['a','b','c'])
        #eor_utils.convertListToDict([('x','y'),('c','d')],['a','b'])
        #eor_utils.convertListToDict([('x','y'),('c','d')])
        if len(table):
            if len(columns) == len(table) and not re.search('tuple',str(type(table[0]))):
                for key in columns:
                    temp=re.match(rex.INTERFACE_NAME,table[columns.index(key)])
                    if temp and temp.group(0) == table[columns.index(key)]:
                        returnDict[key]=normalizeInterfaceName("",table[columns.index(key)]) 
                    else:
                        returnDict[key]=table[columns.index(key)]
            elif len(table) == 1 and len(table[0]) == len(columns) and re.search('tuple',str(type(table[0]))):
                for key in columns:
                    temp=re.match(rex.INTERFACE_NAME,table[0][columns.index(key)])
                    if temp and temp.group(0) == table[0][columns.index(key)]:
                        returnDict[key]=normalizeInterfaceName("",table[0][columns.index(key)]) 
                    else:
                        returnDict[key]=table[0][columns.index(key)]
            elif (len(columns) == 2 or len(columns) == 0)and re.search('tuple',str(type(table[0]))):
                for row in table:
                    if len(row) == 2:
                       temp=re.match(rex.INTERFACE_NAME,row[1])
                       if temp and temp.group(0) == row[1]:
                            returnDict[row[0]]=normalizeInterfaceName("",row[1]) 
                       else:
                            returnDict[row[0]]=row[1]
                    else:
                       return collections.OrderedDict()
    return returnDict

def getUnwrappedBuffer(buffer,delimiter=" "):

    # Returns a string
    # If output has wrapped lines as follows (port-channel summary)
    # "21    Po21(SU)    Eth      NONE      Eth2/11(P)   Eth2/12(D)
    #  22    Po22(SU)    Eth      NONE      Eth1/1(P)    Eth1/2(P)    Eth1/3(P)
    #                                       Eth1/4(P)
    #  101   Po101(SD)   Eth      NONE      Eth2/1(D)    Eth2/2(D)"
    # This converts to
    # "21    Po21(SU)    Eth      NONE      Eth2/11(P)   Eth2/12(D)
    #  22    Po22(SU)    Eth      NONE      Eth1/1(P)    Eth1/2(P)    Eth1/3(P) Eth1/4(P)
    #  101   Po101(SD)   Eth      NONE      Eth2/1(D)    Eth2/2(D)"
    #
    # This helps to write get procedures with everyoutput being a single line 
    # and makes regular expressions seamless independent of wrapped output

    previousline=""
    lines=[]
    returnbuffer = ""
    buffer=re.sub("\r","",buffer)
    for line in buffer.split("\n"):
        wrappedline=re.findall("^[ \t]+(.*)",line,flags=re.I)
        if len(wrappedline) > 0:
           previousline = previousline + delimiter + re.sub("\r\n","",wrappedline[0])
        else:
           if (previousline != ""):
               returnbuffer = returnbuffer + previousline + "\n"
           previousline=re.sub("[\r\n]+","",line)
    if (previousline != ""):
          returnbuffer = returnbuffer + previousline + "\n"
    return returnbuffer




def getVlanDict(vlan):

    cmd = "show vlan id " + vlan 
    showoutput=cli_ex(cmd)

    vlanmemberlist=re.findall("("+rex.NUM+")[ \t]+("+rex.ALPHANUM+")[ \t]+("+rex.VLAN_STATUS+")[ \t]+(.*)",getUnwrappedBuffer(showoutput,", "),flags=re.I|re.M)
    vlanmemberdict=convertListToDict(vlanmemberlist,['VLAN','Name','Status','Ports'],['VLAN'])
    return vlanmemberdict

 
"""This scrpit should not contain any thing other than enums"""
class IfType():
       Ethernet = 1
       PortChannel = 2
       Internal = 3
       Cpu = 4


def replace_output(_lines, _find_word, _replace_word):
    hw_name = _find_word
    new_lines = []

    for line in _lines:
        x = re.sub(r'\b%s\b'%(hw_name), _replace_word, line)
        new_lines.append(x)

    return new_lines

class createHwTableObject(object):

    """ Class to parse the broadcom table outputs and convert to dictionary format. Expects the
    input as 'Index: <Row>' where the <Row> is in key value pairs separated by commas"""

    def __init__( self, bcm_cmd_dump ):

       import re

       self.table=collections.OrderedDict()

       table_rows=bcm_cmd_dump.split('\n')
       for row in table_rows:
          if "d chg" in row:
              continue
          if ":" not in row:
                 continue
          if "Private image version" in row:
                 continue

          (row_key, row_value)=row.split(': ')
          (row_key, row_value)=row.split(': ')
          value_row=row_value.rstrip('\r').lstrip('<').rstrip('>')
          self.table[row_key]=collections.OrderedDict()
          for data_params in value_row.split(','):
             if len(data_params) == 0:
                 continue

             (data_key,data_value)=data_params.split('=')
             self.table[row_key][data_key]=data_value
       #print('Table Data', self.table )



def getSpanningTreeVlanPortStateDict(vlan):
    cmd = "show spanning-tree " + vlan
    showoutput=cli_ex(cmd)
    stplist=re.findall("^([^ \t]+)[ \s]+([^ \t]+)[ \s]+([A-Za-z]+)[ \s]+([0-9]+)[ \s]+\
    ([^ \t]+)[ \s]+([^ \t]+)[ \s\r\n]+",showoutput,flags=re.I|re.M)
    if stplist:
        # if vlan port state is found
        stpdict=convertListToDict(stplist,['vlan','role','state','cost','prio.nbr','type'])
        log.info(" STP state for " + \
        parserutils_lib.argsToCommandOptions(args,arggrammar,log,"str") + " is : " + str(stpdict))
        return stpdict  

def getShowSpanningTreeDict( vlan ):

  
    show_stp_dict=collections.OrderedDict()
 

    # Define the Regexp Patterns to Parse ..

    root_params_pat_non_root='\s+Root ID\s+Priority\s+([0-9]+)\r\n\s+Address\s+({0})\r\n\s+Cost\s+([0-9]+)\r\nPort\s+([0-9]+)\s+\(([a-zA-Z0-9\-]+)\)\r\n\s+Hello Time\s+([0-9]+)\s+sec\s+Max\s+Age\s+([0-9]+)\s+sec\s+Forward\s+Delay\s+([0-9]+)\s+sec\r\n'.format(rex.MACADDR)
    root_params_pat_root='\s+Root ID\s+Priority\s+([0-9]+)\r\n\s+Address\s+({0})\r\n\s+This bridge is the root\r\n\s+Hello Time\s+([0-9]+)\s+sec\s+Max\s+Age\s+([0-9]+)\s+sec\s+Forward\s+Delay\s+([0-9]+)\s+sec\r\n'.format(rex.MACADDR)
    bridge_params_pat='\s+Bridge ID\s+Priority\s+([0-9]+)\s+\(priority\s+([0-9]+)\s+sys-id-ext ([0-9]+)\)\r\n\s+Address\s+({0})\r\n\s+Hello\s+Time\s+([0-9]+)\s+sec\s+Max\s+Age\s+([0-9+)\s+sec\s+Forward Delay\s+([0-9]+) sec\r\n'.format(rex.MACADDR)
    #interface_params_pat='-------\r\n({0})\s+([a-zA-Z]+)\s+([A-Z]+)\s+([0-9]+)\s+([0-9]+).([0-9]+)\s+([\(\)a-zA-Z0-9\s]+)\r'.format(rex.INTERFACE_NAME)
    interface_params_pat='({0})\s+([a-zA-Z]+)\s+([A-Z]+)[\*\s]+([0-9]+)\s+([0-9]+).([0-9]+)\s+'.format(rex.INTERFACE_NAME)


    # Build the command to be executed based on the arguments passed ..
    cmd = 'show spanning-tree '

    cmd = cmd + 'vlan ' + str(vlan)


    show_stp=cli_ex(cmd)

    # Split the output of STP based on VLAN
    show_stp_vlan_split=show_stp.split('VLAN')


    # Iterate over every VLAN block and build the show_stp_dict
    for stp_vlan in show_stp_vlan_split:

      if re.search( '^([0-9]+)', stp_vlan ):

         #removed backslash r
         match=re.search( '^([0-9]+)\n\s+Spanning tree enabled protocol ([a-z]+)', stp_vlan, re.I )
         vlan_id = int(match.group(1))
         stp_mode = match.group(2)
         show_stp_dict[vlan_id]={}
         show_stp_dict[vlan_id]['stp_mode']=stp_mode
         

         if re.search( root_params_pat_root, stp_vlan, re.I ):
             root_info=re.findall( root_params_pat_root, stp_vlan, re.I )
             show_stp_dict[vlan_id]['root_info']=convertListToDict( root_info, ['Priority','Address', \
                 'Hello Time','Max Age','Forward Delay'], ['Priority','Address'])
             show_stp_dict[vlan_id]['root']=True
         else:
             root_info=re.findall( root_params_pat_non_root, stp_vlan, re.I )
             show_stp_dict[vlan_id]['root_info']=convertListToDict( root_info, ['Priority','Address','Cost', \
                 'Port','Hello Time','Max Age','Forward Delay'], ['Priority','Address','Cost', 'Port'])
             show_stp_dict[vlan_id]['root']=False

         bridge_info=re.findall( bridge_params_pat, stp_vlan, re.I )
         show_stp_dict[vlan_id]['bridge_info']=convertListToDict( root_info, ['Priority','Address', \
                'Hello Time','Max Age','Forward Delay'], ['Priority','Address'])

         intf_info=re.findall( interface_params_pat, stp_vlan, re.I )
         show_stp_dict[vlan_id]['Interface_info']=convertListToDict( intf_info, [ 'Interface', 'Role', 'Status', \
                'Cost', 'Prio', 'Nbr' ] , [ 'Interface' ] )

    # Split the output of STP based on MST 
    show_stp_mst_split=show_stp.split('MST')

    for mst_id in show_stp_mst_split:                                                                            
                                                                                                                  
      if re.search( '^([0-9]+)', mst_id):                                                                         
                                                                                                                  
         #removed backslash r                                                                                              
         match=re.search( '^([0-9]+)\n\s+Spanning tree enabled protocol ([a-z]+)', mst_id, re.I )                 
         mst = vlan                                                                        
         stp_mode = match.group(2)                                                                                
         show_stp_dict[mst]={}                                                                                    
         show_stp_dict[mst]['stp_mode']=stp_mode                                                              
                                                                                                              
                                                                                                              
         if re.search( root_params_pat_root, mst_id, re.I ):                                                  
             root_info=re.findall( root_params_pat_root, mst_id, re.I )                                       
             show_stp_dict[mst]['root_info']=convertListToDict( root_info, ['Priority','Address', \
                 'Hello Time','Max Age','Forward Delay'], ['Priority','Address'])                             
             show_stp_dict[mst]['root']=True                
         else:                                                                                                    
             root_info=re.findall( root_params_pat_non_root, mst_id, re.I )                                       
             show_stp_dict[mst]['root_info']=convertListToDict( root_info, ['Priority','Address','Cost', \
                 'Port','Hello Time','Max Age','Forward Delay'], ['Priority','Address','Cost', 'Port'])           
             show_stp_dict[mst]['root']=False                                                             
                                                                                                                  
         bridge_info=re.findall( bridge_params_pat, mst_id, re.I )                                                
         show_stp_dict[mst]['bridge_info']=convertListToDict( root_info, ['Priority','Address', \
                'Hello Time','Max Age','Forward Delay'], ['Priority','Address'])                              
                                                                                                              
         intf_info=re.findall( interface_params_pat, mst_id, re.I )                                           
         show_stp_dict[mst]['Interface_info']=convertListToDict( intf_info, [ 'Interface', 'Role', 'Status', \
                'Cost', 'Prio', 'Nbr' ] , [ 'Interface' ] )               
    return show_stp_dict
    
def pprint_table(out, table):
    """Prints out a table of data, padded for alignment
    @param out: Output stream (file-like object)
    @param table: The table to print. A list of lists.
    Each row must have the same number of columns. """
    col_paddings = []

    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:
        # left col
        print >> out, row[0].ljust(col_paddings[0] + 1),
        # rest of the cols
        for i in range(1, len(row)):
            col = format_num(row[i]).rjust(col_paddings[i] + 2)
            print >> out, col,
        print >> out 
 

def validateIP(ip):
    try:
       socket.inet_aton(ip)
       return 0
    except socket.error:
       return 1

def convertIP(ip):
    hexIP = []
    [hexIP.append(hex(int(x))[2:].zfill(2)) for x in ip.split('.')]
    hexIP = "0x" + "".join(hexIP)
    return hexIP

class createEventHistoryTableObject(object):

    """ Class to parse the event history outputs and convert to dictionary format. Expects the
    input as 'Index: <Row>' where the <Row> is in key value pairs separated by commas"""

    def __init__( self, event_history_dump ):

       import re
       time_format = "at %f usecs after %a %b %d %H:%M:%S %Y"

       self.table=[]

       table_rows=event_history_dump.split('\n')
       new = {}
       esq_req_rsp = {}
       esqs = []
       esq_start = []
       req_rsp = True
       for row in table_rows:
          if "FSM" in row:
              continue
          if ":" not in row:
                 continue

          if "Previous state:" in row:
              if req_rsp == False:
                  esq_start.append(esq_req_rsp)
                  req_rsp = True
                  esq_req_rsp = {}

              if len(esq_start) > 0:
                  esqs.append(esq_start)
                  esq_start = []

              continue
          if "Triggered event:" in row:
              if req_rsp == False:
                  esq_start.append(esq_req_rsp)
                  req_rsp = True
                  esq_req_rsp = {}

              if len(esq_start) > 0:
                  esqs.append(esq_start)
                  esq_start = []

              continue
          if "Next state:" in row:
              if req_rsp == False:
                  esq_start.append(esq_req_rsp)
                  req_rsp = True
                  esq_req_rsp = {}

              if len(esq_start) > 0:
                  esqs.append(esq_start)
                  esq_start = []

              continue


          if "ESQ_START" in row:
              if req_rsp == False:
                  esq_start.append(esq_req_rsp)
                  req_rsp = True
                  esq_req_rsp = {}

              if len(esq_start) > 0:
                  esqs.append(esq_start)

              esq_start = []
              continue

          if "ESQ_REQ" in row or "ESQ_RSP" in row:
              old = esq_req_rsp
              esq_req_rsp = {}
              if len(old) > 0:
                  esq_start.append(old)
                  req_rsp = True

          if "usecs after" in row:
              y = row.split(',')[1].strip()
              t = datetime.datetime.strptime(y, time_format)
              esq_req_rsp['TIME'] = t
              esq_req_rsp['TIME_STRING'] = row

          kvpairs = row.split(',')
          for val in kvpairs:
              
              x = val.strip(' ').strip('\r').split(':')
              if len(x) != 2:
                  continue

              (tk, tv)=val.split(':')
              row_key = tk.strip(' ')
              row_value = tv.strip(' ')
              req_rsp = False
              esq_req_rsp[row_key]=row_value

       if req_rsp == False:
           esq_start.append(esq_req_rsp)
           esqs.append(esq_start)

       self.table = esqs
       

########NEW FILE########
__FILENAME__ = xmltodict
#Copyright (C) 2012 Martin Blech and individual contributors.

#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#!/usr/bin/env python
"Makes working with XML feel like you are working with JSON"

from xml.parsers import expat
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl
try: # pragma no cover
    from cStringIO import StringIO
except ImportError: # pragma no cover
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO
try: # pragma no cover
    from collections import OrderedDict
except ImportError: # pragma no cover
    OrderedDict = dict

try: # pragma no cover
    _basestring = basestring
except NameError: # pragma no cover
    _basestring = str
try: # pragma no cover
    _unicode = unicode
except NameError: # pragma no cover
    _unicode = str

__author__ = 'Martin Blech'
__version__ = '0.5.0'
__license__ = 'MIT'

class ParsingInterrupted(Exception): pass

class _DictSAXHandler(object):
    def __init__(self,
                 item_depth=0,
                 item_callback=lambda *args: True,
                 xml_attribs=True,
                 attr_prefix='@',
                 cdata_key='#text',
                 force_cdata=False,
                 cdata_separator='',
                 postprocessor=None,
                 dict_constructor=OrderedDict,
                 strip_whitespace=True):
        self.path = []
        self.stack = []
        self.data = None
        self.item = None
        self.item_depth = item_depth
        self.xml_attribs = xml_attribs
        self.item_callback = item_callback
        self.attr_prefix = attr_prefix
        self.cdata_key = cdata_key
        self.force_cdata = force_cdata
        self.cdata_separator = cdata_separator
        self.postprocessor = postprocessor
        self.dict_constructor = dict_constructor
        self.strip_whitespace = strip_whitespace

    def startElement(self, name, attrs):
        attrs = self.dict_constructor(zip(attrs[0::2], attrs[1::2]))
        self.path.append((name, attrs or None))
        if len(self.path) > self.item_depth:
            self.stack.append((self.item, self.data))
            if self.xml_attribs:
                attrs = self.dict_constructor(
                    (self.attr_prefix+key, value)
                    for (key, value) in attrs.items())
            else:
                attrs = None
            self.item = attrs or None
            self.data = None

    def endElement(self, name):
        if len(self.path) == self.item_depth:
            item = self.item
            if item is None:
                item = self.data
            should_continue = self.item_callback(self.path, item)
            if not should_continue:
                raise ParsingInterrupted()
        if len(self.stack):
            item, data = self.item, self.data
            self.item, self.data = self.stack.pop()
            if self.strip_whitespace and data is not None:
                data = data.strip() or None
            if data and self.force_cdata and item is None:
                item = self.dict_constructor()
            if item is not None:
                if data:
                    self.push_data(item, self.cdata_key, data)
                self.item = self.push_data(self.item, name, item)
            else:
                self.item = self.push_data(self.item, name, data)
        else:
            self.item = self.data = None
        self.path.pop()

    def characters(self, data):
        if not self.data:
            self.data = data
        else:
            self.data += self.cdata_separator + data

    def push_data(self, item, key, data):
        if self.postprocessor is not None:
            result = self.postprocessor(self.path, key, data)
            if result is None:
                return item
            key, data = result
        if item is None:
            item = self.dict_constructor()
        try:
            value = item[key]
            if isinstance(value, list):
                value.append(data)
            else:
                item[key] = [value, data]
        except KeyError:
            item[key] = data
        return item

def parse(xml_input, encoding='utf-8', expat=expat, *args, **kwargs):
    """Parse the given XML input and convert it into a dictionary.

    `xml_input` can either be a `string` or a file-like object.

    If `xml_attribs` is `True`, element attributes are put in the dictionary
    among regular child elements, using `@` as a prefix to avoid collisions. If
    set to `False`, they are just ignored.

    Simple example::

        >>> doc = xmltodict.parse(\"\"\"
        ... <a prop="x">
        ...   <b>1</b>
        ...   <b>2</b>
        ... </a>
        ... \"\"\")
        >>> doc['a']['@prop']
        u'x'
        >>> doc['a']['b']
        [u'1', u'2']

    If `item_depth` is `0`, the function returns a dictionary for the root
    element (default behavior). Otherwise, it calls `item_callback` every time
    an item at the specified depth is found and returns `None` in the end
    (streaming mode).

    The callback function receives two parameters: the `path` from the document
    root to the item (name-attribs pairs), and the `item` (dict). If the
    callback's return value is false-ish, parsing will be stopped with the
    :class:`ParsingInterrupted` exception.

    Streaming example::

        >>> def handle(path, item):
        ...     print 'path:%s item:%s' % (path, item)
        ...     return True
        ...
        >>> xmltodict.parse(\"\"\"
        ... <a prop="x">
        ...   <b>1</b>
        ...   <b>2</b>
        ... </a>\"\"\", item_depth=2, item_callback=handle)
        path:[(u'a', {u'prop': u'x'}), (u'b', None)] item:1
        path:[(u'a', {u'prop': u'x'}), (u'b', None)] item:2

    The optional argument `postprocessor` is a function that takes `path`, `key`
    and `value` as positional arguments and returns a new `(key, value)` pair
    where both `key` and `value` may have changed. Usage example::

        >>> def postprocessor(path, key, value):
        ...     try:
        ...         return key + ':int', int(value)
        ...     except (ValueError, TypeError):
        ...         return key, value
        >>> xmltodict.parse('<a><b>1</b><b>2</b><b>x</b></a>',
        ...                 postprocessor=postprocessor)
        OrderedDict([(u'a', OrderedDict([(u'b:int', [1, 2]), (u'b', u'x')]))])

    You can pass an alternate version of `expat` (such as `defusedexpat`) by
    using the `expat` parameter. E.g:

        >>> import defusedexpat
        >>> xmltodict.parse('<a>hello</a>', expat=defusedexpat.pyexpat)
        OrderedDict([(u'a', u'hello')])

    """
    handler = _DictSAXHandler(*args, **kwargs)
    parser = expat.ParserCreate()
    parser.ordered_attributes = True
    parser.StartElementHandler = handler.startElement
    parser.EndElementHandler = handler.endElement
    parser.CharacterDataHandler = handler.characters
    try:
        parser.ParseFile(xml_input)
    except (TypeError, AttributeError):
        if isinstance(xml_input, _unicode):
            xml_input = xml_input.encode(encoding)
        parser.Parse(xml_input, True)
    return handler.item

def _emit(key, value, content_handler,
          attr_prefix='@',
          cdata_key='#text',
          root=True,
          preprocessor=None):
    if preprocessor is not None:
        result = preprocessor(key, value)
        if result is None:
            return
        key, value = result
    if not isinstance(value, (list, tuple)):
        value = [value]
    if root and len(value) > 1:
        raise ValueError('document with multiple roots')
    for v in value:
        if v is None:
            v = OrderedDict()
        elif not isinstance(v, dict):
            v = _unicode(v)
        if isinstance(v, _basestring):
            v = OrderedDict(((cdata_key, v),))
        cdata = None
        attrs = OrderedDict()
        children = []
        for ik, iv in v.items():
            if ik == cdata_key:
                cdata = iv
                continue
            if ik.startswith(attr_prefix):
                attrs[ik[len(attr_prefix):]] = iv
                continue
            children.append((ik, iv))
        content_handler.startElement(key, AttributesImpl(attrs))
        for child_key, child_value in children:
            _emit(child_key, child_value, content_handler,
                  attr_prefix, cdata_key, False, preprocessor)
        if cdata is not None:
            content_handler.characters(cdata)
        content_handler.endElement(key)

def unparse(item, output=None, encoding='utf-8', **kwargs):
    ((key, value),) = item.items()
    must_return = False
    if output == None:
        output = StringIO()
        must_return = True
    content_handler = XMLGenerator(output, encoding)
    content_handler.startDocument()
    _emit(key, value, content_handler, **kwargs)
    content_handler.endDocument()
    if must_return:
        value = output.getvalue()
        try: # pragma no cover
            value = value.decode(encoding)
        except AttributeError: # pragma no cover
            pass
        return value

if __name__ == '__main__': # pragma: no cover
    import sys
    import marshal

    (item_depth,) = sys.argv[1:]
    item_depth = int(item_depth)

    def handle_item(path, item):
        marshal.dump((path, item), sys.stdout)
        return True

    try:
        root = parse(sys.stdin,
                     item_depth=item_depth,
                     item_callback=handle_item,
                     dict_constructor=dict)
        if item_depth == 0:
            handle_item([], root)
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = _cisco
# Copyright (C) 2013 Cisco Systems Inc.
# All rights reserved
'''
Dummy file. Some cisco modules import _cisco module, which is a shared library
on the switch. The library does not work off the box. 

Providing a dummy file so that things compile. However 
cisco_socket.py 
md5sum.py
will not work properly, given they depend on the _cisco shared module.
'''
########NEW FILE########
__FILENAME__ = decorate_clid
#!/usr/bin/env python
#
# Copyright (C) 2013 Cisco Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0 
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# This script shows how to use a decorator to change the behavior of the clid
# function from returning a string (which is the default for the 6.1(2)I1(1)
# image on the Nexus 9000) to returning a dictionary.  If this script is
# installed in bootflash://scripts on the Nexus 9000, it can be run using the
# source command:
#
#    source decorate_clid.py
#
# Or it can be run using python from NX-OS (VSH):
#
#    python bootflash:///scripts/decorate_clid.py
#
# Or using python from bash:
#
#    run bash
#    python /bootflash/scripts/decorate_clid.py
#
# Example output:
#
# Switch# source decorate_clid.py
# Type of original clid output: <type 'str'>
# Type of new clid output: <type 'dict'>
# Switch#
#

import json
from cli import *

# Here's our decorator.  The wrapper simply wraps the previous
# function in a json.loads() call to load the json encoded
# string into a dictionary and then returns it.
def dict_decorator(target_function):
    def wrapper(cmd):
        return json.loads(target_function(cmd))
    return wrapper

# Let's see how the current beahvior is.
original = clid("show interface brief")
print "Type of original clid output: " + str(type(original))

# This doesn't use the @ decorator syntax but it _is_ a
# decorator none the less.
clid = dict_decorator(clid)

# Let's see what our decorator does
new = clid("show interface brief")
print "Type of new clid output: " + str(type(new))
########NEW FILE########
__FILENAME__ = enable_and_tail_enhanced_nxapi_debugs
#!/usr/bin/env python
#
# Copyright (C) 2013 Cisco Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0 
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# This script can be used to quickly and easily enable and monitor nx-api
# sessions and debugs on a Nexus 9000 Standalone Switch.  If the script
# is copied into bootflash:///scripts, it can be run as:
#
#    source enable_and_tail_enhanced_nxapi_debugs
#

import os
import sys
import time

def touch(path):
    """ Touch the path, which means create it if it doesn't exist and set the
        path's utime.
    """
    with open(path, 'a'):
        os.utime(path, None)

def get_root(file):
    """ Returns the root filesystem designator in a non-platform-specific way
    """
    somepath = os.path.abspath(sys.executable)
    (drive, path) = os.path.splitdrive(somepath)
    while 1:
        (path, directory) = os.path.split(path)
        if not directory:
            break
    return drive + path

def print_file_from(filename, pos):
    """ Determine where to start printing from within a file
    """
    with open(filename, 'rb') as fh:
        fh.seek(pos)
        while True:
            chunk = fh.read(8192)
            if not chunk:
                break
            sys.stdout.write(chunk)

def _fstat(filename):
    """ stat the file
    """
    st_results = os.stat(filename)
    return (st_results[6], st_results[8])

def _print_if_needed(filename, last_stats):
    changed = False
    #Find the size of the file and move to the end
    tup = _fstat(filename)
    if last_stats[filename] != tup:
        changed = True
        print_file_from(filename, last_stats[filename][0])
        last_stats[filename] = tup
    return changed

def multi_tail(filenames, stdout=sys.stdout, interval=1, idle=10):
    S = lambda (st_size, st_mtime): (max(0, st_size - 124), st_mtime)
    last_stats = dict((fn, S(_fstat(fn))) for fn in filenames)
    last_print = 0
    while 1:
        changed = False
        for filename in filenames:
            if _print_if_needed(filename, last_stats):
                changed = True
        if changed:
            if idle > 0:
                last_print = time.time()
        else:
            if idle > 0 and last_print is not None:
                if time.time() - last_print >= idle:
                    last_print = None
            time.sleep(interval)


# Build a path to the logflag file in a platform non-specific way
nxapi_logs_directory = os.path.join(get_root(sys.executable), 'var', 'nginx', 'logs')
nxapi_enable_debug_file = os.path.join(nxapi_logs_directory, "logflag")

# Touch that file so enhanced nxapi debugs start to be logged
touch(nxapi_enable_debug_file)

print "Tailing the access.log, error.log and the nginx.log, use cntl-c (^C)"
print "to exit."

# Tail the logs
logs = []
logs.append(os.path.join(nxapi_logs_directory, "access.log"))
logs.append(os.path.join(nxapi_logs_directory, "error.log"))
logs.append(os.path.join(nxapi_logs_directory, "nginx.log"))

try:
    multi_tail(logs)
except KeyboardInterrupt:
    pass

# Clean up
try:
    os.remove(nxapi_enable_debug_file)
except:
    pass
########NEW FILE########
__FILENAME__ = get_all_internal_versions
#!/usr/bin/env python
#
# Copyright (C) 2013 Cisco Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0 
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script can be saved to bootflash:///scripts and then run via:
#
#    source get_all_internal_versions.py
#
# The script will get the output of show module, get the
# module number of every component, then print the output of
#            show hardware internal dev-version
# for every component
#

from cli import *
import json

# clid does not produce a dictionary on the Nexus 9000, it
# produces a json encoded string so load it into a dictionary
showmodout=json.loads(clid('show module'))

modlist = []

# Create a list of module number populated with components
# This gets most of everything, including sups, system controllers,
# fabric modules, linecards, ets.
for modrow in showmodout["TABLE_modwwninfo"]["ROW_modwwninfo"]:
    modlist.append(modrow["modwwn"])

# If we have at least one component to print out (which we should)
# print out a string a hypens for consistency
if len(modlist) > 0:
    print "-" * 68
    
for mod in modlist:
    # Label each output so we know which output goes where.
    print "Internal version for module " + mod
    print "-" * 68
    clip("slot " + mod + " show hardware internal dev-version")
    print "-" * 68
########NEW FILE########
__FILENAME__ = get_python_supported_features_status
#!/usr/bin/env python
#
# Copyright (C) 2013 Cisco Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0 
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script can be saved to bootflash:///scripts and then run via:
#
#    source get_python_supported_features_status.py
#
# or it can be run by python natively from NX-OS (VSH):
#
#    python bootflash:///scripts/get_python_supported_features_status.py
#
# or from Bash:
#
#    run bash
#    python /bootflash/scripts/get_python_supported_features_status.py
#

# For formatting the output
import string
# This is all we need to import from the cisco package
from cisco.feature import Feature

print ""
print "Python supported features status:"
print "=" * 68

# Get all the features that python can play with on this device
# Feature.allSupportedFeatures()returns those features as a list of strings
for afeature in Feature.allSupportedFeatures():
    # Setup a temporary string
    temp_string = ""
    # Use the cisco.feature.FeatureFactory to create a temporary object based
    # on the feature name
    temp_feature_obj = Feature.get(afeature)
    # See if the feature is enabled or disabled
    status = temp_feature_obj.is_enabled()
    # Build the output string, start by adding the feature name to it, left
    # justified, padded by white space to ensure 11 characters
    temp_string += string.ljust(afeature, 11)
    # Now add the word "is", centered and padded with space to ensure 3
    # characters
    temp_string += string.center("is", 3)
    # Now add the 'Enabled' or 'Disabled' string depending on the status
    # using a ternary operator, right justified and padded with white
    # space to ensure at least 11 characters
    temp_string += string.rjust(("Enabled" if Feature.get(afeature).is_enabled() else
        "Disabled"), 11)
    print temp_string

print ""
########NEW FILE########
__FILENAME__ = showtrans
#!/usr/bin/env python
#
#
# Copyright (C) 2013 Cisco Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); 
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at 
#
#      http://www.apache.org/licenses/LICENSE-2.0 
#
# Unless required by applicable law or agreed to in writing, software 
# distributed under the License is distributed on an "AS IS" BASIS, 
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and 
# limitations under the License.
#
# v1.2
# verified with  NXOS image file is: bootflash:///n9000-dk9.6.1.2.I1.0.1.bin
#

import re
import sys
from cli import *
from xml.dom import minidom 

# color escape sequences
color_red="\x1b[31;01m"
color_green="\x1b[00;32m"
color_blue="\x1b[34;01m"
color_normal="\x1b[00m"

'''This script creates a pretty table with transceiver information and CDP neighbor detail 
   for each Ethernet interface present in the system
   '''

def nxos_help_string(args):
    # display online help (if asked for) for NX-OS' "source" command 
    # either in config mode or at the exec prompt, if users type "source <script> ?" then help_string appears
    nb_args = len(args)
    if nb_args > 1:
        help_string = color_green + "Returns a list of interfaces with transceiver information. No arguments required." + color_normal
        m = re.match('__cli_script.*help', args[1])
        if m:
                # user entered "source ?" with no parameters: display script help
                if args[1] == "__cli_script_help":
                    print help_string
                    exit(0)
                # argument help
                argv = args[2:]
                # dont count last arg if it was partial help (no-space-question-mark)
                if args[1] == "__cli_script_args_help_partial":
                    argv = argv[:-1]
                nb_args = len(argv)
                # only file name provided: use man-page style help
                print "__man_page"
                print help_string
                exit(0)

def NodeAsText(node):
    # convert a XML element to a string
    try:
        nodetext=node[0].firstChild.data.strip()
        return nodetext
    except IndexError:
        return "__na__"   

def strip_netconf_trailer(x):
    # remove NETCONF's trailing delimiter
    x=x.strip('\\n]]>]]>')
    x+='>'
    return x
	 
def get_CDP(xml):
    # build a dictionary of CDP neighbors with key = interface
    # the format of the dictionary is as follows:
    # neighbors = {'intf': {neighbor: 'foo', remoteport: 'x/y', model: 'bar'}}    
	# this is what NXOS returns:
    # <ROW_cdp_neighbor_brief_info>
          # <ifindex>438829568</ifindex>
          # <device_id>ts-n6k-2(FOC1712R0RX)</device_id>
          # <intf_id>Ethernet6/2</intf_id>
          # <ttl>164</ttl>
          # <capability>router</capability>
          # <capability>switch</capability>
          # <capability>IGMP_cnd_filtering</capability>
          # <capability>Supports-STP-Dispute</capability>
          # <platform_id>N6K-C6004-96Q</platform_id>
          # <port_id>Ethernet1/2</port_id>
    # </ROW_cdp_neighbor_brief_info>
    neighbors = xml.getElementsByTagName("ROW_cdp_neighbor_brief_info")
    cdpdict = {}
    for neighbor in neighbors:
        cdpintf  =  NodeAsText(neighbor.getElementsByTagName("intf_id"))
        cdpintf  =  cdpintf.replace("Ethernet","Eth")
        cdpneig  =  NodeAsText(neighbor.getElementsByTagName("device_id"))
        cdpport  =  NodeAsText(neighbor.getElementsByTagName("port_id"))
        cdpmodel =  NodeAsText(neighbor.getElementsByTagName("platform_id"))
        cdpipaddr = NodeAsText(neighbor.getElementsByTagName("num_mgmtaddr"))
        cdpdict[cdpintf]={'neighbor': cdpneig, \
                          'remoteport': cdpport, \
                          'model': cdpmodel,\
                          'ipaddr': cdpipaddr}
    return cdpdict

def get_intf(xml):
    # build a dictionary of interface details with key = interface
    # the format of the dictionary is as follows:
    # interfaces = {'interface': {iomodule: 'foo', transtype: 'foo', transname: 'foo', transpart: 'foo', transsn: 'foo', bitrate: '100', length: '5'}}    
	# this is what NXOS returns:
    # <ROW_interface>
          # <interface>Ethernet4/1/1</interface>
          # <sfp>present</sfp>
          # <type>QSFP40G-4SFP10G-CU5M</type>
          # <name>CISCO-AMPHENOL  </name>
          # <partnum>605410005       </partnum>
          # <rev>A </rev>
          # <serialnum>APF154300V9     </serialnum>
          # <nom_bitrate>10300</nom_bitrate>
          # <len_cu>5</len_cu>
          # <ciscoid>--</ciscoid>
          # <ciscoid_1>0</ciscoid_1>
    # </ROW_interface>
    interfaces = xml.getElementsByTagName("ROW_interface")
    intfdict = {}
    for intf in interfaces:
        if NodeAsText(intf.getElementsByTagName("sfp"))=="present":
            interface   =  NodeAsText(intf.getElementsByTagName("interface"))
            interface   =  interface.replace("Ethernet","Eth")
            slot        =  re.search("\d",interface)                               # find slot number            
            iomodule    =  mod_dict[slot.group(0)]['model']                        # and use it to find io_module
            transtype   =  NodeAsText(intf.getElementsByTagName("type"))
            transname   =  NodeAsText(intf.getElementsByTagName("name"))
            transpart   =  NodeAsText(intf.getElementsByTagName("partnum"))
            transsn     =  NodeAsText(intf.getElementsByTagName("serialnum"))
            bitrate     =  NodeAsText(intf.getElementsByTagName("nom_bitrate"))
            length      =  NodeAsText(intf.getElementsByTagName("len_cu"))
            intfdict[interface]={'iomodule': iomodule,\
                                 'transtype': transtype, \
                                 'transname': transname, \
                                 'transpart': transpart,\
                                 'transsn': transsn,\
				 'bitrate': bitrate,\
				 'length': length}
    return intfdict

def get_intf_capa(xml):
	# <ROW_interface>
         # <interface>Ethernet4/1/4</interface>
         # <model>N9K-X9636PQ</model>
         # <type>QSFP40G-4SFP10G-CU5M</type>
         # <speed>10000</speed>
         # <duplex>full</duplex>
         # <trunk_encap>802.1Q</trunk_encap>
         # <dce_capable>no</dce_capable>
         # <channel>yes</channel>
         # <bcast_supp>percentage(0-100)</bcast_supp>
         # <flo_ctrl>rx-(off/on/desired),tx-(off/on/desired)</flo_ctrl>
         # <rate_mode>dedicated</rate_mode>
         # <port_mode>Routed,Switched</port_mode>
         # <qos_scheduling>rx-(none),tx-(4q)</qos_scheduling>
         # <cos_rewrite>yes</cos_rewrite>
         # <tos_rewrite>yes</tos_rewrite>
         # <span>yes</span>
         # <udld>yes</udld>
         # <mdix>no</mdix>
         # <tdr>no</tdr>
         # <lnk_debounce>yes</lnk_debounce>
         # <lnk_debounce_time>yes</lnk_debounce_time>
         # <fex_fabric>yes</fex_fabric>
         # <dot1q_tunnel>yes</dot1q_tunnel>
         # <pvlan_trunk_mode>yes</pvlan_trunk_mode>
         # <port_group_members>4</port_group_members>
         # <eee_capable>no</eee_capable>
         # <pfc_capable>yes</pfc_capable>
        # </ROW_interface>
    interfaces = xml.getElementsByTagName("ROW_interface")
    capadict = {}
    for intf in interfaces:
        interface   =  NodeAsText(intf.getElementsByTagName("interface"))
        interface   =  interface.replace("Ethernet","Eth")
        speed       =  NodeAsText(intf.getElementsByTagName("speed"))
        capadict[interface]={'speed': speed}
    return capadict
	
def get_modules(xml):
    # build a dictionary of i/o modules details with key = slot_number
    # the format of the dictionary is as follows:
    # modules = {'slot_number': {model: 'foo'}}    
	# this is what NXOS returns:
	# <ROW_modinfo>
         # <modinf>6</modinf>
         # <ports>36</ports>
         # <modtype>36p 40G Ethernet Module</modtype>
         # <model>N9K-X9636PQ</model>
         # <status>ok</status>
    # </ROW_modinfo>
    modules = xml.getElementsByTagName("ROW_modinfo")
    moddict = {}
    for mod in modules:
        slot=NodeAsText(mod.getElementsByTagName("modinf"))
        try:
	    # fix for a condition where a module reports no model
	    model=NodeAsText(mod.getElementsByTagName("model"))
        except:
	    model=''
	moddict[slot]={'model': model}
    return moddict
	
# Main
nxos_help_string(sys.argv)
intf_list     = cli('show int transceiver detail | xml').replace("\n", '')
cdp_neighbors = cli('show cdp neighbor | xml').replace("\n", '')
io_modules    = cli('show module | xml').replace("\n", '')
intf_capa     = cli('show int capa | xml').replace("\n", '')

# current NXOS and eNXOS versions return NETCONF-friendly XML. We must remove the delimiter.
cdp_neighbors = strip_netconf_trailer(cdp_neighbors)
intf_list     = strip_netconf_trailer(intf_list)
io_modules    = strip_netconf_trailer(io_modules)
intf_capa     = strip_netconf_trailer(intf_capa)

cdp_xml   = minidom.parseString(cdp_neighbors)
cdp_dict  = get_CDP(cdp_xml)
mod_xml   = minidom.parseString(io_modules)
mod_dict  = get_modules(mod_xml)
intf_xml  = minidom.parseString(intf_list)
intf_dict = get_intf(intf_xml)
capa_xml  = minidom.parseString(intf_capa)
capa_dict = get_intf_capa(capa_xml)

header1 = 'Interface  Model          Type                   Name               Part               Speed    Len      CDP Neighbor          '     
header2 = '=========================================================================================================================================='

print color_green+header1
print header2+color_normal

for interface in sorted(intf_dict):
    model = intf_dict[interface]['iomodule']
    type  = intf_dict[interface]['transtype']
    name  = intf_dict[interface]['transname']
    part  = intf_dict[interface]['transpart']
    speed = capa_dict[interface]['speed']
    lencu = intf_dict[interface]['length']
    try:
        cdp = cdp_dict[interface]['neighbor'] + '@' + cdp_dict[interface]['remoteport']
    except KeyError:
            cdp = '__na__'
    str = '{0: <8} | {1: <12} | {2: <20} | {3: <16} | {4: <16} | {5: <6} | {6: <6} | {7:16}'.format(interface,model,type,name,part,speed,lencu,cdp)
    print color_blue+str
print color_normal

########NEW FILE########
__FILENAME__ = show_python_supported_features_status

########NEW FILE########
