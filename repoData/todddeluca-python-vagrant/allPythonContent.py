__FILENAME__ = test_vagrant
'''
Introduces setup and teardown routines suitable for testing Vagrant.

Note that the tests can take few minutes to run because of the time
required to bring up/down the VM.

Most test functions (decorated with `@with_setup`) will actually bring the VM
up/down. This for one is the "proper" way of doing things (isolation).  The
downside of such workflow is that it increases the execution time of the test
suite. The other approach (bringing the VM up once and packing all tests
together) is less extensible.  With few tests it may work, but when the test
suite grows it becomes a problem.

In order to mitigate the inconvenience, each test method actually
encapsulates few related tests. Aside from making the execution time shorter
it also adds to readability.

Before the first test a base box is added to Vagrant under the name
TEST_BOX_NAME. This box is not deleted after the test suite runs in order
to avoid downloading of the box file on every run.
'''


import os
import re
import unittest
import shutil
import subprocess
import sys
import tempfile
import time
from nose.tools import eq_, with_setup

import vagrant

# location of a test file on the created box by provisioning in vm_Vagrantfile
TEST_FILE_PATH = '/home/vagrant/python_vagrant_test_file'
# location of Vagrantfiles used for testing.
MULTIVM_VAGRANTFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'vagrantfiles', 'multivm_Vagrantfile')
VM_VAGRANTFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'vagrantfiles', 'vm_Vagrantfile')
SHELL_PROVISION_VAGRANTFILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'vagrantfiles', 'shell_provision_Vagrantfile')
# the names of the vms from the multi-vm Vagrantfile.
VM_1 = 'web'
VM_2 = 'db'
# name of the base box used for testing
TEST_BOX_NAME = "python-vagrant-base"
# url of the box file used for testing
TEST_BOX_URL = "http://files.vagrantup.com/lucid32.box"
# temp dir for testing.
TD = None



def list_boxes():
    '''
    Return a list if tuples containing the box name and box provider of each
    box in `vagrant box list`.
    '''
    # Example `box list` output (vagrant 1.1.5):
    # base                     (virtualbox)
    # precise32                (virtualbox)
    # precise64                (virtualbox)
    # python-vagrant-base      (virtualbox)
    # python-vagrant-dummy-box (virtualbox)
    # Example `box list` output with no boxes (vagrant 1.2.7):
    # There are no installed boxes! Use `vagrant box add` to add some.
    listing = subprocess.check_output('vagrant box list', shell=True)
    boxes = []
    for line in listing.splitlines():
        m = re.search(r'^\s*(?P<name>.+?)\s+\((?P<provider>[^)]+)\)\s*$', line)
        if m:
            print m.groups()
            boxes.append((m.group('name'), m.group('provider')))
    return boxes


def list_box_names():
    '''
    Return a list of the currently installed vagrant box names.
    '''
    return [box[0] for box in list_boxes()]


# MODULE-LEVEL SETUP AND TEARDOWN

def setup():
    '''
    Creates the directory used for testing and sets up the base box if not
    already set up.

    Creates a directory in a temporary location and checks if there is a base
    box under the `TEST_BOX_NAME`. If not, downloads it from `TEST_BOX_URL` and
    adds to Vagrant.

    This is ran once before the first test (global setup).
    '''
    sys.stderr.write('module setup()\n')
    global TD
    TD = tempfile.mkdtemp()
    sys.stderr.write('test temp dir: {}\n'.format(TD))
    boxes = list_box_names()
    if TEST_BOX_NAME not in boxes:
        cmd = 'vagrant box add {} {}'.format(TEST_BOX_NAME, TEST_BOX_URL)
        subprocess.check_call(cmd, shell=True)


def teardown():
    '''
    Removes the directory created in setup.

    This is run once after the last test.
    '''
    sys.stderr.write('module teardown()\n')
    if TD is not None:
        shutil.rmtree(TD)


# TEST-LEVEL SETUP AND TEARDOWN

def make_setup_vm(vagrantfile=None):
    '''
    Make and return a function that sets up the temporary directory with a
    Vagrantfile.  By default, use VM_VAGRANTFILE.
    vagrantfile: path to a vagrantfile to use as Vagrantfile in the testing temporary directory.
    '''
    if vagrantfile is None:
        vagrantfile = VM_VAGRANTFILE

    def setup_vm():
        shutil.copy(vagrantfile, os.path.join(TD, 'Vagrantfile'))

    return setup_vm


def teardown_vm():
    '''
    Attempts to destroy every VM in the Vagrantfile in the temporary directory, TD.
    It is not an error if a VM has already been destroyed.
    '''
    try:
        # Try to destroy any vagrant box that might be running.
        subprocess.check_call('vagrant destroy -f', cwd=TD, shell=True)
    except subprocess.CalledProcessError:
        pass
    finally:
        # remove Vagrantfile created by setup.
        os.unlink(os.path.join(TD, "Vagrantfile"))



@with_setup(make_setup_vm(), teardown_vm)
def test_plugin_list_parsing():
    '''
    Test the parsing the output of the `vagrant plugin list` command.
    '''
    # listing should match output generated by `vagrant plugin list`.
    listing = '''sahara (0.0.16)
vagrant-login (1.0.1, system)
'''
    # Can compare tuples to Plugin class b/c Plugin is a collections.namedtuple.
    goal = [('sahara', '0.0.16', False), ('vagrant-login', '1.0.1', True)]
    v = vagrant.Vagrant(TD)
    parsed = [v._parse_plugin_list_line(l) for l in listing.splitlines()]
    assert goal == parsed, 'The parsing of the test listing did not match the goal.\nlisting={!r}\ngoal={!r}\nparsed_listing={!r}'.format(listing, goal, parsed)


@with_setup(make_setup_vm(), teardown_vm)
def test_vm_status():
    '''
    Test whether vagrant.status() correctly reports state of the VM, in a
    single-VM environment.
    '''
    v = vagrant.Vagrant(TD)
    assert v.NOT_CREATED == v.status()[0].state, "Before going up status should be vagrant.NOT_CREATED"
    command = 'vagrant up'
    subprocess.check_call(command, cwd=TD, shell=True)
    assert v.RUNNING in v.status()[0].state, "After going up status should be vagrant.RUNNING"

    command = 'vagrant halt'
    subprocess.check_call(command, cwd=TD, shell=True)
    assert v.POWEROFF in v.status()[0].state, "After halting status should be vagrant.POWEROFF"

    command = 'vagrant destroy -f'
    subprocess.check_call(command, cwd=TD, shell=True)
    assert v.NOT_CREATED in v.status()[0].state, "After destroying status should be vagrant.NOT_CREATED"


@with_setup(make_setup_vm(), teardown_vm)
def test_vm_lifecycle():
    '''
    Test methods controlling the VM - init(), up(), halt(), destroy().
    '''

    v = vagrant.Vagrant(TD)

    # Test init by removing Vagrantfile, since v.init() will create one.
    os.unlink(os.path.join(TD, 'Vagrantfile'))
    v.init(TEST_BOX_NAME)
    assert v.NOT_CREATED == v.status()[0].state

    v.up()
    assert v.RUNNING == v.status()[0].state

    v.suspend()
    assert v.SAVED == v.status()[0].state

    v.halt()
    assert v.POWEROFF == v.status()[0].state

    v.destroy()
    assert v.NOT_CREATED == v.status()[0].state


@with_setup(make_setup_vm(), teardown_vm)
def test_vm_config():
    '''
    Test methods retrieving ssh config settings, like user, hostname, and port.
    '''
    v = vagrant.Vagrant(TD)
    v.up()
    command = "vagrant ssh-config"
    ssh_config = subprocess.check_output(command, cwd=TD, shell=True)
    parsed_config = dict(line.strip().split(None, 1) for line in
                            ssh_config.splitlines() if line.strip() and not
                            line.strip().startswith('#'))

    user = v.user()
    expected_user = parsed_config["User"]
    eq_(user, expected_user)

    hostname = v.hostname()
    expected_hostname = parsed_config["HostName"]
    eq_(hostname, expected_hostname)

    port = v.port()
    expected_port = parsed_config["Port"]
    eq_(port, expected_port)

    user_hostname = v.user_hostname()
    eq_(user_hostname, "{}@{}".format(expected_user, expected_hostname))

    user_hostname_port = v.user_hostname_port()
    eq_(user_hostname_port,
        "{}@{}:{}".format(expected_user, expected_hostname, expected_port))

    keyfile = v.keyfile()
    eq_(keyfile, parsed_config["IdentityFile"])


@with_setup(make_setup_vm(), teardown_vm)
def test_vm_sandbox_mode():
    '''
    Test methods for enabling/disabling the sandbox mode
    and committing/rolling back changes.

    This depends on the Sahara plugin.
    '''
    # Only test Sahara if it is installed.
    # This leaves the testing of Sahara to people who care.
    sahara_installed = _plugin_installed(vagrant.Vagrant(TD), 'sahara')
    if not sahara_installed:
        return

    v = vagrant.SandboxVagrant(TD)

    sandbox_status = v.sandbox_status()
    assert sandbox_status == "unknown", "Before the VM goes up the status should be 'unknown', " + "got:'{}'".format(sandbox_status)

    v.up()
    sandbox_status = v.sandbox_status()
    assert sandbox_status == "off", "After the VM goes up the status should be 'off', " + "got:'{}'".format(sandbox_status)

    v.sandbox_on()
    sandbox_status = v.sandbox_status()
    assert sandbox_status == "on", "After enabling the sandbox mode the status should be 'on', " + "got:'{}'".format(sandbox_status)

    v.sandbox_off()
    sandbox_status = v.sandbox_status()
    assert sandbox_status == "off", "After disabling the sandbox mode the status should be 'off', " + "got:'{}'".format(sandbox_status)

    v.sandbox_on()
    v.halt()
    sandbox_status = v.sandbox_status()
    assert sandbox_status == "on", "After halting the VM the status should be 'on', " + "got:'{}'".format(sandbox_status)

    v.up()
    sandbox_status = v.sandbox_status()
    assert sandbox_status == "on", "After bringing the VM up again the status should be 'on', " + "got:'{}'".format(sandbox_status)

    test_file_contents = _read_test_file(v)
    print test_file_contents
    eq_(test_file_contents, None, "There should be no test file")

    _write_test_file(v, "foo")
    test_file_contents = _read_test_file(v)
    print test_file_contents
    eq_(test_file_contents, "foo", "The test file should read 'foo'")

    v.sandbox_rollback()
    time.sleep(10)  # https://github.com/jedi4ever/sahara/issues/16

    test_file_contents = _read_test_file(v)
    print test_file_contents
    eq_(test_file_contents, None, "There should be no test file")

    _write_test_file(v, "foo")
    test_file_contents = _read_test_file(v)
    print test_file_contents
    eq_(test_file_contents, "foo", "The test file should read 'foo'")
    v.sandbox_commit()
    _write_test_file(v, "bar")
    test_file_contents = _read_test_file(v)
    print test_file_contents
    eq_(test_file_contents, "bar", "The test file should read 'bar'")

    v.sandbox_rollback()
    time.sleep(10)  # https://github.com/jedi4ever/sahara/issues/16

    test_file_contents = _read_test_file(v)
    print test_file_contents
    eq_(test_file_contents, "foo", "The test file should read 'foo'")

    sandbox_status = v._parse_vagrant_sandbox_status("Usage: ...")
    eq_(sandbox_status, "not installed", "When 'vagrant sandbox status'" +
        " outputs vagrant help status should be 'not installed', " +
        "got:'{}'".format(sandbox_status))

    v.destroy()
    sandbox_status = v.sandbox_status()
    assert sandbox_status == "unknown", "After destroying the VM the status should be 'unknown', " + "got:'{}'".format(sandbox_status)


@with_setup(make_setup_vm(), teardown_vm)
def test_boxes():
    '''
    Test methods for manipulating boxes - adding, listing, removing.
    '''
    v = vagrant.Vagrant(TD)
    box_name = "python-vagrant-dummy-box"
    provider = "virtualbox"

    # Start fresh with no dummy box
    boxes = list_boxes()
    if (box_name, provider) in boxes:
        subprocess.check_call(
            'vagrant box remove {} {}'.format(box_name, provider), shell=True)

    # Test that there is no dummy box
    boxes = list_boxes()
    eq_((box_name, provider) in boxes, False,
        "There should be no dummy box before it's added")

    # Test adding a box
    v.box_add(box_name, TEST_BOX_URL)
    boxes = list_boxes()
    eq_((box_name, provider) in boxes, True,
        "There should be a dummy box in the list of boxes")

    # Test listing boxes
    boxes = list_boxes()
    reported_boxes = [(b.name, b.provider) for b in v.box_list()]
    for box in boxes:
        eq_(box in reported_boxes, True,
            "The box '{}' should be in the list returned by box_list()".format(box))

    # Test removing a box with name and provider
    v.box_remove(box_name, provider)
    boxes = list_boxes()
    eq_((box_name, provider) in boxes, False,
        "There should be no dummy box after it's been deleted")


@with_setup(make_setup_vm(SHELL_PROVISION_VAGRANTFILE), teardown_vm)
def test_provisioning():
    '''
    Test provisioning support.  The tested provision config creates a file on
    the vm with the contents 'foo'.
    '''
    v = vagrant.Vagrant(TD)

    v.up(no_provision=True)
    test_file_contents = _read_test_file(v)
    eq_(test_file_contents, None, "There should be no test file after up()")

    v.provision()
    test_file_contents = _read_test_file(v)
    print "Contents: {}".format(test_file_contents)
    eq_(test_file_contents, "foo", "The test file should contain 'foo'")


@with_setup(make_setup_vm(MULTIVM_VAGRANTFILE), teardown_vm)
def test_multivm_lifecycle():
    v = vagrant.Vagrant(TD)

    # test getting multiple statuses at once
    eq_(v.status(VM_1)[0].state, v.NOT_CREATED)
    eq_(v.status(VM_2)[0].state, v.NOT_CREATED)

    v.up(vm_name=VM_1)
    eq_(v.status(VM_1)[0].state, v.RUNNING)
    eq_(v.status(VM_2)[0].state, v.NOT_CREATED)

    # start both vms
    v.up()
    eq_(v.status(VM_1)[0].state, v.RUNNING)
    eq_(v.status(VM_2)[0].state, v.RUNNING)

    v.halt(vm_name=VM_1)
    eq_(v.status(VM_1)[0].state, v.POWEROFF)
    eq_(v.status(VM_2)[0].state, v.RUNNING)

    v.destroy(vm_name=VM_1)
    eq_(v.status(VM_1)[0].state, v.NOT_CREATED)
    eq_(v.status(VM_2)[0].state, v.RUNNING)

    v.suspend(vm_name=VM_2)
    eq_(v.status(VM_1)[0].state, v.NOT_CREATED)
    eq_(v.status(VM_2)[0].state, v.SAVED)

    v.destroy(vm_name=VM_2)
    eq_(v.status(VM_1)[0].state, v.NOT_CREATED)
    eq_(v.status(VM_2)[0].state, v.NOT_CREATED)


@with_setup(make_setup_vm(MULTIVM_VAGRANTFILE), teardown_vm)
def test_multivm_config():
    '''
    Test methods retrieving configuration settings.
    '''
    v = vagrant.Vagrant(TD, quiet_stdout=False, quiet_stderr=False)
    v.up(vm_name=VM_1)
    command = "vagrant ssh-config " + VM_1
    ssh_config = subprocess.check_output(command, cwd=TD, shell=True)
    parsed_config = dict(line.strip().split(None, 1) for line in
                            ssh_config.splitlines() if line.strip() and not
                            line.strip().startswith('#'))

    user = v.user(vm_name=VM_1)
    expected_user = parsed_config["User"]
    eq_(user, expected_user)

    hostname = v.hostname(vm_name=VM_1)
    expected_hostname = parsed_config["HostName"]
    eq_(hostname, expected_hostname)

    port = v.port(vm_name=VM_1)
    expected_port = parsed_config["Port"]
    eq_(port, expected_port)

    user_hostname = v.user_hostname(vm_name=VM_1)
    eq_(user_hostname, "{}@{}".format(expected_user, expected_hostname))

    user_hostname_port = v.user_hostname_port(vm_name=VM_1)
    eq_(user_hostname_port,
        "{}@{}:{}".format(expected_user, expected_hostname, expected_port))

    keyfile = v.keyfile(vm_name=VM_1)
    eq_(keyfile, parsed_config["IdentityFile"])


def _execute_command_in_vm(v, command):
    '''
    Run command via ssh on the test vagrant box.  Returns a tuple of the
    return code and output of the command.
    '''
    vagrant_exe = vagrant.get_vagrant_executable()

    if not vagrant_exe:
        raise RuntimeError(vagrant.VAGRANT_NOT_FOUND_WARNING)

    # ignore the fact that this host is not in our known hosts
    ssh_command = [vagrant_exe, 'ssh', '-c', command]
    return subprocess.check_output(ssh_command, cwd=v.root)


def _write_test_file(v, file_contents):
    '''
    Writes given contents to the test file.
    '''
    command = "echo '{}' > {}".format(file_contents, TEST_FILE_PATH)
    _execute_command_in_vm(v, command)


def _read_test_file(v):
    '''
    Returns the contents of the test file stored in the VM or None if there
    is no file.
    '''
    command = 'cat {}'.format(TEST_FILE_PATH)
    try:
        output = _execute_command_in_vm(v, command)
        return output.strip()
    except subprocess.CalledProcessError:
        return None


def _plugin_installed(v, plugin_name):
    plugins = v.plugin_list()
    return plugin_name in [plugin.name for plugin in plugins]

########NEW FILE########
__FILENAME__ = test_vagrant_test_case
"""
Tests for the various functionality provided by the VagrantTestCase class

There are a handful of classes to try to provide multiple different varying samples of possible setups
"""
import os
from vagrant import Vagrant
from vagrant.test import VagrantTestCase


def get_vagrant_root(test_vagrant_root_path):
    return os.path.dirname(os.path.realpath(__file__)) + '/vagrantfiles/' + test_vagrant_root_path

SINGLE_BOX = get_vagrant_root('single_box')
MULTI_BOX = get_vagrant_root('multi_box')


class AllMultiBoxesTests(VagrantTestCase):
    """Tests for a multiple box setup where vagrant_boxes is left empty"""

    vagrant_root = MULTI_BOX

    def test_default_boxes_list(self):
        """Tests that all boxes in a Vagrantfile if vagrant_boxes is not defined"""
        self.assertGreater(len(self.vagrant_boxes), 0)


class SingleBoxTests(VagrantTestCase):
    """Tests for a single box setup"""

    vagrant_root = SINGLE_BOX

    def test_box_up(self):
        """Tests that the box starts as expected"""
        state = self.vagrant.status(vm_name=self.vagrant_boxes[0])[0].state
        self.assertEqual(state, Vagrant.RUNNING)


class SpecificMultiBoxTests(VagrantTestCase):
    """Tests for a multiple box setup where only some of the boxes are to be on"""

    vagrant_boxes = ['precise32']
    vagrant_root = MULTI_BOX

    def test_all_boxes_up(self):
        """Tests that all boxes listed are up after starting"""
        for box_name in self.vagrant_boxes:
            state = self.vagrant.status(vm_name=box_name)[0].state
            self.assertEqual(state, Vagrant.RUNNING)

    def test_unlisted_boxes_ignored(self):
        """Tests that the boxes not listed are not brought up"""
        for box_name in [s.name for s in self.vagrant.status()]:
            if box_name in self.vagrant_boxes:
                self.assertBoxUp(box_name)
            else:
                self.assertBoxNotCreated(box_name)

########NEW FILE########
__FILENAME__ = test
"""
A TestCase class, tying together the Vagrant class and removing some of the boilerplate involved in writing tests
that leverage vagrant boxes.
"""
from unittest import TestCase
from vagrant import Vagrant

__author__ = 'nick'


class VagrantTestCase(TestCase):
	"""
	TestCase class to control vagrant boxes during testing

	vagrant_boxes: An iterable of vagrant boxes. If empty or None, all boxes will be used. Defaults to []
	vagrant_root: The root directory that holds a Vagrantfile for configuration. Defaults to the working directory
	restart_boxes: If True, the boxes will be restored to their initial states between each test, otherwise the boxes
		will remain up. Defaults to False
	"""

	vagrant_boxes = []
	vagrant_root = None
	restart_boxes = False

	__initial_box_statuses = {}
	__cleanup_actions = {
		Vagrant.NOT_CREATED: 'destroy',
		Vagrant.POWEROFF: 'halt',
		Vagrant.SAVED: 'suspend',
	}

	def __init__(self, *args, **kwargs):
		"""Check that the vagrant_boxes attribute is not left empty, and is populated by all boxes if left blank"""
		self.vagrant = Vagrant(self.vagrant_root)
		if not self.vagrant_boxes:
			boxes = [s.name for s in self.vagrant.status()]
			if len(boxes) == 1:
				self.vagrant_boxes = ['default']
			else:
				self.vagrant_boxes = boxes
		super(VagrantTestCase, self).__init__(*args, **kwargs)

	def assertBoxStatus(self, box, status):
		"""Assertion for a box status"""
		box_status = [s.state for s in self.vagrant.status() if s.name == box][0]
		if box_status != status:
			self.failureException('{} has status {}, not {}'.format(box, box_status, status))

	def assertBoxUp(self, box):
		"""Assertion for a box being up"""
		self.assertBoxStatus(box, Vagrant.RUNNING)

	def assertBoxSuspended(self, box):
		"""Assertion for a box being up"""
		self.assertBoxStatus(box, Vagrant.SAVED)

	def assertBoxHalted(self, box):
		"""Assertion for a box being up"""
		self.assertBoxStatus(box, Vagrant.POWEROFF)

	def assertBoxNotCreated(self, box):
		"""Assertion for a box being up"""
		self.assertBoxStatus(box, Vagrant.NOT_CREATED)

	def run(self, result=None):
		"""Override run to have provide a hook into an alternative to tearDownClass with a reference to self"""
		self.setUpOnce()
		run = super(VagrantTestCase, self).run(result)
		self.tearDownOnce()
		return run

	def setUpOnce(self):
		"""Collect the box states before starting"""
		for box_name in self.vagrant_boxes:
			box_state = [s.state for s in self.vagrant.status() if s.name == box_name][0]
			self.__initial_box_statuses[box_name] = box_state

	def tearDownOnce(self):
		"""Restore all boxes to their initial states after running all tests, unless tearDown handled it already"""
		if not self.restart_boxes:
			self.restore_box_states()

	def restore_box_states(self):
		"""Restores all boxes to their original states"""
		for box_name in self.vagrant_boxes:
			action = self.__cleanup_actions.get(self.__initial_box_statuses[box_name])
			if action:
				getattr(self.vagrant, action)(vm_name=box_name)

	def setUp(self):
		"""Starts all boxes before running tests"""
		for box_name in self.vagrant_boxes:
			self.vagrant.up(vm_name=box_name)

		super(VagrantTestCase, self).setUp()

	def tearDown(self):
		"""Returns boxes to their initial status after each test if self.restart_boxes is True"""
		if self.restart_boxes:
			self.restore_box_states()

		super(VagrantTestCase, self).tearDown()

########NEW FILE########
