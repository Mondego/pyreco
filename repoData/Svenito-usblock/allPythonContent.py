__FILENAME__ = install_requirements
from __future__ import unicode_literals, print_function

import sys
import os


def get_requirements_file_path():
    """Returns the absolute path to the correct requirements file."""
    directory = os.path.dirname(__file__)

    requirements_file = 'requirements.txt'

    return os.path.join(directory, requirements_file)


def main():
    requirements_file = get_requirements_file_path()
    print('Installing requirements from %s' % requirements_file)
    os.system('pip install -r %s --use-mirrors' % requirements_file)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_registrar
import os
import nose
from nose.tools import *

from usblock import registrar

CONFIG_FILE = "./test.conf"
CONFIG_CONTENTS = ("[device1]\n"
                   "devicelabel = TEST\n"
                   "devicesize = 249500160\n"
                   "deviceid = storage")


def setup_func():
    with open(CONFIG_FILE, 'w') as f:
        f.write(CONFIG_CONTENTS)


def teardown_func():
    os.unlink(CONFIG_FILE)


@with_setup(setup_func, teardown_func)
def test_load_config():
    r = registrar.Registrar(CONFIG_FILE)
    r.load_config()

    eq_(len(r.devices), 1)
    eq_(r.devices[0].uuid, "storage")
    eq_(r.devices[0].size, "249500160")
    eq_(r.devices[0].label, "TEST")


def test_write_config():
    r = registrar.Registrar(CONFIG_FILE)
    d = registrar.Device("new", "12345", "label")

    # Writes automatically
    r.add_device(d)

    new_r = registrar.Registrar(CONFIG_FILE)
    new_r.load_config()

    eq_(len(r.devices), 1)
    eq_(r.devices[0].uuid, "new")
    eq_(r.devices[0].size, "12345")
    eq_(r.devices[0].label, "label")
    os.unlink(CONFIG_FILE)


@with_setup(setup_func, teardown_func)
def test_validate():
    r = registrar.Registrar(CONFIG_FILE)
    r_blank = registrar.Registrar(CONFIG_FILE)
    r.load_config()

    d = registrar.Device("storage", "249500160", "TEST")
    d_fail = registrar.Device("stoadrage", "2495500160", "3TEST")

    assert(r.verify_device(d))
    assert(not r.verify_device(d_fail))
    assert(not r_blank.verify_device(d))


########NEW FILE########
__FILENAME__ = listener
import os
import sys
import dbus
import signal
import gobject
import subprocess
from dbus.mainloop.glib import DBusGMainLoop

from .registrar import Device
from .logger import logger


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif cmp(default, "yes") == 0:
        prompt = " [Y/n] "
    elif cmp(default, "no") == 0:
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


class Listener(object):
    '''Base class that listens to device insertion and removal
    and manages device adding/removing
    '''
    def __init__(self, registrar):
        self.registrar = registrar
        self._add_device = False
        self._device_udi = None
        self._adding_device = False

    def add_device(self):
        '''Begin adding a device procedure
        '''
        self._adding_device = True
        print("Please (re)insert the device you want to register.")

    def list_devices(self):
        '''List all registered devices
        '''
        devices = self.registrar.devices
        if not devices:
            print("There are currently no registered devices.")
            return

        print("These are the currently registered devices:")
        for num, device in enumerate(devices, start=1):
            print ("%d) Label: %s\n\t ID: %s" %
                  (num, device.label, device.uuid))

    def remove_device(self):
        '''List known devices and allow user to select one
        to remove
        '''
        devices = self.registrar.devices
        if not devices:
            print("No devices to remove.")
            return

        print("Select a device to remove:")
        self.list_devices()
        while True:
            choice = raw_input("Enter number to remove: ")
            try:
                choice = int(choice)
            except ValueError:
                print("Invalid choice.")
                continue

            if 0 < choice <= len(devices):
                if query_yes_no("You are about to remove device %d. Is this OK?"
                                % (choice)):
                    del devices[choice - 1]
            else:
                print("Invalid choice,")
                continue

            if not devices:
                break

            if not query_yes_no("Remove another?"):
                break

        self.registrar.devices = devices
        self.registrar.write_config()

    def listen(self):
        '''Starts listening for inserted devices
        Needs to be implemented in derived class
        '''

    def _register_device(self, device):
        '''Take device details of inserted device and guide user
        through adding it to known devices
        '''
        if device.uuid in [d.uuid for d in self.registrar.devices]:
            print ("Device %s with ID %s already registered." %
                  (device.label, device.uuid))
            if not query_yes_no("Would you like to add another device?"):
                return False
            else:
                print("Please insert another device.")
            return True

        print ("You are about to add device %s with ID %s." %
              (device.label, device.uuid))

        if not query_yes_no("Is this OK?"):
            return False

        self.registrar.add_device(device)

        print("Device added successfully.")
        return False


class LinuxListener(Listener):
    '''Specialised listener for Linux based systems that support
    dbus implementation
    '''
    def __init__(self, registrar):
        super(LinuxListener, self).__init__(registrar)
        self._loop = None
        self._xlock_pid = 0

    def listen(self):
        '''Starts listening for inserted devices
        '''
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        hal_manager_obj = bus.get_object(
            "org.freedesktop.Hal",
            "/org/freedesktop/Hal/Manager")

        hal_manager = dbus.Interface(hal_manager_obj,
                                     "org.freedesktop.Hal.Manager")

        hal_manager.connect_to_signal("DeviceAdded", self._add_event)
        hal_manager.connect_to_signal("DeviceRemoved", self._remove_event)

        self._loop = gobject.MainLoop()
        self._loop.run()

    def _get_device(self, udi):
        '''Check if device is a volume and return it if it is
        '''
        bus = dbus.SystemBus()
        device_obj = bus.get_object("org.freedesktop.Hal", udi)
        device = dbus.Interface(device_obj, "org.freedesktop.Hal.Device")
        if device.QueryCapability("volume"):
            uuid = device.GetProperty("block.storage_device").split('/')[-1]
            size = device.GetProperty("volume.size")
            label = device.GetProperty("volume.label")
            return Device(uuid, size, label)
        return None

    def _add_event(self, udi):
        '''Called when a device is added. Performs validation
        '''
        device = self._get_device(udi)
        if device is None:
            return
        logger.debug("Device insertion detected %s %s" %
                     (device.label, device.uuid))

        if self._adding_device is True:
            if not self._register_device(device):
                self._loop.quit()
                return False
            return True

        if self.registrar.verify_device(device):
            logger.debug("Device verified OK")
            self._device_udi = udi
            if self._xlock_pid != 0:
                logger.debug("Unlocking.")
                os.kill(self._xlock_pid, signal.SIGTERM)
                self._xlock_pid = 0

    def _remove_event(self, udi):
        '''Called when device removed. Starts xlock if not already
        running
        '''
        if self._xlock_pid != 0:
            return

        if udi == self._device_udi:
            logger.debug("Device matches. Locking screen.")
            xlock_proc = subprocess.Popen(['/usr/bin/xlock', '-mode', 'blank'])
            self._xlock_pid = xlock_proc.pid


class MacListener(Listener):
    def __init__(self):
        raise Exception("MacListener not yet implemented")


class WinListener(Listener):
    def __init__(self):
        raise Exception("WinListener not yet implemented")

########NEW FILE########
__FILENAME__ = logger
import logging

logger = logging.getLogger("usblock")


def setup_logging(level, to_file=""):
    level = int(level)
    if level > 5:
        level = 5

    level *= 10
    logger.setLevel(level)

    # create console handler and set level to debug
    if to_file:
        handler = logging.FileHandler(to_file)
    else:
        handler = logging.StreamHandler()
    handler.setLevel(level)
    # create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - "
                                  "%(levelname)s -%(message)s")
    # add formatter to ch
    handler.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(handler)
    return handler

########NEW FILE########
__FILENAME__ = registrar
import errno
import os
import ConfigParser
from collections import namedtuple

from .logger import logger

Device = namedtuple("Device", ["uuid", "size", "label"])


class Registrar(object):
    '''Handles reading and writing device details to the
    config file'''
    def __init__(self, path=""):
        self.devices = []

        self._path = path
        self._config = None

    def load_config(self):
        '''Read the config file and get all listed
        devices.
        '''
        self._create_conf_dir()
        self._config = ConfigParser.ConfigParser()
        opened_files = self._config.read(self._path)
        if not len(opened_files):
            try:
                file_handle = open(self._path, "w+")
                file_handle.close()
                os.chmod(self._path, 0600)
            except IOError:
                raise Exception("Failed to open %s for writing." %
                                self._path)
        else:
            self._set_values()

    def write_config(self):
        '''Write all current devices stored in memory to config file
        '''
        # Start with a clean config and just dump everything
        logger.debug("Write out config file")
        del self._config
        self._config = ConfigParser.ConfigParser()

        for num, device in enumerate(self.devices, start=1):
            section_name = "device%d" % num
            self._config.add_section(section_name)
            self._config.set(section_name, "deviceid", device.uuid)
            self._config.set(section_name, "devicesize", device.size)
            self._config.set(section_name, "devicelabel", device.label)

        with open(self._path, "w") as config_fh:
            self._config.write(config_fh)

    def add_device(self, device):
        '''Adds a device to the list and writes the new config
        '''
        self.devices.append(device)
        self.write_config()

    def verify_device(self, device):
        '''Checks supplied device against known devices. Returns
        True if a match is found, False otherwise
        '''
        if device.uuid not in [d.uuid for d in self.devices]:
            return False

        if str(device.size) not in [d.size for d in self.devices]:
            return False

        return True

    def _create_conf_dir(self):
        '''Create a config dir. Raise Exception if unable to
        create it
        '''
        try:
            os.makedirs(os.path.dirname(self._path))
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise Exception("Unable to create config dir %s %s" %
                                (self._path, os.strerror(err.errno)))

    def _set_values(self):
        '''Set up devices for current config
        '''
        if not len(self._config.sections()):
            return

        for section in self._config.sections():
            device = Device(self._config.get(section, "deviceid"),
                            self._config.get(section, "devicesize"),
                            self._config.get(section, "devicelabel"))
            self.devices.append(device)

########NEW FILE########
