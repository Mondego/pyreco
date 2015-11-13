__FILENAME__ = dnsrecon
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    DNSRecon
#
#    Copyright (C) 2014  Carlos Perez
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; Applies version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

__version__ = '0.8.8'
__author__ = 'Carlos Perez, Carlos_Perez@darkoperator.com'

__doc__ = """
DNSRecon http://www.darkoperator.com

 by Carlos Perez, Darkoperator

requires dnspython http://www.dnspython.org/
requires netaddr https://github.com/drkjam/netaddr/

"""
import getopt
import os
import string
import sqlite3
import datetime

import netaddr


# Manage the change in Python3 of the name of the Queue Library
try:
    from Queue import Queue
except ImportError:
    from queue import Queue

from random import Random
from threading import Lock, Thread
from xml.dom import minidom
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import dns.message
import dns.query
import dns.rdatatype
import dns.resolver
import dns.reversename
import dns.zone
import dns.message
import dns.rdata
import dns.rdatatype
import dns.flags
import json
from dns.dnssec import algorithm_to_text

from lib.gooenum import *
from lib.whois import *
from lib.dnshelper import DnsHelper
from lib.msf_print import *

# Global Variables for Brute force Threads
brtdata = []


# Function Definitions
# -------------------------------------------------------------------------------

# Worker & Threadpool classes ripped from
# http://code.activestate.com/recipes/577187-python-thread-pool/

class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""

    lck = Lock()

    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()
        # Global variable that will hold the results
        global brtdata

    def run(self):

        found_recrd = []
        while True:
            (func, args, kargs) = self.tasks.get()
            try:
                found_recrd = func(*args, **kargs)
                if found_recrd:
                    Worker.lck.acquire()
                    brtdata.append(found_recrd)
                    for r in found_recrd:
                        if type(r).__name__ == "dict":
                            for k, v in r.iteritems():
                                print_status("\t{0}:{1}".format(k, v))
                            print_status()
                        else:
                            print_status("\t {0}".format(" ".join(r)))
                    Worker.lck.release()

            except Exception as e:
                print_debug(e)
            self.tasks.task_done()


class ThreadPool:
    """Pool of threads consuming tasks from a queue"""

    def __init__(self, num_threads):
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks)

    def add_task(self,
                 func,
                 *args,
                 **kargs):
        """Add a task to the queue"""

        self.tasks.put((func, args, kargs))

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue"""

        self.tasks.join()

    def count(self):
        """Return number of tasks in the queue"""

        return self.tasks.qsize()


def exit_brute(pool):
    print_error("You have pressed Ctrl-C. Saving found records.")
    print_status("Waiting for {0} remaining threads to finish.".format(pool.count()))
    pool.wait_completion()


def process_range(arg):
    """
    Function will take a string representation of a range for IPv4 or IPv6 in
    CIDR or Range format and return a list of IPs.
    """
    try:
        ip_list = None
        range_vals = []
        if re.match(r'\S*\/\S*', arg):
            ip_list = IPNetwork(arg)

        elif (re.match(r'\S*\-\S*', arg)):
            range_vals.extend(arg.split("-"))
            if len(range_vals) == 2:
                ip_list = IPRange(range_vals[0], range_vals[1])
        else:
            print_error("Range provided is not valid")
            return []
    except:
        print_error("Range provided is not valid")
        return []
    return ip_list


def process_spf_data(res, data):
    """
    This function will take the text info of a TXT or SPF record, extract the
    IPv4, IPv6 addresses and ranges, request process include records and return
    a list of IP Addresses for the records specified in the SPF Record.
    """
    # Declare lists that will be used in the function.
    ipv4 = []
    ipv6 = []
    includes = []
    ip_list = []

    # check first if it is a sfp record
    if not re.search(r'v\=spf', data):
        return

    # Parse the record for IPv4 Ranges, individual IPs and include TXT Records.
    ipv4.extend(re.findall('ip4:(\S*) ', "".join(data)))
    ipv6.extend(re.findall('ip6:(\S*)', "".join(data)))

    # Create a list of IPNetwork objects.
    for ip in ipv4:
        for i in IPNetwork(ip):
            ip_list.append(i)

    for ip in ipv6:
        for i in IPNetwork(ip):
            ip_list.append(i)

    # Extract and process include values.
    includes.extend(re.findall('include:(\S*)', "".join(data)))
    for inc_ranges in includes:
        for spr_rec in res.get_txt(inc_ranges):
            spf_data = process_spf_data(res, spr_rec[2])
            if spf_data is not None:
                ip_list.extend(spf_data)

    # Return a list of IP Addresses
    return [str(ip) for ip in ip_list]


def expand_cidr(cidr_to_expand):
    """
    Function to expand a given CIDR and return an Array of IP Addresses that
    form the range covered by the CIDR.
    """
    ip_list = []
    c1 = IPNetwork(cidr_to_expand)
    return c1


def expand_range(startip, endip):
    """
    Function to expand a given range and return an Array of IP Addresses that
    form the range.
    """
    return IPRange(startip, endip)


def range2cidr(ip1, ip2):
    """
    Function to return the maximum CIDR given a range of IP's
    """
    r1 = IPRange(ip1, ip2)
    return str(r1.cidrs()[-1])


def write_to_file(data, target_file):
    """
    Function for writing returned data to a file
    """
    f = open(target_file, "w")
    f.write(data)
    f.close


def check_wildcard(res, domain_trg):
    """
    Function for checking if Wildcard resolution is configured for a Domain
    """
    wildcard = None
    test_name = ''.join(Random().sample(string.hexdigits + string.digits,
                                        12)) + '.' + domain_trg
    ips = res.get_a(test_name)

    if len(ips) > 0:
        print_debug('Wildcard resolution is enabled on this domain')
        print_debug('It is resolving to {0}'.format(''.join(ips[0][2])))
        print_debug("All queries will resolve to this address!!")
        wildcard = ''.join(ips[0][2])

    return wildcard


def brute_tlds(res, domain, verbose=False):
    """
    This function performs a check of a given domain for known TLD values.
    prints and returns a dictionary of the results.
    """
    global brtdata
    brtdata = []

    # tlds taken from http://data.iana.org/TLD/tlds-alpha-by-domain.txt
    gtld = ['co', 'com', 'net', 'biz', 'org']
    tlds = ['ac', 'ad', 'aeaero', 'af', 'ag', 'ai', 'al', 'am', 'an', 'ao', 'aq', 'ar',
            'arpa', 'as', 'asia', 'at', 'au', 'aw', 'ax', 'az', 'ba', 'bb', 'bd', 'be', 'bf', 'bg',
            'bh', 'bi', 'biz', 'bj', 'bm', 'bn', 'bo', 'br', 'bs', 'bt', 'bv', 'bw', 'by', 'bzca',
            'cat', 'cc', 'cd', 'cf', 'cg', 'ch', 'ci', 'ck', 'cl', 'cm', 'cn', 'co', 'com', 'coop',
            'cr', 'cu', 'cv', 'cx', 'cy', 'cz', 'de', 'dj', 'dk', 'dm', 'do', 'dz', 'ec', 'edu', 'ee',
            'eg', 'er', 'es', 'et', 'eu', 'fi', 'fj', 'fk', 'fm', 'fo', 'fr', 'ga', 'gb', 'gd', 'ge',
            'gf', 'gg', 'gh', 'gi', 'gl', 'gm', 'gn', 'gov', 'gp', 'gq', 'gr', 'gs', 'gt', 'gu', 'gw',
            'gy', 'hk', 'hm', 'hn', 'hr', 'ht', 'hu', 'id', 'ie', 'il', 'im', 'in', 'info', 'int',
            'io', 'iq', 'ir', 'is', 'it', 'je', 'jm', 'jo', 'jobs', 'jp', 'ke', 'kg', 'kh', 'ki', 'km',
            'kn', 'kp', 'kr', 'kw', 'ky', 'kz', 'la', 'lb', 'lc', 'li', 'lk', 'lr', 'ls', 'lt', 'lu',
            'lv', 'ly', 'ma', 'mc', 'md', 'me', 'mg', 'mh', 'mil', 'mk', 'ml', 'mm', 'mn', 'mo',
            'mobi', 'mp', 'mq', 'mr', 'ms', 'mt', 'mu', 'museum', 'mv', 'mw', 'mx', 'my', 'mz', 'na',
            'name', 'nc', 'ne', 'net', 'nf', 'ng', 'ni', 'nl', 'no', 'np', 'nr', 'nu', 'nz', 'om',
            'org', 'pa', 'pe', 'pf', 'pg', 'ph', 'pk', 'pl', 'pm', 'pn', 'pr', 'pro', 'ps', 'pt', 'pw',
            'py', 'qa', 're', 'ro', 'rs', 'ru', 'rw', 'sa', 'sb', 'sc', 'sd', 'se', 'sg', 'sh', 'si',
            'sj', 'sk', 'sl', 'sm', 'sn', 'so', 'sr', 'st', 'su', 'sv', 'sy', 'sz', 'tc', 'td', 'tel',
            'tf', 'tg', 'th', 'tj', 'tk', 'tl', 'tm', 'tn', 'to', 'tp', 'tr', 'travel', 'tt', 'tv',
            'tw', 'tz', 'ua', 'ug', 'uk', 'us', 'uy', 'uz', 'va', 'vc', 've', 'vg', 'vi', 'vn', 'vu',
            'wf', 'ws', 'ye', 'yt', 'za', 'zm', 'zw']
    found_tlds = []
    domain_main = domain.split(".")[0]

    # Let the user know how long it could take
    print_status("The operation could take up to: {0}".format(time.strftime('%H:%M:%S',
                                                                            time.gmtime(len(tlds) / 4))))

    try:
        for t in tlds:
            if verbose:
                print_status("Trying {0}".format(domain_main + "." + t))
            pool.add_task(res.get_ip, domain_main + "." + t)
            for g in gtld:
                if verbose:
                    print_status("Trying {0}".format(domain_main + "." + g + "." + t))
                pool.add_task(res.get_ip, domain_main + "." + g + "." + t)

        # Wait for threads to finish.
        pool.wait_completion()

    except (KeyboardInterrupt):
        exit_brute(pool)

    # Process the output of the threads.
    for rcd_found in brtdata:
        for rcd in rcd_found:
            if re.search(r'^A', rcd[0]):
                found_tlds.extend([{'type': rcd[0], 'name': rcd[1], 'address': rcd[2]}])

    print_good("{0} Records Found".format(len(found_tlds)))

    return found_tlds


def brute_srv(res, domain, verbose=False):
    """
    Brute-force most common SRV records for a given Domain. Returns an Array with
    records found.
    """
    global brtdata
    brtdata = []
    returned_records = []
    srvrcd = [
        '_gc._tcp.', '_kerberos._tcp.', '_kerberos._udp.', '_ldap._tcp.',
        '_test._tcp.', '_sips._tcp.', '_sip._udp.', '_sip._tcp.', '_aix._tcp.',
        '_aix._tcp.', '_finger._tcp.', '_ftp._tcp.', '_http._tcp.', '_nntp._tcp.',
        '_telnet._tcp.', '_whois._tcp.', '_h323cs._tcp.', '_h323cs._udp.',
        '_h323be._tcp.', '_h323be._udp.', '_h323ls._tcp.', '_https._tcp.',
        '_h323ls._udp.', '_sipinternal._tcp.', '_sipinternaltls._tcp.',
        '_sip._tls.', '_sipfederationtls._tcp.', '_jabber._tcp.',
        '_xmpp-server._tcp.', '_xmpp-client._tcp.', '_imap.tcp.',
        '_certificates._tcp.', '_crls._tcp.', '_pgpkeys._tcp.',
        '_pgprevokations._tcp.', '_cmp._tcp.', '_svcp._tcp.', '_crl._tcp.',
        '_ocsp._tcp.', '_PKIXREP._tcp.', '_smtp._tcp.', '_hkp._tcp.',
        '_hkps._tcp.', '_jabber._udp.', '_xmpp-server._udp.', '_xmpp-client._udp.',
        '_jabber-client._tcp.', '_jabber-client._udp.', '_kerberos.tcp.dc._msdcs.',
        '_ldap._tcp.ForestDNSZones.', '_ldap._tcp.dc._msdcs.', '_ldap._tcp.pdc._msdcs.',
        '_ldap._tcp.gc._msdcs.', '_kerberos._tcp.dc._msdcs.', '_kpasswd._tcp.', '_kpasswd._udp.',
        '_imap._tcp.']

    try:
        for srvtype in srvrcd:
            if verbose:
                print_status("Trying {0}".format(res.get_srv, srvtype + domain))
            pool.add_task(res.get_srv, srvtype + domain)

        # Wait for threads to finish.
        pool.wait_completion()

    except (KeyboardInterrupt):
        exit_brute(pool)

    # Make sure we clear the variable
    if len(brtdata) > 0:
        for rcd_found in brtdata:
            for rcd in rcd_found:
                returned_records.extend([{'type': rcd[0],
                                          'name': rcd[1],
                                          'target': rcd[2],
                                          'address': rcd[3],
                                          'port': rcd[4]}])

    else:
        print_error("No SRV Records Found for {0}".format(domain))

    print_good("{0} Records Found".format(len(returned_records)))

    return returned_records


def brute_reverse(res, ip_list, verbose=False):
    """
    Reverse look-up brute force for given CIDR example 192.168.1.1/24. Returns an
    Array of found records.
    """
    global brtdata
    brtdata = []

    returned_records = []
    print_status("Performing Reverse Lookup from {0} to {1}".format(ip_list[0], ip_list[-1]))

    # Resolve each IP in a separate thread.
    try:
        ip_range = xrange(len(ip_list) - 1)
    except NameError:
        ip_range = range(len(ip_list) - 1)

    try:
        for x in ip_range:
            ipaddress = str(ip_list[x])
            if verbose:
                print_status("Trying {0}".format(ipaddress))
            pool.add_task(res.get_ptr, ipaddress)

        # Wait for threads to finish.
        pool.wait_completion()

    except (KeyboardInterrupt):
        exit_brute(pool)

    for rcd_found in brtdata:
        for rcd in rcd_found:
            returned_records.extend([{'type': rcd[0],
                                      "name": rcd[1],
                                      'address': rcd[2]}])

    print_good("{0} Records Found".format(len(returned_records)))

    return returned_records


def brute_domain(res, dict, dom, filter=None, verbose=False, ignore_wildcard=False):
    """
    Main Function for domain brute forcing
    """
    global brtdata
    brtdata = []
    wildcard_ip = None
    found_hosts = []
    continue_brt = 'y'

    # Check if wildcard resolution is enabled
    wildcard_ip = check_wildcard(res, dom)
    if wildcard_ip and not ignore_wildcard:
        print_status('Do you wish to continue? y/n ')
        continue_brt = str(sys.stdin.readline()[:-1])
    if re.search(r'y', continue_brt, re.I):
        # Check if Dictionary file exists

        if os.path.isfile(dict):
            f = open(dict, 'r+')

            # Thread brute-force.
            try:
                for line in f:
                    if verbose:
                        print_status("Trying {0}".format(line.strip() + '.' + dom.strip()))
                    target = line.strip() + '.' + dom.strip()
                    pool.add_task(res.get_ip, target)

                # Wait for threads to finish
                pool.wait_completion()

            except (KeyboardInterrupt):
                exit_brute(pool)

        # Process the output of the threads.
        for rcd_found in brtdata:
            for rcd in rcd_found:
                if re.search(r'^A', rcd[0]):
                    # Filter Records if filtering was enabled
                    if filter:
                        if not wildcard_ip == rcd[2]:
                            found_hosts.extend([{'type': rcd[0], 'name': rcd[1], 'address': rcd[2]}])
                    else:
                        found_hosts.extend([{'type': rcd[0], 'name': rcd[1], 'address': rcd[2]}])
                elif re.search(r'^CNAME', rcd[0]):
                    found_hosts.extend([{'type': rcd[0], 'name': rcd[1], 'target': rcd[2]}])

        # Clear Global variable
        brtdata = []

    print_good("{0} Records Found".format(len(found_hosts)))
    return found_hosts


def in_cache(dict_file, ns):
    """
    Function for Cache Snooping, it will check a given NS server for specific
    type of records for a given domain are in it's cache.
    """
    found_records = []
    f = open(dict_file, 'r+')
    for zone in f:
        dom_to_query = str.strip(zone)
        query = dns.message.make_query(dom_to_query, dns.rdatatype.A, dns.rdataclass.IN)
        query.flags ^= dns.flags.RD
        answer = dns.query.udp(query, ns)
        if len(answer.answer) > 0:
            for an in answer.answer:
                for rcd in an:
                    if rcd.rdtype == 1:
                        print_status("\tName: {0} TTL: {1} Address: {2} Type: A".format(an.name, an.ttl, rcd.address))

                        found_records.extend([{'type': "A", 'name': an.name,
                                               'address': rcd.address, 'ttl': an.ttl}])

                    elif rcd.rdtype == 5:
                        print_status("\tName: {0} TTL: {1} Target: {2} Type: CNAME".format(an.name, an.ttl, rcd.target))
                        found_records.extend([{'type': "CNAME", 'name': an.name,
                                               'target': rcd.target, 'ttl': an.ttl}])

                    else:
                        print_status()
    return found_records


def scrape_google(dom):
    """
    Function for enumerating sub-domains and hosts by scrapping Google.
    """
    results = []
    filtered = []
    searches = ["100", "200", "300", "400", "500"]
    data = ""
    urllib._urlopener = AppURLopener()

    for n in searches:
        url = "http://google.com/search?hl=en&lr=&ie=UTF-8&q=%2B" + dom + "&start=" + n + "&sa=N&filter=0&num=100"
        sock = urllib.urlopen(url)
        data += sock.read()
        sock.close()
    results.extend(unique(re.findall("htt\w{1,2}:\/\/([^:?]*[a-b0-9]*[^:?]*\." + dom + ")\/", data)))

    # Make sure we are only getting the host
    for f in results:
        filtered.extend(re.findall("^([a-z.0-9^]*" + dom + ")", f))
    time.sleep(2)
    return unique(filtered)


def goo_result_process(res, found_hosts):
    """
    This function processes the results returned from the Google Search and does
    an A and AAAA query for the IP of the found host. Prints and returns a dictionary
    with all the results found.
    """
    returned_records = []
    for sd in found_hosts:
        for sdip in res.get_ip(sd):
            if re.search(r'^A|CNAME', sdip[0]):
                print_status('\t {0} {1} {2}'.format(sdip[0], sdip[1], sdip[2]))
                if re.search(r'^A', sdip[0]):
                    returned_records.extend([{'type': sdip[0], 'name': sdip[1],
                                              'address': sdip[2]}])
                else:
                    returned_records.extend([{'type': sdip[0], 'name': sdip[1],
                                              'target': sdip[2]}])

    print_good("{0} Records Found".format(len(returned_records)))
    return returned_records


def get_whois_nets_iplist(ip_list):
    """
    This function will perform whois queries against a list of IP's and extract
    the net ranges and if available the organization list of each and remover any
    duplicate entries.
    """
    seen = {}
    idfun = repr
    found_nets = []
    for ip in ip_list:
        if ip != "no_ip":
            # Find appropiate Whois Server for the IP
            whois_server = get_whois(ip)
            # If we get a Whois server Process get the whois and process.
            if whois_server:
                whois_data = whois(ip, whois_server)
                arin_style = re.search('NetRange', whois_data)
                ripe_apic_style = re.search('netname', whois_data)
                if (arin_style or ripe_apic_style):
                    net = get_whois_nets(whois_data)
                    if net:
                        for network in net:
                            org = get_whois_orgname(whois_data)
                            found_nets.append({'start': network[0], 'end': network[1], 'orgname': "".join(org)})
                else:
                    for line in whois_data.splitlines():
                        recordentrie = re.match('^(.*)\s\S*-\w*\s\S*\s(\S*\s-\s\S*)', line)
                        if recordentrie:
                            org = recordentrie.group(1)
                            net = get_whois_nets(recordentrie.group(2))
                            for network in net:
                                found_nets.append({'start': network[0], 'end': network[1], 'orgname': "".join(org)})
    #Remove Duplicates
    return [seen.setdefault(idfun(e), e) for e in found_nets if idfun(e) not in seen]


def whois_ips(res, ip_list):
    """
    This function will process the results of the whois lookups and present the
    user with the list of net ranges found and ask the user if he wishes to perform
    a reverse lookup on any of the ranges or all the ranges.
    """
    answer = ""
    found_records = []
    print_status("Performing Whois lookup against records found.")
    list = get_whois_nets_iplist(unique(ip_list))
    if len(list) > 0:
        print_status("The following IP Ranges where found:")
        for i in range(len(list)):
            print_status(
                "\t {0} {1}-{2} {3}".format(str(i) + ")", list[i]['start'], list[i]['end'], list[i]['orgname']))
        print_status('What Range do you wish to do a Revers Lookup for?')
        print_status('number, comma separated list, a for all or n for none')
        val = sys.stdin.readline()[:-1]
        answer = str(val).split(",")

        if "a" in answer:
            for i in range(len(list)):
                print_status("Performing Reverse Lookup of range {0}-{1}".format(list[i]['start'], list[i]['end']))
                found_records.append(brute_reverse(res, expand_range(list[i]['start'], list[i]['end'])))

        elif "n" in answer:
            print_status("No Reverse Lookups will be performed.")
            pass
        else:
            for a in answer:
                net_selected = list[int(a)]
                print_status(net_selected['orgname'])
                print_status(
                    "Performing Reverse Lookup of range {0}-{1}".format(net_selected['start'], net_selected['end']))
                found_records.append(brute_reverse(res, expand_range(net_selected['start'], net_selected['end'])))
    else:
        print_error("No IP Ranges where found in the Whois query results")

    return found_records


def prettify(elem):
    """
    Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")


def dns_record_from_dict(record_dict_list, scan_info, domain):
    """
    Saves DNS Records to XML Given a a list of dictionaries each representing
    a record to be saved, returns the XML Document formatted.
    """

    xml_doc = Element("records")
    for r in record_dict_list:
        elem = Element("record")
        if type(r) is not str:
            try:
                for k, v in r.items():
                    elem.attrib[k] = v
                xml_doc.append(elem)
            except AttributeError:
                continue

    scanelem = Element("scaninfo")
    scanelem.attrib["arguments"] = scan_info[0]
    scanelem.attrib["time"] = scan_info[1]
    xml_doc.append(scanelem)
    if domain is not None:
        domelem = Element("domain")
        domelem.attrib["domain_name"] = domain
        xml_doc.append(domelem)
    return prettify(xml_doc)


def create_db(db):
    """
    Function will create the specified database if not present and it will create
    the table needed for storing the data returned by the modules.
    """

    # Connect to the DB
    con = sqlite3.connect(db)

    # Create SQL Queries to be used in the script
    make_table = """CREATE TABLE data (
    serial integer  Primary Key Autoincrement,
    type TEXT(8),
    name TEXT(32),
    address TEXT(32),
    target TEXT(32),
    port TEXT(8),
    text TEXT(256),
    zt_dns TEXT(32)
    )"""

    # Set the cursor for connection
    con.isolation_level = None
    cur = con.cursor()

    # Connect and create table
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data';")
    if cur.fetchone() is None:
        cur.execute(make_table)
        con.commit()
    else:
        pass


def make_csv(data):
    csv_data = "Type,Name,Address,Target,Port,String\n"
    for n in data:

        if re.search(r'PTR|^[A]$|AAAA', n['type']):
            csv_data += n['type'] + "," + n['name'] + "," + n['address'] + "\n"

        elif re.search(r'NS', n['type']):
            csv_data += n['type'] + "," + n['target'] + "," + n['address'] + "\n"

        elif re.search(r'SOA', n['type']):
            csv_data += n['type'] + "," + n['mname'] + "," + n['address'] + "\n"

        elif re.search(r'MX', n['type']):
            csv_data += n['type'] + "," + n['exchange'] + "," + n['address'] + "\n"

        elif re.search(r'SPF', n['type']):
            if "zone_server" in n:
                csv_data += n['type'] + ",,,,,\'" + n['strings'] + "\'\n"
            else:
                csv_data += n['type'] + ",,,,,\'" + n['strings'] + "\'\n"

        elif re.search(r'TXT', n['type']):
            if "zone_server" in n:
                csv_data += n['type'] + ",,,,,\'" + n['strings'] + "\'\n"
            else:
                csv_data += n['type'] + "," + n['name'] + ",,,,\'" + n['strings'] + "\'\n"

        elif re.search(r'SRV', n['type']):
            csv_data += n['type'] + "," + n['name'] + "," + n['address'] + "," + n['target'] + "," + n['port'] + "\n"

        elif re.search(r'CNAME', n['type']):
            csv_data += n['type'] + "," + n['name'] + ",," + n['target'] + ",\n"

        else:
            # Handle not common records
            t = n['type']
            del n['type']
            record_data = "".join(['%s =%s,' % (key, value) for key, value in n.items()])
            records = [t, record_data]
            csv_data + records[0] + ",,,,," + records[1] + "\n"

    return csv_data


def write_json(jsonfile, data, scan_info):
    scaninfo = {'type': 'ScanInfo', 'arguments': scan_info[0], 'date': scan_info[1]}
    data.insert(0, scaninfo)
    json_data = json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))
    write_to_file(json_data, jsonfile)


def write_db(db, data):
    """
    Function to write DNS Records SOA, PTR, NS, A, AAAA, MX, TXT, SPF and SRV to
    DB.
    """

    con = sqlite3.connect(db)
    # Set the cursor for connection
    con.isolation_level = None
    cur = con.cursor()


    # Normalize the dictionary data
    for n in data:

        if re.match(r'PTR|^[A]$|AAAA', n['type']):
            query = 'insert into data( type, name, address ) ' + \
                    'values( "%(type)s", "%(name)s","%(address)s" )' % n

        elif re.match(r'NS', n['type']):
            query = 'insert into data( type, name, address ) ' + \
                    'values( "%(type)s", "%(target)s", "%(address)s" )' % n

        elif re.match(r'SOA', n['type']):
            query = 'insert into data( type, name, address ) ' + \
                    'values( "%(type)s", "%(mname)s", "%(address)s" )' % n

        elif re.match(r'MX', n['type']):
            query = 'insert into data( type, name, address ) ' + \
                    'values( "%(type)s", "%(exchange)s", "%(address)s" )' % n

        elif re.match(r'TXT', n['type']):
            query = 'insert into data( type, name, text) ' + \
                    'values( "%(type)s", "%(name)s" ,"%(strings)s" )' % n

        elif re.match(r'SPF', n['type']):
            query = 'insert into data( type, text) ' + \
                    'values( "%(type)s","%(text)s" )' % n

        elif re.match(r'SPF', n['type']):
            query = 'insert into data( type, text) ' + \
                    'values( "%(type)s","%(text)s" )' % n

        elif re.match(r'SRV', n['type']):
            query = 'insert into data( type, name, target, address, port ) ' + \
                    'values( "%(type)s", "%(name)s" , "%(target)s", "%(address)s" ,"%(port)s" )' % n

        elif re.match(r'CNAME', n['type']):
            query = 'insert into data( type, name, target ) ' + \
                    'values( "%(type)s", "%(name)s" , "%(target)s" )' % n

        else:
            # Handle not common records
            t = n['type']
            del n['type']
            record_data = "".join(['%s=%s,' % (key, value) for key, value in n.items()])
            records = [t, record_data]
            query = "insert into data(type,text) values ('" + \
                    records[0] + "','" + records[1] + "')"

        # Execute Query and commit
        cur.execute(query)
        con.commit()


def get_nsec_type(domain, res):
    target = "0." + domain

    answer = get_a_answer(target, res._res.nameservers[0], res._res.timeout)
    for a in answer.authority:
        if a.rdtype == 50:
            return "NSEC3"
        elif a.rdtype == 47:
            return "NSEC"


def dns_sec_check(domain, res):
    """
    Check if a zone is configured for DNSSEC and if so if NSEC or NSEC3 is used.
    """
    try:
        answer = res._res.query(domain, 'DNSKEY')
        print_status("DNSSEC is configured for {0}".format(domain))
        nsectype = get_nsec_type(domain, res)
        print_status("DNSKEYs:")
        for rdata in answer:
            if rdata.flags == 256:
                key_type = "ZSK"

            if rdata.flags == 257:
                key_type = "KSk"

            print_status("\t{0} {1} {2} {3}".format(nsectype, key_type, algorithm_to_text(rdata.algorithm),
                                                    dns.rdata._hexify(rdata.key)))

    except dns.resolver.NXDOMAIN:
        print_error("Could not resolve domain: {0}".format(domain))
        sys.exit(1)

    except dns.exception.Timeout:
        print_error("A timeout error occurred please make sure you can reach the target DNS Servers")
        print_error("directly and requests are not being filtered. Increase the timeout from {0} second".format(
            res._res.timeout))
        print_error("to a higher number with --lifetime <time> option.")
        sys.exit(1)
    except dns.resolver.NoAnswer:
        print_error("DNSSEC is not configured for {0}".format(domain))


def check_bindversion(ns_server, timeout):
    """
    Check if the version of Bind can be queried for.
    """
    version = ""
    request = dns.message.make_query('version.bind', 'txt', 'ch')
    try:
        response = dns.query.udp(request, ns_server, timeout=timeout, one_rr_per_rrset=True)
        if (len(response.answer) > 0):
            print_status("\t Bind Version for {0} {1}".format(ns_server, response.answer[0].items[0].strings[0]))
            version = response.answer[0].items[0].strings[0]
    except (dns.resolver.NXDOMAIN, dns.exception.Timeout, dns.resolver.NoAnswer, socket.error, dns.query.BadResponse):
        return version
    return version


def check_recursive(ns_server):
    """
    Check if a NS Server is recursive.
    """
    is_recursive = False
    query = dns.message.make_query('www.google.com.', dns.rdatatype.NS)
    try:
        response = dns.query.udp(query, ns_server)
        recursion_flag_pattern = "\.*RA\.*"
        flags = dns.flags.to_text(response.flags)
        result = re.findall(recursion_flag_pattern, flags)
        if (result):
            print_error("\t Recursion enabled on NS Server {0}".format(ns_server))
        is_recursive = True
    except (socket.error):
        return is_recursive
    return is_recursive


def general_enum(res, domain, do_axfr, do_google, do_spf, do_whois, zw):
    """
    Function for performing general enumeration of a domain. It gets SOA, NS, MX
    A, AAA and SRV records for a given domain.It Will first try a Zone Transfer
    if not successful it will try individual record type enumeration. If chosen
    it will also perform a Google Search and scrape the results for host names and
    perform an A and AAA query against them.
    """
    returned_records = []

    # Var for SPF Record Range Reverse Look-up
    found_spf_ranges = []

    # Var to hold the IP Addresses that will be queried in Whois
    ip_for_whois = []

    # Check if wildcards are enabled on the target domain
    check_wildcard(res, domain)

    # To identify when the records come from a Zone Transfer
    from_zt = None

    # Perform test for Zone Transfer against all NS servers of a Domain
    if do_axfr is not None:
        zonerecs = res.zone_transfer()
        if zonerecs is not None:
            returned_records.extend(res.zone_transfer())
            if len(returned_records) == 0:
                from_zt = True

    # If a Zone Trasfer was possible there is no need to enumerate the rest
    if from_zt is None:

        # Check if DNSSEC is configured
        dns_sec_check(domain, res)

        # Enumerate SOA Record

        try:
            found_soa_records = res.get_soa()
            for found_soa_record in found_soa_records:
                print_status('\t {0} {1} {2}'.format(found_soa_record[0], found_soa_record[1], found_soa_record[2]))

                # Save dictionary of returned record
                returned_records.extend([{'type': found_soa_record[0],
                                          "mname": found_soa_record[1], 'address': found_soa_record[2]}])

                ip_for_whois.append(found_soa_record[2])

        except:
            print_error("Could not Resolve SOA Record for {0}".format(domain))

        # Enumerate Name Servers
        try:
            for ns_rcrd in res.get_ns():
                print_status('\t {0} {1} {2}'.format(ns_rcrd[0], ns_rcrd[1], ns_rcrd[2]))

                # Save dictionary of returned record
                recursive = check_recursive(ns_rcrd[2])
                bind_ver = check_bindversion(ns_rcrd[2], res._res.timeout)
                returned_records.extend([
                    {'type': ns_rcrd[0], "target": ns_rcrd[1], 'address': ns_rcrd[2], 'recursive': str(recursive),
                     "Version": bind_ver}])
                ip_for_whois.append(ns_rcrd[2])

        except dns.resolver.NoAnswer:
            print_error("Could not Resolve NS Records for {0}".format(domain))

        # Enumerate MX Records
        try:
            for mx_rcrd in res.get_mx():
                print_status('\t {0} {1} {2}'.format(mx_rcrd[0], mx_rcrd[1], mx_rcrd[2]))

                # Save dictionary of returned record
                returned_records.extend([{'type': mx_rcrd[0], "exchange": mx_rcrd[1], 'address': mx_rcrd[2]}])

                ip_for_whois.append(mx_rcrd[2])

        except dns.resolver.NoAnswer:
            print_error("Could not Resolve MX Records for {0}".format(domain))

        # Enumerate A Record for the targeted Domain
        for a_rcrd in res.get_ip(domain):
            print_status('\t {0} {1} {2}'.format(a_rcrd[0], a_rcrd[1], a_rcrd[2]))

            # Save dictionary of returned record
            returned_records.extend([{'type': a_rcrd[0], "name": a_rcrd[1], 'address': a_rcrd[2]}])

            ip_for_whois.append(a_rcrd[2])

        # Enumerate SFP and TXT Records for the target domain
        text_data = ""
        spf_text_data = res.get_spf()

        # Save dictionary of returned record
        if spf_text_data is not None:
            for s in spf_text_data:
                print_status('\t {0} {1}'.format(s[0], s[1]))
                text_data = s[1]
                returned_records.extend([{'type': s[0], "strings": s[1]}])

        txt_text_data = res.get_txt()

        # Save dictionary of returned record
        if txt_text_data is not None:
            for t in txt_text_data:
                print_status('\t {0} {1} {2}'.format(t[0], t[1], t[2]))
                text_data += t[2]
                returned_records.extend([{'type': t[0], 'name': t[1], "strings": t[2]}])

        domainkey_text_data = res.get_txt("_domainkey." + domain)

        # Save dictionary of returned record
        if domainkey_text_data is not None:
            for t in domainkey_text_data:
                print_status('\t {0} {1} {2}'.format(t[0], t[1], t[2]))
                text_data += t[2]
                returned_records.extend([{'type': t[0], 'name': t[1], "strings": t[2]}])

        # Process SPF records if selected
        if do_spf is not None and len(text_data) > 0:
            print_status("Expanding IP ranges found in DNS and TXT records for Reverse Look-up")
            found_spf_ranges.extend(process_spf_data(res, text_data))
            if len(found_spf_ranges) > 0:
                print_status("Performing Reverse Look-up of SPF Ranges")
                returned_records.extend(brute_reverse(res, unique(found_spf_ranges)))
            else:
                print_status("No IP Ranges where found in SPF and TXT Records")

        # Enumerate SRV Records for the targeted Domain
        print_status('Enumerating SRV Records')
        srv_rcd = brute_srv(res, domain)
        if srv_rcd:
            for r in srv_rcd:
                ip_for_whois.append(r['address'])
                returned_records.append(r)

        # Do Google Search enumeration if selected
        if do_google is not None:
            print_status('Performing Google Search Enumeration')
            goo_rcd = goo_result_process(res, scrape_google(domain))
            if goo_rcd:
                for r in goo_rcd:
                    if 'address' in goo_rcd:
                        ip_for_whois.append(r['address'])
                returned_records.extend(goo_rcd)

        if do_whois:
            whois_rcd = whois_ips(res, ip_for_whois)
            returned_records.extend(whois_rcd)

        if zw:
            zone_info = ds_zone_walk(res, domain)
            if zone_info:
                returned_records.extend(zone_info)

        return returned_records

        #sys.exit(0)


def query_ds(target, ns, timeout=5.0):
    """
    Function for performing DS Record queries. Retuns answer object. Since a
    timeout will break the DS NSEC chain of a zone walk it will exit if a timeout
    happens.
    """
    try:
        query = dns.message.make_query(target, dns.rdatatype.DS, dns.rdataclass.IN)
        query.flags += dns.flags.CD
        query.use_edns(edns=True, payload=4096)
        query.want_dnssec(True)
        answer = dns.query.udp(query, ns, timeout)
    except dns.exception.Timeout:
        print_error("A timeout error occurred please make sure you can reach the target DNS Servers")
        print_error(
            "directly and requests are not being filtered. Increase the timeout from {0} second".format(timeout))
        print_error("to a higher number with --lifetime <time> option.")
        sys.exit(1)
    except:
        print("Unexpected error: {0}".format(sys.exc_info()[0]))
        raise
    return answer


def get_constants(prefix):
    """
    Create a dictionary mapping socket module constants to their names.
    """
    return dict((getattr(socket, n), n)
                for n in dir(socket)
                if n.startswith(prefix))


def socket_resolv(target):
    """
    Resolve IPv4 and IPv6 .
    """
    found_recs = []
    families = get_constants('AF_')
    types = get_constants('SOCK_')
    try:
        for response in socket.getaddrinfo(target, 0):
            # Unpack the response tuple
            family, socktype, proto, canonname, sockaddr = response
            if families[family] == "AF_INET" and types[socktype] == "SOCK_DGRAM":
                found_recs.append(["A", target, sockaddr[0]])
            elif families[family] == "AF_INET6" and types[socktype] == "SOCK_DGRAM":
                found_recs.append(["AAAA", target, sockaddr[0]])
    except:
        return found_recs
    return found_recs


def lookup_next(target, res):
    """
    Try to get the most accurate information for the record found.
    """
    res_sys = DnsHelper(target)
    returned_records = []

    if re.search("^_[A-Za-z0-9_-]*._[A-Za-z0-9_-]*.", target, re.I):
        srv_answer = res.get_srv(target)
        if len(srv_answer) > 0:
            for r in srv_answer:
                print_status("\t {0}".format(" ".join(r)))
                returned_records.append({'type': r[0],
                                         'name': r[1],
                                         'target': r[2],
                                         'address': r[3],
                                         'port': r[4]})

    elif re.search("(_autodiscover\\.|_spf\\.|_domainkey\\.)", target, re.I):
        txt_answer = res.get_txt(target)
        if len(txt_answer) > 0:
            for r in txt_answer:
                print_status("\t {0}".format(" ".join(r)))
                returned_records.append({'type': r[0],
                                         'name': r[1], 'strings': r[2]})
        else:
            txt_answer = res_sys.get_tx(target)
            if len(txt_answer) > 0:
                for r in txt_answer:
                    print_status("\t {0}".format(" ".join(r)))
                    returned_records.append({'type': r[0],
                                             'name': r[1], 'strings': r[2]})
            else:
                print_status('\t A {0} no_ip'.format(target))
                returned_records.append({'type': 'A', 'name': target, 'address': "no_ip"})

    else:
        a_answer = res.get_ip(target)
        if len(a_answer) > 0:
            for r in a_answer:
                print_status('\t {0} {1} {2}'.format(r[0], r[1], r[2]))
                if r[0] == 'CNAME':
                    returned_records.append({'type': r[0], 'name': r[1], 'target': r[2]})
                else:
                    returned_records.append({'type': r[0], 'name': r[1], 'address': r[2]})
        else:
            a_answer = socket_resolv(target)
            if len(a_answer) > 0:
                for r in a_answer:
                    print_status('\t {0} {1} {2}'.format(r[0], r[1], r[2]))
                    returned_records.append({'type': r[0], 'name': r[1], 'address': r[2]})
            else:
                print_status('\t A {0} no_ip'.format(target))
                returned_records.append({'type': 'A', 'name': target, 'address': "no_ip"})

    return returned_records


def get_a_answer(target, ns, timeout):
    query = dns.message.make_query(target, dns.rdatatype.A, dns.rdataclass.IN)
    query.flags += dns.flags.CD
    query.use_edns(edns=True, payload=4096)
    query.want_dnssec(True)
    answer = dns.query.udp(query, ns, timeout)
    return answer


def get_next(target, ns, timeout):
    next_host = None
    response = get_a_answer(target, ns, timeout)
    for a in response.authority:
        if a.rdtype == 47:
            for r in a:
                next_host = r.next.to_text()[:-1]
    return next_host


def ds_zone_walk(res, domain):
    """
    Perform DNSSEC Zone Walk using NSEC records found the the error additional
    records section of the message to find the next host to query int he zone.
    """
    print_status("Performing NSEC Zone Walk for {0}".format(domain))

    print_status("Getting SOA record for {0}".format(domain))
    soa_rcd = res.get_soa()[0][2]

    print_status("Name Server {0} will be used".format(soa_rcd))
    res = DnsHelper(domain, soa_rcd, 3)
    nameserver = soa_rcd

    timeout = res._res.timeout

    records = []

    transformations = [
        # Send the hostname as-is
        lambda h, hc, dc: h,

        # Prepend a zero as a subdomain
        lambda h, hc, dc: "0.{0}".format(h),

        # Append a hyphen to the host portion
        lambda h, hc, dc: "{0}-.{1}".format(hc, dc),

        # Double the last character of the host portion
        lambda h, hc, dc: "{0}{1}.{2}".format(hc, hc[-1], dc)
    ]

    pending = set([domain])
    finished = set()

    try:
        while pending:
            # Get the next pending hostname
            hostname = pending.pop()
            finished.add(hostname)

            # Get all the records we can for the hostname
            records.extend(lookup_next(hostname, res))

            # Arrange the arguments for the transformations
            fields = re.search("(^[^.]*).(\S*)", hostname)
            params = [hostname, fields.group(1), fields.group(2)]

            for transformation in transformations:
                # Apply the transformation
                target = transformation(*params)

                # Perform a DNS query for the target and process the response
                response = get_a_answer(target, nameserver, timeout)
                for a in response.authority:
                    if a.rdtype != 47:
                        continue

                    # NSEC records give two results:
                    #   1) The previous existing hostname that is signed
                    #   2) The subsequent existing hostname that is signed
                    # Add the latter to our list of pending hostnames
                    for r in a:
                        pending.add(r.next.to_text()[:-1])

            # Ensure nothing pending has already been queried
            pending -= finished

    except (KeyboardInterrupt):
        print_error("You have pressed Ctrl + C. Saving found records.")

    except (dns.exception.Timeout):
        print_error("A timeout error occurred while performing the zone walk please make ")
        print_error("sure you can reach the target DNS Servers directly and requests")
        print_error("are not being filtered. Increase the timeout to a higher number")
        print_error("with --lifetime <time> option.")

    # Give a summary of the walk
    if len(records) > 0:
        print_good("{0} records found".format(len(records)))
    else:
        print_error("Zone could not be walked")

    return records


def usage():
    print("Version: {0}".format(__version__))
    print("Usage: dnsrecon.py <options>\n")
    print("Options:")
    print("   -h, --help                  Show this help message and exit")
    print("   -d, --domain      <domain>  Domain to Target for enumeration.")
    print("   -r, --range       <range>   IP Range for reverse look-up brute force in formats (first-last)")
    print("                               or in (range/bitmask).")
    print("   -n, --name_server <name>    Domain server to use, if none is given the SOA of the")
    print("                               target will be used")
    print("   -D, --dictionary  <file>    Dictionary file of sub-domain and hostnames to use for")
    print("                               brute force.")
    print("   -f                          Filter out of Brute Force Domain lookup records that resolve to")
    print("                               the wildcard defined IP Address when saving records.")
    print("   -t, --type        <types>   Specify the type of enumeration to perform:")
    print("                               std      To Enumerate general record types, enumerates.")
    print("                                        SOA, NS, A, AAAA, MX and SRV if AXRF on the")
    print("                                        NS Servers fail.\n")
    print("                               rvl      To Reverse Look Up a given CIDR IP range.\n")
    print("                               brt      To Brute force Domains and Hosts using a given")
    print("                                        dictionary.\n")
    print("                               srv      To Enumerate common SRV Records for a given \n")
    print("                                        domain.\n")
    print("                               axfr     Test all NS Servers in a domain for misconfigured")
    print("                                        zone transfers.\n")
    print("                               goo      Perform Google search for sub-domains and hosts.\n")
    print("                               snoop    To Perform a Cache Snooping against all NS ")
    print("                                        servers for a given domain, testing all with")
    print("                                        file containing the domains, file given with -D")
    print("                                        option.\n")
    print("                               tld      Will remove the TLD of given domain and test against")
    print("                                        all TLD's registered in IANA\n")
    print("                               zonewalk Will perform a DNSSEC Zone Walk using NSEC Records.\n")
    print("   -a                          Perform AXFR with the standard enumeration.")
    print("   -s                          Perform Reverse Look-up of ipv4 ranges in the SPF Record of the")
    print("                               targeted domain with the standard enumeration.")
    print("   -g                          Perform Google enumeration with the standard enumeration.")
    print("   -w                          Do deep whois record analysis and reverse look-up of IP")
    print("                               ranges found thru whois when doing standard query.")
    print("   -z                          Performs a DNSSEC Zone Walk with the standard enumeration.")
    print("   --threads          <number> Number of threads to use in Range Reverse Look-up, Forward")
    print("                               Look-up Brute force and SRV Record Enumeration")
    print("   --lifetime         <number> Time to wait for a server to response to a query.")
    print("   --db               <file>   SQLite 3 file to save found records.")
    print("   --xml              <file>   XML File to save found records.")
    print("   --iw                        Continua bruteforcing a domain even if a wildcard record resolution is ")
    print("                               discovered.")
    print("   -c, --csv          <file>   Comma separated value file.")
    print("   -j, --json         <file>   JSON file.")
    print("   -v                          Show attempts in the bruteforce modes.")
    sys.exit(0)


# Main
#-------------------------------------------------------------------------------
def main():
    #
    # Option Variables
    #

    returned_records = []
    domain = None
    ns_server = None
    output_file = None
    dict = None
    type = None
    xfr = None
    goo = None
    spf_enum = None
    do_whois = None
    thread_num = 10
    request_timeout = 3.0
    ip_range = None
    results_db = None
    zonewalk = None
    csv_file = None
    json_file = None
    wildcard_filter = False
    verbose = False
    ignore_wildcardrr = False

    #
    # Global Vars
    #

    global pool

    #
    # Define options
    #
    try:
        options, args = getopt.getopt(sys.argv[1:], 'hzd:n:x:D:t:aq:gwr:fsc:vj:',
                                      ['help',
                                       'zone_walk'
                                       'domain=',
                                       'name_server=',
                                       'xml=',
                                       'dictionary=',
                                       'type=',
                                       'axfr',
                                       'google',
                                       'do_whois',
                                       'range=',
                                       'do_spf',
                                       'csv=',
                                       'lifetime=',
                                       'threads=',
                                       'db=',
                                       'iw',
                                       'verbose',
                                       'json='])

    except getopt.GetoptError:
        print_error("Wrong Option Provided!")
        usage()
    #
    # Parse options
    #
    for opt, arg in options:
        if opt in ('-t', '--type'):
            type = arg

        elif opt in ('-d', '--domain'):
            domain = arg

        elif opt in ('-n', '--name_server'):
            # Check if we got an IP or a FQDN
            if netaddr.valid_glob(arg):
                ns_server = arg
            else:
                # Resolve in the case if FQDN
                answer = socket_resolv(arg)
                # Check we actually got a list
                if len(answer) > 0:
                    # We will use the first IP found as the NS
                    ns_server = answer[0][2]
                else:
                    # Exit if we cannot resolve it
                    print_error("Could not resolve NS server provided")
                    sys.exit(1)

        elif opt in ('-x', '--xml'):
            output_file = arg

        elif opt in ('-D', '--dictionary'):
            #Check if the dictionary file exists
            if os.path.isfile(arg):
                dict = arg
            else:
                print_error("File {0} does not exist!".format(arg))
                exit(1)

        elif opt in ('-r', '--range'):
            ip_list = process_range(arg)
            if len(ip_list) > 0:
                if type is None:
                    type = "rvl"
                elif not re.search(r'rvl', type):
                    type = "rvl," + type
            else:
                usage()
                sys.exit(1)

        elif opt in ('--theads'):
            thread_num = int(arg)

        elif opt in ('--lifetime'):
            request_timeout = float(arg)

        elif opt in ('--db'):
            results_db = arg

        elif opt in ('-c', '--csv'):
            csv_file = arg

        elif opt in ('-j', '--json'):
            json_file = arg

        elif opt in ('-v', '--verbose'):
            verbose = True

        elif opt in ('--iw'):
            ignore_wildcardrr = True

        elif opt in ('-h'):
            usage()

    # Make sure standard enumeration modificators are set.
    if ('-a' in sys.argv) or ('--axfr' in sys.argv):
        xfr = True

    if ('-g' in sys.argv) or ('--google' in sys.argv):
        goo = True

    if ('-w' in sys.argv) or ('--do_whois' in sys.argv):
        do_whois = True

    if ('-z' in sys.argv) or ('--zone_walk' in sys.argv):
        zonewalk = True

    if ('-s' in sys.argv) or ('--do_spf' in sys.argv):
        spf_enum = True

    if ('-f' in sys.argv):
        wildcard_filter = True

    # Setting the number of threads to 10
    pool = ThreadPool(thread_num)

    # Set the resolver
    res = DnsHelper(domain, ns_server, request_timeout)

    domain_req = ['axfr', 'std', 'srv', 'tld', 'goo', 'zonewalk']
    scan_info = [" ".join(sys.argv), str(datetime.datetime.now())]

    if type is not None:
        for r in type.split(','):
            if r in domain_req and domain is None:
                print_error('No Domain to target specified!')
                sys.exit(1)
            try:
                if r == 'axfr':
                    print_status('Testing NS Servers for Zone Transfer')
                    zonercds = res.zone_transfer()
                    if zonercds:
                        returned_records.extend(zonercds)
                    else:
                        print_error("No records were returned in the zone transfer attempt.")

                elif r == 'std':
                    print_status("Performing General Enumeration of Domain:".format(domain))
                    std_enum_records = general_enum(res, domain, xfr, goo,
                                                    spf_enum, do_whois, zonewalk)

                    if (output_file is not None) or (results_db is not None) or (csv_file is not None):
                        returned_records.extend(std_enum_records)

                elif r == 'rvl':
                    if len(ip_list) > 0:
                        print_status('Reverse Look-up of a Range')
                        rvl_enum_records = brute_reverse(res, ip_list, verbose)

                        if (output_file is not None) or (results_db is not None) or (csv_file is not None):
                            returned_records.extend(rvl_enum_records)
                    else:
                        print_error('Failed CIDR or Range is Required for type rvl')

                elif r == 'brt':
                    if (dict is not None) and (domain is not None):
                        print_status('Performing host and subdomain brute force against {0}'.format(domain))
                        brt_enum_records = brute_domain(res, dict, domain, wildcard_filter, verbose, ignore_wildcardrr)

                        if (output_file is not None) or (results_db is not None) or (csv_file is not None):
                            returned_records.extend(brt_enum_records)
                    elif (domain is not None):
                        script_dir = os.path.dirname(os.path.realpath(__file__)) + os.sep
                        print_status("No file was specified with domains to check.")
                        name_list_dic = script_dir + "namelist.txt"
                        if os.path.isfile(name_list_dic):
                            print_status("Using file provided with tool: " + name_list_dic)
                            brt_enum_records = brute_domain(res, name_list_dic, domain, wildcard_filter, verbose,
                                                            ignore_wildcardrr)
                        else:
                            print_error("File {0} does not exist!".format(name_list_dic))
                            exit(1)
                    else:
                        print_error('Could not execute a brute force enumeration. A domain was not given.')
                        sys.exit(1)

                elif r == 'srv':
                    print_status('Enumerating Common SRV Records against {0}'.format(domain))
                    srv_enum_records = brute_srv(res, domain, verbose)

                    if (output_file is not None) or (results_db is not None) or (csv_file is not None):
                        returned_records.extend(srv_enum_records)

                elif r == 'tld':
                    print_status("Performing TLD Brute force Enumeration against {0}".format(domain))
                    tld_enum_records = brute_tlds(res, domain, verbose)
                    if (output_file is not None) or (results_db is not None) or (csv_file is not None):
                        returned_records.extend(tld_enum_records)

                elif r == 'goo':
                    print_status("Performing Google Search Enumeration against {0}".format(domain))
                    goo_enum_records = goo_result_process(res, scrape_google(domain))
                    if (output_file is not None) or (results_db is not None) or (csv_file is not None):
                        returned_records.extend(goo_enum_records)

                elif r == "snoop":
                    if (dict is not None) and (ns_server is not None):
                        print_status("Performing Cache Snooping against NS Server: {0}".format(ns_server))
                        cache_enum_records = in_cache(dict, ns_server)
                        if (output_file is not None) or (results_db is not None) or (csv_file is not None):
                            returned_records.extend(cache_enum_records)

                    else:
                        print_error('No Domain or Name Server to target specified!')
                        sys.exit(1)

                elif r == "zonewalk":
                    if (output_file is not None) or (results_db is not None) or (csv_file is not None):
                        returned_records.extend(ds_zone_walk(res, domain))
                    else:
                        ds_zone_walk(res, domain)

                else:
                    print_error("This type of scan is not in the list {0}".format(r))
                    usage()

            except dns.resolver.NXDOMAIN:
                print_error("Could not resolve domain: {0}".format(domain))
                sys.exit(1)

            except dns.exception.Timeout:
                print_error("A timeout error occurred please make sure you can reach the target DNS Servers")
                print_error("directly and requests are not being filtered. Increase the timeout from {0} second".format(
                    request_timeout))
                print_error("to a higher number with --lifetime <time> option.")
                sys.exit(1)

        # if an output xml file is specified it will write returned results.
        if (output_file is not None):
            print_status("Saving records to XML file: {0}".format(output_file, scan_info))
            xml_enum_doc = dns_record_from_dict(returned_records, scan_info, domain)
            write_to_file(xml_enum_doc, output_file)

        # if an output db file is specified it will write returned results.
        if (results_db is not None):
            print_status("Saving records to SQLite3 file: {0}".format(results_db))
            create_db(results_db)
            write_db(results_db, returned_records)

        # if an output csv file is specified it will write returned results.
        if (csv_file is not None):
            print_status("Saving records to CSV file: {0}".format(csv_file))
            write_to_file(make_csv(returned_records), csv_file)

        # if an output json file is specified it will write returned results.
        if (json_file is not None):
            print_status("Saving records to JSON file: {0}".format(json_file))
            write_json(json_file, returned_records, scan_info)

        sys.exit(0)

    elif domain is not None:
        try:
            print_status("Performing General Enumeration of Domain: {0}".format(domain))
            std_enum_records = std_enum_records = general_enum(res, domain, xfr, goo,
                                                               spf_enum, do_whois, zonewalk)

            returned_records.extend(std_enum_records)

            # if an output xml file is specified it will write returned results.
            if (output_file is not None):
                print_status("Saving records to XML file: {0}".format(output_file, scan_info))
                xml_enum_doc = dns_record_from_dict(returned_records, scan_info, domain)
                write_to_file(xml_enum_doc, output_file)

            # if an output db file is specified it will write returned results.
            if (results_db is not None):
                print_status("Saving records to SQLite3 file: {0}".format(results_db))
                create_db(results_db)
                write_db(results_db, returned_records)

            # if an output csv file is specified it will write returned results.
            if (csv_file is not None):
                print_status("Saving records to CSV file: {0}".format(csv_file))
                write_to_file(make_csv(returned_records), csv_file)

                # if an output json file is specified it will write returned results.
            if (json_file is not None):
                print_status("Saving records to JSON file: {0}".format(json_file))
                write_json(json_file, returned_records, scan_info)

            sys.exit(0)
        except dns.resolver.NXDOMAIN:
            print_error("Could not resolve domain: {0}".format(domain))
            sys.exit(1)

        except dns.exception.Timeout:
            print_error("A timeout error occurred please make sure you can reach the target DNS Servers")
            print_error("directly and requests are not being filtered. Increase the timeout")
            print_error("to a higher number with --lifetime <time> option.")
            sys.exit(1)
    else:
        usage()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = dnshelper
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    Copyright (C) 2013  Carlos Perez
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; Applies version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


import re
import dns.query
import dns.resolver
import dns.reversename
import socket
from dns.zone import *
from dns.dnssec import algorithm_to_text
from .msf_print import *


DNS_PORT_NUMBER = 53
DNS_QUERY_TIMEOUT = 4.0


class DnsHelper:
    def __init__(self, domain, ns_server=None, request_timeout=3.0, ):
        self._domain = domain
        if ns_server:
            self._res = dns.resolver.Resolver(configure=False)
            self._res.nameservers = [ns_server]
        else:
            self._res = dns.resolver.Resolver(configure=True)
        # Set timing
        self._res.timeout = request_timeout
        self._res.lifetime = request_timeout

    def check_tcp_dns(self, address):
        """
        Function to check if a server is listening at port 53 TCP. This will aid
        in IDS/IPS detection since a AXFR will not be tried if port 53 is found to
        be closed.
        """
        s = socket.socket()

        s.settimeout(DNS_QUERY_TIMEOUT)
        try:
            s.connect((address, DNS_PORT_NUMBER))
        except Exception:
            return False
        else:
            return True

    def resolve(self, target, type, ns=None):
        """
        Function for performing general resolution types returning the RDATA
        """
        if ns:
            res = dns.resolver.Resolver(configure=False)
            res.nameservers = [ns]
        else:
            res = dns.resolver.Resolver(configure=True)

        answers = res.query(target, type)
        return answers

    def get_a(self, host_trg):
        """
        Function for resolving the A Record for a given host. Returns an Array of
        the IP Address it resolves to. It will also return CNAME data.
        """
        address = []
        try:
            ipv4_answers = self._res.query(host_trg, 'A')
            for ardata in ipv4_answers.response.answer:
                for rdata in ardata:
                    if rdata.rdtype == 5:
                        address.append(["CNAME", host_trg, rdata.target.to_text()[:-1]])
                        host_trg = rdata.target.to_text()[:-1]
                    else:
                        address.append(["A", host_trg, rdata.address])
        except:
            return address
        return address

    def get_aaaa(self, host_trg):
        """
        Function for resolving the AAAA Record for a given host. Returns an Array of
        the IP Address it resolves to. It will also return CNAME data.
        """
        address = []
        try:
            ipv6_answers = self._res.query(host_trg, 'AAAA')
            for ardata in ipv6_answers.response.answer:
                for rdata in ardata:
                    if rdata.rdtype == 5:
                        address.append(["CNAME", host_trg, rdata.target.to_text()[:-1]])
                        host_trg = rdata.target.to_text()[:-1]
                    else:
                        address.append(["AAAA", host_trg, rdata.address])
        except:
            return address
        return address

    def get_ip(self, hostname):
        """
        Function resolves a host name to its given A and/or AAA record. Returns Array
        of found hosts and IPv4 or IPv6 Address.
        """
        found_ip_add = []
        found_ip_add.extend(self.get_a(hostname))
        found_ip_add.extend(self.get_aaaa(hostname))

        return found_ip_add

    def get_mx(self):
        """
        Function for MX Record resolving. Returns all MX records. Returns also the IP
        address of the host both in IPv4 and IPv6. Returns an Array
        """
        mx_records = []
        answers = self._res.query(self._domain, 'MX')
        for rdata in answers:
            try:
                name = rdata.exchange.to_text()
                ipv4_answers = self._res.query(name, 'A')
                for ardata in ipv4_answers:
                    mx_records.append(['MX', name[:-1], ardata.address,
                                      rdata.preference])
            except:
                pass
        try:
            for rdata in answers:
                name = rdata.exchange.to_text()
                ipv6_answers = self._res.query(name, 'AAAA')
                for ardata in ipv6_answers:
                    mx_records.append(['MX', name[:-1], ardata.address,
                                      rdata.preference])
            return mx_records
        except:
            return mx_records

    def get_ns(self):
        """
        Function for NS Record resolving. Returns all NS records. Returns also the IP
        address of the host both in IPv4 and IPv6. Returns an Array.
        """
        name_servers = []
        answer = self._res.query(self._domain, 'NS')
        if answer is not None:
            for aa in answer:
                name = aa.target.to_text()[:-1]
                ip_addrs = self.get_ip(name)
                for addresses in ip_addrs:
                    if re.search(r'^A', addresses[0]):
                        name_servers.append(['NS', name, addresses[2]])
        return name_servers

    def get_soa(self):
        """
        Function for SOA Record resolving. Returns all SOA records. Returns also the IP
        address of the host both in IPv4 and IPv6. Returns an Array.
        """
        soa_records = []
        answers = self._res.query(self._domain, 'SOA')
        for rdata in answers:
            name = rdata.mname.to_text()
            ipv4_answers = self._res.query(name, 'A')
            for ardata in ipv4_answers:
                soa_records.append(['SOA', name[:-1], ardata.address])

        try:
            for rdata in answers:
                name = rdata.mname.to_text()
                ipv4_answers = self._res.query(name, 'AAAA')
                for ardata in ipv4_answers:
                    soa_records.append(['SOA', name[:-1], ardata.address])

            return soa_records
        except:
            return soa_records

    def get_spf(self):
        """
        Function for SPF Record resolving returns the string with the SPF definition.
        Prints the string for the SPF Record and Returns the string
        """
        spf_record = []

        try:
            answers = self._res.query(self._domain, 'SPF')
            for rdata in answers:
                name = ''.join(rdata.strings)
                spf_record.append(['SPF', name])
        except:
            return None

        return spf_record

    def get_txt(self, target=None):
        """
        Function for TXT Record resolving returns the string.
        """
        txt_record = []
        if target is None:
            target = self._domain
        try:
            answers = self._res.query(target, 'TXT')
            for rdata in answers:
                string = "".join(rdata.strings)
                txt_record.append(['TXT', target, string])
        except:
            return []

        return txt_record

    def get_ptr(self, ipaddress):
        """
        Function for resolving PTR Record given it's IPv4 or IPv6 Address.
        """
        found_ptr = []
        n = dns.reversename.from_address(ipaddress)
        try:
            answers = self._res.query(n, 'PTR')
            for a in answers:
                found_ptr.append(['PTR', a.target.to_text()[:-1], ipaddress])
            return found_ptr
        except:
            return None

    def get_srv(self, host):
        """
        Function for resolving SRV Records.
        """
        record = []
        try:
            answers = self._res.query(host, 'SRV')
            for a in answers:
                target = a.target.to_text()
                #print a.target.to_text()
                ips = self.get_ip(target[:-1])
                if ips:
                    for ip in ips:
                        if re.search('(^A|AAAA)', ip[0]):
                            record.append(['SRV', host, a.target.to_text()[:-1], ip[2],
                                          str(a.port), str(a.weight)])

                else:
                    record.append(['SRV', host, a.target.to_text()[:-1], "no_ip",
                                  str(a.port), str(a.weight)])
        except:
            return record
        return record

    def get_nsec(self, host):
        """
        Function for querying for a NSEC record and retriving the rdata object.
        This function is used mostly for performing a Zone Walk against a zone.
        """
        answer = self._res.query(host, 'NSEC')
        return answer

    def from_wire(self, xfr, zone_factory=Zone, relativize=True):
        """
        Method for turning returned data from a DNS AXFR in to RRSET, this method will not perform a
        check origin on the zone data as the method included with dnspython
        """
        z = None
        for r in xfr:
            if z is None:
                if relativize:
                    origin = r.origin
                else:
                    origin = r.answer[0].name
                rdclass = r.answer[0].rdclass
                z = zone_factory(origin, rdclass, relativize=relativize)
            for rrset in r.answer:
                znode = z.nodes.get(rrset.name)
                if not znode:
                    znode = z.node_factory()
                    z.nodes[rrset.name] = znode
                zrds = znode.find_rdataset(rrset.rdclass, rrset.rdtype,
                                           rrset.covers, True)
                zrds.update_ttl(rrset.ttl)
                for rd in rrset:
                    rd.choose_relativity(z.origin, relativize)
                    zrds.add(rd)

        return z

    def zone_transfer(self):
        """
        Function for testing for zone transfers for a given Domain, it will parse the
        output by record type.
        """
        # if anyone reports a record not parsed I will add it, the list is a long one
        # I tried to include those I thought where the most common.

        zone_records = []
        ns_records = []
        print_status('Checking for Zone Transfer for {0} name servers'.format(self._domain))

        # Find SOA for Domain
        print_status("Resolving SOA Record")
        try:
            soa_srvs = self.get_soa()
            for s in soa_srvs:
                print_good("\t {0}".format(" ".join(s)))
                ns_records.append(s[2])
        except:
            print_error("Could not obtain the domains SOA Record.")
            return

        # Find NS for Domain
        print_status("Resolving NS Records")
        ns_srvs = []
        try:
            ns_srvs = self.get_ns()
            print_status("NS Servers found:")
            for ns in ns_srvs:
                print_status("\t{0}".format(" ".join(ns)))
                ns_ip = ''.join(ns[2])
                ns_records.append(ns_ip)
        except Exception as s:
            print_error("Could not Resolve NS Records")

        # Remove duplicates
        print_status("Removing any duplicate NS server IP Addresses...")
        ns_records = list(set(ns_records))
        # Test each NS Server
        for ns_srv in ns_records:
            print_status(" ")
            print_status('Trying NS server {0}'.format(ns_srv))
            if self.check_tcp_dns(ns_srv):

                print_good('{0} Has port 53 TCP Open'.format(ns_srv))
                try:
                    zone = self.from_wire(dns.query.xfr(ns_srv, self._domain))
                    print_good('Zone Transfer was successful!!')
                    zone_records.append({'type': 'info', 'zone_transfer': 'success', 'ns_server': ns_srv})
                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.SOA):
                        for rdata in rdataset:
                            for mn_ip in self.get_ip(rdata.mname.to_text()):
                                if re.search(r'^A', mn_ip[0]):
                                    print_status('\t SOA {0} {1}'.format(rdata.mname.to_text()[:-1], mn_ip[2]))
                                    zone_records.append({'zone_server': ns_srv, 'type': 'SOA',
                                                         'mname': rdata.mname.to_text()[:-1], 'address': mn_ip[2]})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.NS):
                        for rdata in rdataset:
                            for n_ip in self.get_ip(rdata.target.to_text()):
                                if re.search(r'^A', n_ip[0]):
                                    print_status('\t NS {0} {1}'.format(rdata.target.to_text()[:-1], n_ip[2]))
                                    zone_records.append({'zone_server': ns_srv, 'type': 'NS',
                                                        'target': rdata.target.to_text()[:-1], 'address': n_ip[2]})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.TXT):
                        for rdata in rdataset:
                            print_status('\t TXT {0}'.format(''.join(rdata.strings)))
                            zone_records.append({'zone_server': ns_srv, 'type': 'TXT',
                                                'strings': ''.join(rdata.strings)})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.SPF):
                        for rdata in rdataset:
                            print_status('\t SPF {0}'.format(''.join(rdata.strings)))
                            zone_records.append({'zone_server': ns_srv, 'type': 'SPF',
                                                 'strings': ''.join(rdata.strings)})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.PTR):
                        for rdata in rdataset:
                            for n_ip in self.get_ip(rdata.target.to_text() + "." + self._domain):
                                if re.search(r'^A', n_ip[0]):
                                    print_status('\t PTR {0} {1}'.format(rdata.target.to_text() + "." + self._domain, n_ip[2]))
                                    zone_records.append({'zone_server': ns_srv, 'type': 'PTR',
                                                         'name': rdata.target.to_text() + "." + self._domain, 'address': n_ip[2]})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.MX):
                        for rdata in rdataset:
                            for e_ip in self.get_ip(rdata.exchange.to_text()):
                                if re.search(r'^A', e_ip[0]):
                                    print_status('\t MX {0} {1} {2}'.format(str(name) + '.' + self._domain,
                                                 rdata.exchange.to_text()[:-1], e_ip[2]))
                                zone_records.append({'zone_server': ns_srv, 'type': 'MX',
                                                     'name': str(name) + '.' + self._domain,
                                                     'exchange': rdata.exchange.to_text()[:-1],
                                                     'address': e_ip[2]})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.AAAA):
                        for rdata in rdataset:
                            print_status('\t AAAA {0} {1}'.format(str(name) + '.' + self._domain,
                                         rdata.address))
                            zone_records.append({'zone_server': ns_srv, 'type': 'AAAA',
                                                'name': str(name) + '.' + self._domain,
                                                'address': rdata.address})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.A):
                        for rdata in rdataset:
                            print_status('\t A {0} {1}'.format(str(name) + '.' + self._domain,
                                         rdata.address))
                            zone_records.append({'zone_server': ns_srv, 'type': 'A',
                                                'name': str(name) + '.' + self._domain,
                                                'address': rdata.address})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.CNAME):
                        for rdata in rdataset:
                            for t_ip in self.get_ip(rdata.target.to_text()):
                                if re.search(r'^A', t_ip[0]):
                                    print_status('\t CNAME {0} {1} {2}'.format(str(name) + '.'
                                                 + self._domain, rdata.target.to_text(), t_ip[2]))
                                    zone_records.append({'zone_server': ns_srv, 'type': 'CNAME',
                                                         'name': str(name) + '.' + self._domain,
                                                         'target': str(rdata.target.to_text())[:-1],
                                                         'address': t_ip[2]})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.SRV):
                        for rdata in rdataset:
                            ip_list = self.get_ip(rdata.target.to_text())
                            if ip_list:
                                for t_ip in self.get_ip(rdata.target.to_text()):
                                    if re.search(r'^A', t_ip[0]):
                                        print_status('\t SRV {0} {1} {2} {3} {4}'.format(str(name) + '.' + self._domain, rdata.target,
                                                     str(rdata.port), str(rdata.weight), t_ip[2]))
                                        zone_records.append({'zone_server': ns_srv, 'type': 'SRV',
                                                            'name': str(name) + '.' + self._domain,
                                                            'target': rdata.target.to_text()[:-1],
                                                            'address': t_ip[2],
                                                            'port': str(rdata.port),
                                                            'weight': str(rdata.weight)})
                            else:
                                print_status('\t SRV {0} {1} {2} {3} {4}'.format(str(name) + '.' + self._domain, rdata.target,
                                             str(rdata.port), str(rdata.weight), 'no_ip'))
                                zone_records.append({'zone_server': ns_srv, 'type': 'SRV',
                                                    'name': str(name) + '.' + self._domain,
                                                    'target': rdata.target.to_text()[:-1],
                                                    'address': "no_ip",
                                                    'port': str(rdata.port),
                                                    'weight': str(rdata.weight)})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.HINFO):
                        for rdata in rdataset:
                            print_status('\t HINFO {0} {1}'.format(rdata.cpu, rdata.os))
                            zone_records.append({'zone_server': ns_srv, 'type': 'HINFO',
                                                'cpu': rdata.cpu, 'os': rdata.os})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.WKS):
                        for rdata in rdataset:
                            print_status('\t WKS {0} {1} {2}'.format(rdata.address, rdata.bitmap, rdata.protocol))
                            zone_records.append({'zone_server': ns_srv, 'type': 'WKS',
                                                'address': rdata.address, 'bitmap': rdata.bitmap,
                                                'protocol': rdata.protocol})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.RP):
                        for rdata in rdataset:
                            print_status('\t RP {0} {1}'.format(rdata.mbox, rdata.txt))
                            zone_records.append({'zone_server': ns_srv, 'type': 'RP',
                                                'mbox': rdata.mbox.to_text(), 'txt': rdata.txt.to_text()})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.AFSDB):
                        for rdata in rdataset:
                            print_status('\t AFSDB {0} {1}'.format(str(rdata.subtype), rdata.hostname))
                            zone_records.append({'zone_server': ns_srv, 'type': 'AFSDB',
                                                'subtype': str(rdata.subtype), 'hostname': rdata.hostname.to_text()})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.LOC):
                        for rdata in rdataset:
                            print_status('\t LOC {0}'.format(rdata.to_text()))
                            zone_records.append({'zone_server': ns_srv, 'type': 'LOC',
                                                'coordinates': rdata.to_text()})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.X25):
                        for rdata in rdataset:
                            print_status('\tX25 {0}'.format(rdata.address))
                            zone_records.append({'zone_server': ns_srv, 'type': 'X25',
                                                'address': rdata.address})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.ISDN):
                        for rdata in rdataset:
                            print_status('\t ISDN {0}'.format(rdata.address))
                            zone_records.append({'zone_server': ns_srv, 'type': 'ISDN',
                                                 'address': rdata.address})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.RT):
                        for rdata in rdataset:
                            print_status('\t RT {0} {1}'.format(str(rdata.exchange), rdata.preference))
                            zone_records.append({'zone_server': ns_srv, 'type': 'X25',
                                                 'address': rdata.address})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.NSAP):
                        for rdata in rdataset:
                            print_status('\t NSAP {0}'.format(rdata.address))
                            zone_records.append({'zone_server': ns_srv, 'type': 'NSAP',
                                                 'address': rdata.address})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.NAPTR):
                        for rdata in rdataset:
                            print_status('\t NAPTR {0} {1} {2} {3} {4} {5}'.format(rdata.flags,
                                                                                   rdata.order,
                                                                                   rdata.preference,
                                                                                   rdata.regexp,
                                                                                   rdata.replacement,
                                                                                   rdata.service))
                            zone_records.append({'zone_server': ns_srv, 'type': 'NAPTR',
                                                 'order': str(rdata.order),
                                                 'preference': str(rdata.preference),
                                                 'regex': rdata.regexp,
                                                 'replacement': rdata.replacement.to_text(),
                                                 'service': rdata.service})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.CERT):
                        for rdata in rdataset:
                            print_status('\t CERT {0}'.format(rdata.to_text()))
                            zone_records.append({'zone_server': ns_srv, 'type': 'CERT',
                                                 'algorithm': rdata.algorithm,
                                                 'certificate': rdata.certificate,
                                                 'certificate_type': rdata.certificate_type,
                                                 'key_tag': rdata.key_tag})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.SIG):
                        for rdata in rdataset:
                            print_status('\t SIG {0} {1} {2} {3} {4} {5} {6} {7} {8}'.format(
                                algorithm_to_text(rdata.algorithm), rdata.expiration,
                                rdata.inception, rdata.key_tag, rdata.labels, rdata.original_ttl,
                                rdata.signature, str(rdata.signer), rdata.type_covered))
                            zone_records.append({'zone_server': ns_srv, 'type': 'SIG',
                                                'algorithm': algorithm_to_text(rdata.algorithm),
                                                'expiration': rdata.expiration,
                                                'inception': rdata.inception,
                                                'key_tag': rdata.key_tag,
                                                'labels': rdata.labels,
                                                'original_ttl': rdata.original_ttl,
                                                'signature': rdata.signature,
                                                'signer': str(rdata.signer),
                                                'type_covered': rdata.type_covered})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.RRSIG):
                        for rdata in rdataset:
                            print_status('\t RRSIG {0} {1} {2} {3} {4} {5} {6} {7} {8}'.format(
                                algorithm_to_text(rdata.algorithm), rdata.expiration,
                                rdata.inception, rdata.key_tag, rdata.labels, rdata.original_ttl,
                                rdata.signature, str(rdata.signer), rdata.type_covered))
                            zone_records.append({'zone_server': ns_srv, 'type': 'RRSIG',
                                                 'algorithm': algorithm_to_text(rdata.algorithm),
                                                 'expiration': rdata.expiration,
                                                 'inception': rdata.inception,
                                                 'key_tag': rdata.key_tag,
                                                 'labels': rdata.labels,
                                                 'original_ttl': rdata.original_ttl,
                                                 'signature': rdata.signature,
                                                 'signer': str(rdata.signer),
                                                 'type_covered': rdata.type_covered})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.DNSKEY):
                        for rdata in rdataset:
                            print_status('\t DNSKEY {0} {1} {2} {3}'.format(
                                algorithm_to_text(rdata.algorithm), rdata.flags, dns.rdata._hexify(rdata.key),
                                rdata.protocol))
                            zone_records.append({'zone_server': ns_srv, 'type': 'DNSKEY',
                                                 'algorithm': algorithm_to_text(rdata.algorithm),
                                                 'flags': rdata.flags,
                                                 'key': dns.rdata._hexify(rdata.key),
                                                 'protocol': rdata.protocol})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.DS):
                        for rdata in rdataset:
                            print_status('\t DS {0} {1} {2} {3}'.format(algorithm_to_text(rdata.algorithm), dns.rdata._hexify(rdata.digest),
                                         rdata.digest_type, rdata.key_tag))
                            zone_records.append({'zone_server': ns_srv, 'type': 'DS',
                                                'algorithm': algorithm_to_text(rdata.algorithm),
                                                'digest': dns.rdata._hexify(rdata.digest),
                                                'digest_type': rdata.digest_type,
                                                'key_tag': rdata.key_tag})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.NSEC):
                        for rdata in rdataset:
                            print_status('\t NSEC {0}'.format(rdata.next))
                            zone_records.append({'zone_server': ns_srv, 'type': 'NSEC',
                                                 'next': rdata.next})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.NSEC3):
                        for rdata in rdataset:
                            print_status('\t NSEC3 {0} {1} {2} {3}'.format(algorithm_to_text(rdata.algorithm), rdata.flags,
                                         rdata.iterations, rdata.salt))
                            zone_records.append({'zone_server': ns_srv, 'type': 'NSEC3',
                                                 'algorithm': algorithm_to_text(rdata.algorithm),
                                                 'flags': rdata.flags,
                                                 'iterations': rdata.iterations,
                                                 'salt': dns.rdata._hexify(rdata.salt)})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.NSEC3PARAM):
                        for rdata in rdataset:
                            print_status('\t NSEC3PARAM {0} {1} {2} {3}'.format(algorithm_to_text(rdata.algorithm), rdata.flags,
                                         rdata.iterations, rdata.salt))
                            zone_records.append({'zone_server': ns_srv, 'type': 'NSEC3PARAM',
                                                 'algorithm': algorithm_to_text(rdata.algorithm),
                                                 'flags': rdata.flags,
                                                 'iterations': rdata.iterations,
                                                 'salt': rdata.salt})

                    for (name, rdataset) in zone.iterate_rdatasets(dns.rdatatype.IPSECKEY):
                        for rdata in rdataset:
                            print_status('\t PSECKEY {0} {1} {2} {3} {4}'.format(algorithm_to_text(rdata.algorithm), rdata.gateway,
                                         rdata.gateway_type, dns.rdata._hexify(rdata.key), rdata.precedence))
                            zone_records.append({'zone_server': ns_srv, 'type': 'IPSECKEY',
                                                 'algorithm': algorithm_to_text(rdata.algorithm),
                                                 'gateway': rdata.gateway,
                                                 'gateway_type': rdata.gateway_type,
                                                 'key': dns.rdata._hexify(rdata.key),
                                                 'precedence': rdata.precedence})
                except Exception as e:
                    print_error('Zone Transfer Failed!')
                    print_error(e)
                    zone_records.append({'type': 'info', 'zone_transfer': 'failed', 'ns_server': ns_srv})
            else:
                print_error('Zone Transfer Failed for {0}!'.format(ns_srv))
                print_error('Port 53 TCP is being filtered')
                zone_records.append({'type': 'info', 'zone_transfer': 'failed', 'ns_server': ns_srv})
        return zone_records


def main():
    resolver = DnsHelper('google.com')
    print(resolver.get_a("www.yahoo.com"))
    print(resolver.get_aaaa('baddata-cname-to-baddata-aaaa.test.dnssec-tools.org'))
    print(resolver.get_mx())
    print(resolver.get_ip('www.google.com'))
    print(resolver.get_txt("3rdparty1._spf.paypal.com"))
    print(resolver.get_ns())
    print(resolver.get_soa())
    print(resolver.get_txt())
    print(resolver.get_spf())
    #tresolver = DnsHelper('weightmans.com')
    tresolver = DnsHelper('google.com')
    print(tresolver.zone_transfer())
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = gooenum
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    Copyright (C) 2010  Carlos Perez
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; Applies version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


import urllib
import re
import time

try:
    url_opener = urllib.FancyURLopener
except AttributeError:
    import urllib.request
    url_opener = urllib.request.FancyURLopener


class AppURLopener(url_opener):

    version = 'Mozilla/5.0 (compatible; Googlebot/2.1; + http://www.google.com/bot.html)'


def scrape_google(dom):
    """
    Function for enumerating sub-domains and hosts by scrapping Google. It returns a unique
    list if host name extracted from the HREF entries from the Google search.
    """
    results = []
    filtered = []
    searches = ["100", "200", "300", "400", "500"]
    data = ""
    urllib._urlopener = AppURLopener()
    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
    headers = {'User-Agent': user_agent, }
    #opener.addheaders = [('User-Agent','Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)')]
    for n in searches:
        url = "http://google.com/search?hl=en&lr=&ie=UTF-8&q=%2B" + dom + "&start=" + n + "&sa=N&filter=0&num=100"
        try:
            sock = urllib.urlopen(url)
            data += sock.read()
            sock.close()
        except AttributeError:
            request = urllib.request.Request(url, None, headers)
            response = urllib.request.urlopen(request)
            data += str(response.read())
    results.extend(unique(re.findall("href=\"htt\w{1,2}:\/\/([^:?]*[a-b0-9]*[^:?]*\." + dom + ")\/", data)))
    # Make sure we are only getting the host
    for f in results:
        filtered.extend(re.findall("^([a-z.0-9^]*" + dom + ")", f))
    time.sleep(2)
    return unique(filtered)


def unique(seq, idfun=repr):
    """
    Function to remove duplicates in an array. Returns array with duplicates
    removed.
    """
    seen = {}
    return [seen.setdefault(idfun(e), e) for e in seq if idfun(e) not in seen]

########NEW FILE########
__FILENAME__ = mdnsenum
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    Copyright (C) 2010  Carlos Perez
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; Applies version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import pybonjour
import select
import re

def mdns_browse(regtype):
    """
    Function for resolving a specific mDNS record in the Local Subnet.
    """
    found_mdns_records = []
    domain = None
    browse_timeout = 1
    resolve_timeout = 1
    results = []
    resolved = []

    def resolve_callback(
        sdRef,
        flags,
        interfaceIndex,
        errorCode,
        fullname,
        hosttarget,
        port,
        txtRecord,
        ):

        n = re.compile(u'(\x00|\x07|\x1A|\x16|\x06|\x08|\x1f|\xdb|\xb2|\xb0|\xb1'
                   u'\xc9|\xb9|\xcd|\u2019|\u2018|\u2019|\u201c|\u201d|\u2407)')

        t = re.compile(r'[\x00-\x1f|\x7f|\x0e]')

        if errorCode == pybonjour.kDNSServiceErr_NoError:
            results.append({
                'type': 'MDNS',
                'name': n.sub(" ",fullname),
                'host': str(hosttarget).replace('\032'," "),
                'port': str(port),
                'txtRecord': t.sub(" ",txtRecord.strip())
                })
            resolved.append(True)

    def browse_callback(
        sdRef,
        flags,
        interfaceIndex,
        errorCode,
        serviceName,
        regtype,
        replyDomain,
        ):
        if errorCode != pybonjour.kDNSServiceErr_NoError:
            return

        if not flags & pybonjour.kDNSServiceFlagsAdd:

            # Service removed

            return

        resolve_sdRef = pybonjour.DNSServiceResolve(
            0,
            interfaceIndex,
            serviceName,
            regtype,
            replyDomain,
            resolve_callback,
            )

        try:
            while not resolved:
                ready = select.select([resolve_sdRef], [], [],
                        resolve_timeout)

                if resolve_sdRef not in ready[0]:

                    # Resolve timed out

                    break

                pybonjour.DNSServiceProcessResult(resolve_sdRef)
            else:

                resolved.pop()
        finally:

            resolve_sdRef.close()

    browse_sdRef = pybonjour.DNSServiceBrowse(regtype=regtype,
            domain=domain, callBack=browse_callback)

    try:
        while True:
            ready = select.select([browse_sdRef], [], [],
                                  browse_timeout)

            if not ready[0]:
                break

            if browse_sdRef in ready[0]:
                pybonjour.DNSServiceProcessResult(browse_sdRef)

            _results = results

            for result in _results:
                found_mdns_records = [result]
    finally:

        browse_sdRef.close()
    return found_mdns_records

########NEW FILE########
__FILENAME__ = msf_print
#!/usr/bin/env python
import sys
import platform

# -*- coding: utf-8 -*-

#    Copyright (C) 2012  Carlos Perez
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; Applies version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


def print_status(message=""):
    if sys.stdout.isatty() and platform.system() != "Windows":
        print("\033[1;34m[*]\033[1;m {0}".format(message))
    else:
        print("[*] {0}".format(message))


def print_good(message=""):
    if sys.stdout.isatty() and platform.system() != "Windows":
        print("\033[1;32m[*]\033[1;m {0}".format(message))
    else:
        print("[*] {0}".format(message))


def print_error(message=""):
    if sys.stdout.isatty() and platform.system() != "Windows":
        print("\033[1;31m[-]\033[1;m {0}".format(message))
    else:
        print("[-] {0}".format(message))


def print_debug(message=""):
    if sys.stdout.isatty() and platform.system() != "Windows":
        print("\033[1;31m[!]\033[1;m {0}".format(message))
    else:
        print("[!] {0}".format(message))


def print_line(message=""):
    print("{0}".format(message))

########NEW FILE########
__FILENAME__ = whois
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    Copyright (C) 2010  Carlos Perez
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; Applies version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import re
from netaddr import *
import socket

WHOIS_PORT_NUMBER = 43
WHOIS_RECEIVE_BUFFER_SIZE = 4096


def get_whois(ip_addrs):
    """
    Function that returns what whois server is the one to be queried for
    registration information, returns whois.arin.net is not in database, returns
    None if private.
    """
    whois_server = None
    ip = IPAddress(ip_addrs)
    info_of_ip = ip.info
    if ip.version == 4 and ip.is_private() is False:
        for i in info_of_ip['IPv4']:
            whois_server = i['whois']
            if len(whois_server) == 0 and i['status'] != "Reserved":
                whois_server = "whois.arin.net"
            elif len(whois_server) == 0:
                whois_server = None

    return whois_server


def whois(target, whois_srv):
    """
    Performs a whois query against a arin.net for a given IP, Domain or Host as a
    string and returns the answer of the query.
    """
    response = ""
    counter = 1
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((whois_srv, WHOIS_PORT_NUMBER))
        if whois_srv == "whois.arin.net":
            s.send(("n " + target + "\r\n").encode("utf-8"))
        else:
            s.send((target + "\r\n").encode("utf-8"))
        response = ''
        while True:
            d = s.recv(WHOIS_RECEIVE_BUFFER_SIZE)
            response += str(d)
            counter += 1
            if str(d) == '' or counter == 5:
                break
        s.close()
    except Exception as e:
        print(e)
        pass
    return response


def get_whois_nets(data):
    """
    Parses whois data and extracts the Network Ranges returning an array of lists
    where each list has the starting and ending IP of the found range.
    """

    patern = '([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}) - ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})'
    results = re.findall(patern, data)

    return results


def get_whois_orgname(data):
    org_pattern = "OrgName\:\s*(.*)\n"
    result = re.findall(org_pattern, data)
    # Lets try RIPENET Format
    if not result :
        org_pattern = "netname\:\s*(.*)\n"
        result = re.findall(org_pattern, data)
    if not result:
        result.append("Not Found")
    return result

########NEW FILE########
__FILENAME__ = parser
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    DNSRecon Data Parser
#
#    Copyright (C) 2012  Carlos Perez
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; Applies version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

__version__ = '0.0.6'
__author__ = 'Carlos Perez, Carlos_Perez@darkoperator.com'

import xml.etree.cElementTree as cElementTree
import csv
import os
import getopt
import sys
import re

from netaddr import *

# Function Definitions
# ------------------------------------------------------------------------------


def print_status(message=""):
    print("\033[1;34m[*]\033[1;m {0}".format(message))


def print_good(message=""):
    print("\033[1;32m[*]\033[1;m {0}".format(message))


def print_error(message=""):
    print("\033[1;31m[-]\033[1;m {0}".format(message))


def print_debug(message=""):
    print("\033[1;31m[!]\033[1;m {0}".format(message))


def print_line(message=""):
    print("{0}".format(message))


def process_range(arg):
    """
    Function will take a string representation of a range for IPv4 or IPv6 in
    CIDR or Range format and return a list of IPs.
    """
    try:
        ip_list = None
        range_vals = []
        if re.match(r'\S*\/\S*', arg):
            ip_list = IPNetwork(arg)

        range_vals.extend(arg.split("-"))
        if len(range_vals) == 2:
            ip_list = IPNetwork(IPRange(range_vals[0], range_vals[1])).cidrs()[-1]
    except:
        print_error("Range provided is not valid: {0}".format(arg()))
        return []
    return ip_list


def xml_parse(xm_file, ifilter, tfilter, nfilter, list):
    """
    Function for parsing XML files created by DNSRecon and apply filters.
    """
    iplist = []
    for event, elem in cElementTree.iterparse(xm_file):
        # Check if it is a record
        if elem.tag == "record":
            # Check that it is a RR Type that has an IP Address
            if "address" in elem.attrib:
                # Check if the IP is in the filter list of IPs to ignore
                if (len(ifilter) == 0 or IPAddress(elem.attrib['address']) in ifilter) and (elem.attrib['address'] != "no_ip"):
                    # Check if the RR Type against the types
                    if re.match(tfilter, elem.attrib['type'], re.I):
                        # Process A, AAAA and PTR Records
                        if re.search(r'PTR|^[A]$|AAAA', elem.attrib['type']) \
                        and re.search(nfilter, elem.attrib['name'], re.I):
                            if list:
                                if elem.attrib['address'] not in iplist:
                                    print elem.attrib['address']
                            else:
                                print_good("{0} {1} {2}".format(elem.attrib['type'], elem.attrib['name'], elem.attrib['address']))

                        # Process NS Records
                        elif re.search(r'NS', elem.attrib['type']) and \
                        re.search(nfilter, elem.attrib['target'], re.I):
                            if list:
                                if elem.attrib['address'] not in iplist:
                                    iplist.append(elem.attrib['address'])
                            else:
                                print_good("{0} {1} {2}".format(elem.attrib['type'], elem.attrib['target'], elem.attrib['address']))

                        # Process SOA Records
                        elif re.search(r'SOA', elem.attrib['type']) and \
                        re.search(nfilter, elem.attrib['mname'], re.I):
                            if list:
                                if elem.attrib['address'] not in iplist:
                                    iplist.append(elem.attrib['address'])
                            else:
                                print_good("{0} {1} {2}".format(elem.attrib['type'], elem.attrib['mname'], elem.attrib['address']))

                        # Process MS Records
                        elif re.search(r'MX', elem.attrib['type']) and \
                        re.search(nfilter, elem.attrib['exchange'], re.I):
                            if list:
                                if elem.attrib['address'] not in iplist:
                                    iplist.append(elem.attrib['address'])
                            else:
                                print_good("{0} {1} {2}".format(elem.attrib['type'], elem.attrib['exchange'], elem.attrib['address']))

                        # Process SRV Records
                        elif re.search(r'SRV', elem.attrib['type']) and \
                        re.search(nfilter, elem.attrib['target'], re.I):
                            if list:
                                if elem.attrib['address'] not in iplist:
                                    iplist.append(elem.attrib['address'])
                            else:
                                print_good("{0} {1} {2} {3}".format(elem.attrib['type'], elem.attrib['name'], elem.attrib['address'], elem.attrib['target'], elem.attrib['port']))
            else:
                if re.match(tfilter, elem.attrib['type'], re.I):
                    # Process TXT and SPF Records
                    if re.search(r'TXT|SPF', elem.attrib['type']):
                        if not list:
                            print_good("{0} {1}".format(elem.attrib['type'], elem.attrib['strings']))
    # Process IPs in list
    if len(iplist) > 0:
        try:
            for ip in filter(None, iplist):
                print_line(ip)
        except IOError:
            sys.exit(0)


def csv_parse(csv_file, ifilter, tfilter, nfilter, list):
    """
    Function for parsing CSV files created by DNSRecon and apply filters.
    """
    iplist = []
    reader = csv.reader(open(csv_file, 'r'), delimiter=',')
    reader.next()
    for row in reader:
        # Check if IP is in the filter list of addresses to ignore
        if ((len(ifilter) == 0) or (IPAddress(row[2]) in ifilter)) and (row[2] != "no_ip"):
            # Check Host Name regex and type list
            if re.search(tfilter, row[0], re.I) and re.search(nfilter, row[1], re.I):
                if list:
                    if row[2] not in iplist:
                        print(row[2])
                else:
                    print_good(" ".join(row))
    # Process IPs for target list if available
    #if len(iplist) > 0:
    #    for ip in filter(None, iplist):
    #        print_line(ip)


def extract_hostnames(file):
    host_names = []
    hostname_pattern = re.compile("(^[^.]*)")
    file_type = detect_type(file)
    if file_type == "xml":
        for event, elem in cElementTree.iterparse(file):
            # Check if it is a record
            if elem.tag == "record":
                # Check that it is a RR Type that has an IP Address
                if "address" in elem.attrib:
                    # Process A, AAAA and PTR Records
                    if re.search(r'PTR|^[A]$|AAAA', elem.attrib['type']):
                        host_names.append(re.search(hostname_pattern, elem.attrib['name']).group(1))

                    # Process NS Records
                    elif re.search(r'NS', elem.attrib['type']):
                        host_names.append(re.search(hostname_pattern, elem.attrib['target']).group(1))

                    # Process SOA Records
                    elif re.search(r'SOA', elem.attrib['type']):
                        host_names.append(re.search(hostname_pattern, elem.attrib['mname']).group(1))

                    # Process MX Records
                    elif re.search(r'MX', elem.attrib['type']):
                        host_names.append(re.search(hostname_pattern, elem.attrib['exchange']).group(1))

                    # Process SRV Records
                    elif re.search(r'SRV', elem.attrib['type']):
                        host_names.append(re.search(hostname_pattern, elem.attrib['target']).group(1))

    elif file_type == "csv":
        reader = csv.reader(open(file, 'r'), delimiter=',')
        reader.next()
        for row in reader:
            host_names.append(re.search(hostname_pattern, row[1]).group(1))

    host_names = list(set(host_names))
    # Return list with no empty values
    return filter(None, host_names)


def detect_type(file):
    """
    Function for detecting the file type by checking the first line of the file.
    Returns xml, csv or None.
    """
    ftype = None

    # Get the fist lile of the file for checking
    f = open(file, 'r')
    firs_line = f.readline()

    # Determine file type based on the fist line content
    import re
    if re.search("(xml version)", firs_line):
        ftype = "xml"
    elif re.search(r'\w*,[^,]*,[^,]*', firs_line):
        ftype = "csv"
    else:
        raise Exception("Unsupported File Type")
    return ftype


def usage():
    print("Version: {0}".format(__version__))
    print("DNSRecon output file parser")
    print("Usage: parser.py <options>\n")
    print("Options:")
    print("   -h, --help               Show this help message and exit")
    print("   -f, --file    <file>     DNSRecon XML or CSV output file to parse.")
    print("   -l, --list               Output an unique IP List that can be used with other tools.")
    print("   -i, --ips     <ranges>   IP Ranges in a comma separated list each in formats (first-last)")
    print("                            or in (range/bitmask) for ranges to be included from output.")
    print("                            For A, AAAA, NS, MX, SOA, SRV and PTR Records.")
    print("   -t, --type    <type>     Resource Record Types as a regular expression to filter output.")
    print("                            For A, AAAA, NS, MX, SOA, TXT, SPF, SRV and PTR Records.")
    print("   -s, --str     <regex>    Regular expression between quotes for filtering host names on.")
    print("                            For A, AAAA, NS, MX, SOA, SRV and PTR Records.")
    print("   -n, --name               Return list of unique host names.")
    print("                            For A, AAAA, NS, MX, SOA, SRV and PTR Records.")
    sys.exit(0)

# Main
#-------------------------------------------------------------------------------


def main():
    #
    # Option Variables
    #
    ip_filter = []
    name_filter = "(.*)"
    type_filter = "(.*)"
    target_list = False
    file = None
    names = False

    #
    # Define options
    #
    try:
        options, args = getopt.getopt(sys.argv[1:], 'hi:t:s:lf:n',
                                           ['help',
                                           'ips='
                                           'type=',
                                           'str=',
                                           'list',
                                           'file=',
                                           'name'
                                           ])

    except getopt.GetoptError as error:
        print_error("Wrong Option Provided!")
        print_error(error)
        return

    #
    # Parse options
    #
    for opt, arg in options:
        if opt in ('-t', '--type'):
            type_filter = arg

        elif opt in ('-i', '--ips'):
            ipranges = arg.split(",")
            for r in ipranges:
                ip_filter.extend(process_range(r))
            ip_set = IPSet(ip_filter)

        elif opt in ('-s', '--str'):
            name_filter = "({0})".format(arg)

        elif opt in ('-l', '--list'):
            target_list = True

        elif opt in ('-f', '--file'):

            #Check if the dictionary file exists
            if os.path.isfile(arg):
                file = arg
            else:
                print_error("File {0} does not exist!".format(arg))
                exit(1)

        elif opt in ('-r', '--range'):
            ip_range = process_range(arg)
            if len(ip_range) > 0:
                ip_list.extend(ip_range)
            else:
                sys.exit(1)
        elif opt in ('-n', '--name'):
            names = True

        elif opt in ('-h'):
            usage()

    # start execution based on options
    if file:
        if names:
            try:
                found_names = extract_hostnames(file)
                found_names.sort()
                for n in found_names:
                    print_line(n)
            except IOError:
                sys.exit(0)
        else:
            file_type = detect_type(file)
            if file_type == "xml":
                xml_parse(file, ip_set, type_filter, name_filter, target_list)
            elif file_type == "csv":
                csv_parse(file, ip_set, type_filter, name_filter, target_list)
    else:
        print_error("A DNSRecon XML or CSV output file must be provided to be parsed")
        usage()

if __name__ == "__main__":
    main()

########NEW FILE########
