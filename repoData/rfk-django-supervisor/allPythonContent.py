__FILENAME__ = config
"""

djsupervisor.config:  config loading and merging code for djsupervisor
----------------------------------------------------------------------

The code in this module is responsible for finding the supervisord.conf
files from all installed apps, merging them together with the config
files from your project and any options specified on the command-line,
and producing a final config file to control supervisord/supervisorctl.

"""

import sys
import os
import hashlib

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from ConfigParser import RawConfigParser, NoSectionError, NoOptionError

from django import template
from django.conf import settings
from django.utils.importlib import import_module

from djsupervisor.templatetags import djsupervisor_tags

CONFIG_FILE = getattr(settings, "SUPERVISOR_CONFIG_FILE", "supervisord.conf")


def get_merged_config(**options):
    """Get the final merged configuration for supvervisord, as a string.

    This is the top-level function exported by this module.  It combines
    the config file from the main project with default settings and those
    specified in the command-line, processes various special section names,
    and returns the resulting configuration as a string.
    """
    #  Find and load the containing project module.
    #  This can be specified explicity using the --project-dir option.
    #  Otherwise, we attempt to guess by looking for the manage.py file.
    project_dir = options.get("project_dir")
    if project_dir is None:
        project_dir = guess_project_dir()
    # Find the config file to load.
    # Default to <project-dir>/supervisord.conf.
    config_file = options.get("config_file")
    if config_file is None:
        config_file = os.path.join(project_dir,CONFIG_FILE)
    #  Build the default template context variables.
    #  This is mostly useful information about the project and environment.
    ctx = {
        "PROJECT_DIR": project_dir,
        "PYTHON": os.path.realpath(os.path.abspath(sys.executable)),
        "SUPERVISOR_OPTIONS": rerender_options(options),
        "settings": settings,
        "environ": os.environ,
    }
    #  Initialise the ConfigParser.
    #  Fortunately for us, ConfigParser has merge-multiple-config-files
    #  functionality built into it.  You just read each file in turn, and
    #  values from later files overwrite values from former.
    cfg = RawConfigParser()
    #  Start from the default configuration options.
    data = render_config(DEFAULT_CONFIG,ctx)
    cfg.readfp(StringIO(data))
    #  Add in the project-specific config file.
    with open(config_file,"r") as f:
        data = render_config(f.read(),ctx)
    cfg.readfp(StringIO(data))
    #  Add in the options specified on the command-line.
    cfg.readfp(StringIO(get_config_from_options(**options)))
    #  Add options from [program:__defaults__] to each program section
    #  if it happens to be missing that option.
    PROG_DEFAULTS = "program:__defaults__"
    if cfg.has_section(PROG_DEFAULTS):
        for option in cfg.options(PROG_DEFAULTS):
            default = cfg.get(PROG_DEFAULTS,option)
            for section in cfg.sections():
                if section.startswith("program:"):
                    if not cfg.has_option(section,option):
                        cfg.set(section,option,default)
        cfg.remove_section(PROG_DEFAULTS)
    #  Add options from [program:__overrides__] to each program section
    #  regardless of whether they already have that option.
    PROG_OVERRIDES = "program:__overrides__"
    if cfg.has_section(PROG_OVERRIDES):
        for option in cfg.options(PROG_OVERRIDES):
            override = cfg.get(PROG_OVERRIDES,option)
            for section in cfg.sections():
                if section.startswith("program:"):
                    cfg.set(section,option,override)
        cfg.remove_section(PROG_OVERRIDES)
    #  Make sure we've got a port configured for supervisorctl to
    #  talk to supervisord.  It's passworded based on secret key.
    #  If they have configured a unix socket then use that, otherwise
    #  use an inet server on localhost at fixed-but-randomish port.
    username = hashlib.md5(settings.SECRET_KEY).hexdigest()[:7]
    password = hashlib.md5(username).hexdigest()
    if cfg.has_section("unix_http_server"):
        set_if_missing(cfg,"unix_http_server","username",username)
        set_if_missing(cfg,"unix_http_server","password",password)
        serverurl = "unix://" + cfg.get("unix_http_server","file")
    else:
        #  This picks a "random" port in the 9000 range to listen on.
        #  It's derived from the secret key, so it's stable for a given
        #  project but multiple projects are unlikely to collide.
        port = int(hashlib.md5(password).hexdigest()[:3],16) % 1000
        addr = "127.0.0.1:9%03d" % (port,)
        set_if_missing(cfg,"inet_http_server","port",addr)
        set_if_missing(cfg,"inet_http_server","username",username)
        set_if_missing(cfg,"inet_http_server","password",password)
        serverurl = "http://" + cfg.get("inet_http_server","port")
    set_if_missing(cfg,"supervisorctl","serverurl",serverurl)
    set_if_missing(cfg,"supervisorctl","username",username)
    set_if_missing(cfg,"supervisorctl","password",password)
    set_if_missing(cfg,"rpcinterface:supervisor",
                       "supervisor.rpcinterface_factory",
                       "supervisor.rpcinterface:make_main_rpcinterface")
    #  Remove any [program:] sections with exclude=true
    for section in cfg.sections():
        try:
            if cfg.getboolean(section,"exclude"):
                cfg.remove_section(section)
        except NoOptionError:
            pass
    #  Sanity-check to give better error messages.
    for section in cfg.sections():
        if section.startswith("program:"):
            if not cfg.has_option(section,"command"):
                msg = "Process name '%s' has no command configured"
                raise ValueError(msg % (section.split(":",1)[-1]))
    #  Write it out to a StringIO and return the data
    s = StringIO()
    cfg.write(s)
    return s.getvalue()


def render_config(data,ctx):
    """Render the given config data using Django's template system.

    This function takes a config data string and a dict of context variables,
    renders the data through Django's template system, and returns the result.
    """
    djsupervisor_tags.current_context = ctx
    data = "{% load djsupervisor_tags %}" + data
    t = template.Template(data)
    c = template.Context(ctx)
    return t.render(c).encode("ascii")


def get_config_from_options(**options):
    """Get config file fragment reflecting command-line options."""
    data = []
    #  Set whether or not to daemonize.
    #  Unlike supervisord, our default is to stay in the foreground.
    data.append("[supervisord]\n")
    if options.get("daemonize",False):
        data.append("nodaemon=false\n")
    else:
        data.append("nodaemon=true\n")
    if options.get("pidfile",None):
        data.append("pidfile=%s\n" % (options["pidfile"],))
    if options.get("logfile",None):
        data.append("logfile=%s\n" % (options["logfile"],))
    #  Set which programs to launch automatically on startup.
    for progname in options.get("launch",None) or []:
        data.append("[program:%s]\nautostart=true\n" % (progname,))
    for progname in options.get("nolaunch",None) or []:
        data.append("[program:%s]\nautostart=false\n" % (progname,))
    #  Set which programs to include/exclude from the config
    for progname in options.get("include",None) or []:
        data.append("[program:%s]\nexclude=false\n" % (progname,))
    for progname in options.get("exclude",None) or []:
        data.append("[program:%s]\nexclude=true\n" % (progname,))
    #  Set which programs to autoreload when code changes.
    #  When this option is specified, the default for all other
    #  programs becomes autoreload=false.
    if options.get("autoreload",None):
        data.append("[program:autoreload]\nexclude=false\nautostart=true\n")
        data.append("[program:__defaults__]\nautoreload=false\n")
        for progname in options["autoreload"]:
            data.append("[program:%s]\nautoreload=true\n" % (progname,))
    #  Set whether to use the autoreloader at all.
    if options.get("noreload",False):
        data.append("[program:autoreload]\nexclude=true\n")
    return "".join(data)


def guess_project_dir():
    """Find the top-level Django project directory.

    This function guesses the top-level Django project directory based on
    the current environment.  It looks for module containing the currently-
    active settings module, in both pre-1.4 and post-1.4 layours.
    """
    projname = settings.SETTINGS_MODULE.split(".",1)[0]
    projmod = import_module(projname)
    projdir = os.path.dirname(projmod.__file__)

    # For Django 1.3 and earlier, the manage.py file was located
    # in the same directory as the settings file.
    if os.path.isfile(os.path.join(projdir,"manage.py")):
        return projdir

    # For Django 1.4 and later, the manage.py file is located in
    # the directory *containing* the settings file.
    projdir = os.path.abspath(os.path.join(projdir, os.path.pardir))
    if os.path.isfile(os.path.join(projdir,"manage.py")):
        return projdir

    msg = "Unable to determine the Django project directory;"\
          " use --project-dir to specify it"
    raise RuntimeError(msg)


def set_if_missing(cfg,section,option,value):
    """If the given option is missing, set to the given value."""
    try:
        cfg.get(section,option)
    except NoSectionError:
        cfg.add_section(section)
        cfg.set(section,option,value)
    except NoOptionError:
        cfg.set(section,option,value)


def rerender_options(options):
    """Helper function to re-render command-line options.

    This assumes that command-line options use the same name as their
    key in the options dictionary.
    """
    args = []
    for name,value in options.iteritems():
        name = name.replace("_","-")
        if value is None:
            pass
        elif isinstance(value,bool):
            if value:
                args.append("--%s" % (name,))
        elif isinstance(value,list):
            for item in value:
                args.append("--%s=%s" % (name,item))
        else:
            args.append("--%s=%s" % (name,value))
    return " ".join(args)


#  These are the default configuration options provided by djsupervisor.
#
DEFAULT_CONFIG = """

;  In debug mode, we watch for changes in the project directory and inside
;  any installed apps.  When something changes, restart all processes.
[program:autoreload]
command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py supervisor {{ SUPERVISOR_OPTIONS }} autoreload
autoreload=true
{% if not settings.DEBUG %}
exclude=true
{% endif %}

;  All programs are auto-reloaded by default.
[program:__defaults__]
autoreload=true
redirect_stderr=true

[supervisord]
{% if settings.DEBUG %}
loglevel=debug
{% endif %}

"""

########NEW FILE########
__FILENAME__ = events

import time

from watchdog.events import PatternMatchingEventHandler


class CallbackModifiedHandler(PatternMatchingEventHandler):
    """
    A pattern matching event handler that calls the provided
    callback when a file is modified.
    """
    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.repeat_delay = kwargs.pop("repeat_delay", 0)
        self.last_fired_time = 0
        super(CallbackModifiedHandler, self).__init__(*args, **kwargs)

    def on_modified(self, event):
        super(CallbackModifiedHandler, self).on_modified(event)
        now = time.time()
        if self.last_fired_time + self.repeat_delay < now:
            if not event.is_directory:
                self.last_fired_time = now
                self.callback()

########NEW FILE########
__FILENAME__ = supervisor
"""

djsupervisor.management.commands.supervisor:  djsupervisor mangement command
----------------------------------------------------------------------------

This module defines the main management command for the djsupervisor app.
The "supervisor" command acts like a combination of the supervisord and
supervisorctl programs, allowing you to start up, shut down and manage all
of the proceses defined in your Django project.

The "supervisor" command suports several modes of operation:

    * called without arguments, it launches supervisord to spawn processes.

    * called with the single argument "getconfig", is prints the merged
      supervisord config to stdout.

    * called with the single argument "autoreload", it watches for changes
      to python modules and restarts all processes if things change.

    * called with any other arguments, it passes them on the supervisorctl.

"""

from __future__ import absolute_import, with_statement

import sys
import os
import time
from optparse import make_option
from textwrap import dedent
import traceback
from ConfigParser import RawConfigParser, NoOptionError
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from supervisor import supervisord, supervisorctl

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from djsupervisor.config import get_merged_config
from djsupervisor.events import CallbackModifiedHandler

AUTORELOAD_PATTERNS = getattr(settings, "SUPERVISOR_AUTORELOAD_PATTERNS",
                              ['*.py'])
AUTORELOAD_IGNORE = getattr(settings, "SUPERVISOR_AUTORELOAD_IGNORE_PATTERNS", 
                            [".*", "#*", "*~"])

class Command(BaseCommand):

    args = "[<command> [<process>, ...]]"

    help = dedent("""
           Manage processes with supervisord.

           With no arguments, this spawns the configured background processes.

           With a command argument it lets you control the running processes.
           Available commands include:

               supervisor getconfig
               supervisor shell
               supervisor start <progname>
               supervisor stop <progname>
               supervisor restart <progname>

           """).strip()

    option_list = BaseCommand.option_list + (
        make_option("--daemonize","-d",
            action="store_true",
            dest="daemonize",
            default=False,
            help="daemonize before launching subprocessess"
        ),
        make_option("--pidfile",None,
            action="store",
            dest="pidfile",
            help="store daemon PID in this file"
        ),
        make_option("--logfile",None,
            action="store",
            dest="logfile",
            help="write logging output to this file"
        ),
        make_option("--project-dir",None,
            action="store",
            dest="project_dir",
            help="the root directory for the django project"
                 " (by default this is guessed from the location"
                 " of manage.py)"
        ),
        make_option("--config-file",None,
            action="store",
            dest="config_file",
            help="the supervisord configuration file to load"
                 " (by default this is <project-dir>/supervisord.conf)"
        ),
        make_option("--launch","-l",
            metavar="PROG",
            action="append",
            dest="launch",
            help="launch program automatically at supervisor startup"
        ),
        make_option("--nolaunch","-n",
            metavar="PROG",
            action="append",
            dest="nolaunch",
            help="don't launch program automatically at supervisor startup"
        ),
        make_option("--exclude","-x",
            metavar="PROG",
            action="append",
            dest="exclude",
            help="exclude program from supervisor config"
        ),
        make_option("--include","-i",
            metavar="PROG",
            action="append",
            dest="include",
            help="don't exclude program from supervisor config"
        ),
        make_option("--autoreload","-r",
            metavar="PROG",
            action="append",
            dest="autoreload",
            help="restart program automatically when code files change"
                 " (debug mode only;"
                 " if not set then all programs are autoreloaded)"
        ),
        make_option("--noreload",
            action="store_true",
            dest="noreload",
            help="don't restart processes when code files change"
        ),
    )

    def run_from_argv(self,argv):
        #  Customize option handling so that it doesn't choke on any
        #  options that are being passed straight on to supervisorctl.
        #  Basically, we insert "--" before the supervisorctl command.
        #
        #  For example, automatically turn this:
        #      manage.py supervisor -l celeryd tail -f celeryd
        #  Into this:
        #      manage.py supervisor -l celeryd -- tail -f celeryd
        #
        i = 2
        while i < len(argv):
            arg = argv[i]
            if arg == "--":
                break
            elif arg.startswith("--"):
                i += 1
            elif arg.startswith("-"):
                i += 2
            else:
                argv = argv[:i] + ["--"] + argv[i:]
                break
        return super(Command,self).run_from_argv(argv)

    def handle(self, *args, **options):
        #  We basically just construct the merged supervisord.conf file
        #  and forward it on to either supervisord or supervisorctl.
        #  Due to some very nice engineering on behalf of supervisord authors,
        #  you can pass it a StringIO instance for the "-c" command-line
        #  option.  Saves us having to write the config to a tempfile.
        cfg_file = OnDemandStringIO(get_merged_config, **options)
        #  With no arguments, we launch the processes under supervisord.
        if not args:
            return supervisord.main(("-c",cfg_file))
        #  With arguments, the first arg specifies the sub-command
        #  Some commands we implement ourself with _handle_<command>.
        #  The rest we just pass on to supervisorctl.
        if not args[0].isalnum():
            raise ValueError("Unknown supervisor command: %s" % (args[0],))
        methname = "_handle_%s" % (args[0],)
        try:
            method = getattr(self,methname)
        except AttributeError:
            return supervisorctl.main(("-c",cfg_file) + args)
        else:
            return method(cfg_file,*args[1:],**options)

    #
    #  The following methods implement custom sub-commands.
    #

    def _handle_shell(self,cfg_file,*args,**options):
        """Command 'supervisord shell' runs the interactive command shell."""
        args = ("--interactive",) + args
        return supervisorctl.main(("-c",cfg_file) + args)

    def _handle_getconfig(self,cfg_file,*args,**options):
        """Command 'supervisor getconfig' prints merged config to stdout."""
        if args:
            raise CommandError("supervisor getconfig takes no arguments")
        print cfg_file.read()
        return 0

    def _handle_autoreload(self,cfg_file,*args,**options):
        """Command 'supervisor autoreload' watches for code changes.

        This command provides a simulation of the Django dev server's
        auto-reloading mechanism that will restart all supervised processes.

        It's not quite as accurate as Django's autoreloader because it runs
        in a separate process, so it doesn't know the precise set of modules
        that have been loaded. Instead, it tries to watch all python files
        that are "nearby" the files loaded at startup by Django.
        """
        if args:
            raise CommandError("supervisor autoreload takes no arguments")
        live_dirs = self._find_live_code_dirs()
        reload_progs = self._get_autoreload_programs(cfg_file)

        def autoreloader():
            """
            Forks a subprocess to make the restart call.
            Otherwise supervisord might kill us and cancel the restart!
            """
            if os.fork() == 0:
                sys.exit(self.handle("restart", *reload_progs, **options))

        # Call the autoreloader callback whenever a .py file changes.
        # To prevent thrashing, limit callbacks to one per second.
        handler = CallbackModifiedHandler(callback=autoreloader,
                                          repeat_delay=1,
                                          patterns=AUTORELOAD_PATTERNS,
                                          ignore_patterns=AUTORELOAD_IGNORE,
                                          ignore_directories=True)

        # Try to add watches using the platform-specific observer.
        # If this fails, print a warning and fall back to the PollingObserver.
        # This will avoid errors with e.g. too many inotify watches.
        from watchdog.observers import Observer
        from watchdog.observers.polling import PollingObserver
        
        observer = None
        for ObserverCls in (Observer, PollingObserver):
            observer = ObserverCls()
            try:
                for live_dir in set(live_dirs):
                    observer.schedule(handler, live_dir, True)
                break
            except Exception:
                print>>sys.stderr, "COULD NOT WATCH FILESYSTEM USING"
                print>>sys.stderr, "OBSERVER CLASS: ", ObserverCls
                traceback.print_exc()
                observer.start()
                observer.stop()

        # Fail out if none of the observers worked.
        if observer is None:
            print>>sys.stderr, "COULD NOT WATCH FILESYSTEM"
            return 1

        # Poll if we have an observer.
        # TODO: Is this sleep necessary?  Or will it suffice
        # to block indefinitely on something and wait to be killed?
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
        return 0

    def _get_autoreload_programs(self,cfg_file):
        """Get the set of programs to auto-reload when code changes.

        Such programs will have autoreload=true in their config section.
        This can be affected by config file sections or command-line
        arguments, so we need to read it out of the merged config.
        """
        cfg = RawConfigParser()
        cfg.readfp(cfg_file)
        reload_progs = []
        for section in cfg.sections():
            if section.startswith("program:"):
                try:
                    if cfg.getboolean(section,"autoreload"):
                        reload_progs.append(section.split(":",1)[1])
                except NoOptionError:
                    pass
        return reload_progs

    def _find_live_code_dirs(self):
        """Find all directories in which we might have live python code.

        This walks all of the currently-imported modules and adds their
        containing directory to the list of live dirs.  After normalization
        and de-duplication, we get a pretty good approximation of the
        directories on sys.path that are actively in use.
        """
        live_dirs = []
        for mod in sys.modules.values():
            #  Get the directory containing that module.
            #  This is deliberately casting a wide net.
            try:
                dirnm = os.path.dirname(mod.__file__)
            except AttributeError:
                continue
            #  Normalize it for comparison purposes.
            dirnm = os.path.realpath(os.path.abspath(dirnm))
            if not dirnm.endswith(os.sep):
                dirnm += os.sep
            #  Check that it's not an egg or some other wierdness
            if not os.path.isdir(dirnm):
                continue
            #  If it's a subdir of one we've already found, ignore it.
            for dirnm2 in live_dirs:
                if dirnm.startswith(dirnm2):
                    break
            else:
                #  Remove any ones we've found that are subdirs of it.
                live_dirs = [dirnm2 for dirnm2 in live_dirs\
                                    if not dirnm2.startswith(dirnm)]
                live_dirs.append(dirnm)
        return live_dirs


class OnDemandStringIO(object):
    """StringIO standin that demand-loads its contents and resets on EOF.

    This class is a little bit of a hack to make supervisord reloading work
    correctly.  It provides the readlines() method expected by supervisord's
    config reader, but it resets itself after indicating end-of-file.  If
    the supervisord process then SIGHUPs and tries to read the config again,
    it will be re-created and available for updates.
    """

    def __init__(self, callback, *args, **kwds):
        self._fp = None
        self.callback = callback
        self.args = args
        self.kwds = kwds

    @property
    def fp(self):
        if self._fp is None:
            self._fp = StringIO(self.callback(*self.args, **self.kwds))
        return self._fp

    def read(self, *args, **kwds):
        data = self.fp.read(*args, **kwds)
        if not data:
            self._fp = None
        return data

    def readline(self, *args, **kwds):
        line = self.fp.readline(*args, **kwds)
        if not line:
            self._fp = None
        return line

########NEW FILE########
__FILENAME__ = models
"""

djsupervisor.models:  fake models file for djsupervisor
-------------------------------------------------------

This application doesn't actually define any models.  But Django will freak out
if it's missing a "models.py file, so here we are...

"""


########NEW FILE########
__FILENAME__ = djsupervisor_tags
"""

djsupervisor.templatetags.djsupervisor_tags:  custom template tags
------------------------------------------------------------------

This module defines a custom template filter "templated" which can be used
to apply the djsupervisor templating logic to other config files in your
project.
"""

import os
import shutil

from django import template
register = template.Library()

import djsupervisor.config

current_context = None

@register.filter
def templated(template_path):
    # Interpret paths relative to the project directory.
    project_dir = current_context["PROJECT_DIR"]
    full_path = os.path.join(project_dir, template_path)
    templated_path = full_path + ".templated"
    # If the target file doesn't exist, we will copy over source file metadata.
    # Do so *after* writing the file, as the changed permissions might e.g.
    # affect our ability to write to it.
    created = not os.path.exists(templated_path)
    # Read and process the source file.
    with open(full_path, "r") as f:
        templated = djsupervisor.config.render_config(f.read(), current_context)
    # Write it out to the corresponding .templated file.
    with open(templated_path, "w") as f:
        f.write(templated)
    # Copy metadata if necessary.
    if created:
        try:
            info = os.stat(full_path)
            shutil.copystat(full_path, templated_path)
            os.chown(templated_path, info.st_uid, info.st_gid)
        except EnvironmentError:
            pass
    return templated_path

########NEW FILE########
__FILENAME__ = tests
"""

djsupervisor.tests:  testcases for djsupervisor
-----------------------------------------------

These are just some simple tests for the moment, more to come...

"""

import os
import sys
import difflib
import unittest

import djsupervisor


class TestDJSupervisorDocs(unittest.TestCase):

    def test_readme_matches_docstring(self):
        """Ensure that the README is in sync with the docstring.

        This test should always pass; if the README is out of sync it just
        updates it with the contents of djsupervisor.__doc__.
        """
        dirname = os.path.dirname
        readme = os.path.join(dirname(dirname(__file__)),"README.rst")
        if not os.path.isfile(readme):
            f = open(readme,"wb")
            f.write(djsupervisor.__doc__.encode())
            f.close()
        else:
            f = open(readme,"rb")
            if f.read() != djsupervisor.__doc__:
                f.close()
                f = open(readme,"wb")
                f.write(djsupervisor.__doc__.encode())
                f.close()



########NEW FILE########
