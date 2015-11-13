__FILENAME__ = init_sqlite
# Sebastian Raschka 01/26/2014
# Intialization of a SQLite Database with 6056212
# entries from a data file.
# Uses pyprind.ProgPercent() to visualize the progess as percentage

import sqlite3
import subprocess
import time

input_file = './id_list.txt'

# get line count of the input file
line_cnt = subprocess.check_output(['wc', '-l', input_file])
line_cnt = int(line_cnt.split()[0])

print('Processing %d lines ...' % (line_cnt))
start_time = time.clock()

# open connection and create a new database
conn = sqlite3.connect('./my_sqlite_db.sqlite')
c = conn.cursor()
c.execute('CREATE TABLE my_db (ID INT PRIMARY KEY, column2 TEXT)')

# read entries from a text file and add them to the database
with open(input_file, 'r') as in_file:
    for line in in_file:
        line = line.strip()
        c.execute('INSERT INTO my_db VALUES (%s, "yes")' % (line))

# report CPU time
end_time = time.clock()
total_time = end_time - start_time
print('Time elapsed: {0:.4f} sec'.format(total_time))

# commit changes and close connection
conn.commit()
conn.close()



########NEW FILE########
__FILENAME__ = init_sqlite_percentind
# Sebastian Raschka 01/26/2014
# Intialization of a SQLite Database with 6056212
# entries from a data file

import sqlite3
import subprocess
import pyprind

input_file = './id_list.txt'

# get line count of the input file
line_cnt = subprocess.check_output(['wc', '-l', input_file])
line_cnt = int(line_cnt.split()[0])

print('Processing %d lines ...' % (line_cnt))

# instatiating new progress bar object
my_perc = pyprind.ProgPercent(line_cnt)

# open connection and create a new database
conn = sqlite3.connect('./my_sqlite_db.sqlite')
c = conn.cursor()
c.execute('CREATE TABLE my_db (ID INT PRIMARY KEY, column2 TEXT)')

# read entries from a text file and add them to the database
with open(input_file, 'r') as in_file:
    for line in in_file:
        line = line.strip()
        c.execute('INSERT INTO my_db VALUES (%s, "yes")' % (line))

        # update the progress bar
        my_perc.update()


# End the progress tracking adn report CPU time
my_perc.finish()

# commit changes and close connection
conn.commit()
conn.close()





########NEW FILE########
__FILENAME__ = init_sqlite_progbar
# Sebastian Raschka 01/26/2014
# Intialization of a SQLite Database with 6056212
# entries from a data file.
# Uses pyprind.ProgBar() to visualize the progess as bar

import sqlite3
import subprocess
import pyprind

input_file = './id_list.txt'

# get line count of the input file
line_cnt = subprocess.check_output(['wc', '-l', input_file])
line_cnt = int(line_cnt.split()[0])

print('Processing %d lines ...' % (line_cnt))

# instatiating new progress bar object
my_bar = pyprind.ProgBar(line_cnt)

# open connection and create a new database
conn = sqlite3.connect('./my_sqlite_db.sqlite')
c = conn.cursor()
c.execute('CREATE TABLE my_db (ID INT PRIMARY KEY, column2 TEXT)')

# read entries from a text file and add them to the database
with open(input_file, 'r') as in_file:
    for line in in_file:
        line = line.strip()
        c.execute('INSERT INTO my_db VALUES (%s, "yes")' % (line))

        # update the progress bar
        my_bar.update()


# End the progress tracking adn report CPU time
my_bar.finish()

# commit changes and close connection
conn.commit()
conn.close()




########NEW FILE########
__FILENAME__ = barplot_init_sqlite
# Sebastian Raschka 01/26/2014
# Plotting performance of init_sqlite_.py scripts
# bar chart of relative comparison with variances as error bars

import numpy as np
import matplotlib.pyplot as plt

performance = [
                253.5762,
                270.3271,
                292.1328
              ]
variance = [
            2.5117,
            1.8397,
            1.0503
           ]
scripts = [
            'init_sqlite.py', 
            'init_sqlite_progbar.py', 
            'init_sqlite_percentind.py'
          ]

x_pos = np.arange(len(scripts))

plt.bar(x_pos, performance, yerr=variance, align='center', alpha=0.5)
plt.xticks(x_pos, scripts)
plt.ylim([0,350])

plt.ylabel('CPU time in sec')
plt.title('PyPrind Benchmark on SQLite Database Initialization\nwith 6056212 entries')

#plt.show()
plt.savefig(‘./barplot_init_sqlite.png')

########NEW FILE########
__FILENAME__ = init_sqlite_lines_per_sec
# Sebastian Raschka 01/26/2014
# Plotting performance of init_sqlite_.py scripts
# Barplot of additional computing time as lines per sec

import numpy as np
import matplotlib.pyplot as plt

performance = [
                361546.9081,
                157073.5612,
              ]
scripts = [
            'init_sqlite_progbar.py', 
            'init_sqlite_percentind.py'
          ]

x_pos = np.arange(len(scripts))

plt.bar(x_pos, performance, align='center', alpha=0.5)
plt.xticks(x_pos, scripts)
#plt.ylim([0,350])

plt.ylabel('Lines per sec')
plt.title('PyPrind Benchmark: How many lines per second can be processed\n\
        for 1 second of performance loss?')

#plt.show()
plt.savefig('./init_sqlite_lines_per_sec.png')

########NEW FILE########
__FILENAME__ = percentage_indicator
# Sebastian Raschka 01/25/2014
# Percentage Indicator Examples 

import pyprind

def example_1():
    n = 1000000
    my_perc = pyprind.ProgPercent(n)
    for i in range(n):
        # do some computation
        my_perc.update()

if __name__ == '__main__':
    example_1() 


########NEW FILE########
__FILENAME__ = progress_bar
# Sebastian Raschka 01/25/2014
# Progress Bar Examples 

import pyprind


def example_1():
    n = 1000000
    my_bar = pyprind.ProgBar(n, width=40)
    for i in range(n):
       my_bar.update()


if __name__ == '__main__':
    example_1() 


########NEW FILE########
__FILENAME__ = init_sqlite
# Sebastian Raschka 02/01/2014
# Intialization of a SQLite Database with 6056212
# entries from a data file.


import sqlite3
import subprocess
import time

input_file = './id_list.txt'

# get line count of the input file
line_cnt = subprocess.check_output(['wc', '-l', input_file])
line_cnt = int(line_cnt.split()[0])

print('Processing %d lines ...' % (line_cnt))
start_time = time.clock()

# open connection and create a new database
conn = sqlite3.connect('./my_sqlite_db.sqlite')
c = conn.cursor()
c.execute('CREATE TABLE my_db (id INT PRIMARY KEY, rank TEXT)')

# read entries from a text file and add them to the database
with open(input_file, 'r') as in_file:
    for line in in_file:
        line = line.strip().split(',')
        c.execute('INSERT INTO my_db (id, rank) VALUES (%s, "%s")' 
            % (line[0],line[1]))

# report CPU time
end_time = time.clock()
total_time = end_time - start_time
print('Time elapsed: {0:.4f} sec'.format(total_time))

# commit changes and close connection
conn.commit()
conn.close()



########NEW FILE########
__FILENAME__ = init_sqlite_percentind
# Sebastian Raschka 02/01/2014
# Intialization of a SQLite Database with 6056212
# entries from a data file which consists of 2 comma-separated columns
# Uses pyprind.ProgPercent() to visualize the progess as percentage

import sqlite3
import subprocess
import pyprind

input_file = './id_list.txt'

# get line count of the input file
line_cnt = subprocess.check_output(['wc', '-l', input_file])
line_cnt = int(line_cnt.split()[0])

print('Processing %d lines ...' % (line_cnt))

# instatiating new progress bar object
my_perc = pyprind.ProgPercent(line_cnt)

# open connection and create a new database
conn = sqlite3.connect('./my_sqlite_db.sqlite')
c = conn.cursor()
c.execute('CREATE TABLE my_db (ID INT PRIMARY KEY, rank TEXT)')

# read entries from a text file and add them to the database
with open(input_file, 'r') as in_file:
    for line in in_file:
        line = line.strip().split(',')
        c.execute('INSERT INTO my_db (id, rank) VALUES (%s, "%s")' 
            % (line[0],line[1]))

        # update the progress bar
        my_perc.update()


# commit changes and close connection
conn.commit()
conn.close()





########NEW FILE########
__FILENAME__ = init_sqlite_progbar
# Sebastian Raschka 02/01/2014
# Intialization of a SQLite Database with 6056212
# entries from a data file which consists of 2 comma-separated columns
# Uses pyprind.ProgBar() to visualize the progess as bar

import sqlite3
import subprocess
import pyprind

input_file = './id_list.txt'

# get line count of the input file
line_cnt = subprocess.check_output(['wc', '-l', input_file])
line_cnt = int(line_cnt.split()[0])

print('Processing %d lines ...' % (line_cnt))

# instatiating new progress bar object
my_bar = pyprind.ProgBar(line_cnt)

# open connection and create a new database
conn = sqlite3.connect('./my_sqlite_db.sqlite')
c = conn.cursor()
c.execute('CREATE TABLE my_db (ID INT PRIMARY KEY, rank TEXT)')

# read entries from a text file and add them to the database
with open(input_file, 'r') as in_file:
    for line in in_file:
        line = line.strip().split(',')
        c.execute('INSERT INTO my_db (id, rank) VALUES (%s, "%s")' 
            % (line[0],line[1]))

        # update the progress bar
        my_bar.update()


# commit changes and close connection
conn.commit()
conn.close()




########NEW FILE########
__FILENAME__ = barplot_init_sqlite
# Sebastian Raschka 01/26/2014
# Plotting performance of init_sqlite_.py scripts
# bar chart of relative comparison with variances as error bars

import numpy as np
import matplotlib.pyplot as plt

performance = [
                285.8613,
                306.6960,
                326.3473
              ]
variance = [
            9.1784,
            1.0644,
            0.6383
           ]
scripts = [
            'init_sqlite.py', 
            'init_sqlite_progbar.py', 
            'init_sqlite_percentind.py'
          ]

x_pos = np.arange(len(scripts))

plt.bar(x_pos, performance, yerr=variance, align='center', alpha=0.5)
plt.xticks(x_pos, scripts)
plt.ylim([0,400])

plt.ylabel('CPU time in sec')
plt.title('PyPrind Benchmark on SQLite Database Initialization\nwith 6056212 entries')

#plt.show()
plt.savefig('./barplot_init_sqlite.png')

########NEW FILE########
__FILENAME__ = init_sqlite_lines_per_sec
# Sebastian Raschka 01/26/2014
# Plotting performance of init_sqlite_.py scripts
# Barplot of additional computing time as lines per sec

import numpy as np
import matplotlib.pyplot as plt

performance = [
                290678.6424,
                149587.5618,
              ]
scripts = [
            'init_sqlite_progbar.py', 
            'init_sqlite_percentind.py'
          ]

x_pos = np.arange(len(scripts))

plt.bar(x_pos, performance, align='center', alpha=0.5)
plt.xticks(x_pos, scripts)
#plt.ylim([0,350])

plt.ylabel('Lines per sec')
plt.title('PyPrind Benchmark: How many lines per second can be processed\n\
        for 1 second of performance loss?')

#plt.show()
plt.savefig('./init_sqlite_lines_per_sec.png')

########NEW FILE########
__FILENAME__ = ex1_percentage_indicator_stderr
# Sebastian Raschka 01/25/2014
# Percentage Indicator Examples 

import pyprind


def example_1():
    n = 10000000
    my_perc = pyprind.ProgPercent(n, stream=2)
    for i in range(n):
        # do some computation
        my_perc.update()

if __name__ == '__main__':
    example_1() 


########NEW FILE########
__FILENAME__ = ex1_percentage_indicator_stdout
# Sebastian Raschka 01/25/2014
# Percentage Indicator Examples 

import pyprind


def example_1():
    n = 1000000
    my_perc = pyprind.ProgPercent(n, stream=1)
    for i in range(n):
        # do some computation
        my_perc.update()


if __name__ == '__main__':
    example_1() 

########NEW FILE########
__FILENAME__ = ex1_progress_bar_stderr
# Sebastian Raschka 01/25/2014
# Progress Bar Examples 

import pyprind


def example_1():
    n = 1000000
    my_bar = pyprind.ProgBar(n, width=40, stream=2)
    for i in range(n):
        my_bar.update()


if __name__ == '__main__':
    example_1() 


########NEW FILE########
__FILENAME__ = ex1_progress_bar_stdout
# Sebastian Raschka 01/25/2014
# Progress Bar Examples 

import pyprind


def example_1():
    n = 1000000
    my_bar = pyprind.ProgBar(n, stream=1)
    for i in range(n):
        # do some computation
        my_bar.update()


if __name__ == '__main__':
    example_1() 


########NEW FILE########
__FILENAME__ = ex2_percent_indicator_allargs
# Sebastian Raschka 01/25/2014
# Progress Bar Examples 

import pyprind


def example_2():
    n = 1000000
    my_per = pyprind.ProgPercent(n, stream=1, track_time=True, title='My Percent Indicator', monitor=True)
    for i in range(n):
        # do some computation
        my_per.update()
    print('\n\nPrint tracking object ...\n')
    print(my_per)

if __name__ == '__main__':
    example_2()
         


########NEW FILE########
__FILENAME__ = ex2_progressbar_allargs
# Sebastian Raschka 01/25/2014
# Progress Bar Examples 

import pyprind


def example_2():
    n = 1000000
    my_bar = pyprind.ProgBar(n, stream=1, width=30, track_time=True, title='My Progress Bar', monitor=True)
    for i in range(n):
        # do some computation
        my_bar.update()
    print('\n\nPrint tracking object ...\n')
    print(my_bar)

if __name__ == '__main__':
    example_2()
         


########NEW FILE########
__FILENAME__ = ex3_percentage_indicator_monitor
# Sebastian Raschka 01/25/2014
# Percentage Indicator Examples 

import pyprind


def example_3():
    n = 1000000
    my_perc = pyprind.ProgPercent(n, stream=1, title='example3', monitor=True)
    for i in range(n):
        # do some computation
        my_perc.update()
    print(my_perc)

if __name__ == '__main__':
    example_3() 

########NEW FILE########
__FILENAME__ = ex3_progress_bar_monitor
# Sebastian Raschka 01/25/2014
# Progress Bar Examples 

import pyprind


def example_3():
    n = 1000000
    my_bar = pyprind.ProgBar(n, stream=1, title='example3', monitor=True)
    for i in range(n):
        # do some computation
        my_bar.update()
    print(my_bar)



if __name__ == '__main__':
    example_3() 


########NEW FILE########
__FILENAME__ = init_sqlite_percentind
# Sebastian Raschka 02/01/2014
# Intialization of a SQLite Database with 6056212
# entries from a data file which consists of 2 comma-separated columns
# Uses pyprind.ProgPercent() to visualize the progess as percentage

import sqlite3
import subprocess
import pyprind

input_file = './id_list.txt'

# get line count of the input file
line_cnt = subprocess.check_output(['wc', '-l', input_file])
line_cnt = int(line_cnt.split()[0])

print('Processing %d lines ...' % (line_cnt))

# instantiating new percentage indicator object
my_perc = pyprind.ProgPercent(line_cnt)

# open connection and create a new database
conn = sqlite3.connect('./my_sqlite_db.sqlite')
c = conn.cursor()
c.execute('CREATE TABLE my_db (ID INT PRIMARY KEY, rank TEXT)')

# read entries from a text file and add them to the database
with open(input_file, 'r') as in_file:
    for line in in_file:
        line = line.strip().split(',')
        c.execute('INSERT INTO my_db (id, rank) VALUES (%s, "%s")' 
            % (line[0],line[1]))

        # update the percentage indicator
        my_perc.update()


# commit changes and close connection
conn.commit()
conn.close()





########NEW FILE########
__FILENAME__ = init_sqlite_progbar
# Sebastian Raschka 02/01/2014
# Intialization of a SQLite Database with 6056212
# entries from a data file which consists of 2 comma-separated columns
# Uses pyprind.ProgBar() to visualize the progess as bar

import sqlite3
import subprocess
import pyprind

input_file = './id_list.txt'

# get line count of the input file
line_cnt = subprocess.check_output(['wc', '-l', input_file])
line_cnt = int(line_cnt.split()[0])

print('Processing %d lines ...' % (line_cnt))

# instantiating new progress bar object
my_bar = pyprind.ProgBar(line_cnt)

# open connection and create a new database
conn = sqlite3.connect('./my_sqlite_db.sqlite')
c = conn.cursor()
c.execute('CREATE TABLE my_db (ID INT PRIMARY KEY, rank TEXT)')

# read entries from a text file and add them to the database
with open(input_file, 'r') as in_file:
    for line in in_file:
        line = line.strip().split(',')
        c.execute('INSERT INTO my_db (id, rank) VALUES (%s, "%s")' 
            % (line[0],line[1]))

        # update the progress bar
        my_bar.update()


# commit changes and close connection
conn.commit()
conn.close()




########NEW FILE########
__FILENAME__ = progbar
# Sebastian Raschka 2014
#
# Progress Bar class to instantiate a progress bar object
# that is printed to the standard output screen to visualize the
# progress in a iterative Python procedure

from math import floor
from pyprind.prog_class import Prog


class ProgBar(Prog):
    """
    Initializes a progress bar object that allows visuzalization
    of an iterational computation in the standard output screen. 

    Keyword Arguments:
        iterations (int): number of iterations of the computation
        track_time (bool): default True. Prints elapsed time when loop has finished
        width (int): default 30. Sets the progress bar width in characters.
        stream (int): default 2. Takes 1 for stdout, 2 for stderr, or given stream object
        title (str): default ''. A title for the progress bar
        monitor (bool): default False. Monitors CPU and memory usage if True 
            (requires 'psutil' package).

    """
    def __init__(self, iterations, track_time=True, width=30, stream=2, title='', monitor=False):
        Prog.__init__(self, iterations, track_time, stream, title, monitor)
        self.bar_width = width
        self._adjust_width()
        self.last_progress = 0
        self._print_labels()
        self._print_progress_bar(0)
        if monitor:
            try:
                self.process.get_cpu_percent()
                self.process.get_memory_percent()
            except AttributeError: # old version of psutil
                cpu_total = self.process.cpu_percent()
                mem_total = self.process.memory_percent()   

    def _adjust_width(self):
        """Shrinks bar if number of iterations is less than the bar width"""
        if self.bar_width > self.max_iter:
            self.bar_width = int(self.max_iter) 
            # some Python 3.3.3 users specifically
            # on Linux Red Hat 4.4.7-1, GCC v. 4.4.7
            # reported that self.max_iter was converted to
            # float. Thus this fix to prevent float multiplication of chars.

    def _print_labels(self):
        self._stream_out('0% {} 100%\n'.format(' ' * (self.bar_width - 6)))
        self._stream_flush()

    def _print_progress_bar(self, progress):
        remaining = self.bar_width - progress
        self._stream_out('[{}{}]'.format('#' * int(progress), ' ' * int(remaining)))
        # int() fix for Python 2 users
        self._stream_flush()

    def _print_eta(self):
        self._stream_out(' | ETA[sec]: {:.3f} '.format(self._calc_eta()))
        self._stream_flush()

    def _print_bar(self):
        progress = floor(self._calc_percent() / 100 * self.bar_width)
        if progress > self.last_progress:
            self._stream_out('\r')
            self._print_progress_bar(progress)
            if self._calc_eta() and self.track:
                self._print_eta()
        self.last_progress = progress

    def update(self, iterations=1):
        """
        Updates the progress bar in every iteration of the task.

        Keyword arguments:
            iterations (int): default argument can be changed to integer values
                >=1 in order to update the progress indicators more than once 
                per iteration.

        """
        self.cnt += iterations
        self._print_bar()
        self._finish() 

########NEW FILE########
__FILENAME__ = progpercent
# Sebastian Raschka 2014
#
# Progress Percentage class to instantiate a percentage indicator object
# that is printed to the standard output screen to visualize the
# progress in a iterative Python procedure

from pyprind.prog_class import Prog


class ProgPercent(Prog):
    """
    Initializes a percentage indicator object that allows visuzalization
    of an iterational computation in the standard output screen. 

    Keyword Arguments:
        iterations (int): number of iterations of the computation
        track_time (bool): default True. Prints elapsed time when loop has finished
        stream (int): default 2. Takes 1 for stdout, 2 for stderr, or given stream object
        title (str): default ''. A title for the progress bar
        monitor (bool): default False. Monitors CPU and memory usage if True 
            (requires 'psutil' package).

    """
    def __init__(self, iterations, track_time=True, stream=2, title='', monitor=False):
        Prog.__init__(self, iterations, track_time, stream, title, monitor)
        self.perc = 0
        self._print_update()
        if monitor:
            try:
                self.process.get_cpu_percent()
                self.process.get_memory_percent()
            except AttributeError: # old version of psutil
                cpu_total = self.process.cpu_percent()
                mem_total = self.process.memory_percent()   

    def _print_update(self):
        """Prints formatted integer percentage and tracked time to the screen."""
        self._stream_out('\r[%3d %%]' % (self.perc))
        if self.track:
            self._stream_out(' elapsed[sec]: {:.3f}'.format(self._elapsed()))
            if self._calc_eta():
                self._stream_out(' | ETA[sec]: {:.3f} '.format(self._calc_eta()))  
            self._stream_flush()

    def update(self, iterations=1):
        """
        Updates the progress bar in every iteration of the task.

        Keyword arguments:
            iterations (int): default argument can be changed to integer values
                >=1 in order to update the progress indicators more than once 
                per iteration.

        """
        self.cnt += iterations
        next_perc = self._calc_percent()
        if next_perc > self.perc:
            self.perc = next_perc
            self._print_update()
            self._stream_flush()
        self._finish()

########NEW FILE########
__FILENAME__ = prog_class
import time
import sys
import os
from io import UnsupportedOperation

class Prog():
    def __init__(self, iterations, track_time, stream, title, monitor):
        """ Initializes tracking object. """
        self.cnt = 0
        self.title = title
        self.max_iter = float(iterations) # to support Python 2.x
        self.track = track_time
        self.start = time.time()
        self.end = None
        self.total_time = 0.0
        self.monitor = monitor
        self.stream = stream
        self._stream_out = self._no_stream
        self._stream_flush = self._no_stream
        self._check_stream()
        self._print_title()
        
        if self.monitor:
            import psutil
            self.process = psutil.Process()

    def _check_stream(self):
        """ Determines which output stream (stdout, stderr, or custom) to use. """
        
        try:
            if self.stream == 1 and os.isatty(sys.stdout.fileno()):
                self._stream_out = sys.stdout.write
                self._stream_flush = sys.stdout.flush
            elif self.stream == 2 and os.isatty(sys.stderr.fileno()):
                self._stream_out = sys.stderr.write
                self._stream_flush = sys.stderr.flush
        except UnsupportedOperation: # a fix for IPython notebook "IOStream has no fileno."
            if self.stream == 1:
                self._stream_out = sys.stdout.write
                self._stream_flush = sys.stdout.flush
            elif self.stream == 2:
                self._stream_out = sys.stderr.write
                self._stream_flush = sys.stderr.flush
        else: 
            if self.stream is not None and hasattr(self.stream, 'write'):
                self._stream_out = self.stream.write
                self._stream_flush = self.stream.flush
            else:
                print('Warning: No valid output stream.')



    def _elapsed(self):
        """ Returns elapsed time at update. """
        return time.time() - self.start

    def _calc_eta(self):
        """ Calculates estimated time left until completion. """
        elapsed = self._elapsed()
        if self.cnt == 0 or elapsed < 0.001:
            return None
        rate = float(self.cnt) / elapsed
        return (float(self.max_iter) - float(self.cnt)) / rate

    def _calc_percent(self):
        """Calculates the rel. progress in percent with 2 decimal points."""
        return round(self.cnt / self.max_iter * 100, 2)

    def _no_stream(self, text=None):
        """ Called when no valid output stream is available. """
        pass

    def _finish(self):
        """ Determines if maximum number of iterations (seed) is reached. """
        if self.cnt == self.max_iter:
            self.total_time = self._elapsed()
            self.end = time.time()
            if self.track:
                self._stream_out('\nTotal time elapsed: {:.3f} sec'.format(self.total_time))
            self._stream_out('\n')

    def _print_title(self):
        """ Prints tracking title at initialization. """
        if self.title:
            self._stream_out('{}\n'.format(self.title))
            self._stream_flush()

    def __repr__(self):
        str_start = time.strftime('%m/%d/%Y %H:%M:%S', time.localtime(self.start))
        str_end = time.strftime('%m/%d/%Y %H:%M:%S', time.localtime(self.end))
        if not self.monitor:
            return """Title: {}
                      Started: {}
                      Finished: {}
                      Total time elapsed: {:.3f} sec""".format(self.title, str_start, 
                                                               str_end, self.total_time)
        else:
            try:
                cpu_total = self.process.get_cpu_percent()
                mem_total = self.process.get_memory_percent()
            except AttributeError: # old version of psutil
                cpu_total = self.process.cpu_percent()
                mem_total = self.process.memory_percent()    

            return """Title: {}
                      Started: {}
                      Finished: {}
                      Total time elapsed: {:.3f} sec
                      CPU %: {:2f}
                      Memory %: {:2f}""".format(self.title, str_start, str_end, self.total_time, cpu_total, mem_total)

    def __str__(self):
        return self.__repr__()

########NEW FILE########
__FILENAME__ = custom_stream
import sys
import pyprind

n= 1000000
mbar = pyprind.ProgBar(n, stream=sys.stdout)

for i in range(n):
    mbar.update()

mper = pyprind.ProgPercent(n, stream=sys.stdout)
for i in range(n):
    mper.update()

mbar2 = pyprind.ProgBar(n, stream='test')
for i in range(n):
    mbar2.update()


########NEW FILE########
__FILENAME__ = test_small_progbar
import pyprind as ppr

n = 1000
mbar = ppr.ProgBar(n)
for i in range(n):
    mbar.update()

print('\n\nshort progress bar')

n = 1
mbar2 = ppr.ProgBar(n)
for i in range(n):
    mbar2.update()


########NEW FILE########
