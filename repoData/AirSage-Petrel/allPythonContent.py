__FILENAME__ = cmdline
import os
import sys
import argparse
import traceback
import subprocess
import re

import pkg_resources
import yaml

from .util import read_yaml
from .package import build_jar
from .emitter import EmitterBase
from .status import status

def get_storm_version():
    version = subprocess.check_output(['storm', 'version']).strip()
    m = re.search('^\d\.\d\.\d', version)
    return m.group(0)


def get_sourcejar():
    storm_version = get_storm_version()
    sourcejar = pkg_resources.resource_filename(
        pkg_resources.Requirement.parse('petrel'),
        'petrel/generated/storm-petrel-%s-SNAPSHOT.jar' % storm_version)
    return sourcejar

def submit(sourcejar, destjar, config, venv, name, definition, logdir, extrastormcp):
    # Build a topology jar and submit it to Storm.
    if not sourcejar:
        sourcejar = get_sourcejar()
    build_jar(
        source_jar_path=sourcejar,
        dest_jar_path=destjar,
        config=config,
        definition=definition,
        venv=venv,
        logdir=logdir)
    storm_class_path = [ subprocess.check_output(["storm","classpath"]).strip(), destjar ]
    if extrastormcp is not None:
        storm_class_path = [ extrastormcp ] + storm_class_path
    storm_home = os.path.dirname(os.path.dirname(
        subprocess.check_output(['which', 'storm'])))
    submit_args = [
        "",
        "-client",
        "-Dstorm.options=",
        "-Dstorm.home=%s" % storm_home,
        "-cp",":".join(storm_class_path),
        "-Dstorm.jar=%s" % destjar,
        "storm.petrel.GenericTopology",
    ]
    if name:
        submit_args += [name]
    os.execvp('java', submit_args)

def kill(name, config):
    config = read_yaml(config)
    
    # Read the nimbus.host setting from topology YAML so we can submit the
    # "kill" command to the correct cluster.
    nimbus_host = config.get('nimbus.host')
    kill_args = ['', 'kill', name]
    if nimbus_host:
        kill_args += ['-c', 'nimbus.host=%s' % nimbus_host]
    os.execvp('storm', kill_args)

def main():
    parser = argparse.ArgumentParser(prog='petrel', description='Petrel command line')
    subparsers = parser.add_subparsers()
    parser_submit = subparsers.add_parser('submit')
    parser_submit.add_argument('--sourcejar', dest='sourcejar', help='source JAR path')
    parser_submit.add_argument('--destjar', dest='destjar', default='topology.jar',
                        help='destination JAR path')
    parser_submit.add_argument('--config', dest='config', required=True,
                        help='YAML file with the topology configuration')
    parser_submit.add_argument('--definition', dest='definition',
                        help='python module and function defining the topology (must be in current directory)')
    parser_submit.add_argument('--venv', dest='venv',
                        help='An existing virtual environment to reuse on the server')
    parser_submit.add_argument('--logdir', dest='logdir',
                        help='Root directory for logfiles (default: the storm supervisor directory)')
    parser_submit.add_argument('--extrastormcp', dest='extrastormcp',
                        help='Extra jars on the storm classpath, useful for controlling log4j')
    parser_submit.add_argument('name', const=None, nargs='?',
        help='name of the topology. If provided, the topology is submitted to the cluster. ' +
        'If omitted, the topology runs in local mode.')
    parser_submit.set_defaults(func=submit)

    parser_status = subparsers.add_parser('status', help='Report status of running topologies')
    parser_status.add_argument(
        'nimbus',
        help='Nimbus host address')
    parser_status.add_argument('--worker', help='Only list tasks on this worker')
    parser_status.add_argument('--port', help='Only list tasks on this port number')
    parser_status.add_argument('--topology', help='Only list information on this topology')
    parser_status.set_defaults(func=status)
    
    parser_kill = subparsers.add_parser('kill', help='kill a topology running on a cluster')
    parser_kill.add_argument('name', help='name of the topology')
    parser_kill.add_argument('--config', dest='config', required=True,
                        help='YAML file with the topology configuration')
    parser_kill.set_defaults(func=kill)

    try:
        args = parser.parse_args()
        func = args.__dict__.pop('func')
        func(**args.__dict__)
    except Exception as e:
        print str(e)
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = emitter
import os
import sys

import storm

class EmitterBase(object):
    DEFAULT_PYTHON = 'python%d.%d' % (sys.version_info.major, sys.version_info.minor)

    def __init__(self, script):
        # We assume 'script' is in the current directory. We simply get the
        # base part and turn it into a .py name for inclusion in the Storm
        # jar we create.
        path, basename = os.path.split(os.path.relpath(script))
        assert len(path) == 0
        script = '%s.py' % os.path.splitext(basename)[0]
        self.execution_command = self.DEFAULT_PYTHON
        self.script = script
        self._json = {}
        super(EmitterBase, self).__init__()
    
    def declareOutputFields(declarer):
        raise NotImplementedError()

    def getComponentConfiguration(self):
        if len(self._json):
            return self._json
        else:
            return None

class Spout(EmitterBase, storm.Spout):
    pass

class BasicBolt(EmitterBase, storm.BasicBolt):
    pass

class Bolt(EmitterBase, storm.Bolt):
    pass

########NEW FILE########
__FILENAME__ = mock
from collections import deque, defaultdict, namedtuple

import storm

python_id = id

STORM_TUPLE = 0
LIST = 1
TUPLE = 2
NAMEDTUPLE = 3

class MockSpout(storm.Spout):
    def __init__(self, output_fields, data):
        self.output_fields = output_fields
        self.data = data
        self.index = 0

    def declareOutputFields(self):
        return self.output_fields

    def nextTuple(self):
        if self.index < len(self.data):
            storm.emit(self.data[self.index])
            self.index += 1

class Mock(object):
    def __init__(self):
        self.output_type = {}
        self.pending = defaultdict(deque)
        self.processed = defaultdict(deque)
        self.emitter = None
    
    def __enter__(self):
        self.old_emit = storm.emit
        storm.emit = self.emit
        self.old_emitMany = storm.emitMany
        storm.emitMany = self.emitMany
        return self

    def __exit__(self, type, value, traceback):
        storm.emit = self.old_emit
        storm.emitMany = self.old_emitMany
    
    def activate(self, emitter):
        self.emitter = emitter
        if isinstance(emitter, storm.Spout):
            storm.MODE = storm.Spout
        elif isinstance(emitter, (storm.Bolt, storm.BasicBolt)):
            storm.MODE = storm.Bolt
        else:
            assert False, "Neither a spout nor a bolt!"
    
    def emit(self, *args, **kwargs):
        self.__emit(*args, **kwargs)
        #return readTaskIds()
    
    def __emit(self, *args, **kwargs):
        if storm.MODE == storm.Bolt:
            self.emitBolt(*args, **kwargs)
        elif storm.MODE == storm.Spout:
            self.emitSpout(*args, **kwargs)

    def emitMany(self, *args, **kwargs):
        if storm.MODE == storm.Bolt:
            self.emitManyBolt(*args, **kwargs)
        elif storm.MODE == storm.Spout:
            self.emitManySpout(*args, **kwargs)

    def emitManyBolt(self, tuples, stream=None, anchors = [], directTask=None):
        for t in tuples:
            self.emitBolt(t, stream, anchors, directTask)
    
    def emitManySpout(self, tuples, stream=None, anchors = [], directTask=None):
        for t in tuples:
            self.emitSpout(t, stream, id, directTask)

    def emitter_id(self, emitter=None):
        if emitter is None:
            emitter = self.emitter
        return type(emitter).__name__, python_id(emitter)
    
    def emitBolt(self, tup, stream=None, anchors = [], directTask=None):
        # Nice idea, but throws off profiling
        #assert len(tup) == len(self.emitter.declareOutputFields())
        # TODO: We should probably be capturing "anchors" so tests can verify
        # the topology is anchoring output tuples correctly.
        self.pending[self.emitter_id()].append(storm.Tuple(id=None, component=None, stream=stream, task=directTask, values=tup))
        
    def emitSpout(self, tup, stream=None, id=None, directTask=None):
        # Nice idea, but throws off profiling
        #assert len(tup) == len(self.emitter.declareOutputFields())
        self.pending[self.emitter_id()].append(storm.Tuple(id=id, component=None, stream=stream, task=directTask, values=tup))

    def read(self, source_emitter):
        emitter_id = self.emitter_id(source_emitter)
        result = self.pending[emitter_id].popleft()
        self.processed[emitter_id].append(result)
        return result
    
    def get_output_type(self, emitter):
        emitter_id = self.emitter_id(emitter)
        if emitter_id not in self.output_type:
            self.output_type[emitter_id] = namedtuple('%sTuple' % type(emitter).__name__, emitter.declareOutputFields())
            
        return self.output_type[emitter_id]

    @classmethod
    def run_simple_topology(cls, config, emitters, result_type=NAMEDTUPLE, max_spout_emits=None):
        """Tests a simple topology. "Simple" means there it has no branches
        or cycles. "emitters" is a list of emitters, starting with a spout
        followed by 0 or more bolts that run in a chain."""
        
        # The config is almost always required. The only known reason to pass
        # None is when calling run_simple_topology() multiple times for the
        # same components. This can be useful for testing spout ack() and fail()
        # behavior.
        if config is not None:
            for emitter in emitters:
                emitter.initialize(config, {})

        with cls() as self:
            # Read from the spout.
            spout = emitters[0]
            spout_id = self.emitter_id(spout)
            old_length = -1
            length = len(self.pending[spout_id])
            while length > old_length and (max_spout_emits is None or length < max_spout_emits):
                old_length = length 
                self.activate(spout)
                spout.nextTuple()
                length = len(self.pending[spout_id])

            # For each bolt in the sequence, consume all upstream input.
            for i, bolt in enumerate(emitters[1:]):
                previous = emitters[i]
                self.activate(bolt)
                while len(self.pending[self.emitter_id(previous)]) > 0:
                    bolt.process(self.read(previous))

        def make_storm_tuple(t, emitter):
            return t
        
        def make_python_list(t, emitter):
            return list(t.values)
        
        def make_python_tuple(t, emitter):
            return tuple(t.values)

        def make_named_tuple(t, emitter):
            return self.get_output_type(emitter)(*t.values)

        if result_type == STORM_TUPLE:
            make = make_storm_tuple
        elif result_type == LIST:
            make = make_python_list
        elif result_type == NAMEDTUPLE:
            make = make_named_tuple
        else:
            assert False, 'Invalid result type specified: %s' % result_type

        result_values = \
            [ [ make(t, emitter) for t in self.processed[self.emitter_id(emitter)]] for emitter in emitters[:-1] ] + \
            [ [ make(t, emitters[-1]) for t in self.pending[self.emitter_id(emitters[-1])] ] ]
        return dict((k, v) for k, v in zip(emitters, result_values))
        
def run_simple_topology(*l, **kw):
    return Mock.run_simple_topology(*l, **kw)

########NEW FILE########
__FILENAME__ = package
import os
import sys
import shutil
import getpass
import socket
import zipfile
import glob
import pkg_resources
from itertools import chain
from cStringIO import StringIO

from emitter import EmitterBase
from topologybuilder import TopologyBuilder
from util import read_yaml

MANIFEST = 'manifest.txt'

def add_to_jar(jar, name, data):
    path = 'resources/%s' % name
    print 'Adding %s' % path
    jar.writestr(path, data)

def add_file_to_jar(jar, directory, script=None, required=True, strip_dir=True):
    if script is not None:
        path = os.path.join(directory, script)
    else:
        path = directory
    
    # Use glob() to allow for wildcards, e.g. in manifest.txt.
    path_list = glob.glob(path)

    if len(path_list) == 0 and required:
        raise ValueError('No files found matching: %s' % path)
    #elif len(path_list) > 1:
    #    raise ValueError("Wildcard '%s' matches multiple files: %s" % (path, ', '.join(path_list)))
    for this_path in path_list:
        with open(this_path, 'r') as f:
            if strip_dir:
                # Drop the path when adding to the jar.
                name = os.path.basename(this_path)
            else:
                name = os.path.relpath(this_path)
            add_to_jar(jar, name, f.read())

def add_dir_to_jar(jar, directory, required=True):
    dir_path_list = glob.glob(directory)

    if len(dir_path_list) == 0 and required:
        raise ValueError('No directory found matching: %s' % path)
    for dir_path in dir_path_list:
        for dirpath, dirnames, filenames in os.walk(dir_path):
            for filename in filenames:
                add_file_to_jar(jar, dirpath, filename, strip_dir=False)

def add_item_to_jar(jar, item):
    path_list = glob.glob(item)
    for this_path in path_list:
        if os.path.isdir(this_path):
            add_dir_to_jar(jar, this_path)
        elif os.path.isfile(this_path):
            add_file_to_jar(jar, this_path)
        else:
            raise ValueError("No file or directory found matching: %s" % this_path)

def build_jar(source_jar_path, dest_jar_path, config, venv=None, definition=None, logdir=None):
    """Build a StormTopology .jar which encapsulates the topology defined in
    topology_dir. Optionally override the module and function names. This
    feature supports the definition of multiple topologies in a single
    directory."""

    if definition is None:
        definition = 'create.create'

    # Prepare data we'll use later for configuring parallelism.
    config_yaml = read_yaml(config)
    parallelism = dict((k.split('.')[-1], v) for k, v in config_yaml.iteritems()
        if k.startswith('petrel.parallelism'))

    pip_options = config_yaml.get('petrel.pip_options', '')

    module_name, dummy, function_name = definition.rpartition('.')
    
    topology_dir = os.getcwd()

    # Make a copy of the input "jvmpetrel" jar. This jar acts as a generic
    # starting point for all Petrel topologies.
    source_jar_path = os.path.abspath(source_jar_path)
    dest_jar_path = os.path.abspath(dest_jar_path)
    if source_jar_path == dest_jar_path:
        raise ValueError("Error: Destination and source path are the same.")
    shutil.copy(source_jar_path, dest_jar_path)
    jar = zipfile.ZipFile(dest_jar_path, 'a', compression=zipfile.ZIP_DEFLATED)
    
    added_path_entry = False
    try:
        # Add the files listed in manifest.txt to the jar.
        with open(os.path.join(topology_dir, MANIFEST), 'r') as f:
            for fn in f.readlines():
                # Ignore blank and comment lines.
                fn = fn.strip()
                if len(fn) and not fn.startswith('#'):

                    add_item_to_jar(jar, os.path.expandvars(fn.strip()))

        # Add user and machine information to the jar.
        add_to_jar(jar, '__submitter__.yaml', '''
petrel.user: %s
petrel.host: %s
''' % (getpass.getuser(),socket.gethostname()))
        
        # Also add the topology configuration to the jar.
        with open(config, 'r') as f:
            config_text = f.read()
        add_to_jar(jar, '__topology__.yaml', config_text)
    
        # Call module_name/function_name to populate a Thrift topology object.
        builder = TopologyBuilder()
        module_dir = os.path.abspath(topology_dir)
        if module_dir not in sys.path:
            sys.path[:0] = [ module_dir ]
            added_path_entry = True
        module = __import__(module_name)
        getattr(module, function_name)(builder)

        # Add the spout and bolt Python scripts to the jar. Create a
        # setup_<script>.sh for each Python script.

        # Add Python scripts and any other per-script resources.
        for k, v in chain(builder._spouts.iteritems(), builder._bolts.iteritems()):
            add_file_to_jar(jar, topology_dir, v.script)

            # Create a bootstrap script.
            if venv is not None:
                # Allow overriding the execution command from the "petrel"
                # command line. This is handy if the server already has a
                # virtualenv set up with the necessary libraries.
                v.execution_command = os.path.join(venv, 'bin/python')

            # If a parallelism value was specified in the configuration YAML,
            # override any setting provided in the topology definition script.
            if k in parallelism:
                builder._commons[k].parallelism_hint = int(parallelism.pop(k))

            v.execution_command, v.script = \
                intercept(venv, v.execution_command, os.path.splitext(v.script)[0],
                          jar, pip_options, logdir)

        if len(parallelism):
            raise ValueError(
                'Parallelism settings error: There are no components named: %s' %
                ','.join(parallelism.keys()))

        # Build the Thrift topology object and serialize it to the .jar. Must do
        # this *after* the intercept step above since that step may modify the
        # topology definition.
        io = StringIO()
        topology = builder.write(io)
        add_to_jar(jar, 'topology.ser', io.getvalue())
    finally:
        jar.close()
        if added_path_entry:
            # Undo our sys.path change.
            sys.path[:] = sys.path[1:]

def intercept(venv, execution_command, script, jar, pip_options, logdir):
    #create_virtualenv = 1 if execution_command == EmitterBase.DEFAULT_PYTHON else 0
    create_virtualenv = 1 if venv is None else 0
    script_base_name = os.path.splitext(script)[0]
    intercept_script = 'setup_%s.sh' % script_base_name

    # Bootstrap script that sets up the worker's Python environment.
    add_to_jar(jar, intercept_script, '''#!/bin/bash
set -e
SCRIPT=%(script)s
LOG=%(logdir)s/petrel$$_$SCRIPT.log
VENV_LOG=%(logdir)s/petrel$$_virtualenv.log
echo "Beginning task setup" >>$LOG 2>&1

# I've seen Storm Supervisor crash repeatedly if we create any new
# subdirectories (e.g. Python virtualenvs) in the worker's "resources" (i.e.
# startup) directory. So we put new directories in /tmp. It seems okay to create
# individual files though, e.g. the log.
PYVER=%(major)d.%(minor)d
CWDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &&  pwd )"
# Should we also allow dots in topology names?
TOPOLOGY_ID_REGEX="([+A-Za-z0-9_\-]+)/resources$"
[[ $CWDIR =~ $TOPOLOGY_ID_REGEX ]] && TOPOLOGY_ID="${BASH_REMATCH[1]}"
WRKDIR=/tmp/petrel-$TOPOLOGY_ID

VENV=%(venv)s
CREATE_VENV=%(create_virtualenv)d

START=$SECONDS
mkdir -p $WRKDIR/egg_cache >>$LOG 2>&1
export PYTHON_EGG_CACHE=$WRKDIR/egg_cache

set +e
python$PYVER -c "print" >>/dev/null 2>&1
RETVAL=$?
set -e
if [ $RETVAL -ne 0 ]; then
    # If desired Python is not found, run the user's .bashrc. Maybe it will
    # add the desired Python to the path.
    source ~/.bashrc >>$LOG 2>&1
fi
# Now the desired Python *must* be available. This line ensures we detect the
# error and fail before continuing.
python$PYVER -c "print" >>$LOG 2>&1


unamestr=`uname`
if [[ "$unamestr" != 'Darwin' ]]; then
    # Create at most ONE virtualenv for the topology. Put the lock file in /tmp
    # because when running Storm in local mode, each task runs in a different
    # subdirectory. Thus they have different lock files but are creating the same
    # virtualenv. This causes multiple tasks to get into the lock before the
    # virtualenv has all the libraries installed.
    set +e
    which flock >>$LOG 2>&1
    has_flock=$?
    set -e
    LOCKFILE="/tmp/petrel-$TOPOLOGY_ID.lock"
    LOCKFD=99
    # PRIVATE
    _lock()             { flock -$1 $LOCKFD; }
    _no_more_locking()  { _lock u; _lock xn && rm -f $LOCKFILE; }
    _prepare_locking()  { eval "exec $LOCKFD>\\"$LOCKFILE\\""; trap _no_more_locking EXIT; }
    # ON START
    if [ "$has_flock" -eq "0" ]
    then
        _prepare_locking
    fi
    # PUBLIC
    exlock_now()        { _lock xn; }  # obtain an exclusive lock immediately or fail
    exlock()            { _lock x; }   # obtain an exclusive lock
    shlock()            { _lock s; }   # obtain a shared lock
    unlock()            { _lock u; }   # drop a lock

    if [ $CREATE_VENV -ne 0 ]; then
        # On Mac OS X, the "flock" command is not available
        create_new=1
        if [ "$has_flock" -eq "0" ]
        then 
            if [ -d $VENV ];then
                echo "Using existing venv: $VENV" >>$LOG 2>&1
                shlock
                source $VENV/bin/activate >>$LOG 2>&1
                unlock
                create_new=0
            elif ! exlock_now;then
                echo "Using existing venv: $VENV" >>$LOG 2>&1
                shlock
                source $VENV/bin/activate >>$LOG 2>&1
                unlock
                create_new=0
            fi
        fi
        if [ "$create_new" -eq "1" ]
        then
            echo "Creating new venv: $VENV" >>$LOG 2>&1
            virtualenv --system-site-packages --python python$PYVER $VENV >>$VENV_LOG 2>&1
            source $VENV/bin/activate >>$VENV_LOG 2>&1

            # Ensure the version of Thrift on the worker matches our version.
            # This may not matter since Petrel only uses Thrift for topology build
            # and submission, but I've had some odd version problems with Thrift
            # and Storm/Java so I want to be safe.
            for f in simplejson==2.6.1 thrift==%(thrift_version)s PyYAML==3.10
            do
                echo "Installing $f" >>$VENV_LOG 2>&1
                pip install %(pip_options)s $f >>$VENV_LOG 2>&1
            done

            easy_install petrel-*-py$PYVER.egg >>$VENV_LOG 2>&1
            if [ -f ./setup.sh ]; then
                /bin/bash ./setup.sh $CREATE_VENV >>$VENV_LOG 2>&1
            fi
            if [ "$has_flock" -eq "0" ]
            then 
                unlock
            fi
        fi
    else
        # This is a prototype feature where the topology specifies a virtualenv
        # that already exists. Could be useful in some cases, since this means the
        # topology is up and running more quickly.
        if ! exlock_now;then
            echo "Using existing venv: $VENV" >>$LOG 2>&1
            shlock
            source $VENV/bin/activate >>$LOG 2>&1
            unlock
        else
            echo "Updating pre-existing venv: $VENV" >>$LOG 2>&1
            source $VENV/bin/activate >>$LOG 2>&1
            easy_install -U petrel-*-py$PYVER.egg >>$VENV_LOG 2>&1
            if [ -f ./setup.sh ]; then
                /bin/bash ./setup.sh $CREATE_VENV >>$VENV_LOG 2>&1
            fi
            unlock
        fi
    fi
fi

ELAPSED=$(($SECONDS-$START))
echo "Task setup took $ELAPSED seconds" >>$LOG 2>&1
echo "Launching: python -m petrel.run $SCRIPT $LOG" >>$LOG 2>&1
# We use exec to avoid creating another process. Creating a second process is
# not only less efficient but also confuses the way Storm monitors processes.
exec python -m petrel.run $SCRIPT $LOG
''' % dict(
    major=sys.version_info.major,
    minor=sys.version_info.minor,
    script=script,
    venv='$WRKDIR/venv' if venv is None else venv,
    logdir='$PWD' if logdir is None else logdir,
    create_virtualenv=create_virtualenv,
    thrift_version=pkg_resources.get_distribution("thrift").version,
    pip_options=pip_options,
    ))

    return '/bin/bash', intercept_script

########NEW FILE########
__FILENAME__ = rdebug
## {{{ http://code.activestate.com/recipes/576515/ (r2)
try: import readline  # For readline input support
except: pass

import sys, os, traceback, signal, codeop, cStringIO, cPickle, tempfile

def pipename(pid):
    """Return name of pipe to use"""
    return os.path.join(tempfile.gettempdir(), 'debug-%d' % pid)

class NamedPipe(object):
    def __init__(self, name, end=0, mode=0666):
        """Open a pair of pipes, name.in and name.out for communication
        with another process.  One process should pass 1 for end, and the
        other 0.  Data is marshalled with pickle."""
        self.in_name, self.out_name = name +'.in',  name +'.out',
        try: os.mkfifo(self.in_name,mode)
        except OSError: pass
        try: os.mkfifo(self.out_name,mode)
        except OSError: pass
        
        # NOTE: The order the ends are opened in is important - both ends
        # of pipe 1 must be opened before the second pipe can be opened.
        if end:
            self.inp = open(self.out_name,'r')
            self.out = open(self.in_name,'w')
        else:
            self.out = open(self.out_name,'w')
            self.inp = open(self.in_name,'r')
        self._open = True

    def is_open(self):
        return not (self.inp.closed or self.out.closed)
        
    def put(self,msg):
        if self.is_open():
            data = cPickle.dumps(msg,1)
            self.out.write("%d\n" % len(data))
            self.out.write(data)
            self.out.flush()
        else:
            raise Exception("Pipe closed")
        
    def get(self):
        txt=self.inp.readline()
        if not txt: 
            self.inp.close()
        else:
            l = int(txt)
            data=self.inp.read(l)
            if len(data) < l: self.inp.close()
            return cPickle.loads(data)  # Convert back to python object.
            
    def close(self):
        self.inp.close()
        self.out.close()
        try: os.remove(self.in_name)
        except OSError: pass
        try: os.remove(self.out_name)
        except OSError: pass

    def __del__(self):
        self.close()
        
def remote_debug(sig,frame):
    """Handler to allow process to be remotely debugged."""
    def _raiseEx(ex):
        """Raise specified exception in the remote process"""
        _raiseEx.ex = ex
    _raiseEx.ex = None
    
    try:
        # Provide some useful functions.
        locs = {'_raiseEx' : _raiseEx}
        locs.update(frame.f_locals)  # Unless shadowed.
        globs = frame.f_globals
        
        pid = os.getpid()  # Use pipe name based on pid
        pipe = NamedPipe(pipename(pid))
    
        old_stdout, old_stderr = sys.stdout, sys.stderr
        txt = ''
        pipe.put("Interrupting process at following point:\n" + 
               ''.join(traceback.format_stack(frame)) + ">>> ")
        
        try:
            while pipe.is_open() and _raiseEx.ex is None:
                line = pipe.get()
                if line is None: continue # EOF
                txt += line
                try:
                    code = codeop.compile_command(txt)
                    if code:
                        sys.stdout = cStringIO.StringIO()
                        sys.stderr = sys.stdout
                        exec code in globs,locs
                        txt = ''
                        pipe.put(sys.stdout.getvalue() + '>>> ')
                    else:
                        pipe.put('... ')
                except:
                    txt='' # May be syntax err.
                    sys.stdout = cStringIO.StringIO()
                    sys.stderr = sys.stdout
                    traceback.print_exc()
                    pipe.put(sys.stdout.getvalue() + '>>> ')
        finally:
            sys.stdout = old_stdout # Restore redirected output.
            sys.stderr = old_stderr
            pipe.close()

    except Exception:  # Don't allow debug exceptions to propogate to real program.
        traceback.print_exc()
        
    if _raiseEx.ex is not None: raise _raiseEx.ex
    
def debug_process(pid):
    """Interrupt a running process and debug it."""
    os.kill(pid, signal.SIGUSR1)  # Signal process.
    pipe = NamedPipe(pipename(pid), 1)
    try:
        while pipe.is_open():
            txt=raw_input(pipe.get()) + '\n'
            pipe.put(txt)
    except EOFError:
        pass # Exit.
    pipe.close()

def listen():
    signal.signal(signal.SIGUSR1, remote_debug) # Register for remote debugging.

if __name__=='__main__':
    if len(sys.argv) != 2:
        print "Error: Must provide process id to debug"
    else:
        pid = int(sys.argv[1])
        debug_process(pid)
## end of http://code.activestate.com/recipes/576515/ }}}

########NEW FILE########
__FILENAME__ = run
import os
import sys
import socket
import logging.config
import traceback

import storm

LOG_CONFIG_FILE = 'logconfig.ini'

log_file_path = None
log_initialized = False
module_name = ''

def open_log():
    return open(log_file_path, 'a')

def handle_exception(type, value, tb):
    message = 'E_RUNFAILED_%s_%s_%d_%s' % (module_name,
                                        socket.gethostname(),
                                        os.getpid(),
                                        type.__name__)
    if log_initialized:
        log = logging.getLogger('petrel.run')
        log.error(message)
    storm.sendFailureMsgToParent(message)
   
    with open_log() as f:
        print >> f, 'Exception occurred in %s. Worker exiting.' % module_name
        f.write(''.join(traceback.format_exception(type, value, tb)))

def log_config():
    assert 'PETREL_LOG_PATH' in os.environ
    from subprocess import check_output
    
    # Set an environment variable that points to the Nimbus server.
    # logconfig.ini may use this to direct SysLogHandler to this machine.
    try:
        os.environ['NIMBUS_HOST'] = check_output(['storm', 'remoteconfvalue', 'nimbus.host']).split(':')[1].strip()
    except Exception as e:
        # It's not worth crashing if we can't set this.
        pass
    
    if os.path.exists(LOG_CONFIG_FILE):
        logging.config.fileConfig(LOG_CONFIG_FILE)

# This code is still a work in progress. It may have bugs that cause
# topologies to be unstable. I've seen it cause ShellSpout.querySubprocess()
# in Java to receive a JSONObject with a null "command" value.
class StormHandler(logging.Handler):
    def __init__(self, *l, **kw):
        super(StormHandler, self).__init__(*l, **kw)
        hostname = socket.gethostname().split('.')[0]
        script_name = os.getenv('SCRIPT') # Should be passed by setup_*.sh.
        if script_name is None:
            script_name = '<unknown>'
        process_id = os.getpid()
        self.format_string = '[%s][%s][%d] %%s' % (hostname, script_name, process_id)
    
    def emit(self, record):
        from petrel import storm
        msg = self.format(record)
        for line in msg.split('\n'):
            formatted_line = self.format_string % line
            #print >> sys.stderr, "Calling storm.log with: %s" % formatted_line
            storm.log('%s' % formatted_line)

# Comment this out until logging to Storm proves to be stable.
#logging.StormHandler = StormHandler

def main():
    if len(sys.argv) != 3:
        print >> sys.stderr, "Usage: %s <module> <log file>" % os.path.splitext(os.path.basename(sys.argv[0]))[0]
        sys.exit(1)

    try:
        global log_file_path, log_initialized, module_name
        os.environ['PETREL_LOG_PATH'] = log_file_path = os.path.abspath(sys.argv[2])
        os.environ['SCRIPT'] = module_name = sys.argv[1]
        sys.excepthook = handle_exception
    
        with open_log() as f:
            print >> f, '%s invoked with the following arguments: %s' % (sys.argv[0], repr(sys.argv[1:]))
            ver_info = sys.version_info
            print >> f, "python version: %d.%d.%d" % (ver_info.major, ver_info.minor, ver_info.micro)
            import getpass
            print >> f, 'user=%s' % getpass.getuser()
            print >> f, 'PATH=%s' % os.getenv('PATH')
            print >> f, 'LD_LIBRARY_PATH=%s' % os.getenv('LD_LIBRARY_PATH')
            print >> f, 'PYTHON_EGG_CACHE=%s' % os.getenv('PYTHON_EGG_CACHE')

        # Initialize logging. Redirect stderr to the log as well.
        log_config()
        log_initialized = True
        
        storm.initialize_profiling()
        
        sys.path[:0] = [ os.getcwd() ]
        module = __import__(module_name)
        getattr(module, 'run')()
        with open_log() as f:
            print >> f, 'Worker %s exiting normally.' % module_name
    except:
        # Here we explicitly catch exceptions from the worker. This is a "belt
        # and suspenders" approach in case our sys.excepthook gets overwritten
        # by another library.
        handle_exception(*sys.exc_info())

# When invoked as a main program, invoke Petrel on a spout or bolt module.
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = status
# Based on this code: http://tutorials.github.com/pages/retrieving-storm-data-from-nimbus.html
import datetime
from cStringIO import StringIO

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

import petrel.topologybuilder # Install the __hash__ monkeypatch
from petrel.generated.storm import Nimbus
from petrel.generated.storm.ttypes import *
from petrel.generated.storm.constants import *

def get_statistic(es, name):
    if hasattr(es, 'stats') and es.stats is not None:
        if es.component_id == '__acker':
            return sum(es.stats.specific.bolt.acked[':all-time'].values())
        elif hasattr(es.stats, name):
            tmp = getattr(es.stats, name).get(':all-time', {})
            if 'default' in tmp:
                return tmp['default']

    return '-'

def print_topology_status(client, topology, worker, port):
    records = []
    print 'id,uptime,host,port,component,emitted,transferred,acked,failed,num_errors'
    info = client.getTopologyInfo(topology.id)
    for i, es in enumerate(info.tasks):
        emit = True
        host = es.host.split('.')[0]
        if worker is not None and host != worker:
            emit = False
        if port is not None and es.port != port:
            emit = False
        
        if emit:
            record = {}
            record['columns'] = [
                es.task_id,
                es.uptime_secs,
                es.host.split('.')[0],
                es.port,
                es.component_id,
                get_statistic(es, 'emitted'),
                get_statistic(es, 'transferred'),
                get_statistic(es, 'acked'),
                get_statistic(es, 'failed'),
                len(es.errors)
            ]
            if len(es.errors):
                msg = StringIO()
                for i, e in enumerate(es.errors):
                    print >>msg, 'Error #%d (%s)' % (
                        i+1, (datetime.datetime.fromtimestamp(es.errors[i].error_time_secs).strftime('%Y/%m/%d %H:%M:%S')))
                    print >>msg
                    print >>msg, es.errors[i].error
                record['error'] = msg.getvalue()
                
            records.append(record)

    records.sort(key=lambda r: (r['columns'][0], r['columns'][1]))
    for record in records:
        print ', '.join(tuple(str(v) for v in record['columns']))
        if 'error' in record:
            print record['error']

def status(nimbus, topology, worker, port):
    socket      = TSocket.TSocket(nimbus, 6627)
    transport   = TTransport.TFramedTransport(socket)
    protocol    = TBinaryProtocol.TBinaryProtocol(transport)
    client      = Nimbus.Client(protocol)

    transport.open()
    try:
        summary = client.getClusterInfo()
        #print summary
        
        assert len(summary.topologies) == 1
        for running_topology in summary.topologies:
            if topology is None or topology == running_topology.name:
                print_topology_status(client, running_topology, worker, port)
    finally:
        transport.close()

########NEW FILE########
__FILENAME__ = storm
import sys
import os
import time
import socket
import logging
import traceback
from collections import deque

try:
    # Use simplejson instead of json because it is released more frequently and
    # is generally faster.
    import simplejson as json

    # However, if speedups are not installed, simplejson will be slow, so use
    # the built-in json instead.
    if json._import_c_make_encoder() is None:
        import json
except ImportError:
    import json

storm_log = logging.getLogger('storm')

TUPLE_PROFILING = False

json_encode = lambda x: json.dumps(x)
json_decode = lambda x: json.loads(x)

BLANK_LINE_CHECK = True

# Save old stdout so we can still write to it after redirecting.
old_stdout = sys.stdout

# TODO: Get this value from a topology configuration setting.
MAX_MESSAGE_SIZE = 16777216

class StormIPCException(Exception):
    pass

#reads lines and reconstructs newlines appropriately
def readMsg():
    def read_message_lines():
        if BLANK_LINE_CHECK:
            count_blank = 0
        i_line = 0
        message_size = 0
        while True:
            line = sys.stdin.readline()[0:-1]
            i_line += 1
            message_size += len(line)
            if line == "end":
                break
            # If message size exceeds MAX_MESSAGE_SIZE, we assume that the Storm
            # worker has died, and we would be reading an infinite series of blank
            # lines. Throw an error to halt processing, otherwise the task will
            # use 100% CPU and will quickly consume a huge amount of RAM.
            if MAX_MESSAGE_SIZE is not None and message_size > MAX_MESSAGE_SIZE:
                raise StormIPCException('Message exceeds MAX_MESSAGE_SIZE -- assuming this is an error')

            if BLANK_LINE_CHECK:
                if not line:
                    storm_log.debug('Message line #%d is blank. Pipe to Storm supervisor may be broken.', i_line)
                    count_blank += 1
                    if count_blank >= 20:
                        raise StormIPCException('Pipe to Storm supervisor seems to be broken!')
                if i_line > 100:
                    raise StormIPCException('Message exceeds 100 lines -- assuming this is an error')
                if count_blank > 0:
                    storm_log.debug('Message line #%d: %s', i_line + 1, line)
            yield line
    msg = ''.join('%s\n' % line for line in read_message_lines())
    return json_decode(msg)

MODE = None
ANCHOR_TUPLE = None

#queue up commands we read while trying to read taskids
pending_commands = deque()

def readTaskIds():
    if pending_taskids:
        return pending_taskids.popleft()
    else:
        msg = readMsg()
        while type(msg) is not list:
            pending_commands.append(msg)
            msg = readMsg()
        return msg

#queue up taskids we read while trying to read commands/tuples
pending_taskids = deque()

def readCommand():
    if pending_commands:
        return pending_commands.popleft()
    else:
        msg = readMsg()
        while type(msg) is list:
            pending_taskids.append(msg)
            msg = readMsg()
        return msg

def readTuple():
    cmd = readCommand()
    return Tuple(cmd["id"], cmd["comp"], cmd["stream"], cmd["task"], cmd["tuple"])

def sendMsgToParent(msg):
    print >> old_stdout, json_encode(msg)
    print >> old_stdout, "end"
    try:
        old_stdout.flush()
    except (IOError, OSError) as e:
        storm_log.exception(str(e))
        raise StormIPCException('%s error [Errno %d] in sendMsgToParent: %s' % (
            type(e).__name__,
            e.errno,
            str(e)))
    
# This function is probably obsolete with the addition of the new
# reportError() function.
# TODO: Consider getting rid of this function and call reportError() instead.
# However, need to consider the case where we are running on an older version
# of Storm where the Storm back end does not support reportError()? Can we
# detect that case and use this function instead?
def sendFailureMsgToParent(msg):
    """This function is kind of a hack, but useful when a Python task
    encounters a fatal exception. "msg" should be a simple string like
    "E_SPOUTFAILED". This function sends "msg" as-is to the Storm worker,
    which tries to parse it as JSON. The hacky aspect is that we
    *deliberately* make it fail by sending it non-JSON data. This causes
    the Storm worker to throw an error and restart the Python task. This
    is cleaner than simply letting the task die without notifying Storm,
    because this way Storm restarts the task more quickly."""
    assert isinstance(msg, basestring)
    print >> old_stdout, msg
    print >> old_stdout, "end"
    storm_log.error('Sent failure message ("%s") to Storm', msg)
    
def sync():
    sendMsgToParent({'command':'sync'})

def sendpid(heartbeatdir):
    pid = os.getpid()
    sendMsgToParent({'pid':pid})
    open(heartbeatdir + "/" + str(pid), "w").close()    

def emit(*args, **kwargs):
    result = __emit(*args, **kwargs)
    if result:
        return readTaskIds()

def emitMany(*args, **kwargs):
    """A more efficient way to emit a number of tuples at once."""
    global MODE
    if MODE == Bolt:
        emitManyBolt(*args, **kwargs)
    elif MODE == Spout:
        emitManySpout(*args, **kwargs)

def emitDirect(task, *args, **kwargs):
    kwargs["directTask"] = task
    __emit(*args, **kwargs)

def __emit(*args, **kwargs):
    global MODE
    if MODE == Bolt:
        return emitBolt(*args, **kwargs)
    elif MODE == Spout:
        return emitSpout(*args, **kwargs)

def emitManyBolt(tuples, stream=None, anchors = [], directTask=None):
    global ANCHOR_TUPLE
    if ANCHOR_TUPLE is not None:
        anchors = [ANCHOR_TUPLE]
    m = {
        "command": "emit",
        "anchors": [a.id for a in anchors],
        "tuple": None,
        "need_task_ids": False,
    }
    if stream is not None:
        m["stream"] = stream
    if directTask is not None:
        m["task"] = directTask
    
    lines = []
    for tup in tuples:
        m["tuple"] = tup
        lines.append(json_encode(m))
        lines.append('end')
    print >> old_stdout, '\n'.join(lines)

def emitBolt(tup, stream=None, anchors = [], directTask=None, need_task_ids=False):
    global ANCHOR_TUPLE
    if ANCHOR_TUPLE is not None:
        anchors = [ANCHOR_TUPLE]
    m = {
        "command": "emit",
        "anchors": [a.id for a in anchors],
        "tuple": tup,
        "need_task_ids": need_task_ids,
    }
    if stream is not None:
        m["stream"] = stream
    if directTask is not None:
        m["task"] = directTask
    sendMsgToParent(m)
    return need_task_ids
    
def emitManySpout(tuples, stream=None, id=None, directTask=None):
    m = {
        "command": "emit",
        "tuple": None,
        "need_task_ids": need_task_ids,
    }
    if id is not None:
        m["id"] = id
    if stream is not None:
        m["stream"] = stream
    if directTask is not None:
        m["task"] = directTask

    lines = []
    for tup in tuples:
        m["tuple"] = tup
        lines.append(json_encode(m))
        lines.append('end')
    print >> old_stdout, '\n'.join(lines)

def emitSpout(tup, stream=None, id=None, directTask=None, need_task_ids=False):
    m = {
        "command": "emit",
        "tuple": tup,
        "need_task_ids": need_task_ids,
    }
    if id is not None:
        m["id"] = id
    if stream is not None:
        m["stream"] = stream
    if directTask is not None:
        m["task"] = directTask
    sendMsgToParent(m)
    return need_task_ids

def ack(tup):
    """Acknowledge a tuple"""
    sendMsgToParent({"command": "ack", "id": tup.id})

def ackId(tupid):
    """Acknowledge a tuple when you only have its ID"""
    sendMsgToParent({"command": "ack", "id": tupid})

def fail(tup):
    """Fail a tuple"""
    sendMsgToParent({"command": "fail", "id": tup.id})

def reportError(msg):
    sendMsgToParent({"command": "error", "msg": msg})

def log(msg):
    sendMsgToParent({"command": "log", "msg": msg})

def initComponent():
    # Redirect stdout and stderr to logger instances. This is particularly
    # important for stdout so 'print' statements won't crash the Storm Java
    # worker.
    sys.stdout = LogStream(logging.getLogger('storm.stdout'))
    sys.stderr = LogStream(logging.getLogger('storm.stderr'))

    setupInfo = readMsg()
    storm_log.info('Task received setupInfo from Storm: %s', setupInfo)
    sendpid(setupInfo['pidDir'])
    storm_log.info('Task sent pid to Storm')
    return [setupInfo['conf'], setupInfo['context']]

class Tuple(object):
    __slots__ = ['id', 'component', 'stream', 'task', 'values']
    def __init__(self, id, component, stream, task, values):
        self.id = id
        self.component = component
        self.stream = stream
        self.task = task
        self.values = values

    def __eq__(self, other):
        if not isinstance(other, Tuple):
            return False
        
        for k in self.__slots__:
            if getattr(self, k) != getattr(other, k):
                return False
            
        return True

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return '<%s%s>' % (
                self.__class__.__name__,
                ''.join(' %s=%r' % (k, getattr(self, k)) for k in sorted(self.__slots__)))

class Task(object):
    def shared_initialize(self):
        conf, context = initComponent()
        
        # These values are only available with a patched version of Storm.
        self.task_index = context.get('taskIndex', -1)
        self.worker_port = context.get('workerPort', -1)
        
        self.initialize(conf, context)

    def report_exception(self, base_message, exception):
        parameters = (
            base_message,
            os.environ.get('SCRIPT', sys.argv[0]),
            socket.gethostname(),
            'pid', os.getpid(),
            'port', self.worker_port,
            'taskindex', self.task_index,
            type(exception).__name__,
            #str(exception),
        )
        #message = '%s: %s (pid %d) on %s failed with %s: %s' % parameters
        message = '__'.join(str(p).replace('.', '_') for p in parameters)
        sendFailureMsgToParent(message)
        
        # Sleep for a few seconds to try and ensure Storm reads this message
        # before we terminate. If it does, then our message above will appear in
        # the Storm UI.
        time.sleep(5)

class Bolt(Task):
    def __init__(self):
        if TUPLE_PROFILING:
            self.profiler = BoltProfiler()
        else:
            self.profiler = None

    def initialize(self, stormconf, context):
        pass

    def process(self, tuple):
        pass

    def run(self):
        global MODE
        MODE = Bolt
        self.shared_initialize()
        profiler = self.profiler
        try:
            while True:
                if profiler is not None: profiler.pre_read()
                tup = readTuple()
                if profiler is not None: profiler.post_read()
                self.process(tup)
                if profiler is not None: profiler.post_process()
        except Exception, e:
            self.report_exception('E_BOLTFAILED', e)
            storm_log.exception('Caught exception in Bolt.run')
            if 'tup' in locals():
                # Only print the first 2000 characters of the tuple, otherwise
                # the message may be too long for certain handlers (e.g.
                # SysLogHandler).
                storm_log.error(
                    'The error occurred while processing this tuple: %s',
                    repr(tup.values)[:2000])

class BasicBolt(Task):
    def __init__(self):
        if TUPLE_PROFILING:
            self.profiler = BasicBoltProfiler()
        else:
            self.profiler = None

    def initialize(self, stormconf, context):
        pass

    def process(self, tuple):
        pass

    def run(self):
        global MODE
        MODE = Bolt
        global ANCHOR_TUPLE
        self.shared_initialize()
        profiler = self.profiler
        try:
            while True:
                if profiler is not None: profiler.pre_read()
                tup = readTuple()
                if profiler is not None: profiler.post_read()
                ANCHOR_TUPLE = tup
                self.process(tup)
                if profiler is not None: profiler.post_process()
                ack(tup)
                if profiler is not None: profiler.post_ack()
        except Exception, e:
            self.report_exception('E_BOLTFAILED', e)
            storm_log.exception('Caught exception in BasicBolt.run')
            if 'tup' in locals():
                # Only print the first 2000 characters of the tuple, otherwise
                # I've seen errors because the message is too long for
                # SysLogHandler.
                storm_log.error(
                    'The error occurred while processing this tuple: %s',
                    repr(tup.values)[:2000])

class Spout(Task):
    def initialize(self, conf, context):
        pass

    def ack(self, id):
        pass

    def fail(self, id):
        pass

    def nextTuple(self):
        pass

    def run(self):
        global MODE
        MODE = Spout
        self.shared_initialize()
        try:
            while True:
                msg = readCommand()
                command = msg["command"]
                if command == "next":
                    self.nextTuple()
                elif command == "ack":
                    self.ack(msg["id"])
                elif command == "fail":
                    self.fail(msg["id"])
                sync()
        except Exception, e:
            self.report_exception('E_SPOUTFAILED', e)
            storm_log.exception('Caught exception in Spout.run: %s', str(e))

class BoltProfiler(object):
    """Helper class for Bolt. Implements some simple log-based counters for
    profiling performance."""
    MAX_COUNT = 1000

    def __init__(self):
        self.read_time = self.process_time = 0.0
        self.num_tuples = self.total_num_tuples = 0
        self.start_interval = None

    def pre_read(self):
        self.t1 = time.time()
        if self.start_interval is None:
            self.start_interval = self.t1

    def post_read(self):
        self.t2 = time.time()
        self.read_time += self.t2 - self.t1

    def post_process(self):
        self.t3 = time.time()
        self.process_time += self.t3 - self.t2

        self.num_tuples += 1
        if self.num_tuples % self.MAX_COUNT == 0 or self.t3 - self.start_interval > 1.0:
            self.total_num_tuples += self.num_tuples
            self.total_time = self.read_time + self.process_time
            storm_log.debug(
                'Bolt profile: total_num_tuples=%d, num_tuples=%d, avg_read_time=%f (%.1f%%), avg_process_time=%f (%.1f%%)',
                self.total_num_tuples,
                self.num_tuples,
                self.read_time / self.num_tuples, self.read_time / self.total_time * 100.0,
                self.process_time / self.num_tuples, self.process_time / self.total_time * 100.0)

            # Clear the timing data.
            self.start_interval = None
            self.num_tuples = 0
            self.read_time = self.process_time = 0.0

class BasicBoltProfiler(object):
    """Helper class for BasicBolt. Implements some simple log-based counters for
    profiling performance."""
    MAX_COUNT = 1000

    def __init__(self):
        self.read_time = self.process_time = self.ack_time = 0.0
        self.num_tuples = self.total_num_tuples = 0
        self.start_interval = None

    def pre_read(self):
        self.t1 = time.time()
        if self.start_interval is None:
            self.start_interval = self.t1

    def post_read(self):
        self.t2 = time.time()
        self.read_time += self.t2 - self.t1

    def post_process(self):
        self.t3 = time.time()
        self.process_time += self.t3 - self.t2

    def post_ack(self):
        self.t4 = time.time()
        self.ack_time += self.t4 - self.t3

        self.num_tuples += 1
        if self.num_tuples % self.MAX_COUNT == 0 or self.t4 - self.start_interval > 1.0:
            self.total_num_tuples += self.num_tuples
            self.total_time = self.read_time + self.process_time + self.ack_time
            storm_log.debug(
                'BasicBolt profile: total_num_tuples=%d, num_tuples=%d, avg_read_time=%f (%.1f%%), avg_process_time=%f (%.1f%%), avg_ack_time=%f (%.1f%%)',
                self.total_num_tuples,
                self.num_tuples,
                self.read_time / self.num_tuples, self.read_time / self.total_time * 100.0,
                self.process_time / self.num_tuples, self.process_time / self.total_time * 100.0,
                self.ack_time / self.num_tuples, self.ack_time / self.total_time * 100.0)

            # Clear the timing data.
            self.start_interval = None
            self.num_tuples = 0
            self.read_time = self.process_time = self.ack_time = 0.0

def initialize_profiling():
    global TUPLE_PROFILING
    TUPLE_PROFILING = storm_log.isEnabledFor(logging.DEBUG)
    if TUPLE_PROFILING:
        storm_log.info('Tuple profiling enabled. Will log tuple processing times.')
    else:
        storm_log.info('Tuple profiling NOT enabled. Will not log tuple processing times.')

class LogStream(object):
    """Object that implements enough of the Python stream API to be used as
    sys.stdout and sys.stderr. Messages are written to the Python logger.
    """
    def __init__(self, logger):
        self.logger = logger
 
    def write(self, message):
        for line in message.split('\n'):
            self.logger.error(line)

########NEW FILE########
__FILENAME__ = test_topology
import unittest
from cStringIO import StringIO

from petrel.topologybuilder import TopologyBuilder
from petrel.emitter import Spout, BasicBolt

from petrel.generated.storm.ttypes import Bolt, SpoutSpec

class RandomSentenceSpout(Spout):
    def __init__(self, execution_command=None):
        super(RandomSentenceSpout, self).__init__(script='randomsentence.py')

    def declareOutputFields(self):
        return ['sentence']

class SplitSentence(BasicBolt):
    def __init__(self, execution_command=None):
        super(SplitSentence, self).__init__(script='splitsentence.py')

    def declareOutputFields(self):
        return ['word']

class WordCount(BasicBolt):
    def __init__(self, execution_command=None):
        super(WordCount, self).__init__(script='wordcount.py')

    def declareOutputFields(self):
        return ['word', 'count']

class TestTopology(unittest.TestCase):
    def test1(self):
        # Build a topology
        builder = TopologyBuilder()
        builder.setSpout("spout", RandomSentenceSpout(), 5)
        builder.setBolt("split", SplitSentence(), 8).shuffleGrouping("spout")
        builder.setBolt("count", WordCount(), 12).fieldsGrouping("split", ["word"])

        # Save the topology.        
        io_out = StringIO()
        builder.write(io_out)
        
        # Read the topology.
        io_in = StringIO(io_out.getvalue())
        topology = builder.read(io_in)
        
        # Verify the topology settings were saved and loaded correctly.
        self.assertEqual(['spout'], topology.spouts.keys())
        self.assertEqual(['count', 'split'], sorted(topology.bolts.keys()))

        spout = topology.spouts['spout']
        self.assertEqual('python2.7', spout.spout_object.shell.execution_command)
        self.assertEqual('randomsentence.py', spout.spout_object.shell.script)
        self.assertEqual(['default'], sorted(spout.common.streams.keys()))
        self.assertEqual(['sentence'], spout.common.streams['default'].output_fields)
        self.assertEqual(False, spout.common.streams['default'].direct)

        bolt = topology.bolts['split']
        self.assertEqual('python2.7', bolt.bolt_object.shell.execution_command)
        self.assertEqual('splitsentence.py', bolt.bolt_object.shell.script)
        self.assertEqual(['default'], sorted(bolt.common.streams.keys()))
        self.assertEqual(['word'], bolt.common.streams['default'].output_fields)
        self.assertEqual(False, bolt.common.streams['default'].direct)

        bolt = topology.bolts['count']
        self.assertEqual('python2.7', bolt.bolt_object.shell.execution_command)
        self.assertEqual('wordcount.py', bolt.bolt_object.shell.script)
        self.assertEqual(['default'], sorted(bolt.common.streams.keys()))
        self.assertEqual(['word', 'count'], bolt.common.streams['default'].output_fields)
        self.assertEqual(False, bolt.common.streams['default'].direct)

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = topologybuilder
import json

from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from petrel.generated.storm.ttypes import ComponentCommon, Grouping, NullStruct, GlobalStreamId
from petrel.generated.storm.ttypes import StreamInfo, Bolt, SpoutSpec, ShellComponent
from petrel.generated.storm.ttypes import ComponentObject, StormTopology

# Storm uses GlobalStreamId as a dict key, but the Thrift Python binding doesn't
# support this. As a simple workaround, add a hash function that always returns
# 0. The resulting map won't be efficient at storing large amounts of data, but
# it should work in all cases.
# https://issues.apache.org/jira/browse/THRIFT-162.
assert not hasattr(GlobalStreamId, '__hash__')
GlobalStreamId.__hash__ = lambda self: 0

##########################################################################

class TopologyBuilder(object):
    def __init__(self):
        self._bolts = {}
        self._spouts = {}
        self._commons = {}
    
    #/**
    # * Define a new bolt in this topology with the specified amount of parallelism.
    # *
    # * @param id the id of this component. This id is referenced by other components that want to consume this bolt's outputs.
    # * @param bolt the bolt
    # * @param parallelism_hint the number of tasks that should be assigned to execute this bolt. Each task will run on a thread in a process somewhere around the cluster.
    # * @return use the returned object to declare the inputs to this component
    # */
    def setBolt(self, id, bolt, parallelism_hint=None):
        self._validateUnusedId(id);
        self._initCommon(id, bolt, parallelism_hint);
        self._bolts[id] = bolt

        return _BoltGetter(self, id)

    #/**
    # * Define a new spout in this topology.
    # *
    # * @param id the id of this component. This id is referenced by other components that want to consume this spout's outputs.
    # * @param spout the spout
    # */
    def setSpout(self, id, spout, parallelism_hint=None):
        self._validateUnusedId(id);
        self._initCommon(id, spout, parallelism_hint);
        self._spouts[id] = spout

    def addOutputStream(self, id, streamId, output_fields, direct=False):
        self._commons[id].streams[streamId] = StreamInfo(output_fields, direct=direct)

    def createTopology(self):
        boltSpecs = {}
        spoutSpecs = {}
        for boltId, bolt in self._bolts.iteritems():
            t_bolt = Bolt()
            shell_object = ShellComponent()
            shell_object.execution_command = bolt.execution_command
            shell_object.script = bolt.script
            t_bolt.bolt_object = ComponentObject()
            t_bolt.bolt_object.shell = shell_object
            t_bolt.common = self._getComponentCommon(boltId, bolt)
            boltSpecs[boltId] = t_bolt

        for spoutId, spout in self._spouts.iteritems():
            spout_spec = SpoutSpec()
            shell_object = ShellComponent()
            shell_object.execution_command = spout.execution_command
            shell_object.script = spout.script
            spout_spec.spout_object = ComponentObject()
            spout_spec.spout_object.shell = shell_object
            spout_spec.common = self._getComponentCommon(spoutId, spout)
            spoutSpecs[spoutId] = spout_spec

        topology = StormTopology()
        topology.spouts = spoutSpecs
        topology.bolts = boltSpecs
        topology.state_spouts = {} # Not supported yet, I think
        return topology

    def write(self, stream):
        """Writes the topology to a stream or file."""
        topology = self.createTopology()
        def write_it(stream):
            transportOut = TTransport.TMemoryBuffer()
            protocolOut = TBinaryProtocol.TBinaryProtocol(transportOut)
            topology.write(protocolOut)
            bytes = transportOut.getvalue()
            stream.write(bytes)

        if isinstance(stream, basestring):
            with open(stream, 'wb') as f:
                write_it(f)
        else:
            write_it(stream)
            
        return topology

    def read(self, stream):
        """Reads the topology from a stream or file."""
        def read_it(stream):
            bytes = stream.read()
            transportIn = TTransport.TMemoryBuffer(bytes)
            protocolIn = TBinaryProtocol.TBinaryProtocol(transportIn)
            topology = StormTopology()
            topology.read(protocolIn)
            return topology
            
        if isinstance(stream, basestring):
            with open(stream, 'rb') as f:
                return read_it(f)
        else:
            return read_it(stream)

    def _validateUnusedId(self, id):
        if id in self._bolts:
            raise KeyError("Bolt has already been declared for id " + id);
        elif id in self._spouts:
            raise KeyError("Spout has already been declared for id " + id);

    def _getComponentCommon(self, id, component):
        common = self._commons[id]
        stream_info = StreamInfo()
        stream_info.output_fields = component.declareOutputFields()
        stream_info.direct = False # Appears to be unused by Storm
        common.streams['default'] = stream_info
        
        return common

    def _initCommon(self, id, component, parallelism):
        common = ComponentCommon()
        
        common.inputs = {}
        common.streams = {}
        if parallelism is not None:
            common.parallelism_hint = parallelism
        conf = component.getComponentConfiguration()
        if conf is not None:
            common.json_conf = json.dumps(conf)
        self._commons[id] = common

class _BoltGetter(object):
    def __init__(self, owner, boltId):
        self._owner = owner
        self._boltId = boltId

    def allGrouping(self, componentId, streamId='default'):
        return self.grouping(componentId, 'all', NullStruct(), streamId)

    def fieldsGrouping(self, componentId, fields, streamId='default'):
        return self.grouping(componentId, 'fields', fields, streamId)

    def globalGrouping(self, componentId, streamId='default'):
        return self.fieldsGrouping(componentId, [], streamId)

    def shuffleGrouping(self, componentId, streamId='default'):
        return self.grouping(componentId, 'shuffle', NullStruct(), streamId)

    def localOrShuffleGrouping(self, componentId, streamId='default'):
        return self.grouping(componentId, 'local_or_shuffle', NullStruct(), streamId)

    def noneGrouping(self, componentId, streamId='default'):
        return self.grouping(componentId, 'none', NullStruct(), streamId)

    def directGrouping(self, componentId, streamId='default'):
        return self.grouping(componentId, 'direct', NullStruct(), streamId)

    def grouping(self, componentId, attr, grouping, streamId):
        o_grouping = Grouping()
        setattr(o_grouping, attr, grouping)
        self._owner._commons[self._boltId].inputs[GlobalStreamId(componentId, streamId)] = o_grouping
        return self

########NEW FILE########
__FILENAME__ = util
import os

import yaml

def read_yaml(config):
    if os.path.exists(config):
        with open(config, 'r') as f:
            return yaml.load(f)
    else:
        raise Exception("Config file %s does not exist" % config)

########NEW FILE########
__FILENAME__ = create
import randomsentence
import splitsentence
import wordcount

def create(builder):
    builder.setSpout("spout", randomsentence.RandomSentenceSpout(), 1)
    builder.setBolt("split", splitsentence.SplitSentenceBolt(), 1).shuffleGrouping("spout")
    builder.setBolt("count", wordcount.WordCountBolt(), 1).fieldsGrouping("split", ["word"])

########NEW FILE########
__FILENAME__ = randomsentence
import time
import random
import logging

from petrel import storm
from petrel.emitter import Spout

log = logging.getLogger('randomsentence')

log.debug('randomsentence loading')

class RandomSentenceSpout(Spout):
    def __init__(self):
        super(RandomSentenceSpout, self).__init__(script=__file__)
        #self._index = 0

    @classmethod
    def declareOutputFields(cls):
        return ['sentence']

    sentences = [
        "the cow jumped over the moon",
        "an apple a day keeps the doctor away",
        "four score and seven years ago",
        "snow white and the seven dwarfs",
        "i am at two with nature"
    ]
        
    def nextTuple(self):
        #if self._index == len(self.sentences):
        #    # This is just a demo; keep sleeping and returning None after we run
        #    # out of data. We can't just sleep forever or Storm will hang.
        #    time.sleep(1)
        #    return None

        time.sleep(0.25);
        sentence = self.sentences[random.randint(0, len(self.sentences) - 1)]
        #sentence = self.sentences[self._index]
        #self._index += 1
        log.debug('randomsentence emitting: %s', sentence)
        storm.emit([sentence])

# TODO: Revisit this. Currently the spout runs forever, so it's not suitable
# for run_simple_topology(). We could modify the spout so it stops after
# emitting 'n' tuples.
#def test():
#    # To run this:
#    # pip install nose
#    # nosetests wordcount.py
#    from nose.tools import assert_true
#    from petrel import mock
#    spout = RandomSentenceSpout()
#    result = mock.run_simple_topology(None, [spout])
#    assert_true(isinstance(result[spout][0].sentence, str))

def run():
    RandomSentenceSpout().run()

########NEW FILE########
__FILENAME__ = splitsentence
import logging

from petrel import storm
from petrel.emitter import BasicBolt

log = logging.getLogger('splitsentence')

log.debug('splitsentence loading')

class SplitSentenceBolt(BasicBolt):
    def __init__(self):
        super(SplitSentenceBolt, self).__init__(script=__file__)

    def declareOutputFields(self):
        return ['word']

    def process(self, tup):
        log.debug('SplitSentenceBolt.process() called with: %s', tup)
        words = tup.values[0].split(" ")
        for word in words:
          log.debug('SplitSentenceBolt.process() emitting: %s', word)
          storm.emit([word])

def test():
    # To run this:
    # pip install nose
    # nosetests splitsentence.py
    from nose.tools import assert_equal
    bolt = SplitSentenceBolt()
    from petrel import mock
    from randomsentence import RandomSentenceSpout
    mock_spout = mock.MockSpout(RandomSentenceSpout.declareOutputFields(), [
        ["Madam, I'm Adam."],
    ])
    
    result = mock.run_simple_topology(None, [mock_spout, bolt], result_type=mock.LIST)
    assert_equal([['Madam,'], ["I'm"], ['Adam.']], result[bolt])

def run():
    SplitSentenceBolt().run()

########NEW FILE########
__FILENAME__ = wordcount
import logging
from collections import defaultdict

from petrel import storm
from petrel.emitter import BasicBolt

log = logging.getLogger('wordcount')

log.debug('wordcount loading')

class WordCountBolt(BasicBolt):
    def __init__(self):
        super(WordCountBolt, self).__init__(script='wordcount.py')
        self._count = defaultdict(int)

    @classmethod
    def declareOutputFields(cls):
        return ['word', 'count']

    def process(self, tup):
        log.debug('WordCountBolt.process() called with: %s', tup)
        word = tup.values[0]
        self._count[word] += 1
        log.debug('WordCountBolt.process() emitting: %s', [word, self._count[word]])
        storm.emit([word, self._count[word]])

def test():
    # To run this:
    # pip install nose
    # nosetests wordcount.py
    from nose.tools import assert_equal
    
    bolt = WordCountBolt()
    
    from petrel import mock
    from randomsentence import RandomSentenceSpout
    mock_spout = mock.MockSpout(RandomSentenceSpout.declareOutputFields(), [
        ['word'],
        ['other'],
        ['word'],
    ])
    
    result = mock.run_simple_topology(None, [mock_spout, bolt], result_type=mock.LIST)
    assert_equal(2, bolt._count['word'])
    assert_equal(1, bolt._count['other'])
    assert_equal([['word', 1], ['other', 1], ['word', 2]], result[bolt])

def run():
    WordCountBolt().run()

########NEW FILE########
