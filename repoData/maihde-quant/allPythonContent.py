__FILENAME__ = config
#!/usr/bin/env python
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

from pycommando.commando import command
import os
import yaml

QUANT_DIR=os.path.expanduser("~/.quant")

@command("config")
def getConfig():
    return CONFIG 

class _Config(object):
    __CONFIG_FILE = os.path.join(QUANT_DIR, "quant.cfg")
    __YAML = None

    def __init__(self):
        self.load()

    def has_key(self, index):
        return _Config.__YAML.has_key(index)

    def __getitem__(self, index):
        return _Config.__YAML[index]

    def __str__(self):
        return yaml.dump(_Config.__YAML)

    def load(self):
        try:
            _Config.__YAML = yaml.load(open(_Config.__CONFIG_FILE))
        except IOError:
            pass
        # If a configuration is empty or didn't load, create a sample portfolio
        if _Config.__YAML == None:
            _Config.__YAML = {"portfolios": {"cash": {"$": 10000.0}}}
            self.commit()

    def commit(self):
        f = open(_Config.__CONFIG_FILE, "w")
        f.write(yaml.dump(_Config.__YAML))
        f.close()

# Create a global config singleton object
CONFIG = _Config()

########NEW FILE########
__FILENAME__ = ema
#!/usr/bin/env python
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import tables

class EMAData(tables.IsDescription):
    date = tables.TimeCol()
    value = tables.Float32Col()

class EMA(object):
    def __init__(self, period):
        self.value = None
        self.alpha = 2.0 / (period+1)
        self.tbl = None

    def setupH5(self, h5file, h5where, h5name):
        if h5file != None and h5where != None and h5name != None:
            self.tbl = h5file.createTable(h5where, h5name, EMAData)

    def update(self, value, date=None):
        if self.value == None:
            self.value = value
        else:
            self.value = (value * self.alpha) + (self.value * (1 - self.alpha))
        if self.tbl != None and date:
            self.tbl.row["date"] = date.date().toordinal()
            self.tbl.row["value"] = self.value
            self.tbl.row.append()
            self.tbl.flush()

        return self.value

if __name__ == "__main__":
    import unittest

    class EMATest(unittest.TestCase):

        def test_Alpha(self):
            ema = EMA(9)
            self.assertEqual(ema.alpha, 0.2)

            ema = EMA(19)
            self.assertEqual(ema.alpha, 0.1)

        def test_ConstantValueAlgorithm(self):
            ema = EMA(15)
            self.assertEqual(ema.value, None)
            for i in xrange(50):
                ema.update(5.)
                self.assertEqual(ema.value, 5.)

        def test_ConstantZeroValueAlgorithm(self):
            ema = EMA(10)
            self.assertEqual(ema.value, None)
            for i in xrange(50):
                ema.update(0.)
                self.assertEqual(ema.value, 0.)

        def test_ConstantZeroValueAlgorithm(self):
            ema = EMA(9)
            self.assertEqual(ema.value, None)
            ema.update(1.)
            self.assertEqual(ema.value, 1.)
            ema.update(2.)
            self.assertAlmostEqual(ema.value, 1.2)


    unittest.main()

########NEW FILE########
__FILENAME__ = price
#!/usr/bin/env python
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import tables

class ValueData(tables.IsDescription):
    date = tables.TimeCol()
    value = tables.Float32Col()

class SimpleValue(object):
    def __init__(self):
        self.value = 0.0
        self.tbl = None

    def setupH5(self, h5file, h5where, h5name):
        if h5file != None and h5where != None and h5name != None:
            self.tbl = h5file.createTable(h5where, h5name, ValueData)

    def update(self, value, date=None):
        self.value = value
        if self.tbl != None and date:
            self.tbl.row["date"] = date.date().toordinal()
            self.tbl.row["value"] = self.value
            self.tbl.row.append()
            self.tbl.flush()

        return self.value

########NEW FILE########
__FILENAME__ = rsi
#!/usr/bin/env python
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import tables
import math
from ema import EMA

class RSIData(tables.IsDescription):
    date = tables.TimeCol()
    value = tables.Float32Col()

class RSI(object):

    def __init__(self, period):
        self.value = None
        self.last = None
        self.ema_u = EMA(period)
        self.ema_d = EMA(period)
        self.tbl = None
    
    def setupH5(self, h5file, h5where, h5name):
        if h5file != None and h5where != None and h5name != None:
            self.tbl = h5file.createTable(h5where, h5name, RSIData)

    def update(self, value, date=None):
        if self.last == None:
            self.last = value
        
        U = value - self.last
        D = self.last - value

        self.last = value

        if U > 0:
            D = 0
        elif D > 0:
            U = 0

        self.ema_u.update(U)
        self.ema_d.update(D)

        if self.ema_d.value == 0:
            self.value = 100.0
        else:
            rs = self.ema_u.value / self.ema_d.value
            self.value = 100.0 - (100.0 / (1 + rs))

        if self.tbl != None and date:
            self.tbl.row["date"] = date.date().toordinal()
            self.tbl.row["value"] = self.value
            self.tbl.row.append()
            self.tbl.flush()

        return self.value

if __name__ == "__main__":
    import unittest

    class RSITest(unittest.TestCase):

        def notest_ConstantValueAlgorithm(self):
            rsi = RSI(14)
            self.assertEqual(rsi.value, None)
            self.assertEqual(rsi.last, None)
            for i in xrange(50):
                rsi.update(5.)
                self.assertEqual(rsi.value, 100.0)

        def notest_NoDAlgorithm(self):
            rsi = RSI(14)
            self.assertEqual(rsi.value, None)
            self.assertEqual(rsi.last, None)
                
            rsi.update(5.)    # U = 0, D = 0
            self.assertEqual(rsi.value, 100.0)
            rsi.update(10.)   # U = 5, D = 0
            self.assertEqual(rsi.value, 100.0)
            rsi.update(15.)   # U = 5, D = 0
            self.assertEqual(rsi.value, 100.0)
            rsi.update(20.)   # U = 5, D = 0
            self.assertEqual(rsi.value, 100.0)

        def notest_NoUAlgorithm(self):
            rsi = RSI(14)
            self.assertEqual(rsi.value, None)
            self.assertEqual(rsi.last, None)
                
            rsi.update(50.)   # U = 0, D = 0
            self.assertEqual(rsi.value, 100.0)
            rsi.update(40.)   # U = 0 D = 10
            self.assertEqual(rsi.value, 0.0)
            rsi.update(30.)   # U = 0 D = 10
            self.assertEqual(rsi.value, 0.0)
            rsi.update(20.)   # U = 0 D = 10
            self.assertEqual(rsi.value, 0.0)

        def test_Algorithm(self):
            rsi = RSI(9)
            self.assertEqual(rsi.value, None)
            self.assertEqual(rsi.last, None)
                
            rsi.update(50.)   # U = 0, D = 0, ema_u = 0, ema_d = 0
            self.assertEqual(rsi.value, 100.0)
            rsi.update(40.)   # U = 0 D = 10, ema_u = 0, ema_d = 2, rs = 0
            self.assertEqual(rsi.value, 0.0)
            rsi.update(50.)   # U = 10 D = 0, ema_u = 2, ema_d = 1.6, rs = 1.25, rsi = 55.555555  
            self.assertAlmostEqual(rsi.value, 55.555555555555)

    unittest.main()

########NEW FILE########
__FILENAME__ = simplevalue
#!/usr/bin/env python
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import tables

class ValueData(tables.IsDescription):
    date = tables.TimeCol()
    value = tables.Float32Col()

class SimpleValue(object):
    def __init__(self):
        self.value = 0.0
        self.tbl = None

    def setupH5(self, h5file, h5where, h5name):
        if h5file != None and h5where != None and h5name != None:
            self.tbl = h5file.createTable(h5where, h5name, ValueData)

    def update(self, value, date=None):
        self.value = value
        if self.tbl != None and date:
            self.tbl.row["date"] = date.date().toordinal()
            self.tbl.row["value"] = self.value
            self.tbl.row.append()
            self.tbl.flush()

        return self.value

########NEW FILE########
__FILENAME__ = sma
#!/usr/bin/env python
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import tables

class SMAData(tables.IsDescription):
    date = tables.TimeCol()
    value = tables.Float32Col()

class SMA(object):
    def __init__(self, period):
        self.values = [0.0 for x in xrange(period)]
        self.value = 0.0
        self.period = period
        self.tbl = None

    def setupH5(self, h5file, h5where, h5name):
        if h5file != None and h5where != None and h5name != None:
            self.tbl = h5file.createTable(h5where, h5name, SMAData)

    def update(self, value, date=None):
        oldest = self.values.pop()
        self.values.insert(0, value)
       
        self.value = self.value - (oldest / self.period) + (value / self.period) 

        if self.tbl != None and date:
            self.tbl.row["date"] = date.date().toordinal()
            self.tbl.row["value"] = self.value
            self.tbl.row.append()
            self.tbl.flush()

        return self.value

if __name__ == "__main__":
    import unittest

    class SMATest(unittest.TestCase):

        def test_ConstantValueAlgorithm(self):
            sma = SMA(5)
            self.assertEqual(sma.value, 0.0)
                
            sma.update(5.0)
            self.assertEqual(sma.value, 1.0)
            sma.update(5.0)
            self.assertEqual(sma.value, 2.0)
            sma.update(5.0)
            self.assertEqual(sma.value, 3.0)
            sma.update(5.0)
            self.assertEqual(sma.value, 4.0)
            sma.update(5.0)
            self.assertEqual(sma.value, 5.0)
            sma.update(5.0)
            self.assertEqual(sma.value, 5.0)
            sma.update(5.0)
            self.assertEqual(sma.value, 5.0)

    unittest.main()

########NEW FILE########
__FILENAME__ = plots
#!/usr/bin/env python
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import os
import sys
import tables
from utils.date import ONE_DAY
from pycommando.commando import command
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import matplotlib.ticker as ticker
import matplotlib.dates as dates

@command("show")
def show():
    """Shows all plots that have been created, only necessary if you are
    creating plots in a script.  Typically the last line of a script that
    creates plots will be 'show'.
    """
    plt.show()

@command("plot")
def plot(input_="~/.quant/simulation.h5", node="/Performance", x="date", y="value"):
    try:
        inputFile = tables.openFile(os.path.expanduser(input_), "r")
        tbl = inputFile.getNode(node, classname="Table")

        x_data = tbl.col(x)
        y_data = tbl.col(y)
    finally:
        inputFile.close()

    fig = plt.figure()
    sp = fig.add_subplot(111)
    sp.set_title(input_)
    sp.plot(x_data, y_data, '-')
    
    x_locator = dates.AutoDateLocator()
    sp.xaxis.set_major_locator(x_locator)
    sp.xaxis.set_major_formatter(dates.AutoDateFormatter(x_locator))

    #def format_date(value, pos=None):
    #    return datetime.datetime.fromordinal(int(value)).strftime("%Y-%m-%d")
    #sp.xaxis.set_major_formatter(ticker.FuncFormatter(format_date))
    fig.autofmt_xdate()
    fig.show()

@command("plot_indicators")
def plot_indicators(symbol="", indicator="all", input_="~/.quant/simulation.h5", x="date", y="value"):

    inputFile = tables.openFile(os.path.expanduser(input_), "r")
    try:
        symbols = []
        if symbol == "":
            symbols = [grp._v_name for grp in inputFile.iterNodes("/Indicators", classname="Group")]
        else:
            symbols = (symbol,)

        for sym in symbols:
            fig = plt.figure()
            lines = []
            legend = []
            sp = fig.add_subplot(111)
            sp.set_title(input_ + " " + sym)
            for tbl in inputFile.iterNodes("/Indicators/" + sym, classname="Table"):
                if indicator == "all" or tbl._v_name == indicator:
                    x_data = tbl.col(x)
                    y_data = tbl.col(y)
                    line = sp.plot(x_data, y_data, '-')
                    lines.append(line)
                    legend.append(tbl._v_name)
                    x_locator = dates.AutoDateLocator()
                    sp.xaxis.set_major_locator(x_locator)
                    sp.xaxis.set_major_formatter(dates.AutoDateFormatter(x_locator))
            legend = fig.legend(lines, legend, loc='upper right')
            fig.autofmt_xdate()
            fig.show()
    finally:
        inputFile.close()

########NEW FILE########
__FILENAME__ = portfolio
#!/usr/bin/env python
#
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
from pycommando.commando import command
from config import CONFIG
from utils.date import ONE_DAY
import yahoo
import datetime
import math
import yaml

@command("portfolio_create")
def create(name, cash_percent=0.0, initial_position="{}"):
    if not CONFIG["portfolios"].has_key(name):
        CONFIG["portfolios"][name] = {}
        CONFIG["portfolios"][name]['$'] = cash_percent
        initial_position = yaml.load(initial_position)
        for sym, amt in initial_position.items():
            CONFIG["portfolios"][name][sym] = amt
        CONFIG.commit()
    else:
        raise StandardError, "Portfolio already exists"

@command("portfolio_delete")
def delete(name):
    if CONFIG["portfolios"].has_key(name):
        del CONFIG['portfolios'][name]
        CONFIG.commit()

@command("portfolio_risk")
def risk(portfolio, start, end, initial_value=10000.0):
    # Emulate risk reports found in beancounter
    # TODO
    raise NotImplementedError 

########NEW FILE########
__FILENAME__ = commando
#!/usr/bin/env python
# vim: sw=4: et:
#
# Copyright (c) 2010 by Michael Ihde <mike.ihde@randomwalking.com>
#
#                All Rights Reserved
#
# Permission to use, copy, modify, and distribute this software
# and its documentation for any purpose and without fee is hereby
# granted, provided that the above copyright notice appear in all
# copies and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Michael Ihde  not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# Michael Ihde DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS, IN NO EVENT SHALL Michael Ihde BE LIABLE FOR
# ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#
import inspect
import sys
import string
import cmd
import new
import traceback
import pprint
import os

class Commando(cmd.Cmd):

    ISATTY = True
    def __init__(self, completekey='tab', stdin=sys.stdin, stdout=sys.stdout):
        cmd.Cmd.__init__(self, completekey, stdin, stdout)
        Commando.ISATTY = os.isatty(stdin.fileno()) 
        if not Commando.ISATTY: 
            self.prompt = ""

    def do_shell(self, argstr):
        pass

    def precmd(self, cmd):
        if cmd == "EOF":
            raise SystemExit
        return cmd

    def emptyline(self):
        pass

    def cmdloop(self, intro=None):
        try:
            cmd.Cmd.cmdloop(self, intro)
        except KeyboardInterrupt:
            pass
        except SystemExit:
            pass
        print

def parseargs(argstr):
    """Args are separated by white-space or commas.  Unless a value is
    surrounded by single quotes, white space will be trimmed.

    >>> parseargs('A B C')
    ('A', 'B', 'C')

    >>> parseargs('A    B    C')
    ('A', 'B', 'C')

    >>> parseargs('A, B, C')
    ('A', 'B', 'C')

    >>> parseargs('A B, C')
    ('A', 'B', 'C')
    
    >>> parseargs('A,   B, C')
    ('A', 'B', 'C')

    >>> parseargs('A,   B   C')
    ('A', 'B', 'C')

    >>> parseargs('A ,, C')
    ('A', None, 'C')

    >>> parseargs("'A ' ' B ' C")
    ('A ', ' B ', 'C')

    >>> parseargs("'A, B, C'")
    ('A, B, C',)

    >>> parseargs("'A, B' C")
    ('A, B', 'C')
    """
    args = []
    def parser():
        while True:
            char = (yield)
            if char != ' ': 
                arg_accumulator = []
                if char not in (',', "'", " "):
                    arg_accumulator.append(char)
                if char == "'":
                    while True:
                        char = (yield)
                        if char == "'":
                            break
                        else:
                            arg_accumulator.append(char)
                while True:
                    char = (yield)
                    if char in (',', " ", None):
                        arg = "".join(arg_accumulator)
                        if arg == "":
                            args.append(None)
                        else:
                            args.append(arg)
                        break
                    else:
                        arg_accumulator.append(char)

    p = parser()
    p.send(None) # Start up the coroutine
    for char in argstr:
        p.send(char)
    p.send(None)

    return tuple(args)

# DECORATOR
class command(object):
    def __init__(self, name, prompts=(), category=None):
        self.name = name
	self.prompts = {}
        for argname, prompt, argtype in prompts:
            self.prompts[argname] = (prompt, argtype)

    def promptForYesNo(self, prompt, default):
        val = None
        if not Commando.ISATTY: 
            val = default
        else:
            while val == None:
                if default == None:
                    input = raw_input(prompt + " Y/N: ")
                    if input.upper() in ("Y", "YES"):
                        val = True
                    elif input.upper() in ("N", "NO"):
                        val = False
                else:
                    if default == True:
                        val = raw_input(prompt + " [Y]/N: ")
                    elif default == False:
                        val = raw_input(prompt + " Y/[N]: ")
                    else:
                        raise ValueError

        if val.strip() == "":
            val = default
        elif val.upper() in ("Y", "YES"):
            val = True
        elif val.upper() in ("N", "NO"):
            val = False

        return val

    def promptForValue(self, prompt, default, val_type):
        val = None
        if not Commando.ISATTY: 
            val = default
        else:
            while val == None:
                if default == None:
                    input = raw_input(prompt + ": ")
                    if input.strip() != "":
                        val = input
                else:
                    val = raw_input(prompt + " [%s]: " % (default))
                    if val.strip() == "":
                        val = default
        try:
            val = val_type(val)
        except ValueError:
            val = None

        return val

    def __call__(self, f):
        # Pull out meta data about the function
        f_args, f_varargs, f_varkwargs, f_defaults = inspect.getargspec(f)
        if f_defaults != None:
            f_first_default_index = len(f_args) - len(f_defaults)
        else:
            f_first_default_index = None

        # Define the wrapped function
        def wrapped_f(commando, argstr):
	    args = parseargs(argstr)
            vals = []

            for i in xrange(len(f_args)):
                # See if this argument has a default or not
                default = None
                if f_first_default_index != None and i >= f_first_default_index:
                    default = f_defaults[i - f_first_default_index]

                try:
                    text, val_type = self.prompts[f_args[i]]
                except KeyError:
                    # No prompt was provided, so use a generic one
                    text = "Enter %s" % (f_args[i])
                    # infer the type from the default when possible
                    if default != None:
                        val_type = type(default)
                    else:
                        val_type = str
               
                val = None
                if i < len(args):
                    # The user passed the value so we don't need to prompt
                    # if args[i] is None (not to be confused with "None")
                    # then they explictly wanted the default (without a prompt)
                    # because they entered two commas back to back with an
                    # empty string
                    if (args[i]) != None:
                        if val_type == bool:
                            if args[i].upper() in ("Y", "YES", "TRUE"):
                                val = True
                            elif args[i].upper() in ("N", "NO", "FALSE"):
                                val = False
                            else:
                                raise ValueError
                        else:
                            val = val_type(args[i])
                    elif (args[i]) == None and default != None:
                        val = default
                    else:
                        if val_type == bool:
                            val = self.promptForYesNo(text, default)
                        else:
                            val = self.promptForValue(text, default, val_type)
                else:
                    # Treat bools as yes/no
                    if val_type == bool:
                        val = self.promptForYesNo(text, default)
                    else:
                        val = self.promptForValue(text, default, val_type)
                vals.append(val)

            if f_varargs != None and len(args) > len(f_args):
                vals.extend(args[len(f_args):])
            # Call the function and print the result using pprint
            try:
                result = f(*vals)
                if result != None:
                    if type(result) in (dict, list, tuple):
                        pprint.pprint(result)
                    else:
                        print result
            except Exception, e:
                traceback.print_exc()
                if not Commando.ISATTY: 
                    raise SystemExit

        # Inherit the provided docstring
        # and augment it with information about the arguments
        wrapped_f.__doc__ = f.__doc__
        wrapped_f.__doc__ = "\nUsage: %s %s\n\n %s" % (self.name, " ".join(f_args), f.__doc__)

        f_name = "do_" + self.name
        setattr(Commando, f_name, new.instancemethod(wrapped_f, None, Commando))

	# Don't return the wrapped function, because we want
	# to be able to call the functions without the prompt logic
        return f

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = example
#!/usr/bin/env python
# vim: sw=4: et:
import readline
import sys
from commando import *

# Define a command called "action1"
@command("action1")
def action1():
    """Do something"""
    print "action1"

# Define a command called "doit"
@command("doit", prompts=(("value2", "Enter a number", int),
                          ("value1", "Enter a string", str)))
def action2(value1, value2=5):
    """Do something else"""
    print "action2", repr(value1), repr(value2)

# Define a command called "go" using default prompts
@command("go")
def action3(value1=False):
    """Do another thing
    but do it well"""
    print "action3", repr(value1)

# Define multiple commands that call the same function
@command("exit")
@command("quit")
def exit():
    """Quit"""
    sys.exit(0)

commando = Commando()
commando.cmdloop()
# Some examples
# (Cmd) doit
# Enter a string: abc
# Enter a number [5]: 6
# action2 'abc' 6
# (Cmd) doit def
# Enter a number [5]: 
# action2 'def' 5
# (Cmd) doit abc ,,
# action2 'abc' 5
# (Cmd) doit ,,,
# Enter a string: abc
# action2 'abc' 5
# (Cmd) go
# Enter value1 Y/[N]: 
# action3 False
# (Cmd) go 
# Enter value1 Y/[N]: Y
# action3 True
# (Cmd) go Y
# action3 True
# (Cmd) go N
# action3 False
# (Cmd) go True
# action3 True
# (Cmd) go False
# action3 False
# (Cmd) go No
# action3 False
# (Cmd) go Yes
# action3 True

########NEW FILE########
__FILENAME__ = report
#!/usr/bin/env python
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import os
import tables
import datetime
import math
from utils.progress_bar import ProgressBar
from pycommando.commando import command

def calculate_performance(inputfname="~/.quant/simulation.h5"):
    report = {}

    inputFile = tables.openFile(os.path.expanduser(inputfname), "r")
    try:
        tbl = inputFile.getNode("/Performance", classname="Table")

        equity_curve = zip([datetime.datetime.fromordinal(int(x)) for x in tbl.col("date")], tbl.col("value"))
        starting_date, starting_value = equity_curve[0]
        ending_date, ending_value = equity_curve[-1] 

        # Analysis
        max_draw_down_duration = {'days': 0, 'start': None, 'end': None}
        max_draw_down_amount = {'amount': 0.0, 'high': None, 'low': None}
        daily_returns = [10000.0]
        #benchmark_returns = [10000.0]
        #excess_returns = []

        last = equity_curve[0]
        highwater = equity_curve[0] # The highwater date and equity
        lowwater = equity_curve[0] # The highwater date and equity
        for date, equity in equity_curve[1:]:
            # If we have passed the highwater or we are at the end of the simulation
            if equity >= highwater[1] or date == equity_curve[-1][0]:
                drawdown_dur = (date - highwater[0]).days
                drawdown_amt = highwater[1] - lowwater[1] 
                if drawdown_dur > max_draw_down_duration['days']:
                    max_draw_down_duration['days'] = drawdown_dur
                    max_draw_down_duration['start'] = highwater
                    max_draw_down_duration['end'] = (date, equity)
                if drawdown_amt > max_draw_down_amount['amount']:
                    max_draw_down_amount['amount'] = drawdown_amt
                    max_draw_down_amount['high'] = highwater
                    max_draw_down_amount['low'] = lowwater
                highwater = (date, equity)
                lowwater = (date, equity)

            if equity <= lowwater[1]:
                lowwater = (date, equity)

            daily_return = (equity - last[1]) / last[1]
            daily_returns.append((daily_return * daily_returns[-1]) + daily_returns[-1])

            last = (date, equity)

        total_days = (ending_date - starting_date).days
        total_years = float(total_days) / 365.0
        equity_return = ending_value - starting_value
        equity_percent = 100.0 * (equity_return / starting_value)
        cagr = 100.0 * (math.pow((ending_value / starting_value), (1 / total_years)) - 1)
        drawdown_percent = 0.0
        if max_draw_down_amount['high'] != None:
            drawdown_percent = 100.0 * (max_draw_down_amount['amount'] / max_draw_down_amount['high'][1])
      
        report['period'] = total_days
        report['starting_date'] = starting_date
        report['starting_value'] = starting_value
        report['ending_date'] = ending_date
        report['ending_value'] = ending_value
        report['ending_value'] = ending_value
        report['equity_return'] = equity_return
        report['equity_percent'] = equity_percent 
        report['cagr'] = cagr
        report['drawdown_dur'] = max_draw_down_duration['days']
        report['drawdown_amt'] = max_draw_down_amount['amount']
        report['drawdown_per'] = drawdown_percent
        report['initial_pos'] = (starting_date, starting_value)
        report['final_pos'] = (ending_date, ending_value)

        report['orders'] = []
        # Calculate cost-basis/and profit on trades using single-category method
        tbl = inputFile.getNode("/Orders", classname="Table")
        winning = 0
        losing = 0
        largest_winning = (0, "")
        largest_losing = (0, "")
        conseq_win = 0
        conseq_lose = 0
        largest_conseq_win = 0
        largest_conseq_lose = 0
        total_profit = 0
        total_win = 0
        total_lose = 0
        total_trades = 0
        for order in tbl.iterrows():
            o = (datetime.datetime.fromordinal(order['date']).date(), order['executed_quantity'], order['executed_price'], order['basis'], order['order'])
            report['orders'].append(o)
            if order['order_type'] == "SELL":
                total_trades += 1
                profit = (order['executed_price'] - order['basis']) * order['executed_quantity']
                total_profit += profit
                if profit > 0:
                    winning += 1
                    conseq_win += 1
                    total_win += profit
                    if conseq_lose > largest_conseq_lose:
                        largest_conseq_lose = conseq_lose
                    conseq_lose = 0
                elif profit < 0:
                    losing += 1
                    conseq_lose += 1
                    total_lose += profit
                    if conseq_win > largest_conseq_win:
                        largest_conseq_win = conseq_win
                    conseq_win = 0

                if profit > largest_winning[0]:
                    largest_winning = (profit, order['date_str'])
                if profit < largest_losing[0]:
                    largest_losing = (profit, order['date_str'])

        if winning == 0:
            avg_winning = 0
        else:
            avg_winning = total_win / winning
        if losing == 0:
            avg_losing = 0
        else:
            avg_losing = total_lose / losing
        if conseq_win > largest_conseq_win:
            largest_conseq_win = conseq_win
        if conseq_lose > largest_conseq_lose:
            largest_conseq_lose = conseq_lose

        report['total_trades'] = total_trades
        report['winning_trades'] = winning
        report['losing_trades'] = losing
        if total_trades > 0:
            report['avg_trade'] = total_profit / total_trades
        else:
            report['avg_trade'] = 0
        report['avg_winning_trade'] = avg_winning
        report['avg_losing_trade'] = avg_losing
        report['conseq_win'] = largest_conseq_win
        report['conseq_lose'] = largest_conseq_lose
        report['largest_win'] = largest_winning
        report['largest_lose'] = largest_losing

    finally:
        inputFile.close()

    return report

@command("report_performance")
def report_performance(inputfname="~/.quant/simulation.h5"):
    report = calculate_performance(inputfname)
    print
    print "######################################################################################"
    print " Report:", inputfname
    print
    print "Simulation Period: %(period)s days" % report
    print "Starting Value: $%(starting_value)0.2f" % report
    print "Ending Value: $%(ending_value)0.2f" % report
    print "Return: $%(equity_return)0.2f (%(equity_percent)3.2f%%)" % report
    print "CAGR: %(cagr)3.2f%%" % report
    print "Maximum Drawdown Duration: %(drawdown_dur)d days" % report
    print "Maxium Drawdown Amount: $%(drawdown_amt)0.2f (%(drawdown_per)3.2f%%)" % report
    print "Inital Position:", report['starting_date'], report['starting_value']
    print "Final Position:", report['ending_date'], report['ending_value']
    print

    # Calculate cost-basis/and profit on trades using single-category method
    print "Date\t\tQty\tPrice\tBasis\tOrder"
    for order in report['orders']:
        print "%s\t%0.2f\t%0.2f\t%0.2f\t%s" % order

    if report['total_trades'] > 0:
        print
        print "Total # of Trades:", report['total_trades']
        print "# of Winning Trades:", report['winning_trades']
        print "# of Losing Trades:", report['losing_trades']
        print "Percent Profitable:", report['winning_trades'] / report['total_trades']
        print
        print "Average Trade:", report['avg_trade']
        print "Average Winning Trade:", report['avg_winning_trade']
        print "Average Losing Trade:", report['avg_losing_trade']
        print
        print "Max. conseq. Winners:", report['conseq_win']
        print "Max. conseq. Losers:", report['conseq_lose']
        print "Largest Winning Trade:", report['largest_win'][0], report['largest_win'][1]
        print "Largest Losing Trade:", report['largest_lose'][0], report['largest_lose'][1]
    print "######################################################################################"
    print

@command("list_orders")
def list_orders(input_="~/.quant/simulation.h5", node="/Orders"):
    try:
        inputFile = tables.openFile(os.path.expanduser(input_), "r")
        tbl = inputFile.getNode(node, classname="Table")
        for d in tbl.iterrows():
            print d
    finally:
        inputFile.close()

########NEW FILE########
__FILENAME__ = simulation
#/usr/bin/env python
# vim: sw=4: et
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import logging
import datetime
import numpy
import os
import sys
import tables
import math
import yaml
from config import CONFIG
from yahoo import Market
from utils.progress_bar import ProgressBar
from utils.model import *
from utils.market import *
from utils.date import ONE_DAY
from pycommando.commando import command
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import matplotlib.ticker as ticker
import matplotlib.dates as dates

MARKET = Market()

def initialize_position(portfolio, date):
    p = CONFIG['portfolios'][portfolio]

    if not type(date) == datetime.datetime:
        date = datetime.datetime.strptime(date, "%Y-%m-%d")

    # Turn the initial cash value into shares based off the portfolio percentage
    position = {'$': 0.0}
    market = Market()
    for instrument, amt in p.items():
        instrument = instrument.strip()
        if type(amt) == str:
            amt = amt.strip()

        if instrument == "$":
            position[instrument] += float(amt)
        else:
            d = date
            price = market[instrument][d].adjclose
            while price == None:
                # Walk backwards looking for a day that had a close price, but not too far
                # because the given instrument may not exist at any time for the given
                # date or prior to it
                d = d - ONE_DAY
                if (date - d) > datetime.timedelta(days=7):
                    break
                price = market[instrument][d].adjclose
            if price == None:
                # This occurs it the instrument does not exist in the market
                # at the start of the simulation period
                position[instrument] = Position(0.0, 0.0)
                if type(amt) == str and amt.startswith('$'):
                    amt = float(amt[1:])
                    position['$'] += amt
                else:
                    print "Warning.  Non-cash value used for instrument that is not available at start of simulation period"
            else:
                if type(amt) == str and amt.startswith('$'):
                    amt = float(amt[1:])
                    amt = math.floor(amt / price)
                position[instrument] = Position(float(amt), price)
    return position

def write_position(table, position, date):
    for instrument, p in position.items():
        table.row['date'] = date.date().toordinal()
        table.row['date_str'] = str(date.date())
        table.row['symbol'] = instrument 
        if instrument == '$':
            table.row['amount'] = 0
            table.row['value'] = p
        else:
            table.row['amount'] = p.amount
            table.row['basis'] = p.basis
            price = MARKET[instrument][date].adjclose
            if price:
                table.row['value'] = price
            else:
                table.row['value'] = 0.0
        table.row.append()

def write_performance(table, position, date):
    value = 0.0
    for instrument, p in position.items():
        if instrument == '$':
            value += p
        else:
            price = MARKET[instrument][date].adjclose
            if price:
                value += (price * p.amount)

    table.row['date'] = date.date().toordinal()
    table.row['date_str'] = str(date.date())
    table.row['value'] = value
    table.row.append()

def execute_orders(table, position, date, orders):
    for order in orders:
        logging.debug("Executing order %s", order)
        if position.has_key(order.symbol):
            ticker = MARKET[order.symbol]
            if order.order == Order.SELL:
                if order.price_type == Order.MARKET_PRICE:
                    strike_price = ticker[date].adjopen
                elif order.price_type == Order.MARKET_ON_CLOSE:
                    strike_price = ticker[date].adjclose
                else:
                    raise StandardError, "Unsupport price type"

                qty = None
                if order.quantity == "ALL":
                    qty = position[order.symbol].amount
                else:
                    qty = order.quantity

                if qty > position[order.symbol] or qty < 1:
                    logging.warn("Ignoring invalid order %s.  Invalid quantity", order)
                    continue
             
                price_paid = 0.0

                table.row['date'] = date.date().toordinal() 
                table.row['date_str'] = str(date.date())
                table.row['order_type'] = order.order
                table.row['symbol'] = order.symbol
                table.row['order'] = str(order)
                table.row['executed_quantity'] = qty
                table.row['executed_price'] = strike_price
                table.row['basis'] = position[order.symbol].basis 
                table.row.append()

                position[order.symbol].remove(qty, strike_price)
                position['$'] += (qty * strike_price)
                position['$'] -= 9.99 # TODO make trading cost configurable

            elif order.order == Order.BUY:
                if order.price_type == Order.MARKET_PRICE:
                    strike_price = ticker[date].adjopen
                elif order.price_type == Order.MARKET_ON_CLOSE:
                    strike_price = ticker[date].adjclose

                if type(order.quantity) == str and order.quantity[0] == "$":
                    qty = int(float(order.quantity[1:]) / strike_price)
                else:
                    qty = int(order.quantity)

                table.row['date'] = date.date().toordinal() 
                table.row['date_str'] = str(date.date())
                table.row['order_type'] = order.order
                table.row['symbol'] = order.symbol
                table.row['order'] = str(order)
                table.row['executed_quantity'] = qty
                table.row['executed_price'] = strike_price
                table.row['basis'] = 0.0
                table.row.append()

                position[order.symbol].add(qty, strike_price)
                position['$'] -= (qty * strike_price)
                position['$'] -= 9.99


def load_strategy(name):
    mydir = os.path.abspath(os.path.dirname(sys.argv[0]))
    strategydir = os.path.join(mydir, "strategies")
    sys.path.insert(0, strategydir)
    if name in sys.modules.keys():
        reload(sys.modules[name])
    else:
        __import__(name)

    clazz = getattr(sys.modules[name], "CLAZZ")
    sys.path.pop(0)

    return clazz


@command("analyze")
def analyze(strategy_name, portfolio, strategy_params="{}"):
    """Using a given strategy and portfolio, make a trading decision"""
    now = datetime.datetime.today()
    position = initialize_position(portfolio, now)

    # Initialize the strategy
    params = yaml.load(strategy_params)
    strategy_clazz = load_strategy(strategy_name)
    strategy = strategy_clazz(now, now, position, MARKET, params)
    
    orders = strategy.evaluate(now, position, MARKET)

    for order in orders:
        print order

@command("simulate")
def simulate(strategy_name, portfolio, start_date, end_date, output="~/.quant/simulation.h5", strategy_params="{}"):
    """A simple simulator that simulates a strategy that only makes
    decisions at closing.  Only BUY and SELL orders are supported.  Orders
    are only good for the next day.

    A price type of MARKET is executed at the open price the next day.

    A price type of MARKET_ON_CLOSE is executed at the close price the next day.

    A price type of LIMIT will be executed at the LIMIT price the next day if LIMIT
    is between the low and high prices of the day.

    A price type of STOP will be executed at the STOP price the next day if STOP
    is between the low and high prices of the day.

    A price type of STOP_LIMIT will be executed at the LIMIT price the next day if STOP
    is between the low and high prices of the day.
    """

    outputFile = openOutputFile(output)
    # Get some of the tables from the output file
    order_tbl = outputFile.getNode("/Orders")
    postion_tbl = outputFile.getNode("/Position")
    performance_tbl = outputFile.getNode("/Performance")
        
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    # Start the simulation at closing of the previous trading day
    now = getPrevTradingDay(start_date)

    try:
        position = initialize_position(portfolio, now)

        # Pre-cache some info to make the simulation faster
        ticker = MARKET["^DJI"].updateHistory(start_date, end_date)
        for symbol in position.keys():
            if symbol != '$':
                MARKET[symbol].updateHistory(start=start_date, end=end_date)
        days = (end_date - start_date).days
        
        # Initialize the strategy
        params = yaml.load(strategy_params)
        strategy_clazz = load_strategy(strategy_name)
        strategy = strategy_clazz(start_date, end_date, position, MARKET, params, outputFile)

        p = ProgressBar(maxValue=days, totalWidth=80)
        print "Starting Simulation"

        while now <= end_date:

            # Write the initial position to the database
            write_position(postion_tbl, position, now)
            write_performance(performance_tbl, position, now)
            
            # Remember 'now' is after closing, so the strategy
            # can use any information from 'now' or earlier
            orders = strategy.evaluate(now, position, MARKET)
               
            # Go to the next day to evalute the orders
            now += ONE_DAY
            while not isTradingDay(now):
                now += ONE_DAY
                p.performWork(1)
                continue
            
            # Execute orders
            execute_orders(order_tbl, position, now, orders)

            # Flush the data to disk
            outputFile.flush()
            p.performWork(1)
            print p, '\r',

        p.updateAmount(p.max)
        print p, '\r',
        print '\n' # End the progress bar here before calling finalize
        orders = strategy.finalize()
    finally:
        outputFile.close()

########NEW FILE########
__FILENAME__ = hold
#!/usr/bin/env python
# vim: sw=4: et
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
from strategy import Strategy
from utils.model import Order

class Hold(Strategy):
    """The most basic strategy.  It holds the initial postion and
    makes no trades....ever...for any reason.
    """
    def evaluate(self, date, position, market):
        return () # There are never any orders from this strategy

CLAZZ = Hold

########NEW FILE########
__FILENAME__ = sell
#!/usr/bin/env python
# vim: sw=4: et
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
from strategy import Strategy
from utils.model import Order

class SellOff(Strategy):
    """A simple strategy, useful for testing, that sells everything immediately."""
    def evaluate(self, date, position, market):
        orders = [] 
        for symbol, p in position.items():
            if symbol != '$' and p.amount > 0:
                orders.append(Order(Order.SELL, symbol, p.amount, Order.MARKET_PRICE))
        return orders

CLAZZ = SellOff

########NEW FILE########
__FILENAME__ = strategy
#!/usr/bin/env python
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
from utils.date import ONE_DAY
import tables

class Strategy(object):
    def __init__(self, start_date, end_date, initial_position, market, params, h5file=None):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_position = initial_position
        self.market = market
        self.params = params

        # Manage indicators, the dictionary is:
        #  key = symbol
        #  value = dictionary(key="indicator name", value=indicator)
        self.indicators = {}

        # If the strategy was passed h5 info, use it to store information
        self.h5file = h5file
        if h5file != None:
            self.indicator_h5group = h5file.createGroup("/", "Indicators")
            self.strategy_h5group = h5file.createGroup("/", "Strategy")

    def addIndicator(self, symbol, name, indicator):
        if not self.indicators.has_key(symbol):
            self.indicators[symbol] = {}
        self.indicators[symbol][name] = indicator

        if self.h5file != None:
            try:
                symgroup = self.h5file.getNode(self.indicator_h5group._v_pathname, symbol, classname="Group")  
            except tables.NoSuchNodeError:
                symgroup = self.h5file.createGroup(self.indicator_h5group._v_pathname, symbol)

            if self.h5file and self.indicator_h5group:
                indicator.setupH5(self.h5file, symgroup, name)

    def removeIndicator(self, symbol, name):
        del self.indicators[symbol][name]

    def updateIndicators(self, start_date, end_date=None):
        for symbol, indicators in self.indicators.items():
            ticker = self.market[symbol]
            if end_date != None:
                quotes = ticker[start_date:end_date] # Call this to cache everything
                end = end_date
            else:
                end = start_date + ONE_DAY

            d = start_date
            while d < end:
                quote = ticker[d]
                if quote.adjclose != None:
                    for indicator in indicators.values():
                        indicator.update(quote.adjclose, d)
                d += ONE_DAY

    def evaluate(self, date, position):
        raise NotImplementedError

    def finalize(self):
        self.h5file = None
        self.indicator_h5group = None
        self.strategy_h5group = None

########NEW FILE########
__FILENAME__ = trending
# A module for all built-in commands.
# vim: sw=4: et
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import datetime
import os
import tables
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import matplotlib.ticker as ticker

from indicators.ema import EMA
from indicators.rsi import RSI 
from indicators.simplevalue import SimpleValue
from strategy import Strategy
from utils.model import Order
from utils.date import ONE_DAY

class SymbolData(tables.IsDescription):
    date = tables.TimeCol()
    closing = tables.Float32Col()
    ema_short = tables.Float32Col()
    ema_long = tables.Float32Col()

class Trending(Strategy):
    DEF_LONG_DAYS = 200
    DEF_SHORT_DAYS = 15
    DEF_RSI_PERIOD = 14

    def __init__(self, start_date, end_date, initial_position, market, params, h5file=None):
        Strategy.__init__(self, start_date, end_date, initial_position, market, params, h5file)
        for symbol in initial_position.keys():
            if symbol == "$":
                continue

            self.addIndicator(symbol, "value", SimpleValue()) 
            try:
                short = params['short']
            except KeyError:
                short = Trending.DEF_SHORT_DAYS
            self.addIndicator(symbol, "short", EMA(short)) 
            try:
                long_ = params['long']
            except KeyError:
                long_ = Trending.DEF_LONG_DAYS
            self.addIndicator(symbol, "long", EMA(long_)) 
            try:
                rsi = params['rsi']
            except KeyError:
                rsi = Trending.DEF_RSI_PERIOD
            self.addIndicator(symbol, "rsi", RSI(rsi)) 

        # Backfill the indicators 
        try:
            backfill = params['backfill']
        except KeyError:
            backfill = long_

        d = start_date - (backfill * ONE_DAY)
        self.updateIndicators(d, start_date)
    
    def evaluate(self, date, position, market):
        self.updateIndicators(date)
       
        # Based of indicators, create signals
        buyTriggers = []
        sellTriggers = []
        for symbol, qty in position.items():
            if symbol != '$':
                ticker = market[symbol]
                close_price = ticker[date].adjclose
                if self.indicators[symbol]["short"].value < self.indicators[symbol]["long"].value:
                    sellTriggers.append(symbol)
                elif self.indicators[symbol]["short"].value > self.indicators[symbol]["long"].value:
                    buyTriggers.append(symbol)
       
        # Using the basic MoneyManagement strategy, split all available cash
        # among all buy signals
        # Evaluate sell orders
        orders = []
        for sellTrigger in sellTriggers:
            if position[sellTrigger].amount > 0:
                orders.append(Order(Order.SELL, sellTrigger, "ALL", Order.MARKET_PRICE))

        # Evaluate all buy orders
        if len(buyTriggers) > 0:
            cash = position['$']
            cashamt = position['$'] / len(buyTriggers)
            for buyTrigger in buyTriggers:
                ticker = market[buyTrigger]
                close_price = ticker[date].adjclose
                if close_price != None:
                    estimated_shares = int(cashamt / close_price)
                    # Only issues orders that buy at least one share
                    if estimated_shares >= 1:
                        orders.append(Order(Order.BUY, buyTrigger, "$%f" % cashamt, Order.MARKET_PRICE))
                
        return orders

CLAZZ = Trending

########NEW FILE########
__FILENAME__ = date
#!/usr/bin/env python
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import datetime

ONE_DAY = datetime.timedelta(days=1)

########NEW FILE########
__FILENAME__ = market
#!/usr/bin/env python
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
from yahoo import Market
from utils.date import ONE_DAY
import datetime

MARKET = Market()

def isTradingDay(date):
    if date.weekday() in (0,1,2,3,4):
        # Consider any day the Dow was active as a trading day
        ticker = MARKET["^DJI"]
        if (ticker != None):
            quote = ticker[date]
            if quote.adjclose != None:
                return True
    return False


def getPrevTradingDay(date):
    prev_trading_day = date - ONE_DAY
    while isTradingDay(prev_trading_day) == False:
        prev_trading_day = prev_trading_day - ONE_DAY
    return prev_trading_day

def getNextTradingDay(date):
    next_trading_day = date + ONE_DAY
    while isTradingDay(next_trading_day) == False:
        next_trading_day = next_trading_day - ONE_DAY
    return next_trading_day

########NEW FILE########
__FILENAME__ = model
#/usr/bin/env python
# vim: sw=4: et
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import logging
import datetime
import numpy
import os
import tables

###############################################################################
# Data structures used by filters/strategies/riskmanagement
###############################################################################
class Order(object):
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    COVER = "COVER"
    BUY_TO_OPEN = "BUY_TO_OPEN"
    BUY_TO_CLOSE = "BUY_TO_CLOSE"
    SELL_TO_CLOSE = "SELL_TO_CLOSE"
    SELL_TO_OPEN = "SELL_TO_OPEN"

    MARKET_PRICE = "MARKET_PRICE"
    MARKET_ON_CLOSE = "MARKET_ON_CLOSE"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

    def __init__(self, order, symbol, quantity, price_type, stop=None, limit=None):
        self._order = order
        self._sym = symbol
        self._qty = quantity
        self._price_type = price_type
        self._stop = stop
        self._limit = limit

    # Use propreties so that the Order class attributes behave as 
    # readonly
    def getOrder(self):
        return self._order
    order = property(fget=getOrder)
    
    def getSymbol(self):
        return self._sym
    symbol = property(fget=getSymbol)

    def getQuantity(self):
        return self._qty
    quantity = property(fget=getQuantity)

    def getPriceType(self):
        return self._price_type
    price_type = property(fget=getPriceType)

    def getStop(self):
        return self._stop
    stop = property(fget=getStop)

    def getLimit(self):
        return self._limit
    limit = property(fget=getLimit)

    def __str__(self):
        if type(self._qty) == "float":
            qty = "$%0.2f" % self.quantity
        else:
            qty = self.quantity
        res = "%s %s %s at %s" % (self.order, qty, self.symbol, self.price_type)
        if self.price_type in (Order.LIMIT):
           res += " " + self.limit
        elif self.price_type in (Order.STOP):
           res += " " + self.stop
        elif self.price_type in (Order.STOP_LIMIT):
           res += " " + self.limit + " when " + self.stop
        return res

class Position(object):
    def __init__(self, amount, basis):
        self.amount = amount
        self.basis = basis

    def add(self, qty, price_paid):
        v = (self.amount * self.basis) + (qty * price_paid)
        self.amount += qty
        self.basis = v / self.amount

    def remove(self, qty, price_sold):
        self.amount -= qty

    def __str__(self):
        return str(self.amount)

###############################################################################
# PyTables data structures
###############################################################################
class OrderData(tables.IsDescription):
    date = tables.TimeCol()
    order_type = tables.StringCol(16)
    symbol = tables.StringCol(16)
    date_str = tables.StringCol(16)
    order = tables.StringCol(64)
    executed_quantity = tables.Int32Col()
    executed_price = tables.Float32Col()
    basis = tables.Float32Col()

class PositionData(tables.IsDescription):
    date = tables.TimeCol()
    date_str = tables.StringCol(16)
    symbol = tables.StringCol(16)
    amount = tables.Int32Col()
    value = tables.Float32Col()
    basis = tables.Float32Col() # The basis using single-category averaging

class PerformanceData(tables.IsDescription):
    date = tables.TimeCol()
    date_str = tables.StringCol(16)
    value = tables.Float32Col()

###############################################################################
# Helper functions
###############################################################################
def openOutputFile(filepath):
    """After opening the file, get the tables like this.
   
    file.getNode("/Orders")
    file.getNode("/Position")
    file.getNode("/Performance")
    """
    try:
        os.remove(os.path.expanduser(filepath))
    except OSError:
        pass
    outputFile = tables.openFile(os.path.expanduser(filepath), mode="w", title="Quant Simulation")
    outputFile.createTable("/", 'Orders', OrderData)
    outputFile.createTable("/", 'Position', PositionData)
    outputFile.createTable("/", 'Performance', PositionData)
    return outputFile

########NEW FILE########
__FILENAME__ = progress_bar
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

class ProgressBar:
    def __init__(self, minValue = 0, maxValue = 10, totalWidth=12):
	self.progBar = "[]"   # This holds the progress bar string
	self.min = minValue
	self.max = maxValue
	self.span = maxValue - minValue
	self.width = totalWidth
	self.amount = 0       # When amount == max, we are 100% done 
	self.updateAmount(0)  # Build progress bar string

    def performWork(self, work):
	self.updateAmount(self.amount + work)

    def updateAmount(self, newAmount = 0):
	if newAmount < self.min: newAmount = self.min
	if newAmount > self.max: newAmount = self.max
	self.amount = newAmount

	# Figure out the new percent done, round to an integer
	diffFromMin = float(self.amount - self.min)
	percentDone = (diffFromMin / float(self.span)) * 100.0
	percentDone = round(percentDone)
	percentDone = int(percentDone)

	# Figure out how many hash bars the percentage should be
	allFull = self.width - 2
	numHashes = (percentDone / 100.0) * allFull
	numHashes = int(round(numHashes))

	# build a progress bar with hashes and spaces
	self.progBar = "[" + '#'*numHashes + ' '*(allFull-numHashes) + "]"

	# figure out where to put the percentage, roughly centered
	percentPlace = (len(self.progBar) / 2) - len(str(percentDone)) 
	percentString = str(percentDone) + "%"

	# slice the percentage into the bar
	self.progBar = self.progBar[0:percentPlace] + percentString + self.progBar[percentPlace+len(percentString):]

    def __str__(self):
	return str(self.progBar)

########NEW FILE########
__FILENAME__ = YahooQuote
LICENSE="""
This module is released under the GNU Lesser General Public License,
the wording of which is available on the GNU website, http://www.gnu.org
"""

"""
YahooQuote - a set of classes for fetching stock quotes from
finance.yahoo.com

Created by David McNab ((david AT conscious DOT co DOT nz))

Originally this was a wrapper of the original
'pyq' utility by Rimon Barr:
    - http://www.cs.cornell.edu/barr/repository/pyq/index.html
But now, the back-end has been completely re-written.

The original version stored stock quotes in a MetaKit database
file.  Since metakit isn't available as a Ubuntu package, the
cache storage has been changed to sqlite3 to be as portable 
as possible.

Usage Examples::

 >>> import YahooQuote

 >>> market = YahooQuote.Market()

 >>> redhat = market['rht']
 >>> redhat
 <Ticker:rht>

 >>> redhat[20070601]
 <Quote:rht/20070601:m=-0.31 o=24.88 c=24.57 l=24.40 h=25.25 a=24.57 v=8579200>

 >>> redhat.now  # magic attribute via __getattr__
 <Quote:rht/20071506:m=-0.22 o=23.50 c=23.28 l=23.22 h=23.75 a=23.28 v=1185200>

 >>> ms = market['msft']
 >>> ms
 <Ticker:msft>  # note the 'dji/msft', meaning that MS is on DJI index

 >>> ms[20070604:20070609]  # get range of dates as slice - Jun4 - Jun8
 [<Quote:msft/20070604:m=+0.30 o=30.42 c=30.72 l=30.40 h=30.76 a=30.72 v=41434500>, 
 <Quote:msft/20070605:m=-0.04 o=30.62 c=30.58 l=30.33 h=30.63 a=30.58 v=44265000>, 
 <Quote:msft/20070606:m=-0.08 o=30.37 c=30.29 l=30.25 h=30.53 a=30.29 v=38217500>, 
 <Quote:msft/20070607:m=-0.40 o=30.02 c=29.62 l=29.59 h=30.29 a=29.62 v=71971400>]

 >>> lastThu = ms[20070614]  # fetch a single trading day

 >>> lastThu
 <Quote:msft/20070614:m=+0.17 o=30.35 c=30.52 l=30.30 h=30.71 a=30.52 v=59065700>

 >>> lastThu.__dict__      # see what is in a Quote object
 {'volume': 59065700, 'open': 30.350000000000001, 'high': 30.710000000000001,
  'adjclose': 30.52, 'low': 30.300000000000001, 'date': '20070614',
  'close': 30.52, 'ticker': <Ticker:dji/msft>}

 >>> ms[20070603]  # sunday, markets closed, build dummy quote from Friday
 <Quote:msft/20070603:m=0.00 o=30.59 c=30.59 l=30.59 h=30.59 a=30.59 v=0>

Read the API documentation for further features/methods
"""

import os, sys, re, traceback, getopt, time
#import strptime
import urllib
import weakref, gc
import csv
import logging
import Queue, thread, threading
import datetime
import sqlite3

Y2KCUTOFF=60
__version__ = "0.4"

CACHE='~/.quant/stocks.db'

MONTH2NUM = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
  'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

DAYSECS = 60 * 60 * 24

DEBUG = 0

ENABLE_INTERPOLATION = False

# base URLs for fetching quotes and history
baseUrlHistory = "http://ichart.finance.yahoo.com/table.csv"
baseUrlQuote = "http://download.finance.yahoo.com/d/quotes.csv"

fetchWindow = 90

# maximum number of threads for fetching histories
maxHistoryThreads = 10

# hardwired table listing the various stock indexes around the world.
# from time to time, this will need to be updated
indexes = {
    "DJA": {"name": "Dow Jones Composite", "country": "USA"},
    "DJI": {"name": "Dow Jones Industrial Average", "country": "USA"},
    "DJT": {"name": "Dow Jones Transportation Average", "country": "USA"},
    "DJU": {"name": "Dow Jones Utility Average", "country": "USA"},
    "NYA": {"name": "NYSE Composite", "country": "USA"},
    "NIN": {"name": "NYSE International 100", "country": "USA"},
    "NTM": {"name": "NYSE TMT", "country": "USA"},
    "NUS": {"name": "NYSE US 100", "country": "USA"},
    "NWL": {"name": "NYSE World Leaders", "country": "USA"},
    "IXBK":{"name": "NASDAQ Bank", "country": "USA"},
    "NBI": {"name": "NASDAQ Biotech", "country": "USA"},
    "IXIC":{"name": "NASDAQ Composite", "country": "USA"},
    "IXK": {"name": "NASDAQ Computer", "country": "USA"},
    "IXF": {"name": "NASDAQ Financial 100", "country": "USA"},
    "IXID":{"name": "NASDAQ Industrial", "country": "USA"},
    "IXIS":{"name": "NASDAQ Insurance", "country": "USA"},
    "IXQ": {"name": "NASDAQ NNM Composite", "country": "USA"},
    "IXFN":{"name": "NASDAQ Other Finance", "country": "USA"},
    "IXUT":{"name": "NASDAQ Telecommunications", "country": "USA"},
    "IXTR":{"name": "NASDAQ Transportation", "country": "USA"},
    "NDX": {"name": "NASDAQ-100 (DRM)", "country": "USA"},
    "OEX": {"name": "S&P 100 Index", "country": "USA"},
    "MID": {"name": "S&P 400 Midcap Index", "country": "USA"},
    "GSPC":{"name": "S&P 500 Index", "country": "USA"},
    "SPSUPX":{"name": "S&P Composite 1500 Index", "country": "USA"},
    "SML": {"name": "S&P Smallcap 600 Index", "country": "USA"},
    "XAX": {"name": "AMEX COMPOSITE INDEX", "country": "USA"},
    "IIX": {"name": "AMEX INTERACTIVE WEEK INTERNET", "country": "USA"},
    "NWX": {"name": "AMEX NETWORKING INDEX", "country": "USA"},
    "PSE": {"name": "ArcaEx Tech 100 Index", "country": "USA"},
    "DWC": {"name": "DJ WILSHIRE 5000", "country": "USA"},
    "XMI": {"name": "MAJOR MARKET INDEX", "country": "USA"},
    "SOXX": {"name": "PHLX SEMICONDUCTOR SECTOR INDEX", "country": "USA"},
    "DOT": {"name": "PHLX THESTREET.COM INTERNET SEC", "country": "USA"},
    "RUI": {"name": "RUSSELL 1000 INDEX", "country": "USA"},
    "RUT": {"name": "RUSSELL 2000 INDEX", "country": "USA"},
    "RUA": {"name": "RUSSELL 3000 INDEX", "country": "USA"},
    "MERV": {"name": "MerVal", "country": "?"},
    "BVSP": {"name": "Bovespa", "country": "?"},
    "GSPTSE": {"name": "S&P TSX Composite", "country": "?"},
    "MXX": {"name": "IPC", "country": "?"},
    "GSPC": {"name": "500 Index", "country": "?"},
    "AORD": {"name": "All Ordinaries", "country": "Australia"},
    "SSEC": {"name": "Shanghai Composite", "country": "China"},
    "HSI": {"name": "Hang Seng", "country": "Hong Kong"},
    "BSESN": {"name": "BSE", "country": "?"},
    "JKSE": {"name": "Jakarta Composite", "country": "Indonesia"},
    "KLSE": {"name": "KLSE Composite", "country": "?"},
    "N225": {"name": "Nikkei 225", "country": "Japan"},
    "NZ50": {"name": "NZSE 50", "country": "New Zealand"},
    "STI": {"name": "Straits Times", "country": "?"},
    "KS11": {"name": "Seoul Composite", "country": "?"},
    "TWII": {"name": "Taiwan Weighted", "country": "Taiwan"},
    "ATX": {"name": "ATX", "country": "?"},
    "BFX": {"name": "BEL-20", "country": "?"},
    "FCHI": {"name": "CAC 40", "country": "?"},
    "GDAXI": {"name": "DAX", "country": "?"},
    "AEX": {"name": "AEX General", "country": "?"},
    "OSEAX": {"name": "OSE All Share", "country": "?"},
    "MIBTEL": {"name": "MIBTel", "country": "?"},
    "IXX": {"name": "ISE National-100", "country": "?"},
    "SMSI": {"name": "Madrid General", "country": "Spain"},
    "OMXSPI": {"name": "Stockholm General", "country": "Sweden"},
    "SSMI": {"name": "Swiss Market", "country": "Swizerland"},
    "FTSE": {"name": "FTSE 100", "country": "UK"},
    "CCSI": {"name": "CMA", "country": "?"},
    "TA100": {"name": "TA-100", "country": "?"},
    }


class SymbolNotFound(Exception):
    pass


class Cache:
    """
    Class that provides the cache using sqllite.
    """
    HISTORY_COL_DEF=(
        "stock_id integer primary key autoincrement",
        "symbol text not null",
        "date date",
        "open float",
        "close float",
        "low float",
        "high float",
        "volume float",
        "adjclose float")

    def __init__(self):
        dbPath = os.path.expanduser(CACHE)
        dbDir = os.path.split(dbPath)[0]
        if not os.path.isdir(dbDir):
            os.mkdir(dbDir)

        self.db = sqlite3.connect(dbPath)

        cursor = self.db.cursor()
	cursor.execute("CREATE TABLE IF NOT EXISTS history (%s)" % (", ".join(Cache.HISTORY_COL_DEF)))
	cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ticker ON history (symbol, date ASC)")
	cursor.close()

    def symbols(self):
        """Return a list of symbols that have been cached."""
	cursor = self.db.cursor()
	symbols = cursor.execute("select distinct symbol from history").fetchall()
	cursor.close()
        return [x[0] for x in symbols]

    def get(self, symbol, wantDate, priorDate=None):
	cursor = self.db.cursor()
        if priorDate == None:
            hist = cursor.execute("SELECT * FROM HISTORY WHERE (date='%s' and symbol='%s')" % (wantDate, symbol)).fetchall()
        else:
            hist = cursor.execute("SELECT * FROM HISTORY WHERE (date>='%s' and date<='%s' and symbol='%s')" % (priorDate, wantDate, symbol)).fetchall()
        return [Quote.fromRow(x) for x in hist]

    def init(self, symbol, wantDate, priorDate):
        d = priorDate
        while d <= wantDate:
            cursor = self.db.cursor()
            cursor.execute("INSERT OR REPLACE INTO HISTORY VALUES (NULL, '%s', '%s', NULL, NULL, NULL, NULL, NULL, NULL)" % (symbol, d))
            cursor.close()
            d += 1
        self.db.commit()

    def put(self, quotes):
        for quote in quotes:
            cursor = self.db.cursor()
            cursor.execute("INSERT OR REPLACE INTO HISTORY VALUES (NULL, '%(symbol)s', '%(date)s', '%(open)s', %(close)f, %(low)f, %(high)f, %(volume)f, %(adjclose)f)" % quote.__dict__)
            cursor.close()
        self.db.commit()

    def purge(self, symbol):
	cursor = self.db.cursor()
	hist = cursor.execute("DELETE FROM HISTORY WHERE (symbol='%s')" % (symbol)).fetchall()
	cursor.close()
        self.db.commit()

    def __del__(self):
        try:
            self.db.commit()
        except:
            pass


class Market:
    """
    Main top-level class for YahooQuote.

    Holds/fetches info on a per-ticker basis

    Use this like a dict, where the keys are ticker symbols,
    and the values are Ticker objects (see class Ticker)
    """
    def __init__(self):
        """
        Creates a 'Market' object, which accesses quotes for
        various ticker symbols through Ticker object

        No args or keywords needed.
        """
        self.cache = Cache()

        self.indexes = {}
        self.tickersBySymbol = {}
        self.symbolIndex = {}

    def loadIndexes(self):
        """
        loads all index components.

        The first time this method is executed, it will download
        a list of component stocks for each index and store them in the
        database.

        Subsequent calls to this method, even in future sessions, will
        just load these component stock lists from the database
        """
        logging.debug("loading indexes and components")
        # load up all the indexes and their parts
        for symbol in indexes.keys():
            idx = Index(self, symbol, **indexes[symbol])
            self.indexes[symbol] = idx
            for stocksym in idx.components:
                self.symbolIndex[stocksym] = symbol
        logging.debug("  index components loaded")


    def __getitem__(self, symbol):
        """
        If 'symbol' is an index, returns an L{Index} object for that index symbol.

        If 'symbol' is an individual stock symbol, then returns a L{Ticker}
        object for that stock
        """
        su = symbol.upper()
        if su in self.indexes:
            return self.indexes[su]

        # we store weak refs to the tickers, to save memory when
        # the tickers go away
        ticker = None
        ref = self.tickersBySymbol.get(symbol, None)
        if ref:
            ticker = ref()

        if not ticker:
            ticker = Ticker(self, symbol)
            self.tickersBySymbol[symbol] = weakref.ref(ticker)

        return ticker


    def fetchHistory(self):
        """
        Fetches all history for all known stocks

        This can take an hour or more, even with a broadband connection, and
        will leave you with a cache file of over 100MB.

        If you're only interested in specific stocks or indexes, you might prefer
        to invoke L{Index.fetchHistory} or L{Ticker.FetchHistory}, respectively.
        """
        logging.info("fetching history for all stocks")
        if len(self.indexes.values()) == 0:
	    self.loadIndexes()

        try:
            for index in self.indexes.values():
                # fill the queue with callable methods
		logging.debug("fetching index %s", index)
                index.fetchHistory()
        except KeyboardInterrupt:
            logging.info("interrupted by user")

    def updateHistory(self):
        """
        Updates all known stocks' histories. Don't run this unless
        you have previously invoked L{Market.fetchHistory}
        """
        for symbol in self.cache.symbols():
	    logging.debug("updating symbol %s", symbol)
            ticker = self[symbol]
            ticker.updateHistory()


class Index:
    """
    encapsulates a stock index, eg 'dji' for dow jones
    """
    def __init__(self, market, symbol, **kw):
        """
        Creates a market index container. You shouldn't normally have to
        create these yourself.
        """
        symbol = symbol.lower()
        self.market = market
        self.symbol = symbol
        self.__dict__.update(kw)

        # fetch the components from yahoo
        self.components = []
	self.fetchFromYahoo()

    def __repr__(self):

        return "<Index:%s>" % self.symbol


    def load(self, row):
        """
        loads component names from database
        """
        for symbolRow in row.stocks:
            self.components.append(symbolRow.symbol)

    def fetchFromYahoo(self):
        """
        retrieves a list of component stocks for this index from the
        Yahoo Finance website
        """
        logging.debug("Refreshing list of component stocks for %s" % self.symbol)

        # create args
        parmsDict = {
            "s": "@^"+self.symbol.upper(),
            "f": "sl1d1t1c1ohgv",
            "e": ".csv",
            "h": 0,
            }
        parms = "&".join([("%s=%s" % (k,v)) for k,v in parmsDict.items()])

        # construct full URL
        url = "http://download.finance.yahoo.com/d/quotes.csv?%s" % parms

        # get the CSV for this index
        f = urllib.urlopen(url)
        lines = f.readlines()
        csvReader = csv.reader(lines)

        # extract the component symbols
        componentSymbols = [item[0].lower() for item in csvReader if item]

        # save to database
        for symbol in componentSymbols:
            self.components.append(symbol)

    def fetchHistory(self):
        """
        Invokes L{Ticker.fetchHistory} on all component stocks of this index
        """
        logging.debug("index %s" % self.symbol)

        for sym in self.components:

            ticker = self.market[sym]
            ticker.fetchHistory()

    def __getitem__(self, symbol):
        """
        retrieves a component ticker
        """
        return self.market[self.components[symbol]]



class Ticker:
    """
    Represents the prices of a single ticker symbol.

    Works as a smart sequence, keyed by yyyymmdd numbers

    The magic attribute 'now' fetches current prices
    """
    baseUrlQuote = baseUrlQuote
    baseUrlHistory = baseUrlHistory

    def __init__(self, market, symbol, index=None):
        """
        Create a Ticker class, which gets/caches/retrieves quotes
        for a single ticker symbol

        Treat objects of this class like an array, where you can get
        a single item (date) to return a Quote object for the symbol 
        and date, or get a slice, to return a list of Quote objects
        for the date range.

        Note - you shouldn't instantiate this class directly, but instead
        get an instance by indexing a L{Market} object - see
        L{Market.__getitem__}
        """
        self.market = market

        self.symbol = symbol.lower()
        index = index or self.market.symbolIndex.get(symbol, None)
        if isinstance(index, str):
            index = self.market[index]
        self.index = index

        self.dates = {}

        self.firstKey = "first"
        self.lastKey = "last"

    def getQuote(self):
        """
        Returns a Quote object for this stock
        """
        # construct the query URL
        #?s=MSFT&f=sl1d1t1c1ohgv&e=.csv
        baseUrl = self.baseUrlQuote
        parms = [
            "s=%s" % self.symbol,
            "f=sl1d1t1c1ohgv",
            "e=.csv",
            ]
        url = baseUrl + "?" + "&".join(parms)

        # get the raw csv lines from Yahoo
        lines = urllib.urlopen(url).readlines()

        # and get the quote from it
        return Quote.fromYahooQuote(self, lines[0])

    def __getitem__(self, date):
        """
        Retrieves/creates a Quote object for this ticker's prices
        for a particular date
        """
        logging.debug("date=%s", date)

        logging.debug("%s(1): refs=%s" % (self.symbol, self.refs))

        now = QuoteDate.now()

        if isinstance(date, slice):
            # give back a slice
            priorDate = QuoteDate(date.start)
            wantDate = QuoteDate(date.stop)
        else:
            wantDate = date
            priorDate = None

        if not isinstance(wantDate, QuoteDate):
            wantDate = QuoteDate(wantDate)
        if priorDate != None and not isinstance(priorDate, QuoteDate):
            priorDate = QuoteDate(priorDate)

        # attempted prescience?
        if wantDate > now or priorDate > now:
            raise IndexError("Prescience disabled by order of Homeland Security")

        # no, seek it from db or yahoo
        quotes = self.market.cache.get(self.symbol, wantDate, priorDate)
        if priorDate == None:
            expectedQuotes = 1
        else:
            expectedQuotes = (wantDate - priorDate) + 1
        if len(quotes) != expectedQuotes:
            self._fetch(wantDate, priorDate)
            quotes = self.market.cache.get(self.symbol, wantDate, priorDate)
       
        if isinstance(date, slice):
            return quotes
        else:
            return quotes[0]

    def __repr__(self):
        if self.index:
            idx = "%s/" % self.index.symbol
        else:
            idx = ""
        return "<Ticker:%s%s>" % (idx, self.symbol)

    def __getattr__(self, attr):
        """
        Intercept attribute 'now' to mean a fetch of present prices
        """
        if attr in ['now', 'today']:
            return self.getQuote()

        if attr == 'refs':
            return len(gc.get_referrers(self))

        raise AttributeError(attr)

    def _fetch(self, wantDate, priorDate=None, checkDuplicates=True):
        """
        fetches a range of quotes from site, hopefully
        including given date, and stores these in the database

        argument 'date' MUST be a QuoteDate object
        """
        if not isinstance(wantDate, QuoteDate):
            raise Exception("Invalid date %s: not a QuoteDate" % wantDate)

        # go some days before and after
        if priorDate == None:
            priorDate = wantDate - fetchWindow + 1
        year1, month1, day1 = priorDate.toYmd()
        year2, month2, day2 = (wantDate + 1).toYmd()

        self.market.cache.init(self.symbol, wantDate, priorDate)
        logging.info("fetching %s for %s-%s-%s to %s-%s-%s" % (
                    self.symbol,
                    year1, month1, day1,
                    year2, month2, day2))

        baseUrl = self.baseUrlHistory
        parms = [
            "s=%s" % self.symbol.upper(),
            "a=%d" % (month1-1),
            "b=%d" % day1,
            "c=%d" % year1,
            "d=%d" % (month2-1),
            "e=%d" % day2,
            "f=%d" % year2,
            "g=d",
            "ignore=.csv",
            ]

        url = baseUrl + "?" + "&".join(parms)
        logging.debug("  fetching URL %s", url)
        #print "url=%s" % url

        # get the raw csv lines from Yahoo
        resp = urllib.urlopen(url)
        if resp.getcode() == 404:
            logging.info("%s: No history for %04d-%02d-%02d to %04d-%02d-%02d" % (
                        self.symbol,
                        year1, month1, day1,
                        year2, month2, day2))
            return
        lines = resp.readlines()

        logging.debug("   fetched %s", lines)

        if lines[0].startswith("Date"):
            lines = lines[1:]

        quotes = []
        try:
            quotes = [Quote.fromYahooHistory(self.symbol, line) for line in lines]
        except:
            logging.exception("Failed to process yahoo data")

        if len(quotes) == 0:
            logging.info("%s: No history for %04d-%02d-%02d to %04d-%02d-%02d" % (
                        self.symbol,
                        year1, month1, day1,
                        year2, month2, day2))
        else:        
            # sort quotes into ascending order and fill in any missing dates
            quotes.sort(lambda q1, q2: cmp(q1.date, q2.date))
            self.market.cache.put(quotes)

    def fetchHistory(self, start=None, end=None):
        """
        fetches this stock's entire history - you should only ever
        do this once, and thereafter, invoke
        L{Ticker.updateHistory} to keep the history up to date
        """
        if start == None:
            startDay = QuoteDate.fromYmd(1950, 1, 1)
        else:
            startDay = QuoteDate(end)

        if end == None:
            endDay = QuoteDate.now()
        else:
            endDay = QuoteDate(start)

	cursor = self.market.cache.purge(self.symbol)

        try:
            # now get the whole history, lock stock and barrel
            self._fetch(endDay, startDay, False)
        except KeyboardInterrupt:
            raise
        except:
            logging.exception("%s: failed to fetch" % self.symbol)

    def updateHistory(self, start=None, end=None):
        """
        Updates this stock's history. You should not invoke this
        method unless you have invoked L{Ticker.fetchHistory} at
        some time in the past.
        """
        if end == None:
            end = QuoteDate.now()
        if start == None:
            cursor = self.market.db
            lastdate = cursor.execute("select MAX(date) from history where (symbol='%s')" % self.symbol).fetchone()[0]
	    start = QuoteDate(lastdate) + 1

        if not isinstance(start, QuoteDate):
            start = QuoteDate(start)
        if not isinstance(end, QuoteDate):
            end = QuoteDate(end)

        if end <= start:
            return

        quotes = self.market.cache.get(self.symbol, end, start)
        if (len(quotes) - 1) != (end - start):
            self._fetch(end, start)

class Quote:
    """
    dumb object which wraps quote data
    """
    def __init__(self, symbol, **kw):
        self.symbol = symbol
        self.date=None
        self.open=None
        self.close=None
        self.low=None
        self.high=None
        self.volume=None
        self.adjclose=None
        self.__dict__.update(kw)

    # Normalization concept from http://luminouslogic.com/how-to-normalize-historical-data-for-splits-dividends-etc.htm
    def get_adjopen(self):
        if self.adjclose:
            return (self.adjclose / self.close) * self.open
        else:
            return None
    adjopen = property(fget=get_adjopen)

    def get_adjlow(self):
        if self.adjclose:
            return (self.adjclose / self.close) * self.low
        else:
            return None
    adjlow = property(fget=get_adjlow)

    def get_adjhigh(self):
        if self.adjclose:
            return (self.adjclose / self.close) * self.high
        else:
            return None
    adjhigh = property(fget=get_adjhigh)

    def __repr__(self):

    #        date = "%04d%02d%02d" % (year, month, day)
    #        quoteDict['open'] = float(open)
    #        quoteDict['high'] = float(high)
    #        quoteDict['low'] = float(low)
    #        quoteDict['close'] = float(close)
    #        quoteDict['volume'] = float(vol)
    #        quoteDict['adjclose'] = float(adjclose)


        if None in (self.open, self.close, self.low, self.high, self.adjclose, self.volume):
            return "<Quote:%s/%s>" % (self.symbol, self.date)
        else: 
            if self.close > self.open:
                m = "+%.02f" % (self.close - self.open)
            elif self.close < self.open:
                m = "%.02f" % (self.close - self.open)
            else:
                m = "0.00"
            return "<Quote:%s/%s:m=%s o=%.2f c=%.2f l=%.2f h=%.2f a=%.2f v=%d>" \
                    % (self.symbol,
                       self.date,
                       m,
                       self.open, self.close,
                       self.low, self.high,
                       self.adjclose,
                       self.volume)

    def fromYahooHistory(symbol, line):
        """
        Static method - reads a raw line from yahoo history
        and returns a Quote object
        """
        #logging.info("fromYahooHistory: line=%s" % repr(line))

        items = csv.reader([line]).next()

        logging.debug("items=%s" % str(items))

        ydate, open, high, low, close, vol, adjclose = items

        # determine date of this next result
        quote = Quote(symbol, 
                      date=QuoteDate.fromYahoo(ydate),
                      open=float(open),
                      close=float(close),
                      low=float(low),
                      high=float(high),
                      volume=int(vol),
                      adjclose=float(adjclose))
        return quote

    fromYahooHistory = staticmethod(fromYahooHistory)

    def fromYahooQuote(symbol, line):
        """
        Static method - given a ticker object and a raw quote line from Yahoo for
        that ticker, build and return a Quote object with that data
        """
        # examples:
        # sym    last   d/m/y     time        change  open   high   low    volume
        # MSFT,  30.49,	6/15/2007,4:00:00 PM, -0.03,  30.88, 30.88, 30.43, 100941384
        # TEL.NZ,4.620, 6/15/2007,12:58am,    0.000,  4.640, 4.640, 4.590, 3692073

        items = csv.reader([line]).next()
        sym, last, date, time, change, open, high, low, volume = items

        # massage/convert the fields
        sym = sym.lower()
        last = float(last)

        day, month, year = [int(f) for f in date.split("/")]

        date = QuoteDate.fromYmd(year, month, day)
        if change.startswith("-"):
            change = -float(change[1:])
        elif change.startswith("+"):
            change = float(change[1:])
        else:
            change = float(change)
        open = float(open)
        close = last
        high = float(high)
        low = float(low)
        volume = float(volume)
        adjclose = last

        # got all the bits, now can wrap a Quote
        return Quote(sym,
                     date=date,
                     open=open,
                     close=last,
                     high=high,
                     low=low,
                     volume=volume,
                     adjclose=adjclose)

    fromYahooQuote = staticmethod(fromYahooQuote)

    def fromRow(row):
        """
        Static method - Constructs a L{Quote} object from a given sqlite row
        """
        return Quote(symbol=row[1],
                    date=row[2],
                    open=row[3],
                    close=row[4],
                    low=row[5],
                    high=row[6],
                    volume=row[7],
                    adjclose=row[8])

    fromRow = staticmethod(fromRow)


class QuoteDate(int):
    """
    Simple int subclass that represents yyyymmdd quote dates
    """
    def __new__(cls, val):
        """
        Create a QuoteDate object. Argument can be an int or string,
        as long as it is in the form YYYYMMDD
        """
        if isinstance(val, datetime.datetime):
            val = (val.year * 10000) + (val.month * 100) + val.day
        inst = super(QuoteDate, cls).__new__(cls, val)
        inst.year, inst.month, inst.day = inst.toYmd()
        return inst

    def __add__(self, n):
        """
        Adds n days to this QuoteDate, and returns a new QuoteDate object
        """
        return QuoteDate.fromUnix(self.toUnix() + n * DAYSECS)

    def __sub__(self, n):
        """
        Subtracts n days from this QuoteDate, and returns a new QuoteDate object
        """
        if isinstance(n, QuoteDate):
            return int((self.toUnix() - n.toUnix()) / DAYSECS)
        else:
            return QuoteDate.fromUnix(self.toUnix() - n * DAYSECS)

    def toUnix(self):
        """
        Converts this QuoteDate object to a unix 'seconds since epoch'
        time
        """
        return time.mktime(self.toYmd() + (0,0,0,0,0,0))

    def fromUnix(udate):
        """
        Static method - converts a unix 'seconds since epoch'
        date into a QuoteDate string
        """
        return QuoteDate(time.strftime("%Y%m%d", time.localtime(float(udate))))

    fromUnix = staticmethod(fromUnix)

    def toDateTime(self):
        return datetime.date.fromtimestamp(self.toUnix())

    def now():
        """
        Static method - returns a QuoteDate object for today
        """
        return QuoteDate.fromUnix(time.time())

    now = staticmethod(now)

    def toYmd(self):
        """
        returns tuple (year, month, day)
        """
        s = "%08d" % self
        return int(s[0:4]), int(s[4:6]), int(s[6:8])

    def fromYmd(year, month, day):
        """
        Static method - instantiates a QuoteDate
        set to given year, month, day
        """
        return QuoteDate("%04d%02d%02d" % (int(year), int(month), int(day)))

    fromYmd = staticmethod(fromYmd)

    def fromYahoo(ydate):
        """
        Static method - converts a 'yyyy-mmm-dd'
        yahoo date into a QuoteDate object
        """
        dateFields = ydate.split("-")
        year = int(dateFields[0])
        try:
            monthStr = MONTH2NUM[dateFields[1]]
        except:
            monthStr = dateFields[1]
        month = int(monthStr)
        day = int(dateFields[2])
        return QuoteDate.fromYmd(year, month, day)

    fromYahoo = staticmethod(fromYahoo)

########NEW FILE########
__FILENAME__ = yahoo
#!/usr/bin/env python
LICENSE="""
Copyright (C) 2011  Michael Ihde

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import os
import datetime
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import matplotlib.ticker as ticker
import matplotlib.dates as dates
from pycommando.commando import command
from utils.YahooQuote import *

@command("db_ls")
def list():
    """
    Lists the symbols that are in the database
    """
    return Market().cache.symbols()

@command("db_up")
def update(symbol):
    """
    Updates the historical daily prices for all stocks
    currently in the database.
    """
    market = Market()
    try:
        ticker = market[symbol]
        if ticker != None:
            ticker.updateHistory()
    except IndexError:
        market.updateHistory()

@command("db_flush")
def flush():
    """
    Completely removes the yahoo cache
    """
    os.remove(YahooQuote.CACHE) 
    Market()._dbInit()

@command("db_load")
def load(symbol=None):
    """
    Load's historical prices for a given ticker or index
    symbol from 1950 until today.  This may take a long time,
    especially if you don't provide a symbol because it will
    cache all major indexes from 1950 until today.
    """
    market = Market()
    if symbol == None:
        market.fetchHistory()
    else:
        ticker = market[symbol]
        if ticker != None:
            ticker.fetchHistory()

@command("db_fetch")
def fetch(symbol, start="today", end="today"):
    """
    Prints the daily price for the stock on a given day.
    """
    if start.upper() == "TODAY":
        day_start = datetime.date.today()
    else:
        day_start = datetime.datetime.strptime(start, "%Y-%m-%d")
    day_start = (day_start.year * 10000) + (day_start.month * 100) + day_start.day

    if end.upper() == "TODAY":
        day_end = None
    else:
        day_end = datetime.datetime.strptime(end, "%Y-%m-%d")
        day_end = (day_end.year * 10000) + (day_end.month * 100) + day_end.day

    ticker = Market()[symbol]
    if ticker != None:
        if day_end == None:
            return ticker[day_start]
        else:
            return ticker[day_start:day_end]

@command("db_plot")
def plot(symbol, start, end):
    """
    Prints the daily price for the stock on a given day.
    """

    quotes = fetch(symbol, start, end)
    x_data = [QuoteDate(q.date).toDateTime() for q in quotes]
    y_data = [q.adjclose for q in quotes]

    fig = plt.figure()
    fig.canvas.set_window_title("%s %s-%s" % (symbol, start, end))
    sp = fig.add_subplot(111)
    sp.plot(x_data, y_data, '-')
    x_locator = dates.AutoDateLocator()
    sp.xaxis.set_major_locator(x_locator)
    sp.xaxis.set_major_formatter(dates.AutoDateFormatter(x_locator))
    fig.autofmt_xdate()
    fig.show()

########NEW FILE########
