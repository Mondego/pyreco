__FILENAME__ = byzantium_configd
#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# Copyright (C) 2013 Project Byzantium
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or any later version.

# byzantium_configd.py - A (relatively) simple daemon that automatically
# configures wireless interfaces on a Byzantium node.  No user interaction is
# required.  Much of this code was taken from the control panel, it's just
# been assembled into a more compact form.  The default network settings are
# the same ones used by Commotion Wireless, so this means that our respective
# projects are now seamlessly interoperable.  For the record, we tested this
# in Red Hook in November of 2012 and it works.

# This utility is less of a hack, but it's far from perfect.

# By: The Doctor [412/724/301/703] [ZS|Media] <drwho at virtadpt dot net>
# License: GPLv3

# Imports
import os
import os.path
import random
import re
import subprocess
import sys
import time

# Layer 1 and 2 defaults.  Note that ESSIDs are for logical separation of
# wireless networks and not signal separation.  It's the BSSIDs that count.
channel = '5'
frequency = '2.432'
bssid = '02:CA:FF:EE:BA:BE'
essid = 'Byzantium'

# Layer 3 defaults.
mesh_netmask = '255.255.0.0'
client_netmask = '255.255.255.0'
commotion_network = '5.0.0.0'
commotion_netmask = '255.0.0.0'

# Paths to generated configuration files.
hostsmesh = '/etc/hosts.mesh'
dnsmasq_include_file = '/etc/dnsmasq.conf.include'

# Global variables.
wireless = []
mesh_ip = ''
client_ip = ''

# Initialize the randomizer.
random.seed()

# Enumerate all network interfaces and pick out only the wireless ones.
# Ignore the rest.
interfaces = os.listdir('/sys/class/net')

# Remove the loopback interface because that's our failure case.
if 'lo' in interfaces:
    interfaces.remove('lo')
if not interfaces:
    print "ERROR: No wireless interfaces found.  Terminating."
    sys.exit(1)

# For each network interface's pseudofile in /sys, test to see if a
# subdirectory 'wireless/' exists.  Use this to sort the list of
# interfaces into wired and wireless.
for i in interfaces:
    if os.path.isdir("/sys/class/net/%s/wireless" % i):
        wireless.append(i)

# Find unused IP addresses to configure this node's interfaces with.
if len(wireless):
    interface = wireless[0]
    print "Attempting to configure interface %s." % interface

    # Turn down the interface.
    command = ['/sbin/ifconfig', interface, 'down']
    subprocess.Popen(command)
    time.sleep(5)

    # Set wireless parameters on the interface.  Do this by going into a loop
    # that tests the configuration for correctness and starts the procedure
    # over if it didn't take the first time.
    # We wait a few seconds between iwconfig operations because some wireless
    # chipsets are pokey (coughAtheroscough) and silently reset themselves if
    # you try to configure them too rapidly, meaning that they drop out of
    # ad-hoc mode.
    success = False
    for try_num in range(3):
        print "Attempting to configure the wireless interface. Try:", try_num
        # Configure the wireless chipset.
        command = ['/sbin/iwconfig', interface, 'mode', 'ad-hoc']
        subprocess.Popen(command)
        time.sleep(5)
        command = ['/sbin/iwconfig', interface, 'essid', essid]
        subprocess.Popen(command)
        time.sleep(5)
        command = ['/sbin/iwconfig', interface, 'ap', bssid]
        subprocess.Popen(command)
        time.sleep(5)
        command = ['/sbin/iwconfig', interface, 'channel', channel]
        subprocess.Popen(command)
        time.sleep(5)

        # Capture the interface's current settings.
        command = ['/sbin/iwconfig', interface]
        configuration = ''
        output = subprocess.Popen(command, stdout=subprocess.PIPE).stdout
        configuration = output.readlines()

        # Test the interface's current configuration.  Go back to the top of
        # the configuration loop and try again if it's not what we expect.
        Mode = False
        Essid = False
        Bssid = False
        Frequency = False
        for line in configuration:
            # Ad-hoc mode?
            match = re.search('Mode:([\w-]+)', line)
            if match and match.group(1) == 'Ad-Hoc':
                print "Mode is correct."
                Mode = True

            # Correct ESSID?
            match = re.search('ESSID:"([\w]+)"', line)
            if match and match.group(1) == essid:
                print "ESSID is correct."
                Essid = True

            # Correct BSSID?
            match = re.search('Cell: (([\dA-F][\dA-F]:){5}[\dA-F][\dA-F])', line)
            if match and match.group(1) == bssid:
                print "BSSID is correct."
                Bssid = True

            # Correct frequency (because iwconfig doesn't report channels)?
            match = re.search('Frequency:([\d.]+)', line)
            if match and match.group(1) == frequency:
                print "Channel is correct."
                Frequency = True

        # "Victory is mine!"
        #     --Stewie, _Family Guy_
        if Mode and Essid and Bssid and Frequency:
            success = True
            break
        else:
            print "Failed to setup the interface properly. Retrying..."
    if not success:
        sys.exit(1)

    # Turn up the interface.
    command = ['/sbin/ifconfig', interface, 'up']
    subprocess.Popen(command)
    time.sleep(5)

    # Start with the mesh interface.
    ip_in_use = 1
    while ip_in_use:
        # Generate a pseudorandom IP address for the mesh interface.
        addr = '192.168.'
        addr = addr + str(random.randint(0, 255)) + '.'
        addr = addr + str(random.randint(1, 254))

        # Use arping to see if anyone's claimed it.
        arping = ['/sbin/arping', '-c 5', '-D', '-f', '-q', '-I', interface,
                  addr]
        ip_in_use = subprocess.call(arping)

        # If the IP isn't in use, ip_in_use == 0 so we bounce out of the loop.
        # We lose nothing by saving the address anyway.
        mesh_ip = addr
    print "Mesh interface address: %s" % mesh_ip

    # Now configure the client interface.
    ip_in_use = 1
    while ip_in_use:
        # Generate a pseudorandom IP address for the client interface.
        addr = '10.'
        addr = addr + str(random.randint(0, 254)) + '.'
        addr = addr + str(random.randint(0, 254)) + '.1'

        # Use arping to see if anyone's claimed it.
        arping = ['/sbin/arping', '-c 5', '-D', '-f', '-q', '-I', interface,
                  addr]
        ip_in_use = subprocess.call(arping)

        # If the IP isn't in use, ip_in_use==0 so we bounce out of the loop.
        # We lose nothing by saving the address anyway.
        client_ip = addr
    print "Client interface address: %s" % client_ip

    # Configure the mesh interface.
    command = ['/sbin/ifconfig', interface, mesh_ip, 'netmask', mesh_netmask,
               'up']
    subprocess.Popen(command)
    time.sleep(5)
    print "Mesh interface %s configured." % interface

    # Configure the client interface.
    client_interface = interface + ':1'
    command = ['/sbin/ifconfig', client_interface, client_ip, 'up']
    subprocess.Popen(command)
    time.sleep(5)
    print "Client interface %s configured." % client_interface

    # Add a route for any Commotion nodes nearby.
    print "Adding Commotion route..."
    command = ['/sbin/route', 'add', '-net', commotion_network, 'netmask',
               commotion_netmask, 'dev', interface]
    commotion_route_return = subprocess.Popen(command)

    # Start the captive portal daemon on that interface.
    captive_portal_daemon = ['/usr/local/sbin/captive_portal.py', '-i',
                             interface, '-a', client_ip]
    captive_portal_return = 0
    captive_portal_return = subprocess.Popen(captive_portal_daemon)
    time.sleep(5)
    print "Started captive portal daemon."
else:
    # There is no wireless interface.  Don't even bother continuing.
    print "ERROR: I wasn't able to find a wireless interface to configure.  ABENDing."
    sys.exit(1)

# Build a string which can be used as a template for an /etc/hosts style file.
(octet_one, octet_two, octet_three, _) = client_ip.split('.')
prefix = octet_one + '.' + octet_two + '.' + octet_three + '.'

# Make an /etc/hosts.mesh file, which will be used by dnsmasq to resolve its
# mesh clients.
hosts = open(hostsmesh, "w")
line = prefix + str('1') + '\tbyzantium.mesh\n'
hosts.write(line)
for i in range(2, 254):
    line = prefix + str(i) + '\tclient-' + prefix + str(i) + '.byzantium.mesh\n'
    hosts.write(line)
hosts.close()

# Generate an /etc/dnsmasq.conf.include file.
(octet_one, octet_two, octet_three, _) = client_ip.split('.')
prefix = octet_one + '.' + octet_two + '.' + octet_three + '.'
start = prefix + str('2')
end = prefix + str('254')
dhcp_range = 'dhcp-range=' + start + ',' + end + ',5m\n'
include_file = open(dnsmasq_include_file, 'w')
include_file.write(dhcp_range)
include_file.close()

# Start dnsmasq.
print "Starting dnsmasq."
subprocess.Popen(['/etc/rc.d/rc.dnsmasq', 'restart'])

# Start olsrd.
olsrd_command = ['/usr/sbin/olsrd', '-i']

#for i in wireless:

if len(wireless):
    olsrd_command.append(wireless[0])

print "Starting routing daemon."
subprocess.Popen(olsrd_command)
time.sleep(5)

# Fin.
sys.exit(0)

########NEW FILE########
__FILENAME__ = captive_portal
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :
# Project Byzantium: http://wiki.hacdc.org/index.php/Byzantium
__license__ = 'GPL v3'

# captive_portal.py
# This application implements a little web server that mesh clients will be
# redirected to if they haven't been added to the whitelist in IP tables.  When
# the user clicks a button a callback will be triggered that runs iptables and
# adds the IP and MAC addresses to the whitelist so that it won't run into the
# captive portal anymore.

# The fiddly configuration-type stuff is passed on the command line to avoid
# having to manage a config file with the control panel.

# Codes passed to exit().  They'll be of use to the control panel later.
#    0: Normal termination.
#    1: Insufficient CLI args.
#    2: Bad CLI args.
#    3: Bad IP tables commands during initialization.
#    4: Bad parameters passed to IP tables during initialization.
#    5: Daemon already running on this network interface.

# v0.1 - Initial release.
# v0.2 - Added a --test option that doesn't actually do anything to the system
#        the daemon's running on, it just prints what the command would be.
#        Makes debugging easier and helps with testing. (Github ticket #87)
#      - Added a 404 error handler that redirects the client to / on the same
#        port that the captive portal daemon is listening on. (Github
#        ticket #85)
#      - Figured out how to make CherryPy respond to the usual signals (i.e.,
#        SIGTERM) and call a cleanup function to take care of things before
#        terminating.  It took a couple of hours of hacking but I finally found
#        something that worked.
# v0.3 - Added code to implement an Apple iOS captive portal detector.
#      - Added code that starts the idle client reaper daemon that Haxwithaxe
#        wrote.
#      - Added a second listener for HTTPS connections.

# TODO:

# Modules.
import cherrypy
from cherrypy.process.plugins import PIDFile
from mako.lookup import TemplateLookup

import argparse
import fcntl
import logging
import os
import socket
import struct
import subprocess

# Need this for the 404 method.
def get_ip_address(interface):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(sock.fileno(), 0x8915,
                            struct.pack('256s', interface[:15]))[20:24])

# The CaptivePortalDetector class implements a fix for an undocumented bit of
# fail in Apple iOS.  iProducts attempt to access a particular file hidden in
# the Apple Computer website.  If it can't find it, iOS forces the user to try
# to log into the local captive portal (even if it doesn't support that
# functionality).  This breaks things for users of iOS, unless we fix it in
# the captive portal.
class CaptivePortalDetector(object):
    # index(): Pretends to be /library/test and /library/test/index.html.
    def index(self):
        return("You shouldn't be seeing this, either.")
    index.exposed = True

    # success_html(): Pretends to be http://apple.com/library/test/success.html.
    def success_html(self):
        logging.debug("iOS device detected.")
        success = '''
                <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">
                <HTML>
                <HEAD>
                        <TITLE>Success</TITLE>
                </HEAD>
                <BODY>
                        Success
                </BODY>
                </HTML>
                '''
        return success
    success_html.exposed = True

# Dummy class that has to exist to create a durectory URI hierarchy.
class Library(object):

    logging.debug("Instantiating Library() dummy object.")
    test = CaptivePortalDetector()

    # index(): Pretends to be /library and /library/index.html.
    def index(self):
        return("You shouldn't be seeing this.")
    index.exposed = True


# The CaptivePortal class implements the actual captive portal stuff - the
# HTML front-end and the IP tables interface.
class CaptivePortal(object):

    def __init__(self, args):
        self.args = args

        logging.debug("Mounting Library() from CaptivePortal().")
        self.library = Library()

    # index(): Pretends to be / and /index.html.
    def index(self):
        # Identify the primary language the client's web browser supports.
        try:
            clientlang = cherrypy.request.headers['Accept-Language']
            clientlang = clientlang.split(',')[0].lower()
        except:
            logging.debug("Client language not found.  Defaulting to en-us.")
            clientlang = 'en-us'
        logging.debug("Current browser language: %s", clientlang)

        # Piece together the filename of the /index.html file to return based
        # on the primary language.
        indexhtml = "index.html." + clientlang
        templatelookup = build_templatelookup(self.args)
        try:
            page = templatelookup.get_template(indexhtml)
        except:
            page = templatelookup.get_template('index.html.en-us')
            logging.debug("Unable to find HTML template for language %s!", clientlang)
            logging.debug("\tDefaulting to /srv/captiveportal/index.html.en-us.")
        return page.render()
    index.exposed = True

    # whitelist(): Takes the form input from /index.html.*, adds the IP address
    # of the client to IP tables, and then flips the browser to the node's
    # frontpage.  Takes one argument, a value for the variable 'accepted'.
    # Returns an HTML page with an HTTP refresh as its sole content to the
    # client.
    def whitelist(self, accepted=None):
        # Extract the client's IP address from the client headers.
        clientip = cherrypy.request.headers['Remote-Addr']
        logging.debug("Client's IP address: %s", clientip)

        # Set up the command string to add the client to the IP tables ruleset.
        addclient = ['/usr/local/sbin/captive-portal.sh', 'add', clientip]
        if self.args.test:
            logging.debug("Command that would be executed:\n%s", addclient)
        else:
            subprocess.call(addclient)

        # Assemble some HTML to redirect the client to the node's frontpage.
        redirect = """
                   <html>
                   <head>
                   <!-- Disable browser caching -->
                   <meta http-equiv="cache-control" content="max-age=0" />
                   <meta http-equiv="cache-control" content="no-cache" />
                   <meta http-equiv="expires" content="0" />
                   <meta http-equiv="expires" content="Tue, 01 Jan 1980 1:00:00 GMT" />
                   <meta http-equiv="pragma" content="no-cache" />

                   <meta http-equiv="refresh" content="0; url=http://""" + self.args.address + """/index.html" />
                   </head>
                   <body>
                   </body>
                   </html>"""

        logging.debug("Generated HTML refresh is:")
        logging.debug(redirect)

        # Fire the redirect at the client.
        return redirect
    whitelist.exposed = True

    # error_page_404(): Registered with CherryPy as the default handler for
    # HTTP 404 errors (file or resource not found).  Takes four arguments
    # (required by CherryPy), returns some HTML generated at runtime that
    # redirects the client to http://<IP address>/, where it'll be caught by
    # CaptivePortal.index().  I wish there was an easier way to do this (like
    # calling self.index() directly) but the stable's fresh out of ponies.
    # We don't use any of the arguments passed to this method so I reference
    # them in debug mode.
    def error_page_404(status, message, traceback, version):
        # Extract the client's IP address from the client headers.
        clientip = cherrypy.request.headers['Remote-Addr']
        logging.debug("Client's IP address: %s", clientip)
        logging.debug("Value of status is: %s", status)
        logging.debug("Value of message is: %s", message)
        logging.debug("Value of traceback is: %s", traceback)
        logging.debug("Value of version is: %s", version)

        # Assemble some HTML to redirect the client to the captive portal's
        # /index.html-* page.
        #
        # We are using wlan0:1 here for the address - this may or may not be
        # right, but since we can't get at self.args.address it's the best we
        # can do.
        redirect = """
<html>
  <head>
    <!-- Disable browser caching -->
    <meta http-equiv="cache-control" content="max-age=0" />
    <meta http-equiv="cache-control" content="no-cache" />
    <meta http-equiv="expires" content="0" />
    <meta http-equiv="expires" content="Tue, 01 Jan 1980 1:00:00 GMT" />
    <meta http-equiv="pragma" content="no-cache" />

    <meta http-equiv="refresh" content="0; url=http://""" + get_ip_address("wlan0:1") + """/" />
  </head>
  <body></body>
</html>"""

        logging.debug("Generated HTML refresh is:")
        logging.debug(redirect)
        logging.debug("Redirecting client to /.")

        # Fire the redirect at the client.
        return redirect
    cherrypy.config.update({'error_page.404':error_page_404})


def parse_args():
    parser = argparse.ArgumentParser(conflict_handler='resolve', description="This daemon implements the captive "
                                     "portal functionality of Byzantium Linux. pecifically, it acts as the front end "
                                     "to IP tables and automates the addition of mesh clients to the whitelist.")
    parser.add_argument("-a", "--address", action="store",
                        help="The IP address of the interface the daemon listens on.")
    parser.add_argument("--appconfig", action="store", default="/etc/captiveportal/captiveportal.conf")
    parser.add_argument("--cachedir", action="store", default="/tmp/portalcache")
    parser.add_argument("-c", "--certificate", action="store", default="/etc/httpd/server.crt",
                        help="Path to an SSL certificate. (Defaults to /etc/httpd/server.crt)")
    parser.add_argument("--configdir", action="store", default="/etc/captiveportal")
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Enable debugging mode.")
    parser.add_argument("--filedir", action="store", default="/srv/captiveportal")
    parser.add_argument("-i", "--interface", action="store", required=True,
                        help="The name of the interface the daemon listens on.")
    parser.add_argument("-k", "--key", action="store", default="/etc/httpd/server.key",
                        help="Path to an SSL private key file. (Defaults to /etc/httpd/server.key)")
    parser.add_argument("--pidfile", action="store")
    parser.add_argument("-p", "--port", action="store", default=31337, type=int,
                        help="Port to listen on.  Defaults to 31337/TCP.")
    parser.add_argument("-s", "--sslport", action="store", default=31338, type=int,
                        help="Port to listen for HTTPS connections on. (Defaults to HTTP port +1.")
    parser.add_argument("-t", "--test", action="store_true", default=False,
                        help="Disables actually doing anything, it just prints what would be done.  Used for testing "
                        "commands without altering the test system.")
    return parser.parse_args()


def check_args(args):
    if not args.port == 31337 and args.sslport == 31338:
        args.sslport = args.port + 1
        logging.debug("Setting ssl port to %d/TCP", args.sslport)

    if not os.path.exists(args.certificate):
        if not args.test:
            logging.error("Specified SSL cert not found: %s", args.certificate)
            exit(2)
    else:
        logging.debug("Using SSL cert at: %s", args.certificate)

    if not os.path.exists(args.key):
        if not args.test:
            logging.error("Specified SSL private key not found: %s", args.key)
            exit(2)
    else:
        logging.debug("Using SSL private key at: %s", args.key)

    if not args.configdir == "/etc/captiveportal" and args.appconfig == "/etc/captiveportal/captiveportal.conf":
        args.appconfig = "%s/captiveportal.conf" % args.configdir

    if args.debug:
        print "Captive portal debugging mode is on."

    if args.test:
        print "Captive portal functional testing mode is on."

    return args


def create_pidfile(args):
    # Create the filename for this instance's PID file.
    if not args.pidfile:
        if args.test:
            args.pidfile = '/tmp/captive_portal.'
        else:
            args.pidfile = '/var/run/captive_portal.'
    full_pidfile = args.pidfile + args.interface
    logging.debug("Name of PID file is: %s", full_pidfile)

    # If a PID file already exists for this network interface, ABEND.
    if os.path.exists(full_pidfile):
        logging.error("A pidfile already exists for network interface %s.", full_pidfile)
        logging.error("Is a daemon already running on this interface?")
        exit(5)

    # Write the PID file of this instance to the PID file.
    logging.debug("Creating pidfile for network interface %s.", str(args.interface))
    logging.debug("PID of process is %s.", str(os.getpid()))
    pid = PIDFile(cherrypy.engine, full_pidfile)
    pid.subscribe()


def update_cherrypy_config(port):
    # Configure a few things about the web server so we don't have to fuss
    # with an extra config file, namely, the port and IP address to listen on.
    cherrypy.config.update({'server.socket_host':'0.0.0.0', })
    cherrypy.config.update({'server.socket_port':port, })


def start_ssl_listener(args):
    # Set up an SSL listener running in parallel.
    ssl_listener = cherrypy._cpserver.Server()
    ssl_listener.socket_host = '0.0.0.0'
    ssl_listener.socket_port = args.sslport
    ssl_listener.ssl_certificate = args.certificate
    ssl_listener.ssl_private_key = args.key
    ssl_listener.subscribe()


def build_templatelookup(args):
    # Set up the location the templates will be served out of.
    return TemplateLookup(directories=[args.filedir], module_directory=args.cachedir, collection_size=100)


def setup_url_tree(args):
    # Attach the captive portal object to the URL tree.
    root = CaptivePortal(args)

    # Mount the object for the root of the URL tree, which happens to be the
    # system status page.  Use the application config file to set it up.
    logging.debug("Mounting web app in %s to /.", args.appconfig)
    cherrypy.tree.mount(root, "/", args.appconfig)


def setup_iptables(args):
    # Initialize the IP tables ruleset for the node.
    initialize_iptables = ['/usr/local/sbin/captive-portal.sh', 'initialize',
                           args.address, args.interface]
    iptables = 0
    if args.test:
        logging.debug("Command that would be executed:\n%s", ' '.join(initialize_iptables))
    else:
        iptables = subprocess.call(initialize_iptables)
    return iptables


def setup_reaper(test):
    # Start up the idle client reaper daemon.
    idle_client_reaper = ['/usr/local/sbin/mop_up_dead_clients.py', '-m', '600',
                          '-i', '60']
    reaper = 0
    if test:
        logging.debug("Idle client monitor command that would be executed:\n%s", ' '.join(idle_client_reaper))
    else:
        logging.debug("Starting mop_up_dead_clients.py.")
        reaper = subprocess.Popen(idle_client_reaper)
    if not reaper:
        logging.error("mop_up_dead_clients.py did not start.")


def setup_hijacker(args):
    # Start the fake DNS server that hijacks every resolution request with the
    # IP address of the client interface.
    dns_hijacker = ['/usr/local/sbin/fake_dns.py', args.address]
    hijacker = 0
    if args.test:
        logging.debug("Command that would start the fake DNS server:\n%s", ' '.join(dns_hijacker))
    else:
        logging.debug("Starting fake_dns.py.")
        hijacker = subprocess.Popen(dns_hijacker)
    if not hijacker:
        logging.error("fake_dns.py did not start.")


def check_ip_tables(iptables, args):
    # Now do some error checking in case IP tables went pear-shaped.  This appears
    # oddly specific, but /usr/sbin/iptables treats these two kinds of errors
    # differently and that makes a difference during troubleshooting.
    if iptables == 1:
        logging.error("Unknown IP tables error during firewall initialization.")
        logging.error("Packet filters NOT configured.  Examine the rules in captive-portal.sh.")
        exit(3)

    if iptables == 2:
        logging.error("Invalid or incorrect options passed to iptables in captive-portal.sh")
        logging.error("Packet filters NOT configured.  Examine the rules in captive-portal.sh.")
        logging.error("Parameters passed to captive-portal.sh: initialize, %s, %s" % args.address, args.interface)
        exit(4)


def start_web_server():
    # Start the web server.
    logging.debug("Starting web server.")
    cherrypy.engine.start()
    cherrypy.engine.block()
    # [Insert opening anthem from Blaster Master here.]
    # Fin.


def main():
    args = check_args(parse_args())
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)
    create_pidfile(args)
    update_cherrypy_config(args.port)
    start_ssl_listener(args)
    setup_url_tree(args)
    iptables = setup_iptables(args)
    setup_reaper(args.test)
    setup_hijacker(args)
    check_ip_tables(iptables, args)
    start_web_server()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = captive_portal_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :
# Project Byzantium: http://wiki.hacdc.org/index.php/Byzantium
# Copyright (C) 2013 Project Byzantium
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

# captive_portal_test.py

import flexmock  # http://has207.github.com/flexmock
import unittest
import captive_portal


class CaptivePortalDetectorTest(unittest.TestCase):
    
    def setUp(self):
        self.detector = captive_portal.CaptivePortalDetector()

    def test_index(self):
        self.assertEqual("You shouldn't be seeing this, either.", self.detector.index())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = fake_dns
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# http://minidns.googlecode.com/hg/minidns
# Found by: Haxwithaxe

# Import Python modules.
import sys
import socket
import fcntl
import struct

# DNSQuery class from http://code.activestate.com/recipes/491264-mini-fake-dns-server/
class DNSQuery:
  # 'data' is the actual DNS resolution request from the client.
  def __init__(self, data):
    self.data=data
    self.domain=''

    tipo = (ord(data[2]) >> 3) & 15   # Opcode bits

    # Determine if the client is making a standard resolution request.
    # Otherwise, don't do anything because it's not a resolution request.
    if tipo == 0:
      ini=12
      lon=ord(data[ini])
      while lon != 0:
        self.domain+=data[ini+1:ini+lon+1]+'.'
        ini+=lon+1
        lon=ord(data[ini])

  # Build a reply packet for the client.
  def respuesta(self, ip):
    packet=''
    if self.domain:
      packet+=self.data[:2] + "\x81\x80"

      # Question and answer counts.
      packet+=self.data[4:6] + self.data[4:6] + '\x00\x00\x00\x00'

      # A copy of the original resolution query from the client.
      packet+=self.data[12:]

      # Pointer to the domain name.
      packet+='\xc0\x0c'

      # Response type, TTL of the reply, and length of data in reply.
      packet+='\x00\x01'  # TYPE: A record
      packet+='\x00\x01'  # CLASS: IN (Internet)
      packet+='\x00\x00\x00\x00'  # TTL: 0 sec
      packet+='\x00\x04'  # Length of data: 4 bytes

      # The IP address of the server the DNS is running on.
      packet+=str.join('',map(lambda x: chr(int(x)), ip.split('.')))
    return packet

# get_ip_address code from http://code.activestate.com/recipes/439094-get-the-ip-address-associated-with-a-network-inter/
# Method that acquires the IP address of a network interface on the system
# this daemon is running on.  It will only be invoked if an IP address is not
# passed on the command line to the daemon.
def get_ip_address(ifname):
  # > LOOK
  # You are in a maze of twisty passages, all alike.
  # > GO WEST
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  try:
    # It is dark here.  You are likely to be eaten by a grue.
    # > _
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])
  except:
    return None

# Display usage information to the user.
def usage():
  print "Usage:"
  print "\t# minidns [ip | interface]\n"
  print "Description:"
  print "\tMiniDNS will respond to all DNS queries with a single IPv4 address."
  print "\tYou may specify the IP address to be returned as the first argument"
  print "\ton the command line:\n"
  print "\t\t# minidns 1.2.3.4\n"
  print "\tAlternatively, you may specify an interface name and MiniDNS will"
  print "\tuse the IP address currently assigned to that interface:\n"
  print "\t\t# minidns eth0\n"
  print "\tIf no interface or IP address is specified, the IP address of eth0"
  print "\twill be used."
  sys.exit(1)

# Core code.
if __name__ == '__main__':
  # Set defaults for basic operation.  Hopefully these will be overridden on
  # the command line.
  ip = None
  iface = 'eth0'

  # Parse the argument vector.
  if len(sys.argv) == 2:
    if sys.argv[-1] == '-h' or sys.argv[-1] == '--help':
      usage()
    else:
      if len(sys.argv[-1].split('.')) == 4:
        ip=sys.argv[-1]
      else:
        iface = sys.argv[-1]

  # In the event that an interface name was given but not an IP address, get
  # the IP address.
  if ip is None:
    ip = get_ip_address(iface)

  # If the IP address can't be gotten somehow, carp.
  if ip is None:
    print "ERROR: Invalid IP address or interface name specified!"
    usage()

  # Open a socket to listen on.  Haxwithaxe set this to port 31339/udp because
  # this is the DNS hijacker bit of the captive portal.  Only clients that
  # aren't in the whitelist will see it.
  try:
    udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udps.bind(('',31339))
  except Exception, e:
    print "Failed to create socket on UDP port 31339:", e
    sys.exit(1)

  # Print something for anyone watching a TTY.  All 'A' records this daemon
  # serves up have a TTL of 15 seconds.
  print 'miniDNS :: * 15 IN A %s\n' % ip

  # The do-stuff loop.
  try:
    while 1:
      # Receive a DNS resolution request from a client.
      data, addr = udps.recvfrom(1024)

      # Generate the response.
      p=DNSQuery(data)

      # Send the response to the client.
      udps.sendto(p.respuesta(ip), addr)
      print 'Request: %s -> %s' % (p.domain, ip)
  except KeyboardInterrupt:
    print '\nBye!'
    udps.close()

# Fin.

########NEW FILE########
__FILENAME__ = mop_up_dead_clients
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :
# mop_up_dead_clients.py - Daemon that pairs with the captive portal to remove
#    IP tables rules for idle clients so they don't overflow the kernel.
# By: Haxwithaxe
# Copyright (C) 2013 Project Byzantium
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.


# Modules
import sys
import os
import time
import subprocess

# Global variables.
# Defaults are set here but they can be overridden on the command line.
CACHEFILE = '/tmp/captive_portal-mopup.cache'
STASHTO = 'ram' # options are 'ram','disk'
MAXIDLESEC = 18000 # max idle time in seconds (18000s == 5hr)
CHECKEVERY = 1800.0 # check every CHECKEVERY seconds for idle clients (1800s == 30min)
IPTABLESCMD = ['/usr/sbin/iptables','-t','mangle','-L','internet','-n','-v']
USAGE = '''[(-c|--cache) <cache file>]\n\t[(-s|--stashto) <disk|ram>]\n\t[(-m|--maxidle) <time before idle client expires in seconds>]\n\t[(-i|--checkinterval) <time between each check for idle clients in\n\t\tseconds>]'''

# List of clients the daemon knows about.
clients={}

# _stash(): Writes the cache of known clients' information (documented below)
#           to a JSON file on disk.  Takes one argument, a dict containing a
#           client's information.  Returns nothing.  Only does something if the
#           stashtype is 'disk'.
'''@param	info	dict of mac:{'ip':string,'mac':string,'metric':int,'lastChange':int} (lastChange in unix timestamp)'''
def _stash(info):
    if STASHTO == 'disk':
        fobj = open(CACHEFILE,'w')
        fobj.write(json.dumps(info))
        fobj.close()

# _get_stash(): Tries to load the database of the node's clients from disk if
#               it exists.  Returns a dict containing the list of clients
#               associated with the node.
'''@return		False if empty or not found, else dict of mac:{'ip':string,'mac':string,'metric':int,'lastChange':int} (lastChange in unix timestamp)'''
def _get_stash():
    try:
        fobj = open(CACHEFILE,'r')
        fstr = fobj.read()
        fobj.close()
        if fstr:
            try:
                return json.loads()
            except ValueError as ve:
                print('Reading Cache File: Cache File Likely Empty '+str(ve))
    except IOError as ioe:
        print('Reading Cache File: Cache File Not Found '+str(ioe))
    return False

# _die(): Top-level error handler for the daemon.  Prints the usage info and
#         terminates.
def _die():
    print "USAGE: %s" % sys.argv[0], USAGE
    sys.exit(1)

# _scrub_dead(): Calls captive-portal.sh to remove an IP tables rule for a mesh
#                client that no longer exists.  Takes the MAC address of the
#                client as an arg, returns nothing.
'''@param	mac	string representing the mac address of a client to be removed'''
def _scrub_dead(mac):
    del clients[mac]
    subprocess.call(['/usr/local/sbin/captive-portal.sh', 'remove', mac])

# read_metrics(): Updates the client cache with the number of packets logged
#                 per client.  Takes no args.  Returns a dict containing the
#                 MAC and the current packet count.
'''@return	list of dict of {'ip':string,'mac':string,'metric':int}'''
def read_metrics():
    metrics = []
    packetcounts = get_packetcounts()
    for mac, pc in packetcounts.items():
        metrics += [{'mac':mac, 'metric':pc}]
    return metrics

# get_packetcounts(): Calls /usr/sbin/iptables to display the list of rules
#                     that correspond to mesh clients, in particular the number
#                     of packets sent or received by the client at time t.
#                     Returns a dict consisting of <MAC address>:<packet count>
#                     pairs.
def get_packetcounts():
    # Run iptables to dump a list of clients currently connected to this node.
    packetcounts = {}
    p = subprocess.Popen(IPTABLESCMD)
    p.wait()
    stdout, stderr = p.communicate()

    # If nothing was returned from iptables, return an empty list.
    if not stdout:
        return packetcounts

    # Roll through the captured output from iptables to pick out the packet
    # counts on a per client basis.
    for line in stdout.split('\n')[2:]:
        # If the line's empty, just exit this method so it doesn't error out
        # later.
        if not line:
            break
        larr = line.strip().split()

        # If the string's contents after being cleaned up are null, skip this
        # iteration.
        if not larr:
            continue

        # If the line contains a MAC address take it apart to extract the
        # MAC address and the packet count associated with it.
        if 'MAC' in larr:
            pcount = int(larr[0].strip() or 0)
            if len(larr) >= larr.index('MAC')+1:
                mac = larr[larr.index('MAC')+1]
                packetcounts[mac] = pcount

    # Return the hash to the calling method.
    return packetcounts

# bring_out_your_dead(): Method that carries out the task of checking to see
#                        which clients have been active and which haven't.
#                        This method is also responsible for calling the
#                        methods that remove a client's IP tables rule and
#                        maintain the internal database of clients.
def bring_out_your_dead(metrics):
    global clients

    # If the clients dict isn't populated, go through the dict of clients and
    # associate the current time (in time_t format) with their packet count.
    if not clients:
        for c in metrics:
            c['lastChanged'] = int(time.time())
            clients[c['mac']] = c
    else:
        for c in metrics:
            # Test every client we know about to see if it's been active or
            # not.
            if c['mac'] in clients:
                # If the number of packets recieved has changed, then update
                # its last known-alive time.
                if clients[c['mac']]['metric'] != c['metric']:
                    clients[c['mac']]['lastChanged'] = int(time.time())

                # If the client hasn't been alive for longer than MAXIDLESEC,
                # remove its rule from IP tables.  It'll have to reassociate.
                elif (int(time.time()) - clients[c['mac']]['lastChanged']) > MAXIDLESEC:
                    _scrub_dead(c['mac'])
            else:
                # Else, add the client.
                c['lastChanged'] = int(time.time())
                clients[c['mac']] = c
    # Update the cache of clients.
    _stash(clients)
    print(metrics,clients)

# mop_up(): Wrapper method that calls all of the methods that do the heavy
#           lifting in sequence.  Supposed to run when this code is imported
#           into other code as a module.  Takes no args.  Returns nothing.
'''call this if this is used as a module'''
def mop_up():
    metrics = read_metrics()
    print(metrics)
    bring_out_your_dead(metrics)

# If running this code as a separate process, main() gets called.
'''this is run if this is used as a script'''
def main(args):
    if args:
        global CACHEFILE
        global STASHTO
        global MAXIDLESEC
        global CHECKEVERY
        try:
            if '-c' in args:
                CACHEFILE = args[args.index('-c')+1]
            if '--cache' in args:
                CACHEFILE = args[args.index('--cache')+1]
            if '-s' in args:
                STASHTO = args[args.index('-s')+1]
            if '--stashto' in args:
                STASHTO = args[args.index('--stashto')+1]
            if '-m' in args:
                MAXIDLESEC = args[args.index('-m')+1]
            if '--maxidle' in args:
                MAXIDLESEC = args[args.index('--maxidle')+1]
            if '-i' in args:
                CHECKEVERY = float(args[args.index('-i')+1])
            if '--checkinterval' in args:
                CHECKEVERY = float(args[args.index('--checkinterval')+1])
            if '--help' in args:
                print "USAGE: %s" % sys.argv[0], USAGE
                sys.exit(1)
        except IndexError as ie:
            _die(USAGE % args[0])

        # Go to sleep for a period of time equal to three delay intervals to
        # give the node a chance to have some clients associate with it.
        # Otherwise this daemon will immediately try to build a list of
        # associated clients, not find any, and crash.
        time.sleep(CHECKEVERY * 3)

        # Go into a loop of mopping up and sleeping endlessly.
        while True:
            mop_up()
            time.sleep(CHECKEVERY)

if __name__ == '__main__':
    main(sys.argv)

# Fin.

########NEW FILE########
__FILENAME__ = avahiutil
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :
__license__ = 'GPL v3'
import os.path
import _utils

services_store_dir = _utils.Config().services_store_dir
services_live_dir = _utils.Config().services_live_dir


def _mksname(name):
    return name.lower().replace(' ','_')


def add(name,port,host = '',domain = '',stype = '_http._tcp',subtype = None,protocol = None,text = []):
    ''' Adds service file to storage dir
        @param  name    service name
        @param  port    integer port number. (udp: 0-65535, tcp: 1-65535)
        @param  host    hostname. multicast or unicast DNS findable host name.
        @param  domain  FQDN eg: myname.local or google.com
        @param  stype   see http://www.dns-sd.org/ServiceTypes.html (default: '_http._ftp')
        @param  subtype service subtype
        @param  protocol    [any|ipv4|ipv6] (default: any; as per spec in "man avahi.service")
        @param  text    list/tuple of <text-record/> values
        USAGE: add('service name',9007) all other parameters are optional
    '''
    ## notes for haxwithaxe
    # See http://www.dns-sd.org/ServiceTypes.html
    # name: <name>1
    # stype: <service>+
    #   protocol: <service ?protocol="ipv4|ipv6|any">
    #   domain: <domain-name>?
    #   host: <host-name>? (explicit FQDN eg: me.local)
    #  subtype: <subtype>?
    #  text: <txt-record>*
    #  port: <port>? (uint)

    service_tmpl = file2str(config().service_template)
    service_path = os.path.join(services_store_dir, _mksname(name)+'.service')
    stext = ''
    for i in text:
        stext += '<text-record>'+i.strip()+'</text-record>'
    service_conf = service_tmpl % {'name':name,'port':port,'host':host,'domain':domain,'stype':stype,'subtype':subtype or '','protocol':protocol or 'any','text':stext}
    _utils.str2file(service_conf, service_path)
    # activate here?

def activate(name):
    service_file = os.path.join(services_store_dir,_mksname(name)+'.service')
    service_link = os.path.join(services_live_dir,_mksname(name)+'.service')
    if service_file != service_link:
        if os.path.exists(service_file):
            if os.path.exists(os.path.split(service_link)[0]):
                try:
                    os.symlink(service_file,service_link)
                except Exception as sym_e:
                    return {'code':False,'message':repr(sym_e)}
            else:
                return {'code':False,'message':'Directory not found: "%s"' % os.path.split(service_link)[0]}
        else:
                return {'code':False,'message':'Directory not found: "%s"' % service_file}
    reload_avahi_daemon()
    return {'code':True,'message':'Activated'}

def deactivate(name):
    service_file = os.path.join(services_store_dir,_mksname(name)+'.service')
    service_link = os.path.join(services_live_dir,_mksname(name)+'.service')
    if service_file != service_link:
        if os.path.exists(service_link):
            try:
                os.remove(service_link)
            except Exception as rm_sym_e:
                return {'code':False,'message':repr(rm_sym_e)}
        else:
                return {'code':False,'message':'Directory not found: "%s"' % service_link}
        reload_avahi_daemon()
        return {'code':True,'message':'Deactivated'}
    else:
        return {'code':False,'message':'Service file is the same as service link (file:"%s", link:"%s")' % (service_file,service_link)}

def reload_avahi_daemon():
    import subprocess
    cmd = ['/usr/sbin/avahi-daemon','--reload']
    subprocess.call(cmd)

########NEW FILE########
__FILENAME__ = control_panel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# Project Byzantium: http://wiki.hacdc.org/index.php/Byzantium
# License: GPLv3

# control_panel.py
# This application runs in the background and implements a (relatively) simple
# HTTP server using CherryPy (http://www.cherrypy.org/) that controls the
# major functions of the Byzantium node, such as configuring, starting, and
# stopping the mesh networking subsystem.  CherryPy is hardcoded to listen on
# the loopback interface (127.0.0.1) on port 8080/TCP unless told otherwise.
# For security reasons I see no reason to change this; if you want to admin a
# Byzantium node remotely you'll have to use SSH port forwarding.

# v0.2  - Split the network traffic graphs from the system status report.
# v0.1  - Initial release.

# Import modules.
import cherrypy
from mako.lookup import TemplateLookup

import argparse
import logging
import os

from status import Status


def parse_args():
    parser = argparse.ArgumentParser(conflict_handler='resolve',
                                     description="This daemon implements the "
                                     "control panel functionality of Byzantium "
                                     "Linux.")
    parser.add_argument("--cachedir", action="store",
                        default="/tmp/controlcache")
    parser.add_argument("--configdir", action="store",
                        default="/etc/controlpanel")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                        help="Enable debugging mode.")
    parser.add_argument("--filedir", action="store",
                        default="/srv/controlpanel")
    parser.add_argument("-t", "--test", action="store_true", default=False,
                        help="Disables actually doing anything, it just prints "
                        "what would be done.  Used for testing commands "
                        "without altering the test system.")
    return parser.parse_args()


def check_args(args):
    if args.debug:
        print "Control panel debugging mode is on."
    if args.test:
        print "Control panel functional testing mode is on."
        # Configure for running in the current working directory.  This will
        # always be Byzantium/control_panel/.
        print("TEST: Referencing files from current working directory for "
              "testing.")
        args.filedir = 'srv/controlpanel'
        args.configdir = 'etc/controlpanel'
    return args


def main():
    args = check_args(parse_args())
    if args.debug or args.test:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)
    globalconfig = os.path.join(args.configdir,'controlpanelGlobal.conf')
    if args.test:
        appconfig = os.path.join(args.configdir,'controlpanel_test.conf')
    else:
        appconfig = os.path.join(args.configdir,'controlpanel.conf')

    # Set up the location the templates will be served out of.
    templatelookup = TemplateLookup(directories=[args.filedir],
                                    module_directory=args.cachedir,
                                    collection_size=100)

    # Read in the name and location of the appserver's global config file.
    cherrypy.config.update(globalconfig)

    # Allocate the objects representing the URL tree.
    root = Status(templatelookup, args.test, args.filedir)

    # Mount the object for the root of the URL tree, which happens to be the
    # system status page.  Use the application config file to set it up.
    logging.debug("Mounting Status() object as webapp root.")
    cherrypy.tree.mount(root, "/", appconfig)

    # Start the web server.
    if args.debug:
        logging.debug("Starting CherryPy.")
    cherrypy.engine.start()
    cherrypy.engine.block()

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = gateways
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# gateways.py - Implements the network gateway configuration subsystem of the
#    Byzantium control panel.

# Project Byzantium: http://wiki.hacdc.org/index.php/Byzantium
# License: GPLv3

# TODO:
# - In Gateways.activate(), add some code before running iptables to make sure
#   that NAT rules don't exist already.
#   iptables -t nat -n -L | grep MASQUERADE
# - Add code to configure encryption on wireless gateways.
# - Make it possible to specify IP configuration information on a wireless
#   uplink.
# - Add code to update_network_interfaces() to delete interfaces from the
#   database if they don't exist anymore.

import logging
import sqlite3
import subprocess
import time

import _utils
import networkconfiguration


def audit_procnetdev(procnetdev):
    if procnetdev:
        logging.debug("Successfully opened /proc/net/dev.")
    else:
        # Note: This means that we use the contents of the database.
        logging.debug("Warning: Unable to open /proc/net/dev.")
        return False

    # Smoke test by trying to read the first two lines from the pseudofile
    # (which comprises the column headers.  If this fails, just return
    # because we're falling back on the existing contents of the database.
    headers = procnetdev.readline()
    headers = procnetdev.readline()
    if not headers:
        logging.debug("Smoke test of /proc/net/dev read failed.")
        procnetdev.close()
        return False
    return True
    
    
def build_interfaces(interfaces, procnetdev):
    for line in procnetdev:
        interface = line.split()[0]
        interface = interface.strip()
        interface = interface.strip(':')
        interfaces.append(interface)
    return interfaces


def check_for_wired_interface(interface, cursor):
    template = (interface,)
    logging.debug("Checking to see if interface %s is a known wired interface...", interface)
    cursor.execute("SELECT interface FROM wired WHERE interface=?;", template)
    result = cursor.fetchall()
    if not result:
        logging.debug("Interface %s isn't a known wired interface.  Checking wireless interfaces...",
                      interface)
        return ''
    else:
        logging.debug("Interface %s is a known wired interface.", interface)
        return 'wired'


def check_for_wireless_interface(interface, cursor):
    template = (interface,)
    cursor.execute("SELECT mesh_interface FROM wireless WHERE mesh_interface=?;", template)
    result = cursor.fetchall()

    # If it's not in there, either, figure out which table it
    # has to go in.
    if not result:
        logging.debug("%s isn't a known wireless interface, either.  Figuring out where it has to go...", 
                      interface)
    else:
        logging.debug("%s is a known wireless interface.", interface)
        return 'wireless'


def check_wireless_table(interface):
    table = False
    procnetwireless = open('/proc/net/wireless', 'r')
    procnetwireless.readline()
    procnetwireless.readline()
    for line in procnetwireless:
        if interface in line:
            logging.debug("Goes in wireless table.")
            table = True
    procnetwireless.close()
    return table


# Classes.
# This class allows the user to turn a configured network interface on their
# node into a gateway from the mesh to another network (usually the global Net).
class Gateways(object):

    def __init__(self, templatelookup, test):
        self.templatelookup = templatelookup
        self.test = test

        self.netconfdb, self.meshconfdb = _utils.set_confdbs(self.test)

        # Configuration information for the network device chosen by the user to
        # act as the uplink.
        self.interface = ''
        self.channel = 0
        self.essid = ''

        # Used for sanity checking user input.
        self.frequency = 0
        
        # Class attributes which make up a network interface.  By default they are
        # blank, but will be populated from the network.sqlite database if the
        # user picks an already-configured interface.
        self.mesh_interface = ''
        self.mesh_ip = ''
        self.client_interface = ''
        self.client_ip = ''

        # Set the netmasks aside so everything doesn't run together.
        self.mesh_netmask = '255.255.0.0'
        self.client_netmask = '255.255.255.0'

        # Attributes for flat files that this object maintains for the client side
        # of the network subsystem.
        self.hosts_file = '/etc/hosts.mesh'
        self.dnsmasq_include_file = '/etc/dnsmasq.conf.include'

    # Pretends to be index.html.
    def index(self):
        ethernet_buttons = ""
        wireless_buttons = ""

        # To find any new network interfaces, rescan the network interfaces on
        # the node.
        self.update_network_interfaces()

        query = "SELECT interface FROM wired WHERE gateway='no';"
        _, cursor = _utils.execute_query(self.netconfdb, query)
        results = cursor.fetchall()
        if results:
            for interface in results:
                ethernet_buttons = ethernet_buttons + "<td><input type='submit' name='interface' value='" + interface[0] + "' /></td>\n"

        # Generate a list of wireless interfaces on the node that are not
        # enabled but are known.  As before, each button gets is own button
        # in a table.
        cursor.execute("SELECT mesh_interface FROM wireless WHERE gateway='no';")
        results = cursor.fetchall()
        if results:
            for interface in results:
                wireless_buttons = wireless_buttons + "<td><input type='submit' name='interface' value='" + interface[0] + "' /></td>\n"

        # Close the connection to the database.
        cursor.close()

        # Render the HTML page.
        try:
            page = self.templatelookup.get_template("/gateways/index.html")
            return page.render(title = "Network Gateway",
                               purpose_of_page = "Configure Network Gateway",
                               ethernet_buttons = ethernet_buttons,
                               wireless_buttons = wireless_buttons)
        except:
            _utils.output_error_data()
    index.exposed = True

    # Utility method to update the list of all network interfaces on a node.
    # New ones detected are added to the network.sqlite database.  Takes no
    # arguments; returns nothing (but alters the database).
    def update_network_interfaces(self):
        logging.debug("Entered Gateways.update_network_interfaces().")

        # Open the kernel's canonical list of network interfaces.
        procnetdev = open("/proc/net/dev", "r")
        if not audit_procnetdev(procnetdev):
            return

        # Open the network configuration database.
        connection = sqlite3.connect(self.netconfdb)
        cursor = connection.cursor()

        # Begin parsing the contents of /proc/net/dev to extract the names of
        # the interfaces.
        interfaces = []
        if self.test:
            logging.debug("Pretending to harvest /proc/net/dev for network interfaces.  Actually using the contents of %s and loopback.", self.netconfdb)
            return
        else:
            interfaces = build_interfaces(interfaces, procnetdev)

            # Walk through the list of interfaces just generated and see if
            # each one is already in the database.  If it's not, add it.
            for interface in interfaces:

                # See if it's in the table of wired interfaces.
                found = check_for_wired_interface(interface, cursor)

                # If it's not in the wired table, check the wireless table.
                if not found:
                    found = check_for_wireless_interface(interface, cursor)

                # If it still hasn't been found, figure out where it has to go.
                if not found:
                    logging.debug("Interface %s really is new.  Figuring out where it should go.", interface)

                    # Look in /proc/net/wireless.  If it's in there, it
                    # goes in the wireless table.  Otherwise it goes in
                    # the wired table.
                    if check_wireless_table(interface):
                        template = ('no', interface + ':1', 'no', 0, '', interface , )
                        cursor.execute("INSERT INTO wireless VALUES (?,?,?,?,?,?);", template)
                    else:
                        logging.debug("Goes in wired table.")
                        template = ('no', 'no', interface, )
                        cursor.execute("INSERT INTO wired VALUES (?,?,?);", template)

                    connection.commit()

        # Close the network configuration database and return.
        cursor.close()
        logging.debug("Leaving Gateways.enumerate_network_interfaces().")

    # Implements step two of the wired gateway configuration process: turning
    # the gateway on.  This method assumes that whichever Ethernet interface
    # chosen is already configured via DHCP through ifplugd.
    def tcpip(self, interface=None, essid=None, channel=None):
        logging.debug("Entered Gateways.tcpip().")

        # Define this variable in case wireless configuration information is
        # passed into this method.
        iwconfigs = ''

        # Test to see if the interface argument has been passed.  If it hasn't
        # then this method is being called from Gateways.wireless(), so
        # populate it from the class attribute variable.
        if interface is None:
            interface = self.interface

        # If an ESSID and channel were passed to this method, store them in
        # class attributes.
        if essid:
            self.essid = essid
            iwconfigs = '<p>Wireless network configuration:</p>\n'
            iwconfigs = iwconfigs + '<p>ESSID: ' + essid + '</p>\n'
        if channel:
            self.channel = channel
            iwconfigs = iwconfigs + '<p>Channel: ' + channel + '</p>\n'

        # Run the "Are you sure?" page through the template interpeter.
        try:
            page = self.templatelookup.get_template("/gateways/confirm.html")
            return page.render(title = "Enable gateway?",
                               purpose_of_page = "Confirm gateway mode.",
                               interface = interface, iwconfigs = iwconfigs)
        except:
            _utils.output_error_data()
    tcpip.exposed = True

    # Allows the user to enter the ESSID and wireless channel of the wireless
    # network interface that will act as an uplink to another Network for the
    # mesh.  Takes as an argument the value of the 'interface' variable passed
    # from the form on /gateways/index.html.
    def wireless(self, interface=None):
        # Store the name of the interface in question in a class attribute for
        # use later.
        self.interface = interface

        # Set up variables to hold the ESSID and channel of the wireless
        # uplink.
        channel = 0
        essid = ''

        channel, essid, warning = _utils.check_for_configured_interface(self.netconfdb, interface, channel, essid)

        # The forms in the HTML template do everything here, as well.  This
        # method only accepts input for use later.
        try:
            page = self.templatelookup.get_template("/gateways/wireless.html")
            return page.render(title = "Configure wireless uplink.",
                           purpose_of_page = "Set wireless uplink parameters.",
                           warning = warning, interface = interface,
                           channel = channel, essid = essid)
        except:
            _utils.output_error_data()
    wireless.exposed = True

    def _get_mesh_interfaces(self, interface):
        interfaces = []
        query = "SELECT interface FROM meshes WHERE enabled='yes' AND protocol='babel';"
        _, cursor = _utils.execute_query(self.meshconfdb, query)
        results = cursor.fetchall()
        for i in results:
            interfaces.append(i[0])
        interfaces.append(interface)
        cursor.close()
        return interfaces
        
    def _update_netconfdb(self, interface):
        query = "SELECT interface FROM wired WHERE interface=?;"
        connection, cursor = _utils.execute_query(self.netconfdb, query, template=(interface, ))
        template = ('yes', interface, )
        results = cursor.fetchall()
        if results:
            cursor.execute("UPDATE wired SET gateway=? WHERE interface=?;",
                            template)
        # Otherwise, it's a wireless interface.
        else:
            cursor.execute("UPDATE wireless SET gateway=? WHERE mesh_interface=?;", template)

        # Clean up.
        connection.commit()
        cursor.close()

    # Method that does the deed of turning an interface into a gateway.  This
    def activate(self, interface=None):
        logging.debug("Entered Gateways.activate().")

        # Test to see if wireless configuration attributes are set, and if they
        # are, use iwconfig to set up the interface.
        if self.essid:
            command = ['/sbin/iwconfig', interface, 'essid', self.essid]
            logging.debug("Setting ESSID to %s.", self.essid)
            if self.test:
                logging.debug("Command to set ESSID:\n%s", ' '.join(command))
            else:
                subprocess.Popen(command)
        if self.channel:
            command = ['/sbin/iwconfig', interface, 'channel', self.channel]
            logging.debug("Setting channel %s.", self.channel)
            if self.test:
                logging.debug("Command to set channel:\n%s", ' '.join(command))
            else:
                subprocess.Popen(command)

        # If we have to configure layers 1 and 2, then it's a safe bet that we
        # should use DHCP to set up layer 3.  This is wrapped in a shell script
        # because of a timing conflict between the time dhcpcd starts, the
        # time dhcpcd gets IP configuration information (or not) and when
        # avahi-daemon is bounced.
        command = ['/usr/local/sbin/gateway.sh', interface]
        logging.debug("Preparing to configure interface %s.", interface)
        if self.test:
            logging.debug("Pretending to run gateway.sh on interface %s.", interface)
            logging.debug("Command that would be run:\n%s", ' '.join(command))
        else:
            subprocess.Popen(command)

        # See what value was returned by the script.

        # Set up a list of mesh interfaces for which babeld is already running.
        #
        # NOTE: the interfaces variable doesn't seem to ever get used anywhere :/
        #
        interfaces = self._get_mesh_interfaces(interface)

        # Update the network configuration database to reflect the fact that
        # the interface is now a gateway.  Search the table of Ethernet
        # interfaces first.
        self._update_netconfdb(interface)

        # Display the confirmation of the operation to the user.
        try:
            page = self.templatelookup.get_template("/gateways/done.html")
            return page.render(title = "Enable gateway?",
                               purpose_of_page = "Confirm gateway mode.",
                               interface = interface)
        except:
            _utils.output_error_data()
    activate.exposed = True

    # Configure the network interface.
    def set_ip(self):
        # If we've made it this far, the user's decided to (re)configure a
        # network interface.  Full steam ahead, damn the torpedoes!

        # First, take the wireless NIC offline so its mode can be changed.
        command = ['/sbin/ifconfig', self.mesh_interface, 'down']
        output = subprocess.Popen(command)
        time.sleep(5)

        # Wrap this whole process in a loop to ensure that stubborn wireless
        # interfaces are configured reliably.  The wireless NIC has to make it
        # all the way through one iteration of the loop without errors before
        # we can go on.
        while True:
            # Set the mode, ESSID and channel.
            command = ['/sbin/iwconfig', self.mesh_interface, 'mode ad-hoc']
            output = subprocess.Popen(command)
            command = ['/sbin/iwconfig', self.mesh_interface, 'essid', self.essid]
            output = subprocess.Popen(command)
            command = ['/sbin/iwconfig', self.mesh_interface, 'channel',  self.channel]
            output = subprocess.Popen(command)

            # Run iwconfig again and capture the current wireless configuration.
            command = ['/sbin/iwconfig', self.mesh_interface]
            output = subprocess.Popen(command).stdout
            configuration = output.readlines()

            # Test the interface by going through the captured text to see if
            # it's in ad-hoc mode.  If it's not, put it in ad-hoc mode and go
            # back to the top of the loop to try again.
            for line in configuration:
                if 'Mode' in line:
                    line = line.strip()
                    mode = line.split(' ')[0].split(':')[1]
                    if mode != 'Ad-Hoc':
                        continue

            # Test the ESSID to see if it's been set properly.
            for line in configuration:
                if 'ESSID' in line:
                    line = line.strip()
                    essid = line.split(' ')[-1].split(':')[1]
                    if essid != self.essid:
                        continue

            # Check the wireless channel to see if it's been set properly.
            for line in configuration:
                if 'Frequency' in line:
                    line = line.strip()
                    frequency = line.split(' ')[2].split(':')[1]
                    if frequency != self.frequency:
                        continue

            # "Victory is mine!"
            # --Stewie, _Family Guy_
            break

        # Call ifconfig and set up the network configuration information.
        command = ['/sbin/ifconfig', self.mesh_interface, self.mesh_ip,
                   'netmask', self.mesh_netmask, 'up']
        output = subprocess.Popen(command)
        time.sleep(5)

        # Add the client interface.
        command = ['/sbin/ifconfig', self.client_interface, self.client_ip, 'up']
        output = subprocess.Popen(command)

        template = ('yes', self.channel, self.essid, self.mesh_interface, self.client_interface, self.mesh_interface)
        _utils.set_wireless_db_entry(self.netconfdb, template)

        # Send this information to the methods that write the /etc/hosts and
        # dnsmasq config files.
        networkconfiguration.make_hosts(self.hosts_file, self.test, starting_ip=self.client_ip)
        networkconfiguration.configure_dnsmasq(self.dnsmasq_include_file, self.test, starting_ip=self.client_ip)

        # Render and display the page.
        try:
            page = self.templatelookup.get_template("/network/done.html")
            return page.render(title = "Network interface configured.",
                               purpose_of_page = "Configured!",
                               interface = self.mesh_interface,
                               ip_address = self.mesh_ip,
                               netmask = self.mesh_netmask,
                               client_ip = self.client_ip,
                               client_netmask = self.client_netmask)
        except:
            _utils.output_error_data()
    set_ip.exposed = True


########NEW FILE########
__FILENAME__ = meshconfiguration
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# meshconfiguration.py - Lets the user configure and manipulate mesh-enabled
#    wireless network interfaces.  Wired interfaces (Ethernet) are reserved for
#    use as net.gateways and fall under a different web app.

# For the time being this class is designed to operate with the Babel protocol
# (http://www.pps.jussieu.fr/~jch/software/babel/).  It would have to be
# rewritten to support a different (or more) protocols.

# Project Byzantium: http://wiki.hacdc.org/index.php/Byzantium
# License: GPLv3

# TODO:
# - Make network interfaces that don't exist anymore go away.
# - Detect when an interface is already routing and instead offer the ability
#   to remove it from the mesh.  Do that in the MeshConfiguration.index()
#   method.
# - Add support for other mesh routing protocols for interoperability.  This
#   will involve the user picking the routing protocol after picking the
#   network interface.  This will also likely involve selecting multiple mesh
#   routing protocols (i.e., babel+others).

import logging
import os
import signal
import sqlite3
import subprocess
import time

import _utils


# Classes.
# Allows the user to configure mesh networking on wireless network interfaces.
class MeshConfiguration(object):

    def __init__(self, templatelookup, test):
        self.templatelookup = templatelookup
        self.test = test

        # Class constants.
        self.babeld = '/usr/local/bin/babeld'
        self.babeld_pid = '/var/run/babeld.pid'
        self.babeld_timeout = 3

        self.netconfdb, self.meshconfdb = _utils.set_confdbs(self.test)

        # Class attributes which apply to a network interface.  By default they
        # are blank but will be populated from the mesh.sqlite database if the
        # user picks an interface that's already been set up.
        self.interface = ''
        self.protocol = ''
        self.enabled = ''
        self.pid = ''

    def pid_check(self):
        pid = ''
        if os.path.exists(self.babeld_pid):
            logging.debug("Reading PID of babeld.")
            pidfile = open(self.babeld_pid, 'r')
            pid = pidfile.readline()
            pidfile.close()
            logging.debug("PID of babeld: %s", str(pid))
        return pid

    # Pretends to be index.html.
    def index(self):
        # This is technically irrelevant because the class' attributes are blank
        # when instantiated, but it's useful for setting up the HTML fields.
        self.reinitialize_attributes()

        # Populate the database of mesh interfaces using the network interface
        # database as a template.  Start by pulling a list of interfaces out of
        # the network configuration database.
        error = []
        netconfconn = sqlite3.connect(self.netconfdb)
        netconfcursor = netconfconn.cursor()
        interfaces = []
        netconfcursor.execute("SELECT mesh_interface, enabled FROM wireless;")
        results = netconfcursor.fetchall()
        active_interfaces = []
        if not results:
            # Display an error page which says that no wireless interfaces have
            # been configured yet.
            error.append("<p>ERROR: No wireless network interfaces have been configured yet.  <a href='/network'>You need to do that first!</a></p>")
        else:
            # Open a connection to the mesh configuration database.
            meshconfconn = sqlite3.connect(self.meshconfdb)
            meshconfcursor = meshconfconn.cursor()

            # Walk through the list of results.
            for i in results:
                # Is the network interface already configured?
                if i[1] == 'yes':
                    # See if the interface is already in the mesh configuration
                    # database, and if it's not insert it.
                    template = (i[0], )
                    meshconfcursor.execute("SELECT interface, enabled FROM meshes WHERE interface=?;", template)
                    interface_found = meshconfcursor.fetchall()
                    interface_tag = "<input type='submit' name='interface' value='"
                    if not interface_found:
                        template = ('no', i[0], 'babel', )
                        meshconfcursor.execute("INSERT INTO meshes VALUES (?, ?, ?);", template)
                        meshconfconn.commit()

                        # This is a network interface that's ready to configure,
                        # so add it to the HTML template as a button.
                        interfaces.append("%s%s' style='background-color:white;' />\n" % (interface_tag, i[0]))
                    else:
                        # If the interface is enabled, add it to the row of
                        # active interfaces with a different color.
                        if interface_found[0][1] == 'yes':
                            active_interfaces.append("%s%s' style='background-color:green;' />\n" % (interface_tag, i[0]))
                        else:
                            # The mesh interface hasn't been configured.
                            interfaces.append("%s%s' />\n" % (interface_tag, i[0]))

                else:
                    # This interface isn't configured but it's in the database,
                    # so add it to the template as an unclickable button.
                    # While it might not be a good idea to put unusable buttons
                    # into the page, it would tell the user that the interfaces
                    # were detected.
                    interfaces.append("%s%s' style='background-color:orange;' />\n" % (interface_tag, i[0]))
            meshconfcursor.close()

        # Clean up our connections to the configuration databases.
        netconfcursor.close()

        # Render the HTML page.
        try:
            page = self.templatelookup.get_template("/mesh/index.html")
            return page.render(title = "Byzantium Node Mesh Configuration",
                               purpose_of_page = "Configure Mesh Interfaces",
                               error = ''.join(error), interfaces = ''.join(interfaces),
                               active_interfaces = ''.join(active_interfaces))
        except:
            _utils.output_error_data()
    index.exposed = True

    # Reinitialize the attributes of an instance of this class to a known
    # state.
    def reinitialize_attributes(self):
        logging.debug("Reinitializing class attributes of MeshConfiguration().")
        self.interface = ''
        self.protocol = ''
        self.enabled = ''
        self.pid = ''

    # Allows the user to add a wireless interface to the mesh.  Assumes that
    # the interface is already configured (we wouldn't get this far if it
    # wasn't.
    def addtomesh(self, interface=None):
        # Store the name of the network interface and whether or not it's
        # enabled in the object's attributes.  Right now only the Babel
        # protocol is supported, so that's hardcoded for the moment (but it
        # could change in later releases).
        self.interface = interface
        self.protocol = 'babel'
        self.enabled = 'no'

        # Render the HTML page.
        try:
            page = self.templatelookup.get_template("/mesh/addtomesh.html")
            return page.render(title = "Byzantium Node Mesh Configuration",
                               purpose_of_page = "Enable Mesh Interfaces",
                               interface = self.interface,
                               protocol = self.protocol)
        except:
            _utils.output_error_data()
    addtomesh.exposed = True
    
    def _pid_helper(self, pid, error, output, cursor, connection, commit=False):
        if not os.path.isdir('/proc/' + pid):
            error = "ERROR: babeld is not running!  Did it crash during or after startup?"
        else:
            output = "%s has been successfully started with PID %s." % (self.babeld, pid)
            
            # Update the mesh configuration database to take into account
            # the presence of the new interface.
            template = ('yes', self.interface, )
            cursor.execute("UPDATE meshes SET enabled=? WHERE interface=?;", template)
            if commit:
                connection.commit()
        return error, output

    def update_babeld(self, common_babeld_opts, unique_babeld_opts, interfaces):
        # Assemble the invocation of babeld.
        babeld_command = []
        babeld_command.append(self.babeld)
        babeld_command = babeld_command + common_babeld_opts
        babeld_command = babeld_command + unique_babeld_opts + interfaces
        logging.debug("babeld command to be executed: %s", ' '.join(babeld_command))

        # Test to see if babeld is running.  If it is, it's routing for at
        # least one interface, in which case we add the one the user just
        # picked to the list because we'll have to restart babeld.  Otherwise,
        # we just start babeld.
        pid = self.pid_check()
        if pid:
            if self.test:
                logging.debug("Pretending to kill babeld.")
            else:
                logging.debug("Killing babeld...")
                os.kill(int(pid), signal.SIGTERM)
            time.sleep(self.babeld_timeout)
        if self.test:
            logging.debug("Pretending to restart babeld.")
        else:
            logging.debug("Restarting babeld.")
            subprocess.Popen(babeld_command)
        time.sleep(self.babeld_timeout)
        return babeld_command

    # Runs babeld to turn self.interface into a mesh interface.
    def enable(self):
        # Set up the error and successful output messages.
        error = ''
        output = ''

        # Set up a default set of command line options for babeld.  Some of
        # these are redundant but are present in case an older version of
        # babeld is used on the node.  See the following file to see why:
        # http://www.pps.jussieu.fr/~jch/software/babel/CHANGES.text
        common_babeld_opts = ['-m', 'ff02:0:0:0:0:0:1:6', '-p', '6696', '-D',
			      '-g', '33123' , '-c', '/etc/babeld.conf']

        # Create a set of unique command line options for babeld.  Right now,
        # this variable is empty but it might be used in the future.  Maybe
        # it'll be populated from a config file or something.
        unique_babeld_opts = []

        # Set up a list of mesh interfaces for which babeld is already running.
        interfaces = []
        query = "SELECT interface, enabled, protocol FROM meshes WHERE enabled='yes' AND protocol='babel';"
        connection, cursor = _utils.execute_query(self.meshconfdb, query)
        results = cursor.fetchall()
        for i in results:
            logging.debug("Adding interface: %s", i[0])
            interfaces.append(i[0])

        # By definition, if we're in this method the new interface hasn't been
        # added yet.
        interfaces.append(self.interface)

        self.update_babeld(common_babeld_opts, unique_babeld_opts, interfaces)

        # Get the PID of babeld, then test to see if that pid exists and
        # corresponds to a running babeld process.  If there is no match,
        # babeld isn't running.
        pid = self.pid_check()
        if pid:
            error, output = self._pid_helper(pid, error, output, cursor, connection, commit=True)
        cursor.close()

        # Render the HTML page.
        try:
            page = self.templatelookup.get_template("/mesh/enabled.html")
            return page.render(title = "Byzantium Node Mesh Configuration",
                               purpose_of_page = "Mesh Interface Enabled",
                               protocol = self.protocol,
                               interface = self.interface,
                               error = error, output = output)
        except:
            _utils.output_error_data()
    enable.exposed = True

    # Allows the user to remove a configured interface from the mesh.  Takes
    # one argument from self.index(), the name of the interface.
    def removefrommesh(self, interface=None):
        logging.debug("Entered MeshConfiguration.removefrommesh().")

        # Configure this instance of the object for the interface the user
        # wants to remove from the mesh.
        self.interface = interface
        self.protocol = 'babel'
        self.enabled = 'yes'

        # Render the HTML page.
        try:
            page = self.templatelookup.get_template("/mesh/removefrommesh.html")
            return page.render(title = "Byzantium Node Mesh Configuration",
                               purpose_of_page = "Disable Mesh Interface",
                               interface = interface)
        except:
            _utils.output_error_data()
    removefrommesh.exposed = True

    # Re-runs babeld without self.interface to drop it out of the mesh.
    def disable(self):
        logging.debug("Entered MeshConfiguration.disable().")

        # Set up the error and successful output messages.
        error = ''
        output = ''

        # Set up a default set of command line options for babeld.  Some of
        # these are redundant but are present in case an older version of
        # babeld is used on the node.  See the following file to see why:
        # http://www.pps.jussieu.fr/~jch/software/babel/CHANGES.text
        common_babeld_opts = ['-m', 'ff02:0:0:0:0:0:1:6', '-p', '6696', '-D']

        # Create a set of unique command line options for babeld.  Right now,
        # this variable is empty but it might be used in the future.  Maybe
        # it'll be populated from a config file or something.
        unique_babeld_opts = []

        # Set up a list of mesh interfaces for which babeld is already running
        # but omit self.interface.
        interfaces = []
        query = "SELECT interface FROM meshes WHERE enabled='yes' AND protocol='babel';"
        connection, cursor = _utils.execute_query(self.meshconfdb, query)
        results = cursor.fetchall()
        for i in results:
            if i[0] != self.interface:
                interfaces.append(i[0])

        # If there are no mesh interfaces configured anymore, then the node
        # is offline.
        if not interfaces:
            output = 'Byzantium node offline.'

        babeld_command = self.update_babeld(common_babeld_opts, unique_babeld_opts, interfaces)

        # If there is at least one wireless network interface still configured,
        # then re-run babeld.
        if interfaces:
            logging.debug("value of babeld_command is %s", babeld_command)
            if self.test:
                logging.debug("Pretending to restart babeld.")
            else:
                subprocess.Popen(babeld_command)
            time.sleep(self.babeld_timeout)

        # Get the PID of babeld, then test to see if that pid exists and
        # corresponds to a running babeld process.  If there is no match,
        # babeld isn't running, in which case something went wrong.
        pid = self.pid_check()
        if pid:
            error, output = self._pid_helper(pid, error, output, cursor, connection)
        else:
            # There are no mesh interfaces left, so update the database to
            # deconfigure self.interface.
            template = ('no', self.interface, )
            cursor.execute("UPDATE meshes SET enabled=? WHERE interface=?;",
                           template)
        connection.commit()
        cursor.close()

        # Render the HTML page.
        try:
            page = self.templatelookup.get_template("/mesh/disabled.html")
            return page.render(title = "Byzantium Node Mesh Configuration",
                               purpose_of_page = "Disable Mesh Interface",
                               error = error, output = output)
        except:
            _utils.output_error_data()
    removefrommesh.exposed = True
    disable.exposed = True

########NEW FILE########
__FILENAME__ = networkconfiguration
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# networkconfiguration.py - Implements the network interface configuration
#    subsystem of the Byzantium control panel.

# Project Byzantium: http://wiki.hacdc.org/index.php/Byzantium
# License: GPLv3

# TODO:
# - Figure out what columns in the network configuration database to index.
#   It's doubtful that a Byzantium node would have more than three interfaces
#   (not counting lo) but it's wise to plan for the future.  Profile based on
#   which columns are SELECTed from most often.
# - Find a way to prune network interfaces that have vanished.
#   MOOF MOOF MOOF - Stubbed in.

import logging
import os
import os.path
import random
import re
import sqlite3
import subprocess
import time

import _utils
        

# Utility method to enumerate all of the network interfaces on a node.
# Returns two lists, one of wired interfaces and one of wireless
# interfaces.
def enumerate_network_interfaces():
    logging.debug("Entered NetworkConfiguration.enumerate_network_interfaces().")
    logging.debug("Reading contents of /sys/class/net/.")
    wired = []
    wireless = []

    # Enumerate network interfaces.
    interfaces = os.listdir('/sys/class/net')

    # Remove the loopback interface because that's our failure case.
    if 'lo' in interfaces:
        interfaces.remove('lo')

    # Failure case: If the list of interfaces is empty, return lists
    # containing only the loopback.
    if not interfaces:
        logging.debug("No interfaces found.  Defaulting.")
        return(['lo'], ['lo'])

    # For each network interface's pseudofile in /sys, test to see if a
    # subdirectory 'wireless/' exists.  Use this to sort the list of
    # interfaces into wired and wireless.
    for i in interfaces:
        logging.debug("Adding network interface %s.", i)
        if os.path.isdir("/sys/class/net/%s/wireless" % i):
            wireless.append(i)
        else:
            wired.append(i)
    return (wired, wireless)


# Method that generates an /etc/hosts.mesh file for the node for dnsmasq.
# Takes three args, the first and last IP address of the netblock.  Returns
# nothing.
def make_hosts(hosts_file, test, starting_ip=None):
    logging.debug("Entered NetworkConfiguration.make_hosts().")

    # See if the /etc/hosts.mesh backup file exists.  If it does, delete it.
    old_hosts_file = hosts_file + '.bak'
    if test:
        logging.debug("Deleted old /etc/hosts.mesh.bak.")
    else:
        if os.path.exists(old_hosts_file):
            os.remove(old_hosts_file)

    # Back up the old hosts.mesh file.
    if test:
        logging.debug("Renamed /etc/hosts.mesh file to /etc/hosts.mesh.bak.")
    else:
        if os.path.exists(hosts_file):
            os.rename(hosts_file, old_hosts_file)

    # We can make a few assumptions given only the starting IP address of
    # the client IP block.  Each node has a /24 netblock for clients, so
    # we only have to generate 254 entries for that file (.2-254).  First,
    # split the last octet off of the IP address passed to this method.
    (octet_one, octet_two, octet_three, _) = starting_ip.split('.')
    prefix = octet_one + '.' + octet_two + '.' + octet_three + '.'

    # Generate the contents of the new hosts.mesh file.
    if test:
        logging.debug("Pretended to generate new /etc/hosts.mesh file.")
        return False
    else:
        hosts = open(hosts_file, "w")
        line = prefix + str('1') + '\tbyzantium.byzantium.mesh\n'
        hosts.write(line)
        for i in range(2, 255):
            line = prefix + str(i) + '\tclient-' + prefix + str(i) + '.byzantium.mesh\n'
            hosts.write(line)
        hosts.close()

    # Test for successful generation of the file.
    error = False
    if not os.path.exists(hosts_file):
        os.rename(old_hosts_file, hosts_file)
        error = True
    return error

# Generates an /etc/dnsmasq.conf.include file for the node.  Takes one arg,
# the IP address to start from.
def configure_dnsmasq(dnsmasq_include_file, test, starting_ip=None):
    logging.debug("Entered NetworkConfiguration.configure_dnsmasq().")

    # Split the last octet off of the IP address passed into this
    # method.
    (octet_one, octet_two, octet_three, _) = starting_ip.split('.')
    prefix = octet_one + '.' + octet_two + '.' + octet_three + '.'
    start = prefix + str('2')
    end = prefix + str('254')

    # Use that to generate the line for the config file.
    # dhcp-range=<starting IP>,<ending IP>,<length of lease>
    dhcp_range = 'dhcp-range=' + start + ',' + end + ',5m\n'

    # If an include file already exists, move it out of the way.
    oldfile = dnsmasq_include_file + '.bak'
    if test:
        logging.debug("Deleting old /etc/dnsmasq.conf.include.bak file.")
    else:
        if os.path.exists(oldfile):
            os.remove(oldfile)

    # Back up the old dnsmasq.conf.include file.
    if test:
        logging.debug("Backing up /etc/dnsmasq.conf.include file.")
        logging.debug("Now returning to save time.")
        return
    else:
        if os.path.exists(dnsmasq_include_file):
            os.rename(dnsmasq_include_file, oldfile)

    # Open the include file so it can be written to.
    include_file = open(dnsmasq_include_file, 'w')

    # Write the DHCP range for this node's clients.
    include_file.write(dhcp_range)

    # Close the include file.
    include_file.close()

    # Restart dnsmasq.
    subprocess.Popen(['/etc/rc.d/rc.dnsmasq', 'restart'])
    return


# Constants.
# Ugly, I know, but we need a list of wi-fi channels to frequencies for the
# sanity checking code.
frequencies = [2.412, 2.417, 2.422, 2.427, 2.432, 2.437, 2.442, 2.447, 2.452,
               2.457, 2.462, 2.467, 2.472, 2.484]

# Classes.
# This class allows the user to configure the network interfaces of their node.
# Note that this does not configure mesh functionality.
class NetworkConfiguration(object):

    def __init__(self, templatelookup, test):
        self.templatelookup = templatelookup
        self.test = test

        # Location of the network.sqlite database, which holds the configuration
        # of every network interface in the node.
        if self.test:
            # self.netconfdb = '/home/drwho/network.sqlite'
            self.netconfdb = 'var/db/controlpanel/network.sqlite'
            logging.debug("Location of NetworkConfiguration.netconfdb: %s", self.netconfdb)
        else:
            self.netconfdb = '/var/db/controlpanel/network.sqlite'

        # Class attributes which make up a network interface.  By default they are
        # blank, but will be populated from the network.sqlite database if the
        # user picks an already-configured interface.
        self.mesh_interface = ''
        self.mesh_ip = ''
        self.client_interface = ''
        self.client_ip = ''
        self.channel = ''
        self.essid = ''
        self.bssid = '02:CA:FF:EE:BA:BE'
        self.ethernet_interface = ''
        self.ethernet_ip = ''
        self.frequency = 0.0
        self.gateway = 'no'

        # Set the netmasks aside so everything doesn't run together.
        self.mesh_netmask = '255.255.0.0'
        self.client_netmask = '255.255.255.0'

        # Attributes for flat files that this object maintains for the client side
        # of the network subsystem.
        self.hosts_file = '/etc/hosts.mesh'
        self.dnsmasq_include_file = '/etc/dnsmasq.conf.include'

    # Pretends to be index.html.
    def index(self):
        logging.debug("Entering NetworkConfiguration.index().")

        # Reinitialize this class' attributes in case the user wants to
        # reconfigure an interface.  It'll be used to set the default values
        # of the HTML fields.
        self.reinitialize_attributes()

        # Get a list of all network interfaces on the node (sans loopback).
        wired, wireless = enumerate_network_interfaces()
        logging.debug("Contents of wired[]: %s", wired)
        logging.debug("Contents of wireless[]: %s", wireless)

        # MOOF MOOF MOOF - call to stub implementation.  We can use the list
        # immediately above (interfaces) as the list to compare the database
        # against.
        # Test to see if any network interfaces have gone away.
        #logging.debug("Pruning missing network interfaces.")
        #self.prune(interfaces)

        # Build tables containing the interfaces extant.  At the same time,
        # search the network configuration databases for interfaces that are
        # already configured and give them a different color.  If they're up
        # and running give them yet another color.
        connection = sqlite3.connect(self.netconfdb)
        cursor = connection.cursor()
        wireless_buttons = ""
        ethernet_buttons = ""

        interface_tag_start = "<input type='submit' name='interface' value='"

        # Start with wireless interfaces.
        for i in wireless:
            logging.debug("Checking to see if %s is in the database.", i)
            cursor.execute("SELECT mesh_interface, enabled FROM wireless WHERE mesh_interface=?", (i, ))
            result = cursor.fetchall()

            # If the interface is not found in database, add it.
            if not result:
                logging.debug("Adding %s to table 'wireless'.", i)

                # gateway, client_interface, enabled, channel, essid,
                # mesh_interface
                template = ('no', (i + ':1'), 'no', '0', '', i, )

                cursor.execute("INSERT INTO wireless VALUES (?,?,?,?,?,?);", template)
                connection.commit()
                wireless_buttons += "%s%s' />\n" % (interface_tag_start, i)
                continue

            # If it is there test to see if it's been configured or not.  If it
            # has, use a CSS hack to make its button a different color.
            if result[0][1] == "yes":
                wireless_buttons += "%s%s' style='background-color:red' />\n" % (interface_tag_start, i)
                continue

            # If all else fails, just add the button without any extra
            # decoration.
            wireless_buttons += "%s%s' />\n" % (interface_tag_start, i)

        # Wired interfaces.
        for i in wired:
            logging.debug("Checking to see if %s is in the database.", i)
            cursor.execute("SELECT interface, enabled FROM wired WHERE interface=?", (i, ))
            result = cursor.fetchall()

            # If the interface is not found in database, add it.
            if not result:
                logging.debug("Adding %s to table 'wired'.", i)

                # enabled, gateway, interface
                template = ('no', 'no', i, )
                cursor.execute("INSERT INTO wired VALUES (?,?,?);", template)
                connection.commit()
                ethernet_buttons += "%s%s' />\n" % (interface_tag_start, i)
                continue

            # If it is found test to see if it's been configured or not.  If it
            # has, use a CSS hack to make its button a different color.
            if result[0][1] == "yes":
                ethernet_buttons += "%s%s' style='background-color:red' />\n" % (interface_tag_start, i)
                continue

            # If all else fails, just add the button without any extra
            # decoration.
            ethernet_buttons += "%s%s' />\n" % (interface_tag_start, i)

        # Render the HTML page.
        cursor.close()
        try:
            page = self.templatelookup.get_template("/network/index.html")
            return page.render(title = "Byzantium Node Network Interfaces",
                               purpose_of_page = "Configure Network Interfaces",
                               wireless_buttons = wireless_buttons,
                               ethernet_buttons = ethernet_buttons)
        except:
            _utils.output_error_data()
    index.exposed = True

    # Used to reset this class' attributes to a known state.
    def reinitialize_attributes(self):
        logging.debug("Reinitializing class attributes of NetworkConfiguration().")
        self.mesh_interface = ''
        self.client_interface = ''
        self.channel = ''
        self.essid = ''
        self.mesh_ip = ''
        self.client_ip = ''
        self.frequency = 0.0
        self.gateway = 'no'

    # This method is run every time the NetworkConfiguration() object is
    # instantiated by the admin browsing to /network.  It traverses the list
    # of network interfaces extant on the system and compares it against the
    # network configuration database.  Anything in the database that isn't in
    # the kernel is deleted.  Takes one argument, the list of interfaces the
    # kernel believes are present.
    # def prune(self, interfaces=None):
    #    logging.debug("Entered NetworkConfiguration.prune()")

    # Allows the user to enter the ESSID and wireless channel of their node.
    # Takes as an argument the value of the 'interface' variable defined in
    # the form on /network/index.html.
    def wireless(self, interface=None):
        logging.debug("Entered NetworkConfiguration.wireless().")

        # Store the name of the network interface chosen by the user in the
        # object's attribute set and then generate the name of the client
        # interface.
        self.mesh_interface = interface
        self.client_interface = interface + ':1'

        # Default settings for /network/wireless.html page.
        channel = 3
        essid = 'Byzantium'

        # This is a hidden class attribute setting, used for sanity checking
        # later in the configuration process.
        self.frequency = frequencies[channel - 1]

        channel, essid, warning = _utils.check_for_configured_interface(self.netconfdb, interface, channel, essid)

        # The forms in the HTML template do everything here, as well.  This
        # method only accepts input for use later.
        try:
            page = self.templatelookup.get_template("/network/wireless.html")
            return page.render(title = "Configure wireless for Byzantium node.",
                           purpose_of_page = "Set wireless network parameters.",
                           warning = warning, interface = self.mesh_interface,
                           channel = channel, essid = essid)
        except:
            _utils.output_error_data()
    wireless.exposed = True

    def get_raw_interface(self, interface):
        return interface.rsplit(":",1)[0]

    def get_unused_ip(self, interface, addr, kind):
        """docstring for get_unused_ip"""
        ip_in_use = 1
        interface = self.get_raw_interface(interface)
        while ip_in_use:
            # Run arping to see if any node in range has claimed that IP address
            # and capture the return code.
            # Argument breakdown:
            # -c 5: Send 5 packets
            # -D: Detect specified address.  Return 1 if found, 0 if not,
            # -f: Stop after the first positive response.
            # -I Network interface to use.  Mandatory.
            arping = ['/sbin/arping', '-c 5', '-D', '-f', '-q', '-I',
                      interface, addr]
            if self.test:
                logging.debug("NetworkConfiguration.tcpip() command to probe for a %s interface IP address is %s", kind, ' '.join(arping))
                time.sleep(5)
            else:
                ip_in_use = subprocess.call(arping)

            # arping returns 1 if the IP is in use, 0 if it's not.
            if not ip_in_use:
                logging.debug("IP address of %s interface is %s.", kind, addr)
                return addr
                
            # In test mode, don't let this turn into an endless loop.
            if self.test:
                logging.debug("Breaking out of this loop to exercise the rest of the code.")
                break

    def update_mesh_interface_status(self, status):
        """docstring for update_mesh_interface_status"""
        logging.debug("Setting wireless interface status: %s", status)
        command = ['/sbin/ifconfig', self.mesh_interface, status]
        if self.test:
            logging.debug("NetworkConfiguration.tcpip() command to update mesh interface status: %s", command)
        else:
            subprocess.Popen(command)

    # Implements step two of the interface configuration process: selecting
    # IP address blocks for the mesh and client interfaces.  Draws upon class
    # attributes where they exist but pseudorandomly chooses values where it
    # needs to.
    def tcpip(self, essid=None, channel=None):
        logging.debug("Entered NetworkConfiguration.tcpip().")

        # Store the ESSID and wireless channel in the class' attribute set if
        # they were passed as args.
        if essid:
            self.essid = essid
        if channel:
            self.channel = channel

        # Initialize the Python environment's randomizer.
        random.seed()

        # Connect to the network configuration database.
        connection = sqlite3.connect(self.netconfdb)
        cursor = connection.cursor()

        # To run arping, the interface has to be up.  Check the database to
        # see if it's up, and if not flip it on for a few seconds to test.
        template = (self.mesh_interface, 'yes', )
        cursor.execute("SELECT mesh_interface, enabled FROM wireless WHERE mesh_interface=? AND enabled=?;", template)
        result = cursor.fetchall()
        if not result:
            self.update_mesh_interface_status('up')

            # Sleep five seconds to give the hardware a chance to catch up.
            time.sleep(5)

        # First pick an IP address for the mesh interface on the node.
        # Go into a loop in which pseudorandom IP addresses are chosen and
        # tested to see if they have been taken already or not.  Loop until we
        # have a winner.
        logging.debug("Probing for an IP address for the mesh interface.")
        # Pick a random IP address in a 192.168/24.
        addr = '192.168.'
        addr = addr + str(random.randint(0, 254)) + '.'
        addr = addr + str(random.randint(1, 254))
        self.mesh_ip = self.get_unused_ip(self.mesh_interface, addr, kind="mesh")
    
        # Next pick a distinct IP address for the client interface and its
        # netblock.  This is potentially trickier depending on how large the
        # mesh gets.
        logging.debug("Probing for an IP address for the client interface.")
        # Pick a random IP address in a 10/24.
        addr = '10.'
        addr = addr + str(random.randint(0, 254)) + '.'
        addr = addr + str(random.randint(0, 254)) + '.1'
        self.mesh_ip = self.get_unused_ip(self.client_interface, addr, kind="client")

        # For testing, hardcode some IP addresses so the rest of the code has
        # something to work with.
        if self.test:
            self.mesh_ip = '192.168.1.1'
            self.client_ip = '10.0.0.1'

        # Deactivate the interface as if it was down to begin with.
        if not result:
            self.update_mesh_interface_status('down')

        # Close the database connection.
        connection.close()

        # Run the "Are you sure?" page through the template interpeter.
        try:
            page = self.templatelookup.get_template("/network/confirm.html")
            return page.render(title = "Confirm network address for interface.",
                               purpose_of_page = "Confirm IP configuration.",
                               interface = self.mesh_interface,
                               mesh_ip = self.mesh_ip,
                               mesh_netmask = self.mesh_netmask,
                               client_ip = self.client_ip,
                               client_netmask = self.client_netmask)
        except:
            _utils.output_error_data()
    tcpip.exposed = True

    # Configure the network interface.
    def set_ip(self):
        logging.debug("Entered NetworkConfiguration.set_ip().")

        # Set up the error catcher variable.
        error = []

        # Define the PID of the captive portal daemon in the topmost context
        # of this method.
        portal_pid = 0

        # If we've made it this far, the user's decided to (re)configure a
        # network interface.  Full steam ahead, damn the torpedoes!
        # First, take the wireless NIC offline so its mode can be changed.
        self.update_mesh_interface_status('down')
        time.sleep(5)

        # Wrap this whole process in a loop to ensure that stubborn wireless
        # interfaces are configured reliably.  The wireless NIC has to make it
        # all the way through one iteration of the loop without errors before
        # we can go on.
        while True:
            logging.debug("At top of wireless configuration loop.")

            chunks = {"mode": ("mode", "ad-hoc"),
                      "ESSID": ("essid", self.essid),
                      "BSSID": ("ap", self.bssid),
                      "channel": ("channel", self.channel)}
            for k, v in chunks.iteritems():
                logging.debug("Configuring wireless interface: %s = %s", k, v)
                command = ['/sbin/iwconfig', self.mesh_interface]
                command.extend(v)
                if self.test:
                    logging.debug("NetworkConfiguration.set_ip() command to set the %s: %s", k, ' '.join(command))
                else:
                    subprocess.Popen(command)
                    time.sleep(1)

            # Run iwconfig again and capture the current wireless configuration.
            command = ['/sbin/iwconfig', self.mesh_interface]
            configuration = ''
            if self.test:
                logging.debug("NetworkConfiguration.set_ip()command to capture the current state of a network interface: %s", command)
            else:
                output = subprocess.Popen(command, stdout=subprocess.PIPE).stdout
                configuration = output.readlines()

            break_flag = False
            # Test the interface by going through the captured text to see if
            # it's in ad-hoc mode.  If it's not, go back to the top of the
            # loop to try again.
            for line in configuration:
                if re.search("Mode|ESSID|Cell|Frequency", line):
                    line = line.split(' ')
                else:
                    continue

                if 'Mode' in line:
                    mode = line[0].split(':')[1]
                    if mode != 'Ad-Hoc':
                        logging.debug("Uh-oh!  Not in ad-hoc mode!  Starting over.")
                        break_flag = True
                        break

                # Test the ESSID to see if it's been set properly.
                if 'ESSID' in line:
                    essid = line[-1].split(':')[1]
                    if essid != self.essid:
                        logging.debug("Uh-oh!  ESSID wasn't set!  Starting over.")
                        break_flag = True
                        break

                # Test the BSSID to see if it's been set properly.
                if 'Cell' in line:
                    bssid = line[-1]
                    if bssid != self.bssid:
                        logging.debug("Uh-oh!  BSSID wasn't set!  Starting over.")
                        break_flag = True
                        break

                # Check the wireless channel to see if it's been set properly.
                if 'Frequency' in line:
                    frequency = line[2].split(':')[1]
                    if frequency != self.frequency:
                        logging.debug("Uh-oh!  Wireless channel wasn't set!  starting over.")
                        break_flag = True
                        break

            logging.debug("Hit bottom of the wireless configuration loop.")

            # For the purpose of testing, exit after one iteration so we don't
            # get stuck in an infinite loop.
            if self.test:
                break

            # "Victory is mine!"
            #     --Stewie, _Family Guy_
            if not(break_flag):
                break

        logging.debug("Wireless interface configured successfully.")

        # Call ifconfig and set up the network configuration information.
        logging.debug("Setting IP configuration information on wireless interface.")
        command = ['/sbin/ifconfig', self.mesh_interface, self.mesh_ip,
                   'netmask', self.mesh_netmask, 'up']
        if self.test:
            logging.debug("NetworkConfiguration.set_ip()command to set the IP configuration of the mesh interface: %s", command)
        else:
            subprocess.Popen(command)
        time.sleep(5)

        # Add the client interface.
        logging.debug("Adding client interface.")
        command = ['/sbin/ifconfig', self.client_interface, self.client_ip, 'up']
        if self.test:
            logging.debug("NetworkConfiguration.set_ip()command to set the IP configuration of the client interface: %s", command)
        else:
            subprocess.Popen(command)

        template = ('yes', self.channel, self.essid, self.mesh_interface, self.client_interface, self.mesh_interface)
        _utils.set_wireless_db_entry(self.netconfdb, template)

        # Start the captive portal daemon.  This will also initialize the IP
        # tables ruleset for the client interface.
        logging.debug("Starting captive portal daemon.")
        captive_portal_daemon = ['/usr/local/sbin/captive_portal.py', '-i',
                                 str(self.mesh_interface), '-a', self.client_ip,
                                 '-d' ]
        captive_portal_return = 0
        if self.test:
            logging.debug("NetworkConfiguration.set_ip() command to start the captive portal daemon: %s", captive_portal_daemon)
            captive_portal_return = 6
        else:
            captive_portal_return = subprocess.Popen(captive_portal_daemon)
        logging.debug("Sleeping for 5 seconds to see if a race condition is the reason we can't get the PID of the captive portal daemon.")
        time.sleep(5)

        # Now do some error checking.
        warnings = "<p>WARNING!  captive_portal.py exited with code %d - %s!</p>\n"
        if captive_portal_return == 1:
            error.append(warnings % (captive_portal_return, "insufficient command line arguments passed to daemon"))
        elif captive_portal_return == 2:
            error.append(warnings % (captive_portal_return, "bad arguments passed to daemon"))
        elif captive_portal_return == 3:
            error.append(warnings % (captive_portal_return, "bad IP tables commands during firewall initialization"))
        elif captive_portal_return == 4:
            error.append(warnings % (captive_portal_return, "bad parameters passed to IP tables"))
        elif captive_portal_return == 5:
            error.append(warnings % (captive_portal_return, "daemon already running on interface"))
        elif captive_portal_return == 6:
            error.append("<p>NOTICE: captive_portal.py started in TEST mode - did not actually start up!</p>\n")
        else:
            logging.debug("Getting PID of captive portal daemon.")

            # If the captive portal daemon started successfully, get its PID.
            # Note that we have to take into account both regular and test mode.
            captive_portal_pidfile = 'captive_portal.' + self.mesh_interface

            if os.path.exists('/var/run/' + captive_portal_pidfile):
                captive_portal_pidfile = '/var/run/' + captive_portal_pidfile
            elif os.path.exists('/tmp/' + captive_portal_pidfile):
                captive_portal_pidfile = '/tmp/' + captive_portal_pidfile
            else:
                error.append("<p>WARNING: Unable to open captive portal PID file " + captive_portal_pidfile + "</p>\n")
                logging.debug("Unable to find PID file %s of captive portal daemon.", captive_portal_pidfile)

            # Try to open the PID file.
            logging.debug("Trying to open %s.", captive_portal_pidfile)
            portal_pid = 0
            try:
                pidfile = open(str(captive_portal_pidfile), 'r')
                portal_pid = pidfile.readline()
                pidfile.close()
            except:
                error.append("<p>WARNING: Unable to open captive portal PID file " + captive_portal_pidfile + "</p>\n")

            logging.debug("value of portal_pid is %s.", portal_pid)
            if self.test:
                logging.debug("Faking PID of captive_portal.py.")
                portal_pid = "Insert clever PID for captive_portal.py here."

            if not portal_pid:
                portal_pid = "ERROR: captive_portal.py failed, returned code " + str(captive_portal_return) + "."
                logging.debug("Captive portal daemon failed to start.  Exited with code %s.", str(captive_portal_return))

        # Send this information to the methods that write the /etc/hosts and
        # dnsmasq config files.
        logging.debug("Generating dnsmasq configuration files.")

        problem = make_hosts(self.hosts_file, self.test, starting_ip=self.client_ip)
        if problem:
            error.append("<p>WARNING!  /etc/hosts.mesh not generated!  Something went wrong!</p>")
            logging.debug("Couldn't generate /etc/hosts.mesh!")
        configure_dnsmasq(self.dnsmasq_include_file, self.test, starting_ip=self.client_ip)

        # Render and display the page.
        try:
            page = self.templatelookup.get_template("/network/done.html")
            return page.render(title = "Network interface configured.",
                               purpose_of_page = "Configured!",
                               error = ''.join(error), interface = self.mesh_interface,
                               ip_address = self.mesh_ip,
                               netmask = self.mesh_netmask,
                               portal_pid = portal_pid,
                               client_ip = self.client_ip,
                               client_netmask = self.client_netmask)
        except:
            _utils.output_error_data()
    set_ip.exposed = True


########NEW FILE########
__FILENAME__ = networktraffic
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# networktraffic.py - Web application that displays the rrdtool traffic
#    graphs, so that the node's administrator can see how active their node is.

# Project Byzantium: http://wiki.hacdc.org/index.php/Byzantium
# License: GPLv3

# Import modules.
import logging
import os


# Classes.
# This class implements the network traffic status report page.
class NetworkTraffic(object):
    # Pretends to be index.html.
    
    def __init__(self, filedir, templatelookup):
        self.filedir = filedir
        self.templatelookup = templatelookup
    
    def index(self):
        # Enumerate the list of PNG files in the graphs/ directory and generate
        # a sequence of IMG SRCs to insert into the HTML template.
        graphdir = os.path.join(self.filedir,"graphs")
        try:
          images = os.listdir(graphdir)
        except OSError as ex:
          logging.error("Couldn't find images: %s" % ex)
          images = []

        # Pack the string of IMG SRCs into a string.
        graphs = ""
        for image in images:
            graphs = graphs + '<img src="/graphs/' + image + '" width="75%"' + 'height="75%" alt="' + image + '" /><br />'

        page = self.templatelookup.get_template("/traffic/index.html")
        return page.render(graphs = graphs,
                           title = "Byzantium Network Traffic Report",
                           purpose_of_page = "Traffic Graphs")
    index.exposed = True

########NEW FILE########
__FILENAME__ = services
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# services.py - Lets the user start and stop web applications and daemons
#    running on their Byzantium node.

# Project Byzantium: http://wiki.hacdc.org/index.php/Byzantium
# License: GPLv3

# TODO:
# - List the initscripts in a config file to make them easier to edit?
# - Come up with a method for determining whether or not a system service was
#   successfully deactivated.  Not all services have initscripts, and of those
#   that do, not all of them put PID files in /var/run/<nameofapp>.pid.

# Import external modules.
from mako import exceptions

import logging
import sqlite3
import subprocess

import _utils


# Classes.
# Allows the user to configure to configure mesh networking on wireless network
# interfaces.
class Services(object):
    
    def __init__(self, templatelookup, test):
        self.templatelookup = templatelookup
        self.test = test
    
        # Database used to store states of services and webapps.
        
        if self.test:
            self.servicedb = 'var/db/controlpanel/services.sqlite'
        else:
            self.servicedb = '/var/db/controlpanel/services.sqlite'
            # self.servicedb = '/home/drwho/services.sqlite'

        # Static class attributes.
        self.pid = '/var/run/httpd/httpd.pid'

        # These attributes will be used as scratch variables to keep from running
        # the same SQL queries over and over again.
        self.app = ''
        self.status = ''
        self.initscript = ''

    def generate_rows(self, results, kind):
        # Set up the opening tag of the table.
        row = '<tr>'

        # Roll through the list returned by the SQL query.
        for (name, status) in results:
            # Set up the first cell in the row, the name of the webapp.
            if status == 'active':
                # White on green means that it's active.
                row += "<td style='background-color:green; color:white;' >%s</td>" % name
            else:
                # White on red means that it's not active.
                row += "<td style='background-color:red; color:white;' >%s</td>" % name

            # Set up the second cell in the row, the toggle that will either
            # turn the web app off or on.
            if status == 'active':
                # Give the option to deactivate the app.
                row += "<td><button type='submit' name='%s' value='%s' style='background-color:red; color:white;' >Deactivate</button></td>" % (kind, name)
            else:
                # Give the option to activate the app.
                row += "<td><button type='submit' name='%s' value='%s' style='background-color:green; color:white;' >Activate</button></td>" % (kind, name)

            # Set the closing tag of the row.
            row += "</tr>\n"

        # Add that row to the buffer of HTML for the webapp table.
        return row

    # Pretends to be index.html.
    def index(self):
        # Set up the strings that will hold the HTML for the tables on this
        # page.
        webapps = ''
        systemservices = ''

        # Set up access to the system services database.  We're going to need
        # to read successive lines from it to build the HTML tables.
        error = ''
        connection = sqlite3.connect(self.servicedb)
        cursor = connection.cursor()

        # Use the contents of the services.webapps table to build an HTML table
        # of buttons that are either go/no-go indicators.  It's a bit
        # complicated, so I'll break it into smaller pieces.
        cursor.execute("SELECT name, status FROM webapps;")
        results = cursor.fetchall()
        if not results:
            # Display an error page that says that something went wrong.
            error = "<p>ERROR: Something went wrong in database %s, table webapps.  SELECT query failed.</p>" % self.servicedb
        else:
            webapps = self.generate_rows(results, 'app')

        # Do the same thing for system services.
        cursor.execute("SELECT name, status FROM daemons;")
        results = cursor.fetchall()
        if not results:
            # Display an error page that says that something went wrong.
            error = "<p>ERROR: Something went wrong in database %s, table daemons.  SELECT query failed.</p>" % self.servicedb
        else:
            systemservices = self.generate_rows(results, 'service')

        # Gracefully detach the system services database.
        cursor.close()

        # Render the HTML page.
        try:
            page = self.templatelookup.get_template("/services/index.html")
            return page.render(title = "Byzantium Node Services",
                               purpose_of_page = "Manipulate services",
                               error = error, webapps = webapps,
                               systemservices = systemservices)
        except:
            # Holy crap, this is a better exception analysis method than the
            # one above, because it actually prints useful information to the
            # web browser, rather than forcing you to figure it out from stderr.
            # I might have to start using this more.
            return exceptions.html_error_template().render()
    index.exposed = True

    # Handler for changing the state of a web app.  This method is only called
    # when the user wants to toggle the state of the app, so it looks in the
    # configuration database and switches 'enabled' to 'disabled' or vice versa
    # depending on what it finds.
    def webapps(self, app=None):
        # Save the name of the app in a class attribute to save effort later.
        self.app = app

        query = "SELECT name, status FROM webapps WHERE name=?;"
        template = (self.app, )
        _, cursor = _utils.execute_query(self.servicedb, query, template=template)
        result = cursor.fetchall()
        status = result[0][1]

        # Save the status of the app in another class attribute for later.
        self.status = status

        # Determine what to do.
        if status == 'active':
            action = 'deactivate'
            warning = 'This will deactivate the application!'
        else:
            action = 'activate'
            warning = 'This will activate the application!'

        # Close the connection to the database.
        cursor.close()

        # Display to the user the page that asks them if they really want to
        # shut down that app.
        try:
            page = self.templatelookup.get_template("/services/webapp.html")
            return page.render(title = "Byzantium Node Services",
                               purpose_of_page = (action + " service"),
                               app = app, action = action, warning = warning)
        except:
            return exceptions.html_error_template().render()
    webapps.exposed = True

    # The method that updates the services.sqlite database to flag a given web
    # application as accessible to mesh users or not.  Takes one argument, the
    # name of the app.
    def toggle_webapp(self, action=None):
        # Set up a generic error catching variable for this page.
        error = ''

        if action == 'activate':
            status = 'active'
            action = 'activated'
        else:
            status = 'disabled'
            action = 'deactivated'

        query = "UPDATE webapps SET status=? WHERE name=?;"
        template = template = (status, self.app, )
        database, cursor = _utils.execute_query(self.servicedb, query, template=template)
        database.commit()
        cursor.close()

        # Render the HTML page and send it to the browser.
        try:
            page = self.templatelookup.get_template("/services/toggled.html")
            return page.render(title = "Byzantium Node Services",
                               purpose_of_page = "Service toggled.",
                               error = error, app = self.app,
                               action = action)
        except:
            return exceptions.html_error_template().render()
    toggle_webapp.exposed = True

    # Handler for changing the state of a system service.  This method is also
    # only called when the user wants to toggle the state of the app, so it
    # looks in the configuration database and switches 'enabled' to 'disabled'
    # or vice versa depending on what it finds.
    def services(self, service=None):
        # Save the name of the app in a class attribute to save effort later.
        self.app = service

        query = "SELECT name, status, initscript FROM daemons WHERE name=?;"
        template = (service, )
        _, cursor = _utils.execute_query(self.servicedb, query, template=template)
        result = cursor.fetchall()
        status = result[0][1]
        initscript = result[0][2]

        # Save the status of the app and the initscript in class attributes for
        # later use.
        self.status = status
        self.initscript = initscript

        # Figure out what to do.
        if status == 'active':
            action = 'deactivate'
            warning = 'This will deactivate the application!'
        else:
            action = 'activate'
            warning = 'This will activate the application!'

        # Close the connection to the database.
        cursor.close()

        # Display to the user the page that asks them if they really want to
        # shut down that app.
        try:
            page = self.templatelookup.get_template("/services/services.html")
            return page.render(title = "Byzantium Node Services",
                               purpose_of_page = (action + " service"),
                               action = action, app = service, warning = warning)
        except:
            return exceptions.html_error_template().render()
    services.exposed = True

    # The method that does the actual work of running initscripts located in
    # /etc/rc.d and starting or stopping system services.  Takes one argument,
    # the name of the app.  This should never be called from anywhere other than
    # Services.services().
    def toggle_service(self, action=None):
        # Set up an error handling variable just in case.
        error = ''
        query = "SELECT name, initscript FROM daemons WHERE name=?;"
        template = template = (self.app, )
        database, cursor = _utils.execute_query(self.servicedb, query, template=template)
        results = cursor.fetchall()
        self.initscript = results[0][1]

        if action == 'activate':
            status = 'active'
        else:
            status = 'disabled'

        # Construct the command line ahead of time to make the code a bit
        # simpler in the long run.
        initscript = '/etc/rc.d/' + self.initscript
        if self.status == 'active':
            if self.test:
                logging.debug('Would run "%s stop" here.' % initscript)
            else:
                subprocess.Popen([initscript, 'stop'])
        else:
            if self.test:
                logging.debug('Would run "%s start" here.' % initscript)
            else:
                subprocess.Popen([initscript, 'start'])

        # Update the status of the service in the database.
        template = (status, self.app, )
        cursor.execute("UPDATE daemons SET status=? WHERE name=?;", template)
        database.commit()
        cursor.close()

        # Render the HTML page and send it to the browser.
        try:
            page = self.templatelookup.get_template("/services/toggled.html")
            return page.render(title = "Byzantium Node Services",
                               purpose_of_page = "Service toggled.",
                               app = self.app, action = action, error = error)
        except:
            return exceptions.html_error_template().render()
    toggle_service.exposed = True

########NEW FILE########
__FILENAME__ = status
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# status.py - Implements the status screen of the Byzantium control panel.
#    Relies on a few other things running under the hood that are independent
#    of the control panel.  By default, this comprises the /index.html part of
#    the web app.

# Project Byzantium: http://wiki.hacdc.org/index.php/Byzantium
# License: GPLv3

# Import modules.
import logging
import os
import os.path
import sqlite3
import subprocess

# Import control panel modules.
# from control_panel import *
from networktraffic import NetworkTraffic
from networkconfiguration import NetworkConfiguration
from meshconfiguration import MeshConfiguration
from services import Services
from gateways import Gateways


# Query the node's uptime (in seconds) from the OS.
def get_uptime(injected_open=open):
    # Open /proc/uptime.
    try:
        uptime = injected_open("/proc/uptime", "r")
    except IOError:
        # Can't find file
        return False

    system_uptime = uptime.readline()

    # Separate the uptime from the idle time.
    node_uptime = system_uptime.split()[0]

    # Cleanup.
    uptime.close()

    # Return the system uptime (in seconds).
    return node_uptime


# Queries the OS to get the system load stats.
def get_load(injected_open=open):
    # Open /proc/loadavg.
    try:
        loadavg = injected_open("/proc/loadavg", "r")
    except IOError:
        return False

    loadstring = loadavg.readline()
    # Extract the load averages from the string.
    averages = loadstring.split(' ')
    loadavg.close()
    # check to avoid errors
    if len(averages) < 3:
        print('WARNING: /proc/loadavg is not formatted as expected')
        return False

    # Return the load average values.
    return (averages[:3])


# Queries the OS to get the system memory usage stats.
def get_memory(injected_open=open):
    memtotal = 0
    memused = 0
    # Open /proc/meminfo.
    try:
        meminfo = injected_open("/proc/meminfo", "r")
    except IOError:
        return False

    # Read in the contents of that virtual file.  Put them into a dictionary
    # to make it easy to pick out what we want.  If this can't be done,
    # return nothing and let the default values handle it.
    for line in meminfo:
        # Homoginize the data.
        line = line.strip().lower()
        # Figure out how much RAM and swap are in use right now
        try:
            if line.startswith('memtotal'):
                memtotal = int(line.split()[1])
            elif line.startswith('memfree'):
                memfree = int(line.split()[1])
            # break out early
            if bool(memtotal) and bool(memused):
                break
        except KeyError as ex:
            print(ex)
            print('WARNING: /proc/meminfo is not formatted as expected')
            return False
    memused = memtotal - memfree

    # Return total RAM, RAM used, total swap space, swap space used.
    return (memtotal, memused)


def get_ip_address(interface):
    ip_address = ''
    command = ['/sbin/ifconfig', interface]
    output = subprocess.Popen(command, stdout=subprocess.PIPE).stdout
    configuration = output.readlines()
    logging.debug("Output of ifconfig:")
    logging.debug(configuration)

    # Parse the output of ifconfig.
    for line in configuration:
        if 'inet addr' in line:
            line = line.strip()
            ip_address = line.split(' ')[1].split(':')[1]
            logging.debug("IP address is %s", ip_address)
    return ip_address

# The Status class implements the system status report page that makes up
# /index.html.
class Status(object):

    def __init__(self, templatelookup, test, filedir):
        self.templatelookup = templatelookup
        self.test = test
        # Allocate objects for all of the control panel's main features.
        self.traffic = NetworkTraffic(filedir, templatelookup)
        self.network = NetworkConfiguration(templatelookup, test)
        self.mesh = MeshConfiguration(templatelookup, test)
        self.services = Services(templatelookup, test)
        self.gateways = Gateways(templatelookup, test)

        # Location of the network.sqlite database, which holds the configuration
        # of every network interface in the node.
        if test:
            # self.netconfdb = '/home/drwho/network.sqlite'
            self.netconfdb = 'var/db/controlpanel/network.sqlite'
            logging.debug("Location of NetworkConfiguration.netconfdb: %s", self.netconfdb)
        else:
            self.netconfdb = '/var/db/controlpanel/network.sqlite'

    # Pretends to be index.html.
    def index(self):
        logging.debug("Entered Status.index().")
        
        # Get the node's uptime from the OS.
        uptime = get_uptime() or 0

        # Convert the uptime in seconds into something human readable.
        (minutes, seconds) = divmod(float(uptime), 60)
        (hours, minutes) = divmod(minutes, 60)
        uptime = "%i hours, %i minutes, %i seconds" % (hours, minutes, seconds)
        logging.debug("System uptime: %s", uptime)

        # Get the amount of RAM in and in use by the system.
        ram, ram_used = get_memory()
        logging.debug("Total RAM: %s", ram)
        logging.debug("RAM in use: %s", ram_used)

        # For the purposes of debugging, test to see if the network
        # configuration database file exists and print a tell to the console.
        logging.debug("Checking for existence of network configuration database.")
        if os.path.exists(self.netconfdb):
            logging.debug("Network configuration database %s found.", self.netconfdb)
        else:
            logging.debug("DEBUG: Network configuration database %s NOT found!", self.netconfdb)

        # Pull a list of the mesh interfaces on this system out of the network
        # configuration database.  If none are found, report none.
        mesh_interfaces = ''
        ip_address = ''

        connection = sqlite3.connect(self.netconfdb)
        cursor = connection.cursor()
        query = "SELECT mesh_interface, essid, channel FROM wireless;"
        cursor.execute(query)
        result = cursor.fetchall()

        if not result:
            # Fields:
            #    interface, IP, ESSID, channel
            mesh_interfaces = "<tr><td>n/a</td>\n<td>n/a</td>\n<td>n/a</td>\n<td>n/a</td></tr>\n"
        else:
            for (mesh_interface, essid, channel) in result:
                # Test to see if any of the variables retrieved from the
                # database are empty, and if they are set them to obviously
                # non-good but also non-null values.
                if not mesh_interface:
                    logging.debug("Value of mesh_interface is empty.")
                    mesh_interface = ' '
                if not essid:
                    logging.debug("Value of ESSID is empty.")
                    essid = ' '
                if not channel:
                    logging.debug("Value of channel is empty.")
                    channel = 0

                # For every mesh interface found in the database, get its
                # current IP address with ifconfig.
                command = ['/sbin/ifconfig', mesh_interface]
                if self.test:
                    print "TEST: Status.index() command to pull the configuration of a mesh interface:"
                    print '/sbin/ifconfig' + mesh_interface
                else:
                    logging.debug("Running ifconfig to collect configuration of interface %s.", mesh_interface)

                    ip_address = get_ip_address(mesh_interface)

                # Assemble the HTML for the status page using the mesh
                # interface configuration data.
                mesh_interfaces = mesh_interfaces + "<tr><td>" + mesh_interface + "</td>\n<td>" + ip_address + "</td>\n<td>" + essid + "</td>\n<td>" + str(channel) + "</td></tr>\n"

        # Pull a list of the client interfaces on this system.  If none are
        # found, report none.
        client_interfaces = ''
        ip_address = ''
        number_of_clients = 0

        query = "SELECT client_interface FROM wireless;"
        cursor.execute(query)
        result = cursor.fetchall()

        if not result:
            # Fields:
            #    interface, IP, active clients
            client_interfaces = "<tr><td>n/a</td>\n<td>n/a</td>\n<td>0</td></tr>\n"
        else:
            for client_interface in result:
                # For every client interface found, run ifconfig and pull
                # its configuration information.
                if self.test:
                    print "TEST: Status.index() command to pull the configuration of a client interface:"
                    print '/sbin/ifconfig' + client_interface[0]
                else:
                    logging.debug("Running ifconfig to collect configuration of interface %s.", client_interface)
                    ip_address = get_ip_address(client_interface[0])

                # For each client interface, count the number of rows in its
                # associated arp table to count the number of clients currently
                # associated.  Note that one has to be subtracted from the
                # count of rows to account for the line of column headers.
                command = ['/sbin/arp', '-n', '-i', client_interface[0]]
                if self.test:
                    print "TEST: Status.index() command to dump the ARP table of interface %s: " % client_interface
                    print command
                else:
                    logging.debug("Running arp to dump the ARP table of client interface %s.", client_interface)
                    output = subprocess.Popen(command, stdout=subprocess.PIPE).stdout
                    arp_table = output.readlines()
                    logging.debug("Contents of ARP table:")
                    logging.debug(arp_table)

                    # Count the number of clients associated with the client
                    # interface by analyzing the ARP table.
                    number_of_clients = len(arp_table) - 1
                    logging.debug("Number of associated clients: %i", number_of_clients)

                # Assemble the HTML for the status page using the mesh
                # interface configuration data.
                client_interfaces = client_interfaces + "<tr><td>" + client_interface[0] + "</td>\n<td>" + ip_address + "</td>\n<td>" + str(number_of_clients) + "</td></tr>\n"

        # Render the HTML page and return to the client.
        cursor.close()
        page = self.templatelookup.get_template("index.html")
        return page.render(ram_used = ram_used, ram = ram, uptime = uptime,
                           mesh_interfaces = mesh_interfaces,
                           client_interfaces = client_interfaces,
                           title = "Byzantium Mesh Node Status",
                           purpose_of_page = "System Status")
    index.exposed = True






########NEW FILE########
__FILENAME__ = status_test
#!/usr/bin/env python

# Project Byzantium: http://wiki.hacdc.org/index.php/Byzantium
# License: GPLv3

# captive_portal_test.py

from flexmock import flexmock  # http://has207.github.com/flexmock
import unittest
import status
import subprocess
import sys


class StatusHelpersTest(unittest.TestCase):

    def _raise_ioerror(self, x, y):
        raise IOError()

    def test_get_uptime_returns_false_on_ioerror(self):
        self.assertFalse(status.get_uptime(injected_open=self._raise_ioerror))

    def test_get_uptime_succeeds(self):
        mock = flexmock()
        mock.should_receive('readline').once.and_return('16544251.37 3317189.25\n')
        mock.should_receive('close').once
        self.assertEqual('16544251.37', status.get_uptime(injected_open=lambda x, y: mock))

    def test_get_load_returns_false_on_ioerror(self):
        self.assertFalse(status.get_load(injected_open=self._raise_ioerror))

    def test_get_load_returns_false_with_bad_formatting(self):
        mock = flexmock()
        mock.should_receive('readline').once.and_return('12345 6789\n')
        mock.should_receive('close').once
        self.assertFalse(status.get_load(injected_open=lambda x, y: mock))

    def test_get_load_succeeds(self):
        mock = flexmock()
        mock.should_receive('readline').once.and_return('0.00 0.01 0.05 1/231 11054\n')
        mock.should_receive('close').once
        expected = ['0.00', '0.01', '0.05']
        self.assertEqual(expected, status.get_load(injected_open=lambda x, y: mock))

    def test_get_memory_returns_false_on_ioerror(self):
        self.assertFalse(status.get_load(injected_open=self._raise_ioerror))

    def test_get_memory_succeds(self):
        mem = ['MemTotal:         509424 kB',
               'MemFree:           60232 kB',
               'Buffers:           98136 kB']
        expected = (509424, 449192)
        self.assertEqual(expected, status.get_memory(injected_open=lambda x, y: mem))

    def test_get_ip_address(self):
        out = ['eth0      Link encap:Ethernet  HWaddr ff:ff:ff:ff:ff:ff\n',
               '          inet addr:12.12.12.12  Bcast:12.12.12.255  Mask:255.255.255.0\n',
               '          inet6 addr: ffff::ffff:ffff:ffff:ffff/64 Scope:Link\n']
        mockfile = flexmock(readlines=lambda: out)
        mock = flexmock(stdout=mockfile)
        flexmock(subprocess).should_receive('Popen').once.and_return(mock)
        self.assertEqual('12.12.12.12', status.get_ip_address('eth0'))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = _utils
from mako.exceptions import RichTraceback

import logging
import sqlite3

def debug(message,level = '1'):
    import os
    _debug = ('BYZ_DEBUG' in os.environ)
    if _debug and os.environ['BYZ_DEBUG'] >= level:
        print(repr(message))

def file2str(file_name, mode = 'r'):
    fileobj = open(file_name,mode)
    filestr = fileobj.read()
    fileobj.close()
    return filestr

def str2file(string,file_name,mode = 'w'):
    fileobj = open(file_name,mode)
    fileobj.write(string)
    fileobj.close()

class Config(object):
    ''' Make me read from a file '''
    def __init__(self):
        self.services_cache = '/tmp/byz_services.json'
        self.service_template = '/etc/byzantium/services/avahi/template.service'
        self.services_store_dir = '/etc/avahi/inactive'
        self.services_live_dir = '/etc/avahi/services'

def execute_query(db, query, template=None):
    """docstring for execute_query"""
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    if template:
        cursor.execute(query, template)
    else:
        cursor.execute(query)
    return connection, cursor

def check_for_configured_interface(netconfdb, interface, channel, essid):
    """docstring for check_for_configured_interface"""
    warning = ""

    # If a network interface is marked as configured in the database, pull
    # its settings and insert them into the page rather than displaying the
    # defaults.
    query = "SELECT enabled, channel, essid FROM wireless WHERE mesh_interface=?;"
    template = (interface, )
    connection, cursor = execute_query(netconfdb, query, template)
    result = cursor.fetchall()
    if result and (result[0][0] == 'yes'):
        channel = result[0][1]
        essid = result[0][2]
        warning = '<p>WARNING: This interface is already configured!  Changing it now will break the local mesh!  You can hit cancel now without changing anything!</p>'
    connection.close()
    return (channel, essid, warning)

def set_confdbs(test):
    if test:
        # self.netconfdb = '/home/drwho/network.sqlite'
        netconfdb = 'var/db/controlpanel/network.sqlite'
        logging.debug("Location of netconfdb: %s", netconfdb)
        # self.meshconfdb = '/home/drwho/mesh.sqlite'
        meshconfdb = 'var/db/controlpanel/mesh.sqlite'
        logging.debug("Location of meshconfdb: %s", meshconfdb)
    else:
        netconfdb = '/var/db/controlpanel/network.sqlite'
        meshconfdb = '/var/db/controlpanel/mesh.sqlite'
    return netconfdb, meshconfdb

def set_wireless_db_entry(netconfdb, template):
    """docstring for set_wireless_db_entry"""
    # Commit the interface's configuration to the database.
    connection = sqlite3.connect(netconfdb)
    cursor = connection.cursor()
    # Update the wireless table.
    cursor.execute("UPDATE wireless SET enabled=?, channel=?, essid=?, mesh_interface=?, client_interface=? WHERE mesh_interface=?;", template)
    connection.commit()
    cursor.close()

def output_error_data():
    traceback = RichTraceback()
    for filename, lineno, function, line in traceback.traceback:
        print '\n'
        print ('Error in file %s\n\tline %s\n\tfunction %s') % ((filename, lineno, function))
        print ('Execution died on line %s\n') % (line)
        print ('%s: %s') % ((str(traceback.error.__class__.__name__), traceback.error))

########NEW FILE########
__FILENAME__ = dnsserver
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

## {{{ http://code.activestate.com/recipes/491264/ (r4)
import socket

class DNSQuery:
    def __init__(self, data):
        self.data=data
        self.domain=''

        tipo = (ord(data[2]) >> 3) & 15   # Opcode bits
        if tipo == 0:                     # Standard query
            ini=12
            lon=ord(data[ini])
            while lon != 0:
                self.domain+=data[ini+1:ini+lon+1]+'.'
                ini+=lon+1
                lon=ord(data[ini])

    def response(self, ip):
        packet=''
        if self.domain:
            packet+=self.data[:2] + "\x81\x80"
            packet+=self.data[4:6] + self.data[4:6] + '\x00\x00\x00\x00'   # Questions and Answers Counts
            packet+=self.data[12:]                                         # Original Domain Name Question
            packet+='\xc0\x0c'                                             # Pointer to domain name
            packet+='\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'             # Response type, ttl and resource data length -> 4 bytes
            packet+=str.join('',map(lambda x: chr(int(x)), ip.split('.'))) # 4bytes of IP
        return packet

if __name__ == '__main__':
    ip='192.168.1.1'
    print 'DistDNS:: dom.query. 60 IN A %s' % ip
  
    udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udps.bind(('',53))
  
    try:
        while 1:
            data, addr = udps.recvfrom(1024)
            p=DNSQuery(data)
            udps.sendto(p.response(ip), addr)
            print 'Response: %s -> %s' % (p.domain, ip)
    except KeyboardInterrupt:
        print 'Finished'
        udps.close()
## end of http://code.activestate.com/recipes/491264/ }}}


########NEW FILE########
__FILENAME__ = powerdns
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

import sys

msg = '%s\t%s\t%s\t%s\t%s\t%s\n' # type qname   qclass  qtype   id  remote-ip-address

def output(data):

    sys.stdout.write(data)

def input():

    return sys.stdin.readline()

class PDNS:

    def __init__(self):

        self.db = records.Database('/etc/resolv.db')

        self.isaxfr = False

        self.gothelo = False

        while True:

            line = input()

            if self.gothelo and not line in (None, ''):

                output(self.handleinput(line))

            elif line == 'HELO\t1\n':

                output('OK\t\n')

                self.gothelo = True

            else:

                return 1

    def handleinput(line):

        line = line.split('\t')

        if line[0] == 'Q':

            return self.lookup(line)

        elif line[0] == 'AXFR':

            return self.axfr(line)

        elif line[0] == 'PING':

            pass

        elif line[0] == 'DATA':

            self.store(line)

        elif line[0] == 'END':

            pass

        elif line[0] == 'FAIL':

            pass

        else:

            return 'FAIL\t\n'

    def store(self,line):

        getmac(line[6])

        self.db.add({'ip': line[6],'name': line[1],'mac': macaddr,'type': line[3]})

    def lookup(self,line):

        self.db.check("type='%s', name='%s'")

    def axfr(self,line):

        output = ''

        self.db.check()

        for i in self.db:

            output += msg % ('DATA',i['name'],'IN',i['type'],str(i['ttl']),'1'+i['ip'])

        return output

########NEW FILE########
__FILENAME__ = records
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

import sqlite3

class Database:

    def __init__(self, dbfile):

        self.database = sqlite3.connect(dbfile) # can be :memory: to run db in memory

        self.db = self.database.cursor()

        if not os.path.isfile(dbfile):

            self.db.execute('create table hosts (ip text, name text, mac text, type text, ttl integer, ts integer)')

        self.database.commit()

    def add(self, vals):

        # check for record

        # do magic to remove old dups

        self.db.execute("insert into hosts values ('%s', '%s', '%s')" % (vals['ip'], vals['name'], vals['mac'], vals['type']) )

        self.database.commit()

    def del(self, cond):

      self.execute("delete from hosts where %s" % cond )

        self.database.commit()

    def check(self, name, rectype = 'A'):

        records = []

        rectype = rectype.upper()

        self.db.execute("select * from hosts where name = '%s' and type = '%s'" % (name, rectype) )

        for i in self.db:

            records.append(i)

        return records

    def close(self):

        self.database.close()

########NEW FILE########
__FILENAME__ = config
# qwebirc configuration file
#
# This a Python program that is imported, so feel free to use any
# Python here!
#
# Note that some changes to this configuration file require re-running
# compile.py and others require restarting qwebirc (and some require
# both!)
# If in doubt always re-compile and restart.

# The following line is required, don't remove it!
from qwebirc.config_options import *

# IRC OPTIONS
# ---------------------------------------------------------------------
#
# OPTION: IRCSERVER
#         Hostname (or IP address) of IRC server to connect to.
# OPTION: IRCPORT
#         Port of IRC server to connect to.
IRCSERVER, IRCPORT = "localhost", 6667

# OPTION: REALNAME
#         The realname field of IRC clients will be set to this value.
REALNAME = "Byzantium User"

# OPTION: IDENT
#        ident to use on irc, possible values include:
#        - a string, e.g. IDENT = "webchat"
#        - the literal value IDENT_HEX, this will set the ident to the
#          a hexadecimal version of the users IP address, e.g
#          IDENT = IDENT_HEX
#        - the literal value IDENT_NICKNAME, this will use the users
#          supplied nickname as their ident.
IDENT = "user"

# OPTION: OUTGOING_IP
#         The IP address to bind to when connecting to the IRC server.
#
#         This will not change the IP address that qwebirc listens on. 
#         You will need to call run.py with the --ip/-i option if you 
#         want that.
#OUTGOING_IP = "127.0.0.1"

# OPTION: WEBIRC_MODE
#         This option controls how the IP/hostname of the connecting
#         browser will be sent to IRC.
#
#         Possible values include:
#         - the string "webirc", i.e. WEBIRC_MODE = "webirc"
#           Use WEBIRC type blocks, with a server configuration of
#           the following style:
#
#           cgiirc {
#             type webirc;
#             hostname <qwebirc's ip address>;
#             password <password>;
#           };
#
#           Remember to set the WEBIRC_PASSWORD value to be the
#           same as <password>.
#         - the string "cgiirc", i.e. WEBIRC_MODE = "cgiirc"
#           old style CGIIRC command, set CGIIRC_STRING to be the
#           command used to set the ip/hostname, and set
#           WEBIRC_PASSWORD to be the password used in the server's
#           configuration file.
#         - the literal value None, i.e. WEBIRC_MODE = None
#           Send the IP and hostname in the realname field, overrides
#          the REALNAME option.
WEBIRC_MODE = "webirc"

# OPTION: WEBIRC_PASSWORD
#         Used for WEBIRC_MODE webirc and cgiirc, see WEBIRC_MODE
#         option documentation.
WEBIRC_PASSWORD = ""

# OPTION: CGIIRC_STRING
#         Command sent to IRC server in for cgiirc WEBIRC_MODE.
#         See WEBIRC_MODE option documentation.
#CGIIRC_STRING = "CGIIRC"


# OPTION: CHANNEL
#        The default channel what the user should join upon connect.
#        This will only apply when no channel parameters are specified
#        in the URI.
CHANNEL = "#byzantium"

# UI OPTIONS
# ---------------------------------------------------------------------
#
# OPTION: BASE_URL
#         URL that this qwebirc instance will be available at, add the
#         port number if your instance runs on a port other than 80.
BASE_URL = "http://localhost/"

# OPTION: NETWORK_NAME
#         The name of your IRC network, displayed throughout the
#         application.
NETWORK_NAME = "Byzantium Mesh"

# OPTION: APP_TITLE
#         The title of the application in the web browser.
APP_TITLE = NETWORK_NAME + " Chat"

# NICKNAME VALIDATION OPTIONS
# ---------------------------------------------------------------------
#
# OPTION: NICKNAME_VALIDATE
#         If True then user nicknames will be validated according to
#         the configuration below, otherwise they will be passed
#         directly to the ircd.
NICKNAME_VALIDATE = True

# OPTION: NICKNAME_VALID_FIRST_CHAR
#         A string containing valid characters for the first letter of
#         a nickname.
#         Default is as in RFC1459.
import string
NICKNAME_VALID_FIRST_CHAR = string.letters + "_[]{}`^\\|"

# OPTION: NICKNAME_VALID_SUBSEQUENT_CHAR
#         A string containing valid characters for the rest of the
#         nickname.
NICKNAME_VALID_SUBSEQUENT_CHARS = NICKNAME_VALID_FIRST_CHAR + string.digits + "-"

# OPTION: NICKNAME_MINIMUM_LENGTH
#         Minimum characters permitted in a nickname on your network.
NICKNAME_MINIMUM_LENGTH = 2

# OPTION: NICKNAME_MAXIMUM_LENGTH
#         Maximum characters permitted in a nickname on your network.
#         Ideally we'd extract this from the ircd, but we need to know
#         before we connect.
NICKNAME_MAXIMUM_LENGTH = 15

# FEEDBACK OPTIONS
# ---------------------------------------------------------------------
#
# These options control the feedback module, which allows users to
# send feedback directly from qwebirc (via email).
#
# OPTION: FEEDBACK_FROM
#         E-mail address that feedback will originate from.
#FEEDBACK_FROM = "moo@moo.com"

# OPTION: FEEDBACK_TO:
#         E-mail address that feedback will be sent to.
#FEEDBACK_TO = "moo@moo.com"

# OPTION: FEEDBACK_SMTP_HOST
#         Hostname/IP address of SMTP server feedback will be sent
#         through.
# OPTION: FEEDBACK_SMTP_PORT
#         Port of SMTP server feedback will be sent through.
#FEEDBACK_SMTP_HOST, FEEDBACK_SMTP_PORT = "127.0.0.1", 25

# ADMIN ENGINE OPTIONS
# ---------------------------------------------------------------------
#
# OPTION: ADMIN_ENGINE_HOSTS:
#         List of IP addresses to allow onto the admin engine at
#         http://instance/adminengine
ADMIN_ENGINE_HOSTS = ["127.0.0.1"]

# PROXY OPTIONS
# ---------------------------------------------------------------------
#
# OPTION: FORWARDED_FOR_HEADER
#         If you're using a proxy that passes through a forwarded-for
#         header set this option to the header name, also set
#         FORWARDED_FOR_IPS.
#FORWARDED_FOR_HEADER="x-forwarded-for"
 
# OPTION: FORWARDED_FOR_IPS
#         This option specifies the IP addresses that forwarded-for
#         headers will be accepted from.
#FORWARDED_FOR_IPS=["127.0.0.1"]

# EXECUTION OPTIONS
# ---------------------------------------------------------------------
#
# OPTION: ARGS (optional)
#         These arguments will be used as if qwebirc was run directly
#         with them, see run.py --help for a list of options.
#ARGS = "-n -p 3989"

# OPTION: SYSLOG_ADDR (optional)
#         Used in conjunction with util/syslog.py and -s option.
#         This option specifies the address and port that syslog
#         datagrams will be sent to.
#SYSLOG_ADDR = "127.0.0.1", 514

# TUNEABLE VALUES
# ---------------------------------------------------------------------
#
# You probably don't want to fiddle with these unless you really know
# what you're doing...

# OPTION: UPDATE_FREQ
#         Maximum rate (in seconds) at which updates will be propagated
#         to clients
UPDATE_FREQ = 1.0

# OPTION: MAXBUFLEN
#         Maximum client AJAX recieve buffer size (in bytes), if this
#         buffer size is exceeded then the client will be disconnected.
#         This value should match the client sendq size in your ircd's
#         configuration.
MAXBUFLEN = 100000

# OPTION: MAXSUBSCRIPTIONS
#         Maximum amount of 'subscriptions' to a specific AJAX channel,
#         i.e. an IRC connection.
#         In theory with a value greater than one you can connect more
#         than one web IRC client to the same IRC connection, ala
#         irssi-proxy.
MAXSUBSCRIPTIONS = 1

# OPTION: MAXLINELEN
#         If the client sends a line greater than MAXLINELEN (in bytes)
#         then they will be disconnected.
#         Note that IRC normally silently drops messages >=512 bytes.
MAXLINELEN = 600

# OPTION: DNS_TIMEOUT
#         DNS requests that do not respond within DNS_TIMEOUT seconds
#         will be cancelled.
DNS_TIMEOUT = 20

# OPTION: HTTP_AJAX_REQUEST_TIMEOUT
#         Connections made to the AJAX engine are closed after this
#         this many seconds.
#         Note that this value is intimately linked with the client
#         AJAX code at this time, changing it will result in bad
#         things happening.
HTTP_AJAX_REQUEST_TIMEOUT = 30

# OPTION: HTTP_REQUEST_TIMEOUT
#         Connections made to everything but the AJAX engine will
#         be closed after this many seconds, including connections
#         that haven't started/completed an HTTP request.
HTTP_REQUEST_TIMEOUT = 5

# OPTION: STATIC_BASE_URL
#         This value is used to build the URL for all static HTTP
#         requests.
#         You'd find this useful if you're running multiple qwebirc
#         instances on the same host.
STATIC_BASE_URL = ""

# OPTION: DYNAMIC_BASE_URL
#         This value is used to build the URL for all dynamic HTTP
#         requests.
#         You'd find this useful if you're running multiple qwebirc
#         instances on the same host.
DYNAMIC_BASE_URL = ""

# OPTION: CONNECTION_RESOLVER
#         A list of (ip, port) tuples of resolvers to use for looking
#         the SRV record(s) used for connecting to the name set in
#         IRC_SERVER.
#         The default value is None, and in this case qwebirc will use
#         the system's default resolver(s).
CONNECTION_RESOLVER = None

# QUAKENET SPECIFIC VALUES
# ---------------------------------------------------------------------
#
# These values are of no interest if you're not QuakeNet.
# At present they still need to be set, this will change soon.
#
# OPTION: HMACKEY
#         Shared key to use with hmac WEBIRC_MODE.
HMACKEY = "mrmoo"

# OPTION: HMACTEMPORAL
#         Divisor used for modulo HMAC timestamp generation.
HMACTEMPORAL = 30

# OPTION: AUTHGATEDOMAIN
#         Domain accepted inside authgate tickets.
AUTHGATEDOMAIN = "webchat_test"

# OPTION: QTICKETKEY
#         Key shared with the authgate that is used to decrypt
#         qtickets.
QTICKETKEY = "boo"

# OPTION: AUTH_SERVICE
#         Service that auth commands are sent to. Also used to check
#         responses from said service.
AUTH_SERVICE = "Q!TheQBot@CServe.quakenet.org"

# OPTION: AUTH_OK_REGEX
#         JavaScript regular expression that should match when
#         AUTH_SERVICE has returned an acceptable response to
#         authentication.
AUTH_OK_REGEX = "^You are now logged in as [^ ]+\\.$"

# OPTION: AUTHGATEPROVIDER
#         Authgate module to use, normally imported directly.
#         dummyauthgate does nothing.
import dummyauthgate as AUTHGATEPROVIDER

########NEW FILE########
__FILENAME__ = avahiclient
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :
# Copyright (C) 2013 Project Byzantium
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

__license__ = 'GPL v3'

import select
import json
import sys
import os
import pybonjour
import _utils

conf = _utils.Config()
logging = _utils.get_logging()

SERVICE_TYPE = '__byz__._tcp'

timeout  = 5
resolved = []

def update_services_cache(service,action = 'add'):
    logging.debug(service)
    logging.debug('updating cache')
    if os.path.exists(conf.services_cache):
        services = json.loads(_utils.file2str(conf.services_cache))
    else:
        services = {}

    if action.lower() == 'add':
        services.update(service)
        logging.debug('Service added')
    elif action.lower() == 'del' and service in services:
        del services[service]
        logging.debug('Service removed')
    _utils.str2file(json.dumps(services),conf.services_cache)

def resolve_callback(sdRef, flags, interfaceIndex, errorCode, fullname, hosttarget, port, txtRecord):
    if errorCode == pybonjour.kDNSServiceErr_NoError:
        logging.debug('adding')
        update_services_cache({fullname:{'host':hosttarget,'port':port,'text':txtRecord}})
        resolved.append(True)

def browse_callback(sdRef, flags, interfaceIndex, errorCode, serviceName, regtype, replyDomain):
    logging.debug(serviceName)
    if errorCode != pybonjour.kDNSServiceErr_NoError:
        return

    if not (flags & pybonjour.kDNSServiceFlagsAdd):
        update_services_cache(serviceName+'.'+regtype+replyDomain,'del')
        return

    resolve_sdRef = pybonjour.DNSServiceResolve(0, interfaceIndex, serviceName, regtype, replyDomain, resolve_callback)

    try:
        while not resolved:
            ready = select.select([resolve_sdRef], [], [], timeout)
            if resolve_sdRef not in ready[0]:
                logging.debug('Resolve timed out',1)
                break
            pybonjour.DNSServiceProcessResult(resolve_sdRef)
        else:
            resolved.pop()
    finally:
        resolve_sdRef.close()

def run():
    browse_sdRef = pybonjour.DNSServiceBrowse(regtype = SERVICE_TYPE, callBack = browse_callback)
    try:
        try:
            while True:
                ready = select.select([browse_sdRef], [], [])
                if browse_sdRef in ready[0]:
                    pybonjour.DNSServiceProcessResult(browse_sdRef)
        except KeyboardInterrupt:
            pass
    finally:
        browse_sdRef.close()

if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = services
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :
# Copyright (C) 2013 Project Byzantium
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

__license__ = 'GPL v3'

import _services
import _utils

conf = _utils.Config()


def has_internet():
    '''
    determine whether there is an internet connection available with a reasonable amount of certainty.
    return bool True if there is an internet connection False if not
    '''
    # insert magic to determine if there is an internet gateway here
    return False

def main():
    service_entry = _utils.file2str('tmpl/services_entry.tmpl')
    page = _utils.file2str('tmpl/services_page.tmpl')
    services_list = _services.get_services_list()
    if not services_list:
        page = page % {'service-list':conf.no_services_msg}
    else:
        services_html = ''
        for entry in services_list:
            services_html += service_entry % entry
        page = page % {'service-list':services_html}
    return page

if __name__ == '__main__':
    print('Content-type: text/html\n\n')
    print(main())

########NEW FILE########
__FILENAME__ = _services
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :
''' services.py
A module that reads the database of services running on the node and those found via avahi (mdns) and spits them out for use elsewhere.
'''
# Copyright (C) 2013 Project Byzantium
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.


__author__ = 'haxwithaxe (me at haxwithaxe dot net)'

__license__ = 'GPL v3'

import _utils
import sqlite3

# grab shared config
conf = _utils.Config()
logging = _utils.get_logging()

def get_local_services_list():
    '''Get the list of services running on this node from the databases.'''
    # Define the location of the service database.
    servicedb = conf.servicedb
    service_list = []

    # Set up a connection to the database.
    logging.debug("DEBUG: Opening service database.")
    connection = sqlite3.connect(servicedb)
    cursor = connection.cursor()

    # Pull a list of running web apps on the node.
    logging.debug("DEBUG: Getting list of running webapps from database.")
    cursor.execute("SELECT name FROM webapps WHERE status='active';")
    results = cursor.fetchall()
    for service in results:
        service_list += [{'name':service[0],'path':'/%s' % service[0],'description':''}]

    # Pull a list of daemons running on the node. This means that most of the web apps users will access will be displayed.
    logging.debug("DEBUG: Getting list of running servers from database.")
    cursor.execute("SELECT name FROM daemons WHERE status='active' AND showtouser='yes';")
    results = cursor.fetchall()
    for service in results:
        logging.debug("DEBUG: Value of service: %s" % str(service))
        if service[0] in conf.service_info:
            path = conf.service_info[service[0]]
        else:
            path = '/%s/' % service[0]
        service_list += [{'name':service[0],'path':path,'description':''}]

        # Clean up after ourselves.
        logging.debug("DEBUG: Closing service database.")
        cursor.close()
    return service_list

def get_remote_services_list():
    '''Get list of services advertised by Byzantium nodes found by avahi.'''
    import re
    service_list = []
    srvcdict = file2json(conf.services_cache)
    if not srvcdict: return service_list
    for name, vals in srvcdict.items():
        if re.search('\.__byz__\._[tucdp]{3}',name):
            description = ''
            path = vals['host']
            if vals['port']: path += str(vals['port'])
            if vals['text'] not in ('','\x00'):
                for entry in vals['text'].split('\n'):
                    key,val = (entry+'=').split('=')
                    v = list(val)
                    v.pop(-1)
                    val = ''.join(v)
                    if key == conf.uri_post_port_string_key:
                        path += val
                    elif key == conf.service_description_key:
                        description += val
            name = re.sub('\.__byz__\._[udtcp]{3}.*','',name)
            service_list = [{'name':name,'path':path,'description':description}]
    return service_list

def get_services_list():
    local_srvc = get_local_services_list()
    remote_srvc = get_remote_services_list()
    return local_srvc + remote_srvc

if __name__ == '__main__':
    logging.debug(get_services_list())

########NEW FILE########
__FILENAME__ = _utils
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :
# Copyright (C) 2013 Project Byzantium
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.
__license__ = 'GPL v3'

import os
import json
import logging

if os.environ['BYZ_DEBUG']:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.ERROR)

def get_logging():
    return logging

def file2str(file_name, mode = 'r'):
    if not os.path.exists(file_name):
        logging.debug('File not found: '+file_name)
        return ''
    fileobj = open(file_name,mode)
    filestr = fileobj.read()
    fileobj.close()
    return filestr

def file2json(file_name, mode = 'r'):
    filestr = file2str(file_name, mode)
    try:
        return_value = json.loads(filestr)
    except ValueError as val_e:
        logging.debug(val_e)
        return_value = None
    return return_value

def str2file(string,file_name,mode = 'w'):
    fileobj = open(file_name,mode)
    fileobj.write(string)
    fileobj.close()

def json2file(obj, file_name, mode = 'w'):
    try:
        string = json.dumps(obj)
        str2file(string, file_name, mode)
        return True
    except TypeError as type_e:
        logging.debug(type_e)
        return False

class Config(object):
    ''' Make me read from a file and/or environment'''
    def __init__(self):
        self.services_cache = '/tmp/byz_services.json'
        self.service_template = '/etc/byzantium/services/avahi/template.service'
        self.services_store_dir = '/etc/avahi/inactive'
        self.services_live_dir = '/etc/avahi/services'
        self.servicedb = '/var/db/controlpanel/services.sqlite'
        self.no_services_msg = 'No services found in the network. Please try again in a little while.'
        self.no_internet_msg = '<span class="sad-face">This mesh network is probably not connected to the internet.</span>'
        self.no_internet_msg = '<span class="winning">This mesh network is probably connected to the internet.</span>'
        self.uri_post_port_string_key = 'appendtourl'
        self.service_description_key = 'description'
        self.service_info = {'chat':'/chat/?channels=byzantium'}


########NEW FILE########
__FILENAME__ = wicd-cli
#!/usr/bin/python

#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import optparse
import dbus
import dbus.service
import sys
from wicd import misc

misc.RenameProcess('wicd-cli')

if getattr(dbus, 'version', (0, 0, 0)) < (0, 80, 0):
    import dbus.glib
else:
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

bus = dbus.SystemBus()
try:
	daemon = dbus.Interface(bus.get_object('org.wicd.daemon', '/org/wicd/daemon'),
			'org.wicd.daemon')
	wireless = dbus.Interface(bus.get_object('org.wicd.daemon', '/org/wicd/daemon/wireless'),
			'org.wicd.daemon.wireless')
	wired = dbus.Interface(bus.get_object('org.wicd.daemon', '/org/wicd/daemon/wired'),
			'org.wicd.daemon.wired')
	config = dbus.Interface(bus.get_object('org.wicd.daemon', '/org/wicd/daemon/config'),
			'org.wicd.daemon.config')
except dbus.DBusException:
	print 'Error: Could not connect to the daemon. Please make sure it is running.'
	sys.exit(3)

parser = optparse.OptionParser()

parser.add_option('--network', '-n', type='int', default=-1)
parser.add_option('--network-property', '-p')
parser.add_option('--set-to', '-s')
parser.add_option('--name', '-m')

parser.add_option('--scan', '-S', default=False, action='store_true')
parser.add_option('--save', '-w', default=False, action='store_true')
parser.add_option('--list-networks', '-l', default=False, action='store_true')
parser.add_option('--network-details', '-d', default=False, action='store_true')
parser.add_option('--disconnect', '-x', default=False, action='store_true')
parser.add_option('--connect', '-c', default=False, action='store_true')
parser.add_option('--list-encryption-types', '-e', default=False, action='store_true')
# short options for these two aren't great.
parser.add_option('--wireless', '-y', default=False, action='store_true')
parser.add_option('--wired', '-z', default=False, action='store_true')
parser.add_option('--load-profile', '-o', default=False, action='store_true')

options, arguments = parser.parse_args()

op_performed = False

if not (options.wireless or options.wired):
	print "Please use --wireless or --wired to specify " + \
	"the type of connection to operate on."

# functions
def is_valid_wireless_network_id(network_id):
	if not (network_id >= 0 \
			and network_id < wireless.GetNumberOfNetworks()):
		print 'Invalid wireless network identifier.'
		sys.exit(1)

def is_valid_wired_network_id(network_id):
	num = len(wired.GetWiredProfileList())
	if not (network_id < num and \
			network_id >= 0):
		print 'Invalid wired network identifier.'
		sys.exit(4)

def is_valid_wired_network_profile(profile_name):
	if not profile_name in wired.GetWiredProfileList():
		print 'Profile of that name does not exist.'
		sys.exit(5)

if options.scan and options.wireless:
	# synchronized scan
	wireless.Scan(True)
	op_performed = True

if options.load_profile and options.wired:
	is_valid_wired_network_profile(options.name)
	config.ReadWiredNetworkProfile(options.name)
	op_performed = True

if options.list_networks:
	if options.wireless:
		print '#\tBSSID\t\t\tChannel\tESSID'
		for network_id in range(0, wireless.GetNumberOfNetworks()):
			print '%s\t%s\t%s\t%s' % (network_id,
				wireless.GetWirelessProperty(network_id, 'bssid'),
				wireless.GetWirelessProperty(network_id, 'channel'),
				wireless.GetWirelessProperty(network_id, 'essid'))
	elif options.wired:
		print '#\tProfile name'
		id = 0
		for profile in wired.GetWiredProfileList():
			print '%s\t%s' % (id, profile)
			id += 1
	op_performed = True

if options.network_details:
	if options.wireless:
		if options.network >= 0:
			is_valid_wireless_network_id(options.network)
			network_id = options.network
		else:
			network_id = wireless.GetCurrentNetworkID(0)
			is_valid_wireless_network_id(network_id)
			# we're connected to a network, print IP
			print "IP: %s" % wireless.GetWirelessIP(0)

		print "Essid: %s" % wireless.GetWirelessProperty(network_id, "essid")
		print "Bssid: %s" % wireless.GetWirelessProperty(network_id, "bssid")
		if wireless.GetWirelessProperty(network_id, "encryption"):
			print "Encryption: On"
			print "Encryption Method: %s" % \
					wireless.GetWirelessProperty(network_id, "encryption_method")
		else:
			print "Encryption: Off"
		print "Quality: %s" % wireless.GetWirelessProperty(network_id, "quality")
		print "Mode: %s" % wireless.GetWirelessProperty(network_id, "mode")
		print "Channel: %s" % wireless.GetWirelessProperty(network_id, "channel")
		print "Bit Rates: %s" % wireless.GetWirelessProperty(network_id, "bitrates")
	op_performed = True

# network properties

if options.network_property:
	options.network_property = options.network_property.lower()
	if options.wireless:
		if options.network >= 0:
			is_valid_wireless_network_id(options.network)
			network_id = options.network
		else:
			network_id = wireless.GetCurrentNetworkID(0)
			is_valid_wireless_network_id(network_id)
		if not options.set_to:
			print wireless.GetWirelessProperty(network_id, options.network_property)
		else:
			wireless.SetWirelessProperty(network_id, \
					options.network_property, options.set_to)
	elif options.wired:
		if not options.set_to:
			print wired.GetWiredProperty(options.network_property)
		else:
			wired.SetWiredProperty(options.network_property, options.set_to)
	op_performed = True

if options.disconnect:
	daemon.Disconnect()
	if options.wireless:
		if wireless.GetCurrentNetworkID(0) > -1:
			print "Disconnecting from %s on %s" % (wireless.GetCurrentNetwork(0),
					wireless.DetectWirelessInterface())
	elif options.wired:
		if wired.CheckPluggedIn():
			print "Disconnecting from wired connection on %s" % wired.DetectWiredInterface()
	op_performed = True

if options.connect:
	if options.wireless and options.network > -1:
		is_valid_wireless_network_id(options.network)
		name = wireless.GetWirelessProperty(options.network, 'essid')
		encryption = wireless.GetWirelessProperty(options.network, 'enctype')
		print "Connecting to %s with %s on %s" % (name, encryption,
				wireless.DetectWirelessInterface())
		wireless.ConnectWireless(options.network)

		check = lambda: wireless.CheckIfWirelessConnecting()
		message = lambda: wireless.CheckWirelessConnectingMessage()
	elif options.wired:
		print "Connecting to wired connection on %s" % wired.DetectWiredInterface()
		wired.ConnectWired()

		check = lambda: wired.CheckIfWiredConnecting()
		message = lambda: wired.CheckWiredConnectingMessage()

	# update user on what the daemon is doing
	last = None
	while check():
		next = message()
		if next != last:
			# avoid a race condition where status is updated to "done" after the
			# loop check
			if next == "done":
				break
			print "%s..." % next.replace("_", " ")
			last = next
	print "done!"
	op_performed = True

# pretty print optional and required properties
def str_properties(prop):
	if len(prop) == 0:
		return "None"
	else:
		return ', '.join("%s (%s)" % (x[0], x[1].replace("_", " ")) for x in type['required'])

if options.wireless and options.list_encryption_types:
	et = misc.LoadEncryptionMethods()
	# print 'Installed encryption templates:'
	print '%s\t%-20s\t%s' % ('#', 'Name', 'Description')
	id = 0
	for type in et:
		print '%s\t%-20s\t%s' % (id, type['type'], type['name'])
		print '  Req: %s' % str_properties(type['required'])
		print '---'
		# don't print optionals (yet)
		#print '  Opt: %s' % str_properties(type['optional'])
		id += 1
	op_performed = True

if options.save and options.network > -1:
	if options.wireless:
		is_valid_wireless_network_id(options.network)
		config.SaveWirelessNetworkProfile(options.network)
	elif options.wired:
		config.SaveWiredNetworkProfile(options.name)
	op_performed = True

if not op_performed:
	print "No operations performed."


########NEW FILE########
