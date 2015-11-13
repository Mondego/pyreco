__FILENAME__ = AppDelegate
from Cocoa import NSApp
from Foundation import NSObject
from MainWindowController import MainWindowController

class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        window = MainWindowController()
        window.showWindow_(window)
        NSApp.activateIgnoringOtherApps_(True)

    def applicationShouldTerminateAfterLastWindowClosed_(self, sender):
        return True

########NEW FILE########
__FILENAME__ = Capture
import bisect
from Foundation import NSAutoreleasePool, NSObject, NSThread
from PyObjCTools import AppHelper
import re
import struct

PROBE_CALLS = re.compile(r"^\/stalker\/probes\/(.*?)\/calls$")

class Capture(NSObject):
    def __new__(cls, device):
        return cls.alloc().initWithDevice_(device)

    def initWithDevice_(self, device):
        self = self.init()
        self.state = CaptureState.DETACHED
        self.device = device
        self._delegate = None
        self.session = None
        self.script = None
        self.modules = Modules()
        self.recvTotal = 0
        self.calls = Calls(self)
        return self

    def delegate(self):
        return self._delegate

    def setDelegate_(self, delegate):
        self._delegate = delegate

    def attachToProcess_triggerPort_(self, process, triggerPort):
        assert self.state == CaptureState.DETACHED
        self._updateState_(CaptureState.ATTACHING)
        NSThread.detachNewThreadSelector_toTarget_withObject_('_doAttachWithParams:', self, (process.pid, triggerPort))

    def detach(self):
        assert self.state == CaptureState.ATTACHED
        session = self.session
        script = self.script
        self.session = None
        self.script = None
        self._updateState_(CaptureState.DETACHED)
        NSThread.detachNewThreadSelector_toTarget_withObject_('_doDetachWithParams:', self, (session, script))

    def _post(self, message):
        NSThread.detachNewThreadSelector_toTarget_withObject_('_doPostWithParams:', self, (self.script, message))

    def _updateState_(self, newState):
        self.state = newState
        self._delegate.captureStateDidChange()

    def _doAttachWithParams_(self, params):
        pid, triggerPort = params
        pool = NSAutoreleasePool.alloc().init()
        session = None
        script = None
        error = None
        try:
            session = self.device.attach(pid)
            session.on('detached', self._onSessionDetached)
            script = session.session.create_script(SCRIPT_TEMPLATE % {
                'trigger_port': triggerPort
            })
            script.on('message', self._onScriptMessage)
            script.load()
        except Exception, e:
            if session is not None:
                try:
                    session.detach()
                except:
                    pass
                session = None
            script = None
            error = e
        AppHelper.callAfter(self._attachDidCompleteWithSession_script_error_, session, script, error)
        del pool

    def _doDetachWithParams_(self, params):
        session, script = params
        pool = NSAutoreleasePool.alloc().init()
        try:
            script.unload()
        except:
            pass
        try:
            session.detach()
        except:
            pass
        del pool

    def _doPostWithParams_(self, params):
        script, message = params
        pool = NSAutoreleasePool.alloc().init()
        try:
            script.post_message(message)
        except Exception, e:
            print "Failed to post to script:", e
        del pool

    def _attachDidCompleteWithSession_script_error_(self, session, script, error):
        if self.state == CaptureState.ATTACHING:
            self.session = session
            self.script = script
            if error is None:
                self._updateState_(CaptureState.ATTACHED)
            else:
                self._updateState_(CaptureState.DETACHED)
                self._delegate.captureFailedToAttachWithError_(error)

    def _sessionDidDetach(self):
        if self.state == CaptureState.ATTACHING or self.state == CaptureState.ATTACHED:
            self.session = None
            self._updateState_(CaptureState.DETACHED)

    def _sessionDidReceiveMessage_data_(self, message, data):
        if message['type'] == 'send':
            stanza = message['payload']
            fromAddress = stanza['from']
            name = stanza['name']
            if fromAddress == "/process/modules" and name == '+sync':
                self.modules._sync(stanza['payload'])
            elif fromAddress == "/stalker/calls" and name == '+add':
                self.calls._add_(stanza['payload'])
            elif fromAddress == "/interceptor/functions" and name == '+add':
                self.recvTotal += 1
                self._delegate.captureRecvTotalDidChange()
            else:
                if not self.calls._handleStanza_(stanza):
                    print "Woot! Got stanza: %s from=%s" % (stanza['name'], stanza['from'])
        else:
            print "Unhandled message:", message

    def _onSessionDetached(self):
        AppHelper.callAfter(self._sessionDidDetach)

    def _onScriptMessage(self, message, data):
        AppHelper.callAfter(self._sessionDidReceiveMessage_data_, message, data)

class CaptureState:
    DETACHED = 1
    ATTACHING = 2
    ATTACHED = 3

class Modules:
    def __init__(self):
        self._modules = []
        self._indices = []

    def _sync(self, payload):
        modules = []
        for item in payload['items']:
            modules.append(Module(item['name'], int(item['base'], 16), item['size']))
        modules.sort(lambda x, y: x.address - y.address)
        self._modules = modules
        self._indices = [ m.address for m in modules ]

    def lookup(self, addr):
        idx = bisect.bisect(self._indices, addr)
        if idx == 0:
            return None
        m = self._modules[idx - 1]
        if addr >= m.address + m.size:
            return None
        return m

class Module:
    def __init__(self, name, address, size):
        self.name = name
        self.address = address
        self.size = size

    def __repr__(self):
        return "(%d, %d, %s)" % (self.address, self.size, self.name)

class Calls(NSObject):
    def __new__(cls, capture):
        return cls.alloc().initWithCapture_(capture)

    def initWithCapture_(self, capture):
        self = self.init()
        self.capture = capture
        self.targetModules = []
        self._targetModuleByAddress = {}
        self._delegate = None
        self._probes = {}
        return self

    def delegate(self):
        return self._delegate

    def setDelegate_(self, delegate):
        self._delegate = delegate

    def addProbe_(self, func):
        self.capture._post({
            'to': "/stalker/probes",
            'name': '+add',
            'payload': {
                'address': "0x%x" % func.address
            }
        })
        self._probes[func.address] = func

    def removeProbe_(self, func):
        self.capture._post({
            'to': "/stalker/probes",
            'name': '+remove',
            'payload': {
                'address': "0x%x" % func.address
            }
        })
        self._probes.pop(func.address, None)

    def _add_(self, data):
        modules = self.capture.modules
        for rawTarget, count in data['summary'].items():
            target = int(rawTarget, 16)
            tm = self.getTargetModuleByModule_(modules.lookup(target))
            if tm is not None:
                tm.total += count
                tf = tm.getTargetFunctionByAddress_(target)
                tf.total += count

        self.targetModules.sort(key=lambda tm: tm.total, reverse=True)
        for tm in self.targetModules:
            tm.functions.sort(self._compareFunctions)
        self._delegate.callsDidChange()

    def _compareFunctions(self, x, y):
        if x.hasProbe == y.hasProbe:
            return x.total - y.total
        elif x.hasProbe:
            return -1
        elif y.hasProbe:
            return 1
        else:
            return x.total - y.total

    def _handleStanza_(self, stanza):
        m = PROBE_CALLS.match(stanza['from'])
        if m is not None:
            func = self._probes.get(int(m.groups()[0], 16), None)
            if func is not None:
                if len(func.calls) == 3:
                    func.calls.pop(0)
                func.calls.append(FunctionCall(func, stanza['payload']['args']))
                self._delegate.callItemDidChange_(func)
            return True
        return False

    def getTargetModuleByModule_(self, module):
        if module is None:
            return None
        tm = self._targetModuleByAddress.get(module.address, None)
        if tm is None:
            tm = TargetModule(module)
            self.targetModules.append(tm)
            self._targetModuleByAddress[module.address] = tm
        return tm

    def outlineView_numberOfChildrenOfItem_(self, outlineView, item):
        if item is None:
            return len(self.targetModules)
        elif isinstance(item, TargetModule):
            return len(item.functions)
        elif isinstance(item, TargetFunction):
            return len(item.calls)
        else:
            return 0

    def outlineView_isItemExpandable_(self, outlineView, item):
        if item is None:
            return False
        elif isinstance(item, TargetModule):
            return len(item.functions) > 0
        elif isinstance(item, TargetFunction):
            return len(item.calls) > 0
        else:
            return False

    def outlineView_child_ofItem_(self, outlineView, index, item):
        if item is None:
            return self.targetModules[index]
        elif isinstance(item, TargetModule):
            return item.functions[index]
        elif isinstance(item, TargetFunction):
            return item.calls[index]
        else:
            return None

    def outlineView_objectValueForTableColumn_byItem_(self, outlineView, tableColumn, item):
        identifier = tableColumn.identifier()
        if isinstance(item, TargetModule):
            if identifier == 'name':
                return item.module.name
            elif identifier == 'total':
                return item.total
            else:
                return False
        elif isinstance(item, TargetFunction):
            if identifier == 'name':
                return item.name
            elif identifier == 'total':
                return item.total
            else:
                return item.hasProbe
        else:
            if identifier == 'name':
                return item.summary
            elif identifier == 'total':
                return ""
            else:
                return False

class TargetModule(NSObject):
    def __new__(cls, module):
        return cls.alloc().initWithModule_(module)

    def initWithModule_(self, module):
        self = self.init()
        self.module = module
        self.functions = []
        self._functionByAddress = {}
        self.total = 0
        return self

    def getTargetFunctionByAddress_(self, address):
        f = self._functionByAddress.get(address, None)
        if f is None:
            f = TargetFunction(self, address - self.module.address)
            self.functions.append(f)
            self._functionByAddress[address] = f
        return f

class TargetFunction(NSObject):
    def __new__(cls, module, offset):
        return cls.alloc().initWithModule_offset_(module, offset)

    def initWithModule_offset_(self, targetModule, offset):
        self = self.init()
        self.name = "sub_%x" % offset
        self.module = targetModule
        self.address = targetModule.module.address + offset
        self.offset = offset
        self.total = 0
        self.hasProbe = False
        self.calls = []
        return self

class FunctionCall(NSObject):
    def __new__(cls, func, args):
        return cls.alloc().initWithFunction_args_(func, args)

    def initWithFunction_args_(self, func, args):
        self = self.init()
        self.func = func
        self.args = args
        self.summary = "%s(%s)" % (func.name, ", ".join(args))
        return self

SCRIPT_TEMPLATE = """
var probes = Object.create(null);

var initialize = function initialize() {
    Stalker.trustThreshold = 2000;
    Stalker.queueCapacity = 1000000;
    Stalker.queueDrainInterval = 250;

    sendModules(function () {
        interceptReadFunction('recv');
        interceptReadFunction('read$UNIX2003');
        interceptReadFunction('readv$UNIX2003');
    });

    recv(onStanza);
};

var onStanza = function onStanza(stanza) {
    if (stanza.to === "/stalker/probes") {
        var address = stanza.payload.address,
            probeId;
        switch (stanza.name) {
            case '+add':
                if (probes[address] === undefined) {
                    var probeAddress = "/stalker/probes/" + address + "/calls";
                    probeId = Stalker.addCallProbe(ptr(address), function probe(args) {
                        var data = [
                            "0x" + args[0].toString(16),
                            "0x" + args[1].toString(16),
                            "0x" + args[2].toString(16),
                            "0x" + args[3].toString(16)
                        ];
                        send({ from: probeAddress, name: '+add', payload: { args: data } });
                    });
                    probes[address] = probeId;
                }
                break;
            case '+remove':
                probeId = probes[address];
                if (probeId !== undefined) {
                    Stalker.removeCallProbe(probeId);
                    delete probes[address];
                }
                break;
        }
    }

    recv(onStanza);
};

var sendModules = function sendModules(callback) {
    var modules = [];
    Process.enumerateModules({
        onMatch: function onMatch(module) {
            modules.push(module);
        },
        onComplete: function onComplete() {
            send({ name: '+sync', from: "/process/modules", payload: { items: modules } });
            callback();
        }
    });
};

var stalkedThreadId = null;
var interceptReadFunction = function interceptReadFunction(functionName) {
    Interceptor.attach(Module.findExportByName('libSystem.B.dylib', functionName), {
        onEnter: function(args) {
            this.fd = args[0].toInt32();
        },
        onLeave: function (retval) {
            var fd = this.fd;
            if (Socket.type(fd) === 'tcp') {
                var address = Socket.peerAddress(fd);
                if (address !== null && address.port === %(trigger_port)d) {
                    send({ name: '+add', from: "/interceptor/functions", payload: { items: [{ name: functionName }] } });
                    if (stalkedThreadId === null) {
                        stalkedThreadId = Process.getCurrentThreadId();
                        Stalker.follow(stalkedThreadId, {
                            events: {
                                call: true
                            },
                            onCallSummary: function onCallSummary(summary) {
                                send({ name: '+add', from: "/stalker/calls", payload: { summary: summary } });
                            }
                        });
                    }
                }
            }
        }
    });
}

setTimeout(initialize, 0);
"""

########NEW FILE########
__FILENAME__ = CpuShark
import sys
sys.path.insert(0, "/Users/oleavr/src/oss/frida-build-env/build/frida-mac-universal/lib/python2.7/site-packages")
import AppDelegate
import Capture
import MainWindowController
import ProcessList

if __name__ == "__main__":
    from PyObjCTools import AppHelper
    AppHelper.runEventLoop()

########NEW FILE########
__FILENAME__ = MainWindowController
import frida
from Capture import Capture, CaptureState, TargetFunction
from Cocoa import NSRunCriticalAlertPanel, NSUserDefaults, NSWindowController, objc
from ProcessList import ProcessList

class MainWindowController(NSWindowController):
    processCombo = objc.IBOutlet()
    triggerField = objc.IBOutlet()
    attachProgress = objc.IBOutlet()
    attachButton = objc.IBOutlet()
    detachButton = objc.IBOutlet()
    recvTotalLabel = objc.IBOutlet()
    callTableView = objc.IBOutlet()

    def __new__(cls):
        return cls.alloc().initWithTitle_("CpuShark")

    def initWithTitle_(self, title):
        self = self.initWithWindowNibName_("MainWindow")
        self.window().setTitle_(title)

        self.retain()

        return self

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)

        device = [device for device in frida.get_device_manager().enumerate_devices() if device.type == 'local'][0]
        self.processList = ProcessList(device)
        self.capture = Capture(device)
        self.processCombo.setUsesDataSource_(True)
        self.processCombo.setDataSource_(self.processList)
        self.capture.setDelegate_(self)

        self.callTableView.setDataSource_(self.capture.calls)
        self.capture.calls.setDelegate_(self)

        self.loadDefaults()

        self.updateAttachForm_(self)

    def windowWillClose_(self, notification):
        self.saveDefaults()

        self.autorelease()

    def loadDefaults(self):
        defaults = NSUserDefaults.standardUserDefaults()
        targetProcess = defaults.stringForKey_("targetProcess")
        if targetProcess is not None:
            for i, process in enumerate(self.processList.processes):
                if process.name == targetProcess:
                    self.processCombo.selectItemAtIndex_(i)
                    break
        triggerPort = defaults.integerForKey_("triggerPort") or 80
        self.triggerField.setStringValue_(str(triggerPort))

    def saveDefaults(self):
        defaults = NSUserDefaults.standardUserDefaults()
        process = self.selectedProcess()
        if process is not None:
            defaults.setObject_forKey_(process.name, "targetProcess")
        defaults.setInteger_forKey_(self.triggerField.integerValue(), "triggerPort")

    def selectedProcess(self):
        index = self.processCombo.indexOfSelectedItem()
        if index != -1:
            return self.processList.processes[index]
        return None

    def triggerPort(self):
        return self.triggerField.integerValue()

    @objc.IBAction
    def attach_(self, sender):
        self.capture.attachToProcess_triggerPort_(self.selectedProcess(), self.triggerPort())

    @objc.IBAction
    def detach_(self, sender):
        self.capture.detach()

    @objc.IBAction
    def toggleTracing_(self, sender):
        item = sender.itemAtRow_(sender.selectedRow())
        if isinstance(item, TargetFunction):
            func = item
            if func.hasProbe:
                self.capture.calls.removeProbe_(func)
            else:
                self.capture.calls.addProbe_(func)
            func.hasProbe = not func.hasProbe
            self.callTableView.reloadItem_(func)

    def updateAttachForm_(self, sender):
        isDetached = self.capture.state == CaptureState.DETACHED
        hasProcess = self.selectedProcess() is not None
        hasTrigger = len(self.triggerField.stringValue()) > 0
        self.processCombo.setEnabled_(isDetached)
        self.triggerField.setEnabled_(isDetached)
        self.attachProgress.setHidden_(self.capture.state != CaptureState.ATTACHING)
        self.attachButton.setHidden_(self.capture.state == CaptureState.ATTACHED)
        self.attachButton.setEnabled_(isDetached and hasProcess and hasTrigger)
        self.detachButton.setHidden_(self.capture.state != CaptureState.ATTACHED)
        if self.capture.state == CaptureState.ATTACHING:
            self.attachProgress.startAnimation_(self)
        else:
            self.attachProgress.stopAnimation_(self)

    def controlTextDidChange_(self, notification):
        self.updateAttachForm_(self)

    def comboBoxSelectionDidChange_(self, notification):
        self.updateAttachForm_(self)

    def captureStateDidChange(self):
        self.updateAttachForm_(self)

    def captureFailedToAttachWithError_(self, error):
        NSRunCriticalAlertPanel("Error", "Failed to attach: %s" % error, None, None, None)

    def captureRecvTotalDidChange(self):
        self.recvTotalLabel.setStringValue_(self.capture.recvTotal)

    def callsDidChange(self):
        self.callTableView.reloadData()

    def callItemDidChange_(self, item):
        self.callTableView.reloadItem_reloadChildren_(item, True)


########NEW FILE########
__FILENAME__ = ProcessList
from Foundation import NSObject, NSNotFound

class ProcessList(NSObject):
    def __new__(cls, device):
        return cls.alloc().initWithDevice_(device)

    def initWithDevice_(self, device):
        self = self.init()
        self.processes = sorted(device.enumerate_processes(), key=lambda d: d.name.lower())
        self._processNames = []
        self._processIndexByName = {}
        for i, process in enumerate(self.processes):
            lowerName = process.name.lower()
            self._processNames.append(lowerName)
            self._processIndexByName[lowerName] = i
        return self

    def numberOfItemsInComboBox_(self, comboBox):
        return len(self.processes)

    def comboBox_objectValueForItemAtIndex_(self, comboBox, index):
        return self.processes[index].name

    def comboBox_completedString_(self, comboBox, uncompletedString):
        lowerName = uncompletedString.lower()
        for i, name in enumerate(self._processNames):
            if name.startswith(lowerName):
                return self.processes[i].name
        return None

    def comboBox_indexOfItemWithStringValue_(self, comboBox, value):
        return self._processIndexByName.get(value.lower(), NSNotFound)


########NEW FILE########
__FILENAME__ = application
# -*- coding: utf-8 -*-

import collections
from optparse import OptionParser
import sys
import threading
import time

import colorama
from colorama import Style

import frida


def await_enter():
    if sys.version_info[0] >= 3:
        input()
    else:
        raw_input()

class ConsoleApplication(object):
    def __init__(self, run_until_return=await_enter):
        colorama.init(autoreset=True)

        parser = OptionParser(usage=self._usage())
        parser.add_option("-U", "--usb", help="connect to USB device",
                action='store_const', const='tether', dest="device_type", default='local')
        parser.add_option("-R", "--remote", help="connect to remote device",
                action='store_const', const='remote', dest="device_type", default='local')
        self._add_options(parser)

        (options, args) = parser.parse_args()

        self._device_type = options.device_type
        self._device = None
        self._schedule_on_device_lost = lambda: self._reactor.schedule(self._on_device_lost)
        self._target = None
        self._process = None
        self._schedule_on_process_detached = lambda: self._reactor.schedule(self._on_process_detached)
        self._started = False
        self._reactor = Reactor(run_until_return)
        self._exit_status = None
        self._status_updated = False

        self._initialize(parser, options, args)

        target_specifier = self._target_specifier(parser, options, args)
        if target_specifier is not None:
            try:
                self._target = int(target_specifier)
            except:
                self._target = target_specifier
        else:
            self._target = None

    def run(self):
        mgr = frida.get_device_manager()
        on_devices_changed = lambda: self._reactor.schedule(self._try_start)
        mgr.on('changed', on_devices_changed)
        self._reactor.schedule(self._try_start)
        self._reactor.schedule(self._show_message_if_no_device, delay=0.1)
        self._reactor.run()
        if self._started:
            self._stop()
        if self._process is not None:
            self._process.off('detached', self._schedule_on_process_detached)
            self._process.detach()
            self._process = None
        if self._device is not None:
            self._device.off('lost', self._schedule_on_device_lost)
        mgr.off('changed', on_devices_changed)
        frida.shutdown()
        sys.exit(self._exit_status)

    def _add_options(self, parser):
        pass

    def _initialize(self, parser, options, args):
        pass

    def _target_specifier(self, parser, options, args):
        return None

    def _start(self):
        pass

    def _stop(self):
        pass

    def _exit(self, exit_status):
        self._exit_status = exit_status
        self._reactor.stop()

    def _try_start(self):
        if self._device is not None:
            return
        self._device = find_device(self._device_type)
        if self._device is None:
            return
        self._device.on('lost', self._schedule_on_device_lost)
        if self._target is not None:
            try:
                self._update_status("Attaching...")
                self._process = self._device.attach(self._target)
                self._process.on('detached', self._schedule_on_process_detached)
            except Exception as e:
                self._update_status("Failed to attach: %s" % e)
                self._exit(1)
                return
        self._start()
        self._started = True

    def _show_message_if_no_device(self):
        if self._device is None:
            print("Waiting for USB device to appear...")

    def _on_device_lost(self):
        if self._exit_status is not None:
            return
        print("Device disconnected.")
        self._exit(1)

    def _on_process_detached(self):
        print("Target process terminated.")
        self._exit(1)

    def _update_status(self, message):
        if self._status_updated:
            cursor_position = "\033[A"
        else:
            cursor_position = ""
        print("%-80s" % (cursor_position + Style.BRIGHT + message,))
        self._status_updated = True

def find_device(type):
    for device in frida.get_device_manager().enumerate_devices():
        if device.type == type:
            return device
    return None


class Reactor(object):
    def __init__(self, run_until_return):
        self._running = False
        self._run_until_return = run_until_return
        self._pending = collections.deque([])
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)

    def run(self):
        with self._lock:
            self._running = True

        def termination_watcher():
            self._run_until_return()
            self.stop()
        watcher_thread = threading.Thread(target=termination_watcher)
        watcher_thread.daemon = True
        watcher_thread.start()

        running = True
        while running:
            now = time.time()
            work = None
            timeout = None
            with self._lock:
                for item in self._pending:
                    (f, when) = item
                    if now >= when:
                        work = f
                        self._pending.remove(item)
                        break
                if len(self._pending) > 0:
                    timeout = max([min(map(lambda item: item[1], self._pending)) - now, 0])
            if work is not None:
                work()
            with self._lock:
                if self._running:
                    self._cond.wait(timeout)
                running = self._running

    def stop(self):
        with self._lock:
            self._running = False
            self._cond.notify()

    def schedule(self, f, delay=None):
        now = time.time()
        if delay is not None:
            when = now + delay
        else:
            when = now
        with self._lock:
            self._pending.append((f, when))
            self._cond.notify()

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-

import bisect
import fnmatch
import numbers
import sys
import threading


class DeviceManager(object):
    def __init__(self, manager):
        self._manager = manager

    def __repr__(self):
        return repr(self._manager)

    def enumerate_devices(self):
        return [Device(device) for device in self._manager.enumerate_devices()]

    def get_device(self, device_id):
        devices = self._manager.enumerate_devices()
        if device_id is None:
            return Device(devices[0])
        for device in devices:
            if device.id == device_id:
                return Device(device)
        raise ValueError("device not found")

    def on(self, signal, callback):
        self._manager.on(signal, callback)

    def off(self, signal, callback):
        self._manager.off(signal, callback)

class Device(object):
    def __init__(self, device):
        self.id = device.id
        self.name = device.name
        self.icon = device.icon
        self.type = device.type
        self._device = device

    def __repr__(self):
        return repr(self._device)

    def enumerate_processes(self):
        return self._device.enumerate_processes()

    def get_process(self, process_name):
        process_name_lc = process_name.lower()
        matching = [process for process in self._device.enumerate_processes() if fnmatch.fnmatchcase(process.name.lower(), process_name_lc)]
        if len(matching) == 1:
            return matching[0]
        elif len(matching) > 1:
            raise ValueError("ambiguous name; it matches: %s" % ", ".join(["%s (pid: %d)" % (process.name, process.pid) for process in matching]))
        else:
            raise ValueError("process not found")

    def spawn(self, command_line):
        return self._device.spawn(command_line)

    def resume(self, target):
        return self._device.resume(self._pid_of(target))

    def attach(self, target):
        return Process(self._device.attach(self._pid_of(target)))

    def on(self, signal, callback):
        self._device.on(signal, callback)

    def off(self, signal, callback):
        self._device.off(signal, callback)

    def _pid_of(self, target):
        if isinstance(target, numbers.Number):
            return target
        else:
            return self.get_process(target).pid

class FunctionContainer(object):
    def __init__(self):
        self._functions = {}

    """
    @param address is relative to container
    """
    def ensure_function(self, address):
        f = self._functions.get(address)
        if f is not None:
            return f
        return self._do_ensure_function(address)

    def _do_ensure_function(self, address):
        raise NotImplementedError("not implemented")

class Process(FunctionContainer):
    def __init__(self, session):
        super(Process, self).__init__()
        self.session = session
        self._modules = None
        self._module_map = None

    def detach(self):
        self.session.detach()

    def enumerate_modules(self):
        if self._modules is None:
            script = self.session.create_script(
    """
    var modules = [];
    Process.enumerateModules({
        onMatch: function (module) {
            modules.push(module);
        },
        onComplete: function () {
            send(modules);
        }
    });
    """)
            self._modules = [Module(data['name'], int(data['base'], 16), data['size'], data['path'], self.session) for data in _execute_script(script)]
        return self._modules

    """
      @param protection example '--x'
    """
    def enumerate_ranges(self, protection):
        script = self.session.create_script(
"""
var ranges = [];
Process.enumerateRanges(\"%s\", {
    onMatch: function (range) {
        ranges.push(range);
    },
    onComplete: function () {
        send(ranges);
    }
});
""" % protection)
        return [Range(int(data['base'], 16), data['size'], data['protection']) for data in _execute_script(script)]

    def _exec_script(self, script_source, post_hook = None):
        script = self.session.create_script(script_source)
        return _execute_script(script, post_hook)

    def find_base_address(self, module_name):
        return int(self._exec_script("var p = Module.findBaseAddress(\"%s\"); send(p !== null ? p.toString() : \"0\");" % module_name), 16)

    def read_bytes(self, address, length):
        return self._exec_script("send(null, Memory.readByteArray(ptr(\"%u\"), %u));" % (address, length))

    def read_utf8(self, address, length = -1):
        return self._exec_script("send(Memory.readUtf8String(ptr(\"%u\"), %u));" % (address, length))

    def write_bytes(self, address, data):
        script = \
"""
recv(function (data) {
    var base = ptr("%u");
    for (var i = 0; i !== data.length; i++)
        Memory.writeU8(base.add(i), data[i]);
    send(true);
});
""" % address

        def send_data(script):
            script.post_message([x for x in iterbytes(data)])

        self._exec_script(script, send_data)

    def write_utf8(self, address, string):
        script = \
"""
recv(function (string) {
    Memory.writeUtf8String(ptr("%u"), string);
    send(true);
});
""" % address

        def send_data(script):
            script.post_message(string)

        self._exec_script(script, send_data)

    def on(self, signal, callback):
        self.session.on(signal, callback)

    def off(self, signal, callback):
        self.session.off(signal, callback)

    def _do_ensure_function(self, absolute_address):
        if self._module_map is None:
            self._module_map = ModuleMap(self.enumerate_modules())
        m = self._module_map.lookup(absolute_address)
        if m is not None:
            f = m.ensure_function(absolute_address - m.base_address)
        else:
            f = Function("dsub_%x" % absolute_address, absolute_address)
            self._functions[absolute_address] = f
        return f

class Module(FunctionContainer):
    def __init__(self, name, base_address, size, path, session):
        super(Module, self).__init__()
        self.name = name
        self.base_address = base_address
        self.size = size
        self.path = path
        self._exports = None
        self._session = session

    def __repr__(self):
        return "Module(name=\"%s\", base_address=0x%x, size=%d, path=\"%s\")" % (self.name, self.base_address, self.size, self.path)

    def __hash__(self):
        return self.base_address.__hash__()

    def __cmp__(self, other):
        return self.base_address.__cmp__(other.base_address)

    def __eq__(self, other):
        return self.base_address == other.base_address

    def __ne__(self, other):
        return self.base_address != other.base_address

    def enumerate_exports(self):
        if self._exports is None:
            script = self._session.create_script(
"""
var exports = [];
Module.enumerateExports(\"%s\", {
    onMatch: function (exp) {
        if (exp.type === 'function') {
            exports.push(exp);
        }
    },
    onComplete: function () {
        send(exports);
    }
});
""" % self.name)
            self._exports = []
            for export in _execute_script(script):
                relative_address = int(export["address"], 16) - self.base_address
                mf = ModuleFunction(self, export["name"], relative_address, True)
                self._exports.append(mf)
        return self._exports

    """
      @param protection example '--x'
    """
    def enumerate_ranges(self, protection):
        script = self._session.create_script(
"""
var ranges = [];
Module.enumerateRanges(\"%s\", \"%s\", {
    onMatch: function (range) {
        ranges.push(range);
    },
    onComplete: function () {
        send(ranges);
    }
});
""" % (self.name, protection))
        return [Range(int(data['base'], 16), data['size'], data['protection']) for data in _execute_script(script)]

    def _do_ensure_function(self, relative_address):
        if self._exports is None:
            for mf in self.enumerate_exports():
                self._functions[mf.relative_address] = mf
        mf = self._functions.get(relative_address)
        if mf is None:
            mf = ModuleFunction(self, "sub_%x" % relative_address, relative_address, False)
            self._functions[relative_address] = mf
        return mf

class Function(object):
    def __init__(self, name, absolute_address):
        self.name = name
        self.absolute_address = absolute_address

    def __str__(self):
        return self.name

    def __repr__(self):
        return "Function(name=\"%s\", absolute_address=0x%x)" % (self.name, self.absolute_address)

    def __hash__(self):
        return self.absolute_address.__hash__()

    def __cmp__(self, other):
        return self.absolute_address.__cmp__(other.absolute_address)

    def __eq__(self, other):
        return self.absolute_address == other.absolute_address

    def __ne__(self, other):
        return self.absolute_address != other.absolute_address

class ModuleFunction(Function):
    def __init__(self, module, name, relative_address, exported):
        super(ModuleFunction, self).__init__(name, module.base_address + relative_address)
        self.module = module
        self.relative_address = relative_address
        self.exported = exported

    def __repr__(self):
        return "ModuleFunction(module=\"%s\", name=\"%s\", relative_address=0x%x)" % (self.module.name, self.name, self.relative_address)

class Range(object):
    def __init__(self, base_address, size, protection):
        self.base_address = base_address
        self.size = size
        self.protection = protection

    def __repr__(self):
        return "Range(base_address=0x%x, size=%s, protection='%s')" % (self.base_address, self.size, self.protection)

class Error(Exception):
    pass

class AddressMap(object):
    def __init__(self, items, get_address, get_size):
        self._items = sorted(items, key=get_address)
        self._indices = [ get_address(item) for item in self._items ]
        self._get_address = get_address
        self._get_size = get_size

    def lookup(self, address):
        index = bisect.bisect(self._indices, address)
        if index == 0:
            return None
        item = self._items[index - 1]
        if address >= self._get_address(item) + self._get_size(item):
            return None
        return item

class ModuleMap(AddressMap):
    def __init__(self, modules):
        super(ModuleMap, self).__init__(modules, lambda m: m.base_address, lambda m: m.size)

class FunctionMap(AddressMap):
    def __init__(self, functions, get_address = lambda f: f.absolute_address):
        super(FunctionMap, self).__init__(functions, get_address, lambda f: 1)

def _execute_script(script, post_hook = None):
    def on_message(message, data):
        if message['type'] == 'send':
            if data is not None:
                result['data'] = data
            else:
                result['data'] = message['payload']
        elif message['type'] == 'error':
            result['error'] = message['description']
        event.set()

    result = {}
    event = threading.Event()

    script.on('message', on_message)
    script.load()
    if post_hook:
        post_hook(script)
    event.wait()
    script.unload()
    script.off('message', on_message)

    if 'error' in result:
        raise Error(result['error'])

    return result['data']

if sys.version_info[0] >= 3:
    iterbytes = lambda x: iter(x)
else:
    def iterbytes(data):
        return (ord(char) for char in data)

########NEW FILE########
__FILENAME__ = discoverer
# -*- coding: utf-8 -*-

from frida.core import ModuleFunction


class Discoverer(object):
    def __init__(self, reactor):
        self._reactor = reactor
        self._script = None

    def start(self, process, ui):
        def on_message(message, data):
            self._reactor.schedule(lambda: self._process_message(message, data, process, ui))
        source = self._create_discover_script()
        self._script = process.session.create_script(source)
        self._script.on("message", on_message)
        self._script.load()

    def stop(self):
        if self._script is not None:
            try:
                self._script.unload()
            except:
                pass
            self._script = None

    def _create_discover_script(self):
        return """
var Sampler = function Sampler() {
    var total = 0;
    var pending = [];
    var active = [];
    var samples = {};
    Process.enumerateThreads({
        onMatch: function (thread) {
            pending.push(thread);
        },
        onComplete: function () {
            var currentThreadId = Process.getCurrentThreadId();
            pending = pending.filter(function (thread) {
                return thread.id !== currentThreadId;
            });
            total = pending.length;
            var processNext = function processNext() {
                active.forEach(function (thread) {
                    Stalker.unfollow(thread.id);
                });
                active = pending.splice(0, 4);
                if (active.length > 0) {
                    var begin = total - pending.length - active.length;
                    send({
                        from: "/sampler",
                        name: '+progress',
                        payload: {
                            begin: begin,
                            end: begin + active.length - 1,
                            total: total
                        }
                    });
                } else {
                    for (var address in samples) {
                        if (samples.hasOwnProperty(address)) {
                            var counts = samples[address].counts;
                            var sum = 0;
                            for (var i = 0; i !== counts.length; i++) {
                                sum += counts[i];
                            }
                            var callsPerSecond = Math.round(sum / (counts.length * 0.25));
                            samples[address] = callsPerSecond;
                        }
                    }
                    send({
                        from: "/sampler",
                        name: '+result',
                        payload: {
                            samples: samples
                        }
                    });
                    samples = null;
                }
                active.forEach(function (thread) {
                    Stalker.follow(thread.id, {
                        events: { call: true },
                        onCallSummary: function (summary) {
                            if (samples === null) {
                                return;
                            }

                            for (var address in summary) {
                                if (summary.hasOwnProperty(address)) {
                                    var sample = samples[address];
                                    if (sample === undefined) {
                                        sample = { counts: [] };
                                        samples[address] = sample;
                                    }
                                    sample.counts.push(summary[address]);
                                }
                            }
                        }
                    });
                });
                if (active.length > 0) {
                    setTimeout(processNext, 2000);
                    setTimeout(Stalker.garbageCollect, 2100);
                }
            };
            setTimeout(processNext, 0);
        }
    });
};
sampler = new Sampler();
"""

    def _process_message(self, message, data, process, ui):
        if message['type'] == 'send':
            stanza = message['payload']
            name = stanza['name']
            payload = stanza['payload']
            if stanza['from'] == "/sampler":
                if name == '+progress':
                    ui.on_sample_progress(payload['begin'], payload['end'], payload['total'])
                elif name == '+result':
                    module_functions = {}
                    dynamic_functions = []
                    for address, rate in payload['samples'].items():
                        address = int(address, 16)
                        function = process.ensure_function(address)
                        if isinstance(function, ModuleFunction):
                            functions = module_functions.get(function.module, [])
                            if len(functions) == 0:
                                module_functions[function.module] = functions
                            functions.append((function, rate))
                        else:
                            dynamic_functions.append((function, rate))
                    ui.on_sample_result(module_functions, dynamic_functions)
                else:
                    print(message, data)
            else:
                print(message, data)
        else:
            print(message, data)

class UI(object):
    def on_sample_progress(self, begin, end, total):
        pass

    def on_sample_result(self, module_functions, dynamic_functions):
        pass


def main():
    from frida.application import ConsoleApplication

    class DiscovererApplication(ConsoleApplication, UI):
        def _usage(self):
            return "usage: %prog [options] process-name-or-id"

        def _initialize(self, parser, options, args):
            self._discoverer = None

        def _target_specifier(self, parser, options, args):
            if len(args) != 1:
                parser.error("process name or id must be specified")
            return args[0]

        def _start(self):
            self._update_status("Injecting script...")
            self._discoverer = Discoverer(self._reactor)
            self._discoverer.start(self._process, self)

        def _stop(self):
            print("Stopping...")
            self._discoverer.stop()
            self._discoverer = None

        def on_sample_progress(self, begin, end, total):
            self._update_status("Sampling %d threads: %d through %d..." % (total, begin, end))

        def on_sample_result(self, module_functions, dynamic_functions):
            for module, functions in module_functions.items():
                print(module.name)
                print("\t%-10s\t%s" % ("Rate", "Function"))
                for function, rate in sorted(functions, key=lambda item: item[1], reverse=True):
                    print("\t%-10d\t%s" % (rate, function))
                print("")

            if len(dynamic_functions) > 0:
                print("Dynamic functions:")
                print("\t%-10s\t%s" % ("Rate", "Function"))
                for function, rate in sorted(dynamic_functions, key=lambda item: item[1], reverse=True):
                    print("\t%-10d\t%s" % (rate, function))

            self._exit(0)

    app = DiscovererApplication()
    app.run()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = ps
def main():
    from frida.application import ConsoleApplication

    class PSApplication(ConsoleApplication):
        def _usage(self):
            return "usage: %prog [options]"

        def _start(self):
            try:
                processes = self._device.enumerate_processes()
            except Exception as e:
                self._update_status("Failed to enumerate processes: %s" % e)
                self._exit(1)
                return
            pid_column_width = max(map(lambda p: len("%d" % p.pid), processes))
            header_format = "%" + str(pid_column_width) + "s %s"
            print(header_format % ("PID", "NAME"))
            line_format = "%" + str(pid_column_width) + "d %s"
            for process in sorted(processes, key=cmp_to_key(compare_devices)):
                print(line_format % (process.pid, process.name))
            self._exit(0)

    def compare_devices(a, b):
        a_has_icon = a.get_small_icon() is not None
        b_has_icon = b.get_small_icon() is not None
        if a_has_icon == b_has_icon:
            if a.name > b.name:
                return 1
            elif a.name < b.name:
                return -1
            else:
                return 0
        elif a_has_icon:
            return -1
        else:
            return 1

    def cmp_to_key(mycmp):
        "Convert a cmp= function into a key= function"
        class K:
            def __init__(self, obj, *args):
                self.obj = obj
            def __lt__(self, other):
                return mycmp(self.obj, other.obj) < 0
            def __gt__(self, other):
                return mycmp(self.obj, other.obj) > 0
            def __eq__(self, other):
                return mycmp(self.obj, other.obj) == 0
            def __le__(self, other):
                return mycmp(self.obj, other.obj) <= 0
            def __ge__(self, other):
                return mycmp(self.obj, other.obj) >= 0
            def __ne__(self, other):
                return mycmp(self.obj, other.obj) != 0
        return K

    app = PSApplication()
    app.run()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = repl
def main():
    from frida.application import ConsoleApplication
    import json
    try:
        import readline
        HAVE_READLINE = True
    except:
        HAVE_READLINE = False
    import sys
    import threading

    class REPLApplication(ConsoleApplication):
        def __init__(self):
            if HAVE_READLINE:
                readline.parse_and_bind("tab: complete")
            self._idle = threading.Event()
            super(REPLApplication, self).__init__(self._process_input)

        def _usage(self):
            return "usage: %prog [options]"

        def _target_specifier(self, parser, options, args):
            if len(args) != 1:
                parser.error("process name or id must be specified")
            return args[0]

        def _start(self):
            def on_message(message, data):
                self._reactor.schedule(lambda: self._process_message(message, data))
            self._script = self._process.session.create_script(self._create_repl_script())
            self._script.on("message", on_message)
            self._script.load()
            self._idle.set()

        def _stop(self):
            self._script.unload()

        def _create_repl_script(self):
            return """\

Object.defineProperty(this, 'modules', {
    enumerable: true,
    get: function () {
        var result = [];
        Process.enumerateModules({
            onMatch: function onMatch(mod) {
                result.push(mod);
            },
            onComplete: function onComplete() {
            }
        });
        return result;
    }
});

function onExpression(expression) {
    try {
        var result;
        eval("result = " + expression);
        var sentRaw = false;
        if (result && result.hasOwnProperty('length')) {
            try {
                send({ name: '+result', payload: "OOB" }, result);
                sentRaw = true;
            } catch (e) {
            }
        }
        if (!sentRaw) {
            send({ name: '+result', payload: result });
        }
    } catch (e) {
        send({ name: '+error', payload: e.toString() });
    }
    recv(onExpression);
}
recv(onExpression);
"""

        def _process_input(self):
            if sys.version_info[0] >= 3:
                input_impl = input
            else:
                input_impl = raw_input
            while True:
                self._idle.wait()
                expression = ""
                line = ""
                while len(expression) == 0 or line.endswith("\\"):
                    try:
                        if len(expression) == 0:
                            line = input_impl(">>> ")
                        else:
                            line = input_impl("... ")
                    except EOFError:
                        return
                    if len(line.strip()) > 0:
                        if len(expression) > 0:
                            expression += "\n"
                        expression += line.rstrip("\\")

                if HAVE_READLINE:
                    readline.add_history(expression)
                self._idle.clear()
                self._reactor.schedule(lambda: self._send_expression(expression))

        def _send_expression(self, expression):
            self._script.post_message(expression)

        def _process_message(self, message, data):
            handled = False

            if message['type'] == 'send' and 'payload' in message:
                stanza = message['payload']
                if isinstance(stanza, dict) and stanza.get('name') in ('+result', '+error'):
                    handled = True
                    if data is not None:
                        output = hexdump(data).rstrip("\n")
                    else:
                        if 'payload' in stanza:
                            value = stanza['payload']
                            if stanza['name'] == '+result':
                                output = json.dumps(value, sort_keys=True, indent=4, separators=(",", ": "))
                            else:
                                output = value
                        else:
                            output = "undefined"
                    sys.stdout.write(output + "\n")
                    sys.stdout.flush()
                    self._idle.set()

            if not handled:
                print("message:", message, "data:", data)

    def hexdump(src, length=16):
        try:
            xrange
        except NameError:
            xrange = range
        FILTER = "".join([(len(repr(chr(x))) == 3) and chr(x) or "." for x in range(256)])
        lines = []
        for c in xrange(0, len(src), length):
            chars = src[c:c + length]
            hex = " ".join(["%02x" % x for x in iterbytes(chars)])
            printable = ''.join(["%s" % ((x <= 127 and FILTER[x]) or ".") for x in iterbytes(chars)])
            lines.append("%04x  %-*s  %s\n" % (c, length*3, hex, printable))
        return "".join(lines)

    if sys.version_info[0] >= 3:
        iterbytes = lambda x: iter(x)
    else:
        def iterbytes(data):
            return (ord(char) for char in data)

    app = REPLApplication()
    app.run()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tracer
# -*- coding: utf-8 -*-

import os
import fnmatch
import time
import re
import binascii

from frida.core import ModuleFunction


class TracerProfileBuilder(object):
    _RE_REL_ADDRESS = re.compile("(?P<module>[^\s!]+)!(?P<offset>(0x)?[0-9a-fA-F]+)")

    def __init__(self):
        self._spec = []

    def include_modules(self, *module_name_globs):
        for m in module_name_globs:
            self._spec.append(("include", "module", m))
        return self

    def exclude_modules(self, *module_name_globs):
        for m in module_name_globs:
            self._spec.append(("exclude", "module", m))
        return self

    def include(self, *function_name_globs):
        for f in function_name_globs:
            self._spec.append(("include", "function", f))
        return self

    def exclude(self, *function_name_globs):
        for f in function_name_globs:
            self._spec.append(("exclude", "function", f))
        return self

    def include_rel_address(self, *address_rel_offsets):
        for f in address_rel_offsets:
            m = TracerProfileBuilder._RE_REL_ADDRESS.search(f)
            if m is None:
                continue
            self._spec.append(("include", "rel_address", 
                               {'module':m.group('module'), 
                                'offset':int(m.group('offset'), base=16)}))

    def build(self):
        return TracerProfile(self._spec)

class TracerProfile(object):
    def __init__(self, spec):
        self._spec = spec

    def resolve(self, process):
        all_modules = process.enumerate_modules()
        working_set = set()
        for (operation, scope, param) in self._spec:
            if scope == "module":
                if operation == "include":
                    working_set = working_set.union(self._include_module(param, all_modules))
                elif operation == "exclude":
                    working_set = self._exclude_module(param, working_set)
            elif scope == "function":
                if operation == "include":
                    working_set = working_set.union(self._include_function(param, all_modules))
                elif operation == "exclude":
                    working_set = self._exclude_function(param, working_set)
            elif scope == 'rel_address':
                if operation == "include":
                    abs_address = process.find_base_address(param['module']) + param['offset']
                    working_set.add(process.ensure_function(abs_address))
        return list(working_set)

    def _include_module(self, glob, all_modules):
        r = []
        for module in all_modules:
            if fnmatch.fnmatchcase(module.name, glob):
                for export in module.enumerate_exports():
                    r.append(export)
        return r

    def _exclude_module(self, glob, working_set):
        r = []
        for export in working_set:
            if not fnmatch.fnmatchcase(export.module.name, glob):
                r.append(export)
        return set(r)

    def _include_function(self, glob, all_modules):
        r = []
        for module in all_modules:
            for export in module.enumerate_exports():
                if fnmatch.fnmatchcase(export.name, glob):
                    r.append(export)
        return r

    def _exclude_function(self, glob, working_set):
        r = []
        for export in working_set:
            if not fnmatch.fnmatchcase(export.name, glob):
                r.append(export)
        return set(r)

class Tracer(object):
    def __init__(self, reactor, repository, profile):
        self._reactor = reactor
        self._repository = repository
        self._profile = profile
        self._script = None

    def start_trace(self, process, ui):
        def on_create(*args):
            ui.on_trace_handler_create(*args)
        self._repository.on_create(on_create)

        def on_load(*args):
            ui.on_trace_handler_load(*args)
        self._repository.on_load(on_load)

        def on_update(function, handler, source):
            self._script.post_message({
                'to': "/targets",
                'name': '+update',
                'payload': {
                    'items': [{
                        'absolute_address': hex(function.absolute_address),
                        'handler': handler
                    }]
                }
            })
        self._repository.on_update(on_update)

        def on_message(message, data):
            self._reactor.schedule(lambda: self._process_message(message, data, ui))

        ui.on_trace_progress('resolve')
        working_set = self._profile.resolve(process)
        source = self._create_trace_script()
        ui.on_trace_progress('upload')
        self._script = process.session.create_script(source)
        self._script.on("message", on_message)
        self._script.load()
        for chunk in [working_set[i:i+1000] for i in range(0, len(working_set), 1000)]:
            targets = [{
                    'absolute_address': hex(function.absolute_address),
                    'handler': self._repository.ensure_handler(function)
                } for function in chunk]
            self._script.post_message({
                'to': "/targets",
                'name': '+add',
                'payload': {
                    'items': targets
                }
            })
        ui.on_trace_progress('ready')

        return working_set

    def stop(self):
        if self._script is not None:
            try:
                self._script.unload()
            except:
                pass
            self._script = None

    def _create_trace_script(self):
        return """\
var started = new Date();
var pending = [];
var timer = null;
var handlers = {};
function onStanza(stanza) {
    if (stanza.to === "/targets") {
        if (stanza.name === '+add') {
            add(stanza.payload.items);
        } else if (stanza.name === '+update') {
            update(stanza.payload.items);
        }
    }

    recv(onStanza);
}
function add(targets) {
    targets.forEach(function (target) {
        var targetAddress = target.absolute_address;
        eval("var handler = " + target.handler);
        target = null;

        var h = [handler];
        handlers[targetAddress] = h;
        function log(message) {
            send({
                from: "/events",
                name: '+add',
                payload: {
                    items: [[new Date().getTime() - started.getTime(), targetAddress, message]]
                }
            });
        }
        var state = {};

        pending.push(function attachToTarget() {
            Interceptor.attach(ptr(targetAddress), {
                onEnter: function onEnter(args) {
                    h[0].onEnter(log, args, state);
                },
                onLeave: function onLeave(retval) {
                    h[0].onLeave(log, retval, state);
                }
            });
        });
    });

    scheduleNext();
}
function update(targets) {
    targets.forEach(function (target) {
        eval("var handler = " + target.handler);
        handlers[target.absolute_address][0] = handler;
    });
}
function scheduleNext() {
    if (timer === null) {
        timer = setTimeout(processNext, 0);
    }
}
function processNext() {
    timer = null;

    if (pending.length > 0) {
        var work = pending.shift();
        work();
        scheduleNext();
    }
}
recv(onStanza);
"""

    def _process_message(self, message, data, ui):
        if message['type'] == 'send':
            stanza = message['payload']
            if stanza['from'] == "/events":
                if stanza['name'] == '+add':
                    events = [(timestamp, int(target_address.rstrip("L"), 16), message) for timestamp, target_address, message in stanza['payload']['items']]

                    ui.on_trace_events(events)

                    target_addresses = set([target_address for timestamp, target_address, message in events])
                    for target_address in target_addresses:
                        self._repository.sync_handler(target_address)
                else:
                    print(stanza)
            else:
                print(stanza)
        else:
            print(message)

class Repository(object):
    def __init__(self):
        self._on_create_callback = None
        self._on_load_callback = None
        self._on_update_callback = None

    def ensure_handler(self, function):
        raise NotImplementedError("not implemented")

    def sync_handler(self, function_address):
        pass

    def on_create(self, callback):
        self._on_create_callback = callback

    def on_load(self, callback):
        self._on_load_callback = callback

    def on_update(self, callback):
        self._on_update_callback = callback

    def _notify_create(self, function, handler, source):
        if self._on_create_callback is not None:
            self._on_create_callback(function, handler, source)

    def _notify_load(self, function, handler, source):
        if self._on_load_callback is not None:
            self._on_load_callback(function, handler, source)

    def _notify_update(self, function, handler, source):
        if self._on_update_callback is not None:
            self._on_update_callback(function, handler, source)

    def _create_stub_handler(self, function):
        return """\
/*
 * Auto-generated by Frida. Please modify to match the signature of %(name)s.
 * This stub is somewhat dumb. Future verions of Frida could auto-generate
 * based on OS API references, manpages, etc. (Pull-requests appreciated!)
 *
 * For full API reference, see: http://www.frida.re/docs/javascript-api/
 */

{
    /**
     * Called synchronously when about to call %(name)s.
     *
     * @this {object} - Object allowing you to store state for use in onLeave.
     * @param {function} log - Call this function with a string to be presented to the user.
     * @param {array} args - Function arguments represented as an array of NativePointer objects.
     * For example use Memory.readUtf8String(args[0]) if the first argument is a pointer to a C string encoded as UTF-8.
     * It is also possible to modify arguments by assigning a NativePointer object to an element of this array.
     * @param {object} state - Object allowing you to keep state across function calls.
     * Only one JavaScript function will execute at a time, so do not worry about race-conditions.
     * However, do not use this to store function arguments across onEnter/onLeave, but instead
     * use "this" which is an object for keeping state local to an invocation.
     */
    onEnter: function onEnter(log, args, state) {
        log("%(name)s()");
    },

    /**
     * Called synchronously when about to return from %(name)s.
     *
     * See onEnter for details.
     *
     * @this {object} - Object allowing you to access state stored in onEnter.
     * @param {function} log - Call this function with a string to be presented to the user.
     * @param {NativePointer} retval - Return value represented as a NativePointer object.
     * @param {object} state - Object allowing you to keep state across function calls.
     */
    onLeave: function onLeave(log, retval, state) {
    }
}
""" % { 'name': function.name }

class MemoryRepository(Repository):
    def __init__(self):
        super(MemoryRepository, self).__init__()
        self._handlers = {}

    def ensure_handler(self, function):
        handler = self._handlers.get(function)
        if handler is None:
            handler = self._create_stub_handler(function)
            self._handlers[function] = handler
            self._notify_create(function, handler, "memory")
        else:
            self._notify_load(function, handler, "memory")
        return handler

class FileRepository(Repository):
    def __init__(self):
        super(FileRepository, self).__init__()
        self._handlers = {}
        self._repo_dir = os.path.join(os.getcwd(), "__handlers__")

    def ensure_handler(self, function):
        entry = self._handlers.get(function.absolute_address)
        if entry is not None:
            (function, handler, handler_file, handler_mtime, last_sync) = entry
            return handler

        handler = None
        handler_files_to_try = []

        if isinstance(function, ModuleFunction):
            module_dir = os.path.join(self._repo_dir, to_filename(function.module.name))
            module_handler_file = os.path.join(module_dir, to_handler_filename(function.name))
            handler_files_to_try.append(module_handler_file)

        any_module_handler_file = os.path.join(self._repo_dir, to_handler_filename(function.name))
        handler_files_to_try.append(any_module_handler_file)

        for handler_file in handler_files_to_try:
            if os.path.isfile(handler_file):
                with open(handler_file, 'r') as f:
                    handler = f.read()
                self._notify_load(function, handler, handler_file)
                break

        if handler is None:
            handler = self._create_stub_handler(function)
            handler_file = handler_files_to_try[0]
            handler_dir = os.path.dirname(handler_file)
            if not os.path.isdir(handler_dir):
                os.makedirs(handler_dir)
            with open(handler_file, 'w') as f:
                f.write(handler)
            self._notify_create(function, handler, handler_file)

        handler_mtime = os.stat(handler_file).st_mtime
        self._handlers[function.absolute_address] = (function, handler, handler_file, handler_mtime, time.time())

        return handler

    def sync_handler(self, function_address):
        (function, handler, handler_file, handler_mtime, last_sync) = self._handlers[function_address]
        delta = time.time() - last_sync
        if delta >= 1.0:
            changed = False

            try:
                new_mtime = os.stat(handler_file).st_mtime
                if new_mtime != handler_mtime:
                    with open(handler_file, 'r') as f:
                        new_handler = f.read()
                    changed = new_handler != handler
                    handler = new_handler
                    handler_mtime = new_mtime
            except:
                pass

            self._handlers[function_address] = (function, handler, handler_file, handler_mtime, time.time())

            if changed:
                self._notify_update(function, handler, handler_file)

class UI(object):
    def on_trace_progress(self, operation):
        pass

    def on_trace_events(self, events):
        pass

    def on_trace_handler_create(self, function, handler, source):
        pass

    def on_trace_handler_load(self, function, handler, source):
        pass


def main():
    from frida.application import ConsoleApplication

    class TracerApplication(ConsoleApplication, UI):
        def _add_options(self, parser):
            pb = TracerProfileBuilder()
            def process_builder_arg(option, opt_str, value, parser, method, **kwargs):
                method(value)
            parser.add_option("-I", "--include-module", help="include MODULE", metavar="MODULE",
                    type='string', action='callback', callback=process_builder_arg, callback_args=(pb.include_modules,))
            parser.add_option("-X", "--exclude-module", help="exclude MODULE", metavar="MODULE",
                    type='string', action='callback', callback=process_builder_arg, callback_args=(pb.exclude_modules,))
            parser.add_option("-i", "--include", help="include FUNCTION", metavar="FUNCTION",
                    type='string', action='callback', callback=process_builder_arg, callback_args=(pb.include,))
            parser.add_option("-x", "--exclude", help="exclude FUNCTION", metavar="FUNCTION",
                    type='string', action='callback', callback=process_builder_arg, callback_args=(pb.exclude,))
            parser.add_option("-a", "--add", help="add MODULE!OFFSET", metavar="MODULE!OFFSET",
                    type='string', action='callback', callback=process_builder_arg, callback_args=(pb.include_rel_address,))
            self._profile_builder = pb

        def _usage(self):
            return "usage: %prog [options] process-name-or-id"

        def _initialize(self, parser, options, args):
            self._tracer = None
            self._profile = self._profile_builder.build()

        def _target_specifier(self, parser, options, args):
            if len(args) != 1:
                parser.error("process name or id must be specified")
            return args[0]

        def _start(self):
            self._tracer = Tracer(self._reactor, FileRepository(), self._profile)
            targets = self._tracer.start_trace(self._process, self)
            if len(targets) == 1:
                plural = ""
            else:
                plural = "s"
            self._update_status("Started tracing %d function%s. Press ENTER to stop." % (len(targets), plural))

        def _stop(self):
            print("Stopping...")
            self._tracer.stop()
            self._tracer = None

        def on_trace_progress(self, operation):
            if operation == 'resolve':
                self._update_status("Resolving functions...")
            elif operation == 'upload':
                self._update_status("Uploading data...")
            elif operation == 'ready':
                self._update_status("Ready!")

        def on_trace_events(self, events):
            self._status_updated = False
            for timestamp, target_address, message in events:
                print("%6d ms\t%s" % (timestamp, message))

        def on_trace_handler_create(self, function, handler, source):
            print("%s: Auto-generated handler at \"%s\"" % (function, source))

        def on_trace_handler_load(self, function, handler, source):
            print("%s: Loaded handler at \"%s\"" % (function, source))

    app = TracerApplication()
    app.run()

def to_filename(name):
    result = ""
    for c in name:
        if c.isalnum() or c == ".":
            result += c
        else:
            result += "_"
    return result

def to_handler_filename(name):
    full_filename = to_filename(name)
    if len(full_filename) <= 41:
        return full_filename + ".js"
    crc = binascii.crc32(full_filename.encode())
    return full_filename[0:32] + "_%08x.js" % crc

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_core
# -*- coding: utf-8 -*-

import platform
import subprocess
import sys
import threading
try:
    import unittest2 as unittest
except:
    import unittest

import frida


class TestCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        system = platform.system()
        if system == 'Windows':
            cls.target = subprocess.Popen([r"C:\Windows\notepad.exe"])
        else:
            cls.target = subprocess.Popen(["/bin/cat"])
        cls.process = frida.attach(cls.target.pid)

    @classmethod
    def tearDownClass(cls):
        cls.process.detach()
        cls.target.terminate()

    def test_enumerate_devices(self):
        devices = frida.get_device_manager().enumerate_devices()
        self.assertTrue(len(devices) > 0)

    def test_enumerate_modules(self):
        modules = self.process.enumerate_modules()
        self.assertGreater(len(modules), 1)
        m = modules[0]
        self.assertIsInstance(repr(m), str)
        self.assertIsInstance(str(m), str)

    def test_enumerate_ranges(self):
        ranges = self.process.enumerate_ranges('r--')
        self.assertTrue(len(ranges) > 0)
        r = ranges[0]
        self.assertIsInstance(repr(r), str)
        self.assertIsInstance(str(r), str)

    def test_find_base_address(self):
        m = self.process.enumerate_modules()[0]
        self.assertEqual(self.process.find_base_address(m.name), m.base_address)
        self.assertEqual(self.process.find_base_address(m.name + "_does_not_exist$#@$"), 0)

    def test_memory_access(self):
        result = {}
        event = threading.Event()
        def on_message(message, data):
            self.assertEqual(message['type'], 'send')
            result['address'] = int(message['payload'], 16)
            event.set()

        script = self.process.session.create_script("""\
hello = Memory.allocUtf8String("Hello");
send(hello);
""")
        script.on('message', on_message)
        script.load()
        event.wait()
        hello_address = result['address']

        self.assertListEqual([x for x in iterbytes(self.process.read_bytes(hello_address, 6))],
            [0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x00])
        self.assertEqual(self.process.read_utf8(hello_address), "Hello")

        self.process.write_bytes(hello_address, b"Yo\x00")
        self.assertListEqual([x for x in iterbytes(self.process.read_bytes(hello_address, 6))],
            [0x59, 0x6f, 0x00, 0x6c, 0x6f, 0x00])
        self.assertEqual(self.process.read_utf8(hello_address), "Yo")
        self.process.write_utf8(hello_address, "Hei")
        self.assertListEqual([x for x in iterbytes(self.process.read_bytes(hello_address, 6))],
            [0x48, 0x65, 0x69, 0x00, 0x6f, 0x00])
        self.assertEqual(self.process.read_utf8(hello_address), "Hei")

        script.off('message', on_message)
        script.unload()

    def test_enumerate_module_exports(self):
        m = self.process.enumerate_modules()[1]
        exports = m.enumerate_exports()
        e = exports[0]
        self.assertIsInstance(repr(e), str)
        self.assertIsInstance(str(e), str)

    def test_enumerate_module_ranges(self):
        m = self.process.enumerate_modules()[1]
        ranges = m.enumerate_ranges('r--')
        r = ranges[0]
        self.assertIsInstance(repr(r), str)
        self.assertIsInstance(str(r), str)


if sys.version_info[0] >= 3:
    iterbytes = lambda x: iter(x)
else:
    def iterbytes(data):
        return (ord(char) for char in data)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_discoverer
# -*- coding: utf-8 -*-

import platform
import subprocess
import threading
try:
    import unittest2 as unittest
except:
    import unittest

import frida
from frida.application import Reactor
from frida.discoverer import Discoverer, UI


class TestDiscoverer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        system = platform.system()
        if system == 'Windows':
            cls.target = subprocess.Popen([r"C:\Windows\notepad.exe"])
        else:
            cls.target = subprocess.Popen(["/bin/cat"])
        cls.process = frida.attach(cls.target.pid)

    @classmethod
    def tearDownClass(cls):
        cls.process.detach()
        cls.target.terminate()

    def test_basics(self):
        test_ui = TestUI()
        reactor = Reactor(test_ui.on_result.wait)
        def start():
            d = Discoverer(reactor)
            d.start(self.process, test_ui)
        reactor.schedule(start)
        reactor.run()
        self.assertIsInstance(test_ui.module_functions, dict)
        self.assertIsInstance(test_ui.dynamic_functions, list)

class TestUI(UI):
    def __init__(self):
        super(UI, self).__init__()
        self.module_functions = None
        self.dynamic_functions = None
        self.on_result = threading.Event()

    def on_sample_result(self, module_functions, dynamic_functions):
        self.module_functions = module_functions
        self.dynamic_functions = dynamic_functions
        self.on_result.set()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_tracer
# -*- coding: utf-8 -*-

import platform
import subprocess
import threading
try:
    import unittest2 as unittest
except:
    import unittest

import frida
from frida.application import Reactor
from frida.tracer import Tracer, TracerProfileBuilder, MemoryRepository, UI


class TestTracer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        system = platform.system()
        if system == 'Windows':
            cls.target = subprocess.Popen([r"C:\Windows\notepad.exe"])
        else:
            cls.target = subprocess.Popen(["/bin/cat"])
        cls.process = frida.attach(cls.target.pid)

    @classmethod
    def tearDownClass(cls):
        cls.process.detach()
        cls.target.terminate()

    def test_basics(self):
        never = threading.Event()
        reactor = Reactor(never.wait)
        def start():
            tp = TracerProfileBuilder().include("open*")
            t = Tracer(reactor, MemoryRepository(), tp.build())
            targets = t.start_trace(self.process, UI())
            t.stop()
            reactor.stop()
        reactor.schedule(start)
        reactor.run()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
