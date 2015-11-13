__FILENAME__ = break
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "break" command'

import andbug.command, andbug.screed, andbug.options
from Queue import Queue

def report_hit(t):
    t = t[0]
    with andbug.screed.section("Breakpoint hit in %s, process suspended." % t):
        t.sess.suspend()
        for f in t.frames:
            name = str(f.loc)
            if f.native:
                name += ' <native>'
            andbug.screed.item(name)

def cmd_break_methods(ctxt, cpath, mpath):
    for c in ctxt.sess.classes(cpath):
        for m in c.methods(mpath):
            l = m.firstLoc
            if l.native:
                andbug.screed.item('Could not hook native %s' % l)
                continue
            h = l.hook(func = report_hit)
            andbug.screed.item('Hooked %s' % h)

def cmd_break_classes(ctxt, cpath):
    for c in ctxt.sess.classes(cpath):
        h = c.hookEntries(func = report_hit)
        andbug.screed.item('Hooked %s' % h)

def cmd_break_line(ctxt, cpath, mpath, line):
    for c in ctxt.sess.classes(cpath):
        for m in c.methods(mpath):
            l = m.lineTable
            if l is None or len(l) <= 0:
                continue
            if line == 'show':
                andbug.screed.item(str(sorted(l.keys())))
                continue
            l = l.get(line, None)
            if l is None:
                andbug.screed.item("can't found line %i" % line)
                continue
            if l.native:
                andbug.screed.item('Could not hook native %s' % l)
                continue
            h = l.hook(func = report_hit)
            andbug.screed.item('Hooked %s' % h)

@andbug.command.action(
    '<class> [<method>] [show/lineNo]', name='break', aliases=('b',), shell=True
)
def cmd_break(ctxt, cpath, mquery=None, line=None):
    'set breakpoint'
    cpath, mname, mjni = andbug.options.parse_mquery(cpath, mquery)
    if line is not None:
        if line != 'show':
            line = int(line)

    with andbug.screed.section('Setting Hooks'):
        if mname is None:
            cmd_break_classes(ctxt, cpath)
        elif line is None:
            cmd_break_methods(ctxt, cpath, mname)
        else:
            cmd_break_line(ctxt, cpath, mname, line)

    ctxt.block_exit()

########NEW FILE########
__FILENAME__ = break_list
## Copyright 2011, Felipe Barriga Richards <spam@felipebarriga.cl>.
##                 All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "break-list" command'

import andbug.command, andbug.screed

@andbug.command.action('', name='break-list', shell=True)
def break_list(ctxt):
    'list active breakpoints/hooks'
    with andbug.screed.section('Active Hooks'):
        for eid in ctxt.sess.emap:
            andbug.screed.item('Hook %s' % ctxt.sess.emap[eid])

    ctxt.block_exit()

########NEW FILE########
__FILENAME__ = break_remove
## Copyright 2011, Felipe Barriga Richards <spam@felipebarriga.cl>.
##                 All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under
## the terms of version 3 of the GNU Lesser General Public License as
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "break-remove" command'

import andbug.command, andbug.screed

@andbug.command.action('<eid/all>', name='break-remove', shell=True)
def break_remove(ctxt, eid):
    'remove hook/breakpoint'
    ctxt.sess.suspend()
    try:
        if eid == 'all':
            with andbug.screed.section('remove all hook'):
                for eid in ctxt.sess.emap.keys():
                    ctxt.sess.emap[eid].clear()
                    andbug.screed.item('Hook <%s> removed' % eid)
        else:
            eid = int(eid)
            if eid in ctxt.sess.emap:
                ctxt.sess.emap[eid].clear()
                andbug.screed.section('Hook <%s> removed' % eid)
            else:
                print '!! error, hook not found. eid=%s' % eid
    finally:
        ctxt.sess.resume()

########NEW FILE########
__FILENAME__ = classes
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "classes" command'

import andbug.command, andbug.screed

@andbug.command.action('[<partial class name>]')
def classes(ctxt, expr=None):
    'lists loaded classes. if no partial class name supplied, list all classes.'
    with andbug.screed.section('Loaded Classes'):
	    for c in ctxt.sess.classes():
	        n = c.jni
	        if n.startswith('L') and n.endswith(';'):
                    n = n[1:-1].replace('/', '.')
                else:
                    continue

                if expr is not None:
                    if n.find(expr) >= 0:
                        andbug.screed.item(n)
                else:
                    andbug.screed.item(n)


########NEW FILE########
__FILENAME__ = class_trace
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "class-trace" command'

import andbug.command, andbug.screed, andbug.options
from Queue import Queue
import re

def report_hit(t):
    t = t[0]
    try:
        with andbug.screed.section("trace %s" % t):
            for f in t.frames:
                name = str(f.loc)
                if f.native:
                    name += ' <native>'
                with andbug.screed.item(name):
                    for k, v in f.values.items():
                        andbug.screed.item( "%s=%s" %(k, v))
    finally:
        t.resume()

@andbug.command.action('<class-path>', aliases=('ct', 'ctrace'))
def class_trace(ctxt, cpath):
    'reports calls to dalvik methods associated with a class'
    cpath = andbug.options.parse_cpath(cpath)

    with andbug.screed.section('Setting Hooks'):
        for c in ctxt.sess.classes(cpath):
            c.hookEntries(func = report_hit)
            andbug.screed.item('Hooked %s' % c)
    
    ctxt.block_exit()

########NEW FILE########
__FILENAME__ = dump
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "methods" command'

import andbug.command, andbug.options

def find_last_method_line(source, first_line):
    for last_line in range(first_line,len(source)):
        if source[last_line][1].startswith('.end method'):
            return last_line
    return False

@andbug.command.action('<class-path> [<method-query>]')
def dump(ctxt, cpath, mquery=None):
    'dumps methods using original sources or apktool sources' 
    cpath, mname, mjni = andbug.options.parse_mquery(cpath, mquery)
    for method in ctxt.sess.classes(cpath).methods(name=mname, jni=mjni):
        source = False
        klass = method.klass.name           

        first_line = method.firstLoc.line
        if first_line is None:
            print '!! could not determine first line of', method
            continue
        
        source = andbug.source.load_source(klass)
        if not source:
            print '!! could not find source for', klass
            continue

        last_line = method.lastLoc.line or find_last_method_line(source, first_line)
        if last_line is False:
            print '!! could not determine last line of', method
            continue

        andbug.source.dump_source(source[first_line:last_line], str(method))
########NEW FILE########
__FILENAME__ = exit
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "stop" command'

import andbug.command
import os

@andbug.command.action('', shell=True)
def exit(name=None):
    'terminates andbug with prejudice'
    os._exit(0)

########NEW FILE########
__FILENAME__ = help
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "help" command'

import andbug.command, andbug.options, andbug.screed

BANNER = 'AndBug (C) 2011 Scott W. Dunlop <swdunlop@gmail.com>'

SHELL_INTRO = '''
    The AndBug shell is a simple interactive console shell that reduces typing
    and overhead involved in setting up a debugging session.  Commands entered
    at the prompt will be evaluated using the current device and process as a
    context.  Where possible, AndBug uses readline; if your Python
    install lacks readline, this shell will be more difficult to use due to
    the poor console I/O functionality in vanilla Python.  (The "rlwrap" 
    utility may help.)'''

CLI_INTRO = '''
    AndBug is a reverse-engineering debugger for the Android Dalvik virtual
    machine employing the Java Debug Wire Protocol (JDWP) to interact with
    Android applications without the need for source code.  The majority of
    AndBug's commands require the context of a connected Android device and
    a specific Android process to target, which should be specified using the
    -d and -p options.

    The debugger offers two modes -- interactive and noninteractive, and a
    comprehensive Python API for writing debugging scripts.  The interactive
    mode is accessed using:

    $ andbug shell [-d <device>] -p <process>.

    The device specification, if omitted, defaults in an identical fashion to
    the ADB debugging bridge command, which AndBug uses heavily.  The process
    specification is either the PID of the process to debug, or the name of
    the process, as found in "adb shell ps."'''

CAUTION = '''
    AndBug is NOT intended for a piracy tool, or other illegal purposes, but 
    as a tool for researchers and developers to gain insight into the 
    implementation of Android applications.  Use of AndBug is at your own risk,
    like most open source tools, and no guarantee of fitness or safety is
    made or implied.'''

SHELL_EXAMPLES = (
    'threads',
    'threads verbose=2',
    'threads "Signal Catcher" verbose=3',
    'classes',
    'classes ioactive',
    'methods com.ioactive.decoy.DecoyActivity onInit',
    'method-trace com.ioactive.decoy.DecoyActivity'
)

CLI_EXAMPLES = (
   'andbug classes -p com.ioactive.decoy',
   'andbug methods -p com.ioactive.decoy com.ioactive.decoy.DecoyActivity onInit'
)

def help_on(ctxt, cmd):
    act = andbug.command.ACTION_MAP.get(cmd)
    if act is None:
        print '!! there is no command named "%s."' % cmd
        return
    if not ctxt.can_perform(act):
        if ctxt.shell:
            print '!! %s is not available in the shell.' % cmd
        else:
            print '!! %s is only available in the shell.' % cmd
        return

    opts = "" if ctxt.shell else " [-d <dev>] -p <pid>"
    usage = "%s%s %s" % (cmd, opts, act.usage)

    if ctxt.shell:
        head = andbug.screed.section(usage)
    else:
        head = andbug.screed.section(BANNER)
        head = andbug.screed.item(usage)
    
    with head:
        andbug.screed.text(act.__doc__)

def general_help(ctxt):
    with andbug.screed.section(BANNER):
        andbug.screed.body(SHELL_INTRO if ctxt.shell else CLI_INTRO)
        andbug.screed.body(CAUTION)
    
    if not ctxt.shell:
        with andbug.screed.section("Options:"):
            for k, d in andbug.command.OPTIONS:
                with andbug.screed.item( "-%s, --%s <opt>" % (k[0], k)):
                    andbug.screed.text(d)

    with andbug.screed.section("Commands:"):
        actions = andbug.command.ACTION_LIST[:]
        actions.sort(lambda a,b: cmp(a.name, b.name))

        for row in actions:
            if ctxt.can_perform(row):
                name  =' | '.join((row.name,) + row.aliases)
                with andbug.screed.item("%s %s" % (name, row.usage)):
                    andbug.screed.text(row.__doc__.strip())

    with andbug.screed.section("Examples:"):
        for ex in (SHELL_EXAMPLES if ctxt.shell else CLI_EXAMPLES):
          andbug.screed.item(ex)

@andbug.command.action('[<command>]', proc=False)
def help(ctxt, topic = None):
    'information about how to use andbug'

    return help_on(ctxt, topic) if topic else general_help(ctxt)

########NEW FILE########
__FILENAME__ = inspect
## Copyright 2011, Felipe Barriga Richards <spam@felipebarriga.cl>.
##                 All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "inspect" command'

import andbug.command, andbug.screed

def find_object(ctxt, oid):
    for t in ctxt.sess.threads():
        for f in t.frames:
            for k, v in f.values.items():
                if type(v) is andbug.vm.Object and v.oid == oid:
                    return (v, t)
    return None

@andbug.command.action('<object-id>')
def inspect(ctxt, oid):
    'inspect an object'
    ctxt.sess.suspend()
    
    try:
        oid = long(oid)
        rtval = find_object(ctxt, oid)
        if rtval is None:
            andbug.screed.section('object <%s> not found' % oid)
        else:
            obj, thread = rtval
            with andbug.screed.section('object <%s> %s in %s'
                % (str(obj.oid), str(obj.jni), str(thread))):
                for k, v in obj.fields.items():
                    andbug.screed.item('%s=%s <%s>' % (k, v, type(v).__name__))
    except ValueError:
        print('!! error, invalid oid param. expecting <long> and got <%s>.'
            % type(oid).__name__)

    finally:
        ctxt.sess.resume()
  
########NEW FILE########
__FILENAME__ = methods
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "methods" command'

import andbug.command, andbug.options

@andbug.command.action('<class-path> [<method-query>]')
def methods(ctxt, cpath, mquery=None):
    'lists the methods of a class'
    cpath, mname, mjni = andbug.options.parse_mquery(cpath, mquery)
    title = "Methods " + ((cpath + "->" + mquery) if mquery else (cpath))
    with andbug.screed.section(title):
    	for m in ctxt.sess.classes(cpath).methods(name=mname, jni=mjni):
	    	andbug.screed.item(str(m))

########NEW FILE########
__FILENAME__ = method_trace
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "mtrace" command'

import andbug.command, andbug.screed, andbug.options
from Queue import Queue

def report_hit(t):
    t = t[0]
    try:
        with andbug.screed.section("trace %s" % t):
            f = t.frames[0]
            name = str(f.loc)
            if f.native:
            	name += ' <native>'
            with andbug.screed.item(name):
            	for k, v in f.values.items():
                	andbug.screed.item( "%s=%s" %(k, v))
    finally:
        t.resume()

def cmd_hook_methods(ctxt, cpath, mpath):
    for c in ctxt.sess.classes(cpath):
        for m in c.methods(mpath):
            l = m.firstLoc
            if l.native:
                andbug.screed.item('Could not hook native %s' % l)
                continue
            l.hook(func = report_hit)
            andbug.screed.item('Hooked %s' % l)

@andbug.command.action(
    '<method>', name='method-trace', aliases=('mt','mtrace'), shell=True
)
def method_trace(ctxt, mpath):
    'reports calls to specific dalvik method'
	
    cpath, mname, mjni = andbug.options.parse_mquery(".".join(mpath.split('.')[0:-1]),  mpath.split('.')[-1])

    with andbug.screed.section('Setting Hooks'):
		cmd_hook_methods(ctxt, cpath, mname)

    ctxt.block_exit()

########NEW FILE########
__FILENAME__ = navi
#!/usr/bin/env python

## TODO: expand the forest to use <slot>, <info>, <more>
## TODO: add <value> browser
## TODO: add <value>/<slot> browser.
## TODO: add <array>/<index> browser.
## TODO: add close button to popouts
## TODO: add static class list

import andbug, os.path, json, subprocess, threading
import re

try:
    import bottle
except ImportError:
    raise andbug.DependencyError('navi requires the "bottle" package')
    
################################################################### UTILITIES
# These functions make life a little easier, doing things like restructuring
# data structures to be easier to use from templates.
#############################################################################

def index_seq(seq):
    for i in range(len(seq)):
        yield i, seq[i]

def get_threads():
    global proc # set by navi_loop
    threads = proc.threads()[:] # TODO This workaround for view is vulgar.
    def tin(name):
        try:
            return int(re.split('<|>', name)[1])
        except Exception:
            return name

    threads.sort(lambda a, b: cmp(tin(a.name), tin(b.name)))
    return threads

def get_classes():
    global proc # set by navi_loop
    classes = proc.classes()[:] # TODO This workaround for view is vulgar.
    classes.sort(lambda a, b: cmp(a.jni, b.jni))

############################################################## INFO UTILITIES
# These functions summarize various Java objects into human-readable 
# representations.
#############################################################################

def thread_info(thread):
    info = str(thread)
    return info[7:] if info.startswith('thread ') else info

def frame_info(frame):
    info = str(frame).split( ', at ', 1)
    return info[0 if (len(info) == 1) else 1]

def truncate_ojni(jni):
    if jni.startswith('['):
        return truncate_ojni(jni[1:]) + '[]'

    if jni.startswith('L'): 
        jni = jni[1:]
        if jni.endswith(';'): jni = jni[:-1]

    jni = jni.split('/')
    if len(jni) == 1:
        return jni[0]
    else:
        return '%s.%s' % (
            '.'.join((a[0] if a else '') for a in jni[:-1]),
            jni[-1]
        )

def object_info(object):
    return '<%s>' % truncate_ojni(object.jni)

def info(value):
    if isinstance(value, andbug.Thread):
        return thread_info(value)
    if isinstance(value, andbug.Frame):
        return frame_info(value)
    if isinstance(value, andbug.Array):
        if value.jni in ('[C', '[B'):
            return repr(value).replace('\\x00', '') # HACK
    if isinstance(value, andbug.Object):
        return object_info(value)
    return value
    
############################################################## VIEW UTILITIES
# These functions summarize various Java objects into JSON views suitable for
# navigation panels.  Each view comes as a list, consisting of the name of a
# suitable constructor, and a series of arguments for the constructor.
#############################################################################

def sequence_view(value):
    seq = ['seq', value.jni]
    for val in value:
        seq.append(info(val))
    return seq
    #TODO: slots

def object_view(value):
    seq = ['obj', value.jni]
    for key, val in value.fields.iteritems():
        seq.append((key, info(val), key))
    return seq
    #TODO: slots

def view(value):
    if isinstance(value, andbug.Array):
        return sequence_view(value)
    if isinstance(value, andbug.Object):
        return object_view(value)
    return ['val', info(value)]

################################################################## DATA ROOTS
# We use static roots derived from the location of the Navi script.
#############################################################################

# note: __file__ is injected into the module by import
NAVI_ROOT = os.path.abspath( 
    os.path.join( os.path.dirname(__file__), '..' )
)
STATIC_ROOT = os.path.join( NAVI_ROOT, 'data', '' )
COFFEE_ROOT = os.path.join( NAVI_ROOT, 'coffee', '' )
bottle.TEMPLATE_PATH.append( os.path.join( NAVI_ROOT, 'view' ) )

def resolve_resource(root, rsrc):
    assert root.endswith(os.path.sep)
    rsrc = os.path.abspath(root + rsrc)
    if rsrc.startswith(root):
        return rsrc
    else:
        raise Exception('Less dots next time.')

@bottle.route( '/s/:req#.*#' )
def static_data(req):
    rsrc = resolve_resource(COFFEE_ROOT, req)  

    if rsrc.endswith('.coffee') and os.path.exists(rsrc):
        req = rsrc.replace(COFFEE_ROOT, '')[:-7] + '.js'
        try:
            subprocess.call(('coffee', '-o', STATIC_ROOT, '-c', rsrc))
        except OSError:
            pass # use the cached version, looks like coffee isn't working.
    return bottle.static_file(req, root=STATIC_ROOT)

################################################################# GLOBAL DATA
# Our Bottle server uses WSGIRef, which is a single-process asynchronous HTTP
# server.  Any given request handler can be sure that it has complete control
# of these globals, because WSGIRef is far too stupid to handle multiple
# concurrent requests.
#############################################################################

NAVI_VERNO = '0.2'
NAVI_VERSION = 'AndBug Navi ' + NAVI_VERNO

################################################################# THREAD AXIS
# The thread axis works from the process's thread list, digging into 
# individual thread frames and their associated slots.
#############################################################################

def get_object_item(val, key):
    try:
        return val.field(key)
    except KeyError:
        raise bottle.HTTPError(
        code=404, output='object does not have field "%s".' % key
    )

def get_array_item(val, key):
    key = int(key)

    try:
        return val[key]
    except KeyError:
        raise bottle.HTTPError(
        code=404, output='array does not have index %s.' % key
    )

def get_item(val, key):
    if isinstance(val, andbug.Array):
        return get_array_item(val, key)
        
    if isinstance(val, andbug.Object):
        return get_object_item(val, key)
        
    raise bottle.HTTPError(
        code=404, output='cannot navigate type %s.' % type(val).__name__
    )

def deref_frame(tid, fid):
    threads = get_threads()
    return tuple(threads[tid].frames)[fid]

def deref_value(tid, fid, key, path):
    if isinstance(path, basestring):
        path = path.split('/')

    value = deref_frame(tid, fid).value(key)
    while path:
        key = path[0]
        path = path[1:]
        value = get_item(value, key)
    
    return value

@bottle.post('/t/:tid/:fid/:key')
@bottle.post('/t/:tid/:fid/:key/:path#.*#')
def change_slot(tid, fid, key, path=None):
    'changes a value in a frame or object'
    try:
        tid, fid, key = int(tid), int(fid), str(key)
        content_type = bottle.request.get_header('Content-Type', '')
        if not content_type.startswith('application/json'):
            return {"error":"new value must be provided as JSON"}
        if path:
            path = path.split('/')
            value = deref_value(tid, fid, key, path[:-1])
            key = path[-1]
        else:
            value = deref_frame(tid, fid)
        data = bottle.request.json 
    except Exception as exc:
        #TODO: indicate that this was a deref error
        #TODO: log all non-HTTP errors to stderr
        return {"error":str(exc)}
    
    try:
        #if isinstance(value, andbug.Array):
            # return set_array_item(value, key)
        if isinstance(value, andbug.Object):
            return set_object_field(value, key, data)
        elif isinstance(value, andbug.Frame):
            return set_frame_slot(value, key, data)
        return {"error":"navi can only modify object fields and frame slots"}
    except Exception as exc:
        #TODO: indicate that this was an assignment error
        #TODO: log all non-HTTP errors to stderr
        return {"error":str(exc)}

def set_frame_slot(frame, key, data): #TEST
    'changes the value of a frame slot'
    #TODO: make sure frame.setValue throws a KeyError on failed slot update
    try:
        result = frame.setValue(key, data)
    except KeyError:
        return {"error":"navi cannot find slot %r" % key}
    
    if result:
        return {}
    return {"error":"navi could not change slot %r" % key}

def set_object_field(val, key, value): #TEST
    'changes the value of an object field'
    try:
        result = val.setField(key, value)
    except KeyError:
        return {"error":"navi cannot find field %r" % key}
    
    if result:
        return {}
    return {"error":"navi could not change field %r" % key}

#def set_array_item(val, key):
#    key = int(key)
#
#    try:
#        return val[key]
#    except KeyError:
#        raise bottle.HTTPError(
#            code=404, output='array does not have index %s.' % key
#        )

@bottle.route('/t/:tid/:fid/:key')
@bottle.route('/t/:tid/:fid/:key/:path#.*#')
def view_slot(tid, fid, key, path=None):
    'lists the values in the frame'
    
    tid, fid, key = int(tid), int(fid), str(key)
    value = deref_value(tid, fid, key, path)
    data = json.dumps(view(value))
    bottle.response.content_type = 'application/json'
    return data

###################################################### THE THREAD FOREST (TT)
# The thread-forest API produces a JSON summary of the threads and their
# frame stacks.  This is consolidated into one data structure to reduce
# round trip latency.
#############################################################################

#TODO: INSULATE
def seq_frame(frame, url):
    if not url.endswith('/'):
        url += '/'
    seq = [info(frame), frame.native]
    for key, val in frame.values.iteritems():
        seq.append((key, info(val), url + key))
    return seq

def seq_thread(thread, url):
    if not url.endswith('/'): 
        url += '/'
    seq = [info(thread)]
    frames = thread.frames
    for i in range(len(frames)):
        seq.append(seq_frame(frames[i], url + str(i)))
    return seq

def seq_process():            
    threads = get_threads()
    return list(
        seq_thread(threads[i], '/t/%s/' % i) for i in range(len(threads))
    )

@bottle.route('/tt')
def json_process():
    data = json.dumps(seq_process())
    bottle.response.content_type = 'application/json'
    return data

############################################################## FRONT SIDE (/)
# The front-side interface uses the JSON API with jQuery and jQuery UI to
# present a coherent 'one-page' interface to the user; embeds the process
# forest for efficiency.
#############################################################################

@bottle.route('/')
def frontend():
    return bottle.template('frontend', forest=json.dumps(seq_process()))

################################################################### BOOTSTRAP
# Bottle assumes that the server session will dominate the process, and does
# not handle being spun up and down on demand.  Navi does not depend heavily
# on Bottle, so this could be decoupled and put under WSGIREF.
#############################################################################

def navi_loop(p, address, port):
    # Look, bottle makes me do sad things..
    global proc
    proc = p
    
    bottle.debug(True)
    bottle.run(
        host=address,
        port=port,
        reloader=False,
        quiet=True
    )

svr = None

@andbug.command.action('[allowRemote=<False or anychar>] [port=<8080>]')
def navi(ctxt, allowRemote = False, port = None):
    'starts an http server for browsing process state'
    global svr
    if svr is not None:
        andbug.screed.section('navigation process already running')
        return

    address = '0.0.0.0' if allowRemote else 'localhost'
    port = int(port) if port else 8080

    with andbug.screed.section(
        'navigating process state at http://localhost:%i' % port
    ):
        andbug.screed.item('Process suspended for navigation.')
        ctxt.sess.suspend()
    

    svr = threading.Thread(target=lambda: navi_loop(ctxt.sess, address, port))
    svr.daemon = 1 if ctxt.shell else 0
    svr.start()
    

########NEW FILE########
__FILENAME__ = resume
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "resume" command'

import andbug.command, andbug.screed

@andbug.command.action('[<name>]', shell=True)
def resume(ctxt, name=None):
    'resumes threads in the process'
    if name is None:
        ctxt.sess.resume()
        return andbug.screed.section('Process Resumed')
    elif name == '*':
        name = None

    with andbug.screed.section('Resuming Threads'):
        for t in ctxt.sess.threads(name):
            t.resume()
            andbug.screed.item('resumed %s' % t)

########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/env python
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import shlex
import andbug.command, andbug.screed

BANNER = 'AndBug (C) 2011 Scott W. Dunlop <swdunlop@gmail.com>'

def input():
    return raw_input('>> ')

def completer(text, state):
    available_commands = andbug.command.ACTION_MAP.keys()
    options = [x for x in available_commands if x.startswith(text)]
    try:
        return options[state]
    except IndexError:
        return None


@andbug.command.action('')
def shell(ctxt):
    'starts the andbug shell with the specified process'
    if not ctxt.shell:
        try:
            import readline
            readline.set_completer(completer)
            readline.parse_and_bind("tab: complete")

        except:
            readline = None
        ctxt.shell = True
        andbug.screed.section(BANNER)

    while True:
        try:
            cmd = shlex.split(input())
        except EOFError:
            return
        andbug.screed.pollcap()
        if cmd:
            andbug.command.run_command(cmd, ctxt=ctxt)

########NEW FILE########
__FILENAME__ = source
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "methods" command'

import andbug.source, os.path

@andbug.command.action('<src-dir>')
def source(ctxt, srcdir):
    'adds a source directory for finding files' 

    if os.path.isdir(srcdir):
        if os.path.isdir(os.path.join(srcdir, "smali")):
            srcdir = os.path.join(srcdir, "smali")
        andbug.source.add_srcdir(srcdir)
    else:
        print '!! directory not found:', repr(srcdir)

########NEW FILE########
__FILENAME__ = statics
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "statics" command'

import andbug.command, andbug.options

@andbug.command.action('<class-path>')
def statics(ctxt, cpath):
    'lists the methods of a class'
    cpath = andbug.options.parse_cpath(cpath)
    for c in ctxt.sess.classes(cpath):
        andbug.screed.section("Static Fields, %s" % c)
        for k, v in c.statics.iteritems():
            andbug.screed.item("%s = %s" % (k, v))

########NEW FILE########
__FILENAME__ = suspend
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "suspend" command'

import andbug.command, andbug.screed

@andbug.command.action('[<name>]', shell=True)
def suspend(ctxt, name=None):
    'suspends threads in the process'
    if name is None:
        ctxt.sess.suspend()
        return andbug.screed.section('Process Suspended')
    elif name == '*':
        name = None

    with andbug.screed.section('Suspending Threads'):
        for t in ctxt.sess.threads(name):
            t.suspend()
            andbug.screed.item('suspended %s' % t)

########NEW FILE########
__FILENAME__ = threads
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "threads" command'

import andbug.command, andbug.screed
import re

def thread_methods(t, verbose):
    for f in t.frames:
        name = str(f.loc)
        if f.native:
            name += ' <native>'
        with andbug.screed.item(name):
            if verbose > 1:
                for k, v in f.values.items():
                    if verbose == 2:
                        andbug.screed.item("%s=<%s>" % (k, type(v).__name__))
                    else:
                        andbug.screed.item("%s=%s <%s>" % (k, v, type(v).__name__))
 
@andbug.command.action('[<name>] [verbose=<verbose level>]')
def threads(ctxt, arg1 = None, arg2 = None):
    'lists threads in the process. verbosity: 0 (thread), (1 methods), (2 vars), (3 vars data)'

    def threadId(name):
        """Extract threadId from name (e.g. "thread <2> HeapWorker" => 2)."""
        return int(re.split('<|>', str(name))[1])

    def parse_verbosity(param):
        """Return False if it's not a verbosity argument.
        If it's an invalid number return 0"""
        if param is None or param[:8] != 'verbose=':
            return False

        verbosity = int(param[8:])
        return verbosity

    def parse_args(arg1, arg2):
        if arg1 is None:
            return (None, 0)

        if arg2 is None:
            verbose = parse_verbosity(arg1)
            if verbose is False:
                return (arg1, 0)
            else:
                return (None, verbose)

        verbose = parse_verbosity(arg2)
        if verbose is False: verbose = 0
        
        return (arg1, verbose)

    name, verbose = parse_args(arg1, arg2)
    ctxt.sess.suspend()

    try:
        threads = sorted(ctxt.sess.threads(name).items, key=threadId)

        for t in threads:
            with andbug.screed.section(str(t)):
                if verbose > 0:
                    thread_methods(t, verbose)
    finally:
        ctxt.sess.resume()
        

########NEW FILE########
__FILENAME__ = thread_trace
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of the "thread trace" command'

import andbug.command, andbug.screed, andbug.options
from Queue import Queue

def report_hit(t):
    t = t[0]
    try:
        with andbug.screed.section("trace %s" % t):
            for f in t.frames:
                name = str(f.loc)
                if f.native:
                    name += ' <native>'
                with andbug.screed.item(name):
                    for k, v in f.values.items():
                        andbug.screed.item( "%s=%s" %(k, v))
    finally:
        t.resume()

@andbug.command.action('<thread-name>', aliases=('tt','ttrace'))

def thread_trace(ctxt, tname=None):
	'reports calls to specific thread in the process'
	ctxt.sess.suspend()
	with andbug.screed.section('Setting Hooks'):
		try:
			for t in ctxt.sess.threads(tname):
				t.hook(func = report_hit)
				andbug.screed.item('Hooked %s' % t)
		finally:
			ctxt.sess.resume()

########NEW FILE########
__FILENAME__ = version
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under
## the terms of version 3 of the GNU Lesser General Public License as
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'implementation of recent allocations commands'

import andbug.command, andbug.screed, andbug.options
from Queue import Queue

from andbug.vm import RequestError

@andbug.command.action(
    '', name='version', aliases=('v',), shell=False,
)
def version(ctxt):
    'Send version request.'

    conn = ctxt.sess.conn
    buf = conn.buffer()

    # 0x0101 = {1, 1} VirtualMachine.Version
    code, ret = conn.request(0x0101, buf.data())
    if code != 0:
        raise RequestError(code)

    # string    description	Text information on the VM version
    # int	jdwpMajor	Major JDWP Version number
    # int	jdwpMinor	Minor JDWP Version number
    # string	vmVersion	Target VM JRE version, as in the java.version property
    # string	vmName	        Target VM name, as in the java.vm.name property

    rets = ret.unpack("$ii$$")
    (description, jdwpMajor, jdwpMinor, vmVersion, vmName) = rets

    with andbug.screed.section('Version'):
        with andbug.screed.section('Text information on the VM version'):
            andbug.screed.item("%s" % description)
        with andbug.screed.section('JDWP Version number'):
            andbug.screed.item(str((jdwpMajor, jdwpMinor)))
        with andbug.screed.section('Target VM'):
            andbug.screed.item(str((vmVersion, vmName)))

########NEW FILE########
__FILENAME__ = command
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'''
The andbug.command module underpins the andbug command system by providing 
context and a central registry to command modules in the andbug.cmd package.

Commands for andbug are typically defined as ::

    @andbug.action(
        '<used-argument> [<extra-argument>]'
        (('debug', 'sets the debug level'))
    )
    def sample(ctxt, used, extra=None):
        ...

'''

import os, os.path, sys, getopt, inspect
import andbug.vm, andbug.cmd, andbug.source, andbug.util
import traceback
from time import sleep
from andbug.errors import *

#TODO: make short_opts, long_opts, opt_table a dynamic parsing derivative.

OPTIONS = (
    ('pid', 'the process to be debugged, by pid or name'),
    ('dev', 'the device or emulator to be debugged (see adb)'),
    ('src', 'adds a directory where .java or .smali files could be found')
)

class Context(object):
    '''
    Commands in AndBug are associated with a command Context, which contains
    options and environment information for the command.  This information
    may be reused for multiple commands within the AndBug shell.
    '''

    def __init__(self):
        self.sess = None
        self.pid = None
        self.dev = None
        self.shell = False
    
    def connect(self):
        'connects using vm.connect to the process if not already connected'
        if self.sess is not None: return
        self.sess = andbug.vm.connect(self.pid, self.dev)

    def parseOpts(self, args, options=OPTIONS, proc=True):
        'parse command options in OPTIONS format'
        short_opts = ''.join(opt[0][0] + ':' for opt in options)
        long_opts = list(opt[0] + '=' for opt in options)
        opt_table = {}

        for opt in options:
            opt_table['-' + opt[0][0]] = opt[0]
            opt_table['--' + opt[0]] = opt[0]

        opts, args = getopt.gnu_getopt(args, short_opts, long_opts)

        opts = list((opt_table[k], v) for k, v in opts)
        t = {}
        for k, v in opts: 
            if k == 'src':
                andbug.source.add_srcdir(v)
            else:
                t[k] = v
        
        if proc:
            pid = t.get('pid')
            dev = t.get('dev')

            self.findDev(dev)
            self.findPid(pid)
        return args, opts

    def findDev(self, dev=None):
        'determines the device for the command based on dev'
        if self.dev is not None: return
        self.dev = andbug.util.find_dev(dev)

    def findPid(self, pid=None):
        'determines the process id for the command based on dev, pid and/or name'        
        if self.pid is not None: return
        self.pid = andbug.util.find_pid(pid, self.dev)

    def can_perform(self, act):
        'uses the act.shell property to determine if it makes sense'
        if self.shell:
            return act.shell != False
        return act.shell != True

    def block_exit(self):
        'prevents termination outside of shells'

        if self.shell:
            # we do not need to block_exit, readline is doing a great
            # job of that for us.
            return

        while True:
            # the purpose of the main thread becomes sleeping forever
            # this is because Python's brilliant threading model only
            # allows the main thread to perceive CTRL-C.
            sleep(3600)
        
    def perform(self, cmd, args):
        'performs the named command with the supplied arguments'
        act = ACTION_MAP.get(cmd)

        if not act:
            perr('!! command not supported: "%s."' % cmd)
            return False

        if not self.can_perform(act):
            if ctxt.shell:
                perr('!! %s is not available in the shell.' % cmd)
            else:
                perr('!! %s is only available in the shell.' % cmd)
            return False

        args, opts = self.parseOpts(args, act.opts, act.proc)
        argct = len(args) + 1 

        if argct < act.min_arity:
            perr('!! command "%s" requires more arguments.' % cmd)
            return False
        elif argct > act.max_arity:
            perr('!! too many arguments for command "%s."' % cmd)
            return False

        opts = filter(lambda opt: opt[0] in act.keys, opts)
        kwargs  = {}
        for k, v in opts: 
            kwargs[k] = v

        if act.proc: self.connect()
        try:
            act(self, *args, **kwargs)
        except Exception as exc:
            dump_exc(exc)
            return False

        return True

def dump_exc(exc):       
    tp, val, tb = sys.exc_info()
    with andbug.screed.section("%s: %s" % (tp.__name__, val)):
        for step in traceback.format_tb(tb):
            step = step.splitlines()
            with andbug.screed.item(step[0].strip()):
                for line in step[1:]:
                    andbug.screed.line(line.strip())

ACTION_LIST = []
ACTION_MAP = {}

def bind_action(name, fn, aliases):
    ACTION_LIST.append(fn)
    ACTION_MAP[name] = fn
    for alias in aliases:
        ACTION_MAP[alias] = fn

def action(usage, opts = (), proc = True, shell = None, name = None, aliases=()):
    'decorates a command implementation with usage and argument information'
    def bind(fn):
        fn.proc = proc
        fn.shell = shell
        fn.usage = usage
        fn.opts = OPTIONS[:] + opts
        fn.keys = list(opt[0] for opt in opts)
        fn.aliases = aliases
        spec = inspect.getargspec(fn)
        defct = len(spec.defaults) if spec.defaults else 0
        argct = len(spec.args) if spec.args else 0
        fn.min_arity = argct - defct
        fn.max_arity = argct
        fn.name = name or fn.__name__.replace('_', '-')

        bind_action(fn.name, fn, aliases)
    return bind

CMD_DIR_PATH = os.path.abspath(os.path.join( os.path.dirname(__file__), "cmd" ))

def load_commands():
    'loads commands from the andbug.cmd package'
    for name in os.listdir(CMD_DIR_PATH):
        if name.startswith( '__' ):
            continue
        if name.endswith( '.py' ):
            name = 'andbug.cmd.' + name[:-3]
            try:
                __import__( name )
            except andbug.errors.DependencyError:
                pass # okay, okay..

def run_command(args, ctxt = None):
    'runs the specified command with a new context'
    if ctxt is None:
        ctxt = Context()
            
    for item in args:
        if item in ('-h', '--help', '-?', '-help'):
            args = ('help', args[0])
            break
    
    return ctxt.perform(args[0], args[1:])

__all__ = (
    'run_command', 'load_commands', 'action', 'Context', 'OptionError'
)

########NEW FILE########
__FILENAME__ = data
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

from threading import Lock

class multidict(dict):
    '''
    boring old multidicts..
    '''
    def get(self, key, alt=[]):
        return dict.get(self, key, alt)
    
    def put(self, key, val):
        try:
            dict.__getitem__(self, key).append(val)
        except KeyError:
            v = view()
            v.append(val)
            dict.__setitem__(self, key, v)

    def __setitem__(self, key, val):
        self.put(key, val)
    
    def __getitem__(self, key):
        return self.get(key)

class pool(object):
    '''
    a pool of singleton objects such that, for any combination of constructor 
    and 1 or more initializers, there may be zero or one objects; attempting
    to reference a nonexisted object causes it to be created.

    example:
        def t(a): return [a,0]
        p = pool()
        t1 = p(t,1)
        t2 = p(t,2)
        p(t,1)[1] = -1
        # t1[1] is now -1, not 1
    '''
    def __init__(self):
        self.pools = {}
        self.lock = Lock()
    def __call__(self, *ident):
        with self.lock:
            pool = self.pools.get(ident)
            if pool is None:
                pool = ident[0](*ident[1:])
                self.pools[ident] = pool
            return pool

class view(object):
    '''
    a homogenous collection of objects that may be acted upon in unison, such
    that calling a method on the collection with given arguments would result
    in calling that method on each object and returning the results as a list
    '''

    def __init__(self, items = []):
        self.items = list(items)
    def __repr__(self):
        return '(' + ', '.join(str(item) for item in self.items) + ')'
    def __len__(self):
        return len(self.items)
    def __getitem__(self, index):
        return self.items[index]
    def __iter__(self):
        return iter(self.items)
    def __getattr__(self, key):
        def poolcall(*args, **kwargs):
            t = tuple( 
                getattr(item, key)(*args, **kwargs) for item in self.items
            )
            for n in t:
                if not isinstance(n, view):
                    return view(t)
            return view(flatten(t))
        poolcall.func_name = '*' + key
        return poolcall
    def get(self, key):
        return view(getattr(item, key) for item in self.items)
    def set(self, key, val):
        for item in self.items:
            setattr(item, key, val)
    def append(self, val):
        self.items.append(val)

def flatten(seq):
    for ss in seq:
        for s in ss:
            yield s

def defer(func, name):
    '''
    a property decorator that, when applied, specifies a property that relies
    on the execution of a costly function for its resolution; this permits the
    deferral of evaluation until the first time it is needed.

    unlike other deferral implementation, this one accepts the reality that the
    product of a single calculation may be multiple properties
    '''
    def fget(obj, type=None):   
        try:
            return obj.props[name]
        except KeyError:
            pass
        except AttributeError:
            obj.props = {}

        obj.props[name] = None
        func(obj)
        return obj.props[name]
    
    def fset(obj, value):
        try:
            obj.props[name] = value
        except AttributeError:
            obj.props = {name : value}

    fget.func_name = 'get_' + name
    fset.func_name = 'set_' + name
    return property(fget, fset)

if __name__ == '__main__':
    pool = pool()

    class classitem:
        def __init__(self, cid):
            self.cid = cid
        def __repr__(self):
            return '<class %s>' % self.cid

    class methoditem:
        def __init__(self, cid, mid):
            self.cid = cid
            self.mid = mid
        def __repr__(self):
            return '<method %s:%s>' % (self.cid, self.mid)
        def classitem(self):
            return pool(classitem, self.cid)
        def load_line_table(self):
            print "LOAD-LINE-TABLE", self.cid, self.mid
            self.first = 1
            self.last = 1
            self.lines = []
        def trace(self):
            print "TRACE", self.cid, self.mid

        first = defer(load_line_table, 'first')
        last =  defer(load_line_table, 'last')
        lines = defer(load_line_table, 'lines')

    m1 = pool(methoditem, 'c1', 'm1')
    m2 = pool(methoditem, 'c1', 'm2')
    m3 = pool(methoditem, 'c2', 'm3')
    v = view((m1,m2,m3))
    print v
    print v.trace
    print v.trace()
    print (v.get('first'))
    print (v.get('last'))
    print v.classitem()
    print list(m for m in v)

########NEW FILE########
__FILENAME__ = errors
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

import sys

class UserError(Exception):
    'indicates an error in how AndBug was used'
    pass

class OptionError(UserError):
    'indicates an error parsing an option supplied to a command'
    pass

class ConfigError(UserError):
    'indicates an error in the configuration of AndBug'
    pass

class DependencyError(UserError):
    'indicates that an optional dependency was not found'
    pass

class VoidError(UserError):
    'indicates a process returned a nil object'

def perr(*args):
    print >>sys.stderr, ' '.join(map(str, args))


########NEW FILE########
__FILENAME__ = log
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.
   
import os, sys, time
from cStringIO import StringIO

def blocks(seq, sz):
    ofs = 0
    lim = len(seq)
    while ofs < lim:
        yield seq[ofs:ofs+sz]
        ofs += sz

def censor(seq):
    for ch in seq:
        if ch < '!': 
            yield '.'
        elif ch > '~':
            yield '.'
        else:
            yield ch

def format_hex(data, indent="", width=16, out=None):
    if out == None:
        out = StringIO()
        strout = True
    else:
        strout = False

    indent += "%08x:  "
    ofs = 0
    for block in blocks(data, width):
        out.write(indent % ofs)
        out.write(' '.join(map(lambda x: x.encode('hex'), block)))
        if len(block) < width:
            out.write( '   ' * (width - len(block)) )
        out.write('  ')
        out.write(''.join(censor(block)))
        out.write(os.linesep)
        ofs += len(block)

    if strout:
        return out.getvalue()

def parse_hex(dump, out=None):
    if out == None:
        out = StringIO()
        strout = True
    else:
        strout = False

    for row in dump.splitlines():
        row = row.strip().split('  ')
        block = row[1].strip().split(' ')
        block = ''.join(map(lambda x: chr(int(x, 16)), block))
        out.write(block)

    if strout:
        return out.getvalue()

class LogEvent(object):
    def __init__(self, time, tag, meta, data):
        self.time = time
        self.tag = tag
        self.meta = meta
        self.data = data or ''
    
    def __str__(self):
        return "%s %s %s\n%s" % (
            self.tag, self.time, self.meta, 
            format_hex(self.data, indent="    ")
        )

class LogWriter(object):
    def __init__(self, file=sys.stdout):
        self.file = file
        
    def writeEvent(self, evt):
        self.file.write(str(evt))

class LogReader(object):
    def __init__(self, file=sys.stdin):
        self.file = file
        self.last = None
    
    def readLine(self):
        if self.last is None:
            line = self.file.readline().rstrip()
        else:
            line = self.last
            self.last = None
        return line

    def pushLine(self, line):
        self.last = line

    def readEvent(self):
        line = self.readLine()
        if not line: return None
        if line[0] == ' ':
            return self.readEvent() # Again..
         
        tag, time, meta = line.split(' ', 3)
        time = int(time)
        data = []

        while True:
            line = self.readLine()
            if line.startswith( '    ' ):
                data.append(line)
            else:
                self.pushLine(line)
                break
                
        if data:
            data = parse_hex('\n'.join(data))
        else:
            data = ''

        return LogEvent(time, tag, meta, data)

stderr = LogWriter(sys.stderr)
stdout = LogWriter(sys.stdout)

def error(tag, meta, data = None):
    now = int(time.time())
    stderr.writeEvent(LogEvent(now, tag, meta, data))

def info(tag, meta, data = None):
    now = int(time.time())
    stdout.writeEvent(LogEvent(now, tag, meta, data))

def read_log(path=None, file=None):
    if path is None:
        if file is None:
            reader = LogReader(sys.stdin)
        else:
            reader = LogReader(file)
    return reader

########NEW FILE########
__FILENAME__ = options
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

class ParseError(Exception):
    def __init__(self, reason, option):
        self.reason = reason
        self.option = option

    def __str__(self):
        return '%s: %r.' % (self.reason, self.option)

def parse_cpath(path):
	if path.startswith('L') and path.endswith(';') and ('.' not in path):
		return path
	elif path.startswith('L') or path.endswith(';') or ('/' in path):
		raise ParseError('could not determine if path is a JNI or logical class path', path)
	else:
		return'L' + path.replace('.', '/') + ';'

def parse_mspec(mspec):
    if (mspec == '*') or (not mspec):
        return None, None
    
    s = mspec.find('(')
    if s < 0:
        return mspec, None

    return mspec[:s], mspec[s:]

def parse_mquery(cp, ms):
    #TODO: support class->method syntax.
    cp = parse_cpath(cp)
    mn, mj = parse_mspec(ms)
    return cp, mn, mj

'''
def parse_mpath(path):
    'given a JNI or logical method path, yields class-jni, meth-name, args-jni and retn-jni'

    if '(' in path:
        clsmet, argret = path.split('(', 1)    
    else:
        clsmet, argret = path, None
    
    if argret and (')' in argret):
        arg, ret = argret.rsplit(')', 1)    
    else:
        arg, ret = None, None
    
    if '.' in clsmet:
        cls, met = clsmet.rsplit('.', 1)
    elif ';' in clsmet:
        cls, met = clsmet.rsplit(';', 1)
        cls += ';'
    else:
        cls, met = None, clsmet

    if cls is not None:
        cls = parse_cpath(cls)
                
    return cls, met, arg, ret
'''

def format_mjni(name, args, retn):
    return '%s(%s)%s' % (name, args, retn)


########NEW FILE########
__FILENAME__ = proto
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'''
The andbug.proto module abstracts the JDWP wire protocol into a more 
manageable request/response API using an input worker thread in the
background and a number of mutexes to control contests for output.
'''

import socket, tempfile
import andbug.util
from threading import Thread, Lock
from andbug.jdwp import JdwpBuffer
from Queue import Queue, Empty as EmptyQueue

class EOF(Exception):
    'signals that an EOF has been encountered'
    def __init__(self, inner = None):
        Exception.__init__(
            self, str(inner) if inner else "EOF"
        )

class HandshakeError(Exception):
    'signals that the JDWP handshake failed'
    def __init__(self):
        Exception.__init__(
            self, 'handshake error, received message did not match'
        )

class ProtocolError(Exception):
    pass

HANDSHAKE_MSG = 'JDWP-Handshake'
HEADER_FORMAT = '4412'
IDSZ_REQ = (
    '\x00\x00\x00\x0B' # Length
    '\x00\x00\x00\x01' # Identifier
    '\x00'             # Flags
    '\x01\x07'         # Command 1:7
)

def forward(pid, dev=None):
    'constructs an adb forward for the context to access the pid via jdwp'
    if dev:
        dev = andbug.util.find_dev(dev)
    pid = andbug.util.find_pid(pid)
    temp = tempfile.mktemp()
    cmd = ('-s', dev) if dev else ()
    cmd += ('forward', 'localfilesystem:' + temp,  'jdwp:%s' % pid)
    andbug.util.adb(*cmd)
    return temp

def connect(addr, portno = None, trace=False):
    'connects to an AF_UNIX or AF_INET JDWP transport'
    if addr and portno:
        conn = socket.create_connection((addr, portno))
    elif isinstance(addr, int):
        conn = socket.create_connection(('127.0.0.1', addr))
    else:
        conn = socket.socket(socket.AF_UNIX)
        conn.connect(addr)

    def read(amt):
        'read wrapper internal to andbug.proto.connect'
        req = amt
        buf = ''
        while req:
            pkt = conn.recv(req)
            if not pkt: raise EOF()
            buf += pkt
            req -= len(pkt)
        if trace:
            print ":: RECV:", repr(buf)
        return buf 
    
    def write(data):
        'write wrapper internal to andbug.proto.connect'
        try:
            if trace:
                print ":: XMIT:", repr(data)
            conn.sendall(data)
        except Exception as exc:
            raise EOF(exc)
        
    p = Connection(read, write)
    p.start()
    return p

class Connection(Thread):
    '''
    The JDWP Connection is a thread which abstracts the asynchronous JDWP protocol
    into a more synchronous one.  The thread will listen for packets using the
    supplied read function, and transmit them using the write function.  

    Requests are sent by the processor using the calling thread, with a mutex 
    used to protect the write function from concurrent access.  The requesting
    thread is then blocked waiting on a response from the processor thread.

    The Connectionor will repeatedly use the read function to receive packets, which
    will be dispatched based on whether they are responses to a previous request,
    or events.  Responses to requests will cause the requesting thread to be
    unblocked, thus simulating a synchronous request.
    '''

    def __init__(self, read, write):
        Thread.__init__(self)
        self.xmitbuf = JdwpBuffer()
        self.recvbuf = JdwpBuffer()
        self._read = read
        self.write = write
        self.initialized = False
        self.next_id = 3
        self.bindqueue = Queue()
        self.qmap = {}
        self.rmap = {}
        self.xmitlock = Lock()

    def read(self, sz):
        'read size bytes'
        if sz == 0: return ''
        pkt = self._read(sz)
        if not len(pkt): raise EOF()
        return pkt

    ###################################################### INITIALIZATION STEPS
    
    def writeIdSzReq(self):
        'write an id size request'
        return self.write(IDSZ_REQ)

    def readIdSzRes(self):
        'read an id size response'
        head = self.readHeader()
        if head[0] != 20:
            raise ProtocolError('expected size of an idsize response')
        if head[2] != 0x80:
            raise ProtocolError(
                'expected first server message to be a response'
            )
        if head[1] != 1:
            raise ProtocolError('expected first server message to be 1')

        sizes = self.recvbuf.unpack( 'iiiii', self.read(20) )
        self.sizes = sizes
        self.recvbuf.config(*sizes)
        self.xmitbuf.config(*sizes)
        return None

    def readHandshake(self):
        'read the jdwp handshake'
        data = self.read(len(HANDSHAKE_MSG))
        if data != HANDSHAKE_MSG:
            raise HandshakeError()
        
    def writeHandshake(self):
        'write the jdwp handshake'
        return self.write(HANDSHAKE_MSG)

    ############################################### READING / PROCESSING PACKETS
    
    def readHeader(self):
        'reads a header and returns [size, id, flags, event]'
        head = self.read(11)
        data = self.recvbuf.unpack(HEADER_FORMAT, head)
        data[0] -= 11
        return data
    
    def process(self):
        'invoked repeatedly by the processing thread'

        size, ident, flags, code = self.readHeader() #TODO: HANDLE CLOSE
        data = self.read(size) #TODO: HANDLE CLOSE
        try: # We process binds after receiving messages to prevent a race
            while True:
                self.processBind(*self.bindqueue.get(False))
        except EmptyQueue:
            pass

        #TODO: update binds with all from bindqueue
        
        if flags == 0x80:
            self.processResponse(ident, code, data)
        else:
            self.processRequest(ident, code, data)

    def processBind(self, qr, ident, chan):
        'internal to i/o thread; performs a query or request bind'
        if qr == 'q':
            self.qmap[ident] = chan
        elif qr == 'r':
            self.rmap[ident] = chan

    def processRequest(self, ident, code, data):
        'internal to the i/o thread w/ recv ctrl; processes incoming request'
        chan = self.rmap.get(code)
        if not chan: return #TODO
        buf = JdwpBuffer()
        buf.config(*self.sizes)
        buf.prepareUnpack(data)
        return chan.put((ident, buf))
        
    def processResponse(self, ident, code, data):
        'internal to the i/o thread w/ recv ctrl; processes incoming response'
        chan = self.qmap.pop(ident, None)
        if not chan: return
        buf = JdwpBuffer()
        buf.config(*self.sizes)
        buf.prepareUnpack(data)
        return chan.put((code, buf))

    def hook(self, code, chan):
        '''
        when code requests are received, they will be put in chan for
        processing
        '''

        with self.xmitlock:
            self.bindqueue.put(('r', code, chan))
        
    ####################################################### TRANSMITTING PACKETS
    
    def acquireIdent(self):
        'used internally by the processor; must have xmit control'
        ident = self.next_id
        self.next_id += 2
        return ident

    def writeContent(self, ident, flags, code, body):
        'used internally by the processor; must have xmit control'

        size = len(body) + 11
        self.xmitbuf.preparePack(11)
        data = self.xmitbuf.pack(
            HEADER_FORMAT, size, ident, flags, code
        )
        self.write(data)
        return self.write(body)

    def request(self, code, data='', timeout=None):
        'send a request, then waits for a response; returns response'
        queue = Queue()

        with self.xmitlock:
            ident = self.acquireIdent()
            self.bindqueue.put(('q', ident, queue))
            self.writeContent(ident, 0x0, code, data)
        
        try:
            return queue.get(1, timeout)
        except EmptyQueue:
            return None

    def buffer(self):
        'returns a JdwpBuffer configured for this connection'
        buf = JdwpBuffer()
        buf.config(*self.sizes)
        return buf
        
    ################################################################# THREAD API
    
    def start(self):
        'performs handshaking and solicits configuration information'
        self.daemon = True

        if not self.initialized:
            self.writeHandshake()
            self.readHandshake()
            self.writeIdSzReq()
            self.readIdSzRes()
            self.initialized = True
            Thread.start(self)
        return None

    def run(self):
        'runs forever; overrides the default Thread.run()'
        try:
            while True:
                self.process()
        except EOF:
            return
    

########NEW FILE########
__FILENAME__ = screed
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'''
Screed (plural Screeds)

1. A long discourse or harangue.
2. A piece of writing.
3. A tool, usually a long strip of wood or other material, for producing a smooth, flat surface on, for example, a concrete floor or a plaster wall.
4. A smooth flat layer of concrete or similar material.
5. A python module for formatting text output

Written language has evolved concurrent with the advent of movable type and
the information age, introducing a number of typographic conventions that are
used to impose structure.  The Screed format employs a subset of these 
conventions to structure output in way that is easily parsed by software or 
read in a terminal.

Screed is used by AndBug to format command output as well.

'''

import textwrap
import sys
import subprocess
import re
import andbug.log

rx_blocksep = re.compile('[\r\n][ \t]*[\r\n]+')
rx_linesep = re.compile('[\r\n][ \t]*')

def body(data):
    blocks = rx_blocksep.split(data.strip())

    for block in blocks:
        block = block.strip()
        block = rx_linesep.sub(' ', block)
        if not block: continue
        if block.startswith('-- '):
            item(block[3:])
        else:
            text(block)

def tput(attr, alt=None):
    p = subprocess.Popen(('tput', attr), stdout=subprocess.PIPE, stderr=None)
    p.wait()
    if p.returncode:
        return alt
    o, _ = p.communicate()
    return int(o)

class area(object):
    def __init__(self, title):
        self.title = title
        self.create()
    def __enter__(self):
        self.enter()
    def __exit__(self, *_):
        self.exit()
        return False

    def enter(self):
        pass 
    def exit(self):
        pass
    def create(self):
        pass

class section(area):
    def create(self):
        output().create_section(self.title)
    def enter(self):
        output().enter_section(self.title)
    def exit(self):
        output().exit_section(self.title)

class item(area):
    def create(self):
        output().create_item(self.title)
    def enter(self):
        output().enter_item(self.title)
    def exit(self):
        output().exit_item(self.title)

class meta(area):
    def create(self):
        output().create_item(self.title)
    def enter(self):
        output().enter_item(self.title)
    def exit(self):
        output().exit_item(self.title)

class refer(area):
    def create(self):
        output().create_refer(self.title)
    def enter(self):
        output().enter_refer(self.title)
    def exit(self):
        output().exit_refer(self.title)

def text(data):
    output().create_text(data)

def line(data, row=None):
    output().create_line(data, row)

def dump(data):
    output().create_dump(data)


class surface(object):
    def __init__(self, output=None):
        if output is None:
            output = sys.stdout
        self.output = output
        self.tty = self.output.isatty()
        self.indent = []
        self.textwrap = textwrap.TextWrapper()

    def __call__(self):
        return self

    @property
    def current_indent(self):
        return self.indent[-1] if self.indent else ''

    def push_indent(self, indent):
        self.indent.append(indent)       
        self.textwrap.subsequent_indent = indent

    def pop_indent(self):
        self.indent = self.indent[:-1]
        self.textwrap.subsequent_indent = self.current_indent

    def write(self, data):
        self.output.write(data)
    
    def newline(self):
        self.write('\n')

    def create_section(self, title):
        pass
                        
    def enter_section(self, title):
        pass

    def exit_section(self, title):
        pass

    def create_item(self, title):
        pass
                        
    def enter_item(self, title):
        pass

    def exit_item(self, title):
        pass

    def create_dump(self, data):
        width = self.width
        indent = self.current_indent

        if self.width is None:
            width = 16
        else:
            width -= len(self.indent)
            width -= 13 # overhead
            width = width / 4 # dd_c

        hex = andbug.log.format_hex(data, self.current_indent, width)
        self.write(hex)
        self.newline()

    def create_line(self, line, row = None):
        if row is None:
            self.wrap_line(self.current_indent + line)
        else:
            row = "%4i: " % row
            self.wrap_line(self.current_indent + row + line, " " * len(row))

    def wrap_line(self, line, indent=None):
        if self.width is None:
            self.write(line)
            self.newline()
            return
        if indent is not None:
            self.textwrap.subsequent_indent = indent
            lines = self.textwrap.wrap(line)
            self.textwrap.subsequent_indent = self.current_indent
        else:
            lines = self.textwrap.wrap(line)

        self.write('\n'.join(lines))
        self.newline()                

class scheme(object):
    def __init__(self, binds = []):
        self.c16 = {}
        self.c256 = {}

        for bind in binds:
            self.bind(*bind)

    def bind(self, tag, c16, c256 = None):
        if c16 > 7:
            c16 = '\x1B[1;3' + str(c16 - 8) + 'm'
        else:
            c16 = '\x1B[0;3' + str(c16) + 'm'

        if c256 is not None:
            c256 = '\x1B[38;05;' + str(c256) + 'm'
        else:
            c256 = c16

        self.c16[tag] = c16
        self.c256[tag] = c256

    def load(self, tag, depth):
        if not depth: return ''
        return (self.c256 if (depth == 256) else self.c16).get(tag, '\x1B[0m')

redmedicine = scheme((
    ('##',  9,  69),
    ('--', 15, 254),
    ('$$',  7, 146),
    ('::', 11, 228),
    ('//',  7, 242),
))

class ascii(surface):
    def __init__(self, output=None, width=None, depth=None, palette=redmedicine):
        surface.__init__(self, output)
        if width is None:
            width = 79
        if depth is None:
            depth = 16 if self.tty else 0
        self.width = width
        self.depth = depth
        if self.tty:
            self.pollcap()
        self.next_indent = None
        self.context = []
        self.prev_tag = ''
        self.palette = palette

    def transition(self, next):
        prev = self.prev_tag
        self.prev_tag = next
        #print "TRANSITION", repr(prev), "->", repr(next)

        if prev == '00':
            return # Nothing to do.
        elif next == '00':
            return # Also nothing to do.
        elif prev == '  ':
            return # first children are never set off.
        elif (prev == '$$') and (next == '$$'):
            self.newline()
        elif prev == next:  
            return # Identical children are not set off.
        else:
            self.newline()
            self.prev_tag = '00'

    def create_section(self, title):
        self.create_tagged_area( '##', title)

    def enter_section(self, title):
        self.enter_tagged_area()
    
    def exit_section(self, title):
        self.exit_tagged_area()

    def create_item(self, title):
        self.create_tagged_area( '--', title)

    def enter_item(self, title):
        self.enter_tagged_area()
    
    def exit_item(self, title):
        self.exit_tagged_area()

    def create_meta(self, title):
        self.create_tagged_area( '//', title)

    def enter_meta(self, title):
        self.enter_tagged_area()
    
    def exit_meta(self, title):
        self.exit_tagged_area()

    def create_refer(self, title):
        self.create_tagged_area( '::', title)

    def enter_refer(self, title):
        self.enter_tagged_area()
    
    def exit_refer(self, title):
        self.exit_tagged_area()

    def create_text(self, text):
        self.transition('$$')
        self.write(self.palette.load('$$', self.depth))
        self.wrap_line(self.current_indent + text)
        self.write("\x1B[01m")

    def create_tagged_area(self, tag, banner):
        self.transition(tag)
        self.write(self.palette.load(tag, self.depth))
        tag += ' '
        self.next_indent = self.current_indent + ' ' * len(tag)
        self.wrap_line(self.current_indent + tag + banner, self.next_indent)
        self.write("\x1B[0m")

    def enter_tagged_area(self):
        self.push_indent(self.next_indent)
        self.context.append(self.prev_tag)
        #print 'ENTER', repr(self.prev_tag), "-> '  '"
        self.prev_tag = '  '
    
    def exit_tagged_area(self):
        self.pop_indent()
        next = self.context.pop(-1)
        if self.prev_tag != '00':
            self.prev_tag = next
        #print 'EXIT ->', repr(self.prev_tag)

    def pollcap(self):
        if not self.tty: return
        self.width = tput('cols', self.width)
        self.depth = tput('colors', self.depth)        
        self.textwrap.width = self.width

OUTPUT = None
PALETTE = None

def scheme():
    if PALETTE is None:
        return redmedicine
    else:
        return PALETTE

def output():
    global OUTPUT
    if OUTPUT is None:
        OUTPUT = ascii(palette=scheme())
    return OUTPUT

if __name__ == '__main__':
    with section('Introduction'):
        text('''Since the sentence detection algorithm relies on string.lowercase for the definition of lowercase letter, and a convention of using two spaces after a period to separate sentences on the same line, it is specific to English-language texts.''')
        text('''If true, TextWrapper attempts to detect sentence endings and ensure that sentences are always separated by exactly two spaces. This is generally desired for text in a monospaced font. However, the sentence detection algorithm is imperfect: it assumes that a sentence ending consists of a lowercase letter followed by one of '.', '!', or '?', possibly followed by one of '"' or "'", followed by a space. One problem with this is algorithm is that it is unable to detect the difference.''')
    with section('Points of Interest'):
        item('''String that will be prepended to the first line of wrapped output. Counts towards the length of the first line.''')
        text('''this is some inbetween text''')
        item('''This is a much shorter item.''')
    with section('Data'):
        dump(open('/dev/urandom').read(1024))
    with section('Conclusion'):
        text('''The textwrap module provides two convenience functions, wrap() and fill(), as well as TextWrapper, the class that does all the work, and a utility function dedent(). If you're just wrapping or filling one or two text strings, the convenience functions should be good enough; otherwise, you should use an instance of TextWrapper for efficiency.''')

def pollcap():
    output().pollcap()

########NEW FILE########
__FILENAME__ = source
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

'''
andbug.source converts andbug.vm.Locations into file lines using either the
original java sources or the product of apktool.
'''

import os
import os.path
import re
import andbug.screed

SOURCES = []
SEPARATOR = os.pathsep
if SEPARATOR == ':': # fuck you, python.. this isn't macos 9!
    SEPARATOR = '/'

rx_delim = re.compile('[./]')

def add_srcdir(path):
    path = os.path.expanduser(path)
    path = os.path.abspath(path)
    if not path.endswith(SEPARATOR):
        path += SEPARATOR
    SOURCES.insert(0, path)

def find_source(cjni):
    if cjni.startswith("L") and cjni.endswith(";"):
        cjni = cjni[1:-1]
    cpath = rx_delim.sub(SEPARATOR, cjni)
    for src in SOURCES:
        csp = os.path.normpath(src + cpath)
        if not csp.startswith(src):
            continue # looks like someone's playing games with ..
        if os.path.isfile(csp + ".java"):
            return csp + ".java"
        if os.path.isfile(csp + ".smali"):
            return csp + ".smali"
    return False

def normalize_range(count, first, last):
    if first < 0: 
        first = count + first
    if last < 0:
        last = count + first
    if first >= count:
        first = count - 1
    if last >= count:
        last = count - 1
    if first > last: 
        first, last = first, last

    return first, last + 1

def load_source(cjni, first=0, last=-1):
    src = find_source(cjni)
    if not src: 
        return False
    lines = open(src).readlines()
    if not lines:
        return False
    first, last = normalize_range(len(lines), first, last)
    d = map(lambda x, y: (x, y), range(first, last), lines[first:last])
    return d

import itertools

def dump_source(lines, head = None):
    ctxt = [None]
    
    def enter_area(func, title):
        exit()
        title = title.strip()
        ctxt[0] = func(title)
        ctxt[0].enter()
    def item(title):
        enter_area(andbug.screed.item, title)
    def section(title):
        enter_area(andbug.screed.section, title)
    def meta(title):
        enter_area(andbug.screed.meta, title)
    def refer(title):
        enter_area(andbug.screed.refer, title)
    def exit():
        if ctxt[0] is not None:
            ctxt[0].exit()
        ctxt[0] = None

    if head:
        section(head)
    for row, line in lines:
        line = line.strip()
        if not line: continue
        lead = line[0]
        if lead == '.':
            if line.startswith(".method "):
                section(line[1:])
            elif line.startswith(".end"):
                exit()
            elif line == '...':
                andbug.screed.line(line, row)
            else:
                item(line[1:])
        elif line.startswith(":"):
            refer(line[1:])
        elif line.startswith("#"):
            meta(line[1:])
        elif line == '*/}':
            pass # meh
        elif line.endswith('{/*'):
            pass # meh 
        else:
            andbug.screed.line(line, row)
    exit()

########NEW FILE########
__FILENAME__ = util
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## Redistribution and use in source and binary forms, with or without 
## modification, are permitted provided that the following conditions are 
## met:
## 
##    1. Redistributions of source code must retain the above copyright 
##       notice, this list of conditions and the following disclaimer.
## 
##    2. Redistributions in binary form must reproduce the above copyright 
##       notice, this list of conditions and the following disclaimer in the
##       documentation and/or other materials provided with the distribution.
## 
## THIS SOFTWARE IS PROVIDED BY SCOTT DUNLOP 'AS IS' AND ANY EXPRESS OR 
## IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
## OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
## IN NO EVENT SHALL SCOTT DUNLOP OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
## INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
## (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
## SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) 
## HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, 
## STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
## ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
## POSSIBILITY OF SUCH DAMAGE.

import subprocess, os, os.path
import re
from andbug.errors import *
RE_INT = re.compile('^[0-9]+$')

class ShellException( Exception ):
    def __init__( self, command, output, status ):
        self.command = command
        self.output = output
        self.status = status

def printout( prefix, data ):
    data = data.rstrip()
    if not data: return ''
    print prefix + data.replace( '\n', '\n' + prefix )

def sh( command, no_echo=True, no_fail=False, no_wait=False ):
    if not no_echo: 
        printout( '>>> ', repr( command ) )

    process = subprocess.Popen( 
        command,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
        stdin = None,
        shell = True if isinstance( command, str ) else False
    )
    
    if no_wait: return process

    output, _ = process.communicate( )
    status = process.returncode

    if status: 
        if not no_echo: printout( '!!! ', output )
        if not no_fail: raise ShellException( command, output, status )
    else:
        if not no_echo: printout( '::: ', output )

    return output

def which( utility ):
    for path in os.environ['PATH'].split( os.pathsep ):
        path = os.path.expanduser( os.path.join( path, utility ) )
        if os.path.exists( path ):
            return path

def test( command, no_echo=False ):
    process = subprocess.Popen( 
        command,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
        stdin = None,
        shell = True if isinstance( command, str ) else False
    )
    
    output, _ = process.communicate( )
    return process.returncode

def cat(*seqs):
    for seq in seqs:
        for item in seq:
            yield item

def seq(*args):
    return args

def adb(*args):
    #print adb, ' '.join(map(str, args))
    try:
        return sh(seq("adb", *args))
    except OSError:
        raise ConfigError('could not find "adb" from the Android SDK in your PATH')

def find_dev(dev=None):
    'determines the device for the command based on dev'
    if dev:
        if dev not in map( 
            lambda x: x.split()[0], 
            adb('devices').splitlines()[1:-1]
        ):
            raise OptionError('device serial number not online')
    else:
        lines = adb('devices').splitlines()
        if len(lines) != 3:
            raise OptionError(
                'you must specify a device serial unless there is only'
                ' one online'
            )
        dev = lines[1].split()[0]
        
    return dev

def find_pid(pid, dev=None):
    'determines the process id for the command based on dev, pid and/or name'

    ps = ('-s', dev, 'shell', 'ps') if dev else ('shell', 'ps') 
    ps = adb(*ps)
    ps = ps.splitlines()
    head = ps[0]
    ps = (p.split() for p in ps[1:])

    if head.startswith('PID'):
        ps = ((int(p[0]), p[-1]) for p in ps)
    elif head.startswith('USER'):
        ps = ((int(p[1]), p[-1]) for p in ps)
    else:
        raise ConfigError('could not parse "adb shell ps" output')
    
    if RE_INT.match(str(pid)):
        pid = int(pid)
        ps = list(p for p in ps if p[0] == pid)
        if not ps:
            raise OptionError('could not find process ' + pid)
    elif pid:
        ps = list(ps)
        ps = list(p for p in ps if p[1] == pid)
        if not ps:
            raise OptionError('could not find process ' + pid)
        pid = ps[0][0]
    else:
        raise OptionError('process pid or name must be specified')

    return pid

########NEW FILE########
__FILENAME__ = vm
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

import andbug, andbug.data, andbug.proto, andbug.errors
import threading, re
from andbug.data import defer
from threading import Lock
from Queue import Queue

## Implementation Questions:
## -- unpackFrom methods are used to unpack references to an element from
##    a JDWP buffer.  This does not mean unpacking the actual definition of
##    the element, which tends to be one-shot.
##
## References:
## -- All codes that are sent to Dalvik VM where extracted from
##    dalvik/vm/jdwp/JdwpHandler.cpp and converted to HEX values
##    (e.g. Resume Thread: {11, 3, ....} => 0b03)
## -- JDWP Protocol:
##    dalvik implements a subset of these, verify with JdwpHandler.cpp:
##    http://docs.oracle.com/javase/6/docs/platform/jpda/jdwp/jdwp-protocol.html
##    

class RequestError(Exception):
    'raised when a request for more information from the process fails'
    def __init__(self, code):
        Exception.__init__(self, 'request failed, code %s' % code)
        self.code = code

class Element(object):
    def __repr__(self):
        return '<%s>' % self

    def __str__(self):
        return '%s:%s' % (type(self).__name__, id(self))

class SessionElement(Element):
    def __init__(self, sess):
        self.sess = sess

    @property
    def conn(self):
        return self.sess.conn

class Field(SessionElement):
    def __init__(self, session, fid):
        SessionElement.__init__(self, session)
        self.fid = fid
    
    @classmethod 
    def unpackFrom(impl, sess, buf):
        return sess.pool(impl, sess, buf.unpackFieldId())
    
    @property
    def public(self):
        return self.flags & 0x0001
    
    @property
    def private(self):
        return self.flags & 0x0002
    
    @property
    def protected(self):
        return self.flags & 0x0004
    
    @property
    def static(self):
        return self.flags & 0x0008
    
    @property
    def final(self):
        return self.flags & 0x0010

    @property
    def volatile(self):
        return self.flags & 0x0040
    
    @property
    def transient(self):
        return self.flags & 0x0080
    
class Value(SessionElement):
    @property
    def isPrimitive(self):
        return self.TAG in PRIMITIVE_TAGS

    @property
    def isObject(self):
        return self.TAG in OBJECT_TAGS

class Frame(SessionElement):
    def __init__(self, sess, fid):
        SessionElement.__init__(self, sess)
        self.fid = fid
        self.loc = None
        self.tid = None

    def __str__(self):
        return 'frame %s, at %s' % (self.fid, self.loc)   

    @classmethod 
    def unpackFrom(impl, sess, buf):
        return sess.pool(impl, sess, buf.unpackFrameId())
    
    def packTo(self, buf):
        buf.packFrameId(self.fid)

    @property
    def native(self):
        return self.loc.native

    @property
    def values(self):
        vals = {}
        if self.native: return vals
        
        sess = self.sess
        conn = self.conn
        buf = conn.buffer()
        buf.packObjectId(self.tid)
        buf.packFrameId(self.fid)
        slots = self.loc.slots
        buf.packInt(len(slots))

        for slot in slots:
            buf.packInt(slot.index)
            buf.packU8(slot.tag) #TODO: GENERICS

        code, buf = conn.request(0x1001, buf.data())
        if code != 0:
            raise RequestError(code)
        ct = buf.unpackInt()

        for x in range(0, ct):
            s = slots[x]
            vals[s.name] = unpack_value(sess, buf)

        return vals

    def value(self, name):
        if self.native: return None

        sess = self.sess
        conn = self.conn
        buf = conn.buffer()
        buf.packObjectId(self.tid)
        buf.packFrameId(self.fid)
        slots = self.loc.slots
        buf.packInt(1)

        loc = None
        for i in range(0, len(slots)):
            if slots[i].name == name:
                loc = i
                break
            else:
                continue

        if loc is None:
            return None
        slot = slots[loc]
        buf.packInt(slot.index)
        buf.packU8(slot.tag) #TODO: GENERICS

        code, buf = conn.request(0x1001, buf.data())
        if code != 0:
            raise RequestError(code)
        if buf.unpackInt() != 1:
            return None

        return unpack_value(sess, buf)

    def setValue(self, name, value):
        if self.native: return False

        sess = self.sess
        conn = self.conn
        buf = conn.buffer()
        buf.packObjectId(self.tid)
        buf.packFrameId(self.fid)
        slots = self.loc.slots
        buf.packInt(1)

        loc = None
        for i in range(0, len(slots)):
            if slots[i].name == name:
                loc = i
                break
            else:
                continue

        if loc is None:
            return False
        slot = slots[loc]
        buf.packInt(slot.index)
        pack_value(sess, buf, value, slot.jni) #TODO: GENERICS

        code, buf = conn.request(0x1002, buf.data())
        if code != 0:
            raise RequestError(code)

        return True

class Thread(SessionElement):
    #TODO: promote to Value
    def __init__(self, sess, tid):
        SessionElement.__init__(self, sess)
        self.tid = tid
    
    def __str__(self):
        tStatus, sStatus = self.status
        return 'thread %s\t(%s %s)' % (self.name or hex(self.tid), Thread.threadStatusStr(tStatus), Thread.suspendStatusStr(sStatus))

    def suspend(self):  
        conn = self.conn
        buf = conn.buffer()
        buf.packObjectId(self.tid)
        code, buf = conn.request(0x0b02, buf.data())
        if code != 0:
            raise RequestError(code)

    def resume(self):
        conn = self.conn
        buf = conn.buffer()
        buf.packObjectId(self.tid)
        code, buf = conn.request(0x0b03, buf.data())
        if code != 0:
            raise RequestError(code)

    def packTo(self, buf):
        buf.packObjectId(self.tid)

    def hook(self, func = None, queue = None):
        conn = self.conn
        buf = conn.buffer()
        # 40:EK_METHOD_ENTRY, 1: SP_THREAD, 1 condition of type ClassRef (3), ThreadId
        buf.pack('11i1t', 40, 1, 1, 3, self.tid) 
        code, buf = conn.request(0x0f01, buf.data())
        if code != 0:
            raise RequestError(code)
        eid = buf.unpackInt()
        return self.sess.hook(eid, func, queue, self)

    @classmethod
    def unpackFrom(impl, sess, buf):
        tid = buf.unpackObjectId()
        return sess.pool(impl, sess, tid)

    @property
    def frames(self):
        tid = self.tid
        sess = self.sess
        conn = self.conn
        buf = conn.buffer()
        buf.pack('oii', self.tid, 0, -1)
        code, buf = conn.request(0x0b06, buf.data())
        if code != 0:
            raise RequestError(code)
        ct = buf.unpackInt()

        def load_frame():
            f = Frame.unpackFrom(sess, buf)
            f.loc = Location.unpackFrom(sess, buf)
            f.tid = tid
            return f

        return andbug.data.view(load_frame() for i in range(0,ct))

    @property
    def frameCount(self):   
        conn = self.conn
        buf = conn.buffer()
        buf.packObjectId(self.tid)
        code, buf = conn.request(0x0b07, buf.data())
        if code != 0:
            raise RequestError(code)
        return buf.unpackInt()

    @property
    def name(self): 
        conn = self.conn
        buf = conn.buffer()
        buf.packObjectId(self.tid)
        code, buf = conn.request(0x0b01, buf.data())
        if code != 0:
            raise RequestError(code)
        return buf.unpackStr()

    @property
    def status(self):
        conn = self.conn
        buf = conn.buffer()
        buf.packObjectId(self.tid)
        code, buf = conn.request(0x0b04, buf.data())
        if code != 0:
            raise RequestError(code)

        threadStatus = buf.unpackInt()
        suspendStatus = buf.unpackInt()

        return threadStatus, suspendStatus

    @staticmethod
    def threadStatusStr(tStatus):
        szTS = ('zombie', 'running', 'sleeping', 'monitor', 'waiting', 'initializing', 'starting', 'native', 'vmwait')
        tStatus = int(tStatus)
        if tStatus < 0 or tStatus >= len(szTS):
            return "UNKNOWN"
        return szTS[tStatus]

    @staticmethod
    def suspendStatusStr(sStatus):
        szSS = ('running', 'suspended')
        sStatus = int(sStatus)
        if sStatus < 0 or sStatus >= len(szSS):
            return "UNKNOWN"
        return szSS[sStatus]

class Location(SessionElement):
    def __init__(self, sess, tid, mid, loc):
        SessionElement.__init__(self, sess)
        self.tid = tid
        self.mid = mid
        self.loc = loc
        self.line = None

    def __str__(self):
        if self.loc >= 0:
            return '%s:%i' % (self.method, self.loc)
        else:
            return str(self.method)

    def packTo(self, buf):
        c = self.klass
        buf.ipack('1tm8', c.tag, self.tid, self.mid, self.loc)

    @classmethod
    def unpackFrom(impl, sess, buf):
        tag, tid, mid, loc = buf.unpack('1tm8')
        return sess.pool(impl, sess, tid, mid, loc)

    def hook(self, func = None, queue = None):
        conn = self.conn
        buf = conn.buffer()
        # 2: BREAKPOINT
        # 40:METHOD_ENTRY
        # 41:METHOD_EXIT
        if self == self.method.firstLoc:
            eventKind = 40
        elif self == self.method.lastLoc:
            eventKind = 41
        else:
            eventKind = 2
        # 1: SP_THREAD, 1 condition of type Location (7)
        buf.pack('11i1', eventKind, 1, 1, 7)

        self.packTo(buf)
        code, buf = conn.request(0x0f01, buf.data())
        if code != 0:
            raise RequestError(code)
        eid = buf.unpackInt()
        return self.sess.hook(eid, func, queue, self)

    @property
    def native(self):
        return self.loc == -1

    @property
    def method(self):
        return self.sess.pool(Method, self.sess, self.tid, self.mid)

    @property
    def klass(self):
        return self.sess.pool(Class, self.sess, self.tid)

    @property
    def slots(self):
        l = self.loc
        def filter_slots():
            for slot in self.method.slots:
                f = slot.firstLoc
                if f > l: continue
                if l - f > slot.locLength: continue
                yield slot
        return tuple() if self.native else tuple(filter_slots())

class Slot(SessionElement):
    def __init__(self, sess, tid, mid, index):
        SessionElement.__init__(self, sess)
        self.tid = tid
        self.mid = mid
        self.index = index
        self.name = None

    def __str__(self):
        if self.name:
            return 'slot %s at index %i' % (self.name, self.index)
        else:
            return 'slot at index %i' % (self.index)

    def load_slot(self):
        self.sess.pool(Class, self.sess, self.tid).load_slots()

    firstLoc = defer(load_slot, 'firstLoc')
    locLength = defer(load_slot, 'locLength')
    name = defer(load_slot, 'name')
    jni = defer(load_slot, 'jni')
    gen = defer(load_slot, 'gen')

    @property
    def tag(self):
        return ord(self.jni[0])

class Method(SessionElement):
    def __init__(self, sess, tid, mid):
        SessionElement.__init__(self, sess)
        self.tid = tid
        self.mid = mid

    @property
    def klass(self):
        return self.sess.pool(Class, self.sess, self.tid)

    def __str__(self):
        return '%s.%s%s' % (
            self.klass, self.name, self.jni 
    )       
     
    def __repr__(self):
        return '<method %s>' % self

    def load_line_table(self):
        sess = self.sess
        conn = sess.conn
        pool = sess.pool
        tid = self.tid
        mid = self.mid
        data = conn.buffer().pack('om', tid, mid)
        code, buf = conn.request(0x0601, data)
        if code != 0: raise RequestError(code)
        
        f, l, ct = buf.unpack('88i')
        if (f == -1) or (l == -1):             
            self.firstLoc = None
            self.lastLoc = None
            self.lineTable = andbug.data.view([])
            #TODO: How do we handle native methods?
 
        self.firstLoc = pool(Location, sess, tid, mid, f)
        self.lastLoc = pool(Location, sess, tid, mid, l)

        ll = {}
        self.lineTable = ll
        def line_loc():
            loc, line  = buf.unpack('8i')
            loc = pool(Location, sess, tid, mid, loc)
            loc.line = line
            ll[line] = loc

        for i in range(0,ct):
            line_loc()
    
    firstLoc = defer(load_line_table, 'firstLoc')
    lastLoc = defer(load_line_table, 'lastLoc')
    lineTable = defer(load_line_table, 'lineTable')

    def load_method(self):
        self.klass.load_methods()

    name = defer(load_method, 'name')
    jni = defer(load_method, 'jni')
    gen = defer(load_method, 'gen')
    flags = defer(load_method, 'flags' )

    def load_slot_table(self):
        sess = self.sess
        conn = self.conn
        pool = sess.pool
        tid = self.tid
        mid = self.mid
        data = conn.buffer().pack('om', tid, mid)
        code, buf = conn.request(0x0605, data)
        if code != 0: raise RequestError(code)
    
        act, sct = buf.unpack('ii')
        #TODO: Do we care about the argCnt ?
         
        def load_slot():
            codeIndex, name, jni, gen, codeLen, index  = buf.unpack('l$$$ii')
            slot = pool(Slot, sess, tid, mid, index)
            slot.firstLoc = codeIndex
            slot.locLength = codeLen
            slot.name = name
            slot.jni = jni
            slot.gen = gen

            return slot

        self.slots = andbug.data.view(load_slot() for i in range(0,sct))

    slots = defer(load_slot_table, 'slots')

class RefType(SessionElement):
    def __init__(self, sess, tag, tid):
        SessionElement.__init__(self, sess)
        self.tag = tag
        self.tid = tid
    
    def __repr__(self):
        return '<type %s %s#%x>' % (self.jni, chr(self.tag), self.tid)

    def __str__(self):
        return repr(self)

    @classmethod 
    def unpackFrom(impl, sess, buf):
        return sess.pool(impl, sess, buf.unpackU8(), buf.unpackTypeId())

    def packTo(self, buf):
        buf.packObjectId(self.tid)

    def load_signature(self):
        conn = self.conn
        buf = conn.buffer()
        self.packTo(buf)
        code, buf = conn.request(0x020d, buf.data())
        if code != 0:
            raise RequestError(code)
        self.jni = buf.unpackStr()
        self.gen = buf.unpackStr()

    gen = defer(load_signature, 'gen')
    jni = defer(load_signature, 'jni')

    def load_fields(self):
        sess = self.sess
        conn = self.conn
        buf = conn.buffer()
        buf.pack("t", self.tid)
        code, buf = conn.request(0x020e, buf.data())
        if code != 0:
            raise RequestError(code)

        ct = buf.unpackU32()

        def load_field():
            field = Field.unpackFrom(sess, buf)
            name, jni, gen, flags = buf.unpack('$$$i')
            field.name = name
            field.jni = jni
            field.gen = gen
            field.flags = flags
            return field
        
        self.fieldList = andbug.data.view(
            load_field() for i in range(ct)
        )        

    fieldList = defer(load_fields, 'fieldList')

    @property
    def statics(self):
        sess = self.sess
        conn = self.conn
        buf = conn.buffer()
        buf.packTypeId(self.tid)
        fields = list(f for f in self.fieldList if f.static)
        buf.packInt(len(fields))
        for field in fields:
            buf.packFieldId(field.fid)
        code, buf = conn.request(0x0206, buf.data())
        if code != 0:
            raise RequestError(code)
        ct = buf.unpackInt()

        vals = {}
        for x in range(ct):
            f = fields[x]
            vals[f.name] = unpack_value(sess, buf)
        return vals

    def load_methods(self):
        tid = self.tid
        sess = self.sess
        conn = self.conn
        pool = sess.pool
        buf = conn.buffer()
        buf.pack("t", tid)
        code, buf = conn.request(0x020f, buf.data())
        if code != 0:
            raise RequestError(code)

        ct = buf.unpackU32()
                
        def load_method():
            mid, name, jni, gen, flags = buf.unpack('m$$$i')
            obj = pool(Method, sess, tid, mid)
            obj.name = name
            obj.jni = jni
            obj.gen = gen
            obj.flags = flags
            return obj
    
        self.methodList = andbug.data.view(
            load_method() for i in range(0, ct)
        )
        self.methodByJni = andbug.data.multidict()
        self.methodByName = andbug.data.multidict()

        for item in self.methodList:
            jni = item.jni
            name = item.name
            self.methodByJni[jni] = item
            self.methodByName[name] = item
    
    methodList = defer(load_methods, 'methodList')
    methodByJni = defer(load_methods, 'methodByJni')
    methodByName = defer(load_methods, 'methodByName')

    methodList = defer(load_methods, 'methodList')
    methodByJni = defer(load_methods, 'methodByJni')
    methodByName = defer(load_methods, 'methodByName')

    def methods(self, name=None, jni=None):
        if name and jni:
            seq = self.methodByName[name]
            seq = filter(x in seq, self.methodByJni[jni])
        elif name:
            seq = andbug.data.view(self.methodByName[name])
        elif jni:
            seq = self.methodByJni[jni]
        else:
            seq = self.methodList
        return andbug.data.view(seq)
    
    @property
    def name(self):
        name = self.jni
        if name.startswith('L'): name = name[1:]
        if name.endswith(';'): name = name[:-1]
        name = name.replace('/', '.')
        return name

class Class(RefType): 
    def __init__(self, sess, tid):
        RefType.__init__(self, sess, 'L', tid)
        
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return '<class %s>' % self

    def hookEntries(self, func = None, queue = None):
        conn = self.conn
        buf = conn.buffer()
        # 40:EK_METHOD_ENTRY, 1: SP_THREAD, 1 condition of type ClassRef (4)
        buf.pack('11i1t', 40, 1, 1, 4, self.tid) 
        code, buf = conn.request(0x0f01, buf.data())
        if code != 0:
            raise RequestError(code)
        eid = buf.unpackInt()
        return self.sess.hook(eid, func, queue, self)
        
    #def load_class(self):
    #   self.sess.load_classes()
    #   assert self.tag != None
    #   assert self.flags != None

    #tag = defer(load_class, 'tag')
    #jni = defer(load_class, 'jni')
    #gen = defer(load_class, 'gen')
    #flags = defer(load_class, 'flags')

class Hook(SessionElement):
    def __init__(self, sess, ident, func = None, queue = None, origin = None):
        SessionElement.__init__(self, sess)
        if queue is not None:
            self.queue = queue
        elif func is None:
            self.queue = queue or Queue()
        self.func = func        

        self.ident = ident
        self.origin = origin
        #TODO: unclean
        with self.sess.ectl:
            self.sess.emap[ident] = self

    def __str__(self):
        return ('<%s> %s %s' %
            (str(self.ident), str(self.origin), str(type(self.origin))))

    def put(self, data):
        if self.func is not None:
            return self.func(data)
        else:
            return self.queue.put(data)
            
    def get(self, block = False, timeout = None):
        return self.queue.get(block, timeout)

    def clear(self):
        #TODO: unclean
        conn = self.conn
        buf = conn.buffer()
        # 40:EK_METHOD_ENTRY
        buf.pack('1i', 40, int(self.ident))
        # 0x0f02 = {15, 2} EventRequest.Clear
        code, unknown = conn.request(0x0f02, buf.data())
        # fixme: check what a hell is the value stored in unknown
        if code != 0:
            raise RequestError(code)

        with self.sess.ectl:
            del self.sess.emap[self.ident]

unpack_impl = [None,] * 256

def register_unpack_impl(ek, fn):
    unpack_impl[ek] = fn

def unpack_events(sess, buf):
    sp, ct = buf.unpack('1i')
    for i in range(0, ct):
        ek = buf.unpackU8()
        im = unpack_impl[ek]
        if im is None:
            raise RequestError(ek)
        else:
            yield im(sess, buf)

def unpack_event_location(sess, buf):
    rid = buf.unpackInt()
    t = Thread.unpackFrom(sess, buf)
    loc = Location.unpackFrom(sess, buf)
    return rid, t, loc

# Breakpoint
register_unpack_impl(2, unpack_event_location)
# MothodEntry
register_unpack_impl(40, unpack_event_location)
# MothodExit
register_unpack_impl(41, unpack_event_location)

class Session(object):
    def __init__(self, conn):
        self.pool = andbug.data.pool()
        self.conn = conn
        self.emap = {}
        self.ectl = Lock()
        self.evtq = Queue()
        conn.hook(0x4064, self.evtq)
        self.ethd = threading.Thread(
            name='Session', target=self.run
        )
        self.ethd.daemon=1
        self.ethd.start()

    def run(self):
        while True:
            self.processEvent(*self.evtq.get())

    def hook(self, ident, func = None, queue = None, origin = None):
        return Hook(self, ident, func, queue, origin)

    def processEvent(self, ident, buf):
        pol, ct = buf.unpack('1i')

        for i in range(0,ct):
            ek = buf.unpackU8()
            im = unpack_impl[ek]
            if im is None:
                raise RequestError(ek)
            evt = im(self, buf)
            with self.ectl:
                hook = self.emap.get(evt[0])
            if hook is not None:
                hook.put(evt[1:])
                          
    def load_classes(self):
        code, buf = self.conn.request(0x0114)
        if code != 0:
            raise RequestError(code)

        def load_class():
            tag, tid, jni, gen, flags = buf.unpack('1t$$i')
            obj = self.pool(Class, self, tid)
            obj.tag = tag
            obj.tid = tid
            obj.jni = jni
            obj.gen = gen
            obj.flags = flags
            return obj 
                        
        ct = buf.unpackU32()

        self.classList = andbug.data.view(load_class() for i in range(0, ct))
        self.classByJni = andbug.data.multidict()
        for item in self.classList:
            self.classByJni[item.jni] = item

    classList = defer(load_classes, 'classList')
    classByJni = defer(load_classes, 'classByJni')

    def classes(self, jni=None):
        if jni:
            seq = self.classByJni[jni]
        else:
            seq = self.classList
        return andbug.data.view(seq)
    
    def suspend(self):
        code, buf = self.conn.request(0x0108, '')
        if code != 0:
            raise RequestError(code)

    @property
    def count(self):
        code, buf = self.conn.request(0x0108, '')
        if code != 0:
            raise RequestError(code)

    def resume(self):
        code, buf = self.conn.request(0x0109, '')
        if code != 0:
            raise RequestError(code)

    def exit(self, code = 0):
        conn = self.conn
        buf = conn.buffer()
        buf.pack('i', code)
        code, buf = conn.request(0x010A, '')
        if code != 0:
            raise RequestError(code)

    def threads(self, name=None):
        pool = self.pool
        code, buf = self.conn.request(0x0104, '')
        if code != 0:
            raise RequestError(code)
        ct = buf.unpackInt()

        def load_thread():
            tid = buf.unpackObjectId()
            return pool(Thread, self, tid)

        seq = (load_thread() for x in range(0,ct))
        if name is not None:
            if rx_dalvik_tname.match(name):
                seq = (t for t in seq if t.name == name)
            else:
                name = str(name)
                name = name if not re.match('^\d+$', name) else '<' + name + '>'
                seq = (t for t in seq if name in t.name.split(' ',1))
        return andbug.data.view(seq)

rx_dalvik_tname = re.compile('^<[0-9]+> .*$')

class Object(Value):
    def __init__(self, sess, oid):
        if oid == 0: raise andbug.errors.VoidError()
        SessionElement.__init__(self, sess)
        self.oid = oid

    def __repr__(self):
        return '<obj %s #%x>' % (self.jni, self.oid)
    
#    def __str__(self):
#        return str(self.fields.values())
    def __str__(self):
        return str("%s <%s>" % (str(self.jni), str(self.oid)))
        
    @classmethod
    def unpackFrom(impl, sess, buf):
        oid = buf.unpackObjectId()
        # oid = 0 indicates a GC omgfuckup in Dalvik
        # which is NOT as uncommon as we would like..
        if not oid: return None 
        return sess.pool(impl, sess, oid)

    def packTo(self, buf):
        buf.packObjectId(self.oid)

    @property
    def gen(self):
        return self.refType.gen
    
    @property
    def jni(self):
        return self.refType.jni

    def load_refType(self):
        conn = self.sess.conn
        buf = conn.buffer()
        self.packTo(buf)
        code, buf = conn.request(0x0901, buf.data())
        if code != 0:
            raise RequestError(code)
        self.refType = RefType.unpackFrom(self.sess, buf)
    
    refType = defer(load_refType, 'refType')

    @property
    def fieldList(self):
        r = list(f for f in self.refType.fieldList if not f.static)
        return r

    @property
    def typeTag(self):
        return self.refType.tag

    @property
    def fields(self):
        sess = self.sess
        conn = self.conn
        buf = conn.buffer()
        buf.packTypeId(self.oid)
        fields = self.fieldList
        buf.packInt(len(fields))
        for field in fields:
            buf.packFieldId(field.fid)
        code, buf = conn.request(0x0902, buf.data())
        if code != 0:
            raise RequestError(code)
        ct = buf.unpackInt()
        vals = {}
        for x in range(ct):
            f = fields[x]
            vals[f.name] = unpack_value(sess, buf)

        return vals

    def field(self, name):
        sess = self.sess
        conn = self.conn
        buf = conn.buffer()
        buf.packTypeId(self.oid)
        fields = self.fieldList
        buf.packInt(1)

        loc = None
        for i in range(0, len(fields)):
            if fields[i].name == name:
                loc = i
                break
            else:
                continue

        if loc is None:
            return None
        field = fields[loc]
        buf.packFieldId(field.fid)
        code, buf = conn.request(0x0902, buf.data())
        if code != 0:
            raise RequestError(code)
        if buf.unpackInt() != 1:
            return None
        return unpack_value(sess, buf)


    def setField(self, name, value):
        sess = self.sess
        conn = self.conn
        buf = conn.buffer()
        buf.packTypeId(self.oid)
        fields = self.fieldList
        buf.packInt(1)

        loc = None
        for i in range(0, len(fields)):
            if fields[i].name == name:
                loc = i
                break
            else:
                continue

        if loc is None:
            return None
        field = fields[loc]
        buf.packFieldId(field.fid)
        #TODO: WTF: ord(field.jni) !?
        pack_value(sess, buf, value, field.jni[0])
        code, buf = conn.request(0x0903, buf.data())
        if code != 0:
            raise RequestError(code)
        return True

## with andbug.screed.item(str(obj)):
##     if hasattr(obj, 'dump'):
##        obj.dump()

class Array(Object):
    def __repr__(self):
        data = self.getSlice()

        # Java very commonly uses character and byte arrays to express
        # text instead of strings, because they are mutable and have 
        # different encoding implications.

        if self.jni == '[C':
            return repr(''.join(data))
        elif self.jni == '[B':
            return repr(''.join(chr(c) for c in data))
        else:
            return repr(data)

    def __getitem__(self, index):
        if index < 0:
            self.getSlice(index-1, index)
        else:
            return self.getSlice(index, index+1)
    
    def __len__(self):
        return self.length
    
    def __iter__(self): return iter(self.getSlice())

    def __str__(self):
        return str(self.getSlice())
        
    @property
    def length(self):
        conn = self.conn
        buf = conn.buffer()
        self.packTo(buf)
        code, buf = conn.request(0x0d01, buf.data())        
        if code != 0:
            raise RequestError(code)
        return buf.unpackInt()

    def getSlice(self, first=0, last=-1):
        length = self.length
        if first > length:
            raise IndexError('first offset (%s) past length of array' % first)
        if last > length:
            raise IndexError('last offset (%s) past length of array' % last)
        if first < 0:
            first = length + first + 1
            if first < 0:
                raise IndexError('first absolute (%s) past length of array' % first)
        if last < 0:
            last = length + last + 1
            if last < 0:
                raise IndexError('last absolute (%s) past length of array' % last)
        if first > last:
            first, last = last, first
        
        count = last - first
        if not count: return []

        conn = self.conn
        buf = conn.buffer()
        self.packTo(buf)
        buf.packInt(first)
        buf.packInt(count)
        code, buf = conn.request(0x0d02, buf.data())
        if code != 0:
            raise RequestError(code)
        tag = buf.unpackU8()
        ct = buf.unpackInt()
        
        sess = self.sess
        if tag in OBJECT_TAGS:
            return tuple(unpack_value(sess, buf) for i in range(ct))
        else:
            return tuple(unpack_value(sess, buf, tag) for i in range(ct))

PRIMITIVE_TAGS = set(ord(c) for c in 'BCFDIJSVZ')
OBJECT_TAGS = set(ord(c) for c in 'stglcL')

class String(Object):
    def __repr__(self):
        return '#' + repr(str(self))

    def __str__(self):
        return self.data

    @property
    def data(self):
        conn = self.conn
        buf = conn.buffer()
        self.packTo(buf)
        code, buf = conn.request(0x0A01, buf.data())
        if code != 0:
            raise RequestError(code)
        return buf.unpackStr()

unpack_value_impl = [None,] * 256
def register_unpack_value(tag, func):
    for t in tag:
        unpack_value_impl[ord(t)] = func

register_unpack_value('B', lambda p, b: b.unpackU8())
register_unpack_value('C', lambda p, b: chr(b.unpackU8()))
register_unpack_value('F', lambda p, b: b.unpackFloat()) #TODO: TEST
register_unpack_value('D', lambda p, b: b.unpackDouble()) #TODO:TEST
register_unpack_value('I', lambda p, b: b.unpackInt())
register_unpack_value('J', lambda p, b: b.unpackLong())
register_unpack_value('S', lambda p, b: b.unpackShort()) #TODO: TEST
register_unpack_value('V', lambda p, b: b.unpackVoid())
register_unpack_value('Z', lambda p, b: (True if b.unpackU8() else False))
register_unpack_value('L', Object.unpackFrom)
register_unpack_value('tglc', Object.unpackFrom) #TODO: IMPL
register_unpack_value('s', String.unpackFrom)
register_unpack_value('[', Array.unpackFrom)

def unpack_value(sess, buf, tag = None):
    if tag is None: tag = buf.unpackU8()
    fn = unpack_value_impl[tag]
    if fn is None:
        raise RequestError(tag)
    else:
        return fn(sess, buf)

pack_value_impl = [None,] * 256
def register_pack_value(tag, func):
    for t in tag:
        pack_value_impl[ord(t)] = func

register_pack_value('B', lambda p, b, v: b.packU8(int(v)))
register_pack_value('F', lambda p, b, v: b.packFloat(float(v))) #TODO: TEST
register_pack_value('D', lambda p, b, v: b.packDouble(float(v))) #TODO:TEST
register_pack_value('I', lambda p, b, v: b.packInt(int(v)))
register_pack_value('J', lambda p, b, v: b.packLong(long(v)))
register_pack_value('S', lambda p, b, v: b.packShort(int(v))) #TODO: TEST
register_pack_value('V', lambda p, b, v: b.packVoid())
register_pack_value('Z', lambda p, b, v: b.packU8(bool(v) and 1 or 0))
#register_pack_value('s', lambda p, b, v: b.packStr(v)) # TODO: pack String

def pack_value(sess, buf, value, tag = None):
    if not tag:
        raise RequestError(tag)
    if isinstance(tag, basestring):
        tag = ord(tag[0])
    print "PACK", repr(tag), repr(value)
    fn = pack_value_impl[tag]
    if fn is None:
        raise RequestError(tag)
    else:
        buf.packU8(tag)
        return fn(sess, buf, value)

def connect(pid, dev=None):
    'connects using proto.forward() to the process associated with this context'
    conn = andbug.proto.connect(andbug.proto.forward(pid, dev))
    return andbug.vm.Session(conn)


########NEW FILE########
__FILENAME__ = jdwp
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

import andbug.jdwp
from unittest import TestCase, main as test_main

def newbuf():
	buf = andbug.jdwp.JdwpBuffer()
	buf.config(1,2,2,4,8) # f, m, o, t, s
	return buf

class TestJdwp(TestCase):
	def test_pack(self):
		def pack(fmt, pkt, *data):
			print ":: %r of %r -> %r" % (fmt, data, pkt)
			data = list(data)
			buf = newbuf()
			res = buf.pack(fmt, *data)
			self.assertEqual(res, pkt)
			
			buf = newbuf()
			res = buf.unpack(fmt, pkt)
			self.assertEqual(res, data)

		pack("", "")
		pack("1", "\0", 0)
		pack("2", "\0\1", 1)
		pack("4", "\0\0\0\1", 1)
		pack("8", "\0\0\0\0\0\0\0\1", 1)
		pack("f", "\1", 1)
		pack("m", "\0\1", 1)
		pack("o", "\0\1", 1)
		pack("t", "\0\0\0\1", 1)
		pack("s", "\0\0\0\0\0\0\0\1", 1)
		pack("$", "\0\0\0\4abcd", "abcd")
		
		pack("1248", (
			"\0"
			"\0\1"
			"\0\0\0\1"
			"\0\0\0\0\0\0\0\1"
		), 0, 1, 1, 1)

		pack("fmots", (
			"\0"
			"\0\1"
			"\0\1"
			"\0\0\0\1"
			"\0\0\0\0\0\0\0\1"
		), 0, 1, 1, 1, 1)

	def test_incr_pack(self):
		buf = newbuf()
		buf.packU8(1)
		buf.packU16(1)
		buf.packU32(1)
		buf.packU64(1)
		self.assertEqual(buf.data(), "\1\0\1\0\0\0\1\0\0\0\0\0\0\0\1")		

if __name__ == '__main__':
	test_main()
########NEW FILE########
__FILENAME__ = log
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

from andbug.log import LogReader, LogWriter, LogEvent
from unittest import TestCase, main as test_main
from cStringIO import StringIO
import sys

class TestLog(TestCase):
	def test_log(self):
		def log(time, tag, meta, data):
			o = StringIO()
			w = LogWriter(o)
			evt = LogEvent(time, tag, meta, data)
			sys.stdout.write(str(evt))
			w.writeEvent(evt)
			i = StringIO(o.getvalue())
			r = LogReader(i)
			evt = r.readEvent()
			self.assertEqual(evt.tag, tag)
			self.assertEqual(evt.meta, meta)
			self.assertEqual(evt.time, time)
			self.assertEqual(evt.data, data)
		
		log( 1, "<<<", "META", "" )
		log( 2, ">>>", "META", "the quick brown fox" )

if __name__ == '__main__':
	test_main()
########NEW FILE########
__FILENAME__ = options
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

from andbug.options import parse_cpath, parse_mquery
from unittest import TestCase, main as test_main

class TestOptions(TestCase):
    def test_cpath(self):
        def case(opt, res):
            self.assertEqual(parse_cpath(opt), res)
        
        case('a.b.c.d', 'La/b/c/d;')
        case('La/b/c/d;', 'La/b/c/d;')
        case('La;', 'La;')
        case('a', 'La;')
    
    def test_mquery(self):
        def case(c, m, (cp, mn, mj)):
            p, n, j = parse_mquery(c, m)
            self.assertEqual(cp, p)
            self.assertEqual(mn, n)
            self.assertEqual(mj, j)
 
        case('abc',       None,       ('Labc;', None, None))
        case('abc',       '',         ('Labc;', None, None))
        case('abc',       '*',        ('Labc;', None, None))
        case('abc',       'foo',      ('Labc;', 'foo', None))
        case('abc.xyz',   'foo()I',   ('Labc/xyz;', 'foo', '()I'))
        case('Labc/xyz;', 'foo(DD)I', ('Labc/xyz;', 'foo', '(DD)I'))
        
if __name__ == '__main__':
    test_main()
########NEW FILE########
__FILENAME__ = proto
## Copyright 2011, IOActive, Inc. All rights reserved.
##
## AndBug is free software: you can redistribute it and/or modify it under 
## the terms of version 3 of the GNU Lesser General Public License as 
## published by the Free Software Foundation.
##
## AndBug is distributed in the hope that it will be useful, but WITHOUT ANY
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
## FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for 
## more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with AndBug.  If not, see <http://www.gnu.org/licenses/>.

from andbug.proto import Connection, HANDSHAKE_MSG, IDSZ_REQ
from unittest import TestCase, main as test_main
from cStringIO import StringIO
import sys

IDSZ_RES = (
	'\x00\x00\x00\x1F' # Length
	'\x00\x00\x00\x01' # Identifier
	'\x80'             # Response
	'\x00\x00'         # Not an error

	'\x00\x00\x00\x01' # F-Sz
	'\x00\x00\x00\x02' # M-Sz
	'\x00\x00\x00\x02' # O-Sz
	'\x00\x00\x00\x04' # T-Sz
	'\x00\x00\x00\x08' # S-Sz
)

class IoHarness:
	def __init__(self, test, convo):
		self.test = test
		self.readbuf = StringIO(
			"".join(map(lambda x: x[1], convo))
		)
		self.writebuf = StringIO(
			"".join(map(lambda x: x[0], convo))
		)

	def read(self, length):
		return self.readbuf.read(length)

	def write(self, data):
		exp = self.writebuf.read(len(data))
		self.test.assertEqual(exp, data)

def make_conn(harness):
	conn = Connection(harness.read, harness.write)
	conn.start()
	return conn

SAMPLE_REQ = (
	'\x00\x00\x00\x0B' # Length
	'\x00\x00\x00\x03' # Identifier
	'\x00'             # Request
	'\x42\x42'         # Not an error
)

SAMPLE_RES = (
	'\x00\x00\x00\x0B' # Length
	'\x00\x00\x00\x03' # Identifier
	'\x80'             # Response
	'\x00\x00'         # Success
)

class TestConnection(TestCase):
	def test_start(self):
		h = IoHarness( self, [
			(HANDSHAKE_MSG, HANDSHAKE_MSG),
			(IDSZ_REQ, IDSZ_RES)
		])
		p = make_conn(h)
		self.assertEqual(True, p.initialized)

if __name__ == '__main__':
	test_main()

########NEW FILE########
