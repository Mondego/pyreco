__FILENAME__ = main
"""Main function a la Guido:

    http://www.artima.com/weblogs/viewpost.jsp?thread=4829

"""
import getopt
import sys

from assertEquals.cli.reporters import detail, summarize


WINDOWS = sys.platform.find('win') == 0


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            short = "fst:x:"
            long_ = [ "find-only"
                    , "scripted"
                    , "testcase=","TestCase="
                    , "stopwords="
                     ]
            opts, args = getopt.getopt(argv[1:], short, long_)
        except getopt.error, msg:
            raise Usage(msg)

        find_only = False   # -f
        scripted = False    # -s
        stopwords = []      # -x
        testcase = None     # -t

        for opt, value in opts:
            if opt in ('-f', '--find-only'):
                find_only = True
            elif opt in ('-s', '--scripted'):
                scripted = True
            elif opt in ('-x', '--stopwords'):
                stopwords = value.split(',')
            elif opt in ('-t', '--testcase', '--TestCase'):
                testcase = value

        if len(args) == 1:
            module = args[0]
        else:
            raise Usage("Please specify a module.")

        if WINDOWS or scripted:
            if testcase is None:
                report = summarize(module, find_only, stopwords)
            else:
                report = detail(module, testcase)
            sys.stdout.write(report)
            
            tfail, terr, tall = summarize._Summarize__totals
            if tfail > 0 or terr > 0: return 2 # non-zero exit-code on errors
            else: return 0
        else:
            from assertEquals.interactive import CursesInterface
            CursesInterface(module, stopwords)

    except Usage, err:
        print >> sys.stderr, err.msg
        print >> sys.stderr, "'man 1 assertEquals' for instructions."
        return 2

########NEW FILE########
__FILENAME__ = reporters
import os
import sys
import types
import unittest
from StringIO import StringIO

from assertEquals.cli.utils import *


def detail(module_name, testcase_name):
    """Given a module name and a TestCase name, return a detail report.
    """

    # Get a TestSuite for a single TestCase.
    # ======================================

    try:
        module = load(module_name)
        testcase = getattr(module, testcase_name)
    except:
        raise ImportError("Unable to find %s in " % testcase_name +
                          "%s." % module_name)
    if not isinstance(testcase, (type, types.ClassType)):
        raise TypeError("%s is not a TestCase." % testcase_name)
    if not issubclass(testcase, unittest.TestCase):
        raise TypeError("%s is not a TestCase." % testcase_name)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(testcase)


    # Run tests.
    # ==========
    # We only write our report to stdout after the tests have been run. This is
    # necessary because we don't want to clutter the report with an program
    # output and/or pdb sessions.

    report = StringIO()
    print >> report, BANNER
    runner = unittest.TextTestRunner(report)
    runner.run(suite)
    return report.getvalue()


class _Summarize:
    """Given a dotted module name, return a summary report on its tests.

    The format of the report is:

        -------------<| assertEquals |>-------------
        <header row>
        --------------------------------------------
        <name> <passing> <failures> <errors> <total>
        --------------------------------------------
        TOTALS <passing> <failures> <errors> <total>

    Boilerplate rows are actually 80 characters long, though. <passing> is given
    as a percentage (with a terminating percent sign); the other three are given
    in absolute terms. Data rows will be longer than 80 characters iff the field
    values exceed the following character lengths:

        name        60
        failures     4
        errors       4
        total        4

    If run is False, then no statistics on passes, failures, and errors will be
    available, and the output for each will be a dash character ('-'). run
    defaults to True. All submodules will also be included in the output, unless
    their name contains a stopword.

    The report is delivered after it is fully complete. We do this rather than
    delivering data in real time in order to avoid program output and pdb
    sessions from cluttering up our report.

    This callable is implemented as a class to make testing easier. It should be
    used via the singleton named summarize.

    """

    def __init__(self):
        """
        """
        self.report = StringIO()
        self.runner = unittest.TextTestRunner(dev_null())
        self.make_suite = unittest.defaultTestLoader.loadTestsFromTestCase


    def __call__(self, module, find_only=False, stopwords=()):
        """
        """
        self.module = module
        self.find_only = find_only
        self.stopwords = stopwords

        self.find_testcases()

        self.print_header()
        self.print_body()
        self.print_footer()

        return self.report.getvalue()


    def load_testcases(self, module):
        """Given a module, return a list of TestCases defined there.

        We only keep the TestCase if it has tests.

        """
        testcases = []
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, (type, types.ClassType)):
                if issubclass(obj, unittest.TestCase):
                    for _name in dir(obj):
                        if _name.startswith('test'):
                            name_dotted = module.__name__+'.'+obj.__name__
                            testcases.append((name_dotted, obj))
                            break
        return testcases


    def find_testcases(self):
        """Store a list of TestCases below the currently named module.
        """

        basemod = load(self.module)
        testcases = self.load_testcases(basemod)

        path = os.path.dirname(basemod.__file__)
        for name in sorted(sys.modules):
            if name == basemod.__name__:
               continue
            try:
                for word in self.stopwords:
                    if word and word in name:
                        stop = True
                        raise StopWord
            except StopWord:
                continue
            if not name.startswith(self.module):
                continue
            module = sys.modules[name]
            if module is None:
                continue
            if not module.__file__.startswith(path):
                # Skip external modules that ended up in our namespace.
                continue
            testcases.extend(self.load_testcases(module))

        self.__testcases = testcases


    def print_header(self):
        """Print the report header.
        """
        print >> self.report, BANNER
        print >> self.report, HEADERS
        print >> self.report, BORDER


    def print_body(self):
        """Print the report body; set three members on self for print_footer.
        """

        tfail = terr = tall = 0

        for name, testcase in self.__testcases:

            pass5 = fail = err = 0 # FWIW: pass -> pass% -> pass5
            suite = self.make_suite(testcase)
            all = suite.countTestCases()


            # Run tests if requested.
            # =======================

            if not self.find_only:
                pass5 = fail = err = 0
                if all != 0:
                    result = self.runner.run(suite)
                    fail = len(result.failures)
                    err = len(result.errors)
                    pass5 = (all - fail - err) / float(all)
                    pass5 =  int(round(pass5*100))

                tall += all
                tfail += fail
                terr += err

            else:
                pass5 = fail = err = '-'
                tall += all


            # Format and print.
            # =================

            name = name.ljust(60)
            sfail, serr, sall = [str(s).rjust(4) for s in (fail, err, all)]
            if pass5 == '-':
                pass5 = '  - '
            else: # int
                pass5 = str(pass5).rjust(3)+'%'
            print >> self.report, name, pass5, sfail, serr, sall


        self.__totals = tfail, terr, tall


    def print_footer(self, *totals):
        """Print the report footer; uses the 3 integers set by print_body.
        """

        tfail, terr, tall = self.__totals

        if not self.find_only:
            tpass5 = 0
            if tall:
                tpass5 = (tall - tfail - terr) / float(tall)
            tpass5 = int(round(tpass5*100))
            tpass5 = str(tpass5).rjust(3)+'%'
        else:
            tfail = '-'
            terr = '-'
            tpass5 = '- '

        raw = (tpass5, tfail, terr, tall)
        tpass5, tfail, terr, tall = [str(s).rjust(4) for s in raw]

        print >> self.report, BORDER
        print >> self.report, "TOTALS".ljust(60), tpass5, tfail, terr, tall


summarize = _Summarize()

########NEW FILE########
__FILENAME__ = utils
import unittest

__all__ = ( 'BANNER', 'BORDER', 'HEADERS', 'StopWord', 'dev_null', 'flatten'
          , 'load')



C = '-'
BANNER = C*31 + "<| assertEquals |>" + C*31
BORDER = C * 80
HEADERS = ' '.join(["MODULE".ljust(60), "PASS", "FAIL", " ERR", " ALL"])


class StopWord(StandardError):
    """Signals a stop word within a dotted module name.
    """


class dev_null:
    """Output buffer that swallows everything.
    """
    def write(self, wheeeee):
        pass
    def flush(self):
        pass


def flatten(_suite):
    """Given a TestSuite, return a flattened TestSuite.
    """
    suite = unittest.TestSuite()
    for item in _suite:
        if isinstance(item, unittest.TestCase):
            suite.addTest(item)
        if isinstance(item, unittest.TestSuite):
            suite.addTests(flatten(item))
    return suite


def load(name):
    """Given a dotted name, return the last-named module instead of the first.

        http://docs.python.org/lib/built-in-funcs.html

    """
    module = __import__(name)
    for _name in name.split('.')[1:]:
        module = getattr(module, _name)
    return module

########NEW FILE########
__FILENAME__ = detail
import logging
import os
import re
import subprocess
import sys

from assertEquals.cli.utils import BANNER, BORDER, HEADERS
from assertEquals.interactive.utils import RefreshError, Process


BREAK1 = ("=" * 70) + '\n'
BREAK2 = ("-" * 70) + '\n'

ALL_RE = re.compile('Ran (\d*) test')
OBJ_RE = re.compile('\((\S)\)')
FAIL_RE = re.compile('failures=(\d*)')
ERR_RE = re.compile('errors=(\d*)')

logger = logging.getLogger('assertEquals.tests')


class Detail:
    """Represent the data from an inter-process detail() call.

    This is designed to be a persistent object. Repeated calls to refresh will
    update the dataset. Unlike Summary, there are no partial updates here. The
    assumption is that you will always want to re-run all tests at once. There
    is a show flag for each record; only items for which this are true are
    included in the name, index and __len__ calls.

    """

    module = ''     # the current module dotted module name
    data = None     # a dictionary, {name:<2-list>}:
                    #   0 'error' or 'failure'
                    #   1 full report
    names = None    # a sorted list of names for which show is True
    totals = ()     # a 4-tuple: (pass5, fail, err, all)


    def __init__(self, module):
        """
        """
        self.module = module
        self.data = {}
        self.names = []

    def __repr__(self):
        return "<Detail (%d tests)>" % len(self.names)



    # Container emulation
    # ===================

    def __getitem__(self, i):
        """Takes an int index into self.names
        """
        name = self.names[i]
        return [name] + self.data[name]

    def __len__(self):
        return len(self.names)

    def __iter__(self):
        return self.names.__iter__()


    # Main callable
    # =============

    def refresh(self):
        """Re-run our tests.
        """
        self._call()
        self._set_data()


    # Helpers
    # =======

    def _call(self):
        """Invoke a child process and return its output.

        We hand on our environment and any sys.path manipulations to the child,
        and we capture stderr as well as stdout so we can handle errors.

        """
        module, testcase = self.module.rsplit('.', 1)
        args = ( sys.executable
               , '-u' # unbuffered, so we can interact with it
               , sys.argv[0]
               , '--scripted'
               , '--testcase=%s' % testcase
               , module
                )
        environ = os.environ.copy()
        environ['PYTHONPATH'] = ':'.join(sys.path)

        proc = Process(args=args, env=environ)

        raw = proc.communicate()
        if BANNER not in raw:
            raise RefreshError(raw)
        self.__raw = raw


    def _set_data(self):
        """Extract and store data from __raw.
        """

        garbage, report = self.__raw.split(BANNER,1)
        items, result = report.rsplit(BREAK2,1)
        details = items.split(BREAK1)[1:]


        # Totals
        # ======

        m = ALL_RE.search(result)
        try:
            all = m.group(1)
        except:
            logger.debug(self.__raw)
            raise
        fail = err = '0'
        if 'FAILED' in result:
            m = FAIL_RE.search(result)
            if m is not None:
                fail = str(m.group(1))
            m = ERR_RE.search(result)
            if m is not None:
                err = str(m.group(1))
        pass5 = '0'
        if all != '0':
            pass5 = int(100 * (int(all) - int(fail) - int(err)) / float(all))
        pass5 = str(pass5) + '%'
        totals = (pass5, fail, err, all)


        # Data
        # ====

        data = {}
        for detail in details:
            flop, name, module, break2, traceback_ = detail.split(None, 4)
            if flop == 'FAIL:':
                flop = 'failure'
            elif flop == 'ERROR:':
                flop = 'error'
            name = '.'.join((module[1:-1], name))[len(self.module)+1:]
            traceback_ = traceback_.strip()
            data[name] = [flop, traceback_]


        # Update self.
        # ============

        self.totals = totals
        self.data = data
        self.names = sorted(data)
        del self.__raw

########NEW FILE########
__FILENAME__ = base
import logging
import traceback

from assertEquals.interactive.utils import CommunicationProblem


logger = logging.getLogger('assertEquals.base')


class BaseScreen:
    """This is a mixin for objects representing curses screens.

    Provides:

        H, W -- the height and width of the screen, 0-indexed
        __loop() -- main event loop; calls react()
        go() -- called by CursesInterface; returns another BaseScreen
                error handling happens here
        getsize() -- returns the (H, W) tuple
        inited -- a boolean indicating whether init() has been run
        console_mode -- a boolean indicating whether to use getch() or getstr()


    Expects:

        init() -- called after the object is created, but before entering the
                  UI event loop; not called on resizes.
        react() -- method that takes a single curses key character, and returns
                   None or another BaseScreen
        resize() -- called before init(), and again every time the terminal is
                    resized.
        ui_chars -- sequence of keys to trap

    """

    inited = False
    console_mode = False

    def go(self):
        """Interact with the user, return the next screen.
        """
        try:
            self.H = self.W = 0 # triggers a call to resize, redrawing screen
            return self.__loop()
        except KeyboardInterrupt, SystemExit:
            raise
        except CommunicationProblem, prob:
            return DebuggingScreen(self, prob.proc)
        except Exception, exc:
            if hasattr(exc, 'traceback'):
                tb = exc.traceback
            else:
                tb = traceback.format_exc()
            return ErrorScreen(self, tb)
        except:
            tb = traceback.format_exc()
            return ErrorScreen(self, tb)


    def __loop(self):
        """Main loop.
        """

        while 1:

            # React to UI events, including resizes.
            # ======================================

            H, W = self.getsize()

            if (H <= 10) or (W <= 40): # terminal is too small
                self.win.clear()
                self.win.refresh()
                msg = "Terminal too small."
                if (H == 0) or (W < len(msg)):
                    continue
                self.win.addstr(H/2,(W-len(msg))/2,msg)
                self.win.refresh()
                c = self.win.getch()
                if c == ord('q'):
                    raise KeyboardInterrupt
                continue

            elif (self.H, self.W) != (H, W): # terminal has been resized
                self.win.clear()
                self.win.refresh()
                self.H, self.W = (H, W)
                self.resize()

            elif not self.inited:
                if hasattr(self, 'init'):
                    self.init()
                self.inited = True

            else: # react to key presses
                screen = None
                if self.console_mode:
                    screen = self.react(self.win.getstr())
                else:
                    c = self.win.getch()
                    if c in self.ui_chars:
                        screen = self.react(c)
                if screen is not None:
                    return screen


    def getsize(self):
        """getmaxyx is 1-indexed, but just about everything else is 0-indexed.
        """
        H, W = self.win.getmaxyx()
        return (H-1, W-1)



# Down here to dodge circular import without repeated import.
# ===========================================================
from assertEquals.interactive.screens.error import ErrorScreen
from assertEquals.interactive.screens.debugging import DebuggingScreen

########NEW FILE########
__FILENAME__ = debugging
import curses
import logging
import traceback

from assertEquals.interactive.utils import ScrollArea
from assertEquals.interactive.screens.base import BaseScreen


logger = logging.getLogger('assertEquals.screens.debugging')


class DebuggingScreen(BaseScreen):
    """Interacts with Pdb in a child process.
    """

    console_mode = True

    def __init__(self, screen, proc):
        """Takes the screen where the error occured and a Process object.
        """
        self.screen = screen
        self.colors = screen.colors
        self.blocks = screen.blocks
        self.proc = proc
        self.win = self.screen.win

        curses.nocbreak()
        curses.echo()
        curses.curs_set(1)
        self.win.idlok(1)
        self.win.scrollok(1)


    # BaseScreen contracts
    # ====================

    def init(self):
        self.win.addstr(0,0,self.proc.intro)
        self.win.refresh()

    def resize(self):
        pass

    def react(self, s):
        """Given an input string, proxy it to the child process.
        """
        if not self.proc.stdin.closed:
            output = self.proc.communicate(s)
        if self.proc.poll() is None:    # not done yet, write to screen
            self.win.addstr(output)
            self.win.refresh()
        else:                           # all done, exit cleanly
            curses.cbreak()
            curses.noecho()
            curses.curs_set(0)
            self.win.idlok(0)
            self.win.scrollok(0)
            return self.screen

########NEW FILE########
__FILENAME__ = detail
import Queue
import curses
import logging
import traceback
from curses import ascii

from assertEquals.interactive.detail import Detail
from assertEquals.interactive.utils import Spinner, ScrollArea, format_tb
from assertEquals.interactive.screens.base import BaseScreen
from assertEquals.interactive.screens.error import ErrorScreen


logger = logging.getLogger('assertEquals.screens.detail')

TESTS = 'tests'
RESULT = 'result'


class DetailScreen(BaseScreen):
    """Represent a detail report for a specific module.

        F5/space -- rerun the tests for this module


    """

    banner = " assertEquals " # shows up at the top
    bottomrows = 3  # the number of boilerplate rows at the bottom
    toprows = 3     # the number of boilerplate rows at the top of the screen
    focus = TESTS   # the currently selected ScrollArea: tests/result
    tests = None    # the left ScrollArea
    result = None   # the right ScrollArea
    detail = None   # a Detail instance
    curresult = ()  # list of lines in the currently displayed result text
    selected = ''   # the name of the currently selected test


    def __init__(self, summary):
        """Takes a dotted module name.
        """
        self.summary = summary
        self.win = summary.win
        self.base = summary.selected
        self.colors = summary.colors
        self.blocks = summary.blocks
        self.spinner = Spinner(self.spin)
        self.detail = Detail(self.base)
        self.refresh()


    # BaseScreen contracts
    # ====================

    ui_chars = ( ord('q')
               , ord(' ')
               , curses.KEY_F5
               , curses.KEY_BACKSPACE
               , curses.KEY_ENTER
               , curses.KEY_UP
               , curses.KEY_DOWN
               , curses.KEY_LEFT
               , curses.KEY_RIGHT
               , curses.KEY_PPAGE
               , curses.KEY_NPAGE
               , curses.KEY_HOME
               , curses.KEY_END
               , ascii.BS
               , ascii.TAB
               , ascii.LF
               , ascii.ESC
                )

    def init(self):
        if self.detail.names:
            self.selected = self.detail.names[0]
        self.populate()
        self.draw_content()

    def resize(self):
        c1h = c2h = self.H - self.toprows - self.bottomrows
        c1w = (self.W/2) - 5
        c2w = self.W - c1w - 5 - 3
        self.c1 = (c1h, c1w)
        self.c2 = (c2h, c2w)
        self.draw_frame()
        if self.inited:
            self.populate()
            self.draw_content()

    def react(self, c):

        # Commands that do work
        # =====================

        if c in ( ord('q')                      # back to summary
                , curses.KEY_BACKSPACE
                , ascii.ESC
                , ascii.BS
                , curses.KEY_LEFT):
            return self.summary

        elif c in ( curses.KEY_ENTER            # forward to traceback
                  , ascii.LF
                  , curses.KEY_RIGHT
                   ):
            if self.selected == '':
                return StandardError("No test selected.")
            else:
                traceback_ = self.detail.data[self.selected][1]
                return ErrorScreen(self, traceback_)

        elif c in (ord(' '), curses.KEY_F5):    # stay put and refresh
            self.spinner(self.refresh)
            if self.detail.totals[0] == '100%': # all tests passed!
                return self.summary
            if self.selected not in self.detail.names:
                self.selected = self.detail.names[0]
            self.populate()


        # Focus/paging commands
        # =====================

        elif c == ascii.TAB:
            self.focus = (self.focus == RESULT) and TESTS or RESULT

        elif self.focus == TESTS:
            if c == curses.KEY_UP:      # up
                self.tests.scroll(-1)
            elif c == curses.KEY_DOWN:  # down
                self.tests.scroll(1)
            elif c == curses.KEY_PPAGE: # page up
                self.tests.page_up()
            elif c == curses.KEY_NPAGE: # page down
                self.tests.page_down()
            elif c == curses.KEY_HOME:  # home
                self.tests.home()
            elif c == curses.KEY_END:   # down
                self.tests.end()
        else:
            if c == curses.KEY_UP:      # up
                self.result.move_cursor(0)
                self.result.scroll(-1)
            elif c == curses.KEY_DOWN:  # down
                self.result.move_cursor(self.result.numrows-1)
                self.result.scroll(1)
            elif c == curses.KEY_PPAGE: # page up
                self.result.page_up()
            elif c == curses.KEY_NPAGE: # page down
                self.result.page_down()

        self.draw_content()


    # Helpers
    # =======

    def spin(self):
        """Put a 'working' indicator in the banner.

        This is called by our Spinner instance.

        """
        l = (self.W - len(self.banner)) / 2
        stop = False
        while not stop:
            for i in range(4):
                spun = "  working%s  " % ('.'*i).ljust(3)
                self.win.addstr(0,l,spun,self.colors.BLUE)
                self.win.refresh()
                try:
                    stop = self.spinner.flag.get(timeout=0.25)
                except Queue.Empty:
                    pass
        self.draw_banner()

    def populate(self):
        """[Re]create both ScrollAreas.

        In order to retain the current page and selection, we only recreate
        the tests pane if the parameters of this area have changed.

        """

        args = { 'numrows': self.c1[0]+1
               , 'numitems':len(self.detail)
               , 'toprow': self.toprows
                }

        if not self.tests:
            self.tests = ScrollArea(**args)
        else:
            for k,v in args.items():
                if getattr(self.tests, k) != v:
                    self.tests = ScrollArea(**args)
                    break

        self.populate_result()

    def populate_result(self):
        """[Re]create just the result ScrollArea.
        """
        if self.selected == '':
            curresult = ()
        else:
            traceback_ = self.detail.data[self.selected][1]
            self.curresult = format_tb(self.c2[1], traceback_)
        self.result = ScrollArea( self.c1[0]+1
                                , len(self.curresult)
                                , self.toprows
                                 )

    def refresh(self):
        """Refresh our results and update the summary too.
        """
        self.detail.refresh()
        if not self.selected:
            if self.detail.names:
                self.selected = self.detail.names[0]
        self.summary.summary.update(self.base, *self.detail.totals)


    # Writers
    # =======

    def draw_banner(self):
        l = (self.W - len(self.banner)) / 2
        self.win.addstr(0,l,self.banner,self.colors.BLUE_DIM)


    def draw_frame(self):
        """Draw the screen.
        """

        H, W = self.H, self.W
        c1h, c1w = self.c1
        c2h, c2w = self.c2


        # Background and border
        # =====================

        color = self.colors.WHITE

        self.win.bkgd(' ')
        self.win.border() # not sure how to make this A_BOLD
        self.win.addch(0,0,curses.ACS_ULCORNER,color)
        self.win.addch(0,W,curses.ACS_URCORNER,color)
        self.win.addch(H,0,curses.ACS_LLCORNER,color)
        #self.win.addch(H,W,curses.ACS_LRCORNER,color) error! why?
        for i in range(1,W):
            self.win.addch(0,i,curses.ACS_HLINE,color)
            self.win.addch(H,i,curses.ACS_HLINE,color)
        for i in range(1,H):
            self.win.addch(i,0,curses.ACS_VLINE,color)
            self.win.addch(i,W,curses.ACS_VLINE,color)

        # headers bottom border
        self.win.addch(2,0,curses.ACS_LTEE,color)
        for i in range(0,W-1):
            self.win.addch(2,i+1,curses.ACS_HLINE,color)
        self.win.addch(2,W,curses.ACS_RTEE,color)

        # footer top border
        self.win.addch(H-2,0,curses.ACS_LTEE,color)
        for i in range(0,W-1):
            self.win.addch(H-2,i+1,curses.ACS_HLINE,color)
        self.win.addch(H-2,W,curses.ACS_RTEE,color)

        # column border
        bw = c1w+5
        self.win.vline(3,bw,curses.ACS_VLINE,H-5,color)
        self.win.addch(2,bw,curses.ACS_TTEE,color)
        self.win.addch(H-2,bw,curses.ACS_BTEE,color)


        # Banner text and column headers
        # ==============================

        l = (W - len(self.banner)) / 2
        r = l + len(self.banner)
        self.win.addch(0,l-2,curses.ACS_LARROW,color)
        self.win.addch(0,l-1,curses.ACS_VLINE,color)
        self.draw_banner()
        self.win.addch(0,r,curses.ACS_VLINE,color)
        self.win.addch(0,r+1,curses.ACS_RARROW,color)


        # Commit our changes.
        # ===================

        self.win.refresh()


    def draw_content(self):
        """Erase the current listing and redraw.
        """

        W = self.W
        c1h, c1w = self.c1
        c2h, c2w = self.c2


        # Clear both panes and draw scrollbar(s).
        # =======================================

        if self.focus == TESTS:
            tests_scrollbg_color = self.colors.BLUE
            tests_scrollbar_color = self.blocks.BLUE
            result_scrollbg_color = self.colors.GRAY
            result_scrollbar_color = self.blocks.GRAY
        else:
            tests_scrollbg_color = self.colors.GRAY
            tests_scrollbar_color = self.blocks.GRAY
            result_scrollbg_color = self.colors.BLUE
            result_scrollbar_color = self.blocks.BLUE

        bg = curses.ACS_CKBOARD

        for i in range(self.toprows, self.toprows+self.c1[0]+1):
            self.win.addstr(i,1,' '*(c1w+4))
            self.win.addstr(i,c1w+6,' '*(c2w+2))

            if self.tests.bar is None:
                self.win.addch(i,0,curses.ACS_VLINE,self.colors.WHITE)
            elif i in self.tests.bar:
                self.win.addstr(i,0,' ',tests_scrollbar_color)
            else:
                self.win.addch(i,0,bg,tests_scrollbg_color)

            if self.result.bar is None:
                self.win.addch(i,W,curses.ACS_VLINE,self.colors.WHITE)
            elif i in self.result.bar:
                self.win.addstr(i,W,' ',result_scrollbar_color)
            else:
                self.win.addch(i,W,bg,result_scrollbg_color)


        # tests
        # =====

        if self.tests.numitems != 0:
            for index, rownum  in self.tests:
                self.draw_row(index, rownum)
            selected = ''
            if self.focus == TESTS:
                self.selected = self.detail.names[self.tests.curitem]
                self.populate_result()


        # result
        # ======

        color = self.colors.GRAY
        if self.focus == RESULT:
            color = self.colors.WHITE
        for index, rownum in self.result:
            self.win.addstr(rownum,c1w+7,self.curresult[index],color)


        # Totals
        # ======

        pass5, fail, err, all = self.detail.totals

        color = self.colors.RED
        if pass5 == '100%':
            color = self.colors.GREEN

        if len(fail) > 4:
            fail = '9999'
        if len(err) > 4:
            err = '9999'
        if len(all) > 4:
            all = '9999'

        h = self.H-1
        w = self.W-21
        self.win.addstr(h,w,pass5.rjust(4),color)
        self.win.addstr(h,w+5,fail.rjust(4),color)
        self.win.addstr(h,w+10,err.rjust(4),color)
        self.win.addstr(h,w+15,all.rjust(4),color)

        base = self.base
        w = w-4
        if len(base) > w:
            base = base[:w-3] + '...'
        base = base.ljust(w)
        self.win.addstr(self.H-1,3,base,color)


        # Commit changes.
        # ===============

        self.win.refresh()


    def draw_row(self, index, rownum):
        """Given two ints, write a row to the screen.

        The first int is the index into self.names. The second is the number of
        the row on the screen to write to. Both are 0-indexed.

        """

        c1h, c1w = self.c1
        c2h, c2w = self.c2

        name, flub, result = self.detail[index]


        # Determine highlighting for this row.
        # ====================================

        if self.focus == RESULT:
            bullet_color = self.colors.GRAY
            if flub == 'error':
                color = self.colors.YELLOW_DIM
            elif flub == 'failure':
                color = self.colors.RED_DIM
            else:
                color = self.colors.WHITE_DIM
        else:
            bullet_color = self.colors.BLUE
            if flub == 'error':
                color = self.colors.YELLOW
            elif flub == 'failure':
                color = self.colors.RED
            else:
                color = self.colors.WHITE


        # Test name and bullets
        # =====================

        if len(name) > c1w:
            name = name[:c1w-3] + '...'
        name = name.ljust(c1w)
        self.win.addstr(rownum,3,name,color)

        l = ' '
        r = ' '
        if index == self.tests.curitem:
            l = curses.ACS_RARROW
            r = curses.ACS_LARROW
        self.win.addch(rownum,1,l,bullet_color)
        self.win.addch(rownum,c1w+4,r,bullet_color)


########NEW FILE########
__FILENAME__ = error
import curses
import logging
import traceback
from curses import ascii

from assertEquals.interactive.utils import ScrollArea, format_tb
from assertEquals.interactive.screens.base import BaseScreen


logger = logging.getLogger('assertEquals.screens.error')


class ErrorScreen(BaseScreen):
    """Display a traceback within curses.
    """

    def __init__(self, screen, traceback_):
        """Takes the screen where the error occured and the traceback.
        """
        self.screen = screen
        self.colors = screen.colors
        self.blocks = screen.blocks
        self.traceback_ = traceback_
        self.win = self.screen.win
        self.win.clear()
        self.win.refresh()


    # BaseScreen contracts
    # ====================

    ui_chars = ( ord('q')
               , curses.KEY_UP
               , curses.KEY_DOWN
               , curses.KEY_LEFT
               , curses.KEY_PPAGE
               , curses.KEY_NPAGE
               , curses.KEY_BACKSPACE
                )

    def resize(self):
        try:
            self.lines = format_tb(self.W-1, self.traceback_)
            self.area = ScrollArea(self.H, len(self.lines), 0)
            self.draw()
        except:
            logger.critical(traceback.format_exc())

    def react(self, c):
        try:
            if c in ( ord('q')
                    , curses.KEY_BACKSPACE
                    , ascii.BS
                    , ascii.ESC
                    , curses.KEY_LEFT
                     ):
                return self.screen
            elif c == curses.KEY_UP:    # up
                self.area.move_cursor(0)
                self.area.scroll(-1)
            elif c == curses.KEY_DOWN:  # down
                self.area.move_cursor(self.area.numrows-1)
                self.area.scroll(1)
            elif c == curses.KEY_PPAGE: # page up
                self.area.page_up()
            elif c == curses.KEY_NPAGE: # page down
                self.area.page_down()
            self.draw()
        except:
            logger.critical(traceback.format_exc())


    # Writes
    # ======

    def draw(self):

        # Clear the screen and then draw our rows.
        # ========================================

        self.win.clear()
        self.win.refresh()
        for index, rownum in self.area:
            self.win.addstr(rownum,0,self.lines[index])


        # Continuation indicators
        # =======================

        color = self.colors.BLUE

        if self.area.start > 0:
            c = curses.ACS_UARROW
        else:
            c = ord(' ')
        self.win.addch(0,self.W,c,color)

        if self.area.end_ < self.area.numitems:
            c = curses.ACS_LANTERN
        else:
            c = ord(' ')
        self.win.addch(self.H-1,self.W,c,color)


        # Commit
        # ======

        self.win.refresh()

########NEW FILE########
__FILENAME__ = summary
import Queue
import curses
import logging
import traceback
from curses import ascii

from assertEquals.interactive.summary import Summary
from assertEquals.interactive.utils import ScrollArea, Spinner
from assertEquals.interactive.screens.base import BaseScreen
from assertEquals.interactive.screens.detail import DetailScreen
from assertEquals.interactive.screens.error import ErrorScreen


logger = logging.getLogger('assertEquals.screens.summary')


class SummaryScreen(BaseScreen):
    """Represents the main module listing.

    UI-driven events:

        <ctrl>-F5 -- refresh list of modules, resetting tests to un-run
        F5/enter/space -- run selected tests, possibly going to results screen

    """

    banner = " assertEquals " # shows up at the top
    bottomrows = 3          # the number of boilerplate rows at the bottom
    listing = None          # a ScrollArea
    selected = ''           # the dotted name of the currently selected item
    summary = {}            # a data dictionary per summarize()
    toprows = 3             # the number of boilerplate rows at the top
    win = None              # a curses window


    def __init__(self, iface):
        """Takes a CursesInterface object.
        """
        self.win = iface.win
        self.module = iface.module
        self.colors = iface.colors
        self.blocks = iface.blocks
        self.stopwords = iface.stopwords
        self.spinner = Spinner(self.spin)
        self.summary = Summary(self.stopwords)


    # BaseScreen contracts
    # ====================

    ui_chars = ( ord('q')
               , ord(' ')
               , curses.KEY_F5
               , curses.KEY_ENTER
               , curses.KEY_UP
               , curses.KEY_DOWN
               , curses.KEY_RIGHT
               , curses.KEY_NPAGE
               , curses.KEY_PPAGE
               , curses.KEY_HOME
               , curses.KEY_END
               , ascii.LF
               , ascii.FF
                )

    def init(self):
        self.spinner(self.summary.refresh, self.module)
        self.update_selection()
        self.populate()
        self.draw_content()

    def resize(self):
        c1h = c2h = self.H - self.toprows - self.bottomrows
        c2w = 20
        c1w = self.W - c2w - 7
        self.c1 = (c1h, c1w)
        self.c2 = (c2h, c2w)
        self.draw_frame()
        if self.inited:
            self.populate()
            self.draw_content()

    def react(self, c):

        if c == ord('q'):
            raise KeyboardInterrupt
        elif c == ord('h'):
            return # return HelpScreen(self)


        # NB: page_up() and page_down() are switched because of observed
        # behavior. I don't know if this is a quirk of my terminal or
        # an error in ScrollArea or what. Also, I haven't observed the
        # home() and down() functions in action. Again, probably a
        # terminal quirk. UPDATE: Actually, I think it might be an error
        # in the curses docs? Or is this nomenclature just Unix lore?

        if c == curses.KEY_UP:          # up
            self.listing.scroll(-1)
        elif c == curses.KEY_DOWN:      # down
            self.listing.scroll(1)
        elif c == curses.KEY_PPAGE:     # page up
            self.listing.page_up()
        elif c == curses.KEY_NPAGE:     # page down
            self.listing.page_down()
        elif c == curses.KEY_HOME:      # home
            self.listing.home()
        elif c == curses.KEY_END:       # end
            self.listing.end()


        # Actions that do work
        # ====================

        elif c == ascii.FF:             # refresh our TestCase list
            self.reload()
        elif c in ( ord(' ')            # run tests!
                  , ascii.LF
                  , curses.KEY_ENTER
                  , curses.KEY_RIGHT
                  , curses.KEY_F5
                   ):

            # Update the summary if we are on a module/package, or go to a
            # DetailScreen if we are on a TestCase and not all tests pass.

            if self.selected:
                isTestCase = self.summary.data[self.selected][0]
                if isTestCase:          # TestCase
                    detailscreen = self.spinner(DetailScreen, self)
                    if c != ord(' '):
                        if detailscreen.detail.totals[0] != '100%':
                            return detailscreen
                else:                   # module/package
                    self.spinner( self.summary.refresh
                                , self.selected
                                , find_only=False
                                 )
                    self.update_selection()

            else:
                raise StandardError("No module selected.")


        self.draw_content()


    # Helpers
    # =======

    def reload(self):
        self.summary = Summary(self.stopwords)
        self.spinner(self.summary.refresh, self.module)
        self.update_selection()

    def populate(self):
        """[Re]create the scroll area if needed.

        In order to retain the current page and selection, we only recreate the
        pane if its size parameters have changed.

        """

        args = { 'numrows': self.c1[0]+1
               , 'numitems':len(self.summary)
               , 'toprow': self.toprows
                }

        if not self.listing:
            self.listing = ScrollArea(**args)
        else:
            for k,v in args.items():
                if getattr(self.listing, k) != v:
                    self.listing = ScrollArea(**args)
                    break


    def spin(self):
        """Put a 'working' indicator in the banner.

        This is called by our Spinner instance.

        """
        l = (self.W - len(self.banner)) / 2
        stop = False
        while not stop:
            for i in range(4):
                spun = "  working%s  " % ('.'*i).ljust(3)
                self.win.addstr(0,l,spun,self.colors.BLUE)
                self.win.refresh()
                try:
                    stop = self.spinner.flag.get(timeout=0.25)
                except Queue.Empty:
                    pass
        self.draw_banner()

    def update_selection(self):
        if (not self.selected) and self.summary.names:
            self.selected = self.summary.names[0]


    # Methods that actually write to the screen
    # =========================================

    def draw_banner(self):
        l = (self.W - len(self.banner)) / 2
        self.win.addstr(0,l,self.banner,self.colors.BLUE_DIM)


    def draw_frame(self):
        """Draw the screen.
        """

        H, W = self.H, self.W
        c1h, c1w = self.c1
        c2h, c2w = self.c2


        # Background and border
        # =====================

        bold = curses.A_BOLD

        self.win.bkgd(' ')
        self.win.border() # not sure how to make this A_BOLD
        self.win.addch(0,0,curses.ACS_ULCORNER,bold)
        self.win.addch(0,W,curses.ACS_URCORNER,bold)
        self.win.addch(H,0,curses.ACS_LLCORNER,bold)
        #self.win.addch(H,W,curses.ACS_LRCORNER,bold) error! why?
        for i in range(1,W):
            self.win.addch(0,i,curses.ACS_HLINE,bold)
            self.win.addch(H,i,curses.ACS_HLINE,bold)
        for i in range(1,H):
            self.win.addch(i,0,curses.ACS_VLINE,bold)
            self.win.addch(i,W,curses.ACS_VLINE,bold)

        # headers bottom border
        self.win.addch(2,0,curses.ACS_LTEE,bold)
        for i in range(0,W-1):
            self.win.addch(2,i+1,curses.ACS_HLINE,bold)
        self.win.addch(2,W,curses.ACS_RTEE,bold)

        # footer top border
        self.win.addch(H-2,0,curses.ACS_LTEE,bold)
        for i in range(0,W-1):
            self.win.addch(H-2,i+1,curses.ACS_HLINE,bold)
        self.win.addch(H-2,W,curses.ACS_RTEE,bold)

        # column border
        bw = (W-c2w-3)
        self.win.addch(0,bw,curses.ACS_TTEE,bold)
        self.win.vline(1,bw,curses.ACS_VLINE,H-1,bold)
        self.win.addch(2,bw,curses.ACS_PLUS,bold)
        self.win.addch(H-2,bw,curses.ACS_PLUS,bold)
        self.win.addch(H,bw,curses.ACS_BTEE,bold)


        # Banner text and column headers
        # ==============================

        l = (W - len(self.banner)) / 2
        r = l + len(self.banner)
        self.win.addch(0,l-2,curses.ACS_LARROW,bold)
        self.win.addch(0,l-1,curses.ACS_VLINE,bold)
        self.win.addch(0,r,curses.ACS_VLINE,bold)
        self.win.addch(0,r+1,curses.ACS_RARROW,bold)

        self.draw_banner()

        self.win.addstr(1,3,"TESTCASES",bold)
        self.win.addstr(1,self.W-c2w-1,"PASS",bold)
        self.win.addstr(1,self.W-c2w-1+5,"FAIL",bold)
        self.win.addstr(1,self.W-c2w-1+10," ERR",bold)
        self.win.addstr(1,self.W-c2w-1+15," ALL",bold)


        # Commit writes.
        # ==============

        self.win.refresh()


    def draw_content(self):
        """Draw the list of modules; called on almost every UI event.
        """

        W = self.W
        c1h, c1w = self.c1
        c2h, c2w = self.c2
        longname = self.selected


        # Clear listing area and draw any scrollbar.
        # ==========================================

        bg = curses.ACS_CKBOARD

        for i in range(self.toprows, self.toprows+self.listing.numrows):
            self.win.addstr(i,1,' '*(c1w+3))
            self.win.addstr(i,c1w+5,' '*(c2w+2))

            if self.listing.bar is None:
                self.win.addch(i,W,curses.ACS_VLINE,self.colors.WHITE)
            elif i in self.listing.bar:
                self.win.addstr(i,W,' ',self.blocks.BLUE)
            else:
                self.win.addch(i,W,bg,self.colors.BLUE)


        # Write listing rows if we have any.
        # ==================================
        # parent is a signal for the submodule bullets logic.

        if self.listing.numitems != 0:
            parent = ''
            for index, rownum  in self.listing:
                parent = self.draw_row(index, rownum, parent)
            self.selected = self.summary.names[self.listing.curitem]


        # Update totals.
        # ==============

        tpass5, tfail, terr, tall = self.summary.totals
        if tpass5 == '-':
            tpass5 = '- '
        if len(tfail) > 4:
            tfail = '9999'
        if len(terr) > 4:
            terr = '9999'
        if len(tall) > 4:
            tall = '9999'

        if not '%' in tpass5:
            color = self.colors.WHITE
        elif int(tfail) or int(terr):
            color = self.colors.RED
        else:
            color = self.colors.GREEN

        h = self.toprows + 1 + c1h + 1
        w = self.W-c2w-1
        self.win.addstr(h,w,tpass5.rjust(4),color)
        self.win.addstr(h,w+5,tfail.rjust(4),color)
        self.win.addstr(h,w+10,terr.rjust(4),color)
        self.win.addstr(h,w+15,tall.rjust(4),color)

        module = self.summary.module
        if len(module) > c1w:
            module = module[:c1w-3] + '...'
        module = module.ljust(c1w)
        self.win.addstr(h,3,module,color)


        # Finally, commit our writes.
        # ===========================

        self.win.refresh()


    def draw_row(self, index, rownum, parent):
        """Given two ints, write a row to the screen.

        The first int is the index into self.names. The second is the number of
        the row on the screen to write to. Both are 0-indexed. parent is a
        signal to our bullet logic (we show a secondary bullet for submodules).

        """

        c1h, c1w = self.c1
        c2h, c2w = self.c2

        name, stats, fresh = self.summary[index]


        # Pick a color, and see if we have a result to show.
        # ==================================================


        if stats is None:           # module/package

            color = self.colors.GRAY
            show_result = False

        else:                       # TestCase

            pass5, fail, err, all = stats

            if fresh is None:           # not run yet
                color = self.colors.WHITE
            elif fresh is False:        # run but not most recently
                if pass5 != '100%':
                    color = self.colors.RED_DIM
                else:
                    color = self.colors.GREEN_DIM
            elif fresh is True:         # just run
                if pass5 != '100%':
                    color = self.colors.RED
                else:
                    color = self.colors.GREEN

            show_result = True


        # Show the result if applicable.
        # ==============================

        if show_result:
            if not int(all):
                pass5 = fail = err = '-'

            if pass5 == '-':
                pass5 = '- '
            if len(fail) > 4:
                fail = '9999'
            if len(err) > 4:
                err = '9999'
            if len(all) > 4:
                all = '9999'

            w = self.W-c2w-1
            self.win.addstr(rownum,w,pass5.rjust(4),color)
            self.win.addstr(rownum,w+5,fail.rjust(4),color)
            self.win.addstr(rownum,w+10,err.rjust(4),color)
            self.win.addstr(rownum,w+15,all.rjust(4),color)


        # Short name, with indent.
        # ========================

        i = len('.'.join(self.module.split('.')[:-1]))
        parts = name[i:].lstrip('.').split('.')
        shortname = ('  '*(len(parts)-1)) + parts[-1]
        if len(shortname) > c1w:
            shortname = shortname[:c1w-3] + '...'
        shortname = shortname.ljust(c1w)
        self.win.addstr(rownum,3,shortname,color)


        # Bullet(s)
        # =========

        l = ' '
        r = ' '
        a = self.colors.BLUE
        if index == self.listing.curitem:
            if not parent:
                parent = name
            l = curses.ACS_RARROW
            r = curses.ACS_LARROW
        elif parent and name.startswith(parent):
            l = r = curses.ACS_BULLET
        self.win.addch(rownum,1,l,a)
        self.win.addch(rownum,self.W-1,r,a)


        return parent

########NEW FILE########
__FILENAME__ = summary
import logging
import os
import subprocess
import sys

from assertEquals.cli.utils import BANNER, BORDER, HEADERS
from assertEquals.interactive.utils import RefreshError, Process


logger = logging.getLogger('assertEquals.interactive.summary')


class Summary:
    """Represent the data from an inter-process summarize() call.

    This is designed to be a persistent object. Repeated calls to refresh will
    update the dataset. On partial updates, existing data will be marked as
    stale. There is also a show flag for each record; only items for which this
    are true are included in the name index and __len__ calls.

    """

    module = ''     # the current module dotted module name
    data = None     # a dictionary, {name:(stats, fresh)}:
                    #   stats: None or (pass5, fail, err, all)
                    #   fresh: None or False or True
    names = None    # a sorted list of names for which show is True
    run = True      # the current state of the run flag
    totals = ()     # a single 4-tuple per summarize()
    __lines = None  # for communication between _set_totals and _set_data
    __raw = ''      # for communication between _call and _set_data


    def __init__(self, stopwords=()):
        """Takes a sequence.
        """
        self.stopwords = stopwords
        self.data = {}
        self.totals = ()
        self.names = []


    # Container emulation
    # ===================

    def __getitem__(self, i):
        """Takes an int index into self.names
        """
        name = self.names[i]
        return [name] + self.data[name]

    def __len__(self):
        """Only count items for which show is True.
        """
        return len(self.names)

    def __iter__(self):
        return self.names.__iter__()
    iterkeys = __iter__


    # Main callable
    # =============

    def refresh(self, module, find_only=True):
        """Update our information.
        """
        self.module = module
        self.find_only = find_only

        self._call()

        self._set_stale()
        self._set_totals()
        self._set_data()


    def update(self, name, pass5, fail, err, all):
        """Given data on one testcase, update its info.

        This is called from DetailScreen.

        """
        if name not in self.data:
            raise StandardError("Running detail for module not in " +
                                "summary: %s." % name)
        self._set_stale()
        self.data[name] = [(pass5, fail, err, all), True]
        self.totals = [pass5, fail, err, all]


    # Helpers
    # =======

    def _call(self):
        """Invoke a child process and return its output.

        We hand on our environment and any sys.path manipulations to the child,
        and we capture stderr as well as stdout so we can handle errors.

        """
        args = [ sys.executable
               , '-u' # unbuffered, so we can interact with it
               , sys.argv[0]
               , '--stopwords=%s' % ','.join(self.stopwords)
               , '--scripted'
               , self.module
                ]
        if self.find_only:
            args.insert(4, '--find-only')

        environ = os.environ.copy()
        environ['PYTHONPATH'] = ':'.join(sys.path)

        proc = Process(args=args, env=environ)

        raw = proc.communicate()
        if BANNER not in raw:
            raise RefreshError(raw)
        self.__raw = raw


    def _set_stale(self):
        """Mark currently fresh data as stale.
        """
        for name, datum in self.data.iteritems():
            if datum[1] is True:
                datum[1] = False


    def _set_totals(self):
        """Given self.__raw, set totals and __lines on self.
        """
        lines = self.__raw.splitlines()
        self.totals = tuple(lines[-1].split()[1:])
        del lines[-1]
        self.__lines = lines


    def _set_data(self):
        """Extract and store data from __lines.
        """

        data = {}
        reading_report = False # ignore any output that precedes our report

        for line in self.__lines:

            # Decide if we want this line, and if so, split it on spaces.
            # ===========================================================

            line = line.strip('\n')
            if line == BANNER:
                reading_report = True
                continue
            if (not reading_report) or (not line) or line in (HEADERS, BORDER):
                continue
            tokens = line.split()


            # Convert the row to our record format.
            # =====================================
            # The raw report lists TestCases by full dotted name, but we want to
            # only show short names, and indent under a module tree. So we add
            # all parent modules to data, and set their value to (None, None)

            name = tokens[0]
            stats = tuple(tokens[1:])

            module_dotted, testcase = name.rsplit('.',1)

            parts = module_dotted.split('.')
            for i in range(len(parts),self.module.count('.'),-1):
                ancestor = '.'.join(parts[:i])
                data[ancestor] = [None, None]

            fresh = None
            if '-' not in stats:
                fresh = True

            data[name] = [stats, fresh]

        self.data.update(data)
        self.names = sorted(self.data.keys())
        del self.__lines


########NEW FILE########
__FILENAME__ = utils
import Queue
import curses
import logging
import subprocess
import textwrap
import threading
import traceback
from curses import ascii

logger = logging.getLogger('assertEquals.interactive.utils')


class Bucket:
    """
    """


class RefreshError(StandardError):
    """An error refreshing the summary.
    """
    def __init__(self, traceback):
        """Save the remote traceback.
        """
        StandardError.__init__(self)
        self.traceback = traceback


class CommunicationProblem(StandardError):
    """Wrap a Process that wants to talk.
    """
    def __init__(self, proc):
        StandardError.__init__(self)
        self.proc = proc


class Process(subprocess.Popen):
    """Represent a child process that might want to interact with us.
    """

    prompt = '(Pdb) ' # The signal that it wants to talk.
    intro = '' # If it wants to talk, this will be the first thing it said.
    interactive = False # whether or not we are interacting with the child

    def __init__(self, *args, **kwargs):
        """Extend to capture I/O streams.
        """
        _kwargs = { 'stdin':subprocess.PIPE
                  , 'stdout':subprocess.PIPE
                  , 'stderr':subprocess.STDOUT
                   }
        kwargs.update(_kwargs)
        subprocess.Popen.__init__(self, *args, **kwargs)


    def __str__(self):
        return "<Process #%d>" % self.pid
    __repr__ = __str__


    def communicate(self, input=None):
        """Override to support Pdb interaction.

        If input is None, then we will raise ourselves if the process wants to
        interact. Otherwise, we will return the last thing it said. To see if
        the conversation is over, use self.poll().

        """

        if input is not None:
            self.stdin.write(input + '\n')

        output = []
        i = len(self.prompt)

        while 1:
            retcode = self.poll()
            if retcode is None:
                # Conversation not done; check to see if it's our turn to talk.
                if len(output) >= i:
                    latest = ''.join(output[-i:])
                    if latest == self.prompt:
                        self.interactive = True
                        break
                output.append(self.stdout.read(1))
            else:
                # The process is done; assume we can read to EOF.
                output.append(self.stdout.read())
                break

        output = ''.join(output)
        if self.interactive and (input is None):
            self.intro = output
            raise CommunicationProblem(self)
        else:
            return output


class Spinner:
    """Represent a random work indicator, handled in a separate thread.
    """

    def __init__(self, spin):
        """Takes a callable that actually draws/undraws the spinner.
        """
        self.spin = spin
        self.flag = Queue.Queue(1)

    def start(self):
        """Show a spinner.
        """
        self.thread = threading.Thread(target=self.spin)
        self.thread.start()

    def stop(self):
        """Stop the spinner.
        """
        self.flag.put(True)
        self.thread.join()

    def __call__(self, call, *args, **kwargs):
        """Convenient way to run a routine with a spinner.
        """
        self.start()
        try:
            return call(*args, **kwargs)
        finally:
            self.stop()




class DoneScrolling(StandardError):
    """Represents the edge of a scrolling area.
    """


class ScrollArea:
    """Represents a scrollable portion of a screen.
    """

    numrows = 0         # number of viewable rows; len semantics
    cursor = 0          # index of the currently curitem row; 0-indexed
    toprow = 0          # index of our top row within the window; 0-indexed

    numitems = 0        # the total number of items in the list; len semantics
    curitem = 0         # index of the currently curitem item; 0-indexed
    start = end_ = 0    # coordinates in your list of items; slice semantics
    bar = None          # a range() within range(numrows) for which a scrollbar
                        #   should be drawn

    def __init__(self, numrows, numitems, toprow):
        """
        """
        self.numrows = numrows
        self.numitems = numitems
        self.toprow = toprow
        if self.numitems < self.numrows:
            self.end_ = self.numitems
        else:
            self.end_ = self.numrows
        self.update()

    def __repr__(self):
        return "<ScrollArea %s>" % str(self.stat())
    __str__ = __repr__


    # Container emulation
    # ===================
    # As a container, we are a list of 2-tuples: (index, rownum)
    #   index -- an index of an item currently being displayed
    #   rownum -- a row number relative to the current window object

    def __list(self):
        def rownum(i):
            return self.toprow + i - self.start
        return [(i, rownum(i)) for i in range(self.start, self.end_)]

    def __iter__(self):
        return iter(self.__list())

    def __len__(self):
        return len(self.__list())


    # Basic API
    # =========

    def scroll_one(self, up=False):
        """Scroll the viewport by one row.
        """

        if self.numitems == 0: # short-circuit
            raise DoneScrolling

        if up: # scroll up
            if self.cursor == 0: # top of viewport
                if self.start == 0: # top of list
                    raise DoneScrolling
                else: # not top of list
                    self.start -= 1
                    if self.end_ - self.start > self.numrows:
                        self.end_ -= 1
            else: # not top of viewport
                self.cursor -= 1

        else: # scroll down
            if self.curitem + 1 == self.numitems: # bottom of list
                raise DoneScrolling
            else: # not bottom of list
                if self.cursor + 1 == self.numrows: # bottom of viewport
                    self.start += 1
                    self.end_ += 1
                else: # not bottom of viewport
                    self.cursor += 1

        self.update()


    def scroll(self, delta):
        """Support multi-line scrolling.
        """
        up = delta < 0
        delta = abs(delta)
        try:
            for i in range(delta):
                self.scroll_one(up)
        except DoneScrolling:
            self._refuse()


    # Extended API
    # ============

    def page_up(self):
        """Scroll up one page.
        """
        if self.numitems == 0:              # empty page
            self._refuse()
        elif self.numitems <= self.numrows: # partial/single page
            self.cursor = 0
            self._refuse()
        elif self.numitems > self.numrows:  # multiple pages

            # already at top
            if self.curitem == 0:
                self.cursor = 0
                self._refuse()

            # less than a full page above
            elif self.start+1 - self.numrows < 0:
                self.start = 0
                self.end_ = self.numrows
                self.cursor = 0
                self._refuse()

            # exactly one page above
            elif self.start+1 - self.numrows == 0:
                self.start = 0
                self.end_ = self.numrows
                self.cursor = 0

            # more than one page above
            else:
                self.start -= self.numrows
                self.end_ = self.start + self.numrows

        self.update()


    def page_down(self):
        """
        """
        if self.numitems == 0:              # empty page
            self._refuse()
        elif self.numitems <= self.numrows: # partial/single page
            self.cursor = self.numitems - 1
            self._refuse()
        elif self.numitems > self.numrows:  # multiple pages

            #if hasattr(self, 'flag'):
            #    import pdb; pdb.set_trace()

            # already on the last page (exact or partial)
            if self.numitems - self.start <= self.numrows:
                self.start = self.numitems - 1
                self.end_ = self.numitems
                self.cursor = 0
                self._refuse()

            # less than a full page left
            elif self.numitems - self.end_ < self.numrows:
                self.start = self.end_
                self.end_ = self.numitems
                rows_displayed = self.end_ - self.start
                if self.cursor > rows_displayed:
                    self.cursor = rows_displayed - 1

            # one full page or more left
            else:
                self.start += self.numrows
                self.end_ += self.numrows

        self.update()


    def home(self):
        """
        """
        if self.numitems == 0:              # empty page
            self._refuse()
        elif self.numitems <= self.numrows: # partial/single page
            if self.cursor == 0:
                self._refuse()
            else:
                self.cursor = 0
        elif self.numitems > self.numrows:  # multiple pages
            self.start = 0
            self.end_ = self.start + self.numrows
            self.cursor = 0
            if self.curitem == 0:
                self._refuse()
        self.update()


    def end(self):
        """
        """
        if self.numitems == 0:              # empty page
            self._refuse()
        elif self.numitems <= self.numrows: # partial/single page
            if self.cursor == self.numitems - 1:
                self._refuse()
            else:
                self.cursor = self.numitems - 1
        elif self.numitems > self.numrows:  # multiple pages
            self.cursor = self.numrows - 1
            self.end_ = self.numitems
            self.start = self.end_ - self.numrows
            if self.curitem == self.numitems - 1:
                self._refuse()
        self.update()


    # Helpers
    # =======

    def _refuse(self):
        """Factored out for easier testing.
        """
        self.update()
        self.refuse()

    def refuse(self):
        """Factored out for easier testing.
        """
        curses.beep()

    def update(self):
        """Update self.bar and self.curitem.
        """
        if self.numrows > self.numitems:
            bar = None
        else:
            numitems_f = float(self.numitems)
            size = int((self.numrows/numitems_f) * self.numrows)
            start = int((self.start/numitems_f) * self.numrows)
            end = start + size + 1
            if end > self.numrows:
                end = self.numrows
            bar = range(start+self.toprow, end+self.toprow)
        self.bar = bar
        self.curitem = self.start + self.cursor

    def stat(self):
        return ( self.numrows   # 1-indexed
               , self.cursor    # 0-indexed
               , self.numitems  # 1-indexed
               , self.start     # 0-indexed
               , self.end_      # 0-indexed
               , self.curitem   # 0-indexed
               , self.bar       # 0-indexed
                )

    def move_cursor(self, rownum):
        """Move the cursor to a specific row, selecting the item there.
        """
        if (self.numrows < self.numitems) and (rownum in range(self.numrows)):
            self.cursor = rownum
            if rownum not in [i[1] for i in self]:
                self._refuse()
            else:
                self.update()
        else:
            self._refuse()


wrapper_1 = textwrap.TextWrapper( initial_indent=''
                                , subsequent_indent=''
                                , break_long_words=True
                                 )
wrapper_2 = textwrap.TextWrapper( initial_indent='  '
                                , subsequent_indent='    '
                                , break_long_words=True
                                 )

def format_tb(width, traceback_):
    """Given a traceback, return a list of strings.

    I would like to format tracebacks differently, but that will have to
    wait for another day.

    """
    wrapper_1.width = wrapper_2.width = width
    raw = traceback_.splitlines()
    lines = wrapper_1.wrap(raw[0])
    lines.append('')
    for line in raw[1:-1]:
        line = line.strip()
        lines.extend(wrapper_2.wrap(line))
        if not line.startswith('File'):
            lines.append('')
    lines.extend(wrapper_1.wrap(raw[-1]))
    return lines

########NEW FILE########
__FILENAME__ = cli
import sys
import unittest

from assertEquals.cli.reporters import detail, _Summarize
from assertEquals.tests.utils import reportersTestCase


OUTPUT_START="""\
-------------------------------<| assertEquals |>-------------------------------
.EF..
======================================================================
ERROR: test_errs (assertEqualsTests.TestCase)
----------------------------------------------------------------------
Traceback (most recent call last):"""; """
<snip>
StandardError: heck

======================================================================
FAIL: test_fails (assertEqualsTests.TestCase)
----------------------------------------------------------------------
Traceback (most recent call last):
<snip>
AssertionError

----------------------------------------------------------------------
Ran 5 tests in 0.002s"""; OUTPUT_END="""

FAILED (failures=1, errors=1)
"""


REPORT_SUCCESS = """\
-------------------------------<| assertEquals |>-------------------------------
..
----------------------------------------------------------------------
Ran 2 tests in 0.000s

OK
"""



class Detail(reportersTestCase):

    def testOnlyModuleNoTestCaseTriggersNameError(self):
        self.assertRaises(TypeError, detail, 'needsADot')

    def testBadModuleTriggersImportError(self):
        self.assertRaises(ImportError, detail, 'probablyDoesntExist', 'TestCase')

    def testBadTestCaseNameAlsoTriggersImportError(self):
        self.assertRaises(ImportError, detail, 'assertEqualsTests', 'ToastCase')

    def testBadTestCaseTriggersTypeError(self):
        self.assertRaises(TypeError, detail, 'assertEqualsTests', 'itDoesExist')

    def testReturnsNormalUnitTestOutputWithOurBanner(self):
        actual = detail('assertEqualsTests', 'TestCase')
        start = actual[:len(OUTPUT_START)]
        end = actual[-len(OUTPUT_END):]
        self.assertEqual(start, OUTPUT_START)
        self.assertEqual(end, OUTPUT_END)

    def testDoesntContainProgramOutput(self):
        actual = detail('assertEqualsTests', 'TestCase')
        start = actual[:len(OUTPUT_START)]
        end = actual[-len(OUTPUT_END):]
        self.assertEqual(start, OUTPUT_START)
        self.assertEqual(end, OUTPUT_END)

    def testTestCaseInSubmodulesWorks(self):
        expected = REPORT_SUCCESS
        actual = detail('assertEqualsTests.itDoesExist', 'TestCase')
        self.assertEqual(expected, actual)




HEADER = """\
-------------------------------<| assertEquals |>-------------------------------
MODULE                                                       PASS FAIL  ERR  ALL
--------------------------------------------------------------------------------
"""

BODY = """\
assertEqualsTests.TestCase                                       60%    1    1    5
assertEqualsTests.itDoesExist.TestCase                          100%    0    0    2
assertEqualsTests.itDoesExist.TestCase2                         100%    0    0    1
assertEqualsTests.subpkg.TestCase                               100%    0    0    2
"""
BODY_FIND = """\
assertEqualsTests.TestCase                                        -     -    -    5
assertEqualsTests.itDoesExist.TestCase                            -     -    -    2
assertEqualsTests.itDoesExist.TestCase2                           -     -    -    1
assertEqualsTests.subpkg.TestCase                                 -     -    -    2
"""
BODY_DOTTED_RUN_VERBOSE = """\
assertEqualsTests.itDoesExist.TestCase                          100%    0    0    2
assertEqualsTests.itDoesExist.TestCase2                         100%    0    0    1
"""


TOTALS_BASIC = """\
--------------------------------------------------------------------------------
TOTALS                                                        50%    4    5   18
"""
TOTALS_BASIC_NO_RUN = """\
--------------------------------------------------------------------------------
TOTALS                                                         -     -    -   18
"""
TOTALS_ZERO = """\
--------------------------------------------------------------------------------
TOTALS                                                         0%    0    0    0
"""
TOTALS_ZERO_NO_RUN = """\
--------------------------------------------------------------------------------
TOTALS                                                         -     -    -    0
"""
TOTALS_ZERO_PERCENT = """\
--------------------------------------------------------------------------------
TOTALS                                                         0%    5    5   10
"""
TOTALS_ZERO_PERCENT_NO_RUN = """\
--------------------------------------------------------------------------------
TOTALS                                                         -     -    -   10
"""
TOTALS_ALL_PASSING = """\
--------------------------------------------------------------------------------
TOTALS                                                       100%    0    0   10
"""
TOTALS_ALL_PASSING_NO_RUN = """\
--------------------------------------------------------------------------------
TOTALS                                                         -     -    -   10
"""
TOTALS_SUMMARIZE = """\
--------------------------------------------------------------------------------
TOTALS                                                        80%    1    1   10
"""

SUMMARIZE = HEADER + BODY + TOTALS_SUMMARIZE


class Summary(reportersTestCase):

    def setUpUp(self):
        self.summarize = _Summarize()
        self.summarize.module = 'assertEqualsTests'
        self.summarize.find_only = False
        self.summarize.stopwords = ()


    # __call__
    # ========

    def testSummarize(self):
        expected = SUMMARIZE
        actual = self.summarize('assertEqualsTests')
        self.assertEqual(expected, actual)

    def testTestCaseTriggersImportError(self):
        self.assertRaises(ImportError, self.summarize, 'assertEqualsTests.TestCase')


    # load_testcases
    # ==============

    def testLoadTestCases(self):
        mod = __import__('assertEqualsTests')
        expected = [('assertEqualsTests.TestCase', mod.TestCase)]
        actual = self.summarize.load_testcases(mod)
        self.assertEqual(expected, actual)

    def testLoadTestCasesDottedAndMultiple(self):
        mod = __import__('assertEqualsTests.itDoesExist')
        expected = [ ( 'assertEqualsTests.itDoesExist.TestCase'
                     , mod.itDoesExist.TestCase
                      )
                   , ( 'assertEqualsTests.itDoesExist.TestCase2'
                     , mod.itDoesExist.TestCase2
                      )
                    ]
        actual = self.summarize.load_testcases(mod.itDoesExist)
        self.assertEqual(expected, actual)

    def testLoadTestCasesOnlyIfTheyHaveTests(self):
        mod = __import__('assertEqualsTests.subpkg')
        reload(mod.subpkg)
        expected = [ ( 'assertEqualsTests.subpkg.TestCase'
                     , mod.subpkg.TestCase
                      )
                    ]
        actual = self.summarize.load_testcases(mod.subpkg)
        self.assertEqual(expected, actual)
        self.setUp()


    # find_testcases
    # ==============

    def testFindTestCases(self):
        self.summarize.module = 'assertEqualsTests'
        self.summarize.find_testcases()
        mod = __import__('assertEqualsTests')
        expected = [ ( 'assertEqualsTests.TestCase'
                     , mod.TestCase
                      )
                   , ( 'assertEqualsTests.itDoesExist.TestCase'
                     , mod.itDoesExist.TestCase
                      )
                   , ( 'assertEqualsTests.itDoesExist.TestCase2'
                     , mod.itDoesExist.TestCase2
                      )
                   , ( 'assertEqualsTests.subpkg.TestCase'
                     , mod.subpkg.TestCase
                      )
                    ]
        actual = self.summarize._Summarize__testcases
        self.assertEqual(expected, actual)

    def testFindTestCasesStopWords(self):
        self.summarize.module = 'assertEqualsTests'
        self.summarize.stopwords = ('Does',)
        self.summarize.find_testcases()
        mod = __import__('assertEqualsTests')
        expected = [ ('assertEqualsTests.TestCase', mod.TestCase)
                   , ('assertEqualsTests.subpkg.TestCase', mod.subpkg.TestCase)]
        actual = self.summarize._Summarize__testcases
        self.assertEqual(expected, actual)

    def testFindTestCasesEmptyStopWordsOk(self):
        self.summarize.module = 'assertEqualsTests'
        self.summarize.stopwords = ('',)
        self.summarize.find_testcases()
        mod = __import__('assertEqualsTests')
        expected = [ ( 'assertEqualsTests.TestCase'
                     , mod.TestCase
                      )
                   , ( 'assertEqualsTests.itDoesExist.TestCase'
                     , mod.itDoesExist.TestCase
                      )
                   , ( 'assertEqualsTests.itDoesExist.TestCase2'
                     , mod.itDoesExist.TestCase2
                      )
                   , ( 'assertEqualsTests.subpkg.TestCase'
                     , mod.subpkg.TestCase
                      )
                    ]
        actual = self.summarize._Summarize__testcases
        self.assertEqual(expected, actual)


    # print_header
    # ============

    def testPrintHeader(self):
        self.summarize.print_header()
        actual = self.summarize.report.getvalue()
        expected = HEADER
        self.assertEqual(expected, actual)


    # print_body
    # ==========

    def testPrintBody(self):
        self.summarize.module = 'assertEqualsTests'
        self.summarize.find_testcases()
        self.summarize.print_body()

        expected = BODY
        actual = self.summarize.report.getvalue()
        self.assertEqual(expected, actual)

        expected = (1, 1, 10)
        actual = self.summarize._Summarize__totals
        self.assertEqual(expected, actual)

    def testPrintBodyNoRun(self):
        self.summarize.module = 'assertEqualsTests'
        self.summarize.find_only = True
        self.summarize.find_testcases()
        self.summarize.print_body()

        expected = BODY_FIND
        actual = self.summarize.report.getvalue()
        self.assertEqual(expected, actual)

        expected = (0, 0, 10)
        actual = self.summarize._Summarize__totals
        self.assertEqual(expected, actual)

    def testPrintBodyBaseIsDotted(self):
        self.summarize.module = 'assertEqualsTests.itDoesExist'
        self.summarize.find_testcases()
        self.summarize.quiet = False
        self.summarize.print_body()

        expected = BODY_DOTTED_RUN_VERBOSE
        actual = self.summarize.report.getvalue()
        self.assertEqual(expected, actual)

        expected = (0, 0, 3)
        actual = self.summarize._Summarize__totals
        self.assertEqual(expected, actual)



    # print_footer
    # ============

    def testPrintFooterBasicTotalsWithRun(self):
        self.summarize._Summarize__totals = (4, 5, 18)
        self.summarize.print_footer()
        actual = self.summarize.report.getvalue()
        expected = TOTALS_BASIC
        self.assertEqual(expected, actual)

    def testPrintFooterBasicTotalsNoRun(self):
        self.summarize._Summarize__totals = (4, 5, 18)
        self.summarize.find_only = True
        self.summarize.print_footer()
        actual = self.summarize.report.getvalue()
        expected = TOTALS_BASIC_NO_RUN
        self.assertEqual(expected, actual)

    def testPrintFooterZeroTotalsWithRun(self):
        self.summarize._Summarize__totals = (0, 0, 0)
        self.summarize.print_footer()
        actual = self.summarize.report.getvalue()
        expected = TOTALS_ZERO
        self.assertEqual(expected, actual)

    def testPrintFooterZeroTotalsNoRun(self):
        self.summarize._Summarize__totals = (0, 0, 0)
        self.summarize.find_only = True
        self.summarize.print_footer()
        actual = self.summarize.report.getvalue()
        expected = TOTALS_ZERO_NO_RUN
        self.assertEqual(expected, actual)

    def testPrintFooterZeroPercentWithRun(self):
        self.summarize._Summarize__totals = (5, 5, 10)
        self.summarize.print_footer()
        actual = self.summarize.report.getvalue()
        expected = TOTALS_ZERO_PERCENT
        self.assertEqual(expected, actual)

    def testPrintFooterZeroPercentNoRun(self):
        self.summarize._Summarize__totals = (5, 5, 10)
        self.summarize.tfail = 5
        self.summarize.terr = 5
        self.summarize.tall = 10
        self.summarize.find_only = True
        self.summarize.print_footer()
        actual = self.summarize.report.getvalue()
        expected = TOTALS_ZERO_PERCENT_NO_RUN
        self.assertEqual(expected, actual)

    def testPrintFooterAllPassing(self):
        self.summarize._Summarize__totals = (0, 0, 10)
        self.summarize.tfail = 0
        self.summarize.terr = 0
        self.summarize.tall = 10
        self.summarize.print_footer()
        actual = self.summarize.report.getvalue()
        expected = TOTALS_ALL_PASSING
        self.assertEqual(expected, actual)

    def testPrintFooterAllPassingNoRun(self):
        self.summarize._Summarize__totals = (0, 0, 10)
        self.summarize.tfail = 0
        self.summarize.terr = 0
        self.summarize.tall = 10
        self.summarize.find_only = True
        self.summarize.print_footer()
        actual = self.summarize.report.getvalue()
        expected = TOTALS_ALL_PASSING_NO_RUN
        self.assertEqual(expected, actual)

########NEW FILE########
__FILENAME__ = demo
import unittest

class BadTests(unittest.TestCase):

    def testFailure(self):
        self.assertEqual(1,2)

    def testError(self):
        raise 'heck'

    def testDebug(self):
        expected = 1
        actual = 2
        #import pdb; pdb.set_trace()
        self.assertEqual(expected, actual)


########NEW FILE########
__FILENAME__ = marshallers
import os

from assertEquals.interactive.detail import Detail as _Detail
from assertEquals.interactive.utils import RefreshError
from assertEquals.interactive.summary import Summary as _Summary
from assertEquals.tests.utils import reportersTestCase


RAW = """\
Hey there!
-------------------------------<| assertEquals |>-------------------------------
.EF..
======================================================================
ERROR: test_errs (assertEqualsTests.TestCase)
----------------------------------------------------------------------
Traceback (most recent call last):"""; RAW2= """
  File "/tmp/assertEqualsTests/__init__.py", line 21, in test_errs
    raise StandardError(\'heck\')
StandardError: heck

======================================================================
FAIL: test_fails (assertEqualsTests.TestCase)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/assertEqualsTests/__init__.py", line 18, in test_fails
    self.assert_(0)
AssertionError

----------------------------------------------------------------------
Ran 5 tests in 0.002s

FAILED (failures=1, errors=1)
"""
_RAW = RAW+RAW2

RAW_ONE = """\
Hey there!
-------------------------------<| assertEquals |>-------------------------------
.E..
======================================================================
ERROR: test_errs (assertEqualsTests.TestCase)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/assertEqualsTests/__init__.py", line 21, in test_errs
    raise StandardError(\'heck\')
StandardError: heck

----------------------------------------------------------------------
Ran 1 test in 0.002s

FAILED (errors=1)
"""

TOTALS = ('60%', '1', '1', '5')
TOTALS_ONE = ('0%', '0', '1', '1')


# cross-platform hack
import os, tempfile
hack = os.path.join('', tempfile.gettempdir(), 'assertEqualsTests', '__init__.py')

DATA = {
'test_errs' : ['error', """\
Traceback (most recent call last):
  File "%s", line 21, in test_errs
    raise StandardError(\'heck\')
StandardError: heck""" % hack],
'test_fails' : ['failure', """\
Traceback (most recent call last):
  File "%s", line 18, in test_fails
    self.assert_(0)
AssertionError""" % hack]
        }
DATA_ONE = {
'test_errs' : ['error', """\
Traceback (most recent call last):
  File "%s", line 21, in test_errs
    raise StandardError(\'heck\')
StandardError: heck""" % hack]
        }


class Detail(reportersTestCase):

    def setUpUp(self):
        self.detail = _Detail('assertEqualsTests.TestCase')

    def testCall(self):
        try:
            self.detail._call()
        except RefreshError, err:
            raise StandardError(err.traceback)
        expected = RAW
        actual = self.detail._Detail__raw[:len(RAW)]
        self.assertEqual(expected, actual)

    def testCallCatchesErrorsInChildProcess(self):
        path = os.path.join( self.site_packages
                           , 'assertEqualsTests'
                           , '__init__.py'
                            )
        open(path, 'w+').write("wheeee!")
        self.assertRaises( RefreshError
                         , self.detail._call
                          )
        try:
            self.detail._call()
        except RefreshError, err:
            expected = 'Traceback (most recent call last):'
            actual = err.traceback
            self.assertEqual(expected, actual[:len(expected)])



    # _set_data
    # =========

    def testSetData(self):
        self.detail._Detail__raw = _RAW
        self.detail._set_data()
        expected = DATA
        actual = self.detail.data
        self.assertEqual(expected, actual)

        expected = TOTALS
        actual = self.detail.totals
        self.assertEqual(expected, actual)

    def testSetDataWorksForOneTest(self):
        self.detail._Detail__raw = RAW_ONE
        self.detail._set_data()
        expected = DATA_ONE
        actual = self.detail.data
        self.assertEqual(expected, actual)

        expected = TOTALS_ONE
        actual = self.detail.totals
        self.assertEqual(expected, actual)



RAW2 = """\
Hey there!
-------------------------------<| assertEquals |>-------------------------------
MODULE                                                       PASS FAIL  ERR  ALL
--------------------------------------------------------------------------------
assertEqualsTests.TestCase                                       60%    1    1    5
assertEqualsTests.itDoesExist.TestCase                          100%    0    0    2
assertEqualsTests.itDoesExist.TestCase2                         100%    0    0    1
assertEqualsTests.subpkg.TestCase                               100%    0    0    2
--------------------------------------------------------------------------------
TOTALS                                                        80%    1    1   10
"""
LINES = [ 'Hey there!'
, '-------------------------------<| assertEquals |>-------------------------------'
, 'MODULE                                                       PASS FAIL  ERR  ALL'
, '--------------------------------------------------------------------------------'
, 'assertEqualsTests.TestCase                                       60%    1    1    5'
, 'assertEqualsTests.itDoesExist.TestCase                          100%    0    0    2'
, 'assertEqualsTests.itDoesExist.TestCase2                         100%    0    0    1'
, 'assertEqualsTests.subpkg.TestCase                               100%    0    0    2'
, '--------------------------------------------------------------------------------'
]


RAW_ALL_PASSING = """\
Hey there!
-------------------------------<| assertEquals |>-------------------------------
MODULE                                                       PASS FAIL  ERR  ALL
--------------------------------------------------------------------------------
assertEqualsTests                                                60%    0    0    5
assertEqualsTests.itDoesExist                                   100%    0    0    2
--------------------------------------------------------------------------------
TOTALS                                                       100%    0    0    7
"""
LINES_ALL_PASSING = [ 'Hey there!'
, '-------------------------------<| assertEquals |>-------------------------------'
, 'MODULE                                                       PASS FAIL  ERR  ALL'
, '--------------------------------------------------------------------------------'
, 'assertEqualsTests                                                60%    0    0    5'
, 'assertEqualsTests.itDoesExist                                   100%    0    0    2'
, '--------------------------------------------------------------------------------'
]


RAW_DOTTED = """\
Hey there!
-------------------------------<| assertEquals |>-------------------------------
MODULE                                                       PASS FAIL  ERR  ALL
--------------------------------------------------------------------------------
assertEqualsTests.itDoesExist                                   100%    0    0    2
--------------------------------------------------------------------------------
TOTALS                                                        71%    1    1    7
"""
LINES_DOTTED = [ 'Hey there!'
, '-------------------------------<| assertEquals |>-------------------------------'
, 'MODULE                                                       PASS FAIL  ERR  ALL'
, '--------------------------------------------------------------------------------'
, 'assertEqualsTests.itDoesExist                                   100%    0    0    2'
, '--------------------------------------------------------------------------------'
]
DATA_DOTTED = {
    'assertEqualsTests': [None, None]
  , 'assertEqualsTests.itDoesExist': [('100%', '0', '0', '2'), True]
   }


TRACEBACK = """\
Traceback (most recent call last):
  File "./bin/assertEquals", line 3, in ?
    raise SystemExit(main())
  File "/usr/home/whit537/workbench/assertEquals/site-packages/assertEquals/cli/main.py", line 66, in main
    report = summarize(base, quiet, recursive, run, stopwords)
  File "/usr/home/whit537/workbench/assertEquals/site-packages/assertEquals/cli/reporters.py", line 87, in __call__
    self.modules = self.get_modules()
  File "/usr/home/whit537/workbench/assertEquals/site-packages/assertEquals/cli/reporters.py", line 100, in get_modules
    module = load(self.base)
  File "/usr/home/whit537/workbench/assertEquals/site-packages/assertEquals/cli/utils.py", line 44, in load
    module = __import__(name)
  File "/tmp/assertEqualsTests/__init__.py", line 3, in ?
    from assertEqualsTests import itDoesExist
  File "/tmp/assertEqualsTests/itDoesExist.py", line 3
    wheeee!
          ^
SyntaxError: invalid syntax
"""




class Summary(reportersTestCase):

    def setUpUp(self):
        self.summary = _Summary()


    # _call
    # =====

    def testCall(self):
        self.summary.module = 'assertEqualsTests'
        self.summary.find_only = False
        try:
            self.summary._call()
        except RefreshError, err:
            raise StandardError(err.traceback)
        expected = RAW2
        actual = self.summary._Summary__raw
        self.assertEqual(expected, actual)

    def testCallCatchesErrorsInChildProcess(self):
        path = os.path.join( self.site_packages
                           , 'assertEqualsTests'
                           , '__init__.py'
                            )
        open(path, 'w+').write("wheeee!")
        self.summary.base = 'assertEqualsTests'
        self.summary.find_only = False
        self.assertRaises( RefreshError
                         , self.summary._call
                          )
        try:
            self.summary._call()
        except RefreshError, err:
            expected = 'Traceback (most recent call last):'
            actual = err.traceback
            self.assertEqual(expected, actual[:len(expected)])


    # _set_totals
    # ===========

    def testSetTotals(self):
        self.summary._Summary__raw = RAW2
        self.summary._set_totals()

        expected = LINES
        actual = self.summary._Summary__lines
        self.assertEqual(expected, actual)

        expected = ('80%', '1', '1', '10')
        actual = self.summary.totals
        self.assertEqual(expected, actual)

    def testSetTotalsAllPassing(self):
        self.summary._Summary__raw = RAW_ALL_PASSING
        self.summary._set_totals()

        expected = LINES_ALL_PASSING
        actual = self.summary._Summary__lines
        self.assertEqual(expected, actual)

        expected = ('100%', '0', '0', '7')
        actual = self.summary.totals
        self.assertEqual(expected, actual)

    def testSetTotalsDotted(self):
        self.summary._Summary__raw = RAW_DOTTED
        self.summary._set_totals()

        expected = LINES_DOTTED
        actual = self.summary._Summary__lines
        self.assertEqual(expected, actual)

        expected = ('71%', '1', '1', '7')
        actual = self.summary.totals
        self.assertEqual(expected, actual)



    # _set_data
    # =========

    def testSetData(self):
        self.summary._Summary__raw = RAW2
        self.summary._set_totals()

        expected = LINES
        actual = self.summary._Summary__lines
        self.assertEqual(expected, actual)

        expected = ('80%', '1', '1', '10')
        actual = self.summary.totals
        self.assertEqual(expected, actual)

    def testSetDataDotted(self):
        self.summary._Summary__lines = LINES_DOTTED
        self.summary._set_data()
        expected = DATA_DOTTED
        actual = self.summary.data
        self.assertEqual(expected, actual)

########NEW FILE########
__FILENAME__ = scrollarea
import unittest

from assertEquals.interactive.utils import ScrollArea, DoneScrolling


def refuse_pass():
    pass
def refuse_raise():
    raise DoneScrolling


class TwoAndAHalfPageListing(unittest.TestCase):

    def setUp(self):
        #wheeee!
        self.area = ScrollArea(20, 50, 3)
        self.area.refuse = refuse_pass

    def testInit(self):
        expected = (20, 0, 50, 0, 20, 0, [3, 4, 5, 6, 7, 8, 9, 10, 11])
        actual = self.area.stat()
        self.assertEqual(expected, actual)


    # scroll_one
    # ==========

    def testScrollOne(self):
        self.area.scroll_one()
        expected = (20, 1, 50, 0, 20, 1, range(3,12))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollDownThenUp(self):
        self.area.scroll_one()
        self.area.scroll_one(up=True)
        expected = (20, 0, 50, 0, 20, 0, range(3,12))
        actual = self.area.stat()
        self.assertEqual(expected, actual)


    # scroll
    # ======

    def testScroll(self):
        self.area.scroll(1)
        expected = (20, 1, 50, 0, 20, 1, range(3,12))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollToEdgeOfScreen(self):
        self.area.scroll(19)
        expected = (20, 19, 50, 0, 20, 19, range(3,12))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollJustPastEdgeOfScreen(self):
        self.area.scroll(20)
        expected = (20, 19, 50, 1, 21, 20, range(3,12))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollWellPastEdgeOfScreen(self):
        self.area.scroll(25)
        expected = (20, 19, 50, 6, 26, 25, range(5,14))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollToEdgeOfList(self):
        self.area.scroll(50)
        expected = (20, 19, 50, 30, 50, 49, range(15,23))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollJustPastEdgeOfList(self):
        self.area.scroll(51)
        expected = (20, 19, 50, 30, 50, 49, range(15,23))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollWellPastEdgeOfList(self):
        self.area.scroll(1000)
        expected = (20, 19, 50, 30, 50, 49, range(15,23))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollTooFarDownTriggersRefusal(self):
        self.area.refuse = refuse_raise
        self.assertRaises(DoneScrolling, self.area.scroll, 1000)


    # scroll up

    def testScrollAllTheWayDownAndThenUpToEdgeOfList(self):
        self.area.scroll(50)
        expected = (20, 19, 50, 30, 50, 49, range(15,23))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

        self.area.scroll(-50)
        expected = (20, 0, 50, 0, 20, 0, range(3,12))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollAllTheWayDownAndThenUpJustPastEdgeOfList(self):
        self.area.scroll(50)
        expected = (20, 19, 50, 30, 50, 49, range(15,23))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

        self.area.scroll(-51)
        expected = (20, 0, 50, 0, 20, 0, range(3,12))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollAllTheWayDownAndThenUpWellPastEdgeOfList(self):
        self.area.scroll(50)
        expected = (20, 19, 50, 30, 50, 49, range(15,23))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

        self.area.scroll(-1000)
        expected = (20, 0, 50, 0, 20, 0, range(3,12))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollTooFarUpTriggersRefusal(self):
        self.area.refuse = refuse_raise
        self.assertRaises(DoneScrolling, self.area.scroll, -1000)


    # page_down
    # =========

    def testPageDown(self):
        self.area.page_down()
        expected = (20, 0, 50, 20, 40, 20, range(11,20))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testPageDownFullThenPartial(self):
        self.area.page_down()
        self.area.page_down()
        expected = (20, 0, 50, 40, 50, 40, range(19,23))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testPageDownFullThenPartialThenFinal(self):
        self.area.page_down()
        self.area.page_down()
        self.area.page_down()
        expected = (20, 0, 50, 49, 50, 49, range(22,23))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testPageDownCursorStaysPut(self):
        self.area.cursor = 7
        self.area.page_down()
        expected = (20, 7, 50, 20, 40, 27, range(11,20))
        actual = self.area.stat()
        self.assertEqual(expected, actual)


    # page_up
    # =======
    # Each starts by scrolling all the way down.

    def testPageUp(self):
        self.area.scroll(50)
        self.area.page_up()
        expected = (20, 19, 50, 10, 30, 29, range(7,16))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testPageUpFullThenPartial(self):
        self.area.scroll(50)
        self.area.page_up()
        self.area.page_up()
        #expected = (20, 19, 50, 0, 20, 19, range(3,12))
        expected = (20, 0, 50, 0, 20, 0, range(3,12))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testPageUpCursorStaysPut(self):
        self.area.scroll(50)
        self.area.cursor = 7
        self.area.page_up()
        expected = (20, 7, 50, 10, 30, 17, range(7,16))
        actual = self.area.stat()
        self.assertEqual(expected, actual)


    # combined
    # ========

    def testPageDownIntoPartialThenUp(self):
        self.area.page_down()
        self.area.page_down()
        self.area.page_up()
        expected = (20, 0, 50, 20, 40, 20, range(11,20))
        actual = self.area.stat()
        self.assertEqual(expected, actual)


    # home/end
    # ========

    def testHome(self):
        self.area.scroll(50)
        self.area.home()
        expected = (20, 0, 50, 0, 20, 0, range(3,12))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testEnd(self):
        self.area.end()
        expected = (20, 19, 50, 30, 50, 49, range(15,23))
        actual = self.area.stat()
        self.assertEqual(expected, actual)




class HalfPageListing(unittest.TestCase):

    def setUp(self):
        self.area = ScrollArea(20, 10, 3)
        self.area.refuse = refuse_pass

    def testInit(self):
        expected = (20, 0, 10, 0, 10, 0, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)


    # scroll_one
    # ==========

    def testScrollOne(self):
        self.area.scroll_one()
        expected = (20, 1, 10, 0, 10, 1, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollDownThenUp(self):
        self.area.scroll_one()
        self.area.scroll_one(up=True)
        expected = (20, 0, 10, 0, 10, 0, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)


    # scroll
    # ======

    def testScroll(self):
        self.area.scroll(1)
        expected = (20, 1, 10, 0, 10, 1, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollToEdgeOfScreen(self):
        self.area.scroll(19)
        expected = (20, 9, 10, 0, 10, 9, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollJustPastEdgeOfScreen(self):
        self.area.scroll(20)
        expected = (20, 9, 10, 0, 10, 9, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollWellPastEdgeOfScreen(self):
        self.area.scroll(25)
        expected = (20, 9, 10, 0, 10, 9, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollToEdgeOfList(self):
        self.area.scroll(9)
        expected = (20, 9, 10, 0, 10, 9, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollJustPastEdgeOfList(self):
        self.area.scroll(11)
        expected = (20, 9, 10, 0, 10, 9, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollWellPastEdgeOfList(self):
        self.area.scroll(1000)
        expected = (20, 9, 10, 0, 10, 9, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollTooFarDownTriggersRefusal(self):
        self.area.refuse = refuse_raise
        self.assertRaises(DoneScrolling, self.area.scroll, 1000)


    # scroll up

    def testScrollAllTheWayDownAndThenUpToEdgeOfList(self):
        self.area.scroll(9)
        self.area.scroll(-9)
        expected = (20, 0, 10, 0, 10, 0, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollAllTheWayDownAndThenUpJustPastEdgeOfList(self):
        self.area.scroll(9)
        self.area.scroll(-10)
        expected = (20, 0, 10, 0, 10, 0, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollAllTheWayDownAndThenUpWellPastEdgeOfList(self):
        self.area.scroll(9)
        self.area.scroll(-1000)
        expected = (20, 0, 10, 0, 10, 0, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollTooFarUpTriggersRefusal(self):
        self.area.refuse = refuse_raise
        self.assertRaises(DoneScrolling, self.area.scroll, -1000)



class EmptyPage(unittest.TestCase):

    def setUp(self):
        self.area = ScrollArea(20, 0, 3)
        self.area.refuse = refuse_raise

    def testInit(self):
        expected = (20, 0, 0, 0, 0, 0, None)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollDown(self):
        self.assertRaises(DoneScrolling, self.area.scroll, 1)

    def testScrollUp(self):
        self.assertRaises(DoneScrolling, self.area.scroll, -1)

    def testPageDown(self):
        self.assertRaises(DoneScrolling, self.area.page_down)

    def testPageUp(self):
        self.assertRaises(DoneScrolling, self.area.page_up)

    def testHome(self):
        self.assertRaises(DoneScrolling, self.area.home)

    def testEnd(self):
        self.assertRaises(DoneScrolling, self.area.end)



class ExactlyOneFullPage(unittest.TestCase):

    def setUp(self):
        self.area = ScrollArea(20, 20, 3)
        self.area.refuse = refuse_raise

    def testInit(self):
        expected = (20, 0, 20, 0, 20, 0, range(3,23))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testScrollDown(self):
        self.assertRaises(DoneScrolling, self.area.scroll, 20)

    def testScrollUp(self):
        self.assertRaises(DoneScrolling, self.area.scroll, -1)

    def testPageDown(self):
        self.assertRaises(DoneScrolling, self.area.page_down)

    def testPageUp(self):
        self.assertRaises(DoneScrolling, self.area.page_up)

    def testHome(self):
        self.assertRaises(DoneScrolling, self.area.home)

    def testEnd(self):
        self.area.end()
        self.assertRaises(DoneScrolling, self.area.end)



class PageDownBorking:#(unittest.TestCase):

    def setUp(self):
        self.area = ScrollArea(4, 5, 3)
        self.area.refuse = refuse_raise

    def testInit(self):
        expected = (4, 0, 5, 0, 4, 0)
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testPageDown(self):
        self.area.page_down()
        expected = (4, 0, 5, 4, 5, 4)
        actual = self.area.stat()
        self.assertEqual(expected, actual)
        self.assertRaises(DoneScrolling, self.area.page_down)

    def testPageDownThenScrollUp(self):
        self.area.page_down()
        self.area.scroll(-1)
        expected = (4, 0, 5, 3, 5, 3)
        actual = self.area.stat()
        self.assertEqual(expected, actual)



class PageDownMultiplePages(unittest.TestCase):

    def setUp(self):
        self.area = ScrollArea(20, 50, 0)
        self.area.refuse = refuse_raise


    # cursor == 0

    def testOneRowShowing(self):
        self.area.start = 49
        self.area.end_ = 50
        self.assertRaises(DoneScrolling, self.area.page_down)
        expected = (20, 0, 50, 49, 50, 49, range(19,20))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testTwoRowsShowing(self):
        self.area.start = 48
        self.area.end_ = 50
        self.assertRaises(DoneScrolling, self.area.page_down)
        expected = (20, 0, 50, 49, 50, 49, range(19,20))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testPartialPageShowing(self):
        self.area.start = 30
        self.area.end_ = 50
        self.assertRaises(DoneScrolling, self.area.page_down)
        expected = (20, 0, 50, 49, 50, 49, range(19,20))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testExactlyOnePageShowing(self):
        self.area.start = 30
        self.area.end_ = 50
        self.assertRaises(DoneScrolling, self.area.page_down)
        expected = (20, 0, 50, 49, 50, 49, range(19,20))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testOneRowTillLastPage(self):
        self.area.start = 29
        self.area.end_ = 49
        self.area.page_down()
        expected = (20, 0, 50, 49, 50, 49, range(19,20))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testSeveralRowsTillLastPage(self):
        self.area.start = 24
        self.area.end_ = 44
        self.area.page_down()
        expected = (20, 0, 50, 44, 50, 44, range(17,20))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testExactlyOnePageTillLastPage(self):
        self.area.start = 10
        self.area.end_ = 30
        self.area.page_down()
        expected = (20, 0, 50, 30, 50, 30, range(12,20))
        actual = self.area.stat()
        self.assertEqual(expected, actual)


    # cursor != 0

    def testCursorExactlyOnePageTillLastPage(self):
        self.area.cursor = 1
        self.area.start = 10
        self.area.end_ = 30
        self.area.page_down()
        expected = (20, 1, 50, 30, 50, 31, range(12,20))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

    def testExactlyOnePageShowingCursorAtBottom(self):
        self.area.cursor = 20
        self.area.start = 30
        self.area.end_ = 50
        self.assertRaises(DoneScrolling, self.area.page_down)
        expected = (20, 0, 50, 49, 50, 49, range(19,20))
        actual = self.area.stat()
        self.assertEqual(expected, actual)

########NEW FILE########
__FILENAME__ = utils
import os
import sys
import tempfile
import unittest


MODULE = """\
import unittest

class TestCase(unittest.TestCase):
    def test_foo(self):
        pass
    def test_bar(self):
        pass

class TestCase2(unittest.TestCase):
    def test_blam(self):
        pass

"""

MODULE_2 = """\
import unittest

# This module is never imported, and therefore never shows up in our reports.

class TestCase(unittest.TestCase):
    def test_foo(self):
        pass
    def test_bar(self):
        pass

class TestCase2(unittest.TestCase):
    def test_blam(self):
        pass

"""

_INIT__2 = """\
import unittest

class TestCase(unittest.TestCase):
    def test_foo(self):
        pass
    def test_bar(self):
        pass

class TestCase2(unittest.TestCase):
    pass

"""

_INIT__ = """\
import unittest

from assertEqualsTests import itDoesExist, subpkg


def my_program():
    print 'Hey there!'

class TestCase(unittest.TestCase):

    def test_passes(self):
        self.assert_(1)

    def test_does_nothing(self):
        pass

    def test_fails(self):
        self.assert_(0)

    def test_errs(self):
        raise StandardError('heck')

    def test_prints_stuff(self):
        my_program()

"""



class reportersTestCase(unittest.TestCase):
    """A base class for reporter tests. Provides setUpUp and pkg hooks.

    """

    # fixture
    # =======

    def setUp(self):
        self.tmp = tempfile.gettempdir()
        self.site_packages = os.path.join(self.tmp, 'site-packages')
        sys.path.insert(0, self.site_packages)

        # [re]build a temporary package tree in /tmp/site-packages/
        self.removeTestPkg()
        self.buildTestPkg()

        if hasattr(self, 'setUpUp'):
            self.setUpUp()

    def tearDown(self):
        if self.site_packages in sys.path:
            sys.path.remove(self.site_packages)
        for pkgname in os.listdir(self.site_packages):
            for modname in list(sys.modules.keys()):
                if modname.startswith(pkgname):
                    del sys.modules[modname]
        self.removeTestPkg()


    # test package
    # ============
    # pkg is a list of strings and tuples. If a string, it is interpreted as a
    # path to a directory that should be created. If a tuple, the first element
    # is a path to a file, the second is the contents of the file. You must use
    # forward slashes in your paths (they will be converted cross-platform). Any
    # leading slashes will be removed before they are interpreted.
    #
    # site_packages is the filesystem path under which to create the test site.

    site_packages = ''                                  # set in setUp
    pkg = [  'assertEqualsTests'                           # can be overriden
          , ('assertEqualsTests/__init__.py', _INIT__)
          , ('assertEqualsTests/itDoesExist.py', MODULE)
          ,  'assertEqualsTests/subpkg'
          , ('assertEqualsTests/subpkg/__init__.py', _INIT__2)
           ]

    def buildTestPkg(self):
        """Build the package described in self.pkg.
        """
        os.mkdir(self.site_packages)
        for item in self.pkg:
            if isinstance(item, basestring):
                path = self.convert_path(item.lstrip('/'))
                path = os.sep.join([self.site_packages, path])
                os.mkdir(path)
            elif isinstance(item, tuple):
                filepath, contents = item
                path = self.convert_path(filepath.lstrip('/'))
                path = os.sep.join([self.site_packages, path])
                file(path, 'w').write(contents)

    def removeTestPkg(self):
        """Remove the package described in self.pkg.
        """
        if not os.path.isdir(self.site_packages):
            return
        for root, dirs, files in os.walk(self.site_packages, topdown=False):
            for name in dirs:
                os.rmdir(os.path.join(root, name))
            for name in files:
                os.remove(os.path.join(root, name))
        os.rmdir(self.site_packages)

    def convert_path(self, path):
        """Given a Unix path, convert it for the current platform.
        """
        return os.sep.join(path.split('/'))

    def convert_paths(self, paths):
        """Given a tuple of Unix paths, convert them for the current platform.
        """
        return tuple([self.convert_path(p) for p in paths])

########NEW FILE########
__FILENAME__ = update
#!/usr/bin/env python

import os
import stat
import subprocess
import time

c = 'make'
mtimes = {}
try:
    while 1:
        made = False
        for name in os.listdir('.'):
            if not (  name == 'Makefile'
                   or name.endswith('.tex')
                   or name.endswith('.css')
                     ):
                continue
            if name not in mtimes:
                mtime = 0
            else:
                mtime = mtimes[name]
            newtime = os.stat(name)[stat.ST_MTIME]
            if mtime != newtime:
                mtimes[name] = newtime
                if not made:
                    p = subprocess.Popen(c, shell=True)
                    sts = os.waitpid(p.pid, 0)
                    made = True
                t = time.strftime('%I:%M.%S%p').replace(' 0', ' ')
                print "%s @ %s" % (name, t)
        time.sleep(0.5)
except KeyboardInterrupt:
    os.system("make clean")

########NEW FILE########
