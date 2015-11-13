__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

# parsing arguments
parser = OptionParser(
    'This is a custom version of the zc.buildout %prog script.  It is '
    'intended to meet a temporary need if you encounter problems with '
    'the zc.buildout 1.5 release.')
parser.add_option("-v", "--version", dest="version", default='1.4.4',
                          help='Use a specific zc.buildout version.  *This '
                          'bootstrap script defaults to '
                          '1.4.4, unlike usual buildpout bootstrap scripts.*')
parser.add_option("-d", "--distribute",
                   action="store_true", dest="distribute", default=False,
                   help="Use Disribute rather than Setuptools.")

parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.version is not None:
    VERSION = '==%s' % options.version
else:
    VERSION = ''

USE_DISTRIBUTE = options.distribute
args = args + ['bootstrap']

to_reload = False
try:
    import pkg_resources
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}
    if USE_DISTRIBUTE:
        exec urllib2.urlopen('http://python-distribute.org/distribute_setup.py'
                         ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0, no_fake=True)
    else:
        exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                             ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

ws  = pkg_resources.working_set

if USE_DISTRIBUTE:
    requirement = 'distribute'
else:
    requirement = 'setuptools'

env = dict(os.environ,
           PYTHONPATH=
           ws.find(pkg_resources.Requirement.parse(requirement)).location
           )

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(tmpeggs)]

if 'bootstrap-testing-find-links' in os.environ:
    cmd.extend(['-f', os.environ['bootstrap-testing-find-links']])

cmd.append('zc.buildout' + VERSION)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else: # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
assert exitcode == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = common
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import re

from dumbo.util import incrcounter, setstatus, configopts

class Params(object):
    """
    >>> os.environ["hi"] = "world"
    >>> p = Params()
    >>> "hi" in p
    True
    >>> p["hi"] == "world"
    True
    >>> p.get("hi") == "world"
    True
    >>> p.get("hello", "dumbo") == "dumbo"
    True
    >>>
    """
    def get(self, name, default=None): 
        try:
            return os.environ[name]
        except KeyError:
            return default

    def __getitem__(self, key):
        return self.get(str(key))

    def __contains__(self, key):
        return self.get(str(key)) is not None


class Counter(object):

    def __init__(self, name, group='Program'):
        self.group = group
        self.name = name

    def incr(self, amount):
        incrcounter(self.group, self.name, amount)
        return self
    __iadd__ = incr


class Counters(object):
    
    def __init__(self):
        self.counters = {}

    def __getitem__(self, key):
        try:
            return self.counters[key]
        except KeyError:
            counter = Counter(str(key))
            self.counters[key] = counter
            return counter

    def __setitem__(self, key, value):
        pass


class MapRedBase(object):
    
    params = Params()
    counters = Counters()

    getparam = params.get
    
    def setstatus(self, msg):
        setstatus(msg)
    status = property(fset=setstatus)


class JoinKey(object):

    def __init__(self, body, isprimary=False):
        self.body = body
        self.isprimary = isprimary
  
    def __cmp__(self, other):
        if isinstance(other, JoinKey):
            # For isprimary, order is switched because we want True to sort before False
            return cmp(self.body, other.body) or cmp(other.isprimary, self.isprimary)
        else:
            return -1     # JoinKeys arbitrarily come before everything else

    @classmethod
    def fromjoinkey(cls, jk):
        return cls(jk.body, jk.isprimary)

    @classmethod
    def fromdump(cls, dump):
        return cls(dump[0], dump[1] == 1)

    def dump(self):
        return (self.body, 2 - int(self.isprimary))

    def __repr__(self):
        return repr(self.dump())


class RunInfo(object):

    def get_input_path(self):
        return 'unknown'


class Iteration(object):

    def __init__(self, prog, opts):
        (self.prog, self.opts) = (prog, opts)

    def run(self):
        opts = self.opts
        attrs = ['fake', 'debug', 'python', 'iteration', 'itercount', 'hadoop', 
            'starter', 'name', 'memlimit', 'param', 'parser', 'record', 
            'joinkeys', 'hadoopconf', 'mapper', 'reducer']
        addedopts = opts.filter(attrs)
        opts.remove(*attrs)

        if 'yes' in addedopts['fake']:
            def dummysystem(*args, **kwargs):
                return 0
            global system
            system = dummysystem  # not very clean, but it works...
        if 'yes' in addedopts['debug']:
            opts.add('cmdenv', 'dumbo_debug=yes')
        if not addedopts['python']:
            python = 'python'
        else:
            python = addedopts['python'][0]
        opts.add('python', python)
        if not addedopts['iteration']:
            iter = 0
        else:
            iter = int(addedopts['iteration'][0])
        if not addedopts['itercount']:
            itercnt = 1
        else:
            itercnt = int(addedopts['itercount'][0])
        if addedopts['name']:
            name = addedopts['name'][0]
        else:
            name = self.prog.split('/')[-1]
        opts.add('name', '%s (%s/%s)' % (name, iter + 1, itercnt))
        if not addedopts['hadoop']:
            pypath = '/'.join(self.prog.split('/')[:-1])
            if pypath:
                opts.add('pypath', pypath)
        else:
            opts.add('hadoop', addedopts['hadoop'][0])
        progmod = self.prog.split('/')[-1]
        progmod = progmod[:-3] if progmod.endswith('.py') else progmod
        memlim = ' 262144000'  # 250MB limit by default
        if addedopts['memlimit']:
            # Limit amount of memory. This supports syntax 
            # of the form '256m', '12g' etc.
            try:
                _memlim = int(addedopts['memlimit'][0][:-1])
                memlim = ' %i' % {
                    'g': 1073741824    * _memlim,
                    'm': 1048576       * _memlim,
                    'k': 1024          * _memlim,
                    'b': 1             * _memlim,
                }[addedopts['memlimit'][0][-1].lower()]
            except KeyError:
                # Assume specified in bytes by default
                memlim = ' ' + addedopts['memlimit'][0]

        if addedopts['mapper']:
            opts.add('mapper', addedopts['mapper'][0])
        else:
            opts.add('mapper', '%s -m %s map %i%s' % (python, progmod, iter, 
                memlim))
        if addedopts['reducer']:
            opts.add('reducer', addedopts['reducer'][0])
        else:
            opts.add('reducer', '%s -m %s red %i%s' % (python, progmod, 
                iter, memlim))
        for param in addedopts['param']:
            opts.add('cmdenv', param)
        if addedopts['parser'] and iter == 0:
            parser = addedopts['parser'][0]
            shortcuts = dict(configopts('parsers', self.prog))
            if parser in shortcuts:
                parser = shortcuts[parser]
            opts.add('cmdenv', 'dumbo_parser=' + parser)
        if addedopts['record'] and iter == 0:
            record = addedopts['record'][0]
            shortcuts = dict(configopts('records', self.prog))
            if record in shortcuts:
                record = shortcuts[record]
            opts.add('cmdenv', 'dumbo_record=' + record)
        if 'yes' in addedopts['joinkeys']:
            opts.add('cmdenv', 'dumbo_joinkeys=yes')
            opts.add('partitioner', 'org.apache.hadoop.mapred.lib.BinaryPartitioner')
            opts.add('jobconf', 'mapred.binary.partitioner.right.offset=-6')
        for hadoopconf in addedopts['hadoopconf']:
            opts.add('jobconf', hadoopconf)
        opts.add('libegg', re.sub('\.egg.*$', '.egg', __file__))
        return 0


class FileSystem(object):
    
    def cat(self, path, opts):
        return 1  # fail by default
    
    def ls(self, path, opts):
        return 1  # fail by default
    
    def exists(self, path, opts):
        return 1  # fail by default
    
    def rm(self, path, opts):
        return 1  # fail by default
    
    def put(self, path1, path2, opts):
        return 1  # fail by default
    
    def get(self, path1, path2, opts):
        return 1  # fail by default


class Backend(object):
    
    def matches(self, opts):
        """ Returns True if the backend matches with the given opts """ 
        return True

    #abstractmethod
    def create_iteration(self, opts):
        """ Creates a suitable Iteration object """
        pass
    
    #abstractmethod
    def create_filesystem(self, opts):
        """ Creates a suitable FileSystem object """
        pass

    def get_mapredbase_class(self, opts):
        """ Returns a suitable MapRedBase class """
        return MapRedBase
    
    def get_joinkey_class(self, opts):
        """ Returns a suitable JoinKey class """
        return JoinKey

    def get_runinfo_class(self, opts):
        """ Returns a suitable RunInfo class """
        return RunInfo

########NEW FILE########
__FILENAME__ = streaming
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import re

from dumbo.backends.common import Backend, Iteration, FileSystem, RunInfo
from dumbo.util import (configopts, envdef, execute, findhadoop, findjar,
        dumpcode, dumptext, Options)


class StreamingBackend(Backend):
    
    def matches(self, opts):
        return bool(opts['hadoop'])
        
    def create_iteration(self, opts):
        return StreamingIteration(opts.pop('prog')[0], opts)

    def create_filesystem(self, opts):
        return StreamingFileSystem(findhadoop(opts['hadoop'][0]))

    def get_runinfo_class(self, opts):
        return StreamingRunInfo


class StreamingIteration(Iteration):

    def __init__(self, prog, opts):
        Iteration.__init__(self, prog, opts)
        self.opts += Options(configopts('streaming', prog, self.opts))
        hadoop_streaming = 'streaming_%s' % self.opts['hadoop'][0]
        self.opts += Options(configopts(hadoop_streaming, prog, self.opts))

    def run(self):
        retval = Iteration.run(self)
        if retval != 0:
            return retval
        opts = self.opts
        if os.path.exists(self.prog):
            opts.add('file', self.prog)

        keys = ['hadoop', 'name', 'delinputs', 'libegg', 'libjar',
            'inputformat', 'outputformat', 'nummaptasks', 'numreducetasks',
            'priority', 'queue', 'cachefile', 'cachearchive', 'file',
            'codewritable', 'addpath', 'getpath', 'python', 'streamoutput',
            'pypath', 'hadooplib']
        addedopts = opts.filter(keys)
        opts.remove(*keys)

        hadoop = findhadoop(addedopts['hadoop'][0])
        streamingjar = findjar(hadoop, 'streaming', addedopts['hadooplib'])
        if not streamingjar:
            print >> sys.stderr, 'ERROR: Streaming jar not found'
            return 1

        try:
            import typedbytes
        except ImportError:
            print >> sys.stderr, 'ERROR: "typedbytes" module not found'
            return 1
        modpath = re.sub('\.egg.*$', '.egg', typedbytes.__file__)
        if modpath.endswith('.egg'):
            addedopts.add('libegg', modpath)
        else:
            opts.add('file', 'file://%s' % os.path.abspath(modpath))
        opts.add('jobconf', 'stream.map.input=typedbytes')
        opts.add('jobconf', 'stream.reduce.input=typedbytes')

        if addedopts['numreducetasks'] and addedopts['numreducetasks'][0] == '0':
            opts.add('jobconf', 'stream.reduce.output=typedbytes')
            if addedopts['streamoutput']:
                id_ = addedopts['streamoutput'][0]
                opts.add('jobconf', 'stream.map.output=' + id_)
            else:
                opts.add('jobconf', 'stream.map.output=typedbytes')
        else:
            opts.add('jobconf', 'stream.map.output=typedbytes')
            if addedopts['streamoutput']:
                id_ = addedopts['streamoutput'][0]
                opts.add('jobconf', 'stream.reduce.output=' + id_)
            else:
                opts.add('jobconf', 'stream.reduce.output=typedbytes')

        progname = self.prog.split('/')[-1] if not addedopts['name'] \
                                            else addedopts['name'][0]
        opts.add('jobconf', 'mapred.job.name=%s' % progname)

        nummaptasks = addedopts['nummaptasks']
        numreducetasks = addedopts['numreducetasks']
        if nummaptasks:
            opts.add('jobconf', 'mapred.map.tasks=%s' % nummaptasks[0])
        if numreducetasks:
            opts.add('numReduceTasks', numreducetasks[0])
        if addedopts['priority']:
            opts.add('jobconf', 'mapred.job.priority=%s' % addedopts['priority'][0])
        if addedopts['queue']:
            opts.add('jobconf', 'mapred.job.queue.name=%s' % addedopts['queue'][0])

        for cachefile in addedopts['cachefile']:
            opts.add('cacheFile', cachefile)

        for cachearchive in addedopts['cachearchive']:
            opts.add('cacheArchive', cachearchive)

        for _file in addedopts['file']:
            if not '://' in _file:
                if not os.path.exists(_file):
                    raise ValueError('file "%s" does not exist' % _file)
                _file = 'file://%s' % os.path.abspath(_file)
            opts.add('file', _file)

        if not addedopts['inputformat']:
            addedopts.add('inputformat', 'auto')

        inputformat_shortcuts = {
            'code': 'org.apache.hadoop.streaming.AutoInputFormat',
            'text': 'org.apache.hadoop.mapred.TextInputFormat',
            'sequencefile': 'org.apache.hadoop.streaming.AutoInputFormat',
            'auto': 'org.apache.hadoop.streaming.AutoInputFormat'
        }
        inputformat_shortcuts.update(configopts('inputformats', self.prog))

        inputformat = addedopts['inputformat'][0]
        if inputformat.lower() in inputformat_shortcuts:
            inputformat = inputformat_shortcuts[inputformat.lower()]
        opts.add('inputformat', inputformat)

        if not addedopts['outputformat']:
            addedopts.add('outputformat', 'sequencefile')

        if addedopts['getpath'] and 'no' not in addedopts['getpath']:
            outputformat_shortcuts = {
                'code': 'fm.last.feathers.output.MultipleSequenceFiles',
                'text': 'fm.last.feathers.output.MultipleTextFiles',
                'raw': 'fm.last.feathers.output.MultipleRawFileOutputFormat',
                'sequencefile': 'fm.last.feathers.output.MultipleSequenceFiles'
            }
        else:
            outputformat_shortcuts = {
                'code': 'org.apache.hadoop.mapred.SequenceFileOutputFormat',
                'text': 'org.apache.hadoop.mapred.TextOutputFormat',
                'raw': 'fm.last.feathers.output.RawFileOutputFormat',
                'sequencefile': 'org.apache.hadoop.mapred.SequenceFileOutputFormat'
            }
        outputformat_shortcuts.update(configopts('outputformats', self.prog))

        outputformat = addedopts['outputformat'][0]
        if outputformat.lower() in outputformat_shortcuts:
            outputformat = outputformat_shortcuts[outputformat.lower()]
        opts.add('outputformat', outputformat)

        if addedopts['addpath'] and 'no' not in addedopts['addpath']:
            opts.add('cmdenv', 'dumbo_addpath=true')

        pyenv = envdef('PYTHONPATH', addedopts['libegg'], 'file', self.opts,
            shortcuts=dict(configopts('eggs', self.prog)), quote=False, trim=True,
            extrapaths=addedopts['pypath'])
        if pyenv:
            opts.add('cmdenv', pyenv)

        hadenv = envdef('HADOOP_CLASSPATH', addedopts['libjar'], 'libjar',
            self.opts, shortcuts=dict(configopts('jars', self.prog)))

        tmpfiles = []
        for _file in opts.pop('file'):
            if _file.startswith('file://'):
                opts.add('file', _file[7:])
            else:
                tmpfiles.append(_file)
        if tmpfiles:
            opts.add('jobconf', 'tmpfiles=%s' % ','.join(tmpfiles))

        tmpjars = []
        for jar in opts.pop('libjar'):
            if jar.startswith('file://'):
                opts.add('file', jar[7:])
            else:
                tmpjars.append(jar)
        if tmpjars:
            opts.add('jobconf', 'tmpjars=%s' % ','.join(tmpjars))

        cmd = hadoop + '/bin/hadoop jar ' + streamingjar
        retval = execute(cmd, opts, hadenv)

        if 'yes' in addedopts['delinputs']:
            inputs = opts['input']
            for path in inputs:
                execute("%s/bin/hadoop fs -rmr '%s'" % (hadoop, path))
        return retval

class StreamingFileSystem(FileSystem):
    
    def __init__(self, hadoop):
        self.hadoop = hadoop
        self.hdfs = hadoop + '/bin/hadoop fs'
    
    def cat(self, path, opts):
        streamingjar = findjar(self.hadoop, 'streaming',
                               opts['hadooplib'] if 'hadooplib' in opts else None)
        if not streamingjar:
            print >> sys.stderr, 'ERROR: Streaming jar not found'
            return 1
        hadenv = envdef('HADOOP_CLASSPATH', opts['libjar'],
            shortcuts=dict(configopts('jars')))
        try:
            import typedbytes

            if "combined" in opts and opts["combined"][0] == "yes":
                subpaths = [path]
            else:
                ls = os.popen('%s %s -ls %s' % (hadenv, self.hdfs, path))
                subpaths = [line.split()[-1] for line in ls if ":" in line]
                ls.close()

            for subpath in subpaths:
                if subpath.split("/")[-1].startswith("_"):
                    continue
                dumptb = os.popen('%s %s/bin/hadoop jar %s dumptb %s 2> /dev/null'
                                  % (hadenv, self.hadoop, streamingjar, subpath))

                dump = dumpcode if 'yes' in opts['ascode'] else dumptext
                outputs = dump(typedbytes.PairedInput(dumptb))

                for output in outputs:
                    print '\t'.join(output)
                dumptb.close()
        except IOError:
            pass  # ignore
        return 0
    
    def ls(self, path, opts):
        return execute("%s -ls '%s'" % (self.hdfs, path),
                       printcmd=False)
    
    def exists(self, path, opts):
        shellcmd = "%s -stat '%s' >/dev/null 2>&1"
        return 1 - int(execute(shellcmd % (self.hdfs, path), printcmd=False) == 0)
    
    def rm(self, path, opts):
        return execute("%s -rmr '%s'" % (self.hdfs, path),
                       printcmd=False)
    
    def put(self, path1, path2, opts):
        return execute("%s -put '%s' '%s'" % (self.hdfs, path1,
                       path2), printcmd=False)
    
    def get(self, path1, path2, opts):
        return execute("%s -get '%s' '%s'" % (self.hdfs, path1,
                       path2), printcmd=False)


class StreamingRunInfo(RunInfo):

    def get_input_path(self):
        if os.environ.has_key('mapreduce_map_input_file'):
            return os.environ['mapreduce_map_input_file']
        return os.environ['map_input_file']

########NEW FILE########
__FILENAME__ = unix
'''
Created on 26 Jul 2010

@author: klaas
'''

import sys
import operator

from dumbo.backends.common import Backend, Iteration, FileSystem
from dumbo.util import configopts, envdef, execute, Options
from dumbo.cmd import decodepipe


class UnixBackend(Backend):

    def matches(self, opts):
        return True  # always matches, but it's last in the list

    def create_iteration(self, opts):
        return UnixIteration(opts['prog'][0], opts)

    def create_filesystem(self, opts):
        return UnixFileSystem()


class UnixIteration(Iteration):

    def __init__(self, prog, opts):
        Iteration.__init__(self, prog, opts)
        self.opts += Options(configopts('unix', prog, self.opts))

    def run(self):
        retval = Iteration.run(self)
        if retval != 0:
            return retval

        opts = self.opts
        keys = ['input', 'output', 'mapper', 'reducer', 'libegg', 'delinputs',
            'cmdenv', 'pv', 'addpath', 'inputformat', 'outputformat',
            'numreducetasks', 'python', 'pypath', 'sorttmpdir', 'sortbufsize']
        addedopts = opts.filter(keys)
        opts.remove(*keys)

        mapper, reducer = addedopts['mapper'][0], addedopts['reducer'][0]
        if not addedopts['input'] or not addedopts['output']:
            print >> sys.stderr, 'ERROR: input or output not specified'
            return 1

        _inputs = addedopts['input']
        _output = addedopts['output']

        inputs = reduce(operator.concat, (inp.split(' ') for inp in _inputs))
        output = _output[0]

        pyenv = envdef('PYTHONPATH', addedopts['libegg'],
            shortcuts=dict(configopts('eggs', self.prog)), 
            extrapaths=addedopts['pypath'])
        cmdenv = ' '.join("%s='%s'" % tuple(arg.split('=')) for arg in
                          addedopts['cmdenv'])

        if 'yes' in addedopts['pv']:
            mpv = '| pv -s `du -b %s | cut -f 1` -cN map ' % ' '.join(inputs)
            (spv, rpv) = ('| pv -cN sort ', '| pv -cN reduce ')
        else:
            (mpv, spv, rpv) = ('', '', '')

        sorttmpdir, sortbufsize = '', ''
        if addedopts['sorttmpdir']:
            sorttmpdir = "-T %s" % addedopts['sorttmpdir'][0]
        if addedopts['sortbufsize']:
            sortbufsize = "-S %s" % addedopts['sortbufsize'][0]

        python = addedopts['python'][0]
        encodepipe = pyenv + ' ' + python + \
                     ' -m dumbo.cmd encodepipe -file ' + ' -file '.join(inputs)

        if 'code' in addedopts['inputformat']:
            encodepipe += ' -alreadycoded yes'
        if addedopts['addpath'] and 'no' not in addedopts['addpath']:
            encodepipe += ' -addpath yes'
        if addedopts['numreducetasks'] and addedopts['numreducetasks'][0] == '0':
            retval = execute("%s | %s %s %s %s > '%s'" % (encodepipe,
                                                          pyenv,
                                                          cmdenv,
                                                          mapper,
                                                          mpv,
                                                          output))
        else:
            retval = execute("%s | %s %s %s %s| LC_ALL=C sort %s %s %s| %s %s %s %s> '%s'"
                             % (encodepipe,
                                pyenv,
                                cmdenv,
                                mapper,
                                mpv,
                                sorttmpdir,
                                sortbufsize,
                                spv,
                                pyenv,
                                cmdenv,
                                reducer,
                                rpv,
                                output))

        if 'yes' in addedopts['delinputs']:
            for _file in addedopts['input']:
                execute('rm ' + _file)
        return retval


class UnixFileSystem(FileSystem):

    def cat(self, path, opts):
        opts = Options(opts)
        opts.add('file', path)
        return decodepipe(opts)

    def ls(self, path, opts):
        return execute("ls -l '%s'" % path, printcmd=False)

    def exists(self, path, opts):
        return execute("test -e '%s'" % path, printcmd=False)

    def rm(self, path, opts):
        return execute("rm -rf '%s'" % path, printcmd=False)

    def put(self, path1, path2, opts):
        return execute("cp '%s' '%s'" % (path1, path2), printcmd=False)

    def get(self, path1, path2, opts):
        return execute("cp '%s' '%s'" % (path1, path2), printcmd=False)

########NEW FILE########
__FILENAME__ = cmd
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os

from dumbo.util import (dumpcode, Options, loadcode, dumptext, loadtext,
    configopts, parseargs, execute, envdef)
from dumbo.backends import create_filesystem


def dumbo():
    if len(sys.argv) < 2:
        print 'Usages:'
        print '  dumbo start <python program> [<options>]'
        print '  dumbo cat <path> [<options>]'
        print '  dumbo ls <path> [<options>]'
        print '  dumbo exists <path> [<options>]'
        print '  dumbo rm <path> [<options>]'
        print '  dumbo put <path1> <path2> [<options>]'
        print '  dumbo get <path1> <path2> [<options>]'
        print '  dumbo encodepipe [<options>]'
        print '  dumbo decodepipe [<options>]'
        print '  dumbo doctest <python program>'
        return 1
    if sys.argv[1] == 'start':
        retval = start(sys.argv[2], parseargs(sys.argv[2:]))
    elif sys.argv[1] == 'cat':
        retval = cat(sys.argv[2], parseargs(sys.argv[2:]))
    elif sys.argv[1] == 'ls':
        retval = ls(sys.argv[2], parseargs(sys.argv[2:]))
    elif sys.argv[1] == 'exists':
        retval = exists(sys.argv[2], parseargs(sys.argv[2:]))
    elif sys.argv[1] == 'rm':
        retval = rm(sys.argv[2], parseargs(sys.argv[2:]))
    elif sys.argv[1] == 'put':
        retval = put(sys.argv[2], sys.argv[3], parseargs(sys.argv[3:]))
    elif sys.argv[1] == 'get':
        retval = get(sys.argv[2], sys.argv[3], parseargs(sys.argv[3:]))
    elif sys.argv[1] == 'encodepipe':
        retval = encodepipe(parseargs(sys.argv[2:]))
    elif sys.argv[1] == 'decodepipe':
        retval = decodepipe(parseargs(sys.argv[2:]))
    elif sys.argv[1] == 'doctest':
        retval = doctest(sys.argv[2])
    elif sys.argv[1].endswith('.py'):
        retval = start(sys.argv[1], parseargs(sys.argv[1:]))
    else:
        print >> sys.stderr, 'ERROR: unknown dumbo command:', sys.argv[1]
        retval = 1
    return retval


def start(prog,
          opts,
          stdout=sys.stdout,
          stderr=sys.stderr):

    opts = Options(opts)
    opts += Options(configopts('common'))
    opts += Options(configopts('start'))

    pyenv = envdef('PYTHONPATH', opts['libegg'],
                   shortcuts=dict(configopts('eggs', prog)),
                   extrapaths=sys.path)

    if not opts['prog']:
        opts.add('prog', prog)

    if not os.path.exists(prog):
        if prog.endswith(".py"):
            print >> sys.stderr, 'ERROR:', prog, 'does not exist'
            return 1
        prog = '-m ' + prog

    return execute("%s %s" % (sys.executable, prog),
                   opts,
                   pyenv,
                   stdout=stdout,
                   stderr=stderr,
                   printcmd=False)


def cat(path, opts):
    opts = Options(opts)
    opts += Options(configopts('common'))
    opts += Options(configopts('cat'))
    return create_filesystem(opts).cat(path, opts)


def ls(path, opts):
    opts = Options(opts)
    opts += Options(configopts('common'))
    opts += Options(configopts('ls'))
    return create_filesystem(opts).ls(path, opts)


def exists(path, opts):
    opts = Options(opts)
    opts += Options(configopts('common'))
    opts += Options(configopts('exists'))
    return create_filesystem(opts).exists(path, opts)


def rm(path, opts):
    opts = Options(opts)
    opts += Options(configopts('common'))
    opts += Options(configopts('rm'))
    return create_filesystem(opts).rm(path, opts)


def put(path1, path2, opts):
    opts = Options(opts)
    opts += Options(configopts('common'))
    opts += Options(configopts('put'))
    return create_filesystem(opts).put(path1, path2, opts)


def get(path1, path2, opts):
    opts = Options(opts)
    opts += Options(configopts('common'))
    opts += Options(configopts('get'))
    return create_filesystem(opts).get(path1, path2, opts)


def encodepipe(opts=None):
    opts = opts or Options()
    keys = ['addpath', 'file', 'alreadycoded']
    addedopts = opts.filter(keys)
    opts.remove(*keys)

    ofiles = addedopts['file']
    files = map(open, ofiles) if ofiles else [sys.stdin]

    loadfun = loadcode if addedopts['alreadycoded'] else loadtext
    addpath = addedopts['addpath']

    for _file in files:
        outputs = loadfun(line[:-1] for line in _file)
        if addpath:
            outputs = (((_file.name, key), value) for (key, value) in outputs)
        for output in dumpcode(outputs):
            print '\t'.join(output)
        _file.close()
    return 0


def decodepipe(opts=None):
    opts = opts or Options()
    ofiles = opts.pop('file')
    files = map(open, ofiles) if ofiles else [sys.stdin]

    for _file in files:
        outputs = loadcode(line[:-1] for line in _file)
        for output in dumptext(outputs):
            print '\t'.join(output)
        _file.close()
        return 0


def doctest(prog):
    import doctest
    sys.path.append(os.getcwd())
    failures = doctest.testmod(__import__(prog[:-3]))
    print '%s failures in %s tests' % failures
    return int(failures > 0)


if __name__ == '__main__':
    sys.exit(dumbo())

########NEW FILE########
__FILENAME__ = core
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import types
import resource
import copy
from itertools import groupby, chain
from operator import itemgetter

from dumbo.backends import get_backend
from dumbo.util import *
from dumbo.cmd import *


class Error(Exception):
    pass


class Job(object):
    
    def __init__(self):
        self.iters = []
        self.deps = {}  # will contain last dependency for each node
        self.root = -1  # id for the job's root input
        self._argopts = parseargs(sys.argv[1:])
        self.initializer = None
    
    def additer(self, *args, **kwargs):
        kwargs.setdefault('input', len(self.iters)-1)
        input = kwargs['input']
        if type(input) == int:
            input = [input]

        self.iters.append((args, kwargs))
        iter = len(self.iters)-1

        for initer in input:
            self.deps[initer] = iter

        return iter

    def getparam(self, key, default=None):
        if key in os.environ:
            return os.environ.get(key, default)
        elif "param" in self._argopts:
            params = dict(s.split("=", 1) for s in self._argopts["param"])
            return params.get(key, default)
        else:
            return default

    def run(self):
        if len(sys.argv) > 1 and not sys.argv[1][0] == '-':
            iterarg = 0  # default value
            if len(sys.argv) > 2:
                iterarg = int(sys.argv[2])
            # for loop isn't necessary but helps for error reporting apparently
            for args, kwargs in self.iters[iterarg:iterarg+1]:
                kwargs['iter'] = iterarg
                run(*args, **kwargs)
        else:
            for _iter, (args, kwargs) in enumerate(self.iters):
                kwargs['iter'] = _iter
                opts = Options(kwargs.get('opts', []))
                opts += self._argopts
                
                # this has to be done early, while all the opts are still there
                backend = get_backend(opts)
                fs = backend.create_filesystem(opts)

                preoutputsopt = opts.pop('preoutputs')
                delinputsopt = opts.pop('delinputs')

                job_inputs = opts['input']
                if not job_inputs:
                    print >> sys.stderr, 'ERROR: No input path specified'
                    sys.exit(1)

                outputopt = opts['output']
                if not outputopt:
                    print >> sys.stderr, 'ERROR: No output path specified'
                    sys.exit(1)

                job_output = outputopt[0]

                newopts = Options()
                newopts.add('iteration', str(_iter))
                newopts.add('itercount', str(len(self.iters)))

                _input = kwargs['input']
                if type(_input) == int:
                    _input = [_input]
                if _input == [-1]:
                    kwargs['input'] = job_inputs
                    delinputs = 'yes' if 'yes' in delinputsopt and _iter == self.deps[-1] else 'no'
                    newopts.add('delinputs', delinputs)
                else:
                    if -1 in _input:
                        print >> sys.stderr, 'ERROR: Cannot mix job input with intermediate results'
                        sys.exit(1)
                    kwargs['input'] = [job_output + "_pre" + str(initer + 1) for initer in _input]
                    newopts.add('inputformat', 'code')
                    if 'yes' in opts['addpath']:  # not when == 'iter'
                        newopts.add('addpath', 'no')
                    newopts.add('delinputs', 'no')

                if _iter == len(self.iters) - 1:
                    kwargs['output'] = job_output
                else:
                    kwargs['output'] = job_output + "_pre" + str(_iter + 1)
                    newopts.add('outputformat', 'code')
                    if 'yes' in opts['getpath']:  # not when == 'iter'
                        newopts.add('getpath', 'no')

                keys = [k for k, _ in opts if k in newopts]
                opts.remove(*keys)
                opts += newopts

                kwargs['opts'] = opts

                if "initializer" not in kwargs and self.initializer is not None:
                    kwargs["initializer"] = self.initializer

                run(*args, **kwargs)

                if 'yes' not in preoutputsopt and _input != [-1]:
                    for initer in _input:
                        if _iter == self.deps[initer]:
                            fs.rm(job_output + "_pre" + str(initer + 1), opts)


class Program(object):

    def __init__(self, prog, opts=None):
        self.prog, self.opts = prog, opts or Options()
        self.started = False

    def addopt(self, key, value):
        self.opts.add(key, value)

    def delopts(self, key):
        return self.opts.pop(key)

    def delopt(self, key):
        try:
            return self.delopts(key)[0]
        except IndexError:
            return None

    def getopts(self, key):
        return self.opts[key]

    def getopt(self, key):
        try:
            return self.getopts(key)[0]
        except IndexError:
            return None

    def addparam(self, key, value):
        self.addopt("param", "%s=%s" % (key, value))

    def clone(self):
        return copy.deepcopy(self)

    def start(self):
        if self.started:
            return 0
        self.started = True
        return start(self.prog, self.opts)


def main(runner, starter=None, variator=None):
    opts = parseargs(sys.argv[1:])
    starteropt = opts.pop('starter')
    opts.add('starter', 'no')
    if starter and 'no' not in starteropt and \
            not (len(sys.argv) > 1 and sys.argv[1][0] != '-'):
        progopt = opts.pop('prog')
        progname = progopt[0] if progopt else sys.argv[0]
        program = Program(progname, opts)

        try:
            if variator:
                programs = variator(program)
                # note the the variator can be a generator, which
                # implies that exceptions might only occur later
            else:
                programs = [program]
            status = 0
            for program in programs:
                try:
                    errormsg = starter(program)
                except Error, e:
                    errormsg = str(e)
                    status = 1
                if errormsg:
                    print >> sys.stderr, "ERROR: " + errormsg
                    status = 1
                else:
                    retval = program.start()
                    if retval != 0:
                        status = retval
            if status != 0:
                sys.exit(status)
        except Error, e:
            print >> sys.stderr, "ERROR: " + str(e)
            sys.exit(1)
    else:
        job = Job()
        errormsg = runner(job)
        if errormsg:
            print >> sys.stderr, errormsg
            sys.exit(1)
        job.run()


def run(mapper,
        reducer=None,
        combiner=None,
        buffersize=None,
        mapconf=None,
        redconf=None,
        combconf=None,
        mapclose=None,
        redclose=None,
        combclose=None,
        mapcleanup=None,
        redcleanup=None,
        combcleanup=None,
        opts=None,
        input=None,
        output=None,
        iter=0,
        initializer=None):
    if len(sys.argv) > 1 and not sys.argv[1][0] == '-':
        iterarg = 0  # default value
        if len(sys.argv) > 2:
            iterarg = int(sys.argv[2])
        memlim = None  # memory limit
        if len(sys.argv) > 3:
            memlim = int(sys.argv[3])
            resource.setrlimit(resource.RLIMIT_AS, (memlim, memlim))

        mrbase_class = loadclassname(os.environ['dumbo_mrbase_class'])
        jk_class = loadclassname(os.environ['dumbo_jk_class'])
        runinfo = loadclassname(os.environ['dumbo_runinfo_class'])()

        if iterarg == iter:
            if sys.argv[1].startswith('map'):
                if type(mapper) in (types.ClassType, type):
                    mappercls = type('DumboMapper', (mapper, mrbase_class), {})
                    mapper = mappercls()
                if hasattr(mapper, 'configure'):
                    mapconf = mapper.configure
                if hasattr(mapper, 'close'):
                    mapclose = mapper.close
                if hasattr(mapper, 'map'):
                    mapper = mapper.map
                if hasattr(mapper, 'cleanup'):
                    mapcleanup = mapper.cleanup
                if type(combiner) in (types.ClassType, type):
                    combinercls = type('DumboCombiner', (combiner, mrbase_class), {})
                    combiner = combinercls()
                if hasattr(combiner, 'configure'):
                    combconf = combiner.configure
                if hasattr(combiner, 'close'):
                    combclose = combiner.close
                if hasattr(combiner, 'reduce'):
                    combiner = combiner.reduce
                if hasattr(combiner, 'cleanup'):
                    combcleanup = combiner.cleanup
                try:
                    print >> sys.stderr, "INFO: consuming %s" % \
                                         os.environ['map_input_file']
                except KeyError:
                    pass
                if os.environ.has_key('stream_map_input') and \
                os.environ['stream_map_input'].lower() == 'typedbytes':
                    print >> sys.stderr, "INFO: inputting typed bytes"
                    try: import ctypedbytes as typedbytes
                    except ImportError: import typedbytes
                    inputs = typedbytes.PairedInput(sys.stdin).reads()
                else:
                    inputs = loadcode(line[:-1] for line in sys.stdin)
                if mapconf:
                    mapconf()
                if combconf:
                    combconf()
                if os.environ.has_key('dumbo_addpath'):
                    path = runinfo.get_input_path()
                    inputs = (((path, k), v) for (k, v) in inputs)
                if os.environ.has_key('dumbo_joinkeys'):
                    inputs = ((jk_class(k), v) for (k, v) in inputs)

                if os.environ.has_key('dumbo_parser'):
                    parser = os.environ['dumbo_parser']
                    clsname = parser.split('.')[-1]
                    modname = '.'.join(parser.split('.')[:-1])
                    if not modname:
                        raise ImportError(parser)
                    module = __import__(modname, fromlist=[clsname])
                    parse = getattr(module, clsname)().parse
                    outputs = itermap(inputs, mapper, parse)
                elif os.environ.has_key('dumbo_record'):
                    record = os.environ['dumbo_record']
                    clsname = record.split('.')[-1]
                    modname = '.'.join(record.split('.')[:-1])
                    if not modname:
                        raise ImportError(parser)
                    module = __import__(modname, fromlist=[clsname])
                    set = getattr(module, clsname)().set
                    outputs = itermap(inputs, mapper, lambda v: set(*v))
                else:
                    outputs = itermap(inputs, mapper)
                if mapcleanup:
                    outputs = chain(outputs, mapcleanup())

                # Combiner
                if combiner and type(combiner) != str:
                    if (not buffersize) and memlim:
                        buffersize = int(memlim * 0.33) / 512  # educated guess
                        print >> sys.stderr, 'INFO: buffersize =', buffersize
                    inputs = sorted(outputs, buffersize)
                    if os.environ.has_key('dumbo_joinkeys'):
                        outputs = iterreduce(inputs, combiner,
                                             keyfunc=jk_class.fromjoinkey)
                    else:
                        outputs = iterreduce(inputs, combiner)
                if os.environ.has_key('dumbo_joinkeys'):
                    outputs = ((jk.dump(), v) for (jk, v) in outputs)
                if combcleanup:
                    outputs = chain(outputs, combcleanup())

                if os.environ.has_key('stream_map_output') and \
                os.environ['stream_map_output'].lower() == 'typedbytes':
                    print >> sys.stderr, "INFO: outputting typed bytes"
                    try: import ctypedbytes as typedbytes
                    except ImportError: import typedbytes
                    typedbytes.PairedOutput(sys.stdout).writes(outputs)
                else:
                    for output in dumpcode(outputs):
                        print '\t'.join(output)
                if combclose:
                    combclose()
                if mapclose:
                    mapclose()

            elif reducer:
                # Reducer
                if type(reducer) in (types.ClassType, type):
                    reducercls = type('DumboReducer', (reducer, mrbase_class), {})
                    reducer = reducercls()
                if hasattr(reducer, 'configure'):
                    redconf = reducer.configure
                if hasattr(reducer, 'close'):
                    redclose = reducer.close
                if hasattr(reducer, 'reduce'):
                    reducer = reducer.reduce
                if hasattr(reducer, 'cleanup'):
                    redcleanup = reducer.cleanup
                if os.environ.has_key('stream_reduce_input') and \
                os.environ['stream_reduce_input'].lower() == 'typedbytes':
                    print >> sys.stderr, "INFO: inputting typed bytes"
                    try: import ctypedbytes as typedbytes
                    except ImportError: import typedbytes
                    inputs = typedbytes.PairedInput(sys.stdin).reads()
                else:
                    inputs = loadcode(line[:-1] for line in sys.stdin)
                if redconf:
                    redconf()
                if os.environ.has_key('dumbo_joinkeys'):
                    outputs = iterreduce(inputs, reducer,
                                         keyfunc=jk_class.fromdump)
                    outputs = ((jk.body, v) for (jk, v) in outputs)
                else:
                    outputs = iterreduce(inputs, reducer)
                if redcleanup:
                    outputs = chain(outputs, redcleanup())
                if os.environ.has_key('stream_reduce_output') and \
                os.environ['stream_reduce_output'].lower() == 'typedbytes':
                    print >> sys.stderr, "INFO: outputting typed bytes"
                    try: import ctypedbytes as typedbytes
                    except ImportError: import typedbytes
                    typedbytes.PairedOutput(sys.stdout).writes(outputs)
                else:
                    for output in dumpcode(outputs):
                        print '\t'.join(output)
                if redclose:
                    redclose()
            else:
                for output in dumpcode(inputs):
                    print '\t'.join(output)
    else:
        opts = Options(opts)
        if type(mapper) == str:
            opts.add('mapper', mapper)
        elif hasattr(mapper, 'opts'):
            opts += mapper.opts
        if type(reducer) == str:
            opts.add('reducer', reducer)
        elif hasattr(reducer, 'opts'):
            opts += reducer.opts
        if type(combiner) == str:
            opts.add('combiner', combiner)
        opts += parseargs(sys.argv[1:])

        if input is not None:
            opts.remove('input')
            for infile in input:
                opts.add('input', infile)

        if output is None:
            outputopt = opts['output']
            if not outputopt:
                print >> sys.stderr, 'ERROR: No output path specified'
                sys.exit(1)
            output = outputopt[0]

        newopts = Options()
        newopts.add('output', output)
        if not reducer:
            newopts.add('numreducetasks', '0')

        keys = [k for k, _ in opts if k in newopts]
        opts.remove(*keys)
        opts += newopts

        if initializer is not None:
            initializer(opts)

        backend = get_backend(opts)

        overwriteopt = opts.pop('overwrite')
        checkoutput = 'no' not in opts.pop('checkoutput')
        fs = backend.create_filesystem(opts)
        if 'yes' in overwriteopt:
            fs.rm(output, opts)
        elif checkoutput and fs.exists(output, opts) == 0:
            print >> sys.stderr, 'ERROR: Output path exists already: %s' % output
            sys.exit(1)
        
        opts.add('cmdenv', 'dumbo_mrbase_class=' + \
                     getclassname(backend.get_mapredbase_class(opts)))
        opts.add('cmdenv', 'dumbo_jk_class=' + \
                     getclassname(backend.get_joinkey_class(opts)))
        opts.add('cmdenv', 'dumbo_runinfo_class=' + \
                     getclassname(backend.get_runinfo_class(opts)))
        retval = backend.create_iteration(opts).run()
        if retval == 127:
            print >> sys.stderr, 'ERROR: Are you sure that "python" is on your path?'
        if retval != 0:
            sys.exit(retval)


def valwrapper(data, valfunc):
    MAX_LOGGED_BADVALUES = 500
    badvalues = 0
    for (key, value) in data:
        try:
            yield (key, valfunc(value))
        except (ValueError, TypeError):
            if badvalues <= MAX_LOGGED_BADVALUES:
                print >> sys.stderr, \
                     'WARNING: skipping bad value (%s)' % str(value)
            if os.environ.has_key('dumbo_debug'):
                raise
            badvalues += 1
            incrcounter('Dumbo', 'Bad inputs', 1)


def mapfunc_iter(data, mapfunc):
    for (key, value) in data:
        for output in mapfunc(key, value):
            yield output


def itermap(data, mapfunc, valfunc=None):
    if valfunc:
        data = valwrapper(data, valfunc)
    try:
        return mapfunc(data)
    except TypeError:
        return mapfunc_iter(data, mapfunc)


def redfunc_iter(data, redfunc):
    for (key, values) in data:
        for output in redfunc(key, values):
            yield output


def iterreduce(data, redfunc, keyfunc=None):
    data = groupby(data, itemgetter(0))
    data = ((key, (v[1] for v in values)) for key, values in data)
    if keyfunc:
        data = ((keyfunc(key), values) for key, values in data)
    try:
        return redfunc(data)
    except TypeError:
        return redfunc_iter(data, redfunc)


def itermapred(data, mapfunc, redfunc):
    return iterreduce(sorted(itermap(data, mapfunc)), redfunc)

########NEW FILE########
__FILENAME__ = decor
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dumbo.lib import PrimaryMapper, SecondaryMapper
from dumbo.util import Options

class opt(object):

    def __init__(self, name, value):
        self.opt = (name, value)

    def __call__(self, func):
        if hasattr(func, 'opts'):
            key, value = self.opt
            func.opts.add(key, value)
        else:
            func.opts = Options([self.opt])
        return func


def primary(mapper):
    return PrimaryMapper(mapper)

def secondary(mapper):
    return SecondaryMapper(mapper)

########NEW FILE########
__FILENAME__ = cdbreducer
import os
from tempfile import mkstemp
import cdb

from .rawreducer import RawReducer, chunkedread, CHUNKSIZE


class CDBFactory(object):
    """A RawReducer factory suitable to generate constant dbs from dumbo jobs

    For more info on constant dbs see http://cr.yp.to/cdb.html
    """
    chunksize = CHUNKSIZE

    def __init__(self):
        fd, self.fn = mkstemp('.cdb', dir=os.getcwd())
        os.close(fd)
        self.maker = cdb.cdbmake(self.fn, self.fn + '.tmp')

    def __call__(self, key, values):
        for value in values:
            self.maker.add(key, value)

    def close(self):
        self.maker.finish()
        for chk in chunkedread(self.fn, chunksize=self.chunksize):
            yield chk
        os.unlink(self.fn)


class CDBReducer(RawReducer):
    factory = CDBFactory

########NEW FILE########
__FILENAME__ = jsonlinesreducer
try:
    import json
except ImportError:
    import simplejson as json

from .rawreducer import RawReducer


class JsonLinesReducer(RawReducer):

    def factory(self):
        return lambda key, values: (json.dumps(v) + '\n' for v in values)

########NEW FILE########
__FILENAME__ = rawreducer
"""A reducer base class to output one or multiple files in its raw fileformat"""
from itertools import groupby
from dumbo.util import Options

class RawReducer(object):
    """Reducer to generate outputs in raw file format"""

    multipleoutput = False
    singleopts = Options([
        ('outputformat', 'raw'),
    ])
    multipleopts = Options([
        ('getpath', 'yes'),
        ('outputformat', 'raw'),
        ('partitioner', 'fm.last.feathers.partition.Prefix'),
        ('jobconf', 'feathers.output.filename.strippart=true'),
    ])

    def __init__(self, factory=None, multipleoutput=None):
        if factory:
            self.factory = factory
        if multipleoutput is not None:
            self.multipleoutput = multipleoutput
        self.opts = self.multipleopts if self.multipleoutput else self.singleopts

    def __call__(self, data):
        if not self.multipleoutput:
            data = (((None, key), values) for key, values in data)

        proc = self.factory()
        for path, group in groupby(data, lambda x:x[0][0]):
            proc = self.factory()
            for (_, key), values in group:
                for chk in proc(key, values) or ():
                    yield path, chk

            close = getattr(proc, 'close', tuple)
            for chk in close() or ():
                yield path, chk

    def factory(self):
        """Processor factory used to consume reducer input (one per path on multiple outputs)

        Must return a callable (aka processor) that accepts two parameters
        "key" and "values", and returns an iterable of strings or None.

        The processor may have a close() method that returns an iterable of
        strings or None. This method is called when the last key-values pair
        for a path is seen.

        """
        return lambda key, values: values

CHUNKSIZE = 2*1024*1024 # default chunk size to read a file
def chunkedread(filename_or_fileobj, chunksize=CHUNKSIZE):
    """Returns a generator that reads a file in chunks"""
    if hasattr(filename_or_fileobj, 'read'):
        fileobj = filename_or_fileobj
        needclose = False
    else:
        fileobj = open(filename_or_fileobj, 'rb')
        needclose = True

    try:
        content = fileobj.read(chunksize)
        while content:
            yield content
            content = fileobj.read(chunksize)
    finally:
        if needclose:
            fileobj.close()


########NEW FILE########
__FILENAME__ = tokyocabinetreducer
import os
from tempfile import mkstemp
from tokyo.cabinet import HDB, HDBOWRITER, HDBOCREAT

from .rawreducer import RawReducer, chunkedread, CHUNKSIZE


class TokyoCabinetFactory(object):
    """A RawReducer factory suitable to generate tokyocabinets from dumbo jobs"""

    dbcls = HDB
    flags = HDBOWRITER | HDBOCREAT
    methodname = 'putasync'
    chunksize = CHUNKSIZE

    def __init__(self):
        fd, self.fn = mkstemp('.db', 'tc-', os.getcwd())
        os.close(fd)
        self.db = self.dbcls()
        self.db.setxmsiz(0)
        self.db.open(self.fn, self.flags)
        self.add = getattr(self.db, self.methodname)

    def __call__(self, key, values):
        for value in values:
            self.add(key, value)

    def close(self):
        self.db.close()
        for chk in chunkedread(self.fn, chunksize=self.chunksize):
            yield chk
        os.unlink(self.fn)


class TokyoCabinetReducer(RawReducer):
    factory = TokyoCabinetFactory

########NEW FILE########
__FILENAME__ = mapredtest
#!/usr/bin/env python
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
dumbo.mapredtest

Provide a simple way of unit-testing MapReduce jobs written
in dumbo locally. This is loosely based on Cloudera's MRUnit design.

See for example discussion on unit-testing MR jobs:
http://www.cloudera.com/blog/2009/07/advice-on-qa-testing-your-mapreduce-jobs/
http://www.cloudera.com/blog/2009/07/debugging-mapreduce-programs-with-mrunit/
"""

import sys
import os
import inspect
from itertools import imap, izip_longest, ifilter

from dumbo.core import itermap, iterreduce, itermapred
from dumbo.backends.common import MapRedBase

__all__ = ['MapDriver', 'ReduceDriver', 'MapReduceDriver']

def assert_iters_equal(expected, actual):
    """:Raise AssertionError: If the elements of iterators `expected` and `actual`
    are not equal (or one has more elements than the other)."""
    sentinel = object()
    expdiff, actdiff = next(ifilter(lambda x: cmp(*x), izip_longest(iter(expected), iter(actual), fillvalue=sentinel)), (None, None))
    if expdiff == sentinel:
        raise AssertionError("expected sequence exhausted before actual at element {0}".format(actdiff))
    elif actdiff == sentinel:
        raise AssertionError("actual sequence exhausted before expected at element {0}".format(expdiff))
    elif expdiff != actdiff:
        raise AssertionError("Element {0} did not match expected output: {1}".format(actdiff, expdiff))


class BaseDriver(object):
    """A Generic test driver that passes
    input stream through a callable and
    checks output stream matches specified one.
    Implements some MapReduce/dumbo specific checks
    and verification on parameters."""
    
    def __init__(self, kallable):
        """Initialize instance data"""
        
        # Check if given callable is a function or a class 
        # type that needs instantiation
        if inspect.isclass(kallable):
            # Re-derive class using dumbo's common MapRedBase object.
            kallable = self._instrument_class(kallable)
            self._callable = kallable()
        else:
            self._callable = kallable        
            	
        self._input_source = None
        self._output_source = None
    
    def with_params(self, params):
        for k, v in params:
            os.environ[k] = v
        return self
        
    def with_input(self, input_source):
        """Bind input stream"""
        if not hasattr(input_source, "next"):
            # Not an iterator
            self._input_source = iter(input_source)
        else:
            self._input_source = input_source
        return self
    
    def with_output(self, output_source):
        """Bind output stream"""
        if not hasattr(output_source, 'next'):
            # Not an iterator
            self._output_source = iter(output_source)
        else:
            self._output_source = output_source
        return self
        
    def run(self):
        """Run test"""
        assert_iters_equal(self._output_source, imap(self._func, self._input_source))
      
    def _instrument_class(self, cls):
        """Instrument a class for use with dumbo mapreduce tests"""
        newcls = type('InstrumentedClass', (cls, MapRedBase), {})
        return newcls
    
        
class MapDriver(BaseDriver):
    """Driver for Map operations"""    

    @property
    def mapper(self):
        return self._callable
    
    def run(self):
        """Run test"""
        assert_iters_equal(self._output_source, itermap(self._input_source, self._callable))
    
    
class ReduceDriver(BaseDriver):
    """Stub driver for Reduce operations"""    

    @property
    def reducer(self):
        return self._callable
    
    def run(self):
        """Run test"""
        assert_iters_equal(self._output_source, iterreduce(self._input_source, self._callable))
    
    
class MapReduceDriver(BaseDriver):
    """Stub driver for Map operations"""
    
    def __init__(self, mapper, reducer):
        BaseDriver.__init__(self, None)
        
        if inspect.isclass(mapper):
            mapper = self._instrument_class(mapper)
            self._mapper = mapper()
        else:
            self._mapper = mapper  
            
        if inspect.isclass(reducer):
            reducer = self._instrument_class(reducer)
            self._reducer = reducer()
        else:
            self._reducer = reducer
            
    @property
    def mapper(self):
        return self._mapper
    
    @property
    def reducer(self):
        return self._reducer
    
    def run(self):
        """Run test"""
        assert_iters_equal(self._output_source, itermapred(self._input_source, self._mapper, self._reducer))

########NEW FILE########
__FILENAME__ = util
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import re
import subprocess
import warnings
from collections import defaultdict

def sorted(iterable, piecesize=None, key=None, reverse=False):
    if not piecesize:
        values = list(iterable)
        values.sort(key=key, reverse=reverse)
        for value in values:
            yield value
    else:  # piecewise sorted
        sequence = iter(iterable)
        while True:
            values = list(sequence.next() for i in xrange(piecesize))
            values.sort(key=key, reverse=reverse)
            for value in values:
                yield value
            if len(values) < piecesize:
                break

def incrcounter(group, counter, amount):
    print >> sys.stderr, 'reporter:counter:%s,%s,%s' % (group, counter, amount)


def setstatus(message):
    print >> sys.stderr, 'reporter:status:%s' % message


def dumpcode(outputs):
    for output in outputs:
        yield map(repr, output)


def loadcode(inputs):
    for input in inputs:
        try:
            yield map(eval, input.split('\t', 1))
        except (ValueError, TypeError):
            print >> sys.stderr, 'WARNING: skipping bad input (%s)' % input
            if os.environ.has_key('dumbo_debug'):
                raise
            incrcounter('Dumbo', 'Bad inputs', 1)


def dumptext(outputs):
    newoutput = []
    for output in outputs:
        for item in output:
            if not hasattr(item, '__iter__'):
                newoutput.append(str(item))
            else:
                newoutput.append('\t'.join(map(str, item)))
        yield newoutput
        del newoutput[:]


def loadtext(inputs):
    offset = 0
    for input in inputs:
        yield (offset, input)
        offset += len(input)

class Options(object):
    """
    Class that represents a set of options. A key can hold
    more than one value and keys are stored in lowercase.
    The order of the values is preserved per key.
    """

    def __init__(self, seq=None, **kwargs):
        """
        Initialize the option object

        Args:
         - seq: a list of (key, value) pairs 
        """
        self._opts = defaultdict(list)  # not sets since order is important
        options = seq or []
        for k, v in kwargs.iteritems():
            self.add(k, v)
        for k, v in options:
            self.add(k, v)

    def add(self, key, value):
        optlist = self._opts[key]
        try:
            optlist.remove(value)
        except ValueError:
            pass  # ignore "not in list" error
        optlist.append(value)

    def update(self, key, values):
        for value in values:
            self.add(key, value)

    def get(self, key):
        if key not in self._opts:
            return []
        return list(self._opts[key])

    def __getitem__(self, key):
        return self.get(key)

    def __delitem__(self, key):
        return self.remove(key)

    def __iadd__(self, opts):
        if isinstance(opts, Options):
            for k, vs in opts._opts.items():
                self.update(k, vs)
            return self
        elif isinstance(opts, (list, tuple, set)):
            for k, v in opts:
                self.add(k, v)
            return self
        else:
            raise ValueError('Invalid opts type. Must be an iterable of (key, value)')

    def __iter__(self):
        return iter(self.allopts())

    def __contains__(self, key):
        return key in self._opts

    def __len__(self):
        return len(self.allopts())

    def __bool__(self):
        return bool(self._opts)

    def filter(self, keys):
        return Options(seq=[(k, v) for k, v in self.allopts() if k in keys])

    def allopts(self):
        """Return a list with all the options in the form of (key, value)"""
        return [(k, v) for k, vs in self._opts.items() for v in vs]

    def to_dict(self):
        return dict((k, list(vs)) for k, vs in self._opts.items())

    def __str__(self):
        ps = self.allopts()
        return "Options(%s)" % (', '.join('%s="%s"' % (k, v) for k, v in ps))
    __repr__ = __str__

    def remove(self, *keys):
        opts = self._opts
        for k in keys:
            if k in opts:
                del opts[k]

    def pop(self, key, default=None):
        return list(self._opts.pop(key, default or ()))

def parseargs(args):
    (opts, key, values) = (Options(), None, [])
    for arg in args:
        if arg[0] == '-' and len(arg) > 1:
            if key:
                opts.add(key, ' '.join(values))
            (key, values) = (arg[1:], [])
        else:
            values.append(arg)
    if key:
        opts.add(key, ' '.join(values))
    return opts

def getopts(opts, keys, delete=True):
    warnings.warn("getopts will be deprecated. use dumbo.util.Options", 
            DeprecationWarning)
    o = Options(opts)
    result = o.filter(keys).to_dict()
    if delete:
        for k in keys:
            for v in o.get(k):
                opts.remove((k, v))
            if k in o:
                o.remove(k)
    return result

def getopt(opts, key, delete=True):
    warnings.warn("getopts will be deprecated. use dumbo.util.Options", 
            DeprecationWarning)
    o = Options(opts)
    if key not in o:
        return []
    values = o.get(key)
    if delete:
        for val in values:
            opts.remove((key, val))
        o.remove(key)
    return values

def configopts(section, prog=None, opts=None):
    from ConfigParser import SafeConfigParser, NoSectionError
    if prog:
        prog = prog.split('/')[-1]
        prog = prog[:-3] if prog.endswith('.py') else prog
        defaults = {'prog': prog}
    else:
        defaults = {}
    try:
        defaults.update([('user', os.environ['USER']), ('pwd',
                        os.environ['PWD'])])
    except KeyError:
        pass
    for (key, value) in opts or Options():
        defaults[key.lower()] = value
    parser = SafeConfigParser(defaults)
    parser.read(['/etc/dumbo.conf', os.environ['HOME'] + '/.dumborc'])
    (results, excludes) = ([], set(defaults.iterkeys()))
    try:
        for (key, value) in parser.items(section):
            if not key.lower() in excludes:
                results.append((key.split('_', 1)[0], value))
    except NoSectionError:
        pass
    return results


def execute(cmd,
            opts=None,
            precmd='',
            printcmd=True,
            stdout=sys.stdout,
            stderr=sys.stderr):
    if precmd:
        cmd = ' '.join((precmd, cmd))
    opts = opts or Options()
    args = ' '.join("-%s '%s'" % (key, value) for (key, value) in opts)
    if args:
        cmd = ' '.join((cmd, args))
    if printcmd:
        print >> stderr, 'EXEC:', cmd
    return system(cmd, stdout, stderr)


def system(cmd, stdout=sys.stdout, stderr=sys.stderr):
    if sys.version[:3] == '2.4':
        return os.system(cmd)
    proc = subprocess.Popen(cmd, shell=True, stdout=stdout,
                            stderr=stderr)
    return proc.wait()


def findhadoop(optval):
    (hadoop, hadoop_shortcuts) = (optval, dict(configopts('hadoops')))
    if hadoop_shortcuts.has_key(hadoop.lower()):
        hadoop = hadoop_shortcuts[hadoop.lower()]
    if not os.path.exists(hadoop):
        print >> sys.stderr, 'ERROR: directory %s does not exist' % hadoop
        sys.exit(1)
    return hadoop


def findjar(hadoop, name, libdirs=None):
    """Tries to find a JAR file based on given
    hadoop home directory and component base name (e.g 'streaming')"""

    searchdirs = [hadoop]
    if libdirs:
        for libdir in libdirs:
            if os.path.exists(libdir):
                searchdirs.append(libdir)

    jardir_candidates = []
    for searchdir in searchdirs:
        jardir_candidates += filter(os.path.exists, [
            os.path.join(searchdir, 'mapred', 'build', 'contrib', name),
            os.path.join(searchdir, 'build', 'contrib', name),
            os.path.join(searchdir, 'mapred', 'contrib', name, 'lib'),
            os.path.join(searchdir, 'contrib', name, 'lib'),
            os.path.join(searchdir, 'mapred', 'contrib', name),
            os.path.join(searchdir, 'contrib', name),
            os.path.join(searchdir, 'mapred', 'contrib'),
            os.path.join(searchdir, 'contrib'),
            searchdir
        ])

    regex = re.compile(r'hadoop.*%s.*\.jar' % name)

    for jardir in jardir_candidates:
        matches = filter(regex.match, os.listdir(jardir))
        if matches:
            return os.path.join(jardir, matches[-1])

    return None


def envdef(varname,
           files,
           optname=None,
           opts=None,
           commasep=False,
           shortcuts={},
           quote=True,
           trim=False,
           extrapaths=None):
    (pathvals, optvals) = ([], [])
    for file in files:
        if shortcuts.has_key(file.lower()):
            file = shortcuts[file.lower()]
        if file.startswith('path://'):
            pathvals.append(file[7:])
        else:
            if not '://' in file:
                if not os.path.exists(file):
                    raise ValueError('file "' + file + '" does not exist')
                file = 'file://' + os.path.abspath(file)
            if not trim:
                pathvals.append(file.split('://', 1)[1])
            else:
                pathvals.append(file.split('/')[-1])
            optvals.append(file)
    if extrapaths:
        pathvals.extend(extrapaths)
    path = ':'.join(pathvals)
    if optname and optvals:
        opts = opts or Options()
        if not commasep:
            for optval in optvals:
                opts.add(optname, optval)
        else:
            opts.add(optname, ','.join(optvals))
    if not quote:
        return '%s=%s' % (varname, path)
    else:
        return '%s="%s"' % (varname, ':'.join((path, '$' + varname)))


def getclassname(cls):
    return cls.__module__ + "." + cls.__name__


def loadclassname(name):
    modname, _, clsname = name.rpartition(".")
    mod = __import__(modname, fromlist=[clsname])
    return getattr(mod, clsname)

########NEW FILE########
__FILENAME__ = altwordcount
"""
Counts how many times each word occurs, using the alternative 
(more low-level) interface to mappers/reducers.
"""

def mapper(data):
    for key, value in data:
        for word in value.split(): yield word,1

def reducer(data):
    for key, values in data:
        yield key,sum(values)

if __name__ == "__main__":
    import dumbo
    dumbo.run(mapper,reducer,reducer)

########NEW FILE########
__FILENAME__ = itertwice
"""
Example of two iterations in one Dumbo program.
"""

def mapper1(key,value):
    for word in value.split(): yield word,1

def mapper2(key,value):
    for letter in key: yield letter,1

def reducer1(key,values):
    count = sum(values)
    if count > 1: yield key,count

def reducer2(key,values):
    yield key,sum(values)

if __name__ == "__main__":
    import dumbo
    job = dumbo.Job()
    job.additer(mapper1,reducer1,reducer2)
    job.additer(mapper2,reducer2,reducer2)
    job.run()

########NEW FILE########
__FILENAME__ = join
"""
Joins hostnames with logs and counts number of logs per host.
"""

import dumbo
from dumbo.lib import JoinReducer
from dumbo.decor import primary, secondary

def mapper1(key, value):
    yield value.split("\t", 1) 

class Reducer1(JoinReducer):
    def __init__(self):
        self.hostname = "unknown"
    def primary(self, key, values):
        self.hostname = values.next()
    def secondary(self, key, values):
        key = self.hostname
        self.hostname = "unknown"
        for value in values:
            yield key, value

def mapper2(key, value):
    yield key, 1

def reducer2(key, values):
    yield key, sum(values)
    
def runner(job):
    multimapper = dumbo.MultiMapper()
    multimapper.add("hostnames", primary(mapper1))
    multimapper.add("logs", secondary(mapper1))
    job.additer(multimapper, Reducer1)
    job.additer(mapper2, reducer2, combiner=reducer2)

if __name__ == "__main__":
    dumbo.main(runner)

########NEW FILE########
__FILENAME__ = multicount
"""
Illustrates MultiMapper.
"""

from dumbo import main, MultiMapper, sumreducer

def mapper1(key, value):
    for word in value.split():
        yield ("A", word), 1

class Mapper2:
    def __call__(self, key, value):
        for word in value.split():
            yield ("B", word), 1

def runner(job):
    mapper = MultiMapper()
    mapper.add("brian", mapper1)
    mapper.add("eno", Mapper2)
    job.additer(mapper, sumreducer, combiner=sumreducer)

if __name__ == "__main__":
    main(runner)

########NEW FILE########
__FILENAME__ = oowordcount
"""
Counts how many times each non-excluded word occurs.
"""

class Mapper:
    def __init__(self):
        file = open(self.params["excludes"],"r")
        self.excludes = set(line.strip() for line in file)
        file.close()
    def __call__(self,key,value):
        for word in value.split(): 
            if not (word in self.excludes): yield word,1

def reducer(key,values):
    yield key,sum(values)

def runner(job):
    job.additer(Mapper,reducer,reducer)

def starter(prog):
    excludes = prog.delopt("excludes")
    if excludes: prog.addopt("param","excludes="+excludes)

if __name__ == "__main__":
    import dumbo
    dumbo.main(runner,starter)

########NEW FILE########
__FILENAME__ = wordcount
"""
Counts how many times each word occurs.
"""

def mapper(key,value):
    for word in value.split(): yield word,1

def reducer(key,values):
    yield key,sum(values)

if __name__ == "__main__":
    import dumbo
    dumbo.run(mapper,reducer,reducer)

########NEW FILE########
__FILENAME__ = testcdbreducer
import os
import unittest
from tempfile import mkstemp
import cdb

from dumbo.lib.cdbreducer import CDBReducer, CDBFactory


class CDBTestCase(unittest.TestCase):

    def test_default(self):
        proc = CDBFactory()
        self.assertEqual(proc('k1', ['v1']), None)
        self.assertEqual(proc('k2', ['v2', 'v3']), None)
        chunks = proc.close()
        fn = mkstemp()[1]
        fo = open(fn, 'wb')
        for chk in chunks:
            self.assertTrue(len(chk) <= proc.chunksize)
            fo.write(chk)
        fo.close()

        db = cdb.init(fn)
        self.assertEqual([(k, db[k]) for k in db.keys()],
                [('k1', 'v1'), ('k2', 'v2')])
        os.remove(fn)

    def test_reducer(self):
        red = CDBReducer()
        output = red(zip('abcde', '12345'))

        fn = mkstemp()[1]
        fo = open(fn, 'wb')
        fo.writelines(v for k, v in output)
        fo.close()

        db = cdb.init(fn)
        self.assertEqual([(k, db[k]) for k in db.keys()],
                [('a', '1'), ('b', '2'), ('c', '3'), ('d', '4'), ('e', '5')])
        os.remove(fn)


########NEW FILE########
__FILENAME__ = testcoding
import unittest
from dumbo import util

class TestCoding(unittest.TestCase):

    def dotest(self,data):
        dumped = "\t".join(util.dumpcode([("dummy",data)]).next())
        self.assertEqual(util.loadcode([dumped]).next()[1],data)

    def testtuple(self):
        self.dotest(tuple())
        self.dotest((1,(2,(3,4)),5))

    def testlist(self):
        self.dotest([])
        self.dotest([(1,2),3,4])

    def testmap(self):
        self.dotest({})
        self.dotest({'key': 'value'})

    def teststring(self):
        self.dotest("{'key': 1}")

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCoding)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = testexamples
import os
import sys
import unittest
from dumbo import cmd, util
from dumbo.util import Options

class TestExamples(unittest.TestCase):

    def setUp(self):
        if "directory" in os.environ:
            rootdir = os.environ["directory"]
            self.exdir = rootdir + "/examples/"
            self.tstdir = rootdir + "/tests/"
        elif "/" in __file__:
            self.exdir = __file__.split("tests/")[0] + "examples/"
            self.tstdir = "/".join(__file__.split("/")[:-1]) + "/"
        else:
            self.exdir = "../examples/"
            self.tstdir = "./"
        self.logfile = open(self.tstdir+"log.txt", "w")
        self.outfile = self.tstdir + "output.code"
        self.common_opts = Options([('checkoutput', 'no')])

    def tearDown(self):
        self.logfile.close()
        os.remove(self.outfile)

    def testwordcount(self):
        opts = self.common_opts
        opts += [('input', self.exdir+'brian.txt'), ('output', self.outfile)]
        retval = cmd.start(self.exdir+'wordcount.py', opts,
                           stdout=self.logfile, stderr=self.logfile)
        self.assertEqual(0, retval)
        output = dict(util.loadcode(open(self.outfile)))
        self.assertEqual(6, int(output['Brian']))

    def testoowordcount(self):
        opts = self.common_opts
        opts += [('excludes', self.exdir+'excludes.txt'),
                 ('input', self.exdir+'brian.txt'), ('output', self.outfile)]
        retval = cmd.start(self.exdir+'oowordcount.py', opts,
                           stdout=self.logfile, stderr=self.logfile)
        self.assertEquals(0, retval)
        output = dict(util.loadcode(open(self.outfile)))
        self.assertEquals(6, int(output['Brian']))

    def testaltwordcount(self):
        opts = self.common_opts
        opts += [('input', self.exdir+'brian.txt'), ('output', self.outfile)]
        retval = cmd.start(self.exdir+'altwordcount.py', opts,
                           stdout=self.logfile, stderr=self.logfile)
        self.assertEqual(0, retval)
        output = dict(util.loadcode(open(self.outfile)))
        self.assertEqual(6, int(output['Brian']))

    def testitertwice(self):
        opts = self.common_opts
        opts += [('input', self.exdir+'brian.txt'), ('output', self.outfile)]
        retval = cmd.start(self.exdir+'itertwice.py', opts,
                           stdout=self.logfile, stderr=self.logfile)
        self.assertEqual(0, retval)
        output = dict(util.loadcode(open(self.outfile)))
        self.assertEqual(14, int(output['e']))

    def testjoin(self):
        opts = self.common_opts
        opts += [('input', self.exdir+'hostnames.txt'),
                 ('input', self.exdir+'logs.txt'),
                 ('output', self.outfile)]
        retval = cmd.start(self.exdir+'join.py', opts,
                           stdout=self.logfile, stderr=self.logfile)
        self.assertEqual(0, retval)
        output = dict(util.loadcode(open(self.outfile)))
        self.assertEqual(5, int(output['node1']))

    def testmulticount(self):
        opts = self.common_opts
        opts += [('input', self.exdir+'brian.txt'),
                 ('input', self.exdir+'eno.txt'),
                 ('output', self.outfile)]
        retval = cmd.start(self.exdir+'multicount.py', opts,
                           stdout=self.logfile, stderr=self.logfile)
        self.assertEqual(0, retval)
        output = dict(util.loadcode(open(self.outfile)))
        self.assertEqual(6, int(output[('A', 'Brian')]))
        self.assertEqual(6, int(output[('B', 'Eno')]))


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestExamples)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = testlib
import unittest
from dumbo import lib, core

class TestLib(unittest.TestCase):

    def teststats(self):
        input = [('testkey',i) for i in xrange(10)]
        input = core.itermapred(input, lib.identitymapper, lib.statscombiner)
        output = dict(core.itermapred(input, lib.identitymapper, lib.statsreducer))
        self.assertEqual(output['testkey'][0], 10) # n
        self.assertEqual(output['testkey'][1], 4.5) # mean
        self.assertAlmostEqual(output['testkey'][2], 3.02765035409749) # std 

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMapReduce)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = testmapred
import unittest
from dumbo import core

class TestMapRed(unittest.TestCase):
    def testwordcount(self):
        def mapper(key,value):
            for word in value.split(): yield word,1
        def reducer(key,values):
            yield key,sum(values)
        input = enumerate(['one two','two one two'])
        output = dict(core.itermapred(input,mapper,reducer))
        self.assertEqual(output['one'],2)
        self.assertEqual(output['two'],3)

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMapReduce)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = testmapredtest
#!/usr/bin/env python
"""
(meta-)test the dumbo.mapredtest unit-test framework,
running it on a mock map/reduce job to make sure
validation works as expected.
"""

import unittest

from dumbo.mapredtest import MapDriver, ReduceDriver, MapReduceDriver

# Example mapper / reducers
class mapper(object):
    def __call__(self, key, value):
        self.counters['test_counter'] += 1
        for word in value.split(): yield word,1

def reducer(key,values):
    yield key,sum(values)
    
class reducer_with_params(object):
    
    def __call__(self, key, value):
        self.counters['test_counter'] += 1
        yield 'foo', str(self.params['foo'])
        yield 'one', str(self.params['one'])
        self.counters['test_counter'] += 1
    

class MRTestCase(unittest.TestCase):
    def testmapper(self):
        input = [
            (0, "test me"),
            (1, "hello")
        ]
        output = [('test', 1),
                  ('me', 1),
                  ('hello', 1)]
        MapDriver(mapper).with_input(input).with_output(output).run()

    def testreducer_with_params(self):
        input = [
            (0, "test me"),
            (1, "hello")
        ]
        #each 3 map calls will yield with both params 
        output = [('foo', 'bar'), ('one', '1')] * 2
        params = [('foo', 'bar'), ('one', '1')]
        ReduceDriver(reducer_with_params).with_params(params).with_input(input).with_output(output).run()
       
    def testreducer(self):
        input = [('test', 1), ('test', 1), ('me', 1,), ('hello', 1)]
        output = [('test', 2), ('me', 1), ('hello', 1)]
        ReduceDriver(reducer).with_input(input).with_output(output).run()

    def testmapreduce(self):
        input = [
            (0, "test me"),
            (1, "hello"),
            (2, "test")
        ]
        output = [('hello', 1), ('me', 1), ('test', 2)]
        MapReduceDriver(mapper, reducer).with_input(input).with_output(output).run()

    def test_toomany(self):
        input_ = [(0, 'a b c')]
        output = [('a', 1), ('b', 1)]
        self.assertRaises(AssertionError, MapDriver(mapper).with_input(input_).with_output(output).run)
        output = [('a', 1), ('b', 1), ('c', 1), ('d', 1)]
        self.assertRaises(AssertionError, MapDriver(mapper).with_input(input_).with_output(output).run)

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(MRTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
        
########NEW FILE########
__FILENAME__ = testrawreducer
import os
import unittest
from tempfile import mkstemp
from cStringIO import StringIO
from dumbo.lib.rawreducer import RawReducer, chunkedread


DATA = [('k1', ['v1a', 'v1b']), ('k2', ['v2c']), ('k3', ['v3d', 'v3e', 'v3f'])]
MULTIDATA = sorted(((str(i), k), [v]) for k, vs in DATA for i, v in enumerate(vs))


class RawReducerTestCase(unittest.TestCase):

    def test_default_factory(self):
        red = RawReducer()
        self.assertEqual(list(red(iter(DATA))),
                [(None, 'v1a'), (None, 'v1b'), (None, 'v2c'),
                 (None, 'v3d'), (None, 'v3e'), (None, 'v3f')])

        red = RawReducer(multipleoutput=True)
        self.assertEqual(list(red(iter(MULTIDATA))),
                [('0', 'v1a'), ('0', 'v2c'), ('0', 'v3d'),
                 ('1', 'v1b'), ('1', 'v3e'), ('2', 'v3f')])

    def test_custom_factory(self):
        def first_value_factory():
            return lambda k, v: [v[0]]

        red = RawReducer(first_value_factory)
        self.assertEqual(list(red(iter(DATA))),
                [(None, 'v1a'), (None, 'v2c'), (None, 'v3d')])

        red = RawReducer(first_value_factory, multipleoutput=True)
        self.assertEqual(list(red(iter(MULTIDATA))),
                [('0', 'v1a'), ('0', 'v2c'), ('0', 'v3d'),
                 ('1', 'v1b'), ('1', 'v3e'), ('2', 'v3f')])

    def test_custom_factory_with_close(self):
        class CloseFactory(object):
            def __init__(self):
                self.items = []

            def __call__(self, key, values):
                self.items.extend(values)

            def close(self):
                return self.items

        red = RawReducer(CloseFactory)
        self.assertEqual(list(red(iter(DATA))),
                [(None, 'v1a'), (None, 'v1b'), (None, 'v2c'),
                 (None, 'v3d'), (None, 'v3e'), (None, 'v3f')])

        red = RawReducer(CloseFactory, multipleoutput=True)
        self.assertEqual(list(red(iter(MULTIDATA))),
                [('0', 'v1a'), ('0', 'v2c'), ('0', 'v3d'),
                 ('1', 'v1b'), ('1', 'v3e'), ('2', 'v3f')])

    def test_extending_rawreducer_class(self):
        class DummyFactory(object):
            def __call__(self, key, values):
                yield key

        class DummyReducer(RawReducer):
            factory = DummyFactory

        red = DummyReducer()
        self.assertEqual(list(red(iter(DATA))),
                [(None, 'k1'), (None, 'k2'), (None, 'k3')])

        red = DummyReducer(multipleoutput=True)
        self.assertEqual(list(red(iter(MULTIDATA))),
                [('0', 'k1'), ('0', 'k2'), ('0', 'k3'),
                 ('1', 'k1'), ('1', 'k3'), ('2', 'k3')])

        class MultiDummyReducer(RawReducer):
            factory = DummyFactory
            multipleoutput = True

        red = MultiDummyReducer()
        self.assertEqual(list(red(iter(MULTIDATA))),
                [('0', 'k1'), ('0', 'k2'), ('0', 'k3'),
                 ('1', 'k1'), ('1', 'k3'), ('2', 'k3')])


class ChunkedReadTestCase(unittest.TestCase):

    def test_chunkedread_on_fileobject(self):
        fo = StringIO('one\nbig\nchunk\nof\ndata\n')
        chunks = chunkedread(fo, chunksize=10)
        self.assertEqual(chunks.next(), 'one\nbig\nch')
        self.assertEqual(chunks.next(), 'unk\nof\ndat')
        self.assertEqual(chunks.next(), 'a\n')
        self.assertRaises(StopIteration, chunks.next)
        fo.close()

    def test_chunkedread_on_filename(self):
        fn = mkstemp()[1]
        try:
            fo = open(fn, 'wb')
            fo.write('one\nbig\nchunk\nof\ndata\n')
            fo.close()
            chunks = chunkedread(fn, chunksize=10)
            self.assertEqual(chunks.next(), 'one\nbig\nch')
            self.assertEqual(chunks.next(), 'unk\nof\ndat')
            self.assertEqual(chunks.next(), 'a\n')
            self.assertRaises(StopIteration, chunks.next)
        finally:
            os.unlink(fn)

########NEW FILE########
__FILENAME__ = testtokyocabinetreducer
import unittest
import os
from tempfile import mkstemp
from tokyo.cabinet import HDB, HDBOREADER, BDB, BDBOREADER, BDBOWRITER, BDBOCREAT

from dumbo.lib.tokyocabinetreducer import TokyoCabinetReducer, TokyoCabinetFactory


class TokyoCabinetTestCase(unittest.TestCase):

    def test_default(self):
        proc = TokyoCabinetFactory()
        self.assertEqual(proc('k1', ['v1']), None)
        self.assertEqual(proc('k2', ['v2', 'v3']), None)
        chunks = proc.close()
        fn = mkstemp()[1]
        fo = open(fn, 'wb')
        for chk in chunks:
            self.assertTrue(len(chk) <= proc.chunksize)
            fo.write(chk)
        fo.close()

        db = HDB()
        db.open(fn, HDBOREADER)
        self.assertEqual(list(db.iteritems()), [('k1', 'v1'), ('k2', 'v3')])
        db.close()
        os.remove(fn)

    def test_extended(self):
        class BDBFactory(TokyoCabinetFactory):
            dbcls = BDB
            flags = BDBOWRITER | BDBOCREAT
            methodname = 'addint'
            chunksize = 10 # very small

        proc = BDBFactory()
        self.assertEqual(proc('k1', [2]), None)
        self.assertEqual(proc('k2', [3, 6]), None)
        chunks = proc.close()
        fn = mkstemp()[1]
        fo = open(fn, 'wb')
        for chk in chunks:
            self.assertTrue(len(chk) <= 10)
            fo.write(chk)
        fo.close()

        db = BDB()
        db.open(fn, BDBOWRITER)
        self.assertEqual(len(db), 2)
        self.assertEqual(db.addint('k1', 0), 2)
        self.assertEqual(db.addint('k2', 0), 9)
        db.close()
        os.remove(fn)

    def test_reducer(self):
        red = TokyoCabinetReducer()
        output = red(zip('abcde', '12345'))

        fn = mkstemp()[1]
        fo = open(fn, 'wb')
        fo.writelines(v for k, v in output)
        fo.close()
        db = HDB()
        db.open(fn, HDBOREADER)
        self.assertEqual(list(db.iteritems()),
                [('a', '1'), ('b', '2'), ('c', '3'), ('d', '4'), ('e', '5')])
        db.close()
        os.remove(fn)

########NEW FILE########
__FILENAME__ = testutil
import unittest
from dumbo.util import getopt, getopts, Options

class TestUtil(unittest.TestCase):

    def test_getopt(self):
        # Test for backward compatibility
        opts = []
        values = getopt(opts, 'input')
        self.assertEquals(values, [])
        self.assertEquals(opts, [])

        opts = [('param', 'p1'), ('param', 'p2'), ('input', '/dev/path')]
        values = getopt(opts, 'param')
        expected = ['p2', 'p1']
        self.assertEquals(set(values), set(expected))
        self.assertEquals(set(opts), set([('input', '/dev/path')]))

        opts = [('output', '/prod/path')]
        values = getopt(opts, 'output', delete=False)
        self.assertEquals(values, ['/prod/path'])
        self.assertEquals(opts, [('output', '/prod/path')])

        values = getopt(opts, 'output')
        self.assertEquals(values, ['/prod/path'])
        self.assertEquals(opts, [])

    def test_getopts(self):
        # Test for backward compatibility
        opts = []
        values = getopts(opts, ['input'])
        self.assertEquals(values, {})
        self.assertEquals(opts, [])

        opts = [('param', 'p1'), ('param', 'p2'), ('input', '/dev/path'),
                ('output', '/prod/path')]
        values = getopts(opts, ['param', 'input'])
        expected = {'input': ['/dev/path'], 'param': ['p2', 'p1']}
        settize = lambda _dict: set([(k, tuple(sorted(v))) for k, v in _dict.items()])
        self.assertEquals(settize(values), settize(expected))
        self.assertEquals(set(opts), set([('output', '/prod/path')]))

        opts = [('output', '/prod/path')]
        values = getopts(opts, ['output'], delete=False)
        self.assertEquals(values, {'output': ['/prod/path']})
        self.assertEquals(opts, [('output', '/prod/path')])

        values = getopts(opts, ['output'])
        self.assertEquals(values, {'output': ['/prod/path']})
        self.assertEquals(opts, [])

    def test_Options(self):
        o = Options([('param', 'p1')])
        # test add / get
        o.add('param', 'p2')

        # test repeat add same parameter
        o.add('param', 'p2')
        o.add('input', '/dev/path')
        o.add('output', '/dev/out')
        self.assertEquals(set(o.get('param')), set(['p1', 'p2']))
        self.assertEquals(o.get('input'), ['/dev/path'])
        self.assertEquals(o.get('notexist'), [])

        # test __getitem__
        self.assertEquals(set(o['param']), set(['p1', 'p2']))
        self.assertEquals(o['input'], ['/dev/path'])
        self.assertEquals(o['notexist'], [])

        # test __delitem__
        self.assertEquals(o['output'], ['/dev/out'])
        del o['output']
        self.assertEquals(o['output'], [])

        # test __iadd__
        # adding Options objects
        o += Options([('output', '/dev/out2'), ('jar', 'my.jar')])
        self.assertEquals(o['output'], ['/dev/out2'])
        self.assertEquals(o['jar'], ['my.jar'])
        # adding a list & set
        o += [('param', 'p3'), ('egg', 'lib.egg')]
        self.assertEquals(set(o['param']), set(['p1', 'p2', 'p3']))
        self.assertEquals(o['egg'], ['lib.egg'])

        o += set([('cmdenv', 'p=2')])
        self.assertEquals(o['cmdenv'], ['p=2'])

        # testing iter / allopts
        o2 = Options([('param', 'p1')])
        o2.add('param', 'p2')
        o2.add('input', '/dev/path')
        self.assertEquals(set(o2), set([('param', 'p1'), ('param', 'p2'), ('input', '/dev/path')]))
        self.assertEquals(set(o2.allopts()), set([('param', 'p1'), ('param', 'p2'), ('input', '/dev/path')]))


        # testing len
        self.assertEquals(len(o), 8)
        self.assertEquals(len(o2), 3)
        self.assertEquals(len(Options()), 0)

        # testing boolean
        self.assertTrue(o)
        self.assertTrue(o2)
        self.assertFalse(Options())

        # testing filter
        self.assertEquals(set(o2.filter(['param'])['param']), set(['p1', 'p2']))
        self.assertEquals(o2.filter(['input'])['input'], ['/dev/path'])

        nop = o.filter(['param', 'jar', 'egg'])
        self.assertEquals(len(nop), 5)
        self.assertEquals(set(nop['param']), set(['p1', 'p2', 'p3']))
        self.assertEquals(nop['jar'], ['my.jar'])
        self.assertEquals(nop['egg'], ['lib.egg'])

        # testing to_dict
        expected = {
            'param': ['p1', 'p2', 'p3'],
            'egg': ['lib.egg'],
            'jar': ['my.jar']
        }
        self.assertEquals(nop.to_dict(), expected)

        # testing remove
        nop.remove('param', 'jar')
        self.assertEquals(len(nop), 1)
        self.assertEquals(nop['param'], [])
        self.assertEquals(nop['jar'], [])
        self.assertEquals(nop['egg'], ['lib.egg'])

        # testing pop
        self.assertEquals(nop.pop('egg'), ['lib.egg'])
        self.assertEquals(len(nop), 0)
        self.assertEquals(nop['egg'], [])

        self.assertEquals(nop.pop('notexist'), [])







if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUtil)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
