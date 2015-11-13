__FILENAME__ = amap
#!/usr/bin/env python

from os import path, environ, pathsep
from subprocess import Popen, PIPE
from re import findall


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'AmapReportParser',
    'AmapScanner'
]


class AmapReportParser(object):

    def __init__(self, input):
        self.output = input

    @property
    def banners(self):
        return findall('Protocol on (.+?) matches (.+?) - banner: (.+)', self.output)


class AmapScanner(object):

    output = ''
    cmd = ''

    def getversion(self):
        for p in environ['PATH'].split(pathsep):
            program = path.join(p, 'amap')
            if path.exists(program):
                self.program = program
                self.version = self.run([])
                return True
        return False

    def run(self, args):
        self.cmd = ' '.join([self.program]+args)
        self._pipe = Popen([self.program]+args, stdin=PIPE, stdout=PIPE)
        r, e = self._pipe.communicate()
        self.output = r

        return r.strip('\n')

    def __init__(self):
        if not self.getversion():
            raise OSError('Could not find amap, check your OS path')

    def scan(self, args, sendto=AmapReportParser):
        r = self.run(args)
        if callable(sendto):
            return sendto(r)
        return sendto.write(r)

    def terminate(self):
        self._pipe.terminate()

    def __del__(self):
        try:
            self.terminate()
        except OSError:
            pass
########NEW FILE########
__FILENAME__ = nmap
#!/usr/bin/env python

from os import path, pathsep, environ
from subprocess import Popen, PIPE

from lxml.etree import XML

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'NmapReportParser',
    'NmapScanner'
]


def NmapReportParser(output):
    if not output:
        return None
    elif 'xmloutputversion="1.03"' in output:
        return NmapReportVersion103(output)
    elif 'xmloutputversion="1.04"' in output:
        return NmapReportVersion104(output)
    raise NotImplementedError('Nmap 5.x and 6.x XML reports are the only supported formats')


class NmapReportBase(object):

    def __init__(self, output):
        self.output = output
        self.xml = XML(output)

    @property
    def addresses(self):
        raise NotImplementedError

    @property
    def report(self):
        return self.output

    def mac(self, address):
        raise NotImplementedError

    def _host(self, address):
        raise NotImplementedError

    def ports(self, address):
        raise NotImplementedError

    @property
    def scaninfo(self):
        raise NotImplementedError

    @property
    def verbosity(self):
        raise NotImplementedError

    @property
    def debugging(self):
        raise NotImplementedError

    def hostnames(self, address):
        raise NotImplementedError

    def times(self, address):
        raise NotImplementedError

    @property
    def runstats(self):
        raise NotImplementedError

    def scanstats(self, address):
        raise NotImplementedError

    def status(self, address):
        raise NotImplementedError

    @property
    def nmaprun(self):
        raise NotImplementedError

    def tobanner(self, port):
        raise NotImplementedError

    @property
    def greppable(self):
        raise NotImplementedError


class NmapReportVersion103(NmapReportBase):

    def os(self, address):
        host = self._host(address)
        if host is not None:
            r = {
                'osmatch': [osm.attrib for osm in host.findall('os/osmatch')],
                'osclass': [osm.attrib for osm in host.findall('os/osclass')],
                'portused': host.find('os/portused').attrib  if host.find('os/portused') is not None else {}
            }
            return r
        return { 'osmatch' : [], 'osclass' : [], 'portused' : {} }

    @property
    def addresses(self):
        return [ a.get('addr') for a in self.xml.xpath('host/address[@addrtype="ipv4" or @addrtype="ipv6"]') ]

    def mac(self, address):
        host = self._host(address)
        if host is not None:
            address = host.find('address[@addrtype="mac"]')
            if address is not None:
                return address.get('addr')
        return None

    def _host(self, address):
        return self.xml.xpath('host[address[@addr="%s"]]' % address.replace('"', ''))[0]

    def ports(self, address):
        host = self._host(address)
        ports = []
        if host is not None:
            for p in host.findall('ports/port'):
                r = dict(p.attrib)
                r['script'] = {}
                for child in p.getchildren():
                    if child.tag == 'script':
                        r['script'][child.get('id')] = child.get('output')
                    else:
                        r.update(child.attrib)
                ports.append(r)
        return ports

    @property
    def scaninfo(self):
        return self.xml.find('scaninfo').attrib

    @property
    def verbosity(self):
        return self.xml.find('verbose').get('level')

    @property
    def debugging(self):
        return self.xml.find('debugging').get('level')

    def hostnames(self, address):
        host = self._host(address)
        if host is not None:
            return [ hn.attrib for hn in host.findall('hostnames/hostname') ]
        return []

    def times(self, address):
        host = self._host(address)
        if host is not None:
            return host.find('times').attrib
        return {}

    @property
    def runstats(self):
        rs = {}
        map(lambda x: rs.update(x.attrib), self.xml.find('runstats').getchildren())
        return rs

    def scanstats(self, address):
        host = self._host(address)
        if host is not None:
            return host.attrib
        return {}

    def status(self, address):
        host = self._host(address)
        if host is not None:
            return host.find('status').attrib
        return {}

    @property
    def nmaprun(self):
        return self.xml.attrib

    def tobanner(self, port):
        banner = port.get('product', 'Unknown')
        version = port.get('version')
        if version is not None:
            banner += ' %s' % version
        extrainfo = port.get('extrainfo')
        if extrainfo is not None:
            banner += ' (%s)' % extrainfo
        return banner

    @property
    def greppable(self):
        n = self.nmaprun
        output = '# Nmap %s scan initiated %s as: %s\n' % (n['version'], n['startstr'], n['args'])
        for a in self.addresses:
            s = self.status(a)
            output += 'Host: %s () Status: %s\n' % (a, s['state'].title())
            output += 'Host: %s () Ports:' % a
            for p in self.ports(a):
                output += ' %s/%s/%s//%s///,' % (p['portid'], p['state'], p['protocol'], p['name'])
            output = output.rstrip(',')
        output += '\n# %s\n' % self.runstats['summary']
        return output


class NmapReportVersion104(NmapReportVersion103):
    pass


class NmapScanner(object):

    output = ''
    cmd = ''

    def getversion(self, binargs=[], binpath=None):
        if binargs:
            self.program = binargs if isinstance(binargs, list) else [ binargs ]
            self.version = self.run(['--version'])
            return True
        elif binpath is None:
            for p in environ['PATH'].split(pathsep):
                program = path.join(p, 'nmap')
                if path.exists(program):
                    self.program = [ program ]
                    self.version = self.run(['--version'])
                    return True
        elif path.exists(binpath):
            self.program = [ binpath ]
            self.version = self.run(['--version'])
            return True
        return False

    def run(self, args):
        self.cmd = ' '.join(self.program + args)
        self._pipe = Popen(self.program + args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        r, e = self._pipe.communicate()
        self.output = r
        self.error = e

        return r.strip('\n')

    def __init__(self, binargs=[], binpath=None):
        if not self.getversion(binargs, binpath):
            raise OSError('Could not find nmap, check your OS path')

    def scan(self, target, *args, **kwargs):
        args = list(args)
        if ':' in target and '-6' not in args:
            args.append('-6')
        r = self.run([target, '-oX', '-'] + args)
        sendto = kwargs.get('sendto', NmapReportParser)
        if callable(sendto):
            return sendto(r)
        return sendto.write(r)

    def terminate(self):
        self._pipe.terminate()

    def __del__(self):
        try:
            self.terminate()
        except OSError:
            pass
########NEW FILE########
__FILENAME__ = p0f
# !/usr/bin/env python

import subprocess
from canari.maltego.utils import debug

from canari.utils.fs import cookie
from canari.config import config
from scapy.all import conf

from ctypes import Structure, c_ubyte, c_uint32, c_uint16, addressof, sizeof, POINTER, string_at, c_char_p, cast
from socket import socket, AF_UNIX, AF_INET, AF_INET6, inet_pton
import os
from numbers import Number


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'P0fMagic',
    'P0fStatus',
    'P0fAddr',
    'P0fMatch',
    'P0fError',
    'fingerprint'
]


class P0fApiQuery(Structure):
    _fields_ = [
        ('magic', c_uint32),
        ('addr_type', c_ubyte),
        ('addr', c_ubyte * 16)
    ]


class P0fApiResponse(Structure):
    _fields_ = [
        ('magic', c_uint32),
        ('status', c_uint32),
        ('first_seen', c_uint32),
        ('last_seen', c_uint32),
        ('total_conn', c_uint32),
        ('uptime_min', c_uint32),
        ('up_mod_days', c_uint32),
        ('last_nat', c_uint32),
        ('last_chg', c_uint32),
        ('distance', c_uint16),
        ('bad_sw', c_ubyte),
        ('os_match_q', c_ubyte),
        ('os_name', c_ubyte * 32),
        ('os_flavor', c_ubyte * 32),
        ('http_name', c_ubyte * 32),
        ('http_flavor', c_ubyte * 32),
        ('link_type', c_ubyte * 32),
        ('language', c_ubyte * 32),
    ]


class P0fMagic:
    Query = 0x50304601
    Response = 0x50304602


class P0fStatus:
    BadQuery = 0x00
    OK = 0x10
    NoMatch = 0x20


class P0fAddr:
    IPv4 = 0x04
    IPv6 = 0x06


class P0fMatch:
    Fuzzy = 0x01
    Generic = 0x02


class P0fError(Exception):
    pass


def fingerprint(ip):
    iface = conf.route.route(ip)[0]
    us = cookie('.sploitego.p0f.%s.sock' % iface)

    if not os.path.exists(us):
        log = cookie('.sploitego.p0f.%s.log' % iface)
        cmd = os.path.join(config['p0f/path'], 'p0f')
        fpf = os.path.join(config['p0f/path'], 'p0f.fp')
        p = subprocess.Popen(
            [cmd, '-d', '-s', us, '-o', log, '-f', fpf, '-i', iface, '-u', 'nobody'],
            stdout=subprocess.PIPE
        )
        debug(*p.communicate()[0].split('\n'))
        debug(
            "!!!!!!!!!!!!!!!!!!!!!!!!!! WARNING !!!!!!!!!!!!!!!!!!!!!!!!!!",
            "! IF THIS TRANSFORM IS STILL RUNNING THEN SHUT IT DOWN AND  !",
            "! TRY AGAIN! THERE IS A BUG IN MALTEGO THAT DOES NOT        !",
            "! TERMINATE TRANSFORMS IF A TRANSFORM SPAWNS A CHILD        !",
            "! PROCESS. PLEASE BUG SUPPORT@PATERVA.COM FOR A FIX.        !",
            "!!!!!!!!!!!!!!!!!!!!!!!!!! WARNING !!!!!!!!!!!!!!!!!!!!!!!!!!",
        )
        if p.returncode:
            raise P0fError('Could not locate or successfully execute the p0f executable.')
        return {'status': P0fStatus.NoMatch}

    r = P0fApiQuery()
    r.magic = P0fMagic.Query

    if ':' in ip:
        r.addr_type = P0fAddr.IPv6
        ip = inet_pton(AF_INET6, ip)
    else:
        r.addr_type = P0fAddr.IPv4
        ip = inet_pton(AF_INET, ip)

    for i, a in enumerate(ip):
        r.addr[i] = ord(a)

    s = socket(AF_UNIX)
    s.connect(us)
    s.send(string_at(addressof(r), sizeof(r)))
    data = c_char_p(s.recv(sizeof(P0fApiResponse)))
    pr = cast(data, POINTER(P0fApiResponse)).contents
    s.close()

    if pr.status == P0fStatus.BadQuery:
        raise P0fError('P0f could not understand the query.')

    return dict(
        (
            fn,
            getattr(pr, fn) if isinstance(getattr(pr, fn), Number) else string_at(getattr(pr, fn))
        ) for fn, ft in pr._fields_
    )
########NEW FILE########
__FILENAME__ = exploit
#!/usr/bin/env python
import sys
from time import sleep
from re import sub, findall

from PySide.QtCore import *
from PySide.QtGui import *

from ui.exploit import Ui_MainWindow


class ComboBox(QComboBox):

    def __init__(self, dict_, key, items, default=None, tooltip=None, parent=None):
        super(ComboBox, self).__init__(parent)

        self.setObjectName('%sComboBox' % key.replace(' ', ''))

        # properties
        self.dict_ = dict_
        self.key = key
        self.setItems(items)

        # UI stuff
        if tooltip is not None:
            self.setToolTip(tooltip)

        self.currentIndexChanged.connect(self.updateDataSource)

        self.changeCurrentValue(default)


    def changeCurrentValue(self, value):
        index = self.findData(value)
        if index == -1:
            index = 0
        self.setCurrentIndex(index)
        self.currentIndexChanged.emit(index)


    def setItems(self, value):
        self.clear()
        if isinstance(value, dict):
            for k, v in value.iteritems():
                self.addItem(v, k)
        else:
            for i in value:
                self.addItem(i, i)

    def updateDataSource(self, index):
        self.dict_[self.key] = self.itemData(self.currentIndex())


class SpinBox(QSpinBox):

    def __init__(self, dict_, key, default=0, range_=(-2147483648, 2147483647), tooltip=None, parent=None):
        super(SpinBox, self).__init__(parent)

        self.setObjectName('%sSpinBox' % key.replace(' ', ''))
        self.setRange(*range_)

        # properties
        self.dict_ = dict_
        self.key = key

        # UI stuff
        if tooltip is not None:
            self.setToolTip(tooltip)

        self.valueChanged.connect(self.updateDataSource)

        self.setValue(default)

    def updateDataSource(self, value):
        self.dict_[self.key] = value


class CheckBox(QCheckBox):

    def __init__(self, dict_, key, default=False, tooltip=None, parent=None):
        super(CheckBox, self).__init__(parent)

        self.setObjectName('%sCheckBox' % key.replace(' ', ''))

        # properties
        self.dict_ = dict_
        self.key = key

        # UI stuff
        if tooltip is not None:
            self.setToolTip(tooltip)

        self.stateChanged.connect(self.updateDataSource)

        self.changeState(default)

    def changeState(self, state):
        state = Qt.CheckState.Checked if state else Qt.CheckState.Unchecked
        self.setCheckState(state)
        self.stateChanged.emit(state)

    def updateDataSource(self, value):
        self.dict_[self.key] = bool(value)


class LineEdit(QLineEdit):

    def __init__(self, dict_, key, default='', tooltip=None, parent=None):
        super(LineEdit, self).__init__(parent)

        self.setObjectName('%sLineEdit' % key.replace(' ', ''))

        # properties
        self.dict_ = dict_
        self.key = key

        # UI stuff
        if tooltip is not None:
            self.setToolTip(tooltip)

        self.editingFinished.connect(self.updateDataSource)

        self.changeText(default)

    def changeText(self, text):
        if not isinstance(text, basestring):
            text = str(text)
        self.setText(text)
        self.editingFinished.emit()

    def updateDataSource(self):
        self.dict_[self.key] = self.text()


class Label(QLabel):

    def __init__(self, name, label, tooltip=None, bold=False, parent=None):
        super(Label, self).__init__(parent)

        self.setObjectName('%sLabel' % name.replace(' ', ''))

        self.setText(label)

        if tooltip is not None:
            self.setToolTip(tooltip)

        if bold:
            font = QFont()
            font.setBold(True)
            font.setWeight(75)
            self.setFont(font)


class ExploitWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, msfrpc, defaults, filter_=None, parent=None):
        QMainWindow.__init__(self, parent)
        self.defaults = defaults
        self.sessionid = -1
        self.exploits = []
        self.setupUi(self)
        self.exploitCommandLinkButton.clicked.connect(self.exploit)
        self._msfInit(msfrpc, filter_)

    def _msfInit(self, msfrpc, filter_):
        self.rpc = msfrpc
        self.m = self.rpc.modules

        if filter_ is not None:
            c = self.rpc.consoles.console()
            c.read() # get banner out of the way
            c.write('search %s' % filter_)
            while True:
                d = c.read()
                if not d['busy']:
                    self.exploits.extend(findall('exploit/([^\s]+)', d['data']))
                    break
                sleep(1)
        if not self.exploits:
            self.exploits.extend(self.rpc.modules.exploits)

        for i, e in enumerate(self.exploits):
            self.exploitComboBox.addItem(e)

        self.exploitComboBox.currentIndexChanged.connect(self._exploitChanged)
        self.exploitComboBox.setCurrentIndex(0)
        self.exploitComboBox.currentIndexChanged.emit(0)

    def _exploitChanged(self, index):
        self.e = self.m.use('exploit', self.exploits[index])
        self.setWindowTitle(self.e.name)
        self._setDescription()
        self._populatePages()
        if hasattr(self, 'targetComboBox'):
            del self.targetComboBox
            del self.payloadComboBox
        self._initTargetComboBox()

    def _setDescription(self):
        d = sub(r'\t+', '', self.e.description)
        d = sub(r'([^\n])\n([^\n])', r'\1 \2', d).strip(' ').strip('\n')
        self.descriptionTextBrowser.setText(d)

    def _populatePages(self):

        # Clear all layouts
        for layout in [self.requiredFormLayout, self.evasionFormLayout, self.advancedFormLayout]:
            self.clearLayout(layout)

        # Create dynamic forms
        for i in self.e.options:
            o = self.e.optioninfo(i)

            # set any defaults
            if i in self.defaults:
                self.e.optioninfo(i)['default'] = self.defaults[i]

            # default is required page
            page = self.requiredOptionsPage
            layout = self.requiredFormLayout

            # is it evasion option?
            if o['evasion']:
                page = self.evasionOptionsPage
                layout = self.evasionFormLayout
            # is it advanced option?
            elif o['advanced']:
                page = self.advancedOptionsPage
                layout = self.advancedFormLayout
                # add to layout
            self._populate(page, layout, i, o, self.e)



    def exploit(self):
        j = None
        try:
            j = self.e.execute(payload=self.p)
        except TypeError, e:
            qmb = QMessageBox()
            qmb.setWindowTitle('Error!')
            qmb.setText(str(e))
            qmb.exec_()
            return
        self.hide()
        if j['job_id'] is not None:
            while j['job_id'] in self.rpc.jobs.list:
                sleep(1)
            timeout = self.e.runoptions.get('ConnectTimeout', 10)
            for i in range(timeout):
                sessions = self.rpc.sessions.list
                for k in sessions:
                    if sessions[k]['exploit_uuid'] == j['uuid']:
                        self.sessionid = k
                        break
                sleep(1)
        self.close()


    def _initTargetComboBox(self):
        self.targetComboBox = self._populate(
            self.requiredOptionsPage,
            self.requiredFormLayout,
            'TARGET',
            {
                'default': 0,
                'type': 'targets',
                'enums': self.e.targets,
                'required': True
            },
            self
        )[1]

    def __setitem__(self, key, value):
        if key == 'TARGET' and value is not None:
            self.e.target = value
            self._targetChanged(value)
        elif key == 'PAYLOAD' and value is not None:
            self._payloadChanged(value)

    def _targetChanged(self, target):
        if not hasattr(self, 'payloadComboBox'):
            self._initPayloadComboBox()
        self.payloadComboBox.setItems(self.e.targetpayloads(target))

    def _initPayloadComboBox(self):
        payloads = self.e.targetpayloads(0)

        self.payloadComboBox = self._populate(
            self.requiredOptionsPage,
            self.requiredFormLayout,
            'PAYLOAD',
            {
                'default': payloads[0],
                'type': 'enum',
                'enums': payloads,
                'required' : True
            },
            self
        )[1]

    def clearLayout(self, layout):
        while layout.count():
            c = layout.takeAt(0)
            c.widget().deleteLater()

    def _payloadChanged(self, payload):

        self.clearLayout(self.payloadFormLayout)

        self.p = self.m.use('payload', payload)

        for i in self.p.options:
            if i not in ['RHOST', 'WORKSPACE']:
                self._populate(
                    self.payloadGroupBox,
                    self.payloadFormLayout,
                    i,
                    self.p.optioninfo(i),
                    self.p
                )



    def _populate(self, page, layout, name, optioninfo, dataset):
        type_ = optioninfo['type']
        default = optioninfo.get('default')
        description = optioninfo['desc'] if 'desc' in optioninfo else None

        if default is None:
            if type_ == 'bool':
                default = False
            elif type_ in ['integer', 'port']:
                default = 0
            else:
                default = ''

        l = Label(
            '%sLabel' % name.replace(' ', ''),
            '%s:' % name,
            description,
            optioninfo['required'],
            page
        )

        f = None

        if type_ == 'bool':
            f = CheckBox(dataset, name, default, description, page)
        elif type_ == 'integer':
            f = SpinBox(dataset, name, default, tooltip=description, parent=page)
        elif type_ == 'port':
            f = SpinBox(dataset, name, default, (0, 65535), description, page)
        elif type_ == 'enum':
            f = ComboBox(dataset, name, optioninfo['enums'], default, description, page)
        elif type_ == 'targets':
            f = ComboBox(dataset, name, optioninfo['enums'], default, description, page)
        else:
            f = LineEdit(dataset, name, default, description, page)

        layout.addRow(l, f)
        return l, f

def launch(msfrpc, defaults, filter_=None):
    app = QApplication(sys.argv)
    w = ExploitWindow(msfrpc, defaults, filter_)
    w.show()
    if sys.platform == 'darwin':
        from subprocess import Popen
        Popen(['osascript', '-e', 'tell application "Python" to activate'])
    app.exec_()
    return w.sessionid

########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/env python
from Tkinter import Tk
import sys
from PySide.QtGui import QMainWindow, QApplication, QTextCursor
from PySide.QtCore import SIGNAL

from metasploit.msfconsole import MsfRpcConsole
from metasploit.msfrpc import MsfRpcClient
from ui.shell import Ui_MainWindow

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = [ 'Nadeem Douba' ]

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


class MsfShellWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, msfrpc, **kwargs):
        QMainWindow.__init__(self, kwargs.pop('parent', None))
        self.setupUi(self)
        self.setWindowTitle('Metasploit Console')
        self._initCommandLine()
        self._msfInit(msfrpc, **kwargs)

    def _msfInit(self, msfrpc, **kwargs):
        self.connect(self.outputTextBrowser, SIGNAL('textChanged(QString)'), self._getOutput)
        self.prompt = 'msf >'
        self.c = MsfRpcConsole(msfrpc, sessionid=kwargs.get('sessionid'),cb=self._emitSignal)
        if 'command' in kwargs:
            self.commanderLineEdit.setText(kwargs['command'])
            self.commanderLineEdit.emit(SIGNAL('returnPressed()'))

    def _emitSignal(self, d):
        self.outputTextBrowser.emit(SIGNAL('textChanged(QString)'), repr(d))

    def _initCommandLine(self):
        self.connect(self.commanderLineEdit, SIGNAL('returnPressed()'), self._sendCommand)
        self.vb = self.outputTextBrowser.verticalScrollBar()

    def _sendCommand(self):
        c = self.outputTextBrowser.textCursor()
        c.movePosition(QTextCursor.End)
        self.outputTextBrowser.setTextCursor(c)
        cmd = str(self.commanderLineEdit.text())
        if cmd == 'exit':
            self.close()
            return
        self.c.execute(cmd)
        self.outputTextBrowser.insertHtml('%s<br>' % cmd)
        self.commanderLineEdit.clear()
        self.vb.setValue(self.vb.maximum())

    def _getOutput(self, d):
        d = eval(str(d))
        self.prompt = d['prompt']
        self.outputTextBrowser.insertPlainText('\n%s\n' % d['data'])
        self.outputTextBrowser.insertHtml('<font color="red"><b>%s</b></font><font color="black">&nbsp;</font>' % self.prompt)
        self.vb.setValue(self.vb.maximum())

    def closeEvent(self, event):
        self.c.__del__()
        QMainWindow.close(self)


def launch(msfrpc, **kwargs):
    app = QApplication(sys.argv)
    MsfShellWindow(msfrpc, **kwargs).show()
    if sys.platform == 'darwin':
        from subprocess import Popen
        Popen(['osascript', '-e', 'tell application "Python" to activate'])
    app.exec_()
########NEW FILE########
__FILENAME__ = exploit
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created: Sun Apr  8 20:11:13 2012
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(573, 783)
        self.centralWidget = QtGui.QWidget(MainWindow)
        self.centralWidget.setObjectName(_fromUtf8("centralWidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.centralWidget)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.scrollArea = QtGui.QScrollArea(self.centralWidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName(_fromUtf8("scrollArea"))
        self.scrollAreaWidgetContents = QtGui.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 547, 663))
        self.scrollAreaWidgetContents.setObjectName(_fromUtf8("scrollAreaWidgetContents"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.toolBox = QtGui.QToolBox(self.scrollAreaWidgetContents)
        self.toolBox.setObjectName(_fromUtf8("toolBox"))
        self.informationPage = QtGui.QWidget()
        self.informationPage.setGeometry(QtCore.QRect(0, 0, 523, 503))
        self.informationPage.setObjectName(_fromUtf8("informationPage"))
        self.verticalLayout_4 = QtGui.QVBoxLayout(self.informationPage)
        self.verticalLayout_4.setObjectName(_fromUtf8("verticalLayout_4"))
        self.line_0 = QtGui.QFrame(self.informationPage)
        self.line_0.setFrameShape(QtGui.QFrame.HLine)
        self.line_0.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_0.setObjectName(_fromUtf8("line"))
        self.verticalLayout_4.addWidget(self.line_0)
        self.exploitLabel = QtGui.QLabel(self.informationPage)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.exploitLabel.sizePolicy().hasHeightForWidth())
        self.exploitLabel.setSizePolicy(sizePolicy)
        self.boldFont = QtGui.QFont()
        self.boldFont.setBold(True)
        self.boldFont.setWeight(75)
        self.exploitLabel.setFont(self.boldFont)
        self.exploitLabel.setObjectName(_fromUtf8("label"))
        self.verticalLayout_4.addWidget(self.exploitLabel)
        self.exploitComboBox = QtGui.QComboBox(self.informationPage)
        self.exploitComboBox.setObjectName(_fromUtf8("exploitComboBox"))
        self.verticalLayout_4.addWidget(self.exploitComboBox)
        self.line_1 = QtGui.QFrame(self.informationPage)
        self.line_1.setFrameShape(QtGui.QFrame.HLine)
        self.line_1.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_1.setObjectName(_fromUtf8("line"))
        self.verticalLayout_4.addWidget(self.line_1)
        self.descriptionLabel = QtGui.QLabel(self.informationPage)
        self.descriptionLabel.setSizePolicy(sizePolicy)
        self.boldFont = QtGui.QFont()
        self.boldFont.setBold(True)
        self.boldFont.setWeight(75)
        self.descriptionLabel.setFont(self.boldFont)
        self.descriptionLabel.setObjectName(_fromUtf8("label"))
        self.verticalLayout_4.addWidget(self.descriptionLabel)
        self.descriptionTextBrowser = QtGui.QLabel(self.informationPage)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.descriptionTextBrowser.sizePolicy().hasHeightForWidth())
        self.descriptionTextBrowser.setSizePolicy(sizePolicy)
        self.descriptionTextBrowser.setAutoFillBackground(False)
        self.descriptionTextBrowser.setStyleSheet(_fromUtf8("background-color: white;"))
        self.descriptionTextBrowser.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.descriptionTextBrowser.setWordWrap(True)
        self.descriptionTextBrowser.setMargin(5)
        self.descriptionTextBrowser.setIndent(5)
        self.descriptionTextBrowser.setObjectName(_fromUtf8("descriptionLabel"))
        self.verticalLayout_4.addWidget(self.descriptionTextBrowser)
        self.line_2 = QtGui.QFrame(self.informationPage)
        self.line_2.setFrameShape(QtGui.QFrame.HLine)
        self.line_2.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_2.setObjectName(_fromUtf8("line_2"))
        self.verticalLayout_4.addWidget(self.line_2)
        self.toolBox.addItem(self.informationPage, _fromUtf8(""))
        self.requiredOptionsPage = QtGui.QWidget()
        self.requiredOptionsPage.setGeometry(QtCore.QRect(0, 0, 523, 503))
        self.requiredOptionsPage.setObjectName(_fromUtf8("requiredOptionsPage"))
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.requiredOptionsPage)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.line_3 = QtGui.QFrame(self.requiredOptionsPage)
        self.line_3.setFrameShape(QtGui.QFrame.HLine)
        self.line_3.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_3.setObjectName(_fromUtf8("line_3"))
        self.verticalLayout_3.addWidget(self.line_3)
        self.requiredFormLayout = QtGui.QFormLayout()
        self.requiredFormLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.requiredFormLayout.setLabelAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.requiredFormLayout.setObjectName(_fromUtf8("requiredFormLayout"))
        self.verticalLayout_3.addLayout(self.requiredFormLayout)
        self.line_9 = QtGui.QFrame(self.requiredOptionsPage)
        self.line_9.setFrameShape(QtGui.QFrame.HLine)
        self.line_9.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_9.setObjectName(_fromUtf8("line_9"))
        self.verticalLayout_3.addWidget(self.line_9)
        self.payloadGroupBox = QtGui.QGroupBox(self.requiredOptionsPage)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.payloadGroupBox.sizePolicy().hasHeightForWidth())
        self.payloadGroupBox.setSizePolicy(sizePolicy)
        self.payloadGroupBox.setObjectName(_fromUtf8("payloadGroupBox"))
        self.verticalLayout_7 = QtGui.QVBoxLayout(self.payloadGroupBox)
        self.verticalLayout_7.setObjectName(_fromUtf8("verticalLayout_7"))
        self.payloadFormLayout = QtGui.QFormLayout()
        self.payloadFormLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.payloadFormLayout.setObjectName(_fromUtf8("payloadFormLayout"))
        self.verticalLayout_7.addLayout(self.payloadFormLayout)
        self.verticalLayout_3.addWidget(self.payloadGroupBox)
        self.line_4 = QtGui.QFrame(self.requiredOptionsPage)
        self.line_4.setFrameShape(QtGui.QFrame.HLine)
        self.line_4.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_4.setObjectName(_fromUtf8("line_4"))
        self.verticalLayout_3.addWidget(self.line_4)
        self.toolBox.addItem(self.requiredOptionsPage, _fromUtf8(""))
        self.advancedOptionsPage = QtGui.QWidget()
        self.advancedOptionsPage.setGeometry(QtCore.QRect(0, 0, 523, 503))
        self.advancedOptionsPage.setObjectName(_fromUtf8("advancedOptionsPage"))
        self.verticalLayout_5 = QtGui.QVBoxLayout(self.advancedOptionsPage)
        self.verticalLayout_5.setObjectName(_fromUtf8("verticalLayout_5"))
        self.line_8 = QtGui.QFrame(self.advancedOptionsPage)
        self.line_8.setFrameShape(QtGui.QFrame.HLine)
        self.line_8.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_8.setObjectName(_fromUtf8("line_8"))
        self.verticalLayout_5.addWidget(self.line_8)
        self.advancedFormLayout = QtGui.QFormLayout()
        self.advancedFormLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.advancedFormLayout.setObjectName(_fromUtf8("advancedFormLayout"))
        self.verticalLayout_5.addLayout(self.advancedFormLayout)
        self.line_7 = QtGui.QFrame(self.advancedOptionsPage)
        self.line_7.setFrameShape(QtGui.QFrame.HLine)
        self.line_7.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_7.setObjectName(_fromUtf8("line_7"))
        self.verticalLayout_5.addWidget(self.line_7)
        self.toolBox.addItem(self.advancedOptionsPage, _fromUtf8(""))
        self.evasionOptionsPage = QtGui.QWidget()
        self.evasionOptionsPage.setGeometry(QtCore.QRect(0, 0, 523, 503))
        self.evasionOptionsPage.setObjectName(_fromUtf8("evasionOptionsPage"))
        self.verticalLayout_6 = QtGui.QVBoxLayout(self.evasionOptionsPage)
        self.verticalLayout_6.setObjectName(_fromUtf8("verticalLayout_6"))
        self.line_6 = QtGui.QFrame(self.evasionOptionsPage)
        self.line_6.setFrameShape(QtGui.QFrame.HLine)
        self.line_6.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_6.setObjectName(_fromUtf8("line_6"))
        self.verticalLayout_6.addWidget(self.line_6)
        self.evasionFormLayout = QtGui.QFormLayout()
        self.evasionFormLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.evasionFormLayout.setObjectName(_fromUtf8("evasionFormLayout"))
        self.verticalLayout_6.addLayout(self.evasionFormLayout)
        self.line_5 = QtGui.QFrame(self.evasionOptionsPage)
        self.line_5.setFrameShape(QtGui.QFrame.HLine)
        self.line_5.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_5.setObjectName(_fromUtf8("line_5"))
        self.verticalLayout_6.addWidget(self.line_5)
        self.toolBox.addItem(self.evasionOptionsPage, _fromUtf8(""))
        self.verticalLayout_2.addWidget(self.toolBox)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout.addWidget(self.scrollArea)
        self.exploitCommandLinkButton = QtGui.QCommandLinkButton(self.centralWidget)
        self.exploitCommandLinkButton.setObjectName(_fromUtf8("exploitCommandLinkButton"))
        self.exploitCommandLinkButton.setStyleSheet('font: 14pt;')
        self.verticalLayout.addWidget(self.exploitCommandLinkButton)
        MainWindow.setCentralWidget(self.centralWidget)
        self.menuBar = QtGui.QMenuBar(MainWindow)
        self.menuBar.setGeometry(QtCore.QRect(0, 0, 573, 22))
        self.menuBar.setObjectName(_fromUtf8("menuBar"))
        MainWindow.setMenuBar(self.menuBar)
        self.mainToolBar = QtGui.QToolBar(MainWindow)
        self.mainToolBar.setObjectName(_fromUtf8("mainToolBar"))
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.mainToolBar)
        self.statusBar = QtGui.QStatusBar(MainWindow)
        self.statusBar.setObjectName(_fromUtf8("statusBar"))
        MainWindow.setStatusBar(self.statusBar)

        self.retranslateUi(MainWindow)
        self.toolBox.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "MainWindow", None, QtGui.QApplication.UnicodeUTF8))
        self.exploitLabel.setText(QtGui.QApplication.translate("MainWindow", "Exploit:", None, QtGui.QApplication.UnicodeUTF8))
        self.descriptionLabel.setText(QtGui.QApplication.translate("MainWindow", "Description:", None, QtGui.QApplication.UnicodeUTF8))
        self.descriptionTextBrowser.setText(QtGui.QApplication.translate("MainWindow", "TextLabel", None, QtGui.QApplication.UnicodeUTF8))
        self.toolBox.setItemText(self.toolBox.indexOf(self.informationPage), QtGui.QApplication.translate("MainWindow", "Exploit Information", None, QtGui.QApplication.UnicodeUTF8))
        self.payloadGroupBox.setTitle(QtGui.QApplication.translate("MainWindow", "Payload Options", None, QtGui.QApplication.UnicodeUTF8))
        self.toolBox.setItemText(self.toolBox.indexOf(self.requiredOptionsPage), QtGui.QApplication.translate("MainWindow", "Required Options", None, QtGui.QApplication.UnicodeUTF8))
        self.toolBox.setItemText(self.toolBox.indexOf(self.advancedOptionsPage), QtGui.QApplication.translate("MainWindow", "Advanced Options", None, QtGui.QApplication.UnicodeUTF8))
        self.toolBox.setItemText(self.toolBox.indexOf(self.evasionOptionsPage), QtGui.QApplication.translate("MainWindow", "Evasion Options", None, QtGui.QApplication.UnicodeUTF8))
        self.exploitCommandLinkButton.setText(QtGui.QApplication.translate("MainWindow", "Exploit", None, QtGui.QApplication.UnicodeUTF8))


########NEW FILE########
__FILENAME__ = shell
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created: Mon Apr 23 10:02:10 2012
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(673, 603)
        self.centralWidget = QtGui.QWidget(MainWindow)
        self.centralWidget.setObjectName(_fromUtf8("centralWidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.outputTextBrowser = QtGui.QTextBrowser(self.centralWidget)
        self.outputTextBrowser.setObjectName(_fromUtf8("textBrowser"))
        self.outputTextBrowser.setStyleSheet('font: 12pt "Courier";')
        self.gridLayout.addWidget(self.outputTextBrowser, 0, 0, 1, 1)
        self.commanderLineEdit = QtGui.QLineEdit(self.centralWidget)
        self.commanderLineEdit.setObjectName(_fromUtf8("lineEdit"))
        self.gridLayout.addWidget(self.commanderLineEdit, 2, 0, 1, 1)
        self.label = QtGui.QLabel(self.centralWidget)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralWidget)
        self.menuBar = QtGui.QMenuBar(MainWindow)
        self.menuBar.setGeometry(QtCore.QRect(0, 0, 673, 22))
        self.menuBar.setObjectName(_fromUtf8("menuBar"))
        MainWindow.setMenuBar(self.menuBar)
        self.mainToolBar = QtGui.QToolBar(MainWindow)
        self.mainToolBar.setObjectName(_fromUtf8("mainToolBar"))
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.mainToolBar)
        self.statusBar = QtGui.QStatusBar(MainWindow)
        self.statusBar.setObjectName(_fromUtf8("statusBar"))
        MainWindow.setStatusBar(self.statusBar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "MainWindow", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("MainWindow", "Command:", None, QtGui.QApplication.UnicodeUTF8))


########NEW FILE########
__FILENAME__ = resource
#!/usr/bin/env python

from pkg_resources import resource_filename
from os import path


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

images = 'sploitego.resources.images'
etc = 'sploitego.resources.etc'

def imageicon(cat, name):
    return 'file://%s' % resource_filename('.'.join([ images, cat ]), name)

def imagepath(cat, name):
    return '%s' % resource_filename('.'.join([ images, cat ]), name)

# operating systems

systems = dict(
    apple = imageicon('os', 'apple.gif'),
    archlinux = imageicon('os', 'archlinux.png'),
    debian = imageicon('os', 'debian.png'),
    freebsd = imageicon('os', 'freebsd.png'),
    gentoo = imageicon('os', 'gentoo.png'),
    linux = imageicon('os', 'linux.png'),
    ubuntu = imageicon('os', 'ubuntu.png'),
    windows = imageicon('os', 'windows.png'),
    cisco = imageicon('os', 'cisco.gif'),
    hp = imageicon('os', 'hp.png'),
)

# networking
unavailableport = imageicon('networking', 'unavailableport.gif')
openport = imageicon('networking', 'openport.gif')
timedoutport = imageicon('networking', 'timedoutport.gif')
closedport = imageicon('networking', 'closedport.gif')

# severity
critical = imageicon('severity', 'critical.gif')
high = imageicon('severity', 'high.gif')
medium = imageicon('severity', 'medium.gif')
low = imageicon('severity', 'low.gif')
info = imageicon('severity', 'info.gif')

# logos
nmap = imagepath('logos', 'nmap.gif')
metasploit = imagepath('logos', 'metasploit.png')
nessus = imagepath('logos', 'nessus.png')

# etc
conf = resource_filename(etc, 'sploitego.conf')

# flags
def flag(c):
    f = imageicon('flags', '%s.png' % c.lower())
    if path.exists(f[7:]):
        return f
    return None
########NEW FILE########
__FILENAME__ = dns
#!/usr/bin/env python

from struct import unpack, pack
import socket

from scapy.all import (   IP, ICMP, TCP, DNS, UDP, DNSQR, DNSgetstr, DNSRRField, DNSStrField, DNSRR,
                       ShortEnumField, IntField, ShortField, StrField, dnstypes, dnsclasses, RDataField, RDLenField,
                       RandShort)
from iptools.ip import resolvers


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ =[
    'nslookup',
    'inquery',
    'ixfr',
    'axfr'
]


def __decodeRR(self, name, s, p):
    ret = s[p:p+10]
    type,cls,ttl,rdlen = unpack("!HHIH", ret)
    p += 10

    rr = None
    if type == 15:
        rr = DNSMXRR("\x00"+ret+s[p:p+rdlen])
        rr.rdata = DNSgetstr(s, p+2)[0]
        rr.rdlen = rdlen
    elif type == 6:
        rr = DNSSOARR("\x00"+ret+s[p:p+rdlen])
        rr.mname, q = DNSgetstr(s, p)
        rr.rname, q = DNSgetstr(s, q)
        rr.serial,rr.refresh,rr.retry,rr.expire,rr.minimum = unpack('!IIIII', s[q:q+20])
        rr.rdlen = rdlen
    else:
        rr = DNSRR("\x00"+ret+s[p:p+rdlen])
        if 2 <= rr.type <= 5:
            rr.rdata = DNSgetstr(s, p)[0]
        del rr.rdlen

    p += rdlen

    rr.rrname = name
    return rr,p

DNSRRField.decodeRR = __decodeRR


class DNSMXRR(DNSRR):
    name = "DNS MX Resource Record"
    show_indent=0
    fields_desc = [ DNSStrField("rrname",""),
                    ShortEnumField("type", 1, dnstypes),
                    ShortEnumField("rclass", 1, dnsclasses),
                    IntField("ttl", 0),
                    RDLenField("rdlen"),
                    ShortField("mxpriority", 0),
                    RDataField("rdata", "", length_from=lambda pkt: pkt.rdlen - 2) ]


class DNSSOARR(DNSRR):
    name = "DNS SOA Resource Record"
    show_indent=0
    fields_desc = [ DNSStrField("rrname",""),
                    ShortEnumField("type", 1, dnstypes),
                    ShortEnumField("rclass", 1, dnsclasses),
                    IntField("ttl", 0),
                    ShortField("rdlen", 0),
                    StrField("mname", ""),
                    StrField("rname", ""),
                    IntField("serial", 0),
                    IntField("refresh", 0),
                    IntField("retry", 0),
                    IntField("expire", 0),
                    IntField("minimum", 0)]


def nslookup(qname, qtype='A', nameserver=resolvers(), rd=1, timeout=2, retry=2):

    if qtype in [ 'AXFR', 'IXFR' ]:
        ans = inquery(qname, 'SOA', nameserver, timeout=timeout, retry=retry)
        if ans is not None and ans.ancount:
            authns = [ a.mname for a in ans.an ]
            if qtype == 'AXFR':
                ans = axfr(qname, authns, timeout=timeout, retry=retry)
            else:
                ans = ixfr(qname, authns, timeout=timeout, retry=retry)
    else:
        ans = inquery(qname, qtype, nameserver, rd, timeout=timeout, retry=retry)

    return ans


def inquery(qname, qtype, nameserver, rd=1, timeout=2, retry=2):

    if not isinstance(nameserver, list):
        nameserver = [ nameserver ]

    s = socket.socket(type=socket.SOCK_DGRAM)
    s.settimeout(timeout)

    dnsq = DNS(id=RandShort(), rd=rd, qd=DNSQR(qname=qname, qtype=qtype))
    sendit = True
    id = 0

    for ns in nameserver:
        for r in range(0, retry+1):
            try:
                if sendit:
                    p = str(dnsq)
                    id = unpack('!H', p[0:2])[0]
                    s.sendto(p, 0, (ns, 53))
                dnsr = DNS(s.recvfrom(4096)[0])
                if id != dnsr.id:
                    sendit = False
                    continue
                return dnsr
            except socket.timeout:
                sendit = True
                continue
            except socket.error:
                sendit = True
                continue

    return None


def ixfr(qname, authnameserver, serial=0, refresh=0, retry_int=0, expiry=0, ttl=0, timeout=2, retry=2):
    soa = '\xc0\x0c\x00\x06\x00\x01\x00\x00\x00\x00\x00\x16\x00\x00'
    soa += pack('!IIIII', serial, refresh, retry_int, expiry, ttl)

    dnsq = DNS(id=RandShort(), rd=0, ra=0, nscount=1, qd=DNSQR(qname=qname, qtype='IXFR'))/soa
    return _dnsxfr(authnameserver, dnsq, timeout, retry)


def axfr(qname, authnameserver, timeout=2, retry=2):

    dnsq = DNS(id=RandShort(), rd=0, ra=0, qd=DNSQR(qname=qname, qtype='AXFR'))
    return _dnsxfr(authnameserver, dnsq, timeout, retry)


def _dnsxfr(authnameserver, packet, timeout=2, retry=2):

    if not isinstance(authnameserver, list):
        authnameserver = [ authnameserver ]

    for ns in authnameserver:
        for r in range(0, retry+1):
            s = socket.socket()
            s.settimeout(timeout)
            d = ''
            try:
                s.connect((ns, 53))
                s.sendall('%s%s' % (pack('!H', len(packet)), str(packet)))
                while True:
                    dr = s.recv(8192)
                    d += dr
            except socket.timeout:
                s.close()
                if d:
                    return _parsexfr(d)
                continue
            except socket.error:
                s.close()
                continue

    return []


def _parsexfr(xfr):
    i = 0
    ans = []
    while i < len(xfr):
        sz = unpack('!H', xfr[i:i+2])[0]
        i += 2
        ans.append(DNS(xfr[i:i+sz]))
        i += sz

    if len(ans) == 1:
        return ans[0]

    return ans
########NEW FILE########
__FILENAME__ = route
#!/usr/bin/env python

from scapy.all import sr, sr1, conf, IP
from iptools.ip import IPNetwork, IPAddress


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'route',
    'traceroute',
    'traceroute2'
]


def route(ip):

    routes = [ {
        'network' : IPNetwork([r[0], r[1]]),
        'nexthop' : IPAddress(r[2]),
        'iface' : r[3],
        'iface_ip' : IPAddress(r[4])
    } for r in conf.route.routes ]

    routes.sort(key=lambda r: r['network'])

    for r in routes:
        if r['network'].cidrlen != 32 and ip in r['network']:
            return r


def traceroute(dst, probe, ttl=(0, 255), timeout=2, retry=2, verbose=0):
    return sr(IP(dst=dst, ttl=ttl)/probe, timeout=timeout, retry=retry, verbose=verbose)[0]


def traceroute2(dst, probe, timeout=2, retry=2, verbose=0):
    hops = []
    for i in range(1, 256):
        r = sr1(IP(dst=dst, ttl=i)/probe, timeout=timeout, retry=retry, verbose=verbose)
        if r is not None:
            hops.append({ 'ttl' : i, 'ip' : r.src })
        else:
            continue
        if r.src == dst:
            break
    return hops
########NEW FILE########
__FILENAME__ = snmp
#!/usr/bin/env python

from socket import socket, SOCK_DGRAM, AF_INET, timeout
from random import randint
from time import sleep

from scapy.all import (SNMP, SNMPnext, SNMPvarbind, ASN1_OID, SNMPget, ASN1_DECODING_ERROR, ASN1_NULL, ASN1_IPADDRESS,
                       SNMPset, SNMPbulk)
from iptools.ip import IPAddress


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


class SNMPError(Exception):
    pass


class SNMPVersion:
    v1 = 0
    v2c = 1
    v3 = 2

    @classmethod
    def iversion(cls, v):
        if v in ['v1', '1']:
            return cls.v1
        elif v in ['v2', '2', 'v2c']:
            return cls.v2c
        elif v in ['v3', '3']:
            return cls.v3
        raise ValueError('No such version %s' % v)

    @classmethod
    def sversion(cls, v):
        if not v:
            return 'v1'
        elif v == 1:
            return 'v2c'
        elif v == 2:
            return 'v3'
        raise ValueError('No such version number %s' % v)


class SNMPManager(object):

    def __init__(self, agent, port=161, community='public', version='v2c', timeout=2, retry=3):
        self.version = SNMPVersion.iversion(version)
        self.s = socket(AF_INET, SOCK_DGRAM)
        self.s.settimeout(timeout)
        self.addr = (agent, port)
        self.community = community
        self.retry = retry + 1
        self._check()

    def _check(self):
        return self.description

    @property
    def description(self):
        return self.get('1.3.6.1.2.1.1.1.0')['value']

    @property
    def contact(self):
        return self.get('1.3.6.1.2.1.1.4.0')['value']

    @property
    def hostname(self):
        return self.get('1.3.6.1.2.1.1.5.0')['value']

    @property
    def location(self):
        return self.get('1.3.6.1.2.1.1.6.0')['value']

    def _sr(self, p):
        retry = 0
        while retry < self.retry:
            i = randint(0, 2147483647)
            p.PDU.id = i
            self.s.sendto(str(p), self.addr)
            r = None
            try:
                while True:
                    r = SNMP(self.s.recvfrom(65535)[0])
                    if r.PDU.id.val == i:
                        break
            except timeout:
                retry += 1
                continue
            error = r.PDU.error.val
            if not error:
                return r
            elif error == 1:
                raise SNMPError('Response message too large to transport.')
            elif error == 2:
                raise SNMPError('The name of the requested object was not found.')
            elif error == 3:
                raise SNMPError('A data type in the request did not match the data type in the SNMP agent.')
            elif error == 4:
                raise SNMPError('The SNMP manager attempted to set a read-only parameter')
            raise SNMPError('An unknown error has occurred')
        raise SNMPError('Unable to connect to host %s.' % repr(self.addr))

    def getnext(self, oid):
        p = SNMP(
            community=self.community,
            version=self.version,
            PDU=SNMPnext(varbindlist=[SNMPvarbind(oid=ASN1_OID(oid))])
        )
        r = self._sr(p).PDU.varbindlist[0]
        return {'oid':r.oid.val, 'type':type(r.value), 'value':r.value.val}

    def walk(self, oid):
        tree = []
        current = self.getnext(oid)
        while current['oid'].startswith(oid) and current['type'] not in [ASN1_NULL, ASN1_DECODING_ERROR]:
            tree.append(current)
            current = self.getnext(current['oid'])
        return tree

    def bulk(self, oid, num=10):
        tree = []
        p = SNMP(
            community=self.community,
            version=self.version,
            PDU=SNMPbulk(max_repetitions=num, varbindlist=[SNMPvarbind(oid=ASN1_OID(oid))])
        )
        r = self._sr(p).PDU.varbindlist
        for v in r:
            tree.append({'oid':v.oid.val, 'type':type(v.value), 'value':v.value.val})
        return tree


    def get(self, oid):
        p = SNMP(
            community=self.community,
            version=self.version,
            PDU=SNMPget(varbindlist=[SNMPvarbind(oid=ASN1_OID(oid))])
        )
        r = self._sr(p).PDU.varbindlist[0]
        return { 'oid' : r.oid.val, 'type' : type(r.value), 'value' : r.value.val }

    def set(self, oid, value):
        p = SNMP(
            community=self.community,
            version=self.version,
            PDU=SNMPset(varbindlist=[SNMPvarbind(oid=ASN1_OID(oid), value=value)])
        )
        self._sr(p)

    def setint(self, oid, value):
        if not isinstance(value, int):
            raise TypeError('Expected int got %s instead.' % type(value).__name__)
        self.set(oid, value)

    def setstr(self, oid, value):
        if not isinstance(value, basestring):
            value = str(value)
        self.set(oid, value)

    def setip(self, oid, value):
        if not isinstance(value, IPAddress) and not isinstance(value, ASN1_IPADDRESS):
            value = ASN1_IPADDRESS(str(IPAddress(value)))
        self.set(oid, value)

    def __del__(self):
        self.s.close()


class SNMPBruteForcer(object):

    def __init__(self, agent, port=161, version='v2c', timeout=0.5, rate=1000):
        self.version = SNMPVersion.iversion(version)
        self.s = socket(AF_INET, SOCK_DGRAM)
        self.s.settimeout(timeout)
        self.addr = (agent, port)
        self.rate = rate

    def guess(self, communities):
        if 'public' not in communities:
            communities.append('public')
        if 'private' not in communities:
            communities.append('private')
        p = SNMP(
            version=self.version,
            PDU=SNMPget(varbindlist=[SNMPvarbind(oid=ASN1_OID('1.3.6.1.2.1.1.1.0'))])
        )
        r = set()
        for c in communities:
            i = randint(0, 2147483647)
            p.PDU.id = i
            p.community = c
            self.s.sendto(str(p), self.addr)
            sleep(1/self.rate)
        while True:
            try:
                p = SNMP(self.s.recvfrom(65535)[0])
            except timeout:
                break
            r.add(p.community.val)
        return r

    def __del__(self):
        self.s.close()
########NEW FILE########
__FILENAME__ = amap
#!/usr/bin/env python

from sploitego.cmdtools.amap import AmapScanner, AmapReportParser
from canari.maltego.entities import BuiltWithTechnology
from sploitego.cmdtools.nmap import NmapReportParser
from canari.maltego.message import Label
from canari.framework import configure
from common.entities import NmapReport

from tempfile import NamedTemporaryFile


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Banners [Amap]',
    description='This transform uses Amap to fingerprint services identified from an Nmap Report.',
    uuids=[ 'sploitego.v2.NmapReportToBanner_Amap' ],
    inputs=[ ( 'Reconnaissance', NmapReport ) ]
)
def dotransform(request, response):
    s = AmapScanner()
    f = NamedTemporaryFile(suffix='.gnmap', mode='wb')
    f.write(NmapReportParser(file(request.entity.file).read()).greppable)
    f.flush()
    r = s.scan(['-bqi', f.name], AmapReportParser)
    f.close()
    for b in r.banners:
        e = BuiltWithTechnology(b[1])
        e += Label('Destination', b[0])
        e += Label('Extra Information', b[2])
        response += e
    return response
########NEW FILE########
__FILENAME__ = bcsitereview
#!/usr/bin/env python

from canari.maltego.entities import Website
from canari.framework import configure

from common.entities import SiteCategory


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Site Category [Blue Coat]',
    description='Gets the site category for a given Website.',
    uuids=['sploitego.v2.WebsiteToSiteCategory_BlueCoat'],
    inputs=[('Reconnaissance', Website)],
    remote=True
)
def dotransform(request, response, config):
    from sploitego.webtools.bluecoat import sitereview
    for c in sitereview(request.value, config):
        response += SiteCategory(c)
    return response
########NEW FILE########
__FILENAME__ = bingsubdomains
#!/usr/bin/env python

from httplib import urlsplit
from re import findall

from canari.maltego.configuration import BuiltInTransformSets
from canari.maltego.entities import DNSName, Domain
from sploitego.webtools.bing import searchweb
from canari.framework import configure
from canari.config import config


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To DNS Names [Bing]',
    description='This transform attempts to find subdomains using the Microsoft Bing search engine.',
    uuids=['sploitego.v2.DomainToDNSName_Bing'],
    inputs=[(BuiltInTransformSets.DNSFromDomain, Domain)]
)
def dotransform(request, response):
    domain = request.value
    exclude = set()
    for i in range(0, config['bingsubdomains/maxrecursion']):
        q = ' '.join(['site:%s' % domain] + map(lambda x: '-site:%s' % x, exclude))
        results = searchweb(q)
        for r in results:
            domains = [urlsplit(d).netloc for d in findall('<web:Url>(.+?)</web:Url>', r)]
            for d in domains:
                if d not in exclude and d != domain:
                    exclude.add(d)
                    response += DNSName(d)
    return response
########NEW FILE########
__FILENAME__ = dnstools
#!/usr/bin/env python
import collections

import socket

import dns.query
import dns.resolver
import dns.reversename
import dns.rdatatype

from canari.maltego.entities import DNSName, MXRecord, NSRecord, IPv4Address, Phrase
from canari.maltego.message import UIMessage, Field

from entities import IPv6Address


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'nslookup'
]


def xfr(ns, domain, response, type_='AXFR', fallback_to_ixfr=True, discovered_names=None):
    if discovered_names is None:
        discovered_names = []
    try:
        for msg in dns.query.xfr(ns, domain, type_):
            for ans in msg.answer:
                name = ans.name.to_text(True)
                if ans.rdtype in [1, 5] and name not in discovered_names:
                    discovered_names.append(name)
                    response += DNSName(domain if name == '@' else '.'.join([name, domain]))
    except dns.resolver.NXDOMAIN:
        response += UIMessage("DNS records for %s do not exist on %s." % (repr(domain), repr(ns)))
    except dns.resolver.Timeout:
        response += UIMessage("DNS request for %s timed out on %s." % (repr(domain), repr(ns)))
    except dns.exception.FormError:
        if type_ != 'IXFR' and fallback_to_ixfr:
            xfr(ns, domain, response, 'IXFR', discovered_names=discovered_names)
        else:
            response += UIMessage("Could not transfer DNS zone for %s from %s." % (repr(domain), repr(ns)))
    return discovered_names


def nslookup(name, type_, response, resolvers=None, recursive=True):
    name = name.rstrip('.')
    if isinstance(type_, basestring):
        type_ = dns.rdatatype.from_text(type_)
    if type_ == dns.rdatatype.PTR:
        name = dns.reversename.from_address(name)
    if not resolvers:
        resolvers = dns.resolver.get_default_resolver().nameservers
    elif isinstance(resolvers, basestring):
        resolvers = [resolvers]

    if type_ in [dns.rdatatype.AXFR, dns.rdatatype.IXFR]:
        try:
            discovered_names = []
            for ns in dns.resolver.query(name, dns.rdatatype.NS):
                xfr(ns.to_text(), name, response, discovered_names=discovered_names)
            return True
        except dns.resolver.NXDOMAIN:
            response += UIMessage("DNS records for %s do not exist." % repr(name))
        except dns.resolver.NoNameservers:
            response += UIMessage("No nameservers found for %s." % repr(name))
        except dns.resolver.Timeout:
            response += UIMessage("DNS request for %s timed out." % repr(name))
        except dns.resolver.NoAnswer:
            response += UIMessage("DNS request for %s resulted in no response." % repr(name))
        except socket.error:
            response += UIMessage("A socket error has occurred. Make sure you are connected or the traffic is allowed.")
        return False

    try:
        request = dns.message.make_query(name, type_, dns.rdataclass.IN)
        if not recursive:
            request.flags ^= dns.flags.RD
        for resolver in resolvers:
            ans = dns.query.udp(request, resolver).answer
            if ans:
                for rrset in ans:
                    for rr in rrset:
                        if rr.rdtype == type_:
                            if type_ == dns.rdatatype.A:
                                response += IPv4Address(rr.to_text(True))
                            elif type_ == dns.rdatatype.NS:
                                response += UIMessage(repr(rr))
                                response += NSRecord(rr.to_text()[:-1])
                            elif type_ == dns.rdatatype.CNAME:
                                response += DNSName(rr.to_text())
                            elif type_ == dns.rdatatype.SOA:
                                e = NSRecord(rr.mname.to_text(True))
                                e += Field('mailaddr', rr.rname.to_text(True), displayname='Authority')
                                response += e
                            elif type_ == dns.rdatatype.PTR:
                                response += DNSName(rr.to_text()[:-1])
                            elif type_ == dns.rdatatype.MX:
                                e = MXRecord(rr.exchange.to_text(True))
                                e.mxpriority = rr.preference
                                response += e
                            elif type_ == dns.rdatatype.TXT:
                                response += Phrase(rr.to_text(True))
                            elif type_ == dns.rdatatype.AAAA:
                                response += IPv6Address(rr.to_text(True))
                            else:
                                response += Phrase(rr.to_text(True))
                return True
    except dns.resolver.NXDOMAIN:
        response += UIMessage("DNS records for %s do not exist." % repr(name))
    except dns.resolver.Timeout:
        response += UIMessage("DNS request for %s timed out." % repr(name))
    except dns.resolver.NoNameservers:
        response += UIMessage("No name servers found for %s." % repr(name))
    except dns.resolver.NoAnswer:
        response += UIMessage("The DNS server returned with no response for %s." % repr(name))
    except socket.error:
        response += UIMessage("A socket error has occurred. Make sure you are connected or the traffic is allowed.")
    return False


def nslookup_raw(name, type_=dns.rdatatype.A, resolver=None, recursive=True, tcp=False, timeout=10):
    if not resolver:
        try:
            resolver = dns.resolver.get_default_resolver().nameservers[0]
        except IndexError:
            raise OSError("A DNS resolver could not be found.")
    m = dns.message.make_query(name, type_, dns.rdataclass.IN)
    if not recursive:
        m.flags ^= dns.flags.RD
    if tcp:
        return dns.query.tcp(m, resolver, timeout=timeout)
    return dns.query.udp(m, resolver, timeout=timeout)
########NEW FILE########
__FILENAME__ = entities
#!/usr/bin/env python

from canari.maltego.message import Entity, EntityField, EntityFieldType, MatchingRule
from sploitego.resource import (unavailableport, closedport, timedoutport, openport, high, medium, low, info, critical,
                                systems)


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'SploitegoEntity',
    'PortStatus',
    'Port',
    'NmapReport',
    'Service',
    'OS',
    'SiteCategory'
]


class SploitegoEntity(Entity):

    _namespace_ = 'sploitego'


class PortStatus(object):
    Open = 'Open'
    Closed = 'Closed'
    Unavailable = 'Service Unavailable'
    TimedOut = 'TimedOut'
    Filtered = 'Filtered'

    @staticmethod
    def icon(obj, val):
        values = val.split('|')
        if PortStatus.Open in values:
            obj.iconurl = openport
        elif PortStatus.Closed in values:
            obj.iconurl = closedport
        elif PortStatus.Unavailable in values:
            obj.iconurl = unavailableport
        elif PortStatus.TimedOut in values or PortStatus.Filtered in values:
            obj.iconurl = timedoutport


class VulnerabilitySeverity(object):
    Critical = 4
    High = 3
    Medium = 2
    Low = 1
    Info = 0

    @staticmethod
    def icon(obj, val):
        val = int(val)
        if val == VulnerabilitySeverity.Critical:
            obj.iconurl = critical
        elif val == VulnerabilitySeverity.High:
            obj.iconurl = high
        elif val == VulnerabilitySeverity.Medium:
            obj.iconurl = medium
        elif val == VulnerabilitySeverity.Low:
            obj.iconurl = low
        else:
            obj.iconurl = info


class OsName(object):

    @staticmethod
    def icon(obj, val):
        for s in systems:
            if s in val.lower():
                obj.iconurl = systems[s]
                return


class IPv6Address(SploitegoEntity):
    pass


@EntityField(name='ip.source', propname='source', displayname='Source IP')
@EntityField(name='ip.destination', propname='destination', displayname='Destination IP')
@EntityField(name='protocol')
@EntityField(name='port.response', propname='response', displayname='Port Response')
@EntityField(name='port.status', propname='status', displayname='Port Status', decorator=PortStatus.icon)
class Port(SploitegoEntity):
    pass


@EntityField(name='report.file', propname='file', displayname='Report File')
@EntityField(name='scan.command', propname='command', displayname='Command')
class NmapReport(SploitegoEntity):
    pass


@EntityField(name='ip.destination', propname='destination', displayname='Destination IP')
@EntityField(name='protocol')
@EntityField(name='port', matchingrule=MatchingRule.Loose)
class Service(SploitegoEntity):
    pass


@EntityField(name='os.name', propname='name', displayname='Operating System', decorator=OsName.icon)
class OS(SploitegoEntity):
    pass


class SiteCategory(SploitegoEntity):
    pass


@EntityField(name='snmp.community', propname='community', displayname='SNMP Community')
@EntityField(name='snmp.version', propname='version', displayname='SNMP Version',
    type=EntityFieldType.Enum, choices=['1', '2c', '2', '3', 'v1', 'v2c', 'v3'])
@EntityField(name='snmp.agent', propname='agent', displayname='SNMP Agent')
@EntityField(name='ip.port', propname='port', displayname='Port', type=EntityFieldType.Integer)
@EntityField(name='protocol')
class SNMPCommunity(SploitegoEntity):
    pass


@EntityField(name='nessusreport.uuid', propname='uuid', displayname='Report UUID')
@EntityField(name='nessus.server', propname='server', displayname='Nessus Server')
@EntityField(name='nessus.port', propname='port', displayname='Nessus Port')
#@EntityField(name='nessusreport.errors', propname='errors', displayname='Errors')
class NessusReport(SploitegoEntity):
    pass


@EntityField(name='nessusplugin.id', propname='pluginid', displayname='Plugin ID')
@EntityField(name='nessusplugin.family', propname='family', displayname='Plugin Family')
@EntityField(name='nessusplugin.severity', propname='severity',
    displayname='Severity', decorator=VulnerabilitySeverity.icon)
@EntityField(name='nessusplugin.count', propname='count', displayname='Count')
@EntityField(name='nessusreport.uuid', propname='uuid', displayname='Report UUID')
@EntityField(name='nessus.server', propname='server', displayname='Nessus Server')
@EntityField(name='nessus.port', propname='port', displayname='Nessus Port')
class NessusVulnerability(SploitegoEntity):
    pass


@EntityField(name='msfrpcd.server', propname='server', displayname='Metasploit Server')
@EntityField(name='msfrpcd.port', propname='port', displayname='Metasploit Port')
@EntityField(name='msfrpcd.uri', propname='uri', displayname='Metasploit URI')
@EntityField(name='session.uuid', propname='sessionid', displayname='Metasploit Session ID')
class MetasploitSession(SploitegoEntity):
    pass

########NEW FILE########
__FILENAME__ = msfrpcd
#!/usr/bin/env python

import socket
from urlparse import parse_qsl
from urllib import urlencode
from os import path, unlink

from canari.easygui import multpasswordbox
from canari.utils.fs import cookie, fsemaphore
from canari.config import config

from metasploit.msfrpc import MsfRpcClient, MsfRpcError


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'login'
]


def login(**kwargs):
    s = None
    host = kwargs.get('host', config['msfrpcd/server'])
    port = kwargs.get('port', config['msfrpcd/port'])
    uri = kwargs.get('uri', config['msfrpcd/uri'])
    fn = cookie('%s.%s.%s.msfrpcd' % (host, port, uri.replace('/', '.')))
    if not path.exists(fn):
        f = fsemaphore(fn, 'wb')
        f.lockex()
        fv = [ host, port, uri, 'msf' ]
        errmsg = ''
        while True:
            fv = multpasswordbox(errmsg, 'Metasploit Login', ['Server:', 'Port:', 'URI', 'Username:', 'Password:'], fv)
            if not fv:
                return
            try:
                s = MsfRpcClient(fv[4], server=fv[0], port=fv[1], uri=fv[2], username=fv[3])
            except MsfRpcError, e:
                errmsg = str(e)
                continue
            except socket.error, e:
                errmsg = str(e)
                continue
            break
        f.write(urlencode({'host' : fv[0], 'port' : fv[1], 'uri': fv[2], 'token': s.sessionid}))
        f.unlock()

        if 'db' not in s.db.status:
            s.db.connect(
                config['metasploit/dbusername'],
                database=config['metasploit/dbname'],
                driver=config['metasploit/dbdriver'],
                host=config['metasploit/dbhost'],
                port=config['metasploit/dbport'],
                password=config['metasploit/dbpassword']
            )
    else:
        f = fsemaphore(fn)
        f.locksh()
        try:
            d = dict(parse_qsl(f.read()))
            s = MsfRpcClient('', **d)
        except MsfRpcError:
            unlink(fn)
            return login()
        except socket.error:
            unlink(fn)
            return login()
    return s
########NEW FILE########
__FILENAME__ = nmap
#!/usr/bin/env python

from ConfigParser import NoOptionError
from sploitego.cmdtools.nmap import NmapScanner

from entities import Port, NmapReport, OS
from canari.maltego.message import Label
from canari.utils.fs import ufile
from canari.config import config

import os
from time import strftime


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


def getscanner():
    binargs = None
    try:
        binargs = config['nmap/nmapcmd'].split(' ')
    except NoOptionError:
        pass
    return NmapScanner() if binargs is None else NmapScanner(binargs)


def addports(report, response):

    for addr in report.addresses:
        for port in report.ports(addr):
            e = Port(port['portid'])
            e.protocol = port['protocol'].upper()
            e.status = port['state'].title()
            e.destination = addr
            e.response = port['reason']
            e += Label('Service Name', port.get('name', 'unknown'))
            if 'servicefp' in port:
                e += Label('Service Fingerprint', port['servicefp'])
            if 'extrainfo' in port:
                e += Label('Extra Information', port['extrainfo'])
            if 'method' in port:
                e += Label('Method', port['method'])
            response += e


def savereport(report):
    if not os.path.lexists(config['nmap/reportdir']):
        os.makedirs(config['nmap/reportdir'])
    with ufile(strftime(os.path.join(config['nmap/reportdir'], config['nmap/namefmt']))) as f:
        f.write(report.output)
        return f.name


def addreport(report, response, tag, cmd):
    e = NmapReport('Nmap %s Report: %s' % (tag, report.nmaprun['startstr']))
    e.file = savereport(report)
    e.command = cmd
    response += e


def addsystems(report, response):
    for addr in report.addresses:
        for osm in report.os(addr)['osmatch']:
            e = OS(osm['name'])
            e.name = osm['name']
            e += Label('Accuracy', osm['accuracy'])
            response += e
########NEW FILE########
__FILENAME__ = reversegeo
#!/usr/bin/env python

from sploitego.webtools.geolocate import reversegeo
from sploitego.webtools.geolocate import geomac
from canari.maltego.entities import Location

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


def getlocbymac(mac):
    ll = geomac(mac)
    gcr = reversegeo(ll['latitude'], ll['longitude'])[0]
    l = Location('-, -')
    l.city = '-'
    l.country = '-'
    for i in gcr['address_components']:
        if 'locality' in i['types']:
            l.city = i['long_name']
        if 'administrative_area_level_1' in i['types']:
            l.area = i['long_name']
        if 'country' in i['types']:
            l.country = i['long_name']
    l.latitude = gcr['geometry']['location']['lat']
    l.longitude = gcr['geometry']['location']['lng']
    l.value = '%s, %s' % (l.city, l.country)
    return l
########NEW FILE########
__FILENAME__ = snmp
#!/usr/bin/env python

from canari.maltego.message import MaltegoException
from iptools.ip import IPAddress
from canari.config import config


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


def snmpargs(request):
    protocol = (request.entity.protocol or 'UDP').upper()
    if protocol != 'UDP':
        raise MaltegoException('SNMP over UDP for versions 1 and 2c are only supported.')
    return (
        str(IPAddress(request.entity.agent)),
        int(request.entity.port),
        request.value,
        request.entity.version,
        config['scapy/sr_timeout'],
        config['scapy/sr_retries']
    )
########NEW FILE########
__FILENAME__ = tenable
# !/usr/bin/env python
import socket

from nessus import NessusXmlRpcClient, NessusSessionException, NessusException
from canari.easygui import multpasswordbox, choicebox
from canari.utils.fs import cookie, fsemaphore
from canari.config import config

from urlparse import parse_qsl
from urllib import urlencode

import os
import time


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'login',
    'policy',
    'scan'
]


def login(host='localhost', port='8834', username='', password=''):
    s = None
    fn = cookie('%s.%s.nessus' % (host, port))
    if not os.path.exists(fn):
        with fsemaphore(fn, 'wb') as f:
            f.lockex()
            errmsg = ''
            while True:
                fv = multpasswordbox(
                    errmsg,
                    'Nessus Login',
                    ['Server:', 'Port:', 'Username:', 'Password:'],
                    [host, port, username, password]
                )
                if not fv:
                    f.close()
                    os.unlink(fn)
                    return
                host, port, username, password = fv
                try:
                    s = NessusXmlRpcClient(username, password, host, port)
                except NessusException, e:
                    errmsg = str(e)
                    continue
                except socket.error, e:
                    errmsg = str(e)
                    continue
                break
            f.write(urlencode(dict(host=host, port=port, token=s.token)))
    else:
        with fsemaphore(fn) as f:
            f.locksh()
            try:
                d = dict(parse_qsl(f.read()))
                s = NessusXmlRpcClient(**d)
                policies = s.policies.list
            except NessusException:
                os.unlink(fn)
                return login()
            except NessusSessionException:
                os.unlink(fn)
                return login()
            except socket.error:
                os.unlink(fn)
                return login()
    return s


def policy(s):
    ps = s.policies.list
    c = choicebox('Select a Nessus scanning policy', 'Nessus Policies', ps)
    if c is None:
        return
    return filter(lambda x: str(x) == c, ps)[0]


def scan(s, t, p):
    return s.scanner.scan(time.strftime(config['nessus/namefmt']), t, p)

########NEW FILE########
__FILENAME__ = dnsaaaalookup
#!/usr/bin/env python

from canari.maltego.configuration import BuiltInTransformSets
from canari.maltego.entities import DNSName
from canari.framework import configure

from common.dnstools import nslookup

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To IPv6 Address [DNS]',
    description='This transform attempts to resolve a DNS record to an IPv6 Address.',
    uuids=[
        'sploitego.v2.DNSNameToIPv6Address_DNS'
    ],
    inputs=[
        ( BuiltInTransformSets.ResolveToIP, DNSName )
    ]
)
def dotransform(request, response):
    nslookup(request.value, 'AAAA', response)
    return response
########NEW FILE########
__FILENAME__ = dnsalookup
#!/usr/bin/env python

from canari.maltego.configuration import BuiltInTransformSets
from canari.maltego.entities import DNSName
from canari.framework import configure

from common.dnstools import nslookup

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To IPv4 Address [DNS]',
    description='This transform attempts to resolve a DNS record to an IPv4 Address.',
    uuids=[
        'sploitego.v2.DNSNameToIPv4Address_DNS'
    ],
    inputs=[
        ( BuiltInTransformSets.ResolveToIP, DNSName )
    ]
)
def dotransform(request, response):
    nslookup(request.value, 'A', response)
    return response
########NEW FILE########
__FILENAME__ = dnscachesnoop
# !/usr/bin/env python

from canari.maltego.entities import NSRecord, DNSName, IPv4Address
from canari.maltego.message import Label, UIMessage
from canari.framework import configure
from canari.maltego.utils import debug
from canari.maltego.html import Table
from canari.config import config

import dns.query
import dns.message
import dns.rdatatype
import dns.rdataclass

from common.dnstools import nslookup_raw

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To DNS Names [Cache Snoop]',
    description='This transform performs DNS cache snooping on the target DNS server for the Alexa top 500 list.',
    uuids=[
        'sploitego.v2.IPv4AddressToDNSName_CacheSnoop',
        'sploitego.v2.NSRecordToDNSName_CacheSnoop'
    ],
    inputs=[
        ('Reconnaissance', IPv4Address),
        ('Reconnaissance', NSRecord)
    ]
)
def dotransform(request, response):
    nameserver = request.value

    if nslookup_raw('www.google.ca', resolver=nameserver).answer:
        for site in config['dnscachesnoop/wordlist']:
            debug('Resolving %s' % site)

            msg = nslookup_raw(site, resolver=nameserver, recursive=False)
            if not msg.answer:
                msg = nslookup_raw('www.%s' % site, resolver=nameserver, recursive=False)
            if msg.answer:
                e = DNSName(site)
                t = Table(['Name', 'Query Class', 'Query Type', 'Data', 'TTL'], 'Cached Answers')
                for rrset in msg.answer:
                    for rr in rrset:
                        t.addrow([
                            rrset.name.to_text(),
                            dns.rdataclass.to_text(rr.rdclass),
                            dns.rdatatype.to_text(rr.rdtype),
                            rr.to_text(),
                            rrset.ttl
                        ])
                e += Label('Cached Answers from %s' % nameserver, t, type='text/html')
                response += e
    else:
        response += UIMessage('DNS server did not respond to initial DNS request.')
    return response
########NEW FILE########
__FILENAME__ = dnsmxlookup
#!/usr/bin/env python

from canari.maltego.configuration import BuiltInTransformSets
from canari.maltego.entities import Domain
from canari.framework import configure

from common.dnstools import nslookup


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To MX Records [DNS]',
    description='This transform will fetch the MX records for a given domain.',
    uuids=[ 'sploitego.v2.DomainToMXRecord_DNS' ],
    inputs=[ ( BuiltInTransformSets.DNSFromDomain, Domain ) ]
)
def dotransform(request, response):
    nslookup(request.value, 'MX', response)
    return response
########NEW FILE########
__FILENAME__ = dnsnslookup
#!/usr/bin/env python

from canari.maltego.configuration import BuiltInTransformSets
from canari.maltego.entities import Domain
from canari.framework import configure

from common.dnstools import nslookup


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To NS Records [DNS]',
    description='This transform attempts to resolve a DNS record to an IPv4 Address.',
    uuids=[ 'sploitego.v2.DomainToNSRecord_DNS' ],
    inputs=[ ( BuiltInTransformSets.DNSFromDomain, Domain ) ]
)
def dotransform(request, response):
    nslookup(request.value, 'NS', response)
    return response
########NEW FILE########
__FILENAME__ = dnsptrlookup
#!/usr/bin/env python

from canari.maltego.configuration import BuiltInTransformSets
from canari.maltego.entities import IPv4Address
from canari.framework import configure

from common.entities import IPv6Address
from common.dnstools import nslookup


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To DNS Name [DNS]',
    description='This transform will fetch the DNS records for a IP address.',
    uuids=[ 'sploitego.v2.IPv4AddressToDNSName_DNS', 'sploitego.v2.IPv6AddressToDNSName_DNS' ],
    inputs=[ ( BuiltInTransformSets.DNSFromIP, IPv4Address ), ( BuiltInTransformSets.DNSFromIP, IPv6Address ) ]
)
def dotransform(request, response):
    nslookup(request.value, 'PTR', response)
    return response
########NEW FILE########
__FILENAME__ = dnstodomain
#!/usr/bin/env python

from canari.maltego.configuration import BuiltInTransformSets
from canari.maltego.entities import DNSName, Domain
from canari.framework import configure


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Domain [DNS]',
    description='This transform gets the domain of the DNS name.',
    uuids=[
        'sploitego.v2.DNSNameToDomain_DNS',
#        'sploitego.v2.NSRecordToDomain_DNS',
#        'sploitego.v2.MXRecordToDomain_DNS'
    ],
    inputs=[
        ( BuiltInTransformSets.DomainFromDNS, DNSName ),
#        ( BuiltInTransformSets.DomainFromDNS, NSRecord ),
#        ( BuiltInTransformSets.DomainFromDNS, MXRecord )
    ]
)
def dotransform(request, response):
    dns = request.value
    if '.' in dns:
        response += Domain('.'.join(dns.split('.')[-2:]))
    else:
        response += Domain(request.value)
    return response
########NEW FILE########
__FILENAME__ = dnstxtlookup
#!/usr/bin/env python

from canari.maltego.configuration import BuiltInTransformSets
from canari.maltego.entities import DNSName
from canari.framework import configure

from common.dnstools import nslookup

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To TXT Record [DNS]',
    description='This transform attempts to resolve a DNS record to an TXT record.',
    uuids=[
        'sploitego.v2.DNSNameToTXT_DNS'
    ],
    inputs=[
        ( BuiltInTransformSets.ResolveToIP, DNSName )
    ]
)
def dotransform(request, response):
    nslookup(request.value, 'TXT', response)
    return response
########NEW FILE########
__FILENAME__ = dnsxfrlookup
#!/usr/bin/env python

from canari.maltego.configuration import BuiltInTransformSets
from canari.maltego.entities import Domain
from canari.framework import configure

from common.dnstools import nslookup

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]

@configure(
    label='To DNS Names [DNS AXFR/IXFR]',
    description='This transform attempts to perform a DNS AXFR/IXFR transfer.',
    uuids=[ 'sploitego.v2.DomainToDNSName_XFR' ],
    inputs=[ ( BuiltInTransformSets.DNSFromDomain, Domain ) ]
)
def dotransform(request, response):
    nslookup(request.value, 'AXFR', response)
    return response
########NEW FILE########
__FILENAME__ = findlocbymac
# !/usr/bin/env python

from canari.maltego.entities import IPv4Address
from canari.maltego.message import UIMessage
from common.reversegeo import getlocbymac
from canari.framework import configure


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform',
    'onterminate'
]


@configure(
    label='To Locations [Google Maps]',
    description='Gets device locations based on MAC address.',
    uuids=['sploitego.v2.IPv4AddressToLocation_GoogleMaps'],
    inputs=[('Reconnaissance', IPv4Address)]
)
def dotransform(request, response):
    if 'ethernet.hwaddr' not in request.fields or not request.fields['ethernet.hwaddr']:
        response += UIMessage('You must provide an Ethernet Hardware Address (ethernet.hwaddr) property.')
    else:
        response += getlocbymac(request.fields['ethernet.hwaddr'])
    return response
########NEW FILE########
__FILENAME__ = findneighbors
#!/usr/bin/env python

from xml.etree.cElementTree import fromstring

from scapy.all import arping, sr, sr1, TCP, IP, ICMP, sniff, ARP
from canari.maltego.message import Field, MaltegoException
from sploitego.scapytools.route import route, traceroute2
from canari.framework import configure, superuser
from canari.maltego.entities import IPv4Address
from iptools.ip import IPNetwork, IPAddress
from canari.maltego.utils import debug
from canari.config import config
from iptools.arin import whoisip


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@superuser
@configure(
    label='To Neighbors [Active Scan]',
    description='This transform attempts to identify hosts that are directly attached to the same router as the target',
    uuids=[ 'sploitego.v2.IPv4AddressToNeighbors_ActiveScan' ],
    inputs=[ ( "Reconnaissance", IPv4Address ) ],
)
def dotransform(request, response):
    r = route(request.value)
    if r is None:
        raise MaltegoException('Network is unavailable')
    elif not r['nexthop']:
        return findlocalneighbors(r['network'], response)
    return findremoteneighbors(IPAddress(request.value), response)


def findlocalneighbors(network, response):

    debug('ARP sweeping %s' % network.netblock)
#    e = Netblock(network.netblock)
#    e += Label('CIDR Notation', repr(network))
#    e += Label('Network Mask', network.netmask)
#    e += Label('Number of Hosts', int(~network.netmask) - 1)
#    response += e

    ans = arping(
        repr(network),
        timeout=config['scapy/sr_timeout'],
        verbose=config['scapy/sr_verbose']
    )[0]

    for i in ans:
        e = IPv4Address(i[1].psrc)
        e.internal = True
        e += Field('ethernet.hwaddr', i[1].hwsrc, displayname='Hardware Address')
        response += e

    if len(ans) <= 1:
        passivescan(network, response)

    return response


def passivescan(network, response):

    nodes = {}
    debug('Sniffing network traffic for more hosts.')
    ans = sniff(count=config['scapy/sniffcount'], timeout=config['scapy/snifftimeout'])
    debug('Analyzing traffic.')
    for i in ans:
        src = None
        dst = None
        if IP in i:
            src = i[IP].src
            dst = i[IP].dst
        elif ARP in i:
            src = i[ARP].psrc
            dst = i[ARP].pdst
        else:
            continue

        if src in network and src not in nodes:
            nodes[src] = True
            e = IPv4Address(src, internal=True)
            e += Field('ethernet.hwaddr', i.src, displayname='Hardware Address')
            response += e

        if dst in network and dst not in nodes and i.dst != 'ff:ff:ff:ff:ff:ff':
            nodes[dst] = True
            e = IPv4Address(dst, internal=True)
            e += Field('ethernet.hwaddr', i.dst, displayname='Hardware Address')
            response += e


def findremoteneighbors(ip, response):

    debug('Doing an ARIN whois lookup...')
    w = fromstring(whoisip(ip, accept='application/xml'))
    network = IPNetwork([
        w.find('{http://www.arin.net/whoisrws/core/v1}startAddress').text,
        w.find('{http://www.arin.net/whoisrws/core/v1}endAddress').text
    ])

#    e = Netblock(network.netblock)
#    e += Label('CIDR Notation', repr(network))
#    e += Label('Network Mask', network.netmask)
#    e += Label('Number of Hosts', int(~network.netmask) - 1)
#    response += e

    if network.cidrlen < 24:
        debug('According to ARIN, the CIDR length is %d, reducing it to 24 for the scan...' % network.cidrlen)
        network.netblock = '%s/24' % ip

    debug('Probing the host on TCP ports 0-1024...')
    r = sr1(
        IP(dst=str(ip))/TCP(dport=(0,1024)),
        timeout=config['scapy/sr_timeout'],
        verbose=config['scapy/sr_verbose'],
        retry=config['scapy/sr_retries']
    )

    if r is not None and r.src == ip:
        dport = r.sport

        debug('Performing a traceroute to destination %s' % ip)
        ans = traceroute2(
            str(ip),
            TCP(dport=dport),
            timeout=config['scapy/sr_timeout'],
            verbose=config['scapy/sr_verbose'],
            retry=config['scapy/sr_retries']
        )

        l_hop = ans[-1]
        sl_hop = ans[-2]

        if sl_hop['ttl'] != l_hop['ttl'] - 1:
            debug(
                "It takes %d hops to get to %s but we could only find the router at hop %d (%s)." %
                (l_hop['ttl'], ip, sl_hop['ttl'], sl_hop['ip'])
            )
            debug("Can't find second last hop... aborting...")
        else:
            debug('It takes %d hops to get to %s and it is attached to router %s...' % (l_hop['ttl'], ip, sl_hop['ip']))
            debug('Sending probe packets to %s with ttl %d...' % (network, sl_hop['ttl']))

            ans = sr(
                IP(dst=repr(network), ttl=sl_hop['ttl'])/TCP(dport=dport),
                timeout=config['scapy/sr_timeout'],
                verbose=config['scapy/sr_verbose'],
                retry=config['scapy/sr_retries']
            )[0]

            for r in ans:
                if r[1].src == sl_hop['ip']:
                    debug('%s is attached to the same router...' % r[0].dst)

                    e = IPv4Address(r[0].dst)

                    alive = sr1(
                        IP(dst=r[0].dst)/TCP(dport=dport),
                        timeout=config['scapy/sr_timeout'],
                        verbose=config['scapy/sr_verbose'],
                        retry=config['scapy/sr_retries']
                    )

                    if alive is not None:
                       e += Field('alive', 'true')
                    response += e

    return response
########NEW FILE########
__FILENAME__ = findnexthop
#!/usr/bin/env python

from canari.framework import superuser, configure
from canari.maltego.entities import IPv4Address
from canari.maltego.message import Field
from scapy.all import conf, getmacbyip


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform',
]


@superuser
@configure(
    label='To Next Hop [Routing Table]',
    description='This transform fetches the next hop or router for a given destination.',
    uuids=[ 'sploitego.v2.IPv4AddressToNextHop_RoutingTable' ],
    inputs=[ ( 'Reconnaissance', IPv4Address ) ],
)
def dotransform(request, response):
    nexthop = conf.route6.route(request.value)[2] if ':' in request.value else conf.route.route(request.value)[2]
    e = IPv4Address(nexthop)
    e.internal = True
    if ':' not in nexthop:
        e += Field('ethernet.hwaddr', getmacbyip(nexthop), displayname='Hardware Address')
    response += e
    return response
########NEW FILE########
__FILENAME__ = findresolvers
#!/usr/bin/env python

from canari.maltego.entities import Location, IPv4Address
from sploitego.scapytools.dns import resolvers
from canari.framework import configure

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


__all__ = [
    'dotransform'
]


@configure(
    label='To DNS Servers [IP Config]',
    description='This transform gets the DNS servers being used by this machine.',
    uuids=[ 'sploitego.v2.LocationToDNSServer_IPConfig' ],
    inputs=[ ( 'Reconnaissance', Location ) ],
)
def dotransform(request, response):
    for r in resolvers():
        response += IPv4Address(r)
    return response
########NEW FILE########
__FILENAME__ = findsubdomains
# !/usr/bin/env python
from Queue import Queue
import re

from threading import Thread
from time import sleep
from uuid import uuid4

from canari.maltego.configuration import BuiltInTransformSets
from canari.maltego.entities import DNSName, Domain
from canari.maltego.message import UIMessage
from canari.maltego.utils import debug
from canari.framework import configure
from canari.config import config

import dns

from common.dnstools import nslookup_raw


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'onterminate',
    'dotransform'
]


class DNSResolver(Thread):
    def __init__(self, domain, queue_recv, queue_send, lookup_rate=None):
        super(DNSResolver, self).__init__()
        self.domain = domain
        self.lookup_rate = lookup_rate or config['dnsdiscovery/lookup_rate']
        self.queue_send = queue_send
        self.queue_recv = queue_recv

    def run(self):
        while True:
            subdomain = self.queue_recv.get()
            if not subdomain:
                break
            name = '%s.%s' % (subdomain, self.domain)
            name = re.sub('\.+', '.', name)
            # debug('Resolving name: %s' % name)
            try:
                msg = nslookup_raw(name)
                if msg.answer:
                    self.queue_send.put(msg)
            except dns.exception.Timeout:
                debug('Request timed out for name: %s' % name)
                pass
            sleep(1 / self.lookup_rate)
        self.queue_send.put(None)

def get_names(domain, msg):
    names = set([])
    if msg.answer:
        for rrset in msg.answer:
            name = rrset.name.to_text()[:-1]
            if rrset.name.to_text()[:-1].endswith(domain):
                names.add(name)
            for rr in rrset:
                cname = rr.to_text()[:-1]
                if rr.rdtype == dns.rdatatype.CNAME and cname.endswith(domain):
                    names.add(cname)
    return names


def get_ip_addresses(msg):
    return set([rr.to_text() for rrset in msg.answer for rr in rrset if rrset.rdtype == 1])


@configure(
    label='To DNS Names [Brute Force]',
    description='This transform attempts to find subdomains using brute-force with a custom word list.',
    uuids=['sploitego.v2.DomainToDNSName_BruteForce'],
    inputs=[( BuiltInTransformSets.DNSFromIP, Domain )],
)
def dotransform(request, response):

    domain = request.value
    wildcard_ips = set()
    found_subdomains = {}

    try:
        msg = nslookup_raw('%s.%s' % (str(uuid4()), domain))
        if msg.answer:
            wildcard_ips = get_ip_addresses(msg)
            name = '*.%s' % domain
            response += DNSName(name)
            found_subdomains[name] = 1
    except dns.exception.Timeout:
        pass

    if wildcard_ips:
        warning = 'Warning: wildcard domain is defined... results may not be accurate'
        debug(warning)
        response += UIMessage(warning)

    ncount = 0
    nthreads = config['dnsdiscovery/numthreads']
    subdomains = set(config['dnsdiscovery/wordlist'])

    threads = []
    queue_send = Queue()
    queue_recv = Queue()
    for i in range(0, nthreads):
        t = DNSResolver(request.value, queue_send, queue_recv)
        t.start()
        threads.append(t)

    for s in subdomains:
        queue_send.put(s)

    for i in range(0, nthreads):
        queue_send.put(None)

    while True:
        msg = queue_recv.get()
        if not msg:
            ncount += 1
            if ncount == nthreads:
                break
        elif msg.answer:
            ips = get_ip_addresses(msg)
            if wildcard_ips and wildcard_ips.issuperset(ips):
                continue
            for name in get_names(domain, msg):
                if name in found_subdomains:
                    continue
                else:
                    found_subdomains[name] = 1
                    response += DNSName(name)

    for t in threads:
        t.join()
    return response
########NEW FILE########
__FILENAME__ = geoip
#!/usr/bin/env python

import string

from canari.maltego.entities import Location, IPv4Address, DNSName
from canari.maltego.message import UIMessage, Label
from canari.framework import configure
from canari.maltego.html import A

from sploitego.webtools.geoip import locate
from sploitego.resource import flag


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform',
    'onterminate'
]


def maplink(r, config):
    l = config['geoip/maplink']
    return l.format(**r)

@configure(
    label='To Location [Smart IP]',
    description='This transform attempts to geo locate the given IP or hostname.',
    uuids=[
        'sploitego.v2.IPv4AddressToLocation_SmartIP',
        'sploitego.v2.DNSNameToLocation_SmartIP'
    ],
    inputs=[
        ('Reconnaissance', IPv4Address),
        ('Reconnaissance', DNSName)
    ],
    remote=True
)
def dotransform(request, response, config):
    r = locate(request.value)
    if r is not None:
        if 'error' in r:
            response += UIMessage(r['error'])
            return response
        locname = ''
        cityf = None
        countryf = None
        if 'city' in r:
            locname += r['city']
            cityf = r['city']
        if 'country_name' in r:
            locname += ', %s' % r['country_name']
            countryf = r['country_name']
        e = Location(locname)
        if 'longitude' in r and 'latitude' in r:
            e.longitude = float(r['longitude'] or 0.0)
            e.latitude = float(r['latitude'] or 0.0)
            link = maplink(r, config)
            e += Label('Map It', A(link, link), type='text/html')
        if 'region_name' in r:
            e.area = r['region_name']
        if cityf is not None:
            e.city = cityf
        if countryf is not None:
            e.country = countryf
            e.iconurl = flag(countryf)
        if 'country_code' in r:
            e.countrycode = r['country_code']
            if e.iconurl is None:
                e.iconurl = flag(r['country_code'])
        response += e
    return response

########NEW FILE########
__FILENAME__ = ipv4tonetblock
#!/usr/bin/env python

from canari.maltego.configuration import BuiltInTransformSets
from canari.maltego.entities import Netblock, IPv4Address
from xml.etree.cElementTree import fromstring
from iptools.ip import IPAddress, IPNetwork
from canari.maltego.message import Label
from canari.framework import configure
from iptools.arin import whoisip


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Netblocks [ARIN WHOIS]',
    description='This transform fetches the net blocks that the given IP belongs to using an ARIN WHOIS lookup.',
    uuids=[ 'sploitego.v2.IPv4AddressToNetblock_ARIN' ],
    inputs=[ ( BuiltInTransformSets.IPOwnerDetail, IPv4Address ) ],
)
def dotransform(request, response):
    ip = IPAddress(request.value)
    w = fromstring(whoisip(ip, accept='application/xml'))
    network = IPNetwork([
        w.find('{http://www.arin.net/whoisrws/core/v1}startAddress').text,
        w.find('{http://www.arin.net/whoisrws/core/v1}endAddress').text
    ])
    e = Netblock(network.netblock)
    e += Label('CIDR Notation', repr(network))
    e += Label('Network Mask', network.netmask)
    e += Label('Number of Hosts', int(~network.netmask) - 1)
    response += e
    for nb in w.findall('netBlocks/netBlock'):
        network = IPNetwork([
            nb.find('startAddress').text,
            nb.find('endAddress').text
        ])
        e = Netblock(network.netblock)
        e += Label('CIDR Notation', repr(network))
        e += Label('Network Mask', network.netmask)
        e += Label('Number of Hosts', int(~network.netmask) - 1)
    return response
########NEW FILE########
__FILENAME__ = irsscan
# !/usr/bin/env python

from optparse import OptionParser
from Queue import Queue, Empty
from threading import Thread
from time import sleep

from scapy.all import Ether, ARP, IP, TCP, ICMP, sendp, srp, RandShort, RandInt, arping
from canari.maltego.entities import Netblock, IPv4Address
from canari.framework import configure, superuser
from common.entities import Port, PortStatus
from iptools.ip import iprange, portrange
from canari.maltego.message import Label
from canari.maltego.utils import debug
from canari.config import config


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = ['Inspired by IRS Scan tool (http://oxid.it)']

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'onterminate',
    'dotransform'
]


class ArpCachePoisoner(Thread):
    def __init__(self, *args):
        self.mac = args[0]
        self.rmac = args[1]
        self.poison_rate = config['irsscan/poison_rate']
        super(ArpCachePoisoner, self).__init__()

    def whohas(self, ip):
        ans = arping(ip, verbose=False)[0]
        if not ans:
            return None
        return ans[0][1].hwsrc

    def run(self):

        debug('ARP cache poisoning thread waiting for victims...')
        ip = q.get()
        debug('Acquired first victim... %s' % ip)

        pe = Ether(src=self.mac, dst=self.rmac)
        pa = ARP(op='who-has', hwsrc=self.mac, psrc=ip, pdst=ip, hwdst=self.rmac)

        oldmac = self.whohas(ip)
        oldip = ip

        while True:
            try:
                ip = q.get_nowait()
                if oldmac is not None:
                    debug('Healing victim %s/%s' % (oldip, oldmac))
                    pa.psrc = oldip
                    pa.hwsrc = oldmac
                    sendp(pe / pa, verbose=0)
                if ip is None:
                    break
                else:
                    debug('Changing victim to %s...' % ip)
                    pa.psrc = ip
                    pa.hwsrc = self.mac
                    oldip = ip
                    oldmac = self.whohas(ip)
            except Empty:
                # Send the poison... all your base are belong to us!
                debug('Poisoning %s...' % ip)
                sendp(pe / pa, verbose=0)
                sleep(1 / self.poison_rate)


def parse_args(args):
    parser = OptionParser(
        prog=__name__,
        version=__version__,
        description='Spoofs IP range attempting to reach target host via given ports.'
    )
    parser.add_option('-d', dest='target_host', help='Target destination for IRS scan', metavar='host')
    parser.add_option('-p', dest='target_ports', help='Target ports for IRS scan', metavar='p1,p2,pN')
    return parser.parse_args(args)[0]


@superuser
@configure(
    label='To Ports [IRS Scan]',
    description='This transform performs an IRS scan for the given net block. Note: this is an active attack.',
    uuids=[
        'sploitego.v2.NetblockToPort_IRSScan',
        'sploitego.v2.IPv4AddressToPort_IRSScan'
    ],
    inputs=[
        ('Reconnaissance', Netblock),
        ('Reconnaissance', IPv4Address)
    ]
)
def dotransform(request, response):
    params = parse_args(request.params)

    ports = portrange(params.target_ports) if params.target_ports is not None else config['irsscan/target_ports']
    dst = params.target_host if params.target_host is not None else config['irsscan/target_host']

    global q
    q = Queue()

    debug('Sending probes to %s' % dst)

    # This is the template used to send traffic
    p = Ether() / IP(dst=dst, id=int(RandShort())) / TCP(dport=ports, sport=int(RandShort()), seq=int(RandInt()))

    # We need to fix these values so that Scapy doesn't poop all over them
    p.dst = router_mac = p.dst
    p.src = my_mac = p.src

    # Begin the evil... mwuahahahahaha..
    apw = ArpCachePoisoner(my_mac, router_mac)
    apw.start()

    # Loop through our IP address block and send out the probes
    for i in iprange(request.value):

        # Queue and set the current IP we are poisoning for the poisoner.
        q.put(str(i))
        p[IP].src = str(i)
        sleep(0.5)

        # Send the probes!
        ans, unans = srp(
            p,
            retry=config['irsscan/sr_retries'],
            timeout=config['irsscan/sr_timeout'],
            verbose=config['irsscan/sr_verbose']
        )

        if ans:
            for a in ans:
                req, res = a
                e = Port(req.dport)
                e.source = req[IP].src
                e.destination = req[IP].dst
                e.protocol = 'tcp'
                e += Label('Summary', res.summary())
                if TCP in res:
                    e.response = res[TCP].sprintf('TCP:%flags%')
                    e.status = PortStatus.Closed if (res[TCP].flags & 4) else PortStatus.Open
                elif ICMP in res:
                    e.response = res[ICMP].sprintf('ICMP:%type%')
                    e.status = PortStatus.TimedOut
                response += e

        if unans:
            for u in unans:
                e = Port(u.dport)
                e.source = u[IP].src
                e.destination = u[IP].dst
                e.status = PortStatus.TimedOut
                e.response = 'none'
                response += e


    # Goodbye!
    q.put(None)
    apw.join()

    return response


def onterminate(*args):
    debug('Terminated.')
    exit(0)
########NEW FILE########
__FILENAME__ = loctonetblock
#!/usr/bin/env python

from canari.maltego.entities import Netblock, Location
from iptools.ip import IPAddress, IPNetwork
from canari.framework import configure
from scapy.all import conf

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To IP Netblocks [Local]',
    description='This transform gets the netblocks that are directly attached to this computer.',
    uuids=[ 'sploitego.v2.LocationToNetblock_Local' ],
    inputs=[ ( 'Reconnaissance', Location ) ],
)
def dotransform(request, response):

    for r in conf.route.routes:
        net = IPNetwork([IPAddress(r[0]), IPAddress(r[1])])
        if net.cidrlen not in [32, 0]:
            response += Netblock(net.netblock)

    return response
########NEW FILE########
__FILENAME__ = mactodevice
#!/usr/bin/env python

from re import split

from canari.maltego.message import UIMessage, Field, MatchingRule
from canari.maltego.entities import Device, IPv4Address
from canari.framework import configure


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Device [IEEE OUI]',
    description='This transform gets the device manufacturer based on the MAC Address OUI.',
    uuids=['sploitego.v2.IPv4AddressToDevice_IEEEOUI'],
    inputs=[('Reconnaissance', IPv4Address)],
)
def dotransform(request, response):
    from sploitego.webtools.ieee import ouis
    if 'ethernet.hwaddr' not in request.fields or not request.fields['ethernet.hwaddr']:
        response += UIMessage('You must provide an Ethernet Hardware Address (ethernet.hwaddr) property.')
    else:
        oui = ''.join(request.fields['ethernet.hwaddr'].split(':')[0:3]).upper()
        if oui in ouis:
            e = Device(split('[^\w]', ouis[oui], 1)[0].title())
            e += Field('organization', ouis[oui], matchingrule=MatchingRule.Loose)
            response += e
        else:
            response += Device('Unknown Manufacturer')
    return response
########NEW FILE########
__FILENAME__ = nessusmetasploit
#!/usr/bin/env python

from nessus import Report, ReportFilter, ReportFilterQuery
from canari.resource import icon_resource
from canari.maltego.message import Field
from canari.framework import configure


from common.entities import NessusVulnerability, NessusReport
from common.tenable import login


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Metasploitable [Nessus]',
    description='This transform returns the list of discovered vulnerabilities that have exploits available in Metasploit.',
    uuids=['sploitego.v2.NessusReportToMetasploitable_Nessus'],
    inputs=[('Scanning', NessusReport)],
    debug=False
)
def dotransform(request, response):
    s = login()
    if s is None:
        return response

    vulns = Report(s, request.entity.uuid, request.value).search(
        ReportFilterQuery(
            ReportFilter(
                'exploit_framework_metasploit',
                'eq',
                'true'
            )
        )
    )

    for k, v in vulns.iteritems():
        e = NessusVulnerability(v.name, weight=v.count)
        e.severity = v.severity
        e.iconurl = icon_resource('logos/metasploit.png')
        e.pluginid = v.id
        e.count = v.count
        e.family = v.family
        e.uuid = v.uuid
        e.server = s.server
        e.port = s.port
        e += Field('metasploit_name', v.hosts[0].details[0].output['metasploit_name'], displayname='Metasploit Name')
        response += e
    return response


########NEW FILE########
__FILENAME__ = nessusports
#!/usr/bin/env python

from common.entities import Port, NessusVulnerability
from canari.framework import configure
from common.tenable import login
from nessus import Report


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Ports [Nessus]',
    description='This transform retrieves all the ports associated with a given vulnerability.',
    uuids=['sploitego.v2.NessusVulnerabilityToPorts_Nessus'],
    inputs=[('Scanning', NessusVulnerability)],
    debug=False
)
def dotransform(request, response):
    s = login(host=request.entity.server, port=request.entity.port)
    if s is None:
        return response
    vulns = Report(s, request.entity.uuid, '').vulnerabilities
    for h in vulns[request.entity.pluginid].hosts:
        p = Port(h.port)
        p.destination = h.name
        p.status = 'Open'
        p.protocol = h.protocol
        response += p
    return response
########NEW FILE########
__FILENAME__ = nessusscan
#!/usr/bin/env python

from time import sleep

from canari.maltego.entities import IPv4Address
from common.tenable import scan, login, policy
from common.entities import NessusReport
from canari.framework import configure

from common.entities import IPv6Address


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Nessus Report [Nessus]',
    description='This transform performs a Nessus scan on a host.',
    uuids=['sploitego.v2.IPv6AddressToNessusReport_Nessus', 'sploitego.v2.IPv4AddressToNessusReport_Nessus'],
    inputs=[('Scanning', IPv6Address), ('Scanning', IPv4Address)],
    debug=False
)
def dotransform(request, response):
    s = login()
    if s is None:
        return response
    p = policy(s)
    if p is None:
        return response
    r = scan(s, request.value, p).report
    while r.status != 'completed':
        sleep(1)
    nr = NessusReport(r.name)
    nr.uuid = r.uuid
    nr.server = s.server
    nr.port = s.port
    response += nr
    return response


########NEW FILE########
__FILENAME__ = nessusvulns
#!/usr/bin/env python

from common.entities import NessusVulnerability, NessusReport
from canari.framework import configure
from common.tenable import login
from nessus import Report


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Vulnerabilities [Nessus]',
    description='This transform returns the list of discovered vulnerabilities.',
    uuids=['sploitego.v2.NessusReportToVulnerabilities_Nessus'],
    inputs=[('Scanning', NessusReport)],
    debug=False
)
def dotransform(request, response):
    s = login(host=request.entity.server, port=request.entity.port)
    if s is None:
        return response
    vulns = Report(s, request.entity.uuid, request.value).vulnerabilities
    for k in vulns:
        v = vulns[k]
        e = NessusVulnerability(v.name, weight=v.count)
        e.severity = v.severity
        e.pluginid = v.id
        e.count = v.count
        e.family = v.family
        e.uuid = v.uuid
        e.server = s.server
        e.port = s.port
        response += e
    return response


########NEW FILE########
__FILENAME__ = nmapallscan
#!/usr/bin/env python

from canari.framework import configure, superuser
from canari.maltego.entities import IPv4Address
from canari.maltego.message import UIMessage
from canari.maltego.utils import debug

from common.nmap import addreport, getscanner
from common.entities import IPv6Address

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


__all__ = [
    'dotransform'
]


@superuser
@configure(
    label='To Nmap Report [Nmap -A]',
    description='This transform performs an active Nmap scan.',
    uuids=[ 'sploitego.v2.IPv4AddressToNmapReport_NmapA', 'sploitego.v2.IPv6AddressToNmapReport_NmapA' ],
    inputs=[ ( 'Reconnaissance', IPv4Address ), ( 'Reconnaissance', IPv6Address ) ],
)
def dotransform(request, response):
    s = getscanner()
    debug('Starting scan on host: %s' % request.params)
    args = ['-n', '-A'] + request.params
    r = s.scan(request.value, *args)
    if r is not None:
        addreport(r, response, ' '.join(args + [request.value]), s.cmd)
    else:
        response += UIMessage(s.error)
    return response

########NEW FILE########
__FILENAME__ = nmapfastscan
#!/usr/bin/env python

from canari.framework import configure, superuser
from canari.maltego.entities import IPv4Address
from canari.maltego.message import UIMessage

from common.nmap import addreport, getscanner
from common.entities import IPv6Address


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@superuser
@configure(
    label='To Nmap Report [Nmap -F]',
    description='This transform performs an active Nmap scan.',
    uuids=['sploitego.v2.IPv4AddressToNmapReport_NmapF', 'sploitego.v2.IPv6AddressToNmapReport_NmapF'],
    inputs=[('Reconnaissance', IPv4Address), ('Reconnaissance', IPv6Address)],
)
def dotransform(request, response):
    s = getscanner()
    args = ['-n', '-Pn', '-F'] + request.params
    r = s.scan(request.value, *args)
    if r is not None:
        addreport(r, response, ' '.join(args + [request.value]), s.cmd)
    else:
        response += UIMessage(s.error)
    return response



########NEW FILE########
__FILENAME__ = nmapmonlist
# !/usr/bin/env python

import re

from sploitego.cmdtools.nmap import NmapReportParser
from canari.maltego.entities import IPv4Address
from canari.framework import configure, superuser
from canari.maltego.message import UIMessage, Field, Label
from common.entities import Port
from common.nmap import getscanner, savereport


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform',
    'onterminate'
]


@superuser
@configure(
    label='To Client IPv4Address [NTP monlist]',
    description='This transform performs an Nmap NTP monlist scan to retrieve a list of NTP clients.',
    uuids=['sploitego.v2.PortToClients_NTPMonList'],
    inputs=[('Reconnaissance', Port)],
)
def dotransform(request, response):
    if request.entity.protocol != 'UDP':
        response += UIMessage('NTP Monlist scans only work on UDP ports.')
        return response

    s = getscanner()

    args = ['-n', '-Pn', '-sU', '--script=ntp-monlist', '-p', request.value] + request.params

    r = s.scan(request.entity.destination, *args)

    if r is not None:
        for host in r.addresses:
            for port in r.ports(host):
                if 'ntp-monlist' in port['script']:
                    to_clients(response, port['script']['ntp-monlist'])
    else:
        response += UIMessage(s.error)

    return response


class Category:
    AlternativeTargetInterfaces = 0
    PrivateServers = 1
    PublicServers = 2
    PrivatePeers = 3
    PublicPeers = 4
    PrivateClients = 5
    PublicClients = 6
    OtherAssociations = 7

    @classmethod
    def name(cls, id):
        if not id:
            return 'Alternative Target Interfaces'
        elif id == 1:
            return 'Private Servers'
        elif id == 2:
            return 'Public Servers'
        elif id == 3:
            return 'Private Peers'
        elif id == 4:
            return 'Public Peers'
        elif id == 5:
            return 'Private Clients'
        elif id == 6:
            return 'Public Clients'
        elif id == 7:
            return 'Other Associations'


ip_matcher = re.compile('([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3})')


def to_clients(response, output):
    cat = None
    for line in output.split('\n'):
        if not line:
            continue
        elif line.startswith('      '):
            e = None
            if cat in range(Category.AlternativeTargetInterfaces, Category.OtherAssociations):
                for ip in ip_matcher.findall(line):
                    e = IPv4Address(ip)
                    e += Field('category', Category.name(cat), displayname='Category')
                    response += e
            elif cat == Category.OtherAssociations:
                ip, desc = line.strip().split(' ', 1)
                e = IPv4Address(ip)
                e += Label('Additional Info', desc)
                e += Field('category', Category.name(cat), displayname='Category')
                response += e
        elif line.startswith('  '):
            for id in range(Category.AlternativeTargetInterfaces, Category.OtherAssociations + 1):
                if Category.name(id) in line:
                    cat = id
                    break
########NEW FILE########
__FILENAME__ = nmaptoos
# !/usr/bin/env python

from sploitego.transforms.common.entities import NmapReport
from sploitego.transforms.common.nmap import addsystems
from sploitego.cmdtools.nmap import NmapReportParser
from canari.framework import configure


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


@configure(
    label='To OS [Nmap Report]',
    description='This transform mines OS information from an Nmap report.',
    uuids=['sploitego.v2.NmapReportToOS_NmapReport'],
    inputs=[('Reconnaissance', NmapReport)],
)
def dotransform(request, response):
    r = NmapReportParser(file(request.entity.file).read())
    addsystems(r, response)
    return response
########NEW FILE########
__FILENAME__ = nmaptoports
# !/usr/bin/env python

from sploitego.transforms.common.entities import NmapReport
from sploitego.transforms.common.nmap import addports
from sploitego.cmdtools.nmap import NmapReportParser
from canari.framework import configure


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


@configure(
    label='To Ports [Nmap Report]',
    description='This transform mines port scan information from an Nmap report.',
    uuids=['sploitego.v2.NmapReportToPorts_NmapReport'],
    inputs=[('Reconnaissance', NmapReport)],
)
def dotransform(request, response):
    r = NmapReportParser(file(request.entity.file).read())
    addports(r, response)
    return response
########NEW FILE########
__FILENAME__ = nmapudpscan
# !/usr/bin/env python

from canari.framework import configure, superuser
from canari.maltego.message import UIMessage
from canari.maltego.entities import IPv4Address

from common.nmap import addreport, getscanner
from common.entities import IPv6Address

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.2'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__author__ = 'Nadeem Douba'

__all__ = [
    'dotransform'
]


@superuser
@configure(
    label='To Nmap Report [Nmap -sU]',
    description='This transform performs an active UDP Nmap scan.',
    uuids=['sploitego.v2.IPv4AddressToNmapReport_NmapU', 'sploitego.v2.IPv6AddressToNmapReport_NmapU'],
    inputs=[('Reconnaissance', IPv4Address), ('Reconnaissance', IPv6Address)],
)
def dotransform(request, response):
    s = getscanner()
    args = ['-n', '-sU', '-Pn'] + request.params

    r = s.scan(request.value, *args)
    if r is not None:
        addreport(r, response, ' '.join(args + [request.value]), s.cmd)
    else:
        response += UIMessage(s.error)
    return response



########NEW FILE########
__FILENAME__ = nmapversionscan
# !/usr/bin/env python

from canari.maltego.entities import BuiltWithTechnology
from canari.framework import configure, superuser
from canari.maltego.message import UIMessage
from canari.maltego.message import Label

from common.entities import Port
from common.nmap import getscanner


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform',
    'onterminate'
]


@superuser
@configure(
    label='To Banner [Nmap -sV]',
    description='This transform performs an Nmap Version Scan. Note: this is an active scan.',
    uuids=['sploitego.v2.PortToBanner_NmapV'],
    inputs=[('Reconnaissance', Port)],
)
def dotransform(request, response):
    s = getscanner()
    args = ['-n', '-Pn', '-sV', '-p', request.value] + request.params
    if not request.entity.protocol:
        request.entity.protocol = 'TCP'
    elif request.entity.protocol.upper() == 'UDP':
        args.insert(0, '-sU')
    r = s.scan(request.entity.destination, *args)
    if r is not None:
        for host in r.addresses:
            for port in r.ports(host):
                e = BuiltWithTechnology(r.tobanner(port))
                if 'servicefp' in port:
                    e += Label('Service Fingerprint', port['servicefp'])
                if 'extrainfo' in port:
                    e += Label('Extra Information', port['extrainfo'])
                if 'method' in port:
                    e += Label('Method', port['method'])
                response += e
    else:
        response += UIMessage(s.error)
    return response
########NEW FILE########
__FILENAME__ = p0f
#!/usr/bin/env python

from canari.maltego.entities import BuiltWithTechnology, IPv4Address
from sploitego.cmdtools.p0f import fingerprint, P0fStatus
from canari.framework import configure, superuser


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform',
    'onterminate'
]

@superuser
@configure(
    label='To Technology [P0f]',
    description='This transform queries the P0f API for an OS fingerprint.',
    uuids=['sploitego.v2.IPv4AddressToTechnology_P0f'],
    inputs=[('Reconnaissance', IPv4Address)],
)
def dotransform(request, response):
    i = fingerprint(request.value)
    if i['status'] == P0fStatus.OK and i['os_name']:
        d = '%s %s' % (i['os_name'], i['os_flavor'])
        if i['http_name']:
            d = '%s (%s)' % (i['http_name'], d)
        response += BuiltWithTechnology(d)
    return response
########NEW FILE########
__FILENAME__ = passivedns
#!/usr/bin/env python

from canari.maltego.entities import Location, DNSName
from canari.framework import configure, superuser
from canari.config import config
from scapy.all import DNS, sniff

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@superuser
@configure(
    label='To DNS Names [Passive Scan]',
    description='This transform returns the DNS queries that are occuring on the local network.',
    uuids=[ 'sploitego.v2.LocationToDNSName_PassiveScan' ],
    inputs=[ ( 'Reconnaissance', Location ) ]
)
def dotransform(request, response):
    r = sniff(count=config['scapy/sniffcount'], timeout=config['scapy/snifftimeout'])
    names = {}
    for i in r:
        if DNS in i:
            for j in range(i[DNS].qdcount):
                q = i[DNS].qd[j].qname.rstrip('.')
                if q not in names:
                    names[q] = True
                    response += DNSName(q)

    return response
########NEW FILE########
__FILENAME__ = pipltolocation
# !/usr/bin/env python

from json.decoder import JSONDecoder

from canari.maltego.entities import Person, Location
from canari.maltego.message import UIMessage, Label
from sploitego.webtools.pipl import pipljsonsearch
from canari.framework import configure

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Location [Pipl]',
    description="This transform attempts to find a person's address.",
    uuids=['sploitego.v2.PersonToLocation_Pipl'],
    inputs=[('Location From Person', Person)],
)
def dotransform(request, response):
    p = JSONDecoder().decode(
        pipljsonsearch(
            first_name=request.entity.firstnames or '',
            last_name=request.entity.lastname or ''
        )
    )

    if 'error' in p:
        response += UIMessage(p['error'])

    for r in p['results']['records']:
        if 'addresses' in r:
            for a in r['addresses']:
                e = Location(a['display'])
                e.countrycode = a['country']
                e += Label(
                    'Source', '<a href="%s">%s</a>' % (r['source']['url'], r['source']['@ds_name']), type='text/html'
                )
                response += e

    return response
########NEW FILE########
__FILENAME__ = pipltorelationships
#!/usr/bin/env python

from json.decoder import JSONDecoder

from canari.maltego.message import UIMessage, Label
from sploitego.webtools.pipl import pipljsonsearch
from canari.maltego.entities import Person
from canari.framework import configure

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Related People [Pipl]',
    description="This transform attempts to find people related to the person in question.",
    uuids=[ 'sploitego.v2.PersonToRelatedPeople_Pipl' ],
    inputs=[ ( 'Relationships From Person', Person ) ],
)
def dotransform(request, response):
    p = JSONDecoder().decode(
        pipljsonsearch(
            first_name=request.entity.firstnames or '',
            last_name=request.entity.lastname or ''
        )
    )

    if 'error' in p:
        response += UIMessage(p['error'])

    for r in p['results']['records']:
        if 'relationships' in r:
            for rel in r['relationships']:
                e = Person(rel['name']['display'])
                e += Label(
                    'Source', '<a href="%s">%s</a>' % (r['source']['url'], r['source']['@ds_name']), type='text/html'
                )
                response += e

    return response
########NEW FILE########
__FILENAME__ = sitereputation
#!/usr/bin/env python

from sploitego.webtools.aceinsights import AceInsightMiner, Miner
from canari.maltego.entities import Website
from common.entities import SiteCategory
from canari.framework import configure

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Site Category [Websense]',
    description='Gets the site category for a given Website.',
    uuids=[ 'sploitego.v2.WebsiteToSiteCategory_Websense' ],
    inputs=[('Reconnaissance', Website)]
)
def dotransform(request, response):
    ac = AceInsightMiner(request.value)
    r = ac.getdata(Miner.WebsenseCategory)
    if r is not None:
        if 'static_category_name' in r:
            response += SiteCategory(r['static_category_name'])
        elif 'realtime_category_name' in r:
            response += SiteCategory(r['realtime_category_name'])
    return response

########NEW FILE########
__FILENAME__ = snmpbruteforcer
#!/usr/bin/env python

from sploitego.scapytools.snmp import SNMPBruteForcer
from canari.maltego.message import MaltegoException
from common.entities import Port, SNMPCommunity
from canari.utils.wordlist import wordlist
from canari.framework import configure
from iptools.ip import IPAddress
from canari.config import config

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To SNMP Community [Brute Force]',
    description='This transform attempts to find SNMP community strings using a word list',
    uuids=['sploitego.v2.PortToSNMPCommunity_BruteForce'],
    inputs=[('Reconnaissance', Port)]
)
def dotransform(request, response):
    protocol = (request.entity.protocol or 'UDP').upper()
    if protocol != 'UDP':
        raise MaltegoException('SNMP over UDP for versions 1 and 2c are only supported.')
    agent = str(IPAddress(request.entity.destination))
    port = int(request.value)
    wl = config['snmp/wordlist']
    for v in ['v1', 'v2c']:
        bf = SNMPBruteForcer(agent, port, v, config['snmp/bf_timeout'], config['snmp/bf_rate'])
        for c in bf.guess(wl):
            e = SNMPCommunity(c)
            e.port = port
            e.agent = agent
            e.protocol = protocol
            e.version = v
            response += e
    return response

########NEW FILE########
__FILENAME__ = snmpcontact
#!/usr/bin/env python

from sploitego.scapytools.snmp import SNMPManager, SNMPError
from canari.maltego.message import UIMessage
from canari.maltego.entities import Person
from common.entities import SNMPCommunity
from canari.framework import configure
from common.snmp import snmpargs


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Person [SNMP]',
    description='This transform uses SNMP to retrieve the responsible person for the device being queried.',
    uuids=['sploitego.v2.SNMPCommunityToPerson_SNMP'],
    inputs=[('Reconnaissance', SNMPCommunity)]
)
def dotransform(request, response):
    try:
        s = SNMPManager(*snmpargs(request))
        response += Person(s.contact)
    except SNMPError, s:
        response += UIMessage(str(s))
    return response



########NEW FILE########
__FILENAME__ = snmphostname
#!/usr/bin/env python

from sploitego.scapytools.snmp import SNMPManager, SNMPError
from canari.maltego.message import UIMessage
from canari.maltego.entities import DNSName
from common.entities import SNMPCommunity
from canari.framework import configure
from common.snmp import snmpargs


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To DNS Name [SNMP]',
    description='This transform uses SNMP to retrieve the hostname of the device being queried.',
    uuids=['sploitego.v2.SNMPCommunityToDNSName_SNMP'],
    inputs=[('Reconnaissance', SNMPCommunity)]
)
def dotransform(request, response):
    try:
        s = SNMPManager(*snmpargs(request))
        response += DNSName(s.hostname)
    except SNMPError, s:
        response += UIMessage(str(s))
    return response
########NEW FILE########
__FILENAME__ = snmplocation
#!/usr/bin/env python

from sploitego.scapytools.snmp import SNMPManager, SNMPError
from canari.maltego.message import UIMessage
from canari.maltego.entities import Location
from common.entities import SNMPCommunity
from canari.framework import configure
from common.snmp import snmpargs


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Location [SNMP]',
    description='This transform uses SNMP to retrieve the location of the device being queried.',
    uuids=['sploitego.v2.SNMPCommunityToLocation_SNMP'],
    inputs=[('Reconnaissance', SNMPCommunity)]
)
def dotransform(request, response):
    try:
        s = SNMPManager(*snmpargs(request))
        response += Location(s.location)
    except SNMPError, s:
        response += UIMessage(str(s))
    return response



########NEW FILE########
__FILENAME__ = snmproutes
#!/usr/bin/env python

from sploitego.scapytools.snmp import SNMPManager, SNMPError
from canari.maltego.message import UIMessage, Label
from canari.maltego.entities import IPv4Address
from common.entities import SNMPCommunity
from canari.framework import configure
from canari.maltego.html import Table
from common.snmp import snmpargs


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Routes [SNMP]',
    description='This transform uses SNMP to retrieve the routing table for the device being queried.',
    uuids=['sploitego.v2.SNMPCommunityToRoute_SNMP'],
    inputs=[('Reconnaissance', SNMPCommunity)]
)
def dotransform(request, response):
    try:
        s = SNMPManager(*snmpargs(request))
        nexthops = {}
        for i in s.walk('1.3.6.1.2.1.4.21.1.1'):
            nm = s.get('.'.join(['1.3.6.1.2.1.4.21.1.11', i['value']]))
            if nm['value'] != '255.255.255.255':
                nh = s.get('.'.join(['1.3.6.1.2.1.4.21.1.7', i['value']]))
                if nh['value'] not in nexthops:
                    nexthops[nh['value']] = []
                nexthops[nh['value']].append(i['value'])
        for nh in nexthops:
            e = IPv4Address(nh)
            t = Table(['Destination Network'], 'Routing Table')
            for r in nexthops[nh]:
                t.addrow([r])
            e += Label('Routing Table', t, type='text/html')
            response += e
    except SNMPError, s:
        response += UIMessage(str(s))
    return response
########NEW FILE########
__FILENAME__ = tometasploitsession
# !/usr/bin/env python

from nessus import Report
from canari.resource import icon_resource
from canari.framework import configure

from common.entities import NessusVulnerability, MetasploitSession
from common.tenable import login as nessus_login
from common.msfrpcd import login as metasploit_login


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Session [Metasploit]',
    description='This transform returns a Metasploit session if successful.',
    uuids=['sploitego.v2.NessusVulnToMetasploitSession_Metasploit'],
    inputs=[('Exploitation', NessusVulnerability)],
    debug=False
)
def dotransform(request, response):
    from sploitego.msftools.exploit import launch

    s = nessus_login(host=request.entity.server, port=request.entity.port)
    if s is None:
        return response
    m = metasploit_login()
    if m is None:
        return response

    vulns = Report(s, request.entity.uuid, '').vulnerabilities
    for h in vulns[request.entity.pluginid].hosts:
        session = launch(m, {'RPORT': int(h.port), 'RHOST': h.name}, filter_=request.fields.get('metasploit_name'))

        if session != -1:
            e = MetasploitSession('%s:%s' % (h.name, h.port))
            e.sessionid = session
            e.server = m.server
            e.port = m.port
            e.uri = m.uri
            e.iconurl = icon_resource('logos/terminal.png')
            response += e
        break

    return response


########NEW FILE########
__FILENAME__ = tometasploitshell
#!/usr/bin/env python
import os
import subprocess
from canari.commands.common import get_bin_dir

from canari.framework import configure

from common.entities import MetasploitSession


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To Shell [Metasploit]',
    description='This transform returns a Metasploit shell if successful.',
    uuids=['sploitego.v2.MetasploitSessionToShell_Metasploit'],
    inputs=[('Exploitation', MetasploitSession)],
    debug=False
)
def dotransform(request, response):
    script = os.path.join(get_bin_dir(), 'qtmsfconsole')
    subprocess.Popen(
        [
            script,
            request.entity.server,
            request.entity.port,
            request.entity.uri,
            request.entity.uuid
        ]
    )
    return response


########NEW FILE########
__FILENAME__ = towebsite
# !/usr/bin/env python

from urllib import urlopen

from canari.maltego.entities import Website, DNSName
from sploitego.webtools.thumbnails import thumbnail
from canari.maltego.message import UIMessage
from canari.framework import configure

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform',
    'onterminate'
]


@configure(
    label='To Web site [Query Ports 80]',
    description='This transform queries port 80 for websites',
    uuids=['sploitego.v2.DNSNameToWebsite_QueryPorts'],
    inputs=[('Reconnaissance', DNSName)],
)
def dotransform(request, response):
    try:
        url = 'http://%s' % request.value
        urlopen(url)
        response += Website(request.value, iconurl=thumbnail(url))
    except IOError, ioe:
        response += UIMessage(str(ioe))
    return response
########NEW FILE########
__FILENAME__ = wappalyzer
#!/usr/bin/env python

from canari.maltego.entities import URL, BuiltWithTechnology
from sploitego.webtools.wappalyzer import Wappalyzer
from canari.maltego.message import Field
from canari.framework import configure


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = ['Inspired by Wappalyzer (http://wappalyzer.com)']

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]

@configure(
    label='To BuiltWith [Wappalyzer]',
    description='This transform will attempt to fingerprint the URLs application stack',
    uuids=['sploitego.v2.URLToBuiltWith_Wappalyzer'],
    inputs=[('Reconnaissance', URL)],
    debug=True
)
def dotransform(request, response):
    r = Wappalyzer().analyze(request.value)
    for i in r:
        e = BuiltWithTechnology(i)
        e += Field('categories', ', '.join(r[i]))
        response += e
    return response
########NEW FILE########
__FILENAME__ = whatismyhostname
#!/usr/bin/env python

from socket import gethostname

from canari.maltego.entities import DNSName, Location
from canari.framework import configure

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To DNS Name [Hostname]',
    description='This transform gets this hosts Host Name.',
    uuids=[ 'sploitego.v2.LocationToDNSName_Hostname' ],
    inputs=[ ( 'Reconnaissance', Location ) ],
)
def dotransform(request, response):
    response += DNSName(gethostname())
    return response
########NEW FILE########
__FILENAME__ = whatismyinternetip
# !/usr/bin/env python

from canari.maltego.entities import Location, IPv4Address
from sploitego.webtools.geoip import locate
from canari.framework import configure

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform',
    'onterminate'
]


@configure(
    label='To IP Address [Internet]',
    description='This transform returns your Internet IP.',
    uuids=['sploitego.v2.LocationToIPv4Address_Internet'],
    inputs=[('Reconnaissance', Location)],
)
def dotransform(request, response):
    r = locate()
    if r is not None:
        response += IPv4Address(r['ip'])
    return response
########NEW FILE########
__FILENAME__ = whatismyip
#!/usr/bin/env python

from canari.maltego.entities import IPv4Address, Location
from canari.maltego.message import Field, MatchingRule
from canari.framework import configure
from scapy.all import IP, Ether

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='To IP Address [Local]',
    description='This transform gets the interface IP Address.',
    uuids=[ 'sploitego.v2.LocationToIPv4Address_Local' ],
    inputs=[ ( 'Reconnaissance', Location ) ],
)
def dotransform(request, response):
    e = IPv4Address(IP(dst='4.2.2.1').src)
    e.internal = True
    e += Field(
        "ethernet.hwaddr", (Ether()/IP(dst='4.2.2.1')).src,
        displayname="Hardware Address", matching_rule=MatchingRule.Loose
    )
    response += e
    return response
########NEW FILE########
__FILENAME__ = aceinsights
#!/usr/bin/env python

from json import JSONDecoder, JSONEncoder
from httplib import HTTPConnection
from time import sleep


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'MinerError',
    'Miner',
    'AceInsightMiner'
]


class MinerError(Exception):
    pass


class Miner(object):
    GeoLocation = 1
    GlobalRanking = 2
    AlexaMetrics = 3
    TwitterTrend = 4
    Unknown = 5
    WebsenseCategory = 6
    SecurityCategory = 7
    CurrentThreatLevel = 8


class AceInsightMiner(object):

    _headers = {'Content-Type' : 'application/json; charset=utf-8'}

    def __init__(self, url):
        self.conn = HTTPConnection('aceinsight.websense.com')
        self._jd = JSONDecoder()
        self._je = JSONEncoder()
        self._lid = self._guid(url)

    def _status(self, miner, attempt):
        self.conn.request(
            'POST',
            '/AceDataService.svc/GetMinerStatus',
            headers=self._headers,
            body=self._je.encode({
                'lookupId' : self._lid,
                'minerId' : miner,
                'attempts' : attempt
            })
        )
        r = self.conn.getresponse()
        return r.status == 200 and r.read() == '{"d":"Complete"}'

    def _guid(self, url):
        self.conn.request(
            'POST',
            '/AceDataService.svc/GetGuid',
            headers=self._headers,
            body=self._je.encode({
                'currentUrl' : url,
                'userIp' : '',
                'userName' : 'guest'
            })
        )
        r = self.conn.getresponse()
        if r.status == 200:
            data = self._jd.decode(r.read())
            if isinstance(data['d'], dict) and 'LookupId' in data['d']:
                return data['d']['LookupId']
        return None

    def getdata(self, miner):
        data = {}
        if self._lid is not None:
            for attempt in xrange(0, 10):
                if self._status(miner, attempt):
                    self.conn.request(
                        'POST',
                        '/AceDataService.svc/GetCategoryData',
                        headers=self._headers,
                        body=self._je.encode({
                            'lookupId' : self._lid,
                            'minerId' : miner
                        })
                    )
                    r = self.conn.getresponse()
                    if r.status == 200:
                        data = self._jd.decode(self._jd.decode(r.read())['d'])
                    break
                sleep(0.5)
        return data


########NEW FILE########
__FILENAME__ = adplanner
#!/usr/bin/env python

from os import path

from canari.utils.fs import fsemaphore, age, cookie
from canari.utils.wordlist import wordlist
from canari.config import config


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'topsites'
]


def updatelist(filename):
    topsites = wordlist('http://www.google.com/adplanner/static/top1000/', '<a href="http://(.*?)/"target')
    f = fsemaphore(filename, 'wb')
    f.lockex()
    f.write('\n'.join(topsites))
    f.close()
    return topsites


def readlist(filename):
    f = fsemaphore(filename)
    f.locksh()
    data = wordlist('file://%s' % filename)
    f.close()
    return data


topsites = None
tmpfile = cookie('sploitego.adplanner.tmp')


if not path.exists(tmpfile) or age(tmpfile) >= config['cookie/maxage']:
    topsites = updatelist(tmpfile)
else:
    topsites = readlist(tmpfile)






########NEW FILE########
__FILENAME__ = alexa
#!/usr/bin/env python

from os import path

from canari.utils.fs import fsemaphore, cookie, age
from canari.utils.wordlist import wordlist
from canari.config import config

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'topsites'
]


def updatelist(filename):
    topsites = []
    f = fsemaphore(filename, 'wb')
    f.lockex()
    for i in xrange(20):
        page = wordlist('http://www.alexa.com/topsites/global;%d' % i, '<a href="/siteinfo/(.+)?">')
        topsites += page
        f.write('\n'.join(page))
        f.write('\n')
    f.close()
    return topsites


def readlist(filename):
    f = fsemaphore(filename)
    f.locksh()
    data = wordlist('file://%s' % filename)
    f.close()
    return data


topsites = None
tmpfile = cookie('sploitego.alexa.tmp')


if not path.exists(tmpfile) or age(tmpfile) >= config['cookie/maxage']:
    topsites = updatelist(tmpfile)
else:
    topsites = readlist(tmpfile)
########NEW FILE########
__FILENAME__ = bing
#!/usr/bin/env python

from httplib import HTTPConnection
from urllib import urlencode

from canari.config import config


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'searchweb'
]


def searchweb(query, content_type='xml'):
    if content_type not in ['xml', 'json']:
        raise ValueError('Invalid content type requested: %s' % content_type)

    maxpages = config['bing/maxpages']
    appid = config['bing/appid']
    c = HTTPConnection('api.bing.net')
    params = {'Appid': appid, 'query': query, 'sources': 'web', 'web.count': 50, 'web.offset' : 0}


    pages = []
    for i in range(0, maxpages):
        c.request('GET', '/%s.aspx?%s' % (content_type, urlencode(params)))
        r = c.getresponse()

        if r.status == 200:
            pages.append(r.read())

        params['web.offset'] += 50

    return pages

########NEW FILE########
__FILENAME__ = bluecoat
#!/usr/bin/env python

from xml.etree.cElementTree import fromstring
from urllib import urlopen
import os
from json import loads, dumps

from canari.utils.fs import fsemaphore, age, cookie
from canari.utils.wordlist import wordlist


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'sitereview'
]


def updatelist(filename):
    d = None
    with fsemaphore(filename, 'wb') as f:
        f.lockex()
        try:
            categories = wordlist(
                'http://sitereview.bluecoat.com/rest/categoryList?alpha=true',
                loads
            )
            d = dict([('%02x' % c['num'], c['name']) for c in categories])
            f.write(dumps(d))
        except Exception, e:
            f.close()
            os.unlink(tmpfile)
            raise e
    return d


def readlist(filename):
    with fsemaphore(filename) as f:
        f.locksh()
        data = wordlist('file://%s' % filename, loads)
    return data


tmpfile = cookie('sploitego.bluecoat.tmp')


def _chunks(s):
    return [s[i:i + 2] for i in range(0, len(s), 2)]


def sitereview(site, config, port=80):
    categories = None
    if not os.path.exists(tmpfile) or age(tmpfile) >= config['cookie/maxage']:
        categories = updatelist(tmpfile)
    else:
        categories = readlist(tmpfile)

    r = urlopen(
        'http://sp.cwfservice.net/1/R/%s/K9-00006/0/GET/HTTP/%s/%s///' % (config['bluecoat/license'], site, port)
    )

    if r.code == 200:
        e = fromstring(r.read())
        domc = e.find('DomC')
        dirc = e.find('DirC')
        if domc is not None:
            cats = _chunks(domc.text)
            return [categories.get(c, 'Unknown') for c in cats]
        elif dirc is not None:
            cats = _chunks(dirc.text)
            return [categories.get(c, 'Unknown') for c in cats]
    return []

########NEW FILE########
__FILENAME__ = dnsdiscovery
#!/usr/bin/env python

from os import path

from canari.utils.fs import cookie, age, fsemaphore
from canari.utils.wordlist import wordlist
from canari.config import config

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'subdomains'
]


def updatelist(filename):
    f = fsemaphore(filename, 'wb')
    f.lockex()
    subdomains = config['dnsdiscovery/wordlist']
    f.write('\n'.join(subdomains))
    f.close()
    return subdomains


def readlist(filename):
    f = fsemaphore(filename)
    f.locksh()
    data = wordlist('file://%s' % filename)
    f.close()
    return data


subdomains = None
tmpfile = cookie('sploitego.dnsdiscovery.tmp')

if not path.exists(tmpfile) or age(tmpfile) >= config['cookie/maxage']:
    subdomains = updatelist(tmpfile)
else:
    subdomains = readlist(tmpfile)






########NEW FILE########
__FILENAME__ = geoip
#!/usr/bin/env python

from urllib2 import urlopen
from json import loads


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'locate'
]


def locate(ip=''):
    r = urlopen('http://freegeoip.net/json/%s' % ip)
    if r.code == 200:
        return loads(r.read())
    return None
########NEW FILE########
__FILENAME__ = geolocate
#!/usr/bin/env python

from json.decoder import JSONDecoder
from httplib import HTTPSConnection
from urllib import urlencode, urlopen
from random import randint
from sys import platform


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'GeoLocateError',
    'geolocate'
]


class GeoLocateError(Exception):
    pass


def _fullmac(mac):
    b = mac.split(':')
    return '-'.join(['%02X' % int(B, 16) for B in b])


def geolocate():
    networks = []
    if platform == 'darwin':
        from Foundation import NSBundle, objc
        b = NSBundle.bundleWithPath_(objc.pathForFramework('/System/Library/Frameworks/CoreWLAN.framework'))
        if b is None:
            raise SystemError('Unable to load wireless bundle. Maybe its not supported?')
        b.load()
        cwi = b.classNamed_('CWInterface')
        if cwi is None:
            raise SystemError('Unable to load CWInterface.')
        iface = cwi.interface()
        if iface is None or not iface:
            raise SystemError('Unable to load wireless interface.')
        networks = map(
            lambda x: {'ssid':x.ssid(),'mac':x.bssid(),'ss':x.rssi()},
            iface.scanForNetworksWithParameters_error_(None, None)
        )
#        iface.release()
#        b.unload()
    else:
        raise NotImplementedError('This module is still under development.')

    return _geolocate(networks)


def geomac(bssid):
    return _geolocate([{'ss': randint(-100, -70), 'mac': bssid, 'ssid': 'test'}])


def _geolocate(networks):
    if networks:
        p = '/maps/api/browserlocation/json?browser=sploitego&sensor=true'
        for n in networks:
            p += '&%s' % urlencode({'wifi':'mac:%s|ssid:%s|ss:%s' % (_fullmac(n['mac']), n['ssid'], n['ss'])})

        print p
        c = HTTPSConnection('maps.googleapis.com')
        c.request('GET', p)
        r = c.getresponse()

        if r.status == 200 and r.getheader('Content-Type').startswith('application/json'):
            j = JSONDecoder()
            d = j.decode(r.read())
            if d['status'] == 'OK':
                l = d['location']
                return {'latitude':l['lat'],'longitude':l['lng'],'accuracy':d['accuracy']}

    raise GeoLocateError('Unable to geolocate.')


def reversegeo(lat, lng):
    r = urlopen('https://maps.googleapis.com/maps/api/geocode/json?latlng=%f,%f&sensor=true' % (lat, lng))
    if r.code == 200 and r.headers['Content-Type'].startswith('application/json'):
        r = JSONDecoder().decode(r.read())
        if r['status'] == 'OK':
            return r['results']
        else:
            raise GeoLocateError('Unable to reverse geo code lat long: %s.' % r['status'])
    raise GeoLocateError('Unable to reverse geo code lat long.')
########NEW FILE########
__FILENAME__ = ieee
#!/usr/bin/env python

from os import path
from re import split

from canari.utils.fs import cookie, age, fsemaphore
from canari.utils.wordlist import wordlist
from canari.config import config


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'ouis'
]


def updatelist(filename):

    f = fsemaphore(filename, 'wb')
    f.lockex()
    ouis = dict(
        map(
            lambda x: split(r'\s+\(base 16\)\s+', x),
            wordlist('http://standards.ieee.org/develop/regauth/oui/oui.txt', r'([\d\w]{6}\s+\(base 16\)\s+\w.+)\n')
        )
    )
    for o in ouis:
        f.write('%s\n' % ','.join([o, ouis[o]]))
    f.close()
    return ouis


def readlist(filename):
    f = fsemaphore(filename)
    f.locksh()
    data = wordlist('file://%s' % filename)
    f.close()
    return dict(map(lambda x: (x[0],x[1]), map(lambda x: x.split(','), data)))


ouis = None
tmpfile = cookie('sploitego.ieee.tmp')


if not path.exists(tmpfile) or age(tmpfile) >= config['cookie/maxage']:
    ouis = updatelist(tmpfile)
else:
    ouis = readlist(tmpfile)
########NEW FILE########
__FILENAME__ = pipl
#!/usr/bin/env python

from urllib import urlencode, urlopen

from canari.config import config

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'PiplSearchError',
    'PiplSearchType',
    'PiplPeopleMode',
    'piplsearch',
    'piplxmlsearch',
    'pipljsonsearch'
]


class PiplSearchError(Exception):
    pass


class PiplSearchType(object):
    XML = "xml"
    JSON = "json"


class PiplPeopleMode(object):
    All = "all"
    One = "one"


def piplsearch(**kwargs):

    type = kwargs.get('type', PiplSearchType.XML)

    if type not in [PiplSearchType.JSON, PiplSearchType.XML]:
        raise PiplSearchError("Search type must be either 'json' or 'xml' not '%s'." % type)

    d = {
        'exact_name': kwargs.get('exact_name', 0),
        'no_sponsored': kwargs.get('no_sponsored', 1),
        'person_mode': kwargs.get('person_mode', PiplPeopleMode.All),
        'key': config['pipl/apikey']
    }

    if d['key'] is None:
        raise PiplSearchError('You need an API key to search Pipl.')

    if d['person_mode'] not in [PiplPeopleMode.All, PiplPeopleMode.One]:
        raise PiplSearchError("Person search mode must be either 'all' or 'one' not '%s'." % d['person_mode'])

    if 'country' in d and len(d['country']) != 2:
        raise PiplSearchError("Country must be a two letter country code.")

    if 'state' in d and len(d['state']) != 2:
        raise PiplSearchError("State/province must be a two letter state code.")

    params = [
        'first_name','middle_name','last_name','country','state',
        'city','from_age','to_age','email','phone','username','tag'
    ]

    for k in kwargs:
        if k in params and kwargs[k] is not None:
            d[k] = kwargs[k]

    url = 'http://apis.pipl.com/search/v2/%s/?%s' % (type, urlencode(d))

    r = urlopen(url)

    return r.read()


def piplxmlsearch(**kwargs):
    kwargs.update({'type':'xml'})
    return piplsearch(**kwargs)


def pipljsonsearch(**kwargs):
    kwargs.update({'type':'json'})
    return piplsearch(**kwargs)
########NEW FILE########
__FILENAME__ = thumbnails
#!/usr/bin/env python

from canari.config import config

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


def thumbnail(url):
    return config['thumbnail/service'].replace('$url', url)


########NEW FILE########
__FILENAME__ = wappalyzer
#!/usr/bin/env python

from urllib import urlopen
from re import search, findall


__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


class Wappalyzer:
    categories = {
        1: { 'name': 'CMS', 'plural': 'CMS' },
        2: { 'name': 'Message Board', 'plural': 'Message Boards' },
        3: { 'name': 'Database Manager', 'plural': 'Database Managers' },
        4: { 'name': 'Documentation Tool', 'plural': 'Documentation Tools' },
        5: { 'name': 'Widget', 'plural': 'Widgets' },
        6: { 'name': 'Web Shop', 'plural': 'Web Shops' },
        7: { 'name': 'Photo Gallery', 'plural': 'Photo Galleries' },
        8: { 'name': 'Wiki', 'plural': 'Wikis' },
        9: { 'name': 'Hosting Panel', 'plural': 'Hosting Panels' },
        10: { 'name': 'Analytics', 'plural': 'Analytics' },
        11: { 'name': 'Blog', 'plural': 'Blogs' },
        12: { 'name': 'JavaScript Framework', 'plural': 'JavaScript Frameworks' },
        13: { 'name': 'Issue Tracker', 'plural': 'Issue Trackers' },
        14: { 'name': 'Video Player', 'plural': 'Video Players' },
        15: { 'name': 'Comment System', 'plural': 'Comment Systems' },
        16: { 'name': 'CAPTCHA', 'plural': 'CAPTCHAs' },
        17: { 'name': 'Font Script', 'plural': 'Font Scripts' },
        18: { 'name': 'Web Framework', 'plural': 'Web Frameworks' },
        19: { 'name': 'Miscellaneous', 'plural': 'Miscellaneous' },
        20: { 'name': 'Editor', 'plural': 'Editors' },
        21: { 'name': 'LMS', 'plural': 'LMS' },
        22: { 'name': 'Web Server', 'plural': 'Web Servers' },
        23: { 'name': 'Cache Tool', 'plural': 'Cache Tools' },
        24: { 'name': 'Rich Text Editor', 'plural': 'Rich Text Editors' },
        25: { 'name': 'Javascript Graphics', 'plural': 'Javascript Graphics' },
        26: { 'name': 'Mobile Framework', 'plural': 'Mobile Frameworks' },
        27: { 'name': 'Programming Language', 'plural': 'Programming Languages' },
        28: { 'name': 'Operating System', 'plural': 'Operating Systems' },
        29: { 'name': 'Search Engine', 'plural': 'Search Engines'}
    }

    apps = {
        '1und1':                 { 'cats': [   6 ], 'url': r'/shop/catalog/browse\?sessid\=' },
        '1C-Bitrix':             { 'cats': [   1 ], 'html': '<link[^>]+components/bitrix(?i)', 'script': '1c\-bitrix(?i)' },
        '2z Project':            { 'cats': [   1 ], 'meta': { 'generator': '2z project(?i)' } },
        'AddThis':               { 'cats': [   5 ], 'script': r'addthis\.com/js', 'env': '^addthis$' },
        'Adobe GoLive':          { 'cats': [  20 ], 'meta': { 'generator': 'Adobe GoLive(?i)' } },
        'Advanced Web Stats':    { 'cats': [  10 ], 'html': r'aws.src = [^<]+caphyon\-analytics(?i)' },
        'Ametys':                { 'cats': [   1 ], 'meta': { 'generator': '(Ametys|Anyware Technologies)(?i)' }, 'script': 'STools.js' },
        'Amiro.CMS':             { 'cats': [   1 ], 'meta': { 'generator': 'Amiro(?i)' } },
        'AOLserver':             { 'cats': [  22 ], 'headers': { 'Server': 'AOLserver(?i)' } },
        'Apache':                { 'cats': [  22 ], 'headers': { 'Server': '(Apache($|[^-])|HTTPD)(?i)' } },
        'Apache Tomcat':         { 'cats': [  22 ], 'headers': { 'Server': 'Apache-Coyote(?i)' } },
        'Apache Traffic Server': { 'cats': [  22 ], 'headers': { 'Server': 'YTS(?i)' } },
        'Arc Forum':             { 'cats': [   2 ], 'html': r'ping\.src = node\.href;' },
        'ATG Web Commerce':      { 'cats': [   6 ], 'headers': { 'X-ATG-Version': 'ATG(?i)' }, 'html': '<[^>]+_DARGS' },
        'Atlassian Confluence':  { 'cats': [   8 ], 'html': r"Powered by <a href=.'http'://www\.atlassian\.com/software/confluence(?i)" },
        'Atlassian Jira':        { 'cats': [  13 ], 'env': '^jira$(?i)', 'html': r"Powered by <a href=.'http'://www\.atlassian\.com/software/jira(?i)", 'implies': [ 'Java' ] },
        'Alloy':                 { 'cats': [  12 ], 'env': '^AUI$' },
        'AWStats':               { 'cats': [  10 ], 'meta': { 'generator': 'AWStats(?i)' } },
        'Banshee':               { 'cats': [   1,  18 ], 'html': r'Built upon the <a href=("|\')[^>]+banshee-php\.org(?i)' },
        'Backbone.js':           { 'cats': [  12 ], 'script': r'backbone.*\.js', 'env': '^Backbone$' },
        'BIGACE':                { 'cats': [   1 ], 'meta': { 'generator': 'BIGACE' }, 'html': r'Powered by <a href=("|\')[^>]+BIGACE|<!--\s+Site is running BIGACE(?i)' },
        'BigDump':               { 'cats': [   3 ], 'html': "<!-- <h1>'BigDump': Staggered MySQL Dump Importer" },
        'Bigware':               { 'cats': [   6 ], 'html': 'bigware(?i)' },
        'blip.tv':               { 'cats': [  14 ], 'html': r'<(param|embed)[^>]+blip\.tv/play(?i)' },
        'Blogger':               { 'cats': [  11 ], 'meta': { r'generator': 'blogger(?i)' }, 'url': r'^(www.)?.+\.blogspot\.com(?i)' },
        'Bugzilla':              { 'cats': [  13 ], 'html': r'<[^>]+(id|title|name)=("|\')bugzilla(?i)' },
        'Burning Board':         { 'cats': [   2 ], 'html': r'<a href=(\'|")[^>]+woltlab\.com.+Burning Board(?i)' },
        'Business Catalyst':     { 'cats': [   1 ], 'script': 'CatalystScripts', 'html': '<!-- BC_OBNW -->' },
        'CakePHP':               { 'cats': [  18 ], 'headers': { 'set-cookie': 'cakephp=' }, 'meta': { 'application-name': 'CakePHP' } },
        'Cargo':                 { 'cats': [   1 ], 'script': r'/cargo\.(?i)', 'html': '<link [^>]+Cargo feed' },
        'CentOS':                { 'cats': [  28 ], 'headers': { 'Server': 'CentOS(?i)', 'X-Powered-By': 'CentOS(?i)' } },
        'Chameleon':             { 'cats': [   1 ], 'meta': { r'generator': 'chameleon\-cms(?i)' } },
        'chartbeat':             { 'cats': [  10 ], 'html': r'function loadChartbeat\(\) {(?i)' },
        'Chamilo':               { 'cats': [  21 ], 'meta': { 'generator': 'Chamilo(?i)' }, 'headers': { 'X-Powered-By': 'Chamilo' } },
        'Cherokee':              { 'cats': [  22 ], 'headers': { 'Server': 'Cherokee(?i)' } },
        'CKEditor':              { 'cats': [  24 ], 'env': '^CKEDITOR$' },
        'ClickHeat':             { 'cats': [  10 ], 'script': r'clickheat.*\.js(?i)', 'env': '^clickHeatBrowser$' },
        'ClickTale':             { 'cats': [  10 ], 'html': r'if\(typeof ClickTale(Tag)*==("|\')function("|\')\)', 'env': '^ClickTale(?i)' },
        'Clicky':                { 'cats': [  10 ], 'script': r'static\.getclicky\.com', 'env': '^clicky$' },
        'CMS Made Simple':       { 'cats': [   1 ], 'meta': { 'generator': 'CMS Made Simple(?i)' } },
        'CO2Stats':              { 'cats': [  10 ], 'html': r'src=("|\')\'http\'://www\.co2stats\.com/propres\.php' },
        'CodeIgniter':           { 'cats': [  18 ], 'headers': { 'Set-Cookie': '(exp_last_activity|exp_tracker|ci_session)' }, 'implies': [ 'PHP' ] },
        'Commerce Server':       { 'cats': [   6 ], 'headers': { 'COMMERCE-SERVER-SOFTWARE': '.+' } },
        'comScore':              { 'cats': [  10 ], 'html': '<i{1}frame[^>]* (id=("|\')comscore("|\')|scr=[^>]+comscore)', 'env': '^_?COMSCORE$(?i)' },
        'Concrete5':             { 'cats': [   1 ], 'meta': { 'generator': 'concrete5(?i)' } },
        'Contao':                { 'cats': [  1,  6 ], 'html': r'(<!--\s+This website is powered by (TYPOlight|Contao)|<link[^>]+(typolight|contao).css)(?i)', 'implies': [ 'PHP' ] },
        'Contens':               { 'cats': [   1 ], 'meta': { 'generator': 'contens(?i)' } },
        'ConversionLab':         { 'cats': [  10 ], 'script': r'conversionlab\.trackset\.com/track/tsend\.js' },
        'Coppermine':            { 'cats': [   7 ], 'html': '<!--Coppermine Photo Gallery(?i)', 'implies': [ 'PHP' ] },
        'Cosmoshop':             { 'cats': [   6 ], 'script': r'cosmoshop_functions\.js' },
        'Cotonti':               { 'cats': [   1 ], 'meta': { 'generator': 'Cotonti(?i)' } },
        'CouchDB':               { 'cats': [  22 ], 'headers': { 'Server': 'CouchDB(?i)' } },
        'cPanel':                { 'cats': [   9 ], 'html': '<!-- cPanel(?i)' },
        'Crazy Egg':             { 'cats': [  10 ], 'script': r'cetrk\.com/pages/scripts/[0-9]+/[0-9]+\.js' },
        'CS Cart':               { 'cats': [   6 ], 'html': r"&nbsp;Powered by (<a href=.'http'://www\.cs\-cart\.com|CS\-Cart)(?i)" },
        'CubeCart':              { 'cats': [   6 ], 'html': r"(Powered by <a href=.'http'://www\.cubecart\.com|<p[^>]+>Powered by CubeCart)(?i)" },
        'cufon':                 { 'cats': [  17 ], 'script': r'cufon\-yui\.js', 'env': '^Cufon$' },
        'd3':                    { 'cats': [  25 ], 'script': r'd3(\.min)?\.js' },
        'Dancer':                { 'cats': [  18 ], 'headers': { 'X-Powered-By': 'Perl Dancer', 'Server': 'Perl Dancer' }, 'implies': [ 'Perl' ] },
        'Danneo CMS':            { 'cats': [   1 ], 'meta': { 'generator': 'Danneo(?i)' } },
        'DataLife Engine':       { 'cats': [   1 ], 'meta': { 'generator': 'DataLife Engine(?i)' } },
        'David Webbox':          { 'cats': [  22 ], 'headers': { 'Server': 'David-WebBox(?i)' } },
        'Debian':                { 'cats': [  28 ], 'headers': { 'Server': 'Debian(?i)', 'X-Powered-By': '(Debian|dotdeb|etch|lenny|squeeze|wheezy)(?i)' } },
        'DedeCMS':               { 'cats': [   1 ], 'env': '^Dede', 'script': 'dedeajax' },
        'Demandware':            { 'cats': [   6 ], 'html': '<[^>]+demandware.edgesuite', 'env': '^dwAnalytics' },
        'DHTMLX':                { 'cats': [  12 ], 'script': r'dhtmlxcommon\.js' },
        'DirectAdmin':           { 'cats': [   9 ], 'html': '<a[^>]+>DirectAdmin</a> Web Control Panel(?i)' },
        'Disqus':                { 'cats': [  15 ], 'script': 'disqus_url', 'html': r'<div[^>]+id=("|\')disqus_thread("|\')', 'env': '^DISQUS(?i)' },
        'Django':                { 'cats': [  18 ] },
        'Django CMS':            { 'cats': [   1 ], 'script': r'media/cms/js/csrf\.js', 'headers': { 'Set-Cookie': 'django' }, 'implies': [ 'Django' ] },
        'dojo':                  { 'cats': [  12 ], 'script': r'dojo(\.xd)?\.js', 'env': '^dojo$' },
        'Dokeos':                { 'cats': [  21 ], 'meta': { 'generator': 'Dokeos(?i)' }, 'html': 'Portal <a[^>]+>Dokeos|@import "[^"]+dokeos_blue(?i)', 'headers': { 'X-Powered-By': 'Dokeos' } },
        'DokuWiki':              { 'cats': [   8 ], 'meta': { 'generator': 'DokuWiki(?i)' } },
        'DotNetNuke':            { 'cats': [   1 ], 'meta': { 'generator': 'DotNetNuke(?i)' }, 'html': r'(<!\-\- by DotNetNuke Corporation|<link[^>]+/portals/_default/[^>]+\.css)(?i)', 'env': '^(DDN|DotNetNuke)(?i)' },
        'DreamWeaver':           { 'cats': [  20 ], 'html': r'(<!\-\-[^>]*(InstanceBeginEditable|Dreamweaver[^>]+target|DWLayoutDefaultTable)|function MM_preloadImages\(\) {)' },
        'Drupal':                { 'cats': [   1 ], 'script': r'drupal\.js', 'html': r"(jQuery\.extend\(Drupal\.settings, \{|Drupal\.extend\(\{ 'settings': \{|<link[^>]+sites/(default|all)/themes/|<style[^>]+sites/(default|all)/(themes|modules)/)(?i)", 'headers': { 'X-Drupal-Cache': '.*', 'X-Generator': 'Drupal', 'Expires': '19 Nov 1978' }, 'env': '^Drupal$', 'implies': [ 'PHP' ] },
        'Drupal Commerce':       { 'cats': [   6 ], 'html': 'id="block[_-]commerce[_-]cart[_-]cart|class="commerce[_-]product[_-]field(?i)', 'implies': [ 'PHP' ] },
        'Dynamicweb':            { 'cats': [   1 ], 'meta': { 'generator': 'Dynamicweb(?i)' } },
        'e107':                  { 'cats': [   1 ], 'script': r'e107\.js' },
        'Ecodoo':                { 'cats': [   6 ], 'script': r'addons/lytebox/lytebox\.js' },
        'Exhibit':               { 'cats': [  25 ], 'script': r'exhibit.*\.js', 'env': '^Exhibit$' },
        'ExtJS':                 { 'cats': [  12 ], 'script': r'ext\-base\.js', 'env': '^Ext$' },
        'ExpressionEngine':      { 'cats': [   1 ], 'headers': { 'Set-Cookie': '(exp_last_activity|exp_tracker)' } },
        'eZ Publish':            { 'cats': [   1 ], 'meta': { 'generator': 'eZ Publish(?i)' } },
        'FAST Search for SharePoint': {'cats': [ 29], 'url': r'Pages/SearchResults\.aspx\?k\=', 'implies': [ 'Microsoft ASP.NET' ] },
        'FAST ESP':              { 'cats': [  29 ], 'html': r'fastsearch|searchProfile\=|searchCategory\=(?i)', 'url': 'esppublished|searchProfile\=|searchCategory\=(?i)' },
        'Fact Finder':           { 'cats': [  29 ], 'html': r'/images/fact-finder\.gif|ViewParametricSearch|factfinder|Suggest\.ff(?i)', 'url': 'ViewParametricSearch|factfinder|ffsuggest(?i)' },
        'FlexCMP':               { 'cats': [   1 ], 'meta': { 'generator': 'FlexCMP' }, 'headers': { 'X-Powered-By': 'FlexCMP' } },
        'FluxBB':                { 'cats': [   2 ], 'html': r'Powered by (<strong>)?<a href=("|\')[^>]+fluxbb(?i)' },
        'Flyspray':              { 'cats': [  13 ], 'html': r'(<a[^>]+>Powered by Flyspray|<map id=("|\')projectsearchform)' },
        'FreeBSD':               { 'cats': [  28 ], 'headers': { 'Server': 'FreeBSD(?i)' } },
        'FWP':                   { 'cats': [   6 ], 'meta': {'generator': 'FWP Shop' } },
        'FrontPage':             { 'cats': [  20 ], 'meta': { 'generator': 'Microsoft FrontPage' }, 'html': r"<html[^>]+'urn':schemas\-microsoft\-'com':'office':office(?i)" },
        'Gallery':               { 'cats': [   7 ], 'env': 'galleryAuthToken', 'html': '<div id="gsNavBar" class="gcBorder1">' },
        'Gambio':                { 'cats': [   6 ], 'html': r'brought to you by XT-Commerce|[Gg]ambio|content\.php\?coID=\d'},
        'Gauges':                { 'cats': [  10 ], 'html': r"t\.src = '//secure\.gaug\.es/track\.js", 'env': '^_gauges$' },
        'Get Satisfaction':      { 'cats': [  13 ], 'html': r'var feedback_widget = new GSFN\.feedback_widget\(feedback_widget_options\)' },
        'Google Analytics':      { 'cats': [  10 ], 'script': r'(\.google\-analytics\.com/ga\.js|google-analytics\.com/urchin\.js)', 'env': '^gaGlobal$' },
        'Google App Engine':     { 'cats': [  22 ], 'headers': { 'Server': 'Google Frontend(?i)' } },
        'Google Font API':       { 'cats': [  17 ], 'script': 'googleapis.com/.+webfont', 'html': r'<link[^>]* href=("|\')\'http\'://fonts\.googleapis\.com', 'env': '^WebFont' },
        'Google Friend Connect': { 'cats': [   5 ], 'script': 'google.com/friendconnect' },
        'Google Maps':           { 'cats': [   5 ], 'script': r'(maps\.google\.com/maps\?file=api|maps\.google\.com/maps/api/staticmap)' },
        'Google Sites':          { 'cats': [   1 ], 'url': 'sites.google.com' },
        'GoStats':               { 'cats': [  10 ], 'env': '^_go(stats|_track)(?i)' },
        'Graffiti CMS':          { 'cats': [   1 ], 'meta': { 'generator': 'Graffiti CMS(?i)' } },
        'Gravatar':              { 'cats': [  19 ], 'env': '^Gravatar$' },
        'Gravity Insights':      { 'cats': [  10 ], 'html': r"gravityInsightsParams\.site_guid = '", 'env': '^GravityInsights$' },
        'Handlebars':            { 'cats': [  12 ], 'env': '^Handlebars$' },
        'Hiawatha':              { 'cats': [  22 ], 'headers': { 'Server': 'Hiawatha(?i)' } },
        'Highcharts':            { 'cats': [  25 ], 'script': r'highcharts.*\.js', 'env': '^Highcharts$' },
        'Hotaru CMS':            { 'cats': [   1 ], 'meta': { 'generator': 'Hotaru CMS(?i)' } },
        'Hybris':                { 'cats': [   6 ], 'html': '/sys_master/|/hybr/', 'header': { 'Set-Cookie': '_hybris' }, 'implies': [ 'Java' ] },
        'IIS':                   { 'cats': [  22 ], 'headers': { 'Server': 'IIS(?i)' }, 'implies': [ 'Windows Server' ] },
        'Indexhibit':            { 'cats': [   1 ], 'html': '<link [^>]+ndxz-studio(?i)' },
        'InstantCMS':            { 'cats': [   1 ], 'meta': { 'generator': 'InstantCMS(?i)' } },
        'Intershop':             { 'cats': [   6 ], 'url': 'is-bin|INTERSHOP(?i)', 'script': 'is-bin|INTERSHOP(?i)' },
        'IPB':                   { 'cats': [   2 ], 'script': 'jscripts/ips_', 'env': '^IPBoard', 'html': r'<link[^>]+ipb_[^>]+\.css' },
        'iWeb':                  { 'cats': [  20 ], 'meta': { 'generator': 'iWeb(?i)' } },
        'Jalios':                { 'cats': [   1 ], 'meta': { 'generator': 'Jalios(?i)' } },
        'Java':                  { 'cats': [  27 ] },
        'Javascript Infovis Toolkit': { 'cats': [  25 ], 'script': r'jit.*\.js', 'env': r'^\$jit$' },
        'Jo':                    { 'cats': [  26,  12 ], 'env': '^jo(Cache|DOM|Event)$' },
        'Joomla':                { 'cats': [   1 ], 'meta': { 'generator': 'Joomla(?i)' }, 'html': r'(<!\-\- JoomlaWorks "K2"|<[^>]+(feed|components)/com_)(?i)', 'headers': { 'X-Content-Encoded-By': 'Joomla' }, 'env': '^(jcomments)$(?i)' },
        'jqPlot':                { 'cats': [  25 ], 'script': r'jqplot.*\.js', 'env': '^jQuery.jqplot$' },
        'jQTouch':               { 'cats': [  26 ], 'script': r'jqtouch.*\.js(?i)', 'env':'^jQT$' },
        'jQuery UI':             { 'cats': [  12 ], 'script': r'jquery\-ui.*\.js', 'implies': [ 'jQuery' ] },
        'jQuery':                { 'cats': [  12 ], 'script': 'jquery.*.js', 'env': '^jQuery$' },
        'jQuery Mobile':         { 'cats': [  26 ], 'script': r'jquery\.mobile.*\.js(?i)' },
        'jQuery Sparklines':     { 'cats': [  25 ], 'script': r'jquery\.sparkline.*\.js(?i)' },
        'JS Charts':             { 'cats': [  25 ], 'script': r'jscharts.*\.js(?i)', 'env': '^JSChart$' },
        'JTL Shop':              { 'cats': [   6 ], 'html': r'(<input[^>]+name=(\'|")JTLSHOP|<a href=(\'|")jtl\.php)(?i)' },
        'K2':                    { 'cats': [  19 ], 'html': r'<!\-\- JoomlaWorks "K2"', 'env': '^K2RatingURL$', 'implies': [ 'Joomla' ] },
        'Kampyle':               { 'cats': [  10 ], 'script': r'cf\.kampyle\.com/k_button\.js' },
        'Kentico CMS':           { 'cats': [   1 ], 'meta': { 'generator': r'Kentico CMS(?i)' } },
        'Koego':                 { 'cats': [  10 ], 'script': r'tracking\.koego\.com/end/ego\.js' },
        'Kohana':                { 'cats': [  18 ], 'headers': { 'Set-Cookie': 'kohanasession(?i)', 'X-Powered-By': 'Kohana' }, 'implies': [ 'PHP' ] },
        'Kolibri CMS':           { 'cats': [   1 ], 'meta': { 'generator': 'Kolibri(?i)' } },
        'Koobi':                 { 'cats': [   1 ], 'meta': { 'generator': 'Koobi(?i)' } },
        'lighttpd':              { 'cats': [  22 ], 'headers': { 'Server': 'lighttpd(?i)' } },
        'LiveJournal':           { 'cats': [  11 ], 'url': r'^(www.)?.+\.livejournal\.com(?i)' },
        'Liferay':               { 'cats': [  1  ], 'env': '^Liferay$', 'headers': { 'Liferay-Portal': '.*(?i)' } },
        'Lotus Domino':          { 'cats': [  22 ], 'headers': { 'Server': r'Lotus\-Domino(?i)' } },
        'Magento':               { 'cats': [   6 ], 'script': '/(js/mage|skin/frontend/(default|enterprise))/', 'env': '^(Mage|VarienForm)$', 'implies': [ 'PHP '] },
        'Mambo':                 { 'cats': [   1 ], 'meta': { 'generator': 'Mambo(?i)' } },
        'MantisBT':              { 'cats': [  13 ], 'html': r'<img[^>]+ alt=("|\')Powered by Mantis Bugtracker(?i)' },
        'MaxSite CMS':           { 'cats': [   1 ], 'meta': { 'generator': 'MaxSite CMS(?i)' } },
        'MediaWiki':             { 'cats': [   8 ], 'meta': { 'generator': 'MediaWiki(?i)' }, 'html': r'(<a[^>]+>Powered by MediaWiki</a>|<[^>]+id=("|\')t\-specialpages)(?i)' },
        'Meebo':                 { 'cats': [   5 ], 'html': r'(<iframe id=("|\')meebo\-iframe("|\')|Meebo\(\'domReady\'\))' },
        'Microsoft ASP.NET':     { 'cats': [  18 ], 'html': r'<input[^>]+name=("|\')__VIEWSTATE', 'headers': { 'X-Powered-By': 'ASP\.NET', 'X-AspNet-Version': '.+' }, 'implies': [ 'Windows Server' ] },
        'Microsoft SharePoint':  { 'cats': [   1 ], 'meta': { 'generator': 'Microsoft SharePoint(?i)' }, 'headers': { 'MicrosoftSharePointTeamServices': '.*', 'X-SharePointHealthScore': '.*', 'SPRequestGuid': '.*', 'SharePointHealthScore': '.*' } },
        'MiniBB':                { 'cats': [   2 ], 'html': r'<a href=("|\')[^>]+minibb.+\s+<!--End of copyright link(?i)' },
        'Mint':                  { 'cats': [  10 ], 'script': r'mint/\?js', 'env': '^Mint$' },
        'Mixpanel':              { 'cats': [  10 ], 'script': r'api\.mixpanel\.com/track' },
        'MochiKit':              { 'cats': [  12 ], 'script': r'MochiKit\.js', 'env': '^MochiKit$' },
        'Modernizr':             { 'cats': [  12 ], 'script': r'modernizr.*\.js', 'env': '^Modernizr$' },
        'MODx':                  { 'cats': [   1 ], 'html': r'(<a[^>]+>Powered by MODx</a>|var el= \$\(\'modxhost\'\);|<script type=("|\')text/javascript("|\')>var MODX_MEDIA_PATH = "media";)|<(link|script)[^>]+assets/snippets/(?i)' },
        'Mojolicious':           { 'cats': [  18 ], 'headers': { 'x-powered-by': 'mojolicious' }, 'implies': [ 'PERL' ] },
        'Mollom':                { 'cats': [  16 ], 'script': r'mollom\.js', 'html': '<img[^>]+/.mollom/.com(?i)' },
        'Mondo Media':           { 'cats': [   6 ], 'meta': { 'generator': 'Mondo Shop' } },
        'Mongrel':               { 'cats': [  22 ], 'headers': { 'Server': 'Mongrel' }, 'implies': [ 'Ruby' ] },
        'Moodle':                { 'cats': [  21 ], 'html': r'(var moodleConfigFn = function\(me\)|<img[^>]+moodlelogo)(?i)', 'implies': [ 'PHP' ] },
        'Moogo':                 { 'cats': [   1 ], 'script': 'kotisivukone.js' },
        'MooTools':              { 'cats': [  12 ], 'script': r'mootools.*\.js', 'env': '^MooTools$' },
        'Movable Type':          { 'cats': [   1 ], 'meta': { 'generator': 'Movable Type(?i)' } },
        'Mustache':              { 'cats': [  12 ], 'env': '^Mustache$' },
        'MyBB':                  { 'cats': [   2 ], 'html': r'(<script [^>]+\s+<!--\s+lang\.no_new_posts|<a[^>]* title=("|\')Powered By MyBB)(?i)', 'env': '^MyBB' },
        'MyBlogLog':             { 'cats': [   5 ], 'script': r'pub\.mybloglog\.com(?i)' },
        'Mynetcap':              { 'cats': [   1 ], 'meta': { 'generator': 'Mynetcap(?i)' } },
        'Nedstat':               { 'cats': [  10 ], 'html': r'sitestat\(("|\')\'http\'://nl\.sitestat\.com' },
        'Netmonitor':            { 'cats': [  10 ], 'script': 'netmonitor\.fi/nmtracker\.js', 'env': '^netmonitor' },
        'Nginx':                 { 'cats': [  22 ], 'headers': { 'Server': 'nginx(?i)' } },
        'NOIX':                  { 'cats': [  19 ], 'html': r'<[^>]+(src|href)=[^>]*(/media/noix)|<!\-\- NOIX(?i)' },
        'nopCommerce':           { 'cats': [   6 ], 'html': r"(<!\-\-Powered by nopCommerce|Powered 'by': <a[^>]+nopcommerce)(?i)" },
        'OneStat':               { 'cats': [  10 ], 'html': r'var p=("|\')http("|\')\+\(d\.URL\.indexOf\(\'\'https\':\'\)==0\?\'s\':\'\'\)\+("|\')://stat\.onestat\.com/stat\.aspx\?tagver(?i)' },
        'OpenCart':              { 'cats': [   6 ], 'html': r'(Powered By <a href=("|\')[^>]+OpenCart|route = getURLVar\(("|\')route)(?i)' },
        'openEngine':            { 'cats': [   1 ], 'html': '<meta[^>]+openEngine(?i)' },
        'OpenGSE':               { 'cats': [  22 ], 'headers': { 'Server': 'GSE(?i)' } },
        'OpenLayers':            { 'cats': [   5 ], 'script': 'openlayers', 'env':'^OpenLayers$' },
        'OpenNemas':             { 'cats': [   1 ], 'headers': { 'X-Powered-By': 'OpenNemas' } },
        'Open Web Analytics':    { 'cats': [  10 ], 'html': '<!-- (Start|End) Open Web Analytics Tracker -->', 'env': '^_?owa_(?i)' },
        'Optimizely':            { 'cats': [  10 ], 'env': '^optimizely' },
        'Oracle Recommendations On Demand': { 'cats': [  10 ], 'script': r'atgsvcs.+atgsvcs\.js' },
        'osCommerce':            { 'cats': [   6 ], 'html': '<a[^>]*osCsid(?i)' },
        'osCSS':                 { 'cats': [   6 ], 'html': r'<body onload=("|\')window\.defaultStatus=\'oscss templates\';("|\')(?i)' },
        'OXID eShop':            { 'cats': [   6 ], 'html': '<!--.*OXID eShop', 'env': '^ox(TopMenu|ModalPopup|LoginBox|InputValidator)' },
        'PANSITE':               { 'cats': [   1 ], 'meta': { 'generator': 'PANSITE(?i)' } },
        'papaya CMS':            { 'cats': [   1 ], 'html': '<link[^>]*/papaya-themes/(?i)' },
        'Parse.ly':              { 'cats': [  10 ], 'env': '^PARSELY$' },
        'Perl':                  { 'cats': [  27 ] },
        'PHP':                   { 'cats': [  27 ], 'headers': { 'Server': 'php(?i)', 'X-Powered-By': 'php(?i)', 'Set-Cookie': 'PHPSESSID' }, 'url': '\.php$' },
        'Phpcms':                { 'cats': [   1 ], 'env': '^phpcms' },
        'PHP-Fusion':            { 'cats': [   1 ], 'html': r'Powered by <a href=("|\')[^>]+php-fusion(?i)' },
        'PHP-Nuke':              { 'cats': [   2 ], 'meta': { 'generator': 'PHP-Nuke(?i)' }, 'html': r'<[^>]+Powered by PHP\-Nuke(?i)' },
        'phpBB':                 { 'cats': [   2 ], 'meta': { 'copyright': 'phpBB Group' }, 'html': '(Powered by <a[^>]+phpbb|<a[^>]+phpbb[^>]+class=.copyright|\tphpBB style name|<[^>]+styles/(sub|pro)silver/theme|<img[^>]+i_icon_mini|<table class="forumline)(?i)', 'env': '^(style_cookie_settings|phpbb_)', 'headers': { 'Set-Cookie': '^phpbb' }, 'implies': [ 'PHP' ] },
        'phpDocumentor':         { 'cats': [   4 ], 'html': '<!-- Generated by phpDocumentor', 'implies': [ 'PHP' ] },
        'phpMyAdmin':            { 'cats': [   3 ], 'html': r"(var pma_absolute_uri = '|PMA_sendHeaderLocation\(|<title>phpMyAdmin</title>)(?i)", 'implies': [ 'PHP' ] },
        'phpPgAdmin':            { 'cats': [   3 ], 'html': r'(<title>phpPgAdmin</title>|<span class=("|\')appname("|\')>phpPgAdmin)(?i)' },
        'Piwik':                 { 'cats': [  10 ], 'html': r'var piwikTracker = Piwik\.getTracker\((?i)', 'env': '^Piwik$' },
        'Plentymarkets':         { 'cats': [   6 ], 'meta': { 'generator': r'www\.plentyMarkets\.(?i)' } },
        'Plesk':                 { 'cats': [   9 ], 'script': r'common\.js\?plesk(?i)' },
        'Plone':                 { 'cats': [   1 ], 'meta': { 'generator': 'Plone(?i)' }, 'implies': [ 'Python' ] },
        'Plura':                 { 'cats': [  19 ], 'html': r'<iframe src="\'http\'://pluraserver\.com' },
        'posterous':             { 'cats': [   1,  11 ], 'html': '<div class=("|\')posterous(?i)', 'env': '^Posterous(?i)' },
        'Powergap':              { 'cats': [   6 ], 'html': r'(s\d\d)\.php\?shopid=\x01' },
        'Prestashop':            { 'cats': [   6 ], 'meta': { 'generator': 'PrestaShop(?i)' }, 'html': r'Powered by <a href=("|\')[^>]+PrestaShop(?i)' },
        'Prototype':             { 'cats': [  12 ], 'script': r'(prototype|protoaculous)\.js', 'env': '^Prototype$' },
        'Protovis':              { 'cats': [  25 ], 'script': r'protovis.*\.js', 'env': '^protovis$' },
        'punBB':                 { 'cats': [   2 ], 'html': r'Powered by <a href=("|\')[^>]+punbb(?i)' },
        'Python':                { 'cats': [  27 ] },
        'Quantcast':             { 'cats': [  10 ], 'script': r'edge\.quantserve\.com/quant\.js', 'env': '^quantserve$' },
        'Quick.Cart':            { 'cats': [   6 ], 'html': r'<a href="[^>]+opensolution\.org/">Powered by(?i)' },
        'ReallyCMS':             { 'cats': [   1 ], 'meta': { 'generator': 'ReallyCMS' } },
        'Red Hat':               { 'cats': [  28 ], 'headers': { 'Server': 'Red Hat(?i)', 'X-Powered-By': 'Red Hat(?i)' } },
        'Raphael':               { 'cats': [  25 ], 'script': r'raphael.*\.js', 'env': '^Raphael$' },
        'reCAPTCHA':             { 'cats': [  16 ], 'script': r'(api\-secure\.recaptcha\.net|recaptcha_ajax\.js)', 'html': r'<div[^>]+id=("|\')recaptcha_image', 'env': '^Recaptcha$' },
        'Reddit':                { 'cats': [   2 ], 'html': '(<script[^>]+>var reddit = {|<a[^>]+Powered by Reddit|powered by <a[^>]+>reddit<)(?i)', 'url': r'^(www\.)?reddit\.com', 'env': '^reddit$', 'implies': [ 'Python' ] },
        'Redmine':               { 'cats': [  13 ], 'meta': { 'description': 'Redmine(?i)' }, 'html': r'Powered by <a href=("|\')[^>]+Redmine(?i)', 'implies': [ 'Ruby' ] },
        'Reinvigorate':          { 'cats': [  10 ], 'html': r'reinvigorate\.track\("' },
        'RequireJS':             { 'cats': [  12 ], 'script': r'require.*\.js' , 'env': '^requirejs$'},
        'Ruby':                  { 'cats': [  27 ], 'headers': { 'Server': '(Mongrel|WEBrick|Ruby|mod_rails|mod_rack|Phusion.Passenger)(?i)', 'X-Powered-By': '(mod_rails|mod_rack|Phusion.Passenger)(?i)' } },
        'S.Builder':             { 'cats': [   1 ], 'meta': { 'generator': r'S\.Builder(?i)' } },
        's9y':                   { 'cats': [   1 ], 'meta': { 'generator': 'Serendipity(?i)', 'Powered-By': 'Serendipity(?i)' } },
        'script.aculo.us':       { 'cats': [  12 ], 'script': r'(scriptaculous|protoaculous)\.js', 'env': '^Scriptaculous$' },
        'Sencha Touch':          { 'cats': [  26,  12], 'script': r'sencha\-touch.*\.js' },
        'Seoshop':               { 'cats': [   6 ], 'html': r"'http'://www\.getseoshop\.com" },
        'ShareThis':             { 'cats': [   5 ], 'script': r'w\.sharethis\.com/', 'env': '^SHARETHIS$' },
        'Shopify':               { 'cats': [   6 ], 'html': r'<link[^>]+=cdn\.shopify\.com', 'env': '^Shopify$' },
        'sIFR':                  { 'cats': [  17 ], 'script': r'sifr\.js' },
        'Site Meter':            { 'cats': [  10 ], 'script': r'sitemeter.com/js/counter\.js\?site=' },
        'SiteCatalyst':          { 'cats': [  10 ], 'html': r'var s_code=s\.t\(\);if\(s_code\)document\.write\(s_code\)(?i)', 'env': '^s_account$' },
        'SiteEdit':              { 'cats': [   1 ], 'meta': { 'generator': 'SiteEdit(?i)' } },
        'Smartstore':            { 'cats': [   6 ], 'script': r'smjslib\.js' },
        'SMF':                   { 'cats': [   2 ], 'html': r'<script [^>]+\s+var smf_(?i)', 'env': '^smf_' },
        'sNews':                 { 'cats': [   1 ], 'meta': { 'generator': 'sNews' } },
        'Snoobi':                { 'cats': [  10 ], 'script': r'snoobi\.com/snoop\.php' },
        'SOBI 2':                { 'cats': [  19 ], 'html': r'(<!\-\- start of Sigsiu Online Business Index|<div[^>]* class=("|\')sobi2)(?i)' },
        'SoundManager':          { 'cats': [  12 ], 'env': '^(SoundManager|BaconPlayer)$' },
        'Sphinx':                { 'cats': [   4 ], 'html': r'<a href="http\://sphinx.pocoo.org/">Sphinx</a>'},
        'SPIP':                  { 'cats': [   1 ], 'meta': { 'generator': 'SPIP(?i)' }, 'headers': { 'X-Spip-Cache': '.*' } },
        'SQL Buddy':             { 'cats': [   3 ], 'html': r'(<title>SQL Buddy</title>|<[^>]+onclick=("|\')sideMainClick\(("|\')home\.php)(?i)' },
        'Squarespace':           { 'cats': [   1 ], 'html': r'Squarespace\.Constants\.CURRENT_MODULE_ID(?i)' },
        'Squiz Matrix':          { 'cats': [   1 ], 'meta': { 'generator': 'Squiz Matrix' }, 'html': '  Running (MySource|Squiz) Matrix(?i)', 'X-Powered-By': 'Squiz Matrix' },
        'StatCounter':           { 'cats': [  10 ], 'script': r'statcounter\.com/counter/counter' },
        'Store Systems':         { 'cats': [   6 ], 'html': r'Shopsystem von <a href="\'http\'://www\.store-systems\.de"|\.mws_boxTop' },
        'SWFObject':             { 'cats': [  19 ], 'script': r'swfobject.*\.js(?i)', 'env': '^SWFObject$' },
        'swift.engine':          { 'cats': [   1 ], 'headers': { 'X-Powered-By': r'swift\.engine' } },
        'Swiftlet':              { 'cats': [  18 ], 'meta': { 'generator': 'Swiftlet(?i)' }, 'html': r'Powered by <a href=("|\')[^>]+Swiftlet(?i)', 'headers': { 'X-Swiftlet-Cache': '.*', 'X-Powered-By': 'Swiftlet', 'X-Generator': 'Swiftlet' }, 'implies': [ 'PHP' ] },
        'Textpattern CMS':       { 'cats': [   1 ], 'meta': { 'generator': 'Textpattern(?i)' } },
        'Tiki Wiki CMS Groupware': { 'cats': [  1,  2,  8,  11,  13 ], 'script': '(/|_)tiki', 'meta': { 'generator': '^Tiki(?i)' } },
        'Timeplot':              { 'cats': [  25 ], 'script': r'timeplot.*\.js', 'env': '^Timeplot$' },
        'TinyMCE':               { 'cats': [  24 ], 'env': '^tinyMCE$' },
        'TomatoCart':            { 'cats': [   6 ], 'meta': { 'generator': 'TomatoCart(?i)' } },
        'Trac':                  { 'cats': [  13 ], 'html': r'(<a id=("|\')tracpowered)(?i)', 'implies': [ 'Python' ] },
        'Tumblr':                { 'cats': [  11 ], 'html': r'<iframe src=("|\')\'http\'://www\.tumblr\.com(?i)', 'url': r'^(www.)?.+\.tumblr\.com(?i)', 'headers': { 'X-Tumblr-Usec': '.*' } },
        'Twilight CMS':          { 'cats': [   1 ], 'headers': { 'X-Powered-CMS': 'Twilight CMS' } },
        'Twitter Bootstrap':     { 'cats': [  18 ], 'script': r'twitter\.github\.com/bootstrap', 'html': '<link[^>]+bootstrap[^>]+css', 'env': '^Twipsy$' },
        'Typekit':               { 'cats': [  17 ], 'script': 'use.typekit.com', 'env': '^Typekit$' },
        'TypePad':               { 'cats': [  11 ], 'meta': { 'generator': 'typepad(?i)' }, 'url': r'^(www.)?.+\.typepad\.com(?i)' },
        'TYPO3':                 { 'cats': [   1 ], 'headers': { 'Set-Cookie': 'fe_typo_user' }, 'meta': { 'generator': 'TYPO3(?i)' }, 'html': '(<(script[^>]* src|link[^>]* href)=[^>]*fileadmin|<!--TYPO3SEARCH)(?i)', 'url': '/typo3(?i)' },
        'Ubercart':              { 'cats': [   6 ], 'script': r'uc_cart/uc_cart_block\.js' },
        'Ubuntu':                { 'cats': [  28 ], 'headers': { 'Server': 'Ubuntu(?i)', 'X-Powered-By': 'Ubuntu(?i)' } },
        'Umbraco':               { 'cats': [   1 ], 'meta': { 'generator': 'umbraco(?i)' }, 'headers': { 'X-Umbraco-Version': '.+' }, 'html': 'powered by <a href=[^>]+umbraco(?i)', 'implies': [ 'Microsoft ASP.NET' ] },
        'Underscore.js':         { 'cats': [  12 ], 'script': r'underscore.*\.js' },
        'UNIX':                  { 'cats': [  28 ], 'headers': { 'Server': 'Unix(?i)' } },
        'UserRules':             { 'cats': [  13 ], 'html': 'var _usrp =' , 'env': r'^\_usrp$' },
        'UserVoice':             { 'cats': [  13 ], 'env': '^UserVoice$' },
        'Vanilla':               { 'cats': [   2 ], 'html': r'<body id=("|\')(DiscussionsPage|vanilla)(?i)', 'headers': { 'X-Powered-By': 'Vanilla' } },
        'Varnish':               { 'cats': [  22 ], 'headers': { 'X-Varnish': '.+', 'X-Varnish-Age': '.+', 'X-Varnish-Cache': '.+', 'X-Varnish-Action': '.+', 'X-Varnish-Hostname': '.+', 'Via': 'Varnish(?i)' } },
        'vBulletin':             { 'cats': [   2 ], 'meta': { 'generator': 'vBulletin(?i)' }, 'env': '^(vBulletin|vB_)' },
        'viennaCMS':             { 'cats': [   1 ], 'html': r'powered by <a href=("|\')[^>]+viennacms(?i)' },
        'Vignette':              { 'cats': [   1 ], 'html': r'<[^>]+?=("|\')(vgn\-ext|vgnext)(?i)' },
        'Vimeo':                 { 'cats': [  14 ], 'html': r'<(param|embed)[^>]+vimeo\.com/moogaloop(?i)' },
        'VirtueMart':            { 'cats': [   6 ], 'html': r'<div id=("|\')vmMainPage' },
        'VisualPath':            { 'cats': [  10 ], 'script': r'visualpath[^/]*\.trackset\.it/[^/]+/track/include\.js' },
        'VIVVO':                 { 'cats': [   1 ], 'headers': { 'Set-Cookie': 'VivvoSessionId', 'env': '^vivvo(?i)' } },
        'Vox':                   { 'cats': [  11 ], 'url': r'^(www.)?.+\.vox\.com(?i)' },
        'VP-ASP':                { 'cats': [   6 ], 'script': r'vs350\.js', 'html': r'<a[^>]+>Powered By VP\-ASP Shopping Cart</a>', 'implies': [ 'Microsoft ASP.NET' ] },
        'W3Counter':             { 'cats': [  10 ], 'script': r'w3counter\.com/tracker\.js' },
        'Web Optimizer':         { 'cats': [  10 ], 'html': r'<title [^>]*lang=("|\')wo("|\')>' },
        'Websale':               { 'cats': [   6 ], 'url': '/websale7/' },
        'webEdition':            { 'cats': [   1 ], 'meta': { 'generator': 'webEdition(?i)', 'DC.title': 'webEdition(?i)' } },
        'WebGUI':                { 'cats': [   1 ], 'meta': { 'generator': 'WebGUI(?i)' } },
        'WebPublisher':          { 'cats': [   1 ], 'meta': { 'generator': r'WEB\|Publisher(?i)' } },
        'WebsiteBaker':          { 'cats': [   1 ], 'meta': { 'generator': 'WebsiteBaker(?i)' } },
        'Webtrekk':              { 'cats': [  10 ], 'html': 'var webtrekk = new Object' },
        'Webtrends':             { 'cats': [  10 ], 'html': r'<img[^>]+id=("|\')DCSIMG("|\')[^>]+webtrends(?i)', 'env': '^(WTOptimize|WebTrends)(?i)' },
        'Weebly':                { 'cats': [   1 ], 'html': r'<[^>]+class=("|\')weebly(?i)' },
        'WikkaWiki':             { 'cats': [   8 ], 'meta': { 'generator': 'WikkaWiki' }, 'html': r'Powered by <a href=("|\')[^>]+WikkaWiki(?i)' },
        'Windows Server':        { 'cats': [  28 ] },
        'wink':                  { 'cats': [  26,  12 ], 'script': r'(\_base/js/base|wink).*\.js(?i)', 'env': '^wink$' },
        'Wolf CMS':              { 'cats': [   1 ], 'html': r'<a href=("|\')[^>]+wolfcms.org.+Wolf CMS.+inside(?i)' },
        'Woopra':                { 'cats': [  10 ], 'script': r'static\.woopra\.com' },
        'WordPress':             { 'cats': [   1,  11 ], 'meta': { 'generator': 'WordPress(?i)' }, 'html': r'<link rel=("|\')stylesheet("|\') [^>]+wp-content(?i)', 'env': '^wp_username$', 'implies': [ 'PHP' ] },
        'xajax':                 { 'cats': [  12 ], 'script': r'xajax_core.*\.js(?i)' },
        'Xanario':               { 'cats': [   6 ], 'meta': { 'generator': 'xanario shopsoftware(?i)' } },
        'XenForo':               { 'cats': [   2 ], 'html': r"(jQuery\.extend\(true, XenForo|Forum software by XenForo&trade;|<!\-\-'XF':branding)" },
        'XiTi':                  { 'cats': [  10 ], 'html': r'<[^>]+src=("|\')[^>]+xiti.com/hit.xiti(?i)', 'env': '^Xt_' },
        'XMB':                   { 'cats': [   2 ], 'html': '<!-- Powered by XMB(?i)' },
        'xui':                   { 'cats': [  26,  12 ], r'script': '[^a-zA-Z]xui.*\.js(?i)', 'env': '^xui$' },
        'XOOPS':                 { 'cats': [   1 ], 'meta': { 'generator': 'XOOPS(?i)' } },
        'xtCommerce':            { 'cats': [   6 ], 'meta': { 'generator': "'xt':Commerce" }, 'html': r'<div class=("|\')copyright("|\')>.+<a[^>]+>\'xt\':Commerce(?i)' },
        'YaBB':                  { 'cats': [   2 ], 'html': r'Powered by <a href=("|\')[^>]+yabbforum(?i)' },
        'Yahoo! Web Analytics':  { 'cats': [  10 ], 'script': r'd\.yimg\.com/mi/ywa\.js' },
        'Yandex.Metrika':        { 'cats': [  10 ], 'script': r'mc\.yandex\.ru/metrika/watch\.js' },
        'YouTube':               { 'cats': [  14 ], 'html': r'<(param|embed|iframe)[^>]+youtube(-nocookie)?\.com/(v|embed)(?i)' },
        'YUI Doc':               { 'cats': [   4 ], 'html': r'<html[^>]* yuilibrary\.com/rdf/[0-9.]+/yui\.rdf(?i)' },
        'YUI':                   { 'cats': [  12 ], 'script': r'/yui/|yui\.yahooapis\.com', 'env': '^YAHOO$' },
        'Zen Cart':              { 'cats': [   6 ], 'meta': { 'generator': 'Zen Cart(?i)' } },
        'Zend':                  { 'cats': [  22 ], 'headers': { 'X-Powered-By': 'Zend' } },
        'Zepto':                 { 'cats': [  12 ], 'script': 'zepto.*.js', 'env': '^Zepto$' }
    }

    def analyze(self, url):

        r = urlopen(url)
        headers = r.headers
        data = r.read()
        results = {}

        for app in self.apps:
            for type in self.apps[app]:
                if app in results:
                    break

                if type == 'url':
                    if search(self.apps[app][type], url) is not None:
                        self._report(results, app)

                elif type == 'html':
                    if not data:
                        continue
                    if search(self.apps[app][type], data) is not None:
                        self._report(results, app)

                elif type == 'script':
                    if not data:
                        continue
                    for s in findall(r'<script[^>]+src=["\']([^"\']+)(?i)', data):
                        if search(self.apps[app][type], s) is not None:
                            self._report(results, app)
                            break

                elif type == 'meta':
                    if not data:
                        continue
                    for m in findall(r'<meta[^>]+>(?i)', data):
                        for meta in self.apps[app][type]:
                            if search('name=["\']%s["\'](?i)' % meta, m) is not None:
                                content = findall(r'content=["\']([^"\']+)["\'](?i)', m)
                                if content and search(self.apps[app][type][meta], content[0]) is not None:
                                    self._report(results, app)

                elif type == 'headers':
                    if not headers:
                        continue

                    for header in self.apps[app][type]:
                        if header in headers and search(self.apps[app][type][header], headers[header]) is not None:
                            self._report(results, app)
                            break
                elif type == 'env':
                    # No support for JSObject at this moment in python
                    pass
        return results

    def _report(self, report, app):
        if app in report:
            return
        report[app] = [ self.categories[i]['name'] for i in self.apps[app]['cats'] ]
        if 'implies' in self.apps[app]:
            for a in self.apps[app]['implies']:
                if a not in report:
                    self._report(report, a)
########NEW FILE########
__FILENAME__ = wikipedia
#!/usr/bin/env python

from json.decoder import JSONDecoder
from httplib import HTTPConnection
from urllib import urlencode

from canari.config import config

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, Sploitego Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


class WikipediaError(Exception):
    pass


def usercontribs(**kwargs):
    """Get all edits by a user

    This module requires read rights
    Parameters:
    uclimit             - The maximum number of contributions to return
                        No more than 500 (5000 for bots) allowed
                        Default: 10
    ucstart             - The start timestamp to return from
    ucend               - The end timestamp to return to
    uccontinue          - When more results are available, use this to continue
    ucuser              - The users to retrieve contributions for
    ucuserprefix        - Retrieve contibutions for all users whose names begin with this value. Overrides ucuser
    ucdir               - In which direction to enumerate
                         newer          - List oldest first. Note: ucstart has to be before ucend.
                         older          - List newest first (default). Note: ucstart has to be later than ucend.
                        One value: newer, older
                        Default: older
    ucnamespace         - Only list contributions in these namespaces
                        Values (separate with '|'): 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 100, 101, 108, 109
                        Maximum number of values 50 (500 for bots)
    ucprop              - Include additional pieces of information
                         ids            - Adds the page ID and revision ID
                         title          - Adds the title and namespace ID of the page
                         timestamp      - Adds the timestamp of the edit
                         comment        - Adds the comment of the edit
                         parsedcomment  - Adds the parsed comment of the edit
                         size           - Adds the size of the page
                         flags          - Adds flags of the edit
                         patrolled      - Tags patrolled edits
                         tags           - Lists tags for the edit
                        Values (separate with '|'): ids, title, timestamp, comment, parsedcomment, size, flags, patrolled, tags
                        Default: ids|title|timestamp|comment|size|flags
    ucshow              - Show only items that meet this criteria, e.g. non minor edits only: ucshow=!minor
                        NOTE: if ucshow=patrolled or ucshow=!patrolled is set, revisions older than $wgRCMaxAge (2592000) won't be shown
                        Values (separate with '|'): minor, !minor, patrolled, !patrolled
    uctag               - Only list revisions tagged with this tag
    uctoponly           - Only list changes which are the latest revision
    """

    diff = set(kwargs).difference([
        'uclimit',
        'ucstart',
        'ucend',
        'uccontinue',
        'ucuser',
        'ucuserprefix',
        'ucdir',
        'ucnamespace',
        'ucprop',
        'ucshow',
        'uctag',
        'uctoponly'
    ])

    if diff:
        raise TypeError('Unknown parameter(s): %s' % ', '.join(diff))

    if not any([ i in kwargs for i in ['ucuser', 'ucuserprefix'] ]):
        raise TypeError('Must specify either ucuser or ucuserprefix keyword args.')


    params = {
        'uclimit' : kwargs.get('uclimit', 10),
        'ucdir' : kwargs.get('ucdir', 'older'),
        'ucprop' : kwargs.get('ucprop', 'ids|title|timestamp|comment|parsedcomment|size|flags|tags')
    }

    params.update(kwargs)

    results = []
    headers = { "User-Agent" : "Mozilla Firefox" }

    c = HTTPConnection("en.wikipedia.org")
    c.request(
        "GET",
        "/w/api.php?apihighlimits=true&action=query&format=json&list=usercontribs&%s" % urlencode(params),
        headers=headers
    )

    r = c.getresponse()

    if r.status == 200:
        result = JSONDecoder().decode(r.read())

        if 'error' in result:
            raise WikipediaError('%s: %s' % (result['error']['info'], result['error']['code']))

        results.extend(result['query']['usercontribs'])

        if 'query-continue' in result:
            i = len(result['query']['usercontribs'])
            while 'query-continue' in result and 'uccontinue' in result['query-continue']['usercontribs'] and \
                  i < config['wikipedia/maxresults']:
                params['uccontinue'] = result['query-continue']['usercontribs']['uccontinue']
                c.request(
                    "GET",
                    "/w/api.php?apihighlimits=true&action=query&format=json&list=usercontribs&%s" % urlencode(params),
                    headers=headers
                )
                r = c.getresponse()
                if r.status == 200:
                    result = JSONDecoder().decode(r.read())
                    results.extend(result['query']['usercontribs'])
                    i += len(result['query']['usercontribs'])
                else:
                    break

    return results

########NEW FILE########
