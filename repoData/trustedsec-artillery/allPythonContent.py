__FILENAME__ = artillery
#!/usr/bin/python
#####################################################################
#
#  Artillery v1.0
#
# Written by Dave Kennedy (ReL1K)
#
# Still a work in progress.
#
#####################################################################
import time,sys,thread,os,subprocess

# check if its installed
if not os.path.isfile("/var/artillery/artillery.py"):
    print "[*] Artillery is not installed, running setup.py.."
    subprocess.Popen("python setup.py", shell=True).wait()
    sys.exit()

from src.core import *

# create the database directories if they aren't there
if not os.path.isdir("/var/artillery/database/"):
        os.makedirs("/var/artillery/database/")
if not os.path.isfile("/var/artillery/database/temp.database"):
        filewrite = file("/var/artillery/database/temp.database", "w")
        filewrite.write("")
        filewrite.close()

# let the logfile know artillery has started successfully
write_log("Artillery has started successfully.")

# prep everything for artillery first run
check_banlist_path()

try:
    # update artillery
    if is_config_enabled("AUTO_UPDATE"):
        thread.start_new_thread(update, ())

    # import base monitoring of fs
    if is_config_enabled("MONITOR"):
        from src.monitor import *

    # port ranges to spawn
    port = read_config("PORTS")

    # spawn honeypot
    import src.honeypot

    # spawn ssh monitor
    if is_config_enabled("SSH_BRUTE_MONITOR"):
        import src.ssh_monitor

    ftp_monitor = read_config("FTP_BRUTE_MONITOR")
    if ftp_monitor.lower() == "on":
        #imprt the ftp monitor
        import src.ftp_monitor

    # start monitor engine
    import src.monitor

    # check hardening
    import src.harden

    # start the email handler
    import src.email_handler

    # if we are running posix then lets create a new iptables chain
    if is_posix():
        time.sleep(2)
        thread.start_new_thread(create_iptables_subset, ())

        # start anti_dos
        import src.anti_dos

    # check to see if we are using the intelligence feed
    if is_config_enabled("THREAT_INTELLIGENCE_FEED"):
        thread.start_new_thread(intelligence_update, ())

    # check to see if we are a threat server or not
    if is_config_enabled("THREAT_SERVER"):
        thread.start_new_thread(threat_server, ())

    # let the program to continue to run
    while 1:
        try:
            time.sleep(100000)
        except KeyboardInterrupt:
            print "\n[!] Exiting Artillery... hack the gibson.\n"
            sys.exit()

except sys.excepthook, e:
    print "Excepthook exception: " + format(e)
    pass

except KeyboardInterrupt:
    sys.exit()

except Exception, e:
    print "General exception: " + format(e)
    sys.exit()

########NEW FILE########
__FILENAME__ = remove_ban
#!/usr/bin/python
#
# simple remove banned ip
#
#
import sys
from src.core import *

try:
    ipaddress = sys.argv[1]
    if is_valid_ipv4(ipaddress):
        path = check_banlist_path()
        fileopen = file(path, "r")
        data = fileopen.read()
        data = data.replace(ipaddress + "\n", "")
        filewrite = file(path, "w")
        filewrite.write(data)
        filewrite.close()

        print "Listing all iptables looking for a match... if there is a massive amount of blocked IP's this could take a few minutes.."
        proc = subprocess.Popen("iptables -L ARTILLERY -n -v --line-numbers | grep %s" % (ipaddress), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        for line in proc.stdout.readlines():
            line = str(line)
            match = re.search(ipaddress, line)
            if match:
                # this is the rule number
                line = line.split(" ")
                line = line[0]
                print line
                # delete it
                subprocess.Popen("iptables -D ARTILLERY %s" % (line), stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)


    # if not valid then flag
    else:
        print "[!] Not a valid IP Address. Exiting."
        sys.exit()

except IndexError:
    print "Description: Simple removal of IP address from banned sites."
    print "[!] Usage: remove_ban.py <ip_address_to_ban>"

########NEW FILE########
__FILENAME__ = restart_server
#!/usr/bin/python
#
# restart artillery
#
#
import subprocess
import os
import signal
from src.core import *
proc = subprocess.Popen("ps -A x | grep artiller[y]", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
try:
    pid = proc.communicate()[0]
    pid = pid.split(" ")
    pid = int(pid[0])
    write_log("[!] Killing the old Artillery process...")
    print "[*] Killing Old Artillery Process...."
    os.kill(pid, signal.SIGKILL)
except:
    pass

print "[*] Restarting Artillery Server..."
if os.path.isfile("/var/artillery/artillery.py"):
    write_log("[*] Restarting the Artillery Server process...")
    subprocess.Popen("python /var/artillery/artillery.py &", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

########NEW FILE########
__FILENAME__ = anti_dos
#!/usr/bin/python
#
# basic for now, more to come
#
#
import subprocess
from src.core import *

anti_dos_ports = read_config("ANTI_DOS_PORTS")
anti_dos_throttle = read_config("ANTI_DOS_THROTTLE_CONNECTIONS")
anti_dos_burst = read_config("ANTI_DOS_LIMIT_BURST")

if is_config_enabled("ANTI_DOS"):
    # basic throttle for some ports
    anti_dos_ports = anti_dos_ports.split(",")
    for ports in anti_dos_ports:
        subprocess.Popen("iptables -A ARTILLERY -p tcp --dport %s -m limit --limit %s/minute --limit-burst %s -j ACCEPT" % (ports,anti_dos_throttle,anti_dos_burst), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).wait()

########NEW FILE########
__FILENAME__ = apache_monitor
#127.0.0.1 - - [10/Mar/2012:15:35:53 -0500] "GET /sdfsdfds.dsfds HTTP/1.1" 404 501 "-" "Mozilla/5.0 (X11; Linux i686 on x86_64; rv:10.0.2) Gecko/20100101 Firefox/10.0.2"

def tail(some_file):
    this_file = open(some_file)
    # Go to the end of the file
    this_file.seek(0,2)

    while True:
        line = this_file.readline()
        if line:
            yield line
        yield None

# grab the access logs and tail them
access = "/var/log/apache2/access.log"
access_log = tail(access)

# grab the error logs and tail them
errors = "/var/log/apache2/error.log"
error_log = tail(errors)

########NEW FILE########
__FILENAME__ = core
#
#
# core module for reusable / central code
#
#
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders
import os
import re
import subprocess
import urllib
import os
import time
import shutil
import logging
import logging.handlers

def get_config_path():
    path = ""
    if is_posix():
        if os.path.isfile("/var/artillery/config"):
            path = "/var/artillery/config"
        if os.path.isfile("config"):
            path = "config"
    if is_windows():
        program_files = os.environ["ProgramFiles"]
        if os.path.isfile(program_files + "\\Artillery\\config"):
            path = program_files + "\\Artillery\\config"
    return path

def read_config(param):
    path = get_config_path()
    fileopen = file(path, "r")
    for line in fileopen:
        if not line.startswith("#"):
            match = re.search(param + "=", line)
            if match:
                line = line.rstrip()
                line = line.replace('"', "")
                line = line.split("=")
                return line[1]

def is_config_enabled(param):
    config = read_config(param).lower()
    return config in ("on", "yes")

def ban(ip):
    # ip check routine to see if its a valid IP address
    if is_valid_ipv4(ip.strip()):
        # if we are running nix variant then trigger ban through iptables
        if is_posix():
            fileopen = file("/var/artillery/banlist.txt", "r")
            data = fileopen.read()
            if ip not in data:
                filewrite = file("/var/artillery/banlist.txt", "a")
                subprocess.Popen("iptables -I ARTILLERY 1 -s %s -j DROP" % ip, shell=True).wait()
                filewrite.write(ip+"\n")
                filewrite.close()

        # if running windows then route attacker to some bs address
        if is_windows():
            subprocess.Popen("route ADD %s MASK 255.255.255.255 10.255.255.255" % (ip), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

def update():
    if is_posix():
        if os.path.isdir("/var/artillery/.svn"):
            print "[!] Old installation detected that uses subversion. Fixing and moving to github."
            try:
                shutil.rmtree("/var/artillery")
                subprocess.Popen("git clone https://github.com/trustedsec/artillery", shell=True).wait()
            except:
                print "[!] Something failed. Please type 'git clone https://github.com/trustedsec/artillery /var/artillery' to fix!"

        subprocess.Popen("cd /var/artillery;git pull", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

def is_whitelisted_ip(ip):
    # set base counter
    counter = 0
    # grab ips
    ipaddr = str(ip)
    whitelist = read_config("WHITELIST_IP")
    match = re.search(ip, whitelist)
    if match:
        # if we return one, the ip has already beeb banned
        counter = 1
    # else we'll check cidr notiation
    else:
        counter = printCIDR(ip)

    return counter

# validate that its an actual ip address versus something else stupid
def is_valid_ipv4(ip):
    pattern = re.compile(r"""
    ^
    (?:
      # Dotted variants:
      (?:
        # Decimal 1-255 (no leading 0's)
        [3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}
      |
        0x0*[0-9a-f]{1,2}  # Hexadecimal 0x0 - 0xFF (possible leading 0's)
      |
        0+[1-3]?[0-7]{0,2} # Octal 0 - 0377 (possible leading 0's)
      )
      (?:                  # Repeat 0-3 times, separated by a dot
        \.
        (?:
          [3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}
        |
          0x0*[0-9a-f]{1,2}
        |
          0+[1-3]?[0-7]{0,2}
        )
      ){0,3}
    |
      0x0*[0-9a-f]{1,8}    # Hexadecimal notation, 0x0 - 0xffffffff
    |
      0+[0-3]?[0-7]{0,10}  # Octal notation, 0 - 037777777777
    |
      # Decimal notation, 1-4294967295:
      429496729[0-5]|42949672[0-8]\d|4294967[01]\d\d|429496[0-6]\d{3}|
      42949[0-5]\d{4}|4294[0-8]\d{5}|429[0-3]\d{6}|42[0-8]\d{7}|
      4[01]\d{8}|[1-3]\d{0,9}|[4-9]\d{0,8}
    )
    $
    """, re.VERBOSE | re.IGNORECASE)
    return pattern.match(ip) is not None

def check_banlist_path():
    path = ""
    if is_posix():
        if os.path.isfile("banlist.txt"):
            path = "banlist.txt"

        if os.path.isfile("/var/artillery/banlist.txt"):
            path = "/var/artillery/banlist.txt"

        # if path is blank then try making the file
        if path == "":
            if os.path.isdir("/var/artillery"):
                filewrite=file("/var/artillery/banlist.txt", "w")
                filewrite.write("#\n#\n#\n# TrustedSec's Artillery Threat Intelligence Feed and Banlist Feed\n# https://www.trustedsec.com\n#\n# Note that this is for public use only.\n# The ATIF feed may not be used for commercial resale or in products that are charging fees for such services.\n# Use of these feeds for commerical (having others pay for a service) use is strictly prohibited.\n#\n#\n#\n")
                filewrite.close()
                path = "/var/artillery/banlist.txt"

    if is_windows():
        program_files = os.environ["ProgramFiles"]
        if os.path.isfile(program_files + "\\Artillery\\banlist.txt"):
            # grab the path
            path = program_files + "\\Artillery\\banlist.txt"
        if path == "":
            if os.path.isdir(program_files + "\\Artillery"):
                path = program_files + "\\Artillery"
                filewrite = file(program_files + "\\Artillery\\banlist.txt", "w")
                filewrite.write("#\n#\n#\n# TrustedSec's Artillery Threat Intelligence Feed and Banlist Feed\n# https://www.trustedsec.com\n#\n# Note that this is for public use only.\n# The ATIF feed may not be used for commercial resale or in products that are charging fees for such services.\n# Use of these feeds for commerical (having others pay for a service) use is strictly prohibited.\n#\n#\n#\n")
                filewrite.close()
    return path

# this will write out a log file for us to be sent eventually
def prep_email(alert):
    if is_posix():
        # write the file out to program_junk
        filewrite=file("/var/artillery/src/program_junk/email_alerts.log", "w")
    if is_windows():
        program_files = os.environ["ProgramFiles"]
        filewrite=file(program_files + "\\Artillery\\src\\program_junk\\email_alerts.log", "w")
    filewrite.write(alert)
    filewrite.close()

def is_posix():
    return os.name == "posix"

def is_windows():
    return os.name == "nt"

def create_iptables_subset():
    if is_posix():
        subprocess.Popen("iptables -N ARTILLERY", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        subprocess.Popen("iptables -F ARTILLERY", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        subprocess.Popen("iptables -I INPUT -j ARTILLERY", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    #sync our iptables blocks with the existing ban file so we don't forget attackers
    proc = subprocess.Popen("iptables -L ARTILLERY -n --line-numbers", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    iptablesbanlist = proc.stdout.readlines()

    if os.path.isfile(check_banlist_path()):
        banfile = file(check_banlist_path(), "r")
    else:
        filewrite = file("banlist.txt", "w")
        filewrite.write("")
        filewrite.close()
        banfile = file("banlist.txt", "r")

    # iterate through lines in ban file and ban them if not already banned
    for ip in banfile:
        if not ip.startswith("#"):
            if ip not in iptablesbanlist:
                subprocess.Popen("iptables -I ARTILLERY 1 -s %s -j DROP" % ip.strip(), shell=True).wait()

# valid if IP address is legit
def is_valid_ip(ip):
    return is_valid_ipv4(ip)

# convert a binary string into an IP address
def bin2ip(b):
    ip = ""
    for i in range(0,len(b),8):
        ip += str(int(b[i:i+8],2))+"."
    return ip[:-1]

# convert an IP address from its dotted-quad format to its 32 binary digit representation
def ip2bin(ip):
    b = ""
    inQuads = ip.split(".")
    outQuads = 4
    for q in inQuads:
        if q != "":
            b += dec2bin(int(q),8)
            outQuads -= 1
    while outQuads > 0:
        b += "00000000"
        outQuads -= 1
    return b

# convert a decimal number to binary representation
# if d is specified, left-pad the binary number with 0s to that length
def dec2bin(n,d=None):
    s = ""
    while n>0:
        if n&1:
            s = "1"+s
        else:
            s = "0"+s
        n >>= 1

    if d is not None:
        while len(s)<d:
            s = "0"+s
    if s == "": s = "0"
    return s

# print a list of IP addresses based on the CIDR block specified
def printCIDR(attacker_ip):
    trigger = 0
    whitelist = read_config("WHITELIST_IP")
    whitelist = whitelist.split(",")
    for c in whitelist:
        match = re.search("/", c)
        if match:
            parts = c.split("/")
            baseIP = ip2bin(parts[0])
            subnet = int(parts[1])
            # Python string-slicing weirdness:
            # if a subnet of 32 was specified simply print the single IP
            if subnet == 32:
                ipaddr = bin2ip(baseIP)
            # for any other size subnet, print a list of IP addresses by concatenating
            # the prefix with each of the suffixes in the subnet
            else:
                ipPrefix = baseIP[:-(32-subnet)]
                for i in range(2**(32-subnet)):
                    ipaddr = bin2ip(ipPrefix+dec2bin(i, (32-subnet)))
                    ip_check = is_valid_ip(ipaddr)
                    # if the ip isnt messed up then do this
                    if ip_check != False:
                        # compare c (whitelisted IP) to subnet IP address whitelist
                        if c == ipaddr:
                            # if we equal each other then trigger that we are whitelisted
                            trigger = 1

    # return the trigger - 1 = whitelisted 0 = not found in whitelist
    return trigger

def intelligence_update():
    try:
    # loop forever
        while 1:
            try:

                threat_feed = read_config("THREAT_FEED")
                threat_feed = threat_feed.split(",")
                # allow multiple feeds if needed
                for threats in threat_feed:
                    banlist = urllib.urlopen('%s' % (threats))
                    for line in banlist:
                        line = line.rstrip()
                        ban(line)
                        # sleep a millisecond as to not spike CPU up
                        time.sleep(1)

                # wait 24 hours
                time.sleep(86400)

            except Exception: pass

    except Exception, e:
        print "Unable to fully load banlist, something went wrong: " + str(e)

def threat_server():
    public_http = read_config("THREAT_LOCATION")
    if os.path.isdir(public_http):
        while 1:
            subprocess.Popen("cp /var/artillery/banlist.txt %s" % (public_http), shell=True).wait()
            time.sleep(800)

# send the message then if its local or remote
def syslog(message):
    type = read_config("SYSLOG_TYPE").lower()

    # if we are sending remote syslog
    if type == "remote":

        import socket
        FACILITY = {
                'kern': 0, 'user': 1, 'mail': 2, 'daemon': 3,
                'auth': 4, 'syslog': 5, 'lpr': 6, 'news': 7,
                'uucp': 8, 'cron': 9, 'authpriv': 10, 'ftp': 11,
                'local0': 16, 'local1': 17, 'local2': 18, 'local3': 19,
                'local4': 20, 'local5': 21, 'local6': 22, 'local7': 23,
                }

        LEVEL = {
                'emerg': 0, 'alert':1, 'crit': 2, 'err': 3,
                'warning': 4, 'notice': 5, 'info': 6, 'debug': 7
                }


        def syslog_send(message, level=LEVEL['notice'], facility=FACILITY['daemon'],
                host='localhost', port=514):

            # Send syslog UDP packet to given host and port.
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data = '<%d>%s' % (level + facility*8, message + "\n")
            sock.sendto(data, (host, port))
            sock.close()

        # send the syslog message
        remote_syslog = read_config("SYSLOG_REMOTE_HOST")
        syslog_send(message, host=remote_syslog)

    # if we are sending local syslog messages
    if type == "local":
        my_logger = logging.getLogger('Artillery')
        my_logger.setLevel(logging.DEBUG)
        handler = logging.handlers.SysLogHandler(address = '/dev/log')
        my_logger.addHandler(handler)
    for line in message.splitlines():
        my_logger.critical(line + "\n")

def write_log(alert):
    if is_posix():
        syslog(alert)

    if is_windows():
        program_files = os.environ["ProgramFiles"]
        if not os.path.isdir(program_files + "\\Artillery\\logs"):
            os.makedirs(program_files + "\\Artillery\\logs")
        if not os.path.isfile(program_files + "\\Artillery\\logs\\alerts.log"):
            filewrite = file(program_files + "\\Artillery\\logs\\alerts.log", "w")
            filewrite.write("***** Artillery Alerts Log *****\n")
            filewrite.close()
        filewrite = file(program_files + "\\Artillery\\logs\\alerts.log", "a")
        filewrite.write(alert+"\n")
        filewrite.close()

def warn_the_good_guys(subject, alert):
    email_alerts = is_config_enabled("EMAIL_ALERTS")
    email_frequency = is_config_enabled("EMAIL_FREQUENCY")

    if email_alerts and not email_frequency:
        send_mail(subject, alert)

    if email_alerts and email_frequency:
        prep_email(alert + "\n")

    write_log(alert)

user = read_config("SMTP_USERNAME")
pwd = read_config("SMTP_PASSWORD")
smtp_address = read_config("SMTP_ADDRESS")
# port we use, default is 25
smtp_port = int(read_config("SMTP_PORT"))
smtp_from = read_config("SMTP_FROM")

def send_mail(subject, text):
    mail(read_config("ALERT_USER_EMAIL"), subject, text)

def mail(to, subject, text):
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(text))
        # prep the smtp server
        mailServer = smtplib.SMTP("%s" % (smtp_address), smtp_port)
        # send ehlo
        mailServer.ehlo()
        # tls support?
        mailServer.starttls()
        # some servers require ehlo again
        mailServer.ehlo()
        # login to server if we aren't using an open mail relay
        if user != None:
            mailServer.login(user, pwd)
        mailServer.sendmail(to, to, msg.as_string())
        mailServer.close()
    except:
        write_log("[!] Error, Artillery was unable to log into the mail server")

########NEW FILE########
__FILENAME__ = email_handler
#!/usr/bin/python
#
#
# Handles emails from the config. Delivers after X amount of time
#
#
import shutil,time,thread
from src.core import *

# check how long to send the email
mail_time = read_config("EMAIL_FREQUENCY")

# this is what handles the loop for checking email alert frequencies
def check_alert():
    # loop forever
    while 1:
        # if the file is there, read it in then trigger email
        if os.path.isfile("/var/artillery/src/program_junk/email_alerts.log"):
            # read open the file to be sent
            fileopen = file("/var/artillery/src/program_junk/email_alerts.log", "r")
            data = fileopen.read()
            if is_config_enabled("EMAIL_ALERTS"):
                send_mail("[!] Artillery has new notifications for you. [!]",
                data)
                # save this for later just in case we need it
                shutil.move("/var/artillery/src/program_junk/email_alerts.log", "/var/artillery/src/program_junk/email_alerts.old")
        time.sleep(int(mail_time))

junk = ""
thread.start_new_thread(check_alert, ())

########NEW FILE########
__FILENAME__ = ftp_monitor
#!/usr/bin/python

#############################
#
# monitor ftp and ban
# added by e @ Nov 5th
#############################

import time,re, thread
from src.core import *

send_email = read_config("ALERT_USER_EMAIL")

# how frequently we need to monitor
monitor_time = read_config("MONITOR_FREQUENCY")
monitor_time = int(monitor_time)
ftp_attempts = read_config("FTP_BRUTE_ATTEMPTS")
# check for whitelist
def ftp_monitor(monitor_time):
    while 1:
        # for debian base
        if os.path.isfile("/var/log/vsftpd.log"):
            fileopen1 = file("/var/log/auth.log", "r")
        else:
            print "Has not found configuration file for ftp. Ftp monitor now stops."
            break


        if not os.path.isfile("/var/artillery/banlist.txt"):
            # create a blank file
            filewrite = file("/var/artillery/banlist.txt", "w")
            filewrite.write("")
            filewrite.close()

        try:
            # base ftp counter to see how many attempts we've had
            ftp_counter = 0
            counter = 0
            for line in fileopen1:
                counter = 0
                fileopen2 = file("/var/artillery/banlist.txt", "r")
                line = line.rstrip()
                # search for bad ftp
                match = re.search("CONNECT: Client", line)
                if match:
                    ftp_counter = ftp_counter + 1
                    # split based on spaces
                    line = line.split('"')
                    # pull ipaddress
                    ipaddress = line[-2]
                    ip_check = is_valid_ipv4(ipaddress)
                    if ip_check != False:

                        # if its not a duplicate then ban that ass
                        if ftp_counter >= int(ftp_attempts):
                            banlist = fileopen2.read()
                            match = re.search(ipaddress, banlist)
                            if match:
                                counter = 1
                                # reset FTP counter
                                ftp_counter = 0

                            # if counter is equal to 0 then we know that we need to ban
                            if counter == 0:
                                whitelist_match = whitelist(ipaddress)
                                if whitelist_match == 0:

                                    # if we have email alerting on we can send email messages
                                    email_alerts = read_config("EMAIL_ALERTS").lower()
                                    # check email frequency
                                    email_frequency = read_config("EMAIL_FREQUENCY").lower()

                                    if email_alerts == "on" and email_frequency == "off":
                                        mail(send_email,
                                        "[!] Artillery has banned an FTP brute force. [!]",
                                        "The following IP has been blocked: " + ipaddress)

                                    # check frequency is allowed
                                    if email_alerts == "on" and email_frequency == "on":
                                        prep_email("Artillery has blocked (blacklisted) the following IP for FTP brute forcing violations: " + ipaddress + "\n")

                                    # write out to log
                                    write_log("Artillery has blocked (blacklisted) the following IP for FTP brute forcing violations: " + ipaddress)

                                    # do the actual ban, this is pulled from src.core
                                    ban(ipaddress)
                                    ftp_counter = 0

                                    # wait one to make sure everything is caught up
                                    time.sleep(1)
            # sleep for defined time
            time.sleep(monitor_time)

        except Exception, e:
            print "[*] An error in ftp monitor occured. Printing it out here: " + str(e)

if is_posix():
    # start thread
    thread.start_new_thread(ftp_monitor,(monitor_time,))

########NEW FILE########
__FILENAME__ = harden
#!/usr/bin/python
#
# eventual home for checking some base files for security configurations
#
import re
import os
from src.core import *

# flag warnings, base is nothing
warning = ""

if is_posix():
    #
    # check ssh config
    #
    if os.path.isfile("/etc/ssh/sshd_config"):
        fileopen = file("/etc/ssh/sshd_config", "r")
        data = fileopen.read()
        if is_config_enabled("ROOT_CHECK"):
            match = re.search("RootLogin yes", data)
            # if we permit root logins trigger alert
            if match:
                # trigger warning if match
                warning = warning + "Issue identified: /etc/ssh/sshd_config allows RootLogin. An attacker can gain root access to the system if password is guessed. Recommendation: Change RootLogin yes to RootLogin no\n\n"
        match = re.search(r"Port 22\b", data)
        if match:
            if is_config_enabled("SSH_DEFAULT_PORT_CHECK"):
                # trigger warning is match
                warning = warning + "Issue identified: /etc/ssh/sshd_config. SSH is running on the default port 22. An attacker commonly scans for these type of ports. Recommendation: Change the port to something high that doesn't get picked up by typical port scanners.\n\n"

    #
    # check ftp config
    #
    if os.path.isfile("/etc/vsftpd.conf"):
        fileopen = file("/etc/vsftpd.conf", "r")
        data = fileopen.read()
        match = re.search("anonymous_enable=YES", data)
        if match:	
            # trigger warning if match
            warning = warning + "Issue identified: /etc/vsftpd.conf allows Anonymous login. An attacker can gain a foothold to the system with absolutel zero effort. Recommendation: Change anonymous_enable yes to anonymous_enable no\n\n"


    #
    # check /var/www permissions
    #
    if os.path.isdir("/var/www/"):
        for path, subdirs, files in os.walk("/var/www/"):
            for name in files:
                trigger_warning = 0
                filename = os.path.join(path, name)
                if os.path.isfile(filename):
                    # check permission
                    check_perm = os.stat(filename)
                    check_perm = str(check_perm)
                    match = re.search("st_uid=0", check_perm)
                    if not match:
                        trigger_warning = 1
                    match = re.search("st_gid=0", check_perm)
                    if not match:
                        trigger_warning = 1
                    # if we trigger on vuln
                    if trigger_warning == 1:
                        warning = warning + "Issue identified: %s permissions are not set to root. If an attacker compromises the system and is running under the Apache user account, could view these files. Recommendation: Change the permission of %s to root:root. Command: chown root:root %s\n\n" % (filename,filename,filename)

    #
    # if we had warnings then trigger alert
    #
    if len(warning) > 1:
        subject = "[!] Insecure configuration detected on filesystem"
        warn_the_good_guys(subject, subject + warning)

########NEW FILE########
__FILENAME__ = honeypot
#!/usr/bin/python
#
# this is the honeypot stuff
#
#
import thread
import socket
import sys
import re
import subprocess
import time
import SocketServer
import os
import random
import datetime

from src.core import *

# port ranges to spawn pulled from config
ports = read_config("PORTS")
# check to see what IP we need to bind to
bind_interface = read_config("BIND_INTERFACE")
honeypot_ban = is_config_enabled("HONEYPOT_BAN")

# main socket server listener for responses
class SocketListener((SocketServer.BaseRequestHandler)):

    def handle(self):
        pass

    def setup(self):
        # hehe send random length garbage to the attacker
        length = random.randint(5, 30000)

        # fake_string = random number between 5 and 30,000 then os.urandom the command back
        fake_string = os.urandom(int(length))

        # try the actual sending and banning
        try:
            self.request.send(fake_string)
            ip = self.client_address[0]
            if is_valid_ipv4(ip):
                check_whitelist = is_whitelisted_ip(ip)
                # ban the mofos
                if check_whitelist == 0:
                    now = str(datetime.datetime.today())
                    port = self.server.server_address[1]
                    subject = "%s [!] Artillery has detected an attack from the IP Address: %s" % (now, ip)
                    alert = ""
                    if honeypot_ban:
                        alert = "%s [!] Artillery has blocked (and blacklisted) the IP Address: %s for connecting to a honeypot restricted port: %s" % (now, ip, port)
                    else:
                        alert = "%s [!] Artillery has detected an attack from IP address: %s for a connection on a honeypot port: %s" % (now, ip, port)
                    warn_the_good_guys(subject, alert)

                    # close the socket
                    self.request.close()

                    # if it isn't whitelisted and we are set to ban
                    if honeypot_ban:
                        ban(self.client_address[0])
        except Exception, e:
            print "[!] Error detected. Printing: " + str(e)
            pass

# here we define a basic server
def listen_server(port,bind_interface):
    try:
        port = int(port)
        if bind_interface == "":
            server = SocketServer.ThreadingTCPServer(('', port), SocketListener)
        else:
            server = SocketServer.ThreadingTCPServer(('%s' % bind_interface, port), SocketListener)
        server.serve_forever()

    # if theres already something listening on this port
    except Exception: pass

# check to see which ports we are using and ban if ports are touched
def main(ports,bind_interface):

        # pull the banlist path
    if os.path.isfile("check_banlist_path"):
        banlist_path = check_banlist_path()
        fileopen = file(banlist_path, "r")
        for line in fileopen:
        # remove any bogus characters
            line = line.rstrip()
            # ban actual IP addresses
            if honeypot_ban:
                whitelist = read_config("WHITELIST_IP")
                match = re.search(line, whitelist)
                if not match:
                        # ban the ipaddress
                    ban(line)
    # split into tuple
    ports = ports.split(",")
    for port in ports:
        thread.start_new_thread(listen_server, (port,bind_interface,))

# launch the application
main(ports,bind_interface)

########NEW FILE########
__FILENAME__ = monitor
#!/usr/bin/python
#
# This one monitors file system integrity
#
import os,re, hashlib, time, subprocess, thread,datetime, shutil
from src.core import *

def monitor_system(time_wait):
    # total_compare is a tally of all sha512 hashes
    total_compare = ""
    # what files we need to monitor
    check_folders = read_config("MONITOR_FOLDERS")
    # split lines
    exclude_counter = 0
    check_folders = check_folders.replace('"', "")
    check_folders = check_folders.replace("MONITOR_FOLDERS=", "")
    check_folders = check_folders.rstrip()
    check_folders = check_folders.split(",")
    # cycle through tuple
    for directory in check_folders:
        time.sleep(0.1)
        exclude_counter = 0
        # we need to check to see if the directory is there first, you never know
        if os.path.isdir(directory):
            # check to see if theres an include
            exclude_check = read_config("EXCLUDE")
            match = re.search(exclude_check, directory)
            # if we hit a match then we need to exclude
            if match:
                if exclude_check != "":
                    exclude_counter = 1
            # do a try block in case empty
            # if we didn't trigger exclude
            if exclude_counter == 0:
                # this will pull a list of files and associated folders
                for path, subdirs, files in os.walk(directory):
                    for name in files:
                        exclude_counter = 0
                        filename = os.path.join(path, name)
                        # check for exclusion
                        match = re.search(exclude_check, filename)
                        if match:
                            if exclude_check != "":
                                exclude_counter = 1
                        if exclude_counter == 0:
                            # some system protected files may not show up, so we check here
                            if os.path.isfile(filename):
                                try:
                                    fileopen = file(filename, "rb")
                                    data = fileopen.read()

                                except: pass
                                hash = hashlib.sha512()
                                try:
                                    hash.update(data)
                                except: pass
                                # here we split into : with filename : hexdigest
                                compare = filename + ":" + hash.hexdigest() + "\n"
                                # this will be all of our hashes
                                total_compare = total_compare + compare

    # write out temp database
    temp_database_file = file("/var/artillery/database/temp.database", "w")
    temp_database_file.write(total_compare)
    temp_database_file.close()

    # once we are done write out the database, if this is the first time, create a database then compare
    if not os.path.isfile("/var/artillery/database/integrity.database"):
        # prep the integrity database to be written for first time
        database_file = file("/var/artillery/database/integrity.database", "w")
        database_file.write(total_compare)
        database_file.close()

    # hash the original database
    if os.path.isfile("/var/artillery/database/integrity.database"):
        database_file = file("/var/artillery/database/integrity.database", "r")
        database_content = database_file.read()
        if os.path.isfile("/var/artillery/database/temp.database"):
            temp_database_file = file("/var/artillery/database/temp.database", "r")
            temp_hash = temp_database_file.read()

            # hash the databases then compare
            database_hash = hashlib.sha512()
            database_hash.update(database_content)
            database_hash = database_hash.hexdigest()

            # this is the temp integrity database
            temp_database_hash = hashlib.sha512()
            temp_database_hash.update(temp_hash)
            temp_database_hash = temp_database_hash.hexdigest()
            # if we don't match then there was something that was changed
            if database_hash != temp_database_hash:
                # using diff for now, this will be rewritten properly at a later time
                compare_files = subprocess.Popen("diff /var/artillery/database/integrity.database /var/artillery/database/temp.database", shell=True, stdout=subprocess.PIPE)
                output_file = compare_files.communicate()[0]
                if output_file == "":
                    # no changes
                    pass

                else:
                    subject = "[!] Artillery has detected a change. [!]"
                    output_file = "********************************** The following changes were detect at %s **********************************\n" % (datetime.datetime.now()) + output_file + "\n********************************** End of changes. **********************************\n\n"
                    warn_the_good_guys(subject, output_file)

    # put the new database as old
    if os.path.isfile("/var/artillery/database/temp.database"):
        shutil.move("/var/artillery/database/temp.database", "/var/artillery/database/integrity.database")

def start_monitor():
    # check if we want to monitor files
    if is_config_enabled("MONITOR"):
        # start the monitoring
        time_wait = read_config("MONITOR_FREQUENCY")

        # loop forever
        while 1:
            thread.start_new_thread(monitor_system, (time_wait,))
            time_wait = int(time_wait)
            time.sleep(time_wait)

# start the thread only if its running posix will rewrite this module to use difflib and some others butfor now its reliant on linux
if is_posix():
    thread.start_new_thread(start_monitor, ())

########NEW FILE########
__FILENAME__ = ssh_monitor
#!/usr/bin/python
#
# monitor ssh and ban
#
import time,re, thread
from src.core import *

monitor_frequency = int(read_config("MONITOR_FREQUENCY"))
ssh_attempts = read_config("SSH_BRUTE_ATTEMPTS")

def ssh_monitor(monitor_frequency):
    while 1:
        # for debian base
        if os.path.isfile("/var/log/auth.log"):
            fileopen1 = file("/var/log/auth.log", "r")

            # for OS X
            if os.path.isfile("/var/log/secure.log"):
                fileopen1 = file("/var/log/secure.log", "r")

        # for centOS
        if os.path.isfile("/var/log/secure"):
            fileopen1 = file("/var/log/secure", "r")

        # for Debian
        if os.path.isfile("/var/log/faillog"):
            fileopen1 = file("/var/log/faillog", "r")

        if not os.path.isfile("/var/artillery/banlist.txt"):
            # create a blank file
            filewrite = file("/var/artillery/banlist.txt", "w")
            filewrite.write("")
            filewrite.close()

        try:
            # base ssh counter to see how many attempts we've had
            ssh_counter = 0
            counter = 0
            for line in fileopen1:
                counter = 0
                fileopen2 = file("/var/artillery/banlist.txt", "r")
                line = line.rstrip()
                # search for bad ssh
                match = re.search("Failed password for", line)
                if match:
                    ssh_counter = ssh_counter + 1
                    line = line.split(" ")
                    # pull ipaddress
                    ipaddress = line[-4]
                    if is_valid_ipv4(ipaddress):

                        # if its not a duplicate then ban that ass
                        if ssh_counter >= int(ssh_attempts):
                            banlist = fileopen2.read()
                            match = re.search(ipaddress, banlist)
                            if match:
                                counter = 1
                                # reset SSH counter
                                ssh_counter = 0

                            # if counter is equal to 0 then we know that we need to ban
                            if counter == 0:
                                whitelist_match = is_whitelisted_ip(ipaddress)
                                if whitelist_match == 0:
                                    subject = "[!] Artillery has banned an SSH brute force. [!]"
                                    alert = "Artillery has blocked (blacklisted) the following IP for SSH brute forcing violations: " + ipaddress
                                    warn_the_good_guys(subject, alert)

                                    # do the actual ban, this is pulled from src.core
                                    ban(ipaddress)
                                    ssh_counter = 0

                                    # wait one to make sure everything is caught up
                                    time.sleep(1)
            # sleep for defined time
            time.sleep(monitor_frequency)

        except Exception, e:
            print "[*] An error in ssh monitor occured. Printing it out here: " + str(e)

if is_posix():
    thread.start_new_thread(ssh_monitor,(monitor_frequency,))

########NEW FILE########
