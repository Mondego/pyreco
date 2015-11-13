__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
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
"""

import os, shutil, sys, tempfile
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", help="use a specific zc.buildout version")

parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", "--config-file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))
parser.add_option("-f", "--find-links",
                   help=("Specify a URL to search for buildout releases"))


options, args = parser.parse_args()

######################################################################
# load/install distribute

to_reload = False
try:
    import pkg_resources, setuptools
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}

    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    exec(urlopen('http://python-distribute.org/distribute_setup.py').read(), ez)
    setup_args = dict(to_dir=tmpeggs, download_delay=0, no_fake=True)
    ez['use_setuptools'](**setup_args)

    if to_reload:
        reload(pkg_resources)
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

######################################################################
# Install buildout

ws  = pkg_resources.working_set

cmd = [sys.executable, '-c',
       'from setuptools.command.easy_install import main; main()',
       '-mZqNxd', tmpeggs]

find_links = os.environ.get(
    'bootstrap-testing-find-links',
    options.find_links or
    ('http://downloads.buildout.org/'
     if options.accept_buildout_test_releases else None)
    )
if find_links:
    cmd.extend(['-f', find_links])

distribute_path = ws.find(
    pkg_resources.Requirement.parse('distribute')).location

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'
    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[distribute_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version
if version:
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

import subprocess
if subprocess.call(cmd, env=dict(os.environ, PYTHONPATH=distribute_path)) != 0:
    raise Exception(
        "Failed to execute command:\n%s",
        repr(cmd)[1:-1])

######################################################################
# Import and run buildout

ws.add_entry(tmpeggs)
ws.require(requirement)
import zc.buildout.buildout

if not [a for a in args if '=' not in a]:
    args.append('bootstrap')

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = arbiter
import errno
import logging
import os
import gc
from circus.fixed_threading import Thread, get_ident
import sys
from time import sleep
import select
import socket
from tornado import gen
import time

import zmq
from zmq.eventloop import ioloop

from circus.controller import Controller
from circus.exc import AlreadyExist
from circus import logger
from circus.watcher import Watcher
from circus.util import debuglog, _setproctitle, parse_env_dict
from circus.util import DictDiffer, synchronized, tornado_sleep
from circus.config import get_config
from circus.plugins import get_plugin_cmd
from circus.sockets import CircusSocket, CircusSockets


_ENV_EXCEPTIONS = ('__CF_USER_TEXT_ENCODING', 'PS1', 'COMP_WORDBREAKS',
                   'PROMPT_COMMAND')


class Arbiter(object):

    """Class used to control a list of watchers.

    Options:

    - **watchers** -- a list of Watcher objects
    - **endpoint** -- the controller ZMQ endpoint
    - **pubsub_endpoint** -- the pubsub endpoint
    - **statsd** -- If True, a circusd-stats process is run (default: False)
    - **stats_endpoint** -- the stats endpoint.
    - **statsd_close_outputs** -- if True sends the circusd-stats stdout/stderr
      to /dev/null (default: False)
    - **multicast_endpoint** -- the multicast endpoint for circusd cluster
      auto-discovery (default: udp://237.219.251.97:12027)
      Multicast addr should be between 224.0.0.0 to 239.255.255.255 and the
      same for the all cluster.
    - **check_delay** -- the delay between two controller points
      (default: 1 s)
    - **prereload_fn** -- callable that will be executed on each reload
      (default: None)
    - **context** -- if provided, the zmq context to reuse.
      (default: None)
    - **loop**: if provided, a :class:`zmq.eventloop.ioloop.IOLoop` instance
       to reuse. (default: None)
    - **plugins** -- a list of plugins. Each item is a mapping with:

        - **use** -- Fully qualified name that points to the plugin class
        - every other value is passed to the plugin in the **config** option
    - **sockets** -- a mapping of sockets. Each key is the socket name,
      and each value a :class:`CircusSocket` class. (default: None)
    - **warmup_delay** -- a delay in seconds between two watchers startup.
      (default: 0)
    - **httpd** -- If True, a circushttpd process is run (default: False)
    - **httpd_host** -- the circushttpd host (default: localhost)
    - **httpd_port** -- the circushttpd port (default: 8080)
    - **httpd_close_outputs** -- if True, sends circushttpd stdout/stderr
      to /dev/null. (default: False)
    - **debug** -- if True, adds a lot of debug info in the stdout (default:
      False)
    - **debug_gc** -- if True, does gc.set_debug(gc.DEBUG_LEAK) (default:
      False)
      to circusd to analyze problems (default: False)
    - **proc_name** -- the arbiter process name
    - **fqdn_prefix** -- a prefix for the unique identifier of the circus
                         instance on the cluster.
    - **endpoint_owner** -- unix user to chown the endpoint to if using ipc.
    """

    def __init__(self, watchers, endpoint, pubsub_endpoint, check_delay=1.0,
                 prereload_fn=None, context=None, loop=None, statsd=False,
                 stats_endpoint=None, statsd_close_outputs=False,
                 multicast_endpoint=None, plugins=None,
                 sockets=None, warmup_delay=0, httpd=False,
                 httpd_host='localhost', httpd_port=8080,
                 httpd_close_outputs=False, debug=False, debug_gc=False,
                 ssh_server=None, proc_name='circusd', pidfile=None,
                 loglevel=None, logoutput=None, loggerconfig=None,
                 fqdn_prefix=None, umask=None, endpoint_owner=None):

        self.watchers = watchers
        self.endpoint = endpoint
        self.check_delay = check_delay
        self.prereload_fn = prereload_fn
        self.pubsub_endpoint = pubsub_endpoint
        self.multicast_endpoint = multicast_endpoint
        self.proc_name = proc_name
        self.ssh_server = ssh_server
        self.evpub_socket = None
        self.pidfile = pidfile
        self.loglevel = loglevel
        self.logoutput = logoutput
        self.loggerconfig = loggerconfig
        self.umask = umask
        self.endpoint_owner = endpoint_owner
        self._running = False
        try:
            # getfqdn appears to fail in Python3.3 in the unittest
            # framework so fall back to gethostname
            socket_fqdn = socket.getfqdn()
        except KeyError:
            socket_fqdn = socket.gethostname()
        if fqdn_prefix is None:
            fqdn = socket_fqdn
        else:
            fqdn = '{}@{}'.format(fqdn_prefix, socket_fqdn)
        self.fqdn = fqdn

        self.ctrl = self.loop = None
        self._provided_loop = False
        self.socket_event = False
        if loop is not None:
            self._provided_loop = True
            self.loop = loop

        # initialize zmq context
        self._init_context(context)
        self.pid = os.getpid()
        self._watchers_names = {}
        self._stopping = False
        self._restarting = False
        self.debug = debug
        self._exclusive_running_command = None
        if self.debug:
            self.stdout_stream = self.stderr_stream = {'class': 'StdoutStream'}
        else:
            self.stdout_stream = self.stderr_stream = None

        self.debug_gc = debug_gc
        if debug_gc:
            gc.set_debug(gc.DEBUG_LEAK)

        # initializing circusd-stats as a watcher when configured
        self.statsd = statsd
        self.stats_endpoint = stats_endpoint

        if self.statsd:
            cmd = "%s -c 'from circus import stats; stats.main()'" % \
                sys.executable
            cmd += ' --endpoint %s' % self.endpoint
            cmd += ' --pubsub %s' % self.pubsub_endpoint
            cmd += ' --statspoint %s' % self.stats_endpoint
            if ssh_server is not None:
                cmd += ' --ssh %s' % ssh_server
            if debug:
                cmd += ' --log-level DEBUG'
            elif self.loglevel:
                cmd += ' --log-level ' + self.loglevel
            if self.logoutput:
                cmd += ' --log-output ' + self.logoutput
            stats_watcher = Watcher('circusd-stats', cmd, use_sockets=True,
                                    singleton=True,
                                    stdout_stream=self.stdout_stream,
                                    stderr_stream=self.stderr_stream,
                                    copy_env=True, copy_path=True,
                                    close_child_stderr=statsd_close_outputs,
                                    close_child_stdout=statsd_close_outputs)

            self.watchers.append(stats_watcher)

        # adding the httpd
        if httpd:
            # adding the socket
            httpd_socket = CircusSocket(name='circushttpd', host=httpd_host,
                                        port=httpd_port)
            if sockets is None:
                sockets = [httpd_socket]
            else:
                sockets.append(httpd_socket)

            cmd = ("%s -c 'from circusweb import circushttpd; "
                   "circushttpd.main()'") % sys.executable
            cmd += ' --endpoint %s' % self.endpoint
            cmd += ' --fd $(circus.sockets.circushttpd)'
            if ssh_server is not None:
                cmd += ' --ssh %s' % ssh_server

            # Adding the watcher
            httpd_watcher = Watcher('circushttpd', cmd, use_sockets=True,
                                    singleton=True,
                                    stdout_stream=self.stdout_stream,
                                    stderr_stream=self.stderr_stream,
                                    copy_env=True, copy_path=True,
                                    close_child_stderr=httpd_close_outputs,
                                    close_child_stdout=httpd_close_outputs)
            self.watchers.append(httpd_watcher)

        # adding each plugin as a watcher
        ch_stderr = self.stderr_stream is None
        ch_stdout = self.stdout_stream is None

        if plugins is not None:
            for plugin in plugins:
                fqn = plugin['use']
                cmd = get_plugin_cmd(plugin, self.endpoint,
                                     self.pubsub_endpoint, self.check_delay,
                                     ssh_server, debug=self.debug,
                                     loglevel=self.loglevel,
                                     logoutput=self.logoutput)
                plugin_cfg = dict(cmd=cmd, priority=1, singleton=True,
                                  stdout_stream=self.stdout_stream,
                                  stderr_stream=self.stderr_stream,
                                  copy_env=True, copy_path=True,
                                  close_child_stderr=ch_stderr,
                                  close_child_stdout=ch_stdout)
                plugin_cfg.update(plugin)
                if 'name' not in plugin_cfg:
                    plugin_cfg['name'] = fqn

                plugin_watcher = Watcher.load_from_config(plugin_cfg)
                self.watchers.append(plugin_watcher)

        self.sockets = CircusSockets(sockets)
        self.warmup_delay = warmup_delay

    @property
    def running(self):
        return self._running

    def _init_context(self, context):
        self.context = context or zmq.Context.instance()
        if self.loop is None:
            ioloop.install()
            self.loop = ioloop.IOLoop.instance()
        self.ctrl = Controller(self.endpoint, self.multicast_endpoint,
                               self.context, self.loop, self, self.check_delay,
                               self.endpoint_owner)

    def get_socket(self, name):
        return self.sockets.get(name, None)

    def get_socket_config(self, config, name):
        for i in config.get('sockets', []):
            if i['name'] == name:
                return i.copy()
        return None

    def get_watcher_config(self, config, name):
        for i in config.get('watchers', []):
            if i['name'] == name:
                return i.copy()
        return None

    def get_plugin_config(self, config, name):
        for i in config.get('plugins', []):
            if i['name'] == name:
                cfg = i.copy()
                cmd = get_plugin_cmd(cfg, self.endpoint,
                                     self.pubsub_endpoint, self.check_delay,
                                     self.ssh_server, debug=self.debug)

                cfg.update(dict(cmd=cmd, priority=1, singleton=True,
                                stdout_stream=self.stdout_stream,
                                stderr_stream=self.stderr_stream,
                                copy_env=True, copy_path=True))
                return cfg
        return None

    @classmethod
    def get_arbiter_config(cls, config):
        cfg = config.copy()
        del cfg['watchers']
        del cfg['plugins']
        del cfg['sockets']

        return cfg

    @synchronized("arbiter_reload_config")
    @gen.coroutine
    def reload_from_config(self, config_file=None, inside_circusd=False):
        new_cfg = get_config(config_file if config_file else self.config_file)
        # if arbiter is changed, reload everything
        if self.get_arbiter_config(new_cfg) != self._cfg:
            yield self._restart(inside_circusd=inside_circusd)
            return

        ignore_sn = set(['circushttpd'])
        ignore_wn = set(['circushttpd', 'circusd-stats'])

        # Gather socket names.
        current_sn = set([i.name for i in self.sockets.values()]) - ignore_sn
        new_sn = set([i['name'] for i in new_cfg.get('sockets', [])])
        added_sn = new_sn - current_sn
        deleted_sn = current_sn - new_sn
        maybechanged_sn = current_sn - deleted_sn
        changed_sn = set([])
        wn_with_changed_socket = set([])
        wn_with_deleted_socket = set([])

        # get changed sockets
        for n in maybechanged_sn:
            s = self.get_socket(n)
            if self.get_socket_config(new_cfg, n) != s._cfg:
                changed_sn.add(n)

                # just delete the socket and add it again
                deleted_sn.add(n)
                added_sn.add(n)

                # Get the watchers whichs use these, so they could be
                # deleted and added also
                for w in self.iter_watchers():
                    if 'circus.sockets.%s' % n.lower() in w.cmd:
                        wn_with_changed_socket.add(w.name)

        # get deleted sockets
        for n in deleted_sn:
            s = self.get_socket(n)
            s.close()
            # Get the watchers whichs use these, these should not be
            # active anymore
            for w in self.iter_watchers():
                if 'circus.sockets.%s' % n.lower() in w.cmd:
                    wn_with_deleted_socket.add(w.name)
            del self.sockets[s.name]

        # get added sockets
        for n in added_sn:
            socket_config = self.get_socket_config(new_cfg, n)
            s = CircusSocket.load_from_config(socket_config)
            s.bind_and_listen()
            self.sockets[s.name] = s

        if added_sn or deleted_sn:
            # make sure all existing watchers get the new sockets in
            # their attributes and get the old removed
            # XXX: is this necessary? self.sockets is an mutable
            # object
            for watcher in self.iter_watchers():
                # XXX: What happens as initalize is called on a
                # running watcher?
                watcher.initialize(self.evpub_socket, self.sockets, self)

        # Gather watcher names.
        current_wn = set([i.name for i in self.iter_watchers()]) - ignore_wn
        new_wn = set([i['name'] for i in new_cfg.get('watchers', [])])
        new_wn = new_wn | set([i['name'] for i in new_cfg.get('plugins', [])])
        added_wn = (new_wn - current_wn) | wn_with_changed_socket
        deleted_wn = current_wn - new_wn - wn_with_changed_socket
        maybechanged_wn = current_wn - deleted_wn
        changed_wn = set([])

        if wn_with_deleted_socket and wn_with_deleted_socket not in new_wn:
            raise ValueError('Watchers %s uses a socket which is deleted' %
                             wn_with_deleted_socket)

        # get changed watchers
        for n in maybechanged_wn:
            w = self.get_watcher(n)
            new_watcher_cfg = (self.get_watcher_config(new_cfg, n) or
                               self.get_plugin_config(new_cfg, n))
            old_watcher_cfg = w._cfg.copy()

            if 'env' in new_watcher_cfg:
                new_watcher_cfg['env'] = parse_env_dict(new_watcher_cfg['env'])

            # discarding env exceptions
            for key in _ENV_EXCEPTIONS:
                if 'env' in new_watcher_cfg and key in new_watcher_cfg['env']:
                    del new_watcher_cfg['env'][key]

                if 'env' in new_watcher_cfg and key in old_watcher_cfg['env']:
                    del old_watcher_cfg['env'][key]

            diff = DictDiffer(new_watcher_cfg, old_watcher_cfg).changed()

            if diff == set(['numprocesses']):
                # if nothing but the number of processes is
                # changed, just changes this
                w.set_numprocesses(int(new_watcher_cfg['numprocesses']))
                changed = False
            else:
                changed = len(diff) > 0

            if changed:
                # Others things are changed. Just delete and add the watcher.
                changed_wn.add(n)
                deleted_wn.add(n)
                added_wn.add(n)

        # delete watchers
        for n in deleted_wn:
            w = self.get_watcher(n)
            yield w._stop()
            del self._watchers_names[w.name.lower()]
            self.watchers.remove(w)

        # add watchers
        for n in added_wn:
            new_watcher_cfg = (self.get_plugin_config(new_cfg, n) or
                               self.get_watcher_config(new_cfg, n))

            w = Watcher.load_from_config(new_watcher_cfg)
            w.initialize(self.evpub_socket, self.sockets, self)
            yield self.start_watcher(w)
            self.watchers.append(w)
            self._watchers_names[w.name.lower()] = w

    @classmethod
    def load_from_config(cls, config_file, loop=None):
        cfg = get_config(config_file)
        watchers = []
        for watcher in cfg.get('watchers', []):
            watchers.append(Watcher.load_from_config(watcher))

        sockets = []
        for socket_ in cfg.get('sockets', []):
            sockets.append(CircusSocket.load_from_config(socket_))

        httpd = cfg.get('httpd', False)
        if httpd:
            # controlling that we have what it takes to run the web UI
            # if something is missing this will tell the user
            try:
                import circusweb  # NOQA
            except ImportError:
                logger.error('You need to install circus-web')
                sys.exit(1)

        # creating arbiter
        arbiter = cls(watchers, cfg['endpoint'], cfg['pubsub_endpoint'],
                      check_delay=cfg.get('check_delay', 1.),
                      prereload_fn=cfg.get('prereload_fn'),
                      statsd=cfg.get('statsd', False),
                      stats_endpoint=cfg.get('stats_endpoint'),
                      multicast_endpoint=cfg.get('multicast_endpoint'),
                      plugins=cfg.get('plugins'), sockets=sockets,
                      warmup_delay=cfg.get('warmup_delay', 0),
                      httpd=httpd,
                      loop=loop,
                      httpd_host=cfg.get('httpd_host', 'localhost'),
                      httpd_port=cfg.get('httpd_port', 8080),
                      debug=cfg.get('debug', False),
                      debug_gc=cfg.get('debug_gc', False),
                      ssh_server=cfg.get('ssh_server', None),
                      pidfile=cfg.get('pidfile', None),
                      loglevel=cfg.get('loglevel', None),
                      logoutput=cfg.get('logoutput', None),
                      loggerconfig=cfg.get('loggerconfig', None),
                      fqdn_prefix=cfg.get('fqdn_prefix', None),
                      umask=cfg['umask'],
                      endpoint_owner=cfg.get('endpoint_owner', None))

        # store the cfg which will be used, so it can be used later
        # for checking if the cfg has been changed
        arbiter._cfg = cls.get_arbiter_config(cfg)
        arbiter.config_file = config_file

        return arbiter

    def iter_watchers(self, reverse=True):
        return sorted(self.watchers, key=lambda a: a.priority, reverse=reverse)

    @debuglog
    def initialize(self):
        # set process title
        _setproctitle(self.proc_name)

        # set umask even though we may have already set it early in circusd.py
        if self.umask is not None:
            os.umask(self.umask)

        # event pub socket
        self.evpub_socket = self.context.socket(zmq.PUB)
        self.evpub_socket.bind(self.pubsub_endpoint)
        self.evpub_socket.linger = 0

        # initialize sockets
        if len(self.sockets) > 0:
            self.sockets.bind_and_listen_all()
            logger.info("sockets started")

        # initialize watchers
        for watcher in self.iter_watchers():
            self._watchers_names[watcher.name.lower()] = watcher
            watcher.initialize(self.evpub_socket, self.sockets, self)

    @gen.coroutine
    def start_watcher(self, watcher):
        """Aska a specific watcher to start and wait for the specified
        warmup delay."""
        if watcher.autostart:
            yield watcher._start()
            yield tornado_sleep(self.warmup_delay)

    @gen.coroutine
    @debuglog
    def start(self):
        """Starts all the watchers.

        If the ioloop has been provided during __init__() call,
        starts all watchers as a standard coroutine

        If the ioloop hasn't been provided during __init__() call (default),
        starts all watchers and the eventloop (and blocks here). In this mode
        the method MUST NOT yield anything because it's called as a standard
        method.
        """
        logger.info("Starting master on pid %s", self.pid)
        self.initialize()

        # start controller
        self.ctrl.start()
        self._restarting = False
        try:
            # initialize processes
            logger.debug('Initializing watchers')
            if self._provided_loop:
                yield self.start_watchers()
            else:
                # start_watchers will be called just after the start_io_loop()
                self.loop.add_future(self.start_watchers(), lambda x: None)
            logger.info('Arbiter now waiting for commands')
            self._running = True
            if not self._provided_loop:
                # If an event loop is not provided, block at this line
                self.start_io_loop()
        finally:
            if not self._provided_loop:
                # If an event loop is not provided, do some cleaning
                self.stop_controller_and_close_sockets()
        raise gen.Return(self._restarting)

    def stop_controller_and_close_sockets(self):
        self.ctrl.stop()
        self.evpub_socket.close()

        if len(self.sockets) > 0:
            self.sockets.close_all()

        self._running = False

    def start_io_loop(self):
        """Starts the ioloop and wait inside it
        """
        while True:
            try:
                self.loop.start()
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    raise
            else:
                break

    @synchronized("arbiter_stop")
    @gen.coroutine
    def stop(self):
        yield self._stop()

    @gen.coroutine
    def _emergency_stop(self):
        """Emergency and fast stop, to use only in circusd
        """
        for watcher in self.iter_watchers():
            watcher.graceful_timeout = 0
        yield self._stop_watchers()
        self.stop_controller_and_close_sockets()

    @gen.coroutine
    def _stop(self):
        logger.info('Arbiter exiting')
        self._stopping = True
        yield self._stop_watchers(close_output_streams=True)
        if self._provided_loop:
            cb = self.stop_controller_and_close_sockets
            self.loop.add_callback(cb)
        else:
            self.loop.add_timeout(time.time() + 1, self._stop_cb)

    def _stop_cb(self):
        self.loop.stop()
        # stop_controller_and_close_sockets will be
        # called in the end of start() method

    def reap_processes(self):
        # map watcher to pids
        watchers_pids = {}
        for watcher in self.iter_watchers():
            if not watcher.is_stopped():
                for process in watcher.processes.values():
                    watchers_pids[process.pid] = watcher

        # detect dead children
        while True:
            try:
                # wait for our child (so it's not a zombie)
                pid, status = os.waitpid(-1, os.WNOHANG)
                if not pid:
                    break

                if pid in watchers_pids:
                    watcher = watchers_pids[pid]
                    watcher.reap_process(pid, status)
            except OSError as e:
                if e.errno == errno.EAGAIN:
                    sleep(0)
                    continue
                elif e.errno == errno.ECHILD:
                    # process already reaped
                    return
                else:
                    raise

    @synchronized("manage_watchers")
    @gen.coroutine
    def manage_watchers(self):
        if self._stopping:
            return

        need_on_demand = False
        # manage and reap processes
        self.reap_processes()
        list_to_yield = []
        for watcher in self.iter_watchers():
            if watcher.on_demand and watcher.is_stopped():
                need_on_demand = True
            list_to_yield.append(watcher.manage_processes())
        if len(list_to_yield) > 0:
            yield list_to_yield

        if need_on_demand:
            sockets = [x.fileno() for x in self.sockets.values()]
            rlist, wlist, xlist = select.select(sockets, [], [], 0)
            if rlist:
                self.socket_event = True
                self._start_watchers()
                self.socket_event = False

    @synchronized("arbiter_reload")
    @gen.coroutine
    @debuglog
    def reload(self, graceful=True, sequential=False):
        """Reloads everything.

        Run the :func:`prereload_fn` callable if any, then gracefuly
        reload all watchers.
        """
        if self._stopping:
            return
        if self.prereload_fn is not None:
            self.prereload_fn(self)

        # reopen log files
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.acquire()
                handler.stream.close()
                handler.stream = open(handler.baseFilename, handler.mode)
                handler.release()

        # gracefully reload watchers
        for watcher in self.iter_watchers():
            yield watcher._reload(graceful=graceful, sequential=sequential)
            tornado_sleep(self.warmup_delay)

    def numprocesses(self):
        """Return the number of processes running across all watchers."""
        return sum([len(watcher) for watcher in self.watchers])

    def numwatchers(self):
        """Return the number of watchers."""
        return len(self.watchers)

    def get_watcher(self, name):
        """Return the watcher *name*."""
        return self._watchers_names[name]

    def statuses(self):
        return dict([(watcher.name, watcher.status())
                     for watcher in self.watchers])

    @synchronized("arbiter_add_watcher")
    def add_watcher(self, name, cmd, **kw):
        """Adds a watcher.

        Options:

        - **name**: name of the watcher to add
        - **cmd**: command to run.
        - all other options defined in the Watcher constructor.
        """
        if name in self._watchers_names:
            raise AlreadyExist("%r already exist" % name)

        if not name:
            return ValueError("command name shouldn't be empty")

        watcher = Watcher(name, cmd, **kw)
        if self.evpub_socket is not None:
            watcher.initialize(self.evpub_socket, self.sockets, self)
        self.watchers.append(watcher)
        self._watchers_names[watcher.name.lower()] = watcher
        return watcher

    @synchronized("arbiter_rm_watcher")
    @gen.coroutine
    def rm_watcher(self, name):
        """Deletes a watcher.

        Options:

        - **name**: name of the watcher to delete
        """
        logger.debug('Deleting %r watcher', name)

        # remove the watcher from the list
        watcher = self._watchers_names.pop(name)
        del self.watchers[self.watchers.index(watcher)]

        # stop the watcher
        yield watcher._stop()

    @synchronized("arbiter_start_watchers")
    @gen.coroutine
    def start_watchers(self):
        yield self._start_watchers()

    @gen.coroutine
    def _start_watchers(self):
        for watcher in self.iter_watchers():
            if watcher.autostart:
                yield watcher._start()
                yield tornado_sleep(self.warmup_delay)

    @gen.coroutine
    @debuglog
    def _stop_watchers(self, close_output_streams=False):
        yield [w._stop(close_output_streams)
               for w in self.iter_watchers(reverse=False)]

    @synchronized("arbiter_stop_watchers")
    @gen.coroutine
    def stop_watchers(self):
        yield self._stop_watchers()

    @gen.coroutine
    def _restart(self, inside_circusd=False):
        if inside_circusd:
            self._restarting = True
            yield self._stop()
        else:
            yield self._stop_watchers()
            yield self._start_watchers()

    @synchronized("arbiter_restart")
    @gen.coroutine
    def restart(self, inside_circusd=False):
        yield self._restart(inside_circusd=inside_circusd)

    @property
    def endpoint_owner_mode(self):
        return self.ctrl.endpoint_owner_mode  # just wrap the controller


class ThreadedArbiter(Thread, Arbiter):

    def __init__(self, *args, **kw):
        Thread.__init__(self)
        Arbiter.__init__(self, *args, **kw)

    def start(self):
        return Thread.start(self)

    def run(self):
        return Arbiter.start(self)

    def stop(self):
        Arbiter.stop(self)
        if get_ident() != self.ident and self.isAlive():
            self.join()

########NEW FILE########
__FILENAME__ = circusctl
# -*- coding: utf-8 -
import argparse
import cmd
import getopt
import json
import logging
import os
import sys
import textwrap
import traceback
import shlex

# import pygments if here
try:
    import pygments     # NOQA
    from pygments.lexers import get_lexer_for_mimetype
    from pygments.formatters import TerminalFormatter
except ImportError:
    pygments = False    # NOQA

from circus import __version__
from circus.client import CircusClient
from circus.commands import get_commands
from circus.consumer import CircusConsumer
from circus.exc import CallError, ArgumentError
from circus.util import DEFAULT_ENDPOINT_SUB, DEFAULT_ENDPOINT_DEALER


USAGE = 'circusctl [options] command [args]'
VERSION = 'circusctl ' + __version__
TIMEOUT_MSG = """\

A time out usually happens in one of those cases:

#1 The Circus daemon could not be reached.
#2 The Circus daemon took too long to perform the operation

For #1, make sure you are hitting the right place
by checking your --endpoint option.

For #2, if you are not expecting a result to
come back, increase your timeout option value
(particularly with waiting switches)
"""


def prettify(jsonobj, prettify=True):
    """ prettiffy JSON output """
    if not prettify:
        return json.dumps(jsonobj)

    json_str = json.dumps(jsonobj, indent=2, sort_keys=True)
    if pygments:
        try:
            lexer = get_lexer_for_mimetype("application/json")
            return pygments.highlight(json_str, lexer, TerminalFormatter())
        except:
            pass

    return json_str


class _Help(argparse.HelpFormatter):

    commands = None

    def _metavar_formatter(self, action, default_metavar):
        if action.dest != 'command':
            return super(_Help, self)._metavar_formatter(action,
                                                         default_metavar)

        commands = sorted(self.commands.items())
        max_len = max([len(name) for name, help in commands])

        output = []
        for name, command in commands:
            output.append('\t%-*s\t%s' % (max_len, name, command.short))

        def format(tuple_size):
            res = '\n'.join(output)
            return (res, ) * tuple_size

        return format

    def start_section(self, heading):
        if heading == 'positional arguments':
            heading = 'Commands'
        super(_Help, self).start_section(heading)


def _get_switch_str(opt):
    """
    Output just the '-r, --rev [VAL]' part of the option string.
    """
    if opt[2] is None or opt[2] is True or opt[2] is False:
        default = ""
    else:
        default = "[VAL]"
    if opt[0]:
        # has a short and long option
        return "-%s, --%s %s" % (opt[0], opt[1], default)
    else:
        # only has a long option
        return "--%s %s" % (opt[1], default)


class ControllerApp(object):

    def __init__(self, commands, client=None):
        self.commands = commands
        self.client = client

    def run(self, args):
        try:
            return self.dispatch(args)
        except getopt.GetoptError as e:
            print("Error: %s\n" % str(e))
            self.display_help()
            return 2
        except CallError as e:
            sys.stderr.write("%s\n" % str(e))
            return 1
        except ArgumentError as e:
            sys.stderr.write("%s\n" % str(e))
            return 1
        except KeyboardInterrupt:
            return 1
        except Exception:
            sys.stderr.write(traceback.format_exc())
            return 1

    def dispatch(self, args):
        opts = {}
        command = self.commands[args.command]
        for option in command.options:
            name = option[1]
            if name in args:
                opts[name] = getattr(args, name)

        if args.help:
            print(textwrap.dedent(command.__doc__))
            return 0
        else:
            if hasattr(args, 'start'):
                opts['start'] = args.start

            if args.endpoint is None and command.msg_type != 'dealer':
                if command.msg_type == 'sub':
                    args.endpoint = DEFAULT_ENDPOINT_SUB
                else:
                    args.endpoint = DEFAULT_ENDPOINT_DEALER

            msg = command.message(*args.args, **opts)
            handler = getattr(self, "handle_%s" % command.msg_type)
            return handler(command, self.globalopts, msg, args.endpoint,
                           int(args.timeout), args.ssh, args.ssh_keyfile)

    def handle_sub(self, command, opts, topics, endpoint, timeout, ssh_server,
                   ssh_keyfile):
        consumer = CircusConsumer(topics, endpoint=endpoint)
        for topic, msg in consumer:
            print("%s: %s" % (topic, msg))
        return 0

    def _console(self, client, command, opts, msg):
        if opts['json']:
            return prettify(client.call(msg), prettify=opts['prettify'])
        else:
            return command.console_msg(client.call(msg))

    def handle_dealer(self, command, opts, msg, endpoint, timeout, ssh_server,
                      ssh_keyfile):
        if endpoint is not None:
            client = CircusClient(endpoint=endpoint, timeout=timeout,
                                  ssh_server=ssh_server,
                                  ssh_keyfile=ssh_keyfile)
        else:
            client = self.client

        try:
            if isinstance(msg, list):
                for i, c in enumerate(msg):
                    clm = self._console(client, c['cmd'], opts,
                                        c['msg'])
                    print("%s: %s" % (i, clm))
            else:
                print(self._console(client, command, opts, msg))
        except CallError as e:
            msg = str(e)
            if 'timed out' in str(e).lower():
                msg += TIMEOUT_MSG
            sys.stderr.write(msg)
            return 1
        finally:
            if endpoint is not None:
                client.stop()

        return 0


class CircusCtl(cmd.Cmd, object):
    """CircusCtl tool."""
    prompt = '(circusctl) '

    def __new__(cls, client, commands, *args, **kw):
        """Auto add do and complete methods for all known commands."""
        cls.commands = commands
        cls.controller = ControllerApp(commands, client)
        cls.client = client
        for name, command in commands.items():
            cls._add_do_cmd(name, command)
            cls._add_complete_cmd(name, command)
        return super(CircusCtl, cls).__new__(cls, *args, **kw)

    def __init__(self, client, *args, **kwargs):
        super(CircusCtl, self).__init__()

    @classmethod
    def _add_do_cmd(cls, cmd_name, command):
        def inner_do_cmd(cls, line):
            arguments = parse_arguments([cmd_name] + shlex.split(line),
                                        cls.commands)
            cls.controller.run(arguments['args'])
        inner_do_cmd.__doc__ = textwrap.dedent(command.__doc__)
        inner_do_cmd.__name__ = "do_%s" % cmd_name
        setattr(cls, inner_do_cmd.__name__, inner_do_cmd)

    @classmethod
    def _add_complete_cmd(cls, cmd_name, command):
        def inner_complete_cmd(cls, *args, **kwargs):
            if hasattr(command, 'autocomplete'):
                try:
                    return command.autocomplete(cls.client, *args, **kwargs)
                except Exception as e:
                    sys.stderr.write(str(e) + "\n")
                    traceback.print_exc(file=sys.stderr)
            else:
                return []
        inner_complete_cmd.__doc__ = "Complete the %s command" % cmd_name
        inner_complete_cmd.__name__ = "complete_%s" % cmd_name
        setattr(cls, inner_complete_cmd.__name__, inner_complete_cmd)

    def do_EOF(self, line):
        return True

    def postloop(self):
        sys.stdout.write('\n')

    def autocomplete(self, autocomplete=False, words=None, cword=None):
        """
        Output completion suggestions for BASH.

        The output of this function is passed to BASH's `COMREPLY` variable and
        treated as completion suggestions. `COMREPLY` expects a space
        separated string as the result.

        The `COMP_WORDS` and `COMP_CWORD` BASH environment variables are used
        to get information about the cli input. Please refer to the BASH
        man-page for more information about this variables.

        Subcommand options are saved as pairs. A pair consists of
        the long option string (e.g. '--exclude') and a boolean
        value indicating if the option requires arguments. When printing to
        stdout, a equal sign is appended to options which require arguments.

        Note: If debugging this function, it is recommended to write the debug
        output in a separate file. Otherwise the debug output will be treated
        and formatted as potential completion suggestions.
        """
        autocomplete = autocomplete or 'AUTO_COMPLETE' in os.environ

        # Don't complete if user hasn't sourced bash_completion file.
        if not autocomplete:
            return

        words = words or os.environ['COMP_WORDS'].split()[1:]
        cword = cword or int(os.environ['COMP_CWORD'])

        try:
            curr = words[cword - 1]
        except IndexError:
            curr = ''

        subcommands = get_commands()

        if cword == 1:  # if completing the command name
            print(' '.join(sorted([x for x in subcommands
                                   if x.startswith(curr)])))
        sys.exit(1)

    def start(self, globalopts):
        self.autocomplete()

        self.controller.globalopts = globalopts

        args = globalopts['args']
        parser = globalopts['parser']

        if hasattr(args, 'command'):
            sys.exit(self.controller.run(globalopts['args']))

        if args.help:
            for command in sorted(self.commands.keys()):
                doc = textwrap.dedent(self.commands[command].__doc__)
                help = doc.split('\n')[0]
                parser.add_argument(command, help=help)
            parser.print_help()
            sys.exit(0)

        # no command, no --help: enter the CLI
        print(VERSION)
        self.do_status('')
        try:
            self.cmdloop()
        except KeyboardInterrupt:
            sys.stdout.write('\n')
        sys.exit(0)


def parse_arguments(args, commands):
    _Help.commands = commands

    options = {
        'endpoint': {'default': None, 'help': 'connection endpoint'},
        'timeout': {'default': 5, 'help': 'connection timeout',
                    'type': int},

        'help': {
            'default': False,
            'action': 'store_true',
            'help': 'Show help and exit'},

        'json': {'default': False, 'action': 'store_true',
                 'help': 'output to JSON'},

        'prettify': {
            'default': False,
            'action': 'store_true',
            'help': 'prettify output'},

        'ssh': {
            'default': None,
            'help': 'SSH Server in the format user@host:port'},

        'ssh_keyfile': {
            'default': None,
            'help': 'the path to the keyfile to authorise the user'},

        'version': {
            'default': False,
            'action': 'version',
            'version': VERSION,
            'help': 'display version and exit'},
    }

    parser = argparse.ArgumentParser(
        description="Controls a Circus daemon",
        formatter_class=_Help, usage=USAGE, add_help=False)

    for option in sorted(options.keys()):
        parser.add_argument('--' + option, **options[option])

    if any([value in commands for value in args]):
        subparsers = parser.add_subparsers(dest='command')

        for command, klass in commands.items():

            subparser = subparsers.add_parser(command)
            subparser.add_argument('args', nargs="*",
                                   help=argparse.SUPPRESS)
            for option in klass.options:
                __, name, default, desc = option
                if isinstance(default, bool):
                    action = 'store_true'
                else:
                    action = 'store'

                subparser.add_argument('--' + name, action=action,
                                       default=default, help=desc)

    args = parser.parse_args(args)

    globalopts = {'args': args, 'parser': parser}
    for option in options:
        globalopts[option] = getattr(args, option)
    return globalopts


def main():
    logging.basicConfig()
    # TODO, we should ask the server for its command list
    commands = get_commands()
    globalopts = parse_arguments(sys.argv[1:], commands)
    if globalopts['endpoint'] is None:
        globalopts['endpoint'] = os.environ.get('CIRCUSCTL_ENDPOINT',
                                                DEFAULT_ENDPOINT_DEALER)
    client = CircusClient(endpoint=globalopts['endpoint'],
                          timeout=globalopts['timeout'],
                          ssh_server=globalopts['ssh'],
                          ssh_keyfile=globalopts['ssh_keyfile'])

    CircusCtl(client, commands).start(globalopts)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = circusd
import sys
import argparse
import os
import resource

from circus import logger
from circus.arbiter import Arbiter
from circus.pidfile import Pidfile
from circus import __version__
from circus.util import MAXFD, REDIRECT_TO, configure_logger, LOG_LEVELS
from circus.util import check_future_exception_and_log


def get_maxfd():
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if maxfd == resource.RLIM_INFINITY:
        maxfd = MAXFD
    return maxfd


try:
    from os import closerange
except ImportError:
    def closerange(fd_low, fd_high):    # NOQA
        # Iterate through and close all file descriptors.
        for fd in range(fd_low, fd_high):
            try:
                os.close(fd)
            except OSError:    # ERROR, fd wasn't open to begin with (ignored)
                pass


# http://www.svbug.com/documentation/comp.unix.programmer-FAQ/faq_2.html#SEC16
def daemonize():
    """Standard daemonization of a process.
    """
    # guard to prevent daemonization with gevent loaded
    for module in sys.modules.keys():
        if module.startswith('gevent'):
            raise ValueError('Cannot daemonize if gevent is loaded')

    child_pid = os.fork()

    if child_pid != 0:
        # we're in the parent
        os._exit(0)

    # child process
    os.setsid()

    subchild = os.fork()
    if subchild:
        os._exit(0)

    # subchild
    maxfd = get_maxfd()
    closerange(0, maxfd)

    os.open(REDIRECT_TO, os.O_RDWR)
    os.dup2(0, 1)
    os.dup2(0, 2)


def main():
    import zmq
    try:
        zmq_version = [int(part) for part in zmq.__version__.split('.')]
        if len(zmq_version) < 2:
            raise ValueError()
    except (AttributeError, ValueError):
        print('Unknown PyZQM version - aborting...')
        sys.exit(0)

    if zmq_version[0] < 13 or (zmq_version[0] == 13 and zmq_version[1] < 1):
        print('circusd needs PyZMQ >= 13.1.0 to run - aborting...')
        sys.exit(0)

    parser = argparse.ArgumentParser(description='Run some watchers.')
    parser.add_argument('config', help='configuration file', nargs='?')

    # XXX we should be able to add all these options in the config file as well
    parser.add_argument('--log-level', dest='loglevel',
                        choices=list(LOG_LEVELS.keys()) + [
                            key.upper() for key in LOG_LEVELS.keys()],
                        help="log level")
    parser.add_argument('--log-output', dest='logoutput', help=(
        "The location where the logs will be written. The default behavior "
        "is to write to stdout (you can force it by passing '-' to "
        "this option). Takes a filename otherwise."))
    parser.add_argument("--logger-config", dest="loggerconfig", help=(
        "The location where a standard Python logger configuration INI, "
        "JSON or YAML file can be found.  This can be used to override "
        "the default logging configuration for the arbiter."))

    parser.add_argument('--daemon', dest='daemonize', action='store_true',
                        help="Start circusd in the background")
    parser.add_argument('--pidfile', dest='pidfile')
    parser.add_argument('--version', action='store_true', default=False,
                        help='Displays Circus version and exits.')

    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    if args.config is None:
        parser.print_usage()
        sys.exit(0)

    if args.daemonize:
        daemonize()

    # From here it can also come from the arbiter configuration
    # load the arbiter from config
    arbiter = Arbiter.load_from_config(args.config)

    # go ahead and set umask early if it is in the config
    if arbiter.umask is not None:
        os.umask(arbiter.umask)

    pidfile = args.pidfile or arbiter.pidfile or None
    if pidfile:
        pidfile = Pidfile(pidfile)

        try:
            pidfile.create(os.getpid())
        except RuntimeError as e:
            print(str(e))
            sys.exit(1)

    # configure the logger
    loglevel = args.loglevel or arbiter.loglevel or 'info'
    logoutput = args.logoutput or arbiter.logoutput or '-'
    loggerconfig = args.loggerconfig or arbiter.loggerconfig or None
    configure_logger(logger, loglevel, logoutput, loggerconfig)

    # Main loop
    restart = True
    while restart:
        try:
            arbiter = arbiter or Arbiter.load_from_config(args.config)
            future = arbiter.start()
            restart = False
            if check_future_exception_and_log(future) is None:
                restart = arbiter._restarting
        except Exception as e:
            # emergency stop
            arbiter.loop.run_sync(arbiter._emergency_stop)
            raise(e)
        except KeyboardInterrupt:
            pass
        finally:
            arbiter = None
            if pidfile is not None:
                pidfile.unlink()
    sys.exit(0)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = client

# -*- coding: utf-8 -
import errno
import uuid

import zmq
import zmq.utils.jsonapi as json
from zmq.eventloop.zmqstream import ZMQStream
import tornado

from circus.exc import CallError
from circus.py3compat import string_types, b
from circus.util import DEFAULT_ENDPOINT_DEALER, get_connection


def make_message(command, **props):
    return {"command": command, "properties": props or {}}


def cast_message(command, **props):
    return {"command": command, "msg_type": "cast", "properties": props or {}}


def make_json(command, **props):
    return json.dumps(make_message(command, **props))


class AsyncCircusClient(object):

    def __init__(self, context=None, endpoint=DEFAULT_ENDPOINT_DEALER,
                 timeout=5.0, ssh_server=None, ssh_keyfile=None):
        self._init_context(context)
        self.endpoint = endpoint
        self._id = b(uuid.uuid4().hex)
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self._id)
        self.socket.setsockopt(zmq.LINGER, 0)
        get_connection(self.socket, endpoint, ssh_server, ssh_keyfile)
        self._timeout = timeout
        self.timeout = timeout * 1000
        self.stream = ZMQStream(self.socket, tornado.ioloop.IOLoop.instance())

    def _init_context(self, context):
        self.context = context or zmq.Context.instance()

    def stop(self):
        self.stream.stop_on_recv()
        # only supported by libzmq >= 3
        if hasattr(self.socket, 'disconnect'):
            self.socket.disconnect(self.endpoint)
        self.socket.close()

    def send_message(self, command, **props):
        return self.call(make_message(command, **props))

    @tornado.gen.coroutine
    def call(self, cmd):
        if isinstance(cmd, string_types):
            raise DeprecationWarning('call() takes a mapping')

        call_id = uuid.uuid4().hex
        cmd['id'] = call_id
        try:
            cmd = json.dumps(cmd)
        except ValueError as e:
            raise CallError(str(e))

        try:
            yield tornado.gen.Task(self.stream.send, cmd)
        except zmq.ZMQError as e:
            raise CallError(str(e))

        while True:
            messages = yield tornado.gen.Task(self.stream.on_recv)
            for message in messages:
                try:
                    res = json.loads(message)
                    if res.get('id') != call_id:
                        # we got the wrong message
                        continue
                    raise tornado.gen.Return(res)
                except ValueError as e:
                    raise CallError(str(e))


class CircusClient(object):
    def __init__(self, context=None, endpoint=DEFAULT_ENDPOINT_DEALER,
                 timeout=5.0, ssh_server=None, ssh_keyfile=None):
        self._init_context(context)
        self.endpoint = endpoint
        self._id = b(uuid.uuid4().hex)
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self._id)
        self.socket.setsockopt(zmq.LINGER, 0)
        get_connection(self.socket, endpoint, ssh_server, ssh_keyfile)
        self._init_poller()
        self._timeout = timeout
        self.timeout = timeout * 1000

    def _init_context(self, context):
        self.context = context or zmq.Context.instance()

    def _init_poller(self):
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def stop(self):
        # only supported by libzmq >= 3
        if hasattr(self.socket, 'disconnect'):
            self.socket.disconnect(self.endpoint)
        self.socket.close()

    def send_message(self, command, **props):
        return self.call(make_message(command, **props))

    def call(self, cmd):
        if isinstance(cmd, string_types):
            raise DeprecationWarning('call() takes a mapping')

        call_id = uuid.uuid4().hex
        cmd['id'] = call_id
        try:
            cmd = json.dumps(cmd)
        except ValueError as e:
            raise CallError(str(e))

        try:
            self.socket.send(cmd)
        except zmq.ZMQError as e:
            raise CallError(str(e))

        while True:
            try:
                events = dict(self.poller.poll(self.timeout))
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    print(str(e))
                    raise CallError(str(e))

            if len(events) == 0:
                raise CallError("Timed out.")

            for socket in events:
                msg = socket.recv()
                try:
                    res = json.loads(msg)
                    if res.get('id') != call_id:
                        # we got the wrong message
                        continue
                    return res
                except ValueError as e:
                    raise CallError(str(e))

########NEW FILE########
__FILENAME__ = addwatcher
from circus.commands.base import Command
from circus.commands.util import validate_option
from circus.exc import ArgumentError, MessageError


class AddWatcher(Command):
    """\
        Add a watcher
        =============

        This command add a watcher dynamically to a arbiter.

        ZMQ Message
        -----------

        ::

            {
                "command": "add",
                "properties": {
                    "cmd": "/path/to/commandline --option"
                    "name": "nameofwatcher"
                    "args": [],
                    "options": {},
                    "start": false
                }
            }

        A message contains 2 properties:

        - cmd: Full command line to execute in a process
        - args: array, arguments passed to the command (optional)
        - name: name of watcher
        - options: options of a watcher
        - start: start the watcher after the creation

        The response return a status "ok".

        Command line
        ------------

        ::

            $ circusctl add [--start] <name> <cmd>

        Options
        +++++++

        - <name>: name of the watcher to create
        - <cmd>: full command line to execute in a process
        - --start: start the watcher immediately

    """

    name = "add"
    options = [('', 'start', False, "start immediately the watcher")]
    properties = ['name', 'cmd']

    def message(self, *args, **opts):
        if len(args) < 2:
            raise ArgumentError("Invalid number of arguments")

        return self.make_message(name=args[0], cmd=" ".join(args[1:]),
                                 start=opts.get('start', False))

    def execute(self, arbiter, props):
        options = props.get('options', {})

        # check for endpoint_owner uid restriction mode
        # it would be better to use some type of SO_PEERCRED lookup on the ipc
        # socket to get the uid of the client process and restrict on that,
        # but there's no good portable pythonic way of doing that right now
        # inside pyzmq or here. So we'll assume that the administrator has
        # set good rights on the ipc socket to help prevent privilege
        # escalation
        if arbiter.endpoint_owner_mode:
            cmd_uid = options.get('uid', None)
            if cmd_uid != arbiter.endpoint_owner:
                raise MessageError("uid does not match endpoint_owner")
        watcher = arbiter.add_watcher(props['name'], props['cmd'],
                                      args=props.get('args'), **options)
        if props.get('start', False):
            return watcher.start()

    def validate(self, props):
        super(AddWatcher, self).validate(props)
        if 'options' in props:
            options = props.get('options')
            if not isinstance(options, dict):
                raise MessageError("'options' property should be an object")

            for key, val in props['options'].items():
                validate_option(key, val)

########NEW FILE########
__FILENAME__ = base
import copy
import textwrap
import time

from circus.exc import MessageError
from circus.commands import errors


KNOWN_COMMANDS = []


def get_commands():
    commands = {}
    for c in KNOWN_COMMANDS:
        cmd = c()
        commands[c.name] = cmd.copy()
    return commands


def ok(props=None):
    resp = {"status": "ok", "time": time.time()}
    if props:
        resp.update(props)
    return resp


def error(reason="unknown", tb=None, errno=errors.NOT_SPECIFIED):
    return {
        "status": "error",
        "reason": reason,
        "tb": tb,
        "time": time.time(),
        "errno": errno
    }


class CommandMeta(type):

    def __new__(cls, name, bases, attrs):
        super_new = type.__new__
        parents = [b for b in bases if isinstance(b, CommandMeta)]

        if not parents:
            return super_new(cls, name, bases, attrs)

        attrs["order"] = len(KNOWN_COMMANDS)
        new_class = super_new(cls, name, bases, attrs)
        new_class.fmt_desc()
        KNOWN_COMMANDS.append(new_class)
        return new_class

    def fmt_desc(cls):
        desc = textwrap.dedent(cls.__doc__).strip()
        setattr(cls, "desc",  desc)
        setattr(cls, "short", desc.splitlines()[0])


class Command(object):

    name = None
    msg_type = "dealer"
    options = []
    properties = []
    waiting = False
    waiting_options = [('waiting', 'waiting', False,
                        "Waiting the real end of the process")]

    ##################################################
    # These methods run within the circusctl process #
    ##################################################

    def make_message(self, **props):
        name = props.pop("command", self.name)
        return {"command": name, "properties": props or {}}

    def message(self, *args, **opts):
        raise NotImplementedError("message function isn't implemented")

    def console_error(self, msg):
        return "error: %s" % msg.get("reason")

    def console_msg(self, msg):
        if msg.get('status') == "ok":
            return "ok"
        return self.console_error(msg)

    def copy(self):
        return copy.copy(self)

    ################################################
    # These methods run within the circusd process #
    ################################################

    def execute(self, arbiter, props):
        raise NotImplementedError("execute function is not implemented")

    def _get_watcher(self, arbiter, watcher_name):
        """Get watcher from the arbiter if any."""
        try:
            return arbiter.get_watcher(watcher_name.lower())
        except KeyError:
            raise MessageError("program %s not found" % watcher_name)

    def validate(self, props):
        if not self.properties:
            return

        for propname in self.properties:
            if propname not in props:
                raise MessageError("message invalid %r is missing" % propname)


Command = CommandMeta('Command', (Command,), {})

########NEW FILE########
__FILENAME__ = decrproc
from circus.commands.incrproc import IncrProc
from circus.util import TransformableFuture


class DecrProcess(IncrProc):
    """\
        Decrement the number of processes in a watcher
        ==============================================

        This comment decrement the number of processes in a watcher by -1.

        ZMQ Message
        -----------

        ::

            {
                "command": "decr",
                "propeties": {
                    "name": "<watchername>"
                    "nb": <nbprocess>
                    "waiting": False
                }
            }

        The response return the number of processes in the 'numprocesses`
        property::

            { "status": "ok", "numprocesses": <n>, "time", "timestamp" }

        Command line
        ------------

        ::

            $ circusctl decr <name> [<nb>] [--waiting]

        Options
        +++++++

        - <name>: name of the watcher
        - <nb>: the number of processes to remove.

    """
    name = "decr"
    properties = ['name']

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))
        nb = props.get('nb', 1)
        resp = TransformableFuture()
        resp.set_upstream_future(watcher.decr(nb))
        resp.set_transform_function(lambda x: {"numprocesses": x})
        return resp

########NEW FILE########
__FILENAME__ = dstats
from circus.exc import ArgumentError
from circus.commands.base import Command
from circus.util import get_info

_INFOLINE = ("%(pid)s  %(cmdline)s %(username)s %(nice)s %(mem_info1)s "
             "%(mem_info2)s %(cpu)s %(mem)s %(ctime)s")


class Daemontats(Command):
    """\
       Get circusd stats
       =================

       You can get at any time some statistics about circusd
       with the dstat command.

       ZMQ Message
       -----------

       To get the circusd stats, simply run::

            {
                "command": "dstats"
            }


       The response returns a mapping the property "infos"
       containing some process informations::

            {
              "info": {
                "children": [],
                "cmdline": "python",
                "cpu": 0.1,
                "ctime": "0:00.41",
                "mem": 0.1,
                "mem_info1": "3M",
                "mem_info2": "2G",
                "nice": 0,
                "pid": 47864,
                "username": "root"
              },
              "status": "ok",
              "time": 1332265655.897085
            }

       Command Line
       ------------

       ::

            $ circusctl dstats

    """

    name = "dstats"

    def message(self, *args, **opts):
        if len(args) > 0:
            raise ArgumentError("Invalid message")
        return self.make_message()

    def execute(self, arbiter, props):
        return {'info': get_info(interval=0.01)}

    def _to_str(self, info):
        children = info.pop("children", [])
        ret = ['Main Process:',  '    ' + _INFOLINE % info]

        if len(children) > 0:
            ret.append('Children:')
            for child in children:
                ret.append('    ' + _INFOLINE % child)

        return "\n".join(ret)

    def console_msg(self, msg):
        if msg['status'] == "ok":
            return self._to_str(msg['info'])
        else:
            return self.console_error(msg)

########NEW FILE########
__FILENAME__ = errors

NOT_SPECIFIED = 0
INVALID_JSON = 1
UNKNOWN_COMMAND = 2
MESSAGE_ERROR = 3
OS_ERROR = 4
COMMAND_ERROR = 5
BAD_MSG_DATA_ERROR = 6

########NEW FILE########
__FILENAME__ = get
from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError
from circus.util import convert_opt


class Get(Command):
    """\
        Get the value of specific watcher options
        =========================================

        This command can be used to query the current value of one or
        more watcher options.

        ZMQ Message
        -----------

        ::

            {
                "command": "get",
                "properties": {
                    "keys": ["key1, "key2"]
                    "name": "nameofwatcher"
                }
            }

        A request message contains two properties:

        - keys: list, The option keys for which you want to get the values
        - name: name of watcher

        The response object has a property ``options`` which is a
        dictionary of option names and values.

        eg::

            {
                "status": "ok",
                "options": {
                    "graceful_timeout": 300,
                    "send_hup": True,
                },
                time': 1332202594.754644
            }


        Command line
        ------------

        ::

            $ circusctl get <name> <key1> <key2>

    """

    name = "get"
    properties = ['name', 'keys']

    def message(self, *args, **opts):
        if len(args) < 2:
            raise ArgumentError("Invalid number of arguments")

        return self.make_message(name=args[0], keys=args[1:])

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))

        # get options values. It return an error if one of the asked
        # options isn't found
        options = {}
        for name in props.get('keys', []):
            if name in watcher.optnames:
                options[name] = getattr(watcher, name)
            else:
                raise MessageError("%r option not found" % name)

        return {"options": options}

    def console_msg(self, msg):
        if msg['status'] == "ok":
            ret = []
            for k, v in msg.get('options', {}).items():
                ret.append("%s: %s" % (k, convert_opt(k, v)))
            return "\n".join(ret)
        return self.console_error(msg)

########NEW FILE########
__FILENAME__ = globaloptions
from circus.commands.base import Command
from circus.exc import MessageError
from circus.util import convert_opt


_OPTIONS = ('endpoint', 'stats_endpoint', 'pubsub_endpoint',
            'check_delay', 'multicast_endpoint')


class GlobalOptions(Command):
    """\
        Get the arbiter options
        =======================

        This command return the arbiter options

        ZMQ Message
        -----------

        ::

            {
                "command": "globaloptions",
                "properties": {
                    "key1": "val1",
                    ..
                }
            }

        A message contains 2 properties:

        - keys: list, The option keys for which you want to get the values

        The response return an object with a property "options"
        containing the list of key/value returned by circus.

        eg::

            {
                "status": "ok",
                "options": {
                    "check_delay": 1,
                    ...
                },
                time': 1332202594.754644
            }



        Command line
        ------------

        ::

            $ circusctl globaloptions


        Options
        -------

        Options Keys are:

        - endpoint: the controller ZMQ endpoint
        - pubsub_endpoint: the pubsub endpoint
        - check_delay: the delay between two controller points
        - multicast_endpoint: the multicast endpoint for circusd cluster
          auto-discovery
    """

    name = "globaloptions"
    properties = []

    def message(self, *args, **opts):
        if len(args) > 0:
            return self.make_message(option=args[0])
        else:
            return self.make_message()

    def execute(self, arbiter, props):
        wanted = props.get('option')
        if wanted:
            if wanted not in _OPTIONS:
                raise MessageError('%r not an existing option' % wanted)
            options = (wanted,)
        else:
            options = _OPTIONS

        res = {}

        for option in options:
            res[option] = getattr(arbiter, option)

        return {"options": res}

    def console_msg(self, msg):
        if msg['status'] == "ok":
            ret = []
            for k, v in msg.get('options', {}).items():
                ret.append("%s: %s" % (k, convert_opt(k, v)))
            return "\n".join(ret)
        return msg['reason']

########NEW FILE########
__FILENAME__ = incrproc
from circus.commands.base import Command
from circus.exc import ArgumentError
from circus.util import TransformableFuture


class IncrProc(Command):
    """\
        Increment the number of processes in a watcher
        ==============================================

        This comment increment the number of processes in a watcher by +1.

        ZMQ Message
        -----------

        ::

            {
                "command": "incr",
                "properties": {
                    "name": "<watchername>",
                    "nb": <nbprocess>,
                    "waiting": False
                }
            }

        The response return the number of processes in the 'numprocesses`
        property::

            { "status": "ok", "numprocesses": <n>, "time", "timestamp" }

        Command line
        ------------

        ::

            $ circusctl incr <name> [<nb>] [--waiting]

        Options
        +++++++

        - <name>: name of the watcher.
        - <nb>: the number of processes to add.

    """

    name = "incr"
    properties = ['name']
    options = Command.waiting_options

    def message(self, *args, **opts):
        if len(args) < 1:
            raise ArgumentError("Invalid number of arguments")
        options = {'name': args[0]}
        if len(args) > 1:
            options['nb'] = int(args[1])
        options.update(opts)
        return self.make_message(**options)

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))
        if watcher.singleton:
            return {"numprocesses": watcher.numprocesses, "singleton": True}
        else:
            nb = props.get("nb", 1)
            resp = TransformableFuture()
            resp.set_upstream_future(watcher.incr(nb))
            resp.set_transform_function(lambda x: {"numprocesses": x})
            return resp

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            if "singleton" in msg:
                return ('This watcher is a Singleton - not changing the number'
                        ' of processes')
            else:
                return str(msg.get("numprocesses", "ok"))
        return self.console_error(msg)

########NEW FILE########
__FILENAME__ = ipythonshell
import os
import sys
from circus.exc import ArgumentError
from circus.commands.base import Command


class IPythonShell(Command):
    """\
       Create shell into circusd process
       =================================

       This command is only useful if you have the ipython package installed.

       Command Line
       ------------

       ::

            $ circusctl ipython

    """

    name = "ipython"

    def message(self, *args, **opts):
        if len(args) > 0:
            raise ArgumentError("Invalid message")
        return self.make_message()

    def execute(self, arbiter, props):
        shell = 'kernel-%d.json' % os.getpid()
        msg = None
        try:
            from IPython.kernel.zmq.kernelapp import IPKernelApp
            if not IPKernelApp.initialized():
                app = IPKernelApp.instance()
                app.initialize([])
                main = app.kernel.shell._orig_sys_modules_main_mod
                if main is not None:
                    sys.modules[
                        app.kernel.shell._orig_sys_modules_main_name
                    ] = main
                app.kernel.user_module = sys.modules[__name__]
                app.kernel.user_ns = {'arbiter': arbiter}
                app.shell.set_completer_frame()
                app.kernel.start()

        except Exception as e:
            shell = False
            msg = str(e)

        return {'shell': shell, 'msg': msg}

    def console_msg(self, msg):
        if msg['status'] == "ok":
            shell = msg['shell']
            if shell:
                from IPython import start_ipython
                start_ipython(['console', '--existing', shell])
                return ''
            else:
                msg['reason'] = 'Could not start ipython kernel'
        return self.console_error(msg)

########NEW FILE########
__FILENAME__ = list
from circus.commands.base import Command
from circus.exc import ArgumentError

from circus import logger


class List(Command):
    """\
        Get list of watchers or processes in a watcher
        ==============================================

        ZMQ Message
        -----------


        To get the list of all the watchers::

            {
                "command": "list",
            }


        To get the list of active processes in a watcher::

            {
                "command": "list",
                "properties": {
                    "name": "nameofwatcher",
                }
            }


        The response return the list asked. the mapping returned can either be
        'watchers' or 'pids' depending the request.

        Command line
        ------------

        ::

            $ circusctl list [<name>]
    """
    name = "list"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("Invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            processes = watcher.get_active_processes()
            status = [(p.pid, p.status) for p in processes]
            logger.debug('here is the status of the processes %s' % status)
            return {"pids":  [p.pid for p in processes]}
        else:
            watchers = sorted(arbiter._watchers_names)
            return {"watchers": [name for name in watchers]}

    def console_msg(self, msg):
        if "pids" in msg:
            return ",".join([str(process_id)
                             for process_id in msg.get('pids')])
        elif 'watchers' in msg:
            return ",".join([watcher for watcher in msg.get('watchers')])
        if 'reason' not in msg:
            msg['reason'] = "Response doesn't contain 'pids' nor 'watchers'."
        return self.console_error(msg)

########NEW FILE########
__FILENAME__ = listen
from circus.commands.base import Command
from circus.exc import MessageError


class Listen(Command):
    """\
        Subscribe to a watcher event
        ============================

        ZMQ
        ---

        At any moment you can subscribe to a circus event. Circus provides
        a PUB/SUB feed on which any clients can subscribe. The subscriber
        endpoint URI is set in the circus.ini configuration file.

        Events are pubsub topics:

        - `watcher.<watchername>.reap`: when a process is reaped
        - `watcher.<watchername>.spawn`: when a process is spawned
        - `watcher.<watchername>.kill`: when a process is killed
        - `watcher.<watchername>.updated`: when watcher configuration
          is updated
        - `watcher.<watchername>.stop`: when a watcher is stopped
        - `watcher.<watchername>.start`: when a watcher is started

        All events messages are in a json struct.

        Command line
        ------------

        The client has been updated to provide a simple way to listen on the
        events::

            circusctl listen [<topic>, ...]

        Example of result:
        ++++++++++++++++++

        ::

            $ circusctl listen tcp://127.0.0.1:5556
            watcher.refuge.spawn: {u'process_id': 6, u'process_pid': 72976,
                                   u'time': 1331681080.985104}
            watcher.refuge.spawn: {u'process_id': 7, u'process_pid': 72995,
                                   u'time': 1331681086.208542}
            watcher.refuge.spawn: {u'process_id': 8, u'process_pid': 73014,
                                   u'time': 1331681091.427005}
    """
    name = "listen"
    msg_type = "sub"

    def message(self, *args, **opts):
        if not args:
            return [""]
        return list(args)

    def execute(self, arbiter, args):
        raise MessageError("invalid message. use a pub/sub socket")

########NEW FILE########
__FILENAME__ = listsockets
from circus.commands.base import Command
import operator


class ListSockets(Command):
    """\
        Get the list of sockets
        =======================

        ZMQ Message
        -----------


        To get the list of sockets::

            {
                "command": "listsockets",
            }


        The response return a list of json mappings with keys for fd, name,
        host and port.

        Command line
        ------------

        ::

            $ circusctl listsockets
    """
    name = "listsockets"

    def message(self, *args, **opts):
        return self.make_message()

    def execute(self, arbiter, props):

        def _get_info(socket):
            sock = {'fd': socket.fileno(),
                    'name': socket.name,
                    'backlog': socket.backlog}

            if socket.host is not None:
                sock['host'] = socket.host
                sock['port'] = socket.port
            else:
                sock['path'] = socket.path

            return sock

        sockets = [_get_info(socket) for socket in arbiter.sockets.values()]
        sockets.sort(key=operator.itemgetter('fd'))
        return {"sockets": sockets}

    def console_msg(self, msg):
        if 'sockets' in msg:
            sockets = []
            for sock in msg['sockets']:
                d = "%(fd)d:socket '%(name)s' "
                if 'path' in sock:
                    d = (d + 'at %(path)s') % sock
                else:
                    d = (d + 'at %(host)s:%(port)d') % sock

                sockets.append(d)

            return "\n".join(sockets)

        return self.console_error(msg)

########NEW FILE########
__FILENAME__ = numprocesses
from circus.commands.base import Command
from circus.exc import ArgumentError


class NumProcesses(Command):
    """\
        Get the number of processes
        ===========================

        Get the number of processes in a watcher or in a arbiter

        ZMQ Message
        -----------

        ::

            {
                "command": "numprocesses",
                "propeties": {
                    "name": "<watchername>"
                }

            }

        The response return the number of processes in the 'numprocesses`
        property::

            { "status": "ok", "numprocesses": <n>, "time", "timestamp" }

        If the property name isn't specified, the sum of all processes
        managed is returned.

        Command line
        ------------

        ::

            $ circusctl numprocesses [<name>]

        Options
        +++++++

        - <name>: name of the watcher

    """
    name = "numprocesses"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("message invalid")

        if len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            return {
                "numprocesses": len(watcher),
                "watcher_name": props['name']
            }
        else:
            return {"numprocesses": arbiter.numprocesses()}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return str(msg.get("numprocesses"))
        return self.console_error(msg)

########NEW FILE########
__FILENAME__ = numwatchers
from circus.commands.base import Command
from circus.exc import ArgumentError


class NumWatchers(Command):
    """\
        Get the number of watchers
        ==========================

        Get the number of watchers in a arbiter

        ZMQ Message
        -----------

        ::

            {
                "command": "numwatchers",
            }

        The response return the number of watchers in the 'numwatchers`
        property::

            { "status": "ok", "numwatchers": <n>, "time", "timestamp" }


        Command line
        ------------

        ::

            $ circusctl numwatchers

    """
    name = "numwatchers"

    def message(self, *args, **opts):
        if len(args) > 0:
            raise ArgumentError("Invalid number of arguments")
        return self.make_message()

    def execute(self, arbiter, props):
        return {"numwatchers": arbiter.numwatchers()}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return str(msg.get("numwatchers"))
        return self.console_error(msg)

########NEW FILE########
__FILENAME__ = options
from circus.commands.base import Command
from circus.exc import ArgumentError
from circus.util import convert_opt


class Options(Command):
    """\
        Get the value of all options for a watcher
        ==========================================

        This command returns all option values for a given watcher.

        ZMQ Message
        -----------

        ::

            {
                "command": "options",
                "properties": {
                    "name": "nameofwatcher",
                }
            }

        A message contains 1 property:

        - name: name of watcher

        The response object has a property ``options`` which is a
        dictionary of option names and values.

        eg::

            {
                "status": "ok",
                "options": {
                    "graceful_timeout": 300,
                    "send_hup": True,
                    ...
                },
                time': 1332202594.754644
            }


        Command line
        ------------

        ::

            $ circusctl options <name>


        Options
        -------

        - <name>: name of the watcher

        Options Keys are:

        - numprocesses: integer, number of processes
        - warmup_delay: integer or number, delay to wait between process
          spawning in seconds
        - working_dir: string, directory where the process will be executed
        - uid: string or integer, user ID used to launch the process
        - gid: string or integer, group ID used to launch the process
        - send_hup: boolean, if TRU the signal HUP will be used on reload
        - shell: boolean, will run the command in the shell environment if
          true
        - cmd: string, The command line used to launch the process
        - env: object, define the environnement in which the process will be
          launch
        - retry_in: integer or number, time in seconds we wait before we retry
          to launch the process if the maximum number of attempts
          has been reach.
        - max_retry: integer, The maximum of retries loops
        - graceful_timeout: integer or number, time we wait before we
          definitely kill a process.
        - priority: used to sort watchers in the arbiter
        - singleton: if True, a singleton watcher.
        - max_age: time a process can live before being restarted
        - max_age_variance: variable additional time to live, avoids
          stampeding herd.
    """

    name = "options"
    properties = ['name']

    def message(self, *args, **opts):

        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        return self.make_message(name=args[0])

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props['name'])
        return {"options": dict(watcher.options())}

    def console_msg(self, msg):
        if msg['status'] == "ok":
            ret = []
            for k, v in msg.get('options', {}).items():
                ret.append("%s: %s" % (k, convert_opt(k, v)))
            return "\n".join(ret)
        return self.console_error(msg)

########NEW FILE########
__FILENAME__ = quit
from circus.commands.base import Command


class Quit(Command):
    """\
        Quit the arbiter immediately
        ============================

        When the arbiter receive this command, the arbiter exit.

        ZMQ Message
        -----------

        ::

            {
                "command": "quit",
                "waiting": False
            }

        The response return the status "ok".

        If ``waiting`` is False (default), the call will return immediately
        after calling ``stop_signal`` on each process.

        If ``waiting`` is True, the call will return only when the stop process
        is completely ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.


        Command line
        ------------

        ::

            $ circusctl quit [--waiting]

    """
    name = "quit"
    options = Command.waiting_options

    def message(self, *args, **opts):
        return self.make_message(**opts)

    def execute(self, arbiter, props):
        return arbiter.stop()

########NEW FILE########
__FILENAME__ = reload
from circus.commands.base import Command
from circus.exc import ArgumentError
from circus.util import TransformableFuture


class Reload(Command):
    """\
        Reload the arbiter or a watcher
        ===============================

        This command reloads all the process in a watcher or all watchers. This
        will happen in one of 3 ways:

        * If graceful is false, a simple restart occurs.
        * If `send_hup` is true for the watcher, a HUP signal is sent to each
          process.
        * Otherwise:
            * If sequential is false, the arbiter will attempt to spawn
              `numprocesses` new processes. If the new processes are spawned
              successfully, the result is that all of the old processes are
              stopped, since by default the oldest processes are stopped when
              the actual number of processes for a watcher is greater than
              `numprocesses`.
            * If sequential is true, the arbiter will restart each process
              in a sequential way (with a `warmup_delay` pause between each
              step)


        ZMQ Message
        -----------

        ::

            {
                "command": "reload",
                "properties": {
                    "name": '<name>",
                    "graceful": true,
                    "sequential": false,
                    "waiting": False
                }
            }

        The response return the status "ok". If the property graceful is
        set to true the processes will be exited gracefully.

        If the property name is present, then the reload will be applied
        to the watcher.


        Command line
        ------------

        ::

            $ circusctl reload [<name>] [--terminate] [--waiting]
                                        [--sequential]

        Options
        +++++++

        - <name>: name of the watcher
        - --terminate; quit the node immediately

    """
    name = "reload"
    options = (Command.options + Command.waiting_options +
               [('', 'sequential', False, "sequential reload")] +
               [('', 'terminate', False, "stop immediately")])

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        graceful = not opts.get("terminate", False)
        waiting = opts.get("waiting", False)
        sequential = opts.get("sequential", False)
        if len(args) == 1:
            return self.make_message(name=args[0], graceful=graceful,
                                     waiting=waiting, sequential=sequential)
        else:
            return self.make_message(graceful=graceful, waiting=waiting,
                                     sequential=sequential)

    def execute(self, arbiter, props):
        graceful = props.get('graceful', True)
        sequential = props.get('sequential', False)
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            if props.get('waiting'):
                resp = TransformableFuture()
                resp.set_upstream_future(watcher.reload(
                    graceful=graceful,
                    sequential=sequential))
                resp.set_transform_function(lambda x: {"info": x})
                return resp
            return watcher.reload(graceful=graceful,
                                  sequential=sequential)
        else:
            return arbiter.reload(graceful=graceful, sequential=sequential)

########NEW FILE########
__FILENAME__ = reloadconfig
from circus.commands.base import Command


class ReloadConfig(Command):
    """\
        Reload the configuration file
        =============================

        This command reloads the configuration file, so changes in the
        configuration file will be reflected in the configuration of
        circus.


        ZMQ Message
        -----------

        ::

            {
                "command": "reloadconfig",
                "waiting": False
            }

        The response return the status "ok". If the property graceful is
        set to true the processes will be exited gracefully.


        Command line
        ------------

        ::

            $ circusctl reloadconfig [--waiting]

    """
    name = "reloadconfig"
    options = Command.waiting_options

    def message(self, *args, **opts):
        return self.make_message(**opts)

    def execute(self, arbiter, props):
        return arbiter.reload_from_config()

########NEW FILE########
__FILENAME__ = restart
from circus.commands.base import Command
from circus.exc import ArgumentError
from circus.util import TransformableFuture


class Restart(Command):
    """\
        Restart the arbiter or a watcher
        ================================

        This command restart all the process in a watcher or all watchers. This
        funtion simply stop a watcher then restart it.

        ZMQ Message
        -----------

        ::

            {
                "command": "restart",
                "properties": {
                    "name": "<name>",
                    "waiting": False
                }
            }

        The response return the status "ok".

        If the property name is present, then the reload will be applied
        to the watcher.

        If ``waiting`` is False (default), the call will return immediately
        after calling `stop_signal` on each process.

        If ``waiting`` is True, the call will return only when the restart
        process is completely ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.


        Command line
        ------------

        ::

            $ circusctl restart [<name>] [--waiting]

        Options
        +++++++

        - <name>: name of the watcher
    """

    name = "restart"
    options = Command.waiting_options

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("Invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0], **opts)

        return self.make_message(**opts)

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            if props.get('waiting'):
                resp = TransformableFuture()
                resp.set_upstream_future(watcher.restart())
                resp.set_transform_function(lambda x: {"info": x})
                return resp
            return watcher.restart()
        else:
            return arbiter.restart(inside_circusd=True)

########NEW FILE########
__FILENAME__ = rmwatcher
from circus.commands.base import Command
from circus.exc import ArgumentError


class RmWatcher(Command):
    """\
        Remove a watcher
        ================

        This command remove a watcher dynamically from the arbiter. The
        watchers are gracefully stopped.

        ZMQ Message
        -----------

        ::

            {
                "command": "rm",
                "properties": {
                    "name": "<nameofwatcher>",
                    "waiting": False
                }
            }

        The response return a status "ok".

        If ``waiting`` is False (default), the call will return immediatly
        after starting to remove and stop the corresponding watcher.

        If ``waiting`` is True, the call will return only when the remove and
        stop process is completly ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.

        Command line
        ------------

        ::

            $ circusctl rm <name> [--waiting]

        Options
        +++++++

        - <name>: name of the watcher to remove

    """

    name = "rm"
    properties = ['name']
    options = Command.waiting_options

    def message(self, *args, **opts):
        if len(args) < 1 or len(args) > 1:
            raise ArgumentError("Invalid number of arguments")

        return self.make_message(name=args[0])

    def execute(self, arbiter, props):
        self._get_watcher(arbiter, props['name'])
        return arbiter.rm_watcher(props['name'])

########NEW FILE########
__FILENAME__ = sendsignal
from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError
from circus.util import to_signum


class Signal(Command):
    """\
        Send a signal
        =============

        This command allows you to send a signal to all processes in a watcher,
        a specific process in a watcher or its children.

        ZMQ Message
        -----------

        To send a signal to all the processes for a watcher::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "signum": <signum>
            }

        To send a signal to a process::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "pid": <processid>,
                    "signum": <signum>
            }

        An optional property "children" can be used to send the signal
        to all the children rather than the process itself::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "pid": <processid>,
                    "signum": <signum>,
                    "children": True
            }

        To send a signal to a process child::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "pid": <processid>,
                    "signum": <signum>,
                    "child_pid": <childpid>,
            }

        It is also possible to send a signal to all the children of the
        watcher::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "signum": <signum>,
                    "children": True
            }

        Lastly, you can send a signal to the process *and* its children, with
        the *recursive* option::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "signum": <signum>,
                    "recursive": True
            }



        Command line
        ------------

        ::

            $ circusctl signal <name> [<pid>] [--children]
                    [--recursive] <signum>

        Options:
        ++++++++

        - <name>: the name of the watcher
        - <pid>: integer, the process id.
        - <signum>: the signal number (or name) to send.
        - <childpid>: the pid of a child, if any
        - <children>: boolean, send the signal to all the children
        - <recursive>: boolean, send the signal to the process and its children

    """

    name = "signal"
    options = [('', 'children', False, "Only signal children of the process"),
               ('', 'recursive', False, "Signal parent and children")]
    properties = ['name', 'signum']

    def message(self, *args, **opts):
        largs = len(args)
        if largs < 2 or largs > 3:
            raise ArgumentError("Invalid number of arguments")

        props = {
            'name': args[0],
            'children': opts.get("children", False),
            'recursive': opts.get("recursive", False),
            'signum': args[-1],
        }
        if len(args) == 3:
            props['pid'] = int(args[1])
        return self.make_message(**props)

    def execute(self, arbiter, props):
        name = props.get('name')
        watcher = self._get_watcher(arbiter, name)
        signum = props.get('signum')
        pids = [props['pid']] if 'pid' in props else watcher.get_active_pids()
        childpid = props.get('childpid', None)
        children = props.get('children', False)
        recursive = props.get('recursive', False)

        for pid in pids:
            if childpid:
                watcher.send_signal_child(pid, childpid, signum)
            elif children:
                watcher.send_signal_children(pid, signum)
            else:
                # send to the given pid
                watcher.send_signal(pid, signum)

                if recursive:
                    # also send to the children
                    watcher.send_signal_children(pid, signum)

    def validate(self, props):
        super(Signal, self).validate(props)

        if 'childpid' in props and 'pid' not in props:
            raise ArgumentError('cannot specify childpid without pid')

        try:
            props['signum'] = to_signum(props['signum'])
        except ValueError:
            raise MessageError('signal invalid')

########NEW FILE########
__FILENAME__ = set
from circus.commands.base import Command
from circus.commands.util import convert_option, validate_option
from circus.exc import ArgumentError, MessageError


class Set(Command):
    """\
        Set a watcher option
        ====================

        ZMQ Message
        -----------

        ::

            {
                "command": "set",
                "properties": {
                    "name": "nameofwatcher",
                    "options": {
                        "key1": "val1",
                        ..
                    }
                    "waiting": False
                }
            }


        The response return the status "ok". See the command Options for
        a list of key to set.

        Command line
        ------------

        ::

            $ circusctl set <name> <key1> <value1> <key2> <value2> --waiting


    """

    name = "set"
    properties = ['name', 'options']
    options = Command.waiting_options

    def message(self, *args, **opts):
        if len(args) < 3:
            raise ArgumentError("Invalid number of arguments")

        args = list(args)
        watcher_name = args.pop(0)
        if len(args) % 2 != 0:
            raise ArgumentError("List of key/values is invalid")

        options = {}
        while len(args) > 0:
            kv, args = args[:2], args[2:]
            kvl = kv[0].lower()
            options[kvl] = convert_option(kvl, kv[1])

        if opts.get('waiting', False):
            return self.make_message(name=watcher_name, waiting=True,
                                     options=options)
        else:
            return self.make_message(name=watcher_name, options=options)

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.pop('name'))
        action = 0
        for key, val in props.get('options', {}).items():
            if key == 'hooks':
                new_action = 0
                for name, _val in val.items():
                    action = watcher.set_opt('hooks.%s' % name, _val)
                    if action == 1:
                        new_action = 1
            else:
                new_action = watcher.set_opt(key, val)

            if new_action == 1:
                action = 1
        # trigger needed action
        return watcher.do_action(action)

    def validate(self, props):
        super(Set, self).validate(props)

        options = props['options']
        if not isinstance(options, dict):
            raise MessageError("'options' property should be an object")

        for key, val in options.items():
            validate_option(key, val)

########NEW FILE########
__FILENAME__ = start
from circus.commands.base import Command
from circus.exc import ArgumentError
from circus.util import TransformableFuture


class Start(Command):
    """\
        Start the arbiter or a watcher
        ==============================

        This command starts all the processes in a watcher or all watchers.


        ZMQ Message
        -----------

        ::

            {
                "command": "start",
                "properties": {
                    "name": '<name>",
                    "waiting": False
                }
            }

        The response return the status "ok".

        If the property name is present, the watcher will be started.

        If ``waiting`` is False (default), the call will return immediately
        after calling `start` on each process.

        If ``waiting`` is True, the call will return only when the start
        process is completely ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.

        Command line
        ------------

        ::

            $ circusctl start [<name>] --waiting

        Options
        +++++++

        - <name>: name of the watcher

    """
    name = "start"
    options = Command.waiting_options

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("Invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0], **opts)

        return self.make_message(**opts)

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            if props.get('waiting'):
                resp = TransformableFuture()
                resp.set_upstream_future(watcher.start())
                resp.set_transform_function(lambda x: {"info": x})
                return resp
            return watcher.start()
        else:
            return arbiter.start_watchers()

########NEW FILE########
__FILENAME__ = stats
from circus.exc import MessageError, ArgumentError
from circus.commands.base import Command

_INFOLINE = ("%(pid)s  %(cmdline)s %(username)s %(nice)s %(mem_info1)s "
             "%(mem_info2)s %(cpu)s %(mem)s %(ctime)s")


class Stats(Command):
    """\
       Get process infos
       =================

       You can get at any time some statistics about your processes
       with the stat command.

       ZMQ Message
       -----------

       To get stats for all watchers::

            {
                "command": "stats"
            }


       To get stats for a watcher::

            {
                "command": "stats",
                "properties": {
                    "name": <name>
                }
            }

       To get stats for a process::

            {
                "command": "stats",
                "properties": {
                    "name": <name>,
                    "process": <processid>
                }
            }

       Stats can be extended with the extended_stats hook but extended stats
       need to be requested::

            {
                "command": "stats",
                "properties": {
                    "name": <name>,
                    "process": <processid>,
                    "extended": True
                }
            }

       The response retun an object per process with the property "info"
       containing some process informations::

            {
              "info": {
                "children": [],
                "cmdline": "python",
                "cpu": 0.1,
                "ctime": "0:00.41",
                "mem": 0.1,
                "mem_info1": "3M",
                "mem_info2": "2G",
                "nice": 0,
                "pid": 47864,
                "username": "root"
              },
              "process": 5,
              "status": "ok",
              "time": 1332265655.897085
            }

       Command Line
       ------------

       ::

            $ circusctl stats [--extended] [<watchername>] [<processid>]

        """

    name = "stats"
    options = [('', 'extended', False,
                "Include info from extended_stats hook")]

    def message(self, *args, **opts):
        if len(args) > 2:
            raise ArgumentError("message invalid")

        extended = opts.get("extended", False)
        if len(args) == 2:
            return self.make_message(name=args[0], process=int(args[1]),
                                     extended=extended)
        elif len(args) == 1:
            return self.make_message(name=args[0], extended=extended)
        else:
            return self.make_message(extended=extended)

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            if 'process' in props:
                try:
                    return {
                        "process": props['process'],
                        "info": watcher.process_info(props['process'],
                                                     props.get('extended')),
                    }
                except KeyError:
                    raise MessageError("process %r not found in %r" % (
                        props['process'], props['name']))
            else:
                return {"name": props['name'],
                        "info": watcher.info(props.get('extended'))}
        else:
            infos = {}
            for watcher in arbiter.watchers:
                infos[watcher.name] = watcher.info()
            return {"infos": infos}

    def _to_str(self, info):
        if isinstance(info, dict):
            children = info.pop("children", [])
            ret = [_INFOLINE % info]
            for child in children:
                ret.append("   " + _INFOLINE % child)
            return "\n".join(ret)
        else:  # basestring, int, ..
            return info

    def console_msg(self, msg):
        if msg['status'] == "ok":
            if "name" in msg:
                ret = ["%s:" % msg.get('name')]
                for process, info in msg.get('info', {}).items():
                    ret.append("%s: %s" % (process, self._to_str(info)))
                return "\n".join(ret)
            elif 'infos' in msg:
                ret = []
                for watcher, watcher_info in msg.get('infos', {}).items():
                    ret.append("%s:" % watcher)
                    watcher_info = watcher_info or {}
                    for process, info in watcher_info.items():
                        ret.append("%s: %s" % (process, self._to_str(info)))

                return "\n".join(ret)
            else:
                return "%s: %s\n" % (msg['process'], self._to_str(msg['info']))
        else:
            return self.console_error(msg)

########NEW FILE########
__FILENAME__ = status
from circus.commands.base import Command
from circus.exc import ArgumentError


class Status(Command):
    """\
        Get the status of a watcher or all watchers
        ===========================================

        This command start get the status of a watcher or all watchers.

        ZMQ Message
        -----------

        ::

            {
                "command": "status",
                "properties": {
                    "name": '<name>",
                }
            }

        The response return the status "active" or "stopped" or the
        status / watchers.


        Command line
        ------------

        ::

            $ circusctl status [<name>]

        Options
        +++++++

        - <name>: name of the watcher

        Example
        +++++++

        ::

            $ circusctl status dummy
            active
            $ circusctl status
            dummy: active
            dummy2: active
            refuge: active

    """

    name = "status"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("message invalid")

        if len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            return {"status": watcher.status()}
        else:
            return {"statuses": arbiter.statuses()}

    def console_msg(self, msg):
        if "statuses" in msg:
            statuses = msg.get("statuses")
            watchers = sorted(statuses)
            return "\n".join(["%s: %s" % (watcher, statuses[watcher])
                              for watcher in watchers])
        elif "status" in msg and "status" != "error":
            return msg.get("status")
        return self.console_error(msg)

########NEW FILE########
__FILENAME__ = stop
from circus.commands.base import Command


class Stop(Command):
    """\
        Stop watchers
        =============

        This command stops a given watcher or all watchers.

        ZMQ Message
        -----------

        ::

            {
                "command": "stop",
                "properties": {
                    "name": "<name>",
                    "waiting": False
                }
            }

        The response returns the status "ok".

        If the ``name`` property is present, then the stop will be applied
        to the watcher corresponding to that name. Otherwise, all watchers
        will get stopped.

        If ``waiting`` is False (default), the call will return immediatly
        after calling `stop_signal` on each process.

        If ``waiting`` is True, the call will return only when the stop process
        is completly ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.


        Command line
        ------------

        ::

            $ circusctl stop [<name>] [--waiting]

        Options
        +++++++

        - <name>: name of the watcher
    """

    name = "stop"
    options = Command.waiting_options

    def message(self, *args, **opts):
        if len(args) >= 1:
            return self.make_message(name=args[0], **opts)
        return self.make_message(**opts)

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            return watcher.stop()
        else:
            return arbiter.stop_watchers()

########NEW FILE########
__FILENAME__ = util
from circus.exc import ArgumentError, MessageError
from circus.py3compat import string_types
from circus import util
import resource
import warnings


_HOOKS = ('before_start', 'after_start', 'before_stop', 'after_stop',
          'before_spawn', 'after_spawn', 'before_signal', 'after_signal',
          'extended_stats')


def convert_option(key, val):
    if key == "numprocesses":
        return int(val)
    elif key == "warmup_delay":
        return float(val)
    elif key == "working_dir":
        return val
    elif key == "uid":
        return val
    elif key == "gid":
        return val
    elif key == "send_hup":
        return util.to_bool(val)
    elif key == "stop_signal":
        return util.to_signum(val)
    elif key == "stop_children":
        return util.to_bool(val)
    elif key == "shell":
        return util.to_bool(val)
    elif key == "copy_env":
        return util.to_bool(val)
    elif key == "env":
        return util.parse_env_dict(val)
    elif key == "cmd":
        return val
    elif key == "args":
        return val
    elif key == "retry_in":
        return float(val)
    elif key == "max_retry":
        return int(val)
    elif key == "graceful_timeout":
        return float(val)
    elif key == 'max_age':
        return int(val)
    elif key == 'max_age_variance':
        return int(val)
    elif key == 'respawn':
        return util.to_bool(val)
    elif key == "singleton":
        return util.to_bool(val)
    elif key.startswith('stderr_stream.') or key.startswith('stdout_stream.'):
        subkey = key.split('.', 1)[-1]
        if subkey in ('max_bytes', 'backup_count'):
            return int(val)
        return val
    elif key == 'hooks':
        res = {}
        for hook in val.split(','):
            if hook == '':
                continue
            hook = hook.split(':')
            if len(hook) != 2:
                raise ArgumentError(hook)

            name, value = hook
            if name not in _HOOKS:
                raise ArgumentError(name)

            res[name] = value

        return res
    elif key.startswith('hooks.'):
        # we can also set a single hook
        name = key.split('.', 1)[-1]
        if name not in _HOOKS:
            raise ArgumentError(name)
        return val
    elif key.startswith('rlimit_'):
        return int(val)

    raise ArgumentError("unknown key %r" % key)


def validate_option(key, val):
    valid_keys = ('numprocesses', 'warmup_delay', 'working_dir', 'uid',
                  'gid', 'send_hup', 'stop_signal', 'stop_children',
                  'shell', 'env', 'cmd', 'args', 'copy_env', 'retry_in',
                  'max_retry', 'graceful_timeout', 'stdout_stream',
                  'stderr_stream', 'max_age', 'max_age_variance', 'respawn',
                  'singleton', 'hooks')

    valid_prefixes = ('stdout_stream.', 'stderr_stream.', 'hooks.', 'rlimit_')

    def _valid_prefix():
        for prefix in valid_prefixes:
            if key.startswith('%s' % prefix):
                return True
        return False

    if key not in valid_keys and not _valid_prefix():
        raise MessageError('unknown key %r' % key)

    if key in ('numprocesses', 'max_retry', 'max_age', 'max_age_variance',
               'stop_signal'):
        if not isinstance(val, int):
            raise MessageError("%r isn't an integer" % key)

    elif key in ('warmup_delay', 'retry_in', 'graceful_timeout',):
        if not isinstance(val, (int, float)):
            raise MessageError("%r isn't a number" % key)

    elif key in ('uid', 'gid',):
        if not isinstance(val, int) and not isinstance(val, string_types):
            raise MessageError("%r isn't an integer or string" % key)

    elif key in ('send_hup', 'shell', 'copy_env', 'respawn', 'stop_children'):
        if not isinstance(val, bool):
            raise MessageError("%r isn't a valid boolean" % key)

    elif key in ('env', ):
        if not isinstance(val, dict):
            raise MessageError("%r isn't a valid object" % key)

        for k, v in val.items():
            if not isinstance(v, string_types):
                raise MessageError("%r isn't a string" % k)

    elif key == 'hooks':
        if not isinstance(val, dict):
            raise MessageError("%r isn't a valid hook dict" % val)

        for key in val:
            if key not in _HOOKS:
                raise MessageError("Unknown hook %r" % val)

    elif key in ('stderr_stream', 'stdout_stream'):
        if not isinstance(val, dict):
            raise MessageError("%r isn't a valid object" % key)
        if 'class' not in val:
            raise MessageError("%r must have a 'class' key" % key)
        if 'refresh_time' in val:
            warnings.warn("'refresh_time' is deprecated and not useful "
                          "anymore for %r" % key)

    elif key.startswith('rlimit_'):
        rlimit_key = key[7:]
        rlimit_int = getattr(resource, 'RLIMIT_' + rlimit_key.upper(), None)
        if rlimit_int is None:
            raise MessageError("%r isn't a valid rlimit setting" % key)
        if not isinstance(val, int):
            raise MessageError("%r rlimit value isn't a valid int" % val)

########NEW FILE########
__FILENAME__ = config
import glob
import os
import signal
import warnings
from fnmatch import fnmatch

from circus import logger
from circus.py3compat import sort_by_field
from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB,
                         DEFAULT_ENDPOINT_MULTICAST, DEFAULT_ENDPOINT_STATS,
                         StrictConfigParser, replace_gnu_args, to_signum,
                         to_bool)


def watcher_defaults():
    return {
        'name': '',
        'cmd': '',
        'args': '',
        'numprocesses': 1,
        'warmup_delay': 0,
        'executable': None,
        'working_dir': None,
        'shell': False,
        'uid': None,
        'gid': None,
        'send_hup': False,
        'stop_signal': signal.SIGTERM,
        'stop_children': False,
        'max_retry': 5,
        'graceful_timeout': 30,
        'rlimits': dict(),
        'stderr_stream': dict(),
        'stdout_stream': dict(),
        'priority': 0,
        'use_sockets': False,
        'singleton': False,
        'copy_env': False,
        'copy_path': False,
        'hooks': dict(),
        'respawn': True,
        'autostart': True}


class DefaultConfigParser(StrictConfigParser):

    def __init__(self, *args, **kw):
        StrictConfigParser.__init__(self, *args, **kw)
        self._env = dict(os.environ)

    def set_env(self, env):
        self._env = dict(env)

    def get(self, section, option):
        res = StrictConfigParser.get(self, section, option)
        return replace_gnu_args(res, env=self._env)

    def items(self, section, noreplace=False):
        items = StrictConfigParser.items(self, section)
        if noreplace:
            return items

        return [(key, replace_gnu_args(value, env=self._env))
                for key, value in items]

    def dget(self, section, option, default=None, type=str):
        if not self.has_option(section, option):
            return default

        value = self.get(section, option)

        if type is int:
            value = int(value)
        elif type is bool:
            value = to_bool(value)
        elif type is float:
            value = float(value)
        elif type is not str:
            raise NotImplementedError()

        return value


def read_config(config_path):
    cfg = DefaultConfigParser()
    with open(config_path) as f:
        if hasattr(cfg, 'read_file'):
            cfg.read_file(f)
        else:
            cfg.readfp(f)

    current_dir = os.path.dirname(config_path)

    # load included config files
    includes = []

    def _scan(filename, includes):
        if os.path.abspath(filename) != filename:
            filename = os.path.join(current_dir, filename)

        paths = glob.glob(filename)
        if paths == []:
            logger.warn('%r does not lead to any config. Make sure '
                        'include paths are relative to the main config '
                        'file' % filename)
        includes += paths

    for include_file in cfg.dget('circus', 'include', '').split():
        _scan(include_file, includes)

    for include_dir in cfg.dget('circus', 'include_dir', '').split():
        _scan(os.path.join(include_dir, '*.ini'), includes)

    logger.debug('Reading config files: %s' % includes)
    return cfg, [config_path] + cfg.read(includes)


def get_config(config_file):
    if not os.path.exists(config_file):
        raise IOError("the configuration file %r does not exist\n" %
                      config_file)

    cfg, cfg_files_read = read_config(config_file)
    dget = cfg.dget
    config = {}

    # reading the global environ first
    global_env = dict(os.environ.items())
    local_env = dict()

    # update environments with [env] section
    if 'env' in cfg.sections():
        local_env.update(dict(cfg.items('env')))
        global_env.update(local_env)

    # always set the cfg environment
    cfg.set_env(global_env)

    # main circus options
    config['check_delay'] = dget('circus', 'check_delay', 5., float)
    config['endpoint'] = dget('circus', 'endpoint', DEFAULT_ENDPOINT_DEALER)
    config['endpoint_owner'] = dget('circus', 'endpoint_owner', None, str)
    config['pubsub_endpoint'] = dget('circus', 'pubsub_endpoint',
                                     DEFAULT_ENDPOINT_SUB)
    config['multicast_endpoint'] = dget('circus', 'multicast_endpoint',
                                        DEFAULT_ENDPOINT_MULTICAST)
    config['stats_endpoint'] = dget('circus', 'stats_endpoint', None)
    config['statsd'] = dget('circus', 'statsd', False, bool)
    config['umask'] = dget('circus', 'umask', None)
    if config['umask']:
        config['umask'] = int(config['umask'], 8)

    if config['stats_endpoint'] is None:
        config['stats_endpoint'] = DEFAULT_ENDPOINT_STATS
    elif not config['statsd']:
        warnings.warn("You defined a stats_endpoint without "
                      "setting up statsd to True.",
                      DeprecationWarning)
        config['statsd'] = True

    config['warmup_delay'] = dget('circus', 'warmup_delay', 0, int)
    config['httpd'] = dget('circus', 'httpd', False, bool)
    config['httpd_host'] = dget('circus', 'httpd_host', 'localhost', str)
    config['httpd_port'] = dget('circus', 'httpd_port', 8080, int)
    config['debug'] = dget('circus', 'debug', False, bool)
    config['debug_gc'] = dget('circus', 'debug_gc', False, bool)
    config['pidfile'] = dget('circus', 'pidfile')
    config['loglevel'] = dget('circus', 'loglevel')
    config['logoutput'] = dget('circus', 'logoutput')
    config['loggerconfig'] = dget('circus', 'loggerconfig', None)
    config['fqdn_prefix'] = dget('circus', 'fqdn_prefix', None, str)

    # Initialize watchers, plugins & sockets to manage
    watchers = []
    plugins = []
    sockets = []

    for section in cfg.sections():
        if section.startswith("socket:"):
            sock = dict(cfg.items(section))
            sock['name'] = section.split("socket:")[-1].lower()
            sock['so_reuseport'] = dget(section, "so_reuseport", False, bool)
            sock['replace'] = dget(section, "replace", False, bool)
            sockets.append(sock)

        if section.startswith("plugin:"):
            plugin = dict(cfg.items(section))
            plugin['name'] = section
            if 'priority' in plugin:
                plugin['priority'] = int(plugin['priority'])
            plugins.append(plugin)

        if section.startswith("watcher:"):
            watcher = watcher_defaults()
            watcher['name'] = section.split("watcher:", 1)[1]

            # create watcher options
            for opt, val in cfg.items(section, noreplace=True):
                if opt in ('cmd', 'args', 'working_dir', 'uid', 'gid'):
                    watcher[opt] = val
                elif opt == 'numprocesses':
                    watcher['numprocesses'] = dget(section, 'numprocesses', 1,
                                                   int)
                elif opt == 'warmup_delay':
                    watcher['warmup_delay'] = dget(section, 'warmup_delay', 0,
                                                   int)
                elif opt == 'executable':
                    watcher['executable'] = dget(section, 'executable', None,
                                                 str)
                # default bool to False
                elif opt in ('shell', 'send_hup', 'stop_children',
                             'close_child_stderr', 'use_sockets', 'singleton',
                             'copy_env', 'copy_path', 'close_child_stdout'):
                    watcher[opt] = dget(section, opt, False, bool)
                elif opt == 'stop_signal':
                    watcher['stop_signal'] = to_signum(val)
                elif opt == 'max_retry':
                    watcher['max_retry'] = dget(section, "max_retry", 5, int)
                elif opt == 'graceful_timeout':
                    watcher['graceful_timeout'] = dget(
                        section, "graceful_timeout", 30, int)
                elif opt.startswith('stderr_stream') or \
                        opt.startswith('stdout_stream'):
                    stream_name, stream_opt = opt.split(".", 1)
                    watcher[stream_name][stream_opt] = val
                elif opt.startswith('rlimit_'):
                    limit = opt[7:]
                    watcher['rlimits'][limit] = int(val)
                elif opt == 'priority':
                    watcher['priority'] = dget(section, "priority", 0, int)
                elif opt.startswith('hooks.'):
                    hook_name = opt[len('hooks.'):]
                    val = [elmt.strip() for elmt in val.split(',', 1)]
                    if len(val) == 1:
                        val.append(False)
                    else:
                        val[1] = to_bool(val[1])

                    watcher['hooks'][hook_name] = val
                # default bool to True
                elif opt in ('check_flapping', 'respawn', 'autostart'):
                    watcher[opt] = dget(section, opt, True, bool)
                else:
                    # freeform
                    watcher[opt] = val

            if watcher['copy_env']:
                watcher['env'] = dict(global_env)
            else:
                watcher['env'] = dict(local_env)

            watchers.append(watcher)

    # making sure we return consistent lists
    sort_by_field(watchers)
    sort_by_field(plugins)
    sort_by_field(sockets)

    # Second pass to make sure env sections apply to all watchers.

    def _extend(target, source):
        for name, value in source:
            if name in target:
                continue
            target[name] = value

    def _expand_vars(target, key, env):
        if isinstance(target[key], str):
            target[key] = replace_gnu_args(target[key], env=env)
        elif isinstance(target[key], dict):
            for k in target[key].keys():
                _expand_vars(target[key], k, env)

    def _expand_section(section, env, exclude=None):
        if exclude is None:
            exclude = ('name', 'env')

        for option in section.keys():
            if option in exclude:
                continue
            _expand_vars(section, option, env)

    # build environment for watcher sections
    for section in cfg.sections():
        if section.startswith('env:'):
            section_elements = section.split("env:", 1)[1]
            watcher_patterns = [s.strip() for s in section_elements.split(',')]
            env_items = dict(cfg.items(section, noreplace=True))

            for pattern in watcher_patterns:
                match = [w for w in watchers if fnmatch(w['name'], pattern)]

                for watcher in match:
                    watcher['env'].update(env_items)

    # expand environment for watcher sections
    for watcher in watchers:
        env = dict(global_env)
        env.update(watcher['env'])
        _expand_section(watcher, env)

    config['watchers'] = watchers
    config['plugins'] = plugins
    config['sockets'] = sockets
    return config

########NEW FILE########
__FILENAME__ = consumer
import errno
import zmq

from circus.util import DEFAULT_ENDPOINT_SUB, get_connection
from circus.py3compat import b


class CircusConsumer(object):
    def __init__(self, topics, context=None, endpoint=DEFAULT_ENDPOINT_SUB,
                 ssh_server=None, timeout=1.):
        self.topics = topics
        self.keep_context = context is not None
        self._init_context(context)
        self.endpoint = endpoint
        self.pubsub_socket = self.context.socket(zmq.SUB)
        get_connection(self.pubsub_socket, self.endpoint, ssh_server)
        for topic in self.topics:
            self.pubsub_socket.setsockopt(zmq.SUBSCRIBE, b(topic))
        self._init_poller()
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """ On context manager exit, destroy the zmq context """
        self.stop()

    def __iter__(self):
        return self.iter_messages()

    def _init_context(self, context):
        self.context = context or zmq.Context()

    def _init_poller(self):
        self.poller = zmq.Poller()
        self.poller.register(self.pubsub_socket, zmq.POLLIN)

    def iter_messages(self):
        """ Yields tuples of (topic, message) """
        with self:
            while True:
                try:
                    events = dict(self.poller.poll(self.timeout * 1000))
                except zmq.ZMQError as e:
                    if e.errno == errno.EINTR:
                        continue
                    raise

                if len(events) == 0:
                    continue

                topic, message = self.pubsub_socket.recv_multipart()
                yield topic, message

    def stop(self):
        if self.keep_context:
            return
        try:
            self.context.destroy(0)
        except zmq.ZMQError as e:
            if e.errno == errno.EINTR:
                pass
            else:
                raise

########NEW FILE########
__FILENAME__ = controller
import os
import sys
import traceback
import functools
try:
    from queue import Queue, Empty
    from urllib.parse import urlparse
except ImportError:
    from Queue import Queue, Empty  # NOQA
    from urlparse import urlparse  # NOQA


import zmq
import zmq.utils.jsonapi as json
from zmq.eventloop import ioloop, zmqstream
from tornado.concurrent import Future

from circus.util import create_udp_socket
from circus.util import check_future_exception_and_log
from circus.util import to_uid
from circus.commands import get_commands, ok, error, errors
from circus import logger
from circus.exc import MessageError, ConflictError
from circus.py3compat import string_types
from circus.sighandler import SysHandler


class Controller(object):

    def __init__(self, endpoint, multicast_endpoint, context, loop, arbiter,
                 check_delay=1.0, endpoint_owner=None):
        self.arbiter = arbiter
        self.caller = None
        self.endpoint = endpoint
        self.multicast_endpoint = multicast_endpoint
        self.context = context
        self.loop = loop
        self.check_delay = check_delay * 1000
        self.endpoint_owner = endpoint_owner
        self.started = False
        self._managing_watchers_future = None

        # initialize the sys handler
        self._init_syshandler()

        # get registered commands
        self.commands = get_commands()

    def _init_syshandler(self):
        self.sys_hdl = SysHandler(self)

    def _init_stream(self):
        self.stream = zmqstream.ZMQStream(self.ctrl_socket, self.loop)
        self.stream.on_recv(self.handle_message)

    def _init_multicast_endpoint(self):
        multicast_addr, multicast_port = urlparse(self.multicast_endpoint)\
            .netloc.split(':')
        try:
            self.udp_socket = create_udp_socket(multicast_addr,
                                                multicast_port)
            self.loop.add_handler(self.udp_socket.fileno(),
                                  self.handle_autodiscover_message,
                                  ioloop.IOLoop.READ)
        except (IOError, OSError, ValueError):
            message = ("Multicast discovery is disabled, there was an"
                       "error during udp socket creation.")
            logger.warning(message, exc_info=True)

    @property
    def endpoint_owner_mode(self):
        return self.endpoint_owner is not None and \
            self.endpoint.startswith('ipc://')

    def initialize(self):
        # initialize controller

        # Initialize ZMQ Sockets
        self.ctrl_socket = self.context.socket(zmq.ROUTER)
        self.ctrl_socket.bind(self.endpoint)
        self.ctrl_socket.linger = 0

        # support chown'ing the zmq endpoint on unix platforms
        if self.endpoint_owner_mode:
            uid = to_uid(self.endpoint_owner)
            sockpath = self.endpoint[6:]  # length of 'ipc://' prefix
            os.chown(sockpath, uid, -1)

        self._init_stream()

        # Initialize UDP Socket
        if self.multicast_endpoint:
            self._init_multicast_endpoint()

    def manage_watchers(self):
        if self._managing_watchers_future is not None:
            logger.debug("manage_watchers is already running...")
            return
        try:
            self._managing_watchers_future = self.arbiter.manage_watchers()
            self.loop.add_future(self._managing_watchers_future,
                                 self._manage_watchers_cb)
        except ConflictError:
            logger.debug("manage_watchers is conflicting with another command")

    def _manage_watchers_cb(self, future):
        self._managing_watchers_future = None

    def start(self):
        self.initialize()
        if self.check_delay > 0:
            # The specific case (check_delay < 0)
            # so with no period callback to manage_watchers
            # is probably "unit tests only"
            self.caller = ioloop.PeriodicCallback(self.manage_watchers,
                                                  self.check_delay, self.loop)
            self.caller.start()
        self.started = True

    def stop(self):
        if self.started:
            if self.caller is not None:
                self.caller.stop()
            try:
                self.stream.flush()
                self.stream.close()
            except (IOError, zmq.ZMQError):
                pass
            self.ctrl_socket.close()
        self.sys_hdl.stop()

    def handle_message(self, raw_msg):
        cid, msg = raw_msg
        msg = msg.strip()

        if not msg:
            self.send_response(None, cid, msg, "error: empty command")
        else:
            logger.debug("got message %s", msg)
            self.dispatch((cid, msg))

    def handle_autodiscover_message(self, fd_no, type):
        __, address = self.udp_socket.recvfrom(1024)
        self.udp_socket.sendto(json.dumps({'endpoint': self.endpoint}),
                               address)

    def _dispatch_callback_future(self, msg, cid, mid, cast, cmd_name,
                                  send_resp, future):
        exception = check_future_exception_and_log(future)
        if exception is not None:
            if send_resp:
                self.send_error(mid, cid, msg, "server error", cast=cast,
                                errno=errors.BAD_MSG_DATA_ERROR)
        else:
            resp = future.result()
            if send_resp:
                self._dispatch_callback(msg, cid, mid, cast, cmd_name, resp)

    def _dispatch_callback(self, msg, cid, mid, cast, cmd_name, resp=None):
        if resp is None:
            resp = ok()

        if not isinstance(resp, (dict, list)):
            msg = "msg %r tried to send a non-dict: %s" % (msg, str(resp))
            logger.error("msg %r tried to send a non-dict: %s", msg, str(resp))
            return self.send_error(mid, cid, msg, "server error", cast=cast,
                                   errno=errors.BAD_MSG_DATA_ERROR)

        if isinstance(resp, list):
            resp = {"results": resp}

        self.send_ok(mid, cid, msg, resp, cast=cast)

        if cmd_name.lower() == "quit":
            if cid is not None:
                self.stream.flush()

            self.arbiter.stop()

    def dispatch(self, job, future=None):
        cid, msg = job
        try:
            json_msg = json.loads(msg)
        except ValueError:
            return self.send_error(None, cid, msg, "json invalid",
                                   errno=errors.INVALID_JSON)

        mid = json_msg.get('id')
        cmd_name = json_msg.get('command')
        properties = json_msg.get('properties', {})
        cast = json_msg.get('msg_type') == "cast"

        try:
            cmd = self.commands[cmd_name.lower()]
        except KeyError:
            error_ = "unknown command: %r" % cmd_name
            return self.send_error(mid, cid, msg, error_, cast=cast,
                                   errno=errors.UNKNOWN_COMMAND)

        try:
            cmd.validate(properties)
            resp = cmd.execute(self.arbiter, properties)
            if isinstance(resp, Future):
                if properties.get('waiting', False):
                    cb = functools.partial(self._dispatch_callback_future, msg,
                                           cid, mid, cast, cmd_name, True)
                    resp.add_done_callback(cb)
                else:
                    cb = functools.partial(self._dispatch_callback_future, msg,
                                           cid, mid, cast, cmd_name, False)
                    resp.add_done_callback(cb)
                    self._dispatch_callback(msg, cid, mid, cast,
                                            cmd_name, None)
            else:
                self._dispatch_callback(msg, cid, mid, cast,
                                        cmd_name, resp)
        except MessageError as e:
            return self.send_error(mid, cid, msg, str(e), cast=cast,
                                   errno=errors.MESSAGE_ERROR)
        except ConflictError as e:
            if self._managing_watchers_future is not None:
                logger.debug("the command conflicts with running "
                             "manage_watchers, re-executing it at "
                             "the end")
                cb = functools.partial(self.dispatch, job)
                self.loop.add_future(self._managing_watchers_future, cb)
                return
            # conflicts between two commands, sending error...
            return self.send_error(mid, cid, msg, str(e), cast=cast,
                                   errno=errors.COMMAND_ERROR)
        except OSError as e:
            return self.send_error(mid, cid, msg, str(e), cast=cast,
                                   errno=errors.OS_ERROR)
        except:
            exctype, value = sys.exc_info()[:2]
            tb = traceback.format_exc()
            reason = "command %r: %s" % (msg, value)
            logger.debug("error: command %r: %s\n\n%s", msg, value, tb)
            return self.send_error(mid, cid, msg, reason, tb, cast=cast,
                                   errno=errors.COMMAND_ERROR)

    def send_error(self, mid, cid, msg, reason="unknown", tb=None, cast=False,
                   errno=errors.NOT_SPECIFIED):
        resp = error(reason=reason, tb=tb, errno=errno)
        self.send_response(mid, cid, msg, resp, cast=cast)

    def send_ok(self, mid, cid, msg, props=None, cast=False):
        resp = ok(props)
        self.send_response(mid, cid, msg, resp, cast=cast)

    def send_response(self, mid, cid, msg, resp, cast=False):
        if cast:
            return

        if cid is None:
            return

        if isinstance(resp, string_types):
            raise DeprecationWarning('Takes only a mapping')

        resp['id'] = mid
        resp = json.dumps(resp)

        try:
            self.stream.send(cid, zmq.SNDMORE)
            self.stream.send(resp)
        except zmq.ZMQError as e:
            logger.debug("Received %r - Could not send back %r - %s", msg,
                         resp, str(e))

########NEW FILE########
__FILENAME__ = exc


class AlreadyExist(Exception):
    """Raised when a watcher exists """
    pass


class MessageError(Exception):
    """ error raised when a message is invalid """
    pass


class CallError(Exception):
    pass


class ArgumentError(Exception):
    """Exception raised when one argument or the number of
    arguments is invalid"""
    pass


class ConflictError(Exception):
    """Exception raised when one exclusive command is already running
    in background"""
    pass

########NEW FILE########
__FILENAME__ = fixed_threading
from . import _patch  # NOQA
from threading import Thread, RLock, Timer  # NOQA
try:
    from _thread import get_ident
except ImportError:
    from thread import get_ident  # NOQA

########NEW FILE########
__FILENAME__ = arbiter
from circus.arbiter import Arbiter as _Arbiter
from circus.green.controller import Controller

from zmq.green.eventloop import ioloop
from zmq.green import Context


class Arbiter(_Arbiter):
    def _init_context(self, context):
        self.context = context or Context.instance()
        self.loop = ioloop.IOLoop.instance()
        self.ctrl = Controller(self.endpoint, self.multicast_endpoint,
                               self.context, self.loop, self, self.check_delay)

########NEW FILE########
__FILENAME__ = client
from circus.client import CircusClient as _CircusClient

from zmq.green import Context, Poller, POLLIN


class CircusClient(_CircusClient):
    def _init_context(self, context):
        self.context = context or Context.instance()

    def _init_poller(self):
        self.poller = Poller()
        self.poller.register(self.socket, POLLIN)

########NEW FILE########
__FILENAME__ = consumer
from circus.consumer import CircusConsumer as _CircusConsumer

from zmq.green import Context, Poller, POLLIN


class CircusConsumer(_CircusConsumer):
    def _init_context(self, context):
        self.context = context or Context()

    def _init_poller(self):
        self.poller = Poller()
        self.poller.register(self.pubsub_socket, POLLIN)

########NEW FILE########
__FILENAME__ = controller
from circus.controller import Controller as _Controller
from circus.green.sighandler import SysHandler

from zmq.green.eventloop import ioloop, zmqstream


class Controller(_Controller):

    def _init_syshandler(self):
        self.sys_hdl = SysHandler(self)

    def _init_stream(self):
        self.stream = zmqstream.ZMQStream(self.ctrl_socket, self.loop)
        self.stream.on_recv(self.handle_message)

    def start(self):
        self.initialize()
        self.caller = ioloop.PeriodicCallback(self.arbiter.manage_watchers,
                                              self.check_delay, self.loop)
        self.caller.start()

########NEW FILE########
__FILENAME__ = sighandler
import gevent

from circus.sighandler import SysHandler as _SysHandler


class SysHandler(_SysHandler):

    def _register(self):
        for sig in self.SIGNALS:
            gevent.signal(sig, self.signal, sig)

########NEW FILE########
__FILENAME__ = pidfile
import errno
import os
import tempfile


class Pidfile(object):
    """
    Manage a PID file. If a specific name is provided
    it and '"%s.oldpid" % name' will be used. Otherwise
    we create a temp file using os.mkstemp.
    """

    def __init__(self, fname):
        self.fname = fname
        self.pid = None

    def create(self, pid):
        oldpid = self.validate()
        if oldpid:
            if oldpid == os.getpid():
                return
            raise RuntimeError("Already running on PID %s (or pid file '%s' "
                               "is stale)" % (os.getpid(), self.fname))

        self.pid = pid

        # Write pidfile
        fdir = os.path.dirname(self.fname)
        if fdir and not os.path.isdir(fdir):
            raise RuntimeError("%s doesn't exist. Can't create pidfile" % fdir)
        fd, fname = tempfile.mkstemp(dir=fdir)
        os.write(fd, "{0}\n".format(self.pid).encode('utf-8'))
        if self.fname:
            os.rename(fname, self.fname)
        else:
            self.fname = fname
        os.close(fd)

        # set permissions to -rw-r--r--
        os.chmod(self.fname, 420)

    def rename(self, path):
        self.unlink()
        self.fname = path
        self.create(self.pid)

    def unlink(self):
        """ delete pidfile"""
        try:
            with open(self.fname, "r") as f:
                pid1 = int(f.read() or 0)

            if pid1 == self.pid:
                os.unlink(self.fname)
        except:
            pass

    def validate(self):
        """ Validate pidfile and make it stale if needed"""
        if not self.fname:
            return
        try:
            with open(self.fname, "r") as f:
                wpid = int(f.read() or 0)

                if wpid <= 0:
                    return

                try:
                    os.kill(wpid, 0)
                    return wpid
                except OSError as e:
                    if e.args[0] == errno.ESRCH:
                        return
                    raise
        except IOError as e:
            if e.args[0] == errno.ENOENT:
                return
            raise

########NEW FILE########
__FILENAME__ = command_reloader
import os

from circus.plugins import CircusPlugin
from circus import logger
from zmq.eventloop import ioloop


class CommandReloader(CircusPlugin):

    name = 'command_reloader'

    def __init__(self, *args, **config):
        super(CommandReloader, self).__init__(*args, **config)
        self.name = config.get('name')
        self.loop_rate = int(self.config.get('loop_rate', 1))
        self.cmd_files = {}

    def is_modified(self, watcher, current_mtime, current_path):
        if watcher not in self.cmd_files:
            return False
        if current_mtime != self.cmd_files[watcher]['mtime']:
            return True
        if current_path != self.cmd_files[watcher]['path']:
            return True
        return False

    def look_after(self):
        list_ = self.call('list')
        watchers = [watcher for watcher in list_['watchers']
                    if not watcher.startswith('plugin:')]

        for watcher in list(self.cmd_files.keys()):
            if watcher not in watchers:
                del self.cmd_files[watcher]

        for watcher in watchers:
            watcher_info = self.call('get', name=watcher, keys=['cmd'])
            cmd = watcher_info['options']['cmd']
            cmd_path = os.path.realpath(cmd)
            cmd_mtime = os.stat(cmd_path).st_mtime
            if self.is_modified(watcher, cmd_mtime, cmd_path):
                logger.info('%s modified. Restarting.', cmd_path)
                self.call('restart', name=watcher)
            self.cmd_files[watcher] = {
                'path': cmd_path,
                'mtime': cmd_mtime,
            }

    def handle_init(self):
        self.period = ioloop.PeriodicCallback(self.look_after,
                                              self.loop_rate * 1000,
                                              self.loop)
        self.period.start()

    def handle_stop(self):
        self.period.stop()

    def handle_recv(self, data):
        pass

########NEW FILE########
__FILENAME__ = flapping
from circus.fixed_threading import Timer
import time

from circus import logger
from circus.plugins import CircusPlugin
from circus.util import to_bool


INFINITE_RETRY = -1


class Flapping(CircusPlugin):
    """ Plugin that controls the flapping and stops the watcher in case
        it happens too often.

    Plugin Options -- all of them can be overriden in the watcher options
    with a *flapping.* prefix:

    - **attempts** -- number of times a process can restart before we
      start to detect the flapping (default: 2)
    - **window** -- the time window in seconds to test for flapping.
      If the process restarts more than **times** times, we consider it a
      flapping process. (default: 1)
    - **retry_in**: time in seconds to wait until we try to start a process
      that has been flapping. (default: 7)
    - **max_retry**: the number of times we attempt to start a process, before
      we abandon and stop the whole watcher. (default: 5) Set to -1 to
      disable max_retry and retry indefinitely.
    - **active** -- define if the plugin is active or not (default: True).
      If the global flag is set to False, the plugin is not started.

    """
    name = 'flapping'

    def __init__(self, endpoint, pubsub_endpoint, check_delay, ssh_server,
                 **config):
        super(Flapping, self).__init__(endpoint, pubsub_endpoint,
                                       check_delay, ssh_server=ssh_server,
                                       **config)
        self.timelines = {}
        self.timers = {}
        self.configs = {}
        self.tries = {}

        # default options
        self.attempts = int(config.get('attempts', 2))
        self.window = float(config.get('window', 1))
        self.retry_in = float(config.get('retry_in', 7))
        self.max_retry = int(config.get('max_retry', 5))

    def handle_stop(self):
        for timer in list(self.timers.values()):
            timer.cancel()

    def handle_recv(self, data):
        watcher_name, action, msg = self.split_data(data)
        if action == "reap":
            timeline = self.timelines.get(watcher_name, [])
            timeline.append(time.time())
            self.timelines[watcher_name] = timeline

            self.check(watcher_name)
        elif action == "updated":
            self.update_conf(watcher_name)

    def update_conf(self, watcher_name):
        msg = self.call("options", name=watcher_name)
        conf = self.configs.get(watcher_name, {})
        for key, value in msg.get('options', {}).items():
            key = key.split('.')
            if key[0] != self.name:
                continue
            key = '.'.join(key[1:])
            if key in ('attempts', 'max_retry'):
                value = int(value)
            elif key in ('window', 'retry_in'):
                value = float(value)

            conf[key] = value

        self.configs[watcher_name] = conf
        return conf

    def reset(self, watcher_name):
        self.timelines[watcher_name] = []
        self.tries[watcher_name] = 0
        if watcher_name is self.timers:
            timer = self.timers.pop(watcher_name)
            timer.cancel()

    def _get_conf(self, conf, name):
        return conf.get(name, getattr(self, name))

    def check(self, watcher_name):
        timeline = self.timelines[watcher_name]
        if watcher_name in self.configs:
            conf = self.configs[watcher_name]
        else:
            conf = self.update_conf(watcher_name)

        # if the watcher is not activated, we skip it
        if not to_bool(self._get_conf(conf, 'active')):
            # nothing to do here
            return

        tries = self.tries.get(watcher_name, 0)

        if len(timeline) == self._get_conf(conf, 'attempts'):
            duration = timeline[-1] - timeline[0] - self.check_delay

            if duration <= self._get_conf(conf, 'window'):
                max_retry = self._get_conf(conf, 'max_retry')
                if tries < max_retry or max_retry == INFINITE_RETRY:
                    next_tries = tries + 1
                    logger.info("%s: flapping detected: retry in %2ds "
                                "(attempt number %s)", watcher_name,
                                self._get_conf(conf, 'retry_in'), next_tries)

                    self.cast("stop", name=watcher_name)
                    self.timelines[watcher_name] = []
                    self.tries[watcher_name] = next_tries

                    def _start():
                        self.cast("start", name=watcher_name)

                    timer = Timer(self._get_conf(conf, 'retry_in'), _start)
                    timer.start()
                    self.timers[watcher_name] = timer
                else:
                    logger.info(
                        "%s: flapping detected: reached max retry limit",
                        watcher_name)
                    self.timelines[watcher_name] = []
                    self.tries[watcher_name] = 0
                    self.cast("stop", name=watcher_name)
            else:
                self.timelines[watcher_name] = []
                self.tries[watcher_name] = 0

########NEW FILE########
__FILENAME__ = http_observer

from circus.plugins.statsd import BaseObserver
try:
    from tornado.httpclient import AsyncHTTPClient
except ImportError:
    raise ImportError("This plugin requires tornado-framework to run.")


class HttpObserver(BaseObserver):

    name = 'http_observer'
    default_app_name = "http_observer"

    def __init__(self, *args, **config):
        super(HttpObserver, self).__init__(*args, **config)
        self.http_client = AsyncHTTPClient(io_loop=self.loop)
        self.check_url = config.get("check_url", "http://localhost/")
        self.timeout = float(config.get("timeout", 10))

        self.restart_on_error = config.get("restart_on_error", None)

    def look_after(self):

        def handle_response(response, *args, **kwargs):
            if response.error:
                self.statsd.increment("http_stats.error")
                self.statsd.increment("http_stats.error.%s" % response.code)
                if self.restart_on_error:
                    self.cast("restart", name=self.restart_on_error)
                    self.statsd.increment("http_stats.restart_on_error")
                return

            self.statsd.timed("http_stats.request_time",
                              int(response.request_time * 1000))

        self.http_client.fetch(self.check_url, handle_response,
                               request_timeout=self.timeout)

########NEW FILE########
__FILENAME__ = redis_observer

from circus.plugins.statsd import BaseObserver

try:
    import redis
except ImportError:
    raise ImportError("This plugin requires the redis-lib to run.")


class RedisObserver(BaseObserver):

    name = 'redis_observer'
    default_app_name = "redis_observer"

    OBSERVE = ['pubsub_channels', 'connected_slaves', 'lru_clock',
               'connected_clients', 'keyspace_misses', 'used_memory',
               'used_memory_peak', 'total_commands_processed',
               'used_memory_rss', 'total_connections_received',
               'pubsub_patterns', 'used_cpu_sys', 'used_cpu_sys_children',
               'blocked_clients', 'used_cpu_user', 'client_biggest_input_buf',
               'mem_fragmentation_ratio', 'expired_keys', 'evicted_keys',
               'client_longest_output_list', 'uptime_in_seconds',
               'keyspace_hits']

    def __init__(self, *args, **config):
        super(RedisObserver, self).__init__(*args, **config)
        self.redis = redis.from_url(config.get("redis_url",
                                    "redis://localhost:6379/0"),
                                    float(config.get("timeout", 5)))

        self.restart_on_timeout = config.get("restart_on_timeout", None)

    def look_after(self):
        try:
            info = self.redis.info()
        except redis.ConnectionError:
            self.statsd.increment("redis_stats.error")
            if self.restart_on_timeout:
                self.cast("restart", name=self.restart_on_timeout)
                self.statsd.increment("redis_stats.restart_on_error")
            return

        for key in self.OBSERVE:
            self.statsd.gauge("redis_stats.%s" % key, info[key])

########NEW FILE########
__FILENAME__ = resource_watcher
import signal
import warnings
from circus.plugins.statsd import BaseObserver
from circus.util import to_bool
from circus.util import human2bytes


class ResourceWatcher(BaseObserver):

    def __init__(self, *args, **config):
        super(ResourceWatcher, self).__init__(*args, **config)
        self.watcher = config.get("watcher", None)
        self.service = config.get("service", None)
        if self.service is not None:
            warnings.warn("ResourceWatcher.service is deprecated "
                          "please use ResourceWatcher.watcher instead.",
                          category=DeprecationWarning)
            if self.watcher is None:
                self.watcher = self.service
        if self.watcher is None:
            self.statsd.stop()
            self.loop.close()
            raise NotImplementedError('watcher is mandatory for now.')

        self.max_cpu = float(config.get("max_cpu", 90))     # in %
        self.max_mem = config.get("max_mem")

        if self.max_mem is None:
            self.max_mem = 90.
            self._max_percent = True
        else:
            try:
                self.max_mem = float(self.max_mem)          # float -> %
                self._max_percent = True
            except ValueError:
                self.max_mem = human2bytes(self.max_mem)    # int -> absolute
                self._max_percent = False

        self.min_cpu = config.get("min_cpu")
        if self.min_cpu is not None:
            self.min_cpu = float(self.min_cpu)              # in %
        self.min_mem = config.get("min_mem")
        if self.min_mem is not None:
            try:
                self.min_mem = float(self.min_mem)          # float -> %
                self._min_percent = True
            except ValueError:
                self.min_mem = human2bytes(self.min_mem)    # int -> absolute
                self._min_percent = True
        self.health_threshold = float(config.get("health_threshold",
                                      75))  # in %
        self.max_count = int(config.get("max_count", 3))

        self.process_children = to_bool(config.get("process_children", '0'))
        self.child_signal = int(config.get("child_signal", signal.SIGTERM))

        self._count_over_cpu = {}
        self._count_over_mem = {}
        self._count_under_cpu = {}
        self._count_under_mem = {}
        self._count_health = {}

    def look_after(self):
        info = self.call("stats", name=self.watcher)

        if info["status"] == "error":
            self.statsd.increment("_resource_watcher.%s.error" % self.watcher)
            return

        stats = info['info']

        self._process_index('parent', self._collect_data(stats))
        if not self.process_children:
            return

        for sub_info in stats.values():
            if isinstance(sub_info, dict):
                for child_info in sub_info['children']:
                    data = self._collect_data({child_info['pid']: child_info})
                    self._process_index(child_info['pid'], data)

    def _collect_data(self, stats):
        data = {}
        cpus = []
        mems = []
        mems_abs = []

        for sub_info in stats.values():
            if isinstance(sub_info, dict):
                cpus.append(100 if sub_info['cpu'] == 'N/A' else
                            float(sub_info['cpu']))
                mems.append(100 if sub_info['mem'] == 'N/A' else
                            float(sub_info['mem']))
                mems_abs.append(0 if sub_info['mem_info1'] == 'N/A' else
                                human2bytes(sub_info['mem_info1']))

        if cpus:
            data['max_cpu'] = max(cpus)
            data['max_mem'] = max(mems)
            data['max_mem_abs'] = max(mems_abs)
            data['min_cpu'] = min(cpus)
            data['min_mem'] = min(mems)
            data['min_mem_abs'] = min(mems_abs)
        else:
            # we dont' have any process running. max = 0 then
            data['max_cpu'] = 0
            data['max_mem'] = 0
            data['min_cpu'] = 0
            data['min_mem'] = 0
            data['max_mem_abs'] = 0
            data['min_mem_abs'] = 0

        return data

    def _process_index(self, index, stats):

        if (index not in self._count_over_cpu or
                index not in self._count_over_mem or
                index not in self._count_under_cpu or
                index not in self._count_under_mem or
                index not in self._count_health):
            self._reset_index(index)

        if self.max_cpu and stats['max_cpu'] > self.max_cpu:
            self.statsd.increment("_resource_watcher.%s.over_cpu" %
                                  self.watcher)
            self._count_over_cpu[index] += 1
        else:
            self._count_over_cpu[index] = 0

        if self.min_cpu is not None and stats['min_cpu'] <= self.min_cpu:
            self.statsd.increment("_resource_watcher.%s.under_cpu" %
                                  self.watcher)
            self._count_under_cpu[index] += 1
        else:
            self._count_under_cpu[index] = 0

        if self.max_mem is not None:
            over_percent = (self._max_percent and
                            stats['max_mem'] > self.max_mem)
            over_value = (not self._max_percent and
                          stats['max_mem_abs'] > self.max_mem)

            if over_percent or over_value:
                self.statsd.increment("_resource_watcher.%s.over_memory" %
                                      self.watcher)
                self._count_over_mem[index] += 1
            else:
                self._count_over_mem[index] = 0
        else:
            self._count_over_mem[index] = 0

        if self.min_mem is not None:
            under_percent = (self._min_percent and
                             stats['min_mem'] < self.min_mem)
            under_value = (not self._min_percent
                           and stats['min_mem_abs'] < self.min_mem)

            if under_percent or under_value:
                self.statsd.increment("_resource_watcher.%s.under_memory" %
                                      self.watcher)
                self._count_under_mem[index] += 1
            else:
                self._count_under_mem[index] = 0
        else:
            self._count_under_mem[index] = 0

        max_cpu = stats['max_cpu']
        max_mem = stats['max_mem']

        if (self.health_threshold and
                (max_cpu + max_mem) / 2.0 > self.health_threshold):
            self.statsd.increment("_resource_watcher.%s.over_health" %
                                  self.watcher)
            self._count_health[index] += 1
        else:
            self._count_health[index] = 0

        if max([self._count_over_cpu[index], self._count_under_cpu[index],
                self._count_over_mem[index], self._count_under_mem[index],
                self._count_health[index]]) > self.max_count:
            self.statsd.increment("_resource_watcher.%s.restarting" %
                                  self.watcher)

            # todo: restart only process instead of the whole watcher
            if index == 'parent':
                self.cast("restart", name=self.watcher)
                self._reset_index(index)
            else:
                self.cast(
                    "signal",
                    name=self.watcher,
                    signum=self.child_signal,
                    child_pid=index
                )
                self._remove_index(index)

            self._reset_index(index)

    def _reset_index(self, index):
        self._count_over_cpu[index] = 0
        self._count_over_mem[index] = 0
        self._count_under_cpu[index] = 0
        self._count_under_mem[index] = 0
        self._count_health[index] = 0

    def _remove_index(self, index):
        del self._count_over_cpu[index]
        del self._count_over_mem[index]
        del self._count_under_cpu[index]
        del self._count_under_mem[index]
        del self._count_health[index]

    def stop(self):
        self.statsd.stop()
        super(ResourceWatcher, self).stop()

########NEW FILE########
__FILENAME__ = statsd
import socket

from zmq.eventloop import ioloop

from circus.plugins import CircusPlugin
from circus.util import human2bytes


class StatsdClient(object):

    def __init__(self, host=None, port=None, prefix=None, sample_rate=1):
        self.host = host
        self.port = port
        self.prefix = prefix
        self.sample_rate = sample_rate
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, bucket, value, sample_rate=None):
        sample_rate = sample_rate or self.sample_rate
        if sample_rate != 1:
            value += "|@%s" % sample_rate

        if self.prefix:
            bucket = "%s.%s" % (self.prefix, bucket)

        self.socket.sendto("%s:%s" % (bucket, value), (self.host, self.port))

    def decrement(self, bucket, delta=1):
        if delta > 0:
            delta = - delta
        self.increment(bucket, delta)

    def increment(self, bucket, delta=1):
        self.send(bucket, "%d|c" % delta)

    def gauge(self, bucket, value):
        self.send(bucket, "%s|g" % value)

    def timed(self, bucket, value):
        self.send(bucket, "%s|ms" % value)

    def stop(self):
        self.socket.close()


class StatsdEmitter(CircusPlugin):
    """Plugin that sends stuff to statsd
    """
    name = 'statsd'
    default_app_name = "app"

    def __init__(self, endpoint, pubsub_endpoint, check_delay, ssh_server,
                 **config):
        super(StatsdEmitter, self).__init__(endpoint, pubsub_endpoint,
                                            check_delay, ssh_server=ssh_server)
        self.app = config.get('application_name', self.default_app_name)
        self.prefix = 'circus.%s.watcher' % self.app

        # initialize statsd
        self.statsd = StatsdClient(host=config.get('host', 'localhost'),
                                   port=int(config.get('port', '8125')),
                                   prefix=self.prefix,
                                   sample_rate=float(
                                       config.get('sample_rate', '1.0')))

    def handle_recv(self, data):
        watcher_name, action, msg = self.split_data(data)
        self.statsd.increment('%s.%s' % (watcher_name, action))

    def stop(self):
        self.statsd.stop()
        super(StatsdEmitter, self).stop()


class BaseObserver(StatsdEmitter):

    def __init__(self, *args, **config):
        super(BaseObserver, self).__init__(*args, **config)
        self.loop_rate = float(config.get("loop_rate", 60))  # in seconds

    def handle_init(self):
        self.period = ioloop.PeriodicCallback(self.look_after,
                                              self.loop_rate * 1000, self.loop)
        self.period.start()

    def handle_stop(self):
        self.period.stop()
        self.statsd.stop()

    def handle_recv(self, data):
        pass

    def look_after(self):
        raise NotImplementedError()


class FullStats(BaseObserver):

    name = 'full_stats'

    def look_after(self):
        info = self.call("stats")
        if info["status"] == "error":
            self.statsd.increment("_stats.error")
            return

        for name, stats in info['infos'].items():
            if name.startswith("plugin:"):
                # ignore plugins
                continue

            cpus = []
            mems = []
            mem_infos = []

            for sub_name, sub_info in stats.items():
                if isinstance(sub_info, dict):
                    cpus.append(sub_info['cpu'])
                    mems.append(sub_info['mem'])
                    mem_infos.append(human2bytes(sub_info['mem_info1']))
                elif sub_name == "spawn_count":
                    # spawn_count info is in the same level as processes
                    # dict infos, so if spawn_count is given, take it and
                    # continue
                    self.statsd.gauge("_stats.%s.spawn_count" % name,
                                      sub_info)

            self.statsd.gauge("_stats.%s.watchers_num" % name, len(cpus))

            if not cpus:
                # if there are only dead processes, we have an empty list
                # and we can't measure it
                continue

            self.statsd.gauge("_stats.%s.cpu_max" % name, max(cpus))
            self.statsd.gauge("_stats.%s.cpu_sum" % name, sum(cpus))
            self.statsd.gauge("_stats.%s.mem_pct_max" % name, max(mems))
            self.statsd.gauge("_stats.%s.mem_pct_sum" % name, sum(mems))
            self.statsd.gauge("_stats.%s.mem_max" % name, max(mem_infos))
            self.statsd.gauge("_stats.%s.mem_sum" % name, sum(mem_infos))

########NEW FILE########
__FILENAME__ = watchdog
import re
import socket
import time
import signal

from zmq.eventloop import ioloop
from circus.plugins import CircusPlugin
from circus import logger


class WatchDog(CircusPlugin):
    """Plugin that bind an udp socket and wait for watchdog messages.
    For "watchdoged" processes, the watchdog will kill them if they
    don't send heartbeat in a certain period of time materialized by
    loop_rate * max_count. (circus will automatically restart the missing
    processes in the watcher)

    Each monitored process should send udp message at least at the loop_rate.
    The udp message format is a line of text, decoded using **msg_regex**
    parameter.
    The heartbeat message MUST at least contain the pid of the process sending
    the message.

    The list of monitored watchers are determined by the parameter
    **watchers_regex** in the configuration.

    At startup, the plugin does not know all the circus watchers and pids,
    so it's needed to discover all watchers and pids. After the discover, the
    monitoring list is updated by messages from circusd handled in
    self.handle_recv

    Plugin Options --

    - **loop_rate** -- watchdog loop rate in seconds. At each loop, WatchDog
      will looks for "dead" processes.
    - **watchers_regex** -- regex for matching watcher names that should be
      monitored by the watchdog (default: ".*" all watchers are monitored)
    - **msg_regex** -- regex for decoding the received heartbeat
      message in udp (default: "^(?P<pid>.*);(?P<timestamp>.*)$")
      the default format is a simple text message: "pid;timestamp"
    - **max_count** -- max number of passed loop without receiving
      any heartbeat before restarting process (default: 3)
    - **ip** -- ip the watchdog will bind on (default: 127.0.0.1)
    - **port** -- port the watchdog will bind on (default: 1664)
    """
    name = 'watchdog'

    def __init__(self, endpoint, pubsub_endpoint, check_delay, ssh_server,
                 **config):
        super(WatchDog, self).__init__(endpoint, pubsub_endpoint,
                                       check_delay, ssh_server=ssh_server)

        self.loop_rate = float(config.get("loop_rate", 60))  # in seconds
        self.watchers_regex = config.get("watchers_regex", ".*")
        self.msg_regex = config.get("msg_regex",
                                    "^(?P<pid>.*);(?P<timestamp>.*)$")
        self.max_count = config.get("max_count", 3)
        self.watchdog_ip = config.get("ip", "127.0.0.1")
        self.watchdog_port = config.get("port", 1664)

        self.pid_status = dict()
        self.period = None
        self.starting = True

    def handle_init(self):
        """Initialization of plugin

        - set the periodic call back for the process monitoring (at loop_rate)
        - create the listening UDP socket
        """
        self.period = ioloop.PeriodicCallback(self.look_after,
                                              self.loop_rate * 1000,
                                              self.loop)
        self.period.start()
        self._bind_socket()

    def handle_stop(self):
        if self.period is not None:
            self.period.stop()
        self.sock.close()
        self.sock = None

    def handle_recv(self, data):
        """Handle received message from circusd

        We need to handle two messages:
        - spawn: add a new monitored child pid
        - reap: remove a killed child pid from monitoring
        """
        watcher_name, action, msg = self.split_data(data)
        logger.debug("received data from circusd: watcher.%s.%s, %s",
                     watcher_name, action, msg)
        # check if monitored watchers:
        if self._match_watcher_name(watcher_name):
            try:
                message = self.load_message(msg)
            except ValueError:
                logger.error("Error while decoding json for message: %s",
                             msg)
            else:
                if "process_pid" not in message:
                    logger.warning('no process_pid in message')
                    return
                pid = str(message.get("process_pid"))
                if action == "spawn":
                    self.pid_status[pid] = dict(watcher=watcher_name,
                                                last_activity=time.time())
                    logger.info("added new monitored pid for %s:%s",
                                watcher_name,
                                pid)
                # very questionable fix for Py3 here!
                # had to add check for pid in self.pid_status
                elif action == "reap" and pid in self.pid_status:
                    old_pid = self.pid_status.pop(pid)
                    logger.info("removed monitored pid for %s:%s",
                                old_pid['watcher'],
                                pid)

    def _discover_monitored_pids(self):
        """Try to discover all the monitored pids.

        This should be done only at startup time, because if new watchers or
        pids are created in running time, we should receive the message
        from circusd which is handled by self.handle_recv
        """
        self.pid_status = dict()
        all_watchers = self.call("list")
        for watcher_name in all_watchers['watchers']:
            if self._match_watcher_name(watcher_name):
                processes = self.call("list", name=watcher_name)
                if 'pids' in processes:
                    for pid in processes['pids']:
                        pid = str(pid)
                        self.pid_status[pid] = dict(watcher=watcher_name,
                                                    last_activity=time.time())
                        logger.info("discovered: %s, pid:%s",
                                    watcher_name,
                                    pid)

    def _bind_socket(self):
        """bind the listening socket for watchdog udp and start an event
        handler for handling udp received messages.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((self.watchdog_ip, self.watchdog_port))
        except socket.error as socket_error:
            logger.error(
                "Problem while binding watchdog socket on %s:%s (err %s",
                self.watchdog_ip,
                self.watchdog_port,
                str(socket_error))
            self.sock = None
        else:
            self.sock.settimeout(1)
            self.loop.add_handler(self.sock.fileno(),
                                  self.receive_udp_socket,
                                  ioloop.IOLoop.READ)
            logger.info("Watchdog listening UDP on %s:%s",
                        self.watchdog_ip, self.watchdog_port)

    def _match_watcher_name(self, name):
        """Match the given watcher name with the watcher_regex given in config

        :return: re.match object or None
        """
        return re.match(self.watchers_regex, name)

    def _decode_received_udp_message(self, data):
        """decode the received message according to the msg_regex

        :return: decoded message
        :rtype: dict or None
        """
        result = re.match(self.msg_regex, data)
        if result is not None:
            return result.groupdict()

    def receive_udp_socket(self, fd, events):
        """Check the socket for received UDP message.
        This method is periodically called by the ioloop.
        If messages are received and parsed, update the status of
        the corresponing pid.
        """
        data, _ = self.sock.recvfrom(1024)
        heartbeat = self._decode_received_udp_message(data)
        if "pid" in heartbeat:
            if heartbeat['pid'] in self.pid_status:
                # TODO: check and compare received time
                # with our own time.time()
                self.pid_status[heartbeat["pid"]][
                    'last_activity'] = time.time()
            else:
                logger.warning("received watchdog for a"
                               "non monitored process:%s",
                               heartbeat)
        logger.debug("watchdog message: %s", heartbeat)

    def look_after(self):
        """Checks for the watchdoged watchers and restart a process if no
        received watchdog after the loop_rate * max_count period.
        """
        # if first check, do a full discovery first.
        if self.starting:
            self._discover_monitored_pids()
            self.starting = False

        max_timeout = self.loop_rate * self.max_count
        too_old_time = time.time() - max_timeout
        for pid, detail in self.pid_status.items():
            if detail['last_activity'] < too_old_time:
                logger.info("watcher:%s, pid:%s is not responding. Kill it !",
                            detail['watcher'],
                            pid)
                self.cast("signal",
                          name=detail['watcher'],
                          pid=int(pid),
                          signum=signal.SIGKILL)

########NEW FILE########
__FILENAME__ = _statsd
# kept for backwards compatibility
from circus.plugins.statsd import StatsdEmitter   # NOQA

########NEW FILE########
__FILENAME__ = process
try:
    import ctypes
except MemoryError:
    # selinux execmem denial
    # https://bugzilla.redhat.com/show_bug.cgi?id=488396
    ctypes = None       # NOQA
except ImportError:
    # Python on Solaris compiled with Sun Studio doesn't have ctypes
    ctypes = None       # NOQA

import sys
import errno
import os
import resource
from subprocess import PIPE
import time
import shlex
import warnings

from psutil import Popen, STATUS_ZOMBIE, STATUS_DEAD, NoSuchProcess

from circus.py3compat import bytestring, string_types, quote
from circus.sockets import CircusSocket
from circus.util import (get_info, to_uid, to_gid, debuglog, get_working_dir,
                         ObjectDict, replace_gnu_args, is_win, get_default_gid,
                         get_username_from_uid)
from circus import logger


_INFOLINE = ("%(pid)s  %(cmdline)s %(username)s %(nice)s %(mem_info1)s "
             "%(mem_info2)s %(cpu)s %(mem)s %(ctime)s")


RUNNING = 0
DEAD_OR_ZOMBIE = 1
UNEXISTING = 2
OTHER = 3


# psutil < 2.x compat
def get_children(proc, recursive=False):
    try:
        return proc.children(recursive)
    except AttributeError:
        return proc.get_children(recursive)


def get_memory_info(proc):
    try:
        return proc.memory_info()
    except AttributeError:
        return proc.get_memory_info()


def get_cpu_percent(proc, **kw):
    try:
        return proc.cpu_percent(**kw)
    except AttributeError:
        return proc.get_cpu_percent(**kw)


def get_memory_percent(proc):
    try:
        return proc.memory_percent()
    except AttributeError:
        return proc.get_memory_percent()


def get_cpu_times(proc):
    try:
        return proc.cpu_times()
    except AttributeError:
        return proc.get_cpu_times()


def get_nice(proc):
    try:
        return proc.nice()
    except (AttributeError, TypeError):
        return proc.get_nice()


def get_cmdline(proc):
    try:
        return proc.cmdline()
    except TypeError:
        return proc.cmdline


def get_create_time(proc):
    try:
        return proc.create_time()
    except TypeError:
        return proc.create_time


def get_username(proc):
    try:
        return proc.username()
    except TypeError:
        return proc.username


def get_status(proc):
    try:
        return proc.status()
    except TypeError:
        return proc.status


class Process(object):
    """Wraps a process.

    Options:

    - **wid**: the process unique identifier. This value will be used to
      replace the *$WID* string in the command line if present.

    - **cmd**: the command to run. May contain any of the variables available
      that are being passed to this class. They will be replaced using the
      python format syntax.

    - **args**: the arguments for the command to run. Can be a list or
      a string. If **args** is  a string, it's splitted using
      :func:`shlex.split`. Defaults to None.

    - **executable**: When executable is given, the first item in
      the args sequence obtained from **cmd** is still treated by most
      programs as the command name, which can then be different from the
      actual executable name. It becomes the display name for the executing
      program in utilities such as **ps**.

    - **working_dir**: the working directory to run the command in. If
      not provided, will default to the current working directory.

    - **shell**: if *True*, will run the command in the shell
      environment. *False* by default. **warning: this is a
      security hazard**.

    - **uid**: if given, is the user id or name the command should run
      with. The current uid is the default.

    - **gid**: if given, is the group id or name the command should run
      with. The current gid is the default.

    - **env**: a mapping containing the environment variables the command
      will run with. Optional.

    - **rlimits**: a mapping containing rlimit names and values that will
      be set before the command runs.

    - **use_fds**: if True, will not close the fds in the subprocess.
      default: False.

    - **pipe_stdout**: if True, will open a PIPE on stdout. default: True.

    - **pipe_stderr**: if True, will open a PIPE on stderr. default: True.

    - **close_child_stdout**: If True, redirects the child process' stdout
      to /dev/null after the fork. default: False.

    - **close_child_stderr**: If True, redirects the child process' stdout
      to /dev/null after the fork. default: False.
    """
    def __init__(self, wid, cmd, args=None, working_dir=None, shell=False,
                 uid=None, gid=None, env=None, rlimits=None, executable=None,
                 use_fds=False, watcher=None, spawn=True,
                 pipe_stdout=True, pipe_stderr=True,
                 close_child_stdout=False, close_child_stderr=False):

        self.wid = wid
        self.cmd = cmd
        self.args = args
        self.working_dir = working_dir or get_working_dir()
        self.shell = shell
        if uid:
            self.uid = to_uid(uid)
            self.username = get_username_from_uid(self.uid)
        else:
            self.username = None
            self.uid = None
        self.gid = to_gid(gid) if gid else None
        self.env = env or {}
        self.rlimits = rlimits or {}
        self.executable = executable
        self.use_fds = use_fds
        self.watcher = watcher
        self.pipe_stdout = pipe_stdout
        self.pipe_stderr = pipe_stderr
        self.close_child_stdout = close_child_stdout
        self.close_child_stderr = close_child_stderr
        self.stopping = False
        # sockets created before fork, should be let go after.
        self._sockets = []

        if self.uid is not None and self.gid is None:
            self.gid = get_default_gid(self.uid)

        if spawn:
            self.spawn()

    def _null_streams(self, streams):
        devnull = os.open(os.devnull, os.O_RDWR)
        try:
            for stream in streams:
                if not hasattr(stream, 'fileno'):
                    # we're probably dealing with a file-like
                    continue
                try:
                    stream.flush()
                    os.dup2(devnull, stream.fileno())
                except IOError:
                    # some streams, like stdin - might be already closed.
                    pass
        finally:
            os.close(devnull)

    def _get_sockets_fds(self):
        """Returns sockets dict. If this worker's cmd indicates use of
        a SO_REUSEPORT socket, a new socket is created and bound. This
        new socket's FD replaces original socket's FD in returned dict.
        This method populates `self._sockets` list. This list should be
        let go after `fork()`.
        """
        sockets_fds = None

        if self.watcher is not None and self.watcher.sockets is not None:
            sockets_fds = self.watcher._get_sockets_fds()
            reuseport_sockets = tuple((sn, s) for (sn, s)
                                      in self.watcher.sockets.items()
                                      if s.so_reuseport)

            for sn, s in reuseport_sockets:
                # watcher.cmd uses this reuseport socket
                if 'circus.sockets.%s' % sn in self.watcher.cmd:
                    sock = CircusSocket.load_from_config(s._cfg)
                    sock.bind_and_listen()
                    # replace original socket's fd
                    sockets_fds[sn] = sock.fileno()
                    # keep new socket until fork returns
                    self._sockets.append(sock)

        return sockets_fds

    def spawn(self):
        sockets_fds = self._get_sockets_fds()

        args = self.format_args(sockets_fds=sockets_fds)

        def preexec_fn():
            streams = [sys.stdin]

            if self.close_child_stdout:
                streams.append(sys.stdout)

            if self.close_child_stderr:
                streams.append(sys.stderr)

            self._null_streams(streams)
            os.setsid()

            for limit, value in self.rlimits.items():
                res = getattr(resource, 'RLIMIT_%s' % limit.upper(), None)
                if res is None:
                    raise ValueError('unknown rlimit "%s"' % limit)
                # TODO(petef): support hard/soft limits
                resource.setrlimit(res, (value, value))

            if self.gid:
                try:
                    os.setgid(self.gid)
                except OverflowError:
                    if not ctypes:
                        raise
                    # versions of python < 2.6.2 don't manage unsigned int for
                    # groups like on osx or fedora
                    os.setgid(-ctypes.c_int(-self.gid).value)

                if self.username is not None:
                    try:
                        os.initgroups(self.username, self.gid)
                    except (OSError, AttributeError):
                        # not support on Mac or 2.6
                        pass

            if self.uid:
                os.setuid(self.uid)

        extra = {}
        if self.pipe_stdout:
            extra['stdout'] = PIPE

        if self.pipe_stderr:
            extra['stderr'] = PIPE

        self._worker = Popen(args, cwd=self.working_dir,
                             shell=self.shell, preexec_fn=preexec_fn,
                             env=self.env, close_fds=not self.use_fds,
                             executable=self.executable, **extra)

        # let go of sockets created only for self._worker to inherit
        self._sockets = []

        self.started = time.time()

    def format_args(self, sockets_fds=None):
        """ It's possible to use environment variables and some other variables
        that are available in this context, when spawning the processes.
        """
        logger.debug('cmd: ' + bytestring(self.cmd))
        logger.debug('args: ' + str(self.args))

        current_env = ObjectDict(self.env.copy())

        format_kwargs = {
            'wid': self.wid, 'shell': self.shell, 'args': self.args,
            'env': current_env, 'working_dir': self.working_dir,
            'uid': self.uid, 'gid': self.gid, 'rlimits': self.rlimits,
            'executable': self.executable, 'use_fds': self.use_fds}

        if sockets_fds is not None:
            format_kwargs['sockets'] = sockets_fds

        if self.watcher is not None:
            for option in self.watcher.optnames:
                if option not in format_kwargs\
                        and hasattr(self.watcher, option):
                    format_kwargs[option] = getattr(self.watcher, option)

        cmd = replace_gnu_args(self.cmd, **format_kwargs)

        if '$WID' in cmd or (self.args and '$WID' in self.args):
            msg = "Using $WID in the command is deprecated. You should use "\
                  "the python string format instead. In you case, this means "\
                  "replacing the $WID in your command by $(WID)."

            warnings.warn(msg, DeprecationWarning)
            self.cmd = cmd.replace('$WID', str(self.wid))

        if self.args is not None:
            if isinstance(self.args, string_types):
                args = shlex.split(bytestring(replace_gnu_args(
                    self.args, **format_kwargs)))
            else:
                args = [bytestring(replace_gnu_args(arg, **format_kwargs))
                        for arg in self.args]
            args = shlex.split(bytestring(cmd)) + args
        else:
            args = shlex.split(bytestring(cmd))

        if self.shell:
            # subprocess.Popen(shell=True) implies that 1st arg is the
            # requested command, remaining args are applied to sh.
            args = [' '.join(quote(arg) for arg in args)]
            shell_args = format_kwargs.get('shell_args', None)
            if shell_args and is_win():
                logger.warn("shell_args won't apply for "
                            "windows platforms: %s", shell_args)
            elif isinstance(shell_args, string_types):
                args += shlex.split(bytestring(replace_gnu_args(
                    shell_args, **format_kwargs)))
            elif shell_args:
                args += [bytestring(replace_gnu_args(arg, **format_kwargs))
                         for arg in shell_args]

        elif format_kwargs.get('shell_args', False):
            logger.warn("shell_args is defined but won't be used "
                        "in this context: %s", format_kwargs['shell_args'])
        logger.debug("process args: %s", args)
        return args

    def returncode(self):
        return self._worker.returncode

    @debuglog
    def poll(self):
        return self._worker.poll()

    @debuglog
    def is_alive(self):
        return self.poll() is None

    @debuglog
    def send_signal(self, sig):
        """Sends a signal **sig** to the process."""
        logger.debug("sending signal %s to %s" % (sig, self.pid))
        return self._worker.send_signal(sig)

    @debuglog
    def stop(self):
        """Stop the process and close stdout/stderr

        If the corresponding process is still here
        (normally it's already killed by the watcher),
        a SIGTERM is sent, then a SIGKILL after 1 second.

        The shutdown process (SIGTERM then SIGKILL) is
        normally taken by the watcher. So if the process
        is still there here, it's a kind of bad behavior
        because the graceful timeout won't be respected here.
        """
        try:
            try:
                if self._worker.poll() is None:
                    return self._worker.terminate()
            finally:
                if self._worker.stderr is not None:
                    self._worker.stderr.close()
                if self._worker.stdout is not None:
                    self._worker.stdout.close()
        except NoSuchProcess:
            pass

    def age(self):
        """Return the age of the process in seconds."""
        return time.time() - self.started

    def info(self):
        """Return process info.

        The info returned is a mapping with these keys:

        - **mem_info1**: Resident Set Size Memory in bytes (RSS)
        - **mem_info2**: Virtual Memory Size in bytes (VMS).
        - **cpu**: % of cpu usage.
        - **mem**: % of memory usage.
        - **ctime**: process CPU (user + system) time in seconds.
        - **pid**: process id.
        - **username**: user name that owns the process.
        - **nice**: process niceness (between -20 and 20)
        - **cmdline**: the command line the process was run with.
        """
        try:
            info = get_info(self._worker)
        except NoSuchProcess:
            return "No such process (stopped?)"

        info["age"] = self.age()
        info["started"] = self.started
        info["children"] = []
        info['wid'] = self.wid
        for child in get_children(self._worker):
            info["children"].append(get_info(child))

        return info

    def children(self):
        """Return a list of children pids."""
        return [child.pid for child in get_children(self._worker)]

    def is_child(self, pid):
        """Return True is the given *pid* is a child of that process."""
        pids = [child.pid for child in get_children(self._worker)]
        if pid in pids:
            return True
        return False

    @debuglog
    def send_signal_child(self, pid, signum):
        """Send signal *signum* to child *pid*."""
        children = dict((child.pid, child)
                        for child in get_children(self._worker))
        try:
            children[pid].send_signal(signum)
        except KeyError:
            raise NoSuchProcess(pid)

    @debuglog
    def send_signal_children(self, signum):
        """Send signal *signum* to all children."""
        for child in get_children(self._worker):
            try:
                child.send_signal(signum)
            except OSError as e:
                if e.errno != errno.ESRCH:
                    raise

    @property
    def status(self):
        """Return the process status as a constant

        - RUNNING
        - DEAD_OR_ZOMBIE
        - UNEXISTING
        - OTHER
        """
        try:
            if get_status(self._worker) in (STATUS_ZOMBIE, STATUS_DEAD):
                return DEAD_OR_ZOMBIE
        except NoSuchProcess:
            return UNEXISTING

        if self._worker.is_running():
            return RUNNING
        return OTHER

    @property
    def pid(self):
        """Return the *pid*"""
        return self._worker.pid

    @property
    def stdout(self):
        """Return the *stdout* stream"""
        return self._worker.stdout

    @property
    def stderr(self):
        """Return the *stdout* stream"""
        return self._worker.stderr

    def __eq__(self, other):
        return self is other

    def __lt__(self, other):
        return self.started < other.started

    def __gt__(self, other):
        return self.started > other.started

########NEW FILE########
__FILENAME__ = py3compat
import sys

PY2 = sys.version_info[0] < 3

if PY2:
    string_types = basestring  # NOQA
    integer_types = (int, long)
    text_type = unicode  # NOQA
    long = long
    bytes = str

    def bytestring(s):  # NOQA
        if isinstance(s, unicode):  # NOQA
            return s.encode('utf-8')
        return s

    def cast_bytes(s, encoding='utf8'):
        """cast unicode or bytes to bytes"""
        if isinstance(s, unicode):
            return s.encode(encoding)
        return str(s)

    def cast_unicode(s, encoding='utf8', errors='replace'):
        """cast bytes or unicode to unicode.
          errors options are strict, ignore or replace"""
        if isinstance(s, unicode):
            return s
        return str(s).decode(encoding)

    def cast_string(s, errors='replace'):
        return s if isinstance(s, basestring) else str(s)

    try:
        import cStringIO
        StringIO = cStringIO.StringIO   # NOQA
    except ImportError:
        import StringIO
        StringIO = StringIO.StringIO    # NOQA

    BytesIO = StringIO

    eval(compile('def raise_with_tb(E): raise E, None, sys.exc_info()[2]',
                 'py3compat.py', 'exec'))

    def is_callable(c):  # NOQA
        return callable(c)

    def get_next(c):  # NOQA
        return c.next

    # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
    class X(object):
        def __len__(self):
            return 1 << 31
    try:
        len(X())
    except OverflowError:
        # 32-bit
        MAXSIZE = int((1 << 31) - 1)        # NOQA
    else:
        # 64-bit
        MAXSIZE = int((1 << 63) - 1)        # NOQA
    del X

    def sort_by_field(obj, field='name'):   # NOQA
        def _by_field(item1, item2):
            return cmp(item1[field], item2[field])

        obj.sort(_by_field)

else:
    import collections
    string_types = str
    integer_types = int
    text_type = str
    long = int
    unicode = str

    def sort_by_field(obj, field='name'):       # NOQA
        def _by_field(item):
            return item[field]

        obj.sort(key=_by_field)

    def bytestring(s):  # NOQA
        return s

    def cast_bytes(s, encoding='utf8'):  # NOQA
        """cast unicode or bytes to bytes"""
        if isinstance(s, bytes):
            return s
        return str(s).encode(encoding)

    def cast_unicode(s, encoding='utf8', errors='replace'):  # NOQA
        """cast bytes or unicode to unicode.
          errors options are strict, ignore or replace"""
        if isinstance(s, bytes):
            return s.decode(encoding, errors=errors)
        return str(s)

    cast_string = cast_unicode

    import io
    StringIO = io.StringIO      # NOQA
    BytesIO = io.BytesIO        # NOQA

    def raise_with_tb(E):     # NOQA
        raise E.with_traceback(sys.exc_info()[2])

    def is_callable(c):  # NOQA
        return isinstance(c, collections.Callable)

    def get_next(c):  # NOQA
        return c.__next__

    MAXSIZE = sys.maxsize       # NOQA

b = cast_bytes
s = cast_string
u = cast_unicode

try:
    # PY >= 3.3
    from shlex import quote  # NOQA
except ImportError:
    from pipes import quote  # NOQA

########NEW FILE########
__FILENAME__ = sighandler
import signal
import traceback
import sys

from circus import logger
from circus.client import make_json


class SysHandler(object):

    SIGNALS = [getattr(signal, "SIG%s" % x) for x in
               "HUP QUIT INT TERM WINCH".split()]

    SIG_NAMES = dict(
        (getattr(signal, name), name[3:].lower()) for name in dir(signal)
        if name[:3] == "SIG" and name[3] != "_"
    )

    def __init__(self, controller):
        self.controller = controller

        # init signals
        logger.info('Registering signals...')
        self._old = {}
        self._register()

    def stop(self):
        for sig, callback in self._old.items():
            try:
                signal.signal(sig, callback)
            except ValueError:
                pass

    def _register(self):
        for sig in self.SIGNALS:
            self._old[sig] = signal.getsignal(sig)
            signal.signal(sig, self.signal)

        # Don't let SIGQUIT and SIGUSR1 disturb active requests
        # by interrupting system calls
        if hasattr(signal, 'siginterrupt'):  # python >= 2.6
            signal.siginterrupt(signal.SIGQUIT, False)
            signal.siginterrupt(signal.SIGUSR1, False)

    def signal(self, sig, frame=None):
        signame = self.SIG_NAMES.get(sig)
        logger.info('Got signal SIG_%s' % signame.upper())

        if signame is not None:
            try:
                handler = getattr(self, "handle_%s" % signame)
                handler()
            except AttributeError:
                pass
            except Exception as e:
                tb = traceback.format_exc()
                logger.error("error: %s [%s]" % (e, tb))
                sys.exit(1)

    def handle_int(self):
        self.controller.dispatch((None, make_json("quit")))

    def handle_term(self):
        self.controller.dispatch((None, make_json("quit")))

    def handle_quit(self):
        self.controller.dispatch((None, make_json("quit")))

    def handle_winch(self):
        pass

    def handle_hup(self):
        self.controller.dispatch((None, make_json("reload", graceful=True)))

########NEW FILE########
__FILENAME__ = sockets
import socket
import os

from circus import logger


_FAMILY = {
    'AF_UNIX': socket.AF_UNIX,
    'AF_INET': socket.AF_INET,
    'AF_INET6': socket.AF_INET6
}

_TYPE = {
    'SOCK_STREAM': socket.SOCK_STREAM,
    'SOCK_DGRAM': socket.SOCK_DGRAM,
    'SOCK_RAW': socket.SOCK_RAW,
    'SOCK_RDM': socket.SOCK_RDM,
    'SOCK_SEQPACKET': socket.SOCK_SEQPACKET
}


def addrinfo(host, port, family):
    for _addrinfo in socket.getaddrinfo(host, port):
        if len(_addrinfo[-1]) == 2:
            return _addrinfo[-1][-2], _addrinfo[-1][-1]

        if family == socket.AF_INET6 and len(_addrinfo[-1]) == 4:
            return _addrinfo[-1][-4], _addrinfo[-1][-3]

    raise ValueError((host, port))


class CircusSocket(socket.socket):
    """Inherits from socket, to add a few extra options.
    """
    def __init__(self, name='', host='localhost', port=8080,
                 family=socket.AF_INET, type=socket.SOCK_STREAM,
                 proto=0, backlog=2048, path=None, umask=None, replace=False,
                 interface=None, so_reuseport=False):
        if path is not None:
            family = socket.AF_UNIX

        super(CircusSocket, self).__init__(family=family, type=type,
                                           proto=proto)
        self.name = name
        self.socktype = type
        self.path = path
        self.umask = umask
        self.replace = replace

        if family == socket.AF_UNIX:
            self.host = self.port = None
            self.is_unix = True
        else:
            self.host, self.port = addrinfo(host, port, family)
            self.is_unix = False

        self.interface = interface
        self.backlog = backlog
        self.so_reuseport = so_reuseport

        if self.so_reuseport and hasattr(socket, 'SO_REUSEPORT'):
            try:
                self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except socket.error:
                # see 699
                pass
        else:
            self.so_reuseport = False

        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    @property
    def location(self):
        if self.is_unix:
            return '%r' % self.path
        return '%s:%d' % (self.host, self.port)

    def __str__(self):
        return 'socket %r at %s' % (self.name, self.location)

    def close(self):
        socket.socket.close(self)
        if self.is_unix and os.path.exists(self.path):
            os.remove(self.path)

    def bind_and_listen(self):
        try:
            if self.is_unix:
                if os.path.exists(self.path):
                    if self.replace:
                        os.unlink(self.path)
                    else:
                        raise OSError("%r already exists. You might want to "
                                      "remove it. If it's a stalled socket "
                                      "file, just restart Circus" % self.path)
                if self.umask is None:
                    self.bind(self.path)
                else:
                    old_mask = os.umask(self.umask)
                    self.bind(self.path)
                    os.umask(old_mask)
            else:
                if self.interface is not None:
                    # Bind to device if given, e.g. to limit which device to
                    # bind when binding on IN_ADDR_ANY or IN_ADDR_BROADCAST.
                    import IN
                    if hasattr(IN, 'SO_BINDTODEVICE'):
                        self.setsockopt(socket.SOL_SOCKET, IN.SO_BINDTODEVICE,
                                        self.interface + '\0')
                        logger.debug('Binding to device: %s' % self.interface)

                self.bind((self.host, self.port))
        except socket.error:
            logger.error('Could not bind %s' % self.location)
            raise

        self.setblocking(0)
        if self.socktype in (socket.SOCK_STREAM, socket.SOCK_SEQPACKET):
            self.listen(self.backlog)

        if not self.is_unix:
            if self.family == socket.AF_INET6:
                self.host, self.port, _flowinfo, _scopeid = self.getsockname()
            else:
                self.host, self.port = self.getsockname()

        logger.debug('Socket bound at %s - fd: %d' % (self.location,
                                                      self.fileno()))

    @classmethod
    def load_from_config(cls, config):
        params = {'name': config['name'],
                  'host': config.get('host', 'localhost'),
                  'port': int(config.get('port', '8080')),
                  'path': config.get('path'),
                  'interface': config.get('interface', None),
                  'family': _FAMILY[config.get('family', 'AF_INET').upper()],
                  'type': _TYPE[config.get('type', 'SOCK_STREAM').upper()],
                  'backlog': int(config.get('backlog', 2048)),
                  'so_reuseport': config.get('so_reuseport', False),
                  'umask': int(config.get('umask', 8)),
                  'replace': config.get('replace')}
        proto_name = config.get('proto')
        if proto_name is not None:
            params['proto'] = socket.getprotobyname(proto_name)
        s = cls(**params)

        # store the config for later checking if config has changed
        s._cfg = config.copy()

        return s


class CircusSockets(dict):
    """Manage CircusSockets objects.
    """
    def __init__(self, sockets=None, backlog=2048):
        self.backlog = backlog
        if sockets is not None:
            for sock in sockets:
                self[sock.name] = sock

    def add(self, name, host='localhost', port=8080, family=socket.AF_INET,
            type=socket.SOCK_STREAM, proto=0, backlog=None, path=None,
            umask=None, interface=None):

        if backlog is None:
            backlog = self.backlog

        sock = self.get(name)
        if sock is not None:
            raise ValueError('A socket already exists %s' % sock)

        sock = CircusSocket(name=name, host=host, port=port, family=family,
                            type=type, proto=proto, backlog=backlog, path=path,
                            umask=umask, interface=interface)
        self[name] = sock
        return sock

    def close_all(self):
        for sock in self.values():
            sock.close()

    def bind_and_listen_all(self):
        for sock in self.values():
            # so_reuseport sockets should not be bound at this point
            if not sock.so_reuseport:
                sock.bind_and_listen()

########NEW FILE########
__FILENAME__ = client
import argparse
import sys
import curses
from collections import defaultdict
import errno
import circus.fixed_threading as threading
import time
import logging

import zmq
import zmq.utils.jsonapi as json

from circus.consumer import CircusConsumer
from circus import __version__
from circus.util import DEFAULT_ENDPOINT_STATS
from circus.py3compat import s


class StatsClient(CircusConsumer):
    def __init__(self, endpoint=DEFAULT_ENDPOINT_STATS, ssh_server=None,
                 context=None):
        CircusConsumer.__init__(self, ['stat.'], context, endpoint, ssh_server)

    def iter_messages(self):
        """ Yields tuples of (watcher, subtopic, stat)"""
        recv = self.pubsub_socket.recv_multipart
        with self:
            while True:
                try:
                    events = dict(self.poller.poll(self.timeout * 1000))
                except zmq.ZMQError as e:
                    if e.errno == errno.EINTR:
                        continue
                    raise

                if len(events) == 0:
                    continue

                try:
                    topic, stat = recv()
                except zmq.core.error.ZMQError as e:
                    if e.errno != errno.EINTR:
                        raise
                    else:
                        try:
                            sys.exc_clear()
                        except Exception:
                            pass
                        continue

                topic = s(topic).split('.')
                if len(topic) == 3:
                    __, watcher, subtopic = topic
                    yield watcher, subtopic, json.loads(stat)
                elif len(topic) == 2:
                    __, watcher = topic
                    yield watcher, None, json.loads(stat)


def _paint(stdscr, watchers=None, old_h=None, old_w=None):

    current_h, current_w = stdscr.getmaxyx()

    def addstr(x, y, text):
        text_len = len(text)

        if x < current_h:
            padding = current_w - y
            if text_len >= padding:
                text = text[:padding - 1]
            else:
                text += ' ' * (padding - text_len - 1)

            if text == '':
                return

            stdscr.addstr(x, y, text)

    stdscr.erase()

    if watchers is None:
        stdscr.erase()
        addstr(1, 0, '*** Waiting for data ***')
        stdscr.refresh()
        return current_h, current_w

    if current_h != old_h or current_w != old_w:
        # we need a resize
        curses.endwin()
        stdscr.refresh()
        stdscr.erase()
        stdscr.resize(current_h, current_w)

    addstr(0, 0, 'Circus Top')
    addstr(1, 0, '-' * current_w)
    names = sorted(watchers.keys())
    line = 2
    for name in names:
        if name in ('circusd-stats', 'circushttpd'):
            continue

        addstr(line, 0, name.replace('-', '.'))
        line += 1

        if name == 'sockets':
            addstr(line, 3, 'ADDRESS')
            addstr(line, 28, 'HITS')

            line += 1

            fds = []

            total = 0
            for stats in watchers[name].values():
                if 'addresses' in stats:
                    total = stats['reads']
                    continue

                reads = stats['reads']
                address = stats['address']
                fds.append((reads, address))

            fds.sort()
            fds.reverse()

            for reads, address in fds:
                addstr(line, 2, str(address))
                addstr(line, 29, '%3d' % reads)
                line += 1

            addstr(line, 29, '%3d (sum)' % total)
            line += 2

        else:
            addstr(line, 3, 'PID')
            addstr(line, 28, 'CPU (%)')
            addstr(line, 48, 'MEMORY (%)')
            addstr(line, 68, 'AGE (s)')
            line += 1

            # sorting by CPU
            pids = []
            total = '', 'N/A', 'N/A', None
            for pid, stat in watchers[name].items():
                if stat['cpu'] == 'N/A':
                    cpu = 'N/A'
                else:
                    cpu = "%.2f" % stat['cpu']

                if stat['mem'] == 'N/A':
                    mem = 'N/A'
                else:
                    mem = "%.2f" % stat['mem']

                if stat['age'] == 'N/A':
                    age = 'N/A'
                else:
                    age = "%.2f" % stat['age']

                if pid == 'all' or isinstance(pid, list):
                    total = (cpu + ' (avg)', mem + ' (sum)', age + ' (older)',
                             '', None)
                else:
                    pids.append((cpu, mem, age, str(stat['pid']),
                                 stat['name']))

            pids.sort()
            pids.reverse()
            pids = pids[:10] + [total]

            for cpu, mem, age, pid, name in pids:
                if name is not None:
                    pid = '%s (%s)' % (pid, name)
                addstr(line, 2, pid)
                addstr(line, 29, cpu)
                addstr(line, 49, mem)
                addstr(line, 69, age)
                line += 1
            line += 1

    if line < current_h and len(watchers) > 0:
        addstr(line, 0, '-' * current_w)

    stdscr.refresh()
    return current_h, current_w


class Painter(threading.Thread):
    def __init__(self, screen, watchers, h, w):
        threading.Thread.__init__(self)
        self.daemon = True
        self.screen = screen
        self.watchers = watchers
        self.running = False
        self.h = h
        self.w = w

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            self.h, self.w = _paint(self.screen, self.watchers, self.h, self.w)
            time.sleep(1.)


def main():
    logging.basicConfig()
    desc = 'Runs Circus Top'
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('--endpoint',
                        help='The circusd-stats ZeroMQ socket to connect to',
                        default=DEFAULT_ENDPOINT_STATS)

    parser.add_argument('--version', action='store_true',
                        default=False,
                        help='Displays Circus version and exits.')

    parser.add_argument('--ssh', default=None, help='SSH Server')

    parser.add_argument('--process-timeout',
                        default=3,
                        help='After this delay of inactivity, a process will \
                         be removed')

    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    stdscr = curses.initscr()
    watchers = defaultdict(dict)
    h, w = _paint(stdscr)
    last_refresh_for_pid = defaultdict(float)
    time.sleep(1.)

    painter = Painter(stdscr, watchers, h, w)
    painter.start()

    try:
        client = StatsClient(args.endpoint, args.ssh)
        try:
            for watcher, subtopic, stat in client:
                # building the line
                stat['watcher'] = watcher
                if subtopic is None:
                    subtopic = 'all'

                # Clean pids that have not been updated recently
                valid_pid = lambda p: p.isdigit() and p in watchers[watcher]
                for pid in filter(valid_pid, watchers[watcher]):
                    if (last_refresh_for_pid[pid] <
                            time.time() - int(args.process_timeout)):
                        del watchers[watcher][pid]
                last_refresh_for_pid[subtopic] = time.time()

                # adding it to the structure
                watchers[watcher][subtopic] = stat
        except KeyboardInterrupt:
            client.stop()
    finally:
        painter.stop()
        curses.endwin()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = collector
import errno
from collections import defaultdict
from select import select
import socket

from circus import util
from circus import logger
from zmq.eventloop import ioloop


class BaseStatsCollector(ioloop.PeriodicCallback):

    def __init__(self, streamer, name, callback_time=1., io_loop=None):
        ioloop.PeriodicCallback.__init__(self, self._callback,
                                         callback_time * 1000, io_loop)
        self.streamer = streamer
        self.name = name

    def _callback(self):
        logger.debug('Publishing stats about {0}'.format(self.name))
        for stats in self.collect_stats():
            if stats is None:
                continue
            self.streamer.publisher.publish(self.name, stats)

    def collect_stats(self):
        # should be implemented in subclasses
        raise NotImplementedError()  # PRAGMA: NOCOVER


class WatcherStatsCollector(BaseStatsCollector):
    def _aggregate(self, aggregate):
        res = {'pid': list(aggregate.keys())}
        stats = list(aggregate.values())

        # aggregating CPU does not mean anything
        # but the average can be a good indicator
        cpu = [stat['cpu'] for stat in stats]
        if 'N/A' in cpu:
            res['cpu'] = 'N/A'
        else:
            try:
                res['cpu'] = sum(cpu) / len(cpu)
            except ZeroDivisionError:
                res['cpu'] = 0.

        # aggregating memory does make sense
        mem = [stat['mem'] for stat in stats]
        if 'N/A' in mem:
            res['mem'] = 'N/A'
        else:
            res['mem'] = sum(mem)

        # finding out the older process
        ages = [stat['age'] for stat in stats if stat['age'] != 'N/A']
        if len(ages) == 0:
            res['age'] = 'N/A'
        else:
            res['age'] = max(ages)

        return res

    def collect_stats(self):
        aggregate = {}

        # sending by pids
        for pid in self.streamer.get_pids(self.name):
            name = None

            if self.name == 'circus':
                if pid in self.streamer.circus_pids:
                    name = self.streamer.circus_pids[pid]

            try:
                info = util.get_info(pid)
                aggregate[pid] = info
                info['subtopic'] = pid
                info['name'] = name
                yield info
            except util.NoSuchProcess:
                # the process is gone !
                pass
            except Exception as e:
                logger.exception('Failed to get info for %d. %s' % (pid,
                                                                    str(e)))

        # now sending the aggregation
        yield self._aggregate(aggregate)


# RESOLUTION is a value in seconds that will be used
# to determine the poller timeout of the sockets stats collector
#
# The PeriodicCallback calls the poller every LOOP_RES ms, and block
# for RESOLUTION seconds unless a read ready event occurs in the
# socket.
#
# This timer is used to limit the number of polls done on the
# socket, so the circusd-stats process don't eat all your CPU
# when you have a high-loaded socket.
#
_RESOLUTION = .1
_LOOP_RES = 10


class SocketStatsCollector(BaseStatsCollector):

    def __init__(self, streamer, name, callback_time=1., io_loop=None):
        super(SocketStatsCollector, self).__init__(streamer, name,
                                                   callback_time, io_loop)
        self._rstats = defaultdict(int)
        self.sockets = [sock for sock, address, fd in self.streamer.sockets]
        self._p = ioloop.PeriodicCallback(self._select, _LOOP_RES,
                                          io_loop=io_loop)

    def start(self):
        self._p.start()
        super(SocketStatsCollector, self).start()

    def stop(self):
        self._p.stop()
        BaseStatsCollector.stop(self)

    def _select(self):
        try:
            rlist, wlist, xlist = select(self.sockets, [], [], .01)
        except socket.error as err:
            if err.errno == errno.EBADF:
                return
            raise

        if len(rlist) == 0:
            return

        for sock in rlist:
            try:
                fileno = sock.fileno()
            except socket.error as err:
                if err.errno == errno.EBADF:
                    continue
                else:
                    raise

            self._rstats[fileno] += 1

    def _aggregate(self, aggregate):
        raise NotImplementedError()

    def collect_stats(self):
        # sending hits by sockets
        sockets = self.streamer.sockets

        if len(sockets) == 0:
            yield None
        else:
            fds = []

            for sock, address, fd in sockets:
                try:
                    fileno = sock.fileno()
                except socket.error as err:
                    if err.errno == errno.EBADF:
                        continue
                    else:
                        raise

                fds.append((address, fileno, fd))

            total = {'addresses': [], 'reads': 0}

            # we might lose a few hits here but it's ok
            for address, monitored_fd, fd in fds:
                info = {}
                info['fd'] = info['subtopic'] = fd
                info['reads'] = self._rstats[monitored_fd]
                total['reads'] += info['reads']
                total['addresses'].append(address)
                info['address'] = address
                self._rstats[monitored_fd] = 0
                yield info

            yield total

########NEW FILE########
__FILENAME__ = publisher
import zmq
import zmq.utils.jsonapi as json
from circus.py3compat import b

from circus import logger


class StatsPublisher(object):
    def __init__(self, stats_endpoint='tcp://127.0.0.1:5557', context=None):
        self.ctx = context or zmq.Context()
        self.destroy_context = context is None
        self.stats_endpoint = stats_endpoint
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.bind(self.stats_endpoint)
        self.socket.linger = 0

    def publish(self, name, stat):
        try:
            topic = 'stat.%s' % str(name)
            if 'subtopic' in stat:
                topic += '.%d' % stat['subtopic']

            stat = json.dumps(stat)
            logger.debug('Sending %s' % stat)
            self.socket.send_multipart([b(topic), stat])

        except zmq.ZMQError:
            if self.socket.closed:
                pass
            else:
                raise

    def stop(self):
        if self.destroy_context:
            self.ctx.destroy(0)
        logger.debug('Publisher stopped')

########NEW FILE########
__FILENAME__ = streamer
from collections import defaultdict
from itertools import chain
import os
import errno
import socket

import zmq
import zmq.utils.jsonapi as json
from zmq.eventloop import ioloop, zmqstream

from circus.commands import get_commands
from circus.client import CircusClient
from circus.stats.collector import WatcherStatsCollector, SocketStatsCollector
from circus.stats.publisher import StatsPublisher
from circus import logger
from circus.py3compat import s


class StatsStreamer(object):
    def __init__(self, endpoint, pubsub_endoint, stats_endpoint,
                 ssh_server=None, delay=1., loop=None):
        self.topic = b'watcher.'
        self.delay = delay
        self.ctx = zmq.Context()
        self.pubsub_endpoint = pubsub_endoint
        self.sub_socket = self.ctx.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, self.topic)
        self.sub_socket.connect(self.pubsub_endpoint)
        self.loop = loop or ioloop.IOLoop.instance()
        self.substream = zmqstream.ZMQStream(self.sub_socket, self.loop)
        self.substream.on_recv(self.handle_recv)
        self.client = CircusClient(context=self.ctx, endpoint=endpoint,
                                   ssh_server=ssh_server)
        self.cmds = get_commands()
        self.publisher = StatsPublisher(stats_endpoint, self.ctx)
        self._initialize()

    def _initialize(self):
        self._pids = defaultdict(list)
        self._callbacks = dict()
        self.running = False  # should the streamer be running?
        self.stopped = False  # did the collect started yet?
        self.circus_pids = {}
        self.sockets = []
        self.get_watchers = self._pids.keys

    def get_pids(self, watcher=None):
        if watcher is not None:
            if watcher == 'circus':
                return list(self.circus_pids.keys())
            return self._pids[watcher]
        return chain(*list(self._pids.values()))

    def get_circus_pids(self):
        watchers = self.client.send_message('list').get('watchers', [])

        # getting the circusd, circusd-stats and circushttpd pids
        res = self.client.send_message('dstats')
        pids = {os.getpid(): 'circusd-stats'}

        if 'info' in res:
            pids[res['info']['pid']] = 'circusd'

        if 'circushttpd' in watchers:
            httpd_pids = self.client.send_message('list', name='circushttpd')

            if 'pids' in httpd_pids:
                httpd_pids = httpd_pids['pids']
                if len(httpd_pids) == 1:
                    pids[httpd_pids[0]] = 'circushttpd'

        return pids

    def _add_callback(self, name, start=True, kind='watcher'):
        logger.debug('Callback added for %s' % name)

        if kind == 'watcher':
            klass = WatcherStatsCollector
        elif kind == 'socket':
            klass = SocketStatsCollector
        else:
            raise ValueError('Unknown callback kind %r' % kind)

        self._callbacks[name] = klass(self, name, self.delay, self.loop)
        if start:
            self._callbacks[name].start()

    def _init(self):
        self._pids.clear()

        # getting the initial list of watchers/pids
        res = self.client.send_message('list')

        for watcher in res['watchers']:
            if watcher in ('circusd', 'circushttpd', 'circusd-stats'):
                # this is dealt by the special 'circus' collector
                continue

            pid_list = self.client.send_message('list', name=watcher)
            pids = pid_list.get('pids', [])
            for pid in pids:
                self._append_pid(watcher, pid)

        # getting the circus pids
        self.circus_pids = self.get_circus_pids()
        if 'circus' not in self._callbacks:
            self._add_callback('circus')
        else:
            self._callbacks['circus'].start()

        # getting the initial list of sockets
        res = self.client.send_message('listsockets')
        for sock in res.get('sockets', []):
            fd = sock['fd']
            if 'path' in sock:
                # unix socket
                address = sock['path']
            else:
                address = '%s:%s' % (sock['host'], sock['port'])

            # XXX type / family ?
            sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
            self.sockets.append((sock, address, fd))

        self._add_callback('sockets', kind='socket')

    def stop_watcher(self, watcher):
        for pid in self._pids[watcher]:
            self.remove_pid(watcher, pid)

    def remove_pid(self, watcher, pid):
        if pid in self._pids[watcher]:
            logger.debug('Removing %d from %s' % (pid, watcher))
            self._pids[watcher].remove(pid)
            if len(self._pids[watcher]) == 0:
                logger.debug(
                    'Stopping the periodic callback for {0}' .format(watcher))
                self._callbacks[watcher].stop()

    def _append_pid(self, watcher, pid):
        if watcher not in self._pids or len(self._pids[watcher]) == 0:
            logger.debug(
                'Starting the periodic callback for {0}'.format(watcher))
            if watcher not in self._callbacks:
                self._add_callback(watcher)
            else:
                self._callbacks[watcher].start()

        if pid in self._pids[watcher]:
            return
        self._pids[watcher].append(pid)
        logger.debug('Adding %d in %s' % (pid, watcher))

    def start(self):
        self.running = True
        logger.info('Starting the stats streamer')
        self._init()
        logger.debug('Initial list is ' + str(self._pids))
        logger.debug('Now looping to get circusd events')

        while self.running:
            try:
                self.loop.start()
            except zmq.ZMQError as e:
                logger.debug(str(e))

                if e.errno == errno.EINTR:
                    continue
                elif e.errno == zmq.ETERM:
                    break
                else:
                    logger.debug("got an unexpected error %s (%s)", str(e),
                                 e.errno)
                    raise
            else:
                break
        self.stop()

    def handle_recv(self, data):
        """called each time circusd sends an event"""
        # maintains a periodic callback to compute mem and cpu consumption for
        # each pid.
        logger.debug('Received an event from circusd: %s' % str(data))
        topic, msg = data
        try:
            topic = s(topic)
            watcher = topic.split('.')[1:-1][0]
            action = topic.split('.')[-1]
            msg = json.loads(msg)

            if action in ('reap', 'kill'):
                # a process was reaped
                pid = msg['process_pid']
                self.remove_pid(watcher, pid)
            elif action == 'spawn':
                # a process was added
                pid = msg['process_pid']
                self._append_pid(watcher, pid)
            elif action == 'stop':
                # the whole watcher was stopped.
                self.stop_watcher(watcher)
            else:
                logger.debug('Unknown action: %r' % action)
                logger.debug(msg)
        except Exception:
            logger.exception('Failed to handle %r' % msg)

    def stop(self):
        # stop all the periodic callbacks running
        for callback in self._callbacks.values():
            callback.stop()

        self.loop.stop()
        self.ctx.destroy(0)
        self.publisher.stop()
        self.stopped = True
        self.running = False
        logger.info('Stats streamer stopped')

########NEW FILE########
__FILENAME__ = file_stream
import errno
import os
import tempfile
from datetime import datetime
import time as time_
import re
from stat import ST_DEV, ST_INO, ST_MTIME
from circus import logger
from circus.py3compat import s, PY2


class _FileStreamBase(object):
    """Base class for all file writer handler classes"""
    # You may want to use another now method (not naive or a mock).
    now = datetime.now

    def __init__(self, filename, time_format):
        if filename is None:
            fd, filename = tempfile.mkstemp()
            os.close(fd)
        self._filename = filename
        self._file = self._open()
        self._time_format = time_format
        self._buffer = []  # XXX - is this really needed?

    def _open(self):
        return open(self._filename, 'a+')

    def close(self):
        self._file.close()

    def write_data(self, data):
        # data to write on file
        file_data = s(data['data'])

        # If we want to prefix the stream with the current datetime
        if self._time_format is not None:
            time = self.now().strftime(self._time_format)
            prefix = '{time} [{pid}] | '.format(time=time, pid=data['pid'])
            file_data = prefix + file_data.rstrip('\n')
            file_data = file_data.replace('\n', '\n' + prefix)
            file_data += '\n'

        # writing into the file
        try:
            self._file.write(file_data)
        except Exception:
            # we can strip the string down on Py3 but not on Py2
            if not PY2:
                file_data = file_data.encode('latin-1', errors='replace')
                file_data = file_data.decode('latin-1')
                self._file.write(file_data)

        self._file.flush()


class FileStream(_FileStreamBase):
    def __init__(self, filename=None, max_bytes=0, backup_count=0,
                 time_format=None, **kwargs):
        '''
        File writer handler which writes output to a file, allowing rotation
        behaviour based on Python's ``logging.handlers.RotatingFileHandler``.

        By default, the file grows indefinitely. You can specify particular
        values of max_bytes and backup_count to allow the file to rollover at
        a predetermined size.

        Rollover occurs whenever the current log file is nearly max_bytes in
        length. If backup_count is >= 1, the system will successively create
        new files with the same pathname as the base file, but with extensions
        ".1", ".2" etc. appended to it. For example, with a backup_count of 5
        and a base file name of "app.log", you would get "app.log",
        "app.log.1", "app.log.2", ... through to "app.log.5". The file being
        written to is always "app.log" - when it gets filled up, it is closed
        and renamed to "app.log.1", and if files "app.log.1", "app.log.2" etc.
        exist, then they are renamed to "app.log.2", "app.log.3" etc.
        respectively.

        If max_bytes is zero, rollover never occurs.

        You may also configure the timestamp format as defined by
        datetime.strftime.

        Here is an example: ::

          [watcher:foo]
          cmd = python -m myapp.server
          stdout_stream.class = FileStream
          stdout_stream.filename = /var/log/circus/out.log
          stdout_stream.time_format = %Y-%m-%d %H:%M:%S
        '''
        super(FileStream, self).__init__(filename, time_format)
        self._max_bytes = int(max_bytes)
        self._backup_count = int(backup_count)

    def __call__(self, data):
        if self._should_rollover(data['data']):
            self._do_rollover()

        self.write_data(data)

    def _do_rollover(self):
        """
        Do a rollover, as described in __init__().
        """
        if self._file:
            self._file.close()
            self._file = None
        if self._backup_count > 0:
            for i in range(self._backup_count - 1, 0, -1):
                sfn = "%s.%d" % (self._filename, i)
                dfn = "%s.%d" % (self._filename, i + 1)
                if os.path.exists(sfn):
                    logger.debug("Log rotating %s -> %s" % (sfn, dfn))
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self._filename + ".1"
            if os.path.exists(dfn):
                os.remove(dfn)
            os.rename(self._filename, dfn)
            logger.debug("Log rotating %s -> %s" % (self._filename, dfn))
        self._file = self._open()

    def _should_rollover(self, raw_data):
        """
        Determine if rollover should occur.

        Basically, see if the supplied raw_data would cause the file to exceed
        the size limit we have.
        """
        if self._file is None:                 # delay was set...
            self._file = self._open()
        if self._max_bytes > 0:                   # are we rolling over?
            self._file.seek(0, 2)  # due to non-posix-compliant Windows feature
            if self._file.tell() + len(raw_data) >= self._max_bytes:
                return 1
        return 0


class WatchedFileStream(_FileStreamBase):
    def __init__(self, filename=None, time_format=None, **kwargs):
        '''
        File writer handler which writes output to a file, allowing an external
        log rotation process to handle rotation, like Python's
        ``logging.handlers.WatchedFileHandler``.

        By default, the file grows indefinitely, and you are responsible for
        ensuring that log rotation happens with some external tool like
        logrotate.

        You may also configure the timestamp format as defined by
        datetime.strftime.

        Here is an example: ::

          [watcher:foo]
          cmd = python -m myapp.server
          stdout_stream.class = WatchedFileStream
          stdout_stream.filename = /var/log/circus/out.log
          stdout_stream.time_format = %Y-%m-%d %H:%M:%S
        '''
        super(WatchedFileStream, self).__init__(filename, time_format)
        self.dev, self.ino = -1, -1
        self._statfile()

    def _statfile(self):
        stb = os.fstat(self._file.fileno())
        self.dev, self.ino = stb[ST_DEV], stb[ST_INO]

    def _statfilename(self):
        try:
            stb = os.stat(self._filename)
            return stb[ST_DEV], stb[ST_INO]
        except OSError as err:
            if err.errno == errno.ENOENT:
                return -1, -1
            else:
                raise

    def __call__(self, data):
        # stat the filename to see if the file we opened still exists. If the
        # ino or dev doesn't match, we need to open a new file handle
        dev, ino = self._statfilename()
        if dev != self.dev or ino != self.ino:
            self._file.flush()
            self._file.close()
            self._file = self._open()
            self._statfile()

        self.write_data(data)


_MIDNIGHT = 24 * 60 * 60  # number of seconds in a day


class TimedRotatingFileStream(FileStream):

    def __init__(self, filename=None, backup_count=0, time_format=None,
                 rotate_when=None, rotate_interval=1, utc=False, **kwargs):
        '''
        File writer handler which writes output to a file, allowing rotation
        behaviour based on Python's
        ``logging.handlers.TimedRotatingFileHandler``.

        The parameters are the same as ``FileStream`` except max_bytes.

        In addition you can specify extra parameters:

        - utc: if True, times in UTC will be used. otherwise local time is
          used. Default: False.
        - rotate_when: the type of interval. Can be S, M, H, D,
          'W0'-'W6' or 'midnight'. See Python's TimedRotatingFileHandler
          for more information.
        - rotate_interval: Rollover interval in seconds. Default: 1

        Here is an example: ::

          [watcher:foo]
          cmd = python -m myapp.server
          stdout_stream.class = TimedRotatingFileStream
          stdout_stream.filename = /var/log/circus/out.log
          stdout_stream.time_format = %Y-%m-%d %H:%M:%S
          stdout_stream.utc = True
          stdout_stream.rotate_when = H
          stdout_stream.rotate_interval = 1

        '''
        super(TimedRotatingFileStream,
              self).__init__(filename=filename, backup_count=backup_count,
                             time_format=time_format, utc=False,
                             **kwargs)

        self._utc = bool(utc)
        self._when = rotate_when

        if self._when == "S":
            self._interval = 1
            self._suffix = "%Y%m%d%H%M%S"
            self._ext_match = r"^\d{4}\d{2}\d{2}\d{2}\d{2}\d{2}$"
        elif self._when == "M":
            self._interval = 60
            self._suffix = "%Y%m%d%H%M"
            self._ext_match = r"^\d{4}\d{2}\d{2}\d{2}\d{2}$"
        elif self._when == "H":
            self._interval = 60 * 60
            self._suffix = "%Y%m%d%H"
            self._ext_match = r"^\d{4}\d{2}\d{2}\d{2}$"
        elif self._when in ("D", "MIDNIGHT"):
            self._interval = 60 * 60 * 24
            self._suffix = "%Y%m%d"
            self._ext_match = r"^\d{4}\d{2}\d{2}$"
        elif self._when.startswith("W"):
            self._interval = 60 * 60 * 24 * 7
            if len(self._when) != 2:
                raise ValueError("You must specify a day for weekly\
rollover from 0 to 6 (0 is Monday): %s" % self._when)
            if self._when[1] < "0" or self._when[1] > "6":
                raise ValueError("Invalid day specified\
for weekly rollover: %s" % self._when)
            self._day_of_week = int(self._when[1])
            self._suffix = "%Y%m%d"
            self._ext_match = r"^\d{4}\d{2}\d{2}$"
        else:
            raise ValueError("Invalid rollover interval specified: %s" %
                             self._when)

        self._ext_match = re.compile(self._ext_match)
        self._interval = self._interval * int(rotate_interval)

        if os.path.exists(self._filename):
            t = os.stat(self._filename)[ST_MTIME]
        else:
            t = int(time_.time())
        self._rollover_at = self._compute_rollover(t)

    def _do_rollover(self):
        if self._file:
            self._file.close()
            self._file = None

        current_time = int(time_.time())
        dst_now = time_.localtime(current_time)[-1]
        t = self._rollover_at - self._interval
        if self._utc:
            time_touple = time_.gmtime(t)
        else:
            time_touple = time_.localtime(t)
            dst_then = time_touple[-1]
            if dst_now != dst_then:
                if dst_now:
                    addend = 3600
                else:
                    addend = -3600
                time_touple = time_.localtime(t + addend)

        dfn = self._filename + "." + time_.strftime(self._suffix, time_touple)

        if os.path.exists(dfn):
            os.remove(dfn)

        if os.path.exists(self._filename):
            os.rename(self._filename, dfn)
            logger.debug("Log rotating %s -> %s" % (self._filename, dfn))

        if self._backup_count > 0:
            for f in self._get_files_to_delete():
                os.remove(f)

        self._file = self._open()

        new_rollover_at = self._compute_rollover(current_time)
        while new_rollover_at <= current_time:
            new_rollover_at = new_rollover_at + self._interval
        self._rollover_at = new_rollover_at

    def _compute_rollover(self, current_time):
        result = current_time + self._interval

        if self._when == "MIDNIGHT" or self._when.startswith("W"):
            if self._utc:
                t = time_.gmtime(current_time)
            else:
                t = time_.localtime(current_time)
            current_hour = t[3]
            current_minute = t[4]
            current_second = t[5]

            r = _MIDNIGHT - ((current_hour * 60 + current_minute) *
                             60 + current_second)
            result = current_time + r

            if self._when.startswith("W"):
                day = t[6]
                if day != self._day_of_week:
                    days_to_wait = self._day_of_week - day
                else:
                    days_to_wait = 6 - day + self._day_of_week + 1
                new_rollover_at = result + (days_to_wait * (60 * 60 * 24))
                if not self._utc:
                    dst_now = t[-1]
                    dst_at_rollover = time_.localtime(new_rollover_at)[-1]
                    if dst_now != dst_at_rollover:
                        if not dst_now:
                            addend = -3600
                        else:
                            addend = 3600
                        new_rollover_at += addend
                result = new_rollover_at

        return result

    def _get_files_to_delete(self):
        dirname, basename = os.path.split(self._filename)
        prefix = basename + "."
        plen = len(prefix)

        result = []
        for filename in os.listdir(dirname):
            if filename[:plen] == prefix:
                suffix = filename[plen:]
                if self._ext_match.match(suffix):
                    result.append(os.path.join(dirname, filename))
        result.sort()
        if len(result) < self._backup_count:
            return []
        return result[:len(result) - self._backup_count]

    def _should_rollover(self, raw_data):
        """
        Determine if rollover should occur.

        record is not used, as we are just comparing times, but it is needed so
        the method signatures are the same
        """
        t = int(time_.time())
        if t >= self._rollover_at:
            return 1
        return 0

########NEW FILE########
__FILENAME__ = redirector
import errno
import os
import sys

from zmq.eventloop import ioloop


class RedirectorHandler(object):
    def __init__(self, redirector, name, process, pipe):
        self.redirector = redirector
        self.name = name
        self.process = process
        self.pipe = pipe

    def __call__(self, fd, events):
        if not (events & ioloop.IOLoop.READ):
            if events == ioloop.IOLoop.ERROR:
                self.redirector.remove_redirection(self.pipe)
            return
        try:
            data = os.read(fd, self.redirector.buffer)
            if len(data) == 0:
                self.redirector.remove_redirection(self.pipe)
            else:
                datamap = {'data': data, 'pid': self.process.pid,
                           'name': self.name}
                datamap.update(self.redirector.extra_info)
                self.redirector.redirect(datamap)
        except IOError as ex:
            if ex.args[0] != errno.EAGAIN:
                raise
            try:
                sys.exc_clear()
            except Exception:
                pass


class Redirector(object):
    def __init__(self, redirect, extra_info=None,
                 buffer=4096, loop=None):
        self.running = False
        self.pipes = {}
        self._active = {}
        self.redirect = redirect
        self.extra_info = extra_info
        self.buffer = buffer
        if extra_info is None:
            extra_info = {}
        self.extra_info = extra_info
        self.loop = loop or ioloop.IOLoop.instance()

    def _start_one(self, name, process, pipe):
        fd = pipe.fileno()
        if fd not in self._active:
            handler = RedirectorHandler(self, name, process, pipe)
            self.loop.add_handler(fd, handler, ioloop.IOLoop.READ)
            self._active[fd] = handler

    def start(self):
        for name, process, pipe in self.pipes.values():
            self._start_one(name, process, pipe)
        self.running = True

    def _stop_one(self, fd):
        if fd in self._active:
            self.loop.remove_handler(fd)
            del self._active[fd]

    def stop(self):
        for fd in list(self._active.keys()):
            self._stop_one(fd)
        self.running = False

    def add_redirection(self, name, process, pipe):
        fd = pipe.fileno()
        self._stop_one(fd)
        self.pipes[fd] = name, process, pipe
        if self.running:
            self._start_one(name, process, pipe)

    def remove_redirection(self, pipe):
        try:
            fd = pipe.fileno()
        except ValueError:
            return
        self._stop_one(fd)
        if fd in self.pipes:
            del self.pipes[fd]

########NEW FILE########
__FILENAME__ = generic
import sys


def resolve_name(name):
    ret = None
    parts = name.split('.')
    cursor = len(parts)
    module_name = parts[:cursor]
    last_exc = None

    while cursor > 0:
        try:
            ret = __import__('.'.join(module_name))
            break
        except ImportError as exc:
            last_exc = exc
            if cursor == 0:
                raise
            cursor -= 1
            module_name = parts[:cursor]

    for part in parts[1:]:
        try:
            ret = getattr(ret, part)
        except AttributeError:
            if last_exc is not None:
                raise last_exc
            raise ImportError(name)

    if ret is None:
        if last_exc is not None:
            raise last_exc
        raise ImportError(name)

    return ret


if __name__ == '__main__':
    callback = resolve_name(sys.argv[1])
    try:
        if len(sys.argv) > 2:
            test_file = sys.argv[2]
            sys.exit(callback(test_file))
        else:
            sys.exit(callback())
    except:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = support
from tempfile import mkstemp, mkdtemp
import os
import signal
import sys
from time import time, sleep
from collections import defaultdict
import cProfile
import pstats
import shutil
import functools
import multiprocessing
import socket
try:
    import sysconfig
    DEBUG = sysconfig.get_config_var('Py_DEBUG') == 1
except ImportError:
    # py2.6, we don't really care about that flage here
    # since no one will run Python --with-pydebug in 2.6
    DEBUG = 0

try:
    from unittest import skip, skipIf, TestCase, TestSuite, findTestCases
except ImportError:
    from unittest2 import skip, skipIf, TestCase, TestSuite  # NOQA
    from unittest2 import findTestCases  # NOQA

from tornado.testing import AsyncTestCase
from zmq.eventloop import ioloop
import mock
import tornado

from circus import get_arbiter
from circus.util import DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB
from circus.util import tornado_sleep, ConflictError
from circus.client import AsyncCircusClient, make_message
from circus.stream import QueueStream

ioloop.install()
if 'ASYNC_TEST_TIMEOUT' not in os.environ:
    os.environ['ASYNC_TEST_TIMEOUT'] = '30'


class EasyTestSuite(TestSuite):
    def __init__(self, name):
        try:
            super(EasyTestSuite, self).__init__(
                findTestCases(sys.modules[name]))
        except KeyError:
            pass


def resolve_name(name):
    ret = None
    parts = name.split('.')
    cursor = len(parts)
    module_name = parts[:cursor]
    last_exc = None

    while cursor > 0:
        try:
            ret = __import__('.'.join(module_name))
            break
        except ImportError as exc:
            last_exc = exc
            if cursor == 0:
                raise
            cursor -= 1
            module_name = parts[:cursor]

    for part in parts[1:]:
        try:
            ret = getattr(ret, part)
        except AttributeError:
            if last_exc is not None:
                raise last_exc
            raise ImportError(name)

    if ret is None:
        if last_exc is not None:
            raise last_exc
        raise ImportError(name)

    return ret


_CMD = sys.executable


def get_ioloop():
    from zmq.eventloop.ioloop import ZMQPoller
    from zmq.eventloop.ioloop import ZMQError, ETERM
    from tornado.ioloop import PollIOLoop

    class DebugPoller(ZMQPoller):
        def __init__(self):
            super(DebugPoller, self).__init__()
            self._fds = []

        def register(self, fd, events):
            if fd not in self._fds:
                self._fds.append(fd)
            return self._poller.register(fd, self._map_events(events))

        def modify(self, fd, events):
            if fd not in self._fds:
                self._fds.append(fd)
            return self._poller.modify(fd, self._map_events(events))

        def unregister(self, fd):
            if fd in self._fds:
                self._fds.remove(fd)
            return self._poller.unregister(fd)

        def poll(self, timeout):
            """
            #737 - For some reason the poller issues events with
            unexistant FDs, usually with big ints. We have not found yet the
            reason of this
            behavior that happens only during the tests. But by filtering out
            those events, everything works fine.

            """
            z_events = self._poller.poll(1000*timeout)
            return [(fd, self._remap_events(evt)) for fd, evt in z_events
                    if fd in self._fds]

    class DebugLoop(PollIOLoop):
        def initialize(self, **kwargs):
            PollIOLoop.initialize(self, impl=DebugPoller(), **kwargs)

        def handle_callback_exception(self, callback):
            exc_type, exc_value, tb = sys.exc_info()
            raise exc_value

        @staticmethod
        def instance():
            PollIOLoop.configure(DebugLoop)
            return PollIOLoop.instance()

        def start(self):
            try:
                super(DebugLoop, self).start()
            except ZMQError as e:
                if e.errno == ETERM:
                    # quietly return on ETERM
                    pass
                else:
                    raise e

    from tornado import ioloop
    ioloop.IOLoop.configure(DebugLoop)
    return ioloop.IOLoop.instance()


def get_available_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("", 0))
        return s.getsockname()[1]
    finally:
        s.close()


class TestCircus(AsyncTestCase):

    arbiter_factory = get_arbiter
    arbiters = []

    def setUp(self):
        super(TestCircus, self).setUp()
        self.files = []
        self.dirs = []
        self.tmpfiles = []
        self._clients = {}
        self.plugins = []

    @property
    def cli(self):
        if self.arbiters == []:
            # nothing is running
            raise Exception("nothing is running")

        endpoint = self.arbiters[-1].endpoint
        if endpoint in self._clients:
            return self._clients[endpoint]

        cli = AsyncCircusClient(endpoint=endpoint)
        self._clients[endpoint] = cli
        return cli

    def _stop_clients(self):
        for client in self._clients.values():
            client.stop()
        self._clients.clear()

    def get_new_ioloop(self):
        return get_ioloop()

    def tearDown(self):
        for file in self.files + self.tmpfiles:
            if os.path.exists(file):
                os.remove(file)
        for dir in self.dirs:
            shutil.rmtree(dir)

        self._stop_clients()

        for plugin in self.plugins:
            plugin.stop()

        for arbiter in self.arbiters:
            if arbiter.running:
                try:
                    arbiter.stop()
                except ConflictError:
                    pass

        self.arbiters = []
        super(TestCircus, self).tearDown()

    def make_plugin(self, klass, endpoint=DEFAULT_ENDPOINT_DEALER,
                    sub=DEFAULT_ENDPOINT_SUB, check_delay=1,
                    **config):
        config['active'] = True
        plugin = klass(endpoint, sub, check_delay, None, **config)
        self.plugins.append(plugin)
        return plugin

    @tornado.gen.coroutine
    def start_arbiter(self, cmd='circus.tests.support.run_process',
                      stdout_stream=None, debug=True, **kw):
        if stdout_stream is None:
            self.stream = QueueStream()
            stdout_stream = {'stream': self.stream}
        testfile, arbiter = self._create_circus(
            cmd, stdout_stream=stdout_stream,
            debug=debug, async=True, **kw)
        self.test_file = testfile
        self.arbiter = arbiter
        self.arbiters.append(arbiter)
        yield self.arbiter.start()

    @tornado.gen.coroutine
    def stop_arbiter(self):
        for watcher in self.arbiter.iter_watchers():
            yield self.arbiter.rm_watcher(watcher.name)
        yield self.arbiter._emergency_stop()

    @tornado.gen.coroutine
    def status(self, cmd, **props):
        resp = yield self.call(cmd, **props)
        raise tornado.gen.Return(resp.get('status'))

    @tornado.gen.coroutine
    def numwatchers(self, cmd, **props):
        resp = yield self.call(cmd, waiting=True, **props)
        raise tornado.gen.Return(resp.get('numprocesses'))

    @tornado.gen.coroutine
    def numprocesses(self, cmd, **props):
        resp = yield self.call(cmd, waiting=True, **props)
        raise tornado.gen.Return(resp.get('numprocesses'))

    @tornado.gen.coroutine
    def pids(self):
        resp = yield self.call('list', name='test')
        raise tornado.gen.Return(resp.get('pids'))

    def get_tmpdir(self):
        dir_ = mkdtemp()
        self.dirs.append(dir_)
        return dir_

    def get_tmpfile(self, content=None):
        fd, file = mkstemp()
        os.close(fd)
        self.tmpfiles.append(file)
        if content is not None:
            with open(file, 'w') as f:
                f.write(content)
        return file

    @classmethod
    def _create_circus(cls, callable_path, plugins=None, stats=False,
                       async=False, arbiter_kw=None, **kw):
        resolve_name(callable_path)   # used to check the callable
        fd, testfile = mkstemp()
        os.close(fd)
        wdir = os.path.dirname(__file__)
        args = ['generic.py', callable_path, testfile]
        worker = {'cmd': _CMD, 'args': args, 'working_dir': wdir,
                  'name': 'test', 'graceful_timeout': 2}
        worker.update(kw)
        if not arbiter_kw:
            arbiter_kw = {}
        debug = arbiter_kw['debug'] = kw.get('debug',
                                             arbiter_kw.get('debug', False))
        # -1 => no periodic callback to manage_watchers by default
        arbiter_kw['check_delay'] = kw.get('check_delay',
                                           arbiter_kw.get('check_delay', -1))

        _gp = get_available_port
        arbiter_kw['controller'] = "tcp://127.0.0.1:%d" % _gp()
        arbiter_kw['pubsub_endpoint'] = "tcp://127.0.0.1:%d" % _gp()
        arbiter_kw['multicast_endpoint'] = "udp://237.219.251.97:12027"

        if stats:
            arbiter_kw['statsd'] = True
            arbiter_kw['stats_endpoint'] = "tcp://127.0.0.1:%d" % _gp()
            arbiter_kw['statsd_close_outputs'] = not debug

        if async:
            arbiter_kw['background'] = False
            arbiter_kw['loop'] = get_ioloop()
        else:
            arbiter_kw['background'] = True

        arbiter = cls.arbiter_factory([worker], plugins=plugins, **arbiter_kw)
        cls.arbiters.append(arbiter)
        return testfile, arbiter

    def _run_circus(self, callable_path, plugins=None, stats=False, **kw):

        testfile, arbiter = TestCircus._create_circus(callable_path,
                                                      plugins, stats, **kw)
        self.arbiters.append(arbiter)
        self.files.append(testfile)
        return testfile

    @tornado.gen.coroutine
    def _stop_runners(self):
        for arbiter in self.arbiters:
            yield arbiter.stop()
        self.arbiters = []

    @tornado.gen.coroutine
    def call(self, _cmd, **props):
        msg = make_message(_cmd, **props)
        resp = yield self.cli.call(msg)
        raise tornado.gen.Return(resp)


def profile(func):
    """Can be used to dump profile stats"""
    def _profile(*args, **kw):
        profiler = cProfile.Profile()
        try:
            return profiler.runcall(func, *args, **kw)
        finally:
            pstats.Stats(profiler).sort_stats('time').print_stats(30)
    return _profile


class Process(object):

    def __init__(self, testfile):
        self.testfile = testfile
        # init signal handling
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)
        signal.signal(signal.SIGCHLD, self.handle_chld)
        self.alive = True

    def _write(self, msg):
        with open(self.testfile, 'a+') as f:
            f.write(msg)

    def handle_quit(self, *args):
        self._write('QUIT')
        self.alive = False

    def handle_chld(self, *args):
        self._write('CHLD')
        return

    def run(self):
        self._write('START')
        while self.alive:
            sleep(0.1)
        self._write('STOP')


def run_process(test_file):
    process = Process(test_file)
    process.run()
    return 1


def has_gevent():
    try:
        import gevent       # NOQA
        return True
    except ImportError:
        return False


def has_circusweb():
    try:
        import circusweb       # NOQA
        return True
    except ImportError:
        return False


class TimeoutException(Exception):
    pass


def poll_for_callable(func, *args, **kwargs):
    """Replay to update the status during timeout seconds."""
    timeout = 5

    if 'timeout' in kwargs:
        timeout = kwargs.pop('timeout')

    start = time()
    last_exception = None
    while time() - start < timeout:
        try:
            func_args = []
            for arg in args:
                if callable(arg):
                    func_args.append(arg())
                else:
                    func_args.append(arg)
            func(*func_args)
        except AssertionError as e:
            last_exception = e
            sleep(0.1)
        else:
            return True
    raise last_exception or AssertionError('No exception triggered yet')


def poll_for(filename, needles, timeout=5):
    """Poll a file for a given string.

    Raises a TimeoutException if the string isn't found after timeout seconds
    of polling.

    """
    if isinstance(needles, str):
        needles = [needles]

    start = time()
    needle = content = None
    while time() - start < timeout:
        with open(filename) as f:
            content = f.read()
        for needle in needles:
            if needle in content:
                return True
        # When using gevent this will make sure the redirector greenlets are
        # scheduled.
        sleep(0.1)
    raise TimeoutException('Timeout polling "%s" for "%s". Content: %s' % (
        filename, needle, content))


@tornado.gen.coroutine
def async_poll_for(filename, needles, timeout=5):
    """Async version of poll_for
    """
    if isinstance(needles, str):
        needles = [needles]

    start = time()
    needle = content = None
    while time() - start < timeout:
        with open(filename) as f:
            content = f.read()
        for needle in needles:
            if needle in content:
                raise tornado.gen.Return(True)
        yield tornado_sleep(0.1)
    raise TimeoutException('Timeout polling "%s" for "%s". Content: %s' % (
        filename, needle, content))


def truncate_file(filename):
    """Truncate a file (empty it)."""
    open(filename, 'w').close()  # opening as 'w' overwrites the file


def run_plugin(klass, config, plugin_info_callback=None, duration=300,
               endpoint=DEFAULT_ENDPOINT_DEALER,
               pubsub_endpoint=DEFAULT_ENDPOINT_SUB):
    check_delay = 1
    ssh_server = None

    class _Statsd(object):
        gauges = []
        increments = defaultdict(int)

        def gauge(self, name, value):
            self.gauges.append((name, value))

        def increment(self, name):
            self.increments[name] += 1

        def stop(self):
            pass

    _statsd = _Statsd()
    plugin = klass(endpoint, pubsub_endpoint, check_delay, ssh_server,
                   **config)

    # make sure we close the existing statsd client
    if hasattr(plugin, 'statsd'):
        plugin.statsd.stop()

    plugin.statsd = _statsd

    deadline = time() + (duration / 1000.)
    plugin.loop.add_timeout(deadline, plugin.stop)

    plugin.start()
    try:
        if plugin_info_callback:
            plugin_info_callback(plugin)
    finally:
        plugin.stop()

    return _statsd


@tornado.gen.coroutine
def async_run_plugin(klass, config, plugin_info_callback, duration=300,
                     endpoint=DEFAULT_ENDPOINT_DEALER,
                     pubsub_endpoint=DEFAULT_ENDPOINT_SUB):
    queue = multiprocessing.Queue()
    plugin_info_callback = functools.partial(plugin_info_callback, queue)
    circusctl_process = multiprocessing.Process(
        target=run_plugin,
        args=(klass, config, plugin_info_callback, duration,
              endpoint, pubsub_endpoint))
    circusctl_process.start()

    while queue.empty():
        yield tornado_sleep(.1)

    result = queue.get()
    raise tornado.gen.Return(result)


class FakeProcess(object):

    def __init__(self, pid, status, started=1, age=1):
        self.status = status
        self.pid = pid
        self.started = started
        self.age = age
        self.stopping = False

    def is_alive(self):
        return True

    def stop(self):
        pass


class MagicMockFuture(mock.MagicMock, tornado.concurrent.Future):

    def cancel(self):
        return False

    def cancelled(self):
        return False

    def running(self):
        return False

    def done(self):
        return True

    def result(self, timeout=None):
        return None

    def exception(self, timeout=None):
        return None

    def add_done_callback(self, fn):
        fn(self)

    def set_result(self, result):
        pass

    def set_exception(self, exception):
        pass

########NEW FILE########
__FILENAME__ = test_arbiter
import os
import socket
import sys
import tornado
from tempfile import mkstemp
from time import time
import zmq.utils.jsonapi as json
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse  # NOQA

from circus.arbiter import Arbiter
from circus.client import CircusClient
from circus.plugins import CircusPlugin
from circus.tests.support import TestCircus, async_poll_for, truncate_file
from circus.tests.support import EasyTestSuite, skipIf, get_ioloop
from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_MULTICAST,
                         DEFAULT_ENDPOINT_SUB)
from circus.watcher import Watcher
from circus.tests.support import (has_circusweb, poll_for_callable,
                                  get_available_port)
from circus import watcher as watcher_mod
from circus.py3compat import s


_GENERIC = os.path.join(os.path.dirname(__file__), 'generic.py')


class Plugin(CircusPlugin):
    name = 'dummy'

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        with open(self.config['file'], 'a+') as f:
            f.write('PLUGIN STARTED')

    def handle_recv(self, data):
        topic, msg = data
        topic_parts = s(topic).split(".")
        watcher = topic_parts[1]
        action = topic_parts[2]
        with open(self.config['file'], 'a+') as f:
            f.write('%s:%s' % (watcher, action))


class TestTrainer(TestCircus):

    def setUp(self):
        super(TestTrainer, self).setUp()
        self.old = watcher_mod.tornado_sleep

    def tearDown(self):
        watcher_mod.tornado_sleep = self.old
        super(TestTrainer, self).tearDown()

    @tornado.gen.coroutine
    def _call(self, _cmd, **props):
        resp = yield self.call(_cmd, waiting=True, **props)
        raise tornado.gen.Return(resp)

    @tornado.testing.gen_test
    def test_numwatchers(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("numwatchers")
        self.assertTrue(resp.get("numwatchers") >= 1)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_numprocesses(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("numprocesses")
        self.assertTrue(resp.get("numprocesses") >= 1)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_processes(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = "test_processes"
        resp = yield self._call("add", name=name,
                                cmd=self._get_cmd(),
                                start=True,
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("list", name=name)
        self.assertEqual(len(resp.get('pids')), 1)

        resp = yield self._call("incr", name=name)
        self.assertEqual(resp.get('numprocesses'), 2)

        resp = yield self._call("incr", name=name, nb=2)
        self.assertEqual(resp.get('numprocesses'), 4)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_watchers(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = "test_watchers"
        resp = yield self._call("add", name=name,
                                cmd=self._get_cmd(),
                                start=True,
                                options=self._get_options())

        resp = yield self._call("list")
        self.assertTrue(name in resp.get('watchers'))
        yield self.stop_arbiter()

    def _get_cmd(self):
        fd, testfile = mkstemp()
        os.close(fd)
        cmd = '%s %s %s %s' % (
            sys.executable, _GENERIC,
            'circus.tests.support.run_process',
            testfile)

        return cmd

    def _get_cmd_args(self):
        cmd = sys.executable
        args = [_GENERIC, 'circus.tests.support.run_process']
        return cmd, args

    def _get_options(self, **kwargs):
        if 'graceful_timeout' not in kwargs:
            kwargs['graceful_timeout'] = 4
        return kwargs

    @tornado.testing.gen_test
    def test_add_watcher(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("add", name="test_add_watcher",
                                cmd=self._get_cmd(),
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher_arbiter_stopped(self):
        yield self.start_arbiter(graceful_timeout=0)
        # stop the arbiter
        resp = yield self._call("stop")
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("add",
                                name="test_add_watcher_arbiter_stopped",
                                cmd=self._get_cmd(),
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("start")
        self.assertEqual(resp.get("status"), "ok")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher1(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = "test_add_watcher1"
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         options=self._get_options())
        resp = yield self._call("list")
        self.assertTrue(name in resp.get('watchers'))
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher2(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("numwatchers")
        before = resp.get("numwatchers")

        name = "test_add_watcher2"
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         options=self._get_options())
        resp = yield self._call("numwatchers")
        self.assertEqual(resp.get("numwatchers"), before + 1)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher_already_exists(self):
        yield self.start_arbiter(graceful_timeout=0)
        options = {'name': 'test_add_watcher3', 'cmd': self._get_cmd(),
                   'options': self._get_options()}

        yield self._call("add", **options)
        resp = yield self._call("add", **options)
        self.assertTrue(resp.get('status'), 'error')
        self.assertTrue(self.arbiter._exclusive_running_command is None)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher4(self):
        yield self.start_arbiter(graceful_timeout=0)
        cmd, args = self._get_cmd_args()
        resp = yield self._call("add", name="test_add_watcher4",
                                cmd=cmd, args=args,
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher5(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = "test_add_watcher5"
        cmd, args = self._get_cmd_args()
        resp = yield self._call("add", name=name,
                                cmd=cmd, args=args,
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("start", name=name)
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("status", name=name)
        self.assertEqual(resp.get("status"), "active")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher6(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = 'test_add_watcher6'
        cmd, args = self._get_cmd_args()
        resp = yield self._call("add", name=name, cmd=cmd, args=args,
                                start=True, options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("status", name=name)
        self.assertEqual(resp.get("status"), "active")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher7(self):
        yield self.start_arbiter(graceful_timeout=0)
        cmd, args = self._get_cmd_args()
        name = 'test_add_watcher7'
        resp = yield self._call("add", name=name, cmd=cmd, args=args,
                                start=True,
                                options=self._get_options(send_hup=True))
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("status", name=name)
        self.assertEqual(resp.get("status"), "active")

        resp = yield self._call("options", name=name)
        options = resp.get('options', {})
        self.assertEqual(options.get("send_hup"), True)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_rm_watcher(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = 'test_rm_watcher'
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         options=self._get_options())
        resp = yield self._call("numwatchers")
        before = resp.get("numwatchers")
        yield self._call("rm", name=name)
        resp = yield self._call("numwatchers")
        self.assertEqual(resp.get("numwatchers"), before - 1)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def _test_stop(self):
        resp = yield self._call("quit")
        self.assertEqual(resp.get("status"), "ok")

    @tornado.testing.gen_test
    def test_reload(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("reload")
        self.assertEqual(resp.get("status"), "ok")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_reload1(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = 'test_reload1'
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         start=True, options=self._get_options())

        resp = yield self._call("list", name=name)
        processes1 = resp.get('pids')

        truncate_file(self.test_file)  # clean slate

        yield self._call("reload")
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted

        resp = yield self._call("list", name=name)
        processes2 = resp.get('pids')

        self.assertNotEqual(processes1, processes2)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_reload_sequential(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = 'test_reload_sequential'
        options = self._get_options(numprocesses=4)
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         start=True, options=options)
        resp = yield self._call("list", name=name)
        processes1 = resp.get('pids')
        truncate_file(self.test_file)  # clean slate
        yield self._call("reload", sequential=True)
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted
        resp = yield self._call("list", name=name)
        processes2 = resp.get('pids')
        self.assertNotEqual(processes1, processes2)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_reload2(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("list", name="test")
        processes1 = resp.get('pids')
        self.assertEqual(len(processes1), 1)

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted

        resp = yield self._call("list", name="test")
        processes2 = resp.get('pids')
        self.assertEqual(len(processes2), 1)
        self.assertNotEqual(processes1[0], processes2[0])
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_reload_wid_1_worker(self):
        yield self.start_arbiter(graceful_timeout=0)

        resp = yield self._call("stats", name="test")
        processes1 = list(resp['info'].keys())
        self.assertEqual(len(processes1), 1)
        wids1 = [resp['info'][process]['wid'] for process in processes1]
        self.assertEqual(wids1, [1])

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted

        resp = yield self._call("stats", name="test")
        processes2 = list(resp['info'].keys())
        self.assertEqual(len(processes2), 1)
        self.assertNotEqual(processes1, processes2)
        wids2 = [resp['info'][process]['wid'] for process in processes2]
        self.assertEqual(wids2, [2])

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted

        resp = yield self._call("stats", name="test")
        processes3 = list(resp['info'].keys())
        self.assertEqual(len(processes3), 1)
        self.assertNotIn(processes3[0], (processes1[0], processes2[0]))
        wids3 = [resp['info'][process]['wid'] for process in processes3]
        self.assertEqual(wids3, [1])

        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_reload_wid_4_workers(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("incr", name="test", nb=3)
        self.assertEqual(resp.get('numprocesses'), 4)

        resp = yield self._call("stats", name="test")
        processes1 = list(resp['info'].keys())
        self.assertEqual(len(processes1), 4)
        wids1 = set(resp['info'][process]['wid'] for process in processes1)
        self.assertSetEqual(wids1, set([1, 2, 3, 4]))

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted

        resp = yield self._call("stats", name="test")
        processes2 = list(resp['info'].keys())
        self.assertEqual(len(processes2), 4)
        self.assertEqual(len(set(processes1) & set(processes2)), 0)
        wids2 = set(resp['info'][process]['wid'] for process in processes2)
        self.assertSetEqual(wids2, set([5, 6, 7, 8]))

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted

        resp = yield self._call("stats", name="test")
        processes3 = list(resp['info'].keys())
        self.assertEqual(len(processes3), 4)
        self.assertEqual(len(set(processes1) & set(processes3)), 0)
        self.assertEqual(len(set(processes2) & set(processes3)), 0)
        wids3 = set([resp['info'][process]['wid'] for process in processes3])
        self.assertSetEqual(wids3, set([1, 2, 3, 4]))

        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_stop_watchers(self):
        yield self.start_arbiter(graceful_timeout=0)
        yield self._call("stop")
        resp = yield self._call("status", name="test")
        self.assertEqual(resp.get("status"), "stopped")

        yield self._call("start")

        resp = yield self._call("status", name="test")
        self.assertEqual(resp.get("status"), 'active')
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_stop_watchers3(self):
        yield self.start_arbiter(graceful_timeout=0)
        cmd, args = self._get_cmd_args()
        name = "test_stop_watchers3"
        resp = yield self._call("add", name=name, cmd=cmd, args=args,
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("start", name=name)
        self.assertEqual(resp.get("status"), "ok")

        yield self._call("stop", name=name)
        resp = yield self._call("status", name=name)
        self.assertEqual(resp.get('status'), "stopped")

        yield self._call("start", name=name)
        resp = yield self._call("status", name=name)
        self.assertEqual(resp.get('status'), "active")
        yield self.stop_arbiter()

    # XXX TODO
    @tornado.testing.gen_test
    def _test_plugins(self):

        fd, datafile = mkstemp()
        os.close(fd)

        # setting up a circusd with a plugin
        dummy_process = 'circus.tests.support.run_process'
        plugin = 'circus.tests.test_arbiter.Plugin'
        plugins = [{'use': plugin, 'file': datafile}]
        self._run_circus(dummy_process, plugins=plugins)

        # doing a few operations
        def nb_processes():
            return len(cli.send_message('list', name='test').get('pids'))

        def incr_processes():
            return cli.send_message('incr', name='test')

        # wait for the plugin to be started
        self.assertTrue(async_poll_for(datafile, 'PLUGIN STARTED'))

        cli = CircusClient()
        self.assertEqual(nb_processes(), 1)
        incr_processes()
        self.assertEqual(nb_processes(), 2)
        # wait for the plugin to receive the signal
        self.assertTrue(async_poll_for(datafile, 'test:spawn'))
        truncate_file(datafile)
        incr_processes()
        self.assertEqual(nb_processes(), 3)
        # wait for the plugin to receive the signal
        self.assertTrue(async_poll_for(datafile, 'test:spawn'))

    # XXX TODO
    @tornado.testing.gen_test
    def _test_singleton(self):
        self._stop_runners()

        dummy_process = 'circus.tests.support.run_process'
        self._run_circus(dummy_process, singleton=True)
        cli = CircusClient()

        # adding more than one process should fail
        res = cli.send_message('incr', name='test')
        self.assertEqual(res['numprocesses'], 1)

    # TODO XXX
    @tornado.testing.gen_test
    def _test_udp_discovery(self):
        """test_udp_discovery: Test that when the circusd answer UDP call.

        """
        self._stop_runners()

        dummy_process = 'circus.tests.support.run_process'
        self._run_circus(dummy_process)

        ANY = '0.0.0.0'

        multicast_addr, multicast_port = urlparse(DEFAULT_ENDPOINT_MULTICAST)\
            .netloc.split(':')

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                             socket.IPPROTO_UDP)
        sock.bind((ANY, 0))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.sendto(json.dumps(''),
                    (multicast_addr, int(multicast_port)))

        timer = time()
        resp = False
        endpoints = []
        while time() - timer < 10:
            data, address = sock.recvfrom(1024)
            data = json.loads(data)
            endpoint = data.get('endpoint', "")

            if endpoint == DEFAULT_ENDPOINT_DEALER:
                resp = True
                break

            endpoints.append(endpoint)

        if not resp:
            print(endpoints)

        self.assertTrue(resp)

    # XXX TODO
    @tornado.testing.gen_test
    def _test_start_watchers_warmup_delay(self):
        yield self.start_arbiter()
        called = []

        @tornado.gen.coroutine
        def _sleep(duration):
            called.append(duration)
            loop = get_ioloop()
            yield tornado.gen.Task(loop.add_timeout, time() + duration)

        watcher_mod.tornado_sleep = _sleep

        watcher = MockWatcher(name='foo', cmd='sleep 1', priority=1)
        yield self.arbiter.start_watcher(watcher)

        self.assertTrue(called, [self.arbiter.warmup_delay])

        # now make sure we don't sleep when there is a autostart
        watcher = MockWatcher(name='foo', cmd='serve', priority=1,
                              autostart=False)
        yield self.arbiter.start_watcher(watcher)
        self.assertTrue(called, [self.arbiter.warmup_delay])
        yield self.stop_arbiter()


class MockWatcher(Watcher):

    def start(self):
        self.started = True

    def spawn_process(self):
        self.processes[1] = 'dummy'


class TestArbiter(TestCircus):
    """
    Unit tests for the arbiter class to codify requirements within
    behavior.
    """
    @tornado.testing.gen_test
    def test_start_watcher(self):
        watcher = MockWatcher(name='foo', cmd='serve', priority=1)
        arbiter = Arbiter([], None, None, check_delay=-1)
        yield arbiter.start_watcher(watcher)
        self.assertTrue(watcher.is_active())

    def test_start_watchers_with_autostart(self):
        watcher = MockWatcher(name='foo', cmd='serve', priority=1,
                              autostart=False)
        arbiter = Arbiter([], None, None, check_delay=-1)
        arbiter.start_watcher(watcher)
        self.assertFalse(getattr(watcher, 'started', False))

    @tornado.testing.gen_test
    def test_add_watcher(self):
        controller = "tcp://127.0.0.1:%d" % get_available_port()
        sub = "tcp://127.0.0.1:%d" % get_available_port()
        arbiter = Arbiter([], controller, sub, loop=get_ioloop(),
                          check_delay=-1)
        arbiter.add_watcher('foo', 'sleep 5')
        try:
            yield arbiter.start()
            self.assertEqual(arbiter.watchers[0].status(), 'active')
        finally:
            yield arbiter.stop()

    @tornado.testing.gen_test
    def test_start_arbiter_with_autostart(self):
        arbiter = Arbiter([], DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB,
                          loop=get_ioloop(),
                          check_delay=-1)
        arbiter.add_watcher('foo', 'sleep 5', autostart=False)
        try:
            yield arbiter.start()
            self.assertEqual(arbiter.watchers[0].status(), 'stopped')
        finally:
            yield arbiter.stop()


@skipIf(not has_circusweb(), 'Tests for circus-web')
class TestCircusWeb(TestCircus):

    @tornado.testing.gen_test
    def test_circushttpd(self):
        controller = "tcp://127.0.0.1:%d" % get_available_port()
        sub = "tcp://127.0.0.1:%d" % get_available_port()

        arbiter = Arbiter([], controller, sub, loop=get_ioloop(),
                          check_delay=-1, httpd=True, debug=True)
        self.arbiters.append(arbiter)
        try:
            yield arbiter.start()
            poll_for_callable(self.assertDictEqual,
                              arbiter.statuses, {'circushttpd': 'active'})
        finally:
            yield arbiter.stop()

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_circusctl
import subprocess
import sys
import shlex
from multiprocessing import Process, Queue

from tornado.testing import gen_test
from tornado.gen import coroutine, Return

from circus.circusctl import USAGE, VERSION, CircusCtl
from circus.tests.support import (TestCircus, async_poll_for, EasyTestSuite,
                                  skipIf, DEBUG)
from circus.util import tornado_sleep, DEFAULT_ENDPOINT_DEALER
from circus.py3compat import b, s


def run_ctl(args, queue=None, stdin='', endpoint=DEFAULT_ENDPOINT_DEALER):
    cmd = '%s -m circus.circusctl' % sys.executable
    if '--endpoint' not in args:
        args = '--endpoint %s ' % endpoint + args

    proc = subprocess.Popen(cmd.split() + shlex.split(args),
                            stdin=subprocess.PIPE if stdin else None,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate(b(stdin) if stdin else None)
    stdout = s(stdout)
    stderr = s(stderr)
    if queue:
        queue.put(stderr)
        queue.put(stdout)
    try:
        import gevent
        if hasattr(gevent, 'shutdown'):
            gevent.shutdown()
    except ImportError:
        pass
    return stdout, stderr


@coroutine
def async_run_ctl(args, stdin='', endpoint=DEFAULT_ENDPOINT_DEALER):
    """
    Start a process that will start the actual circusctl process and poll its
    ouput, via a queue, without blocking the I/O loop. We do this to avoid
    blocking the main thread while waiting for circusctl output, so that the
    arbiter will be able to respond to requests coming from circusctl.
    """
    queue = Queue()
    circusctl_process = Process(target=run_ctl,
                                args=(args, queue, stdin,
                                      endpoint))
    circusctl_process.start()
    while queue.empty():
        yield tornado_sleep(.1)
    stderr = queue.get()
    stdout = queue.get()
    raise Return((stdout, stderr))


class CommandlineTest(TestCircus):

    @skipIf(DEBUG, 'Py_DEBUG=1')
    def test_help_switch_no_command(self):
        stdout, stderr = run_ctl('--help')
        if stderr:
            self.assertIn('UserWarning', stderr)
        output = stdout.splitlines()
        self.assertEqual(output[0], 'usage: ' + USAGE)
        self.assertEqual(output[2], 'Controls a Circus daemon')
        self.assertEqual(output[4], 'Commands:')

    def test_help_invalid_command(self):
        stdout, stderr = run_ctl('foo')
        self.assertEqual(stdout, '')
        err = stderr.splitlines()
        while err and 'import' in err[0]:
            del err[0]
        self.assertEqual(err[0], 'usage: ' + USAGE)
        self.assertEqual(err[1],
                         'circusctl.py: error: unrecognized arguments: foo')

    @skipIf(DEBUG, 'Py_DEBUG=1')
    def test_help_for_add_command(self):
        stdout, stderr = run_ctl('--help add')
        if stderr:
            self.assertIn('UserWarning', stderr)
        self.assertEqual(stdout.splitlines()[0], 'Add a watcher')

    @skipIf(DEBUG, 'Py_DEBUG=1')
    @gen_test
    def test_add(self):
        yield self.start_arbiter()
        async_poll_for(self.test_file, 'START')
        ep = self.arbiter.endpoint

        stdout, stderr = yield async_run_ctl('add test2 "sleep 1"',
                                             endpoint=ep)
        if stderr:
            self.assertIn('UserWarning', stderr)
        self.assertEqual(stdout, 'ok\n')

        stdout, stderr = yield async_run_ctl('status test2',
                                             endpoint=ep)
        if stderr:
            self.assertIn('UserWarning', stderr)
        self.assertEqual(stdout, 'stopped\n')
        yield self.stop_arbiter()

    @skipIf(DEBUG, 'Py_DEBUG=1')
    @gen_test
    def test_add_start(self):
        yield self.start_arbiter()
        async_poll_for(self.test_file, 'START')
        ep = self.arbiter.endpoint

        stdout, stderr = yield async_run_ctl('add --start test2 "sleep 1"',
                                             endpoint=ep)
        if stderr:
            self.assertIn('UserWarning', stderr)
        self.assertEqual(stdout, 'ok\n')
        stdout, stderr = yield async_run_ctl('status test2',
                                             endpoint=ep)
        if stderr:
            self.assertIn('UserWarning', stderr)
        self.assertEqual(stdout, 'active\n')
        yield self.stop_arbiter()


class CLITest(TestCircus):

    @coroutine
    def run_ctl(self, command='', endpoint=DEFAULT_ENDPOINT_DEALER):
        """Send the given command to the CLI, and ends with EOF."""
        if command:
            command += '\n'
        stdout, stderr = yield async_run_ctl('', command + 'EOF\n',
                                             endpoint=endpoint)
        raise Return((stdout, stderr))

    @skipIf(DEBUG, 'Py_DEBUG=1')
    @gen_test
    def test_launch_cli(self):
        yield self.start_arbiter()
        async_poll_for(self.test_file, 'START')

        stdout, stderr = yield self.run_ctl(endpoint=self.arbiter.endpoint)
        if stderr:
            self.assertIn('UserWarning', stderr)
        output = stdout.splitlines()
        self.assertEqual(output[0], VERSION)
        # strip of term escape characters, if any
        prompt = output[2][-len(CircusCtl.prompt):]
        self.assertEqual(prompt, CircusCtl.prompt)

        yield self.stop_arbiter()

    def test_cli_help(self):
        stdout, stderr = yield self.run_ctl('help')
        self.assertEqual(stderr, '')
        prompt = stdout.splitlines()
        # first two lines are VERSION and prompt, followed by a blank line
        self.assertEqual(prompt[3], "Documented commands (type help <topic>):")

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_circusd
import sys
import os
import tempfile
import six
from copy import copy

from circus.circusd import get_maxfd, daemonize, main
from circus import circusd
from circus.arbiter import Arbiter
from circus.util import REDIRECT_TO
from circus import util
from circus.tests.support import has_gevent, TestCase, skipIf, EasyTestSuite


CIRCUS_INI = os.path.join(os.path.dirname(__file__), 'config', 'circus.ini')


class TestCircusd(TestCase):

    def setUp(self):
        self.saved = dict(sys.modules)
        self.argv = copy(sys.argv)
        self.starter = Arbiter.start
        Arbiter.start = lambda x: None
        self.exit = sys.exit
        sys.exit = lambda x: None
        self._files = []
        self.fork = os.fork
        os.fork = self._forking
        self.setsid = os.setsid
        os.setsid = lambda: None
        self.forked = 0
        self.closerange = circusd.closerange
        circusd.closerange = lambda x, y: None
        self.open = os.open
        os.open = self._open
        self.dup2 = os.dup2
        os.dup2 = lambda x, y: None
        self.stop = Arbiter.stop
        Arbiter.stop = lambda x: None
        self.config = util.configure_logger
        circusd.configure_logger = util.configure_logger = self._logger

    def _logger(self, *args, **kw):
        pass

    def _open(self, path, *args, **kw):
        if path == REDIRECT_TO:
            return
        return self.open(path, *args, **kw)

    def tearDown(self):
        circusd.configure_logger = util.configure_logger = self.config
        Arbiter.stop = self.stop
        sys.argv = self.argv
        os.dup2 = self.dup2
        os.open = self.open
        circusd.closerange = self.closerange
        os.setsid = self.setsid
        sys.modules = self.saved
        Arbiter.start = self.starter
        sys.exit = self.exit
        os.fork = self.fork
        for file in self._files:
            if os.path.exists(file):
                os.remove(file)
        self.forked = 0

    def _forking(self):
        self.forked += 1
        return 0

    @skipIf('TRAVIS' in os.environ, 'Travis detected')
    @skipIf(not has_gevent(), "Only when Gevent is loaded")
    def test_daemon(self):
        # if gevent is loaded, we want to prevent
        # daemonize() to work
        self.assertRaises(ValueError, daemonize)

        for module in sys.modules.keys():
            if module.startswith('gevent'):
                del sys.modules[module]

        import gevent
        sys.modules['gevent'] = gevent
        self.assertRaises(ValueError, daemonize)

    def test_maxfd(self):
        max = get_maxfd()
        self.assertTrue(isinstance(max, six.integer_types))

    @skipIf(has_gevent(), "Gevent is loaded")
    def test_daemonize(self):
        daemonize()
        self.assertEqual(self.forked, 2)

    def _get_file(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        self._files.append(path)
        return path

    def test_main(self):

        def _check_pid(cls):
            self.assertTrue(os.path.exists(pid_file))

        Arbiter.start = _check_pid
        pid_file = self._get_file()
        sys.argv = ['circusd', CIRCUS_INI, '--pidfile', pid_file]
        main()
        self.assertFalse(os.path.exists(pid_file))

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_client
import time

from tornado.testing import gen_test
from tornado.gen import coroutine, Return

from circus.tests.support import TestCircus, EasyTestSuite
from circus.client import make_message, CallError
from circus.stream import QueueStream


class TestClient(TestCircus):

    @coroutine
    def status(self, cmd, **props):
        resp = yield self.call(cmd, **props)
        raise Return(resp.get('status'))

    @coroutine
    def numprocesses(self, cmd, **props):
        resp = yield self.call(cmd, waiting=True, **props)
        raise Return(resp.get('numprocesses'))

    @coroutine
    def numwatchers(self, cmd, **props):
        resp = yield self.call(cmd, **props)
        raise Return(resp.get('numwatchers'))

    @coroutine
    def set(self, name, **opts):
        resp = yield self.status("set", name=name, waiting=True, options=opts)
        raise Return(resp)

    @gen_test
    def test_client(self):
        # playing around with the watcher
        yield self.start_arbiter()
        msg = make_message("numwatchers")
        resp = yield self.cli.call(msg)
        self.assertEqual(resp.get("numwatchers"), 1)
        self.assertEqual((yield self.numprocesses("numprocesses")), 1)

        self.assertEqual((yield self.set("test", numprocesses=2)), 'ok')
        self.assertEqual((yield self.numprocesses("numprocesses")), 2)

        self.assertEqual((yield self.set("test", numprocesses=1)), 'ok')
        self.assertEqual((yield self.numprocesses("numprocesses")), 1)
        self.assertEqual((yield self.numwatchers("numwatchers")), 1)

        self.assertEqual((yield self.call("list")).get('watchers'), ['test'])
        self.assertEqual((yield self.numprocesses("incr", name="test")), 2)
        self.assertEqual((yield self.numprocesses("numprocesses")), 2)
        self.assertEqual((yield self.numprocesses("incr", name="test", nb=2)),
                         4)
        self.assertEqual((yield self.numprocesses("decr", name="test", nb=3)),
                         1)
        self.assertEqual((yield self.numprocesses("numprocesses")), 1)
        self.assertEqual((yield self.set("test", env={"test": 2})),
                         'error')
        self.assertEqual((yield self.set("test", env={"test": '2'})),
                         'ok')
        resp = yield self.call('get', name='test', keys=['env'])
        options = resp.get('options', {})
        self.assertEqual(options.get('env'), {'test': '2'})

        resp = yield self.call('stats', name='test')
        self.assertEqual(resp['status'], 'ok')

        resp = yield self.call('globaloptions', name='test')
        self.assertEqual(resp['options']['pubsub_endpoint'],
                         self.arbiter.pubsub_endpoint)
        yield self.stop_arbiter()


def long_hook(*args, **kw):
    time.sleep(5)


class TestWithHook(TestCircus):

    def run_with_hooks(self, hooks):
        self.stream = QueueStream()
        self.errstream = QueueStream()
        dummy_process = 'circus.tests.support.run_process'
        return self._create_circus(dummy_process,
                                   stdout_stream={'stream': self.stream},
                                   stderr_stream={'stream': self.errstream},
                                   hooks=hooks)

    def test_message_id(self):
        hooks = {'before_stop': ('circus.tests.test_client.long_hook', False)}
        testfile, arbiter = self.run_with_hooks(hooks)
        try:
            msg = make_message("numwatchers")
            resp = yield self.cli.call(msg)
            self.assertEqual(resp.get("numwatchers"), 1)

            # this should timeout
            self.assertRaises(CallError, self.cli.call, make_message("stop"))

            # and we should get back on our feet
            del arbiter.watchers[0].hooks['before_stop']

            while arbiter.watchers[0].status() != 'stopped':
                time.sleep(.1)

            resp = self.cli.call(make_message("numwatchers"))
            self.assertEqual(resp.get("numwatchers"), 1)
        finally:
            arbiter.stop()

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_command_decrproc
from circus.tests.test_command_incrproc import FakeArbiter
from circus.tests.support import TestCircus, EasyTestSuite
from circus.commands.decrproc import DecrProcess


class DecrProcTest(TestCircus):

    def test_decr_proc(self):
        cmd = DecrProcess()
        arbiter = FakeArbiter()
        self.assertTrue(arbiter.watchers[0].nb, 1)

        props = cmd.message('dummy')['properties']
        cmd.execute(arbiter, props)
        self.assertEqual(arbiter.watchers[0].nb, 0)

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_command_incrproc
from circus.tests.support import TestCircus, EasyTestSuite
from circus.commands.incrproc import IncrProc


class FakeWatcher(object):
    name = 'one'
    singleton = False
    nb = 1

    def info(self, *args):
        if len(args) == 1 and args[0] == 'meh':
            raise KeyError('meh')
        return 'yeah'

    process_info = info

    def incr(self, nb):
        self.nb += nb

    def decr(self, nb):
        self.nb -= nb


class FakeLoop(object):
    def add_callback(self, function):
        function()


class FakeArbiter(object):

    watcher_class = FakeWatcher

    def __init__(self):
        self.watchers = [self.watcher_class()]
        self.loop = FakeLoop()

    def get_watcher(self, name):
        return self.watchers[0]

    def stop_watchers(self, **options):
        self.watchers[:] = []

    def stop(self, **options):
        self.stop_watchers(**options)


class IncrProcTest(TestCircus):

    def test_incr_proc_message(self):
        cmd = IncrProc()
        message = cmd.message('dummy')
        self.assertTrue(message['properties'], {'name': 'dummy'})

        message = cmd.message('dummy', 3)
        props = sorted(message['properties'].items())
        self.assertEqual(props, [('name', 'dummy'), ('nb', 3)])

    def test_incr_proc(self):
        cmd = IncrProc()
        arbiter = FakeArbiter()
        size_before = arbiter.watchers[0].nb

        props = cmd.message('dummy', 3)['properties']
        cmd.execute(arbiter, props)
        self.assertEqual(arbiter.watchers[0].nb, size_before + 3)

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_command_list
from circus.tests.support import TestCircus, EasyTestSuite
from circus.commands.list import List


class ListCommandTest(TestCircus):

    def test_list_watchers(self):
        cmd = List()
        self.assertTrue(
            cmd.console_msg({'watchers': ['foo', 'bar']}),
            'foo,bar')

    def test_list_processors(self):
        cmd = List()
        self.assertTrue(
            cmd.console_msg({'pids': [12, 13]}), '12,13')

    def test_list_error(self):
        cmd = List()
        self.assertTrue("error" in cmd.console_msg({'foo': 'bar'}))

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_command_quit
from circus.tests.test_command_incrproc import FakeArbiter
from circus.tests.support import TestCircus, EasyTestSuite
from circus.commands.quit import Quit


class QuitTest(TestCircus):
    def test_quit(self):
        cmd = Quit()
        arbiter = FakeArbiter()
        self.assertTrue(arbiter.watchers[0].nb, 1)
        props = cmd.message('dummy')['properties']
        cmd.execute(arbiter, props)
        self.assertEqual(len(arbiter.watchers), 0)

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_command_set
from circus.tests.support import TestCircus, EasyTestSuite
from circus.tests.test_command_incrproc import FakeArbiter as _FakeArbiter
from circus.commands.set import Set


class FakeWatcher(object):
    def __init__(self):
        self.actions = []
        self.options = {}

    def set_opt(self, key, val):
        self.options[key] = val

    def do_action(self, action):
        self.actions.append(action)


class FakeArbiter(_FakeArbiter):
    watcher_class = FakeWatcher


class SetTest(TestCircus):

    def test_set_stream(self):
        arbiter = FakeArbiter()
        cmd = Set()

        # setting streams
        props = cmd.message('dummy', 'stdout_stream.class', 'FileStream')
        props = props['properties']
        cmd.execute(arbiter, props)
        watcher = arbiter.watchers[0]
        self.assertEqual(watcher.options,
                         {'stdout_stream.class': 'FileStream'})
        self.assertEqual(watcher.actions, [0])

        # setting hooks
        props = cmd.message('dummy', 'hooks.before_start', 'some.hook')
        props = props['properties']
        cmd.execute(arbiter, props)
        watcher = arbiter.watchers[0]
        self.assertEqual(watcher.options['hooks.before_start'],
                         'some.hook')
        self.assertEqual(watcher.actions, [0, 0])

        # we can also set several hooks at once
        props = cmd.message('dummy', 'hooks',
                            'before_start:some,after_start:hook')
        props = props['properties']
        cmd.execute(arbiter, props)
        watcher = arbiter.watchers[0]
        self.assertEqual(watcher.options['hooks.before_start'],
                         'some')
        self.assertEqual(watcher.options['hooks.after_start'],
                         'hook')

    def test_set_args(self):
        arbiter = FakeArbiter()
        cmd = Set()

        props = cmd.message('dummy2', 'args', '--arg1 1 --arg2 2')
        props = props['properties']
        cmd.execute(arbiter, props)
        watcher = arbiter.watchers[0]
        self.assertEqual(watcher.options['args'], '--arg1 1 --arg2 2')

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_command_signal
import sys
import time
import signal
import multiprocessing
import tornado

from circus.tests.support import TestCircus, EasyTestSuite, TimeoutException
from circus.client import AsyncCircusClient
from circus.stream import QueueStream, Empty
from circus.util import tornado_sleep
from circus.py3compat import s


exiting = False
channels = {0: [], 1: [], 2: [], 3: []}


def run_process(child_id, test_file=None):
    def send(msg):
        sys.stdout.write('{0}:{1}\n'.format(child_id, msg))
        sys.stdout.flush()

    names = {}
    signals = "HUP QUIT INT TERM USR1 USR2".split()
    exit_signals = set("INT TERM".split())
    children = []

    if not isinstance(child_id, int):
        child_id = 0
        for i in range(3):
            p = multiprocessing.Process(target=run_process, args=(i + 1,))
            p.daemon = True
            p.start()
            children.append(p)

    def callback(sig, frame=None):
        global exiting
        name = names[sig]
        send(name)
        if name in exit_signals:
            exiting = True

    for signal_name in signals:
        signum = getattr(signal, "SIG%s" % signal_name)
        names[signum] = signal_name
        signal.signal(signum, callback)

    send('STARTED')
    while not exiting:
        signal.pause()
    send('EXITING')


@tornado.gen.coroutine
def read_from_stream(stream, desired_channel, timeout=5):
    start = time.time()
    accumulator = ''
    while not channels[desired_channel] and time.time() - start < timeout:
        try:
            data = stream.get_nowait()
            data = s(data['data']).split('\n')
            accumulator += data.pop(0)
            if data:
                data.insert(0, accumulator)
                accumulator = data.pop()
                for line in data:
                    if len(line) > 1 and line[1] == ':':
                        channel, string = line.partition(':')[::2]
                        channels[int(channel)].append(string)
        except Empty:
            yield tornado_sleep(0.1)
    if channels[desired_channel]:
        raise tornado.gen.Return(channels[desired_channel].pop(0))
    raise TimeoutException('Timeout reading queue')


class SignalCommandTest(TestCircus):

    @tornado.testing.gen_test
    def test_handler(self):
        stream = QueueStream()
        cmd = 'circus.tests.test_command_signal.run_process'
        stdout_stream = {'stream': stream}
        stderr_stream = {'stream': stream}
        yield self.start_arbiter(cmd=cmd, stdout_stream=stdout_stream,
                                 stderr_stream=stderr_stream, stats=True,
                                 stop_signal=signal.SIGINT,
                                 debug=False)

        # waiting for data to appear in the queue
        data = yield read_from_stream(stream, 0)
        self.assertEqual('STARTED', data)

        # waiting for children
        data = yield read_from_stream(stream, 3)
        self.assertEqual('STARTED', data)
        data = yield read_from_stream(stream, 2)
        self.assertEqual('STARTED', data)
        data = yield read_from_stream(stream, 1)
        self.assertEqual('STARTED', data)

        # checking that our system is live and running
        client = AsyncCircusClient(endpoint=self.arbiter.endpoint)
        res = yield client.send_message('list')
        watchers = sorted(res['watchers'])
        self.assertEqual(['circusd-stats', 'test'], watchers)

        # send USR1 to parent only
        res = yield client.send_message('signal', name='test', signum='usr1')
        self.assertEqual(res['status'], 'ok')
        res = yield read_from_stream(stream, 0)
        self.assertEqual(res, 'USR1')

        # send USR2 to children only
        res = yield client.send_message('signal', name='test', signum='usr2',
                                        children=True)
        self.assertEqual(res['status'], 'ok')
        res = yield read_from_stream(stream, 1)
        self.assertEqual(res, 'USR2')
        res = yield read_from_stream(stream, 2)
        self.assertEqual(res, 'USR2')
        res = yield read_from_stream(stream, 3)
        self.assertEqual(res, 'USR2')

        # send HUP to parent and children
        res = yield client.send_message('signal', name='test', signum='hup',
                                        recursive=True)
        self.assertEqual(res['status'], 'ok')
        res = yield read_from_stream(stream, 0)
        self.assertEqual(res, 'HUP')
        res = yield read_from_stream(stream, 1)
        self.assertEqual(res, 'HUP')
        res = yield read_from_stream(stream, 2)
        self.assertEqual(res, 'HUP')
        res = yield read_from_stream(stream, 3)
        self.assertEqual(res, 'HUP')

        # stop process
        res = yield client.send_message('stop', name='test')
        self.assertEqual(res['status'], 'ok')
        res = yield read_from_stream(stream, 0)
        self.assertEqual(res, 'INT')
        res = yield read_from_stream(stream, 0)
        self.assertEqual(res, 'EXITING')
        res = yield read_from_stream(stream, 1)
        self.assertEqual(res, 'TERM')
        res = yield read_from_stream(stream, 1)
        self.assertEqual(res, 'EXITING')
        res = yield read_from_stream(stream, 2)
        self.assertEqual(res, 'TERM')
        res = yield read_from_stream(stream, 2)
        self.assertEqual(res, 'EXITING')
        res = yield read_from_stream(stream, 3)
        self.assertEqual(res, 'TERM')
        res = yield read_from_stream(stream, 3)
        self.assertEqual(res, 'EXITING')

        timeout = time.time() + 5
        stopped = False
        while time.time() < timeout:
            res = yield client.send_message('status', name='test')
            if res['status'] == 'stopped':
                stopped = True
                break
            self.assertEqual(res['status'], 'stopping')
        self.assertTrue(stopped)

        yield self.stop_arbiter()

test_suite = EasyTestSuite(__name__)

if __name__ == '__main__':
    run_process(*sys.argv)

########NEW FILE########
__FILENAME__ = test_command_stats
from circus.tests.support import TestCircus, EasyTestSuite
from circus.commands.stats import Stats, MessageError


_WANTED = """\
foo:
one: 1233  xx tarek false 132 132 13 123 xx
   1233  xx tarek false 132 132 13 123 xx
   1233  xx tarek false 132 132 13 123 xx"""


class FakeWatcher(object):
    name = 'one'

    def info(self, *args):
        if len(args) == 2 and args[0] == 'meh':
            raise KeyError('meh')
        return 'yeah'

    process_info = info


class FakeArbiter(object):
    watchers = [FakeWatcher()]

    def get_watcher(self, name):
        return FakeWatcher()


class StatsCommandTest(TestCircus):

    def test_console_msg(self):
        cmd = Stats()
        info = {'pid': '1233',
                'cmdline': 'xx',
                'username': 'tarek',
                'nice': 'false',
                'mem_info1': '132',
                'mem_info2': '132',
                'cpu': '13',
                'mem': '123',
                'ctime': 'xx'}

        info['children'] = [dict(info), dict(info)]

        res = cmd.console_msg({'name': 'foo',
                               'status': 'ok',
                               'info': {'one': info}})

        self.assertEqual(res, _WANTED)

    def test_execute(self):
        cmd = Stats()
        arbiter = FakeArbiter()
        res = cmd.execute(arbiter, {})
        self.assertEqual({'infos': {'one': 'yeah'}}, res)

        # info about a specific watcher
        props = {'name': 'one'}
        res = cmd.execute(arbiter, props)
        res = sorted(res.items())
        wanted = [('info', 'yeah'), ('name', 'one')]
        self.assertEqual(wanted, res)

        # info about a specific process
        props = {'process': '123', 'name': 'one'}
        res = cmd.execute(arbiter, props)
        res = sorted(res.items())
        wanted = [('info', 'yeah'), ('process', '123')]
        self.assertEqual(wanted, res)

        # info that breaks
        props = {'name': 'meh', 'process': 'meh'}
        self.assertRaises(MessageError, cmd.execute, arbiter, props)

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_config
import os
import signal
from mock import patch

from circus import logger
from circus.arbiter import Arbiter
from circus.config import get_config
from circus.watcher import Watcher
from circus.process import Process
from circus.sockets import CircusSocket
from circus.tests.support import TestCase, EasyTestSuite
from circus.util import replace_gnu_args
from circus.py3compat import PY2


HERE = os.path.join(os.path.dirname(__file__))
CONFIG_DIR = os.path.join(HERE, 'config')

_CONF = {
    'issue137': os.path.join(CONFIG_DIR, 'issue137.ini'),
    'include': os.path.join(CONFIG_DIR, 'include.ini'),
    'issue210': os.path.join(CONFIG_DIR, 'issue210.ini'),
    'issue310': os.path.join(CONFIG_DIR, 'issue310.ini'),
    'issue395': os.path.join(CONFIG_DIR, 'issue395.ini'),
    'hooks': os.path.join(CONFIG_DIR, 'hooks.ini'),
    'env_var': os.path.join(CONFIG_DIR, 'env_var.ini'),
    'env_section': os.path.join(CONFIG_DIR, 'env_section.ini'),
    'multiple_wildcard': os.path.join(CONFIG_DIR, 'multiple_wildcard.ini'),
    'empty_include': os.path.join(CONFIG_DIR, 'empty_include.ini'),
    'circus': os.path.join(CONFIG_DIR, 'circus.ini'),
    'nope': os.path.join(CONFIG_DIR, 'nope.ini'),
    'unexistant': os.path.join(CONFIG_DIR, 'unexistant.ini'),
    'issue442': os.path.join(CONFIG_DIR, 'issue442.ini'),
    'expand_vars': os.path.join(CONFIG_DIR, 'expand_vars.ini'),
    'issue546': os.path.join(CONFIG_DIR, 'issue546.ini'),
    'env_everywhere': os.path.join(CONFIG_DIR, 'env_everywhere.ini'),
    'copy_env': os.path.join(CONFIG_DIR, 'copy_env.ini'),
    'env_sensecase': os.path.join(CONFIG_DIR, 'env_sensecase.ini'),
    'issue567': os.path.join(CONFIG_DIR, 'issue567.ini'),
    'issue594': os.path.join(CONFIG_DIR, 'issue594.ini'),
    'reuseport': os.path.join(CONFIG_DIR, 'reuseport.ini'),
    'issue651': os.path.join(CONFIG_DIR, 'issue651.ini'),
    'issue665': os.path.join(CONFIG_DIR, 'issue665.ini'),
    'issue680': os.path.join(CONFIG_DIR, 'issue680.ini'),
}


def hook(watcher, hook_name):
    "Yeah that's me"
    pass


class TestConfig(TestCase):

    def setUp(self):
        self.saved = os.environ.copy()

    def tearDown(self):
        os.environ = self.saved

    def test_issue310(self):
        '''
        https://github.com/mozilla-services/circus/pull/310

        Allow $(circus.sockets.name) to be used in args.
        '''
        conf = get_config(_CONF['issue310'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        socket = CircusSocket.load_from_config(conf['sockets'][0])
        try:
            watcher.initialize(None, {'web': socket}, None)
            process = Process(watcher._nextwid, watcher.cmd,
                              args=watcher.args,
                              working_dir=watcher.working_dir,
                              shell=watcher.shell, uid=watcher.uid,
                              gid=watcher.gid, env=watcher.env,
                              rlimits=watcher.rlimits, spawn=False,
                              executable=watcher.executable,
                              use_fds=watcher.use_sockets,
                              watcher=watcher)

            sockets_fds = watcher._get_sockets_fds()
            formatted_args = process.format_args(sockets_fds=sockets_fds)

            fd = sockets_fds['web']
            self.assertEqual(formatted_args,
                             ['foo', '--fd', str(fd)])
        finally:
            socket.close()

    def test_issue137(self):
        conf = get_config(_CONF['issue137'])
        watcher = conf['watchers'][0]
        self.assertEqual(watcher['uid'], 'me')

    def test_issues665(self):
        '''
        https://github.com/mozilla-services/circus/pull/665

        Ensure args formatting when shell = True.
        '''
        conf = get_config(_CONF['issue665'])

        def load(watcher_conf):
            watcher = Watcher.load_from_config(watcher_conf.copy())
            process = Process(watcher._nextwid, watcher.cmd,
                              args=watcher.args,
                              working_dir=watcher.working_dir,
                              shell=watcher.shell, uid=watcher.uid,
                              gid=watcher.gid, env=watcher.env,
                              rlimits=watcher.rlimits, spawn=False,
                              executable=watcher.executable,
                              use_fds=watcher.use_sockets,
                              watcher=watcher)
            return process.format_args()

        import circus.process
        is_win = circus.process.is_win

        try:
            # force nix
            circus.process.is_win = lambda: False

            # without shell_args
            with patch.object(logger, 'warn') as mock_logger_warn:
                formatted_args = load(conf['watchers'][0])
                self.assertEqual(formatted_args, ['foo --fd'])
                self.assertFalse(mock_logger_warn.called)

            # with shell_args
            with patch.object(logger, 'warn') as mock_logger_warn:
                formatted_args = load(conf['watchers'][1])
                self.assertEqual(formatted_args,
                                 ['foo --fd', 'bar', 'baz', 'qux'])
                self.assertFalse(mock_logger_warn.called)

            # with shell_args but not shell
            with patch.object(logger, 'warn') as mock_logger_warn:
                formatted_args = load(conf['watchers'][2])
                self.assertEqual(formatted_args, ['foo', '--fd'])
                self.assertTrue(mock_logger_warn.called)

            # force win
            circus.process.is_win = lambda: True

            # without shell_args
            with patch.object(logger, 'warn') as mock_logger_warn:
                formatted_args = load(conf['watchers'][0])
                self.assertEqual(formatted_args, ['foo --fd'])
                self.assertFalse(mock_logger_warn.called)

            # with shell_args
            with patch.object(logger, 'warn') as mock_logger_warn:
                formatted_args = load(conf['watchers'][1])
                self.assertEqual(formatted_args, ['foo --fd'])
                self.assertTrue(mock_logger_warn.called)

            # with shell_args but not shell
            with patch.object(logger, 'warn') as mock_logger_warn:
                formatted_args = load(conf['watchers'][2])
                self.assertEqual(formatted_args, ['foo', '--fd'])
                self.assertTrue(mock_logger_warn.called)
        finally:
            circus.process.is_win = is_win

    def test_include_wildcards(self):
        conf = get_config(_CONF['include'])
        watchers = conf['watchers']
        self.assertEqual(len(watchers), 4)

    def test_include_multiple_wildcards(self):
        conf = get_config(_CONF['multiple_wildcard'])
        watchers = conf['watchers']
        self.assertEqual(len(watchers), 3)

    @patch.object(logger, 'warn')
    def test_empty_include(self, mock_logger_warn):
        """https://github.com/mozilla-services/circus/pull/473"""
        try:
            get_config(_CONF['empty_include'])
        except:
            self.fail('Non-existent includes should not raise')
        self.assertTrue(mock_logger_warn.called)

    def test_watcher_graceful_timeout(self):
        conf = get_config(_CONF['issue210'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        watcher.stop()

    def test_plugin_priority(self):
        arbiter = Arbiter.load_from_config(_CONF['issue680'])
        watchers = arbiter.iter_watchers()
        self.assertEqual(watchers[0].priority, 30)
        self.assertEqual(watchers[0].name, 'plugin:myplugin')
        self.assertEqual(watchers[1].priority, 20)
        self.assertEqual(watchers[1].cmd, 'sleep 20')
        self.assertEqual(watchers[2].priority, 10)
        self.assertEqual(watchers[2].cmd, 'sleep 10')

    def test_hooks(self):
        conf = get_config(_CONF['hooks'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        self.assertEqual(watcher.hooks['before_start'].__doc__, hook.__doc__)
        self.assertTrue('before_start' not in watcher.ignore_hook_failure)

    def test_watcher_env_var(self):
        conf = get_config(_CONF['env_var'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        self.assertEqual("%s:/bin" % os.getenv('PATH'), watcher.env['PATH'])
        watcher.stop()

    def test_env_section(self):
        conf = get_config(_CONF['env_section'])
        watchers_conf = {}
        for watcher_conf in conf['watchers']:
            watchers_conf[watcher_conf['name']] = watcher_conf
        watcher1 = Watcher.load_from_config(watchers_conf['watcher1'])
        watcher2 = Watcher.load_from_config(watchers_conf['watcher2'])

        self.assertEqual('lie', watcher1.env['CAKE'])
        self.assertEqual('cake', watcher2.env['LIE'])

        for watcher in [watcher1, watcher2]:
            self.assertEqual("%s:/bin" % os.getenv('PATH'),
                             watcher.env['PATH'])

        self.assertEqual('test1', watcher1.env['TEST1'])
        self.assertEqual('test1', watcher2.env['TEST1'])

        self.assertEqual('test2', watcher1.env['TEST2'])
        self.assertEqual('test2', watcher2.env['TEST2'])

        self.assertEqual('test3', watcher1.env['TEST3'])
        self.assertEqual('test3', watcher2.env['TEST3'])

    def test_issue395(self):
        conf = get_config(_CONF['issue395'])
        watcher = conf['watchers'][0]
        self.assertEqual(watcher['graceful_timeout'], 88)

    def test_pidfile(self):
        conf = get_config(_CONF['circus'])
        self.assertEqual(conf['pidfile'], 'pidfile')

    def test_logoutput(self):
        conf = get_config(_CONF['circus'])
        self.assertEqual(conf['logoutput'], 'logoutput')

    def test_loglevel(self):
        conf = get_config(_CONF['circus'])
        self.assertEqual(conf['loglevel'], 'debug')

    def test_override(self):
        conf = get_config(_CONF['multiple_wildcard'])
        watchers = conf['watchers']
        self.assertEqual(len(watchers), 3)
        watchers = conf['watchers']
        if PY2:
            watchers.sort()
        else:
            watchers = sorted(watchers, key=lambda a: a['__name__'])
        self.assertEqual(watchers[2]['env']['INI'], 'private.ini')
        self.assertEqual(conf['check_delay'], 555)

    def test_config_unexistant(self):
        self.assertRaises(IOError, get_config, _CONF['unexistant'])

    def test_variables_everywhere(self):
        os.environ['circus_stats_endpoint'] = 'tcp://0.0.0.0:9876'
        os.environ['circus_statsd'] = 'True'

        # these will be overriden
        os.environ['circus_uid'] = 'ubuntu'
        os.environ['circus_gid'] = 'ubuntu'

        conf = get_config(_CONF['issue442'])

        self.assertEqual(conf['stats_endpoint'], 'tcp://0.0.0.0:9876')
        self.assertTrue(conf['statsd'])
        self.assertEqual(conf['watchers'][0]['uid'], 'tarek')
        self.assertEqual(conf['watchers'][0]['gid'], 'root')

    def test_expand_vars(self):
        '''
        https://github.com/mozilla-services/circus/pull/554
        '''
        conf = get_config(_CONF['expand_vars'])
        watcher = conf['watchers'][0]
        self.assertEqual(watcher['stdout_stream']['filename'], '/tmp/echo.log')

    def test_dashes(self):
        conf = get_config(_CONF['issue546'])
        replaced = replace_gnu_args(conf['watchers'][0]['cmd'],
                                    sockets={'some-socket': 3})
        self.assertEqual(replaced, '../bin/chaussette --fd 3')

    def test_env_everywhere(self):
        conf = get_config(_CONF['env_everywhere'])

        self.assertEqual(conf['endpoint'], 'tcp://127.0.0.1:1234')
        self.assertEqual(conf['sockets'][0]['path'], '/var/run/broken.sock')
        self.assertEqual(conf['plugins'][0]['use'], 'bad.has.been.broken')

    def test_copy_env(self):
        # #564 make sure we respect copy_env
        os.environ['BAM'] = '1'
        conf = get_config(_CONF['copy_env'])
        for watcher in conf['watchers']:
            if watcher['name'] == 'watcher1':

                self.assertFalse('BAM' in watcher['env'])
            else:
                self.assertTrue('BAM' in watcher['env'])
            self.assertTrue('TEST1' in watcher['env'])

    def test_env_casesense(self):
        # #730 make sure respect case
        conf = get_config(_CONF['env_sensecase'])
        w = conf['watchers'][0]
        self.assertEqual(w['name'], 'webapp')
        self.assertTrue('http_proxy' in w['env'])
        self.assertEqual(w['env']['http_proxy'], 'http://localhost:8080')

        self.assertTrue('HTTPS_PROXY' in w['env'])
        self.assertEqual(w['env']['HTTPS_PROXY'], 'http://localhost:8043')

        self.assertTrue('FunKy_soUl' in w['env'])
        self.assertEqual(w['env']['FunKy_soUl'], 'scorpio')

    def test_issue567(self):
        os.environ['GRAVITY'] = 'down'
        conf = get_config(_CONF['issue567'])

        # make sure the global environment makes it into the cfg environment
        # even without [env] section
        self.assertEqual(conf['watchers'][0]['cmd'], 'down')

    def test_watcher_stop_signal(self):
        conf = get_config(_CONF['issue594'])
        self.assertEqual(conf['watchers'][0]['stop_signal'], signal.SIGINT)
        watcher = Watcher.load_from_config(conf['watchers'][0])
        watcher.stop()

    def test_socket_so_reuseport_yes(self):
        conf = get_config(_CONF['reuseport'])
        s1 = conf['sockets'][1]
        self.assertEqual(s1['so_reuseport'], True)

    def test_socket_so_reuseport_no(self):
        conf = get_config(_CONF['reuseport'])
        s1 = conf['sockets'][0]
        self.assertEqual(s1['so_reuseport'], False)

    def test_check_delay(self):
        conf = get_config(_CONF['issue651'])
        self.assertEqual(conf['check_delay'], 10.5)


test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_controller
from circus.tests.support import TestCase, EasyTestSuite, get_ioloop
from circus.controller import Controller
from circus.util import DEFAULT_ENDPOINT_MULTICAST
from circus import logger
import circus.controller

import mock


class TestController(TestCase):

    def test_add_job(self):
        arbiter = mock.MagicMock()

        class MockedController(Controller):
            called = False

            def _init_stream(self):
                pass  # NO OP

            def initialize(self):
                pass  # NO OP

            def dispatch(self, job):
                self.called = True
                self.loop.stop()

        loop = get_ioloop()
        controller = MockedController('endpoint', 'multicast_endpoint',
                                      mock.sentinel.context, loop, arbiter,
                                      check_delay=-1.0)

        controller.dispatch((None, 'something'))
        controller.start()
        loop.start()
        self.assertTrue(controller.called)

    def _multicast_side_effect_helper(self, side_effect):
        arbiter = mock.MagicMock()
        loop = mock.MagicMock()
        context = mock.sentinel.context

        controller = circus.controller.Controller(
            'endpoint', DEFAULT_ENDPOINT_MULTICAST, context, loop, arbiter
        )

        with mock.patch('circus.util.create_udp_socket') as m:
            m.side_effect = side_effect
            circus.controller.create_udp_socket = m

            with mock.patch.object(logger, 'warning') as mock_logger_warn:
                controller._init_multicast_endpoint()
                self.assertTrue(mock_logger_warn.called)

    def test_multicast_ioerror(self):
        self._multicast_side_effect_helper(IOError)

    def test_multicast_oserror(self):
        self._multicast_side_effect_helper(OSError)

    def test_multicast_valueerror(self):
        arbiter = mock.MagicMock()
        loop = mock.MagicMock()
        context = mock.sentinel.context

        wrong_multicast_endpoint = 'udp://127.0.0.1:12027'
        controller = Controller('endpoint', wrong_multicast_endpoint,
                                context, loop, arbiter)

        with mock.patch.object(logger, 'warning') as mock_logger_warn:
            controller._init_multicast_endpoint()
            self.assertTrue(mock_logger_warn.called)


test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_convert_option
from circus.tests.support import TestCase, EasyTestSuite

from circus.commands.util import convert_option, ArgumentError


class TestConvertOption(TestCase):

    def test_env(self):
        env = convert_option("env", {"port": "8080"})
        self.assertDictEqual({"port": "8080"}, env)

    def test_stdout_and_stderr_stream(self):
        expected_convertions = (
            ('stdout_stream.class', 'class', 'class'),
            ('stdout_stream.filename', 'file', 'file'),
            ('stdout_stream.other_option', 'other', 'other'),
            ('stdout_stream.refresh_time', '10', '10'),
            ('stdout_stream.max_bytes', '10', 10),
            ('stdout_stream.backup_count', '20', 20),
            ('stderr_stream.class', 'class', 'class'),
            ('stderr_stream.filename', 'file', 'file'),
            ('stderr_stream.other_option', 'other', 'other'),
            ('stderr_stream.refresh_time', '10', '10'),
            ('stderr_stream.max_bytes', '10', 10),
            ('stderr_stream.backup_count', '20', 20),
            ('stderr_stream.some_number', '99', '99'),
            ('stderr_stream.some_number_2', 99, 99),
        )

        for option, value, expected in expected_convertions:
            ret = convert_option(option, value)
            self.assertEqual(ret, expected)

    def test_hooks(self):
        ret = convert_option('hooks', 'before_start:one')
        self.assertEqual(ret, {'before_start': 'one'})

        ret = convert_option('hooks', 'before_start:one,after_start:two')

        self.assertEqual(ret['before_start'], 'one')
        self.assertEqual(ret['after_start'], 'two')

        self.assertRaises(ArgumentError, convert_option, 'hooks',
                          'before_start:one,DONTEXIST:two')

        self.assertRaises(ArgumentError, convert_option, 'hooks',
                          'before_start:one:two')

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_logging
try:
    from io import StringIO
    from io import BytesIO
except ImportError:
    from cStringIO import StringIO  # NOQA
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser  # NOQA
from circus.tests.support import TestCase
from circus.tests.support import EasyTestSuite
from circus.tests.support import skipIf
import os
import shutil
import tempfile
from pipes import quote as shell_escape_arg
import subprocess
import time
import yaml
import json
import logging.config
import sys


HERE = os.path.abspath(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(HERE, 'config', 'circus.ini')


def run_circusd(options=(), config=(), log_capture_path="log.txt",
                additional_files=()):
    options = list(options)
    additional_files = dict(additional_files)
    config_ini_update = {
        "watcher:touch.cmd": sys.executable,
        "watcher:touch.args": "-c \"open('workerstart.txt', 'w+').close()\"",
        "watcher:touch.respawn": 'False'
    }
    config_ini_update.update(dict(config))
    config_ini = ConfigParser()
    config_ini.read(CONFIG_PATH)
    for dottedkey in config_ini_update:
        section, key = dottedkey.split(".", 1)
        if section not in config_ini.sections():
            config_ini.add_section(section)
        config_ini.set(
            section, key, config_ini_update[dottedkey])
    temp_dir = tempfile.mkdtemp()
    try:
        circus_ini_path = os.path.join(temp_dir, "circus.ini")
        with open(circus_ini_path, "w") as fh:
            config_ini.write(fh)
        for relpath in additional_files:
            path = os.path.join(temp_dir, relpath)
            with open(path, "w") as fh:
                fh.write(additional_files[relpath])
        env = os.environ.copy()
        # We're going to run circus from a process with a different
        # cwd, so we need to make sure that Python will import the
        # current version of circus
        pythonpath = env.get('PYTHONPATH', '')
        pythonpath += ':%s' % os.path.abspath(
            os.path.join(HERE, os.pardir, os.pardir))
        env['PYTHONPATH'] = pythonpath
        argv = ["circus.circusd"] + options + [circus_ini_path]
        if sys.gettrace() is None:
            argv = [sys.executable, "-m"] + argv
        else:
            exe_dir = os.path.dirname(sys.executable)
            coverage = os.path.join(exe_dir, "coverage")
            if not os.path.isfile(coverage):
                coverage = "coverage"
            argv = [coverage, "run", "-p", "-m"] + argv

        child = subprocess.Popen(argv, cwd=temp_dir, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 env=env)
        try:
            touch_path = os.path.join(temp_dir, "workerstart.txt")
            while True:
                child.poll()
                if os.path.exists(touch_path):
                    break
                if child.returncode is not None:
                    break
                time.sleep(0.01)
        finally:
            child.terminate()
            child.wait()

        log_file_path = os.path.join(temp_dir, log_capture_path)

        try:
            if os.path.exists(log_file_path):
                with open(log_file_path, "r") as fh:
                    return fh.read()
            else:
                if child.stdout is not None:
                    raise Exception(child.stdout.read().decode("ascii"))
        finally:
            if child.stdout is not None:
                child.stdout.close()
            if child.stderr is not None:
                child.stderr.close()
            if child.stdin is not None:
                child.stdin.close()

        assert child.returncode == 0, \
            " ".join(shell_escape_arg(a) for a in argv)
    finally:
        for basename in sorted(os.listdir(temp_dir)):
            if basename.startswith(".coverage."):
                source = os.path.join(temp_dir, basename)
                target = os.path.abspath(basename)
                shutil.copy(source, target)
        shutil.rmtree(temp_dir)

EXAMPLE_YAML = """\
version: 1
disable_existing_loggers: false
formatters:
  simple:
    format: '%(asctime)s - %(name)s - [%(levelname)s] %(message)s'
handlers:
  logfile:
    class: logging.FileHandler
    filename: logoutput.txt
    level: DEBUG
    formatter: simple
loggers:
  circus:
    level: DEBUG
    handlers: [logfile]
    propagate: no
root:
  level: DEBUG
  handlers: [logfile]
"""

EXPECTED_LOG_MESSAGE = "[INFO] Arbiter now waiting for commands"


def logging_dictconfig_to_ini(config):
    assert config.get("version", 1) == 1, config
    ini = ConfigParser()
    ini.add_section("loggers")
    loggers = config.get("loggers", {})
    if "root" in config:
        loggers["root"] = config["root"]
    ini.set("loggers", "keys", ",".join(sorted(loggers.keys())))
    for logger in sorted(loggers.keys()):
        section = "logger_%s" % (logger.replace(".", "_"),)
        ini.add_section(section)
        for key, value in sorted(loggers[logger].items()):
            if key == "handlers":
                value = ",".join(value)
            if key == "propagate":
                value = "1" if value else "0"
            ini.set(section, key, value)
        ini.set(section, "qualname", logger)
    ini.add_section("handlers")
    handlers = config.get("handlers", {})
    ini.set("handlers", "keys", ",".join(sorted(handlers.keys())))
    for handler in sorted(handlers.keys()):
        section = "handler_%s" % (handler,)
        ini.add_section(section)
        args = []
        for key, value in sorted(handlers[handler].items()):
            if (handlers[handler]["class"] == "logging.FileHandler"
                    and key == "filename"):
                args.append(value)
            else:
                ini.set(section, key, value)
        ini.set(section, "args", repr(tuple(args)))
    ini.add_section("formatters")
    formatters = config.get("formatters", {})
    ini.set("formatters", "keys", ",".join(sorted(formatters.keys())))
    for formatter in sorted(formatters.keys()):
        section = "formatter_%s" % (formatter,)
        ini.add_section(section)
        for key, value in sorted(formatters[formatter].items()):
            ini.set(section, key, value)
    try:
        # Older Python (without io.StringIO/io.BytesIO) and Python 3 use
        # this code path.
        result = StringIO()
        ini.write(result)
        return result.getvalue()
    except TypeError:
        # Python 2.7 has io.StringIO and io.BytesIO but ConfigParser.write
        # has not been fixed to work with StringIO.
        result = BytesIO()
        ini.write(result)
        return result.getvalue().decode("ascii")


def hasDictConfig():
    return hasattr(logging.config, "dictConfig")


class TestLoggingConfig(TestCase):

    def test_loggerconfig_default_ini(self):
        logs = run_circusd(
            [], {"circus.logoutput": "log_ini.txt"},
            log_capture_path="log_ini.txt")
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    def test_loggerconfig_default_opt(self):
        logs = run_circusd(
            ["--log-output", "log_opt.txt"], {},
            log_capture_path="log_opt.txt")
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    @skipIf(not hasDictConfig(), "Needs logging.config.dictConfig()")
    def test_loggerconfig_yaml_ini(self):
        config = yaml.load(EXAMPLE_YAML)
        config["handlers"]["logfile"]["filename"] = "log_yaml_ini.txt"
        logs = run_circusd(
            [], {"circus.loggerconfig": "logging.yaml"},
            log_capture_path="log_yaml_ini.txt",
            additional_files={"logging.yaml": yaml.dump(config)})
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    @skipIf(not hasDictConfig(), "Needs logging.config.dictConfig()")
    def test_loggerconfig_yaml_opt(self):
        config = yaml.load(EXAMPLE_YAML)
        config["handlers"]["logfile"]["filename"] = "log_yaml_opt.txt"
        logs = run_circusd(
            ["--logger-config", "logging.yaml"], {},
            log_capture_path="log_yaml_opt.txt",
            additional_files={"logging.yaml": yaml.dump(config)})
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    @skipIf(not hasDictConfig(), "Needs logging.config.dictConfig()")
    def test_loggerconfig_json_ini(self):
        config = yaml.load(EXAMPLE_YAML)
        config["handlers"]["logfile"]["filename"] = "log_json_ini.txt"
        logs = run_circusd(
            [], {"circus.loggerconfig": "logging.json"},
            log_capture_path="log_json_ini.txt",
            additional_files={"logging.json": json.dumps(config)})
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    @skipIf(not hasDictConfig(), "Needs logging.config.dictConfig()")
    def test_loggerconfig_json_opt(self):
        config = yaml.load(EXAMPLE_YAML)
        config["handlers"]["logfile"]["filename"] = "log_json_opt.txt"
        logs = run_circusd(
            ["--logger-config", "logging.json"], {},
            log_capture_path="log_json_opt.txt",
            additional_files={"logging.json": json.dumps(config)})
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    def test_loggerconfig_ini_ini(self):
        config = yaml.load(EXAMPLE_YAML)
        config["handlers"]["logfile"]["filename"] = "log_ini_ini.txt"
        logs = run_circusd(
            [], {"circus.loggerconfig": "logging.ini"},
            log_capture_path="log_ini_ini.txt",
            additional_files={
                "logging.ini": logging_dictconfig_to_ini(config)})
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    def test_loggerconfig_ini_opt(self):
        config = yaml.load(EXAMPLE_YAML)
        config["handlers"]["logfile"]["filename"] = "log_ini_opt.txt"
        logs = run_circusd(
            ["--logger-config", "logging.ini"], {},
            log_capture_path="log_ini_opt.txt",
            additional_files={
                "logging.ini": logging_dictconfig_to_ini(config)})
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_pidfile
import tempfile
import os
import subprocess

from circus.pidfile import Pidfile
from circus.tests.support import TestCase, EasyTestSuite


class TestPidfile(TestCase):
    def test_pidfile(self):
        proc = subprocess.Popen('sleep 120', shell=True)
        fd, path = tempfile.mkstemp()
        os.close(fd)

        try:
            pidfile = Pidfile(path)

            pidfile.create(proc.pid)
            self.assertRaises(RuntimeError, pidfile.create, proc.pid)
            pidfile.unlink()
            pidfile.create(proc.pid)
            pidfile.rename(path + '.2')
            self.assertTrue(os.path.exists(path + '.2'))
            self.assertFalse(os.path.exists(path))
        finally:
            os.remove(path + '.2')

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_plugin_command_reloader
from mock import patch

from circus.plugins.command_reloader import CommandReloader
from circus.tests.support import TestCircus, EasyTestSuite


class TestCommandReloader(TestCircus):

    def setup_os_mock(self, realpath, mtime):
        patcher = patch('circus.plugins.command_reloader.os')
        os_mock = patcher.start()
        self.addCleanup(patcher.stop)
        os_mock.path.realpath.return_value = realpath
        os_mock.stat.return_value.st_mtime = mtime
        return os_mock

    def setup_call_mock(self, watcher_name):
        patcher = patch.object(CommandReloader, 'call')
        call_mock = patcher.start()
        self.addCleanup(patcher.stop)
        call_mock.side_effect = [
            {'watchers': [watcher_name]},
            {'options': {'cmd': watcher_name}},
            None,
        ]
        return call_mock

    def test_default_loop_rate(self):
        plugin = self.make_plugin(CommandReloader, active=True)
        self.assertEqual(plugin.loop_rate, 1)

    def test_non_default_loop_rate(self):
        plugin = self.make_plugin(CommandReloader, active=True, loop_rate='2')
        self.assertEqual(plugin.loop_rate, 2)

    def test_mtime_is_modified(self):
        plugin = self.make_plugin(CommandReloader, active=True)
        plugin.cmd_files = {'foo': {'path': '/bar/baz', 'mtime': 1}}
        self.assertTrue(plugin.is_modified('foo', 2, '/bar/baz'))

    def test_path_is_modified(self):
        plugin = self.make_plugin(CommandReloader, active=True)
        plugin.cmd_files = {'foo': {'path': '/bar/baz', 'mtime': 1}}
        self.assertTrue(plugin.is_modified('foo', 1, '/bar/quux'))

    def test_not_modified(self):
        plugin = self.make_plugin(CommandReloader, active=True)
        plugin.cmd_files = {'foo': {'path': '/bar/quux', 'mtime': 1}}
        self.assertIs(plugin.is_modified('foo', 1, '/bar/quux'), False)

    def test_look_after_known_watcher_triggers_restart(self):
        call_mock = self.setup_call_mock(watcher_name='foo')
        self.setup_os_mock(realpath='/bar/foo', mtime=42)
        plugin = self.make_plugin(CommandReloader, active=True)
        plugin.cmd_files = {'foo': {'path': 'foo', 'mtime': 1}}

        plugin.look_after()

        self.assertEqual(plugin.cmd_files, {
            'foo': {'path': '/bar/foo', 'mtime': 42}
        })
        call_mock.assert_called_with('restart', name='foo')

    def test_look_after_new_watcher_does_not_restart(self):
        call_mock = self.setup_call_mock(watcher_name='foo')
        self.setup_os_mock(realpath='/bar/foo', mtime=42)
        plugin = self.make_plugin(CommandReloader, active=True)
        plugin.cmd_files = {}

        plugin.look_after()

        self.assertEqual(plugin.cmd_files, {
            'foo': {'path': '/bar/foo', 'mtime': 42}
        })
        # No restart, so last call should be for the 'get' command
        call_mock.assert_called_with('get', name='foo', keys=['cmd'])

    def test_missing_watcher_gets_removed_from_plugin_dict(self):
        self.setup_call_mock(watcher_name='bar')
        self.setup_os_mock(realpath='/bar/foo', mtime=42)
        plugin = self.make_plugin(CommandReloader, active=True)
        plugin.cmd_files = {'foo': {'path': 'foo', 'mtime': 1}}

        plugin.look_after()

        self.assertNotIn('foo', plugin.cmd_files)

    def test_handle_recv_implemented(self):
        plugin = self.make_plugin(CommandReloader, active=True)
        plugin.handle_recv('whatever')

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_plugin_flapping
from mock import patch

from circus.tests.support import TestCircus, EasyTestSuite
from circus.plugins.flapping import Flapping


class TestFlapping(TestCircus):

    def _flapping_plugin(self, **config):
        plugin = self.make_plugin(Flapping, active=True, **config)
        plugin.configs['test'] = {'active': True}
        plugin.timelines['test'] = [1, 2]
        return plugin

    def test_default_config(self):
        plugin = self._flapping_plugin()
        self.assertEqual(plugin.attempts, 2)
        self.assertEqual(plugin.window, 1)
        self.assertEqual(plugin.retry_in, 7)
        self.assertEqual(plugin.max_retry, 5)

    @patch.object(Flapping, 'check')
    def test_reap_message_calls_check(self, check_mock):
        plugin = self._flapping_plugin()
        topic = 'watcher.test.reap'

        plugin.handle_recv([topic, None])

        check_mock.assert_called_with('test')

    @patch.object(Flapping, 'cast')
    @patch('circus.plugins.flapping.Timer')
    def test_below_max_retry_triggers_restart(self, timer_mock, cast_mock):
        plugin = self._flapping_plugin(max_retry=5)
        plugin.tries['test'] = 4

        plugin.check('test')

        cast_mock.assert_called_with("stop", name="test")
        self.assertTrue(timer_mock.called)

    @patch.object(Flapping, 'cast')
    @patch('circus.plugins.flapping.Timer')
    def test_above_max_retry_triggers_final_stop(self, timer_mock, cast_mock):
        plugin = self._flapping_plugin(max_retry=5)
        plugin.tries['test'] = 5

        plugin.check('test')

        cast_mock.assert_called_with("stop", name="test")
        self.assertFalse(timer_mock.called)

    def test_beyond_window_resets_tries(self):
        plugin = self._flapping_plugin(max_retry=-1)
        plugin.tries['test'] = 1
        timestamp_beyond_window = plugin.window + plugin.check_delay + 1
        plugin.timelines['test'] = [0, timestamp_beyond_window]

        plugin.check('test')

        self.assertEqual(plugin.tries['test'], 0)

    @patch.object(Flapping, 'cast')
    @patch('circus.plugins.flapping.Timer')
    def test_minus_one_max_retry_triggers_restart(self, timer_mock, cast_mock):
        plugin = self._flapping_plugin(max_retry=-1)
        plugin.timelines['test'] = [1, 2]
        plugin.tries['test'] = 5

        plugin.check('test')

        cast_mock.assert_called_with("stop", name="test")
        self.assertTrue(timer_mock.called)

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_plugin_resource_watcher
import warnings

from tornado.testing import gen_test

from circus.tests.support import TestCircus, async_poll_for, Process
from circus.tests.support import async_run_plugin, EasyTestSuite
from circus.plugins.resource_watcher import ResourceWatcher

# Make sure we don't allow more than 300MB in case things go wrong
MAX_CHUNKS = 10000
CHUNK_SIZE = 30000


class Leaky(Process):
    def run(self):
        self._write('START')
        m = ' '
        chunks_count = 0
        while self.alive and chunks_count < MAX_CHUNKS:
            m += '*' * CHUNK_SIZE  # for memory
            chunks_count += 1

        self._write('STOP')


def run_leaky(test_file):
    process = Leaky(test_file)
    process.run()
    return 1


fqn = 'circus.tests.test_plugin_resource_watcher.run_leaky'


def get_statsd_increments(queue, plugin):
    queue.put(plugin.statsd.increments)


class TestResourceWatcher(TestCircus):

    def _check_statsd(self, increments, name):
        res = list(increments.items())
        self.assertTrue(len(res) > 0)
        for stat, items in res:
            if name == stat and items > 0:
                return
        raise AssertionError("%r stat not found" % name)

    def test_service_config_param_is_deprecated(self):
        with warnings.catch_warnings(record=True) as ws:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            self.make_plugin(ResourceWatcher, service='whatever')
            self.assertTrue(any('ResourceWatcher' in w.message.args[0]
                                for w in ws))

    def test_watcher_config_param_is_required(self):
        self.assertRaises(NotImplementedError, self.make_plugin,
                          ResourceWatcher)

    @gen_test
    def test_resource_watcher_max_mem(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')
        config = {'loop_rate': 0.1, 'max_mem': 0.05, 'watcher': 'test'}
        kw = {'endpoint': self.arbiter.endpoint,
              'pubsub_endpoint': self.arbiter.pubsub_endpoint}

        statsd_increments = yield async_run_plugin(ResourceWatcher,
                                                   config,
                                                   get_statsd_increments, **kw)

        self._check_statsd(statsd_increments,
                           '_resource_watcher.test.over_memory')
        yield self.stop_arbiter()

    @gen_test
    def test_resource_watcher_max_mem_abs(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')
        config = {'loop_rate': 0.1, 'max_mem': '1M', 'watcher': 'test'}
        kw = {'endpoint': self.arbiter.endpoint,
              'pubsub_endpoint': self.arbiter.pubsub_endpoint}

        statsd_increments = yield async_run_plugin(ResourceWatcher,
                                                   config,
                                                   get_statsd_increments, **kw)

        self._check_statsd(statsd_increments,
                           '_resource_watcher.test.over_memory')
        yield self.stop_arbiter()

    @gen_test
    def test_resource_watcher_min_mem(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')
        config = {'loop_rate': 0.1, 'min_mem': 100000.1, 'watcher': 'test'}
        kw = {'endpoint': self.arbiter.endpoint,
              'pubsub_endpoint': self.arbiter.pubsub_endpoint}

        statsd_increments = yield async_run_plugin(ResourceWatcher,
                                                   config,
                                                   get_statsd_increments, **kw)

        self._check_statsd(statsd_increments,
                           '_resource_watcher.test.under_memory')
        yield self.stop_arbiter()

    @gen_test
    def test_resource_watcher_min_mem_abs(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')
        config = {'loop_rate': 0.1, 'min_mem': '100M', 'watcher': 'test'}
        kw = {'endpoint': self.arbiter.endpoint,
              'pubsub_endpoint': self.arbiter.pubsub_endpoint}

        statsd_increments = yield async_run_plugin(ResourceWatcher,
                                                   config,
                                                   get_statsd_increments,
                                                   **kw)

        self._check_statsd(statsd_increments,
                           '_resource_watcher.test.under_memory')
        yield self.stop_arbiter()

    @gen_test
    def test_resource_watcher_max_cpu(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')
        config = {'loop_rate': 0.1, 'max_cpu': 0.1, 'watcher': 'test'}
        kw = {'endpoint': self.arbiter.endpoint,
              'pubsub_endpoint': self.arbiter.pubsub_endpoint}

        statsd_increments = yield async_run_plugin(ResourceWatcher,
                                                   config,
                                                   get_statsd_increments, **kw)

        self._check_statsd(statsd_increments,
                           '_resource_watcher.test.over_cpu')
        yield self.stop_arbiter()

    @gen_test
    def test_resource_watcher_min_cpu(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')
        config = {'loop_rate': 0.1, 'min_cpu': 99.0, 'watcher': 'test'}

        kw = {'endpoint': self.arbiter.endpoint,
              'pubsub_endpoint': self.arbiter.pubsub_endpoint}

        statsd_increments = yield async_run_plugin(ResourceWatcher,
                                                   config,
                                                   get_statsd_increments,
                                                   **kw)

        self._check_statsd(statsd_increments,
                           '_resource_watcher.test.under_cpu')
        yield self.stop_arbiter()

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_plugin_statsd
from tornado.testing import gen_test

from circus.tests.support import TestCircus, async_poll_for
from circus.tests.support import async_run_plugin, EasyTestSuite
from circus.plugins.statsd import FullStats


def get_gauges(queue, plugin):
    queue.put(plugin.statsd.gauges)


class TestFullStats(TestCircus):

    @gen_test
    def test_full_stats(self):
        dummy_process = 'circus.tests.support.run_process'
        yield self.start_arbiter(dummy_process)
        async_poll_for(self.test_file, 'START')

        config = {'loop_rate': 0.2}
        gauges = yield async_run_plugin(
            FullStats, config,
            plugin_info_callback=get_gauges,
            duration=1000,
            endpoint=self.arbiter.endpoint,
            pubsub_endpoint=self.arbiter.pubsub_endpoint)

        # we should have a bunch of stats events here
        self.assertTrue(len(gauges) >= 5)
        last_batch = sorted(name for name, value in gauges[-5:])
        wanted = ['_stats.test.cpu_sum', '_stats.test.mem_max',
                  '_stats.test.mem_pct_max', '_stats.test.mem_pct_sum',
                  '_stats.test.mem_sum']
        self.assertEqual(last_batch, wanted)

        yield self.stop_arbiter()


test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_plugin_watchdog
import socket
import time
import os
import warnings

from tornado.testing import gen_test

from circus.tests.support import TestCircus, Process, async_poll_for
from circus.tests.support import async_run_plugin as arp, EasyTestSuite
from circus.plugins.watchdog import WatchDog


class DummyWatchDogged(Process):
    def run(self):
        self._write('STARTWD')
        sock = socket.socket(socket.AF_INET,
                             socket.SOCK_DGRAM)  # UDP
        try:
            my_pid = os.getpid()
            for _ in range(5):
                message = "{pid};{time}".format(pid=my_pid, time=time.time())
                sock.sendto(message, ('127.0.0.1', 1664))
                time.sleep(0.5)
            self._write('STOPWD')
        finally:
            sock.close()


def run_dummy_watchdogged(test_file):
    process = DummyWatchDogged(test_file)
    process.run()
    return 1


def get_pid_status(queue, plugin):
    queue.put(plugin.pid_status)


fqn = 'circus.tests.test_plugin_watchdog.run_dummy_watchdogged'


class TestPluginWatchDog(TestCircus):

    @gen_test
    def test_watchdog_discovery_found(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'STARTWD')
        pubsub = self.arbiter.pubsub_endpoint

        config = {'loop_rate': 0.1, 'watchers_regex': "^test.*$"}
        with warnings.catch_warnings():
            pid_status = yield arp(WatchDog, config,
                                   get_pid_status,
                                   endpoint=self.arbiter.endpoint,
                                   pubsub_endpoint=pubsub)
        self.assertEqual(len(pid_status), 1, pid_status)
        yield self.stop_arbiter()
        async_poll_for(self.test_file, 'STOPWD')

    @gen_test
    def test_watchdog_discovery_not_found(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')
        pubsub = self.arbiter.pubsub_endpoint

        config = {'loop_rate': 0.1, 'watchers_regex': "^foo.*$"}
        with warnings.catch_warnings():
            pid_status = yield arp(WatchDog, config,
                                   get_pid_status,
                                   endpoint=self.arbiter.endpoint,
                                   pubsub_endpoint=pubsub)
        self.assertEqual(len(pid_status), 0, pid_status)
        yield self.stop_arbiter()

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_process
import os
import sys

from circus.process import Process
from circus.tests.support import (TestCircus, skipIf, EasyTestSuite, DEBUG,
                                  poll_for)
import circus.py3compat
from circus.py3compat import StringIO, PY2


RLIMIT = """\
import resource, sys

try:
    with open(sys.argv[1], 'w') as f:
        for limit in ('NOFILE', 'NPROC'):
            res = getattr(resource, 'RLIMIT_%s' % limit)
            f.write('%s=%s\\n' % (limit, resource.getrlimit(res)))
        f.write('END')
finally:
    sys.exit(0)
"""


VERBOSE = """\
import sys

try:
    for i in range(1000):
        for stream in (sys.stdout, sys.stderr):
            stream.write(str(i))
            stream.flush()
    with open(sys.argv[1], 'w') as f:
        f.write('END')
finally:
    sys.exit(0)

"""


def _nose_no_s():
    if PY2:
        return not hasattr(sys.stdout, 'fileno')
    else:
        return isinstance(sys.stdout, StringIO)


class TestProcess(TestCircus):

    def test_base(self):
        cmd = sys.executable
        args = "-c 'import time; time.sleep(2)'"
        process = Process('test', cmd, args=args, shell=False)
        try:
            info = process.info()
            self.assertEqual(process.pid, info['pid'])
            age = process.age()
            self.assertTrue(age > 0.)
            self.assertFalse(process.is_child(0))
        finally:
            process.stop()

    @skipIf(DEBUG, 'Py_DEBUG=1')
    def test_rlimits(self):
        script_file = self.get_tmpfile(RLIMIT)
        output_file = self.get_tmpfile()

        cmd = sys.executable
        args = [script_file, output_file]
        rlimits = {'nofile': 20,
                   'nproc': 20}

        process = Process('test', cmd, args=args, rlimits=rlimits)
        poll_for(output_file, 'END')
        process.stop()

        with open(output_file, 'r') as f:
            output = {}
            for line in f.readlines():
                line = line.rstrip()
                line = line.split('=', 1)
                if len(line) != 2:
                    continue
                limit, value = line
                output[limit] = value

        def srt2ints(val):
            return [circus.py3compat.long(key) for key in val[1:-1].split(',')]

        wanted = [circus.py3compat.long(20), circus.py3compat.long(20)]

        self.assertEqual(srt2ints(output['NOFILE']), wanted)
        self.assertEqual(srt2ints(output['NPROC']), wanted)

    def test_comparison(self):
        cmd = sys.executable
        args = ['import time; time.sleep(2)', ]
        p1 = Process('1', cmd, args=args)
        p2 = Process('2', cmd, args=args)

        self.assertTrue(p1 < p2)
        self.assertFalse(p1 == p2)
        self.assertTrue(p1 == p1)

        p1.stop()
        p2.stop()

    def test_process_parameters(self):
        # all the options passed to the process should be available by the
        # command / process

        p1 = Process('1', 'make-me-a-coffee',
                     '$(circus.wid) --type $(circus.env.type)',
                     shell=False, spawn=False, env={'type': 'macchiato'})

        self.assertEqual(['make-me-a-coffee', '1', '--type', 'macchiato'],
                         p1.format_args())

        p2 = Process('1', 'yeah $(CIRCUS.WID)', spawn=False)
        self.assertEqual(['yeah', '1'], p2.format_args())

        os.environ['coffee_type'] = 'american'
        p3 = Process('1', 'yeah $(circus.env.type)', shell=False, spawn=False,
                     env={'type': 'macchiato'})
        self.assertEqual(['yeah', 'macchiato'], p3.format_args())
        os.environ.pop('coffee_type')

    @skipIf(DEBUG, 'Py_DEBUG=1')
    @skipIf(_nose_no_s(), 'Nose runs without -s')
    def test_streams(self):
        script_file = self.get_tmpfile(VERBOSE)
        output_file = self.get_tmpfile()

        cmd = sys.executable
        args = [script_file, output_file]

        # 1. streams sent to /dev/null
        process = Process('test', cmd, args=args, close_child_stdout=True,
                          close_child_stderr=True)
        try:
            poll_for(output_file, 'END')

            # the pipes should be empty
            self.assertEqual(process.stdout.read(), b'')
            self.assertEqual(process.stderr.read(), b'')
        finally:
            process.stop()

        # 2. streams sent to /dev/null, no PIPEs
        output_file = self.get_tmpfile()
        args[1] = output_file

        process = Process('test', cmd, args=args, close_child_stdout=True,
                          close_child_stderr=True, pipe_stdout=False,
                          pipe_stderr=False)

        try:
            poll_for(output_file, 'END')
            # the pipes should be unexistant
            self.assertTrue(process.stdout is None)
            self.assertTrue(process.stderr is None)
        finally:
            process.stop()

        # 3. streams & pipes open
        output_file = self.get_tmpfile()
        args[1] = output_file
        process = Process('test', cmd, args=args)

        try:
            poll_for(output_file, 'END')

            # the pipes should be unexistant
            self.assertEqual(len(process.stdout.read()), 2890)
            self.assertEqual(len(process.stderr.read()), 2890)
        finally:
            process.stop()

    def test_initgroups(self):
        cmd = sys.executable
        args = ['import time; time.sleep(2)']
        gid = os.getgid()
        uid = os.getuid()
        p1 = Process('1', cmd, args=args, gid=gid, uid=uid)
        p1.stop()


test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_reloadconfig
import os
import tornado
import tornado.testing

from circus.arbiter import Arbiter
from circus.tests.support import EasyTestSuite


HERE = os.path.join(os.path.dirname(__file__))
CONFIG_DIR = os.path.join(HERE, 'config')

_CONF = {
    'reload_base': os.path.join(CONFIG_DIR, 'reload_base.ini'),
    'reload_numprocesses': os.path.join(CONFIG_DIR, 'reload_numprocesses.ini'),
    'reload_addwatchers': os.path.join(CONFIG_DIR, 'reload_addwatchers.ini'),
    'reload_delwatchers': os.path.join(CONFIG_DIR, 'reload_delwatchers.ini'),
    'reload_changewatchers': os.path.join(CONFIG_DIR,
                                          'reload_changewatchers.ini'),
    'reload_addplugins': os.path.join(CONFIG_DIR, 'reload_addplugins.ini'),
    'reload_delplugins': os.path.join(CONFIG_DIR, 'reload_delplugins.ini'),
    'reload_changeplugins': os.path.join(CONFIG_DIR,
                                         'reload_changeplugins.ini'),
    'reload_addsockets': os.path.join(CONFIG_DIR, 'reload_addsockets.ini'),
    'reload_delsockets': os.path.join(CONFIG_DIR, 'reload_delsockets.ini'),
    'reload_changesockets': os.path.join(CONFIG_DIR,
                                         'reload_changesockets.ini'),
    'reload_changearbiter': os.path.join(CONFIG_DIR,
                                         'reload_changearbiter.ini'),
    'reload_statsd': os.path.join(CONFIG_DIR, 'reload_statsd.ini'),
}


class FakeSocket(object):
    closed = False

    def send_multipart(self, *args):
        pass
    close = send_multipart


class TestConfig(tornado.testing.AsyncTestCase):

    def setUp(self):
        super(TestConfig, self).setUp()
        self.a = self._load_base_arbiter()

    @tornado.gen.coroutine
    def _tearDown(self):
        yield self._tear_down_arbiter(self.a)

    @tornado.gen.coroutine
    def _tear_down_arbiter(self, a):
        for watcher in a.iter_watchers():
            yield watcher._stop()
        a.sockets.close_all()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def _load_base_arbiter(self, name='reload_base'):
        loop = tornado.ioloop.IOLoop.instance()
        a = Arbiter.load_from_config(_CONF[name], loop=loop)
        a.evpub_socket = FakeSocket()
        # initialize watchers
        for watcher in a.iter_watchers():
            a._watchers_names[watcher.name.lower()] = watcher
        return a

    def test_watcher_names(self):
        watcher_names = sorted(i.name for i in self.a.watchers)
        self.assertEqual(watcher_names, ['plugin:myplugin', 'test1', 'test2'])

    @tornado.testing.gen_test
    def test_reload_numprocesses(self):
        w = self.a.get_watcher('test1')
        self.assertEqual(w.numprocesses, 1)
        yield self.a.reload_from_config(_CONF['reload_numprocesses'])
        self.assertEqual(w.numprocesses, 2)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_addwatchers(self):
        self.assertEqual(len(self.a.watchers), 3)
        yield self.a.reload_from_config(_CONF['reload_addwatchers'])
        self.assertEqual(len(self.a.watchers), 4)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_delwatchers(self):
        self.assertEqual(len(self.a.watchers), 3)
        yield self.a.reload_from_config(_CONF['reload_delwatchers'])
        self.assertEqual(len(self.a.watchers), 2)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_changewatchers(self):
        self.assertEqual(len(self.a.watchers), 3)
        w0 = self.a.get_watcher('test1')
        w1 = self.a.get_watcher('test2')
        yield self.a.reload_from_config(_CONF['reload_changewatchers'])
        self.assertEqual(len(self.a.watchers), 3)
        self.assertEqual(self.a.get_watcher('test1'), w0)
        self.assertNotEqual(self.a.get_watcher('test2'), w1)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_addplugins(self):
        self.assertEqual(len(self.a.watchers), 3)
        yield self.a.reload_from_config(_CONF['reload_addplugins'])
        self.assertEqual(len(self.a.watchers), 4)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_delplugins(self):
        self.assertEqual(len(self.a.watchers), 3)
        yield self.a.reload_from_config(_CONF['reload_delplugins'])
        self.assertEqual(len(self.a.watchers), 2)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_changeplugins(self):
        self.assertEqual(len(self.a.watchers), 3)
        p = self.a.get_watcher('plugin:myplugin')
        yield self.a.reload_from_config(_CONF['reload_changeplugins'])
        self.assertEqual(len(self.a.watchers), 3)
        self.assertNotEqual(self.a.get_watcher('plugin:myplugin'), p)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_addsockets(self):
        self.assertEqual(len(self.a.sockets), 1)
        yield self.a.reload_from_config(_CONF['reload_addsockets'])
        self.assertEqual(len(self.a.sockets), 2)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_delsockets(self):
        self.assertEqual(len(self.a.sockets), 1)
        yield self.a.reload_from_config(_CONF['reload_delsockets'])
        self.assertEqual(len(self.a.sockets), 0)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_changesockets(self):
        self.assertEqual(len(self.a.sockets), 1)
        s = self.a.get_socket('mysocket')
        yield self.a.reload_from_config(_CONF['reload_changesockets'])
        self.assertEqual(len(self.a.sockets), 1)
        self.assertNotEqual(self.a.get_socket('mysocket'), s)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_envdictparsed(self):
        # environ var that needs a `circus.util.parse_env_dict` treatment
        os.environ['SHRUBBERY'] = ' NI '
        a = self._load_base_arbiter()
        try:
            w = a.get_watcher('test1')
            yield a.reload_from_config(_CONF['reload_base'])
            self.assertEqual(a.get_watcher('test1'), w)
        finally:
            del os.environ['SHRUBBERY']
            yield self._tear_down_arbiter(a)

    @tornado.testing.gen_test
    def test_reload_ignorearbiterwatchers(self):
        a = self._load_base_arbiter('reload_statsd')
        statsd = a.get_watcher('circusd-stats')
        yield a.reload_from_config(_CONF['reload_statsd'])
        self.assertEqual(statsd, a.get_watcher('circusd-stats'))

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_runner
from tornado.testing import gen_test
from circus.tests.support import TestCircus, async_poll_for, EasyTestSuite


def Dummy(test_file):
    with open(test_file, 'w') as f:
        f.write('..........')
    return 1


class TestRunner(TestCircus):

    @gen_test
    def test_dummy(self):
        yield self.start_arbiter('circus.tests.test_runner.Dummy')
        self.assertTrue(async_poll_for(self.test_file, '..........'))
        yield self.stop_arbiter()

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_sighandler
from tornado.testing import gen_test

from circus.tests.support import TestCircus, async_poll_for, EasyTestSuite


class TestSigHandler(TestCircus):

    @gen_test
    def test_handler(self):
        yield self.start_arbiter()

        # wait for the process to be started
        self.assertTrue(async_poll_for(self.test_file, 'START'))

        # stopping...
        yield self.arbiter.stop()

        # wait for the process to be stopped
        self.assertTrue(async_poll_for(self.test_file, 'QUIT'))

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_sockets
import os
import socket
import tempfile
try:
    import IN
except ImportError:
    pass
import mock

from circus.tests.support import TestCase, skipIf, EasyTestSuite
from circus.sockets import CircusSocket, CircusSockets


def so_bindtodevice_supported():
    try:
        if hasattr(IN, 'SO_BINDTODEVICE'):
            return True
    except NameError:
        pass
    return False


class TestSockets(TestCase):

    def setUp(self):
        super(TestSockets, self).setUp()
        self.files = []

    def tearDown(self):
        for file_ in self.files:
            if os.path.exists(file_):
                os.remove(file_)

        super(TestSockets, self).tearDown()

    def _get_file(self):
        fd, _file = tempfile.mkstemp()
        os.close(fd)
        self.files.append(_file)
        return _file

    def _get_tmp_filename(self):
        # XXX horrible way to get a filename
        fd, _file = tempfile.mkstemp()
        os.close(fd)
        os.remove(_file)
        return _file

    def test_socket(self):
        sock = CircusSocket('somename', 'localhost', 0)
        try:
            sock.bind_and_listen()
        finally:
            sock.close()

    def test_manager(self):
        mgr = CircusSockets()

        for i in range(5):
            mgr.add(str(i), 'localhost', 0)

        port = mgr['1'].port
        try:
            mgr.bind_and_listen_all()
            # we should have a port now
            self.assertNotEqual(port, mgr['1'].port)
        finally:
            mgr.close_all()

    def test_load_from_config_no_proto(self):
        """When no proto in the config, the default (0) is used."""
        config = {'name': ''}
        sock = CircusSocket.load_from_config(config)
        self.assertEqual(sock.proto, 0)
        sock.close()

    def test_load_from_config_unknown_proto(self):
        """Unknown proto in the config raises an error."""
        config = {'name': '', 'proto': 'foo'}
        self.assertRaises(socket.error, CircusSocket.load_from_config, config)

    def test_load_from_config_umask(self):
        sockfile = self._get_tmp_filename()
        config = {'name': 'somename', 'path': sockfile, 'umask': 0}
        sock = CircusSocket.load_from_config(config)
        try:
            self.assertEqual(sock.umask, 0)
        finally:
            sock.close()

    def test_load_from_config_replace(self):
        sockfile = self._get_file()

        config = {'name': 'somename', 'path': sockfile, 'replace': False}
        sock = CircusSocket.load_from_config(config)
        try:
            self.assertRaises(OSError, sock.bind_and_listen)
        finally:
            sock.close()

        config = {'name': 'somename', 'path': sockfile, 'replace': True}
        sock = CircusSocket.load_from_config(config)
        sock.bind_and_listen()
        try:
            self.assertEqual(sock.replace, True)
        finally:
            sock.close()

    def test_unix_socket(self):
        sockfile = self._get_tmp_filename()
        sock = CircusSocket('somename', path=sockfile, umask=0)
        try:
            sock.bind_and_listen()
            self.assertTrue(os.path.exists(sockfile))
            permissions = oct(os.stat(sockfile).st_mode)[-3:]
            self.assertEqual(permissions, '777')
        finally:
            sock.close()

    def test_unix_cleanup(self):
        sockets = CircusSockets()
        sockfile = self._get_tmp_filename()
        try:
            sockets.add('unix', path=sockfile)
            sockets.bind_and_listen_all()
            self.assertTrue(os.path.exists(sockfile))
        finally:
            sockets.close_all()
            self.assertTrue(not os.path.exists(sockfile))

    @skipIf(not so_bindtodevice_supported(),
            'SO_BINDTODEVICE unsupported')
    def test_bind_to_interface(self):
        config = {'name': '', 'host': 'localhost', 'port': 0,
                  'interface': 'lo'}

        sock = CircusSocket.load_from_config(config)
        self.assertEqual(sock.interface, config['interface'])
        sock.setsockopt = mock.Mock()
        try:
            sock.bind_and_listen()
            sock.setsockopt.assert_any_call(socket.SOL_SOCKET,
                                            IN.SO_BINDTODEVICE,
                                            config['interface'] + '\0')
        finally:
            sock.close()

    def test_inet6(self):
        config = {'name': '', 'host': '::1', 'port': 0,
                  'family': 'AF_INET6'}
        sock = CircusSocket.load_from_config(config)
        self.assertEqual(sock.host, config['host'])
        self.assertEqual(sock.port, config['port'])
        sock.setsockopt = mock.Mock()
        try:
            sock.bind_and_listen()
            # we should have got a port set
            self.assertNotEqual(sock.port, 0)
        finally:
            sock.close()

    @skipIf(not hasattr(socket, 'SO_REUSEPORT'),
            'socket.SO_REUSEPORT unsupported')
    def test_reuseport_supported(self):
        config = {'name': '', 'host': 'localhost', 'port': 0,
                  'so_reuseport': True}

        sock = CircusSocket.load_from_config(config)
        try:
            sockopt = sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT)
        except socket.error:
            # see #699
            return
        finally:
            sock.close()

        self.assertEqual(sock.so_reuseport, True)
        self.assertNotEqual(sockopt, 0)

    def test_reuseport_unsupported(self):
        config = {'name': '', 'host': 'localhost', 'port': 0,
                  'so_reuseport': True}
        saved = None

        try:
            if hasattr(socket, 'SO_REUSEPORT'):
                saved = socket.SO_REUSEPORT
                del socket.SO_REUSEPORT
            sock = CircusSocket.load_from_config(config)
            self.assertEqual(sock.so_reuseport, False)
        finally:
            if saved is not None:
                socket.SO_REUSEPORT = saved
            sock.close()


test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_stats_client
import time
import tempfile
import os
import sys
import tornado

from circus.tests.support import TestCircus, EasyTestSuite
from circus.client import AsyncCircusClient
from circus.stream import FileStream
from circus.py3compat import get_next
from circus.util import tornado_sleep


def run_process(*args, **kw):
    try:
        i = 0
        while True:
            sys.stdout.write('%.2f-stdout-%d-%s\n' % (time.time(),
                                                      os.getpid(), i))
            sys.stdout.flush()
            sys.stderr.write('%.2f-stderr-%d-%s\n' % (time.time(),
                                                      os.getpid(), i))
            sys.stderr.flush()
            time.sleep(.25)
    except:
        return 1


class TestStatsClient(TestCircus):

    def setUp(self):
        super(TestStatsClient, self).setUp()
        self.files = []

    def _get_file(self):
        fd, log = tempfile.mkstemp()
        os.close(fd)
        self.files.append(log)
        return log

    def tearDown(self):
        super(TestStatsClient, self).tearDown()
        for file in self.files:
            if os.path.exists(file):
                os.remove(file)

    @tornado.testing.gen_test
    def test_handler(self):
        log = self._get_file()
        stream = {'stream': FileStream(log)}
        cmd = 'circus.tests.test_stats_client.run_process'
        stdout_stream = stream
        stderr_stream = stream
        yield self.start_arbiter(cmd=cmd, stdout_stream=stdout_stream,
                                 stderr_stream=stderr_stream, stats=True,
                                 debug=False)

        # waiting for data to appear in the file stream
        empty = True
        while empty:
            with open(log) as f:
                empty = f.read() == ''
            yield tornado_sleep(.1)

        # checking that our system is live and running
        client = AsyncCircusClient(endpoint=self.arbiter.endpoint)
        res = yield client.send_message('list')

        watchers = sorted(res['watchers'])
        self.assertEqual(['circusd-stats', 'test'], watchers)

        # making sure the stats process run
        res = yield client.send_message('status', name='test')
        self.assertEqual(res['status'], 'active')

        res = yield client.send_message('status', name='circusd-stats')
        self.assertEqual(res['status'], 'active')

        # playing around with the stats now: we should get some !
        from circus.stats.client import StatsClient
        client = StatsClient(endpoint=self.arbiter.stats_endpoint)

        next = get_next(client.iter_messages())

        for i in range(10):
            watcher, pid, stat = next()
            self.assertTrue(watcher in ('test', 'circusd-stats', 'circus'),
                            watcher)
        yield self.stop_arbiter()

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_stats_collector
import socket
import time
from collections import defaultdict
from circus.fixed_threading import Thread

from zmq.eventloop import ioloop

from circus.stats import collector as collector_module
from circus.stats.collector import SocketStatsCollector, WatcherStatsCollector
from circus.tests.support import TestCase, EasyTestSuite


class TestCollector(TestCase):

    def setUp(self):
        # let's create 10 sockets and their clients
        self.socks = []
        self.clients = []
        self.fds = []
        self.pids = {}

    def tearDown(self):
        for sock, _, _ in self.socks:
            sock.close()

        for sock in self.clients:
            sock.close()

    def _get_streamer(self):
        for i in range(10):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', 0))
            sock.listen(1)
            self.socks.append((sock, 'localhost:0', sock.fileno()))
            self.fds.append(sock.fileno())
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(sock.getsockname())
            self.clients.append(client)

        class FakeStreamer(object):
            stats = []

            def __init__(this):
                this.sockets = self.socks

            @property
            def circus_pids(this):
                return self.circus_pids

            def get_pids(this, name):
                return self.pids[name]

            @property
            def publisher(this):
                return this

            def publish(this, name, stat):
                this.stats.append(stat)

        self.streamer = FakeStreamer()
        return self.streamer

    def _get_collector(self, collector_class):
        self._get_streamer()

        class Collector(Thread):

            def __init__(this, streamer):
                Thread.__init__(this)
                this.streamer = streamer
                this.loop = ioloop.IOLoop()
                this.daemon = True

            def run(self):
                collector = collector_class(
                    self.streamer, 'sockets', callback_time=0.1,
                    io_loop=self.loop)
                collector.start()
                self.loop.start()

            def stop(self):
                self.loop.add_callback(self.loop.stop)
                self.loop.add_callback(self.loop.close)

        return Collector(self.streamer)

    def test_watcherstats(self):
        calls = defaultdict(int)
        info = []
        for i in range(2):
            info.append({
                'age': 154058.91111397743 + i,
                'children': [],
                'cmdline': 'python',
                'cpu': 0.0 + i / 10.,
                'create_time': 1378663281.96,
                'ctime': '0:00.0',
                'mem': 0.0,
                'mem_info1': '52K',
                'mem_info2': '39M',
                'nice': 0,
                'pid': None,
                'username': 'alexis'})

        def _get_info(pid):
            try:
                data = info[calls[pid]].copy()
            except IndexError:
                raise collector_module.util.NoSuchProcess(pid)
            data['pid'] = pid
            calls[pid] += 1
            return data

        old_info = collector_module.util.get_info
        try:
            collector_module.util.get_info = _get_info

            self.pids['firefox'] = [2353, 2354]
            collector = WatcherStatsCollector(self._get_streamer(), 'firefox')

            stats = list(collector.collect_stats())
            self.assertEqual(len(stats), 3)

            stats = list(collector.collect_stats())
            self.assertEqual(len(stats), 3)

            stats = list(collector.collect_stats())
            self.assertEqual(len(stats), 1)

            self.circus_pids = {1234: 'ohyeah'}
            self.pids['circus'] = [1234]
            collector = WatcherStatsCollector(self._get_streamer(), 'circus')
            stats = list(collector.collect_stats())
            self.assertEqual(stats[0]['name'], 'ohyeah')

        finally:
            collector_module.util.get_info = old_info

    def test_collector_aggregation(self):
        collector = WatcherStatsCollector(self._get_streamer(), 'firefox')
        aggregate = {}
        for i in range(0, 10):
            pid = 1000 + i
            aggregate[pid] = {
                'age': 154058.91111397743, 'children': [],
                'cmdline': 'python', 'cpu': 0.0 + i / 10.,
                'create_time': 1378663281.96,
                'ctime': '0:00.0', 'mem': 0.0 + i // 10,
                'mem_info1': '52K', 'mem_info2': '39M',
                'username': 'alexis', 'subtopic': pid, 'name': 'firefox'}

        res = collector._aggregate(aggregate)
        self.assertEqual(res['mem'], 0)
        self.assertEqual(len(res['pid']), 10)
        self.assertEqual(res['cpu'], 0.45)

    def test_collector_aggregation_when_unknown_values(self):
        collector = WatcherStatsCollector(self._get_streamer(), 'firefox')
        aggregate = {}
        for i in range(0, 10):
            pid = 1000 + i
            aggregate[pid] = {
                'age': 'N/A', 'children': [], 'cmdline': 'python',
                'cpu': 'N/A', 'create_time': 1378663281.96,
                'ctime': '0:00.0', 'mem': 'N/A', 'mem_info1': '52K',
                'mem_info2': '39M', 'nice': 0, 'pid': pid,
                'username': 'alexis', 'subtopic': pid, 'name': 'firefox'}

        res = collector._aggregate(aggregate)
        self.assertEqual(res['mem'], 'N/A')
        self.assertEqual(len(res['pid']), 10)
        self.assertEqual(res['cpu'], 'N/A')

    def test_socketstats(self):
        collector = self._get_collector(SocketStatsCollector)
        collector.start()
        time.sleep(1.)

        # doing some socket things as a client
        for i in range(10):
            for client in self.clients:
                client.send(b'ok')
                # client.recv(2)

        # stopping
        collector.stop()
        for s, _, _ in self.socks:
            s.close()

        # let's see what we got
        self.assertTrue(len(self.streamer.stats) > 2)

        stat = self.streamer.stats[0]
        self.assertTrue(stat['fd'] in self.fds)
        self.assertTrue(stat['reads'] > 1)

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_stats_publisher
import mock

import zmq
import zmq.utils.jsonapi as json

from circus.tests.support import TestCase, EasyTestSuite
from circus.stats.publisher import StatsPublisher


class TestStatsPublisher(TestCase):

    def test_publish(self):
        publisher = StatsPublisher()
        publisher.socket.close()
        publisher.socket = mock.MagicMock()
        stat = {'subtopic': 1, 'foo': 'bar'}
        publisher.publish('foobar', stat)
        publisher.socket.send_multipart.assert_called_with(
            [b'stat.foobar.1', json.dumps(stat)])

    def test_publish_reraise_zmq_errors(self):
        publisher = StatsPublisher()
        publisher.socket = mock.MagicMock()
        publisher.socket.closed = False
        publisher.socket.send_multipart.side_effect = zmq.ZMQError()

        stat = {'subtopic': 1, 'foo': 'bar'}
        self.assertRaises(zmq.ZMQError, publisher.publish, 'foobar', stat)

    def test_publish_silent_zmq_errors_when_socket_closed(self):
        publisher = StatsPublisher()
        publisher.socket = mock.MagicMock()
        publisher.socket.closed = True
        publisher.socket.send_multipart.side_effect = zmq.ZMQError()

        stat = {'subtopic': 1, 'foo': 'bar'}
        publisher.publish('foobar', stat)

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_stats_streamer
import os
import tempfile

import mock

from circus.tests.support import TestCircus, EasyTestSuite
from circus.stats.streamer import StatsStreamer
from circus import client


class _StatsStreamer(StatsStreamer):

    msgs = []

    def handle_recv(self, data):
        self.msgs.append(data)


class FakeStreamer(StatsStreamer):
    def __init__(self, *args, **kwargs):
        self._initialize()


class TestStatsStreamer(TestCircus):

    def setUp(self):
        self.old = client.CircusClient.call
        client.CircusClient.call = self._call
        fd, self._unix = tempfile.mkstemp()
        os.close(fd)

    def tearDown(self):
        client.CircusClient.call = self.old
        os.remove(self._unix)

    def _call(self, cmd):
        what = cmd['command']
        if what == 'list':
            name = cmd['properties'].get('name')
            if name is None:
                return {'watchers': ['one', 'two', 'three']}
            return {'pids': [123, 456]}
        elif what == 'dstats':
            return {'info': {'pid': 789}}
        elif what == 'listsockets':
            return {'status': 'ok',
                    'sockets': [{'path': self._unix,
                                 'fd': 5,
                                 'name': 'XXXX',
                                 'backlog': 2048}],
                    'time': 1369647058.967524}

        raise NotImplementedError(cmd)

    def test_get_pids_circus(self):
        streamer = FakeStreamer()
        streamer.circus_pids = {1234: 'circus-top', 1235: 'circusd'}
        self.assertEqual(streamer.get_pids('circus'), [1234, 1235])

    def test_get_pids(self):
        streamer = FakeStreamer()
        streamer._pids['foobar'] = [1234, 1235]
        self.assertEqual(streamer.get_pids('foobar'), [1234, 1235])

    def test_get_all_pids(self):
        streamer = FakeStreamer()
        streamer._pids['foobar'] = [1234, 1235]
        streamer._pids['barbaz'] = [1236, 1237]
        self.assertEqual(set(streamer.get_pids()),
                         set([1234, 1235, 1236, 1237]))

    @mock.patch('os.getpid', lambda: 2222)
    def test_get_circus_pids(self):
        def _send_message(message, name=None):
            if message == 'list':
                if name == 'circushttpd':
                    return {'pids': [3333]}
                return {'watchers': ['circushttpd']}

            if message == 'dstats':
                return {'info': {'pid': 1111}}

        streamer = FakeStreamer()
        streamer.client = mock.MagicMock()
        streamer.client.send_message = _send_message

        self.assertEqual(
            streamer.get_circus_pids(),
            {1111: 'circusd', 2222: 'circusd-stats',
             3333: 'circushttpd'})

    def test_remove_pid(self):
        streamer = FakeStreamer()
        streamer._callbacks['foobar'] = mock.MagicMock()
        streamer._pids = {'foobar': [1234, 1235]}
        streamer.remove_pid('foobar', 1234)
        self.assertFalse(streamer._callbacks['foobar'].stop.called)

        streamer.remove_pid('foobar', 1235)
        self.assertTrue(streamer._callbacks['foobar'].stop.called)

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_stream
import time
import sys
import os
import tempfile
import tornado

from datetime import datetime
from circus.py3compat import StringIO

from circus.client import make_message
from circus.tests.support import TestCircus, async_poll_for, truncate_file
from circus.tests.support import TestCase, EasyTestSuite
from circus.stream import FileStream, WatchedFileStream
from circus.stream import TimedRotatingFileStream
from circus.stream import FancyStdoutStream


def run_process(testfile, *args, **kw):
    try:
        # print once, then wait
        sys.stdout.write('stdout')
        sys.stdout.flush()
        sys.stderr.write('stderr')
        sys.stderr.flush()
        with open(testfile, 'a+') as f:
            f.write('START')
        time.sleep(1.)
    except:
        return 1


class TestWatcher(TestCircus):
    dummy_process = 'circus.tests.test_stream.run_process'

    def setUp(self):
        super(TestWatcher, self).setUp()
        fd, self.stdout = tempfile.mkstemp()
        os.close(fd)
        fd, self.stderr = tempfile.mkstemp()
        os.close(fd)
        self.stdout_stream = FileStream(self.stdout)
        self.stderr_stream = FileStream(self.stderr)
        self.stdout_arg = {'stream': self.stdout_stream}
        self.stderr_arg = {'stream': self.stderr_stream}

    def tearDown(self):
        self.stdout_stream.close()
        self.stderr_stream.close()
        if os.path.exists(self.stdout):
            os.remove(self.stdout)
        if os.path.exists(self.stderr):
            os.remove(self.stderr)

    @tornado.gen.coroutine
    def _start_arbiter(self):
        yield self.start_arbiter(cmd=self.dummy_process,
                                 stdout_stream=self.stdout_arg,
                                 stderr_stream=self.stderr_arg)

    @tornado.gen.coroutine
    def restart_arbiter(self):
        yield self.arbiter.restart()

    @tornado.gen.coroutine
    def call(self, _cmd, **props):
        msg = make_message(_cmd, **props)
        resp = yield self.cli.call(msg)
        raise tornado.gen.Return(resp)

    @tornado.testing.gen_test
    def test_file_stream(self):
        yield self._start_arbiter()
        stream = FileStream(self.stdout, max_bytes='12', backup_count='3')
        self.assertTrue(isinstance(stream._max_bytes, int))
        self.assertTrue(isinstance(stream._backup_count, int))
        yield self.stop_arbiter()
        stream.close()

    @tornado.testing.gen_test
    def test_watched_file_stream(self):
        yield self._start_arbiter()
        stream = WatchedFileStream(self.stdout,
                                   time_format='%Y-%m-%d %H:%M:%S')
        self.assertTrue(isinstance(stream._time_format, str))
        yield self.stop_arbiter()
        stream.close()

    @tornado.testing.gen_test
    def test_timed_rotating_file_stream(self):
        yield self._start_arbiter()
        stream = TimedRotatingFileStream(self.stdout,
                                         rotate_when='H',
                                         rotate_interval='5',
                                         backup_count='3',
                                         utc='True')
        self.assertTrue(isinstance(stream._interval, int))
        self.assertTrue(isinstance(stream._backup_count, int))
        self.assertTrue(isinstance(stream._utc, bool))
        self.assertTrue(stream._suffix is not None)
        self.assertTrue(stream._ext_match is not None)
        self.assertTrue(stream._rollover_at > 0)
        yield self.stop_arbiter()
        stream.close()

    @tornado.testing.gen_test
    def test_stream(self):
        yield self._start_arbiter()
        # wait for the process to be started
        res1 = yield async_poll_for(self.stdout, 'stdout')
        res2 = yield async_poll_for(self.stderr, 'stderr')
        self.assertTrue(res1)
        self.assertTrue(res2)

        # clean slate
        truncate_file(self.stdout)
        truncate_file(self.stderr)

        # restart and make sure streams are still working
        yield self.restart_arbiter()

        # wait for the process to be restarted
        res1 = yield async_poll_for(self.stdout, 'stdout')
        res2 = yield async_poll_for(self.stderr, 'stderr')
        self.assertTrue(res1)
        self.assertTrue(res2)
        yield self.stop_arbiter()


class TestFancyStdoutStream(TestCase):

    def color_start(self, code):
        return '\033[0;3%s;40m' % code

    def color_end(self):
        return '\033[0m\n'

    def get_stream(self, *args, **kw):
        # need a constant timestamp
        now = datetime.now()
        stream = FancyStdoutStream(*args, **kw)

        # patch some details that will be used
        stream.out = StringIO()
        stream.now = lambda: now

        return stream

    def get_output(self, stream):
        # stub data
        data = {'data': 'hello world',
                'pid': 333}

        # get the output
        stream(data)
        output = stream.out.getvalue()
        stream.out.close()

        expected = self.color_start(stream.color_code)
        expected += stream.now().strftime(stream.time_format) + " "
        expected += "[333] | " + data['data'] + self.color_end()
        return output, expected

    def test_random_colored_output(self):
        stream = self.get_stream()
        output, expected = self.get_output(stream)
        self.assertEqual(output, expected)

    def test_red_colored_output(self):
        stream = self.get_stream(color='red')
        output, expected = self.get_output(stream)
        self.assertEqual(output, expected)

    def test_time_formatting(self):
        stream = self.get_stream(time_format='%Y/%m/%d %H.%M.%S')
        output, expected = self.get_output(stream)
        self.assertEqual(output, expected)

    def test_data_split_into_lines(self):
        stream = self.get_stream(color='red')
        data = {'data': '\n'.join(['foo', 'bar', 'baz']),
                'pid': 333}

        stream(data)
        output = stream.out.getvalue()
        stream.out.close()

        # NOTE: We expect 4 b/c the last line needs to add a newline
        #       in order to prepare for the next chunk
        self.assertEqual(len(output.split('\n')), 4)

    def test_data_with_extra_lines(self):
        stream = self.get_stream(color='red')

        # There is an extra newline
        data = {'data': '\n'.join(['foo', 'bar', 'baz', '']),
                'pid': 333}

        stream(data)
        output = stream.out.getvalue()
        stream.out.close()

        self.assertEqual(len(output.split('\n')), 4)

    def test_color_selections(self):
        # The colors are chosen from an ordered list where each index
        # is used to calculate the ascii escape sequence.
        for i, color in enumerate(FancyStdoutStream.colors):
            stream = self.get_stream(color)
            self.assertEqual(i + 1, stream.color_code)
            stream.out.close()


class TestFileStream(TestCase):
    stream_class = FileStream

    def get_stream(self, *args, **kw):
        # need a constant timestamp
        now = datetime.now()
        stream = self.stream_class(*args, **kw)

        # patch some details that will be used
        stream._file.close()
        stream._file = StringIO()
        stream._open = lambda: stream._file
        stream.now = lambda: now

        return stream

    def get_output(self, stream):
        # stub data
        data = {'data': 'hello world',
                'pid': 333}

        # get the output
        stream(data)
        output = stream._file.getvalue()
        stream._file.close()

        expected = stream.now().strftime(stream._time_format) + " "
        expected += "[333] | " + data['data'] + '\n'
        return output, expected

    def test_time_formatting(self):
        stream = self.get_stream(time_format='%Y/%m/%d %H.%M.%S')
        output, expected = self.get_output(stream)
        self.assertEqual(output, expected)

    def test_data_split_into_lines(self):
        stream = self.get_stream(time_format='%Y/%m/%d %H.%M.%S')
        data = {'data': '\n'.join(['foo', 'bar', 'baz']),
                'pid': 333}

        stream(data)
        output = stream._file.getvalue()
        stream._file.close()

        # NOTE: We expect 4 b/c the last line needs to add a newline
        #       in order to prepare for the next chunk
        self.assertEqual(len(output.split('\n')), 4)

    def test_data_with_extra_lines(self):
        stream = self.get_stream(time_format='%Y/%m/%d %H.%M.%S')

        # There is an extra newline
        data = {'data': '\n'.join(['foo', 'bar', 'baz', '']),
                'pid': 333}

        stream(data)
        output = stream._file.getvalue()
        stream._file.close()
        self.assertEqual(len(output.split('\n')), 4)

    def test_data_with_no_EOL(self):
        stream = self.get_stream()

        # data with no newline and more than 1024 chars
        data = {'data': '*' * 1100, 'pid': 333}

        stream(data)
        stream(data)
        output = stream._file.getvalue()
        stream._file.close()

        self.assertEqual(output, '*' * 2200)


class TestWatchedFileStream(TestFileStream):
    stream_class = WatchedFileStream

    def get_real_stream(self, *args, **kw):
        # need a constant timestamp
        now = datetime.now()
        stream = self.stream_class(*args, **kw)
        stream.now = lambda: now
        return stream

    def test_move_file(self):
        _test_fd, test_filename = tempfile.mkstemp()
        stream = self.get_real_stream(filename=test_filename)

        line1_contents = 'line 1'
        line2_contents = 'line 2'
        file1 = test_filename + '.1'

        # write data, then move the file to simulate a log rotater that will
        # rename the file underneath us, then write more data to ensure that
        # logging continues to work after the rename
        stream({'data': line1_contents})
        os.rename(test_filename, file1)
        stream({'data': line2_contents})
        stream.close()

        with open(test_filename) as line2:
            self.assertEqual(line2.read().strip(), line2_contents)
        with open(file1) as line1:
            self.assertEqual(line1.read().strip(), line1_contents)

        os.unlink(test_filename)
        os.unlink(file1)


test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_umask
import sys
import os
import tornado
import signal
import time

from circus.tests.support import TestCircus, EasyTestSuite, TimeoutException
from circus.stream import QueueStream, Empty
from circus.util import tornado_sleep
from zmq.utils.strtypes import u


class Process(object):

    def __init__(self, test_file):
        with open('/tmp/aack.txt', 'a') as f:
            if os.path.exists(test_file):
                f.write('Removing {0}\n'.format(test_file))
                if os.path.isdir(test_file):
                    os.removedirs(test_file)
                else:
                    os.unlink(test_file)
            else:
                f.write('Hmm, {0} is missing\n'.format(test_file))
            f.write('Creating folder {0}\n'.format(test_file))
            os.makedirs(test_file)

        # init signal handling
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)
        self.alive = True
        sys.stdout.write('Done')
        sys.stdout.flush()

    # noinspection PyUnusedLocal
    def handle_quit(self, *args):
        self.alive = False

    def run(self):
        while self.alive:
            time.sleep(0.1)


def run_process(test_file):
    process = Process(test_file)
    process.run()
    return 1


@tornado.gen.coroutine
def read_from_stream(stream, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            data = stream.get_nowait()
            raise tornado.gen.Return(u(data['data']))
        except Empty:
            yield tornado_sleep(0.1)
    raise TimeoutException('Timeout reading queue')


class UmaskTest(TestCircus):

    def setUp(self):
        super(UmaskTest, self).setUp()
        self.original_umask = os.umask(int('022', 8))

    def tearDown(self):
        super(UmaskTest, self).tearDown()
        dirname = self.test_file
        if os.path.isdir(dirname):
            os.removedirs(dirname)
        os.umask(self.original_umask)

    @tornado.gen.coroutine
    def _call(self, _cmd, **props):
        resp = yield self.call(_cmd, waiting=True, **props)
        raise tornado.gen.Return(resp)

    @tornado.testing.gen_test
    def test_inherited(self):
        cmd = 'circus.tests.test_umask.run_process'
        stream = QueueStream()
        stdout_stream = {'stream': stream}
        yield self.start_arbiter(cmd=cmd, stdout_stream=stdout_stream)

        res = yield read_from_stream(stream)
        self.assertEqual(res, 'Done')

        yield self.stop_arbiter()

        self.assertTrue(os.path.isdir(self.test_file))
        mode = oct(os.stat(self.test_file).st_mode)[-3:]
        self.assertEqual(mode, '755')

    @tornado.testing.gen_test
    def test_set_before_launch(self):
        os.umask(2)
        cmd = 'circus.tests.test_umask.run_process'
        stream = QueueStream()
        stdout_stream = {'stream': stream}
        yield self.start_arbiter(cmd=cmd, stdout_stream=stdout_stream)

        res = yield read_from_stream(stream)
        self.assertEqual(res, 'Done')

        yield self.stop_arbiter()

        self.assertTrue(os.path.isdir(self.test_file))
        mode = oct(os.stat(self.test_file).st_mode)[-3:]
        self.assertEqual(mode, '775')

    @tornado.testing.gen_test
    def test_set_by_arbiter(self):
        cmd = 'circus.tests.test_umask.run_process'
        stream = QueueStream()
        stdout_stream = {'stream': stream}
        yield self.start_arbiter(cmd=cmd, stdout_stream=stdout_stream,
                                 arbiter_kw={'umask': 0})

        res = yield read_from_stream(stream)
        self.assertEqual(res, 'Done')

        yield self.stop_arbiter()

        self.assertTrue(os.path.isdir(self.test_file))
        mode = oct(os.stat(self.test_file).st_mode)[-3:]
        self.assertEqual(mode, '777')

test_suite = EasyTestSuite(__name__)

if __name__ == '__main__':
    run_process(sys.argv[1])

########NEW FILE########
__FILENAME__ = test_util
from __future__ import unicode_literals
import tempfile
import grp
import pwd
import shutil
import os
import sys

from psutil import Popen
import mock

from circus.tests.support import TestCase, EasyTestSuite

from circus import util
from circus.util import (
    get_info, bytes2human, human2bytes, to_bool, parse_env_str, env_to_str,
    to_uid, to_gid, replace_gnu_args, get_python_version, load_virtualenv,
    get_working_dir
)


class TestUtil(TestCase):

    def setUp(self):
        self.dirs = []

    def tearDown(self):
        for dir in self.dirs:
            if os.path.exists(dir):
                shutil.rmtree(dir)

    def test_get_info(self):
        worker = Popen(["python -c 'import time;time.sleep(5)'"], shell=True)
        try:
            info = get_info(worker)
        finally:
            worker.terminate()

        self.assertTrue(isinstance(info['pid'], int))
        self.assertEqual(info['nice'], 0)

    def test_get_info_still_works_when_denied_access(self):
        def access_denied():
            return mock.MagicMock(side_effect=util.AccessDenied)

        class WorkerMock(mock.MagicMock):
            def __getattr__(self, attr):
                raise util.AccessDenied()

        worker = WorkerMock()
        worker.get_memory_info = access_denied()
        worker.get_cpu_percent = access_denied()
        worker.get_cpu_times = access_denied()
        worker.get_nice = access_denied()
        worker.get_memory_percent = access_denied()
        worker.cmdline = []

        info = get_info(worker)

        self.assertEqual(info['mem'], 'N/A')
        self.assertEqual(info['cpu'], 'N/A')
        self.assertEqual(info['ctime'], 'N/A')
        self.assertEqual(info['pid'], 'N/A')
        self.assertEqual(info['username'], 'N/A')
        self.assertEqual(info['nice'], 'N/A')
        self.assertEqual(info['create_time'], 'N/A')
        self.assertEqual(info['age'], 'N/A')

        worker.nice = mock.MagicMock(side_effect=util.NoSuchProcess(1234))
        self.assertEqual(get_info(worker)['nice'], 'Zombie')

    def test_convert_opt(self):
        self.assertEqual(util.convert_opt('env', {'key': 'value'}),
                         'key=value')
        self.assertEqual(util.convert_opt('test', None), '')
        self.assertEqual(util.convert_opt('test', 1), '1')

    def test_bytes2human(self):
        self.assertEqual(bytes2human(10000), '9K')
        self.assertEqual(bytes2human(100001221), '95M')
        self.assertRaises(TypeError, bytes2human, '1')

    def test_human2bytes(self):
        self.assertEqual(human2bytes('1B'), 1)
        self.assertEqual(human2bytes('9K'), 9216)
        self.assertEqual(human2bytes('1129M'), 1183842304)
        self.assertEqual(human2bytes('67T'), 73667279060992)
        self.assertEqual(human2bytes('13P'), 14636698788954112)
        self.assertRaises(ValueError, human2bytes, '')
        self.assertRaises(ValueError, human2bytes, 'faoej')
        self.assertRaises(ValueError, human2bytes, '123KB')
        self.assertRaises(ValueError, human2bytes, '48')
        self.assertRaises(ValueError, human2bytes, '23V')
        self.assertRaises(TypeError, human2bytes, 234)

    def test_tobool(self):
        for value in ('True ', '1', 'true'):
            self.assertTrue(to_bool(value))

        for value in ('False', '0', 'false'):
            self.assertFalse(to_bool(value))

        for value in ('Fal', '344', ''):
            self.assertRaises(ValueError, to_bool, value)

    def test_parse_env_str(self):
        env = 'booo=2,test=1'
        parsed = parse_env_str(env)
        self.assertEqual(parsed, {'test': '1', 'booo': '2'})
        self.assertEqual(env_to_str(parsed), env)

    def test_to_uid(self):
        with mock.patch('pwd.getpwnam') as getpw:
            m = mock.Mock()
            m.pw_uid = '1000'
            getpw.return_value = m
            uid = to_uid('user')
            self.assertEqual('1000', uid)
            uid = to_uid('user')
            self.assertEqual('1000', uid)

    def test_to_uidgid(self):
        self.assertRaises(ValueError, to_uid, 'xxxxxxx')
        self.assertRaises(ValueError, to_gid, 'xxxxxxx')
        self.assertRaises(ValueError, to_uid, -12)
        self.assertRaises(ValueError, to_gid, -12)
        self.assertRaises(TypeError, to_uid, None)
        self.assertRaises(TypeError, to_gid, None)

    def test_to_uid_str(self):
        with mock.patch('pwd.getpwuid') as getpwuid:
            uid = to_uid('1066')
            self.assertEqual(1066, uid)
            getpwuid.assert_called_with(1066)

    def test_to_gid_str(self):
        with mock.patch('grp.getgrgid') as getgrgid:
            gid = to_gid('1042')
            self.assertEqual(1042, gid)
            getgrgid.assert_called_with(1042)

    def test_negative_uid_gid(self):
        # OSX allows negative uid/gid and throws KeyError on a miss. On
        # 32-bit and 64-bit Linux, all negative values throw KeyError as do
        # requests for non-existent uid/gid.
        def int32(val):
            if val & 0x80000000:
                val += -0x100000000
            return val

        def uid_min_max():
            uids = sorted([int32(e[2]) for e in pwd.getpwall()])
            uids[0] = uids[0] if uids[0] < 0 else -1
            return uids[0], uids[-1]

        def gid_min_max():
            gids = sorted([int32(e[2]) for e in grp.getgrall()])
            gids[0] = gids[0] if gids[0] < 0 else -1
            return gids[0], gids[-1]

        uid_min, uid_max = uid_min_max()
        gid_min, gid_max = gid_min_max()

        getpwuid = lambda pid: pwd.getpwuid(pid)
        getgrgid = lambda gid: grp.getgrgid(gid)

        self.assertRaises(KeyError, getpwuid, uid_max + 1)
        self.assertRaises(KeyError, getpwuid, uid_min - 1)
        # getgrid may raises overflow error on mac/os x, fixed in python2.7.5
        # see http://bugs.python.org/issue17531
        self.assertRaises((KeyError, OverflowError), getgrgid, gid_max + 1)
        self.assertRaises((KeyError, OverflowError), getgrgid, gid_min - 1)

    def test_replace_gnu_args(self):
        repl = replace_gnu_args

        self.assertEqual('dont change --fd ((circus.me)) please',
                         repl('dont change --fd ((circus.me)) please'))

        self.assertEqual('dont change --fd $(circus.me) please',
                         repl('dont change --fd $(circus.me) please'))

        self.assertEqual('thats an int 2',
                         repl('thats an int $(circus.me)',
                              me=2))

        self.assertEqual('foobar', replace_gnu_args('$(circus.test)',
                         test='foobar'))
        self.assertEqual('foobar', replace_gnu_args('$(circus.test)',
                         test='foobar'))
        self.assertEqual('foo, foobar, baz',
                         replace_gnu_args('foo, $(circus.test), baz',
                                          test='foobar'))
        self.assertEqual('foo, foobar, baz',
                         replace_gnu_args('foo, ((circus.test)), baz',
                                          test='foobar'))

        self.assertEqual('foobar', replace_gnu_args('$(cir.test)',
                                                    prefix='cir',
                                                    test='foobar'))

        self.assertEqual('foobar', replace_gnu_args('((cir.test))',
                                                    prefix='cir',
                                                    test='foobar'))

        self.assertEqual('thats an int 2',
                         repl('thats an int $(s.me)', prefix='s',
                              me=2))

        self.assertEqual('thats an int 2',
                         repl('thats an int ((s.me))', prefix='s',
                              me=2))

        self.assertEqual('thats an int 2',
                         repl('thats an int $(me)', prefix=None,
                              me=2))

        self.assertEqual('thats an int 2',
                         repl('thats an int ((me))', prefix=None,
                              me=2))

    def test_get_python_version(self):
        py_version = get_python_version()

        self.assertEqual(3, len(py_version))

        for x in py_version:
            self.assertEqual(int, type(x))

        self.assertGreaterEqual(py_version[0], 2)
        self.assertGreaterEqual(py_version[1], 0)
        self.assertGreaterEqual(py_version[2], 0)

    def _create_dir(self):
        dir = tempfile.mkdtemp()
        self.dirs.append(dir)
        return dir

    def test_load_virtualenv(self):
        watcher = mock.Mock()
        watcher.copy_env = False

        # we need the copy_env flag
        self.assertRaises(ValueError, load_virtualenv, watcher)

        watcher.copy_env = True
        watcher.virtualenv = 'XXX'

        # we want virtualenv to be a directory
        self.assertRaises(ValueError, load_virtualenv, watcher)

        watcher.virtualenv = self._create_dir()

        # we want virtualenv directory to contain a site-packages
        self.assertRaises(ValueError, load_virtualenv, watcher)

        py_ver = sys.version.split()[0][:3]
        site_pkg = os.path.join(watcher.virtualenv, 'lib',
                                'python%s' % py_ver, 'site-packages')
        os.makedirs(site_pkg)
        watcher.env = {}
        load_virtualenv(watcher)
        self.assertEqual(site_pkg, watcher.env['PYTHONPATH'])

    @mock.patch('circus.util.os.environ', {'PWD': '/path/to/pwd'})
    @mock.patch('circus.util.os.getcwd', lambda: '/path/to/cwd')
    def test_working_dir_return_pwd_when_paths_are_equals(self):
        def _stat(path):
            stat = mock.MagicMock()
            stat.ino = 'path'
            stat.dev = 'dev'
            return stat
        _old_os_stat = util.os.stat
        try:
            util.os.stat = _stat

            self.assertEqual(get_working_dir(), '/path/to/pwd')
        finally:
            util.os.stat = _old_os_stat

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_validate_option
from circus.tests.support import TestCase, EasyTestSuite
from mock import patch

from circus.commands.util import validate_option
from circus.exc import MessageError


class TestValidateOption(TestCase):

    def test_uidgid(self):
        self.assertRaises(MessageError, validate_option, 'uid', {})
        validate_option('uid', 1)
        validate_option('uid', 'user')
        self.assertRaises(MessageError, validate_option, 'gid', {})
        validate_option('gid', 1)
        validate_option('gid', 'user')

    @patch('warnings.warn')
    def test_stdout_stream(self, warn):
        self.assertRaises(
            MessageError, validate_option, 'stdout_stream', 'something')
        self.assertRaises(MessageError, validate_option, 'stdout_stream', {})
        validate_option('stdout_stream', {'class': 'MyClass'})
        validate_option(
            'stdout_stream', {'class': 'MyClass', 'my_option': '1'})
        validate_option(
            'stdout_stream', {'class': 'MyClass', 'refresh_time': 1})
        self.assertEqual(warn.call_count, 1)

    @patch('warnings.warn')
    def test_stderr_stream(self, warn):
        self.assertRaises(
            MessageError, validate_option, 'stderr_stream', 'something')
        self.assertRaises(MessageError, validate_option, 'stderr_stream', {})
        validate_option('stderr_stream', {'class': 'MyClass'})
        validate_option(
            'stderr_stream', {'class': 'MyClass', 'my_option': '1'})
        validate_option(
            'stderr_stream', {'class': 'MyClass', 'refresh_time': 1})
        self.assertEqual(warn.call_count, 1)

    def test_hooks(self):
        validate_option('hooks', {'before_start': ['all', False]})

        # make sure we control the hook names
        self.assertRaises(MessageError, validate_option, 'hooks',
                          {'IDONTEXIST': ['all', False]})

    def test_rlimit(self):
        validate_option('rlimit_core', 1)

        # require int parameter
        self.assertRaises(MessageError, validate_option, 'rlimit_core', '1')

        # require valid rlimit settings
        self.assertRaises(MessageError, validate_option, 'rlimit_foo', 1)


test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = test_watcher
import signal
import sys
import os
import time
import warnings
try:
    import queue as Queue
except ImportError:
    import Queue  # NOQA
try:
    from test.support import captured_output
except ImportError:
    try:
        from test.test_support import captured_output  # NOQA
    except ImportError:
        captured_output = None  # NOQA

import tornado
import mock

from circus import logger
from circus.process import RUNNING, UNEXISTING

from circus.stream import QueueStream
from circus.tests.support import TestCircus, truncate_file
from circus.tests.support import async_poll_for, EasyTestSuite
from circus.tests.support import MagicMockFuture
from circus.util import get_python_version, tornado_sleep
from circus.watcher import Watcher
from circus.py3compat import s

warnings.filterwarnings('ignore',
                        module='threading', message='sys.exc_clear')


class FakeProcess(object):

    def __init__(self, pid, status, started=1, age=1):
        self.status = status
        self.pid = pid
        self.started = started
        self.age = age
        self.stopping = False

    def returncode(self):
        return 0

    def children(self):
        return []

    def is_alive(self):
        return True

    def stop(self):
        pass


class TestWatcher(TestCircus):

    runner = None

    @tornado.testing.gen_test
    def test_decr_too_much(self):
        yield self.start_arbiter()
        res = yield self.numprocesses('decr', name='test', nb=100)
        self.assertEqual(res, 0)
        res = yield self.numprocesses('decr', name='test', nb=100)
        self.assertEqual(res, 0)
        res = yield self.numprocesses('incr', name='test', nb=1)
        self.assertEqual(res, 1)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_signal(self):
        yield self.start_arbiter(check_delay=1.0)
        resp = yield self.numprocesses('incr', name='test')
        self.assertEqual(resp, 2)
        # wait for both to have started
        resp = yield async_poll_for(self.test_file, 'STARTSTART')
        self.assertTrue(resp)
        truncate_file(self.test_file)

        pids = yield self.pids()
        self.assertEqual(len(pids), 2)
        to_kill = pids[0]
        status = yield self.status('signal', name='test', pid=to_kill,
                                   signum=signal.SIGKILL)
        self.assertEqual(status, 'ok')

        # make sure the process is restarted
        res = yield async_poll_for(self.test_file, 'START')
        self.assertTrue(res)

        # we still should have two processes, but not the same pids for them
        pids = yield self.pids()
        count = 0
        while len(pids) < 2 and count < 10:
            pids = yield self.pids()
            time.sleep(.1)
        self.assertEqual(len(pids), 2)
        self.assertTrue(to_kill not in pids)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_unexisting(self):
        yield self.start_arbiter()
        watcher = self.arbiter.get_watcher("test")

        to_kill = []
        nb_proc = len(watcher.processes)

        for process in list(watcher.processes.values()):
            to_kill.append(process.pid)
            # the process is killed in an unsual way
            try:
                # use SIGKILL instead of SIGSEGV so we don't get
                # 'app crashed' dialogs on OS X
                os.kill(process.pid, signal.SIGKILL)
            except OSError:
                pass

            # and wait for it to die
            try:
                os.waitpid(process.pid, 0)
            except OSError:
                pass

            # ansure the old process is considered "unexisting"
            self.assertEqual(process.status, UNEXISTING)

        # this should clean up and create a new process
        yield watcher.reap_and_manage_processes()

        # watcher ids should have been reused
        wids = [p.wid for p in watcher.processes.values()]
        self.assertEqual(max(wids), watcher.numprocesses)
        self.assertEqual(sum(wids), sum(range(1, watcher.numprocesses + 1)))

        # we should have a new process here now
        self.assertEqual(len(watcher.processes), nb_proc)
        for p in watcher.processes.values():
            # and that one needs to have a new pid.
            self.assertFalse(p.pid in to_kill)

            # and should not be unexisting...
            self.assertNotEqual(p.status, UNEXISTING)

        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_stats(self):
        yield self.start_arbiter()
        resp = yield self.call("stats")
        self.assertTrue("test" in resp.get('infos'))
        watchers = resp.get('infos')['test']

        self.assertEqual(watchers[list(watchers.keys())[0]]['cmdline'].lower(),
                         sys.executable.split(os.sep)[-1].lower())
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_max_age(self):
        yield self.start_arbiter()
        # let's run 15 processes
        yield self.numprocesses('incr', name='test', nb=14)
        initial_pids = yield self.pids()

        # we want to make sure the watcher is really up and running 14
        # processes, and stable
        async_poll_for(self.test_file, 'START' * 15)
        truncate_file(self.test_file)  # make sure we have a clean slate

        # we want a max age of 1 sec.
        options = {'max_age': 1, 'max_age_variance': 0}
        result = yield self.call('set', name='test', waiting=True,
                                 options=options)

        self.assertEqual(result.get('status'), 'ok')

        current_pids = yield self.pids()
        self.assertEqual(len(current_pids), 15)
        self.assertNotEqual(initial_pids, current_pids)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_arbiter_reference(self):
        yield self.start_arbiter()
        self.assertEqual(self.arbiter.watchers[0].arbiter,
                         self.arbiter)
        yield self.stop_arbiter()


class TestWatcherInitialization(TestCircus):

    @tornado.testing.gen_test
    def test_copy_env(self):
        old_environ = os.environ
        try:
            os.environ = {'COCONUTS': 'MIGRATE'}
            watcher = Watcher("foo", "foobar", copy_env=True)
            self.assertEqual(watcher.env, os.environ)

            watcher = Watcher("foo", "foobar", copy_env=True,
                              env={"AWESOMENESS": "YES"})
            self.assertEqual(watcher.env,
                             {'COCONUTS': 'MIGRATE', 'AWESOMENESS': 'YES'})
        finally:
            os.environ = old_environ

    @tornado.testing.gen_test
    def test_hook_in_PYTHON_PATH(self):
        # we have a hook in PYTHONPATH
        tempdir = self.get_tmpdir()

        hook = 'def hook(*args, **kw):\n    return True\n'
        with open(os.path.join(tempdir, 'plugins.py'), 'w') as f:
            f.write(hook)

        old_environ = os.environ
        try:
            os.environ = {'PYTHONPATH': tempdir}
            hooks = {'before_start': ('plugins.hook', False)}

            watcher = Watcher("foo", "foobar", copy_env=True, hooks=hooks)

            self.assertEqual(watcher.env, os.environ)
        finally:
            os.environ = old_environ

    @tornado.testing.gen_test
    def test_copy_path(self):
        watcher = SomeWatcher()
        yield watcher.run()
        # wait for watcher data at most 5s
        messages = []
        resp = False
        start_time = time.time()
        while (time.time() - start_time) <= 5:
            yield tornado_sleep(0.5)
            # More than one Queue.get call is needed to get full
            # output from a watcher in an environment with rich sys.path.
            try:
                m = watcher.stream.get(block=False)
                messages.append(m)
            except Queue.Empty:
                pass
            data = ''.join(s(m['data']) for m in messages)
            if 'XYZ' in data:
                resp = True
                break
        self.assertTrue(resp)
        yield watcher.stop()

    @tornado.testing.gen_test
    def test_venv(self):
        venv = os.path.join(os.path.dirname(__file__), 'venv')
        watcher = SomeWatcher(virtualenv=venv)
        yield watcher.run()
        try:
            py_version = get_python_version()
            major = py_version[0]
            minor = py_version[1]
            wanted = os.path.join(venv, 'lib', 'python%d.%d' % (major, minor),
                                  'site-packages',
                                  'pip-7.7-py%d.%d.egg' % (major, minor))
            ppath = watcher.watcher.env['PYTHONPATH']
        finally:
            yield watcher.stop()
        self.assertTrue(wanted in ppath)

    @tornado.testing.gen_test
    def test_venv_site_packages(self):
        venv = os.path.join(os.path.dirname(__file__), 'venv')
        watcher = SomeWatcher(virtualenv=venv)
        yield watcher.run()
        try:
            yield tornado_sleep(1)
            py_version = get_python_version()
            major = py_version[0]
            minor = py_version[1]
            wanted = os.path.join(venv, 'lib', 'python%d.%d' % (major, minor),
                                  'site-packages')
            ppath = watcher.watcher.env['PYTHONPATH']
        finally:
            yield watcher.stop()

        self.assertTrue(wanted in ppath.split(os.pathsep))


class SomeWatcher(object):

    def __init__(self, loop=None, **kw):
        self.stream = QueueStream()
        self.watcher = None
        self.kw = kw
        if loop is None:
            self.loop = tornado.ioloop.IOLoop.instance()
        else:
            self.loop = loop

    @tornado.gen.coroutine
    def run(self):
        qstream = {'stream': self.stream}
        old_environ = os.environ
        old_paths = sys.path[:]
        try:
            sys.path = ['XYZ']
            os.environ = {'COCONUTS': 'MIGRATE'}
            cmd = ('%s -c "import sys; '
                   'sys.stdout.write(\':\'.join(sys.path)); '
                   ' sys.stdout.flush()"') % sys.executable

            self.watcher = Watcher('xx', cmd, copy_env=True, copy_path=True,
                                   stdout_stream=qstream, loop=self.loop,
                                   **self.kw)
            yield self.watcher.start()
        finally:
            os.environ = old_environ
            sys.path[:] = old_paths

    @tornado.gen.coroutine
    def stop(self):
        if self.watcher is not None:
            yield self.watcher.stop()


SUCCESS = 1
FAILURE = 2
ERROR = 3


class TestWatcherHooks(TestCircus):

    def run_with_hooks(self, hooks):
        self.stream = QueueStream()
        self.errstream = QueueStream()
        dummy_process = 'circus.tests.support.run_process'
        return self._create_circus(dummy_process,
                                   stdout_stream={'stream': self.stream},
                                   stderr_stream={'stream': self.errstream},
                                   hooks=hooks, debug=True, async=True)

    @tornado.gen.coroutine
    def _stop(self):
        yield self.call("stop", name="test", waiting=True)

    @tornado.gen.coroutine
    def _stats(self):
        yield self.call("stats", name="test")

    @tornado.gen.coroutine
    def _extended_stats(self):
        yield self.call("stats", name="test", extended=True)

    @tornado.gen.coroutine
    def get_status(self):
        resp = yield self.call("status", name="test")
        raise tornado.gen.Return(resp['status'])

    def test_missing_hook(self):
        hooks = {'before_start': ('fake.hook.path', False)}
        self.assertRaises(ImportError, self.run_with_hooks, hooks)

    @tornado.gen.coroutine
    def _test_hooks(self, hook_name='before_start', status='active',
                    behavior=SUCCESS, call=None,
                    hook_kwargs_test_function=None):
        events = {'before_start_called': False}

        def hook(watcher, arbiter, hook_name, **kwargs):
            events['%s_called' % hook_name] = True
            events['arbiter_in_hook'] = arbiter

            if hook_kwargs_test_function is not None:
                hook_kwargs_test_function(kwargs)

            if hook_name == 'extended_stats':
                kwargs['stats']['tx'] = 1000
                return
            if behavior == SUCCESS:
                return True
            elif behavior == FAILURE:
                return False

            raise TypeError('beeeuuua')

        old = logger.exception
        logger.exception = lambda x: x

        hooks = {hook_name: (hook, False)}
        testfile, arbiter = self.run_with_hooks(hooks)
        yield arbiter.start()
        try:
            if call:
                yield call()
            resp_status = yield self.get_status()
            self.assertEqual(resp_status, status)
        finally:
            yield arbiter.stop()
            logger.exception = old

        self.assertTrue(events['%s_called' % hook_name])
        self.assertEqual(events['arbiter_in_hook'], arbiter)

    @tornado.gen.coroutine
    def _test_extended_stats(self, extended=False):
        events = {'extended_stats_called': False}

        def hook(watcher, arbiter, hook_name, **kwargs):
            events['extended_stats_called'] = True

        old = logger.exception
        logger.exception = lambda x: x

        hooks = {'extended_stats': (hook, False)}
        testfile, arbiter = self.run_with_hooks(hooks)
        yield arbiter.start()
        try:
            if extended:
                yield self._extended_stats()
            else:
                yield self._stats()
            resp_status = yield self.get_status()
            self.assertEqual(resp_status, 'active')
        finally:
            yield arbiter.stop()
            logger.exception = old

        self.assertEqual(events['extended_stats_called'], extended)

    @tornado.testing.gen_test
    def test_before_start(self):
        yield self._test_hooks()

    @tornado.testing.gen_test
    def test_before_start_fails(self):
        yield self._test_hooks(behavior=ERROR, status='stopped')

    @tornado.testing.gen_test
    def test_before_start_false(self):
        yield self._test_hooks(behavior=FAILURE, status='stopped',
                               hook_name='after_start')

    @tornado.testing.gen_test
    def test_after_start(self):
        yield self._test_hooks(hook_name='after_start')

    @tornado.testing.gen_test
    def test_after_start_fails(self):
        if captured_output:
            with captured_output('stderr'):
                yield self._test_hooks(behavior=ERROR, status='stopped',
                                       hook_name='after_start')

    @tornado.testing.gen_test
    def test_after_start_false(self):
        yield self._test_hooks(behavior=FAILURE, status='stopped',
                               hook_name='after_start')

    @tornado.testing.gen_test
    def test_before_stop(self):
        yield self._test_hooks(hook_name='before_stop', status='stopped',
                               call=self._stop)

    @tornado.testing.gen_test
    def _hook_signal_kwargs_test_function(self, kwargs):
        self.assertTrue("pid" not in kwargs)
        self.assertTrue("signum" not in kwargs)
        self.assertTrue(kwargs["pid"] in (signal.SIGTERM, signal.SIGKILL))
        self.assertTrue(int(kwargs["signum"]) > 1)

    @tornado.testing.gen_test
    def test_before_signal(self):
        func = self._hook_signal_kwargs_test_function
        yield self._test_hooks(hook_name='before_signal', status='stopped',
                               call=self._stop,
                               hook_kwargs_test_function=func)

    @tornado.testing.gen_test
    def test_after_signal(self):
        func = self._hook_signal_kwargs_test_function
        yield self._test_hooks(hook_name='after_signal', status='stopped',
                               call=self._stop,
                               hook_kwargs_test_function=func)

    @tornado.testing.gen_test
    def test_before_stop_fails(self):
        if captured_output:
            with captured_output('stdout'):
                yield self._test_hooks(behavior=ERROR, status='stopped',
                                       hook_name='before_stop',
                                       call=self._stop)

    @tornado.testing.gen_test
    def test_before_stop_false(self):
        yield self._test_hooks(behavior=FAILURE, status='stopped',
                               hook_name='before_stop', call=self._stop)

    @tornado.testing.gen_test
    def test_after_stop(self):
        yield self._test_hooks(hook_name='after_stop', status='stopped',
                               call=self._stop)

    @tornado.testing.gen_test
    def test_after_stop_fails(self):
        if captured_output:
            with captured_output('stdout'):
                yield self._test_hooks(behavior=ERROR, status='stopped',
                                       hook_name='after_stop',
                                       call=self._stop)

    @tornado.testing.gen_test
    def test_after_stop_false(self):
        yield self._test_hooks(behavior=FAILURE, status='stopped',
                               hook_name='after_stop', call=self._stop)

    @tornado.testing.gen_test
    def test_before_spawn(self):
        yield self._test_hooks(hook_name='before_spawn')

    @tornado.testing.gen_test
    def test_before_spawn_failure(self):
        if captured_output:
            with captured_output('stdout'):
                yield self._test_hooks(behavior=ERROR, status='stopped',
                                       hook_name='before_spawn',
                                       call=self._stop)

    @tornado.testing.gen_test
    def test_before_spawn_false(self):
        yield self._test_hooks(behavior=FAILURE, status='stopped',
                               hook_name='before_spawn', call=self._stop)

    @tornado.testing.gen_test
    def test_after_spawn(self):
        yield self._test_hooks(hook_name='after_spawn')

    @tornado.testing.gen_test
    def test_after_spawn_failure(self):
        if captured_output:
            with captured_output('stdout'):
                yield self._test_hooks(behavior=ERROR, status='stopped',
                                       hook_name='after_spawn',
                                       call=self._stop)

    @tornado.testing.gen_test
    def test_after_spawn_false(self):
        yield self._test_hooks(behavior=FAILURE, status='stopped',
                               hook_name='after_spawn', call=self._stop)

    @tornado.testing.gen_test
    def test_extended_stats(self):
        yield self._test_extended_stats()
        yield self._test_extended_stats(extended=True)


def oneshot_process(test_file):
    pass


class RespawnTest(TestCircus):

    @tornado.testing.gen_test
    def test_not_respawning(self):
        oneshot_process = 'circus.tests.test_watcher.oneshot_process'
        testfile, arbiter = self._create_circus(oneshot_process,
                                                respawn=False, async=True)
        yield arbiter.start()
        watcher = arbiter.watchers[-1]
        try:
            # Per default, we shouldn't respawn processes,
            # so we should have one process, even if in a dead state.
            resp = yield self.call("numprocesses", name="test")
            self.assertEqual(resp['numprocesses'], 1)

            # let's reap processes and explicitely ask for process management
            yield watcher.reap_and_manage_processes()

            # we should have zero processes (the process shouldn't respawn)
            self.assertEqual(len(watcher.processes), 0)

            # If we explicitely ask the watcher to respawn its processes,
            # ensure it's doing so.
            yield watcher.start()
            self.assertEqual(len(watcher.processes), 1)
        finally:
            yield arbiter.stop()

    @tornado.testing.gen_test
    def test_stopping_a_watcher_doesnt_spawn(self):
        watcher = Watcher("foo", "foobar", respawn=True, numprocesses=3,
                          graceful_timeout=0)
        watcher._status = "started"

        watcher.spawn_processes = MagicMockFuture()
        watcher.send_signal = mock.MagicMock()

        # We have one running process and a dead one.
        watcher.processes = {1234: FakeProcess(1234, status=RUNNING),
                             1235: FakeProcess(1235, status=RUNNING)}

        # When we call manage_process(), the watcher should try to spawn a new
        # process since we aim to have 3 of them.
        yield watcher.manage_processes()
        self.assertTrue(watcher.spawn_processes.called)
        # Now, we want to stop everything.
        watcher.processes = {1234: FakeProcess(1234, status=RUNNING),
                             1235: FakeProcess(1235, status=RUNNING)}
        watcher.spawn_processes.reset_mock()
        yield watcher.stop()
        yield watcher.manage_processes()
        # And be sure we don't spawn new processes in the meantime.
        self.assertFalse(watcher.spawn_processes.called)

test_suite = EasyTestSuite(__name__)

########NEW FILE########
__FILENAME__ = util
import functools
import logging
import logging.config
import os
import re
import shlex
import socket
import sys
import time
import traceback
import json
try:
    import yaml
except ImportError:
    yaml = None  # NOQA
try:
    import pwd
    import grp
    import fcntl
except ImportError:
    fcntl = None
    grp = None
    pwd = None
from tornado.ioloop import IOLoop
from tornado import gen
from tornado import concurrent
from circus.py3compat import (
    integer_types, bytestring, raise_with_tb, text_type
)
try:
    from configparser import (
        ConfigParser, MissingSectionHeaderError, ParsingError, DEFAULTSECT
    )
except ImportError:
    from ConfigParser import (  # NOQA
        ConfigParser, MissingSectionHeaderError, ParsingError, DEFAULTSECT
    )
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse  # NOQA

from datetime import timedelta
from functools import wraps
import signal
from pipes import quote as shell_escape_arg

try:
    import importlib
    reload_module = importlib.reload
except (ImportError, AttributeError):
    from imp import reload as reload_module

from zmq import ssh


from psutil import AccessDenied, NoSuchProcess, Process

from circus.exc import ConflictError
from circus import logger
from circus.py3compat import string_types


# default endpoints
DEFAULT_ENDPOINT_DEALER = "tcp://127.0.0.1:5555"
DEFAULT_ENDPOINT_SUB = "tcp://127.0.0.1:5556"
DEFAULT_ENDPOINT_STATS = "tcp://127.0.0.1:5557"
DEFAULT_ENDPOINT_MULTICAST = "udp://237.219.251.97:12027"


try:
    from setproctitle import setproctitle

    def _setproctitle(title):       # NOQA
        setproctitle(title)
except ImportError:
    def _setproctitle(title):       # NOQA
        return


MAXFD = 1024
if hasattr(os, "devnull"):
    REDIRECT_TO = os.devnull  # PRAGMA: NOCOVER
else:
    REDIRECT_TO = "/dev/null"  # PRAGMA: NOCOVER

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG}

LOG_FMT = r"%(asctime)s %(name)s[%(process)d] [%(levelname)s] %(message)s"
LOG_DATE_FMT = r"%Y-%m-%d %H:%M:%S"
LOG_DATE_SYSLOG_FMT = r"%b %d %H:%M:%S"
_SYMBOLS = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
_all_signals = {}


def get_working_dir():
    """Returns current path, try to use PWD env first.

    Since os.getcwd() resolves symlinks, we want to use
    PWD first if present.
    """
    pwd_ = os.environ.get('PWD')
    cwd = os.getcwd()

    if pwd_ is None:
        return cwd

    # if pwd is the same physical file than the one
    # pointed by os.getcwd(), we use it.
    try:
        pwd_stat = os.stat(pwd_)
        cwd_stat = os.stat(cwd)

        if pwd_stat.ino == cwd_stat.ino and pwd_stat.dev == cwd_stat.dev:
            return pwd_
    except Exception:
        pass

    # otherwise, just use os.getcwd()
    return cwd


def bytes2human(n):
    """Translates bytes into a human repr.
    """
    if not isinstance(n, integer_types):
        raise TypeError(n)

    prefix = {}
    for i, s in enumerate(_SYMBOLS):
        prefix[s] = 1 << (i + 1) * 10

    for s in reversed(_SYMBOLS):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "%sB" % n


_HSYMBOLS = {
    'customary': ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext': ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                      'zetta', 'iotta'),
    'iec': ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext': ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                'zebi', 'yobi'),
}


_HSYMBOLS_VALUES = _HSYMBOLS.values()


def human2bytes(s):
    init = s
    num = ""
    while s and s[0:1].isdigit() or s[0:1] == '.':
        num += s[0]
        s = s[1:]

    num = float(num)
    letter = s.strip()

    for sset in _HSYMBOLS_VALUES:
        if letter in sset:
            break

    else:
        if letter == 'k':
            # treat 'k' as an alias for 'K' as per: http://goo.gl/kTQMs
            sset = _HSYMBOLS['customary']
            letter = letter.upper()
        else:
            raise ValueError("can't interpret %r" % init)

    prefix = {sset[0]: 1}
    for i, s in enumerate(sset[1:]):
        prefix[s] = 1 << (i+1) * 10

    return int(num * prefix[letter])


# XXX weak dict ?
_PROCS = {}


def get_info(process=None, interval=0, with_childs=False):
    """Return information about a process. (can be an pid or a Process object)

    If process is None, will return the information about the current process.
    """
    # XXX moce get_info to circus.process ?
    from circus.process import (get_children, get_memory_info,
                                get_cpu_percent, get_memory_percent,
                                get_cpu_times, get_nice, get_cmdline,
                                get_create_time, get_username)

    if process is None or isinstance(process, int):
        if process is None:
            pid = os.getpid()
        else:
            pid = process

        if pid in _PROCS:
            process = _PROCS[pid]
        else:
            _PROCS[pid] = process = Process(pid)

    info = {}
    try:
        mem_info = get_memory_info(process)
        info['mem_info1'] = bytes2human(mem_info[0])
        info['mem_info2'] = bytes2human(mem_info[1])
    except AccessDenied:
        info['mem_info1'] = info['mem_info2'] = "N/A"

    try:
        info['cpu'] = get_cpu_percent(process, interval=interval)
    except AccessDenied:
        info['cpu'] = "N/A"

    try:
        info['mem'] = round(get_memory_percent(process), 1)
    except AccessDenied:
        info['mem'] = "N/A"

    try:
        cpu_times = get_cpu_times(process)
        ctime = timedelta(seconds=sum(cpu_times))
        ctime = "%s:%s.%s" % (ctime.seconds // 60 % 60,
                              str((ctime.seconds % 60)).zfill(2),
                              str(ctime.microseconds)[:2])
    except AccessDenied:
        ctime = "N/A"

    info['ctime'] = ctime

    try:
        info['pid'] = process.pid
    except AccessDenied:
        info['pid'] = 'N/A'

    try:
        info['username'] = get_username(process)
    except AccessDenied:
        info['username'] = 'N/A'

    try:
        info['nice'] = get_nice(process)
    except AccessDenied:
        info['nice'] = 'N/A'
    except NoSuchProcess:
        info['nice'] = 'Zombie'

    raw_cmdline = get_cmdline(process)

    try:
        cmdline = os.path.basename(shlex.split(raw_cmdline[0])[0])
    except (AccessDenied, IndexError):
        cmdline = "N/A"

    try:
        info['create_time'] = get_create_time(process)
    except AccessDenied:
        info['create_time'] = 'N/A'

    try:
        info['age'] = time.time() - get_create_time(process)
    except TypeError:
        info['create_time'] = get_create_time(process)
    except AccessDenied:
        info['age'] = 'N/A'

    info['cmdline'] = cmdline

    info['children'] = []
    if with_childs:
        for child in get_children(process):
            info['children'].append(get_info(child, interval=interval))

    return info

TRUTHY_STRINGS = ('yes', 'true', 'on', '1')
FALSY_STRINGS = ('no', 'false', 'off', '0')


def to_bool(s):
    if isinstance(s, bool):
        return s

    if s.lower().strip() in TRUTHY_STRINGS:
        return True
    elif s.lower().strip() in FALSY_STRINGS:
        return False
    else:
        raise ValueError("%r is not a boolean" % s)


def to_signum(signum):
    if not _all_signals:
        for name in dir(signal):
            if name.startswith('SIG'):
                value = getattr(signal, name)
                _all_signals[name[3:]] = value
                _all_signals[name] = value
                _all_signals[str(value)] = value
                _all_signals[value] = value

    try:
        if isinstance(signum, string_types):
            signum = signum.upper()
        return _all_signals[signum]
    except KeyError:
        raise ValueError('signal invalid')


if pwd is None:

    def to_uid(name):
        raise RuntimeError("'to_uid' not available on this operating system")

else:

    def to_uid(name):  # NOQA
        """Return an uid, given a user name.
        If the name is an integer, make sure it's an existing uid.

        If the user name is unknown, raises a ValueError.
        """
        try:
            name = int(name)
        except ValueError:
            pass

        if isinstance(name, int):
            try:
                pwd.getpwuid(name)
                return name
            except KeyError:
                raise ValueError("%r isn't a valid user id" % name)

        from circus.py3compat import string_types  # circular import fix

        if not isinstance(name, string_types):
            raise TypeError(name)

        try:
            return pwd.getpwnam(name).pw_uid
        except KeyError:
            raise ValueError("%r isn't a valid user name" % name)

if grp is None:

    def to_gid(name):
        raise RuntimeError("'to_gid' not available on this operating system")

else:

    def to_gid(name):  # NOQA
        """Return a gid, given a group name

        If the group name is unknown, raises a ValueError.
        """
        try:
            name = int(name)
        except ValueError:
            pass

        if isinstance(name, int):
            try:
                grp.getgrgid(name)
                return name
            # getgrid may raises overflow error on mac/os x,
            # fixed in python2.7.5
            # see http://bugs.python.org/issue17531
            except (KeyError, OverflowError):
                raise ValueError("No such group: %r" % name)

        from circus.py3compat import string_types  # circular import fix

        if not isinstance(name, string_types):
            raise TypeError(name)

        try:
            return grp.getgrnam(name).gr_gid
        except KeyError:
            raise ValueError("No such group: %r" % name)


def get_username_from_uid(uid):
    """Return the username of a given uid."""
    if isinstance(uid, int):
        return pwd.getpwuid(uid).pw_name
    return uid


def get_default_gid(uid):
    """Return the default group of a specific user."""
    if isinstance(uid, int):
        return pwd.getpwuid(uid).pw_gid
    return pwd.getpwnam(uid).pw_gid


def parse_env_str(env_str):
    env = dict()
    for kvs in env_str.split(','):
        k, v = kvs.split('=')
        env[k.strip()] = v.strip()
    return parse_env_dict(env)


def parse_env_dict(env):
    ret = dict()
    for k, v in env.items():
        v = re.sub(r'\$([A-Z]+[A-Z0-9_]*)', replace_env, v)
        ret[k.strip()] = v.strip()
    return ret


def replace_env(var):
    return os.getenv(var.group(1))


def env_to_str(env):
    if not env:
        return ""
    return ",".join(["%s=%s" % (k, v) for k, v in
                     sorted(env.items(), key=lambda i: i[0])])


if fcntl is None:

    def close_on_exec(fd):
        raise RuntimeError(
            "'close_on_exec' not available on this operating system")

else:

    def close_on_exec(fd):  # NOQA
        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        flags |= fcntl.FD_CLOEXEC
        fcntl.fcntl(fd, fcntl.F_SETFD, flags)


def get_python_version():
    """Get a 3 element tuple with the python version"""
    return sys.version_info[:3]


INDENTATION_LEVEL = 0


def debuglog(func):
    @wraps(func)
    def _log(self, *args, **kw):
        if os.environ.get('DEBUG') is None:
            return func(self, *args, **kw)

        from circus import logger
        cls = self.__class__.__name__
        global INDENTATION_LEVEL
        func_name = func.func_name if hasattr(func, 'func_name')\
            else func.__name__
        logger.debug("    " * INDENTATION_LEVEL +
                     "'%s.%s' starts" % (cls, func_name))
        INDENTATION_LEVEL += 1
        try:
            return func(self, *args, **kw)
        finally:
            INDENTATION_LEVEL -= 1
            logger.debug("    " * INDENTATION_LEVEL +
                         "'%s.%s' ends" % (cls, func_name))

    return _log


def convert_opt(key, val):
    """ get opt
    """
    if key == "env":
        val = env_to_str(val)
    else:
        if val is None:
            val = ""
        else:
            val = str(val)
    return val


# taken from werkzeug
class ImportStringError(ImportError):

    """Provides information about a failed :func:`import_string` attempt."""

    #: String in dotted notation that failed to be imported.
    import_name = None
    #: Wrapped exception.
    exception = None

    def __init__(self, import_name, exception):
        self.import_name = import_name
        self.exception = exception

        msg = (
            'import_string() failed for %r. Possible reasons are:\n\n'
            '- missing __init__.py in a package;\n'
            '- package or module path not included in sys.path;\n'
            '- duplicated package or module name taking precedence in '
            'sys.path;\n'
            '- missing module, class, function or variable;\n\n'
            'Debugged import:\n\n%s\n\n'
            'Original exception:\n\n%s: %s')

        name = ''
        tracked = []
        for part in import_name.replace(':', '.').split('.'):
            name += (name and '.') + part
            imported = resolve_name(name, silent=True)
            if imported:
                tracked.append((name, getattr(imported, '__file__', None)))
            else:
                track = ['- %r found in %r.' % (n, i) for n, i in tracked]
                track.append('- %r not found.' % name)
                msg = msg % (import_name, '\n'.join(track),
                             exception.__class__.__name__, str(exception))
                break

        ImportError.__init__(self, msg)

    def __repr__(self):
        return '<%s(%r, %r)>' % (self.__class__.__name__, self.import_name,
                                 self.exception)


def resolve_name(import_name, silent=False, reload=False):
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If `silent` is True the return value will be `None` if the import fails.

    :param import_name: the dotted name for the object to import.
    :param silent: if set to `True` import errors are ignored and
                   `None` is returned instead.
    :param reload: if set to `True` modules that are already loaded will be
                   reloaded
    :return: imported object
    """
    # force the import name to automatically convert to strings
    import_name = bytestring(import_name)
    try:
        if ':' in import_name:
            module, obj = import_name.split(':', 1)
        elif '.' in import_name and import_name not in sys.modules:
            module, obj = import_name.rsplit('.', 1)
        else:
            module, obj = import_name, None
            # __import__ is not able to handle unicode strings in the fromlist

        mod = None
        # if the module is a package
        if reload and module in sys.modules:
            try:
                importlib.invalidate_caches()
            except Exception:
                pass
            try:
                mod = reload_module(sys.modules[module])
            except Exception:
                pass
        if not mod:
            if not obj:
                return __import__(module)
            try:
                mod = __import__(module, None, None, [obj])
            except ImportError:
                if ':' in import_name:
                    raise
                return __import__(import_name)
        if not obj:
            return mod
        try:
            return getattr(mod, obj)
        except AttributeError:
            # support importing modules not yet set up by the parent module
            # (or package for that matter)
            if ':' in import_name:
                raise
            return __import__(import_name)
    except ImportError as e:
        if not silent:
            raise_with_tb(ImportStringError(import_name, e))


_SECTION_NAME = '\w\.\-'
_PATTERN1 = r'\$\(%%s\.([%s]+)\)' % _SECTION_NAME
_PATTERN2 = r'\(\(%%s\.([%s]+)\)\)' % _SECTION_NAME
_CIRCUS_VAR = re.compile(_PATTERN1 % 'circus' + '|' +
                         _PATTERN2 % 'circus', re.I)


def replace_gnu_args(data, prefix='circus', **options):
    fmt_options = {}
    for key, value in options.items():
        key = key.lower()

        if prefix is not None:
            key = '%s.%s' % (prefix, key)

        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                subkey = subkey.lower()
                subkey = '%s.%s' % (key, subkey)
                fmt_options[subkey] = subvalue
        else:
            fmt_options[key] = value

    if prefix is None:
        pattern = r'\$\(([%s]+)\)|\(\(([%s]+)\)\)' % (_SECTION_NAME,
                                                      _SECTION_NAME)
        match = re.compile(pattern, re.I)
    elif prefix == 'circus':
        match = _CIRCUS_VAR
    else:
        match = re.compile(_PATTERN1 % prefix + '|' + _PATTERN2 % prefix,
                           re.I)

    def _repl(matchobj):
        option = None

        for result in matchobj.groups():
            if result is not None:
                option = result.lower()
                break

        if prefix is not None and not option.startswith(prefix):
            option = '%s.%s' % (prefix, option)

        if option in fmt_options:
            return str(fmt_options[option])

        return matchobj.group()

    return match.sub(_repl, data)


class ObjectDict(dict):

    def __getattr__(self, item):
        return self[item]


def configure_logger(logger, level='INFO', output="-", loggerconfig=None,
                     name=None):
    if loggerconfig is None or loggerconfig.lower().strip() == "default":
        root_logger = logging.getLogger()
        loglevel = LOG_LEVELS.get(level.lower(), logging.INFO)
        root_logger.setLevel(loglevel)
        datefmt = LOG_DATE_FMT
        if output in ("-", "stdout"):
            handler = logging.StreamHandler()
        elif output.startswith('syslog://'):
            # URLs are syslog://host[:port]?facility or syslog:///path?facility
            info = urlparse(output)
            facility = 'user'
            if info.query in logging.handlers.SysLogHandler.facility_names:
                facility = info.query
            if info.netloc:
                address = (info.netloc, info.port or 514)
            else:
                address = info.path
            datefmt = LOG_DATE_SYSLOG_FMT
            handler = logging.handlers.SysLogHandler(
                address=address, facility=facility)
        else:
            handler = logging.handlers.WatchedFileHandler(output)
            close_on_exec(handler.stream.fileno())
        formatter = logging.Formatter(fmt=LOG_FMT, datefmt=datefmt)
        handler.setFormatter(formatter)
        root_logger.handlers = [handler]
    else:
        loggerconfig = os.path.abspath(loggerconfig)
        if loggerconfig.lower().endswith(".ini"):
            logging.config.fileConfig(loggerconfig,
                                      disable_existing_loggers=True)
        elif loggerconfig.lower().endswith(".json"):
            if not hasattr(logging.config, "dictConfig"):
                raise Exception("Logger configuration file %s appears to be "
                                "a JSON file but this version of Python "
                                "does not support the "
                                "logging.config.dictConfig function. Try "
                                "Python 2.7.")
            with open(loggerconfig, "r") as fh:
                logging.config.dictConfig(json.loads(fh.read()))
        elif loggerconfig.lower().endswith(".yaml"):
            if not hasattr(logging.config, "dictConfig"):
                raise Exception("Logger configuration file %s appears to be "
                                "a YAML file but this version of Python "
                                "does not support the "
                                "logging.config.dictConfig function. Try "
                                "Python 2.7.")
            if yaml is None:
                raise Exception("Logger configuration file %s appears to be "
                                "a YAML file but PyYAML is not available. "
                                "Try: pip install PyYAML"
                                % (shell_escape_arg(loggerconfig),))
            with open(loggerconfig, "r") as fh:
                logging.config.dictConfig(yaml.load(fh.read()))
        else:
            raise Exception("Logger configuration file %s is not in one "
                            "of the recognized formats.  The file name "
                            "should be: *.ini, *.json or *.yaml."
                            % (shell_escape_arg(loggerconfig),))


class StrictConfigParser(ConfigParser):

    def _read(self, fp, fpname):
        cursect = None                        # None, or a dictionary
        optname = None
        lineno = 0
        e = None                              # None, or an exception
        while True:
            line = fp.readline()
            if not line:
                break
            lineno += 1
            # comment or blank line?
            if line.strip() == '' or line[0] in '#;':
                continue
            if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
                # no leading whitespace
                continue
            # continuation line?
            if line[0].isspace() and cursect is not None and optname:
                value = line.strip()
                if value:
                    cursect[optname].append(value)
            # a section header or option header?
            else:
                # is it a section header?
                mo = self.SECTCRE.match(line)
                if mo:
                    sectname = mo.group('header')
                    if sectname in self._sections:
                        # we're extending/overriding, we're good
                        cursect = self._sections[sectname]
                    elif sectname == DEFAULTSECT:
                        cursect = self._defaults
                    else:
                        cursect = self._dict()
                        cursect['__name__'] = sectname
                        self._sections[sectname] = cursect
                    # So sections can't start with a continuation line
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    raise MissingSectionHeaderError(fpname, lineno, line)
                # an option line?
                else:
                    try:
                        mo = self._optcre.match(line)   # 2.7
                    except AttributeError:
                        mo = self.OPTCRE.match(line)    # 2.6
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        self.optionxform = text_type
                        optname = self.optionxform(optname.rstrip())
                        # We don't want to override.
                        if optname in cursect:
                            continue
                        # This check is fine because the OPTCRE cannot
                        # match if it would set optval to None
                        if optval is not None:
                            if vi in ('=', ':') and ';' in optval:
                                # ';' is a comment delimiter only if it follows
                                # a spacing character
                                pos = optval.find(';')
                                if pos != -1 and optval[pos - 1].isspace():
                                    optval = optval[:pos]
                            optval = optval.strip()
                            # allow empty values
                            if optval == '""':
                                optval = ''
                            cursect[optname] = [optval]
                        else:
                            # valueless option handling
                            cursect[optname] = optval
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not e:
                            e = ParsingError(fpname)
                        e.append(lineno, repr(line))
        # if any parsing errors occurred, raise an exception
        if e:
            raise e

        # join the multi-line values collected while reading
        all_sections = [self._defaults]
        all_sections.extend(self._sections.values())
        for options in all_sections:
            for name, val in options.items():
                if isinstance(val, list):
                    options[name] = '\n'.join(val)


def get_connection(socket, endpoint, ssh_server=None, ssh_keyfile=None):
    if ssh_server is None:
        socket.connect(endpoint)
    else:
        try:
            try:
                ssh.tunnel_connection(socket, endpoint, ssh_server,
                                      keyfile=ssh_keyfile)
            except ImportError:
                ssh.tunnel_connection(socket, endpoint, ssh_server,
                                      keyfile=ssh_keyfile, paramiko=True)
        except ImportError:
            raise ImportError("pexpect was not found, and failed to use "
                              "Paramiko.  You need to install Paramiko")


def load_virtualenv(watcher):
    if not watcher.copy_env:
        raise ValueError('copy_env must be True to to use virtualenv')

    py_ver = sys.version.split()[0][:3]

    # XXX Posix scheme - need to add others
    sitedir = os.path.join(watcher.virtualenv, 'lib', 'python' + py_ver,
                           'site-packages')

    if not os.path.exists(sitedir):
        raise ValueError("%s does not exist" % sitedir)

    bindir = os.path.join(watcher.virtualenv, 'bin')

    if os.path.exists(bindir):
        watcher.env['PATH'] = ':'.join([bindir, watcher.env.get('PATH', '')])

    def process_pth(sitedir, name):
        packages = set()
        fullname = os.path.join(sitedir, name)
        try:
            f = open(fullname, "rU")
        except IOError:
            return
        with f:
            for line in f.readlines():
                if line.startswith(("#", "import")):
                    continue
                line = line.rstrip()
                pkg_path = os.path.abspath(os.path.join(sitedir, line))
                if os.path.exists(pkg_path):
                    packages.add(pkg_path)
        return packages

    venv_pkgs = set()
    dotpth = os.extsep + "pth"
    for name in os.listdir(sitedir):
        if name.endswith(dotpth):
            try:
                packages = process_pth(sitedir, name)
                if packages:
                    venv_pkgs |= packages
            except OSError:
                continue

    py_path = watcher.env.get('PYTHONPATH')
    path = None

    if venv_pkgs:
        venv_path = os.pathsep.join(venv_pkgs)

        if py_path:
            path = os.pathsep.join([venv_path, py_path])
        else:
            path = venv_path

    # Add watcher virtualenv site-packages dir to the python path
    if path and sitedir not in path.split(os.pathsep):
        path = os.pathsep.join([path, sitedir])
    else:
        if py_path:
            path = os.pathsep.join([py_path, sitedir])
        else:
            path = sitedir

    watcher.env['PYTHONPATH'] = path


def create_udp_socket(mcast_addr, mcast_port):
    """Create an udp multicast socket for circusd cluster auto-discovery.
    mcast_addr must be between 224.0.0.0 and 239.255.255.255
    """
    try:
        ip_splitted = list(map(int, mcast_addr.split('.')))
        mcast_port = int(mcast_port)
    except ValueError:
        raise ValueError('Wrong UDP multicast_endpoint configuration. Should '
                         'looks like: "%r"' % DEFAULT_ENDPOINT_MULTICAST)

    if ip_splitted[0] < 224 or ip_splitted[0] > 239:
        raise ValueError('The multicast address is not valid should be '
                         'between 224.0.0.0 and 239.255.255.255')

    any_addr = "0.0.0.0"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # Allow reutilization of addr
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Some platform exposes SO_REUSEPORT
    if hasattr(socket, 'SO_REUSEPORT'):
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except socket.error:
            # see #699
            pass
    # Put packet ttl to max
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
    # Register socket to multicast group
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                    socket.inet_aton(mcast_addr) + socket.inet_aton(any_addr))
    # And finally bind all interfaces
    sock.bind((any_addr, mcast_port))
    return sock


# taken from http://stackoverflow.com/questions/1165352

class DictDiffer(object):

    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """

    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = (set(current_dict.keys()),
                                           set(past_dict.keys()))
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return set(o for o in self.intersect
                   if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect
                   if self.past_dict[o] == self.current_dict[o])


def dict_differ(dict1, dict2):
    return len(DictDiffer(dict1, dict2).changed()) > 0


def _synchronized_cb(arbiter, future):
    if arbiter is not None:
        arbiter._exclusive_running_command = None


def synchronized(name):
    def real_decorator(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            arbiter = None
            if hasattr(self, "arbiter"):
                arbiter = self.arbiter
            elif hasattr(self, "_exclusive_running_command"):
                arbiter = self
            if arbiter is not None:
                if arbiter._restarting:
                    raise ConflictError("arbiter is restarting...")
                if arbiter._exclusive_running_command is not None:
                    raise ConflictError("arbiter is already running %s command"
                                        % arbiter._exclusive_running_command)
                arbiter._exclusive_running_command = name
            resp = None
            try:
                resp = f(self, *args, **kwargs)
            finally:
                if isinstance(resp, concurrent.Future):
                    cb = functools.partial(_synchronized_cb, arbiter)
                    resp.add_done_callback(cb)
                else:
                    if arbiter is not None:
                        arbiter._exclusive_running_command = None
            return resp
        return wrapper
    return real_decorator


def tornado_sleep(duration):
    """Sleep without blocking the tornado event loop

    To use with a gen.coroutines decorated function
    Thanks to http://stackoverflow.com/a/11135204/433050
    """
    return gen.Task(IOLoop.instance().add_timeout, time.time() + duration)


class TransformableFuture(concurrent.Future):

    _upstream_future = None
    _upstream_callback = None
    _transform_function = lambda x: x
    _result = None
    _exception = None

    def set_transform_function(self, fn):
        self._transform_function = fn

    def set_upstream_future(self, upstream_future):
        self._upstream_future = upstream_future

    def result(self, timeout=None):
        if self._upstream_future is None:
            raise Exception("upstream_future is not set")
        return self._transform_function(self._result)

    def _internal_callback(self, future):
        self._result = future.result()
        self._exception = future.exception()
        if self._upstream_callback is not None:
            self._upstream_callback(self)

    def add_done_callback(self, fn):
        if self._upstream_future is None:
            raise Exception("upstream_future is not set")
        self._upstream_callback = fn
        self._upstream_future.add_done_callback(self._internal_callback)

    def exception(self, timeout=None):
        if self._exception:
            return self._exception
        else:
            return None


def check_future_exception_and_log(future):
    if isinstance(future, concurrent.Future):
        exception = future.exception()
        if exception is not None:
            logger.error("exception %s caught" % exception)
            if hasattr(future, "exc_info"):
                exc_info = future.exc_info()
                traceback.print_tb(exc_info[2])
            return exception


def is_win():
    """checks if platform is Windows"""
    return sys.platform == "win32"

########NEW FILE########
__FILENAME__ = watcher
import copy
import errno
import os
import signal
import time
import sys
from random import randint
try:
    from itertools import zip_longest as izip_longest
except ImportError:
    from itertools import izip_longest  # NOQA
import site
from tornado import gen

from psutil import NoSuchProcess
import zmq.utils.jsonapi as json
from zmq.eventloop import ioloop

from circus.process import Process, DEAD_OR_ZOMBIE, UNEXISTING
from circus import logger
from circus import util
from circus.stream import get_pipe_redirector, get_stream
from circus.util import parse_env_dict, resolve_name, tornado_sleep
from circus.py3compat import bytestring, is_callable, b


class Watcher(object):

    """
    Class managing a list of processes for a given command.

    Options:

    - **name**: name given to the watcher. Used to uniquely identify it.

    - **cmd**: the command to run. May contain *$WID*, which will be
      replaced by **wid**.

    - **args**: the arguments for the command to run. Can be a list or
      a string. If **args** is  a string, it's splitted using
      :func:`shlex.split`. Defaults to None.

    - **numprocesses**: Number of processes to run.

    - **working_dir**: the working directory to run the command in. If
      not provided, will default to the current working directory.

    - **shell**: if *True*, will run the command in the shell
      environment. *False* by default. **warning: this is a
      security hazard**.

    - **uid**: if given, is the user id or name the command should run
      with. The current uid is the default.

    - **gid**: if given, is the group id or name the command should run
      with. The current gid is the default.

    - **send_hup**: if True, a process reload will be done by sending
      the SIGHUP signal. Defaults to False.

    - **stop_signal**: the signal to send when stopping the process.
      Defaults to SIGTERM.

    - **stop_children**: send the **stop_signal** to the children too.
      Defaults to False.

    - **env**: a mapping containing the environment variables the command
      will run with. Optional.

    - **rlimits**: a mapping containing rlimit names and values that will
      be set before the command runs.

    - **stdout_stream**: a mapping that defines the stream for
      the process stdout. Defaults to None.

      Optional. When provided, *stdout_stream* is a mapping containing up to
      three keys:

      - **class**: the stream class. Defaults to
        `circus.stream.FileStream`
      - **filename**: the filename, if using a FileStream
      - **max_bytes**: maximum file size, after which a new output file is
        opened. defaults to 0 which means no maximum size (only applicable
        with FileStream).
      - **backup_count**: how many backups to retain when rotating files
        according to the max_bytes parameter. defaults to 0 which means
        no backups are made (only applicable with FileStream)

      This mapping will be used to create a stream callable of the specified
      class.
      Each entry received by the callable is a mapping containing:

      - **pid** - the process pid
      - **name** - the stream name (*stderr* or *stdout*)
      - **data** - the data

    - **stderr_stream**: a mapping that defines the stream for
      the process stderr. Defaults to None.

      Optional. When provided, *stderr_stream* is a mapping containing up to
      three keys:
      - **class**: the stream class. Defaults to `circus.stream.FileStream`
      - **filename**: the filename, if using a FileStream
      - **max_bytes**: maximum file size, after which a new output file is
        opened. defaults to 0 which means no maximum size (only applicable
        with FileStream)
      - **backup_count**: how many backups to retain when rotating files
        according to the max_bytes parameter. defaults to 0 which means
        no backups are made (only applicable with FileStream).

      This mapping will be used to create a stream callable of the specified
      class.

      Each entry received by the callable is a mapping containing:

      - **pid** - the process pid
      - **name** - the stream name (*stderr* or *stdout*)
      - **data** - the data

    - **priority** -- integer that defines a priority for the watcher. When
      the Arbiter do some operations on all watchers, it will sort them
      with this field, from the bigger number to the smallest.
      (default: 0)

    - **singleton** -- If True, this watcher has a single process.
      (default:False)

    - **use_sockets** -- If True, the processes will inherit the file
      descriptors, thus can reuse the sockets opened by circusd.
      (default: False)

    - **on_demand** -- If True, the processes will be started only
      at the first connection to the socket
      (default: False)

    - **copy_env** -- If True, the environment in which circus is running
      run will be reproduced for the workers. (default: False)

    - **copy_path** -- If True, circusd *sys.path* is sent to the
      process through *PYTHONPATH*. You must activate **copy_env** for
      **copy_path** to work. (default: False)

    - **max_age**: If set after around max_age seconds, the process is
      replaced with a new one.  (default: 0, Disabled)

    - **max_age_variance**: The maximum number of seconds that can be added to
      max_age. This extra value is to avoid restarting all processes at the
      same time.  A process will live between max_age and
      max_age + max_age_variance seconds.

    - **hooks**: callback functions for hooking into the watcher startup
      and shutdown process. **hooks** is a dict where each key is the hook
      name and each value is a 2-tuple with the name of the callable
      or the callabled itself and a boolean flag indicating if an
      exception occuring in the hook should not be ignored.
      Possible values for the hook name: *before_start*, *after_start*,
      *before_spawn*, *after_spawn*, *before_stop*, *after_stop*.,
      *before_signal*, *after_signal* or *extended_stats*.

    - **options** -- extra options for the worker. All options
      found in the configuration file for instance, are passed
      in this mapping -- this can be used by plugins for watcher-specific
      options.

    - **respawn** -- If set to False, the processes handled by a watcher will
      not be respawned automatically. (default: True)

    - **virtualenv** -- The root directory of a virtualenv. If provided, the
      watcher will load the environment for its execution. (default: None)

    - **close_child_stdout**: If True, closes the stdout after the fork.
      default: False.

    - **close_child_stderr**: If True, closes the stderr after the fork.
      default: False.
    """

    def __init__(self, name, cmd, args=None, numprocesses=1, warmup_delay=0.,
                 working_dir=None, shell=False, shell_args=None, uid=None,
                 max_retry=5, gid=None, send_hup=False,
                 stop_signal=signal.SIGTERM, stop_children=False, env=None,
                 graceful_timeout=30.0, prereload_fn=None, rlimits=None,
                 executable=None, stdout_stream=None, stderr_stream=None,
                 priority=0, loop=None, singleton=False, use_sockets=False,
                 copy_env=False, copy_path=False, max_age=0,
                 max_age_variance=30, hooks=None, respawn=True,
                 autostart=True, on_demand=False, virtualenv=None,
                 close_child_stdout=False, close_child_stderr=False,
                 **options):
        self.name = name
        self.use_sockets = use_sockets
        self.on_demand = on_demand
        self.res_name = name.lower().replace(" ", "_")
        self.numprocesses = int(numprocesses)
        self.warmup_delay = warmup_delay
        self.cmd = cmd
        self.args = args
        self._status = "stopped"
        self.graceful_timeout = float(graceful_timeout)
        self.prereload_fn = prereload_fn
        self.executable = None
        self.priority = priority
        self.stdout_stream_conf = copy.copy(stdout_stream)
        self.stderr_stream_conf = copy.copy(stderr_stream)
        self.stdout_stream = get_stream(self.stdout_stream_conf)
        self.stderr_stream = get_stream(self.stderr_stream_conf)
        self.stdout_redirector = self.stderr_redirector = None
        self.max_retry = max_retry
        self._options = options
        self.singleton = singleton
        self.copy_env = copy_env
        self.copy_path = copy_path
        self.virtualenv = virtualenv
        self.max_age = int(max_age)
        self.max_age_variance = int(max_age_variance)
        self.ignore_hook_failure = ['before_stop', 'after_stop',
                                    'before_signal', 'after_signal',
                                    'extended_stats']

        self.respawn = respawn
        self.autostart = autostart
        self.close_child_stdout = close_child_stdout
        self.close_child_stderr = close_child_stderr
        self.loop = loop or ioloop.IOLoop.instance()

        if singleton and self.numprocesses not in (0, 1):
            raise ValueError("Cannot have %d processes with a singleton "
                             " watcher" % self.numprocesses)

        self.optnames = (("numprocesses", "warmup_delay", "working_dir",
                          "uid", "gid", "send_hup", "stop_signal",
                          "stop_children", "shell", "shell_args",
                          "env", "max_retry", "cmd", "args",
                          "graceful_timeout", "executable", "use_sockets",
                          "priority", "copy_env", "singleton",
                          "stdout_stream_conf", "on_demand",
                          "stderr_stream_conf", "max_age", "max_age_variance",
                          "close_child_stdout", "close_child_stderr")
                         + tuple(options.keys()))

        if not working_dir:
            # working dir hasn't been set
            working_dir = util.get_working_dir()

        self.working_dir = working_dir
        self.processes = {}
        self.shell = shell
        self.shell_args = shell_args
        self.uid = uid
        self.gid = gid

        if self.copy_env:
            self.env = os.environ.copy()
            if self.copy_path:
                path = os.pathsep.join(sys.path)
                self.env['PYTHONPATH'] = path
            if env is not None:
                self.env.update(env)
        else:
            if self.copy_path:
                raise ValueError(('copy_env and copy_path must have the '
                                  'same value'))
            self.env = env

        if self.virtualenv:
            util.load_virtualenv(self)

        # load directories in PYTHONPATH if provided
        # so if a hook is there, it can be loaded
        if self.env is not None and 'PYTHONPATH' in self.env:
            for path in self.env['PYTHONPATH'].split(os.pathsep):
                if path in sys.path:
                    continue
                site.addsitedir(path)

        self.rlimits = rlimits
        self.send_hup = send_hup
        self.stop_signal = stop_signal
        self.stop_children = stop_children
        self.sockets = self.evpub_socket = None
        self.arbiter = None
        self.hooks = {}
        self._resolve_hooks(hooks)

    def _reload_hook(self, key, hook, ignore_error):
        hook_name = key.split('.')[-1]
        self._resolve_hook(hook_name, hook, ignore_error, reload_module=True)

    def _reload_stream(self, key, val):
        parts = key.split('.', 1)

        action = 0
        if parts[0] == 'stdout_stream':
            old_stream = self.stdout_stream
            self.stdout_stream_conf[parts[1]] = val
            self.stdout_stream = get_stream(self.stdout_stream_conf,
                                            reload=True)
            if self.stdout_redirector:
                self.stdout_redirector.redirect = self.stdout_stream['stream']
            else:
                self.stdout_redirector = get_pipe_redirector(
                    self.stdout_stream, loop=self.loop)
                self.stdout_redirector.start()
                action = 1

            if old_stream and hasattr(old_stream['stream'], 'close'):
                old_stream['stream'].close()
        else:
            old_stream = self.stderr_stream
            self.stderr_stream_conf[parts[1]] = val
            self.stderr_stream = get_stream(self.stderr_stream_conf,
                                            reload=True)
            if self.stderr_redirector:
                self.stderr_redirector.redirect = self.stderr_stream['stream']
            else:
                self.stderr_redirector = get_pipe_redirector(
                    self.stderr_stream, loop=self.loop)
                self.stderr_redirector.start()
                action = 1

            if old_stream and hasattr(old_stream['stream'], 'close'):
                old_stream['stream'].close()

        return action

    def _create_redirectors(self):
        if self.stdout_stream:
            if self.stdout_redirector is not None:
                self.stdout_redirector.stop()
            self.stdout_redirector = get_pipe_redirector(
                self.stdout_stream, loop=self.loop)
        else:
            self.stdout_redirector = None

        if self.stderr_stream:
            if self.stderr_redirector is not None:
                self.stderr_redirector.stop()
            self.stderr_redirector = get_pipe_redirector(
                self.stderr_stream, loop=self.loop)
        else:
            self.stderr_redirector = None

    def _resolve_hook(self, name, callable_or_name, ignore_failure,
                      reload_module=False):
        if is_callable(callable_or_name):
            self.hooks[name] = callable_or_name
        else:
            # will raise ImportError on failure
            self.hooks[name] = resolve_name(callable_or_name,
                                            reload=reload_module)

        if ignore_failure:
            self.ignore_hook_failure.append(name)

    def _resolve_hooks(self, hooks):
        """Check the supplied hooks argument to make sure we can find
        callables"""
        if hooks is None:
            return
        for name, (callable_or_name, ignore_failure) in hooks.items():
            self._resolve_hook(name, callable_or_name, ignore_failure)

    @property
    def pending_socket_event(self):
        return self.on_demand and not self.arbiter.socket_event

    @classmethod
    def load_from_config(cls, config):
        if 'env' in config:
            config['env'] = parse_env_dict(config['env'])
        cfg = config.copy()

        w = cls(name=config.pop('name'), cmd=config.pop('cmd'), **config)
        w._cfg = cfg

        return w

    @util.debuglog
    def initialize(self, evpub_socket, sockets, arbiter):
        self.evpub_socket = evpub_socket
        self.sockets = sockets
        self.arbiter = arbiter

    def __len__(self):
        return len(self.processes)

    def notify_event(self, topic, msg):
        """Publish a message on the event publisher channel"""

        name = bytestring(self.res_name)

        multipart_msg = [b("watcher.%s.%s" % (name, topic)), json.dumps(msg)]

        if self.evpub_socket is not None and not self.evpub_socket.closed:
            self.evpub_socket.send_multipart(multipart_msg)

    @util.debuglog
    def reap_process(self, pid, status=None):
        """ensure that the process is killed (and not a zombie)"""
        if pid not in self.processes:
            return
        process = self.processes.pop(pid)

        if status is None:
            while True:
                try:
                    _, status = os.waitpid(pid, os.WNOHANG)
                except OSError as e:
                    if e.errno == errno.EAGAIN:
                        time.sleep(0.001)
                        continue
                    elif e.errno == errno.ECHILD:
                        # nothing to do here, we do not have any child
                        # process running
                        # but we still need to send the "reap" signal.
                        #
                        # This can happen if poll() or wait() were called on
                        # the underlying process.
                        logger.debug('reaping already dead process %s [%s]',
                                     pid, self.name)
                        self.notify_event(
                            "reap",
                            {"process_pid": pid,
                             "time": time.time(),
                             "exit_code": process.returncode()})
                        process.stop()
                        return
                    else:
                        raise

        # get return code
        if os.WIFSIGNALED(status):
            # The Python Popen object returns <-signal> in it's returncode
            # property if the process exited on a signal, so emulate that
            # behavior here so that pubsub clients watching for reap can
            # distinguish between an exit with a non-zero exit code and
            # a signal'd exit. This is also consistent with the notify_event
            # reap message above that uses the returncode function (that ends
            # up calling Popen.returncode)
            exit_code = -os.WTERMSIG(status)
        # process exited using exit(2) system call; return the
        # integer exit(2) system call has been called with
        elif os.WIFEXITED(status):
            exit_code = os.WEXITSTATUS(status)
        else:
            # should never happen
            raise RuntimeError("Unknown process exit status")

        # if the process is dead or a zombie try to definitely stop it.
        if process.status in (DEAD_OR_ZOMBIE, UNEXISTING):
            process.stop()

        logger.debug('reaping process %s [%s]', pid, self.name)
        self.notify_event("reap",
                          {"process_pid": pid,
                           "time": time.time(),
                           "exit_code": exit_code})

    @util.debuglog
    def reap_processes(self):
        """Reap all the processes for this watcher.
        """
        if self.is_stopped():
            logger.debug('do not reap processes as the watcher is stopped')
            return

        # reap_process changes our dict, look through the copy of keys
        for pid in list(self.processes.keys()):
            self.reap_process(pid)

    @gen.coroutine
    @util.debuglog
    def manage_processes(self):
        """Manage processes."""
        if self.is_stopped():
            return

        # remove dead or zombie processes first
        for process in list(self.processes.values()):
            if process.status in (DEAD_OR_ZOMBIE, UNEXISTING):
                self.processes.pop(process.pid)

        if self.max_age:
            yield self.remove_expired_processes()

        # adding fresh processes
        if len(self.processes) < self.numprocesses and not self.is_stopping():
            if self.respawn:
                yield self.spawn_processes()
            elif not len(self.processes) and not self.on_demand:
                yield self._stop()

        # removing extra processes
        if len(self.processes) > self.numprocesses:
            processes_to_kill = []
            for process in sorted(self.processes.values(),
                                  key=lambda process: process.started,
                                  reverse=True)[self.numprocesses:]:
                if process.status in (DEAD_OR_ZOMBIE, UNEXISTING):
                    self.processes.pop(process.pid)
                else:
                    processes_to_kill.append(process)

            removes = yield [self.kill_process(process)
                             for process in processes_to_kill]
            for i, process in enumerate(processes_to_kill):
                if removes[i]:
                    self.processes.pop(process.pid)

    @gen.coroutine
    @util.debuglog
    def remove_expired_processes(self):
        max_age = self.max_age + randint(0, self.max_age_variance)
        expired_processes = [p for p in self.processes.values()
                             if p.age() > max_age]
        removes = yield [self.kill_process(x) for x in expired_processes]
        for i, process in enumerate(expired_processes):
            if removes[i]:
                self.processes.pop(process.pid)

    @gen.coroutine
    @util.debuglog
    def reap_and_manage_processes(self):
        """Reap & manage processes."""
        if self.is_stopped():
            return
        self.reap_processes()
        yield self.manage_processes()

    @gen.coroutine
    @util.debuglog
    def spawn_processes(self):
        """Spawn processes.
        """
        # when an on_demand process dies, do not restart it until
        # the next event
        if self.pending_socket_event:
            self._status = "stopped"
            return
        for i in range(self.numprocesses - len(self.processes)):
            res = self.spawn_process()
            if res is False:
                yield self._stop()
                break
            yield tornado_sleep(self.warmup_delay)

    def _get_sockets_fds(self):
        # XXX should be cached
        if self.sockets is None:
            return {}
        fds = {}
        for name, sock in self.sockets.items():
            fds[name] = sock.fileno()
        return fds

    def spawn_process(self):
        """Spawn process.

        Return True if ok, False if the watcher must be stopped
        """
        if self.is_stopped():
            return True

        if not self.call_hook('before_spawn'):
            return False

        cmd = util.replace_gnu_args(self.cmd, env=self.env)
        nb_tries = 0

        while nb_tries < self.max_retry or self.max_retry == -1:
            process = None
            pipe_stdout = self.stdout_redirector is not None
            pipe_stderr = self.stderr_redirector is not None

            try:
                process = Process(self._nextwid, cmd,
                                  args=self.args, working_dir=self.working_dir,
                                  shell=self.shell, uid=self.uid, gid=self.gid,
                                  env=self.env, rlimits=self.rlimits,
                                  executable=self.executable,
                                  use_fds=self.use_sockets, watcher=self,
                                  pipe_stdout=pipe_stdout,
                                  pipe_stderr=pipe_stderr,
                                  close_child_stdout=self.close_child_stdout,
                                  close_child_stderr=self.close_child_stderr)

                # stream stderr/stdout if configured
                if pipe_stdout and self.stdout_redirector is not None:
                    self.stdout_redirector.add_redirection('stdout',
                                                           process,
                                                           process.stdout)

                if pipe_stderr and self.stderr_redirector is not None:
                    self.stderr_redirector.add_redirection('stderr',
                                                           process,
                                                           process.stderr)

                self.processes[process.pid] = process
                logger.debug('running %s process [pid %d]', self.name,
                             process.pid)
                if not self.call_hook('after_spawn', pid=process.pid):
                    self.kill_process(process)
                    del self.processes[process.pid]
                    return False
            except OSError as e:
                logger.warning('error in %r: %s', self.name, str(e))

            if process is None:
                nb_tries += 1
                continue
            else:
                self.notify_event("spawn", {"process_pid": process.pid,
                                            "time": time.time()})
                return True
        return False

    @util.debuglog
    def send_signal_process(self, process, signum):
        """Send the signum signal to the process

        The signal is sent to the process itself then to all the children
        """
        children = None
        try:
            # getting the process children
            children = process.children()

            # sending the signal to the process itself
            self.send_signal(process.pid, signum)
            self.notify_event("kill", {"process_pid": process.pid,
                                       "time": time.time()})
        except NoSuchProcess:
            # already dead !
            if children is None:
                return

        # now sending the same signal to all the children
        for child_pid in children:
            try:
                process.send_signal_child(child_pid, signum)
                self.notify_event("kill", {"process_pid": child_pid,
                                  "time": time.time()})
            except NoSuchProcess:
                # already dead !
                pass

    def _process_remove_redirections(self, process):
        """Remove process redirections
        """
        if self.stdout_redirector is not None and process.stdout is not None:
            self.stdout_redirector.remove_redirection(process.stdout)
        if self.stderr_redirector is not None and process.stderr is not None:
            self.stderr_redirector.remove_redirection(process.stderr)

    @gen.coroutine
    @util.debuglog
    def kill_process(self, process):
        """Kill process (stop_signal, graceful_timeout then SIGKILL)
        """
        if process.stopping:
            raise gen.Return(False)
        try:
            logger.debug("%s: kill process %s", self.name, process.pid)
            if self.stop_children:
                self.send_signal_process(process, self.stop_signal)
            else:
                self.send_signal(process.pid, self.stop_signal)
                self.notify_event("kill", {"process_pid": process.pid,
                                           "time": time.time()})
        except NoSuchProcess:
            raise gen.Return(False)

        process.stopping = True
        waited = 0
        while waited < self.graceful_timeout:
            if not process.is_alive():
                break
            yield tornado_sleep(0.1)
            waited += 0.1
        if waited >= self.graceful_timeout:
            # We are not smart anymore
            self.send_signal_process(process, signal.SIGKILL)
        self._process_remove_redirections(process)
        process.stopping = False
        process.stop()
        raise gen.Return(True)

    @gen.coroutine
    @util.debuglog
    def kill_processes(self):
        """Kill all processes (stop_signal, graceful_timeout then SIGKILL)
        """
        active_processes = self.get_active_processes()
        try:
            yield [self.kill_process(process) for process in active_processes]
        except OSError as e:
            if e.errno != errno.ESRCH:
                raise

    @util.debuglog
    def send_signal(self, pid, signum):
        if pid in self.processes:
            process = self.processes[pid]
            hook_result = self.call_hook("before_signal",
                                         pid=pid, signum=signum)
            if signum != signal.SIGKILL and not hook_result:
                logger.debug("before_signal hook didn't return True "
                             "=> signal %i is not sent to %i" % (signum, pid))
            else:
                process.send_signal(signum)
            self.call_hook("after_signal", pid=pid, signum=signum)
        else:
            logger.debug('process %s does not exist' % pid)

    @util.debuglog
    def send_signal_child(self, pid, child_id, signum):
        """Send signal to a child.
        """
        process = self.processes[pid]
        try:
            process.send_signal_child(int(child_id), signum)
        except OSError as e:
            if e.errno != errno.ESRCH:
                raise

    @util.debuglog
    def send_signal_children(self, pid, signum):
        """Send signal to all children.
        """
        process = self.processes[int(pid)]
        process.send_signal_children(signum)

    @util.debuglog
    def status(self):
        return self._status

    @util.debuglog
    def process_info(self, pid, extended=False):
        process = self.processes[int(pid)]
        result = process.info()
        if extended and 'extended_stats' in self.hooks:
            self.hooks['extended_stats'](self, self.arbiter,
                                         'extended_stats',
                                         pid=pid, stats=result)
        return result

    @util.debuglog
    def info(self, extended=False):
        result = dict([(proc.pid, proc.info())
                       for proc in self.processes.values()])
        if extended and 'extended_stats' in self.hooks:
            for pid, stats in result.items():
                self.hooks['extended_stats'](self, self.arbiter,
                                             'extended_stats',
                                             pid=pid, stats=stats)
        return result

    @util.synchronized("watcher_stop")
    @gen.coroutine
    def stop(self):
        yield self._stop()

    @util.debuglog
    @gen.coroutine
    def _stop(self, close_output_streams=False):
        if self.is_stopped():
            return
        self._status = "stopping"
        logger.debug('stopping the %s watcher' % self.name)
        logger.debug('gracefully stopping processes [%s] for %ss' % (
                     self.name, self.graceful_timeout))
        # We ignore the hook result
        self.call_hook('before_stop')
        yield self.kill_processes()
        self.reap_processes()

        # stop redirectors
        if self.stdout_redirector is not None:
            self.stdout_redirector.stop()
            self.stdout_redirector = None
        if self.stderr_redirector is not None:
            self.stderr_redirector.stop()
            self.stderr_redirector = None
        if close_output_streams:
            if self.stdout_stream and hasattr(self.stdout_stream['stream'],
                                              'close'):
                self.stdout_stream['stream'].close()
            if self.stderr_stream and hasattr(self.stderr_stream['stream'],
                                              'close'):
                self.stderr_stream['stream'].close()
        # notify about the stop
        if self.evpub_socket is not None:
            self.notify_event("stop", {"time": time.time()})
        self._status = "stopped"
        # We ignore the hook result
        self.call_hook('after_stop')
        logger.info('%s stopped', self.name)

    def get_active_processes(self):
        """return a list of pids of active processes (not already stopped)"""
        return [p for p in self.processes.values()
                if p.status not in (DEAD_OR_ZOMBIE, UNEXISTING)]

    def get_active_pids(self):
        """return a list of pids of active processes (not already stopped)"""
        return [p.pid for p in self.processes.values()
                if p.status not in (DEAD_OR_ZOMBIE, UNEXISTING)]

    @property
    def pids(self):
        """Returns a list of PIDs"""
        return [process.pid for process in self.processes]

    @property
    def _nextwid(self):
        used_wids = set([p.wid for p in self.processes.values()])
        all_wids = set(range(1, self.numprocesses * 2 + 1))
        available_wids = sorted(all_wids - used_wids)
        try:
            return available_wids[0]
        except IndexError:
            raise RuntimeError("Process count > numproceses*2")

    def call_hook(self, hook_name, **kwargs):
        """Call a hook function"""
        hook_kwargs = {'watcher': self, 'arbiter': self.arbiter,
                       'hook_name': hook_name}
        hook_kwargs.update(kwargs)
        if hook_name in self.hooks:
            try:
                result = self.hooks[hook_name](**hook_kwargs)
                self.notify_event("hook_success",
                                  {"name": hook_name, "time": time.time()})
            except Exception as error:
                logger.exception('Hook %r failed' % hook_name)
                result = hook_name in self.ignore_hook_failure
                self.notify_event("hook_failure",
                                  {"name": hook_name, "time": time.time(),
                                   "error": str(error)})

            return result
        else:
            return True

    @util.synchronized("watcher_start")
    @gen.coroutine
    def start(self):
        before_pids = set() if self.is_stopped() else set(self.processes)
        yield self._start()
        after_pids = set(self.processes)
        raise gen.Return({'started': sorted(after_pids - before_pids),
                          'kept': sorted(after_pids & before_pids)})

    @gen.coroutine
    @util.debuglog
    def _start(self):
        """Start.
        """
        if self.pending_socket_event:
            return

        if not self.is_stopped():
            if len(self.processes) < self.numprocesses:
                self.reap_processes()
                yield self.spawn_processes()
            return

        if not self.call_hook('before_start'):
            logger.debug('Aborting startup')
            return

        self._status = "starting"

        self._create_redirectors()
        self.reap_processes()
        yield self.spawn_processes()

        # If not self.processes, the before_spawn or after_spawn hooks have
        # probably prevented startup so give up
        if not self.processes or not self.call_hook('after_start'):
            logger.debug('Aborting startup')
            yield self._stop()
            return

        if self.stdout_redirector is not None:
            self.stdout_redirector.start()

        if self.stderr_redirector is not None:
            self.stderr_redirector.start()

        self._status = "active"
        logger.info('%s started' % self.name)
        self.notify_event("start", {"time": time.time()})

    @util.synchronized("watcher_restart")
    @gen.coroutine
    def restart(self):
        before_pids = set() if self.is_stopped() else set(self.processes)
        yield self._restart()
        after_pids = set(self.processes)
        raise gen.Return({'stopped': sorted(before_pids - after_pids),
                          'started': sorted(after_pids - before_pids),
                          'kept': sorted(after_pids & before_pids)})

    @gen.coroutine
    @util.debuglog
    def _restart(self):
        yield self._stop()
        yield self._start()

    @util.synchronized("watcher_reload")
    @gen.coroutine
    def reload(self, graceful=True, sequential=False):
        before_pids = set() if self.is_stopped() else set(self.processes)
        yield self._reload(graceful=graceful, sequential=sequential)
        after_pids = set(self.processes)
        raise gen.Return({'stopped': sorted(before_pids - after_pids),
                          'started': sorted(after_pids - before_pids),
                          'kept': sorted(after_pids & before_pids)})

    @gen.coroutine
    @util.debuglog
    def _reload(self, graceful=True, sequential=False):
        """ reload
        """
        if not(graceful) and sequential:
            logger.warn("with graceful=False, sequential=True is ignored")
        if self.prereload_fn is not None:
            self.prereload_fn(self)

        if not graceful:
            yield self._restart()
            return

        if self.is_stopped():
            yield self._start()
        elif self.send_hup:
            for process in self.processes.values():
                logger.info("SENDING HUP to %s" % process.pid)
                process.send_signal(signal.SIGHUP)
        else:
            if sequential:
                active_processes = self.get_active_processes()
                for process in active_processes:
                    yield self.kill_process(process)
                    self.reap_process(process.pid)
                    self.spawn_process()
                    yield tornado_sleep(self.warmup_delay)
            else:
                for i in range(self.numprocesses):
                    self.spawn_process()
                yield self.manage_processes()
        self.notify_event("reload", {"time": time.time()})
        logger.info('%s reloaded', self.name)

    @gen.coroutine
    def set_numprocesses(self, np):
        if np < 0:
            np = 0
        if self.singleton and np > 1:
            raise ValueError('Singleton watcher has a single process')
        self.numprocesses = np
        yield self.manage_processes()
        raise gen.Return(self.numprocesses)

    @util.synchronized("watcher_incr")
    @gen.coroutine
    @util.debuglog
    def incr(self, nb=1):
        res = yield self.set_numprocesses(self.numprocesses + nb)
        raise gen.Return(res)

    @util.synchronized("watcher_decr")
    @gen.coroutine
    @util.debuglog
    def decr(self, nb=1):
        res = yield self.set_numprocesses(self.numprocesses - nb)
        raise gen.Return(res)

    @util.synchronized("watcher_set_opt")
    def set_opt(self, key, val):
        """Set a watcher option.

        This function set the watcher options. unknown keys are ignored.
        This function return an action number:

        - 0: trigger the process management
        - 1: trigger a graceful reload of the processes;
        """
        action = 0

        if key in self._options:
            self._options[key] = val
            action = -1    # XXX for now does not trigger a reload
        elif key == "numprocesses":
            val = int(val)
            if val < 0:
                val = 0
            if self.singleton and val > 1:
                raise ValueError('Singleton watcher has a single process')
            self.numprocesses = val
        elif key == "warmup_delay":
            self.warmup_delay = float(val)
        elif key == "working_dir":
            self.working_dir = val
            action = 1
        elif key == "uid":
            self.uid = util.to_uid(val)
            action = 1
        elif key == "gid":
            self.gid = util.to_gid(val)
            action = 1
        elif key == "send_hup":
            self.send_hup = val
        elif key == "stop_signal":
            self.stop_signal = util.to_signum(val)
        elif key == "stop_children":
            self.stop_children = util.to_bool(val)
        elif key == "shell":
            self.shell = val
            action = 1
        elif key == "env":
            self.env = val
            action = 1
        elif key == "cmd":
            self.cmd = val
            action = 1
        elif key == "args":
            self.args = val
            action = 1
        elif key == "graceful_timeout":
            self.graceful_timeout = float(val)
            action = -1
        elif key == "max_age":
            self.max_age = int(val)
            action = 1
        elif key == "max_age_variance":
            self.max_age_variance = int(val)
            action = 1
        elif (key.startswith('stdout_stream') or
              key.startswith('stderr_stream')):
            action = self._reload_stream(key, val)
        elif key.startswith('hooks'):
            val = val.split(',')
            if len(val) == 2:
                ignore_error = util.to_bool(val[1])
            else:
                ignore_error = False
            hook = val[0]
            self._reload_hook(key, hook, ignore_error)
            action = 0

        # send update event
        self.notify_event("updated", {"time": time.time()})
        return action

    @util.synchronized("watcher_do_action")
    @gen.coroutine
    def do_action(self, num):
        # trigger needed action
        if num == 0:
            yield self.manage_processes()
        elif not self.is_stopped():
            # graceful restart
            yield self._reload()

    @util.debuglog
    def options(self, *args):
        options = []
        for name in sorted(self.optnames):
            if name in self._options:
                options.append((name, self._options[name]))
            else:
                options.append((name, getattr(self, name)))
        return options

    def is_stopping(self):
        return self._status == 'stopping'

    def is_stopped(self):
        return self._status == 'stopped'

    def is_active(self):
        return self._status == 'active'

########NEW FILE########
__FILENAME__ = _patch
import threading
from threading import (_active_limbo_lock, _limbo, _active, _sys, _trace_hook,
                       _profile_hook, _format_exc)


debugger = False
try:
    import pydevd
    debugger = pydevd.GetGlobalDebugger()
except ImportError:
    pass

if not debugger:
    # see http://bugs.python.org/issue1596321
    if hasattr(threading.Thread, '_Thread__stop'):
        def _bootstrap_inner(self):
            try:
                self._set_ident()
                self._Thread__started.set()
                with _active_limbo_lock:
                    _active[self._Thread__ident] = self
                    del _limbo[self]

                if _trace_hook:
                    _sys.settrace(_trace_hook)
                if _profile_hook:
                    _sys.setprofile(_profile_hook)

                try:
                    self.run()
                except SystemExit:
                    pass
                except:
                    if _sys:
                        _sys.stderr.write("Exception in thread %s:\n%s\n" %
                                          (self.name, _format_exc()))
                    else:
                        exc_type, exc_value, exc_tb = self._exc_info()
                        try:
                            self._stderr.write(
                                "Exception in thread " + self.name + " (most "
                                "likely raised during interpreter shutdown):")

                            self._stderr.write("Traceback (most recent call "
                                               "last):")
                            while exc_tb:
                                self._stderr.write(
                                    '  File "%s", line %s, in %s' %
                                    (exc_tb.tb_frame.f_code.co_filename,
                                        exc_tb.tb_lineno,
                                        exc_tb.tb_frame.f_code.co_name))

                                exc_tb = exc_tb.tb_next
                            self._stderr.write("%s: %s" %
                                               (exc_type, exc_value))
                        finally:
                            del exc_type, exc_value, exc_tb
                finally:
                    pass
            finally:
                with _active_limbo_lock:
                    self._Thread__stop()
                    try:
                        del _active[self._Thread__ident]
                    except:
                        pass

        def _delete(self):
            try:
                with _active_limbo_lock:
                    del _active[self._Thread__ident]
            except KeyError:
                if 'dummy_threading' not in _sys.modules:
                    raise

        # http://bugs.python.org/issue14308
        def _stop(self):
            # DummyThreads delete self.__block, but they have no waiters to
            # notify anyway (join() is forbidden on them).
            if not hasattr(self, '_Thread__block'):
                return
            self._Thread__stop_old()

        threading.Thread._Thread__bootstrap_inner = _bootstrap_inner
        threading.Thread._Thread__delete = _delete
        threading.Thread._Thread__stop_old = threading.Thread._Thread__stop
        threading.Thread._Thread__stop = _stop
    else:
        def _bootstrap_inner(self):  # NOQA
            try:
                self._set_ident()
                self._started.set()
                with _active_limbo_lock:
                    _active[self._ident] = self
                    del _limbo[self]

                if _trace_hook:
                    _sys.settrace(_trace_hook)
                if _profile_hook:
                    _sys.setprofile(_profile_hook)

                try:
                    self.run()
                except SystemExit:
                    pass
                except:
                    if _sys:
                        _sys.stderr.write("Exception in thread %s:\n%s\n" %
                                          (self.name, _format_exc()))
                    else:
                        exc_type, exc_value, exc_tb = self._exc_info()
                        try:
                            self._stderr.write(
                                "Exception in thread " + self.name + " (most "
                                "likely raised during interpreter shutdown):")

                            self._stderr.write("Traceback (most recent call "
                                               "last):")
                            while exc_tb:
                                self._stderr.write(
                                    '  File "%s", line %s, in %s' %
                                    (exc_tb.tb_frame.f_code.co_filename,
                                        exc_tb.tb_lineno,
                                        exc_tb.tb_frame.f_code.co_name))

                                exc_tb = exc_tb.tb_next
                            self._stderr.write("%s: %s" %
                                               (exc_type, exc_value))
                        finally:
                            del exc_type, exc_value, exc_tb
                finally:
                    pass
            finally:
                with _active_limbo_lock:
                    self._stop()
                    try:
                        del _active[self._ident]
                    except:
                        pass

        def _delete(self):  # NOQA
            try:
                with _active_limbo_lock:
                    del _active[self._ident]
            except KeyError:
                if 'dummy_threading' not in _sys.modules:
                    raise

        # http://bugs.python.org/issue14308
        def _stop(self):  # NOQA
            # DummyThreads delete self.__block, but they have no waiters to
            # notify anyway (join() is forbidden on them).
            if not hasattr(self, '_block'):
                return
            self._stop_old()

        threading.Thread._bootstrap_inner = _bootstrap_inner
        threading.Thread._delete = _delete
        threading.Thread._stop_old = threading.Thread._stop
        threading.Thread._stop = _stop

########NEW FILE########
__FILENAME__ = circus_ext
import os
from circus.commands import get_commands


def generate_commands(app):
    path = os.path.join(app.srcdir, "for-ops", "commands")
    ext = app.config['source_suffix']
    if not os.path.exists(path):
        os.makedirs(path)

    tocname = os.path.join(app.srcdir, "for-ops", "commands%s" % ext)

    commands = get_commands()
    items = commands.items()
    items = sorted(items)

    with open(tocname, "w") as toc:
        toc.write(".. include:: commands-intro%s\n\n" % ext)
        toc.write("circus-ctl commands\n")
        toc.write("-------------------\n\n")

        commands = get_commands()
        for name, cmd in items:
            toc.write("- **%s**: :doc:`commands/%s`\n" % (name, name))

            # write the command file
            refline = ".. _%s:" % name
            fname = os.path.join(path, "%s%s" % (name, ext))
            with open(fname, "w") as f:
                f.write("\n".join([refline, "\n", cmd.desc, ""]))

        toc.write("\n")
        toc.write(".. toctree::\n")
        toc.write("   :hidden:\n")
        toc.write("   :glob:\n\n")
        toc.write("   commands/*\n")

def setup(app):
    app.connect('builder-inited', generate_commands)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Circus documentation build configuration file, created by
# sphinx-quickstart on Fri Feb 24 15:30:44 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
import mozilla_sphinx_theme

class Mock(object):
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Mock()

    @classmethod
    def __getattr__(self, name):
        if name in ('__file__', '__path__'):
            return '/dev/null'
        elif name[0] == name[0].upper():
            return type(name, (), {})

        return Mock()


MOCK_MODULES = ['zmq', 'zmq.eventloop', 'zmq.utils.jsonapi', 'zmq.utils']

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if on_rtd:
    for mod_name in MOCK_MODULES:
        sys.modules[mod_name] = Mock()


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.

CURDIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(CURDIR, '..', '..'))
sys.path.append(os.path.join(CURDIR, '..'))

import circus
extensions = ['sphinx.ext.autodoc', 'circus_ext']


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Circus'
copyright = u''

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
release = version = circus.__version__

# The full version, including alpha/beta/rc tags.

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['**/commands-intro.rst']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_short_title = "Circus"

html_theme_path = [os.path.dirname(mozilla_sphinx_theme.__file__)]
html_theme = 'mozilla'

#html_logo = "images/circus32.png"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

CURDIR = os.path.dirname(__file__)
sidebars = []
for f in os.listdir(CURDIR):
    name, ext = os.path.splitext(f)
    if ext != '.rst':
        continue
    sidebars.append((name, 'indexsidebar.html'))

html_sidebars = dict(sidebars)

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Circusdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Circus.tex', u'Circus Documentation',
   u'Mozilla Foundation', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'circus', u'Circus Documentation',
     [u'Mozilla Foundation', u'Benoit Chesneau'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Circus', u'Circus Documentation',
   u'Mozilla Foundation', 'Circus', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = addworkers
from circus.client import CircusClient
from circus.util import DEFAULT_ENDPOINT_DEALER

client = CircusClient(endpoint=DEFAULT_ENDPOINT_DEALER)

command = '../bin/python dummy_fly.py 111'
name = 'dummy'


for i in range(50):
    print(client.call("""
    {
        "command": "add",
        "properties": {
            "cmd": "%s",
            "name": "%s",
            "options": {
            "copy_env": true,
            "stdout_stream": {
                "filename": "stdout.log"
            },
            "stderr_stream": {
                "filename": "stderr.log"
            }
            },
            "start": true
        }
    }
    """ % (command, name + str(i))))


########NEW FILE########
__FILENAME__ = apis

from circus import get_arbiter

myprogram = {"cmd": "sleep 30", "numprocesses": 4}

print('Runnning...')
arbiter = get_arbiter([myprogram])
try:
    arbiter.start()
finally:
    arbiter.stop()


########NEW FILE########
__FILENAME__ = byapi
myprogram = {
    "cmd": "python",
    "args": "-u dummy_fly.py $(circus.wid)",
    "numprocesses": 3,
}

from circus import get_arbiter

arbiter = get_arbiter([myprogram], debug=True)
try:
    arbiter.start()
finally:
    arbiter.stop()


########NEW FILE########
__FILENAME__ = demo
import random


def set_var(watcher, arbiter, hook_name):
    watcher.env['myvar'] = str(random.randint(10, 100))
    return True

########NEW FILE########
__FILENAME__ = dummy_fly
#!/usr/bin/env python
import os
import signal
import sys


class DummyFly(object):

    def __init__(self, wid):
        self.wid = wid
        # init signal handling
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)
        signal.signal(signal.SIGCHLD, self.handle_chld)
        self.alive = True

    def handle_quit(self, *args):
        self.alive = False
        sys.exit(0)

    def handle_chld(self, *args):
        return

    def run(self):
        print("hello, fly #%s (pid: %s) is alive" % (self.wid, os.getpid()))

        a = 2
        while self.alive:
            a = a + 200

if __name__ == "__main__":
    DummyFly(sys.argv[1]).run()

########NEW FILE########
__FILENAME__ = dummy_fly2
import os
import signal
import sys
import time


class DummyFly(object):

    def __init__(self, wid):
        self.wid = wid
        # init signal handling
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)
        signal.signal(signal.SIGCHLD, self.handle_chld)
        self.alive = True

    def handle_quit(self, *args):
        self.alive = False
        sys.exit(0)

    def handle_chld(self, *args):
        return

    def run(self):
        print("hello, fly 2 #%s (pid: %s) is alive" % (self.wid, os.getpid()))

        while self.alive:
            time.sleep(0.1)

if __name__ == "__main__":
    DummyFly(sys.argv[1]).run()

########NEW FILE########
__FILENAME__ = flask_app
#import resource

#resource.setrlimit(resource.RLIMIT_NOFILE, (100, 100))

from flask import Flask
app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello World!"


if __name__ == "__main__":
    app.run(debug=True, port=8181, host='0.0.0.0')

########NEW FILE########
__FILENAME__ = flask_redirect
from flask import Flask, redirect, make_response
app = Flask(__name__)
app.debug = True

@app.route("/file.pdf")
def file():
    with open('file.pdf', 'rb') as f:
        response = make_response(f.read())
        response.headers['Content-Type'] = "application/pdf"
        return response

@app.route("/")
def page_redirect():
    return redirect("http://localhost:8000")


if __name__ == "__main__":
    app.run(debug=True, port=8181, host='0.0.0.0')

########NEW FILE########
__FILENAME__ = flask_serve
from flask import Flask, make_response
app = Flask(__name__)
app.debug = True
import requests

@app.route("/")
def pdf():
    pdf = requests.get('http://localhost:5000/file.pdf')
    response = make_response(pdf.content)
    response.headers['Content-Type'] = "application/pdf"
    return response


if __name__ == "__main__":
    app.run(debug=True, port=8181, host='0.0.0.0')

########NEW FILE########
__FILENAME__ = hang
import sys
import StringIO

from flask import Flask
app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello World!"

if __name__ == "__main__":
    #sys.stderr = sys.stdout = StringIO.StringIO()
    app.run(port=8000)


########NEW FILE########
__FILENAME__ = leaker
# sleeps for 55555 then leaks memory
import time

if __name__ == '__main__':
    time.sleep(5)
    memory = ''

    while True:
        memory += 100000 * ' '

########NEW FILE########
__FILENAME__ = listener
from circus.consumer import CircusConsumer
import json


ZMQ_ENDPOINT = 'tcp://127.0.0.1:5556'
topic = 'show:'

for message, message_topic in CircusConsumer(topic, endpoint=ZMQ_ENDPOINT):
    response = json.dumps(dict(message=message, topic=message_topic))
    print(response)

########NEW FILE########
__FILENAME__ = plugin_watchdog
import socket
import time
import os

UDP_IP = "127.0.0.1"
UDP_PORT = 1664

sock = socket.socket(socket.AF_INET,
                     socket.SOCK_DGRAM)  # UDP

my_pid = os.getpid()

for _ in range(25):
    message = "{pid};{time}".format(pid=my_pid, time=time.time())
    print('sending:{0}'.format(message))
    sock.sendto(message, (UDP_IP, UDP_PORT))
    time.sleep(2)

########NEW FILE########
__FILENAME__ = simplesocket_client
import socket

#connect to a worker
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 8888))

data = sock.recv(100)
print('Received : {0}'.format(repr(data)))
sock.close()

########NEW FILE########
__FILENAME__ = simplesocket_server
import socket
import sys
import time
import os
import random

fd = int(sys.argv[1])   # getting the FD from circus
sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)

# By default socket created by circus is in non-blocking mode. For this example
# we change this.
sock.setblocking(1)
random.seed()

while True:
    conn, addr = sock.accept()
    conn.sendall("Hello Circus by %s" % (os.getpid(),))
    seconds = random.randint(2, 12)
    time.sleep(seconds)
    conn.close()

########NEW FILE########
__FILENAME__ = uwsgi_lossless_reload
__author__ = 'Code Cobblers, Inc.'

# This is an example of how to get lossless reload of WSGI web servers with
# circus and uWSGI. You will, of course, need to specify the web app you
# need for uWSGI to run.
#
# This example also solves another problem I have faced many times with uWSGI.
# When you start an app with a defect in uWSGI, uWSGI will keep restarting
# if forever. So this example includes an after_spawn hook that does flapping
# detection on the uWSGI workers.
#
# Here is the flow for a reload:
# 1. You issue a reload command to the watcher
# 2. The watcher starts a new instance of uWSGI
# 3. The after_spawn hook ensures that the workers are not flapping and halts
#    the new process if it is, aborting the reload. This would leave the old
#    process running so that you are not just SOL.
# 4. The watcher issues SIGQUIT to the old instance, which is intercepted by
#    the before_signal hook
# 5. We send SIGTSTP to the old process to tell uWSGI to stop receiving new
#    connections
# 6. We query the stats from the old process in a loop waiting for the old
#    workers to go to the pause state
# 7. We return True, allowing the SIGQUIT to be issued to the old process

from time import time, sleep
import socket
from json import loads
import signal
from circus import logger
import re

worker_states = {
    'running': "idle busy cheap".split(" "),
    'paused': "pause".split(" "),
}
NON_JSON_CHARACTERS = re.compile(r'[\x00-\x1f\x7f-\xff]')


class TimeoutError(Exception):
    """The operation timed out."""


def get_uwsgi_stats(name, wid):
    try:
        sock = socket.create_connection(('127.0.0.1', 8090 + wid),
                                        timeout=1)
    except Exception as e:
        logger.error(
            "Error: Connection refused for {0}} on 127.0.0.1:809{1} - {2}"
            .format(name, wid, e))
        raise e
    received = sock.recv(100000)
    data = bytes()
    while received:
        data += received
        received = sock.recv(100000)
    if not data:
        logger.error(
            "Error: No stats seem available for WID %d of %s", wid, name)
        return
    # recent versions of uWSGI had some garbage in the JSON so strip it out
    data = NON_JSON_CHARACTERS.sub('', data.decode())
    return loads(data)


def get_worker_states(name, wid, minimum_age=0.0):
    stats = get_uwsgi_stats(name, wid)
    if 'workers' not in stats:
        logger.error("Error: No workers found for WID %d of %d", wid, name)
        return ['unknown']
    workers = stats['workers']
    return [
        worker["status"] if 'status' in worker and worker['last_spawn'] < time() - minimum_age else 'unknown'
        for worker in workers
    ]


def wait_for_workers(name, wid, state, timeout_seconds=60, minimum_age=0):
    started = time()
    while True:
        try:
            if all(worker.lower() in worker_states[state]
                   for worker in get_worker_states(name, wid, minimum_age)):
                return
        except Exception:
            if time() > started + 3:
                raise TimeoutError('timeout')
        if timeout_seconds and time() > started + timeout_seconds:
            raise TimeoutError('timeout')
        sleep(0.25)


def extended_stats(watcher, arbiter, hook_name, pid, stats, **kwargs):
    name = watcher.name
    wid = watcher.processes[pid].wid
    try:
        uwsgi_stats = get_uwsgi_stats(name, wid)
        for k in ('load', 'version'):
            if k in uwsgi_stats:
                stats[k] = uwsgi_stats[k]
        if 'children' in stats and 'workers' in uwsgi_stats:
            workers = dict((worker['pid'], worker) for worker in uwsgi_stats['workers'])
            for worker in stats['children']:
                uwsgi_worker = workers.get(worker['pid'])
                if uwsgi_worker:
                    for k in ('exceptions', 'harakiri_count', 'requests', 'respawn_count', 'status', 'tx'):
                        if k in uwsgi_worker:
                            worker[k] = uwsgi_worker[k]
    except Exception:
        pass
    return True


def children_started(watcher, arbiter, hook_name, pid, **kwargs):
    name = watcher.name
    wid = watcher.processes[pid].wid
    try:
        wait_for_workers(name, wid, 'running', timeout_seconds=10,
                         minimum_age=5)
        return True
    except TimeoutError:
        logger.error('%s children are flapping on %d', name, pid)
        return False


def clean_stop(watcher, arbiter, hook_name, pid, signum, **kwargs):
    if len(watcher.processes) > watcher.numprocesses and signum == signal.SIGQUIT:
        name = watcher.name
        started = watcher.processes[pid].started
        newer_pids = [p for p, w in watcher.processes.items() if p != pid and w.started > started]
        # if the one being stopped is actually the newer one, just do it
        if len(newer_pids) < watcher.numprocesses:
            return True
        wid = watcher.processes[pid].wid
        logger.info('%s pausing', name)
        watcher.send_signal(pid, signal.SIGTSTP)
        try:
            wait_for_workers(name, wid, 'paused')
            logger.info('%s workers idle', name)
        except Exception as e:
            logger.exception('trouble pausing %s: %s', name, e)
    return True

########NEW FILE########
__FILENAME__ = verbose_fly
#!/usr/bin/env python
import os
import time
import sys

i = 0

while True:
    #print '%d:%d' % (os.getpid(), i)
    sys.stdout.write('%d:%d\n' % (os.getpid(), i))
    sys.stdout.flush()
    time.sleep(0.1)
    i += 1

########NEW FILE########
__FILENAME__ = bread
# -*- coding: utf-8 -*-
"""
    Bread: A Simple Web Client for Circus

"""
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

import json
import argparse

from circus.consumer import CircusConsumer
from flask import Flask, request, render_template


ZMQ_ENDPOINT = 'tcp://127.0.0.1:5556'

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api')
def api():
    """WebSocket endpoint; Takes a 'topic' GET param."""
    ws = request.environ.get('wsgi.websocket')
    topic = request.args.get('topic')

    if None in (ws, topic):
        return

    topic = topic.encode('ascii')
    for message, message_topic in CircusConsumer(topic, endpoint=ZMQ_ENDPOINT):
        response = json.dumps(dict(message=message, topic=message_topic))
        ws.send(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=5000)
    args = parser.parse_args()
    server_loc = (args.host, args.port)
    print('HTTP Server running at http://%s:%s/...' % server_loc)
    http_server = WSGIServer(server_loc, app, handler_class=WebSocketHandler)
    http_server.serve_forever()


if __name__ == '__main__':
    main()

########NEW FILE########
