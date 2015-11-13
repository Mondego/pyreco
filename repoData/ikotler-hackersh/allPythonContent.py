__FILENAME__ = _preamble
# This makes sure that users don't have to set up their environment
# specially in order to run the interpreter.

# This helper is not intended to be packaged or installed, it is only
# a developer convenience. By the time Hackersh is actually installed
# somewhere, the environment should already be set up properly without
# the help of this tool.


import sys
import os


path = os.path.abspath(sys.argv[0])


while os.path.dirname(path) != path:

    if os.path.exists(os.path.join(path, 'hackersh', '__init__.py')):

        sys.path.insert(0, path)

        break

    path = os.path.dirname(path)

########NEW FILE########
__FILENAME__ = amap
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.1"


# Implementation

class Amap(hackersh.objects.ExternalComponentFileOutput):

    class AmapCSVOutputHandler(hackersh.objects.CSVOutputHandler):

        def startDocument(self):

            self._entry_or_entries = []

        # i.e. test.old:21:tcp:open::ftp:220 ProFTPD 1.3.4a Server (Debian) [ffff127.0.0.1]\r\n500 GET not understood\r\n500 Invalid command try being more creative\r\n:"220 ProFTPD 1.3.4a Server (Debian) [::ffff:127.0.0.1]\r\n500 GET not understood\r\n500 Invalid command: try being more creative\r\n"

        def startRow(self, row):

            try:

                # IP_ADDRESS:PORT:PROTOCOL:PORT_STATUS:SSL:IDENTIFICATION:PRINTABLE_BANNER:FULL_BANNER

                (ip_addr, port, proto, port_status, ssl, identification) = row[:6]

                self._entry_or_entries.extend([{'PROTO': proto.upper(), 'PORT': str(int(port)), 'SERVICE': identification.upper()}])

            except Exception:

                pass

        def endRow(self):

            pass

        def endDocument(self):

            for entry in self._entry_or_entries:

                self._output.append(hackersh.objects.RemoteSessionContext(self._context, **entry))

            if not self._output:

                self._output.append(self._context)

        # CSV Parsing Parameter

        delimiter = ':'

    # Consts

    DEFAULT_FILENAME = "amap"

    DEFAULT_OUTPUT_OPTIONS = "-m -o"

    DEFAULT_FILTER = \
        "(context['IPV4_ADDRESS'] or context['HOSTNAME']) and context['PROTO'] == 'TCP'"

    DEFAULT_QUERY = \
        "(context['IPV4_ADDRESS'] or context['HOSTNAME']) + ' ' + context['PORT']"

########NEW FILE########
__FILENAME__ = dnsdict6
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class DnsDict6(hackersh.objects.ExternalComponentStdoutOutput):

    class DnsDict6IPv4Output(hackersh.objects.SimpleRegExHandler):

        PATTERN = "(?P<HOSTNAME>.*)\s+->\s+(?P<IPV4_ADDRESS>.*)"

    class DnsDict6IPv6Output(hackersh.objects.SimpleRegExHandler):

        PATTERN = "(?P<HOSTNAME>.*)\s+=>\s+(?P<IPV6_ADDRESS>.*)"

    # Consts

    DEFAULT_FILENAME = "dnsdict6"

    DEFAULT_OUTPUT_OPTIONS = ''

    DEFAULT_QUERY = DEFAULT_FILTER = "context['DOMAIN']"

########NEW FILE########
__FILENAME__ = nbtscan
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import csv


# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.1"


# Implementation

class NbtScan(hackersh.objects.ExternalComponentStdoutOutput):

    class NbtScanStdoutOutputHandler(hackersh.objects.StdoutOutputHandler):

        def startDocument(self):

            self._names = {}

        def feed(self, data):

            for row in csv.reader(data.split('\n'), delimiter=','):

                # i.e. 192.168.1.106,TV             ,Workstation Service

                try:

                    (ip_addr, group_name, netbios_service) = row[:3]

                    self._names[group_name.strip().upper()] = self._names.get(group_name.strip().upper(), []) + [netbios_service.strip()]

                except Exception:

                    pass

        def endDocument(self):

            if self._names:

                self._output.append(hackersh.objects.RemoteSessionContext(self._context, **{'PROTO': 'UDP', 'PORT': '137', 'SERVICE': 'NETBIOS-NS', 'NETBIOS-NS': {'NAMES': self._names}}))

    # Consts

    DEFAULT_FILENAME = "nbtscan"

    DEFAULT_OUTPUT_OPTIONS = "-v -h -q -s ,"

    DEFAULT_FILTER = DEFAULT_QUERY = "context['IPV4_ADDRESS']"

########NEW FILE########
__FILENAME__ = nikto
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.1"


# Implementation

class Nikto(hackersh.objects.ExternalComponentFileOutput):

    # XML Parser(s)

    class NiktoXMLOutputHandler(hackersh.objects.XMLOutputHandler):

        def startDocument(self):

            self._vulnerabilities = []

        def startElement(self, name, attrs):

            # <item id="999990" osvdbid="0" osvdblink="0_LINK" method="GET">
            # <description><![CDATA[Allowed HTTP Methods: GET, HEAD, POST, OPTIONS ]]></description>
            # <uri><![CDATA[/]]></uri>
            # <namelink><![CDATA[http://localhost:80/]]></namelink>
            # <iplink><![CDATA[http://127.0.0.1:80/]]></iplink>
            # </item>

            if name == "item":

                self._entry = {'OSVDBID': str(attrs['osvdbid'])}

        def characters(self, content):

            self._data = str(content)

        def endElement(self, name):

            if name == "item":

                self._entry['DESTINATION'] = self._entry['NAMELINK']

                self._vulnerabilities.append(dict(self._entry))

                self._entry = {}

            else:

                self._entry[str(name).upper()] = self._data

        def endDocument(self):

            self._output.append(hackersh.objects.RemoteSessionContext(self._context, **{'VULNERABILITIES': self._context.get('VULNERABILITIES', []) + self._vulnerabilities}))

    # Consts

    DEFAULT_FILENAME = "nikto"

    DEFAULT_STDIN_BUFFER = "n\n\n"

    DEFAULT_OUTPUT_OPTIONS = "-Format xml -o"

    DEFAULT_FILTER = \
        "(context['SERVICE'] == 'HTTP' or context['SERVICE'] == 'HTTPS') and " \
        "(context['IPV4_ADDRESS'] or context['HOSTNAME']) and " \
        "context['PROTO'] == 'TCP'"

    DEFAULT_QUERY = \
        "'-host ' + (context['IPV4_ADDRESS'] or context['HOSTNAME']) + ' -port ' + context['PORT']"

########NEW FILE########
__FILENAME__ = nmap
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.1"


# Implementation

class Nmap(hackersh.objects.ExternalComponentFileOutput):

    # XML Parser(s)

    class NmapXMLOutputHandler(hackersh.objects.XMLOutputHandler):

        def startElement(self, name, attrs):

            # i.e. <port protocol="tcp" portid="22"><state state="open" reason="syn-ack" reason_ttl="64"/><service name="ssh" method="table" conf="3" /></port>

            if name == "port":

                self._open = False

                self._portid = str(attrs['portid']).upper()

                self._protocol = str(attrs['protocol']).upper()

            # i.e. <state state="open" reason="syn-ack" reason_ttl="64"/>

            if name == "state":

                if attrs['state'] == 'open':

                    self._open = True

            # i.e. <service name="ssh" method="table" conf="3" />

            if name == "service":

                self._service = str(attrs['name']).upper()

        def endElement(self, name):

            if name == "port" and self._open:

                spinoffs = []

                # 'HTTP-PROXY' => 'HTTP' Spinoff.

                if self._service == 'HTTP-PROXY':

                    spinoffs.extend([{"PROTO": self._protocol.upper(), "PORT": self._portid, "SERVICE": 'HTTP'}])

                # PORT is already set, but with a different SERVICE? Spinoff.

                if self._context["PORT"] == self._portid \
                    and self._context['PROTO'] == self._protocol.upper() \
                    and self._context['SERVICE'] != self._service and self._service != 'HTTP-PROXY':

                    # "AS IT IS" Spinoff.

                    spinoffs.extend([{}])

                # i.e. {'PORT': 22, 'SERVICE': 'SSH'}

                spinoffs.extend([{'PROTO': self._protocol.upper(), 'PORT': self._portid, 'SERVICE': self._service}])

                for entry in spinoffs:

                    # Context per entry

                    self._output.append(hackersh.objects.RemoteSessionContext(self._context, **entry))

        def endDocument(self):

            if not self._output:

                self._output.append(self._context)

    # Consts

    DEFAULT_FILENAME = "nmap"

    DEFAULT_OUTPUT_OPTIONS = "-oX"

    DEFAULT_QUERY = DEFAULT_FILTER = "context['IPV4_ADDRESS'] or context['HOSTNAME']"

########NEW FILE########
__FILENAME__ = ping
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.1"


# Implementation

class Ping(hackersh.objects.ExternalComponentReturnValueOutput):

    def _processor(self, context, data):

        retval = False

        # i.e. Return Value == 0

        if data == 0:

            retval = hackersh.objects.RemoteSessionContext(context, PINGABLE=True)

        return retval

    # Consts

    DEFAULT_FILENAME = "ping"

    DEFAULT_OUTPUT_OPTIONS = "-c 3"

    DEFAULT_QUERY = DEFAULT_FILTER = "context['IPV4_ADDRESS'] or context['HOSTNAME']"

########NEW FILE########
__FILENAME__ = sqlmap
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.2"


# Implementation

class SqlMap(hackersh.objects.ExternalComponentStdoutOutput):

    # ---
    # Place: GET
    # Parameter: id
    #     Type: error-based
    #     Title: MySQL >= 5.0 AND error-based - WHERE or HAVING clause
    #     Payload: id=vGep' AND (SELECT 4752 FROM(SELECT COUNT(*),CONCAT(0x3a79706f3a,(SELECT (CASE WHEN (4752=4752) THEN 1 ELSE 0 END)),0x3a7a74783a,FLOOR(RAND(0)*2))x FROM INFORMATION_SCHEMA.CHARACTER_SETS GROUP BY x)a) AND 'ZzRA'='ZzRA&Submit=Submit
    #
    #     Type: UNION query
    #     Title: MySQL UNION query (NULL) - 2 columns
    #     Payload: id=vGep' LIMIT 1,1 UNION ALL SELECT CONCAT(0x3a79706f3a,0x4f674d774c6351717853,0x3a7a74783a), NULL#&Submit=Submit
    #
    #     Type: AND/OR time-based blind
    #     Title: MySQL < 5.0.12 AND time-based blind (heavy query)
    #     Payload: id=vGep' AND 7534=BENCHMARK(5000000,MD5(0x6d704e4c)) AND 'eALp'='eALp&Submit=Submit
    # ---

    class SqlMapStdoutOutputHandler(hackersh.objects.StdoutOutputHandler):

        def startDocument(self):

            self._vulnerabilities = []

        def feed(self, data):

            for vuln_parameter in data.split('---'):

                if vuln_parameter.startswith('\nPlace'):

                    entry = {}

                    for line in vuln_parameter.split('\n'):

                        if line.find(':') == -1:

                            if entry:

                                # Fixup: if GET && Append URL to NAMELINK Value

                                if entry['Place'] == 'GET':

                                    entry['DESTINATION'] = self._context['URL'] + entry['DESTINATION']

                                self.vulnerabilities.append(dict(entry))

                            continue

                        (k, v) = line.lstrip().split(':')

                        entry[self.SQLMAP_KEYS_TO_GENERIC_WEB_VULN_KEYS.get(k, k)] = v.lstrip()

        def endDocument(self):

            self._output.append(hackersh.objects.RemoteSessionContext(self._context, **{'VULNERABILITIES': self._context.get('VULNERABILITIES', []) + self._vulnerabilities}))

        # Consts

        SQLMAP_KEYS_TO_GENERIC_WEB_VULN_KEYS = {'Title': 'DESCRIPTION', 'Payload': 'DESTINATION'}

    # Consts

    DEFAULT_FILENAME = "sqlmap.py"

    DEFAULT_OUTPUT_OPTIONS = ''

    DEFAULT_FILTER = "context['URL']"

    DEFAULT_QUERY = \
        "(('--cookie ' + str(context['COOKIES'])) if context['COOKIES'] else '') + ' -u ' + context['URL']"

########NEW FILE########
__FILENAME__ = w3af
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import tempfile
import os
import subprocess
import shlex


# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.1"


# Implementation

class W3af(hackersh.objects.ExternalComponentFileOutput):

    class W3afHTMLOutputHandler(hackersh.objects.HTMLOutputHandler):

        def startDocument(self):

            self._dups = {}

            self._data = ""

            self._export_data = False

            self._in_tr = False

            self._vulnerabilities = []

        def handle_starttag(self, tag, attrs):

            if self._in_tr:

                if tag == 'td' and attrs == [('class', 'default'), ('width', '80%')]:

                    self._export_data = True

            if tag == 'tr':

                self._in_tr = True

        def handle_endtag(self, tag):

            if tag == 'tr':

                self._in_tr = False

            if tag == 'td' and self._export_data:

                self._export_data = False

                if self._data.find('\nSeverity'):

                    details = self._data.split('\nSeverity')[0].split('URL : ')

                else:

                    details = self._data.split('URL : ')

                if details[0].find('.') != -1:

                    # Remove the 'This vulnerability was found in the request with id 484.'

                    details[0] = '.'.join(details[0].split('.')[:-2])

                if not details[0].strip() in self._dups:

                    self._vulnerabilities.append({'DESCRIPTION': details[0], 'DESTINATION': details[1]})

                    self._dups[details[0].strip()] = True

                self._data = ""

        def handle_data(self, data):

                if self._export_data:

                    self._data = self._data + data

        def endDocument(self):

            self._output.append(hackersh.objects.RemoteSessionContext(self._context, **{'VULNERABILITIES': self._context.get('VULNERABILITIES', []) + self._vulnerabilities}))

#    class W3afCSVOutputHandler(hackersh.objects.CSVOutputHandler):
#
#        def startDocument(self):
#
#            self._vulnerabilities = []
#
#        # i.e. Cross site scripting vulnerability,GET,http://192.168.1.108:8008/feed.gtl?uid=<SCrIPT>alert("flgC")</SCrIPT>,uid,uid=%3CSCrIPT%3Ealert%28%22flgC%22%29%3C%2FSCrIPT%3E,[1499],|Cross Site Scripting was found at: "http://192.168.1.108:8008/feed.gtl", using HTTP method GET. The sent data was: "uid=%3CSCrIPT%3Ealert%28%22flgC%22%29%3C%2FSCrIPT%3E". This vulnerability affects ALL browsers. This vulnerability was found in the request with id 1499.|
#
#        def startRow(self, row):
#
#            try:
#
#                (desc, method, url) = row[:3]
#
#                self._vulnerabilities.append({'DESCRIPTION': desc, 'DESTINATION': url})
#
#            except Exception:
#
#                pass
#
#        def endRow(self):
#
#            pass
#
#        def endDocument(self):
#
#            self._output.append(hackersh.objects.RemoteSessionContext(self._context, **{'VULNERABILITIES': self._context.get('VULNERABILITIES', []) + self._vulnerabilities}))

    # Custom _execute

    def _execute(self, argv, context):

        if len(argv) < 2:

            return False

        tmp_script_file = tempfile.NamedTemporaryFile()

        tmp_output_file = tempfile.NamedTemporaryFile()

        tmp_input_csv_file = tempfile.NamedTemporaryFile()

        tmp_cj_file = tempfile.NamedTemporaryFile()

        url = argv[1]

        tmp_input_csv_file.write("GET,%s,''" % url)

        tmp_input_csv_file.flush()

        script_content = [
            "plugins",
            "output console, csv_file, textFile, htmlFile",
            "output config csv_file",
            "set output_file /tmp/output.csv",
            "back",
            "output config console",
            "set verbose False",
            "back",
            "output config textFile",
            "set httpFileName /tmp/output-http.txt",
            "set fileName /tmp/output.txt",
            "set verbose True",
            "back",
            "output htmlFile",
            "output config htmlFile",
            "set fileName %s" % tmp_output_file.name,
            "set verbose False",
            "back",
            "output config xmlFile",
            "set fileName /tmp/output.xml",
            "back",
            "back"
        ]

        # Cookies?

        cj = context['COOKIES']

        if cj:

            cj.save(tmp_cj_file.name, True, True)

            script_content.extend([
                "http-settings",
                "set cookieJarFile %s" % tmp_cj_file.name,
                "back"
            ])

            tmp_cj_file.flush()

            os.fsync(tmp_cj_file.fileno())

        # User-Agent?

        ua = context['USER-AGENT']

        if ua:

            script_content.extend([
                "http-settings",
                "set userAgent %s" % ua,
                "back",
            ])

        # Visited URL's?

        visited_urls_list = context['VISITED_URLS']

        if visited_urls_list:

            script_content.extend([
                "misc-settings",
                "set nonTargets %s" % ','.join(visited_urls_list),
                "back"
            ])

            pass

        script_content.extend([
            "plugins",
            "grep all, !pathDisclosure"
        ])

        if self._kwargs.get('step', False):

            script_content.extend([
                "discovery !all, allowedMethods, importResults",
                "discovery config importResults",
                "set input_csv %s" % tmp_input_csv_file.name,
                "back"
            ])

        else:

            script_content.extend([
                "discovery !all, allowedMethods, webSpider",
                "discovery config webSpider",
                "set onlyForward True",
                "back"
            ])

        script_content.extend([
            "audit all, !xsrf",
            "bruteforce all",
            "audit config xss",
            "set numberOfChecks 15",
            "back",
            "back",
            "target",
            "set target %s" % url,
            "back",
            "start",
            "exit"
        ])

        tmp_script_file.write('\n'.join(script_content))

        tmp_script_file.flush()

        os.fsync(tmp_script_file.fileno())

        cmd = argv[0] + ' -s ' + tmp_script_file.name

        self.logger.debug('Invoking Popen w/ %s' % cmd)

        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        (stdout_output, stderr_output) = p.communicate()

        tmp_output_file.flush()

        os.fsync(tmp_output_file.fileno())

        app_output = tmp_output_file.read()

        self.logger.debug('Application-specific Output:\n %s' % app_output)

        return app_output

    # Consts

    DEFAULT_FILENAME = "w3af_console"

    DEFAULT_FILTER = \
        "(context['SERVICE'] == 'HTTP' or context['SERVICE'] == 'HTTPS') and " \
        "(context['IPV4_ADDRESS'] or context['HOSTNAME']) and " \
        "context['PROTO'] == 'TCP'"

    DEFAULT_QUERY = \
        "context['URL'] or (context['SERVICE'].lower() + '://' + (context['IPV4_ADDRESS'] or context['HOSTNAME']) + ':' + context['PORT'])"

########NEW FILE########
__FILENAME__ = xprobe2
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.1"


# Implementation

class Xprobe2(hackersh.objects.ExternalComponentFileOutput):

    # XML Parser(s)

    class Xprobe2XMLOutputHandler(hackersh.objects.XMLOutputHandler):

        def startDocument(self):

            self._read_content = False

            self._os_guess = []

        def startElement(self, name, attrs):

            #   <os_guess>
            #       <primary probability="100" unit="percent"> "Linux Kernel 2.4.30" </primary>
            #       <secondary probability="100" unit="percent"> "Linux Kernel 2.4.29" </secondary>
            #       <secondary probability="100" unit="percent"> "Linux Kernel 2.4.28" </secondary>
            #       <secondary probability="100" unit="percent"> "Linux Kernel 2.4.27" </secondary>
            #       <secondary probability="100" unit="percent"> "Linux Kernel 2.4.26" </secondary>
            #       <secondary probability="100" unit="percent"> "Linux Kernel 2.4.25" </secondary>
            #       <secondary probability="100" unit="percent"> "Linux Kernel 2.4.24" </secondary>
            #       <secondary probability="100" unit="percent"> "Linux Kernel 2.4.19" </secondary>
            #       <secondary probability="100" unit="percent"> "Linux Kernel 2.4.20" </secondary>
            #       <secondary probability="100" unit="percent"> "Linux Kernel 2.4.21" </secondary>
            #    </os_guess>

            if name == "primary" or name == "secondary":

                self._entry = {}

                self._read_content = True

        def characters(self, content):

            if self._read_content:

                self._entry.update({"OS": str(content).replace('"', '').strip()})

        def endElement(self, name):

            if name == "primary" or name == "secondary":

                self._os_guess.append(hackersh.objects.RemoteSessionContext(self._context, **self._entry))

                self._read_content = False

        def endDocument(self):

            if not self._os_guess:

                self._output.append(self._context)

            else:

                for entry in self._os_guess:

                    self._output.append(entry)

    # Consts

    DEFAULT_FILENAME = "xprobe2"

    DEFAULT_OUTPUT_OPTIONS = "-X -o"

    DEFAULT_QUERY = DEFAULT_FILTER = "context['IPV4_ADDRESS'] or context['HOSTNAME']"

########NEW FILE########
__FILENAME__ = browse
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import cookielib
import mechanize
import tempfile
import os


# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.1"


# Implementation

class _MozillaCookieJarAsCommandLineArgument(cookielib.MozillaCookieJar):

    def __str__(self):

        cookies_arg = ""

        for cookie in self:

            cookies_arg += cookie.name + '=' + cookie.value + '; '

        return '"' + cookies_arg + '"'


class Browse(hackersh.objects.InternalComponent):

    def run(self, argv, context):

        url = argv[0]

        br = mechanize.Browser()

        cj = _MozillaCookieJarAsCommandLineArgument()

        already_existing_cj = context['COOKIES']

        # Duplicate Jar

        if already_existing_cj:

            tmp_cj_file = tempfile.NamedTemporaryFile()

            already_existing_cj.save(tmp_cj_file.name, True, True)

            tmp_cj_file.flush()

            os.fsync(tmp_cj_file.fileno())

            cj.load(tmp_cj_file.name, True, True)

        br.set_cookiejar(cj)

        # Browser Options

        br.set_handle_equiv(True)
        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

        if self._kwargs.get('ua', False):

            br.addheaders = [('User-agent', self._kwargs.get('ua'))]

            context['USER-AGENT'] = self._kwargs['ua']

        # Open URL

        response = br.open(url)

        response = br.open(url)

        if self._kwargs.get('dump', False):

            print response.read()

        return hackersh.objects.RemoteSessionContext(context, **{'BR_OBJECT': br, 'URL': url, 'COOKIES': cj})

    DEFAULT_FILTER = \
        "(" \
        " (context['SERVICE'] == 'HTTP' or context['SERVICE'] == 'HTTPS') and " \
        " (context['IPV4_ADDRESS'] or context['HOSTNAME']) and " \
        " context['PROTO'] == 'TCP'" \
        ")" \
        "or" \
        "(" \
        " context['URL']" \
        ")"

    DEFAULT_QUERY = \
        "context['URL'] or (context['SERVICE'].lower() + '://' + (context['IPV4_ADDRESS'] or context['HOSTNAME']) + ':' + context['PORT'])"

########NEW FILE########
__FILENAME__ = domain
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.


# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class Domain(hackersh.objects.RootComponent):

    def run(self, argv, context):

        _context = False

        if argv[0].find('.') != -1:

            _context = hackersh.objects.RemoteSessionContext(DOMAIN=argv[0])

        return _context

########NEW FILE########
__FILENAME__ = hostname
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import socket


# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class Hostname(hackersh.objects.RootComponent):

    def run(self, argv, context):

        _context = False

        try:

            socket.gethostbyname(argv[0])

            _context = hackersh.objects.RemoteSessionContext(HOSTNAME=argv[0])

        except socket.error as e:

            # i.e. socket.gaierror: [Errno -2] Name or service not known

            self.logger.debug('Caught exception %s' % str(e))

            pass

        return _context

########NEW FILE########
__FILENAME__ = ipv4_address
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import socket


# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class IPv4_Address(hackersh.objects.RootComponent):

    def run(self, argv, context):

        _context = False

        try:

            socket.inet_aton(argv[0])

            _context = hackersh.objects.RemoteSessionContext(IPV4_ADDRESS=argv[0])

        except socket.error, e:

            self.logger.debug('Caught exception %s' % str(e))

            # i.e. illegal IP address string passed to inet_aton

            pass

        return _context

########NEW FILE########
__FILENAME__ = ipv4_range
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import netaddr


# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class IPv4_Range(hackersh.objects.RootComponent):

    def run(self, argv, context):

        contexts = []

        ipv4_addresses_gen = None

        try:

            # 192.168.1.0-255

            try:

                ipv4_addresses_gen = netaddr.IPGlob(argv[0])

            except netaddr.core.AddrFormatError as e:

                self.logger.debug('Caught exception %s' % str(e))

                try:

                    # 192.168.1.0/24

                    ipv4_addresses_gen = netaddr.IPNetwork(argv[0])

                except netaddr.core.AddrFormatError as e:

                    self.logger.debug('Caught exception %s' % str(e))

                    pass

            for ipv4_addr in ipv4_addresses_gen:

                contexts.append(hackersh.objects.RemoteSessionContext(IPV4_ADDRESS=str(ipv4_addr)))

        except TypeError as e:

            pass

        return contexts

########NEW FILE########
__FILENAME__ = ipv6_address
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import socket


# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class IPv6_Address(hackersh.objects.RootComponent):

    def run(self, argv, context):

        _context = False

        try:

            socket.inet_pton(socket.AF_INET6, argv[0])

            _context = hackersh.objects.RemoteSessionContext(IPV6_ADDRESS=argv[0])

        except socket.error, e:

            self.logger.debug('Caught exception %s' % str(e))

            # i.e. illegal IP address string passed to inet_aton

            pass

        return _context

########NEW FILE########
__FILENAME__ = iterate_links
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class Iterate_Links(hackersh.objects.InternalComponent):

    def run(self, argv, context):

        contexts = []

        br = argv[0]

        for link in br.links():

            contexts.append(hackersh.objects.RemoteSessionContext(context, URL=link.absolute_url))

        return contexts if contexts else False

    DEFAULT_FILTER = DEFAULT_QUERY = "context['BR_OBJECT']"

########NEW FILE########
__FILENAME__ = nslookup
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import socket


# Local imports

import hackersh.objects
import hackersh.components.internal.ipv4_address


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class Nslookup(hackersh.objects.RootComponent):

    def run(self, argv, context):

        _context = False

        try:

            # i.e. '127.0.0.1'

            if isinstance(argv[0], basestring):

                _context = hackersh.components.internal.ipv4_address.IPv4_Address().run([socket.gethostbyname(argv[0])], {})

            # i.e. RemoteSessionContext(HOSTNAME='localhost', ...)

            else:

                __context = hackersh.objects.RemoteSessionContext(argv[0])

                _context = hackersh.components.internal.ipv4_address.IPv4_Address().run([socket.gethostbyname(__context['HOSTNAME'])], {})

                _context.update(__context)

                # Turn HOSTNAME into a shadowed key

                __context['_HOSTNAME'] = __context['HOSTNAME']

                del __context['HOSTNAME']

        except socket.error as e:

            # i.e. socket.gaierror: [Errno -5] No address associated with hostname

            self.logger.debug('Caught exception %s' % str(e))

            pass

        return _context

########NEW FILE########
__FILENAME__ = submit
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class Submit(hackersh.objects.InternalComponent):

    def run(self, argv, context):

        br = argv[0]

        br.select_form(nr=0)

        for k, v in self._kwargs.iteritems():

            br[k] = v

        response = br.submit()

        return hackersh.objects.RemoteSessionContext(context, **{'BR_OBJECT': br, 'URL': response.geturl()})

    DEFAULT_FILTER = DEFAULT_QUERY = "context['BR_OBJECT']"

########NEW FILE########
__FILENAME__ = url
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import urlparse


# Local imports

import hackersh.objects
import hackersh.components.internal.ipv4_address
import hackersh.components.internal.hostname


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class URL(hackersh.objects.RootComponent):

    def run(self, argv, context):

        _context = hackersh.objects.RemoteSessionContext({'URL': argv[0]})

        parse_result = urlparse.urlparse(argv[0])

        if parse_result.scheme and parse_result.netloc:

            netloc = parse_result.netloc

            # i.e. http://localhost:8080

            try:

                (netloc, netport) = netloc.split(':')

            except ValueError:

            # i.e. http://localhost

                netport = '80'

            # i.e. http://locahost or http://127.0.0.1?

            __context = hackersh.components.internal.ipv4_address.IPv4_Address().run([netloc], {})

            if not __context:

                __context = hackersh.components.internal.hostname.Hostname().run([netloc], {})

                if not __context:

                    # TODO: IPv6? MAC Address?

                    return __context

            # TODO: xrefer w/ URI scheme to make sure it's TCP, and not just assume

            _context.update(__context)

            _context.update({'PORT': netport, 'SERVICE': parse_result.scheme.upper(), 'PROTO': 'TCP'})

        return _context

########NEW FILE########
__FILENAME__ = alert
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class Alert(hackersh.objects.Component):

    def __call__(self, arg):

        return arg.__class__(arg, **{'VULNERABILITIES': arg.get('VULNERABILITIES', []) + [self._kwargs]})

########NEW FILE########
__FILENAME__ = null
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class Null(hackersh.objects.Component):

    def __call__(self, arg):

        return ''

########NEW FILE########
__FILENAME__ = print
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import sys


# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class print_(hackersh.objects.Component):

    def __call__(self, arg):

        sys.stdout.write(str(arg) + '\n')

        sys.stdout.flush()

        return arg

########NEW FILE########
__FILENAME__ = system
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import subprocess
import shlex


# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class System(hackersh.objects.Component):

    def __call__(self, arg):

        cmd = shlex.split(self._kwargs['path']) + list(self._args)

        self.logger.debug('Executing shell command %s' % ' '.join(cmd))

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)

        (stdout_output, stderr_output) = p.communicate(arg)

        return str(stdout_output)

########NEW FILE########
__FILENAME__ = tmpfile
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import tempfile


# Local imports

import hackersh.objects


# Metadata

__author__ = "Itzik Kotler <xorninja@gmail.com>"
__version__ = "0.1.0"


# Implementation

class tmpfile(hackersh.objects.Component):

    def __call__(self, arg):

        tfile = tempfile.NamedTemporaryFile(delete=False)

        print tfile.name

        tfile.write(str(arg))

        tfile.close()

        return ''

########NEW FILE########
__FILENAME__ = conio
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import os
import fcntl
import termios
import struct
import textwrap
import prettytable


# http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python/566752#566752

def __ioctl_GWINSZ(fd):

    cr = None

    try:

        cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))

    except Exception:

        pass

    return cr


def terminalsize():

    cr = __ioctl_GWINSZ(0) or __ioctl_GWINSZ(1) or __ioctl_GWINSZ(2)

    if not cr:

        try:

            fd = os.open(os.ctermid(), os.O_RDONLY)

            cr = __ioctl_GWINSZ(fd)

            os.close(fd)

        except:

            try:

                cr = (os.environ['LINES'], os.environ['COLUMNS'])

            except:

                cr = (25, 80)

    return int(cr[1]), int(cr[0])


def draw_underline(string):

    return string + '\n' + '-' * len(string) + '\n'


def __mk_tbl(fields):

    tbl = prettytable.PrettyTable(fields, left_padding_width=1, right_padding_width=1, hrules=prettytable.ALL)

    col_max_width = (terminalsize()[0] / len(fields)) - 30

    for k in tbl.align:

        tbl.align[k] = 'l'

    return (tbl, col_max_width)


def draw_static_tbl(data, fields, values):

    (tbl, col_max_width) = __mk_tbl(fields)

    for dataset in data:

        row_data = []

        for value in values:

            row_data.append('\n'.join(textwrap.wrap(dataset.get(value, '<N/A>'), col_max_width)))

        tbl.add_row(row_data)

    return tbl.get_string()


def draw_dict_tbl(dct, fields, keys):

    (tbl, col_max_width) = __mk_tbl(fields)

    for key in keys:

        row_data = [str(key).title()]

        row_data.append('\n'.join(textwrap.wrap(str(dct.get(key, '<N/A>')), col_max_width)))

        tbl.add_row(row_data)

    return tbl.get_string()


def draw_msgbox(string):

    msgbox = '\n'
    msgbox += '*' * 80 + '\n'
    msgbox += '*' + ' '.ljust(78) + '*' + '\n'
    msgbox += '*' + ' '.ljust(78) + '*' + '\n'
    msgbox += '*  ' + string.ljust(76) + '*' + '\n'
    msgbox += '*' + ' '.ljust(78) + '*' + '\n'
    msgbox += '*' + ' '.ljust(78) + '*' + '\n'
    msgbox += '*' * 80 + '\n'

    return msgbox

########NEW FILE########
__FILENAME__ = eval
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import types
import os
import shlex
import pythonect
import networkx


# Local imports

import miscellaneous


def __quotes_wrap(list):

    new_list = []

    for e in list:

        new_list.append("'%s'" % e)

    return new_list


def __hackersh_preprocessor(source, sym_tbl):

    orig_source = source

    # i.e. nmap

    if source in sym_tbl and not isinstance(sym_tbl[source], types.FunctionType):

        source = "%s()" % source

    # i.e. /usr/bin/nmap or ./nmap

    if source.startswith('/') or source.startswith('./') or source.startswith('../'):

        expression_cmd = shlex.split(source)

        external_component_path = os.path.abspath(expression_cmd[0])

        external_component_name = os.path.splitext(os.path.basename(external_component_path))[0]

        external_component_kwargs = '**{}'

        # External binary? (i.e. /bin/ls)

        if external_component_name not in sym_tbl:

            if not os.path.isfile(external_component_path):

                external_component_path = miscellaneous.which(expression_cmd[0])[0]

                if not external_component_path:

                    print '%s: command not found' % expression_cmd[0]

                    return False

            external_component_kwargs = "**{'path':'%s'}" % external_component_path

            external_component_name = "system"

            external_component_args = "*(%s)" % ','.join(__quotes_wrap(expression_cmd[1:]) + [' '])

        source = "%s(%s, %s)" % (external_component_name, external_component_args, external_component_kwargs)

    # print '%s => %s' % (orig_source, source)

    return source


def _hackersh_graph_transform(graph, hackersh_locals):

    # TODO: XSLT?

    for node in graph:

        graph.node[node]['CONTENT'] = __hackersh_preprocessor(graph.node[node]['CONTENT'].strip(), hackersh_locals)

    return graph


def parse(source):

    return pythonect.parse(source)


def eval(source, locals_):

    return_value = None

    graph = None

    if source != "pass":

        if not isinstance(source, networkx.DiGraph):

            graph = parse(source)

        else:

            graph = source

        return_value = pythonect.eval(_hackersh_graph_transform(graph, locals_), {}, locals_)

    return return_value

########NEW FILE########
__FILENAME__ = exceptions
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.


class HackershError(Exception):

    def __init__(self, context, msg):
        self.context = context
        self.msg = msg

########NEW FILE########
__FILENAME__ = log
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import logging


VERBOSE_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]


logging.basicConfig(format="%(asctime)s %(name)s: [%(levelname)s] %(message)s", datefmt='%b %d %R:%S', level=logging.ERROR)


# Default Logger

logger = logging.getLogger('hackersh')

########NEW FILE########
__FILENAME__ = miscellaneous
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import os
import shlex


def shell_split(s):
    lex = shlex.shlex(s)
    lex.quotes = '"'
    lex.whitespace_split = True
    lex.commenters = ''
    return list(lex)


# https://twistedmatrix.com/trac/browser/tags/releases/twisted-8.2.0/twisted/python/procutils.py

def which(name, flags=os.X_OK):

    result = []

    exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))

    path = os.environ.get('PATH', None)

    if path is None:

        return []

    for p in os.environ.get('PATH', '').split(os.pathsep):

        p = os.path.join(p, name)

        if os.access(p, flags):
            result.append(p)

        for e in exts:

            pext = p + e

            if os.access(pext, flags):
                result.append(pext)

    return result

########NEW FILE########
__FILENAME__ = objects
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

import os
import tempfile
import subprocess
import types
import xml.sax
import csv
import HTMLParser
import re


# Local imports

import log
import conio
import miscellaneous
import _ordereddict
import exceptions


# Component Classes

class Component(object):

    def __init__(self, *args, **kwargs):

        self.DEFAULT_STDIN_BUFFER = None

        self._args = args

        self._kwargs = kwargs

        self.logger = log.logging.getLogger(self.__class__.__name__.lower())

        if 'debug' in kwargs:

            self.logger.setLevel(log.logging.DEBUG)

        self.logger.debug('Initialized %s with args = %s and kwargs = %s' % (repr(self), args, kwargs))

    def __call__(self, arg):

        context = arg

        if not eval(self._kwargs.get('filter', self.DEFAULT_FILTER), {'context': context}):

                self.logger.debug("Filter %s is False" % self._kwargs.get('filter', self.DEFAULT_FILTER))

                raise exceptions.HackershError(context, "%s: not enough data to start" % self.__class__.__name__.lower())

        self.logger.debug("Filter %s is True" % self._kwargs.get('filter', self.DEFAULT_FILTER))

        component_args_as_str = eval(self._kwargs.get('query', self.DEFAULT_QUERY), {'context': context})

        self.logger.debug("Query = %s" % component_args_as_str)

        argv = []

        try:

            argv = miscellaneous.shell_split(self._args[0] + ' ' + component_args_as_str)

        except IndexError:

            try:

                argv = miscellaneous.shell_split(component_args_as_str)

            except Exception:

                # "AS IT IS"

                argv = [component_args_as_str]

        self.logger.debug('Running with argv = %s and context = %s' % (argv, repr(context)))

        context = self.run(argv, context)

        if context:

            if isinstance(context, list):

                for _context in context:

                    # Update STACK

                    _context.update({'STACK': _context.get('STACK', []) + [self.__class__.__name__]})

            else:

                # Don't iterate Generator, wrap it with another Generator

                if isinstance(context, types.GeneratorType):

                    # TODO: Add support for Generaor

                    pass

                else:

                    context.update({'STACK': context.get('STACK', []) + [self.__class__.__name__]})

        return context

    # Application Binary Interface-like

    def run(self, argv, context):

        raise NotImplementedError


class RootComponent(Component):

    def __call__(self, arg):

        argv = list(self._args) or [arg]

        self.logger.debug('Running with argv = %s and context = None' % argv)

        context = self.run(argv, None)

        if context:

            if isinstance(context, list):

                for _context in context:

                     # Add 'ROOT' and 'STACK'

                    _context.update({'ROOT': _context.get('ROOT', argv[0]), 'STACK': [self.__class__.__name__] + _context.get('STACK', [])})

            else:

                context.update({'ROOT': context.get('ROOT', argv[0]), 'STACK': [self.__class__.__name__] + context.get('STACK', [])})

        return context


class InternalComponent(Component):

    pass


class ExternalComponent(Component):

    def _execute(self, argv, context):

        raise NotImplementedError

    def run(self, argv, context):

        filename = self._kwargs.get('filename', self.DEFAULT_FILENAME)

        self.logger.debug('FILENAME = ' + filename)

        path = miscellaneous.which(filename)[:1]

        if not path:

            self.logger.debug("NO PATH!")

            raise exceptions.HackershError(context, "%s: command not found" % self._kwargs.get('filename', self.DEFAULT_FILENAME))

        self.logger.debug('PATH = ' + path[0])

        return self._processor(context, self._execute(path + argv, context))

    def _processor(self, context, data):

        raise NotImplementedError


class ExternalComponentReturnValueOutput(ExternalComponent):

    def _execute(self, argv, context):

        cmd = argv[0] + ' ' + self._kwargs.get('output_opts', self.DEFAULT_OUTPUT_OPTIONS) + " " + ' '.join(argv[1:])

        self.logger.debug('CMD = ' + cmd)

        p = subprocess.Popen(miscellaneous.shell_split(cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        p.wait()

        return p.returncode


class ExternalComponentStreamOutput(ExternalComponent):

    def __init__(self, *args, **kwargs):

        ExternalComponent.__init__(self, *args, **kwargs)

        self._handlers = []

        # Auto-discovery of Output Handlers

        for name in dir(self):

            obj = getattr(self, name)

            if isinstance(obj, types.ClassType) and issubclass(obj, OutputHandler):

                self._handlers.append(obj)

    def _execute(self, argv, context):

        tmpfile = tempfile.NamedTemporaryFile(delete=False)

        fname = tmpfile.name

        data = ""

        try:

            cmd = argv[0] + ' ' + self._kwargs.get('output_opts', self.DEFAULT_OUTPUT_OPTIONS) + " " + tmpfile.name + " " + ' '.join(argv[1:])

            self.logger.debug('CMD = ' + cmd)

            p = subprocess.Popen(miscellaneous.shell_split(cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            (stdout_output, stderr_output) = p.communicate(input=self._kwargs.get('stdin', self.DEFAULT_STDIN_BUFFER))

            self.logger.debug(stdout_output)

            tmpfile.flush()

            os.fsync(tmpfile.fileno())

            tmpfile.close()

            tmpfile = open(fname, 'r')

            data = tmpfile.read()

            self.logger.debug('DATA (%d bytes) = %s' % (len(data), data))

        except Exception:

            os.remove(fname)

        return data

    def _processor(self, context, data):

        if data:

            contexts = []

            # Do-while, try parse data with *every* possible Output Handler

            for handler in self._handlers:

                handler_instance = handler(context, contexts)

                handler_instance.parse(data)

            # No Output Handler could process output, unknown format?

            if not contexts:

                raise exceptions.HackershError(context, "%s: unable to parse: %s" % (self.__class__.__name__.lower(), str(data)))

            return contexts

        else:

            return data


class ExternalComponentFileOutput(ExternalComponentStreamOutput):

    def _execute(self, argv, context):

        tmpfile = tempfile.NamedTemporaryFile(delete=False)

        fname = tmpfile.name

        data = ""

        try:

            cmd = argv[0] + ' ' + self._kwargs.get('output_opts', self.DEFAULT_OUTPUT_OPTIONS) + " " + tmpfile.name + " " + ' '.join(argv[1:])

            self.logger.debug('CMD = ' + cmd)

            p = subprocess.Popen(miscellaneous.shell_split(cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            (stdout_output, stderr_output) = p.communicate(input=self._kwargs.get('stdin', self.DEFAULT_STDIN_BUFFER))

            self.logger.debug(stdout_output)

            tmpfile.flush()

            os.fsync(tmpfile.fileno())

            tmpfile.close()

            tmpfile = open(fname, 'r')

            data = tmpfile.read()

            self.logger.debug('DATA (%d bytes) = %s' % (len(data), data))

        except Exception:

            os.remove(fname)

        return data


class ExternalComponentStdoutOutput(ExternalComponentStreamOutput):

    def _execute(self, argv, context):

        cmd = argv[0] + ' ' + self._kwargs.get('output_opts', self.DEFAULT_OUTPUT_OPTIONS) + " " + ' '.join(argv[1:])

        self.logger.debug('CMD = ' + cmd)

        p = subprocess.Popen(miscellaneous.shell_split(cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        p_stdout = p.communicate(input=self._kwargs.get('stdin', self.DEFAULT_STDIN_BUFFER))[0]

        self.logger.debug('DATA (%d bytes) = %s' % (len(p_stdout), p_stdout))

        return p_stdout


# Datatype Classes

class OutputHandler:

    def __init__(self, context, output):

        self._context = context

        self._output = output

    def parse(self):

        raise NotImplementedError


# Pseudo SAX Content Handler for Simple Regualr Expression Match Handler

class SimpleRegExHandler(OutputHandler):

    def parse(self, data):

        regex = re.compile(self.PATTERN)

        for match in regex.finditer(data):

            self._output.append(self._context.__class__(self._context, **match.groupdict()))

    PATTERN = ""


# Pseudo SAX Content Handler for Stdout Output

class StdoutOutputHandler(OutputHandler):

    def startDocument():
        pass

    def endDocument():
        pass

    def parse(self, data):

        self.startDocument()

        self.feed(data)

        self.endDocument()


# Pseudo SAX Content Handler for CSV

class CSVOutputHandler(OutputHandler):

    def parse(self, data):

        self.startDocument()

        for row in csv.reader(data.split('\n'), delimiter=self.delimiter, quotechar=self.quotechar):

            self.startRow(row)

            self.endRow()

        self.endDocument()

    delimiter = csv.excel.delimiter

    quotechar = csv.excel.quotechar


# Pseudo SAX Content Handler for HTML

class HTMLOutputHandler(OutputHandler, HTMLParser.HTMLParser):

    def __init__(self, context, output):

        HTMLParser.HTMLParser.__init__(self)

        self._context = context

        self._output = output

    def parse(self, data):

        self.startDocument()

        self.feed(data)

        self.endDocument()


class XMLOutputHandler(OutputHandler, xml.sax.handler.ContentHandler):

    def __init__(self, context, output):

        xml.sax.handler.ContentHandler.__init__(self)

        self._context = context

        self._output = output

    def parse(self, data):

        xml.sax.parseString(data, self)


class SessionContext(_ordereddict.OrderedDict):

    def __getitem__(self, key):

        value = False

        try:

            # Case insensitive

            value = _ordereddict.OrderedDict.__getitem__(self, key.upper())

        except KeyError:

            pass

        return value


class RemoteSessionContext(SessionContext):

    def __init__(self, *args, **kwargs):

        SessionContext.__init__(self, *args, **kwargs)

    def _tree_str(self):

        # TCP / UDP ?

        if self['PROTO'] == 'TCP' or self['PROTO'] == 'UDP':

            return self['PORT'] + '/' + self['PROTO'].lower() + ' (' + self.get('SERVICE', '?') + ')'

        else:

            return ''

    def __str__(self):

        # Properties

        output = \
            '\n' + conio.draw_underline('Properties:') + '\n' + \
            conio.draw_dict_tbl(self, ["Property", "Value"], filter(lambda key: not key.startswith('_') and key != 'VULNERABILITIES', self.keys())) + '\n'

        # Vulnerabilities

        if 'VULNERABILITIES' in self:

            output = \
                output + '\n' + \
                conio.draw_underline('Vulnerabilities:') + '\n' + \
                conio.draw_static_tbl(self['VULNERABILITIES'], ["VULNERABILITY DESCRIPTION", "URL"], ["DESCRIPTION", "DESTINATION"]) + '\n'

        return output


class LocalSessionContext(SessionContext):

    pass


class SessionsTree(object):

    def __init__(self, children):

        self.children = []

        self.keys = _ordereddict.OrderedDict()

        # N

        if isinstance(children, list):

            # Remove False's

            self.children = filter(lambda x: not isinstance(x, bool), children)

        # 1

        elif not isinstance(children, bool):

            self.children.append(children)

        if self.children:

            children_roots = list(set([child.values()[0] for child in self.children]))

            # 1

            if len(children_roots) == 1:

                self.keys[children_roots[0]] = self

            # N

            else:

                for children_root in children_roots:

                    self.keys[children_root] = SessionsTree(filter(lambda child: child.values()[0] == children_root, self.children))

    def _tree_str(self):

        if self.keys:

            if len(self.keys) == 1:

                yield self.children[0].values()[0]

                last = self.children[-1] if self.children else None

                for child in self.children:

                    prefix = '  `-' if child is last else '  +-'

                    for line in child._tree_str().splitlines():

                        yield '\n' + prefix + line

                        prefix = '  ' if child is last else '  | '

                yield '\n'

            # N

            else:

                for key in self.keys.keys():

                    yield self.keys[key]

        else:

            yield "Error\n"

    def __str__(self):

        return reduce(lambda x, y: str(x) + str(y), self._tree_str())

    def __getitem__(self, key):

        return self.keys.get(key, False)

########NEW FILE########
__FILENAME__ = _ordereddict
# Copyright (C) 2013 Itzik Kotler
#
# This file is part of Hackersh.
#
# Hackersh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# Hackersh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hackersh; see the file COPYING.  If not,
# see <http://www.gnu.org/licenses/>.

try:

    # Python 2.7+

    from collections import OrderedDict

except Exception as e:

    # Python2.6

    from ordereddict import OrderedDict

########NEW FILE########
__FILENAME__ = _version
__version__ = '0.2.0'

########NEW FILE########
