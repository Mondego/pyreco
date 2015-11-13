__FILENAME__ = log
class Log(object):
    """ Log class that outputs text to a curses screen """

    msg = None
    cursesScreen = None

    def __init__(self):
        self.width = None

    def setScreen(self, cursesScreen):
        self.cursesScreen = cursesScreen
        self.width = cursesScreen.getmaxyx()[1] - 5

        # Redisplay the last message
        if self.msg:
            self.write(self.msg)

    def write(self, msg):
        self.msg = msg.strip()

        if self.cursesScreen:
            self.cursesScreen.erase()
            self.cursesScreen.addstr(0, 1, self.msg[0: self.width]
                                     .replace("\r", "").replace("\n", ""))
            self.cursesScreen.refresh()

    def readline(self):
        pass

########NEW FILE########
__FILENAME__ = main
import csv
import sys
import curses
import logging
from argparse import ArgumentParser
from os import path, getenv

from .radio import PyRadio

PATTERN = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def __configureLogger():
    logger = logging.getLogger("pyradio")
    logger.setLevel(logging.DEBUG)

    # Handler
    fh = logging.FileHandler("pyradio.log")
    fh.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(PATTERN)

    # add formatter to ch
    fh.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(fh)

DEFAULT_FILE = ''
for p in [path.join(getenv('HOME', '~'), '.pyradio', 'stations.csv'),
          path.join(getenv('HOME', '~'), '.pyradio'),
          path.join(path.dirname(__file__), 'stations.csv')]:
    if path.exists(p) and path.isfile(p):
        DEFAULT_FILE = p
        break


def shell():
    parser = ArgumentParser(description="Console radio player")
    parser.add_argument("--stations", "-s", default=DEFAULT_FILE,
                        help="Path on stations csv file.")
    parser.add_argument("--play", "-p", nargs='?', default=False,
                        help="Start and play. "
                        "The value is num station or empty for random.")
    parser.add_argument("--add", "-a", action='store_true',
                        help="Add station to list.")
    parser.add_argument("--list", "-l", action='store_true',
                        help="List of added stations.")
    parser.add_argument("--debug", "-d", action='store_true',
                        help="Start pyradio in debug mode.")
    args = parser.parse_args()

    # No need to parse the file if we add station
    if args.add:
        params = input("Enter the name: "), input("Enter the url: ")
        with open(args.stations, 'a') as cfgfile:
            writter = csv.writer(cfgfile)
            writter.writerow(params)
            sys.exit()

    with open(args.stations, 'r') as cfgfile:
        stations = []
        for row in csv.reader(cfgfile, skipinitialspace=True):
            if row[0].startswith('#'):
                continue
            name, url = [s.strip() for s in row]
            stations.append((name, url))

    if args.list:
        for name, url in stations:
            print(('{0:50s} {1:s}'.format(name, url)))
        sys.exit()

    if args.debug:
        __configureLogger()
        print("Debug mode acitvated")

    # Starts the radio gui.
    pyradio = PyRadio(stations, play=args.play)
    curses.wrapper(pyradio.setup)


if __name__ == '__main__':
    shell()

########NEW FILE########
__FILENAME__ = player
import subprocess
import threading
import os
import logging

logger = logging.getLogger(__name__)


class Player(object):
    """ Media player class. Playing is handled by mplayer """
    process = None

    def __init__(self, outputStream):
        self.outputStream = outputStream

    def __del__(self):
        self.close()

    def updateStatus(self):
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug("updateStatus thread started.")
        try:
            out = self.process.stdout
            while(True):
                subsystemOut = out.readline().decode("utf-8")
                if subsystemOut == '':
                    break
                subsystemOut = subsystemOut.strip()
                subsystemOut = subsystemOut.replace("\r", "").replace("\n", "")
                if (logger.isEnabledFor(logging.DEBUG)):
                    logger.debug("User input: {}".format(subsystemOut))
                self.outputStream.write(subsystemOut)
        except:
            logger.error("Error in updateStatus thread.",
                         exc_info=True)
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug("updateStatus thread stopped.")

    def isPlaying(self):
        return bool(self.process)

    def play(self, streamUrl):
        """ use a multimedia player to play a stream """
        self.close()
        opts = []
        isPlayList = streamUrl.split("?")[0][-3:] in ['m3u', 'pls']
        opts = self._buildStartOpts(streamUrl, isPlayList)
        self.process = subprocess.Popen(opts, shell=False,
                                        stdout=subprocess.PIPE,
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
        t = threading.Thread(target=self.updateStatus, args=())
        t.start()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Player started")

    def _sendCommand(self, command):
        """ send keystroke command to mplayer """

        if(self.process is not None):
            try:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Command: {}".format(command).strip())
                self.process.stdin.write(command.encode("utf-8"))
            except:
                msg = "Error when sending: {}"
                logger.error(msg.format(command).strip(),
                             exc_info=True)

    def close(self):
        """ exit pyradio (and kill mplayer instance) """

        # First close the subprocess
        self._stop()

        # Here is fallback solution and cleanup
        if self.process is not None:
            os.kill(self.process.pid, 15)
            self.process.wait()
        self.process = None

    def _buildStartOpts(self, streamUrl, playList):
        pass

    def mute(self):
        pass

    def _stop(self):
        pass

    def volumeUp(self):
        pass

    def volumeDown(self):
        pass


class MpPlayer(Player):
    """Implementation of Player object for MPlayer"""

    PLAYER_CMD = "mplayer"

    def _buildStartOpts(self, streamUrl, playList=False):
        """ Builds the options to pass to subprocess."""
        if playList:
            opts = [self.PLAYER_CMD, "-quiet", "-playlist", streamUrl]
        else:
            opts = [self.PLAYER_CMD, "-quiet", streamUrl]
        return opts

    def mute(self):
        """ mute mplayer """
        self._sendCommand("m")

    def pause(self):
        """ pause streaming (if possible) """
        self._sendCommand("p")

    def _stop(self):
        """ exit pyradio (and kill mplayer instance) """
        self._sendCommand("q")

    def volumeUp(self):
        """ increase mplayer's volume """
        self._sendCommand("*")

    def volumeDown(self):
        """ decrease mplayer's volume """
        self._sendCommand("/")


class VlcPlayer(Player):
    """Implementation of Player for VLC"""

    PLAYER_CMD = "cvlc"

    muted = False

    def _buildStartOpts(self, streamUrl, playList=False):
        """ Builds the options to pass to subprocess."""
        opts = [self.PLAYER_CMD, "-Irc", "--quiet", streamUrl]
        return opts

    def mute(self):
        """ mute mplayer """

        if not self.muted:
            self._sendCommand("volume 0\n")
            self.muted = True
        else:
            self._sendCommand("volume 256\n")
            self.muted = False

    def pause(self):
        """ pause streaming (if possible) """
        self._sendCommand("stop\n")

    def _stop(self):
        """ exit pyradio (and kill mplayer instance) """
        self._sendCommand("shutdown\n")

    def volumeUp(self):
        """ increase mplayer's volume """
        self._sendCommand("volup\n")

    def volumeDown(self):
        """ decrease mplayer's volume """
        self._sendCommand("voldown\n")


def probePlayer():
    """ Probes the multimedia players which are available on the host
    system."""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Probing available multimedia players...")
    implementedPlayers = Player.__subclasses__()
    if logger.isEnabledFor(logging.INFO):
        logger.info("Implemented players: " +
                    ", ".join([player.PLAYER_CMD
                              for player in implementedPlayers]))

    for player in implementedPlayers:
        try:
            p = subprocess.Popen([player.PLAYER_CMD, "--help"],
                                 stdout=subprocess.PIPE,
                                 stdin=subprocess.PIPE,
                                 shell=False)
            p.terminate()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("{} supported.".format(str(player)))
            return player
        except OSError:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("{} not supported.".format(str(player)))

########NEW FILE########
__FILENAME__ = radio
#!/usr/bin/env python

# PyRadio: Curses based Internet Radio Player
# http://www.coderholic.com/pyradio
# Ben Dowling - 2009 - 2010
# Kirill Klenov - 2012
import curses
import logging
import os
import random

from .log import Log
from . import player

import locale
locale.setlocale(locale.LC_ALL, "")


logger = logging.getLogger(__name__)


def rel(path):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), path)


class PyRadio(object):
    startPos = 0
    selection = 0
    playing = -1

    def __init__(self, stations, play=False):
        self.stations = stations
        self.play = play
        self.stdscr = None

    def setup(self, stdscr):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("GUI initialization")
        self.stdscr = stdscr

        try:
            curses.curs_set(0)
        except:
            pass

        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(8, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_GREEN)

        self.log = Log()
        # For the time being, supported players are mplayer and vlc.
        self.player = player.probePlayer()(self.log)

        self.stdscr.nodelay(0)
        self.setupAndDrawScreen()

        self.run()

    def setupAndDrawScreen(self):
        self.maxY, self.maxX = self.stdscr.getmaxyx()

        self.headWin = curses.newwin(1, self.maxX, 0, 0)
        self.bodyWin = curses.newwin(self.maxY - 2, self.maxX, 1, 0)
        self.footerWin = curses.newwin(1, self.maxX, self.maxY - 1, 0)
        self.initHead()
        self.initBody()
        self.initFooter()

        self.log.setScreen(self.footerWin)

        #self.stdscr.timeout(100)
        self.bodyWin.keypad(1)

        #self.stdscr.noutrefresh()

        curses.doupdate()

    def initHead(self):
        from pyradio import version

        info = " PyRadio {0} ".format(version)
        self.headWin.addstr(0, 0, info, curses.color_pair(4))
        rightStr = "www.coderholic.com/pyradio"
        self.headWin.addstr(0, self.maxX - len(rightStr) - 1, rightStr,
                            curses.color_pair(2))
        self.headWin.bkgd(' ', curses.color_pair(7))
        self.headWin.noutrefresh()

    def initBody(self):
        """ Initializes the body/story window """
        #self.bodyWin.timeout(100)
        #self.bodyWin.keypad(1)
        self.bodyMaxY, self.bodyMaxX = self.bodyWin.getmaxyx()
        self.bodyWin.noutrefresh()
        self.refreshBody()

    def initFooter(self):
        """ Initializes the body/story window """
        self.footerWin.bkgd(' ', curses.color_pair(7))
        self.footerWin.noutrefresh()

    def refreshBody(self):
        self.bodyWin.erase()
        self.bodyWin.box()
        self.bodyWin.move(1, 1)
        maxDisplay = self.bodyMaxY - 1
        for lineNum in range(maxDisplay - 1):
            i = lineNum + self.startPos
            if i < len(self.stations):
                self.__displayBodyLine(lineNum, self.stations[i])
        self.bodyWin.refresh()

    def __displayBodyLine(self, lineNum, station):
        col = curses.color_pair(5)

        if lineNum + self.startPos == self.selection and \
                self.selection == self.playing:
            col = curses.color_pair(9)
            self.bodyWin.hline(lineNum + 1, 1, ' ', self.bodyMaxX - 2, col)
        elif lineNum + self.startPos == self.selection:
            col = curses.color_pair(6)
            self.bodyWin.hline(lineNum + 1, 1, ' ', self.bodyMaxX - 2, col)
        elif lineNum + self.startPos == self.playing:
            col = curses.color_pair(4)
            self.bodyWin.hline(lineNum + 1, 1, ' ', self.bodyMaxX - 2, col)
        line = "{0}. {1}".format(lineNum + self.startPos + 1, station[0])
        self.bodyWin.addstr(lineNum + 1, 1, line, col)

    def run(self):

        if not self.play is False:
            num = (self.play and (int(self.play) - 1)
                   or random.randint(0, len(self.stations)))
            self.setStation(num)
            self.playSelection()
            self.refreshBody()

        while True:
            try:
                c = self.bodyWin.getch()
                ret = self.keypress(c)
                if (ret == -1):
                    return
            except KeyboardInterrupt:
                break

    def setStation(self, number):
        """ Select the given station number """
        # If we press up at the first station, we go to the last one
        # and if we press down on the last one we go back to the first one.
        if number < 0:
            number = len(self.stations) - 1
        elif number >= len(self.stations):
            number = 0

        self.selection = number

        maxDisplayedItems = self.bodyMaxY - 2

        if self.selection - self.startPos >= maxDisplayedItems:
            self.startPos = self.selection - maxDisplayedItems + 1
        elif self.selection < self.startPos:
            self.startPos = self.selection

    def playSelection(self):
        self.playing = self.selection
        name = self.stations[self.selection][0]
        stream_url = self.stations[self.selection][1].strip()
        self.log.write('Playing ' + name)
        try:
            self.player.play(stream_url)
        except OSError:
            self.log.write('Error starting player.'
                           'Are you sure mplayer is installed?')

    def keypress(self, char):
        # Number of stations to change with the page up/down keys
        pageChange = 5

        if char == curses.KEY_EXIT or char == ord('q'):
            self.player.close()
            return -1

        if char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            self.playSelection()
            self.refreshBody()
            self.setupAndDrawScreen()
            return

        if char == ord(' '):
            if self.player.isPlaying():
                self.player.close()
                self.log.write('Playback stopped')
            else:
                self.playSelection()

            self.refreshBody()
            return

        if char == curses.KEY_DOWN or char == ord('j'):
            self.setStation(self.selection + 1)
            self.refreshBody()
            return

        if char == curses.KEY_UP or char == ord('k'):
            self.setStation(self.selection - 1)
            self.refreshBody()
            return

        if char == ord('+'):
            self.player.volumeUp()
            return

        if char == ord('-'):
            self.player.volumeDown()
            return

        if char == curses.KEY_PPAGE:
            self.setStation(self.selection - pageChange)
            self.refreshBody()
            return

        if char == curses.KEY_NPAGE:
            self.setStation(self.selection + pageChange)
            self.refreshBody()
            return

        if char == ord('m'):
            self.player.mute()
            return

        if char == ord('r'):
            # Pick a random radio station
            self.setStation(random.randint(0, len(self.stations)))
            self.playSelection()
            self.refreshBody()

        if char == ord('#') or char == curses.KEY_RESIZE:
            self.setupAndDrawScreen()

# pymode:lint_ignore=W901

########NEW FILE########
