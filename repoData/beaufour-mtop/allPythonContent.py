__FILENAME__ = ops
from pymongo.errors import AutoReconnect
try:
    from bson.son import SON
except ImportError:
    # fall back to old location
    from pymongo.son import SON


class MongoOps():
    """
    Helper class for mongo commands we use.

    Wraps calls in try/except so that resizing does not break them.
    """

    def __init__(self, connection):
        """
        @param connection: pymongo Connection to use.
        """

        self._connection = connection

    def get_inprog(self):
        ret = None
        try:
            ret = self._connection.db['$cmd.sys.inprog'].find_one()
        except AutoReconnect:
            pass

        return ret['inprog'] if ret else []

    def get_server_status(self):
        ret = None
        try:
            ret = self._connection.db.command(SON([('serverStatus', 1),
                                                   ('repl', 2),
                                                   ['workingSet', 1],
                                                   ]))
        except AutoReconnect:
            pass

        return ret

########NEW FILE########
__FILENAME__ = runner
import json
import time

from lib.ops import MongoOps
from lib.screen import Screen
from lib.util import op_cmp
from lib.util import stringify_query_dict


class Runner:
    """
    Main logic for 'mtop'. Once initialized, L{run()} keeps updating
    until ctrl-c is pressed.
    """

    def __init__(self, connection, interval):
        """
        @param connection: pymongo Connection to use.
        @param interval: Delay between updates (ms).
        """

        self._connection = connection
        self._timeout = interval / 1000.
        self._mongo_ops = MongoOps(self._connection)

    def run(self):
        """
        Run loop.

        @param screen: cursus screen object.
        @return: 0 if normal exit, negative values otherwise
        """

        self._screen = Screen()
        try:
            return self._do_run()
        except KeyboardInterrupt:
            pass
        finally:
            self._screen.end()

        return 0

    def _do_run(self):
        self._screen.timeout(self._timeout)
        self._last_opstats = {}
        self._maxy, self._maxx = self._screen.getmaxyx()

        if self._maxy < 5:
            return -3

        while True:
            self._y = 0

            srvstat = self._mongo_ops.get_server_status()
            inprog = self._mongo_ops.get_inprog()
            inprog.sort(op_cmp)

            self._screen.clear()
            if srvstat:
                self._server_stats(srvstat)
                self._memory_stats(srvstat)
                self._repl_stats(srvstat)
                self._op_stats(srvstat)

            if inprog:
                self._inprog(inprog)

            time.sleep(self._timeout)

            # In the event of a resize
            self._maxy, self._maxx = self._screen.getmaxyx()

    def _print(self, arr):
        try:
            self._screen.addstr(self._y, 0, ''.join(arr)[:self._maxx])
            self._y += 1
        except:
            pass

    def _server_stats(self, d):
        host = self._connection.host
        out = []
        out.append("%s. v%s, %d bit" % (host, d['version'], d['mem']['bits']))
        out.append('. Conns: %d/%d' % (d['connections']['current'], d['connections']['available']))
        ratio = d['globalLock'].get('ratio')
        if ratio is None:
            ratio = float(d['globalLock']['lockTime']) / float(d['globalLock']['totalTime'])
        out.append('. Lock %%: %.2f' % round(ratio, 2))
        self._print(out)

    def _memory_stats(self, d):
        out = []
        out.append('Mem (MB): %s resident, %s virtual, %s mapped' % (d['mem']['resident'], d['mem']['virtual'], d['mem']['mapped']))
        if 'workingSet' in d:
            # value is in pages (i.e. 4k blocks), so divide it by / 256 to get MB
            out.append(', %d working set' % (round(int(d['workingSet']['pagesInMemory']) / 256.0)))
        self._print(out)

    def _repl_stats(self, d):
        repl = d.get('repl')
        if not repl:
            return

        hosts = repl.get('hosts')
        if not hosts:
            return

        out = []
        out.append('Rep (%s):' % repl['setName'])
        for host in hosts:
            out.append(' %s(%s)' % (host, 'P' if host == repl['primary'] else 'S'))
        self._print(out)

    def _op_stats(self, d):
        out = []
        out.append('Ops:')
        ops = []
        total = 0
        for op in d['opcounters']:
            val = 0
            if op in self._last_opstats:
                val = d['opcounters'][op] - self._last_opstats[op]
            self._last_opstats[op] = d['opcounters'][op]
            ops.append(' %4d %s' % (val, op))
            total += val

        ops.insert(0, ' %4d total' % total)
        out.append(','.join(ops))
        self._print(out)

    def _inprog(self, inprog):
        template = "%11s %21s %7s %1s %5s %s"
        self._print([template % ('ID', 'CLIENT', 'OP', 'A', 'LOCKW', 'NS / QUERY')])

        opsmax = self._maxy - self._y
        if len(inprog) > opsmax:
            # Leave room for '% more' line
            opsmax -= 1

        for op in inprog[:opsmax]:
            a = 'T' if op['active'] else 'F'
            lock = op.get('lockType') if op['waitingForLock'] else ''
            client = op.get('client', 'internal')
            ns_query = op['ns']
            if client == 'internal':
                ns_query += op.get('desc', '')
            query = op.get('query')
            if query:
                ns_query += " " + json.dumps(stringify_query_dict(query))[:(self._maxx - 40)]
            self._print([template % (op['opid'], client, op['op'], a, lock, ns_query)])

        if len(inprog) > opsmax:
            self._print(['( ... %d more ... )' % (len(inprog) - opsmax)])

########NEW FILE########
__FILENAME__ = screen
import fcntl
import os
import signal
import sys
import struct
import termios


class Screen:
    """
    Class that behaves like `curses`.

    NOTE: Would love to just use the standard python curses library,
    but I failed to handle terminal resizing properly (on Mac OS
    X). This interface is about the same as the curses screen one
    though, so it should be easy to swap in/out.
    """

    def __init__(self):
        signal.signal(signal.SIGWINCH, self._on_resize)

    def _on_resize(self, a, b):
        pass

    def end(self):
        print '\x1b[5l'

    def timeout(self, timeout):
        self._timeout = timeout / 1000

    def clear(self):
        print '\x1b[H\x1b[J',
        sys.stdout.flush()

    def addstr(self, y, x, txt):
        print '\x1b[%d;%dH%s' % (y + 1, x, txt),
        sys.stdout.flush()

    def getmaxyx(self):
        try:
            return int(os.environ["LINES"]), int(os.environ["COLUMNS"])
        except KeyError:
            height, width = struct.unpack("hhhh",
                                          fcntl.ioctl(0, termios.TIOCGWINSZ, "\000" * 8))[0:2]
        if not height:
            return 25, 80

        return height, width

########NEW FILE########
__FILENAME__ = util
try:
    from bson.binary import Binary
except ImportError:
    # fall back to old location
    from pymongo.binary import Binary


def op_cmp(op1, op2):
    """
    Compare an operation by active and then opid.
    """
    if op1['active'] != op2['active']:
        return -1 if op1['active'] else 1

    return cmp(op1['opid'], op2['opid'])


def stringify_query_dict(query):
    for k, v in query.iteritems():
        if isinstance(v, dict):
            query[k] = stringify_query_dict(v)
        elif isinstance(v, Binary):
            query[k] = "bin:" + hex(v)
        elif isinstance(v, basestring):
            pass
        else:
            query[k] = str(v)
    return query

########NEW FILE########
__FILENAME__ = mtop
#!/usr/bin/env python
#
# Copyright 2011-2013 Allan Beaufour
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from optparse import OptionParser
import sys

import pymongo
from pymongo.errors import AutoReconnect

from lib.runner import Runner


def main():
    parser = OptionParser(usage='mtop.py [options]\nSee also: https://github.com/beaufour/mtop')
    parser.add_option('-s', '--server',
                      dest='server', default='localhost',
                      help='connect to mongo on SERVER', metavar='SERVER')
    parser.add_option('-d', '--delay',
                      dest='delay', type=int, default=1000,
                      help='update every MS', metavar='MS')

    (options, _) = parser.parse_args()

    try:
        if hasattr(pymongo, 'version_tuple') and pymongo.version_tuple[0] >= 2 and pymongo.version_tuple[1] >= 4:
            from pymongo import MongoClient
            from pymongo.read_preferences import ReadPreference
            connection = MongoClient(host=options.server,
                                     read_preference=ReadPreference.SECONDARY)
        else:
            from pymongo.connection import Connection
            connection = Connection(options.server, slave_okay=True)
    except AutoReconnect, ex:
        print 'Connection to %s failed: %s' % (options.server, str(ex))
        return -1

    runner = Runner(connection, options.delay)

    rc = runner.run()

    if rc == -3:
        print 'Screen size too small'

    return rc


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
