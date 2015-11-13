__FILENAME__ = chnroutes
#!/usr/bin/env python

import re
import urllib2
import sys
import argparse
import math
import textwrap


def generate_ovpn(metric):
    results = fetch_ip_data()  
    rfile=open('routes.txt','w')
    for ip,mask,_ in results:
        route_item="route %s %s net_gateway %d\n"%(ip,mask,metric)
        rfile.write(route_item)
    rfile.close()
    print "Usage: Append the content of the newly created routes.txt to your openvpn config file," \
          " and also add 'max-routes %d', which takes a line, to the head of the file." % (len(results)+20)


def generate_linux(metric):
    results = fetch_ip_data()
    upscript_header=textwrap.dedent("""\
    #!/bin/bash
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"
    
    OLDGW=`ip route show | grep '^default' | sed -e 's/default via \\([^ ]*\\).*/\\1/'`
    
    if [ $OLDGW == '' ]; then
        exit 0
    fi
    
    if [ ! -e /tmp/vpn_oldgw ]; then
        echo $OLDGW > /tmp/vpn_oldgw
    fi
    
    """)
    
    downscript_header=textwrap.dedent("""\
    #!/bin/bash
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"
    
    OLDGW=`cat /tmp/vpn_oldgw`
    
    """)
    
    upfile=open('ip-pre-up','w')
    downfile=open('ip-down','w')
    
    upfile.write(upscript_header)
    upfile.write('\n')
    downfile.write(downscript_header)
    downfile.write('\n')
    
    for ip,mask,_ in results:
        upfile.write('route add -net %s netmask %s gw $OLDGW\n'%(ip,mask))
        downfile.write('route del -net %s netmask %s\n'%(ip,mask))

    downfile.write('rm /tmp/vpn_oldgw\n')


    print "For pptp only, please copy the file ip-pre-up to the folder/etc/ppp," \
          "and copy the file ip-down to the folder /etc/ppp/ip-down.d."

def generate_mac(metric):
    results=fetch_ip_data()
    
    upscript_header=textwrap.dedent("""\
    #!/bin/sh
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"
    
    OLDGW=`netstat -nr | grep '^default' | grep -v 'ppp' | sed 's/default *\\([0-9\.]*\\) .*/\\1/'`

    if [ ! -e /tmp/pptp_oldgw ]; then
        echo "${OLDGW}" > /tmp/pptp_oldgw
    fi
    
    dscacheutil -flushcache

    route add 10.0.0.0/8 "${OLDGW}"
    route add 172.16.0.0/12 "${OLDGW}"
    route add 192.168.0.0/16 "${OLDGW}"
    """)
    
    downscript_header=textwrap.dedent("""\
    #!/bin/sh
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"
    
    if [ ! -e /tmp/pptp_oldgw ]; then
            exit 0
    fi
    
    ODLGW=`cat /tmp/pptp_oldgw`

    route delete 10.0.0.0/8 "${OLDGW}"
    route delete 172.16.0.0/12 "${OLDGW}"
    route delete 192.168.0.0/16 "${OLDGW}"
    """)
    
    upfile=open('ip-up','w')
    downfile=open('ip-down','w')
    
    upfile.write(upscript_header)
    upfile.write('\n')
    downfile.write(downscript_header)
    downfile.write('\n')
    
    for ip,_,mask in results:
        upfile.write('route add %s/%s "${OLDGW}"\n'%(ip,mask))
        downfile.write('route delete %s/%s ${OLDGW}\n'%(ip,mask))
    
    downfile.write('\n\nrm /tmp/pptp_oldgw\n')
    upfile.close()
    downfile.close()
    
    print "For pptp on mac only, please copy ip-up and ip-down to the /etc/ppp folder," \
          "don't forget to make them executable with the chmod command."

def generate_win(metric):
    results = fetch_ip_data()  

    upscript_header=textwrap.dedent("""@echo off
    for /F "tokens=3" %%* in ('route print ^| findstr "\\<0.0.0.0\\>"') do set "gw=%%*"
    
    """)
    
    upfile=open('vpnup.bat','w')
    downfile=open('vpndown.bat','w')
    
    upfile.write(upscript_header)
    upfile.write('\n')
    upfile.write('ipconfig /flushdns\n\n')
    
    downfile.write("@echo off")
    downfile.write('\n')
    
    for ip,mask,_ in results:
        upfile.write('route add %s mask %s %s metric %d\n'%(ip,mask,"%gw%",metric))
        downfile.write('route delete %s\n'%(ip))
    
    upfile.close()
    downfile.close()
    
#    up_vbs_wrapper=open('vpnup.vbs','w')
#    up_vbs_wrapper.write('Set objShell = CreateObject("Wscript.shell")\ncall objShell.Run("vpnup.bat",0,FALSE)')
#    up_vbs_wrapper.close()
#    down_vbs_wrapper=open('vpndown.vbs','w')
#    down_vbs_wrapper.write('Set objShell = CreateObject("Wscript.shell")\ncall objShell.Run("vpndown.bat",0,FALSE)')
#    down_vbs_wrapper.close()
    
    print "For pptp on windows only, run vpnup.bat before dialing to vpn," \
          "and run vpndown.bat after disconnected from the vpn."

def generate_android(metric):
    results = fetch_ip_data()
    
    upscript_header=textwrap.dedent("""\
    #!/bin/sh
    alias nestat='/system/xbin/busybox netstat'
    alias grep='/system/xbin/busybox grep'
    alias awk='/system/xbin/busybox awk'
    alias route='/system/xbin/busybox route'
    
    OLDGW=`netstat -rn | grep ^0\.0\.0\.0 | awk '{print $2}'`
    
    """)
    
    downscript_header=textwrap.dedent("""\
    #!/bin/sh
    alias route='/system/xbin/busybox route'
    
    """)
    
    upfile=open('vpnup.sh','w')
    downfile=open('vpndown.sh','w')
    
    upfile.write(upscript_header)
    upfile.write('\n')
    downfile.write(downscript_header)
    downfile.write('\n')
    
    for ip,mask,_ in results:
        upfile.write('route add -net %s netmask %s gw $OLDGW\n'%(ip,mask))
        downfile.write('route del -net %s netmask %s\n'%(ip,mask))
    
    upfile.close()
    downfile.close()
    
    print "Old school way to call up/down script from openvpn client. " \
          "use the regular openvpn 2.1 method to add routes if it's possible"


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
        
        results.append((starting_ip,mask,mask2))
         
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser(description="Generate routing rules for vpn.")
    parser.add_argument('-p','--platform',
                        dest='platform',
                        default='openvpn',
                        nargs='?',
                        help="Target platforms, it can be openvpn, mac, linux," 
                        "win, android. openvpn by default.")
    parser.add_argument('-m','--metric',
                        dest='metric',
                        default=5,
                        nargs='?',
                        type=int,
                        help="Metric setting for the route rules")
    
    args = parser.parse_args()
    
    if args.platform.lower() == 'openvpn':
        generate_ovpn(args.metric)
    elif args.platform.lower() == 'linux':
        generate_linux(args.metric)
    elif args.platform.lower() == 'mac':
        generate_mac(args.metric)
    elif args.platform.lower() == 'win':
        generate_win(args.metric)
    elif args.platform.lower() == 'android':
        generate_android(args.metric)
    else:
        print>>sys.stderr, "Platform %s is not supported."%args.platform
        exit(1)

########NEW FILE########
__FILENAME__ = main
from __future__ import with_statement
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

import urllib
from models import MyFile

class MainPage(webapp.RequestHandler):
    def get(self):
        q=MyFile.all()
        mfiles=q.fetch(100)
        template_values={'files':mfiles}
        content = template.render('templates/index.html',template_values)
        self.response.out.write(content)

class DownloadHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, resource):
        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        self.send_blob(blob_info)

application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/downloads/([^/]+)?',DownloadHandler),
                                      ], debug=False)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = models
from google.appengine.ext import db


class MyFile(db.Model):
    name = db.StringProperty(required=True)
    blob_key = db.StringProperty(required=True)
    update_date = db.DateProperty()
########NEW FILE########
__FILENAME__ = generate_all
from __future__ import with_statement
import zipfile
import StringIO
from models import MyFile
import re
import urllib2
import math
import textwrap
import datetime

from google.appengine.api import files
from google.appengine.ext import blobstore

def generate_all():
    q=MyFile.all()
    mfiles=q.fetch(100)
    
    # delete all old files and data
    for mf in mfiles:
        bk=mf.blob_key
        blobstore.delete(bk)
        # delete data entity
        mf.delete()
    
    # dict of zipfiles being generated and their relevant generators
    generators={'openvpn.zip':generate_ovpn,
            'windows.zip':generate_win,
            'linux.zip':generate_linux,
            'mac.zip':generate_mac,
            'android.zip':generate_android
            }
    
    ip_data = fetch_ip_data()
    
    for fn,g in generators.iteritems():
        data=g(ip_data)
        z=zipit(data) #compress the data
        blob_file=files.blobstore.create('application/zip', 
                                         _blobinfo_uploaded_filename=fn)
        with files.open(blob_file,'a') as f:
            f.write(z)
        files.finalize(blob_file)
        blob_key = files.blobstore.get_blob_key(blob_file)
        mf=MyFile(name=fn,blob_key=str(blob_key))
        mf.update_date=datetime.datetime.now().date()
        mf.put()

def fetch_ip_data():
    #fetch data from apnic
    url=r'http://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest'
    data=urllib2.urlopen(url).read()
    cnregex=re.compile(r'apnic\|cn\|ipv4\|[0-9\.]+\|[0-9]+\|[0-9]+\|a.*',re.IGNORECASE)
    cndata=cnregex.findall(data)
    ip_data=[]

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
        
        ip_data.append((starting_ip,mask,mask2))
         
    return ip_data

def generate_ovpn(ip_data, metric=25):
    s=StringIO.StringIO()
    for ip,mask,_ in ip_data:
        route_item="route %s %s net_gateway %d\n"%(ip,mask,metric)
        s.write(route_item)
    return {'routes.txt':s.getvalue()}

def generate_linux(ip_data,metric=25):
    upscript_header=textwrap.dedent("""\
    #!/bin/bash
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"
    
    OLDGW=`ip route show | grep '^default' | sed -e 's/default via \\([^ ]*\\).*/\\1/'`
    
    if [ $OLDGW == '' ]; then
        exit 0
    fi
    
    if [ ! -e /tmp/vpn_oldgw ]; then
        echo $OLDGW > /tmp/vpn_oldgw
    fi
    
    """)
    
    downscript_header=textwrap.dedent("""\
    #!/bin/bash
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"
    
    OLDGW=`cat /tmp/vpn_oldgw`
    
    """)
    
    up=StringIO.StringIO()
    down=StringIO.StringIO()
    
    up.write(upscript_header)
    up.write('\n')
    down.write(downscript_header)
    down.write('\n')
    
    for ip,mask,_ in ip_data:
        up.write('route add -net %s netmask %s gw $OLDGW\n'%(ip,mask))
        down.write('route del -net %s netmask %s\n'%(ip,mask))

    down.write('rm /tmp/vpn_oldgw\n')

    return {'ip-pre-up':up.getvalue(),'ip-down':down.getvalue()}

def generate_mac(ip_data,metric=25):
    upscript_header=textwrap.dedent("""\
    #!/bin/sh
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"
    
    OLDGW=`netstat -nr | grep '^default' | grep -v 'ppp' | sed 's/default *\\([0-9\.]*\\) .*/\\1/'`

    if [ ! -e /tmp/pptp_oldgw ]; then
        echo "${OLDGW}" > /tmp/pptp_oldgw
    fi
    
    dscacheutil -flushcache
    
    """)
    
    downscript_header=textwrap.dedent("""\
    #!/bin/sh
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"
    
    if [ ! -e /tmp/pptp_oldgw ]; then
            exit 0
    fi
    
    ODLGW=`cat /tmp/pptp_oldgw`
    
    """)
    
    up=StringIO.StringIO()
    down=StringIO.StringIO()
    
    up.write(upscript_header)
    up.write('\n')
    down.write(downscript_header)
    down.write('\n')
    
    for ip,_,mask in ip_data:
        up.write('route add %s/%s "${OLDGW}"\n'%(ip,mask))
        down.write('route delete %s/%s ${OLDGW}\n'%(ip,mask))
    
    down.write('\n\nrm /tmp/pptp_oldgw\n')
    return {'ip-up':up.getvalue(),'ip-down':down.getvalue()}

def generate_win(ip_data,metric=25):

    upscript_header="@echo off\r\n" + """for /F "tokens=3" %%* in ('route print ^| findstr "\\<0.0.0.0\\>"') do set "gw=%%*"\r\n"""
    
    up=StringIO.StringIO()
    down=StringIO.StringIO()
    
    up.write(upscript_header)
    up.write('\r\n')
    up.write('ipconfig /flushdns\r\n')
    
    down.write("@echo off")
    down.write('\r\n')
    
    for ip,mask,_ in ip_data:
        up.write('route add %s mask %s %s metric %d\r\n'%(ip,mask,"%gw%",metric))
        down.write('route delete %s\r\n'%(ip))
    
    return {'vpnup.bat':up.getvalue(),'vpndown.bat':down.getvalue()}


def generate_android(ip_data,metric=25):   
    upscript_header=textwrap.dedent("""\
    #!/bin/sh
    alias nestat='/system/xbin/busybox netstat'
    alias grep='/system/xbin/busybox grep'
    alias awk='/system/xbin/busybox awk'
    alias route='/system/xbin/busybox route'
    
    OLDGW=`netstat -rn | grep ^0\.0\.0\.0 | awk '{print $2}'`
    
    """)
    
    downscript_header=textwrap.dedent("""\
    #!/bin/sh
    alias route='/system/xbin/busybox route'
    
    """)
    
    up=StringIO.StringIO()
    down=StringIO.StringIO()
    
    up.write(upscript_header)
    up.write('\n')
    down.write(downscript_header)
    down.write('\n')
    
    for ip,mask,_ in ip_data:
        up.write('route add -net %s netmask %s gw $OLDGW\n'%(ip,mask))
        down.write('route del -net %s netmask %s\n'%(ip,mask))
    
    return {'vpnup.sh':up.getvalue(),'vpndown.sh':down.getvalue()}

def zipit(data):
    zfile=StringIO.StringIO()
    z=zipfile.ZipFile(zfile,'w',zipfile.ZIP_DEFLATED)
    for fn,d in data.iteritems():
            z.writestr(fn,d)
    z.close()
    return zfile.getvalue()
    
if __name__ == '__main__':
    generate_all()
########NEW FILE########
