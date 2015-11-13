__FILENAME__ = ansicolor
##
# https://github.com/philipbergen/zero
# Licensed under terms of MIT license (see LICENSE-MIT)
# Copyright (c) 2013 Philip Bergen, philip.bergen@me.com

''' Exports ansicolor functions.
    You want to probably use this as:
        from ansicolor import blk, red, grn, yel, blu, mag, cya, wht, off, bld, unl, bnk, dim, FG, BG, BRT
    print BLD(red('Hello')), yel('world!', BG)
'''

_colors = 'blk red grn yel blu mag cya wht'.split()
__all__ = _colors + 'off bld dim rvv bnk unl FG BG BRT'.split()

_CSI = '\033[%dm'
_OFF = _CSI % 0
FG = 30   # Add to a color for foreground
BG = 40   # Add to a color for background
BRT = 60  # Add to a color for bright colors


def bld(s=None):
    'Wraps s in ANSI codes for bold'
    if not s:
        return _CSI % 1
    return _CSI % 1 + s + _OFF


def rvv(s=None):
    'Wraps s in ANSI codes for reverse video'
    if not s:
        return _CSI % 7
    return _CSI % 7 + s + _OFF


def bnk(s=None):
    'Wraps s in ANSI codes for blink'
    if not s:
        return _CSI % 5
    return _CSI % 5 + s + _OFF


def unl(s=None):
    'Wraps s in ANSI codes for underline'
    if not s:
        return _CSI % 4
    return _CSI % 4 + s + _OFF


def dim(s=None):
    'Wraps s in ANSI codes for dim'
    if not s:
        return _CSI % 2
    return _CSI % 2 + s + _OFF


def off(fg=FG):
    'Returns ANSI codes for turning off all color and style'
    if not fg:
        return _CSI % 0
    return _CSI % (fg + 9)


for col_n, col in enumerate(_colors):
    def colorwrap(s='', fg=FG, col_n=col_n):
        'Returns s wrapped in ANSI color codes for each available color'
        if not s:
            return _CSI % (fg + col_n)
        return _CSI % (fg + col_n) + s + _OFF
    locals()[col] = colorwrap

########NEW FILE########
__FILENAME__ = rpc
''' Base classes for use by workers (not intended to be used outside this module.
'''
import json
from itertools import izip

__all__ = ('ZeroRPC', 'ConfiguredRPC', 'zrpc')


class ZeroRPC(object):
    ''' Inherit and implement your own methods on from this.
        Then supply to ZeroSetup:

        Zero(ZeroSetup('pull', 8000)).activated(ZeroRPC())
    '''
    def __call__(self, obj):
        'Calls the method from obj (always of the form [<method name>, {<kwargs>}]).'
        from traceback import format_exc
        try:
            if obj[0][:1] == '_':
                raise Exception('Method not available')
            if len(obj) == 1:
                obj = [obj[0], {}]
            if not hasattr(self, obj[0]):
                return self._unsupported(obj[0], **obj[1])
            func = getattr(self, obj[0])
            return func(**obj[1])
        except:
            self.zero.setup.err('Exception: ' + format_exc())
            return ['ERROR', format_exc()]

    def _unsupported(self, func, **kwargs):
        'Catch-all method for when the object received does not fit.'
        return ['UnsupportedFunc', func, kwargs]

    @staticmethod
    def _test_rpc():
        ''' For doctest
            >>> from zero.rpc import ZeroRPC
            >>> ZeroRPC._test_rpc()
            REP u'hello'
            REP 100
        '''
        from zero import Zero, ZeroSetup
        class Z(ZeroRPC):
            def hi(self):
                return "hello"

            def sqr(self, x):
                return x*x

        def listen():
            zero = Zero(ZeroSetup('rep', 8000)).activated(Z())
            for _, msg in izip(range(2), zero):
                zero(msg)
            zero.close()

        from threading import Thread
        t = Thread(name='TestRPC', target=listen)
        t.daemon = True
        t.start()

        zero = Zero(ZeroSetup('req', 8000))
        msg = ['hi']
        rep = zero(msg)
        print 'REP %r' % rep
        msg = ['sqr', {'x': 10}]
        rep = zero(msg)
        print 'REP %r' % rep
        zero.close()
        t.join()


class ConfiguredRPC(ZeroRPC):
    ''' Does not implement any RPC methods. This class adds methods and members for accessing 
        system configuration.

        System configuration as json looks like this:
        {
            "workers": {
                "imagestore": {
                    "module": "noep.workers.store",
                    "class": "ImageStoreRPC",
                    "zmq": {
                        "method": "rep",
                        "port": 8805,
                        "debug": true,
                        "host": "localhost"
                    }
                },
                "gphoto": {
                    "module": "noep.workers.gphoto",
                    "class": "GphotoRPC",
                    "zmq": {
                        "method": "rep",
                        "port": 8804,
                        "debug": true,
                        "host": "localhost"
                    },
                    "filename": "gphoto-%n.%C"
                }
            }
        }

        Each worker has a module and class name as well as a zmq configuration. Additional keys
        may be added. zero.rpc will ignore everything outside of "workers" -> (worker type) -> 
        ["module", "class", "zmq" -> ["method", "port", "debug"*, "bind"*, "host"*]].

        *) optional

        To instantiate a worker from the config do something similar to this:

        from zero.rpc import zrpc
        from json import load
        with open('config.json') as fin:
            sysconfig = load(fin)
        rpc = zrpc(sysconfig, 'gphoto')
    '''
    def __init__(self, configuration, workertype):
        self._config = (configuration, workertype)

    def _worker_config(self, workertype=None):
        if not workertype:
            workertype = self._config[1]
        return self._config[0]['workers'][workertype]

    def _system_config(self):
        return self._config[0]

    
def zrpc(sysconfig, workertype):
    ''' Returns an activated Zero with RPC worker of type workertype as specified in sysconfig.
        >>> from .test import _get_test_config
        >>> from zero import zbg
        >>> from itertools import izip
        >>> from socket import gethostname
        >>> from time import time
        >>> cfg = _get_test_config()
        >>> z = zrpc(cfg, 'common')
        >>> o = z.opposite()
        >>> z  # doctest: +ELLIPSIS
        Zero(ZeroSetup('rep', 8000).binding(True)).activated(<zero.test.CommonRPC object at ...>)
        >>> o
        Zero(ZeroSetup('req', 8000).binding(False))
        >>> t = zbg(o, [['ping'], ['echo', {'msg': 'Hello'}], ['hostname'], ['time']], lambda x: x)
        >>> reps = []
        >>> for _, msg in izip(range(4), z):  # doctest: +ELLIPSIS
        ...     reps.append(msg)
        ...     z(msg)
        >>> reps[0]
        'pong'
        >>> reps[1]
        u'Hello'
        >>> reps[2] == gethostname()
        True
        >>> abs(time() - reps[3]) < 1
        True
        >>> t.join()
    '''
    from zero import Zero, ZeroSetup
    wconf = sysconfig['workers'][workertype]
    zconf = wconf['zmq']
    setup = ZeroSetup(zconf['method'], zconf['port']).debugging(zconf.get('debug', False))
    if 'bind' in zconf:
        setup.binding(zconf['bind'])
    if 'host' in zconf and not setup.bind:
        setup._point = 'tcp://%(host)s:%(port)s' % zconf
    mod = __import__(wconf['module'])
    for modpart in wconf['module'].split('.')[1:]:
        mod = getattr(mod, modpart)
    klass = getattr(mod, wconf['class'])
    return Zero(setup).activated(klass(sysconfig, workertype))


def _test():
    import doctest
    return doctest.testmod()


if __name__ == '__main__':
    from zero import Zero, ZeroSetup
    _test()

########NEW FILE########
__FILENAME__ = test
''' Simple RPC functions that can be used for testing.
'''

__all__ = ('CommonRPC', '_get_test_config')
from zero.rpc import ConfiguredRPC

def _get_test_config():
    return {
        'workers': {
            'common': {
                'module': 'zero.test',
                'class': 'CommonRPC',
                'zmq': {
                    'port': 8000,
                    'method': 'rep'
                }
            }
        }
    }


class CommonRPC(ConfiguredRPC):
    'Simple network functions.'
    def ping(self):
        return 'pong'

    def echo(self, msg):
        return msg

    def hostname(self):
        from socket import gethostname
        return gethostname()

    def time(self):
        import time
        return time.time()

########NEW FILE########
__FILENAME__ = __main__
def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Running tests, not zeros
        import doctest
        sys.path.insert(0, '..')
        import zero
        import zero.rpc
        fails, tests = doctest.testmod(zero)
        fails2, tests2 = doctest.testmod(zero.rpc)
        tests += tests2
        if fails + fails2:
            msg = 'Completed %d tests, %d failed. Run zero test -v for more information.'
            sys.exit(msg % (tests, fails + fails2))
        print 'Successfully completed %d tests.' % tests
        return

    import json
    from zero import Zero, ZeroSetup, zauto, UnsupportedZmqMethod
    try:
        # Regular zero run
        setup, loop = ZeroSetup.argv()
        zero = Zero(setup)

        for msg in zauto(zero, loop, setup.args['--wait']):
            sys.stdout.write(json.dumps(msg) + '\n')
            sys.stdout.flush()
    except UnsupportedZmqMethod, e:
        args = e.args[2]
        if args['rpc']:
            # Configured RPC not supported by zauto
            from zero.rpc import zrpc
            with open(args['<config>']) as fin:
                config = json.load(fin)
            if len(args['<type>']) == 1:
                zero = zrpc(config, args['<type>'][0])
                setup = zero.setup
                if args['--dbg']:
                    setup.debugging(True)
                for msg in zero:
                    if setup.transmits:
                        zero(msg)
            else:
                raise ValueError('Multiple RPC workers not yet supported.', args['<type>'])
        else:
            # Something happened...
            raise e
        if setup.args['--wait']:
            raw_input('Press enter when done.')
        zero.close()
    
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = zlog-sink
#!/usr/bin/env python
##
# https://github.com/philipbergen/zero
# Licensed under terms of MIT license (see LICENSE-MIT)
# Copyright (c) 2013 Philip Bergen, philip.bergen@me.com

''' USAGE:
      zlog-sink [<config>]

    <config>  Path to configuration file [default: log.json]
'''

from ansicolor import *


class Logout(object):
    width = 100
    def __init__(self, conf):
        self.colwidth = [0] * 5
        self.lvls = {}
        for lvl, col in conf['levels']:
            self.lvls[lvl] = eval(col)
        self.ts_format = conf['ts-format']

    def tty(self, logline):

        def wide(n, s):
            self.colwidth[n] = max(self.colwidth[n], len(s))
            return ('%-' + str(self.colwidth[n]) + 's') % s

        from json import loads
        from time import strftime
        from traceback import format_exc
        try:
            sender, host, lvl, ts, msg = loads(logline)
        except (ValueError, TypeError):
            print format_exc()
            lvl = host = sender = '?'
            ts = strftime(self.ts_format)
            msg = logline
        if lvl not in self.lvls:
            lvl = '?'
        try:
            lines = iter(msg.split('\n'))
        except AttributeError:
            lines = [repr(msg)]
        msg = []
        for tmp in lines:
            for i in range(0, len(tmp), self.width):
                msg.append(tmp[i:i+self.width])
        msg = iter(msg)
        col = self.lvls[lvl]
        print wide(1, ts), col(wide(0, lvl)), col(wide(2, host))
        for m in msg:
            print self.lvls[lvl](' ------>'), cya(sender), m


def main():
    import os.path
    from sys import argv
    from json import load
    from zero import Zero, ZeroSetup
    HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    conf = HERE + '/log.json'
    if len(argv) > 1:
        conf = argv[1]
    print 'Loading config from', conf
    with open(conf) as fin:
        conf = load(fin)['log']
    setup = ZeroSetup('pull', conf['port'])
    path = conf['file']
    if path[0] != '/':
        path = HERE + '/' + path
    print 'Logger started for', setup
    print 'Logging to', path
    with open(path, 'a', 1) as fout:
        logout = Logout(conf)
        try:
            for line in Zero(setup):
                fout.write(line)
                fout.write('\n')
                logout.tty(line)
        except KeyboardInterrupt:
            print 'Logger quitting.'
    print 'Logger stopped on', setup


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = zlog
#!/usr/bin/env python
##
# https://github.com/philipbergen/zero
# Licensed under terms of MIT license (see LICENSE-MIT)
# Copyright (c) 2013 Philip Bergen, philip.bergen@me.com

''' USAGE:
      zlog [<config>] (lol|fyi|wtf|omg) <sender> (-|<message> <message>...)

    <sender> is a logical name of emitting party.

    If <message> is -, message lines are read from stdin.
'''

__all__ = ('ZLogger', 'zlogger')
from socket import gethostname
from zero import ZeroSetup, Zero


class ZLogger(object):
    'ZMQ logging object. Caches host and sender. Transmits via a queue to the push Zero.'
    def __init__(self, config, logq, sender, host):
        self.logq = logq
        self.sender = sender
        self.host = host
        for lvl, _ in config['levels']:
            def logout(msg, lvl=lvl):
                'Local function object for dynamic log level functions such as fyi or wtf.'
                self.log(msg, lvl)
            setattr(self, lvl, logout)

    def log(self, msg, level):
        'Formats a message and puts it on the logging queue.'
        self.logq.put(self.format(self.sender, level, msg, self.host))

    @classmethod
    def format(cls, sender, level, msg, host=gethostname(), ts_format='%Y-%m-%dT%H:%M:%S%Z'):
        'Returns a correctly formatted zlog json message.'
        from json import dumps
        from time import strftime
        return dumps([sender, host, level, strftime(ts_format), msg])


def zlogger(config, sender):
    ''' Convenience function for setting up a ZLogger and queue. Returns a ZLogger
        object with .fyi, .wtf, .omg functions as specified in config['log']['levels'].
    '''
    from Queue import Queue
    from threading import Thread
    logq = Queue()
    slog = Zero(ZeroSetup('push', 'tcp://%(host)s:%(port)s' % config).nonblocking())

    def thread(slog=slog):
        for t in iter(logq.get, ''):
            slog(t)
    t = Thread(target=thread)
    t.daemon = True
    t.start()
    return ZLogger(config, logq, sender, gethostname())


def main():
    'For CLI use, see usage in __doc__.'
    import os.path
    from sys import argv, exit
    from json import load
    from os.path import exists
    from itertools import imap
    from collections import deque
    HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    args = deque(argv[1:])
    if len(args) < 3:
        exit(__doc__)
    conf = HERE + '/log.json'
    level = args.popleft()
    if exists(level):
        conf = level
        level = args.popleft()
    with open(conf) as fin:
        conf = load(fin)['log']
    sender = args.popleft()
    if args[0] == '-':
        messages = ZeroSetup.iter_stdin()
    else:
        messages = iter(args)
    messages = imap(lambda x: ZLogger.format(sender, level, x), messages)
    z = Zero(ZeroSetup('push', conf['port']))
    for msg in messages:
        z(msg)


if __name__ == '__main__':
    main()

########NEW FILE########
