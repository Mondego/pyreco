__FILENAME__ = config
sniffer_type = 'L2' # can be L3 or Tcpdump, but L2 is working more reliably
min_ttl = 3
max_ttl = 20
debug = True
batch_size = 4
output_dir = 'var'
interval_between_poke_and_peek = 2

fixed_route = None
# uncomment below if you have a broken routing table
# which caused the detected outgoing ip or interface is wrong
#fixed_route = ('venet0:0', 'a.b.c.d')

# tcp_route_probe must not be None
# it is used to test if route changes when sport/dport changed
tcp_route_probe = {
    'a_sport': 9264,
    'b_sport': 8375,
    'c_sport': 7486,
    'a_dport': 6597,
    'b_dport': 5618,
    'c_dport': 4729
}

# udp_route_probe must not be None
# it is used to test if route changes when sport/dport changed
udp_route_probe = {
    'a_sport': 9264,
    'b_sport': 8375,
    'c_sport': 7486,
    'a_dport': 6597,
    'b_dport': 5618,
    'c_dport': 4729
}

dns_wrong_answer_probe = {
    'sport': 19841,
    'dport': 53
}
# uncomment below to disable dns_wrong_answer_probe
# dns_wrong_answer_probe = None

http_tcp_rst_probe = {
    'sport': 19842,
    'dport': 80,
    'interval_between_syn_and_http_get': 0.5
}
# uncomment below to disable http_tcp_rst_probe
# http_tcp_rst_probe = None

dns_tcp_rst_probe = {
    'sport': 19843,
    'dport': 53,
    'interval_between_syn_and_dns_question': 0.5
}
# uncomment below to disable dns_tcp_rst_probe
# dns_tcp_rst_probe = None

smtp_mail_from_tcp_rst_probe = {
    'sport': 19844,
    'dport': 25,
    'interval_between_syn_and_mail_from': 0.5
}
# uncomment below to disable smtp_mail_from_tcp_rst_probe
# smtp_mail_from_tcp_rst_probe = None

smtp_rcpt_to_tcp_rst_probe = {
    'sport': 19845,
    'dport': 25,
    'interval_between_syn_and_rcpt_to': 0.5
}
# uncomment below to disable smtp_rcpt_to_tcp_rst_probe
# smtp_rcpt_to_tcp_rst_probe = None

smtp_helo_rcpt_to_tcp_rst_probe = {
    'sport': 19846,
    'dport': 25,
    'interval_between_syn_and_helo': 0.5
}
# uncomment below to disable smtp_helo_rcpt_to_tcp_rst_probe
# smtp_helo_rcpt_to_tcp_rst_probe = None

tcp_packet_drop_probe = None
# uncomment below if you have tcp port being blocked by GFW
# if dport is blocked, set the sport to the same
# if sport is blocked, set the dport to the same
# example below demonstrated the case which sport 8080 is blocked
#tcp_packet_drop_probe = {
#    'blocked_sport': 8080,
#    'comparison_sport': 8081,
#    'blocked_dport': 1234,
#    'comparison_dport': 1234
#}

udp_packet_drop_probe = None
# uncomment below if you have udp port being blocked by GFW
# if dport is blocked, set the sport to the same
# if sport is blocked, set the dport to the same
# example below demonstrated the case which sport 8080 is blocked
#udp_packet_drop_probe = {
#    'blocked_sport': 8080,
#    'comparison_sport': 8081,
#    'blocked_dport': 53,
#    'comparison_dport': 53
#}

# config below works when you probe from China to abroad
ip_providers = [
    'by_country.py JP | limit.py 50'
]
# if you want to probe from abroad to China, uncomment settings below
# ip_providers = [
#     'by_carrier.py CHINANET | limit.py 50',
#     'by_carrier.py CNCGROUP | limit.py 50',
#     'by_carrier.py CN-CMCC | limit.py 50',
#     'by_carrier.py CN-CRTC | limit.py 50',
#     'by_carrier.py CERNET-AP | limit.py 50',
#     'by_carrier.py CN-CSTNET | limit.py 50'
# ]

# you can use a file at ~/.qiang.cfg to override settings in this config file
import os
import sys

QIANG_CFG_PATH = os.path.join(os.getenv('HOME'), '.qiang.cfg')
if os.path.exists(QIANG_CFG_PATH):
    with open(QIANG_CFG_PATH) as f:
        user_config_code = compile(f.read(), QIANG_CFG_PATH, 'exec')
    user_config = {}
    exec user_config_code in user_config
    sys.modules[__name__].__dict__.update(user_config)

if not os.path.exists(output_dir):
    os.mkdir(output_dir)
########NEW FILE########
__FILENAME__ = by_asn
#!/usr/bin/env python
import re
import urllib2
import math
import struct
import socket
import random
import sys

RE_IP_RANGE = re.compile(r'([0-9]+(?:\.[0-9]+){3})/([0-9]+)')

def main(as_number=None):
    if '@stdin' == as_number:
        while True:
            as_number = sys.stdin.readline().strip()
            if as_number:
                list_ip_for_asn(as_number)
            else:
                return
    else:
        list_ip_for_asn(as_number)


def list_ip_for_asn(as_number):
    urllib2.socket.setdefaulttimeout(10)
    request = urllib2.Request('http://bgp.he.net/AS%s' % as_number)
    request.add_header('User-Agent',
        'Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.8.1.14) Gecko/20080404 (FoxPlus) Firefox/2.0.0.14')
    response = urllib2.urlopen(request)
    for ip_range in RE_IP_RANGE.findall(response.read()):
        start_ip, netmask = ip_range
        netmask = int(netmask)
        if netmask == 0:
            continue
        print(get_random_ip_in_range(start_ip, netmask))


def get_random_ip_in_range(start_ip, netmask):
# http://dregsoft.com/blog/?p=24
    ip_count = int(math.pow(2, 32 - netmask))
    start_ip_bytes = struct.unpack('!i', socket.inet_aton(start_ip))[0]
    random_ip_bytes = random.randrange(start_ip_bytes, start_ip_bytes + ip_count)
    random_ip = socket.inet_ntoa(struct.pack('!i', random_ip_bytes))
    return random_ip

if 1 == len(sys.argv):
    print('[Usage] ./by_asn.py as_number > ip_list.txt')
    print('@stdin is a special as_number indicating as number should be read from stdin')
    sys.exit(3)
else:
    main(*sys.argv[1:])
########NEW FILE########
__FILENAME__ = by_carrier
#!/usr/bin/env python
import socket
import re
import struct
import random
import sys

# Generate random ip from ip range of specific network carrier
# It is useful because for same carrier, GFW tend to install device in a very narrow ip range
# There are at least 6 major network carriers in China which have GFW attached to its boarder gateway
# The filtering and jamming behavior differ from carrier to carrier,
# which makes this carrier based ip selection interesting

RE_INETNUM = re.compile(r'inetnum:\s+(.+?)\s+-\s+(.+)', re.IGNORECASE)
RE_AUTNUM = re.compile(r'aut\-num:\s+AS(\d+)', re.IGNORECASE)

def main(carrier, query_type='ip', whoise_server='whois.apnic.net'):
    lines = query_whoise(whoise_server, '-i mb MAINT-%s' % carrier).splitlines()
    for line in lines:
        if 'asn' == query_type:
            query_asn(line)
        else:
            assert 'ip' == query_type
            query_ip(line)
    print('') # end indicator


def query_asn(line):
    result = RE_AUTNUM.findall(line)
    if result:
        print(result[0])


def query_ip(line):
    result = RE_INETNUM.findall(line)
    if result:
        start_ip, end_ip = result[0]
        if start_ip == end_ip:
            return start_ip
        else:
            try:
                print(get_random_ip_in_range(start_ip, end_ip))
            except:
                import traceback

                traceback.print_exc()
                print(start_ip, end_ip, '!!!')


def query_whoise(server, query):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(15)
    try:
        s.connect((server, 43))
        s.send((query + '\r\n').encode())
        response = b''
        while True:
            d = s.recv(4096)
            response += d
            if not d:
                break
    finally:
        s.close()
    return response


def get_random_ip_in_range(start_ip, end_ip):
# http://dregsoft.com/blog/?p=24
    start_ip_bytes = struct.unpack('!i', socket.inet_aton(start_ip))[0]
    end_ip_bytes = struct.unpack('!i', socket.inet_aton(end_ip))[0]
    random_ip_bytes = random.randrange(start_ip_bytes, end_ip_bytes)
    random_ip = socket.inet_ntoa(struct.pack('!i', random_ip_bytes))
    return random_ip


if 1 == len(sys.argv):
    print('[Usage] ./by_carrier.py carrier [ip|asn] [whoise_server] > ip_list.txt')
    print('China Telecom:\t\t\t\tCHINANET')
    print('China Unicom:\t\t\t\tCNCGROUP')
    print('China Mobile:\t\t\t\tCN-CMCC')
    print('China Railway Telecom:\t\t\tCN-CRTC')
    print('China Education & Research Network:\tCERNET-AP')
    print('China Science & Technology Network:\tCN-CSTNET')
    print('Can also: ./by_carrier.py CHINANET asn | ./by_asn @stdin')
    sys.exit(3)
else:
    main(*sys.argv[1:])


########NEW FILE########
__FILENAME__ = by_country
#!/usr/bin/env python
import socket
import struct
import random
import sys
import urllib2

# Generate random ip from ip range of specific country

def main(target_country='CN', query_type='ip'):
    response = urllib2.urlopen('http://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest')
    lines = response.read().splitlines()
    if 'asn' == query_type:
        lines = [line for line in lines if '|asn|' in line]
        for line in lines[1:]:
            _, country, _, start_asn, asn_count, _, _ = line.split('|')
            if target_country == country:
                for i in range(int(asn_count)):
                    print(int(start_asn) + i)
    else:
        assert 'ip' == query_type
        lines = [line for line in lines if '|ipv4|' in line]
        for line in lines[1:]:
            _, country, _, start_ip, ip_count, _, _ = line.split('|')
            if target_country == country:
                print(get_random_ip_in_range(start_ip, int(ip_count)))
    print('') # end indicator


def get_random_ip_in_range(start_ip, ip_count):
# http://dregsoft.com/blog/?p=24
    start_ip_bytes = struct.unpack('!i', socket.inet_aton(start_ip))[0]
    random_ip_bytes = random.randrange(start_ip_bytes, start_ip_bytes + ip_count)
    random_ip = socket.inet_ntoa(struct.pack('!i', random_ip_bytes))
    return random_ip

if 1 == len(sys.argv):
    print('[Usage] ./by_country.py two_letter_country_code [ip|asn] > ip_list.txt')
    print('Lookup http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2 to find out')
    print('Can also: ./by_country.py CN asn | ./by_asn @stdin')
    sys.exit(3)
else:
    main(*sys.argv[1:])
########NEW FILE########
__FILENAME__ = limit
#!/usr/bin/env python
import sys
import random

def main(limit):
    limit = int(limit)
    all_ips = []
    while True:
        ip = sys.stdin.readline().strip()
        if ip:
            all_ips.append(ip)
        else:
            break
    if len(all_ips) > limit:
        selected_ips = random.sample(all_ips, limit)
    else:
        selected_ips = all_ips
    for ip in selected_ips:
        print(ip)
    print('')

if 1 == len(sys.argv):
    print('[Usage] ./limit.py limit')
    print('it reads ip line by line from stdin, and pick limit from all')
    sys.exit(3)
else:
    main(*sys.argv[1:])
########NEW FILE########
__FILENAME__ = l2_sniffer
#!/usr/bin/env python
import select
import threading
import contextlib
import traceback
import sys
from scapy.layers.inet import IP, IPerror
from scapy.config import conf

class L2Sniffer(threading.Thread):
    def __init__(self, iface, src, dst, no_filter=True):
        super(L2Sniffer, self).__init__()
        self.daemon = True
        self.no_filter = no_filter
        self.iface = iface
        self.src = src
        self.dst = dst
        self.started = threading.Event()
        self.started.clear()
        self.should_stop = False
        self.packets = []

    def run(self):
        try:
            if self.no_filter:
                filter = None # for PPP link
            else:
                filter = '(dst host %s and src host %s) or icmp' % (self.src, self.dst)
            with contextlib.closing(conf.L2listen(iface=self.iface, filter=filter)) as l2_listen_socket:
                self.started.set()
                while True:
                    result = select.select([l2_listen_socket], [], [], 0.1)
                    if l2_listen_socket not in result[0]:
                        if self.should_stop:
                            return # no data and should stop => stop
                        continue
                    packet = l2_listen_socket.recv(2048)
                    if IP in packet:
                        packet = packet[IP]
                    else:
                        continue
                    self.collect_packet(packet)
        except:
            traceback.print_exc()

    def start_sniffing(self):
        self.start()
        self.started.wait(1)

    def stop_sniffing(self):
        self.should_stop = True
        self.join()
        return self.packets

    def collect_packet(self, packet):
        packet.mark = None
        if self.dst == packet.src and self.src == packet.dst:
            self.packets.append(packet)
        elif IPerror in packet:
            if self.src == packet[IPerror].src and self.dst == packet[IPerror].dst:
                self.packets.append(packet)

if '__main__' == __name__:
    if 1 == len(sys.argv):
        print('[Usage] ./l2_sniffer.py destination_ip')
        sys.exit(3)
    else:
        import routing_table

        dst = sys.argv[1]
        no_filter = True
        iface, src, _ = routing_table.get_route(dst)
        sniffer = L2Sniffer(iface, src, dst, no_filter=no_filter)
        sniffer.start_sniffing()
        print('press enter to stop...')
        sys.stdin.readline()
        for packet in sniffer.stop_sniffing():
            print(packet.time, packet.src, packet.dst)
########NEW FILE########
__FILENAME__ = l3_sniffer
#!/usr/bin/env python
import socket
import threading
import contextlib
import traceback
import time
import sys
from scapy.arch.linux import get_last_packet_timestamp
from scapy.layers.inet import IP, IPerror

ERROR_NO_DATA = 11

class L3Sniffer(threading.Thread):
    def __init__(self, src, dst):
        super(L3Sniffer, self).__init__()
        self.daemon = True
        self.src = src
        self.dst = dst
        self.started = threading.Event()
        self.started.clear()
        self.should_stop = False
        self.packets = []

    def run(self):
        try:
            with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)) as icmp_socket:
                icmp_socket.settimeout(0)
                with contextlib.closing(
                    socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)) as udp_socket:
                    udp_socket.settimeout(0)
                    with contextlib.closing(
                        socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)) as tcp_socket:
                        tcp_socket.settimeout(0)
                        self.started.set()
                        self.capture(icmp_socket, udp_socket, tcp_socket)

        except:
            traceback.print_exc()

    def capture(self, icmp_socket, udp_socket, tcp_socket):
        while True:
            icmp_packet = try_receive_packet(icmp_socket)
            udp_packet = try_receive_packet(udp_socket)
            tcp_packet = try_receive_packet(tcp_socket)
            if icmp_packet is not None:
                self.collect_packet(icmp_packet)
            if udp_packet is not None:
                self.collect_packet(udp_packet)
            if tcp_packet is not None:
                self.collect_packet(tcp_packet)
            if icmp_packet is None and udp_packet is None and tcp_packet is None:
                if self.should_stop:
                    return
                else:
                    time.sleep(0.1)

    def collect_packet(self, packet):
        packet.mark = None
        if self.dst == packet.src and self.src == packet.dst:
            self.packets.append(packet)
        elif IPerror in packet:
            if self.src == packet[IPerror].src and self.dst == packet[IPerror].dst:
                self.packets.append(packet)

    def start_sniffing(self):
        self.start()
        self.started.wait(1)

    def stop_sniffing(self):
        self.should_stop = True
        self.join()
        return self.packets


def dump_socket(s, packet_class):
    packets = []
    while True:
        packet = try_receive_packet(s, packet_class)
        if packet is None:
            return packets
        else:
            packets.append(packet)


def try_receive_packet(s, packet_class=IP):
    try:
        packet = packet_class(s.recv(1024))
        packet.time = get_last_packet_timestamp(s)
        return packet
    except socket.error as e:
        if ERROR_NO_DATA == e[0]:
            return None
        else:
            raise


if '__main__' == __name__:
    if 1 == len(sys.argv):
        print('[Usage] ./l3_sniffer.py destination_ip')
        sys.exit(3)
    else:
        import routing_table

        dst = sys.argv[1]
        _, src, _ = routing_table.get_route(dst)
        sniffer = L3Sniffer(src, dst)
        sniffer.start_sniffing()
        print('press enter to stop...')
        sys.stdin.readline()
        for packet in sniffer.stop_sniffing():
            print(packet.time, packet.src, packet.dst)
########NEW FILE########
__FILENAME__ = raw_socket_sender
from scapy.layers.inet import TCP, UDP
import socket
import atexit
import time

raw_socket = None

def send(packet):
    packet.time = time.time()
    if UDP in packet:
        get_socket().sendto(str(packet), (packet.dst, packet[UDP].dport))
    elif TCP in packet:
        get_socket().sendto(str(packet), (packet.dst, packet[TCP].dport))
    else:
        raise Exception('packet is neither UDP nor TCP')


def get_socket():
    global raw_socket
    if raw_socket:
        return raw_socket
    raw_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    raw_socket.setsockopt(socket.SOL_IP, socket.IP_HDRINCL, 1)
    atexit.register(raw_socket.close)
    return raw_socket
########NEW FILE########
__FILENAME__ = routing_table
__import__('scapy.route')
from scapy.config import conf
import os


def make_route_fixed(outbound_iface, outbound_ip):
    conf.route.ifadd(outbound_iface, '%s/0' % outbound_ip)


def get_route(dst):
    return conf.route.route(dst)

OUTBOUND_IFACE = os.getenv('OUTBOUND_IFACE')
OUTBOUND_IP = os.getenv('OUTBOUND_IP')
if OUTBOUND_IFACE and OUTBOUND_IP:
    make_route_fixed(OUTBOUND_IFACE, OUTBOUND_IP)
########NEW FILE########
__FILENAME__ = tcpdump_sniffer
#!/usr/bin/env python
import subprocess
import tempfile
import sys
from scapy.layers.inet import IP, IPerror
from scapy.utils import rdpcap

class TcpdumpSniffer(object):
    def __init__(self, iface, src, dst):
        self.iface = iface
        self.src = src
        self.dst = dst
        self.packets = []

    def start_sniffing(self):
        self.pcap_file_path = tempfile.mktemp()
        filter = '(dst host %s and src host %s) or icmp' % (self.src, self.dst)
        self.tcmpdump_proc = subprocess.Popen(
            ['tcpdump', '-i', self.iface, '-w', self.pcap_file_path, filter],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=subprocess.PIPE)

    def stop_sniffing(self):
        self.tcmpdump_proc.terminate()
        self.tcmpdump_proc.wait()
        for packet in rdpcap(self.pcap_file_path):
            if IP in packet:
                self.collect_packet(packet[IP])
        return self.packets

    def collect_packet(self, packet):
        packet.mark = None
        if self.dst == packet.src and self.src == packet.dst:
            self.packets.append(packet)
        elif IPerror in packet:
            if self.src == packet[IPerror].src and self.dst == packet[IPerror].dst:
                self.packets.append(packet)


if '__main__' == __name__:
    if 1 == len(sys.argv):
        print('[Usage] ./tcpdump_sniffer.py destination_ip')
        sys.exit(3)
    else:
        import routing_table

        dst = sys.argv[1]
        iface, src, _ = routing_table.get_route(dst)
        sniffer = TcpdumpSniffer(iface, src, dst)
        sniffer.start_sniffing()
        print('capturing at %s between %s and %s, press enter to stop...' % (iface, src, dst))
        sys.stdin.readline()
        for packet in sniffer.stop_sniffing():
            print(packet.time, packet.src, packet.dst)
########NEW FILE########
__FILENAME__ = dns_wrong_answer_probe
#!/usr/bin/env python
import sys
import os
import time
import socket
import atexit
from scapy.layers.inet import IP, UDP, UDPerror, IPerror
from scapy.layers.dns import DNS, DNSQR

SYS_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if SYS_PATH not in sys.path:
    sys.path.append(SYS_PATH)
from qiang import networking

# Probe using the fact GFW will send back wrong dns answer if the dns question is about certain domain name
#
# Send offending payload (A.K.A try resolve domain name twitter.com) with TTL 1
# PROBE =OFFENDING_PAYLOAD=> ROUTER-1 (TTL is 1)
# PROBE <=ICMP_TTL_EXCEEDED= ROUTER-1
# Router will send back a ICMP packet tell us its (the router) ip address
#
# Send offending payload (A.K.A try resolve domain name twitter.com) with big enough TTL
# PROBE =OFFENDING_PAYLOAD => ROUTER-1 .. => ROUTER ATTACHED GFW (TTL is N)
# PROBE <=ICMP_TTL_EXCEEDED= ROUTER-1 .. <= ROUTER ATTACHED GFW
# PROBE <=WRONG_DNS_ANSWER= ROUTER-1 .. <=ROUTER ATTACHED GFW (WRONG_DNS_ANSWER was sent by GFW)
# The wrong dns answer sent back by GFW will be accepted by our browser so will try to access twitter.com
# via a wrong ip address. To tell if the answer is right or wrong, check the list below.
# When we found a wrong answer, we know the router is attached with GFW. The ip adress of the router
# can be told from the ICMP packet sent back previously.

# source http://zh.wikipedia.org/wiki/%E5%9F%9F%E5%90%8D%E6%9C%8D%E5%8A%A1%E5%99%A8%E7%BC%93%E5%AD%98%E6%B1%A1%E6%9F%93
WRONG_ANSWERS = set([
    '4.36.66.178',
    '8.7.198.45',
    '37.61.54.158',
    '46.82.174.68',
    '59.24.3.173',
    '64.33.88.161',
    '64.33.99.47',
    '64.66.163.251',
    '65.104.202.252',
    '65.160.219.113',
    '66.45.252.237',
    '72.14.205.99',
    '72.14.205.104',
    '78.16.49.15',
    '93.46.8.89',
    '128.121.126.139',
    '159.106.121.75',
    '169.132.13.103',
    '192.67.198.6',
    '202.106.1.2',
    '202.181.7.85',
    '203.161.230.171',
    '203.98.7.65',
    '207.12.88.98',
    '208.56.31.43',
    '209.36.73.33',
    '209.145.54.50',
    '209.220.30.174',
    '211.94.66.147',
    '213.169.251.35',
    '216.221.188.182',
    '216.234.179.13',
    '243.185.187.39'
])

DNS_TYPE_A = 1
SPORT = 19840
DPORT = 53
ROOT_USER_ID = 0

def main(dst, ttl):
    iface, src, _ = networking.get_route(dst)
    if ROOT_USER_ID == os.geteuid():
        sniffer = networking.create_sniffer(iface, src, dst)
        probe = DnsWrongAnswerProbe(src, SPORT, dst, DPORT, int(ttl), sniffer)
        sniffer.start_sniffing()
        probe.poke()
        time.sleep(2)
        sniffer.stop_sniffing()
        report = probe.peek()
    else:
        probe = DnsWrongAnswerProbe(src, SPORT, dst, DPORT, int(ttl), sniffer=None)
        probe.poke()
        time.sleep(2)
        report = probe.peek()
        report.pop('ROUTER_IP')
    report.pop('PACKETS')
    print(report)


class DnsWrongAnswerProbe(object):
    def __init__(self, src, sport, dst, dport, ttl, sniffer):
        self.src = src
        self.sport = sport
        self.dst = dst
        self.dport = dport
        self.ttl = ttl
        self.sniffer = sniffer
        self.report = {
            'ROUTER_IP': None,
            'WRONG_ANSWER': None,
            'RIGHT_ANSWER': None,
            'PACKETS': []
        }
        self.udp_socket = None

    def poke(self):
        question = DNS(rd=1, qd=DNSQR(qname='twitter.com'))
        if self.sniffer:
            packet = IP(dst=self.dst, src=self.src, id=self.ttl, ttl=self.ttl) / UDP(
                sport=self.sport) / question
            networking.send(packet)
            self.report['PACKETS'].append(('QUESTION', packet))
        else:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            atexit.register(self.udp_socket.close)
            self.udp_socket.settimeout(0)
            self.udp_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, self.ttl)
            self.udp_socket.bind((self.src, self.sport))
            self.udp_socket.sendto(str(question), (self.dst, self.dport))

    def peek(self):
        if self.sniffer:
            packets = self.sniffer.packets
        else:
            packets = networking.dump_socket(self.udp_socket, packet_class=DNS)
            self.udp_socket.close()
        for packet in packets:
            if DNS in packet:
                self.analyze_dns_packet(packet)
            elif IPerror in packet and UDPerror in packet:
                self.analyze_udp_error_packet(packet)
        return self.report

    def close(self):
        if self.udp_socket:
            self.udp_socket.close()

    def analyze_dns_packet(self, packet):
        if UDP in packet:
            if self.dport != packet[UDP].sport:
                return
            if self.sport != packet[UDP].dport:
                return
        if 0 == packet[DNS].ancount:
            return self.record_wrong_answer('[BLANK]', packet)
        for i in range(packet[DNS].ancount):
            if DNS_TYPE_A == packet[DNS].an[i].type:
                answer = packet[DNS].an[i].rdata
                if answer in WRONG_ANSWERS:
                    return self.record_wrong_answer(answer, packet)
                else:
                    return self.record_right_answer(answer, packet)
        self.report['PACKETS'].append('UNKNOWN', packet)

    def analyze_udp_error_packet(self, packet):
        if self.sport != packet[UDPerror].sport:
            return
        if self.dport != packet[UDPerror].dport:
            return
        self.record_router_ip(packet.src, packet)

    def record_wrong_answer(self, wrong_answer, packet):
        if self.report['WRONG_ANSWER']:
            self.report['PACKETS'].append(('ADDITIONAL_WRONG_ANSWER', packet))
        else:
            self.report['PACKETS'].append(('WRONG_ANSWER', packet))
            self.report['WRONG_ANSWER'] = wrong_answer

    def record_right_answer(self, right_answer, packet):
        if self.report['RIGHT_ANSWER']:
            self.report['PACKETS'].append(('ADDITIONAL_RIGHT_ANSWER', packet))
        else:
            self.report['PACKETS'].append(('RIGHT_ANSWER', packet))
            self.report['RIGHT_ANSWER'] = right_answer

    def record_router_ip(self, router_ip, packet):
        if self.report['ROUTER_IP']:
            self.report['PACKETS'].append(('ADDITIONAL_ROUTER_IP', packet))
        else:
            self.report['PACKETS'].append(('ROUTER_IP', packet))
            self.report['ROUTER_IP'] = router_ip

if '__main__' == __name__:
    if 1 == len(sys.argv):
        print('[Usage] ./dns_wrong_answer_probe.py destination_ip ttl')
        sys.exit(3)
    else:
        main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = tcp_packet_drop_probe
#!/usr/bin/env python
import socket
import os
import sys
import time
import atexit
from scapy.layers.inet import IP, TCP, IPerror, TCPerror

SYS_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if SYS_PATH not in sys.path:
    sys.path.append(SYS_PATH)
from qiang import networking

# Probe using the fact GFW will configure some router to only drop packet of certain source ip and port combination
#
# Normally GFW does not drop your packet, it will jam the connection using TCP RST or FAKE DNS ANSWER.
# However, if you are running some OpenVPN like service on the server and being detected *somehow* by GFW,
# it will block your ip or just a specific port of that ip. We can use the fact some router is dropping packet
# to show its connection with GFW.
#
# Send offending payload (A.K.A source port being the blocked port) with TTL 1
# PROBE =OFFENDING_PAYLOAD=> ROUTER-1 (TTL is 1)
# PROBE <=ICMP_TTL_EXCEEDED= ROUTER-1
# Router will send back a ICMP packet tell us its (the router) ip address
#
# Send offending payload (A.K.A source port being the blocked port) with big enough TTL
# PROBE =OFFENDING_PAYLOAD => ROUTER-1 .. => ROUTER ATTACHED GFW (TTL is N)
# PROBE <=NOTHING= (Nothing returned after 2 seconds)
# We know the router is dropping our packet as no ICMP being returned
#
# Send non-offending payload (A.K.A source port being the reference port) with big enough TTL
# PROBE =NON_OFFENDING_PAYLOAD => ROUTER-1 .. => ROUTER ATTACHED GFW (TTL is N)
# PROBE <=ICMP_TTL_EXCEEDED= ROUTER-1 .. <= ROUTER ATTACHED GFW
# Although the router ip returned from this ICMP might not be same router, as source port was not the same.
# But there is a great chance the router is the same router, as we can tell same router is responsible for
# TCP RST and FAKE DNS ANSWER.

TH_SYN = 0x02        # synchronize sequence numbers
TH_ACK = 0x10        # acknowledgment number set
ROOT_USER_ID = 0

def main(dst, sport, ttl):
    iface, src, _ = networking.get_route(dst)
    if ROOT_USER_ID == os.geteuid():
        sniffer = networking.create_sniffer(iface, src, dst)
        probe = TcpPacketDropProbe(src, int(sport), dst, 80, int(ttl), sniffer)
        sniffer.start_sniffing()
        probe.poke()
        time.sleep(2)
        sniffer.stop_sniffing()
        report = probe.peek()
    else:
        probe = TcpPacketDropProbe(src, int(sport), dst, 80, int(ttl), sniffer=None)
        probe.poke()
        time.sleep(2)
        report = probe.peek()
    packets = report.pop('PACKETS')
    print(report)
    for mark, packet in packets:
        formatted_packet = packet.sprintf('%.time% %IP.src% -> %IP.dst% %TCP.flags%')
        print('[%s] %s' % (mark, formatted_packet))


class TcpPacketDropProbe(object):
    def __init__(self, src, sport, dst, dport, ttl, sniffer, one_packet_only=False):
        self.src = src
        self.sport = sport
        self.dst = dst
        self.dport = dport
        self.ttl = ttl
        self.sniffer = sniffer
        self.one_packet_only = one_packet_only
        self.report = {
            'ROUTER_IP_FOUND_BY_PACKET_1': None,
            'ROUTER_IP_FOUND_BY_PACKET_2': None,
            'ROUTER_IP_FOUND_BY_PACKET_3': None,
            'SYN_ACK?': None,
            'PACKETS': []
        }
        self.tcp_socket = None

    def poke(self):
        if self.sniffer:
            packet1 = IP(src=self.src, dst=self.dst, id=self.ttl * 10 + 1, ttl=self.ttl) / TCP(
                sport=self.sport, dport=self.dport, flags='S', seq=0)
            networking.send(packet1)
            self.report['PACKETS'].append(('PACKET_1', packet1))
            if not self.one_packet_only:
                packet2 = IP(src=self.src, dst=self.dst, id=self.ttl * 10 + 2, ttl=self.ttl) / TCP(
                    sport=self.sport, dport=self.dport, flags='S', seq=0)
                networking.send(packet2)
                self.report['PACKETS'].append(('PACKET_2', packet2))
                packet3 = IP(src=self.src, dst=self.dst, id=self.ttl * 10 + 3, ttl=self.ttl) / TCP(
                    sport=self.sport, dport=self.dport, flags='S', seq=0)
                networking.send(packet3)
                self.report['PACKETS'].append(('PACKET_3', packet3))
        else:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            atexit.register(networking.immediately_close_tcp_socket_so_sport_can_be_reused, self.tcp_socket)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, self.ttl)
            self.tcp_socket.settimeout(2)
            self.tcp_socket.bind((self.src, self.sport)) # if sport change the route going through might change
            try:
                self.tcp_socket.connect((self.dst, self.dport))
                self.report['SYN_ACK?'] = True
            except socket.timeout:
                pass

    def close(self):
        networking.immediately_close_tcp_socket_so_sport_can_be_reused(self.tcp_socket)

    def peek(self):
        if not self.sniffer:
            return self.report
        for packet in self.sniffer.packets:
            if TCP in packet:
                self.analyze_tcp_packet(packet)
            elif IPerror in packet and TCPerror in packet:
                self.analyze_tcp_error_packet(packet)
        return self.report

    def analyze_tcp_packet(self, packet):
        if self.dport != packet[TCP].sport:
            return
        if self.sport != packet[TCP].dport:
            return
        if packet[TCP].flags & TH_SYN and packet[TCP].flags & TH_ACK:
            self.record_syn_ack(packet)
        else:
            self.report['PACKETS'].append(('UNKNOWN', packet))

    def analyze_tcp_error_packet(self, packet):
        if self.sport != packet[TCPerror].sport:
            return
        if self.dport != packet[TCPerror].dport:
            return
        if self.ttl * 10 + 1 == packet[IPerror].id:
            self.record_router_ip(packet.src, 1, packet)
        elif self.ttl * 10 + 2 == packet[IPerror].id:
            self.record_router_ip(packet.src, 2, packet)
        elif self.ttl * 10 + 3 == packet[IPerror].id:
            self.record_router_ip(packet.src, 3, packet)
        else:
            self.report['PACKETS'].append(('UNKNOWN', packet))

    def record_syn_ack(self, packet):
        if self.report['SYN_ACK?']:
            self.report['PACKETS'].append(('ADDITIONAL_SYN_ACK', packet))
        else:
            self.report['PACKETS'].append(('SYN_ACK', packet))
            self.report['SYN_ACK?'] = True

    def record_router_ip(self, router_ip, packet_index, packet):
        if self.report['ROUTER_IP_FOUND_BY_PACKET_%s' % packet_index]:
            self.report['PACKETS'].append(('ADDITIONAL_ROUTER_IP_FOUND_BY_PACKET_%s' % packet_index, packet))
        else:
            self.report['PACKETS'].append(('ROUTER_IP_FOUND_BY_PACKET_%s' % packet_index, packet))
            self.report['ROUTER_IP_FOUND_BY_PACKET_%s' % packet_index] = router_ip

if '__main__' == __name__:
    if 1 == len(sys.argv):
        print('[Usage] ./tcp_packet_drop_probe.py destination_ip sport ttl')
        sys.exit(3)
    else:
        main(*sys.argv[1:])
########NEW FILE########
__FILENAME__ = tcp_rst_probe
#!/usr/bin/env python
import sys
import time
import os
import socket
import struct
import atexit
from scapy.layers.inet import IP, TCP, IPerror, TCPerror
from scapy.layers.dns import DNS, DNSQR

SYS_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if SYS_PATH not in sys.path:
    sys.path.append(SYS_PATH)
from qiang import networking

# Probe using the fact GFW will send back TCP RST if keyword detected in HTTP GET URL or HOST
#
# Send SYN with TTL 1
# PROBE =SYN=> ROUTER-1 (TTL is 1)
# PROBE <=ICMP_TTL_EXCEEDED= ROUTER-1
# Router will send back a ICMP packet tell us its (the router) ip address
#
# Send offending payload after SYN (A.K.A GET facebook.com) with TTL 1
# PROBE =OFFENDING_PAYLOAD=> ROUTER-1 (TTL is 1)
# PROBE <=ICMP_TTL_EXCEEDED= ROUTER-1
# Router will send back a ICMP packet tell us its (the router) ip address
#
# Send SYN with big enough TTL
# PROBE =OFFENDING_PAYLOAD => ROUTER-1 .. => ROUTER ATTACHED GFW (TTL is N)
# PROBE <=ICMP_TTL_EXCEEDED= ROUTER-1 .. <= ROUTER ATTACHED GFW
# SYN just by itself does not trigger GFW
#
# Send offending payload after SYN (A.K.A GET facebook.com) with big enough TTL
# PROBE =OFFENDING_PAYLOAD => ROUTER-1 .. => ROUTER ATTACHED GFW (TTL is N)
# PROBE <=ICMP_TTL_EXCEEDED= ROUTER-1 .. <= ROUTER ATTACHED GFW
# PROBE <=RST= ROUTER-1 .. <=ROUTER ATTACHED GFW (RST was sent by GFW to jam the connection)
# SYN by itself does not trigger GFW. Offending payload by itself does not trigger GFW as well.
# Only if SYN follows the ACK in a short time, and keyword in the HTTP GET URL or HOST will trigger.
# SYN+ACK will not be sent back in this case, as SYN never reaches the destination.
# The RST sent back from GFW will have TTL different from other packets sent back from destination.
# So by checking TTL of returning packets we can tell if GFW is jamming the connection.
# Also based on the ICMP packet we can tell the ip address of router attached GFW.

ERROR_CONNECTION_RESET = 104
ERROR_NO_DATA = 11
TH_SYN = 0x02        # synchronize sequence numbers
TH_RST = 0x04        # reset connection
TH_ACK = 0x10        # acknowledgment number set
SPORT = 19840
HTTP_DPORT = 80
DNS_DPORT = 53
SMTP_DPORT = 25
ROOT_USER_ID = 0


def main(dst, ttl, probe_type_code='HTTP', waits_for_syn_ack=False):
    probe_types = list_probe_types()
    probe_type = probe_types[probe_type_code]
    iface, src, _ = networking.get_route(dst)
    dport = probe_type.get_default_dport()
    if ROOT_USER_ID == os.geteuid():
        sniffer = networking.create_sniffer(iface, src, dst)
        probe = probe_type(
            src, SPORT, dst, dport, int(ttl), sniffer,
            waits_for_syn_ack=waits_for_syn_ack)
        sniffer.start_sniffing()
        probe.poke()
        time.sleep(2)
        sniffer.stop_sniffing()
        report = probe.peek()
    else:
        probe = probe_type(src, SPORT, dst, dport, int(ttl), sniffer=None)
        probe.poke()
        time.sleep(2)
        report = probe.peek()
    packets = report.pop('PACKETS')
    print(report)
    for mark, packet in packets:
        formatted_packet = packet.sprintf('%.time% %IP.src% -> %IP.dst% %TCP.flags%')
        print('[%s] %s' % (mark, formatted_packet))


def list_probe_types():
    return {
        'HTTP': HttpTcpRstProbe,
        'DNS': DnsTcpRstProbe,
        'SMTP_HELO_RCPT_TO': SmtpHeloRcptToTcpRstProbe,
        'SMTP_MAIL_FROM': SmtpMailFromTcpRstProbe,
        'SMTP_RCPT_TO': SmtpRcptToTcpRstProbe
    }


class TcpRstProbe(object):
    def __init__(self, src, sport, dst, dport, ttl, sniffer,
                 interval_between_syn_and_offending_payload=0.5,
                 waits_for_syn_ack=False):
        self.src = src
        self.sport = sport
        self.dst = dst
        self.dport = dport
        self.ttl = ttl
        self.sniffer = sniffer
        self.interval_between_syn_and_offending_payload = interval_between_syn_and_offending_payload
        self.waits_for_syn_ack = waits_for_syn_ack
        self.report = self.initialize_report({
            'ROUTER_IP_FOUND_BY_SYN': None,
            'ROUTER_IP_FOUND_BY_OFFENDING_PAYLOAD': None,
            'SYN_ACK?': None,
            'RST_AFTER_SYN?': None,
            'RST_AFTER_OFFENDING_PAYLOAD?': None,
            'PACKETS': []
        })
        self.tcp_socket = None
        self.offending_payload_sent_at = None

    @classmethod
    def initialize_report(cls, report):
        return report

    def poke(self):
        self.send_syn()
        time.sleep(self.interval_between_syn_and_offending_payload)
        self.offending_payload_sent_at = time.time()
        self.send_offending_payload()

    def send_syn(self):
        if self.sniffer:
            packet = IP(src=self.src, dst=self.dst, id=self.ttl * 10 + 1,
                        ttl=64 if self.waits_for_syn_ack else self.ttl) / \
                     TCP(sport=self.sport, dport=self.dport, flags='S', seq=0)
            networking.send(packet)
            self.report['PACKETS'].append(('SYN', packet))
            if self.waits_for_syn_ack:
                self.wait_for_syn_ack()
        else:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            atexit.register(networking.immediately_close_tcp_socket_so_sport_can_be_reused, self.tcp_socket)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.settimeout(2)
            self.tcp_socket.bind((self.src, self.sport)) # if sport change the route going through might change
            self.tcp_socket.connect((self.dst, self.dport))

    def wait_for_syn_ack(self):
        for i in range(10):
            time.sleep(0.3)
            self.peek()
            if self.report['SYN_ACK?']:
                return
        raise Exception('SYN ACK not received')

    def close(self):
        networking.immediately_close_tcp_socket_so_sport_can_be_reused(self.tcp_socket)

    def send_offending_payload(self):
        if self.sniffer:

            packet = IP(src=self.src, dst=self.dst, id=self.ttl * 10 + 2, ttl=self.ttl) / \
                     TCP(sport=self.sport, dport=self.dport, flags='A',
                         seq=1, ack=self.report['SYN_ACK?'] or 100) / self.get_offending_payload()
            networking.send(packet)
            self.report['PACKETS'].append(('OFFENDING_PAYLOAD', packet))
        else:
            self.tcp_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, self.ttl)
            try:
                self.tcp_socket.send(self.get_offending_payload())
            except socket.error as e:
                if ERROR_CONNECTION_RESET == e[0]:
                    self.report['RST_AFTER_SYN?'] = True
                else:
                    raise

    def get_offending_payload(self):
        raise NotImplementedError()

    def peek(self):
        if self.sniffer:
            for packet in self.sniffer.packets:
                if TCP in packet:
                    self.analyze_tcp_packet(packet)
                elif IPerror in packet and TCPerror in packet:
                    self.analyze_tcp_error_packet(packet)
            return self.report
        else:
            if not self.report['RST_AFTER_SYN?']:
                self.tcp_socket.settimeout(0)
                try:
                    self.tcp_socket.recv(1024)
                    self.tcp_socket.recv(1024)
                except socket.error as e:
                    if ERROR_CONNECTION_RESET == e[0]:
                        self.report['RST_AFTER_OFFENDING_PAYLOAD?'] = True
                    elif ERROR_NO_DATA == e[0]:
                        pass
                    else:
                        raise
            return self.report

    def analyze_tcp_packet(self, packet):
        if self.dport != packet[TCP].sport:
            return
        if self.sport != packet[TCP].dport:
            return
        if packet[TCP].flags & TH_SYN and packet[TCP].flags & TH_ACK:
            self.record_syn_ack(packet)
        elif packet[TCP].flags & TH_RST:
            if not self.offending_payload_sent_at or packet.time < self.offending_payload_sent_at:
                self.record_rst_after_syn(packet)
            else:
                self.record_rst_after_offending_payload(packet)
        else:
            self.report['PACKETS'].append((self.handle_unknown_packet(packet), packet))

    def analyze_tcp_error_packet(self, packet):
        if self.sport != packet[TCPerror].sport:
            return
        if self.dport != packet[TCPerror].dport:
            return
        if self.ttl * 10 + 1 == packet[IPerror].id:
            self.record_router_ip_found_by_syn(packet.src, packet)
        elif self.ttl * 10 + 2 == packet[IPerror].id:
            self.record_router_ip_found_by_offending_payload(packet.src, packet)
        else:
            self.report['PACKETS'].append((self.handle_unknown_packet(packet), packet))

    def handle_unknown_packet(self, packet):
        return 'UNKNOWN'

    def record_syn_ack(self, packet):
        if self.report['SYN_ACK?']:
            self.report['PACKETS'].append(('ADDITIONAL_SYN_ACK', packet))
        else:
            self.report['PACKETS'].append(('SYN_ACK', packet))
            self.report['SYN_ACK?'] = packet[TCP].seq

    def record_rst_after_syn(self, packet):
        if self.report['RST_AFTER_SYN?']:
            self.report['PACKETS'].append(('ADDITIONAL_RST_AFTER_SYN', packet))
        else:
            self.report['PACKETS'].append(('RST_AFTER_SYN', packet))
            self.report['RST_AFTER_SYN?'] = True

    def record_rst_after_offending_payload(self, packet):
        if self.report['RST_AFTER_OFFENDING_PAYLOAD?']:
            self.report['PACKETS'].append(('ADDITIONAL_RST_AFTER_OFFENDING_PAYLOAD', packet))
        else:
            self.report['PACKETS'].append(('RST_AFTER_OFFENDING_PAYLOAD', packet))
            self.report['RST_AFTER_OFFENDING_PAYLOAD?'] = True

    def record_router_ip_found_by_syn(self, router_ip, packet):
        if self.report['ROUTER_IP_FOUND_BY_SYN']:
            self.report['PACKETS'].append(('ADDITIONAL_ROUTER_IP_FOUND_BY_SYN', packet))
        else:
            self.report['PACKETS'].append(('ROUTER_IP_FOUND_BY_SYN', packet))
            self.report['ROUTER_IP_FOUND_BY_SYN'] = router_ip

    def record_router_ip_found_by_offending_payload(self, router_ip, packet):
        if self.report['ROUTER_IP_FOUND_BY_OFFENDING_PAYLOAD']:
            self.report['PACKETS'].append(('ADDITIONAL_ROUTER_IP_FOUND_BY_OFFENDING_PAYLOAD', packet))
        else:
            self.report['PACKETS'].append(('ROUTER_IP_FOUND_BY_OFFENDING_PAYLOAD', packet))
            self.report['ROUTER_IP_FOUND_BY_OFFENDING_PAYLOAD'] = router_ip


class ThreePacketTcpRstProbe(TcpRstProbe):
# SYN, OFFENDING_PAYLOAD_1, OFFENDING_PAYLOAD_2
    @classmethod
    def get_default_dport(cls):
        return SMTP_DPORT

    def send_offending_payload(self):
        if self.sniffer:
            packet = IP(src=self.src, dst=self.dst, id=self.ttl * 10 + 2, ttl=self.ttl) / \
                     TCP(sport=self.sport, dport=self.dport, flags='A', seq=1, ack=100)
            networking.send(packet)
            self.report['PACKETS'].append(('OFFENDING_PAYLOAD_1', packet))
            packet = IP(src=self.src, dst=self.dst, id=self.ttl * 10 + 3, ttl=self.ttl) / \
                     TCP(sport=self.sport, dport=self.dport, flags='A', seq=1, ack=100) / self.get_offending_payload()
            networking.send(packet)
            self.report['PACKETS'].append(('OFFENDING_PAYLOAD_2', packet))
        else:
            self.tcp_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, self.ttl)
            try:
                self.tcp_socket.send(self.get_offending_payload())
            except socket.error as e:
                if ERROR_CONNECTION_RESET == e[0]:
                    self.report['RST_AFTER_SYN?'] = True
                else:
                    raise

    def handle_unknown_packet(self, packet):
        if IPerror in packet and self.ttl * 10 + 3 == packet[IPerror].id:
            if self.report.get('ROUTER_IP_FOUND_BY_OFFENDING_PAYLOAD_2'):
                return 'ADDITIONAL_ROUTER_IP_FOUND_BY_OFFENDING_PAYLOAD_2'
            else:
                self.report['ROUTER_IP_FOUND_BY_OFFENDING_PAYLOAD_2'] = packet.src
                return 'ROUTER_IP_FOUND_BY_OFFENDING_PAYLOAD_2'
        return super(ThreePacketTcpRstProbe, self).handle_unknown_packet(packet)


class DnsTcpRstProbe(TcpRstProbe):
    @classmethod
    def get_default_dport(cls):
        return DNS_DPORT

    def get_offending_payload(self):
        offending_payload = str(DNS(rd=1, qd=DNSQR(qname="dl.dropbox.com")))
        return struct.pack("!H", len(offending_payload)) + offending_payload


class HttpTcpRstProbe(TcpRstProbe):
    @classmethod
    def get_default_dport(cls):
        return HTTP_DPORT

    def get_offending_payload(self):
        return 'GET / HTTP/1.1\r\nHost: www.facebook.com\r\n\r\n'


class SmtpMailFromTcpRstProbe(ThreePacketTcpRstProbe):
    def get_offending_payload(self):
        return 'MAIL FROM: xiazai@upup.info\r\n'


class SmtpRcptToTcpRstProbe(ThreePacketTcpRstProbe):
    def get_offending_payload(self):
        return 'RCPT TO: xiazai@upup.info\r\n'


class SmtpHeloRcptToTcpRstProbe(TcpRstProbe):
    @classmethod
    def get_default_dport(cls):
        return SMTP_DPORT

    @classmethod
    def initialize_report(cls, report):
        return dict(report, USER_NOT_LOCAL_ERROR=None)

    def get_offending_payload(self):
        return 'HELO 163.com\r\nRCPT TO: xiazai@upup.info\r\n'

    def handle_unknown_packet(self, packet):
        if TCP in packet and '551 User not local; please try <forward-path>\r\n' == packet[TCP].payload:
            self.report['USER_NOT_LOCAL_ERROR'] = True
            return 'USER_NOT_LOCAL_ERROR'
        return super(SmtpHeloRcptToTcpRstProbe, self).handle_unknown_packet(packet)


if '__main__' == __name__:
    import argparse

    argument_parser = argparse.ArgumentParser(description="Detect GFW attached router using the TCP RST sent back")
    argument_parser.add_argument('destination', help='ip address to shoot at')
    argument_parser.add_argument('ttl', type=int)
    argument_parser.add_argument('--probe', choices=list_probe_types().keys(), default='HTTP')
    argument_parser.add_argument('--behind-firewall', action='store_const', const=True)
    args = argument_parser.parse_args()
    main(args.destination, args.ttl, probe_type_code=args.probe, waits_for_syn_ack=args.behind_firewall)

########NEW FILE########
__FILENAME__ = udp_packet_drop_probe
#!/usr/bin/env python
import socket
import os
import sys
import time
import atexit
from scapy.layers.inet import IP, UDP, IPerror, UDPerror
from scapy.layers.dns import DNS, DNSQR

SYS_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if SYS_PATH not in sys.path:
    sys.path.append(SYS_PATH)
from qiang import networking

# Probe using the fact GFW will configure some router to only drop packet of certain source ip and port combination
#
# Normally GFW does not drop your packet, it will jam the connection using TCP RST or FAKE DNS ANSWER.
# However, if you are running some OpenVPN like service on the server and being detected *somehow* by GFW,
# it will block your ip or just a specific port of that ip. We can use the fact some router is dropping packet
# to show its connection with GFW.
#
# Send offending payload (A.K.A source port being the blocked port) with TTL 1
# PROBE =OFFENDING_PAYLOAD=> ROUTER-1 (TTL is 1)
# PROBE <=ICMP_TTL_EXCEEDED= ROUTER-1
# Router will send back a ICMP packet tell us its (the router) ip address
#
# Send offending payload (A.K.A source port being the blocked port) with big enough TTL
# PROBE =OFFENDING_PAYLOAD => ROUTER-1 .. => ROUTER ATTACHED GFW (TTL is N)
# PROBE <=NOTHING= (Nothing returned after 2 seconds)
# We know the router is dropping our packet as no ICMP being returned
#
# Send non-offending payload (A.K.A source port being the reference port) with big enough TTL
# PROBE =NON_OFFENDING_PAYLOAD => ROUTER-1 .. => ROUTER ATTACHED GFW (TTL is N)
# PROBE <=ICMP_TTL_EXCEEDED= ROUTER-1 .. <= ROUTER ATTACHED GFW
# Although the router ip returned from this ICMP might not be same router, as source port was not the same.
# But there is a great chance the router is the same router, as we can tell same router is responsible for
# TCP RST and FAKE DNS ANSWER.

ERROR_NO_DATA = 11
TH_SYN = 0x02        # synchronize sequence numbers
TH_ACK = 0x10        # acknowledgment number set
ROOT_USER_ID = 0

def main(dst, sport, ttl):
    iface, src, _ = networking.get_route(dst)
    if ROOT_USER_ID == os.geteuid():
        sniffer = networking.create_sniffer(iface, src, dst)
        probe = UdpPacketDropProbe(src, int(sport), dst, 53, int(ttl), sniffer)
        sniffer.start_sniffing()
        probe.poke()
        time.sleep(2)
        sniffer.stop_sniffing()
        report = probe.peek()
    else:
        probe = UdpPacketDropProbe(src, int(sport), dst, 53, int(ttl), sniffer=None)
        probe.poke()
        time.sleep(2)
        report = probe.peek()
    packets = report.pop('PACKETS')
    print(report)
    for mark, packet in packets:
        formatted_packet = packet.sprintf('%.time% %IP.src% -> %IP.dst% %TCP.flags%')
        print('[%s] %s' % (mark, formatted_packet))


class UdpPacketDropProbe(object):
    def __init__(self, src, sport, dst, dport, ttl, sniffer, one_packet_only=False):
        self.src = src
        self.sport = sport
        self.dst = dst
        self.dport = dport
        self.ttl = ttl
        self.sniffer = sniffer
        self.one_packet_only = one_packet_only
        self.report = {
            'ROUTER_IP_FOUND_BY_PACKET_1': None,
            'ROUTER_IP_FOUND_BY_PACKET_2': None,
            'ROUTER_IP_FOUND_BY_PACKET_3': None,
            'RESPONDED?': None,
            'PACKETS': []
        }
        self.udp_socket = None

    def poke(self):
        question = DNS(rd=1, qd=DNSQR(qname='www.gov.cn'))
        if self.sniffer:
            packet1 = IP(src=self.src, dst=self.dst, id=self.ttl * 10 + 1, ttl=self.ttl) / UDP(
                sport=self.sport, dport=self.dport) / question
            networking.send(packet1)
            self.report['PACKETS'].append(('PACKET_1', packet1))
            if not self.one_packet_only:
                packet2 = IP(src=self.src, dst=self.dst, id=self.ttl * 10 + 2, ttl=self.ttl) / UDP(
                    sport=self.sport, dport=self.dport) / question
                networking.send(packet2)
                self.report['PACKETS'].append(('PACKET_2', packet2))
                packet3 = IP(src=self.src, dst=self.dst, id=self.ttl * 10 + 3, ttl=self.ttl) / UDP(
                    sport=self.sport, dport=self.dport) / question
                networking.send(packet3)
                self.report['PACKETS'].append(('PACKET_3', packet3))
        else:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            atexit.register(self.udp_socket.close)
            self.udp_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, self.ttl)
            self.udp_socket.settimeout(0)
            self.udp_socket.bind((self.src, self.sport)) # if sport change the route going through might change
            self.udp_socket.sendto(str(question), (self.dst, self.dport))

    def close(self):
        if self.udp_socket:
            self.udp_socket.close()

    def peek(self):
        if not self.sniffer:
            try:
                self.udp_socket.recv(1024)
                self.report['RESPONDED?'] = True
            except socket.error as e:
                if ERROR_NO_DATA == e[0]:
                    pass
                else:
                    raise
            return self.report
        for packet in self.sniffer.packets:
            if UDP in packet:
                self.analyze_udp_packet(packet)
            elif IPerror in packet and UDPerror in packet:
                self.analyze_udp_error_packet(packet)
        return self.report

    def analyze_udp_packet(self, packet):
        if self.dport != packet[UDP].sport:
            return
        if self.sport != packet[UDP].dport:
            return
        self.report['RESPONDED?'] = True
        self.report['PACKETS'].append(('UNKNOWN', packet))

    def analyze_udp_error_packet(self, packet):
        if self.sport != packet[UDPerror].sport:
            return
        if self.dport != packet[UDPerror].dport:
            return
        self.report['RESPONDED?'] = True
        if self.ttl * 10 + 1 == packet[IPerror].id:
            self.record_router_ip(packet.src, 1, packet)
        elif self.ttl * 10 + 2 == packet[IPerror].id:
            self.record_router_ip(packet.src, 2, packet)
        elif self.ttl * 10 + 3 == packet[IPerror].id:
            self.record_router_ip(packet.src, 3, packet)
        else:
            self.report['PACKETS'].append(('UNKNOWN', packet))

    def record_router_ip(self, router_ip, packet_index, packet):
        if self.report['ROUTER_IP_FOUND_BY_PACKET_%s' % packet_index]:
            self.report['PACKETS'].append(('ADDITIONAL_ROUTER_IP_FOUND_BY_PACKET_%s' % packet_index, packet))
        else:
            self.report['PACKETS'].append(('ROUTER_IP_FOUND_BY_PACKET_%s' % packet_index, packet))
            self.report['ROUTER_IP_FOUND_BY_PACKET_%s' % packet_index] = router_ip

if '__main__' == __name__:
    if 1 == len(sys.argv):
        print('[Usage] ./udp_packet_drop_probe.py destination_ip sport ttl')
        sys.exit(3)
    else:
        main(*sys.argv[1:])
########NEW FILE########
