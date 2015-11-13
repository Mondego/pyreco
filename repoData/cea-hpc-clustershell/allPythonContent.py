__FILENAME__ = check_nodes
#!/usr/bin/python
# check_nodes.py: ClusterShell simple example script.
#
# This script runs a simple command on remote nodes and report node
# availability (basic health check) and also min/max boot dates.
# It shows an example of use of Task, NodeSet and EventHandler objects.
# Feel free to copy and modify it to fit your needs.
#
# Usage example: ./check_nodes.py -n node[1-99]

import optparse
from datetime import date, datetime
import time

from ClusterShell.Event import EventHandler
from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import task_self


class CheckNodesResult:
    """Our result class"""
    def __init__(self):
        """Initialize result class"""
        self.nodes_ok = NodeSet()
        self.nodes_ko = NodeSet()
        self.min_boot_date = None
        self.max_boot_date = None

    def show(self):
        """Display results"""
        if self.nodes_ok:
            print "%s: OK (boot date: min %s, max %s)" % \
                (self.nodes_ok, self.min_boot_date, self.max_boot_date)
        if self.nodes_ko:
            print "%s: FAILED" % self.nodes_ko

class CheckNodesHandler(EventHandler):
    """Our ClusterShell EventHandler"""
    def __init__(self, result):
        """Initialize our event handler with a ref to our result object."""
        EventHandler.__init__(self)
        self.result = result

    def ev_read(self, worker):
        """Read event from remote nodes"""
        node = worker.current_node
        # this is an example to demonstrate remote result parsing
        bootime = " ".join(worker.current_msg.strip().split()[2:])
        date_boot = None
        for fmt in ("%Y-%m-%d %H:%M",): # formats with year
            try:
                # datetime.strptime() is Python2.5+, use old method instead
                date_boot = datetime(*(time.strptime(bootime, fmt)[0:6]))
            except ValueError:
                pass
        for fmt in ("%b %d %H:%M",):    # formats without year
            try:
                date_boot = datetime(date.today().year, \
                    *(time.strptime(bootime, fmt)[1:6]))
            except ValueError:
                pass
        if date_boot:
            if not self.result.min_boot_date or \
                self.result.min_boot_date > date_boot:
                self.result.min_boot_date = date_boot
            if not self.result.max_boot_date or \
                self.result.max_boot_date < date_boot:
                self.result.max_boot_date = date_boot
            self.result.nodes_ok.add(node)
        else:
            self.result.nodes_ko.add(node)

    def ev_timeout(self, worker):
        """Timeout occurred on some nodes"""
        self.result.nodes_ko.add(NodeSet.fromlist(worker.iter_keys_timeout()))

    def ev_close(self, worker):
        """Worker has finished (command done on all nodes)"""
        self.result.show()


def main():
    """ Main script function """
    # Initialize option parser
    parser = optparse.OptionParser()
    parser.add_option("-d", "--debug", action="store_true", dest="debug",
        default=False, help="Enable debug mode")
    parser.add_option("-n", "--nodes", action="store", dest="nodes",
        default="@all", help="Target nodes (default @all group)")
    parser.add_option("-f", "--fanout", action="store", dest="fanout",
        default="128", help="Fanout window size (default 128)", type=int)
    parser.add_option("-t", "--timeout", action="store", dest="timeout",
        default="5", help="Timeout in seconds (default 5)", type=float)
    options, _ = parser.parse_args()

    # Get current task (associated to main thread)
    task = task_self()
    nodes_target = NodeSet(options.nodes)
    task.set_info("fanout", options.fanout)
    if options.debug:
        print "nodeset : %s" % nodes_target
        task.set_info("debug", True)

    # Create ClusterShell event handler
    handler = CheckNodesHandler(CheckNodesResult())

    # Schedule remote command and run task (blocking call)
    task.run("who -b", nodes=nodes_target, handler=handler, \
        timeout=options.timeout)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = Clubak
#!/usr/bin/env python
#
# Copyright CEA/DAM/DIF (2010, 2011, 2012)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
format dsh/pdsh-like output for humans and more

For help, type::
    $ clubak --help
"""

from itertools import imap
import sys

from ClusterShell.MsgTree import MsgTree, MODE_DEFER, MODE_TRACE
from ClusterShell.NodeSet import NodeSetParseError, std_group_resolver

from ClusterShell.CLI.Display import Display, THREE_CHOICES
from ClusterShell.CLI.Error import GENERIC_ERRORS, handle_generic_error
from ClusterShell.CLI.OptionParser import OptionParser
from ClusterShell.CLI.Utils import NodeSet, nodeset_cmp


def display_tree(tree, disp, out):
    """display sub-routine for clubak -T (msgtree trace mode)"""
    togh = True
    offset = 2
    reldepth = -offset
    reldepths = {}
    line_mode = disp.line_mode
    for msgline, keys, depth, nchildren in tree.walk_trace():
        if togh:
            if depth in reldepths:
                reldepth = reldepths[depth]
            else:
                reldepth = reldepths[depth] = reldepth + offset
            if line_mode:
                out.write("%s:\n" % NodeSet.fromlist(keys))
            else:
                out.write("%s\n" % \
                    (disp.format_header(NodeSet.fromlist(keys), reldepth)))
        out.write("%s%s\n" % (" " * reldepth, msgline))
        togh = nchildren != 1

def display(tree, disp, gather, trace_mode, enable_nodeset_key):
    """nicely display MsgTree instance `tree' content according to
    `disp' Display object and `gather' boolean flag"""
    out = sys.stdout
    try:
        if trace_mode:
            display_tree(tree, disp, out)
        else:
            if gather:
                if enable_nodeset_key:
                    # lambda to create a NodeSet from keys returned by walk()
                    ns_getter = lambda x: NodeSet.fromlist(x[1])
                    for nodeset in sorted(imap(ns_getter, tree.walk()),
                                          cmp=nodeset_cmp):
                        disp.print_gather(nodeset, tree[nodeset[0]])
                else:
                    for msg, key in tree.walk():
                        disp.print_gather_keys(key, msg)
            else:
                if enable_nodeset_key:
                    # nodes are automagically sorted by NodeSet
                    for node in NodeSet.fromlist(tree.keys()).nsiter():
                        disp.print_gather(node, tree[str(node)])
                else:
                    for key in tree.keys():
                        disp.print_gather_keys([ key ], tree[key])
    finally:
        out.flush()

def clubak():
    """script subroutine"""

    # Argument management
    parser = OptionParser("%prog [options]")
    parser.install_display_options(verbose_options=True,
                                   separator_option=True,
                                   dshbak_compat=True,
                                   msgtree_mode=True)
    options = parser.parse_args()[0]

    if options.interpret_keys == THREE_CHOICES[-1]: # auto?
        enable_nodeset_key = None # AUTO
    else:
        enable_nodeset_key = (options.interpret_keys == THREE_CHOICES[1])

    # Create new message tree
    if options.trace_mode:
        tree_mode = MODE_TRACE
    else:
        tree_mode = MODE_DEFER
    tree = MsgTree(mode=tree_mode)
    fast_mode = options.fast_mode
    if fast_mode:
        if tree_mode != MODE_DEFER or options.line_mode:
            parser.error("incompatible tree options")
        preload_msgs = {}

    # Feed the tree from standard input lines
    for line in sys.stdin:
        try:
            linestripped = line.rstrip('\r\n')
            if options.verbose or options.debug:
                print "INPUT %s" % linestripped
            key, content = linestripped.split(options.separator, 1)
            key = key.strip()
            if not key:
                raise ValueError("no node found")
            if enable_nodeset_key is False: # interpret-keys=never?
                keyset = [ key ]
            else:
                try:
                    keyset = NodeSet(key)
                except NodeSetParseError:
                    if enable_nodeset_key: # interpret-keys=always?
                        raise
                    enable_nodeset_key = False # auto => switch off
                    keyset = [ key ]
            if fast_mode:
                for node in keyset:
                    preload_msgs.setdefault(node, []).append(content)
            else:
                for node in keyset:
                    tree.add(node, content)
        except ValueError, ex:
            raise ValueError("%s (\"%s\")" % (ex, linestripped))

    if fast_mode:
        # Messages per node have been aggregated, now add to tree one
        # full msg per node
        for key, wholemsg in preload_msgs.iteritems():
            tree.add(key, '\n'.join(wholemsg))

    # Display results
    try:
        disp = Display(options)
        if options.debug:
            std_group_resolver().set_verbosity(1)
            print >> sys.stderr, \
                "clubak: line_mode=%s gather=%s tree_depth=%d" % \
                    (bool(options.line_mode), bool(disp.gather), tree._depth())
        display(tree, disp, disp.gather or disp.regroup, \
                options.trace_mode, enable_nodeset_key is not False)
    except ValueError, exc:
        parser.error("option mismatch (%s)" % exc)

def main():
    """main script function"""
    try:
        clubak()
    except GENERIC_ERRORS, ex:
        sys.exit(handle_generic_error(ex))
    except ValueError, ex:
        print >> sys.stderr, "%s:" % sys.argv[0], ex
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = Clush
#!/usr/bin/env python
#
# Copyright CEA/DAM/DIF (2007, 2008, 2009, 2010, 2011, 2012)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
execute cluster commands in parallel

clush is an utility program to run commands on a cluster which benefits
from the ClusterShell library and its Ssh worker. It features an
integrated output results gathering system (dshbak-like), can get node
groups by running predefined external commands and can redirect lines
read on its standard input to the remote commands.

When no command are specified, clush runs interactively.

"""

import errno
import logging
import os
import resource
import sys
import signal
import threading

from ClusterShell.CLI.Config import ClushConfig, ClushConfigError
from ClusterShell.CLI.Display import Display
from ClusterShell.CLI.Display import VERB_QUIET, VERB_STD, VERB_VERB, VERB_DEBUG
from ClusterShell.CLI.OptionParser import OptionParser
from ClusterShell.CLI.Error import GENERIC_ERRORS, handle_generic_error
from ClusterShell.CLI.Utils import NodeSet, bufnodeset_cmp

from ClusterShell.Event import EventHandler
from ClusterShell.MsgTree import MsgTree
from ClusterShell.NodeSet import RESOLVER_NOGROUP, std_group_resolver
from ClusterShell.NodeSet import NodeSetParseError
from ClusterShell.Task import Task, task_self


class UpdatePromptException(Exception):
    """Exception used by the signal handler"""

class StdInputHandler(EventHandler):
    """Standard input event handler class."""
    def __init__(self, worker):
        EventHandler.__init__(self)
        self.master_worker = worker

    def ev_msg(self, port, msg):
        """invoked when a message is received from port object"""
        if not msg:
            self.master_worker.set_write_eof()
            return
        # Forward messages to master worker
        self.master_worker.write(msg)

class OutputHandler(EventHandler):
    """Base class for clush output handlers."""

    def __init__(self):
        EventHandler.__init__(self)
        self._runtimer = None

    def runtimer_init(self, task, ntotal):
        """Init timer for live command-completed progressmeter."""
        self._runtimer = task.timer(2.0, RunTimer(task, ntotal),
                                    interval=1./3., autoclose=True)

    def _runtimer_clean(self):
        """Hide runtimer counter"""
        if self._runtimer:
            self._runtimer.eh.erase_line()

    def _runtimer_set_dirty(self):
        """Force redisplay of counter"""
        if self._runtimer:
            self._runtimer.eh.set_dirty()

    def _runtimer_finalize(self, worker):
        """Finalize display of runtimer counter"""
        if self._runtimer:
            self._runtimer.eh.finalize(worker.task.default("USER_interactive"))
            self._runtimer.invalidate()
            self._runtimer = None

    def update_prompt(self, worker):
        """
        If needed, notify main thread to update its prompt by sending
        a SIGUSR1 signal. We use task-specific user-defined variable
        to record current states (prefixed by USER_).
        """
        worker.task.set_default("USER_running", False)
        if worker.task.default("USER_handle_SIGUSR1"):
            os.kill(os.getpid(), signal.SIGUSR1)

class DirectOutputHandler(OutputHandler):
    """Direct output event handler class."""

    def __init__(self, display):
        OutputHandler.__init__(self)
        self._display = display

    def ev_read(self, worker):
        node = worker.current_node or worker.key
        self._display.print_line(node, worker.current_msg)

    def ev_error(self, worker):
        node = worker.current_node or worker.key
        self._display.print_line_error(node, worker.current_errmsg)

    def ev_hup(self, worker):
        node = worker.current_node or worker.key
        rc = worker.current_rc
        if rc > 0:
            verb = VERB_QUIET
            if self._display.maxrc:
                verb = VERB_STD
            self._display.vprint_err(verb, \
                "clush: %s: exited with exit code %d" % (node, rc))

    def ev_timeout(self, worker):
        self._display.vprint_err(VERB_QUIET, "clush: %s: command timeout" % \
            NodeSet._fromlist1(worker.iter_keys_timeout()))

    def ev_close(self, worker):
        self.update_prompt(worker)

class CopyOutputHandler(DirectOutputHandler):
    """Copy output event handler."""
    def __init__(self, display, reverse=False):
        DirectOutputHandler.__init__(self, display)
        self.reverse = reverse

    def ev_close(self, worker):
        """A copy worker has finished."""
        for rc, nodes in worker.iter_retcodes():
            if rc == 0:
                if self.reverse:
                    self._display.vprint(VERB_VERB, "%s:`%s' -> `%s'" % \
                        (nodes, worker.source, worker.dest))
                else:
                    self._display.vprint(VERB_VERB, "`%s' -> %s:`%s'" % \
                        (worker.source, nodes, worker.dest))
                break
        # multiple copy workers may be running (handled by this task's thread)
        copies = worker.task.default("USER_copies") - 1
        worker.task.set_default("USER_copies", copies)
        if copies == 0:
            self._runtimer_finalize(worker)
            self.update_prompt(worker)

class GatherOutputHandler(OutputHandler):
    """Gathered output event handler class."""

    def __init__(self, display):
        OutputHandler.__init__(self)
        self._display = display

    def ev_read(self, worker):
        if self._display.verbosity == VERB_VERB:
            node = worker.current_node or worker.key
            self._display.print_line(node, worker.current_msg)

    def ev_error(self, worker):
        self._runtimer_clean()
        self._display.print_line_error(worker.current_node,
                                       worker.current_errmsg)
        self._runtimer_set_dirty()

    def ev_close(self, worker):
        # Worker is closing -- it's time to gather results...
        self._runtimer_finalize(worker)
        assert worker.current_node is not None, "cannot gather local command"
        # Display command output, try to order buffers by rc
        nodesetify = lambda v: (v[0], NodeSet._fromlist1(v[1]))
        cleaned = False
        for _rc, nodelist in sorted(worker.iter_retcodes()):
            # Then order by node/nodeset (see bufnodeset_cmp)
            for buf, nodeset in sorted(map(nodesetify,
                                           worker.iter_buffers(nodelist)),
                                       cmp=bufnodeset_cmp):
                if not cleaned:
                    # clean runtimer line before printing first result
                    self._runtimer_clean()
                    cleaned = True
                self._display.print_gather(nodeset, buf)
        self._display.flush()

        self._close_common(worker)

        # Notify main thread to update its prompt
        self.update_prompt(worker)

    def _close_common(self, worker):
        verbexit = VERB_QUIET
        if self._display.maxrc:
            verbexit = VERB_STD
        # Display return code if not ok ( != 0)
        for rc, nodelist in worker.iter_retcodes():
            if rc != 0:
                ns = NodeSet._fromlist1(nodelist)
                self._display.vprint_err(verbexit, \
                    "clush: %s: exited with exit code %d" % (ns, rc))

        # Display nodes that didn't answer within command timeout delay
        if worker.num_timeout() > 0:
            self._display.vprint_err(verbexit, "clush: %s: command timeout" % \
                NodeSet._fromlist1(worker.iter_keys_timeout()))

class LiveGatherOutputHandler(GatherOutputHandler):
    """Live line-gathered output event handler class."""

    def __init__(self, display, nodes):
        assert nodes is not None, "cannot gather local command"
        GatherOutputHandler.__init__(self, display)
        self._nodes = NodeSet(nodes)
        self._nodecnt = dict.fromkeys(self._nodes, 0)
        self._mtreeq = []
        self._offload = 0

    def ev_read(self, worker):
        # Read new line from node
        node = worker.current_node
        self._nodecnt[node] += 1
        cnt = self._nodecnt[node]
        if len(self._mtreeq) < cnt:
            self._mtreeq.append(MsgTree())
        self._mtreeq[cnt - self._offload - 1].add(node, worker.current_msg)
        self._live_line(worker)

    def ev_hup(self, worker):
        if self._mtreeq and worker.current_node not in self._mtreeq[0]:
            # forget a node that doesn't answer to continue live line
            # gathering anyway
            self._nodes.remove(worker.current_node)
            self._live_line(worker)

    def _live_line(self, worker):
        # if all nodes have replied, display gathered line
        while self._mtreeq and len(self._mtreeq[0]) == len(self._nodes):
            mtree = self._mtreeq.pop(0)
            self._offload += 1
            self._runtimer_clean()
            nodesetify = lambda v: (v[0], NodeSet.fromlist(v[1]))
            for buf, nodeset in sorted(map(nodesetify, mtree.walk()),
                                       cmp=bufnodeset_cmp):
                self._display.print_gather(nodeset, buf)
            self._runtimer_set_dirty()

    def ev_close(self, worker):
        # Worker is closing -- it's time to gather results...
        self._runtimer_finalize(worker)

        for mtree in self._mtreeq:
            nodesetify = lambda v: (v[0], NodeSet.fromlist(v[1]))
            for buf, nodeset in sorted(map(nodesetify, mtree.walk()),
                                       cmp=bufnodeset_cmp):
                self._display.print_gather(nodeset, buf)

        self._close_common(worker)

        # Notify main thread to update its prompt
        self.update_prompt(worker)

class RunTimer(EventHandler):
    """Running progress timer event handler"""
    def __init__(self, task, total):
        EventHandler.__init__(self)
        self.task = task
        self.total = total
        self.cnt_last = -1
        self.tslen = len(str(self.total))
        self.wholelen = 0
        self.started = False

    def ev_timer(self, timer):
        self.update()

    def set_dirty(self):
        self.cnt_last = -1

    def erase_line(self):
        if self.wholelen:
            sys.stderr.write(' ' * self.wholelen + '\r')

    def update(self):
        cnt = len(self.task._engine.clients())
        if cnt != self.cnt_last:
            self.cnt_last = cnt
            # display completed/total clients
            towrite = 'clush: %*d/%*d\r' % (self.tslen, self.total - cnt,
                self.tslen, self.total)
            self.wholelen = len(towrite)
            sys.stderr.write(towrite)
            self.started = True

    def finalize(self, force_cr):
        """finalize display of runtimer"""
        if not self.started:
            return
        # display completed/total clients
        fmt = 'clush: %*d/%*d'
        if force_cr:
            fmt += '\n'
        else:
            fmt += '\r'
        sys.stderr.write(fmt % (self.tslen, self.total, self.tslen, self.total))


def signal_handler(signum, frame):
    """Signal handler used for main thread notification"""
    if signum == signal.SIGUSR1:
        signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        raise UpdatePromptException()

def get_history_file():
    """Turn the history file path"""
    return os.path.join(os.environ["HOME"], ".clush_history")

def readline_setup():
    """
    Configure readline to automatically load and save a history file
    named .clush_history
    """
    import readline
    readline.parse_and_bind("tab: complete")
    readline.set_completer_delims("")
    try:
        readline.read_history_file(get_history_file())
    except IOError:
        pass

def ttyloop(task, nodeset, timeout, display):
    """Manage the interactive prompt to run command"""
    readline_avail = False
    if task.default("USER_interactive"):
        try:
            import readline
            readline_setup()
            readline_avail = True
        except ImportError:
            pass
        display.vprint(VERB_STD, \
            "Enter 'quit' to leave this interactive mode")

    rc = 0
    ns = NodeSet(nodeset)
    ns_info = True
    cmd = ""
    while task.default("USER_running") or cmd.lower() != 'quit':
        try:
            if task.default("USER_interactive") and \
                    not task.default("USER_running"):
                if ns_info:
                    display.vprint(VERB_QUIET, \
                                   "Working with nodes: %s" % ns)
                    ns_info = False
                prompt = "clush> "
            else:
                prompt = ""
            # Set SIGUSR1 handler if needed
            if task.default("USER_handle_SIGUSR1"):
                signal.signal(signal.SIGUSR1, signal_handler)
            try:
                cmd = raw_input(prompt)
                assert cmd is not None, "Result of raw_input() is None!"
            finally:
                signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        except EOFError:
            print
            return
        except UpdatePromptException:
            if task.default("USER_interactive"):
                continue
            return
        except KeyboardInterrupt, kbe:
            if display.gather:
                # Suspend task, so we can safely access its data from
                # the main thread
                task.suspend()

                print_warn = False

                # Display command output, but cannot order buffers by rc
                nodesetify = lambda v: (v[0], NodeSet._fromlist1(v[1]))
                for buf, nodeset in sorted(map(nodesetify, task.iter_buffers()),
                                            cmp=bufnodeset_cmp):
                    if not print_warn:
                        print_warn = True
                        display.vprint_err(VERB_STD, \
                            "Warning: Caught keyboard interrupt!")
                    display.print_gather(nodeset, buf)

                # Return code handling
                verbexit = VERB_QUIET
                if display.maxrc:
                    verbexit = VERB_STD
                ns_ok = NodeSet()
                for rc, nodelist in task.iter_retcodes():
                    ns_ok.add(NodeSet._fromlist1(nodelist))
                    if rc != 0:
                        # Display return code if not ok ( != 0)
                        ns = NodeSet._fromlist1(nodelist)
                        display.vprint_err(verbexit, \
                            "clush: %s: exited with exit code %s" % (ns, rc))
                # Add uncompleted nodeset to exception object
                kbe.uncompleted_nodes = ns - ns_ok

                # Display nodes that didn't answer within command timeout delay
                if task.num_timeout() > 0:
                    display.vprint_err(verbexit, \
                        "clush: %s: command timeout" % \
                            NodeSet._fromlist1(task.iter_keys_timeout()))
            raise kbe

        if task.default("USER_running"):
            ns_reg, ns_unreg = NodeSet(), NodeSet()
            for client in task._engine.clients():
                if client.registered:
                    ns_reg.add(client.key)
                else:
                    ns_unreg.add(client.key)
            if ns_unreg:
                pending = "\nclush: pending(%d): %s" % (len(ns_unreg), ns_unreg)
            else:
                pending = ""
            display.vprint_err(VERB_QUIET, "clush: interrupt (^C to " \
                "abort task)\nclush: in progress(%d): %s%s" % (len(ns_reg), \
                ns_reg, pending))
        else:
            cmdl = cmd.lower()
            try:
                ns_info = True
                if cmdl.startswith('+'):
                    ns.update(cmdl[1:])
                elif cmdl.startswith('-'):
                    ns.difference_update(cmdl[1:])
                elif cmdl.startswith('@'):
                    ns = NodeSet(cmdl[1:])
                elif cmdl == '=':
                    display.gather = not display.gather
                    if display.gather:
                        display.vprint(VERB_STD, \
                            "Switching to gathered output format")
                    else:
                        display.vprint(VERB_STD, \
                            "Switching to standard output format")
                    task.set_default("stdout_msgtree", \
                                     display.gather or display.line_mode)
                    ns_info = False
                    continue
                elif not cmdl.startswith('?'): # if ?, just print ns_info
                    ns_info = False
            except NodeSetParseError:
                display.vprint_err(VERB_QUIET, \
                    "clush: nodeset parse error (ignoring)")

            if ns_info:
                continue

            if cmdl.startswith('!') and len(cmd.strip()) > 0:
                run_command(task, cmd[1:], None, timeout, display)
            elif cmdl != "quit":
                if not cmd:
                    continue
                if readline_avail:
                    readline.write_history_file(get_history_file())
                run_command(task, cmd, ns, timeout, display)
    return rc

def _stdin_thread_start(stdin_port, display):
    """Standard input reader thread entry point."""
    try:
        # Note: read length should be larger and a multiple of 4096 for best
        # performance to avoid excessive unreg/register of writer fd in
        # engine; however, it shouldn't be too large.
        bufsize = 4096 * 8
        # thread loop: blocking read stdin + send messages to specified
        #              port object
        buf = sys.stdin.read(bufsize)
        while buf:
            # send message to specified port object (with ack)
            stdin_port.msg(buf)
            buf = sys.stdin.read(bufsize)
    except IOError, ex:
        display.vprint(VERB_VERB, "stdin: %s" % ex)
    # send a None message to indicate EOF
    stdin_port.msg(None)

def bind_stdin(worker, display):
    """Create a stdin->port->worker binding: connect specified worker
    to stdin with the help of a reader thread and a ClusterShell Port
    object."""
    assert not sys.stdin.isatty()
    # Create a ClusterShell Port object bound to worker's task. This object
    # is able to receive messages in a thread-safe manner and then will safely
    # trigger ev_msg() on a specified event handler.
    port = worker.task.port(handler=StdInputHandler(worker), autoclose=True)
    # Launch a dedicated thread to read stdin in blocking mode. Indeed stdin
    # can be a file, so we cannot use a WorkerSimple here as polling on file
    # may result in different behaviors depending on selected engine.
    threading.Thread(None, _stdin_thread_start, args=(port, display)).start()

def run_command(task, cmd, ns, timeout, display):
    """
    Create and run the specified command line, displaying
    results in a dshbak way when gathering is used.
    """
    task.set_default("USER_running", True)

    if display.verbosity >= VERB_VERB and task.topology:
        print Display.COLOR_RESULT_FMT % '-' * 15
        print Display.COLOR_RESULT_FMT % task.topology,
        print Display.COLOR_RESULT_FMT % '-' * 15

    if (display.gather or display.line_mode) and ns is not None:
        if display.gather and display.line_mode:
            handler = LiveGatherOutputHandler(display, ns)
        else:
            handler = GatherOutputHandler(display)

        if display.verbosity == VERB_STD or display.verbosity == VERB_VERB:
            handler.runtimer_init(task, len(ns))

        worker = task.shell(cmd, nodes=ns, handler=handler, timeout=timeout)
    else:
        worker = task.shell(cmd, nodes=ns, handler=DirectOutputHandler(display),
                            timeout=timeout)
    if ns is None:
        worker.set_key('LOCAL')
    if task.default("USER_stdin_worker"):
        bind_stdin(worker, display)

    task.resume()

def run_copy(task, sources, dest, ns, timeout, preserve_flag, display):
    """
    run copy command
    """
    task.set_default("USER_running", True)
    task.set_default("USER_copies", len(sources))

    copyhandler = CopyOutputHandler(display)
    if display.verbosity == VERB_STD or display.verbosity == VERB_VERB:
        copyhandler.runtimer_init(task, len(ns) * len(sources))

    # Sources check
    for source in sources:
        if not os.path.exists(source):
            display.vprint_err(VERB_QUIET, "ERROR: file \"%s\" not found" % \
                                           source)
            clush_exit(1, task)
        task.copy(source, dest, ns, handler=copyhandler, timeout=timeout,
                  preserve=preserve_flag)
    task.resume()

def run_rcopy(task, sources, dest, ns, timeout, preserve_flag, display):
    """
    run reverse copy command
    """
    task.set_default("USER_running", True)
    task.set_default("USER_copies", len(sources))

    # Sanity checks
    if not os.path.exists(dest):
        display.vprint_err(VERB_QUIET, "ERROR: directory \"%s\" not found" % \
                                       dest)
        clush_exit(1, task)
    if not os.path.isdir(dest):
        display.vprint_err(VERB_QUIET, \
            "ERROR: destination \"%s\" is not a directory" % dest)
        clush_exit(1, task)

    copyhandler = CopyOutputHandler(display, True)
    if display.verbosity == VERB_STD or display.verbosity == VERB_VERB:
        copyhandler.runtimer_init(task, len(ns) * len(sources))
    for source in sources:
        task.rcopy(source, dest, ns, handler=copyhandler, timeout=timeout,
                   preserve=preserve_flag)
    task.resume()

def set_fdlimit(fd_max, display):
    """Make open file descriptors soft limit the max."""
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if hard < fd_max:
        display.vprint(VERB_DEBUG, "Warning: Consider increasing max open " \
            "files hard limit (%d)" % hard)
    rlim_max = min(hard, fd_max)
    if soft != rlim_max:
        display.vprint(VERB_DEBUG, "Modifying max open files soft limit: " \
            "%d -> %d" % (soft, rlim_max))
        resource.setrlimit(resource.RLIMIT_NOFILE, (rlim_max, hard))

def clush_exit(status, task=None):
    """Exit script, flushing stdio buffers and stopping ClusterShell task."""
    if task:
        # Clean, usual termination
        task.abort()
        task.join()
        sys.exit(status)
    else:
        for stream in [sys.stdout, sys.stderr]:
            stream.flush()
        # Use os._exit to avoid threads cleanup
        os._exit(status)

def clush_excepthook(extype, value, traceback):
    """Exceptions hook for clush: this method centralizes exception
    handling from main thread and from (possible) separate task thread.
    This hook has to be previously installed on startup by overriding
    sys.excepthook and task.excepthook."""
    try:
        raise extype(value)
    except ClushConfigError, econf:
        print >> sys.stderr, "ERROR: %s" % econf
    except KeyboardInterrupt, kbe:
        uncomp_nodes = getattr(kbe, 'uncompleted_nodes', None)
        if uncomp_nodes:
            print >> sys.stderr, \
                "Keyboard interrupt (%s did not complete)." % uncomp_nodes
        else:
            print >> sys.stderr, "Keyboard interrupt."
        clush_exit(128 + signal.SIGINT)
    except OSError, exp:
        print >> sys.stderr, "ERROR: %s" % exp
        if exp.errno == errno.EMFILE:
            print >> sys.stderr, "ERROR: current `nofile' limits: " \
                "soft=%d hard=%d" % resource.getrlimit(resource.RLIMIT_NOFILE)
        clush_exit(1)
    except GENERIC_ERRORS, exc:
        clush_exit(handle_generic_error(exc))

    # Error not handled
    task_self().default_excepthook(extype, value, traceback)

def main():
    """clush script entry point"""
    sys.excepthook = clush_excepthook

    # Default values
    nodeset_base, nodeset_exclude = NodeSet(), NodeSet()

    #
    # Argument management
    #
    usage = "%prog [options] command"

    parser = OptionParser(usage)

    parser.add_option("--nostdin", action="store_true", dest="nostdin",
                      help="don't watch for possible input from stdin")

    parser.install_nodes_options()
    parser.install_display_options(verbose_options=True)
    parser.install_filecopy_options()
    parser.install_ssh_options()

    (options, args) = parser.parse_args()

    #
    # Load config file and apply overrides
    #
    config = ClushConfig(options)

    # Should we use ANSI colors for nodes?
    if config.color == "auto":
        color = sys.stdout.isatty() and (options.gatherall or \
                                         sys.stderr.isatty())
    else:
        color = config.color == "always"

    try:
        # Create and configure display object.
        display = Display(options, config, color)
    except ValueError, exc:
        parser.error("option mismatch (%s)" % exc)

    #
    # Compute the nodeset
    #
    if options.nodes:
        nodeset_base = NodeSet.fromlist(options.nodes)
    if options.exclude:
        nodeset_exclude = NodeSet.fromlist(options.exclude)

    if options.groupsource:
        # Be sure -a/g -s source work as espected.
        std_group_resolver().default_sourcename = options.groupsource

    # FIXME: add public API to enforce engine
    Task._std_default['engine'] = options.engine

    # Do we have nodes group?
    task = task_self()
    task.set_info("debug", config.verbosity >= VERB_DEBUG)
    if config.verbosity == VERB_DEBUG:
        std_group_resolver().set_verbosity(1)
    if options.nodes_all:
        all_nodeset = NodeSet.fromall()
        display.vprint(VERB_DEBUG, "Adding nodes from option -a: %s" % \
                                   all_nodeset)
        nodeset_base.add(all_nodeset)

    if options.group:
        grp_nodeset = NodeSet.fromlist(options.group,
                                       resolver=RESOLVER_NOGROUP)
        for grp in grp_nodeset:
            addingrp = NodeSet("@" + grp)
            display.vprint(VERB_DEBUG, \
                "Adding nodes from option -g %s: %s" % (grp, addingrp))
            nodeset_base.update(addingrp)

    if options.exgroup:
        grp_nodeset = NodeSet.fromlist(options.exgroup,
                                       resolver=RESOLVER_NOGROUP)
        for grp in grp_nodeset:
            removingrp = NodeSet("@" + grp)
            display.vprint(VERB_DEBUG, \
                "Excluding nodes from option -X %s: %s" % (grp, removingrp))
            nodeset_exclude.update(removingrp)

    # Do we have an exclude list? (-x ...)
    nodeset_base.difference_update(nodeset_exclude)
    if len(nodeset_base) < 1:
        parser.error('No node to run on.')

    # Set open files limit.
    set_fdlimit(config.fd_max, display)

    #
    # Task management
    #
    # check for clush interactive mode
    interactive = not len(args) and \
                  not (options.copy or options.rcopy)
    # check for foreground ttys presence (input)
    stdin_isafgtty = sys.stdin.isatty() and \
        os.tcgetpgrp(sys.stdin.fileno()) == os.getpgrp()
    # check for special condition (empty command and stdin not a tty)
    if interactive and not stdin_isafgtty:
        # looks like interactive but stdin is not a tty:
        # switch to non-interactive + disable ssh pseudo-tty
        interactive = False
        # SSH: disable pseudo-tty allocation (-T)
        ssh_options = config.ssh_options or ''
        ssh_options += ' -T'
        config._set_main("ssh_options", ssh_options)
    if options.nostdin and interactive:
        parser.error("illegal option `--nostdin' in that case")

    # Force user_interaction if Clush._f_user_interaction for test purposes
    user_interaction = hasattr(sys.modules[__name__], '_f_user_interaction')
    if not options.nostdin:
        # Try user interaction: check for foreground ttys presence (ouput)
        stdout_isafgtty = sys.stdout.isatty() and \
            os.tcgetpgrp(sys.stdout.fileno()) == os.getpgrp()
        user_interaction |= stdin_isafgtty and stdout_isafgtty
    display.vprint(VERB_DEBUG, "User interaction: %s" % user_interaction)
    if user_interaction:
        # Standard input is a terminal and we want to perform some user
        # interactions in the main thread (using blocking calls), so
        # we run cluster commands in a new ClusterShell Task (a new
        # thread is created).
        task = Task()
    # else: perform everything in the main thread

    # Handle special signal only when user_interaction is set
    task.set_default("USER_handle_SIGUSR1", user_interaction)

    task.excepthook = sys.excepthook
    task.set_default("USER_stdin_worker", not (sys.stdin.isatty() or \
                                               options.nostdin or \
                                               user_interaction))
    display.vprint(VERB_DEBUG, "Create STDIN worker: %s" % \
                               task.default("USER_stdin_worker"))

    if config.verbosity >= VERB_DEBUG:
        task.set_info("debug", True)
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("clush: STARTING DEBUG")

    task.set_info("fanout", config.fanout)

    if options.topofile:
        if config.verbosity >= VERB_VERB:
            print Display.COLOR_RESULT_FMT % \
                "Enabling TREE MODE (technology preview)"
        task.set_default("auto_tree", True)
        task.set_topology(options.topofile)

    if options.grooming_delay:
        if config.verbosity >= VERB_VERB:
            print Display.COLOR_RESULT_FMT % ("Grooming delay: %f" % \
                                              options.grooming_delay)
        task.set_info("grooming_delay", options.grooming_delay)

    if config.ssh_user:
        task.set_info("ssh_user", config.ssh_user)
    if config.ssh_path:
        task.set_info("ssh_path", config.ssh_path)
    if config.ssh_options:
        task.set_info("ssh_options", config.ssh_options)
    if config.rsh_path:
        task.set_info("rsh_path", config.rsh_path)
    if config.rcp_path:
        task.set_info("rcp_path", config.rcp_path)
    if config.rsh_options:
        task.set_info("rsh_options", config.rsh_options)

    # Set detailed timeout values
    task.set_info("connect_timeout", config.connect_timeout)
    command_timeout = config.command_timeout
    task.set_info("command_timeout", command_timeout)

    # Enable stdout/stderr separation
    task.set_default("stderr", not options.gatherall)

    # Disable MsgTree buffering if not gathering outputs
    task.set_default("stdout_msgtree", display.gather or display.line_mode)

    # Always disable stderr MsgTree buffering
    task.set_default("stderr_msgtree", False)

    # Set timeout at worker level when command_timeout is defined.
    if command_timeout > 0:
        timeout = command_timeout
    else:
        timeout = -1

    # Configure task custom status
    task.set_default("USER_interactive", interactive)
    task.set_default("USER_running", False)

    if (options.copy or options.rcopy) and not args:
        parser.error("--[r]copy option requires at least one argument")
    if options.copy:
        if not options.dest_path:
            options.dest_path = os.path.dirname(os.path.abspath(args[0]))
        op = "copy sources=%s dest=%s" % (args, options.dest_path)
    elif options.rcopy:
        if not options.dest_path:
            options.dest_path = os.path.dirname(os.path.abspath(args[0]))
        op = "rcopy sources=%s dest=%s" % (args, options.dest_path)
    else:
        op = "command=\"%s\"" % ' '.join(args)

    # print debug values (fanout value is get from the config object
    # and not task itself as set_info() is an asynchronous call.
    display.vprint(VERB_DEBUG, "clush: nodeset=%s fanout=%d [timeout " \
                   "conn=%.1f cmd=%.1f] %s" %  (nodeset_base, config.fanout,
                                                task.info("connect_timeout"),
                                                task.info("command_timeout"),
                                                op))
    if not task.default("USER_interactive"):
        if options.copy:
            run_copy(task, args, options.dest_path, nodeset_base, timeout,
                     options.preserve_flag, display)
        elif options.rcopy:
            run_rcopy(task, args, options.dest_path, nodeset_base, timeout,
                      options.preserve_flag, display)
        else:
            run_command(task, ' '.join(args), nodeset_base, timeout, display)

    if user_interaction:
        ttyloop(task, nodeset_base, timeout, display)
    elif task.default("USER_interactive"):
        display.vprint_err(VERB_QUIET, \
            "ERROR: interactive mode requires a tty")
        clush_exit(1, task)

    rc = 0
    if options.maxrc:
        # Instead of clush return code, return commands retcode
        rc = task.max_retcode()
        if task.num_timeout() > 0:
            rc = 255
    clush_exit(rc, task)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = Config
#!/usr/bin/env python
#
# Copyright CEA/DAM/DIF (2010, 2011)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
CLI configuration classes
"""

import ConfigParser
import os

from ClusterShell.CLI.Display import VERB_QUIET, VERB_STD, \
    VERB_VERB, VERB_DEBUG, THREE_CHOICES


class ClushConfigError(Exception):
    """Exception used by ClushConfig to report an error."""
    def __init__(self, section, option, msg):
        Exception.__init__(self)
        self.section = section
        self.option = option
        self.msg = msg

    def __str__(self):
        return "(Config %s.%s): %s" % (self.section, self.option, self.msg)

class ClushConfig(ConfigParser.ConfigParser, object):
    """Config class for clush (specialized ConfigParser)"""

    main_defaults = { "fanout" : "64",
                      "connect_timeout" : "30",
                      "command_timeout" : "0",
                      "history_size" : "100",
                      "color" : THREE_CHOICES[-1], # auto
                      "verbosity" : "%d" % VERB_STD,
                      "node_count" : "yes",
                      "fd_max" : "16384" }

    def __init__(self, options, filename=None):
        """Initialize ClushConfig object from corresponding
        OptionParser options."""
        ConfigParser.ConfigParser.__init__(self)
        # create Main section with default values
        self.add_section("Main")
        for key, value in ClushConfig.main_defaults.iteritems():
            self.set("Main", key, value)
        # config files override defaults values
        if filename:
            files = [filename]
        else:
            files = ['/etc/clustershell/clush.conf',
                     os.path.expanduser('~/.clush.conf')]
        self.read(files)

        # Apply command line overrides
        if options.quiet:
            self._set_main("verbosity", VERB_QUIET)
        if options.verbose:
            self._set_main("verbosity", VERB_VERB)
        if options.debug:
            self._set_main("verbosity", VERB_DEBUG)
        if options.fanout:
            self._set_main("fanout", options.fanout)
        if options.user:
            self._set_main("ssh_user", options.user)
        if options.options:
            self._set_main("ssh_options", options.options)
        if options.connect_timeout:
            self._set_main("connect_timeout", options.connect_timeout)
        if options.command_timeout:
            self._set_main("command_timeout", options.command_timeout)
        if options.whencolor:
            self._set_main("color", options.whencolor)

    def _set_main(self, option, value):
        """Set given option/value pair in the Main section."""
        self.set("Main", option, str(value))

    def _getx(self, xtype, section, option):
        """Return a value of specified type for the named option."""
        try:
            return getattr(ConfigParser.ConfigParser, 'get%s' % xtype)(self, \
                section, option)
        except (ConfigParser.Error, TypeError, ValueError), exc:
            raise ClushConfigError(section, option, exc)

    def getboolean(self, section, option):
        """Return a boolean value for the named option."""
        return self._getx('boolean', section, option)

    def getfloat(self, section, option):
        """Return a float value for the named option."""
        return self._getx('float', section, option)

    def getint(self, section, option):
        """Return an integer value for the named option."""
        return self._getx('int', section, option)

    def _get_optional(self, section, option):
        """Utility method to get a value for the named option, but do
        not raise an exception if the option doesn't exist."""
        try:
            return self.get(section, option)
        except ConfigParser.Error:
            pass

    @property
    def verbosity(self):
        """verbosity value as an integer"""
        try:
            return self.getint("Main", "verbosity")
        except ClushConfigError:
            return 0

    @property
    def fanout(self):
        """fanout value as an integer"""
        return self.getint("Main", "fanout")

    @property
    def connect_timeout(self):
        """connect_timeout value as a float"""
        return self.getfloat("Main", "connect_timeout")

    @property
    def command_timeout(self):
        """command_timeout value as a float"""
        return self.getfloat("Main", "command_timeout")

    @property
    def ssh_user(self):
        """ssh_user value as a string (optional)"""
        return self._get_optional("Main", "ssh_user")

    @property
    def ssh_path(self):
        """ssh_path value as a string (optional)"""
        return self._get_optional("Main", "ssh_path")

    @property
    def ssh_options(self):
        """ssh_options value as a string (optional)"""
        return self._get_optional("Main", "ssh_options")

    @property
    def rsh_path(self):
        """rsh_path value as a string (optional)"""
        return self._get_optional("Main", "rsh_path")

    @property
    def rcp_path(self):
        """rcp_path value as a string (optional)"""
        return self._get_optional("Main", "rcp_path")

    @property
    def rsh_options(self):
        """rsh_options value as a string (optional)"""
        return self._get_optional("Main", "rsh_options")

    @property
    def color(self):
        """color value as a string in (never, always, auto)"""
        whencolor = self._get_optional("Main", "color")
        if whencolor not in THREE_CHOICES:
            raise ClushConfigError("Main", "color", "choose from %s" % \
                                   THREE_CHOICES)
        return whencolor

    @property
    def node_count(self):
        """node_count value as a boolean"""
        return self.getboolean("Main", "node_count")

    @property
    def fd_max(self):
        """max number of open files (soft rlimit)"""
        return self.getint("Main", "fd_max")


########NEW FILE########
__FILENAME__ = Display
#!/usr/bin/env python
#
# Copyright CEA/DAM/DIF (2010, 2011, 2012)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
CLI results display class
"""

import difflib
import sys

from ClusterShell.NodeSet import NodeSet

# Display constants
VERB_QUIET = 0
VERB_STD = 1
VERB_VERB = 2
VERB_DEBUG = 3
THREE_CHOICES = ["never", "always", "auto"]
WHENCOLOR_CHOICES = THREE_CHOICES   # deprecated; use THREE_CHOICES


class Display(object):
    """
    Output display class for command line scripts.
    """
    COLOR_RESULT_FMT = "\033[32m%s\033[0m"
    COLOR_STDOUT_FMT = "\033[34m%s\033[0m"
    COLOR_STDERR_FMT = "\033[31m%s\033[0m"
    COLOR_DIFFHDR_FMT = "\033[1m%s\033[0m"
    COLOR_DIFFHNK_FMT = "\033[36m%s\033[0m"
    COLOR_DIFFADD_FMT = "\033[32m%s\033[0m"
    COLOR_DIFFDEL_FMT = "\033[31m%s\033[0m"
    SEP = "-" * 15

    class _KeySet(set):
        """Private NodeSet substition to display raw keys"""
        def __str__(self):
            return ",".join(self)

    def __init__(self, options, config=None, color=None):
        """Initialize a Display object from CLI.OptionParser options
        and optional CLI.ClushConfig.

        If `color' boolean flag is not specified, it is auto detected
        according to options.whencolor.
        """
        if options.diff:
            self._print_buffer = self._print_diff
        else:
            self._print_buffer = self._print_content
        self._display = self._print_buffer
        self._diffref = None
        # diff implies at least -b
        self.gather = options.gatherall or options.gather or options.diff
        # check parameter combinaison
        if options.diff and options.line_mode:
            raise ValueError("diff not supported in line_mode")
        self.line_mode = options.line_mode
        self.label = options.label
        self.regroup = options.regroup
        self.groupsource = options.groupsource
        self.noprefix = options.groupbase
        # display may change when 'max return code' option is set
        self.maxrc = getattr(options, 'maxrc', False)

        if color is None:
            # Should we use ANSI colors?
            color = False
            if not options.whencolor or options.whencolor == "auto":
                color = sys.stdout.isatty()
            elif options.whencolor == "always":
                color = True

        self._color = color

        self.out = sys.stdout
        self.err = sys.stderr
        if self._color:
            self.color_stdout_fmt = self.COLOR_STDOUT_FMT
            self.color_stderr_fmt = self.COLOR_STDERR_FMT
            self.color_diffhdr_fmt = self.COLOR_DIFFHDR_FMT
            self.color_diffctx_fmt = self.COLOR_DIFFHNK_FMT
            self.color_diffadd_fmt = self.COLOR_DIFFADD_FMT
            self.color_diffdel_fmt = self.COLOR_DIFFDEL_FMT
        else:
            self.color_stdout_fmt = self.color_stderr_fmt = \
                self.color_diffhdr_fmt = self.color_diffctx_fmt = \
                self.color_diffadd_fmt = self.color_diffdel_fmt = "%s"

        # Set display verbosity
        if config:
            # config object does already apply options overrides
            self.node_count = config.node_count
            self.verbosity = config.verbosity
        else:
            self.node_count = True
            self.verbosity = VERB_STD
            if hasattr(options, 'quiet') and options.quiet:
                self.verbosity = VERB_QUIET
            if hasattr(options, 'verbose') and options.verbose:
                self.verbosity = VERB_VERB
            if hasattr(options, 'debug') and options.debug:
                self.verbosity = VERB_DEBUG

    def flush(self):
        """flush display object buffers"""
        # only used to reset diff display for now
        self._diffref = None

    def _getlmode(self):
        """line_mode getter"""
        return self._display == self._print_lines

    def _setlmode(self, value):
        """line_mode setter"""
        if value:
            self._display = self._print_lines
        else:
            self._display = self._print_buffer
    line_mode = property(_getlmode, _setlmode)

    def _format_nodeset(self, nodeset):
        """Sub-routine to format nodeset string."""
        if self.regroup:
            return nodeset.regroup(self.groupsource, noprefix=self.noprefix)
        return str(nodeset)

    def format_header(self, nodeset, indent=0):
        """Format nodeset-based header."""
        indstr = " " * indent
        nodecntstr = ""
        if self.verbosity >= VERB_STD and self.node_count and len(nodeset) > 1:
            nodecntstr = " (%d)" % len(nodeset)
        if not self.label:
            return ""
        return self.color_stdout_fmt % ("%s%s\n%s%s%s\n%s%s" % \
            (indstr, self.SEP,
             indstr, self._format_nodeset(nodeset), nodecntstr,
             indstr, self.SEP))

    def print_line(self, nodeset, line):
        """Display a line with optional label."""
        if self.label:
            prefix = self.color_stdout_fmt % ("%s: " % nodeset)
            self.out.write("%s%s\n" % (prefix, line))
        else:
            self.out.write("%s\n" % line)

    def print_line_error(self, nodeset, line):
        """Display an error line with optional label."""
        if self.label:
            prefix = self.color_stderr_fmt % ("%s: " % nodeset)
            self.err.write("%s%s\n" % (prefix, line))
        else:
            self.err.write("%s\n" % line)

    def print_gather(self, nodeset, obj):
        """Generic method for displaying nodeset/content according to current
        object settings."""
        return self._display(NodeSet(nodeset), obj)

    def print_gather_keys(self, keys, obj):
        """Generic method for displaying raw keys/content according to current
        object settings (used by clubak)."""
        return self._display(self.__class__._KeySet(keys), obj)

    def _print_content(self, nodeset, content):
        """Display a dshbak-like header block and content."""
        self.out.write("%s\n%s\n" % (self.format_header(nodeset), content))

    def _print_diff(self, nodeset, content):
        """Display unified diff between remote gathered outputs."""
        if self._diffref is None:
            self._diffref = (nodeset, content)
        else:
            nodeset_ref, content_ref = self._diffref
            nsstr_ref = self._format_nodeset(nodeset_ref)
            nsstr = self._format_nodeset(nodeset)
            if self.verbosity >= VERB_STD and self.node_count:
                if len(nodeset_ref) > 1:
                    nsstr_ref += " (%d)" % len(nodeset_ref)
                if len(nodeset) > 1:
                    nsstr += " (%d)" % len(nodeset)

            udiff = difflib.unified_diff(list(content_ref), list(content), \
                                         fromfile=nsstr_ref, tofile=nsstr, \
                                         lineterm='')
            output = ""
            for line in udiff:
                if line.startswith('---') or line.startswith('+++'):
                    output += self.color_diffhdr_fmt % line.rstrip()
                elif line.startswith('@@'):
                    output += self.color_diffctx_fmt % line
                elif line.startswith('+'):
                    output += self.color_diffadd_fmt % line
                elif line.startswith('-'):
                    output += self.color_diffdel_fmt % line
                else:
                    output += line
                output += '\n'
            self.out.write(output)

    def _print_lines(self, nodeset, msg):
        """Display a MsgTree buffer by line with prefixed header."""
        out = self.out
        if self.label:
            if self.gather:
                header = self.color_stdout_fmt % \
                            ("%s: " % self._format_nodeset(nodeset))
                for line in msg:
                    out.write("%s%s\n" % (header, line))
            else:
                for node in nodeset:
                    header = self.color_stdout_fmt % \
                                ("%s: " % self._format_nodeset(node))
                    for line in msg:
                        out.write("%s%s\n" % (header, line))
        else:
            if self.gather:
                for line in msg:
                    out.write(line + '\n')
            else:
                for node in nodeset:
                    for line in msg:
                        out.write(line + '\n')

    def vprint(self, level, message):
        """Utility method to print a message if verbose level is high
        enough."""
        if self.verbosity >= level:
            print message

    def vprint_err(self, level, message):
        """Utility method to print a message on stderr if verbose level
        is high enough."""
        if self.verbosity >= level:
            print >> sys.stderr, message


########NEW FILE########
__FILENAME__ = Error
#!/usr/bin/env python
#
# Copyright CEA/DAM/DIF (2010, 2011, 2012)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
CLI error handling helper functions
"""

import os.path
import signal
import sys

from ClusterShell.Engine.Engine import EngineNotSupportedError
from ClusterShell.CLI.Utils import GroupResolverConfigError  # dummy but safe
from ClusterShell.NodeUtils import GroupResolverIllegalCharError
from ClusterShell.NodeUtils import GroupResolverSourceError
from ClusterShell.NodeUtils import GroupSourceException
from ClusterShell.NodeUtils import GroupSourceNoUpcall
from ClusterShell.NodeSet import NodeSetExternalError, NodeSetParseError
from ClusterShell.NodeSet import RangeSetParseError
from ClusterShell.Topology import TopologyError


GENERIC_ERRORS = (EngineNotSupportedError,
                  NodeSetExternalError,
                  NodeSetParseError,
                  RangeSetParseError,
                  GroupResolverIllegalCharError,
                  GroupResolverSourceError,
                  GroupSourceNoUpcall,
                  GroupSourceException,
                  TopologyError,
                  IOError,
                  KeyboardInterrupt)

def handle_generic_error(excobj, prog=os.path.basename(sys.argv[0])):
    """handle error given `excobj' generic script exception"""
    try:
        raise excobj
    except EngineNotSupportedError, exc:
        print >> sys.stderr, "%s: I/O events engine '%s' not supported on " \
            "this host" % (prog, exc.engineid)
    except NodeSetExternalError, exc:
        print >> sys.stderr, "%s: External error:" % prog, exc
    except (NodeSetParseError, RangeSetParseError), exc:
        print >> sys.stderr, "%s: Parse error:" % prog, exc
    except GroupResolverIllegalCharError, exc:
        print >> sys.stderr, "%s: Illegal group character: \"%s\"" % (prog, exc)
    except GroupResolverSourceError, exc:
        print >> sys.stderr, "%s: Unknown group source: \"%s\"" % (prog, exc)
    except GroupSourceNoUpcall, exc:
        print >> sys.stderr, "%s: No %s upcall defined for group " \
            "source \"%s\"" % (prog, exc, exc.group_source.name)
    except GroupSourceException, exc:
        print >> sys.stderr, "%s: Other group error:" % prog, exc
    except TopologyError, exc:
        print >> sys.stderr, "%s: TREE MODE:" % prog, exc
    except IOError:
        # ignore broken pipe
        pass
    except KeyboardInterrupt, exc:
        return 128 + signal.SIGINT
    except:
        assert False, "wrong GENERIC_ERRORS"

    # Exit with error code 1 (generic failure)
    return 1
        

########NEW FILE########
__FILENAME__ = Nodeset
#!/usr/bin/env python
#
# Copyright CEA/DAM/DIF (2008, 2009, 2010, 2011, 2012)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
compute advanced nodeset operations

The nodeset command is an utility command provided with the
ClusterShell library which implements some features of the NodeSet
and RangeSet classes.
"""

import sys

from ClusterShell.CLI.Error import GENERIC_ERRORS, handle_generic_error
from ClusterShell.CLI.OptionParser import OptionParser
from ClusterShell.CLI.Utils import NodeSet  # safe import

from ClusterShell.NodeSet import RangeSet, grouplist, std_group_resolver


def process_stdin(xsetop, xsetcls, autostep):
    """Process standard input and operate on xset."""
    # Build temporary set (stdin accumulator)
    tmpset = xsetcls(autostep=autostep)
    for line in sys.stdin.readlines():
        # Support multi-lines and multi-nodesets per line
        line = line[0:line.find('#')].strip()
        for elem in line.split():
            # Do explicit object creation for RangeSet
            tmpset.update(xsetcls(elem, autostep=autostep))
    # Perform operation on xset
    if tmpset:
        xsetop(tmpset)

def compute_nodeset(xset, args, autostep):
    """Apply operations and operands from args on xset, an initial
    RangeSet or NodeSet."""
    class_set = xset.__class__
    # Process operations
    while args:
        arg = args.pop(0)
        if arg in ("-i", "--intersection"):
            val = args.pop(0)
            if val == '-':
                process_stdin(xset.intersection_update, class_set, autostep)
            else:
                xset.intersection_update(class_set(val, autostep=autostep))
        elif arg in ("-x", "--exclude"):
            val = args.pop(0)
            if val == '-':
                process_stdin(xset.difference_update, class_set, autostep)
            else:
                xset.difference_update(class_set(val, autostep=autostep))
        elif arg in ("-X", "--xor"):
            val = args.pop(0)
            if val == '-':
                process_stdin(xset.symmetric_difference_update, class_set,
                              autostep)
            else:
                xset.symmetric_difference_update(class_set(val,
                                                           autostep=autostep))
        elif arg == '-':
            process_stdin(xset.update, xset.__class__, autostep)
        else:
            xset.update(class_set(arg, autostep=autostep))

    return xset

def command_list(options, xset):
    """List (-l/-ll/-lll) command handler."""
    list_level = options.list
    # list groups of some specified nodes?
    if options.all or xset or \
        options.and_nodes or options.sub_nodes or options.xor_nodes:
        # When some node sets are provided as argument, the list command
        # retrieves node groups these nodes belong to, thanks to the
        # groups() method (new in 1.6). Note: stdin support is enabled
        # when the '-' special character is encountered.
        groups = xset.groups(options.groupsource, options.groupbase)
        for group, (gnodes, inodes) in groups.iteritems():
            if list_level == 1:         # -l
                print group
            elif list_level == 2:       # -ll
                print "%s %s" % (group, inodes)
            else:                       # -lll
                print "%s %s %d/%d" % (group, inodes, len(inodes), \
                                       len(gnodes))
        return
    # "raw" group list when no argument at all
    for group in grouplist(options.groupsource):
        if options.groupsource and not options.groupbase:
            nsgroup = "@%s:%s" % (options.groupsource, group)
        else:
            nsgroup = "@%s" % group
        if list_level == 1:         # -l
            print nsgroup
        else:
            nodes = NodeSet(nsgroup)
            if list_level == 2:     # -ll
                print "%s %s" % (nsgroup, nodes)
            else:                   # -lll
                print "%s %s %d" % (nsgroup, nodes, len(nodes))

def nodeset():
    """script subroutine"""
    class_set = NodeSet
    usage = "%prog [COMMAND] [OPTIONS] [ns1 [-ixX] ns2|...]"

    parser = OptionParser(usage)
    parser.install_nodeset_commands()
    parser.install_nodeset_operations()
    parser.install_nodeset_options()
    (options, args) = parser.parse_args()

    group_resolver = std_group_resolver()

    if options.debug:
        group_resolver.set_verbosity(1)

    # Check for command presence
    cmdcount = int(options.count) + int(options.expand) + \
               int(options.fold) + int(bool(options.list)) + \
               int(options.regroup) + int(options.groupsources)
    if not cmdcount:
        parser.error("No command specified.")
    elif cmdcount > 1:
        parser.error("Multiple commands not allowed.")

    if options.rangeset:
        class_set = RangeSet

    if options.all or options.regroup:
        if class_set != NodeSet:
            parser.error("-a/-r only supported in NodeSet mode")

    if options.maxsplit is not None and options.contiguous:
        parser.error("incompatible splitting options (split, contiguous)")

    if options.maxsplit is None:
        options.maxsplit = 1

    if options.groupsource and not options.quiet and \
       (class_set == RangeSet or options.groupsources):
        print >> sys.stderr, "WARNING: option group source \"%s\" ignored" \
                                % options.groupsource

    # The groupsources command simply lists group sources.
    if options.groupsources:
        if options.quiet:
            dispdefault = ""    # don't show (default) if quiet is set
        else:
            dispdefault = " (default)"
        for src in group_resolver.sources():
            print "%s%s" % (src, dispdefault)
            dispdefault = ""
        return

    # We want -s <groupsource> to act as a substition of default groupsource
    # (ie. it's not necessary to prefix group names by this group source).
    if options.groupsource:
        group_resolver.default_sourcename = options.groupsource

    # Instantiate RangeSet or NodeSet object
    xset = class_set(autostep=options.autostep)

    if options.all:
        # Include all nodes from external node groups support.
        xset.update(NodeSet.fromall()) # uses default_sourcename

    if not args and not options.all and not options.list:
        # No need to specify '-' to read stdin in these cases
        process_stdin(xset.update, xset.__class__, options.autostep)

    # Apply first operations (before first non-option)
    for nodes in options.and_nodes:
        if nodes == '-':
            process_stdin(xset.intersection_update, xset.__class__,
                          options.autostep)
        else:
            xset.intersection_update(class_set(nodes,
                                               autostep=options.autostep))
    for nodes in options.sub_nodes:
        if nodes == '-':
            process_stdin(xset.difference_update, xset.__class__,
                          options.autostep)
        else:
            xset.difference_update(class_set(nodes, autostep=options.autostep))
    for nodes in options.xor_nodes:
        if nodes == '-':
            process_stdin(xset.symmetric_difference_update, xset.__class__,
                          options.autostep)
        else:
            xset.symmetric_difference_update(class_set(nodes, \
                                             autostep=options.autostep))

    # Finish xset computing from args
    compute_nodeset(xset, args, options.autostep)

    # The list command has a special handling
    if options.list > 0:
        return command_list(options, xset)

    # Interprete special characters (may raise SyntaxError)
    separator = eval('\'%s\'' % options.separator, {"__builtins__":None}, {})

    if options.slice_rangeset:
        _xset = class_set()
        for sli in RangeSet(options.slice_rangeset).slices():
            _xset.update(xset[sli])
        xset = _xset

    # Display result according to command choice
    if options.expand:
        xsubres = lambda x: separator.join(x.striter())
    elif options.fold:
        xsubres = lambda x: x
    elif options.regroup:
        xsubres = lambda x: x.regroup(options.groupsource, \
                                      noprefix=options.groupbase)
    else:
        xsubres = len

    if not xset or options.maxsplit <= 1 and not options.contiguous:
        print xsubres(xset)
    else:
        if options.contiguous:
            xiterator = xset.contiguous()
        else:
            xiterator = xset.split(options.maxsplit)
        for xsubset in xiterator:
            print xsubres(xsubset)

def main():
    """main script function"""
    try:
        nodeset()
    except AssertionError, ex:
        print >> sys.stderr, "ERROR:", ex
        sys.exit(1)
    except IndexError:
        print >> sys.stderr, "ERROR: syntax error"
        sys.exit(1)
    except SyntaxError:
        print >> sys.stderr, "ERROR: invalid separator"
        sys.exit(1)
    except GENERIC_ERRORS, ex:
        sys.exit(handle_generic_error(ex))

    sys.exit(0)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = OptionParser
#!/usr/bin/env python
#
# Copyright CEA/DAM/DIF (2010, 2011, 2012)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
common ClusterShell CLI OptionParser

With few exceptions, ClusterShell command-lines share most option
arguments. This module provides a common OptionParser class.
"""

from copy import copy
import optparse

from ClusterShell import __version__
from ClusterShell.Engine.Factory import PreferredEngine
from ClusterShell.CLI.Display import THREE_CHOICES

def check_safestring(option, opt, value):
    """type-checker function for safestring"""
    try:
        safestr = str(value)
        # check if the string is not empty and not an option
        if not safestr or safestr.startswith('-'):
            raise ValueError()
        return safestr
    except ValueError:
        raise optparse.OptionValueError(
            "option %s: invalid value: %r" % (opt, value))


class Option(optparse.Option):
    """This Option subclass adds a new safestring type."""
    TYPES = optparse.Option.TYPES + ("safestring",)
    TYPE_CHECKER = copy(optparse.Option.TYPE_CHECKER)
    TYPE_CHECKER["safestring"] = check_safestring

class OptionParser(optparse.OptionParser):
    """Derived OptionParser for all CLIs"""
    
    def __init__(self, usage, **kwargs):
        """Initialize ClusterShell CLI OptionParser"""
        optparse.OptionParser.__init__(self, usage,
                                       version="%%prog %s" % __version__,
                                       option_class=Option,
                                       **kwargs)

        # Set parsing to stop on the first non-option
        self.disable_interspersed_args()

        # Always install groupsource support
        self.add_option("-s", "--groupsource", action="store",
                        type="safestring", dest="groupsource",
                        help="optional groups.conf(5) group source to use")

    def install_nodes_options(self):
        """Install nodes selection options"""
        optgrp = optparse.OptionGroup(self, "Selecting target nodes")
        optgrp.add_option("-w", action="append", type="safestring",
                          dest="nodes", help="nodes where to run the command")
        optgrp.add_option("-x", action="append", type="safestring",
                          dest="exclude", metavar="NODES",
                          help="exclude nodes from the node list")
        optgrp.add_option("-a", "--all", action="store_true", dest="nodes_all",
                          help="run command on all nodes")
        optgrp.add_option("-g", "--group", action="append", type="safestring",
                          dest="group", help="run command on a group of nodes")
        optgrp.add_option("-X", action="append", dest="exgroup",
                          metavar="GROUP", type="safestring",
                          help="exclude nodes from this group")
        optgrp.add_option("-E", "--engine", action="store", dest="engine",
                          choices=["auto"] + PreferredEngine.engines.keys(),
                          default="auto", help=optparse.SUPPRESS_HELP)
        optgrp.add_option("-T", "--topology", action="store", dest="topofile",
                          default=None, help=optparse.SUPPRESS_HELP)
        self.add_option_group(optgrp)

    def install_display_options(self,
            debug_option=True,
            verbose_options=False,
            separator_option=False,
            dshbak_compat=False,
            msgtree_mode=False):
        """Install options needed by Display class"""
        optgrp = optparse.OptionGroup(self, "Output behaviour")
        if verbose_options:
            optgrp.add_option("-q", "--quiet", action="store_true",
                dest="quiet", help="be quiet, print essential output only")
            optgrp.add_option("-v", "--verbose", action="store_true",
                dest="verbose", help="be verbose, print informative messages")
        if debug_option:
            optgrp.add_option("-d", "--debug", action="store_true",
                dest="debug",
                help="output more messages for debugging purpose")
        optgrp.add_option("-G", "--groupbase", action="store_true",
            dest="groupbase", default=False,
            help="do not display group source prefix")
        optgrp.add_option("-L", action="store_true", dest="line_mode",
            help="disable header block and order output by nodes")
        optgrp.add_option("-N", action="store_false", dest="label",
            default=True, help="disable labeling of command line")
        if dshbak_compat:
            optgrp.add_option("-b", "-c", "--dshbak", action="store_true",
                dest="gather", help="gather nodes with same output")
        else:
            optgrp.add_option("-b", "--dshbak", action="store_true",
                dest="gather", help="gather nodes with same output")
        optgrp.add_option("-B", action="store_true", dest="gatherall",
            default=False, help="like -b but including standard error")
        optgrp.add_option("-r", "--regroup", action="store_true",
                          dest="regroup", default=False,
                          help="fold nodeset using node groups")

        if separator_option:
            optgrp.add_option("-S", "--separator", action="store",
                              dest="separator", default=':',
                              help="node / line content separator string " \
                              "(default: ':')")
        else:
            optgrp.add_option("-S", action="store_true", dest="maxrc",
                              help="return the largest of command return codes")

        if msgtree_mode:
            # clubak specific
            optgrp.add_option("-F", "--fast", action="store_true",
                              dest="fast_mode",
                              help="faster but memory hungry mode")
            optgrp.add_option("-T", "--tree", action="store_true",
                              dest="trace_mode",
                              help="message tree trace mode")
            optgrp.add_option("--interpret-keys", action="store",
                              dest="interpret_keys", choices=THREE_CHOICES,
                              default=THREE_CHOICES[-1], help="whether to " \
                              "interpret keys (never, always or auto)")

        optgrp.add_option("--color", action="store", dest="whencolor",
                          choices=THREE_CHOICES, help="whether to use ANSI " \
                          "colors (never, always or auto)")
        optgrp.add_option("--diff", action="store_true", dest="diff",
                          help="show diff between gathered outputs")
        self.add_option_group(optgrp)

    def _copy_callback(self, option, opt_str, value, parser):
        """special callback method for copy and rcopy toggles"""
        # enable interspersed args again
        self.enable_interspersed_args()
        # set True to dest option attribute
        setattr(parser.values, option.dest, True)

    def install_filecopy_options(self):
        """Install file copying specific options"""
        optgrp = optparse.OptionGroup(self, "File copying")
        optgrp.add_option("-c", "--copy", action="callback", dest="copy",
                          callback=self._copy_callback,
                          help="copy local file or directory to remote nodes")
        optgrp.add_option("--rcopy", action="callback", dest="rcopy",
                          callback=self._copy_callback,
                          help="copy file or directory from remote nodes")
        optgrp.add_option("--dest", action="store", dest="dest_path",
                          help="destination file or directory on the nodes")
        optgrp.add_option("-p", action="store_true", dest="preserve_flag",
                          help="preserve modification times and modes")
        self.add_option_group(optgrp)

    
    def install_ssh_options(self):
        """Install engine/connector (ssh) options"""
        optgrp = optparse.OptionGroup(self, "Ssh/Tree options")
        optgrp.add_option("-f", "--fanout", action="store", dest="fanout", 
                          help="use a specified fanout", type="int")
        #help="queueing delay for traffic grooming"
        optgrp.add_option("-Q", action="store", dest="grooming_delay", 
                          help=optparse.SUPPRESS_HELP, type="float")
        optgrp.add_option("-l", "--user", action="store", type="safestring",
                          dest="user", help="execute remote command as user")
        optgrp.add_option("-o", "--options", action="store", dest="options",
                          help="can be used to give ssh options")
        optgrp.add_option("-t", "--connect_timeout", action="store",
                          dest="connect_timeout", help="limit time to " \
                          "connect to a node" ,type="float")
        optgrp.add_option("-u", "--command_timeout", action="store",
                          dest="command_timeout", help="limit time for " \
                          "command to run on the node", type="float")
        self.add_option_group(optgrp)

    def install_nodeset_commands(self):
        """Install nodeset commands"""
        optgrp = optparse.OptionGroup(self, "Commands")
        optgrp.add_option("-c", "--count", action="store_true", dest="count", 
                          default=False, help="show number of nodes in " \
                          "nodeset(s)")
        optgrp.add_option("-e", "--expand", action="store_true",
                          dest="expand", default=False, help="expand " \
                          "nodeset(s) to separate nodes")
        optgrp.add_option("-f", "--fold", action="store_true", dest="fold", 
                          default=False, help="fold nodeset(s) (or " \
                          "separate nodes) into one nodeset")
        optgrp.add_option("-l", "--list", action="count", dest="list", 
                          default=False, help="list node groups (see -s " \
                          "GROUPSOURCE)")
        optgrp.add_option("-r", "--regroup", action="store_true",
                          dest="regroup", default=False, help="fold nodes " \
                          "using node groups (see -s GROUPSOURCE)")
        optgrp.add_option("--groupsources", action="store_true",
                          dest="groupsources", default=False, help="list " \
                          "all configured group sources (see groups.conf(5))")
        self.add_option_group(optgrp)

    def install_nodeset_operations(self):
        """Install nodeset operations"""
        optgrp = optparse.OptionGroup(self, "Operations")
        optgrp.add_option("-x", "--exclude", action="append", dest="sub_nodes",
                          default=[], type="string",
                          help="exclude specified nodeset")
        optgrp.add_option("-i", "--intersection", action="append",
                          dest="and_nodes", default=[], type="string",
                          help="calculate nodesets intersection")
        optgrp.add_option("-X", "--xor", action="append", dest="xor_nodes",
                          default=[], type="string", help="calculate " \
                          "symmetric difference between nodesets")
        self.add_option_group(optgrp)

    def install_nodeset_options(self):
        """Install nodeset options"""
        optgrp = optparse.OptionGroup(self, "Options")
        optgrp.add_option("-a", "--all", action="store_true", dest="all", 
                          help="call external node groups support to " \
                               "display all nodes")
        optgrp.add_option("--autostep", action="store", dest="autostep", 
                          help="auto step threshold number when folding " \
                               "nodesets", type="int")
        optgrp.add_option("-d", "--debug", action="store_true", dest="debug",
                          help="output more messages for debugging purpose")
        optgrp.add_option("-q", "--quiet", action="store_true", dest="quiet",
                          help="be quiet, print essential output only")
        optgrp.add_option("-R", "--rangeset", action="store_true",
                          dest="rangeset", help="switch to RangeSet instead " \
                          "of NodeSet. Useful when working on numerical " \
                          "cluster ranges, eg. 1,5,18-31")
        optgrp.add_option("-G", "--groupbase", action="store_true",
                          dest="groupbase", help="hide group source prefix " \
                          "(always \"@groupname\")")
        optgrp.add_option("-S", "--separator", action="store", dest="separator",
                          default=' ', help="separator string to use when " \
                          "expanding nodesets (default: ' ')")
        optgrp.add_option("-I", "--slice", action="store",
                          dest="slice_rangeset",
                          help="return sliced off result", type="string")
        optgrp.add_option("--split", action="store", dest="maxsplit", 
                          help="split result into a number of subsets",
                          type="int")
        optgrp.add_option("--contiguous", action="store_true",
                          dest="contiguous", help="split result into " \
                          "contiguous subsets")
        self.add_option_group(optgrp)



########NEW FILE########
__FILENAME__ = Utils
#!/usr/bin/env python
#
# Copyright CEA/DAM/DIF (2010)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
CLI utility functions
"""

import sys

# CLI modules might safely import the NodeSet class from here.
from ClusterShell.NodeUtils import GroupResolverConfigError
try:
    from ClusterShell.NodeSet import NodeSet
except GroupResolverConfigError, exc:
    print >> sys.stderr, \
        "ERROR: ClusterShell node groups configuration error:\n\t%s" % exc
    sys.exit(1)


def nodeset_cmp(ns1, ns2):
    """Compare 2 nodesets by their length (we want larger nodeset
    first) and then by first node."""
    len_cmp = cmp(len(ns2), len(ns1))
    if not len_cmp:
        smaller = NodeSet.fromlist([ns1[0], ns2[0]])[0]
        if smaller == ns1[0]:
            return -1
        else:
            return 1
    return len_cmp

def bufnodeset_cmp(bn1, bn2):
    """Convenience function to compare 2 (buf, nodeset) tuples by their
    nodeset length (we want larger nodeset first) and then by first
    node."""
    # Extract nodesets and call nodeset_cmp
    return nodeset_cmp(bn1[1], bn2[1])


########NEW FILE########
__FILENAME__ = Communication
#!/usr/bin/env python
#
# Copyright CEA/DAM/DIF (2010, 2011, 2012)
#  Contributor: Henri DOREAU <henri.doreau@cea.fr>
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and abiding
# by the rules of distribution of free software. You can use, modify and/ or
# redistribute the software under the terms of the CeCILL-C license as
# circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and rights to copy, modify
# and redistribute granted by the license, users are provided only with a
# limited warranty and the software's author, the holder of the economic rights,
# and the successive licensors have only limited liability.
#
# In this respect, the user's attention is drawn to the risks associated with
# loading, using, modifying and/or developing or reproducing the software by the
# user in light of its specific status of free software, that may mean that it
# is complicated to manipulate, and that also therefore means that it is
# reserved for developers and experienced professionals having in-depth computer
# knowledge. Users are therefore encouraged to load and test the software's
# suitability as regards their requirements in conditions enabling the security
# of their systems and/or data to be ensured and, more generally, to use and
# operate it in the same conditions as regards security.
#
# The fact that you are presently reading this means that you have had knowledge
# of the CeCILL-C license and that you accept its terms.

"""
ClusterShell inter-nodes communication module

This module contains the required material for nodes to communicate between each
others within the propagation tree. At the highest level, messages are instances
of several classes. They can be converted into XML to be sent over SSH links
through a Channel instance.

In the other side, XML is parsed and new message objects are instanciated.

Communication channels have been implemented as ClusterShell events handlers.
Whenever a message chunk is read, the data is given to a SAX XML parser, that
will use it to create corresponding messages instances as a messages factory.

As soon as an instance is ready, it is then passed to a recv() method in the
channel. The recv() method of the Channel class is a stub, that requires to be
implemented in subclass to process incoming messages. So is the start() method
too.

Subclassing the Channel class allows implementing whatever logic you want on the
top of a communication channel.
"""

import cPickle
import base64
import logging
import xml.sax

from xml.sax.handler import ContentHandler
from xml.sax.saxutils import XMLGenerator
from xml.sax import SAXParseException

from collections import deque
from cStringIO import StringIO

from ClusterShell.Event import EventHandler


class MessageProcessingError(Exception):
    """base exception raised when an error occurs while processing incoming or
    outgoing messages.
    """

class XMLReader(ContentHandler):
    """SAX handler for XML -> Messages instances conversion"""
    def __init__(self):
        """
        """
        ContentHandler.__init__(self)
        self.msg_queue = deque()
        # current packet under construction
        self._draft = None
        self._sections_map = None

    def startElement(self, name, attrs):
        """read a starting xml tag"""
        if name == 'channel':
            pass
        elif name == 'message':
            self._draft_new(attrs)
        elif self._draft is not None:
            self._draft_update(name, attrs)
        else:
            raise MessageProcessingError('Invalid starting tag %s' % name)

    def endElement(self, name):
        """read an ending xml tag"""
        # end of message
        if name == 'message':
            self.msg_queue.appendleft(self._draft)
            self._draft = None
        elif name == 'channel':
            self.msg_queue.append(EndMessage())

    def characters(self, content):
        """read content characters"""
        if self._draft is not None:
            content = content.decode('utf-8')
            if content != '':
                self._draft.data_update(content)

    def msg_available(self):
        """return whether a message is available for delivery or not"""
        return len(self.msg_queue) > 0

    def pop_msg(self):
        """pop and return the oldest message queued"""
        if len(self.msg_queue) > 0:
            return self.msg_queue.pop()

    def _draft_new(self, attributes):
        """start a new packet construction"""
        # associative array to select to correct constructor according to the
        # message type field contained in the serialized representation
        ctors_map = {
            ConfigurationMessage.ident: ConfigurationMessage,
            ControlMessage.ident: ControlMessage,
            ACKMessage.ident: ACKMessage,
            ErrorMessage.ident: ErrorMessage,
            StdOutMessage.ident: StdOutMessage,
            StdErrMessage.ident: StdErrMessage,
            RetcodeMessage.ident: RetcodeMessage,
            TimeoutMessage.ident: TimeoutMessage,
        }
        try:
            msg_type = attributes['type']
            # select the good constructor
            ctor = ctors_map[msg_type]
        except KeyError:
            raise MessageProcessingError('Unknown message type')
        self._draft = ctor()
        # obtain expected sections map for this type of messages
        self._draft_update('message', attributes)

    def _draft_update(self, name, attributes):
        """update the current message draft with a new section"""
        assert(self._draft is not None)
        
        if name == 'message':
            self._draft.selfbuild(attributes)
        else:
            raise MessageProcessingError('Invalid tag %s' % name)

class Channel(EventHandler):
    """Use this event handler to establish a communication channel between to
    hosts whithin the propagation tree.

    The endpoint's logic has to be implemented by subclassing the Channel class
    and overriding the start() and recv() methods.
    
    There is no default behavior for these methods apart raising a
    NotImplementedError.
    
    Usage:
      >> chan = MyChannel() # inherits Channel
      >> task = task_self()
      >> task.shell("uname -a", node="host2", handler=chan)
      >> task.resume()
    """
    def __init__(self):
        """
        """
        EventHandler.__init__(self)
        
        self.exit = False
        self.worker = None

        self._xml_reader = XMLReader()
        self._parser = xml.sax.make_parser(["IncrementalParser"])
        self._parser.setContentHandler(self._xml_reader)

        self.logger = logging.getLogger(__name__)

    def _open(self):
        """open a new communication channel from src to dst"""
        generator = XMLGenerator(self.worker, encoding='UTF-8')
        generator.startDocument()
        generator.startElement('channel', {})

    def _close(self):
        """close an already opened channel"""
        generator = XMLGenerator(self.worker)
        generator.endElement('channel')
        # XXX
        self.worker.write('\n')
        self.exit = True

    def ev_start(self, worker):
        """connection established. Open higher level channel"""
        self.worker = worker
        self.start()

    def ev_written(self, worker):
        if self.exit:
            self.logger.debug("aborting worker after last write")
            self.worker.abort()

    def ev_read(self, worker):
        """channel has data to read"""
        raw = worker.current_msg
        #self.logger.debug("ev_read raw=\'%s\'" % raw)
        try:
            self._parser.feed(raw + '\n')
        except SAXParseException, ex:
            raise MessageProcessingError( \
                'Invalid communication (%s): "%s"' % (ex.getMessage(), raw))

        # pass next message to the driver if ready
        if self._xml_reader.msg_available():
            msg = self._xml_reader.pop_msg()
            assert msg is not None
            self.recv(msg)

    def send(self, msg):
        """write an outgoing message as its XML representation"""
        #print '[DBG] send: %s' % str(msg)
        #self.logger.debug("SENDING to %s: \"%s\"" % (self.worker, msg.xml()))
        self.worker.write(msg.xml() + '\n')

    def start(self):
        """initialization logic"""
        raise NotImplementedError('Abstract method: subclasses must implement')
    
    def recv(self, msg):
        """callback: process incoming message"""
        raise NotImplementedError('Abstract method: subclasses must implement')

class Message(object):
    """base message class"""
    _inst_counter = 0
    ident = 'GEN'

    def __init__(self):
        """
        """
        self.attr = {'type': str, 'msgid': int}
        self.type = self.__class__.ident
        self.msgid = Message._inst_counter
        self.data = ''
        Message._inst_counter += 1

    def data_encode(self, inst):
        """serialize an instance and store the result"""
        self.data = base64.encodestring(cPickle.dumps(inst))

    def data_decode(self):
        """deserialize a previously encoded instance and return it"""
        return cPickle.loads(base64.decodestring(self.data))

    def data_update(self, raw):
        """append data to the instance (used for deserialization)"""
        # TODO : bufferize and use ''.join() for performance
        #self.logger.debug("data_update raw=%s" % raw)
        self.data += raw

    def selfbuild(self, attributes):
        """self construction from a table of attributes"""
        for k, fmt in self.attr.iteritems():
            try:
                setattr(self, k, fmt(attributes[k]))
            except KeyError:
                raise MessageProcessingError(
                    'Invalid "message" attributes: missing key "%s"' % k)

    def __str__(self):
        """printable representation"""
        elts = ['%s: %s' % (k, str(self.__dict__[k])) for k in self.attr.keys()]
        attributes = ', '.join(elts)
        return "Message %s (%s)" % (self.type, attributes)

    def xml(self):
        """generate XML version of a configuration message"""
        out = StringIO()
        generator = XMLGenerator(out)

        # "stringify" entries for XML conversion
        state = {}
        for k in self.attr:
            state[k] = str(getattr(self, k))

        generator.startElement('message', state)
        generator.characters(self.data)
        generator.endElement('message')
        xml_msg = out.getvalue()
        out.close()
        return xml_msg

class ConfigurationMessage(Message):
    """configuration propagation container"""
    ident = 'CFG'

class RoutedMessageBase(Message):
    """abstract class for routed message (with worker source id)"""
    def __init__(self, srcid):
        Message.__init__(self)
        self.attr.update({'srcid': int})
        self.srcid = srcid

class ControlMessage(RoutedMessageBase):
    """action request"""
    ident = 'CTL'

    def __init__(self, srcid=0):
        """
        """
        RoutedMessageBase.__init__(self, srcid)
        self.attr.update({'action': str, 'target': str})
        self.action = ''
        self.target = ''

class ACKMessage(Message):
    """acknowledgement message"""
    ident = 'ACK'

    def __init__(self, ackid=0):
        """
        """
        Message.__init__(self)
        self.attr.update({'ack': int})
        self.ack = ackid

    def data_update(self, raw):
        """override method to ensure that incoming ACK messages don't contain
        unexpected payloads
        """
        raise MessageProcessingError('ACK messages have no payload')

class ErrorMessage(Message):
    """error message"""
    ident = 'ERR'

    def __init__(self, err=''):
        """
        """
        Message.__init__(self)
        self.attr.update({'reason': str})
        self.reason = err

    def data_update(self, raw):
        """override method to ensure that incoming ACK messages don't contain
        unexpected payloads
        """
        raise MessageProcessingError('Error message have no payload')

class StdOutMessage(RoutedMessageBase):
    """container message for standard output"""
    ident = 'OUT'

    def __init__(self, nodes='', output='', srcid=0):
        """
        """
        RoutedMessageBase.__init__(self, srcid)
        self.attr.update({'nodes': str})
        self.nodes = nodes
        self.data = output

class StdErrMessage(StdOutMessage):
    ident = 'SER'

class RetcodeMessage(RoutedMessageBase):
    """container message for return code"""
    ident = 'RET'

    def __init__(self, nodes='', retcode=0, srcid=0):
        """
        """
        RoutedMessageBase.__init__(self, srcid)
        self.attr.update({'retcode': int, 'nodes': str})
        self.retcode = retcode
        self.nodes = nodes

    def data_update(self, raw):
        """override method to ensure that incoming ACK messages don't contain
        unexpected payloads
        """
        raise MessageProcessingError('Retcode message has no payload')

class TimeoutMessage(RoutedMessageBase):
    """container message for timeout notification"""
    ident = 'TIM'

    def __init__(self, nodes='', srcid=0):
        """
        """
        RoutedMessageBase.__init__(self, srcid)
        self.attr.update({'nodes': str})
        self.nodes = nodes

class EndMessage(Message):
    """end of channel message"""
    ident = 'END'


########NEW FILE########
__FILENAME__ = Engine
#
# Copyright CEA/DAM/DIF (2007, 2008, 2009, 2010, 2011)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
Interface of underlying Task's Engine.

An Engine implements a loop your thread enters and uses to call event handlers
in response to incoming events (from workers, timers, etc.).
"""

import errno
import heapq
import logging
import time

# Define epsilon value for time float arithmetic operations
EPSILON = 1.0e-3

class EngineException(Exception):
    """
    Base engine exception.
    """

class EngineAbortException(EngineException):
    """
    Raised on user abort.
    """
    def __init__(self, kill):
        EngineException.__init__(self)
        self.kill = kill

class EngineTimeoutException(EngineException):
    """
    Raised when a timeout is encountered.
    """

class EngineIllegalOperationError(EngineException):
    """
    Error raised when an illegal operation has been performed.
    """

class EngineAlreadyRunningError(EngineIllegalOperationError):
    """
    Error raised when the engine is already running.
    """

class EngineNotSupportedError(EngineException):
    """
    Error raised when the engine mechanism is not supported.
    """
    def __init__(self, engineid):
        EngineException.__init__(self)
        self.engineid = engineid


class EngineBaseTimer:
    """
    Abstract class for ClusterShell's engine timer. Such a timer
    requires a relative fire time (delay) in seconds (as float), and
    supports an optional repeating interval in seconds (as float too).

    See EngineTimer for more information about ClusterShell timers.
    """

    def __init__(self, fire_delay, interval=-1.0, autoclose=False):
        """
        Create a base timer.
        """
        self.fire_delay = fire_delay
        self.interval = interval
        self.autoclose = autoclose
        self._engine = None
        self._timercase = None

    def _set_engine(self, engine):
        """
        Bind to engine, called by Engine.
        """
        if self._engine:
            # A timer can be registered to only one engine at a time.
            raise EngineIllegalOperationError("Already bound to engine.")

        self._engine = engine

    def invalidate(self):
        """
        Invalidates a timer object, stopping it from ever firing again.
        """
        if self._engine:
            self._engine.timerq.invalidate(self)
            self._engine = None

    def is_valid(self):
        """
        Returns a boolean value that indicates whether an EngineTimer
        object is valid and able to fire.
        """
        return self._engine != None

    def set_nextfire(self, fire_delay, interval=-1):
        """
        Set the next firing delay in seconds for an EngineTimer object.

        The optional paramater `interval' sets the firing interval
        of the timer. If not specified, the timer fires once and then
        is automatically invalidated.

        Time values are expressed in second using floating point
        values. Precision is implementation (and system) dependent.

        It is safe to call this method from the task owning this
        timer object, in any event handlers, anywhere.

        However, resetting a timer's next firing time may be a
        relatively expensive operation. It is more efficient to let
        timers autorepeat or to use this method from the timer's own
        event handler callback (ie. from its ev_timer).
        """
        if not self.is_valid():
            raise EngineIllegalOperationError("Operation on invalid timer.")

        self.fire_delay = fire_delay
        self.interval = interval
        self._engine.timerq.reschedule(self)

    def _fire(self):
        raise NotImplementedError("Derived classes must implement.")


class EngineTimer(EngineBaseTimer):
    """
    Concrete class EngineTimer

    An EngineTimer object represents a timer bound to an engine that
    fires at a preset time in the future. Timers can fire either only
    once or repeatedly at fixed time intervals. Repeating timers can
    also have their next firing time manually adjusted.

    A timer is not a real-time mechanism; it fires when the task's
    underlying engine to which the timer has been added is running and
    able to check if the timer's firing time has passed.
    """

    def __init__(self, fire_delay, interval, autoclose, handler):
        EngineBaseTimer.__init__(self, fire_delay, interval, autoclose)
        self.eh = handler
        assert self.eh != None, "An event handler is needed for timer."

    def _fire(self):
        self.eh.ev_timer(self)

class _EngineTimerQ:

    class _EngineTimerCase:
        """
        Helper class that allows comparisons of fire times, to be easily used
        in an heapq.
        """
        def __init__(self, client):
            self.client = client
            self.client._timercase = self
            # arm timer (first time)
            assert self.client.fire_delay > -EPSILON
            self.fire_date = self.client.fire_delay + time.time()

        def __cmp__(self, other):
            return cmp(self.fire_date, other.fire_date)

        def arm(self, client):
            assert client != None
            self.client = client
            self.client._timercase = self
            # setup next firing date
            time_current = time.time()
            if self.client.fire_delay > -EPSILON:
                self.fire_date = self.client.fire_delay + time_current
            else:
                interval = float(self.client.interval)
                assert interval > 0
                self.fire_date += interval
                # If the firing time is delayed so far that it passes one
                # or more of the scheduled firing times, reschedule the
                # timer for the next scheduled firing time in the future.
                while self.fire_date < time_current:
                    self.fire_date += interval

        def disarm(self):
            client = self.client
            client._timercase = None
            self.client = None
            return client

        def armed(self):
            return self.client != None
            

    def __init__(self, engine):
        """
        Initializer.
        """
        self._engine = engine
        self.timers = []
        self.armed_count = 0

    def __len__(self):
        """
        Return the number of active timers.
        """
        return self.armed_count

    def schedule(self, client):
        """
        Insert and arm a client's timer.
        """
        # arm only if fire is set
        if client.fire_delay > -EPSILON:
            heapq.heappush(self.timers, _EngineTimerQ._EngineTimerCase(client))
            self.armed_count += 1
            if not client.autoclose:
                self._engine.evlooprefcnt += 1

    def reschedule(self, client):
        """
        Re-insert client's timer.
        """
        if client._timercase:
            self.invalidate(client)
            self._dequeue_disarmed()
            self.schedule(client)

    def invalidate(self, client):
        """
        Invalidate client's timer. Current implementation doesn't really remove
        the timer, but simply flags it as disarmed.
        """
        if not client._timercase:
            # if timer is being fire, invalidate its values
            client.fire_delay = -1.0
            client.interval = -1.0
            return

        if self.armed_count <= 0:
            raise ValueError, "Engine client timer not found in timer queue"

        client._timercase.disarm()
        self.armed_count -= 1
        if not client.autoclose:
            self._engine.evlooprefcnt -= 1

    def _dequeue_disarmed(self):
        """
        Dequeue disarmed timers (sort of garbage collection).
        """
        while len(self.timers) > 0 and not self.timers[0].armed():
            heapq.heappop(self.timers)

    def fire(self):
        """
        Remove the smallest timer from the queue and fire its associated client.
        Raise IndexError if the queue is empty.
        """
        self._dequeue_disarmed()

        timercase = heapq.heappop(self.timers)
        client = timercase.disarm()
        
        client.fire_delay = -1.0
        client._fire()

        # Note: fire=0 is valid, interval=0 is not
        if client.fire_delay >= -EPSILON or client.interval > EPSILON:
            timercase.arm(client)
            heapq.heappush(self.timers, timercase)
        else:
            self.armed_count -= 1
            if not client.autoclose:
                self._engine.evlooprefcnt -= 1

    def nextfire_delay(self):
        """
        Return next timer fire delay (relative time).
        """
        self._dequeue_disarmed()
        if len(self.timers) > 0:
            return max(0., self.timers[0].fire_date - time.time())

        return -1

    def expired(self):
        """
        Has a timer expired?
        """
        self._dequeue_disarmed()
        return len(self.timers) > 0 and \
            (self.timers[0].fire_date - time.time()) <= EPSILON

    def clear(self):
        """
        Stop and clear all timers.
        """
        for timer in self.timers:
            if timer.armed():
                timer.client.invalidate()

        self.timers = []
        self.armed_count = 0


class Engine:
    """
    Interface for ClusterShell engine. Subclasses have to implement a runloop
    listening for client events.
    """

    # Engine client I/O event interest bits
    E_READ = 0x1
    E_ERROR = 0x2
    E_WRITE = 0x4
    E_ANY = E_READ | E_ERROR | E_WRITE

    identifier = "(none)"

    def __init__(self, info):
        """
        Initialize base class.
        """
        # take a reference on info dict
        self.info = info

        # and update engine id
        self.info['engine'] = self.identifier

        # keep track of all clients
        self._clients = set()
        self._ports = set()

        # keep track of the number of registered clients (delayable only)
        self.reg_clients = 0

        # keep track of registered file descriptors in a dict where keys
        # are fileno and values are clients
        self.reg_clifds = {}

        # Current loop iteration counter. It is the number of performed engine
        # loops in order to keep track of client registration epoch, so we can
        # safely process FDs by chunk and re-use FDs (see Engine._fd2client).
        self._current_loopcnt = 0

        # Current client being processed
        self._current_client = None

        # timer queue to handle both timers and clients timeout
        self.timerq = _EngineTimerQ(self)

        # reference count to the event loop (must include registered
        # clients and timers configured WITHOUT autoclose)
        self.evlooprefcnt = 0

        # running state
        self.running = False
        # runloop-has-exited flag
        self._exited = False

    def release(self):
        """Release engine-specific resources."""
        pass

    def clients(self):
        """
        Get a copy of clients set.
        """
        return self._clients.copy()

    def ports(self):
        """
        Get a copy of ports set.
        """
        return self._ports.copy()

    def _fd2client(self, fd):
        client, fdev = self.reg_clifds.get(fd, (None, None))
        if client:
            if client._reg_epoch < self._current_loopcnt:
                return client, fdev
            else:
                self._debug("ENGINE _fd2client: ignoring just re-used FD %d" \
                            % fd)
        return (None, None)

    def add(self, client):
        """
        Add a client to engine. Subclasses that override this method
        should call base class method.
        """
        # bind to engine
        client._set_engine(self)

        if client.delayable:
            # add to regular client set
            self._clients.add(client)
        else:
            # add to port set (non-delayable)
            self._ports.add(client)

        if self.running:
            # in-fly add if running
            if not client.delayable:
                self.register(client)
            elif self.info["fanout"] > self.reg_clients:
                self.register(client._start())

    def _remove(self, client, abort, did_timeout=False, force=False):
        """
        Remove a client from engine (subroutine).
        """
        # be careful to also remove ports when engine has not started yet
        if client.registered or not client.delayable:
            if client.registered:
                self.unregister(client)
            # care should be taken to ensure correct closing flags
            client._close(abort=abort, flush=not force, timeout=did_timeout)

    def remove(self, client, abort=False, did_timeout=False):
        """
        Remove a client from engine. Subclasses that override this
        method should call base class method.
        """
        self._debug("REMOVE %s" % client)
        if client.delayable:
            self._clients.remove(client)
        else:
            self._ports.remove(client)
        self._remove(client, abort, did_timeout)
        self.start_all()
    
    def clear(self, did_timeout=False, clear_ports=False):
        """
        Remove all clients. Subclasses that override this method should
        call base class method.
        """
        all_clients = [self._clients]
        if clear_ports:
            all_clients.append(self._ports)

        for clients in all_clients:
            while len(clients) > 0:
                client = clients.pop()
                self._remove(client, True, did_timeout, force=True)

    def register(self, client):
        """
        Register an engine client. Subclasses that override this method
        should call base class method.
        """
        assert client in self._clients or client in self._ports
        assert not client.registered

        efd = client.fd_error
        rfd = client.fd_reader
        wfd = client.fd_writer
        assert rfd is not None or wfd is not None

        self._debug("REG %s(e%s,r%s,w%s)(autoclose=%s)" % \
                (client.__class__.__name__, efd, rfd, wfd,
                    client.autoclose))

        client._events = 0
        client.registered = True
        client._reg_epoch = self._current_loopcnt

        if client.delayable:
            self.reg_clients += 1

        if client.autoclose:
            refcnt_inc = 0
        else:
            refcnt_inc = 1

        if efd != None:
            self.reg_clifds[efd] = client, Engine.E_ERROR
            client._events |= Engine.E_ERROR
            self.evlooprefcnt += refcnt_inc
            self._register_specific(efd, Engine.E_ERROR)
        if rfd != None:
            self.reg_clifds[rfd] = client, Engine.E_READ
            client._events |= Engine.E_READ
            self.evlooprefcnt += refcnt_inc
            self._register_specific(rfd, Engine.E_READ)
        if wfd != None:
            self.reg_clifds[wfd] = client, Engine.E_WRITE
            client._events |= Engine.E_WRITE
            self.evlooprefcnt += refcnt_inc
            self._register_specific(wfd, Engine.E_WRITE)

        client._new_events = client._events

        # start timeout timer
        self.timerq.schedule(client)

    def unregister_writer(self, client):
        self._debug("UNREG WRITER r%s,w%s" % (client.reader_fileno(), \
            client.writer_fileno()))
        if client.autoclose:
            refcnt_inc = 0
        else:
            refcnt_inc = 1

        wfd = client.fd_writer
        if wfd != None:
            self._unregister_specific(wfd, client._events & Engine.E_WRITE)
            client._events &= ~Engine.E_WRITE
            del self.reg_clifds[wfd]
            self.evlooprefcnt -= refcnt_inc

    def unregister(self, client):
        """
        Unregister a client. Subclasses that override this method should
        call base class method.
        """
        # sanity check
        assert client.registered
        self._debug("UNREG %s (r%s,e%s,w%s)" % (client.__class__.__name__,
            client.reader_fileno(), client.error_fileno(),
            client.writer_fileno()))
        
        # remove timeout timer
        self.timerq.invalidate(client)
        
        if client.autoclose:
            refcnt_inc = 0
        else:
            refcnt_inc = 1
            
        # clear interest events
        efd = client.fd_error
        if efd is not None:
            self._unregister_specific(efd, client._events & Engine.E_ERROR)
            client._events &= ~Engine.E_ERROR
            del self.reg_clifds[efd]
            self.evlooprefcnt -= refcnt_inc

        rfd = client.fd_reader
        if rfd is not None:
            self._unregister_specific(rfd, client._events & Engine.E_READ)
            client._events &= ~Engine.E_READ
            del self.reg_clifds[rfd]
            self.evlooprefcnt -= refcnt_inc

        wfd = client.fd_writer
        if wfd is not None:
            self._unregister_specific(wfd, client._events & Engine.E_WRITE)
            client._events &= ~Engine.E_WRITE
            del self.reg_clifds[wfd]
            self.evlooprefcnt -= refcnt_inc

        client._new_events = 0
        client.registered = False
        if client.delayable:
            self.reg_clients -= 1

    def modify(self, client, setmask, clearmask):
        """
        Modify the next loop interest events bitset for a client.
        """
        self._debug("MODEV set:0x%x clear:0x%x %s" % (setmask, clearmask,
                                                      client))
        client._new_events &= ~clearmask
        client._new_events |= setmask

        if self._current_client is not client:
            # modifying a non processing client, apply new_events now
            self.set_events(client, client._new_events)

    def _register_specific(self, fd, event):
        """Engine-specific register fd for event method."""
        raise NotImplementedError("Derived classes must implement.")

    def _unregister_specific(self, fd, ev_is_set):
        """Engine-specific unregister fd method."""
        raise NotImplementedError("Derived classes must implement.")

    def _modify_specific(self, fd, event, setvalue):
        """Engine-specific modify fd for event method."""
        raise NotImplementedError("Derived classes must implement.")
        
    def set_events(self, client, new_events):
        """
        Set the active interest events bitset for a client.
        """
        self._debug("SETEV new_events:0x%x events:0x%x %s" % (new_events,
            client._events, client))

        if not client.registered:
            logging.getLogger(__name__).debug( \
                "set_events: client %s not registered" % self)
            return

        chgbits = new_events ^ client._events
        if chgbits == 0:
            return

        # configure interest events as appropriate
        efd = client.fd_error
        if efd is not None:
            if chgbits & Engine.E_ERROR:
                status = new_events & Engine.E_ERROR
                self._modify_specific(efd, Engine.E_ERROR, status)
                if status:
                    client._events |= Engine.E_ERROR
                else:
                    client._events &= ~Engine.E_ERROR

        rfd = client.fd_reader
        if rfd is not None:
            if chgbits & Engine.E_READ:
                status = new_events & Engine.E_READ
                self._modify_specific(rfd, Engine.E_READ, status)
                if status:
                    client._events |= Engine.E_READ
                else:
                    client._events &= ~Engine.E_READ

        wfd = client.fd_writer
        if wfd is not None:
            if chgbits & Engine.E_WRITE:
                status = new_events & Engine.E_WRITE
                self._modify_specific(wfd, Engine.E_WRITE, status)
                if status:
                    client._events |= Engine.E_WRITE
                else:
                    client._events &= ~Engine.E_WRITE

        client._new_events = client._events

    def set_reading(self, client):
        """
        Set client reading state.
        """
        # listen for readable events
        self.modify(client, Engine.E_READ, 0)

    def set_reading_error(self, client):
        """
        Set client reading error state.
        """
        # listen for readable events
        self.modify(client, Engine.E_ERROR, 0)

    def set_writing(self, client):
        """
        Set client writing state.
        """
        # listen for writable events
        self.modify(client, Engine.E_WRITE, 0)

    def add_timer(self, timer):
        """
        Add engine timer.
        """
        timer._set_engine(self)
        self.timerq.schedule(timer)

    def remove_timer(self, timer):
        """
        Remove engine timer.
        """
        self.timerq.invalidate(timer)

    def fire_timers(self):
        """
        Fire expired timers for processing.
        """
        while self.timerq.expired():
            self.timerq.fire()

    def start_ports(self):
        """
        Start and register all port clients.
        """
        # Ports are special, non-delayable engine clients
        for port in self._ports:
            if not port.registered:
                self._debug("START PORT %s" % port)
                self.register(port)

    def start_all(self):
        """
        Start and register all other possible clients, in respect of task fanout.
        """
        # Get current fanout value
        fanout = self.info["fanout"]
        assert fanout > 0
        if fanout <= self.reg_clients:
            return

        # Register regular engine clients within the fanout limit
        for client in self._clients:
            if not client.registered:
                self._debug("START CLIENT %s" % client.__class__.__name__)
                self.register(client._start())
                if fanout <= self.reg_clients:
                    break
    
    def run(self, timeout):
        """
        Run engine in calling thread.
        """
        # change to running state
        if self.running:
            raise EngineAlreadyRunningError()
        self.running = True

        # start port clients
        self.start_ports()

        # peek in ports for early pending messages
        self.snoop_ports()

        # start all other clients
        self.start_all()

        # note: try-except-finally not supported before python 2.5
        try:
            try:
                self.runloop(timeout)
            except Exception, e:
                # any exceptions invalidate clients
                self.clear(isinstance(e, EngineTimeoutException))
                raise
            except: # could later use BaseException above (py2.5+)
                self.clear()
                raise
        finally:
            # cleanup
            self.timerq.clear()
            self.running = False

    def snoop_ports(self):
        """
        Peek in ports for possible early pending messages.
        This method simply tries to read port pipes in non-
        blocking mode.
        """
        # make a copy so that early messages on installed ports may
        # lead to new ports
        ports = self._ports.copy()
        for port in ports:
            try:
                port._handle_read()
            except (IOError, OSError), (err, strerr):
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    # no pending message
                    return
                # raise any other error
                raise

    def runloop(self, timeout):
        """
        Engine specific run loop. Derived classes must implement.
        """
        raise NotImplementedError("Derived classes must implement.")

    def abort(self, kill):
        """
        Abort runloop.
        """
        if self.running:
            raise EngineAbortException(kill)

        self.clear(clear_ports=kill)

    def exited(self):
        """
        Returns True if the engine has exited the runloop once.
        """
        return not self.running and self._exited

    def _debug(self, s):
        # library engine debugging hook
        #import sys
        #print >>sys.stderr, s
        pass


########NEW FILE########
__FILENAME__ = EPoll
#
# Copyright CEA/DAM/DIF (2009-2014)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
A ClusterShell Engine using epoll, an I/O event notification facility.

The epoll event distribution interface is available on Linux 2.6, and
has been included in Python 2.6.
"""

import errno
import select
import time

from ClusterShell.Engine.Engine import Engine
from ClusterShell.Engine.Engine import EngineNotSupportedError
from ClusterShell.Engine.Engine import EngineTimeoutException
from ClusterShell.Worker.EngineClient import EngineClientEOF


class EngineEPoll(Engine):
    """
    EPoll Engine

    ClusterShell Engine class using the select.epoll mechanism.
    """

    identifier = "epoll"

    def __init__(self, info):
        """
        Initialize Engine.
        """
        Engine.__init__(self, info)
        try:
            # get an epoll object
            self.epolling = select.epoll()
        except AttributeError:
            raise EngineNotSupportedError(EngineEPoll.identifier)

    def release(self):
        """Release engine-specific resources."""
        self.epolling.close()

    def _register_specific(self, fd, event):
        """
        Engine-specific fd registering. Called by Engine register.
        """
        eventmask = 0
        if event & (Engine.E_READ | Engine.E_ERROR):
            eventmask = select.EPOLLIN
        elif event == Engine.E_WRITE:
            eventmask = select.EPOLLOUT

        self.epolling.register(fd, eventmask)

    def _unregister_specific(self, fd, ev_is_set):
        """
        Engine-specific fd unregistering. Called by Engine unregister.
        """
        self._debug("UNREGSPEC fd=%d ev_is_set=%x"% (fd, ev_is_set))
        if ev_is_set:
            self.epolling.unregister(fd)

    def _modify_specific(self, fd, event, setvalue):
        """
        Engine-specific modifications after a interesting event change for
        a file descriptor. Called automatically by Engine set_events().
        For the epoll engine, it modifies the event mask associated to a file
        descriptor.
        """
        self._debug("MODSPEC fd=%d event=%x setvalue=%d" % (fd, event,
                                                            setvalue))
        if setvalue:
            eventmask = 0
            if event & (Engine.E_READ | Engine.E_ERROR):
                eventmask = select.EPOLLIN
            elif event == Engine.E_WRITE:
                eventmask = select.EPOLLOUT

            self.epolling.register(fd, eventmask)
        else:
            self.epolling.unregister(fd)

    def runloop(self, timeout):
        """
        Run epoll main loop.
        """
        if not timeout:
            timeout = -1

        start_time = time.time()

        # run main event loop...
        while self.evlooprefcnt > 0:
            self._debug("LOOP evlooprefcnt=%d (reg_clifds=%s) (timers=%d)" % \
                    (self.evlooprefcnt, self.reg_clifds.keys(),
                     len(self.timerq)))
            try:
                timeo = self.timerq.nextfire_delay()
                if timeout > 0 and timeo >= timeout:
                    # task timeout may invalidate clients timeout
                    self.timerq.clear()
                    timeo = timeout
                elif timeo == -1:
                    timeo = timeout

                self._current_loopcnt += 1
                evlist = self.epolling.poll(timeo + 0.001)

            except IOError, ex:
                # might get interrupted by a signal
                if ex.errno == errno.EINTR:
                    continue

            for fd, event in evlist:

                # get client instance
                client, fdev = self._fd2client(fd)
                if client is None:
                    continue

                # set as current processed client
                self._current_client = client

                # check for poll error condition of some sort
                if event & select.EPOLLERR:
                    self._debug("EPOLLERR %s" % client)
                    client._close_writer()
                    self._current_client = None
                    continue

                # check for data to read
                if event & select.EPOLLIN:
                    #self._debug("EPOLLIN fd=%d %s" % (fd, client))
                    assert fdev & (Engine.E_READ | Engine.E_ERROR)
                    assert client._events & fdev
                    self.modify(client, 0, fdev)
                    try:
                        if fdev & Engine.E_READ:
                            client._handle_read()
                        else:
                            client._handle_error()
                    except EngineClientEOF:
                        self._debug("EngineClientEOF %s" % client)
                        if fdev & Engine.E_READ:
                            self.remove(client)
                        self._current_client = None
                        continue

                # or check for end of stream (do not handle both at the same
                # time because handle_read() may perform a partial read)
                elif event & select.EPOLLHUP:
                    self._debug("EPOLLHUP fd=%d %s (r%s,e%s,w%s)" % (fd,
                        client.__class__.__name__, client.fd_reader,
                        client.fd_error, client.fd_writer))
                    if fdev & Engine.E_READ:
                        if client._events & Engine.E_ERROR:
                            self.modify(client, 0, fdev)
                        else:
                            self.remove(client)
                    else:
                        if client._events & Engine.E_READ:
                            self.modify(client, 0, fdev)
                        else:
                            self.remove(client)

                # check for writing
                if event & select.EPOLLOUT:
                    self._debug("EPOLLOUT fd=%d %s (r%s,e%s,w%s)" % (fd,
                        client.__class__.__name__, client.fd_reader,
                        client.fd_error, client.fd_writer))
                    assert fdev == Engine.E_WRITE
                    assert client._events & fdev
                    self.modify(client, 0, fdev)
                    client._handle_write()

                self._current_client = None

                # apply any changes occured during processing
                if client.registered:
                    self.set_events(client, client._new_events)

            # check for task runloop timeout
            if timeout > 0 and time.time() >= start_time + timeout:
                raise EngineTimeoutException()

            # process clients timeout
            self.fire_timers()

        self._debug("LOOP EXIT evlooprefcnt=%d (reg_clifds=%s) (timers=%d)" % \
                (self.evlooprefcnt, self.reg_clifds, len(self.timerq)))


########NEW FILE########
__FILENAME__ = Factory
#
# Copyright CEA/DAM/DIF (2009-2014)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
Engine Factory to select the best working event engine for the current
version of Python and Operating System.
"""

import sys

from ClusterShell.Engine.Engine import EngineNotSupportedError

# Available event engines
from ClusterShell.Engine.EPoll import EngineEPoll
from ClusterShell.Engine.Poll import EnginePoll
from ClusterShell.Engine.Select import EngineSelect

class PreferredEngine(object):
    """
    Preferred Engine selection metaclass (DP Abstract Factory).
    """

    engines = { EngineEPoll.identifier: EngineEPoll,
                EnginePoll.identifier: EnginePoll,
                EngineSelect.identifier: EngineSelect }

    def __new__(cls, hint, info):
        """
        Create a new preferred Engine.
        """
        if not hint or hint == 'auto':
            # in order or preference
            for engine_class in [ EngineEPoll, EnginePoll, EngineSelect ]:
                try:
                    return engine_class(info)
                except EngineNotSupportedError:
                    pass
            raise RuntimeError("FATAL: No supported ClusterShell.Engine found")
        else:
            # User overriding engine selection
            engines = cls.engines.copy()
            try:
                tryengine = engines.pop(hint)
                while True:
                    try:
                        return tryengine(info)
                    except EngineNotSupportedError:
                        if len(engines) == 0:
                            raise
                    tryengine = engines.popitem()[1]
            except KeyError, exc:
                print >> sys.stderr, "Invalid engine identifier", exc
                raise

########NEW FILE########
__FILENAME__ = Poll
#
# Copyright CEA/DAM/DIF (2007, 2008, 2009, 2010, 2011)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
A poll() based ClusterShell Engine.

The poll() system call is available on Linux and BSD.
"""

import errno
import os
import select
import sys
import time

from ClusterShell.Engine.Engine import Engine
from ClusterShell.Engine.Engine import EngineException
from ClusterShell.Engine.Engine import EngineNotSupportedError
from ClusterShell.Engine.Engine import EngineTimeoutException
from ClusterShell.Worker.EngineClient import EngineClientEOF


class EnginePoll(Engine):
    """
    Poll Engine

    ClusterShell engine using the select.poll mechanism (Linux poll()
    syscall).
    """

    identifier = "poll"

    def __init__(self, info):
        """
        Initialize Engine.
        """
        Engine.__init__(self, info)
        try:
            # get a polling object
            self.polling = select.poll()
        except AttributeError:
            raise EngineNotSupportedError(EnginePoll.identifier)

    def _register_specific(self, fd, event):
        if event & (Engine.E_READ | Engine.E_ERROR):
            eventmask = select.POLLIN
        elif event == Engine.E_WRITE:
            eventmask = select.POLLOUT

        self.polling.register(fd, eventmask)

    def _unregister_specific(self, fd, ev_is_set):
        if ev_is_set:
            self.polling.unregister(fd)

    def _modify_specific(self, fd, event, setvalue):
        """
        Engine-specific modifications after a interesting event change for
        a file descriptor. Called automatically by Engine register/unregister and
        set_events().  For the poll() engine, it reg/unreg or modifies the event mask
        associated to a file descriptor.
        """
        self._debug("MODSPEC fd=%d event=%x setvalue=%d" % (fd, event,
                                                            setvalue))
        if setvalue:
            eventmask = 0
            if event & (Engine.E_READ | Engine.E_ERROR):
                eventmask = select.POLLIN
            elif event == Engine.E_WRITE:
                eventmask = select.POLLOUT
            self.polling.register(fd, eventmask)
        else:
            self.polling.unregister(fd)

    def runloop(self, timeout):
        """
        Poll engine run(): start clients and properly get replies
        """
        if not timeout:
            timeout = -1

        start_time = time.time()

        # run main event loop...
        while self.evlooprefcnt > 0:
            self._debug("LOOP evlooprefcnt=%d (reg_clifds=%s) (timers=%d)" \
                % (self.evlooprefcnt, self.reg_clifds.keys(), \
                   len(self.timerq)))
            try:
                timeo = self.timerq.nextfire_delay()
                if timeout > 0 and timeo >= timeout:
                    # task timeout may invalidate clients timeout
                    self.timerq.clear()
                    timeo = timeout
                elif timeo == -1:
                    timeo = timeout

                self._current_loopcnt += 1
                evlist = self.polling.poll(timeo * 1000.0 + 1.0)

            except select.error, (ex_errno, ex_strerror):
                # might get interrupted by a signal
                if ex_errno == errno.EINTR:
                    continue
                elif ex_errno == errno.EINVAL:
                    print >> sys.stderr, \
                            "EnginePoll: please increase RLIMIT_NOFILE"
                raise

            for fd, event in evlist:

                if event & select.POLLNVAL:
                    raise EngineException("Caught POLLNVAL on fd %d" % fd)

                # get client instance
                client, fdev = self._fd2client(fd)
                if client is None:
                    continue

                # process this client
                self._current_client = client

                # check for poll error condition of some sort
                if event & select.POLLERR:
                    self._debug("POLLERR %s" % client)
                    self.unregister_writer(client)
                    os.close(client.fd_writer)
                    client.fd_writer = None
                    self._current_client = None
                    continue

                # check for data to read
                if event & select.POLLIN:
                    assert fdev & (Engine.E_READ | Engine.E_ERROR)
                    assert client._events & fdev
                    self.modify(client, 0, fdev)
                    try:
                        if fdev & Engine.E_READ:
                            client._handle_read()
                        else:
                            client._handle_error()
                    except EngineClientEOF:
                        self._debug("EngineClientEOF %s" % client)
                        if fdev & Engine.E_READ:
                            self.remove(client)
                        self._current_client = None
                        continue

                # or check for end of stream (do not handle both at the same
                # time because handle_read() may perform a partial read)
                elif event & select.POLLHUP:
                    self._debug("POLLHUP fd=%d %s (r%s,e%s,w%s)" % (fd,
                        client.__class__.__name__, client.fd_reader,
                        client.fd_error, client.fd_writer))		
                    if fdev & Engine.E_READ:
                        if client._events & Engine.E_ERROR:
                            self.modify(client, 0, fdev)
                        else:
                            self.remove(client)
                    else:
                        if client._events & Engine.E_READ:
                            self.modify(client, 0, fdev)
                        else:
                            self.remove(client)

                # check for writing
                if event & select.POLLOUT:
                    self._debug("POLLOUT fd=%d %s (r%s,e%s,w%s)" % (fd,
                        client.__class__.__name__, client.fd_reader,
                        client.fd_error, client.fd_writer))
                    assert fdev == Engine.E_WRITE
                    assert client._events & fdev
                    self.modify(client, 0, fdev)
                    client._handle_write()

                self._current_client = None

                # apply any changes occured during processing
                if client.registered:
                    self.set_events(client, client._new_events)

            # check for task runloop timeout
            if timeout > 0 and time.time() >= start_time + timeout:
                raise EngineTimeoutException()

            # process clients timeout
            self.fire_timers()

        self._debug("LOOP EXIT evlooprefcnt=%d (reg_clifds=%s) (timers=%d)" % \
                (self.evlooprefcnt, self.reg_clifds, len(self.timerq)))


########NEW FILE########
__FILENAME__ = Select
#
# Copyright CEA/DAM/DIF (2009, 2010, 2011)
#  Contributors:
#   Henri DOREAU <henri.doreau@cea.fr>
#   Aurelien DEGREMONT <aurelien.degremont@cea.fr>
#   Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
A select() based ClusterShell Engine.

The select() system call is available on almost every UNIX-like systems.
"""

import errno
import select
import sys
import time

from ClusterShell.Engine.Engine import Engine
from ClusterShell.Engine.Engine import EngineTimeoutException
from ClusterShell.Worker.EngineClient import EngineClientEOF


class EngineSelect(Engine):
    """
    Select Engine

    ClusterShell engine using the select.select mechanism
    """

    identifier = "select"

    def __init__(self, info):
        """
        Initialize Engine.
        """
        Engine.__init__(self, info)
        self._fds_r = []
        self._fds_w = []

    def _register_specific(self, fd, event):
        """
        Engine-specific fd registering. Called by Engine register.
        """
        if event & (Engine.E_READ | Engine.E_ERROR):
            self._fds_r.append(fd)
        elif event & Engine.E_WRITE:
            self._fds_w.append(fd)

    def _unregister_specific(self, fd, ev_is_set):
        """
        Engine-specific fd unregistering. Called by Engine unregister.
        """
        if ev_is_set or True:
            if fd in self._fds_r:
                self._fds_r.remove(fd)
            if fd in self._fds_w:
                self._fds_w.remove(fd)

    def _modify_specific(self, fd, event, setvalue):
        """
        Engine-specific modifications after a interesting event change
        for a file descriptor. Called automatically by Engine
        register/unregister and set_events(). For the select() engine,
        it appends/remove the fd to/from the concerned fd_sets.
        """
        self._debug("MODSPEC fd=%d event=%x setvalue=%d" % (fd, event,
                                                            setvalue))
        if setvalue:
            self._register_specific(fd, event)
        else:
            self._unregister_specific(fd, True)

    def runloop(self, timeout):
        """
        Select engine run(): start clients and properly get replies
        """
        if not timeout:
            timeout = -1

        start_time = time.time()

        # run main event loop...
        while self.evlooprefcnt > 0:
            self._debug("LOOP evlooprefcnt=%d (reg_clifds=%s) (timers=%d)" % 
                (self.evlooprefcnt, self.reg_clifds.keys(), len(self.timerq)))
            try:
                timeo = self.timerq.nextfire_delay()
                if timeout > 0 and timeo >= timeout:
                    # task timeout may invalidate clients timeout
                    self.timerq.clear()
                    timeo = timeout
                elif timeo == -1:
                    timeo = timeout

                self._current_loopcnt += 1
                if timeo >= 0:
                    r_ready, w_ready, x_ready = \
                        select.select(self._fds_r, self._fds_w, [], timeo)
                else:
                    # no timeout specified, do not supply the timeout argument
                    r_ready, w_ready, x_ready = \
                        select.select(self._fds_r, self._fds_w, [])
            except select.error, (ex_errno, ex_strerror):
                # might get interrupted by a signal
                if ex_errno == errno.EINTR:
                    continue
                elif ex_errno in [errno.EINVAL, errno.EBADF, errno.ENOMEM]:
                    print >> sys.stderr, "EngineSelect: %s" % ex_strerror
                else:
                    raise

            # iterate over fd on which events occured
            for fd in set(r_ready) | set(w_ready):

                # get client instance
                client, fdev = self._fd2client(fd)
                if client is None:
                    continue

                # process this client
                self._current_client = client

                # check for possible unblocking read on this fd
                if fd in r_ready:
                    assert fdev & (Engine.E_READ | Engine.E_ERROR)
                    assert client._events & fdev
                    self.modify(client, 0, fdev)
                    try:
                        if fdev & Engine.E_READ:
                            client._handle_read()
                        else:
                            client._handle_error()
                    except EngineClientEOF:
                        self._debug("EngineClientEOF %s" % client)
                        # if the EOF occurs on E_READ...
                        if fdev & Engine.E_READ:
                            # and if the client is also waiting for E_ERROR
                            if client._events & Engine.E_ERROR:
                                # just clear the event for E_READ
                                self.modify(client, 0, fdev)
                            else:
                                # otherwise we can remove the client
                                self.remove(client)
                        else:
                            # same thing in the other order...
                            if client._events & Engine.E_READ:
                                self.modify(client, 0, fdev)
                            else:
                                self.remove(client)

                # check for writing
                if fd in w_ready:
                    self._debug("W_READY fd=%d %s (r%s,e%s,w%s)" % (fd,
                        client.__class__.__name__, client.reader_fileno(),
                        client.error_fileno(), client.writer_fileno()))
                    assert fdev == Engine.E_WRITE
                    assert client._events & fdev
                    self.modify(client, 0, fdev)
                    client._handle_write()

                # post processing
                self._current_client = None

                # apply any changes occured during processing
                if client.registered:
                    self.set_events(client, client._new_events)

            # check for task runloop timeout
            if timeout > 0 and time.time() >= start_time + timeout:
                raise EngineTimeoutException()

            # process clients timeout
            self.fire_timers()

        self._debug("LOOP EXIT evlooprefcnt=%d (reg_clifds=%s) (timers=%d)" % \
                (self.evlooprefcnt, self.reg_clifds, len(self.timerq)))


########NEW FILE########
__FILENAME__ = Event
#
# Copyright CEA/DAM/DIF (2007, 2008, 2009, 2010, 2011, 2012)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
Event handler support

EventHandler's derived classes may implement ev_* methods to listen on
worker's events.
"""

class EventHandler(object):
    """
    Base class EventHandler.
    """
    def ev_start(self, worker):
        """
        Called to indicate that a worker has just started.
        """

    def ev_read(self, worker):
        """
        Called to indicate that a worker has data to read.
        """

    def ev_error(self, worker):
        """
        Called to indicate that a worker has error to read (on stderr).
        """

    def ev_written(self, worker):
        """
        Called to indicate that writing has been done.
        """

    def ev_hup(self, worker):
        """
        Called to indicate that a worker's connection has been closed.
        """

    def ev_timeout(self, worker):
        """
        Called to indicate that a worker has timed out (worker timeout only).
        """

    def ev_close(self, worker):
        """
        Called to indicate that a worker has just finished (it may already
        have failed on timeout).
        """

    def ev_msg(self, port, msg):
        """
        Handle port message.

        @param port: The port object on which a message is available.
        """

    def ev_timer(self, timer):
        """
        Handle firing timer.

        @param timer: The timer that is firing. 
        """

    def _ev_routing(self, worker, arg):
        """
        Routing event (private). Called to indicate that a (meta)worker has just
        updated one of its route path. You can safely ignore this event.
        """


########NEW FILE########
__FILENAME__ = Gateway
#!/usr/bin/env python
#
# Copyright CEA/DAM/DIF (2010, 2011, 2012)
#  Contributor: Henri DOREAU <henri.doreau@cea.fr>
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
ClusterShell agent launched on remote gateway nodes. This script reads messages
on stdin via the SSH connexion, interprets them, takes decisions, and prints out
replies on stdout.
"""

import logging
import os
import sys

from ClusterShell.Event import EventHandler
from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import task_self, _getshorthostname
from ClusterShell.Engine.Engine import EngineAbortException
from ClusterShell.Worker.fastsubprocess import set_nonblock_flag
from ClusterShell.Worker.Worker import WorkerSimple
from ClusterShell.Worker.Tree import WorkerTree
from ClusterShell.Communication import Channel, ConfigurationMessage, \
    ControlMessage, ACKMessage, ErrorMessage, EndMessage, StdOutMessage, \
    StdErrMessage, RetcodeMessage, TimeoutMessage


class WorkerTreeResponder(EventHandler):
    """Gateway WorkerTree handler"""
    def __init__(self, task, gwchan, srcwkr):
        EventHandler.__init__(self)
        self.gwchan = gwchan    # gateway channel
        self.srcwkr = srcwkr    # id of distant parent WorkerTree
        self.worker = None      # local WorkerTree instance
        # For messages grooming
        qdelay = task.info("grooming_delay")
        self.timer = task.timer(qdelay, self, qdelay, autoclose=True)
        self.logger = logging.getLogger(__name__)
        self.logger.debug("WorkerTreeResponder: initialized")

    def ev_start(self, worker):
        self.logger.debug("WorkerTreeResponder: ev_start")
        self.worker = worker

    def ev_timer(self, timer):
        """perform gateway traffic grooming"""
        if not self.worker:
            return
        logger = self.logger
        # check for grooming opportunities
        for msg_elem, nodes in self.worker.iter_errors():
            logger.debug("iter(stderr): %s: %d bytes" % \
                (nodes, len(msg_elem.message())))
            self.gwchan.send(StdErrMessage(nodes, msg_elem.message(), \
                                           self.srcwkr))
        for msg_elem, nodes in self.worker.iter_buffers():
            logger.debug("iter(stdout): %s: %d bytes" % \
                (nodes, len(msg_elem.message())))
            self.gwchan.send(StdOutMessage(nodes, msg_elem.message(), \
                                           self.srcwkr))
        self.worker.flush_buffers()

    def ev_error(self, worker):
        self.logger.debug("WorkerTreeResponder: ev_error %s" % \
            worker.current_errmsg)

    def ev_timeout(self, worker):
        """Received timeout event: some nodes did timeout"""
        self.gwchan.send(TimeoutMessage( \
            NodeSet._fromlist1(worker.iter_keys_timeout()), self.srcwkr))

    def ev_close(self, worker):
        """End of responder"""
        self.logger.debug("WorkerTreeResponder: ev_close")
        # finalize grooming
        self.ev_timer(None)
        # send retcodes
        for rc, nodes in self.worker.iter_retcodes():
            self.logger.debug("iter(rc): %s: rc=%d" % (nodes, rc))
            self.gwchan.send(RetcodeMessage(nodes, rc, self.srcwkr))
        self.timer.invalidate()
        # clean channel closing
        ####self.gwchan.close()


class GatewayChannel(Channel):
    """high level logic for gateways"""
    def __init__(self, task, hostname):
        """
        """
        Channel.__init__(self)
        self.task = task
        self.hostname = hostname
        self.topology = None
        self.propagation = None
        self.logger = logging.getLogger(__name__)

        self.current_state = None
        self.states = {
            'CFG': self._state_cfg,
            'CTL': self._state_ctl,
            'GTR': self._state_gtr,
        }

    def start(self):
        """initialization"""
        self._open()
        # prepare to receive topology configuration
        self.current_state = self.states['CFG']
        self.logger.debug('entering config state')

    def close(self):
        """close gw channel"""
        self.logger.debug('closing gw channel')
        self._close()
        self.current_state = None

    def recv(self, msg):
        """handle incoming message"""
        try:
            self.logger.debug('handling incoming message: %s', str(msg))
            if msg.ident == EndMessage.ident:
                self.logger.debug('recv: got EndMessage')
                self.worker.abort()
            else:
                self.current_state(msg)
        except Exception, ex:
            self.logger.exception('on recv(): %s', str(ex))
            self.send(ErrorMessage(str(ex)))

    def _state_cfg(self, msg):
        """receive topology configuration"""
        if msg.type == ConfigurationMessage.ident:
            self.topology = msg.data_decode()
            task_self().topology = self.topology
            self.logger.debug('decoded propagation tree')
            self.logger.debug('%s' % str(self.topology))
            self._ack(msg)
            self.current_state = self.states['CTL']
            self.logger.debug('entering control state')
        else:
            logging.error('unexpected message: %s', str(msg))

    def _state_ctl(self, msg):
        """receive control message with actions to perform"""
        if msg.type == ControlMessage.ident:
            self.logger.debug('GatewayChannel._state_ctl')
            self._ack(msg)
            if msg.action == 'shell':
                data = msg.data_decode()
                cmd = data['cmd']
                stderr = data['stderr']
                timeout = data['timeout']

                #self.propagation.invoke_gateway = data['invoke_gateway']
                self.logger.debug('decoded gw invoke (%s)', \
                                  data['invoke_gateway'])

                taskinfo = data['taskinfo']
                task = task_self()
                task._info = taskinfo
                task._engine.info = taskinfo

                #logging.setLevel(logging.DEBUG)

                self.logger.debug('assigning task infos (%s)' % \
                    str(data['taskinfo']))

                self.logger.debug('inherited fanout value=%d', \
                                  task.info("fanout"))

                #self.current_state = self.states['GTR']
                self.logger.debug('launching execution/enter gathering state')

                responder = WorkerTreeResponder(task, self, msg.srcid)

                self.propagation = WorkerTree(msg.target, responder, timeout,
                                              command=cmd,
                                              topology=self.topology,
                                              newroot=self.hostname,
                                              stderr=stderr)
                responder.worker = self.propagation # FIXME ev_start-not-called workaround
                self.propagation.upchannel = self
                task.schedule(self.propagation)
                self.logger.debug("WorkerTree scheduled")
        else:
            logging.error('unexpected message: %s', str(msg))

    def _state_gtr(self, msg):
        """gather outputs"""
        # FIXME
        self.logger.debug('GatewayChannel._state_gtr')
        self.logger.debug('incoming output msg: %s' % str(msg))

    def _ack(self, msg):
        """acknowledge a received message"""
        self.send(ACKMessage(msg.msgid))


def gateway_main():
    """ClusterShell gateway entry point"""
    host = _getshorthostname()
    # configure root logger
    logdir = os.path.expanduser(os.environ.get('CLUSTERSHELL_GW_LOG_DIR', \
                                               '/tmp'))
    loglevel = os.environ.get('CLUSTERSHELL_GW_LOG_LEVEL', 'INFO')
    logging.basicConfig(level=getattr(logging, loglevel.upper(), logging.INFO),
                        format='%(asctime)s %(name)s %(levelname)s %(message)s',
                        filename=os.path.join(logdir, "%s.gw.log" % host))
    logger = logging.getLogger(__name__)
    logger.debug('Starting gateway on %s', host)
    logger.debug("environ=%s" % os.environ)

    set_nonblock_flag(sys.stdin.fileno())
    set_nonblock_flag(sys.stdout.fileno())
    set_nonblock_flag(sys.stderr.fileno())

    task = task_self()
    
    # Pre-enable MsgTree buffering on gateway (not available at runtime - #181)
    task.set_default("stdout_msgtree", True)
    task.set_default("stderr_msgtree", True)

    if sys.stdin.isatty():
        logger.critical('Gateway failure: sys.stdin.isatty() is True')
        sys.exit(1)

    worker = WorkerSimple(sys.stdin, sys.stdout, sys.stderr, None,
                          handler=GatewayChannel(task, host))
    task.schedule(worker)
    logger.debug('Starting task')
    try:
        task.resume()
        logger.debug('Task performed')
    except EngineAbortException, exc:
        pass
    except IOError, exc:
        logger.debug('Broken pipe (%s)' % exc)
        raise
    except Exception, exc:
        logger.exception('Gateway failure: %s' % exc)
    logger.debug('The End')

if __name__ == '__main__':
    __name__ = 'ClusterShell.Gateway'
    # To enable gateway profiling:
    #import cProfile
    #cProfile.run('gateway_main()', '/tmp/gwprof')
    gateway_main()

########NEW FILE########
__FILENAME__ = MsgTree
#
# Copyright CEA/DAM/DIF (2007, 2008, 2009, 2010, 2011)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
MsgTree

ClusterShell message tree module. The purpose of MsgTree is to
provide a shared message tree for storing message lines received
from ClusterShell Workers (for example, from remote cluster
commands). It should be efficient, in term of algorithm and memory
consumption, especially when remote messages are the same.
"""

from itertools import ifilterfalse, imap
from operator import itemgetter

# MsgTree behavior modes
MODE_DEFER = 0
MODE_SHIFT = 1
MODE_TRACE = 2


class MsgTreeElem(object):
    """
    Class representing an element of the MsgTree and its associated
    message. Object of this class are returned by the various MsgTree
    methods like messages() or walk(). The object can then be used as
    an iterator over the message lines or casted into a string.
    """
    def __init__(self, msgline=None, parent=None, trace=False):
        """
        Initialize message tree element.
        """
        # structure
        self.parent = parent
        self.children = {}
        if trace:  # special behavior for trace mode
            self._shift = self._shift_trace
        else:
            self._shift = self._shift_notrace
        # content
        self.msgline = msgline
        self.keys = None
   
    def __len__(self):
        """Length of whole message string."""
        return len(str(self))

    def __eq__(self, other):
        """Comparison method compares whole message strings."""
        return str(self) == str(other)

    def _add_key(self, key):
        """Add a key to this tree element."""
        if self.keys is None:
            self.keys = set([key])
        else:
            self.keys.add(key)

    def _shift_notrace(self, key, target_elem):
        """Shift one of our key to specified target element."""
        if self.keys and len(self.keys) == 1:
            shifting = self.keys
            self.keys = None
        else:
            shifting = set([ key ])
            if self.keys:
                self.keys.difference_update(shifting)

        if not target_elem.keys:
            target_elem.keys = shifting
        else:
            target_elem.keys.update(shifting)

        return target_elem

    def _shift_trace(self, key, target_elem):
        """Shift one of our key to specified target element (trace
        mode: keep backtrace of keys)."""
        if not target_elem.keys:
            target_elem.keys = set([ key ])
        else:
            target_elem.keys.add(key)
        return target_elem

    def __getitem__(self, i):
        return list(self.lines())[i]

    def __iter__(self):
        """Iterate over message lines starting from this tree element."""
        # no msgline in root element
        if self.msgline is None:
            return
        # trace the message path
        path = [self.msgline]
        parent = self.parent
        while parent.msgline is not None:
            path.append(parent.msgline)
            parent = parent.parent
        # rewind path
        while path:
            yield path.pop()

    def lines(self):
        """
        Get the whole message lines iterator from this tree element.
        """
        return iter(self)

    splitlines = lines

    def message(self):
        """
        Get the whole message buffer from this tree element.
        """
        # concat buffers
        return '\n'.join(self.lines())

    __str__ = message

    def append(self, msgline, key=None):
        """
        A new message is coming, append it to the tree element with
        optional associated source key. Called by MsgTree.add().
        Return corresponding MsgTreeElem (possibly newly created).
        """
        if key is None:
            # No key association, MsgTree is in MODE_DEFER
            return self.children.setdefault(msgline, \
                self.__class__(msgline, self, self._shift == self._shift_trace))
        else:
            # key given: get/create new child element and shift down the key
            return self._shift(key, self.children.setdefault(msgline, \
                self.__class__(msgline, self,
                               self._shift == self._shift_trace)))


class MsgTree(object):
    """
    A MsgTree object maps key objects to multi-lines messages.
    MsgTree's are mutable objects. Keys are almost arbitrary values
    (must be hashable). Message lines are organized as a tree
    internally. MsgTree provides low memory consumption especially
    on a cluster when all nodes return similar messages. Also,
    the gathering of messages is done automatically.
    """

    def __init__(self, mode=MODE_DEFER):
        """MsgTree initializer
        
        The `mode' parameter should be set to one of the following constant:

        MODE_DEFER: all messages are processed immediately, saving memory from
        duplicate message lines, but keys are associated to tree elements only
        when needed.

        MODE_SHIFT: all keys and messages are processed immediately, it is more
        CPU time consuming as MsgTree full state is updated at each add() call.

        MODE_TRACE: all keys and messages and processed immediately, and keys
        are kept for each message element of the tree. The special method
        walk_trace() is then available to walk all elements of the tree.
        """
        self.mode = mode
        # root element of MsgTree
        self._root = MsgTreeElem(trace=(mode == MODE_TRACE))
        # dict of keys to MsgTreeElem
        self._keys = {}

    def clear(self):
        """Remove all items from the MsgTree."""
        self._root = MsgTreeElem(trace=(self.mode == MODE_TRACE))
        self._keys.clear()

    def __len__(self):
        """Return the number of keys contained in the MsgTree."""
        return len(self._keys)

    def __getitem__(self, key):
        """Return the message of MsgTree with specified key. Raises a
        KeyError if key is not in the MsgTree."""
        return self._keys[key]

    def get(self, key, default=None):
        """
        Return the message for key if key is in the MsgTree, else default.
        If default is not given, it defaults to None, so that this method
        never raises a KeyError.
        """
        return self._keys.get(key, default)

    def add(self, key, msgline):
        """
        Add a message line associated with the given key to the MsgTree.
        """
        # try to get current element in MsgTree for the given key,
        # defaulting to the root element
        e_msg = self._keys.get(key, self._root)
        if self.mode >= MODE_SHIFT:
            key_shift = key
        else:
            key_shift = None
        # add child msg and update keys dict
        self._keys[key] = e_msg.append(msgline, key_shift)

    def _update_keys(self):
        """Update keys associated to tree elements."""
        for key, e_msg in self._keys.iteritems():
            assert key is not None and e_msg is not None
            e_msg._add_key(key)

    def keys(self):
        """Return an iterator over MsgTree's keys."""
        return self._keys.iterkeys()

    __iter__ = keys
    
    def messages(self, match=None):
        """Return an iterator over MsgTree's messages."""
        return imap(itemgetter(0), self.walk(match))
    
    def items(self, match=None, mapper=None):
        """
        Return (key, message) for each key of the MsgTree.
        """
        if mapper is None:
            mapper = lambda k: k
        for key, elem in self._keys.iteritems():
            if match is None or match(key):
                yield mapper(key), elem

    def _depth(self):
        """
        Return the depth of the MsgTree, ie. the max number of lines
        per message. Added for debugging.
        """
        depth = 0
        # stack of (element, depth) tuples used to walk the tree
        estack = [ (self._root, depth) ]

        while estack:
            elem, edepth = estack.pop()
            if len(elem.children) > 0:
                estack += [(v, edepth + 1) for v in elem.children.values()]
            depth = max(depth, edepth)
        
        return depth

    def walk(self, match=None, mapper=None):
        """
        Walk the tree. Optionally filter keys on match parameter,
        and optionally map resulting keys with mapper function.
        Return an iterator over (message, keys) tuples for each
        different message in the tree.
        """
        if self.mode == MODE_DEFER:
            self._update_keys()
        # stack of elements used to walk the tree (depth-first)
        estack = [ self._root ]
        while estack:
            elem = estack.pop()
            children = elem.children
            if len(children) > 0:
                estack += children.values()
            if elem.keys: # has some keys
                mkeys = filter(match, elem.keys)
                if len(mkeys):
                    yield elem, map(mapper, mkeys)

    def walk_trace(self, match=None, mapper=None):
        """
        Walk the tree in trace mode. Optionally filter keys on match
        parameter, and optionally map resulting keys with mapper
        function.
        Return an iterator over 4-length tuples (msgline, keys, depth,
        num_children).
        """
        assert self.mode == MODE_TRACE, \
            "walk_trace() is only callable in trace mode"
        # stack of (element, depth) tuples used to walk the tree
        estack = [ (self._root, 0) ]
        while estack:
            elem, edepth = estack.pop()
            children = elem.children
            nchildren = len(children)
            if nchildren > 0:
                estack += [(v, edepth + 1) for v in children.values()]
            if elem.keys:
                mkeys = filter(match, elem.keys)
                if len(mkeys):
                    yield elem.msgline, map(mapper, mkeys), edepth, nchildren

    def remove(self, match=None):
        """
        Modify the tree by removing any matching key references from the
        messages tree.

        Example of use:
            >>> msgtree.remove(lambda k: k > 3)
        """
        estack = [ self._root ]

        # walk the tree to keep only matching keys
        while estack:
            elem = estack.pop()
            if len(elem.children) > 0:
                estack += elem.children.values()
            if elem.keys: # has some keys
                elem.keys = set(ifilterfalse(match, elem.keys))

        # also remove key(s) from known keys dict
        for key in filter(match, self._keys.keys()):
            del self._keys[key]

########NEW FILE########
__FILENAME__ = NodeSet
#
# Copyright CEA/DAM/DIF (2007-2014)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#  Contributor: Aurelien DEGREMONT <aurelien.degremont@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
Cluster node set module.

A module to efficiently deal with node sets and node groups.
Instances of NodeSet provide similar operations than the builtin set() type,
see http://www.python.org/doc/lib/set-objects.html

Usage example
=============
  >>> # Import NodeSet class
  ... from ClusterShell.NodeSet import NodeSet
  >>>
  >>> # Create a new nodeset from string
  ... nodeset = NodeSet("cluster[1-30]")
  >>> # Add cluster32 to nodeset
  ... nodeset.update("cluster32")
  >>> # Remove from nodeset
  ... nodeset.difference_update("cluster[2-5,8-31]")
  >>> # Print nodeset as a pdsh-like pattern
  ... print nodeset
  cluster[1,6-7,32]
  >>> # Iterate over node names in nodeset
  ... for node in nodeset:
  ...     print node
  cluster1
  cluster6
  cluster7
  cluster32
"""

import re
import sys

import ClusterShell.NodeUtils as NodeUtils
from ClusterShell.RangeSet import RangeSet, RangeSetND, RangeSetParseError


# Define default GroupResolver object used by NodeSet
DEF_GROUPS_CONFIG = "/etc/clustershell/groups.conf"
ILLEGAL_GROUP_CHARS = set("@,!&^*")
_DEF_RESOLVER_STD_GROUP = NodeUtils.GroupResolverConfig(DEF_GROUPS_CONFIG, \
                                                        ILLEGAL_GROUP_CHARS)
# Standard group resolver
RESOLVER_STD_GROUP = _DEF_RESOLVER_STD_GROUP
# Special constants for NodeSet's resolver parameter
#   RESOLVER_NOGROUP => avoid any group resolution at all
#   RESOLVER_NOINIT  => reserved use for optimized copy()
RESOLVER_NOGROUP = -1
RESOLVER_NOINIT  = -2
# 1.5 compat (deprecated)
STD_GROUP_RESOLVER = RESOLVER_STD_GROUP
NOGROUP_RESOLVER = RESOLVER_NOGROUP


class NodeSetException(Exception):
    """Base NodeSet exception class."""

class NodeSetError(NodeSetException):
    """Raised when an error is encountered."""

class NodeSetParseError(NodeSetError):
    """Raised when NodeSet parsing cannot be done properly."""
    def __init__(self, part, msg):
        if part:
            msg = "%s : \"%s\"" % (msg, part)
        NodeSetError.__init__(self, msg)
        # faulty part; this allows you to target the error
        self.part = part

class NodeSetParseRangeError(NodeSetParseError):
    """Raised when bad range is encountered during NodeSet parsing."""
    def __init__(self, rset_exc):
        NodeSetParseError.__init__(self, str(rset_exc), "bad range")

class NodeSetExternalError(NodeSetError):
    """Raised when an external error is encountered."""


class NodeSetBase(object):
    """
    Base class for NodeSet.

    This class allows node set base object creation from specified string
    pattern and rangeset object.  If optional copy_rangeset boolean flag is
    set to True (default), provided rangeset object is copied (if needed),
    otherwise it may be referenced (should be seen as an ownership transfer
    upon creation).

    This class implements core node set arithmetics (no string parsing here).

    Example:
       >>> nsb = NodeSetBase('node%s-ipmi', RangeSet('1-5,7'), False)
       >>> str(nsb)
       'node[1-5,7]-ipmi'
       >>> nsb = NodeSetBase('node%s-ib%s', RangeSetND([['1-5,7', '1-2']]), False)
       >>> str(nsb)
       'node[1-5,7]-ib[1-2]'
    """
    def __init__(self, pattern=None, rangeset=None, copy_rangeset=True):
        """New NodeSetBase object initializer"""
        self._length = 0
        self._patterns = {}
        if pattern:
            self._add(pattern, rangeset, copy_rangeset)
        elif rangeset:
            raise ValueError("missing pattern")

    def _iter(self):
        """Iterator on internal item tuples
            (pattern, indexes, padding, autostep)."""
        for pat, rset in sorted(self._patterns.iteritems()):
            if rset:
                autostep = rset.autostep
                if rset.dim() == 1:
                    assert isinstance(rset, RangeSet)
                    padding = rset.padding
                    for idx in rset:
                        yield pat, (idx,), (padding,), autostep
                else:
                    for args, padding in rset.iter_padding():
                        yield pat, args, padding, autostep
            else:
                yield pat, None, None, None

    def _iterbase(self):
        """Iterator on single, one-item NodeSetBase objects."""
        for pat, ivec, pad, autostep in self._iter():
            rset = None     # 'no node index' by default
            if ivec is not None:
                assert len(ivec) > 0
                if len(ivec) == 1:
                    rset = RangeSet.fromone(ivec[0], pad[0] or 0, autostep)
                else:
                    rset = RangeSetND([ivec], pad, autostep)
            yield NodeSetBase(pat, rset)

    def __iter__(self):
        """Iterator on single nodes as string."""
        # Does not call self._iterbase() + str() for better performance.
        for pat, ivec, pads, _ in self._iter():
            if ivec is not None:
                # For performance reasons, add a special case for 1D RangeSet
                if len(ivec) == 1:
                    yield pat % ("%0*d" % (pads[0] or 0, ivec[0]))
                else:
                    yield pat % tuple(["%0*d" % (pad or 0, i) \
                                      for pad, i in zip(pads, ivec)])
            else:
                yield pat

    # define striter() alias for convenience (to match RangeSet.striter())
    striter = __iter__

    # define nsiter() as an object-based iterator that could be used for
    # __iter__() in the future...

    def nsiter(self):
        """Object-based NodeSet iterator on single nodes."""
        for pat, ivec, pad, autostep in self._iter():
            nodeset = self.__class__()
            if ivec is not None:
                if len(ivec) == 1:
                    nodeset._add_new(pat, \
                                     RangeSet.fromone(ivec[0], pad[0] or 0))
                else:
                    nodeset._add_new(pat, RangeSetND([ivec], None, autostep))
            else:
                nodeset._add_new(pat, None)
            yield nodeset

    def contiguous(self):
        """Object-based NodeSet iterator on contiguous node sets.

        Contiguous node set contains nodes with same pattern name and a
        contiguous range of indexes, like foobar[1-100]."""
        for pat, rangeset in sorted(self._patterns.iteritems()):
            if rangeset:
                for cont_rset in rangeset.contiguous():
                    nodeset = self.__class__()
                    nodeset._add_new(pat, cont_rset)
                    yield nodeset
            else:
                nodeset = self.__class__()
                nodeset._add_new(pat, None)
                yield nodeset

    def __len__(self):
        """Get the number of nodes in NodeSet."""
        cnt = 0
        for rangeset in self._patterns.itervalues():
            if rangeset:
                cnt += len(rangeset)
            else:
                cnt += 1
        return cnt

    def __str__(self):
        """Get ranges-based pattern of node list."""
        results = []
        try:
            for pat, rset in sorted(self._patterns.iteritems()):
                if not rset:
                    results.append(pat)
                elif rset.dim() == 1:
                    rgs = str(rset)
                    cnt = len(rset)
                    if cnt > 1:
                        rgs = "[%s]" % rgs
                    results.append(pat % rgs)
                elif rset.dim() > 1:
                    for rgvec in rset.vectors():
                        rgargs = []
                        for rangeset in rgvec:
                            rgs = str(rangeset)
                            cnt = len(rangeset)
                            if cnt > 1:
                                rgs = "[%s]" % rgs
                            rgargs.append(rgs)
                        results.append(pat % tuple(rgargs))
        except TypeError:
            raise NodeSetParseError(pat, "Internal error: " \
                                         "node pattern and ranges mismatch")
        return ",".join(results)

    def copy(self):
        """Return a shallow copy."""
        cpy = self.__class__()
        cpy._length = self._length
        dic = {}
        for pat, rangeset in self._patterns.iteritems():
            if rangeset is None:
                dic[pat] = None
            else:
                dic[pat] = rangeset.copy()
        cpy._patterns = dic
        return cpy

    def __contains__(self, other):
        """Is node contained in NodeSet ?"""
        return self.issuperset(other)

    def _binary_sanity_check(self, other):
        # check that the other argument to a binary operation is also
        # a NodeSet, raising a TypeError otherwise.
        if not isinstance(other, NodeSetBase):
            raise TypeError, \
                "Binary operation only permitted between NodeSetBase"

    def issubset(self, other):
        """Report whether another nodeset contains this nodeset."""
        self._binary_sanity_check(other)
        return other.issuperset(self)

    def issuperset(self, other):
        """Report whether this nodeset contains another nodeset."""
        self._binary_sanity_check(other)
        status = True
        for pat, erangeset in other._patterns.iteritems():
            rangeset = self._patterns.get(pat)
            if rangeset:
                status = rangeset.issuperset(erangeset)
            else:
                # might be an unnumbered node (key in dict but no value)
                status = self._patterns.has_key(pat)
            if not status:
                break
        return status

    def __eq__(self, other):
        """NodeSet equality comparison."""
        # See comment for for RangeSet.__eq__()
        if not isinstance(other, NodeSetBase):
            return NotImplemented
        return len(self) == len(other) and self.issuperset(other)

    # inequality comparisons using the is-subset relation
    __le__ = issubset
    __ge__ = issuperset

    def __lt__(self, other):
        """x.__lt__(y) <==> x<y"""
        self._binary_sanity_check(other)
        return len(self) < len(other) and self.issubset(other)

    def __gt__(self, other):
        """x.__gt__(y) <==> x>y"""
        self._binary_sanity_check(other)
        return len(self) > len(other) and self.issuperset(other)

    def _extractslice(self, index):
        """Private utility function: extract slice parameters from slice object
        `index` for an list-like object of size `length`."""
        length = len(self)
        if index.start is None:
            sl_start = 0
        elif index.start < 0:
            sl_start = max(0, length + index.start)
        else:
            sl_start = index.start
        if index.stop is None:
            sl_stop = sys.maxint
        elif index.stop < 0:
            sl_stop = max(0, length + index.stop)
        else:
            sl_stop = index.stop
        if index.step is None:
            sl_step = 1
        elif index.step < 0:
            # We support negative step slicing with no start/stop, ie. r[::-n].
            if index.start is not None or index.stop is not None:
                raise IndexError, \
                    "illegal start and stop when negative step is used"
            # As RangeSet elements are ordered internally, adjust sl_start
            # to fake backward stepping in case of negative slice step.
            stepmod = (length + -index.step - 1) % -index.step
            if stepmod > 0:
                sl_start += stepmod
            sl_step = -index.step
        else:
            sl_step = index.step
        if not isinstance(sl_start, int) or not isinstance(sl_stop, int) \
            or not isinstance(sl_step, int):
            raise TypeError, "slice indices must be integers"
        return sl_start, sl_stop, sl_step

    def __getitem__(self, index):
        """Return the node at specified index or a subnodeset when a slice is
        specified."""
        if isinstance(index, slice):
            inst = NodeSetBase()
            sl_start, sl_stop, sl_step = self._extractslice(index)
            sl_next = sl_start
            if sl_stop <= sl_next:
                return inst
            length = 0
            for pat, rangeset in sorted(self._patterns.iteritems()):
                if rangeset:
                    cnt = len(rangeset)
                    offset = sl_next - length
                    if offset < cnt:
                        num = min(sl_stop - sl_next, cnt - offset)
                        inst._add(pat, rangeset[offset:offset + num:sl_step])
                    else:
                        #skip until sl_next is reached
                        length += cnt
                        continue
                else:
                    cnt = num = 1
                    if sl_next > length:
                        length += cnt
                        continue
                    inst._add(pat, None)
                # adjust sl_next...
                sl_next += num
                if (sl_next - sl_start) % sl_step:
                    sl_next = sl_start + \
                        ((sl_next - sl_start)/sl_step + 1) * sl_step
                if sl_next >= sl_stop:
                    break
                length += cnt
            return inst
        elif isinstance(index, int):
            if index < 0:
                length = len(self)
                if index >= -length:
                    index = length + index # - -index
                else:
                    raise IndexError, "%d out of range" % index
            length = 0
            for pat, rangeset in sorted(self._patterns.iteritems()):
                if rangeset:
                    cnt = len(rangeset)
                    if index < length + cnt:
                        # return a subrangeset of size 1 to manage padding
                        if rangeset.dim() == 1:
                            return pat % rangeset[index-length:index-length+1]
                        else:
                            sub = rangeset[index-length:index-length+1]
                            for rgvec in sub.vectors():
                                return pat % (tuple(rgvec))
                else:
                    cnt = 1
                    if index == length:
                        return pat
                length += cnt
            raise IndexError, "%d out of range" % index
        else:
            raise TypeError, "NodeSet indices must be integers"

    def _add_new(self, pat, rangeset):
        """Add nodes from a (pat, rangeset) tuple.
        Predicate: pattern does not exist in current set. RangeSet object is
        referenced (not copied)."""
        assert pat not in self._patterns
        self._patterns[pat] = rangeset

    def _add(self, pat, rangeset, copy_rangeset=True):
        """Add nodes from a (pat, rangeset) tuple.
        `pat' may be an existing pattern and `rangeset' may be None.
        RangeSet or RangeSetND objects are copied if re-used internally
        when provided and if copy_rangesets flag is set.
        """
        if pat in self._patterns:
            # existing pattern: get RangeSet or RangeSetND entry...
            pat_e = self._patterns[pat]
            # sanity checks
            if (pat_e is None) is not (rangeset is None):
                raise NodeSetError("Invalid operation")
            # entry may exist but set to None (single node)
            if pat_e:
                pat_e.update(rangeset)
        else:
            # new pattern...
            if rangeset and copy_rangeset:
                rangeset = rangeset.copy()
            self._add_new(pat, rangeset)

    def union(self, other):
        """
        s.union(t) returns a new set with elements from both s and t.
        """
        self_copy = self.copy()
        self_copy.update(other)
        return self_copy

    def __or__(self, other):
        """
        Implements the | operator. So s | t returns a new nodeset with
        elements from both s and t.
        """
        if not isinstance(other, NodeSetBase):
            return NotImplemented
        return self.union(other)

    def add(self, other):
        """
        Add node to NodeSet.
        """
        self.update(other)

    def update(self, other):
        """
        s.update(t) returns nodeset s with elements added from t.
        """
        for pat, rangeset in other._patterns.iteritems():
            self._add(pat, rangeset)

    def updaten(self, others):
        """
        s.updaten(list) returns nodeset s with elements added from given list.
        """
        for other in others:
            self.update(other)

    def clear(self):
        """
        Remove all nodes from this nodeset.
        """
        self._patterns.clear()

    def __ior__(self, other):
        """
        Implements the |= operator. So s |= t returns nodeset s with
        elements added from t. (Python version 2.5+ required)
        """
        self._binary_sanity_check(other)
        self.update(other)
        return self

    def intersection(self, other):
        """
        s.intersection(t) returns a new set with elements common to s
        and t.
        """
        self_copy = self.copy()
        self_copy.intersection_update(other)
        return self_copy

    def __and__(self, other):
        """
        Implements the & operator. So s & t returns a new nodeset with
        elements common to s and t.
        """
        if not isinstance(other, NodeSet):
            return NotImplemented
        return self.intersection(other)

    def intersection_update(self, other):
        """
        s.intersection_update(t) returns nodeset s keeping only
        elements also found in t.
        """
        if other is self:
            return

        tmp_ns = NodeSetBase()

        for pat, irangeset in other._patterns.iteritems():
            rangeset = self._patterns.get(pat)
            if rangeset:
                irset = rangeset.intersection(irangeset)
                # ignore pattern if empty rangeset
                if len(irset) > 0:
                    tmp_ns._add(pat, irset, copy_rangeset=False)
            elif not irangeset and pat in self._patterns:
                # intersect two nodes with no rangeset
                tmp_ns._add(pat, None)

        # Substitute 
        self._patterns = tmp_ns._patterns

    def __iand__(self, other):
        """
        Implements the &= operator. So s &= t returns nodeset s keeping
        only elements also found in t. (Python version 2.5+ required)
        """
        self._binary_sanity_check(other)
        self.intersection_update(other)
        return self

    def difference(self, other):
        """
        s.difference(t) returns a new NodeSet with elements in s but not
        in t.
        """
        self_copy = self.copy()
        self_copy.difference_update(other)
        return self_copy

    def __sub__(self, other):
        """
        Implement the - operator. So s - t returns a new nodeset with
        elements in s but not in t.
        """
        if not isinstance(other, NodeSetBase):
            return NotImplemented
        return self.difference(other)

    def difference_update(self, other, strict=False):
        """
        s.difference_update(t) returns nodeset s after removing
        elements found in t. If strict is True, raise KeyError
        if an element cannot be removed.
        """
        # the purge of each empty pattern is done afterward to allow self = ns
        purge_patterns = []

        # iterate first over exclude nodeset rangesets which is usually smaller
        for pat, erangeset in other._patterns.iteritems():
            # if pattern is found, deal with it
            rangeset = self._patterns.get(pat)
            if rangeset:
                # sub rangeset, raise KeyError if not found
                rangeset.difference_update(erangeset, strict)

                # check if no range left and add pattern to purge list
                if len(rangeset) == 0:
                    purge_patterns.append(pat)
            else:
                # unnumbered node exclusion
                if self._patterns.has_key(pat):
                    purge_patterns.append(pat)
                elif strict:
                    raise KeyError, pat

        for pat in purge_patterns:
            del self._patterns[pat]

    def __isub__(self, other):
        """
        Implement the -= operator. So s -= t returns nodeset s after
        removing elements found in t. (Python version 2.5+ required)
        """
        self._binary_sanity_check(other)
        self.difference_update(other)
        return self

    def remove(self, elem):
        """
        Remove element elem from the nodeset. Raise KeyError if elem
        is not contained in the nodeset.
        """
        self.difference_update(elem, True)

    def symmetric_difference(self, other):
        """
        s.symmetric_difference(t) returns the symmetric difference of
        two nodesets as a new NodeSet.
        
        (ie. all nodes that are in exactly one of the nodesets.)
        """
        self_copy = self.copy()
        self_copy.symmetric_difference_update(other)
        return self_copy

    def __xor__(self, other):
        """
        Implement the ^ operator. So s ^ t returns a new NodeSet with
        nodes that are in exactly one of the nodesets.
        """
        if not isinstance(other, NodeSet):
            return NotImplemented
        return self.symmetric_difference(other)

    def symmetric_difference_update(self, other):
        """
        s.symmetric_difference_update(t) returns nodeset s keeping all
        nodes that are in exactly one of the nodesets.
        """
        purge_patterns = []

        # iterate over our rangesets
        for pat, rangeset in self._patterns.iteritems():
            brangeset = other._patterns.get(pat)
            if brangeset:
                rangeset.symmetric_difference_update(brangeset)
            else:
                if other._patterns.has_key(pat):
                    purge_patterns.append(pat)

        # iterate over other's rangesets
        for pat, brangeset in other._patterns.iteritems():
            rangeset = self._patterns.get(pat)
            if not rangeset and not pat in self._patterns:
                self._add(pat, brangeset)

        # check for patterns cleanup
        for pat, rangeset in self._patterns.iteritems():
            if rangeset is not None and len(rangeset) == 0:
                purge_patterns.append(pat)

        # cleanup
        for pat in purge_patterns:
            del self._patterns[pat]

    def __ixor__(self, other):
        """
        Implement the ^= operator. So s ^= t returns nodeset s after
        keeping all nodes that are in exactly one of the nodesets.
        (Python version 2.5+ required)
        """
        self._binary_sanity_check(other)
        self.symmetric_difference_update(other)
        return self


class ParsingEngine(object):
    """
    Class that is able to transform a source into a NodeSetBase.
    """
    OP_CODES = { 'update': ',',
                 'difference_update': '!',
                 'intersection_update': '&',
                 'symmetric_difference_update': '^' }

    def __init__(self, group_resolver):
        """
        Initialize Parsing Engine.
        """
        self.group_resolver = group_resolver
        self.base_node_re = re.compile("(\D*)(\d*)")

    def parse(self, nsobj, autostep):
        """
        Parse provided object if possible and return a NodeSetBase object.
        """
        # passing None is supported
        if nsobj is None:
            return NodeSetBase()

        # is nsobj a NodeSetBase instance?
        if isinstance(nsobj, NodeSetBase):
            return nsobj

        # or is nsobj a string?
        if type(nsobj) is str:
            try:
                return self.parse_string(str(nsobj), autostep)
            except NodeUtils.GroupSourceQueryFailed, exc:
                raise NodeSetParseError(nsobj, str(exc))

        raise TypeError("Unsupported NodeSet input %s" % type(nsobj))
        
    def parse_string(self, nsstr, autostep):
        """
        Parse provided string and return a NodeSetBase object.
        """
        nodeset = NodeSetBase()

        for opc, pat, rgnd in self._scan_string(nsstr, autostep):
            # Parser main debugging:
            #print "OPC %s PAT %s RANGESETS %s" % (opc, pat, rgnd)
            if self.group_resolver and pat[0] == '@':
                ns_group = NodeSetBase()
                for nodegroup in NodeSetBase(pat, rgnd):
                    # parse/expand nodes group
                    ns_string_ext = self.parse_group_string(nodegroup)
                    if ns_string_ext:
                        # convert result and apply operation
                        ns_group.update(self.parse(ns_string_ext, autostep))
                # perform operation
                getattr(nodeset, opc)(ns_group)
            else:
                getattr(nodeset, opc)(NodeSetBase(pat, rgnd, False))

        return nodeset
        
    def parse_string_single(self, nsstr, autostep):
        """Parse provided string and return a NodeSetBase object."""
        pat, rangesets = self._scan_string_single(nsstr, autostep)
        if len(rangesets) > 1:
            rgobj = RangeSetND([rangesets], None, autostep, copy_rangeset=False)
        elif len(rangesets) == 1:
            rgobj = rangesets[0]
        else: # non-indexed nodename
            rgobj = None
        return NodeSetBase(pat, rgobj, False)
        
    def parse_group(self, group, namespace=None, autostep=None):
        """Parse provided single group name (without @ prefix)."""
        assert self.group_resolver is not None
        nodestr = self.group_resolver.group_nodes(group, namespace)
        return self.parse(",".join(nodestr), autostep)
        
    def parse_group_string(self, nodegroup):
        """Parse provided group string and return a string."""
        assert nodegroup[0] == '@'
        assert self.group_resolver is not None
        grpstr = nodegroup[1:]
        if grpstr.find(':') < 0:
            # default namespace
            if grpstr == '*':
                return ",".join(self.all_nodes())
            return ",".join(self.group_resolver.group_nodes(grpstr))
        else:
            # specified namespace
            namespace, group = grpstr.split(':', 1)
            if group == '*':
                return ",".join(self.all_nodes(namespace))
            return ",".join(self.group_resolver.group_nodes(group, namespace))

    def grouplist(self, namespace=None):
        """Return a sorted list of groups from current resolver (in optional
        group source / namespace)."""
        grpset = NodeSetBase()
        for grpstr in self.group_resolver.grouplist(namespace):
            # We scan each group string to expand any range seen...
            for opc, pat, rgnd in self._scan_string(grpstr, None):
                getattr(grpset, opc)(NodeSetBase(pat, rgnd, False))
        return list(grpset)

    def all_nodes(self, namespace=None):
        """Get all nodes from group resolver as a list of strings."""
        # namespace is the optional group source
        assert self.group_resolver is not None
        all = []
        try:
            # Ask resolver to provide all nodes.
            all = self.group_resolver.all_nodes(namespace)
        except NodeUtils.GroupSourceNoUpcall:
            try:
                # As the resolver is not able to provide all nodes directly,
                # failback to list + map(s) method:
                for grp in self.grouplist(namespace):
                    all += self.group_resolver.group_nodes(grp, namespace)
            except NodeUtils.GroupSourceNoUpcall:
                # We are not able to find "all" nodes, definitely.
                raise NodeSetExternalError("Not enough working external " \
                    "calls (all, or map + list) defined to get all nodes")
        except NodeUtils.GroupSourceQueryFailed, exc:
            raise NodeSetExternalError("Unable to get all nodes due to the " \
                "following external failure:\n\t%s" % exc)
        return all

    def _next_op(self, pat):
        """Opcode parsing subroutine."""
        op_idx = -1
        next_op_code = None
        for opc, idx in [(k, pat.find(v)) \
                            for k, v in ParsingEngine.OP_CODES.iteritems()]:
            if idx >= 0 and (op_idx < 0 or idx <= op_idx):
                next_op_code = opc
                op_idx = idx
        return op_idx, next_op_code

    def _scan_string_single(self, nsstr, autostep):
        """Single node scan, returns (pat, list of rangesets)"""
        # ignore whitespace(s)
        node = nsstr.strip()
        if len(node) == 0:
            raise NodeSetParseError(nsstr, "empty node name")

        # single node parsing
        pfx_nd = [mobj.groups() for mobj in self.base_node_re.finditer(node)]
        pfx_nd = pfx_nd[:-1]
        if not pfx_nd:
            raise NodeSetParseError(node, "parse error")

        # pfx+sfx cannot be empty
        if len(pfx_nd) == 1 and len(pfx_nd[0][0]) == 0:
            raise NodeSetParseError(node, "empty node name")

        pat = ""
        rangesets = []
        for pfx, idx in pfx_nd:
            if idx:
                # optimization: process single index padding directly
                pad = 0
                if int(idx) != 0:
                    idxs = idx.lstrip("0")
                    if len(idx) - len(idxs) > 0:
                        pad = len(idx)
                    idxint = int(idxs)
                else:
                    if len(idx) > 1:
                        pad = len(idx)
                    idxint = 0
                if idxint > 1e100:
                    raise NodeSetParseRangeError( \
                        RangeSetParseError(idx, "invalid rangeset index"))
                # optimization: use numerical RangeSet constructor
                pat += "%s%%s" % pfx
                rangesets.append(RangeSet.fromone(idxint, pad, autostep))
            else:
                # undefined pad means no node index
                pat += pfx
        return pat, rangesets
    
    def _scan_string(self, nsstr, autostep):
        """Parsing engine's string scanner method (iterator)."""
        pat = nsstr.strip()
        # avoid misformatting
        if pat.find('%') >= 0:
            pat = pat.replace('%', '%%')
        next_op_code = 'update'
        while pat is not None:
            # Ignore whitespace(s) for convenience
            pat = pat.lstrip()

            rsets = []
            op_code = next_op_code

            op_idx, next_op_code = self._next_op(pat)
            bracket_idx = pat.find('[')

            # Check if the operator is after the bracket, or if there
            # is no operator at all but some brackets.
            if bracket_idx >= 0 and (op_idx > bracket_idx or op_idx < 0):
                # In this case, we have a pattern of potentially several
                # nodes.
                # Fill prefix, range and suffix from pattern
                # eg. "forbin[3,4-10]-ilo" -> "forbin", "3,4-10", "-ilo"
                newpat = ""
                sfx = pat
                while bracket_idx >= 0 and (op_idx > bracket_idx or op_idx < 0):
                    pfx, sfx = sfx.split('[', 1)
                    try:
                        rng, sfx = sfx.split(']', 1)
                    except ValueError:
                        raise NodeSetParseError(pat, "missing bracket")

                    # illegal closing bracket checks
                    if pfx.find(']') > -1:
                        raise NodeSetParseError(pfx, "illegal closing bracket")

                    if len(sfx) > 0:
                        bra_end = sfx.find(']')
                        bra_start = sfx.find('[')
                        if bra_start == -1:
                            bra_start = bra_end + 1
                        if bra_end >= 0 and bra_end < bra_start:
                            raise NodeSetParseError(sfx, \
                                                    "illegal closing bracket")
                    pfxlen = len(pfx)

                    # pfx + sfx cannot be empty
                    if pfxlen + len(sfx) == 0:
                        raise NodeSetParseError(pat, "empty node name")

                    # but pfx itself can
                    if pfxlen > 0:
                        pfx, pfxrvec = self._scan_string_single(pfx, autostep)
                        rsets += pfxrvec

                    # readahead for sanity check
                    bracket_idx = sfx.find('[', bracket_idx - pfxlen)
                    op_idx, next_op_code = self._next_op(sfx)

                    # Check for empty component or sequenced ranges
                    if len(pfx) == 0 and op_idx == 0:
                        raise NodeSetParseError(sfx, "empty node name before")\

                    if len(sfx) > 0 and sfx[0] in "0123456789[":
                        raise NodeSetParseError(sfx, \
                                "illegal sequenced numeric ranges")

                    newpat += "%s%%s" % pfx
                    try:
                        rsets.append(RangeSet(rng, autostep))
                    except RangeSetParseError, ex:
                        raise NodeSetParseRangeError(ex)

                # Check if we have a next op-separated node or pattern
                op_idx, next_op_code = self._next_op(sfx)
                if op_idx < 0:
                    pat = None
                else:
                    sfx, pat = sfx.split(self.OP_CODES[next_op_code], 1)

                # Ignore whitespace(s)
                sfx = sfx.rstrip()
                if sfx:
                    sfx, sfxrvec = self._scan_string_single(sfx, autostep)
                    newpat += sfx
                    rsets += sfxrvec

                # pfx + sfx cannot be empty
                if len(newpat) == 0:
                    raise NodeSetParseError(pat, "empty node name")

            else:
                # In this case, either there is no comma and no bracket,
                # or the bracket is after the comma, then just return
                # the node.
                if op_idx < 0:
                    node = pat
                    pat = None # break next time
                else:
                    node, pat = pat.split(self.OP_CODES[next_op_code], 1)
                
                # Check for illegal closing bracket
                if node.find(']') > -1:
                    raise NodeSetParseError(node, "illegal closing bracket")

                newpat, rsets = self._scan_string_single(node, autostep)

            if len(rsets) > 1:
                yield op_code, newpat, RangeSetND([rsets], None, autostep,
                                                  copy_rangeset=False)
            elif len(rsets) == 1:
                yield op_code, newpat, rsets[0]
            else:
                yield op_code, newpat, None


class NodeSet(NodeSetBase):
    """
    Iterable class of nodes with node ranges support.

    NodeSet creation examples:
       >>> nodeset = NodeSet()               # empty NodeSet
       >>> nodeset = NodeSet("cluster3")     # contains only cluster3
       >>> nodeset = NodeSet("cluster[5,10-42]")
       >>> nodeset = NodeSet("cluster[0-10/2]")
       >>> nodeset = NodeSet("cluster[0-10/2],othername[7-9,120-300]")

    NodeSet provides methods like update(), intersection_update() or
    difference_update() methods, which conform to the Python Set API.
    However, unlike RangeSet or standard Set, NodeSet is somewhat not
    so strict for convenience, and understands NodeSet instance or
    NodeSet string as argument. Also, there is no strict definition of
    one element, for example, it IS allowed to do:
        >>> nodeset = NodeSet("blue[1-50]")
        >>> nodeset.remove("blue[36-40]")
        >>> print nodeset
        blue[1-35,41-50]

    Additionally, the NodeSet class recognizes the "extended string
    pattern" which adds support for union (special character ","),
    difference ("!"), intersection ("&") and symmetric difference ("^")
    operations. String patterns are read from left to right, by
    proceeding any character operators accordinately.

    Extended string pattern usage examples:
        >>> nodeset = NodeSet("node[0-10],node[14-16]") # union
        >>> nodeset = NodeSet("node[0-10]!node[8-10]")  # difference
        >>> nodeset = NodeSet("node[0-10]&node[5-13]")  # intersection
        >>> nodeset = NodeSet("node[0-10]^node[5-13]")  # xor
    """

    _VERSION = 2

    def __init__(self, nodes=None, autostep=None, resolver=None):
        """
        Initialize a NodeSet.
        The `nodes' argument may be a valid nodeset string or a NodeSet
        object. If no nodes are specified, an empty NodeSet is created.
        """
        NodeSetBase.__init__(self)

        self._autostep = autostep

        # Set group resolver.
        if resolver in (RESOLVER_NOGROUP, RESOLVER_NOINIT):
            self._resolver = None
        else:
            self._resolver = resolver or RESOLVER_STD_GROUP

        # Initialize default parser.
        if resolver == RESOLVER_NOINIT:
            self._parser = None
        else:
            self._parser = ParsingEngine(self._resolver)
            self.update(nodes)

    @classmethod
    def _fromlist1(cls, nodelist, autostep=None, resolver=None):
        """Class method that returns a new NodeSet with single nodes from
        provided list (optimized constructor)."""
        inst = NodeSet(autostep=autostep, resolver=resolver)
        for single in nodelist:
            inst.update(inst._parser.parse_string_single(single, autostep))
        return inst

    @classmethod
    def fromlist(cls, nodelist, autostep=None, resolver=None):
        """Class method that returns a new NodeSet with nodes from provided
        list."""
        inst = NodeSet(autostep=autostep, resolver=resolver)
        inst.updaten(nodelist)
        return inst

    @classmethod
    def fromall(cls, groupsource=None, autostep=None, resolver=None):
        """Class method that returns a new NodeSet with all nodes from optional
        groupsource."""
        inst = NodeSet(autostep=autostep, resolver=resolver)
        if not inst._resolver:
            raise NodeSetExternalError("No node group resolver")
        # Fill this nodeset with all nodes found by resolver
        inst.updaten(inst._parser.all_nodes(groupsource))
        return inst

    def __getstate__(self):
        """Called when pickling: remove references to group resolver."""
        odict = self.__dict__.copy()
        odict['_version'] = NodeSet._VERSION
        del odict['_resolver']
        del odict['_parser']
        return odict

    def __setstate__(self, dic):
        """Called when unpickling: restore parser using non group
        resolver."""
        self.__dict__.update(dic)
        self._resolver = None
        self._parser = ParsingEngine(None)
        if getattr(self, '_version', 1) <= 1:
            # if setting state from first version, a conversion is needed to
            # support native RangeSetND
            old_patterns = self._patterns
            self._patterns = {}
            for pat, rangeset in sorted(old_patterns.iteritems()):
                if rangeset:
                    assert isinstance(rangeset, RangeSet)
                    rgs = str(rangeset)
                    if len(rangeset) > 1:
                        rgs = "[%s]" % rgs
                    self.update(pat % rgs)
                else:
                    self.update(pat)

    def copy(self):
        """Return a shallow copy of a NodeSet."""
        cpy = self.__class__(resolver=RESOLVER_NOINIT)
        dic = {}
        for pat, rangeset in self._patterns.iteritems():
            if rangeset is None:
                dic[pat] = None
            else:
                dic[pat] = rangeset.copy()
        cpy._patterns = dic
        cpy._autostep = self._autostep
        cpy._resolver = self._resolver
        cpy._parser = self._parser
        return cpy

    __copy__ = copy # For the copy module

    def _find_groups(self, node, namespace, allgroups):
        """Find groups of node by namespace."""
        if allgroups:
            # find node groups using in-memory allgroups
            for grp, nodeset in allgroups.iteritems():
                if node in nodeset:
                    yield grp
        else:
            # find node groups using resolver
            for group in self._resolver.node_groups(node, namespace):
                yield group

    def _groups2(self, groupsource=None, autostep=None):
        """Find node groups this nodeset belongs to. [private]"""
        if not self._resolver:
            raise NodeSetExternalError("No node group resolver")
        try:
            # Get all groups in specified group source.
            allgrplist = self._parser.grouplist(groupsource)
        except NodeUtils.GroupSourceException:
            # If list query failed, we still might be able to regroup
            # using reverse.
            allgrplist = None
        groups_info = {}
        allgroups = {}
        # Check for external reverse presence, and also use the
        # following heuristic: external reverse is used only when number
        # of groups is greater than the NodeSet size.
        if self._resolver.has_node_groups(groupsource) and \
            (not allgrplist or len(allgrplist) >= len(self)):
            # use external reverse
            pass
        else:
            if not allgrplist: # list query failed and no way to reverse!
                return groups_info # empty
            try:
                # use internal reverse: populate allgroups
                for grp in allgrplist:
                    nodelist = self._resolver.group_nodes(grp, groupsource)
                    allgroups[grp] = NodeSet(",".join(nodelist), \
                                             resolver=RESOLVER_NOGROUP)
            except NodeUtils.GroupSourceQueryFailed, exc:
                # External result inconsistency
                raise NodeSetExternalError("Unable to map a group " \
                        "previously listed\n\tFailed command: %s" % exc)

        # For each NodeSetBase in self, find its groups.
        for node in self._iterbase():
            for grp in self._find_groups(node, groupsource, allgroups):
                if grp not in groups_info:
                    nodes = self._parser.parse_group(grp, groupsource, autostep)
                    groups_info[grp] = (1, nodes)
                else:
                    i, nodes = groups_info[grp]
                    groups_info[grp] = (i + 1, nodes)
        return groups_info

    def groups(self, groupsource=None, noprefix=False):
        """Find node groups this nodeset belongs to.

        Return a dictionary of the form:
            group_name => (group_nodeset, contained_nodeset)

        Group names are always prefixed with "@". If groupsource is provided,
        they are prefixed with "@groupsource:", unless noprefix is True.
        """
        groups = self._groups2(groupsource, self._autostep)
        result = {}
        for grp, (_, nsb) in groups.iteritems():
            if groupsource and not noprefix:
                key = "@%s:%s" % (groupsource, grp)
            else:
                key = "@" + grp
            result[key] = (NodeSet(nsb, resolver=RESOLVER_NOGROUP), \
                           self.intersection(nsb))
        return result

    def regroup(self, groupsource=None, autostep=None, overlap=False,
                noprefix=False):
        """Regroup nodeset using node groups.

        Try to find fully matching node groups (within specified groupsource)
        and return a string that represents this node set (containing these
        potential node groups). When no matching node groups are found, this
        method returns the same result as str()."""
        groups = self._groups2(groupsource, autostep)
        if not groups:
            return str(self)

        # Keep only groups that are full.
        fulls = []
        for k, (i, nodes) in groups.iteritems():
            assert i <= len(nodes)
            if i == len(nodes):
                fulls.append((i, k))

        rest = NodeSet(self, resolver=RESOLVER_NOGROUP)
        regrouped = NodeSet(resolver=RESOLVER_NOGROUP)

        bigalpha = lambda x, y: cmp(y[0], x[0]) or cmp(x[1], y[1])

        # Build regrouped NodeSet by selecting largest groups first.
        for _, grp in sorted(fulls, cmp=bigalpha):
            if not overlap and groups[grp][1] not in rest:
                continue
            if groupsource and not noprefix:
                regrouped.update("@%s:%s" % (groupsource, grp))
            else:
                regrouped.update("@" + grp)
            rest.difference_update(groups[grp][1])
            if not rest:
                return str(regrouped)

        if regrouped:
            return "%s,%s" % (regrouped, rest)

        return str(rest)

    def issubset(self, other):
        """
        Report whether another nodeset contains this nodeset.
        """
        nodeset = self._parser.parse(other, self._autostep)
        return NodeSetBase.issuperset(nodeset, self)

    def issuperset(self, other):
        """
        Report whether this nodeset contains another nodeset.
        """
        nodeset = self._parser.parse(other, self._autostep)
        return NodeSetBase.issuperset(self, nodeset)

    def __getitem__(self, index):
        """
        Return the node at specified index or a subnodeset when a slice
        is specified.
        """
        base = NodeSetBase.__getitem__(self, index)
        if not isinstance(base, NodeSetBase):
            return base
        # return a real NodeSet
        inst = NodeSet(autostep=self._autostep, resolver=self._resolver)
        inst._patterns = base._patterns
        return inst

    def split(self, nbr):
        """
        Split the nodeset into nbr sub-nodesets (at most). Each
        sub-nodeset will have the same number of elements more or
        less 1. Current nodeset remains unmodified.

        >>> for nodeset in NodeSet("foo[1-5]").split(3):
        ...     print nodeset
        foo[1-2]
        foo[3-4]
        foo5
        """
        assert(nbr > 0)

        # We put the same number of element in each sub-nodeset.
        slice_size = len(self) / nbr
        left = len(self) % nbr

        begin = 0
        for i in range(0, min(nbr, len(self))):
            length = slice_size + int(i < left)
            yield self[begin:begin + length]
            begin += length

    def update(self, other):
        """
        s.update(t) returns nodeset s with elements added from t.
        """
        nodeset = self._parser.parse(other, self._autostep)
        NodeSetBase.update(self, nodeset)

    def intersection_update(self, other):
        """
        s.intersection_update(t) returns nodeset s keeping only
        elements also found in t.
        """
        nodeset = self._parser.parse(other, self._autostep)
        NodeSetBase.intersection_update(self, nodeset)

    def difference_update(self, other, strict=False):
        """
        s.difference_update(t) returns nodeset s after removing
        elements found in t. If strict is True, raise KeyError
        if an element cannot be removed.
        """
        nodeset = self._parser.parse(other, self._autostep)
        NodeSetBase.difference_update(self, nodeset, strict)

    def symmetric_difference_update(self, other):
        """
        s.symmetric_difference_update(t) returns nodeset s keeping all
        nodes that are in exactly one of the nodesets.
        """
        nodeset = self._parser.parse(other, self._autostep)
        NodeSetBase.symmetric_difference_update(self, nodeset)


def expand(pat):
    """
    Commodity function that expands a nodeset pattern into a list of nodes.
    """
    return list(NodeSet(pat))

def fold(pat):
    """
    Commodity function that clean dups and fold provided pattern with ranges
    and "/step" support.
    """
    return str(NodeSet(pat))

def grouplist(namespace=None, resolver=None):
    """
    Commodity function that retrieves the list of raw groups for a specified
    group namespace (or use default namespace).
    Group names are not prefixed with "@".
    """
    return ParsingEngine(resolver or RESOLVER_STD_GROUP).grouplist(namespace)

def std_group_resolver():
    """
    Get the current resolver used for standard "@" group resolution.
    """
    return RESOLVER_STD_GROUP

def set_std_group_resolver(new_resolver):
    """
    Override the resolver used for standard "@" group resolution. The
    new resolver should be either an instance of
    NodeUtils.GroupResolver or None. In the latter case, the group
    resolver is restored to the default one.
    """
    global RESOLVER_STD_GROUP
    RESOLVER_STD_GROUP = new_resolver or _DEF_RESOLVER_STD_GROUP


########NEW FILE########
__FILENAME__ = NodeUtils
# Copyright CEA/DAM/DIF (2010, 2012, 2013, 2014)
#  Contributors:
#   Stephane THIELL <stephane.thiell@cea.fr>
#   Aurelien DEGREMONT <aurelien.degremont@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
Cluster nodes utility module

The NodeUtils module is a ClusterShell helper module that provides
supplementary services to manage nodes in a cluster. It is primarily
designed to enhance the NodeSet module providing some binding support
to external node groups sources in separate namespaces (example of
group sources are: files, jobs scheduler, custom scripts, etc.).
"""

import glob
import os
import sys
import time

from ConfigParser import ConfigParser, NoOptionError, NoSectionError
from string import Template
from subprocess import Popen, PIPE


class GroupSourceException(Exception):
    """Base GroupSource exception"""
    def __init__(self, message, group_source):
        Exception.__init__(self, message)
        self.group_source = group_source

class GroupSourceNoUpcall(GroupSourceException):
    """Raised when upcall is not available"""

class GroupSourceQueryFailed(GroupSourceException):
    """Raised when a query failed (eg. no group found)"""

class GroupResolverError(Exception):
    """Base GroupResolver error"""

class GroupResolverSourceError(GroupResolverError):
    """Raised when upcall is not available"""

class GroupResolverIllegalCharError(GroupResolverError):
    """Raised when an illegal group character is encountered"""

class GroupResolverConfigError(GroupResolverError):
    """Raised when a configuration error is encountered"""


_DEFAULT_CACHE_DELAY = 3600

class GroupSource(object):
    """
    GroupSource class managing external calls for nodegroup support.

    Upcall results are cached for a customizable amount of time. This is
    controled by `cache_delay' attribute. Default is 3600 seconds.
    """

    def __init__(self, name, map_upcall, all_upcall=None,
                 list_upcall=None, reverse_upcall=None, cfgdir=None,
                 cache_delay=None):
        self.name = name
        self.verbosity = 0
        self.cfgdir = cfgdir

        # Supported external upcalls
        self.upcalls = {}
        self.upcalls['map'] = map_upcall
        if all_upcall:
            self.upcalls['all'] = all_upcall
        if list_upcall:
            self.upcalls['list'] = list_upcall
        if reverse_upcall:
            self.upcalls['reverse'] = reverse_upcall

        # Cache upcall data
        self.cache_delay = cache_delay or _DEFAULT_CACHE_DELAY
        self._cache = {}
        self.clear_cache()

    def clear_cache(self):
        """
        Remove all previously cached upcall results whatever their lifetime is.
        """
        self._cache = {
                'map':     {},
                'reverse': {}
            }

    def _verbose_print(self, msg):
        """Print msg depending on the verbosity level."""
        if self.verbosity > 0:
            print >> sys.stderr, "%s<%s> %s" % \
                (self.__class__.__name__, self.name, msg)

    def _upcall_read(self, cmdtpl, args=dict()):
        """
        Invoke the specified upcall command, raise an Exception if
        something goes wrong and return the command output otherwise.
        """
        cmdline = Template(self.upcalls[cmdtpl]).safe_substitute(args)
        self._verbose_print("EXEC '%s'" % cmdline)
        proc = Popen(cmdline, stdout=PIPE, shell=True, cwd=self.cfgdir)
        output = proc.communicate()[0].strip()
        self._verbose_print("READ '%s'" % output)
        if proc.returncode != 0:
            self._verbose_print("ERROR '%s' returned %d" % (cmdline, \
                proc.returncode))
            raise GroupSourceQueryFailed(cmdline, self)
        return output

    def _upcall_cache(self, upcall, cache, key, **args):
        """
        Look for `key' in provided `cache'. If not found, call the
        corresponding `upcall'.

        If `key' is missing, it is added to provided `cache'. Each entry in a
        cache is kept only for a limited time equal to self.cache_delay .
        """
        if not self.upcalls.get(upcall):
            raise GroupSourceNoUpcall(upcall, self)

        # Purge expired data from cache
        if key in cache and cache[key][1] < time.time():
            self._verbose_print("PURGE EXPIRED (%d)'%s'" % (cache[key][1], key))
            del cache[key]

        # Fetch the data if unknown of just purged
        if key not in cache:
            timestamp = time.time() + self.cache_delay
            cache[key] = (self._upcall_read(upcall, args), timestamp)

        return cache[key][0]

    def resolv_map(self, group):
        """
        Get nodes from group 'group', using the cached value if
        available.
        """
        return self._upcall_cache('map', self._cache['map'], group,
                                  GROUP=group)

    def resolv_list(self):
        """
        Return a list of all group names for this group source, using
        the cached value if available.
        """
        return self._upcall_cache('list', self._cache, 'list')
    
    def resolv_all(self):
        """
        Return the content of special group ALL, using the cached value
        if available.
        """
        return self._upcall_cache('all', self._cache, 'all')

    def resolv_reverse(self, node):
        """
        Return the group name matching the provided node, using the
        cached value if available.
        """
        return self._upcall_cache('reverse', self._cache['reverse'], node,
                                  NODE=node)



class GroupResolver(object):
    """
    Base class GroupResolver that aims to provide node/group resolution
    from multiple GroupSources.

    A GroupResolver object might be initialized with a default
    GroupSource object, that is later used when group resolution is
    requested with no source information. As of version 1.7, a set of
    illegal group characters may also be provided for sanity check
    (raising GroupResolverIllegalCharError when found).
    """
    
    def __init__(self, default_source=None, illegal_chars=None):
        """Initialize GroupResolver object."""
        self._sources = {}
        self._default_source = default_source
        self.illegal_chars = illegal_chars or set()
        if default_source:
            self._sources[default_source.name] = default_source
            
    def set_verbosity(self, value):
        """Set debugging verbosity value. """
        for source in self._sources.itervalues():
            source.verbosity = value

    def add_source(self, group_source):
        """Add a GroupSource to this resolver."""
        if group_source.name in self._sources:
            raise ValueError("GroupSource '%s': name collision" % \
                             group_source.name)
        self._sources[group_source.name] = group_source

    def sources(self):
        """Get the list of all resolver source names. """
        return self._sources.keys()

    def _list_nodes(self, source, what, *args):
        """Helper method that returns a list of results (nodes) when
        the source is defined."""
        result = []
        assert source
        raw = getattr(source, 'resolv_%s' % what)(*args)
        for line in raw.splitlines():
            [result.append(x) for x in line.strip().split()]
        return result

    def _list_groups(self, source, what, *args):
        """Helper method that returns a list of results (groups) when
        the source is defined."""
        result = []
        assert source
        raw = getattr(source, 'resolv_%s' % what)(*args)
        for line in raw.splitlines():
            for grpstr in line.strip().split():
                if self.illegal_chars.intersection(grpstr):
                    raise GroupResolverIllegalCharError( \
                        ' '.join(self.illegal_chars.intersection(grpstr)))
                result.append(grpstr)
        return result

    def _source(self, namespace):
        """Helper method that returns the source by namespace name."""
        if not namespace:
            source = self._default_source
        else:
            source = self._sources.get(namespace)
        if not source:
            raise GroupResolverSourceError(namespace or "<default>")
        return source
        
    def group_nodes(self, group, namespace=None):
        """
        Find nodes for specified group name and optional namespace.
        """
        source = self._source(namespace)
        return self._list_nodes(source, 'map', group)

    def all_nodes(self, namespace=None):
        """
        Find all nodes. You may specify an optional namespace.
        """
        source = self._source(namespace)
        return self._list_nodes(source, 'all')

    def grouplist(self, namespace=None):
        """
        Get full group list. You may specify an optional
        namespace.
        """
        source = self._source(namespace)
        return self._list_groups(source, 'list')

    def has_node_groups(self, namespace=None):
        """
        Return whether finding group list for a specified node is
        supported by the resolver (in optional namespace).
        """
        try:
            return 'reverse' in self._source(namespace).upcalls
        except GroupResolverSourceError:
            return False

    def node_groups(self, node, namespace=None):
        """
        Find group list for specified node and optional namespace.
        """
        source = self._source(namespace)
        return self._list_groups(source, 'reverse', node)


class GroupResolverConfig(GroupResolver):
    """
    GroupResolver class that is able to automatically setup its
    GroupSource's from a configuration file. This is the default
    resolver for NodeSet.
    """

    def __init__(self, configfile, illegal_chars=None):
        """
        """
        GroupResolver.__init__(self, illegal_chars=illegal_chars)

        self.default_sourcename = None

        self.config = ConfigParser()
        self.config.read(configfile)
        # Get config file sections
        groupscfgs = {}
        configfile_dirname = os.path.dirname(configfile)
        for section in self.config.sections():
            if section != 'Main':
                groupscfgs[section] = (self.config, configfile_dirname)
        try:
            self.groupsdir = self.config.get('Main', 'groupsdir')
            for groupsdir in self.groupsdir.split():
                # support relative-to-dirname(groups.conf) groupsdir
                groupsdir = os.path.normpath(os.path.join(configfile_dirname, \
                                                          groupsdir))
                if not os.path.isdir(groupsdir):
                    if not os.path.exists(groupsdir):
                        continue
                    raise GroupResolverConfigError("Defined groupsdir %s " \
                            "is not a directory" % groupsdir)
                for groupsfn in sorted(glob.glob('%s/*.conf' % groupsdir)):
                    grpcfg = ConfigParser()
                    grpcfg.read(groupsfn) # ignore files that cannot be read
                    for section in grpcfg.sections():
                        if section in groupscfgs:
                            raise GroupResolverConfigError("Group source " \
                                "\"%s\" re-defined in %s" % (section, groupsfn))
                        groupscfgs[section] = (grpcfg, groupsdir)
        except (NoSectionError, NoOptionError):
            pass

        try:
            self.default_sourcename = self.config.get('Main', 'default')
            if self.default_sourcename and self.default_sourcename \
                                            not in groupscfgs.keys():
                raise GroupResolverConfigError("Default group source not " \
                    "found: \"%s\"" % self.default_sourcename)
        except (NoSectionError, NoOptionError):
            pass

        if not groupscfgs:
            return

        # When not specified, select a random section.
        if not self.default_sourcename:
            self.default_sourcename = groupscfgs.keys()[0]

        try:
            for section, (cfg, cfgdir) in groupscfgs.iteritems():
                # only map is a mandatory upcall
                map_upcall = cfg.get(section, 'map', True)
                all_upcall = list_upcall = reverse_upcall = delay = None
                if cfg.has_option(section, 'all'):
                    all_upcall = cfg.get(section, 'all', True)
                if cfg.has_option(section, 'list'):
                    list_upcall = cfg.get(section, 'list', True)
                if cfg.has_option(section, 'reverse'):
                    reverse_upcall = cfg.get(section, 'reverse', True)
                if cfg.has_option(section, 'cache_delay'):
                    delay = float(cfg.get(section, 'cache_delay', True))

                self.add_source(GroupSource(section, map_upcall, all_upcall, \
                                    list_upcall, reverse_upcall, cfgdir, delay))
        except (NoSectionError, NoOptionError), exc:
            raise GroupResolverConfigError(str(exc))

    def _source(self, namespace):
        return GroupResolver._source(self, namespace or self.default_sourcename)

    def sources(self):
        """
        Get the list of all resolver source names (default source is always
        first).
        """
        srcs = GroupResolver.sources(self)
        if srcs:
            srcs.remove(self.default_sourcename)
            srcs.insert(0, self.default_sourcename)
        return srcs



########NEW FILE########
__FILENAME__ = Propagation
#!/usr/bin/env python
#
# Copyright CEA/DAM/DIF (2010, 2011, 2012)
#  Contributor: Henri DOREAU <henri.doreau@cea.fr>
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
ClusterShell Propagation module. Use the topology tree to send commands
through gateways and gather results.
"""

import logging

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Communication import Channel
from ClusterShell.Communication import ControlMessage, StdOutMessage
from ClusterShell.Communication import StdErrMessage, RetcodeMessage
from ClusterShell.Communication import RoutedMessageBase, EndMessage
from ClusterShell.Communication import ConfigurationMessage, TimeoutMessage


class RouteResolvingError(Exception):
    """error raised on invalid conditions during routing operations"""

class PropagationTreeRouter(object):
    """performs routes resolving operations within a propagation tree.
    This object provides a next_hop method, that will look for the best
    directly connected node to use to forward a message to a remote
    node.

    Upon instanciation, the router will parse the topology tree to
    generate its routing table.
    """
    def __init__(self, root, topology, fanout=0):
        self.root = root
        self.topology = topology
        self.fanout = fanout
        self.nodes_fanin = {}
        self.table = None

        self.table_generate(root, topology)
        self._unreachable_hosts = NodeSet()

    def table_generate(self, root, topology):
        """The router relies on a routing table. The keys are the
        destination nodes and the values are the next hop gateways to
        use to reach these nodes.
        """
        self.table = {}
        root_group = None

        for entry in topology.groups:
            if root in entry.nodeset:
                root_group = entry
                break

        if root_group is None:
            raise RouteResolvingError('Invalid admin node: %s' % root)

        for group in root_group.children():
            self.table[group.nodeset] = NodeSet()
            stack = [group]
            while len(stack) > 0:
                curr = stack.pop()
                self.table[group.nodeset].add(curr.children_ns())
                stack += curr.children()

        # reverse table (it was crafted backward)
        self.table = dict((v, k) for k, v in self.table.iteritems())

    def dispatch(self, dst):
        """dispatch nodes from a target nodeset to the directly
        connected gateways.

        The method acts as an iterator, returning a gateway and the
        associated hosts. It should provide a rather good load balancing
        between the gateways.
        """
        # Check for directly connected targets
        res = [tmp & dst for tmp in self.table.values()]
        nexthop = NodeSet()
        [nexthop.add(x) for x in res]
        if len(nexthop) > 0:
            yield nexthop, nexthop

        # Check for remote targets, that require a gateway to be reached
        for network in self.table.iterkeys():
            dst_inter = network & dst
            dst.difference_update(dst_inter)
            for host in dst_inter.nsiter():
                yield self.next_hop(host), host

    def next_hop(self, dst):
        """perform the next hop resolution. If several hops are
        available, then, the one with the least number of current jobs
        will be returned
        """
        if dst in self._unreachable_hosts:
            raise RouteResolvingError(
                'Invalid destination: %s, host is unreachable' % dst)

        # can't resolve if source == destination
        if self.root == dst:
            raise RouteResolvingError(
                'Invalid resolution request: %s -> %s' % (self.root, dst))

        ## ------------------
        # the routing table is organized this way:
        # 
        #  NETWORK    | NEXT HOP
        # ------------+-----------
        # node[0-9]   | gateway0
        # node[10-19] | gateway[1-2]
        #            ...
        # ---------
        for network, nexthops in self.table.iteritems():
            # destination contained in current network
            if dst in network:
                res = self._best_next_hop(nexthops)
                if res is None:
                    raise RouteResolvingError('No route available to %s' % \
                        str(dst))
                self.nodes_fanin[res] += len(dst)
                return res
            # destination contained in current next hops (ie. directly
            # connected)
            if dst in nexthops:
                return dst

        raise RouteResolvingError(
            'No route from %s to host %s' % (self.root, dst))

    def mark_unreachable(self, dst):
        """mark node dst as unreachable and don't advertise routes
        through it anymore. The cache will be updated only when
        necessary to avoid performing expensive traversals.
        """
        # Simply mark dst as unreachable in a dedicated NodeSet. This
        # list will be consulted by the resolution method
        self._unreachable_hosts.add(dst)

    def _best_next_hop(self, candidates):
        """find out a good next hop gateway"""
        backup = None
        backup_connections = 1e400 # infinity

        candidates = candidates.difference(self._unreachable_hosts)

        for host in candidates:
            # the router tracks established connections in the
            # nodes_fanin table to avoid overloading a gateway
            connections = self.nodes_fanin.setdefault(host, 0)
            # FIXME
            #if connections < self.fanout:
            #    # currently, the first one is the best
            #    return host
            if backup_connections > connections:
                backup = host
                backup_connections = connections
        return backup


class PropagationChannel(Channel):
    """Admin node propagation logic. Instances are able to handle
    incoming messages from a directly connected gateway, process them
    and reply.

    In order to take decisions, the instance acts as a finite states
    machine, whose current state evolves according to received data.

    -- INTERNALS --
    Instance can be in one of the 4 different states:
      - init (implicit)
        This is the very first state. The instance enters the init
        state at start() method, and will then send the configuration
        to the remote node.  Once the configuration is sent away, the
        state changes to cfg.

      - cfg
        During this second state, the instance will wait for a valid
        acknowledgement from the gateway to the previously sent
        configuration message. If such a message is delivered, the
        control message (the one that contains the actions to perform)
        is sent, and the state is set to ctl.

      - ctl
        Third state, the instance is waiting for a valid ack for from
        the gateway to the ctl packet. Then, the state switch to gtr
        (gather).

      - gtr
        Final state: wait for results from the subtree and store them.
    """
    def __init__(self, task):
        """
        """
        Channel.__init__(self)
        self.task = task
        self.workers = {}

        self.current_state = None
        self.states = {
            'STATE_CFG': self._state_config,
            'STATE_CTL': self._state_control,
            #'STATE_GTR': self._state_gather,
        }

        self._history = {} # track informations about previous states
        self._sendq = []
        self.logger = logging.getLogger(__name__)

    def start(self):
        """initial actions"""
        #print '[DBG] start'
        self._open()
        cfg = ConfigurationMessage()
        #cfg.data_encode(self.task._default_topology())
        cfg.data_encode(self.task.topology)
        self._history['cfg_id'] = cfg.msgid
        self.send(cfg)
        self.current_state = self.states['STATE_CFG']

    def recv(self, msg):
        """process incoming messages"""
        self.logger.debug("[DBG] rcvd from: %s" % str(msg))
        if msg.ident == EndMessage.ident:
            #??#self.ptree.notify_close()
            self.logger.debug("closing")
            # abort worker (now working)
            self.worker.abort()
        else:
            self.current_state(msg)

    def shell(self, nodes, command, worker, timeout, stderr, gw_invoke_cmd):
        """command execution through channel"""
        self.logger.debug("shell nodes=%s timeout=%f worker=%s" % \
            (nodes, timeout, id(worker)))

        self.workers[id(worker)] = worker
        
        ctl = ControlMessage(id(worker))
        ctl.action = 'shell'
        ctl.target = nodes

        info = self.task._info.copy()
        info['debug'] = False
        
        ctl_data = {
            'cmd': command,
            'invoke_gateway': gw_invoke_cmd, # XXX
            'taskinfo': info, #self.task._info,
            'stderr': stderr,
            'timeout': timeout,
        }
        ctl.data_encode(ctl_data)

        self._history['ctl_id'] = ctl.msgid
        if self.current_state == self.states['STATE_CTL']:
            # send now if channel state is CTL
            self.send(ctl)
        else:
            self._sendq.append(ctl)
    
    def _state_config(self, msg):
        """handle incoming messages for state 'propagate configuration'"""
        if msg.type == 'ACK': # and msg.ack == self._history['cfg_id']:
            self.current_state = self.states['STATE_CTL']
            for ctl in self._sendq:
                self.send(ctl)
        else:
            print str(msg)

    def _state_control(self, msg):
        """handle incoming messages for state 'control'"""
        if msg.type == 'ACK': # and msg.ack == self._history['ctl_id']:
            #self.current_state = self.states['STATE_GTR']
            self.logger.debug("PropChannel: _state_control -> STATE_GTR")
        elif isinstance(msg, RoutedMessageBase):
            metaworker = self.workers[msg.srcid]
            if msg.type == StdOutMessage.ident:
                if metaworker.eh:
                    nodeset = NodeSet(msg.nodes)
                    self.logger.debug("StdOutMessage: \"%s\"", msg.data)
                    for line in msg.data.splitlines():
                        for node in nodeset:
                            metaworker._on_node_msgline(node, line)
            elif msg.type == StdErrMessage.ident:
                if metaworker.eh:
                    nodeset = NodeSet(msg.nodes)
                    self.logger.debug("StdErrMessage: \"%s\"", msg.data)
                    for line in msg.data.splitlines():
                        for node in nodeset:
                            metaworker._on_node_errline(node, line)
            elif msg.type == RetcodeMessage.ident:
                rc = msg.retcode
                for node in NodeSet(msg.nodes):
                    metaworker._on_node_rc(node, rc)
            elif msg.type == TimeoutMessage.ident:
                self.logger.debug("TimeoutMessage for %s", msg.nodes)
                for node in NodeSet(msg.nodes):
                    metaworker._on_node_timeout(node)
        else:
            self.logger.debug("PropChannel: _state_gather unhandled msg %s" % \
                              msg)
        """
        return
        if self.ptree.upchannel is not None:
            self.logger.debug("_state_gather ->upchan %s" % msg)
            self.ptree.upchannel.send(msg) # send to according event handler passed by shell()
        else:
            assert False
        """
 
    def ev_close(self, worker):
        worker.flush_buffers()


########NEW FILE########
__FILENAME__ = RangeSet
#
# Copyright CEA/DAM/DIF (2012, 2013, 2014)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#  Contributor: Aurelien DEGREMONT <aurelien.degremont@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
Cluster range set module.

Instances of RangeSet provide similar operations than the builtin set type,
extended to support cluster ranges-like format and stepping support ("0-8/2").
"""

from operator import mul

try:
    from itertools import product
except:
    # itertools.product : new in Python 2.6
    def product(*args, **kwds):
        """Cartesian product of input iterables."""
        pools = map(tuple, args) * kwds.get('repeat', 1)
        result = [[]]
        for pool in pools:
            result = [x+[y] for x in result for y in pool]
        for prod in result:
            yield tuple(prod)

__all__ = ['RangeSetException',
           'RangeSetParseError',
           'RangeSetPaddingError',
           'RangeSet',
           'RangeSetND']


class RangeSetException(Exception):
    """Base RangeSet exception class."""

class RangeSetParseError(RangeSetException):
    """Raised when RangeSet parsing cannot be done properly."""
    def __init__(self, part, msg):
        if part:
            msg = "%s : \"%s\"" % (msg, part)
        RangeSetException.__init__(self, msg)
        # faulty subrange; this allows you to target the error
        self.part = part

class RangeSetPaddingError(RangeSetParseError):
    """Raised when a fatal padding incoherency occurs"""
    def __init__(self, part, msg):
        RangeSetParseError.__init__(self, part, "padding mismatch (%s)" % msg)


class RangeSet(set):
    """
    Mutable set of cluster node indexes featuring a fast range-based API.
    
    This class aims to ease the management of potentially large cluster range
    sets and is used by the NodeSet class.

    RangeSet basic constructors:
       >>> rset = RangeSet()            # empty RangeSet
       >>> rset = RangeSet("5,10-42")   # contains 5, 10 to 42
       >>> rset = RangeSet("0-10/2")    # contains 0, 2, 4, 6, 8, 10

    Since v1.6, any iterable of integers can be specified as first argument:
       >>> RangeSet([3, 6, 8, 7, 1])
       1,3,6-8
       >>> rset2 = RangeSet(rset)

    Padding of ranges (eg. "003-009") can be managed through a public RangeSet
    instance variable named padding. It may be changed at any time. Since v1.6,
    padding is a simple display feature per RangeSet object, thus current
    padding value is not taken into account when computing set operations.
    Since v1.6, RangeSet is itself an iterator over its items as integers
    (instead of strings). To iterate over string items as before (with
    optional padding), you can now use the RangeSet.striter() method.

    RangeSet provides methods like union(), intersection(), difference(),
    symmetric_difference() and their in-place versions update(),
    intersection_update(), difference_update(),
    symmetric_difference_update() which conform to the Python Set API.
    """
    _VERSION = 3    # serial version number

    # define __new__() to workaround built-in set subclassing with Python 2.4
    def __new__(cls, pattern=None, autostep=None):
        """Object constructor"""
        return set.__new__(cls)
        
    def __init__(self, pattern=None, autostep=None):
        """Initialize RangeSet with optional string pattern and autostep
        threshold.
        """
        if pattern is None or isinstance(pattern, str):
            set.__init__(self)
        else:
            set.__init__(self, pattern)

        if isinstance(pattern, RangeSet):
            self._autostep = pattern._autostep
            self.padding = pattern.padding
        else:
            self._autostep = None
            self.padding = None
        self.autostep = autostep

        if isinstance(pattern, str):
            self._parse(pattern)

    def _parse(self, pattern):
        """Parse string of comma-separated x-y/step -like ranges"""
        # Comma separated ranges
        if pattern.find(',') < 0:
            subranges = [pattern]
        else:
            subranges = pattern.split(',')

        for subrange in subranges:
            if subrange.find('/') < 0:
                step = 1
                baserange = subrange
            else:
                baserange, step = subrange.split('/', 1)

            try:
                step = int(step)
            except ValueError:
                raise RangeSetParseError(subrange,
                        "cannot convert string to integer")

            if baserange.find('-') < 0:
                if step != 1:
                    raise RangeSetParseError(subrange,
                            "invalid step usage")
                begin = end = baserange
            else:
                begin, end = baserange.split('-', 1)

            # compute padding and return node range info tuple
            try:
                pad = 0
                if int(begin) != 0:
                    begins = begin.lstrip("0")
                    if len(begin) - len(begins) > 0:
                        pad = len(begin)
                    start = int(begins)
                else:
                    if len(begin) > 1:
                        pad = len(begin)
                    start = 0
                if int(end) != 0:
                    ends = end.lstrip("0")
                else:
                    ends = end
                stop = int(ends)
            except ValueError:
                raise RangeSetParseError(subrange,
                        "cannot convert string to integer")

            # check preconditions
            if stop > 1e100 or start > stop or step < 1:
                raise RangeSetParseError(subrange,
                                         "invalid values in range")

            self.add_range(start, stop + 1, step, pad)
        
    @classmethod
    def fromlist(cls, rnglist, autostep=None):
        """Class method that returns a new RangeSet with ranges from provided
        list."""
        inst = RangeSet(autostep=autostep)
        inst.updaten(rnglist)
        return inst

    @classmethod
    def fromone(cls, index, pad=0, autostep=None):
        """Class method that returns a new RangeSet of one single item or
        a single range (from integer or slice object)."""
        inst = RangeSet(autostep=autostep)
        # support slice object with duck-typing
        try:
            inst.add(index, pad)
        except TypeError:
            if not index.stop:
                raise ValueError("Invalid range upper limit (%s)" % index.stop)
            inst.add_range(index.start or 0, index.stop, index.step or 1, pad)
        return inst

    def get_autostep(self):
        """Get autostep value (property)"""
        if self._autostep >= 1E100:
            return None
        else:
            return self._autostep + 1

    def set_autostep(self, val):
        """Set autostep value (property)"""
        if val is None:
            # disabled by default for pdsh compat (+inf is 1E400, but a bug in
            # python 2.4 makes it impossible to be pickled, so we use less)
            # NOTE: Later, we could consider sys.maxint here
            self._autostep = 1E100
        else:
            # - 1 because user means node count, but we means real steps
            self._autostep = int(val) - 1

    autostep = property(get_autostep, set_autostep)
    
    def dim(self):
        """Get the number of dimensions of this RangeSet object. Common
        method with RangeSetND.  Here, it will always return 1 unless
        the object is empty, in that case it will return 0."""
        return int(len(self) > 0)

    def _sorted(self):
        """Get sorted list from inner set."""
        return sorted(set.__iter__(self))

    def __iter__(self):
        """Iterate over each element in RangeSet."""
        return iter(self._sorted())

    def striter(self):
        """Iterate over each (optionally padded) string element in RangeSet."""
        pad = self.padding or 0
        for i in self._sorted():
            yield "%0*d" % (pad, i)

    def contiguous(self):
        """Object-based iterator over contiguous range sets."""
        pad = self.padding or 0
        for sli in self._contiguous_slices():
            yield RangeSet.fromone(slice(sli.start, sli.stop, sli.step), pad)

    def __reduce__(self):
        """Return state information for pickling."""
        return self.__class__, (str(self),), \
            { 'padding': self.padding, \
              '_autostep': self._autostep, \
              '_version' : RangeSet._VERSION }

    def __setstate__(self, dic):
        """called upon unpickling"""
        self.__dict__.update(dic)
        if getattr(self, '_version', 0) < RangeSet._VERSION:
            # unpickle from old version?
            if getattr(self, '_version', 0) <= 1:
                # v1 (no object versioning) - CSv1.3
                setattr(self, '_ranges', [(slice(start, stop + 1, step), pad) \
                    for start, stop, step, pad in getattr(self, '_ranges')])
            elif hasattr(self, '_ranges'):
                # v2 - CSv1.4-1.5
                self_ranges = getattr(self, '_ranges')
                if self_ranges and type(self_ranges[0][0]) is not slice:
                    # workaround for object pickled from Python < 2.5
                    setattr(self, '_ranges', [(slice(start, stop, step), pad) \
                        for (start, stop, step), pad in self_ranges])
            # convert to v3
            for sli, pad in getattr(self, '_ranges'):
                self.add_range(sli.start, sli.stop, sli.step, pad)
            delattr(self, '_ranges')
            delattr(self, '_length')

    def _strslices(self):
        """Stringify slices list (x-y/step format)"""
        pad = self.padding or 0
        for sli in self.slices():
            if sli.start + 1 == sli.stop:
                yield "%0*d" % (pad, sli.start)
            else:
                assert sli.step >= 0, "Internal error: sli.step < 0"
                if sli.step == 1:
                    yield "%0*d-%0*d" % (pad, sli.start, pad, sli.stop - 1)
                else:
                    yield "%0*d-%0*d/%d" % (pad, sli.start, pad, sli.stop - 1, \
                                            sli.step)
        
    def __str__(self):
        """Get comma-separated range-based string (x-y/step format)."""
        return ','.join(self._strslices())

    # __repr__ is the same as __str__ as it is a valid expression that
    # could be used to recreate a RangeSet with the same value
    __repr__ = __str__

    def _contiguous_slices(self):
        """Internal iterator over contiguous slices in RangeSet."""
        k = j = None
        for i in self._sorted():
            if k is None:
                k = j = i
            if i - j > 1:
                yield slice(k, j + 1, 1)
                k = i
            j = i
        if k is not None:
            yield slice(k, j + 1, 1)

    def _folded_slices(self):
        """Internal generator that is able to retrieve ranges organized by
        step."""
        if len(self) == 0:
            return

        prng = None         # pending range
        istart = None       # processing starting indice
        step = 0            # processing step
        for sli in self._contiguous_slices():
            start = sli.start
            stop = sli.stop
            unitary = (start + 1 == stop)   # one indice?
            if istart is None:  # first loop
                if unitary:
                    istart = start
                else:
                    prng = [start, stop, 1]
                    istart = stop - 1
                i = k = istart
            elif step == 0:        # istart is set but step is unknown
                if not unitary:
                    if prng is not None:
                        # yield and replace pending range
                        yield slice(*prng)
                    else:
                        yield slice(istart, istart + 1, 1)
                    prng = [start, stop, 1]
                    istart = k = stop - 1
                    continue
                i = start
            else:               # step > 0
                assert step > 0
                i = start
                # does current range lead to broken step?
                if step != i - k or not unitary:
                    #Python2.6+: j = i if step == i - k else k
                    if step == i - k:
                        j = i
                    else:
                        j = k
                    # stepped is True when autostep setting does apply
                    stepped = (j - istart >= self._autostep * step)
                    if prng:    # yield pending range?
                        if stepped:
                            prng[1] -= 1
                        else:
                            istart += step
                        yield slice(*prng)
                        prng = None
                if step != i - k:
                    # case: step value has changed
                    if stepped:
                        yield slice(istart, k + 1, step)
                    else:
                        for j in range(istart, k - step + 1, step):
                            yield slice(j, j + 1, 1)
                        if not unitary:
                            yield slice(k, k + 1, 1)
                    if unitary:
                        if stepped:
                            istart = i = k = start
                        else:
                            istart = k
                    else:
                        prng = [start, stop, 1]
                        istart = i = k = stop - 1
                elif not unitary:
                    # case: broken step by contiguous range
                    if stepped:
                        # yield 'range/step' by taking first indice of new range
                        yield slice(istart, i + 1, step)
                        i += 1
                    else:
                        # autostep setting does not apply in that case
                        for j in range(istart, i - step + 1, step):
                            yield slice(j, j + 1, 1)
                    if stop > i + 1:    # current->pending only if not unitary
                        prng = [i, stop, 1]
                    istart = i = k = stop - 1
            step = i - k
            k = i
        # exited loop, process pending range or indice...
        if step == 0:
            if prng:
                yield slice(*prng)
            else:
                yield slice(istart, istart + 1, 1)
        else:
            assert step > 0
            stepped = (k - istart >= self._autostep * step)
            if prng:
                if stepped:
                    prng[1] -= 1
                else:
                    istart += step
                yield slice(*prng)
                prng = None
            if stepped:
                yield slice(istart, i + 1, step)
            else:
                for j in range(istart, i + 1, step):
                    yield slice(j, j + 1, 1)

    def slices(self):
        """
        Iterate over RangeSet ranges as Python slice objects.
        """
        # return an iterator
        if self._autostep >= 1E100:
            return self._contiguous_slices()
        else:
            return self._folded_slices()

    def __getitem__(self, index):
        """
        Return the element at index or a subrange when a slice is specified.
        """
        if isinstance(index, slice):
            inst = RangeSet()
            inst._autostep = self._autostep
            inst.padding = self.padding
            inst.update(self._sorted()[index])
            return inst
        elif isinstance(index, int):
            return self._sorted()[index]
        else:
            raise TypeError, \
                "%s indices must be integers" % self.__class__.__name__

    def split(self, nbr):
        """
        Split the rangeset into nbr sub-rangesets (at most). Each
        sub-rangeset will have the same number of elements more or
        less 1. Current rangeset remains unmodified. Returns an
        iterator.

        >>> RangeSet("1-5").split(3) 
        RangeSet("1-2")
        RangeSet("3-4")
        RangeSet("foo5")
        """
        assert(nbr > 0)

        # We put the same number of element in each sub-nodeset.
        slice_size = len(self) / nbr
        left = len(self) % nbr

        begin = 0
        for i in range(0, min(nbr, len(self))):
            length = slice_size + int(i < left)
            yield self[begin:begin + length]
            begin += length

    def add_range(self, start, stop, step=1, pad=0):
        """
        Add a range (start, stop, step and padding length) to RangeSet.
        Like the Python built-in function range(), the last element is
        the largest start + i * step less than stop.
        """
        assert start < stop, "please provide ordered node index ranges"
        assert step > 0
        assert pad >= 0
        assert stop - start < 1e9, "range too large"

        if pad > 0 and self.padding is None:
            self.padding = pad
        set.update(self, range(start, stop, step))

    def copy(self):
        """Return a shallow copy of a RangeSet."""
        cpy = self.__class__()
        cpy._autostep = self._autostep
        cpy.padding = self.padding
        cpy.update(self)
        return cpy

    __copy__ = copy # For the copy module

    def __eq__(self, other):
        """
        RangeSet equality comparison.
        """
        # Return NotImplemented instead of raising TypeError, to
        # indicate that the comparison is not implemented with respect
        # to the other type (the other comparand then gets a change to
        # determine the result, then it falls back to object address
        # comparison).
        if not isinstance(other, RangeSet):
            return NotImplemented
        return len(self) == len(other) and self.issubset(other)

    # Standard set operations: union, intersection, both differences.
    # Each has an operator version (e.g. __or__, invoked with |) and a
    # method version (e.g. union).
    # Subtle:  Each pair requires distinct code so that the outcome is
    # correct when the type of other isn't suitable.  For example, if
    # we did "union = __or__" instead, then Set().union(3) would return
    # NotImplemented instead of raising TypeError (albeit that *why* it
    # raises TypeError as-is is also a bit subtle).

    def _wrap_set_op(self, fun, arg):
        """Wrap built-in set operations for RangeSet to workaround built-in set
        base class issues (RangeSet.__new/init__ not called)"""
        result = fun(self, arg)
        result._autostep = self._autostep
        result.padding = self.padding
        return result

    def __or__(self, other):
        """Return the union of two RangeSets as a new RangeSet.

        (I.e. all elements that are in either set.)
        """
        if not isinstance(other, set):
            return NotImplemented
        return self.union(other)

    def union(self, other):
        """Return the union of two RangeSets as a new RangeSet.

        (I.e. all elements that are in either set.)
        """
        return self._wrap_set_op(set.union, other)

    def __and__(self, other):
        """Return the intersection of two RangeSets as a new RangeSet.

        (I.e. all elements that are in both sets.)
        """
        if not isinstance(other, set):
            return NotImplemented
        return self.intersection(other)

    def intersection(self, other):
        """Return the intersection of two RangeSets as a new RangeSet.

        (I.e. all elements that are in both sets.)
        """
        return self._wrap_set_op(set.intersection, other)

    def __xor__(self, other):
        """Return the symmetric difference of two RangeSets as a new RangeSet.

        (I.e. all elements that are in exactly one of the sets.)
        """
        if not isinstance(other, set):
            return NotImplemented
        return self.symmetric_difference(other)

    def symmetric_difference(self, other):
        """Return the symmetric difference of two RangeSets as a new RangeSet.
        
        (ie. all elements that are in exactly one of the sets.)
        """
        return self._wrap_set_op(set.symmetric_difference, other)

    def __sub__(self, other):
        """Return the difference of two RangeSets as a new RangeSet.

        (I.e. all elements that are in this set and not in the other.)
        """
        if not isinstance(other, set):
            return NotImplemented
        return self.difference(other)

    def difference(self, other):
        """Return the difference of two RangeSets as a new RangeSet.

        (I.e. all elements that are in this set and not in the other.)
        """
        return self._wrap_set_op(set.difference, other)

    # Membership test

    def __contains__(self, element):
        """Report whether an element is a member of a RangeSet.
        Element can be either another RangeSet object, a string or an
        integer.

        (Called in response to the expression `element in self'.)
        """
        if isinstance(element, set):
            return element.issubset(self)

        return set.__contains__(self, int(element))

    # Subset and superset test

    def issubset(self, other):
        """Report whether another set contains this RangeSet."""
        self._binary_sanity_check(other)
        return set.issubset(self, other)

    def issuperset(self, other):
        """Report whether this RangeSet contains another set."""
        self._binary_sanity_check(other)
        return set.issuperset(self, other)

    # Inequality comparisons using the is-subset relation.
    __le__ = issubset
    __ge__ = issuperset

    def __lt__(self, other):
        self._binary_sanity_check(other)
        return len(self) < len(other) and self.issubset(other)

    def __gt__(self, other):
        self._binary_sanity_check(other)
        return len(self) > len(other) and self.issuperset(other)

    # Assorted helpers

    def _binary_sanity_check(self, other):
        """Check that the other argument to a binary operation is also  a set,
        raising a TypeError otherwise."""
        if not isinstance(other, set):
            raise TypeError, "Binary operation only permitted between sets"

    # In-place union, intersection, differences.
    # Subtle:  The xyz_update() functions deliberately return None,
    # as do all mutating operations on built-in container types.
    # The __xyz__ spellings have to return self, though.
    
    def __ior__(self, other):
        """Update a RangeSet with the union of itself and another."""
        self._binary_sanity_check(other)
        set.__ior__(self, other)
        return self

    def union_update(self, other):
        """Update a RangeSet with the union of itself and another."""
        self.update(other)

    def __iand__(self, other):
        """Update a RangeSet with the intersection of itself and another."""
        self._binary_sanity_check(other)
        set.__iand__(self, other)
        return self

    def intersection_update(self, other):
        """Update a RangeSet with the intersection of itself and another."""
        set.intersection_update(self, other)

    def __ixor__(self, other):
        """Update a RangeSet with the symmetric difference of itself and
        another."""
        self._binary_sanity_check(other)
        set.symmetric_difference_update(self, other)
        return self

    def symmetric_difference_update(self, other):
        """Update a RangeSet with the symmetric difference of itself and
        another."""
        set.symmetric_difference_update(self, other)
        
    def __isub__(self, other):
        """Remove all elements of another set from this RangeSet."""
        self._binary_sanity_check(other)
        set.difference_update(self, other)
        return self

    def difference_update(self, other, strict=False):
        """Remove all elements of another set from this RangeSet.
        
        If strict is True, raise KeyError if an element cannot be removed.
        (strict is a RangeSet addition)"""
        if strict and other not in self:
            raise KeyError(other.difference(self)[0])
        set.difference_update(self, other)

    # Python dict-like mass mutations: update, clear

    def update(self, iterable):
        """Add all integers from an iterable (such as a list)."""
        if isinstance(iterable, RangeSet):
            # keep padding unless it has not been defined yet
            if self.padding is None and iterable.padding is not None:
                self.padding = iterable.padding
        assert type(iterable) is not str
        set.update(self, iterable)

    def updaten(self, rangesets):
        """
        Update a rangeset with the union of itself and several others.
        """
        for rng in rangesets:
            if isinstance(rng, set):
                self.update(rng)
            else:
                self.update(RangeSet(rng))
            # py2.5+
            #self.update(rng if isinstance(rng, set) else RangeSet(rng))

    def clear(self):
        """Remove all elements from this RangeSet."""
        set.clear(self)
        self.padding = None

    # Single-element mutations: add, remove, discard

    def add(self, element, pad=0):
        """Add an element to a RangeSet.
        This has no effect if the element is already present.
        """
        set.add(self, int(element))
        if pad > 0 and self.padding is None:
            self.padding = pad

    def remove(self, element):
        """Remove an element from a RangeSet; it must be a member.
        
        Raise KeyError if element is not contained in RangeSet.
        Raise ValueError if element is not castable to integer.
        """
        set.remove(self, int(element))

    def discard(self, element):
        """Remove element from the RangeSet if it is a member.

        If the element is not a member, do nothing.
        """
        try:
            i = int(element)
            set.discard(self, i)
        except ValueError:
            pass # ignore other object types


class RangeSetND(object):
    """Build a N-dimensional RangeSet object.

    Constructors:
        Empty:
            RangeSetND()
        Build from a list of list of RangeSet objects:
            RangeSetND([[rs1, rs2, rs3, ...], ...])
        Strings are also supported:
            RangeSetND([["0-3", "4-10", ...], ...])
        Integers are also supported:
            RangeSetND([(0, 4), (0, 5), (1, 4), (1, 5), ...]

    Options:
        pads: list of 0-padding length (default is to not pad any dimensions)
        autostep: autostep threshold (use range/step notation if more than
                  #autostep items meet the condition) - default is off (None)
        copy_rangeset (advanced): if set to False, do not copy RangeSet objects
            from args (transfer ownership), which is faster. In that case, you
            should not modify these objects afterwards. (default is True)
    """
    def __init__(self, args=None, pads=None, autostep=None, copy_rangeset=True):
        """RangeSetND constructor"""
        # RangeSetND are arranged as a list of N-dimensional RangeSet vectors
        self._veclist = []
        # Dirty flag to avoid doing veclist folding too often
        self._dirty = True
        # Hint on whether several dimensions are varying or not
        self._multivar_hint = False
        if args is None:
            return
        for rgvec in args:
            if rgvec:
                if type(rgvec[0]) is str:
                    self._veclist.append([RangeSet(rg, autostep=autostep) \
                                          for rg in rgvec])
                elif isinstance(rgvec[0], RangeSet):
                    if copy_rangeset:
                        self._veclist.append([rg.copy() for rg in rgvec])
                    else:
                        self._veclist.append(rgvec)
                else:
                    if pads is None:
                        self._veclist.append( \
                            [RangeSet.fromone(rg, autostep=autostep) \
                                for rg in rgvec])
                    else:
                        self._veclist.append( \
                            [RangeSet.fromone(rg, pad, autostep) \
                                for rg, pad in zip(rgvec, pads)])

    class precond_fold(object):
        """Decorator to ease internal folding management"""
        def __call__(self, func):
            def inner(*args, **kwargs):
                rgnd, fargs = args[0], args[1:]
                if rgnd._dirty:
                    rgnd._fold()
                return func(rgnd, *fargs, **kwargs)
            # modify the decorator meta-data for pydoc
            # Note: should be later replaced  by @wraps (functools)
            # as of Python 2.5
            inner.__name__ = func.__name__
            inner.__doc__ = func.__doc__
            inner.__dict__ = func.__dict__
            inner.__module__ = func.__module__
            return inner

    @precond_fold()
    def copy(self):
        """Return a shallow copy of a RangeSetND."""
        cpy = self.__class__()
        cpy._veclist = list(self._veclist)
        cpy._dirty = self._dirty
        return cpy

    __copy__ = copy # For the copy module

    def __eq__(self, other):
        """
        RangeSetND equality comparison.
        """
        # Return NotImplemented instead of raising TypeError, to
        # indicate that the comparison is not implemented with respect
        # to the other type (the other comparand then gets a change to
        # determine the result, then it falls back to object address
        # comparison).
        if not isinstance(other, RangeSetND):
            return NotImplemented
        return len(self) == len(other) and self.issubset(other)

    def __nonzero__(self):
        return bool(self._veclist)

    def __len__(self):
        """Count unique elements in N-dimensional rangeset."""
        return sum([reduce(mul, [len(rg) for rg in rgvec]) \
                                 for rgvec in self.veclist])

    @precond_fold()
    def __str__(self):
        """String representation of N-dimensional RangeSet."""
        result = ""
        for rgvec in self._veclist:
            result += "; ".join([str(rg) for rg in rgvec])
            result += "\n"
        return result

    @precond_fold()
    def __iter__(self):
        return self._iter()

    def _iter(self):
        """Iterate through individual items as tuples."""
        for vec in self._veclist:
            for ivec in product(*vec):
                yield ivec

    @precond_fold()
    def iter_padding(self):
        """Iterate through individual items as tuples with padding info."""
        for vec in self._veclist:
            for ivec in product(*vec):
                yield ivec, [rg.padding for rg in vec]

    @precond_fold()
    def _get_veclist(self):
        """Get folded veclist"""
        return self._veclist

    def _set_veclist(self, val):
        """Set veclist and set dirty flag for deferred folding."""
        self._veclist = val
        self._dirty = True

    veclist = property(_get_veclist, _set_veclist)

    def vectors(self):
        """Get underlying RangeSet vectors"""
        return iter(self.veclist)

    def dim(self):
        """Get the current number of dimensions of this RangeSetND
        object.  Return 0 when object is empty."""
        try:
            return len(self._veclist[0])
        except IndexError:
            return 0

    def pads(self):
        """Get a tuple of padding length info for each dimension."""
        try:
            return tuple(rg.padding for rg in self._veclist[0])
        except IndexError:
            return ()

    @property
    def autostep(self):
        return self._veclist[0][0].autostep
        #return max(rg.autostep for rg in rgvec for rgvec in self.veclist)

    @precond_fold()
    def __getitem__(self, index):
        """
        Return the element at index or a subrange when a slice is specified.
        """
        if isinstance(index, slice):
            iveclist = []
            for rgvec in self._veclist:
                iveclist += product(*rgvec)
            assert(len(iveclist) == len(self))
            rnd = RangeSetND(iveclist[index],
                             pads=[rg.padding for rg in self._veclist[0]],
                             autostep=self.autostep)
            return rnd

        elif isinstance(index, int):
            # find a tuple of integer (multi-dimensional) at position index
            if index < 0:
                length = len(self)
                if index >= -length:
                    index = length + index
                else:
                    raise IndexError, "%d out of range" % index
            length = 0
            for rgvec in self._veclist:
                cnt = reduce(mul, [len(rg) for rg in rgvec])
                if length + cnt < index:
                    length += cnt
                else:
                    for ivec in product(*rgvec):
                        if index == length:
                            return ivec
                        length += 1
            raise IndexError, "%d out of range" % index
        else:
            raise TypeError, \
                "%s indices must be integers" % self.__class__.__name__

    @precond_fold()
    def contiguous(self):
        """Object-based iterator over contiguous range sets."""
        veclist = self._veclist
        try:
            dim = len(veclist[0])
        except IndexError:
            return
        for dimidx in range(dim):
            new_veclist = []
            for rgvec in veclist:
                for rgsli in rgvec[dimidx].contiguous():
                    rgvec = list(rgvec)
                    rgvec[dimidx] = rgsli
                    new_veclist.append(rgvec)
            veclist = new_veclist
        for rgvec in veclist:
            yield RangeSetND([rgvec])

    # Membership test

    @precond_fold()
    def __contains__(self, element):
        """Report whether an element is a member of a RangeSetND.
        Element can be either another RangeSetND object, a string or
        an integer.

        (Called in response to the expression `element in self'.)
        """
        if isinstance(element, RangeSetND):
            rgnd_element = element
        else:
            rgnd_element = RangeSetND([[str(element)]])
        return rgnd_element.issubset(self)

    # Subset and superset test

    def issubset(self, other):
        """Report whether another set contains this RangeSetND."""
        self._binary_sanity_check(other)
        return other.issuperset(self)

    @precond_fold()
    def issuperset(self, other):
        """Report whether this RangeSetND contains another RangeSetND."""
        self._binary_sanity_check(other)
        if self.dim() == 1 and other.dim() == 1:
            return self._veclist[0][0].issuperset(other._veclist[0][0])
        if not other._veclist:
            return True
        test = other.copy()
        test.difference_update(self)
        return not bool(test)

    # Inequality comparisons using the is-subset relation.
    __le__ = issubset
    __ge__ = issuperset

    def __lt__(self, other):
        self._binary_sanity_check(other)
        return len(self) < len(other) and self.issubset(other)

    def __gt__(self, other):
        self._binary_sanity_check(other)
        return len(self) > len(other) and self.issuperset(other)

    # Assorted helpers

    def _binary_sanity_check(self, other):
        """Check that the other argument to a binary operation is also a
        RangeSetND, raising a TypeError otherwise."""
        if not isinstance(other, RangeSetND):
            raise TypeError, \
                "Binary operation only permitted between RangeSetND"

    def _sort(self):
        """N-dimensional sorting."""
        def rgveckeyfunc(rgvec):
            # key used for sorting purposes, based on the following
            # conditions:
            #   (1) larger vector first (#elements)
            #   (2) larger dim first  (#elements)
            #   (3) lower first index first
            #   (4) lower last index first
            return (-reduce(mul, [len(rg) for rg in rgvec]), \
                    tuple((-len(rg), rg[0], rg[-1]) for rg in rgvec))
        self._veclist.sort(key=rgveckeyfunc)

    @precond_fold()
    def fold(self):
        """Explicit folding call. Please note that folding of RangeSetND
        nD vectors are automatically managed, so you should not have to
        call this method. It may be still useful in some extreme cases
        where the RangeSetND is heavily modified."""
        pass

    def _fold(self):
        """In-place N-dimensional folding."""
        assert self._dirty
        if len(self._veclist) > 1:
            self._fold_univariate() or self._fold_multivariate()
        else:
            self._dirty = False

    def _fold_univariate(self):
        """Univariate nD folding. Return True on success and False when
        a multivariate folding is required."""
        dim = self.dim()
        vardim = dimdiff = 0
        if dim > 1:
            # We got more than one dimension, see if only one is changing...
            for i in range(dim):
                # Are all rangesets on this dimension the same?
                slist = [vec[i] for vec in self._veclist]
                if slist.count(slist[0]) != len(slist):
                    dimdiff += 1
                    if dimdiff > 1:
                        break
                    vardim = i
        univar = (dim == 1 or dimdiff == 1)
        if univar:
            # Eligible for univariate folding (faster!)
            for vec in self._veclist[1:]:
                self._veclist[0][vardim].update(vec[vardim])
            del self._veclist[1:]
            self._dirty = False
        self._multivar_hint = not univar
        return univar

    def _fold_multivariate(self):
        """Multivariate nD folding"""
        # PHASE 1: expand with respect to uniqueness
        self._fold_multivariate_expand()
        self._sort()
        # PHASE 2: merge
        self._fold_multivariate_merge()
        self._sort()
        self._dirty = False

    def _fold_multivariate_expand(self):
        """Multivariate nD folding: expand [phase 1]"""
        max_length = sum([reduce(mul, [len(rg) for rg in rgvec]) \
                                       for rgvec in self._veclist])
        # Simple heuristic that makes us faster
        if len(self._veclist) * (len(self._veclist) - 1) / 2 > max_length * 10:
            # *** nD full expand is preferred ***
            self._veclist = [[RangeSet.fromone(i) for i in tvec] \
                             for tvec in set(self._iter())]
            return

        # *** nD compare algorithm is preferred ***
        index1, index2 = 0, 1
        while (index1 + 1) < len(self._veclist):
            # use 2 references on iterator to compare items by couples
            item1 = self._veclist[index1]
            index2 = index1 + 1
            index1 += 1
            while index2 < len(self._veclist):
                item2 = self._veclist[index2]
                index2 += 1
                new_item = None
                disjoint = False
                suppl = []
                for pos, (rg1, rg2) in enumerate(zip(item1, item2)):
                    if not rg1 & rg2:
                        disjoint = True
                        break

                    if new_item is None:
                        new_item = [None] * len(item1)

                    if rg1 == rg2:
                        new_item[pos] = rg1
                    else:
                        assert rg1 & rg2
                        # intersection
                        new_item[pos] = rg1 & rg2
                        # create part 1
                        if rg1 - rg2:
                            item1_p = item1[0:pos] + [rg1 - rg2] + item1[pos+1:]
                            suppl.append(item1_p)
                        # create part 2
                        if rg2 - rg1:
                            item2_p = item2[0:pos] + [rg2 - rg1] + item2[pos+1:]
                            suppl.append(item2_p)
                if not disjoint:
                    assert new_item is not None
                    assert suppl is not None
                    item1 = self._veclist[index1 - 1] = new_item
                    index2 -= 1
                    self._veclist.pop(index2)
                    self._veclist += suppl

    def _fold_multivariate_merge(self):
        """Multivariate nD folding: merge [phase 2]"""
        chg = True
        while chg:
            chg = False
            index1, index2 = 0, 1
            while (index1 + 1) < len(self._veclist):
                # use 2 references on iterator to compare items by couples
                item1 = self._veclist[index1]
                index2 = index1 + 1
                index1 += 1
                while index2 < len(self._veclist):
                    item2 = self._veclist[index2]
                    index2 += 1
                    new_item = [None] * len(item1)
                    nb_diff = 0
                    # compare 2 rangeset vector, item by item, the idea being
                    # to merge vectors if they differ only by one item
                    for pos, (rg1, rg2) in enumerate(zip(item1, item2)):
                        if rg1 == rg2:
                            new_item[pos] = rg1
                        elif not rg1 & rg2: # merge on disjoint ranges
                            nb_diff += 1
                            if nb_diff > 1:
                                break
                            new_item[pos] = rg1 | rg2
                        # if fully contained, keep the largest one
                        elif (rg1 > rg2 or rg1 < rg2): # and nb_diff == 0:
                            nb_diff += 1
                            if nb_diff > 1:
                                break
                            new_item[pos] = max(rg1, rg2)
                        # otherwise, compute rangeset intersection and
                        # keep the two disjoint part to be handled
                        # later...
                        else:
                            # intersection but do nothing
                            nb_diff = 2
                            break
                    # one change has been done: use this new item to compare
                    # with other
                    if nb_diff <= 1:
                        chg = True
                        item1 = self._veclist[index1 - 1] = new_item
                        index2 -= 1
                        self._veclist.pop(index2)

    def __or__(self, other):
        """Return the union of two RangeSetNDs as a new RangeSetND.

        (I.e. all elements that are in either set.)
        """
        if not isinstance(other, RangeSetND):
            return NotImplemented
        return self.union(other)

    def union(self, other):
        """Return the union of two RangeSetNDs as a new RangeSetND.

        (I.e. all elements that are in either set.)
        """
        rgnd_copy = self.copy()
        rgnd_copy.update(other)
        return rgnd_copy

    def update(self, other):
        """Add all RangeSetND elements to this RangeSetND."""
        if isinstance(other, RangeSetND):
            iterable = other._veclist
        else:
            iterable = other
        for vec in iterable:
            # we could avoid rg.copy() here if 'other' is a RangeSetND
            # with immutable underlying RangeSets...
            assert isinstance(vec[0], RangeSet)
            self._veclist.append([rg.copy() for rg in vec])
        self._dirty = True
        if not self._multivar_hint:
            self._fold_univariate()

    union_update = update

    def __ior__(self, other):
        """Update a RangeSetND with the union of itself and another."""
        self._binary_sanity_check(other)
        self.update(other)
        return self

    def __isub__(self, other):
        """Remove all elements of another set from this RangeSetND."""
        self._binary_sanity_check(other)
        self.difference_update(other)
        return self

    def difference_update(self, other, strict=False):
        """Remove all elements of another set from this RangeSetND.

        If strict is True, raise KeyError if an element cannot be removed.
        (strict is a RangeSet addition)"""
        if strict and not other in self:
            raise KeyError(other.difference(self)[0])

        ergvx = other._veclist # read only
        rgnd_new = []
        index1 = 0
        while index1 < len(self._veclist):
            rgvec1 = self._veclist[index1]
            procvx1 = [ rgvec1 ]
            nextvx1 = []
            index2 = 0
            while index2 < len(ergvx):
                rgvec2 = ergvx[index2]
                while len(procvx1) > 0: # refine diff for each resulting vector
                    rgproc1 = procvx1.pop(0)
                    tmpvx = []
                    for pos, (rg1, rg2) in enumerate(zip(rgproc1, rgvec2)):
                        if rg1 == rg2 or rg1 < rg2: # issubset
                            pass
                        elif rg1 & rg2:             # intersect
                            tmpvec = list(rgproc1)
                            tmpvec[pos] = rg1.difference(rg2)
                            tmpvx.append(tmpvec)
                        else:                       # disjoint
                            tmpvx = [ rgproc1 ]     # reset previous work
                            break
                    if tmpvx:
                        nextvx1 += tmpvx
                if nextvx1:
                    procvx1 = nextvx1
                    nextvx1 = []
                index2 += 1
            if procvx1:
                rgnd_new += procvx1
            index1 += 1
        self.veclist = rgnd_new

    def __sub__(self, other):
        """Return the difference of two RangeSetNDs as a new RangeSetND.

        (I.e. all elements that are in this set and not in the other.)
        """
        if not isinstance(other, RangeSetND):
            return NotImplemented
        return self.difference(other)

    def difference(self, other):
        """
        s.difference(t) returns a new object with elements in s but not
        in t.
        """
        self_copy = self.copy()
        self_copy.difference_update(other)
        return self_copy

    def intersection(self, other):
        """
        s.intersection(t) returns a new object with elements common to s
        and t.
        """
        self_copy = self.copy()
        self_copy.intersection_update(other)
        return self_copy

    def __and__(self, other):
        """
        Implements the & operator. So s & t returns a new object with
        elements common to s and t.
        """
        if not isinstance(other, RangeSetND):
            return NotImplemented
        return self.intersection(other)

    def intersection_update(self, other):
        """
        s.intersection_update(t) returns nodeset s keeping only
        elements also found in t.
        """
        if other is self:
            return

        tmp_rnd = RangeSetND()

        empty_rset = RangeSet()

        for rgvec in self._veclist:
            for ergvec in other._veclist:
                irgvec = [rg.intersection(erg) \
                            for rg, erg in zip(rgvec, ergvec)]
                if not empty_rset in irgvec:
                    tmp_rnd.update([irgvec])
        # substitute
        self.veclist = tmp_rnd.veclist

    def __iand__(self, other):
        """
        Implements the &= operator. So s &= t returns object s keeping
        only elements also found in t. (Python version 2.5+ required)
        """
        self._binary_sanity_check(other)
        self.intersection_update(other)
        return self

    def symmetric_difference(self, other):
        """
        s.symmetric_difference(t) returns the symmetric difference of
        two objects as a new RangeSetND.

        (ie. all items that are in exactly one of the RangeSetND.)
        """
        self_copy = self.copy()
        self_copy.symmetric_difference_update(other)
        return self_copy

    def __xor__(self, other):
        """
        Implement the ^ operator. So s ^ t returns a new RangeSetND with
        nodes that are in exactly one of the RangeSetND.
        """
        if not isinstance(other, RangeSetND):
            return NotImplemented
        return self.symmetric_difference(other)

    def symmetric_difference_update(self, other):
        """
        s.symmetric_difference_update(t) returns RangeSetND s keeping all
        nodes that are in exactly one of the objects.
        """
        diff2 = other.difference(self)
        self.difference_update(other)
        self.update(diff2)

    def __ixor__(self, other):
        """
        Implement the ^= operator. So s ^= t returns object s after
        keeping all items that are in exactly one of the RangeSetND.
        (Python version 2.5+ required)
        """
        self._binary_sanity_check(other)
        self.symmetric_difference_update(other)
        return self


########NEW FILE########
__FILENAME__ = Task
#
# Copyright CEA/DAM/DIF (2007-2014)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
ClusterShell Task module.

Simple example of use:

>>> from ClusterShell.Task import task_self
>>>  
>>> # get task associated with calling thread
... task = task_self()
>>> 
>>> # add a command to execute on distant nodes
... task.shell("/bin/uname -r", nodes="tiger[1-30,35]")
<ClusterShell.Worker.Ssh.WorkerSsh object at 0x7f41da71b890>
>>> 
>>> # run task in calling thread
... task.resume()
>>> 
>>> # get results
... for buf, nodelist in task.iter_buffers():
...     print NodeSet.fromlist(nodelist), buf
... 

"""

from itertools import imap
import logging
from operator import itemgetter
import socket
import sys
import threading
from time import sleep
import traceback

from ClusterShell.Engine.Engine import EngineAbortException
from ClusterShell.Engine.Engine import EngineTimeoutException
from ClusterShell.Engine.Engine import EngineAlreadyRunningError
from ClusterShell.Engine.Engine import EngineTimer
from ClusterShell.Engine.Factory import PreferredEngine
from ClusterShell.Worker.EngineClient import EnginePort
from ClusterShell.Worker.Ssh import WorkerSsh
from ClusterShell.Worker.Popen import WorkerPopen
from ClusterShell.Worker.Tree import WorkerTree

from ClusterShell.Event import EventHandler
from ClusterShell.MsgTree import MsgTree
from ClusterShell.NodeSet import NodeSet

from ClusterShell.Topology import TopologyParser, TopologyError
from ClusterShell.Propagation import PropagationTreeRouter, PropagationChannel


class TaskException(Exception):
    """Base task exception."""

class TaskError(TaskException):
    """Base task error exception."""

class TimeoutError(TaskError):
    """Raised when the task timed out."""

class AlreadyRunningError(TaskError):
    """Raised when trying to resume an already running task."""

class TaskMsgTreeError(TaskError):
    """Raised when trying to access disabled MsgTree."""


def _getshorthostname():
    """Get short hostname (host name cut at the first dot)"""
    return socket.gethostname().split('.')[0]

def _task_print_debug(task, s):
    """
    Default task debug printing function. Cannot provide 'print'
    directly as it is not a function (will be in Py3k!).
    """
    print s


class Task(object):
    """
    The Task class defines an essential ClusterShell object which aims to
    execute commands in parallel and easily get their results.

    More precisely, a Task object manages a coordinated (ie. with respect of
    its current parameters) collection of independent parallel Worker objects.
    See ClusterShell.Worker.Worker for further details on ClusterShell Workers.

    Always bound to a specific thread, a Task object acts like a "thread
    singleton". So most of the time, and even more for single-threaded
    applications, you can get the current task object with the following
    top-level Task module function:
        >>> task = task_self()

    However, if you want to create a task in a new thread, use:
        >>> task = Task()

    To create or get the instance of the task associated with the thread
    object thr (threading.Thread):
        >>> task = Task(thread=thr)

    To submit a command to execute locally within task, use:
        >>> task.shell("/bin/hostname")

    To submit a command to execute to some distant nodes in parallel, use:
        >>> task.shell("/bin/hostname", nodes="tiger[1-20]")

    The previous examples submit commands to execute but do not allow result
    interaction during their execution. For your program to interact during
    command execution, it has to define event handlers that will listen for
    local or remote events. These handlers are based on the EventHandler
    class, defined in ClusterShell.Event. The following example shows how to
    submit a command on a cluster with a registered event handler:
        >>> task.shell("uname -r", nodes="node[1-9]", handler=MyEventHandler())

    Run task in its associated thread (will block only if the calling thread is
    the task associated thread):
        >>> task.resume()
    or
        >>> task.run()

    You can also pass arguments to task.run() to schedule a command exactly
    like in task.shell(), and run it:
        >>> task.run("hostname", nodes="tiger[1-20]", handler=MyEventHandler())

    A common need is to set a maximum delay for command execution, especially
    when the command time is not known. Doing this with ClusterShell Task is
    very straighforward. To limit the execution time on each node, use the
    timeout parameter of shell() or run() methods to set a delay in seconds,
    like:
        >>> task.run("check_network.sh", nodes="tiger[1-20]", timeout=30)

    You can then either use Task's iter_keys_timeout() method after execution
    to see on what nodes the command has timed out, or listen for ev_timeout()
    events in your event handler.

    To get command result, you can either use Task's iter_buffers() method for
    standard output, iter_errors() for standard error after command execution
    (common output contents are automatically gathered), or you can listen for
    ev_read() and ev_error() events in your event handler and get live command
    output.

    To get command return codes, you can either use Task's iter_retcodes(),
    node_retcode() and max_retcode() methods after command execution, or
    listen for ev_hup() events in your event handler.
    """
    _std_default = {  "stderr"             : False,
                      "stdout_msgtree"     : True,
                      "stderr_msgtree"     : True,
                      "engine"             : 'auto',
                      "port_qlimit"        : 100,
                      "auto_tree"          : False,
                      "topology_file"      : "/etc/clustershell/topology.conf",
                      "worker"             : WorkerSsh }

    _std_info =     { "debug"              : False,
                      "print_debug"        : _task_print_debug,
                      "fanout"             : 64,
                      "grooming_delay"     : 0.25,
                      "connect_timeout"    : 10,
                      "command_timeout"    : 0 }
    _tasks = {}
    _taskid_max = 0
    _task_lock = threading.Lock()

    class _SyncMsgHandler(EventHandler):
        """Special task control port event handler.
        When a message is received on the port, call appropriate
        task method."""
        def ev_msg(self, port, msg):
            """Message received: call appropriate task method."""
            # pull out function and its arguments from message
            func, (args, kwargs) = msg[0], msg[1:]
            # call task method
            func(port.task, *args, **kwargs)

    class tasksyncmethod(object):
        """Class encapsulating a function that checks if the calling
        task is running or is the current task, and allowing it to be
        used as a decorator making the wrapped task method thread-safe."""
        
        def __call__(self, f):
            def taskfunc(*args, **kwargs):
                # pull out the class instance
                task, fargs = args[0], args[1:]
                # check if the calling task is the current thread task
                if task._is_task_self():
                    return f(task, *fargs, **kwargs)
                elif task._dispatch_port:
                    # no, safely call the task method by message 
                    # through the task special dispatch port
                    task._dispatch_port.msg_send((f, fargs, kwargs))
                else:
                    task.info("print_debug")(task, "%s: dropped call: %s" % \
                                                   (task, str(fargs)))
            # modify the decorator meta-data for pydoc
            # Note: should be later replaced  by @wraps (functools)
            # as of Python 2.5
            taskfunc.__name__ = f.__name__
            taskfunc.__doc__ = f.__doc__
            taskfunc.__dict__ = f.__dict__
            taskfunc.__module__ = f.__module__
            return taskfunc

    class _SuspendCondition(object):
        """Special class to manage task suspend condition."""
        def __init__(self, lock=threading.RLock(), initial=0):
            self._cond = threading.Condition(lock)
            self.suspend_count = initial

        def atomic_inc(self):
            """Increase suspend count."""
            self._cond.acquire()
            self.suspend_count += 1
            self._cond.release()

        def atomic_dec(self):
            """Decrease suspend count."""
            self._cond.acquire()
            self.suspend_count -= 1
            self._cond.release()

        def wait_check(self, release_lock=None):
            """Wait for condition if needed."""
            self._cond.acquire()
            try:
                if self.suspend_count > 0:
                    if release_lock:
                        release_lock.release()
                    self._cond.wait()
            finally:
                self._cond.release()
            
        def notify_all(self):
            """Signal all threads waiting for condition."""
            self._cond.acquire()
            try:
                self.suspend_count = min(self.suspend_count, 0)
                self._cond.notifyAll()
            finally:
                self._cond.release()


    def __new__(cls, thread=None):
        """
        For task bound to a specific thread, this class acts like a
        "thread singleton", so new style class is used and new object
        are only instantiated if needed.
        """
        if thread:
            if thread not in cls._tasks:
                cls._tasks[thread] = object.__new__(cls)
            return cls._tasks[thread]

        return object.__new__(cls)

    def __init__(self, thread=None):
        """Initialize a Task, creating a new non-daemonic thread if
        needed."""
        if not getattr(self, "_engine", None):
            # first time called
            self._default_lock = threading.Lock()
            self._default = self.__class__._std_default.copy()
            self._info = self.__class__._std_info.copy()

            # use factory class PreferredEngine that gives the proper
            # engine instance
            self._engine = PreferredEngine(self.default("engine"), self._info)
            self.timeout = None

            # task synchronization objects
            self._run_lock = threading.Lock()       # primitive lock
            self._suspend_lock = threading.RLock()  # reentrant lock
            # both join and suspend conditions share the same underlying lock
            self._suspend_cond = Task._SuspendCondition(self._suspend_lock, 1)
            self._join_cond = threading.Condition(self._suspend_lock)
            self._suspended = False
            self._quit = False
            self._terminated = False

            # Default router
            self.topology = None
            self.router = None
            self.pwrks = {}
            self.pmwkrs = {}

            # STDIN tree
            self._msgtree = None
            # STDERR tree
            self._errtree = None
            # dict of sources to return codes
            self._d_source_rc = {}
            # dict of return codes to sources
            self._d_rc_sources = {}
            # keep max rc
            self._max_rc = 0
            # keep timeout'd sources
            self._timeout_sources = set()
            # allow no-op call to getters before resume()
            self._reset()

            # special engine port for task method dispatching
            self._dispatch_port = EnginePort(self,
                                            handler=Task._SyncMsgHandler(),
                                            autoclose=True)
            self._engine.add(self._dispatch_port)

            # set taskid used as Thread name
            Task._task_lock.acquire()
            Task._taskid_max += 1
            self._taskid = Task._taskid_max
            Task._task_lock.release()

            # create new thread if needed
            self._thread_foreign = bool(thread)
            if self._thread_foreign:
                self.thread = thread
            else:
                self.thread = thread = \
                    threading.Thread(None,
                                     Task._thread_start,
                                     "Task-%d" % self._taskid,
                                     args=(self,))
                Task._tasks[thread] = self
                thread.start()

    def _is_task_self(self):
        """Private method used by the library to check if the task is
        task_self(), but do not create any task_self() instance."""
        return self.thread == threading.currentThread()

    def default_excepthook(self, exc_type, exc_value, tb):
        """Default excepthook for a newly Task. When an exception is
        raised and uncaught on Task thread, excepthook is called, which
        is default_excepthook by default. Once excepthook overriden,
        you can still call default_excepthook if needed."""
        print >> sys.stderr, 'Exception in thread %s:' % self.thread
        traceback.print_exception(exc_type, exc_value, tb, file=sys.stderr)

    _excepthook = default_excepthook

    def _getexcepthook(self):
        return self._excepthook

    def _setexcepthook(self, hook):
        self._excepthook = hook
        # If thread has not been created by us, install sys.excepthook which
        # might handle uncaught exception.
        if self._thread_foreign:
            sys.excepthook = self._excepthook

    # When an exception is raised and uncaught on Task's thread,
    # excepthook is called. You may want to override this three
    # arguments method (very similar of what you can do with
    # sys.excepthook)."""
    excepthook = property(_getexcepthook, _setexcepthook)
        
    def _thread_start(self):
        """Task-managed thread entry point"""
        while not self._quit:
            self._suspend_cond.wait_check()
            if self._quit:  # may be set by abort()
                break
            try:
                self._resume()
            except:
                self.excepthook(*sys.exc_info())
                self._quit = True

        self._terminate(kill=True)

    def _run(self, timeout):
        """Run task (always called from its self thread)."""
        # check if task is already running
        if self._run_lock.locked():
            raise AlreadyRunningError("task is already running")
        # use with statement later
        try:
            self._run_lock.acquire()
            self._engine.run(timeout)
        finally:
            self._run_lock.release()

    def set_topology(self, topology_file):
        """Set new propagation topology from provided file."""
        self.set_default("topology_file", topology_file)
        self.topology = self._default_topology()

    def _default_topology(self):
        try:
            parser = TopologyParser()
            parser.load(self.default("topology_file"))
            return parser.tree(_getshorthostname())
        except TopologyError, exc:
            logging.getLogger(__name__).exception("_default_topology(): %s", \
                                                  str(exc))
            raise
        return None

    def _default_router(self):
        if self.router is None:
            topology = self.topology
            self.router = PropagationTreeRouter(str(topology.root.nodeset), \
                                                topology)
        return self.router

    def default(self, default_key, def_val=None):
        """
        Return per-task value for key from the "default" dictionary.
        See set_default() for a list of reserved task default_keys.
        """
        self._default_lock.acquire()
        try:
            return self._default.get(default_key, def_val)
        finally:
            self._default_lock.release()

    def set_default(self, default_key, value):
        """
        Set task value for specified key in the dictionary "default".
        Users may store their own task-specific key, value pairs
        using this method and retrieve them with default().
        
        Task default_keys are:
          - "stderr": Boolean value indicating whether to enable
            stdout/stderr separation when using task.shell(), if not
            specified explicitly (default: False).
          - "stdout_msgtree": Whether to enable standard output MsgTree
            for automatic internal gathering of result messages
            (default: True).
          - "stderr_msgtree": Same for stderr (default: True).
          - "engine": Used to specify an underlying Engine explicitly
            (default: "auto").
          - "port_qlimit": Size of port messages queue (default: 32).
          - "worker": Worker-based class used when spawning workers through
            shell()/run().

        Threading considerations
        ========================
          Unlike set_info(), when called from the task's thread or
          not, set_default() immediately updates the underlying
          dictionary in a thread-safe manner. This method doesn't
          wake up the engine when called.
        """
        self._default_lock.acquire()
        try:
            self._default[default_key] = value
        finally:
            self._default_lock.release()

    def info(self, info_key, def_val=None):
        """
        Return per-task information. See set_info() for a list of
        reserved task info_keys.
        """
        return self._info.get(info_key, def_val)

    @tasksyncmethod()
    def set_info(self, info_key, value):
        """
        Set task value for a specific key information. Key, value
        pairs can be passed to the engine and/or workers.
        Users may store their own task-specific info key, value pairs
        using this method and retrieve them with info().
        
        The following example changes the fanout value to 128:
            >>> task.set_info('fanout', 128)

        The following example enables debug messages:
            >>> task.set_info('debug', True)

        Task info_keys are:
          - "debug": Boolean value indicating whether to enable library
            debugging messages (default: False).
          - "print_debug": Debug messages processing function. This
            function takes 2 arguments: the task instance and the
            message string (default: an internal function doing standard
            print).
          - "fanout": Max number of registered clients in Engine at a
            time (default: 64).
          - "grooming_delay": Message maximum end-to-end delay requirement
            used for traffic grooming, in seconds as float (default: 0.5).
          - "connect_timeout": Time in seconds to wait for connecting to
            remote host before aborting (default: 10).
          - "command_timeout": Time in seconds to wait for a command to
            complete before aborting (default: 0, which means
            unlimited).

        Threading considerations
        ========================
          Unlike set_default(), the underlying info dictionary is only
          modified from the task's thread. So calling set_info() from
          another thread leads to queueing the request for late apply
          (at run time) using the task dispatch port. When received,
          the request wakes up the engine when the task is running and
          the info dictionary is then updated.
        """
        self._info[info_key] = value

    def shell(self, command, **kwargs):
        """
        Schedule a shell command for local or distant parallel execution. This
        essential method creates a local or remote Worker (depending on the
        presence of the nodes parameter) and immediately schedules it for
        execution in task's runloop. So, if the task is already running
        (ie. called from an event handler), the command is started immediately,
        assuming current execution contraintes are met (eg. fanout value). If
        the task is not running, the command is not started but scheduled for
        late execution. See resume() to start task runloop.

        The following optional parameters are passed to the underlying local
        or remote Worker constructor:
          - handler: EventHandler instance to notify (on event) -- default is
            no handler (None)
          - timeout: command timeout delay expressed in second using a floating
            point value -- default is unlimited (None)
          - autoclose: if set to True, the underlying Worker is automatically
            aborted as soon as all other non-autoclosing task objects (workers,
            ports, timers) have finished -- default is False
          - stderr: separate stdout/stderr if set to True -- default is False.

        Local usage::
            task.shell(command [, key=key] [, handler=handler]
                  [, timeout=secs] [, autoclose=enable_autoclose]
                  [, stderr=enable_stderr])

        Distant usage::
            task.shell(command, nodes=nodeset [, handler=handler]
                  [, timeout=secs], [, autoclose=enable_autoclose]
                  [, strderr=enable_stderr], [tree=None|False|True])

        Example:

        >>> task = task_self()
        >>> task.shell("/bin/date", nodes="node[1-2345]")
        >>> task.resume()
        """

        handler = kwargs.get("handler", None)
        timeo = kwargs.get("timeout", None)
        autoclose = kwargs.get("autoclose", False)
        stderr = kwargs.get("stderr", self.default("stderr"))

        if kwargs.get("nodes", None):
            assert kwargs.get("key", None) is None, \
                    "'key' argument not supported for distant command"

            tree = kwargs.get("tree")
            if tree and self.topology is None:
                raise TaskError("tree mode required for distant shell command" \
                                " with unknown topology!")
            if tree is None: # means auto
                tree = self.default("auto_tree") and (self.topology is not None)
            if tree:
                # create tree of ssh worker
                worker = WorkerTree(NodeSet(kwargs["nodes"]), command=command,
                                    handler=handler, stderr=stderr,
                                    timeout=timeo, autoclose=autoclose)
            else:
                # create ssh-based worker
                wrkcls = self.default('worker')
                worker = wrkcls(NodeSet(kwargs["nodes"]), command=command,
                                handler=handler, stderr=stderr,
                                timeout=timeo, autoclose=autoclose)
        else:
            # create (local) worker
            worker = WorkerPopen(command, key=kwargs.get("key", None),
                                 handler=handler, stderr=stderr,
                                 timeout=timeo, autoclose=autoclose)

        # schedule worker for execution in this task
        self.schedule(worker)

        return worker

    def copy(self, source, dest, nodes, **kwargs):
        """
        Copy local file to distant nodes.
        """
        assert nodes != None, "local copy not supported"

        handler = kwargs.get("handler", None)
        stderr = kwargs.get("stderr", self.default("stderr"))
        timeo = kwargs.get("timeout", None)
        preserve = kwargs.get("preserve", None)
        reverse = kwargs.get("reverse", False)

        # create a new copy worker
        wrkcls = self.default('worker')
        worker = wrkcls(nodes, source=source, dest=dest, handler=handler,
                        stderr=stderr, timeout=timeo, preserve=preserve,
                        reverse=reverse)

        self.schedule(worker)
        return worker

    def rcopy(self, source, dest, nodes, **kwargs):
        """
        Copy distant file or directory to local node.
        """
        kwargs['reverse'] = True
        return self.copy(source, dest, nodes, **kwargs)

    @tasksyncmethod()
    def _add_port(self, port):
        """Add an EnginePort instance to Engine (private method)."""
        self._engine.add(port)

    @tasksyncmethod()
    def _remove_port(self, port):
        """Remove a port from Engine (private method)."""
        self._engine.remove(port)

    def port(self, handler=None, autoclose=False):
        """
        Create a new task port. A task port is an abstraction object to
        deliver messages reliably between tasks.

        Basic rules:
          - A task can send messages to another task port (thread safe).
          - A task can receive messages from an acquired port either by
            setting up a notification mechanism or using a polling
            mechanism that may block the task waiting for a message
            sent on the port.
          - A port can be acquired by one task only.

        If handler is set to a valid EventHandler object, the port is
        a send-once port, ie. a message sent to this port generates an
        ev_msg event notification issued the port's task. If handler
        is not set, the task can only receive messages on the port by
        calling port.msg_recv().
        """
        port = EnginePort(self, handler, autoclose)
        self._add_port(port)
        return port

    def timer(self, fire, handler, interval=-1.0, autoclose=False):
        """
        Create a timer bound to this task that fires at a preset time
        in the future by invoking the ev_timer() method of `handler'
        (provided EventHandler object). Timers can fire either only
        once or repeatedly at fixed time intervals. Repeating timers
        can also have their next firing time manually adjusted.

        The mandatory parameter `fire' sets the firing delay in seconds.
        
        The optional parameter `interval' sets the firing interval of
        the timer. If not specified, the timer fires once and then is
        automatically invalidated.

        Time values are expressed in second using floating point
        values. Precision is implementation (and system) dependent.

        The optional parameter `autoclose', if set to True, creates
        an "autoclosing" timer: it will be automatically invalidated
        as soon as all other non-autoclosing task's objects (workers,
        ports, timers) have finished. Default value is False, which
        means the timer will retain task's runloop until it is
        invalidated.

        Return a new EngineTimer instance.

        See ClusterShell.Engine.Engine.EngineTimer for more details.
        """
        assert fire >= 0.0, \
            "timer's relative fire time must be a positive floating number"
        
        timer = EngineTimer(fire, interval, autoclose, handler)
        # The following method may be sent through msg port (async
        # call) if called from another task.
        self._add_timer(timer)
        # always return new timer (sync)
        return timer

    @tasksyncmethod()
    def _add_timer(self, timer):
        """Add a timer to task engine (thread-safe)."""
        self._engine.add_timer(timer)

    @tasksyncmethod()
    def schedule(self, worker):
        """
        Schedule a worker for execution, ie. add worker in task running
        loop. Worker will start processing immediately if the task is
        running (eg. called from an event handler) or as soon as the
        task is started otherwise. Only useful for manually instantiated
        workers, for example:

        >>> task = task_self()
        >>> worker = WorkerSsh("node[2-3]", None, 10, command="/bin/ls")
        >>> task.schedule(worker)
        >>> task.resume()
        """
        assert self in Task._tasks.values(), \
            "deleted task instance, call task_self() again!"

        # bind worker to task self
        worker._set_task(self)

        # add worker clients to engine
        for client in worker._engine_clients():
            self._engine.add(client)

    def _resume_thread(self):
        """Resume task - called from another thread."""
        self._suspend_cond.notify_all()

    def _resume(self):
        """Resume task - called from self thread."""
        assert self.thread == threading.currentThread()
        try:
            try:
                self._reset()
                self._run(self.timeout)
            except EngineTimeoutException:
                raise TimeoutError()
            except EngineAbortException, exc:
                self._terminate(exc.kill)
            except EngineAlreadyRunningError:
                raise AlreadyRunningError("task engine is already running")
        finally:
            # task becomes joinable
            self._join_cond.acquire()
            self._suspend_cond.atomic_inc()
            self._join_cond.notifyAll()
            self._join_cond.release()

    def resume(self, timeout=None):
        """
        Resume task. If task is task_self(), workers are executed in the
        calling thread so this method will block until all (non-autoclosing)
        workers have finished. This is always the case for a single-threaded
        application (eg. which doesn't create other Task() instance than
        task_self()). Otherwise, the current thread doesn't block. In that
        case, you may then want to call task_wait() to wait for completion.

        Warning: the timeout parameter can be used to set an hard limit of
        task execution time (in seconds). In that case, a TimeoutError
        exception is raised if this delay is reached. Its value is 0 by
        default, which means no task time limit (TimeoutError is never
        raised). In order to set a maximum delay for individual command
        execution, you should use Task.shell()'s timeout parameter instead.
        """
        # If you change options here, check Task.run() compatibility.

        self.timeout = timeout

        self._suspend_cond.atomic_dec()

        if self._is_task_self():
            self._resume()
        else:
            self._resume_thread()

    def run(self, command=None, **kwargs):
        """
        With arguments, it will schedule a command exactly like a Task.shell()
        would have done it and run it.
        This is the easiest way to simply run a command.

        >>> task.run("hostname", nodes="foo")

        Without argument, it starts all outstanding actions. 
        It behaves like Task.resume().

        >>> task.shell("hostname", nodes="foo")
        >>> task.shell("hostname", nodes="bar")
        >>> task.run()

        When used with a command, you can set a maximum delay of individual
        command execution with the help of the timeout parameter (see
        Task.shell's parameters). You can then listen for ev_timeout() events
        in your Worker event handlers, or use num_timeout() or
        iter_keys_timeout() afterwards.
        But, when used as an alias to Task.resume(), the timeout parameter
        sets an hard limit of task execution time. In that case, a TimeoutError
        exception is raised if this delay is reached.
        """
        worker = None
        timeout = None

        # Both resume() and shell() support a 'timeout' parameter. We need a
        # trick to behave correctly for both cases.
        #
        # Here, we mock: task.resume(10)
        if type(command) in (int, float):
            timeout = command
            command = None
        # Here, we mock: task.resume(timeout=10)
        elif 'timeout' in kwargs and command is None:
            timeout = kwargs.pop('timeout')
        # All other cases mean a classical: shell(...)
        # we mock: task.shell("mycommand", [timeout=..., ...])
        elif command is not None:
            worker = self.shell(command, **kwargs)

        self.resume(timeout)

        return worker

    @tasksyncmethod()
    def _suspend_wait(self):
        """Suspend request received."""
        assert task_self() == self
        # atomically set suspend state
        self._suspend_lock.acquire()
        self._suspended = True
        self._suspend_lock.release()

        # wait for special suspend condition, while releasing l_run
        self._suspend_cond.wait_check(self._run_lock)

        # waking up, atomically unset suspend state
        self._suspend_lock.acquire()
        self._suspended = False
        self._suspend_lock.release()
            
    def suspend(self):
        """
        Suspend task execution. This method may be called from another
        task (thread-safe). The function returns False if the task
        cannot be suspended (eg. it's not running), or returns True if
        the task has been successfully suspended.
        To resume a suspended task, use task.resume().
        """
        # first of all, increase suspend count
        self._suspend_cond.atomic_inc()

        # call synchronized suspend method
        self._suspend_wait()

        # wait for stopped task
        self._run_lock.acquire()    # run_lock ownership transfer
        
        # get result: are we really suspended or just stopped?
        result = True
        self._suspend_lock.acquire()
        if not self._suspended:
            # not acknowledging suspend state, task is stopped
            result = False
            self._run_lock.release()
        self._suspend_lock.release()
        return result

    @tasksyncmethod()
    def _abort(self, kill=False):
        """Abort request received."""
        assert task_self() == self
        # raise an EngineAbortException when task is running
        self._quit = True
        self._engine.abort(kill)

    def abort(self, kill=False):
        """
        Abort a task. Aborting a task removes (and stops when needed)
        all workers. If optional parameter kill is True, the task
        object is unbound from the current thread, so calling
        task_self() creates a new Task object.
        """
        if not self._run_lock.acquire(0):
            # self._run_lock is locked, try to call synchronized method
            self._abort(kill)
            # but there is no guarantee that it has really been called, as the
            # task could have aborted during the same time, so we use polling
            while not self._run_lock.acquire(0):
                sleep(0.001)
        # in any case, once _run_lock has been acquired, confirm abort
        self._quit = True
        self._run_lock.release()
        if self._is_task_self():
            self._terminate(kill)
        else:
            # abort on stopped/suspended task
            self._suspend_cond.notify_all()

    def _terminate(self, kill):
        """
        Abort completion subroutine.
        """
        assert self._quit == True
        self._terminated = True

        if kill:
            # invalidate dispatch port
            self._dispatch_port = None
        # clear engine
        self._engine.clear(clear_ports=kill)
        if kill:
            self._engine.release()
            self._engine = None

        # clear result objects
        self._reset()

        # unlock any remaining threads that are waiting for our
        # termination (late join()s)
        # must be called after _terminated is set to True
        self._join_cond.acquire()
        self._join_cond.notifyAll()
        self._join_cond.release()

        # destroy task if needed
        if kill:
            Task._task_lock.acquire()
            try:
                del Task._tasks[threading.currentThread()]
            finally:
                Task._task_lock.release()

    def join(self):
        """
        Suspend execution of the calling thread until the target task
        terminates, unless the target task has already terminated.
        """
        self._join_cond.acquire()
        try:
            if self._suspend_cond.suspend_count > 0 and not self._suspended:
                # ignore stopped task
                return
            if self._terminated:
                # ignore join() on dead task
                return
            self._join_cond.wait()
        finally:
            self._join_cond.release()

    def running(self):
        """
        Return True if the task is running.
        """
        return self._engine and self._engine.running

    def _reset(self):
        """
        Reset buffers and retcodes management variables.
        """
        # check and reset stdout MsgTree
        if self.default("stdout_msgtree"):
            if not self._msgtree:
                self._msgtree = MsgTree()
            self._msgtree.clear()
        else:
            self._msgtree = None
        # check and reset stderr MsgTree
        if self.default("stderr_msgtree"):
            if not self._errtree:
                self._errtree = MsgTree()
            self._errtree.clear()
        else:
            self._errtree = None
        # other re-init's
        self._d_source_rc = {}
        self._d_rc_sources = {}
        self._max_rc = 0
        self._timeout_sources.clear()

    def _msg_add(self, source, msg):
        """
        Add a worker message associated with a source.
        """
        msgtree = self._msgtree
        if msgtree is not None:
            msgtree.add(source, msg)

    def _errmsg_add(self, source, msg):
        """
        Add a worker error message associated with a source.
        """
        errtree = self._errtree
        if errtree is not None:
            errtree.add(source, msg)

    def _rc_set(self, source, rc, override=True):
        """
        Add a worker return code associated with a source.
        """
        if not override and self._d_source_rc.has_key(source):
            return

        # store rc by source
        self._d_source_rc[source] = rc

        # store source by rc
        self._d_rc_sources.setdefault(rc, set()).add(source)
        
        # update max rc
        if rc > self._max_rc:
            self._max_rc = rc

    def _timeout_add(self, source):
        """
        Add a worker timeout associated with a source.
        """
        # store source in timeout set
        self._timeout_sources.add(source)

    def _msg_by_source(self, source):
        """
        Get a message by its source (worker, key).
        """
        if self._msgtree is None:
            raise TaskMsgTreeError("stdout_msgtree not set")
        s = self._msgtree.get(source)
        if s is None:
            return None
        return str(s)

    def _errmsg_by_source(self, source):
        """
        Get an error message by its source (worker, key).
        """
        if self._errtree is None:
            raise TaskMsgTreeError("stderr_msgtree not set")
        s = self._errtree.get(source)
        if s is None:
            return None
        return str(s)

    def _call_tree_matcher(self, tree_match_func, match_keys=None, worker=None):
        """Call identified tree matcher (items, walk) method with options."""
        if isinstance(match_keys, basestring): # change to str for Python 3
            raise TypeError("Sequence of keys/nodes expected for 'match_keys'.")
        # filter by worker and optionally by matching keys
        if worker and match_keys is None:
            match = lambda k: k[0] is worker
        elif worker and match_keys is not None:
            match = lambda k: k[0] is worker and k[1] in match_keys
        elif match_keys:
            match = lambda k: k[1] in match_keys
        else:
            match = None
        # Call tree matcher function (items or walk)
        return tree_match_func(match, itemgetter(1))
    
    def _rc_by_source(self, source):
        """
        Get a return code by its source (worker, key).
        """
        return self._d_source_rc[source]
   
    def _rc_iter_by_key(self, key):
        """
        Return an iterator over return codes for the given key.
        """
        for (w, k), rc in self._d_source_rc.iteritems():
            if k == key:
                yield rc

    def _rc_iter_by_worker(self, worker, match_keys=None):
        """
        Return an iterator over return codes and keys list for a
        specific worker and optional matching keys.
        """
        if match_keys:
            # Use the items iterator for the underlying dict.
            for rc, src in self._d_rc_sources.iteritems():
                keys = [t[1] for t in src if t[0] is worker and \
                                             t[1] in match_keys]
                if len(keys) > 0:
                    yield rc, keys
        else:
            for rc, src in self._d_rc_sources.iteritems():
                keys = [t[1] for t in src if t[0] is worker]
                if len(keys) > 0:
                    yield rc, keys

    def _krc_iter_by_worker(self, worker):
        """
        Return an iterator over key, rc for a specific worker.
        """
        for rc, src in self._d_rc_sources.iteritems():
            for w, k in src:
                if w is worker:
                    yield k, rc

    def _num_timeout_by_worker(self, worker):
        """
        Return the number of timed out "keys" for a specific worker.
        """
        cnt = 0
        for (w, k) in self._timeout_sources:
            if w is worker:
                cnt += 1
        return cnt

    def _iter_keys_timeout_by_worker(self, worker):
        """
        Iterate over timed out keys (ie. nodes) for a specific worker.
        """
        for (w, k) in self._timeout_sources:
            if w is worker:
                yield k

    def _flush_buffers_by_worker(self, worker):
        """
        Remove any messages from specified worker.
        """
        if self._msgtree is not None:
            self._msgtree.remove(lambda k: k[0] == worker)

    def _flush_errors_by_worker(self, worker):
        """
        Remove any error messages from specified worker.
        """
        if self._errtree is not None:
            self._errtree.remove(lambda k: k[0] == worker)

    def key_buffer(self, key):
        """
        Get buffer for a specific key. When the key is associated
        to multiple workers, the resulting buffer will contain
        all workers content that may overlap. This method returns an
        empty buffer if key is not found in any workers.
        """
        msgtree = self._msgtree
        if msgtree is None:
            raise TaskMsgTreeError("stdout_msgtree not set")
        select_key = lambda k: k[1] == key
        return "".join(imap(str, msgtree.messages(select_key)))
    
    node_buffer = key_buffer

    def key_error(self, key):
        """
        Get error buffer for a specific key. When the key is associated
        to multiple workers, the resulting buffer will contain all
        workers content that may overlap. This method returns an empty
        error buffer if key is not found in any workers.
        """
        errtree = self._errtree
        if errtree is None:
            raise TaskMsgTreeError("stderr_msgtree not set")
        select_key = lambda k: k[1] == key
        return "".join(imap(str, errtree.messages(select_key)))
    
    node_error = key_error

    def key_retcode(self, key):
        """
        Return return code for a specific key. When the key is
        associated to multiple workers, return the max return
        code from these workers. Raises a KeyError if key is not found
        in any finished workers.
        """
        codes = list(self._rc_iter_by_key(key))
        if not codes:
            raise KeyError(key)
        return max(codes)
    
    node_retcode = key_retcode

    def max_retcode(self):
        """
        Get max return code encountered during last run.

        How retcodes work
        =================
          If the process exits normally, the return code is its exit
          status. If the process is terminated by a signal, the return
          code is 128 + signal number.
        """
        return self._max_rc

    def iter_buffers(self, match_keys=None):
        """
        Iterate over buffers, returns a tuple (buffer, keys). For remote
        workers (Ssh), keys are list of nodes. In that case, you should use
        NodeSet.fromlist(keys) to get a NodeSet instance (which is more
        convenient and efficient):

        Optional parameter match_keys add filtering on these keys.

        Usage example:

        >>> for buffer, nodelist in task.iter_buffers():
        ...     print NodeSet.fromlist(nodelist)
        ...     print buffer
        """
        msgtree = self._msgtree
        if msgtree is None:
            raise TaskMsgTreeError("stdout_msgtree not set")
        return self._call_tree_matcher(msgtree.walk, match_keys)

    def iter_errors(self, match_keys=None):
        """
        Iterate over error buffers, returns a tuple (buffer, keys).

        See iter_buffers().
        """
        errtree = self._errtree
        if errtree is None:
            raise TaskMsgTreeError("stderr_msgtree not set")
        return self._call_tree_matcher(errtree.walk, match_keys)
        
    def iter_retcodes(self, match_keys=None):
        """
        Iterate over return codes, returns a tuple (rc, keys).

        Optional parameter match_keys add filtering on these keys.

        How retcodes work
        =================
          If the process exits normally, the return code is its exit
          status. If the process is terminated by a signal, the return
          code is 128 + signal number.
        """
        if match_keys:
            # Use the items iterator for the underlying dict.
            for rc, src in self._d_rc_sources.iteritems():
                keys = [t[1] for t in src if t[1] in match_keys]
                yield rc, keys
        else:
            for rc, src in self._d_rc_sources.iteritems():
                yield rc, [t[1] for t in src]

    def num_timeout(self):
        """
        Return the number of timed out "keys" (ie. nodes).
        """
        return len(self._timeout_sources)

    def iter_keys_timeout(self):
        """
        Iterate over timed out keys (ie. nodes).
        """
        for (w, k) in self._timeout_sources:
            yield k

    def flush_buffers(self):
        """
        Flush all task messages (from all task workers).
        """
        if self._msgtree is not None:
            self._msgtree.clear()

    def flush_errors(self):
        """
        Flush all task error messages (from all task workers).
        """
        if self._errtree is not None:
            self._errtree.clear()

    @classmethod
    def wait(cls, from_thread):
        """
        Class method that blocks calling thread until all tasks have
        finished (from a ClusterShell point of view, for instance,
        their task.resume() return). It doesn't necessarly mean that
        associated threads have finished.
        """
        Task._task_lock.acquire()
        try:
            tasks = Task._tasks.copy()
        finally:
            Task._task_lock.release()
        for thread, task in tasks.iteritems():
            if thread != from_thread:
                task.join()

    def pchannel(self, gateway, metaworker): #gw_invoke_cmd):
        """Get propagation channel for gateway (create one if needed)"""
        # create channel if needed
        if gateway not in self.pwrks:
            chan = PropagationChannel(self)
            # invoke gateway
            timeout = None # FIXME: handle timeout for gateway channels
            worker = self.shell(metaworker.invoke_gateway, nodes=gateway,
                                handler=chan, timeout=timeout, tree=False)
            self.pwrks[gateway] = worker
        else:
            worker = self.pwrks[gateway]
            chan = worker.eh
        
        if metaworker not in self.pmwkrs:
            mw = self.pmwkrs[metaworker] = set()
        else:
            mw = self.pmwkrs[metaworker]
        if worker not in mw:
            #print >>sys.stderr, "pchannel++"
            worker.metarefcnt += 1
            mw.add(worker)
        return chan

    def _pchannel_release(self, metaworker):
        """Release propagation channel"""
        if metaworker in self.pmwkrs:
            for worker in self.pmwkrs[metaworker]:
                #print >>sys.stderr, "pchannel_release2 %s" % worker
                worker.metarefcnt -= 1
                if worker.metarefcnt == 0:
                    #print >>sys.stderr, "worker abort"
                    worker.eh._close()
                    #worker.abort()
            

def task_self():
    """
    Return the current Task object, corresponding to the caller's thread of
    control (a Task object is always bound to a specific thread). This function
    provided as a convenience is available in the top-level ClusterShell.Task
    package namespace.
    """
    return Task(thread=threading.currentThread())

def task_wait():
    """
    Suspend execution of the calling thread until all tasks terminate, unless
    all tasks have already terminated. This function is provided as a
    convenience and is available in the top-level ClusterShell.Task package
    namespace.
    """
    Task.wait(threading.currentThread())

def task_terminate():
    """
    Destroy the Task instance bound to the current thread. A next call to
    task_self() will create a new Task object. Not to be called from a signal
    handler. This function provided as a convenience is available in the
    top-level ClusterShell.Task package namespace.
    """
    task_self().abort(kill=True)

def task_cleanup():
    """
    Cleanup routine to destroy all created tasks. This function provided as a
    convenience is available in the top-level ClusterShell.Task package
    namespace. This is mainly used for testing purposes and should be avoided
    otherwise. task_cleanup() may be called from any threads but not from a
    signal handler.
    """
    # be sure to return to a clean state (no task at all)
    while True:
        Task._task_lock.acquire()
        try:
            tasks = Task._tasks.copy()
            if len(tasks) == 0:
                break
        finally:
            Task._task_lock.release()
        # send abort to all known tasks (it's needed to retry as we may have
        # missed the engine notification window (it was just exiting, which is
        # quite a common case if we didn't task_join() previously), or we may
        # have lost some task's dispatcher port messages.
        for task in tasks.itervalues():
            task.abort(kill=True)
        # also, for other task than self, task.abort() is async and performed
        # through an EngineAbortException, so tell the Python scheduler to give
        # up control to raise this exception (handled by task._terminate())...
        sleep(0.001)

########NEW FILE########
__FILENAME__ = Topology
#!/usr/bin/env python
#
# Copyright CEA/DAM/DIF (2010, 2011, 2012)
#  Contributor: Henri DOREAU <henri.doreau@cea.fr>
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
ClusterShell topology module

This module contains the network topology parser and its related
classes. These classes are used to build a topology tree of nodegroups
according to the configuration file.

This file must be written using the following syntax:

# for now only [Main] tree is taken in account:
[Main]
admin: first_level_gateways[0-10]
first_level_gateways[0-10]: second_level_gateways[0-100]
second_level_gateways[0-100]: nodes[0-2000]
...
"""

import ConfigParser

from ClusterShell.NodeSet import NodeSet


class TopologyError(Exception):
    """topology parser error to report invalid configurations or parsing
    errors
    """

class TopologyNodeGroup(object):
    """Base element for in-memory representation of the propagation tree.
    Contains a nodeset, with parent-children relationships with other
    instances.
    """
    def __init__(self, nodeset=None):
        """initialize a new TopologyNodeGroup instance."""
        # Base nodeset
        self.nodeset = nodeset
        # Parent TopologyNodeGroup (TNG) instance
        self.parent = None
        # List of children TNG instances
        self._children = []
        self._children_len = 0
        # provided for convenience
        self._children_ns = None

    def printable_subtree(self, prefix=''):
        """recursive method that returns a printable version the subtree from
        the current node with a nice presentation
        """
        res = ''
        # For now, it is ok to use a recursive method here as we consider that
        # tree depth is relatively small.
        if self.parent is None:
            # root
            res = '%s\n' % str(self.nodeset)
        elif self.parent.parent is None:
            # first level
            if not self._is_last():
                res = '|- %s\n' % str(self.nodeset)
            else:
                res = '`- %s\n' % str(self.nodeset)
        else:
            # deepest levels...
            if not self.parent._is_last():
                prefix += '|  '
            else:
                # fix last line
                prefix += '   '
            if not self._is_last():
                res = '%s|- %s\n' % (prefix, str(self.nodeset))
            else:
                res = '%s`- %s\n' % (prefix, str(self.nodeset))
        # perform recursive calls to print out every node
        for child in self._children:
            res += child.printable_subtree(prefix)
        return res

    def add_child(self, child):
        """add a child to the children list and define the current instance as
        its parent
        """
        assert isinstance(child, TopologyNodeGroup)

        if child in self._children:
            return
        child.parent = self
        self._children.append(child)
        if self._children_ns is None:
            self._children_ns = NodeSet()
        self._children_ns.add(child.nodeset)

    def clear_child(self, child, strict=False):
        """remove a child"""
        try:
            self._children.remove(child)
            self._children_ns.difference_update(child.nodeset)
            if len(self._children_ns) == 0:
                self._children_ns = None
        except ValueError:
            if strict:
                raise

    def clear_children(self):
        """delete all children"""
        self._children = []
        self._children_ns = None

    def children(self):
        """get the children list"""
        return self._children

    def children_ns(self):
        """return the children as a nodeset"""
        return self._children_ns

    def children_len(self):
        """returns the number of children as the sum of the size of the
        children's nodeset
        """
        if self._children_ns is None:
            return 0
        else:
            return len(self._children_ns)

    def _is_last(self):
        """used to display the subtree: we won't prefix the line the same way if
        the current instance is the last child of the children list of its
        parent.
        """
        return self.parent._children[-1::][0] == self

    def __str__(self):
        """printable representation of the nodegroup"""
        return '<TopologyNodeGroup (%s)>' % str(self.nodeset)

class TopologyTree(object):
    """represent a simplified network topology as a tree of machines to use to
    connect to other ones
    """
    class TreeIterator:
        """efficient tool for tree-traversal"""
        def __init__(self, tree):
            """we do simply manage a stack with the remaining nodes"""
            self._stack = [tree.root]

        def next(self):
            """return the next node in the stack or raise a StopIteration
            exception if the stack is empty
            """
            if len(self._stack) > 0 and self._stack[0] is not None:
                node = self._stack.pop()
                self._stack += node.children()
                return node
            else:
                raise StopIteration()

    def __init__(self):
        """initialize a new TopologyTree instance."""
        self.root = None
        self.groups = []

    def load(self, rootnode):
        """load topology tree"""
        self.root = rootnode

        stack = [rootnode]
        while len(stack) > 0:
            curr = stack.pop()
            self.groups.append(curr)
            if curr.children_len() > 0:
                stack += curr.children()

    def __iter__(self):
        """provide an iterator on the tree's elements"""
        return TopologyTree.TreeIterator(self)

    def __str__(self):
        """printable representation of the tree"""
        if self.root is None:
            return '<TopologyTree instance (empty)>'
        return self.root.printable_subtree()

class TopologyRoute(object):
    """A single route between two nodesets"""
    def __init__(self, src_ns, dst_ns):
        """both src_ns and dst_ns are expected to be non-empty NodeSet
        instances
        """
        self.src = src_ns
        self.dst = dst_ns
        if len(src_ns & dst_ns) != 0:
            raise TopologyError(
                'Source and destination nodesets overlap')

    def dest(self, nodeset=None):
        """get the route's destination. The optionnal argument serves for
        convenience and provides a way to use the method for a subset of the
        whole source nodeset
        """
        if nodeset is None or nodeset in self.src:
            return self.dst
        else:
            return None

    def __str__(self):
        """printable representation"""
        return '%s -> %s' % (str(self.src), str(self.dst))

class TopologyRoutingTable(object):
    """This class provides a convenient way to store and manage topology
    routes
    """
    def __init__(self):
        """Initialize a new TopologyRoutingTable instance."""
        self._routes = []
        self.aggregated_src = NodeSet()
        self.aggregated_dst = NodeSet()

    def add_route(self, route):
        """add a new route to the table. The route argument is expected to be a
        TopologyRoute instance
        """
        if self._introduce_circular_reference(route):
            raise TopologyError(
                'Loop detected! Cannot add route %s' % str(route))
        if self._introduce_convergent_paths(route):
            raise TopologyError(
                'Convergent path detected! Cannot add route %s' % str(route))

        self._routes.append(route)

        self.aggregated_src.add(route.src)
        self.aggregated_dst.add(route.dst)

    def connected(self, src_ns):
        """find out and return the aggregation of directly connected children
        from src_ns.
        Argument src_ns is expected to be a NodeSet instance. Result is returned
        as a NodeSet instance
        """
        next_hop = NodeSet.fromlist([dst for dst in \
            [route.dest(src_ns) for route in self._routes] if dst is not None])
        if len(next_hop) == 0:
            return None
        return next_hop

    def __str__(self):
        """printable representation"""
        return '\n'.join([str(route) for route in self._routes])

    def __iter__(self):
        """return an iterator over the list of rotues"""
        return iter(self._routes)

    def _introduce_circular_reference(self, route):
        """check whether the last added route adds a topology loop or not"""
        current_ns = route.dst
        # iterate over the destinations until we find None or we come back on
        # the src
        while True:
            _dest = self.connected(current_ns)
            if _dest is None or len(_dest) == 0:
                return False
            if len(_dest & route.src) != 0:
                return True
            current_ns = _dest

    def _introduce_convergent_paths(self, route):
        """check for undesired convergent paths"""
        for known_route in self._routes:
            # source cannot be a superset of an already known destination
            if route.src > known_route.dst:
                return True
            # same thing...
            if route.dst < known_route.src:
                return True
            # two different nodegroups cannot point to the same one
            if len(route.dst & known_route.dst) != 0 \
                and route.src != known_route.src:
                return True
        return False

class TopologyGraph(object):
    """represent a complete network topology by storing every "can reach"
    relations between nodes.
    """
    def __init__(self):
        """initialize a new TopologyGraph instance."""
        self._routing = TopologyRoutingTable()
        self._nodegroups = {}
        self._root = ''

    def add_route(self, src_ns, dst_ns):
        """add a new route from src nodeset to dst nodeset. The destination
        nodeset must not overlap with already known destination nodesets
        (otherwise a TopologyError is raised)
        """
        assert isinstance(src_ns, NodeSet)
        assert isinstance(dst_ns, NodeSet)

        #print 'adding %s -> %s' % (str(src_ns), str(dst_ns))
        self._routing.add_route(TopologyRoute(src_ns, dst_ns))

    def dest(self, from_nodeset):
        """return the aggregation of the destinations for a given nodeset"""
        return self._routing.connected(from_nodeset)

    def to_tree(self, root):
        """convert the routing table to a topology tree of nodegroups"""
        # convert the routing table into a table of linked TopologyNodeGroup's
        self._routes_to_tng()
        # ensure this is a valid pseudo-tree
        self._validate(root)
        tree = TopologyTree()
        tree.load(self._nodegroups[self._root])
        return tree

    def __str__(self):
        """printable representation of the graph"""
        res = '<TopologyGraph>\n'
        res += '\n'.join(['%s: %s' % (str(k), str(v)) for k, v in \
            self._nodegroups.iteritems()])
        return res

    def _routes_to_tng(self):
        """convert the routing table into a graph of TopologyNodeGroup
        instances. Loops are not very expensive here as the number of routes
        will always be much lower than the number of nodes.
        """
        # instanciate nodegroups as biggest groups of nodes sharing both parent
        # and destination
        aggregated_src = self._routing.aggregated_src
        for route in self._routing:
            self._nodegroups[str(route.src)] = TopologyNodeGroup(route.src)
            # create a nodegroup for the destination if it is a leaf group.
            # Otherwise, it will be created as src for another route
            leaf = route.dst - aggregated_src
            if len(leaf) > 0:
                self._nodegroups[str(leaf)] = TopologyNodeGroup(leaf)
        
        # add the parent <--> children relationships
        for group in self._nodegroups.itervalues():
            dst_ns = self._routing.connected(group.nodeset)
            if dst_ns is not None:
                for child in self._nodegroups.itervalues():
                    if child.nodeset in dst_ns:
                        group.add_child(child)

    def _validate(self, root):
        """ensure that the graph is valid for conversion to tree"""
        if len(self._nodegroups) == 0:
            raise TopologyError("No route found in topology definition!")

        # ensure that every node is reachable
        src_all = self._routing.aggregated_src
        dst_all = self._routing.aggregated_dst

        res = [(k, v) for k, v in self._nodegroups.items() if root in v.nodeset]
        if len(res) > 0:
            kgroup, group = res[0]
            del self._nodegroups[kgroup]
            self._nodegroups[root] = group
        else:
            raise TopologyError('"%s" is not a valid root node!' % root)
        
        self._root = root

class TopologyParser(ConfigParser.ConfigParser):
    """This class offers a way to interpret network topologies supplied under
    the form :

    # Comment
    <these machines> : <can reach these ones>
    """
    def __init__(self):
        """instance wide variables initialization"""
        ConfigParser.ConfigParser.__init__(self)
        self.optionxform = str # case sensitive parser

        self._topology = {}
        self.graph = None
        self._tree = None

    def load(self, filename):
        """read a given topology configuration file and store the results in
        self._routes. Then build a propagation tree.
        """
        try:
            self.read(filename)
            self._topology = self.items("Main")
        except ConfigParser.Error:
            raise TopologyError(
                'Invalid configuration file: %s' % filename)
        self._build_graph()

    def _build_graph(self):
        """build a network topology graph according to the information we got
        from the configuration file.
        """
        self.graph = TopologyGraph()
        for src, dst in self._topology:
            self.graph.add_route(NodeSet(src), NodeSet(dst))

    def tree(self, root, force_rebuild=False):
        """Return a previously generated propagation tree or build it if
        required. As rebuilding tree can be quite expensive, once built,
        the propagation tree is cached. you can force a re-generation
        using the optionnal `force_rebuild' parameter.
        """
        if self._tree is None or force_rebuild:
            self._tree = self.graph.to_tree(root)
        return self._tree


########NEW FILE########
__FILENAME__ = EngineClient
#
# Copyright CEA/DAM/DIF (2009, 2010, 2011, 2012)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
EngineClient

ClusterShell engine's client interface.

An engine client is similar to a process, you can start/stop it, read data from
it and write data to it.
"""

import errno
import os
import Queue
import thread

from ClusterShell.Worker.fastsubprocess import Popen, PIPE, STDOUT, \
    set_nonblock_flag

from ClusterShell.Engine.Engine import EngineBaseTimer


class EngineClientException(Exception):
    """Generic EngineClient exception."""

class EngineClientEOF(EngineClientException):
    """EOF from client."""

class EngineClientError(EngineClientException):
    """Base EngineClient error exception."""

class EngineClientNotSupportedError(EngineClientError):
    """Operation not supported by EngineClient."""


class EngineClient(EngineBaseTimer):
    """
    Abstract class EngineClient.
    """

    def __init__(self, worker, stderr, timeout, autoclose):
        """
        Initializer. Should be called from derived classes.
        """
        EngineBaseTimer.__init__(self, timeout, -1, autoclose)

        # engine-friendly variables
        self._events = 0                    # current configured set of
                                            # interesting events (read,
                                            # write) for client
        self._new_events = 0                # new set of interesting events
        self._reg_epoch = 0                 # registration generation number

        # read-only public
        self.registered = False             # registered on engine or not
        self.delayable = True               # subject to fanout limit

        self.worker = worker

        # boolean indicating whether stderr is on a separate fd
        self._stderr = stderr

        # associated file descriptors
        self.fd_error = None
        self.fd_reader = None
        self.fd_writer = None

        # initialize error, read and write buffers
        self._ebuf = ""
        self._rbuf = ""
        self._wbuf = ""
        self._weof = False                  # write-ends notification

    def _fire(self):
        """
        Fire timeout timer.
        """
        if self._engine:
            self._engine.remove(self, abort=True, did_timeout=True)

    def _start(self):
        """
        Starts client and returns client instance as a convenience.
        Derived classes (except EnginePort) must implement.
        """
        raise NotImplementedError("Derived classes must implement.")

    def error_fileno(self):
        """
        Return the standard error reader file descriptor as an integer.
        """
        return self.fd_error

    def reader_fileno(self):
        """
        Return the reader file descriptor as an integer.
        """
        return self.fd_reader
    
    def writer_fileno(self):
        """
        Return the writer file descriptor as an integer.
        """
        return self.fd_writer

    def _close(self, abort, flush, timeout):
        """
        Close client. Called by the engine after client has been
        unregistered. This method should handle all termination types
        (normal or aborted) with some options like flushing I/O buffers
        or setting timeout status.

        Derived classes must implement.
        """
        raise NotImplementedError("Derived classes must implement.")

    def _set_reading(self):
        """
        Set reading state.
        """
        self._engine.set_reading(self)

    def _set_reading_error(self):
        """
        Set error reading state.
        """
        self._engine.set_reading_error(self)

    def _set_writing(self):
        """
        Set writing state.
        """
        self._engine.set_writing(self)

    def _read(self, size=65536):
        """
        Read data from process.
        """
        result = os.read(self.fd_reader, size)
        if not len(result):
            raise EngineClientEOF()
        self._set_reading()
        return result

    def _readerr(self, size=65536):
        """
        Read error data from process.
        """
        result = os.read(self.fd_error, size)
        if not len(result):
            raise EngineClientEOF()
        self._set_reading_error()
        return result

    def _handle_read(self):
        """
        Handle a read notification. Called by the engine as the result of an
        event indicating that a read is available.
        """
        raise NotImplementedError("Derived classes must implement.")

    def _handle_error(self):
        """
        Handle a stderr read notification. Called by the engine as the result
        of an event indicating that a read is available on stderr.
        """
        raise NotImplementedError("Derived classes must implement.")

    def _handle_write(self):
        """
        Handle a write notification. Called by the engine as the result of an
        event indicating that a write can be performed now.
        """
        if len(self._wbuf) > 0:
            try:
                wcnt = os.write(self.fd_writer, self._wbuf)
            except OSError, exc:
                if (exc.errno == errno.EAGAIN):
                    self._set_writing()
                    return
                raise
            if wcnt > 0:
                # dequeue written buffer
                self._wbuf = self._wbuf[wcnt:]
                # check for possible ending
                if self._weof and not self._wbuf:
                    self._close_writer()
                else:
                    self._set_writing()
    
    def _exec_nonblock(self, commandlist, shell=False, env=None):
        """
        Utility method to launch a command with stdin/stdout file
        descriptors configured in non-blocking mode.
        """
        full_env = None
        if env:
            full_env = os.environ.copy()
            full_env.update(env)

        if self._stderr:
            stderr_setup = PIPE
        else:
            stderr_setup = STDOUT

        # Launch process in non-blocking mode
        proc = Popen(commandlist, bufsize=0, stdin=PIPE, stdout=PIPE,
            stderr=stderr_setup, shell=shell, env=full_env)

        if self._stderr:
            self.fd_error = proc.stderr
        self.fd_reader = proc.stdout
        self.fd_writer = proc.stdin

        return proc

    def _readlines(self):
        """
        Utility method to read client lines
        """
        # read a chunk of data, may raise eof
        readbuf = self._read()
        assert len(readbuf) > 0, "assertion failed: len(readbuf) > 0"

        # Current version implements line-buffered reads. If needed, we could
        # easily provide direct, non-buffered, data reads in the future.

        buf = self._rbuf + readbuf
        lines = buf.splitlines(True)
        self._rbuf = ""
        for line in lines:
            if line.endswith('\n'):
                if line.endswith('\r\n'):
                    yield line[:-2] # trim CRLF
                else:
                    # trim LF
                    yield line[:-1] # trim LF
            else:
                # keep partial line in buffer
                self._rbuf = line
                # breaking here

    def _readerrlines(self):
        """
        Utility method to read client lines
        """
        # read a chunk of data, may raise eof
        readerrbuf = self._readerr()
        assert len(readerrbuf) > 0, "assertion failed: len(readerrbuf) > 0"

        buf = self._ebuf + readerrbuf
        lines = buf.splitlines(True)
        self._ebuf = ""
        for line in lines:
            if line.endswith('\n'):
                if line.endswith('\r\n'):
                    yield line[:-2] # trim CRLF
                else:
                    # trim LF
                    yield line[:-1] # trim LF
            else:
                # keep partial line in buffer
                self._ebuf = line
                # breaking here

    def _write(self, buf):
        """
        Add some data to be written to the client.
        """
        fd = self.fd_writer
        if fd:
            self._wbuf += buf
            # give it a try now (will set writing flag anyhow)
            self._handle_write()
        else:
            # bufferize until pipe is ready
            self._wbuf += buf

    def _set_write_eof(self):
        self._weof = True
        if not self._wbuf:
            # sendq empty, try to close writer now
            self._close_writer()

    def _close_writer(self):
        if self.fd_writer is not None:
            self._engine.unregister_writer(self)
            os.close(self.fd_writer)
            self.fd_writer = None

    def abort(self):
        """
        Abort processing any action by this client.
        """
        if self._engine:
            self._engine.remove(self, abort=True)

class EnginePort(EngineClient):
    """
    An EnginePort is an abstraction object to deliver messages
    reliably between tasks.
    """

    class _Msg:
        """Private class representing a port message.
        
        A port message may be any Python object.
        """

        def __init__(self, user_msg, sync):
            self._user_msg = user_msg
            self._sync_msg = sync
            self.reply_lock = thread.allocate_lock()
            self.reply_lock.acquire()

        def get(self):
            """
            Get and acknowledge message.
            """
            self.reply_lock.release()
            return self._user_msg

        def sync(self):
            """
            Wait for message acknowledgment if needed.
            """
            if self._sync_msg:
                self.reply_lock.acquire()

    def __init__(self, task, handler=None, autoclose=False):
        """
        Initialize EnginePort object.
        """
        EngineClient.__init__(self, None, False, -1, autoclose)
        self.task = task
        self.eh = handler
        # ports are no subject to fanout
        self.delayable = False

        # Port messages queue
        self._msgq = Queue.Queue(self.task.default("port_qlimit"))

        # Request pipe
        (readfd, writefd) = os.pipe()
        # Set nonblocking flag
        set_nonblock_flag(readfd)
        set_nonblock_flag(writefd)
        self.fd_reader = readfd
        self.fd_writer = writefd

    def _start(self):
        return self

    def _close(self, abort, flush, timeout):
        """
        Close port pipes.
        """
        if not self._msgq.empty():
            # purge msgq
            try:
                while not self._msgq.empty():
                    pmsg = self._msgq.get(block=False)
                    if self.task.info("debug", False):
                        self.task.info("print_debug")(self.task,
                            "EnginePort: dropped msg: %s" % str(pmsg.get()))
            except Queue.Empty:
                pass
        self._msgq = None
        os.close(self.fd_reader)
        self.fd_reader = None
        os.close(self.fd_writer)
        self.fd_writer = None

    def _handle_read(self):
        """
        Handle a read notification. Called by the engine as the result of an
        event indicating that a read is available.
        """
        readbuf = self._read(4096)
        for dummy_char in readbuf:
            # raise Empty if empty (should never happen)
            pmsg = self._msgq.get(block=False)
            self.eh.ev_msg(self, pmsg.get())

    def msg(self, send_msg, send_once=False):
        """
        Port message send method that will wait for acknowledgement
        unless the send_once parameter if set.
        """
        pmsg = EnginePort._Msg(send_msg, not send_once)
        self._msgq.put(pmsg, block=True, timeout=None)
        try:
            ret = os.write(self.writer_fileno(), "M")
        except OSError:
            raise
        pmsg.sync()
        return ret == 1

    def msg_send(self, send_msg):
        """
        Port message send-once method (no acknowledgement).
        """
        self.msg(send_msg, send_once=True)



########NEW FILE########
__FILENAME__ = fastsubprocess
# fastsubprocess - POSIX relaxed revision of subprocess.py
# Based on Python 2.6.4 subprocess.py
# This is a performance oriented version of subprocess module.
# Modified by Stephane Thiell <stephane.thiell@cea.fr>
# Changes:
#   * removed Windows specific code parts
#   * removed pipe for transferring possible exec failure from child to
#     parent, to avoid os.read() blocking call after each fork.
#   * child returns status code 255 on execv failure, which can be
#     handled with Popen.wait().
#   * removed file objects creation using costly fdopen(): this version
#     returns non-blocking file descriptors bound to child
#   * added module method set_nonblock_flag() and used it in Popen().
##
# Original Disclaimer:
#
# For more information about this module, see PEP 324.
#
# This module should remain compatible with Python 2.2, see PEP 291.
#
# Copyright (c) 2003-2005 by Peter Astrand <astrand@lysator.liu.se>
#
# Licensed to PSF under a Contributor Agreement.
# See http://www.python.org/2.4/license for licensing details.

"""_subprocess - Subprocesses with accessible I/O non-blocking file
descriptors

Faster revision of subprocess-like module.
"""

import sys
import os
import types
import gc
import signal

# Exception classes used by this module.
class CalledProcessError(Exception):
    """This exception is raised when a process run by check_call() returns
    a non-zero exit status.  The exit status will be stored in the
    returncode attribute."""
    def __init__(self, returncode, cmd):
        self.returncode = returncode
        self.cmd = cmd
    def __str__(self):
        return "Command '%s' returned non-zero exit status %d" % (self.cmd,
            self.returncode)

import select
import errno
import fcntl

__all__ = ["Popen", "PIPE", "STDOUT", "call", "check_call", \
           "CalledProcessError"]

try:
    MAXFD = os.sysconf("SC_OPEN_MAX")
except:
    MAXFD = 256

_active = []

def _cleanup():
    for inst in _active[:]:
        if inst._internal_poll(_deadstate=sys.maxint) >= 0:
            try:
                _active.remove(inst)
            except ValueError:
                # This can happen if two threads create a new Popen instance.
                # It's harmless that it was already removed, so ignore.
                pass

PIPE = -1
STDOUT = -2


def call(*popenargs, **kwargs):
    """Run command with arguments.  Wait for command to complete, then
    return the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    retcode = call(["ls", "-l"])
    """
    return Popen(*popenargs, **kwargs).wait()


def check_call(*popenargs, **kwargs):
    """Run command with arguments.  Wait for command to complete.  If
    the exit code was zero then return, otherwise raise
    CalledProcessError.  The CalledProcessError object will have the
    return code in the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    check_call(["ls", "-l"])
    """
    retcode = call(*popenargs, **kwargs)
    cmd = kwargs.get("args")
    if cmd is None:
        cmd = popenargs[0]
    if retcode:
        raise CalledProcessError(retcode, cmd)
    return retcode


def set_nonblock_flag(fd):
    """Set non blocking flag to file descriptor fd"""
    old = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, old | os.O_NDELAY)


class Popen(object):
    """A faster Popen"""
    def __init__(self, args, bufsize=0, executable=None,
                 stdin=None, stdout=None, stderr=None,
                 preexec_fn=None, shell=False,
                 cwd=None, env=None, universal_newlines=False):
        """Create new Popen instance."""
        _cleanup()

        self._child_created = False
        if not isinstance(bufsize, (int, long)):
            raise TypeError("bufsize must be an integer")

        self.pid = None
        self.returncode = None
        self.universal_newlines = universal_newlines

        # Input and output objects. The general principle is like
        # this:
        #
        # Parent                   Child
        # ------                   -----
        # p2cwrite   ---stdin--->  p2cread
        # c2pread    <--stdout---  c2pwrite
        # errread    <--stderr---  errwrite
        #
        # On POSIX, the child objects are file descriptors.  On
        # Windows, these are Windows file handles.  The parent objects
        # are file descriptors on both platforms.  The parent objects
        # are None when not using PIPEs. The child objects are None
        # when not redirecting.

        (p2cread, p2cwrite,
         c2pread, c2pwrite,
         errread, errwrite) = self._get_handles(stdin, stdout, stderr)

        self._execute_child(args, executable, preexec_fn,
                            cwd, env, universal_newlines, shell,
                            p2cread, p2cwrite,
                            c2pread, c2pwrite,
                            errread, errwrite)

        if p2cwrite is not None:
            set_nonblock_flag(p2cwrite)
        self.stdin = p2cwrite
        if c2pread is not None:
            set_nonblock_flag(c2pread)
        self.stdout = c2pread
        if errread is not None:
            set_nonblock_flag(errread)
        self.stderr = errread


    def _translate_newlines(self, data):
        data = data.replace("\r\n", "\n")
        data = data.replace("\r", "\n")
        return data


    def __del__(self, sys=sys):
        if not self._child_created:
            # We didn't get to successfully create a child process.
            return
        # In case the child hasn't been waited on, check if it's done.
        self._internal_poll(_deadstate=sys.maxint)
        if self.returncode is None and _active is not None:
            # Child is still running, keep us alive until we can wait on it.
            _active.append(self)


    def communicate(self, input=None):
        """Interact with process: Send data to stdin.  Read data from
        stdout and stderr, until end-of-file is reached.  Wait for
        process to terminate.  The optional input argument should be a
        string to be sent to the child process, or None, if no data
        should be sent to the child.

        communicate() returns a tuple (stdout, stderr)."""

        # Optimization: If we are only using one pipe, or no pipe at
        # all, using select() or threads is unnecessary.
        if [self.stdin, self.stdout, self.stderr].count(None) >= 2:
            stdout = None
            stderr = None
            if self.stdin:
                if input:
                    self.stdin.write(input)
                self.stdin.close()
            elif self.stdout:
                stdout = self.stdout.read()
                self.stdout.close()
            elif self.stderr:
                stderr = self.stderr.read()
                self.stderr.close()
            self.wait()
            return (stdout, stderr)

        return self._communicate(input)


    def poll(self):
        return self._internal_poll()


    def _get_handles(self, stdin, stdout, stderr):
        """Construct and return tupel with IO objects:
        p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
        """
        p2cread, p2cwrite = None, None
        c2pread, c2pwrite = None, None
        errread, errwrite = None, None

        if stdin is None:
            pass
        elif stdin == PIPE:
            p2cread, p2cwrite = os.pipe()
        elif isinstance(stdin, int):
            p2cread = stdin
        else:
            # Assuming file-like object
            p2cread = stdin.fileno()

        if stdout is None:
            pass
        elif stdout == PIPE:
            c2pread, c2pwrite = os.pipe()
        elif isinstance(stdout, int):
            c2pwrite = stdout
        else:
            # Assuming file-like object
            c2pwrite = stdout.fileno()

        if stderr is None:
            pass
        elif stderr == PIPE:
            errread, errwrite = os.pipe()
        elif stderr == STDOUT:
            errwrite = c2pwrite
        elif isinstance(stderr, int):
            errwrite = stderr
        else:
            # Assuming file-like object
            errwrite = stderr.fileno()

        return (p2cread, p2cwrite,
                c2pread, c2pwrite,
                errread, errwrite)


    def _execute_child(self, args, executable, preexec_fn,
                       cwd, env, universal_newlines, shell,
                       p2cread, p2cwrite,
                       c2pread, c2pwrite,
                       errread, errwrite):
        """Execute program (POSIX version)"""

        if isinstance(args, types.StringTypes):
            args = [args]
        else:
            args = list(args)

        if shell:
            args = ["/bin/sh", "-c"] + args

        if executable is None:
            executable = args[0]

        gc_was_enabled = gc.isenabled()
        # Disable gc to avoid bug where gc -> file_dealloc ->
        # write to stderr -> hang.  http://bugs.python.org/issue1336
        gc.disable()
        try:
            self.pid = os.fork()
        except:
            if gc_was_enabled:
                gc.enable()
            raise
        self._child_created = True
        if self.pid == 0:
            # Child
            try:
                # Close parent's pipe ends
                if p2cwrite is not None:
                    os.close(p2cwrite)
                if c2pread is not None:
                    os.close(c2pread)
                if errread is not None:
                    os.close(errread)

                # Dup fds for child
                if p2cread is not None:
                    os.dup2(p2cread, 0)
                if c2pwrite is not None:
                    os.dup2(c2pwrite, 1)
                if errwrite is not None:
                    os.dup2(errwrite, 2)

                # Close pipe fds.  Make sure we don't close the same
                # fd more than once, or standard fds.
                if p2cread is not None and p2cread not in (0,):
                    os.close(p2cread)
                if c2pwrite is not None and c2pwrite not in (p2cread, 1):
                    os.close(c2pwrite)
                if errwrite is not None and errwrite not in \
                        (p2cread, c2pwrite, 2):
                    os.close(errwrite)

                if cwd is not None:
                    os.chdir(cwd)

                if preexec_fn:
                    preexec_fn()

                if env is None:
                    os.execvp(executable, args)
                else:
                    os.execvpe(executable, args, env)
            except:
                # Child execution failure
                os._exit(255)

        # Parent
        if gc_was_enabled:
            gc.enable()

        if p2cread is not None and p2cwrite is not None:
            os.close(p2cread)
        if c2pwrite is not None and c2pread is not None:
            os.close(c2pwrite)
        if errwrite is not None and errread is not None:
            os.close(errwrite)


    def _handle_exitstatus(self, sts):
        if os.WIFSIGNALED(sts):
            self.returncode = -os.WTERMSIG(sts)
        elif os.WIFEXITED(sts):
            self.returncode = os.WEXITSTATUS(sts)
        else:
            # Should never happen
            raise RuntimeError("Unknown child exit status!")


    def _internal_poll(self, _deadstate=None):
        """Check if child process has terminated.  Returns returncode
        attribute."""
        if self.returncode is None:
            try:
                pid, sts = os.waitpid(self.pid, os.WNOHANG)
                if pid == self.pid:
                    self._handle_exitstatus(sts)
            except os.error:
                if _deadstate is not None:
                    self.returncode = _deadstate
        return self.returncode


    def wait(self):
        """Wait for child process to terminate.  Returns returncode
        attribute."""
        if self.returncode is None:
            pid, sts = os.waitpid(self.pid, 0)
            self._handle_exitstatus(sts)
        return self.returncode


    def _communicate(self, input):
        read_set = []
        write_set = []
        stdout = None # Return
        stderr = None # Return

        if self.stdin:
            # Flush stdio buffer.  This might block, if the user has
            # been writing to .stdin in an uncontrolled fashion.
            self.stdin.flush()
            if input:
                write_set.append(self.stdin)
            else:
                self.stdin.close()
        if self.stdout:
            read_set.append(self.stdout)
            stdout = []
        if self.stderr:
            read_set.append(self.stderr)
            stderr = []

        input_offset = 0
        while read_set or write_set:
            try:
                rlist, wlist, xlist = select.select(read_set, write_set, [])
            except select.error, ex:
                if ex.args[0] == errno.EINTR:
                    continue
                raise

            if self.stdin in wlist:
                # When select has indicated that the file is writable,
                # we can write up to PIPE_BUF bytes without risk
                # blocking.  POSIX defines PIPE_BUF >= 512
                chunk = input[input_offset : input_offset + 512]
                bytes_written = os.write(self.stdin.fileno(), chunk)
                input_offset += bytes_written
                if input_offset >= len(input):
                    self.stdin.close()
                    write_set.remove(self.stdin)

            if self.stdout in rlist:
                data = os.read(self.stdout.fileno(), 1024)
                if data == "":
                    self.stdout.close()
                    read_set.remove(self.stdout)
                stdout.append(data)

            if self.stderr in rlist:
                data = os.read(self.stderr.fileno(), 1024)
                if data == "":
                    self.stderr.close()
                    read_set.remove(self.stderr)
                stderr.append(data)

        # All data exchanged.  Translate lists into strings.
        if stdout is not None:
            stdout = ''.join(stdout)
        if stderr is not None:
            stderr = ''.join(stderr)

        # Translate newlines, if requested.  We cannot let the file
        # object do the translation: It is based on stdio, which is
        # impossible to combine with select (unless forcing no
        # buffering).
        if self.universal_newlines and hasattr(file, 'newlines'):
            if stdout:
                stdout = self._translate_newlines(stdout)
            if stderr:
                stderr = self._translate_newlines(stderr)

        self.wait()
        return (stdout, stderr)

    def send_signal(self, sig):
        """Send a signal to the process
        """
        os.kill(self.pid, sig)

    def terminate(self):
        """Terminate the process with SIGTERM
        """
        self.send_signal(signal.SIGTERM)

    def kill(self):
        """Kill the process with SIGKILL
        """
        self.send_signal(signal.SIGKILL)


########NEW FILE########
__FILENAME__ = Pdsh
#
# Copyright CEA/DAM/DIF (2007, 2008, 2009, 2010, 2011)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
WorkerPdsh

ClusterShell worker for executing commands with LLNL pdsh.
"""

import errno
import os
import sys

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Worker.EngineClient import EngineClient
from ClusterShell.Worker.EngineClient import EngineClientError
from ClusterShell.Worker.EngineClient import EngineClientNotSupportedError
from ClusterShell.Worker.Worker import DistantWorker
from ClusterShell.Worker.Worker import WorkerError


class WorkerPdsh(EngineClient, DistantWorker):
    """
    ClusterShell pdsh-based worker Class.

    Remote Shell (pdsh) usage example:
       >>> worker = WorkerPdsh(nodeset, handler=MyEventHandler(),
       ...                     timeout=30, command="/bin/hostname")
       >>> task.schedule(worker)      # schedule worker for execution
       >>> task.resume()              # run

    Remote Copy (pdcp) usage example: 
       >>> worker = WorkerPdsh(nodeset, handler=MyEventHandler(),
       ...                     timeout=30, source="/etc/my.conf",
       ...                     dest="/etc/my.conf")
       >>> task.schedule(worker)      # schedule worker for execution
       >>> task.resume()              # run

    Known limitations:
      - write() is not supported by WorkerPdsh
      - return codes == 0 are not garanteed when a timeout is used (rc > 0
        are fine)
    """

    def __init__(self, nodes, handler, timeout, **kwargs):
        """
        Initialize Pdsh worker instance.
        """
        DistantWorker.__init__(self, handler)

        self.nodes = NodeSet(nodes)
        self.closed_nodes = NodeSet()

        self.command = kwargs.get('command')
        self.source = kwargs.get('source')
        self.dest = kwargs.get('dest')

        autoclose = kwargs.get('autoclose', False)
        stderr = kwargs.get('stderr', False)

        EngineClient.__init__(self, self, stderr, timeout, autoclose)

        if self.command is not None:
            # PDSH
            self.source = None
            self.dest = None
            self.mode = 'pdsh'
        elif self.source:
            # PDCP
            self.command = None
            self.mode = 'pdcp'
            # Preserve modification times and modes?
            self.preserve = kwargs.get('preserve', False)
            # Reverse copy (rpdcp)?
            self.reverse = kwargs.get('reverse', False)
            if self.reverse:
                self.isdir = os.path.isdir(self.dest)
                if not self.isdir:
                    raise ValueError("reverse copy dest must be a directory")
            else:
                self.isdir = os.path.isdir(self.source)
        else:
            raise ValueError("missing command or source parameter in " \
			     "WorkerPdsh constructor")

        self.popen = None
        self._buf = ""

    def _engine_clients(self):
        return [self]

    def _start(self):
        """
        Start worker, initialize buffers, prepare command.
        """
        # Initialize worker read buffer
        self._buf = ""

        pdsh_env = {}

        if self.command is not None:
            # Build pdsh command
            executable = self.task.info("pdsh_path") or "pdsh"
            cmd_l = [ executable, "-b" ]

            fanout = self.task.info("fanout", 0)
            if fanout > 0:
                cmd_l.append("-f %d" % fanout)

            # Pdsh flag '-t' do not really works well. Better to use
            # PDSH_SSH_ARGS_APPEND variable to transmit ssh ConnectTimeout
            # flag.
            connect_timeout = self.task.info("connect_timeout", 0)
            if connect_timeout > 0:
                pdsh_env['PDSH_SSH_ARGS_APPEND'] = "-o ConnectTimeout=%d" % \
                        connect_timeout

            command_timeout = self.task.info("command_timeout", 0)
            if command_timeout > 0:
                cmd_l.append("-u %d" % command_timeout)

            cmd_l.append("-w %s" % self.nodes)
            cmd_l.append("%s" % self.command)

            if self.task.info("debug", False):
                self.task.info("print_debug")(self.task, "PDSH: %s" % \
                                                            ' '.join(cmd_l))
        else:
            # Build pdcp command
            if self.reverse:
                executable  = self.task.info('rpdcp_path') or "rpdcp"
            else:
                executable = self.task.info("pdcp_path") or "pdcp"
            cmd_l = [ executable, "-b" ]

            fanout = self.task.info("fanout", 0)
            if fanout > 0:
                cmd_l.append("-f %d" % fanout)

            connect_timeout = self.task.info("connect_timeout", 0)
            if connect_timeout > 0:
                cmd_l.append("-t %d" % connect_timeout)

            cmd_l.append("-w %s" % self.nodes)

            if self.isdir:
                cmd_l.append("-r")

            if self.preserve:
                cmd_l.append("-p")

            cmd_l.append(self.source)
            cmd_l.append(self.dest)

            if self.task.info("debug", False):
                self.task.info("print_debug")(self.task,"PDCP: %s" % \
                                                            ' '.join(cmd_l))

        self.popen = self._exec_nonblock(cmd_l, env=pdsh_env)
        self._on_start()

        return self

    def write(self, buf):
        """
        Write data to process. Not supported with Pdsh worker.
        """
        raise EngineClientNotSupportedError("writing is not " \
                                            "supported by pdsh worker")

    def _close(self, abort, flush, timeout):
        """
        Close client. See EngineClient._close().
        """
        if abort:
            prc = self.popen.poll()
            if prc is None:
                # process is still running, kill it
                self.popen.kill()
        prc = self.popen.wait()
        if prc >= 0:
            rc = prc
            if rc != 0:
                raise WorkerError("Cannot run pdsh (error %d)" % rc)
        if abort and timeout:
            if self.eh:
                self.eh.ev_timeout(self)

        os.close(self.fd_reader)
        self.fd_reader = None
        if self.fd_error:
            os.close(self.fd_error)
            self.fd_error = None
        if self.fd_writer:
            os.close(self.fd_writer)
            self.fd_writer = None

        if timeout:
            assert abort, "abort flag not set on timeout"
            for node in (self.nodes - self.closed_nodes):
                self._on_node_timeout(node)
        else:
            for node in (self.nodes - self.closed_nodes):
                self._on_node_rc(node, 0)

        if self.eh:
            self.eh.ev_close(self)

    def _parse_line(self, line, stderr):
        """
        Parse Pdsh line syntax.
        """
        if line.startswith("pdsh@") or \
           line.startswith("pdcp@") or \
           line.startswith("sending "):
            try:
                # pdsh@cors113: cors115: ssh exited with exit code 1
                #       0          1      2     3     4    5    6  7
                # corsUNKN: ssh: corsUNKN: Name or service not known
                #     0      1       2       3  4     5     6    7
                # pdsh@fortoy0: fortoy101: command timeout
                #     0             1         2       3
                # sending SIGTERM to ssh fortoy112 pid 32014
                #     0      1     2  3      4      5    6
                # pdcp@cors113: corsUNKN: ssh exited with exit code 255
                #     0             1      2    3     4    5    6    7
                # pdcp@cors113: cors115: fatal: /var/cache/shine/...
                #     0             1      2                   3...

                words  = line.split()
                # Set return code for nodename of worker
                if self.mode == 'pdsh':
                    if len(words) == 4 and words[2] == "command" and \
                       words[3] == "timeout":
                        pass
                    elif len(words) == 8 and words[3] == "exited" and \
                         words[7].isdigit():
                        self._on_node_rc(words[1][:-1], int(words[7]))
                elif self.mode == 'pdcp':
                    self._on_node_rc(words[1][:-1], errno.ENOENT)

            except Exception, exc:
                print >> sys.stderr, exc
                raise EngineClientError()
        else:
            # split pdsh reply "nodename: msg"
            nodename, msg = line.split(': ', 1)
            if stderr:
                self._on_node_errline(nodename, msg)
            else:
                self._on_node_msgline(nodename, msg)

    def _handle_read(self):
        """
        Engine is telling us a read is available.
        """
        debug = self.task.info("debug", False)
        if debug:
            print_debug = self.task.info("print_debug")

        for msg in self._readlines():
            if debug:
                print_debug(self.task, "PDSH: %s" % msg)
            self._parse_line(msg, False)

    def _handle_error(self):
        """
        Engine is telling us an error read is available.
        """
        debug = self.worker.task.info("debug", False)
        if debug:
            print_debug = self.worker.task.info("print_debug")

        for msg in self._readerrlines():
            if debug:
                print_debug(self.task, "PDSH@STDERR: %s" % msg)
            self._parse_line(msg, True)

    def _on_node_rc(self, node, rc):
        """
        Return code received from a node, update last* stuffs.
        """
        DistantWorker._on_node_rc(self, node, rc)
        self.closed_nodes.add(node)


########NEW FILE########
__FILENAME__ = Popen
#
# Copyright CEA/DAM/DIF (2008, 2009, 2010, 2011)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
WorkerPopen

ClusterShell worker for executing local commands.

Usage example:
   >>> worker = WorkerPopen("/bin/uname", key="mykernel") 
   >>> task.schedule(worker)    # schedule worker
   >>> task.resume()            # run task
   >>> worker.retcode()         # get return code
   0
   >>> worker.read()            # read command output
   'Linux'

"""

import os

from ClusterShell.Worker.Worker import WorkerSimple


class WorkerPopen(WorkerSimple):
    """
    Implements the Popen Worker.
    """

    def __init__(self, command, key=None, handler=None,
        stderr=False, timeout=-1, autoclose=False):
        """
        Initialize Popen worker.
        """
        WorkerSimple.__init__(self, None, None, None, key, handler,
            stderr, timeout, autoclose)

        self.command = command
        if not self.command:
            raise ValueError("missing command parameter in WorkerPopen " \
			     "constructor")

        self.popen = None
        self.rc = None

    def _start(self):
        """
        Start worker.
        """
        assert self.popen is None

        self.popen = self._exec_nonblock(self.command, shell=True)

        if self.task.info("debug", False):
            self.task.info("print_debug")(self.task, "POPEN: %s" % self.command)

        if self.eh:
            self.eh.ev_start(self)

        return self

    def _close(self, abort, flush, timeout):
        """
        Close client. See EngineClient._close().
        """
        if flush and self._rbuf:
            # We still have some read data available in buffer, but no
            # EOL. Generate a final message before closing.
            self.worker._on_msgline(self._rbuf)

        rc = -1
        if abort:
            # check if process has terminated
            prc = self.popen.poll()
            if prc is None:
                # process is still running, kill it
                self.popen.kill()
        # release process
        prc = self.popen.wait()
        # get exit status
        if prc >= 0:
            # process exited normally
            rc = prc
        elif not abort:
            # if process was signaled, return 128 + signum (bash-like)
            rc = 128 + -prc

        os.close(self.fd_reader)
        self.fd_reader = None
        if self.fd_error:
            os.close(self.fd_error)
            self.fd_error = None
        if self.fd_writer:
            os.close(self.fd_writer)
            self.fd_writer = None

        if rc >= 0: # filter valid rc
            self._on_rc(rc)
        elif timeout:
            assert abort, "abort flag not set on timeout"
            self._on_timeout()

        if self.eh:
            self.eh.ev_close(self)

    def _on_rc(self, rc):
        """
        Set return code.
        """
        self.rc = rc        # 1.4- compat
        WorkerSimple._on_rc(self, rc)

    def retcode(self):
        """
        Return return code or None if command is still in progress.
        """
        return self.rc
   

########NEW FILE########
__FILENAME__ = Rsh
#
# Copyright CEA/DAM/DIF (2013)
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
ClusterShell RSH support

It could also handles rsh forks, like krsh or mrsh.
This is also the base class for rsh evolutions, like Ssh worker.
"""

import copy
import os

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Worker.EngineClient import EngineClient
from ClusterShell.Worker.Worker import DistantWorker


class Rsh(EngineClient):
    """
    Rsh EngineClient.
    """

    def __init__(self, node, command, worker, stderr, timeout, autoclose=False):
        """
        Initialize Rsh EngineClient instance.
        """
        EngineClient.__init__(self, worker, stderr, timeout, autoclose)

        self.key = copy.copy(node)
        self.command = command
        self.popen = None

    def _build_cmd(self):
        """
        Build the shell command line to start the rsh commmand.
        Return an array of command and arguments.
        """
        # Does not support 'connect_timeout'
        task = self.worker.task
        path = task.info("rsh_path") or "rsh"
        user = task.info("rsh_user")
        options = task.info("rsh_options")

        cmd_l = [ path ]

        if user:
            cmd_l.append("-l")
            cmd_l.append(user)

        # Add custom options
        if options:
            cmd_l += options.split()

        cmd_l.append("%s" % self.key)  # key is the node
        cmd_l.append("%s" % self.command)

        return cmd_l

    def _start(self):
        """
        Start worker, initialize buffers, prepare command.
        """

        # Build command
        cmd_l = self._build_cmd()

        task = self.worker.task
        if task.info("debug", False):
            name = str(self.__class__).upper().split('.')[-1]
            task.info("print_debug")(task, "%s: %s" % (name, ' '.join(cmd_l)))

        self.popen = self._exec_nonblock(cmd_l)
        self.worker._on_start()
        return self

    def _close(self, abort, flush, timeout):
        """
        Close client. See EngineClient._close().
        """
        if flush and self._rbuf:
            # We still have some read data available in buffer, but no
            # EOL. Generate a final message before closing.
            self.worker._on_node_msgline(self.key, self._rbuf)

        rc = -1
        if abort:
            prc = self.popen.poll()
            if prc is None:
                # process is still running, kill it
                self.popen.kill()
        prc = self.popen.wait()
        if prc >= 0:
            rc = prc

        os.close(self.fd_reader)
        self.fd_reader = None
        if self.fd_error:
            os.close(self.fd_error)
            self.fd_error = None
        if self.fd_writer:
            os.close(self.fd_writer)
            self.fd_writer = None

        if rc >= 0:
            self.worker._on_node_rc(self.key, rc)
        elif timeout:
            assert abort, "abort flag not set on timeout"
            self.worker._on_node_timeout(self.key)

        self.worker._check_fini()

    def _handle_read(self):
        """
        Handle a read notification. Called by the engine as the result of an
        event indicating that a read is available.
        """
        # Local variables optimization
        worker = self.worker
        task = worker.task
        key = self.key
        node_msgline = worker._on_node_msgline
        debug = task.info("debug", False)
        if debug:
            print_debug = task.info("print_debug")
        for msg in self._readlines():
            if debug:
                print_debug(task, "%s: %s" % (key, msg))
            node_msgline(key, msg)  # handle full msg line

    def _handle_error(self):
        """
        Handle a read error (stderr) notification.
        """
        # Local variables optimization
        worker = self.worker
        task = worker.task
        key = self.key
        node_errline = worker._on_node_errline
        debug = task.info("debug", False)
        if debug:
            print_debug = task.info("print_debug")
        for msg in self._readerrlines():
            if debug:
                print_debug(task, "%s@STDERR: %s" % (key, msg))
            node_errline(key, msg)  # handle full stderr line



class Rcp(Rsh):
    """
    Rcp EngineClient.
    """

    def __init__(self, node, source, dest, worker, stderr, timeout, preserve,
        reverse):
        """
        Initialize Rcp instance.
        """
        Rsh.__init__(self, node, None, worker, stderr, timeout)
        self.source = source
        self.dest = dest
        self.popen = None

        # Preserve modification times and modes?
        self.preserve = preserve

        # Reverse copy?
        self.reverse = reverse

        # Directory?
        if self.reverse:
            self.isdir = os.path.isdir(self.dest)
            if not self.isdir:
                raise ValueError("reverse copy dest must be a directory")
        else:
            self.isdir = os.path.isdir(self.source)

        # FIXME: file sanity checks could be moved to Rcp._start() as we
        # should now be able to handle error when starting (#215).

    def _build_cmd(self):
        """
        Build the shell command line to start the rcp commmand.
        Return an array of command and arguments.
        """

        # Does not support 'connect_timeout'
        task = self.worker.task
        path = task.info("rcp_path") or "rcp"
        user = task.info("rsh_user")
        options = [ task.info("rsh_options"), task.info("rcp_options") ]

        cmd_l = [ path ]

        if self.isdir:
            cmd_l.append("-r")

        if self.preserve:
            cmd_l.append("-p")


        # Add custom rcp options
        for opts in options:
            if opts:
                cmd_l += opts.split()

        if self.reverse:
            if user:
                cmd_l.append("%s@%s:%s" % (user, self.key, self.source))
            else:
                cmd_l.append("%s:%s" % (self.key, self.source))

            cmd_l.append(os.path.join(self.dest, "%s.%s" % \
                         (os.path.basename(self.source), self.key)))
        else:
            cmd_l.append(self.source)
            if user:
                cmd_l.append("%s@%s:%s" % (user, self.key, self.dest))
            else:
                cmd_l.append("%s:%s" % (self.key, self.dest))

        return cmd_l


class WorkerRsh(DistantWorker):
    """
    ClusterShell rsh-based worker Class.

    Remote Shell (rsh) usage example:
       >>> worker = WorkerRsh(nodeset, handler=MyEventHandler(),
       ...                    timeout=30, command="/bin/hostname")
       >>> task.schedule(worker)      # schedule worker for execution
       >>> task.resume()              # run

    Remote Copy (rcp) usage example:
       >>> worker = WorkerRsh(nodeset, handler=MyEventHandler(),
       ...                     source="/etc/my.conf",
       ...                     dest="/etc/my.conf")
       >>> task.schedule(worker)      # schedule worker for execution
       >>> task.resume()              # run

    connect_timeout option is ignored by this worker.
    """

    SHELL_CLASS = Rsh
    COPY_CLASS = Rcp

    def __init__(self, nodes, handler, timeout, **kwargs):
        """
        Initialize Rsh worker instance.
        """
        DistantWorker.__init__(self, handler)

        self.clients = []
        self.nodes = NodeSet(nodes)
        self.command = kwargs.get('command')
        self.source = kwargs.get('source')
        self.dest = kwargs.get('dest')
        autoclose = kwargs.get('autoclose', False)
        stderr = kwargs.get('stderr', False)
        self._close_count = 0
        self._has_timeout = False

        # Prepare underlying engine clients (mrsh/mrcp processes)
        if self.command is not None:
            # secure remote shell
            for node in self.nodes:
                rsh = self.__class__.SHELL_CLASS
                self.clients.append(rsh(node, self.command, self, stderr,
                                       timeout, autoclose))
        elif self.source:
            # secure copy
            for node in self.nodes:
                rcp = self.__class__.COPY_CLASS
                self.clients.append(rcp(node, self.source, self.dest,
                    self, stderr, timeout, kwargs.get('preserve', False),
                    kwargs.get('reverse', False)))
        else:
            raise ValueError("missing command or source parameter in " \
			     "WorkerRsh constructor")

    def _engine_clients(self):
        """
        Access underlying engine clients.
        """
        return self.clients

    def _on_node_rc(self, node, rc):
        DistantWorker._on_node_rc(self, node, rc)
        self._close_count += 1

    def _on_node_timeout(self, node):
        DistantWorker._on_node_timeout(self, node)
        self._close_count += 1
        self._has_timeout = True

    def _check_fini(self):
        if self._close_count >= len(self.clients):
            handler = self.eh
            if handler:
                if self._has_timeout:
                    handler.ev_timeout(self)
                handler.ev_close(self)

    def write(self, buf):
        """
        Write to worker clients.
        """
        for client in self.clients:
            client._write(buf)

    def set_write_eof(self):
        """
        Tell worker to close its writer file descriptor once flushed. Do not
        perform writes after this call.
        """
        for client in self.clients:
            client._set_write_eof()

    def abort(self):
        """
        Abort processing any action by this worker.
        """
        for client in self.clients:
            client.abort()

########NEW FILE########
__FILENAME__ = Ssh
#
# Copyright CEA/DAM/DIF (2008, 2009, 2010, 2011)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
ClusterShell Ssh/Scp support

This module implements OpenSSH engine client and task's worker.
"""

import os

from ClusterShell.Worker.Rsh import Rsh, Rcp, WorkerRsh


class Ssh(Rsh):
    """
    Ssh EngineClient.
    """

    def _build_cmd(self):
        """
        Build the shell command line to start the ssh commmand.
        Return an array of command and arguments.
        """

        task = self.worker.task
        path = task.info("ssh_path") or "ssh"
        user = task.info("ssh_user")
        options = task.info("ssh_options")

        # Build ssh command
        cmd_l = [ path, "-a", "-x"  ]

        if user:
            cmd_l.append("-l")
            cmd_l.append(user)

        connect_timeout = task.info("connect_timeout", 0)
        if connect_timeout > 0:
            cmd_l.append("-oConnectTimeout=%d" % connect_timeout)

        # Disable passphrase/password querying
        cmd_l.append("-oBatchMode=yes")

        # Add custom ssh options
        if options:
            cmd_l += options.split()

        cmd_l.append("%s" % self.key)
        cmd_l.append("%s" % self.command)

        return cmd_l

class Scp(Rcp):
    """
    Scp EngineClient.
    """

    def _build_cmd(self):
        """
        Build the shell command line to start the scp commmand.
        Return an array of command and arguments.
        """

        task = self.worker.task
        path = task.info("scp_path") or "scp"
        user = task.info("scp_user") or task.info("ssh_user")
        options = [ task.info("ssh_options"), task.info("scp_options") ]

        # Build scp command
        cmd_l = [ path ]

        if self.isdir:
            cmd_l.append("-r")

        if self.preserve:
            cmd_l.append("-p")

        connect_timeout = task.info("connect_timeout", 0)
        if connect_timeout > 0:
            cmd_l.append("-oConnectTimeout=%d" % connect_timeout)

        # Disable passphrase/password querying
        cmd_l.append("-oBatchMode=yes")

        # Add custom scp options
        for opts in options:
            if opts:
                cmd_l += opts.split()

        if self.reverse:
            if user:
                cmd_l.append("%s@%s:%s" % (user, self.key, self.source))
            else:
                cmd_l.append("%s:%s" % (self.key, self.source))

            cmd_l.append(os.path.join(self.dest, "%s.%s" % \
                         (os.path.basename(self.source), self.key)))
        else:
            cmd_l.append(self.source)
            if user:
                cmd_l.append("%s@%s:%s" % (user, self.key, self.dest))
            else:
                cmd_l.append("%s:%s" % (self.key, self.dest))

        return cmd_l

class WorkerSsh(WorkerRsh):
    """
    ClusterShell ssh-based worker Class.

    Remote Shell (ssh) usage example:
       >>> worker = WorkerSsh(nodeset, handler=MyEventHandler(),
       ...                    timeout=30, command="/bin/hostname")
       >>> task.schedule(worker)      # schedule worker for execution
       >>> task.resume()              # run

    Remote Copy (scp) usage example: 
       >>> worker = WorkerSsh(nodeset, handler=MyEventHandler(),
       ...                    timeout=30, source="/etc/my.conf",
       ...                    dest="/etc/my.conf")
       >>> task.schedule(worker)      # schedule worker for execution
       >>> task.resume()              # run
    """

    SHELL_CLASS = Ssh
    COPY_CLASS = Scp

########NEW FILE########
__FILENAME__ = Tree
#
# Copyright CEA/DAM/DIF (2011, 2012)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
ClusterShell v2 tree propagation worker
"""

import logging
import os

from ClusterShell.Event import EventHandler
from ClusterShell.NodeSet import NodeSet
from ClusterShell.Worker.Worker import DistantWorker

from ClusterShell.Propagation import PropagationTreeRouter


class MetaWorkerEventHandler(EventHandler):
    """
    """
    def __init__(self, metaworker):
        self.metaworker = metaworker

    def ev_start(self, worker):
        """
        Called to indicate that a worker has just started.
        """
        self.metaworker._start_count += 1
        self.metaworker._check_ini()

    def ev_read(self, worker):
        """
        Called to indicate that a worker has data to read.
        """
        self.metaworker._on_node_msgline(worker.current_node,
                                         worker.current_msg)

    def ev_error(self, worker):
        """
        Called to indicate that a worker has error to read (on stderr).
        """
        self.metaworker._on_node_errline(worker.current_node,
                                         worker.current_errmsg)

    def ev_written(self, worker):
        """
        Called to indicate that writing has been done.
        """
        metaworker = self.metaworker
        metaworker.current_node = worker.current_node
        metaworker.eh.ev_written(metaworker)

    def ev_hup(self, worker):
        """
        Called to indicate that a worker's connection has been closed.
        """
        #print >>sys.stderr, "ev_hup?"
        self.metaworker._on_node_rc(worker.current_node, worker.current_rc)

    def ev_timeout(self, worker):
        """
        Called to indicate that a worker has timed out (worker timeout only).
        """
        # WARNING!!! this is not possible as metaworking is changing task's
        # shared timeout set!
        #for node in worker.iter_keys_timeout():
        #    self.metaworker._on_node_timeout(node)
        # we use NodeSet to copy set
        for node in NodeSet._fromlist1(worker.iter_keys_timeout()):
            self.metaworker._on_node_timeout(node)

    def ev_close(self, worker):
        """
        Called to indicate that a worker has just finished (it may already
        have failed on timeout).
        """
        #self.metaworker._check_fini()
        pass
        ##print >>sys.stderr, "ev_close?"
        #self._completed += 1
        #if self._completed >= self.grpcount:
        #    #print >>sys.stderr, "ev_close!"
        #    metaworker = self.metaworker
        #    metaworker.eh.ev_close(metaworker)


class WorkerTree(DistantWorker):
    """
    ClusterShell tree worker Class.

    """

    def __init__(self, nodes, handler, timeout, **kwargs):
        """
        Initialize Tree worker instance.

        @param nodes: Targeted nodeset.
        @param handler: Worker EventHandler.
        @param timeout: Timeout value for worker.
        @param command: Command to execute.
        @param topology: Force specific TopologyTree.
        @param newroot: Root node of TopologyTree.
        """
        DistantWorker.__init__(self, handler)

        self.workers = []
        self.nodes = NodeSet(nodes)
        self.timeout = timeout
        self.command = kwargs.get('command')
        self.source = kwargs.get('source')
        self.dest = kwargs.get('dest')
        autoclose = kwargs.get('autoclose', False)
        self.stderr = kwargs.get('stderr', False)
        self._close_count = 0
        self._start_count = 0
        self._child_count = 0
        self._target_count = 0
        self._has_timeout = False
        self.logger = logging.getLogger(__name__)

        if self.command is not None:
            pass
        elif self.source:
            raise NotImplementedError
        else:
            raise ValueError("missing command or source parameter in " \
			     "WorkerTree constructor")

        # build gateway invocation command
        invoke_gw_args = []
        for envname in ('PYTHONPATH', \
                        'CLUSTERSHELL_GW_LOG_DIR', \
                        'CLUSTERSHELL_GW_LOG_LEVEL'):
            envval = os.getenv(envname)
            if envval:
                invoke_gw_args.append("%s=%s" % (envname, envval))
        invoke_gw_args.append("python -m ClusterShell/Gateway -Bu")
        self.invoke_gateway = ' '.join(invoke_gw_args)

        self.topology = kwargs.get('topology')
        if self.topology is not None:
            self.newroot = kwargs.get('newroot') or str(self.topology.root.nodeset)
            self.router = PropagationTreeRouter(self.newroot, self.topology)
        else:
            self.router = None

        self.upchannel = None
        self.metahandler = MetaWorkerEventHandler(self)

    def _set_task(self, task):
        """
        Bind worker to task. Called by task.schedule().
        WorkerTree metaworker: override to schedule sub-workers.
        """
        ##if fanout is None:
        ##    fanout = self.router.fanout
        ##self.task.set_info('fanout', fanout)

        DistantWorker._set_task(self, task)
        # Now bound to task - initalize router
        self.topology = self.topology or task.topology
        self.router = self.router or task._default_router()
        # And launch stuffs
        next_hops = self._distribute(self.task.info("fanout"), self.nodes)
        for gw, targets in next_hops.iteritems():
            if gw == targets:
                self.logger.debug('task.shell cmd=%s nodes=%s timeout=%d' % \
                    (self.command, self.nodes, self.timeout))
                self._child_count += 1
                self._target_count += len(targets)
                self.workers.append(self.task.shell(self.command,
                    nodes=targets, timeout=self.timeout,
                    handler=self.metahandler, stderr=self.stderr, tree=False))
            else:
                self._execute_remote(self.command, targets, gw, self.timeout)

    def _distribute(self, fanout, dst_nodeset):
        """distribute target nodes between next hop gateways"""
        distribution = {}
        self.router.fanout = fanout

        for gw, dstset in self.router.dispatch(dst_nodeset):
            if gw in distribution:
                distribution[gw].add(dstset)
            else:
                distribution[gw] = dstset
        return distribution

    def _execute_remote(self, cmd, targets, gateway, timeout):
        """run command against a remote node via a gateway"""
        self.logger.debug("_execute_remote gateway=%s cmd=%s targets=%s" % \
            (gateway, cmd, targets))
        #self._start_count += 1
        #self._child_count += 1
        self._target_count += len(targets)
        self.task.pchannel(gateway, self).shell(nodes=targets,
            command=cmd, worker=self, timeout=timeout, stderr=self.stderr,
            gw_invoke_cmd=self.invoke_gateway)

    def _engine_clients(self):
        """
        Access underlying engine clients.
        """
        return []

    def _on_node_rc(self, node, rc):
        DistantWorker._on_node_rc(self, node, rc)
        self._close_count += 1
        self._check_fini()

    def _on_node_timeout(self, node):
        DistantWorker._on_node_timeout(self, node)
        self._close_count += 1
        self._has_timeout = True
        self._check_fini()

    def _check_ini(self):
        self.logger.debug("WorkerTree: _check_ini (%d, %d)" % \
            (self._start_count,self._child_count))
        if self._start_count >= self._child_count:
            self.eh.ev_start(self)

    def _check_fini(self):
        if self._close_count >= self._target_count:
            handler = self.eh
            if handler:
                if self._has_timeout:
                    handler.ev_timeout(self)
                handler.ev_close(self)
            self.task._pchannel_release(self)

    def write(self, buf):
        """
        Write to worker clients.
        """
        for c in self._engine_clients():
            c._write(buf)

    def set_write_eof(self):
        """
        Tell worker to close its writer file descriptor once flushed. Do not
        perform writes after this call.
        """
        for c in self._engine_clients():
            c._set_write_eof()

    def abort(self):
        """
        Abort processing any action by this worker.
        """
        for c in self._engine_clients():
            c.abort()


########NEW FILE########
__FILENAME__ = Worker
#
# Copyright CEA/DAM/DIF (2007, 2008, 2009, 2010, 2011)
#  Contributor: Stephane THIELL <stephane.thiell@cea.fr>
#
# This file is part of the ClusterShell library.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

"""
ClusterShell worker interface.

A worker is a generic object which provides "grouped" work in a specific task.
"""

from ClusterShell.Worker.EngineClient import EngineClient
from ClusterShell.NodeSet import NodeSet

import os


class WorkerException(Exception):
    """Generic worker exception."""

class WorkerError(WorkerException):
    """Generic worker error."""

# DEPRECATED: WorkerBadArgumentError exception is deprecated as of 1.4,
# use ValueError instead.
WorkerBadArgumentError = ValueError

class Worker(object):
    """
    Worker is an essential base class for the ClusterShell library. The goal
    of a worker object is to execute a common work on a single or several
    targets (abstract notion) in parallel. Concret targets and also the notion
    of local or distant targets are managed by Worker's subclasses (for
    example, see the DistantWorker base class).

    A configured Worker object is associated to a specific ClusterShell Task,
    which can be seen as a single-threaded Worker supervisor. Indeed, the work
    to be done is executed in parallel depending on other Workers and Task's
    current paramaters, like current fanout value.

    ClusterShell is designed to write event-driven applications, and the Worker
    class is key here as Worker objects are passed as parameter of most event
    handlers (see the ClusterShell.Event.EventHandler class).

    The following public object variables are defined on some events, so you
    may find them useful in event handlers:
        - worker.current_node [ev_read,ev_error,ev_hup]
            node/key concerned by event
        - worker.current_msg [ev_read]
            message just read (from stdout)
        - worker.current_errmsg [ev_error]
            error message just read (from stderr)
        - worker.current_rc [ev_hup]
            return code just received

    Example of use:
        >>> from ClusterShell.Event import EventHandler
        >>> class MyOutputHandler(EventHandler):
        ...     def ev_read(self, worker):
        ...             node = worker.current_node       
        ...             line = worker.current_msg
        ...             print "%s: %s" % (node, line)
        ... 
    """
    def __init__(self, handler):
        """
        Initializer. Should be called from derived classes.
        """
        # Associated EventHandler object
        self.eh = handler
        # Parent task (once bound)
        self.task = None
        self.started = False
        self.metaworker = None
        self.metarefcnt = 0
        # current_x public variables (updated at each event accordingly)
        self.current_node = None
        self.current_msg = None
        self.current_errmsg = None
        self.current_rc = 0

    def _set_task(self, task):
        """
        Bind worker to task. Called by task.schedule()
        """
        if self.task is not None:
            # one-shot-only schedule supported for now
            raise WorkerError("worker has already been scheduled")
        self.task = task

    def _task_bound_check(self):
        if not self.task:
            raise WorkerError("worker is not task bound")

    def _engine_clients(self):
        """
        Return a list of underlying engine clients.
        """
        raise NotImplementedError("Derived classes must implement.")

    def _on_start(self):
        """
        Starting worker.
        """
        if not self.started:
            self.started = True
            if self.eh:
                self.eh.ev_start(self)

    # Base getters

    def last_read(self):
        """
        Get last read message from event handler.
        [DEPRECATED] use current_msg
        """
        raise NotImplementedError("Derived classes must implement.")

    def last_error(self):
        """
        Get last error message from event handler.
        [DEPRECATED] use current_errmsg
        """
        raise NotImplementedError("Derived classes must implement.")

    def did_timeout(self):
        """
        Return whether this worker has aborted due to timeout.
        """
        self._task_bound_check()
        return self.task._num_timeout_by_worker(self) > 0

    # Base actions

    def abort(self):
        """
        Abort processing any action by this worker.
        """
        raise NotImplementedError("Derived classes must implement.")

    def flush_buffers(self):
        """
        Flush any messages associated to this worker.
        """
        self._task_bound_check()
        self.task._flush_buffers_by_worker(self)

    def flush_errors(self):
        """
        Flush any error messages associated to this worker.
        """
        self._task_bound_check()
        self.task._flush_errors_by_worker(self)

class DistantWorker(Worker):
    """
    Base class DistantWorker, which provides a useful set of setters/getters
    to use with distant workers like ssh or pdsh.
    """

    def _on_node_msgline(self, node, msg):
        """
        Message received from node, update last* stuffs.
        """
        # Maxoptimize this method as it might be called very often.
        task = self.task
        handler = self.eh

        self.current_node = node
        self.current_msg = msg

        if task._msgtree is not None:   # don't waste time
            task._msg_add((self, node), msg)

        if handler is not None:
            handler.ev_read(self)

    def _on_node_errline(self, node, msg):
        """
        Error message received from node, update last* stuffs.
        """
        task = self.task
        handler = self.eh

        self.current_node = node
        self.current_errmsg = msg

        if task._errtree is not None:
            task._errmsg_add((self, node), msg)

        if handler is not None:
            handler.ev_error(self)

    def _on_node_rc(self, node, rc):
        """
        Return code received from a node, update last* stuffs.
        """
        self.current_node = node
        self.current_rc = rc

        self.task._rc_set((self, node), rc)

        if self.eh:
            self.eh.ev_hup(self)

    def _on_node_timeout(self, node):
        """
        Update on node timeout.
        """
        # Update current_node to allow node resolution after ev_timeout.
        self.current_node = node

        self.task._timeout_add((self, node))

    def last_node(self):
        """
        Get last node, useful to get the node in an EventHandler
        callback like ev_read().
        [DEPRECATED] use current_node
        """
        return self.current_node

    def last_read(self):
        """
        Get last (node, buffer), useful in an EventHandler.ev_read()
        [DEPRECATED] use (current_node, current_msg)
        """
        return self.current_node, self.current_msg

    def last_error(self):
        """
        Get last (node, error_buffer), useful in an EventHandler.ev_error()
        [DEPRECATED] use (current_node, current_errmsg)
        """
        return self.current_node, self.current_errmsg

    def last_retcode(self):
        """
        Get last (node, rc), useful in an EventHandler.ev_hup()
        [DEPRECATED] use (current_node, current_rc)
        """
        return self.current_node, self.current_rc

    def node_buffer(self, node):
        """
        Get specific node buffer.
        """
        self._task_bound_check()
        return self.task._msg_by_source((self, node))
        
    def node_error(self, node):
        """
        Get specific node error buffer.
        """
        self._task_bound_check()
        return self.task._errmsg_by_source((self, node))

    node_error_buffer = node_error

    def node_retcode(self, node):
        """
        Get specific node return code. Raises a KeyError if command on
        node has not yet finished (no return code available), or is
        node is not known by this worker.
        """
        self._task_bound_check()
        try:
            rc = self.task._rc_by_source((self, node))
        except KeyError:
            raise KeyError(node)
        return rc

    node_rc = node_retcode

    def iter_buffers(self, match_keys=None):
        """
        Returns an iterator over available buffers and associated
        NodeSet. If the optional parameter match_keys is defined, only
        keys found in match_keys are returned.
        """
        self._task_bound_check()
        for msg, keys in self.task._call_tree_matcher( \
                            self.task._msgtree.walk, match_keys, self):
            yield msg, NodeSet.fromlist(keys)

    def iter_errors(self, match_keys=None):
        """
        Returns an iterator over available error buffers and associated
        NodeSet. If the optional parameter match_keys is defined, only
        keys found in match_keys are returned.
        """
        self._task_bound_check()
        for msg, keys in self.task._call_tree_matcher( \
                            self.task._errtree.walk, match_keys, self):
            yield msg, NodeSet.fromlist(keys)

    def iter_node_buffers(self, match_keys=None):
        """
        Returns an iterator over each node and associated buffer.
        """
        self._task_bound_check()
        return self.task._call_tree_matcher(self.task._msgtree.items,
                                            match_keys, self)

    def iter_node_errors(self, match_keys=None):
        """
        Returns an iterator over each node and associated error buffer.
        """
        self._task_bound_check()
        return self.task._call_tree_matcher(self.task._errtree.items,
                                            match_keys, self)

    def iter_retcodes(self, match_keys=None):
        """
        Returns an iterator over return codes and associated NodeSet.
        If the optional parameter match_keys is defined, only keys
        found in match_keys are returned.
        """
        self._task_bound_check()
        for rc, keys in self.task._rc_iter_by_worker(self, match_keys):
            yield rc, NodeSet.fromlist(keys)

    def iter_node_retcodes(self):
        """
        Returns an iterator over each node and associated return code.
        """
        self._task_bound_check()
        return self.task._krc_iter_by_worker(self)

    def num_timeout(self):
        """
        Return the number of timed out "keys" (ie. nodes) for this worker.
        """
        self._task_bound_check()
        return self.task._num_timeout_by_worker(self)

    def iter_keys_timeout(self):
        """
        Iterate over timed out keys (ie. nodes) for a specific worker.
        """
        self._task_bound_check()
        return self.task._iter_keys_timeout_by_worker(self)

class WorkerSimple(EngineClient, Worker):
    """
    Implements a simple Worker being itself an EngineClient.
    """

    def __init__(self, file_reader, file_writer, file_error, key, handler,
            stderr=False, timeout=-1, autoclose=False):
        """
        Initialize worker.
        """
        Worker.__init__(self, handler)
        EngineClient.__init__(self, self, stderr, timeout, autoclose)

        if key is None: # allow key=0
            self.key = self
        else:
            self.key = key
        if file_reader:
            self.fd_reader = file_reader.fileno()
        if file_error:
            self.fd_error = file_error.fileno()
        if file_writer:
            self.fd_writer = file_writer.fileno()

    def _engine_clients(self):
        """
        Return a list of underlying engine clients.
        """
        return [self]

    def set_key(self, key):
        """
        Source key for this worker is free for use. Use this method to
        set the custom source key for this worker.
        """
        self.key = key

    def _start(self):
        """
        Called on EngineClient start.
        """
        # call Worker._on_start()
        self._on_start()
        return self

    def _read(self, size=65536):
        """
        Read data from process.
        """
        return EngineClient._read(self, size)

    def _readerr(self, size=65536):
        """
        Read error data from process.
        """
        return EngineClient._readerr(self, size)

    def _close(self, abort, flush, timeout):
        """
        Close client. See EngineClient._close().
        """
        if flush and self._rbuf:
            # We still have some read data available in buffer, but no
            # EOL. Generate a final message before closing.
            self.worker._on_msgline(self._rbuf)

        if self.fd_reader:
            os.close(self.fd_reader)
        if self.fd_error:
            os.close(self.fd_error)
        if self.fd_writer:
            os.close(self.fd_writer)

        if timeout:
            assert abort, "abort flag not set on timeout"
            self._on_timeout()

        if self.eh:
            self.eh.ev_close(self)

    def _handle_read(self):
        """
        Engine is telling us there is data available for reading.
        """
        # Local variables optimization
        task = self.worker.task
        msgline = self._on_msgline

        debug = task.info("debug", False)
        if debug:
            print_debug = task.info("print_debug")
            for msg in self._readlines():
                print_debug(task, "LINE %s" % msg)
                msgline(msg)
        else:
            for msg in self._readlines():
                msgline(msg)

    def _handle_error(self):
        """
        Engine is telling us there is error available for reading.
        """
        task = self.worker.task
        errmsgline = self._on_errmsgline

        debug = task.info("debug", False)
        if debug:
            print_debug = task.info("print_debug")
            for msg in self._readerrlines():
                print_debug(task, "LINE@STDERR %s" % msg)
                errmsgline(msg)
        else:
            for msg in self._readerrlines():
                errmsgline(msg)

    def last_read(self):
        """
        Read last msg, useful in an EventHandler.
        """
        return self.current_msg

    def last_error(self):
        """
        Get last error message from event handler.
        """
        return self.current_errmsg

    def _on_msgline(self, msg):
        """
        Add a message.
        """
        # add last msg to local buffer
        self.current_msg = msg

        # update task
        self.task._msg_add((self, self.key), msg)

        if self.eh:
            self.eh.ev_read(self)

    def _on_errmsgline(self, msg):
        """
        Add a message.
        """
        # add last msg to local buffer
        self.current_errmsg = msg

        # update task
        self.task._errmsg_add((self, self.key), msg)

        if self.eh:
            self.eh.ev_error(self)

    def _on_rc(self, rc):
        """
        Set return code received.
        """
        self.current_rc = rc

        self.task._rc_set((self, self.key), rc)

        if self.eh:
            self.eh.ev_hup(self)

    def _on_timeout(self):
        """
        Update on timeout.
        """
        self.task._timeout_add((self, self.key))

        # trigger timeout event
        if self.eh:
            self.eh.ev_timeout(self)

    def read(self):
        """
        Read worker buffer.
        """
        self._task_bound_check()
        for key, msg in self.task._call_tree_matcher(self.task._msgtree.items,
                                                     worker=self):
            assert key == self.key
            return str(msg)

    def error(self):
        """
        Read worker error buffer.
        """
        self._task_bound_check()
        for key, msg in self.task._call_tree_matcher(self.task._errtree.items,
                                                     worker=self):
            assert key == self.key
            return str(msg)

    def write(self, buf):
        """
        Write to worker.
        """
        self._write(buf)

    def set_write_eof(self):
        """
        Tell worker to close its writer file descriptor once flushed. Do not
        perform writes after this call.
        """
        self._set_write_eof()


########NEW FILE########
__FILENAME__ = clubak
#!/usr/bin/env python

"""
clubak command-line tool
"""

from ClusterShell.CLI.Clubak import main

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = clush
#!/usr/bin/env python

"""
clush command-line tool
"""

from ClusterShell.CLI.Clush import main

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = nodeset
#!/usr/bin/env python

"""
nodeset command-line tool
"""

from ClusterShell.CLI.Nodeset import main

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = CLIClubakTest
#!/usr/bin/env python
# scripts/clubak.py tool test suite
# Written by S. Thiell 2012-03-22


"""Unit test for CLI/Clubak.py"""

import sys
import unittest

from TLib import *
from ClusterShell.CLI.Clubak import main


class CLIClubakTest(unittest.TestCase):
    """Unit test class for testing CLI/Clubak.py"""

    def _clubak_t(self, args, input, expected_stdout, expected_rc=0,
                  expected_stderr=None):
        CLI_main(self, main, [ 'clubak' ] + args, input, expected_stdout,
                 expected_rc, expected_stderr)

    def test_000_noargs(self):
        """test clubak (no argument)"""
        outfmt = "---------------\n%s\n---------------\n bar\n"
        self._clubak_t([], "foo: bar\n", outfmt % "foo")
        self._clubak_t([], "foo space: bar\n", outfmt % "foo space")
        self._clubak_t([], "foo space1: bar\n", outfmt % "foo space1")
        self._clubak_t([], "foo space1: bar\nfoo space2: bar", outfmt % "foo space1" + outfmt % "foo space2")
        self._clubak_t([], ": bar\n", "", 1, "clubak: no node found (\": bar\")\n")
        self._clubak_t([], "foo[: bar\n", outfmt % "foo[")
        self._clubak_t([], "]o[o]: bar\n", outfmt % "]o[o]")
        self._clubak_t([], "foo:\n", "---------------\nfoo\n---------------\n\n")
        self._clubak_t([], "foo: \n", "---------------\nfoo\n---------------\n \n")

    def test_001_verbosity(self):
        """test clubak (-q/-v/-d)"""
        outfmt = "INPUT foo: bar\n---------------\n%s\n---------------\n bar\n"
        self._clubak_t(["-d"], "foo: bar\n", outfmt % "foo", 0, "line_mode=False gather=False tree_depth=1\n")
        self._clubak_t(["-d", "-b"], "foo: bar\n", outfmt % "foo", 0, "line_mode=False gather=True tree_depth=1\n")
        self._clubak_t(["-d", "-L"], "foo: bar\n", "INPUT foo: bar\nfoo:  bar\n", 0, "line_mode=True gather=False tree_depth=1\n")
        self._clubak_t(["-v"], "foo: bar\n", outfmt % "foo", 0)
        self._clubak_t(["-v", "-b"], "foo: bar\n", outfmt % "foo", 0)
        outfmt = "---------------\n%s\n---------------\n bar\n"
        # no node count with -q
        self._clubak_t(["-q", "-b"], "foo[1-5]: bar\n", outfmt % "foo[1-5]", 0)

    def test_002_b(self):
        """test clubak (gather -b)"""
        outfmt = "---------------\n%s\n---------------\n bar\n"
        self._clubak_t(["-b"], "foo: bar\n", outfmt % "foo")
        self._clubak_t(["-b"], "foo space: bar\n", outfmt % "foo space")
        self._clubak_t(["-b"], "foo space1: bar\n", outfmt % "foo space1")
        self._clubak_t(["-b"], "foo space1: bar\nfoo space2: bar", outfmt % "foo space[1-2] (2)")
        self._clubak_t(["-b"], "foo space1: bar\nfoo space2: foo", "---------------\nfoo space1\n---------------\n bar\n---------------\nfoo space2\n---------------\n foo\n")
        self._clubak_t(["-b"], ": bar\n", "", 1, "clubak: no node found (\": bar\")\n")
        self._clubak_t(["-b"], "foo[: bar\n", outfmt % "foo[")
        self._clubak_t(["-b"], "]o[o]: bar\n", outfmt % "]o[o]")
        self._clubak_t(["-b"], "foo:\n", "---------------\nfoo\n---------------\n\n")
        self._clubak_t(["-b"], "foo: \n", "---------------\nfoo\n---------------\n \n")

    def test_003_L(self):
        """test clubak (line mode -L)"""
        self._clubak_t(["-L"], "foo: bar\n", "foo:  bar\n")
        self._clubak_t(["-L", "-S", ": "], "foo: bar\n", "foo: bar\n")
        self._clubak_t(["-bL"], "foo: bar\n", "foo:  bar\n")
        self._clubak_t(["-bL", "-S", ": "], "foo: bar\n", "foo: bar\n")

    def test_004_N(self):
        """test clubak (no header -N)"""
        self._clubak_t(["-N"], "foo: bar\n", "\n bar\n")
        self._clubak_t(["-NL"], "foo: bar\n", " bar\n")
        self._clubak_t(["-N", "-S", ": "], "foo: bar\n", "\nbar\n")
        self._clubak_t(["-bN"], "foo: bar\n", "\n bar\n")
        self._clubak_t(["-bN", "-S", ": "], "foo: bar\n", "\nbar\n")

    def test_005_fast(self):
        """test clubak (fast mode --fast)"""
        outfmt = "---------------\n%s\n---------------\n bar\n"
        self._clubak_t(["--fast"], "foo: bar\n", outfmt % "foo")
        self._clubak_t(["-b", "--fast"], "foo: bar\n", outfmt % "foo")
        self._clubak_t(["-b", "--fast"], "foo2: bar\nfoo1: bar\nfoo4: bar", outfmt % "foo[1-2,4] (3)")
        # check conflicting options
        self._clubak_t(["-L", "--fast"], "foo2: bar\nfoo1: bar\nfoo4: bar", '', 2, "error: incompatible tree options\n")

    def test_006_tree(self):
        """test clubak (tree mode --tree)"""
        outfmt = "---------------\n%s\n---------------\n bar\n"
        self._clubak_t(["--tree"], "foo: bar\n", outfmt % "foo")
        self._clubak_t(["--tree", "-L"], "foo: bar\n", "foo:\n bar\n")
        input = """foo1:bar
foo2:bar
foo1:moo
foo1:bla
foo2:m00
foo2:bla
foo1:abc
"""
        self._clubak_t(["--tree", "-L"], input, "foo[1-2]:\nbar\nfoo2:\n  m00\n  bla\nfoo1:\n  moo\n  bla\n  abc\n")
        # check conflicting options
        self._clubak_t(["--tree", "--fast"], input, '', 2, "error: incompatible tree options\n")

    def test_007_interpret_keys(self):
        """test clubak (--interpret-keys)"""
        outfmt = "---------------\n%s\n---------------\n bar\n"
        self._clubak_t(["--interpret-keys=auto"], "foo: bar\n", outfmt % "foo")
        self._clubak_t(["-b", "--interpret-keys=auto"], "foo: bar\n", outfmt % "foo")
        self._clubak_t(["-b", "--interpret-keys=never"], "foo: bar\n", outfmt % "foo")
        self._clubak_t(["-b", "--interpret-keys=always"], "foo: bar\n", outfmt % "foo")
        self._clubak_t(["-b", "--interpret-keys=always"], "foo[1-3]: bar\n", outfmt % "foo[1-3] (3)")
        self._clubak_t(["-b", "--interpret-keys=auto"], "[]: bar\n", outfmt % "[]")
        self._clubak_t(["-b", "--interpret-keys=never"], "[]: bar\n", outfmt % "[]")
        self._clubak_t(["-b", "--interpret-keys=always"], "[]: bar\n", '', 1, "Parse error: empty node name : \"[]\"\n")

    def test_008_color(self):
        """test clubak (--color)"""
        outfmt = "---------------\n%s\n---------------\n bar\n"
        self._clubak_t(["-b"], "foo: bar\n", outfmt % "foo")
        self._clubak_t(["-b", "--color=never"], "foo: bar\n", outfmt % "foo")
        self._clubak_t(["-b", "--color=auto"], "foo: bar\n", outfmt % "foo")
        self._clubak_t(["-L", "--color=always"], "foo: bar\n", "\x1b[34mfoo: \x1b[0m bar\n")
        self._clubak_t(["-b", "--color=always"], "foo: bar\n", "\x1b[34m---------------\nfoo\n---------------\x1b[0m\n bar\n")

    def test_009_diff(self):
        """test clubak (--diff)"""
        self._clubak_t(["--diff"], "foo1: bar\nfoo2: bar", "")
        self._clubak_t(["--diff"], "foo1: bar\nfoo2: BAR\nfoo2: end\nfoo1: end",
                                   "--- foo1\n+++ foo2\n@@ -1,2 +1,2 @@\n- bar\n+ BAR\n  end\n")
        self._clubak_t(["--diff"], "foo1: bar\nfoo2: BAR\nfoo3: bar\nfoo2: end\nfoo1: end\nfoo3: end",
                                   "--- foo[1,3] (2)\n+++ foo2\n@@ -1,2 +1,2 @@\n- bar\n+ BAR\n  end\n")
        self._clubak_t(["--diff", "--color=always"], "foo1: bar\nfoo2: BAR\nfoo3: bar\nfoo2: end\nfoo1: end\nfoo3: end",
                                   "\x1b[1m--- foo[1,3] (2)\x1b[0m\n\x1b[1m+++ foo2\x1b[0m\n\x1b[36m@@ -1,2 +1,2 @@\x1b[0m\n\x1b[31m- bar\x1b[0m\n\x1b[32m+ BAR\x1b[0m\n  end\n")
        self._clubak_t(["--diff", "-d"], "foo: bar\n", "INPUT foo: bar\n", 0, "line_mode=False gather=True tree_depth=1\n")
        self._clubak_t(["--diff", "-L"], "foo1: bar\nfoo2: bar", "", 2, "clubak: error: option mismatch (diff not supported in line_mode)\n")


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(CLIClubakTest)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = CLIClushTest
#!/usr/bin/env python
# scripts/clush.py tool test suite
# Written by S. Thiell 2012-03-28


"""Unit test for CLI/Clush.py"""

import errno
import pwd
import subprocess
import sys
import time
import unittest

from TLib import *
import ClusterShell.CLI.Clush
from ClusterShell.CLI.Clush import main
from ClusterShell.Task import task_cleanup


class CLIClushTest_A(unittest.TestCase):
    """Unit test class for testing CLI/Clush.py"""

    def tearDown(self):
        """cleanup all tasks"""
        task_cleanup()

    def _clush_t(self, args, input, expected_stdout, expected_rc=0,
                  expected_stderr=None):
        """This new version allows code coverage checking by calling clush's
        main entry point."""
        def raw_input_mock(prompt):
            # trusty sleep
            wait_time = 60
            start = time.time()
            while (time.time() - start < wait_time):
                time.sleep(wait_time - (time.time() - start))
            return ""
        ClusterShell.CLI.Clush.raw_input = raw_input_mock
        try:
            CLI_main(self, main, [ 'clush' ] + args, input, expected_stdout,
                     expected_rc, expected_stderr)
        finally:
            ClusterShell.CLI.Clush.raw_input = raw_input

    def test_000_display(self):
        """test clush (display options)"""
        self._clush_t(["-w", "localhost", "true"], None, "")
        self._clush_t(["-w", "localhost", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-w", "localhost", "echo", "ok", "ok"], None, \
            "localhost: ok ok\n")
        self._clush_t(["-N", "-w", "localhost", "echo", "ok", "ok"], None, \
            "ok ok\n")
        self._clush_t(["-qw", "localhost", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-vw", "localhost", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-qvw", "localhost", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-Sw", "localhost", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-Sqw", "localhost", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-Svw", "localhost", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["--nostdin", "-w", "localhost", "echo", "ok"], None, \
            "localhost: ok\n")

    def test_001_display_tty(self):
        """test clush (display options) [tty]"""
        setattr(ClusterShell.CLI.Clush, '_f_user_interaction', True)
        try:
            self.test_000_display()
        finally:
            delattr(ClusterShell.CLI.Clush, '_f_user_interaction')

    def test_002_fanout(self):
        """test clush (fanout)"""
        self._clush_t(["-f", "10", "-w", "localhost", "true"], None, "")
        self._clush_t(["-f", "1", "-w", "localhost", "true"], None, "")
        self._clush_t(["-f", "1", "-w", "localhost", "echo", "ok"], None, \
            "localhost: ok\n")

    def test_003_fanout_tty(self):
        """test clush (fanout) [tty]"""
        setattr(ClusterShell.CLI.Clush, '_f_user_interaction', True)
        try:
            self.test_002_fanout()
        finally:
            delattr(ClusterShell.CLI.Clush, '_f_user_interaction')

    def test_004_ssh_options(self):
        """test clush (ssh options)"""
        self._clush_t(["-o", "-oStrictHostKeyChecking=no", "-w", "localhost", \
            "echo", "ok"], None, "localhost: ok\n")
        self._clush_t(["-o", "-oStrictHostKeyChecking=no -oForwardX11=no", \
            "-w", "localhost", "echo", "ok"], None, "localhost: ok\n")
        self._clush_t(["-o", "-oStrictHostKeyChecking=no", "-o", \
            "-oForwardX11=no", "-w", "localhost", "echo", "ok"], None, \
                "localhost: ok\n")
        self._clush_t(["-o-oStrictHostKeyChecking=no", "-o-oForwardX11=no", \
            "-w", "localhost", "echo", "ok"], None, "localhost: ok\n")
        self._clush_t(["-u", "4", "-w", "localhost", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-t", "4", "-u", "4", "-w", "localhost", "echo", \
            "ok"], None, "localhost: ok\n")

    def test_005_ssh_options_tty(self):
        """test clush (ssh options) [tty]"""
        setattr(ClusterShell.CLI.Clush, '_f_user_interaction', True)
        try:
            self.test_004_ssh_options()
        finally:
            delattr(ClusterShell.CLI.Clush, '_f_user_interaction')

    def test_006_output_gathering(self):
        """test clush (output gathering)"""
        self._clush_t(["-w", "localhost", "-L", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-w", "localhost", "-bL", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-w", "localhost", "-qbL", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-w", "localhost", "-BL", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-w", "localhost", "-qBL", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-w", "localhost", "-BLS", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-w", "localhost", "-qBLS", "echo", "ok"], None, \
            "localhost: ok\n")
        self._clush_t(["-w", "localhost", "-vb", "echo", "ok"], None, \
            "localhost: ok\n---------------\nlocalhost\n---------------\nok\n")

    def test_007_output_gathering_tty(self):
        """test clush (output gathering) [tty]"""
        setattr(ClusterShell.CLI.Clush, '_f_user_interaction', True)
        try:
            self.test_006_output_gathering()
        finally:
            delattr(ClusterShell.CLI.Clush, '_f_user_interaction')

    def test_008_file_copy(self):
        """test clush (file copy)"""
        content = "%f" % time.time()
        f = make_temp_file(content)
        self._clush_t(["-w", "localhost", "-c", f.name], None, "")
        f.seek(0)
        self.assertEqual(f.read(), content)
        # test --dest option
        f2 = tempfile.NamedTemporaryFile()
        self._clush_t(["-w", "localhost", "-c", f.name, "--dest", f2.name], \
            None, "")
        f2.seek(0)
        self.assertEqual(f2.read(), content)
        # test --user option
        f2 = tempfile.NamedTemporaryFile()
        self._clush_t(["--user", pwd.getpwuid(os.getuid())[0], "-w", \
            "localhost", "--copy", f.name, "--dest", f2.name], None, "")
        f2.seek(0)
        self.assertEqual(f2.read(), content)
        # test --rcopy
        self._clush_t(["--user", pwd.getpwuid(os.getuid())[0], "-w", \
            "localhost", "--rcopy", f.name, "--dest", \
                os.path.dirname(f.name)], None, "")
        f2.seek(0)
        self.assertEqual(open("%s.localhost" % f.name).read(), content)

    def test_009_file_copy_tty(self):
        """test clush (file copy) [tty]"""
        setattr(ClusterShell.CLI.Clush, '_f_user_interaction', True)
        try:
            self.test_008_file_copy()
        finally:
            delattr(ClusterShell.CLI.Clush, '_f_user_interaction')

    def test_010_diff(self):
        """test clush (diff)"""
        self._clush_t(["-w", "localhost", "--diff", "echo", "ok"], None, "")
        self._clush_t(["-w", "localhost,127.0.0.1", "--diff", "echo", "ok"], None, "")

    def test_011_diff_tty(self):
        """test clush (diff) [tty]"""
        setattr(ClusterShell.CLI.Clush, '_f_user_interaction', True)
        try:
            self.test_010_diff()
        finally:
            delattr(ClusterShell.CLI.Clush, '_f_user_interaction')

    def test_012_stdin(self):
        """test clush (stdin)"""
        self._clush_t(["-w", "localhost", "sleep 1 && cat"], "ok", "localhost: ok\n")
        self._clush_t(["-w", "localhost", "cat"], "ok\nok", "localhost: ok\nlocalhost: ok\n")
        # write binary to stdin
        self._clush_t(["-w", "localhost", "gzip -d"], \
            "1f8b0800869a744f00034bcbcf57484a2ce2020027b4dd1308000000".decode("hex"), "localhost: foo bar\n")

    def test_014_stderr(self):
        """test clush (stderr)"""
        self._clush_t(["-w", "localhost", "echo err 1>&2"], None, "", 0, "localhost: err\n")
        self._clush_t(["-b", "-w", "localhost", "echo err 1>&2"], None, "", 0, "localhost: err\n")
        self._clush_t(["-B", "-w", "localhost", "echo err 1>&2"], None, "---------------\nlocalhost\n---------------\nerr\n")

    def test_015_stderr_tty(self):
        """test clush (stderr) [tty]"""
        setattr(ClusterShell.CLI.Clush, '_f_user_interaction', True)
        try:
            self.test_014_stderr()
        finally:
            delattr(ClusterShell.CLI.Clush, '_f_user_interaction')

    def test_016_retcodes(self):
        """test clush (retcodes)"""
        self._clush_t(["-w", "localhost", "/bin/false"], None, "", 0, "clush: localhost: exited with exit code 1\n")
        self._clush_t(["-w", "localhost", "-b", "/bin/false"], None, "", 0, "clush: localhost: exited with exit code 1\n")
        self._clush_t(["-S", "-w", "localhost", "/bin/false"], None, "", 1, "clush: localhost: exited with exit code 1\n")
        for i in (1, 2, 127, 128, 255):
            self._clush_t(["-S", "-w", "localhost", "exit %d" % i], None, "", i, \
                "clush: localhost: exited with exit code %d\n" % i)
        self._clush_t(["-v", "-w", "localhost", "/bin/false"], None, "", 0, "clush: localhost: exited with exit code 1\n")

    def test_017_retcodes_tty(self):
        """test clush (retcodes) [tty]"""
        setattr(ClusterShell.CLI.Clush, '_f_user_interaction', True)
        try:
            self.test_016_retcodes()
        finally:
            delattr(ClusterShell.CLI.Clush, '_f_user_interaction')

    def test_018_timeout(self):
        """test clush (timeout)"""
        self._clush_t(["-w", "localhost", "-u", "1", "sleep 3"], None,
                       "", 0, "clush: localhost: command timeout\n")
        self._clush_t(["-w", "localhost", "-u", "1", "-b", "sleep 3"], None,
                       "", 0, "clush: localhost: command timeout\n")

    def test_019_timeout_tty(self):
        """test clush (timeout) [tty]"""
        setattr(ClusterShell.CLI.Clush, '_f_user_interaction', True)
        try:
            self.test_018_timeout()
        finally:
            delattr(ClusterShell.CLI.Clush, '_f_user_interaction')

    def test_020_file_copy_timeout(self):
        """test clush file copy (timeout)"""
        content = "%f" % time.time()
        f = make_temp_file(content)
        self._clush_t(["-w", "localhost", "-u", "0.01", "-c", f.name], None,
                       "", 0, "clush: localhost: command timeout\n")

    def test_021_file_copy_timeout_tty(self):
        """test clush file copy (timeout) [tty]"""
        setattr(ClusterShell.CLI.Clush, '_f_user_interaction', True)
        try:
            self.test_020_file_copy_timeout()
        finally:
            delattr(ClusterShell.CLI.Clush, '_f_user_interaction')


class CLIClushTest_B_StdinFailure(unittest.TestCase):
    """Unit test class for testing CLI/Clush.py and stdin failure"""

    def setUp(self):
        class BrokenStdinMock(object):
            def isatty(self):
                return False
            def read(self, bufsize=1024):
                raise IOError(errno.EINVAL, "Invalid argument")

        sys.stdin = BrokenStdinMock()

    def tearDown(self):
        """cleanup all tasks"""
        task_cleanup()
        sys.stdin = sys.__stdin__

    def _clush_t(self, args, input, expected_stdout, expected_rc=0,
                  expected_stderr=None):
        CLI_main(self, main, [ 'clush' ] + args, input, expected_stdout,
                 expected_rc, expected_stderr)

    def test_022_broken_stdin(self):
        """test clush with broken stdin"""
        self._clush_t(["-w", "localhost", "-v", "sleep 1"], None,
                       "stdin: [Errno 22] Invalid argument\n", 0, "")


########NEW FILE########
__FILENAME__ = CLIConfigTest
#!/usr/bin/env python
# ClusterShell.CLI.Config test suite
# Written by S. Thiell 2010-09-19


"""Unit test for CLI.Config"""

import resource
import sys
import tempfile
import unittest

sys.path.insert(0, '../lib')


from ClusterShell.CLI.Clush import set_fdlimit
from ClusterShell.CLI.Config import ClushConfig, ClushConfigError
from ClusterShell.CLI.Display import *
from ClusterShell.CLI.OptionParser import OptionParser


class CLIClushConfigTest(unittest.TestCase):
    """This test case performs a complete CLI.Config.ClushConfig
    verification.  Also CLI.OptionParser is used and some parts are
    verified btw.
    """
    def testClushConfigEmpty(self):
        """test CLI.Config.ClushConfig (empty)"""

        f = tempfile.NamedTemporaryFile(prefix='testclushconfig')
        f.write("""
""")

        parser = OptionParser("dummy")
        parser.install_display_options(verbose_options=True)
        parser.install_ssh_options()
        options, _ = parser.parse_args([])
        config = ClushConfig(options, filename=f.name)
        self.assert_(config != None)
        self.assertEqual(config.color, WHENCOLOR_CHOICES[-1])
        self.assertEqual(config.verbosity, VERB_STD)
        self.assertEqual(config.fanout, 64)
        self.assertEqual(config.node_count, True)
        self.assertEqual(config.connect_timeout, 30)
        self.assertEqual(config.command_timeout, 0)
        self.assertEqual(config.ssh_user, None)
        self.assertEqual(config.ssh_path, None)
        self.assertEqual(config.ssh_options, None)
        f.close()

    def testClushConfigAlmostEmpty(self):
        """test CLI.Config.ClushConfig (almost empty)"""

        f = tempfile.NamedTemporaryFile(prefix='testclushconfig')
        f.write("""
[Main]
""")

        parser = OptionParser("dummy")
        parser.install_display_options(verbose_options=True)
        parser.install_ssh_options()
        options, _ = parser.parse_args([])
        config = ClushConfig(options, filename=f.name)
        self.assert_(config != None)
        self.assertEqual(config.color, WHENCOLOR_CHOICES[-1])
        self.assertEqual(config.verbosity, VERB_STD)
        self.assertEqual(config.node_count, True)
        self.assertEqual(config.fanout, 64)
        self.assertEqual(config.connect_timeout, 30)
        self.assertEqual(config.command_timeout, 0)
        self.assertEqual(config.ssh_user, None)
        self.assertEqual(config.ssh_path, None)
        self.assertEqual(config.ssh_options, None)
        f.close()
        
    def testClushConfigDefault(self):
        """test CLI.Config.ClushConfig (default)"""

        f = tempfile.NamedTemporaryFile(prefix='testclushconfig')
        f.write("""
[Main]
fanout: 42
connect_timeout: 14
command_timeout: 0
history_size: 100
color: auto
verbosity: 1
#ssh_user: root
#ssh_path: /usr/bin/ssh
#ssh_options: -oStrictHostKeyChecking=no
""")

        f.flush()
        parser = OptionParser("dummy")
        parser.install_display_options(verbose_options=True)
        parser.install_ssh_options()
        options, _ = parser.parse_args([])
        config = ClushConfig(options, filename=f.name)
        self.assert_(config != None)
        display = Display(options, config)
        self.assert_(display != None)
        display.vprint(VERB_STD, "test")
        display.vprint(VERB_DEBUG, "shouldn't see this")
        self.assertEqual(config.color, WHENCOLOR_CHOICES[2])
        self.assertEqual(config.verbosity, VERB_STD)
        self.assertEqual(config.node_count, True)
        self.assertEqual(config.fanout, 42)
        self.assertEqual(config.connect_timeout, 14)
        self.assertEqual(config.command_timeout, 0)
        self.assertEqual(config.ssh_user, None)
        self.assertEqual(config.ssh_path, None)
        self.assertEqual(config.ssh_options, None)
        f.close()
        
    def testClushConfigFull(self):
        """test CLI.Config.ClushConfig (full)"""

        f = tempfile.NamedTemporaryFile(prefix='testclushconfig')
        f.write("""
[Main]
fanout: 42
connect_timeout: 14
command_timeout: 0
history_size: 100
color: auto
node_count: yes
verbosity: 1
ssh_user: root
ssh_path: /usr/bin/ssh
ssh_options: -oStrictHostKeyChecking=no
""")

        f.flush()
        parser = OptionParser("dummy")
        parser.install_display_options(verbose_options=True)
        parser.install_ssh_options()
        options, _ = parser.parse_args([])
        config = ClushConfig(options, filename=f.name)
        self.assert_(config != None)
        self.assertEqual(config.color, WHENCOLOR_CHOICES[2])
        self.assertEqual(config.verbosity, VERB_STD)
        self.assertEqual(config.node_count, True)
        self.assertEqual(config.fanout, 42)
        self.assertEqual(config.connect_timeout, 14)
        self.assertEqual(config.command_timeout, 0)
        self.assertEqual(config.ssh_user, "root")
        self.assertEqual(config.ssh_path, "/usr/bin/ssh")
        self.assertEqual(config.ssh_options, "-oStrictHostKeyChecking=no")
        f.close()
        
    def testClushConfigError(self):
        """test CLI.Config.ClushConfig (error)"""

        f = tempfile.NamedTemporaryFile(prefix='testclushconfig')
        f.write("""
[Main]
fanout: 3.2
connect_timeout: foo
command_timeout: bar
history_size: 100
color: maybe
node_count: 3
verbosity: bar
ssh_user: root
ssh_path: /usr/bin/ssh
ssh_options: -oStrictHostKeyChecking=no
""")

        f.flush()
        parser = OptionParser("dummy")
        parser.install_display_options(verbose_options=True)
        parser.install_ssh_options()
        options, _ = parser.parse_args([])
        config = ClushConfig(options, filename=f.name)
        self.assert_(config != None)
        try:
            c = config.color
            self.fail("Exception ClushConfigError not raised (color)")
        except ClushConfigError:
            pass
        self.assertEqual(config.verbosity, 0) # probably for compatibility
        try:
            f = config.fanout
            self.fail("Exception ClushConfigError not raised (fanout)")
        except ClushConfigError:
            pass
        try:
            f = config.node_count
            self.fail("Exception ClushConfigError not raised (node_count)")
        except ClushConfigError:
            pass
        try:
            f = config.fanout
        except ClushConfigError, e:
            self.assertEqual(str(e)[0:20], "(Config Main.fanout)")

        try:
            t = config.connect_timeout
            self.fail("Exception ClushConfigError not raised (connect_timeout)")
        except ClushConfigError:
            pass
        try:
            m = config.command_timeout
            self.fail("Exception ClushConfigError not raised (command_timeout)")
        except ClushConfigError:
            pass
        f.close()

    def testClushConfigSetRlimit(self):
        """test CLI.Config.ClushConfig (setrlimit)"""
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        hard2 = min(32768, hard)
        f = tempfile.NamedTemporaryFile(prefix='testclushconfig')
        f.write("""
[Main]
fanout: 42
connect_timeout: 14
command_timeout: 0
history_size: 100
color: auto
fd_max: %d
verbosity: 1
""" % hard2)

        f.flush()
        parser = OptionParser("dummy")
        parser.install_display_options(verbose_options=True)
        parser.install_ssh_options()
        options, _ = parser.parse_args([])
        config = ClushConfig(options, filename=f.name)
        self.assert_(config != None)
        display = Display(options, config)
        self.assert_(display != None)

        # force a lower soft limit
        resource.setrlimit(resource.RLIMIT_NOFILE, (hard2/2, hard))
        # max_fdlimit should increase soft limit again
        set_fdlimit(config.fd_max, display)
        # verify
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        self.assertEqual(soft, hard2)
        f.close()
       
    def testClushConfigDefaultWithOptions(self):
        """test CLI.Config.ClushConfig (default with options)"""

        f = tempfile.NamedTemporaryFile(prefix='testclushconfig')
        f.write("""
[Main]
fanout: 42
connect_timeout: 14
command_timeout: 0
history_size: 100
color: auto
verbosity: 1
#ssh_user: root
#ssh_path: /usr/bin/ssh
#ssh_options: -oStrictHostKeyChecking=no
""")

        f.flush()
        parser = OptionParser("dummy")
        parser.install_display_options(verbose_options=True)
        parser.install_ssh_options()
        options, _ = parser.parse_args(["-f", "36", "-u", "3", "-t", "7",
                                        "--user", "foobar", "--color",
                                        "always", "-d", "-v", "-q", "-o",
                                        "-oSomething"])
        config = ClushConfig(options, filename=f.name)
        self.assert_(config != None)
        display = Display(options, config)
        self.assert_(display != None)
        display.vprint(VERB_STD, "test")
        display.vprint(VERB_DEBUG, "test")
        self.assertEqual(config.color, WHENCOLOR_CHOICES[1])
        self.assertEqual(config.verbosity, VERB_DEBUG) # takes biggest
        self.assertEqual(config.fanout, 36)
        self.assertEqual(config.connect_timeout, 7)
        self.assertEqual(config.command_timeout, 3)
        self.assertEqual(config.ssh_user, "foobar")
        self.assertEqual(config.ssh_path, None)
        self.assertEqual(config.ssh_options, "-oSomething")
        f.close()
        
    def testClushConfigWithInstalledConfig(self):
        """test CLI.Config.ClushConfig (installed config required)"""
        # This test needs installed configuration files (needed for
        # maximum coverage).
        parser = OptionParser("dummy")
        parser.install_display_options(verbose_options=True)
        parser.install_ssh_options()
        options, _ = parser.parse_args([])
        config = ClushConfig(options)
        self.assert_(config != None)


if __name__ == '__main__':
    suites = [unittest.TestLoader().loadTestsFromTestCase(CLIClushConfigTest)]
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))

########NEW FILE########
__FILENAME__ = CLIDisplayTest
#!/usr/bin/env python
# ClusterShell.CLI.Display test suite
# Written by S. Thiell 2010-09-25


"""Unit test for CLI.Display"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.CLI.Display import Display, WHENCOLOR_CHOICES, VERB_STD
from ClusterShell.CLI.OptionParser import OptionParser

from ClusterShell.MsgTree import MsgTree
from ClusterShell.NodeSet import NodeSet

from ClusterShell.NodeUtils import GroupResolverConfig


def makeTestFile(text):
    """Create a temporary file with the provided text."""
    f = tempfile.NamedTemporaryFile()
    f.write(text)
    f.flush()
    return f

class CLIDisplayTest(unittest.TestCase):
    """This test case performs a complete CLI.Display verification.  Also
    CLI.OptionParser is used and some parts are verified btw.
    """
    def testDisplay(self):
        """test CLI.Display"""
        parser = OptionParser("dummy")
        parser.install_display_options(verbose_options=True)
        options, _ = parser.parse_args([])

        ns = NodeSet("localhost")
        mtree = MsgTree()
        mtree.add("localhost", "message0")
        mtree.add("localhost", "message1")

        for whencolor in WHENCOLOR_CHOICES: # test whencolor switch
            for label in [True, False]:     # test no-label switch
                options.label = label
                options.whencolor = whencolor
                disp = Display(options)
                # inhibit output
                disp.out = open("/dev/null", "w")
                disp.err = open("/dev/null", "w")
                self.assert_(disp != None)
                # test print_* methods...
                disp.print_line(ns, "foo bar")
                disp.print_line_error(ns, "foo bar")
                disp.print_gather(ns, list(mtree.walk())[0][0])
                # test also string nodeset as parameter
                disp.print_gather("localhost", list(mtree.walk())[0][0])
                # test line_mode property
                self.assertEqual(disp.line_mode, False)
                disp.line_mode = True
                self.assertEqual(disp.line_mode, True)
                disp.print_gather("localhost", list(mtree.walk())[0][0])
                disp.line_mode = False
                self.assertEqual(disp.line_mode, False)

    def testDisplayRegroup(self):
        """test CLI.Display (regroup)"""
        parser = OptionParser("dummy")
        parser.install_display_options(verbose_options=True)
        options, _ = parser.parse_args(["-r"])

        mtree = MsgTree()
        mtree.add("localhost", "message0")
        mtree.add("localhost", "message1")

        disp = Display(options)
        self.assertEqual(disp.regroup, True)
        disp.out = open("/dev/null", "w")
        disp.err = open("/dev/null", "w")
        self.assert_(disp != None)
        self.assertEqual(disp.line_mode, False)

        f = makeTestFile("""
# A comment

[Main]
default: local

[local]
map: echo localhost
#all:
list: echo all
#reverse:
        """)
        res = GroupResolverConfig(f.name)
        ns = NodeSet("localhost", resolver=res)

        # nodeset.regroup() is performed by print_gather()
        disp.print_gather(ns, list(mtree.walk())[0][0])

    def testDisplayClubak(self):
        """test CLI.Display for clubak"""
        parser = OptionParser("dummy")
        parser.install_display_options(separator_option=True, dshbak_compat=True)
        options, _ = parser.parse_args([])
        disp = Display(options)
        self.assertEqual(bool(disp.gather), False)
        self.assertEqual(disp.line_mode, False)
        self.assertEqual(disp.label, True)
        self.assertEqual(disp.regroup, False)
        self.assertEqual(bool(disp.groupsource), False)
        self.assertEqual(disp.noprefix, False)
        self.assertEqual(disp.maxrc, False)
        self.assertEqual(disp.node_count, True)
        self.assertEqual(disp.verbosity, VERB_STD)


if __name__ == '__main__':
    suites = [unittest.TestLoader().loadTestsFromTestCase(CLIDisplayTest)]
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))

########NEW FILE########
__FILENAME__ = CLINodesetTest
#!/usr/bin/env python
# scripts/nodeset.py tool test suite
# Written by S. Thiell 2012-03-25


"""Unit test for CLI/Nodeset.py"""

import sys
import unittest

from TLib import *
from ClusterShell.CLI.Nodeset import main

from ClusterShell.NodeUtils import GroupResolverConfig
from ClusterShell.NodeSet import std_group_resolver, set_std_group_resolver

class CLINodesetTestBase(unittest.TestCase):
    """Base unit test class for testing CLI/Nodeset.py"""

    def _nodeset_t(self, args, input, expected_stdout, expected_rc=0,
                   expected_stderr=None):
        CLI_main(self, main, [ 'nodeset' ] + args, input, expected_stdout,
                 expected_rc, expected_stderr)


class CLINodesetTest(CLINodesetTestBase):
    """Unit test class for testing CLI/Nodeset.py"""

    def _battery_count(self, args):
        self._nodeset_t(args + ["--count", "foo"], None, "1\n")
        self._nodeset_t(args + ["--count", "foo", "bar"], None, "2\n")
        self._nodeset_t(args + ["--count", "foo", "foo"], None, "1\n")
        self._nodeset_t(args + ["--count", "foo", "foo", "bar"], None, "2\n")
        self._nodeset_t(args + ["--count", "foo[0]"], None, "1\n")
        self._nodeset_t(args + ["--count", "foo[2]"], None, "1\n")
        self._nodeset_t(args + ["--count", "foo[1,2]"], None, "2\n")
        self._nodeset_t(args + ["--count", "foo[1-2]"], None, "2\n")
        self._nodeset_t(args + ["--count", "foo[1,2]", "foo[1-2]"], None, "2\n")
        self._nodeset_t(args + ["--count", "foo[1-200,245-394]"], None, "350\n")
        self._nodeset_t(args + ["--count", "foo[395-442]", "foo[1-200,245-394]"], None, "398\n")
        self._nodeset_t(args + ["--count", "foo[395-442]", "foo", "foo[1-200,245-394]"], None, "399\n")
        self._nodeset_t(args + ["--count", "foo[395-442]", "foo", "foo[0-200,245-394]"], None, "400\n")
        self._nodeset_t(args + ["--count", "foo[395-442]", "bar3,bar24", "foo[1-200,245-394]"], None, "400\n")
        # from stdin
        self._nodeset_t(args + ["--count"], "foo\n", "1\n")
        self._nodeset_t(args + ["--count"], "foo\nbar\n", "2\n")
        self._nodeset_t(args + ["--count"], "foo\nfoo\n", "1\n")
        self._nodeset_t(args + ["--count"], "foo\nfoo\nbar\n", "2\n")
        self._nodeset_t(args + ["--count"], "foo[0]\n", "1\n")
        self._nodeset_t(args + ["--count"], "foo[2]\n", "1\n")
        self._nodeset_t(args + ["--count"], "foo[1,2]\n", "2\n")
        self._nodeset_t(args + ["--count"], "foo[1-2]\n", "2\n")
        self._nodeset_t(args + ["--count"], "foo[1,2]\nfoo[1-2]\n", "2\n")
        self._nodeset_t(args + ["--count"], "foo[1-200,245-394]\n", "350\n")
        self._nodeset_t(args + ["--count"], "foo[395-442]\nfoo[1-200,245-394]\n", "398\n")
        self._nodeset_t(args + ["--count"], "foo[395-442]\nfoo\nfoo[1-200,245-394]\n", "399\n")
        self._nodeset_t(args + ["--count"], "foo[395-442]\nfoo\nfoo[0-200,245-394]\n", "400\n")
        self._nodeset_t(args + ["--count"], "foo[395-442]\nbar3,bar24\nfoo[1-200,245-394]\n", "400\n")

    def test_001_count(self):
        """test nodeset --count"""
        self._battery_count([])
        self._battery_count(["--autostep=1"])
        self._battery_count(["--autostep=2"])
        self._battery_count(["--autostep=5"])

    def test_002_count_intersection(self):
        """test nodeset --count --intersection"""
        self._nodeset_t(["--count", "foo", "--intersection", "bar"], None, "0\n")
        self._nodeset_t(["--count", "foo", "--intersection", "foo"], None, "1\n")
        self._nodeset_t(["--count", "foo", "--intersection", "foo", "-i", "bar"], None, "0\n")
        self._nodeset_t(["--count", "foo[0]", "--intersection", "foo0"], None, "1\n")
        self._nodeset_t(["--count", "foo[2]", "--intersection", "foo"], None, "0\n")
        self._nodeset_t(["--count", "foo[1,2]", "--intersection", "foo[1-2]"], None, "2\n")
        self._nodeset_t(["--count", "foo[395-442]", "--intersection", "foo[1-200,245-394]"], None, "0\n")
        self._nodeset_t(["--count", "foo[395-442]", "--intersection", "foo", "-i", "foo[1-200,245-394]"], None, "0\n")
        self._nodeset_t(["--count", "foo[395-442]", "-i", "foo", "-i", "foo[0-200,245-394]"], None, "0\n")
        self._nodeset_t(["--count", "foo[395-442]", "--intersection", "bar3,bar24", "-i", "foo[1-200,245-394]"], None, "0\n")

    def test_003_count_intersection_stdin(self):
        """test nodeset --count --intersection (stdin)"""
        self._nodeset_t(["--count", "--intersection", "bar"], "foo\n", "0\n")
        self._nodeset_t(["--count", "--intersection", "foo"], "foo\n", "1\n")
        self._nodeset_t(["--count", "--intersection", "foo", "-i", "bar"], "foo\n", "0\n")
        self._nodeset_t(["--count", "--intersection", "foo0"], "foo[0]\n", "1\n")
        self._nodeset_t(["--count", "--intersection", "foo"], "foo[2]\n", "0\n")
        self._nodeset_t(["--count", "--intersection", "foo[1-2]"], "foo[1,2]\n", "2\n")
        self._nodeset_t(["--count", "--intersection", "foo[1-200,245-394]"], "foo[395-442]\n", "0\n")
        self._nodeset_t(["--count", "--intersection", "foo", "-i", "foo[1-200,245-394]"], "foo[395-442]\n", "0\n")
        self._nodeset_t(["--count", "-i", "foo", "-i", "foo[0-200,245-394]"], "foo[395-442]\n", "0\n")
        self._nodeset_t(["--count", "--intersection", "bar3,bar24", "-i", "foo[1-200,245-394]"], "foo[395-442]\n", "0\n")

    def _battery_fold(self, args):
        self._nodeset_t(args + ["--fold", "foo"], None, "foo\n")
        self._nodeset_t(args + ["--fold", "foo", "bar"], None, "bar,foo\n")
        self._nodeset_t(args + ["--fold", "foo", "foo"], None, "foo\n")
        self._nodeset_t(args + ["--fold", "foo", "foo", "bar"], None, "bar,foo\n")
        self._nodeset_t(args + ["--fold", "foo[0]"], None, "foo0\n")
        self._nodeset_t(args + ["--fold", "foo[2]"], None, "foo2\n")
        self._nodeset_t(args + ["--fold", "foo[1,2]"], None, "foo[1-2]\n")
        self._nodeset_t(args + ["--fold", "foo[1-2]"], None, "foo[1-2]\n")
        self._nodeset_t(args + ["--fold", "foo[1,2]", "foo[1-2]"], None, "foo[1-2]\n")
        self._nodeset_t(args + ["--fold", "foo[1-200,245-394]"], None, "foo[1-200,245-394]\n")
        self._nodeset_t(args + ["--fold", "foo[395-442]", "foo[1-200,245-394]"], None, "foo[1-200,245-442]\n")
        self._nodeset_t(args + ["--fold", "foo[395-442]", "foo", "foo[1-200,245-394]"], None, "foo,foo[1-200,245-442]\n")
        self._nodeset_t(args + ["--fold", "foo[395-442]", "foo", "foo[0-200,245-394]"], None, "foo,foo[0-200,245-442]\n")
        self._nodeset_t(args + ["--fold", "foo[395-442]", "bar3,bar24", "foo[1-200,245-394]"], None, "bar[3,24],foo[1-200,245-442]\n")
        # stdin
        self._nodeset_t(args + ["--fold"], "foo\n", "foo\n")
        self._nodeset_t(args + ["--fold"], "foo\nbar\n", "bar,foo\n")
        self._nodeset_t(args + ["--fold"], "foo\nfoo\n", "foo\n")
        self._nodeset_t(args + ["--fold"], "foo\nfoo\nbar\n", "bar,foo\n")
        self._nodeset_t(args + ["--fold"], "foo[0]\n", "foo0\n")
        self._nodeset_t(args + ["--fold"], "foo[2]\n", "foo2\n")
        self._nodeset_t(args + ["--fold"], "foo[1,2]\n", "foo[1-2]\n")
        self._nodeset_t(args + ["--fold"], "foo[1-2]\n", "foo[1-2]\n")
        self._nodeset_t(args + ["--fold"], "foo[1,2]\nfoo[1-2]\n", "foo[1-2]\n")
        self._nodeset_t(args + ["--fold"], "foo[1-200,245-394]\n", "foo[1-200,245-394]\n")
        self._nodeset_t(args + ["--fold"], "foo[395-442]\nfoo[1-200,245-394]\n", "foo[1-200,245-442]\n")
        self._nodeset_t(args + ["--fold"], "foo[395-442]\nfoo\nfoo[1-200,245-394]\n", "foo,foo[1-200,245-442]\n")
        self._nodeset_t(args + ["--fold"], "foo[395-442]\nfoo\nfoo[0-200,245-394]\n", "foo,foo[0-200,245-442]\n")
        self._nodeset_t(args + ["--fold"], "foo[395-442]\nbar3,bar24\nfoo[1-200,245-394]\n", "bar[3,24],foo[1-200,245-442]\n")

    def test_004_fold(self):
        """test nodeset --fold"""
        self._battery_fold([])
        self._battery_fold(["--autostep=3"])

    def test_005_fold_autostep(self):
        """test nodeset --fold --autostep=X"""
        self._nodeset_t(["--autostep=2", "-f", "foo0", "foo2", "foo4", "foo6"], None, "foo[0-6/2]\n")
        self._nodeset_t(["--autostep=2", "-f", "foo4", "foo2", "foo0", "foo6"], None, "foo[0-6/2]\n")
        self._nodeset_t(["--autostep=3", "-f", "foo0", "foo2", "foo4", "foo6"], None, "foo[0-6/2]\n")
        self._nodeset_t(["--autostep=4", "-f", "foo0", "foo2", "foo4", "foo6"], None, "foo[0-6/2]\n")
        self._nodeset_t(["--autostep=5", "-f", "foo0", "foo2", "foo4", "foo6"], None, "foo[0,2,4,6]\n")

    def test_006_expand(self):
        """test nodeset --expand"""
        self._nodeset_t(["--expand", "foo"], None, "foo\n")
        self._nodeset_t(["--expand", "foo", "bar"], None, "bar foo\n")
        self._nodeset_t(["--expand", "foo", "foo"], None, "foo\n")
        self._nodeset_t(["--expand", "foo[0]"], None, "foo0\n")
        self._nodeset_t(["--expand", "foo[2]"], None, "foo2\n")
        self._nodeset_t(["--expand", "foo[1,2]"], None, "foo1 foo2\n")
        self._nodeset_t(["--expand", "foo[1-2]"], None, "foo1 foo2\n")
        self._nodeset_t(["--expand", "foo[1-2],bar"], None, "bar foo1 foo2\n")

    def test_007_expand_stdin(self):
        """test nodeset --expand (stdin)"""
        self._nodeset_t(["--expand"], "foo\n", "foo\n")
        self._nodeset_t(["--expand"], "foo\nbar\n", "bar foo\n")
        self._nodeset_t(["--expand"], "foo\nfoo\n", "foo\n")
        self._nodeset_t(["--expand"], "foo[0]\n", "foo0\n")
        self._nodeset_t(["--expand"], "foo[2]\n", "foo2\n")
        self._nodeset_t(["--expand"], "foo[1,2]\n", "foo1 foo2\n")
        self._nodeset_t(["--expand"], "foo[1-2]\n", "foo1 foo2\n")
        self._nodeset_t(["--expand"], "foo[1-2],bar\n", "bar foo1 foo2\n")

    def test_008_expand_separator(self):
        """test nodeset --expand -S"""
        self._nodeset_t(["--expand", "-S", ":", "foo"], None, "foo\n")
        self._nodeset_t(["--expand", "-S", ":", "foo", "bar"], None, "bar:foo\n")
        self._nodeset_t(["--expand", "--separator", ":", "foo", "bar"], None, "bar:foo\n")
        self._nodeset_t(["--expand", "--separator=:", "foo", "bar"], None, "bar:foo\n")
        self._nodeset_t(["--expand", "-S", ":", "foo", "foo"], None, "foo\n")
        self._nodeset_t(["--expand", "-S", ":", "foo[0]"], None, "foo0\n")
        self._nodeset_t(["--expand", "-S", ":", "foo[2]"], None, "foo2\n")
        self._nodeset_t(["--expand", "-S", ":", "foo[1,2]"], None, "foo1:foo2\n")
        self._nodeset_t(["--expand", "-S", ":", "foo[1-2]"], None, "foo1:foo2\n")
        self._nodeset_t(["--expand", "-S", " ", "foo[1-2]"], None, "foo1 foo2\n")
        self._nodeset_t(["--expand", "-S", ",", "foo[1-2],bar"], None, "bar,foo1,foo2\n")
        self._nodeset_t(["--expand", "-S", "uuu", "foo[1-2],bar"], None, "baruuufoo1uuufoo2\n")
        self._nodeset_t(["--expand", "-S", "\\n", "foo[1-2]"], None, "foo1\nfoo2\n")

    def test_009_fold_xor(self):
        """test nodeset --fold --xor"""
        self._nodeset_t(["--fold", "foo", "-X", "bar"], None, "bar,foo\n")
        self._nodeset_t(["--fold", "foo", "-X", "foo"], None, "\n")
        self._nodeset_t(["--fold", "foo[1,2]", "-X", "foo[1-2]"], None, "\n")
        self._nodeset_t(["--fold", "foo[1-10]", "-X", "foo[5-15]"], None, "foo[1-4,11-15]\n")
        self._nodeset_t(["--fold", "foo[395-442]", "-X", "foo[1-200,245-394]"], None, "foo[1-200,245-442]\n")
        self._nodeset_t(["--fold", "foo[395-442]", "-X", "foo", "-X", "foo[1-200,245-394]"], None, "foo,foo[1-200,245-442]\n")
        self._nodeset_t(["--fold", "foo[395-442]", "-X", "foo", "-X", "foo[0-200,245-394]"], None, "foo,foo[0-200,245-442]\n")
        self._nodeset_t(["--fold", "foo[395-442]", "-X", "bar3,bar24", "-X", "foo[1-200,245-394]"], None, "bar[3,24],foo[1-200,245-442]\n")

    def test_010_fold_xor_stdin(self):
        """test nodeset --fold --xor (stdin)"""
        self._nodeset_t(["--fold", "-X", "bar"], "foo\n", "bar,foo\n")
        self._nodeset_t(["--fold", "-X", "foo"], "foo\n", "\n")
        self._nodeset_t(["--fold", "-X", "foo[1-2]"], "foo[1,2]\n", "\n")
        self._nodeset_t(["--fold", "-X", "foo[5-15]"], "foo[1-10]\n", "foo[1-4,11-15]\n")
        self._nodeset_t(["--fold", "-X", "foo[1-200,245-394]"], "foo[395-442]\n", "foo[1-200,245-442]\n")
        self._nodeset_t(["--fold", "-X", "foo", "-X", "foo[1-200,245-394]"], "foo[395-442]\n", "foo,foo[1-200,245-442]\n")
        self._nodeset_t(["--fold", "-X", "foo", "-X", "foo[0-200,245-394]"], "foo[395-442]\n", "foo,foo[0-200,245-442]\n")
        self._nodeset_t(["--fold", "-X", "bar3,bar24", "-X", "foo[1-200,245-394]"], "foo[395-442]\n", "bar[3,24],foo[1-200,245-442]\n")
        # using stdin for -X
        self._nodeset_t(["-f","foo[2-4]","-X","-"], "foo4 foo5 foo6\n", "foo[2-3,5-6]\n")
        self._nodeset_t(["-f","-X","-","foo[1-6]"], "foo4 foo5 foo6\n", "foo[1-6]\n")

    def test_011_fold_exclude(self):
        """test nodeset --fold --exclude"""
        # Empty result
        self._nodeset_t(["--fold", "foo", "-x", "foo"], None, "\n")
        # With no range
        self._nodeset_t(["--fold", "foo,bar", "-x", "foo"], None, "bar\n")
        # Normal with range
        self._nodeset_t(["--fold", "foo[0-5]", "-x", "foo[0-10]"], None, "\n")
        self._nodeset_t(["--fold", "foo[0-10]", "-x", "foo[0-5]"], None, "foo[6-10]\n")
        # Do no change
        self._nodeset_t(["--fold", "foo[6-10]", "-x", "bar[0-5]"], None, "foo[6-10]\n")
        self._nodeset_t(["--fold", "foo[0-10]", "foo[13-18]", "--exclude", "foo[5-10,15]"], None, "foo[0-4,13-14,16-18]\n")

    def test_012_fold_exclude_stdin(self):
        """test nodeset --fold --exclude (stdin)"""
        # Empty result
        self._nodeset_t(["--fold", "-x", "foo"], "", "\n")
        self._nodeset_t(["--fold", "-x", "foo"], "\n", "\n")
        self._nodeset_t(["--fold", "-x", "foo"], "foo\n", "\n")
        # With no range
        self._nodeset_t(["--fold", "-x", "foo"], "foo,bar\n", "bar\n")
        # Normal with range
        self._nodeset_t(["--fold", "-x", "foo[0-10]"], "foo[0-5]\n", "\n")
        self._nodeset_t(["--fold", "-x", "foo[0-5]"], "foo[0-10]\n", "foo[6-10]\n")
        # Do no change
        self._nodeset_t(["--fold", "-x", "bar[0-5]"], "foo[6-10]\n", "foo[6-10]\n")
        self._nodeset_t(["--fold", "--exclude", "foo[5-10,15]"], "foo[0-10]\nfoo[13-18]\n", "foo[0-4,13-14,16-18]\n")
        # using stdin for -x
        self._nodeset_t(["-f","foo[1-6]","-x","-"], "foo4 foo5 foo6\n", "foo[1-3]\n")
        self._nodeset_t(["-f","-x","-","foo[1-6]"], "foo4 foo5 foo6\n", "foo[1-6]\n")

    def test_013_fold_intersection(self):
        """test nodeset --fold --intersection"""
        # Empty result
        self._nodeset_t(["--fold", "foo", "-i", "foo"], None, "foo\n")
        # With no range
        self._nodeset_t(["--fold", "foo,bar", "--intersection", "foo"], None, "foo\n")
        # Normal with range
        self._nodeset_t(["--fold", "foo[0-5]", "-i", "foo[0-10]"], None, "foo[0-5]\n")
        self._nodeset_t(["--fold", "foo[0-10]", "-i", "foo[0-5]"], None, "foo[0-5]\n")
        self._nodeset_t(["--fold", "foo[6-10]", "-i", "bar[0-5]"], None, "\n")
        self._nodeset_t(["--fold", "foo[0-10]", "foo[13-18]", "-i", "foo[5-10,15]"], None, "foo[5-10,15]\n")

    def test_014_fold_intersection_stdin(self):
        """test nodeset --fold --intersection (stdin)"""
        # Empty result
        self._nodeset_t(["--fold", "--intersection", "foo"], "", "\n")
        self._nodeset_t(["--fold", "--intersection", "foo"], "\n", "\n")
        self._nodeset_t(["--fold", "-i", "foo"], "foo\n", "foo\n")
        # With no range
        self._nodeset_t(["--fold", "-i", "foo"], "foo,bar\n", "foo\n")
        # Normal with range
        self._nodeset_t(["--fold", "-i", "foo[0-10]"], "foo[0-5]\n", "foo[0-5]\n")
        self._nodeset_t(["--fold", "-i", "foo[0-5]"], "foo[0-10]\n", "foo[0-5]\n")
        # Do no change
        self._nodeset_t(["--fold", "-i", "bar[0-5]"], "foo[6-10]\n", "\n")
        self._nodeset_t(["--fold", "-i", "foo[5-10,15]"], "foo[0-10]\nfoo[13-18]\n", "foo[5-10,15]\n")
        # using stdin for -i
        self._nodeset_t(["-f","foo[1-6]","-i","-"], "foo4 foo5 foo6\n", "foo[4-6]\n")
        self._nodeset_t(["-f","-i","-","foo[1-6]"], "foo4 foo5 foo6\n", "foo[1-6]\n")

    def test_015_rangeset(self):
        """test nodeset --rangeset"""
        self._nodeset_t(["--fold","--rangeset","1,2"], None, "1-2\n")
        self._nodeset_t(["--expand","-R","1-2"], None, "1 2\n")
        self._nodeset_t(["--fold","-R","1-2","-X","2-3"], None, "1,3\n")

    def test_016_rangeset_stdin(self):
        """test nodeset --rangeset (stdin)"""
        self._nodeset_t(["--fold","--rangeset"], "1,2\n", "1-2\n")
        self._nodeset_t(["--expand","-R"], "1-2\n", "1 2\n")
        self._nodeset_t(["--fold","-R","-X","2-3"], "1-2\n", "1,3\n")

    def test_017_stdin(self):
        """test nodeset - (stdin)"""
        self._nodeset_t(["-f","-"], "foo\n", "foo\n")
        self._nodeset_t(["-f","-"], "foo1 foo2 foo3\n", "foo[1-3]\n")
        self._nodeset_t(["--autostep=2", "-f"], "foo0 foo2 foo4 foo6\n", "foo[0-6/2]\n")

    def test_018_split(self):
        """test nodeset --split"""
        self._nodeset_t(["--split=2","-f", "bar"], None, "bar\n")
        self._nodeset_t(["--split", "2","-f", "foo,bar"], None, "bar\nfoo\n")
        self._nodeset_t(["--split", "2","-e", "foo", "bar", "bur", "oof", "gcc"], None, "bar bur foo\ngcc oof\n")
        self._nodeset_t(["--split=2","-f", "foo[2-9]"], None, "foo[2-5]\nfoo[6-9]\n")
        self._nodeset_t(["--split=2","-f", "foo[2-3,7]", "bar9"], None, "bar9,foo2\nfoo[3,7]\n")
        self._nodeset_t(["--split=3","-f", "foo[2-9]"], None, "foo[2-4]\nfoo[5-7]\nfoo[8-9]\n")
        self._nodeset_t(["--split=1","-f", "foo2", "foo3"], None, "foo[2-3]\n")
        self._nodeset_t(["--split=4","-f", "foo[2-3]"], None, "foo2\nfoo3\n")
        self._nodeset_t(["--split=4","-f", "foo3", "foo2"], None, "foo2\nfoo3\n")
        self._nodeset_t(["--split=2","-e", "foo[2-9]"], None, "foo2 foo3 foo4 foo5\nfoo6 foo7 foo8 foo9\n")
        self._nodeset_t(["--split=3","-e", "foo[2-9]"], None, "foo2 foo3 foo4\nfoo5 foo6 foo7\nfoo8 foo9\n")
        self._nodeset_t(["--split=1","-e", "foo3", "foo2"], None, "foo2 foo3\n")
        self._nodeset_t(["--split=4","-e", "foo[2-3]"], None, "foo2\nfoo3\n")
        self._nodeset_t(["--split=4","-e", "foo2", "foo3"], None, "foo2\nfoo3\n")
        self._nodeset_t(["--split=2","-c", "foo2", "foo3"], None, "1\n1\n")

    def test_019_contiguous(self):
        """test nodeset --contiguous"""
        self._nodeset_t(["--contiguous", "-f", "bar"], None, "bar\n")
        self._nodeset_t(["--contiguous", "-f", "foo,bar"], None, "bar\nfoo\n")
        self._nodeset_t(["--contiguous", "-f", "foo", "bar", "bur", "oof", "gcc"], None, "bar\nbur\nfoo\ngcc\noof\n")
        self._nodeset_t(["--contiguous", "-e", "foo", "bar", "bur", "oof", "gcc"], None, "bar\nbur\nfoo\ngcc\noof\n")
        self._nodeset_t(["--contiguous", "-f", "foo2"], None, "foo2\n")
        self._nodeset_t(["--contiguous", "-R", "-f", "2"], None, "2\n")
        self._nodeset_t(["--contiguous", "-f", "foo[2-9]"], None, "foo[2-9]\n")
        self._nodeset_t(["--contiguous", "-f", "foo[2-3,7]", "bar9"], None, "bar9\nfoo[2-3]\nfoo7\n")
        self._nodeset_t(["--contiguous", "-R", "-f", "2-3,7", "9"], None, "2-3\n7\n9\n")
        self._nodeset_t(["--contiguous", "-f", "foo2", "foo3"], None, "foo[2-3]\n")
        self._nodeset_t(["--contiguous", "-f", "foo3", "foo2"], None, "foo[2-3]\n")
        self._nodeset_t(["--contiguous", "-f", "foo3", "foo1"], None, "foo1\nfoo3\n")
        self._nodeset_t(["--contiguous", "-f", "foo[1-5/2]", "foo7"], None, "foo1\nfoo3\nfoo5\nfoo7\n")

    def test_020_slice(self):
        """test nodeset -I/--slice"""
        self._nodeset_t(["--slice=0","-f", "bar"], None, "bar\n")
        self._nodeset_t(["--slice=0","-e", "bar"], None, "bar\n")
        self._nodeset_t(["--slice=1","-f", "bar"], None, "\n")
        self._nodeset_t(["--slice=0-1","-f", "bar"], None, "bar\n")
        self._nodeset_t(["-I0","-f", "bar[34-68,89-90]"], None, "bar34\n")
        self._nodeset_t(["-R", "-I0","-f", "34-68,89-90"], None, "34\n")
        self._nodeset_t(["-I 0","-f", "bar[34-68,89-90]"], None, "bar34\n")
        self._nodeset_t(["-I 0","-e", "bar[34-68,89-90]"], None, "bar34\n")
        self._nodeset_t(["-I 0-3","-f", "bar[34-68,89-90]"], None, "bar[34-37]\n")
        self._nodeset_t(["-I 0-3","-f", "bar[34-68,89-90]", "-x", "bar34"], None, "bar[35-38]\n")
        self._nodeset_t(["-I 0-3","-f", "bar[34-68,89-90]", "-x", "bar35"], None, "bar[34,36-38]\n")
        self._nodeset_t(["-I 0-3","-e", "bar[34-68,89-90]"], None, "bar34 bar35 bar36 bar37\n")
        self._nodeset_t(["-I 3,1,0,2","-f", "bar[34-68,89-90]"], None, "bar[34-37]\n")
        self._nodeset_t(["-I 1,3,7,10,16,20,30,34-35,37","-f", "bar[34-68,89-90]"], None, "bar[35,37,41,44,50,54,64,68,89]\n")
        self._nodeset_t(["-I 8","-f", "bar[34-68,89-90]"], None, "bar42\n")
        self._nodeset_t(["-I 8-100","-f", "bar[34-68,89-90]"], None, "bar[42-68,89-90]\n")
        self._nodeset_t(["-I 0-100","-f", "bar[34-68,89-90]"], None, "bar[34-68,89-90]\n")
        self._nodeset_t(["-I 8-100/2","-f", "bar[34-68,89-90]"], None, "bar[42,44,46,48,50,52,54,56,58,60,62,64,66,68,90]\n")
        self._nodeset_t(["--autostep=2", "-I 8-100/2","-f", "bar[34-68,89-90]"], None, "bar[42-68/2,90]\n")

    def test_021_slice_stdin(self):
        """test nodeset -I/--slice (stdin)"""
        self._nodeset_t(["--slice=0","-f"], "bar\n", "bar\n")
        self._nodeset_t(["--slice=0","-e"], "bar\n", "bar\n")
        self._nodeset_t(["--slice=1","-f"], "bar\n", "\n")
        self._nodeset_t(["--slice=0-1","-f"], "bar\n", "bar\n")
        self._nodeset_t(["-I0","-f"], "bar[34-68,89-90]\n", "bar34\n")
        self._nodeset_t(["-R", "-I0","-f"], "34-68,89-90\n", "34\n")
        self._nodeset_t(["-I 0","-f"], "bar[34-68,89-90]\n", "bar34\n")
        self._nodeset_t(["-I 0","-e"], "bar[34-68,89-90]\n", "bar34\n")
        self._nodeset_t(["-I 0-3","-f"], "bar[34-68,89-90]\n", "bar[34-37]\n")
        self._nodeset_t(["-I 0-3","-f", "-x", "bar34"], "bar[34-68,89-90]\n", "bar[35-38]\n")
        self._nodeset_t(["-I 0-3","-f", "-x", "bar35"], "bar[34-68,89-90]\n", "bar[34,36-38]\n")
        self._nodeset_t(["-I 0-3","-e"], "bar[34-68,89-90]\n", "bar34 bar35 bar36 bar37\n")
        self._nodeset_t(["-I 3,1,0,2","-f"], "bar[34-68,89-90]\n", "bar[34-37]\n")
        self._nodeset_t(["-I 1,3,7,10,16,20,30,34-35,37","-f"], "bar[34-68,89-90]\n", "bar[35,37,41,44,50,54,64,68,89]\n")
        self._nodeset_t(["-I 8","-f"], "bar[34-68,89-90]\n", "bar42\n")
        self._nodeset_t(["-I 8-100","-f"], "bar[34-68,89-90]\n", "bar[42-68,89-90]\n")
        self._nodeset_t(["-I 0-100","-f"], "bar[34-68,89-90]\n", "bar[34-68,89-90]\n")
        self._nodeset_t(["-I 8-100/2","-f"], "bar[34-68,89-90]\n", "bar[42,44,46,48,50,52,54,56,58,60,62,64,66,68,90]\n")
        self._nodeset_t(["--autostep=2", "-I 8-100/2","-f"], "bar[34-68,89-90]\n", "bar[42-68/2,90]\n")

class CLINodesetGroupResolverTest1(CLINodesetTestBase):
    """Unit test class for testing CLI/Nodeset.py with custom Group Resolver"""

    def setUp(self):
        # Special tests that require a default group source set
        f = make_temp_file("""
[Main]
default: local

[local]
map: echo example[1-100]
all: echo example[1-1000]
list: echo foo bar moo
        """)
        set_std_group_resolver(GroupResolverConfig(f.name))

    def tearDown(self):
        set_std_group_resolver(None)

    def test_022_list(self):
        """test nodeset --list"""
        self._nodeset_t(["--list"], None, "@bar\n@foo\n@moo\n")
        self._nodeset_t(["-ll"], None, "@bar example[1-100]\n@foo example[1-100]\n@moo example[1-100]\n")
        self._nodeset_t(["-lll"], None, "@bar example[1-100] 100\n@foo example[1-100] 100\n@moo example[1-100] 100\n")
        self._nodeset_t(["-l", "example[4,95]", "example5"], None, "@moo\n@bar\n@foo\n")
        self._nodeset_t(["-ll", "example[4,95]", "example5"], None, "@moo example[4-5,95]\n@bar example[4-5,95]\n@foo example[4-5,95]\n")
        self._nodeset_t(["-lll", "example[4,95]", "example5"], None, "@moo example[4-5,95] 3/100\n@bar example[4-5,95] 3/100\n@foo example[4-5,95] 3/100\n")
        # test empty result
        self._nodeset_t(["-l", "foo[3-70]", "bar6"], None, "")
        # more arg-mixed tests
        self._nodeset_t(["-a", "-l"], None, "@moo\n@bar\n@foo\n")
        self._nodeset_t(["-a", "-l", "-x example[1-100]"], None, "")
        self._nodeset_t(["-a", "-l", "-x example[1-40]"], None, "@moo\n@bar\n@foo\n")
        self._nodeset_t(["-l", "-x example3"], None, "") # no -a, remove from nothing
        self._nodeset_t(["-l", "-i example3"], None, "") # no -a, intersect from nothing
        self._nodeset_t(["-l", "-X example3"], None, "@moo\n@bar\n@foo\n") # no -a, xor from nothing
        self._nodeset_t(["-l", "-", "-i example3"], "example[3,500]\n", "@moo\n@bar\n@foo\n")

class CLINodesetGroupResolverTest2(CLINodesetTestBase):
    """Unit test class for testing CLI/Nodeset.py with custom Group Resolver"""

    def setUp(self):
        # Special tests that require a default group source set
        f = make_temp_file("""
[Main]
default: test

[test]
map: echo example[1-100]
all: echo @foo,@bar,@moo
list: echo foo bar moo
        """)
        set_std_group_resolver(GroupResolverConfig(f.name))

    def tearDown(self):
        set_std_group_resolver(None)

    def test_023_groups(self):
        """test nodeset with groups"""
        self._nodeset_t(["--split=2","-r", "unknown2", "unknown3"], None, "unknown2\nunknown3\n")
        self._nodeset_t(["-f", "-a"], None, "example[1-100]\n")
        self._nodeset_t(["-f", "@moo"], None, "example[1-100]\n")
        self._nodeset_t(["-f", "@moo", "@bar"], None, "example[1-100]\n")
        self._nodeset_t(["-e", "-a"], None, ' '.join(["example%d" % i for i in range(1, 101)]) + '\n')
        self._nodeset_t(["-c", "-a"], None, "100\n")
        self._nodeset_t(["-r", "-a"], None, "@bar\n")
        self._nodeset_t(["-s", "test", "-c", "-a", "-d"], None, "100\n")
        self._nodeset_t(["-s", "test", "-r", "-a"], None, "@test:bar\n")
        self._nodeset_t(["-s", "test", "-G", "-r", "-a"], None, "@bar\n")
        self._nodeset_t(["-s", "test", "--groupsources"], None, "test (default)\n")
        self._nodeset_t(["-f", "-a", "-"], "example101\n", "example[1-101]\n")
        self._nodeset_t(["-f", "-a", "-"], "example102 example101\n", "example[1-102]\n")


########NEW FILE########
__FILENAME__ = CLIOptionParserTest
#!/usr/bin/env python
# ClusterShell.CLI.OptionParser test suite
# Written by S. Thiell 2010-09-25


"""Unit test for CLI.OptionParser"""

from optparse import OptionConflictError
import os
import sys
import tempfile
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.CLI.OptionParser import OptionParser


class CLIOptionParserTest(unittest.TestCase):
    """This test case performs a complete CLI.OptionParser
    verification.
    """
    def testOptionParser(self):
        """test CLI.OptionParser (1)"""
        parser = OptionParser("dummy")
        parser.install_nodes_options()
        parser.install_display_options(verbose_options=True)
        parser.install_filecopy_options()
        parser.install_ssh_options()
        options, _ = parser.parse_args([])

    def testOptionParser2(self):
        """test CLI.OptionParser (2)"""
        parser = OptionParser("dummy")
        parser.install_nodes_options()
        parser.install_display_options(verbose_options=True, separator_option=True)
        parser.install_filecopy_options()
        parser.install_ssh_options()
        options, _ = parser.parse_args([])

    def testOptionParserConflicts(self):
        """test CLI.OptionParser (conflicting options)"""
        parser = OptionParser("dummy")
        parser.install_nodes_options()
        parser.install_display_options(dshbak_compat=True)
        self.assertRaises(OptionConflictError, parser.install_filecopy_options)

    def testOptionParserClubak(self):
        """test CLI.OptionParser for clubak"""
        parser = OptionParser("dummy")
        parser.install_nodes_options()
        parser.install_display_options(separator_option=True, dshbak_compat=True)
        options, _ = parser.parse_args([])


if __name__ == '__main__':
    suites = [unittest.TestLoader().loadTestsFromTestCase(CLIOptionParserTest)]
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))

########NEW FILE########
__FILENAME__ = MisusageTest
#!/usr/bin/env python
# ClusterShell test suite
# Written by S. Thiell 2010-02-19


"""Unit test for ClusterShell common library misusages"""

import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.Event import EventHandler
from ClusterShell.Worker.Popen import WorkerPopen
from ClusterShell.Worker.Ssh import WorkerSsh
from ClusterShell.Worker.Worker import WorkerError
from ClusterShell.Task import Task, task_self, AlreadyRunningError


class MisusageTest(unittest.TestCase):

    def testTaskResumedTwice(self):
        """test library misusage (task_self resumed twice)"""
        class ResumeAgainHandler(EventHandler):
            def ev_read(self, worker):
                worker.task.resume()
        task = task_self()
        task.shell("/bin/echo OK", handler=ResumeAgainHandler())
        self.assertRaises(AlreadyRunningError, task.resume)

    def testWorkerNotScheduledLocal(self):
        """test library misusage (local worker not scheduled)"""
        task = task_self()
        worker = WorkerPopen(command="/bin/hostname")
        task.resume()
        self.assertRaises(WorkerError, worker.read)

    def testWorkerNotScheduledDistant(self):
        """test library misusage (distant worker not scheduled)"""
        task = task_self()
        worker = WorkerSsh("localhost", command="/bin/hostname", handler=None, timeout=0)
        self.assert_(worker != None)
        task.resume()
        self.assertRaises(WorkerError, worker.node_buffer, "localhost")

    def testTaskScheduleTwice(self):
        """test task worker schedule twice error"""
        task = task_self()
        self.assert_(task != None)
        worker = task.shell("/bin/echo itsme")
        self.assertRaises(WorkerError, task.schedule, worker)
        task.abort()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(MisusageTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = MsgTreeTest
#!/usr/bin/env python
# ClusterShell test suite
# Written by S. Thiell 2010-02-03


"""Unit test for ClusterShell MsgTree Class"""

from operator import itemgetter
import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.MsgTree import *


class MsgTreeTest(unittest.TestCase):

    def test_001_basics(self):
        """test MsgTree basics"""
        tree = MsgTree()
        self.assertEqual(len(tree), 0)

        tree.add("key", "message")
        self.assertEqual(len(tree), 1)

        tree.add("key", "message2")
        self.assertEqual(len(tree), 1)

        tree.add("key2", "message3")
        self.assertEqual(len(tree), 2)

    def test_002_elem(self):
        """test MsgTreeElem"""
        elem = MsgTreeElem()
        self.assertEqual(len(elem), 0)
        for s in elem:
            self.fail("found line in empty MsgTreeElem!")

    def test_003_iterators(self):
        """test MsgTree iterators"""
        # build tree...
        tree = MsgTree()
        self.assertEqual(len(tree), 0)
        tree.add(("item1", "key"), "message0")
        self.assertEqual(len(tree), 1)
        tree.add(("item2", "key"), "message2")
        self.assertEqual(len(tree), 2)
        tree.add(("item3", "key"), "message3")
        self.assertEqual(len(tree), 3)
        tree.add(("item4", "key"), "message3")
        tree.add(("item2", "newkey"), "message4")
        self.assertEqual(len(tree), 5)
        self.assertEqual(tree._depth(), 1)

        # test standard iterator (over keys)
        cnt = 0
        what = set([ ("item1", "key"), ("item2", "key"), ("item3", "key"), \
                    ("item4", "key"), ("item2", "newkey") ])
        for key in tree:
            cnt += 1
            what.remove(key)
        self.assertEqual(cnt, 5)
        self.assertEqual(len(what), 0)

        # test keys() iterator
        cnt = 0
        for key in tree.keys(): # keep this test for return value check
            cnt += 1
        self.assertEqual(cnt, 5)
        self.assertEqual(len(list(iter(tree.keys()))), 5)

        # test messages() iterator (iterate over different messages)
        cnt = 0
        for msg in tree.messages():
            cnt += 1
            self.assertEqual(len(msg), len("message0"))
            self.assertEqual(msg[0][:-1], "message")
        self.assertEqual(cnt, 4)
        self.assertEqual(len(list(iter(tree.messages()))), 4)

        # test items() iterator (iterate over all key, msg pairs)
        cnt = 0
        for key, msg in tree.items():
            cnt += 1
        self.assertEqual(cnt, 5)
        self.assertEqual(len(list(iter(tree.items()))), 5)
            
        # test walk() iterator (iterate by msg and give the list of
        # associated keys)
        cnt = 0
        cnt_2 = 0
        for msg, keys in tree.walk():
            cnt += 1
            if len(keys) == 2:
                self.assertEqual(msg, "message3")
                cnt_2 += 1
        self.assertEqual(cnt, 4)
        self.assertEqual(cnt_2, 1)
        self.assertEqual(len(list(iter(tree.walk()))), 4)

        # test walk() with provided key-filter
        cnt = 0
        for msg, keys in tree.walk(match=lambda s: s[1] == "newkey"):
            cnt += 1
        self.assertEqual(cnt, 1)

        # test walk() with provided key-mapper
        cnt = 0
        cnt_2 = 0
        for msg, keys in tree.walk(mapper=itemgetter(0)):
            cnt += 1
            if len(keys) == 2:
                for k in keys:
                    self.assertEqual(type(k), str)
                cnt_2 += 1
        self.assertEqual(cnt, 4)
        self.assertEqual(cnt_2, 1)

        # test walk with full options: key-filter and key-mapper
        cnt = 0
        for msg, keys in tree.walk(match=lambda k: k[1] == "newkey",
                                       mapper=itemgetter(0)):
            cnt += 1
            self.assertEqual(msg, "message4")
            self.assertEqual(keys[0], "item2")
        self.assertEqual(cnt, 1)

        cnt = 0
        for msg, keys in tree.walk(match=lambda k: k[1] == "key",
                                       mapper=itemgetter(0)):
            cnt += 1
            self.assertEqual(keys[0][:-1], "item")
        self.assertEqual(cnt, 3) # 3 and not 4 because item3 and item4 are merged

    def test_004_getitem(self):
        """test MsgTree get and __getitem__"""
        # build tree...
        tree = MsgTree()
        tree.add("item1", "message0")
        self.assertEqual(len(tree), 1)
        tree.add("item2", "message2")
        tree.add("item3", "message2")
        tree.add("item4", "message3")
        tree.add("item2", "message4")
        tree.add("item3", "message4")
        self.assertEqual(len(tree), 4)
        self.assertEqual(tree["item1"], "message0")
        self.assertEqual(tree.get("item1"), "message0")
        self.assertEqual(tree["item2"], "message2\nmessage4")
        self.assertEqual(tree.get("item2"), "message2\nmessage4")
        self.assertEqual(tree.get("item5", "default_buf"), "default_buf")
        self.assertEqual(tree._depth(), 2)

    def test_005_remove(self):
        """test MsgTree.remove()"""
        # build tree
        tree = MsgTree()
        self.assertEqual(len(tree), 0)
        tree.add(("w1", "key1"), "message0")
        self.assertEqual(len(tree), 1)
        tree.add(("w1", "key2"), "message0")
        self.assertEqual(len(tree), 2)
        tree.add(("w1", "key3"), "message0")
        self.assertEqual(len(tree), 3)
        tree.add(("w2", "key4"), "message1")
        self.assertEqual(len(tree), 4)
        tree.remove(lambda k: k[1] == "key2")
        self.assertEqual(len(tree), 3)
        for msg, keys in tree.walk(match=lambda k: k[0] == "w1",
                                   mapper=itemgetter(1)):
            self.assertEqual(msg, "message0")
            self.assertEqual(len(keys), 2)
        tree.remove(lambda k: k[0] == "w1")
        self.assertEqual(len(tree), 1)
        tree.remove(lambda k: k[0] == "w2")
        self.assertEqual(len(tree), 0)
        tree.clear()
        self.assertEqual(len(tree), 0)

    def test_006_scalability(self):
        """test MsgTree scalability"""
        # build tree...
        tree = MsgTree()
        for i in xrange(0, 10000):
            tree.add("node%d" % i, "message%d" % i)
        self.assertEqual(len(tree), 10000)
        cnt = 0
        for msg, keys in tree.walk():
            cnt += 1

    def test_007_shift_mode(self):
        """test MsgTree in shift mode"""
        tree = MsgTree(mode=MODE_SHIFT)
        tree.add("item1", "message0")
        self.assertEqual(len(tree), 1)
        tree.add("item2", "message2")
        tree.add("item3", "message2")
        tree.add("item4", "message3")
        tree.add("item2", "message4")
        tree.add("item3", "message4")
        self.assertEqual(len(tree), 4)
        self.assertEqual(tree["item1"], "message0")
        self.assertEqual(tree.get("item1"), "message0")
        self.assertEqual(tree["item2"], "message2\nmessage4")
        self.assertEqual(tree.get("item2"), "message2\nmessage4")
        self.assertEqual(tree.get("item5", "default_buf"), "default_buf")
        self.assertEqual(tree._depth(), 2)
        self.assertEqual(len(list(tree.walk())), 3)

    def test_008_trace_mode(self):
        """test MsgTree in trace mode"""
        tree = MsgTree(mode=MODE_TRACE)
        tree.add("item1", "message0")
        self.assertEqual(len(tree), 1)
        tree.add("item2", "message2")
        tree.add("item3", "message2")
        tree.add("item4", "message3")
        tree.add("item2", "message4")
        tree.add("item3", "message4")
        self.assertEqual(len(tree), 4)
        self.assertEqual(tree["item1"], "message0")
        self.assertEqual(tree.get("item1"), "message0")
        self.assertEqual(tree["item2"], "message2\nmessage4")
        self.assertEqual(tree.get("item2"), "message2\nmessage4")
        self.assertEqual(tree.get("item5", "default_buf"), "default_buf")
        self.assertEqual(tree._depth(), 2)
        self.assertEqual(len(list(tree.walk())), 4)
        self.assertEqual(list(tree.walk_trace()), \
            [('message0', ['item1'], 1, 0),
             ('message2', ['item2', 'item3'], 1, 1),
             ('message4', ['item2', 'item3'], 2, 0),
             ('message3', ['item4'], 1, 0)])


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(MsgTreeTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = NodeSetErrorTest
#!/usr/bin/env python
# ClusterShell.NodeSet.NodeSet error handling test suite
# Written by S. Thiell 2008-09-28


"""Unit test for RangeSet errors"""

import copy
import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.RangeSet import RangeSet, RangeSetND
from ClusterShell.NodeSet import NodeSet
from ClusterShell.NodeSet import NodeSetBase
from ClusterShell.NodeSet import NodeSetError
from ClusterShell.NodeSet import NodeSetParseError
from ClusterShell.NodeSet import NodeSetParseRangeError


class NodeSetErrorTest(unittest.TestCase):

    def _testNS(self, pattern, expected_exc):
        try:
            nodeset = NodeSet(pattern)
            print nodeset
        except NodeSetParseError, e:
            self.assertEqual(e.__class__, expected_exc)
            return
        except NodeSetParseRangeError, e:
            self.assertEqual(e.__class__, expected_exc)
            return
        except:
            raise
        self.assert_(0, "error not detected/no exception raised [pattern=%s]" % pattern)
            

    def testBadRangeUsages(self):
        """test NodeSet parse errors in range"""
        self._testNS("", NodeSetParseError)
        self._testNS("nova[]", NodeSetParseRangeError)
        self._testNS("nova[-]", NodeSetParseRangeError)
        self._testNS("nova[A]", NodeSetParseRangeError)
        self._testNS("nova[2-5/a]", NodeSetParseRangeError)
        self._testNS("nova[3/2]", NodeSetParseRangeError)
        self._testNS("nova[3-/2]", NodeSetParseRangeError)
        self._testNS("nova[-3/2]", NodeSetParseRangeError)
        self._testNS("nova[-/2]", NodeSetParseRangeError)
        self._testNS("nova[4-a/2]", NodeSetParseRangeError)
        self._testNS("nova[4-3/2]", NodeSetParseRangeError)
        self._testNS("nova[4-5/-2]", NodeSetParseRangeError)
        self._testNS("nova[4-2/-2]", NodeSetParseRangeError)
        self._testNS("nova[004-002]", NodeSetParseRangeError)
        self._testNS("nova[3-59/2,102a]", NodeSetParseRangeError)
        self._testNS("nova[3-59/2,,102]", NodeSetParseRangeError)
        self._testNS("nova%s" % ("3" * 101), NodeSetParseRangeError)
        # nD
        self._testNS("nova[]p0", NodeSetParseRangeError)
        self._testNS("nova[-]p0", NodeSetParseRangeError)
        self._testNS("nova[A]p0", NodeSetParseRangeError)
        self._testNS("nova[2-5/a]p0", NodeSetParseRangeError)
        self._testNS("nova[3/2]p0", NodeSetParseRangeError)
        self._testNS("nova[3-/2]p0", NodeSetParseRangeError)
        self._testNS("nova[-3/2]p0", NodeSetParseRangeError)
        self._testNS("nova[-/2]p0", NodeSetParseRangeError)
        self._testNS("nova[4-a/2]p0", NodeSetParseRangeError)
        self._testNS("nova[4-3/2]p0", NodeSetParseRangeError)
        self._testNS("nova[4-5/-2]p0", NodeSetParseRangeError)
        self._testNS("nova[4-2/-2]p0", NodeSetParseRangeError)
        self._testNS("nova[004-002]p0", NodeSetParseRangeError)
        self._testNS("nova[3-59/2,102a]p0", NodeSetParseRangeError)
        self._testNS("nova[3-59/2,,102]p0", NodeSetParseRangeError)
        self._testNS("nova%sp0" % ("3" * 101), NodeSetParseRangeError)
        self._testNS("x4nova[]p0", NodeSetParseRangeError)
        self._testNS("x4nova[-]p0", NodeSetParseRangeError)
        self._testNS("x4nova[A]p0", NodeSetParseRangeError)
        self._testNS("x4nova[2-5/a]p0", NodeSetParseRangeError)
        self._testNS("x4nova[3/2]p0", NodeSetParseRangeError)
        self._testNS("x4nova[3-/2]p0", NodeSetParseRangeError)
        self._testNS("x4nova[-3/2]p0", NodeSetParseRangeError)
        self._testNS("x4nova[-/2]p0", NodeSetParseRangeError)
        self._testNS("x4nova[4-a/2]p0", NodeSetParseRangeError)
        self._testNS("x4nova[4-3/2]p0", NodeSetParseRangeError)
        self._testNS("x4nova[4-5/-2]p0", NodeSetParseRangeError)
        self._testNS("x4nova[4-2/-2]p0", NodeSetParseRangeError)
        self._testNS("x4nova[004-002]p0", NodeSetParseRangeError)
        self._testNS("x4nova[3-59/2,102a]p0", NodeSetParseRangeError)
        self._testNS("x4nova[3-59/2,,102]p0", NodeSetParseRangeError)
        self._testNS("x4nova%sp0" % ("3" * 101), NodeSetParseRangeError)

    def testBadUsages(self):
        """test NodeSet other parse errors"""
        self._testNS("nova[3-59/2,102", NodeSetParseError)
        self._testNS("nova3,nova4,,nova6", NodeSetParseError)
        self._testNS("nova3,nova4,5,nova6", NodeSetParseError)
        self._testNS("nova3,nova4,[5-8],nova6", NodeSetParseError)
        self._testNS("nova6,", NodeSetParseError)
        self._testNS("nova6[", NodeSetParseError)
        self._testNS("nova6]", NodeSetParseError)
        #self._testNS("nova%s", NodeSetParseError)
        # nD more
        self._testNS("[1-30][4-9]", NodeSetParseError)
        self._testNS("[1-30][4-9]p", NodeSetParseError)
        self._testNS("x[1-30][4-9]p", NodeSetParseError)
        self._testNS("x[1-30]p4-9]", NodeSetParseError)
        self._testNS("xazer][1-30]p[4-9]", NodeSetParseError)
        self._testNS("xa[[zer[1-30]p[4-9]", NodeSetParseRangeError)

    def testTypeSanityCheck(self):
        """test NodeSet input type sanity check"""
        self.assertRaises(TypeError, NodeSet, dict())
        self.assertRaises(TypeError, NodeSet, list())
        self.assertRaises(ValueError, NodeSetBase, None, RangeSet("1-10"))

    def testRangeSetEntryMismatch(self):
        """test NodeSet RangeSet entry mismatch"""
        nodeset = NodeSet("toto%s")
        rangeset = RangeSet("5")
        self.assertRaises(NodeSetError, nodeset._add, "toto%%s", rangeset)

    def test_bad_slices(self):
        nodeset = NodeSet("cluster[1-30]c[1-2]")
        self.assertRaises(TypeError, nodeset.__getitem__, "zz")
        self.assertRaises(TypeError, nodeset.__getitem__, slice(1,'foo'))

    def test_binary_bad_object_type(self):
        nodeset = NodeSet("cluster[1-30]c[1-2]")
        class Dummy: pass
        dummy = Dummy()
        self.assertRaises(TypeError, nodeset.add, dummy)

    def test_internal_mismatch(self):
        nodeset = NodeSet("cluster[1-30]c[1-2]")
        self.assertTrue("cluster%sc%s" in nodeset._patterns)
        nodeset._patterns["cluster%sc%s"] = RangeSetND([[1]])
        self.assertRaises(NodeSetParseError, str, nodeset)
        nodeset._patterns["cluster%sc%s"] = RangeSetND([[1, 1]])
        self.assertEqual(str(nodeset), "cluster1c1")
        nodeset._patterns["cluster%sc%s"] = RangeSetND([[1, 1, 1]])
        self.assertRaises(NodeSetParseError, str, nodeset)


########NEW FILE########
__FILENAME__ = NodeSetGroupTest
#!/usr/bin/env python
# ClusterShell.Node* test suite
# Written by S. Thiell 2010-03-18


"""Unit test for NodeSet with Group support"""

import copy
import shutil
import sys
import unittest

sys.path.insert(0, '../lib')

from TLib import *

# Wildcard import for testing purpose
from ClusterShell.NodeSet import *
from ClusterShell.NodeUtils import *


def makeTestG1():
    """Create a temporary group file 1"""
    f1 = make_temp_file("""
#
oss: montana5,montana4
mds: montana6
io: montana[4-6]
#42: montana3
compute: montana[32-163]
chassis1: montana[32-33]
chassis2: montana[34-35]
 
chassis3: montana[36-37]
  
chassis4: montana[38-39]
chassis5: montana[40-41]
chassis6: montana[42-43]
chassis7: montana[44-45]
chassis8: montana[46-47]
chassis9: montana[48-49]
chassis10: montana[50-51]
chassis11: montana[52-53]
chassis12: montana[54-55]
Uppercase: montana[1-2]
gpuchassis: @chassis[4-5]
gpu: montana[38-41]
all: montana[1-6,32-163]
""")
    # /!\ Need to return file object and not f1.name, otherwise the temporary
    # file might be immediately unlinked.
    return f1

def makeTestG2():
    """Create a temporary group file 2"""
    f2 = make_temp_file("""
#
#
para: montana[32-37,42-55]
gpu: montana[38-41]
""")
    return f2

def makeTestG3():
    """Create a temporary group file 3"""
    f3 = make_temp_file("""
#
#
all: montana[32-55]
para: montana[32-37,42-55]
gpu: montana[38-41]
login: montana[32-33]
overclock: montana[41-42]
chassis1: montana[32-33]
chassis2: montana[34-35]
chassis3: montana[36-37]
single: idaho
""")
    return f3

def makeTestR3():
    """Create a temporary reverse group file 3"""
    r3 = make_temp_file("""
#
#
montana32: all,para,login,chassis1
montana33: all,para,login,chassis1
montana34: all,para,chassis2
montana35: all,para,chassis2
montana36: all,para,chassis3
montana37: all,para,chassis3
montana38: all,gpu
montana39: all,gpu
montana40: all,gpu
montana41: all,gpu,overclock
montana42: all,para,overclock
montana43: all,para
montana44: all,para
montana45: all,para
montana46: all,para
montana47: all,para
montana48: all,para
montana49: all,para
montana50: all,para
montana51: all,para
montana52: all,para
montana53: all,para
montana54: all,para
montana55: all,para
idaho: single
""")
    return r3

def makeTestG4():
    """Create a temporary group file 4 (nD)"""
    f4 = make_temp_file("""
#
rack-x1y1: idaho1z1,idaho2z1
rack-x1y2: idaho2z1,idaho3z1
rack-x2y1: idaho4z1,idaho5z1
rack-x2y2: idaho6z1,idaho7z1
rack-x1: @rack-x1y[1-2]
rack-x2: @rack-x2y[1-2]
rack-y1: @rack-x[1-2]y1
rack-y2: @rack-x[1-2]y2
rack-all: @rack-x[1-2]y[1-2]
""")
    return f4

class NodeSetGroupTest(unittest.TestCase):

    def setUp(self):
        """setUp test reproducibility: change standard group resolver
        to ensure that no local group source is used during tests"""
        set_std_group_resolver(GroupResolver()) # dummy resolver

    def tearDown(self):
        """tearDown: restore standard group resolver"""
        set_std_group_resolver(None) # restore std resolver

    def testGroupResolverSimple(self):
        """test NodeSet with simple custom GroupResolver"""

        test_groups1 = makeTestG1()

        source = GroupSource("simple",
                             "sed -n 's/^$GROUP:\(.*\)/\\1/p' %s" % test_groups1.name,
                             "sed -n 's/^all:\(.*\)/\\1/p' %s" % test_groups1.name,
                             "sed -n 's/^\([0-9A-Za-z_-]*\):.*/\\1/p' %s" % test_groups1.name,
                             None)

        # create custom resolver with default source
        res = GroupResolver(source)
        self.assertFalse(res.has_node_groups())
        self.assertFalse(res.has_node_groups("dummy_namespace"))

        nodeset = NodeSet("@gpu", resolver=res)
        self.assertEqual(nodeset, NodeSet("montana[38-41]"))
        self.assertEqual(str(nodeset), "montana[38-41]")

        nodeset = NodeSet("@chassis3", resolver=res)
        self.assertEqual(str(nodeset), "montana[36-37]")

        nodeset = NodeSet("@chassis[3-4]", resolver=res)
        self.assertEqual(str(nodeset), "montana[36-39]")

        nodeset = NodeSet("@chassis[1,3,5]", resolver=res)
        self.assertEqual(str(nodeset), "montana[32-33,36-37,40-41]")

        nodeset = NodeSet("@chassis[2-12/2]", resolver=res)
        self.assertEqual(str(nodeset), "montana[34-35,38-39,42-43,46-47,50-51,54-55]")

        nodeset = NodeSet("@chassis[1,3-4,5-11/3]", resolver=res)
        self.assertEqual(str(nodeset), "montana[32-33,36-41,46-47,52-53]")

        # test recursive group gpuchassis
        nodeset1 = NodeSet("@chassis[4-5]", resolver=res)
        nodeset2 = NodeSet("@gpu", resolver=res)
        nodeset3 = NodeSet("@gpuchassis", resolver=res)
        self.assertEqual(nodeset1, nodeset2)
        self.assertEqual(nodeset2, nodeset3)

        # test also with some inline operations
        nodeset = NodeSet("montana3,@gpuchassis!montana39,montana77^montana38",
                          resolver=res)
        self.assertEqual(str(nodeset), "montana[3,40-41,77]")

    def testAllNoResolver(self):
        """test NodeSet.fromall() with no resolver"""
        self.assertRaises(NodeSetExternalError, NodeSet.fromall,
                          resolver=RESOLVER_NOGROUP)
            
    def testGroupsNoResolver(self):
        """test NodeSet.groups() with no resolver"""
        nodeset = NodeSet("foo", resolver=RESOLVER_NOGROUP)
        self.assertRaises(NodeSetExternalError, nodeset.groups)

    def testGroupResolverAddSourceError(self):
        """test GroupResolver.add_source() error"""

        test_groups1 = makeTestG1()

        source = GroupSource("simple",
                             "sed -n 's/^$GROUP:\(.*\)/\\1/p' %s" % test_groups1.name,
                             "sed -n 's/^all:\(.*\)/\\1/p' %s" % test_groups1.name,
                             "sed -n 's/^\([0-9A-Za-z_-]*\):.*/\\1/p' %s" % test_groups1.name,
                             None)

        res = GroupResolver(source)
        # adding the same source again should raise ValueError
        self.assertRaises(ValueError, res.add_source, source)

    def testGroupResolverMinimal(self):
        """test NodeSet with minimal GroupResolver"""
        
        test_groups1 = makeTestG1()

        source = GroupSource("minimal",
                             "sed -n 's/^$GROUP:\(.*\)/\\1/p' %s" % test_groups1.name,
                             None, None, None)

        # create custom resolver with default source
        res = GroupResolver(source)

        nodeset = NodeSet("@gpu", resolver=res)
        self.assertEqual(nodeset, NodeSet("montana[38-41]"))
        self.assertEqual(str(nodeset), "montana[38-41]")

        self.assertRaises(NodeSetExternalError, NodeSet.fromall, resolver=res)

    
    def testConfigEmpty(self):
        """test groups with an empty configuration file"""
        f = make_temp_file("")
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        self.assertRaises(GroupResolverSourceError, nodeset.regroup)
        # non existant group
        self.assertRaises(GroupResolverSourceError, NodeSet, "@bar", resolver=res)

    def testConfigBasicLocal(self):
        """test groups with a basic local config file"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: echo example[1-100]
#all:
list: echo foo
#reverse:
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        self.assertEqual(nodeset.regroup(), "@foo")
        self.assertEqual(nodeset.groups().keys(), ["@foo"])
        self.assertEqual(str(NodeSet("@foo", resolver=res)), "example[1-100]")

        # No 'all' defined: all_nodes() should raise an error
        self.assertRaises(GroupSourceNoUpcall, res.all_nodes)
        # No 'reverse' defined: node_groups() should raise an error
        self.assertRaises(GroupSourceNoUpcall, res.node_groups, "example1")

        # regroup with rest
        nodeset = NodeSet("example[1-101]", resolver=res)
        self.assertEqual(nodeset.regroup(), "@foo,example101")

        # regroup incomplete
        nodeset = NodeSet("example[50-200]", resolver=res)
        self.assertEqual(nodeset.regroup(), "example[50-200]")

        # regroup no matching
        nodeset = NodeSet("example[102-200]", resolver=res)
        self.assertEqual(nodeset.regroup(), "example[102-200]")

    def testConfigWrongSyntax(self):
        """test wrong groups config syntax"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
something: echo example[1-100]
        """)
        self.assertRaises(GroupResolverConfigError, GroupResolverConfig, f.name)

    def testConfigBasicLocalVerbose(self):
        """test groups with a basic local config file (verbose)"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: echo example[1-100]
#all:
list: echo foo
#reverse:
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        self.assertEqual(nodeset.regroup(), "@foo")
        self.assertEqual(str(NodeSet("@foo", resolver=res)), "example[1-100]")

    def testConfigBasicLocalAlternative(self):
        """test groups with a basic local config file (= alternative)"""
        f = make_temp_file("""
# A comment

[Main]
default=local

[local]
map=echo example[1-100]
#all=
list=echo foo
#reverse=
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        self.assertEqual(nodeset.regroup(), "@foo")
        self.assertEqual(str(NodeSet("@foo", resolver=res)), "example[1-100]")
        # @truc?

    def testConfigBasicEmptyDefault(self):
        """test groups with a empty default namespace"""
        f = make_temp_file("""
# A comment

[Main]
default: 

[local]
map: echo example[1-100]
#all:
list: echo foo
#reverse:
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        self.assertEqual(nodeset.regroup(), "@foo")
        self.assertEqual(str(NodeSet("@foo", resolver=res)), "example[1-100]")

    def testConfigBasicNoMain(self):
        """test groups with a local config without main section"""
        f = make_temp_file("""
# A comment

[local]
map: echo example[1-100]
#all:
list: echo foo
#reverse:
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        self.assertEqual(nodeset.regroup(), "@foo")
        self.assertEqual(str(NodeSet("@foo", resolver=res)), "example[1-100]")

    def testConfigBasicWrongDefault(self):
        """test groups with a wrong default namespace"""
        f = make_temp_file("""
# A comment

[Main]
default: pointless

[local]
map: echo example[1-100]
#all:
list: echo foo
#reverse:
        """)
        self.assertRaises(GroupResolverConfigError, GroupResolverConfig, f.name)

    def testConfigQueryFailed(self):
        """test groups with config and failed query"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: false
#all:
list: echo foo
#reverse:
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        self.assertRaises(NodeSetExternalError, nodeset.regroup)

    def testConfigRegroupWrongNamespace(self):
        """test groups by calling regroup(wrong_namespace)"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: echo example[1-100]
#all:
list: echo foo
#reverse:
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertRaises(GroupResolverSourceError, nodeset.regroup, "unknown")

    def testConfigNoListNoReverse(self):
        """test groups with no list and not reverse upcall"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: echo example[1-100]
#all:
#list:
#reverse:
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        # not able to regroup, should still return valid nodeset
        self.assertEqual(nodeset.regroup(), "example[1-100]")

    def testConfigNoListButReverseQuery(self):
        """test groups with no list but reverse upcall"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: echo example[1-100]
#all:
#list: echo foo
reverse: echo foo
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        self.assertEqual(nodeset.regroup(), "@foo")

    def testConfigNoMap(self):
        """test groups with no map upcall"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
#map: echo example[1-100]
all:
list: echo foo
#reverse: echo foo
        """)
        # map is a mandatory upcall, an exception should be raised early
        self.assertRaises(GroupResolverConfigError, GroupResolverConfig, f.name)

    def testConfigWithEmptyList(self):
        """test groups with list upcall returning nothing"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: echo example[1-100]
#all:
list: :
reverse: echo foo
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        self.assertEqual(nodeset.regroup(), "@foo")

    def testConfigListAllWithAll(self):
        """test all groups listing with all upcall"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: echo example[1-100]
all: echo foo bar
list: echo foo
#reverse:
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-50]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-50]")
        self.assertEqual(str(NodeSet.fromall(resolver=res)), "bar,foo")
        # test "@*" magic group listing
        nodeset = NodeSet("@*", resolver=res)
        self.assertEqual(str(nodeset), "bar,foo")
        nodeset = NodeSet("rab,@*,oof", resolver=res)
        self.assertEqual(str(nodeset), "bar,foo,oof,rab")
        # with group source
        nodeset = NodeSet("@local:*", resolver=res)
        self.assertEqual(str(nodeset), "bar,foo")
        nodeset = NodeSet("rab,@local:*,oof", resolver=res)
        self.assertEqual(str(nodeset), "bar,foo,oof,rab")


    def testConfigListAllWithoutAll(self):
        """test all groups listing without all upcall"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: echo example[1-100]
#all:
list: echo foo bar
#reverse:
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-50]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-50]")
        self.assertEqual(str(NodeSet.fromall(resolver=res)), "example[1-100]")
        # test "@*" magic group listing
        nodeset = NodeSet("@*", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        nodeset = NodeSet("@*,example[101-104]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-104]")
        nodeset = NodeSet("example[105-149],@*,example[101-104]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-149]")
        # with group source
        nodeset = NodeSet("@local:*", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        nodeset = NodeSet("example0,@local:*,example[101-110]", resolver=res)
        self.assertEqual(str(nodeset), "example[0-110]")

    def testConfigListAllNDWithoutAll(self):
        """test all groups listing without all upcall (nD)"""
        # Even in nD, ensure that $GROUP is a simple group that has been previously expanded
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: if [[ $GROUP == "x1y[3-4]" ]]; then exit 1; elif [[ $GROUP == "x1y1" ]]; then echo rack[1-5]z[1-42]; else echo rack[6-10]z[1-42]; fi
#all:
list: echo x1y1 x1y2 x1y[3-4]
#reverse:
        """)
        res = GroupResolverConfig(f.name, illegal_chars=ILLEGAL_GROUP_CHARS)
        nodeset = NodeSet("rack3z40", resolver=res)
        self.assertEqual(str(NodeSet.fromall(resolver=res)), "rack[1-10]z[1-42]")
        self.assertEqual(res.grouplist(), ['x1y1', 'x1y2', 'x1y[3-4]']) # raw
        self.assertEqual(grouplist(resolver=res), ['x1y1', 'x1y2', 'x1y3', 'x1y4']) # cleaned
        # test "@*" magic group listing
        nodeset = NodeSet("@*", resolver=res)
        self.assertEqual(str(nodeset), "rack[1-10]z[1-42]")
        # with group source
        nodeset = NodeSet("@local:*", resolver=res)
        self.assertEqual(str(nodeset), "rack[1-10]z[1-42]")
        nodeset = NodeSet("rack11z1,@local:*,rack11z[2-42]", resolver=res)
        self.assertEqual(str(nodeset), "rack[1-11]z[1-42]")

    def testConfigIllegalCharsND(self):
        """test group list containing illegal characters"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: echo rack[6-10]z[1-42]
#all:
list: echo x1y1 x1y2 @illegal x1y[3-4]
#reverse:
        """)
        res = GroupResolverConfig(f.name, illegal_chars=ILLEGAL_GROUP_CHARS)
        nodeset = NodeSet("rack3z40", resolver=res)
        self.assertRaises(GroupResolverIllegalCharError, res.grouplist)

    def testConfigResolverSources(self):
        """test sources() with groups config of 2 sources"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: echo example[1-100]

[other]
map: echo example[1-10]
        """)
        res = GroupResolverConfig(f.name)
        self.assertEqual(len(res.sources()), 2)
        self.assert_('local' in res.sources())
        self.assert_('other' in res.sources())

    def testConfigCrossRefs(self):
        """test groups config with cross references"""
        f = make_temp_file("""
# A comment

[Main]
default: other

[local]
map: echo example[1-100]

[other]
map: echo "foo: @local:foo" | sed -n 's/^$GROUP:\(.*\)/\\1/p'
""")
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("@other:foo", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")

    def testConfigGroupsDirDummy(self):
        """test groups with groupsdir defined (dummy)"""
        f = make_temp_file("""

[Main]
default: local
groupsdir: /path/to/nowhere

[local]
map: echo example[1-100]
#all:
list: echo foo
#reverse:
        """)
        res = GroupResolverConfig(f.name)
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertEqual(str(nodeset), "example[1-100]")
        self.assertEqual(nodeset.regroup(), "@foo")
        self.assertEqual(str(NodeSet("@foo", resolver=res)), "example[1-100]")

    def testConfigGroupsDirExists(self):
        """test groups with groupsdir defined (real, other)"""
        dname = make_temp_dir()
        f = make_temp_file("""

[Main]
default: new_local
groupsdir: %s

[local]
map: echo example[1-100]
#all:
list: echo foo
#reverse:
        """ % dname)
        f2 = make_temp_file("""
[new_local]
map: echo example[1-100]
#all:
list: echo bar
#reverse:
        """, suffix=".conf", dir=dname)
        try:
            res = GroupResolverConfig(f.name)
            nodeset = NodeSet("example[1-100]", resolver=res)
            self.assertEqual(str(nodeset), "example[1-100]")
            self.assertEqual(nodeset.regroup(), "@bar")
            self.assertEqual(str(NodeSet("@bar", resolver=res)), "example[1-100]")
        finally:
            f2.close()
            f.close()
            shutil.rmtree(dname, ignore_errors=True)

    def testConfigGroupsDirDupConfig(self):
        """test groups with duplicate in groupsdir"""
        dname = make_temp_dir()
        f = make_temp_file("""

[Main]
default: iamdup
groupsdir: %s

[local]
map: echo example[1-100]
#all:
list: echo foo
#reverse:
        """ % dname)
        f2 = make_temp_file("""
[iamdup]
map: echo example[1-100]
#all:
list: echo bar
#reverse:
        """, suffix=".conf", dir=dname)
        f3 = make_temp_file("""
[iamdup]
map: echo example[10-200]
#all:
list: echo patato
#reverse:
        """, suffix=".conf", dir=dname)
        try:
            self.assertRaises(GroupResolverConfigError, GroupResolverConfig, f.name)
        finally:
            f3.close()
            f2.close()
            f.close()
            shutil.rmtree(dname, ignore_errors=True)

    def testConfigGroupsDirExistsNoOther(self):
        """test groups with groupsdir defined (real, no other)"""
        dname1 = make_temp_dir()
        dname2 = make_temp_dir()
        f = make_temp_file("""

[Main]
default: new_local
groupsdir: %s %s
        """ % (dname1, dname2))
        f2 = make_temp_file("""
[new_local]
map: echo example[1-100]
#all:
list: echo bar
#reverse:
        """, suffix=".conf", dir=dname2)
        try:
            res = GroupResolverConfig(f.name)
            nodeset = NodeSet("example[1-100]", resolver=res)
            self.assertEqual(str(nodeset), "example[1-100]")
            self.assertEqual(nodeset.regroup(), "@bar")
            self.assertEqual(str(NodeSet("@bar", resolver=res)), "example[1-100]")
        finally:
            f2.close()
            f.close()
            shutil.rmtree(dname1, ignore_errors=True)
            shutil.rmtree(dname2, ignore_errors=True)

    def testConfigGroupsDirNotADirectory(self):
        """test groups with groupsdir defined (not a directory)"""
        dname = make_temp_dir()
        fdummy = make_temp_file("wrong")
        f = make_temp_file("""

[Main]
default: new_local
groupsdir: %s
        """ % fdummy.name)
        try:
            self.assertRaises(GroupResolverConfigError, GroupResolverConfig, f.name)
        finally:
            fdummy.close()
            f.close()
            shutil.rmtree(dname, ignore_errors=True)

    def testConfigIllegalChars(self):
        """test groups with illegal characters"""
        f = make_temp_file("""
# A comment

[Main]
default: local

[local]
map: echo example[1-100]
#all:
list: echo 'foo *'
reverse: echo f^oo
        """)
        res = GroupResolverConfig(f.name, illegal_chars=set("@,&!&^*"))
        nodeset = NodeSet("example[1-100]", resolver=res)
        self.assertRaises(GroupResolverIllegalCharError, nodeset.groups)
        self.assertRaises(GroupResolverIllegalCharError, nodeset.regroup)

    def testGroupResolverND(self):
        """test NodeSet with simple custom GroupResolver (nD)"""

        test_groups4 = makeTestG4()

        source = GroupSource("simple",
                             "sed -n 's/^$GROUP:\(.*\)/\\1/p' %s" % test_groups4.name,
                             "sed -n 's/^all:\(.*\)/\\1/p' %s" % test_groups4.name,
                             "sed -n 's/^\([0-9A-Za-z_-]*\):.*/\\1/p' %s" % test_groups4.name,
                             None)

        # create custom resolver with default source
        res = GroupResolver(source)
        self.assertFalse(res.has_node_groups())
        self.assertFalse(res.has_node_groups("dummy_namespace"))

        nodeset = NodeSet("@rack-x1y2", resolver=res)
        self.assertEqual(nodeset, NodeSet("idaho[2-3]z1"))
        self.assertEqual(str(nodeset), "idaho[2-3]z1")

        nodeset = NodeSet("@rack-y1", resolver=res)
        self.assertEqual(str(nodeset), "idaho[1-2,4-5]z1")

        nodeset = NodeSet("@rack-all", resolver=res)
        self.assertEqual(str(nodeset), "idaho[1-7]z1")

        # test nD groups()
        self.assertEqual(sorted(nodeset.groups().keys()), ['@rack-x1y1', '@rack-x1y2', '@rack-x2y1', '@rack-x2y2'])
        self.assertEqual(sorted(nodeset.groups(groupsource="simple").keys()), ['@simple:rack-x1y1', '@simple:rack-x1y2', '@simple:rack-x2y1', '@simple:rack-x2y2'])
        self.assertEqual(sorted(nodeset.groups(groupsource="simple", noprefix=True).keys()), ['@rack-x1y1', '@rack-x1y2', '@rack-x2y1', '@rack-x2y2'])
        testns = NodeSet()
        for gnodes, inodes in nodeset.groups().itervalues():
            testns.update(inodes)
        self.assertEqual(testns, nodeset)


class NodeSetGroup2GSTest(unittest.TestCase):

    def setUp(self):
        """configure simple RESOLVER_STD_GROUP"""

        # create temporary groups file and keep a reference to avoid file closing
        self.test_groups1 = makeTestG1()
        self.test_groups2 = makeTestG2()

        # create 2 GroupSource objects
        default = GroupSource("default",
                              "sed -n 's/^$GROUP:\(.*\)/\\1/p' %s" % self.test_groups1.name,
                              "sed -n 's/^all:\(.*\)/\\1/p' %s" % self.test_groups1.name,
                              "sed -n 's/^\([0-9A-Za-z_-]*\):.*/\\1/p' %s" % self.test_groups1.name,
                              None)

        source2 = GroupSource("source2",
                              "sed -n 's/^$GROUP:\(.*\)/\\1/p' %s" % self.test_groups2.name,
                              "sed -n 's/^all:\(.*\)/\\1/p' %s" % self.test_groups2.name,
                              "sed -n 's/^\([0-9A-Za-z_-]*\):.*/\\1/p' %s" % self.test_groups2.name,
                              None)

        resolver = GroupResolver(default)
        resolver.add_source(source2)
        set_std_group_resolver(resolver)

    def tearDown(self):
        """restore default RESOLVER_STD_GROUP"""
        set_std_group_resolver(None)
        del self.test_groups1
        del self.test_groups2

    def testGroupSyntaxes(self):
        """test NodeSet group operation syntaxes"""
        nodeset = NodeSet("@gpu")
        self.assertEqual(str(nodeset), "montana[38-41]")

        nodeset = NodeSet("@chassis[1-3,5]&@chassis[2-3]")
        self.assertEqual(str(nodeset), "montana[34-37]")

        nodeset1 = NodeSet("@io!@mds")
        nodeset2 = NodeSet("@oss")
        self.assertEqual(str(nodeset1), str(nodeset2))
        self.assertEqual(str(nodeset1), "montana[4-5]")

    def testGroupListDefault(self):
        """test NodeSet group listing GroupResolver.grouplist()"""
        groups = std_group_resolver().grouplist()
        self.assertEqual(len(groups), 20)
        helper_groups = grouplist()
        self.assertEqual(len(helper_groups), 20)
        total = 0
        nodes = NodeSet()
        for group in groups:
            ns = NodeSet("@%s" % group)
            total += len(ns)
            nodes.update(ns)
        self.assertEqual(total, 310)

        all_nodes = NodeSet.fromall()
        self.assertEqual(len(all_nodes), len(nodes))
        self.assertEqual(all_nodes, nodes)

    def testGroupListSource2(self):
        """test NodeSet group listing GroupResolver.grouplist(source)"""
        groups = std_group_resolver().grouplist("source2")
        self.assertEqual(len(groups), 2)
        total = 0
        for group in groups:
            total += len(NodeSet("@source2:%s" % group))
        self.assertEqual(total, 24)

    def testGroupNoPrefix(self):
        """test NodeSet group noprefix option"""
        nodeset = NodeSet("montana[32-37,42-55]")
        self.assertEqual(nodeset.regroup("source2"), "@source2:para")
        self.assertEqual(nodeset.regroup("source2", noprefix=True), "@para")

    def testGroupGroups(self):
        """test NodeSet.groups()"""
        nodeset = NodeSet("montana[32-37,42-55]")
        self.assertEqual(sorted(nodeset.groups().keys()), ['@all', '@chassis1', '@chassis10', '@chassis11', '@chassis12', '@chassis2', '@chassis3', '@chassis6', '@chassis7', '@chassis8', '@chassis9', '@compute'])
        testns = NodeSet()
        for gnodes, inodes in nodeset.groups().itervalues():
            testns.update(inodes)
        self.assertEqual(testns, nodeset)


class NodeSetRegroupTest(unittest.TestCase):

    def setUp(self):
        """setUp test reproducibility: change standard group resolver
        to ensure that no local group source is used during tests"""
        set_std_group_resolver(GroupResolver()) # dummy resolver

    def tearDown(self):
        """tearDown: restore standard group resolver"""
        set_std_group_resolver(None) # restore std resolver

    def testGroupResolverReverse(self):
        """test NodeSet GroupResolver with reverse upcall"""

        test_groups3 = makeTestG3()
        test_reverse3 = makeTestR3()

        source = GroupSource("test",
                             "sed -n 's/^$GROUP:\(.*\)/\\1/p' %s" % test_groups3.name,
                             "sed -n 's/^all:\(.*\)/\\1/p' %s" % test_groups3.name,
                             "sed -n 's/^\([0-9A-Za-z_-]*\):.*/\\1/p' %s" % test_groups3.name,
                             "awk -F: '/^$NODE:/ { gsub(\",\",\"\\n\",$2); print $2 }' %s" % test_reverse3.name)

        # create custom resolver with default source
        res = GroupResolver(source)

        nodeset = NodeSet("@all", resolver=res)
        self.assertEqual(nodeset, NodeSet("montana[32-55]"))
        self.assertEqual(str(nodeset), "montana[32-55]")
        self.assertEqual(nodeset.regroup(), "@all")
        self.assertEqual(nodeset.regroup(), "@all")

        nodeset = NodeSet("@overclock", resolver=res)
        self.assertEqual(nodeset, NodeSet("montana[41-42]"))
        self.assertEqual(str(nodeset), "montana[41-42]")
        self.assertEqual(nodeset.regroup(), "@overclock")
        self.assertEqual(nodeset.regroup(), "@overclock")

        nodeset = NodeSet("@gpu,@overclock", resolver=res)
        self.assertEqual(str(nodeset), "montana[38-42]")
        self.assertEqual(nodeset, NodeSet("montana[38-42]"))
        # un-overlap :)
        self.assertEqual(nodeset.regroup(), "@gpu,montana42")
        self.assertEqual(nodeset.regroup(), "@gpu,montana42")
        self.assertEqual(nodeset.regroup(overlap=True), "@gpu,@overclock")

        nodeset = NodeSet("montana41", resolver=res)
        self.assertEqual(nodeset.regroup(), "montana41")
        self.assertEqual(nodeset.regroup(), "montana41")

        # test regroup code when using unindexed node
        nodeset = NodeSet("idaho", resolver=res)
        self.assertEqual(nodeset.regroup(), "@single")
        self.assertEqual(nodeset.regroup(), "@single")
        nodeset = NodeSet("@single", resolver=res)
        self.assertEqual(str(nodeset), "idaho")
        # unresolved unindexed:
        nodeset = NodeSet("utah", resolver=res)
        self.assertEqual(nodeset.regroup(), "utah")
        self.assertEqual(nodeset.regroup(), "utah")

        nodeset = NodeSet("@all!montana38", resolver=res)
        self.assertEqual(nodeset, NodeSet("montana[32-37,39-55]"))
        self.assertEqual(str(nodeset), "montana[32-37,39-55]")
        self.assertEqual(nodeset.regroup(), "@para,montana[39-41]")
        self.assertEqual(nodeset.regroup(), "@para,montana[39-41]")
        self.assertEqual(nodeset.regroup(overlap=True),
            "@chassis[1-3],@login,@overclock,@para,montana[39-40]")
        self.assertEqual(nodeset.regroup(overlap=True),
            "@chassis[1-3],@login,@overclock,@para,montana[39-40]")

        nodeset = NodeSet("montana[32-37]", resolver=res)
        self.assertEqual(nodeset.regroup(), "@chassis[1-3]")
        self.assertEqual(nodeset.regroup(), "@chassis[1-3]")

class StaticGroupSource(GroupSource):
    """
    A memory only group source based on a provided dict.
    """

    def __init__(self, name, data):
        all_upcall = None
        if 'all' in data:
            all_upcall = 'fake_all'
        list_upcall = None
        if 'list' in data:
            list_upcall = 'fake_list'
        GroupSource.__init__(self, name, "fake_map", all_upcall, list_upcall)
        self._data = data

    def _upcall_read(self, cmdtpl, args=dict()):
        if cmdtpl == 'map':
            return self._data[cmdtpl].get(args['GROUP'])
        elif cmdtpl == 'reverse':
            return self._data[cmdtpl].get(args['NODE'])
        else:
            return self._data[cmdtpl]

class GroupSourceCacheTest(unittest.TestCase):


    def test_clear_cache(self):
        """test GroupSource.clear_cache()"""
        source = StaticGroupSource('cache', {'map': {'a': 'foo1', 'b': 'foo2'} })

        # create custom resolver with default source
        res = GroupResolver(source)

        # Populate map cache
        self.assertEqual("foo1", str(NodeSet("@a", resolver=res)))
        self.assertEqual("foo2", str(NodeSet("@b", resolver=res)))
        self.assertEqual(len(source._cache['map']), 2)

        # Clear cache
        source.clear_cache()
        self.assertEqual(len(source._cache['map']), 0)

    def test_expired_cache(self):
        """test GroupSource cache entries expired according to config"""
        # create custom resolver with default source
        source = StaticGroupSource('cache', {'map': {'a': 'foo1', 'b': 'foo2'} })
        source.cache_delay = 0.2
        res = GroupResolver(source)

        # Populate map cache
        self.assertEqual("foo1", str(NodeSet("@a", resolver=res)))
        self.assertEqual("foo2", str(NodeSet("@b", resolver=res)))
        self.assertEqual(len(source._cache['map']), 2)

        # Wait for cache expiration
        time.sleep(0.2)

        source._data['map']['a'] = 'something_else'
        self.assertEqual('something_else', str(NodeSet("@a", resolver=res)))

    def test_config_cache_delay(self):
        """test group config cache_delay options"""
        f = make_temp_file("""
[local]
cache_delay: 0.2
map: echo foo1
        """)
        res = GroupResolverConfig(f.name)
        self.assertEqual(res._sources['local'].cache_delay, 0.2)
        self.assertEqual("foo1", str(NodeSet("@local:foo", resolver=res)))

########NEW FILE########
__FILENAME__ = NodeSetTest
#!/usr/bin/env python
# ClusterShell.NodeSet test suite
# Written by S. Thiell 2007-12-05


"""Unit test for NodeSet"""

import binascii
import copy
import pickle
import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.NodeSet import RangeSet, NodeSet, fold, expand
from ClusterShell.NodeSet import NodeSetBase


class NodeSetTest(unittest.TestCase):

    def _assertNode(self, nodeset, nodename):
        self.assertEqual(str(nodeset), nodename)
        self.assertEqual(list(nodeset), [ nodename ])
        self.assertEqual(len(nodeset), 1)

    def testUnnumberedNode(self):
        """test NodeSet with unnumbered node"""
        nodeset = NodeSet("cws-machin")
        self._assertNode(nodeset, "cws-machin")

    def testNodeZero(self):
        """test NodeSet with node0"""
        nodeset = NodeSet("supercluster0")
        self._assertNode(nodeset, "supercluster0")

    def testNoPrefix(self):
        """test NodeSet with node without prefix"""
        nodeset = NodeSet("0cluster")
        self._assertNode(nodeset, "0cluster")
        nodeset = NodeSet("[0]cluster")
        self._assertNode(nodeset, "0cluster")

    def testWhitespacePrefix(self):
        """test NodeSet parsing ignoring whitespace"""
        nodeset = NodeSet(" tigrou2 , tigrou7 , tigrou[5,9-11] ")
        self.assertEqual(str(nodeset), "tigrou[2,5,7,9-11]")
        nodeset = NodeSet("   tigrou2 ,    tigrou5,tigrou7 , tigrou[ 9   - 11 ]    ")
        self.assertEqual(str(nodeset), "tigrou[2,5,7,9-11]")

    def testFromListConstructor(self):
        """test NodeSet.fromlist() constructor"""
        nodeset = NodeSet.fromlist([ "cluster33" ])
        self._assertNode(nodeset, "cluster33")
        nodeset = NodeSet.fromlist([ "cluster0", "cluster1", "cluster2", "cluster5", "cluster8", "cluster4", "cluster3" ])
        self.assertEqual(str(nodeset), "cluster[0-5,8]")
        self.assertEqual(len(nodeset), 7)
        # updaten() test
        nodeset.updaten(["cluster10", "cluster9"])
        self.assertEqual(str(nodeset), "cluster[0-5,8-10]")
        self.assertEqual(len(nodeset), 9)
        # single nodes test
        nodeset = NodeSet.fromlist([ "cluster0", "cluster1", "cluster", "wool", "cluster3" ])
        self.assertEqual(str(nodeset), "cluster,cluster[0-1,3],wool")
        self.assertEqual(len(nodeset), 5)

    def testDigitInPrefix(self):
        """test NodeSet digit in prefix"""
        nodeset = NodeSet("clu-0-3")
        self._assertNode(nodeset, "clu-0-3")
        nodeset = NodeSet("clu-0-[3-23]")
        self.assertEqual(str(nodeset), "clu-0-[3-23]")

    def testNodeWithPercent(self):
        """test NodeSet on nodename with % character"""
        nodeset = NodeSet("cluster%s3")
        self._assertNode(nodeset, "cluster%s3")
        nodeset = NodeSet("clust%ser[3-30]")
        self.assertEqual(str(nodeset), "clust%ser[3-30]")

    def testNodeEightPad(self):
        """test NodeSet padding feature"""
        nodeset = NodeSet("cluster008")
        self._assertNode(nodeset, "cluster008")

    def testNodeRangeIncludingZero(self):
        """test NodeSet with node range including zero"""
        nodeset = NodeSet("cluster[0-10]")
        self.assertEqual(str(nodeset), "cluster[0-10]")
        self.assertEqual(list(nodeset), [ "cluster0", "cluster1", "cluster2", "cluster3", "cluster4", "cluster5", "cluster6", "cluster7", "cluster8", "cluster9", "cluster10" ])
        self.assertEqual(len(nodeset), 11)

    def testSingle(self):
        """test NodeSet single cluster node"""
        nodeset = NodeSet("cluster115")
        self._assertNode(nodeset, "cluster115")

    def testSingleNodeInRange(self):
        """test NodeSet single cluster node in range"""
        nodeset = NodeSet("cluster[115]")
        self._assertNode(nodeset, "cluster115")

    def testRange(self):
        """test NodeSet with simple range"""
        nodeset = NodeSet("cluster[1-100]")
        self.assertEqual(str(nodeset), "cluster[1-100]")
        self.assertEqual(len(nodeset), 100)

        i = 1
        for n in nodeset:
            self.assertEqual(n, "cluster%d" % i)
            i += 1
        self.assertEqual(i, 101)

        lst = copy.deepcopy(list(nodeset))
        i = 1
        for n in lst:
            self.assertEqual(n, "cluster%d" % i)
            i += 1
        self.assertEqual(i, 101)

    def testRangeWithPadding1(self):
        """test NodeSet with range with padding (1)"""
        nodeset = NodeSet("cluster[0001-0100]")
        self.assertEqual(str(nodeset), "cluster[0001-0100]")
        self.assertEqual(len(nodeset), 100)
        i = 1
        for n in nodeset:
            self.assertEqual(n, "cluster%04d" % i)
            i += 1
        self.assertEqual(i, 101)

    def testRangeWithPadding2(self):
        """test NodeSet with range with padding (2)"""
        nodeset = NodeSet("cluster[0034-8127]")
        self.assertEqual(str(nodeset), "cluster[0034-8127]")
        self.assertEqual(len(nodeset), 8094)

        i = 34
        for n in nodeset:
            self.assertEqual(n, "cluster%04d" % i)
            i += 1
        self.assertEqual(i, 8128)

    def testRangeWithSuffix(self):
        """test NodeSet with simple range with suffix"""
        nodeset = NodeSet("cluster[50-99]-ipmi")
        self.assertEqual(str(nodeset), "cluster[50-99]-ipmi")
        i = 50
        for n in nodeset:
            self.assertEqual(n, "cluster%d-ipmi" % i)
            i += 1
        self.assertEqual(i, 100)

    def testCommaSeparatedAndRangeWithPadding(self):
        """test NodeSet comma separated, range and padding"""
        nodeset = NodeSet("cluster[0001,0002,1555-1559]")
        self.assertEqual(str(nodeset), "cluster[0001-0002,1555-1559]")
        self.assertEqual(list(nodeset), [ "cluster0001", "cluster0002", "cluster1555", "cluster1556", "cluster1557", "cluster1558", "cluster1559" ])

    def testCommaSeparatedAndRangeWithPaddingWithSuffix(self):
        """test NodeSet comma separated, range and padding with suffix"""
        nodeset = NodeSet("cluster[0001,0002,1555-1559]-ipmi")
        self.assertEqual(str(nodeset), "cluster[0001-0002,1555-1559]-ipmi")
        self.assertEqual(list(nodeset), [ "cluster0001-ipmi", "cluster0002-ipmi", "cluster1555-ipmi", "cluster1556-ipmi", "cluster1557-ipmi", "cluster1558-ipmi", "cluster1559-ipmi" ])

    def testVeryBigRange(self):
        """test NodeSet iterations with big range size"""
        nodeset = NodeSet("bigcluster[1-1000000]")
        self.assertEqual(str(nodeset), "bigcluster[1-1000000]")
        self.assertEqual(len(nodeset), 1000000)
        i = 1
        for n in nodeset:
            assert n == "bigcluster%d" % i
            i += 1

    def testCommaSeparated(self):
        """test NodeSet comma separated to ranges (folding)"""
        nodeset = NodeSet("cluster115,cluster116,cluster117,cluster130,cluster166")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166]")
        self.assertEqual(len(nodeset), 5)

    def testCommaSeparatedAndRange(self):
        """test NodeSet comma separated and range to ranges (folding)"""
        nodeset = NodeSet("cluster115,cluster116,cluster117,cluster130,cluster[166-169],cluster170")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")

    def testCommaSeparatedAndRanges(self):
        """test NodeSet comma separated and ranges to ranges (folding)"""
        nodeset = NodeSet("cluster[115-117],cluster130,cluster[166-169],cluster170")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")

    def testSimpleStringUpdates(self):
        """test NodeSet simple string-based update()"""
        nodeset = NodeSet("cluster[115-117,130,166-170]")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")
        nodeset.update("cluster171")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-171]")
        nodeset.update("cluster172")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-172]")
        nodeset.update("cluster174")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-172,174]")
        nodeset.update("cluster113")
        self.assertEqual(str(nodeset), "cluster[113,115-117,130,166-172,174]")
        nodeset.update("cluster173")
        self.assertEqual(str(nodeset), "cluster[113,115-117,130,166-174]")
        nodeset.update("cluster114")
        self.assertEqual(str(nodeset), "cluster[113-117,130,166-174]")

    def testSimpleNodeSetUpdates(self):
        """test NodeSet simple nodeset-based update()"""
        nodeset = NodeSet("cluster[115-117,130,166-170]")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")
        nodeset.update(NodeSet("cluster171"))
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-171]")
        nodeset.update(NodeSet("cluster172"))
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-172]")
        nodeset.update(NodeSet("cluster174"))
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-172,174]")
        nodeset.update(NodeSet("cluster113"))
        self.assertEqual(str(nodeset), "cluster[113,115-117,130,166-172,174]")
        nodeset.update(NodeSet("cluster173"))
        self.assertEqual(str(nodeset), "cluster[113,115-117,130,166-174]")
        nodeset.update(NodeSet("cluster114"))
        self.assertEqual(str(nodeset), "cluster[113-117,130,166-174]")

    def testStringUpdatesFromEmptyNodeSet(self):
        """test NodeSet string-based NodeSet.update() from empty nodeset"""
        nodeset = NodeSet()
        self.assertEqual(str(nodeset), "")
        nodeset.update("cluster115")
        self.assertEqual(str(nodeset), "cluster115")
        nodeset.update("cluster118")
        self.assertEqual(str(nodeset), "cluster[115,118]")
        nodeset.update("cluster[116-117]")
        self.assertEqual(str(nodeset), "cluster[115-118]")

    def testNodeSetUpdatesFromEmptyNodeSet(self):
        """test NodeSet-based update() method from empty nodeset"""
        nodeset = NodeSet()
        self.assertEqual(str(nodeset), "")
        nodeset.update(NodeSet("cluster115"))
        self.assertEqual(str(nodeset), "cluster115")
        nodeset.update(NodeSet("cluster118"))
        self.assertEqual(str(nodeset), "cluster[115,118]")
        nodeset.update(NodeSet("cluster[116-117]"))
        self.assertEqual(str(nodeset), "cluster[115-118]")

    def testUpdatesWithSeveralPrefixes(self):
        """test NodeSet.update() using several prefixes"""
        nodeset = NodeSet("cluster3")
        self.assertEqual(str(nodeset), "cluster3")
        nodeset.update("cluster5")
        self.assertEqual(str(nodeset), "cluster[3,5]")
        nodeset.update("tiger5")
        self.assertEqual(str(nodeset), "cluster[3,5],tiger5")
        nodeset.update("tiger7")
        self.assertEqual(str(nodeset), "cluster[3,5],tiger[5,7]")
        nodeset.update("tiger6")
        self.assertEqual(str(nodeset), "cluster[3,5],tiger[5-7]")
        nodeset.update("cluster4")
        self.assertEqual(str(nodeset), "cluster[3-5],tiger[5-7]")

    def testOperatorUnion(self):
        """test NodeSet union | operator"""
        nodeset = NodeSet("cluster[115-117,130,166-170]")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")
        # 1
        n_test1 = nodeset | NodeSet("cluster171")
        self.assertEqual(str(n_test1), "cluster[115-117,130,166-171]")
        nodeset2 = nodeset.copy()
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")
        nodeset2 |= NodeSet("cluster171")
        self.assertEqual(str(nodeset2), "cluster[115-117,130,166-171]")
        # btw validate modifying a copy did not change original
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")
        # 2
        n_test2 = n_test1 | NodeSet("cluster172")
        self.assertEqual(str(n_test2), "cluster[115-117,130,166-172]")
        nodeset2 |= NodeSet("cluster172")
        self.assertEqual(str(nodeset2), "cluster[115-117,130,166-172]")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")
        # 3
        n_test1 = n_test2 | NodeSet("cluster113")
        self.assertEqual(str(n_test1), "cluster[113,115-117,130,166-172]")
        nodeset2 |= NodeSet("cluster113")
        self.assertEqual(str(nodeset2), "cluster[113,115-117,130,166-172]")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")
        # 4
        n_test2 = n_test1 | NodeSet("cluster114")
        self.assertEqual(str(n_test2), "cluster[113-117,130,166-172]")
        nodeset2 |= NodeSet("cluster114")
        self.assertEqual(str(nodeset2), "cluster[113-117,130,166-172]")
        self.assertEqual(nodeset2, NodeSet("cluster[113-117,130,166-172]"))
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")
        # more
        original = NodeSet("cluster0")
        nodeset = original.copy()
        for i in xrange(1, 3000):
            nodeset = nodeset | NodeSet("cluster%d" % i)
        self.assertEqual(len(nodeset), 3000)
        self.assertEqual(str(nodeset), "cluster[0-2999]")
        self.assertEqual(len(original), 1)
        self.assertEqual(str(original), "cluster0")
        nodeset2 = original.copy()
        for i in xrange(1, 3000):
            nodeset2 |= NodeSet("cluster%d" % i)
        self.assertEqual(nodeset, nodeset2)
        for i in xrange(3000, 5000):
            nodeset2 |= NodeSet("cluster%d" % i)
        self.assertEqual(len(nodeset2), 5000)
        self.assertEqual(str(nodeset2), "cluster[0-4999]")
        self.assertEqual(len(nodeset), 3000)
        self.assertEqual(str(nodeset), "cluster[0-2999]")
        self.assertEqual(len(original), 1)
        self.assertEqual(str(original), "cluster0")

    def testOperatorUnionFromEmptyNodeSet(self):
        """test NodeSet union | operator from empty nodeset"""
        nodeset = NodeSet()
        self.assertEqual(str(nodeset), "")
        n_test1 = nodeset | NodeSet("cluster115")
        self.assertEqual(str(n_test1), "cluster115")
        n_test2 = n_test1 | NodeSet("cluster118")
        self.assertEqual(str(n_test2), "cluster[115,118]")
        n_test1 = n_test2 | NodeSet("cluster[116,117]")
        self.assertEqual(str(n_test1), "cluster[115-118]")

    def testOperatorUnionWithSeveralPrefixes(self):
        """test NodeSet union | operator using several prefixes"""
        nodeset = NodeSet("cluster3")
        self.assertEqual(str(nodeset), "cluster3")
        n_test1 = nodeset |  NodeSet("cluster5") 
        self.assertEqual(str(n_test1), "cluster[3,5]")
        n_test2 = n_test1 | NodeSet("tiger5") 
        self.assertEqual(str(n_test2), "cluster[3,5],tiger5")
        n_test1 = n_test2 | NodeSet("tiger7") 
        self.assertEqual(str(n_test1), "cluster[3,5],tiger[5,7]")
        n_test2 = n_test1 | NodeSet("tiger6")
        self.assertEqual(str(n_test2), "cluster[3,5],tiger[5-7]")
        n_test1 = n_test2 | NodeSet("cluster4")
        self.assertEqual(str(n_test1), "cluster[3-5],tiger[5-7]")

    def testOperatorSub(self):
        """test NodeSet difference/sub - operator"""
        nodeset = NodeSet("cluster[115-117,130,166-170]")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")
        # __sub__
        n_test1 = nodeset - NodeSet("cluster[115,130]")
        self.assertEqual(str(n_test1), "cluster[116-117,166-170]")
        nodeset2 = copy.copy(nodeset)
        nodeset2 -= NodeSet("cluster[115,130]")
        self.assertEqual(str(nodeset2), "cluster[116-117,166-170]")
        self.assertEqual(nodeset2, NodeSet("cluster[116-117,166-170]"))

    def testOperatorAnd(self):
        """test NodeSet intersection/and & operator"""
        nodeset = NodeSet("cluster[115-117,130,166-170]")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")
        # __and__
        n_test1 = nodeset & NodeSet("cluster[115-167]")
        self.assertEqual(str(n_test1), "cluster[115-117,130,166-167]")
        nodeset2 = copy.copy(nodeset)
        nodeset2 &= NodeSet("cluster[115-167]")
        self.assertEqual(str(nodeset2), "cluster[115-117,130,166-167]")
        self.assertEqual(nodeset2, NodeSet("cluster[115-117,130,166-167]"))

    def testOperatorXor(self):
        """test NodeSet symmetric_difference/xor & operator"""
        nodeset = NodeSet("cluster[115-117,130,166-170]")
        self.assertEqual(str(nodeset), "cluster[115-117,130,166-170]")
        # __xor__
        n_test1 = nodeset ^ NodeSet("cluster[115-167]")
        self.assertEqual(str(n_test1), "cluster[118-129,131-165,168-170]")
        nodeset2 = copy.copy(nodeset)
        nodeset2 ^= NodeSet("cluster[115-167]")
        self.assertEqual(str(nodeset2), "cluster[118-129,131-165,168-170]")
        self.assertEqual(nodeset2, NodeSet("cluster[118-129,131-165,168-170]"))

    def testLen(self):
        """test NodeSet len() results"""
        nodeset = NodeSet()
        self.assertEqual(len(nodeset), 0)
        nodeset.update("cluster[116-120]")
        self.assertEqual(len(nodeset), 5)
        nodeset = NodeSet("roma[50-99]-ipmi,cors[113,115-117,130,166-172],cws-tigrou,tigrou3")
        self.assertEqual(len(nodeset), 50+12+1+1) 
        nodeset = NodeSet("roma[50-99]-ipmi,cors[113,115-117,130,166-172],cws-tigrou,tigrou3,tigrou3,tigrou3,cors116")
        self.assertEqual(len(nodeset), 50+12+1+1) 

    def testIntersection(self):
        """test NodeSet.intersection()"""
        nsstr = "red[34-55,76-249,300-403],blue,green"
        nodeset = NodeSet(nsstr)
        self.assertEqual(len(nodeset), 302)

        nsstr2 = "red[32-57,72-249,300-341],blue,yellow"
        nodeset2 = NodeSet(nsstr2)
        self.assertEqual(len(nodeset2), 248)

        inodeset = nodeset.intersection(nodeset2)
        # originals should not change
        self.assertEqual(len(nodeset), 302)
        self.assertEqual(len(nodeset2), 248)
        self.assertEqual(str(nodeset), "blue,green,red[34-55,76-249,300-403]")
        self.assertEqual(str(nodeset2), "blue,red[32-57,72-249,300-341],yellow")
        # result
        self.assertEqual(len(inodeset), 239)
        self.assertEqual(str(inodeset), "blue,red[34-55,76-249,300-341]")

    def testIntersectUpdate(self):
        """test NodeSet.intersection_update()"""
        nsstr = "red[34-55,76-249,300-403]"
        nodeset = NodeSet(nsstr)
        self.assertEqual(len(nodeset), 300)

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update("red[78-80]")
        self.assertEqual(str(nodeset), "red[78-80]")

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update("red[54-249]")
        self.assertEqual(str(nodeset), "red[54-55,76-249]")

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update("red[55-249]")
        self.assertEqual(str(nodeset), "red[55,76-249]")

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update("red[55-100]")
        self.assertEqual(str(nodeset), "red[55,76-100]")

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update("red[55-76]")
        self.assertEqual(str(nodeset), "red[55,76]")

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update("red[55,76]")
        self.assertEqual(str(nodeset), "red[55,76]")

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update("red55,red76")
        self.assertEqual(str(nodeset), "red[55,76]")

        # same with intersect(NodeSet)
        nodeset = NodeSet(nsstr)
        nodeset.intersection_update(NodeSet("red[78-80]"))
        self.assertEqual(str(nodeset), "red[78-80]")

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update(NodeSet("red[54-249]"))
        self.assertEqual(str(nodeset), "red[54-55,76-249]")

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update(NodeSet("red[55-249]"))
        self.assertEqual(str(nodeset), "red[55,76-249]")

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update(NodeSet("red[55-100]"))
        self.assertEqual(str(nodeset), "red[55,76-100]")

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update(NodeSet("red[55-76]"))
        self.assertEqual(str(nodeset), "red[55,76]")

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update(NodeSet("red[55,76]"))
        self.assertEqual(str(nodeset), "red[55,76]")

        nodeset = NodeSet(nsstr)
        nodeset.intersection_update(NodeSet("red55,red76"))
        self.assertEqual(str(nodeset), "red[55,76]")

        # single nodes test
        nodeset = NodeSet("red,blue,yellow")
        nodeset.intersection_update("blue,green,yellow")
        self.assertEqual(len(nodeset), 2)
        self.assertEqual(str(nodeset), "blue,yellow")

    def testIntersectSelf(self):
        """test Nodeset.intersection_update(self)"""
        nodeset = NodeSet("red4955")
        self.assertEqual(len(nodeset), 1)
        nodeset.intersection_update(nodeset)
        self.assertEqual(len(nodeset), 1)
        self.assertEqual(str(nodeset), "red4955")

        nodeset = NodeSet("red")
        self.assertEqual(len(nodeset), 1)
        nodeset.intersection_update(nodeset)
        self.assertEqual(len(nodeset), 1)
        self.assertEqual(str(nodeset), "red")

        nodeset = NodeSet("red")
        self.assertEqual(len(nodeset), 1)
        nodeset.intersection_update("red")
        self.assertEqual(len(nodeset), 1)
        self.assertEqual(str(nodeset), "red")

        nodeset = NodeSet("red")
        self.assertEqual(len(nodeset), 1)
        nodeset.intersection_update("blue")
        self.assertEqual(len(nodeset), 0)

        nodeset = NodeSet("red[78-149]")
        self.assertEqual(len(nodeset), 72)
        nodeset.intersection_update(nodeset)
        self.assertEqual(len(nodeset), 72)
        self.assertEqual(str(nodeset), "red[78-149]")

    def testIntersectReturnNothing(self):
        """test NodeSet intersect that returns empty NodeSet"""
        nodeset = NodeSet("blue43")
        self.assertEqual(len(nodeset), 1)
        nodeset.intersection_update("blue42")
        self.assertEqual(len(nodeset), 0)

    def testDifference(self):
        """test NodeSet.difference()"""
        nsstr = "red[34-55,76-249,300-403],blue,green"
        nodeset = NodeSet(nsstr)
        self.assertEqual(str(nodeset), "blue,green,red[34-55,76-249,300-403]")
        self.assertEqual(len(nodeset), 302)

        nsstr2 = "red[32-57,72-249,300-341],blue,yellow"
        nodeset2 = NodeSet(nsstr2)
        self.assertEqual(str(nodeset2), "blue,red[32-57,72-249,300-341],yellow")
        self.assertEqual(len(nodeset2), 248)

        inodeset = nodeset.difference(nodeset2)
        # originals should not change
        self.assertEqual(str(nodeset), "blue,green,red[34-55,76-249,300-403]")
        self.assertEqual(str(nodeset2), "blue,red[32-57,72-249,300-341],yellow")
        self.assertEqual(len(nodeset), 302)
        self.assertEqual(len(nodeset2), 248)
        # result
        self.assertEqual(str(inodeset), "green,red[342-403]")
        self.assertEqual(len(inodeset), 63)

    def testDifferenceUpdate(self):
        """test NodeSet.difference_update()"""
        # nodeset-based subs
        nodeset = NodeSet("yellow120")
        self.assertEqual(len(nodeset), 1)
        nodeset.difference_update(NodeSet("yellow120"))
        self.assertEqual(len(nodeset), 0)

        nodeset = NodeSet("yellow")
        self.assertEqual(len(nodeset), 1)
        nodeset.difference_update(NodeSet("yellow"))
        self.assertEqual(len(nodeset), 0)

        nodeset = NodeSet("yellow")
        self.assertEqual(len(nodeset), 1)
        nodeset.difference_update(NodeSet("blue"))
        self.assertEqual(len(nodeset), 1)
        self.assertEqual(str(nodeset), "yellow")

        nodeset = NodeSet("yellow[45-240,570-764,800]")
        self.assertEqual(len(nodeset), 392)
        nodeset.difference_update(NodeSet("yellow[45-240,570-764,800]"))
        self.assertEqual(len(nodeset), 0)

        # same with string-based subs
        nodeset = NodeSet("yellow120")
        self.assertEqual(len(nodeset), 1)
        nodeset.difference_update("yellow120")
        self.assertEqual(len(nodeset), 0)

        nodeset = NodeSet("yellow")
        self.assertEqual(len(nodeset), 1)
        nodeset.difference_update("yellow")
        self.assertEqual(len(nodeset), 0)

        nodeset = NodeSet("yellow")
        self.assertEqual(len(nodeset), 1)
        nodeset.difference_update("blue")
        self.assertEqual(len(nodeset), 1)
        self.assertEqual(str(nodeset), "yellow")

        nodeset = NodeSet("yellow[45-240,570-764,800]")
        self.assertEqual(len(nodeset), 392)
        nodeset.difference_update("yellow[45-240,570-764,800]")
        self.assertEqual(len(nodeset), 0)

    def testSubSelf(self):
        """test NodeSet.difference_update() method (self)"""
        nodeset = NodeSet("yellow[120-148,167]")
        nodeset.difference_update(nodeset)
        self.assertEqual(len(nodeset), 0)

    def testSubMore(self):
        """test NodeSet.difference_update() method (more)"""
        nodeset = NodeSet("yellow[120-160]")
        self.assertEqual(len(nodeset), 41)
        for i in range(120, 161):
            nodeset.difference_update(NodeSet("yellow%d" % i))
        self.assertEqual(len(nodeset), 0)

    def testSubsAndAdds(self):
        """test NodeSet.update() and difference_update() together"""
        nodeset = NodeSet("yellow[120-160]")
        self.assertEqual(len(nodeset), 41)
        for i in range(120, 131):
            nodeset.difference_update(NodeSet("yellow%d" % i))
        self.assertEqual(len(nodeset), 30)
        for i in range(1940, 2040):
            nodeset.update(NodeSet("yellow%d" % i))
        self.assertEqual(len(nodeset), 130)

    def testSubsAndAddsMore(self):
        """test NodeSet.update() and difference_update() together (more)"""
        nodeset = NodeSet("yellow[120-160]")
        self.assertEqual(len(nodeset), 41)
        for i in range(120, 131):
            nodeset.difference_update(NodeSet("yellow%d" % i))
            nodeset.update(NodeSet("yellow%d" % (i + 1000)))
        self.assertEqual(len(nodeset), 41)
        for i in range(1120, 1131):
            nodeset.difference_update(NodeSet("yellow%d" % i))
        nodeset.difference_update(NodeSet("yellow[131-160]"))
        self.assertEqual(len(nodeset), 0)

    def testSubsAndAddsMoreDigit(self):
        """test NodeSet.update() and difference_update() together (with other digit in prefix)"""
        nodeset = NodeSet("clu-3-[120-160]")
        self.assertEqual(len(nodeset), 41)
        for i in range(120, 131):
            nodeset.difference_update(NodeSet("clu-3-[%d]" % i))
            nodeset.update(NodeSet("clu-3-[%d]" % (i + 1000)))
        self.assertEqual(len(nodeset), 41)
        for i in range(1120, 1131):
            nodeset.difference_update(NodeSet("clu-3-[%d]" % i))
        nodeset.difference_update(NodeSet("clu-3-[131-160]"))
        self.assertEqual(len(nodeset), 0)

    def testSubUnknownNodes(self):
        """test NodeSet.difference_update() with unknown nodes"""
        nodeset = NodeSet("yellow[120-160]")
        self.assertEqual(len(nodeset), 41)
        nodeset.difference_update("red[35-49]")
        self.assertEqual(len(nodeset), 41)
        self.assertEqual(str(nodeset), "yellow[120-160]")

    def testSubMultiplePrefix(self):
        """test NodeSet.difference_update() with multiple prefixes"""
        nodeset = NodeSet("yellow[120-160],red[32-147],blue3,green,white[2-3940],blue4,blue303")
        self.assertEqual(len(nodeset), 4100)
        for i in range(120, 131):
            nodeset.difference_update(NodeSet("red%d" % i))
            nodeset.update(NodeSet("red%d" % (i + 1000)))
            nodeset.update(NodeSet("yellow%d" % (i + 1000)))
        self.assertEqual(len(nodeset), 4111)
        for i in range(1120, 1131):
            nodeset.difference_update(NodeSet("red%d" % i))
            nodeset.difference_update(NodeSet("white%d" %i))
        nodeset.difference_update(NodeSet("yellow[131-160]"))
        self.assertEqual(len(nodeset), 4059)
        nodeset.difference_update(NodeSet("green"))
        self.assertEqual(len(nodeset), 4058)

    def test_getitem(self):
        """test NodeSet.__getitem__()"""
        nodeset = NodeSet("yeti[30,34-51,59-60]")
        self.assertEqual(len(nodeset), 21)
        self.assertEqual(nodeset[0], "yeti30")
        self.assertEqual(nodeset[1], "yeti34")
        self.assertEqual(nodeset[2], "yeti35")
        self.assertEqual(nodeset[3], "yeti36")
        self.assertEqual(nodeset[18], "yeti51")
        self.assertEqual(nodeset[19], "yeti59")
        self.assertEqual(nodeset[20], "yeti60")
        self.assertRaises(IndexError, nodeset.__getitem__, 21)
        # negative indices
        self.assertEqual(nodeset[-1], "yeti60")
        for n in range(1, len(nodeset)):
            self.assertEqual(nodeset[-n], nodeset[len(nodeset)-n])
        self.assertRaises(IndexError, nodeset.__getitem__, -100)

        # test getitem with some nodes without range
        nodeset = NodeSet("abc,cde[3-9,11],fgh")
        self.assertEqual(len(nodeset), 10)
        self.assertEqual(nodeset[0], "abc")
        self.assertEqual(nodeset[1], "cde3")
        self.assertEqual(nodeset[2], "cde4")
        self.assertEqual(nodeset[3], "cde5")
        self.assertEqual(nodeset[7], "cde9")
        self.assertEqual(nodeset[8], "cde11")
        self.assertEqual(nodeset[9], "fgh")
        self.assertRaises(IndexError, nodeset.__getitem__, 10)
        # test getitem with rangeset padding
        nodeset = NodeSet("prune[003-034,349-353/2]")
        self.assertEqual(len(nodeset), 35)
        self.assertEqual(nodeset[0], "prune003")
        self.assertEqual(nodeset[1], "prune004")
        self.assertEqual(nodeset[31], "prune034")
        self.assertEqual(nodeset[32], "prune349")
        self.assertEqual(nodeset[33], "prune351")
        self.assertEqual(nodeset[34], "prune353")
        self.assertRaises(IndexError, nodeset.__getitem__, 35)

    def test_getslice(self):
        """test NodeSet getitem() with slice"""
        nodeset = NodeSet("yeti[30,34-51,59-60]")
        self.assertEqual(len(nodeset), 21)
        self.assertEqual(len(nodeset[0:2]), 2)
        self.assertEqual(str(nodeset[0:2]), "yeti[30,34]")
        self.assertEqual(len(nodeset[1:3]), 2)
        self.assertEqual(str(nodeset[1:3]), "yeti[34-35]")
        self.assertEqual(len(nodeset[19:21]), 2)
        self.assertEqual(str(nodeset[19:21]), "yeti[59-60]")
        self.assertEqual(len(nodeset[20:22]), 1)
        self.assertEqual(str(nodeset[20:22]), "yeti60")
        self.assertEqual(len(nodeset[21:24]), 0)
        self.assertEqual(str(nodeset[21:24]), "")
        # negative indices
        self.assertEqual(str(nodeset[:-1]), "yeti[30,34-51,59]")
        self.assertEqual(str(nodeset[:-2]), "yeti[30,34-51]")
        self.assertEqual(str(nodeset[1:-2]), "yeti[34-51]")
        self.assertEqual(str(nodeset[2:-2]), "yeti[35-51]")
        self.assertEqual(str(nodeset[9:-3]), "yeti[42-50]")
        self.assertEqual(str(nodeset[10:-9]), "yeti[43-44]")
        self.assertEqual(str(nodeset[10:-10]), "yeti43")
        self.assertEqual(str(nodeset[11:-10]), "")
        self.assertEqual(str(nodeset[11:-11]), "")
        self.assertEqual(str(nodeset[::-2]), "yeti[30,35,37,39,41,43,45,47,49,51,60]")
        self.assertEqual(str(nodeset[::-3]), "yeti[35,38,41,44,47,50,60]")
        # advanced
        self.assertEqual(str(nodeset[0:10:2]), "yeti[30,35,37,39,41]")
        self.assertEqual(str(nodeset[1:11:2]), "yeti[34,36,38,40,42]")
        self.assertEqual(str(nodeset[:11:3]), "yeti[30,36,39,42]")
        self.assertEqual(str(nodeset[11::4]), "yeti[44,48,59]")
        self.assertEqual(str(nodeset[14:]), "yeti[47-51,59-60]")
        self.assertEqual(str(nodeset[:]), "yeti[30,34-51,59-60]")
        self.assertEqual(str(nodeset[::5]), "yeti[30,38,43,48,60]")
        # with unindexed nodes
        nodeset = NodeSet("foo,bar,bur")
        self.assertEqual(len(nodeset), 3)
        self.assertEqual(len(nodeset[0:2]), 2)
        self.assertEqual(str(nodeset[0:2]), "bar,bur")
        self.assertEqual(str(nodeset[1:2]), "bur")
        self.assertEqual(str(nodeset[1:3]), "bur,foo")
        self.assertEqual(str(nodeset[2:4]), "foo")
        nodeset = NodeSet("foo,bar,bur3,bur1")
        self.assertEqual(len(nodeset), 4)
        self.assertEqual(len(nodeset[0:2]), 2)
        self.assertEqual(len(nodeset[1:3]), 2)
        self.assertEqual(len(nodeset[2:4]), 2)
        self.assertEqual(len(nodeset[3:5]), 1)
        self.assertEqual(str(nodeset[2:3]), "bur3")
        self.assertEqual(str(nodeset[3:4]), "foo")
        self.assertEqual(str(nodeset[0:2]), "bar,bur1")
        self.assertEqual(str(nodeset[1:3]), "bur[1,3]")
        # using range step
        nodeset = NodeSet("yeti[10-98/2]")
        self.assertEqual(str(nodeset[1:9:3]), "yeti[12,18,24]")
        self.assertEqual(str(nodeset[::17]), "yeti[10,44,78]")
        nodeset = NodeSet("yeti[10-98/2]", autostep=2)
        self.assertEqual(str(nodeset[22:29]), "yeti[54-66/2]")
        self.assertEqual(nodeset._autostep, 2)
        # stepping scalability
        nodeset = NodeSet("yeti[10-9800/2]", autostep=2)
        self.assertEqual(str(nodeset[22:2900]), "yeti[54-5808/2]")
        self.assertEqual(str(nodeset[22:2900:3]), "yeti[54-5808/6]")
        nodeset = NodeSet("yeti[10-14,20-26,30-33]")
        self.assertEqual(str(nodeset[2:6]), "yeti[12-14,20]")
        # multiple patterns
        nodeset = NodeSet("stone[1-9],wood[1-9]")
        self.assertEqual(str(nodeset[:]), "stone[1-9],wood[1-9]")
        self.assertEqual(str(nodeset[1:2]), "stone2")
        self.assertEqual(str(nodeset[8:9]), "stone9")
        self.assertEqual(str(nodeset[8:10]), "stone9,wood1")
        self.assertEqual(str(nodeset[9:10]), "wood1")
        self.assertEqual(str(nodeset[9:]), "wood[1-9]")
        nodeset = NodeSet("stone[1-9],water[10-12],wood[1-9]")
        self.assertEqual(str(nodeset[8:10]), "stone9,water10")
        self.assertEqual(str(nodeset[11:15]), "water12,wood[1-3]")
        nodeset = NodeSet("stone[1-9],water,wood[1-9]")
        self.assertEqual(str(nodeset[8:10]), "stone9,water")
        self.assertEqual(str(nodeset[8:11]), "stone9,water,wood1")
        self.assertEqual(str(nodeset[9:11]), "water,wood1")
        self.assertEqual(str(nodeset[9:12]), "water,wood[1-2]")

    def testSplit(self):
        """test NodeSet split()"""
        # Empty nodeset
        nodeset = NodeSet()
        self.assertEqual((), tuple(nodeset.split(2)))
        # Not enough element
        nodeset = NodeSet("foo[1]")
        self.assertEqual((NodeSet("foo[1]"),), \
                         tuple(nodeset.split(2)))
        # Exact number of elements
        nodeset = NodeSet("foo[1-6]")
        self.assertEqual((NodeSet("foo[1-2]"), NodeSet("foo[3-4]"), \
                         NodeSet("foo[5-6]")), tuple(nodeset.split(3)))
        # Check limit results
        nodeset = NodeSet("bar[2-4]")
        for i in (3, 4):
            self.assertEqual((NodeSet("bar2"), NodeSet("bar3"), \
                             NodeSet("bar4")), tuple(nodeset.split(i)))
        

    def testAdd(self):
        """test NodeSet add()"""
        nodeset = NodeSet()
        nodeset.add("green")
        self.assertEqual(len(nodeset), 1)
        self.assertEqual(str(nodeset), "green")
        self.assertEqual(nodeset[0], "green")
        nodeset = NodeSet()
        nodeset.add("green35")
        self.assertEqual(len(nodeset), 1)
        self.assertEqual(str(nodeset), "green35")
        self.assertEqual(nodeset[0], "green35")
        nodeset = NodeSet()
        nodeset.add("green[3,5-46]")
        self.assertEqual(len(nodeset), 43)
        self.assertEqual(nodeset[0], "green3")
        nodeset = NodeSet()
        nodeset.add("green[3,5-46],black64,orange[045-148]")
        self.assertEqual(len(nodeset), 148)
        self.assert_("green5" in nodeset)
        self.assert_("black64" in nodeset)
        self.assert_("orange046" in nodeset)

    def testAddAdjust(self):
        """test NodeSet adjusting add()"""
        # autostep OFF
        nodeset = NodeSet()
        nodeset.add("green[1-8/2]")
        self.assertEqual(str(nodeset), "green[1,3,5,7]")
        self.assertEqual(len(nodeset), 4)
        nodeset.add("green[6-17/2]")
        self.assertEqual(str(nodeset), "green[1,3,5-8,10,12,14,16]")
        self.assertEqual(len(nodeset), 10)
        # autostep ON
        nodeset = NodeSet(autostep=2)
        nodeset.add("green[1-8/2]")
        self.assertEqual(str(nodeset), "green[1-7/2]")
        self.assertEqual(len(nodeset), 4)
        nodeset.add("green[6-17/2]")
        self.assertEqual(str(nodeset), "green[1-5/2,6-7,8-16/2]")
        self.assertEqual(len(nodeset), 10)

    def testRemove(self):
        """test NodeSet remove()"""
        # from empty nodeset
        nodeset = NodeSet()
        self.assertEqual(len(nodeset), 0)
        self.assertRaises(KeyError, nodeset.remove, "tintin23")
        self.assertRaises(KeyError, nodeset.remove, "tintin[35-36]")
        nodeset.update("milou36")
        self.assertEqual(len(nodeset), 1)
        self.assertRaises(KeyError, nodeset.remove, "tintin23")
        self.assert_("milou36" in nodeset)
        nodeset.remove("milou36")
        self.assertEqual(len(nodeset), 0)
        nodeset.update("milou[36-60,76,95],haddock[1-12],tournesol")
        self.assertEqual(len(nodeset), 40)
        nodeset.remove("milou76")
        self.assertEqual(len(nodeset), 39)
        nodeset.remove("milou[36-39]")
        self.assertEqual(len(nodeset), 35)
        self.assertRaises(KeyError, nodeset.remove, "haddock13")
        self.assertEqual(len(nodeset), 35)
        self.assertRaises(KeyError, nodeset.remove, "haddock[1-15]")
        self.assertEqual(len(nodeset), 35)
        self.assertRaises(KeyError, nodeset.remove, "tutu")
        self.assertEqual(len(nodeset), 35)
        nodeset.remove("tournesol")
        self.assertEqual(len(nodeset), 34)
        nodeset.remove("haddock[1-12]")
        self.assertEqual(len(nodeset), 22)
        nodeset.remove("milou[40-60,95]")
        self.assertEqual(len(nodeset), 0)
        self.assertRaises(KeyError, nodeset.remove, "tournesol")
        self.assertRaises(KeyError, nodeset.remove, "milou40")
        # from non-empty nodeset
        nodeset = NodeSet("haddock[16-3045]")
        self.assertEqual(len(nodeset), 3030)
        self.assertRaises(KeyError, nodeset.remove, "haddock15")
        self.assert_("haddock16" in nodeset)
        self.assertEqual(len(nodeset), 3030)
        nodeset.remove("haddock[16,18-3044]")
        self.assertEqual(len(nodeset), 2)
        self.assertRaises(KeyError, nodeset.remove, "haddock3046")
        self.assertRaises(KeyError, nodeset.remove, "haddock[16,3060]")
        self.assertRaises(KeyError, nodeset.remove, "haddock[3045-3046]")
        self.assertRaises(KeyError, nodeset.remove, "haddock[3045,3049-3051/2]")
        nodeset.remove("haddock3045")
        self.assertEqual(len(nodeset), 1)
        self.assertRaises(KeyError, nodeset.remove, "haddock[3045]")
        self.assertEqual(len(nodeset), 1)
        nodeset.remove("haddock17")
        self.assertEqual(len(nodeset), 0)

    def testClear(self):
        """test NodeSet clear()"""
        nodeset = NodeSet("purple[35-39]")
        self.assertEqual(len(nodeset), 5)
        nodeset.clear()
        self.assertEqual(len(nodeset), 0)

    def test_contains(self):
        """test NodeSet contains()"""
        nodeset = NodeSet()
        self.assertEqual(len(nodeset), 0)
        self.assertTrue("foo" not in nodeset)
        nodeset.update("bar")
        self.assertEqual(len(nodeset), 1)
        self.assertEqual(str(nodeset), "bar")
        self.assertTrue("bar" in nodeset)
        nodeset.update("foo[20-40]")
        self.assertTrue("foo" not in nodeset)
        self.assertTrue("foo39" in nodeset)
        for node in nodeset:
            self.assertTrue(node in nodeset)
        nodeset.update("dark[2000-4000/4]")
        self.assertTrue("dark3000" in nodeset)
        self.assertTrue("dark3002" not in nodeset)
        for node in nodeset:
            self.assertTrue(node in nodeset)
        nodeset = NodeSet("scale[0-10000]")
        self.assertTrue("black64" not in nodeset)
        self.assertTrue("scale9346" in nodeset)
        nodeset = NodeSet("scale[0-10000]", autostep=2)
        self.assertTrue("scale9346" in nodeset[::2])
        self.assertTrue("scale9347" not in nodeset[::2])
        # nD
        nodeset = NodeSet("scale[0-1000]p[1,3]")
        self.assertTrue("black300p2" not in nodeset)
        self.assertTrue("scale333p3" in nodeset)
        self.assertTrue("scale333p1" in nodeset)
        nodeset = NodeSet("scale[0-1000]p[1,3]", autostep=2)
        self.assertEqual(str(nodeset), "scale[0-1000]p[1-3/2]")
        nhalf = nodeset[::2]
        self.assertEqual(str(nhalf), "scale[0-1000]p1")
        self.assertTrue("scale242p1" in nhalf)
        self.assertTrue("scale346p1" in nhalf)

    def testContainsUsingPadding(self):
        """test NodeSet contains() when using padding"""
        nodeset = NodeSet("white[001,030]")
        nodeset.add("white113")
        self.assertTrue(NodeSet("white30") in nodeset)
        self.assertTrue(NodeSet("white030") in nodeset)
        # case: nodeset without padding info is compared to a
        # padding-initialized range
        self.assert_(NodeSet("white113") in nodeset)
        self.assert_(NodeSet("white[001,113]") in nodeset)
        self.assert_(NodeSet("gene0113") in NodeSet("gene[001,030,113]"))
        self.assert_(NodeSet("gene0113") in NodeSet("gene[0001,0030,0113]"))
        self.assert_(NodeSet("gene0113") in NodeSet("gene[098-113]"))
        self.assert_(NodeSet("gene0113") in NodeSet("gene[0098-0113]"))
        # case: len(str(ielem)) >= rgpad
        nodeset = NodeSet("white[001,099]")
        nodeset.add("white100")
        nodeset.add("white1000")
        self.assert_(NodeSet("white1000") in nodeset)

    def test_issuperset(self):
        """test NodeSet issuperset()"""
        nodeset = NodeSet("tronic[0036-1630]")
        self.assertEqual(len(nodeset), 1595)
        self.assert_(nodeset.issuperset("tronic[0036-1630]"))
        self.assert_(nodeset.issuperset("tronic[0140-0200]"))
        self.assert_(nodeset.issuperset(NodeSet("tronic[0140-0200]")))
        self.assert_(nodeset.issuperset("tronic0070"))
        self.assert_(not nodeset.issuperset("tronic0034"))
        # check padding issue - since 1.6 padding is ignored in this case
        self.assert_(nodeset.issuperset("tronic36"))
        self.assert_(nodeset.issuperset("tronic[36-40]"))
        self.assert_(nodeset.issuperset(NodeSet("tronic[36-40]")))
        # check gt
        self.assert_(nodeset > NodeSet("tronic[0100-0200]"))
        self.assert_(not nodeset > NodeSet("tronic[0036-1630]"))
        self.assert_(not nodeset > NodeSet("tronic[0036-1631]"))
        self.assert_(nodeset >= NodeSet("tronic[0100-0200]"))
        self.assert_(nodeset >= NodeSet("tronic[0036-1630]"))
        self.assert_(not nodeset >= NodeSet("tronic[0036-1631]"))
        # multiple patterns case
        nodeset = NodeSet("tronic[0036-1630],lounge[20-660/2]")
        self.assert_(nodeset > NodeSet("tronic[0100-0200]"))
        self.assert_(nodeset > NodeSet("lounge[36-400/2]"))
        self.assert_(nodeset.issuperset(NodeSet("lounge[36-400/2],tronic[0100-660]")))
        self.assert_(nodeset > NodeSet("lounge[36-400/2],tronic[0100-660]"))

    def test_issubset(self):
        """test NodeSet issubset()"""
        nodeset = NodeSet("artcore[3-999]")
        self.assertEqual(len(nodeset), 997)
        self.assert_(nodeset.issubset("artcore[3-999]"))
        self.assert_(nodeset.issubset("artcore[1-1000]"))
        self.assert_(not nodeset.issubset("artcore[350-427]"))
        # check lt
        self.assert_(nodeset < NodeSet("artcore[2-32000]"))
        self.assert_(nodeset < NodeSet("artcore[2-32000],lounge[35-65/2]"))
        self.assert_(not nodeset < NodeSet("artcore[3-999]"))
        self.assert_(not nodeset < NodeSet("artcore[3-980]"))
        self.assert_(not nodeset < NodeSet("artcore[2-998]"))
        self.assert_(nodeset <= NodeSet("artcore[2-32000]"))
        self.assert_(nodeset <= NodeSet("artcore[2-32000],lounge[35-65/2]"))
        self.assert_(nodeset <= NodeSet("artcore[3-999]"))
        self.assert_(not nodeset <= NodeSet("artcore[3-980]"))
        self.assert_(not nodeset <= NodeSet("artcore[2-998]"))
        self.assertEqual(len(nodeset), 997)
        # check padding issue - since 1.6 padding is ignored in this case
        self.assert_(nodeset.issubset("artcore[0001-1000]"))
        self.assert_(not nodeset.issubset("artcore030"))
        # multiple patterns case
        nodeset = NodeSet("tronic[0036-1630],lounge[20-660/2]")
        self.assert_(nodeset < NodeSet("tronic[0036-1630],lounge[20-662/2]"))
        self.assert_(nodeset < NodeSet("tronic[0035-1630],lounge[20-660/2]"))
        self.assert_(not nodeset < NodeSet("tronic[0035-1630],lounge[22-660/2]"))
        self.assert_(nodeset < NodeSet("tronic[0036-1630],lounge[20-660/2],artcore[034-070]"))
        self.assert_(nodeset < NodeSet("tronic[0032-1880],lounge[2-700/2],artcore[039-040]"))
        self.assert_(nodeset.issubset("tronic[0032-1880],lounge[2-700/2],artcore[039-040]"))
        self.assert_(nodeset.issubset(NodeSet("tronic[0032-1880],lounge[2-700/2],artcore[039-040]")))

    def testSymmetricDifference(self):
        """test NodeSet symmetric_difference()"""
        nsstr = "red[34-55,76-249,300-403],blue,green"
        nodeset = NodeSet(nsstr)
        self.assertEqual(len(nodeset), 302)

        nsstr2 = "red[32-57,72-249,300-341],blue,yellow"
        nodeset2 = NodeSet(nsstr2)
        self.assertEqual(len(nodeset2), 248)

        inodeset = nodeset.symmetric_difference(nodeset2)
        # originals should not change
        self.assertEqual(len(nodeset), 302)
        self.assertEqual(len(nodeset2), 248)
        self.assertEqual(str(nodeset), "blue,green,red[34-55,76-249,300-403]")
        self.assertEqual(str(nodeset2), "blue,red[32-57,72-249,300-341],yellow")
        # result
        self.assertEqual(len(inodeset), 72)
        self.assertEqual(str(inodeset), \
            "green,red[32-33,56-57,72-75,342-403],yellow")

    def testSymmetricDifferenceUpdate(self):
        """test NodeSet symmetric_difference_update()"""
        nodeset = NodeSet("artcore[3-999]")
        self.assertEqual(len(nodeset), 997)
        nodeset.symmetric_difference_update("artcore[1-2000]")
        self.assertEqual(len(nodeset), 1003)
        self.assertEqual(str(nodeset), "artcore[1-2,1000-2000]")
        nodeset = NodeSet("artcore[3-999],lounge")
        self.assertEqual(len(nodeset), 998)
        nodeset.symmetric_difference_update("artcore[1-2000]")
        self.assertEqual(len(nodeset), 1004)
        self.assertEqual(str(nodeset), "artcore[1-2,1000-2000],lounge")
        nodeset = NodeSet("artcore[3-999],lounge")
        self.assertEqual(len(nodeset), 998)
        nodeset.symmetric_difference_update("artcore[1-2000],lounge")
        self.assertEqual(len(nodeset), 1003)
        self.assertEqual(str(nodeset), "artcore[1-2,1000-2000]")
        nodeset = NodeSet("artcore[3-999],lounge")
        self.assertEqual(len(nodeset), 998)
        nodeset2 = NodeSet("artcore[1-2000],lounge")
        nodeset.symmetric_difference_update(nodeset2)
        self.assertEqual(len(nodeset), 1003)
        self.assertEqual(str(nodeset), "artcore[1-2,1000-2000]")
        self.assertEqual(len(nodeset2), 2001) # check const argument
        nodeset.symmetric_difference_update("artcore[1-2000],lounge")
        self.assertEqual(len(nodeset), 998)
        self.assertEqual(str(nodeset), "artcore[3-999],lounge")

    def testOperatorSymmetricDifference(self):
        """test NodeSet symmetric_difference() and ^ operator"""
        nodeset = NodeSet("artcore[3-999]")
        self.assertEqual(len(nodeset), 997)
        result = nodeset.symmetric_difference("artcore[1-2000]")
        self.assertEqual(len(result), 1003)
        self.assertEqual(str(result), "artcore[1-2,1000-2000]")
        self.assertEqual(len(nodeset), 997)

        # test ^ operator
        nodeset = NodeSet("artcore[3-999]")
        self.assertEqual(len(nodeset), 997)
        nodeset2 = NodeSet("artcore[1-2000]")
        result = nodeset ^ nodeset2
        self.assertEqual(len(result), 1003)
        self.assertEqual(str(result), "artcore[1-2,1000-2000]")
        self.assertEqual(len(nodeset), 997)
        self.assertEqual(len(nodeset2), 2000)

        # check that n ^ n returns empty NodeSet
        nodeset = NodeSet("lounge[3-999]")
        self.assertEqual(len(nodeset), 997)
        result = nodeset ^ nodeset
        self.assertEqual(len(result), 0)

    def testBinarySanityCheck(self):
        """test NodeSet binary sanity check"""
        ns1 = NodeSet("1-5")
        ns2 = "4-6"
        self.assertRaises(TypeError, ns1.__gt__, ns2)
        self.assertRaises(TypeError, ns1.__lt__, ns2)

    def testBinarySanityCheckNotImplementedSubtle(self):
        """test NodeSet binary sanity check (NotImplemented subtle)"""
        ns1 = NodeSet("1-5")
        ns2 = "4-6"
        self.assertEqual(ns1.__and__(ns2), NotImplemented)
        self.assertEqual(ns1.__or__(ns2), NotImplemented)
        self.assertEqual(ns1.__sub__(ns2), NotImplemented)
        self.assertEqual(ns1.__xor__(ns2), NotImplemented)
        # Should implicitely raises TypeError if the real operator
        # version is invoked. To test that, we perform a manual check
        # as an additional function would be needed to check with
        # assertRaises():
        good_error = False
        try:
            ns3 = ns1 & ns2
        except TypeError:
            good_error = True
        self.assert_(good_error, "TypeError not raised for &")
        good_error = False
        try:
            ns3 = ns1 | ns2
        except TypeError:
            good_error = True
        self.assert_(good_error, "TypeError not raised for |")
        good_error = False
        try:
            ns3 = ns1 - ns2
        except TypeError:
            good_error = True
        self.assert_(good_error, "TypeError not raised for -")
        good_error = False
        try:
            ns3 = ns1 ^ ns2
        except TypeError:
            good_error = True
        self.assert_(good_error, "TypeError not raised for ^")

    def testIsSubSetError(self):
        """test NodeSet issubset type error"""
        ns1 = NodeSet("1-5")
        ns2 = 4
        self.assertRaises(TypeError, ns1.issubset, ns2)

    def testExpandFunction(self):
        """test NodeSet expand() utility function"""
        self.assertEqual(expand("purple[1-3]"), [ "purple1", "purple2", "purple3" ])

    def testFoldFunction(self):
        """test NodeSet fold() utility function"""
        self.assertEqual(fold("purple1,purple2,purple3"), "purple[1-3]")

    def testEquality(self):
        """test NodeSet equality"""
        ns0_1 = NodeSet()
        ns0_2 = NodeSet()
        self.assertEqual(ns0_1, ns0_2)
        ns1 = NodeSet("roma[50-99]-ipmi,cors[113,115-117,130,166-172],cws-tigrou,tigrou3")
        ns2 = NodeSet("roma[50-99]-ipmi,cors[113,115-117,130,166-172],cws-tigrou,tigrou3")
        self.assertEqual(ns1, ns2)
        ns3 = NodeSet("cws-tigrou,tigrou3,cors[113,115-117,166-172],roma[50-99]-ipmi,cors130")
        self.assertEqual(ns1, ns3)
        ns4 = NodeSet("roma[50-99]-ipmi,cors[113,115-117,130,166-171],cws-tigrou,tigrou[3-4]")
        self.assertNotEqual(ns1, ns4)

    def testIterOrder(self):
        """test NodeSet nodes name order in iter and str"""
        ns_b = NodeSet("bcluster25")
        ns_c = NodeSet("ccluster12")
        ns_a1 = NodeSet("acluster4")
        ns_a2 = NodeSet("acluster39")
        ns_a3 = NodeSet("acluster41")
        ns = ns_c | ns_a1 | ns_b | ns_a2 | ns_a3
        self.assertEqual(str(ns), "acluster[4,39,41],bcluster25,ccluster12")
        nodelist = list(iter(ns))
        self.assertEqual(nodelist, ['acluster4', 'acluster39', 'acluster41', \
            'bcluster25', 'ccluster12'])

    def test_nsiter(self):
        """test NodeSet.nsiter() iterator"""
        ns1 = NodeSet("roma[50-61]-ipmi,cors[113,115-117,130,166-169],cws-tigrou,tigrou3")
        self.assertEqual(list(ns1), ['cors113', 'cors115', 'cors116', 'cors117', 'cors130', 'cors166', 'cors167', 'cors168', 'cors169', 'cws-tigrou', 'roma50-ipmi', 'roma51-ipmi', 'roma52-ipmi', 'roma53-ipmi', 'roma54-ipmi', 'roma55-ipmi', 'roma56-ipmi', 'roma57-ipmi', 'roma58-ipmi', 'roma59-ipmi', 'roma60-ipmi', 'roma61-ipmi', 'tigrou3'])
        self.assertEqual(list(ns1), [str(ns) for ns in ns1.nsiter()])

    def test_contiguous(self):
        """test NodeSet.contiguous() iterator"""
        ns1 = NodeSet("cors,roma[50-61]-ipmi,cors[113,115-117,130,166-169],cws-tigrou,tigrou3")
        self.assertEqual(['cors', 'cors113', 'cors[115-117]', 'cors130', 'cors[166-169]', 'cws-tigrou', 'roma[50-61]-ipmi', 'tigrou3'], [str(ns) for ns in ns1.contiguous()])
        # check if NodeSet instances returned by contiguous() iterator are not the same
        testlist = list(ns1.contiguous())
        for i in range(len(testlist)):
            for j in range(i + 1, len(testlist)):
                self.assertNotEqual(testlist[i], testlist[j])
                self.assertNotEqual(id(testlist[i]), id(testlist[j]))

    def testEqualityMore(self):
        """test NodeSet equality (more)"""
        self.assertEqual(NodeSet(), NodeSet())
        ns1 = NodeSet("nodealone")
        ns2 = NodeSet("nodealone")
        self.assertEqual(ns1, ns2)
        ns1 = NodeSet("clu3,clu[4-9],clu11")
        ns2 = NodeSet("clu[3-9,11]")
        self.assertEqual(ns1, ns2)
        if ns1 == None:
            self.fail("ns1 == None succeeded")
        if ns1 != None:
            pass
        else:
            self.fail("ns1 != None failed")

    def testNodeSetNone(self):
        """test NodeSet methods behavior with None argument"""
        nodeset = NodeSet(None)
        self.assertEqual(len(nodeset), 0)
        self.assertEqual(list(nodeset), [])
        nodeset.update(None)
        self.assertEqual(list(nodeset), [])
        nodeset.intersection_update(None)
        self.assertEqual(list(nodeset), [])
        nodeset.difference_update(None)
        self.assertEqual(list(nodeset), [])
        nodeset.symmetric_difference_update(None)
        self.assertEqual(list(nodeset), [])
        n = nodeset.union(None)
        self.assertEqual(list(n), [])
        self.assertEqual(len(n), 0)
        n = nodeset.intersection(None)
        self.assertEqual(list(n), [])
        n = nodeset.difference(None)
        self.assertEqual(list(n), [])
        n = nodeset.symmetric_difference(None)
        self.assertEqual(list(n), [])
        nodeset = NodeSet("abc[3,6-89],def[3-98,104,128-133]")
        self.assertEqual(len(nodeset), 188)
        nodeset.update(None)
        self.assertEqual(len(nodeset), 188)
        nodeset.intersection_update(None)
        self.assertEqual(len(nodeset), 0)
        self.assertEqual(list(nodeset), [])
        nodeset = NodeSet("abc[3,6-89],def[3-98,104,128-133]")
        self.assertEqual(len(nodeset), 188)
        nodeset.difference_update(None)
        self.assertEqual(len(nodeset), 188)
        nodeset.symmetric_difference_update(None)
        self.assertEqual(len(nodeset), 188)
        n = nodeset.union(None)
        self.assertEqual(len(nodeset), 188)
        n = nodeset.intersection(None)
        self.assertEqual(list(n), [])
        self.assertEqual(len(n), 0)
        n = nodeset.difference(None)
        self.assertEqual(len(n), 188)
        n = nodeset.symmetric_difference(None)
        self.assertEqual(len(n), 188)
        self.assertFalse(n.issubset(None))
        self.assertTrue(n.issuperset(None))
        n = NodeSet(None)
        n.clear()
        self.assertEqual(len(n), 0)

    def testCopy(self):
        """test NodeSet.copy()"""
        nodeset = NodeSet("zclu[115-117,130,166-170],glycine[68,4780-4999]")
        self.assertEqual(str(nodeset), \
            "glycine[68,4780-4999],zclu[115-117,130,166-170]")
        nodeset2 = nodeset.copy()
        nodeset3 = nodeset.copy()
        self.assertEqual(nodeset, nodeset2) # content equality
        self.assertTrue(isinstance(nodeset, NodeSet))
        self.assertTrue(isinstance(nodeset2, NodeSet))
        self.assertTrue(isinstance(nodeset3, NodeSet))
        nodeset2.remove("glycine68")
        self.assertEqual(len(nodeset), len(nodeset2) + 1)
        self.assertNotEqual(nodeset, nodeset2)
        self.assertEqual(str(nodeset2), \
            "glycine[4780-4999],zclu[115-117,130,166-170]")
        self.assertEqual(str(nodeset), \
            "glycine[68,4780-4999],zclu[115-117,130,166-170]")
        nodeset2.add("glycine68")
        self.assertEqual(str(nodeset2), \
            "glycine[68,4780-4999],zclu[115-117,130,166-170]")
        self.assertEqual(nodeset, nodeset3)
        nodeset3.update(NodeSet("zclu118"))
        self.assertNotEqual(nodeset, nodeset3)
        self.assertEqual(len(nodeset) + 1, len(nodeset3))
        self.assertEqual(str(nodeset), \
            "glycine[68,4780-4999],zclu[115-117,130,166-170]")
        self.assertEqual(str(nodeset3), \
            "glycine[68,4780-4999],zclu[115-118,130,166-170]")
        # test copy with single nodes
        nodeset = NodeSet("zclu[115-117,130,166-170],foo,bar,glycine[68,4780-4999]")
        nodeset2 = nodeset.copy()
        self.assertEqual(nodeset, nodeset2) # content equality
        # same with NodeSetBase
        nodeset = NodeSetBase("foobar", None)
        nodeset2 = nodeset.copy()
        self.assertEqual(nodeset, nodeset2) # content equality

    def test_unpickle_v1_3_py24(self):
        """test NodeSet unpickling (against v1.3/py24)"""
        nodeset = pickle.loads(binascii.a2b_base64("gAJjQ2x1c3RlclNoZWxsLk5vZGVTZXQKTm9kZVNldApxACmBcQF9cQIoVQdfbGVuZ3RocQNLAFUJX3BhdHRlcm5zcQR9cQUoVQh5ZWxsb3clc3EGKGNDbHVzdGVyU2hlbGwuTm9kZVNldApSYW5nZVNldApxB29xCH1xCShoA0sBVQlfYXV0b3N0ZXBxCkdUskmtJZTDfVUHX3Jhbmdlc3ELXXEMKEsESwRLAUsAdHENYXViVQZibHVlJXNxDihoB29xD31xEChoA0sIaApHVLJJrSWUw31oC11xESgoSwZLCksBSwB0cRIoSw1LDUsBSwB0cRMoSw9LD0sBSwB0cRQoSxFLEUsBSwB0cRVldWJVB2dyZWVuJXNxFihoB29xF31xGChoA0tlaApHVLJJrSWUw31oC11xGShLAEtkSwFLAHRxGmF1YlUDcmVkcRtOdWgKTnViLg=="))
        self.assertEqual(nodeset, NodeSet("blue[6-10,13,15,17],green[0-100],red,yellow4"))
        self.assertEqual(str(nodeset), "blue[6-10,13,15,17],green[0-100],red,yellow4")
        self.assertEqual(len(nodeset), 111)
        self.assertEqual(nodeset[0], "blue6")
        self.assertEqual(nodeset[1], "blue7")
        self.assertEqual(nodeset[-1], "yellow4")

    # unpickle_v1_4_py24 : unpickling fails as v1.4 does not have slice pickling workaround
    def test_unpickle_v1_3_py26(self):
        """test NodeSet unpickling (against v1.3/py26)"""
        nodeset = pickle.loads(binascii.a2b_base64("gAJjQ2x1c3RlclNoZWxsLk5vZGVTZXQKTm9kZVNldApxACmBcQF9cQIoVQdfbGVuZ3RocQNLAFUJX3BhdHRlcm5zcQR9cQUoVQh5ZWxsb3clc3EGKGNDbHVzdGVyU2hlbGwuTm9kZVNldApSYW5nZVNldApxB29xCH1xCShoA0sBVQlfYXV0b3N0ZXBxCkdUskmtJZTDfVUHX3Jhbmdlc3ELXXEMKEsESwRLAUsAdHENYXViVQZibHVlJXNxDihoB29xD31xEChoA0sIaApHVLJJrSWUw31oC11xESgoSwZLCksBSwB0cRIoSw1LDUsBSwB0cRMoSw9LD0sBSwB0cRQoSxFLEUsBSwB0cRVldWJVB2dyZWVuJXNxFihoB29xF31xGChoA0tlaApHVLJJrSWUw31oC11xGShLAEtkSwFLAHRxGmF1YlUDcmVkcRtOdWgKTnViLg=="))
        self.assertEqual(nodeset, NodeSet("blue[6-10,13,15,17],green[0-100],red,yellow4"))
        self.assertEqual(str(nodeset), "blue[6-10,13,15,17],green[0-100],red,yellow4")
        self.assertEqual(len(nodeset), 111)
        self.assertEqual(nodeset[0], "blue6")
        self.assertEqual(nodeset[1], "blue7")
        self.assertEqual(nodeset[-1], "yellow4")

    # unpickle_v1_4_py24 : unpickling fails as v1.4 does not have slice pickling workaround

    def test_unpickle_v1_4_py26(self):
        """test NodeSet unpickling (against v1.4/py26)"""
        nodeset = pickle.loads(binascii.a2b_base64("gAJjQ2x1c3RlclNoZWxsLk5vZGVTZXQKTm9kZVNldApxACmBcQF9cQIoVQdfbGVuZ3RocQNLAFUJX3BhdHRlcm5zcQR9cQUoVQh5ZWxsb3clc3EGKGNDbHVzdGVyU2hlbGwuTm9kZVNldApSYW5nZVNldApxB29xCH1xCihoA0sBVQlfYXV0b3N0ZXBxC0dUskmtJZTDfVUHX3Jhbmdlc3EMXXENY19fYnVpbHRpbl9fCnNsaWNlCnEOSwRLBUsBh3EPUnEQSwCGcRFhVQhfdmVyc2lvbnESSwJ1YlUGYmx1ZSVzcRMoaAdvcRR9cRUoaANLCGgLR1SySa0llMN9aAxdcRYoaA5LBksLSwGHcRdScRhLAIZxGWgOSw1LDksBh3EaUnEbSwCGcRxoDksPSxBLAYdxHVJxHksAhnEfaA5LEUsSSwGHcSBScSFLAIZxImVoEksCdWJVB2dyZWVuJXNxIyhoB29xJH1xJShoA0tlaAtHVLJJrSWUw31oDF1xJmgOSwBLZUsBh3EnUnEoSwCGcSlhaBJLAnViVQNyZWRxKk51aAtOdWIu"))
        self.assertEqual(nodeset, NodeSet("blue[6-10,13,15,17],green[0-100],red,yellow4"))
        self.assertEqual(str(nodeset), "blue[6-10,13,15,17],green[0-100],red,yellow4")
        self.assertEqual(len(nodeset), 111)
        self.assertEqual(nodeset[0], "blue6")
        self.assertEqual(nodeset[1], "blue7")
        self.assertEqual(nodeset[-1], "yellow4")

    def test_unpickle_v1_5_py24(self):
        """test NodeSet unpickling (against v1.5/py24)"""
        nodeset = pickle.loads(binascii.a2b_base64("gAJjQ2x1c3RlclNoZWxsLk5vZGVTZXQKTm9kZVNldApxACmBcQF9cQIoVQdfbGVuZ3RocQNLAFUJX3BhdHRlcm5zcQR9cQUoVQh5ZWxsb3clc3EGKGNDbHVzdGVyU2hlbGwuTm9kZVNldApSYW5nZVNldApxB29xCH1xCihoA0sBVQlfYXV0b3N0ZXBxC0dUskmtJZTDfVUHX3Jhbmdlc3EMXXENSwRLBUsBh3EOSwCGcQ9hVQhfdmVyc2lvbnEQSwJ1YlUGYmx1ZSVzcREoaAdvcRJ9cRMoaANLCGgLR1SySa0llMN9aAxdcRQoSwZLC0sBh3EVSwCGcRZLDUsOSwGHcRdLAIZxGEsPSxBLAYdxGUsAhnEaSxFLEksBh3EbSwCGcRxlaBBLAnViVQdncmVlbiVzcR0oaAdvcR59cR8oaANLZWgLR1SySa0llMN9aAxdcSBLAEtlSwGHcSFLAIZxImFoEEsCdWJVA3JlZHEjTnVoC051Yi4="))
        self.assertEqual(nodeset, NodeSet("blue[6-10,13,15,17],green[0-100],red,yellow4"))
        self.assertEqual(str(nodeset), "blue[6-10,13,15,17],green[0-100],red,yellow4")
        self.assertEqual(len(nodeset), 111)
        self.assertEqual(nodeset[0], "blue6")
        self.assertEqual(nodeset[1], "blue7")
        self.assertEqual(nodeset[-1], "yellow4")

    def test_unpickle_v1_5_py26(self):
        """test NodeSet unpickling (against v1.5/py26)"""
        nodeset = pickle.loads(binascii.a2b_base64("gAJjQ2x1c3RlclNoZWxsLk5vZGVTZXQKTm9kZVNldApxACmBcQF9cQIoVQdfbGVuZ3RocQNLAFUJX3BhdHRlcm5zcQR9cQUoVQh5ZWxsb3clc3EGKGNDbHVzdGVyU2hlbGwuTm9kZVNldApSYW5nZVNldApxB29xCH1xCihoA0sBVQlfYXV0b3N0ZXBxC0dUskmtJZTDfVUHX3Jhbmdlc3EMXXENY19fYnVpbHRpbl9fCnNsaWNlCnEOSwRLBUsBh3EPUnEQSwCGcRFhVQhfdmVyc2lvbnESSwJ1YlUGYmx1ZSVzcRMoaAdvcRR9cRUoaANLCGgLR1SySa0llMN9aAxdcRYoaA5LBksLSwGHcRdScRhLAIZxGWgOSw1LDksBh3EaUnEbSwCGcRxoDksPSxBLAYdxHVJxHksAhnEfaA5LEUsSSwGHcSBScSFLAIZxImVoEksCdWJVB2dyZWVuJXNxIyhoB29xJH1xJShoA0tlaAtHVLJJrSWUw31oDF1xJmgOSwBLZUsBh3EnUnEoSwCGcSlhaBJLAnViVQNyZWRxKk51aAtOdWIu"))
        self.assertEqual(nodeset, NodeSet("blue[6-10,13,15,17],green[0-100],red,yellow4"))
        self.assertEqual(str(nodeset), "blue[6-10,13,15,17],green[0-100],red,yellow4")
        self.assertEqual(len(nodeset), 111)
        self.assertEqual(nodeset[0], "blue6")
        self.assertEqual(nodeset[1], "blue7")
        self.assertEqual(nodeset[-1], "yellow4")

    def test_unpickle_v1_6_py24(self):
        """test NodeSet unpickling (against v1.6/py24)"""
        nodeset = pickle.loads(binascii.a2b_base64("gAJjQ2x1c3RlclNoZWxsLk5vZGVTZXQKTm9kZVNldApxACmBcQF9cQIoVQdfbGVuZ3RocQNLAFUJX3BhdHRlcm5zcQR9cQUoVQh5ZWxsb3clc3EGY0NsdXN0ZXJTaGVsbC5SYW5nZVNldApSYW5nZVNldApxB1UBNHEIhXEJUnEKfXELKFUHcGFkZGluZ3EMTlUJX2F1dG9zdGVwcQ1HVLJJrSWUw31VCF92ZXJzaW9ucQ5LA3ViVQZibHVlJXNxD2gHVQ02LTEwLDEzLDE1LDE3cRCFcRFScRJ9cRMoaAxOaA1HVLJJrSWUw31oDksDdWJVB2dyZWVuJXNxFGgHVQUwLTEwMHEVhXEWUnEXfXEYKGgMTmgNR1SySa0llMN9aA5LA3ViVQNyZWRxGU51aA1OdWIu"))
        self.assertEqual(nodeset, NodeSet("blue[6-10,13,15,17],green[0-100],red,yellow4"))
        self.assertEqual(str(nodeset), "blue[6-10,13,15,17],green[0-100],red,yellow4")
        self.assertEqual(len(nodeset), 111)
        self.assertEqual(nodeset[0], "blue6")
        self.assertEqual(nodeset[1], "blue7")
        self.assertEqual(nodeset[-1], "yellow4")

    def test_unpickle_v1_6_py26(self):
        """test NodeSet unpickling (against v1.6/py26)"""
        nodeset = pickle.loads(binascii.a2b_base64("gAJjQ2x1c3RlclNoZWxsLk5vZGVTZXQKTm9kZVNldApxACmBcQF9cQIoVQdfbGVuZ3RocQNLAFUJX3BhdHRlcm5zcQR9cQUoVQh5ZWxsb3clc3EGY0NsdXN0ZXJTaGVsbC5SYW5nZVNldApSYW5nZVNldApxB1UBNHEIhXEJUnEKfXELKFUHcGFkZGluZ3EMTlUJX2F1dG9zdGVwcQ1HVLJJrSWUw31VCF92ZXJzaW9ucQ5LA3ViVQZibHVlJXNxD2gHVQ02LTEwLDEzLDE1LDE3cRCFcRFScRJ9cRMoaAxOaA1HVLJJrSWUw31oDksDdWJVB2dyZWVuJXNxFGgHVQUwLTEwMHEVhXEWUnEXfXEYKGgMTmgNR1SySa0llMN9aA5LA3ViVQNyZWRxGU51aA1OdWIu"))
        self.assertEqual(nodeset, NodeSet("blue[6-10,13,15,17],green[0-100],red,yellow4"))
        self.assertEqual(str(nodeset), "blue[6-10,13,15,17],green[0-100],red,yellow4")
        self.assertEqual(len(nodeset), 111)
        self.assertEqual(nodeset[0], "blue6")
        self.assertEqual(nodeset[1], "blue7")
        self.assertEqual(nodeset[-1], "yellow4")

    def test_pickle_current(self):
        """test NodeSet pickling (current version)"""
        dump = pickle.dumps(NodeSet("foo[1-100]"))
        self.assertNotEqual(dump, None)
        nodeset = pickle.loads(dump)
        self.assertEqual(nodeset, NodeSet("foo[1-100]"))
        self.assertEqual(str(nodeset), "foo[1-100]")
        self.assertEqual(nodeset[0], "foo1")
        self.assertEqual(nodeset[1], "foo2")
        self.assertEqual(nodeset[-1], "foo100")

    def test_nd_unpickle_v1_6_py26(self):
        """test NodeSet nD unpickling (against v1.6/py26)"""
        # Use cases that will test conversion required when using
        # NodeSet nD (see NodeSet.__setstate__()):

        # TEST FROM v1.6: NodeSet("foo[1-100]bar[1-10]")
        nodeset = pickle.loads(binascii.a2b_base64("Y2NvcHlfcmVnCl9yZWNvbnN0cnVjdG9yCnAwCihjQ2x1c3RlclNoZWxsLk5vZGVTZXQKTm9kZVNldApwMQpjX19idWlsdGluX18Kb2JqZWN0CnAyCk50cDMKUnA0CihkcDUKUydfbGVuZ3RoJwpwNgpJMApzUydfcGF0dGVybnMnCnA3CihkcDgKUydmb28lc2JhclsxLTEwXScKcDkKY0NsdXN0ZXJTaGVsbC5SYW5nZVNldApSYW5nZVNldApwMTAKKFMnMS0xMDAnCnAxMQp0cDEyClJwMTMKKGRwMTQKUydwYWRkaW5nJwpwMTUKTnNTJ19hdXRvc3RlcCcKcDE2CkYxZSsxMDAKc1MnX3ZlcnNpb24nCnAxNwpJMwpzYnNzZzE2Ck5zYi4=\n"))

        self.assertEqual(str(nodeset), str(NodeSet("foo[1-100]bar[1-10]")))
        self.assertEqual(nodeset, NodeSet("foo[1-100]bar[1-10]"))
        self.assertEqual(len(nodeset), 1000)
        self.assertEqual(nodeset[0], "foo1bar1")
        self.assertEqual(nodeset[1], "foo1bar2")
        self.assertEqual(nodeset[-1], "foo100bar10")

        # TEST FROM v1.6: NodeSet("foo[1-100]bar3,foo[1-100]bar7,foo[1-100]bar12")
        nodeset = pickle.loads(binascii.a2b_base64("Y2NvcHlfcmVnCl9yZWNvbnN0cnVjdG9yCnAwCihjQ2x1c3RlclNoZWxsLk5vZGVTZXQKTm9kZVNldApwMQpjX19idWlsdGluX18Kb2JqZWN0CnAyCk50cDMKUnA0CihkcDUKUydfbGVuZ3RoJwpwNgpJMApzUydfcGF0dGVybnMnCnA3CihkcDgKUydmb28lc2JhcjEyJwpwOQpjQ2x1c3RlclNoZWxsLlJhbmdlU2V0ClJhbmdlU2V0CnAxMAooUycxLTEwMCcKcDExCnRwMTIKUnAxMwooZHAxNApTJ3BhZGRpbmcnCnAxNQpOc1MnX2F1dG9zdGVwJwpwMTYKRjFlKzEwMApzUydfdmVyc2lvbicKcDE3CkkzCnNic1MnZm9vJXNiYXIzJwpwMTgKZzEwCihTJzEtMTAwJwpwMTkKdHAyMApScDIxCihkcDIyCmcxNQpOc2cxNgpGMWUrMTAwCnNnMTcKSTMKc2JzUydmb28lc2JhcjcnCnAyMwpnMTAKKFMnMS0xMDAnCnAyNAp0cDI1ClJwMjYKKGRwMjcKZzE1Ck5zZzE2CkYxZSsxMDAKc2cxNwpJMwpzYnNzZzE2Ck5zYi4=\n"))

        self.assertEqual(str(nodeset), str(NodeSet("foo[1-100]bar[3,7,12]")))
        self.assertEqual(nodeset, NodeSet("foo[1-100]bar[3,7,12]"))
        self.assertEqual(len(nodeset), 300)
        self.assertEqual(nodeset[0], "foo1bar3")
        self.assertEqual(nodeset[1], "foo1bar7")
        self.assertEqual(nodeset[-1], "foo100bar12")

        # TEST FROM v1.6: NodeSet("foo1bar3,foo2bar4,foo[6-20]bar3")
        nodeset = pickle.loads(binascii.a2b_base64("Y2NvcHlfcmVnCl9yZWNvbnN0cnVjdG9yCnAwCihjQ2x1c3RlclNoZWxsLk5vZGVTZXQKTm9kZVNldApwMQpjX19idWlsdGluX18Kb2JqZWN0CnAyCk50cDMKUnA0CihkcDUKUydfbGVuZ3RoJwpwNgpJMApzUydfcGF0dGVybnMnCnA3CihkcDgKUydmb28lc2JhcjMnCnA5CmNDbHVzdGVyU2hlbGwuUmFuZ2VTZXQKUmFuZ2VTZXQKcDEwCihTJzEsNi0yMCcKcDExCnRwMTIKUnAxMwooZHAxNApTJ3BhZGRpbmcnCnAxNQpOc1MnX2F1dG9zdGVwJwpwMTYKRjFlKzEwMApzUydfdmVyc2lvbicKcDE3CkkzCnNic1MnZm9vJXNiYXI0JwpwMTgKZzEwCihTJzInCnAxOQp0cDIwClJwMjEKKGRwMjIKZzE1Ck5zZzE2CkYxZSsxMDAKc2cxNwpJMwpzYnNzZzE2Ck5zYi4=\n"))

        self.assertEqual(str(nodeset), str(NodeSet("foo[1,6-20]bar3,foo2bar4")))
        self.assertEqual(nodeset, NodeSet("foo[1,6-20]bar3,foo2bar4"))
        self.assertEqual(len(nodeset), 17)
        self.assertEqual(nodeset[0], "foo1bar3")
        self.assertEqual(nodeset[1], "foo6bar3")
        self.assertEqual(nodeset[-1], "foo2bar4")

        # TEST FROM v1.6: NodeSet("foo[1-100]bar4,foo[1-100]bar,foo[1-20],bar,foo101bar4")
        nodeset = pickle.loads(binascii.a2b_base64("Y2NvcHlfcmVnCl9yZWNvbnN0cnVjdG9yCnAwCihjQ2x1c3RlclNoZWxsLk5vZGVTZXQKTm9kZVNldApwMQpjX19idWlsdGluX18Kb2JqZWN0CnAyCk50cDMKUnA0CihkcDUKUydfbGVuZ3RoJwpwNgpJMApzUydfcGF0dGVybnMnCnA3CihkcDgKUydmb28lcycKcDkKY0NsdXN0ZXJTaGVsbC5SYW5nZVNldApSYW5nZVNldApwMTAKKFMnMS0yMCcKcDExCnRwMTIKUnAxMwooZHAxNApTJ3BhZGRpbmcnCnAxNQpOc1MnX2F1dG9zdGVwJwpwMTYKRjFlKzEwMApzUydfdmVyc2lvbicKcDE3CkkzCnNic1MnZm9vJXNiYXInCnAxOApnMTAKKFMnMS0xMDAnCnAxOQp0cDIwClJwMjEKKGRwMjIKZzE1Ck5zZzE2CkYxZSsxMDAKc2cxNwpJMwpzYnNTJ2ZvbyVzYmFyNCcKcDIzCmcxMAooUycxLTEwMScKcDI0CnRwMjUKUnAyNgooZHAyNwpnMTUKTnNnMTYKRjFlKzEwMApzZzE3CkkzCnNic1MnYmFyJwpwMjgKTnNzZzE2Ck5zYi4=\n"))

        self.assertEqual(str(nodeset), str(NodeSet("bar,foo[1-20],foo[1-100]bar,foo[1-101]bar4")))
        self.assertEqual(nodeset, NodeSet("bar,foo[1-20],foo[1-100]bar,foo[1-101]bar4"))
        self.assertEqual(len(nodeset), 222)
        self.assertEqual(nodeset[0], "bar")
        self.assertEqual(nodeset[1], "foo1")
        self.assertEqual(nodeset[-1], "foo101bar4")

    def test_nd_pickle_current(self):
        """test NodeSet nD pickling (current version)"""
        dump = pickle.dumps(NodeSet("foo[1-100]bar[1-10]"))
        self.assertNotEqual(dump, None)
        nodeset = pickle.loads(dump)
        self.assertEqual(nodeset, NodeSet("foo[1-100]bar[1-10]"))
        self.assertEqual(str(nodeset), "foo[1-100]bar[1-10]")
        self.assertEqual(nodeset[0], "foo1bar1")
        self.assertEqual(nodeset[1], "foo1bar2")
        self.assertEqual(nodeset[-1], "foo100bar10")

        dump = pickle.dumps(NodeSet("foo[1-100]bar4,foo[1-100]bar,foo[1-20],bar,foo101bar4"))
        self.assertNotEqual(dump, None)
        nodeset = pickle.loads(dump)
        self.assertEqual(nodeset, NodeSet("bar,foo[1-20],foo[1-100]bar,foo[1-101]bar4"))
        self.assertEqual(str(nodeset), "bar,foo[1-20],foo[1-100]bar,foo[1-101]bar4")
        self.assertEqual(nodeset[0], "bar")
        self.assertEqual(nodeset[1], "foo1")
        self.assertEqual(nodeset[-1], "foo101bar4")

    def testNodeSetBase(self):
        """test underlying NodeSetBase class"""
        rset = RangeSet("1-100,200")
        self.assertEqual(len(rset), 101)
        nsb = NodeSetBase("foo%sbar", rset) 
        self.assertEqual(len(nsb), len(rset))
        self.assertEqual(str(nsb), "foo[1-100,200]bar")
        nsbcpy = nsb.copy()
        self.assertEqual(len(nsbcpy), 101)
        self.assertEqual(str(nsbcpy), "foo[1-100,200]bar")
        other = NodeSetBase("foo%sbar", RangeSet("201"))
        nsbcpy.add(other)
        self.assertEqual(len(nsb), 101)
        self.assertEqual(str(nsb), "foo[1-100,200]bar")
        self.assertEqual(len(nsbcpy), 102)
        self.assertEqual(str(nsbcpy), "foo[1-100,200-201]bar")

    def test_nd_simple(self):
        ns1 = NodeSet("da3c1")
        ns2 = NodeSet("da3c2")
        self.assertEqual(str(ns1 | ns2), "da3c[1-2]")
        ns1 = NodeSet("da3c1-ipmi")
        ns2 = NodeSet("da3c2-ipmi")
        self.assertEqual(str(ns1 | ns2), "da3c[1-2]-ipmi")
        ns1 = NodeSet("da[2-3]c1")
        ns2 = NodeSet("da[2-3]c2")
        self.assertEqual(str(ns1 | ns2), "da[2-3]c[1-2]")
        ns1 = NodeSet("da[2-3]c1")
        ns2 = NodeSet("da[2-3]c1")
        self.assertEqual(str(ns1 | ns2), "da[2-3]c1")

    def test_nd_multiple(self):
        nodeset = NodeSet("da[30,34-51,59-60]p[1-2]")
        self.assertEqual(len(nodeset), 42)
        nodeset = NodeSet("da[30,34-51,59-60]p[1-2],da[70-77]p3")
        self.assertEqual(len(nodeset), 42+8)
        self.assertEqual(str(nodeset), "da[30,34-51,59-60]p[1-2],da[70-77]p3")
        # advanced parsing checks
        nodeset = NodeSet("da[1-10]c[1-2]")
        self.assertEqual(len(nodeset), 20)
        self.assertEqual(str(nodeset), "da[1-10]c[1-2]")
        nodeset = NodeSet("da[1-10]c[1-2]p")
        self.assertEqual(len(nodeset), 20)
        self.assertEqual(str(nodeset), "da[1-10]c[1-2]p")
        nodeset = NodeSet("da[1-10]c[1-2]p0")
        self.assertEqual(len(nodeset), 20)
        self.assertEqual(str(nodeset), "da[1-10]c[1-2]p0")
        nodeset = NodeSet("da[1-10]c[1-2,8]p0")
        self.assertEqual(len(nodeset), 30)
        self.assertEqual(str(nodeset), "da[1-10]c[1-2,8]p0")
        nodeset = NodeSet("da[1-10]c3p0x3")
        self.assertEqual(len(nodeset), 10)
        self.assertEqual(str(nodeset), "da[1-10]c3p0x3")
        nodeset = NodeSet("[1-7,10]xpc[3,4]p40_3,9xpc[3,4]p40_3,8xpc[3,4]p[40]_[3]")
        self.assertEqual(len(nodeset), 20)
        self.assertEqual(str(nodeset), "[1-10]xpc[3-4]p40_3")

    def test_nd_len(self):
        ns1 = NodeSet("da3c1")
        ns2 = NodeSet("da3c2")
        self.assertEqual(len(ns1 | ns2), 2)

        ns1 = NodeSet("da[2-3]c1")
        self.assertEqual(len(ns1), 2)
        ns2 = NodeSet("da[2-3]c2")
        self.assertEqual(len(ns2), 2)
        self.assertEqual(len(ns1) + len(ns2), 4)

        ns1 = NodeSet("da[1-1000]c[1-2]p[0-1]")
        self.assertEqual(len(ns1), 4000)

        ns1 = NodeSet("tronic[0036-1630]c[3-4]")
        self.assertEqual(len(ns1), 3190)
        ns1 = NodeSet("tronic[0036-1630]c[3-400]")
        self.assertEqual(len(ns1), 634810)

        # checking length of overlapping union
        ns1 = NodeSet("da[2-3]c[0-1]")
        self.assertEqual(len(ns1), 4)
        ns2 = NodeSet("da[2-3]c[1-2]")
        self.assertEqual(len(ns2), 4)
        self.assertEqual(len(ns1) + len(ns2), 8)
        self.assertEqual(len(ns1 | ns2), 6) # da[2-3]c[0-2]

        # checking length of nD + 1D
        ns1 = NodeSet("da[2-3]c[0-1]")
        self.assertEqual(len(ns1), 4)
        ns2 = NodeSet("node[1-1000]")
        self.assertEqual(len(ns2), 1000)
        self.assertEqual(len(ns1) + len(ns2), 1004)
        self.assertEqual(len(ns1 | ns2), 1004)

        # checking length of nD + single node
        ns1 = NodeSet("da[2-3]c[0-1]")
        self.assertEqual(len(ns1), 4)
        ns2 = NodeSet("single")
        self.assertEqual(len(ns2), 1)
        self.assertEqual(len(ns1) + len(ns2), 5)
        self.assertEqual(len(ns1 | ns2), 5)

    def test_nd_iter(self):
        ns1 = NodeSet("da[2-3]c[0-1]")
        result = list(iter(ns1))
        self.assertEqual(result, ['da2c0', 'da2c1', 'da3c0', 'da3c1'])

    def test_nd_iter(self):
        ns1 = NodeSet("da[2-3]c[0-1]")
        result = list(iter(ns1))
        self.assertEqual(result, ['da2c0', 'da2c1', 'da3c0', 'da3c1'])

    def test_nd_nsiter(self):
        ns1 = NodeSet("da[2-3]c[0-1]")
        result = list(ns1.nsiter())
        self.assertEqual(result, [NodeSet('da2c0'), NodeSet('da2c1'), NodeSet('da3c0'), NodeSet('da3c1')])

    def test_nd_getitem(self):
        nodeset = NodeSet("da[30,34-51,59-60]p[1-2]")
        self.assertEqual(len(nodeset), 42)
        self.assertEqual(nodeset[0], "da30p1")
        self.assertEqual(nodeset[1], "da30p2")
        self.assertEqual(nodeset[2], "da34p1")
        self.assertEqual(nodeset[-1], "da60p2")

        nodeset = NodeSet("da[30,34-51,59-60]p[1-2],da[70-77]p2")
        self.assertEqual(len(nodeset), 42+8)
        #self.assertEqual(str(nodeset), "da[30,34-51,59-60,70-77]p2,da[30,34-51,59-60]p1") # OLD FOLD
        self.assertEqual(str(nodeset), "da[30,34-51,59-60]p[1-2],da[70-77]p2")  # NEW FOLD
        #self.assertEqual(nodeset[0], "da30p2") # OLD FOLD
        self.assertEqual(nodeset[0], "da30p1") # NEW FOLD

    def test_nd_split(self):
        nodeset = NodeSet("foo[1-3]bar[2-4]")
        self.assertEqual((NodeSet("foo1bar[2-4]"), \
                          NodeSet("foo2bar[2-4]"), \
                          NodeSet("foo3bar[2-4]")), tuple(nodeset.split(3)))

        nodeset = NodeSet("foo[1-3]bar[2-4]")
        self.assertEqual((NodeSet("foo1bar[2-4],foo2bar[2-3]"), \
                          NodeSet("foo[2-3]bar4,foo3bar[2-3]")), \
                          tuple(nodeset.split(2)))

    def test_nd_contiguous(self):
        ns1 = NodeSet("foo[3-100]bar[4-30]")
        self.assertEqual(str(ns1), "foo[3-100]bar[4-30]")
        self.assertEqual(len(ns1), 98*27)

        ns1 = NodeSet("foo[3-100,200]bar4")
        self.assertEqual(['foo[3-100]bar4', 'foo200bar4'], [str(ns) for ns in ns1.contiguous()])
        self.assertEqual(str(ns1), "foo[3-100,200]bar4")

        ns1 = NodeSet("foo[3-100,102-500]bar[4-30]")
        self.assertEqual(['foo[3-100]bar[4-30]', 'foo[102-500]bar[4-30]'], [str(ns) for ns in ns1.contiguous()])
        self.assertEqual(str(ns1), "foo[3-100,102-500]bar[4-30]")

        ns1 = NodeSet("foo[3-100,102-500]bar[4-30,37]")
        self.assertEqual(['foo[3-100]bar[4-30]', 'foo[3-100]bar37', 'foo[102-500]bar[4-30]', 'foo[102-500]bar37'], [str(ns) for ns in ns1.contiguous()])
        self.assertEqual(str(ns1), "foo[3-100,102-500]bar[4-30,37]")

    def test_nd_fold(self):
        ns = NodeSet("da[2-3]c[1-2],da[3-4]c[3-4]")
        self.assertEqual(str(ns), "da[2-3]c[1-2],da[3-4]c[3-4]")
        ns = NodeSet("da[2-3]c[1-2],da[3-4]c[2-3]")
        self.assertEqual(str(ns), "da3c[1-3],da2c[1-2],da4c[2-3]")
        ns = NodeSet("da[2-3]c[1-2],da[3-4]c[1-2]")
        self.assertEqual(str(ns), "da[2-4]c[1-2]")
        ns = NodeSet("da[2-3]c[1-2]p3,da[3-4]c[1-3]p3")
        self.assertEqual(str(ns), "da[2-4]c[1-2]p3,da[3-4]c3p3")
        ns = NodeSet("da[2-3]c[1-2],da[2,5]c[2-3]")
        self.assertEqual(str(ns), "da2c[1-3],da3c[1-2],da5c[2-3]")

    def test_nd_issuperset(self):
        ns1 = NodeSet("da[2-3]c[1-2]")
        ns2 = NodeSet("da[1-10]c[1-2]")
        self.assertTrue(ns2.issuperset(ns1))
        self.assertFalse(ns1.issuperset(ns2))

        ns1 = NodeSet("da[2-3]c[1-2]")
        ns1.add("da5c2")
        self.assertTrue(ns2.issuperset(ns1))
        self.assertFalse(ns1.issuperset(ns2))

        ns1 = NodeSet("da[2-3]c[1-2]")
        ns1.add("da5c[1-2]")
        self.assertTrue(ns2.issuperset(ns1))
        self.assertFalse(ns1.issuperset(ns2))

        ns1 = NodeSet("da[2-3]c[1-2]")
        ns1.add("da5c[2-3]")
        self.assertFalse(ns2.issuperset(ns1))
        self.assertFalse(ns1.issuperset(ns2))

        # large ranges
        nodeset = NodeSet("tronic[1-5000]c[1-2]")
        self.assertEqual(len(nodeset), 10000)
        self.assertTrue(nodeset.issuperset("tronic[1-5000]c1"))
        self.assertFalse(nodeset.issuperset("tronic[1-5000]c3"))
        nodeset = NodeSet("tronic[1-5000]c[1-200]p3")
        self.assertEqual(len(nodeset), 1000000)
        self.assertTrue(nodeset.issuperset("tronic[1-5000]c200p3"))
        self.assertFalse(nodeset.issuperset("tronic[1-5000]c[200-300]p3"))
        self.assertFalse(nodeset.issuperset("tronic[1-5000/2]c[200-300/2]p3"))

    def test_nd_issubset(self):
        nodeset = NodeSet("artcore[3-999]-ib0")
        self.assertEqual(len(nodeset), 997)
        self.assertTrue(nodeset.issubset("artcore[3-999]-ib[0-1]"))
        self.assertTrue(nodeset.issubset("artcore[1-1000]-ib0"))
        self.assertTrue(nodeset.issubset("artcore[1-1000]-ib[0,2]"))
        self.assertFalse(nodeset.issubset("artcore[350-427]-ib0"))
        # check lt
        self.assertTrue(nodeset < NodeSet("artcore[2-32000]-ib0"))
        self.assertFalse(nodeset > NodeSet("artcore[2-32000]-ib0"))
        self.assertTrue(nodeset < NodeSet("artcore[2-32000]-ib0,lounge[35-65/2]"))
        self.assertFalse(nodeset < NodeSet("artcore[3-999]-ib0"))
        self.assertFalse(nodeset < NodeSet("artcore[3-980]-ib0"))
        self.assertFalse(nodeset < NodeSet("artcore[2-998]-ib0"))
        self.assertTrue(nodeset <= NodeSet("artcore[2-32000]-ib0"))
        self.assertTrue(nodeset <= NodeSet("artcore[2-32000]-ib0,lounge[35-65/2]"))
        self.assertTrue(nodeset <= NodeSet("artcore[3-999]-ib0"))
        self.assertFalse(nodeset <= NodeSet("artcore[3-980]-ib0"))
        self.assertFalse(nodeset <= NodeSet("artcore[2-998]-ib0"))
        self.assertEqual(len(nodeset), 997)
        # check padding issue - since 1.6 padding is ignored in this case
        self.assertTrue(nodeset.issubset("artcore[0001-1000]-ib0"))
        self.assertFalse(nodeset.issubset("artcore030-ib0"))
        # multiple patterns case
        nodeset = NodeSet("tronic[0036-1630],lounge[20-660/2]")
        self.assert_(nodeset < NodeSet("tronic[0036-1630],lounge[20-662/2]"))
        self.assert_(nodeset < NodeSet("tronic[0035-1630],lounge[20-660/2]"))
        self.assert_(not nodeset < NodeSet("tronic[0035-1630],lounge[22-660/2]"))
        self.assert_(nodeset < NodeSet("tronic[0036-1630],lounge[20-660/2],artcore[034-070]"))
        self.assert_(nodeset < NodeSet("tronic[0032-1880],lounge[2-700/2],artcore[039-040]"))
        self.assert_(nodeset.issubset("tronic[0032-1880],lounge[2-700/2],artcore[039-040]"))
        self.assert_(nodeset.issubset(NodeSet("tronic[0032-1880],lounge[2-700/2],artcore[039-040]")))

    def test_nd_intersection(self):
        ns1 = NodeSet("a0b[1-2]")
        ns2 = NodeSet("a0b1")
        self.assertEqual(ns1.intersection(ns2), ns2)
        self.assertEqual(ns1.intersection(ns2), NodeSet("a0b1"))
        self.assertEqual(len(ns1.intersection(ns2)), 1)
        ns1 = NodeSet("a0b[1-2]")
        ns2 = NodeSet("a3b0,a0b1")
        self.assertEqual(ns1.intersection(ns2), NodeSet("a0b1"))
        self.assertEqual(len(ns1.intersection(ns2)), 1)
        ns1 = NodeSet("a[0-100]b[1-2]")
        ns2 = NodeSet("a[50-150]b[2]")
        self.assertEqual(ns1.intersection(ns2), NodeSet("a[50-100]b2"))
        self.assertEqual(len(ns1.intersection(ns2)), 51)

    def test_nd_nonoverlap(self):
        ns1 = NodeSet("a[0-2]b[1-3]c[4]")
        ns1.add("a[0-1]b[2-3]c[4-5]")
        self.assertEqual(str(ns1), "a[0-1]b[2-3]c[4-5],a[0-2]b1c4,a2b[2-3]c4")
        self.assertEqual(len(ns1), 13)

        ns1 = NodeSet("a[0-1]b[2-3]c[4-5]")
        ns1.add("a[0-2]b[1-3]c[4]")
        self.assertEqual(str(ns1), "a[0-1]b[2-3]c[4-5],a[0-2]b1c4,a2b[2-3]c4")
        self.assertEqual(len(ns1), 13)

        ns1 = NodeSet("a[0-2]b[1-3]c[4],a[0-1]b[2-3]c[4-5]")
        self.assertEqual(str(ns1), "a[0-1]b[2-3]c[4-5],a[0-2]b1c4,a2b[2-3]c4")
        self.assertEqual(len(ns1), 13)

        ns1 = NodeSet("a[0-2]b[1-3]c[4-6],a[0-1]b[2-3]c[4-5]")
        self.assertEqual(str(ns1), "a[0-2]b[1-3]c[4-6]")
        self.assertEqual(len(ns1), 3*3*3)

        ns1 = NodeSet("a[0-2]b[2-3]c[4-6],a[0-1]b[1-3]c[4-5]")
        self.assertEqual(str(ns1), "a[0-2]b[2-3]c[4-6],a[0-1]b1c[4-5]")
        self.assertEqual(ns1, NodeSet("a[0-1]b[1-3]c[4-5],a[0-2]b[2-3]c6,a2b[2-3]c[4-5]"))
        self.assertEqual(ns1, NodeSet("a[0-2]b[2-3]c[4-6],a[0-1]b1c[4-5]"))
        self.assertEqual(len(ns1), (3*2*3)+(2*1*2))

        ns1 = NodeSet("a[0-2]b[2-3]c[4-6],a[0-1]b[1-3]c[4-5]")
        self.assertEqual(str(ns1), "a[0-2]b[2-3]c[4-6],a[0-1]b1c[4-5]")
        self.assertEqual(NodeSet("a[0-1]b[1-3]c[4-5],a[0-2]b[2-3]c6,a2b[2-3]c[4-5]"), NodeSet("a[0-2]b[2-3]c[4-6],a[0-1]b1c[4-5]"))
        self.assertEqual(ns1, NodeSet("a[0-2]b[2-3]c[4-6],a[0-1]b1c[4-5]"))
        self.assertEqual(ns1, NodeSet("a[0-1]b[1-3]c[4-5],a[0-2]b[2-3]c6,a2b[2-3]c[4-5]"))
        self.assertEqual(len(ns1), (3*2*3)+(2*1*2))

        ns1 = NodeSet("a[0-2]b[2-3]c[4-6],a[0-1]b[1-3]c[4-5],a2b1c[4-6]")
        self.assertEqual(str(ns1), "a[0-2]b[2-3]c[4-6],a[0-1]b1c[4-5],a2b1c[4-6]")
        self.assertEqual(ns1, NodeSet("a[0-1]b[1-3]c[4-5],a[0-2]b[2-3]c6,a2b[2-3]c[4-5],a2b1c[4-6]"))
        self.assertEqual(ns1, NodeSet("a[0-2]b[2-3]c[4-6],a[0-1]b1c[4-5],a2b1c[4-6]"))
        self.assertEqual(len(ns1), (3*3*2)+1+(3*2*1))
        ns1.add("a1b1c6")
        self.assertEqual(str(ns1), "a[0-2]b[2-3]c[4-6],a[0-1]b1c[4-5],a2b1c[4-6],a1b1c6")
        self.assertEqual(ns1, NodeSet("a[0-2]b[2-3]c[4-6],a[0-1]b1c[4-5],a2b1c[4-6],a1b1c6"))
        ns1.add("a0b1c6")
        self.assertEqual(str(ns1), "a[0-2]b[1-3]c[4-6]")
        self.assertEqual(ns1, NodeSet("a[0-2]b[1-3]c[4-6]"))
        self.assertEqual(ns1, NodeSet("a[0-1]b[1-3]c[4-5],a[0-2]b[2-3]c6,a2b[2-3]c[4-5],a2b1c[4-6],a[0-1]b1c6"))
        self.assertEqual(len(ns1), 3*3*3)

    def test_nd_difference(self):
        ns1 = NodeSet("a0b[1-2]")
        ns2 = NodeSet("a0b1")
        self.assertEqual(ns1.difference(ns2), NodeSet("a0b2"))
        self.assertEqual(len(ns1.difference(ns2)), 1)

        ns1 = NodeSet("a[0-2]b[1-3]c[4-5]")
        ns2 = NodeSet("a[0-2]b[1-3]c4")
        self.assertEqual(str(ns1.difference(ns2)), "a[0-2]b[1-3]c5")
        self.assertEqual(ns1.difference(ns2), NodeSet("a[0-2]b[1-3]c5"))
        self.assertEqual(len(ns1.difference(ns2)), 9)

        ns1 = NodeSet("a[0-2]b[1-3]c[4]")
        ns2 = NodeSet("a[0-3]b[1]c[4-5]")
        self.assertEqual(ns1.difference(ns2), NodeSet("a[0-2]b[2-3]c4"))
        self.assertEqual(len(ns1.difference(ns2)), 6)

        ns1 = NodeSet("a[0-2]b[1-3]c[4],a[0-1]b[2-3]c[4-5]")
        self.assertEqual(str(ns1), "a[0-1]b[2-3]c[4-5],a[0-2]b1c4,a2b[2-3]c4")

        self.assertEqual(len(ns1), 3*3 + 2*2)
        ns2 = NodeSet("a[0-3]b[1]c[4-5]")
        self.assertEqual(len(ns2), 4*2)
        self.assertEqual(str(ns1.difference(ns2)), "a[0-1]b[2-3]c[4-5],a2b[2-3]c4")
        # compare object with different str repr
        self.assertNotEqual(str(ns1.difference(ns2)), "a[0-2]b[2-3]c4,a[0-1]b[2-3]c5")
        self.assertEqual(ns1.difference(ns2), NodeSet("a[0-2]b[2-3]c4,a[0-1]b[2-3]c5"))
        self.assertEqual(len(ns1.difference(ns2)), 3*2+2*2)

        ns1 = NodeSet("a[0-3]b[1-5]c5")
        ns2 = NodeSet("a[0-2]b[2-4]c5")
        self.assertEqual(str(ns1.difference(ns2)), "a[0-3]b[1,5]c5,a3b[2-4]c5")

        ns1 = NodeSet("a[0-3]b2c5")
        ns2 = NodeSet("a[0-2]b1c5")
        self.assertEqual(str(ns1.difference(ns2)), "a[0-3]b2c5")

        ns1 = NodeSet("a[0-3]b[1-4]c[5]")
        ns2 = NodeSet("a[0-2]b1c5")
        self.assertEqual(str(ns1.difference(ns2)), "a[0-3]b[2-4]c5,a3b1c5")

        ns1 = NodeSet("a[0-2]b[1-4]c5")
        ns2 = NodeSet("a[0-3]b[2-3]c5")
        self.assertEqual(str(ns1.difference(ns2)), "a[0-2]b[1,4]c5")

        ns1 = NodeSet("a[0-2]b1c5")
        ns2 = NodeSet("a[0-3]b[1-4]c[5]")
        self.assertEqual(str(ns1.difference(ns2)), "")

        ns1 = NodeSet("a[1-4]b1c5")
        ns2 = NodeSet("a[0-3]b1c5")
        self.assertEqual(str(ns1.difference(ns2)), "a4b1c5")

        ns1 = NodeSet("a[0-2]b1c[5-6]")
        ns2 = NodeSet("a[0-3]b[1-4]c[5]")
        self.assertEqual(str(ns1.difference(ns2)), "a[0-2]b1c6")

        ns1 = NodeSet("a[0-2]b[1-3]c[5]")
        ns2 = NodeSet("a[0-3]b[1-4]c[5]")
        self.assertEqual(ns1.difference(ns2), NodeSet())
        self.assertEqual(len(ns1.difference(ns2)), 0)

    def test_nd_difference_test(self):
        #ns1 = NodeSet("a2b4")
        #ns2 = NodeSet("a2b6")
        #nsdiff = ns1.difference(ns2)
        #self.assertEqual(str(nsdiff), "a2b4")
        #self.assertEqual(nsdiff, NodeSet("a2b4"))

        ns1 = NodeSet("a[1-10]b[1-10]")
        ns2 = NodeSet("a[5-20]b[5-20]")
        nsdiff = ns1.difference(ns2)
        self.assertEqual(str(nsdiff), "a[1-10]b[1-4],a[1-4]b[5-10]")
        self.assertEqual(nsdiff, NodeSet("a[1-4]b[1-10],a[1-10]b[1-4]")) # manually checked with overlap

        # node[1-100]x[1-10] -x node4x4


    def test_nd_difference_m(self):
        ns1 = NodeSet("a[2-3,5]b[1,4],a6b5")
        ns2 = NodeSet("a5b4,a6b5")
        nsdiff = ns1.difference(ns2)
        self.assertEqual(str(nsdiff), "a[2-3]b[1,4],a5b1")
        self.assertEqual(nsdiff, NodeSet("a[2-3]b[1,4],a5b1"))
        self.assertEqual(nsdiff, NodeSet("a[2-3,5]b1,a[2-3]b4"))

        # same with difference_update:
        ns1 = NodeSet("a[2-3,5]b[1,4],a6b5")
        ns2 = NodeSet("a5b4,a6b5")
        ns1.difference_update(ns2)
        self.assertEqual(str(ns1), "a[2-3]b[1,4],a5b1")
        self.assertEqual(ns1, NodeSet("a[2-3]b[1,4],a5b1"))
        self.assertEqual(ns1, NodeSet("a[2-3,5]b1,a[2-3]b4"))

        ns1 = NodeSet("a[2-3,5]b[1,4]p1,a6b5p1")
        ns2 = NodeSet("a5b4p1,a6b5p1")
        nsdiff = ns1.difference(ns2)
        self.assertEqual(str(nsdiff), "a[2-3]b[1,4]p1,a5b1p1")
        self.assertEqual(nsdiff, NodeSet("a[2-3]b[1,4]p1,a5b1p1"))
        self.assertEqual(nsdiff, NodeSet("a[2-3,5]b1p1,a[2-3]b4p1")) # manually checked

        ns1 = NodeSet("a[2-3]b[0,3-4],a[6-10]b[0-2]")
        ns2 = NodeSet("a[3-6]b[2-3]")
        nsdiff = ns1.difference(ns2)
        self.assertEqual(str(nsdiff), "a[7-10]b[0-2],a[2-3]b[0,4],a6b[0-1],a2b3")
        self.assertEqual(nsdiff, NodeSet("a[7-10]b[0-2],a[2-3]b[0,4],a6b[0-1],a2b3"))
        self.assertEqual(nsdiff, NodeSet("a[2-3,6-10]b0,a[6-10]b1,a[7-10]b2,a2b3,a[2-3]b4")) # manually checked

        ns1 = NodeSet("a[2-3,5]b4c[1,4],a6b4c5")
        ns2 = NodeSet("a5b4c4,a6b4c5")
        nsdiff = ns1.difference(ns2)
        self.assertEqual(str(nsdiff), "a[2-3]b4c[1,4],a5b4c1")
        self.assertEqual(nsdiff, NodeSet("a[2-3]b4c[1,4],a5b4c1"))
        self.assertEqual(nsdiff, NodeSet("a[2-3,5]b4c1,a[2-3]b4c4"))

        ns1 = NodeSet("a[1-6]b4")
        ns2 = NodeSet("a5b[2-5]")
        nsdiff = ns1.difference(ns2)
        self.assertEqual(str(nsdiff), "a[1-4,6]b4")
        self.assertEqual(nsdiff, NodeSet("a[1-4,6]b4"))

    def test_nd_xor(self):
        nodeset = NodeSet("artcore[3-999]p1")
        self.assertEqual(len(nodeset), 997)
        nodeset.symmetric_difference_update("artcore[1-2000]p1")
        self.assertEqual(str(nodeset), "artcore[1-2,1000-2000]p1")
        self.assertEqual(len(nodeset), 1003)
        nodeset = NodeSet("artcore[3-999]p1,lounge")
        self.assertEqual(len(nodeset), 998)
        nodeset.symmetric_difference_update("artcore[1-2000]p1")
        self.assertEqual(len(nodeset), 1004)
        self.assertEqual(str(nodeset), "artcore[1-2,1000-2000]p1,lounge")
        nodeset = NodeSet("artcore[3-999]p1,lounge")
        self.assertEqual(len(nodeset), 998)
        nodeset.symmetric_difference_update("artcore[1-2000]p1,lounge")
        self.assertEqual(len(nodeset), 1003)
        self.assertEqual(str(nodeset), "artcore[1-2,1000-2000]p1")
        nodeset = NodeSet("artcore[3-999]p1,lounge")
        self.assertEqual(len(nodeset), 998)
        nodeset2 = NodeSet("artcore[1-2000]p1,lounge")
        nodeset.symmetric_difference_update(nodeset2)
        self.assertEqual(len(nodeset), 1003)
        self.assertEqual(str(nodeset), "artcore[1-2,1000-2000]p1")
        self.assertEqual(len(nodeset2), 2001) # check const argument
        nodeset.symmetric_difference_update("artcore[1-2000]p1,lounge")
        self.assertEqual(len(nodeset), 998)
        self.assertEqual(str(nodeset), "artcore[3-999]p1,lounge")
        #
        first = NodeSet("a[2-3,5]b[1,4],a6b5")
        second = NodeSet("a[4-6]b[3-6]")
        first.symmetric_difference_update(second)
        self.assertEqual(str(first), "a[4-6]b[3,6],a[2-3]b[1,4],a4b[4-5],a5b[1,5],a6b4")
        self.assertEqual(first, NodeSet("a[4-6]b[3,6],a[2-3]b[1,4],a4b[4-5],a5b[1,5],a6b4"))

        first = NodeSet("a[1-50]b[1-20]")
        second = NodeSet("a[40-60]b[10-30]")
        first.symmetric_difference_update(second)
        self.assertEqual(str(first), "a[1-39]b[1-20],a[40-60]b[21-30],a[51-60]b[10-20],a[40-50]b[1-9]")
        self.assertEqual(first, NodeSet("a[1-39]b[1-20],a[51-60]b[10-30],a[40-50]b[1-9,21-30]"))

        first = NodeSet("artcore[3-999]p[1-99,500-598]")
        second = NodeSet("artcore[1-2000]p[40-560]")
        first.symmetric_difference_update(second)
        self.assertEqual(str(first), "artcore[1-2000]p[100-499],artcore[1-2,1000-2000]p[40-99,500-560],artcore[3-999]p[1-39,561-598]")
        self.assertEqual(first, NodeSet("artcore[1-2000]p[100-499],artcore[1-2,1000-2000]p[40-99,500-560],artcore[3-999]p[1-39,561-598]"))

        ns1 = NodeSet("a[1-6]b4")
        ns2 = NodeSet("a5b[2-5]")
        ns1.symmetric_difference_update(ns2)
        self.assertEqual(str(ns1), "a[1-4,6]b4,a5b[2-3,5]")
        self.assertEqual(ns1, NodeSet("a[1-4,6]b4,a5b[2-3,5]"))



if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(NodeSetTest)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = RangeSetErrorTest
#!/usr/bin/env python
# ClusterShell.NodeSet.RangeSet error handling test suite
# Written by S. Thiell 2008-09-28


"""Unit test for RangeSet errors"""

import copy
import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.NodeSet import RangeSet
from ClusterShell.NodeSet import RangeSetParseError


class RangeSetErrorTest(unittest.TestCase):

    def _testRS(self, r, exc):
        try:
            rset = RangeSet(r)
            print rset
        except RangeSetParseError, e:
            self.assertEqual(RangeSetParseError, exc)
            return
        except:
            raise
        self.assert_(0, "error not detected/no exception raised")
            

    def testBadUsages(self):
        """test parse errors"""
        self._testRS("", RangeSetParseError)
        self._testRS("-", RangeSetParseError)
        self._testRS("A", RangeSetParseError)
        self._testRS("2-5/a", RangeSetParseError)
        self._testRS("3/2", RangeSetParseError)
        self._testRS("3-/2", RangeSetParseError)
        self._testRS("-3/2", RangeSetParseError)
        self._testRS("-/2", RangeSetParseError)
        self._testRS("4-a/2", RangeSetParseError)
        self._testRS("4-3/2", RangeSetParseError)
        self._testRS("4-5/-2", RangeSetParseError)
        self._testRS("4-2/-2", RangeSetParseError)
        self._testRS("004-002", RangeSetParseError)
        self._testRS("3-59/2,102a", RangeSetParseError)




if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(RangeSetErrorTest)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = RangeSetNDTest
#!/usr/bin/env python
# ClusterShell.RangeSet.RangeSetND test suite
# Written by S. Thiell


"""Unit test for RangeSetND"""

import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.RangeSet import RangeSet, RangeSetND


class RangeSetNDTest(unittest.TestCase):

    def _testRS(self, test, res, length):
        r1 = RangeSetND(test, autostep=3)
        self.assertEqual(str(r1), res)
        self.assertEqual(len(r1), length)

    def test_simple(self):
        # Test constructors
        self._testRS(None, "", 0)
        self._testRS([[ "0-10" ], [ "40-60" ]], "0-10,40-60\n", 32)
        self._testRS([[ "0-2", "1-2" ], [ "10", "3-5" ]], "0-2; 1-2\n10; 3-5\n", 9)
        self._testRS([[ 0, 1 ], [ 0, 2 ], [ 2, 2 ], [ 2, 1 ], [ 1, 1 ], [ 1, 2 ], [ 10, 4 ], [ 10, 5 ], [ 10, 3 ]], "0-2; 1-2\n10; 3-5\n", 9)
        self._testRS([(0, 4), (0, 5), (1, 4), (1, 5)], "0-1; 4-5\n", 4)
        # construct with copy_rangeset=False
        r0 = RangeSet("0-10,30-40,50")
        r1 = RangeSet("200-202")
        rn = RangeSetND([[r0, r1]], copy_rangeset=False)
        self.assertEqual(str(rn), "0-10,30-40,50; 200-202\n")
        self.assertEqual(len(rn), 69)

    def test_vectors(self):
        rn = RangeSetND([[ "0-10", "1-2" ], [ "5-60", "2" ]])
        # vectors() should perform automatic folding
        self.assertEqual([[RangeSet("0-60"), RangeSet("2")], [RangeSet("0-10"), RangeSet("1")]], list(rn.vectors()))
        self.assertEqual(str(rn), "0-60; 2\n0-10; 1\n")
        self.assertEqual(len(rn), 72)

    def test_nonzero(self):
        r0 = RangeSetND()
        if r0:
            self.assertFalse("nonzero failed")
        r1 = RangeSetND([[ "0-10" ], [ "40-60" ]])
        if not r1:
            self.assertFalse("nonzero failed")

    def test_eq(self):
        r0 = RangeSetND()
        r1 = RangeSetND()
        r2 = RangeSetND([[ "0-10", "1-2" ], [ "40-60", "1-3" ]])
        r3 = RangeSetND([[ "0-10" ], [ "40-60" ]])
        self.assertEqual(r0, r1)
        self.assertNotEqual(r0, r2)
        self.assertNotEqual(r0, r3)
        self.assertNotEqual(r2, r3)
        self.assertFalse(r3 == "foobar") # NotImplemented => object address comparison

    def test_dim(self):
        r0 = RangeSetND()
        self.assertEqual(r0.dim(), 0)
        r1 = RangeSetND([[ "0-10", "1-2" ], [ "40-60", "1-3" ]])
        self.assertEqual(r1.dim(), 2)

    def test_fold(self):
        r1 = RangeSetND([[ "0-10", "1-2" ], [ "5-15,40-60", "1-3" ], [ "0-4", "3" ]])
        r1.fold()
        self.assertEqual(str(r1._veclist), "[[0-15,40-60, 1-3]]")
        self.assertEqual(str(r1), "0-15,40-60; 1-3\n")

    def test_contains(self):
        r1 = RangeSetND([[ "0-10" ], [ "40-60" ]])
        r2 = RangeSetND()
        self.assertTrue(r2 in r1) # <=> issubset()
        r1 = RangeSetND()
        r2 = RangeSetND([[ "0-10" ], [ "40-60" ]])
        self.assertFalse(r2 in r1)
        r1 = RangeSetND([[ "0-10" ], [ "40-60" ]])
        r2 = RangeSetND([[ "4-8" ], [ "10,40-41" ]])
        self.assertTrue(r2 in r1)
        r1 = RangeSetND([[ "0-10", "1-2" ], [ "40-60", "2-5" ]])
        r2 = RangeSetND([[ "4-8", "1" ], [ "10,40-41", "2" ]])
        self.assertTrue(r2 in r1)
        r1 = RangeSetND([[ "0-10", "1-2" ], [ "40-60", "2-5" ]])
        r2 = RangeSetND([[ "4-8", "5" ], [ "10,40-41", "2" ]])
        self.assertTrue(r2 not in r1)
        r1 = RangeSetND([[ "0-10" ], [ "40-60" ]])
        self.assertTrue("10" in r1)
        self.assertTrue(10 in r1)
        self.assertFalse(11 in r1)

    def test_subset_superset(self):
        r1 = RangeSetND([[ "0-10" ], [ "40-60" ]])
        self.assertTrue(r1.issubset(r1))
        self.assertTrue(r1.issuperset(r1))
        r2 = RangeSetND([[ "0-10" ], [ "40-60" ]])
        self.assertTrue(r2.issubset(r1))
        self.assertTrue(r1.issubset(r2))
        self.assertTrue(r2.issuperset(r1))
        self.assertTrue(r1.issuperset(r2))
        r1 = RangeSetND([[ "0-10" ], [ "40-60" ]])
        r2 = RangeSetND()
        self.assertTrue(r2.issubset(r1))
        self.assertFalse(r1.issubset(r2))
        self.assertTrue(r1.issuperset(r2))
        self.assertFalse(r2.issuperset(r1))
        r1 = RangeSetND([[ "0-10" ], [ "40-60" ]])
        r2 = RangeSetND([[ "4" ], [ "10,40-41" ]])
        self.assertFalse(r1.issubset(r2))
        self.assertFalse(r1 < r2)
        self.assertTrue(r2.issubset(r1))
        self.assertTrue(r2 < r1)
        self.assertTrue(r1.issuperset(r2))
        self.assertTrue(r1 > r2)
        self.assertFalse(r2.issuperset(r1))
        self.assertFalse(r2 > r1)
        r1 = RangeSetND([[ "0-10", "1-2" ], [ "40-60", "2-5" ]])
        r2 = RangeSetND([[ "4-8", "1" ], [ "10,40-41", "2" ]])
        self.assertFalse(r1.issubset(r2))
        self.assertFalse(r1 < r2)
        self.assertTrue(r2.issubset(r1))
        self.assertTrue(r2 < r1)
        self.assertTrue(r1.issuperset(r2))
        self.assertTrue(r1 > r2)
        self.assertFalse(r2.issuperset(r1))
        self.assertFalse(r2 > r1)

    def test_sorting(self):
        # Test internal sorting algo
        # sorting condition (1) -- see RangeSetND._sort()
        self._testRS([[ "40-60", "5" ], [ "10-12", "6" ]], "40-60; 5\n10-12; 6\n", 24)
        # sorting condition (2)
        self._testRS([[ "40-42", "5,7" ], [ "10-12", "6" ]], "40-42; 5,7\n10-12; 6\n", 9)
        self._testRS([[ "40-42", "5" ], [ "10-12", "6-7" ]], "10-12; 6-7\n40-42; 5\n", 9)
        # sorting condition (3)
        self._testRS([[ "40-60", "5" ], [ "10-30", "6" ]], "10-30; 6\n40-60; 5\n", 42)
        self._testRS([[ "10-30", "3", "5" ], [ "10-30", "2", "6" ]], "10-30; 2; 6\n10-30; 3; 5\n", 42)
        self._testRS([[ "10-30", "2", "6" ], [ "10-30", "3", "5" ]], "10-30; 2; 6\n10-30; 3; 5\n", 42)
        # sorting condition (4)
        self._testRS([[ "10-30", "2,6", "6" ], [ "10-30", "2-3", "5" ]], "10-30; 2-3; 5\n10-30; 2,6; 6\n", 84)
        # the following test triggers folding loop protection
        self._testRS([[ "40-60", "5" ], [ "30-50", "6" ]], "30-50; 6\n40-60; 5\n", 42)
        # 1D
        self._testRS([[ "40-60" ], [ "10-12" ]], "10-12,40-60\n", 24)

    def test_folding(self):
        self._testRS([[ "0-10" ], [ "11-60" ]],
                     "0-60\n", 61)
        self._testRS([[ "0-2", "1-2" ], [ "3", "1-2" ]],
                     "0-3; 1-2\n", 8)
        self._testRS([[ "3", "1-3" ], [ "0-2", "1-2" ]],
                     "0-2; 1-2\n3; 1-3\n", 9)
        self._testRS([[ "0-2", "1-2" ], [ "3", "1-3" ]],
                     "0-2; 1-2\n3; 1-3\n", 9)
        self._testRS([[ "0-2", "1-2" ], [ "1-3", "1-3" ]],
                     "1-2; 1-3\n0,3; 1-2\n3; 3\n", 11)
        self._testRS([[ "0-2", "1-2", "0-4" ], [ "3", "1-2", "0-5" ]],
                     "0-2; 1-2; 0-4\n3; 1-2; 0-5\n", 42)
        self._testRS([[ "0-2", "1-2", "0-4" ], [ "1-3", "1-3", "0-4" ]],
                     "1-2; 1-3; 0-4\n0,3; 1-2; 0-4\n3; 3; 0-4\n", 55)
        # the following test triggers folding loop protection
        self._testRS([[ "0-100", "50-200" ], [ "2-101", "49" ]],
                     "0-100; 50-200\n2-101; 49\n", 15351)
        # the following test triggers full expand
        veclist = []
        for v1, v2, v3 in zip(range(30), range(5, 35), range(10, 40)):
            veclist.append((v1, v2, v3))
        self._testRS(veclist, "0; 5; 10\n1; 6; 11\n2; 7; 12\n3; 8; 13\n4; 9; 14\n5; 10; 15\n6; 11; 16\n7; 12; 17\n8; 13; 18\n9; 14; 19\n10; 15; 20\n11; 16; 21\n12; 17; 22\n13; 18; 23\n14; 19; 24\n15; 20; 25\n16; 21; 26\n17; 22; 27\n18; 23; 28\n19; 24; 29\n20; 25; 30\n21; 26; 31\n22; 27; 32\n23; 28; 33\n24; 29; 34\n25; 30; 35\n26; 31; 36\n27; 32; 37\n28; 33; 38\n29; 34; 39\n", 30)

    def test_union(self):
        rn1 = RangeSetND([[ "10-100", "1-3" ], [ "1100-1300", "2-3" ]])
        self.assertEqual(str(rn1), "1100-1300; 2-3\n10-100; 1-3\n")
        self.assertEqual(len(rn1), 675)
        rn2 = RangeSetND([[ "1100-1200", "1" ], [ "10-49", "1,3" ]])
        self.assertEqual(str(rn2), "1100-1200; 1\n10-49; 1,3\n")
        self.assertEqual(len(rn2), 181)
        rnu = rn1.union(rn2)
        self.assertEqual(str(rnu), "1100-1300; 2-3\n10-100; 1-3\n1100-1200; 1\n")
        self.assertEqual(len(rnu), 776)
        rnu2 = rn1 | rn2
        self.assertEqual(str(rnu2), "1100-1300; 2-3\n10-100; 1-3\n1100-1200; 1\n")
        self.assertEqual(len(rnu2), 776)
        self.assertEqual(rnu, rnu2) # btw test __eq__
        self.assertNotEqual(rnu, rn1) # btw test __eq__
        self.assertNotEqual(rnu, rn2) # btw test __eq__
        try:
            rn1 | "foobar"
            self.assertFalse("TypeError not raised")
        except TypeError:
            pass
        # binary error
        if sys.version_info >= (2,5,0):
            rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ]])
            rn2 = RangeSetND([[ "1100-1200", "1" ], [ "10-49", "1,3" ]])
            rn1 |= rn2
            self.assertEqual(str(rn2), "1100-1200; 1\n10-49; 1,3\n")
            self.assertEqual(len(rn2), 181)
            rn2 = set([3, 5])
            self.assertRaises(TypeError, rn1.__ior__, rn2)

    def test_difference(self):
        rn1 = RangeSetND([[ "10", "10-13" ], [ "0-3", "1-2" ]])
        rn2 = RangeSetND([[ "10", "12" ]])
        self.assertEqual(len(rn1), 12)
        rnres = rn1.difference(rn2)
        self.assertEqual(str(rnres), "0-3; 1-2\n10; 10-11,13\n")
        self.assertEqual(len(rnres), 11)

        rn1 = RangeSetND([[ "0-2", "1-3", "4-5" ]])
        rn2 = RangeSetND([[ "0-2", "1-3", "4" ]])
        rnres = rn1.difference(rn2)
        self.assertEqual(str(rnres), "0-2; 1-3; 5\n")
        self.assertEqual(len(rnres), 9)

        rn1 = RangeSetND([[ "0-2", "1-3", "4-5" ]])
        rn2 = RangeSetND([[ "10-40", "20-120", "0-100"]])
        rnres = rn1.difference(rn2)
        self.assertEqual(str(rnres), "0-2; 1-3; 4-5\n")
        self.assertEqual(len(rnres), 18)

        rn1 = RangeSetND([[ "0-2", "1-3", "4-5" ]])
        rn2 = RangeSetND([[ "10-40", "20-120", "100-200"]])
        rnres = rn1.difference(rn2)
        self.assertEqual(str(rnres), "0-2; 1-3; 4-5\n")
        self.assertEqual(len(rnres), 18)

        rnres2 = rn1 - rn2
        self.assertEqual(str(rnres2), "0-2; 1-3; 4-5\n")
        self.assertEqual(len(rnres2), 18)
        self.assertEqual(rnres, rnres2) # btw test __eq__

        try:
            rn1 - "foobar"
            self.assertFalse("TypeError not raised")
        except TypeError:
            pass


    def test_difference_update(self):
        rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ]])
        rn2 = RangeSetND([[ "10", "10" ]])
        rn1.difference_update(rn2)
        self.assertEqual(len(rn1), 4)
        self.assertEqual(str(rn1), "10; 9,11-13\n")

        rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ], [ "8-9", "12-15" ]])
        rn2 = RangeSetND([[ "10", "10" ], [ "9", "12-15" ]])
        rn1.difference_update(rn2)
        self.assertEqual(len(rn1), 8)
        self.assertEqual(str(rn1), "8; 12-15\n10; 9,11-13\n")

        rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ], [ "8-9", "12-15" ]])
        rn2 = RangeSetND([[ "10", "10" ], [ "9", "12-15" ], [ "10-12", "11-15" ], [ "11", "14" ]])
        rn1.difference_update(rn2)
        self.assertEqual(len(rn1), 5)
        self.assertEqual(str(rn1), "8; 12-15\n10; 9\n")

        rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ], [ "8-9", "12-15" ], [ "10", "10-13" ], [ "10", "12-16" ], [ "9", "13-16" ]])
        rn2 = RangeSetND([[ "10", "10" ], [ "9", "12-15" ], [ "10-12", "11-15" ], [ "11", "14" ]])
        rn1.difference_update(rn2)
        self.assertEqual(len(rn1), 7)
        # no pre-fold (self._veclist)
        self.assertEqual(str(rn1), "8; 12-15\n9-10; 16\n10; 9\n")
        # pre-fold (self.veclist)
        #self.assertEqual(str(rn1), "8; 12-15\n10; 9,16\n9; 16\n")

        # strict mode
        rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ], [ "8-9", "12-15" ]])
        rn2 = RangeSetND([[ "10", "10" ], [ "9", "12-15" ], [ "10-12", "11-15" ], [ "11", "14" ]])
        self.assertRaises(KeyError, rn1.difference_update, rn2, strict=True)

        if sys.version_info >= (2,5,0):
            rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ]])
            rn2 = RangeSetND([[ "10", "10" ]])
            rn1 -= rn2
            self.assertEqual(str(rn1), "10; 9,11-13\n")
            self.assertEqual(len(rn1), 4)
            # binary error
            rn2 = set([3, 5])
            self.assertRaises(TypeError, rn1.__isub__, rn2)

    def test_intersection(self):
        rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ], [ "8-9", "12-15" ]])
        self.assertEqual(len(rn1), 13)
        self.assertEqual(str(rn1), "8-9; 12-15\n10; 9-13\n")
        rn2 = RangeSetND([[ "10", "10" ], [ "9", "12-15" ]])
        self.assertEqual(len(rn2), 5)
        self.assertEqual(str(rn2), "9; 12-15\n10; 10\n")
        rni = rn1.intersection(rn2)
        self.assertEqual(len(rni), 5)
        self.assertEqual(str(rni), "9; 12-15\n10; 10\n")
        self.assertEqual(len(rn1), 13)
        self.assertEqual(str(rn1), "8-9; 12-15\n10; 9-13\n")
        self.assertEqual(len(rn2), 5)
        self.assertEqual(str(rn2), "9; 12-15\n10; 10\n")
        # test __and__
        rni2 = rn1 & rn2
        self.assertEqual(len(rni2), 5)
        self.assertEqual(str(rni2), "9; 12-15\n10; 10\n")
        self.assertEqual(len(rn1), 13)
        self.assertEqual(str(rn1), "8-9; 12-15\n10; 9-13\n")
        self.assertEqual(len(rn2), 5)
        self.assertEqual(str(rn2), "9; 12-15\n10; 10\n")
        self.assertEqual(rni, rni2) # btw test __eq__
        try:
            rn1 & "foobar"
            self.assertFalse("TypeError not raised")
        except TypeError:
            pass

    def test_intersection_update(self):
        rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ]])
        self.assertEqual(len(rn1), 5)
        self.assertEqual(str(rn1), "10; 9-13\n")
        # self test:
        rn1.intersection_update(rn1)
        self.assertEqual(len(rn1), 5)
        self.assertEqual(str(rn1), "10; 9-13\n")
        #
        rn2 = RangeSetND([[ "10", "10" ]])
        rn1.intersection_update(rn2)
        self.assertEqual(len(rn1), 1)
        self.assertEqual(str(rn1), "10; 10\n")

        rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ], [ "8-9", "12-15" ]])
        rn2 = RangeSetND([[ "10", "10" ], [ "9", "12-15" ]])
        rn1.intersection_update(rn2)
        self.assertEqual(len(rn1), 5)
        self.assertEqual(str(rn1), "9; 12-15\n10; 10\n")

        rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ], [ "8-9", "12-15" ]])
        rn2 = RangeSetND([[ "10", "10" ], [ "9", "12-15" ], [ "10-12", "11-15" ], [ "11", "14" ]])
        rn1.intersection_update(rn2)
        self.assertEqual(len(rn1), 8)
        self.assertEqual(str(rn1), "9; 12-15\n10; 10-13\n")

        rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ], [ "8-9", "12-15" ], [ "10", "10-13" ], [ "10", "12-16" ], [ "9", "13-16" ]])
        rn2 = RangeSetND([[ "10", "10" ], [ "9", "12-15" ], [ "10-12", "11-15" ], [ "11", "14" ]])
        rn1.intersection_update(rn2)
        self.assertEqual(len(rn1), 10)
        self.assertEqual(str(rn1), "10; 10-15\n9; 12-15\n")

        rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ], [ "8-9", "12-15" ], [ "10", "10-13" ], [ "10", "12-16" ], [ "9", "13-16" ]])
        rn2 = RangeSetND([[ "10", "10" ], [ "9", "12-16" ], [ "10-12", "11-15" ], [ "11", "14" ], [ "8", "10-20" ]])
        rn1.intersection_update(rn2)
        self.assertEqual(len(rn1), 15)
        # no pre-fold (self._veclist)
        self.assertEqual(str(rn1), "10; 10-15\n9; 12-16\n8; 12-15\n")
        # pre-fold (self.veclist)
        #self.assertEqual(str(rn1), "8-9; 12-15\n10; 10-15\n9; 16\n")

        # binary error
        if sys.version_info >= (2,5,0):
            rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ]])
            rn2 = RangeSetND([[ "10", "10" ]])
            rn1 &= rn2
            self.assertEqual(len(rn1), 1)
            self.assertEqual(str(rn1), "10; 10\n")
            rn2 = set([3, 5])
            self.assertRaises(TypeError, rn1.__iand__, rn2)

    def test_xor(self):
        rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ]])
        rn2 = RangeSetND([[ "10", "10" ]])
        rnx = rn1.symmetric_difference(rn2)
        self.assertEqual(len(rnx), 4)
        self.assertEqual(str(rnx), "10; 9,11-13\n")
        rnx2 = rn1 ^ rn2
        self.assertEqual(len(rnx2), 4)
        self.assertEqual(str(rnx2), "10; 9,11-13\n")
        self.assertEqual(rnx, rnx2)
        try:
            rn1 ^ "foobar"
            self.assertFalse("TypeError not raised")
        except TypeError:
            pass
        # binary error
        if sys.version_info >= (2,5,0):
            rn1 = RangeSetND([[ "10", "10-13" ], [ "10", "9-12" ]])
            rn2 = RangeSetND([[ "10", "10" ]])
            rn1 ^= rn2
            self.assertEqual(len(rnx), 4)
            self.assertEqual(str(rnx), "10; 9,11-13\n")
            rn2 = set([3, 5])
            self.assertRaises(TypeError, rn1.__ixor__, rn2)

    def test_getitem(self):
        rn1 = RangeSetND([[ "10", "10-13" ], [ "0-3", "1-2" ]])
        self.assertEqual(len(rn1), 12)
        self.assertEqual(rn1[0], (0, 1))
        self.assertEqual(rn1[1], (0, 2))
        self.assertEqual(rn1[2], (1, 1))
        self.assertEqual(rn1[3], (1, 2))
        self.assertEqual(rn1[4], (2, 1))
        self.assertEqual(rn1[5], (2, 2))
        self.assertEqual(rn1[6], (3, 1))
        self.assertEqual(rn1[7], (3, 2))
        self.assertEqual(rn1[8], (10, 10))
        self.assertEqual(rn1[9], (10, 11))
        self.assertEqual(rn1[10], (10, 12))
        self.assertEqual(rn1[11], (10, 13))
        self.assertRaises(IndexError, rn1.__getitem__, 12)
        # negative indices
        self.assertEqual(rn1[-1], (10, 13))
        self.assertEqual(rn1[-2], (10, 12))
        self.assertEqual(rn1[-3], (10, 11))
        self.assertEqual(rn1[-4], (10, 10))
        self.assertEqual(rn1[-5], (3, 2))
        self.assertEqual(rn1[-12], (0, 1))
        self.assertRaises(IndexError, rn1.__getitem__, -13)
        self.assertRaises(TypeError, rn1.__getitem__, "foo")

    def test_getitem_slices(self):
        rn1 = RangeSetND([[ "10", "10-13" ], [ "0-3", "1-2" ]])
        # slices
        self.assertEqual(str(rn1[0:2]), "0; 1-2\n")
        self.assertEqual(str(rn1[0:4]), "0-1; 1-2\n")
        self.assertEqual(str(rn1[0:5]), "0-1; 1-2\n2; 1\n")
        self.assertEqual(str(rn1[0:6]), "0-2; 1-2\n")
        self.assertEqual(str(rn1[0:7]), "0-2; 1-2\n3; 1\n")
        self.assertEqual(str(rn1[0:8]), "0-3; 1-2\n")
        self.assertEqual(str(rn1[0:9]), "0-3; 1-2\n10; 10\n")
        self.assertEqual(str(rn1[0:10]), "0-3; 1-2\n10; 10-11\n")
        self.assertEqual(str(rn1[0:11]), "0-3; 1-2\n10; 10-12\n")
        self.assertEqual(str(rn1[0:12]), "0-3; 1-2\n10; 10-13\n")
        self.assertEqual(str(rn1[0:13]), "0-3; 1-2\n10; 10-13\n")
        # steps
        self.assertEqual(str(rn1[0:12:2]), "0-3; 1\n10; 10,12\n")
        self.assertEqual(str(rn1[1:12:2]), "0-3; 2\n10; 11,13\n")

    def test_contiguous(self):
        rn0 = RangeSetND()
        self.assertEqual([], [str(ns) for ns in rn0.contiguous()])
        rn1 = RangeSetND([[ "10", "10-13,15" ], [ "0-3,5-6", "1-2" ]])
        self.assertEqual(str(rn1), "0-3,5-6; 1-2\n10; 10-13,15\n")
        self.assertEqual(['0-3; 1-2\n', '5-6; 1-2\n', '10; 10-13\n', '10; 15\n'], [str(ns) for ns in rn1.contiguous()])
        self.assertEqual(str(rn1), "0-3,5-6; 1-2\n10; 10-13,15\n")

    def test_iter(self):
        rn0 = RangeSetND([['1-2', '3'], ['1-2', '4'], ['2-6', '6-9,11']])
        self.assertEqual(len([r for r in rn0]), len(rn0))
        self.assertEqual([(2, 6), (2, 7), (2, 8), (2, 9), (2, 11), (3, 6), (3, 7), (3, 8), (3, 9), (3, 11), (4, 6), (4, 7), (4, 8), (4, 9), (4, 11), (5, 6), (5, 7), (5, 8), (5, 9), (5, 11), (6, 6), (6, 7), (6, 8), (6, 9), (6, 11), (1, 3), (1, 4), (2, 3), (2, 4)], [r for r in rn0])

    def test_pads(self):
        rn0 = RangeSetND()
        self.assertEqual(str(rn0), "")
        self.assertEqual(len(rn0), 0)
        self.assertEqual(rn0.pads(), ())
        rn1 = RangeSetND([['01-02', '003'], ['01-02', '004'], ['02-06', '006-009,411']])
        self.assertEqual(str(rn1), "02-06; 006-009,411\n01-02; 003-004\n")
        self.assertEqual(len(rn1), 29)
        self.assertEqual(rn1.pads(), (2, 3))

    def test_mutability_1(self):
        rs0 = RangeSet("2-5")
        rs1 = RangeSet("0-1")
        rn0 = RangeSetND([[rs0, rs1]]) #, copy_rangeset=False)
        self.assertEqual(str(rn0), "2-5; 0-1\n")

        rs2 = RangeSet("6-7")
        rs3 = RangeSet("2-3")
        rn1 = RangeSetND([[rs2, rs3]]) #, copy_rangeset=False)
        rn0.update(rn1)
        self.assertEqual(str(rn0), "2-5; 0-1\n6-7; 2-3\n")

        # check mutability safety
        self.assertEqual(str(rs0), "2-5")
        self.assertEqual(str(rs1), "0-1")
        self.assertEqual(str(rs2), "6-7")
        self.assertEqual(str(rs3), "2-3")

        # reverse check
        rs1.add(2)
        self.assertEqual(str(rs1), "0-2")
        rs3.add(4)
        self.assertEqual(str(rs3), "2-4")
        self.assertEqual(str(rn0), "2-5; 0-1\n6-7; 2-3\n")

        self.assertEqual(str(rn1), "6-7; 2-3\n")
        rn1.update([[rs2, rs3]])
        self.assertEqual(str(rn1), "6-7; 2-4\n")

        self.assertEqual(str(rn0), "2-5; 0-1\n6-7; 2-3\n")

    def test_mutability_2(self):
        rs0 = RangeSet("2-5")
        rs1 = RangeSet("0-1")
        rn0 = RangeSetND([[rs0, rs1]]) #, copy_rangeset=False)
        self.assertEqual(str(rn0), "2-5; 0-1\n")

        rs2 = RangeSet("6-7")
        rs3 = RangeSet("2-3")
        rn0.update([[rs2, rs3]])
        self.assertEqual(str(rn0), "2-5; 0-1\n6-7; 2-3\n")

        rs3.add(4)
        self.assertEqual(str(rs3), "2-4")
        self.assertEqual(str(rn0), "2-5; 0-1\n6-7; 2-3\n")

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(RangeSetNDTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = RangeSetTest
#!/usr/bin/env python
# ClusterShell.NodeSet.RangeSet test suite
# Written by S. Thiell


"""Unit test for RangeSet"""

import binascii
import copy
import pickle
import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.RangeSet import RangeSet


class RangeSetTest(unittest.TestCase):

    def _testRS(self, test, res, length):
        r1 = RangeSet(test, autostep=3)
        self.assertEqual(str(r1), res)
        self.assertEqual(len(r1), length)

    def testSimple(self):
        """test RangeSet simple ranges"""
        self._testRS("0", "0", 1)
        self._testRS("1", "1", 1)
        self._testRS("0-2", "0-2", 3)
        self._testRS("1-3", "1-3", 3)
        self._testRS("1-3,4-6", "1-6", 6)
        self._testRS("1-3,4-6,7-10", "1-10", 10)

    def testStepSimple(self):
        """test RangeSet simple step usages"""
        self._testRS("0-4/2", "0-4/2", 3)
        self._testRS("1-4/2", "1,3", 2)
        self._testRS("1-4/3", "1,4", 2)
        self._testRS("1-4/4", "1", 1)

    def testStepAdvanced(self):
        """test RangeSet advanced step usages"""
        self._testRS("1-4/4,2-6/2", "1,2-6/2", 4)   # 1.6 small behavior change
        self._testRS("6-24/6,9-21/6", "6-24/3", 7)
        self._testRS("0-24/2,9-21/2", "0-8/2,9-22,24", 20)
        self._testRS("0-24/2,9-21/2,100", "0-8/2,9-22,24,100", 21)
        self._testRS("0-24/2,9-21/2,100-101", "0-8/2,9-22,24,100-101", 22)
        self._testRS("3-21/9,6-24/9,9-27/9", "3-27/3", 9)
        self._testRS("101-121/4,1-225/112", "1,101-121/4,225", 8)
        self._testRS("1-32/3,13-28/9", "1-31/3", 11)
        self._testRS("1-32/3,13-22/9", "1-31/3", 11)
        self._testRS("1-32/3,13-31/9", "1-31/3", 11)
        self._testRS("1-32/3,13-40/9", "1-31/3,40", 12)
        self._testRS("1-16/3,13-28/6", "1-19/3,25", 8)
        self._testRS("1-16/3,1-16/6", "1-16/3", 6)
        self._testRS("1-16/6,1-16/3", "1-16/3", 6)
        self._testRS("1-16/3,3-19/6", "1,3-4,7,9-10,13,15-16", 9)
        #self._testRS("1-16/3,3-19/4", "1,3-4,7,10-11,13,15-16,19", 10) # < 1.6
        self._testRS("1-16/3,3-19/4", "1,3,4-10/3,11-15/2,16,19", 10)   # >= 1.6
        self._testRS("1-17/2,2-18/2", "1-18", 18)
        self._testRS("1-17/2,33-41/2,2-18/2", "1-18,33-41/2", 23)
        self._testRS("1-17/2,33-41/2,2-20/2", "1-18,20,33-41/2", 24)
        self._testRS("1-17/2,33-41/2,2-19/2", "1-18,33-41/2", 23)
        self._testRS("1968-1970,1972,1975,1978-1981,1984-1989", "1968-1970,1972-1978/3,1979-1981,1984-1989", 15)

    def testIntersectSimple(self):
        """test RangeSet with simple intersections of ranges"""
        r1 = RangeSet("4-34")
        r2 = RangeSet("27-42")
        r1.intersection_update(r2)
        self.assertEqual(str(r1), "27-34")
        self.assertEqual(len(r1), 8)

        r1 = RangeSet("2-450,654-700,800")
        r2 = RangeSet("500-502,690-820,830-840,900")
        r1.intersection_update(r2)
        self.assertEqual(str(r1), "690-700,800")
        self.assertEqual(len(r1), 12)

        r1 = RangeSet("2-450,654-700,800")
        r3 = r1.intersection(r2)
        self.assertEqual(str(r3), "690-700,800")
        self.assertEqual(len(r3), 12)

        r1 = RangeSet("2-450,654-700,800")
        r3 = r1 & r2
        self.assertEqual(str(r3), "690-700,800")
        self.assertEqual(len(r3), 12)

        r1 = RangeSet()
        r3 = r1.intersection(r2)
        self.assertEqual(str(r3), "")
        self.assertEqual(len(r3), 0)

    def testIntersectStep(self):
        """test RangeSet with more intersections of ranges"""
        r1 = RangeSet("4-34/2")
        r2 = RangeSet("28-42/2")
        r1.intersection_update(r2)
        self.assertEqual(str(r1), "28,30,32,34")
        self.assertEqual(len(r1), 4)

        r1 = RangeSet("4-34/2")
        r2 = RangeSet("27-42/2")
        r1.intersection_update(r2)
        self.assertEqual(str(r1), "")
        self.assertEqual(len(r1), 0)

        r1 = RangeSet("2-60/3", autostep=3)
        r2 = RangeSet("3-50/2", autostep=3)
        r1.intersection_update(r2)
        self.assertEqual(str(r1), "5-47/6")
        self.assertEqual(len(r1), 8)

    def testSubSimple(self):
        """test RangeSet with simple difference of ranges"""
        r1 = RangeSet("4,7-33")
        r2 = RangeSet("8-33")
        r1.difference_update(r2)
        self.assertEqual(str(r1), "4,7")
        self.assertEqual(len(r1), 2)

        r1 = RangeSet("4,7-33")
        r3 = r1.difference(r2)
        self.assertEqual(str(r3), "4,7")
        self.assertEqual(len(r3), 2)

        r3 = r1 - r2
        self.assertEqual(str(r3), "4,7")
        self.assertEqual(len(r3), 2)

        # bounds checking
        r1 = RangeSet("1-10,39-41,50-60")
        r2 = RangeSet("1-10,38-39,50-60")
        r1.difference_update(r2)
        self.assertEqual(len(r1), 2)
        self.assertEqual(str(r1), "40-41")

        r1 = RangeSet("1-20,39-41")
        r2 = RangeSet("1-20,41-42")
        r1.difference_update(r2)
        self.assertEqual(len(r1), 2)
        self.assertEqual(str(r1), "39-40")

        # difference(self) issue
        r1 = RangeSet("1-20,39-41")
        r1.difference_update(r1)
        self.assertEqual(len(r1), 0)
        self.assertEqual(str(r1), "")

        # strict mode
        r1 = RangeSet("4,7-33")
        r2 = RangeSet("8-33")
        r1.difference_update(r2, strict=True)
        self.assertEqual(str(r1), "4,7")
        self.assertEqual(len(r1), 2)

        r3 = RangeSet("4-5")
        self.assertRaises(KeyError, r1.difference_update, r3, True)

    def testSymmetricDifference(self):
        """test RangeSet.symmetric_difference_update()"""
        r1 = RangeSet("4,7-33")
        r2 = RangeSet("8-34")
        r1.symmetric_difference_update(r2)
        self.assertEqual(str(r1), "4,7,34")
        self.assertEqual(len(r1), 3)

        r1 = RangeSet("4,7-33")
        r3 = r1.symmetric_difference(r2)
        self.assertEqual(str(r3), "4,7,34")
        self.assertEqual(len(r3), 3)

        r3 = r1 ^ r2
        self.assertEqual(str(r3), "4,7,34")
        self.assertEqual(len(r3), 3)

        r1 = RangeSet("5,7,10-12,33-50")
        r2 = RangeSet("8-34")
        r1.symmetric_difference_update(r2)
        self.assertEqual(str(r1), "5,7-9,13-32,35-50")
        self.assertEqual(len(r1), 40)

        r1 = RangeSet("8-34")
        r2 = RangeSet("5,7,10-12,33-50")
        r1.symmetric_difference_update(r2)
        self.assertEqual(str(r1), "5,7-9,13-32,35-50")
        self.assertEqual(len(r1), 40)

        r1 = RangeSet("8-30")
        r2 = RangeSet("31-40")
        r1.symmetric_difference_update(r2)
        self.assertEqual(str(r1), "8-40")
        self.assertEqual(len(r1), 33)

        r1 = RangeSet("8-30")
        r2 = RangeSet("8-30")
        r1.symmetric_difference_update(r2)
        self.assertEqual(str(r1), "")
        self.assertEqual(len(r1), 0)

        r1 = RangeSet("8-30")
        r2 = RangeSet("10-13,31-40")
        r1.symmetric_difference_update(r2)
        self.assertEqual(str(r1), "8-9,14-40")
        self.assertEqual(len(r1), 29)

        r1 = RangeSet("10-13,31-40")
        r2 = RangeSet("8-30")
        r1.symmetric_difference_update(r2)
        self.assertEqual(str(r1), "8-9,14-40")
        self.assertEqual(len(r1), 29)

        r1 = RangeSet("1,3,5,7")
        r2 = RangeSet("4-8")
        r1.symmetric_difference_update(r2)
        self.assertEqual(str(r1), "1,3-4,6,8")
        self.assertEqual(len(r1), 5)

        r1 = RangeSet("1-1000")
        r2 = RangeSet("0-40,60-100/4,300,1000,1002")
        r1.symmetric_difference_update(r2)
        self.assertEqual(str(r1), "0,41-59,61-63,65-67,69-71,73-75,77-79,81-83,85-87,89-91,93-95,97-99,101-299,301-999,1002")
        self.assertEqual(len(r1), 949)

        r1 = RangeSet("25,27,29-31,33-35,41-43,48,50-52,55-60,63,66-68,71-78")
        r2 = RangeSet("27-30,35,37-39,42,45-48,50,52-54,56,61,67,69-79,81-82")
        r1.symmetric_difference_update(r2)
        self.assertEqual(str(r1), "25,28,31,33-34,37-39,41,43,45-47,51,53-55,57-61,63,66,68-70,79,81-82")
        self.assertEqual(len(r1), 30)

        r1 = RangeSet("986-987,989,991-992,994-995,997,1002-1008,1010-1011,1015-1018,1021")
        r2 = RangeSet("989-990,992-994,997-1000")
        r1.symmetric_difference_update(r2)
        self.assertEqual(str(r1), "986-987,990-991,993,995,998-1000,1002-1008,1010-1011,1015-1018,1021")
        self.assertEqual(len(r1), 23)

    def testSubStep(self):
        """test RangeSet with more sub of ranges (with step)"""
        # case 1 no sub
        r1 = RangeSet("4-34/2", autostep=3)
        r2 = RangeSet("3-33/2", autostep=3)
        self.assertEqual(r1.autostep, 3)
        self.assertEqual(r2.autostep, 3)
        r1.difference_update(r2)
        self.assertEqual(str(r1), "4-34/2")
        self.assertEqual(len(r1), 16)

        # case 2 diff left
        r1 = RangeSet("4-34/2", autostep=3)
        r2 = RangeSet("2-14/2", autostep=3)
        r1.difference_update(r2)
        self.assertEqual(str(r1), "16-34/2")
        self.assertEqual(len(r1), 10)
        
        # case 3 diff right
        r1 = RangeSet("4-34/2", autostep=3)
        r2 = RangeSet("28-52/2", autostep=3)
        r1.difference_update(r2)
        self.assertEqual(str(r1), "4-26/2")
        self.assertEqual(len(r1), 12)
        
        # case 4 diff with ranges split
        r1 = RangeSet("4-34/2", autostep=3)
        r2 = RangeSet("12-18/2", autostep=3)
        r1.difference_update(r2)
        self.assertEqual(str(r1), "4-10/2,20-34/2")
        self.assertEqual(len(r1), 12)

        # case 5+ more tricky diffs
        r1 = RangeSet("4-34/2", autostep=3)
        r2 = RangeSet("28-55", autostep=3)
        r1.difference_update(r2)
        self.assertEqual(str(r1), "4-26/2")
        self.assertEqual(len(r1), 12)

        r1 = RangeSet("4-34/2", autostep=3)
        r2 = RangeSet("27-55", autostep=3)
        r1.difference_update(r2)
        self.assertEqual(str(r1), "4-26/2")
        self.assertEqual(len(r1), 12)

        r1 = RangeSet("1-100", autostep=3)
        r2 = RangeSet("2-98/2", autostep=3)
        r1.difference_update(r2)
        self.assertEqual(str(r1), "1-99/2,100")
        self.assertEqual(len(r1), 51)

        r1 = RangeSet("1-100,102,105-242,800", autostep=3)
        r2 = RangeSet("1-1000/3", autostep=3)
        r1.difference_update(r2)
        self.assertEqual(str(r1), "2-3,5-6,8-9,11-12,14-15,17-18,20-21,23-24,26-27,29-30,32-33,35-36,38-39,41-42,44-45,47-48,50-51,53-54,56-57,59-60,62-63,65-66,68-69,71-72,74-75,77-78,80-81,83-84,86-87,89-90,92-93,95-96,98,99-105/3,107-108,110-111,113-114,116-117,119-120,122-123,125-126,128-129,131-132,134-135,137-138,140-141,143-144,146-147,149-150,152-153,155-156,158-159,161-162,164-165,167-168,170-171,173-174,176-177,179-180,182-183,185-186,188-189,191-192,194-195,197-198,200-201,203-204,206-207,209-210,212-213,215-216,218-219,221-222,224-225,227-228,230-231,233-234,236-237,239-240,242,800")
        self.assertEqual(len(r1), 160)

        r1 = RangeSet("1-1000", autostep=3)
        r2 = RangeSet("2-999/2", autostep=3)
        r1.difference_update(r2)
        self.assertEqual(str(r1), "1-999/2,1000")
        self.assertEqual(len(r1), 501)

        r1 = RangeSet("1-100/3,40-60/3", autostep=3)
        r2 = RangeSet("31-61/3", autostep=3)
        r1.difference_update(r2)
        self.assertEqual(str(r1), "1-28/3,64-100/3")
        self.assertEqual(len(r1), 23)

        r1 = RangeSet("1-100/3,40-60/3", autostep=3)
        r2 = RangeSet("30-80/5", autostep=3)
        r1.difference_update(r2)
        self.assertEqual(str(r1), "1-37/3,43-52/3,58-67/3,73-100/3")
        self.assertEqual(len(r1), 31)

    def testContains(self):
        """test RangeSet.__contains__()"""
        r1 = RangeSet("1-100,102,105-242,800")
        self.assertEqual(len(r1), 240)
        self.assert_(99 in r1)
        self.assert_("99" in r1)
        self.assert_("099" in r1)
        self.assertRaises(TypeError, r1.__contains__, object())
        self.assert_(101 not in r1)
        self.assertEqual(len(r1), 240)
        r2 = RangeSet("1-100/3,40-60/3", autostep=3)
        self.assertEqual(len(r2), 34)
        self.assert_(1 in r2)
        self.assert_(4 in r2)
        self.assert_(2 not in r2)
        self.assert_(3 not in r2)
        self.assert_(40 in r2)
        self.assert_(101 not in r2)
        r3 = RangeSet("0003-0143,0360-1000")
        self.assert_(360 in r3)
        self.assert_("360" in r3)
        self.assert_("0360" in r3)
        r4 = RangeSet("00-02")
        self.assert_("00" in r4)
        self.assert_(0 in r4)
        self.assert_("0" in r4)
        self.assert_("01" in r4)
        self.assert_(1 in r4)
        self.assert_("1" in r4)
        self.assert_("02" in r4)
        self.assert_(not "03" in r4)
        #
        r1 = RangeSet("115-117,130,132,166-170,4780-4999")
        self.assertEqual(len(r1), 230)
        r2 = RangeSet("116-117,130,4781-4999")
        self.assertEqual(len(r2), 222)
        self.assertTrue(r2 in r1)
        self.assertFalse(r1 in r2)
        r2 = RangeSet("5000")
        self.assertFalse(r2 in r1)
        r2 = RangeSet("4999")
        self.assertTrue(r2 in r1)

    def testIsSuperSet(self):
        """test RangeSet.issuperset()"""
        r1 = RangeSet("1-100,102,105-242,800")
        self.assertEqual(len(r1), 240)
        r2 = RangeSet("3-98,140-199,800")
        self.assertEqual(len(r2), 157)
        self.assertTrue(r1.issuperset(r1))
        self.assertTrue(r1.issuperset(r2))
        self.assertTrue(r1 >= r1)
        self.assertTrue(r1 > r2)
        self.assertFalse(r2 > r1)
        r2 = RangeSet("3-98,140-199,243,800")
        self.assertEqual(len(r2), 158)
        self.assertFalse(r1.issuperset(r2))
        self.assertFalse(r1 > r2)

    def testIsSubSet(self):
        """test RangeSet.issubset()"""
        r1 = RangeSet("1-100,102,105-242,800-900/2")
        self.assertTrue(r1.issubset(r1))
        self.assertTrue(r1.issuperset(r1))
        r2 = RangeSet()
        self.assertTrue(r2.issubset(r1))
        self.assertTrue(r1.issuperset(r2))
        self.assertFalse(r1.issubset(r2))
        self.assertFalse(r2.issuperset(r1))
        r1 = RangeSet("1-100,102,105-242,800-900/2")
        r2 = RangeSet("3,800,802,804,888")
        self.assertTrue(r2.issubset(r2))
        self.assertTrue(r2.issubset(r1))
        self.assertTrue(r2 <= r1)
        self.assertTrue(r2 < r1)
        self.assertTrue(r1 > r2)
        self.assertFalse(r1 < r2)
        self.assertFalse(r1 <= r2)
        self.assertFalse(r2 >= r1)
        # since v1.6, padding is ignored when computing set operations
        r1 = RangeSet("1-100")
        r2 = RangeSet("001-100")
        self.assertTrue(r1.issubset(r2))

    def testGetItem(self):
        """test RangeSet.__getitem__()"""
        r1 = RangeSet("1-100,102,105-242,800")
        self.assertEqual(len(r1), 240)
        self.assertEqual(r1[0], 1)
        self.assertEqual(r1[1], 2)
        self.assertEqual(r1[2], 3)
        self.assertEqual(r1[99], 100)
        self.assertEqual(r1[100], 102)
        self.assertEqual(r1[101], 105)
        self.assertEqual(r1[102], 106)
        self.assertEqual(r1[103], 107)
        self.assertEqual(r1[237], 241)
        self.assertEqual(r1[238], 242)
        self.assertEqual(r1[239], 800)
        self.assertRaises(IndexError, r1.__getitem__, 240)
        self.assertRaises(IndexError, r1.__getitem__, 241)
        # negative indices
        self.assertEqual(r1[-1], 800)
        self.assertEqual(r1[-240], 1)
        for n in range(1, len(r1)):
            self.assertEqual(r1[-n], r1[len(r1)-n])
        self.assertRaises(IndexError, r1.__getitem__, -len(r1)-1)
        self.assertRaises(IndexError, r1.__getitem__, -len(r1)-2)

        r2 = RangeSet("1-37/3,43-52/3,58-67/3,73-100/3,102-106/2")
        self.assertEqual(len(r2), 34)
        self.assertEqual(r2[0], 1)
        self.assertEqual(r2[1], 4)
        self.assertEqual(r2[2], 7)
        self.assertEqual(r2[12], 37)
        self.assertEqual(r2[13], 43)
        self.assertEqual(r2[14], 46)
        self.assertEqual(r2[16], 52)
        self.assertEqual(r2[17], 58)
        self.assertEqual(r2[29], 97)
        self.assertEqual(r2[30], 100)
        self.assertEqual(r2[31], 102)
        self.assertEqual(r2[32], 104)
        self.assertEqual(r2[33], 106)
        self.assertRaises(TypeError, r2.__getitem__, "foo")

    def testGetSlice(self):
        """test RangeSet.__getitem__() with slice"""
        r0 = RangeSet("1-12")
        self.assertEqual(r0[0:3], RangeSet("1-3"))
        self.assertEqual(r0[2:7], RangeSet("3-7"))
        # negative indices - sl_start
        self.assertEqual(r0[-1:0], RangeSet())
        self.assertEqual(r0[-2:0], RangeSet())
        self.assertEqual(r0[-11:0], RangeSet())
        self.assertEqual(r0[-12:0], RangeSet())
        self.assertEqual(r0[-13:0], RangeSet())
        self.assertEqual(r0[-1000:0], RangeSet())
        self.assertEqual(r0[-1:], RangeSet("12"))
        self.assertEqual(r0[-2:], RangeSet("11-12"))
        self.assertEqual(r0[-11:], RangeSet("2-12"))
        self.assertEqual(r0[-12:], RangeSet("1-12"))
        self.assertEqual(r0[-13:], RangeSet("1-12"))
        self.assertEqual(r0[-1000:], RangeSet("1-12"))
        self.assertEqual(r0[-13:1], RangeSet("1"))
        self.assertEqual(r0[-13:2], RangeSet("1-2"))
        self.assertEqual(r0[-13:11], RangeSet("1-11"))
        self.assertEqual(r0[-13:12], RangeSet("1-12"))
        self.assertEqual(r0[-13:13], RangeSet("1-12"))
        # negative indices - sl_stop
        self.assertEqual(r0[0:-1], RangeSet("1-11"))
        self.assertEqual(r0[:-1], RangeSet("1-11"))
        self.assertEqual(r0[0:-2], RangeSet("1-10"))
        self.assertEqual(r0[:-2], RangeSet("1-10"))
        self.assertEqual(r0[1:-2], RangeSet("2-10"))
        self.assertEqual(r0[4:-4], RangeSet("5-8"))
        self.assertEqual(r0[5:-5], RangeSet("6-7"))
        self.assertEqual(r0[6:-5], RangeSet("7"))
        self.assertEqual(r0[6:-6], RangeSet())
        self.assertEqual(r0[7:-6], RangeSet())
        self.assertEqual(r0[0:-1000], RangeSet())

        r1 = RangeSet("10-14,16-20")
        self.assertEqual(r1[2:6], RangeSet("12-14,16"))
        self.assertEqual(r1[2:7], RangeSet("12-14,16-17"))

        r1 = RangeSet("1-2,4,9,10-12")
        self.assertEqual(r1[0:3], RangeSet("1-2,4"))
        self.assertEqual(r1[0:4], RangeSet("1-2,4,9"))
        self.assertEqual(r1[2:6], RangeSet("4,9,10-11"))
        self.assertEqual(r1[2:4], RangeSet("4,9"))
        self.assertEqual(r1[5:6], RangeSet("11"))
        self.assertEqual(r1[6:7], RangeSet("12"))
        self.assertEqual(r1[4:7], RangeSet("10-12"))

        # Slice indices are silently truncated to fall in the allowed range
        self.assertEqual(r1[2:100], RangeSet("4,9-12"))
        self.assertEqual(r1[9:10], RangeSet())

        # Slice stepping
        self.assertEqual(r1[0:1:2], RangeSet("1"))
        self.assertEqual(r1[0:2:2], RangeSet("1"))
        self.assertEqual(r1[0:3:2], RangeSet("1,4"))
        self.assertEqual(r1[0:4:2], RangeSet("1,4"))
        self.assertEqual(r1[0:5:2], RangeSet("1,4,10"))
        self.assertEqual(r1[0:6:2], RangeSet("1,4,10"))
        self.assertEqual(r1[0:7:2], RangeSet("1,4,10,12"))
        self.assertEqual(r1[0:8:2], RangeSet("1,4,10,12"))
        self.assertEqual(r1[0:9:2], RangeSet("1,4,10,12"))
        self.assertEqual(r1[0:10:2], RangeSet("1,4,10,12"))

        self.assertEqual(r1[0:7:3], RangeSet("1,9,12"))
        self.assertEqual(r1[0:7:4], RangeSet("1,10"))

        self.assertEqual(len(r1[1:1:2]), 0)
        self.assertEqual(r1[1:2:2], RangeSet("2"))
        self.assertEqual(r1[1:3:2], RangeSet("2"))
        self.assertEqual(r1[1:4:2], RangeSet("2,9"))
        self.assertEqual(r1[1:5:2], RangeSet("2,9"))
        self.assertEqual(r1[1:6:2], RangeSet("2,9,11"))
        self.assertEqual(r1[1:7:2], RangeSet("2,9,11"))

        # negative indices - sl_step
        self.assertEqual(r1[::-2], RangeSet("1,4,10,12"))
        r2 = RangeSet("1-2,4,9,10-13")
        self.assertEqual(r2[::-2], RangeSet("2,9,11,13"))
        self.assertEqual(r2[::-3], RangeSet("2,10,13"))
        self.assertEqual(r2[::-4], RangeSet("9,13"))
        self.assertEqual(r2[::-5], RangeSet("4,13"))
        self.assertEqual(r2[::-6], RangeSet("2,13"))
        self.assertEqual(r2[::-7], RangeSet("1,13"))
        self.assertEqual(r2[::-8], RangeSet("13"))
        self.assertEqual(r2[::-9], RangeSet("13"))

        # Partial slices
        self.assertEqual(r1[2:], RangeSet("4,9-12"))
        self.assertEqual(r1[:3], RangeSet("1-2,4"))
        self.assertEqual(r1[:3:2], RangeSet("1,4"))

        # Twisted
        r2 = RangeSet("1-9/2,12-32/4")
        self.assertEqual(r2[5:10:2], RangeSet("12-28/8"))
        self.assertEqual(r2[5:10:2], RangeSet("12-28/8", autostep=2))
        self.assertEqual(r2[1:12:3], RangeSet("3,9,20,32"))

        # FIXME: use nosetests/@raises to do that...
        self.assertRaises(TypeError, r1.__getitem__, slice('foo', 'bar'))
        self.assertRaises(TypeError, r1.__getitem__, slice(1, 3, 'bar'))

        r3 = RangeSet("0-600")
        self.assertEqual(r3[30:389], RangeSet("30-388"))
        r3 = RangeSet("0-6000")
        self.assertEqual(r3[30:389:2], RangeSet("30-389/2"))
        self.assertEqual(r3[30:389:2], RangeSet("30-389/2", autostep=2))

    def testSplit(self):
        """test RangeSet.split()"""
        # Empty rangeset
        rangeset = RangeSet()
        self.assertEqual(len(list(rangeset.split(2))), 0)
        # Not enough element
        rangeset = RangeSet("1")
        self.assertEqual((RangeSet("1"),), tuple(rangeset.split(2)))
        # Exact number of elements
        rangeset = RangeSet("1-6")
        self.assertEqual((RangeSet("1-2"), RangeSet("3-4"), RangeSet("5-6")), \
                         tuple(rangeset.split(3)))
        # Check limit results
        rangeset = RangeSet("0-3")
        for i in (4, 5):
            self.assertEqual((RangeSet("0"), RangeSet("1"), \
                             RangeSet("2"), RangeSet("3")), \
                             tuple(rangeset.split(i)))

    def testAdd(self):
        """test RangeSet.add()"""
        r1 = RangeSet("1-100,102,105-242,800")
        self.assertEqual(len(r1), 240)
        r1.add(801)
        self.assertEqual(len(r1), 241)
        self.assertEqual(r1[0], 1)
        self.assertEqual(r1[240], 801)
        r1.add(788)
        self.assertEqual(str(r1), "1-100,102,105-242,788,800-801")
        self.assertEqual(len(r1), 242)
        self.assertEqual(r1[0], 1)
        self.assertEqual(r1[239], 788)
        self.assertEqual(r1[240], 800)
        r1.add(812)
        self.assertEqual(len(r1), 243)
        # test forced padding
        r1 = RangeSet("1-100,102,105-242,800")
        r1.add(801, pad=3)
        self.assertEqual(len(r1), 241)
        self.assertEqual(str(r1), "001-100,102,105-242,800-801")
        r1.padding = 4
        self.assertEqual(len(r1), 241)
        self.assertEqual(str(r1), "0001-0100,0102,0105-0242,0800-0801")

    def testUpdate(self):
        """test RangeSet.update()"""
        r1 = RangeSet("1-100,102,105-242,800")
        self.assertEqual(len(r1), 240)
        r2 = RangeSet("243-799,1924-1984")
        self.assertEqual(len(r2), 618)
        r1.update(r2)
        self.assertEqual(type(r1), RangeSet)
        self.assertEqual(r1.padding, None)
        self.assertEqual(len(r1), 240+618) 
        self.assertEqual(str(r1), "1-100,102,105-800,1924-1984")
        r1 = RangeSet("1-100,102,105-242,800")
        r1.union_update(r2)
        self.assertEqual(len(r1), 240+618) 
        self.assertEqual(str(r1), "1-100,102,105-800,1924-1984")

    def testUnion(self):
        """test RangeSet.union()"""
        r1 = RangeSet("1-100,102,105-242,800")
        self.assertEqual(len(r1), 240)
        r2 = RangeSet("243-799,1924-1984")
        self.assertEqual(len(r2), 618)
        r3 = r1.union(r2)
        self.assertEqual(type(r3), RangeSet)
        self.assertEqual(r3.padding, None)
        self.assertEqual(len(r3), 240+618) 
        self.assertEqual(str(r3), "1-100,102,105-800,1924-1984")
        r4 = r1 | r2
        self.assertEqual(len(r4), 240+618) 
        self.assertEqual(str(r4), "1-100,102,105-800,1924-1984")
        # test with overlap
        r2 = RangeSet("200-799")
        r3 = r1.union(r2)
        self.assertEqual(len(r3), 797)
        self.assertEqual(str(r3), "1-100,102,105-800")
        r4 = r1 | r2
        self.assertEqual(len(r4), 797)
        self.assertEqual(str(r4), "1-100,102,105-800")

    def testRemove(self):
        """test RangeSet.remove()"""
        r1 = RangeSet("1-100,102,105-242,800")
        self.assertEqual(len(r1), 240)
        r1.remove(100)
        self.assertEqual(len(r1), 239)
        self.assertEqual(str(r1), "1-99,102,105-242,800")
        self.assertRaises(KeyError, r1.remove, 101)
        # test remove integer-castable type (convenience)
        r1.remove("106")
        # non integer castable cases raise ValueError (documented since 1.6)
        self.assertRaises(ValueError, r1.remove, "foo")

    def testDiscard(self):
        """test RangeSet.discard()"""
        r1 = RangeSet("1-100,102,105-242,800")
        self.assertEqual(len(r1), 240)
        r1.discard(100)
        self.assertEqual(len(r1), 239)
        self.assertEqual(str(r1), "1-99,102,105-242,800")
        r1.discard(101)     # should not raise KeyError
        # test remove integer-castable type (convenience)
        r1.remove("106")
        r1.discard("foo")

    def testClear(self):
        """test RangeSet.clear()"""
        r1 = RangeSet("1-100,102,105-242,800")
        self.assertEqual(len(r1), 240)
        self.assertEqual(str(r1), "1-100,102,105-242,800")
        r1.clear()
        self.assertEqual(len(r1), 0)
        self.assertEqual(str(r1), "")
    
    def testConstructorIterate(self):
        """test RangeSet(iterable) constructor"""
        # from list
        rgs = RangeSet([3,5,6,7,8,1])
        self.assertEqual(str(rgs), "1,3,5-8")
        self.assertEqual(len(rgs), 6)
        rgs.add(10)
        self.assertEqual(str(rgs), "1,3,5-8,10")
        self.assertEqual(len(rgs), 7)
        # from set
        rgs = RangeSet(set([3,5,6,7,8,1]))
        self.assertEqual(str(rgs), "1,3,5-8")
        self.assertEqual(len(rgs), 6)
        # from RangeSet
        r1 = RangeSet("1,3,5-8")
        rgs = RangeSet(r1)
        self.assertEqual(str(rgs), "1,3,5-8")
        self.assertEqual(len(rgs), 6)

    def testFromListConstructor(self):
        """test RangeSet.fromlist() constructor"""
        rgs = RangeSet.fromlist([ "3", "5-8", "1" ])
        self.assertEqual(str(rgs), "1,3,5-8")
        self.assertEqual(len(rgs), 6)
        rgs = RangeSet.fromlist([ RangeSet("3"), RangeSet("5-8"), RangeSet("1") ])
        self.assertEqual(str(rgs), "1,3,5-8")
        self.assertEqual(len(rgs), 6)
        rgs = RangeSet.fromlist([set([3,5,6,7,8,1])])
        self.assertEqual(str(rgs), "1,3,5-8")
        self.assertEqual(len(rgs), 6)

    def testFromOneConstructor(self):
        """test RangeSet.fromone() constructor"""
        rgs = RangeSet.fromone(42)
        self.assertEqual(str(rgs), "42")
        self.assertEqual(len(rgs), 1)
        # also support slice object (v1.6+)
        rgs = RangeSet.fromone(slice(42))
        self.assertEqual(str(rgs), "0-41")
        self.assertEqual(len(rgs), 42)
        self.assertRaises(ValueError, RangeSet.fromone, slice(12, None))
        rgs = RangeSet.fromone(slice(42, 43))
        self.assertEqual(str(rgs), "42")
        self.assertEqual(len(rgs), 1)
        rgs = RangeSet.fromone(slice(42, 48))
        self.assertEqual(str(rgs), "42-47")
        self.assertEqual(len(rgs), 6)
        rgs = RangeSet.fromone(slice(42, 57, 2))
        self.assertEqual(str(rgs), "42,44,46,48,50,52,54,56")
        rgs.autostep = 3
        self.assertEqual(str(rgs), "42-56/2")
        self.assertEqual(len(rgs), 8)

    def testIterator(self):
        """test RangeSet iterator"""
        matches = [ 1, 3, 4, 5, 6, 7, 8, 11 ]
        rgs = RangeSet.fromlist([ "11", "3", "5-8", "1", "4" ])
        cnt = 0
        for rg in rgs:
            self.assertEqual(rg, matches[cnt])
            cnt += 1
        self.assertEqual(cnt, len(matches))
        # with padding
        rgs = RangeSet.fromlist([ "011", "003", "005-008", "001", "004" ])
        cnt = 0
        for rg in rgs:
            self.assertTrue(type(rg) is int)
            self.assertEqual(rg, matches[cnt])
            cnt += 1
        self.assertEqual(cnt, len(matches))

    def testStringIterator(self):
        """test RangeSet string iterator striter()"""
        matches = [ 1, 3, 4, 5, 6, 7, 8, 11 ]
        rgs = RangeSet.fromlist([ "11", "3", "5-8", "1", "4" ])
        cnt = 0
        for rg in rgs.striter():
            self.assertEqual(rg, str(matches[cnt]))
            cnt += 1
        self.assertEqual(cnt, len(matches))
        # with padding
        rgs = RangeSet.fromlist([ "011", "003", "005-008", "001", "004" ])
        cnt = 0
        for rg in rgs.striter():
            self.assertTrue(type(rg) is str)
            self.assertEqual(rg, "%0*d" % (3, matches[cnt]))
            cnt += 1
        self.assertEqual(cnt, len(matches))

    def testBinarySanityCheck(self):
        """test RangeSet binary sanity check"""
        rg1 = RangeSet("1-5")
        rg2 = "4-6"
        self.assertRaises(TypeError, rg1.__gt__, rg2)
        self.assertRaises(TypeError, rg1.__lt__, rg2)

    def testBinarySanityCheckNotImplementedSubtle(self):
        """test RangeSet binary sanity check (NotImplemented subtle)"""
        rg1 = RangeSet("1-5")
        rg2 = "4-6"
        self.assertEqual(rg1.__and__(rg2), NotImplemented)
        self.assertEqual(rg1.__or__(rg2), NotImplemented)
        self.assertEqual(rg1.__sub__(rg2), NotImplemented)
        self.assertEqual(rg1.__xor__(rg2), NotImplemented)
        # Should implicitely raises TypeError if the real operator
        # version is invoked. To test that, we perform a manual check
        # as an additional function would be needed to check with
        # assertRaises():
        good_error = False
        try:
            rg3 = rg1 & rg2
        except TypeError:
            good_error = True
        self.assert_(good_error, "TypeError not raised for &")
        good_error = False
        try:
            rg3 = rg1 | rg2
        except TypeError:
            good_error = True
        self.assert_(good_error, "TypeError not raised for |")
        good_error = False
        try:
            rg3 = rg1 - rg2
        except TypeError:
            good_error = True
        self.assert_(good_error, "TypeError not raised for -")
        good_error = False
        try:
            rg3 = rg1 ^ rg2
        except TypeError:
            good_error = True
        self.assert_(good_error, "TypeError not raised for ^")

    def testIsSubSetError(self):
        """test RangeSet.issubset() error"""
        rg1 = RangeSet("1-5")
        rg2 = "4-6"
        self.assertRaises(TypeError, rg1.issubset, rg2)

    def testEquality(self):
        """test RangeSet equality"""
        rg0_1 = RangeSet()
        rg0_2 = RangeSet()
        self.assertEqual(rg0_1, rg0_2)
        rg1 = RangeSet("1-4")
        rg2 = RangeSet("1-4")
        self.assertEqual(rg1, rg2)
        rg3 = RangeSet("2-5")
        self.assertNotEqual(rg1, rg3)
        rg4 = RangeSet("1,2,3,4")
        self.assertEqual(rg1, rg4)
        rg5 = RangeSet("1,2,4")
        self.assertNotEqual(rg1, rg5)
        if rg1 == None:
            self.fail("rg1 == None succeeded")
        if rg1 != None:
            pass
        else:
            self.fail("rg1 != None failed")

    def testAddRange(self):
        """test RangeSet.add_range()"""
        r1 = RangeSet()
        r1.add_range(1, 100, 1)
        self.assertEqual(len(r1), 99)
        self.assertEqual(str(r1), "1-99")
        r1.add_range(40, 101, 1)
        self.assertEqual(len(r1), 100)
        self.assertEqual(str(r1), "1-100")
        r1.add_range(399, 423, 2)
        self.assertEqual(len(r1), 112)
        self.assertEqual(str(r1), "1-100,399,401,403,405,407,409,411,413,415,417,419,421")
        # With autostep...
        r1 = RangeSet(autostep=3)
        r1.add_range(1, 100, 1)
        self.assertEqual(r1.autostep, 3)
        self.assertEqual(len(r1), 99)
        self.assertEqual(str(r1), "1-99")
        r1.add_range(40, 101, 1)
        self.assertEqual(len(r1), 100)
        self.assertEqual(str(r1), "1-100")
        r1.add_range(399, 423, 2)
        self.assertEqual(len(r1), 112)
        self.assertEqual(str(r1), "1-100,399-421/2")
        # Bound checks
        r1 = RangeSet("1-30", autostep=2)
        self.assertEqual(len(r1), 30)
        self.assertEqual(str(r1), "1-30")
        self.assertEqual(r1.autostep, 2)
        r1.add_range(32, 35, 1)
        self.assertEqual(len(r1), 33)
        self.assertEqual(str(r1), "1-30,32-34")
        r1.add_range(31, 32, 1)
        self.assertEqual(len(r1), 34)
        self.assertEqual(str(r1), "1-34")
        r1 = RangeSet("1-30/4")
        self.assertEqual(len(r1), 8)
        self.assertEqual(str(r1), "1,5,9,13,17,21,25,29")
        r1.add_range(30, 32, 1)
        self.assertEqual(len(r1), 10)
        self.assertEqual(str(r1), "1,5,9,13,17,21,25,29-31")
        r1.add_range(40, 65, 10)
        self.assertEqual(len(r1), 13)
        self.assertEqual(str(r1), "1,5,9,13,17,21,25,29-31,40,50,60")
        r1 = RangeSet("1-30", autostep=3)
        r1.add_range(40, 65, 10)
        self.assertEqual(r1.autostep, 3)
        self.assertEqual(len(r1), 33)
        self.assertEqual(str(r1), "1-29,30-60/10")
        # One
        r1.add_range(103, 104)
        self.assertEqual(len(r1), 34)
        self.assertEqual(str(r1), "1-29,30-60/10,103")
        # Zero
        self.assertRaises(AssertionError, r1.add_range, 103, 103)

    def testSlices(self):
        """test RangeSet.slices()"""
        r1 = RangeSet()
        self.assertEqual(len(r1), 0)
        self.assertEqual(len(list(r1.slices())), 0)
        # Without autostep
        r1 = RangeSet("1-7/2,8-12,3000-3019")
        self.assertEqual(r1.autostep, None)
        self.assertEqual(len(r1), 29)
        self.assertEqual(list(r1.slices()), [slice(1, 2, 1), slice(3, 4, 1), \
            slice(5, 6, 1), slice(7, 13, 1), slice(3000, 3020, 1)])
        # With autostep
        r1 = RangeSet("1-7/2,8-12,3000-3019", autostep=2)
        self.assertEqual(len(r1), 29)
        self.assertEqual(r1.autostep, 2)
        self.assertEqual(list(r1.slices()), [slice(1, 8, 2), slice(8, 13, 1), \
            slice(3000, 3020, 1)])

    def testCopy(self):
        """test RangeSet.copy()"""
        rangeset = RangeSet("115-117,130,166-170,4780-4999")
        self.assertEqual(len(rangeset), 229)
        self.assertEqual(str(rangeset), "115-117,130,166-170,4780-4999")
        r1 = rangeset.copy()
        r2 = rangeset.copy()
        self.assertEqual(rangeset, r1) # content equality
        r1.remove(166)
        self.assertEqual(len(rangeset), len(r1) + 1)
        self.assertNotEqual(rangeset, r1)
        self.assertEqual(str(rangeset), "115-117,130,166-170,4780-4999")
        self.assertEqual(str(r1), "115-117,130,167-170,4780-4999")
        r2.update(RangeSet("118"))
        self.assertNotEqual(rangeset, r2)
        self.assertNotEqual(r1, r2)
        self.assertEqual(len(rangeset) + 1, len(r2))
        self.assertEqual(str(rangeset), "115-117,130,166-170,4780-4999")
        self.assertEqual(str(r1), "115-117,130,167-170,4780-4999")
        self.assertEqual(str(r2), "115-118,130,166-170,4780-4999")

    def test_unpickle_v1_3_py24(self):
        """test RangeSet unpickling (against v1.3/py24)"""
        rngset = pickle.loads(binascii.a2b_base64("gAIoY0NsdXN0ZXJTaGVsbC5Ob2RlU2V0ClJhbmdlU2V0CnEAb3EBfXECKFUHX2xlbmd0aHEDS2RVCV9hdXRvc3RlcHEER1SySa0llMN9VQdfcmFuZ2VzcQVdcQYoKEsFSwVLAUsAdHEHKEsHS2ZLAUsAdHEIKEtoS2hLAUsAdHEJKEtqS2tLAUsAdHEKZXViLg=="))
        self.assertEqual(rngset, RangeSet("5,7-102,104,106-107"))
        self.assertEqual(str(rngset), "5,7-102,104,106-107")
        self.assertEqual(len(rngset), 100)
        self.assertEqual(rngset[0], 5)
        self.assertEqual(rngset[1], 7)
        self.assertEqual(rngset[-1], 107)

    def test_unpickle_v1_3_py26(self):
        """test RangeSet unpickling (against v1.3/py26)"""
        rngset = pickle.loads(binascii.a2b_base64("gAIoY0NsdXN0ZXJTaGVsbC5Ob2RlU2V0ClJhbmdlU2V0CnEAb3EBfXECKFUHX2xlbmd0aHEDS2RVCV9hdXRvc3RlcHEER1SySa0llMN9VQdfcmFuZ2VzcQVdcQYoKEsFSwVLAUsAdHEHKEsHS2ZLAUsAdHEIKEtoS2hLAUsAdHEJKEtqS2tLAUsAdHEKZXViLg=="))
        self.assertEqual(rngset, RangeSet("5,7-102,104,106-107"))
        self.assertEqual(str(rngset), "5,7-102,104,106-107")
        self.assertEqual(len(rngset), 100)
        self.assertEqual(rngset[0], 5)
        self.assertEqual(rngset[1], 7)
        self.assertEqual(rngset[-1], 107)

    # unpickle_v1_4_py24 : unpickling fails as v1.4 does not have slice pickling workaround

    def test_unpickle_v1_4_py26(self):
        """test RangeSet unpickling (against v1.4/py26)"""
        rngset = pickle.loads(binascii.a2b_base64("gAIoY0NsdXN0ZXJTaGVsbC5Ob2RlU2V0ClJhbmdlU2V0CnEAb3EBfXEDKFUHX2xlbmd0aHEES2RVCV9hdXRvc3RlcHEFR1SySa0llMN9VQdfcmFuZ2VzcQZdcQcoY19fYnVpbHRpbl9fCnNsaWNlCnEISwVLBksBh3EJUnEKSwCGcQtoCEsHS2dLAYdxDFJxDUsAhnEOaAhLaEtpSwGHcQ9ScRBLAIZxEWgIS2pLbEsBh3ESUnETSwCGcRRlVQhfdmVyc2lvbnEVSwJ1Yi4="))
        self.assertEqual(rngset, RangeSet("5,7-102,104,106-107"))
        self.assertEqual(str(rngset), "5,7-102,104,106-107")
        self.assertEqual(len(rngset), 100)
        self.assertEqual(rngset[0], 5)
        self.assertEqual(rngset[1], 7)
        self.assertEqual(rngset[-1], 107)

    def test_unpickle_v1_5_py24(self):
        """test RangeSet unpickling (against v1.5/py24)"""
        rngset = pickle.loads(binascii.a2b_base64("gAIoY0NsdXN0ZXJTaGVsbC5Ob2RlU2V0ClJhbmdlU2V0CnEAb3EBfXEDKFUHX2xlbmd0aHEES2RVCV9hdXRvc3RlcHEFR1SySa0llMN9VQdfcmFuZ2VzcQZdcQcoSwVLBksBh3EISwCGcQlLB0tnSwGHcQpLAIZxC0toS2lLAYdxDEsAhnENS2pLbEsBh3EOSwCGcQ9lVQhfdmVyc2lvbnEQSwJ1Yi4="))
        self.assertEqual(rngset, RangeSet("5,7-102,104,106-107"))
        self.assertEqual(str(rngset), "5,7-102,104,106-107")
        self.assertEqual(len(rngset), 100)
        self.assertEqual(rngset[0], 5)
        self.assertEqual(rngset[1], 7)
        self.assertEqual(rngset[-1], 107)

    def test_unpickle_v1_5_py26(self):
        """test RangeSet unpickling (against v1.5/py26)"""
        rngset = pickle.loads(binascii.a2b_base64("gAIoY0NsdXN0ZXJTaGVsbC5Ob2RlU2V0ClJhbmdlU2V0CnEAb3EBfXEDKFUHX2xlbmd0aHEES2RVCV9hdXRvc3RlcHEFR1SySa0llMN9VQdfcmFuZ2VzcQZdcQcoY19fYnVpbHRpbl9fCnNsaWNlCnEISwVLBksBh3EJUnEKSwCGcQtoCEsHS2dLAYdxDFJxDUsAhnEOaAhLaEtpSwGHcQ9ScRBLAIZxEWgIS2pLbEsBh3ESUnETSwCGcRRlVQhfdmVyc2lvbnEVSwJ1Yi4="))

        self.assertEqual(rngset, RangeSet("5,7-102,104,106-107"))
        self.assertEqual(str(rngset), "5,7-102,104,106-107")
        self.assertEqual(len(rngset), 100)
        self.assertEqual(rngset[0], 5)
        self.assertEqual(rngset[1], 7)
        self.assertEqual(rngset[-1], 107)

    def test_unpickle_v1_6_py24(self):
        """test RangeSet unpickling (against v1.6/py24)"""
        rngset = pickle.loads(binascii.a2b_base64("gAJjQ2x1c3RlclNoZWxsLlJhbmdlU2V0ClJhbmdlU2V0CnEAVRM1LDctMTAyLDEwNCwxMDYtMTA3cQGFcQJScQN9cQQoVQdwYWRkaW5ncQVOVQlfYXV0b3N0ZXBxBkdUskmtJZTDfVUIX3ZlcnNpb25xB0sDdWIu"))
        self.assertEqual(rngset, RangeSet("5,7-102,104,106-107"))
        self.assertEqual(str(rngset), "5,7-102,104,106-107")
        self.assertEqual(len(rngset), 100)
        self.assertEqual(rngset[0], 5)
        self.assertEqual(rngset[1], 7)
        self.assertEqual(rngset[-1], 107)

    def test_unpickle_v1_6_py26(self):
        """test RangeSet unpickling (against v1.6/py26)"""
        rngset = pickle.loads(binascii.a2b_base64("gAJjQ2x1c3RlclNoZWxsLlJhbmdlU2V0ClJhbmdlU2V0CnEAVRM1LDctMTAyLDEwNCwxMDYtMTA3cQGFcQJScQN9cQQoVQdwYWRkaW5ncQVOVQlfYXV0b3N0ZXBxBkdUskmtJZTDfVUIX3ZlcnNpb25xB0sDdWIu"))
        self.assertEqual(rngset, RangeSet("5,7-102,104,106-107"))
        self.assertEqual(str(rngset), "5,7-102,104,106-107")
        self.assertEqual(len(rngset), 100)
        self.assertEqual(rngset[0], 5)
        self.assertEqual(rngset[1], 7)
        self.assertEqual(rngset[-1], 107)

    def test_pickle_current(self):
        """test RangeSet pickling (current version)"""
        dump = pickle.dumps(RangeSet("1-100"))
        self.assertNotEqual(dump, None)
        rngset = pickle.loads(dump)
        self.assertEqual(rngset, RangeSet("1-100"))
        self.assertEqual(str(rngset), "1-100")
        self.assertEqual(rngset[0], 1)
        self.assertEqual(rngset[1], 2)
        self.assertEqual(rngset[-1], 100)

    def testIntersectionLength(self):
        """test RangeSet intersection/length"""
        r1 = RangeSet("115-117,130,166-170,4780-4999")
        self.assertEqual(len(r1), 229)
        r2 = RangeSet("116-117,130,4781-4999")
        self.assertEqual(len(r2), 222)
        res = r1.intersection(r2)
        self.assertEqual(len(res), 222)
        r1 = RangeSet("115-200")
        self.assertEqual(len(r1), 86)
        r2 = RangeSet("116-117,119,123-131,133,149,199")
        self.assertEqual(len(r2), 15)
        res = r1.intersection(r2)
        self.assertEqual(len(res), 15)
        # StopIteration test
        r1 = RangeSet("115-117,130,166-170,4780-4999,5003")
        self.assertEqual(len(r1), 230)
        r2 = RangeSet("116-117,130,4781-4999")
        self.assertEqual(len(r2), 222)
        res = r1.intersection(r2)
        self.assertEqual(len(res), 222)
        # StopIteration test2
        r1 = RangeSet("130,166-170,4780-4999")
        self.assertEqual(len(r1), 226)
        r2 = RangeSet("116-117")
        self.assertEqual(len(r2), 2)
        res = r1.intersection(r2)
        self.assertEqual(len(res), 0)

    def testFolding(self):
        """test RangeSet folding conditions"""
        r1 = RangeSet("112,114-117,119,121,130,132,134,136,138,139-141,144,147-148", autostep=6)
        self.assertEqual(str(r1), "112,114-117,119,121,130,132,134,136,138-141,144,147-148")
        r1.autostep = 5
        self.assertEqual(str(r1), "112,114-117,119,121,130-138/2,139-141,144,147-148")
        
        r1 = RangeSet("1,3-4,6,8")
        self.assertEqual(str(r1), "1,3-4,6,8")
        r1 = RangeSet("1,3-4,6,8", autostep=4)
        self.assertEqual(str(r1), "1,3-4,6,8")
        r1 = RangeSet("1,3-4,6,8", autostep=2)
        self.assertEqual(str(r1), "1,3,4-8/2")
        r1 = RangeSet("1,3-4,6,8", autostep=3)
        self.assertEqual(str(r1), "1,3,4-8/2")

        # empty set
        r1 = RangeSet(autostep=3)
        self.assertEqual(str(r1), "")

    def test_ior(self):
        """test RangeSet.__ior__()"""
        r1 = RangeSet("1,3-9,14-21,30-39,42")
        r2 = RangeSet("2-5,10-32,35,40-41")
        r1 |= r2
        self.assertEqual(len(r1), 42)
        self.assertEqual(str(r1), "1-42")

    def test_iand(self):
        """test RangeSet.__iand__()"""
        r1 = RangeSet("1,3-9,14-21,30-39,42")
        r2 = RangeSet("2-5,10-32,35,40-41")
        r1 &= r2
        self.assertEqual(len(r1), 15)
        self.assertEqual(str(r1), "3-5,14-21,30-32,35")

    def test_ixor(self):
        """test RangeSet.__ixor__()"""
        r1 = RangeSet("1,3-9,14-21,30-39,42")
        r2 = RangeSet("2-5,10-32,35,40-41")
        r1 ^= r2
        self.assertEqual(len(r1), 27)
        self.assertEqual(str(r1), "1-2,6-13,22-29,33-34,36-42")

    def test_isub(self):
        """test RangeSet.__isub__()"""
        r1 = RangeSet("1,3-9,14-21,30-39,42")
        r2 = RangeSet("2-5,10-32,35,40-41")
        r1 -= r2
        self.assertEqual(len(r1), 12)
        self.assertEqual(str(r1), "1,6-9,33-34,36-39,42")

    def test_contiguous(self):
        r0 = RangeSet()
        self.assertEqual([], [str(ns) for ns in r0.contiguous()])
        r1 = RangeSet("1,3-9,14-21,30-39,42")
        self.assertEqual(['1', '3-9', '14-21', '30-39', '42'], [str(ns) for ns in r1.contiguous()])

    def test_dim(self):
        r0 = RangeSet()
        self.assertEqual(r0.dim(), 0)
        r1 = RangeSet("1-10,15-20")
        self.assertEqual(r1.dim(), 1)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(RangeSetTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
        

########NEW FILE########
__FILENAME__ = TaskDistantMixin
#!/usr/bin/env python
# ClusterShell (distant) test suite
# Written by S. Thiell 2009-02-13


"""Unit test for ClusterShell Task (distant)"""

import copy
import pwd
import shutil
import sys

sys.path.insert(0, '../lib')

from TLib import make_temp_filename, make_temp_dir
from ClusterShell.Event import EventHandler
from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import *
from ClusterShell.Worker.Ssh import WorkerSsh
from ClusterShell.Worker.EngineClient import *
from ClusterShell.Worker.Worker import WorkerBadArgumentError

import socket

# TEventHandlerChecker 'received event' flags
EV_START=0x01
EV_READ=0x02
EV_WRITTEN=0x04
EV_HUP=0x08
EV_TIMEOUT=0x10
EV_CLOSE=0x20

class TaskDistantMixin(object):

    def setUp(self):
        self._task = task_self()
        self.assert_(self._task != None)

    def testLocalhostCommand(self):
        # init worker
        worker = self._task.shell("/bin/hostname", nodes='localhost')
        self.assert_(worker != None)
        # run task
        self._task.resume()

    def testLocalhostCommand2(self):
        # init worker
        worker = self._task.shell("/bin/hostname", nodes='localhost')
        self.assert_(worker != None)

        worker = self._task.shell("/bin/uname -r", nodes='localhost')
        self.assert_(worker != None)
        # run task
        self._task.resume()

    def testTaskShellWorkerGetCommand(self):
        worker1 = self._task.shell("/bin/hostname", nodes='localhost')
        self.assert_(worker1 != None)
        worker2 = self._task.shell("/bin/uname -r", nodes='localhost')
        self.assert_(worker2 != None)
        self._task.resume()
        self.assert_(hasattr(worker1, 'command'))
        self.assert_(hasattr(worker2, 'command'))
        self.assertEqual(worker1.command, "/bin/hostname")
        self.assertEqual(worker2.command, "/bin/uname -r")

    def testLocalhostCopy(self):
        # init worker
        dest = make_temp_filename(suffix='LocalhostCopy')
        worker = self._task.copy("/etc/hosts", dest, nodes='localhost')
        self.assert_(worker != None)
        # run task
        self._task.resume()
        os.unlink(dest)

    def testCopyNodeFailure(self):
        # == stderr merged ==
        self._task.set_default("stderr", False)
        dest = make_temp_filename(suffix='LocalhostCopyF')
        worker = self._task.copy("/etc/hosts", dest,
                                 nodes='unlikely-node,localhost')
        self.assert_(worker != None)
        self._task.resume()
        self.assert_(worker.node_error_buffer("unlikely-node") is None)
        self.assert_(len(worker.node_buffer("unlikely-node")) > 2)
        os.unlink(dest)

        # == stderr separated ==
        self._task.set_default("stderr", True)
        try:
            dest = make_temp_filename(suffix='LocalhostCopyF2')
            worker = self._task.copy("/etc/hosts", dest, nodes='unlikely-node,localhost')
            self.assert_(worker != None)
            # run task
            self._task.resume()
            self.assert_(worker.node_buffer("unlikely-node") is None)
            self.assert_(len(worker.node_error_buffer("unlikely-node")) > 2)
            os.unlink(dest)
        finally:
            self._task.set_default("stderr", False)

    def testLocalhostCopyDir(self):
        dtmp_src = make_temp_dir('src')
        dtmp_dst = make_temp_dir('testLocalhostCopyDir')
        try:
            os.mkdir(os.path.join(dtmp_src, "lev1_a"))
            os.mkdir(os.path.join(dtmp_src, "lev1_b"))
            os.mkdir(os.path.join(dtmp_src, "lev1_a", "lev2"))
            worker = self._task.copy(dtmp_src, dtmp_dst, nodes='localhost')
            self.assert_(worker != None)
            self._task.resume()
            self.assert_(os.path.exists(os.path.join(dtmp_dst, \
                os.path.basename(dtmp_src), "lev1_a", "lev2")))
        finally:
            shutil.rmtree(dtmp_dst, ignore_errors=True)
            shutil.rmtree(dtmp_src, ignore_errors=True)

    def testLocalhostExplicitSshCopy(self):
        dest = make_temp_filename('testLocalhostExplicitSshCopy')
        try:
            worker = WorkerSsh("localhost", source="/etc/hosts", dest=dest,
                    handler=None, timeout=10)
            self._task.schedule(worker)
            self._task.resume()
        finally:
            os.remove(dest)

    def testLocalhostExplicitSshCopyDir(self):
        dtmp_src = make_temp_dir('src')
        dtmp_dst = make_temp_dir('testLocalhostExplicitSshCopyDir')
        try:
            os.mkdir(os.path.join(dtmp_src, "lev1_a"))
            os.mkdir(os.path.join(dtmp_src, "lev1_b"))
            os.mkdir(os.path.join(dtmp_src, "lev1_a", "lev2"))
            worker = WorkerSsh("localhost", source=dtmp_src,
                    dest=dtmp_dst, handler=None, timeout=10)
            self._task.schedule(worker)
            self._task.resume()
            self.assert_(os.path.exists(os.path.join(dtmp_dst, \
                os.path.basename(dtmp_src), "lev1_a", "lev2")))
        finally:
            shutil.rmtree(dtmp_dst, ignore_errors=True)
            shutil.rmtree(dtmp_src, ignore_errors=True)

    def testLocalhostExplicitSshCopyDirPreserve(self):
        dtmp_src = make_temp_dir('src')
        dtmp_dst = make_temp_dir('testLocalhostExplicitSshCopyDirPreserve')
        try:
            os.mkdir(os.path.join(dtmp_src, "lev1_a"))
            os.mkdir(os.path.join(dtmp_src, "lev1_b"))
            os.mkdir(os.path.join(dtmp_src, "lev1_a", "lev2"))
            worker = WorkerSsh("localhost", source=dtmp_src, dest=dtmp_dst,
                               handler=None, timeout=10, preserve=True)
            self._task.schedule(worker)
            self._task.resume()
            self.assert_(os.path.exists(os.path.join(dtmp_dst, \
                os.path.basename(dtmp_src), "lev1_a", "lev2")))
        finally:
            shutil.rmtree(dtmp_dst, ignore_errors=True)
            shutil.rmtree(dtmp_src, ignore_errors=True)

    def testExplicitSshWorker(self):
        # init worker
        worker = WorkerSsh("localhost", command="/bin/echo alright", handler=None, timeout=5)
        self.assert_(worker != None)
        self._task.schedule(worker)
        # run task
        self._task.resume()
        # test output
        self.assertEqual(worker.node_buffer("localhost"), "alright")

    def testExplicitSshWorkerStdErr(self):
        # init worker
        worker = WorkerSsh("localhost", command="/bin/echo alright 1>&2",
                    handler=None, stderr=True, timeout=5)
        self.assert_(worker != None)
        self._task.schedule(worker)
        # run task
        self._task.resume()
        # test output
        self.assertEqual(worker.node_error_buffer("localhost"), "alright")

        # Re-test with stderr=False
        worker = WorkerSsh("localhost", command="/bin/echo alright 1>&2",
                    handler=None, stderr=False, timeout=5)
        self.assert_(worker != None)
        self._task.schedule(worker)
        # run task
        self._task.resume()
        # test output
        self.assertEqual(worker.node_error_buffer("localhost"), None)

    class TEventHandlerChecker(EventHandler):

        def __init__(self, test):
            self.test = test
            self.flags = 0
            self.read_count = 0
            self.written_count = 0
        def ev_start(self, worker):
            self.test.assertEqual(self.flags, 0)
            self.flags |= EV_START
        def ev_read(self, worker):
            self.test.assertEqual(self.flags, EV_START)
            self.flags |= EV_READ
            self.last_node, self.last_read = worker.last_read()
        def ev_written(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_WRITTEN
        def ev_hup(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_HUP
            self.last_rc = worker.last_retcode()
        def ev_timeout(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_TIMEOUT
            self.last_node = worker.last_node()
        def ev_close(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.test.assert_(self.flags & EV_CLOSE == 0)
            self.flags |= EV_CLOSE

    def testShellEvents(self):
        # init worker
        test_eh = self.__class__.TEventHandlerChecker(self)
        worker = self._task.shell("/bin/hostname", nodes='localhost', handler=test_eh)
        self.assert_(worker != None)
        # run task
        self._task.resume()
        # test events received: start, read, hup, close
        self.assertEqual(test_eh.flags, EV_START | EV_READ | EV_HUP | EV_CLOSE)

    def testShellEventsWithTimeout(self):
        # init worker
        test_eh = self.__class__.TEventHandlerChecker(self)
        worker = self._task.shell("/bin/echo alright && /bin/sleep 10", nodes='localhost', handler=test_eh,
                timeout=2)
        self.assert_(worker != None)
        # run task
        self._task.resume()
        # test events received: start, read, timeout, close
        self.assertEqual(test_eh.flags, EV_START | EV_READ | EV_TIMEOUT | EV_CLOSE)
        self.assertEqual(worker.node_buffer("localhost"), "alright")
        self.assertEqual(worker.num_timeout(), 1)
        self.assertEqual(self._task.num_timeout(), 1)
        count = 0
        for node in self._task.iter_keys_timeout():
            count += 1
            self.assertEqual(node, "localhost")
        self.assertEqual(count, 1)
        count = 0
        for node in worker.iter_keys_timeout():
            count += 1
            self.assertEqual(node, "localhost")
        self.assertEqual(count, 1)

    def testShellEventsWithTimeout2(self):
        # init worker
        test_eh1 = self.__class__.TEventHandlerChecker(self)
        worker1 = self._task.shell("/bin/echo alright && /bin/sleep 10", nodes='localhost', handler=test_eh1,
                timeout=2)
        self.assert_(worker1 != None)
        test_eh2 = self.__class__.TEventHandlerChecker(self)
        worker2 = self._task.shell("/bin/echo okay && /bin/sleep 10", nodes='localhost', handler=test_eh2,
                timeout=3)
        self.assert_(worker2 != None)
        # run task
        self._task.resume()
        # test events received: start, read, timeout, close
        self.assertEqual(test_eh1.flags, EV_START | EV_READ | EV_TIMEOUT | EV_CLOSE)
        self.assertEqual(test_eh2.flags, EV_START | EV_READ | EV_TIMEOUT | EV_CLOSE)
        self.assertEqual(worker1.node_buffer("localhost"), "alright")
        self.assertEqual(worker2.node_buffer("localhost"), "okay")
        self.assertEqual(worker1.num_timeout(), 1)
        self.assertEqual(worker2.num_timeout(), 1)
        self.assertEqual(self._task.num_timeout(), 2)

    def testShellEventsReadNoEOL(self):
        # init worker
        test_eh = self.__class__.TEventHandlerChecker(self)
        worker = self._task.shell("/bin/echo -n okay", nodes='localhost', handler=test_eh)
        self.assert_(worker != None)
        # run task
        self._task.resume()
        # test events received: start, close
        self.assertEqual(test_eh.flags, EV_START | EV_READ | EV_HUP | EV_CLOSE)
        self.assertEqual(worker.node_buffer("localhost"), "okay")

    def testShellEventsNoReadNoTimeout(self):
        # init worker
        test_eh = self.__class__.TEventHandlerChecker(self)
        worker = self._task.shell("/bin/sleep 2", nodes='localhost', handler=test_eh)
        self.assert_(worker != None)
        # run task
        self._task.resume()
        # test events received: start, close
        self.assertEqual(test_eh.flags, EV_START | EV_HUP | EV_CLOSE)
        self.assertEqual(worker.node_buffer("localhost"), None)

    def testLocalhostCommandFanout(self):
        fanout = self._task.info("fanout")
        self._task.set_info("fanout", 2)
        # init worker
        for i in range(0, 10):
            worker = self._task.shell("/bin/echo %d" % i, nodes='localhost')
            self.assert_(worker != None)
        # run task
        self._task.resume()
        # restore fanout value
        self._task.set_info("fanout", fanout)

    def testWorkerBuffers(self):
        task = task_self()
        self.assert_(task != None)

        worker = task.shell("/usr/bin/printf 'foo\nbar\nxxx\n'", nodes='localhost')
        task.resume()

        cnt = 2
        for buf, nodes in worker.iter_buffers():
            cnt -= 1
            if buf == "foo\nbar\nxxx\n":
                self.assertEqual(len(nodes), 1)
                self.assertEqual(str(nodes), "localhost")
        self.assertEqual(cnt, 1)
        # new check in 1.7 to ensure match_keys is not a string
        testgen = worker.iter_buffers("localhost")
        # cast to list to effectively iterate
        self.assertRaises(TypeError, list, testgen)
        # and also fixed an issue when match_keys was an empty list
        for buf, nodes in worker.iter_buffers([]):
            self.assertFalse("Found buffer with empty match_keys?!")
        for buf, nodes in worker.iter_buffers(["localhost"]):
            cnt -= 1
            if buf == "foo\nbar\nxxx\n":
                self.assertEqual(len(nodes), 1)
                self.assertEqual(str(nodes), "localhost")
        self.assertEqual(cnt, 0)

    def testWorkerNodeBuffers(self):
        task = task_self()
        self.assert_(task != None)

        worker = task.shell("/usr/bin/printf 'foo\nbar\nxxx\n'",
                            nodes='localhost')

        task.resume()

        cnt = 1
        for node, buf in worker.iter_node_buffers():
            cnt -= 1
            if buf == "foo\nbar\nxxx\n":
                self.assertEqual(node, "localhost")
        self.assertEqual(cnt, 0)

    def testWorkerNodeErrors(self):
        task = task_self()
        self.assert_(task != None)

        worker = task.shell("/usr/bin/printf 'foo\nbar\nxxx\n' 1>&2",
                            nodes='localhost', stderr=True)

        task.resume()

        cnt = 1
        for node, buf in worker.iter_node_errors():
            cnt -= 1
            if buf == "foo\nbar\nxxx\n":
                self.assertEqual(node, "localhost")
        self.assertEqual(cnt, 0)

    def testWorkerRetcodes(self):
        task = task_self()
        self.assert_(task != None)

        worker = task.shell("/bin/sh -c 'exit 3'", nodes="localhost")

        task.resume()

        cnt = 2
        for rc, keys in worker.iter_retcodes():
            cnt -= 1
            self.assertEqual(rc, 3)
            self.assertEqual(len(keys), 1)
            self.assert_(keys[0] == "localhost")

        self.assertEqual(cnt, 1)

        for rc, keys in worker.iter_retcodes("localhost"):
            cnt -= 1
            self.assertEqual(rc, 3)
            self.assertEqual(len(keys), 1)
            self.assert_(keys[0] == "localhost")

        self.assertEqual(cnt, 0)

        # test node_retcode
        self.assertEqual(worker.node_retcode("localhost"), 3)   # 1.2.91+
        self.assertEqual(worker.node_rc("localhost"), 3)

        # test node_retcode failure
        self.assertRaises(KeyError, worker.node_retcode, "dummy")

        # test max retcode API
        self.assertEqual(task.max_retcode(), 3)

    def testWorkerNodeRetcodes(self):
        task = task_self()
        self.assert_(task != None)

        worker = task.shell("/bin/sh -c 'exit 3'", nodes="localhost")

        task.resume()

        cnt = 1
        for node, rc in worker.iter_node_retcodes():
            cnt -= 1
            self.assertEqual(rc, 3)
            self.assertEqual(node, "localhost")

        self.assertEqual(cnt, 0)

    def testEscape(self):
        worker = self._task.shell("export CSTEST=foobar; /bin/echo \$CSTEST | sed 's/\ foo/bar/'", nodes="localhost")
        # execute
        self._task.resume()
        # read result
        self.assertEqual(worker.node_buffer("localhost"), "$CSTEST")

    def testEscape2(self):
        worker = self._task.shell("export CSTEST=foobar; /bin/echo $CSTEST | sed 's/\ foo/bar/'", nodes="localhost")
        # execute
        self._task.resume()
        # read result
        self.assertEqual(worker.node_buffer("localhost"), "foobar")

    def testSshUserOption(self):
        ssh_user_orig = self._task.info("ssh_user")
        self._task.set_info("ssh_user", pwd.getpwuid(os.getuid())[0])
        worker = self._task.shell("/bin/echo foobar", nodes="localhost")
        self.assert_(worker != None)
        self._task.resume()
        # restore original ssh_user (None)
        self.assertEqual(ssh_user_orig, None)
        self._task.set_info("ssh_user", ssh_user_orig)

    def testSshUserOptionForScp(self):
        ssh_user_orig = self._task.info("ssh_user")
        self._task.set_info("ssh_user", pwd.getpwuid(os.getuid())[0])
        dest = make_temp_filename('testLocalhostCopyU')
        worker = self._task.copy("/etc/hosts", dest, nodes='localhost')
        self.assert_(worker != None)
        self._task.resume()
        # restore original ssh_user (None)
        self.assertEqual(ssh_user_orig, None)
        self._task.set_info("ssh_user", ssh_user_orig)
        os.unlink(dest)

    def testSshOptionsOption(self):
        ssh_options_orig = self._task.info("ssh_options")
        try:
            self._task.set_info("ssh_options", "-oLogLevel=QUIET")
            worker = self._task.shell("/bin/echo foobar", nodes="localhost")
            self.assert_(worker != None)
            self._task.resume()
            self.assertEqual(worker.node_buffer("localhost"), "foobar")
            # test 3 options
            self._task.set_info("ssh_options", \
                "-oLogLevel=QUIET -oStrictHostKeyChecking=no -oVerifyHostKeyDNS=no")
            worker = self._task.shell("/bin/echo foobar3", nodes="localhost")
            self.assert_(worker != None)
            self._task.resume()
            self.assertEqual(worker.node_buffer("localhost"), "foobar3")
        finally:
            # restore original ssh_user (None)
            self.assertEqual(ssh_options_orig, None)
            self._task.set_info("ssh_options", ssh_options_orig)

    def testSshOptionsOptionForScp(self):
        ssh_options_orig = self._task.info("ssh_options")
        testfile = None
        try:
            testfile = make_temp_filename('testLocalhostCopyO')
            if os.path.exists(testfile):
                os.remove(testfile)
            self._task.set_info("ssh_options", \
                "-oLogLevel=QUIET -oStrictHostKeyChecking=no -oVerifyHostKeyDNS=no")
            worker = self._task.copy("/etc/hosts", testfile, nodes='localhost')
            self.assert_(worker != None)
            self._task.resume()
            self.assert_(os.path.exists(testfile))
        finally:
            os.unlink(testfile)
            # restore original ssh_user (None)
            self.assertEqual(ssh_options_orig, None)
            self._task.set_info("ssh_options", ssh_options_orig)

    def testShellStderrWithHandler(self):
        class StdErrHandler(EventHandler):
            def ev_error(self, worker):
                assert worker.last_error() == "something wrong"

        worker = self._task.shell("echo something wrong 1>&2", nodes='localhost',
                                  handler=StdErrHandler())
        self._task.resume()
        for buf, nodes in worker.iter_errors():
            self.assertEqual(buf, "something wrong")
        for buf, nodes in worker.iter_errors(['localhost']):
            self.assertEqual(buf, "something wrong")

    def testShellWriteSimple(self):
        worker = self._task.shell("cat", nodes='localhost')
        worker.write("this is a test\n")
        worker.set_write_eof()
        self._task.resume()
        self.assertEqual(worker.node_buffer("localhost"), "this is a test")

    def testShellWriteHandler(self):
        class WriteOnReadHandler(EventHandler):
            def __init__(self, target_worker):
                self.target_worker = target_worker
            def ev_read(self, worker):
                self.target_worker.write("%s:%s\n" % worker.last_read())
                self.target_worker.set_write_eof()

        reader = self._task.shell("cat", nodes='localhost')
        worker = self._task.shell("sleep 1; echo foobar", nodes='localhost',
                                  handler=WriteOnReadHandler(reader))
        self._task.resume()
        self.assertEqual(reader.node_buffer("localhost"), "localhost:foobar")

    def testSshBadArgumentOption(self):
	# Check code < 1.4 compatibility
        self.assertRaises(WorkerBadArgumentError, WorkerSsh, "localhost",
			  None, None)
	# As of 1.4, ValueError is raised for missing parameter
        self.assertRaises(ValueError, WorkerSsh, "localhost",
			  None, None) # 1.4+

    def testCopyEvents(self):
        test_eh = self.__class__.TEventHandlerChecker(self)
        dest = make_temp_filename('testLocalhostCopyEvents')
        worker = self._task.copy("/etc/hosts", dest, nodes='localhost',
                handler=test_eh)
        self.assert_(worker != None)
        # run task
        self._task.resume()
        os.unlink(dest)
        self.assertEqual(test_eh.flags, EV_START | EV_HUP | EV_CLOSE)

    def testWorkerAbort(self):
        task = task_self()
        self.assert_(task != None)

        # Test worker.abort() in an event handler.
        class AbortOnTimer(EventHandler):
            def __init__(self, worker):
                EventHandler.__init__(self)
                self.ext_worker = worker
                self.testtimer = False
            def ev_timer(self, timer):
                self.ext_worker.abort()
                self.testtimer = True

        aot = AbortOnTimer(task.shell("sleep 10", nodes="localhost"))
        self.assertEqual(aot.testtimer, False)
        task.timer(1.5, handler=aot)
        task.resume()
        self.assertEqual(aot.testtimer, True)

    def testWorkerAbortSanity(self):
        task = task_self()
        worker = task.shell("sleep 1", nodes="localhost")
        worker.abort()

        # test noop abort() on unscheduled worker
        worker = WorkerSsh("localhost", command="sleep 1", handler=None,
                           timeout=None)
        worker.abort()

    def testLocalhostExplicitSshReverseCopy(self):
        dest = make_temp_dir('testLocalhostExplicitSshRCopy')
        try:
            worker = WorkerSsh("localhost", source="/etc/hosts",
                    dest=dest, handler=None, timeout=10, reverse=True)
            self._task.schedule(worker)
            self._task.resume()
            self.assertEqual(worker.source, "/etc/hosts")
            self.assertEqual(worker.dest, dest)
            self.assert_(os.path.exists(os.path.join(dest, "hosts.localhost")))
        finally:
            shutil.rmtree(dest, ignore_errors=True)

    def testLocalhostExplicitSshReverseCopyDir(self):
        dtmp_src = make_temp_dir('src')
        dtmp_dst = make_temp_dir('testLocalhostExplicitSshReverseCopyDir')
        try:
            os.mkdir(os.path.join(dtmp_src, "lev1_a"))
            os.mkdir(os.path.join(dtmp_src, "lev1_b"))
            os.mkdir(os.path.join(dtmp_src, "lev1_a", "lev2"))
            worker = WorkerSsh("localhost", source=dtmp_src,
                    dest=dtmp_dst, handler=None, timeout=30, reverse=True)
            self._task.schedule(worker)
            self._task.resume()
            self.assert_(os.path.exists(os.path.join(dtmp_dst, \
                "%s.localhost" % os.path.basename(dtmp_src), "lev1_a", "lev2")))
        finally:
            shutil.rmtree(dtmp_dst, ignore_errors=True)
            shutil.rmtree(dtmp_src, ignore_errors=True)

    def testLocalhostExplicitSshReverseCopyDirPreserve(self):
        dtmp_src = make_temp_dir('src')
        dtmp_dst = make_temp_dir('testLocalhostExplicitSshReverseCopyDirPreserve')
        try:
            os.mkdir(os.path.join(dtmp_src, "lev1_a"))
            os.mkdir(os.path.join(dtmp_src, "lev1_b"))
            os.mkdir(os.path.join(dtmp_src, "lev1_a", "lev2"))
            worker = WorkerSsh("localhost", source=dtmp_src,
                    dest=dtmp_dst, handler=None, timeout=30, reverse=True)
            self._task.schedule(worker)
            self._task.resume()
            self.assert_(os.path.exists(os.path.join(dtmp_dst, \
                "%s.localhost" % os.path.basename(dtmp_src), "lev1_a", "lev2")))
        finally:
            shutil.rmtree(dtmp_dst, ignore_errors=True)
            shutil.rmtree(dtmp_src, ignore_errors=True)

    def testErroneousSshPath(self):
        try:
            self._task.set_info("ssh_path", "/wrong/path/to/ssh")
            # init worker
            worker = self._task.shell("/bin/echo ok", nodes='localhost')
            self.assert_(worker != None)
            # run task
            self._task.resume()
            self.assertEqual(self._task.max_retcode(), 255)
        finally:
            # restore fanout value
            self._task.set_info("ssh_path", None)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TaskDistantTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = TaskDistantPdshMixin
#!/usr/bin/env python
# ClusterShell (distant, pdsh worker) test suite
# Written by S. Thiell 2009-02-13


"""Unit test for ClusterShell Task (distant, pdsh worker)"""

import copy
import shutil
import sys

sys.path.insert(0, '../lib')

from TLib import make_temp_filename, make_temp_dir
from ClusterShell.Event import EventHandler
from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import *
from ClusterShell.Worker.Worker import WorkerBadArgumentError
from ClusterShell.Worker.Pdsh import WorkerPdsh
from ClusterShell.Worker.EngineClient import *

import socket

# TEventHandlerChecker 'received event' flags
EV_START=0x01
EV_READ=0x02
EV_WRITTEN=0x04
EV_HUP=0x08
EV_TIMEOUT=0x10
EV_CLOSE=0x20

class TaskDistantPdshMixin(object):

    def setUp(self):
        self._task = task_self()
        self.assert_(self._task != None)

    def testWorkerPdshGetCommand(self):
        # test worker.command with WorkerPdsh
        worker1 = WorkerPdsh("localhost", command="/bin/echo foo bar fuu",
                             handler=None, timeout=5)
        self.assert_(worker1 != None)
        self._task.schedule(worker1)
        worker2 = WorkerPdsh("localhost", command="/bin/echo blah blah foo",
                             handler=None, timeout=5)
        self.assert_(worker2 != None)
        self._task.schedule(worker2)
        # run task
        self._task.resume()
        # test output
        self.assertEqual(worker1.node_buffer("localhost"), "foo bar fuu")
        self.assertEqual(worker1.command, "/bin/echo foo bar fuu")
        self.assertEqual(worker2.node_buffer("localhost"), "blah blah foo")
        self.assertEqual(worker2.command, "/bin/echo blah blah foo")

    def testLocalhostExplicitPdshCopy(self):
        # test simple localhost copy with explicit pdsh worker
        dest = make_temp_filename(suffix='LocalhostExplicitPdshCopy')
        try:
            worker = WorkerPdsh("localhost", source="/etc/hosts",
                    dest=dest, handler=None, timeout=10)
            self._task.schedule(worker)
            self._task.resume()
            self.assertEqual(worker.source, "/etc/hosts")
            self.assertEqual(worker.dest, dest)
        finally:
            os.unlink(dest)

    def testLocalhostExplicitPdshCopyDir(self):
        # test simple localhost copy dir with explicit pdsh worker
        dtmp_src = make_temp_dir('src')
        # pdcp worker doesn't create custom destination directory
        dtmp_dst = make_temp_dir('testLocalhostExplicitPdshCopyDir')
        try:
            os.mkdir(os.path.join(dtmp_src, "lev1_a"))
            os.mkdir(os.path.join(dtmp_src, "lev1_b"))
            os.mkdir(os.path.join(dtmp_src, "lev1_a", "lev2"))
            worker = WorkerPdsh("localhost", source=dtmp_src,
                    dest=dtmp_dst, handler=None, timeout=10)
            self._task.schedule(worker)
            self._task.resume()
            self.assertTrue(os.path.exists(os.path.join(dtmp_dst, \
                os.path.basename(dtmp_src), "lev1_a", "lev2")))
        finally:
            shutil.rmtree(dtmp_dst, ignore_errors=True)
            shutil.rmtree(dtmp_src, ignore_errors=True)

    def testLocalhostExplicitPdshCopyDirPreserve(self):
        # test simple localhost preserve copy dir with explicit pdsh worker
        dtmp_src = make_temp_dir('src')
        # pdcp worker doesn't create custom destination directory
        dtmp_dst = make_temp_dir('testLocalhostExplicitPdshCopyDirPreserve')
        try:
            os.mkdir(os.path.join(dtmp_src, "lev1_a"))
            os.mkdir(os.path.join(dtmp_src, "lev1_b"))
            os.mkdir(os.path.join(dtmp_src, "lev1_a", "lev2"))
            worker = WorkerPdsh("localhost", source=dtmp_src,
                    dest=dtmp_dst, handler=None, timeout=10, preserve=True)
            self._task.schedule(worker)
            self._task.resume()
            self.assert_(os.path.exists(os.path.join(dtmp_dst, \
                os.path.basename(dtmp_src), "lev1_a", "lev2")))
        finally:
            shutil.rmtree(dtmp_dst, ignore_errors=True)
            shutil.rmtree(dtmp_src, ignore_errors=True)

    def testExplicitPdshWorker(self):
        # test simple localhost command with explicit pdsh worker
        # init worker
        worker = WorkerPdsh("localhost", command="echo alright", handler=None, timeout=5)
        self.assert_(worker != None)
        self._task.schedule(worker)
        # run task
        self._task.resume()
        # test output
        self.assertEqual(worker.node_buffer("localhost"), "alright")

    def testExplicitPdshWorkerStdErr(self):
        # test simple localhost command with explicit pdsh worker (stderr)
        # init worker
        worker = WorkerPdsh("localhost", command="echo alright 1>&2",
                    handler=None, stderr=True, timeout=5)
        self.assert_(worker != None)
        self._task.schedule(worker)
        # run task
        self._task.resume()
        # test output
        self.assertEqual(worker.node_error_buffer("localhost"), "alright")

        # Re-test with stderr=False
        worker = WorkerPdsh("localhost", command="echo alright 1>&2",
                    handler=None, stderr=False, timeout=5)
        self.assert_(worker != None)
        self._task.schedule(worker)
        # run task
        self._task.resume()
        # test output
        self.assertEqual(worker.node_error_buffer("localhost"), None)


    def testPdshWorkerWriteNotSupported(self):
        # test that write is reported as not supported with pdsh
        # init worker
        worker = WorkerPdsh("localhost", command="uname -r", handler=None, timeout=5)
        self.assertRaises(EngineClientNotSupportedError, worker.write, "toto")

    class TEventHandlerChecker(EventHandler):
        """simple event trigger validator"""
        def __init__(self, test):
            self.test = test
            self.flags = 0
            self.read_count = 0
            self.written_count = 0
        def ev_start(self, worker):
            self.test.assertEqual(self.flags, 0)
            self.flags |= EV_START
        def ev_read(self, worker):
            self.test.assertEqual(self.flags, EV_START)
            self.flags |= EV_READ
            self.last_node, self.last_read = worker.last_read()
        def ev_written(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_WRITTEN
        def ev_hup(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_HUP
            self.last_rc = worker.last_retcode()
        def ev_timeout(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_TIMEOUT
            self.last_node = worker.last_node()
        def ev_close(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.test.assert_(self.flags & EV_CLOSE == 0)
            self.flags |= EV_CLOSE

    def testExplicitWorkerPdshShellEvents(self):
        # test triggered events with explicit pdsh worker
        # init worker
        test_eh = self.__class__.TEventHandlerChecker(self)
        worker = WorkerPdsh("localhost", command="hostname", handler=test_eh, timeout=None)
        self.assert_(worker != None)
        self._task.schedule(worker)
        # run task
        self._task.resume()
        # test events received: start, read, hup, close
        self.assertEqual(test_eh.flags, EV_START | EV_READ | EV_HUP | EV_CLOSE)

    def testExplicitWorkerPdshShellEventsWithTimeout(self):
        # test triggered events (with timeout) with explicit pdsh worker
        # init worker
        test_eh = self.__class__.TEventHandlerChecker(self)
        worker = WorkerPdsh("localhost", command="echo alright && sleep 10",
                handler=test_eh, timeout=2)
        self.assert_(worker != None)
        self._task.schedule(worker)
        # run task
        self._task.resume()
        # test events received: start, read, timeout, close
        self.assertEqual(test_eh.flags, EV_START | EV_READ | EV_TIMEOUT | EV_CLOSE)
        self.assertEqual(worker.node_buffer("localhost"), "alright")

    def testShellPdshEventsNoReadNoTimeout(self):
        # test triggered events (no read, no timeout) with explicit pdsh worker
        # init worker
        test_eh = self.__class__.TEventHandlerChecker(self)
        worker = WorkerPdsh("localhost", command="sleep 2",
                handler=test_eh, timeout=None)
        self.assert_(worker != None)
        self._task.schedule(worker)
        # run task
        self._task.resume()
        # test events received: start, close
        self.assertEqual(test_eh.flags, EV_START | EV_HUP | EV_CLOSE)
        self.assertEqual(worker.node_buffer("localhost"), None)

    def testWorkerPdshBuffers(self):
        # test buffers at pdsh worker level
        task = task_self()
        self.assert_(task != None)

        worker = WorkerPdsh("localhost", command="printf 'foo\nbar\nxxx\n'",
                            handler=None, timeout=None)
        task.schedule(worker)
        task.resume()

        cnt = 2
        for buf, nodes in worker.iter_buffers():
            cnt -= 1
            if buf == "foo\nbar\nxxx\n":
                self.assertEqual(len(nodes), 1)
                self.assertEqual(str(nodes), "localhost")
        self.assertEqual(cnt, 1)
        # new check in 1.7 to ensure match_keys is not a string
        testgen = worker.iter_buffers("localhost")
        # cast to list to effectively iterate
        self.assertRaises(TypeError, list, testgen)
        # and also fixed an issue when match_keys was an empty list
        for buf, nodes in worker.iter_buffers([]):
            self.assertFalse("Found buffer with empty match_keys?!")
        for buf, nodes in worker.iter_buffers(["localhost"]):
            cnt -= 1
            if buf == "foo\nbar\nxxx\n":
                self.assertEqual(len(nodes), 1)
                self.assertEqual(str(nodes), "localhost")
        self.assertEqual(cnt, 0)

    def testWorkerPdshNodeBuffers(self):
        # test iter_node_buffers on distant pdsh workers
        task = task_self()
        self.assert_(task != None)

        worker = WorkerPdsh("localhost", command="/usr/bin/printf 'foo\nbar\nxxx\n'",
                            handler=None, timeout=None)
        task.schedule(worker)
        task.resume()

        cnt = 1
        for node, buf in worker.iter_node_buffers():
            cnt -= 1
            if buf == "foo\nbar\nxxx\n":
                self.assertEqual(node, "localhost")
        self.assertEqual(cnt, 0)

    def testWorkerPdshNodeErrors(self):
        # test iter_node_errors on distant pdsh workers
        task = task_self()
        self.assert_(task != None)

        worker = WorkerPdsh("localhost", command="/usr/bin/printf 'foo\nbar\nxxx\n' 1>&2",
                            handler=None, timeout=None, stderr=True)
        task.schedule(worker)
        task.resume()

        cnt = 1
        for node, buf in worker.iter_node_errors():
            cnt -= 1
            if buf == "foo\nbar\nxxx\n":
                self.assertEqual(node, "localhost")
        self.assertEqual(cnt, 0)

    def testWorkerPdshRetcodes(self):
        # test retcodes on distant pdsh workers
        task = task_self()
        self.assert_(task != None)

        worker = WorkerPdsh("localhost", command="/bin/sh -c 'exit 3'",
                            handler=None, timeout=None)
        task.schedule(worker)
        task.resume()

        cnt = 2
        for rc, keys in worker.iter_retcodes():
            cnt -= 1
            self.assertEqual(rc, 3)
            self.assertEqual(len(keys), 1)
            self.assert_(keys[0] == "localhost")

        self.assertEqual(cnt, 1)

        for rc, keys in worker.iter_retcodes("localhost"):
            cnt -= 1
            self.assertEqual(rc, 3)
            self.assertEqual(len(keys), 1)
            self.assert_(keys[0] == "localhost")

        self.assertEqual(cnt, 0)

        # test node_retcode
        self.assertEqual(worker.node_retcode("localhost"), 3)   # 1.2.91+
        self.assertEqual(worker.node_rc("localhost"), 3)

        # test node_retcode failure
        self.assertRaises(KeyError, worker.node_retcode, "dummy")

        # test max retcode API
        self.assertEqual(task.max_retcode(), 3)

    def testWorkerNodeRetcodes(self):
        # test iter_node_retcodes on distant pdsh workers
        task = task_self()
        self.assert_(task != None)

        worker = WorkerPdsh("localhost", command="/bin/sh -c 'exit 3'",
                            handler=None, timeout=None)
        task.schedule(worker)
        task.resume()

        cnt = 1
        for node, rc in worker.iter_node_retcodes():
            cnt -= 1
            self.assertEqual(rc, 3)
            self.assertEqual(node, "localhost")

        self.assertEqual(cnt, 0)

    def testEscapePdsh(self):
        # test distant worker (pdsh) cmd with escaped variable
        worker = WorkerPdsh("localhost", command="export CSTEST=foobar; /bin/echo \$CSTEST | sed 's/\ foo/bar/'",
                handler=None, timeout=None)
        self.assert_(worker != None)
        #task.set_info("debug", True)
        self._task.schedule(worker)
        # execute
        self._task.resume()
        # read result
        self.assertEqual(worker.node_buffer("localhost"), "$CSTEST")

    def testEscapePdsh2(self):
        # test distant worker (pdsh) cmd with non-escaped variable
        worker = WorkerPdsh("localhost", command="export CSTEST=foobar; /bin/echo $CSTEST | sed 's/\ foo/bar/'",
                handler=None, timeout=None)
        self._task.schedule(worker)
        # execute
        self._task.resume()
        # read result
        self.assertEqual(worker.node_buffer("localhost"), "foobar")

    def testShellPdshStderrWithHandler(self):
        # test reading stderr of distant pdsh worker on event handler
        class StdErrHandler(EventHandler):
            def ev_error(self, worker):
                assert worker.last_error() == "something wrong"

        worker = WorkerPdsh("localhost", command="echo something wrong 1>&2",
                handler=StdErrHandler(), timeout=None)
        self._task.schedule(worker)
        self._task.resume()
        for buf, nodes in worker.iter_errors():
            self.assertEqual(buf, "something wrong")
        for buf, nodes in worker.iter_errors(['localhost']):
            self.assertEqual(buf, "something wrong")

    def testCommandTimeoutOption(self):
        # test pdsh shell with command_timeout set
        command_timeout_orig = self._task.info("command_timeout")
        self._task.set_info("command_timeout", 1)
        worker = WorkerPdsh("localhost", command="sleep 10",
                handler=None, timeout=None)
        self._task.schedule(worker)
        self.assert_(worker != None)
        self._task.resume()
        # restore original command_timeout (0)
        self.assertEqual(command_timeout_orig, 0)
        self._task.set_info("command_timeout", command_timeout_orig)

    def testPdshBadArgumentOption(self):
        # test WorkerPdsh constructor bad argument
	# Check code < 1.4 compatibility
        self.assertRaises(WorkerBadArgumentError, WorkerPdsh, "localhost",
			  None, None)
	# As of 1.4, ValueError is raised for missing parameter
        self.assertRaises(ValueError, WorkerPdsh, "localhost",
			  None, None) # 1.4+

    def testCopyEvents(self):
        test_eh = self.__class__.TEventHandlerChecker(self)
        dest = "/tmp/cs-test_testLocalhostPdshCopyEvents"
        try:
            worker = WorkerPdsh("localhost", source="/etc/hosts",
                    dest=dest, handler=test_eh, timeout=10)
            self._task.schedule(worker)
            self._task.resume()
            self.assertEqual(test_eh.flags, EV_START | EV_HUP | EV_CLOSE)
        finally:
            os.remove(dest)

    def testWorkerAbort(self):
        # test WorkerPdsh abort() on timer
        task = task_self()
        self.assert_(task != None)

        class AbortOnTimer(EventHandler):
            def __init__(self, worker):
                EventHandler.__init__(self)
                self.ext_worker = worker
                self.testtimer = False
            def ev_timer(self, timer):
                self.ext_worker.abort()
                self.testtimer = True

        worker = WorkerPdsh("localhost", command="sleep 10",
                handler=None, timeout=None)
        task.schedule(worker)

        aot = AbortOnTimer(worker)
        self.assertEqual(aot.testtimer, False)
        task.timer(2.0, handler=aot)
        task.resume()
        self.assertEqual(aot.testtimer, True)

    def testWorkerAbortSanity(self):
        # test WorkerPdsh abort() (sanity)
        task = task_self()
        # test noop abort() on unscheduled worker
        worker = WorkerPdsh("localhost", command="sleep 1", handler=None,
                            timeout=None)
        worker.abort()

    def testLocalhostExplicitPdshReverseCopy(self):
        # test simple localhost rcopy with explicit pdsh worker
        dest = "/tmp/cs-test_testLocalhostExplicitPdshRCopy"
        shutil.rmtree(dest, ignore_errors=True)
        try:
            os.mkdir(dest)
            worker = WorkerPdsh("localhost", source="/etc/hosts",
                    dest=dest, handler=None, timeout=10, reverse=True)
            self._task.schedule(worker)
            self._task.resume()
            self.assertEqual(worker.source, "/etc/hosts")
            self.assertEqual(worker.dest, dest)
            self.assert_(os.path.exists(os.path.join(dest, "hosts.localhost")))
        finally:
            shutil.rmtree(dest, ignore_errors=True)

    def testLocalhostExplicitPdshReverseCopyDir(self):
        # test simple localhost rcopy dir with explicit pdsh worker
        dtmp_src = make_temp_dir('src')
        dtmp_dst = make_temp_dir('testLocalhostExplicitPdshReverseCopyDir')
        try:
            os.mkdir(os.path.join(dtmp_src, "lev1_a"))
            os.mkdir(os.path.join(dtmp_src, "lev1_b"))
            os.mkdir(os.path.join(dtmp_src, "lev1_a", "lev2"))
            worker = WorkerPdsh("localhost", source=dtmp_src,
                    dest=dtmp_dst, handler=None, timeout=30, reverse=True)
            self._task.schedule(worker)
            self._task.resume()
            self.assert_(os.path.exists(os.path.join(dtmp_dst, \
                "%s.localhost" % os.path.basename(dtmp_src), "lev1_a", "lev2")))
        finally:
            shutil.rmtree(dtmp_dst, ignore_errors=True)
            shutil.rmtree(dtmp_src, ignore_errors=True)

    def testLocalhostExplicitPdshReverseCopyDirPreserve(self):
        # test simple localhost preserve rcopy dir with explicit pdsh worker
        dtmp_src = make_temp_dir('src')
        dtmp_dst = make_temp_dir('testLocalhostExplicitPdshReverseCopyDirPreserve')
        try:
            os.mkdir(os.path.join(dtmp_src, "lev1_a"))
            os.mkdir(os.path.join(dtmp_src, "lev1_b"))
            os.mkdir(os.path.join(dtmp_src, "lev1_a", "lev2"))
            worker = WorkerPdsh("localhost", source=dtmp_src,
                    dest=dtmp_dst, handler=None, timeout=30, preserve=True,
                    reverse=True)
            self._task.schedule(worker)
            self._task.resume()
            self.assert_(os.path.exists(os.path.join(dtmp_dst, \
                "%s.localhost" % os.path.basename(dtmp_src), "lev1_a", "lev2")))
        finally:
            shutil.rmtree(dtmp_dst, ignore_errors=True)
            shutil.rmtree(dtmp_src, ignore_errors=True)



########NEW FILE########
__FILENAME__ = TaskDistantPdshTest
#!/usr/bin/env python


"""Unit test for ClusterShell Task with all engines (pdsh distant worker)"""

import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.Engine.Select import EngineSelect
from ClusterShell.Engine.Poll import EnginePoll
from ClusterShell.Engine.EPoll import EngineEPoll
from ClusterShell.Task import *

from TaskDistantPdshMixin import TaskDistantPdshMixin

ENGINE_SELECT_ID = EngineSelect.identifier
ENGINE_POLL_ID = EnginePoll.identifier
ENGINE_EPOLL_ID = EngineEPoll.identifier

class TaskDistantPdshEngineSelectTest(TaskDistantPdshMixin, unittest.TestCase):

    def setUp(self):
        task_terminate()
        self.engine_id_save = Task._std_default['engine']
        Task._std_default['engine'] = ENGINE_SELECT_ID
        # select should be supported anywhere...
        self.assertEqual(task_self().info('engine'), ENGINE_SELECT_ID)
        TaskDistantPdshMixin.setUp(self)

    def tearDown(self):
        Task._std_default['engine'] = self.engine_id_save
        task_terminate()

class TaskDistantPdshEnginePollTest(TaskDistantPdshMixin, unittest.TestCase):

    def setUp(self):
        task_terminate()
        self.engine_id_save = Task._std_default['engine']
        Task._std_default['engine'] = ENGINE_POLL_ID
        if task_self().info('engine') != ENGINE_POLL_ID:
            self.skipTest("engine %s not supported on this host" % ENGINE_POLL_ID)
        TaskDistantPdshMixin.setUp(self)

    def tearDown(self):
        Task._std_default['engine'] = self.engine_id_save
        task_terminate()

# select.epoll is only available with Python 2.6 (if condition to be
# removed once we only support Py2.6+)
if sys.version_info >= (2, 6, 0):

    class TaskDistantPdshEngineEPollTest(TaskDistantPdshMixin, unittest.TestCase):

        def setUp(self):
            task_terminate()
            self.engine_id_save = Task._std_default['engine']
            Task._std_default['engine'] = ENGINE_EPOLL_ID
            if task_self().info('engine') != ENGINE_EPOLL_ID:
                self.skipTest("engine %s not supported on this host" % ENGINE_EPOLL_ID)
            TaskDistantPdshMixin.setUp(self)

        def tearDown(self):
            Task._std_default['engine'] = self.engine_id_save
            task_terminate()


########NEW FILE########
__FILENAME__ = TaskDistantTest
#!/usr/bin/env python


"""Unit test for ClusterShell Task with all engines (distant worker)"""

import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.Engine.Select import EngineSelect
from ClusterShell.Engine.Poll import EnginePoll
from ClusterShell.Engine.EPoll import EngineEPoll
from ClusterShell.Task import *

from TaskDistantMixin import TaskDistantMixin

ENGINE_SELECT_ID = EngineSelect.identifier
ENGINE_POLL_ID = EnginePoll.identifier
ENGINE_EPOLL_ID = EngineEPoll.identifier

class TaskDistantEngineSelectTest(TaskDistantMixin, unittest.TestCase):

    def setUp(self):
        task_terminate()
        self.engine_id_save = Task._std_default['engine']
        Task._std_default['engine'] = ENGINE_SELECT_ID
        # select should be supported anywhere...
        self.assertEqual(task_self().info('engine'), ENGINE_SELECT_ID)
        TaskDistantMixin.setUp(self)

    def tearDown(self):
        Task._std_default['engine'] = self.engine_id_save
        task_terminate()

class TaskDistantEnginePollTest(TaskDistantMixin, unittest.TestCase):

    def setUp(self):
        task_terminate()
        self.engine_id_save = Task._std_default['engine']
        Task._std_default['engine'] = ENGINE_POLL_ID
        if task_self().info('engine') != ENGINE_POLL_ID:
            self.skipTest("engine %s not supported on this host" % ENGINE_POLL_ID)
        TaskDistantMixin.setUp(self)

    def tearDown(self):
        Task._std_default['engine'] = self.engine_id_save
        task_terminate()

# select.epoll is only available with Python 2.6 (if condition to be
# removed once we only support Py2.6+)
if sys.version_info >= (2, 6, 0):

    class TaskDistantEngineEPollTest(TaskDistantMixin, unittest.TestCase):

        def setUp(self):
            task_terminate()
            self.engine_id_save = Task._std_default['engine']
            Task._std_default['engine'] = ENGINE_EPOLL_ID
            if task_self().info('engine') != ENGINE_EPOLL_ID:
                self.skipTest("engine %s not supported on this host" % ENGINE_EPOLL_ID)
            TaskDistantMixin.setUp(self)

        def tearDown(self):
            Task._std_default['engine'] = self.engine_id_save
            task_terminate()


########NEW FILE########
__FILENAME__ = TaskEventTest
#!/usr/bin/env python
# ClusterShell (local) test suite
# Written by S. Thiell 2008-04-09


"""Unit test for ClusterShell Task (event-based mode)"""

import copy
import sys
import unittest

sys.path.insert(0, '../lib')

import ClusterShell

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import *
from ClusterShell.Event import EventHandler

import socket
import thread


class TestHandler(EventHandler):

    def __init__(self):
        self.reset_asserts()

    def do_asserts_read_notimeout(self):
        assert self.did_start, "ev_start not called"
        assert self.did_read, "ev_read not called"
        assert not self.did_readerr, "ev_error called"
        assert self.did_close, "ev_close not called"
        assert not self.did_timeout, "ev_timeout called"

    def do_asserts_timeout(self):
        assert self.did_start, "ev_start not called"
        assert not self.did_read, "ev_read called"
        assert not self.did_readerr, "ev_error called"
        assert self.did_close, "ev_close not called"
        assert self.did_timeout, "ev_timeout not called"

    def reset_asserts(self):
        self.did_start = False
        self.did_open = False
        self.did_read = False
        self.did_readerr = False
        self.did_close = False
        self.did_timeout = False

    def ev_start(self, worker):
        self.did_start = True

    def ev_read(self, worker):
        self.did_read = True
        assert worker.last_read() == "abcdefghijklmnopqrstuvwxyz"
        assert worker.last_error() != "abcdefghijklmnopqrstuvwxyz"

    def ev_error(self, worker):
        self.did_readerr = True
        assert worker.last_error() == "errerrerrerrerrerrerrerr"
        assert worker.last_read() != "errerrerrerrerrerrerrerr"

    def ev_close(self, worker):
        self.did_close = True
        if worker.read():
            assert worker.read().startswith("abcdefghijklmnopqrstuvwxyz")

    def ev_timeout(self, worker):
        self.did_timeout = True

class AbortOnReadHandler(EventHandler):
    def ev_read(self, worker):
        worker.abort()

class TaskEventTest(unittest.TestCase):

    def testSimpleEventHandler(self):
        """test simple event handler"""
        task = task_self()
        self.assert_(task != None)
        eh = TestHandler()
        # init worker
        worker = task.shell("./test_command.py --test=cmp_out", handler=eh)
        self.assert_(worker != None)
        # run task
        task.resume()
        eh.do_asserts_read_notimeout()
        eh.reset_asserts()
        # re-test
        # init worker
        worker = task.shell("./test_command.py --test=cmp_out", handler=eh)
        self.assert_(worker != None)
        # run task
        task.resume()
        eh.do_asserts_read_notimeout()
        eh.reset_asserts()

    def testSimpleEventHandlerWithTaskTimeout(self):
        """test simple event handler with timeout"""
        task = task_self()
        self.assert_(task != None)

        eh = TestHandler()
        # init worker
        worker = task.shell("/bin/sleep 3", handler=eh)
        self.assert_(worker != None)

        try:
            task.resume(2)
        except TimeoutError:
            pass
        else:
            self.fail("did not detect timeout")

        eh.do_asserts_timeout()
       
    class TInFlyAdder(EventHandler):
        def ev_read(self, worker):
            assert worker.task.running()
            # in-fly workers addition
            other1 = worker.task.shell("/bin/sleep 1")
            assert other1 != None
            other2 = worker.task.shell("/bin/sleep 1")
            assert other2 != None

    def testEngineInFlyAdd(self):
        """test client add while running (in-fly add)"""
        task = task_self()
        self.assert_(task != None)
        eh = self.__class__.TInFlyAdder()
        worker = task.shell("/bin/uname", handler=eh)
        self.assert_(worker != None)
        task.resume()

    class TWriteOnStart(EventHandler):
        def ev_start(self, worker):
            assert worker.task.running()
            worker.write("foo bar\n")
        def ev_read(self, worker):
            assert worker.current_msg == "foo bar"
            worker.abort()

    def testWriteOnStartEvent(self):
        """test write on ev_start"""
        task = task_self()
        self.assert_(task != None)
        task.shell("cat", handler=self.__class__.TWriteOnStart())
        task.resume()
        
    def testEngineMayReuseFD(self):
        """test write + worker.abort() on read to reuse FDs"""
        task = task_self()
        fanout = task.info("fanout")
        try:
            task.set_info("fanout", 1)
            eh = AbortOnReadHandler()
            for i in range(10):
                worker = task.shell("echo ok; sleep 1", handler=eh)
                worker.write("OK\n")
                self.assert_(worker is not None)
            task.resume()
        finally:
            task.set_info("fanout", fanout)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TaskEventTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = TaskLocalMixin
#!/usr/bin/env python
# ClusterShell (local) test suite
# Written by S. Thiell 2008-04-09


"""Unit test for ClusterShell Task (local)"""

import copy
import os
import signal
import sys
import time

sys.path.insert(0, '../lib')

import ClusterShell

from ClusterShell.Event import EventHandler
from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import *
from ClusterShell.Worker.Worker import WorkerSimple, WorkerError
from ClusterShell.Worker.Worker import WorkerBadArgumentError

import socket

import threading
import tempfile


def _test_print_debug(task, s):
    # Use custom task info (prefix 'user_' is recommended)
    task.set_info("user_print_debug_last", s)

class TaskLocalMixin(object):
    """Mixin test case class: should be overrided and used in multiple
    inheritance with unittest.TestCase"""

    def testSimpleCommand(self):
        task = task_self()
        self.assert_(task != None)
        # init worker
        worker = task.shell("/bin/hostname")
        self.assert_(worker != None)
        # run task
        task.resume()

    def testSimpleDualTask(self):
        task0 = task_self()
        self.assert_(task0 != None)
        worker1 = task0.shell("/bin/hostname")
        worker2 = task0.shell("/bin/uname -a")
        task0.resume()
        b1 = copy.copy(worker1.read())
        b2 = copy.copy(worker2.read())
        task1 = task_self()
        self.assert_(task1 is task0)
        worker1 = task1.shell("/bin/hostname")
        self.assert_(worker1 != None)
        worker2 = task1.shell("/bin/uname -a")
        self.assert_(worker2 != None)
        task1.resume()
        self.assert_(worker2.read() == b2)
        self.assert_(worker1.read() == b1)

    def testSimpleCommandNoneArgs(self):
        task = task_self()
        self.assert_(task != None)
        # init worker
        worker = task.shell("/bin/hostname", nodes=None, handler=None)
        self.assert_(worker != None)
        # run task
        task.resume()

    def testSimpleMultipleCommands(self):
        task = task_self()
        self.assert_(task != None)
        # run commands
        workers = []
        for i in range(0, 100):
            workers.append(task.shell("/bin/hostname"))
        task.resume()
        # verify results
        hn = socket.gethostname()
        for i in range(0, 100):
            t_hn = workers[i].read().splitlines()[0]
            self.assertEqual(t_hn, hn)

    def testHugeOutputCommand(self):
        task = task_self()
        self.assert_(task != None)

        # init worker
        worker = task.shell("python test_command.py --test huge --rc 0")
        self.assert_(worker != None)

        # run task
        task.resume()
        self.assertEqual(worker.retcode(), 0)
        self.assertEqual(len(worker.read()), 699999)

    # task configuration
    def testTaskInfo(self):
        task = task_self()
        self.assert_(task != None)

        fanout = task.info("fanout")
        self.assertEqual(fanout, Task._std_info["fanout"])

    def testSimpleCommandTimeout(self):
        task = task_self()
        self.assert_(task != None)

        # init worker
        worker = task.shell("/bin/sleep 30")
        self.assert_(worker != None)

        # run task
        self.assertRaises(TimeoutError, task.resume, 1)

    def testSimpleCommandNoTimeout(self):
        task = task_self()
        self.assert_(task != None)

        # init worker
        worker = task.shell("/bin/sleep 1")
        self.assert_(worker != None)

        try:
            # run task
            task.resume(3)
        except TimeoutError:
            self.fail("did detect timeout")

    def testSimpleCommandNoTimeout(self):
        task = task_self()
        self.assert_(task != None)

        # init worker
        worker = task.shell("/bin/usleep 900000")
        self.assert_(worker != None)

        try:
            # run task
            task.resume(1)
        except TimeoutError:
            self.fail("did detect timeout")

    def testWorkersTimeout(self):
        task = task_self()
        self.assert_(task != None)

        # init worker
        worker = task.shell("/bin/sleep 6", timeout=1)
        self.assert_(worker != None)

        worker = task.shell("/bin/sleep 6", timeout=0.5)
        self.assert_(worker != None)

        try:
            # run task
            task.resume()
        except TimeoutError:
            self.fail("did detect timeout")

        self.assert_(worker.did_timeout())

    def testWorkersTimeout2(self):
        task = task_self()
        self.assert_(task != None)

        worker = task.shell("/bin/sleep 10", timeout=1)
        self.assert_(worker != None)

        worker = task.shell("/bin/sleep 10", timeout=0.5)
        self.assert_(worker != None)

        try:
            # run task
            task.resume()
        except TimeoutError:
            self.fail("did detect task timeout")

    def testWorkersAndTaskTimeout(self):
        task = task_self()
        self.assert_(task != None)

        worker = task.shell("/bin/sleep 10", timeout=5)
        self.assert_(worker != None)

        worker = task.shell("/bin/sleep 10", timeout=3)
        self.assert_(worker != None)

        self.assertRaises(TimeoutError, task.resume, 1)

    def testLocalEmptyBuffer(self):
        task = task_self()
        self.assert_(task != None)
        task.shell("true", key="empty")
        task.resume()
        self.assertEqual(task.key_buffer("empty"), '')
        for buf, keys in task.iter_buffers():
            self.assert_(False)

    def testLocalEmptyError(self):
        task = task_self()
        self.assert_(task != None)
        task.shell("true", key="empty")
        task.resume()
        self.assertEqual(task.key_error("empty"), '')
        for buf, keys in task.iter_errors():
            self.assert_(False)

    def testTaskKeyErrors(self):
        task = task_self()
        self.assert_(task != None)
        task.shell("true", key="dummy")
        task.resume()
        # task.key_retcode raises KeyError
        self.assertRaises(KeyError, task.key_retcode, "not_known")
        # unlike task.key_buffer/error
        self.assertEqual(task.key_buffer("not_known"), '')
        self.assertEqual(task.key_error("not_known"), '')

    def testLocalSingleLineBuffers(self):
        task = task_self()
        self.assert_(task != None)

        task.shell("/bin/echo foo", key="foo")
        task.shell("/bin/echo bar", key="bar")
        task.shell("/bin/echo bar", key="bar2")
        task.shell("/bin/echo foobar", key="foobar")
        task.shell("/bin/echo foobar", key="foobar2")
        task.shell("/bin/echo foobar", key="foobar3")

        task.resume()

        self.assert_(task.key_buffer("foobar") == "foobar")

        cnt = 3
        for buf, keys in task.iter_buffers():
            cnt -= 1
            if buf == "foo":
                self.assertEqual(len(keys), 1)
                self.assertEqual(keys[0], "foo")
            elif buf == "bar":
                self.assertEqual(len(keys), 2)
                self.assert_(keys[0] == "bar" or keys[1] == "bar")
            elif buf == "foobar":
                self.assertEqual(len(keys), 3)

        self.assertEqual(cnt, 0)

    def testLocalBuffers(self):
        task = task_self()
        self.assert_(task != None)

        task.shell("/usr/bin/printf 'foo\nbar\n'", key="foobar")
        task.shell("/usr/bin/printf 'foo\nbar\n'", key="foobar2")
        task.shell("/usr/bin/printf 'foo\nbar\n'", key="foobar3")
        task.shell("/usr/bin/printf 'foo\nbar\nxxx\n'", key="foobarX")
        task.shell("/usr/bin/printf 'foo\nfuu\n'", key="foofuu")
        task.shell("/usr/bin/printf 'faa\nber\n'", key="faaber")
        task.shell("/usr/bin/printf 'foo\nfuu\n'", key="foofuu2")

        task.resume()

        cnt = 4
        for buf, keys in task.iter_buffers():
            cnt -= 1
            if buf == "faa\nber\n":
                self.assertEqual(len(keys), 1)
                self.assert_(keys[0].startswith("faaber"))
            elif buf == "foo\nfuu\n":
                self.assertEqual(len(keys), 2)
                self.assert_(keys[0].startswith("foofuu"))
            elif buf == "foo\nbar\n":
                self.assertEqual(len(keys), 3)
            elif buf == "foo\nbar\nxxx\n":
                self.assertEqual(len(keys), 1)
                self.assert_(keys[0].startswith("foobarX"))
                self.assert_(keys[0].startswith("foobar"))
            elif buf == "foo\nbar\nxxx\n":
                self.assertEqual(len(keys), 1)
                self.assert_(keys[0].startswith("foobarX"))

        self.assertEqual(cnt, 0)

    def testLocalRetcodes(self):
        task = task_self()
        self.assert_(task != None)

        # 0 ['worker0']
        # 1 ['worker1']
        # 2 ['worker2']
        # 3 ['worker3bis', 'worker3']
        # 4 ['worker4']
        # 5 ['worker5bis', 'worker5']

        task.shell("true", key="worker0")
        task.shell("false", key="worker1")
        task.shell("/bin/sh -c 'exit 1'", key="worker1bis")
        task.shell("/bin/sh -c 'exit 2'", key="worker2")
        task.shell("/bin/sh -c 'exit 3'", key="worker3")
        task.shell("/bin/sh -c 'exit 3'", key="worker3bis")
        task.shell("/bin/sh -c 'exit 4'", key="worker4")
        task.shell("/bin/sh -c 'exit 1'", key="worker4")
        task.shell("/bin/sh -c 'exit 5'", key="worker5")
        task.shell("/bin/sh -c 'exit 5'", key="worker5bis")

        task.resume()

        # test key_retcode(key)
        self.assertEqual(task.key_retcode("worker2"), 2) # single
        self.assertEqual(task.key_retcode("worker4"), 4) # multiple
        self.assertRaises(KeyError, task.key_retcode, "worker9") # error

        cnt = 6
        for rc, keys in task.iter_retcodes():
            cnt -= 1
            if rc == 0:
                self.assertEqual(len(keys), 1)
                self.assert_(keys[0] == "worker0" )
            elif rc == 1:
                self.assertEqual(len(keys), 3)
                self.assert_(keys[0] in ("worker1", "worker1bis", "worker4"))
            elif rc == 2:
                self.assertEqual(len(keys), 1)
                self.assert_(keys[0] == "worker2" )
            elif rc == 3:
                self.assertEqual(len(keys), 2)
                self.assert_(keys[0] in ("worker3", "worker3bis"))
            elif rc == 4:
                self.assertEqual(len(keys), 1)
                self.assert_(keys[0] == "worker4" )
            elif rc == 5:
                self.assertEqual(len(keys), 2)
                self.assert_(keys[0] in ("worker5", "worker5bis"))

        self.assertEqual(cnt, 0)

        # test max retcode API
        self.assertEqual(task.max_retcode(), 5)

    def testCustomPrintDebug(self):
        task = task_self()
        self.assert_(task != None)

        # first test that simply changing print_debug doesn't enable debug
        default_print_debug = task.info("print_debug")
        try:
            task.set_info("print_debug", _test_print_debug)
            task.shell("true")
            task.resume()
            self.assertEqual(task.info("user_print_debug_last"), None)

            # with debug enabled, it should work
            task.set_info("debug", True)
            task.shell("true")
            task.resume()
            self.assertEqual(task.info("user_print_debug_last"), "POPEN: true")

            # remove debug
            task.set_info("debug", False)
            # re-run for default print debug callback code coverage
            task.shell("true")
            task.resume()
        finally:
            # restore default print_debug
            task.set_info("debug", False)
            task.set_info("print_debug", default_print_debug)

    def testLocalRCBufferGathering(self):
        task = task_self()
        self.assert_(task != None)

        task.shell("/usr/bin/printf 'foo\nbar\n' && exit 1", key="foobar5")
        task.shell("/usr/bin/printf 'foo\nbur\n' && exit 1", key="foobar2")
        task.shell("/usr/bin/printf 'foo\nbar\n' && exit 1", key="foobar3")
        task.shell("/usr/bin/printf 'foo\nfuu\n' && exit 5", key="foofuu")
        task.shell("/usr/bin/printf 'foo\nbar\n' && exit 4", key="faaber")
        task.shell("/usr/bin/printf 'foo\nfuu\n' && exit 1", key="foofuu2")

        task.resume()

        foobur = "foo\nbur"

        cnt = 5
        for rc, keys in task.iter_retcodes():
            for buf, keys in task.iter_buffers(keys):
                cnt -= 1
                if buf == "foo\nbar":
                    self.assert_(rc == 1 or rc == 4)
                elif foobur == buf:
                    self.assertEqual(rc, 1)
                elif "foo\nfuu" == buf:
                    self.assert_(rc == 1 or rc == 5)
                else:
                    self.fail("invalid buffer returned")

        self.assertEqual(cnt, 0)

    def testLocalBufferRCGathering(self):
        task = task_self()
        self.assert_(task != None)

        task.shell("/usr/bin/printf 'foo\nbar\n' && exit 1", key="foobar5")
        task.shell("/usr/bin/printf 'foo\nbur\n' && exit 1", key="foobar2")
        task.shell("/usr/bin/printf 'foo\nbar\n' && exit 1", key="foobar3")
        task.shell("/usr/bin/printf 'foo\nfuu\n' && exit 5", key="foofuu")
        task.shell("/usr/bin/printf 'foo\nbar\n' && exit 4", key="faaber")
        task.shell("/usr/bin/printf 'foo\nfuu\n' && exit 1", key="foofuu2")

        task.resume()

        cnt = 9
        for buf, keys in task.iter_buffers():
            for rc, keys in task.iter_retcodes(keys):
                # same checks as testLocalRCBufferGathering
                cnt -= 1
                if buf == "foo\nbar\n":
                    self.assert_(rc == 1 and rc == 4)
                elif buf == "foo\nbur\n":
                    self.assertEqual(rc, 1)
                elif buf == "foo\nbuu\n":
                    self.assertEqual(rc, 5)

        self.assertEqual(cnt, 0)

    def testLocalWorkerWrites(self):
        # Simple test: we write to a cat process and see if read matches.
        task = task_self()
        self.assert_(task != None)
        worker = task.shell("cat")
        # write first line
        worker.write("foobar\n")
        # write second line
        worker.write("deadbeaf\n")
        worker.set_write_eof()
        task.resume()

        self.assertEqual(worker.read(), "foobar\ndeadbeaf")

    def testLocalWorkerWritesBcExample(self):
        # Other test: write a math statement to a bc process and check
        # for the result.
        task = task_self()
        self.assert_(task != None)
        worker = task.shell("bc -q")

        # write statement
        worker.write("2+2\n")
        worker.set_write_eof()

        # execute
        task.resume()

        # read result
        self.assertEqual(worker.read(), "4")

    def testEscape(self):
        task = task_self()
        self.assert_(task != None)
        worker = task.shell("export CSTEST=foobar; /bin/echo \$CSTEST | sed 's/\ foo/bar/'")
        # execute
        task.resume()
        # read result
        self.assertEqual(worker.read(), "$CSTEST")

    def testEscape2(self):
        task = task_self()
        self.assert_(task != None)
        worker = task.shell("export CSTEST=foobar; /bin/echo $CSTEST | sed 's/\ foo/bar/'")
        # execute
        task.resume()
        # read result
        self.assertEqual(worker.read(), "foobar")

    def testEngineClients(self):
        task = task_self()
        self.assert_(task != None)
        worker = task.shell("/bin/hostname")
        self.assert_(worker != None)
        self.assertEqual(len(task._engine.clients()), 1)
        task.resume()

    def testEnginePorts(self):
        task = task_self()
        self.assert_(task != None)
        worker = task.shell("/bin/hostname")
        self.assert_(worker != None)
        self.assertEqual(len(task._engine.ports()), 1)
        task.resume()

    def testSimpleCommandAutoclose(self):
        task = task_self()
        self.assert_(task != None)
        worker = task.shell("/bin/sleep 3; /bin/uname", autoclose=True)
        self.assert_(worker != None)
        task.resume()
        self.assertEqual(worker.read(), None)

    def testTwoSimpleCommandsAutoclose(self):
        task = task_self()
        self.assert_(task != None)
        worker1 = task.shell("/bin/sleep 2; /bin/echo ok")
        worker2 = task.shell("/bin/sleep 3; /bin/uname", autoclose=True)
        self.assert_(worker2 != None)
        task.resume()
        self.assertEqual(worker1.read(), "ok")
        self.assertEqual(worker2.read(), None)

    def test_unregister_stream_autoclose(self):
        task = task_self()
        self.assert_(task != None)
        worker1 = task.shell("/bin/sleep 2; /bin/echo ok")
        worker2 = task.shell("/bin/sleep 3; /bin/uname", autoclose=True)
        # the following leads to a call to unregister_stream() with autoclose flag set
        worker3 = task.shell("sleep 1; echo blah | cat", autoclose=True)
        task.resume()
        self.assertEqual(worker1.read(), "ok")
        self.assertEqual(worker2.read(), None)

    def testLocalWorkerErrorBuffers(self):
        task = task_self()
        self.assert_(task != None)
        w1 = task.shell("/usr/bin/printf 'foo bar\n' 1>&2", key="foobar", stderr=True)
        w2 = task.shell("/usr/bin/printf 'foo\nbar\n' 1>&2", key="foobar2", stderr=True)
        task.resume()
        self.assertEqual(w1.error(), 'foo bar')
        self.assertEqual(w2.error(), 'foo\nbar')

    def testLocalErrorBuffers(self):
        task = task_self()
        self.assert_(task != None)

        task.shell("/usr/bin/printf 'foo\nbar\n' 1>&2", key="foobar", stderr=True)
        task.shell("/usr/bin/printf 'foo\nbar\n' 1>&2", key="foobar2", stderr=True)
        task.shell("/usr/bin/printf 'foo\nbar\n 1>&2'", key="foobar3", stderr=True)
        task.shell("/usr/bin/printf 'foo\nbar\nxxx\n' 1>&2", key="foobarX", stderr=True)
        task.shell("/usr/bin/printf 'foo\nfuu\n' 1>&2", key="foofuu", stderr=True)
        task.shell("/usr/bin/printf 'faa\nber\n' 1>&2", key="faaber", stderr=True)
        task.shell("/usr/bin/printf 'foo\nfuu\n' 1>&2", key="foofuu2", stderr=True)

        task.resume()

        cnt = 4
        for buf, keys in task.iter_errors():
            cnt -= 1
            if buf == "faa\nber\n":
                self.assertEqual(len(keys), 1)
                self.assert_(keys[0].startswith("faaber"))
            elif buf == "foo\nfuu\n":
                self.assertEqual(len(keys), 2)
                self.assert_(keys[0].startswith("foofuu"))
            elif buf == "foo\nbar\n":
                self.assertEqual(len(keys), 3)
                self.assert_(keys[0].startswith("foobar"))
            elif buf == "foo\nbar\nxxx\n":
                self.assertEqual(len(keys), 1)
                self.assert_(keys[0].startswith("foobarX"))

        self.assertEqual(cnt, 0)

    def testTaskPrintDebug(self):
        task = task_self()
        self.assert_(task != None)
        # simple test, just run a task with debug on to improve test
        # code coverage
        task.set_info("debug", True)
        worker = task.shell("/bin/echo test")
        self.assert_(worker != None)
        task.resume()
        task.set_info("debug", False)

    def testTaskAbortSelf(self):
        task = task_self()
        self.assert_(task != None)

        # abort(False) keeps current task_self() object
        task.abort()
        self.assert_(task == task_self())

        # abort(True) unbinds current task_self() object
        task.abort(True)
        self.assert_(task != task_self())

        # retry
        task = task_self()
        self.assert_(task != None)
        worker = task.shell("/bin/echo shouldnt see that")
        task.abort()
        self.assert_(task == task_self())

    def testTaskAbortHandler(self):

        class AbortOnReadTestHandler(EventHandler):
            def ev_read(self, worker):
                self.has_ev_read = True
                worker.task.abort()
                assert False, "Shouldn't reach this line"

        task = task_self()
        self.assert_(task != None)
        eh = AbortOnReadTestHandler()
        eh.has_ev_read = False
        task.shell("/bin/echo test", handler=eh)
        task.resume()
        self.assert_(eh.has_ev_read)

    def testWorkerSetKey(self):
        task = task_self()
        self.assert_(task != None)
        task.shell("/bin/echo foo", key="foo")
        worker = task.shell("/bin/echo foobar")
        worker.set_key("bar")
        task.resume()
        self.assert_(task.key_buffer("bar") == "foobar")

    def testWorkerSimplePipe(self):
        task = task_self()
        self.assert_(task != None)
        r, w = os.pipe()
        os.write(w, "test\n")
        worker = WorkerSimple(r, None, None, "pipe", None, 0, True)
        self.assert_(worker != None)
        task.schedule(worker)
        task.resume()
        self.assertEqual(task.key_buffer("pipe"), 'test')
        self.assertRaises(OSError, os.close, r)
        os.close(w)


    # FIXME: reconsider this kind of test (which now must fail) especially
    #        when using epoll engine, as soon as testsuite is improved (#95).
    #def testWorkerSimpleFile(self):
    #    """test WorkerSimple (file)"""
    #    task = task_self()
    #    self.assert_(task != None)
    #    # use tempfile
    #    tmpfile = tempfile.TemporaryFile()
    #    tmpfile.write("one line without EOL")
    #    tmpfile.seek(0)
    #    worker = WorkerSimple(tmpfile, None, None, "file", None, 0, True)
    #    self.assert_(worker != None)
    #    task.schedule(worker)
    #    task.resume()
    #    self.assertEqual(worker.read(), "one line without EOL")

    def testInterruptEngine(self):
        class KillerThread(threading.Thread):
            def run(self):
                time.sleep(1)
                os.kill(self.pidkill, signal.SIGUSR1)
                task_wait()

        kth = KillerThread()
        kth.pidkill = os.getpid()

        task = task_self()
        self.assert_(task != None)
        signal.signal(signal.SIGUSR1, lambda x, y: None)
        task.shell("/bin/sleep 2", timeout=5)

        kth.start()
        task.resume()

    def testShellDelayedIO(self):
        class TestDelayedHandler(EventHandler):
            def __init__(self, target_worker=None):
                self.target_worker = target_worker
                self.counter = 0
            def ev_read(self, worker):
                self.counter += 1
                if self.counter == 100:
                    worker.write("another thing to read\n")
                    worker.set_write_eof()
            def ev_timer(self, timer):
                self.target_worker.write("something to read\n" * 300)

        task = task_self()
        hdlr = TestDelayedHandler()
        reader = task.shell("cat", handler=hdlr)
        timer = task.timer(0.6, handler=TestDelayedHandler(reader))
        task.resume()
        self.assertEqual(hdlr.counter, 301)

    def testSimpleCommandReadNoEOL(self):
        task = task_self()
        self.assert_(task != None)
        # init worker
        worker = task.shell("/bin/echo -n okay")
        self.assert_(worker != None)
        # run task
        task.resume()
        self.assertEqual(worker.read(), "okay")

    def testLocalFanout(self):
        task = task_self()
        self.assert_(task != None)
        fanout = task.info("fanout")
        try:
            task.set_info("fanout", 3)

            # Test #1: simple
            for i in range(0, 10):
                worker = task.shell("/bin/echo test %d" % i)
                self.assert_(worker != None)
            task.resume()

            # Test #2: fanout change during run
            class TestFanoutChanger(EventHandler):
                def ev_timer(self, timer):
                    task_self().set_info("fanout", 1)
            timer = task.timer(2.0, handler=TestFanoutChanger())
            for i in range(0, 10):
                worker = task.shell("/bin/echo sleep 1")
                self.assert_(worker != None)
            task.resume()
        finally:
            # restore original fanout value
            task.set_info("fanout", fanout)

    def testPopenBadArgumentOption(self):
	    # Check code < 1.4 compatibility
        self.assertRaises(WorkerBadArgumentError, WorkerPopen, None, None)
	    # As of 1.4, ValueError is raised for missing parameter
        self.assertRaises(ValueError, WorkerPopen, None, None) # 1.4+

    def testWorkerAbort(self):
        task = task_self()
        self.assert_(task != None)

        class AbortOnTimer(EventHandler):
            def __init__(self, worker):
                EventHandler.__init__(self)
                self.ext_worker = worker
                self.testtimer = False
            def ev_timer(self, timer):
                self.ext_worker.abort()
                self.testtimer = True

        aot = AbortOnTimer(task.shell("sleep 10"))
        self.assertEqual(aot.testtimer, False)
        task.timer(1.0, handler=aot)
        task.resume()
        self.assertEqual(aot.testtimer, True)

    def testWorkerAbortSanity(self):
        task = task_self()
        worker = task.shell("sleep 1")
        worker.abort()

        # test noop abort() on unscheduled worker
        worker = WorkerPopen("sleep 1")
        worker.abort()

    def testKBI(self):
        class TestKBI(EventHandler):
            def ev_read(self, worker):
                raise KeyboardInterrupt
        task = task_self()
        self.assert_(task != None)
        ok = False
        try:
            task.run("echo test; sleep 5", handler=TestKBI())
        except KeyboardInterrupt:
            ok = True
            # We want to test here if engine clients are not properly
            # cleaned, or results are not cleaned on re-run()
            #
            # cannot assert on task.iter_retcodes() as we are not sure in
            # what order the interpreter will proceed
            #self.assertEqual(len(list(task.iter_retcodes())), 1)
            self.assertEqual(len(list(task.iter_buffers())), 1)
            # hard to test without really checking the number of clients of engine
            self.assertEqual(len(task._engine._clients), 0)
            task.run("echo newrun")
            self.assertEqual(len(task._engine._clients), 0)
            self.assertEqual(len(list(task.iter_retcodes())), 1)
            self.assertEqual(len(list(task.iter_buffers())), 1)
            self.assertEqual(str(list(task.iter_buffers())[0][0]), "newrun")
        self.assertTrue(ok, "KeyboardInterrupt not raised")

    # From old TaskAdvancedTest.py:

    def testTaskRun(self):
        wrk = task_self().shell("true")
        task_self().run()

    def testTaskRunTimeout(self):
        wrk = task_self().shell("sleep 1")
        self.assertRaises(TimeoutError, task_self().run, 0.3)

        wrk = task_self().shell("sleep 1")
        self.assertRaises(TimeoutError, task_self().run, timeout=0.3)

    def testTaskShellRunLocal(self):
        wrk = task_self().run("false")
        self.assertTrue(wrk)
        self.assertEqual(task_self().max_retcode(), 1)

        # Timeout in shell() fashion way.
        wrk = task_self().run("sleep 1", timeout=0.3)
        self.assertTrue(wrk)
        self.assertEqual(task_self().num_timeout(), 1)

    def testTaskShellRunDistant(self):
        wrk = task_self().run("false", nodes="localhost")
        self.assertTrue(wrk)
        self.assertEqual(wrk.node_retcode("localhost"), 1)

    def testTaskEngineUserSelection(self):
        task_terminate()
        # Uh ho! It's a test case, not an example!
        Task._std_default['engine'] = 'select'
        self.assertEqual(task_self().info('engine'), 'select')
        task_terminate()

    def testTaskEngineWrongUserSelection(self):
        try:
            task_terminate()
            # Uh ho! It's a test case, not an example!
            Task._std_default['engine'] = 'foobar'
            # Check for KeyError in case of wrong engine request
            self.assertRaises(KeyError, task_self)
        finally:
            Task._std_default['engine'] = 'auto'

        task_terminate()

    def testTaskNewThread1(self):
        # create a task in a new thread
        task = Task()
        self.assert_(task != None)

        match = "test"

        # schedule a command in that task
        worker = task.shell("/bin/echo %s" % match)

        # run this task
        task.resume()

        # wait for the task to complete
        task_wait()

        # verify that the worker has completed
        self.assertEqual(worker.read(), match)

        # stop task
        task.abort()

    def testTaskInNewThread2(self):
        # create a task in a new thread
        task = Task()
        self.assert_(task != None)

        match = "again"

        # schedule a command in that task
        worker = task.shell("/bin/echo %s" % match)

        # run this task
        task.resume()

        # wait for the task to complete
        task_wait()

        # verify that the worker has completed
        self.assertEqual(worker.read(), match)

        # stop task
        task.abort()

    def testTaskInNewThread3(self):
        # create a task in a new thread
        task = Task()
        self.assert_(task != None)

        match = "once again"

        # schedule a command in that task
        worker = task.shell("/bin/echo %s" % match)

        # run this task
        task.resume()

        # wait for the task to complete
        task_wait()

        # verify that the worker has completed
        self.assertEqual(worker.read(), match)

        # stop task
        task.abort()


########NEW FILE########
__FILENAME__ = TaskLocalTest
#!/usr/bin/env python


"""Unit test for ClusterShell Task with all engines (local worker)"""

import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.Engine.Select import EngineSelect
from ClusterShell.Engine.Poll import EnginePoll
from ClusterShell.Engine.EPoll import EngineEPoll
from ClusterShell.Task import *

from TaskLocalMixin import TaskLocalMixin

ENGINE_SELECT_ID = EngineSelect.identifier
ENGINE_POLL_ID = EnginePoll.identifier
ENGINE_EPOLL_ID = EngineEPoll.identifier

class TaskLocalEngineSelectTest(TaskLocalMixin, unittest.TestCase):

    def setUp(self):
        task_terminate()
        self.engine_id_save = Task._std_default['engine']
        Task._std_default['engine'] = ENGINE_SELECT_ID
        # select should be supported anywhere...
        self.assertEqual(task_self().info('engine'), ENGINE_SELECT_ID)

    def tearDown(self):
        Task._std_default['engine'] = self.engine_id_save
        task_terminate()

class TaskLocalEnginePollTest(TaskLocalMixin, unittest.TestCase):

    def setUp(self):
        task_terminate()
        self.engine_id_save = Task._std_default['engine']
        Task._std_default['engine'] = ENGINE_POLL_ID
        if task_self().info('engine') != ENGINE_POLL_ID:
            self.skipTest("engine %s not supported on this host" % ENGINE_POLL_ID)

    def tearDown(self):
        Task._std_default['engine'] = self.engine_id_save
        task_terminate()

# select.epoll is only available with Python 2.6 (if condition to be
# removed once we only support Py2.6+)
if sys.version_info >= (2, 6, 0):

    class TaskLocalEngineEPollTest(TaskLocalMixin, unittest.TestCase):

        def setUp(self):
            task_terminate()
            self.engine_id_save = Task._std_default['engine']
            Task._std_default['engine'] = ENGINE_EPOLL_ID
            if task_self().info('engine') != ENGINE_EPOLL_ID:
                self.skipTest("engine %s not supported on this host" % ENGINE_EPOLL_ID)

        def tearDown(self):
            Task._std_default['engine'] = self.engine_id_save
            task_terminate()


########NEW FILE########
__FILENAME__ = TaskMsgTreeTest
#!/usr/bin/env python
# ClusterShell test suite
# Written by S. Thiell 2010-02-18


"""Unit test for ClusterShell TaskMsgTree variants"""

import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.Task import Task, TaskMsgTreeError
from ClusterShell.Task import task_cleanup, task_self


class TaskMsgTreeTest(unittest.TestCase):
    
    def tearDown(self):
        # cleanup task_self between tests to restore defaults
        task_cleanup()

    def testEnabledMsgTree(self):
        """test TaskMsgTree enabled"""
        task = task_self()
        self.assert_(task != None)
        # init worker
        worker = task.shell("echo foo bar")
        self.assert_(worker != None)
        task.set_default('stdout_msgtree', True)
        # run task
        task.resume()
        # should not raise
        for buf, keys in task.iter_buffers():
            pass

    def testDisabledMsgTree(self):
        """test TaskMsgTree disabled"""
        task = task_self()
        self.assert_(task != None)
        # init worker
        worker = task.shell("echo foo bar2")
        self.assert_(worker != None)
        task.set_default('stdout_msgtree', False)
        # run task
        task.resume()
        self.assertRaises(TaskMsgTreeError, task.iter_buffers)

    def testEnabledMsgTreeStdErr(self):
        """test TaskMsgTree enabled for stderr"""
        task = task_self()
        self.assert_(task != None)
        # init worker
        worker = task.shell("echo foo bar 1>&2", stderr=True)
        worker = task.shell("echo just foo bar", stderr=True)
        self.assert_(worker != None)
        task.set_default('stderr_msgtree', True)
        # run task
        task.resume()
        # should not raise:
        for buf, keys in task.iter_errors():
            pass
        # this neither:
        for buf, keys in task.iter_buffers():
            pass

    def testDisabledMsgTreeStdErr(self):
        """test TaskMsgTree disabled for stderr"""
        task = task_self()
        self.assert_(task != None)
        # init worker
        worker = task.shell("echo foo bar2 1>&2", stderr=True)
        worker = task.shell("echo just foo bar2", stderr=True)
        self.assert_(worker != None)
        task.set_default('stderr_msgtree', False)
        # run task
        task.resume()
        # should not raise:
        for buf, keys in task.iter_buffers():
            pass
        # but this should:
        self.assertRaises(TaskMsgTreeError, task.iter_errors)

    def testTaskFlushBuffers(self):
        """test Task.flush_buffers"""
        task = task_self()
        self.assert_(task != None)
        # init worker
        worker = task.shell("echo foo bar")
        self.assert_(worker != None)
        task.set_default('stdout_msgtree', True)
        # run task
        task.resume()
        task.flush_buffers()
        self.assertEqual(len(list(task.iter_buffers())), 0)

    def testTaskFlushErrors(self):
        """test Task.flush_errors"""
        task = task_self()
        self.assert_(task != None)
        # init worker
        worker = task.shell("echo foo bar 1>&2")
        self.assert_(worker != None)
        task.set_default('stderr_msgtree', True)
        # run task
        task.resume()
        task.flush_errors()
        self.assertEqual(len(list(task.iter_errors())), 0)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TaskMsgTreeTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = TaskPortTest
#!/usr/bin/env python
# ClusterShell test suite
# Written by S. Thiell 2009-12-19


"""Unit test for ClusterShell inter-Task msg"""

import pickle
import sys
import threading
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.Task import *
from ClusterShell.Event import EventHandler


class TaskPortTest(unittest.TestCase):

    def tearDown(self):
        task_cleanup()

    def testPortMsg1(self):
        """test port msg from main thread to task"""
        
        TaskPortTest.got_msg = False

        # create task in new thread
        task = Task()

        class PortHandler(EventHandler):
            def ev_msg(self, port, msg):
                # receive msg
                assert msg == "toto"
                assert port.task.thread == threading.currentThread()
                TaskPortTest.got_msg = True
                port.task.abort()

        # create non-autoclosing port
        port = task.port(handler=PortHandler())
        task.resume()
        # send msg from main thread
        port.msg("toto")
        task_wait()
        self.assert_(TaskPortTest.got_msg)

    def testPortRemove(self):
        """test port remove [private as of 1.2]"""
        
        task = Task()

        class PortHandler(EventHandler):
            def ev_msg(self, port, msg):
                pass

        port = task.port(handler=PortHandler(), autoclose=True)
        task.resume()
        task._remove_port(port)
        task_wait()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TaskPortTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = TaskRLimitsTest
#!/usr/bin/env python
# ClusterShell task resource consumption/limits test suite
# Written by S. Thiell 2010-10-19


"""Unit test for ClusterShell Task (resource limits)"""

import resource
import subprocess
import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.Task import *
from ClusterShell.Worker.Pdsh import WorkerPdsh


class TaskRLimitsTest(unittest.TestCase):

    def setUp(self):
        """set soft nofile resource limit to 100"""
        self.soft, self.hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (100, self.hard))

    def tearDown(self):
        """restore original resource limits"""
        resource.setrlimit(resource.RLIMIT_NOFILE, (self.soft, self.hard))

    def _testPopen(self, stderr):
        task = task_self()
        self.assert_(task != None)
        task.set_info("fanout", 10)
        for i in xrange(2000):
            worker = task.shell("/bin/hostname", stderr=stderr)
            self.assert_(worker != None)
        # run task
        task.resume()

    def testPopen(self):
        """test resource usage with local task.shell(stderr=False)"""
        self._testPopen(False)

    def testPopenStderr(self):
        """test resource usage with local task.shell(stderr=True)"""
        self._testPopen(True)

    def _testRemote(self, stderr):
        task = task_self()
        self.assert_(task != None)
        task.set_info("fanout", 10)
        for i in xrange(400):
            worker = task.shell("/bin/hostname", nodes="localhost",
                                stderr=stderr)
            self.assert_(worker != None)
        # run task
        task.resume()

    def testRemote(self):
        """test resource usage with remote task.shell(stderr=False)"""
        self._testRemote(False)

    def testRemoteStderr(self):
        """test resource usage with remote task.shell(stderr=True)"""
        self._testRemote(True)

    def _testRemotePdsh(self, stderr):
        task = task_self()
        self.assert_(task != None)
        task.set_info("fanout", 10)
        for i in xrange(200):
            worker = WorkerPdsh("localhost", handler=None,
                                timeout=0,
                                command="/bin/hostname",
                                stderr=stderr)
            self.assert_(worker != None)
            task.schedule(worker)
        # run task
        task.resume()

    def testRemotePdsh(self):
        """test resource usage with WorkerPdsh(stderr=False)"""
        self._testRemotePdsh(False)

    def testRemotePdshStderr(self):
        """test resource usage with WorkerPdsh(stderr=True)"""
        self._testRemotePdsh(True)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TaskRLimitsTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = TaskThreadJoinTest
#!/usr/bin/env python
# ClusterShell test suite
# Written by S. Thiell 2010-01-16


"""Unit test for ClusterShell task's join feature in multithreaded
environments"""

import sys
import time
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.Task import *
from ClusterShell.Event import EventHandler


class TaskThreadJoinTest(unittest.TestCase):

    def tearDown(self):
        task_cleanup()

    def testThreadTaskWaitWhenRunning(self):
        """test task_wait() when workers are running"""

        for i in range(1, 5):
            task = Task()
            task.shell("sleep %d" % i)
            task.resume()

        task_wait()


    def testThreadTaskWaitWhenSomeFinished(self):
        """test task_wait() when some workers finished"""

        for i in range(1, 5):
            task = Task()
            task.shell("sleep %d" % i)
            task.resume()

        time.sleep(2)
        task_wait()


    def testThreadTaskWaitWhenAllFinished(self):
        """test task_wait() when all workers finished"""

        for i in range(1, 3):
            task = Task()
            task.shell("sleep %d" % i)
            task.resume()

        time.sleep(4)
        task_wait()

    def testThreadSimpleTaskSupervisor(self):
        """test task methods from another thread"""
        #print "PASS 1"
        task = Task()
        task.shell("sleep 3")
        task.shell("echo testing", key=1)
        task.resume()
        task.join()
        self.assertEqual(task.key_buffer(1), "testing")
        #print "PASS 2"
        task.shell("echo ok", key=2)
        task.resume()
        task.join()
        #print "PASS 3"
        self.assertEqual(task.key_buffer(2), "ok")
        task.shell("sleep 1 && echo done", key=3)
        task.resume()
        task.join()
        #print "PASS 4"
        self.assertEqual(task.key_buffer(3), "done")
        task.abort()

    def testThreadTaskBuffers(self):
        """test task data access methods after join()"""
        task = Task()
        # test data access from main thread

        # test stderr separated
        task.set_default("stderr", True)
        task.shell("echo foobar", key="OUT")
        task.shell("echo raboof 1>&2", key="ERR")
        task.resume()
        task.join()
        self.assertEqual(task.key_buffer("OUT"), "foobar")
        self.assertEqual(task.key_error("OUT"), "")
        self.assertEqual(task.key_buffer("ERR"), "")
        self.assertEqual(task.key_error("ERR"), "raboof")

        # test stderr merged
        task.set_default("stderr", False)
        task.shell("echo foobar", key="OUT")
        task.shell("echo raboof 1>&2", key="ERR")
        task.resume()
        task.join()
        self.assertEqual(task.key_buffer("OUT"), "foobar")
        self.assertEqual(task.key_error("OUT"), "")
        self.assertEqual(task.key_buffer("ERR"), "raboof")
        self.assertEqual(task.key_error("ERR"), "")

    def testThreadTaskUnhandledException(self):
        """test task unhandled exception in thread"""
        class TestUnhandledException(Exception):
            """test exception"""
        class RaiseOnRead(EventHandler):
            def ev_read(self, worker):
                raise TestUnhandledException("you should see this exception")

        task = Task()
        # test data access from main thread
        task.shell("echo raisefoobar", key=1, handler=RaiseOnRead())
        task.resume()
        task.join()
        self.assertEqual(task.key_buffer(1), "raisefoobar")
        time.sleep(1) # for pretty display, because unhandled exception
                      # traceback may be sent to stderr after the join()
        self.assertFalse(task.running())


########NEW FILE########
__FILENAME__ = TaskThreadSuspendTest
#!/usr/bin/env python
# ClusterShell test suite
# Written by S. Thiell 2010-01-16


"""Unit test for ClusterShell in multithreaded environments"""

import random
import sys
import time
import thread
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.Task import *
from ClusterShell.Event import EventHandler


class TaskThreadSuspendTest(unittest.TestCase):

    def tearDown(self):
        task_cleanup()

    def testSuspendMiscTwoTasks(self):
        """test task suspend/resume (2 tasks)"""
        task = task_self()
        task2 = Task()

        task2.shell("sleep 4 && echo thr1")
        task2.resume()
        w = task.shell("sleep 1 && echo thr0", key=0)
        task.resume()
        self.assertEqual(task.key_buffer(0), "thr0")
        self.assertEqual(w.read(), "thr0")

        assert task2 != task
        task2.suspend()
        time.sleep(10)
        task2.resume()

        task_wait()

        task2.shell("echo suspend_test", key=1)
        task2.resume()

        task_wait()
        self.assertEqual(task2.key_buffer(1), "suspend_test")

    def _thread_delayed_unsuspend_func(self, task):
        """thread used to unsuspend task during task_wait()"""
        time_th = int(random.random()*6+5)
        #print "TIME unsuspend thread=%d" % time_th
        time.sleep(time_th)
        self.resumed = True
        task.resume()

    def testThreadTaskWaitWithSuspend(self):
        """test task_wait() with suspended tasks"""
        task = Task()
        self.resumed = False
        thread.start_new_thread(TaskThreadSuspendTest._thread_delayed_unsuspend_func, (self, task))
        time_sh = int(random.random()*4)
        #print "TIME shell=%d" % time_sh
        task.shell("sleep %d" % time_sh)
        task.resume()
        time.sleep(1)
        suspended = task.suspend()

        for i in range(1, 4):
            task = Task()
            task.shell("sleep %d" % i)
            task.resume()

        time.sleep(1)
        task_wait()
        self.assert_(self.resumed or suspended == False)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TaskThreadSuspendTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = TaskTimeoutTest
#!/usr/bin/env python
# ClusterShell (local) test suite
# Written by S. Thiell 2009-02-09


"""Unit test for ClusterShell Task/Worker timeout support"""

import copy
import sys
import unittest

sys.path.insert(0, '../lib')

import ClusterShell

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import *

import socket

import thread


class TaskTimeoutTest(unittest.TestCase):
            
    def testWorkersTimeoutBuffers(self):
        """test worker buffers with timeout"""
        task = task_self()
        self.assert_(task != None)

        worker = task.shell("python test_command.py --timeout=10", timeout=4)
        self.assert_(worker != None)

        task.resume()
        self.assertEqual(worker.read(), """some buffer
here...""")
        test = 1
        for buf, keys in task.iter_buffers():
            test = 0
            self.assertEqual(buf, """some buffer
here...""")
        self.assertEqual(test, 0, "task.iter_buffers() did not work")

    
    

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TaskTimeoutTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = TaskTimerTest
#!/usr/bin/env python
# ClusterShell timer test suite
# Written by S. Thiell 2009-02-15


"""Unit test for ClusterShell Task's timer"""

import copy
import thread
from time import sleep, time
import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.Engine.Engine import EngineTimer, EngineIllegalOperationError
from ClusterShell.Event import EventHandler
from ClusterShell.Task import *


EV_START=0x01
EV_READ=0x02
EV_WRITTEN=0x04
EV_HUP=0x08
EV_TIMEOUT=0x10
EV_CLOSE=0x20
EV_TIMER=0x40


class TaskTimerTest(unittest.TestCase):

    class TSimpleTimerChecker(EventHandler):
        def __init__(self):
            self.count = 0

        def ev_timer(self, timer):
            self.count += 1

    def testSimpleTimer(self):
        """test simple timer"""
        task = task_self()
        self.assert_(task != None)

        # init event handler for timer's callback
        test_handler = self.__class__.TSimpleTimerChecker()
        timer1 = task.timer(0.5, handler=test_handler)
        self.assert_(timer1 != None)
        # run task
        task.resume()
        self.assertEqual(test_handler.count, 1)

    def testSimpleTimer2(self):
        """test simple 2 timers with same fire_date"""
        task = task_self()
        self.assert_(task != None)
        test_handler = self.__class__.TSimpleTimerChecker()
        timer1 = task.timer(0.5, handler=test_handler)
        self.assert_(timer1 != None)
        timer2 = task.timer(0.5, handler=test_handler)
        self.assert_(timer2 != None)
        task.resume()
        self.assertEqual(test_handler.count, 2)

    def testSimpleTimerImmediate(self):
        """test simple immediate timer"""
        task = task_self()
        self.assert_(task != None)
        test_handler = self.__class__.TSimpleTimerChecker()
        timer1 = task.timer(0.0, handler=test_handler)
        self.assert_(timer1 != None)
        task.resume()
        self.assertEqual(test_handler.count, 1)

    def testSimpleTimerImmediate2(self):
        """test simple immediate timers"""
        task = task_self()
        self.assert_(task != None)
        test_handler = self.__class__.TSimpleTimerChecker()
        for i in range(10):
            timer1 = task.timer(0.0, handler=test_handler)
            self.assert_(timer1 != None)
        task.resume()
        self.assertEqual(test_handler.count, 10)

    class TRepeaterTimerChecker(EventHandler):
        def __init__(self):
            self.count = 0
            
        def ev_timer(self, timer):
            self.count += 1
            timer.set_nextfire(0.2)
            if self.count > 4:
                timer.invalidate()

    def testSimpleRepeater(self):
        """test simple repeater timer"""
        task = task_self()
        self.assert_(task != None)
        # init event handler for timer's callback
        test_handler = self.__class__.TRepeaterTimerChecker()
        timer1 = task.timer(0.5, interval=0.2, handler=test_handler)
        self.assert_(timer1 != None)
        # run task
        task.resume()
        self.assertEqual(test_handler.count, 5)

    def testRepeaterInvalidatedTwice(self):
        """test repeater timer invalidated two times"""
        task = task_self()
        self.assert_(task != None)
        # init event handler for timer's callback
        test_handler = self.__class__.TRepeaterTimerChecker()
        timer1 = task.timer(0.5, interval=0.2, handler=test_handler)
        self.assert_(timer1 != None)
        # run task
        task.resume()
        self.assertEqual(test_handler.count, 5)

        # force invalidation again (2d time), this should do nothing
        timer1.invalidate()

        # call handler one more time directly: set_nextfire should raise an error
        self.assertRaises(EngineIllegalOperationError, test_handler.ev_timer, timer1)

        # force invalidation again (3th), this should do nothing
        timer1.invalidate()

    def launchSimplePrecisionTest(self, delay):
        task = task_self()
        self.assert_(task != None)
        # init event handler for timer's callback
        test_handler = self.__class__.TSimpleTimerChecker()
        timer1 = task.timer(delay, handler=test_handler)
        self.assert_(timer1 != None)
        t1 = time()
        # run task
        task.resume()
        t2 = time()
        check_precision = 0.05
        self.assert_(abs((t2 - t1) - delay) < check_precision, \
                "%f >= %f" % (abs((t2 - t1) - delay), check_precision))
        self.assertEqual(test_handler.count, 1)

    def testPrecision1(self):
        """test simple timer precision (0.1s)"""
        self.launchSimplePrecisionTest(0.1)

    def testPrecision2(self):
        """test simple timer precision (1.0s)"""
        self.launchSimplePrecisionTest(1.0)

    def testWorkersAndTimer(self):
        """test task with timer and local jobs"""
        task0 = task_self()
        self.assert_(task0 != None)
        worker1 = task0.shell("/bin/hostname")
        worker2 = task0.shell("/bin/uname -a")
        test_handler = self.__class__.TSimpleTimerChecker()
        timer1 = task0.timer(1.0, handler=test_handler)
        self.assert_(timer1 != None)
        task0.resume()
        self.assertEqual(test_handler.count, 1)
        b1 = copy.copy(worker1.read())
        b2 = copy.copy(worker2.read())
        worker1 = task0.shell("/bin/hostname")
        self.assert_(worker1 != None)
        worker2 = task0.shell("/bin/uname -a")
        self.assert_(worker2 != None)
        timer1 = task0.timer(1.0, handler=test_handler)
        self.assert_(timer1 != None)
        task0.resume()
        self.assertEqual(test_handler.count, 2) # same handler, called 2 times
        self.assert_(worker2.read() == b2)
        self.assert_(worker1.read() == b1)

    def testNTimers(self):
        """test multiple timers"""
        task = task_self()
        self.assert_(task != None)
        # init event handler for timer's callback
        test_handler = self.__class__.TSimpleTimerChecker()
        for i in range(0, 30):
            timer1 = task.timer(1.0 + 0.2 * i, handler=test_handler)
            self.assert_(timer1 != None)
        # run task
        task.resume()
        self.assertEqual(test_handler.count, 30)

    class TEventHandlerTimerInvalidate(EventHandler):
        """timer operations event handler simulator"""
        def __init__(self, test):
            self.test = test
            self.timer = None
            self.timer_count = 0
            self.flags = 0
        def ev_start(self, worker):
            self.flags |= EV_START
        def ev_read(self, worker):
            self.test.assertEqual(self.flags, EV_START)
            self.flags |= EV_READ
        def ev_written(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_WRITTEN
        def ev_hup(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_HUP
        def ev_timeout(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_TIMEOUT
        def ev_close(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_CLOSE
        def ev_timer(self, timer):
            self.flags |= EV_TIMER
            self.timer_count += 1
            self.timer.invalidate()

    def testTimerInvalidateInHandler(self):
        """test timer invalidate in event handler"""
        task = task_self()
        self.assert_(task != None)
        test_eh = self.__class__.TEventHandlerTimerInvalidate(self)
        # init worker
        worker = task.shell("/bin/sleep 1", handler=test_eh)
        self.assert_(worker != None)
        worker = task.shell("/bin/sleep 3", nodes='localhost', handler=test_eh)
        self.assert_(worker != None)
        # init timer
        timer = task.timer(1.5, interval=0.5, handler=test_eh)
        self.assert_(timer != None)
        test_eh.timer = timer
        # run task
        task.resume()
        # test timer did fire once
        self.assertEqual(test_eh.timer_count, 1)

    class TEventHandlerTimerSetNextFire(EventHandler):
        def __init__(self, test):
            self.test = test
            self.timer = None
            self.timer_count = 0
            self.flags = 0
        def ev_start(self, worker):
            self.flags |= EV_START
        def ev_read(self, worker):
            self.test.assertEqual(self.flags, EV_START)
            self.flags |= EV_READ
        def ev_written(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_WRITTEN
        def ev_hup(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_HUP
        def ev_timeout(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_TIMEOUT
        def ev_close(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_CLOSE
        def ev_timer(self, timer):
            self.flags |= EV_TIMER
            if self.timer_count < 4:
                self.timer.set_nextfire(0.5)
            # else invalidate automatically as timer does not repeat
            self.timer_count += 1

    def testTimerSetNextFireInHandler(self):
        """test timer set_nextfire in event handler"""
        task = task_self()
        self.assert_(task != None)
        test_eh = self.__class__.TEventHandlerTimerSetNextFire(self)
        # init worker
        worker = task.shell("/bin/sleep 3", nodes='localhost', handler=test_eh)
        self.assert_(worker != None)
        # init timer
        timer = task.timer(1.0, interval=0.2, handler=test_eh)
        self.assert_(timer != None)
        test_eh.timer = timer
        # run task
        task.resume()
        # test timer did fire one time
        self.assertEqual(test_eh.timer_count, 5)
    
    class TEventHandlerTimerOtherInvalidate(EventHandler):
        """timer operations event handler simulator"""
        def __init__(self, test):
            self.test = test
            self.timer = None
            self.flags = 0
        def ev_start(self, worker):
            self.flags |= EV_START
        def ev_read(self, worker):
            self.flags |= EV_READ
            self.timer.invalidate()
        def ev_written(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_WRITTEN
        def ev_hup(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_HUP
        def ev_timeout(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_TIMEOUT
        def ev_close(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_CLOSE
        def ev_timer(self, timer):
            self.flags |= EV_TIMER

    def testTimerInvalidateInOtherHandler(self):
        """test timer invalidate in other event handler"""
        task = task_self()
        self.assert_(task != None)
        test_eh = self.__class__.TEventHandlerTimerOtherInvalidate(self)
        # init worker
        worker = task.shell("/bin/uname -r", handler=test_eh)
        self.assert_(worker != None)
        worker = task.shell("/bin/sleep 2", nodes='localhost', handler=test_eh)
        self.assert_(worker != None)
        # init timer
        timer = task.timer(1.0, interval=0.5, handler=test_eh)
        self.assert_(timer != None)
        test_eh.timer = timer
        # run task
        task.resume()
        # test timer didn't fire, invalidated in a worker's event handler
        self.assert_(test_eh.flags & EV_READ)
        self.assert_(not test_eh.flags & EV_TIMER)

    class TEventHandlerTimerOtherSetNextFire(EventHandler):
        def __init__(self, test):
            self.test = test
            self.timer = None
            self.timer_count = 0
            self.flags = 0
        def ev_start(self, worker):
            self.flags |= EV_START
        def ev_read(self, worker):
            self.test.assertEqual(self.flags, EV_START)
            self.flags |= EV_READ
        def ev_written(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_WRITTEN
        def ev_hup(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_HUP
        def ev_timeout(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_TIMEOUT
        def ev_close(self, worker):
            self.test.assert_(self.flags & EV_START)
            self.flags |= EV_CLOSE
            # set next fire delay, also disable previously setup interval
            # (timer will not repeat anymore)
            self.timer.set_nextfire(0.5)
        def ev_timer(self, timer):
            self.flags |= EV_TIMER
            self.timer_count += 1

    def testTimerSetNextFireInOtherHandler(self):
        """test timer set_nextfire in other event handler"""
        task = task_self()
        self.assert_(task != None)
        test_eh = self.__class__.TEventHandlerTimerOtherSetNextFire(self)
        # init worker
        worker = task.shell("/bin/sleep 1", nodes='localhost', handler=test_eh)
        self.assert_(worker != None)
        # init timer
        timer = task.timer(10.0, interval=0.5, handler=test_eh)
        self.assert_(timer != None)
        test_eh.timer = timer
        # run task
        task.resume()
        # test timer did fire one time
        self.assertEqual(test_eh.timer_count, 1)

    def testAutocloseTimer(self):
        """test timer autoclose (one autoclose timer)"""
        task = task_self()
        self.assert_(task != None)

        # Task should return immediately
        test_handler = self.__class__.TSimpleTimerChecker()
        timer_ac = task.timer(10.0, handler=test_handler, autoclose=True)
        self.assert_(timer_ac != None)

        # run task
        task.resume()
        self.assertEqual(test_handler.count, 0)
    
    def testAutocloseWithTwoTimers(self):
        """test timer autoclose (two timers)"""
        task = task_self()
        self.assert_(task != None)

        # build 2 timers, one of 10 secs with autoclose,
        # and one of 1 sec without autoclose.
        # Task should return after 1 sec.
        test_handler = self.__class__.TSimpleTimerChecker()
        timer_ac = task.timer(10.0, handler=test_handler, autoclose=True)
        self.assert_(timer_ac != None)
        timer_noac = task.timer(1.0, handler=test_handler, autoclose=False)
        self.assert_(timer_noac != None)

        # run task
        task.resume()
        self.assertEqual(test_handler.count, 1)
    
    class TForceDelayedRepeaterChecker(EventHandler):
        def __init__(self):
            self.count = 0

        def ev_timer(self, timer):
            self.count += 1
            if self.count == 1:
                # force delay timer (NOT a best practice!)
                sleep(4)
                # do not invalidate first time
            else:
                # invalidate next time to stop repeater
                timer.invalidate()

    def testForceDelayedRepeater(self):
        """test repeater being forcibly delayed"""
        task = task_self()
        self.assert_(task != None)
        test_handler = self.__class__.TForceDelayedRepeaterChecker()
        repeater1 = task.timer(1.0, interval=0.5, handler=test_handler)
        self.assert_(repeater1 != None)
        task.resume()
        self.assertEqual(test_handler.count, 2)

    def testMultipleAddSameTimerPrivate(self):
        """test multiple add() of same timer [private]"""
        task = task_self()
        self.assert_(task != None)
        test_handler = self.__class__.TSimpleTimerChecker()
        timer = EngineTimer(1.0, -1.0, False, test_handler)
        self.assert_(timer != None)
        task._engine.add_timer(timer)
        self.assertRaises(EngineIllegalOperationError, task._engine.add_timer, timer)
        task_terminate()

    def testRemoveTimerPrivate(self):
        """test engine.remove_timer() [private]"""
        # [private] because engine methods are currently private,
        # users should use timer.invalidate() instead
        task = task_self()
        self.assert_(task != None)
        test_handler = self.__class__.TSimpleTimerChecker()
        timer = EngineTimer(1.0, -1.0, False, test_handler)
        self.assert_(timer != None)
        task._engine.add_timer(timer)
        task._engine.remove_timer(timer)
        task_terminate()

    def _thread_timer_create_func(self, task):
        """thread used to create a timer for another task; hey why not?"""
        timer = task.timer(0.5, self.__class__.TSimpleTimerChecker())
        self.assert_(timer != None)

    def testTimerAddFromAnotherThread(self):
        """test timer creation from another thread"""
        task = task_self()
        thread.start_new_thread(TaskTimerTest._thread_timer_create_func, (self, task))
        task.resume()
        task_wait()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TaskTimerTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = test_command
#!/usr/bin/env python
# ClusterShell test command

"""
test_command.py [--help] [--test=test] [--rc=retcode] [--timeout=timeout]
"""

import getopt
import sys
import time
import unittest


def testHuge():
    for i in range(0, 100000):
        print "huge! ",

def testCmpOut():
    print "abcdefghijklmnopqrstuvwxyz"

def testTimeout(howlong):
    print "some buffer"
    print "here..."
    sys.stdout.flush()
    time.sleep(howlong)

if __name__ == '__main__':
    rc = 0
    test = None
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ht:r:m:", ["help", "test=", "rc=", "timeout="])
    except getopt.error, msg:
        print msg
        print "Try `python %s -h' for more information." % sys.argv[0]
        sys.exit(2)

    for k, v in opts:
        if k in ("-t", "--test"):
            if v == "huge":
                test = testHuge
            elif v == "cmp_out":
                test = testCmpOut
        elif k in ("-r", "--rc"):
            rc = int(v)
        elif k in ("-m", "--timeout"):
            testTimeout(int(v))
        elif k in ("-h", "--help"):
            print __doc__
            sys.exit(0)

    if test:
        test()

    sys.exit(rc)

########NEW FILE########
__FILENAME__ = TLib

"""Unit test small library"""

import os
import socket
import sys
import tempfile
import time

from ConfigParser import ConfigParser
from StringIO import StringIO


def my_node():
    """Helper to get local short hostname."""
    return socket.gethostname().split('.')[0]

def load_cfg(name):
    """Load test configuration file as a new ConfigParser"""
    cfgparser = ConfigParser()
    cfgparser.read([ \
        os.path.expanduser('~/.clustershell/tests/%s' % name),
        '/etc/clustershell/tests/%s' % name])
    return cfgparser

def chrono(func):
    """chrono decorator"""
    def timing(*args):
        start = time.time()
        res = func(*args)
        print "execution time: %f s" % (time.time() - start)
        return res
    return timing

#
# Temp files and directories
#
def make_temp_filename(suffix=''):
    """Return a temporary name for a file."""
    if len(suffix) > 0 and suffix[0] != '-':
        suffix = '-' + suffix
    return (tempfile.mkstemp(suffix, prefix='cs-test-'))[1]

def make_temp_file(text, suffix='', dir=None):
    """Create a temporary file with the provided text."""
    tmp = tempfile.NamedTemporaryFile(prefix='cs-test-',
                                      suffix=suffix, dir=dir)
    tmp.write(text)
    tmp.flush()
    return tmp

def make_temp_dir(suffix=''):
    """Create a temporary directory."""
    if len(suffix) > 0 and suffix[0] != '-':
        suffix = '-' + suffix
    return tempfile.mkdtemp(suffix, prefix='cs-test-')

#
# CLI tests
#
def CLI_main(test, main, args, stdin, expected_stdout, expected_rc=0,
             expected_stderr=None):
    """Generic CLI main() direct calling function that allows code coverage
    checks."""
    rc = -1
    saved_stdin = sys.stdin
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    if stdin is not None:
        sys.stdin = StringIO(stdin)
    sys.stdout = out = StringIO()
    sys.stderr = err = StringIO()
    sys.argv = args
    try:
        try:
            main()
        except SystemExit, exc:
            rc = int(str(exc))
    finally:
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr
        sys.stdin = saved_stdin
    if expected_stdout is not None:
        test.assertEqual(out.getvalue(), expected_stdout)
    out.close()
    if expected_stderr is not None:
        # check the end as stderr messages are often prefixed with argv[0]
        test.assertTrue(err.getvalue().endswith(expected_stderr), err.getvalue())
    if expected_rc is not None:
        test.assertEqual(rc, expected_rc, "rc=%d err=%s" % (rc, err.getvalue()))
    err.close()


########NEW FILE########
__FILENAME__ = CommunicationTest
#!/usr/bin/env python
# ClusterShell communication test suite
# Written by H. Doreau


"""Unit test for Communication"""

import sys
import unittest
import tempfile
import xml

# profiling imports
#import cProfile
#from guppy import hpy
# ---

sys.path.insert(0, '../lib')

from ClusterShell.Task import task_self
from ClusterShell.Worker.Worker import WorkerSimple
from ClusterShell.Communication import XMLReader, Channel
from ClusterShell.Communication import MessageProcessingError
from ClusterShell.Communication import ConfigurationMessage, ControlMessage
from ClusterShell.Communication import ACKMessage, ErrorMessage
from ClusterShell.Communication import StdOutMessage, StdErrMessage



def gen_cfg():
    """return a generic configuration message instance"""
    msg = ConfigurationMessage()
    msg.msgid = 0
    msg.data = 'KGxwMApJMQphSTIKYUkzCmEu'
    return msg

def gen_ctl():
    """return a generic control message instance"""
    msg = ControlMessage()
    msg.msgid = 0
    msg.action = 'shell'
    msg.target = 'node[0-10]'
    params = {'cmd': 'uname -a'}
    msg.data_encode(params)
    return msg

def gen_ack():
    """return a generic acknowledgement message instance"""
    msg = ACKMessage()
    msg.msgid = 0
    msg.ack = 123
    return msg

def gen_err():
    """return a generic error message instance"""
    msg = ErrorMessage()
    msg.msgid = 0
    msg.reason = 'bad stuff'
    return msg

def gen_out():
    """return a generic output message instance"""
    msg = StdOutMessage()
    msg.msgid = 0
    msg.output = "node5"
    msg.output = "Linux galion25 2.6.18-92.el5 #1 SMP Tue Apr 29 " \
                 "03:13:37 EDT 2008 x86_64 x86_64 x86_64 GNU/Linux"
    return msg

# sample message generators
gen_map = {
    ConfigurationMessage.ident: gen_cfg,
    ControlMessage.ident: gen_ctl,
    ACKMessage.ident: gen_ack,
    ErrorMessage.ident: gen_err,
    StdOutMessage.ident: gen_out,
}

class _TestingChannel(Channel):
    """internal channel that handle read messages"""
    def __init__(self):
        """
        """
        Channel.__init__(self)
        self.queue = []
        self._counter = 1
        self._last_id = 0

    def recv(self, msg):
        """process an incoming messages"""
        self._last_id = msg.msgid
        self.queue.append(msg)
        msg = ACKMessage()
        msg.ack = self._last_id
        self.send(msg)
        self._counter += 1
        if self._counter == 4:
            self.exit = True
            self._close()

    def start(self):
        """
        """
        self._open()

    def validate(self, spec):
        """check whether the test was successful or not by comparing the
        current state with the test specifications
        """
        for msg_type in spec.iterkeys():
            elemt = [p for p in self.queue if p.type == msg_type]
            if len(elemt) != spec[msg_type]:
                print '%d %s messages but %d expected!' % (len(elemt), \
                    msg_type, spec[msg_type])
                return False
        return True

class CommunicationTest(unittest.TestCase):
    ## -------------
    # TODO : get rid of the following hardcoded messages
    # ---
    def testXMLConfigurationMessage(self):
        """test configuration message XML serialization"""
        res = gen_cfg().xml()
        ref = '<message msgid="0" type="CFG">KGxwMApJMQphSTIKYUkzCmEu</message>'
        self.assertEquals(res, ref)

    def testXMLControlMessage(self):
        """test control message XML serialization"""
        res = gen_ctl().xml()
        ref = '<message action="shell" msgid="0" srcid="0" target="node[0-10]" type="CTL">' \
            'KGRwMQpTJ2NtZCcKcDIKUyd1bmFtZSAtYScKcDMKcy4=</message>'
        self.assertEquals(res, ref)

    def testXMLACKMessage(self):
        """test acknowledgement message XML serialization"""
        res = gen_ack().xml()
        ref = '<message ack="123" msgid="0" type="ACK"></message>'
        self.assertEquals(res, ref)

    def testXMLErrorMessage(self):
        """test error message XML serialization"""
        res = gen_err().xml()
        ref = '<message msgid="0" reason="bad stuff" type="ERR"></message>'
        self.assertEquals(res, ref)

    def testXMLOutputMessage(self):
        """test output message XML serialization"""
        res = gen_out().xml()
        ref = '<message msgid="0" nodes="" output=' \
        '"Linux galion25 2.6.18-92.el5 #1 SMP Tue Apr 29 03:13:37 EDT 2008 x86_64 x86_64 x86_64 GNU/Linux"' \
        ' srcid="0" type="OUT"></message>'
        self.assertEquals(res, ref)

    def testInvalidMsgStreams(self):
        """test detecting invalid messages"""
        patterns = [
            '<message type="BLA" msgid="-1"></message>',
            '<message type="ACK"></message>',
            '<message type="ACK" msgid="0" ack="12"><foo></foo></message>',
            '<message type="ACK" msgid="0" ack="12">some stuff</message>',
            '<message type="ACK" msgid="123"></message>',
            '<message type="OUT" msgid="123" reason="foo"></message>',
            '<message type="OUT" msgid="123" output="foo" nodes="bar">shoomp</message>',
            '<message type="CFG" msgid="123"><foo></bar></message>',
            '<message type="CFG" msgid="123"><foo></message>',
            '<message type="CTL" msgid="123"><param></param></message>',
            '<message type="CTL" msgid="123"></message>',
            '<message type="CTL" msgid="123"><param><action target="node123" type="foobar"></action></param></message>',
            '<message type="CTL" msgid="123"><action type="foobar"></message>',
            '<message type="CTL" msgid="123"><action type="foobar" target="node1"><param cmd="yeepee"></param></action></message>',
            '<message type="CTL" msgid="123"><action type="foobar"><param cmd="echo fnords"></param></action></message>',
            '<message type="CTL" msgid="123"><action type="shell" target="node1"></action></message>',
            '<message type="CTL" msgid="123"><action type="" target="node1"><param cmd="echo fnords"></param></action></message>',
            '<param cmd=""></param></message>',
            '<message type="ERR" msgid="123"></message>',
            '<message type="ERR" msgid="123" reason="blah">unexpected payload</message>',
            '<message type="ERR" msgid="123" reason="blah"><foo bar="boo"></foo></message>',
        ]
        for msg_xml in patterns:
            parser = xml.sax.make_parser(['IncrementalParser'])
            parser.setContentHandler(XMLReader())

            parser.feed('<?xml version="1.0" encoding="UTF-8"?>\n')
            parser.feed('<channel>\n')

            try:
                parser.feed(msg_xml)
            except MessageProcessingError, m:
                # actually this is Ok, we want this exception to be raised
                pass
            else:
                self.fail('Invalid message goes undetected: %s' % msg_xml)

    def testConfigMsgEncoding(self):
        """test configuration message serialization abilities"""
        msg = gen_cfg()
        msg.data = ''
        inst = {'foo': 'plop', 'blah': 123, 'fnords': 456}
        msg.data_encode(inst)
        self.assertEquals(inst, msg.data_decode())

    def testChannelAbstractMethods(self):
        """test driver interface"""
        c = Channel()
        self.assertRaises(NotImplementedError, c.recv, None)
        self.assertRaises(NotImplementedError, c.start)

    def testDistantChannel(self):
        """schyzophrenic self communication test over SSH"""
        # create a bunch of messages
        spec = {
            # msg type: number of samples
            ConfigurationMessage.ident: 1,
            ControlMessage.ident: 1,
            ACKMessage.ident: 1,
            ErrorMessage.ident: 1
        }
        ftest = tempfile.NamedTemporaryFile()
        ftest.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        ftest.write('<channel>\n')
        for mtype, count in spec.iteritems():
            for i in xrange(count):
                sample = gen_map[mtype]()
                sample.msgid = i
                ftest.write(sample.xml() + '\n')
        ftest.write('</channel>\n')

        ## write data on the disk
        # actually we should do more but this seems sufficient
        ftest.flush()

        task = task_self()
        chan = _TestingChannel()
        task.shell('cat ' + ftest.name, nodes='localhost', handler=chan)
        task.resume()

        ftest.close()
        self.assertEquals(chan.validate(spec), True)

    def testLocalChannel(self):
        """schyzophrenic self local communication"""
        # create a bunch of messages
        spec = {
            # msg type: number of samples
            ConfigurationMessage.ident: 1,
            ControlMessage.ident: 1,
            ACKMessage.ident: 1,
            ErrorMessage.ident: 1
        }
        ftest = tempfile.NamedTemporaryFile()
        ftest.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        ftest.write('<channel>\n')
        for mtype, count in spec.iteritems():
            for i in xrange(count):
                sample = gen_map[mtype]()
                sample.msgid = i
                ftest.write(sample.xml() + '\n')
        ftest.write('</channel>\n')

        ## write data on the disk
        # actually we should do more but this seems sufficient
        ftest.flush()

        fin = open(ftest.name)
        fout = open('/dev/null', 'w')
        
        chan = _TestingChannel()
        worker = WorkerSimple(fin, fout, None, None, handler=chan)

        task = task_self()
        task.schedule(worker)
        task.resume()

        ftest.close()
        fin.close()
        fout.close()
        self.assertEquals(chan.validate(spec), True)

    def testInvalidCommunication(self):
        """test detecting invalid data upon reception"""
        ftest = tempfile.NamedTemporaryFile()
        ftest.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        ftest.write('This is an invalid line\n')
        ftest.write('<channel>\n')
        ftest.write('</channel>\n')

        ## write data on the disk
        # actually we should do more but this seems sufficient
        ftest.flush()

        chan = _TestingChannel()
        task = task_self()

        fin = open(ftest.name)
        fout = open('/dev/null', 'w')
        worker = WorkerSimple(fin, fout, None, None, handler=chan)
        task.schedule(worker)

        self.assertRaises(MessageProcessingError, task.resume)

        fin.close()
        fout.close()
        ftest.close()

    def testPrintableRepresentations(self):
        """test printing messages"""
        msg = gen_cfg()
        self.assertEquals(str(msg), 'Message CFG (msgid: 0, type: CFG)')

def main():
    suite = unittest.TestLoader().loadTestsFromTestCase(CommunicationTest)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    #cProfile.run('main()')
    main()


########NEW FILE########
__FILENAME__ = GatewayTest
#!/usr/bin/env python
# ClusterShell.Gateway test suite
# Written by H. Doreau and S. Thiell


"""Unit test for Gateway"""

import os
import sys
import unittest
import tempfile

import logging

sys.path.insert(0, '../lib')

from ClusterShell.Event import EventHandler
from ClusterShell.NodeSet import NodeSet
from ClusterShell.Propagation import PropagationTree
from ClusterShell.Topology import TopologyParser
from TLib import load_cfg, my_node


class DirectHandler(EventHandler):
    """
    Test Direct EventHandler
    """
    def ev_read(self, worker):
        """stdout event"""
        node, buf = worker.last_read()
        print "%s: %s" % (node, buf)

    def ev_error(self, worker):
        """stderr event"""
        node, buf = worker.last_error()
        print "(stderr) %s: %s" % (node, buf)

    def ev_close(self, worker):
        """close event"""
        print "ev_close %s" % worker


class GatewayTest(unittest.TestCase):
    """TestCase for ClusterShell.Gateway module."""
    
    def testCompletePropagation(self):
        """test a complete command propagation trip"""
        #
        # This test relies on configured parameters (topology2.conf)
        tmpfile = tempfile.NamedTemporaryFile()

        logging.basicConfig(
                level=logging.DEBUG
                )
        logging.debug("STARTING")

        hostname = my_node()
        cfgparser = load_cfg('topology2.conf')
        neighbors = cfgparser.get('CONFIG', 'NEIGHBORS')
        targets = cfgparser.get('CONFIG', 'TARGETS')

        tmpfile.write('[DEFAULT]\n')
        tmpfile.write('%s: %s\n' % (hostname, neighbors))
        tmpfile.write('%s: %s\n' % (neighbors, targets))
        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)
        tmpfile.close()

        nfs_tmpdir = os.path.expanduser('~/.clustershell/tests/tmp')

        tree = parser.tree(hostname)
        print tree

        ptree = PropagationTree(tree, hostname)
        ptree.upchannel = None
        ptree.edgehandler = DirectHandler()

        ptree.fanout = 20
        ptree.invoke_gateway = \
            'cd %s; PYTHONPATH=../lib python -m ClusterShell/Gateway -Bu' % \
                os.getcwd()
        #print ptree.invoke_gateway

        ## delete remaining files from previous tests
        for filename in os.listdir(nfs_tmpdir):
            if filename.startswith("fortoy"):
                os.remove(os.path.join(nfs_tmpdir, filename))

        dst = NodeSet(targets)
        task = ptree.execute('python -c "import time; print time.time()" > ' + \
                             os.path.join(nfs_tmpdir, '$(hostname)'), dst, 20)
        #task = ptree.execute('sleep 2; echo "output from $(hostname)"', \
        #                      dst, 20)
        self.assert_(task)

        res = NodeSet()
        times = []
        for filename in os.listdir(nfs_tmpdir):
            for k in dst:
                if filename.startswith(str(k)):
                    res.add(k)
                    fd = open(os.path.join(nfs_tmpdir, filename))
                    times.append(float(fd.read()))
                    fd.close()

        self.assertEquals(str(res), str(dst))
        print "Complete propagation time: %fs for %d nodes" % \
                (max(times) - min(times), len(dst))

def main():
    suite = unittest.TestLoader().loadTestsFromTestCase(GatewayTest)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = PropagationTest
#!/usr/bin/env python
# ClusterShell propagation test suite
# Written by H. Doreau


"""Unit test for Propagation"""

import os
import sys
import unittest
import tempfile

# profiling imports
#import cProfile
#from guppy import hpy
# ---

sys.path.insert(0, '../lib')

from ClusterShell.Propagation import *
from ClusterShell.NodeSet import NodeSet
from ClusterShell.Topology import TopologyParser
from ClusterShell.Worker.Tree import WorkerTree
from ClusterShell.Task import task_self

from TLib import load_cfg, my_node




class PropagationTest(unittest.TestCase):
    def setUp(self):
        """generate a sample topology tree"""
        tmpfile = tempfile.NamedTemporaryFile()

        tmpfile.write('[Main]\n')
        tmpfile.write('admin[0-2]: proxy\n')
        tmpfile.write('proxy: STA[0-400]\n')
        tmpfile.write('STA[0-400]: STB[0-2000]\n')
        tmpfile.write('STB[0-2000]: node[0-11000]\n')

        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)

        self.topology = parser.tree('admin1')

        # XXX
        os.environ["PYTHONPATH"] = "%s/../lib" % os.getcwd()

    def testRouting(self):
        """test basic routing mecanisms"""
        ptr = PropagationTreeRouter('admin1', self.topology)
        self.assertRaises(RouteResolvingError, ptr.next_hop, 'admin1')

        self.assertEquals(ptr.next_hop('STA0'), 'proxy')
        self.assertEquals(ptr.next_hop('STB2000'), 'proxy')
        self.assertEquals(ptr.next_hop('node10'), 'proxy')

        ptr = PropagationTreeRouter('proxy', self.topology)
        self.assert_(ptr.next_hop('STB0') in NodeSet('STA[0-4000]'))

        ptr = PropagationTreeRouter('STB7', self.topology)
        self.assertEquals(ptr.next_hop('node500'), 'node500')

        ptr = PropagationTreeRouter('STB7', self.topology)
        self.assertRaises(RouteResolvingError, ptr.next_hop, 'foo')
        self.assertRaises(RouteResolvingError, ptr.next_hop, 'admin1')

        self.assertRaises(RouteResolvingError, PropagationTreeRouter, 'bar', self.topology)

    def testHostRepudiation(self):
        """test marking hosts as unreachable"""
        ptr = PropagationTreeRouter('STA42', self.topology)

        res1 = ptr.next_hop('node42')
        self.assertEquals(res1 in NodeSet('STB[0-2000]'), True)

        ptr.mark_unreachable(res1)
        self.assertRaises(RouteResolvingError, ptr.next_hop, res1)

        res2 = ptr.next_hop('node42')
        self.assertEquals(res2 in NodeSet('STB[0-2000]'), True)
        self.assertNotEquals(res1, res2)

    def testRoutingTableGeneration(self):
        """test routing table generation"""
        ptr = PropagationTreeRouter('admin1', self.topology)
        res = [str(v) for v in ptr.table.values()]
        self.assertEquals(res, ['proxy'])

        ptr = PropagationTreeRouter('STA200', self.topology)
        res = [str(v) for v in ptr.table.values()]
        self.assertEquals(res, ['STB[0-2000]'])

    def testFullGateway(self):
        """test router's ability to share the tasks between gateways"""
        ptr = PropagationTreeRouter('admin1', self.topology)
        ptr.fanout = 32
        for node in NodeSet('STB[0-200]'):
            self.assertEquals(ptr.next_hop(node), 'proxy')

    def testPropagationDriver(self):
        """test propagation logic"""
        ## --------
        # This test use a tricky topology, whose next hop for any admin node is
        # localhost. This way, the test machine will connect to itself as if it
        # was a remote gateway.
        # Then, instead of talking to a gateway instance, it will load a
        # specifically crafted file, that contains XML messages as those sent by
        # an actual gateway.
        # -----------------------
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write('[Main]\n')
        tmpfile.write('admin[0-2]: localhost\n')
        tmpfile.write('localhost: node[0-500]\n')

        gwfile = tempfile.NamedTemporaryFile()
        gwfile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        gwfile.write('<channel>\n')
        gwfile.write('<message type="ACK" msgid="0" ack="0"></message>\n')
        gwfile.write('<message type="ACK" msgid="1" ack="1"></message>\n')
        gwfile.write('<message type="ACK" msgid="2" ack="2"></message>\n')
        gwfile.write('<message type="CTL" target="node[0-500]" msgid="3" ' \
            'action="res">' \
            'UydMaW51eCAyLjYuMTgtOTIuZWw1ICMxIFNNUCBUdWUgQXByIDI5IDEzOjE2OjE1IEVEVCAyMDA4' \
            'IHg4Nl82NCB4ODZfNjQgeDg2XzY0IEdOVS9MaW51eCcKcDEKLg==' \
            '</message>\n')
        gwfile.write('</channel>\n')

        tmpfile.flush()
        gwfile.flush()

        parser = TopologyParser()
        parser.load(tmpfile.name)

        """
        XXX need a way to override the way the gateway is remotely launch
        """
        raise RuntimeError

        """
        ptree = PropagationTree(tree, 'admin1')

        ptree.invoke_gateway = 'cat %s' % gwfile.name
        ptree.execute('uname -a', 'node[0-500]', 128, 1)
        """

    def testDistributeTasksSimple(self):
        """test dispatch work between several gateways (simple case)"""
        tmpfile = tempfile.NamedTemporaryFile()

        tmpfile.write('[Main]\n')
        tmpfile.write('admin[0-2]: gw[0-3]\n')
        tmpfile.write('gw[0-1]: node[0-9]\n')
        tmpfile.write('gw[2-3]: node[10-19]\n')

        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)

        tree = parser.tree('admin1')
        wtree = WorkerTree('dummy', None, 0, command=':', topology=tree,
                           newroot='admin1')
        dist = wtree._distribute(128, NodeSet('node[2-18]'))
        self.assertEquals(dist['gw0'], NodeSet('node[2-8/2]'))
        self.assertEquals(dist['gw2'], NodeSet('node[10-18/2]'))

    def testDistributeTasksComplex(self):
        """test dispatch work between several gateways (more complex case)"""
        tmpfile = tempfile.NamedTemporaryFile()

        tmpfile.write('[Main]\n')
        tmpfile.write('admin[0-2]: gw[0-1]\n')
        tmpfile.write('gw0: n[0-9]\n')
        tmpfile.write('gw1: gwa[0-1]\n')
        tmpfile.write('gwa0: n[10-19]\n')
        tmpfile.write('gwa1: n[20-29]\n')

        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)

        tree = parser.tree('admin1')
        wtree = WorkerTree('dummy', None, 0, command=':', topology=tree,
                           newroot='admin1')
        dist = wtree._distribute(5, NodeSet('n[0-29]'))
        self.assertEquals(str(dist['gw0']), 'n[0-9]')
        self.assertEquals(str(dist['gw1']), 'n[10-29]')

    def testExecuteTasksOnNeighbors(self):
        """test execute tasks on directly connected machines"""
        tmpfile = tempfile.NamedTemporaryFile()

        myhost = my_node()
        cfgparser = load_cfg('topology1.conf')
        neighbor = cfgparser.get('CONFIG', 'NEIGHBOR')
        gateways = cfgparser.get('CONFIG', 'GATEWAYS')
        targets = cfgparser.get('CONFIG', 'TARGETS')

        tmpfile.write('[Main]\n')
        tmpfile.write('%s: %s\n' % (myhost, neighbor))
        tmpfile.write('%s: %s\n' % (neighbor, gateways))
        tmpfile.write('%s: %s\n' % (gateways, targets))
        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)

        tree = parser.tree(myhost)
        wtree = WorkerTree(NodeSet(targets), None, 0, command='echo ok',
                           topology=tree, newroot=myhost)
        # XXX Need to propagate topology for this to work in tests
        raise RuntimeError

        task = task_self()
        task.set_info('debug', True)
        task.schedule(wtree)
        task.resume()

        for buf, nodes in task.iter_buffers():
            print '-' * 15
            print str(nodes)
            print '-' * 15
            print buf
            print ''


def main():
    suite = unittest.TestLoader().loadTestsFromTestCase(PropagationTest)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    #cProfile.run('main()')
    main()


########NEW FILE########
__FILENAME__ = TopologyTest
#!/usr/bin/env python
# ClusterShell.Topology test suite
# Written by H. Doreau


"""Unit test for Topology"""

import copy
import sys
import time
import unittest
import tempfile

# profiling imports
#import cProfile
#from guppy import hpy
# ---

sys.path.insert(0, '../lib')

from ClusterShell.Topology import *
from ClusterShell.NodeSet import NodeSet


def chrono(func):
    def timing(*args):
        start = time.time()
        res = func(*args)
        print "execution time: %f s" % (time.time() - start)
        return res
    return timing


class TopologyTest(unittest.TestCase):

    def testInvalidConfigurationFile(self):
        """test detecting invalid configuration file"""
        parser = TopologyParser()
        self.assertRaises(TopologyError, parser.load, '/invalid/path/for/testing')

    def testTopologyGraphGeneration(self):
        """test graph generation"""
        g = TopologyGraph()
        ns1 = NodeSet('nodes[0-5]')
        ns2 = NodeSet('nodes[6-10]')
        g.add_route(ns1, ns2)
        self.assertEqual(g.dest(ns1), ns2)

    def testAddingSeveralRoutes(self):
        """test adding several valid routes"""
        g = TopologyGraph()
        admin = NodeSet('admin')
        ns0 = NodeSet('nodes[0-9]')
        ns1 = NodeSet('nodes[10-19]')
        g.add_route(admin, ns0)
        g.add_route(ns0, ns1)
        # Connect a new dst nodeset to an existing src
        ns2 = NodeSet('nodes[20-29]')
        g.add_route(ns0, ns2)
        # Add the same dst nodeset twice (no error)
        g.add_route(ns0, ns2)

        self.assertEquals(g.dest(admin), ns0)
        self.assertEquals(g.dest(ns0), ns1 | ns2)

    def testBadLink(self):
        """test detecting bad links in graph"""
        g = TopologyGraph()
        admin = NodeSet('admin')
        ns0 = NodeSet('nodes[0-9]')
        ns1 = NodeSet('nodes[10-19]')
        g.add_route(admin, ns0)
        g.add_route(ns0, ns1)
        # Add a known src nodeset as a dst nodeset (error!)
        self.assertRaises(TopologyError, g.add_route, ns1, ns0)

    def testOverlappingRoutes(self):
        """test overlapping routes detection"""
        g = TopologyGraph()
        admin = NodeSet('admin')
        # Add the same nodeset twice
        ns0 = NodeSet('nodes[0-9]')
        ns1 = NodeSet('nodes[10-19]')
        ns1_overlap = NodeSet('nodes[5-29]')

        self.assertRaises(TopologyError, g.add_route, ns0, ns0)
        g.add_route(ns0, ns1)
        self.assertRaises(TopologyError, g.add_route, ns0, ns1_overlap)

    def testBadTopologies(self):
        """test detecting invalid topologies"""
        g = TopologyGraph()
        admin = NodeSet('admin')
        # Add the same nodeset twice
        ns0 = NodeSet('nodes[0-9]')
        ns1 = NodeSet('nodes[10-19]')
        ns2 = NodeSet('nodes[20-29]')

        g.add_route(admin, ns0)
        g.add_route(ns0, ns1)
        g.add_route(ns0, ns2)

        # add a superset of a known destination as source
        ns2_sup = NodeSet('somenode[0-10]')
        ns2_sup.add(ns2)
        self.assertRaises(TopologyError, g.add_route, ns2_sup, NodeSet('foo1'))
        
        # Add a known dst nodeset as a src nodeset
        ns3 = NodeSet('nodes[30-39]')
        g.add_route(ns1, ns3)

        # Add a subset of a known src nodeset as src
        ns0_sub = NodeSet(','.join(ns0[:3:]))
        ns4 = NodeSet('nodes[40-49]')
        g.add_route(ns0_sub, ns4)

        # Add a subset of a known dst nodeset as src
        ns1_sub = NodeSet(','.join(ns1[:3:]))
        self.assertRaises(TopologyError, g.add_route, ns4, ns1_sub)
        # Add a subset of a known src nodeset as dst
        self.assertRaises(TopologyError, g.add_route, ns4, ns0_sub)
        # Add a subset of a known dst nodeset as dst
        self.assertRaises(TopologyError, g.add_route, ns4, ns1_sub)
        # src <- subset of -> dst
        ns5 = NodeSet('nodes[50-59]')
        ns5_sub = NodeSet(','.join(ns5[:3:]))
        self.assertRaises(TopologyError, g.add_route, ns5, ns5_sub)
        self.assertRaises(TopologyError, g.add_route, ns5_sub, ns5)

        self.assertEqual(g.dest(ns0), (ns1 | ns2))
        self.assertEqual(g.dest(ns1), ns3)
        self.assertEqual(g.dest(ns2), None)
        self.assertEqual(g.dest(ns3), None)
        self.assertEqual(g.dest(ns4), None)
        self.assertEqual(g.dest(ns5), None)
        self.assertEqual(g.dest(ns0_sub), (ns1 | ns2 | ns4))

        g = TopologyGraph()
        root = NodeSet('root')
        ns01 = NodeSet('nodes[0-1]')
        ns23 = NodeSet('nodes[2-3]')
        ns45 = NodeSet('nodes[4-5]')
        ns67 = NodeSet('nodes[6-7]')
        ns89 = NodeSet('nodes[8-9]')

        g.add_route(root, ns01)
        g.add_route(root, ns23 | ns45)
        self.assertRaises(TopologyError, g.add_route, ns23, ns23)
        self.assertRaises(TopologyError, g.add_route, ns45, root)
        g.add_route(ns23, ns67)
        g.add_route(ns67, ns89)
        self.assertRaises(TopologyError, g.add_route, ns89, ns67)
        self.assertRaises(TopologyError, g.add_route, ns89, ns89)
        self.assertRaises(TopologyError, g.add_route, ns89, ns23)

        ns_all = NodeSet('root,nodes[0-9]')
        for nodegroup in g.to_tree('root'):
            ns_all.difference_update(nodegroup.nodeset)
        self.assertEqual(len(ns_all), 0)
    
    def testInvalidRootNode(self):
        """test invalid root node specification"""
        g = TopologyGraph()
        ns0 = NodeSet('node[0-9]')
        ns1 = NodeSet('node[10-19]')
        g.add_route(ns0, ns1)
        self.assertRaises(TopologyError, g.to_tree, 'admin1')

    def testMultipleAdminGroups(self):
        """test topology with several admin groups"""
        ## -------------------
        # TODO : uncommenting following lines should not produce an error. This
        # is a valid topology!!
        # ----------
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write('[Main]\n')
        tmpfile.write('admin0: nodes[0-1]\n')
        #tmpfile.write('admin1: nodes[0-1]\n')
        tmpfile.write('admin2: nodes[2-3]\n')
        #tmpfile.write('admin3: nodes[2-3]\n')
        tmpfile.write('nodes[0-1]: nodes[10-19]\n')
        tmpfile.write('nodes[2-3]: nodes[20-29]\n')
        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)

        ns_all = NodeSet('admin2,nodes[2-3,20-29]')
        ns_tree = NodeSet()
        for nodegroup in parser.tree('admin2'):
           ns_tree.add(nodegroup.nodeset)
        self.assertEqual(str(ns_all), str(ns_tree))

    def testTopologyGraphBigGroups(self):
        """test adding huge nodegroups in routes"""
        g = TopologyGraph()
        ns0 = NodeSet('nodes[0-10000]')
        ns1 = NodeSet('nodes[12000-23000]')
        g.add_route(ns0, ns1)
        self.assertEqual(g.dest(ns0), ns1)

        ns2 = NodeSet('nodes[30000-35000]')
        ns3 = NodeSet('nodes[35001-45000]')
        g.add_route(ns2, ns3)
        self.assertEqual(g.dest(ns2), ns3)

    def testNodeString(self):
        """test loading a linear string topology"""
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write('[Main]\n')

        # TODO : increase the size
        ns = NodeSet('node[0-10]')

        prev = 'admin'
        for n in ns:
            tmpfile.write('%s: %s\n' % (prev, str(n)))
            prev = n
        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)

        tree = parser.tree('admin')

        ns.add('admin')
        ns_tree = NodeSet()
        for nodegroup in tree:
            ns_tree.add(nodegroup.nodeset)
        self.assertEquals(ns, ns_tree)

    def testConfigurationParser(self):
        """test configuration parsing"""
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write('# this is a comment\n')
        tmpfile.write('[Main]\n')
        tmpfile.write('admin: nodes[0-1]\n')
        tmpfile.write('nodes[0-1]: nodes[2-5]\n')
        tmpfile.write('nodes[4-5]: nodes[6-9]\n')
        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)

        parser.tree('admin')
        ns_all = NodeSet('admin,nodes[0-9]')
        ns_tree = NodeSet()
        for nodegroup in parser.tree('admin'):
           ns_tree.add(nodegroup.nodeset)
        self.assertEqual(str(ns_all), str(ns_tree))

    def testConfigurationShortSyntax(self):
        """test short topology specification syntax"""
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write('# this is a comment\n')
        tmpfile.write('[Main]\n')
        tmpfile.write('admin: nodes[0-9]\n')
        tmpfile.write('nodes[0-3,5]: nodes[10-19]\n')
        tmpfile.write('nodes[4,6-9]: nodes[30-39]\n')
        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)

        ns_all = NodeSet('admin,nodes[0-19,30-39]')
        ns_tree = NodeSet()
        for nodegroup in parser.tree('admin'):
           ns_tree.add(nodegroup.nodeset)
        self.assertEqual(str(ns_all), str(ns_tree))

    def testConfigurationLongSyntax(self):
        """test detailed topology description syntax"""
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write('# this is a comment\n')
        tmpfile.write('[Main]\n')
        tmpfile.write('admin: proxy\n')
        tmpfile.write('proxy: STA[0-1]\n')
        tmpfile.write('STA0: STB[0-1]\n')
        tmpfile.write('STB0: nodes[0-2]\n')
        tmpfile.write('STB1: nodes[3-5]\n')
        tmpfile.write('STA1: STB[2-3]\n')
        tmpfile.write('STB2: nodes[6-7]\n')
        tmpfile.write('STB3: nodes[8-10]\n')

        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)

        ns_all = NodeSet('admin,proxy,STA[0-1],STB[0-3],nodes[0-10]')
        ns_tree = NodeSet()
        for nodegroup in parser.tree('admin'):
           ns_tree.add(nodegroup.nodeset)
        self.assertEqual(str(ns_all), str(ns_tree))

    def testConfigurationParserDeepTree(self):
        """test a configuration that generates a deep tree"""
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write('# this is a comment\n')
        tmpfile.write('[Main]\n')
        tmpfile.write('admin: nodes[0-9]\n')

        levels = 15 # how deep do you want the tree to be?
        for i in xrange(0, levels*10, 10):
            line = 'nodes[%d-%d]: nodes[%d-%d]\n' % (i, i+9, i+10, i+19)
            tmpfile.write(line)
        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)

        ns_all = NodeSet('admin,nodes[0-159]')
        ns_tree = NodeSet()
        for nodegroup in parser.tree('admin'):
           ns_tree.add(nodegroup.nodeset)
        self.assertEqual(str(ns_all), str(ns_tree))

    def testConfigurationParserBigTree(self):
        """test configuration parser against big propagation tree"""
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write('# this is a comment\n')
        tmpfile.write('[Main]\n')
        tmpfile.write('admin: ST[0-4]\n')
        tmpfile.write('ST[0-4]: STA[0-49]\n')
        tmpfile.write('STA[0-49]: nodes[0-10000]\n')
        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)

        ns_all = NodeSet('admin,ST[0-4],STA[0-49],nodes[0-10000]')
        ns_tree = NodeSet()
        for nodegroup in parser.tree('admin'):
           ns_tree.add(nodegroup.nodeset)
        self.assertEqual(str(ns_all), str(ns_tree))

    def testConfigurationParserConvergentPaths(self):
        """convergent paths detection"""
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write('# this is a comment\n')
        tmpfile.write('[Main]\n')
        tmpfile.write('fortoy32: fortoy[33-34]\n')
        tmpfile.write('fortoy33: fortoy35\n')
        tmpfile.write('fortoy34: fortoy36\n')
        tmpfile.write('fortoy[35-36]: fortoy37\n')

        tmpfile.flush()
        parser = TopologyParser()
        self.assertRaises(TopologyError, parser.load, tmpfile.name)

    def testPrintingTree(self):
        """test printing tree"""
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write('[Main]\n')
        tmpfile.write('n0: n[1-2]\n')
        tmpfile.write('n1: n[10-49]\n')
        tmpfile.write('n2: n[50-89]\n')

        tmpfile.flush()
        parser = TopologyParser()
        parser.load(tmpfile.name)

        tree = parser.tree('n0')

        # In fact it looks like this:
        # ---------------------------
        # n0
        # |_ n1
        # |  |_ n[10-49]
        # |_ n2
        #    |_ n[50-89]
        # ---------------------------
        display_ref = 'n0\n|- n1\n|  `- n[10-49]\n`- n2\n   `- n[50-89]\n'
        display = str(tree)
        print "\n%s" % display
        self.assertEquals(display, display_ref)

        self.assertEquals(str(TopologyTree()), '<TopologyTree instance (empty)>')

    def testAddingInvalidChildren(self):
        """test detecting invalid children"""
        t0 = TopologyNodeGroup(NodeSet('node[0-9]'))
        self.assertRaises(AssertionError, t0.add_child, 'foobar')
        t1 = TopologyNodeGroup(NodeSet('node[10-19]'))

        t0.add_child(t1)
        self.assertEquals(t0.children_ns(), t1.nodeset)
        t0.add_child(t1)
        self.assertEquals(t0.children_ns(), t1.nodeset)

    def testRemovingChild(self):
        """test child removal operation"""
        t0 = TopologyNodeGroup(NodeSet('node[0-9]'))
        t1 = TopologyNodeGroup(NodeSet('node[10-19]'))

        t0.add_child(t1)
        self.assertEquals(t0.children_ns(), t1.nodeset)
        t0.clear_child(t1)
        self.assertEquals(t0.children_ns(), None)

        t0.clear_child(t1) # error discarded
        self.assertRaises(ValueError, t0.clear_child, t1, strict=True)

        t2 = TopologyNodeGroup(NodeSet('node[20-29]'))
        t0.add_child(t1)
        t0.add_child(t2)
        self.assertEquals(t0.children_ns(), t1.nodeset | t2.nodeset)
        t0.clear_children()
        self.assertEquals(t0.children_ns(), None)
        self.assertEquals(t0.children_len(), 0)

    def testStrConversions(self):
        """test str() casts"""
        t = TopologyNodeGroup(NodeSet('admin0'))
        self.assertEquals(str(t), '<TopologyNodeGroup (admin0)>')

        t = TopologyRoutingTable()
        r0 = TopologyRoute(NodeSet('src[0-9]'), NodeSet('dst[5-8]'))
        r1 = TopologyRoute(NodeSet('src[10-19]'), NodeSet('dst[15-18]'))

        self.assertEquals(str(r0), 'src[0-9] -> dst[5-8]')
        
        t.add_route(r0)
        t.add_route(r1)
        self.assertEquals(str(t), 'src[0-9] -> dst[5-8]\nsrc[10-19] -> dst[15-18]')

        g = TopologyGraph()
        # XXX: Actually if g is not empty other things will be printed out...
        self.assertEquals(str(g), '<TopologyGraph>\n')


def main():
    suite = unittest.TestLoader().loadTestsFromTestCase(TopologyTest)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    #cProfile.run('main()')
    main()


########NEW FILE########
