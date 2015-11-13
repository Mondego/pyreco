__FILENAME__ = api
import os,sys
import collections

__all__ = ['get_files', 'file_validator', 'runnable']

def get_files(exts=('py',), dirname=None):
    if dirname is None:
        dirname = os.getcwd()
    if type(exts) is str:
        exts = [exts]
    exts = set(exts)
    for root,dirs,files in os.walk(dirname):
        for f in files:
            if f.split('.')[-1].lower() not in exts:
                continue
            yield os.path.join(root, f)
            
class Wrapper(object):
    def __init__(self, func, api_type):
        self.scent_api_type = api_type
        self.func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
        
        if not isinstance(func, collections.Callable):
            raise TypeError("Given object is not callable.")
    
    def __repr__(self):
        return "<%s %s>" % (self.scent_api_type, self.func.__name__)
        
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

def file_validator(func):
    return Wrapper(func, api_type='file_validator')
    
def runnable(func):
    return Wrapper(func, api_type='runnable')
########NEW FILE########
__FILENAME__ = broadcasters
from __future__ import print_function
import sys


class NullEmitter(object):
    "Emitter that does nothing."
    def success(self, sniffer):
        pass
    def failure(self, sniffer):
        pass

class PrinterEmitter(object):
    "Simply emits exit status info to the console/terminal."
    def success(self, sniffer):
        print(sniffer.pass_colors['bg'](
            sniffer.pass_colors['fg']("In good standing")))

    def failure(self, sniffer):
        print(sniffer.fail_colors['bg'](
            sniffer.fail_colors['fg']("Failed - Back to work!")))

try:
    import pynotify
    class PynotifyEmitter(object):
        "Emits exit status info to libnotify"
        def __init__(self):
            pynotify.init('Sniffer')

        def success(self, sniffer):
            pynotify.Notification('Sniffer', 'In good standing').show()

        def failure(self, sniffer):
            pynotify.Notification('Sniffer', 'Failed - Back to work!').show()

except ImportError:
    PynotifyEmitter = NullEmitter

try:
    import gntp.notifier
    import socket
    class GrowlEmitter(object):
        "Emits exit status info to growl."
        def __init__(self):
            self.growl = gntp.notifier.GrowlNotifier(
                applicationName="Python Sniffer",
                notifications=["Passes", "Failures"],
                defaultNotifications=["Passes"],
            )
            try:
                self.growl.register()
            except socket.error:
                print("Failed to connect to growl! :(", file=sys.stderr)
                self.growl = None

        def success(self, sniffer):
            if self.growl:
                self.growl.notify(
                    noteType="Passes",
                    title="Sniffer",
                    description="In good standing!",
                    sticky=False,
                    priority=1,
                )

        def failure(self, sniffer):
            if self.growl:
                self.growl.notify(
                    noteType="Failures",
                    title="Sniffer",
                    description="Back to work!",
                    sticky=False,
                    priority=1,
                )

except ImportError:
    GrowlEmitter = NullEmitter


class Broadcaster(object):
    def __init__(self, *emitters):
        self.emitters = emitters

    def success(self, sniffer):
        for emit in self.emitters:
            emit.success(sniffer)

    def failure(self, sniffer):
        for emit in self.emitters:
            emit.failure(sniffer)


broadcaster = Broadcaster(
    PrinterEmitter(),
    GrowlEmitter(),
    PynotifyEmitter(),
)

########NEW FILE########
__FILENAME__ = main
"""
Main runners. Bootloads Sniffer class.
"""
from __future__ import print_function, absolute_import
from optparse import OptionParser
from sniffer.scanner import Scanner
from sniffer.runner import Sniffer, ScentSniffer
from sniffer.metadata import __version__
import sys

import colorama
colorama.init()

__all__ = ['run', 'main']

def run(sniffer_instance=None, wait_time=0.5, clear=True, args=(), debug=False):
    """
    Runs the auto tester loop. Internally, the runner instanciates the sniffer_cls and
    scanner class.

    ``sniffer_instance`` The class to run. Usually this is set to but a subclass of scanner.
                    Defaults to Sniffer. Sniffer class documentation for more information.
    ``wait_time``   The time, in seconds, to wait between polls. This is dependent on
                    the underlying scanner implementation. OS-specific libraries may choose
                    to ignore this parameter. Defaults to 0.5 seconds.
    ``clear``       Boolean. Set to True to clear the terminal before running the sniffer,
                    (alias, the unit tests). Defaults to True.
    ``args``        The arguments to pass to the sniffer/test runner. Defaults to ().
    ``debug``       Boolean. Sets the scanner and sniffer in debug mode, printing more internal
                    information. Defaults to False (and should usually be False).
    """
    if sniffer_instance is None:
        sniffer_instance = ScentSniffer()

    if debug:
        scanner = Scanner(sniffer_instance.watch_paths, logger=sys.stdout)
    else:
        scanner = Scanner(sniffer_instance.watch_paths)
    #sniffer = sniffer_cls(tuple(args), clear, debug)
    sniffer_instance.set_up(tuple(args), clear, debug)

    sniffer_instance.observe_scanner(scanner)
    scanner.loop(wait_time)

def main(sniffer_instance=None, test_args=(), progname=sys.argv[0], args=sys.argv[1:]):
    """
    Runs the program. This is used when you want to run this program standalone.

    ``sniffer_instance`` A class (usually subclassed of Sniffer) that hooks into the
                    scanner and handles running the test framework. Defaults to
                    Sniffer instance.
    ``test_args``   This function normally extracts args from ``--test-arg ARG`` command. A
                    preset argument list can be passed. Defaults to an empty tuple.
    ``program``     Program name. Defaults to sys.argv[0].
    ``args``        Command line arguments. Defaults to sys.argv[1:]
    """
    parser = OptionParser(version="%prog " + __version__)
    parser.add_option('-w', '--wait', dest="wait_time", metavar="TIME", default=0.5, type="float",
                      help="Wait time, in seconds, before possibly rerunning tests. "
                      "(default: %default)")
    parser.add_option('--no-clear', dest="clear_on_run", default=True, action="store_false",
                      help="Disable the clearing of screen")
    parser.add_option('--debug', dest="debug", default=False, action="store_true",
                      help="Enabled debugging output. (default: %default)")
    parser.add_option('-x', '--test-arg', dest="test_args", default=[], action="append",
                      help="Arguments to pass to nose (use multiple times to pass multiple "
                      "arguments.)")
    (options, args) = parser.parse_args(args)
    test_args = test_args + tuple(options.test_args)

    if options.debug:
        print("Options:", options)
        print("Test Args:", test_args)
    try:
        print("Starting watch...")
        run(sniffer_instance, options.wait_time, options.clear_on_run, test_args, options.debug)
    except KeyboardInterrupt:
        print("Good bye.")
    except Exception:
        import traceback
        traceback.print_exc()
        return sys.exit(1)
    return sys.exit(0)

if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    main()

########NEW FILE########
__FILENAME__ = metadata
__all__ = [
    '__author__', '__author_email__', '__copyright__', '__credits__',
    '__license__', '__version__'
]


__author__ = "Jeff Hui"
__author_email__ = "jeff@jeffhui.net"
__copyright__ = "Copyright 2013, Jeff Hui"
__credits__ = [
    "Jeff Hui",
    "Patrice Neff",
    "Andrew Lee",
    "Will Harris",
    "Jonas Tingeborn"
]

__license__ = "MIT"
__version__ = "0.3.2"

########NEW FILE########
__FILENAME__ = modules_restore_point
import sys

__all__ = ['ModulesRestorePoint']

# Really only deletes modules that didn't appear in the restore point.
class ModulesRestorePoint(object):
    def __init__(self, sys_modules=sys.modules):
        self._saved_modules = None
        self._sys_modules = sys_modules
        self.save()

    def save(self):
        """Saves the currently loaded modules for restore."""
        self._saved_modules = set(self._sys_modules.keys())

    def restore(self):
        """Unloads all modules that weren't loaded when save_modules was called."""
        sys = set(self._sys_modules.keys())
        for mod_name in sys.difference(self._saved_modules):
            del self._sys_modules[mod_name]

########NEW FILE########
__FILENAME__ = runner
from __future__ import print_function
from __future__ import absolute_import
from .modules_restore_point import ModulesRestorePoint
from .broadcasters import broadcaster
from functools import wraps
from termstyle import bg_red, bg_green, white
import platform
import os
import sys
from . import scent_picker

__all__ = ['Sniffer']

try:
    _ = StandardError
except NameError:
    StandardError = Exception

# for debugging
def echo(text):
    def wrapped(filepath):
        print(text % {'file': filepath})
    return wrapped

class Sniffer(object):
    """
    Handles the execution of the sniffer. The interface that main.run expects is:

    ``set_up(test_args, clear, debug)``

      ``test_args`` The arguments to pass to the test runner.
      ``clear``     Boolean. Set to True if we should clear console before running
                    the tests.
      ``debug``     Boolean. Set to True if we want to print debugging information.

    ``observe_scanner(scanner)``

      ``scanner``   The scanner instance to hook events into. By default, ``self._run`` is
                    attached, which then calls self.run(). The run method should return
                    True on passing and False on failure.
    """
    def __init__(self):
        self.modules = ModulesRestorePoint()
        self._scanners = []
        self.pass_colors = {'fg': white, 'bg': bg_green}
        self.fail_colors = {'fg': white, 'bg': bg_red}
        self.watch_paths = ('.',)
        self.set_up()

    def set_up(self, test_args=(), clear=True, debug=False):
        """
        Sets properties right before calling run.

          ``test_args`` The arguments to pass to the test runner.
          ``clear``     Boolean. Set to True if we should clear console before running
                        the tests.
          ``debug``     Boolean. Set to True if we want to print debugging information.
        """
        self.test_args = test_args
        self.debug, self.clear = debug, clear

    def absorb_args(self, func):
        """
        Calls a function without any arguments. The returned caller function
        accepts any arguments (and throws them away).
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func()
        return wrapper

    def observe_scanner(self, scanner):
        """
        Hooks into multiple events of a scanner.
        """
        scanner.observe(scanner.ALL_EVENTS, self.absorb_args(self.modules.restore))
        if self.clear:
            scanner.observe(scanner.ALL_EVENTS, self.absorb_args(self.clear_on_run))
        scanner.observe(scanner.ALL_EVENTS, self.absorb_args(self._run))
        if self.debug:
            scanner.observe('created',  echo("callback - created  %(file)s"))
            scanner.observe('modified', echo("callback - changed  %(file)s"))
            scanner.observe('deleted',  echo("callback - deleted  %(file)s"))
        self._scanners.append(scanner)

    def clear_on_run(self, prefix="Running Tests:"):
        """Clears console before running the tests."""
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
        if prefix:
            print(prefix)

    def _stop(self):
        """Calls stop() to all scanner in an attempt to quit."""
        for scanner in self._scanners:
            scanner.stop()

    def _run(self):
        """Calls self.run() and wraps for errors."""
        try:
            if self.run():
                broadcaster.success(self)
            else:
                broadcaster.failure(self)
        except StandardError:
            import traceback
            traceback.print_exc()
            self._stop()
            raise
        except Exception:
            self._stop()
            raise
        return True

    def run(self):
        """
        Runs the unit test framework. Can be overridden to run anything.
        Returns True on passing and False on failure.
        """
        try:
            import nose
            arguments = [sys.argv[0]] + list(self.test_args)
            return nose.run(argv=arguments)
        except ImportError:
            print()
            print("*** Nose library missing. Please install it. ***")
            print()
            raise

class ScentSniffer(Sniffer):
    """Runs arbitrary python code in the cwd's scent.py file."""
    def __init__(self, cwd=None, scent="scent.py"):
        self.cwd = cwd or os.getcwd()
        self.scent = scent_picker.exec_from_dir(self.cwd, scent)
        super(ScentSniffer, self).__init__()
        self.update_from_scent()

    def update_from_scent(self):
        if self.scent:
            self.pass_colors['fg'] = self.scent.fg_pass
            self.pass_colors['bg'] = self.scent.bg_pass
            self.fail_colors['fg'] = self.scent.fg_fail
            self.fail_colors['bg'] = self.scent.bg_fail
            self.watch_paths = self.scent.watch_paths

    def refresh_scent(self, filepath):
        if self.scent and filepath == self.scent.filename:
            print("Reloaded Scent:", filepath)
            for s in self._scanners:
                self.unobserve_scanner(s)
            self.scent = self.scent.reload()
            self.update_from_scent()
            for s in self._scanners:
                self.scent_observe_scanner(s)

    def unobserve_scanner(self, scanner):
        for v in self.scent.validators:
            if self.debug:
                print("Removed", repr(v))
            scanner.remove_validator(v)

    def scent_observe_scanner(self, scanner):
        if self.scent:
            for v in self.scent.validators:
                if self.debug:
                    print("Added", repr(v))
                scanner.add_validator(v)

    def observe_scanner(self, scanner):
        scanner.observe('created', self.refresh_scent)
        scanner.observe('modified', self.refresh_scent)
        self.scent_observe_scanner(scanner)
        return super(ScentSniffer, self).observe_scanner(scanner)

    def clear_on_run(self):
        super(ScentSniffer, self).clear_on_run(None)

    def run(self):
        """
        Runs the CWD's scent file.
        """
        if not self.scent or len(self.scent.runners) == 0:
            print("Did not find 'scent.py', running nose:")
            return super(ScentSniffer, self).run()
        else:
            print("Using scent:")
            arguments = [sys.argv[0]] + list(self.test_args)
            return self.scent.run(arguments)
        return True

########NEW FILE########
__FILENAME__ = base
"""
Scanner class.

Provides a polling technique which is an OS-independent and uses no third-party
libraries at the cost of performance. The polling technique constantly walks through
the directory tree to see which files changed, calling os.stat on the files.
"""
import os
import time
import collections

class BaseScanner(object):
    """
    Provides basic hooking and logging mechanisms.
    """
    ALL_EVENTS = ('created', 'modified', 'deleted', 'init')
    def __init__(self, paths, logger=None, *args, **kwargs):
        self._validators = []
        self._paths = [os.path.abspath(p) for p in paths]
        self._logger = logger
        self._events = {}
        for e in self.ALL_EVENTS:
            self._events[e] = []
        self._watched_files = {}

    def add_validator(self, func):
        if not isinstance(func, collections.Callable):
            raise TypeError("Param should return boolean and accept a filename str.")
        self._validators.append(func)

    def remove_validator(self, func):
        self._validators.remove(func)

    def trigger_modified(self, filepath):
        """Triggers modified event if the given filepath mod time is newer."""
        mod_time = self._get_modified_time(filepath)
        if mod_time > self._watched_files.get(filepath, 0):
            self._trigger('modified', filepath)
            self._watched_files[filepath] = mod_time

    def trigger_created(self, filepath):
        """Triggers created event if file exists."""
        if os.path.exists(filepath):
            self._trigger('created', filepath)

    def trigger_deleted(self, filepath):
        """Triggers deleted event if the flie doesn't exist."""
        if not os.path.exists(filepath):
            self._trigger('deleted', filepath)

    def trigger_init(self):
        """Triggers initialization event."""
        self._trigger('init')

    def _get_modified_time(self, filepath):
        """Returns the modified type for the given filepath or None on failure"""
        if not os.path.isfile(filepath):
            return None
        return os.stat(filepath).st_mtime

    def loop(self, sleep_time=0.5, callback=None):
        """Runs a blocking loop."""
        raise NotImplemented()

    def step(self):
        """
        Looks at changes temporarily before stopping.

        Fires a series of events only once, as defined by the backend. But step is
        always ensured to stop.
        """
        raise NotImplemented()

    def stop(self):
        """
        Used by an event caller to stop the blocking loop.
        """
        raise NotImplemented()

    @property
    def paths(self):
        """
        A tuple of directories to watch.
        """
        return tuple(self._paths)

    def add_path(self, path):
        """
        Adds a directory to watch.
        """
        self._paths.append(path)
        return self

    def log(self, *message):
        """
        Logs a messate to a defined io stream if available.
        """
        if self._logger is None:
            return
        s = " ".join([str(m) for m in message])
        self._logger.write(s+'\n')
        self._logger.flush()

    def _trigger(self, event_name, *args, **kwargs):
        """
        Triggers a given event with the following *args and **kwargs parameters.
        """
        self.log('event: %s' % event_name, *args)
        for f in self._events[event_name]:
            f(*args, **kwargs)

    def default_validator(self, filepath):
        """
        The default validator only accepts files ending in .py
        (and not prefixed by a period).
        """
        return filepath.endswith('.py') and not os.path.basename(filepath).startswith('.')

    def not_repo(self, filepath):
        """
        This excludes repository directories because they cause some exceptions occationally.
        """
        filepath = set(filepath.replace('\\', '/').split('/'))
        for p in ('.git', '.hg', '.svn', '.cvs', '.bzr'):
            if p in filepath:
                return False
        return True

    def is_valid_type(self, filepath):
        """
        Returns True if the given filepath is a valid watchable filetype.
        The filepath can be assumed to be a file (not a directory).
        """
        if len(self._validators) == 0:
            validators = [self.default_validator, self.not_repo]
        else:
            validators = self._validators + [self.not_repo]
        for validator in validators:
            if not validator(filepath):
                return False
        return True

    def _modify_event(self, event_name, method, func):
        """
        Wrapper to call a list's method from one of the events
        """
        if event_name not in self.ALL_EVENTS:
            raise TypeError('event_name ("%s") can only be one of the following: %s' % \
                            (event_name, repr(self.ALL_EVENTS)))
        if not isinstance(func, collections.Callable):
            raise TypeError('func must be callable to be added as an observer.')
        getattr(self._events[event_name], method)(func)

    def observe(self, event_name, func):
        """
        event_name := {'created', 'modified', 'deleted'}, list, tuple

        Attaches a function to run to a particular event. The function must be
        unique to be removed cleanly. Alternatively, event_name can be an list/tuple
        if any of the string possibilities to be added on multiple events.
        """
        if isinstance(event_name, list) or isinstance(event_name, tuple):
            for name in event_name:
                self.observe(name, func)
            return
        self.log(func.__name__, "attached to", event_name)
        self._modify_event(event_name, 'append', func)

    def unobserve(self, event_name, func):
        """
        event_name := {'created', 'modified', 'deleted'}, list, tuple

        Removes an observer function from a particular event that was added by
        observe().
        """
        if isinstance(event_name, list) or isinstance(event_name, tuple):
            for name in event_name:
                self.unobserve(name, func)
            return
        self.log(func.__name__, "dettached from", event_name)
        self._modify_event(event_name, 'remove', func)

class PollingScanner(BaseScanner):
    """
    Implements the naive, but cross-platform file scanner.
    """
    def __init__(self, *args, **kwargs):
        super(PollingScanner, self).__init__(*args, **kwargs)
        self._watched_files = {}
        self._running = False
        self._warn = kwargs.get('warn_missing_lib', True)

    def _watch_file(self, filepath, trigger_event=True):
        """Adds the file's modified time into its internal watchlist."""
        is_new = filepath not in self._watched_files
        if trigger_event:
            if is_new:
                self.trigger_created(filepath)
            else:
                self.trigger_modified(filepath)
        try:
            self._watched_files[filepath] = self._get_modified_time(filepath)
        except OSError:
            return # didn't happen

    def _unwatch_file(self, filepath, trigger_event=True):
        """
        Removes the file from the internal watchlist if exists.
        """
        if filepath not in self._watched_files:
            return
        if trigger_event:
            self.trigger_deleted(filepath)
        del self._watched_files[filepath]

    def _is_modified(self, filepath):
        """
        Returns True if the file has been modified since last seen.
        Will return False if the file has not been seen before.
        """
        if self._is_new(filepath):
            return False
        mtime = self._get_modified_time(filepath)
        return self._watched_files[filepath] < mtime

    def _requires_new_modtime(self, filepath):
        """Returns True if the stored modtime needs to be updated."""
        return self._is_new(filepath) or self._is_modified(filepath)

    def _is_new(self, filepath):
        """Returns True if file is not already on the watch list."""
        return filepath not in self._watched_files

    def loop(self, sleep_time=1, callback=None):
        """
        Goes into a blocking IO loop. If polling is used, the sleep_time is
        the interval, in seconds, between polls.
        """

        self.log("No supported libraries found: using polling-method.")
        self._running = True
        self.trigger_init()
        self._scan(trigger=False) # put after the trigger
        if self._warn:
            print("""
You should install a third-party library so I don't eat CPU.
Supported libraries are:
  - pyinotify (Linux)
  - pywin32 (Windows)
  - MacFSEvents (OSX)

Use pip or easy_install and install one of those libraries above.
""")
        while self._running:
            self._scan()
            if isinstance(callback, collections.Callable):
                callback()
            time.sleep(sleep_time)

    def step(self):
        self._scan()

    def stop(self):
        self._running = False

    def _scan(self, trigger=True):
        """
        Walks through the directory to look for changes of the given file types.
        Returns True if changes occurred (False otherwise).
        Returns None if polling method isn't being used.
        """
        changed = False
        files_seen = []
        os_path_join = os.path.join
        for path in self.paths:
            for root, dirs, files in os.walk(path):
                for f in files:
                    fpath = os_path_join(root, f)
                    if not self.is_valid_type(fpath):
                        continue
                    files_seen.append(fpath)
                    if self._requires_new_modtime(fpath):
                        self._watch_file(fpath, trigger)
                        changed = True
            files_seen = set(files_seen)
            for f in self._watched_files:
                if f not in files_seen:
                    self._unwatch_file(f, trigger)
                    changed = True
        return changed

########NEW FILE########
__FILENAME__ = fsevents_scanner
"""
Scanner that relies on the MacFSEvents (OSX) library.

This is an OS-specific implementation that eliminates the constant polling of the
directory tree by hooking into OSX's IO events.
"""
from __future__ import absolute_import
from .base import BaseScanner
import os
import fsevents
import time
import sys

class FSEventsScanner(BaseScanner):
    """
    This works with MacFSEvents to hook into OSX's file watching mechanisms.
    """
    def __init__(self, *args, **kwargs):
        super(FSEventsScanner, self).__init__(*args, **kwargs)
        self._observer = self._generate_observer()

    def _generate_observer(self):
        observer = fsevents.Observer()
        # use file_events=True to mimic other implementations
        for path in self.paths:
            stream = fsevents.Stream(self._callback, path, file_events=True)
            observer.schedule(stream)
        return observer

    def loop(self, sleep_time=None):
        self.log("Library of choice: MacFSEvents")
        self.trigger_init()
        # using observer.run() doesn't let us catch the keyboard interrupt
        self._observer.start() # separate thread
        try:
            while 1:
                time.sleep(60) # simulate blocking
        except (KeyboardInterrupt, OSError, IOError):
            self.stop()
        #observer.run() # blocking

    def stop(self):
        # Ugly hack, calling Observer.stop() creates a lot of atexit errors
        # that we just want to escape without problems.
        #
        # So we're silently absorbing all the errors
        try:
            from io import StringIO
        except:
            try:
                from cStringIO import StringIO
            except:
                from StringIO import StringIO
        old_err, old_out = sys.stderr, sys.stdout
        sys.stderr, sys.stdout = StringIO(), StringIO()

        self._observer.stop()

        sys.stderr, sys.stdout = old_err, old_out

#    def step(self):
#        observer = self._generate_observer()
#        observer.start()
#        time.sleep(1) # it's really a guess at this point :(
#        observer.stop()
#        observer.join()

    def _callback(self, event):
        if not self.is_valid_type(event.name):
            return
        if event.mask & (fsevents.IN_MODIFY):
            self.trigger_modified(event.name)
        if event.mask & fsevents.IN_CREATE:
            self.trigger_created(event.name)
        if event.mask & fsevents.IN_DELETE:
            self.trigger_deleted(event.name)

########NEW FILE########
__FILENAME__ = pyinotify_scanner
from __future__ import absolute_import
from .base import BaseScanner
import platform

import pyinotify

class EventHandler(pyinotify.ProcessEvent):
    def __init__(self, scanner):
        self._scanner = scanner

    def process_IN_CREATE(self, event):
        if self._scanner.is_valid_type(event.pathname):
            self._scanner.trigger_created(event.pathname)

    def process_IN_DELETE(self, event):
        if self._scanner.is_valid_type(event.pathname):
            self._scanner.trigger_deleted(event.pathname)

    def process_IN_MODIFY(self, event):
        #self._process('modified', event.pathname)
        if self._scanner.is_valid_type(event.pathname):
            self._scanner.trigger_modified(event.pathname)


class PyINotifyScanner(BaseScanner):
    """
    Scanner that uses pyinotify (alias, inotify) for notification events.
    """
    def __init__(self, *args, **kwargs):
        super(PyINotifyScanner, self).__init__(*args, **kwargs)
        self.log("Library of choice: pyinotify")
        self._watcher = pyinotify.WatchManager()
        self._notifier = self._generate_notifier()

    def __deinit__(self):
        if self._notifier is not None:
            self._notifier.stop()

    def _generate_notifier(self):
        handler = EventHandler(self)

        notifier = pyinotify.Notifier(self._watcher, handler)
        mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_MODIFY
        for path in self.paths:
            self._watcher.add_watch(path, mask, rec=True, auto_add=True,
                                    exclude_filter=self.is_valid_type)
        
        return notifier

    def loop(self, sleep_time=None, callback=None):
        self.trigger_init()
        try:
            self._notifier.loop(callback)
        except KeyboardInterrupt:
            self._notifier.stop()
            raise

    def step(self):
        self._notifier.process_events()
        if self._notifier.check_events(timeout=1000):
            self.read_events()
        self._notifier.stop()

    def stop(self):
        self._notifier.stop()

########NEW FILE########
__FILENAME__ = pywin_scanner
"""
File watching on windows using the Win32API.
Requires the pywin32 library

The code is based off Tim Golden's work:
http://timgolden.me.uk/python/win32_how_do_i/watch_directory_for_changes.html
"""
from __future__ import absolute_import
from .base import BaseScanner
import win32file
import win32con
import os
import thread, Queue, time

ACTIONS = {}
for i, name in enumerate(('Created', 'Deleted', 'Updated', 'Renamed from', 'Renamed to')):
    ACTIONS[i] = name
FILE_LIST_DIR = 0x0001

class PyWinScanner(BaseScanner):
    """
    Scanner built on PyWin32 (aka, Win32API).
    """
    def __init__(self, *args, **kwargs):
        super(PyWinScanner, self).__init__(*args, **kwargs)
        self._running = False
        self._q = Queue.Queue(1)
        
    def _get_handle(self, path):
        return win32file.CreateFile(
            path,                                                 # filename
            FILE_LIST_DIR,                                        # desired access
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE, # share mode
            None,                                                 # security attrs
            win32con.OPEN_EXISTING,                               # creation disposition
            win32con.FILE_FLAG_BACKUP_SEMANTICS,                  # flags & attrs
            None                                                  # template file (?)
        )

    def _get_changes_blocking(self, handle):
        result = win32file.ReadDirectoryChangesW(
            handle, # directory handle
            1024, # buffer len (return size)
            True, # watch recursively
            # notify filters
            win32con.FILE_NOTIFY_CHANGE_FILE_NAME | # create/rename/delete files
            #win32con.FILE_NOTIFY_CHANGE_DIR_NAME | # create/rename/delete dirs
            win32con.FILE_NOTIFY_CHANGE_LAST_WRITE, #| # on system write
            #win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
            #win32con.FILE_NOTIFY_CHANGE_SIZE |
            #win32con.FILE_NOTIFY_CHANGE_SECURITY,
            None, # overlapped structure (?)
            None  # completion routine (async only)
        )
        self._q.put(result)

    """
      Run the file system monitoring in a separate thread, so that the user
      can interrupt (terminate) the main thread from the console.
    """
    def _get_changes(self, handle):
        thread.start_new_thread(self._get_changes_blocking, (handle,))
        while self._q.empty():
            time.sleep(0.1)
        return self._q.get()

    def step(self):
        for path, handle in ((p, self._get_handle(p)) for p in self.paths):
            results = self._get_changes(handle)
            for action, filename in results:
                fullpath = os.path.join(path, filename)
                if not self.is_valid_type(fullpath):
                    continue
                action = ACTIONS.get(action, "unknown")
                if action == 'Created':
                    self.trigger_created(fullpath)
                elif action in ('Updated', 'Renamed to', 'Renamed from'):
                    self.trigger_modified(fullpath)
                elif action == 'Deleted':
                    self.trigger_deleted(fullpath)
        
    def loop(self, sleep_time=None):
        self.log("Library of choice: PyWin32 (eww)")
        self.trigger_init()
        self._running = True
        while self._running:
            self.step()
            # TODO: figure out if we really need to sleep

    def stop(self):
        self._running = False

########NEW FILE########
__FILENAME__ = scent_picker
from __future__ import print_function
g = globals().copy()
import os, sys, termstyle

class ScentModule(object):
    def __init__(self, mod, filename):
        self.mod = mod
        self.filename = filename
        self.validators = []
        self.runners = []
        for name in dir(self.mod):
            obj = getattr(self.mod, name)
            type = getattr(obj, 'scent_api_type', None)
            if type == 'runnable':
                self.runners.append(obj)
            elif type == 'file_validator':
                self.validators.append(obj)
        self.runners = tuple(self.runners)
        self.validators = tuple(self.validators)
        print(self.validators)
        
    def reload(self):
        try:
            return load_file(self.filename)
        except Exception:
            import traceback
            traceback.print_exc()
            print()
            print("Still using previously valid Scent.")
            return self
    
    def run(self, args):
        try:
            for r in self.runners:
                if not r(*args):
                    return False
            return True
        except Exception:
            import traceback
            traceback.print_exc()
            print()
            return False
        
    @property
    def fg_pass(self):
        return getattr(self.mod, 'pass_fg_color', termstyle.black)
    @property
    def bg_pass(self):
        return getattr(self.mod, 'pass_bg_color', termstyle.bg_green)
    
    @property
    def fg_fail(self):
        return getattr(self.mod, 'fail_fg_color', termstyle.white)
    @property
    def bg_fail(self):
        return getattr(self.mod, 'fail_bg_color', termstyle.bg_red)

    @property
    def watch_paths(self):
        return getattr(self.mod, 'watch_paths', ('.',))


def load_file(filename):
    "Runs the given scent.py file."
    mod_name = '.'.join(os.path.basename(filename).split('.')[:-1])
    mod_path = os.path.dirname(filename)
    
    global_vars = globals()
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    if mod_path not in set(sys.modules.keys()):
        sys.path.insert(0, mod_path)
    return ScentModule(__import__(mod_name, g, g), filename)
    
def exec_from_dir(dirname=None, scent="scent.py"):
    """Runs the scent.py file from the given directory (cwd if None given).
    
    Returns module if loaded a scent, None otherwise.
    """
    if dirname is None:
        dirname = os.getcwd()
    files = os.listdir(dirname)
    
    if scent not in files:
        return None
    
    return load_file(os.path.join(dirname, scent))

########NEW FILE########
