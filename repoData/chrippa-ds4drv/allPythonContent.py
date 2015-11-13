__FILENAME__ = action
from .config import add_controller_option
from .utils import with_metaclass

from functools import wraps

BASE_CLASSES = ["Action", "ReportAction"]


class ActionRegistry(type):
    def __init__(cls, name, bases, attrs):
        if name not in BASE_CLASSES:
            if not hasattr(ActionRegistry, "actions"):
                ActionRegistry.actions = []
            else:
                ActionRegistry.actions.append(cls)


class Action(with_metaclass(ActionRegistry)):
    """Actions are what drives most of the functionality of ds4drv."""

    @classmethod
    def add_option(self, *args, **kwargs):
        add_controller_option(*args, **kwargs)

    def __init__(self, controller):
        self.controller = controller
        self.logger = controller.logger

        self.register_event("device-setup", self.setup)
        self.register_event("device-cleanup", self.disable)
        self.register_event("load-options", self.load_options)

    def create_timer(self, interval, func):
        return self.controller.loop.create_timer(interval, func)

    def register_event(self, event, func):
        self.controller.loop.register_event(event, func)

    def unregister_event(self, event, func):
        self.controller.loop.unregister_event(event, func)

    def setup(self, device):
        pass

    def enable(self):
        pass

    def disable(self):
        pass

    def load_options(self, options):
        pass


class ReportAction(Action):
    def __init__(self, controller):
        super(ReportAction, self).__init__(controller)

        self._last_report = None
        self.register_event("device-report", self._handle_report)

    def create_timer(self, interval, callback):
        @wraps(callback)
        def wrapper(*args, **kwargs):
            if self._last_report:
                return callback(self._last_report, *args, **kwargs)
            return True

        return super(ReportAction, self).create_timer(interval, wrapper)

    def _handle_report(self, report):
        self._last_report = report
        self.handle_report(report)

    def handle_report(self, report):
        pass

########NEW FILE########
__FILENAME__ = battery
from ..action import ReportAction

BATTERY_WARNING = 2

ReportAction.add_option("--battery-flash", action="store_true",
                        help="Flashes the LED once a minute if the "
                             "battery is low")


class ReportActionBattery(ReportAction):
    """Flashes the LED when battery is low."""

    def __init__(self, *args, **kwargs):
        super(ReportActionBattery, self).__init__(*args, **kwargs)

        self.timer_check = self.create_timer(60, self.check_battery)
        self.timer_flash = self.create_timer(5, self.stop_flash)

    def enable(self):
        self.timer_check.start()

    def disable(self):
        self.timer_check.stop()
        self.timer_flash.stop()

    def load_options(self, options):
        if options.battery_flash:
            self.enable()
        else:
            self.disable()

    def stop_flash(self, report):
        self.controller.device.stop_led_flash()

    def check_battery(self, report):
        if report.battery < BATTERY_WARNING and not report.plug_usb:
            self.controller.device.start_led_flash(30, 30)
            self.timer_flash.start()

        return True

########NEW FILE########
__FILENAME__ = binding
import os
import re
import shlex
import subprocess

from collections import namedtuple
from itertools import chain

from ..action import ReportAction
from ..config import buttoncombo

ReportAction.add_option("--bindings", metavar="bindings",
                        help="Use custom action bindings specified in the "
                             "config file")

ReportAction.add_option("--profile-toggle", metavar="button(s)",
                        type=buttoncombo("+"),
                        help="A button combo that will trigger profile "
                             "cycling, e.g. 'R1+L1+PS'")

ActionBinding = namedtuple("ActionBinding", "modifiers button callback args")


class ReportActionBinding(ReportAction):
    """Listens for button presses and executes actions."""

    actions = {}

    @classmethod
    def action(cls, name):
        def decorator(func):
            cls.actions[name] = func
            return func

        return decorator

    def __init__(self, controller):
        super(ReportActionBinding, self).__init__(controller)

        self.bindings = []
        self.active = set()

    def add_binding(self, combo, callback, *args):
        modifiers, button = combo[:-1], combo[-1]
        binding = ActionBinding(modifiers, button, callback, args)
        self.bindings.append(binding)

    def load_options(self, options):
        self.active = set()
        self.bindings = []

        bindings = (self.controller.bindings["global"].items(),
                    self.controller.bindings.get(options.bindings, {}).items())

        for binding, action in chain(*bindings):
            self.add_binding(binding, self.handle_binding_action, action)

        have_profiles = (self.controller.profiles and
                         len(self.controller.profiles) > 1)
        if have_profiles and self.controller.default_profile.profile_toggle:
            self.add_binding(self.controller.default_profile.profile_toggle,
                             lambda r: self.controller.next_profile())

    def handle_binding_action(self, report, action):
        info = dict(name=self.controller.device.name,
                    profile=self.controller.current_profile,
                    device_addr=self.controller.device.device_addr,
                    report=report)

        def replace_var(match):
            var, attr = match.group("var", "attr")
            var = info.get(var)
            if attr:
                var = getattr(var, attr, None)
            return str(var)

        action = re.sub(r"\$(?P<var>\w+)(\.(?P<attr>\w+))?",
                        replace_var, action)
        action_split = shlex.split(action)
        action_type = action_split[0]
        action_args = action_split[1:]

        func = self.actions.get(action_type)
        if func:
            try:
                func(self.controller, *action_args)
            except Exception as err:
                self.logger.error("Failed to execute action: {0}", err)
        else:
            self.logger.error("Invalid action type: {0}", action_type)

    def handle_report(self, report):
        for binding in self.bindings:
            modifiers = True
            for button in binding.modifiers:
                modifiers = modifiers and getattr(report, button)

            active = getattr(report, binding.button)
            released = not active

            if modifiers and active and binding not in self.active:
                self.active.add(binding)
            elif released and binding in self.active:
                self.active.remove(binding)
                binding.callback(report, *binding.args)


@ReportActionBinding.action("exec")
def exec_(controller, cmd, *args):
    """Executes a subprocess in the foreground, blocking until returned."""
    controller.logger.info("Executing: {0} {1}", cmd, " ".join(args))

    try:
        subprocess.check_call([cmd] + list(args))
    except (OSError, subprocess.CalledProcessError) as err:
        controller.logger.error("Failed to execute process: {0}", err)


@ReportActionBinding.action("exec-background")
def exec_background(controller, cmd, *args):
    """Executes a subprocess in the background."""
    controller.logger.info("Executing in the background: {0} {1}",
                           cmd, " ".join(args))

    try:
        subprocess.Popen([cmd] + list(args),
                         stdout=open(os.devnull, "wb"),
                         stderr=open(os.devnull, "wb"))
    except OSError as err:
        controller.logger.error("Failed to execute process: {0}", err)


@ReportActionBinding.action("next-profile")
def next_profile(controller):
    """Loads the next profile."""
    controller.next_profile()


@ReportActionBinding.action("prev-profile")
def prev_profile(controller):
    """Loads the previous profile."""
    controller.prev_profile()


@ReportActionBinding.action("load-profile")
def load_profile(controller, profile):
    """Loads the specified profile."""
    controller.load_profile(profile)

########NEW FILE########
__FILENAME__ = btsignal
from ..action import ReportAction


class ReportActionBTSignal(ReportAction):
    """Warns when a low report rate is discovered and may impact usability."""

    def __init__(self, *args, **kwargs):
        super(ReportActionBTSignal, self).__init__(*args, **kwargs)

        self.timer_check = self.create_timer(2.5, self.check_signal)
        self.timer_reset = self.create_timer(60, self.reset_warning)

    def setup(self, device):
        self.reports = 0
        self.signal_warned = False

        if device.type == "bluetooth":
            self.enable()
        else:
            self.disable()

    def enable(self):
        self.timer_check.start()

    def disable(self):
        self.timer_check.stop()
        self.timer_reset.stop()

    def check_signal(self, report):
        # Less than 60 reports/s means we are probably dropping
        # reports between frames in a 60 FPS game.
        rps = int(self.reports / 2.5)
        if not self.signal_warned and rps < 60:
            self.logger.warning("Signal strength is low ({0} reports/s)", rps)
            self.signal_warned = True
            self.timer_reset.start()

        self.reports = 0

        return True

    def reset_warning(self, report):
        self.signal_warned = False

    def handle_report(self, report):
        self.reports += 1

########NEW FILE########
__FILENAME__ = dump
from ..action import ReportAction

ReportAction.add_option("--dump-reports", action="store_true",
                        help="Prints controller input reports")


class ReportActionDump(ReportAction):
    """Pretty prints the reports to the log."""

    def __init__(self, *args, **kwargs):
        super(ReportActionDump, self).__init__(*args, **kwargs)
        self.timer = self.create_timer(0.02, self.dump)

    def enable(self):
        self.timer.start()

    def disable(self):
        self.timer.stop()

    def load_options(self, options):
        if options.dump_reports:
            self.enable()
        else:
            self.disable()

    def dump(self, report):
        dump = "Report dump\n"
        for key in report.__slots__:
            value = getattr(report, key)
            dump += "    {0}: {1}\n".format(key, value)

        self.logger.info(dump)

        return True

########NEW FILE########
__FILENAME__ = input
from ..action import ReportAction
from ..config import buttoncombo
from ..exceptions import DeviceError
from ..uinput import create_uinput_device

ReportAction.add_option("--emulate-xboxdrv", action="store_true",
                         help="Emulates the same joystick layout as a "
                              "Xbox 360 controller used via xboxdrv")
ReportAction.add_option("--emulate-xpad", action="store_true",
                        help="Emulates the same joystick layout as a wired "
                             "Xbox 360 controller used via the xpad module")
ReportAction.add_option("--emulate-xpad-wireless", action="store_true",
                        help="Emulates the same joystick layout as a wireless "
                             "Xbox 360 controller used via the xpad module")
ReportAction.add_option("--ignored-buttons", metavar="button(s)",
                        type=buttoncombo(","), default=[],
                        help="A comma-separated list of buttons to never send "
                             "as joystick events. For example specify 'PS' to "
                             "disable Steam's big picture mode shortcut when "
                             "using the --emulate-* options")
ReportAction.add_option("--mapping", metavar="mapping",
                        help="Use a custom button mapping specified in the "
                             "config file")
ReportAction.add_option("--trackpad-mouse", action="store_true",
                        help="Makes the trackpad control the mouse")


class ReportActionInput(ReportAction):
    """Creates virtual input devices via uinput."""

    def __init__(self, *args, **kwargs):
        super(ReportActionInput, self).__init__(*args, **kwargs)

        self.joystick = None
        self.joystick_layout = None
        self.mouse = None

        # USB has a report frequency of 4 ms while BT is 2 ms, so we
        # use 5 ms between each mouse emit to keep it consistent and to
        # allow for at least one fresh report to be received inbetween
        self.timer = self.create_timer(0.005, self.emit_mouse)

    def setup(self, device):
        self.timer.start()

    def disable(self):
        self.timer.stop()

        if self.joystick:
            self.joystick.emit_reset()

        if self.mouse:
            self.mouse.emit_reset()

    def load_options(self, options):
        try:
            if options.mapping:
                joystick_layout = options.mapping
            elif options.emulate_xboxdrv:
                joystick_layout = "xboxdrv"
            elif options.emulate_xpad:
                joystick_layout = "xpad"
            elif options.emulate_xpad_wireless:
                joystick_layout = "xpad_wireless"
            else:
                joystick_layout = "ds4"

            if not self.mouse and options.trackpad_mouse:
                self.mouse = create_uinput_device("mouse")
            elif self.mouse and not options.trackpad_mouse:
                self.mouse.device.close()
                self.mouse = None

            if self.joystick and self.joystick_layout != joystick_layout:
                self.joystick.device.close()
                joystick = create_uinput_device(joystick_layout)
                self.joystick = joystick
            elif not self.joystick:
                joystick = create_uinput_device(joystick_layout)
                self.joystick = joystick
                if joystick.device.device:
                    self.logger.info("Created devices {0} (joystick) "
                                     "{1} (evdev) ", joystick.joystick_dev,
                                     joystick.device.device.fn)
            else:
                joystick = None

            self.joystick.ignored_buttons = set()
            for button in options.ignored_buttons:
                self.joystick.ignored_buttons.add(button)

            if joystick:
                self.joystick_layout = joystick_layout

                # If the profile binding is a single button we don't want to
                # send it to the joystick at all
                if (self.controller.profiles and
                    self.controller.default_profile.profile_toggle and
                    len(self.controller.default_profile.profile_toggle) == 1):

                    button = self.controller.default_profile.profile_toggle[0]
                    self.joystick.ignored_buttons.add(button)
        except DeviceError as err:
            self.controller.exit("Failed to create input device: {0}", err)

    def emit_mouse(self, report):
        if self.joystick:
            self.joystick.emit_mouse(report)

        if self.mouse:
            self.mouse.emit_mouse(report)

        return True

    def handle_report(self, report):
        if self.joystick:
            self.joystick.emit(report)

        if self.mouse:
            self.mouse.emit(report)

########NEW FILE########
__FILENAME__ = led
from ..action import Action
from ..config import hexcolor

Action.add_option("--led", metavar="color", default="0000ff", type=hexcolor,
                  help="Sets color of the LED. Uses hex color codes, "
                       "e.g. 'ff0000' is red. Default is '0000ff' (blue)")


class ActionLED(Action):
    """Sets the LED color on the device."""

    def setup(self, device):
        device.set_led(*self.controller.options.led)

    def load_options(self, options):
        if self.controller.device:
            self.controller.device.set_led(*options.led)

########NEW FILE########
__FILENAME__ = status
from ..action import ReportAction

BATTERY_MAX          = 8
BATTERY_MAX_CHARGING = 11


class ReportActionStatus(ReportAction):
    """Reports device statuses such as battery percentage to the log."""

    def __init__(self, *args, **kwargs):
        super(ReportActionStatus, self).__init__(*args, **kwargs)
        self.timer = self.create_timer(1, self.check_status)

    def setup(self, device):
        self.report = None
        self.timer.start()

    def disable(self):
        self.timer.stop()

    def check_status(self, report):
        if not self.report:
            self.report = report
            show_battery = True
        else:
            show_battery = False

        # USB cable
        if self.report.plug_usb != report.plug_usb:
            plug_usb = report.plug_usb and "Connected" or "Disconnected"
            show_battery = True

            self.logger.info("USB: {0}", plug_usb)

        # Battery level
        if self.report.battery != report.battery or show_battery:
            max_value = report.plug_usb and BATTERY_MAX_CHARGING or BATTERY_MAX
            battery = 100 * report.battery // max_value

            if battery < 100:
                self.logger.info("Battery: {0}%", battery)
            else:
                self.logger.info("Battery: Fully charged")

        # Audio cable
        if (self.report.plug_audio != report.plug_audio or
            self.report.plug_mic != report.plug_mic):

            if report.plug_audio and report.plug_mic:
                plug_audio = "Headset"
            elif report.plug_audio:
                plug_audio = "Headphones"
            elif report.plug_mic:
                plug_audio = "Mic"
            else:
                plug_audio = "Speaker"

            self.logger.info("Audio: {0}", plug_audio)

        self.report = report

        return True

########NEW FILE########
__FILENAME__ = backend
class Backend(object):
    """The backend is responsible for finding and creating DS4 devices."""

    __name__ = "backend"

    def __init__(self, manager):
        self.logger = manager.new_module(self.__name__)

    def setup(self):
        """Initialize the backend and make it ready for scanning.

        Raises BackendError on failure.
        """

        raise NotImplementedError

    @property
    def devices(self):
        """This iterator yields any devices found."""

        raise NotImplementedError

########NEW FILE########
__FILENAME__ = bluetooth
import socket
import subprocess

from ..backend import Backend
from ..exceptions import BackendError, DeviceError
from ..device import DS4Device
from ..utils import zero_copy_slice


L2CAP_PSM_HIDP_CTRL = 0x11
L2CAP_PSM_HIDP_INTR = 0x13

HIDP_TRANS_SET_REPORT = 0x50
HIDP_DATA_RTYPE_OUTPUT  = 0x02

REPORT_ID = 0x11
REPORT_SIZE = 79


class BluetoothDS4Device(DS4Device):
    @classmethod
    def connect(cls, addr):
        ctl_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET,
                                   socket.BTPROTO_L2CAP)

        int_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET,
                                   socket.BTPROTO_L2CAP)

        try:
            ctl_socket.connect((addr, L2CAP_PSM_HIDP_CTRL))
            int_socket.connect((addr, L2CAP_PSM_HIDP_INTR))
            int_socket.setblocking(False)
        except socket.error as err:
            DeviceError("Failed to connect: {0}".format(err))

        return cls(addr, ctl_socket, int_socket)

    def __init__(self, addr, ctl_sock, int_sock):
        self.buf = bytearray(REPORT_SIZE)
        self.ctl_sock = ctl_sock
        self.int_sock = int_sock
        self.report_fd = int_sock.fileno()

        super(BluetoothDS4Device, self).__init__(addr.upper(), addr,
                                                 "bluetooth")

    def read_report(self):
        try:
            ret = self.int_sock.recv_into(self.buf)
        except IOError:
            return

        # Disconnection
        if ret == 0:
            return

        # Invalid report size or id, just ignore it
        if ret < REPORT_SIZE or self.buf[1] != REPORT_ID:
            return False

        # Cut off bluetooth data
        buf = zero_copy_slice(self.buf, 3)

        return self.parse_report(buf)

    def write_report(self, report_id, data):
        hid = bytearray((HIDP_TRANS_SET_REPORT | HIDP_DATA_RTYPE_OUTPUT,
                         report_id))

        self.ctl_sock.sendall(hid + data)

    def set_operational(self):
        try:
            self.set_led(255, 255, 255)
        except socket.error as err:
            raise DeviceError("Failed to set operational mode: {0}".format(err))

    def close(self):
        self.int_sock.close()
        self.ctl_sock.close()


class BluetoothBackend(Backend):
    __name__ = "bluetooth"

    def setup(self):
        """Check if the bluetooth controller is available."""
        try:
            subprocess.check_output(["hcitool", "clock"],
                                    stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            raise BackendError("'hcitool clock' returned error. Make sure "
                               "your bluetooth device is powered up with "
                               "'hciconfig hciX up'.")
        except OSError:
            raise BackendError("'hcitool' could not be found, make sure you "
                               "have bluez-utils installed.")

    def scan(self):
        """Scan for bluetooth devices."""
        try:
            res = subprocess.check_output(["hcitool", "scan", "--flush"],
                                          stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
             raise BackendError("'hcitool scan' returned error. Make sure "
                                "your bluetooth device is powered up with "
                                "'hciconfig hciX up'.")

        devices = []
        res = res.splitlines()[1:]
        for _, bdaddr, name in map(lambda l: l.split(b"\t"), res):
            devices.append((bdaddr.decode("utf8"), name.decode("utf8")))

        return devices

    def find_device(self):
        """Scan for bluetooth devices and return a DS4 device if found."""
        for bdaddr, name in self.scan():
            if name == "Wireless Controller":
                self.logger.info("Found device {0}", bdaddr)
                return BluetoothDS4Device.connect(bdaddr)

    @property
    def devices(self):
        """Wait for new DS4 devices to appear."""
        log_msg = True
        while True:
            if log_msg:
                self.logger.info("Scanning for devices")

            try:
                device = self.find_device()
                if device:
                    yield device
                    log_msg = True
                else:
                    log_msg = False
            except BackendError as err:
                self.logger.error("Error while scanning for devices: {0}",
                                  err)
                return
            except DeviceError as err:
                self.logger.error("Unable to connect to detected device: {0}",
                                  err)


########NEW FILE########
__FILENAME__ = hidraw
import fcntl
import itertools
import os

from io import FileIO
from time import sleep

from evdev import InputDevice
from pyudev import Context, Monitor

from ..backend import Backend
from ..exceptions import DeviceError
from ..device import DS4Device
from ..utils import zero_copy_slice


IOC_RW = 3221243904
HIDIOCSFEATURE = lambda size: IOC_RW | (0x06 << 0) | (size << 16)
HIDIOCGFEATURE = lambda size: IOC_RW | (0x07 << 0) | (size << 16)


class HidrawDS4Device(DS4Device):
    def __init__(self, name, addr, type, hidraw_device, event_device):
        try:
            self.report_fd = os.open(hidraw_device, os.O_RDWR | os.O_NONBLOCK)
            self.fd = FileIO(self.report_fd, "rb+", closefd=False)
            self.input_device = InputDevice(event_device)
            self.input_device.grab()
        except (OSError, IOError) as err:
            raise DeviceError(err)

        self.buf = bytearray(self.report_size)

        super(HidrawDS4Device, self).__init__(name, addr, type)

    def read_report(self):
        try:
            ret = self.fd.readinto(self.buf)
        except IOError:
            return

        # Disconnection
        if ret == 0:
            return

        # Invalid report size or id, just ignore it
        if ret < self.report_size or self.buf[0] != self.valid_report_id:
            return False

        if self.type == "bluetooth":
            # Cut off bluetooth data
            buf = zero_copy_slice(self.buf, 2)
        else:
            buf = self.buf

        return self.parse_report(buf)

    def read_feature_report(self, report_id, size):
        op = HIDIOCGFEATURE(size + 1)
        buf = bytearray(size + 1)
        buf[0] = report_id

        return fcntl.ioctl(self.fd, op, bytes(buf))

    def write_report(self, report_id, data):
        if self.type == "bluetooth":
            # TODO: Add a check for a kernel that supports writing
            # output reports when such a kernel has been released.
            return

        hid = bytearray((report_id,))
        self.fd.write(hid + data)

    def close(self):
        try:
            self.fd.close()
            self.input_device.ungrab()
        except IOError:
            pass


class HidrawBluetoothDS4Device(HidrawDS4Device):
    __type__ = "bluetooth"

    report_size = 78
    valid_report_id = 0x11

    def set_operational(self):
        self.read_feature_report(0x02, 37)


class HidrawUSBDS4Device(HidrawDS4Device):
    __type__ = "usb"

    report_size = 64
    valid_report_id = 0x01

    def set_operational(self):
        # Get the bluetooth MAC
        addr = self.read_feature_report(0x81, 6)[1:]
        addr = ["{0:02x}".format(c) for c in bytearray(addr)]
        addr = ":".join(reversed(addr)).upper()

        self.device_name = "{0} {1}".format(addr, self.device_name)
        self.device_addr = addr


HID_DEVICES = {
    "Sony Computer Entertainment Wireless Controller": HidrawUSBDS4Device,
    "Wireless Controller": HidrawBluetoothDS4Device,
}


class HidrawBackend(Backend):
    __name__ = "hidraw"

    def setup(self):
        pass

    def _get_future_devices(self, context):
        """Return a generator yielding new devices."""
        monitor = Monitor.from_netlink(context)
        monitor.filter_by("hidraw")
        monitor.start()

        self._scanning_log_message()
        for device in iter(monitor.poll, None):
            if device.action == "add":
                # Sometimes udev rules has not been applied at this point,
                # causing permission denied error if we are running in user
                # mode. With this sleep this will hopefully not happen.
                sleep(1)

                yield device
                self._scanning_log_message()

    def _scanning_log_message(self):
        self.logger.info("Scanning for devices")

    @property
    def devices(self):
        """Wait for new DS4 devices to appear."""
        context = Context()

        existing_devices = context.list_devices(subsystem="hidraw")
        future_devices = self._get_future_devices(context)

        for hidraw_device in itertools.chain(existing_devices, future_devices):
            hid_device = hidraw_device.parent
            if hid_device.subsystem != "hid":
                continue

            cls = HID_DEVICES.get(hid_device.get("HID_NAME"))
            if not cls:
                continue

            for child in hid_device.parent.children:
                event_device = child.get("DEVNAME", "")
                if event_device.startswith("/dev/input/event"):
                    break
            else:
                continue


            try:
                device_addr = hid_device.get("HID_UNIQ", "").upper()
                if device_addr:
                    device_name = "{0} {1}".format(device_addr,
                                                   hidraw_device.sys_name)
                else:
                    device_name = hidraw_device.sys_name

                yield cls(name=device_name,
                          addr=device_addr,
                          type=cls.__type__,
                          hidraw_device=hidraw_device.device_node,
                          event_device=event_device)

            except DeviceError as err:
                self.logger.error("Unable to open DS4 device: {0}", err)

########NEW FILE########
__FILENAME__ = config
import argparse
import os
import re
import sys

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

from functools import partial
from operator import attrgetter

from . import __version__
from .uinput import parse_uinput_mapping
from .utils import parse_button_combo


CONFIG_FILES = ("~/.config/ds4drv.conf", "/etc/ds4drv.conf")
DAEMON_LOG_FILE = "~/.cache/ds4drv.log"
DAEMON_PID_FILE = "/tmp/ds4drv.pid"


class SortingHelpFormatter(argparse.HelpFormatter):
    def add_argument(self, action):
        # Force the built in options to be capitalized
        if action.option_strings[-1] in ("--version", "--help"):
            action.help = action.help.capitalize()

        super(SortingHelpFormatter, self).add_argument(action)
        self.add_text("")

    def start_section(self, heading):
        heading = heading.capitalize()
        return super(SortingHelpFormatter, self).start_section(heading)

    def add_arguments(self, actions):
        actions = sorted(actions, key=attrgetter("option_strings"))
        super(SortingHelpFormatter, self).add_arguments(actions)


parser = argparse.ArgumentParser(prog="ds4drv",
                                 formatter_class=SortingHelpFormatter)
parser.add_argument("--version", action="version",
                    version="%(prog)s {0}".format(__version__))

configopt = parser.add_argument_group("configuration options")
configopt.add_argument("--config", metavar="filename",
                       type=os.path.expanduser,
                       help="Configuration file to read settings from. "
                            "Default is ~/.config/ds4drv.conf or "
                            "/etc/ds4drv.conf, whichever is found first")

backendopt = parser.add_argument_group("backend options")
backendopt.add_argument("--hidraw", action="store_true",
                        help="Use hidraw devices. This can be used to access "
                             "USB and paired bluetooth devices. Note: "
                             "Bluetooth devices does currently not support "
                             "any LED functionality")

daemonopt = parser.add_argument_group("daemon options")
daemonopt.add_argument("--daemon", action="store_true",
                       help="Run in the background as a daemon")
daemonopt.add_argument("--daemon-log", default=DAEMON_LOG_FILE, metavar="file",
                       help="Log file to create in daemon mode")
daemonopt.add_argument("--daemon-pid", default=DAEMON_PID_FILE, metavar="file",
                       help="PID file to create in daemon mode")

controllopt = parser.add_argument_group("controller options")


class Config(configparser.SafeConfigParser):
    def load(self, filename):
        self.read([filename])

    def section_to_args(self, section):
        args = []

        for key, value in self.section(section).items():
            if value.lower() == "true":
                args.append("--{0}".format(key))
            elif value.lower() == "false":
                pass
            else:
                args.append("--{0}={1}".format(key, value))

        return args

    def section(self, section, key_type=str, value_type=str):
        try:
            # Removes empty values and applies types
            return dict(map(lambda kv: (key_type(kv[0]), value_type(kv[1])),
                            filter(lambda i: bool(i[1]),
                                   self.items(section))))
        except configparser.NoSectionError:
            return {}

    def sections(self, prefix=None):
        for section in configparser.SafeConfigParser.sections(self):
            match = re.match(r"{0}:(.+)".format(prefix), section)
            if match:
                yield match.group(1), section

    def controllers(self):
        controller_sections = dict(self.sections("controller"))
        if not controller_sections:
            return ["--next-controller"]

        last_controller = max(map(lambda c: int(c[0]), controller_sections))
        args = []
        for i in range(1, last_controller + 1):
            section = controller_sections.get(str(i))
            if section:
                for arg in self.section_to_args(section):
                    args.append(arg)

            args.append("--next-controller")

        return args


class ControllerAction(argparse.Action):
    # These options are moved from the normal options namespace to
    # a controller specific namespace on --next-controller.
    __options__ = []

    @classmethod
    def default_controller(cls):
        controller = argparse.Namespace()
        defaults = parser.parse_args([])
        for option in cls.__options__:
            value = getattr(defaults, option)
            setattr(controller, option, value)

        return controller

    def __call__(self, parser, namespace, values, option_string=None):
        if not hasattr(namespace, "controllers"):
            setattr(namespace, "controllers", [])

        controller = argparse.Namespace()
        defaults = parser.parse_args([])
        for option in self.__options__:
            if hasattr(namespace, option):
                value = namespace.__dict__.pop(option)
                if isinstance(value, str):
                    for action in filter(lambda a: a.dest == option,
                                         parser._actions):
                        value = parser._get_value(action, value)
            else:
                value = getattr(defaults, option)

            setattr(controller, option, value)

        namespace.controllers.append(controller)

controllopt.add_argument("--next-controller", nargs=0, action=ControllerAction,
                         help="Creates another controller")

def hexcolor(color):
    color = color.strip("#")

    if len(color) != 6:
        raise ValueError

    values = (color[:2], color[2:4], color[4:6])
    values = map(lambda x: int(x, 16), values)

    return tuple(values)


def stringlist(s):
    return list(filter(None, map(str.strip, s.split(","))))


def buttoncombo(sep):
    func = partial(parse_button_combo, sep=sep)
    func.__name__ = "button combo"
    return func


def merge_options(src, dst, defaults):
    for key, value in src.__dict__.items():
        if key == "controllers":
            continue

        default = getattr(defaults, key)

        if getattr(dst, key) == default and value != default:
            setattr(dst, key, value)


def load_options():
    options = parser.parse_args(sys.argv[1:] + ["--next-controller"])

    config = Config()
    config_paths = options.config and (options.config,) or CONFIG_FILES
    for path in filter(os.path.exists, map(os.path.expanduser, config_paths)):
        config.load(path)
        break

    config_args = config.section_to_args("ds4drv") + config.controllers()
    config_options = parser.parse_args(config_args)

    defaults, remaining_args = parser.parse_known_args(["--next-controller"])
    merge_options(config_options, options, defaults)

    controller_defaults = ControllerAction.default_controller()
    for idx, controller in enumerate(config_options.controllers):
        try:
            org_controller = options.controllers[idx]
            merge_options(controller, org_controller, controller_defaults)
        except IndexError:
            options.controllers.append(controller)

    options.profiles = {}
    for name, section in config.sections("profile"):
        args = config.section_to_args(section)
        profile_options = parser.parse_args(args)
        profile_options.parent = options
        options.profiles[name] = profile_options

    options.bindings = {}
    options.bindings["global"] = config.section("bindings",
                                                key_type=parse_button_combo)
    for name, section in config.sections("bindings"):
        options.bindings[name] = config.section(section,
                                                key_type=parse_button_combo)

    for name, section in config.sections("mapping"):
        mapping = config.section(section)
        for key, attr in mapping.items():
            if '#' in attr: # Remove tailing comments on the line
                attr = attr.split('#', 1)[0].rstrip()
                mapping[key] = attr
        parse_uinput_mapping(name, mapping)

    for controller in options.controllers:
        controller.parent = options

    options.default_controller = ControllerAction.default_controller()
    options.default_controller.parent = options

    return options


def add_controller_option(name, **options):
    option_name = name[2:].replace("-", "_")
    controllopt.add_argument(name, **options)
    ControllerAction.__options__.append(option_name)


add_controller_option("--profiles", metavar="profiles",
                      type=stringlist,
                      help="Profiles to cycle through using the button "
                           "specified by --profile-toggle, e.g. "
                           "'profile1,profile2'")


########NEW FILE########
__FILENAME__ = daemon
import atexit
import os
import sys

from signal import signal, SIGTERM

from .logger import Logger


class Daemon(object):
    logger = Logger()
    logger.set_level("info")
    logger_module = logger.new_module("daemon")

    @classmethod
    def fork(cls, logfile, pidfile):
        if os.path.exists(pidfile):
            cls.exit("ds4drv appears to already be running. Kill it "
                     "or remove {0} if it's not really running.", pidfile)

        cls.logger_module.info("Forking into background, writing log to {0}",
                               logfile)

        try:
            pid = os.fork()
        except OSError as err:
            cls.exit("Failed to fork: {0}", err)

        if pid == 0:
            os.setsid()

            try:
                pid = os.fork()
            except OSError as err:
                cls.exit("Failed to fork child process: {0}", err)

            if pid == 0:
                os.chdir("/")
                cls.open_log(logfile)
            else:
                sys.exit(0)
        else:
            sys.exit(0)

        cls.create_pid(pidfile)

    @classmethod
    def create_pid(cls, pidfile):
        @atexit.register
        def remove_pid():
            if os.path.exists(pidfile):
                os.remove(pidfile)

        signal(SIGTERM, lambda *a: sys.exit())

        try:
            with open(pidfile, "w") as fd:
                fd.write(str(os.getpid()))
        except OSError:
            pass

    @classmethod
    def open_log(cls, logfile):
        logfile = os.path.expanduser(logfile)
        dirname = os.path.dirname(logfile)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except OSError as err:
                cls.exit("Failed to open log file: {0} ({1})", logfile, err)

        try:
            output = open(logfile, "w")
        except OSError as err:
            cls.exit("Failed to open log file: {0} ({1})", logfile, err)

        cls.logger.set_output(output)

    @classmethod
    def exit(cls, *args, **kwargs):
        cls.logger_module.error(*args, **kwargs)
        sys.exit(1)

########NEW FILE########
__FILENAME__ = device
from struct import Struct
from sys import version_info as sys_version


class StructHack(Struct):
    """Python <2.7.4 doesn't support struct unpack from bytearray."""
    def unpack_from(self, buf, offset=0):
        buf = buffer(buf)

        return Struct.unpack_from(self, buf, offset)


if sys_version[0] == 2 and sys_version[1] <= 7 and sys_version[2] <= 4:
    S16LE = StructHack("<h")
else:
    S16LE = Struct("<h")


class DS4Report(object):
    __slots__ = ["left_analog_x",
                 "left_analog_y",
                 "right_analog_x",
                 "right_analog_y",
                 "l2_analog",
                 "r2_analog",
                 "dpad_up",
                 "dpad_down",
                 "dpad_left",
                 "dpad_right",
                 "button_cross",
                 "button_circle",
                 "button_square",
                 "button_triangle",
                 "button_l1",
                 "button_l2",
                 "button_l3",
                 "button_r1",
                 "button_r2",
                 "button_r3",
                 "button_share",
                 "button_options",
                 "button_trackpad",
                 "button_ps",
                 "motion_y",
                 "motion_x",
                 "motion_z",
                 "orientation_roll",
                 "orientation_yaw",
                 "orientation_pitch",
                 "trackpad_touch0_id",
                 "trackpad_touch0_active",
                 "trackpad_touch0_x",
                 "trackpad_touch0_y",
                 "trackpad_touch1_id",
                 "trackpad_touch1_active",
                 "trackpad_touch1_x",
                 "trackpad_touch1_y",
                 "timestamp",
                 "battery",
                 "plug_usb",
                 "plug_audio",
                 "plug_mic"]

    def __init__(self, *args, **kwargs):
        for i, value in enumerate(args):
            setattr(self, self.__slots__[i], value)


class DS4Device(object):
    """A DS4 controller object.

    Used to control the device functions and reading HID reports.
    """

    def __init__(self, device_name, device_addr, type):
        self.device_name = device_name
        self.device_addr = device_addr
        self.type = type

        self._led = (0, 0, 0)
        self._led_flash = (0, 0)
        self._led_flashing = False

        self.set_operational()

    def _control(self, **kwargs):
        self.control(led_red=self._led[0], led_green=self._led[1],
                     led_blue=self._led[2], flash_led1=self._led_flash[0],
                     flash_led2=self._led_flash[1], **kwargs)

    def rumble(self, small=0, big=0):
        """Sets the intensity of the rumble motors. Valid range is 0-255."""
        self._control(small_rumble=small, big_rumble=big)

    def set_led(self, red=0, green=0, blue=0):
        """Sets the LED color. Values are RGB between 0-255."""
        self._led = (red, green, blue)
        self._control()

    def start_led_flash(self, on, off):
        """Starts flashing the LED."""
        if not self._led_flashing:
            self._led_flash = (on, off)
            self._led_flashing = True
            self._control()

    def stop_led_flash(self):
        """Stops flashing the LED."""
        if self._led_flashing:
            self._led_flash = (0, 0)
            self._led_flashing = False
            # Call twice, once to stop flashing...
            self._control()
            # ...and once more to make sure the LED is on.
            self._control()

    def control(self, big_rumble=0, small_rumble=0,
                led_red=0, led_green=0, led_blue=0,
                flash_led1=0, flash_led2=0):
        if self.type == "bluetooth":
            pkt = bytearray(77)
            pkt[0] = 128
            pkt[2] = 255
            offset = 2
            report_id = 0x11

        elif self.type == "usb":
            pkt = bytearray(31)
            pkt[0] = 255
            offset = 0
            report_id = 0x05

        # Rumble
        pkt[offset+3] = min(small_rumble, 255)
        pkt[offset+4] = min(big_rumble, 255)

        # LED (red, green, blue)
        pkt[offset+5] = min(led_red, 255)
        pkt[offset+6] = min(led_green, 255)
        pkt[offset+7] = min(led_blue, 255)

        # Time to flash bright (255 = 2.5 seconds)
        pkt[offset+8] = min(flash_led1, 255)

        # Time to flash dark (255 = 2.5 seconds)
        pkt[offset+9] = min(flash_led2, 255)

        self.write_report(report_id, pkt)

    def parse_report(self, buf):
        """Parse a buffer containing a HID report."""
        dpad = buf[5] % 16

        return DS4Report(
            # Left analog stick
            buf[1], buf[2],

            # Right analog stick
            buf[3], buf[4],

            # L2 and R2 analog
            buf[8], buf[9],

            # DPad up, down, left, right
            (dpad in (0, 1, 7)), (dpad in (3, 4, 5)),
            (dpad in (5, 6, 7)), (dpad in (1, 2, 3)),

            # Buttons cross, circle, square, triangle
            (buf[5] & 32) != 0, (buf[5] & 64) != 0,
            (buf[5] & 16) != 0, (buf[5] & 128) != 0,

            # L1, L2 and L3 buttons
            (buf[6] & 1) != 0, (buf[6] & 4) != 0, (buf[6] & 64) != 0,

            # R1, R2,and R3 buttons
            (buf[6] & 2) != 0, (buf[6] & 8) != 0, (buf[6] & 128) != 0,

            # Share and option buttons
            (buf[6] & 16) != 0, (buf[6] & 32) != 0,

            # Trackpad and PS buttons
            (buf[7] & 2) != 0, (buf[7] & 1) != 0,

            # Acceleration
            S16LE.unpack_from(buf, 13)[0],
            S16LE.unpack_from(buf, 15)[0],
            S16LE.unpack_from(buf, 17)[0],

            # Orientation
            -(S16LE.unpack_from(buf, 19)[0]),
            S16LE.unpack_from(buf, 21)[0],
            S16LE.unpack_from(buf, 23)[0],

            # Trackpad touch 1: id, active, x, y
            buf[35] & 0x7f, (buf[35] >> 7) == 0,
            ((buf[37] & 0x0f) << 8) | buf[36],
            buf[38] << 4 | ((buf[37] & 0xf0) >> 4),

            # Trackpad touch 2: id, active, x, y
            buf[39] & 0x7f, (buf[39] >> 7) == 0,
            ((buf[41] & 0x0f) << 8) | buf[40],
            buf[42] << 4 | ((buf[41] & 0xf0) >> 4),

            # Timestamp and battery
            buf[7] >> 2,
            buf[30] % 16,

            # External inputs (usb, audio, mic)
            (buf[30] & 16) != 0, (buf[30] & 32) != 0,
            (buf[30] & 64) != 0
        )

    def read_report(self):
        """Read and parse a HID report."""
        pass

    def write_report(self, report_id, data):
        """Writes a HID report to the control channel."""
        pass

    def set_operational(self):
        """Tells the DS4 controller we want full HID reports."""
        pass

    def close(self):
        """Disconnects from the device."""
        pass

    @property
    def name(self):
        if self.type == "bluetooth":
            type_name = "Bluetooth"
        elif self.type == "usb":
            type_name = "USB"

        return "{0} Controller ({1})".format(type_name, self.device_name)

########NEW FILE########
__FILENAME__ = eventloop
import os

from collections import defaultdict, deque
from functools import wraps
from select import epoll, EPOLLIN

from .packages import timerfd
from .utils import iter_except


class Timer(object):
    """Simple interface around a timerfd connected to a event loop."""

    def __init__(self, loop, interval, callback):
        self.callback = callback
        self.interval = interval
        self.loop = loop
        self.timer = timerfd.create(timerfd.CLOCK_MONOTONIC)

    def start(self, *args, **kwargs):
        """Starts the timer.

        If the callback returns True the timer will be restarted.
        """

        @wraps(self.callback)
        def callback():
            os.read(self.timer, 8)
            repeat = self.callback(*args, **kwargs)
            if not repeat:
                self.stop()

        spec = timerfd.itimerspec(self.interval, self.interval)
        timerfd.settime(self.timer, 0, spec)

        self.loop.remove_watcher(self.timer)
        self.loop.add_watcher(self.timer, callback)

    def stop(self):
        """Stops the timer if it's running."""
        self.loop.remove_watcher(self.timer)


class EventLoop(object):
    """Basic IO, event and timer loop with callbacks."""

    def __init__(self):
        self.stop()

    def create_timer(self, interval, callback):
        """Creates a timer."""

        return Timer(self, interval, callback)

    def add_watcher(self, fd, callback):
        """Starts watching a non-blocking fd for data."""

        if not isinstance(fd, int):
            fd = fd.fileno()

        self.callbacks[fd] = callback
        self.epoll.register(fd, EPOLLIN)

    def remove_watcher(self, fd):
        """Stops watching a fd."""
        if not isinstance(fd, int):
            fd = fd.fileno()

        if fd not in self.callbacks:
            return

        self.callbacks.pop(fd, None)
        self.epoll.unregister(fd)

    def register_event(self, event, callback):
        """Registers a handler for an event."""
        self.event_callbacks[event].add(callback)

    def unregister_event(self, event, callback):
        """Unregisters a event handler."""
        self.event_callbacks[event].remove(callback)

    def fire_event(self, event, *args, **kwargs):
        """Fires a event."""
        self.event_queue.append((event, args))
        self.process_events()

    def process_events(self):
        """Processes any events in the queue."""
        for event, args in iter_except(self.event_queue.popleft, IndexError):
            for callback in self.event_callbacks[event]:
                callback(*args)

    def run(self):
        """Starts the loop."""
        self.running = True
        while self.running:
            for fd, event in self.epoll.poll():
                callback = self.callbacks.get(fd)
                if callback:
                    callback()

    def stop(self):
        """Stops the loop."""
        self.running = False
        self.callbacks = {}
        self.epoll = epoll()

        self.event_queue = deque()
        self.event_callbacks = defaultdict(set)


########NEW FILE########
__FILENAME__ = exceptions
class BackendError(Exception):
    """Backend related errors."""

class DeviceError(Exception):
    """Device related errors."""

########NEW FILE########
__FILENAME__ = logger
import sys

from threading import Lock


LEVELS = ["none", "error", "warning", "info"]
FORMAT = "[{level}][{module}] {msg}\n"


class Logger(object):
    def __init__(self):
        self.output = sys.stdout
        self.level = 0
        self.lock = Lock()

    def new_module(self, module):
        return LoggerModule(self, module)

    def set_level(self, level):
        try:
            index = LEVELS.index(level)
        except ValueError:
            return

        self.level = index

    def set_output(self, output):
        self.output = output

    def msg(self, module, level, msg, *args, **kwargs):
        if self.level < level or level > len(LEVELS):
            return

        msg = str(msg).format(*args, **kwargs)

        with self.lock:
            self.output.write(FORMAT.format(module=module,
                                            level=LEVELS[level],
                                            msg=msg))
            if hasattr(self.output, "flush"):
                self.output.flush()


class LoggerModule(object):
    def __init__(self, manager, module):
        self.manager = manager
        self.module = module

    def error(self, msg, *args, **kwargs):
        self.manager.msg(self.module, 1, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.manager.msg(self.module, 2, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.manager.msg(self.module, 3, msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.manager.msg(self.module, 4, msg, *args, **kwargs)

########NEW FILE########
__FILENAME__ = timerfd
"""
Copyright (c) 2010  Timo Savola <timo.savola@iki.fi>

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

__all__ = [
	"CLOEXEC",
	"NONBLOCK",

	"TIMER_ABSTIME",

	"CLOCK_REALTIME",
	"CLOCK_MONOTONIC",

	"bufsize",

	"timespec",
	"itimerspec",

	"create",
	"settime",
	"gettime",
	"unpack",
]

import ctypes
import ctypes.util
import math
import os
import struct

CLOEXEC         = 0o02000000
NONBLOCK        = 0o00004000

TIMER_ABSTIME   = 0x00000001

CLOCK_REALTIME  = 0
CLOCK_MONOTONIC = 1

bufsize         = 8

libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

class timespec(ctypes.Structure):

	_fields_ = [
		("tv_sec",      libc.time.restype),
		("tv_nsec",     ctypes.c_long),
	]

	def __init__(self, time=None):
		ctypes.Structure.__init__(self)

		if time is not None:
			self.set_time(time)

	def __repr__(self):
		return "timerfd.timespec(%s)" % self.get_time()

	def set_time(self, time):
		fraction, integer = math.modf(time)

		self.tv_sec = int(integer)
		self.tv_nsec = int(fraction * 1000000000)

	def get_time(self):
		if self.tv_nsec:
			return self.tv_sec + self.tv_nsec / 1000000000.0
		else:
			return self.tv_sec

class itimerspec(ctypes.Structure):

	_fields_ = [
		("it_interval", timespec),
		("it_value",    timespec),
	]

	def __init__(self, interval=None, value=None):
		ctypes.Structure.__init__(self)

		if interval is not None:
			self.it_interval.set_time(interval)

		if value is not None:
			self.it_value.set_time(value)

	def __repr__(self):
		items = [("interval", self.it_interval), ("value", self.it_value)]
		args = ["%s=%s" % (name, value.get_time()) for name, value in items]
		return "timerfd.itimerspec(%s)" % ", ".join(args)

	def set_interval(self, time):
		self.it_interval.set_time(time)

	def get_interval(self):
		return self.it_interval.get_time()

	def set_value(self, time):
		self.it_value.set_time(time)

	def get_value(self):
		return self.it_value.get_time()

def errcheck(result, func, arguments):
	if result < 0:
		errno = ctypes.get_errno()
		raise OSError(errno, os.strerror(errno))

	return result

libc.timerfd_create.argtypes = [ctypes.c_int, ctypes.c_int]
libc.timerfd_create.errcheck = errcheck

libc.timerfd_settime.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(itimerspec), ctypes.POINTER(itimerspec)]
libc.timerfd_settime.errcheck = errcheck

libc.timerfd_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(itimerspec)]
libc.timerfd_gettime.errcheck = errcheck

def create(clock_id, flags=0):
	return libc.timerfd_create(clock_id, flags)

def settime(ufd, flags, new_value):
	old_value = itimerspec()
	libc.timerfd_settime(ufd, flags, ctypes.pointer(new_value), ctypes.pointer(old_value))
	return old_value

def gettime(ufd):
	curr_value = itimerspec()
	libc.timerfd_gettime(ufd, ctypes.pointer(curr_value))
	return curr_value

def unpack(buf):
	count, = struct.unpack("Q", buf[:bufsize])
	return count

########NEW FILE########
__FILENAME__ = uinput
import os.path
import time

from collections import namedtuple

from evdev import UInput, UInputError, ecodes

from .exceptions import DeviceError

BUTTON_MODIFIERS = ("+", "-")

DEFAULT_A2D_DEADZONE = 50
DEFAULT_AXIS_OPTIONS = (0, 255, 0, 5)
DEFAULT_MOUSE_SENSITIVTY = 0.6
DEFAULT_MOUSE_DEADZONE = 5
DEFAULT_SCROLL_REPEAT_DELAY = .250 # Seconds to wait before continual scrolling
DEFAULT_SCROLL_DELAY = .035        # Seconds to wait between scroll events

UInputMapping = namedtuple("UInputMapping",
                           "name bustype vendor product version "
                           "axes axes_options buttons hats keys mouse "
                           "mouse_options")

_mappings = {}

# Add our simulated mousewheel codes
ecodes.REL_WHEELUP = 13      # Unique value for this lib
ecodes.REL_WHEELDOWN = 14    # Ditto


def parse_button(attr):
    if attr[0] in BUTTON_MODIFIERS:
        modifier = attr[0]
        attr = attr[1:]
    else:
        modifier = None

    return (attr, modifier)


def create_mapping(name, description, bustype=0, vendor=0, product=0,
                   version=0, axes={}, axes_options={}, buttons={},
                   hats={}, keys={}, mouse={}, mouse_options={}):
    axes = {getattr(ecodes, k): v for k,v in axes.items()}
    axes_options = {getattr(ecodes, k): v for k,v in axes_options.items()}
    buttons = {getattr(ecodes, k): parse_button(v) for k,v in buttons.items()}
    hats = {getattr(ecodes, k): v for k,v in hats.items()}
    mouse = {getattr(ecodes, k): v for k,v in mouse.items()}

    mapping = UInputMapping(description, bustype, vendor, product, version,
                            axes, axes_options, buttons, hats, keys, mouse,
                            mouse_options)
    _mappings[name] = mapping


# Pre-configued mappings
create_mapping(
    "ds4", "Sony Computer Entertainment Wireless Controller",
    # Bus type,     vendor, product, version
    ecodes.BUS_USB, 1356,   1476,    273,
    # Axes
    {
        "ABS_X":        "left_analog_x",
        "ABS_Y":        "left_analog_y",
        "ABS_Z":        "right_analog_x",
        "ABS_RZ":       "right_analog_y",
        "ABS_RX":       "l2_analog",
        "ABS_RY":       "r2_analog",
        "ABS_THROTTLE": "orientation_roll",
        "ABS_RUDDER":   "orientation_pitch",
        "ABS_WHEEL":    "orientation_yaw",
        "ABS_DISTANCE": "motion_z",
        "ABS_TILT_X":   "motion_x",
        "ABS_TILT_Y":   "motion_y",
    },
    # Axes options
    {
        "ABS_THROTTLE": (-16385, 16384, 0, 0),
        "ABS_RUDDER":   (-16385, 16384, 0, 0),
        "ABS_WHEEL":    (-16385, 16384, 0, 0),
        "ABS_DISTANCE": (-32768, 32767, 0, 10),
        "ABS_TILT_X":   (-32768, 32767, 0, 10),
        "ABS_TILT_Y":   (-32768, 32767, 0, 10),
    },
    # Buttons
    {
        "BTN_TR2":    "button_options",
        "BTN_MODE":   "button_ps",
        "BTN_TL2":    "button_share",
        "BTN_B":      "button_cross",
        "BTN_C":      "button_circle",
        "BTN_A":      "button_square",
        "BTN_X":      "button_triangle",
        "BTN_Y":      "button_l1",
        "BTN_Z":      "button_r1",
        "BTN_TL":     "button_l2",
        "BTN_TR":     "button_r2",
        "BTN_SELECT": "button_l3",
        "BTN_START":  "button_r3",
        "BTN_THUMBL": "button_trackpad"
    },
    # Hats
    {
        "ABS_HAT0X": ("dpad_left", "dpad_right"),
        "ABS_HAT0Y": ("dpad_up", "dpad_down")
    }
)

create_mapping(
    "xboxdrv", "Xbox Gamepad (userspace driver)",
    # Bus type, vendor, product, version
    0,          0,      0,       0,
    # Axes
    {
        "ABS_X":     "left_analog_x",
        "ABS_Y":     "left_analog_y",
        "ABS_RX":    "right_analog_x",
        "ABS_RY":    "right_analog_y",
        "ABS_BRAKE": "l2_analog",
        "ABS_GAS":   "r2_analog"
    },
    # Axes settings
    {},
    #Buttons
    {
        "BTN_START":  "button_options",
        "BTN_MODE":   "button_ps",
        "BTN_SELECT": "button_share",
        "BTN_A":      "button_cross",
        "BTN_B":      "button_circle",
        "BTN_X":      "button_square",
        "BTN_Y":      "button_triangle",
        "BTN_TL":     "button_l1",
        "BTN_TR":     "button_r1",
        "BTN_THUMBL": "button_l3",
        "BTN_THUMBR": "button_r3"
    },
    # Hats
    {
        "ABS_HAT0X": ("dpad_left", "dpad_right"),
        "ABS_HAT0Y": ("dpad_up", "dpad_down")
    }
)

create_mapping(
    "xpad", "Microsoft X-Box 360 pad",
    # Bus type,      vendor, product, version
    ecodes.BUS_USB,  1118,   654,     272,
    # Axes
    {
        "ABS_X":  "left_analog_x",
        "ABS_Y":  "left_analog_y",
        "ABS_RX": "right_analog_x",
        "ABS_RY": "right_analog_y",
        "ABS_Z":  "l2_analog",
        "ABS_RZ": "r2_analog"
    },
    # Axes settings
    {},
    #Buttons
    {
        "BTN_START":  "button_options",
        "BTN_MODE":   "button_ps",
        "BTN_SELECT": "button_share",
        "BTN_A":      "button_cross",
        "BTN_B":      "button_circle",
        "BTN_X":      "button_square",
        "BTN_Y":      "button_triangle",
        "BTN_TL":     "button_l1",
        "BTN_TR":     "button_r1",
        "BTN_THUMBL": "button_l3",
        "BTN_THUMBR": "button_r3"
    },
    # Hats
    {
        "ABS_HAT0X": ("dpad_left", "dpad_right"),
        "ABS_HAT0Y": ("dpad_up", "dpad_down")
    }
)

create_mapping(
    "xpad_wireless", "Xbox 360 Wireless Receiver",
    # Bus type,      vendor, product, version
    ecodes.BUS_USB,  1118,   1817,    256,
    # Axes
    {
        "ABS_X":  "left_analog_x",
        "ABS_Y":  "left_analog_y",
        "ABS_RX": "right_analog_x",
        "ABS_RY": "right_analog_y",
        "ABS_Z":  "l2_analog",
        "ABS_RZ": "r2_analog"
    },
    # Axes settings
    {},
    #Buttons
    {
        "BTN_START":  "button_options",
        "BTN_MODE":   "button_ps",
        "BTN_SELECT": "button_share",
        "BTN_A":      "button_cross",
        "BTN_B":      "button_circle",
        "BTN_X":      "button_square",
        "BTN_Y":      "button_triangle",
        "BTN_TL":     "button_l1",
        "BTN_TR":     "button_r1",
        "BTN_THUMBL": "button_l3",
        "BTN_THUMBR": "button_r3",

        "BTN_TRIGGER_HAPPY1": "dpad_left",
        "BTN_TRIGGER_HAPPY2": "dpad_right",
        "BTN_TRIGGER_HAPPY3": "dpad_up",
        "BTN_TRIGGER_HAPPY4": "dpad_down",
    },
)

create_mapping(
    "mouse", "DualShock4 Mouse Emulation",
    buttons={
        "BTN_LEFT": "button_trackpad",
    },
    mouse={
        "REL_X": "trackpad_touch0_x",
        "REL_Y": "trackpad_touch0_y"
    },
)


class UInputDevice(object):
    def __init__(self, layout):
        self.joystick_dev = None
        self.evdev_dev = None
        self.ignored_buttons = set()
        self.create_device(layout)

        self._write_cache = {}
        self._scroll_details = {}

    def create_device(self, layout):
        """Creates a uinput device using the specified layout."""
        events = {ecodes.EV_ABS: [], ecodes.EV_KEY: [],
                  ecodes.EV_REL: []}

        # Joystick device
        if layout.axes or layout.buttons or layout.hats:
            self.joystick_dev = next_joystick_device()

        for name in layout.axes:
            params = layout.axes_options.get(name, DEFAULT_AXIS_OPTIONS)
            events[ecodes.EV_ABS].append((name, params))

        for name in layout.hats:
            params = (-1, 1, 0, 0)
            events[ecodes.EV_ABS].append((name, params))

        for name in layout.buttons:
            events[ecodes.EV_KEY].append(name)

        if layout.mouse:
            self.mouse_pos = {}
            self.mouse_rel = {}
            self.mouse_analog_sensitivity = float(
                layout.mouse_options.get("MOUSE_SENSITIVITY",
                                         DEFAULT_MOUSE_SENSITIVTY)
            )
            self.mouse_analog_deadzone = int(
                layout.mouse_options.get("MOUSE_DEADZONE",
                                         DEFAULT_MOUSE_DEADZONE)
            )
            self.scroll_repeat_delay = float(
                layout.mouse_options.get("MOUSE_SCROLL_REPEAT_DELAY",
                                         DEFAULT_SCROLL_REPEAT_DELAY)
            )
            self.scroll_delay = float(
                layout.mouse_options.get("MOUSE_SCROLL_DELAY",
                                         DEFAULT_SCROLL_DELAY)
            )

            for name in layout.mouse:
                if name in (ecodes.REL_WHEELUP, ecodes.REL_WHEELDOWN):
                    if ecodes.REL_WHEEL not in events[ecodes.EV_REL]:
                        # This ensures that scroll wheel events can work
                        events[ecodes.EV_REL].append(ecodes.REL_WHEEL)
                else:
                    events[ecodes.EV_REL].append(name)
                self.mouse_rel[name] = 0.0

        self.device = UInput(name=layout.name, events=events,
                             bustype=layout.bustype, vendor=layout.vendor,
                             product=layout.product, version=layout.version)
        self.layout = layout

    def write_event(self, etype, code, value):
        """Writes a event to the device, if it has changed."""
        last_value = self._write_cache.get(code)
        if last_value != value:
            self.device.write(etype, code, value)
            self._write_cache[code] = value

    def emit(self, report):
        """Writes axes, buttons and hats with values from the report to
        the device."""
        for name, attr in self.layout.axes.items():
            value = getattr(report, attr)
            self.write_event(ecodes.EV_ABS, name, value)

        for name, attr in self.layout.buttons.items():
            attr, modifier = attr

            if attr in self.ignored_buttons:
                value = False
            else:
                value = getattr(report, attr)

            if modifier and "analog" in attr:
                if modifier == "+":
                    value = value > (128 + DEFAULT_A2D_DEADZONE)
                elif modifier == "-":
                    value = value < (128 - DEFAULT_A2D_DEADZONE)

            self.write_event(ecodes.EV_KEY, name, value)

        for name, attr in self.layout.hats.items():
            if getattr(report, attr[0]):
                value = -1
            elif getattr(report, attr[1]):
                value = 1
            else:
                value = 0

            self.write_event(ecodes.EV_ABS, name, value)

        self.device.syn()

    def emit_reset(self):
        """Resets the device to a blank state."""
        for name in self.layout.axes:
            params = self.layout.axes_options.get(name, DEFAULT_AXIS_OPTIONS)
            self.write_event(ecodes.EV_ABS, name, int(sum(params[:2]) / 2))

        for name in self.layout.buttons:
            self.write_event(ecodes.EV_KEY, name, False)

        for name in self.layout.hats:
            self.write_event(ecodes.EV_ABS, name, 0)

        self.device.syn()

    def emit_mouse(self, report):
        """Calculates relative mouse values from a report and writes them."""
        for name, attr in self.layout.mouse.items():
            if attr.startswith("trackpad_touch"):
                active_attr = attr[:16] + "active"
                if not getattr(report, active_attr):
                    self.mouse_pos.pop(name, None)
                    continue

                pos = getattr(report, attr)
                if name not in self.mouse_pos:
                    self.mouse_pos[name] = pos

                sensitivity = 0.5
                self.mouse_rel[name] += (pos - self.mouse_pos[name]) * sensitivity
                self.mouse_pos[name] = pos

            elif "analog" in attr:
                pos = getattr(report, attr)
                if (pos > (128 + self.mouse_analog_deadzone)
                    or pos < (128 - self.mouse_analog_deadzone)):
                    accel = (pos - 128) / 10
                else:
                    continue

                sensitivity = self.mouse_analog_sensitivity
                self.mouse_rel[name] += accel * sensitivity

            # Emulate mouse wheel (needs special handling)
            if name in (ecodes.REL_WHEELUP, ecodes.REL_WHEELDOWN):
                ecode = ecodes.REL_WHEEL # The real event we need to emit
                write = False
                if getattr(report, attr):
                    self._scroll_details['direction'] = name
                    now = time.time()
                    last_write = self._scroll_details.get('last_write')
                    if not last_write:
                        # No delay for the first button press for fast feedback
                        write = True
                        self._scroll_details['count'] = 0
                    if name == ecodes.REL_WHEELUP:
                        value = 1
                    elif name == ecodes.REL_WHEELDOWN:
                        value = -1
                    if last_write:
                        # Delay at least one cycle before continual scrolling
                        if self._scroll_details['count'] > 1:
                            if now - last_write > self.scroll_delay:
                                write = True
                        elif now - last_write > self.scroll_repeat_delay:
                            write = True
                    if write:
                        self.device.write(ecodes.EV_REL, ecode, value)
                        self._scroll_details['last_write'] = now
                        self._scroll_details['count'] += 1
                        continue # No need to proceed further
                else:
                    # Reset so you can quickly tap the button to scroll
                    if self._scroll_details.get('direction') == name:
                        self._scroll_details['last_write'] = 0
                        self._scroll_details['count'] = 0

            rel = int(self.mouse_rel[name])
            self.mouse_rel[name] = self.mouse_rel[name] - rel
            self.device.write(ecodes.EV_REL, name, rel)

        self.device.syn()


def create_uinput_device(mapping):
    """Creates a uinput device."""
    if mapping not in _mappings:
        raise DeviceError("Unknown device mapping: {0}".format(mapping))

    try:
        mapping = _mappings[mapping]
        device = UInputDevice(mapping)
    except UInputError as err:
        raise DeviceError(err)

    return device


def parse_uinput_mapping(name, mapping):
    """Parses a dict of mapping options."""
    axes, buttons, mouse, mouse_options = {}, {}, {}, {}
    description = "ds4drv custom mapping ({0})".format(name)

    for key, attr in mapping.items():
        key = key.upper()
        if key.startswith("BTN_") or key.startswith("KEY_"):
            buttons[key] = attr
        elif key.startswith("ABS_"):
            axes[key] = attr
        elif key.startswith("REL_"):
            mouse[key] = attr
        elif key.startswith("MOUSE_"):
            mouse_options[key] = attr

    create_mapping(name, description, axes=axes, buttons=buttons,
                   mouse=mouse, mouse_options=mouse_options)


def next_joystick_device():
    """Finds the next available js device name."""
    for i in range(100):
        dev = "/dev/input/js{0}".format(i)
        if not os.path.exists(dev):
            return dev

########NEW FILE########
__FILENAME__ = utils
import sys

from .device import DS4Report


VALID_BUTTONS = DS4Report.__slots__


def iter_except(func, exception, first=None):
    """Call a function repeatedly until an exception is raised.

    Converts a call-until-exception interface to an iterator interface.
    Like __builtin__.iter(func, sentinel) but uses an exception instead
    of a sentinel to end the loop.
    """
    try:
        if first is not None:
            yield first()
        while True:
            yield func()
    except exception:
        pass


def parse_button_combo(combo, sep="+"):
    def button_prefix(button):
        button = button.strip()
        if button in ("up", "down", "left", "right"):
            prefix = "dpad_"
        else:
            prefix = "button_"

        if prefix + button not in VALID_BUTTONS:
            raise ValueError("Invalid button: {0}".format(button))

        return prefix + button

    return tuple(map(button_prefix, combo.lower().split(sep)))


def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})


def zero_copy_slice(buf, start=None, end=None):
    # No need for an extra copy on Python 3.3+
    if sys.version_info[0] == 3 and sys.version_info[1] >= 3:
        buf = memoryview(buf)

    return buf[start:end]

########NEW FILE########
__FILENAME__ = __main__
import sys

from threading import Thread

from .actions import ActionRegistry
from .backends import BluetoothBackend, HidrawBackend
from .config import load_options
from .daemon import Daemon
from .eventloop import EventLoop
from .exceptions import BackendError


class DS4Controller(object):
    def __init__(self, index, options, dynamic=False):
        self.index = index
        self.dynamic = dynamic
        self.logger = Daemon.logger.new_module("controller {0}".format(index))

        self.error = None
        self.device = None
        self.loop = EventLoop()

        self.actions = [cls(self) for cls in ActionRegistry.actions]
        self.bindings = options.parent.bindings
        self.current_profile = "default"
        self.default_profile = options
        self.options = self.default_profile
        self.profiles = options.profiles
        self.profile_options = dict(options.parent.profiles)
        self.profile_options["default"] = self.default_profile

        if self.profiles:
            self.profiles.append("default")

        self.load_options(self.options)

    def fire_event(self, event, *args):
        self.loop.fire_event(event, *args)

    def load_profile(self, profile):
        if profile == self.current_profile:
            return

        profile_options = self.profile_options.get(profile)
        if profile_options:
            self.logger.info("Switching to profile: {0}", profile)
            self.load_options(profile_options)
            self.current_profile = profile
            self.fire_event("load-profile", profile)
        else:
            self.logger.warning("Ignoring invalid profile: {0}", profile)

    def next_profile(self):
        if not self.profiles:
            return

        next_index = self.profiles.index(self.current_profile) + 1
        if next_index >= len(self.profiles):
            next_index = 0

        self.load_profile(self.profiles[next_index])

    def prev_profile(self):
        if not self.profiles:
            return

        next_index = self.profiles.index(self.current_profile) - 1
        if next_index < 0:
            next_index = len(self.profiles) - 1

        self.load_profile(self.profiles[next_index])

    def setup_device(self, device):
        self.logger.info("Connected to {0}", device.name)

        self.device = device
        self.device.set_led(*self.options.led)
        self.fire_event("device-setup", device)
        self.loop.add_watcher(device.report_fd, self.read_report)
        self.load_options(self.options)

    def cleanup_device(self):
        self.logger.info("Disconnected")
        self.fire_event("device-cleanup")
        self.loop.remove_watcher(self.device.report_fd)
        self.device.close()
        self.device = None

        if self.dynamic:
            self.loop.stop()

    def load_options(self, options):
        self.fire_event("load-options", options)
        self.options = options

    def read_report(self):
        report = self.device.read_report()

        if not report:
            if report is False:
                return

            self.cleanup_device()
            return

        self.fire_event("device-report", report)

    def run(self):
        self.loop.run()

    def exit(self, *args):
        if self.device:
            self.cleanup_device()

        self.logger.error(*args)
        self.error = True


def create_controller_thread(index, controller_options, dynamic=False):
    controller = DS4Controller(index, controller_options, dynamic=dynamic)

    thread = Thread(target=controller.run)
    thread.daemon = True
    thread.controller = controller
    thread.start()

    return thread


def main():
    try:
        options = load_options()
    except ValueError as err:
        Daemon.exit("Failed to parse options: {0}", err)

    if options.hidraw:
        backend = HidrawBackend(Daemon.logger)
    else:
        backend = BluetoothBackend(Daemon.logger)

    try:
        backend.setup()
    except BackendError as err:
        Daemon.exit(err)

    if options.daemon:
        Daemon.fork(options.daemon_log, options.daemon_pid)

    threads = []
    for index, controller_options in enumerate(options.controllers):
        thread = create_controller_thread(index + 1, controller_options)
        threads.append(thread)

    for device in backend.devices:
        connected_devices = []
        for thread in threads:
            # Controller has received a fatal error, exit
            if thread.controller.error:
                sys.exit(1)

            if thread.controller.device:
                connected_devices.append(thread.controller.device.device_addr)

            # Clean up dynamic threads
            if not thread.is_alive():
                threads.remove(thread)

        if device.device_addr in connected_devices:
            backend.logger.warning("Ignoring already connected device: {0}",
                                   device.device_addr)
            continue

        for thread in filter(lambda t: not t.controller.device, threads):
            break
        else:
            thread = create_controller_thread(len(threads) + 1,
                                              options.default_controller,
                                              dynamic=True)
            threads.append(thread)

        thread.controller.setup_device(device)

if __name__ == "__main__":
    main()

########NEW FILE########
