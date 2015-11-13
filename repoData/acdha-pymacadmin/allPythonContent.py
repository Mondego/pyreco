__FILENAME__ = airport-update
#!/usr/bin/python
# encoding: utf-8
"""
Usage: airport-update.py SSID NEW_PASSWORD

Updates the System keychain to replace the existing password for the specified
SSID with NEW_PASSWORD

BUG: Currently provides no way to set a password for a previously-unseen SSID
"""

import sys
import os
from PyMacAdmin.Security.Keychain import Keychain


def main():
    if len(sys.argv) < 3:
        print >> sys.stderr, __doc__.strip()
        sys.exit(1)

    ssid, new_password = sys.argv[1:3]

    if os.getuid() == 0:
        keychain = Keychain("/Library/Keychains/System.keychain")
    else:
        keychain = Keychain()

    try:
        item = keychain.find_generic_password(account_name=ssid)
        if item.password != new_password:
            item.update_password(new_password)

    except RuntimeError, exc:
        print >> sys.stderr, "Unable to change password for Airport network %s: %s" % (ssid, exc)
        sys.exit(1)

    print "Changed password for AirPort network %s to %s" % (ssid, new_password)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = crankd
#!/usr/bin/python2.7
# encoding: utf-8

"""
Usage: %prog

Monitor system event notifications

Configuration:

The configuration file is divided into sections for each class of
events. Each section is a dictionary using the event condition as the
key ("NSWorkspaceDidWakeNotification", "State:/Network/Global/IPv4",
etc). Each event must have one of the following properties:

command:      a shell command
function:     the name of a python function
class:        the name of a python class which will be instantiated once
              and have methods called as events occur.
method:       (class, method) tuple
"""

from Cocoa import \
    CFAbsoluteTimeGetCurrent, \
    CFRunLoopAddSource, \
    CFRunLoopAddTimer, \
    CFRunLoopTimerCreate, \
    NSObject, \
    NSRunLoop, \
    NSWorkspace, \
    kCFRunLoopCommonModes

from SystemConfiguration import \
    SCDynamicStoreCopyKeyList, \
    SCDynamicStoreCreate, \
    SCDynamicStoreCreateRunLoopSource, \
    SCDynamicStoreSetNotificationKeys

from FSEvents import \
    FSEventStreamCreate, \
    FSEventStreamStart, \
    FSEventStreamScheduleWithRunLoop, \
    kFSEventStreamEventIdSinceNow, \
    kCFRunLoopDefaultMode, \
    kFSEventStreamEventFlagMustScanSubDirs, \
    kFSEventStreamEventFlagUserDropped, \
    kFSEventStreamEventFlagKernelDropped

import os
import os.path
import logging
import logging.handlers
import sys
import re
from subprocess import call
from optparse import OptionParser
from plistlib import readPlist, writePlist
from PyObjCTools import AppHelper
from functools import partial
import signal
from datetime import datetime


VERSION          = '$Revision: #4 $'

HANDLER_OBJECTS  = dict()     # Events which have a "class" handler use an instantiated object; we want to load only one copy
SC_HANDLERS      = dict()     # Callbacks indexed by SystemConfiguration keys
FS_WATCHED_FILES = dict()     # Callbacks indexed by filesystem path
WORKSPACE_HANDLERS = dict()   # handlers for workspace events


class BaseHandler(object):
    # pylint: disable-msg=C0111,R0903
    pass

class NotificationHandler(NSObject):
    """Simple base class for handling NSNotification events"""
    # Method names and class structure are dictated by Cocoa & PyObjC, which
    # is substantially different from PEP-8:
    # pylint: disable-msg=C0103,W0232,R0903

    def init(self):
        """NSObject-compatible initializer"""
        self = super(NotificationHandler, self).init()
        if self is None: return None
        self.callable = self.not_implemented
        return self # NOTE: Unlike Python, NSObject's init() must return self!
    
    def not_implemented(self, *args, **kwargs):
        """A dummy function which exists only to catch configuration errors"""
        # TODO: Is there a better way to report the caller's location?
        import inspect
        stack = inspect.stack()
        my_name = stack[0][3]
        caller  = stack[1][3]
        raise NotImplementedError(
            "%s should have been overridden. Called by %s as: %s(%s)" % (
                my_name,
                caller,
                my_name,
                ", ".join(map(repr, args) + [ "%s=%s" % (k, repr(v)) for k,v in kwargs.items() ])
            )
        )

    def onNotification_(self, the_notification):
        """Pass an NSNotifications to our handler"""
        if the_notification.userInfo:
            user_info = the_notification.userInfo()
        else:
            user_info = None
        self.callable(user_info=user_info) # pylint: disable-msg=E1101


def log_list(msg, items, level=logging.INFO):
    """
    Record a a list of values with a message

    This would ordinarily be a simple logging call but we want to keep the
    length below the 1024-byte syslog() limitation and we'll format things
    nicely by repeating our message with as many of the values as will fit.

    Individual items longer than the maximum length will be truncated.
    """

    max_len    = 1024 - len(msg % "")
    cur_len    = 0
    cur_items  = list()

    while [ i[:max_len] for i in items]:
        i = items.pop()
        if cur_len + len(i) + 2 > max_len:
            logging.info(msg % ", ".join(cur_items))
            cur_len = 0
            cur_items = list()

        cur_items.append(i)
        cur_len += len(i) + 2

    logging.log(level, msg % ", ".join(cur_items))

def get_callable_for_event(name, event_config, context=None):
    """
        Returns a callable object which can be used as a callback for any
        event. The returned function has context information, logging, etc.
        included so they do not need to be passed when the actual event
        occurs.

        NOTE: This function does not process "class" handlers - by design they
        are passed to the system libraries which expect a delegate object with
        various event handling methods
    """

    kwargs = {
        'context':  context,
        'key':      name,
        'config':   event_config,
    }

    if "command" in event_config:
        f = partial(do_shell, event_config["command"], **kwargs)
    elif "function" in event_config:
        f = partial(get_callable_from_string(event_config["function"]), **kwargs)
    elif "method" in event_config:
        f = partial(getattr(get_handler_object(event_config['method'][0]), event_config['method'][1]), **kwargs)
    else:
        raise AttributeError("%s have a class, method, function or command" % name)

    return f


def get_mod_func(callback):
    """Convert a fully-qualified module.function name to (module, function) - stolen from Django"""
    try:
        dot = callback.rindex('.')
    except ValueError:
        return (callback, '')
    return (callback[:dot], callback[dot+1:])


def get_callable_from_string(f_name):
    """Takes a string containing a function name (optionally module qualified) and returns a callable object"""
    try:
        mod_name, func_name = get_mod_func(f_name)
        if mod_name == "" and func_name == "":
            raise AttributeError("%s couldn't be converted to a module or function name" % f_name)

        module = __import__(mod_name)

        if func_name == "":
            func_name = mod_name # The common case is an eponymous class

        return getattr(module, func_name)

    except (ImportError, AttributeError), exc:
        raise RuntimeError("Unable to create a callable object for '%s': %s" % (f_name, exc))


def get_handler_object(class_name):
    """Return a single instance of the given class name, instantiating it if necessary"""

    if class_name not in HANDLER_OBJECTS:
        h_obj = get_callable_from_string(class_name)()
        if isinstance(h_obj, BaseHandler):
            pass # TODO: Do we even need BaseHandler any more?
        HANDLER_OBJECTS[class_name] = h_obj

    return HANDLER_OBJECTS[class_name]


def handle_sc_event(store, changed_keys, info):
    """Fire every event handler for one or more events"""

    for key in changed_keys:
        SC_HANDLERS[key](key=key, info=info)


def list_events(option, opt_str, value, parser):
    """Displays the list of events which can be monitored on the current system"""

    print 'On this system SystemConfiguration supports these events:'
    for event in sorted(SCDynamicStoreCopyKeyList(get_sc_store(), '.*')):
        print "\t", event

    print
    print "Standard NSWorkspace Notification messages:\n\t",
    print "\n\t".join('''
        NSWorkspaceDidLaunchApplicationNotification
        NSWorkspaceDidMountNotification
        NSWorkspaceDidPerformFileOperationNotification
        NSWorkspaceDidTerminateApplicationNotification
        NSWorkspaceDidUnmountNotification
        NSWorkspaceDidWakeNotification
        NSWorkspaceSessionDidBecomeActiveNotification
        NSWorkspaceSessionDidResignActiveNotification
        NSWorkspaceWillLaunchApplicationNotification
        NSWorkspaceWillPowerOffNotification
        NSWorkspaceWillSleepNotification
        NSWorkspaceWillUnmountNotification
    '''.split())

    sys.exit(0)


def process_commandline():
    """
        Process command-line options
        Load our preference file
        Configure the module path to add Application Support directories
    """
    parser          = OptionParser(__doc__.strip())
    support_path    = '/Library/' if os.getuid() == 0 else os.path.expanduser('~/Library/')
    preference_file = os.path.join(support_path, 'Preferences', 'com.googlecode.pymacadmin.crankd.plist')
    module_path     = os.path.join(support_path, 'Application Support/crankd')

    if os.path.exists(module_path):
        sys.path.append(module_path)
    else:
        print >> sys.stderr, "Module directory %s does not exist: Python handlers will need to use absolute pathnames" % module_path

    parser.add_option("-f", "--config", dest="config_file", help='Use an alternate config file instead of %default', default=preference_file)
    parser.add_option("-l", "--list-events", action="callback", callback=list_events, help="List the events which can be monitored")
    parser.add_option("-d", "--debug", action="count", default=False, help="Log detailed progress information")
    (options, args) = parser.parse_args()

    if len(args):
        parser.error("Unknown command-line arguments: %s" % args)

    options.support_path = support_path
    options.config_file = os.path.realpath(options.config_file)

    # This is somewhat messy but we want to alter the command-line to use full
    # file paths in case someone's code changes the current directory or the
    sys.argv = [ os.path.realpath(sys.argv[0]), ]

    if options.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        sys.argv.append("--debug")

    if options.config_file:
        sys.argv.append("--config")
        sys.argv.append(options.config_file)

    return options


def load_config(options):
    """Load our configuration from plist or create a default file if none exists"""
    if not os.path.exists(options.config_file):
        logging.info("%s does not exist - initializing with an example configuration" % CRANKD_OPTIONS.config_file)
        print >>sys.stderr, 'Creating %s with default options for you to customize' % options.config_file
        print >>sys.stderr, '%s --list-events will list the events you can monitor on this system' % sys.argv[0]
        example_config = {
            'SystemConfiguration': {
                'State:/Network/Global/IPv4': {
                    'command': '/bin/echo "Global IPv4 config changed"'
                }
            },
            'NSWorkspace': {
                'NSWorkspaceDidMountNotification': {
                    'command': '/bin/echo "A new volume was mounted!"'
                },
                'NSWorkspaceDidWakeNotification': {
                    'command': '/bin/echo "The system woke from sleep!"'
                },
                'NSWorkspaceWillSleepNotification': {
                    'command': '/bin/echo "The system is about to go to sleep!"'
                }
            }
        }
        writePlist(example_config, options.config_file)
        sys.exit(1)

    logging.info("Loading configuration from %s" % CRANKD_OPTIONS.config_file)

    plist = readPlist(options.config_file)

    if "imports" in plist:
        for module in plist['imports']:
            try:
                __import__(module)
            except ImportError, exc:
                print >> sys.stderr, "Unable to import %s: %s" % (module, exc)
                sys.exit(1)
    return plist


def configure_logging():
    """Configures the logging module"""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Enable logging to syslog as well:
    # Normally this would not be necessary but logging assumes syslog listens on
    # localhost syslog/udp, which is disabled on 10.5 (rdar://5871746)
    syslog = logging.handlers.SysLogHandler('/var/run/syslog')
    syslog.setFormatter(logging.Formatter('%(name)s: %(message)s'))
    syslog.setLevel(logging.INFO)
    logging.getLogger().addHandler(syslog)


def get_sc_store():
    """Returns an SCDynamicStore instance"""
    return SCDynamicStoreCreate(None, "crankd", handle_sc_event, None)


def add_workspace_notifications(nsw_config):
    # See http://developer.apple.com/documentation/Cocoa/Conceptual/Workspace/Workspace.html
    notification_center = NSWorkspace.sharedWorkspace().notificationCenter()

    for event in nsw_config:
        event_config = nsw_config[event]

        if "class" in event_config:
            obj         = get_handler_object(event_config['class'])
            objc_method = "on%s:" % event
            py_method   = objc_method.replace(":", "_")
            if not hasattr(obj, py_method) or not callable(getattr(obj, py_method)):
                print  >> sys.stderr, \
                    "NSWorkspace Notification %s: handler class %s must define a %s method" % (event, event_config['class'], py_method)
                sys.exit(1)

            notification_center.addObserver_selector_name_object_(obj, objc_method, event, None)
        else:
            handler          = NotificationHandler.new()
            handler.name     = "NSWorkspace Notification %s" % event
            handler.callable = get_callable_for_event(event, event_config, context=handler.name)

            assert(callable(handler.onNotification_))

            notification_center.addObserver_selector_name_object_(handler, "onNotification:", event, None)
            WORKSPACE_HANDLERS[event] = handler

    log_list("Listening for these NSWorkspace notifications: %s", nsw_config.keys())


def add_sc_notifications(sc_config):
    """
    This uses the SystemConfiguration framework to get a SCDynamicStore session
    and register for certain events. See the Apple SystemConfiguration
    documentation for details:

    <http://developer.apple.com/documentation/Networking/Reference/SysConfig/SCDynamicStore/CompositePage.html>

    TN1145 may also be of interest:
        <http://developer.apple.com/technotes/tn/tn1145.html>

    Inspired by the PyObjC SystemConfiguration callback demos:
    <https://svn.red-bean.com/pyobjc/trunk/pyobjc/pyobjc-framework-SystemConfiguration/Examples/CallbackDemo/>
    """

    keys = sc_config.keys()

    try:
        for key in keys:
            SC_HANDLERS[key] = get_callable_for_event(key, sc_config[key], context="SystemConfiguration: %s" % key)
    except AttributeError, exc:
        print  >> sys.stderr, "Error configuring SystemConfiguration events: %s" % exc
        sys.exit(1)

    store = get_sc_store()

    SCDynamicStoreSetNotificationKeys(store, None, keys)

    # Get a CFRunLoopSource for our store session and add it to the application's runloop:
    CFRunLoopAddSource(
        NSRunLoop.currentRunLoop().getCFRunLoop(),
        SCDynamicStoreCreateRunLoopSource(None, store, 0),
        kCFRunLoopCommonModes
    )

    log_list("Listening for these SystemConfiguration events: %s", keys)


def add_fs_notifications(fs_config):
    for path in fs_config:
        add_fs_notification(path, get_callable_for_event(path, fs_config[path], context="FSEvent: %s" % path))


def add_fs_notification(f_path, callback):
    """Adds an FSEvent notification for the specified path"""
    path = os.path.realpath(os.path.expanduser(f_path))
    if not os.path.exists(path):
        raise AttributeError("Cannot add an FSEvent notification: %s does not exist!" % path)

    if not os.path.isdir(path):
        path = os.path.dirname(path)

    try:
        FS_WATCHED_FILES[path].append(callback)
    except KeyError:
        FS_WATCHED_FILES[path] = [callback]


def start_fs_events():
    stream_ref = FSEventStreamCreate(
        None,                               # Use the default CFAllocator
        fsevent_callback,
        None,                               # We don't need a FSEventStreamContext
        FS_WATCHED_FILES.keys(),
        kFSEventStreamEventIdSinceNow,      # We only want events which happen in the future
        1.0,                                # Process events within 1 second
        0                                   # We don't need any special flags for our stream
    )

    if not stream_ref:
        raise RuntimeError("FSEventStreamCreate() failed!")

    FSEventStreamScheduleWithRunLoop(stream_ref, NSRunLoop.currentRunLoop().getCFRunLoop(), kCFRunLoopDefaultMode)

    if not FSEventStreamStart(stream_ref):
        raise RuntimeError("Unable to start FSEvent stream!")

    logging.debug("FSEventStream started for %d paths: %s" % (len(FS_WATCHED_FILES), ", ".join(FS_WATCHED_FILES)))


def fsevent_callback(stream_ref, full_path, event_count, paths, masks, ids):
    """Process an FSEvent (consult the Cocoa docs) and call each of our handlers which monitors that path or a parent"""
    for i in range(event_count):
        path = os.path.dirname(paths[i])

        if masks[i] & kFSEventStreamEventFlagMustScanSubDirs:
            recursive = True

        if masks[i] & kFSEventStreamEventFlagUserDropped:
            logging.error("We were too slow processing FSEvents and some events were dropped")
            recursive = True

        if masks[i] & kFSEventStreamEventFlagKernelDropped:
            logging.error("The kernel was too slow processing FSEvents and some events were dropped!")
            recursive = True
        else:
            recursive = False

        for i in [k for k in FS_WATCHED_FILES if path.startswith(k)]:
            logging.debug("FSEvent: %s: processing %d callback(s) for path %s" % (i, len(FS_WATCHED_FILES[i]), path))
            for j in FS_WATCHED_FILES[i]:
                j(i, path=path, recursive=recursive)


def timer_callback(*args):
    """Handles the timer events which we use simply to have the runloop run regularly. Currently this logs a timestamp for debugging purposes"""
    logging.debug("timer callback at %s" % datetime.now())


def main():
    configure_logging()

    global CRANKD_OPTIONS, CRANKD_CONFIG
    CRANKD_OPTIONS = process_commandline()
    CRANKD_CONFIG  = load_config(CRANKD_OPTIONS)

    if "NSWorkspace" in CRANKD_CONFIG:
        add_workspace_notifications(CRANKD_CONFIG['NSWorkspace'])

    if "SystemConfiguration" in CRANKD_CONFIG:
        add_sc_notifications(CRANKD_CONFIG['SystemConfiguration'])

    if "FSEvents" in CRANKD_CONFIG:
        add_fs_notifications(CRANKD_CONFIG['FSEvents'])

    # We reuse our FSEvents code to watch for changes to our files and
    # restart if any of our libraries have been updated:
    add_conditional_restart(CRANKD_OPTIONS.config_file, "Configuration file %s changed" % CRANKD_OPTIONS.config_file)
    for m in filter(lambda i: i and hasattr(i, '__file__'), sys.modules.values()):
        if m.__name__ == "__main__":
            msg = "%s was updated" % m.__file__
        else:
            msg = "Module %s was updated" % m.__name__

        add_conditional_restart(m.__file__, msg)

    signal.signal(signal.SIGHUP, partial(restart, "SIGHUP received"))

    start_fs_events()

    # NOTE: This timer is basically a kludge around the fact that we can't reliably get
    #       signals or Control-C inside a runloop. This wakes us up often enough to
    #       appear tolerably responsive:
    CFRunLoopAddTimer(
        NSRunLoop.currentRunLoop().getCFRunLoop(),
        CFRunLoopTimerCreate(None, CFAbsoluteTimeGetCurrent(), 2.0, 0, 0, timer_callback, None),
        kCFRunLoopCommonModes
    )

    try:
        AppHelper.runConsoleEventLoop(installInterrupt=True)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received, exiting")

    sys.exit(0)

def create_env_name(name):
    """
    Converts input names into more traditional shell environment name style

    >>> create_env_name("NSApplicationBundleIdentifier")
    'NSAPPLICATION_BUNDLE_IDENTIFIER'
    >>> create_env_name("NSApplicationBundleIdentifier-1234$foobar!")
    'NSAPPLICATION_BUNDLE_IDENTIFIER_1234_FOOBAR'
    """
    new_name = re.sub(r'''(?<=[a-z])([A-Z])''', '_\\1', name)
    new_name = re.sub(r'\W+', '_', new_name)
    new_name = re.sub(r'_{2,}', '_', new_name)
    return new_name.upper().strip("_")

def do_shell(command, context=None, **kwargs):
    """Executes a shell command with logging"""
    logging.info("%s: executing %s" % (context, command))

    child_env = {'CRANKD_CONTEXT': context}

    # We'll pull a subset of the available information in for shell scripts.
    # Anyone who needs more will probably want to write a Python handler
    # instead so they can reuse things like our logger & config info and avoid
    # ordeals like associative arrays in Bash
    for k in [ 'info', 'key' ]:
        if k in kwargs and kwargs[k]:
            child_env['CRANKD_%s' % k.upper()] = str(kwargs[k])

    user_info = kwargs.get("user_info")
    if user_info:
        for k, v in user_info.items():
            child_env[create_env_name(k)] = str(v)

    try:
        rc = call(command, shell=True, env=child_env)
        if rc == 0:
            logging.debug("`%s` returned %d" % (command, rc))
        elif rc < 0:
            logging.error("`%s` was terminated by signal %d" % (command, -rc))
        else:
            logging.error("`%s` returned %d" % (command, rc))
    except OSError, exc:
        logging.error("Got an exception when executing %s:" % (command, exc))


def add_conditional_restart(file_name, reason):
    """FSEvents monitors directories, not files. This function uses stat to
    restart only if the file's mtime has changed"""
    file_name = os.path.realpath(file_name)
    while not os.path.exists(file_name):
        file_name = os.path.dirname(file_name)
    orig_stat = os.stat(file_name).st_mtime

    def cond_restart(*args, **kwargs):
        try:
            if os.stat(file_name).st_mtime != orig_stat:
                restart(reason)
        except (OSError, IOError, RuntimeError), exc:
            restart("Exception while checking %s: %s" % (file_name, exc))

    add_fs_notification(file_name, cond_restart)


def restart(reason, *args, **kwargs):
    """Perform a complete restart of the current process using exec()"""
    logging.info("Restarting: %s" % reason)
    os.execv(sys.argv[0], sys.argv)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = create-location
#!/usr/bin/python
"""
Usage: %prog USER_VISIBLE_NAME

Creates a new SystemConfiguration location for use in Network Preferences by
copying the Automatic location
"""

from SystemConfiguration import *
from CoreFoundation import *
import sys
import re
import logging
from optparse import OptionParser


def copy_set(path, old_id, old_set):
    new_set      = CFPropertyListCreateDeepCopy(None, old_set, kCFPropertyListMutableContainersAndLeaves)
    new_set_path = SCPreferencesPathCreateUniqueChild(sc_prefs, path)

    if not new_set_path \
      or not re.match(r"^%s/[^/]+$" % path, new_set_path):
        raise RuntimeError("SCPreferencesPathCreateUniqueChild() returned an invalid path for the new location: %s" % new_set_path)

    return new_set_path, new_set


def main():
    # Ugly but this is easiest until we refactor this into an SCPrefs class:
    global sc_prefs

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    parser = OptionParser(__doc__.strip())

    parser.add_option('-v', '--verbose', action="store_true",
        help="Print more information"
    )

    (options, args) = parser.parse_args()

    if not args:
        parser.error("You must specify the user-visible name for the new location")

    if options.verbose:
        logging.getLogger().setLevel(logging.DEBUG)


    new_name   = " ".join(args)
    sc_prefs   = SCPreferencesCreate(None, "create_location", None)
    sets       = SCPreferencesGetValue(sc_prefs, kSCPrefSets)
    old_set_id = None
    old_set    = None

    for k in sets:
        if sets[k][kSCPropUserDefinedName] == new_name:
            raise RuntimeError("A set named %s already exists" % new_name)
        elif sets[k][kSCPropUserDefinedName] == "Automatic":
            old_set_id = k

    if not old_set_id:
        raise RuntimeError("Couldn't find Automatic set")

    old_set = sets[old_set_id]
    logging.debug("Old set %s:\n%s" % (old_set_id, old_set))

    logging.info('Creating "%s" using a copy of "%s"' % (new_name, old_set[kSCPropUserDefinedName]))
    new_set_path, new_set           = copy_set("/%s" % kSCPrefSets, old_set_id, old_set)
    new_set_id                      = new_set_path.split('/')[-1]
    new_set[kSCPropUserDefinedName] = new_name

    service_map = dict()

    for old_service_id in old_set[kSCCompNetwork][kSCCompService]:
        assert(
            old_set[kSCCompNetwork][kSCCompService][old_service_id][kSCResvLink].startswith("/%s" % kSCPrefNetworkServices)
        )

        new_service_path = SCPreferencesPathCreateUniqueChild(sc_prefs, "/%s" % kSCPrefNetworkServices)
        new_service_id   = new_service_path.split("/")[2]
        new_service_cf   = CFPropertyListCreateDeepCopy(
            None,
            SCPreferencesGetValue(sc_prefs, kSCPrefNetworkServices)[old_service_id],
            kCFPropertyListMutableContainersAndLeaves
        )
        SCPreferencesPathSetValue(sc_prefs, new_service_path, new_service_cf)

        new_set[kSCCompNetwork][kSCCompService][new_service_id] = {
            kSCResvLink: new_service_path
        }
        del new_set[kSCCompNetwork][kSCCompService][old_service_id]

        service_map[old_service_id] = new_service_id

    for proto in new_set[kSCCompNetwork][kSCCompGlobal]:
        new_set[kSCCompNetwork][kSCCompGlobal][proto][kSCPropNetServiceOrder] = map(
            lambda k: service_map[k],
            old_set[kSCCompNetwork][kSCCompGlobal][proto][kSCPropNetServiceOrder]
        )

    SCPreferencesPathSetValue(sc_prefs, new_set_path, new_set)

    logging.debug("New Set %s:\n%s\n" % (new_set_id, new_set))

    if not SCPreferencesCommitChanges(sc_prefs):
        raise RuntimeError("Unable to save SystemConfiguration changes")

    if not SCPreferencesApplyChanges(sc_prefs):
        raise RuntimeError("Unable to apply SystemConfiguration changes")


if __name__ == '__main__':
    try:
        main()
    except RuntimeError, e:
        logging.critical(str(e))
        sys.exit(1)

########NEW FILE########
__FILENAME__ = delete-certificate
#!/usr/bin/env python2.5

from PyMacAdmin import carbon_call, load_carbon_framework
from PyMacAdmin.Security import kSecCertificateItemClass
from PyMacAdmin.Security.Keychain import SecKeychainAttribute, SecKeychainAttributeList

import sys
import ctypes
from CoreFoundation import CFRelease

Security = load_carbon_framework('/System/Library/Frameworks/Security.framework/Versions/Current/Security')

label    = "<some label text here>"
plabel   = ctypes.c_char_p(label)
tag      = 'labl'

attr     = SecKeychainAttribute(tag, 1, plabel)
attrList = SecKeychainAttributeList(1, attr)

# http://developer.apple.com/DOCUMENTATION/Security/Reference/keychainservices/Reference/reference.html#//apple_ref/c/tdef/SecItemClass

searchRef = ctypes.c_void_p()
itemRef   = ctypes.c_void_p()

try:
    Security.SecKeychainSearchCreateFromAttributes(
        None,
        kSecCertificateItemClass,
        ctypes.byref(attrList),
        ctypes.pointer(searchRef)
    )

    Security.SecKeychainSearchCopyNext(
        searchRef,
        ctypes.byref(itemRef)
    )

    if searchRef:
        CFRelease(searchRef)

    Security.SecKeychainItemDelete(itemRef)

    if itemRef:
        CFRelease(itemRef)
except RuntimeError, e:
    print >>sys.stderr, "ERROR: %s" % e
    sys.exit(1)
########NEW FILE########
__FILENAME__ = keychain-delete
#!/usr/bin/env python
# encoding: utf-8
"""
Usage: %prog [--service=SERVICE_NAME] [--account=ACCOUNT_NAME] [--keychain=/path/to/keychain]

Remove the specified password from the keychain
"""

from PyMacAdmin.Security.Keychain import Keychain
import os
import sys
from optparse import OptionParser


def main():
    parser = OptionParser(__doc__.strip())

    parser.add_option('-a', '--account', '--account-name',
        help="Set the account name"
    )

    parser.add_option('-s', '--service', '--service-name',
        help="Set the service name"
    )

    parser.add_option('-k', '--keychain',
        help="Path to the keychain file"
    )

    (options, args) = parser.parse_args()

    if not options.keychain and os.getuid() == 0:
        options.keychain = "/Library/Keychains/System.keychain"

    if not (options.account or options.service):
        parser.error("You must specify either an account or service name")

    try:
        keychain = Keychain(options.keychain)
        item = keychain.find_generic_password(
            service_name=options.service,
            account_name=options.account
        )

        print "Removing %s" % item
        keychain.remove(item)
    except KeyError, exc:
        print >>sys.stderr, exc.message
        sys.exit(0)
    except RuntimeError, exc:
        print >>sys.stderr, "Unable to delete keychain item: %s" % exc
        sys.exit(1)

if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = proxy-setenv
#!/usr/bin/python
"""
Usage: eval `proxy-setenv.py`

Generates Bourne-shell environmental variable declarations based on the
current system proxy settings
"""

from SystemConfiguration import SCDynamicStoreCopyProxies

proxies = SCDynamicStoreCopyProxies(None)

if 'HTTPEnable' in proxies and proxies['HTTPEnable']:
    print "export http_proxy=http://%s:%s/" % (proxies['HTTPProxy'], proxies['HTTPPort'])
else:
    print "unset http_proxy"

if 'FTPEnable' in proxies and proxies['FTPEnable']:
    print "export ftp_proxy=http://%s:%s/" % (proxies['FTPProxy'], proxies['FTPPort'])
else:
    print "unset ftp_proxy"

########NEW FILE########
__FILENAME__ = set-proxy
#!/usr/bin/python
# encoding: utf-8
"""
%prog --enable --protocol=HTTP --server=proxy.example.edu --port=3128

Configures the system proxy settings from the command-line using the
PyMacAdmin SystemConfiguration module
"""

from PyMacAdmin.SCUtilities.SCPreferences import SCPreferences
from socket import gethostbyname, gaierror
import sys


def main():
    sc_prefs = SCPreferences()

    from optparse import OptionParser
    parser = OptionParser(__doc__.strip())

    parser.add_option('--enable',   dest='enable', action="store_true", default=True,
        help='Enable proxy for the specified protocol'
    )
    parser.add_option('--disable',  dest='enable', action='store_false',
        help='Disable proxy for the specified protocol'
    )
    parser.add_option('--protocol', choices=sc_prefs.proxy_protocols, metavar='PROTOCOL',
        help='Specify the protocol (%s)' % ", ".join(sc_prefs.proxy_protocols)
    )
    parser.add_option('--server',   metavar='SERVER',
        help="Specify the proxy server's hostname"
    )
    parser.add_option('--port',     type='int', metavar='PORT',
        help="Specify the proxy server's port"
    )

    (options, args) = parser.parse_args()

    # optparser inexplicably lacks a require option due to extreme
    # pedanticism but it's not worth switching to argparse:
    if not options.protocol:
        print >> sys.stderr, "ERROR: You must specify a protocol to %s" % ("enable" if options.enable else "disable")
        sys.exit(1)

    if options.enable and not ( options.server and options.port ):
            print >> sys.stderr, "ERROR: You must specify a %s proxy server and port" % options.protocol
            sys.exit(1)

    if options.server:
        try:
            gethostbyname(options.server)
        except gaierror, exc:
            print >> sys.stderr, "ERROR: couldn't resolve server hostname %s: %s" % (options.server, exc.args[1]) # e.message is broken in the standard socket.gaierror!
            sys.exit(1)

    try:
        sc_prefs.set_proxy(enable=options.enable, protocol=options.protocol, server=options.server, port=options.port)
        sc_prefs.save()
    except RuntimeError, exc:
        print >> sys.stderr, exc.message

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = FolderWatcher
import pprint

class FolderWatcher(object):
    def folder_changed(self, *args, **kwargs):
        print "Folder %(path)s changed" % kwargs

########NEW FILE########
__FILENAME__ = MountManager
from PyMacAdmin.crankd.handlers import BaseHandler

class MountManager(BaseHandler):
    def onNSWorkspaceDidMountNotification_(self, aNotification):
        path = aNotification.userInfo()['NSDevicePath']
        self.logger.info("Mount: %s" % path)

    def onNSWorkspaceDidUnmountNotification_(self, aNotification):
        path = aNotification.userInfo()['NSDevicePath']
        self.logger.info("Unmount: %s" % path)


########NEW FILE########
__FILENAME__ = NetworkConfig
# encoding: utf-8

class NetworkConfig(object):
    """Handles network related changes for crankd"""
    def atalk_change(self, context=None, **kwargs):
        logger.info("Atalk? You poor person, you…")

########NEW FILE########
__FILENAME__ = generate-event-plist
#!/usr/bin/env python

"""
Generates a list of OS X system events into a plist for crankd.

This is designed to create a large (but probably not comprehensive) sample
of the events generated by Mac OS X that crankd can tap into.  The generated
file will call the 'tunnel.sh' as the command for each event; said fail can
be easily edited to redirect the output to wherever you would like it to go.

"""

OUTPUT_FILE = "crankd-config.plist"

from SystemConfiguration import SCDynamicStoreCopyKeyList, SCDynamicStoreCreate

# Each event has a general event type, and a specific event
# The category is the key, and the value is a list of specific events
event_dict = {}

def AddEvent(event_category, specific_event):
    """Adds an event to the event dictionary"""
    if event_category not in event_dict:
        event_dict[event_category] = []
    event_dict[event_category].append(specific_event)

def AddCategoryOfEvents(event_category, events):
    """Adds a list of events that all belong to the same category"""
    for specific_event in events:
        AddEvent(event_category, specific_event)

def AddKnownEvents():
    """Here we add all the events that we know of to the dictionary"""

    # Add a bunch of dynamic events
    store = SCDynamicStoreCreate(None, "generate_event_plist", None, None)
    AddCategoryOfEvents(u"SystemConfiguration",
                        SCDynamicStoreCopyKeyList(store, ".*"))

    # Add some standard NSWorkspace events
    AddCategoryOfEvents(u"NSWorkspace",
                        u'''
        NSWorkspaceDidLaunchApplicationNotification
        NSWorkspaceDidMountNotification
        NSWorkspaceDidPerformFileOperationNotification
        NSWorkspaceDidTerminateApplicationNotification
        NSWorkspaceDidUnmountNotification
        NSWorkspaceDidWakeNotification
        NSWorkspaceSessionDidBecomeActiveNotification
        NSWorkspaceSessionDidResignActiveNotification
        NSWorkspaceWillLaunchApplicationNotification
        NSWorkspaceWillPowerOffNotification
        NSWorkspaceWillSleepNotification
        NSWorkspaceWillUnmountNotification
                        '''.split())

def PrintEvents():
    """Prints all the events, for debugging purposes"""
    for category in sorted(event_dict):

        print category

        for event in sorted(event_dict[category]):
            print "\t" + event

def OutputEvents():
    """Outputs all the events to a file"""

    # print the header for the file
    plist = open(OUTPUT_FILE, 'w')

    print >>plist, '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>'''

    for category in sorted(event_dict):

        # print out the category
        print >>plist, "  <key>%s</key>\n      <dict>" % category

        for event in sorted(event_dict[category]):
            print >>plist, """
        <key>%s</key>
        <dict>
          <key>command</key>
          <string>%s '%s' '%s'</string>
        </dict>""" % ( event, 'tunnel.sh', category, event )

        # end the category
        print >>plist, "  </dict>"

    # end the plist file
    print >>plist, '</dict>'
    print >>plist, '</plist>'

    plist.close()

def main():
    """Runs the program"""
    AddKnownEvents()
    #PrintEvents()
    OutputEvents()

main()



########NEW FILE########
__FILENAME__ = ProxyManager
import socket
import os
import logging

from PyMacAdmin import crankd
from PyMacAdmin.SCUtilities.SCPreferences import SCPreferences

class ProxyManager(crankd.handlers.BaseHandler):
    """
        crankd event handler which selectively enables a SOCKS process based
        on the current network address
    """

    def __init__(self):
        super(crankd.handlers.BaseHandler, self).__init__()
        self.socks_server = 'localhost'
        self.socks_port   = '1080'

        # Fire once at startup to handle situations like system bootup or a
        # crankd restart:
        self.update_proxy_settings()

    def onNSWorkspaceDidMountNotification_(self, aNotification):
        """
        Dummy handler for testing purposes which calls the update code when a
        volume is mounted - this simplifies testing or demos using a DMG.

        BUG: Although harmless, this should be removed in production
        """
        self.update_proxy_settings()

    def update_proxy_settings(self, *args, **kwargs):
        """
        When the network configuration changes, this updates the SOCKS proxy
        settings based the current IP address(es)
        """
        # Open a SystemConfiguration preferences session:
        sc_prefs = SCPreferences()

        # We want to enable the server when our hostname is not on the corporate network:
        # BUG: This does not handle multi-homed systems well:
        current_address = socket.gethostbyname(socket.getfqdn())
        new_state       = not current_address.startswith('10.0.1.')

        logging.info(
            "Current address is now %s: SOCKS proxy will be %s" % (
                current_address,
                "Enabled" if new_state else "Disabled"
            )
        )

        try:
            sc_prefs.set_proxy(
                enable=new_state,
                protocol='SOCKS',
                server=self.socks_server,
                port=self.socks_port
            )
            sc_prefs.save()

            logging.info("Successfully updated SOCKS proxy setting")
        except RuntimeError, e:
            logging.error("Unable to set SOCKS proxy setting: %s" % e.message)

########NEW FILE########
__FILENAME__ = airport-update
#!/usr/bin/python
"""Updates the password for an Airport network"""

import ctypes
import sys

SECURITY = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/Security.framework/Versions/Current/Security')

def find_airport_password(ssid):
    """Returns the password and a Keychain item reference for the requested Airport network"""
    item            = ctypes.c_void_p()
    password_length = ctypes.c_uint32(0)
    password_data   = ctypes.c_char_p(256)

    system_keychain = ctypes.c_void_p()
    keychain_ptr    = ctypes.pointer(system_keychain)

    rc = SECURITY.SecKeychainOpen("/Library/Keychains/System.keychain", keychain_ptr)
    if rc != 0:
        raise RuntimeError("Couldn't open system keychain: rc=%d" % rc)

    # n.b. The service name is often "AirPort Network" in the user's keychain
    #      but in the system keychain it appears to be a UUID. It might be
    #      necessary to check the description for network names which are not
    #      unique in the keychain.
    rc = SECURITY.SecKeychainFindGenericPassword (
        system_keychain,
        None,                               # Length of service name
        None,                               # Service name
        len(ssid),                          # Account name length
        ssid,                               # Account name
        ctypes.byref(password_length),      # Will be filled with pw length
        ctypes.pointer(password_data),      # Will be filled with pw data
        ctypes.pointer(item)
    )

    if rc == -25300:
        raise RuntimeError('No existing password for Airport network %s: rc=%d' % (ssid, rc))
    elif rc != 0:
        raise RuntimeError('Failed to find password for Airport network %s: rc=%d' % (ssid, rc))

    password = password_data.value[0:password_length.value]

    SECURITY.SecKeychainItemFreeContent(None, password_data)

    return (password, item)

def change_airport_password(ssid, new_password):
    """Sets the password for the specified Airport network to the provided value"""
    password, item = find_airport_password(ssid)

    if password != new_password:
        rc = SECURITY.SecKeychainItemModifyAttributesAndData(
            item,
            None,
            len(new_password),
            new_password
        )

        if rc == -61:
            raise RuntimeError("Unable to update password for Airport network %s: permission denied (rc = %d)" % (ssid, rc))
        elif rc != 0:
            raise RuntimeError("Unable to update password for Airport network %s: rc = %d" % (ssid, rc))

def main():
    if len(sys.argv) < 3:
        print >> sys.stderr, "Usage: %s SSID NEW_PASSWORD" % (sys.argv[0])
        sys.exit(1)

    ssid, new_password = sys.argv[1:3]

    try:
        change_airport_password(ssid, new_password)
    except RuntimeError, exc:
        print >> sys.stderr, "Unable to change password for Airport network %s: %s" % ( ssid, exc)
        sys.exit(1)

    print "Changed password for Airport network %s to %s" % (ssid, new_password)

if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = keychain-delete
#!/usr/bin/env python
# encoding: utf-8
"""
Demonstrates how to delete a Keychain item using Python's ctypes library
"""

import ctypes

service_name     = 'Service Name'
account_name     = 'Account Name'
password_length  = ctypes.c_uint32(256)
password_pointer = ctypes.c_char_p()
item             = ctypes.c_char_p()

print "Loading Security.framework"
Security = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/Security.framework/Versions/Current/Security')

print "Searching for the password"

rc = Security.SecKeychainFindGenericPassword(
    None,
    len(service_name),
    service_name,
    len(account_name),
    account_name,
    # Used if you want to  retrieve the password:
    None, # ctypes.byref(password_length),
    None, # ctypes.pointer(password_pointer),
    ctypes.pointer(item)
)

if rc != 0:
    raise RuntimeError('SecKeychainFindGenericPassword failed: rc=%d' % rc)

print "Deleting Keychain item"

rc = Security.SecKeychainItemDelete( item )

if rc != 0:
    raise RuntimeError('SecKeychainItemDelete failed: rc=%d' % rc)


########NEW FILE########
__FILENAME__ = keychain-update
#!/usr/bin/env python
# encoding: utf-8
"""
Updates existing keychain internet password items with a new password.
Usage: keychain-internet-password-update.py account_name new_password

Contributed by Matt Rosenberg
"""

import ctypes
import sys

# Load Security.framework
Security = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/Security.framework/Versions/Current/Security')

def FourCharCode(fcc):
    """Create an integer from the provided 4-byte string, required for finding keychain items based on protocol type"""
    return ord(fcc[0]) << 24 | ord(fcc[1]) << 16 | ord(fcc[2]) << 8 | ord(fcc[3])

def UpdatePassword(account_name, new_password, server_name, protocol_type_string=''):
    """
    Function to update an existing internet password keychain item

    Search for the existing item is based on account name, password, server, and
    protocol (optional). Additional search parameters are available, but are
    hard-coded to null here.

    The list of protocol type codes is in
    /System/Library/Frameworks/Security.framework/Versions/Current/Headers/SecKeychain.h
    """

    item             = ctypes.c_char_p()
    port_number      = ctypes.c_uint16(0) # Set port number to 0, works like setting null for most other search parameters
    password_length  = ctypes.c_uint32(256)
    password_pointer = ctypes.c_char_p()

    if protocol_type_string:
        protocol_type_code = FourCharCode(protocol_type_string)
    else:
        protocol_type_code = 0

    # Call function to locate existing keychain item
    rc = Security.SecKeychainFindInternetPassword(
        None,
        len(server_name),
        server_name,
        None,
        None,
        len(account_name),
        account_name,
        None,
        None,
        port_number,
        protocol_type_code,
        None,
        None, # To retrieve the current password, change this argument to: ctypes.byref(password_length)
        None, # To retrieve the current password, change this argument to: ctypes.pointer(password_pointer)
        ctypes.pointer(item)
    )

    if rc != 0:
        raise RuntimeError('Did not find existing password for server %s, protocol type %s, account name %s: rc=%d' % (server_name, protocol_type_code, account_name, rc))

    # Call function to update password
    rc = Security.SecKeychainItemModifyAttributesAndData(
        item,
        None,
        len(new_password),
        new_password
    )

    if rc != 0:
        raise RuntimeError('Failed to record new password for server %s, protocol type %s, account name %s: rc=%d' % (server_name, protocol_type_code, account_name, rc))

    return 0

# Start execution

# Check to make sure needed arguments were passed
if len(sys.argv) != 3:
    raise RuntimeError('ERROR: Incorrect number of arguments. Required usage: keychain-internet-password-update.py account_name new_password')

# Set variables from the argument list
account_name = sys.argv[1]
new_password = sys.argv[2]

# Call UpdatePassword for each password to update.
#
# If more than one keychain item will match a server and account name, you must
# specify a protocol type. Otherwise, only the first matching item will be
# updated.
#
# The list of protocol type codes is in
# /System/Library/Frameworks/Security.framework/Versions/Current/Headers/SecKeychain.h

# Update a password without specifying a protocol type
print "Updating password for site.domain.com"
UpdatePassword(account_name, new_password, 'site.domain.com')

# Update the password for an HTTP proxy
print "Updating HTTP Proxy password"
UpdatePassword(account_name, new_password, 'webproxy.domain.com', 'htpx')

# Update the password for an HTTPS proxy
print "Updating HTTPS Proxy password"
UpdatePassword(account_name, new_password, 'webproxy.domain.com', 'htsx')

print "Done!"
########NEW FILE########
__FILENAME__ = SCPreferences
#!/usr/bin/env python
# encoding: utf-8
"""
SCPreferences.py: Simplified interaction with SystemConfiguration preferences

TODO:
* Refactor getvalue/setvalue code into generic functions for dealing with things other than proxies
* Add get_proxy() to parallel set_proxy()
"""

import sys
import os
import unittest

from SystemConfiguration import *

class SCPreferences(object):
    """Utility class for working with the SystemConfiguration framework"""
    proxy_protocols = ('HTTP', 'FTP', 'SOCKS') # List of the supported protocols
    session = None

    def __init__(self):
        super(SCPreferences, self).__init__()
        self.session = SCPreferencesCreate(None, "set-proxy", None)

    def save(self):
        if not self.session:
            return
        if not SCPreferencesCommitChanges(self.session):
            raise RuntimeError("Unable to save SystemConfiguration changes")
        if not SCPreferencesApplyChanges(self.session):
            raise RuntimeError("Unable to apply SystemConfiguration changes")

    def set_proxy(self, enable=True, protocol="HTTP", server="localhost", port=3128):
        new_settings = SCPreferencesPathGetValue(self.session, u'/NetworkServices/')

        for interface in new_settings:
            new_settings[interface]['Proxies']["%sEnable" % protocol] = 1 if enable else 0
            if enable:
                new_settings[interface]['Proxies']['%sPort' % protocol]  = int(port)
                new_settings[interface]['Proxies']['%sProxy' % protocol] = server

        SCPreferencesPathSetValue(self.session, u'/NetworkServices/', new_settings)

class SCPreferencesTests(unittest.TestCase):
    def setUp(self):
        raise RuntimeError("Thwack Chris about not writing these yet")

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = Keychain
#!/usr/bin/env python
# encoding: utf-8
"""
Wrapper for the core Keychain API

Most of the internals are directly based on the native Keychain API. Apple's developer documentation is highly relevant:

http://developer.apple.com/documentation/Security/Reference/keychainservices/Reference/reference.html#//apple_ref/doc/uid/TP30000898-CH1-SW1
"""

import os
import ctypes
from PyMacAdmin import Security

class Keychain(object):
    """A friendlier wrapper for the Keychain API"""
    # TODO: Add support for SecKeychainSetUserInteractionAllowed

    def __init__(self, keychain_name=None):
        self.keychain_handle = self.open_keychain(keychain_name)

    def open_keychain(self, path=None):
        """Open a keychain file - if no path is provided, the user's default keychain will be used"""
        if not path:
            return None

        if path and not os.path.exists(path):
            raise IOError("Keychain %s does not exist" % path)

        keychain     = ctypes.c_void_p()
        keychain_ptr = ctypes.pointer(keychain)

        rc           = Security.lib.SecKeychainOpen(path, keychain_ptr)
        if rc != 0:
            raise RuntimeError("Couldn't open system keychain: rc=%d" % rc)

        return keychain

    def find_generic_password(self, service_name="", account_name=""):
        """Pythonic wrapper for SecKeychainFindGenericPassword"""
        item_p          = ctypes.c_uint32()
        password_length = ctypes.c_uint32(0)
        password_data   = ctypes.c_char_p(256)

        # For our purposes None and "" should be equivalent but we need a real
        # string for len() below:
        if not service_name:
            service_name = ""
        if not account_name:
            account_name = ""

        rc = Security.lib.SecKeychainFindGenericPassword (
            self.keychain_handle,
            len(service_name),                  # Length of service name
            service_name,                       # Service name
            len(account_name),                  # Account name length
            account_name,                       # Account name
            ctypes.byref(password_length),      # Will be filled with pw length
            ctypes.pointer(password_data),      # Will be filled with pw data
            ctypes.byref(item_p)
        )

        if rc == -25300:
            raise KeyError('No keychain entry for generic password: service=%s, account=%s' % (service_name, account_name))
        elif rc != 0:
            raise RuntimeError('Unable to retrieve generic password (service=%s, account=%s): rc=%d' % (service_name, account_name, rc))

        password = password_data.value[0:password_length.value]

        Security.lib.SecKeychainItemFreeContent(None, password_data)

        # itemRef: A reference to the keychain item from which you wish to
        # retrieve data or attributes.
        #
        # info:  A pointer to a list of tags of attributes to retrieve.
        #
        # itemClass: A pointer to the item’s class. You should pass NULL if not
        # required. See “Keychain Item Class Constants” for valid constants.
        #
        # attrList: On input, the list of attributes in this item to get; on
        # output the attributes are filled in. You should call the function
        # SecKeychainItemFreeAttributesAndData when you no longer need the
        # attributes and data.
        #
        # length: On return, a pointer to the actual length of the data.
        #
        # outData: A pointer to a buffer containing the data in this item. Pass
        # NULL if not required. You should call the function
        # SecKeychainItemFreeAttributesAndData when you no longer need the
        # attributes and data.

        info    = SecKeychainAttributeInfo()
        attrs_p = SecKeychainAttributeList_p()

        # Thank you Wil Shipley:
        # http://www.wilshipley.com/blog/2006/10/pimp-my-code-part-12-frozen-in.html
        info.count = 1
        info.tag.contents   = Security.kSecLabelItemAttr

        Security.lib.SecKeychainItemCopyAttributesAndData(item_p, ctypes.pointer(info), None, ctypes.byref(attrs_p), None, None)
        attrs = attrs_p.contents
        assert(attrs.count >= 1)

        label = attrs.attr[0].data[:attrs.attr[0].length]

        Security.lib.SecKeychainItemFreeAttributesAndData(attrs_p)

        return GenericPassword(service_name=service_name, account_name=account_name, password=password, keychain_item=item_p, label=label)

    def find_internet_password(self, account_name="", password="", server_name="", security_domain="", path="", port=0, protocol_type=None, authentication_type=None):
        """Pythonic wrapper for SecKeychainFindInternetPassword"""
        item            = ctypes.c_void_p()
        password_length = ctypes.c_uint32(0)
        password_data   = ctypes.c_char_p(256)

        if protocol_type and len(protocol_type) != 4:
            raise TypeError("protocol_type must be a valid FourCharCode - see http://developer.apple.com/documentation/Security/Reference/keychainservices/Reference/reference.html#//apple_ref/doc/c_ref/SecProtocolType")

        if authentication_type and len(authentication_type) != 4:
            raise TypeError("authentication_type must be a valid FourCharCode - see http://developer.apple.com/documentation/Security/Reference/keychainservices/Reference/reference.html#//apple_ref/doc/c_ref/SecAuthenticationType")

        if not isinstance(port, int):
            port = int(port)

        rc = Security.lib.SecKeychainFindInternetPassword(
            self.keychain_handle,
            len(server_name),
            server_name,
            len(security_domain) if security_domain else 0,
            security_domain,
            len(account_name),
            account_name,
            len(path),
            path,
            port,
            protocol_type,
            authentication_type,
            ctypes.byref(password_length),      # Will be filled with pw length
            ctypes.pointer(password_data),      # Will be filled with pw data
            ctypes.pointer(item)
        )

        if rc == -25300:
            raise KeyError('No keychain entry for internet password: server=%s, account=%s' % (server_name, account_name))
        elif rc != 0:
            raise RuntimeError('Unable to retrieve internet password (server=%s, account=%s): rc=%d' % (server_name, account_name, rc))

        password = password_data.value[0:password_length.value]

        Security.lib.SecKeychainItemFreeContent(None, password_data)

        return InternetPassword(server_name=server_name, account_name=account_name, password=password, keychain_item=item, security_domain=security_domain, path=path, port=port, protocol_type=protocol_type, authentication_type=authentication_type)

    def add(self, item):
        """Add the provided GenericPassword or InternetPassword object to this Keychain"""
        assert(isinstance(item, GenericPassword))

        item_ref = ctypes.c_void_p()

        if isinstance(item, InternetPassword):
            rc = Security.lib.SecKeychainAddInternetPassword(
                self.keychain_handle,
                len(item.server_name),
                item.server_name,
                len(item.security_domain),
                item.security_domain,
                len(item.account_name),
                item.account_name,
                len(item.path),
                item.path,
                item.port,
                item.protocol_type,
                item.authentication_type,
                len(item.password),
                item.password,
                ctypes.pointer(item_ref)
            )
        else:
            rc = Security.lib.SecKeychainAddGenericPassword(
                self.keychain_handle,
                len(item.service_name),
                item.service_name,
                len(item.account_name),
                item.account_name,
                len(item.password),
                item.password,
                ctypes.pointer(item_ref)
            )

        if rc != 0:
            raise RuntimeError("Error adding %s: rc=%d" % (item, rc))

        item.keychain_item = item_ref

    def remove(self, item):
        """Remove the provided keychain item as the reverse of Keychain.add()"""
        assert(isinstance(item, GenericPassword))
        item.delete()


class GenericPassword(object):
    """Generic keychain password used with SecKeychainAddGenericPassword and SecKeychainFindGenericPassword"""
    # TODO: Add support for access control and attributes

    account_name  = None
    service_name  = None
    label         = None
    password      = None
    keychain_item = None # An SecKeychainItemRef treated as an opaque object

    def __init__(self, **kwargs):
        super(GenericPassword, self).__init__()
        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise AttributeError("Unknown property %s" % k)
            setattr(self, k, v)

    def update_password(self, new_password):
        """Change the stored password"""

        rc = Security.lib.SecKeychainItemModifyAttributesAndData(
            self.keychain_item,
            None,
            len(new_password),
            new_password
        )

        if rc == -61:
            raise RuntimeError("Permission denied updating %s" % self)
        elif rc != 0:
            raise RuntimeError("Unable to update password for %s: rc = %d" % rc)

    def delete(self):
        """Removes this item from the keychain"""
        rc = Security.lib.SecKeychainItemDelete(self.keychain_item)
        if rc != 0:
            raise RuntimeError("Unable to delete %s: rc=%d" % (self, rc))

        from CoreFoundation import CFRelease
        CFRelease(self.keychain_item)

        self.keychain_item = None
        self.service_name  = None
        self.account_name  = None
        self.password      = None

    def __str__(self):
        return repr(self)

    def __repr__(self):
        props = []
        for k in ['service_name', 'account_name', 'label']:
            props.append("%s=%s" % (k, repr(getattr(self, k))))

        return "%s(%s)" % (self.__class__.__name__, ", ".join(props))


class InternetPassword(GenericPassword):
    """Specialized keychain item for internet passwords used with SecKeychainAddInternetPassword and SecKeychainFindInternetPassword"""
    account_name        = ""
    password            = None
    keychain_item       = None
    server_name         = ""
    security_domain     = ""
    path                = ""
    port                = 0
    protocol_type       = None
    authentication_type = None

    def __init__(self, **kwargs):
        super(InternetPassword, self).__init__(**kwargs)

    def __repr__(self):
        props = []
        for k in ['account_name', 'server_name', 'security_domain', 'path', 'port', 'protocol_type', 'authentication_type']:
            if getattr(self, k):
                props.append("%s=%s" % (k, repr(getattr(self, k))))

        return "%s(%s)" % (self.__class__.__name__, ", ".join(props))

class SecKeychainAttribute(ctypes.Structure):
    """Contains keychain attributes

    tag:    A 4-byte attribute tag.
    length: The length of the buffer pointed to by data.
    data:   A pointer to the attribute data.
    """
    _fields_ = [
        ('tag',     ctypes.c_uint32),
        ('length',  ctypes.c_uint32),
        ('data',    ctypes.c_char_p)
    ]

class SecKeychainAttributeList(ctypes.Structure):
    """Represents a list of keychain attributes

    count:  An unsigned 32-bit integer that represents the number of keychain attributes in the array.
    attr:   A pointer to the first keychain attribute in the array.
    """

    # TODO: Standard iterator support for SecKeychainAttributeList:
    #
    #   for offset in range(0, attrs.count):
    #     print "[%d]: %s: %s" % (offset, attrs.attr[offset].tag, attrs.attr[offset].data[:attrs.attr[offset].length])
    #
    # becomes:
    #
    #   for tag, data in attrs:
    #       …
    #
    #   attrs[tag] should also work
    #

    _fields_ = [
        ('count',   ctypes.c_uint),
        ('attr',    ctypes.POINTER(SecKeychainAttribute))
    ]

class SecKeychainAttributeInfo(ctypes.Structure):
    """Represents a keychain attribute as a pair of tag and format values.

    count:  The number of tag-format pairs in the respective arrays
    tag:    A pointer to the first attribute tag in the array
    format: A pointer to the first CSSM_DB_ATTRIBUTE_FORMAT in the array
    """
    # TODO: SecKeychainAttributeInfo should allow .append(tag, [data])
    _fields_ = [
        ('count',   ctypes.c_uint),
        ('tag',     ctypes.POINTER(ctypes.c_uint)),
        ('format',  ctypes.POINTER(ctypes.c_uint))
    ]

# The APIs expect pointers to SecKeychainAttributeInfo objects:
SecKeychainAttributeInfo_p = ctypes.POINTER(SecKeychainAttributeInfo)
SecKeychainAttributeList_p = ctypes.POINTER(SecKeychainAttributeList)

########NEW FILE########
__FILENAME__ = test_Keychain
#!/usr/bin/env python
# encoding: utf-8

import sys
import unittest
from PyMacAdmin.Security.Keychain import Keychain, GenericPassword, InternetPassword

class KeychainTests(unittest.TestCase):
    """Unit test for the Keychain module"""

    def setUp(self):
        pass

    def test_load_default_keychain(self):
        k = Keychain()
        self.failIfEqual(k, None)

    def test_load_system_keychain(self):
        k = Keychain('/Library/Keychains/System.keychain')
        self.failIfEqual(k, None)

    def test_find_airport_password(self):
        system_keychain = Keychain("/Library/Keychains/System.keychain")
        try:
            system_keychain.find_generic_password(account_name="linksys")
        except KeyError:
            print >> sys.stderr, "test_find_airport_password: assuming the non-existence of linksys SSID is correct"
            pass

    def test_find_nonexistent_generic_password(self):
        import uuid
        system_keychain = Keychain("/Library/Keychains/System.keychain")
        self.assertRaises(KeyError, system_keychain.find_generic_password, **{ 'account_name': "NonExistantGenericPassword-%s" % uuid.uuid4() })

    def test_add_and_remove_generic_password(self):
        import uuid
        k            = Keychain()
        service_name = "PyMacAdmin Keychain Unit Test"
        account_name = str(uuid.uuid4())
        password     = str(uuid.uuid4())

        i            = GenericPassword(service_name=service_name, account_name=account_name, password=password)

        k.add(i)

        self.assertEquals(i.password, k.find_generic_password(service_name, account_name).password)
 
        k.remove(i)
        self.assertRaises(KeyError, k.find_generic_password, **{"service_name": service_name, "account_name": account_name})

    def test_find_internet_password(self):
        keychain = Keychain()
        i = keychain.find_internet_password(server_name="connect.apple.com")
        self.failIfEqual(i, None)

    def test_add_and_remove_internet_password(self):
        import uuid
        k = Keychain()
        kwargs = {
            'server_name':         "pymacadmin.googlecode.com",
            'account_name':        "unittest",
            'protocol_type':       'http',
            'authentication_type': 'http',
            'password':            str(uuid.uuid4())
        }

        i = InternetPassword(**kwargs)
        k.add(i)

        self.assertEquals(i.password, k.find_internet_password(server_name=kwargs['server_name'], account_name=kwargs['account_name']).password)

        k.remove(i)
        self.assertRaises(KeyError, k.find_internet_password, **{"server_name": kwargs['server_name'], "account_name": kwargs['account_name']})


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = dmgtestutilities
#!/usr/bin/python2.5
#
# Use 2.5 so we can import objc & Foundation in tests
#
# Copyright 2008 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This has to run under Apple's python2.5 so it can import Cocoa classes.

"""Helper functions for DMG unit tests."""
__author__ = 'jpb@google.com (Joe Block)'

import subprocess
import Foundation


def RemoveEmpties(a_list):
  """Returns a list with no empty lines."""
  cleaned = []
  for a in a_list:
    if a:
      cleaned.append(a)
  return cleaned


def ProcessCommand(command, strip_empty_lines=True):
  """Return a dict containing command's stdout, stderr & error code.

  Args:
    command: list containing the command line we want run
    strip_empty_lines: Boolean to tell us to strip empty lines or not.

  Returns:
    dict with stdout, stderr and error code from the command run.
  """
  cmd = subprocess.Popen(command, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
  (stdout, stderr) = cmd.communicate()
  info = {}
  info['errorcode'] = cmd.returncode
  if not strip_empty_lines:
    info['stdout'] = stdout.split('\n')
    info['stderr'] = stderr.split('\n')
  else:
    info['stdout'] = RemoveEmpties(stdout.split('\n'))
    info['stderr'] = RemoveEmpties(stderr.split('\n'))
  return info


def LintPlist(path):
  """plutil -lint path.

  Args:
    path: file to lint

  Returns:
    errorcode of plutil -lint
  """
  cmd = ProcessCommand(['/usr/bin/plutil', '-lint', path])
  return cmd['errorcode']


def ReadPlist(plistfile):
  """Read a plist, return a dict.

  Args:
    plistfile: Path to plist file to read

  Returns:
    dict of plist contents.
  """
  return Foundation.NSDictionary.dictionaryWithContentsOfFile_(plistfile)


if __name__ == '__main__':
  print 'This is not a standalone script. It contains only helper functions.'

########NEW FILE########
__FILENAME__ = macdmgtest
#!/usr/bin/python2.5
#
# Use 2.5 so we can import objc & Foundation in tests
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Base class for dmg unit tests."""
__author__ = 'jpb@google.com (Joe Block)'

import os
import unittest


def main():
  """Print usage warning."""
  print 'This is not a standalone test suite. Run with run_image_tests.py.'


class DMGUnitTest(unittest.TestCase):
  """Helper functions for DMG unit tests."""

  def SetMountpoint(self, mountpoint):
    """Set mountpoint."""
    self.mountpoint = mountpoint

  def SetOptions(self, options):
    """Set options parsed from command line.

    Args:
      options: command line options passed in by image testing driver script.
    """
    self.options = options

  def Mountpoint(self):
    """Return mountpoint of dmg being tested."""
    return self.mountpoint

  def ConfigPath(self, configfile):
    """Returns path to a config file with configdir prepended.
    Args:
      path: relative path of config file
    Returns:
      Actual path to that file, based on configdir"""
    return os.path.join(self.options.configdir, configfile)

  def PathOnDMG(self, path):
    """Returns path with dmg mount path prepended.

    Args:
      path: path to a file on the dmg
    """
    # deal with leading /es in path var.
    while path[:1] == '/':
      path = path[1:]
    return os.path.join(self.mountpoint, path)

  def CheckForExistence(self, filename):
    """Make sure filename doesn't exist on the tested image.

    Args:
      filename: file to look for on the dmg
    """
    if filename:
      path = self.PathOnDMG(filename)
      return os.path.exists(path)
    else:
      return False


if __name__ == '__main__':
  Main()

########NEW FILE########
__FILENAME__ = run_image_tests
#!/usr/bin/python2.5
#
# Use 2.5 so we can import objc & Foundation in tests
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Parent script for unit testing a Mac OS X image candidate.

This script expects to be passed the path to a dmg that is a Mac OS X
image candidate. It mounts the image, imports the modules in the tests dir,
builds up a test suite of their test functions and runs them on the image.

Each test has "self.mountpoint" set that is the mountpoint of the dmg

Unit tests in the test directory must be subclasses of macdmgtest.DMGUnitTest.

Naming formats must be as follows:
  Files:    *_test.py
  Classes:  Test*
  Tests:    test*

Author: Nigel Kersten (nigelk@google.com)
Modified by: Joe Block (jpb@google.com)
"""

import optparse
import os
import re
import subprocess
import sys
import types
import unittest
import plistlib


def AttachDiskImage(path):
  """attaches a dmg, returns mountpoint, assuming only one filesystem."""

  command = ["/usr/bin/hdiutil", "attach", path, "-mountrandom", "/tmp",
             "-readonly", "-nobrowse", "-noautoopen", "-plist",
             "-owners", "on"]
  task = subprocess.Popen(command,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
  (stdout, stderr) = task.communicate()
  if task.returncode:
    print "There was an error attaching dmg: %s" % path
    print stderr
    return False
  else:
    mountpoint = False
    dmg_plist = plistlib.readPlistFromString(stdout)
    entities = dmg_plist["system-entities"]
    for entity in entities:
      if "mount-point" in entity:
        mountpoint = entity["mount-point"]
    return mountpoint


def DetachDiskImage(path):
  """forcibly unmounts a given dmg from the mountpoint path."""

  command = ["/usr/bin/hdiutil", "detach", path]
  returncode = subprocess.call(command)
  if returncode:
    command = ["/usr/bin/hdiutil", "detach", "-force", path]
    returncode = subprocess.call(command)
    if returncode:
      raise StandardError("Unable to unmount dmg mounted at: %s" % path)
  return True


def TestClasses(module):
  """returns test classes in a module."""
  classes = []
  pattern = re.compile("^Test\w+$")  # only classes starting with "Test"
  for name in dir(module):
    obj = getattr(module, name)
    if type(obj) in (types.ClassType, types.TypeType):
      if pattern.match(name):
        classes.append(name)
  return classes


def GetTestSuite(path, mountpoint, options):
  """Given path to module, returns suite of test methods."""
  dirname = os.path.dirname(path)
  filename = os.path.basename(path)

  if not dirname in sys.path:
    sys.path.append(dirname)

  modulename = re.sub("\.py$", "", filename)
  module = __import__(modulename)
  for classname in TestClasses(module):
    test_loader = unittest.TestLoader()
    test_suite = test_loader.loadTestsFromName(classname, module)
    # there must be a better way than this protected member access...
    for test in test_suite._tests:
      test.SetMountpoint(mountpoint)
      test.SetOptions(options)
    return test_suite


def ListTests(path):
  """lists tests in directory "path" ending in _test.py."""

  pattern = re.compile("^\w*_test.py$", re.IGNORECASE)
  tests = []
  for test in os.listdir(path):
    if pattern.match(test):
      tests.append(test)
  tests.sort()
  return tests


def SummarizeResults(result):
  """Print a summary of a test result."""
  print
  print "Results"
  print "==============="

  print "total tests run: %s" % result.testsRun
  print "   errors found: %s" % len(result.errors)
  print " failures found: %s" % len(result.failures)
  print


def ParseCLIArgs():
  """Parse command line arguments and set options accordingly."""
  cli = optparse.OptionParser()
  cli.add_option("-c", "--configdir", dest="configdir", default=".",
                 type="string", help="specify directory for test config files")
  cli.add_option("-d", "--dmg", dest="dmg", type="string",
                 help="specify path to dmg to test.")
  cli.add_option("-p", "--pkgdir", dest="pkgdir", type="string",
                 help="specify directory to look for packages in.")
  cli.add_option("-r", "--root", dest="root", type="string",
                 help="specify path to root of a directory tree to test.")
  cli.add_option("-t", "--testdir", dest="testdir", default="tests",
                 type="string", help="specify directory with tests")
  cli.add_option("-v", "--verbosity", type="int", dest="verbosity",
                 help="specify verbosity level", default=0)
  (options, args) = cli.parse_args()
  return (options, args)


def main():
  """entry point."""
  (options, unused_args) = ParseCLIArgs()
  dmg = options.dmg
  verbosity = options.verbosity
  tests_dir = options.testdir
  config_dir = options.configdir
  root = options.root
  if not dmg and not root:
    print "Use --dmg to specify a dmg file or --root to specify a directory."
    sys.exit(1)
  if dmg:
    print "Mounting disk image... (this may take some time)"
    mountpoint = AttachDiskImage(dmg)
    if not mountpoint:
      print "Unable to mount %s" % dmg
      sys.exit(2)
  elif root:
    if not os.path.isdir(root):
      print "%s not a directory" % root
      sys.exit(2)
    mountpoint = root
    print "Checking %s" % mountpoint
  print

  dirname = os.path.dirname(sys.argv[0])
  os.chdir(dirname)
  tests = ListTests(tests_dir)
  test_results = {}
  combo_suite = unittest.TestSuite()
  for test in tests:
    test_path = os.path.join(tests_dir, test)
    combo_suite.addTests(GetTestSuite(test_path, mountpoint, options))

  test_results = unittest.TextTestRunner(verbosity=verbosity).run(combo_suite)

  if dmg:
    DetachDiskImage(mountpoint)

  if test_results.wasSuccessful():
    sys.exit(0)
  else:
    SummarizeResults(test_results)
    bad = len(test_results.errors) + len(test_results.failures)
    sys.exit(bad)


if __name__ == "__main__":
  main()

########NEW FILE########
__FILENAME__ = applications_dir_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Check user/group/permissions in /Applications & /Applications/Utilities.

Author: Joe Block (jpb@google.com)
"""

import logging
import os
import pprint
import stat
import macdmgtest


class TestAppDirectories(macdmgtest.DMGUnitTest):

  def setUp(self):
    """Set up exceptions to standard permissions requirements."""
    self.errors_found = []
    self.standard_stat = {'uid': 0, 'gid': 80, 'mode': '0775'}
    self.application_exceptions = {}
    self.application_exceptions['System Preferences'] = {}
    self.application_exceptions['System Preferences']['gid'] = 0
    self.application_exceptions['System Preferences']['mode'] = '0775'
    self.application_exceptions['System Preferences']['uid'] = 0
    self.utilities_exceptions = {}
    # Here are a couple of examples of making exceptions for stuff we
    # symlink into Applications or Applications/Utilities
    self.utilities_exceptions['Kerberos'] = {}
    self.utilities_exceptions['Kerberos']['gid'] = 0
    self.utilities_exceptions['Kerberos']['mode'] = '0755'
    self.utilities_exceptions['Kerberos']['symlink_ok'] = True
    self.utilities_exceptions['Kerberos']['uid'] = 0
    self.utilities_exceptions['Screen Sharing'] = {}
    self.utilities_exceptions['Screen Sharing']['gid'] = 0
    self.utilities_exceptions['Screen Sharing']['mode'] = '0755'
    self.utilities_exceptions['Screen Sharing']['symlink_ok'] = True
    self.utilities_exceptions['Screen Sharing']['uid'] = 0

  def _SanityCheckApp(self, statmatrix, overrides, thedir, name):
    """Check a .app directory and ensure it has sane perms and ownership."""
    o = os.path.splitext(name)[0]
    if o in overrides:
      g_uid = overrides[o]['uid']
      g_gid = overrides[o]['gid']
      g_mode = overrides[o]['mode']
    else:
      g_uid = statmatrix['uid']
      g_gid = statmatrix['gid']
      g_mode = statmatrix['mode']
    path = os.path.join(self.mountpoint, thedir, name)
    check_stats = os.stat(path)
    a_mode = oct(check_stats[stat.ST_MODE] & 0777)
    a_gid = check_stats[stat.ST_GID]
    a_uid = check_stats[stat.ST_UID]
    if os.path.islink(path):
      if o in overrides:
        if 'symlink_ok' in overrides[o]:
          if not overrides[o]['symlink_ok']:
            msg = '%s/%s is a symlink and should not be.' % (thedir, name)
            self.errors_found.append(msg)
            logging.debug(msg)
      else:
        msg = '%s/%s is a symlink, not an application.' % (thedir, name)
        self.errors_found.append(msg)
        logging.debug(msg)
    if a_uid != g_uid:
      msg = '%s/%s is owned by %s, should be owned by %s' % (thedir, name,
                                                             a_uid, g_uid)
      self.errors_found.append(msg)
      logging.debug(msg)
    if a_gid != g_gid:
      msg = '%s/%s is group %s, should be group %s' % (thedir, name, a_gid,
                                                       g_gid)
      self.errors_found.append(msg)
      logging.debug(msg)
    if a_mode != g_mode:
      msg = '%s/%s was mode %s, should be %s' % (thedir, name, a_mode, g_mode)
      self.errors_found.append(msg)
      logging.debug(msg)

  def testApplicationDirectory(self):
    """Sanity check all applications in /Applications."""
    self.errors_found = []
    appdir = 'Applications'
    for application in os.listdir(os.path.join(self.mountpoint, appdir)):
      if os.path.splitext(application)[1] == '.app':
        self._SanityCheckApp(self.standard_stat, self.application_exceptions,
                             appdir, application)
    if self.errors_found:
      print
      pprint.pprint(self.errors_found)
    self.assertEqual(len(self.errors_found), 0)

  def testUtilitiesDirectory(self):
    """Sanity check applications in /Applications/Utilities."""
    self.errors_found = []
    appdir = 'Applications/Utilities'
    for application in os.listdir(os.path.join(self.mountpoint, appdir)):
      if application[-3:] == 'app':
        self._SanityCheckApp(self.standard_stat, self.utilities_exceptions,
                             appdir, application)
    if self.errors_found:
      print
      pprint.pprint(self.errors_found)
    self.assertEqual(len(self.errors_found), 0)


if __name__ == '__main__':
  macdmgtest.main()

########NEW FILE########
__FILENAME__ = blacklist_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Make sure blacklisted files or directories are not present on the image."""

__author__ = 'jpb@google.com (Joe Block)'

import macdmgtest
import dmgtestutilities


def ReadBlackList(path):
  """Read a blacklist of forbidden directories and files.

  Ignore lines starting with a # so we can comment the datafile.

  Args:
    path: file to load the blacklist from.
  Returns:
    dictionary of path:True mappings
  """
  blacklist_file = open(path, 'r')
  catalog = []
  for entry in blacklist_file:
    if not entry or entry[:1] == '#':
      pass   # ignore comment and empty lines in blacklist file
    else:
      catalog.append(entry.strip())
  return catalog


class TestBlacklists(macdmgtest.DMGUnitTest):

  def setUp(self):
    blacklist_path = self.ConfigPath('file_and_directory.blacklist')
    self.blacklist = ReadBlackList(blacklist_path)

  def ProcessList(self, the_list):
    """files/directories from the_list should be absent from the image.

    Args:
      the_list: A list of paths to file or directories that should be absent
          from the image.
    Returns:
      list of directories/files that are present that shouldn't be.
    """
    bad = []
    for d in the_list:
      if self.CheckForExistence(d) == True:
        bad.append(d)
    return bad

  def testBlacklistedDirectories(self):
    """Ensure directories from blacklist are absent from the image."""
    badfound = self.ProcessList(self.blacklist)
    if badfound:
      print 'These files and directories should not exist:'
      print '%s' % badfound
    self.assertEqual(len(badfound), 0)


if __name__ == '__main__':
  macdmgtest.main()

########NEW FILE########
__FILENAME__ = empty_directory_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Ensure directories that are supposed to be empty actually are."""

__author__ = 'jpb@google.com (Joe Block)'


import os
import macdmgtest


class TestEmptyDirectories(macdmgtest.DMGUnitTest):

  def setUp(self):
    self.empty_directories = ['var/vm',
                              '/private/tmp',
                              'Volumes',
                              'Library/Logs']

  def DirectoryEmpty(self, dirname):
    """Make sure dirname is empty."""
    path = self.PathOnDMG(dirname)
    if os.listdir(path):
      return False
    else:
      return True

  def testEmptyDirectories(self):
    """Ensure every directory that is supposed to be empty on the image, is."""
    full_dirs = []
    for d in self.empty_directories:
      if not self.DirectoryEmpty(d):
        full_dirs.append(d)
    self.assertEqual(len(full_dirs), 0)

if __name__ == '__main__':
  macdmgtest.main()

########NEW FILE########
__FILENAME__ = example_plist_test
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Example test showing how to check values inside a plist.

This example tests the existence of certain fields within:
/Library/Preferences/com.foo.corp.imageinfo.plist

This plist identifies the date at which an image was created, so this series
of tests simply checks whether the plist exists, whether it is a proper file
as opposed to a symlink, whether the imageVersion field exists, whether it can
be made into a valid date, and whether the date is a sane value.

As with this whole framework, the attribute self.mountpoint refers to the
location at which the image to be tested is mounted.

Note that we're copying the plist to a temporary location and converting it
to xml1 format rather than binary. We do this so that plistlib works
(it doesn't work on binary plists) and so that we're not actually trying to
modify the image, which is mounted in read-only mode.

Original Author: Nigel Kersten (nigelk@google.com)
"""

import datetime
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
import plistlib


# don"t use absolute paths with os.path.join
imageinfo_plist = "Library/Preferences/com.foo.corp.imageinfo.plist"


class TestMachineInfo(unittest.TestCase):

  def setUp(self):
    """copy the original file to a temp plist and convert it to xml1."""
    self.tempdir = tempfile.mkdtemp()
    self.orig_imageinfo_file = os.path.join(self.mountpoint, imageinfo_plist)
    imageinfo_file = os.path.join(self.tempdir, "imageinfo.plist")
    shutil.copyfile(self.orig_imageinfo_file, imageinfo_file)
    command = ["plutil", "-convert", "xml1", imageinfo_file]
    returncode = subprocess.call(command)
    if returncode:
      raise StandardError("unable to convert plist to xml1")
    self.imageinfo = plistlib.readPlist(imageinfo_file)

  def tearDown(self):
    """clean up the temporary location."""
    if self.tempdir:
      if os.path.isdir(self.tempdir):
        shutil.rmtree(self.tempdir)

  def testFile(self):
    """test the original file is a proper file."""
    self.assert_(os.path.isfile(self.orig_imageinfo_file))

  def testOwnerGroupMode(self):
    """test owner, group and mode of original file."""
    orig_imageinfo_stat = os.stat(self.orig_imageinfo_file)
    owner = orig_imageinfo_stat[stat.ST_UID]
    group = orig_imageinfo_stat[stat.ST_GID]
    mode = orig_imageinfo_stat[stat.ST_MODE]
    num_mode = oct(mode & 0777)
    self.assertEqual(0, owner)
    self.assertEqual(80, group)
    self.assertEqual('0644', num_mode)

  def testImageVersionPresent(self):
    """test that the ImageVersion field is present."""
    self.failUnless("ImageVersion" in self.imageinfo)

  def testImageVersionFormat(self):
    """test that the ImageVersion field is well formed."""
    pattern = re.compile("^\d{8}$")
    self.failUnless(pattern.match(self.imageinfo["ImageVersion"]))

  def testImageVersionValueIsDate(self):
    """test that the ImageVersion value is actually a date"""
    image_version = self.imageinfo["ImageVersion"]
    year = int(image_version[:4])
    month = int(image_version[4:-2])
    day = int(image_version[6:])
    now = datetime.datetime.now()
    self.failUnless(now.replace(year=year,month=month,day=day))

  def testImageVersionValueIsCurrentDate(self):
    """test that the ImageVersion value is a current date."""
    image_version = self.imageinfo["ImageVersion"]
    year = int(image_version[:4])
    year_range = range(2006, 2100)
    self.failUnless(year in year_range)



if __name__ == "__main__":
  unittest.main()

########NEW FILE########
__FILENAME__ = network_plist_test
#!/usr/bin/python2.5
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Network settings tests to cope with Airbook brain damage."""
__author__ = 'jpb@google.com (Joe Block)'

import dmgtestutilities
import macdmgtest


class TestNetworkAirbookCompliant(macdmgtest.DMGUnitTest):
  """Check that network settings suitably munged for Airbooks."""

  def setUp(self):
    """Setup paths."""
    self.system_pref_path = self.PathOnDMG(
      '/Library/Preferences/SystemConfiguration/preferences.plist')
    self.sys_prefs = dmgtestutilities.ReadPlist(self.system_pref_path)
    if not self.sys_prefs:
      self.sys_prefs = {}

  def testNetworkPlistIsAbsent(self):
    """Ensure NetworkInterfaces.plist absent, it will be rebuilt for Airbook."""
    nw = '/Library/Preferences/SystemConfiguration/NetworkInterfaces.plist'
    self.assertEqual(self.CheckForExistence(nw), False)

  def testSystemPreferencesPlistIsAbsent(self):
    """SystemConfiguration/preferences absent? will be rebuilt for Airbook."""
    self.assertEqual(self.CheckForExistence(self.system_pref_path), False)

  def testEnsureNoCurrentSet(self):
    """SystemConfiguration/preferences.plist must not have CurrentSet key."""
    self.assertEqual('CurrentSet' in self.sys_prefs, False)

  def testEnsureNoNetworkServices(self):
    """SystemConfiguration/preferences.plist can't have NetworkServices key."""
    self.assertEqual('NetworkServices' in self.sys_prefs, False)

  def testEnsureNoSets(self):
    """SystemConfiguration/preferences.plist must not have Sets key."""
    self.assertEqual('Sets' in self.sys_prefs, False)


if __name__ == '__main__':
  macdmgtest.main()

########NEW FILE########
__FILENAME__ = ouradmin_test
#!/usr/bin/python2.5
#
# Copyright 2008-2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Change ouradmin to whatever local admin account you're adding to your image.
#
# We also sanity check that the group plists pass lint to ensure our localadmin
# creation package didn't somehow break them.

"""Make sure there's an ouradmin local account on the machine."""
__author__ = 'jpb@google.com (Joe Block)'

import os
import stat
import dmgtestutilities
import macdmgtest


class TestCheckForouradmin(macdmgtest.DMGUnitTest):
  """Make sure there's an ouradmin local account on the machine."""

  def setUp(self):
    """Setup paths."""
    self.localnode = 'var/db/dslocal/nodes/Default'
    self.admin_plist = self.PathOnDMG('%s/groups/admin.plist' % self.localnode)
    self.ouradmin_plist = self.PathOnDMG('%s/users/ouradmin.plist' %
                                         self.localnode)
    self.ouradmin_stat = os.stat(self.ouradmin_plist)
    self.lpadmin_plist = self.PathOnDMG('%s/groups/_lpadmin.plist' %
                                        self.localnode)
    self.appserveradm_plist = self.PathOnDMG('%s/groups/_appserveradm.plist' %
                                             self.localnode)

  def testOuradminIsMemberOfLPadminGroup(self):
    """Check that ouradmin user is in _lpadmin group."""
    pf = dmgtestutilities.ReadPlist(self.lpadmin_plist)
    self.assertEqual('ouradmin' in pf['users'], True)

  def testOuradminIsMemberOfAppserverAdminGroup(self):
    """Check that ouradmin user is in _appserveradm group."""
    pf = dmgtestutilities.ReadPlist(self.appserveradm_plist)
    self.assertEqual('ouradmin' in pf['users'], True)

  def testOuradminIsMemberOfAdminGroup(self):
    """Check that ouradmin user is in admin group."""
    pf = dmgtestutilities.ReadPlist(self.admin_plist)
    self.assertEqual('ouradmin' in pf['users'], True)

  def testOuradminIsInDSLocal(self):
    """Check for ouradmin user in local ds node."""
    plistpath = self.PathOnDMG('%s/users/ouradmin.plist' % self.localnode)
    self.assertEqual(os.path.exists(plistpath), True)

  def testOuradminPlistMode(self):
    """ouradmin.plist is supposed to be mode 600."""
    mode = self.ouradmin_stat[stat.ST_MODE]
    num_mode = oct(mode & 0777)
    self.assertEqual('0600', num_mode)

  def testOuradminPlistCheckGroup(self):
    """ouradmin.plist should be group wheel."""
    group = self.ouradmin_stat[stat.ST_GID]
    self.assertEqual(0, group)

  def testOuradminPlistCheckOwnership(self):
    """ouradmin.plist should be owned by root."""
    owner = self.ouradmin_stat[stat.ST_UID]
    self.assertEqual(0, owner)

  # lint every plist the localadmin creation package had to touch.

  def testPlistLintAdminGroup(self):
    """Make sure admin.plist passes lint."""
    cmd = dmgtestutilities.LintPlist(self.admin_plist)
    self.assertEqual(cmd, 0)

  def testPlistLintAppserverAdminGroup(self):
    """Make sure _appserveradm.plist passes lint."""
    cmd = dmgtestutilities.LintPlist(self.appserveradm_plist)
    self.assertEqual(cmd, 0)

  def testPlistLintLPAdminGroup(self):
    """Make sure _lpadmin.plist passes lint."""
    cmd = dmgtestutilities.LintPlist(self.lpadmin_plist)
    self.assertEqual(cmd, 0)

  def testOuradminPlistLint(self):
    """Make sure ouradmin.plist passes lint."""
    cmd = dmgtestutilities.LintPlist(self.ouradmin_plist)
    self.assertEqual(cmd, 0)


if __name__ == '__main__':
  macdmgtest.main()

########NEW FILE########
__FILENAME__ = size_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Check size of dmg for sanity.

When I was starting to use InstaDMG/InstaUp2Date, bad configurations tended
to generate ridiculously sized dmg files, so confirm the dmg is in the window
we expected.

Yes, this will need updating if we add a significant amount of new items
to the dmg, but it catches the cases when the Instadmg run failed
spectacularly and creates an absurd output dmg.
"""
__author__ = "jpb@google.com (Joe Block)"

import os
import macdmgtest


TOO_BIG = 6000000000
TOO_SMALL = 5000000000


class TestDMGSize(macdmgtest.DMGUnitTest):

  def setUp(self):
    self.dmgpath = self.options.dmg

  def testDMGTooSmall(self):
    """Sanity check on dmg size: the dmg should be at least 5G."""
    if not self.dmgpath:
      print "..skipping DMGTooSmall check - not testing a dmg"
    else:
      dmg_size = os.path.getsize(self.dmgpath)
      self.failUnless(dmg_size > TOO_SMALL)

  def testDMGTooBig(self):
    """Sanity check on dmg size: the dmg should be no more than 6G."""
    if not self.dmgpath:
      print "..skipping DMGTooBig check - not testing a dmg"
    else:
      dmg_size = os.path.getsize(self.dmgpath)
      self.failUnless(dmg_size < TOO_BIG)


if __name__ == "__main__":
  macdmgtest.main()

########NEW FILE########
__FILENAME__ = software_update_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Ensure correct software update catalog url is set on image.

Author: Joe Block (jpb@google.com)
"""

import os
import stat
import dmgtestutilities
import macdmgtest


class TestSoftwareUpdateURL(macdmgtest.DMGUnitTest):
  """Check validity of Software Update preferences on image."""

  def setUp(self):
    """Setup paths and load plist data."""
    self.su_pref_path = self.PathOnDMG(
        "/Library/Preferences/com.apple.SoftwareUpdate.plist")
    self.su_prefs = dmgtestutilities.ReadPlist(self.su_pref_path)
    if not self.su_prefs:
      self.su_prefs = {}

  def testSoftwareUpdatePlist(self):
    """Ensure com.apple.SoftwareUpdate.plist is installed on the image."""
    self.assertEqual(self.CheckForExistence(
        "/Library/Preferences/com.apple.SoftwareUpdate.plist"), True)

  def testOwnerGroupMode(self):
    """test owner, group and mode of com.apple.SoftwareUpdate.plist."""
    software_update_stat = os.stat(self.su_pref_path)
    owner = software_update_stat[stat.ST_UID]
    group = software_update_stat[stat.ST_GID]
    mode = software_update_stat[stat.ST_MODE]
    num_mode = oct(mode & 0777)
    self.assertEqual(0, owner)
    self.assertEqual(80, group)
    self.assertEqual("0644", num_mode)

  def testSoftwareUpdateCatalogURL(self):
    """test that Software Update is set to use internal CatalogURL."""
    self.assertEqual("http://path/to/your/internal/swupd/",
                     self.su_prefs["CatalogURL"])

if __name__ == "__main__":
  macdmgtest.main()


########NEW FILE########
__FILENAME__ = symlink_checker_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# tests are done in alphabetical order by file name, so since this
# traverses the entire dmg, using zz to push it to the end with the
# other slow unit tests.

"""Check that all symlinks in /Library don't have brain damaged targets."""
__author__ = 'jpb@google.com (Joe Block)'


import dmgtestutilities
import macdmgtest


class TestSymlinks(macdmgtest.DMGUnitTest):
  """Test dmg to ensure no symlinks point to other drives."""

  def testForSymlinksToOtherVolumes(self):
    """SLOW:Search for symbolic links pointing to other drives."""
    cmd = ['/usr/bin/find', self.Mountpoint(), '-type', 'l', '-exec',
           'readlink', '{}', ';']
    res = dmgtestutilities.ProcessCommand(cmd)
    hall_of_shame = []
    for f in res['stdout']:
      # we can't check just the beginning of the filename because of Apple's
      # penchant for destinations that are ../../../../Volumes/Foo/something
      if f.count('/Volumes/'):
        hall_of_shame.append(f)
    if hall_of_shame:
      print 'Bad symlinks found:'
      for h in hall_of_shame:
        print h
    self.assertEqual(0, len(hall_of_shame))


if __name__ == '__main__':
  macdmgtest.main()

########NEW FILE########
__FILENAME__ = zz_plint_test
#!/usr/bin/python2.4
#
# Copyright 2008-2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Check that all .plist files on the dmg pass plutil lint."""
__author__ = 'jpb@google.com (Joe Block)'


import os
import dmgtestutilities
import macdmgtest


class TestLintPlistsOnDMG(macdmgtest.DMGUnitTest):
  """Checks all plist files on the dmg with plutil -lint.

  This is by far the slowest test we run, so force it to run last by starting
  the filename with zz. This way we don't have to wait for it to finish when
  we're testing other unit tests.
  """

  def setUp(self):
    """Setup Error statistics."""
    self.lint_output = []
    self.bad_plists = []

  def _CheckPlistFiles(self, unused_a, path, namelist):
    """Run plutil -lint on all the plist files in namelist."""
    for name in namelist:
      if os.path.splitext(name)[1] == '.plist':
        plistfile = os.path.join(path, name)
        cmd = dmgtestutilities.ProcessCommand(['/usr/bin/plutil', '-lint',
                                               plistfile])
        if cmd['errorcode']:
          self.bad_plists.append(plistfile)
          self.lint_output.append('Error found in %s' % plistfile)
          for x in cmd['stdout']:
            self.lint_output.append(x)

  def testPlistsOnDMG(self):
    """SLOW: Check all plists on dmg with plutil -lint. Can take 5 minutes."""
    dirname = self.PathOnDMG('')
    os.path.walk(dirname, self._CheckPlistFiles, None)
    # Print out the bad list. Normally it would be better practice to just
    # let the assert fail, but we want to know exactly what plists are bad on
    # the image so we can fix them.
    if self.bad_plists:
      print
      print 'Found %s bad plist files.' % len(self.bad_plists)
      print '\n\t'.join(self.bad_plists)
      print '\nErrors detected:'
      print '\n'.join(self.lint_output)
    self.assertEqual(len(self.lint_output), 0)
    self.assertEqual(len(self.bad_plists), 0)

if __name__ == '__main__':
  macdmgtest.main()

########NEW FILE########
__FILENAME__ = zz_suidguid_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# tests are done in alphabetical order by file name, so since this
# traverses the entire dmg, using zz to push it to the end with the
# other slow unit tests.

"""Check that all setuid & setgid files on the dmg are in our whitelist."""
__author__ = 'jpb@google.com (Joe Block)'


import logging
import dmgtestutilities
import macdmgtest


def ListSuidSgid(path):
  """Finds all the suid/sgid files under path.

  Args:
    path: root of directory tree to examine.
  Returns:
    dictionary of Suid/Sgid files.
  """

  cmd = ['/usr/bin/find', path, '-type', 'f', '(', '-perm', '-004000', '-o',
         '-perm', '-002000', ')', '-exec', 'ls', '-l', '{}', ';']
  res = dmgtestutilities.ProcessCommand(cmd)
  catalog = []
  prefix_length = len(path)
  for f in res['stdout']:
    if f:
      snip = f.find('/')
      if snip:
        snip_index = snip + prefix_length
        rawpath = f[snip_index:]
        catalog.append(rawpath)
      else:
        logging.warn('snip: %s' % snip)
        logging.warn(f)
  return catalog


def ReadWhiteList(path):
  """Read a whitelist of setuid/setgid files.

  Ignore lines starting with a # so we can comment the whitelist.

  Args:
    path: file to load the whitelist from.
  Returns:
    dictionary of path:True mappings
  """
  white_file = open(path, 'r')
  catalog = {}
  for entry in white_file:
    if not entry or entry[:1] == '#':
      pass   # ignore comment and empty lines in whitelist file
    else:
      catalog[entry.strip()] = True
  return catalog


class TestSUIDGUIDFiles(macdmgtest.DMGUnitTest):

  def setUp(self):
    whitelist_path = self.ConfigPath('suidguid.whitelist')
    self.whitelisted_suids = ReadWhiteList(whitelist_path)

  def testForUnknownSUIDsAndGUIDs(self):
    """SLOW: Search for non-whitelisted suid/guid files on dmg."""
    scrutinize = ListSuidSgid(self.Mountpoint())
    illegal_suids = []
    for s in scrutinize:
      if s not in self.whitelisted_suids:
        illegal_suids.append(s)
    if illegal_suids:
      # make it easier to update the whitelist when a new Apple update adds
      # a suid/sgid file
      print '\n\n# suid/sgid files suitable for pasting into whitelist.'
      '\n'.join(illegal_suids)
      print '# end paste\n\n'
    self.assertEqual(0, len(illegal_suids))


if __name__ == '__main__':
  macdmgtest.main()

########NEW FILE########
__FILENAME__ = zz_world_writable_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Tests are done in alphabetical order by file name, so since this
# traverses the entire dmg, using zz to push it to the end with the
# other slow unit tests.

"""Confirm all world-writable files and dirs on the dmg are in our whitelist."""
__author__ = 'jpb@google.com (Joe Block)'


import logging
import dmgtestutilities
import macdmgtest


def CatalogWritables(path):
  """Finds all the files and directories that are world-writeable.

  Args:
    path: root of directory tree to examine.
  Returns:
    dictionary of paths to world-writeable files & directories under root,
    with the base path to the root peeled off.
  """

  dir_cmd = ['/usr/bin/find', path, '-type', 'd', '-perm', '+o=w', '-exec',
             'ls', '-ld', '{}', ';']
  file_cmd = ['/usr/bin/find', path, '-type', 'f', '-perm', '+o=w', '-exec',
              'ls', '-l', '{}', ';']
  logging.debug('Searching dmg for world writable files')
  files = dmgtestutilities.ProcessCommand(file_cmd)
  logging.debug('Searching dmg for world writable directories')
  dirs = dmgtestutilities.ProcessCommand(dir_cmd)
  state_of_sin = dirs['stdout'] + files['stdout']

  writeables = []
  prefix_length = len(path)
  for s in state_of_sin:
    if s:
      snip = s.find('/')
      if snip:
        snip_index = snip + prefix_length
        rawpath = s[snip_index:]
        writeables.append(rawpath)
      else:
        logging.warn('snip: %s' % snip)
        logging.warn(s)
  return writeables


def ReadWhiteList(path):
  """Read a whitelist of world writable files and directories into a dict.

  Ignore lines starting with a # so we can comment the whitelist.

  Args:
    path: file to load the whitelist from.
  Returns:
    dictionary of path:True mappings
  """
  white_file = open(path, 'r')
  catalog = {}
  for entry in white_file:
    if not entry or entry[:1] == '#':
      pass   # ignore comment and empty lines
    else:
      catalog[entry.strip()] = True
  return catalog


class TestWritableDirectoriesAndFiles(macdmgtest.DMGUnitTest):

  def setUp(self):
    whitelist_path = self.ConfigPath('writables.whitelist')
    self.whitelisted_writables = ReadWhiteList(whitelist_path)

  def testForWorldWritableFilesOrDirectories(self):
    """SLOW: Search for non-whitelisted world-writable files and directories."""
    scrutinize = CatalogWritables(self.Mountpoint())
    sinners = []
    for s in scrutinize:
      if s not in self.whitelisted_writables:
        sinners.append(s)
    if sinners:
      print '\n\n# world-writable files & dirs for pasting into whitelist.'
      print '\n'.join(sinners)
      print '# end paste\n\n'
    self.assertEqual(0, len(sinners))


if __name__ == '__main__':
  macdmgtest.main()

########NEW FILE########
__FILENAME__ = wtfUpdate
#!/usr/bin/env python
# encoding: utf-8
"""
Generate HTML documentation from an Apple .pkg update

Given a .pkg file this program will generate a list of the installed files,
installer scripts.

Contributed by Chris Barker (chrisb@sneezingdog.com):

    <http://sneezingdog.com/wtfupdate/wtfUpdate.py>
    <http://angrydome.org/?p=18>
"""

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import os
import sys
import shutil
import tempfile
import hashlib
from BeautifulSoup import BeautifulSoup, Tag, NavigableString
from os.path import basename, splitext, exists, join, isfile, isdir

# This will contain a BeautifulSoup object so we can avoid passing it around
# to every function:
SOUP = None

def expand_pkg(pkg_file):
    """ Expand the provided .pkg file and return the temp directory path """

    # n.b. This is a potential security issue but there's not really a good
    # way to avoid it because pkgutil can't handle an existing directory:
    dest = tempfile.mktemp()
    subprocess.check_call(["/usr/sbin/pkgutil", "--expand", pkg_file, dest])
    return dest


def get_description(pkg):
    """Return the HTML description """

    su_desc = pkg + '/Resources/English.lproj/SUDescription.html'

    if not exists(su_desc):
        return "<i>no description</i>"

    soup = BeautifulSoup(open(su_desc).read())
    return soup.body.contents


def load_scripts(pkg):
    """
    Given a package expand ul#scripts to include the contents of any scripts
    """

    script_ul = SOUP.find("ul", {"id": "scripts"})
    script_ul.contents = []

    for f in os.listdir(pkg):
        if splitext(f)[1] != '.pkg':
            continue

        script_dir  = join(pkg, f, 'Scripts')
        script_list = Tag(SOUP, 'ul')

        for script in os.listdir(script_dir):
            if script == "Tools":
                continue

            script_li          = Tag(SOUP, 'li')
            script_li['class'] = 'code'
            script_path        = join(script_dir, script)

            if isfile(script_path):
                script_li.append(join(f, 'Scripts', script))
                script_li.append(anchor_for_name(script_path))
                script_pre = Tag(SOUP, 'pre')
                script_pre.append(NavigableString(open(script_path).read()))
                script_li.append(script_pre)
            elif isdir(script_path):
                subscript_files = os.listdir(script_path)
                if not subscript_files:
                    continue

                script_li.append("%s Scripts" % join(f, 'Scripts', script))
                subscripts = Tag(SOUP, 'ul')

                for subscript in subscript_files:
                    subscript_path = join(script_path, subscript)
                    subscript_li = Tag(SOUP, 'li')
                    subscript_li.append(subscript)
                    subscript_li.append(anchor_for_name(subscript_path))

                    subscript_pre = Tag(SOUP, 'pre')
                    subscript_pre.append(NavigableString(open(subscript_path).read()))
                    subscript_li.append(subscript_pre)

                    subscripts.append(subscript_li)

                script_li.append(subscripts)

            script_list.append(script_li)

        if script_list.contents:
            new_scripts = Tag(SOUP, 'li')
            new_scripts.append(NavigableString("%s Scripts" % f))
            new_scripts.append(script_list)
            script_ul.append(new_scripts)

def get_file_list(pkg, sub_package):
    """
    Expand the ul#files list in the template with a listing of the files
    contained in the sub package's BOM
    """

    file_ul = SOUP.find("ul", {'id': 'files'})
    if not file_ul:
        raise RuntimeError("""Template doesn't appear to have a <ul id="files">!""")

    if not "cleaned" in file_ul.get("class", ""):
        file_ul.contents = [] # Remove any template content

    for k, v in get_bom_contents(pkg + '/' + sub_package + '/Bom').items():
        file_ul.append(get_list_for_key(k, v))

def get_list_for_key(name, children):
    """
    Takes a key and a dictionary containing its children and recursively
    generates HTML lists items. Each item will contain the name and, if it has
    children, an unordered list containing those child items.
    """

    li = Tag(SOUP, "li")
    li.append(NavigableString(name))

    if children:
        ul = Tag(SOUP, "ul")
        for k, v in children.items():
            ul.append(get_list_for_key(k, v))
        li.append(ul)

    return li


def get_bom_contents(bom_file):
    """
    Run lsbom on the provided file and return a nested dict representing
    the file structure
    """

    lsbom = subprocess.Popen(
        ["/usr/bin/lsbom", bom_file], stdout=subprocess.PIPE
    ).communicate()[0]

    file_list = filter(None,
        [ l.split("\t")[0].lstrip("./") for l in lsbom.split("\n") ]
    )
    file_list.sort(key=str.lower)

    contents = dict()

    for f in file_list:
        contents = merge_list(contents, f.split('/'))

    return contents


def merge_list(master_dict, parts):
    """Given a dict and a list of elements, recursively create sub-dicts to represent each "row" """
    if parts:
        head = parts.pop(0)
        master_dict[head] = merge_list(master_dict.setdefault(head, dict()), parts)

    return master_dict

def anchor_for_name(*args):
    file_name = join(*args)
    digest    = hashlib.md5(file_name).hexdigest()
    return Tag(SOUP, "a", [("name", digest)])

def generate_package_report(pkg):
    """Given an expanded package, create an HTML listing of the contents"""

    SOUP.find('div', {'id': 'description'}).contents = get_description(pkg)

    load_scripts(pkg)

    if exists(pkg + "/Bom"):
        get_file_list(pkg, "")

    for f in os.listdir(pkg):
        if splitext(f)[1] == '.pkg':
            get_file_list(pkg, f)


def main(pkg_file_name, html_file_name):
    global SOUP

    print "Generating %s from %s" % (html_file_name, pkg_file_name)

    pkg  = expand_pkg(pkg_file_name)
    SOUP = BeautifulSoup(open("wtfUpdate.html").read())

    SOUP.find('title').contents = [
        NavigableString("wtfUpdate: %s" % basename(pkg_file_name))
    ]

    try:
        generate_package_report(pkg)
        html_file = open(html_file_name, 'w')
        html_file.write(str(SOUP))
        html_file.close()
    except RuntimeError, exc:
        print >> sys.stderr, "ERROR: %s" % exc
        sys.exit(1)
    finally:
        shutil.rmtree(pkg)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print >> sys.stderr, 'Usage: %s file.pkg [output_file.html]' % sys.argv[0]
        sys.exit(1)

    if len(sys.argv) < 3:
        sys.argv.append("%s.html" % splitext(basename(sys.argv[1]))[0])

    main(*sys.argv[1:3])

########NEW FILE########
