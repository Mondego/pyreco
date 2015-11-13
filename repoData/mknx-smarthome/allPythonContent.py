__FILENAME__ = smarthome
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2011-2013 Marcus Popp                          marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################

#####################################################################
# Check Python Version
#####################################################################
import sys
if sys.hexversion < 0x03020000:
    print("Sorry your python interpreter ({0}.{1}) is too old. Please update to 3.2 or newer.".format(sys.version_info[0], sys.version_info[1]))
    exit()

#####################################################################
# Import Python Core Modules
#####################################################################
import argparse
import datetime
import gc
import locale
import logging
import logging.handlers
import os
import re
import signal
import subprocess
import threading
import time
import traceback

#####################################################################
# Base
#####################################################################
logger = logging.getLogger('')
BASE = '/'.join(os.path.realpath(__file__).split('/')[:-2])
sys.path.append(BASE)
sys.path.append(BASE + '/lib/3rd')

#####################################################################
# Import 3rd Party Modules
#####################################################################
from dateutil.tz import gettz

#####################################################################
# Import SmartHome.py Modules
#####################################################################
import lib.config
import lib.connection
import lib.daemon
import lib.item
import lib.log
import lib.logic
import lib.plugin
import lib.scene
import lib.scheduler
import lib.tools
import lib.orb

#####################################################################
# Globals
#####################################################################
MODE = 'default'
LOGLEVEL = logging.INFO
VERSION = '1.0'
TZ = gettz('UTC')
try:
    os.chdir(BASE)
    VERSION = subprocess.check_output(['git', 'describe', '--always', '--dirty=+'], stderr=subprocess.STDOUT).decode().strip('\n')
except Exception as e:
    pass


#####################################################################
# Classes
#####################################################################

class LogHandler(logging.StreamHandler):
    def __init__(self, log):
        logging.StreamHandler.__init__(self)
        self._log = log

    def emit(self, record):
        timestamp = datetime.datetime.fromtimestamp(record.created, TZ)
        self._log.add([timestamp, record.threadName, record.levelname, record.message])


class SmartHome():
    base_dir = BASE
    _plugin_conf = BASE + '/etc/plugin.conf'
    _env_dir = BASE + '/lib/env/'
    _env_logic_conf = _env_dir + 'logic_conf'
    _items_dir = BASE + '/items/'
    _logic_conf = BASE + '/etc/logic.conf'
    _logic_dir = BASE + '/logics/'
    _cache_dir = BASE + '/var/cache/'
    _logfile = BASE + '/var/log/smarthome.log'
    _log_buffer = 50
    __logs = {}
    __event_listeners = {}
    __all_listeners = []
    _plugins = []
    __items = []
    __children = []
    __item_dict = {}
    _utctz = TZ

    def __init__(self, smarthome_conf=BASE + '/etc/smarthome.conf'):
        global TZ
        threading.currentThread().name = 'Main'
        self.alive = True
        self.version = VERSION
        self.connections = []

        #############################################################
        # logfile write test
        #############################################################
        os.umask(0o002)
        try:
            with open(self._logfile, 'a') as f:
                f.write("Init SmartHome.py {0}\n".format(VERSION))
        except IOError as e:
            print("Error creating logfile {}: {}".format(self._logfile, e))

        #############################################################
        # Fork
        #############################################################
        if MODE == 'default':
            lib.daemon.daemonize()

        #############################################################
        # Signal Handling
        #############################################################
        signal.signal(signal.SIGHUP, self.reload_logics)
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        #############################################################
        # Check Time
        #############################################################
        while datetime.date.today().isoformat() < '2013-10-24':  # XXX update date
            time.sleep(5)
            logger.info("Waiting for datetime update")

        #############################################################
        # Logging
        #############################################################
        _logdate = "%Y-%m-%d %H:%M:%S"
        _logformat = "%(asctime)s %(levelname)-8s %(threadName)-12s %(message)s"
        if LOGLEVEL == logging.DEBUG:
            _logdate = None
            _logformat = "%(asctime)s %(levelname)-8s %(threadName)-12s %(message)s -- %(filename)s:%(funcName)s:%(lineno)d"
        logging.basicConfig(level=LOGLEVEL, format=_logformat, datefmt=_logdate)
        if MODE == 'interactive':  # remove default stream handler
            logger.removeHandler(logger.handlers[0])
        # adding logfile
        try:
            formatter = logging.Formatter(_logformat, _logdate)
            log_file = logging.handlers.TimedRotatingFileHandler(self._logfile, when='midnight', backupCount=7)
            log_file.setLevel(LOGLEVEL)
            log_file.setFormatter(formatter)
            if LOGLEVEL == logging.DEBUG:  # clean log
                log_file.doRollover()
            _logdate = None
            logging.getLogger('').addHandler(log_file)
        except IOError as e:
            print("Error creating logfile {}: {}".format(self._logfile, e))

        #############################################################
        # Catching Exceptions
        #############################################################
        sys.excepthook = self._excepthook

        #############################################################
        # Reading smarthome.conf
        #############################################################
        try:
            config = lib.config.parse(smarthome_conf)
            for attr in config:
                if not isinstance(config[attr], dict):  # ignore sub items
                    vars(self)['_' + attr] = config[attr]
            del(config)  # clean up
        except Exception as e:
            logger.warning("Problem reading smarthome.conf: {0}".format(e))

        #############################################################
        # Setting debug level and adding memory handler
        #############################################################
        if hasattr(self, '_loglevel'):
            try:
                logging.getLogger('').setLevel(vars(logging)[self._loglevel.upper()])
            except:
                pass
        self.log = lib.log.Log(self, 'env.core.log', ['time', 'thread', 'level', 'message'], maxlen=self._log_buffer)
        log_mem = LogHandler(self.log)
        log_mem.setLevel(logging.WARNING)
        log_mem.setFormatter(formatter)
        logging.getLogger('').addHandler(log_mem)

        #############################################################
        # Setting (local) tz
        #############################################################
        self.tz = 'UTC'
        os.environ['TZ'] = self.tz
        if hasattr(self, '_tz'):
            tzinfo = gettz(self._tz)
            if tzinfo is not None:
                TZ = tzinfo
                self.tz = self._tz
                os.environ['TZ'] = self.tz
            else:
                logger.warning("Problem parsing timezone: {}. Using UTC.".format(self._tz))
            del(self._tz, tzinfo)
        self._tzinfo = TZ

        logger.info("Start SmartHome.py {0}".format(VERSION))
        logger.debug("Python {0}".format(sys.version.split()[0]))

        #############################################################
        # Link Tools
        #############################################################
        self.tools = lib.tools.Tools()

        #############################################################
        # Link Sun and Moon
        #############################################################
        if hasattr(self, '_lon') and hasattr(self, '_lat'):
            if not hasattr(self, '_elev'):
                self._elev = None
            self.sun = lib.orb.Orb('sun', self._lon, self._lat, self._elev)
            self.moon = lib.orb.Orb('moon', self._lon, self._lat, self._elev)
        else:
            logger.warning('No latitude/longitude specified => you could not use the sun and moon object.')
            self.sun = None
            self.moon = None

    #################################################################
    # Process Methods
    #################################################################

    def start(self):
        threading.currentThread().name = 'Main'

        #############################################################
        # Start Scheduler
        #############################################################
        self.scheduler = lib.scheduler.Scheduler(self)
        self.trigger = self.scheduler.trigger
        self.scheduler.start()

        #############################################################
        # Init Connections
        #############################################################
        self.connections = lib.connection.Connections()

        #############################################################
        # Init Plugins
        #############################################################
        logger.info("Init Plugins")
        self._plugins = lib.plugin.Plugins(self, configfile=self._plugin_conf)

        #############################################################
        # Init Items
        #############################################################
        logger.info("Init Items")
        item_conf = None
        for item_file in sorted(os.listdir(self._env_dir)):
            if item_file.endswith('.conf'):
                try:
                    item_conf = lib.config.parse(self._env_dir + item_file, item_conf)
                except Exception as e:
                    logger.exception("Problem reading {0}: {1}".format(item_file, e))
        for item_file in sorted(os.listdir(self._items_dir)):
            if item_file.endswith('.conf'):
                try:
                    item_conf = lib.config.parse(self._items_dir + item_file, item_conf)
                except Exception as e:
                    logger.exception("Problem reading {0}: {1}".format(item_file, e))
                    continue
        for attr, value in item_conf.items():
            if isinstance(value, dict):
                child_path = attr
                try:
                    child = lib.item.Item(self, self, child_path, value)
                except Exception as e:
                    logger.error("Item {}: problem creating: ()".format(child_path, e))
                else:
                    vars(self)[attr] = child
                    self.add_item(child_path, child)
                    self.__children.append(child)
        del(item_conf)  # clean up
        for item in self.return_items():
            item._init_prerun()
        for item in self.return_items():
            item._init_run()

        #############################################################
        # Start Connections
        #############################################################
        self.scheduler.add('Connections', self.connections.check, cycle=10, offset=0)

        #############################################################
        # Start Plugins
        #############################################################
        self._plugins.start()

        #############################################################
        # Init Logics
        #############################################################
        self._logics = lib.logic.Logics(self, self._logic_conf, self._env_logic_conf)

        #############################################################
        # Init Scenes
        #############################################################
        lib.scene.Scenes(self)

        #############################################################
        # Execute Maintenance Method
        #############################################################
        self.scheduler.add('sh.gc', self._maintenance, prio=8, cron=['init', '4 2 * *'], offset=0)

        #############################################################
        # Main Loop
        #############################################################
        while self.alive:
            try:
                self.connections.poll()
            except Exception as e:
                pass

    def stop(self, signum=None, frame=None):
        self.alive = False
        logger.info("Number of Threads: {0}".format(threading.activeCount()))
        for item in self.__items:
            self.__item_dict[item]._fading = False
        try:
            self.scheduler.stop()
        except:
            pass
        try:
            self._plugins.stop()
        except:
            pass
        try:
            self.connections.close()
        except:
            pass
        for thread in threading.enumerate():
            try:
                thread.join(1)
            except:
                pass
        if threading.active_count() > 1:
            for thread in threading.enumerate():
                logger.info("Thread: {}, still alive".format(thread.name))
        else:
            logger.info("SmartHome.py stopped")
        logging.shutdown()
        exit()

    #################################################################
    # Item Methods
    #################################################################
    def __iter__(self):
        for child in self.__children:
            yield child

    def add_item(self, path, item):
        if path not in self.__items:
            self.__items.append(path)
        self.__item_dict[path] = item

    def return_item(self, string):
        if string in self.__items:
            return self.__item_dict[string]

    def return_items(self):
        for item in self.__items:
            yield self.__item_dict[item]

    def match_items(self, regex):
        regex, __, attr = regex.partition(':')
        regex = regex.replace('.', '\.').replace('*', '.*') + '$'
        regex = re.compile(regex)
        if attr != '':
            return [self.__item_dict[item] for item in self.__items if regex.match(item) and attr in self.__item_dict[item].conf]
        else:
            return [self.__item_dict[item] for item in self.__items if regex.match(item)]

    def find_items(self, conf):
        for item in self.__items:
            if conf in self.__item_dict[item].conf:
                yield self.__item_dict[item]

    def find_children(self, parent, conf):
        children = []
        for item in parent:
            if conf in item.conf:
                children.append(item)
            children += self.find_children(item, conf)
        return children

    #################################################################
    # Plugin Methods
    #################################################################
    def return_plugins(self):
        for plugin in self._plugins:
            yield plugin

    #################################################################
    # Logic Methods
    #################################################################
    def reload_logics(self, signum=None, frame=None):
        for logic in self._logics:
            self._logics[logic].generate_bytecode()

    def return_logic(self, name):
        return self._logics[name]

    def return_logics(self):
        for logic in self._logics:
            yield logic

    #################################################################
    # Log Methods
    #################################################################
    def add_log(self, name, log):
        self.__logs[name] = log

    def return_logs(self):
        return self.__logs

    #################################################################
    # Event Methods
    #################################################################
    def add_event_listener(self, events, method):
        for event in events:
            if event in self.__event_listeners:
                self.__event_listeners[event].append(method)
            else:
                self.__event_listeners[event] = [method]
        self.__all_listeners.append(method)

    def return_event_listeners(self, event='all'):
        if event == 'all':
            return self.__all_listeners
        elif event in self.__event_listeners:
            return self.__event_listeners[event]
        else:
            return []

    #################################################################
    # Time Methods
    #################################################################
    def now(self):
        # tz aware 'localtime'
        return datetime.datetime.now(self._tzinfo)

    def tzinfo(self):
        return self._tzinfo

    def utcnow(self):
        # tz aware utc time
        return datetime.datetime.now(self._utctz)

    def utcinfo(self):
        return self._utctz

    #################################################################
    # Helper Methods
    #################################################################
    def _maintenance(self):
        self._garbage_collection()
        references = sum(self._object_refcount().values())
        logger.debug("Object references: {}".format(references))

    def _excepthook(self, typ, value, tb):
        mytb = "".join(traceback.format_tb(tb))
        logger.error("Unhandled exception: {1}\n{0}\n{2}".format(typ, value, mytb))

    def _garbage_collection(self):
        c = gc.collect()
        logger.debug("Garbage collector: collected {0} objects.".format(c))

    def string2bool(self, string):
        if isinstance(string, bool):
            return string
        if string.lower() in ['0', 'false', 'n', 'no', 'off']:
            return False
        if string.lower() in ['1', 'true', 'y', 'yes', 'on']:
            return True
        else:
            return None

    def object_refcount(self):
        objects = self._object_refcount()
        objects = [(x[1], x[0]) for x in list(objects.items())]
        objects.sort(reverse=True)
        return objects

    def _object_refcount(self):
        objects = {}
        for module in list(sys.modules.values()):
            for sym in dir(module):
                obj = getattr(module, sym)
                if isinstance(obj, type):
                    objects[obj] = sys.getrefcount(obj)
        return objects


#####################################################################
# Private Methods
#####################################################################

def reload_logics():
    pid = lib.daemon.get_pid(__file__)
    if pid:
        os.kill(pid, signal.SIGHUP)


#####################################################################
# Main
#####################################################################

if __name__ == '__main__':
    if locale.getdefaultlocale() == (None, None):
        locale.setlocale(locale.LC_ALL, 'C')
    else:
        locale.setlocale(locale.LC_ALL, '')

    # argument handling
    argparser = argparse.ArgumentParser()
    arggroup = argparser.add_mutually_exclusive_group()
    arggroup.add_argument('-v', '--verbose', help='verbose (debug output) logging to the logfile', action='store_true')
    arggroup.add_argument('-d', '--debug', help='stay in the foreground with verbose output', action='store_true')
    arggroup.add_argument('-i', '--interactive', help='open an interactive shell with tab completion and with verbose logging to the logfile', action='store_true')
    arggroup.add_argument('-l', '--logics', help='reload all logics', action='store_true')
    arggroup.add_argument('-s', '--stop', help='stop SmartHome.py', action='store_true')
    arggroup.add_argument('-q', '--quiet', help='reduce logging to the logfile', action='store_true')
    arggroup.add_argument('-V', '--version', help='show SmartHome.py version', action='store_true')
    arggroup.add_argument('--start', help='start SmartHome.py and detach from console (default)', default=True, action='store_true')
    args = argparser.parse_args()

    if args.interactive:
        LOGLEVEL = logging.DEBUG
        MODE = 'interactive'
        import code
        import rlcompleter  # noqa
        import readline
        import atexit
        # history file
        histfile = os.path.join(os.environ['HOME'], '.history.python')
        try:
            readline.read_history_file(histfile)
        except IOError:
            pass
        atexit.register(readline.write_history_file, histfile)
        readline.parse_and_bind("tab: complete")
        sh = SmartHome()
        _sh_thread = threading.Thread(target=sh.start)
        _sh_thread.start()
        shell = code.InteractiveConsole(locals())
        shell.interact()
        exit(0)
    elif args.logics:
        reload_logics()
        exit(0)
    elif args.version:
        print("SmartHome.py {0}".format(VERSION))
        exit(0)
    elif args.stop:
        lib.daemon.kill(__file__)
        exit(0)
    elif args.debug:
        LOGLEVEL = logging.DEBUG
        MODE = 'debug'
    elif args.quiet:
        LOGLEVEL = logging.WARNING
    elif args.verbose:
        LOGLEVEL = logging.DEBUG

    # check for pid file
    pid = lib.daemon.get_pid(__file__)
    if pid:
        print("SmartHome.py already running with pid {}".format(pid))
        print("Run 'smarthome.py -s' to stop it.")
        exit()

    # Starting SmartHome.py
    sh = SmartHome()
    sh.start()

########NEW FILE########
__FILENAME__ = skeleton
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2013 <AUTHOR>                                        <EMAIL>
#########################################################################
#  This file is part of SmartHome.py.   http://smarthome.sourceforge.net/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import logging

logger = logging.getLogger('')

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

########NEW FILE########
__FILENAME__ = easter
"""
Copyright (c) 2003-2007  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "Simplified BSD"

import datetime

__all__ = ["easter", "EASTER_JULIAN", "EASTER_ORTHODOX", "EASTER_WESTERN"]

EASTER_JULIAN   = 1
EASTER_ORTHODOX = 2
EASTER_WESTERN  = 3

def easter(year, method=EASTER_WESTERN):
    """
    This method was ported from the work done by GM Arts,
    on top of the algorithm by Claus Tondering, which was
    based in part on the algorithm of Ouding (1940), as
    quoted in "Explanatory Supplement to the Astronomical
    Almanac", P.  Kenneth Seidelmann, editor.

    This algorithm implements three different easter
    calculation methods:
    
    1 - Original calculation in Julian calendar, valid in
        dates after 326 AD
    2 - Original method, with date converted to Gregorian
        calendar, valid in years 1583 to 4099
    3 - Revised method, in Gregorian calendar, valid in
        years 1583 to 4099 as well

    These methods are represented by the constants:

    EASTER_JULIAN   = 1
    EASTER_ORTHODOX = 2
    EASTER_WESTERN  = 3

    The default method is method 3.
    
    More about the algorithm may be found at:

    http://users.chariot.net.au/~gmarts/eastalg.htm

    and

    http://www.tondering.dk/claus/calendar.html

    """

    if not (1 <= method <= 3):
        raise ValueError("invalid method")

    # g - Golden year - 1
    # c - Century
    # h - (23 - Epact) mod 30
    # i - Number of days from March 21 to Paschal Full Moon
    # j - Weekday for PFM (0=Sunday, etc)
    # p - Number of days from March 21 to Sunday on or before PFM
    #     (-6 to 28 methods 1 & 3, to 56 for method 2)
    # e - Extra days to add for method 2 (converting Julian
    #     date to Gregorian date)

    y = year
    g = y % 19
    e = 0
    if method < 3:
        # Old method
        i = (19*g+15)%30
        j = (y+y//4+i)%7
        if method == 2:
            # Extra dates to convert Julian to Gregorian date
            e = 10
            if y > 1600:
                e = e+y//100-16-(y//100-16)//4
    else:
        # New method
        c = y//100
        h = (c-c//4-(8*c+13)//25+19*g+15)%30
        i = h-(h//28)*(1-(h//28)*(29//(h+1))*((21-g)//11))
        j = (y+y//4+i+2-c+c//4)%7

    # p can be from -6 to 56 corresponding to dates 22 March to 23 May
    # (later dates apply to method 2, although 23 May never actually occurs)
    p = i-j+e
    d = 1+(p+27+(p+6)//40)%31
    m = 3+(p+26)//30
    return datetime.date(int(y), int(m), int(d))


########NEW FILE########
__FILENAME__ = parser
# -*- coding:iso-8859-1 -*-
"""
Copyright (c) 2003-2007  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "Simplified BSD"

import datetime
import string
import time
import sys
import os
import collections

try:
    from io import StringIO
except ImportError:
    from io import StringIO

from . import relativedelta
from . import tz


__all__ = ["parse", "parserinfo"]


# Some pointers:
#
# http://www.cl.cam.ac.uk/~mgk25/iso-time.html
# http://www.iso.ch/iso/en/prods-services/popstds/datesandtime.html
# http://www.w3.org/TR/NOTE-datetime
# http://ringmaster.arc.nasa.gov/tools/time_formats.html
# http://search.cpan.org/author/MUIR/Time-modules-2003.0211/lib/Time/ParseDate.pm
# http://stein.cshl.org/jade/distrib/docs/java.text.SimpleDateFormat.html


class _timelex(object):

    def __init__(self, instream):
        if isinstance(instream, str):
            instream = StringIO(instream)
        self.instream = instream
        self.wordchars = ('abcdfeghijklmnopqrstuvwxyz'
                          'ABCDEFGHIJKLMNOPQRSTUVWXYZ_'
                          'ßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'
                          'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ')
        self.numchars = '0123456789'
        self.whitespace = ' \t\r\n'
        self.charstack = []
        self.tokenstack = []
        self.eof = False

    def get_token(self):
        if self.tokenstack:
            return self.tokenstack.pop(0)
        seenletters = False
        token = None
        state = None
        wordchars = self.wordchars
        numchars = self.numchars
        whitespace = self.whitespace
        while not self.eof:
            if self.charstack:
                nextchar = self.charstack.pop(0)
            else:
                nextchar = self.instream.read(1)
                while nextchar == '\x00':
                    nextchar = self.instream.read(1)
            if not nextchar:
                self.eof = True
                break
            elif not state:
                token = nextchar
                if nextchar in wordchars:
                    state = 'a'
                elif nextchar in numchars:
                    state = '0'
                elif nextchar in whitespace:
                    token = ' '
                    break # emit token
                else:
                    break # emit token
            elif state == 'a':
                seenletters = True
                if nextchar in wordchars:
                    token += nextchar
                elif nextchar == '.':
                    token += nextchar
                    state = 'a.'
                else:
                    self.charstack.append(nextchar)
                    break # emit token
            elif state == '0':
                if nextchar in numchars:
                    token += nextchar
                elif nextchar == '.':
                    token += nextchar
                    state = '0.'
                else:
                    self.charstack.append(nextchar)
                    break # emit token
            elif state == 'a.':
                seenletters = True
                if nextchar == '.' or nextchar in wordchars:
                    token += nextchar
                elif nextchar in numchars and token[-1] == '.':
                    token += nextchar
                    state = '0.'
                else:
                    self.charstack.append(nextchar)
                    break # emit token
            elif state == '0.':
                if nextchar == '.' or nextchar in numchars:
                    token += nextchar
                elif nextchar in wordchars and token[-1] == '.':
                    token += nextchar
                    state = 'a.'
                else:
                    self.charstack.append(nextchar)
                    break # emit token
        if (state in ('a.', '0.') and
            (seenletters or token.count('.') > 1 or token[-1] == '.')):
            l = token.split('.')
            token = l[0]
            for tok in l[1:]:
                self.tokenstack.append('.')
                if tok:
                    self.tokenstack.append(tok)
        return token

    def __iter__(self):
        return self

    def __next__(self):
        token = self.get_token()
        if token is None:
            raise StopIteration
        return token

    def split(cls, s):
        return list(cls(s))
    split = classmethod(split)


class _resultbase(object):

    def __init__(self):
        for attr in self.__slots__:
            setattr(self, attr, None)

    def _repr(self, classname):
        l = []
        for attr in self.__slots__:
            value = getattr(self, attr)
            if value is not None:
                l.append("%s=%s" % (attr, repr(value)))
        return "%s(%s)" % (classname, ", ".join(l))

    def __repr__(self):
        return self._repr(self.__class__.__name__)


class parserinfo(object):

    # m from a.m/p.m, t from ISO T separator
    JUMP = [" ", ".", ",", ";", "-", "/", "'",
            "at", "on", "and", "ad", "m", "t", "of",
            "st", "nd", "rd", "th"] 

    WEEKDAYS = [("Mon", "Monday"),
                ("Tue", "Tuesday"),
                ("Wed", "Wednesday"),
                ("Thu", "Thursday"),
                ("Fri", "Friday"),
                ("Sat", "Saturday"),
                ("Sun", "Sunday")]
    MONTHS   = [("Jan", "January"),
                ("Feb", "February"),
                ("Mar", "March"),
                ("Apr", "April"),
                ("May", "May"),
                ("Jun", "June"),
                ("Jul", "July"),
                ("Aug", "August"),
                ("Sep", "September"),
                ("Oct", "October"),
                ("Nov", "November"),
                ("Dec", "December")]
    HMS = [("h", "hour", "hours"),
           ("m", "minute", "minutes"),
           ("s", "second", "seconds")]
    AMPM = [("am", "a"),
            ("pm", "p")]
    UTCZONE = ["UTC", "GMT", "Z"]
    PERTAIN = ["of"]
    TZOFFSET = {}

    def __init__(self, dayfirst=False, yearfirst=False):
        self._jump = self._convert(self.JUMP)
        self._weekdays = self._convert(self.WEEKDAYS)
        self._months = self._convert(self.MONTHS)
        self._hms = self._convert(self.HMS)
        self._ampm = self._convert(self.AMPM)
        self._utczone = self._convert(self.UTCZONE)
        self._pertain = self._convert(self.PERTAIN)

        self.dayfirst = dayfirst
        self.yearfirst = yearfirst

        self._year = time.localtime().tm_year
        self._century = self._year//100*100

    def _convert(self, lst):
        dct = {}
        for i in range(len(lst)):
            v = lst[i]
            if isinstance(v, tuple):
                for v in v:
                    dct[v.lower()] = i
            else:
                dct[v.lower()] = i
        return dct

    def jump(self, name):
        return name.lower() in self._jump

    def weekday(self, name):
        if len(name) >= 3:
            try:
                return self._weekdays[name.lower()]
            except KeyError:
                pass
        return None

    def month(self, name):
        if len(name) >= 3:
            try:
                return self._months[name.lower()]+1
            except KeyError:
                pass
        return None

    def hms(self, name):
        try:
            return self._hms[name.lower()]
        except KeyError:
            return None

    def ampm(self, name):
        try:
            return self._ampm[name.lower()]
        except KeyError:
            return None

    def pertain(self, name):
        return name.lower() in self._pertain

    def utczone(self, name):
        return name.lower() in self._utczone

    def tzoffset(self, name):
        if name in self._utczone:
            return 0
        return self.TZOFFSET.get(name)

    def convertyear(self, year):
        if year < 100:
            year += self._century
            if abs(year-self._year) >= 50:
                if year < self._year:
                    year += 100
                else:
                    year -= 100
        return year

    def validate(self, res):
        # move to info
        if res.year is not None:
            res.year = self.convertyear(res.year)
        if res.tzoffset == 0 and not res.tzname or res.tzname == 'Z':
            res.tzname = "UTC"
            res.tzoffset = 0
        elif res.tzoffset != 0 and res.tzname and self.utczone(res.tzname):
            res.tzoffset = 0
        return True


class parser(object):

    def __init__(self, info=None):
        self.info = info or parserinfo()

    def parse(self, timestr, default=None,
                    ignoretz=False, tzinfos=None,
                    **kwargs):
        if not default:
            default = datetime.datetime.now().replace(hour=0, minute=0,
                                                      second=0, microsecond=0)
        res = self._parse(timestr, **kwargs)
        if res is None:
            raise ValueError("unknown string format")
        repl = {}
        for attr in ["year", "month", "day", "hour",
                     "minute", "second", "microsecond"]:
            value = getattr(res, attr)
            if value is not None:
                repl[attr] = value
        ret = default.replace(**repl)
        if res.weekday is not None and not res.day:
            ret = ret+relativedelta.relativedelta(weekday=res.weekday)
        if not ignoretz:
            if isinstance(tzinfos, collections.Callable) or tzinfos and res.tzname in tzinfos:
                if isinstance(tzinfos, collections.Callable):
                    tzdata = tzinfos(res.tzname, res.tzoffset)
                else:
                    tzdata = tzinfos.get(res.tzname)
                if isinstance(tzdata, datetime.tzinfo):
                    tzinfo = tzdata
                elif isinstance(tzdata, str):
                    tzinfo = tz.tzstr(tzdata)
                elif isinstance(tzdata, int):
                    tzinfo = tz.tzoffset(res.tzname, tzdata)
                else:
                    raise ValueError("offset must be tzinfo subclass, " \
                                      "tz string, or int offset")
                ret = ret.replace(tzinfo=tzinfo)
            elif res.tzname and res.tzname in time.tzname:
                ret = ret.replace(tzinfo=tz.tzlocal())
            elif res.tzoffset == 0:
                ret = ret.replace(tzinfo=tz.tzutc())
            elif res.tzoffset:
                ret = ret.replace(tzinfo=tz.tzoffset(res.tzname, res.tzoffset))
        return ret

    class _result(_resultbase):
        __slots__ = ["year", "month", "day", "weekday",
                     "hour", "minute", "second", "microsecond",
                     "tzname", "tzoffset"]

    def _parse(self, timestr, dayfirst=None, yearfirst=None, fuzzy=False):
        info = self.info
        if dayfirst is None:
            dayfirst = info.dayfirst
        if yearfirst is None:
            yearfirst = info.yearfirst
        res = self._result()
        l = _timelex.split(timestr)
        try:

            # year/month/day list
            ymd = []

            # Index of the month string in ymd
            mstridx = -1

            len_l = len(l)
            i = 0
            while i < len_l:

                # Check if it's a number
                try:
                    value_repr = l[i]
                    value = float(value_repr)
                except ValueError:
                    value = None

                if value is not None:
                    # Token is a number
                    len_li = len(l[i])
                    i += 1
                    if (len(ymd) == 3 and len_li in (2, 4)
                        and (i >= len_l or (l[i] != ':' and
                                            info.hms(l[i]) is None))):
                        # 19990101T23[59]
                        s = l[i-1]
                        res.hour = int(s[:2])
                        if len_li == 4:
                            res.minute = int(s[2:])
                    elif len_li == 6 or (len_li > 6 and l[i-1].find('.') == 6):
                        # YYMMDD or HHMMSS[.ss]
                        s = l[i-1] 
                        if not ymd and l[i-1].find('.') == -1:
                            ymd.append(info.convertyear(int(s[:2])))
                            ymd.append(int(s[2:4]))
                            ymd.append(int(s[4:]))
                        else:
                            # 19990101T235959[.59]
                            res.hour = int(s[:2])
                            res.minute = int(s[2:4])
                            res.second, res.microsecond = _parsems(s[4:])
                    elif len_li == 8:
                        # YYYYMMDD
                        s = l[i-1]
                        ymd.append(int(s[:4]))
                        ymd.append(int(s[4:6]))
                        ymd.append(int(s[6:]))
                    elif len_li in (12, 14):
                        # YYYYMMDDhhmm[ss]
                        s = l[i-1]
                        ymd.append(int(s[:4]))
                        ymd.append(int(s[4:6]))
                        ymd.append(int(s[6:8]))
                        res.hour = int(s[8:10])
                        res.minute = int(s[10:12])
                        if len_li == 14:
                            res.second = int(s[12:])
                    elif ((i < len_l and info.hms(l[i]) is not None) or
                          (i+1 < len_l and l[i] == ' ' and
                           info.hms(l[i+1]) is not None)):
                        # HH[ ]h or MM[ ]m or SS[.ss][ ]s
                        if l[i] == ' ':
                            i += 1
                        idx = info.hms(l[i])
                        while True:
                            if idx == 0:
                                res.hour = int(value)
                                if value%1:
                                    res.minute = int(60*(value%1))
                            elif idx == 1:
                                res.minute = int(value)
                                if value%1:
                                    res.second = int(60*(value%1))
                            elif idx == 2:
                                res.second, res.microsecond = \
                                    _parsems(value_repr)
                            i += 1
                            if i >= len_l or idx == 2:
                                break
                            # 12h00
                            try:
                                value_repr = l[i]
                                value = float(value_repr)
                            except ValueError:
                                break
                            else:
                                i += 1
                                idx += 1
                                if i < len_l:
                                    newidx = info.hms(l[i])
                                    if newidx is not None:
                                        idx = newidx
                    elif i+1 < len_l and l[i] == ':':
                        # HH:MM[:SS[.ss]]
                        res.hour = int(value)
                        i += 1
                        value = float(l[i])
                        res.minute = int(value)
                        if value%1:
                            res.second = int(60*(value%1))
                        i += 1
                        if i < len_l and l[i] == ':':
                            res.second, res.microsecond = _parsems(l[i+1])
                            i += 2
                    elif i < len_l and l[i] in ('-', '/', '.'):
                        sep = l[i]
                        ymd.append(int(value))
                        i += 1
                        if i < len_l and not info.jump(l[i]):
                            try:
                                # 01-01[-01]
                                ymd.append(int(l[i]))
                            except ValueError:
                                # 01-Jan[-01]
                                value = info.month(l[i])
                                if value is not None:
                                    ymd.append(value)
                                    assert mstridx == -1
                                    mstridx = len(ymd)-1
                                else:
                                    return None
                            i += 1
                            if i < len_l and l[i] == sep:
                                # We have three members
                                i += 1
                                value = info.month(l[i])
                                if value is not None:
                                    ymd.append(value)
                                    mstridx = len(ymd)-1
                                    assert mstridx == -1
                                else:
                                    ymd.append(int(l[i]))
                                i += 1
                    elif i >= len_l or info.jump(l[i]):
                        if i+1 < len_l and info.ampm(l[i+1]) is not None:
                            # 12 am
                            res.hour = int(value)
                            if res.hour < 12 and info.ampm(l[i+1]) == 1:
                                res.hour += 12
                            elif res.hour == 12 and info.ampm(l[i+1]) == 0:
                                res.hour = 0
                            i += 1
                        else:
                            # Year, month or day
                            ymd.append(int(value))
                        i += 1
                    elif info.ampm(l[i]) is not None:
                        # 12am
                        res.hour = int(value)
                        if res.hour < 12 and info.ampm(l[i]) == 1:
                            res.hour += 12
                        elif res.hour == 12 and info.ampm(l[i]) == 0:
                            res.hour = 0
                        i += 1
                    elif not fuzzy:
                        return None
                    else:
                        i += 1
                    continue

                # Check weekday
                value = info.weekday(l[i])
                if value is not None:
                    res.weekday = value
                    i += 1
                    continue

                # Check month name
                value = info.month(l[i])
                if value is not None:
                    ymd.append(value)
                    assert mstridx == -1
                    mstridx = len(ymd)-1
                    i += 1
                    if i < len_l:
                        if l[i] in ('-', '/'):
                            # Jan-01[-99]
                            sep = l[i]
                            i += 1
                            ymd.append(int(l[i]))
                            i += 1
                            if i < len_l and l[i] == sep:
                                # Jan-01-99
                                i += 1
                                ymd.append(int(l[i]))
                                i += 1
                        elif (i+3 < len_l and l[i] == l[i+2] == ' '
                              and info.pertain(l[i+1])):
                            # Jan of 01
                            # In this case, 01 is clearly year
                            try:
                                value = int(l[i+3])
                            except ValueError:
                                # Wrong guess
                                pass
                            else:
                                # Convert it here to become unambiguous
                                ymd.append(info.convertyear(value))
                            i += 4
                    continue

                # Check am/pm
                value = info.ampm(l[i])
                if value is not None:
                    if value == 1 and res.hour < 12:
                        res.hour += 12
                    elif value == 0 and res.hour == 12:
                        res.hour = 0
                    i += 1
                    continue

                # Check for a timezone name
                if (res.hour is not None and len(l[i]) <= 5 and
                    res.tzname is None and res.tzoffset is None and
                    not [x for x in l[i] if x not in string.ascii_uppercase]):
                    res.tzname = l[i]
                    res.tzoffset = info.tzoffset(res.tzname)
                    i += 1

                    # Check for something like GMT+3, or BRST+3. Notice
                    # that it doesn't mean "I am 3 hours after GMT", but
                    # "my time +3 is GMT". If found, we reverse the
                    # logic so that timezone parsing code will get it
                    # right.
                    if i < len_l and l[i] in ('+', '-'):
                        l[i] = ('+', '-')[l[i] == '+']
                        res.tzoffset = None
                        if info.utczone(res.tzname):
                            # With something like GMT+3, the timezone
                            # is *not* GMT.
                            res.tzname = None

                    continue

                # Check for a numbered timezone
                if res.hour is not None and l[i] in ('+', '-'):
                    signal = (-1, 1)[l[i] == '+']
                    i += 1
                    len_li = len(l[i])
                    if len_li == 4:
                        # -0300
                        res.tzoffset = int(l[i][:2])*3600+int(l[i][2:])*60
                    elif i+1 < len_l and l[i+1] == ':':
                        # -03:00
                        res.tzoffset = int(l[i])*3600+int(l[i+2])*60
                        i += 2
                    elif len_li <= 2:
                        # -[0]3
                        res.tzoffset = int(l[i][:2])*3600
                    else:
                        return None
                    i += 1
                    res.tzoffset *= signal

                    # Look for a timezone name between parenthesis
                    if (i+3 < len_l and
                        info.jump(l[i]) and l[i+1] == '(' and l[i+3] == ')' and
                        3 <= len(l[i+2]) <= 5 and
                        not [x for x in l[i+2]
                                if x not in string.ascii_uppercase]):
                        # -0300 (BRST)
                        res.tzname = l[i+2]
                        i += 4
                    continue

                # Check jumps
                if not (info.jump(l[i]) or fuzzy):
                    return None

                i += 1

            # Process year/month/day
            len_ymd = len(ymd)
            if len_ymd > 3:
                # More than three members!?
                return None
            elif len_ymd == 1 or (mstridx != -1 and len_ymd == 2):
                # One member, or two members with a month string
                if mstridx != -1:
                    res.month = ymd[mstridx]
                    del ymd[mstridx]
                if len_ymd > 1 or mstridx == -1:
                    if ymd[0] > 31:
                        res.year = ymd[0]
                    else:
                        res.day = ymd[0]
            elif len_ymd == 2:
                # Two members with numbers
                if ymd[0] > 31:
                    # 99-01
                    res.year, res.month = ymd
                elif ymd[1] > 31:
                    # 01-99
                    res.month, res.year = ymd
                elif dayfirst and ymd[1] <= 12:
                    # 13-01
                    res.day, res.month = ymd
                else:
                    # 01-13
                    res.month, res.day = ymd
            if len_ymd == 3:
                # Three members
                if mstridx == 0:
                    res.month, res.day, res.year = ymd
                elif mstridx == 1:
                    if ymd[0] > 31 or (yearfirst and ymd[2] <= 31):
                        # 99-Jan-01
                        res.year, res.month, res.day = ymd
                    else:
                        # 01-Jan-01
                        # Give precendence to day-first, since
                        # two-digit years is usually hand-written.
                        res.day, res.month, res.year = ymd
                elif mstridx == 2:
                    # WTF!?
                    if ymd[1] > 31:
                        # 01-99-Jan
                        res.day, res.year, res.month = ymd
                    else:
                        # 99-01-Jan
                        res.year, res.day, res.month = ymd
                else:
                    if ymd[0] > 31 or \
                       (yearfirst and ymd[1] <= 12 and ymd[2] <= 31):
                        # 99-01-01
                        res.year, res.month, res.day = ymd
                    elif ymd[0] > 12 or (dayfirst and ymd[1] <= 12):
                        # 13-01-01
                        res.day, res.month, res.year = ymd
                    else:
                        # 01-13-01
                        res.month, res.day, res.year = ymd

        except (IndexError, ValueError, AssertionError):
            return None

        if not info.validate(res):
            return None
        return res

DEFAULTPARSER = parser()
def parse(timestr, parserinfo=None, **kwargs):
    if parserinfo:
        return parser(parserinfo).parse(timestr, **kwargs)
    else:
        return DEFAULTPARSER.parse(timestr, **kwargs)


class _tzparser(object):

    class _result(_resultbase):

        __slots__ = ["stdabbr", "stdoffset", "dstabbr", "dstoffset",
                     "start", "end"]

        class _attr(_resultbase):
            __slots__ = ["month", "week", "weekday",
                         "yday", "jyday", "day", "time"]

        def __repr__(self):
            return self._repr("")

        def __init__(self):
            _resultbase.__init__(self)
            self.start = self._attr()
            self.end = self._attr()

    def parse(self, tzstr):
        res = self._result()
        l = _timelex.split(tzstr)
        try:

            len_l = len(l)

            i = 0
            while i < len_l:
                # BRST+3[BRDT[+2]]
                j = i
                while j < len_l and not [x for x in l[j]
                                            if x in "0123456789:,-+"]:
                    j += 1
                if j != i:
                    if not res.stdabbr:
                        offattr = "stdoffset"
                        res.stdabbr = "".join(l[i:j])
                    else:
                        offattr = "dstoffset"
                        res.dstabbr = "".join(l[i:j])
                    i = j
                    if (i < len_l and
                        (l[i] in ('+', '-') or l[i][0] in "0123456789")):
                        if l[i] in ('+', '-'):
                            # Yes, that's right.  See the TZ variable
                            # documentation.
                            signal = (1, -1)[l[i] == '+']
                            i += 1
                        else:
                            signal = -1
                        len_li = len(l[i])
                        if len_li == 4:
                            # -0300
                            setattr(res, offattr,
                                    (int(l[i][:2])*3600+int(l[i][2:])*60)*signal)
                        elif i+1 < len_l and l[i+1] == ':':
                            # -03:00
                            setattr(res, offattr,
                                    (int(l[i])*3600+int(l[i+2])*60)*signal)
                            i += 2
                        elif len_li <= 2:
                            # -[0]3
                            setattr(res, offattr,
                                    int(l[i][:2])*3600*signal)
                        else:
                            return None
                        i += 1
                    if res.dstabbr:
                        break
                else:
                    break

            if i < len_l:
                for j in range(i, len_l):
                    if l[j] == ';': l[j] = ','

                assert l[i] == ','

                i += 1

            if i >= len_l:
                pass
            elif (8 <= l.count(',') <= 9 and
                not [y for x in l[i:] if x != ','
                       for y in x if y not in "0123456789"]):
                # GMT0BST,3,0,30,3600,10,0,26,7200[,3600]
                for x in (res.start, res.end):
                    x.month = int(l[i])
                    i += 2
                    if l[i] == '-':
                        value = int(l[i+1])*-1
                        i += 1
                    else:
                        value = int(l[i])
                    i += 2
                    if value:
                        x.week = value
                        x.weekday = (int(l[i])-1)%7
                    else:
                        x.day = int(l[i])
                    i += 2
                    x.time = int(l[i])
                    i += 2
                if i < len_l:
                    if l[i] in ('-', '+'):
                        signal = (-1, 1)[l[i] == "+"]
                        i += 1
                    else:
                        signal = 1
                    res.dstoffset = (res.stdoffset+int(l[i]))*signal
            elif (l.count(',') == 2 and l[i:].count('/') <= 2 and
                  not [y for x in l[i:] if x not in (',', '/', 'J', 'M',
                                                     '.', '-', ':')
                         for y in x if y not in "0123456789"]):
                for x in (res.start, res.end):
                    if l[i] == 'J':
                        # non-leap year day (1 based)
                        i += 1
                        x.jyday = int(l[i])
                    elif l[i] == 'M':
                        # month[-.]week[-.]weekday
                        i += 1
                        x.month = int(l[i])
                        i += 1
                        assert l[i] in ('-', '.')
                        i += 1
                        x.week = int(l[i])
                        if x.week == 5:
                            x.week = -1
                        i += 1
                        assert l[i] in ('-', '.')
                        i += 1
                        x.weekday = (int(l[i])-1)%7
                    else:
                        # year day (zero based)
                        x.yday = int(l[i])+1

                    i += 1

                    if i < len_l and l[i] == '/':
                        i += 1
                        # start time
                        len_li = len(l[i])
                        if len_li == 4:
                            # -0300
                            x.time = (int(l[i][:2])*3600+int(l[i][2:])*60)
                        elif i+1 < len_l and l[i+1] == ':':
                            # -03:00
                            x.time = int(l[i])*3600+int(l[i+2])*60
                            i += 2
                            if i+1 < len_l and l[i+1] == ':':
                                i += 2
                                x.time += int(l[i])
                        elif len_li <= 2:
                            # -[0]3
                            x.time = (int(l[i][:2])*3600)
                        else:
                            return None
                        i += 1

                    assert i == len_l or l[i] == ','

                    i += 1

                assert i >= len_l

        except (IndexError, ValueError, AssertionError):
            return None
        
        return res


DEFAULTTZPARSER = _tzparser()
def _parsetz(tzstr):
    return DEFAULTTZPARSER.parse(tzstr)


def _parsems(value):
    """Parse a I[.F] seconds value into (seconds, microseconds)."""
    if "." not in value:
        return int(value), 0
    else:
        i, f = value.split(".")
        return int(i), int(f.ljust(6, "0")[:6])


# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = relativedelta
"""
Copyright (c) 2003-2010  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "Simplified BSD"

import datetime
import calendar

__all__ = ["relativedelta", "MO", "TU", "WE", "TH", "FR", "SA", "SU"]

class weekday(object):
    __slots__ = ["weekday", "n"]

    def __init__(self, weekday, n=None):
        self.weekday = weekday
        self.n = n

    def __call__(self, n):
        if n == self.n:
            return self
        else:
            return self.__class__(self.weekday, n)

    def __eq__(self, other):
        try:
            if self.weekday != other.weekday or self.n != other.n:
                return False
        except AttributeError:
            return False
        return True

    def __repr__(self):
        s = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")[self.weekday]
        if not self.n:
            return s
        else:
            return "%s(%+d)" % (s, self.n)

MO, TU, WE, TH, FR, SA, SU = weekdays = tuple([weekday(x) for x in range(7)])

class relativedelta:
    """
The relativedelta type is based on the specification of the excelent
work done by M.-A. Lemburg in his mx.DateTime extension. However,
notice that this type does *NOT* implement the same algorithm as
his work. Do *NOT* expect it to behave like mx.DateTime's counterpart.

There's two different ways to build a relativedelta instance. The
first one is passing it two date/datetime classes:

    relativedelta(datetime1, datetime2)

And the other way is to use the following keyword arguments:

    year, month, day, hour, minute, second, microsecond:
        Absolute information.

    years, months, weeks, days, hours, minutes, seconds, microseconds:
        Relative information, may be negative.

    weekday:
        One of the weekday instances (MO, TU, etc). These instances may
        receive a parameter N, specifying the Nth weekday, which could
        be positive or negative (like MO(+1) or MO(-2). Not specifying
        it is the same as specifying +1. You can also use an integer,
        where 0=MO.

    leapdays:
        Will add given days to the date found, if year is a leap
        year, and the date found is post 28 of february.

    yearday, nlyearday:
        Set the yearday or the non-leap year day (jump leap days).
        These are converted to day/month/leapdays information.

Here is the behavior of operations with relativedelta:

1) Calculate the absolute year, using the 'year' argument, or the
   original datetime year, if the argument is not present.

2) Add the relative 'years' argument to the absolute year.

3) Do steps 1 and 2 for month/months.

4) Calculate the absolute day, using the 'day' argument, or the
   original datetime day, if the argument is not present. Then,
   subtract from the day until it fits in the year and month
   found after their operations.

5) Add the relative 'days' argument to the absolute day. Notice
   that the 'weeks' argument is multiplied by 7 and added to
   'days'.

6) Do steps 1 and 2 for hour/hours, minute/minutes, second/seconds,
   microsecond/microseconds.

7) If the 'weekday' argument is present, calculate the weekday,
   with the given (wday, nth) tuple. wday is the index of the
   weekday (0-6, 0=Mon), and nth is the number of weeks to add
   forward or backward, depending on its signal. Notice that if
   the calculated date is already Monday, for example, using
   (0, 1) or (0, -1) won't change the day.
    """

    def __init__(self, dt1=None, dt2=None,
                 years=0, months=0, days=0, leapdays=0, weeks=0,
                 hours=0, minutes=0, seconds=0, microseconds=0,
                 year=None, month=None, day=None, weekday=None,
                 yearday=None, nlyearday=None,
                 hour=None, minute=None, second=None, microsecond=None):
        if dt1 and dt2:
            if (not isinstance(dt1, datetime.date)) or (not isinstance(dt2, datetime.date)):
                raise TypeError("relativedelta only diffs datetime/date")
            if not type(dt1) == type(dt2): #isinstance(dt1, type(dt2)):
                if not isinstance(dt1, datetime.datetime):
                    dt1 = datetime.datetime.fromordinal(dt1.toordinal())
                elif not isinstance(dt2, datetime.datetime):
                    dt2 = datetime.datetime.fromordinal(dt2.toordinal())
            self.years = 0
            self.months = 0
            self.days = 0
            self.leapdays = 0
            self.hours = 0
            self.minutes = 0
            self.seconds = 0
            self.microseconds = 0
            self.year = None
            self.month = None
            self.day = None
            self.weekday = None
            self.hour = None
            self.minute = None
            self.second = None
            self.microsecond = None
            self._has_time = 0

            months = (dt1.year*12+dt1.month)-(dt2.year*12+dt2.month)
            self._set_months(months)
            dtm = self.__radd__(dt2)
            if dt1 < dt2:
                while dt1 > dtm:
                    months += 1
                    self._set_months(months)
                    dtm = self.__radd__(dt2)
            else:
                while dt1 < dtm:
                    months -= 1
                    self._set_months(months)
                    dtm = self.__radd__(dt2)
            delta = dt1 - dtm
            self.seconds = delta.seconds+delta.days*86400
            self.microseconds = delta.microseconds
        else:
            self.years = years
            self.months = months
            self.days = days+weeks*7
            self.leapdays = leapdays
            self.hours = hours
            self.minutes = minutes
            self.seconds = seconds
            self.microseconds = microseconds
            self.year = year
            self.month = month
            self.day = day
            self.hour = hour
            self.minute = minute
            self.second = second
            self.microsecond = microsecond

            if isinstance(weekday, int):
                self.weekday = weekdays[weekday]
            else:
                self.weekday = weekday

            yday = 0
            if nlyearday:
                yday = nlyearday
            elif yearday:
                yday = yearday
                if yearday > 59:
                    self.leapdays = -1
            if yday:
                ydayidx = [31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 366]
                for idx, ydays in enumerate(ydayidx):
                    if yday <= ydays:
                        self.month = idx+1
                        if idx == 0:
                            self.day = yday
                        else:
                            self.day = yday-ydayidx[idx-1]
                        break
                else:
                    raise ValueError("invalid year day (%d)" % yday)

        self._fix()

    def _fix(self):
        if abs(self.microseconds) > 999999:
            s = self.microseconds//abs(self.microseconds)
            div, mod = divmod(self.microseconds*s, 1000000)
            self.microseconds = mod*s
            self.seconds += div*s
        if abs(self.seconds) > 59:
            s = self.seconds//abs(self.seconds)
            div, mod = divmod(self.seconds*s, 60)
            self.seconds = mod*s
            self.minutes += div*s
        if abs(self.minutes) > 59:
            s = self.minutes//abs(self.minutes)
            div, mod = divmod(self.minutes*s, 60)
            self.minutes = mod*s
            self.hours += div*s
        if abs(self.hours) > 23:
            s = self.hours//abs(self.hours)
            div, mod = divmod(self.hours*s, 24)
            self.hours = mod*s
            self.days += div*s
        if abs(self.months) > 11:
            s = self.months//abs(self.months)
            div, mod = divmod(self.months*s, 12)
            self.months = mod*s
            self.years += div*s
        if (self.hours or self.minutes or self.seconds or self.microseconds or
            self.hour is not None or self.minute is not None or
            self.second is not None or self.microsecond is not None):
            self._has_time = 1
        else:
            self._has_time = 0

    def _set_months(self, months):
        self.months = months
        if abs(self.months) > 11:
            s = self.months//abs(self.months)
            div, mod = divmod(self.months*s, 12)
            self.months = mod*s
            self.years = div*s
        else:
            self.years = 0

    def __radd__(self, other):
        if not isinstance(other, datetime.date):
            raise TypeError("unsupported type for add operation")
        elif self._has_time and not isinstance(other, datetime.datetime):
            other = datetime.datetime.fromordinal(other.toordinal())
        year = (self.year or other.year)+self.years
        month = self.month or other.month
        if self.months:
            assert 1 <= abs(self.months) <= 12
            month += self.months
            if month > 12:
                year += 1
                month -= 12
            elif month < 1:
                year -= 1
                month += 12
        day = min(calendar.monthrange(year, month)[1],
                  self.day or other.day)
        repl = {"year": year, "month": month, "day": day}
        for attr in ["hour", "minute", "second", "microsecond"]:
            value = getattr(self, attr)
            if value is not None:
                repl[attr] = value
        days = self.days
        if self.leapdays and month > 2 and calendar.isleap(year):
            days += self.leapdays
        ret = (other.replace(**repl)
               + datetime.timedelta(days=days,
                                    hours=self.hours,
                                    minutes=self.minutes,
                                    seconds=self.seconds,
                                    microseconds=self.microseconds))
        if self.weekday:
            weekday, nth = self.weekday.weekday, self.weekday.n or 1
            jumpdays = (abs(nth)-1)*7
            if nth > 0:
                jumpdays += (7-ret.weekday()+weekday)%7
            else:
                jumpdays += (ret.weekday()-weekday)%7
                jumpdays *= -1
            ret += datetime.timedelta(days=jumpdays)
        return ret

    def __rsub__(self, other):
        return self.__neg__().__radd__(other)

    def __add__(self, other):
        if not isinstance(other, relativedelta):
            raise TypeError("unsupported type for add operation")
        return relativedelta(years=other.years+self.years,
                             months=other.months+self.months,
                             days=other.days+self.days,
                             hours=other.hours+self.hours,
                             minutes=other.minutes+self.minutes,
                             seconds=other.seconds+self.seconds,
                             microseconds=other.microseconds+self.microseconds,
                             leapdays=other.leapdays or self.leapdays,
                             year=other.year or self.year,
                             month=other.month or self.month,
                             day=other.day or self.day,
                             weekday=other.weekday or self.weekday,
                             hour=other.hour or self.hour,
                             minute=other.minute or self.minute,
                             second=other.second or self.second,
                             microsecond=other.second or self.microsecond)

    def __sub__(self, other):
        if not isinstance(other, relativedelta):
            raise TypeError("unsupported type for sub operation")
        return relativedelta(years=other.years-self.years,
                             months=other.months-self.months,
                             days=other.days-self.days,
                             hours=other.hours-self.hours,
                             minutes=other.minutes-self.minutes,
                             seconds=other.seconds-self.seconds,
                             microseconds=other.microseconds-self.microseconds,
                             leapdays=other.leapdays or self.leapdays,
                             year=other.year or self.year,
                             month=other.month or self.month,
                             day=other.day or self.day,
                             weekday=other.weekday or self.weekday,
                             hour=other.hour or self.hour,
                             minute=other.minute or self.minute,
                             second=other.second or self.second,
                             microsecond=other.second or self.microsecond)

    def __neg__(self):
        return relativedelta(years=-self.years,
                             months=-self.months,
                             days=-self.days,
                             hours=-self.hours,
                             minutes=-self.minutes,
                             seconds=-self.seconds,
                             microseconds=-self.microseconds,
                             leapdays=self.leapdays,
                             year=self.year,
                             month=self.month,
                             day=self.day,
                             weekday=self.weekday,
                             hour=self.hour,
                             minute=self.minute,
                             second=self.second,
                             microsecond=self.microsecond)

    def __bool__(self):
        return not (not self.years and
                    not self.months and
                    not self.days and
                    not self.hours and
                    not self.minutes and
                    not self.seconds and
                    not self.microseconds and
                    not self.leapdays and
                    self.year is None and
                    self.month is None and
                    self.day is None and
                    self.weekday is None and
                    self.hour is None and
                    self.minute is None and
                    self.second is None and
                    self.microsecond is None)

    def __mul__(self, other):
        f = float(other)
        return relativedelta(years=self.years*f,
                             months=self.months*f,
                             days=self.days*f,
                             hours=self.hours*f,
                             minutes=self.minutes*f,
                             seconds=self.seconds*f,
                             microseconds=self.microseconds*f,
                             leapdays=self.leapdays,
                             year=self.year,
                             month=self.month,
                             day=self.day,
                             weekday=self.weekday,
                             hour=self.hour,
                             minute=self.minute,
                             second=self.second,
                             microsecond=self.microsecond)

    def __eq__(self, other):
        if not isinstance(other, relativedelta):
            return False
        if self.weekday or other.weekday:
            if not self.weekday or not other.weekday:
                return False
            if self.weekday.weekday != other.weekday.weekday:
                return False
            n1, n2 = self.weekday.n, other.weekday.n
            if n1 != n2 and not ((not n1 or n1 == 1) and (not n2 or n2 == 1)):
                return False
        return (self.years == other.years and
                self.months == other.months and
                self.days == other.days and
                self.hours == other.hours and
                self.minutes == other.minutes and
                self.seconds == other.seconds and
                self.leapdays == other.leapdays and
                self.year == other.year and
                self.month == other.month and
                self.day == other.day and
                self.hour == other.hour and
                self.minute == other.minute and
                self.second == other.second and
                self.microsecond == other.microsecond)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __div__(self, other):
        return self.__mul__(1/float(other))

    def __repr__(self):
        l = []
        for attr in ["years", "months", "days", "leapdays",
                     "hours", "minutes", "seconds", "microseconds"]:
            value = getattr(self, attr)
            if value:
                l.append("%s=%+d" % (attr, value))
        for attr in ["year", "month", "day", "weekday",
                     "hour", "minute", "second", "microsecond"]:
            value = getattr(self, attr)
            if value is not None:
                l.append("%s=%s" % (attr, repr(value)))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(l))

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = rrule
"""
Copyright (c) 2003-2010  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "Simplified BSD"

import itertools
import datetime
import calendar
import _thread
import sys

__all__ = ["rrule", "rruleset", "rrulestr",
           "YEARLY", "MONTHLY", "WEEKLY", "DAILY",
           "HOURLY", "MINUTELY", "SECONDLY",
           "MO", "TU", "WE", "TH", "FR", "SA", "SU"]

# Every mask is 7 days longer to handle cross-year weekly periods.
M366MASK = tuple([1]*31+[2]*29+[3]*31+[4]*30+[5]*31+[6]*30+
                 [7]*31+[8]*31+[9]*30+[10]*31+[11]*30+[12]*31+[1]*7)
M365MASK = list(M366MASK)
M29, M30, M31 = list(range(1, 30)), list(range(1, 31)), list(range(1, 32))
MDAY366MASK = tuple(M31+M29+M31+M30+M31+M30+M31+M31+M30+M31+M30+M31+M31[:7])
MDAY365MASK = list(MDAY366MASK)
M29, M30, M31 = list(range(-29, 0)), list(range(-30, 0)), list(range(-31, 0))
NMDAY366MASK = tuple(M31+M29+M31+M30+M31+M30+M31+M31+M30+M31+M30+M31+M31[:7])
NMDAY365MASK = list(NMDAY366MASK)
M366RANGE = (0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366)
M365RANGE = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365)
WDAYMASK = [0, 1, 2, 3, 4, 5, 6]*55
del M29, M30, M31, M365MASK[59], MDAY365MASK[59], NMDAY365MASK[31]
MDAY365MASK = tuple(MDAY365MASK)
M365MASK = tuple(M365MASK)

(YEARLY,
 MONTHLY,
 WEEKLY,
 DAILY,
 HOURLY,
 MINUTELY,
 SECONDLY) = list(range(7))

# Imported on demand.
easter = None
parser = None

class weekday(object):
    __slots__ = ["weekday", "n"]

    def __init__(self, weekday, n=None):
        if n == 0:
            raise ValueError("Can't create weekday with n == 0")
        self.weekday = weekday
        self.n = n

    def __call__(self, n):
        if n == self.n:
            return self
        else:
            return self.__class__(self.weekday, n)

    def __eq__(self, other):
        try:
            if self.weekday != other.weekday or self.n != other.n:
                return False
        except AttributeError:
            return False
        return True

    def __repr__(self):
        s = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")[self.weekday]
        if not self.n:
            return s
        else:
            return "%s(%+d)" % (s, self.n)

MO, TU, WE, TH, FR, SA, SU = weekdays = tuple([weekday(x) for x in range(7)])

class rrulebase:
    def __init__(self, cache=False):
        if cache:
            self._cache = []
            self._cache_lock = _thread.allocate_lock()
            self._cache_gen  = self._iter()
            self._cache_complete = False
        else:
            self._cache = None
            self._cache_complete = False
        self._len = None

    def __iter__(self):
        if self._cache_complete:
            return iter(self._cache)
        elif self._cache is None:
            return self._iter()
        else:
            return self._iter_cached()

    def _iter_cached(self):
        i = 0
        gen = self._cache_gen
        cache = self._cache
        acquire = self._cache_lock.acquire
        release = self._cache_lock.release
        while gen:
            if i == len(cache):
                acquire()
                if self._cache_complete:
                    break
                try:
                    for j in range(10):
                        cache.append(next(gen))
                except StopIteration:
                    self._cache_gen = gen = None
                    self._cache_complete = True
                    break
                release()
            yield cache[i]
            i += 1
        while i < self._len:
            yield cache[i]
            i += 1

    def __getitem__(self, item):
        if self._cache_complete:
            return self._cache[item]
        elif isinstance(item, slice):
            if item.step and item.step < 0:
                return list(iter(self))[item]
            else:
                return list(itertools.islice(self,
                                             item.start or 0,
                                             item.stop or sys.maxsize,
                                             item.step or 1))
        elif item >= 0:
            gen = iter(self)
            try:
                for i in range(item+1):
                    res = next(gen)
            except StopIteration:
                raise IndexError
            return res
        else:
            return list(iter(self))[item]

    def __contains__(self, item):
        if self._cache_complete:
            return item in self._cache
        else:
            for i in self:
                if i == item:
                    return True
                elif i > item:
                    return False
        return False

    # __len__() introduces a large performance penality.
    def count(self):
        if self._len is None:
            for x in self: pass
        return self._len

    def before(self, dt, inc=False):
        if self._cache_complete:
            gen = self._cache
        else:
            gen = self
        last = None
        if inc:
            for i in gen:
                if i > dt:
                    break
                last = i
        else:
            for i in gen:
                if i >= dt:
                    break
                last = i
        return last

    def after(self, dt, inc=False):
        if self._cache_complete:
            gen = self._cache
        else:
            gen = self
        if inc:
            for i in gen:
                if i >= dt:
                    return i
        else:
            for i in gen:
                if i > dt:
                    return i
        return None

    def between(self, after, before, inc=False):
        if self._cache_complete:
            gen = self._cache
        else:
            gen = self
        started = False
        l = []
        if inc:
            for i in gen:
                if i > before:
                    break
                elif not started:
                    if i >= after:
                        started = True
                        l.append(i)
                else:
                    l.append(i)
        else:
            for i in gen:
                if i >= before:
                    break
                elif not started:
                    if i > after:
                        started = True
                        l.append(i)
                else:
                    l.append(i)
        return l

class rrule(rrulebase):
    def __init__(self, freq, dtstart=None,
                 interval=1, wkst=None, count=None, until=None, bysetpos=None,
                 bymonth=None, bymonthday=None, byyearday=None, byeaster=None,
                 byweekno=None, byweekday=None,
                 byhour=None, byminute=None, bysecond=None,
                 cache=False):
        rrulebase.__init__(self, cache)
        global easter
        if not dtstart:
            dtstart = datetime.datetime.now().replace(microsecond=0)
        elif not isinstance(dtstart, datetime.datetime):
            dtstart = datetime.datetime.fromordinal(dtstart.toordinal())
        else:
            dtstart = dtstart.replace(microsecond=0)
        self._dtstart = dtstart
        self._tzinfo = dtstart.tzinfo
        self._freq = freq
        self._interval = interval
        self._count = count
        if until and not isinstance(until, datetime.datetime):
            until = datetime.datetime.fromordinal(until.toordinal())
        self._until = until
        if wkst is None:
            self._wkst = calendar.firstweekday()
        elif isinstance(wkst, int):
            self._wkst = wkst
        else:
            self._wkst = wkst.weekday
        if bysetpos is None:
            self._bysetpos = None
        elif isinstance(bysetpos, int):
            if bysetpos == 0 or not (-366 <= bysetpos <= 366):
                raise ValueError("bysetpos must be between 1 and 366, "
                                 "or between -366 and -1")
            self._bysetpos = (bysetpos,)
        else:
            self._bysetpos = tuple(bysetpos)
            for pos in self._bysetpos:
                if pos == 0 or not (-366 <= pos <= 366):
                    raise ValueError("bysetpos must be between 1 and 366, "
                                     "or between -366 and -1")
        if not (byweekno or byyearday or bymonthday or
                byweekday is not None or byeaster is not None):
            if freq == YEARLY:
                if not bymonth:
                    bymonth = dtstart.month
                bymonthday = dtstart.day
            elif freq == MONTHLY:
                bymonthday = dtstart.day
            elif freq == WEEKLY:
                byweekday = dtstart.weekday()
        # bymonth
        if not bymonth:
            self._bymonth = None
        elif isinstance(bymonth, int):
            self._bymonth = (bymonth,)
        else:
            self._bymonth = tuple(bymonth)
        # byyearday
        if not byyearday:
            self._byyearday = None
        elif isinstance(byyearday, int):
            self._byyearday = (byyearday,)
        else:
            self._byyearday = tuple(byyearday)
        # byeaster
        if byeaster is not None:
            if not easter:
                from dateutil import easter
            if isinstance(byeaster, int):
                self._byeaster = (byeaster,)
            else:
                self._byeaster = tuple(byeaster)
        else:
            self._byeaster = None
        # bymonthay
        if not bymonthday:
            self._bymonthday = ()
            self._bynmonthday = ()
        elif isinstance(bymonthday, int):
            if bymonthday < 0:
                self._bynmonthday = (bymonthday,)
                self._bymonthday = ()
            else:
                self._bymonthday = (bymonthday,)
                self._bynmonthday = ()
        else:
            self._bymonthday = tuple([x for x in bymonthday if x > 0])
            self._bynmonthday = tuple([x for x in bymonthday if x < 0])
        # byweekno
        if byweekno is None:
            self._byweekno = None
        elif isinstance(byweekno, int):
            self._byweekno = (byweekno,)
        else:
            self._byweekno = tuple(byweekno)
        # byweekday / bynweekday
        if byweekday is None:
            self._byweekday = None
            self._bynweekday = None
        elif isinstance(byweekday, int):
            self._byweekday = (byweekday,)
            self._bynweekday = None
        elif hasattr(byweekday, "n"):
            if not byweekday.n or freq > MONTHLY:
                self._byweekday = (byweekday.weekday,)
                self._bynweekday = None
            else:
                self._bynweekday = ((byweekday.weekday, byweekday.n),)
                self._byweekday = None
        else:
            self._byweekday = []
            self._bynweekday = []
            for wday in byweekday:
                if isinstance(wday, int):
                    self._byweekday.append(wday)
                elif not wday.n or freq > MONTHLY:
                    self._byweekday.append(wday.weekday)
                else:
                    self._bynweekday.append((wday.weekday, wday.n))
            self._byweekday = tuple(self._byweekday)
            self._bynweekday = tuple(self._bynweekday)
            if not self._byweekday:
                self._byweekday = None
            elif not self._bynweekday:
                self._bynweekday = None
        # byhour
        if byhour is None:
            if freq < HOURLY:
                self._byhour = (dtstart.hour,)
            else:
                self._byhour = None
        elif isinstance(byhour, int):
            self._byhour = (byhour,)
        else:
            self._byhour = tuple(byhour)
        # byminute
        if byminute is None:
            if freq < MINUTELY:
                self._byminute = (dtstart.minute,)
            else:
                self._byminute = None
        elif isinstance(byminute, int):
            self._byminute = (byminute,)
        else:
            self._byminute = tuple(byminute)
        # bysecond
        if bysecond is None:
            if freq < SECONDLY:
                self._bysecond = (dtstart.second,)
            else:
                self._bysecond = None
        elif isinstance(bysecond, int):
            self._bysecond = (bysecond,)
        else:
            self._bysecond = tuple(bysecond)

        if self._freq >= HOURLY:
            self._timeset = None
        else:
            self._timeset = []
            for hour in self._byhour:
                for minute in self._byminute:
                    for second in self._bysecond:
                        self._timeset.append(
                                datetime.time(hour, minute, second,
                                                    tzinfo=self._tzinfo))
            self._timeset.sort()
            self._timeset = tuple(self._timeset)

    def _iter(self):
        year, month, day, hour, minute, second, weekday, yearday, _ = \
            self._dtstart.timetuple()

        # Some local variables to speed things up a bit
        freq = self._freq
        interval = self._interval
        wkst = self._wkst
        until = self._until
        bymonth = self._bymonth
        byweekno = self._byweekno
        byyearday = self._byyearday
        byweekday = self._byweekday
        byeaster = self._byeaster
        bymonthday = self._bymonthday
        bynmonthday = self._bynmonthday
        bysetpos = self._bysetpos
        byhour = self._byhour
        byminute = self._byminute
        bysecond = self._bysecond

        ii = _iterinfo(self)
        ii.rebuild(year, month)

        getdayset = {YEARLY:ii.ydayset,
                     MONTHLY:ii.mdayset,
                     WEEKLY:ii.wdayset,
                     DAILY:ii.ddayset,
                     HOURLY:ii.ddayset,
                     MINUTELY:ii.ddayset,
                     SECONDLY:ii.ddayset}[freq]
        
        if freq < HOURLY:
            timeset = self._timeset
        else:
            gettimeset = {HOURLY:ii.htimeset,
                          MINUTELY:ii.mtimeset,
                          SECONDLY:ii.stimeset}[freq]
            if ((freq >= HOURLY and
                 self._byhour and hour not in self._byhour) or
                (freq >= MINUTELY and
                 self._byminute and minute not in self._byminute) or
                (freq >= SECONDLY and
                 self._bysecond and second not in self._bysecond)):
                timeset = ()
            else:
                timeset = gettimeset(hour, minute, second)

        total = 0
        count = self._count
        while True:
            # Get dayset with the right frequency
            dayset, start, end = getdayset(year, month, day)

            # Do the "hard" work ;-)
            filtered = False
            for i in dayset[start:end]:
                if ((bymonth and ii.mmask[i] not in bymonth) or
                    (byweekno and not ii.wnomask[i]) or
                    (byweekday and ii.wdaymask[i] not in byweekday) or
                    (ii.nwdaymask and not ii.nwdaymask[i]) or
                    (byeaster and not ii.eastermask[i]) or
                    ((bymonthday or bynmonthday) and
                     ii.mdaymask[i] not in bymonthday and
                     ii.nmdaymask[i] not in bynmonthday) or
                    (byyearday and
                     ((i < ii.yearlen and i+1 not in byyearday
                                      and -ii.yearlen+i not in byyearday) or
                      (i >= ii.yearlen and i+1-ii.yearlen not in byyearday
                                       and -ii.nextyearlen+i-ii.yearlen
                                           not in byyearday)))):
                    dayset[i] = None
                    filtered = True

            # Output results
            if bysetpos and timeset:
                poslist = []
                for pos in bysetpos:
                    if pos < 0:
                        daypos, timepos = divmod(pos, len(timeset))
                    else:
                        daypos, timepos = divmod(pos-1, len(timeset))
                    try:
                        i = [x for x in dayset[start:end]
                                if x is not None][daypos]
                        time = timeset[timepos]
                    except IndexError:
                        pass
                    else:
                        date = datetime.date.fromordinal(ii.yearordinal+i)
                        res = datetime.datetime.combine(date, time)
                        if res not in poslist:
                            poslist.append(res)
                poslist.sort()
                for res in poslist:
                    if until and res > until:
                        self._len = total
                        return
                    elif res >= self._dtstart:
                        total += 1
                        yield res
                        if count:
                            count -= 1
                            if not count:
                                self._len = total
                                return
            else:
                for i in dayset[start:end]:
                    if i is not None:
                        date = datetime.date.fromordinal(ii.yearordinal+i)
                        for time in timeset:
                            res = datetime.datetime.combine(date, time)
                            if until and res > until:
                                self._len = total
                                return
                            elif res >= self._dtstart:
                                total += 1
                                yield res
                                if count:
                                    count -= 1
                                    if not count:
                                        self._len = total
                                        return

            # Handle frequency and interval
            fixday = False
            if freq == YEARLY:
                year += interval
                if year > datetime.MAXYEAR:
                    self._len = total
                    return
                ii.rebuild(year, month)
            elif freq == MONTHLY:
                month += interval
                if month > 12:
                    div, mod = divmod(month, 12)
                    month = mod
                    year += div
                    if month == 0:
                        month = 12
                        year -= 1
                    if year > datetime.MAXYEAR:
                        self._len = total
                        return
                ii.rebuild(year, month)
            elif freq == WEEKLY:
                if wkst > weekday:
                    day += -(weekday+1+(6-wkst))+self._interval*7
                else:
                    day += -(weekday-wkst)+self._interval*7
                weekday = wkst
                fixday = True
            elif freq == DAILY:
                day += interval
                fixday = True
            elif freq == HOURLY:
                if filtered:
                    # Jump to one iteration before next day
                    hour += ((23-hour)//interval)*interval
                while True:
                    hour += interval
                    div, mod = divmod(hour, 24)
                    if div:
                        hour = mod
                        day += div
                        fixday = True
                    if not byhour or hour in byhour:
                        break
                timeset = gettimeset(hour, minute, second)
            elif freq == MINUTELY:
                if filtered:
                    # Jump to one iteration before next day
                    minute += ((1439-(hour*60+minute))//interval)*interval
                while True:
                    minute += interval
                    div, mod = divmod(minute, 60)
                    if div:
                        minute = mod
                        hour += div
                        div, mod = divmod(hour, 24)
                        if div:
                            hour = mod
                            day += div
                            fixday = True
                            filtered = False
                    if ((not byhour or hour in byhour) and
                        (not byminute or minute in byminute)):
                        break
                timeset = gettimeset(hour, minute, second)
            elif freq == SECONDLY:
                if filtered:
                    # Jump to one iteration before next day
                    second += (((86399-(hour*3600+minute*60+second))
                                //interval)*interval)
                while True:
                    second += self._interval
                    div, mod = divmod(second, 60)
                    if div:
                        second = mod
                        minute += div
                        div, mod = divmod(minute, 60)
                        if div:
                            minute = mod
                            hour += div
                            div, mod = divmod(hour, 24)
                            if div:
                                hour = mod
                                day += div
                                fixday = True
                    if ((not byhour or hour in byhour) and
                        (not byminute or minute in byminute) and
                        (not bysecond or second in bysecond)):
                        break
                timeset = gettimeset(hour, minute, second)

            if fixday and day > 28:
                daysinmonth = calendar.monthrange(year, month)[1]
                if day > daysinmonth:
                    while day > daysinmonth:
                        day -= daysinmonth
                        month += 1
                        if month == 13:
                            month = 1
                            year += 1
                            if year > datetime.MAXYEAR:
                                self._len = total
                                return
                        daysinmonth = calendar.monthrange(year, month)[1]
                    ii.rebuild(year, month)

class _iterinfo(object):
    __slots__ = ["rrule", "lastyear", "lastmonth",
                 "yearlen", "nextyearlen", "yearordinal", "yearweekday",
                 "mmask", "mrange", "mdaymask", "nmdaymask",
                 "wdaymask", "wnomask", "nwdaymask", "eastermask"]

    def __init__(self, rrule):
        for attr in self.__slots__:
            setattr(self, attr, None)
        self.rrule = rrule

    def rebuild(self, year, month):
        # Every mask is 7 days longer to handle cross-year weekly periods.
        rr = self.rrule
        if year != self.lastyear:
            self.yearlen = 365+calendar.isleap(year)
            self.nextyearlen = 365+calendar.isleap(year+1)
            firstyday = datetime.date(year, 1, 1)
            self.yearordinal = firstyday.toordinal()
            self.yearweekday = firstyday.weekday()

            wday = datetime.date(year, 1, 1).weekday()
            if self.yearlen == 365:
                self.mmask = M365MASK
                self.mdaymask = MDAY365MASK
                self.nmdaymask = NMDAY365MASK
                self.wdaymask = WDAYMASK[wday:]
                self.mrange = M365RANGE
            else:
                self.mmask = M366MASK
                self.mdaymask = MDAY366MASK
                self.nmdaymask = NMDAY366MASK
                self.wdaymask = WDAYMASK[wday:]
                self.mrange = M366RANGE

            if not rr._byweekno:
                self.wnomask = None
            else:
                self.wnomask = [0]*(self.yearlen+7)
                #no1wkst = firstwkst = self.wdaymask.index(rr._wkst)
                no1wkst = firstwkst = (7-self.yearweekday+rr._wkst)%7
                if no1wkst >= 4:
                    no1wkst = 0
                    # Number of days in the year, plus the days we got
                    # from last year.
                    wyearlen = self.yearlen+(self.yearweekday-rr._wkst)%7
                else:
                    # Number of days in the year, minus the days we
                    # left in last year.
                    wyearlen = self.yearlen-no1wkst
                div, mod = divmod(wyearlen, 7)
                numweeks = div+mod//4
                for n in rr._byweekno:
                    if n < 0:
                        n += numweeks+1
                    if not (0 < n <= numweeks):
                        continue
                    if n > 1:
                        i = no1wkst+(n-1)*7
                        if no1wkst != firstwkst:
                            i -= 7-firstwkst
                    else:
                        i = no1wkst
                    for j in range(7):
                        self.wnomask[i] = 1
                        i += 1
                        if self.wdaymask[i] == rr._wkst:
                            break
                if 1 in rr._byweekno:
                    # Check week number 1 of next year as well
                    # TODO: Check -numweeks for next year.
                    i = no1wkst+numweeks*7
                    if no1wkst != firstwkst:
                        i -= 7-firstwkst
                    if i < self.yearlen:
                        # If week starts in next year, we
                        # don't care about it.
                        for j in range(7):
                            self.wnomask[i] = 1
                            i += 1
                            if self.wdaymask[i] == rr._wkst:
                                break
                if no1wkst:
                    # Check last week number of last year as
                    # well. If no1wkst is 0, either the year
                    # started on week start, or week number 1
                    # got days from last year, so there are no
                    # days from last year's last week number in
                    # this year.
                    if -1 not in rr._byweekno:
                        lyearweekday = datetime.date(year-1, 1, 1).weekday()
                        lno1wkst = (7-lyearweekday+rr._wkst)%7
                        lyearlen = 365+calendar.isleap(year-1)
                        if lno1wkst >= 4:
                            lno1wkst = 0
                            lnumweeks = 52+(lyearlen+
                                           (lyearweekday-rr._wkst)%7)%7//4
                        else:
                            lnumweeks = 52+(self.yearlen-no1wkst)%7//4
                    else:
                        lnumweeks = -1
                    if lnumweeks in rr._byweekno:
                        for i in range(no1wkst):
                            self.wnomask[i] = 1

        if (rr._bynweekday and
            (month != self.lastmonth or year != self.lastyear)):
            ranges = []
            if rr._freq == YEARLY:
                if rr._bymonth:
                    for month in rr._bymonth:
                        ranges.append(self.mrange[month-1:month+1])
                else:
                    ranges = [(0, self.yearlen)]
            elif rr._freq == MONTHLY:
                ranges = [self.mrange[month-1:month+1]]
            if ranges:
                # Weekly frequency won't get here, so we may not
                # care about cross-year weekly periods.
                self.nwdaymask = [0]*self.yearlen
                for first, last in ranges:
                    last -= 1
                    for wday, n in rr._bynweekday:
                        if n < 0:
                            i = last+(n+1)*7
                            i -= (self.wdaymask[i]-wday)%7
                        else:
                            i = first+(n-1)*7
                            i += (7-self.wdaymask[i]+wday)%7
                        if first <= i <= last:
                            self.nwdaymask[i] = 1

        if rr._byeaster:
            self.eastermask = [0]*(self.yearlen+7)
            eyday = easter.easter(year).toordinal()-self.yearordinal
            for offset in rr._byeaster:
                self.eastermask[eyday+offset] = 1

        self.lastyear = year
        self.lastmonth = month

    def ydayset(self, year, month, day):
        return list(range(self.yearlen)), 0, self.yearlen

    def mdayset(self, year, month, day):
        set = [None]*self.yearlen
        start, end = self.mrange[month-1:month+1]
        for i in range(start, end):
            set[i] = i
        return set, start, end

    def wdayset(self, year, month, day):
        # We need to handle cross-year weeks here.
        set = [None]*(self.yearlen+7)
        i = datetime.date(year, month, day).toordinal()-self.yearordinal
        start = i
        for j in range(7):
            set[i] = i
            i += 1
            #if (not (0 <= i < self.yearlen) or
            #    self.wdaymask[i] == self.rrule._wkst):
            # This will cross the year boundary, if necessary.
            if self.wdaymask[i] == self.rrule._wkst:
                break
        return set, start, i

    def ddayset(self, year, month, day):
        set = [None]*self.yearlen
        i = datetime.date(year, month, day).toordinal()-self.yearordinal
        set[i] = i
        return set, i, i+1

    def htimeset(self, hour, minute, second):
        set = []
        rr = self.rrule
        for minute in rr._byminute:
            for second in rr._bysecond:
                set.append(datetime.time(hour, minute, second,
                                         tzinfo=rr._tzinfo))
        set.sort()
        return set

    def mtimeset(self, hour, minute, second):
        set = []
        rr = self.rrule
        for second in rr._bysecond:
            set.append(datetime.time(hour, minute, second, tzinfo=rr._tzinfo))
        set.sort()
        return set

    def stimeset(self, hour, minute, second):
        return (datetime.time(hour, minute, second,
                tzinfo=self.rrule._tzinfo),)


class rruleset(rrulebase):

    class _genitem:
        def __init__(self, genlist, gen):
            try:
                self.dt = gen()
                genlist.append(self)
            except StopIteration:
                pass
            self.genlist = genlist
            self.gen = gen

        def __next__(self):
            try:
                self.dt = self.gen()
            except StopIteration:
                self.genlist.remove(self)

        def __lt__(self, other):
            return self.dt < other.dt

        def __gt__(self, other):
            return self.dt > other.dt

        def __eq__(self, other):
            return self.dt == other.dt

    def __init__(self, cache=False):
        rrulebase.__init__(self, cache)
        self._rrule = []
        self._rdate = []
        self._exrule = []
        self._exdate = []

    def rrule(self, rrule):
        self._rrule.append(rrule)
    
    def rdate(self, rdate):
        self._rdate.append(rdate)

    def exrule(self, exrule):
        self._exrule.append(exrule)

    def exdate(self, exdate):
        self._exdate.append(exdate)

    def _iter(self):
        rlist = []
        self._rdate.sort()
        self._genitem(rlist, iter(self._rdate).__next__)
        for gen in [iter(x).__next__ for x in self._rrule]:
            self._genitem(rlist, gen)
        rlist.sort()
        exlist = []
        self._exdate.sort()
        self._genitem(exlist, iter(self._exdate).__next__)
        for gen in [iter(x).__next__ for x in self._exrule]:
            self._genitem(exlist, gen)
        exlist.sort()
        lastdt = None
        total = 0
        while rlist:
            ritem = rlist[0]
            if not lastdt or lastdt != ritem.dt:
                while exlist and exlist[0] < ritem:
                    next(exlist[0])
                    exlist.sort()
                if not exlist or ritem != exlist[0]:
                    total += 1
                    yield ritem.dt
                lastdt = ritem.dt
            next(ritem)
            rlist.sort()
        self._len = total

class _rrulestr:

    _freq_map = {"YEARLY": YEARLY,
                 "MONTHLY": MONTHLY,
                 "WEEKLY": WEEKLY,
                 "DAILY": DAILY,
                 "HOURLY": HOURLY,
                 "MINUTELY": MINUTELY,
                 "SECONDLY": SECONDLY}

    _weekday_map = {"MO":0,"TU":1,"WE":2,"TH":3,"FR":4,"SA":5,"SU":6}

    def _handle_int(self, rrkwargs, name, value, **kwargs):
        rrkwargs[name.lower()] = int(value)

    def _handle_int_list(self, rrkwargs, name, value, **kwargs):
        rrkwargs[name.lower()] = [int(x) for x in value.split(',')]

    _handle_INTERVAL   = _handle_int
    _handle_COUNT      = _handle_int
    _handle_BYSETPOS   = _handle_int_list
    _handle_BYMONTH    = _handle_int_list
    _handle_BYMONTHDAY = _handle_int_list
    _handle_BYYEARDAY  = _handle_int_list
    _handle_BYEASTER   = _handle_int_list
    _handle_BYWEEKNO   = _handle_int_list
    _handle_BYHOUR     = _handle_int_list
    _handle_BYMINUTE   = _handle_int_list
    _handle_BYSECOND   = _handle_int_list

    def _handle_FREQ(self, rrkwargs, name, value, **kwargs):
        rrkwargs["freq"] = self._freq_map[value]

    def _handle_UNTIL(self, rrkwargs, name, value, **kwargs):
        global parser
        if not parser:
            from dateutil import parser
        try:
            rrkwargs["until"] = parser.parse(value,
                                           ignoretz=kwargs.get("ignoretz"),
                                           tzinfos=kwargs.get("tzinfos"))
        except ValueError:
            raise ValueError("invalid until date")

    def _handle_WKST(self, rrkwargs, name, value, **kwargs):
        rrkwargs["wkst"] = self._weekday_map[value]

    def _handle_BYWEEKDAY(self, rrkwargs, name, value, **kwarsg):
        l = []
        for wday in value.split(','):
            for i in range(len(wday)):
                if wday[i] not in '+-0123456789':
                    break
            n = wday[:i] or None
            w = wday[i:]
            if n: n = int(n)
            l.append(weekdays[self._weekday_map[w]](n))
        rrkwargs["byweekday"] = l

    _handle_BYDAY = _handle_BYWEEKDAY

    def _parse_rfc_rrule(self, line,
                         dtstart=None,
                         cache=False,
                         ignoretz=False,
                         tzinfos=None):
        if line.find(':') != -1:
            name, value = line.split(':')
            if name != "RRULE":
                raise ValueError("unknown parameter name")
        else:
            value = line
        rrkwargs = {}
        for pair in value.split(';'):
            name, value = pair.split('=')
            name = name.upper()
            value = value.upper()
            try:
                getattr(self, "_handle_"+name)(rrkwargs, name, value,
                                               ignoretz=ignoretz,
                                               tzinfos=tzinfos)
            except AttributeError:
                raise ValueError("unknown parameter '%s'" % name)
            except (KeyError, ValueError):
                raise ValueError("invalid '%s': %s" % (name, value))
        return rrule(dtstart=dtstart, cache=cache, **rrkwargs)

    def _parse_rfc(self, s,
                   dtstart=None,
                   cache=False,
                   unfold=False,
                   forceset=False,
                   compatible=False,
                   ignoretz=False,
                   tzinfos=None):
        global parser
        if compatible:
            forceset = True
            unfold = True
        s = s.upper()
        if not s.strip():
            raise ValueError("empty string")
        if unfold:
            lines = s.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].rstrip()
                if not line:
                    del lines[i]
                elif i > 0 and line[0] == " ":
                    lines[i-1] += line[1:]
                    del lines[i]
                else:
                    i += 1
        else:
            lines = s.split()
        if (not forceset and len(lines) == 1 and
            (s.find(':') == -1 or s.startswith('RRULE:'))):
            return self._parse_rfc_rrule(lines[0], cache=cache,
                                         dtstart=dtstart, ignoretz=ignoretz,
                                         tzinfos=tzinfos)
        else:
            rrulevals = []
            rdatevals = []
            exrulevals = []
            exdatevals = []
            for line in lines:
                if not line:
                    continue
                if line.find(':') == -1:
                    name = "RRULE"
                    value = line
                else:
                    name, value = line.split(':', 1)
                parms = name.split(';')
                if not parms:
                    raise ValueError("empty property name")
                name = parms[0]
                parms = parms[1:]
                if name == "RRULE":
                    for parm in parms:
                        raise ValueError("unsupported RRULE parm: "+parm)
                    rrulevals.append(value)
                elif name == "RDATE":
                    for parm in parms:
                        if parm != "VALUE=DATE-TIME":
                            raise ValueError("unsupported RDATE parm: "+parm)
                    rdatevals.append(value)
                elif name == "EXRULE":
                    for parm in parms:
                        raise ValueError("unsupported EXRULE parm: "+parm)
                    exrulevals.append(value)
                elif name == "EXDATE":
                    for parm in parms:
                        if parm != "VALUE=DATE-TIME":
                            raise ValueError("unsupported RDATE parm: "+parm)
                    exdatevals.append(value)
                elif name == "DTSTART":
                    for parm in parms:
                        raise ValueError("unsupported DTSTART parm: "+parm)
                    if not parser:
                        from dateutil import parser
                    dtstart = parser.parse(value, ignoretz=ignoretz,
                                           tzinfos=tzinfos)
                else:
                    raise ValueError("unsupported property: "+name)
            if (forceset or len(rrulevals) > 1 or
                rdatevals or exrulevals or exdatevals):
                if not parser and (rdatevals or exdatevals):
                    from dateutil import parser
                set = rruleset(cache=cache)
                for value in rrulevals:
                    set.rrule(self._parse_rfc_rrule(value, dtstart=dtstart,
                                                    ignoretz=ignoretz,
                                                    tzinfos=tzinfos))
                for value in rdatevals:
                    for datestr in value.split(','):
                        set.rdate(parser.parse(datestr,
                                               ignoretz=ignoretz,
                                               tzinfos=tzinfos))
                for value in exrulevals:
                    set.exrule(self._parse_rfc_rrule(value, dtstart=dtstart,
                                                     ignoretz=ignoretz,
                                                     tzinfos=tzinfos))
                for value in exdatevals:
                    for datestr in value.split(','):
                        set.exdate(parser.parse(datestr,
                                                ignoretz=ignoretz,
                                                tzinfos=tzinfos))
                if compatible and dtstart:
                    set.rdate(dtstart)
                return set
            else:
                return self._parse_rfc_rrule(rrulevals[0],
                                             dtstart=dtstart,
                                             cache=cache,
                                             ignoretz=ignoretz,
                                             tzinfos=tzinfos)

    def __call__(self, s, **kwargs):
        return self._parse_rfc(s, **kwargs)

rrulestr = _rrulestr()

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = tz
"""
Copyright (c) 2003-2007  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "Simplified BSD"

import datetime
import struct
import time
import sys
import os

relativedelta = None
parser = None
rrule = None

__all__ = ["tzutc", "tzoffset", "tzlocal", "tzfile", "tzrange",
           "tzstr", "tzical", "tzwin", "tzwinlocal", "gettz"]

try:
    from dateutil.tzwin import tzwin, tzwinlocal
except (ImportError, OSError):
    tzwin, tzwinlocal = None, None

ZERO = datetime.timedelta(0)
EPOCHORDINAL = datetime.datetime.utcfromtimestamp(0).toordinal()

class tzutc(datetime.tzinfo):

    def utcoffset(self, dt):
        return ZERO
     
    def dst(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def __eq__(self, other):
        return (isinstance(other, tzutc) or
                (isinstance(other, tzoffset) and other._offset == ZERO))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    __reduce__ = object.__reduce__

class tzoffset(datetime.tzinfo):

    def __init__(self, name, offset):
        self._name = name
        self._offset = datetime.timedelta(seconds=offset)

    def utcoffset(self, dt):
        return self._offset

    def dst(self, dt):
        return ZERO

    def tzname(self, dt):
        return self._name

    def __eq__(self, other):
        return (isinstance(other, tzoffset) and
                self._offset == other._offset)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__,
                               repr(self._name),
                               self._offset.days*86400+self._offset.seconds)

    __reduce__ = object.__reduce__

class tzlocal(datetime.tzinfo):

    _std_offset = datetime.timedelta(seconds=-time.timezone)
    if time.daylight:
        _dst_offset = datetime.timedelta(seconds=-time.altzone)
    else:
        _dst_offset = _std_offset

    def utcoffset(self, dt):
        if self._isdst(dt):
            return self._dst_offset
        else:
            return self._std_offset

    def dst(self, dt):
        if self._isdst(dt):
            return self._dst_offset-self._std_offset
        else:
            return ZERO

    def tzname(self, dt):
        return time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        # We can't use mktime here. It is unstable when deciding if
        # the hour near to a change is DST or not.
        # 
        # timestamp = time.mktime((dt.year, dt.month, dt.day, dt.hour,
        #                         dt.minute, dt.second, dt.weekday(), 0, -1))
        # return time.localtime(timestamp).tm_isdst
        #
        # The code above yields the following result:
        #
        #>>> import tz, datetime
        #>>> t = tz.tzlocal()
        #>>> datetime.datetime(2003,2,15,23,tzinfo=t).tzname()
        #'BRDT'
        #>>> datetime.datetime(2003,2,16,0,tzinfo=t).tzname()
        #'BRST'
        #>>> datetime.datetime(2003,2,15,23,tzinfo=t).tzname()
        #'BRST'
        #>>> datetime.datetime(2003,2,15,22,tzinfo=t).tzname()
        #'BRDT'
        #>>> datetime.datetime(2003,2,15,23,tzinfo=t).tzname()
        #'BRDT'
        #
        # Here is a more stable implementation:
        #
        timestamp = ((dt.toordinal() - EPOCHORDINAL) * 86400
                     + dt.hour * 3600
                     + dt.minute * 60
                     + dt.second)
        return time.localtime(timestamp+time.timezone).tm_isdst

    def __eq__(self, other):
        if not isinstance(other, tzlocal):
            return False
        return (self._std_offset == other._std_offset and
                self._dst_offset == other._dst_offset)
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    __reduce__ = object.__reduce__

class _ttinfo(object):
    __slots__ = ["offset", "delta", "isdst", "abbr", "isstd", "isgmt"]

    def __init__(self):
        for attr in self.__slots__:
            setattr(self, attr, None)

    def __repr__(self):
        l = []
        for attr in self.__slots__:
            value = getattr(self, attr)
            if value is not None:
                l.append("%s=%s" % (attr, repr(value)))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(l))

    def __eq__(self, other):
        if not isinstance(other, _ttinfo):
            return False
        return (self.offset == other.offset and
                self.delta == other.delta and
                self.isdst == other.isdst and
                self.abbr == other.abbr and
                self.isstd == other.isstd and
                self.isgmt == other.isgmt)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __getstate__(self):
        state = {}
        for name in self.__slots__:
            state[name] = getattr(self, name, None)
        return state

    def __setstate__(self, state):
        for name in self.__slots__:
            if name in state:
                setattr(self, name, state[name])

class tzfile(datetime.tzinfo):

    # http://www.twinsun.com/tz/tz-link.htm
    # ftp://elsie.nci.nih.gov/pub/tz*.tar.gz
    
    def __init__(self, fileobj):
        if isinstance(fileobj, str):
            self._filename = fileobj
            fileobj = open(fileobj, 'rb')
        elif hasattr(fileobj, "name"):
            self._filename = fileobj.name
        else:
            self._filename = repr(fileobj)

        # From tzfile(5):
        #
        # The time zone information files used by tzset(3)
        # begin with the magic characters "TZif" to identify
        # them as time zone information files, followed by
        # sixteen bytes reserved for future use, followed by
        # six four-byte values of type long, written in a
        # ``standard'' byte order (the high-order  byte
        # of the value is written first).

        if fileobj.read(4).decode() != "TZif":
            raise ValueError("magic not found")

        fileobj.read(16)

        (
         # The number of UTC/local indicators stored in the file.
         ttisgmtcnt,

         # The number of standard/wall indicators stored in the file.
         ttisstdcnt,
         
         # The number of leap seconds for which data is
         # stored in the file.
         leapcnt,

         # The number of "transition times" for which data
         # is stored in the file.
         timecnt,

         # The number of "local time types" for which data
         # is stored in the file (must not be zero).
         typecnt,

         # The  number  of  characters  of "time zone
         # abbreviation strings" stored in the file.
         charcnt,

        ) = struct.unpack(">6l", fileobj.read(24))

        # The above header is followed by tzh_timecnt four-byte
        # values  of  type long,  sorted  in ascending order.
        # These values are written in ``standard'' byte order.
        # Each is used as a transition time (as  returned  by
        # time(2)) at which the rules for computing local time
        # change.

        if timecnt:
            self._trans_list = struct.unpack(">%dl" % timecnt,
                                             fileobj.read(timecnt*4))
        else:
            self._trans_list = []

        # Next come tzh_timecnt one-byte values of type unsigned
        # char; each one tells which of the different types of
        # ``local time'' types described in the file is associated
        # with the same-indexed transition time. These values
        # serve as indices into an array of ttinfo structures that
        # appears next in the file.
        
        if timecnt:
            self._trans_idx = struct.unpack(">%dB" % timecnt,
                                            fileobj.read(timecnt))
        else:
            self._trans_idx = []
        
        # Each ttinfo structure is written as a four-byte value
        # for tt_gmtoff  of  type long,  in  a  standard  byte
        # order, followed  by a one-byte value for tt_isdst
        # and a one-byte  value  for  tt_abbrind.   In  each
        # structure, tt_gmtoff  gives  the  number  of
        # seconds to be added to UTC, tt_isdst tells whether
        # tm_isdst should be set by  localtime(3),  and
        # tt_abbrind serves  as an index into the array of
        # time zone abbreviation characters that follow the
        # ttinfo structure(s) in the file.

        ttinfo = []

        for i in range(typecnt):
            ttinfo.append(struct.unpack(">lbb", fileobj.read(6)))

        abbr = fileobj.read(charcnt).decode()

        # Then there are tzh_leapcnt pairs of four-byte
        # values, written in  standard byte  order;  the
        # first  value  of  each pair gives the time (as
        # returned by time(2)) at which a leap second
        # occurs;  the  second  gives the  total  number of
        # leap seconds to be applied after the given time.
        # The pairs of values are sorted in ascending order
        # by time.

        # Not used, for now
        if leapcnt:
            leap = struct.unpack(">%dl" % (leapcnt*2),
                                 fileobj.read(leapcnt*8))

        # Then there are tzh_ttisstdcnt standard/wall
        # indicators, each stored as a one-byte value;
        # they tell whether the transition times associated
        # with local time types were specified as standard
        # time or wall clock time, and are used when
        # a time zone file is used in handling POSIX-style
        # time zone environment variables.

        if ttisstdcnt:
            isstd = struct.unpack(">%db" % ttisstdcnt,
                                  fileobj.read(ttisstdcnt))

        # Finally, there are tzh_ttisgmtcnt UTC/local
        # indicators, each stored as a one-byte value;
        # they tell whether the transition times associated
        # with local time types were specified as UTC or
        # local time, and are used when a time zone file
        # is used in handling POSIX-style time zone envi-
        # ronment variables.

        if ttisgmtcnt:
            isgmt = struct.unpack(">%db" % ttisgmtcnt,
                                  fileobj.read(ttisgmtcnt))

        # ** Everything has been read **

        # Build ttinfo list
        self._ttinfo_list = []
        for i in range(typecnt):
            gmtoff, isdst, abbrind =  ttinfo[i]
            # Round to full-minutes if that's not the case. Python's
            # datetime doesn't accept sub-minute timezones. Check
            # http://python.org/sf/1447945 for some information.
            gmtoff = (gmtoff+30)//60*60
            tti = _ttinfo()
            tti.offset = gmtoff
            tti.delta = datetime.timedelta(seconds=gmtoff)
            tti.isdst = isdst
            tti.abbr = abbr[abbrind:abbr.find('\x00', abbrind)]
            tti.isstd = (ttisstdcnt > i and isstd[i] != 0)
            tti.isgmt = (ttisgmtcnt > i and isgmt[i] != 0)
            self._ttinfo_list.append(tti)

        # Replace ttinfo indexes for ttinfo objects.
        trans_idx = []
        for idx in self._trans_idx:
            trans_idx.append(self._ttinfo_list[idx])
        self._trans_idx = tuple(trans_idx)

        # Set standard, dst, and before ttinfos. before will be
        # used when a given time is before any transitions,
        # and will be set to the first non-dst ttinfo, or to
        # the first dst, if all of them are dst.
        self._ttinfo_std = None
        self._ttinfo_dst = None
        self._ttinfo_before = None
        if self._ttinfo_list:
            if not self._trans_list:
                self._ttinfo_std = self._ttinfo_first = self._ttinfo_list[0]
            else:
                for i in range(timecnt-1, -1, -1):
                    tti = self._trans_idx[i]
                    if not self._ttinfo_std and not tti.isdst:
                        self._ttinfo_std = tti
                    elif not self._ttinfo_dst and tti.isdst:
                        self._ttinfo_dst = tti
                    if self._ttinfo_std and self._ttinfo_dst:
                        break
                else:
                    if self._ttinfo_dst and not self._ttinfo_std:
                        self._ttinfo_std = self._ttinfo_dst

                for tti in self._ttinfo_list:
                    if not tti.isdst:
                        self._ttinfo_before = tti
                        break
                else:
                    self._ttinfo_before = self._ttinfo_list[0]

        # Now fix transition times to become relative to wall time.
        #
        # I'm not sure about this. In my tests, the tz source file
        # is setup to wall time, and in the binary file isstd and
        # isgmt are off, so it should be in wall time. OTOH, it's
        # always in gmt time. Let me know if you have comments
        # about this.
        laststdoffset = 0
        self._trans_list = list(self._trans_list)
        for i in range(len(self._trans_list)):
            tti = self._trans_idx[i]
            if not tti.isdst:
                # This is std time.
                self._trans_list[i] += tti.offset
                laststdoffset = tti.offset
            else:
                # This is dst time. Convert to std.
                self._trans_list[i] += laststdoffset
        self._trans_list = tuple(self._trans_list)

    def _find_ttinfo(self, dt, laststd=0):
        timestamp = ((dt.toordinal() - EPOCHORDINAL) * 86400
                     + dt.hour * 3600
                     + dt.minute * 60
                     + dt.second)
        idx = 0
        for trans in self._trans_list:
            if timestamp < trans:
                break
            idx += 1
        else:
            return self._ttinfo_std
        if idx == 0:
            return self._ttinfo_before
        if laststd:
            while idx > 0:
                tti = self._trans_idx[idx-1]
                if not tti.isdst:
                    return tti
                idx -= 1
            else:
                return self._ttinfo_std
        else:
            return self._trans_idx[idx-1]

    def utcoffset(self, dt):
        if not self._ttinfo_std:
            return ZERO
        return self._find_ttinfo(dt).delta

    def dst(self, dt):
        if not self._ttinfo_dst:
            return ZERO
        tti = self._find_ttinfo(dt)
        if not tti.isdst:
            return ZERO

        # The documentation says that utcoffset()-dst() must
        # be constant for every dt.
        return tti.delta-self._find_ttinfo(dt, laststd=1).delta

        # An alternative for that would be:
        #
        # return self._ttinfo_dst.offset-self._ttinfo_std.offset
        #
        # However, this class stores historical changes in the
        # dst offset, so I belive that this wouldn't be the right
        # way to implement this.
        
    def tzname(self, dt):
        if not self._ttinfo_std:
            return None
        return self._find_ttinfo(dt).abbr

    def __eq__(self, other):
        if not isinstance(other, tzfile):
            return False
        return (self._trans_list == other._trans_list and
                self._trans_idx == other._trans_idx and
                self._ttinfo_list == other._ttinfo_list)

    def __ne__(self, other):
        return not self.__eq__(other)


    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self._filename))

    def __reduce__(self):
        if not os.path.isfile(self._filename):
            raise ValueError("Unpickable %s class" % self.__class__.__name__)
        return (self.__class__, (self._filename,))

class tzrange(datetime.tzinfo):

    def __init__(self, stdabbr, stdoffset=None,
                 dstabbr=None, dstoffset=None,
                 start=None, end=None):
        global relativedelta
        if not relativedelta:
            from dateutil import relativedelta
        self._std_abbr = stdabbr
        self._dst_abbr = dstabbr
        if stdoffset is not None:
            self._std_offset = datetime.timedelta(seconds=stdoffset)
        else:
            self._std_offset = ZERO
        if dstoffset is not None:
            self._dst_offset = datetime.timedelta(seconds=dstoffset)
        elif dstabbr and stdoffset is not None:
            self._dst_offset = self._std_offset+datetime.timedelta(hours=+1)
        else:
            self._dst_offset = ZERO
        if dstabbr and start is None:
            self._start_delta = relativedelta.relativedelta(
                    hours=+2, month=4, day=1, weekday=relativedelta.SU(+1))
        else:
            self._start_delta = start
        if dstabbr and end is None:
            self._end_delta = relativedelta.relativedelta(
                    hours=+1, month=10, day=31, weekday=relativedelta.SU(-1))
        else:
            self._end_delta = end

    def utcoffset(self, dt):
        if self._isdst(dt):
            return self._dst_offset
        else:
            return self._std_offset

    def dst(self, dt):
        if self._isdst(dt):
            return self._dst_offset-self._std_offset
        else:
            return ZERO

    def tzname(self, dt):
        if self._isdst(dt):
            return self._dst_abbr
        else:
            return self._std_abbr

    def _isdst(self, dt):
        if not self._start_delta:
            return False
        year = datetime.datetime(dt.year, 1, 1)
        start = year+self._start_delta
        end = year+self._end_delta
        dt = dt.replace(tzinfo=None)
        if start < end:
            return dt >= start and dt < end
        else:
            return dt >= start or dt < end

    def __eq__(self, other):
        if not isinstance(other, tzrange):
            return False
        return (self._std_abbr == other._std_abbr and
                self._dst_abbr == other._dst_abbr and
                self._std_offset == other._std_offset and
                self._dst_offset == other._dst_offset and
                self._start_delta == other._start_delta and
                self._end_delta == other._end_delta)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s(...)" % self.__class__.__name__

    __reduce__ = object.__reduce__

class tzstr(tzrange):
    
    def __init__(self, s):
        global parser
        if not parser:
            from dateutil import parser
        self._s = s

        res = parser._parsetz(s)
        if res is None:
            raise ValueError("unknown string format")

        # Here we break the compatibility with the TZ variable handling.
        # GMT-3 actually *means* the timezone -3.
        if res.stdabbr in ("GMT", "UTC"):
            res.stdoffset *= -1

        # We must initialize it first, since _delta() needs
        # _std_offset and _dst_offset set. Use False in start/end
        # to avoid building it two times.
        tzrange.__init__(self, res.stdabbr, res.stdoffset,
                         res.dstabbr, res.dstoffset,
                         start=False, end=False)

        if not res.dstabbr:
            self._start_delta = None
            self._end_delta = None
        else:
            self._start_delta = self._delta(res.start)
            if self._start_delta:
                self._end_delta = self._delta(res.end, isend=1)

    def _delta(self, x, isend=0):
        kwargs = {}
        if x.month is not None:
            kwargs["month"] = x.month
            if x.weekday is not None:
                kwargs["weekday"] = relativedelta.weekday(x.weekday, x.week)
                if x.week > 0:
                    kwargs["day"] = 1
                else:
                    kwargs["day"] = 31
            elif x.day:
                kwargs["day"] = x.day
        elif x.yday is not None:
            kwargs["yearday"] = x.yday
        elif x.jyday is not None:
            kwargs["nlyearday"] = x.jyday
        if not kwargs:
            # Default is to start on first sunday of april, and end
            # on last sunday of october.
            if not isend:
                kwargs["month"] = 4
                kwargs["day"] = 1
                kwargs["weekday"] = relativedelta.SU(+1)
            else:
                kwargs["month"] = 10
                kwargs["day"] = 31
                kwargs["weekday"] = relativedelta.SU(-1)
        if x.time is not None:
            kwargs["seconds"] = x.time
        else:
            # Default is 2AM.
            kwargs["seconds"] = 7200
        if isend:
            # Convert to standard time, to follow the documented way
            # of working with the extra hour. See the documentation
            # of the tzinfo class.
            delta = self._dst_offset-self._std_offset
            kwargs["seconds"] -= delta.seconds+delta.days*86400
        return relativedelta.relativedelta(**kwargs)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self._s))

class _tzicalvtzcomp:
    def __init__(self, tzoffsetfrom, tzoffsetto, isdst,
                       tzname=None, rrule=None):
        self.tzoffsetfrom = datetime.timedelta(seconds=tzoffsetfrom)
        self.tzoffsetto = datetime.timedelta(seconds=tzoffsetto)
        self.tzoffsetdiff = self.tzoffsetto-self.tzoffsetfrom
        self.isdst = isdst
        self.tzname = tzname
        self.rrule = rrule

class _tzicalvtz(datetime.tzinfo):
    def __init__(self, tzid, comps=[]):
        self._tzid = tzid
        self._comps = comps
        self._cachedate = []
        self._cachecomp = []

    def _find_comp(self, dt):
        if len(self._comps) == 1:
            return self._comps[0]
        dt = dt.replace(tzinfo=None)
        try:
            return self._cachecomp[self._cachedate.index(dt)]
        except ValueError:
            pass
        lastcomp = None
        lastcompdt = None
        for comp in self._comps:
            if not comp.isdst:
                # Handle the extra hour in DST -> STD
                compdt = comp.rrule.before(dt-comp.tzoffsetdiff, inc=True)
            else:
                compdt = comp.rrule.before(dt, inc=True)
            if compdt and (not lastcompdt or lastcompdt < compdt):
                lastcompdt = compdt
                lastcomp = comp
        if not lastcomp:
            # RFC says nothing about what to do when a given
            # time is before the first onset date. We'll look for the
            # first standard component, or the first component, if
            # none is found.
            for comp in self._comps:
                if not comp.isdst:
                    lastcomp = comp
                    break
            else:
                lastcomp = comp[0]
        self._cachedate.insert(0, dt)
        self._cachecomp.insert(0, lastcomp)
        if len(self._cachedate) > 10:
            self._cachedate.pop()
            self._cachecomp.pop()
        return lastcomp

    def utcoffset(self, dt):
        return self._find_comp(dt).tzoffsetto

    def dst(self, dt):
        comp = self._find_comp(dt)
        if comp.isdst:
            return comp.tzoffsetdiff
        else:
            return ZERO

    def tzname(self, dt):
        return self._find_comp(dt).tzname

    def __repr__(self):
        return "<tzicalvtz %s>" % repr(self._tzid)

    __reduce__ = object.__reduce__

class tzical:
    def __init__(self, fileobj):
        global rrule
        if not rrule:
            from dateutil import rrule

        if isinstance(fileobj, str):
            self._s = fileobj
            fileobj = open(fileobj)
        elif hasattr(fileobj, "name"):
            self._s = fileobj.name
        else:
            self._s = repr(fileobj)

        self._vtz = {}

        self._parse_rfc(fileobj.read())

    def keys(self):
        return list(self._vtz.keys())

    def get(self, tzid=None):
        if tzid is None:
            keys = list(self._vtz.keys())
            if len(keys) == 0:
                raise ValueError("no timezones defined")
            elif len(keys) > 1:
                raise ValueError("more than one timezone available")
            tzid = keys[0]
        return self._vtz.get(tzid)

    def _parse_offset(self, s):
        s = s.strip()
        if not s:
            raise ValueError("empty offset")
        if s[0] in ('+', '-'):
            signal = (-1, +1)[s[0]=='+']
            s = s[1:]
        else:
            signal = +1
        if len(s) == 4:
            return (int(s[:2])*3600+int(s[2:])*60)*signal
        elif len(s) == 6:
            return (int(s[:2])*3600+int(s[2:4])*60+int(s[4:]))*signal
        else:
            raise ValueError("invalid offset: "+s)

    def _parse_rfc(self, s):
        lines = s.splitlines()
        if not lines:
            raise ValueError("empty string")

        # Unfold
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            if not line:
                del lines[i]
            elif i > 0 and line[0] == " ":
                lines[i-1] += line[1:]
                del lines[i]
            else:
                i += 1

        tzid = None
        comps = []
        invtz = False
        comptype = None
        for line in lines:
            if not line:
                continue
            name, value = line.split(':', 1)
            parms = name.split(';')
            if not parms:
                raise ValueError("empty property name")
            name = parms[0].upper()
            parms = parms[1:]
            if invtz:
                if name == "BEGIN":
                    if value in ("STANDARD", "DAYLIGHT"):
                        # Process component
                        pass
                    else:
                        raise ValueError("unknown component: "+value)
                    comptype = value
                    founddtstart = False
                    tzoffsetfrom = None
                    tzoffsetto = None
                    rrulelines = []
                    tzname = None
                elif name == "END":
                    if value == "VTIMEZONE":
                        if comptype:
                            raise ValueError("component not closed: "+comptype)
                        if not tzid:
                            raise ValueError("mandatory TZID not found")
                        if not comps:
                            raise ValueError("at least one component is needed")
                        # Process vtimezone
                        self._vtz[tzid] = _tzicalvtz(tzid, comps)
                        invtz = False
                    elif value == comptype:
                        if not founddtstart:
                            raise ValueError("mandatory DTSTART not found")
                        if tzoffsetfrom is None:
                            raise ValueError("mandatory TZOFFSETFROM not found")
                        if tzoffsetto is None:
                            raise ValueError("mandatory TZOFFSETFROM not found")
                        # Process component
                        rr = None
                        if rrulelines:
                            rr = rrule.rrulestr("\n".join(rrulelines),
                                                compatible=True,
                                                ignoretz=True,
                                                cache=True)
                        comp = _tzicalvtzcomp(tzoffsetfrom, tzoffsetto,
                                              (comptype == "DAYLIGHT"),
                                              tzname, rr)
                        comps.append(comp)
                        comptype = None
                    else:
                        raise ValueError("invalid component end: "+value)
                elif comptype:
                    if name == "DTSTART":
                        rrulelines.append(line)
                        founddtstart = True
                    elif name in ("RRULE", "RDATE", "EXRULE", "EXDATE"):
                        rrulelines.append(line)
                    elif name == "TZOFFSETFROM":
                        if parms:
                            raise ValueError("unsupported %s parm: %s "%(name, parms[0]))
                        tzoffsetfrom = self._parse_offset(value)
                    elif name == "TZOFFSETTO":
                        if parms:
                            raise ValueError("unsupported TZOFFSETTO parm: "+parms[0])
                        tzoffsetto = self._parse_offset(value)
                    elif name == "TZNAME":
                        if parms:
                            raise ValueError("unsupported TZNAME parm: "+parms[0])
                        tzname = value
                    elif name == "COMMENT":
                        pass
                    else:
                        raise ValueError("unsupported property: "+name)
                else:
                    if name == "TZID":
                        if parms:
                            raise ValueError("unsupported TZID parm: "+parms[0])
                        tzid = value
                    elif name in ("TZURL", "LAST-MODIFIED", "COMMENT"):
                        pass
                    else:
                        raise ValueError("unsupported property: "+name)
            elif name == "BEGIN" and value == "VTIMEZONE":
                tzid = None
                comps = []
                invtz = True

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self._s))

if sys.platform != "win32":
    TZFILES = ["/etc/localtime", "localtime"]
    TZPATHS = ["/usr/share/zoneinfo", "/usr/lib/zoneinfo", "/etc/zoneinfo"]
else:
    TZFILES = []
    TZPATHS = []

def gettz(name=None):
    tz = None
    if not name:
        try:
            name = os.environ["TZ"]
        except KeyError:
            pass
    if name is None or name == ":":
        for filepath in TZFILES:
            if not os.path.isabs(filepath):
                filename = filepath
                for path in TZPATHS:
                    filepath = os.path.join(path, filename)
                    if os.path.isfile(filepath):
                        break
                else:
                    continue
            if os.path.isfile(filepath):
                try:
                    tz = tzfile(filepath)
                    break
                except (IOError, OSError, ValueError):
                    pass
        else:
            tz = tzlocal()
    else:
        if name.startswith(":"):
            name = name[:-1]
        if os.path.isabs(name):
            if os.path.isfile(name):
                tz = tzfile(name)
            else:
                tz = None
        else:
            for path in TZPATHS:
                filepath = os.path.join(path, name)
                if not os.path.isfile(filepath):
                    filepath = filepath.replace(' ', '_')
                    if not os.path.isfile(filepath):
                        continue
                try:
                    tz = tzfile(filepath)
                    break
                except (IOError, OSError, ValueError):
                    pass
            else:
                tz = None
                if tzwin:
                    try:
                        tz = tzwin(name)
                    except OSError:
                        pass
                if not tz:
                    from dateutil.zoneinfo import gettz
                    tz = gettz(name)
                if not tz:
                    for c in name:
                        # name must have at least one offset to be a tzstr
                        if c in "0123456789":
                            try:
                                tz = tzstr(name)
                            except ValueError:
                                pass
                            break
                    else:
                        if name in ("GMT", "UTC"):
                            tz = tzutc()
                        elif name in time.tzname:
                            tz = tzlocal()
    return tz

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = tzwin
# This code was originally contributed by Jeffrey Harris.
import datetime
import struct
import winreg

__author__ = "Jeffrey Harris & Gustavo Niemeyer <gustavo@niemeyer.net>"

__all__ = ["tzwin", "tzwinlocal"]

ONEWEEK = datetime.timedelta(7)

TZKEYNAMENT = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones"
TZKEYNAME9X = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Time Zones"
TZLOCALKEYNAME = r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation"

def _settzkeyname():
    global TZKEYNAME
    handle = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    try:
        winreg.OpenKey(handle, TZKEYNAMENT).Close()
        TZKEYNAME = TZKEYNAMENT
    except WindowsError:
        TZKEYNAME = TZKEYNAME9X
    handle.Close()

_settzkeyname()

class tzwinbase(datetime.tzinfo):
    """tzinfo class based on win32's timezones available in the registry."""

    def utcoffset(self, dt):
        if self._isdst(dt):
            return datetime.timedelta(minutes=self._dstoffset)
        else:
            return datetime.timedelta(minutes=self._stdoffset)

    def dst(self, dt):
        if self._isdst(dt):
            minutes = self._dstoffset - self._stdoffset
            return datetime.timedelta(minutes=minutes)
        else:
            return datetime.timedelta(0)
        
    def tzname(self, dt):
        if self._isdst(dt):
            return self._dstname
        else:
            return self._stdname

    def list():
        """Return a list of all time zones known to the system."""
        handle = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        tzkey = winreg.OpenKey(handle, TZKEYNAME)
        result = [winreg.EnumKey(tzkey, i)
                  for i in range(winreg.QueryInfoKey(tzkey)[0])]
        tzkey.Close()
        handle.Close()
        return result
    list = staticmethod(list)

    def display(self):
        return self._display
    
    def _isdst(self, dt):
        dston = picknthweekday(dt.year, self._dstmonth, self._dstdayofweek,
                               self._dsthour, self._dstminute,
                               self._dstweeknumber)
        dstoff = picknthweekday(dt.year, self._stdmonth, self._stddayofweek,
                                self._stdhour, self._stdminute,
                                self._stdweeknumber)
        if dston < dstoff:
            return dston <= dt.replace(tzinfo=None) < dstoff
        else:
            return not dstoff <= dt.replace(tzinfo=None) < dston


class tzwin(tzwinbase):

    def __init__(self, name):
        self._name = name

        handle = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        tzkey = winreg.OpenKey(handle, "%s\%s" % (TZKEYNAME, name))
        keydict = valuestodict(tzkey)
        tzkey.Close()
        handle.Close()

        self._stdname = keydict["Std"].encode("iso-8859-1")
        self._dstname = keydict["Dlt"].encode("iso-8859-1")

        self._display = keydict["Display"]
        
        # See http://ww_winreg.jsiinc.com/SUBA/tip0300/rh0398.htm
        tup = struct.unpack("=3l16h", keydict["TZI"])
        self._stdoffset = -tup[0]-tup[1]         # Bias + StandardBias * -1
        self._dstoffset = self._stdoffset-tup[2] # + DaylightBias * -1
        
        (self._stdmonth,
         self._stddayofweek,  # Sunday = 0
         self._stdweeknumber, # Last = 5
         self._stdhour,
         self._stdminute) = tup[4:9]

        (self._dstmonth,
         self._dstdayofweek,  # Sunday = 0
         self._dstweeknumber, # Last = 5
         self._dsthour,
         self._dstminute) = tup[12:17]

    def __repr__(self):
        return "tzwin(%s)" % repr(self._name)

    def __reduce__(self):
        return (self.__class__, (self._name,))


class tzwinlocal(tzwinbase):
    
    def __init__(self):

        handle = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)

        tzlocalkey = winreg.OpenKey(handle, TZLOCALKEYNAME)
        keydict = valuestodict(tzlocalkey)
        tzlocalkey.Close()

        self._stdname = keydict["StandardName"].encode("iso-8859-1")
        self._dstname = keydict["DaylightName"].encode("iso-8859-1")

        try:
            tzkey = winreg.OpenKey(handle, "%s\%s"%(TZKEYNAME, self._stdname))
            _keydict = valuestodict(tzkey)
            self._display = _keydict["Display"]
            tzkey.Close()
        except OSError:
            self._display = None

        handle.Close()
        
        self._stdoffset = -keydict["Bias"]-keydict["StandardBias"]
        self._dstoffset = self._stdoffset-keydict["DaylightBias"]


        # See http://ww_winreg.jsiinc.com/SUBA/tip0300/rh0398.htm
        tup = struct.unpack("=8h", keydict["StandardStart"])

        (self._stdmonth,
         self._stddayofweek,  # Sunday = 0
         self._stdweeknumber, # Last = 5
         self._stdhour,
         self._stdminute) = tup[1:6]

        tup = struct.unpack("=8h", keydict["DaylightStart"])

        (self._dstmonth,
         self._dstdayofweek,  # Sunday = 0
         self._dstweeknumber, # Last = 5
         self._dsthour,
         self._dstminute) = tup[1:6]

    def __reduce__(self):
        return (self.__class__, ())

def picknthweekday(year, month, dayofweek, hour, minute, whichweek):
    """dayofweek == 0 means Sunday, whichweek 5 means last instance"""
    first = datetime.datetime(year, month, 1, hour, minute)
    weekdayone = first.replace(day=((dayofweek-first.isoweekday())%7+1))
    for n in range(whichweek):
        dt = weekdayone+(whichweek-n)*ONEWEEK
        if dt.month == month:
            return dt

def valuestodict(key):
    """Convert a registry key's values to a dictionary."""
    dict = {}
    size = winreg.QueryInfoKey(key)[1]
    for i in range(size):
        data = winreg.EnumValue(key, i)
        dict[data[0]] = data[1]
    return dict

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2013 Marcus Popp                               marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import logging
import collections

logger = logging.getLogger('')


def strip_quotes(string):
    string = string.strip()
    if string[0] in ['"', "'"]:  # check if string starts with ' or "
        if string[0] == string[-1]:  # and end with it
            if string.count(string[0]) == 2:  # if they are the only one
                string = string[1:-1]  # remove them
    return string


def parse(filename, config=None):
    valid_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
    valid_set = set(valid_chars)
    if config is None:
        config = collections.OrderedDict()
    item = config
    with open(filename, 'r') as f:
        linenu = 0
        parent = collections.OrderedDict()
        for raw in f.readlines():
            linenu += 1
            line = raw.lstrip('\ufeff')  # remove BOM
            line = line.partition('#')[0].strip()
            if line is '':
                continue
            if line[0] == '[':  # item
                brackets = 0
                level = 0
                closing = False
                for index in range(len(line)):
                    if line[index] == '[' and not closing:
                        brackets += 1
                        level += 1
                    elif line[index] == ']':
                        closing = True
                        brackets -= 1
                    else:
                        closing = True
                        if line[index] not in valid_chars + "'":
                            logger.error("Problem parsing '{}' invalid character in line {}: {}. Valid characters are: {}".format(filename, linenu, line, valid_chars))
                            return config
                if brackets != 0:
                    logger.error("Problem parsing '{}' unbalanced brackets in line {}: {}".format(filename, linenu, line))
                    return config
                name = line.strip("[]")
                name = strip_quotes(name)
                if level == 1:
                    if name not in config:
                        config[name] = collections.OrderedDict()
                    item = config[name]
                    parents = collections.OrderedDict()
                    parents[level] = item
                else:
                    if level - 1 not in parents:
                        logger.error("Problem parsing '{}' no parent item defined for item in line {}: {}".format(filename, linenu, line))
                        return config
                    parent = parents[level - 1]
                    if name not in parent:
                        parent[name] = collections.OrderedDict()
                    item = parent[name]
                    parents[level] = item

            else:  # attribute
                attr, __, value = line.partition('=')
                if not value:
                    continue
                attr = attr.strip()
                if not set(attr).issubset(valid_set):
                    logger.error("Problem parsing '{}' invalid character in line {}: {}. Valid characters are: {}".format(filename, linenu, attr, valid_chars))
                    continue
                if '|' in value:
                    item[attr] = [strip_quotes(x) for x in value.split('|')]
                else:
                    item[attr] = strip_quotes(value)
        return config


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    conf = parse('dev.conf')
    print(conf)

########NEW FILE########
__FILENAME__ = connection
#!/usr/bin/env python3
#########################################################################
#  Copyright 2013 Marcus Popp                              marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import logging
import socket
import collections
import threading
import select
import time

logger = logging.getLogger('')


class Base():

    _poller = None
    _family = {'UDP': socket.AF_INET, 'UDP6': socket.AF_INET6, 'TCP': socket.AF_INET, 'TCP6': socket.AF_INET6}
    _type = {'UDP': socket.SOCK_DGRAM, 'UDP6': socket.SOCK_DGRAM, 'TCP': socket.SOCK_STREAM, 'TCP6': socket.SOCK_STREAM}
    _monitor = []

    def __init__(self, monitor=False):
        self._name = self.__class__.__name__
        if monitor:
            self._monitor.append(self)

    def _create_socket(self, flags=None):
        family, type, proto, canonname, sockaddr = socket.getaddrinfo(self._host, self._port, family=self._family[self._proto], type=self._type[self._proto])[0]
        self.socket = socket.socket(family, type, proto)
        return sockaddr


class Connections(Base):

    _connections = {}
    _servers = {}
    _ro = select.EPOLLIN | select.EPOLLHUP | select.EPOLLERR
    _rw = _ro | select.EPOLLOUT

    def __init__(self):
        Base.__init__(self)
        Base._poller = self
        self._epoll = select.epoll()

    def register_server(self, fileno, obj):
        self._servers[fileno] = obj
        self._connections[fileno] = obj
        self._epoll.register(fileno, self._ro)

    def register_connection(self, fileno, obj):
        self._connections[fileno] = obj
        self._epoll.register(fileno, self._ro)

    def unregister_connection(self, fileno):
        try:
            self._epoll.unregister(fileno)
            del(self._connections[fileno])
            del(self._servers[fileno])
        except:
            pass

    def monitor(self, obj):
        self._monitor.append(obj)

    def check(self):
        for obj in self._monitor:
            if not obj.connected:
                obj.connect()

    def trigger(self, fileno):
        if self._connections[fileno].outbuffer:
            self._epoll.modify(fileno, self._rw)

    def poll(self):
        time.sleep(0.0000000001)  # give epoll.modify a chance
        if not self._connections:
            time.sleep(1)
            return
        for fileno in self._connections:
            if fileno not in self._servers:
                if self._connections[fileno].outbuffer:
                    self._epoll.modify(fileno, self._rw)
                else:
                    self._epoll.modify(fileno, self._ro)
        for fileno, event in self._epoll.poll(timeout=1):
            if fileno in self._servers:
                server = self._servers[fileno]
                server.handle_connection()
            else:
                if event & select.EPOLLIN:
                    try:
                        con = self._connections[fileno]
                        con._in()
                    except Exception as e:  # noqa
#                       logger.exception("{}: {}".format(self._name, e))
                        con.close()
                        continue
                if event & select.EPOLLOUT:
                    try:
                        con = self._connections[fileno]
                        con._out()
                    except Exception as e:  # noqa
#                       logger.exception("{}: {}".format(self._name, e))
                        con.close()
                        continue
                if event & (select.EPOLLHUP | select.EPOLLERR):
                    try:
                        con = self._connections[fileno]
                        con.close()
                        continue
                    except:
                        pass

    def close(self):
        for fileno in self._connections:
            try:
                self._connections[fileno].close()
            except:
                pass


class Server(Base):

    def __init__(self, host, port, proto='TCP'):
        Base.__init__(self, monitor=True)
        self._host = host
        self._port = port
        self._proto = proto
        self.address = "{}:{}".format(host, port)
        self.connected = False

    def connect(self):
        try:
            sockaddr = self._create_socket()
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(sockaddr)
            if self._proto.startswith('TCP'):
                self.socket.listen(5)
            self.socket.setblocking(0)
        except Exception as e:
            logger.error("{}: problem binding {} ({}): {}".format(self._name, self.address, self._proto, e))
            self.close()
        else:
            self.connected = True
            logger.debug("{}: binding to {} ({})".format(self._name, self.address, self._proto))
            self._poller.register_server(self.socket.fileno(), self)

    def close(self):
        self.connected = False
        try:
            self._poller.unregister_connection(self.socket.fileno())
        except:
            pass
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            self.socket.close()
        except:
            pass
        try:
            del(self.socket)
        except:
            pass

    def accept(self):
        try:
            sock, addr = self.socket.accept()
            sock.setblocking(0)
            addr = "{}:{}".format(addr[0], addr[1])
            logger.debug("{}: incoming connection from {} to {}".format(self._name, addr, self.address))
            return sock, addr
        except:
            return None, None

    def handle_connection(self):
        pass


class Stream(Base):

    def __init__(self, sock=None, address=None, monitor=False):
        Base.__init__(self, monitor=monitor)
        self.connected = False
        self.address = address
        self.inbuffer = bytearray()
        self.outbuffer = collections.deque()
        self._frame_size_in = 4096
        self._frame_size_out = 4096
        self.terminator = b'\r\n'
        self._balance_open = False
        self._balance_close = False
        self._close_after_send = False
        if sock is not None:
            self.socket = sock
            self._connected()

    def _connected(self):
            self._poller.register_connection(self.socket.fileno(), self)
            self.connected = True
            self.handle_connect()

    def _in(self):
        max_size = self._frame_size_in
        try:
            data = self.socket.recv(max_size)
        except Exception as e:  # noqa
#           logger.warning("{}: {}".format(self._name, e))
            self.close()
            return
        if data == b'':
            self.close()
            return
        self.inbuffer.extend(data)
        while True:
            terminator = self.terminator
            buffer_len = len(self.inbuffer)
            if not terminator:
                if not self._balance_open:
                    break
                index = self._is_balanced()
                if index:
                    data = self.inbuffer[:index]
                    self.inbuffer = self.inbuffer[index:]
                    self.found_balance(data)
                else:
                    break
            elif isinstance(terminator, int):
                if buffer_len < terminator:
                    break
                else:
                    data = self.inbuffer[:terminator]
                    self.inbuffer = self.inbuffer[terminator:]
                    self.terminator = 0
                    self.found_terminator(data)
            else:
                if terminator not in self.inbuffer:
                    break
                index = self.inbuffer.find(terminator)
                data = self.inbuffer[:index]
                cut = index + len(terminator)
                self.inbuffer = self.inbuffer[cut:]
                self.found_terminator(data)

    def _is_balanced(self):
        stack = []
        for index, char in enumerate(self.inbuffer):
            if char == self._balance_open:
                stack.append(char)
            elif char == self._balance_close:
                stack.append(char)
                if stack.count(self._balance_open) < stack.count(self._balance_close):
                    logger.warning("{}: unbalanced input!".format(self._name))
                    logger.close()
                    return False
                if stack.count(self._balance_open) == stack.count(self._balance_close):
                    return index + 1
        return False

    def _out(self):
        while self.outbuffer and self.connected:
            frame = self.outbuffer.pop()
            if not frame:
                if frame is None:
                    self.close()
                    return
                continue  # ignore empty frames
            try:
                sent = self.socket.send(frame)
            except socket.error:
#               logger.exception("{}: {}".format(self._name, e))
                self.outbuffer.append(frame)
                return
            else:
                if sent < len(frame):
                    self.outbuffer.append(frame[sent:])
        if self._close_after_send:
            self.close()

    def balance(self, bopen, bclose):
        self._balance_open = ord(bopen)
        self._balance_close = ord(bclose)

    def close(self):
        if self.connected:
            logger.debug("{}: closing socket {}".format(self._name, self.address))
        self.connected = False
        try:
            self._poller.unregister_connection(self.socket.fileno())
        except:
            pass
        try:
            self.handle_close()
        except:
            pass
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            self.socket.close()
        except:
            pass
        try:
            del(self.socket)
        except:
            pass

    def discard_buffers(self):
        self.inbuffer = bytearray()
        self.outbuffer.clear()

    def found_terminator(self, data):
        pass

    def found_balance(self, data):
        pass

    def handle_close(self):
        pass

    def handle_connect(self):
        pass

    def send(self, data, close=False):
        self._close_after_send = close
        if not self.connected:
            return False
        frame_size = self._frame_size_out
        if len(data) > frame_size:
            for i in range(0, len(data), frame_size):
                self.outbuffer.appendleft(data[i:i + frame_size])
        else:
            self.outbuffer.appendleft(data)
        self._poller.trigger(self.socket.fileno())
        return True


class Client(Stream):

    def __init__(self, host, port, proto='TCP', monitor=False):
        Stream.__init__(self, monitor=monitor)
        self._host = host
        self._port = port
        self._proto = proto
        self.address = "{}:{}".format(host, port)
        self._connection_attempts = 0
        self._connection_errorlog = 60
        self._connection_lock = threading.Lock()

    def connect(self):
        self._connection_lock.acquire()
        if self.connected:
            self._connection_lock.release()
            return
        try:
            sockaddr = self._create_socket()
            self.socket.settimeout(2)
            self.socket.connect(sockaddr)
            self.socket.setblocking(0)
#           self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception as e:
            self._connection_attempts -= 1
            if self._connection_attempts <= 0:
                logger.error("{}: could not connect to {} ({}): {}".format(self._name, self.address, self._proto, e))
                self._connection_attempts = self._connection_errorlog
            self.close()
        else:
            logger.debug("{}: connected to {}".format(self._name, self.address))
            self._connected()
        finally:
            self._connection_lock.release()

########NEW FILE########
__FILENAME__ = daemon
#!/usr/bin/env python3
#########################################################################
#  Copyright 2013 Marcus Popp                              marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import logging
import signal
import time
import os

logger = logging.getLogger('')


def daemonize():
    pid = os.fork()  # fork first child
    if pid == 0:
        os.setsid()
        pid = os.fork()  # fork second child
        if pid == 0:
            os.chdir('/')
        else:
            time.sleep(0.1)
            os._exit(0)  # exit parent
    else:
        time.sleep(0.1)
        os._exit(0)  # exit parent
    # close files
    for fd in range(0, 1024):
        try:
            os.close(fd)
        except OSError:
            pass
    # redirect I/O
    os.open(os.devnull, os.O_RDWR)  # input
    os.dup2(0, 1)  # output
    os.dup2(0, 2)  # error


def get_pid(filename):
    cpid = str(os.getpid())
    for pid in os.listdir('/proc'):
        if pid.isdigit() and pid != cpid:
            try:
                with open('/proc/{}/cmdline'.format(pid), 'r') as f:
                    cmdline = f.readline()
                    if filename in cmdline:
                        if cmdline.startswith('python'):
                            return int(pid)
            except:
                pass
    return 0


def kill(filename, wait=5):
    pid = get_pid(filename)
    delay = 0.25
    waited = 0
    if pid:
        os.kill(pid, signal.SIGTERM)
        while waited < wait:
            try:
                os.kill(pid, 0)
            except OSError:
                os._exit(0)
            waited += delay
            time.sleep(0.25)
        try:
            print("Killing {}".format(os.path.basename(filename)))
            os.kill(pid, signal.SIGKILL)
        except OSError:
            os._exit(0)

########NEW FILE########
__FILENAME__ = init

# lib/env/init.py

sh.env.core.version(sh.version)
sh.env.core.start(sh.now())

namefile = "/proc/sys/kernel/hostname"
with open(namefile, 'r') as f:
    hostname = f.read().strip()
sh.env.system.name(hostname)

# system start
with open("/proc/uptime", 'r') as f:
    uptime = f.read()
uptime = int(float(uptime.split()[0]))
start = sh.now() - datetime.timedelta(seconds=uptime)
sh.env.system.start(start)

########NEW FILE########
__FILENAME__ = location

# lib/env/location.py

if sh.sun:
    sh.env.location.sunrise(sh.sun.rise().astimezone(sh.tzinfo()))
    sh.env.location.sunset(sh.sun.set().astimezone(sh.tzinfo()))

    sh.env.location.moonrise(sh.moon.rise().astimezone(sh.tzinfo()))
    sh.env.location.moonset(sh.moon.set().astimezone(sh.tzinfo()))
    sh.env.location.moonphase(sh.moon.phase())

    # setting day and night
    day = sh.sun.rise(-6).day != sh.sun.set(-6).day
    sh.env.location.day(day)
    sh.env.location.night(not day)

########NEW FILE########
__FILENAME__ = stat

# lib/env/statistic.py

# Garbage
gc.collect()
if gc.garbage != []:
    sh.env.core.garbage(len(gc.garbage))
    logger.warning("Garbage: {} objects".format(len(gc.garbage)))
    logger.info("Garbage: {}".format(gc.garbage))
    del gc.garbage[:]

# Threads
sh.env.core.threads(threading.activeCount())

# Memory
statusfile = "/proc/{0}/status".format(os.getpid())
units = {'kB': 1024, 'mB': 1048576}
with open(statusfile, 'r') as f:
    data = f.read()
status = {}
for line in data.splitlines():
    key, sep, value = line.partition(':')
    status[key] = value.strip()
size, unit = status['VmRSS'].split(' ')
mem = round(int(size) * units[unit])
sh.env.core.memory(mem)

# Load
l1, l5, l15 = os.getloadavg()
sh.env.system.load(round(l5, 2))

if sh.moon:
    sh.env.location.moonlight(sh.moon.light())

########NEW FILE########
__FILENAME__ = item
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2012-2013 Marcus Popp                          marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import datetime
import logging
import os
import pickle
import threading

logger = logging.getLogger('')


#####################################################################
# Cast Methods
#####################################################################

def _cast_str(value):
    if isinstance(value, str):
        return value
    else:
        raise ValueError


def _cast_list(value):
    if isinstance(value, list):
        return value
    else:
        raise ValueError


def _cast_dict(value):
    if isinstance(value, dict):
        return value
    else:
        raise ValueError


def _cast_foo(value):
    return value


def _cast_bool(value):
    if type(value) in [bool, int, float]:
        if value in [False, 0]:
            return False
        elif value in [True, 1]:
            return True
        else:
            raise ValueError
    elif type(value) in [str, str]:
        if value.lower() in ['0', 'false', 'no', 'off']:
            return False
        elif value.lower() in ['1', 'true', 'yes', 'on']:
            return True
        else:
            raise ValueError
    else:
        raise TypeError


def _cast_scene(value):
    return int(value)


def _cast_num(value):
    if isinstance(value, float):
        return value
    try:
        return int(value)
    except:
        pass
    try:
        return float(value)
    except:
        pass
    raise ValueError


#####################################################################
# Cache Methods
#####################################################################
def _cache_read(filename, tz):
    ts = os.path.getmtime(filename)
    dt = datetime.datetime.fromtimestamp(ts, tz)
    value = None
    with open(filename, 'rb') as f:
        value = pickle.load(f)
    return (dt, value)


def _cache_write(filename, value):
    try:
        with open(filename, 'wb') as f:
            pickle.dump(value, f)
    except IOError:
        logger.warning("Could not write to {}".format(filename))


#####################################################################
# Fade Method
#####################################################################
def _fadejob(item, dest, step, delta):
    if item._fading:
        return
    else:
        item._fading = True
    if item._value < dest:
        while (item._value + step) < dest and item._fading:
            item(item._value + step, 'fader')
            item._lock.acquire()
            item._lock.wait(delta)
            item._lock.release()
    else:
        while (item._value - step) > dest and item._fading:
            item(item._value - step, 'fader')
            item._lock.acquire()
            item._lock.wait(delta)
            item._lock.release()
    if item._fading:
        item._fading = False
        item(dest, 'Fader')


#####################################################################
# Item Class
#####################################################################


class Item():

    def __init__(self, smarthome, parent, path, config):
        self._autotimer = False
        self._cache = False
        self.cast = _cast_bool
        self.__changed_by = 'Init:None'
        self.__children = []
        self.conf = {}
        self._crontab = None
        self._cycle = None
        self._enforce_updates = False
        self._eval = None
        self._eval_trigger = False
        self._fading = False
        self._items_to_trigger = []
        self.__last_change = smarthome.now()
        self.__last_update = smarthome.now()
        self._lock = threading.Condition()
        self.__logics_to_trigger = []
        self._name = path
        self.__prev_change = smarthome.now()
        self.__methods_to_trigger = []
        self.__parent = parent
        self._path = path
        self._sh = smarthome
        self._threshold = False
        self._type = None
        self._value = None
        if hasattr(smarthome, '_item_change_log'):
            self._change_logger = logger.info
        else:
            self._change_logger = logger.debug
        #############################################################
        # Item Attributes
        #############################################################
        for attr, value in config.items():
            if not isinstance(value, dict):
                if attr in ['cycle', 'eval', 'name', 'type', 'value']:
                    setattr(self, '_' + attr, value)
                elif attr in ['cache', 'enforce_updates']:  # cast to bool
                    try:
                        setattr(self, '_' + attr, _cast_bool(value))
                    except:
                        logger.warning("Item '{0}': problem parsing '{1}'.".format(self._path, attr))
                        continue
                elif attr in ['crontab', 'eval_trigger']:  # cast to list
                    if isinstance(value, str):
                        value = [value, ]
                    setattr(self, '_' + attr, value)
                elif attr == 'autotimer':
                    time, __, value = value.partition('=')
                    if value is not None:
                        self._autotimer = time, value
                elif attr == 'threshold':
                    low, __, high = value.rpartition(':')
                    if not low:
                        low = high
                    self._threshold = True
                    self.__th_crossed = False
                    self.__th_low = float(low)
                    self.__th_high = float(high)
                    logger.debug("Item {}: set threshold => low: {} high: {}".format(self._path, self.__th_low, self.__th_high))
                else:
                    self.conf[attr] = value
        #############################################################
        # Child Items
        #############################################################
        for attr, value in config.items():
            if isinstance(value, dict):
                child_path = self._path + '.' + attr
                try:
                    child = Item(smarthome, self, child_path, value)
                except Exception as e:
                    logger.error("Item {}: problem creating: {}".format(child_path, e))
                else:
                    vars(self)[attr] = child
                    smarthome.add_item(child_path, child)
                    self.__children.append(child)
        #############################################################
        # Cache
        #############################################################
        if self._cache:
            self._cache = self._sh._cache_dir + self._path
            try:
                self.__last_change, self._value = _cache_read(self._cache, self._sh._tzinfo)
                self.__last_update = self.__last_change
                self.__changed_by = 'Cache:None'
            except Exception as e:
                logger.warning("Item {}: problem reading cache: {}".format(self._path, e))
        #############################################################
        # Type
        #############################################################
        __defaults = {'num': 0, 'str': '', 'bool': False, 'list': [], 'dict': {}, 'foo': None, 'scene': 0}
        if self._type is None:
            logger.debug("Item {}: no type specified.".format(self._path))
            return
        if self._type not in __defaults:
            logger.error("Item {}: type '{}' unknown. Please use one of: {}.".format(self._path, self._type, ', '.join(list(__defaults.keys()))))
            raise AttributeError
        self.cast = globals()['_cast_' + self._type]
        #############################################################
        # Value
        #############################################################
        if self._value is None:
            self._value = __defaults[self._type]
        try:
            self._value = self.cast(self._value)
        except:
            logger.error("Item {}: value {} does not match type {}.".format(self._path, self._value, self._type))
            raise
        self.__prev_value = self._value
        #############################################################
        # Crontab/Cycle
        #############################################################
        if self._crontab is not None or self._cycle is not None:
            self._sh.scheduler.add(self._path, self, cron=self._crontab, cycle=self._cycle)
        #############################################################
        # Plugins
        #############################################################
        for plugin in self._sh.return_plugins():
            if hasattr(plugin, 'parse_item'):
                update = plugin.parse_item(self)
                if update:
                    self.add_method_trigger(update)

    def __call__(self, value=None, caller='Logic', source=None, dest=None):
        if value is None or self._type is None:
            return self._value
        if self._eval:
            args = {'value': value, 'caller': caller, 'source': source, 'dest': dest}
            self._sh.trigger(name=self._path + '-eval', obj=self.__run_eval, value=args, by=caller, source=source, dest=dest)
        else:
            self.__update(value, caller, source, dest)

    def __iter__(self):
        for child in self.__children:
            yield child

    def __setitem__(self, item, value):
        vars(self)[item] = value

    def __getitem__(self, item):
        return vars(self)[item]

    def __bool__(self):
        return self._value

    def __str__(self):
        return self._name

    def __repr__(self):
        return "Item: {}".format(self._path)

    def _init_prerun(self):
        if self._eval_trigger:
            _items = []
            for trigger in self._eval_trigger:
                _items.extend(self._sh.match_items(trigger))
            for item in _items:
                if item != self:  # prevent loop
                        item._items_to_trigger.append(self)
            if self._eval:
                items = ['sh.' + x.id() + '()' for x in _items]
                if self._eval == 'and':
                    self._eval = ' and '.join(items)
                elif self._eval == 'or':
                    self._eval = ' or '.join(items)
                elif self._eval == 'sum':
                    self._eval = ' + '.join(items)
                elif self._eval == 'avg':
                    self._eval = '({0})/{1}'.format(' + '.join(items), len(items))

    def _init_run(self):
        if self._eval_trigger:
            if self._eval:
                self._sh.trigger(name=self._path, obj=self.__run_eval, by='Init', value={'value': self._value, 'caller': 'Init'})

    def __run_eval(self, value=None, caller='Eval', source=None, dest=None):
        if self._eval:
            sh = self._sh  # noqa
            try:
                value = eval(self._eval)
            except Exception as e:
                logger.warning("Item {}: problem evaluating {}: {}".format(self._path, self._eval, e))
            else:
                if value is None:
                    logger.info("Item {}: evaluating {} returns None".format(self._path, self._eval))
                else:
                    self.__update(value, caller, source, dest)

    def __trigger_logics(self):
        for logic in self.__logics_to_trigger:
            logic.trigger('Item', self._path, self._value)

    def __update(self, value, caller='Logic', source=None, dest=None):
        try:
            value = self.cast(value)
        except:
            try:
                logger.warning("Item {}: value {} does not match type {}. Via {} {}".format(self._path, value, self._type, caller, source))
            except:
                pass
            return
        self._lock.acquire()
        _changed = False
        if value != self._value:
            _changed = True
            self.__prev_value = self._value
            self._value = value
            self.__prev_change = self.__last_change
            self.__last_change = self._sh.now()
            self.__changed_by = "{0}:{1}".format(caller, source)
            if caller != "fader":
                self._fading = False
                self._lock.notify_all()
                self._change_logger("Item {} = {} via {} {} {}".format(self._path, value, caller, source, dest))
        self._lock.release()
        if _changed or self._enforce_updates:
            self.__last_update = self._sh.now()
            for method in self.__methods_to_trigger:
                try:
                    method(self, caller, source, dest)
                except Exception as e:
                    logger.exception("Item {}: problem running {}: {}".format(self._path, method, e))
            if self._threshold and self.__logics_to_trigger:
                if self.__th_crossed and self._value <= self.__th_low:  # cross lower bound
                    self.__th_crossed = False
                    self.__trigger_logics()
                elif not self.__th_crossed and self._value >= self.__th_high:  # cross upper bound
                    self.__th_crossed = True
                    self.__trigger_logics()
            elif self.__logics_to_trigger:
                self.__trigger_logics()
            for item in self._items_to_trigger:
                args = {'value': value, 'source': self._path}
                self._sh.trigger(name=item.id(), obj=item.__run_eval, value=args, by=caller, source=source, dest=dest)
        if _changed and self._cache and not self._fading:
            try:
                _cache_write(self._cache, value)
            except Exception as e:
                logger.warning("Item: {}: could update cache {}".format(self._path, e))
        if self._autotimer and caller != 'Autotimer' and not self._fading:
            _time, _value = self._autotimer
            self.timer(_time, _value, True)

    def add_logic_trigger(self, logic):
        self.__logics_to_trigger.append(logic)

    def add_method_trigger(self, method):
        self.__methods_to_trigger.append(method)

    def age(self):
        delta = self._sh.now() - self.__last_change
        return delta.total_seconds()

    def autotimer(self, time=None, value=None):
        if time is not None and value is not None:
            self._autotimer = time, value
        else:
            self._autotimer = False

    def changed_by(self):
        return self.__changed_by

    def fade(self, dest, step=1, delta=1):
        dest = float(dest)
        self._sh.trigger(self._path, _fadejob, value={'item': self, 'dest': dest, 'step': step, 'delta': delta})

    def id(self):
        return self._path

    def last_change(self):
        return self.__last_change

    def last_update(self):
        return self.__last_update

    def prev_age(self):
        delta = self.__last_change - self.__prev_change
        return delta.total_seconds()

    def prev_change(self):
        return self.__prev_change

    def prev_value(self):
        return self.__prev_value

    def return_children(self):
        for child in self.__children:
            yield child

    def return_parent(self):
        return self.__parent

    def set(self, value, caller='Logic', source=None, dest=None):
        try:
            value = self.cast(value)
        except:
            try:
                logger.warning("Item {}: value {} does not match type {}. Via {} {}".format(self._path, value, self._type, caller, source))
            except:
                pass
            return
        self._lock.acquire()
        self._value = value
        self.__prev_change = self.__last_change
        self.__last_change = self._sh.now()
        self.__changed_by = "{0}:{1}".format(caller, None)
        self._lock.release()
        self._change_logger("Item {} = {} via {} {} {}".format(self._path, value, caller, source, dest))

    def timer(self, time, value, auto=False):
        try:
            if isinstance(time, str):
                time = time.strip()
                if time.endswith('m'):
                    time = int(time.strip('m')) * 60
                else:
                    time = int(time)
            if isinstance(value, str):
                value = value.strip()
            if auto:
                caller = 'Autotimer'
                self._autotimer = time, value
            else:
                caller = 'Timer'
            next = self._sh.now() + datetime.timedelta(seconds=time)
        except Exception as e:
            logger.warning("Item {}: timer ({}, {}) problem: {}".format(self._path, time, value, e))
        else:
            self._sh.scheduler.add(self.id() + '-Timer', self.__call__, value={'value': value, 'caller': caller}, next=next)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    i = Item('sh', 'parent', 'path1', {'type': 'str', 'child1': {'type': 'bool'}, 'value': 'tqwer'})
    i = Item('sh', 'parent', 'path', {'type': 'str', 'value': 'tqwer'})
    i('test2')

########NEW FILE########
__FILENAME__ = log
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2012-2013 Marcus Popp                          marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import collections
import time


class Log(collections.deque):

    def __init__(self, smarthome, name, mapping, maxlen=50):
        collections.deque.__init__(self, maxlen=maxlen)
        self.mapping = mapping
        self.update_hooks = []
        self._sh = smarthome
        self._name = name
        smarthome.add_log(name, self)

    def add(self, entry):
        self.appendleft(entry)
        for listener in self._sh.return_event_listeners('log'):
            listener('log', {'name': self._name, 'log': [dict(zip(self.mapping, entry))]})

    def last(self, number):
        return(list(self)[-number:])

    def export(self, number):
        return [dict(zip(self.mapping, x)) for x in list(self)[:number]]

    def clean(self, dt):
        while True:
            try:
                entry = self.pop()
            except Exception:
                return
            if entry[0] > dt:
                self.append(entry)
                return

########NEW FILE########
__FILENAME__ = logic
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2011-2013 Marcus Popp                          marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py.  If not, see <http://www.gnu.org/licenses/>.
##########################################################################

import logging
import os

import lib.config

logger = logging.getLogger('')


class Logics():

    def __init__(self, smarthome, userlogicconf, envlogicconf):
        logger.info('Start Logics')
        self._sh = smarthome
        self._workers = []
        self._logics = {}
        self._bytecode = {}
        self.alive = True
        _config = {}
        _config.update(self._read_logics(envlogicconf, smarthome._env_dir))
        _config.update(self._read_logics(userlogicconf, smarthome._logic_dir))

        for name in _config:
            logger.debug("Logic: {}".format(name))
            logic = Logic(self._sh, name, _config[name])
            if hasattr(logic, 'bytecode'):
                self._logics[name] = logic
                self._sh.scheduler.add(name, logic, logic.prio, logic.crontab, logic.cycle)
            else:
                continue
            # plugin hook
            for plugin in self._sh._plugins:
                if hasattr(plugin, 'parse_logic'):
                    plugin.parse_logic(logic)
            # item hook
            if hasattr(logic, 'watch_item'):
                if isinstance(logic.watch_item, str):
                    logic.watch_item = [logic.watch_item]
                for entry in logic.watch_item:
                    for item in self._sh.match_items(entry):
                        item.add_logic_trigger(logic)

    def _read_logics(self, filename, directory):
        logger.debug("Reading Logics from {}".format(filename))
        try:
            config = lib.config.parse(filename)
            for name in config:
                if 'filename' in config[name]:
                    config[name]['filename'] = directory + config[name]['filename']
        except Exception as e:
            logger.critical(e)
            config = {}
        return config

    def __iter__(self):
        for logic in self._logics:
            yield logic

    def __getitem__(self, name):
        if name in self._logics:
            return self._logics[name]


class Logic():

    def __init__(self, smarthome, name, attributes):
        self._sh = smarthome
        self.name = name
        self.crontab = None
        self.cycle = None
        self.prio = 3
        self.last = None
        self.conf = attributes
        for attribute in attributes:
            vars(self)[attribute] = attributes[attribute]
        self.generate_bytecode()
        self.prio = int(self.prio)

    def id(self):
        return self.name

    def __str__(self):
        return self.name

    def __call__(self, caller='Logic', source=None, value=None, dest=None, dt=None):
        self._sh.scheduler.trigger(self.name, self, prio=self.prio, by=caller, source=source, dest=dest, value=value, dt=dt)

    def trigger(self, by='Logic', source=None, value=None, dest=None, dt=None):
        self._sh.scheduler.trigger(self.name, self, prio=self.prio, by=by, source=source, dest=dest, value=value, dt=dt)

    def generate_bytecode(self):
        if hasattr(self, 'filename'):
            if not os.access(self.filename, os.R_OK):
                logger.warning("{}: Could not access logic file ({}) => ignoring.".format(self.name, self.filename))
                return
            try:
                code = open(self.filename).read()
                code = code.lstrip('\ufeff')  # remove BOM
                self.bytecode = compile(code, self.filename, 'exec')
            except Exception as e:
                logger.exception("Exception: {}".format(e))
        else:
            logger.warning("{}: No filename specified => ignoring.".format(self.name))

########NEW FILE########
__FILENAME__ = orb
#!/usr/bin/env python3
#
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2011-2013 Marcus Popp                          marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py.  If not, see <http://www.gnu.org/licenses/>.
##########################################################################

import logging
import datetime

logger = logging.getLogger('')

try:
    import ephem
except ImportError as e:
    ephem = None  # noqa

import dateutil.relativedelta
from dateutil.tz import tzutc


class Orb():

    def __init__(self, orb, lon, lat, elev=False):
        if ephem is None:
            logger.warning("Could not find/use ephem!")
            return
        self._obs = ephem.Observer()
        self._obs.long = str(lon)
        self._obs.lat = str(lat)
        if elev:
            self._obs.elevation = int(elev)
        if orb == 'sun':
            self._orb = ephem.Sun()
        elif orb == 'moon':
            self._orb = ephem.Moon()
            self.phase = self._phase
            self.light = self._light

    def rise(self, doff=0, moff=0, center=True, dt=None):
        # workaround if rise is 0.001 seconds in the past
        if dt is not None:
            self._obs.date = dt - dt.utcoffset()
        else:
            self._obs.date = datetime.datetime.utcnow() - dateutil.relativedelta.relativedelta(minutes=moff) + dateutil.relativedelta.relativedelta(seconds=2)
        self._obs.horizon = str(doff)
        if doff != 0:
            next_rising = self._obs.next_rising(self._orb, use_center=center).datetime()
        else:
            next_rising = self._obs.next_rising(self._orb).datetime()
        next_rising = next_rising + dateutil.relativedelta.relativedelta(minutes=moff)
        return next_rising.replace(tzinfo=tzutc())

    def set(self, doff=0, moff=0, center=True, dt=None):
        # workaround if set is 0.001 seconds in the past
        if dt is not None:
            self._obs.date = dt - dt.utcoffset()
        else:
            self._obs.date = datetime.datetime.utcnow() - dateutil.relativedelta.relativedelta(minutes=moff) + dateutil.relativedelta.relativedelta(seconds=2)
        self._obs.horizon = str(doff)
        if doff != 0:
            next_setting = self._obs.next_setting(self._orb, use_center=center).datetime()
        else:
            next_setting = self._obs.next_setting(self._orb).datetime()
        next_setting = next_setting + dateutil.relativedelta.relativedelta(minutes=moff)
        return next_setting.replace(tzinfo=tzutc())

    def pos(self, offset=None):  # offset in minutes
        date = datetime.datetime.utcnow()
        if offset:
            date += dateutil.relativedelta.relativedelta(minutes=offset)
        self._obs.date = date
        self._orb.compute(self._obs)
        return (self._orb.az, self._orb.alt)

    def _light(self, offset=None):  # offset in minutes
        date = datetime.datetime.utcnow()
        if offset:
            date += dateutil.relativedelta.relativedelta(minutes=offset)
        self._obs.date = date
        self._orb.compute(self._obs)
        return int(round(self._orb.moon_phase * 100))

    def _phase(self, offset=None):  # offset in minutes
        date = datetime.datetime.utcnow()
        cycle = 29.530588861
        if offset:
            date += dateutil.relativedelta.relativedelta(minutes=offset)
        self._obs.date = date
        self._orb.compute(self._obs)
        last = ephem.previous_new_moon(self._obs.date)
        frac = (self._obs.date - last) / cycle
        return int(round(frac * 8))

########NEW FILE########
__FILENAME__ = plugin
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2011-2013 Marcus Popp                          marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py.  If not, see <http://www.gnu.org/licenses/>.
##########################################################################

import logging
import threading

import lib.config

logger = logging.getLogger('')


class Plugins():
    _plugins = []
    _threads = []

    def __init__(self, smarthome, configfile):
        try:
            _conf = lib.config.parse(configfile)
        except IOError as e:
            logger.critical(e)
            return

        for plugin in _conf:
            args = ''
            logger.debug("Plugin: {0}".format(plugin))
            for arg in _conf[plugin]:
                if arg != 'class_name' and arg != 'class_path':
                    value = _conf[plugin][arg]
                    if isinstance(value, str):
                        value = "'{0}'".format(value)
                    args = args + ", {0}={1}".format(arg, value)
            classname = _conf[plugin]['class_name']
            classpath = _conf[plugin]['class_path']
            try:
                plugin_thread = Plugin(smarthome, plugin, classname, classpath, args)
                self._threads.append(plugin_thread)
                self._plugins.append(plugin_thread.plugin)
            except Exception as e:
                logger.exception("Plugin {0} exception: {1}".format(plugin, e))
        del(_conf)  # clean up

    def __iter__(self):
        for plugin in self._plugins:
            yield plugin

    def start(self):
        logger.info('Start Plugins')
        for plugin in self._threads:
            plugin.start()

    def stop(self):
        logger.info('Stop Plugins')
        for plugin in self._threads:
            plugin.stop()


class Plugin(threading.Thread):

    def __init__(self, smarthome, name, classname, classpath, args):
        threading.Thread.__init__(self, name=name)
        exec("import {0}".format(classpath))
        exec("self.plugin = {0}.{1}(smarthome{2})".format(classpath, classname, args))
        setattr(smarthome, self.name, self.plugin)

    def run(self):
        self.plugin.run()

    def stop(self):
        self.plugin.stop()

########NEW FILE########
__FILENAME__ = scene
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2013-2013 Marcus Popp                          marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import logging
import os.path
import csv

logger = logging.getLogger('')


class Scenes():

    def __init__(self, smarthome):
        self._scenes = {}
        self._scenes_dir = smarthome.base_dir + '/scenes/'
        if not os.path.isdir(self._scenes_dir):
            logger.warning("Directory scenes not found. Ignoring scenes.".format(self._scenes_dir))
            return
        for item in smarthome.return_items():
            if item._type == 'scene':
                scene_file = "{}{}.conf".format(self._scenes_dir, item.id())
                try:
                    with open(scene_file, 'r') as f:
                        reader = csv.reader(f, delimiter=' ')
                        for row in reader:
                            ditem = smarthome.return_item(row[1])
                            if ditem is None:
                                ditem = smarthome.return_logic(row[1])
                                if ditem is None:
                                    logger.warning("Could not find item or logic '{0}' specified in {1}".format(row[1], scene_file))
                                    continue
                            if item.id() in self._scenes:
                                if row[0] in self._scenes[item.id()]:
                                    self._scenes[item.id()][row[0]].append([ditem, row[2]])
                                else:
                                    self._scenes[item.id()][row[0]] = [[ditem, row[2]]]
                            else:
                                self._scenes[item.id()] = {row[0]: [[ditem, row[2]]]}
                except Exception as e:
                    logger.warning("Problem reading scene file {0}: {1}".format(scene_file, e))
                    continue
                item.add_method_trigger(self._trigger)

    def _trigger(self, item, caller, source, dest):
        if not item.id() in self._scenes:
            return
        if str(item()) in self._scenes[item.id()]:
            for ditem, value in self._scenes[item.id()][str(item())]:
                ditem(value=value, caller='Scene', source=item.id())

########NEW FILE########
__FILENAME__ = scheduler
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2011-2013 Marcus Popp                          marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py.  If not, see <http://www.gnu.org/licenses/>.
##########################################################################

import gc  # noqa
import logging
import time
import datetime
import calendar
import sys
import traceback
import threading
import os  # noqa
import random
import types  # noqa
import subprocess  # noqa

import dateutil.relativedelta
from dateutil.relativedelta import MO, TU, WE, TH, FR, SA, SU
from dateutil.tz import tzutc

logger = logging.getLogger('')


class PriorityQueue:

    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()

    def insert(self, priority, data):
        self.lock.acquire()
        lo = 0
        hi = len(self.queue)
        while lo < hi:
            mid = (lo + hi) // 2
            if priority < self.queue[mid][0]:
                hi = mid
            else:
                lo = mid + 1
        self.queue.insert(lo, (priority, data))
        self.lock.release()

    def get(self):
        self.lock.acquire()
        try:
            return self.queue.pop(0)
        except IndexError:
            raise
        finally:
            self.lock.release()

    def qsize(self):
        return len(self.queue)


class Scheduler(threading.Thread):

    _workers = []
    _worker_num = 5
    _worker_max = 20
    _worker_delta = 60  # wait 60 seconds before adding another worker thread
    _scheduler = {}
    _runq = PriorityQueue()
    _triggerq = PriorityQueue()

    def __init__(self, smarthome):
        threading.Thread.__init__(self, name='Scheduler')
        logger.info('Init Scheduler')
        self._sh = smarthome
        self._lock = threading.Lock()
        self._runc = threading.Condition()

    def run(self):
        self.alive = True
        logger.debug("creating {0} workers".format(self._worker_num))
        for i in range(self._worker_num):
            self._add_worker()
        while self.alive:
            now = self._sh.now()
            if self._runq.qsize() > len(self._workers):
                delta = now - self._last_worker
                if delta.seconds > self._worker_delta:
                    if len(self._workers) < self._worker_max:
                        self._add_worker()
                    else:
                        logger.error("Needing more worker threads than the specified maximum of {0}!".format(self._worker_max))
                        tn = {}
                        for t in threading.enumerate():
                            tn[t.name] = tn.get(t.name, 0) + 1
                        logger.info('Threads: ' + ', '.join("{0}: {1}".format(k, v) for (k, v) in list(tn.items())))
                        self._add_worker()
            while self._triggerq.qsize() > 0:
                try:
                    (dt, prio), (name, obj, by, source, dest, value) = self._triggerq.get()
                except Exception as e:
                    logger.warning("Trigger queue exception: {0}".format(e))
                    break

                if dt < now:  # run it
                    self._runc.acquire()
                    self._runq.insert(prio, (name, obj, by, source, dest, value))
                    self._runc.notify()
                    self._runc.release()
                else:  # put last entry back and break while loop
                    self._triggerq.insert((dt, prio), (name, obj, by, source, dest, value))
                    break
            self._lock.acquire()
            for name in self._scheduler:
                task = self._scheduler[name]
                if task['next'] is not None:
                    if task['next'] < now:
                        self._runc.acquire()
                        self._runq.insert(task['prio'], (name, task['obj'], 'Scheduler', None, None, task['value']))
                        self._runc.notify()
                        self._runc.release()
                        task['next'] = None
                    else:
                        continue
                elif not task['active']:
                    continue
                else:
                    if task['cron'] is None and task['cycle'] is None:
                        continue
                    else:
                        self._next_time(name)
            self._lock.release()
            time.sleep(0.5)

    def stop(self):
        self.alive = False

    def trigger(self, name, obj=None, by='Logic', source=None, value=None, dest=None, prio=3, dt=None):
        if obj is None:
            if name in self._scheduler:
                obj = self._scheduler[name]['obj']
            else:
                logger.warning("Logic name not found: {0}".format(name))
                return
        if name in self._scheduler:
            if not self._scheduler[name]['active']:
                logger.debug("Logic '{0}' deactivated. Ignoring trigger from {1} {2}".format(name, by, source))
                return
        if dt is None:
            logger.debug("Triggering {0} - by: {1} source: {2} dest: {3} value: {4}".format(name, by, source, dest, str(value)[:40]))
            self._runc.acquire()
            self._runq.insert(prio, (name, obj, by, source, dest, value))
            self._runc.notify()
            self._runc.release()
        else:
            if not isinstance(dt, datetime.datetime):
                logger.warning("Trigger: Not a valid timezone aware datetime for {0}. Ignoring.".format(name))
                return
            if dt.tzinfo is None:
                logger.warning("Trigger: Not a valid timezone aware datetime for {0}. Ignoring.".format(name))
                return
            logger.debug("Triggering {0} - by: {1} source: {2} dest: {3} value: {4} at: {5}".format(name, by, source, dest, str(value)[:40], dt))
            self._triggerq.insert((dt, prio), (name, obj, by, source, dest, value))

    def remove(self, name):
        self._lock.acquire()
        if name in self._scheduler:
            del(self._scheduler[name])
        self._lock.release()

    def return_next(self, name):
        if name in self._scheduler:
            return self._scheduler[name]['next']

    def add(self, name, obj, prio=3, cron=None, cycle=None, value=None, offset=None, next=None):
        self._lock.acquire()
        if isinstance(cron, str):
            cron = [cron, ]
        if isinstance(cron, list):
            _cron = {}
            for entry in cron:
                desc, __, _value = entry.partition('=')
                desc = desc.strip()
                if _value == '':
                    _value = None
                else:
                    _value = _value.strip()
                if desc.startswith('init'):
                    offset = 5  # default init offset
                    desc, op, seconds = desc.partition('+')
                    if op:
                        offset += int(seconds)
                    else:
                        desc, op, seconds = desc.partition('-')
                        if op:
                            offset -= int(seconds)
                    value = _value
                    next = self._sh.now() + datetime.timedelta(seconds=offset)
                else:
                    _cron[desc] = _value
            if _cron == {}:
                cron = None
            else:
                cron = _cron
        if isinstance(cycle, int):
            cycle = {cycle: None}
        elif isinstance(cycle, str):
            cycle, __, _value = cycle.partition('=')
            try:
                cycle = int(cycle.strip())
            except Exception:
                logger.warning("Scheduler: invalid cycle entry for {0} {1}".format(name, cycle))
                return
            if _value != '':
                _value = _value.strip()
            else:
                _value = None
            cycle = {cycle: _value}
        if cycle is not None and offset is None:  # spread cycle jobs
                offset = random.randint(10, 15)
        self._scheduler[name] = {'prio': prio, 'obj': obj, 'cron': cron, 'cycle': cycle, 'value': value, 'next': next, 'active': True}
        if next is None:
            self._next_time(name, offset)
        self._lock.release()

    def change(self, name, **kwargs):
        if name in self._scheduler:
            for key in kwargs:
                if key in self._scheduler[name]:
                    if key == 'cron':
                        if isinstance(kwargs[key], str):
                            kwargs[key] = kwargs[key].split('|')
                    elif key == 'active':
                        if kwargs['active'] and not self._scheduler[name]['active']:
                            logger.info("Activating logic: {0}".format(name))
                        elif not kwargs['active'] and self._scheduler[name]['active']:
                            logger.info("Deactivating logic: {0}".format(name))
                    self._scheduler[name][key] = kwargs[key]
                else:
                    logger.warning("Attribute {0} for {1} not specified. Could not change it.".format(key, name))
            if self._scheduler[name]['active'] is True:
                if 'cycle' in kwargs or 'cron' in kwargs:
                    self._next_time(name)
            else:
                self._scheduler[name]['next'] = None
        else:
            logger.warning("Could not change {0}. No logic/method with this name found.".format(name))

    def _next_time(self, name, offset=None):
        job = self._scheduler[name]
        if None == job['cron'] == job['cycle']:
            self._scheduler[name]['next'] = None
            return
        next_time = None
        value = None
        now = self._sh.now()
        now = now.replace(microsecond=0)
        if job['cycle'] is not None:
            cycle = list(job['cycle'].keys())[0]
            value = job['cycle'][cycle]
            if offset is None:
                offset = cycle
            next_time = now + datetime.timedelta(seconds=offset)
        if job['cron'] is not None:
            for entry in job['cron']:
                ct = self._crontab(entry)
                if next_time is not None:
                    if ct < next_time:
                        next_time = ct
                        value = job['cron'][entry]
                else:
                    next_time = ct
                    value = job['cron'][entry]
        self._scheduler[name]['next'] = next_time
        self._scheduler[name]['value'] = value
        if name not in ['Connections', 'series', 'SQLite dump']:
            logger.debug("{0} next time: {1}".format(name, next_time))

    def __iter__(self):
        for job in self._scheduler:
            yield job

    def _add_worker(self):
        self._last_worker = self._sh.now()
        t = threading.Thread(target=self._worker)
        t.start()
        self._workers.append(t)
        if len(self._workers) > self._worker_num:
            logger.info("Adding worker thread. Total: {0}".format(len(self._workers)))
            tn = {}
            for t in threading.enumerate():
                tn[t.name] = tn.get(t.name, 0) + 1
            logger.info('Threads: ' + ', '.join("{0}: {1}".format(k, v) for (k, v) in list(tn.items())))

    def _worker(self):
        while self.alive:
            self._runc.acquire()
            self._runc.wait(timeout=1)
            try:
                prio, (name, obj, by, source, dest, value) = self._runq.get()
            except IndexError:
                continue
            finally:
                self._runc.release()
            self._task(name, obj, by, source, dest, value)

    def _task(self, name, obj, by, source, dest, value):
        threading.current_thread().name = name
        logger = logging.getLogger(name)
        if obj.__class__.__name__ == 'Logic':
            trigger = {'by': by, 'source': source, 'dest': dest, 'value': value}  # noqa
            logic = obj  # noqa
            sh = self._sh  # noqa
            try:
                exec(obj.bytecode)
            except SystemExit:
                # ignore exit() call from logic.
                pass
            except Exception as e:
                tb = sys.exc_info()[2]
                tb = traceback.extract_tb(tb)[-1]
                logger.exception("Logic: {0}, File: {1}, Line: {2}, Method: {3}, Exception: {4}".format(name, tb[0], tb[1], tb[2], e))
        elif obj.__class__.__name__ == 'Item':
            try:
                if value is not None:
                    obj(value, caller="Scheduler")
            except Exception as e:
                logger.exception("Item {0} exception: {1}".format(name, e))
        else:  # method
            try:
                if value is None:
                    obj()
                else:
                    obj(**value)
            except Exception as e:
                logger.exception("Method {0} exception: {1}".format(name, e))
        threading.current_thread().name = 'idle'

    def _crontab(self, crontab):
        try:
            # process sunrise/sunset
            for entry in crontab.split('<'):
                if entry.startswith('sun'):
                    return self._sun(crontab)
            next_event = self._parse_month(crontab)  # this month
            if not next_event:
                next_event = self._parse_month(crontab, next_month=True)  # next month
            return next_event
        except:
            logger.error("Error parsing crontab: {}".format(crontab))
            return datetime.datetime.now(tzutc()) + dateutil.relativedelta.relativedelta(years=+10)

    def _parse_month(self, crontab, next_month=False):
        now = self._sh.now()
        minute, hour, day, wday = crontab.split(' ')
        # evaluate the crontab strings
        minute_range = self._range(minute, 00, 59)
        hour_range = self._range(hour, 00, 23)
        if not next_month:
            mdays = calendar.monthrange(now.year, now.month)[1]
        elif now.month == 12:
            mdays = calendar.monthrange(now.year + 1, 1)[1]
        else:
            mdays = calendar.monthrange(now.year, now.month + 1)[1]
        if wday == '*' and day == '*':
            day_range = self._day_range('0, 1, 2, 3, 4, 5, 6')
        elif wday != '*' and day == '*':
            day_range = self._day_range(wday)
        elif wday != '*' and day != '*':
            day_range = self._day_range(wday)
            day_range = day_range + self._range(day, 0o1, mdays)
        else:
            day_range = self._range(day, 0o1, mdays)
        # combine the differnt ranges
        event_range = sorted([str(day) + '-' + str(hour) + '-' + str(minute) for minute in minute_range for hour in hour_range for day in day_range])
        if next_month:  # next month
            next_event = event_range[0]
            next_time = now + dateutil.relativedelta.relativedelta(months=+1)
        else:  # this month
            now_str = now.strftime("%d-%H-%M")
            next_event = self._next(lambda event: event > now_str, event_range)
            if not next_event:
                return False
            next_time = now
        day, hour, minute = next_event.split('-')
        return next_time.replace(day=int(day), hour=int(hour), minute=int(minute), second=0, microsecond=0)

    def _next(self, f, seq):
        for item in seq:
            if f(item):
                return item
        return False

    def _sun(self, crontab):
        if not self._sh.sun:  # no sun object created
            logger.warning('No latitude/longitude specified. You could not use sunrise/sunset as crontab entry.')
            return datetime.datetime.now(tzutc()) + dateutil.relativedelta.relativedelta(years=+10)
        # find min/max times
        tabs = crontab.split('<')
        if len(tabs) == 1:
            smin = None
            cron = tabs[0].strip()
            smax = None
        elif len(tabs) == 2:
            if tabs[0].startswith('sun'):
                smin = None
                cron = tabs[0].strip()
                smax = tabs[1].strip()
            else:
                smin = tabs[0].strip()
                cron = tabs[1].strip()
                smax = None
        elif len(tabs) == 3:
            smin = tabs[0].strip()
            cron = tabs[1].strip()
            smax = tabs[2].strip()
        else:
            logger.error('Wrong syntax: {0}. Should be [H:M<](sunrise|sunset)[+|-][offset][<H:M]'.format(crontab))
            return datetime.datetime.now(tzutc()) + dateutil.relativedelta.relativedelta(years=+10)

        doff = 0  # degree offset
        moff = 0  # minute offset
        tmp, op, offs = cron.rpartition('+')
        if op:
            if offs.endswith('m'):
                moff = int(offs.strip('m'))
            else:
                doff = float(offs)
        else:
            tmp, op, offs = cron.rpartition('-')
            if op:
                if offs.endswith('m'):
                    moff = -int(offs.strip('m'))
                else:
                    doff = -float(offs)

        if cron.startswith('sunrise'):
            next_time = self._sh.sun.rise(doff, moff)
        elif cron.startswith('sunset'):
            next_time = self._sh.sun.set(doff, moff)
        else:
            logger.error('Wrong syntax: {0}. Should be [H:M<](sunrise|sunset)[+|-][offset][<H:M]'.format(crontab))
            return datetime.datetime.now(tzutc()) + dateutil.relativedelta.relativedelta(years=+10)

        if smin is not None:
            h, sep, m = smin.partition(':')
            try:
                dmin = next_time.replace(hour=int(h), minute=int(m), second=0, tzinfo=self._sh.tzinfo())
            except Exception:
                logger.error('Wrong syntax: {0}. Should be [H:M<](sunrise|sunset)[+|-][offset][<H:M]'.format(crontab))
                return datetime.datetime.now(tzutc()) + dateutil.relativedelta.relativedelta(years=+10)
            if dmin > next_time:
                next_time = dmin
        if smax is not None:
            h, sep, m = smax.partition(':')
            try:
                dmax = next_time.replace(hour=int(h), minute=int(m), second=0, tzinfo=self._sh.tzinfo())
            except Exception:
                logger.error('Wrong syntax: {0}. Should be [H:M<](sunrise|sunset)[+|-][offset][<H:M]'.format(crontab))
                return datetime.datetime.now(tzutc()) + dateutil.relativedelta.relativedelta(years=+10)
            if dmax < next_time:
                if dmax < self._sh.now():
                    dmax = dmax + datetime.timedelta(days=1)
                next_time = dmax
        return next_time

    def _range(self, entry, low, high):
        result = []
        item_range = []
        if entry == '*':
            item_range = list(range(low, high + 1))
        else:
            for item in entry.split(','):
                item = int(item)
                if item > high:  # entry above range
                    item = high  # truncate value to highest possible
                item_range.append(item)
        for entry in item_range:
            result.append('{:02d}'.format(entry))
        return result

    def _day_range(self, days):
        now = datetime.date.today()
        wdays = [MO, TU, WE, TH, FR, SA, SU]
        result = []
        for day in days.split(','):
            wday = wdays[int(day)]
            # add next weekday occurence
            day = now + dateutil.relativedelta.relativedelta(weekday=wday)
            result.append(day.strftime("%d"))
            # safety add-on if weekday equals todays weekday
            day = now + dateutil.relativedelta.relativedelta(weekday=wday(+2))
            result.append(day.strftime("%d"))
        return result

########NEW FILE########
__FILENAME__ = tools
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2012-2013 Marcus Popp                          marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py.  If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import base64
import datetime
import http.client
import logging
import math
import subprocess
import time

logger = logging.getLogger('')


class Tools():

    def __init__(self):
        self._start = datetime.datetime.now()

    def ping(self, host):
        try:
            retcode = subprocess.call("ping -W 1 -c 1 " + host + " > /dev/null", shell=True)
            if retcode == 0:
                return True
            else:
                return False
        except OSError:
            return False

    def dewpoint(self, t, rf):
        log = math.log((rf + 0.01) / 100)  # + 0.01 to 'cast' float
        return round((241.2 * log + 4222.03716 * t / (241.2 + t)) / (17.5043 - log - 17.5043 * t / (241.2 + t)), 2)

    def dt2js(self, dt):
        return time.mktime(dt.timetuple()) * 1000 + int(dt.microsecond / 1000)

    def dt2ts(self, dt):
        return time.mktime(dt.timetuple())

    def fetch_url(self, url, username=None, password=None, timeout=2):
        headers = {'Accept': 'text/plain'}
        plain = True
        if url.startswith('https'):
            plain = False
        lurl = url.split('/')
        host = lurl[2]
        purl = '/' + '/'.join(lurl[3:])
        if plain:
            conn = http.client.HTTPConnection(host, timeout=timeout)
        else:
            conn = http.client.HTTPSConnection(host, timeout=timeout)
        if username and password:
            headers['Authorization'] = ('Basic '.encode() + base64.b64encode((username + ':' + password).encode()))
        try:
            conn.request("GET", purl, headers=headers)
        except Exception as e:
            logger.warning("Problem fetching {0}: {1}".format(url, e))
            conn.close()
            return False
        resp = conn.getresponse()
        if resp.status == 200:
            content = resp.read()
        else:
            logger.warning("Problem fetching {0}: {1} {2}".format(url, resp.status, resp.reason))
            content = False
        conn.close()
        return content

    def rel2abs(self, t, rf):
        t += 273.15
        if rf > 1:
            rf /= 100
        sat = 611.0 * math.exp(-2.5e6 * 18.0160 / 8.31432E3 * (1.0 / t - 1.0 / 273.16))
        mix = 18.0160 / 28.9660 * rf * sat / (100000 - rf * sat)
        rhov = 100000 / (287.0 * (1 - mix) + 462.0 * mix) / t
        return mix * rhov * 1000

    def runtime(self):
        return datetime.datetime.now() - self._start

########NEW FILE########
__FILENAME__ = name
#!/usr/bin/env python
#
# cp name.py /usr/share/asterisk/agi-bin/name.py
#

import sys
import re
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse

while 1:
    line = sys.stdin.readline()
    if not line.startswith('agi_'):
        break
    key,value = line.split(':')
    vars()[key] = value.strip()

if agi_callerid == 'unknown':
    sys.exit()

number = urllib.parse.quote(agi_callerid)
exp = re.compile('<[^>]*id="name0"[^>]*>([^<]+)<', re.MULTILINE)
lookup = urllib.request.urlopen("http://www3.dastelefonbuch.de/?kw={0}&cmd=search".format(number), data="User-Agent: Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11", timeout=1)
name = exp.search(lookup.read())
if name != None:
    name = name.group(1).strip()
    sys.stdout.write("SET VARIABLE CALLERID(name) \"{0}\"\n".format(name))
    sys.stdout.flush()
    line = sys.stdin.readline()
    sys.stdout.write("DATABASE PUT cache {0} \"{1}\"\n".format(agi_callerid, name))
    sys.stdout.flush()
    line = sys.stdin.readline()

lookup.fp._sock.recv=None
lookup.close()

########NEW FILE########
__FILENAME__ = dpts
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2012-2013 Marcus Popp                         marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py.  If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import struct
import datetime


def en1(value):
    return [int(value) & 0x01]


def de1(payload):
    if len(payload) != 1:
        return None
    return bool(payload[0] & 0x01)


def en2(payload):
    # control, value
    return [(payload[0] << 1) & 0x02 | payload[1] & 0x01]


def de2(payload):
    if len(payload) != 1:
        return None
    return [payload[0] >> 1 & 0x01, payload[0] & 0x01]


def en3(vlist):
    # direction, value
    return [(int(vlist[0]) << 3) & 0x08 | int(vlist[1]) & 0x07]


def de3(payload):
    if len(payload) != 1:
        return None
    # up/down, stepping
    return [payload[0] >> 3 & 0x01, payload[0] & 0x07]


def en4002(value):
    if isinstance(value, str):
        value = value.encode('iso-8859-1')
    else:
        value = str(value)
    return [0, ord(value) & 0xff]


def de4002(payload):
    if len(payload) != 1:
        return None
    return payload.decode('iso-8859-1')


def en5(value):
    if value < 0:
        value = 0
    elif value > 255:
        value = 255
    return [0, int(value) & 0xff]


def de5(payload):
    if len(payload) != 1:
        return None
    return struct.unpack('>B', payload)[0]


def en5001(value):
    if value < 0:
        value = 0
    elif value > 100:
        value = 100
    return [0, int(value * 255.0 / 100) & 0xff]


def de5001(payload):
    if len(payload) != 1:
        return None
    return struct.unpack('>B', payload)[0] * 100.0 / 255


def en6(value):
    if value < -128:
        value = -128
    elif value > 127:
        value = 127
    return [0, struct.pack('b', int(value))[0]]


def de6(payload):
    if len(payload) != 1:
        return None
    return struct.unpack('b', payload)[0]


def en7(value):
    ret = bytearray([0])
    ret.extend(struct.pack('>H', int(value)))
    return ret


def de7(payload):
    if len(payload) != 2:
        return None
    return struct.unpack('>H', payload)[0]


def en8(value):
    if value < -32768:
        value = -32768
    elif value > 32767:
        value = 32767
    ret = bytearray([0])
    ret.extend(struct.pack('>h', int(value)))
    return ret


def de8(payload):
    if len(payload) != 2:
        return None
    return struct.unpack('>h', payload)[0]


def en9(value):
    s = 0
    e = 0
    if value < 0:
        s = 0x8000
    m = int(value * 100)
    while (m > 2047) or (m < -2048):
        e = e + 1
        m = m >> 1
    num = s | (e << 11) | (int(m) & 0x07ff)
    return en7(num)


def de9(payload):
    if len(payload) != 2:
        return None
    i1 = payload[0]
    i2 = payload[1]
    s = (i1 & 0x80) >> 7
    e = (i1 & 0x78) >> 3
    m = (i1 & 0x07) << 8 | i2
    if s == 1:
        s = -1 << 11
    f = (m | s) * 0.01 * pow(2, e)
    return round(f, 2)


def en10(dt):
    return [0, (dt.isoweekday() << 5) | dt.hour, dt.minute, dt.second]


def de10(payload):
    h = payload[0] & 0x1f
    m = payload[1] & 0x3f
    s = payload[2] & 0x3f
    return datetime.time(h, m, s)


def en11(date):
    return [0, date.day, date.month, date.year - 2000]


def de11(payload):
    d = payload[0] & 0x1f
    m = payload[1] & 0x0f
    y = (payload[2] & 0x7f) + 2000  # sorry no 20th century...
    return datetime.date(y, m, d)


def en12(value):
    if value < 0:
        value = 0
    elif value > 4294967295:
        value = 4294967295
    ret = bytearray([0])
    ret.extend(struct.pack('>I', int(value)))
    return ret


def de12(payload):
    if len(payload) != 4:
        return None
    return struct.unpack('>I', payload)[0]


def en13(value):
    if value < -2147483648:
        value = -2147483648
    elif value > 2147483647:
        value = 2147483647
    ret = bytearray([0])
    ret.extend(struct.pack('>i', int(value)))
    return ret


def de13(payload):
    if len(payload) != 4:
        return None
    return struct.unpack('>i', payload)[0]


def en14(value):
    ret = bytearray([0])
    ret.extend(struct.pack('>f', int(value)))
    return ret


def de14(payload):
    if len(payload) != 4:
        return None
    return struct.unpack('>f', payload)[0]


def en16000(value):
    enc = bytearray(1)
    enc.extend(value.encode('ascii')[:14])
    enc.extend([0] * (15 - len(enc)))
    return enc


def en16001(value):
    enc = bytearray(1)
    enc.extend(value.encode('iso-8859-1')[:14])
    enc.extend([0] * (15 - len(enc)))
    return enc


def de16000(payload):
    return payload.rstrip(b'0').decode()


def de16001(payload):
    return payload.rstrip(b'0').decode('iso-8859-1')


def en17(value):
    return [0, int(value) & 0x3f]


def de17(payload):
    if len(payload) != 1:
        return None
    return struct.unpack('>B', payload)[0] & 0x3f


def en20(value):
    return [0, int(value) & 0xff]


def de20(payload):
    if len(payload) != 1:
        return None
    return struct.unpack('>B', payload)[0]


def en24(value):
    enc = bytearray(1)
    enc.extend(value.encode('iso-8859-1'))
    enc.append(0)
    return enc


def de24(payload):
    return payload.rstrip(b'\x00').decode('iso-8859-1')


def en232(value):
    return [0, int(value[0]) & 0xff, int(value[1]) & 0xff, int(value[2]) & 0xff]


def de232(payload):
    if len(payload) != 3:
        return None
    return list(struct.unpack('>BBB', payload))


def depa(string):
    if len(string) != 2:
        return None
    pa = struct.unpack(">H", string)[0]
    return "{0}.{1}.{2}".format((pa >> 12) & 0x0f, (pa >> 8) & 0x0f, (pa) & 0xff)


def enga(ga):
    ga = ga.split('/')
    return [int(ga[0]) << 3 | int(ga[1]), int(ga[2])]


def dega(string):
    if len(string) != 2:
        return None
    ga = struct.unpack(">H", string)[0]
    return "{0}/{1}/{2}".format((ga >> 11) & 0x1f, (ga >> 8) & 0x07, (ga) & 0xff)


decode = {
    '1': de1,
    '2': de2,
    '3': de3,
    '4002': de4002,
    '4.002': de4002,
    '5': de5,
    '5001': de5001,
    '5.001': de5001,
    '6': de6,
    '7': de7,
    '8': de8,
    '9': de9,
    '10': de10,
    '11': de11,
    '12': de12,
    '13': de13,
    '14': de14,
    '16000': de16000,
    '16': de16000,
    '16001': de16001,
    '16.001': de16001,
    '17': de17,
    '20': de20,
    '24': de24,
    '232': de232,
    'pa': depa,
    'ga': dega
}

encode = {
    '1': en1,
    '2': en2,
    '3': en3,
    '4002': en4002,
    '4.002': en4002,
    '5': en5,
    '5001': en5001,
    '5.001': en5001,
    '6': en6,
    '7': en7,
    '8': en8,
    '9': en9,
    '10': en10,
    '11': en11,
    '12': en12,
    '13': en13,
    '14': en14,
    '16000': en16000,
    '16': en16000,
    '16001': en16001,
    '16.001': en16001,
    '17': en17,
    '20': en20,
    '24': en24,
    '232': en232,
    'ga': enga
}
# DPT: 19, 28

########NEW FILE########
__FILENAME__ = generator
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2012-2013 Marcus Popp                         marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import logging

logger = logging.getLogger('')


def return_html(smarthome, item):
    html = ''
    if 'visu' in item.conf:
        visu = item.conf['visu']
        dom = item.id().replace('.', '_')
        if visu in ['text', 'textarea', 'toggle', 'checkbox', 'radio', 'select', 'slider']:  # regular form elements
            html += '<div data-role="fieldcontain">\n'.format(dom)
            if visu == 'text':
                html += '    <label for="{0}">{1}</label>\n'.format(dom, item)
                html += '    <input id="{0}" data-sh="{1}" type="text" />\n'.format(dom, item.id())
            elif visu == 'textarea':
                html += '    <label for="{0}">{1}</label>\n'.format(dom, item)
                html += '    <textarea id="{0}" data-sh="{1}" type="checkbox"></textarea>\n'.format(dom, item.id())
            elif visu == 'toggle':
                html += '    <label for="{0}">{1}</label>\n'.format(dom, item)
                if 'visu_opt' in item.conf:
                    opt = item.conf['visu_opt']
                else:
                    opt = ['Off', 'On']
                html += '    <select id="{0}" data-sh="{1}" data-role="slider"><option value="off">{2}</option><option value="on">{3}</option></select>\n'.format(dom, item.id(), opt[0], opt[1])
            elif visu == 'checkbox':
                html += '    <label for="{0}">{1}</label>\n'.format(dom, item)
                html += '    <input id="{0}" data-sh="{1}" type="checkbox" />\n'.format(dom, item.id())
            elif visu == 'slider':
                html += '    <label for="{0}">{1}</label>\n'.format(dom, item)
                if 'visu_opt' in item.conf:
                    opt = item.conf['visu_opt']
                else:
                    opt = [0, 100, 5]
                html += '    <input id="{0}" data-sh="{1}" type="range" min="{2}" max="{3}" step="{4}" />\n'.format(dom, item.id(), opt[0], opt[1], opt[2])
            elif visu == 'select':
                html += '<fieldset data-role="controlgroup">\n'
                if 'visu_opt' in item.conf:
                    opt = item.conf['visu_opt']
                else:
                    opt = ['Please specify the "visu_opt" attribute']
                html += '    <legend>{0}</legend>\n'.format(item)
                html += '    <select id="{0}" data-sh="{1}">\n'.format(dom, item.id())
                for value in opt:
                    html += '        <option value="{0}">{0}</option>\n'.format(value)
                html += '    </select>\n'
                html += '</fieldset>\n'
            elif visu == 'radio':
                html += '<fieldset data-role="controlgroup">\n'
                i = 0
                if 'visu_opt' in item.conf:
                    opt = item.conf['visu_opt']
                else:
                    opt = ['Please specify the "visu_opt" attribute']
                html += '    <legend>{0}</legend>\n'.format(item)
                for value in opt:
                    i += 1
                    html += '    <label for="{0}{1}">{2}</label>\n'.format(dom, i, value)
                    html += '    <input id="{0}{1}" name="{0}" data-sh="{2}" value="{3}" type="radio" />\n'.format(dom, i, item.id(), value)
                html += '</fieldset>\n'
            html += '</div>\n'
        elif visu in ['div', 'span', 'img', 'list']:  # passive elements
            if 'unit' in item.conf:
                unit = ' data-unit="{0}"'.format(item.conf['unit'])
            else:
                unit = ''
            if visu == 'div':
                html += '<div>{0}: <span data-sh="{1}"{2}></span></div>\n'.format(item, item.id(), unit)
            elif visu == 'span':
                html += '<div>{0}: <span data-sh="{1}"{2}></span></div>\n'.format(item, item.id(), unit)
            elif visu == 'img':
                html += '<div>{0}: <img data-sh="{1}" src="{2}" /></div>\n'.format(item, item.id(), item())
            elif visu == 'list':
                html += '<h2>{0}</h2><ul data-sh="{1}" data-filter="true" data-role="listview" data-inset="true"></ul>\n'.format(item, item.id())
        elif visu in ['switch', 'push', 'dpt3']:  # active elements
            if visu == 'switch':
                html += '<div>{0}: <img data-sh="{1}" src="/img/t.png" class="switch" /></div>\n'.format(item, item.id())
            elif visu == 'push':
                if 'visu_opt' not in item.conf:
                    logger.warning('No viso_opt img specified for push button {0}'.format(item.id()))
                    return
                if 'knx_dpt' in item.conf:
                    if item.conf['knx_dpt'] == '3':
                        html += '<div>{0}: <img data-sh="{1}" src="{2}" class="push" data-cycle="500" data-arr="0" />\n'.format(item, item.id(), item.conf['visu_opt'][0])
                        html += '<img data-sh="{1}" src="{2}" class="push" data-cycle="500" data-arr="1" /></div>\n'.format(item, item.id(), item.conf['visu_opt'][1])
                    else:
                        html += '<div>{0}: <img data-sh="{1}" src="{2}" class="push" /></div>\n'.format(item, item.id(), item.conf['visu_opt'])
                else:
                    html += '<div>{0}: <img data-sh="{1}" src="{2}" class="push" /></div>\n'.format(item, item.id(), item.conf['visu_opt'])
        elif visu == 'rrd':
            if 'visu_opt' in item.conf:
                if isinstance(item.conf['visu_opt'], list):
                    rrd = []
                    for path in item.conf['visu_opt']:
                        vitem = smarthome.return_item(path)
                        if vitem is not None:
                            if 'rrd' in vitem.conf:
                                rrd.append("{0}='label': '{1}'".format(vitem.id(), vitem))
                    rrd = "|".join(rrd)
            else:
                rrd = "{0}='label': '{1}'".format(item.id(), item)
            html += '<div data-rrd="{0}" data-frame="1d" style="margin:20px;width:device-width;height:300px"></div>\n'.format(rrd)
    return html


def return_tree(smarthome, item):
    html = ''
    html += return_html(smarthome, item)
    for child in item:
        html += return_tree(smarthome, child)
    return html

########NEW FILE########
__FILENAME__ = smartvisu
#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2013 Marcus Popp                              marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import logging
import os
import shutil

logger = logging.getLogger('')


def parse_tpl(template, replace):
    try:
        with open(template, 'r', encoding='utf-8') as f:
            tpl = f.read()
            tpl = tpl.lstrip('\ufeff')  # remove BOM
    except Exception as e:
        logger.error("Could not read template file '{0}': {1}".format(template, e))
        return ''
    for s, r in replace:
        tpl = tpl.replace(s, r)
    return tpl


def room(smarthome, room, tpldir):
    widgets = ''
    if 'sv_img' in room.conf:
        rimg = room.conf['sv_img']
    else:
        rimg = ''
    if 'sv_widget' in room.conf:
        items = [room]
    else:
        items = []
    items.extend(smarthome.find_children(room, 'sv_widget'))
    for item in items:
        if 'sv_img' in item.conf:
            img = item.conf['sv_img']
        else:
            img = ''
        if isinstance(item.conf['sv_widget'], list):
            for widget in item.conf['sv_widget']:
                widgets += parse_tpl(tpldir + '/widget.html', [('{{ visu_name }}', str(item)), ('{{ visu_img }}', img), ('{{ visu_widget }}', widget), ('item.name', str(item)), ("'item", "'" + item.id())])
        else:
            widget = item.conf['sv_widget']
            widgets += parse_tpl(tpldir + '/widget.html', [('{{ visu_name }}', str(item)), ('{{ visu_img }}', img), ('{{ visu_widget }}', widget), ('item.name', str(item)), ("'item", "'" + item.id())])
    return parse_tpl(tpldir + '/room.html', [('{{ visu_name }}', str(room)), ('{{ visu_widgets }}', widgets), ('{{ visu_img }}', rimg)])


def pages(smarthome, directory):
    nav_lis = ''
    outdir = directory + '/pages/smarthome'
    tpldir = directory + '/pages/base/tpl'
    tmpdir = directory + '/temp'
    # clear temp directory
    if not os.path.isdir(tmpdir):
        logger.warning("Could not find directory: {0}".format(tmpdir))
        return
    for dn in os.listdir(tmpdir):
        if len(dn) != 2:  # only delete Twig temp files
            continue
        dp = os.path.join(tmpdir, dn)
        try:
            if os.path.isdir(dp):
                shutil.rmtree(dp)
        except Exception as e:
            logger.warning("Could not delete directory {0}: {1}".format(dp, e))
    # create output directory
    try:
        os.mkdir(outdir)
    except:
        pass
    # remove old dynamic files
    if not os.path.isdir(outdir):
        logger.warning("Could not find/create directory: {0}".format(outdir))
        return
    for fn in os.listdir(outdir):
        fp = os.path.join(outdir, fn)
        try:
            if os.path.isfile(fp):
                os.unlink(fp)
        except Exception as e:
            logger.warning("Could not delete file {0}: {1}".format(fp, e))
    for item in smarthome.find_items('sv_page'):
        r = room(smarthome, item, tpldir)
        if 'sv_img' in item.conf:
            img = item.conf['sv_img']
        else:
            img = ''
        nav_lis += parse_tpl(tpldir + '/navi.html', [('{{ visu_page }}', item.id()), ('{{ visu_name }}', str(item)), ('{{ visu_img }}', img)])
        try:
            with open("{0}/{1}.html".format(outdir, item.id()), 'w') as f:
                f.write(r)
        except Exception as e:
            logger.warning("Could not write to {0}/{1}.html: {}".format(outdir, item.id(), e))
    nav = parse_tpl(tpldir + '/navigation.html', [('{{ visu_navis }}', nav_lis)])
    try:
        with open(outdir + '/navigation.html', 'w') as f:
            f.write(nav)
    except Exception as e:
        logger.warning("Could not write to {0}/navigation.html".format(outdir))
    shutil.copy(tpldir + '/rooms.html', outdir + '/')
    shutil.copy(tpldir + '/index.html', outdir + '/')

########NEW FILE########
__FILENAME__ = ets4parser
#!/usr/bin/env python
#
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2012 KNX-User-Forum e.V.            http://knx-user-forum.de/
#########################################################################
#  This file is part of SmartHome.py.   http://smarthome.sourceforge.net/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
##########################################################################

import os
import sys
from collections import namedtuple
import xml.etree.ElementTree as ET

# erster Knoten ist meist das Projekt, damit das nicht mit abgebildet wird
# folgende Option auf 1 setzen
IGNORE_TOP_LEVEL = 1

NS_URL = '{http://knx.org/xml/project/10}'
FIND_BUILDINGS = NS_URL + 'Buildings'
FIND_BUILDINGPART = NS_URL + 'BuildingPart'
FIND_DEVICEREF = NS_URL + 'DeviceInstanceRef'
FIND_DEVICE = NS_URL + 'DeviceInstance'
FIND_COMREF = NS_URL + 'ComObjectInstanceRef'
FIND_CONNECTOR = NS_URL + 'Connectors'
FIND_SEND = NS_URL + 'Send'
FIND_RECEIVE = NS_URL + 'Receive'
FIND_GA = NS_URL + 'GroupAddress'
FIND_DPT = NS_URL + 'DatapointType'
FIND_DPST = NS_URL + 'DatapointSubtype'

def processBuildingPart(root, part, depth, f, dpts):
	print(u"processing {0} {1} ({2})".format(part.tag, part.attrib['Name'], part.attrib['Type']))

	if part.attrib['Type'] != "DistributionBoard":
		write_item(part.attrib['Name'], depth, f)
		
		for devref in part.findall(FIND_DEVICEREF):
			processDevice(root, devref.attrib['RefId'], depth + 1, f, dpts)

	for subpart in part.findall(FIND_BUILDINGPART):
		processBuildingPart(root, subpart, depth + 1, f, dpts)
		
	f.write('\n')

def processDevice(root, ref, depth, f, dpts):
	print(u"process device {0}".format(ref))
	device = root.findall('.//' + FIND_DEVICE + "[@Id='" + ref + "']")[0]
	if 'Description' in device.attrib.keys():
		print(u"".format(device.attrib['Description']))

	for comobj in device.findall('.//' + FIND_COMREF):
		if 'DatapointType' not in comobj.attrib.keys():
			continue

		if comobj.attrib['DatapointType'] not in dpts:
			dpt = 1
		else:
			dpt = dpts[comobj.attrib['DatapointType']].dpt.number

		for connector in comobj.findall('.//' + FIND_CONNECTOR):

			for send in connector.findall('.//' + FIND_SEND):
				if 'GroupAddressRefId' in send.keys():
					ga_ref = send.attrib['GroupAddressRefId']
					print(u"process ga {0}".format(ga_ref))
					ga = root.findall('.//' + FIND_GA + "[@Id='" + ga_ref + "']")[0]
					ga_str = ga2str(int(ga.attrib['Address']))
					print(u"Send GA: {0} ({1})".format(ga_str, ga.attrib['Name']))

					if len(ga_str) > 0:
						write_item(ga.attrib['Name'], depth, f)
						write_dpt(dpt, depth + 1, f)
						write_param("knx_send=" + ga_str, depth + 1, f)
						write_param("knx_listen=" + ga_str, depth + 1, f)

			for receive in connector.findall('.//' + FIND_RECEIVE):
				if 'GroupAddressRefId' in receive.keys():
					ga_ref = receive.attrib['GroupAddressRefId']
					print(u"process ga {0}".format(ga_ref))
					ga = root.findall('.//' + FIND_GA + "[@Id='" + ga_ref + "']")[0]
					ga_str = ga2str(int(ga.attrib['Address']))
					print(u"Receive GA: {0} ({1})".format(ga_str, ga.attrib['Name']))

					if len(ga_str) > 0:
						write_item(ga.attrib['Name'], depth, f)
						write_dpt(dpt, depth + 1, f)
						write_param("knx_read=" + ga_str, depth + 1, f)
						write_param("knx_listen=" + ga_str, depth + 1, f)

def write_dpt(dpt, depth, f):
	if dpt == 1:
		write_param("type=bool", depth, f)
		write_param("visu=toggle", depth, f)
	elif dpt == 2 or dpt == 3 or dpt == 10 or dpt == 11:
		write_param("type=foo", depth, f)
	elif dpt == 4 or dpt == 24:
		write_param("type=str", depth, f)
		write_param("visu=div", depth, f)
	else:
		write_param("type=num", depth, f)
		write_param("visu=slider", depth, f)
		write_param("knx_dpt=5001", depth, f)
		return

	write_param("knx_dpt=" + str(dpt), depth, f)

def write_param(string, depth, f):
	for i in range(depth):
		f.write('    ')

	f.write(string + '\n')

def write_item(string, depth, f):
	for i in range(depth):
		f.write('    ')

	for i in range(depth + 1):
		f.write('[')

	f.write("'" + string.encode('UTF-8').lower() + "'")

	for i in range(depth + 1):
		f.write(']')

	f.write('\n')

def ga2str(ga):
	return "%d/%d/%d" % ((ga >> 11) & 0xf, (ga >> 8) & 0x7, ga & 0xff)

def pa2str(pa):
	return "%d.%d.%d" % (pa >> 12, (pa >> 8) & 0xf, pa & 0xff)

##############################################################
#		Main
##############################################################

KNXMASTERFILE = sys.argv[1]
PROJECTFILE = sys.argv[2]
OUTFILE = sys.argv[3]

print "Master: " + KNXMASTERFILE
print "Project: " + PROJECTFILE
print "Outfile: " + OUTFILE

if (os.path.exists(OUTFILE)):
	os.remove(OUTFILE)

master = ET.parse(KNXMASTERFILE)
root = master.getroot()
dpts = {}

DPT = namedtuple('DPT', ['id', 'number', 'name', 'text', 'size', 'dpsts'])
DPST = namedtuple('DPST', ['id', 'number', 'name', 'text', 'dpt'])

for dpt in root.findall('.//' + FIND_DPT):
	item = DPT(id = dpt.attrib['Id'], number = int(dpt.attrib['Number']), name = dpt.attrib['Name'], text = dpt.attrib['Text'], size = int(dpt.attrib['SizeInBit']), dpsts = {})

	for dpst in dpt.findall('.//' + FIND_DPST):
		sub = DPST(id = dpst.attrib['Id'], number = int(dpst.attrib['Number']), name = dpst.attrib['Name'], text = dpst.attrib['Text'], dpt = item)
		item.dpsts[sub.id] = sub
		dpts[sub.id] = sub

	dpts[item.id] = item


project = ET.parse(PROJECTFILE)
root = project.getroot()
buildings = root.find('.//' + FIND_BUILDINGS)

if buildings is None:
	print "Buildings not found"
else:
	with open(OUTFILE, 'w') as f:
		if IGNORE_TOP_LEVEL:
			for part in buildings[0]:
				processBuildingPart(root, part, 0, f, dpts)
		else:
			for part in buildings:
				processBuildingPart(root, part, 0, f, dpts)



########NEW FILE########
__FILENAME__ = ga2conf
#!/usr/bin/env python
#
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2012 KNX-User-Forum e.V.            http://knx-user-forum.de/
#########################################################################
#  This file is part of SmartHome.py.   http://smarthome.sourceforge.net/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
##########################################################################

import os
import sys
import re
from collections import namedtuple
import xml.etree.ElementTree as ET

NS_URL = '{http://knx.org/xml/project/10}'
FIND_GA = NS_URL + 'GroupAddress'

def write_dpt(dpt, depth, f):
	if dpt == 1:
		write_param("type=bool", depth, f)
		write_param("visu=toggle", depth, f)
	elif dpt == 2 or dpt == 3 or dpt == 10 or dpt == 11:
		write_param("type=foo", depth, f)
	elif dpt == 4 or dpt == 24:
		write_param("type=str", depth, f)
		write_param("visu=div", depth, f)
	else:
		write_param("type=num", depth, f)
		write_param("visu=slider", depth, f)
		write_param("knx_dpt=5001", depth, f)
		return

	write_param("knx_dpt=" + str(dpt), depth, f)

def write_dict(a, depth, f):
    if 'sh_attributes' in a.keys():
        write_attributes(a['sh_attributes'], depth, f)

    for k in a.keys():
        if k == 'sh_attributes':
            continue

        write_item(k, depth, f)
        write_dict(a[k], depth+1, f)

def write_attributes(attr, depth, f):
    attr_str = ""
    for k in attr.keys():
        val = ""
        attr[k] = list(set(attr[k]))
        for v in attr[k]:
            if len(val) > 0:
                val += ", "
            val += v
        write_param(u"{0} = {1}".format(k, val), depth, f)    

def write_param(string, depth, f):
	for i in range(depth):
		f.write('    ')

	f.write(string + '\n')

def write_item(string, depth, f):
	for i in range(depth):
		f.write('    ')

	for i in range(depth + 1):
		f.write('[')

	f.write("'" + string.encode('UTF-8').lower() + "'")

	for i in range(depth + 1):
		f.write(']')

	f.write('\n')

def ga2str(ga):
	return "%d/%d/%d" % ((ga >> 11) & 0xf, (ga >> 8) & 0x7, ga & 0xff)

def pa2str(pa):
	return "%d.%d.%d" % (pa >> 12, (pa >> 8) & 0xf, pa & 0xff)

class AutoVivification(dict):
    """Implementation of perl's autovivification feature."""
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value

##############################################################
#		Main
##############################################################

PROJECTFILE = sys.argv[1]

print "Project: " + PROJECTFILE

project = ET.parse(PROJECTFILE)
root = project.getroot()
a = AutoVivification()

for ga in root.findall('.//' + FIND_GA):
    if 'Description' in ga.attrib.keys() and 'Name' in ga.attrib.keys():
        desc = ga.attrib['Description']
        name = ga.attrib['Name']

        match = re.match(r".*\s*sh\((?P<sh_str>[^)]*)\).*", desc)
        if match:
            parts = name.split(' ')
            item = a
            for part in parts:
                item = item[part]
            
            parts = match.group('sh_str').split('|',1)
            ga_str = ga2str(int(ga.attrib['Address']))
            ga_attributes = parts[0].split(',')

            for ga_attribute in ga_attributes:
                if not ga_attribute in item['sh_attributes'].keys():
                    item['sh_attributes'][ga_attribute] = []
                item['sh_attributes'][ga_attribute].append(ga_str)
            
            if len(parts) > 1:
                for part in parts[1].split('|'):
                    p = part.split('=')
                    if len(p) == 2:
                        if not p[0] in item['sh_attributes'].keys():
                            item['sh_attributes'][p[0]] = []
                        item['sh_attributes'][p[0]].append(p[1].strip())                            

for k in a.keys():
    OUTFILE = u"{0}.conf".format(k)
    print u"Create File: {0}".format(OUTFILE)
    
    if (os.path.exists(OUTFILE)):
	    os.remove(OUTFILE)

    with open(OUTFILE, 'w') as f:
        write_item(k, 0, f)
        write_dict(a[k], 1, f)

########NEW FILE########
__FILENAME__ = owmonitor
#!/usr/bin/env python
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2012-2013 KNX-User-Forum e.V.       http://knx-user-forum.de/
#########################################################################
#  This file is part of SmartHome.py.   http://smarthome.sourceforge.net/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
##########################################################################

import time
import sys
import logging
sys.path.append("/usr/smarthome")

import plugins.onewire

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('')

host = '127.0.0.1'
port = 4304

ow = plugins.onewire.OwBase(host, port)
ow.connect()

old = []
while 1:
    try:
        new = ow.dir('/uncached')
    except Exception, e:
        logger.error(e)
        sys.exit()
    dif = list(set(new) - set(old))
    for sensor in dif:
        try:
            sensor = sensor.replace('/uncached', '')
            typ = ow.read(sensor + 'type')
            sensors = ow.identify_sensor(sensor)
            print("new sensor {0} ({1}) provides: {2}".format(sensor, typ, sensors))
        except Exception, e:
            pass
    old += dif
    time.sleep(1)

########NEW FILE########
__FILENAME__ = owsensors2items
#!/usr/bin/env python
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2012-2013 KNX-User-Forum e.V.       http://knx-user-forum.de/
#########################################################################
#  This file is part of SmartHome.py.   http://smarthome.sourceforge.net/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
##########################################################################


import ConfigParser, io, sys

conf = ''
# read conf and skip header entries (no section)
try:

    with open(sys.argv[1], 'r') as cfg:
        found_section = False
        for l in cfg.readlines():
            if len(l.strip()) == 0: 
                continue
            if l[0] != '[' and found_section == False:
                continue
            found_section = True
            conf += l

    with open(sys.argv[2], 'w') as out:
        config = ConfigParser.ConfigParser()
        config.readfp(io.BytesIO(conf))
        for section in config.sections():
            try:
                name = config.get(section, 'name')
                typ = config.get(section, 'type')
            except ConfigParser.NoOptionError:
                continue
            if typ == 'DS1820':
                sensor = 'T' + config.get(section, 'resolution')
                typ = 'num'
                knx_send = config.get(section, 'eib_ga_temp')
            elif typ == 'DS2438Hum' or typ == 'DS2438Datanab':
                sensor = 'H'
                typ = 'num'
            elif typ == 'DS1990':
                sensor = 'B'
                typ = 'bool'
                knx_send = config.get(section, 'eib_ga_present')
            elif typ == 'DS2401':
                sensor = 'B'
                typ = 'bool'
                knx_send = config.get(section, 'eib_ga_present')
            elif typ == 'DS9490':
                sensor = 'BM'
                typ = 'bool'
            else:
                continue

            out.write('''
[[{0}]]
    name = {0}
    type = {1}
    ow_addr = {2}
    ow_sensor = {3}
    #knx_send = {4}
    #knx_reply = {4}
        '''.format(name, typ, section, sensor,knx_send))

except:
    print "usage: owsensors2item.py <input_file> <output_file>"
    sys.exit()

########NEW FILE########
