__FILENAME__ = argv
# coding: utf-8

def argv(*args, **opts):
    """
    Produces an argument vector from its array of arguments and keyword
    options. First, the options are unpacked. When the value is a ``bool``,
    the option is passed without an argument if it is true and skipped if it
    is ``false``. When the option is one of the flat built-in types -- a
    ``string`` or ``unicode`` or ``bytes`` or an ``int`` or a ``long`` or a
    ``float`` -- it is passed literally. If the value is a subclass of
    ``dict``, ``.items()`` is called on it the option is passed multiple times
    for key-value pair, with the key and value joined by an ``=``. Otherwise,
    if the value is iterable, the option is passed once for each element, and
    each element is treated like an atomic type. Underscores in the names of
    options are turned in to dashes. If the name of an option is a single
    letter, only a single dash is used when passing it. If an option is passed
    with the key ``__`` and value ``True``, it is put at the end of the
    argument list. The arguments are appended to the end of the argument list,
    each on treated as an atomic type.

    >>> argv.argv(1, 2, 'a', u'ü', dev='/dev/cba', v=True, y=[3,2])
    ['-y', '3', '-y', '2', '--dev', '/dev/cba', '-v', '1', '2', 'a', u'\xfc']

    """
    spacer = ["--"] if opts.get("__") else []
    args   = [ arg(_) for _ in args ]
    opts   = [ _ for k, v in opts.items() for _ in opt(k, v) ]
    return opts + spacer + args

def arg(v):
    if type(v) in strings: return v
    if type(v) in nums: return str(v)
    raise TypeError("Type %s is not a simple, flat type" % type(v))

def opt(k, v):
    k = arg(k).replace("_", "-")
    if k == "--":
        return []
    k = ("--" if len(k) > 1 else "-") + k
    if type(v) is bool:
        return [k] if v else []
    if type(v) in simple:
        return [k, arg(v)]
    if isinstance(v, dict):
        v = [ "%s=%s" % (arg(kk), arg(vv)) for kk, vv in v.items() ]
    return [ _ for element in v for _ in [k, arg(element)] ]

nums    = set([int, long, float])
strings = set([str, unicode, bytes])
simple  = strings | nums


########NEW FILE########
__FILENAME__ = cgroups
import logging

from deimos.logger import log
from deimos._struct import _Struct


class CGroups(_Struct):
    "Holder for a container's cgroups hierarchy."
    def __init__(self, **cgroups_path_mapping):
        properties = {}
        for k, v in cgroups_path_mapping.items():
            properties[k] = construct(v, k)
        _Struct.__init__(self, **properties)
        log.debug(" ".join(self.keys()))

class CGroup(object):
    "A generic CGroup, allowing lookup of CGroup values as Python attributes."
    def __init__(self, path, name):
        self.path = path
        self.name = name
    def __getattr__(self, key):
        path = self.path + "/" + self.name + "." + key
        try:
            with open(path) as h:
                data = h.read()
            return data
        except OSError as e:
            if e.errno != errno.ENOENT: raise e
            log.warning("Could not read %s.%s (%s)", self.name, key, path)
            return None
    def stat_data(self):
        return StatFile(self.stat)

def construct(path, name=None):
    "Selects an appropriate CGroup subclass for the given CGroup path."
    name = name if name else path.split("/")[4]
    classes = { "memory"  : Memory,
                "cpu"     : CPU,
                "cpuacct" : CPUAcct }
    constructor = classes.get(name, CGroup)
    log.debug("Chose %s for: %s", constructor.__name__, path)
    return constructor(path, name)

class Memory(CGroup):
    def rss(self):
        return int(self.stat_data().rss)
    def limit(self):
        return int(self.limit_in_bytes)

class CPU(CGroup):
    def limit(self):
        return float(self.shares) / 1024
        # The scale factor must be the same as for the Docker module. This
        # scale factor is the same as the Docker tools use by default. When a
        # task is started without any explicit CPU limit, the limit that shows
        # up in CGroups is 1024.

class CPUAcct(CGroup):
    def user_time(self):
        "Total user time for container in seconds."
        return float(self.stat_data().user) / 100
    def system_time(self):
        "Total system time for container in seconds."
        return float(self.stat_data().system) / 100

class StatFile(_Struct):
    def __init__(self, data):
        kvs = [ line.strip().split(" ") for line in data.strip().split("\n") ]
        res = {}
        for kvs in kvs:
            if len(kvs) != 2: continue  # Silently skip lines that aren't pairs
            k, v = kvs
            res[k] = v
        _Struct.__init__(self, **res)


########NEW FILE########
__FILENAME__ = cleanup
from fcntl import LOCK_EX, LOCK_NB
import glob
import os
import subprocess
import time

from deimos.cmd import Run
import deimos.flock
from deimos.logger import log
from deimos.timestamp import iso
from deimos._struct import _Struct


class Cleanup(_Struct):
    def __init__(self, root="/tmp/deimos", optimistic=False):
        _Struct.__init__(self, root=root,
                               optimistic=optimistic,
                               lock=os.path.join(root, "cleanup"))
    def dirs(self, before=time.time(), exited=True):
        """
        Provider a generator of container state directories.

        If exited is None, all are returned. If it is False, unexited
        containers are returned. If it is True, only exited containers are
        returned.
        """
        timestamp = iso(before)
        root = os.path.join(self.root, "start-time")
        os.chdir(root)
        by_t = ( d for d in glob.iglob("????-??-??T*.*Z") if d < timestamp )
        if exited is None:
            def predicate(directory):
                return True
        else:
            def predicate(directory):
                exit = os.path.join(directory, "exit")
                return os.path.exists(exit) is exited
        return ( os.path.join(root, d) for d in by_t if predicate(d) )
    def remove(self, *args, **kwargs):
        errors = 0
        lk = deimos.flock.LK(self.lock, LOCK_EX|LOCK_NB) 
        try:
            lk.lock()
        except deimos.flock.Err:
            msg = "Lock unavailable -- is cleanup already running?"
            if self.optimistic:
                log.info(msg)
                return 0
            else:
                log.error(msg)
                raise e
        try:
            for d in self.dirs(*args, **kwargs):
                state = deimos.state.state(d)
                if state is None:
                    log.warning("Not able to load state from: %s", d)
                    continue
                try:
                    cmd  = ["rm", "-rf", d + "/"]
                    cmd += [state._mesos()]
                    if state.cid() is not None:
                        cmd += [state._docker()]
                    Run()(cmd)
                except subprocess.CalledProcessError:
                    errors += 1
        finally:
            lk.unlock()
        if errors != 0:
            log.error("There were failures on %d directories", errors)
            return 4


########NEW FILE########
__FILENAME__ = cmd
import logging
import os
import pipes
import subprocess
import sys

import deimos.logger
from deimos.err import *
from deimos._struct import _Struct


class Run(_Struct):
    def __init__(self, log=None, data=False, in_sh=True,
                       close_stdin=True, log_stderr=True,
                       start_level=logging.DEBUG,
                       success_level=logging.DEBUG,
                       error_level=logging.WARNING):
        _Struct.__init__(self, log   = log if log else deimos.logger.logger(2),
                               data  = data,
                               in_sh = in_sh,
                               close_stdin   = close_stdin,
                               log_stderr    = log_stderr,
                               start_level   = start_level,
                               success_level = success_level,
                               error_level   = error_level)
    def __call__(self, argv, *args, **opts):
        out, err = None, None
        if "stdout" not in opts:
            opts["stdout"] = subprocess.PIPE if self.data else None
        if "stderr" not in opts:
            opts["stderr"] = subprocess.PIPE if self.log_stderr else None
        try:
            self.log.log(self.start_level, present(argv))
            argv_  = in_sh(argv, not self.data) if self.in_sh else argv
            with open(os.devnull) as devnull:
                if self.close_stdin and "stdin" not in opts:
                    opts["stdin"] = devnull
                p = subprocess.Popen(argv_, *args, **opts)
                out, err = p.communicate()
                code = p.wait()
            if code == 0:
                self.log.log(self.success_level, present(argv, 0))
                if out is not None:
                    self.log.log(self.success_level, "STDOUT // " + out)
                return out
        except subprocess.CalledProcessError as e:
            code = e.returncode
        self.log.log(self.error_level, present(argv, code))
        if err is not None:
            self.log.log(self.error_level, "STDERR // " + err)
        raise subprocess.CalledProcessError(code, argv)

def present(argv, exit=None):
    if exit is not None:
        return "exit %d // %s" % (exit, escape(argv))
    else:
        return "call // %s" % escape(argv)

def escape(argv):
    # NB: The pipes.quote() function is deprecated in Python 3
    return " ".join(pipes.quote(_) for _ in argv)

def in_sh(argv, allstderr=True):
    """
    Provides better error messages in case of file not found or permission
    denied. Note that this has nothing at all to do with shell=True, since
    quoting prevents the shell from interpreting any arguments -- they are
    passed straight on to shell exec.
    """
    # NB: The use of single and double quotes in constructing the call really
    #     matters.
    call = 'exec "$@" >&2' if allstderr else 'exec "$@"'
    return ["/bin/sh", "-c", call, "sh"] + argv


########NEW FILE########
__FILENAME__ = config
from ConfigParser import SafeConfigParser, NoSectionError
import json
import logging
import os
import sys

import deimos.argv
import deimos.docker
from deimos.logger import log
import deimos.logger
from deimos._struct import _Struct


def load_configuration(f=None, interactive=sys.stdout.isatty()):
    error = None
    defaults = _Struct(docker     = Docker(),
                       index      = DockerIndex(),
                       containers = Containers(),
                       uris       = URIs(),
                       state      = State(),
                       log        = Log(
                         console  = logging.DEBUG if interactive     else None,
                         syslog   = logging.INFO  if not interactive else None
                       ))
    parsed = None
    try:
        f = f if f else path()
        if f:
            parsed = parse(f)
    except Exception as e:
        error = e
    finally:
        confs = defaults.merge(parsed) if parsed else defaults
        deimos.logger.initialize(**dict(confs.log.items()))
        if error:
            log.exception((("Error loading %s: " % f) if f else "")+str(error))
            sys.exit(16)
        if parsed:
            log.info("Loaded configuration from %s" % f)
            for _, conf in parsed.items():
                log.debug("Found: %r", conf)
    return confs

def coercearray(array):
    if type(array) in deimos.argv.strings:
        if array[0:1] != "[":
            return [array]
        try:
            arr = json.loads(array)
            if type(arr) is not list:
                raise ValueError()
            return arr
        except:
            raise ValueError("Not an array: %s" % array)
    return list(array)

def coerceloglevel(level):
    if not level:
        return
    if type(level) is int:
        return level
    levels = { "DEBUG"    : logging.DEBUG,
               "INFO"     : logging.INFO,
               "WARNING"  : logging.WARNING,
               "ERROR"    : logging.ERROR,
               "CRITICAL" : logging.CRITICAL,
               "NOTSET"   : logging.NOTSET }
    try:
        return levels[level]
    except:
        raise ValueError("Not a log level: %s" % level)

def coercebool(b):
    if type(b) is bool:
        return b
    try:
        bl = json.loads(b)
        if type(bl) is not bool:
            raise ValueError()
        return bl
    except:
        raise ValueError("Not a bool: %s" % b)

def coerceoption(val):
    try:
        return coercearray(val)
    except:
        return coercebool(val)


class Image(_Struct):
    def __init__(self, default=None, ignore=False):
        _Struct.__init__(self, default=default, ignore=coercebool(ignore))
    def override(self, image=None):
        return image if (image and not self.ignore) else self.default

class Options(_Struct):
    def __init__(self, default=[], append=[], ignore=False):
        _Struct.__init__(self, default=coercearray(default),
                               append=coercearray(append),
                               ignore=coercebool(ignore))
    def override(self, options=[]):
        a = options if (len(options) > 0 and not self.ignore) else self.default
        return a + self.append

class Containers(_Struct):
    def __init__(self, image=Image(), options=Options()):
        _Struct.__init__(self, image=image, options=options)
    def override(self, image=None, options=[]):
        return self.image.override(image), self.options.override(options)

class URIs(_Struct):
    def __init__(self, unpack=True):
        _Struct.__init__(self, unpack=coercebool(unpack))

class Log(_Struct):
    def __init__(self, console=None, syslog=None):
        _Struct.__init__(self, console=coerceloglevel(console),
                               syslog=coerceloglevel(syslog))

class Docker(_Struct):
    def __init__(self, **properties):
        for k in properties.keys():
            properties[k] = coerceoption(properties[k])
        _Struct.__init__(self, **properties)
    def argv(self):
        return deimos.argv.argv(**dict(self.items()))

class DockerIndex(_Struct):
    def __init__(self, index=None, account_libmesos="libmesos", account=None):
        _Struct.__init__(self, index=index,
                               account_libmesos=account_libmesos,
                               account=account)

class State(_Struct):
    def __init__(self, root="/tmp/deimos"):
        if ":" in root:
            raise ValueError("Deimos root storage path must not contain ':'")
        _Struct.__init__(self, root=root)


def parse(f):
    config = SafeConfigParser()
    config.read(f)
    parsed = {}
    sections = [("log", Log), ("state", State), ("uris", URIs),
                ("docker",             Docker),
                ("docker.index",       DockerIndex),
                ("containers.image",   Image),
                ("containers.options", Options)]
    for key, cls in sections:
        try:
            parsed[key] = cls(**dict(config.items(key)))
        except:
            continue
    containers = {}
    if "containers.image" in parsed:
        containers["image"] = parsed["containers.image"]
        del parsed["containers.image"]
    if "containers.options" in parsed:
        containers["options"] = parsed["containers.options"]
        del parsed["containers.options"]
    if len(containers) > 0:
        parsed["containers"] = Containers(**containers)
    return _Struct(**parsed)

def path():
    for p in search_path:
        if os.path.exists(p):
            return p

search_path = ["./deimos.cfg",
               os.path.expanduser("~/.deimos"),
               "/etc/deimos.cfg",
               "/usr/etc/deimos.cfg",
               "/usr/local/etc/deimos.cfg"]


########NEW FILE########
__FILENAME__ = containerizer
import base64
import errno
from fcntl import LOCK_EX, LOCK_NB, LOCK_SH, LOCK_UN
import inspect
import logging
import os
import random
import re
import signal
import subprocess
import sys
import time

import google.protobuf

try:    import mesos_pb2 as protos                 # Prefer system installation
except: import deimos.mesos_pb2 as protos

import deimos.cgroups
from deimos.cmd import Run
import deimos.config
import deimos.containerizer
import deimos.docker
from deimos.err import Err
import deimos.logger
from deimos.logger import log
import deimos.path
from deimos._struct import _Struct
import deimos.state
import deimos.sig


class Containerizer(object):
    def __init__(self): pass
    def launch(self, container_id, *args): pass
    def update(self, container_id, *args): pass
    def usage(self, container_id, *args): pass
    def wait(self, container_id, *args): pass
    def destroy(self, container_id, *args): pass
    def __call__(self, *args):
        try:
            name   = args[0]
            method = { "launch"  : self.launch,
                       "update"  : self.update,
                       "usage"   : self.usage,
                       "wait"    : self.wait,
                       "destroy" : self.destroy }[name]
        except IndexError:
            raise Err("Please choose a subcommand")
        except KeyError:
            raise Err("Subcommand %s is not valid for containerizers" % name)
        return method(*args[1:])

def methods():
    "Names of operations provided by containerizers, as a set."
    pairs = inspect.getmembers(Containerizer, predicate=inspect.ismethod)
    return set( k for k, _ in pairs if k[0:1] != "_" )

class Docker(Containerizer, _Struct):
    def __init__(self, workdir="/tmp/mesos-sandbox",
                       state_root="/tmp/deimos",
                       shared_dir="fs",
                       optimistic_unpack=True,
                       container_settings=deimos.config.Containers(),
                       index_settings=deimos.config.DockerIndex()):
        _Struct.__init__(self, workdir=workdir,
                               state_root=state_root,
                               shared_dir=shared_dir,
                               optimistic_unpack=optimistic_unpack,
                               container_settings=container_settings,
                               index_settings=index_settings,
                               runner=None,
                               state=None)
    def launch(self, container_id, *args):
        log.info(" ".join([container_id] + list(args)))
        deimos.sig.install(self.sig_proxy)
        run_options = []
        state = deimos.state.State(self.state_root, mesos_id=container_id)
        state.push()
        lk_l = state.lock("launch", LOCK_EX)
        mesos_directory()
        task = protos.TaskInfo()
        task.ParseFromString(sys.stdin.read())
        for line in proto_lines(task):
            log.debug(line)
        state.executor_id = executor_id(task)
        state.push()
        state.ids()
        url, options = self.container_settings.override(*container(task))
        pre, image = re.split(r"^docker:///?", url)
        if pre != "":
            raise Err("URL '%s' is not a valid docker:// URL!" % url)
        if image == "":
            image = self.default_image(task)
        log.info("image  = %s", image)
        run_options += [ "--sig-proxy" ]
        run_options += [ "--rm" ]     # This is how we ensure container cleanup
        run_options += [ "--cidfile", state.resolve("cid") ]

        place_uris(task, self.shared_dir, self.optimistic_unpack)
        run_options += [ "-w", self.workdir ]

        # Docker requires an absolute path to a source filesystem, separated
        # from the bind path in the container with a colon, but the absolute
        # path to the Mesos sandbox might have colons in it (TaskIDs with
        # timestamps can cause this situation). So we create a soft link to it
        # and mount that.
        shared_full = os.path.abspath(self.shared_dir)
        sandbox_symlink = state.sandbox_symlink(shared_full)
        run_options += [ "-v", "%s:%s" % (sandbox_symlink, self.workdir) ]

        cpus, mems = cpu_and_mem(task)
        env = [(_.name, _.value) for _ in task.command.environment.variables]
        run_options += options

        # We need to wrap the call to Docker in a call to the Mesos executor
        # if no executor is passed as part of the task. We need to pass the
        # MESOS_* environment variables in to the container if we're going to
        # start an executor.
        observer_argv = None
        if needs_executor_wrapper(task):
            options = ["--mesos-executor", "--observer"]
            if not(len(args) > 1 and args[0] in options):
                raise Err("Task %s needs --observer to be set!" % state.eid())
            observer_argv = list(args[1:]) + [ deimos.path.me(),
                                               "wait", "--docker" ]
        else:
            env += mesos_env() + [("MESOS_DIRECTORY", self.workdir)]

        runner_argv = deimos.docker.run(run_options, image, argv(task),
                                        env=env, ports=ports(task),
                                        cpus=cpus, mems=mems)

        log_mesos_env(logging.DEBUG)

        observer = None
        with open("stdout", "w") as o:        # This awkward multi 'with' is a
            with open("stderr", "w") as e:    # concession to 2.6 compatibility
                with open(os.devnull) as devnull:
                    log.info(deimos.cmd.present(runner_argv))
                    self.runner = subprocess.Popen(runner_argv, stdin=devnull,
                                                                stdout=o,
                                                                stderr=e)
                    state.pid(self.runner.pid)
                    state.await_cid()
                    state.push()
                    lk_w = state.lock("wait", LOCK_EX)
                    lk_l.unlock()
                    state.ids()
                    proto_out(protos.ExternalStatus, message="launch: ok")
                    sys.stdout.close()  # Mark STDOUT as closed for Python code
                    os.close(1) # Use low-level call to close OS side of STDOUT
                    if observer_argv is not None:
                        observer_argv += [state.cid()]
                        log.info(deimos.cmd.present(observer_argv))
                        call = deimos.cmd.in_sh(observer_argv, allstderr=False)
                        # TODO: Collect these leaking file handles.
                        obs_out = open(state.resolve("observer.out"), "w+")
                        obs_err = open(state.resolve("observer.err"), "w+")
                        # If the Mesos executor sees LIBPROCESS_PORT=0 (which
                        # is passed by the slave) there are problems when it
                        # attempts to bind. ("Address already in use").
                        # Purging both LIBPROCESS_* net variables, to be safe.
                        for v in ["LIBPROCESS_PORT", "LIBPROCESS_IP"]:
                            if v in os.environ:
                                del os.environ[v]
                        observer = subprocess.Popen(call, stdin=devnull,
                                                          stdout=obs_out,
                                                          stderr=obs_err,
                                                          close_fds=True)
        data = Run(data=True)(deimos.docker.wait(state.cid()))
        state.exit(data)
        lk_w.unlock()
        for p, arr in [(self.runner, runner_argv), (observer, observer_argv)]:
            if p is None or p.wait() == 0:
                continue
            log.warning(deimos.cmd.present(arr, p.wait()))
        return state.exit()
    def usage(self, container_id, *args):
        log.info(" ".join([container_id] + list(args)))
        state = deimos.state.State(self.state_root, mesos_id=container_id)
        state.await_launch()
        state.ids()
        if state.cid() is None:
            log.info("Container not started?")
            return 0
        if state.exit() is not None:
            log.info("Container is stopped")
            return 0
        cg = deimos.cgroups.CGroups(**deimos.docker.cgroups(state.cid()))
        if len(cg.keys()) == 0:
            log.info("Container has no CGroups...already stopped?")
            return 0
        try:
            proto_out(protos.ResourceStatistics,
                      timestamp             = time.time(),
                      mem_limit_bytes       = cg.memory.limit(),
                      cpus_limit            = cg.cpu.limit(),
                    # cpus_user_time_secs   = cg.cpuacct.user_time(),
                    # cpus_system_time_secs = cg.cpuacct.system_time(),
                      mem_rss_bytes         = cg.memory.rss())
        except AttributeError as e:
            log.error("Missing CGroup!")
            raise e
        return 0
    def wait(self, *args):
        log.info(" ".join(list(args)))
        if list(args[0:1]) != ["--docker"]:
            return      # We rely on the Mesos default wait strategy in general
        # In Docker mode, we use Docker wait to wait for the container and
        # then exit with the returned exit code. The passed in ID should be a
        # Docker CID, not a Mesos container ID.
        state = deimos.state.State(self.state_root, docker_id=args[1])
        self.state = state
        deimos.sig.install(self.stop_docker_and_resume)
        state.await_launch()
        try:
            state.lock("wait", LOCK_SH, seconds=None)
        except IOError as e:                       # Allows for signal recovery
            if e.errno != errno.EINTR:
                raise e
            state.lock("wait", LOCK_SH, 1)
        if state.exit() is not None:
            return state.exit()
        raise Err("Wait lock is not held nor is exit file present")
    def destroy(self, container_id, *args):
        log.info(" ".join([container_id] + list(args)))
        state = deimos.state.State(self.state_root, mesos_id=container_id)
        state.await_launch()
        lk_d = state.lock("destroy", LOCK_EX)
        if state.exit() is not None:
            Run()(deimos.docker.stop(state.cid()))
        else:
            log.info("Container is stopped")
        if not sys.stdout.closed:
            # If we're called as part of the signal handler set up by launch,
            # STDOUT is probably closed already. Writing the Protobuf would
            # only result in a bevy of error messages.
            proto_out(protos.ExternalStatus, message="destroy: ok")
        return 0
    def sig_proxy(self, signum):
        if self.runner is not None:
            self.runner.send_signal(signum)
    def stop_docker_and_resume(self, signum):
        if self.state is not None and self.state.cid() is not None:
            cid = self.state.cid()
            log.info("Trying to stop Docker container: %s", cid)
            try:
                Run()(deimos.docker.stop(cid))
            except subprocess.CalledProcessError:
                pass
            return deimos.sig.Resume()
    def default_image(self, task):
        opts = dict(self.index_settings.items(onlyset=True))
        if "account_libmesos" in opts:
            if not needs_executor_wrapper(task):
                opts["account"] = opts["account_libmesos"]
            del opts["account_libmesos"]
        return deimos.docker.matching_image_for_host(**opts)

####################################################### Mesos interface helpers

def fetch_command(task):
    if task.HasField("executor"):
        return task.executor.command
    return task.command

def fetch_container(task):
    cmd = fetch_command(task)
    if cmd.HasField("container"):
        return cmd.container

def container(task):
    container = fetch_container(task)
    if container is not None:
        return container.image, list(container.options)
    return "docker:///", []

def argv(task):
    cmd = fetch_command(task)
    if cmd.HasField("value") and cmd.value != "":
        return ["sh", "-c", cmd.value]
    return []

def uris(task):
    return fetch_command(task).uris

def executor_id(task):
    if needs_executor_wrapper(task):
        return task.task_id.value
    else:
        return task.executor.executor_id.value

def ports(task):
    resources = [ _.ranges.range for _ in task.resources if _.name == 'ports' ]
    ranges = [ _ for __ in resources for _ in __ ]
    # NB: Casting long() to int() so there's no trailing 'L' in later
    #     stringifications. Ports should only ever be shorts, anyways.
    ports = [ range(int(_.begin), int(_.end)+1) for _ in ranges ]
    return [ port for r in ports for port in r ]

def cpu_and_mem(task):
    cpu, mem = None, None
    for r in task.resources:
        if r.name == "cpus":
            cpu = str(int(r.scalar.value * 1024))
        if r.name == "mem":
            mem = str(int(r.scalar.value)) + "m"
    return (cpu, mem)

def needs_executor_wrapper(task):
    return not task.HasField("executor")

MESOS_ESSENTIAL_ENV = [ "MESOS_SLAVE_ID",     "MESOS_SLAVE_PID",
                        "MESOS_FRAMEWORK_ID", "MESOS_EXECUTOR_ID" ]

def mesos_env():
    env = os.environ.get
    return [ (k, env(k)) for k in MESOS_ESSENTIAL_ENV if env(k) ]

def log_mesos_env(level=logging.INFO):
    for k, v in os.environ.items():
        if k.startswith("MESOS_") or k.startswith("LIBPROCESS_"):
            log.log(level, "%s=%s" % (k, v))

def mesos_directory():
    if not "MESOS_DIRECTORY" in os.environ: return
    work_dir = os.path.abspath(os.getcwd())
    task_dir = os.path.abspath(os.environ["MESOS_DIRECTORY"])
    if task_dir != work_dir:
        log.info("Changing directory to MESOS_DIRECTORY=%s", task_dir)
        os.chdir(task_dir)

def place_uris(task, directory, optimistic_unpack=False):
    cmd = deimos.cmd.Run()
    cmd(["mkdir", "-p", directory])
    for item in uris(task):
        uri = item.value
        gen_unpack_cmd = unpacker(uri) if optimistic_unpack else None
        log.info("Retrieving URI: %s", deimos.cmd.escape([uri]))
        try:
            basename = uri.split("/")[-1]
            f = os.path.join(directory, basename)
            if basename == "":
                raise IndexError
        except IndexError:
            log.info("Not able to determine basename: %r", uri)
            continue
        try:
            cmd(["curl", "-sSfL", uri, "--output", f])
        except subprocess.CalledProcessError as e:
            log.warning("Failed while processing URI: %s",
                        deimos.cmd.escape(uri))
            continue
        if item.executable:
            os.chmod(f, 0755)
        if gen_unpack_cmd is not None:
            log.info("Unpacking %s" % f)
            cmd(gen_unpack_cmd(f, directory))
            cmd(["rm", "-f", f])

def unpacker(uri):
    if re.search(r"[.](t|tar[.])(bz2|xz|gz)$", uri):
        return lambda f, directory: ["tar", "-C", directory, "-xf", f]
    if re.search(r"[.]zip$", uri):
        return lambda f, directory: ["unzip", "-d", directory, f]


####################################################### IO & system interaction

def proto_out(cls, **properties):
    """
    With a Protobuf class and properies as keyword arguments, sets all the
    properties on a new instance of the class and serializes the resulting
    value to stdout.
    """
    obj = cls()
    for k, v in properties.iteritems():
        log.debug("%s.%s = %r", cls.__name__, k, v)
        setattr(obj, k, v)
    data = obj.SerializeToString()
    sys.stdout.write(data)
    sys.stdout.flush()

def proto_lines(proto):
    s = google.protobuf.text_format.MessageToString(proto)
    return s.strip().split("\n")


########NEW FILE########
__FILENAME__ = docker
import glob
import itertools
import json
import logging
import os
import re
import subprocess
import sys
import time

from deimos.cmd import Run
from deimos.err import *
from deimos.logger import log
from deimos._struct import _Struct


def run(options, image, command=[], env={}, cpus=None, mems=None, ports=[]):
    envs  = env.items() if isinstance(env, dict) else env
    pairs = [ ("-e", "%s=%s" % (k, v)) for k, v in envs ]
    if ports != []:               # NB: Forces external call to pre-fetch image
        port_pairings = list(itertools.izip_longest(ports, inner_ports(image)))
        log.info("Port pairings (Mesos, Docker) // %r", port_pairings)
        for allocated, target in port_pairings:
            if allocated is None:
                log.warning("Container exposes more ports than were allocated")
                break
            options += [ "-p", "%d:%d" % (allocated, target or allocated) ]
    argv  = [ "run" ] + options
    argv += [ "-c", str(cpus) ] if cpus else []
    argv += [ "-m", str(mems) ] if mems else []
    argv += [ _ for __ in pairs for _ in __ ]            # This is just flatten
    argv += [ image ] + command
    return docker(*argv)

def stop(ident):
    return docker("stop", "-t=2", ident)

def rm(ident):
    return docker("rm", ident)

def wait(ident):
    return docker("wait", ident)


images = {} ######################################## Cache of image information

def pull(image):
    Run(data=True)(docker("pull", image))
    refresh_docker_image_info(image)

def pull_once(image):
    if image not in images:
        pull(image)

def image_info(image):
    if image in images:
        return images[image]
    else:
        return refresh_docker_image_info(image)

def refresh_docker_image_info(image):
    try:
        text   = Run(data=True)(docker("inspect", image))
        parsed = json.loads(text)[0]
        images[image] = parsed
        return parsed
    except subprocess.CalledProcessError as e:
        return None

def ensure_image(f):
    def f_(image, *args, **kwargs):
        pull_once(image)
        return f(image, *args, **kwargs)
    return f_

@ensure_image
def inner_ports(image):
    info = image_info(image)
    config = info.get("Config", info.get("config"))
    if config:
        exposed = config.get("ExposedPorts", {})
        if exposed and isinstance(exposed, dict):
            return sorted( int(k.split("/")[0]) for k in exposed.keys() )
        specs = config.get("PortSpecs", [])
        if specs and isinstance(specs, list):
            return sorted( int(v.split(":")[-1]) for v in specs )
    return [] # If all else fails...


################################################# System and process interfaces

class Status(_Struct):
    def __init__(self, cid=None, pid=None, exit=None):
        _Struct.__init__(self, cid=cid, pid=pid, exit=exit)

def cgroups(cid):
    paths = []
    paths += glob.glob("/sys/fs/cgroup/*/" + cid)
    paths += glob.glob("/sys/fs/cgroup/*/docker/" + cid)
    return dict( (s.split("/")[4], s) for s in paths )

def matching_image_for_host(distro=None, release=None, *args, **kwargs):
    if distro is None or release is None:
        # TODO: Use redhat-release, &c
        rel_string = Run(data=True)(["bash", "-c", """
            set -o errexit -o nounset -o pipefail
            ( source /etc/os-release && tr A-Z a-z <<<"$ID\t$VERSION_ID" )
        """])
        probed_distro, probed_release = rel_string.strip().split()
        distro, release = (distro or probed_distro, release or probed_release)
    return image_token("%s:%s" % (distro, release), *args, **kwargs)

def image_token(name, account=None, index=None):
    return "/".join(_ for _ in [index, account, name] if _ is not None)

def probe(ident, quiet=False):
    fields = "{{.ID}} {{.State.Pid}} {{.State.ExitCode}}"
    level  = logging.DEBUG if quiet else logging.WARNING
    argv   = docker("inspect", "--format=" + fields, ident)
    run    = Run(data=True, error_level=level)
    text   = run(argv).strip()
    cid, pid, exit = text.split()
    return Status(cid=cid, pid=pid, exit=(exit if pid == 0 else None))

def exists(ident, quiet=False):
    try:
        return probe(ident, quiet)
    except subprocess.CalledProcessError as e:
        if e.returncode != 1:
            raise e
        return None

def await(ident, t=0.05, n=10):
    for _ in range(0, n):
        result = exists(ident, quiet=True)
        if result:
            return result
        time.sleep(t)
    result = exists(ident, quiet=True)
    if result:
        return result
    msg = "Container %s not ready after %d sleeps of %g seconds"
    log.warning(msg % (ident, n, t))
    raise AwaitTimeout("Timed out waiting for %s" % ident)

def read_wait_code(data):
    try:
        code = int(data)
        code = 128 + abs(code) if code < 0 else code
        return code % 256
    except:
        log.error("Result of `docker wait` wasn't an int: %r", data)
        return 111

class AwaitTimeout(Err):
    pass


############################################################### Global settings

options = []

def docker(*args):
    return ["docker"] + options + list(args)


########NEW FILE########
__FILENAME__ = err
class Err(RuntimeError): pass

########NEW FILE########
__FILENAME__ = flock
from contextlib import contextmanager
import errno
import fcntl
import os
import signal
import subprocess
import time

import deimos.err
from deimos.logger import log
from deimos._struct import _Struct


locks = {}

class LK(_Struct):
    default_timeout = 10
    def __new__(cls, path, flags, seconds=default_timeout):
        if os.path.abspath(path) in locks:
            return locks[path]
        else:
            return super(LK, cls).__new__(cls, path, flags, seconds)
    def __init__(self, path, flags, seconds=default_timeout):
        """Construct a lockable file handle. Handles are recycled.

        If seconds is 0, LOCK_NB will be set. If LOCK_NB is set, seconds will
        be set to 0. If seconds is None, there will be no timeout; but flags
        will not be adjusted in any way.
        """
        full = os.path.abspath(path)
        flags, seconds = nb_seconds(flags, seconds)
        if full not in locks:
            _Struct.__init__(self, path=full,
                                   handle=None,
                                   fd=None,
                                   flags=flags,
                                   seconds=seconds)
            locks[self.path] = self
    def lock(self):
        if self.handle is None or self.handle.closed:
            self.handle = open(self.path, "w+")
            self.fd = self.handle.fileno()
        if (self.flags & fcntl.LOCK_NB) != 0 or self.seconds is None:
            try:
                fcntl.flock(self.handle, self.flags)
            except IOError as e:
                if e.errno not in [errno.EACCES, errno.EAGAIN]:
                    raise e
                raise Locked(self.path)
        else:
            with timeout(self.seconds):
                try:
                    fcntl.flock(self.handle, self.flags)
                except IOError as e:
                    if e.errno not in [errno.EINTR, errno.EACCES, errno.EAGAIN]:
                        raise e
                    raise Timeout(self.path)
    def unlock(self):
        if not self.handle.closed:
            fcntl.flock(self.handle, fcntl.LOCK_UN)
            self.handle.close()

def format_lock_flags(flags):
    tokens = [ ("EX", fcntl.LOCK_EX), ("SH", fcntl.LOCK_SH),
               ("UN", fcntl.LOCK_UN), ("NB", fcntl.LOCK_NB) ]
    return "|".join( s for s, flag in tokens if (flags & flag) != 0 )

def nb_seconds(flags, seconds):
    if seconds == 0:
        flags |= fcntl.LOCK_NB
    if (flags & fcntl.LOCK_NB) != 0:
        seconds = 0
    return flags, seconds

class Err(deimos.err.Err): pass
class Timeout(Err): pass
class Locked(Err): pass

def lock_browser(directory):
    bash = """
        set -o errexit -o nounset -o pipefail

        function files_by_inode {
          find "$1" -type f -printf '%i %p\\n' | LC_ALL=C LANG=C sort
        }

        function locking_pids_by_inode { 
          cat /proc/locks |
          sed -r '
            s/^.+ ([^ ]+) +([0-9]+) [^ :]+:[^ :]+:([0-9]+) .+$/\\3 \\2 \\1/
          ' | LC_ALL=C LANG=C sort
        }

        join <(locking_pids_by_inode) <(files_by_inode "$1")
    """
    subprocess.check_call([ "bash", "-c", bash, "bash",
                            os.path.abspath(directory) ])

# Thanks to Glenn Maynard
# http://stackoverflow.com/questions/5255220/fcntl-flock-how-to-implement-a-timeout/5255473#5255473
@contextmanager
def timeout(seconds):
    def timeout_handler(signum, frame):
        pass
    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    try:
        signal.alarm(seconds)
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)


########NEW FILE########
__FILENAME__ = logger
import inspect
import logging
import logging.handlers
import os


root = logging.getLogger("deimos")

class log(): # Really just a namespace
    @staticmethod
    def debug(*args, **opts):     logger(2).debug(*args, **opts)
    @staticmethod
    def info(*args, **opts):      logger(2).info(*args, **opts)
    @staticmethod
    def warning(*args, **opts):   logger(2).warning(*args, **opts)
    @staticmethod
    def error(*args, **opts):     logger(2).error(*args, **opts)
    @staticmethod
    def critical(*args, **opts):  logger(2).critical(*args, **opts)
    @staticmethod
    def exception(*args, **opts): logger(2).exception(*args, **opts)
    @staticmethod
    def log(*args, **opts):       logger(2).log(*args, **opts)

def initialize(console=logging.DEBUG, syslog=logging.INFO):
    global _settings
    global _initialized
    if _initialized: return
    _settings = locals()
    _initialized = True
    root.setLevel(min( level for level in [console, syslog] if level ))
    if console:
        stderr = logging.StreamHandler()
        fmt = "%(asctime)s.%(msecs)03d %(name)s %(message)s"
        stderr.setFormatter(logging.Formatter(fmt=fmt, datefmt="%H:%M:%S"))
        stderr.setLevel(console)
        root.addHandler(stderr)
    if syslog:
        dev = "/dev/log" if os.path.exists("/dev/log") else "/var/run/syslog"
        fmt = "deimos[%(process)d]: %(name)s %(message)s"
        logger = logging.handlers.SysLogHandler(address=dev)
        logger.setFormatter(logging.Formatter(fmt=fmt))
        logger.setLevel(syslog)
        root.addHandler(logger)
    root.removeHandler(_null_handler)

def logger(height=1):                 # http://stackoverflow.com/a/900404/48251
    """
    Obtain a function logger for the calling function. Uses the inspect module
    to find the name of the calling function and its position in the module
    hierarchy. With the optional height argument, logs for caller's caller, and
    so forth.
    """
    caller   = inspect.stack()[height]
    scope    = caller[0].f_globals
    function = caller[3]
    path     = scope["__name__"]
    if path == "__main__" and scope["__package__"]:
        path = scope["__package__"]
    return logging.getLogger(path + "." + function + "()")

_initialized = False

_settings = {}

_null_handler = logging.NullHandler()

root.addHandler(_null_handler)

########NEW FILE########
__FILENAME__ = mesos_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: mesos.proto

from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)




DESCRIPTOR = _descriptor.FileDescriptor(
  name='mesos.proto',
  package='mesos',
  serialized_pb='\n\x0bmesos.proto\x12\x05mesos\"\x1c\n\x0b\x46rameworkID\x12\r\n\x05value\x18\x01 \x02(\t\"\x18\n\x07OfferID\x12\r\n\x05value\x18\x01 \x02(\t\"\x18\n\x07SlaveID\x12\r\n\x05value\x18\x01 \x02(\t\"\x17\n\x06TaskID\x12\r\n\x05value\x18\x01 \x02(\t\"\x1b\n\nExecutorID\x12\r\n\x05value\x18\x01 \x02(\t\"\x1c\n\x0b\x43ontainerID\x12\r\n\x05value\x18\x01 \x02(\t\"\xa6\x01\n\rFrameworkInfo\x12\x0c\n\x04user\x18\x01 \x02(\t\x12\x0c\n\x04name\x18\x02 \x02(\t\x12\x1e\n\x02id\x18\x03 \x01(\x0b\x32\x12.mesos.FrameworkID\x12\x1b\n\x10\x66\x61ilover_timeout\x18\x04 \x01(\x01:\x01\x30\x12\x19\n\ncheckpoint\x18\x05 \x01(\x08:\x05\x66\x61lse\x12\x0f\n\x04role\x18\x06 \x01(\t:\x01*\x12\x10\n\x08hostname\x18\x07 \x01(\t\"\xfb\x01\n\x0b\x43ommandInfo\x12$\n\x04uris\x18\x01 \x03(\x0b\x32\x16.mesos.CommandInfo.URI\x12\'\n\x0b\x65nvironment\x18\x02 \x01(\x0b\x32\x12.mesos.Environment\x12\r\n\x05value\x18\x03 \x02(\t\x12\x33\n\tcontainer\x18\x04 \x01(\x0b\x32 .mesos.CommandInfo.ContainerInfo\x1a(\n\x03URI\x12\r\n\x05value\x18\x01 \x02(\t\x12\x12\n\nexecutable\x18\x02 \x01(\x08\x1a/\n\rContainerInfo\x12\r\n\x05image\x18\x01 \x02(\t\x12\x0f\n\x07options\x18\x02 \x03(\t\"\xd5\x01\n\x0c\x45xecutorInfo\x12&\n\x0b\x65xecutor_id\x18\x01 \x02(\x0b\x32\x11.mesos.ExecutorID\x12(\n\x0c\x66ramework_id\x18\x08 \x01(\x0b\x32\x12.mesos.FrameworkID\x12#\n\x07\x63ommand\x18\x07 \x02(\x0b\x32\x12.mesos.CommandInfo\x12\"\n\tresources\x18\x05 \x03(\x0b\x32\x0f.mesos.Resource\x12\x0c\n\x04name\x18\t \x01(\t\x12\x0e\n\x06source\x18\n \x01(\t\x12\x0c\n\x04\x64\x61ta\x18\x04 \x01(\x0c\"W\n\nMasterInfo\x12\n\n\x02id\x18\x01 \x02(\t\x12\n\n\x02ip\x18\x02 \x02(\r\x12\x12\n\x04port\x18\x03 \x02(\r:\x04\x35\x30\x35\x30\x12\x0b\n\x03pid\x18\x04 \x01(\t\x12\x10\n\x08hostname\x18\x05 \x01(\t\"\xe4\x01\n\tSlaveInfo\x12\x10\n\x08hostname\x18\x01 \x02(\t\x12\x12\n\x04port\x18\x08 \x01(\x05:\x04\x35\x30\x35\x31\x12\"\n\tresources\x18\x03 \x03(\x0b\x32\x0f.mesos.Resource\x12$\n\nattributes\x18\x05 \x03(\x0b\x32\x10.mesos.Attribute\x12\x1a\n\x02id\x18\x06 \x01(\x0b\x32\x0e.mesos.SlaveID\x12\x19\n\ncheckpoint\x18\x07 \x01(\x08:\x05\x66\x61lse\x12\x16\n\x0ewebui_hostname\x18\x02 \x01(\t\x12\x18\n\nwebui_port\x18\x04 \x01(\x05:\x04\x38\x30\x38\x31\"\xfc\x02\n\x05Value\x12\x1f\n\x04type\x18\x01 \x02(\x0e\x32\x11.mesos.Value.Type\x12#\n\x06scalar\x18\x02 \x01(\x0b\x32\x13.mesos.Value.Scalar\x12#\n\x06ranges\x18\x03 \x01(\x0b\x32\x13.mesos.Value.Ranges\x12\x1d\n\x03set\x18\x04 \x01(\x0b\x32\x10.mesos.Value.Set\x12\x1f\n\x04text\x18\x05 \x01(\x0b\x32\x11.mesos.Value.Text\x1a\x17\n\x06Scalar\x12\r\n\x05value\x18\x01 \x02(\x01\x1a#\n\x05Range\x12\r\n\x05\x62\x65gin\x18\x01 \x02(\x04\x12\x0b\n\x03\x65nd\x18\x02 \x02(\x04\x1a+\n\x06Ranges\x12!\n\x05range\x18\x01 \x03(\x0b\x32\x12.mesos.Value.Range\x1a\x13\n\x03Set\x12\x0c\n\x04item\x18\x01 \x03(\t\x1a\x15\n\x04Text\x12\r\n\x05value\x18\x01 \x02(\t\"1\n\x04Type\x12\n\n\x06SCALAR\x10\x00\x12\n\n\x06RANGES\x10\x01\x12\x07\n\x03SET\x10\x02\x12\x08\n\x04TEXT\x10\x03\"\xc4\x01\n\tAttribute\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x1f\n\x04type\x18\x02 \x02(\x0e\x32\x11.mesos.Value.Type\x12#\n\x06scalar\x18\x03 \x01(\x0b\x32\x13.mesos.Value.Scalar\x12#\n\x06ranges\x18\x04 \x01(\x0b\x32\x13.mesos.Value.Ranges\x12\x1d\n\x03set\x18\x06 \x01(\x0b\x32\x10.mesos.Value.Set\x12\x1f\n\x04text\x18\x05 \x01(\x0b\x32\x11.mesos.Value.Text\"\xb3\x01\n\x08Resource\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x1f\n\x04type\x18\x02 \x02(\x0e\x32\x11.mesos.Value.Type\x12#\n\x06scalar\x18\x03 \x01(\x0b\x32\x13.mesos.Value.Scalar\x12#\n\x06ranges\x18\x04 \x01(\x0b\x32\x13.mesos.Value.Ranges\x12\x1d\n\x03set\x18\x05 \x01(\x0b\x32\x10.mesos.Value.Set\x12\x0f\n\x04role\x18\x06 \x01(\t:\x01*\"\xcc\x02\n\x12ResourceStatistics\x12\x11\n\ttimestamp\x18\x01 \x02(\x01\x12\x1b\n\x13\x63pus_user_time_secs\x18\x02 \x01(\x01\x12\x1d\n\x15\x63pus_system_time_secs\x18\x03 \x01(\x01\x12\x12\n\ncpus_limit\x18\x04 \x02(\x01\x12\x17\n\x0f\x63pus_nr_periods\x18\x07 \x01(\r\x12\x19\n\x11\x63pus_nr_throttled\x18\x08 \x01(\r\x12 \n\x18\x63pus_throttled_time_secs\x18\t \x01(\x01\x12\x15\n\rmem_rss_bytes\x18\x05 \x01(\x04\x12\x17\n\x0fmem_limit_bytes\x18\x06 \x01(\x04\x12\x16\n\x0emem_file_bytes\x18\n \x01(\x04\x12\x16\n\x0emem_anon_bytes\x18\x0b \x01(\x04\x12\x1d\n\x15mem_mapped_file_bytes\x18\x0c \x01(\x04\"\xe9\x01\n\rResourceUsage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\x12(\n\x0c\x66ramework_id\x18\x02 \x02(\x0b\x32\x12.mesos.FrameworkID\x12&\n\x0b\x65xecutor_id\x18\x03 \x01(\x0b\x32\x11.mesos.ExecutorID\x12\x15\n\rexecutor_name\x18\x04 \x01(\t\x12\x1e\n\x07task_id\x18\x05 \x01(\x0b\x32\r.mesos.TaskID\x12-\n\nstatistics\x18\x06 \x01(\x0b\x32\x19.mesos.ResourceStatistics\"O\n\x07Request\x12 \n\x08slave_id\x18\x01 \x01(\x0b\x32\x0e.mesos.SlaveID\x12\"\n\tresources\x18\x02 \x03(\x0b\x32\x0f.mesos.Resource\"\xf4\x01\n\x05Offer\x12\x1a\n\x02id\x18\x01 \x02(\x0b\x32\x0e.mesos.OfferID\x12(\n\x0c\x66ramework_id\x18\x02 \x02(\x0b\x32\x12.mesos.FrameworkID\x12 \n\x08slave_id\x18\x03 \x02(\x0b\x32\x0e.mesos.SlaveID\x12\x10\n\x08hostname\x18\x04 \x02(\t\x12\"\n\tresources\x18\x05 \x03(\x0b\x32\x0f.mesos.Resource\x12$\n\nattributes\x18\x07 \x03(\x0b\x32\x10.mesos.Attribute\x12\'\n\x0c\x65xecutor_ids\x18\x06 \x03(\x0b\x32\x11.mesos.ExecutorID\"\xd8\x01\n\x08TaskInfo\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x1e\n\x07task_id\x18\x02 \x02(\x0b\x32\r.mesos.TaskID\x12 \n\x08slave_id\x18\x03 \x02(\x0b\x32\x0e.mesos.SlaveID\x12\"\n\tresources\x18\x04 \x03(\x0b\x32\x0f.mesos.Resource\x12%\n\x08\x65xecutor\x18\x05 \x01(\x0b\x32\x13.mesos.ExecutorInfo\x12#\n\x07\x63ommand\x18\x07 \x01(\x0b\x32\x12.mesos.CommandInfo\x12\x0c\n\x04\x64\x61ta\x18\x06 \x01(\x0c\"\xa1\x01\n\nTaskStatus\x12\x1e\n\x07task_id\x18\x01 \x02(\x0b\x32\r.mesos.TaskID\x12\x1f\n\x05state\x18\x02 \x02(\x0e\x32\x10.mesos.TaskState\x12\x0f\n\x07message\x18\x04 \x01(\t\x12\x0c\n\x04\x64\x61ta\x18\x03 \x01(\x0c\x12 \n\x08slave_id\x18\x05 \x01(\x0b\x32\x0e.mesos.SlaveID\x12\x11\n\ttimestamp\x18\x06 \x01(\x01\"$\n\x07\x46ilters\x12\x19\n\x0erefuse_seconds\x18\x01 \x01(\x01:\x01\x35\"f\n\x0b\x45nvironment\x12.\n\tvariables\x18\x01 \x03(\x0b\x32\x1b.mesos.Environment.Variable\x1a\'\n\x08Variable\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\r\n\x05value\x18\x02 \x02(\t\"\'\n\tParameter\x12\x0b\n\x03key\x18\x01 \x02(\t\x12\r\n\x05value\x18\x02 \x02(\t\"1\n\nParameters\x12#\n\tparameter\x18\x01 \x03(\x0b\x32\x10.mesos.Parameter\"/\n\nCredential\x12\x11\n\tprincipal\x18\x01 \x02(\t\x12\x0e\n\x06secret\x18\x02 \x01(\x0c\"2\n\rResourceArray\x12!\n\x08resource\x18\x01 \x03(\x0b\x32\x0f.mesos.Resource\"F\n\x13\x45xternalTermination\x12\x0e\n\x06status\x18\x01 \x02(\r\x12\x0e\n\x06killed\x18\x02 \x02(\x08\x12\x0f\n\x07message\x18\x03 \x02(\t\"!\n\x0e\x45xternalStatus\x12\x0f\n\x07message\x18\x01 \x02(\t*\\\n\x06Status\x12\x16\n\x12\x44RIVER_NOT_STARTED\x10\x01\x12\x12\n\x0e\x44RIVER_RUNNING\x10\x02\x12\x12\n\x0e\x44RIVER_ABORTED\x10\x03\x12\x12\n\x0e\x44RIVER_STOPPED\x10\x04*\x86\x01\n\tTaskState\x12\x10\n\x0cTASK_STAGING\x10\x06\x12\x11\n\rTASK_STARTING\x10\x00\x12\x10\n\x0cTASK_RUNNING\x10\x01\x12\x11\n\rTASK_FINISHED\x10\x02\x12\x0f\n\x0bTASK_FAILED\x10\x03\x12\x0f\n\x0bTASK_KILLED\x10\x04\x12\r\n\tTASK_LOST\x10\x05\x42\x1a\n\x10org.apache.mesosB\x06Protos')

_STATUS = _descriptor.EnumDescriptor(
  name='Status',
  full_name='mesos.Status',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='DRIVER_NOT_STARTED', index=0, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DRIVER_RUNNING', index=1, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DRIVER_ABORTED', index=2, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DRIVER_STOPPED', index=3, number=4,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=3635,
  serialized_end=3727,
)

Status = enum_type_wrapper.EnumTypeWrapper(_STATUS)
_TASKSTATE = _descriptor.EnumDescriptor(
  name='TaskState',
  full_name='mesos.TaskState',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='TASK_STAGING', index=0, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TASK_STARTING', index=1, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TASK_RUNNING', index=2, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TASK_FINISHED', index=3, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TASK_FAILED', index=4, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TASK_KILLED', index=5, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TASK_LOST', index=6, number=5,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=3730,
  serialized_end=3864,
)

TaskState = enum_type_wrapper.EnumTypeWrapper(_TASKSTATE)
DRIVER_NOT_STARTED = 1
DRIVER_RUNNING = 2
DRIVER_ABORTED = 3
DRIVER_STOPPED = 4
TASK_STAGING = 6
TASK_STARTING = 0
TASK_RUNNING = 1
TASK_FINISHED = 2
TASK_FAILED = 3
TASK_KILLED = 4
TASK_LOST = 5


_VALUE_TYPE = _descriptor.EnumDescriptor(
  name='Type',
  full_name='mesos.Value.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='SCALAR', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='RANGES', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SET', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TEXT', index=3, number=3,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=1479,
  serialized_end=1528,
)


_FRAMEWORKID = _descriptor.Descriptor(
  name='FrameworkID',
  full_name='mesos.FrameworkID',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='mesos.FrameworkID.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=22,
  serialized_end=50,
)


_OFFERID = _descriptor.Descriptor(
  name='OfferID',
  full_name='mesos.OfferID',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='mesos.OfferID.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=52,
  serialized_end=76,
)


_SLAVEID = _descriptor.Descriptor(
  name='SlaveID',
  full_name='mesos.SlaveID',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='mesos.SlaveID.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=78,
  serialized_end=102,
)


_TASKID = _descriptor.Descriptor(
  name='TaskID',
  full_name='mesos.TaskID',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='mesos.TaskID.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=104,
  serialized_end=127,
)


_EXECUTORID = _descriptor.Descriptor(
  name='ExecutorID',
  full_name='mesos.ExecutorID',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='mesos.ExecutorID.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=129,
  serialized_end=156,
)


_CONTAINERID = _descriptor.Descriptor(
  name='ContainerID',
  full_name='mesos.ContainerID',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='mesos.ContainerID.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=158,
  serialized_end=186,
)


_FRAMEWORKINFO = _descriptor.Descriptor(
  name='FrameworkInfo',
  full_name='mesos.FrameworkInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='user', full_name='mesos.FrameworkInfo.user', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='name', full_name='mesos.FrameworkInfo.name', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='id', full_name='mesos.FrameworkInfo.id', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='failover_timeout', full_name='mesos.FrameworkInfo.failover_timeout', index=3,
      number=4, type=1, cpp_type=5, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='checkpoint', full_name='mesos.FrameworkInfo.checkpoint', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='role', full_name='mesos.FrameworkInfo.role', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=True, default_value=unicode("*", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='hostname', full_name='mesos.FrameworkInfo.hostname', index=6,
      number=7, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=189,
  serialized_end=355,
)


_COMMANDINFO_URI = _descriptor.Descriptor(
  name='URI',
  full_name='mesos.CommandInfo.URI',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='mesos.CommandInfo.URI.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='executable', full_name='mesos.CommandInfo.URI.executable', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=520,
  serialized_end=560,
)

_COMMANDINFO_CONTAINERINFO = _descriptor.Descriptor(
  name='ContainerInfo',
  full_name='mesos.CommandInfo.ContainerInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='image', full_name='mesos.CommandInfo.ContainerInfo.image', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='options', full_name='mesos.CommandInfo.ContainerInfo.options', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=562,
  serialized_end=609,
)

_COMMANDINFO = _descriptor.Descriptor(
  name='CommandInfo',
  full_name='mesos.CommandInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='uris', full_name='mesos.CommandInfo.uris', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='environment', full_name='mesos.CommandInfo.environment', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value', full_name='mesos.CommandInfo.value', index=2,
      number=3, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='container', full_name='mesos.CommandInfo.container', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_COMMANDINFO_URI, _COMMANDINFO_CONTAINERINFO, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=358,
  serialized_end=609,
)


_EXECUTORINFO = _descriptor.Descriptor(
  name='ExecutorInfo',
  full_name='mesos.ExecutorInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='executor_id', full_name='mesos.ExecutorInfo.executor_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.ExecutorInfo.framework_id', index=1,
      number=8, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='command', full_name='mesos.ExecutorInfo.command', index=2,
      number=7, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='resources', full_name='mesos.ExecutorInfo.resources', index=3,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='name', full_name='mesos.ExecutorInfo.name', index=4,
      number=9, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='source', full_name='mesos.ExecutorInfo.source', index=5,
      number=10, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='data', full_name='mesos.ExecutorInfo.data', index=6,
      number=4, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=612,
  serialized_end=825,
)


_MASTERINFO = _descriptor.Descriptor(
  name='MasterInfo',
  full_name='mesos.MasterInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='mesos.MasterInfo.id', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='ip', full_name='mesos.MasterInfo.ip', index=1,
      number=2, type=13, cpp_type=3, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='port', full_name='mesos.MasterInfo.port', index=2,
      number=3, type=13, cpp_type=3, label=2,
      has_default_value=True, default_value=5050,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='pid', full_name='mesos.MasterInfo.pid', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='hostname', full_name='mesos.MasterInfo.hostname', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=827,
  serialized_end=914,
)


_SLAVEINFO = _descriptor.Descriptor(
  name='SlaveInfo',
  full_name='mesos.SlaveInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='hostname', full_name='mesos.SlaveInfo.hostname', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='port', full_name='mesos.SlaveInfo.port', index=1,
      number=8, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=5051,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='resources', full_name='mesos.SlaveInfo.resources', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='attributes', full_name='mesos.SlaveInfo.attributes', index=3,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='id', full_name='mesos.SlaveInfo.id', index=4,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='checkpoint', full_name='mesos.SlaveInfo.checkpoint', index=5,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='webui_hostname', full_name='mesos.SlaveInfo.webui_hostname', index=6,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='webui_port', full_name='mesos.SlaveInfo.webui_port', index=7,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=8081,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=917,
  serialized_end=1145,
)


_VALUE_SCALAR = _descriptor.Descriptor(
  name='Scalar',
  full_name='mesos.Value.Scalar',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='mesos.Value.Scalar.value', index=0,
      number=1, type=1, cpp_type=5, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1328,
  serialized_end=1351,
)

_VALUE_RANGE = _descriptor.Descriptor(
  name='Range',
  full_name='mesos.Value.Range',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='begin', full_name='mesos.Value.Range.begin', index=0,
      number=1, type=4, cpp_type=4, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='end', full_name='mesos.Value.Range.end', index=1,
      number=2, type=4, cpp_type=4, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1353,
  serialized_end=1388,
)

_VALUE_RANGES = _descriptor.Descriptor(
  name='Ranges',
  full_name='mesos.Value.Ranges',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='range', full_name='mesos.Value.Ranges.range', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1390,
  serialized_end=1433,
)

_VALUE_SET = _descriptor.Descriptor(
  name='Set',
  full_name='mesos.Value.Set',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='item', full_name='mesos.Value.Set.item', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1435,
  serialized_end=1454,
)

_VALUE_TEXT = _descriptor.Descriptor(
  name='Text',
  full_name='mesos.Value.Text',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='mesos.Value.Text.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1456,
  serialized_end=1477,
)

_VALUE = _descriptor.Descriptor(
  name='Value',
  full_name='mesos.Value',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='type', full_name='mesos.Value.type', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='scalar', full_name='mesos.Value.scalar', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='ranges', full_name='mesos.Value.ranges', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='set', full_name='mesos.Value.set', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='text', full_name='mesos.Value.text', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_VALUE_SCALAR, _VALUE_RANGE, _VALUE_RANGES, _VALUE_SET, _VALUE_TEXT, ],
  enum_types=[
    _VALUE_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1148,
  serialized_end=1528,
)


_ATTRIBUTE = _descriptor.Descriptor(
  name='Attribute',
  full_name='mesos.Attribute',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='mesos.Attribute.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='type', full_name='mesos.Attribute.type', index=1,
      number=2, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='scalar', full_name='mesos.Attribute.scalar', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='ranges', full_name='mesos.Attribute.ranges', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='set', full_name='mesos.Attribute.set', index=4,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='text', full_name='mesos.Attribute.text', index=5,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1531,
  serialized_end=1727,
)


_RESOURCE = _descriptor.Descriptor(
  name='Resource',
  full_name='mesos.Resource',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='mesos.Resource.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='type', full_name='mesos.Resource.type', index=1,
      number=2, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='scalar', full_name='mesos.Resource.scalar', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='ranges', full_name='mesos.Resource.ranges', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='set', full_name='mesos.Resource.set', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='role', full_name='mesos.Resource.role', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=True, default_value=unicode("*", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1730,
  serialized_end=1909,
)


_RESOURCESTATISTICS = _descriptor.Descriptor(
  name='ResourceStatistics',
  full_name='mesos.ResourceStatistics',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='mesos.ResourceStatistics.timestamp', index=0,
      number=1, type=1, cpp_type=5, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='cpus_user_time_secs', full_name='mesos.ResourceStatistics.cpus_user_time_secs', index=1,
      number=2, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='cpus_system_time_secs', full_name='mesos.ResourceStatistics.cpus_system_time_secs', index=2,
      number=3, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='cpus_limit', full_name='mesos.ResourceStatistics.cpus_limit', index=3,
      number=4, type=1, cpp_type=5, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='cpus_nr_periods', full_name='mesos.ResourceStatistics.cpus_nr_periods', index=4,
      number=7, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='cpus_nr_throttled', full_name='mesos.ResourceStatistics.cpus_nr_throttled', index=5,
      number=8, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='cpus_throttled_time_secs', full_name='mesos.ResourceStatistics.cpus_throttled_time_secs', index=6,
      number=9, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='mem_rss_bytes', full_name='mesos.ResourceStatistics.mem_rss_bytes', index=7,
      number=5, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='mem_limit_bytes', full_name='mesos.ResourceStatistics.mem_limit_bytes', index=8,
      number=6, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='mem_file_bytes', full_name='mesos.ResourceStatistics.mem_file_bytes', index=9,
      number=10, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='mem_anon_bytes', full_name='mesos.ResourceStatistics.mem_anon_bytes', index=10,
      number=11, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='mem_mapped_file_bytes', full_name='mesos.ResourceStatistics.mem_mapped_file_bytes', index=11,
      number=12, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1912,
  serialized_end=2244,
)


_RESOURCEUSAGE = _descriptor.Descriptor(
  name='ResourceUsage',
  full_name='mesos.ResourceUsage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.ResourceUsage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.ResourceUsage.framework_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='executor_id', full_name='mesos.ResourceUsage.executor_id', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='executor_name', full_name='mesos.ResourceUsage.executor_name', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='task_id', full_name='mesos.ResourceUsage.task_id', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='statistics', full_name='mesos.ResourceUsage.statistics', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2247,
  serialized_end=2480,
)


_REQUEST = _descriptor.Descriptor(
  name='Request',
  full_name='mesos.Request',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.Request.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='resources', full_name='mesos.Request.resources', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2482,
  serialized_end=2561,
)


_OFFER = _descriptor.Descriptor(
  name='Offer',
  full_name='mesos.Offer',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='mesos.Offer.id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.Offer.framework_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.Offer.slave_id', index=2,
      number=3, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='hostname', full_name='mesos.Offer.hostname', index=3,
      number=4, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='resources', full_name='mesos.Offer.resources', index=4,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='attributes', full_name='mesos.Offer.attributes', index=5,
      number=7, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='executor_ids', full_name='mesos.Offer.executor_ids', index=6,
      number=6, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2564,
  serialized_end=2808,
)


_TASKINFO = _descriptor.Descriptor(
  name='TaskInfo',
  full_name='mesos.TaskInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='mesos.TaskInfo.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='task_id', full_name='mesos.TaskInfo.task_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.TaskInfo.slave_id', index=2,
      number=3, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='resources', full_name='mesos.TaskInfo.resources', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='executor', full_name='mesos.TaskInfo.executor', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='command', full_name='mesos.TaskInfo.command', index=5,
      number=7, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='data', full_name='mesos.TaskInfo.data', index=6,
      number=6, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2811,
  serialized_end=3027,
)


_TASKSTATUS = _descriptor.Descriptor(
  name='TaskStatus',
  full_name='mesos.TaskStatus',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='task_id', full_name='mesos.TaskStatus.task_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='state', full_name='mesos.TaskStatus.state', index=1,
      number=2, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=6,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='message', full_name='mesos.TaskStatus.message', index=2,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='data', full_name='mesos.TaskStatus.data', index=3,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.TaskStatus.slave_id', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='mesos.TaskStatus.timestamp', index=5,
      number=6, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3030,
  serialized_end=3191,
)


_FILTERS = _descriptor.Descriptor(
  name='Filters',
  full_name='mesos.Filters',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='refuse_seconds', full_name='mesos.Filters.refuse_seconds', index=0,
      number=1, type=1, cpp_type=5, label=1,
      has_default_value=True, default_value=5,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3193,
  serialized_end=3229,
)


_ENVIRONMENT_VARIABLE = _descriptor.Descriptor(
  name='Variable',
  full_name='mesos.Environment.Variable',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='mesos.Environment.Variable.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value', full_name='mesos.Environment.Variable.value', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3294,
  serialized_end=3333,
)

_ENVIRONMENT = _descriptor.Descriptor(
  name='Environment',
  full_name='mesos.Environment',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='variables', full_name='mesos.Environment.variables', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_ENVIRONMENT_VARIABLE, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3231,
  serialized_end=3333,
)


_PARAMETER = _descriptor.Descriptor(
  name='Parameter',
  full_name='mesos.Parameter',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='mesos.Parameter.key', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value', full_name='mesos.Parameter.value', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3335,
  serialized_end=3374,
)


_PARAMETERS = _descriptor.Descriptor(
  name='Parameters',
  full_name='mesos.Parameters',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='parameter', full_name='mesos.Parameters.parameter', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3376,
  serialized_end=3425,
)


_CREDENTIAL = _descriptor.Descriptor(
  name='Credential',
  full_name='mesos.Credential',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='principal', full_name='mesos.Credential.principal', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='secret', full_name='mesos.Credential.secret', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3427,
  serialized_end=3474,
)


_RESOURCEARRAY = _descriptor.Descriptor(
  name='ResourceArray',
  full_name='mesos.ResourceArray',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='resource', full_name='mesos.ResourceArray.resource', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3476,
  serialized_end=3526,
)


_EXTERNALTERMINATION = _descriptor.Descriptor(
  name='ExternalTermination',
  full_name='mesos.ExternalTermination',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='status', full_name='mesos.ExternalTermination.status', index=0,
      number=1, type=13, cpp_type=3, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='killed', full_name='mesos.ExternalTermination.killed', index=1,
      number=2, type=8, cpp_type=7, label=2,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='message', full_name='mesos.ExternalTermination.message', index=2,
      number=3, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3528,
  serialized_end=3598,
)


_EXTERNALSTATUS = _descriptor.Descriptor(
  name='ExternalStatus',
  full_name='mesos.ExternalStatus',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='message', full_name='mesos.ExternalStatus.message', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3600,
  serialized_end=3633,
)

_FRAMEWORKINFO.fields_by_name['id'].message_type = _FRAMEWORKID
_COMMANDINFO_URI.containing_type = _COMMANDINFO;
_COMMANDINFO_CONTAINERINFO.containing_type = _COMMANDINFO;
_COMMANDINFO.fields_by_name['uris'].message_type = _COMMANDINFO_URI
_COMMANDINFO.fields_by_name['environment'].message_type = _ENVIRONMENT
_COMMANDINFO.fields_by_name['container'].message_type = _COMMANDINFO_CONTAINERINFO
_EXECUTORINFO.fields_by_name['executor_id'].message_type = _EXECUTORID
_EXECUTORINFO.fields_by_name['framework_id'].message_type = _FRAMEWORKID
_EXECUTORINFO.fields_by_name['command'].message_type = _COMMANDINFO
_EXECUTORINFO.fields_by_name['resources'].message_type = _RESOURCE
_SLAVEINFO.fields_by_name['resources'].message_type = _RESOURCE
_SLAVEINFO.fields_by_name['attributes'].message_type = _ATTRIBUTE
_SLAVEINFO.fields_by_name['id'].message_type = _SLAVEID
_VALUE_SCALAR.containing_type = _VALUE;
_VALUE_RANGE.containing_type = _VALUE;
_VALUE_RANGES.fields_by_name['range'].message_type = _VALUE_RANGE
_VALUE_RANGES.containing_type = _VALUE;
_VALUE_SET.containing_type = _VALUE;
_VALUE_TEXT.containing_type = _VALUE;
_VALUE.fields_by_name['type'].enum_type = _VALUE_TYPE
_VALUE.fields_by_name['scalar'].message_type = _VALUE_SCALAR
_VALUE.fields_by_name['ranges'].message_type = _VALUE_RANGES
_VALUE.fields_by_name['set'].message_type = _VALUE_SET
_VALUE.fields_by_name['text'].message_type = _VALUE_TEXT
_VALUE_TYPE.containing_type = _VALUE;
_ATTRIBUTE.fields_by_name['type'].enum_type = _VALUE_TYPE
_ATTRIBUTE.fields_by_name['scalar'].message_type = _VALUE_SCALAR
_ATTRIBUTE.fields_by_name['ranges'].message_type = _VALUE_RANGES
_ATTRIBUTE.fields_by_name['set'].message_type = _VALUE_SET
_ATTRIBUTE.fields_by_name['text'].message_type = _VALUE_TEXT
_RESOURCE.fields_by_name['type'].enum_type = _VALUE_TYPE
_RESOURCE.fields_by_name['scalar'].message_type = _VALUE_SCALAR
_RESOURCE.fields_by_name['ranges'].message_type = _VALUE_RANGES
_RESOURCE.fields_by_name['set'].message_type = _VALUE_SET
_RESOURCEUSAGE.fields_by_name['slave_id'].message_type = _SLAVEID
_RESOURCEUSAGE.fields_by_name['framework_id'].message_type = _FRAMEWORKID
_RESOURCEUSAGE.fields_by_name['executor_id'].message_type = _EXECUTORID
_RESOURCEUSAGE.fields_by_name['task_id'].message_type = _TASKID
_RESOURCEUSAGE.fields_by_name['statistics'].message_type = _RESOURCESTATISTICS
_REQUEST.fields_by_name['slave_id'].message_type = _SLAVEID
_REQUEST.fields_by_name['resources'].message_type = _RESOURCE
_OFFER.fields_by_name['id'].message_type = _OFFERID
_OFFER.fields_by_name['framework_id'].message_type = _FRAMEWORKID
_OFFER.fields_by_name['slave_id'].message_type = _SLAVEID
_OFFER.fields_by_name['resources'].message_type = _RESOURCE
_OFFER.fields_by_name['attributes'].message_type = _ATTRIBUTE
_OFFER.fields_by_name['executor_ids'].message_type = _EXECUTORID
_TASKINFO.fields_by_name['task_id'].message_type = _TASKID
_TASKINFO.fields_by_name['slave_id'].message_type = _SLAVEID
_TASKINFO.fields_by_name['resources'].message_type = _RESOURCE
_TASKINFO.fields_by_name['executor'].message_type = _EXECUTORINFO
_TASKINFO.fields_by_name['command'].message_type = _COMMANDINFO
_TASKSTATUS.fields_by_name['task_id'].message_type = _TASKID
_TASKSTATUS.fields_by_name['state'].enum_type = _TASKSTATE
_TASKSTATUS.fields_by_name['slave_id'].message_type = _SLAVEID
_ENVIRONMENT_VARIABLE.containing_type = _ENVIRONMENT;
_ENVIRONMENT.fields_by_name['variables'].message_type = _ENVIRONMENT_VARIABLE
_PARAMETERS.fields_by_name['parameter'].message_type = _PARAMETER
_RESOURCEARRAY.fields_by_name['resource'].message_type = _RESOURCE
DESCRIPTOR.message_types_by_name['FrameworkID'] = _FRAMEWORKID
DESCRIPTOR.message_types_by_name['OfferID'] = _OFFERID
DESCRIPTOR.message_types_by_name['SlaveID'] = _SLAVEID
DESCRIPTOR.message_types_by_name['TaskID'] = _TASKID
DESCRIPTOR.message_types_by_name['ExecutorID'] = _EXECUTORID
DESCRIPTOR.message_types_by_name['ContainerID'] = _CONTAINERID
DESCRIPTOR.message_types_by_name['FrameworkInfo'] = _FRAMEWORKINFO
DESCRIPTOR.message_types_by_name['CommandInfo'] = _COMMANDINFO
DESCRIPTOR.message_types_by_name['ExecutorInfo'] = _EXECUTORINFO
DESCRIPTOR.message_types_by_name['MasterInfo'] = _MASTERINFO
DESCRIPTOR.message_types_by_name['SlaveInfo'] = _SLAVEINFO
DESCRIPTOR.message_types_by_name['Value'] = _VALUE
DESCRIPTOR.message_types_by_name['Attribute'] = _ATTRIBUTE
DESCRIPTOR.message_types_by_name['Resource'] = _RESOURCE
DESCRIPTOR.message_types_by_name['ResourceStatistics'] = _RESOURCESTATISTICS
DESCRIPTOR.message_types_by_name['ResourceUsage'] = _RESOURCEUSAGE
DESCRIPTOR.message_types_by_name['Request'] = _REQUEST
DESCRIPTOR.message_types_by_name['Offer'] = _OFFER
DESCRIPTOR.message_types_by_name['TaskInfo'] = _TASKINFO
DESCRIPTOR.message_types_by_name['TaskStatus'] = _TASKSTATUS
DESCRIPTOR.message_types_by_name['Filters'] = _FILTERS
DESCRIPTOR.message_types_by_name['Environment'] = _ENVIRONMENT
DESCRIPTOR.message_types_by_name['Parameter'] = _PARAMETER
DESCRIPTOR.message_types_by_name['Parameters'] = _PARAMETERS
DESCRIPTOR.message_types_by_name['Credential'] = _CREDENTIAL
DESCRIPTOR.message_types_by_name['ResourceArray'] = _RESOURCEARRAY
DESCRIPTOR.message_types_by_name['ExternalTermination'] = _EXTERNALTERMINATION
DESCRIPTOR.message_types_by_name['ExternalStatus'] = _EXTERNALSTATUS

class FrameworkID(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _FRAMEWORKID

  # @@protoc_insertion_point(class_scope:mesos.FrameworkID)

class OfferID(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _OFFERID

  # @@protoc_insertion_point(class_scope:mesos.OfferID)

class SlaveID(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SLAVEID

  # @@protoc_insertion_point(class_scope:mesos.SlaveID)

class TaskID(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _TASKID

  # @@protoc_insertion_point(class_scope:mesos.TaskID)

class ExecutorID(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _EXECUTORID

  # @@protoc_insertion_point(class_scope:mesos.ExecutorID)

class ContainerID(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CONTAINERID

  # @@protoc_insertion_point(class_scope:mesos.ContainerID)

class FrameworkInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _FRAMEWORKINFO

  # @@protoc_insertion_point(class_scope:mesos.FrameworkInfo)

class CommandInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class URI(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _COMMANDINFO_URI

    # @@protoc_insertion_point(class_scope:mesos.CommandInfo.URI)

  class ContainerInfo(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _COMMANDINFO_CONTAINERINFO

    # @@protoc_insertion_point(class_scope:mesos.CommandInfo.ContainerInfo)
  DESCRIPTOR = _COMMANDINFO

  # @@protoc_insertion_point(class_scope:mesos.CommandInfo)

class ExecutorInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _EXECUTORINFO

  # @@protoc_insertion_point(class_scope:mesos.ExecutorInfo)

class MasterInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _MASTERINFO

  # @@protoc_insertion_point(class_scope:mesos.MasterInfo)

class SlaveInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SLAVEINFO

  # @@protoc_insertion_point(class_scope:mesos.SlaveInfo)

class Value(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class Scalar(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _VALUE_SCALAR

    # @@protoc_insertion_point(class_scope:mesos.Value.Scalar)

  class Range(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _VALUE_RANGE

    # @@protoc_insertion_point(class_scope:mesos.Value.Range)

  class Ranges(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _VALUE_RANGES

    # @@protoc_insertion_point(class_scope:mesos.Value.Ranges)

  class Set(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _VALUE_SET

    # @@protoc_insertion_point(class_scope:mesos.Value.Set)

  class Text(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _VALUE_TEXT

    # @@protoc_insertion_point(class_scope:mesos.Value.Text)
  DESCRIPTOR = _VALUE

  # @@protoc_insertion_point(class_scope:mesos.Value)

class Attribute(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ATTRIBUTE

  # @@protoc_insertion_point(class_scope:mesos.Attribute)

class Resource(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RESOURCE

  # @@protoc_insertion_point(class_scope:mesos.Resource)

class ResourceStatistics(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RESOURCESTATISTICS

  # @@protoc_insertion_point(class_scope:mesos.ResourceStatistics)

class ResourceUsage(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RESOURCEUSAGE

  # @@protoc_insertion_point(class_scope:mesos.ResourceUsage)

class Request(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REQUEST

  # @@protoc_insertion_point(class_scope:mesos.Request)

class Offer(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _OFFER

  # @@protoc_insertion_point(class_scope:mesos.Offer)

class TaskInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _TASKINFO

  # @@protoc_insertion_point(class_scope:mesos.TaskInfo)

class TaskStatus(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _TASKSTATUS

  # @@protoc_insertion_point(class_scope:mesos.TaskStatus)

class Filters(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _FILTERS

  # @@protoc_insertion_point(class_scope:mesos.Filters)

class Environment(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class Variable(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _ENVIRONMENT_VARIABLE

    # @@protoc_insertion_point(class_scope:mesos.Environment.Variable)
  DESCRIPTOR = _ENVIRONMENT

  # @@protoc_insertion_point(class_scope:mesos.Environment)

class Parameter(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _PARAMETER

  # @@protoc_insertion_point(class_scope:mesos.Parameter)

class Parameters(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _PARAMETERS

  # @@protoc_insertion_point(class_scope:mesos.Parameters)

class Credential(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CREDENTIAL

  # @@protoc_insertion_point(class_scope:mesos.Credential)

class ResourceArray(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RESOURCEARRAY

  # @@protoc_insertion_point(class_scope:mesos.ResourceArray)

class ExternalTermination(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _EXTERNALTERMINATION

  # @@protoc_insertion_point(class_scope:mesos.ExternalTermination)

class ExternalStatus(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _EXTERNALSTATUS

  # @@protoc_insertion_point(class_scope:mesos.ExternalStatus)


DESCRIPTOR.has_options = True
DESCRIPTOR._options = _descriptor._ParseOptions(descriptor_pb2.FileOptions(), '\n\020org.apache.mesosB\006Protos')
# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = path
import os
import sys

def me():
    return os.path.abspath(sys.argv[0])


########NEW FILE########
__FILENAME__ = sig
import os
import signal

import deimos.logger


def is_signal_name(s):
    return s.startswith("SIG") and not s.startswith("SIG_")

names = dict((getattr(signal, s), s) for s in dir(signal) if is_signal_name(s))

def install(f, signals=[signal.SIGINT, signal.SIGTERM]):
    log = deimos.logger.logger(2)
    def handler(signum, _):
        log.warning("%s (%d)", names.get(signum, "SIG???"), signum)
        response = f(signum)
        if type(response) == Resume:
            return
        if type(response) is int:
            os._exit(response)
        os._exit(-signum)
    for _ in signals: signal.signal(_, handler)

class Resume(object):
    def __eq__(self, other):
        return self.__class__ == other.__class__


########NEW FILE########
__FILENAME__ = state
import errno
from fcntl import LOCK_EX, LOCK_NB, LOCK_SH, LOCK_UN
import itertools
import os
import random
import signal
import time

import deimos.docker
from deimos.err import *
from deimos.logger import log
from deimos._struct import _Struct
from deimos.timestamp import iso


class State(_Struct):
    def __init__(self, root, docker_id=None, mesos_id=None, executor_id=None):
        _Struct.__init__(self, root=os.path.abspath(root),
                               docker_id=docker_id,
                               mesos_id=mesos_id,
                               executor_id=executor_id,
                               timestamp=None)
    def resolve(self, *args, **kwargs):
        if self.mesos_id is not None:
            return self._mesos(*args, **kwargs)
        else:
            return self._docker(*args, **kwargs)
    def mesos_container_id(self):
        if self.mesos_id is None:
            self.mesos_id = self._readf("mesos-container-id")
        return self.mesos_id
    def eid(self):
        if self.executor_id is None:
            self.executor_id = self._readf("eid")
        return self.executor_id
    def sandbox_symlink(self, value=None):
        p = self.resolve("fs")
        if value is not None:
            link(value, p)
        return p
    def pid(self, value=None):
        if value is not None:
            self._writef("pid", str(value))
        data = self._readf("pid")
        if data is not None:
            return int(data)
    def cid(self, refresh=False):
        if self.docker_id is None or refresh:
            self.docker_id = self._readf("cid")
        return self.docker_id
    def t(self):
        if self.timestamp is None:
            self.timestamp = self._readf("t")
        return self.timestamp
    def await_cid(self, seconds=60):
        base   = 0.05
        start  = time.time()
        steps  = [ 1.0, 1.25, 1.6, 2.0, 2.5, 3.2, 4.0, 5.0, 6.4, 8.0 ]
        scales = ( 10.0 ** n for n in itertools.count() )
        scaled = ( [scale * step for step in steps] for scale in scales )
        sleeps = itertools.chain.from_iterable(scaled)
        log.info("Awaiting CID file: %s", self.resolve("cid"))
        while self.cid(refresh=True) in [None, ""]:
            time.sleep(next(sleeps))
            if time.time() - start >= seconds:
                raise CIDTimeout("No CID file after %ds" % seconds)
    def await_launch(self):
        lk_l = self.lock("launch", LOCK_SH)
        self.ids(3)
        if self.cid() is None:
            lk_l.unlock()
            self.await_cid()
            lk_l = self.lock("launch", LOCK_SH)
        return lk_l
    def lock(self, name, flags, seconds=60):
        fmt_time  = "indefinite" if seconds is None else "%ds" % seconds
        fmt_flags = deimos.flock.format_lock_flags(flags)
        flags, seconds = deimos.flock.nb_seconds(flags, seconds)
        log.info("request // %s %s (%s)", name, fmt_flags, fmt_time)
        p = self.resolve(os.path.join("lock", name), mkdir=True)
        lk = deimos.flock.LK(p, flags, seconds)
        try:
            lk.lock()
        except deimos.flock.Err:
            log.error("failure // %s %s (%s)", name, fmt_flags, fmt_time)
            raise
        if (flags & LOCK_EX) != 0:
            lk.handle.write(iso() + "\n")
        log.info("success // %s %s (%s)", name, fmt_flags, fmt_time)
        return lk
    def exit(self, value=None):
        if value is not None:
            self._writef("exit", str(value))
        else:
            data = self._readf("exit")
            if data is not None:
                return deimos.docker.read_wait_code(data)
    def push(self):
        self._mkdir()
        properties = [("cid", self.docker_id),
                      ("mesos-container-id", self.mesos_id),
                      ("eid", self.executor_id)]
        self.set_start_time()
        for k, v in properties:
            if v is not None and not os.path.exists(self.resolve(k)):
                self._writef(k, v)
        if self.cid() is not None:
            docker = os.path.join(self.root, "docker", self.cid())
            link("../mesos/" + self.mesos_id, docker)
    def set_start_time(self):
        if self.t() is not None:
            return
        d = os.path.abspath(os.path.join(self.root, "start-time"))
        create(d)
        start, t = time.time(), iso()
        while time.time() - start <= 1.0:
            try:
                p = os.path.join(d, t)
                os.symlink("../mesos/" + self.mesos_id, p)
                self._writef("t", t)
                self.timestamp = t
                return
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                time.sleep(random.uniform(0.005, 0.025))
                t = iso()
    def _mkdir(self):
        create(self._mesos())
    def _readf(self, path):
        f = self.resolve(path)
        if os.path.exists(f):
            with open(f) as h:
                return h.read().strip()
    def _writef(self, path, value):
        f = self.resolve(path)
        with open(f, "w+") as h:
            h.write(value + "\n")
    def _docker(self, path=None, mkdir=False):
        if path is None:
            p = os.path.join(self.root, "docker", self.docker_id)
        else:
            p = os.path.join(self.root, "docker", self.docker_id, path)
        p = os.path.abspath(p)
        if mkdir:
            docker = os.path.join(self.root, "docker", self.docker_id)
            if not os.path.exists(docker):
                log.error("No Docker symlink (this should be impossible)")
                raise Err("Bad Docker symlink state")
            create(os.path.dirname(p))
        return p
    def _mesos(self, path=None, mkdir=False):
        if path is None:
            p = os.path.join(self.root, "mesos", self.mesos_id)
        else:
            p = os.path.join(self.root, "mesos", self.mesos_id, path)
        p = os.path.abspath(p)
        if mkdir:
            create(os.path.dirname(p))
        return p
    def ids(self, height=2):
        log = deimos.logger.logger(height)
        if self.eid() is not None:
            log.info("eid    = %s", self.eid())
        if self.mesos_container_id() is not None:
            log.info("mesos  = %s", self.mesos_container_id())
        if self.cid() is not None:
            log.info("docker = %s", self.cid())

class CIDTimeout(Err): pass

def create(path):
    if not os.path.exists(path):
        os.makedirs(path)

def link(source, target):
    if not os.path.exists(target):
        create(os.path.dirname(target))
        os.symlink(source, target)

def state(directory):
    mesos = os.path.join(directory, "mesos-container-id")
    if os.path.exists(mesos):
        with open(mesos) as h:
            mesos_id = h.read().strip()
        root = os.path.dirname(os.path.dirname(os.path.realpath(directory)))
        return State(root=root, mesos_id=mesos_id)


########NEW FILE########
__FILENAME__ = timestamp
import time


def iso(t=time.time()):
    ms  = ("%0.03f" % (t % 1))[1:]
    iso = time.strftime("%FT%T", time.gmtime(t))
    return iso + ms + "Z"


########NEW FILE########
__FILENAME__ = usage
import logging
import resource

from deimos.logger import log
from deimos._struct import _Struct


def report(level=logging.DEBUG):
    self(level)
    children(level)

def self(level=logging.DEBUG):
    log.log(level, rusage(resource.RUSAGE_SELF))

def children(level=logging.DEBUG):
    log.log(level, rusage(resource.RUSAGE_CHILDREN))

def rusage(target=resource.RUSAGE_SELF):
    r = resource.getrusage(target)
    fmt = "rss = %0.03fM  user = %0.03f  sys = %0.03f"
    return fmt % (r.ru_maxrss / (1024.0 * 1024.0), r.ru_utime, r.ru_stime)


########NEW FILE########
__FILENAME__ = _struct
class _Struct(object):
    def __init__(self, **properties):
        self.__dict__.update(properties)
        self._properties = properties.keys()
    def __repr__(self):
        mod, cls = self.__class__.__module__, self.__class__.__name__
        fields = [ "%s=%r" % (k, v) for k, v in self.items() ]
        return mod + "." + cls + "(" + ", ".join(fields) + ")"
    def keys(self):
        return self._properties
    def items(self, onlyset=False):
        vals = [ (k, self.__dict__[k]) for k in self._properties ]
        return [ (k, v) for k, v in vals if v ] if onlyset else vals
    def merge(self, other):
        # NB: Use leftmost constructor, to recheck validity of fields.
        return self.__class__(**dict(self.items() + other.items()))


########NEW FILE########
__FILENAME__ = deimos-test
#!/usr/bin/env python
import argparse
import collections
import os
import logging
import random
import signal
import sys
import threading
import time

import google.protobuf as pb

os.environ["GLOG_minloglevel"] = "3"        # Set before mesos module is loaded
import mesos
import mesos_pb2


#################################### Schedulers implement the integration tests

class Scheduler(mesos.Scheduler):
    def __init__(self, trials=10):
        self.token    = "%08x" % random.getrandbits(32)
        self.trials   = trials
        self.tasks    = []
        self.statuses = {}
        self.log      = log.getChild("scheduler")
        self.loggers  = {}
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)
    def registered(self, driver, framework_id, master):
        self.framework_id = framework_id
        self.log.info("Registered with ID:\n  %s" % framework_id.value)
    def statusUpdate(self, driver, update):
        task, code = update.task_id.value, update.state
        if self.statuses.get(task, None) in Scheduler.terminal:
            self.loggers[task].info(present_status(update) + " (redundant)")
        else:
            self.loggers[task].info(present_status(update))
            self.statuses[task] = code
    def all_tasks_done(self):
        agg = [_ for _ in self.statuses.values() if _ in Scheduler.terminal]
        return len(agg) >= self.trials
    def sum_up(self):
        sums = [ "%s=%d" % (k, v) for k, v in self.task_status_summary() ]
        log.info(" ".join(sums))
    def task_status_summary(self):
        counts = collections.defaultdict(int)
        for task, code in self.statuses.items():
            counts[code] += 1
        return [ (mesos_pb2.TaskState.Name(code), count)
                 for code, count in counts.items() ]
    def next_task_id(self):
        short_id = "%s.task-%02d" % (self.token, len(self.tasks))
        long_id  = "deimos-test." + short_id
        self.loggers[long_id] = log.getChild(short_id)
        return long_id
    terminal = set([ mesos_pb2.TASK_FINISHED,
                     mesos_pb2.TASK_FAILED,
                     mesos_pb2.TASK_KILLED,
                     mesos_pb2.TASK_LOST ])
    failed   = set([ mesos_pb2.TASK_FAILED,
                     mesos_pb2.TASK_KILLED,
                     mesos_pb2.TASK_LOST ])

class SleepScheduler(Scheduler):
    wiki = "https://en.wikipedia.org/wiki/Main_Page"
    def __init__(self, sleep=10, uris=[wiki], container=None, trials=5):
        Scheduler.__init__(self, trials)
        self.sleep     = sleep
        self.uris      = uris
        self.container = container
        self.done      = []
    def statusUpdate(self, driver, update):
        super(type(self), self).statusUpdate(driver, update)
        if self.all_tasks_done():
            self.sum_up()
            driver.stop()
    def resourceOffers(self, driver, offers):
        delay = int(float(self.sleep) / self.trials)
        for offer in offers:
            if len(self.tasks) >= self.trials: break
          # time.sleep(self.sleep + 0.5)
            time.sleep(delay)                    # Space out the requests a bit
            tid  = self.next_task_id()
            sid  = offer.slave_id
            cmd  = "date -u +%T ; sleep " + str(self.sleep) + " ; date -u +%T"
            task = task_with_command(tid, sid, cmd, self.uris, self.container)
            self.tasks += [task]
            self.loggers[tid].info(present_task(task))
            driver.launchTasks(offer.id, [task])

class PGScheduler(Scheduler):
    def __init__(self, sleep=10,
                       container="docker:///zaiste/postgresql",
                       trials=10):
        Scheduler.__init__(self, trials)
        self.container = container
        self.sleep = sleep
    def statusUpdate(self, driver, update):
        super(type(self), self).statusUpdate(driver, update)
        if update.state == mesos_pb2.TASK_RUNNING:
            def end_task():
                time.sleep(self.sleep)
                driver.killTask(update.task_id)
            thread = threading.Thread(target=end_task)
            thread.daemon = True
            thread.start()
        if self.all_tasks_done():
            self.sum_up()
            driver.stop()
    def resourceOffers(self, driver, offers):
        for offer in offers:
            if len(self.tasks) >= self.trials: break
            tid  = self.next_task_id()
            sid  = offer.slave_id
            task = task_with_daemon(tid, sid, self.container)
            self.tasks += [task]
            self.loggers[tid].info(present_task(task))
            driver.launchTasks(offer.id, [task])

class ExecutorScheduler(Scheduler):
    sh = "python deimos-test.py --executor"
    this = "file://" + os.path.abspath(__file__)
    libmesos = "docker:///mesosphere/libmesos"
    shutdown_message = "shutdown"
    def __init__(self, command=sh, uris=[this], container=libmesos, trials=10):
        Scheduler.__init__(self, trials)
        self.command   = command
        self.uris      = uris
        self.container = container
        self.messages  = []
        self.executor  = "deimos-test.%s.executor" % self.token
    def statusUpdate(self, driver, update):
        super(type(self), self).statusUpdate(driver, update)
        if self.all_tasks_done():
            sid = update.slave_id
            eid = mesos_pb2.ExecutorID()
            eid.value = self.executor
            driver.sendFrameworkMessage(eid, sid, type(self).shutdown_message)
            self.sum_up()
            driver.stop()
    def frameworkMessage(self, driver, eid, sid, msg):
        self.messages += [msg]
        driver.killTask(update.task_id)
    def resourceOffers(self, driver, offers):
        for offer in offers:
            if len(self.tasks) >= self.trials: break
            tid  = self.next_task_id()
            task = task_with_executor(tid, offer.slave_id, self.executor,
                                      self.command, self.uris, self.container)
            self.tasks += [task]
            self.loggers[tid].info(present_task(task))
            driver.launchTasks(offer.id, [task])

class ExecutorSchedulerExecutor(mesos.Executor):
    def launchTask(self, driver, task):
        def run():
            log.info("Running task %s" % task.task_id.value)
            update = mesos_pb2.TaskStatus()
            update.task_id.value = task.task_id.value
            update.state = mesos_pb2.TASK_RUNNING
            driver.sendStatusUpdate(update)
            log.info("Sent: TASK_RUNNING")
            update = mesos_pb2.TaskStatus()
            update.task_id.value = task.task_id.value
            update.state = mesos_pb2.TASK_FINISHED
            update.data = "ping"
            driver.sendStatusUpdate(update)
            log.info("Sent: TASK_FINISHED")
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
    def frameworkMessage(self, driver, message):
        if message == ExecutorScheduler.shutdown_message:
            log.warning("Received shutdown message: %s", message)
            driver.stop()
        else:
            log.warning("Unexpected message: %s", message)


################################################################ Task factories

def task_with_executor(tid, sid, eid, *args):
    executor = mesos_pb2.ExecutorInfo()
    executor.executor_id.value = eid
    executor.name = eid
    executor.command.MergeFrom(command(*args))
    task = task_base(tid, sid)
    task.executor.MergeFrom(executor)
    return task

def task_with_command(tid, sid, *args):
    task = task_base(tid, sid)
    task.command.MergeFrom(command(*args))
    return task

def task_with_daemon(tid, sid, image):
    task = task_base(tid, sid)
    task.command.MergeFrom(command(image=image))
    return task

def task_base(tid, sid, cpu=0.5, ram=256):
    task = mesos_pb2.TaskInfo()
    task.task_id.value = tid
    task.slave_id.value = sid.value
    task.name = tid
    cpus = task.resources.add()
    cpus.name = "cpus"
    cpus.type = mesos_pb2.Value.SCALAR
    cpus.scalar.value = cpu
    mem = task.resources.add()
    mem.name = "mem"
    mem.type = mesos_pb2.Value.SCALAR
    mem.scalar.value = ram
    return task

def command(shell="", uris=[], image=None):
    command = mesos_pb2.CommandInfo()
    command.value = shell
    for uri in uris:
        command.uris.add().value = uri
    if image:                      # Rely on the default image when none is set
        container = mesos_pb2.CommandInfo.ContainerInfo()
        container.image = image
        command.container.MergeFrom(container)
    return command

def present_task(task):
    if task.HasField("executor"):
        token, body = "executor", task.executor
    else:
        token, body = "command", task.command
    lines = pb.text_format.MessageToString(body).strip().split("\n")
    return "\n  %s {\n    %s\n  }" % (token, "\n    ".join(lines))

def present_status(update):
    info = mesos_pb2.TaskState.Name(update.state)
    if update.state in Scheduler.failed and update.HasField("message"):
        info += '\n  message: "%s"' % update.message
    return info


########################################################################## Main

def cli():
    schedulers = { "sleep"    : SleepScheduler,
                   "pg"       : PGScheduler,
                   "executor" : ExecutorScheduler }
    p = argparse.ArgumentParser(prog="deimos-test.py")
    p.add_argument("--master", default="localhost:5050",
                   help="Mesos master URL")
    p.add_argument("--test", choices=schedulers.keys(), default="sleep",
                   help="Test scheduler to use")
    p.add_argument("--executor", action="store_true", default=False,
                   help="Runs the executor instead of a test scheduler")
    p.add_argument("--test.container",
                   help="Image URL to use (for any test)")
    p.add_argument("--test.uris", action="append",
                   help="Pass any number of times to add URIs (for any test)")
    p.add_argument("--test.trials", type=int,
                   help="Number of tasks to run (for any test)")
    p.add_argument("--test.sleep", type=int,
                   help="Seconds to sleep (for sleep test)")
    p.add_argument("--test.command",
                   help="Command to use (for executor test)")
    parsed = p.parse_args()

    if parsed.executor:
        log.info("Mesos executor mode was chosen")
        driver = mesos.MesosExecutorDriver(ExecutorSchedulerExecutor())
        code = driver.run()
        log.info(mesos_pb2.Status.Name(code))
        driver.stop()
        if code != mesos_pb2.DRIVER_STOPPED:
            log.error("Driver died in an anomalous state")
            os._exit(2)
        os._exit(0)

    pairs = [ (k.split("test.")[1:], v) for k, v in vars(parsed).items() ]
    constructor_args = dict( (k[0], v) for k, v in pairs if len(k) == 1 and v )
    scheduler_class = schedulers[parsed.test]
    scheduler = scheduler_class(**constructor_args)
    args = ", ".join( "%s=%r" % (k, v) for k, v in constructor_args.items() )
    log.info("Testing: %s(%s)" % (scheduler_class.__name__, args))

    framework = mesos_pb2.FrameworkInfo()
    framework.name = "deimos-test"
    framework.user = ""
    driver = mesos.MesosSchedulerDriver(scheduler, framework, parsed.master)
    code = driver.run()
    log.info(mesos_pb2.Status.Name(code))
    driver.stop()
    ################  2 => driver problem  1 => tests failed  0 => tests passed
    if code != mesos_pb2.DRIVER_STOPPED:
        log.error("Driver died in an anomalous state")
        log.info("Aborted: %s(%s)" % (scheduler_class.__name__, args))
        os._exit(2)
    if any(_ in Scheduler.failed for _ in scheduler.statuses.values()):
        log.error("Test run failed -- not all tasks made it")
        log.info("Failure: %s(%s)" % (scheduler_class.__name__, args))
        os._exit(1)
    log.info("Success: %s(%s)" % (scheduler_class.__name__, args))
    os._exit(0)

logging.basicConfig(format="%(asctime)s.%(msecs)03d %(name)s %(message)s",
                    datefmt="%H:%M:%S", level=logging.DEBUG)
log = logging.getLogger("deimos-test")

if __name__ == "__main__":
    def handler(signum, _):
        log.warning("Signal: " + str(signum))
        os._exit(-signum)
    signal.signal(signal.SIGINT, handler)
    cli()


########NEW FILE########
