__FILENAME__ = china_ip
import socket
import struct
import math
import os
import logging

LOGGER = logging.getLogger(__name__)

def load_china_ip_ranges():
    with open(os.path.join(os.path.dirname(__file__), 'china_ip.txt')) as f:
        line = f.readline()
        while line:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                continue
            if 'CN|ipv4' not in line:
                continue
                # apnic|CN|ipv4|223.255.252.0|512|20110414|allocated
            _, _, _, start_ip, ip_count, _, _ = line.split('|')
            start_ip_as_int = ip_to_int(start_ip)
            end_ip_as_int = start_ip_as_int + int(ip_count)
            yield start_ip_as_int, end_ip_as_int
            line = f.readline()
    yield translate_ip_range('111.0.0.0', 10) # china mobile
    yield translate_ip_range('202.55.0.0', 19) # china telecom


def translate_ip_range(ip, netmask):
    return ip_to_int(ip), ip_to_int(ip) + int(math.pow(2, 32 - netmask))


def ip_to_int(ip):
    return struct.unpack('!i', socket.inet_aton(ip))[0]


CHINA_IP_RANGES = list(load_china_ip_ranges())

def is_china_ip(ip):
    ip_as_int = ip_to_int(ip)
    for start_ip_as_int, end_ip_as_int in CHINA_IP_RANGES:
        if start_ip_as_int <= ip_as_int <= end_ip_as_int:
            return True
    return False
########NEW FILE########
__FILENAME__ = config_file
import os
import json
from uuid import uuid4
import shutil
import logging

LOGGER = logging.getLogger(__name__)
DEFAULT_PUBLIC_SERVERS_SOURCE = 'proxies.dyn.fqrouter.com'

def DEFAULT_CONFIG():
    return {
        'config_file': None,
        'china_shortcut_enabled': True,
        'direct_access_enabled': True,
        'google_scrambler_enabled': True,
        'tcp_scrambler_enabled': True,
        'https_enforcer_enabled': True,
        'access_check_enabled': True,
        'hosted_domain_enabled': True,
        'prefers_private_proxy': False,
        'http_manager': {
            'enabled': True,
            'ip': '',
            'port': 2515
        },
        'http_gateway': {
            'enabled': False,
            'ip': '',
            'port': 2516
        },
        'dns_server': {
            'enabled': False,
            'ip': '',
            'port': 12345
        },
        'tcp_gateway': {
            'enabled': False,
            'ip': '',
            'port': 12345
        },
        'wifi_repeater': {
            'ssid': 'fqrouter',
            'password': '12345678'
        },
        'upnp': {
            'port': 25,
            'is_password_protected': False,
            'username': '',
            'password': ''
        },
        'public_servers': {
            'source': DEFAULT_PUBLIC_SERVERS_SOURCE,
            'goagent_enabled': True,
            'ss_enabled': True
        },
        'private_servers': {}
    }

cli_args = None


def read_config():
    config = _read_config()
    migrate_config(config)
    config['log_level'] = cli_args.log_level
    config['log_file'] = cli_args.log_file
    config['ip_command'] = cli_args.ip_command
    config['ifconfig_command'] = cli_args.ifconfig_command
    config['outbound_ip'] = cli_args.outbound_ip
    config['google_host'] = cli_args.google_host
    for props in cli_args.proxy:
        props = props.split(',')
        prop_dict = dict(p.split('=') for p in props[1:])
        n = int(prop_dict.pop('n', 0))
        add_proxy(config, props[0], n, **prop_dict)
    if cli_args.china_shortcut_enabled is not None:
        config['china_shortcut_enabled'] = cli_args.china_shortcut_enabled
    if cli_args.direct_access_enabled is not None:
        config['direct_access_enabled'] = cli_args.direct_access_enabled
    if cli_args.google_scrambler_enabled is not None:
        config['google_scrambler_enabled'] = cli_args.google_scrambler_enabled
    if cli_args.tcp_scrambler_enabled is not None:
        config['tcp_scrambler_enabled'] = cli_args.tcp_scrambler_enabled
    if cli_args.access_check_enabled is not None:
        config['access_check_enabled'] = cli_args.access_check_enabled
    if cli_args.no_http_manager:
        config['http_manager']['enabled'] = False
    if cli_args.http_manager_listen:
        config['http_manager']['enabled'] = True
        config['http_manager']['ip'], config['http_manager']['port'] = parse_ip_colon_port(cli_args.http_manager_listen)
    if cli_args.http_gateway_listen:
        config['http_gateway']['enabled'] = True
        config['http_gateway']['ip'], config['http_gateway']['port'] = parse_ip_colon_port(cli_args.http_gateway_listen)
    if cli_args.no_dns_server:
        config['dns_server']['enabled'] = False
    if cli_args.dns_server_listen:
        config['dns_server']['enabled'] = True
        config['dns_server']['ip'], config['dns_server']['port'] = parse_ip_colon_port(cli_args.dns_server_listen)
    if cli_args.tcp_gateway_listen:
        config['tcp_gateway']['enabled'] = True
        config['tcp_gateway']['ip'], config['tcp_gateway']['port'] = parse_ip_colon_port(cli_args.tcp_gateway_listen)
    return config


def add_proxy(config, proxy_type, n=0, **kwargs):
    if n:
        for i in range(1, 1 + n):
            private_server = {k: v.replace('#n#', str(i)) for k, v in kwargs.items()}
            private_server['proxy_type'] = proxy_type
            config['private_servers'][str(uuid4())] = private_server
    else:
        kwargs['proxy_type'] = proxy_type
        config['private_servers'][str(uuid4())] = kwargs


def _read_config():
    if not cli_args:
        return DEFAULT_CONFIG()
    config = DEFAULT_CONFIG()
    config['config_file'] = cli_args.config_file
    if os.path.exists(cli_args.config_file):
        with open(cli_args.config_file) as f:
            content = f.read()
            if content:
                config.update(json.loads(content))
            return config
    else:
        return config


def migrate_config(config):
    if 'proxies.fqrouter.com' == config['public_servers']['source']:
        config['public_servers']['source'] = DEFAULT_PUBLIC_SERVERS_SOURCE
    if not config['config_file']:
        return
    config_dir = os.path.dirname(config['config_file'])
    migrate_goagent_config(config, config_dir)
    migrate_shadowsocks_config(config, config_dir)
    migrate_http_proxy_config(config, config_dir)
    migrate_ssh_config(config, config_dir)


def migrate_goagent_config(config, config_dir):
    goagent_json_file = os.path.join(config_dir, 'goagent.json')
    if os.path.exists(goagent_json_file):
        try:
            with open(goagent_json_file) as f:
                for server in json.loads(f.read()):
                    add_proxy(config, 'GoAgent', path=server['path'],
                              goagent_password=server['password'], appid=server['appid'])
            with open(cli_args.config_file, 'w') as f:
                f.write(json.dumps(config))
        except:
            LOGGER.exception('failed to migrate goagent config')
        finally:
            shutil.move(goagent_json_file, os.path.join(config_dir, 'goagent.json.bak'))


def migrate_shadowsocks_config(config, config_dir):
    shadowsocks_json_file = os.path.join(config_dir, 'shadowsocks.json')
    if os.path.exists(shadowsocks_json_file):
        try:
            with open(shadowsocks_json_file) as f:
                for server in json.loads(f.read()):
                    add_proxy(config, 'Shadowsocks', host=server['host'],
                              password=server['password'], port=server['port'],
                              encrypt_method=server['encryption_method'])
            with open(cli_args.config_file, 'w') as f:
                f.write(json.dumps(config))
        except:
            LOGGER.exception('failed to migrate shadowsocks config')
        finally:
            shutil.move(shadowsocks_json_file, os.path.join(config_dir, 'shadowsocks.json.bak'))


def migrate_http_proxy_config(config, config_dir):
    http_proxy_json_file = os.path.join(config_dir, 'http-proxy.json')
    if os.path.exists(http_proxy_json_file):
        try:
            with open(http_proxy_json_file) as f:
                for server in json.loads(f.read()):
                    if 'spdy (webvpn)' == server['transport_type']:
                        add_proxy(config, 'SPDY', host=server['host'],
                                  password=server['password'], port=server['port'],
                                  username=server['username'],
                                  traffic_type=server['traffic_type'].upper().replace(' ', ''),
                                  connections_count=server['spdy_connections_count'])
                    else:
                        add_proxy(config, 'HTTP', host=server['host'],
                                  password=server['password'], port=server['port'],
                                  username=server['username'],
                                  transport_type='SSL' if 'ssl' == server['transport_type'] else 'HTTP',
                                  traffic_type=server['traffic_type'].upper().replace(' ', ''))
            with open(cli_args.config_file, 'w') as f:
                f.write(json.dumps(config))
        except:
            LOGGER.exception('failed to migrate http proxy config')
        finally:
            shutil.move(http_proxy_json_file, os.path.join(config_dir, 'http-proxy.json.bak'))


def migrate_ssh_config(config, config_dir):
    ssh_json_file = os.path.join(config_dir, 'ssh.json')
    if os.path.exists(ssh_json_file):
        try:
            with open(ssh_json_file) as f:
                for server in json.loads(f.read()):
                    add_proxy(config, 'SSH', host=server['host'],
                              password=server['password'], port=server['port'],
                              username=server['username'], connections_count=server['connections_count'])
            with open(cli_args.config_file, 'w') as f:
                f.write(json.dumps(config))
        except:
            LOGGER.exception('failed to migrate ssh config')
        finally:
            shutil.move(ssh_json_file, os.path.join(config_dir, 'ssh.json.bak'))


def update_config(apply=None, **kwargs):
    if not cli_args:
        return
    config = _read_config()
    config.update(kwargs)
    if apply:
        apply(config)
    with open(cli_args.config_file, 'w') as f:
        f.write(json.dumps(config))


def parse_ip_colon_port(ip_colon_port):
    if not isinstance(ip_colon_port, basestring):
        return ip_colon_port
    if ':' in ip_colon_port:
        server_ip, server_port = ip_colon_port.split(':')
        server_port = int(server_port)
    else:
        server_ip = ip_colon_port
        server_port = 53
    return '' if '*' == server_ip else server_ip, server_port
########NEW FILE########
__FILENAME__ = fqsocks
#!/usr/bin/env python
# thanks @phuslu https://github.com/phus/sniproxy/blob/master/sniproxy.py
# thanks @ofmax https://github.com/madeye/gaeproxy/blob/master/assets/modules/python.mp3
import logging
import logging.handlers
import sys
import argparse
import httplib
import fqlan
import fqdns

import gevent.server
import gevent.monkey

from .proxies.goagent import GoAgentProxy
import httpd
import networking
from .gateways import proxy_client
from .gateways import tcp_gateway
from .gateways import http_gateway
from .pages import lan_device
from .pages import upstream
from . import config_file


__import__('fqsocks.pages')
LOGGER = logging.getLogger(__name__)

dns_pollution_ignored = False
networking.DNS_HANDLER = fqdns.DnsHandler()
reset_force_us_ip_greenlet = None

@httpd.http_handler('GET', 'dns-polluted-at')
def get_dns_polluted_at(environ, start_response):
    global dns_pollution_ignored
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    if not dns_pollution_ignored and proxy_client.dns_polluted_at > 0:
        dns_pollution_ignored = True
        yield str(proxy_client.dns_polluted_at)
    else:
        yield '0'


@httpd.http_handler('POST', 'force-us-ip')
def handle_force_us_ip(environ, start_response):
    global reset_force_us_ip_greenlet
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    if reset_force_us_ip_greenlet is not None:
        reset_force_us_ip_greenlet.kill()
    reset_force_us_ip_greenlet = gevent.spawn(reset_force_us_ip)
    LOGGER.info('force_us_ip set to True')
    proxy_client.force_us_ip = True
    yield 'OK'


def reset_force_us_ip():
    global reset_force_us_ip_greenlet
    gevent.sleep(30)
    reset_force_us_ip_greenlet = None
    LOGGER.info('force_us_ip reset to False')
    proxy_client.force_us_ip = False



@httpd.http_handler('POST', 'clear-states')
def handle_clear_states(environ, start_response):
    proxy_client.clear_proxy_states()
    http_gateway.dns_cache = {}
    networking.default_interface_ip_cache = None
    lan_device.lan_devices = {}
    if lan_device.forge_greenlet is not None:
        lan_device.forge_greenlet.kill()
    LOGGER.info('cleared states upon request')
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    yield 'OK'


def setup_logging(log_level, log_file=None):
    logging.basicConfig(
        stream=sys.stdout, level=log_level, format='%(asctime)s %(levelname)s %(message)s')
    if log_file:
        handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=1024 * 512, backupCount=1)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        handler.setLevel(log_level)
        logging.getLogger('fqsocks').setLevel(log_level)
        logging.getLogger('fqsocks').addHandler(handler)


def init_config(argv):
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('--tcp-gateway-listen')
    argument_parser.add_argument('--http-gateway-listen')
    argument_parser.add_argument('--dns-server-listen')
    argument_parser.add_argument('--no-dns-server', action='store_true')
    argument_parser.add_argument('--http-manager-listen')
    argument_parser.add_argument('--no-http-manager', action='store_true')
    argument_parser.add_argument('--outbound-ip')
    argument_parser.add_argument('--ip-command')
    argument_parser.add_argument('--ifconfig-command')
    argument_parser.add_argument('--config-file')
    argument_parser.add_argument('--log-level', default='INFO')
    argument_parser.add_argument('--log-file')
    argument_parser.add_argument('--proxy', action='append', default=[], help='for example --proxy goagent,appid=abcd')
    argument_parser.add_argument('--google-host', action='append', default=[])
    argument_parser.add_argument('--access-check', dest='access_check_enabled', action='store_true')
    argument_parser.add_argument('--no-access-check', dest='access_check_enabled', action='store_false')
    argument_parser.set_defaults(access_check_enabled=None)
    argument_parser.add_argument('--direct-access', dest='direct_access_enabled', action='store_true')
    argument_parser.add_argument('--no-direct-access', dest='direct_access_enabled', action='store_false')
    argument_parser.set_defaults(direct_access_enabled=None)
    argument_parser.add_argument('--china-shortcut', dest='china_shortcut_enabled', action='store_true')
    argument_parser.add_argument('--no-china-shortcut', dest='china_shortcut_enabled', action='store_false')
    argument_parser.set_defaults(china_shortcut_enabled=None)
    argument_parser.add_argument('--tcp-scrambler', dest='tcp_scrambler_enabled', action='store_true')
    argument_parser.add_argument('--no-tcp-scrambler', dest='tcp_scrambler_enabled', action='store_false')
    argument_parser.set_defaults(tcp_scrambler_enabled=None)
    argument_parser.add_argument('--google-scrambler', dest='google_scrambler_enabled', action='store_true')
    argument_parser.add_argument('--no-google-scrambler', dest='google_scrambler_enabled', action='store_false')
    argument_parser.set_defaults(google_scrambler_enabled=None)
    args = argument_parser.parse_args(argv)
    config_file.cli_args = args
    config = config_file.read_config()
    log_level = getattr(logging, config['log_level'])
    setup_logging(log_level, config['log_file'])
    LOGGER.info('config: %s' % config)
    if config['ip_command']:
        fqlan.IP_COMMAND = config['ip_command']
    if config['ifconfig_command']:
        fqlan.IFCONFIG_COMMAND = config['ifconfig_command']
    networking.OUTBOUND_IP = config['outbound_ip']
    fqdns.OUTBOUND_IP = config['outbound_ip']
    if config['google_host']:
        GoAgentProxy.GOOGLE_HOSTS = config['google_host']
    proxy_client.china_shortcut_enabled = config['china_shortcut_enabled']
    proxy_client.direct_access_enabled = config['direct_access_enabled']
    proxy_client.tcp_scrambler_enabled = config['tcp_scrambler_enabled']
    proxy_client.google_scrambler_enabled = config['google_scrambler_enabled']
    proxy_client.https_enforcer_enabled = config['https_enforcer_enabled']
    proxy_client.goagent_public_servers_enabled = config['public_servers']['goagent_enabled']
    proxy_client.ss_public_servers_enabled = config['public_servers']['ss_enabled']
    proxy_client.prefers_private_proxy = config['prefers_private_proxy']
    networking.DNS_HANDLER.enable_hosted_domain = config['hosted_domain_enabled']
    http_gateway.LISTEN_IP, http_gateway.LISTEN_PORT = config['http_gateway']['ip'], config['http_gateway']['port']
    tcp_gateway.LISTEN_IP, tcp_gateway.LISTEN_PORT = config['tcp_gateway']['ip'], config['tcp_gateway']['port']
    httpd.LISTEN_IP, httpd.LISTEN_PORT = config['http_manager']['ip'], config['http_manager']['port']

def main(argv=None):
    if argv:
        init_config(argv)
    config = config_file.read_config()
    gevent.monkey.patch_all(ssl=False, thread=True)
    try:
        gevent.monkey.patch_ssl()
    except:
        LOGGER.exception('failed to patch ssl')
    greenlets = []
    if config['dns_server']['enabled']:
        dns_server_address = (config['dns_server']['ip'], config['dns_server']['port'])
        dns_server = fqdns.HandlerDatagramServer(dns_server_address, networking.DNS_HANDLER)
        greenlets.append(gevent.spawn(dns_server.serve_forever))
    if config['http_gateway']['enabled']:
        http_gateway.server_greenlet = gevent.spawn(http_gateway.serve_forever)
        greenlets.append(http_gateway.server_greenlet)
    if config['tcp_gateway']['enabled']:
        tcp_gateway.server_greenlet = gevent.spawn(tcp_gateway.serve_forever)
        greenlets.append(tcp_gateway.server_greenlet)
    if config['http_manager']['enabled']:
        httpd.server_greenlet = gevent.spawn(httpd.serve_forever)
        greenlets.append(httpd.server_greenlet)
    greenlets.append(gevent.spawn(proxy_client.init_proxies, config))
    for greenlet in greenlets:
        try:
            greenlet.join()
        except KeyboardInterrupt:
            return
        except:
            LOGGER.exception('greenlet join failed')
            return


# TODO add socks4 proxy
# TODO add socks5 proxy
# TODO === future ===
# TODO add vpn as proxy (setup vpn, mark packet, mark based routing)

if '__main__' == __name__:
    main(sys.argv[1:])
########NEW FILE########
__FILENAME__ = http_gateway
import logging
import urlparse
import httplib
import os
import base64

import gevent.server
import jinja2

from .. import networking
from .proxy_client import ProxyClient
from .proxy_client import handle_client
from ..proxies.http_try import recv_till_double_newline
from ..proxies.http_try import parse_request
from ..proxies.http_try import is_no_direct_host
from .. import config_file
from .. import httpd
from .. import lan_ip


LOGGER = logging.getLogger(__name__)
WHITELIST_PAC_FILE = os.path.join(os.path.dirname(__file__), '..', 'templates', 'whitelist.pac')
dns_cache = {}
LISTEN_IP = None
LISTEN_PORT = None
UPNP_PORT = None
UPNP_AUTH = None
UPNP_AUTH_NONE = 'NONE'
server_greenlet = None
external_ip_address = None


@httpd.http_handler('GET', 'pac')
def pac_page(environ, start_response):
    with open(WHITELIST_PAC_FILE) as f:
        template = jinja2.Template(unicode(f.read(), 'utf8'))
    ip = networking.get_default_interface_ip()
    start_response(httplib.OK, [('Content-Type', 'application/x-ns-proxy-autoconfig')])
    return [template.render(http_gateway='%s:%s' % (ip, LISTEN_PORT)).encode('utf8')]


def handle(downstream_sock, address):
    src_ip, src_port = address
    request, payload = recv_till_double_newline('', downstream_sock)
    if not request:
        return
    method, path, headers = parse_request(request)
    if 'GET' == method.upper() and '/' == path and is_http_gateway_host(headers.get('Host')):
        with open(WHITELIST_PAC_FILE) as f:
            template = jinja2.Template(unicode(f.read(), 'utf8'))
        downstream_sock.sendall(
            'HTTP/1.1 200 OK\r\n\r\n%s' % template.render(http_gateway=headers.get('Host')).encode('utf8'))
        return
    if lan_ip.is_lan_ip(src_ip):
        authorized = True
    elif UPNP_AUTH_NONE == get_upnp_auth():
        authorized = True
    else:
        authorized = get_upnp_auth() == headers.get('Proxy-Authorization')
    if not authorized:
        downstream_sock.sendall(
"""HTTP/1.1 407 Proxy authentication required
Connection: close
Content-Type: text/html
Content-Length: 0
Proxy-Authenticate: Basic realm="fqrouter"

""")
        return
    if 'CONNECT' == method.upper():
        if ':' in path:
            dst_host, dst_port = path.split(':')
            dst_port = int(dst_port)
        else:
            dst_host = path
            dst_port = 443
        dst_ip = resolve_ip(dst_host)
        if not dst_ip:
            return
        if lan_ip.is_lan_ip(dst_ip):
            return
        downstream_sock.sendall('HTTP/1.1 200 OK\r\n\r\n')
        client = ProxyClient(downstream_sock, src_ip, src_port, dst_ip, dst_port)
        client.us_ip_only = is_no_direct_host(dst_host)
        handle_client(client)
    else:
        dst_host = urlparse.urlparse(path)[1]
        if ':' in dst_host:
            dst_host, dst_port = dst_host.split(':')
            dst_port = int(dst_port)
        else:
            dst_port = 80
        dst_ip = resolve_ip(dst_host)
        if not dst_ip:
            return
        if lan_ip.is_lan_ip(dst_ip):
            return
        client = ProxyClient(downstream_sock, src_ip, src_port, dst_ip, dst_port)
        client.us_ip_only = is_no_direct_host(dst_host)
        request_lines = ['%s %s HTTP/1.1\r\n' % (method, path[path.find(dst_host) + len(dst_host):])]
        headers.pop('Proxy-Connection', None)
        headers['Host'] = dst_host
        headers['Connection'] = 'close'
        for key, value in headers.items():
            request_lines.append('%s: %s\r\n' % (key, value))
        request = ''.join(request_lines)
        client.peeked_data = request + '\r\n' + payload
        handle_client(client)


def is_http_gateway_host(host):
    if '127.0.0.1:%s' % LISTEN_PORT == host:
        return True
    if '%s:%s' % (networking.get_default_interface_ip(), LISTEN_PORT) == host:
        return True
    if external_ip_address and '%s:%s' % (external_ip_address, get_upnp_port()) == host:
        return True
    return False


def get_upnp_auth():
    global UPNP_AUTH
    if not UPNP_AUTH:
        upnp_config = config_file.read_config()['upnp']
        if upnp_config['is_password_protected']:
            UPNP_AUTH = base64.b64encode('%s:%s' % (upnp_config['username'], upnp_config['password'])).strip()
            UPNP_AUTH = 'Basic %s' % UPNP_AUTH
        else:
            UPNP_AUTH = UPNP_AUTH_NONE
    return UPNP_AUTH


def get_upnp_port():
    global UPNP_PORT

    if UPNP_PORT:
        return UPNP_PORT
    UPNP_PORT = config_file.read_config()['upnp']['port']
    return UPNP_PORT


def resolve_ip(host):
    if host in dns_cache:
        return dns_cache[host]
    ips = networking.resolve_ips(host)
    if ips:
        ip = ips[0]
    else:
        ip = None
    dns_cache[host] = ip
    return dns_cache[host]


def serve_forever():
    server = gevent.server.StreamServer((LISTEN_IP, LISTEN_PORT), handle)
    LOGGER.info('started fqsocks http gateway at %s:%s' % (LISTEN_IP, LISTEN_PORT))
    try:
        server.serve_forever()
    except:
        LOGGER.exception('failed to start http gateway')
    finally:
        LOGGER.info('http gateway stopped')


########NEW FILE########
__FILENAME__ = proxy_client
import logging
import sys
import socket
import errno
import select
import random
import re
import math
import traceback
import time
import contextlib
import fqdns
import ssl
import urlparse
import gevent
import dpkt
from .. import networking
from .. import stat
from ..proxies.http_try import recv_and_parse_request
from ..proxies.http_try import NotHttp
from ..proxies.http_try import HTTP_TRY_PROXY
from ..proxies.http_try import TCP_SCRAMBLER
from ..proxies.google_http_try import GOOGLE_SCRAMBLER
from ..proxies.google_http_try import HTTPS_ENFORCER
from ..proxies.tcp_smuggler import TCP_SMUGGLER
from ..proxies.http_relay import HttpRelayProxy
from ..proxies.http_connect import HttpConnectProxy
from ..proxies import direct
from ..proxies.goagent import GoAgentProxy
from ..proxies.dynamic import DynamicProxy
from ..proxies.dynamic import proxy_types
from ..proxies.shadowsocks import ShadowSocksProxy
from ..proxies.ssh import SshProxy
from .. import us_ip
from .. import lan_ip
from .. import china_ip
from ..proxies.direct import DIRECT_PROXY
from ..proxies.direct import NONE_PROXY
from ..proxies.https_try import HTTPS_TRY_PROXY
from .. import ip_substitution
from .. import config_file
import os.path

TLS1_1_VERSION = 0x0302
RE_HTTP_HOST = re.compile('Host: (.+)\r\n')
LOGGER = logging.getLogger(__name__)

proxies = []
dns_polluted_at = 0
china_shortcut_enabled = True
direct_access_enabled = True
tcp_scrambler_enabled = True
google_scrambler_enabled = True
prefers_private_proxy = False
https_enforcer_enabled = True
goagent_public_servers_enabled = True
ss_public_servers_enabled = True
last_refresh_started_at = -1
refresh_timestamps = []
goagent_group_exhausted = False
force_us_ip = False
on_clear_states = None


class ProxyClient(object):
    def __init__(self, downstream_sock, src_ip, src_port, dst_ip, dst_port):
        super(ProxyClient, self).__init__()
        self.downstream_sock = downstream_sock
        self.downstream_rfile = downstream_sock.makefile('rb', 8192)
        self.downstream_wfile = downstream_sock.makefile('wb', 0)
        self.forward_started = False
        self.resources = [self.downstream_sock, self.downstream_rfile, self.downstream_wfile]
        self.src_ip = src_ip
        self.src_port = src_port
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.peeked_data = ''
        self.host = ''
        self.protocol = None
        self.tried_proxies = {}
        self.forwarding_by = None
        self.us_ip_only = force_us_ip
        self.delayed_penalties = []
        self.ip_substituted = False

    def create_tcp_socket(self, server_ip, server_port, connect_timeout):
        upstream_sock = networking.create_tcp_socket(server_ip, server_port, connect_timeout)
        upstream_sock.counter = stat.opened(upstream_sock, self.forwarding_by, self.host, self.dst_ip)
        self.resources.append(upstream_sock)
        self.resources.append(upstream_sock.counter)
        return upstream_sock

    def add_resource(self, res):
        self.resources.append(res)

    def forward(self, upstream_sock, timeout=7, after_started_timeout=360, encrypt=None, decrypt=None,
                delayed_penalty=None, on_forward_started=None):

        if self.forward_started:
            if 5228 == self.dst_port: # Google Service
                upstream_sock.settimeout(None)
            else: # More than 5 minutes
                upstream_sock.settimeout(after_started_timeout)
        else:
            upstream_sock.settimeout(timeout)
        self.downstream_sock.settimeout(None)

        def from_upstream_to_downstream():
            try:
                while True:
                    data = upstream_sock.recv(262144)
                    upstream_sock.counter.received(len(data))
                    if data:
                        if not self.forward_started:
                            self.forward_started = True
                            if 5228 == self.dst_port: # Google Service
                                upstream_sock.settimeout(None)
                            else: # More than 5 minutes
                                upstream_sock.settimeout(after_started_timeout)
                            self.apply_delayed_penalties()
                            if on_forward_started:
                                on_forward_started()
                        if decrypt:
                            data = decrypt(data)
                        self.downstream_sock.sendall(data)
                    else:
                        return
            except socket.error:
                return
            except gevent.GreenletExit:
                return
            except:
                LOGGER.exception('forward u2d failed')
                return sys.exc_info()[1]

        def from_downstream_to_upstream():
            try:
                while True:
                    data = self.downstream_sock.recv(262144)
                    if data:
                        if encrypt:
                            data = encrypt(data)
                        upstream_sock.counter.sending(len(data))
                        upstream_sock.sendall(data)
                    else:
                        return
            except socket.error:
                return
            except gevent.GreenletExit:
                return
            except:
                LOGGER.exception('forward d2u failed')
                return sys.exc_info()[1]
            finally:
                upstream_sock.close()

        u2d = gevent.spawn(from_upstream_to_downstream)
        d2u = gevent.spawn(from_downstream_to_upstream)
        try:
            for greenlet in gevent.iwait([u2d, d2u]):
                e = greenlet.get()
                if e:
                    raise e
                break
            try:
                upstream_sock.close()
            except:
                pass
            if not self.forward_started:
                self.fall_back(reason='forward does not receive any response', delayed_penalty=delayed_penalty)
        finally:
            try:
                u2d.kill()
            except:
                pass
            try:
                d2u.kill()
            except:
                pass

    def apply_delayed_penalties(self):
        if self.delayed_penalties:
            LOGGER.info('[%s] apply delayed penalties' % repr(self))
        for delayed_penalty in self.delayed_penalties:
            try:
                delayed_penalty()
            except:
                LOGGER.exception('failed to apply delayed penalty: %s' % delayed_penalty)


    def close(self):
        for res in self.resources:
            try:
                res.close()
            except:
                pass

    def fall_back(self, reason, delayed_penalty=None, silently=False):
        if self.forward_started:
            LOGGER.fatal('[%s] fall back can not happen after forward started:\n%s' %
                         (repr(self), traceback.format_stack()))
            raise Exception('!!! fall back can not happen after forward started !!!')
        if delayed_penalty:
            self.delayed_penalties.append(delayed_penalty)
        raise ProxyFallBack(reason, silently=silently)

    def dump_proxies(self):
        LOGGER.info('dump proxies: %s' % [p for p in proxies if not p.died])

    def has_tried(self, proxy):
        if proxy in self.tried_proxies:
            return True
        if isinstance(proxy, DynamicProxy):
            proxy = proxy.delegated_to
        if self.us_ip_only:
            if hasattr(proxy, 'proxy_ip') and not us_ip.is_us_ip(proxy.proxy_ip):
                LOGGER.info('skip %s' % proxy.proxy_ip)
                return True
        return proxy in self.tried_proxies

    def __repr__(self):
        description = '%s:%s => %s:%s' % (self.src_ip, self.src_port, self.dst_ip, self.dst_port)
        if self.host:
            description = '%s %s' % (description, self.host)
        if self.forwarding_by:
            description = '%s %s' % (description, repr(self.forwarding_by))
        return description


class ProxyFallBack(Exception):
    def __init__(self, reason, silently):
        super(ProxyFallBack, self).__init__(reason)
        self.reason = reason
        self.silently = silently


ProxyClient.ProxyFallBack = ProxyFallBack


def handle_client(client):
    if goagent_group_exhausted:
        gevent.spawn(load_more_goagent_proxies)
    try:
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug('[%s] downstream connected' % repr(client))
        pick_proxy_and_forward(client)
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug('[%s] done' % repr(client))
    except NoMoreProxy:
        if HTTP_TRY_PROXY.host_slow_detection_enabled and client.host in HTTP_TRY_PROXY.host_slow_list:
            LOGGER.critical('!!! disable host slow detection !!!')
            HTTP_TRY_PROXY.host_slow_list.clear()
            HTTP_TRY_PROXY.host_slow_detection_enabled = False
        return
    except:
        err_msg = str(sys.exc_info()[1])
        if 'ascii' in err_msg or LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.exception('[%s] done with error' % repr(client))
        else:
            LOGGER.info('[%s] done with error: %s' % (repr(client), err_msg))
    finally:
        client.close()


def pick_proxy_and_forward(client):
    global dns_polluted_at
    if lan_ip.is_lan_ip(client.dst_ip):
        try:
            DIRECT_PROXY.forward(client)
        except ProxyFallBack:
            pass
        return
    if client.dst_ip in fqdns.WRONG_ANSWERS:
        LOGGER.error('[%s] destination is GFW wrong answer' % repr(client))
        dns_polluted_at = time.time()
        NONE_PROXY.forward(client)
        return
    if china_shortcut_enabled and is_china_dst(client):
        try:
            DIRECT_PROXY.forward(client)
        except ProxyFallBack:
            pass
        return
    peek_data(client)
    for i in range(3):
        try:
            proxy = pick_proxy(client)
        except NotHttp:
            return # give up
        if not proxy:
            raise NoMoreProxy()
        if 'DIRECT' in proxy.flags:
            LOGGER.debug('[%s] picked proxy: %s' % (repr(client), repr(proxy)))
        else:
            LOGGER.info('[%s] picked proxy: %s' % (repr(client), repr(proxy)))
        try:
            proxy.forward(client)
            return
        except ProxyFallBack as e:
            if not e.silently:
                LOGGER.error('[%s] fall back to other proxy due to %s: %s' % (repr(client), e.reason, repr(proxy)))
            client.tried_proxies[proxy] = e.reason
        except NotHttp:
            return # give up
    raise NoMoreProxy()


def is_china_dst(client):
    if china_ip.is_china_ip(client.dst_ip):
        return True
    if client.host and fqdns.is_china_domain(client.host):
        return True
    return False


def peek_data(client):
    if not client.peeked_data:
        ins, _, errors = select.select([client.downstream_sock], [], [client.downstream_sock], 0.1)
        if errors:
            LOGGER.error('[%s] peek data failed' % repr(client))
            return DIRECT_PROXY
        if not ins:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('[%s] peek data timed out' % repr(client))
        else:
            client.peeked_data = client.downstream_sock.recv(8192)
    protocol, domain = analyze_protocol(client.peeked_data)
    if LOGGER.isEnabledFor(logging.DEBUG):
        LOGGER.debug('[%s] analyzed traffic: %s %s' % (repr(client), protocol, domain))
    client.host = domain
    client.protocol = protocol
    if 'UNKNOWN' == client.protocol:
        if client.dst_port == 80:
            client.protocol = 'HTTP'
        elif client.dst_port == 443:
            client.protocol = 'HTTPS'


class NoMoreProxy(Exception):
    pass


def on_proxy_died(proxy):
    if isinstance(proxy, DynamicProxy):
        proxy = proxy.delegated_to
    else:
        return
    if isinstance(proxy, GoAgentProxy):
        gevent.spawn(load_more_goagent_proxies)
    else:
        gevent.spawn(refresh_proxies)
direct.on_proxy_died = on_proxy_died


def load_more_goagent_proxies():
    global goagent_group_exhausted
    global last_refresh_started_at
    if time.time() - last_refresh_started_at < get_refresh_interval():
        LOGGER.error('skip load more goagent proxies after last attempt %s seconds' % (time.time() - last_refresh_started_at))
        return
    last_refresh_started_at = time.time()
    goagent_groups = {}
    for proxy in proxies:
        if proxy.died:
            continue
        if isinstance(proxy, DynamicProxy):
            proxy = proxy.delegated_to
        else:
            continue
        if isinstance(proxy, GoAgentProxy):
            proxy.query_version()
            if proxy.died:
                continue
            goagent_groups.setdefault(proxy.group, set()).add(proxy.appid)
    if goagent_group_exhausted:
        goagent_groups.setdefault(goagent_group_exhausted, set())
    for group, appids in goagent_groups.items():
        LOGGER.critical('current %s appids count: %s' % (group, len(appids)))
        if len(appids) < 3:
            goagent_group_exhausted = group
            config = config_file.read_config()
            if len(proxies) < 50:
                load_public_proxies({
                    'source': config['public_servers']['source'],
                    'goagent_enabled': True
                })
            refresh_proxies(force=True)
            return
    goagent_group_exhausted = False


def pick_proxy(client):
    picks_public = None
    if not direct_access_enabled:
        picks_public = False
    if not china_shortcut_enabled:
        picks_public = False
    if client.protocol == 'HTTP':
        return pick_preferred_private_proxy(client) or \
               pick_http_try_proxy(client) or \
               pick_tcp_smuggler(client) or \
               pick_proxy_supports(client, picks_public)
    elif client.protocol == 'HTTPS':
        return pick_preferred_private_proxy(client) or \
               pick_https_try_proxy(client) or \
               pick_proxy_supports(client, picks_public)
    else:
        return pick_preferred_private_proxy(client) or DIRECT_PROXY


def pick_preferred_private_proxy(client):
    if prefers_private_proxy:
        return pick_proxy_supports(client, picks_public=False)
    else:
        return None


def analyze_protocol(peeked_data):
    try:
        match = RE_HTTP_HOST.search(peeked_data)
        if match:
            return 'HTTP', match.group(1).strip()
        try:
            ssl3 = dpkt.ssl.SSL3(peeked_data)
        except dpkt.NeedData:
            return 'UNKNOWN', ''
        if ssl3.version in (dpkt.ssl.SSL3_VERSION, dpkt.ssl.TLS1_VERSION, TLS1_1_VERSION):
            return 'HTTPS', parse_sni_domain(peeked_data).strip()
    except:
        LOGGER.exception('failed to analyze protocol')
    return 'UNKNOWN', ''


def parse_sni_domain(data):
    domain = ''
    try:
        # extrace SNI from ClientHello packet, quick and dirty.
        domain = (m.group(2) for m in re.finditer('\x00\x00(.)([\\w\\.]{4,255})', data)
                  if ord(m.group(1)) == len(m.group(2))).next()
    except StopIteration:
        pass
    return domain


def pick_direct_proxy(client):
    return None if DIRECT_PROXY in client.tried_proxies else DIRECT_PROXY


def pick_http_try_proxy(client):
    if getattr(client, 'http_proxy_tried', False):
        return None
    try:
        if client.us_ip_only:
            return None
        if not direct_access_enabled:
            return None
        if not hasattr(client, 'is_payload_complete'): # only parse it once
            client.is_payload_complete = recv_and_parse_request(client)
        if tcp_scrambler_enabled and \
                not TCP_SMUGGLER.is_protocol_supported('HTTP', client) and \
                TCP_SCRAMBLER.is_protocol_supported('HTTP', client):
            return TCP_SCRAMBLER
        if https_enforcer_enabled and HTTPS_ENFORCER.is_protocol_supported('HTTP', client):
            return HTTPS_ENFORCER
        if google_scrambler_enabled and GOOGLE_SCRAMBLER.is_protocol_supported('HTTP', client):
            return GOOGLE_SCRAMBLER
        return HTTP_TRY_PROXY if HTTP_TRY_PROXY.is_protocol_supported('HTTP', client) else None
    finally:
        # one shot
        client.http_proxy_tried = True


def pick_tcp_smuggler(client):
    if not hasattr(client, 'is_payload_complete'): # only parse it once
        client.is_payload_complete = recv_and_parse_request(client)
    if tcp_scrambler_enabled and TCP_SMUGGLER.is_protocol_supported('HTTP', client):
        return TCP_SMUGGLER
    return None


def pick_https_try_proxy(client):
    if client.us_ip_only:
        client.tried_proxies[HTTPS_TRY_PROXY] = 'us ip only'
        return None
    if not direct_access_enabled:
        client.tried_proxies[HTTPS_TRY_PROXY] = 'direct access disabled'
        return None
    return HTTPS_TRY_PROXY if HTTPS_TRY_PROXY.is_protocol_supported('HTTPS', client) else None


def pick_proxy_supports(client, picks_public=None):
    supported_proxies = [proxy for proxy in proxies if should_pick(proxy, client, picks_public)]
    if not supported_proxies:
        if False is not picks_public and (goagent_public_servers_enabled or ss_public_servers_enabled):
            gevent.spawn(refresh_proxies)
        return None
    prioritized_proxies = {}
    for proxy in supported_proxies:
        prioritized_proxies.setdefault(proxy.priority, []).append(proxy)
    highest_priority = sorted(prioritized_proxies.keys())[0]
    picked_proxy = random.choice(sorted(prioritized_proxies[highest_priority], key=lambda proxy: proxy.latency)[:3])
    if picked_proxy.latency == 0:
        return random.choice(prioritized_proxies[highest_priority])
    return picked_proxy


def should_pick(proxy, client, picks_public):
    if proxy.died:
        return False
    if client.has_tried(proxy):
        return False
    if not proxy.is_protocol_supported(client.protocol, client):
        return False
    if not china_shortcut_enabled and isinstance(proxy, DynamicProxy):
        return False
    if picks_public is not None:
        is_public = isinstance(proxy, DynamicProxy)
        return is_public == picks_public
    else:
        return True


def refresh_proxies(force=False):
    global proxies
    global last_refresh_started_at
    if not force:
        if last_refresh_started_at == -1: # wait for proxy directories to load
            LOGGER.error('skip refreshing proxy because proxy directories not loaded yet')
            return False
        if time.time() - last_refresh_started_at < get_refresh_interval():
            LOGGER.error('skip refreshing proxy after last attempt %s seconds' % (time.time() - last_refresh_started_at))
            return False
    last_refresh_started_at = time.time()
    refresh_timestamps.append(time.time())
    LOGGER.info('refresh proxies: %s' % proxies)
    socks = []
    type_to_proxies = {}
    for proxy in proxies:
        type_to_proxies.setdefault(proxy.__class__, []).append(proxy)
    success = True
    for proxy_type, instances in type_to_proxies.items():
        try:
            success = success and proxy_type.refresh(instances)
        except:
            LOGGER.exception('failed to refresh proxies %s' % instances)
            success = False
    for sock in socks:
        try:
            sock.close()
        except:
            pass
    LOGGER.info('%s, refreshed proxies: %s' % (success, proxies))
    return success


def get_refresh_interval():
    if not refresh_timestamps:
        return 60
    while refresh_timestamps:
        if refresh_timestamps[0] < (time.time() - 10 * 60):
            refresh_timestamps.remove(refresh_timestamps[0])
        else:
            break
    return len(refresh_timestamps) * 30 + 60


def init_private_proxies(config):
    for proxy_id, private_server in config['private_servers'].items():
        try:
            proxy_type = private_server.pop('proxy_type')
            if 'GoAgent' == proxy_type:
                for appid in private_server['appid'].split('|'):
                    if not appid.strip():
                        continue
                    is_rc4_enabled = False
                    is_obfuscate_enabled = False
                    if 'rc4_obfuscate' == private_server.get('goagent_options'):
                        is_rc4_enabled = True
                        is_obfuscate_enabled = True
                    elif 'rc4' == private_server.get('goagent_options'):
                        is_rc4_enabled = True
                        is_obfuscate_enabled = False
                    elif 'obfuscate' == private_server.get('goagent_options'):
                        is_rc4_enabled = False
                        is_obfuscate_enabled = True
                    proxy = GoAgentProxy(
                        appid.strip(), private_server.get('path'),
                        private_server.get('goagent_password'),
                        is_rc4_enabled=is_rc4_enabled,
                        is_obfuscate_enabled=is_obfuscate_enabled)
                    proxy.proxy_id = proxy_id
                    proxies.append(proxy)
            elif 'SSH' == proxy_type:
                for i in range(private_server.get('connections_count') or 4):
                    proxy = SshProxy(
                        private_server['host'], private_server['port'],
                        private_server['username'], private_server.get('password'))
                    proxy.proxy_id = proxy_id
                    proxies.append(proxy)
            elif 'Shadowsocks' == proxy_type:
                proxy = ShadowSocksProxy(
                    private_server['host'], private_server['port'],
                    private_server['password'], private_server['encrypt_method'])
                proxy.proxy_id = proxy_id
                proxies.append(proxy)
            elif 'HTTP' == proxy_type:
                is_secured = 'SSL' == private_server.get('transport_type')
                if 'HTTP' in private_server.get('traffic_type'):
                    proxy = HttpRelayProxy(
                        private_server['host'], private_server['port'],
                        private_server['username'], private_server['password'],
                        is_secured=is_secured)
                    proxy.proxy_id = proxy_id
                    proxies.append(proxy)
                if 'HTTPS' in private_server.get('traffic_type'):
                    proxy = HttpConnectProxy(
                        private_server['host'], private_server['port'],
                        private_server['username'], private_server['password'],
                        is_secured=is_secured)
                    proxy.proxy_id = proxy_id
                    proxies.append(proxy)
            elif 'SPDY' == proxy_type:
                from ..proxies.spdy_relay import SpdyRelayProxy
                from ..proxies.spdy_connect import SpdyConnectProxy

                for i in range(private_server.get('connections_count') or 4):
                    if 'HTTP' in private_server.get('traffic_type'):
                        proxy = SpdyRelayProxy(
                            private_server['host'], private_server['port'], 'auto',
                            private_server['username'], private_server['password'])
                        proxy.proxy_id = proxy_id
                        proxies.append(proxy)
                    if 'HTTPS' in private_server.get('traffic_type'):
                        proxy = SpdyConnectProxy(
                            private_server['host'], private_server['port'], 'auto',
                            private_server['username'], private_server['password'])
                        proxy.proxy_id = proxy_id
                        proxies.append(proxy)
            else:
                raise NotImplementedError('proxy type: %s' % proxy_type)
        except:
            LOGGER.exception('failed to init %s' % private_server)


def init_proxies(config):
    global last_refresh_started_at
    last_refresh_started_at = -1
    init_private_proxies(config)
    if tcp_scrambler_enabled:
        TCP_SMUGGLER.try_start_if_network_is_ok()
        TCP_SCRAMBLER.try_start_if_network_is_ok()
    try:
        success = False
        for i in range(8):
            if load_public_proxies(config['public_servers']):
                last_refresh_started_at = 0
                if refresh_proxies():
                    success = True
                    break
            retry_interval = math.pow(2, i)
            LOGGER.error('refresh failed, will retry %s seconds later' % retry_interval)
            gevent.sleep(retry_interval)
        if success:
            LOGGER.critical('proxies init successfully')
            us_ip_cache_file = None
            if config['config_file']:
                us_ip_cache_file = os.path.join(os.path.dirname(config['config_file']), 'us_ip')
            us_ip.load_cache(us_ip_cache_file)
            for proxy in proxies:
                if isinstance(proxy, DynamicProxy):
                    proxy = proxy.delegated_to
                if hasattr(proxy, 'proxy_ip'):
                    us_ip.is_us_ip(proxy.proxy_ip)
            us_ip.save_cache(us_ip_cache_file)
        else:
            LOGGER.critical('proxies init failed')
    except:
        LOGGER.exception('failed to init proxies')


def load_public_proxies(public_servers):
    try:
        more_proxies = []
        results = networking.resolve_txt(public_servers['source'])
        for an in results:
            priority, proxy_type, count, partial_dns_record = an.text[0].split(':')[:4]
            count = int(count)
            priority = int(priority)
            if public_servers.get('%s_enabled' % proxy_type, True) and proxy_type in proxy_types:
                for i in range(count):
                    dns_record = '%s.fqrouter.com' % partial_dns_record.replace('#', str(i + 1))
                    dynamic_proxy = DynamicProxy(dns_record=dns_record, type=proxy_type, priority=priority)
                    if dynamic_proxy not in proxies:
                        more_proxies.append(dynamic_proxy)
        LOGGER.info('loaded public servers: %s' % more_proxies)
        proxies.extend(more_proxies)
        return True
    except:
        LOGGER.exception('failed to load proxy from directory')
        return False


def clear_proxy_states():
    global last_refresh_started_at
    last_refresh_started_at = 0
    HTTP_TRY_PROXY.timeout = HTTP_TRY_PROXY.INITIAL_TIMEOUT
    HTTP_TRY_PROXY.slow_ip_list.clear()
    HTTP_TRY_PROXY.host_black_list.clear()
    HTTP_TRY_PROXY.host_slow_list.clear()
    HTTP_TRY_PROXY.host_slow_detection_enabled = True
    TCP_SCRAMBLER.bad_requests.clear()
    # http proxies black list
    HTTP_TRY_PROXY.dst_black_list.clear()
    TCP_SCRAMBLER.dst_black_list.clear()
    GOOGLE_SCRAMBLER.dst_black_list.clear()
    HTTPS_ENFORCER.dst_black_list.clear()
    TCP_SMUGGLER.dst_black_list.clear()
    HTTPS_TRY_PROXY.timeout = HTTPS_TRY_PROXY.INITIAL_TIMEOUT
    HTTPS_TRY_PROXY.slow_ip_list.clear()
    HTTPS_TRY_PROXY.dst_black_list.clear()
    ip_substitution.sub_map.clear()
    for proxy in proxies:
        proxy.clear_latency_records()
        proxy.clear_failed_times()
    GoAgentProxy.global_gray_list = set()
    GoAgentProxy.global_black_list = set()
    GoAgentProxy.google_ip_failed_times = {}
    GoAgentProxy.google_ip_latency_records = {}
    stat.counters = []
    if tcp_scrambler_enabled:
        TCP_SMUGGLER.try_start_if_network_is_ok()
        TCP_SCRAMBLER.try_start_if_network_is_ok()
    if on_clear_states:
        on_clear_states()
########NEW FILE########
__FILENAME__ = tcp_gateway
import logging
import gevent.server
from .. import networking
from .proxy_client import ProxyClient
from .proxy_client import handle_client

LOGGER = logging.getLogger(__name__)
LISTEN_IP = None
LISTEN_PORT = None
server_greenlet = None


def handle(downstream_sock, address):
    src_ip, src_port = address
    try:
        dst_ip, dst_port = networking.get_original_destination(downstream_sock, src_ip, src_port)
        client = ProxyClient(downstream_sock, src_ip, src_port, dst_ip, dst_port)
        handle_client(client)
    except:
        LOGGER.exception('failed to handle %s:%s' % (src_ip, src_port))


def serve_forever():
    server = gevent.server.StreamServer((LISTEN_IP, LISTEN_PORT), handle)
    LOGGER.info('started fqsocks tcp gateway at %s:%s' % (LISTEN_IP, LISTEN_PORT))
    try:
        server.serve_forever()
    except:
        LOGGER.exception('failed to start tcp gateway')
    finally:
        LOGGER.info('tcp gateway stopped')
########NEW FILE########
__FILENAME__ = httpd
import logging
import httplib
import cgi
import os
from gevent.wsgi import WSGIServer

LOGGER = logging.getLogger(__name__)
HANDLERS = {}
server_greenlet = None
LISTEN_IP = None
LISTEN_PORT = None


def handle_request(environ, start_response):
    method = environ.get('REQUEST_METHOD')
    path = environ.get('PATH_INFO', '').strip('/')
    environ['REQUEST_ARGUMENTS'] = cgi.FieldStorage(
        fp=environ['wsgi.input'],
        environ=environ,
        keep_blank_values=True)
    accept_language = environ.get('HTTP_ACCEPT_LANGUAGE', None)
    if accept_language and 'zh' in accept_language:
        environ['select_text'] = select_zh_text
    else:
        environ['select_text'] = select_en_text
    handler = HANDLERS.get((method, path))
    if handler:
        try:
            lines = handler(environ, lambda status, headers: start_response(get_http_response(status), headers))
        except:
            LOGGER.exception('failed to handle request: %s %s' % (method, path))
            raise
    else:
        start_response(get_http_response(httplib.NOT_FOUND), [('Content-Type', 'text/plain')])
        lines = []
    for line in lines:
        yield line


def select_en_text(en_txt, zh_txt):
    return en_txt


def select_zh_text(en_txt, zh_txt):
    return zh_txt


def get_http_response(code):
    return '%s %s' % (code, httplib.responses[code])


def http_handler(method, url):
    def decorator(func):
        HANDLERS[(method, url)] = func
        return func

    return decorator


def serve_forever():
    try:
        server = WSGIServer((LISTEN_IP, LISTEN_PORT), handle_request)
        LOGGER.info('serving HTTP on port %s:%s...' % (LISTEN_IP, LISTEN_PORT))
    except:
        LOGGER.exception('failed to start HTTP server on port %s:%s' % (LISTEN_IP, LISTEN_PORT))
        os._exit(1)
    server.serve_forever()
########NEW FILE########
__FILENAME__ = ip_substitution
from . import networking
import logging
import random
import sys
import gevent

LOGGER = logging.getLogger(__name__)

sub_map = {}
sub_lock = set()

def substitute_ip(client, dst_black_list):
    if client.dst_ip not in sub_map:
        gevent.spawn(fill_sub_map, client.host, client.dst_ip)
        return False
    if client.dst_ip in sub_map and sub_map[client.dst_ip] is None:
        return False
    candidate_ips = []
    for ip in sub_map.get(client.dst_ip):
        if (ip, client.dst_port) not in dst_black_list:
            candidate_ips.append(ip)
    if candidate_ips:
        substituted_ip = random.choice(candidate_ips)
        LOGGER.info('[%s] substitute ip: %s %s => %s' % (client, client.host, client.dst_ip, substituted_ip))
        client.dst_ip = substituted_ip
        return True
    return False


def fill_sub_map(host, dst_ip):
    if host in sub_lock:
        return
    sub_lock.add(host)
    try:
        sub_host = '%s.sub.f-q.co' % '.'.join(reversed(dst_ip.split('.')))
        ips = networking.resolve_ips(sub_host)
        if host:
            ips += networking.resolve_ips(host)
        if dst_ip in ips:
            ips.remove(dst_ip)
        if ips:
            sub_map[dst_ip] = ips
        else:
            sub_map[dst_ip] = None
    except:
        LOGGER.error('failed to fill host map due to %s' % sys.exc_info()[1])
    finally:
        sub_lock.remove(host)

########NEW FILE########
__FILENAME__ = lan_ip
import china_ip

LOCAL_NETWORKS = [
    china_ip.translate_ip_range('0.0.0.0', 8),
    china_ip.translate_ip_range('10.0.0.0', 8),
    china_ip.translate_ip_range('127.0.0.0', 8),
    china_ip.translate_ip_range('169.254.0.0', 16),
    china_ip.translate_ip_range('172.16.0.0', 12),
    china_ip.translate_ip_range('192.168.0.0', 16),
    china_ip.translate_ip_range('224.0.0.0', 4),
    china_ip.translate_ip_range('240.0.0.0', 4)]


def is_lan_traffic(src, dst):
    from_lan = is_lan_ip(src)
    to_lan = is_lan_ip(dst)
    return from_lan and to_lan


def is_lan_ip(ip):
    ip_as_int = china_ip.ip_to_int(ip)
    return any(start_ip_as_int <= ip_as_int <= end_ip_as_int for start_ip_as_int, end_ip_as_int in LOCAL_NETWORKS)
########NEW FILE########
__FILENAME__ = networking
import socket
import struct
import dpkt
import logging
import random
import re
import fqlan

LOGGER = logging.getLogger(__name__)
SO_ORIGINAL_DST = 80
SO_MARK = 36
OUTBOUND_IP = None
SPI = {}
RE_IP = re.compile(r'^\d+\.\d+\.\d+\.\d+$')
DNS_HANDLER = None

default_interface_ip_cache = None

def get_default_interface_ip():
    global default_interface_ip_cache
    if not default_interface_ip_cache:
        default_interface_ip_cache = fqlan.get_default_interface_ip()
    return default_interface_ip_cache


def create_tcp_socket(server_ip, server_port, connect_timeout):
    sock = SPI['create_tcp_socket'](server_ip, server_port, connect_timeout)
    # set reuseaddr option to avoid 10048 socket error
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # resize socket recv buffer 8K->32K to improve browser releated application performance
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 32*1024)
    # disable negal algorithm to send http request quickly.
    sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, True)
    return sock


def _create_tcp_socket(server_ip, server_port, connect_timeout):
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    if OUTBOUND_IP:
        sock.bind((OUTBOUND_IP, 0))
    sock.setblocking(0)
    sock.settimeout(connect_timeout)
    try:
        sock.connect((server_ip, server_port))
    except:
        sock.close()
        raise
    sock.settimeout(None)
    return sock


SPI['create_tcp_socket'] = _create_tcp_socket


def get_original_destination(sock, src_ip, src_port):
    return SPI['get_original_destination'](sock, src_ip, src_port)


def _get_original_destination(sock, src_ip, src_port):
    dst = sock.getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
    dst_port, dst_ip = struct.unpack("!2xH4s8x", dst)
    dst_ip = socket.inet_ntoa(dst_ip)
    return dst_ip, dst_port


SPI['get_original_destination'] = _get_original_destination


def resolve_ips(host):
    if RE_IP.match(host):
        return [host]
    request = dpkt.dns.DNS(
        id=random.randint(1, 65535), qd=[dpkt.dns.DNS.Q(name=str(host), type=dpkt.dns.DNS_A)])
    response = DNS_HANDLER.query(request, str(request))
    ips = [socket.inet_ntoa(an.ip) for an in response.an if hasattr(an, 'ip')]
    return ips


def resolve_txt(domain):
    request = dpkt.dns.DNS(
        id=random.randint(1, 65535), qd=[dpkt.dns.DNS.Q(name=str(domain), type=dpkt.dns.DNS_TXT)])
    return DNS_HANDLER.query(request, str(request)).an
########NEW FILE########
__FILENAME__ = nfqueue_ipset
#!/usr/bin/env python
import logging
import logging.handlers
import argparse
import sys
import socket
import china_ip

import dpkt


LOGGER = logging.getLogger('nfqueue-ipset')

RULES = []


def main():
    global DEFAULT_VERDICT
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('--log-file')
    argument_parser.add_argument('--log-level', choices=['INFO', 'DEBUG'], default='INFO')
    argument_parser.add_argument('--queue-number', default=0, type=int)
    argument_parser.add_argument(
        '--rule', default=[], action='append', help='direction,ip_set_name,verdict, for example dst,china,0xfeed1')
    argument_parser.add_argument('--default', default='ACCEPT', help='if no rule matched')
    args = argument_parser.parse_args()
    log_level = getattr(logging, args.log_level)
    logging.basicConfig(stream=sys.stdout, level=log_level, format='%(asctime)s %(levelname)s %(message)s')
    if args.log_file:
        logging.getLogger('nfqueue-ipset').handlers = []
        handler = logging.handlers.RotatingFileHandler(
            args.log_file, maxBytes=1024 * 16, backupCount=0)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        handler.setLevel(log_level)
        logging.getLogger('nfqueue-ipset').addHandler(handler)
    for input in args.rule:
        RULES.append(Rule.parse(input))
    Rule.DEFAULT_VERDICT = Rule.parse_verdict(args.default)
    Rule.MATCHED_DEFAULT = 'default,%s,%s => ' + args.default
    handle_nfqueue(args.queue_number)


def handle_nfqueue(queue_number):
    from netfilterqueue import NetfilterQueue
    for i in range(3):
        try:
            nfqueue = NetfilterQueue()
            nfqueue.bind(queue_number, handle_packet)
            LOGGER.info('handling nfqueue at queue number %s' % queue_number)
            nfqueue.run()
        except:
            LOGGER.exception('failed to handle nfqueue')
            return
        finally:
            LOGGER.info('stopped handling nfqueue')

counter = 0

def handle_packet(nfqueue_element):
    global counter
    try:
        counter = (counter + 1) % 100
        if counter == 0:
            LOGGER.info('100 packets')
        ip_packet = dpkt.ip.IP(nfqueue_element.get_payload())
        src = socket.inet_ntoa(ip_packet.src)
        dst = socket.inet_ntoa(ip_packet.dst)
        verdict = Rule.get_verdict(src, dst)
        if 'ACCEPT' == verdict:
            nfqueue_element.accept()
        elif 'DROP' == verdict:
            nfqueue_element.drop()
        else:
            nfqueue_element.set_mark(verdict)
            nfqueue_element.repeat()
    except:
        LOGGER.exception('failed to handle packet')
        nfqueue_element.accept()


class Rule(object):
    DEFAULT_VERDICT = None
    MATCHED_DEFAULT = None

    def __init__(self, direction, ipset_name, verdict):
        super(Rule, self).__init__()
        self.direction = direction
        self.ipset_name = ipset_name
        self.matched_src = 'src,%s => ' + verdict
        self.matched_dst = 'dst,%s => ' + verdict
        self.verdict = Rule.parse_verdict(verdict)
        assert self.ipset_name == 'china' # it is not a generic implementation yet
        self.match = getattr(self, 'match_%s' % direction)

    def match_src(self, src, dst):
        matched = china_ip.is_china_ip(src)
        if matched:
            LOGGER.debug(self.matched_src % src)
        return matched

    def match_dst(self, src, dst):
        matched = china_ip.is_china_ip(dst)
        if matched:
            LOGGER.debug(self.matched_dst % dst)
        return matched

    @classmethod
    def get_verdict(cls, src, dst):
        for rule in RULES:
            if rule.match(src, dst):
                return rule.verdict
        LOGGER.debug(Rule.MATCHED_DEFAULT % (src, dst))
        return Rule.DEFAULT_VERDICT

    @classmethod
    def parse_verdict(cls, verdict):
        if verdict in ('ACCEPT', 'DROP'):
            return verdict
        else:
            return eval(verdict)

    @classmethod
    def parse(cls, input):
        return Rule(*input.split(','))


if '__main__' == __name__:
    main()
########NEW FILE########
__FILENAME__ = assets
# -*- coding: utf-8 -*-
import httplib
import os.path
import functools
from .. import httpd

ASSETS_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets')

def get_asset(file_path, content_type, environ, start_response):
    start_response(httplib.OK, [('Content-Type', content_type)])
    with open(file_path) as f:
        return [f.read()]


httpd.HANDLERS[('GET', 'assets/bootstrap/css/bootstrap.css')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'bootstrap', 'css', 'bootstrap.css'), 'text/css')

httpd.HANDLERS[('GET', 'assets/bootstrap/css/bootstrap-theme.css')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'bootstrap', 'css', 'bootstrap-theme.css'), 'text/css')

httpd.HANDLERS[('GET', 'assets/bootstrap/fonts/glyphicons-halflings-regular.eot')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'bootstrap', 'fonts', 'glyphicons-halflings-regular.eot'),
    'application/vnd.ms-fontobject')

httpd.HANDLERS[('GET', 'assets/bootstrap/fonts/glyphicons-halflings-regular.ttf')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'bootstrap', 'fonts', 'glyphicons-halflings-regular.ttf'), 'font/ttf')

httpd.HANDLERS[('GET', 'assets/bootstrap/fonts/glyphicons-halflings-regular.svg')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'bootstrap', 'fonts', 'glyphicons-halflings-regular.svg'), 'image/svg+xml')

httpd.HANDLERS[('GET', 'assets/bootstrap/fonts/glyphicons-halflings-regular.woff')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'bootstrap', 'fonts', 'glyphicons-halflings-regular.woff'), 'font/x-woff')

httpd.HANDLERS[('GET', 'assets/bootstrap/js/bootstrap.js')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'bootstrap', 'js', 'bootstrap.js'), 'text/javascript')

httpd.HANDLERS[('GET', 'assets/jquery.min.js')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'jquery.min.js'), 'text/javascript')

httpd.HANDLERS[('GET', 'assets/tablesort.min.js')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'tablesort.min.js'), 'text/javascript')

httpd.HANDLERS[('GET', 'assets/visibility.core.js')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'visibility.core.js'), 'text/javascript')

httpd.HANDLERS[('GET', 'assets/visibility.timer.js')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'visibility.timer.js'), 'text/javascript')

httpd.HANDLERS[('GET', 'assets/masonry.pkgd.min.js')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'masonry.pkgd.min.js'), 'text/javascript')

httpd.HANDLERS[('GET', 'assets/bootbox.min.js')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'bootbox.min.js'), 'text/javascript')

httpd.HANDLERS[('GET', 'assets/bootstrap-switch.css')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'bootstrap-switch.css'), 'text/css')

httpd.HANDLERS[('GET', 'assets/bootstrap-switch.js')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'bootstrap-switch.js'), 'text/javascript')

httpd.HANDLERS[('GET', 'assets/busy-indicator.gif')] = functools.partial(
    get_asset, os.path.join(ASSETS_DIR, 'busy-indicator.gif'), 'image/gif')
########NEW FILE########
__FILENAME__ = downstream
# -*- coding: utf-8 -*-
import httplib
import os
import json
from gevent import subprocess
import logging
import re

import gevent

from .. import httpd

from ..gateways import http_gateway
from .. import config_file
from .. import networking


LOGGER = logging.getLogger(__name__)
DOWNSTREAM_HTML_FILE = os.path.join(os.path.dirname(__file__), '..', 'templates', 'downstream.html')
RE_EXTERNAL_IP_ADDRESS = re.compile(r'ExternalIPAddress = (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
spi_wifi_repeater = None
spi_upnp = None


@httpd.http_handler('POST', 'http-gateway/enable')
def handle_enable_http_gateway(environ, start_response):
    if http_gateway.server_greenlet is None:
        http_gateway.server_greenlet = gevent.spawn(http_gateway.serve_forever)

    def apply(config):
        config['http_gateway']['enabled'] = True

    config_file.update_config(apply)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'http-gateway/disable')
def handle_disable_http_gateway(environ, start_response):
    if http_gateway.server_greenlet is not None:
        http_gateway.server_greenlet.kill()
        http_gateway.server_greenlet = None

    def apply(config):
        config['http_gateway']['enabled'] = False

    config_file.update_config(apply)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'http-manager/config/update')
def handle_update_http_manager_config(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    port = environ['REQUEST_ARGUMENTS']['port'].value
    try:
        httpd.LISTEN_PORT = int(port)
    except:
        return [environ['select_text']('must be a number', '只能是数字')]
    if httpd.server_greenlet is not None:
        httpd.server_greenlet.kill()
        httpd.server_greenlet = None
    httpd.server_greenlet = gevent.spawn(httpd.serve_forever)
    gevent.sleep(0.5)
    if httpd.server_greenlet.ready():
        httpd.server_greenlet = None
        return [environ['select_text']('failed to start on new port', '用新端口启动失败')]

    def apply(config):
        config['http_manager']['port'] = httpd.LISTEN_PORT

    config_file.update_config(apply)
    return []


@httpd.http_handler('POST', 'http-gateway/config/update')
def handle_update_http_gateway_config(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    port = environ['REQUEST_ARGUMENTS']['port'].value
    try:
        http_gateway.LISTEN_PORT = int(port)
    except:
        return [environ['select_text']('must be a number', '只能是数字')]
    if http_gateway.server_greenlet is not None:
        http_gateway.server_greenlet.kill()
        http_gateway.server_greenlet = None
    http_gateway.server_greenlet = gevent.spawn(http_gateway.serve_forever)
    gevent.sleep(0.5)
    if http_gateway.server_greenlet.ready():
        http_gateway.server_greenlet = None
        return [environ['select_text']('failed to start on new port', '用新端口启动失败')]

    def apply(config):
        config['http_gateway']['port'] = http_gateway.LISTEN_PORT

    config_file.update_config(apply)
    return []


@httpd.http_handler('POST', 'wifi-repeater/enable')
def handle_enable_wifi_repeater(environ, start_response):
    config = config_file.read_config()
    if spi_wifi_repeater:
        error = spi_wifi_repeater['start'](config['wifi_repeater']['ssid'], config['wifi_repeater']['password'])
    else:
        error = 'unsupported'
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return [error]


@httpd.http_handler('POST', 'wifi-repeater/disable')
def handle_enable_wifi_repeater(environ, start_response):
    if spi_wifi_repeater:
        error = spi_wifi_repeater['stop']()
    else:
        error = 'unsupported'
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return [error]


@httpd.http_handler('POST', 'wifi-repeater/reset')
def handle_reset_wifi_repeater(environ, start_response):
    if spi_wifi_repeater:
        spi_wifi_repeater['reset']()
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'wifi-repeater/config/update')
def handle_update_wifi_repeater_config(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    if not spi_wifi_repeater:
        return ['Wifi repeater is unsupported']
    ssid = environ['REQUEST_ARGUMENTS']['ssid'].value
    password = environ['REQUEST_ARGUMENTS']['password'].value
    if not ssid:
        return [environ['select_text']('SSID must not be empty', 'SSID不能为空')]
    if not password:
        return [environ['select_text']('Password must not be empty', '密码不能为空')]
    if len(password) < 8:
        return [environ['select_text']('Password must not be shorter than 8 characters', '密码长度必须大于8位')]

    def apply(config):
        config['wifi_repeater']['ssid'] = ssid
        config['wifi_repeater']['password'] = password

    config_file.update_config(apply)
    if spi_wifi_repeater['is_started']():
        error = spi_wifi_repeater['stop']()
        if error:
            return [error]
        error = spi_wifi_repeater['start']()
        if error:
            return [error]
    return []


@httpd.http_handler('POST', 'wifi-p2p/enable')
def handle_enable_wifi_p2p(environ, start_response):
    if spi_wifi_repeater:
        error = spi_wifi_repeater['enable_wifi_p2p']()
    else:
        error = 'unsupported'
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return [error]


@httpd.http_handler('POST', 'wifi-p2p/disable')
def handle_enable_wifi_p2p(environ, start_response):
    if spi_wifi_repeater:
        error = spi_wifi_repeater['disable_wifi_p2p']()
    else:
        error = 'unsupported'
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return [error]


@httpd.http_handler('GET', 'upnp/status')
def handle_get_upnp_status(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/json')])
    try:
        upnp_status = get_upnp_status()
    except:
        LOGGER.exception('failed to get upnp status')
        upnp_status = {
            'external_ip_address': None,
            'port': None,
            'is_enabled': False
        }
    return [json.dumps(upnp_status)]


@httpd.http_handler('POST', 'upnp/enable')
def handle_enable_upnp(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/json')])
    upnp_port = int(environ['REQUEST_ARGUMENTS']['upnp_port'].value)
    upnp_username = environ['REQUEST_ARGUMENTS']['upnp_username'].value
    upnp_password = environ['REQUEST_ARGUMENTS']['upnp_password'].value
    upnp_is_password_protected = 'true' == environ['REQUEST_ARGUMENTS']['upnp_is_password_protected'].value
    def apply(config):
        config['upnp']['port'] = upnp_port
        config['upnp']['username'] = upnp_username
        config['upnp']['password'] = upnp_password
        config['upnp']['is_password_protected'] = upnp_is_password_protected

    config_file.update_config(apply)
    try:
        default_interface_ip = networking.get_default_interface_ip()
        if not default_interface_ip:
            return ['failed to get default interface ip']
        execute_upnpc('-a %s %s %s tcp' % (default_interface_ip, http_gateway.LISTEN_PORT, upnp_port))
    except:
        LOGGER.exception('failed to enable upnp')
        return ['failed to enable upnp']

    def apply(config):
        config['upnp']['port'] = upnp_port

    config_file.update_config(apply)
    status = get_upnp_status()
    if not status['is_enabled']:
        if upnp_port < 1024:
            upnp_port += 1100
            execute_upnpc('-a %s %s %s tcp' % (default_interface_ip, http_gateway.LISTEN_PORT, upnp_port))

            def apply(config):
                config['upnp']['port'] = upnp_port

            config_file.update_config(apply)
            status = get_upnp_status()
        else:
            return ['failed to enable upnp']
    http_gateway.UPNP_PORT = upnp_port
    http_gateway.UPNP_AUTH = None
    return [json.dumps(status)]


@httpd.http_handler('POST', 'upnp/disable')
def handle_disable_upnp(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    upnp_port = http_gateway.get_upnp_port()
    try:
        execute_upnpc('-d %s tcp' % upnp_port)
    except:
        LOGGER.exception('failed to disable upnp')
        return ['failed to disable upnp']
    return []


def get_upnp_status():
    output = execute_upnpc('-l')
    match = RE_EXTERNAL_IP_ADDRESS.search(output)
    if match:
        external_ip_address = match.group(1)
        http_gateway.external_ip_address = external_ip_address
    else:
        external_ip_address = None
    upnp_port = http_gateway.get_upnp_port()
    return {
        'external_ip_address': external_ip_address,
        'port': upnp_port,
        'is_enabled': (':%s' % http_gateway.LISTEN_PORT) in output
    }


def execute_upnpc(args):
    if spi_upnp:
        return spi_upnp['execute_upnpc'](args)
    LOGGER.info('upnpc %s' % args)
    try:
        output = subprocess.check_output('upnpc %s' % args, shell=True)
        LOGGER.info('succeed, output: %s' % output)
    except subprocess.CalledProcessError, e:
        LOGGER.error('failed, output: %s' % e.output)
        raise
    return output
########NEW FILE########
__FILENAME__ = home
# -*- coding: utf-8 -*-
import httplib
import logging
import os.path
import fqdns
import time
import urllib2

import jinja2

from .. import httpd
from ..gateways import proxy_client
from .. import config_file
from ..gateways import http_gateway
from . import downstream
from .. import networking
from . import upstream
HOME_HTML_FILE = os.path.join(os.path.dirname(__file__), '..', 'templates', 'home.html')
LOGGER = logging.getLogger(__name__)

@httpd.http_handler('GET', '')
@httpd.http_handler('GET', 'home')
def home_page(environ, start_response):
    with open(HOME_HTML_FILE) as f:
        template = jinja2.Template(unicode(f.read(), 'utf8'))
    start_response(httplib.OK, [('Content-Type', 'text/html')])
    is_root = 0 == os.getuid()
    args = dict(
        _=environ['select_text'],
        domain_name=environ.get('HTTP_HOST') or '127.0.0.1:2515',
        tcp_scrambler_enabled=proxy_client.tcp_scrambler_enabled,
        google_scrambler_enabled=proxy_client.google_scrambler_enabled,
        https_enforcer_enabled=proxy_client.https_enforcer_enabled,
        china_shortcut_enabled=proxy_client.china_shortcut_enabled,
        direct_access_enabled=proxy_client.direct_access_enabled,
        prefers_private_proxy=proxy_client.prefers_private_proxy,
        config=config_file.read_config(),
        is_root=is_root,
        default_interface_ip=networking.get_default_interface_ip(),
        http_gateway=http_gateway,
        httpd=httpd,
        spi_wifi_repeater=downstream.spi_wifi_repeater if is_root else None,
        now=time.time(),
        hosted_domain_enabled=networking.DNS_HANDLER.enable_hosted_domain)
    html = template.render(**args).encode('utf8')
    return [html]


@httpd.http_handler('GET', 'notice')
def get_notice_url(environ, start_response):
    try:
        domain = environ['select_text']('en.url.notice.fqrouter.com', 'cn.url.notice.fqrouter.com')
        results = networking.resolve_txt(domain)
        LOGGER.info('%s => %s' % (domain, results))
        url = results[0].text[0]
        start_response(httplib.FOUND, [
            ('Content-Type', 'text/html'),
            ('Cache-Control', 'no-cache, no-store, must-revalidate'),
            ('Pragma', 'no-cache'),
            ('Expires', '0'),
            ('Location', url)])
        return []
    except:
        LOGGER.exception('failed to resolve notice url')
        start_response(httplib.FOUND, [
            ('Content-Type', 'text/html'),
            ('Cache-Control', 'no-cache, no-store, must-revalidate'),
            ('Pragma', 'no-cache'),
            ('Expires', '0'),
            ('Location', 'https://s3.amazonaws.com/fqrouter-notice/index.html')])
        return []
########NEW FILE########
__FILENAME__ = lan_device
import httplib
import json
import fqlan
import logging
import os

import gevent
import jinja2

from .. import httpd


LAN_DEVICES_HTML_FILE = os.path.join(os.path.dirname(__file__), '..', 'templates', 'lan-devices.html')
LOGGER = logging.getLogger(__name__)
scan_greenlet = None
forge_greenlet = None
lan_devices = {}


@httpd.http_handler('POST', 'lan/scan')
def handle_lan_scan(environ, start_response):
    global scan_greenlet
    start_response(httplib.OK, [('Content-Type', 'application/json')])
    was_running = False
    if scan_greenlet is not None:
        if scan_greenlet.ready():
            scan_greenlet = gevent.spawn(lan_scan)
        else:
            was_running = True
    else:
        scan_greenlet = gevent.spawn(lan_scan)
    return [json.dumps({
        'was_running': was_running
    })]


@httpd.http_handler('GET', 'lan/devices')
def lan_devices_page(environ, start_response):
    with open(LAN_DEVICES_HTML_FILE) as f:
        template = jinja2.Template(unicode(f.read(), 'utf8'))
    start_response(httplib.OK, [('Content-Type', 'text/html')])
    is_scan_completed = scan_greenlet.ready() if scan_greenlet is not None else False
    return [template.render(
        _=environ['select_text'], lan_devices=lan_devices,
        is_scan_completed=is_scan_completed).encode('utf8')]


@httpd.http_handler('POST', 'lan/update')
def handle_lan_update(environ, start_response):
    global forge_greenlet
    start_response(httplib.OK, [('Content-Type', 'application/json')])
    ip = environ['REQUEST_ARGUMENTS']['ip'].value
    is_picked = 'true' == environ['REQUEST_ARGUMENTS']['is_picked'].value
    LOGGER.info('update %s %s' % (ip, is_picked))
    if ip not in lan_devices:
        return [json.dumps({'success': False})]
    lan_devices[ip]['is_picked'] = is_picked
    if forge_greenlet:
        forge_greenlet.kill()
    forge_greenlet = gevent.spawn(lan_forge)
    return [json.dumps({'success': True})]


@httpd.http_handler('GET', 'pick-and-play/is-started')
def is_pick_and_play_started(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    is_started = not forge_greenlet.ready() if forge_greenlet is not None else False
    return ['TRUE' if is_started else 'FALSE']


def lan_scan():
    for result in fqlan.scan(mark='0xcafe'):
        ip, mac, hostname = result
        if ip not in lan_devices:
            lan_devices[ip] = {
                'ip': ip,
                'mac': mac,
                'hostname': hostname,
                'is_picked': False
            }


def lan_forge():
    victims = []
    for lan_device in lan_devices.values():
        if lan_device['is_picked']:
            victims.append((lan_device['ip'], lan_device['mac']))
    if victims:
        fqlan.forge(victims)
    else:
        LOGGER.info('no devices picked')
########NEW FILE########
__FILENAME__ = upstream
# -*- coding: utf-8 -*-
import httplib
import time
import logging
import os.path
import json
from datetime import datetime

import gevent
import jinja2

from .. import stat
from .. import httpd
from ..gateways import proxy_client
from ..proxies.http_try import HTTP_TRY_PROXY
from .. import config_file
from .. import networking


PROXIES_HTML_FILE = os.path.join(os.path.dirname(__file__), '..', 'templates', 'proxies.html')
UPSTREAM_HTML_FILE = os.path.join(os.path.dirname(__file__), '..', 'templates', 'upstream.html')
LOGGER = logging.getLogger(__name__)
MAX_TIME_RANGE = 60 * 10


@httpd.http_handler('POST', 'refresh-proxies')
def handle_refresh_proxies(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    proxy_client.auto_fix_enabled = True
    proxy_client.clear_proxy_states()
    proxy_client.refresh_proxies()
    return ['OK']


@httpd.http_handler('GET', 'proxies')
def handle_list_proxies(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/html')])
    proxies_counters = {}
    for counter in stat.counters:
        proxies_counters.setdefault(counter.proxy.public_name, []).append(counter)
    after = time.time() - MAX_TIME_RANGE
    proxies_stats = {}
    for proxy_public_name, proxy_counters in sorted(proxies_counters.items(),
                                                    key=lambda (proxy_public_name, proxy_counters): proxy_public_name):
        rx_bytes_list, rx_seconds_list, _ = zip(*[counter.total_rx(after) for counter in proxy_counters])
        rx_bytes = sum(rx_bytes_list)
        rx_seconds = sum(rx_seconds_list)
        if rx_seconds:
            rx_speed = rx_bytes / (rx_seconds * 1000)
        else:
            rx_speed = 0
        tx_bytes_list, tx_seconds_list, _ = zip(*[counter.total_tx(after) for counter in proxy_counters])
        tx_bytes = sum(tx_bytes_list)
        tx_seconds = sum(tx_seconds_list)
        if tx_seconds:
            tx_speed = tx_bytes / (tx_seconds * 1000)
        else:
            tx_speed = 0
        if not proxy_public_name:
            continue
        proxies_stats[proxy_public_name] = {
            'proxy_id': None,
            'rx_speed_value': rx_speed,
            'rx_speed_label': '%05.2f KB/s' % rx_speed,
            'rx_bytes_value': rx_bytes,
            'rx_bytes_label': to_human_readable_size(rx_bytes),
            'tx_speed_value': tx_speed,
            'tx_speed_label': '%05.2f KB/s' % tx_speed,
            'tx_bytes_value': tx_bytes,
            'tx_bytes_label': to_human_readable_size(tx_bytes)
        }
    for proxy in proxy_client.proxies:
        proxy_public_name = proxy.public_name
        if not proxy_public_name:
            continue
        if proxy_public_name in proxies_stats:
            proxies_stats[proxy_public_name]['died'] = proxies_stats[proxy_public_name].get('died', False) or proxy.died
            proxies_stats[proxy_public_name]['proxy_id'] = proxy.proxy_id
        else:
            proxies_stats[proxy_public_name] = {
                'proxy_id': proxy.proxy_id,
                'died': proxy.died,
                'rx_speed_value': 0,
                'rx_speed_label': '00.00 KB/s',
                'rx_bytes_value': 0,
                'rx_bytes_label': '000.00 B',
                'tx_speed_value': 0,
                'tx_speed_label': '00.00 KB/s',
                'tx_bytes_value': 0,
                'tx_bytes_label': '000.00 B'
            }
    with open(PROXIES_HTML_FILE) as f:
        template = jinja2.Template(f.read())
    return template.render(proxies_stats=proxies_stats).encode('utf8')


def enable_proxies():
    proxy_client.clear_proxy_states()
    gevent.spawn(proxy_client.init_proxies, config_file.read_config())


def disable_proxies():
    proxy_client.proxies = []
    proxy_client.clear_proxy_states()


@httpd.http_handler('POST', 'tcp-scrambler/enable')
def handle_enable_tcp_scrambler(environ, start_response):
    proxy_client.tcp_scrambler_enabled = True
    config_file.update_config(tcp_scrambler_enabled=True)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'tcp-scrambler/disable')
def handle_disable_tcp_scrambler(environ, start_response):
    proxy_client.tcp_scrambler_enabled = False
    config_file.update_config(tcp_scrambler_enabled=False)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'google-scrambler/enable')
def handle_enable_googlescrambler(environ, start_response):
    proxy_client.google_scrambler_enabled = True
    config_file.update_config(google_scrambler_enabled=True)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'google-scrambler/disable')
def handle_disable_google_scrambler(environ, start_response):
    proxy_client.google_scrambler_enabled = False
    config_file.update_config(google_scrambler_enabled=False)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'https-enforcer/enable')
def handle_enable_https_enforcer(environ, start_response):
    proxy_client.https_enforcer_enabled = True
    config_file.update_config(https_enforcer_enabled=True)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'https-enforcer/disable')
def handle_disable_https_enforcer(environ, start_response):
    proxy_client.https_enforcer_enabled = False
    config_file.update_config(https_enforcer_enabled=False)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'china-shortcut/enable')
def handle_enable_china_shortcut(environ, start_response):
    proxy_client.china_shortcut_enabled = True
    config_file.update_config(china_shortcut_enabled=True)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'china-shortcut/disable')
def handle_disable_china_shortcut(environ, start_response):
    proxy_client.china_shortcut_enabled = False
    config_file.update_config(china_shortcut_enabled=False)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'direct-access/enable')
def handle_enable_direct_access(environ, start_response):
    proxy_client.direct_access_enabled = True
    config_file.update_config(direct_access_enabled=True)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'direct-access/disable')
def handle_disable_direct_access(environ, start_response):
    proxy_client.direct_access_enabled = False
    config_file.update_config(direct_access_enabled=False)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'hosted-domain/enable')
def handle_enable_hosted_domain(environ, start_response):
    networking.DNS_HANDLER.enable_hosted_domain = True
    config_file.update_config(hosted_domain_enabled=True)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'hosted-domain/disable')
def handle_disable_hosted_domain(environ, start_response):
    networking.DNS_HANDLER.enable_hosted_domain = False
    config_file.update_config(hosted_domain_enabled=False)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'prefers-private-proxy/enable')
def handle_enable_prefers_private_proxy(environ, start_response):
    proxy_client.prefers_private_proxy = True
    config_file.update_config(prefers_private_proxy=True)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'prefers-private-proxy/disable')
def handle_disable_prefers_private_proxy(environ, start_response):
    proxy_client.prefers_private_proxy = False
    config_file.update_config(prefers_private_proxy=False)
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'goagent-public-servers/enable')
def handle_enable_goagent_public_servers(environ, start_response):
    def apply(config):
        config['public_servers']['goagent_enabled'] = True

    proxy_client.goagent_public_servers_enabled = True
    config_file.update_config(apply)
    disable_proxies()
    enable_proxies()
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'goagent-public-servers/disable')
def handle_disable_goagent_public_servers(environ, start_response):
    def apply(config):
        config['public_servers']['goagent_enabled'] = False

    proxy_client.goagent_public_servers_enabled = False
    config_file.update_config(apply)
    disable_proxies()
    enable_proxies()
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'ss-public-servers/enable')
def handle_enable_ss_public_servers(environ, start_response):
    def apply(config):
        config['public_servers']['ss_enabled'] = True

    proxy_client.ss_public_servers_enabled = True
    config_file.update_config(apply)
    disable_proxies()
    enable_proxies()
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'ss-public-servers/disable')
def handle_disable_ss_public_servers(environ, start_response):
    def apply(config):
        config['public_servers']['ss_enabled'] = False

    proxy_client.ss_public_servers_enabled = False
    config_file.update_config(apply)
    disable_proxies()
    enable_proxies()
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


@httpd.http_handler('POST', 'proxies/add')
def handle_add_proxy(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    private_server = to_private_server(environ)
    if isinstance(private_server, basestring):
        return [private_server]
    proxy_type = environ['REQUEST_ARGUMENTS']['proxy_type'].value

    def apply(config):
        config_file.add_proxy(config, proxy_type=proxy_type,**private_server)

    config_file.update_config(apply)
    disable_proxies()
    enable_proxies()
    return []


@httpd.http_handler('POST', 'proxies/update')
def handle_update_proxy(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    proxy_id = environ['REQUEST_ARGUMENTS']['proxy_id'].value
    proxy_type = environ['REQUEST_ARGUMENTS']['proxy_type'].value
    private_server = to_private_server(environ)
    if isinstance(private_server, basestring):
        return [private_server]
    private_server['proxy_type'] = proxy_type
    def apply(config):
        config['private_servers'][proxy_id] = private_server

    config_file.update_config(apply)
    disable_proxies()
    enable_proxies()
    return []


def to_private_server(environ):
    _ = environ['select_text']
    args = {key: environ['REQUEST_ARGUMENTS'][key].value for key in environ['REQUEST_ARGUMENTS'].keys()}
    args.pop('proxy_id', None)
    proxy_type = args['proxy_type']
    if 'GoAgent' == proxy_type:
        appid = args['appid']
        if not appid:
            return _('App Id must not be empty', 'App Id 必填')
        return {
            'appid': appid,
            'path': args.get('path') or '/2',
            'goagent_options': args.get('goagent_options'),
            'goagent_password': args.get('goagent_password')
        }
    elif 'SSH' == proxy_type:
        host = args['host']
        if not host:
            return _('Host must not be empty', '主机必填')
        port = args['port']
        if not port:
            return _('Port must not be empty', '端口必填')
        try:
            port = int(port)
        except:
            return _('Port must be number', '端口必须是数字')
        username = args['username']
        if not username:
            return _('User name must not be empty', '用户名必填')
        password = args.get('password')
        connections_count = int(args.get('connections_count') or 4)
        return {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'connections_count': connections_count
        }
    elif 'Shadowsocks' == proxy_type:
        host = args['host']
        if not host:
            return _('Host must not be empty', '主机必填')
        port = args['port']
        if not port:
            return _('Port must not be empty', '端口必填')
        password = args.get('password')
        if not password:
            return _('Password must not be empty', '密码必填')
        encrypt_method = args.get('encrypt_method')
        if not encrypt_method:
            return _('Encrypt method must not be empty', '加密方式必填')
        return {
            'host': host,
            'port': port,
            'password': password,
            'encrypt_method': encrypt_method
        }
    elif 'HTTP' == proxy_type:
        host = args['host']
        if not host:
            return _('Host must not be empty', '主机必填')
        port = args['port']
        if not port:
            return _('Port must not be empty', '端口必填')
        try:
            port = int(port)
        except:
            return _('Port must be number', '端口必须是数字')
        username = args['username']
        password = args.get('password')
        return {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'traffic_type': args.get('traffic_type') or 'HTTP/HTTPS',
            'transport_type': args.get('transport_type') or 'HTTP'
        }
    elif 'SPDY' == proxy_type:
        host = args['host']
        if not host:
            return _('Host must not be empty', '主机必填')
        port = args['port']
        if not port:
            return _('Port must not be empty', '端口必填')
        try:
            port = int(port)
        except:
            return _('Port must be number', '端口必须是数字')
        username = args['username']
        if not username:
            return _('User name must not be empty', '用户名必填')
        password = args.get('password')
        if not password:
            return _('Password must not be empty', '密码必填')
        connections_count = int(args.get('connections_count') or 4)
        return {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'traffic_type': args.get('traffic_type') or 'HTTP/HTTPS',
            'connections_count': connections_count
        }
    else:
        return _('Internal Error', '内部错误')


@httpd.http_handler('GET', 'proxy')
def handle_get_proxy(environ, start_response):
    proxy_id = environ['REQUEST_ARGUMENTS']['proxy_id'].value
    proxy = config_file.read_config()['private_servers'].get(proxy_id)
    start_response(httplib.OK, [('Content-Type', 'application/json')])
    if proxy:
        proxy_type = proxy.pop('proxy_type')
        yield json.dumps({
            'proxy_id': proxy_id,
            'proxy_type': proxy_type,
            'properties': proxy
        })
    else:
        yield json.dumps({})


@httpd.http_handler('POST', 'proxies/delete')
def handle_get_proxy(environ, start_response):
    proxy_id = environ['REQUEST_ARGUMENTS']['proxy_id'].value
    def apply(config):
        config['private_servers'].pop(proxy_id, None)

    config_file.update_config(apply)
    disable_proxies()
    enable_proxies()
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    return []


def to_human_readable_size(num):
    for x in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return '%06.2f %s' % (num, x)
        num /= 1024.0


########NEW FILE########
__FILENAME__ = direct
import logging
from .. import networking

LOGGER = logging.getLogger(__name__)
on_proxy_died = None


def to_bool(s):
    if isinstance(s, bool):
        return s
    return 'True' == s


class Proxy(object):
    def __init__(self):
        super(Proxy, self).__init__()
        self.died = False
        self.flags = set()
        self.priority = 0
        self.proxy_id = None
        self._proxy_ip = None
        self.latency_records_total = 0
        self.latency_records_count = 0
        self.failed_times = 0

    def increase_failed_time(self):
        LOGGER.error('failed once/%s: %s' % (self.failed_times, self))
        self.failed_times += 1
        if self.failed_times > 3:
            self.died = True
            LOGGER.fatal('!!! proxy died !!!: %s' % self)

    def record_latency(self, latency):
        self.latency_records_total += latency
        self.latency_records_count += 1
        if self.latency_records_count > 100:
            self.latency_records_total = self.latency
            self.latency_records_count = 1

    def clear_latency_records(self):
        self.latency_records_total = 0
        self.latency_records_count = 0

    def clear_failed_times(self):
        self.failed_times = 0

    @property
    def latency(self):
        if self.latency_records_count:
            return self.latency_records_total / self.latency_records_count
        else:
            return 0

    @property
    def proxy_ip(self):
        if self._proxy_ip:
            return self._proxy_ip
        ips = networking.resolve_ips(self.proxy_host)
        if not ips:
            LOGGER.critical('!!! failed to resolve proxy ip: %s' % self.proxy_host)
            self._proxy_ip = '0.0.0.0'
            self.died = True
            return self._proxy_ip
        self._proxy_ip = ips[0]
        return self._proxy_ip

    def forward(self, client):
        client.forwarding_by = self
        try:
            self.do_forward(client)
        finally:
            if self.died:
                LOGGER.fatal('[%s] !!! proxy died !!!: %s' % (repr(client), self))
                client.dump_proxies()
                if on_proxy_died:
                    on_proxy_died(self)

    def do_forward(self, client):
        raise NotImplementedError()

    @classmethod
    def refresh(cls, proxies):
        for proxy in proxies:
            proxy.died = False
        return True

    def is_protocol_supported(self, protocol, client=None):
        return False

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __hash__(self):
        return hash(repr(self))

    @property
    def public_name(self):
        return None


class DirectProxy(Proxy):
    DEFAULT_CONNECT_TIMEOUT = 5

    def __init__(self, connect_timeout=DEFAULT_CONNECT_TIMEOUT):
        super(DirectProxy, self).__init__()
        self.flags.add('DIRECT')
        self.connect_timeout = connect_timeout

    def do_forward(self, client):
        try:
            upstream_sock = self.create_upstream_sock(client)
        except:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('[%s] direct connect upstream socket timed out' % (repr(client)), exc_info=1)
            client.fall_back(reason='direct connect upstream socket timed out')
            return
        upstream_sock.settimeout(None)
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug('[%s] direct upstream connected' % repr(client))
        upstream_sock.counter.sending(len(client.peeked_data))
        upstream_sock.sendall(client.peeked_data)
        client.forward(upstream_sock, timeout=60, after_started_timeout=60 * 60)

    def create_upstream_sock(self, client):
        return client.create_tcp_socket(client.dst_ip, client.dst_port, self.connect_timeout)

    def is_protocol_supported(self, protocol, client=None):
        return True

    def __repr__(self):
        return 'DirectProxy'


class NoneProxy(Proxy):
    def do_forward(self, client):
        return

    def is_protocol_supported(self, protocol, client=None):
        return True

    def __repr__(self):
        return 'NoneProxy'


DIRECT_PROXY = DirectProxy()
NONE_PROXY = NoneProxy()

########NEW FILE########
__FILENAME__ = dynamic
import logging
import random
import time
import sys
import contextlib
from .. import config_file

import gevent
import dpkt

from .direct import Proxy
from .http_connect import HttpConnectProxy
from .goagent import GoAgentProxy
from .shadowsocks import ShadowSocksProxy
from .http_relay import HttpRelayProxy
from .ssh import SshProxy
from .. import networking


LOGGER = logging.getLogger(__name__)


class DynamicProxy(Proxy):

    def __init__(self, dns_record, type=None, priority=0, **kwargs):
        self.dns_record = dns_record
        self.type = type
        self.delegated_to = None
        self.kwargs = {k: False if 'False' == v else v for k, v in kwargs.items()}
        super(DynamicProxy, self).__init__()
        self.priority = int(priority)

    def do_forward(self, client):
        if self.delegated_to:
            self.delegated_to.forward(client)
        else:
            raise NotImplementedError()

    def clear_latency_records(self):
        if self.delegated_to:
            self.delegated_to.clear_latency_records()


    def clear_failed_times(self):
        if self.delegated_to:
            self.delegated_to.clear_failed_times()


    @property
    def latency(self):
        if self.delegated_to:
            return self.delegated_to.latency
        else:
            return 0

    @property
    def died(self):
        if self.delegated_to:
            return self.delegated_to.died
        else:
            return False

    @died.setter
    def died(self, value):
        if self.delegated_to:
            self.delegated_to.died = value
        else:
            pass # ignore

    @property
    def flags(self):
        if self.delegated_to:
            return self.delegated_to.flags
        else:
            return ()

    @flags.setter
    def flags(self, value):
        if self.delegated_to:
            self.delegated_to.flags = value
        else:
            pass

    @classmethod
    def refresh(cls, proxies):
        greenlets = []
        for proxy in proxies:
            gevent.sleep(0.1)
            greenlets.append(gevent.spawn(resolve_proxy, proxy))
        success_count = 0
        deadline = time.time() + 30
        for greenlet in greenlets:
            try:
                timeout = deadline - time.time()
                if timeout > 0:
                    if greenlet.get(timeout=timeout):
                        success_count += 1
                else:
                    if greenlet.get(block=False):
                        success_count += 1
            except:
                pass
        LOGGER.info('resolved proxies: %s/%s' % (success_count, len(proxies)))
        success = success_count > (len(proxies) / 2)
        type_to_proxies = {}
        for proxy in proxies:
            if proxy.delegated_to:
                type_to_proxies.setdefault(proxy.delegated_to.__class__, []).append(proxy.delegated_to)
        for proxy_type, instances in type_to_proxies.items():
            try:
                success = proxy_type.refresh(instances) and success
            except:
                LOGGER.exception('failed to refresh proxies %s' % instances)
                success = False
        return success

    def is_protocol_supported(self, protocol, client=None):
        if self.delegated_to:
            return self.delegated_to.is_protocol_supported(protocol, client)
        else:
            return False

    def __eq__(self, other):
        if hasattr(other, 'dns_record'):
            return self.dns_record == other.dns_record
        else:
            return False

    def __hash__(self):
        return hash(self.dns_record)

    def __repr__(self):
        return 'DynamicProxy[%s=>%s]' % (self.dns_record, self.delegated_to or 'UNRESOLVED')

    @property
    def public_name(self):
        if 'GoAgentProxy' == self.delegated_to.__class__.__name__:
            return 'GoAgent\tPublic #%s' % self.dns_record.replace('.fqrouter.com', '').replace('goagent', '')
        elif 'ShadowSocksProxy' == self.delegated_to.__class__.__name__:
            return 'SS\tPublic #%s' % self.dns_record.replace('.fqrouter.com', '').replace('ss', '')
        elif 'HttpConnectProxy' == self.delegated_to.__class__.__name__:
            return 'HTTP\tPublic #%s' % self.dns_record.replace('.fqrouter.com', '').replace('proxy', '')
        else:
            return None # ignore

proxy_types = {
    'http-relay': HttpRelayProxy,
    'http-connect': HttpConnectProxy,
    'goagent': GoAgentProxy,
    'dynamic': DynamicProxy,
    'ss': ShadowSocksProxy,
    'ssh': SshProxy
}
try:
    from .spdy_relay import SpdyRelayProxy
    proxy_types['spdy-relay'] = SpdyRelayProxy
except:
    pass
try:
    from .spdy_connect import SpdyConnectProxy
    proxy_types['spdy-connect'] = SpdyConnectProxy
except:
    pass

def resolve_proxy(proxy):
    for i in range(3):
        try:
            dyn_props = networking.resolve_txt(proxy.dns_record)
            if not dyn_props:
                LOGGER.info('resolved empty proxy: %s' % repr(proxy))
                return False
            if len(dyn_props) == 1:
                connection_info = dyn_props[0].text[0]
                if connection_info:
                    if '=' in connection_info:
                        update_new_style_proxy(proxy, [connection_info])
                    else:
                        update_old_style_proxy(proxy, connection_info)
                else:
                    LOGGER.info('resolved empty proxy: %s' % repr(proxy))
                    return False
            else:
                update_new_style_proxy(proxy, [dyn_prop.text[0] for dyn_prop in dyn_props])
            LOGGER.info('resolved proxy: %s' % repr(proxy))
            return True
        except:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('failed to resolve proxy: %s' % repr(proxy), exc_info=1)
            else:
                LOGGER.info('failed to resolve proxy: %s %s' % (repr(proxy), sys.exc_info()[1]))
        gevent.sleep(1)
    LOGGER.error('give up resolving proxy: %s' % repr(proxy))
    return False

def update_new_style_proxy(proxy, dyn_props):
    dyn_prop_dict = {}
    for dyn_prop in dyn_props:
        key, _, value = dyn_prop.partition('=')
        if not key:
            continue
        if key in dyn_prop_dict:
            if isinstance(dyn_prop_dict[key], list):
                dyn_prop_dict[key].append(value)
            else:
                dyn_prop_dict[key] = [dyn_prop_dict[key], value]
        else:
            dyn_prop_dict[key] = value
    proxy_cls = proxy_types.get(proxy.type)
    if proxy_cls:
        proxy.delegated_to = proxy_cls(**dyn_prop_dict)
        proxy.delegated_to.resolved_by_dynamic_proxy = proxy
    else:
        pass # ignore


def update_old_style_proxy(proxy, connection_info):
    if 'goagent' == proxy.type:
        proxy.delegated_to = GoAgentProxy(connection_info, **proxy.kwargs)
        proxy.delegated_to.resolved_by_dynamic_proxy = proxy
    elif 'ss' == proxy.type:
        ip, port, password, encrypt_method = connection_info.split(':')
        proxy.delegated_to = ShadowSocksProxy(ip, port, password, encrypt_method, supported_protocol='HTTPS')
        proxy.delegated_to.resolved_by_dynamic_proxy = proxy
    else:
        proxy_type, ip, port, username, password = connection_info.split(':')
        assert 'http-connect' == proxy_type # only support one type currently
        proxy.delegated_to = HttpConnectProxy(ip, port, username, password, **proxy.kwargs)
        proxy.delegated_to.resolved_by_dynamic_proxy = proxy


########NEW FILE########
__FILENAME__ = encrypt
#!/usr/bin/env python

# Copyright (c) 2012 clowwindy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import hashlib
import string
import struct
import logging


def random_string(length):
    import M2Crypto.Rand
    return M2Crypto.Rand.rand_bytes(length)


def get_table(key):
    m = hashlib.md5()
    m.update(key)
    s = m.digest()
    (a, b) = struct.unpack('<QQ', s)
    table = [c for c in string.maketrans('', '')]
    for i in xrange(1, 1024):
        table.sort(lambda x, y: int(a % (ord(x) + i) - a % (ord(y) + i)))
    return table

tables = {}

def init_table(key):
    if key not in tables:
        encrypt_table = ''.join(get_table(key))
        decrypt_table = string.maketrans(encrypt_table, string.maketrans('', ''))
        tables[key] = (encrypt_table, decrypt_table)
    return tables[key]


def EVP_BytesToKey(password, key_len, iv_len):
    # equivalent to OpenSSL's EVP_BytesToKey() with count 1
    # so that we make the same key and iv as nodejs version
    # TODO: cache the results
    m = []
    i = 0
    while len(''.join(m)) < (key_len + iv_len):
        md5 = hashlib.md5()
        data = password
        if i > 0:
            data = m[i - 1] + password
        md5.update(data)
        m.append(md5.digest())
        i += 1
    ms = ''.join(m)
    key = ms[:key_len]
    iv = ms[key_len:key_len + iv_len]
    return (key, iv)


method_supported = {
    'aes-128-cfb': (16, 16),
    'aes-192-cfb': (24, 16),
    'aes-256-cfb': (32, 16),
    'bf-cfb': (16, 8),
    'camellia-128-cfb': (16, 16),
    'camellia-192-cfb': (24, 16),
    'camellia-256-cfb': (32, 16),
    'cast5-cfb': (16, 8),
    'des-cfb': (8, 8),
    'idea-cfb': (16, 8),
    'rc2-cfb': (8, 8),
    'rc4': (16, 0),
    'seed-cfb': (16, 16),
    }


class Encryptor(object):
    def __init__(self, key, method=None):
        if method == 'table':
            method = None
        self.key = key
        self.method = method
        self.iv = None
        self.iv_sent = False
        self.cipher_iv = ''
        self.decipher = None
        if method:
            self.cipher = self.get_cipher(key, method, 1, iv=random_string(32))
            self.encrypt_table, self.decrypt_table = None, None
        else:
            self.cipher = None
            self.encrypt_table, self.decrypt_table = init_table(key)

    def get_cipher_len(self, method):
        method = method.lower()
        m = method_supported.get(method, None)
        return m

    def iv_len(self):
        return len(self.cipher_iv)

    def get_cipher(self, password, method, op, iv=None):
        import M2Crypto.EVP
        password = password.encode('utf-8')
        method = method.lower()
        m = self.get_cipher_len(method)
        if m:
            key, iv_ = EVP_BytesToKey(password, m[0], m[1])
            if iv is None:
                iv = iv_[:m[1]]
            if op == 1:
                self.cipher_iv = iv[:m[1]]  # this iv is for cipher, not decipher
            return M2Crypto.EVP.Cipher(method.replace('-', '_'), key, iv, op, key_as_bytes=0, d='md5', salt=None, i=1, padding=1)

        logging.error('method %s not supported' % method)
        sys.exit(1)

    def encrypt(self, buf):
        if len(buf) == 0:
            return buf
        if self.cipher:
            if self.iv_sent:
                return self.cipher.update(buf)
            else:
                self.iv_sent = True
                return self.cipher_iv + self.cipher.update(buf)
        else:
            return string.translate(buf, self.encrypt_table)

    def decrypt(self, buf):
        if len(buf) == 0:
            return buf
        if self.cipher:
            if self.decipher is None:
                decipher_iv_len = self.get_cipher_len(self.method)[1]
                decipher_iv = buf[:decipher_iv_len]
                self.decipher = self.get_cipher(self.key, self.method, 0, iv=decipher_iv)
                buf = buf[decipher_iv_len:]
                if len(buf) == 0:
                    return buf
            return self.decipher.update(buf)
        else:
            return string.translate(buf, self.decrypt_table)
########NEW FILE########
__FILENAME__ = goagent
# thanks @phuslu modified from https://github.com/goagent/goagent/blob/2.0/local/proxy.py
# coding:utf-8
import logging
import socket
import time
import sys
import re
import functools
import fnmatch
import urllib
import httplib
import random
import contextlib
import zlib
import struct
import io
import copy
import threading
import base64
from .. import config_file

import ssl
import gevent.queue

from .. import networking
from .. import stat
from .direct import to_bool
from .direct import Proxy
from .http_try import recv_and_parse_request, NotHttp
from .http_try import CapturingSock
from .http_try import HttpTryProxy
from Crypto.Cipher.ARC4 import new as _Crypto_Cipher_ARC4_new


try:
    import urllib.request
    import urllib.parse
except ImportError:
    import urllib

    urllib.request = __import__('urllib2')
    urllib.parse = __import__('urlparse')

try:
    import queue
except ImportError:
    import Queue as queue

try:
    import http.server
    import http.client
except ImportError:
    http = type(sys)('http')
    http.server = __import__('BaseHTTPServer')
    http.client = __import__('httplib')
    http.client.parse_headers = http.client.HTTPMessage

LOGGER = logging.getLogger(__name__)

RE_VERSION = re.compile(r'\d+\.\d+\.\d+')
SKIP_HEADERS = frozenset(
    ['Vary', 'Via', 'X-Forwarded-For', 'Proxy-Authorization', 'Proxy-Connection', 'Upgrade', 'X-Chrome-Variations',
     'Connection', 'Cache-Control'])
ABBV_HEADERS = {'Accept': ('A', lambda x: '*/*' in x),
                'Accept-Charset': ('AC', lambda x: x.startswith('UTF-8,')),
                'Accept-Language': ('AL', lambda x: x.startswith('zh-CN')),
                'Accept-Encoding': ('AE', lambda x: x.startswith('gzip,')), }
GAE_OBFUSCATE = 0
GAE_PASSWORD = ''
GAE_PATH = '/2'

AUTORANGE_HOSTS = (
    '*.c.youtube.com',
    '*.atm.youku.com',
    '*.googlevideo.com',
    'av.vimeo.com',
    'smile-*.nicovideo.jp',
    'video.*.fbcdn.net',
    's*.last.fm',
    'x*.last.fm',
    '*.x.xvideos.com',
    'cdn*.pornhub.com',
    '*.edgecastcdn.net',
    '*.d.rncdn3.com',
    'cdn*.public.tube8.com',
    '*.redtubefiles.com',
    '*.mms.vlog.xuite.net',
    'vs*.thisav.com',
    'archive.rthk.hk',
    'video*.modimovie.com')
AUTORANGE_HOSTS_MATCH = [re.compile(fnmatch.translate(h)).match for h in AUTORANGE_HOSTS]
AUTORANGE_ENDSWITH = '.f4v|.flv|.hlv|.m4v|.mp4|.mp3|.ogg|.avi|.exe|.zip|.iso|.rar|.bz2|.xz|.dmg'.split('|')
AUTORANGE_ENDSWITH = tuple(AUTORANGE_ENDSWITH)
AUTORANGE_NOENDSWITH = '.xml|.json|.html|.php|.py.js|.css|.jpg|.jpeg|.png|.gif|.ico'.split('|')
AUTORANGE_NOENDSWITH = tuple(AUTORANGE_NOENDSWITH)
AUTORANGE_MAXSIZE = 1048576
AUTORANGE_WAITSIZE = 524288
AUTORANGE_BUFSIZE = 8192
AUTORANGE_THREADS = 3
SKIP_HEADERS = frozenset(['Vary', 'Via', 'X-Forwarded-For', 'Proxy-Authorization', 'Proxy-Connection',
                          'Upgrade', 'X-Chrome-Variations', 'Connection', 'Cache-Control'])

normcookie = functools.partial(re.compile(', ([^ =]+(?:=|$))').sub, '\\r\\nSet-Cookie: \\1')


class GoAgentProxy(Proxy):
    global_gray_list = set()
    global_black_list = set()
    google_ip_failed_times = {}
    google_ip_latency_records = {}

    GOOGLE_HOSTS = ['www.g.cn', 'www.google.cn', 'www.google.com', 'mail.google.com']
    GOOGLE_IPS = []
    proxies = []

    def __init__(self, appid, path='/2', password='', is_rc4_enabled=False, is_obfuscate_enabled=False,
                 whitelist_host=(), blacklist_host=(), group='default', **ignore):
        super(GoAgentProxy, self).__init__()
        assert appid
        self.appid = appid
        self.path = path or '/2'
        self.password = password
        self.is_rc4_enabled = to_bool(is_rc4_enabled)
        self.is_obfuscate_enabled = to_bool(is_obfuscate_enabled)
        self.version = 'UNKNOWN'
        self.whitelist_host = whitelist_host if isinstance(whitelist_host, (list, tuple)) else [whitelist_host]
        self.blacklist_host = list(blacklist_host) if isinstance(blacklist_host, (list, tuple)) else [blacklist_host]
        self.blacklist_host.append('.c.android.clients.google.com')
        self.blacklist_host.append('.c.pack.google.com')
        self.group = group

    @property
    def fetch_server(self):
        return 'https://%s.appspot.com%s?' % (self.appid, self.path)

    def query_version(self):
        try:
            ssl_sock = create_ssl_connection()
            with contextlib.closing(ssl_sock):
                with contextlib.closing(ssl_sock.sock):
                    ssl_sock.settimeout(5)
                    ssl_sock.sendall('GET https://%s.appspot.com/2 HTTP/1.1\r\n\r\n\r\n' % self.appid)
                    response = ssl_sock.recv(8192)
                    match = RE_VERSION.search(response)
                    if 'Over Quota' in response:
                        self.died = True
                        LOGGER.info('%s over quota' % self)
                        return
                    if match:
                        self.version = match.group(0)
                        LOGGER.info('queried appid version: %s' % self)
                    else:
                        LOGGER.info('failed to query appid version %s: %s' % (self.appid, response))
        except:
            LOGGER.exception('failed to query goagent %s version' % self.appid)

    def do_forward(self, client):
        try:
            if not recv_and_parse_request(client):
                raise Exception('payload is too large')
            if client.method.upper() not in ('GET', 'POST', 'HEAD'):
                raise Exception('unsupported method: %s' % client.method)
            if client.host in GoAgentProxy.global_black_list:
                raise Exception('%s failed to proxy via goagent before' % client.host)
        except NotHttp:
            raise
        except:
            for proxy in self.proxies:
                client.tried_proxies[proxy] = 'skip goagent'
            LOGGER.error('[%s] failed to recv and parse request: %s' % (repr(client), sys.exc_info()[1]))
            client.fall_back(reason='failed to recv and parse request, %s' % sys.exc_info()[1])
        forward(client, self)

    def is_protocol_supported(self, protocol, client=None):
        if 'HTTP' != protocol:
            return False
        if client:
            if self.whitelist_host:
                for whitelist_host in self.whitelist_host:
                    if whitelist_host in client.host:
                        return True
                return False
            if self.blacklist_host:
                for blacklist_host in self.blacklist_host:
                    if blacklist_host in client.host:
                        return False
                return True
        return True

    @classmethod
    def refresh(cls, proxies):
        cls.proxies = proxies
        resolved_google_ips = cls.resolve_google_ips()
        if resolved_google_ips:
            for proxy in proxies:
                proxy.died = False
                gevent.spawn(proxy.query_version)
        else:
            for proxy in proxies:
                proxy.died = not resolved_google_ips
        return resolved_google_ips

    @classmethod
    def resolve_google_ips(cls):
        if cls.GOOGLE_IPS:
            return True
        LOGGER.info('resolving google ips from %s' % cls.GOOGLE_HOSTS)
        all_ips = set()
        for host in cls.GOOGLE_HOSTS:
            if re.match(r'\d+\.\d+\.\d+\.\d+', host):
                all_ips.add(host)
            else:
                ips = networking.resolve_ips(host)
                LOGGER.info('%s => %s' % (host, ips))
                if len(ips) > 1:
                    all_ips |= set(ips)
        if not all_ips:
            LOGGER.fatal('failed to resolve google ip')
            return False
        cls.GOOGLE_IPS = list(all_ips)
        random.shuffle(cls.GOOGLE_IPS)
        return True

    def __repr__(self):
        return 'GoAgentProxy[%s ver %s]' % (self.appid, self.version)

    @property
    def public_name(self):
        return 'GoAgent\t%s' % self.appid


def forward(client, proxy):
    parsed_url = urllib.parse.urlparse(client.url)
    range_in_query = 'range=' in parsed_url.query or 'redirect_counter=' in parsed_url.query
    special_range = (any(x(client.host) for x in AUTORANGE_HOSTS_MATCH) or client.url.endswith(
        AUTORANGE_ENDSWITH)) and not client.url.endswith(
        AUTORANGE_NOENDSWITH) and not 'redirector.c.youtube.com' == client.host
    if client.host in GoAgentProxy.global_gray_list:
        special_range = True
    range_end = 0
    auto_ranged = False
    if 'Range' in client.headers:
        LOGGER.info('[%s] range present: %s' % (repr(client), client.headers['Range']))
        m = re.search('bytes=(\d+)-(\d*)', client.headers['Range'])
        if m:
            range_start = int(m.group(1))
            range_end = int(m.group(2)) if m.group(2) else 0
            if not range_end or range_end - range_start > AUTORANGE_MAXSIZE:
                client.headers['Range'] = 'bytes=%d-%d' % (range_start, range_start + AUTORANGE_MAXSIZE)
                LOGGER.info('[%s] adjusted range: %s' % (repr(client), client.headers['Range']))
    elif not range_in_query and special_range:
        client.headers['Range'] = 'bytes=%d-%d' % (0, AUTORANGE_MAXSIZE)
        auto_ranged = True
        LOGGER.info('[%s] auto range: %s' % (repr(client), client.headers['Range']))
    response = None
    try:
        try:
            response = gae_urlfetch(
                client, proxy, client.method, client.url, client.headers, client.payload,
                password=proxy.password,
                is_obfuscate_enabled=proxy.is_obfuscate_enabled,
                is_rc4_enabled=proxy.is_rc4_enabled)
        except ConnectionFailed:
            for proxy in GoAgentProxy.proxies:
                client.tried_proxies[proxy] = 'skip goagent'
            client.fall_back('can not connect to google ip')
        except ReadResponseFailed:
            if 'youtube.com' not in client.host and 'googlevideo.com' not in client.host:
                GoAgentProxy.global_gray_list.add(client.host)
                if auto_ranged:
                    LOGGER.error('[%s] !!! blacklist goagent for %s !!!' % (repr(client), client.host))
                    GoAgentProxy.global_black_list.add(client.host)
                    if client.host in HttpTryProxy.host_slow_list:
                        HttpTryProxy.host_slow_list.remove(client.host)
            for proxy in GoAgentProxy.proxies:
                client.tried_proxies[proxy] = 'skip goagent'
            client.fall_back(reason='failed to read response from gae_urlfetch')
        if response is None:
            client.fall_back('urlfetch empty response')
        if response.app_status == 503:
            LOGGER.error('%s died due to 503' % proxy)
            proxy.died = True
            client.fall_back('goagent server over quota')
        if response.app_status == 500:
            # LOGGER.error('%s died due to 500' % proxy)
            # proxy.died = True
            client.fall_back('goagent server busy')
        if response.app_status == 404:
            LOGGER.error('%s died due to 404' % proxy)
            proxy.died = True
            client.fall_back('goagent server not found')
        if response.app_status == 302:
            LOGGER.error('%s died due to 302' % proxy)
            proxy.died = True
            client.fall_back('goagent server 302 moved')
        if response.app_status == 403:
            # LOGGER.error('%s died due to 403' % proxy)
            # proxy.died = True
            client.fall_back('goagent server %s banned this host' % proxy)
        if response.app_status != 200:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('HTTP/1.1 %s\r\n%s\r\n' % (response.status, ''.join(
                    '%s: %s\r\n' % (k.title(), v) for k, v in response.getheaders() if k != 'transfer-encoding')))
                LOGGER.debug(response.read())
            client.fall_back('urlfetch failed: %s' % response.app_status)
        client.forward_started = True
        if response.status == 206:
            LOGGER.info('[%s] start range fetch' % repr(client))
            rangefetch = RangeFetch(client, range_end, auto_ranged, response)
            return rangefetch.fetch()
        if 'Set-Cookie' in response.msg:
            response.msg['Set-Cookie'] = normcookie(response.msg['Set-Cookie'])
        client.downstream_wfile.write('HTTP/1.1 %s\r\n%s\r\n' % (response.status, ''.join(
            '%s: %s\r\n' % (k.title(), v) for k, v in response.getheaders() if k != 'transfer-encoding')))
        content_length = int(response.getheader('Content-Length', 0))
        content_range = response.getheader('Content-Range', '')
        if content_range:
            start, end, length = list(map(int, re.search(r'bytes (\d+)-(\d+)/(\d+)', content_range).group(1, 2, 3)))
        else:
            start, end, length = 0, content_length - 1, content_length
        while 1:
            try:
                data = response.read(8192)
                response.ssl_sock.counter.received(len(response.counted_sock.rfile.captured))
                response.counted_sock.rfile.captured = ''
            except httplib.IncompleteRead as e:
                LOGGER.error('incomplete read: %s' % e.partial)
                raise
            if not data:
                response.close()
                return
            start += len(data)
            client.downstream_wfile.write(data)
            if start >= end:
                response.close()
                return
    finally:
        if response:
            response.close()


def _create_ssl_connection(ip, port):
    sock = None
    ssl_sock = None
    try:
        sock = networking.create_tcp_socket(ip, port, 2)
        ssl_sock = ssl.wrap_socket(sock, do_handshake_on_connect=False)
        ssl_sock.settimeout(2)
        ssl_sock.do_handshake()
        ssl_sock.sock = sock
        return ssl_sock
    except:
        if ssl_sock:
            ssl_sock.close()
        if sock:
            sock.close()
        return None


def create_ssl_connection():
    for i in range(3):
        google_ip = pick_best_google_ip()
        started_at = time.time()
        ssl_sock = _create_ssl_connection(google_ip, 443)
        if ssl_sock:
            record_google_ip_latency(google_ip, time.time() - started_at)
            ssl_sock.google_ip = google_ip
            return ssl_sock
        else:
            LOGGER.error('!!! failed to connect google ip %s !!!' % google_ip)
            GoAgentProxy.google_ip_failed_times[google_ip] = GoAgentProxy.google_ip_failed_times.get(google_ip, 0) + 1
            gevent.sleep(0.1)
    raise ConnectionFailed()


def pick_best_google_ip():
    random.shuffle(GoAgentProxy.GOOGLE_IPS)
    google_ips = sorted(GoAgentProxy.GOOGLE_IPS, key=lambda ip: GoAgentProxy.google_ip_failed_times.get(ip, 0))[:3]
    return sorted(google_ips, key=lambda ip: get_google_ip_latency(ip))[0]


def get_google_ip_latency(google_ip):
    if google_ip in GoAgentProxy.google_ip_latency_records:
        total_elapsed_seconds, times = GoAgentProxy.google_ip_latency_records[google_ip]
        return total_elapsed_seconds / times
    else:
        return 0


def record_google_ip_latency(google_ip, elapsed_seconds):
    if google_ip in GoAgentProxy.google_ip_latency_records:
        total_elapsed_seconds, times = GoAgentProxy.google_ip_latency_records[google_ip]
        total_elapsed_seconds += elapsed_seconds
        times += 1
        if times > 100:
            total_elapsed_seconds = total_elapsed_seconds / times
            times = 1
        GoAgentProxy.google_ip_latency_records[google_ip] = (total_elapsed_seconds, times)
    else:
        GoAgentProxy.google_ip_latency_records[google_ip] = (elapsed_seconds, 1)


class ConnectionFailed(Exception):
    pass


def http_call(ssl_sock, method, path, headers, payload):
    ssl_sock.settimeout(15)
    request_data = ''
    request_data += '%s %s HTTP/1.1\r\n' % (method, path)
    request_data += ''.join('%s: %s\r\n' % (k, v) for k, v in headers.items() if k not in SKIP_HEADERS)
    request_data += '\r\n'
    request_data = request_data.encode() + payload
    ssl_sock.counter.sending(len(request_data))
    ssl_sock.sendall(request_data)
    rfile = None
    counted_sock = None
    try:
        rfile = ssl_sock.makefile('rb', 0)
        counted_sock = CountedSock(rfile, ssl_sock.counter)
        response = http.client.HTTPResponse(counted_sock)
        response.ssl_sock = ssl_sock
        response.rfile = rfile
        response.counted_sock = counted_sock
        try:
            response.begin()
        except http.client.BadStatusLine:
            response = None
        ssl_sock.counter.received(len(counted_sock.rfile.captured))
        counted_sock.rfile.captured = ''
        return response
    except:
        for res in [ssl_sock, ssl_sock.sock, rfile, counted_sock]:
            try:
                if res:
                    res.close()
            except:
                pass
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.exception('failed to read goagent response')
        else:
            LOGGER.error('failed to read goagent response: %s' % sys.exc_info()[1])
        raise ReadResponseFailed()


class CountedSock(CapturingSock):
    def __init__(self, rfile, counter):
        super(CountedSock, self).__init__(rfile)
        self.counter = counter

    def close(self):
        self.counter.received(len(self.rfile.captured))


class ReadResponseFailed(Exception):
    pass


def gae_urlfetch(client, proxy, method, url, headers, payload,
                 password=None, is_obfuscate_enabled=False, is_rc4_enabled=False):
    if payload:
        if len(payload) < 10 * 1024 * 1024 and 'Content-Encoding' not in headers:
            zpayload = zlib.compress(payload)[2:-4]
            if len(zpayload) < len(payload):
                payload = zpayload
                headers['Content-Encoding'] = 'deflate'
        headers['Content-Length'] = str(len(payload))
        # GAE donot allow set `Host` header
    if 'Host' in headers:
        del headers['Host']
    metadata = 'G-Method:%s\nG-Url:%s\n' % (method, url)
    if password:
        metadata += 'G-password:%s\n' % password
    metadata += ''.join('%s:%s\n' % (k.title(), v) for k, v in headers.items() if k not in SKIP_HEADERS)
    metadata = metadata.encode('utf8')
    request_method = 'POST'
    request_headers = {}
    if is_obfuscate_enabled:
        if is_rc4_enabled:
            request_headers['X-GOA-Options'] = 'rc4'
            cookie = base64.b64encode(rc4crypt(zlib.compress(metadata)[2:-4], password)).strip()
            payload = rc4crypt(payload, password)
        else:
            cookie = base64.b64encode(zlib.compress(metadata)[2:-4]).strip()
        request_headers['Cookie'] = cookie
        if payload:
            request_headers['Content-Length'] = str(len(payload))
        else:
            request_method = 'GET'
    else:
        metadata = zlib.compress(metadata)[2:-4]
        payload = '%s%s%s' % (struct.pack('!h', len(metadata)), metadata, payload)
        if is_rc4_enabled:
            request_headers['X-GOA-Options'] = 'rc4'
            payload = rc4crypt(payload, password)
        request_headers['Content-Length'] = str(len(payload))
    ssl_sock = create_ssl_connection()
    ssl_sock.counter = stat.opened(ssl_sock, proxy, host=client.host, ip=client.dst_ip)
    LOGGER.info('[%s] urlfetch %s %s via %s %0.2f'
                % (repr(client), method, url, ssl_sock.google_ip, get_google_ip_latency(ssl_sock.google_ip)))
    client.add_resource(ssl_sock)
    client.add_resource(ssl_sock.counter)
    client.add_resource(ssl_sock.sock)
    response = http_call(ssl_sock, request_method, proxy.fetch_server, request_headers, payload)
    client.add_resource(response.rfile)
    client.add_resource(response.counted_sock)
    response.app_status = response.status
    response.app_options = response.getheader('X-GOA-Options', '')
    if response.status != 200:
        return response
    data = response.read(4)
    if len(data) < 4:
        response.status = 502
        response.fp = io.BytesIO(b'connection aborted. too short leadtype data=' + data)
        response.read = response.fp.read
        return response
    response.status, headers_length = struct.unpack('!hh', data)
    data = response.read(headers_length)
    if len(data) < headers_length:
        response.status = 502
        response.fp = io.BytesIO(b'connection aborted. too short headers data=' + data)
        response.read = response.fp.read
        return response
    if 'rc4' not in response.app_options:
        response.msg = httplib.HTTPMessage(io.BytesIO(zlib.decompress(data, -zlib.MAX_WBITS)))
    else:
        response.msg = httplib.HTTPMessage(io.BytesIO(zlib.decompress(rc4crypt(data, password), -zlib.MAX_WBITS)))
        if password and response.fp:
            response.fp = RC4FileObject(response.fp, password)
    return response


class RangeFetch(object):
    def __init__(self, client, range_end, auto_ranged, response):
        self.client = client
        self.range_end = range_end
        self.auto_ranged = auto_ranged
        self.wfile = client.downstream_wfile
        self.response = response
        self.command = client.method
        self.url = client.url
        self.headers = client.headers
        self.payload = client.payload
        self._stopped = None

    def fetch(self):
        response_status = self.response.status
        response_headers = dict((k.title(), v) for k, v in self.response.getheaders())
        content_range = response_headers['Content-Range']
        LOGGER.info('auto ranged: %s' % self.auto_ranged)
        LOGGER.info('original response: %s' % content_range)
        #content_length = response_headers['Content-Length']
        start, end, length = list(map(int, re.search(r'bytes (\d+)-(\d+)/(\d+)', content_range).group(1, 2, 3)))
        if self.auto_ranged:
            response_status = 200
            response_headers.pop('Content-Range', None)
            response_headers['Content-Length'] = str(length)
        else:
            if self.range_end:
                response_headers['Content-Range'] = 'bytes %s-%s/%s' % (start, self.range_end, length)
                response_headers['Content-Length'] = str(self.range_end - start + 1)
            else:
                response_headers['Content-Range'] = 'bytes %s-%s/%s' % (start, length - 1, length)
                response_headers['Content-Length'] = str(length - start)

        if self.range_end:
            LOGGER.info('>>>>>>>>>>>>>>> RangeFetch started(%r) %d-%d', self.url, start, self.range_end)
        else:
            LOGGER.info('>>>>>>>>>>>>>>> RangeFetch started(%r) %d-end', self.url, start)
        general_resposne = ('HTTP/1.1 %s\r\n%s\r\n' % (
        response_status, ''.join('%s: %s\r\n' % (k, v) for k, v in response_headers.items()))).encode()
        LOGGER.info(general_resposne)
        self.wfile.write(general_resposne)

        data_queue = gevent.queue.PriorityQueue()
        range_queue = gevent.queue.PriorityQueue()
        range_queue.put((start, end, self.response))
        for begin in range(end + 1, self.range_end + 1 if self.range_end else length, AUTORANGE_MAXSIZE):
            range_queue.put((begin, min(begin + AUTORANGE_MAXSIZE - 1, length - 1), None))
        for i in range(AUTORANGE_THREADS):
            gevent.spawn(self.__fetchlet, range_queue, data_queue)
        has_peek = hasattr(data_queue, 'peek')
        peek_timeout = 90
        expect_begin = start
        while expect_begin < (self.range_end or (length - 1)):
            try:
                if has_peek:
                    begin, data = data_queue.peek(timeout=peek_timeout)
                    if expect_begin == begin:
                        data_queue.get()
                    elif expect_begin < begin:
                        gevent.sleep(0.1)
                        continue
                    else:
                        LOGGER.error('RangeFetch Error: begin(%r) < expect_begin(%r), quit.', begin, expect_begin)
                        break
                else:
                    begin, data = data_queue.get(timeout=peek_timeout)
                    if expect_begin == begin:
                        pass
                    elif expect_begin < begin:
                        data_queue.put((begin, data))
                        gevent.sleep(0.1)
                        continue
                    else:
                        LOGGER.error('RangeFetch Error: begin(%r) < expect_begin(%r), quit.', begin, expect_begin)
                        break
            except queue.Empty:
                LOGGER.error('data_queue peek timeout, break')
                break
            try:
                self.wfile.write(data)
                expect_begin += len(data)
            except (socket.error, ssl.SSLError, OSError) as e:
                LOGGER.info('RangeFetch client connection aborted(%s).', e)
                break
        self._stopped = True

    def __fetchlet(self, range_queue, data_queue):
        headers = copy.copy(self.headers)
        headers['Connection'] = 'close'
        while 1:
            try:
                if self._stopped:
                    return
                if data_queue.qsize() * AUTORANGE_BUFSIZE > 180 * 1024 * 1024:
                    gevent.sleep(10)
                    continue
                proxy = None
                try:
                    start, end, response = range_queue.get(timeout=1)
                    headers['Range'] = 'bytes=%d-%d' % (start, end)
                    if not response:
                        not_died_proxies = [p for p in GoAgentProxy.proxies if not p.died and p.is_protocol_supported('HTTP', self.client)]
                        if not not_died_proxies:
                            self._stopped = True
                            return
                        proxy = random.choice(not_died_proxies)
                        response = gae_urlfetch(
                            self.client, proxy, self.command, self.url, headers, self.payload)
                except queue.Empty:
                    continue
                except (socket.error, ssl.SSLError, OSError, ConnectionFailed, ReadResponseFailed) as e:
                    LOGGER.warning("Response %r in __fetchlet", e)
                if not response:
                    LOGGER.warning('RangeFetch %s return %r', headers['Range'], response)
                    range_queue.put((start, end, None))
                    continue
                if response.app_status != 200:
                    LOGGER.warning('Range Fetch "%s %s" %s return %s via %s', self.command, self.url, headers['Range'],
                                   response.app_status, proxy.appid)
                    response.close()
                    range_queue.put((start, end, None))
                    if proxy and response.app_status not in (500, 403): # server busy or appid banned the host
                        LOGGER.error('%s died due to app status not 200' % proxy)
                        proxy.died = True
                    continue
                if response.getheader('Location'):
                    self.url = response.getheader('Location')
                    LOGGER.info('RangeFetch Redirect(%r)', self.url)
                    response.close()
                    range_queue.put((start, end, None))
                    continue
                if 200 <= response.status < 300:
                    content_range = response.getheader('Content-Range')
                    if not content_range:
                        LOGGER.warning('RangeFetch "%s %s" return Content-Range=%r: response headers=%r', self.command,
                                       self.url, content_range, response.getheaders())
                        response.close()
                        range_queue.put((start, end, None))
                        continue
                    content_length = int(response.getheader('Content-Length', 0))
                    LOGGER.info('>>>>>>>>>>>>>>> [thread %s] %s %s', threading.currentThread().ident, content_length,
                                content_range)
                    while 1:
                        try:
                            data = response.read(AUTORANGE_BUFSIZE)
                            response.ssl_sock.counter.received(len(response.counted_sock.rfile.captured))
                            response.counted_sock.rfile.captured = ''
                            if not data:
                                break
                            data_queue.put((start, data))
                            start += len(data)
                        except (socket.error, ssl.SSLError, OSError) as e:
                            LOGGER.warning('RangeFetch "%s %s" %s failed: %s', self.command, self.url, headers['Range'],
                                           e)
                            break
                    if start < end:
                        LOGGER.warning('RangeFetch "%s %s" retry %s-%s', self.command, self.url, start, end)
                        response.close()
                        range_queue.put((start, end, None))
                        continue
                else:
                    LOGGER.error('RangeFetch %r return %s', self.url, response.status)
                    response.close()
                    range_queue.put((start, end, None))
                    continue
            except Exception as e:
                LOGGER.exception('RangeFetch._fetchlet error:%s', e)
                raise



def rc4crypt(data, key):
    return _Crypto_Cipher_ARC4_new(key).encrypt(data) if key else data


class RC4FileObject(object):
    """fileobj for rc4"""
    def __init__(self, stream, key):
        self.__stream = stream
        self.__cipher = _Crypto_Cipher_ARC4_new(key) if key else lambda x:x
    def __getattr__(self, attr):
        if attr not in ('__stream', '__cipher'):
            return getattr(self.__stream, attr)
    def read(self, size=-1):
        return self.__cipher.encrypt(self.__stream.read(size))
########NEW FILE########
__FILENAME__ = google_http_try
from .http_try import HttpTryProxy
from .http_try import NotHttp
from .http_try import try_receive_response_body
from .http_try import try_receive_response_header
from .. import networking
import logging
import ssl
import socket
import httplib
import gevent

LOGGER = logging.getLogger(__name__)

class HttpsEnforcer(HttpTryProxy):
    def get_or_create_upstream_sock(self, client):
        LOGGER.info('[%s] force https: %s' % (repr(client), client.url))
        upstream_sock = client.create_tcp_socket(client.dst_ip, 443, 3)
        old_counter = upstream_sock.counter
        upstream_sock = ssl.wrap_socket(upstream_sock)
        upstream_sock.counter = old_counter
        return upstream_sock

    def process_response(self, client, upstream_sock, response, http_response):
        if http_response:
            if httplib.FORBIDDEN == http_response.status:
                client.fall_back(reason='403 forbidden')
            if httplib.NOT_FOUND == http_response.status:
                client.fall_back(reason='404 not found')
        return super(HttpsEnforcer, self).process_response(client, upstream_sock, response, http_response)

    def forward_upstream_sock(self, client, http_response, upstream_sock):
        client.forward(upstream_sock)

    def is_protocol_supported(self, protocol, client=None):
        if not super(HttpsEnforcer, self).is_protocol_supported(protocol, client):
            return False
        if not is_blocked_google_host(client.host):
            return False
        return True

    def __repr__(self):
        return 'HttpsEnforcer'


class GoogleScrambler(HttpTryProxy):

    def before_send_request(self, client, upstream_sock, is_payload_complete):
        client.google_scrambler_hacked = is_payload_complete
        if client.google_scrambler_hacked:
            if 'Referer' in client.headers:
                del client.headers['Referer']
            LOGGER.info('[%s] scramble google traffic' % repr(client))
            return 'GET http://www.google.com/ncr HTTP/1.1\r\n\r\n\r\n'
        return ''

    def forward_upstream_sock(self, client, http_response, upstream_sock):
        if client.google_scrambler_hacked:
            client.forward(upstream_sock) # google will 400 error if keep-alive and scrambling
        else:
            super(GoogleScrambler, self).forward_upstream_sock(client, http_response, upstream_sock)

    def after_send_request(self, client, upstream_sock):
        google_scrambler_hacked = getattr(client, 'google_scrambler_hacked', False)
        if google_scrambler_hacked:
            try_receive_response_body(try_receive_response_header(client, upstream_sock), reads_all=True)

    def process_response(self, client, upstream_sock, response, http_response):
        google_scrambler_hacked = getattr(client, 'google_scrambler_hacked', False)
        if not google_scrambler_hacked:
            return response
        if len(response) < 10:
            client.fall_back('response is too small: %s' % response)
        if http_response:
            if httplib.FORBIDDEN == http_response.status:
                client.fall_back(reason='403 forbidden')
            if httplib.NOT_FOUND == http_response.status:
                client.fall_back(reason='404 not found')
            if http_response.content_length \
                and httplib.PARTIAL_CONTENT != http_response.status \
                and 0 < http_response.content_length < 10:
                client.fall_back('content length is too small: %s' % http_response.msg.dict)
        return response

    def is_protocol_supported(self, protocol, client=None):
        if not super(GoogleScrambler, self).is_protocol_supported(protocol, client):
            return False
        if not is_blocked_google_host(client.host):
            return False
        return True

    def __repr__(self):
        return 'GoogleScrambler'

GOOGLE_SCRAMBLER = GoogleScrambler()
HTTPS_ENFORCER = HttpsEnforcer()

def is_blocked_google_host(client_host):
    if not client_host:
        return False
    return 'youtube.com' in client_host or 'ytimg.com' in client_host or 'googlevideo.com' in client_host

########NEW FILE########
__FILENAME__ = https_try
from .direct import DirectProxy
from .. import ip_substitution
import logging
import gevent
import time
import sys

LOGGER = logging.getLogger(__name__)


class HttpsTryProxy(DirectProxy):

    INITIAL_TIMEOUT = 1

    def __init__(self):
        super(HttpsTryProxy, self).__init__()
        self.timeout = HttpsTryProxy.INITIAL_TIMEOUT
        self.slow_ip_list = set()
        self.dst_black_list = {}

    def do_forward(self, client):
        dst = (client.dst_ip, client.dst_port)
        try:
            super(HttpsTryProxy, self).do_forward(client)
            if dst in self.dst_black_list:
                LOGGER.error('HttpsTryProxy removed dst %s:%s from blacklist' % dst)
                del self.dst_black_list[dst]
        except client.ProxyFallBack:
            if dst not in self.dst_black_list:
                LOGGER.error('HttpsTryProxy blacklist dst %s:%s' % dst)
            self.dst_black_list[dst] = self.dst_black_list.get(dst, 0) + 1
            raise

    def create_upstream_sock(self, client):
        success, upstream_sock = gevent.spawn(self.try_connect, client).get(timeout=self.timeout)
        if not success:
            raise upstream_sock
        return upstream_sock

    def try_connect(self, client):
        try:
            begin_time = time.time()
            upstream_sock = client.create_tcp_socket(
                client.dst_ip, client.dst_port,
                connect_timeout=max(5, HTTPS_TRY_PROXY.timeout * 2))
            elapsed_seconds = time.time() - begin_time
            if elapsed_seconds > self.timeout:
                self.slow_ip_list.add(client.dst_ip)
                self.dst_black_list.clear()
                if len(self.slow_ip_list) > 3:
                    LOGGER.critical('!!! increase http timeout %s=>%s' % (self.timeout, self.timeout + 1))
                    self.timeout += 1
                    self.slow_ip_list.clear()
            return True, upstream_sock
        except:
            return False, sys.exc_info()[1]

    def is_protocol_supported(self, protocol, client=None):
        if self.died:
            return False
        if client and self in client.tried_proxies:
            return False
        dst = (client.dst_ip, client.dst_port)
        if self.dst_black_list.get(dst, 0) % 16:
            if ip_substitution.substitute_ip(client, self.dst_black_list):
                return True
            self.dst_black_list[dst] = self.dst_black_list.get(dst, 0) + 1
            return False
        return 'HTTPS' == protocol

    def __repr__(self):
        return 'HttpsTryProxy'


HTTPS_TRY_PROXY = HttpsTryProxy()


########NEW FILE########
__FILENAME__ = http_connect
import logging
import re
import sys
import base64
import socket
import time

import ssl

from .direct import to_bool
from .direct import Proxy
from .http_try import recv_till_double_newline


LOGGER = logging.getLogger(__name__)

RE_STATUS = re.compile(r'HTTP/1.\d (\d+) ')


class HttpConnectProxy(Proxy):
    def __init__(self, proxy_host, proxy_port, username=None, password=None, is_secured=False, priority=0, **ignore):
        super(HttpConnectProxy, self).__init__()
        self.proxy_host = proxy_host
        if not self.proxy_host:
            self.died = True
        self.proxy_port = int(proxy_port)
        self.username = username
        self.password = password
        self.failed_times = 0
        self.is_secured = to_bool(is_secured)
        self.priority = int(priority)

    def do_forward(self, client):
        LOGGER.info('[%s] http connect %s:%s' % (repr(client), self.proxy_ip, self.proxy_port))
        begin_at = time.time()
        try:
            upstream_sock = client.create_tcp_socket(self.proxy_ip, self.proxy_port, 3)
            if self.is_secured:
                counter = upstream_sock.counter
                upstream_sock = ssl.wrap_socket(upstream_sock)
                upstream_sock.counter = counter
                client.add_resource(upstream_sock)
        except:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('[%s] http-connect upstream socket connect timed out' % (repr(client)), exc_info=1)
            return client.fall_back(
                reason='http-connect upstream socket connect timed out',
                delayed_penalty=self.increase_failed_time)
        upstream_sock.settimeout(3)
        upstream_sock.sendall('CONNECT %s:%s HTTP/1.0\r\n' % (client.dst_ip, client.dst_port))
        if self.username and self.password:
            auth = base64.b64encode('%s:%s' % (self.username, self.password)).strip()
            upstream_sock.sendall('Proxy-Authorization: Basic %s\r\n' % auth)
        upstream_sock.sendall('\r\n')
        try:
            response, _ = recv_till_double_newline('', upstream_sock)
        except socket.timeout:
            return client.fall_back(
                reason='http-connect upstream connect command timed out',
                delayed_penalty=self.increase_failed_time)
        except:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('[%s] http-connect upstream connect command failed' % (repr(client)), exc_info=1)
            return client.fall_back(
                reason='http-connect upstream connect command failed: %s,%s'
                       % (sys.exc_info()[0], sys.exc_info()[1]),
                delayed_penalty=self.increase_failed_time)
        match = RE_STATUS.search(response)
        if match and '200' == match.group(1):
            self.record_latency(time.time() - begin_at)
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('[%s] upstream connected' % repr(client))
            upstream_sock.sendall(client.peeked_data)
            client.forward(upstream_sock)
        else:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('[%s] http connect response: %s' % (repr(client), response.strip()))
            LOGGER.error('[%s] http connect rejected: %s' %
                         (repr(client), response.splitlines()[0] if response.splitlines() else 'unknown'))
            self.died = True
            client.fall_back(
                response.splitlines()[0] if response.splitlines() else 'unknown',
                delayed_penalty=self.increase_failed_time)
        self.failed_times = 0

    def is_protocol_supported(self, protocol, client=None):
        return protocol == 'HTTPS'

    def __repr__(self):
        return 'HttpConnectProxy[%s:%s %0.2f]' % (self.proxy_host, self.proxy_port, self.latency)

    @property
    def public_name(self):
        return 'HTTP\t%s' % self.proxy_host


########NEW FILE########
__FILENAME__ = http_relay
import logging
import base64
import sys
import time

import ssl

from .direct import Proxy
from .direct import to_bool
from .http_try import try_receive_response_header
from .http_try import try_receive_response_body
from .http_try import recv_and_parse_request


LOGGER = logging.getLogger(__name__)


class HttpRelayProxy(Proxy):
    def __init__(self, proxy_host, proxy_port, username=None, password=None, is_secured=False, priority=0, **ignore):
        super(HttpRelayProxy, self).__init__()
        self.proxy_host = proxy_host
        if not self.proxy_host:
            self.died = True
        self.proxy_port = int(proxy_port)
        self.username = username
        self.password = password
        self.failed_times = 0
        self.is_secured = to_bool(is_secured)
        self.priority = int(priority)

    def do_forward(self, client):
        LOGGER.info('[%s] http relay %s:%s' % (repr(client), self.proxy_ip, self.proxy_port))
        begin_at = time.time()
        try:
            upstream_sock = client.create_tcp_socket(self.proxy_ip, self.proxy_port, 3)
            if self.is_secured:
                counter = upstream_sock.counter
                upstream_sock = ssl.wrap_socket(upstream_sock)
                upstream_sock.counter = counter
                client.add_resource(upstream_sock)
        except:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('[%s] http-relay upstream socket connect timed out' % (repr(client)), exc_info=1)
            return client.fall_back(
                reason='http-relay upstream socket connect timed out',
                delayed_penalty=self.increase_failed_time)
        upstream_sock.settimeout(3)
        is_payload_complete = recv_and_parse_request(client)
        request_data = '%s %s HTTP/1.1\r\n' % (client.method, client.url)
        client.headers['Connection'] = 'close' # no keep-alive
        request_data += ''.join('%s: %s\r\n' % (k, v) for k, v in client.headers.items())
        if self.username and self.password:
            auth = base64.b64encode('%s:%s' % (self.username, self.password)).strip()
            request_data += 'Proxy-Authorization: Basic %s\r\n' % auth
        request_data += '\r\n'
        try:
            request_data = request_data + client.payload
            upstream_sock.counter.sending(len(request_data))
            upstream_sock.sendall(request_data)
        except:
            client.fall_back(
                reason='send to upstream failed: %s' % sys.exc_info()[1],
                delayed_penalty=self.increase_failed_time)
        if is_payload_complete:
            response = try_receive_response_body(try_receive_response_header(client, upstream_sock))
            upstream_sock.counter.received(len(response))
            client.forward_started = True
            client.downstream_sock.sendall(response)
        self.record_latency(time.time() - begin_at)
        client.forward(upstream_sock)
        self.failed_times = 0

    def is_protocol_supported(self, protocol, client=None):
        return protocol == 'HTTP'

    def __repr__(self):
        return 'HttpRelayProxy[%s:%s %0.2f]' % (self.proxy_host, self.proxy_port, self.latency)

    @property
    def public_name(self):
        return 'HTTP\t%s' % self.proxy_host


########NEW FILE########
__FILENAME__ = http_try
import logging
import httplib
import socket
import sys
import StringIO
import gzip
import fnmatch
import time
import gevent
import ssl

from .direct import Proxy
from .. import networking
from .. import stat
from .. import ip_substitution

LOGGER = logging.getLogger(__name__)

NO_DIRECT_PROXY_HOSTS = {
    'hulu.com',
    '*.hulu.com',
    'huluim.com',
    '*.huluim.com',
    'netflix.com',
    '*.netflix.com',
    'skype.com',
    '*.skype.com',
    'radiotime.com',
    '*.radiotime.com'
    'myfreecams.com',
    '*.myfreecams.com'
    'pandora.com',
    '*.pandora.com'
}

WHITE_LIST = {
    'www.google.com',
    'google.com',
    'www.google.com.hk',
    'google.com.hk',
}


def is_no_direct_host(client_host):
    return any(fnmatch.fnmatch(client_host, host) for host in NO_DIRECT_PROXY_HOSTS)

REASON_HTTP_TRY_CONNECT_FAILED = 'http try connect failed'

class HttpTryProxy(Proxy):

    INITIAL_TIMEOUT = 1
    timeout = INITIAL_TIMEOUT
    slow_ip_list = set()
    host_black_list = {} # host => count
    host_slow_list = {}
    host_slow_detection_enabled = True
    connection_pool = {}

    def __init__(self):
        super(HttpTryProxy, self).__init__()
        self.flags.add('DIRECT')
        self.dst_black_list = {} # (ip, port) => count

    def do_forward(self, client):
        dst = (client.dst_ip, client.dst_port)
        try:
            self.try_direct(client)
            if dst in self.dst_black_list:
                LOGGER.error('%s remove dst %s:%s from blacklist' % (repr(self), dst[0], dst[1]))
                del self.dst_black_list[dst]
            if client.host in HttpTryProxy.host_black_list:
                if HttpTryProxy.host_black_list.get(client.host, 0) > 3:
                    LOGGER.error('HttpTryProxies remove host %s from blacklist' % client.host)
                del HttpTryProxy.host_black_list[client.host]
            if client.host in HTTP_TRY_PROXY.host_slow_list:
                if HttpTryProxy.host_slow_list.get(client.host, 0) > 3:
                    LOGGER.error('HttpTryProxies remove host %s from slowlist' % client.host)
                del HttpTryProxy.host_slow_list[client.host]
        except NotHttp:
            raise
        except client.ProxyFallBack as e:
            if REASON_HTTP_TRY_CONNECT_FAILED == e.reason:
                if dst not in self.dst_black_list:
                    LOGGER.error('%s blacklist dst %s:%s' % (repr(self), dst[0], dst[1]))
                self.dst_black_list[dst] = self.dst_black_list.get(dst, 0) + 1
            if client.host and client.host not in WHITE_LIST:
                HttpTryProxy.host_black_list[client.host] = HttpTryProxy.host_black_list.get(client.host, 0) + 1
                if HttpTryProxy.host_black_list[client.host] == 4:
                    LOGGER.error('HttpTryProxies blacklist host %s' % client.host)
            raise

    def try_direct(self, client, is_retrying=0):
        try:
            try:
                upstream_sock = self.get_or_create_upstream_sock(client)
            except gevent.Timeout:
                client.http_try_connect_timed_out = True
                raise
        except:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('[%s] http try connect failed' % (repr(client)), exc_info=1)
            client.fall_back(reason=REASON_HTTP_TRY_CONNECT_FAILED)
            return
        client.headers['Host'] = client.host
        request_data = self.before_send_request(client, upstream_sock, client.is_payload_complete)
        request_data += '%s %s HTTP/1.1\r\n' % (client.method, client.path)
        request_data += ''.join('%s: %s\r\n' % (k, v) for k, v in client.headers.items())
        request_data += '\r\n'
        try:
            upstream_sock.sendall(request_data + client.payload)
        except:
            client.fall_back(reason='send to upstream failed: %s' % sys.exc_info()[1])
        self.after_send_request(client, upstream_sock)
        if client.is_payload_complete:
            try:
                http_response = try_receive_response_header(
                    client, upstream_sock, rejects_error=('GET' == client.method))
            except httplib.BadStatusLine:
                if is_retrying > 3:
                    client.fall_back(reason='failed to read response: %s' % upstream_sock.history)
                LOGGER.info('[%s] retry with another connection' % repr(client))
                return self.try_direct(client, is_retrying=is_retrying + 1)
            response = self.detect_slow_host(client, http_response)
            is_keep_alive = 'Connection: keep-alive' in response
            try:
                fallback_if_youtube_unplayable(client, http_response)
                response = self.process_response(client, upstream_sock, response, http_response)
            except client.ProxyFallBack:
                raise
            except:
                LOGGER.exception('process response failed')
            client.forward_started = True
            client.downstream_sock.sendall(response)
            if is_keep_alive:
                self.forward_upstream_sock(client, http_response, upstream_sock)
            else:
                client.forward(upstream_sock)
        else:
            if client.method and 'GET' != client.method.upper():
                client.forward(upstream_sock, timeout=360)
            else:
                client.forward(upstream_sock)

    def detect_slow_host(self, client, http_response):
        if HttpTryProxy.host_slow_detection_enabled:
            greenlet = gevent.spawn(
                try_receive_response_body, http_response, reads_all='youtube.com/watch?' in client.url)
            try:
                return greenlet.get(timeout=5)
            except gevent.Timeout:
                slow_times = HttpTryProxy.host_slow_list.get(client.host, 0) + 1
                HttpTryProxy.host_slow_list[client.host] = slow_times
                LOGGER.error('[%s] host %s is too slow to direct access %s/3' % (repr(client), client.host, slow_times))
                client.fall_back('too slow')
            finally:
                greenlet.kill()
        else:
            return try_receive_response_body(http_response)

    def get_or_create_upstream_sock(self, client):
        if HttpTryProxy.connection_pool.get(client.dst_ip):
            upstream_sock = HttpTryProxy.connection_pool[client.dst_ip].pop()
            if not HttpTryProxy.connection_pool[client.dst_ip]:
                del HttpTryProxy.connection_pool[client.dst_ip]
            if upstream_sock.last_used_at - time.time() > 7:
                LOGGER.debug('[%s] close old connection %s' % (repr(client), upstream_sock.history))
                upstream_sock.close()
                return self.get_or_create_upstream_sock(client)
            client.add_resource(upstream_sock)
            if len(upstream_sock.history) > 5:
                return self.get_or_create_upstream_sock(client)
            LOGGER.debug('[%s] reuse connection %s' % (repr(client), upstream_sock.history))
            upstream_sock.history.append(client.src_port)
            upstream_sock.last_used_at = time.time()
            return upstream_sock
        else:
            LOGGER.debug('[%s] open new connection' % repr(client))
            pool_size = len(HttpTryProxy.connection_pool.get(client.dst_ip, []))
            if pool_size <= 2:
                gevent.spawn(self.prefetch_to_connection_pool, client)
            return self.create_upstream_sock(client)

    def create_upstream_sock(self, client):
        success, upstream_sock = gevent.spawn(try_connect, client).get(timeout=HttpTryProxy.timeout)
        if not success:
            raise upstream_sock
        upstream_sock.last_used_at = time.time()
        upstream_sock.history = [client.src_port]
        return upstream_sock

    def prefetch_to_connection_pool(self, client):
        try:
            upstream_sock = self.create_upstream_sock(client)
            client.resources.remove(upstream_sock)
            HttpTryProxy.connection_pool.setdefault(client.dst_ip, []).append(upstream_sock)
            LOGGER.debug('[%s] prefetch success' % repr(client))
        except:
            LOGGER.debug('[%s] prefetch failed' % repr(client), exc_info=1)

    def forward_upstream_sock(self, client, http_response, upstream_sock):
        real_fp = http_response.capturing_sock.rfile.fp
        http_response.fp = ForwardingFile(real_fp, client.downstream_sock)
        while not http_response.isclosed() and (http_response.length > 0 or http_response.length is None):
            try:
                http_response.read(amt=8192)
            except:
                break
        if upstream_sock in client.resources:
            client.resources.remove(upstream_sock)
        HttpTryProxy.connection_pool.setdefault(client.dst_ip, []).append(upstream_sock)


    def before_send_request(self, client, upstream_sock, is_payload_complete):
        return ''

    def after_send_request(self, client, upstream_sock):
        pass

    def process_response(self, client, upstream_sock, response, http_response):
        return response

    def is_protocol_supported(self, protocol, client=None):
        if self.died:
            return False
        if client and self in client.tried_proxies:
            return False
        dst = (client.dst_ip, client.dst_port)
        if self.dst_black_list.get(dst, 0) % 16:
            if ip_substitution.substitute_ip(client, self.dst_black_list):
                return True
            self.dst_black_list[dst] = self.dst_black_list.get(dst, 0) + 1
            return False
        if is_no_direct_host(client.host):
            return False
        host_slow_times = HttpTryProxy.host_slow_list.get(client.host, 0)
        if host_slow_times > 3 and host_slow_times % 16:
            HttpTryProxy.host_slow_list[client.host] = host_slow_times + 1
            return False
        host_failed_times = HttpTryProxy.host_black_list.get(client.host, 0)
        if host_failed_times > 3 and host_failed_times % 16:
            HttpTryProxy.host_black_list[client.host] = host_failed_times + 1
            return False
        return 'HTTP' == protocol

    def __repr__(self):
        return 'HttpTryProxy'


class TcpScrambler(HttpTryProxy):
    def __init__(self):
        super(TcpScrambler, self).__init__()
        self.bad_requests = {} # host => count
        self.died = True
        self.is_trying = False

    def try_start_if_network_is_ok(self):
        if self.is_trying:
            return
        self.died = True
        self.is_trying = True
        gevent.spawn(self._try_start)

    def _try_start(self):
        try:
            LOGGER.info('will try start tcp scrambler in 30 seconds')
            gevent.sleep(5)
            LOGGER.info('try tcp scrambler')
            if not detect_if_ttl_being_ignored():
                self.died = False
        finally:
            self.is_trying = False

    def before_send_request(self, client, upstream_sock, is_payload_complete):
        if 'Referer' in client.headers:
            del client.headers['Referer']
        upstream_sock.setsockopt(socket.SOL_SOCKET, networking.SO_MARK, 0xbabe)
        return ''

    def after_send_request(self, client, upstream_sock):
        pass

    def process_response(self, client, upstream_sock, response, http_response):
        upstream_sock.setsockopt(socket.SOL_SOCKET, networking.SO_MARK, 0)
        if httplib.BAD_REQUEST == http_response.status:
            LOGGER.info('[%s] bad request to %s' % (repr(client), client.host))
            self.bad_requests[client.host] = self.bad_requests.get(client.host, 0) + 1
            if self.bad_requests[client.host] >= 3:
                LOGGER.critical('!!! too many bad requests, disable tcp scrambler !!!')
                self.died = True
            client.fall_back('tcp scrambler bad request')
        else:
            if client.host in self.bad_requests:
                LOGGER.info('[%s] reset bad request to %s' % (repr(client), client.host))
                del self.bad_requests[client.host]
            response = response.replace('Connection: keep-alive', 'Connection: close')
        return response

    def __repr__(self):
        return 'TcpScrambler'



HTTP_TRY_PROXY = HttpTryProxy()
TCP_SCRAMBLER = TcpScrambler()



def detect_if_ttl_being_ignored():
    gevent.sleep(5)
    for i in range(2):
        try:
            LOGGER.info('detecting if ttl being ignored')
            baidu_ip = networking.resolve_ips('www.baidu.com')[0]
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            if networking.OUTBOUND_IP:
                sock.bind((networking.OUTBOUND_IP, 0))
            sock.setblocking(0)
            sock.settimeout(2)
            sock.setsockopt(socket.SOL_IP, socket.IP_TTL, 3)
            try:
                sock.connect((baidu_ip, 80))
            finally:
                sock.close()
            LOGGER.info('ttl 3 should not connect baidu, disable fqting')
            return True
        except:
            LOGGER.exception('detected if ttl being ignored')
            gevent.sleep(1)
    return False



def try_connect(client):
    try:
        begin_time = time.time()
        upstream_sock = client.create_tcp_socket(
            client.dst_ip, client.dst_port,
            connect_timeout=max(5, HttpTryProxy.timeout * 2))
        elapsed_seconds = time.time() - begin_time
        if elapsed_seconds > HttpTryProxy.timeout:
            HttpTryProxy.slow_ip_list.add(client.dst_ip)
            HttpTryProxy.host_black_list.clear()
            if len(HttpTryProxy.slow_ip_list) > 3:
                LOGGER.critical('!!! increase http timeout %s=>%s' % (HttpTryProxy.timeout, HttpTryProxy.timeout + 1))
                HttpTryProxy.timeout += 1
                HttpTryProxy.slow_ip_list.clear()
        return True, upstream_sock
    except:
        return False, sys.exc_info()[1]

def fallback_if_youtube_unplayable(client, http_response):
    if not http_response:
        return
    if 'youtube.com/watch?' not in client.url:
        return
    if http_response.body and 'gzip' == http_response.msg.dict.get('content-encoding'):
        stream = StringIO.StringIO(http_response.body)
        gzipper = gzip.GzipFile(fileobj=stream)
        http_response.body = gzipper.read()
    if http_response.body and (
                'id="unavailable-message" class="message"' in http_response.body or 'UNPLAYABLE' in http_response.body):
        client.fall_back(reason='youtube player not available in China')



def try_receive_response_header(client, upstream_sock, rejects_error=False):
    try:
        upstream_rfile = upstream_sock.makefile('rb', 0)
        client.add_resource(upstream_rfile)
        capturing_sock = CapturingSock(upstream_rfile)
        http_response = httplib.HTTPResponse(capturing_sock)
        http_response.capturing_sock = capturing_sock
        http_response.body = None
        http_response.begin()
        content_length = http_response.msg.dict.get('content-length')
        if content_length:
            http_response.content_length = int(content_length)
        else:
            http_response.content_length = 0
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug('[%s] http try read response header: %s %s' %
                         (repr(client), http_response.status, http_response.content_length))
        if http_response.chunked:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('[%s] skip try reading response due to chunked' % repr(client))
            return http_response
        if not http_response.content_length:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('[%s] skip try reading response due to no content length' % repr(client))
            return http_response
        if rejects_error and http_response.status == 400:
            raise Exception('http try read response status is 400')
        return http_response
    except NotHttp:
        raise
    except httplib.BadStatusLine:
        raise
    except:
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug('[%s] http try read response failed' % (repr(client)), exc_info=1)
        client.fall_back(reason='http try read response failed: %s' % sys.exc_info()[1])

def try_receive_response_body(http_response, reads_all=False):
    content_type = http_response.msg.dict.get('content-type')
    if content_type and 'text/html' in content_type:
        reads_all = True
    if reads_all:
        http_response.body = http_response.read()
    else:
        http_response.body = http_response.read(min(http_response.content_length, 64 * 1024))
    return http_response.capturing_sock.rfile.captured

class CapturingSock(object):
    def __init__(self, rfile):
        self.rfile = CapturingFile(rfile)

    def makefile(self, mode='r', buffersize=-1):
        if 'rb' != mode:
            raise NotImplementedError()
        return self.rfile


class CapturingFile(object):
    def __init__(self, fp):
        self.fp = fp
        self.captured = ''

    def read(self, *args, **kwargs):
        chunk = self.fp.read(*args, **kwargs)
        self.captured += chunk
        return chunk

    def readline(self, *args, **kwargs):
        chunk = self.fp.readline(*args, **kwargs)
        self.captured += chunk
        return chunk

    def readlines(self,  *args, **kwargs):
        raise NotImplementedError()

    def close(self):
        self.fp.close()


class ForwardingFile(object):
    def __init__(self, fp, downstream_sock):
        self.fp = fp
        self.downstream_sock = downstream_sock

    def read(self, *args, **kwargs):
        chunk = self.fp.read(*args, **kwargs)
        self.downstream_sock.sendall(chunk)
        return chunk

    def readline(self, *args, **kwargs):
        chunk = self.fp.readline(*args, **kwargs)
        self.downstream_sock.sendall(chunk)
        return chunk

    def readlines(self, *args, **kwargs):
        raise NotImplementedError()

    def close(self):
        self.fp.close()

def recv_and_parse_request(client):
    client.peeked_data, client.payload = recv_till_double_newline(client.peeked_data, client.downstream_sock)
    if 'Host:' not in client.peeked_data:
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug('[%s] not http' % (repr(client)))
        raise NotHttp()
    try:
        client.method, client.path, client.headers = parse_request(client.peeked_data)
        client.host = client.headers.pop('Host', '')
        if not client.host:
            raise Exception('missing host')
        if client.path[0] == '/':
            client.url = 'http://%s%s' % (client.host, client.path)
        else:
            client.url = client.path
        if 'youtube.com/watch' in client.url:
            LOGGER.info('[%s] %s' % (repr(client), client.url))
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug('[%s] parsed http header: %s %s' % (repr(client), client.method, client.url))
        if 'Content-Length' in client.headers:
            more_payload_len = int(client.headers.get('Content-Length', 0)) - len(client.payload)
            if more_payload_len > 1024 * 1024:
                client.peeked_data += client.payload
                LOGGER.info('[%s] skip try reading request payload due to too large: %s' %
                            (repr(client), more_payload_len))
                return False
            if more_payload_len > 0:
                client.payload += client.downstream_rfile.read(more_payload_len)
        if client.payload:
            client.peeked_data += client.payload
        return True
    except:
        LOGGER.error('[%s] failed to parse http request:\n%s' % (repr(client), client.peeked_data))
        raise


def recv_till_double_newline(peeked_data, sock):
    for i in range(16):
        if peeked_data.find(b'\r\n\r\n') != -1:
            header, crlf, payload = peeked_data.partition(b'\r\n\r\n')
            return header + crlf, payload
        more_data = sock.recv(8192)
        if not more_data:
            return peeked_data, ''
        peeked_data += more_data
    raise Exception('http end not found')


class NotHttp(Exception):
    pass


def parse_request(request):
    lines = request.splitlines()
    method, path = lines[0].split()[:2]
    headers = dict()
    for line in lines[1:]:
        keyword, _, value = line.partition(b':')
        keyword = keyword.title()
        value = value.strip()
        if keyword and value:
            headers[keyword] = value
    return method, path, headers
########NEW FILE########
__FILENAME__ = shadowsocks
import socket
import struct
import logging
import time
import functools
import gevent

from .direct import Proxy
from . import encrypt
from .. import networking


LOGGER = logging.getLogger(__name__)


class ShadowSocksProxy(Proxy):
    def __init__(self, proxy_host, proxy_port, password, encrypt_method, supported_protocol=None, **ignore):
        super(ShadowSocksProxy, self).__init__()
        self.proxy_host = proxy_host
        if not self.proxy_host:
            self.died = True
        self.proxy_port = int(proxy_port)
        self.password = password
        self.encrypt_method = encrypt_method
        self.supported_protocol = supported_protocol
        gevent.spawn(self.test_latency)

    def test_latency(self):
        gevent.sleep(5)
        elapsed_time = 0
        try:
            for i in range(3):
                gevent.sleep(1)
                begin_at = time.time()
                sock = networking.create_tcp_socket(self.proxy_ip, self.proxy_port, 5)
                sock.close()
                elapsed_time += time.time() - begin_at
        except:
            self.record_latency(10) # fixed penalty
            self.increase_failed_time()
            return
        LOGGER.info('%s => %s' % (self.proxy_ip, elapsed_time))
        self.record_latency(elapsed_time)

    def do_forward(self, client):
        encryptor = encrypt.Encryptor(self.password, self.encrypt_method)
        addr_to_send = '\x01'
        addr_to_send += socket.inet_aton(client.dst_ip)
        addr_to_send += struct.pack('>H', client.dst_port)
        begin_at = time.time()
        try:
            upstream_sock = client.create_tcp_socket(self.proxy_ip, self.proxy_port, 5)
        except:
            self.record_latency(10) # fixed penalty
            client.fall_back(reason='can not connect to proxy', delayed_penalty=self.increase_failed_time)
        encrypted_addr = encryptor.encrypt(addr_to_send)
        upstream_sock.counter.sending(len(encrypted_addr))
        upstream_sock.sendall(encrypted_addr)
        encrypted_peeked_data = encryptor.encrypt(client.peeked_data)
        upstream_sock.counter.sending(len(encrypted_peeked_data))
        upstream_sock.sendall(encrypted_peeked_data)
        client.forward(
            upstream_sock, timeout=5 + self.failed_times * 2,
            encrypt=encryptor.encrypt, decrypt=encryptor.decrypt,
            delayed_penalty=self.increase_failed_time if client.peeked_data else None,
            on_forward_started=functools.partial(self.on_forward_started, begin_at=begin_at))
        self.clear_failed_times()

    def on_forward_started(self, begin_at):
        self.record_latency(time.time() - begin_at)

    def is_protocol_supported(self, protocol, client=None):
        if hasattr(self, 'resolved_by_dynamic_proxy'):
            if 'youtube.com' in client.host or 'googlevideo.com' in client.host:
                return False
        if not self.supported_protocol:
            return True
        return self.supported_protocol == protocol

    def __repr__(self):
        return 'ShadowSocksProxy[%s:%s %0.2f]' % (self.proxy_host, self.proxy_port, self.latency)

    @property
    def public_name(self):
        return 'SS\t%s' % self.proxy_host
########NEW FILE########
__FILENAME__ = spdy_client
import select
import tlslite

import gevent
import gevent.queue
import gevent.event
import spdy.context
import spdy.frames
import sys
import logging
import socket
from .. import networking
from .. import stat


LOGGER = logging.getLogger(__name__)

LOCAL_INITIAL_WINDOW_SIZE = 65536
WORKING = 'working'
SPDY_3 = 3
SPDY_2 = 2


class SpdyClient(object):
    def __init__(self, ip, port, requested_spdy_version):
        self.sock = networking.create_tcp_socket(ip, port, 3)
        self.tls_conn = tlslite.TLSConnection(self.sock)
        if 'auto' == requested_spdy_version:
            nextProtos=['spdy/3', 'spdy/2']
        elif 'spdy/2' == requested_spdy_version:
            nextProtos=['spdy/2']
        elif 'spdy/3' == requested_spdy_version:
            nextProtos=['spdy/3']
        else:
            raise Exception('unknown requested spdy version: %s' % requested_spdy_version)
        self.tls_conn.handshakeClientCert(nextProtos=nextProtos)
        LOGGER.info('negotiated protocol: %s' % self.tls_conn.next_proto)
        if 'spdy/2' == self.tls_conn.next_proto:
            self.spdy_version = SPDY_2
        elif 'spdy/3' == self.tls_conn.next_proto:
            self.spdy_version = SPDY_3
        else:
            raise Exception('not spdy')
        self.spdy_context = spdy.context.Context(spdy.context.CLIENT, version=self.spdy_version)
        self.remote_initial_window_size = 65536
        self.streams = {}
        self.send(spdy.frames.Settings(1, {spdy.frames.INITIAL_WINDOW_SIZE: (0, LOCAL_INITIAL_WINDOW_SIZE)}))

    def open_stream(self, headers, client):
        stream_id = self.spdy_context.next_stream_id
        stream = SpdyStream(
            stream_id, client,
            upstream_window_size=self.remote_initial_window_size,
            downstream_window_size=LOCAL_INITIAL_WINDOW_SIZE,
            send_cb=self.send,
            spdy_version=self.spdy_version)
        self.streams[stream_id] = stream
        self.send(spdy.frames.SynStream(stream_id, headers, version=self.spdy_version, flags=0))
        if client.payload:
            stream.counter.sending(len(client.payload))
            self.send(spdy.frames.DataFrame(stream_id, client.payload, flags=0))
        gevent.spawn(stream.poll_from_downstream)
        return stream_id

    def end_stream(self, stream_id):
        self.send(spdy.frames.RstStream(stream_id, error_code=spdy.frames.CANCEL, version=self.spdy_version))
        if stream_id in self.streams:
            self.streams[stream_id].close()
            del self.streams[stream_id]

    def poll_stream(self, stream_id, on_frame_cb):
        stream = self.streams[stream_id]
        try:
            while not stream.done:
                try:
                    frame = stream.upstream_frames.get(timeout=10)
                except gevent.queue.Empty:
                    if stream.client.forward_started:
                        return
                    else:
                        return stream.client.fall_back('no response from proxy')
                if WORKING == frame:
                    continue
                elif isinstance(frame, spdy.frames.RstStream):
                    LOGGER.info('[%s] rst: %s' % (repr(stream.client), frame))
                    return
                else:
                    on_frame_cb(stream, frame)
        finally:
            self.end_stream(stream_id)

    def loop(self):
        while True:
            data = self.tls_conn.read()
            if not data:
                return
            self.spdy_context.incoming(data)
            self.consume_frames()


    def consume_frames(self):
        while True:
            frame = self.spdy_context.get_frame()
            if not frame:
                return
            try:
                if isinstance(frame, spdy.frames.Settings):
                    all_settings = dict(frame.id_value_pairs)
                    LOGGER.info('received spdy settings: %s' % all_settings)
                    initial_window_size_settings = all_settings.get(spdy.frames.INITIAL_WINDOW_SIZE)
                    if initial_window_size_settings:
                        self.remote_initial_window_size = initial_window_size_settings[1]
                elif isinstance(frame, spdy.frames.DataFrame):
                    if frame.stream_id in self.streams:
                        stream = self.streams[frame.stream_id]
                        stream.send_to_downstream(frame.data)
                elif isinstance(frame, spdy.frames.WindowUpdate):
                    if frame.stream_id in self.streams:
                        stream = self.streams[frame.stream_id]
                        stream.update_upstream_window(frame.delta_window_size)
                elif hasattr(frame, 'stream_id'):
                    if frame.stream_id in self.streams:
                        stream = self.streams[frame.stream_id]
                        stream.upstream_frames.put(frame)
                else:
                    LOGGER.warn('!!! unknown frame: %s %s !!!' % (frame, getattr(frame, 'frame_type')))
            except:
                LOGGER.exception('failed to handle frame: %s' % frame)

    def send(self, frame):
        self.spdy_context.put_frame(frame)
        data = self.spdy_context.outgoing()
        self.tls_conn.write(data)


    def close(self):
        try:
            self.tls_conn.close()
            self.tls_conn = None
        except:
            pass
        try:
            self.sock.close()
            self.sock = None
        except:
            pass


class SpdyStream(object):
    def __init__(self, stream_id, client, upstream_window_size, downstream_window_size, send_cb, spdy_version):
        self.stream_id = stream_id
        self.upstream_frames = gevent.queue.Queue()
        self.client = client
        self.upstream_window_size = upstream_window_size
        self.downstream_window_size = downstream_window_size
        self.remote_ready = gevent.event.Event()
        self.send_cb = send_cb
        self.sent_bytes = len(client.payload)
        self.received_bytes = 0
        self.request_content_length = sys.maxint
        self.response_content_length = sys.maxint
        self.spdy_version = spdy_version
        self._done = False
        self.counter = stat.opened(self, client.forwarding_by, client.host, client.dst_ip)

    def send_to_downstream(self, data):
        try:
            if not self.client.forward_started:
                gevent.sleep(0)
            self.client.downstream_sock.sendall(data)
            self.upstream_frames.put(WORKING)
            self.counter.received(len(data))
            self.received_bytes += len(data)
            if self.spdy_version == SPDY_3:
                self.downstream_window_size -= len(data)
                if self.downstream_window_size < 65536 / 2:
                    self.send_cb(spdy.frames.WindowUpdate(
                        self.stream_id, 65536 - self.downstream_window_size, version=SPDY_3))
                    self.downstream_window_size = 65536
        except socket.error:
            self._done = True
        except:
            self._done = True
            LOGGER.exception('[%s] failed to send to downstream' % repr(self.client))

    def update_upstream_window(self, delta_window_size):
        if self.spdy_version == SPDY_3:
            self.upstream_window_size += delta_window_size
            if self.upstream_window_size > 0:
                self.remote_ready.set()

    def poll_from_downstream(self):
        try:
            while not self.done:
                ins, _, _ = select.select([self.client.downstream_sock], [], [], 2)
                if self.done:
                    return
                if self.client.downstream_sock in ins:
                    data = self.client.downstream_sock.recv(8192)
                    if data:
                        self.upstream_frames.put(WORKING)
                        self.send_cb(spdy.frames.DataFrame(self.stream_id, data, flags=0))
                        self.counter.sending(len(data))
                        self.sent_bytes += len(data)
                        if self.spdy_version == SPDY_3:
                            self.upstream_window_size -= len(data)
                            if self.upstream_window_size <= 0:
                                self.remote_ready.clear()
                                self.remote_ready.wait()
                    else:
                        self._done = True
                        return
        except select.error:
            self._done = True
        except socket.error:
            self._done = True
        except:
            self._done = True
            LOGGER.exception('[%s] failed to poll from downstream' % repr(self.client))

    @property
    def done(self):
        if self.received_bytes >= self.response_content_length and self.sent_bytes >= self.request_content_length:
            self._done = True
        return self._done

    def close(self):
        pass

########NEW FILE########
__FILENAME__ = spdy_connect
import logging
import base64

import gevent
import spdy.context
import spdy.frames

from .direct import Proxy
from .spdy_client import SpdyClient
from .spdy_client import SPDY_3


LOGGER = logging.getLogger(__name__)


class SpdyConnectProxy(Proxy):
    def __init__(self, proxy_host, proxy_port, requested_spdy_version='auto',
                 username=None, password=None, priority=0, **ignore):
        super(SpdyConnectProxy, self).__init__()
        self.proxy_host = proxy_host
        self.proxy_port = int(proxy_port)
        self.username = username
        self.password = password
        self.spdy_client = None
        self.requested_spdy_version = requested_spdy_version
        self.died = True
        self.loop_greenlet = None
        self.priority = int(priority)

    def connect(self):
        try:
            try:
                if self.loop_greenlet:
                    self.loop_greenlet.kill()
            except:
                pass
            self.loop_greenlet = gevent.spawn(self.loop)
        except:
            LOGGER.exception('failed to connect spdy-connect proxy: %s' % self)
            self.died = True

    def loop(self):
        try:
            while True:
                self.close()
                if '0.0.0.0' == self.proxy_ip:
                    return
                try:
                    self.spdy_client = SpdyClient(self.proxy_ip, self.proxy_port, self.requested_spdy_version)
                except:
                    LOGGER.exception('failed to connect spdy connect: %s' % self)
                    gevent.sleep(10)
                    self.spdy_client = SpdyClient(self.proxy_ip, self.proxy_port, self.requested_spdy_version)
                self.died = False
                try:
                    self.spdy_client.loop()
                except:
                    LOGGER.exception('spdy client loop failed')
                finally:
                    LOGGER.info('spdy client loop quit')
                self.died = True
        except:
            LOGGER.exception('spdy connect loop failed')
            self.died = True

    def close(self):
        if self.spdy_client:
            self.spdy_client.close()
            self.spdy_client = None
        self.died = True

    def do_forward(self, client):
        if not self.spdy_client:
            self.died = True
            client.fall_back(reason='not connected yet')
        if SPDY_3 == self.spdy_client.spdy_version:
            headers = {
                ':method': 'CONNECT',
                ':scheme': 'https',
                ':path': '%s:%s' % (client.dst_ip, client.dst_port),
                ':version': 'HTTP/1.1',
                ':host': '%s:%s' % (client.dst_ip, client.dst_port)
            }
        else:
            headers = {
                'method': 'CONNECT',
                'scheme': 'https',
                'url': '%s:%s' % (client.dst_ip, client.dst_port),
                'version': 'HTTP/1.1',
                'host': '%s:%s' % (client.dst_ip, client.dst_port)
            }
        if self.username and self.password:
            auth = base64.b64encode('%s:%s' % (self.username, self.password)).strip()
            headers['proxy-authorization'] = 'Basic %s' % auth
        client.payload = client.peeked_data
        stream_id = self.spdy_client.open_stream(headers, client)
        self.spdy_client.poll_stream(stream_id, self.on_frame)

    def on_frame(self, stream, frame):
        if isinstance(frame, spdy.frames.SynReply):
            self.on_syn_reply_frame(stream, frame)
            return
        else:
            LOGGER.warn('!!! [%s] unknown frame: %s %s !!!'
                        % (repr(stream.client), frame, getattr(frame, 'frame_type')))

    def on_syn_reply_frame(self, stream, frame):
        client = stream.client
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug('[%s] syn reply: %s' % (repr(client), frame.headers))
        headers = dict(frame.headers)
        if SPDY_3 == self.spdy_client.spdy_version:
            status = headers.pop(':status')
        else:
            status = headers.pop('status')
        if status.startswith('200'):
            client.forward_started = True
        else:
            LOGGER.error('[%s] proxy rejected CONNECT: %s' % (repr(client), status))
            self.died = True
            self.loop_greenlet.kill()


    @classmethod
    def refresh(cls, proxies):
        for proxy in proxies:
            proxy.connect()
        return True

    def is_protocol_supported(self, protocol, client=None):
        return protocol == 'HTTPS'

    def __repr__(self):
        return 'SpdyConnectProxy[%s:%s]' % (self.proxy_host, self.proxy_port)

    @property
    def public_name(self):
        return 'SPDY\t%s' % self.proxy_host


########NEW FILE########
__FILENAME__ = spdy_relay
import logging
import sys
import base64

import gevent
import spdy.context
import spdy.frames

from .http_try import recv_and_parse_request
from .direct import Proxy
from .spdy_client import SpdyClient
from .spdy_client import SPDY_3


LOGGER = logging.getLogger(__name__)


class SpdyRelayProxy(Proxy):
    def __init__(self, proxy_host, proxy_port, requested_spdy_version='auto',
                 username=None, password=None, priority=0, **ignore):
        super(SpdyRelayProxy, self).__init__()
        self.proxy_host = proxy_host
        self.proxy_port = int(proxy_port)
        self.username = username
        self.password = password
        self.spdy_client = None
        self.requested_spdy_version = requested_spdy_version
        self.died = True
        self.loop_greenlet = None
        self.priority = int(priority)

    def connect(self):
        try:
            try:
                if self.loop_greenlet:
                    self.loop_greenlet.kill()
            except:
                pass
            self.loop_greenlet = gevent.spawn(self.loop)
        except:
            LOGGER.exception('failed to connect spdy-relay proxy: %s' % self)
            self.died = True

    def loop(self):
        try:
            while True:
                self.close()
                if '0.0.0.0' == self.proxy_ip:
                    return
                try:
                    self.spdy_client = SpdyClient(self.proxy_ip, self.proxy_port, self.requested_spdy_version)
                except:
                    LOGGER.exception('failed to connect spdy relay: %s' % self)
                    gevent.sleep(10)
                    self.spdy_client = SpdyClient(self.proxy_ip, self.proxy_port, self.requested_spdy_version)
                self.died = False
                try:
                    self.spdy_client.loop()
                except:
                    LOGGER.exception('spdy client loop failed')
                finally:
                    LOGGER.info('spdy client loop quit')
                self.died = True
        except:
            LOGGER.exception('spdy relay loop failed')
            self.died = True

    def close(self):
        if self.spdy_client:
            self.spdy_client.close()
            self.spdy_client = None
        self.died = True

    def do_forward(self, client):
        if not self.spdy_client:
            self.died = True
            client.fall_back(reason='not connected yet')
        recv_and_parse_request(client)
        if SPDY_3 == self.spdy_client.spdy_version:
            headers = {
                ':method': client.method,
                ':scheme': 'http',
                ':path': client.url,
                ':version': 'HTTP/1.1',
                ':host': client.host
            }
        else:
            headers = {
                'method': client.method,
                'scheme': 'http',
                'url': client.url,
                'version': 'HTTP/1.1',
                'host': client.host
            }
        if self.username and self.password:
            auth = base64.b64encode('%s:%s' % (self.username, self.password)).strip()
            headers['proxy-authorization'] = 'Basic %s' % auth
        for k, v in client.headers.items():
            headers[k.lower()] = v
        headers['connection'] = 'close'
        stream_id = self.spdy_client.open_stream(headers, client)
        stream = self.spdy_client.streams[stream_id]
        stream.request_content_length = int(headers.get('content-length', 0))
        self.spdy_client.poll_stream(stream_id, self.on_frame)

    def on_frame(self, stream, frame):
        if isinstance(frame, spdy.frames.SynReply):
            stream.response_content_length = self.on_syn_reply_frame(stream, frame)
        else:
            LOGGER.warn('!!! [%s] unknown frame: %s %s !!!'
                        % (repr(stream.client), frame, getattr(frame, 'frame_type')))

    def on_syn_reply_frame(self, stream, frame):
        client = stream.client
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug('[%s] syn reply: %s' % (repr(client), frame.headers))
        headers = dict(frame.headers)
        if SPDY_3 == self.spdy_client.spdy_version:
            http_version = headers.pop(':version')
            status = headers.pop(':status')
        else:
            http_version = headers.pop('version')
            status = headers.pop('status')
        client.forward_started = True
        client.downstream_sock.sendall('%s %s\r\n' % (http_version, status))
        for k, v in headers.items():
            client.downstream_sock.sendall('%s: %s\r\n' % (k, v))
        client.downstream_sock.sendall('\r\n')
        if status.startswith('304'):
            return 0
        else:
            return int(headers.pop('content-length', sys.maxint))


    @classmethod
    def refresh(cls, proxies):
        for proxy in proxies:
            proxy.connect()
        return True

    def is_protocol_supported(self, protocol, client=None):
        return protocol == 'HTTP'

    def __repr__(self):
        return 'SpdyRelayProxy[%s:%s]' % (self.proxy_host, self.proxy_port)

    @property
    def public_name(self):
        return 'SPDY\t%s' % self.proxy_host


########NEW FILE########
__FILENAME__ = ssh
import logging
import sys
import os
import contextlib
import functools
import time

import paramiko
import gevent
import gevent.event

from .direct import Proxy
from .. import networking
from .. import stat


LOGGER = logging.getLogger(__name__)


class SshProxy(Proxy):
    def __init__(self, proxy_host, proxy_port=22, username=None, password=None, key_filename=None, priority=0, **ignore):
        super(SshProxy, self).__init__()
        self.proxy_host = proxy_host
        if not self.proxy_host:
            self.died = True
        self.proxy_port = int(proxy_port)
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.ssh_client = None
        self.connection_failed = gevent.event.Event()
        self.failed_times = 0
        self.priority = int(priority)

    def connect(self):
        if '0.0.0.0' == self._proxy_ip:
            return False
        try:
            self.close()
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.load_system_host_keys()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            sock = networking.create_tcp_socket(self.proxy_ip, self.proxy_port, 3)
            self.key_filename = self.key_filename or '/sdcard/%s' % self.proxy_host
            if not os.path.exists(self.key_filename):
                self.key_filename = None
            self.ssh_client.connect(
                self.proxy_ip, self.proxy_port,
                username=self.username, password=self.password,
                key_filename=self.key_filename,
                sock=sock,
                look_for_keys=True if self.key_filename else False)
            return True
        except:
            LOGGER.exception('failed to connect ssh proxy: %s' % self)
            self.increase_failed_time()
            return False

    def guard(self):
        while not self.died:
            self.connection_failed.wait()
            LOGGER.critical('!!! %s reconnect' % self)
            if not self.connect():
                continue
            self.connection_failed.clear()
            gevent.sleep(1)
        LOGGER.critical('!!! %s gurad loop exit !!!' % self)


    def close(self):
        if self.ssh_client:
            self.ssh_client.close()

    def do_forward(self, client):
        begin_at = time.time()
        try:
            upstream_socket = self.open_channel(client)
        except:
            LOGGER.info('[%s] failed to open channel: %s' % (repr(client), sys.exc_info()[1]))
            gevent.sleep(1)
            self.connection_failed.set()
            return client.fall_back(reason='ssh open channel failed', delayed_penalty=self.increase_failed_time)
        with contextlib.closing(upstream_socket):
            upstream_socket.counter = stat.opened(upstream_socket, self, client.host, client.dst_ip)
            LOGGER.info('[%s] channel opened: %s' % (repr(client), upstream_socket))
            client.add_resource(upstream_socket)
            upstream_socket.sendall(client.peeked_data)
            client.forward(
                upstream_socket, delayed_penalty=self.increase_failed_time,
                on_forward_started=functools.partial(self.on_forward_started, begin_at=begin_at))
            self.failed_times = 0

    def on_forward_started(self, begin_at):
        self.record_latency(time.time() - begin_at)

    def open_channel(self, client):
        return self.ssh_client.get_transport().open_channel(
            'direct-tcpip', (client.dst_ip, client.dst_port), (client.src_ip, client.src_port))

    @classmethod
    def refresh(cls, proxies):
        for proxy in proxies:
            proxy.connection_failed.set()
            gevent.spawn(proxy.guard)
        return True

    def is_protocol_supported(self, protocol, client=None):
        return True

    def __repr__(self):
        return 'SshProxy[%s:%s]' % (self.proxy_host, self.proxy_port)

    @property
    def public_name(self):
        return 'SSH\t%s' % self.proxy_host
########NEW FILE########
__FILENAME__ = tcp_smuggler
import socket
import time
import logging
import sys

import gevent

from .http_try import HttpTryProxy
from .http_try import is_no_direct_host
from .. import networking
from .. import stat
from .. import ip_substitution


LOGGER = logging.getLogger(__name__)


class TcpSmuggler(HttpTryProxy):
    def __init__(self):
        super(TcpSmuggler, self).__init__()
        self.died = True
        self.is_trying = False
        self.flags.remove('DIRECT')

    def try_start_if_network_is_ok(self):
        if self.is_trying:
            return
        self.died = True
        self.is_trying = True
        gevent.spawn(self._try_start)

    def _try_start(self):
        try:
            LOGGER.info('will try start tcp smuggler in 30 seconds')
            gevent.sleep(5)
            LOGGER.info('try tcp smuggler')
            create_smuggled_sock('8.8.8.8', 53)
            LOGGER.info('tcp smuggler is working')
            self.died = False
        except:
            LOGGER.info('tcp smuggler is not working: %s' % sys.exc_info()[0])
        finally:
            self.is_trying = False

    def get_or_create_upstream_sock(self, client):
        return self.create_upstream_sock(client)

    def create_upstream_sock(self, client):
        upstream_sock = create_smuggled_sock(client.dst_ip, client.dst_port)
        upstream_sock.history = [client.src_port]
        upstream_sock.counter = stat.opened(upstream_sock, client.forwarding_by, client.host, client.dst_ip)
        client.add_resource(upstream_sock)
        client.add_resource(upstream_sock.counter)
        return upstream_sock

    def before_send_request(self, client, upstream_sock, is_payload_complete):
        upstream_sock.setsockopt(socket.SOL_SOCKET, networking.SO_MARK, 0xfeee)
        return ''

    def process_response(self, client, upstream_sock, response, http_response):
        upstream_sock.setsockopt(socket.SOL_SOCKET, networking.SO_MARK, 0)
        return super(TcpSmuggler, self).process_response(client, upstream_sock, response, http_response)

    def is_protocol_supported(self, protocol, client=None):
        if self.died:
            return False
        if client:
            if self in client.tried_proxies:
                return False
            if getattr(client, 'http_try_connect_timed_out', False):
                return False
            dst = (client.dst_ip, client.dst_port)
            if self.dst_black_list.get(dst, 0) % 16:
                if ip_substitution.substitute_ip(client, self.dst_black_list):
                    return True
                self.dst_black_list[dst] = self.dst_black_list.get(dst, 0) + 1
                return False
            if is_no_direct_host(client.host):
                return False
        return 'HTTP' == protocol

    def __repr__(self):
        return 'TcpSmuggler'


TCP_SMUGGLER = TcpSmuggler()


def create_smuggled_sock(ip, port):
    upstream_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    if networking.OUTBOUND_IP:
        upstream_sock.bind((networking.OUTBOUND_IP, 0))
    upstream_sock.setsockopt(socket.SOL_SOCKET, networking.SO_MARK, 0xfeee)
    upstream_sock.settimeout(3)
    try:
        upstream_sock.connect((ip, port))
    except:
        upstream_sock.close()
        raise
    upstream_sock.last_used_at = time.time()
    upstream_sock.settimeout(None)
    return upstream_sock
########NEW FILE########
__FILENAME__ = stat
# -*- coding: utf-8 -*-
import time
import logging

LOGGER = logging.getLogger(__name__)

counters = [] # not closed or closed within 5 minutes

MAX_TIME_RANGE = 60 * 10

def opened(attached_to_resource, proxy, host, ip):
    if hasattr(proxy, 'resolved_by_dynamic_proxy'):
        proxy = proxy.resolved_by_dynamic_proxy
    counter = Counter(proxy, host, ip)
    orig_close = attached_to_resource.close

    def new_close():
        try:
            orig_close()
        finally:
            counter.close()

    attached_to_resource.close = new_close
    if '127.0.0.1' != counter.ip:
        counters.append(counter)
    clean_counters()
    return counter


def clean_counters():
    global counters
    try:
        expired_counters = find_expired_counters()
        for counter in expired_counters:
            counters.remove(counter)
    except:
        LOGGER.exception('failed to clean counters')
        counters = []


def find_expired_counters():
    now = time.time()
    expired_counters = []
    for counter in counters:
        counter_time = counter.closed_at or counter.opened_at
        if now - counter_time > MAX_TIME_RANGE:
            expired_counters.append(counter)
        else:
            return expired_counters
    return []


class Counter(object):
    def __init__(self, proxy, host, ip):
        self.proxy = proxy
        self.host = host
        self.ip = ip
        self.opened_at = time.time()
        self.closed_at = None
        self.events = []

    def sending(self, bytes_count):
        self.events.append(('tx', time.time(), bytes_count))


    def received(self, bytes_count):
        self.events.append(('rx', time.time(), bytes_count))

    def total_rx(self, after=0):
        if not self.events:
            return 0, 0, 0
        bytes = 0
        seconds = 0
        last_event_time = self.opened_at
        for event_type, event_time, event_bytes in self.events:
            if event_time > after and 'rx' == event_type:
                seconds += (event_time - last_event_time)
                bytes += event_bytes
            last_event_time = event_time
        if not bytes:
            return 0, 0, 0
        return bytes, seconds, bytes / (seconds * 1000)

    def total_tx(self, after=0):
        if not self.events:
            return 0, 0, 0
        bytes = 0
        seconds = 0
        pending_tx_events = []
        for event_type, event_time, event_bytes in self.events:
            if event_time > after:
                if 'tx' == event_type:
                    pending_tx_events.append((event_time, event_bytes))
                else:
                    if pending_tx_events:
                        seconds += (event_time - pending_tx_events[-1][0])
                        bytes += sum(b for _, b in pending_tx_events)
                    pending_tx_events = []
        if pending_tx_events:
            seconds += ((self.closed_at or time.time()) - pending_tx_events[0][0])
            bytes += sum(b for _, b in pending_tx_events)
        if not bytes:
            return 0, 0, 0
        return bytes, seconds, bytes / (seconds * 1000)

    def close(self):
        if not self.closed_at:
            self.closed_at = time.time()

    def __str__(self):
        rx_bytes, rx_seconds, rx_speed = self.total_rx()
        tx_bytes, tx_seconds, tx_speed = self.total_tx()
        return '[%s~%s] %s%s via %s rx %0.2fKB/s(%s/%s) tx %0.2fKB/s(%s/%s)' % (
            self.opened_at, self.closed_at or '',
            self.ip, '(%s)' % self.host if self.host else '', self.proxy,
            rx_speed, rx_bytes, rx_seconds,
            tx_speed, tx_bytes, tx_seconds)
########NEW FILE########
__FILENAME__ = us_ip
# coding=utf-8
import urllib2
import json
import logging
import httplib
import os.path
from . import networking

LOGGER = logging.getLogger(__name__)

US_IP_CACHE = {}
HOST_IP = {}

def load_cache(file):
    if not file:
        return
    if not os.path.exists(file):
        return
    with open(file) as f:
        US_IP_CACHE.update(json.loads(f.read()))

def save_cache(file):
    if not file:
        return
    with open(file, 'w') as f:
        f.write(json.dumps(US_IP_CACHE))

def is_us_ip(ip):
    if ip in US_IP_CACHE:
        return US_IP_CACHE[ip]
    try:
        return query_from_taobao(ip)
    except:
        LOGGER.exception('failed to query geoip from taobao')
        try:
            return query_from_sina(ip)
        except:
            LOGGER.exception('failed to query geoip from sina')
            try:
                return query_from_telize(ip)
            except:
                LOGGER.exception('failed to query from telize')
    return False


def query_from_taobao(ip):
    response = json.loads(http_get('http://ip.taobao.com/service/getIpInfo.php?ip=%s' % ip))
    yes = 'US' == response['data']['country_id']
    US_IP_CACHE[ip] = yes
    LOGGER.info('queried ip %s is us ip %s from taobao' % (ip, yes))
    return yes


def query_from_sina(ip):
    response = json.loads(http_get('http://int.dpool.sina.com.cn/iplookup/iplookup.php?ip=%s&format=json' % ip))
    yes = u'美国' == response['country']
    US_IP_CACHE[ip] = yes
    LOGGER.info('queried ip %s is us ip %s from sina' % (ip, yes))
    return yes


def query_from_telize(ip):
    response = json.loads(http_get('http://www.telize.com/geoip/%s' % ip))
    yes = 'US' == response['country_code']
    US_IP_CACHE[ip] = yes
    LOGGER.info('queried ip %s is us ip %s from telize' % (ip, yes))
    return yes


def http_get(url):
    class MyHTTPConnection(httplib.HTTPConnection):
        def connect(self):
            if self.host in HOST_IP:
                self.host = HOST_IP[self.host]
            else:
                ip = networking.resolve_ips(self.host)[0]
                HOST_IP[self.host] = ip
                self.host = ip
            return httplib.HTTPConnection.connect(self)

    class MyHTTPHandler(urllib2.HTTPHandler):
        def http_open(self, req):
            return self.do_open(MyHTTPConnection, req)

    opener = urllib2.build_opener(MyHTTPHandler)
    return opener.open(url).read()
########NEW FILE########
__FILENAME__ = __main__
import sys

from .fqsocks import main


main(sys.argv[1:])


########NEW FILE########
