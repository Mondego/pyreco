__FILENAME__ = compat
import sys

PY3 = sys.version_info[0] == 3

if PY3:
    basestring = str
    class unicode(str):
        def __init__(self, string, encoding, errors):
            str.__init__(self, string)
else:
    basestring = basestring
    unicode = unicode

########NEW FILE########
__FILENAME__ = resulthandler
from supervisor.dispatchers import RejectEvent
from supervisor_twiddler.compat import unicode, basestring

def stdin_write_handler(event, response):
    """ A supervisor eventlistener result handler that accepts a
    special 'STDIN:' result and writes what follows to the STDIN
    of the process associated with the event. """
    if response.startswith("STDIN:"):
        _stdin_write(event.process, response[6:])
    elif response != 'OK':
        raise RejectEvent(response)

def _stdin_write(process, chars):
    """ Write chars to the stdin of process.  If the process is
    not running or another error occurs, there is not anything we
    can do so just return False. """
    if isinstance(chars, unicode):
        chars = chars.encode('utf-8')

    if not isinstance(chars, basestring):
        return False

    if not process.pid or process.killing:
        return False

    try:
        process.write(chars)
    except OSError:
        return False

    return True

########NEW FILE########
__FILENAME__ = rpcinterface
from supervisor.options import UnhosedConfigParser
from supervisor.datatypes import list_of_strings
from supervisor.states import SupervisorStates
from supervisor.states import STOPPED_STATES
from supervisor.xmlrpc import Faults as SupervisorFaults
from supervisor.xmlrpc import RPCError
import supervisor.loggers

API_VERSION = '1.0'

class Faults:
    NOT_IN_WHITELIST = 230

class TwiddlerNamespaceRPCInterface:
    """ A supervisor rpc interface that facilitates manipulation of
    supervisor's configuration and state in ways that are not
    normally accessible at runtime.
    """
    def __init__(self, supervisord, whitelist=[]):
        self.supervisord = supervisord
        self._whitelist = list_of_strings(whitelist)

    def _update(self, func_name):
        self.update_text = func_name

        state = self.supervisord.get_state()
        if state == SupervisorStates.SHUTDOWN:
            raise RPCError(SupervisorFaults.SHUTDOWN_STATE)

        if len(self._whitelist):
            if func_name not in self._whitelist:
                raise RPCError(Faults.NOT_IN_WHITELIST, func_name)

    # RPC API methods

    def getAPIVersion(self):
        """ Return the version of the RPC API used by supervisor_twiddler

        @return int version version id
        """
        self._update('getAPIVersion')
        return API_VERSION

    def getGroupNames(self):
        """ Return an array with the names of the process groups.

        @return array                Process group names
        """
        self._update('getGroupNames')
        return list(self.supervisord.process_groups.keys())

    def log(self, message, level=supervisor.loggers.LevelsByName.INFO):
        """ Write an arbitrary message to the main supervisord log.  This is
            useful for recording information about your twiddling.

        @param  string      message      Message to write to the log
        @param  string|int  level        Log level name (INFO) or code (20)
        @return boolean                  Always True unless error
        """
        self._update('log')

        if isinstance(level, str):
            level = getattr(supervisor.loggers.LevelsByName,
                            level.upper(), None)

        if supervisor.loggers.LOG_LEVELS_BY_NUM.get(level, None) is None:
            raise RPCError(SupervisorFaults.INCORRECT_PARAMETERS)

        self.supervisord.options.logger.log(level, message)
        return True

    def addProgramToGroup(self, group_name, program_name, program_options):
        """ Add a new program to an existing process group.  Depending on the
            numprocs option, this will result in one or more processes being
            added to the group.

        @param string  group_name       Name of an existing process group
        @param string  program_name     Name of the new process in the process table
        @param struct  program_options  Program options, same as in supervisord.conf
        @return boolean                 Always True unless error
        """
        self._update('addProgramToGroup')

        group = self._getProcessGroup(group_name)

        # make configparser instance for program options
        section_name = 'program:%s' % program_name
        parser = self._makeConfigParser(section_name, program_options)

        # make process configs from parser instance
        options = self.supervisord.options
        try:
            new_configs = options.processes_from_section(parser, section_name, group_name)
        except ValueError as e:
            raise RPCError(SupervisorFaults.INCORRECT_PARAMETERS, e)

        # check new process names don't already exist in the config
        for new_config in new_configs:
            for existing_config in group.config.process_configs:
                if new_config.name == existing_config.name:
                    raise RPCError(SupervisorFaults.BAD_NAME, new_config.name)

        # add process configs to group
        group.config.process_configs.extend(new_configs)

        for new_config in new_configs:
            # the process group config already exists and its after_setuid hook
            # will not be called again to make the auto child logs for this process.
            new_config.create_autochildlogs()

            # add process instance
            group.processes[new_config.name] = new_config.make_process(group)

        return True

    def removeProcessFromGroup(self, group_name, process_name):
        """ Remove a process from a process group.  When a program is added with
            addProgramToGroup(), one or more processes for that program is added
            to the group.  This method removes individual processes (named by the
            numprocs and process_name options), not programs.

        @param string group_name    Name of an existing process group
        @param string process_name  Name of the process to remove from group
        @return boolean             Always return True unless error
        """
        self._update('removeProcessFromGroup')

        group = self._getProcessGroup(group_name)

        # check process exists and is running
        process = group.processes.get(process_name)
        if process is None:
            raise RPCError(SupervisorFaults.BAD_NAME, process_name)
        if process.pid or process.state not in STOPPED_STATES:
            raise RPCError(SupervisorFaults.STILL_RUNNING, process_name)

        group.transition()

        # del process config from group, then del process
        for index, config in enumerate(group.config.process_configs):
            if config.name == process_name:
                del group.config.process_configs[index]

        del group.processes[process_name]
        return True

    def _getProcessGroup(self, name):
        """ Find a process group by its name """
        group = self.supervisord.process_groups.get(name)
        if group is None:
            raise RPCError(SupervisorFaults.BAD_NAME, 'group: %s' % name)
        return group

    def _makeConfigParser(self, section_name, options):
        """ Populate a new UnhosedConfigParser instance with a
        section built from an options dict.
        """
        config = UnhosedConfigParser()
        try:
            config.add_section(section_name)
            for k, v in dict(options).items():
                config.set(section_name, k, v)
        except (TypeError, ValueError):
            raise RPCError(SupervisorFaults.INCORRECT_PARAMETERS)
        return config

def make_twiddler_rpcinterface(supervisord, **config):
    return TwiddlerNamespaceRPCInterface(supervisord, **config)

########NEW FILE########
__FILENAME__ = test_resulthandler
import sys
import unittest
import supervisor_twiddler
import supervisor_twiddler.resulthandler
from supervisor.tests.base import DummyEvent, DummyOptions, DummyPConfig, DummyProcess
from supervisor.dispatchers import RejectEvent

class TestStdinWriteHandler(unittest.TestCase):
    def test_handler_does_nothing_when_response_is_OK(self):
        event = DummyEvent()
        response = 'OK'
        supervisor_twiddler.resulthandler.stdin_write_handler(event, response)

    def test_handler_rejects_event_when_response_is_unexpected(self):
        event = DummyEvent()
        response = 'unexpected'
        self.assertRaises(RejectEvent,
                          supervisor_twiddler.resulthandler.stdin_write_handler,
                          event, response)

    def test_handler_writes_chars_when_response_is_STDIN(self):
        options = DummyOptions()
        config = DummyPConfig(options, 'cat', 'bin/cat')

        process = DummyProcess(config)
        process.pid = 42
        process.killing = False

        event = DummyEvent()
        event.process = process

        response = 'STDIN:foobar'
        supervisor_twiddler.resulthandler.stdin_write_handler(event, response)
        self.assertEqual(process.stdin_buffer, 'foobar')

    def test_write_encodes_unicode_as_utf8(self):
        options = DummyOptions()
        config = DummyPConfig(options, 'cat', 'bin/cat')

        process = DummyProcess(config)
        process.pid = 42
        process.killing = False

        event = DummyEvent()
        event.process = process

        response = u'STDIN:foobar'
        supervisor_twiddler.resulthandler.stdin_write_handler(event, response)
        self.assertEqual(process.stdin_buffer, 'foobar')

    def test_write_fails_silently_if_process_has_no_pid(self):
        options = DummyOptions()
        config = DummyPConfig(options, 'cat', 'bin/cat')

        process = DummyProcess(config)
        process.pid = None
        process.killing = False

        event = DummyEvent()
        event.process = process

        response = 'STDIN:foobar'
        supervisor_twiddler.resulthandler.stdin_write_handler(event, response)
        self.assertEqual(process.stdin_buffer, '')

    def test_write_fails_silently_if_process_is_killing(self):
        options = DummyOptions()
        config = DummyPConfig(options, 'cat', 'bin/cat')

        process = DummyProcess(config)
        process.pid = 42
        process.killing = True

        event = DummyEvent()
        event.process = process

        response = 'STDIN:foobar'
        supervisor_twiddler.resulthandler.stdin_write_handler(event, response)
        self.assertEqual(process.stdin_buffer, '')

    def test_write_fails_silently_if_oserror_during_write(self):
        options = DummyOptions()
        config = DummyPConfig(options, 'cat', 'bin/cat')

        process = DummyProcess(config)
        process.pid = 42
        process.killing = False
        process.write_error = True

        event = DummyEvent()
        event.process = process

        response = 'STDIN:foobar'
        supervisor_twiddler.resulthandler.stdin_write_handler(event, response)
        self.assertEqual(process.stdin_buffer, '')

def test_suite():
    return unittest.findTestCases(sys.modules[__name__])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

########NEW FILE########
__FILENAME__ = test_rpcinterface
import sys
import unittest

import supervisor
from supervisor.xmlrpc import Faults as SupervisorFaults
from supervisor.states import SupervisorStates, ProcessStates

from supervisor_twiddler.rpcinterface import Faults as TwiddlerFaults

from supervisor.tests.base import DummySupervisor
from supervisor.tests.base import DummyPConfig, DummyProcess
from supervisor.tests.base import DummyPGroupConfig, DummyProcessGroup

class TestRPCInterface(unittest.TestCase):

    # Fault Constants

    def test_twiddler_fault_names_dont_clash_with_supervisord_fault_names(self):
        supervisor_faults = self.attrDictWithoutUnders(SupervisorFaults)
        twiddler_faults = self.attrDictWithoutUnders(TwiddlerFaults)

        for name in supervisor_faults.keys():
            self.assertTrue(twiddler_faults.get(name) is None)

    def test_twiddler_fault_codes_dont_clash_with_supervisord_fault_codes(self):
        supervisor_fault_codes = self.attrDictWithoutUnders(SupervisorFaults).values()
        twiddler_fault_codes = self.attrDictWithoutUnders(TwiddlerFaults).values()

        for code in supervisor_fault_codes:
            self.assertFalse(code in twiddler_fault_codes)

    # Constructor

    def test_ctor_assigns_supervisord(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)

        self.assertEqual(supervisord, interface.supervisord)

    # Factory

    def test_make_twiddler_rpcinterface_factory(self):
        from supervisor_twiddler import rpcinterface

        supervisord = DummySupervisor()
        interface = rpcinterface.make_twiddler_rpcinterface(supervisord)

        self.assertTrue(isinstance(interface,
            rpcinterface.TwiddlerNamespaceRPCInterface))
        self.assertEqual(supervisord, interface.supervisord)

    # Updater

    def test_updater_raises_shutdown_error_if_supervisord_in_shutdown_state(self):
        supervisord = DummySupervisor(state = SupervisorStates.SHUTDOWN)
        interface = self.makeOne(supervisord)

        self.assertRPCError(SupervisorFaults.SHUTDOWN_STATE,
                            interface.getAPIVersion)

    # API Method twiddler.getAPIVersion()

    def test_getAPIVersion_can_be_disabled(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord, whitelist='foo,bar')

        self.assertRPCError(TwiddlerFaults.NOT_IN_WHITELIST,
                            interface.getAPIVersion)

    def test_getAPIVersion_returns_api_version(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)

        version = interface.getAPIVersion()
        self.assertEqual('getAPIVersion', interface.update_text)

        from supervisor_twiddler.rpcinterface import API_VERSION
        self.assertEqual(version, API_VERSION)

    # API Method twiddler.getGroupNames()

    def test_getGroupNames_can_be_disabled(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord, whitelist='foo,bar')

        self.assertRPCError(TwiddlerFaults.NOT_IN_WHITELIST,
                            interface.getGroupNames)

    def test_getGroupNames_returns_empty_array_when_no_groups(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)

        names = interface.getGroupNames()
        self.assertTrue(isinstance(names, list))
        self.assertEqual(0, len(names))

    def test_getGroupNames_returns_group_names(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        pgroups = {'foo': pgroup, 'bar': pgroup}
        supervisord = DummySupervisor(process_groups = pgroups)
        interface = self.makeOne(supervisord)

        names = interface.getGroupNames()
        self.assertTrue(isinstance(names, list))
        self.assertEqual(2, len(names))
        names.index('foo')
        names.index('bar')

    # API Method twiddler.addProgramToGroup()

    def test_addProgramToGroup_can_be_disabled(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord, whitelist='foo,bar')

        self.assertRPCError(TwiddlerFaults.NOT_IN_WHITELIST,
                            interface.addProgramToGroup, 'grp', 'prog', {})

    def test_addProgramToGroup_raises_bad_name_when_group_doesnt_exist(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        supervisord = DummySupervisor(process_groups = {'foo': pgroup})
        interface = self.makeOne(supervisord)

        self.assertRPCError(SupervisorFaults.BAD_NAME,
                            interface.addProgramToGroup,
                            'nonexistant_group', 'foo', {})

    def test_addProgramToGroup_raises_bad_name_when_process_already_exists(self):
        pconfig = DummyPConfig(None, 'process_that_exists', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()
        interface = self.makeOne(supervisord)

        poptions = {'command': '/usr/bin/find /'}
        self.assertRPCError(SupervisorFaults.BAD_NAME,
                            interface.addProgramToGroup,
                            'group_name', 'process_that_exists', poptions)

    def test_addProgramToGroup_raises_incorrect_params_when_poptions_is_not_dict(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()
        interface = self.makeOne(supervisord)

        bad_poptions = 42
        self.assertRPCError(SupervisorFaults.INCORRECT_PARAMETERS,
                            interface.addProgramToGroup,
                            'group_name', 'new_process', bad_poptions)

    def test_addProgramToGroup_raises_incorrect_params_when_poptions_is_invalid(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()

        interface = self.makeOne(supervisord)

        poptions_missing_command = {}
        self.assertRPCError(SupervisorFaults.INCORRECT_PARAMETERS,
                            interface.addProgramToGroup,
                            'group_name', 'new_process', poptions_missing_command)

    def test_addProgramToGroup_adds_new_process_to_supervisord_processes(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = {}

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()

        interface = self.makeOne(supervisord)

        poptions = {'command': '/usr/bin/find /'}
        self.assertTrue(interface.addProgramToGroup('group_name', 'new_process', poptions))
        self.assertEqual('addProgramToGroup', interface.update_text)

        process = pgroup.processes['new_process']

        self.assertTrue(isinstance(process, supervisor.process.Subprocess))
        self.assertEqual('/usr/bin/find /', process.config.command)

    def test_addProgramToGroup_adds_new_process_config_to_group(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = {}

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()

        interface = self.makeOne(supervisord)

        poptions = {'command': '/usr/bin/find /'}
        self.assertTrue(interface.addProgramToGroup('group_name', 'new_process', poptions))
        self.assertEqual('addProgramToGroup', interface.update_text)

        config = pgroup.config.process_configs[1]
        self.assertEqual('new_process', config.name)
        self.assertTrue(isinstance(config, supervisor.options.ProcessConfig))

    def test_addProgramToGroup_uses_process_name_from_options(self):
        gconfig = DummyPGroupConfig(None, pconfigs=[])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = {}

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()

        interface = self.makeOne(supervisord)

        poptions = {'process_name': 'renamed', 'command': '/usr/bin/find /'}
        self.assertTrue(interface.addProgramToGroup('group_name', 'new_process', poptions))
        self.assertEqual('addProgramToGroup', interface.update_text)

        config = pgroup.config.process_configs[0]
        self.assertEqual('renamed', config.name)
        self.assertTrue(pgroup.processes.get('new_process') is None)
        self.assertTrue(isinstance(pgroup.processes.get('renamed'),
          supervisor.process.Subprocess))

    def test_addProgramToGroup_adds_all_processes_resulting_from_program_options(self):
        gconfig = DummyPGroupConfig(None, pconfigs=[])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = {}

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()

        interface = self.makeOne(supervisord)

        poptions = {'command': '/usr/bin/find /',
                    'process_name': 'find_%(process_num)d',
                    'numprocs': 3}
        self.assertTrue(interface.addProgramToGroup('group_name', 'new_process', poptions))
        self.assertEqual('addProgramToGroup', interface.update_text)

        self.assertEqual(3, len(pgroup.config.process_configs))
        self.assertEqual(3, len(pgroup.processes))

    # API Method twiddler.removeProcessFromGroup()

    def test_removeProcessFromGroup_can_be_disabled(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord, whitelist='foo,bar')

        self.assertRPCError(TwiddlerFaults.NOT_IN_WHITELIST,
                            interface.removeProcessFromGroup, 'group', 'process')

    def test_removeProcessFromGroup_raises_bad_name_when_group_doesnt_exist(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        interface = self.makeOne(supervisord)

        self.assertRPCError(SupervisorFaults.BAD_NAME,
                            interface.removeProcessFromGroup,
                            'nonexistant_group_name', 'process_name')

    def test_removeProcessFromGroup_raises_bad_name_when_process_does_not_exist(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = {}

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        interface = self.makeOne(supervisord)

        self.assertRPCError(SupervisorFaults.BAD_NAME,
                            interface.removeProcessFromGroup,
                            'group_name', 'nonexistant_process_name')

    def test_removeProcessFromGroup_raises_still_running_when_process_has_pid(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        process = DummyProcess(pconfig)
        process.pid = 42

        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = { 'process_with_pid': process }

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        interface = self.makeOne(supervisord)

        self.assertRPCError(SupervisorFaults.STILL_RUNNING,
                            interface.removeProcessFromGroup,
                            'group_name', 'process_with_pid')

    def test_removeProcessFromGroup_transitions_process_group(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        process = DummyProcess(pconfig, ProcessStates.EXITED)

        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = { 'process_name': process }

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        interface = self.makeOne(supervisord)

        result = interface.removeProcessFromGroup('group_name', 'process_name')
        self.assertTrue(result)
        self.assertTrue(pgroup.transitioned)

    def test_removeProcessFromGroup_deletes_the_process(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        process = DummyProcess(pconfig, ProcessStates.STOPPED)

        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = { 'process_name': process }

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        interface = self.makeOne(supervisord)

        result = interface.removeProcessFromGroup('group_name', 'process_name')
        self.assertTrue(result)
        self.assertTrue(pgroup.processes.get('process_name') is None)
        self.assertEqual('removeProcessFromGroup', interface.update_text)

    # API Method twiddler.log()

    def test_log_can_be_disabled(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord, whitelist='foo,bar')

        self.assertRPCError(TwiddlerFaults.NOT_IN_WHITELIST,
                            interface.log, 'message')

    def test_log_write_message_when_level_is_string(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)

        result = interface.log('hello', 'info')
        self.assertTrue(result)
        result = interface.log('there', 'INFO')
        self.assertTrue(result)
        self.assertEqual('log', interface.update_text)

        logger = supervisord.options.logger
        self.assertEqual(['hello', 'there'], logger.data)

    def test_log_write_message_when_level_is_integer(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)

        from supervisor.loggers import LevelsByName
        result = interface.log('hello', LevelsByName.INFO)
        self.assertTrue(result)

        logger = supervisord.options.logger
        self.assertEqual(['hello'], logger.data)

    def test_log_raises_incorrect_parameters_when_level_is_bad(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)

        for bad_level in ['bad_level', 9999, None]:
            self.assertRPCError(SupervisorFaults.INCORRECT_PARAMETERS,
                                interface.log, 'hello', bad_level)

    # Helpers Methods

    def getTargetClass(self):
        from supervisor_twiddler.rpcinterface import TwiddlerNamespaceRPCInterface
        return TwiddlerNamespaceRPCInterface

    def makeOne(self, *arg, **kw):
        return self.getTargetClass()(*arg, **kw)

    def attrDictWithoutUnders(self, obj):
        """ Returns the __dict__ for an object with __unders__ removed """
        attrs = {}
        for k, v in obj.__dict__.items():
            if not k.startswith('__'): attrs[k] = v
        return attrs

    # Helper Assertion Methods

    def assertRPCError(self, code, callable, *args, **kw):
        try:
            callable(*args, **kw)
        except supervisor.xmlrpc.RPCError as e:
            self.assertEqual(e.code, code)
        else:
            self.fail('RPCError was never raised')


def test_suite():
    return unittest.findTestCases(sys.modules[__name__])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

########NEW FILE########
