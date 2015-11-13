__FILENAME__ = test
from datetime import datetime

import gitbench.git as git
reload(git)

# repo_path = '/home/wesm/code/pandas'
# repo = git.GitRepo(repo_path)

# hists = repo.messages

# def churn_graph(repo):
#     omit_paths = [path for path in churn.major_axis
#                   if not path.endswith('.pyx') or not path.endswith('.py')]
#     omit_shas = [sha for sha in churn.minor_axis
#                  if 'LF' in hists[sha]]
#     omit_shas.append('dcf3490')

#     by_date = repo.get_churn(omit_shas=omit_shas, omit_paths=omit_paths)
#     by_date = by_date.drop([datetime(2011, 6, 10)])

#     # clean out days where I touched Cython
#     by_date = by_date[by_date < 5000]
#     return by_date

REPO_PATH = '/home/wesm/code/pandas'
TMP_DIR = '/home/wesm/tmp/gb_pandas'
BUILD = """
python setup.py build_ext --inplace
"""

repo = git.GitRepo(REPO_PATH)

burp = git.BenchRepo(REPO_PATH, TMP_DIR, BUILD)

########NEW FILE########
__FILENAME__ = api
# pylint: disable=W0611

from vbench.benchmark import Benchmark
from vbench.db import BenchmarkDB
from vbench.runner import BenchmarkRunner
from vbench.git import GitRepo
from vbench.utils import collect_benchmarks

########NEW FILE########
__FILENAME__ = benchmark
# pylint: disable=W0122

from cStringIO import StringIO

import cProfile
try:
    import pstats
except ImportError:
    # pstats.py was not available in python 2.6.6 distributed on Debian squeeze
    # systems and was included only starting from 2.6.7-2.  That is why import
    # from a local copy
    import _pstats as pstats

import gc
import hashlib
import time
import traceback
import inspect

# from pandas.util.testing import set_trace


class Benchmark(object):

    def __init__(self, code, setup, ncalls=None, repeat=3, cleanup=None,
                 name=None, module_name=None, description=None, start_date=None,
                 logy=False):
        self.code = code
        self.setup = setup
        self.cleanup = cleanup or ''
        self.ncalls = ncalls
        self.repeat = repeat

        if name is None:
            try:
                name = _get_assigned_name(inspect.currentframe().f_back)
            except:
                pass

        self.name = name
        self.module_name = module_name

        self.description = description
        self.start_date = start_date
        self.logy = logy

    def __repr__(self):
        return "Benchmark('%s')" % self.name

    def _setup(self):
        ns = globals().copy()
        exec self.setup in ns
        return ns

    def _cleanup(self, ns):
        exec self.cleanup in ns

    @property
    def checksum(self):
        return hashlib.md5(self.setup + self.code + self.cleanup).hexdigest()

    def profile(self, ncalls):
        prof = cProfile.Profile()
        ns = self._setup()

        code = compile(self.code, '<f>', 'exec')

        def f(*args, **kw):
            for i in xrange(ncalls):
                exec code in ns
        prof.runcall(f)

        self._cleanup(ns)

        return pstats.Stats(prof).sort_stats('cumulative')

    def get_results(self, db_path):
        from vbench.db import BenchmarkDB
        db = BenchmarkDB.get_instance(db_path)
        return db.get_benchmark_results(self.checksum)

    def run(self):
        ns = None
        try:
            stage = 'setup'
            ns = self._setup()

            stage = 'benchmark'
            result = magic_timeit(ns, self.code, ncalls=self.ncalls,
                                  repeat=self.repeat, force_ms=True)
            result['succeeded'] = True
        except:
            buf = StringIO()
            traceback.print_exc(file=buf)
            result = {'succeeded': False,
                      'stage': stage,
                      'traceback': buf.getvalue()}

        if ns:
            self._cleanup(ns)
        return result

    def _run(self, ns, ncalls, disable_gc=False):
        if ncalls is None:
            ncalls = self.ncalls
        code = self.code
        if disable_gc:
            gc.disable()

        start = time.clock()
        for _ in xrange(ncalls):
            exec code in ns

        elapsed = time.clock() - start
        if disable_gc:
            gc.enable()

        return elapsed

    def to_rst(self, image_path=None):
        output = """**Benchmark setup**

.. code-block:: python

%s

**Benchmark statement**

.. code-block:: python

%s

""" % (indent(self.setup), indent(self.code))

        if image_path is not None:
            output += ("**Performance graph**\n\n.. image:: %s"
                       "\n   :width: 6in" % image_path)

        return output

    def plot(self, db_path, label='time', ax=None, title=True):
        import matplotlib.pyplot as plt
        from matplotlib.dates import MonthLocator, DateFormatter

        results = self.get_results(db_path)

        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)

        timing = results['timing']
        if self.start_date is not None:
            timing = timing.truncate(before=self.start_date)

        timing.plot(ax=ax, style='b-', label=label)
        ax.set_xlabel('Date')
        ax.set_ylabel('milliseconds')

        if self.logy:
            ax2 = ax.twinx()
            try:
                timing.plot(ax=ax2, label='%s (log scale)' % label,
                            style='r-',
                            logy=self.logy)
                ax2.set_ylabel('milliseconds (log scale)')
                ax.legend(loc='best')
                ax2.legend(loc='best')
            except ValueError:
                pass

        ylo, yhi = ax.get_ylim()

        if ylo < 1:
            ax.set_ylim([0, yhi])

        formatter = DateFormatter("%b %Y")
        ax.xaxis.set_major_locator(MonthLocator())
        ax.xaxis.set_major_formatter(formatter)
        ax.autoscale_view(scalex=True)

        if title:
            ax.set_title(self.name)

        return ax


def _get_assigned_name(frame):
    import ast

    # hackjob to retrieve assigned name for Benchmark
    info = inspect.getframeinfo(frame)
    line = info.code_context[0]
    path = info.filename
    lineno = info.lineno - 1

    def _has_assignment(line):
        try:
            mod = ast.parse(line.strip())
            return isinstance(mod.body[0], ast.Assign)
        except SyntaxError:
            return False

    if not _has_assignment(line):
        while not 'Benchmark' in line:
            prev = open(path).readlines()[lineno - 1]
            line = prev + line
            lineno -= 1

        if not _has_assignment(line):
            prev = open(path).readlines()[lineno - 1]
            line = prev + line
    varname = line.split('=', 1)[0].strip()
    return varname


def parse_stmt(frame):
    import ast
    info = inspect.getframeinfo(frame)
    call = info[-2][0]
    mod = ast.parse(call)
    body = mod.body[0]
    if isinstance(body, (ast.Assign, ast.Expr)):
        call = body.value
    elif isinstance(body, ast.Call):
        call = body
    return _parse_call(call)


def _parse_call(call):
    import ast
    func = _maybe_format_attribute(call.func)

    str_args = []
    for arg in call.args:
        if isinstance(arg, ast.Name):
            str_args.append(arg.id)
        elif isinstance(arg, ast.Call):
            formatted = _format_call(arg)
            str_args.append(formatted)

    return func, str_args, {}


def _format_call(call):
    func, args, kwds = _parse_call(call)
    content = ''
    if args:
        content += ', '.join(args)
    if kwds:
        fmt_kwds = ['%s=%s' % item for item in kwds.iteritems()]
        joined_kwds = ', '.join(fmt_kwds)
        if args:
            content = content + ', ' + joined_kwds
        else:
            content += joined_kwds
    return '%s(%s)' % (func, content)


def _maybe_format_attribute(name):
    import ast
    if isinstance(name, ast.Attribute):
        return _format_attribute(name)
    return name.id


def _format_attribute(attr):
    import ast
    obj = attr.value
    if isinstance(attr.value, ast.Attribute):
        obj = _format_attribute(attr.value)
    else:
        obj = obj.id
    return '.'.join((obj, attr.attr))


def indent(string, spaces=4):
    dent = ' ' * spaces
    return '\n'.join([dent + x for x in string.split('\n')])


class BenchmarkSuite(list):
    """Basically a list, but the special type is needed for discovery"""
    @property
    def benchmarks(self):
        """Discard non-benchmark elements of the list"""
        return filter(lambda elem: isinstance(elem, Benchmark), self)

# Modified from IPython project, http://ipython.org


def magic_timeit(ns, stmt, ncalls=None, repeat=3, force_ms=False):
    """Time execution of a Python statement or expression

    Usage:\\
      %timeit [-n<N> -r<R> [-t|-c]] statement

    Time execution of a Python statement or expression using the timeit
    module.

    Options:
    -n<N>: execute the given statement <N> times in a loop. If this value
    is not given, a fitting value is chosen.

    -r<R>: repeat the loop iteration <R> times and take the best result.
    Default: 3

    -t: use time.time to measure the time, which is the default on Unix.
    This function measures wall time.

    -c: use time.clock to measure the time, which is the default on
    Windows and measures wall time. On Unix, resource.getrusage is used
    instead and returns the CPU user time.

    -p<P>: use a precision of <P> digits to display the timing result.
    Default: 3


    Examples:

      In [1]: %timeit pass
      10000000 loops, best of 3: 53.3 ns per loop

      In [2]: u = None

      In [3]: %timeit u is None
      10000000 loops, best of 3: 184 ns per loop

      In [4]: %timeit -r 4 u == None
      1000000 loops, best of 4: 242 ns per loop

      In [5]: import time

      In [6]: %timeit -n1 time.sleep(2)
      1 loops, best of 3: 2 s per loop


    The times reported by %timeit will be slightly higher than those
    reported by the timeit.py script when variables are accessed. This is
    due to the fact that %timeit executes the statement in the namespace
    of the shell, compared with timeit.py, which uses a single setup
    statement to import function or create variables. Generally, the bias
    does not matter as long as results from timeit.py are not mixed with
    those from %timeit."""

    import timeit
    import math

    units = ["s", "ms", 'us', "ns"]
    scaling = [1, 1e3, 1e6, 1e9]

    timefunc = timeit.default_timer

    timer = timeit.Timer(timer=timefunc)
    # this code has tight coupling to the inner workings of timeit.Timer,
    # but is there a better way to achieve that the code stmt has access
    # to the shell namespace?

    src = timeit.template % {'stmt': timeit.reindent(stmt, 8),
                             'setup': "pass"}
    # Track compilation time so it can be reported if too long
    # Minimum time above which compilation time will be reported
    code = compile(src, "<magic-timeit>", "exec")

    exec code in ns
    timer.inner = ns["inner"]

    if ncalls is None:
        # determine number so that 0.2 <= total time < 2.0
        number = 1
        for _ in range(1, 10):
            if timer.timeit(number) >= 0.1:
                break
            number *= 10
    else:
        number = ncalls

    best = min(timer.repeat(repeat, number)) / number

    if force_ms:
        order = 1
    else:
        if best > 0.0 and best < 1000.0:
            order = min(-int(math.floor(math.log10(best)) // 3), 3)
        elif best >= 1000.0:
            order = 0
        else:
            order = 3

    return {'loops': number,
            'repeat': repeat,
            'timing': best * scaling[order],
            'units': units[order]}


def gather_benchmarks(ns):
    benchmarks = []
    for v in ns.values():
        if isinstance(v, Benchmark):
            benchmarks.append(v)
        elif isinstance(v, BenchmarkSuite):
            benchmarks.extend(v.benchmarks)
    return benchmarks

########NEW FILE########
__FILENAME__ = config
import pytz, sys

TIME_ZONE = pytz.timezone('US/Eastern')


def set_timezone(tz):
    global TIME_ZONE
    TIME_ZONE = tz

def is_interactive():
    """Return True if all in/outs are tty"""
    return sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()


########NEW FILE########
__FILENAME__ = db
from pandas import DataFrame

from sqlalchemy import Table, Column, MetaData, create_engine, ForeignKey
from sqlalchemy import types as sqltypes
from sqlalchemy import sql

import logging
log = logging.getLogger('vb.db')

class BenchmarkDB(object):
    """
    Persist vbench results in a sqlite3 database
    """

    def __init__(self, dbpath):
        log.info("Initializing DB at %s" % dbpath)
        self.dbpath = dbpath

        self._engine = create_engine('sqlite:///%s' % dbpath)
        self._metadata = MetaData()
        self._metadata.bind = self._engine

        self._benchmarks = Table('benchmarks', self._metadata,
            Column('checksum', sqltypes.String(32), primary_key=True),
            Column('name', sqltypes.String(200), nullable=False),
            Column('description', sqltypes.Text)
        )
        self._results = Table('results', self._metadata,
            Column('checksum', sqltypes.String(32),
                   ForeignKey('benchmarks.checksum'), primary_key=True),
            Column('revision', sqltypes.String(50), primary_key=True),
            Column('timestamp', sqltypes.DateTime, nullable=False),
            Column('ncalls', sqltypes.String(50)),
            Column('timing', sqltypes.Float),
            Column('traceback', sqltypes.Text),
        )

        self._blacklist = Table('blacklist', self._metadata,
            Column('revision', sqltypes.String(50), primary_key=True)
        )

        self._ensure_tables_created()

    _instances = {}

    @classmethod
    def get_instance(cls, dbpath):
        if dbpath not in cls._instances:
            cls._instances[dbpath] = BenchmarkDB(dbpath)
        return cls._instances[dbpath]

    def _ensure_tables_created(self):
        log.debug("Ensuring DB tables are created")
        self._benchmarks.create(self._engine, checkfirst=True)
        self._results.create(self._engine, checkfirst=True)
        self._blacklist.create(self._engine, checkfirst=True)

    def update_name(self, benchmark):
        """
        benchmarks : list
        """
        table = self._benchmarks
        stmt = (table.update().
                where(table.c.checksum == benchmark.checksum).
                values(checksum=benchmark.checksum))
        self.conn.execute(stmt)

    def restrict_to_benchmarks(self, benchmarks):
        """
        benchmarks : list
        """
        checksums = set([b.checksum for b in benchmarks])

        ex_benchmarks = self.get_benchmarks()

        to_delete = set(ex_benchmarks.index) - checksums

        t = self._benchmarks
        for chksum in to_delete:
            log.info('Deleting %s\n%s' % (chksum, ex_benchmarks.xs(chksum)))
            stmt = t.delete().where(t.c.checksum == chksum)
            self.conn.execute(stmt)

    @property
    def conn(self):
        return self._engine.connect()

    def write_benchmark(self, bm, overwrite=False):
        """

        """
        ins = self._benchmarks.insert()
        ins = ins.values(name=bm.name, checksum=bm.checksum,
                         description=bm.description)
        self.conn.execute(ins)  # XXX: return the result?

    def delete_benchmark(self, checksum):
        """

        """
        pass

    def write_result(self, checksum, revision, timestamp, ncalls,
                     timing, traceback=None, overwrite=False):
        """

        """
        ins = self._results.insert()
        ins = ins.values(checksum=checksum, revision=revision,
                         timestamp=timestamp,
                         ncalls=ncalls, timing=timing, traceback=traceback)
        self.conn.execute(ins)  # XXX: return the result?

    def delete_result(self, checksum, revision):
        """

        """
        pass

    def delete_error_results(self):
        tab = self._results
        ins = tab.delete()
        ins = ins.where(tab.c.timing == None)
        self.conn.execute(ins)

    def get_benchmarks(self):
        stmt = sql.select([self._benchmarks])
        result = self.conn.execute(stmt)
        return _sqa_to_frame(result).set_index('checksum')

    def get_rev_results(self, rev):
        tab = self._results
        stmt = sql.select([tab],
                          sql.and_(tab.c.revision == rev))
        results = list(self.conn.execute(stmt))
        return dict((v.checksum, v) for v in results)

    def delete_rev_results(self, rev):
        tab = self._results
        stmt = tab.delete().where(tab.c.revision == rev)
        self.conn.execute(stmt)

    def add_rev_blacklist(self, rev):
        """
        Don't try running this revision again
        """
        stmt = self._blacklist.insert().values(revision=rev)
        self.conn.execute(stmt)

    def get_rev_blacklist(self):
        stmt = self._blacklist.select()
        return [x['revision'] for x in self.conn.execute(stmt)]

    def clear_blacklist(self):
        stmt = self._blacklist.delete()
        self.conn.execute(stmt)

    def get_benchmark_results(self, checksum):
        """

        """
        tab = self._results
        stmt = sql.select([tab.c.timestamp, tab.c.revision, tab.c.ncalls,
                           tab.c.timing, tab.c.traceback],
                          sql.and_(tab.c.checksum == checksum))
        results = self.conn.execute(stmt)

        df = _sqa_to_frame(results).set_index('timestamp')
        return df.sort_index()


def _sqa_to_frame(result):
    rows = [tuple(x) for x in result]
    if not rows:
        return DataFrame(columns=result.keys())
    return DataFrame.from_records(rows, columns=result.keys())

########NEW FILE########
__FILENAME__ = git
from dateutil import parser
import subprocess
import os
import shutil

import numpy as np

from pandas import Series, DataFrame, Panel
from vbench.utils import run_cmd

import logging
log = logging.getLogger('vb.git')


class Repo(object):

    def __init__(self):
        raise NotImplementedError


class GitRepo(Repo):
    """
    Read some basic statistics about a git repository
    """

    def __init__(self, repo_path):
        log.info("Initializing GitRepo to look at %s" % repo_path)
        self.repo_path = repo_path
        self.git = _git_command(self.repo_path)
        (self.shas, self.messages,
         self.timestamps, self.authors) = self._parse_commit_log()

    @property
    def commit_date(self):
        from pandas.core.datetools import normalize_date
        return self.timestamps.map(normalize_date)

    def _parse_commit_log(self):
        log.debug("Parsing the commit log of %s" % self.repo_path)
        githist = self.git + ('log --graph --pretty=format:'
                              '\"::%h::%cd::%s::%an\" > githist.txt')
        os.system(githist)
        githist = open('githist.txt').read()
        os.remove('githist.txt')

        shas = []
        timestamps = []
        messages = []
        authors = []
        for line in githist.split('\n'):
            # skip commits not in mainline
            if not line[0] == '*':
                continue
            # split line into three real parts, ignoring git-graph in front
            _, sha, stamp, message, author = line.split('::', 4)

            # parse timestamp into datetime object
            stamp = parser.parse(stamp)
            # avoid duplicate timestamps by ignoring them
            # presumably there is a better way to deal with this
            if stamp in timestamps:
                continue

            shas.append(sha)
            timestamps.append(stamp)
            messages.append(message)
            authors.append(author)

        # to UTC for now
        timestamps = _convert_timezones(timestamps)

        shas = Series(shas, timestamps)
        messages = Series(messages, shas)
        timestamps = Series(timestamps, shas)
        authors = Series(authors, shas)
        return shas[::-1], messages[::-1], timestamps[::-1], authors[::-1]

    def get_churn(self, omit_shas=None, omit_paths=None):
        churn = self.get_churn_by_file()

        if omit_paths is not None:
            churn = churn.drop(omit_paths, axis='major')

        if omit_shas is not None:
            churn = churn.drop(omit_shas, axis='minor')

        # sum files and add insertions + deletions
        by_commit = churn.sum('major').sum(1)
        by_date = by_commit.groupby(self.commit_date).sum()
        return by_date

    def get_churn_by_file(self):
        hashes = self.shas.values
        prev = hashes[0]

        insertions = {}
        deletions = {}

        for cur in hashes[1:]:
            i, d = self.diff(cur, prev)
            insertions[cur] = i
            deletions[cur] = d
            prev = cur
        return Panel({'insertions': DataFrame(insertions),
                      'deletions': DataFrame(deletions)},
                     minor_axis=hashes)

    def diff(self, sha, prev_sha):
        cmdline = self.git.split() + ['diff', sha, prev_sha, '--numstat']
        stdout = subprocess.Popen(cmdline, stdout=subprocess.PIPE).stdout

        stdout = stdout.read()

        insertions = {}
        deletions = {}

        for line in stdout.split('\n'):
            try:
                i, d, path = line.split('\t')
                insertions[path] = int(i)
                deletions[path] = int(d)
            except Exception:  # EAFP
                pass

        # statline = stdout.split('\n')[-2]

        # match = re.match('.*\s(.*)\sinsertions.*\s(.*)\sdeletions', statline)

        # insertions = int(match.group(1))
        # deletions = int(match.group(2))
        return insertions, deletions

    def checkout(self, sha):
        pass

class BenchRepo(object):
    """
    Manage an isolated copy of a repository for benchmarking
    """
    def __init__(self, source_url, target_dir, build_cmds, prep_cmd,
                 clean_cmd=None, dependencies=None, always_clean=False):
        self.source_url = source_url
        self.target_dir = target_dir
        self.target_dir_tmp = target_dir + '_tmp'
        self.build_cmds = build_cmds
        self.prep_cmd = prep_cmd
        self.clean_cmd = clean_cmd
        self.dependencies = dependencies
        self.always_clean = always_clean
        self._clean_checkout()
        self._copy_repo()

    def _clean_checkout(self):
        log.debug("Clean checkout of %s from %s"
                  % (self.source_url, self.target_dir_tmp))
        self._clone(self.source_url, self.target_dir_tmp, rm=True)

    def _copy_repo(self):
        log.debug("Repopulating %s" % self.target_dir)
        self._clone(self.target_dir_tmp, self.target_dir, rm=True)
        self._prep()

    def _clone(self, source, target, rm=False):
        log.info("Cloning %s over to %s" % (source, target))
        if os.path.exists(target):
            if rm:
                log.info('Deleting %s first' % target)
                # response = raw_input('%s exists, delete? y/n' % self.target_dir)
                # if response == 'n':
                #     raise Exception('foo')
                # yoh: no need to divert from Python
                #run_cmd('rm -rf %s' % self.target_dir)
                shutil.rmtree(target)
            else:
                raise RuntimeError("Target directory %s already exists. "
                                   "Can't clone into it" % target)
        run_cmd(['git', 'clone', source, target])

    def _copy_benchmark_scripts_and_deps(self):
        pth, _ = os.path.split(os.path.abspath(__file__))
        deps = [os.path.join(pth, 'scripts/vb_run_benchmarks.py')]
        if self.dependencies is not None:
            deps.extend(self.dependencies)

        for dep in deps:
            proc = run_cmd('cp %s %s' % (dep, self.target_dir), shell=True)

    def switch_to_revision(self, rev):
        """
        rev: git SHA
        """
        log.info("Switching to revision %s", rev)
        if self.always_clean:
            self.hard_clean()
        else:
            self._clean()

        self._checkout(rev)
        self._copy_benchmark_scripts_and_deps()
        self._clean_pyc_files()
        self._build()

    def _checkout(self, rev):
        git = _git_command(self.target_dir)
        rest = 'checkout -f %s' % rev
        args = git.split() + rest.split()
        # checkout of a detached commit would always produce stderr
        proc = run_cmd(args, stderr_levels=('debug', 'error'))

    def _build(self):
        cmd = ';'.join([x for x in self.build_cmds.split('\n')
                        if len(x.strip()) > 0])
        proc = run_cmd(cmd, shell=True, cwd=self.target_dir)

    def _prep(self):
        cmd = ';'.join([x for x in self.prep_cmd.split('\n')
                        if len(x.strip()) > 0])
        proc = run_cmd(cmd, shell=True, cwd=self.target_dir)

    def _clean(self):
        if not self.clean_cmd:
            return
        cmd = ';'.join([x for x in self.clean_cmd.split('\n')
                        if len(x.strip()) > 0])
        proc = run_cmd(cmd, shell=True, cwd=self.target_dir)

    def hard_clean(self):
        self._copy_repo()

    def _clean_pyc_files(self, extensions=('.pyc', '.pyo')):
        clean_me = []
        for root, dirs, files in list(os.walk(self.target_dir)):
            for f in files:
                if os.path.splitext(f)[-1] in extensions:
                    clean_me.append(os.path.join(root, f))

        for path in clean_me:
            try:
                os.unlink(path)
            except Exception:
                pass


def _convert_timezones(stamps):
    # tz = config.TIME_ZONE
    def _convert(dt):
        offset = dt.tzinfo.utcoffset(dt)
        dt = dt.replace(tzinfo=None)
        dt = dt - offset
        return dt

    return [_convert(x) for x in stamps]


def _git_command(repo_path):
    return ('git --git-dir=%s/.git --work-tree=%s ' % (repo_path, repo_path))


def get_commit_history():
    # return TimeSeries

    rungithist()

    githist = open('githist.txt').read()
    os.remove('githist.txt')

    sha_date = []
    for line in githist.split('\n'):
        sha_date.append(line.split()[:2])

    return Series(dates, shas), hists


def get_commit_churn(sha, prev_sha):
    # TODO: handle stderr
    stdout = subprocess.Popen(['git', 'diff', sha, prev_sha, '--numstat'],
                              stdout=subprocess.PIPE).stdout
    stdout = stdout.read()

    insertions = {}
    deletions = {}

    for line in stdout.split('\n'):
        try:
            i, d, path = line.split('\t')
            insertions[path] = int(i)
            deletions[path] = int(d)
        except:  # EAFP
            pass

    # statline = stdout.split('\n')[-2]
    # match = re.match('.*\s(.*)\sinsertions.*\s(.*)\sdeletions', statline)
    # insertions = int(match.group(1))
    # deletions = int(match.group(2))
    return insertions, deletions


def get_code_churn(commits):
    shas = commits.index[::-1]

    prev = shas[0]

    insertions = [np.nan]
    deletions = [np.nan]

    insertions = {}
    deletions = {}

    for cur in shas[1:]:
        i, d = get_commit_churn(cur, prev)

        insertions[cur] = i
        deletions[cur] = d

        # insertions.append(i)
        # deletions.append(d)

        prev = cur

    return Panel({'insertions': DataFrame(insertions),
                  'deletions': DataFrame(deletions)}, minor_axis=shas)


    # return DataFrame({'insertions' : insertions,
    #                   'deletions' : deletions}, index=shas)

if __name__ == '__main__':
    repo_path = '/home/wesm/code/pandas'  # XXX:  specific?
    repo = GitRepo(repo_path)
    by_commit = 5

########NEW FILE########
__FILENAME__ = graphs
import matplotlib.pyplot as plt

########NEW FILE########
__FILENAME__ = log
#!/usr/bin/python
#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:
"""
 COPYRIGHT: Yaroslav Halchenko 2013

 LICENSE: MIT

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
  THE SOFTWARE.
"""

__author__ = 'Yaroslav Halchenko'
__copyright__ = 'Copyright (c) 2013 Yaroslav Halchenko'
__license__ = 'MIT'

import logging, sys

from vbench.config import is_interactive

# Recipe from http://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
# by Brandon Thomson
# Adjusted for automagic determination either coloring is needed and
# prefixing of multiline log lines
class ColorFormatter(logging.Formatter):

  FORMAT = ("$BOLD%(asctime)-15s$RESET [%(levelname)s] "
            "%(message)s "
            "($BOLD%(filename)s$RESET:%(lineno)d)")

  BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

  RESET_SEQ = "\033[0m"
  COLOR_SEQ = "\033[1;%dm"
  BOLD_SEQ = "\033[1m"

  COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
  }

  def __init__(self, use_color=None):
    if use_color is None:
      # if 'auto' - use color only if all streams are tty
      use_color = is_interactive()
    msg = self.formatter_msg(self.FORMAT, use_color)
    logging.Formatter.__init__(self, msg)
    self.use_color = use_color

  def formatter_msg(self, fmt, use_color=False):
    if use_color:
      fmt = fmt.replace("$RESET", self.RESET_SEQ).replace("$BOLD", self.BOLD_SEQ)
    else:
      fmt = fmt.replace("$RESET", "").replace("$BOLD", "")
    return fmt

  def format(self, record):
    levelname = record.levelname
    if self.use_color and levelname in self.COLORS:
      fore_color = 30 + self.COLORS[levelname]
      levelname_color = self.COLOR_SEQ % fore_color + "%-6s" % levelname + self.RESET_SEQ
      record.levelname = levelname_color
    record.msg = record.msg.replace("\n", "\n| ")
    return logging.Formatter.format(self, record)

# Setup default vbench logging

# By default mimic previously talkative behavior
log = logging.getLogger('vb')
log.setLevel(logging.INFO)
_log_handler = logging.StreamHandler(sys.stdout)

# But now improve with colors and useful information such as time
_log_handler.setFormatter(ColorFormatter())
#logging.Formatter('%(asctime)-15s %(levelname)-6s %(message)s'))
log.addHandler(_log_handler)


########NEW FILE########
__FILENAME__ = report
class RSTReport(object):
    pass

########NEW FILE########
__FILENAME__ = reports
#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:
"""Functionality to ease generation of vbench reports
"""
__copyright__ = '2012-2013 Wes McKinney, Yaroslav Halchenko'
__license__ = 'MIT'

import os

import logging
log = logging.getLogger('vb.reports')

def generate_rst_files(benchmarks, dbpath, outpath, description=""):
    import matplotlib as mpl
    mpl.use('Agg')
    import matplotlib.pyplot as plt

    vb_path = os.path.join(outpath, 'vbench')
    fig_base_path = os.path.join(vb_path, 'figures')

    if not os.path.exists(vb_path):
        log.info('Creating %s' % vb_path)
        os.makedirs(vb_path)

    if not os.path.exists(fig_base_path):
        log.info('Creating %s' % fig_base_path)
        os.makedirs(fig_base_path)

    log.info("Generating rst files for %d benchmarks" % (len(benchmarks)))
    for bmk in benchmarks:
        log.debug('Generating rst file for %s' % bmk.name)
        rst_path = os.path.join(outpath, 'vbench/%s.rst' % bmk.name)

        fig_full_path = os.path.join(fig_base_path, '%s.png' % bmk.name)

        # make the figure
        plt.figure(figsize=(10, 6))
        ax = plt.gca()
        bmk.plot(dbpath, ax=ax)

        start, end = ax.get_xlim()

        plt.xlim([start - 30, end + 30])
        plt.savefig(fig_full_path, bbox_inches='tight')
        plt.close('all')

        fig_rel_path = 'vbench/figures/%s.png' % bmk.name
        rst_text = bmk.to_rst(image_path=fig_rel_path)
        with open(rst_path, 'w') as f:
            f.write(rst_text)

    with open(os.path.join(outpath, 'index.rst'), 'w') as f:
        print >> f, """
Performance Benchmarks
======================

These historical benchmark graphs were produced with `vbench
<http://github.com/pydata/vbench>`__.

%(description)s

.. toctree::
    :hidden:
    :maxdepth: 3
""" % locals()
        # group benchmarks by module there belonged to
        benchmarks_by_module = {}
        for b in benchmarks:
            module_name = b.module_name or "orphan"
            if not module_name in benchmarks_by_module:
                benchmarks_by_module[module_name] = []
            benchmarks_by_module[module_name].append(b)

        for modname, mod_bmks in sorted(benchmarks_by_module.items()):
            print >> f, '    vb_%s' % modname
            modpath = os.path.join(outpath, 'vb_%s.rst' % modname)
            with open(modpath, 'w') as mh:
                header = '%s\n%s\n\n' % (modname, '=' * len(modname))
                print >> mh, header

                for bmk in mod_bmks:
                    print >> mh, bmk.name
                    print >> mh, '-' * len(bmk.name)
                    print >> mh, '.. include:: vbench/%s.rst\n' % bmk.name


########NEW FILE########
__FILENAME__ = runner
import cPickle as pickle
import os
import subprocess

from vbench.git import GitRepo, BenchRepo
from vbench.db import BenchmarkDB
from vbench.utils import multires_order

from datetime import datetime

import logging
log = logging.getLogger('vb.runner')

_RUN_ORDERS = dict(
    normal=lambda x:x,
    reverse=lambda x:x[::-1],
    multires=multires_order,
    )

class BenchmarkRunner(object):
    """

    Parameters
    ----------
    benchmarks : list of Benchmark objects
    repo_path
    build_cmd
    db_path
    run_option : {'eod', 'all', 'last', integer}, default: 'eod'
        eod: use the last revision for each calendar day
        all: benchmark every revision
        last: only try to run the last revision
        some integer N: run each N revisions
    run_order :
        normal : original order (default)
        reverse: in reverse order (latest first)
        multires: cover all revisions but in the order increasing
                  temporal detail
    overwrite : boolean
    dependencies : list or None
        should be list of modules visible in cwd
    """

    def __init__(self, benchmarks, repo_path, repo_url,
                 build_cmd, db_path, tmp_dir,
                 prep_cmd,
                 clean_cmd=None,
                 run_option='eod', run_order='normal',
                 start_date=None, overwrite=False,
                 module_dependencies=None,
                 always_clean=False,
                 use_blacklist=True):
        log.info("Initializing benchmark runner for %d benchmarks" % (len(benchmarks)))
        self._benchmarks = None
        self._checksums = None

        self.start_date = start_date
        self.run_option = run_option
        self.run_order = run_order

        self.repo_path = repo_path
        self.db_path = db_path

        self.repo = GitRepo(self.repo_path)
        self.db = BenchmarkDB(db_path)

        self.use_blacklist = use_blacklist

        self.blacklist = set(self.db.get_rev_blacklist())

        # where to copy the repo
        self.tmp_dir = tmp_dir
        self.bench_repo = BenchRepo(repo_url, self.tmp_dir, build_cmd,
                                    prep_cmd,
                                    clean_cmd,
                                    always_clean=always_clean,
                                    dependencies=module_dependencies)

        self.benchmarks = benchmarks

    def _get_benchmarks(self):
        return self._benchmarks

    def _set_benchmarks(self, benchmarks):
        self._benchmarks = benchmarks
        self._checksums = [b.checksum for b in benchmarks]
        self._register_benchmarks()

    benchmarks = property(fget=_get_benchmarks, fset=_set_benchmarks)
    checksums = property(fget=lambda self:self._checksums)

    def run(self):
        log.info("Collecting revisions to run")
        revisions = self._get_revisions_to_run()
        ran_revisions = []
        log.info("Running benchmarks for %d revisions" % (len(revisions),))
        for rev in revisions:
            if self.use_blacklist and rev in self.blacklist:
                log.warn('Skipping blacklisted %s' % rev)
                continue

            any_succeeded, n_active = self._run_and_write_results(rev)
            ran_revisions.append((rev, (any_succeeded, n_active)))
            log.debug("%s succeeded among %d active benchmarks",
                      {True: "Some", False: "None"}[any_succeeded],
                      n_active)
            if not any_succeeded and n_active > 0:
                self.bench_repo.hard_clean()

                any_succeeded2, n_active = self._run_and_write_results(rev)

                # just guessing that this revision is broken, should stop
                # wasting our time
                if (not any_succeeded2 and n_active > 5
                    and self.use_blacklist):
                    log.warn('Blacklisting %s' % rev)
                    self.db.add_rev_blacklist(rev)
        return ran_revisions

    def _run_and_write_results(self, rev):
        """
        Returns True if any runs succeeded
        """
        n_active_benchmarks, results = self._run_revision(rev)
        tracebacks = []

        any_succeeded = False

        for checksum, timing in results.iteritems():
            if 'traceback' in timing:
                tracebacks.append(timing['traceback'])

            timestamp = self.repo.timestamps[rev]

            any_succeeded = any_succeeded or 'timing' in timing

            self.db.write_result(checksum, rev, timestamp,
                                 timing.get('loops'),
                                 timing.get('timing'),
                                 timing.get('traceback'))

        return any_succeeded, n_active_benchmarks

    def _register_benchmarks(self):
        log.info('Getting benchmarks')
        ex_benchmarks = self.db.get_benchmarks()
        db_checksums = set(ex_benchmarks.index)
        log.info("Registering %d benchmarks" % len(ex_benchmarks))
        for bm in self.benchmarks:
            if bm.checksum in db_checksums:
                self.db.update_name(bm)
            else:
                log.info('Writing new benchmark %s, %s' % (bm.name, bm.checksum))
                self.db.write_benchmark(bm)

    def _run_revision(self, rev):
        need_to_run = self._get_benchmarks_for_rev(rev)

        if not need_to_run:
            log.info('No benchmarks need running at %s' % rev)
            return 0, {}

        log.info('Running %d benchmarks for revision %s' % (len(need_to_run), rev))
        for bm in need_to_run:
            log.debug(bm.name)

        self.bench_repo.switch_to_revision(rev)

        pickle_path = os.path.join(self.tmp_dir, 'benchmarks.pickle')
        results_path = os.path.join(self.tmp_dir, 'results.pickle')
        if os.path.exists(results_path):
            os.remove(results_path)
        pickle.dump(need_to_run, open(pickle_path, 'w'))

        # run the process
        cmd = 'python vb_run_benchmarks.py %s %s' % (pickle_path, results_path)
        log.debug("CMD: %s" % cmd)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True,
                                cwd=self.tmp_dir)
        stdout, stderr = proc.communicate()

        if stdout:
            log.debug('stdout: %s' % stdout)

        if proc.returncode:
            log.warn("Returned with non-0 code: %d" % proc.returncode)

        if stderr:
            log.warn("stderr: %s" % stderr)
            if ("object has no attribute" in stderr or
                'ImportError' in stderr):
                log.warn('HARD CLEANING!')
                self.bench_repo.hard_clean()

        if not os.path.exists(results_path):
            log.warn('Failed for revision %s' % rev)
            return len(need_to_run), {}

        results = pickle.load(open(results_path, 'r'))

        try:
            os.remove(pickle_path)
        except OSError:
            pass

        return len(need_to_run), results

    def _get_benchmarks_for_rev(self, rev):
        existing_results = self.db.get_rev_results(rev)
        need_to_run = []

        timestamp = self.repo.timestamps[rev]

        for b in self.benchmarks:
            if b.start_date is not None and b.start_date > timestamp:
                continue

            if b.checksum not in existing_results:
                need_to_run.append(b)

        return need_to_run

    def _get_revisions_to_run(self):

        # TODO generalize someday to other vcs...git only for now

        rev_by_timestamp = self.repo.shas.sort_index()

        # # assume they're in order, but check for now
        # assert(rev_by_timestamp.index.is_monotonic)

        if self.start_date is not None:
            rev_by_timestamp = rev_by_timestamp.ix[self.start_date:]

        if self.run_option == 'eod':
            grouped = rev_by_timestamp.groupby(datetime.date)
            revs_to_run = grouped.apply(lambda x: x[-1]).values
        elif self.run_option == 'all':
            revs_to_run = rev_by_timestamp.values
        elif self.run_option == 'last':
            revs_to_run = rev_by_timestamp.values[-1:]
            # TODO: if the very last revision fails, there should be a way
            # to look for the second last, etc, until the last one that was run
        elif isinstance(self.run_option, int):
            revs_to_run = rev_by_timestamp.values[::self.run_option]
        else:
            raise ValueError('unrecognized run_option=%r' % self.run_option)

        if not self.run_order in _RUN_ORDERS:
            raise ValueError('unrecognized run_order=%r. Must be among %s'
                             % (self.run_order, _RUN_ORDERS.keys()))
        revs_to_run = _RUN_ORDERS[self.run_order](revs_to_run)

        return revs_to_run

########NEW FILE########
__FILENAME__ = vb_run_benchmarks
import sys
import cPickle as pickle

if len(sys.argv) != 3:
    print('Usage: script.py input output')
    sys.exit()

in_path, out_path = sys.argv[1:]
benchmarks = pickle.load(open(in_path))

results = {}
errors = 0
for bmk in benchmarks:
    try:
        res = bmk.run()
    except Exception, e:
        errors += 1
        print("E: Got an exception while running %s\n%s" % (bmk, e))
        continue

    results[bmk.checksum] = res

    if not res['succeeded']:
        errors += 1
        print("I: Failed to succeed with %s in stage %s."
               % (bmk, res.get('stage', 'UNKNOWN')))
        print(res.get('traceback', 'Traceback: UNKNOWN'))

benchmarks = pickle.dump(results, open(out_path, 'w'))
sys.exit(errors)

########NEW FILE########
__FILENAME__ = test_db
import unittest

# from gitbench.db import BenchmarkDB  # FIXME: test is actually empty


class TestBenchmarkDB(unittest.TestCase):

    test_path = '__test__.db'

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vvs', '-x', '--pdb', '--pdb-failure'],
                   exit=False)

########NEW FILE########
__FILENAME__ = test_utils
#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 noet:
#------------------------- =+- Python script -+= -------------------------
"""
 COPYRIGHT: Yaroslav Halchenko 2013

 LICENSE: MIT

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
  THE SOFTWARE.
"""

__author__ = 'Yaroslav Halchenko'
__copyright__ = 'Copyright (c) 2013 Yaroslav Halchenko'
__license__ = 'MIT'

from nose.tools import eq_, ok_

from vbench.utils import multires_order

def test_multires_order():
    r = [str(x) for x in range(5)]
    eq_(multires_order(tuple(r)), ('0', '2', '4', '1', '3'))
    eq_(multires_order(r), ['0', '2', '4', '1', '3'])
    import numpy as np
    oa = multires_order(np.array(r))
    ok_(isinstance(oa, np.ndarray))
    ok_(np.all(oa == np.array(['0', '2', '4', '1', '3'])))

    for n in range(123):
        o = multires_order(n)
        # print n, o[-10:]
        eq_(len(o), n)
        eq_(len(set(o)), n) #  all are unique
        if n > 0: eq_(o[0], 0)
        if n > 1: ok_(o[1] in [n//2,n//2-1])
        if n > 2: eq_(o[2], n-1)
        if n > 8: ok_(o[3] != 1)          # we must not get to the 1st yet
        if n > 3: ok_(o[-1] in [n-2, n-3])   # end should be very close to last ones

########NEW FILE########
__FILENAME__ = suite
import os
from datetime import datetime

from vbench.api import collect_benchmarks

benchmarks = collect_benchmarks(
    ['vb_sins'])

cur_dir = os.path.dirname(__file__)
REPO_PATH = os.path.join(cur_dir, 'vbenchtest')
REPO_URL = 'git://github.com/yarikoptic/vbenchtest.git'
DB_PATH = os.path.join(cur_dir, 'db/benchmarks.db')
TMP_DIR = os.path.join(cur_dir, 'tmp')
# Assure corresponding directories existence
for s in (REPO_PATH, os.path.dirname(DB_PATH), TMP_DIR):
    if not os.path.exists(s):
        os.makedirs(s)

PREPARE = """
python setup.py clean
"""

CLEAN=PREPARE

BUILD = """
python setup.py build_ext --inplace
"""

DEPENDENCIES = [os.path.join(cur_dir, 'vb_common.py')]

START_DATE = datetime(2011, 01, 01)

########NEW FILE########
__FILENAME__ = test_bench
#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:

__author__ = 'Yaroslav Halchenko'
__copyright__ = 'Copyright (c) 2013 Yaroslav Halchenko'
__license__ = 'MIT'

import os
import shutil

from glob import glob
from os.path import exists, join as pjoin, dirname, basename

from nose.tools import ok_, eq_
from numpy.testing import assert_array_equal

#import logging
#log = logging.getLogger('vb')
#log.setLevel('DEBUG')


def test_benchmarkrunner():
    from vbench.api import BenchmarkRunner
    from suite import *

    # Just to make sure there are no left-overs
    shutil.rmtree(TMP_DIR)
    if exists(DB_PATH):
        os.unlink(DB_PATH)
    ok_(not exists(DB_PATH))

    runner = BenchmarkRunner(benchmarks, REPO_PATH, REPO_URL,
                             BUILD, DB_PATH, TMP_DIR, PREPARE,
                             clean_cmd=CLEAN,
                             run_option='all', run_order='normal',
                             start_date=START_DATE,
                             module_dependencies=DEPENDENCIES)
    revisions_to_run = runner._get_revisions_to_run()
    eq_(len(revisions_to_run), 4)                # we had 4 so far

    revisions_ran = runner.run()
    # print "D1: ", revisions_ran
    assert_array_equal([x[0] for x in revisions_ran],
                       revisions_to_run)
    # First revision
    eq_(revisions_ran[0][1], (False, 3))    # no functions were available at that point
    eq_(revisions_ran[1][1], (True, 3))     # all 3 tests were available in the first rev

    ok_(exists(TMP_DIR))
    ok_(exists(DB_PATH))

    eq_(len(runner.blacklist), 0)

    # Run 2nd time and verify that all are still listed BUT none new succeeds
    revisions_ran = runner.run()
    #print "D2: ", revisions_ran
    for rev, v in revisions_ran:
        eq_(v, (False, 0))

    # What if we expand list of benchmarks and run 3rd time
    runner.benchmarks = collect_benchmarks(['vb_sins', 'vb_sins2'])
    revisions_ran = runner.run()
    # for that single added benchmark there still were no function
    eq_(revisions_ran[0][1], (False, 1))
    # all others should have "succeeded" on that single one
    for rev, v in revisions_ran[1:]:
        eq_(v, (True, 1))

    # and on 4th run -- nothing new
    revisions_ran = runner.run()
    for rev, v in revisions_ran:
        eq_(v, (False, 0))

    # Now let's smoke test generation of the .rst files
    from vbench.reports import generate_rst_files
    rstdir = pjoin(TMP_DIR, 'sources')
    generate_rst_files(runner.benchmarks, DB_PATH, rstdir, """VERY LONG DESCRIPTION""")

    # Verify that it all looks close to the desired
    image_files = [basename(x) for x in glob(pjoin(rstdir, 'vbench/figures/*.png'))]
    target_image_files = [b.name + '.png' for b in runner.benchmarks]
    eq_(set(image_files), set(target_image_files))

    rst_files = [basename(x) for x in glob(pjoin(rstdir, 'vbench/*.rst'))]
    target_rst_files = [b.name + '.rst' for b in runner.benchmarks]
    eq_(set(rst_files), set(target_rst_files))

    module_files = [basename(x) for x in glob(pjoin(rstdir, '*.rst'))]
    target_module_files = list(set(['vb_' + b.module_name + '.rst' for b in runner.benchmarks]))
    eq_(set(module_files), set(target_module_files + ['index.rst']))

    #print TMP_DIR
    shutil.rmtree(TMP_DIR)
    shutil.rmtree(dirname(DB_PATH))

########NEW FILE########
__FILENAME__ = vb_common
#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:

__author__ = 'Yaroslav Halchenko'
__copyright__ = 'Copyright (c) 2013 Yaroslav Halchenko'
__license__ = 'MIT'

import numpy as np

test_variable = "just so we could check if things are loaded/available correctly"

########NEW FILE########
__FILENAME__ = vb_sins
#emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:
from vbench.benchmark import Benchmark

setup = """\
from vb_common import *
"""

# We do not care about precision, so ncalls is set low

# Separate benchmark
vb1000 = Benchmark("manysins(1000)", setup=setup+"from vbenchtest.m1 import manysins",
                   ncalls=2)

# List of the benchmarks
vb_collection = [Benchmark("manysins(%d)" % n ,
                           setup=setup+"from vbenchtest.m1 import manysins",
                           name="manysins(%d)_from_collection" % (n,),
                           ncalls=2)
                 for n in [100, 2000]]

########NEW FILE########
__FILENAME__ = vb_sins2
#emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:
from vbench.benchmark import Benchmark

# We do not care about precision, so ncalls is set low
# Separate benchmark
a_single_sin = Benchmark("manysins(1)", setup="from vbenchtest.m1 import manysins", ncalls=2)

########NEW FILE########
__FILENAME__ = utils
#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 noet:
#------------------------- =+- Python script -+= -------------------------
"""
 COPYRIGHT: Yaroslav Halchenko 2013

 LICENSE: MIT

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
  THE SOFTWARE.
"""

__author__ = 'Yaroslav Halchenko'
__copyright__ = 'Copyright (c) 2013 Yaroslav Halchenko'
__license__ = 'MIT'

from itertools import chain
from math import ceil

import importlib, sys, subprocess

from vbench.benchmark import Benchmark

import logging
log = logging.getLogger('vb')

def multires_order(n):
    """Provide order of indexes slowly detailing into the history

    Often it is desirable to order investigation of events in history
    at "multiple resolutions".  So at first we get a glimpse of the
    history at 3 points (first, middle, last) and then get deeper by
    making our step twice smaller at each "resolution".  So for
    e.g. n=9 order of indexes for such inspection would be [0, 4, 8,
    2, 6, 1, 5, 3, 7] .

    It should remind (if not being identical) to traversing the binary
    heap associated with a list of indexes: as if we first took at
    corners and then go layer by layer including the depth.

    Current procedure is a very sloppy implementation, so inefficient
    in general but good enough for real use (e.g. 26.6ms for n=10000)
    """

    if isinstance(n, list) or isinstance(n, tuple):
       return n.__class__(n[i] for i in multires_order(len(n)))
    elif 'ndarray' in str(type(n)):
       return n[multires_order(len(n))]
    assert(isinstance(n, int))

    out = []
    # to speed up checks, we will consume some memory but mark
    # each index whenever we add it to out
    seen = [False] * n
    for i in xrange(1, n):
        # fp step so we could point to the 0th, middle, last
        # on the first run
        step = float(n-1)/(2*i)
        gotnew = False
        for k in xrange(int(ceil(float(n)/step))):
            idx = int(k*step)
            if not seen[idx]: # in seen:
               out.append(idx)
               seen[idx] = True
               gotnew = True
        if not gotnew:
            #print "D: exiting from loop with i=%d n=%d" % (i, n)
            break
    if len(out) != n:
        # Fill in the holes -- some might still be missing, so
        # add them at the end
        # print "D: %d are still missing" % (n-len(out))
        out.extend([i for i in range(n) if not seen[i]])
    assert(set(out) == set(range(n)))
    return out

def run_cmd(cmd, stderr_levels=('warn', 'error'), **kwargs):
    """Helper function to unify invocation and logging of external commands

    stderr_levels : (success, failure)
      Levels of output dependent on success or failure of the command
    """

    log.debug(cmd if isinstance(cmd, basestring) else ' '.join(cmd))
    proc = subprocess.Popen(cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs)
    stdout, stderr = proc.communicate()
    if stdout: log.debug("stdout: " + stdout)
    if stderr:
        stderr_level = stderr_levels[int(proc.returncode>0)]
        if stderr_level:
            getattr(log, stderr_level)("stderr: " + stderr)
    return proc

# TODO: join two together
def collect_benchmarks_from_object(obj):
    if isinstance(obj, Benchmark):
        return [obj]
    elif isinstance(obj, list) or isinstance(obj, tuple):
        return [x for x in obj if isinstance(x, Benchmark)]
        ## no recursion for now
        #list(chain(*[collect_benchmarks(x) for x in obj]))
    else:
        return []

def collect_benchmarks(modules):
    log.info("Collecting benchmarks from modules %s" % " ".join(modules))
    benchmarks = []

    for module_name in modules:
        log.debug(" Loading %s" % module_name)
        ref = importlib.import_module(module_name)
        new_benchmarks = list(chain(
            *[collect_benchmarks_from_object(x) for x in ref.__dict__.values()]))
        for bm in new_benchmarks:
            assert(bm.name is not None)
            bm.module_name = module_name
        benchmarks.extend(new_benchmarks)

    # Verify that they are all unique according to their checksums
    checksums = [b.checksum for b in benchmarks]
    if not (len(checksums) == len(set(checksums))):
        # Houston we have a problem
        checksums_ = set()
        for b in benchmarks:
            if b.checksum in checksums_:
                log.error(" Benchmark %s already known" % b)
            else:
                checksums_.add(b.checksum)

        raise ValueError("There were duplicate benchmarks -- check if you didn't leak variables")
    return benchmarks

########NEW FILE########
__FILENAME__ = _pstats
"""Class for printing reports on profiled python code."""

# Class for printing reports on profiled python code. rev 1.0  4/1/94
#
# Written by James Roskind
# Based on prior profile module by Sjoerd Mullender...
#   which was hacked somewhat by: Guido van Rossum

"""Class for profiling Python code."""

# Copyright Disney Enterprises, Inc.  All Rights Reserved.
# Licensed to PSF under a Contributor Agreement
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.  See the License for the specific language
# governing permissions and limitations under the License.


import sys
import os
import time
import marshal
import re

__all__ = ["Stats"]

class Stats:
    """This class is used for creating reports from data generated by the
    Profile class.  It is a "friend" of that class, and imports data either
    by direct access to members of Profile class, or by reading in a dictionary
    that was emitted (via marshal) from the Profile class.

    The big change from the previous Profiler (in terms of raw functionality)
    is that an "add()" method has been provided to combine Stats from
    several distinct profile runs.  Both the constructor and the add()
    method now take arbitrarily many file names as arguments.

    All the print methods now take an argument that indicates how many lines
    to print.  If the arg is a floating point number between 0 and 1.0, then
    it is taken as a decimal percentage of the available lines to be printed
    (e.g., .1 means print 10% of all available lines).  If it is an integer,
    it is taken to mean the number of lines of data that you wish to have
    printed.

    The sort_stats() method now processes some additional options (i.e., in
    addition to the old -1, 0, 1, or 2).  It takes an arbitrary number of
    quoted strings to select the sort order.  For example sort_stats('time',
    'name') sorts on the major key of 'internal function time', and on the
    minor key of 'the name of the function'.  Look at the two tables in
    sort_stats() and get_sort_arg_defs(self) for more examples.

    All methods return self,  so you can string together commands like:
        Stats('foo', 'goo').strip_dirs().sort_stats('calls').\
                            print_stats(5).print_callers(5)
    """

    def __init__(self, *args, **kwds):
        # I can't figure out how to explictly specify a stream keyword arg
        # with *args:
        #   def __init__(self, *args, stream=sys.stdout): ...
        # so I use **kwds and sqauwk if something unexpected is passed in.
        self.stream = sys.stdout
        if "stream" in kwds:
            self.stream = kwds["stream"]
            del kwds["stream"]
        if kwds:
            keys = kwds.keys()
            keys.sort()
            extras = ", ".join(["%s=%s" % (k, kwds[k]) for k in keys])
            raise ValueError, "unrecognized keyword args: %s" % extras
        if not len(args):
            arg = None
        else:
            arg = args[0]
            args = args[1:]
        self.init(arg)
        self.add(*args)

    def init(self, arg):
        self.all_callees = None  # calc only if needed
        self.files = []
        self.fcn_list = None
        self.total_tt = 0
        self.total_calls = 0
        self.prim_calls = 0
        self.max_name_len = 0
        self.top_level = {}
        self.stats = {}
        self.sort_arg_dict = {}
        self.load_stats(arg)
        trouble = 1
        try:
            self.get_top_level_stats()
            trouble = 0
        finally:
            if trouble:
                print >> self.stream, "Invalid timing data",
                if self.files: print >> self.stream, self.files[-1],
                print >> self.stream

    def load_stats(self, arg):
        if not arg:  self.stats = {}
        elif isinstance(arg, basestring):
            f = open(arg, 'rb')
            self.stats = marshal.load(f)
            f.close()
            try:
                file_stats = os.stat(arg)
                arg = time.ctime(file_stats.st_mtime) + "    " + arg
            except:  # in case this is not unix
                pass
            self.files = [ arg ]
        elif hasattr(arg, 'create_stats'):
            arg.create_stats()
            self.stats = arg.stats
            arg.stats = {}
        if not self.stats:
            raise TypeError,  "Cannot create or construct a %r object from '%r''" % (
                              self.__class__, arg)
        return

    def get_top_level_stats(self):
        for func, (cc, nc, tt, ct, callers) in self.stats.items():
            self.total_calls += nc
            self.prim_calls  += cc
            self.total_tt    += tt
            if ("jprofile", 0, "profiler") in callers:
                self.top_level[func] = None
            if len(func_std_string(func)) > self.max_name_len:
                self.max_name_len = len(func_std_string(func))

    def add(self, *arg_list):
        if not arg_list: return self
        if len(arg_list) > 1: self.add(*arg_list[1:])
        other = arg_list[0]
        if type(self) != type(other) or self.__class__ != other.__class__:
            other = Stats(other)
        self.files += other.files
        self.total_calls += other.total_calls
        self.prim_calls += other.prim_calls
        self.total_tt += other.total_tt
        for func in other.top_level:
            self.top_level[func] = None

        if self.max_name_len < other.max_name_len:
            self.max_name_len = other.max_name_len

        self.fcn_list = None

        for func, stat in other.stats.iteritems():
            if func in self.stats:
                old_func_stat = self.stats[func]
            else:
                old_func_stat = (0, 0, 0, 0, {},)
            self.stats[func] = add_func_stats(old_func_stat, stat)
        return self

    def dump_stats(self, filename):
        """Write the profile data to a file we know how to load back."""
        f = file(filename, 'wb')
        try:
            marshal.dump(self.stats, f)
        finally:
            f.close()

    # list the tuple indices and directions for sorting,
    # along with some printable description
    sort_arg_dict_default = {
              "calls"     : (((1,-1),              ), "call count"),
              "cumulative": (((3,-1),              ), "cumulative time"),
              "file"      : (((4, 1),              ), "file name"),
              "line"      : (((5, 1),              ), "line number"),
              "module"    : (((4, 1),              ), "file name"),
              "name"      : (((6, 1),              ), "function name"),
              "nfl"       : (((6, 1),(4, 1),(5, 1),), "name/file/line"),
              "pcalls"    : (((0,-1),              ), "call count"),
              "stdname"   : (((7, 1),              ), "standard name"),
              "time"      : (((2,-1),              ), "internal time"),
              }

    def get_sort_arg_defs(self):
        """Expand all abbreviations that are unique."""
        if not self.sort_arg_dict:
            self.sort_arg_dict = dict = {}
            bad_list = {}
            for word, tup in self.sort_arg_dict_default.iteritems():
                fragment = word
                while fragment:
                    if not fragment:
                        break
                    if fragment in dict:
                        bad_list[fragment] = 0
                        break
                    dict[fragment] = tup
                    fragment = fragment[:-1]
            for word in bad_list:
                del dict[word]
        return self.sort_arg_dict

    def sort_stats(self, *field):
        if not field:
            self.fcn_list = 0
            return self
        if len(field) == 1 and type(field[0]) == type(1):
            # Be compatible with old profiler
            field = [ {-1: "stdname",
                      0:"calls",
                      1:"time",
                      2: "cumulative" }  [ field[0] ] ]

        sort_arg_defs = self.get_sort_arg_defs()
        sort_tuple = ()
        self.sort_type = ""
        connector = ""
        for word in field:
            sort_tuple = sort_tuple + sort_arg_defs[word][0]
            self.sort_type += connector + sort_arg_defs[word][1]
            connector = ", "

        stats_list = []
        for func, (cc, nc, tt, ct, callers) in self.stats.iteritems():
            stats_list.append((cc, nc, tt, ct) + func +
                              (func_std_string(func), func))

        stats_list.sort(key=CmpToKey(TupleComp(sort_tuple).compare))

        self.fcn_list = fcn_list = []
        for tuple in stats_list:
            fcn_list.append(tuple[-1])
        return self

    def reverse_order(self):
        if self.fcn_list:
            self.fcn_list.reverse()
        return self

    def strip_dirs(self):
        oldstats = self.stats
        self.stats = newstats = {}
        max_name_len = 0
        for func, (cc, nc, tt, ct, callers) in oldstats.iteritems():
            newfunc = func_strip_path(func)
            if len(func_std_string(newfunc)) > max_name_len:
                max_name_len = len(func_std_string(newfunc))
            newcallers = {}
            for func2, caller in callers.iteritems():
                newcallers[func_strip_path(func2)] = caller

            if newfunc in newstats:
                newstats[newfunc] = add_func_stats(
                                        newstats[newfunc],
                                        (cc, nc, tt, ct, newcallers))
            else:
                newstats[newfunc] = (cc, nc, tt, ct, newcallers)
        old_top = self.top_level
        self.top_level = new_top = {}
        for func in old_top:
            new_top[func_strip_path(func)] = None

        self.max_name_len = max_name_len

        self.fcn_list = None
        self.all_callees = None
        return self

    def calc_callees(self):
        if self.all_callees: return
        self.all_callees = all_callees = {}
        for func, (cc, nc, tt, ct, callers) in self.stats.iteritems():
            if not func in all_callees:
                all_callees[func] = {}
            for func2, caller in callers.iteritems():
                if not func2 in all_callees:
                    all_callees[func2] = {}
                all_callees[func2][func]  = caller
        return

    #******************************************************************
    # The following functions support actual printing of reports
    #******************************************************************

    # Optional "amount" is either a line count, or a percentage of lines.

    def eval_print_amount(self, sel, list, msg):
        new_list = list
        if type(sel) == type(""):
            new_list = []
            for func in list:
                if re.search(sel, func_std_string(func)):
                    new_list.append(func)
        else:
            count = len(list)
            if type(sel) == type(1.0) and 0.0 <= sel < 1.0:
                count = int(count * sel + .5)
                new_list = list[:count]
            elif type(sel) == type(1) and 0 <= sel < count:
                count = sel
                new_list = list[:count]
        if len(list) != len(new_list):
            msg = msg + "   List reduced from %r to %r due to restriction <%r>\n" % (
                         len(list), len(new_list), sel)

        return new_list, msg

    def get_print_list(self, sel_list):
        width = self.max_name_len
        if self.fcn_list:
            list = self.fcn_list[:]
            msg = "   Ordered by: " + self.sort_type + '\n'
        else:
            list = self.stats.keys()
            msg = "   Random listing order was used\n"

        for selection in sel_list:
            list, msg = self.eval_print_amount(selection, list, msg)

        count = len(list)

        if not list:
            return 0, list
        print >> self.stream, msg
        if count < len(self.stats):
            width = 0
            for func in list:
                if  len(func_std_string(func)) > width:
                    width = len(func_std_string(func))
        return width+2, list

    def print_stats(self, *amount):
        for filename in self.files:
            print >> self.stream, filename
        if self.files: print >> self.stream
        indent = ' ' * 8
        for func in self.top_level:
            print >> self.stream, indent, func_get_function_name(func)

        print >> self.stream, indent, self.total_calls, "function calls",
        if self.total_calls != self.prim_calls:
            print >> self.stream, "(%d primitive calls)" % self.prim_calls,
        print >> self.stream, "in %.3f CPU seconds" % self.total_tt
        print >> self.stream
        width, list = self.get_print_list(amount)
        if list:
            self.print_title()
            for func in list:
                self.print_line(func)
            print >> self.stream
            print >> self.stream
        return self

    def print_callees(self, *amount):
        width, list = self.get_print_list(amount)
        if list:
            self.calc_callees()

            self.print_call_heading(width, "called...")
            for func in list:
                if func in self.all_callees:
                    self.print_call_line(width, func, self.all_callees[func])
                else:
                    self.print_call_line(width, func, {})
            print >> self.stream
            print >> self.stream
        return self

    def print_callers(self, *amount):
        width, list = self.get_print_list(amount)
        if list:
            self.print_call_heading(width, "was called by...")
            for func in list:
                cc, nc, tt, ct, callers = self.stats[func]
                self.print_call_line(width, func, callers, "<-")
            print >> self.stream
            print >> self.stream
        return self

    def print_call_heading(self, name_size, column_title):
        print >> self.stream, "Function ".ljust(name_size) + column_title
        # print sub-header only if we have new-style callers
        subheader = False
        for cc, nc, tt, ct, callers in self.stats.itervalues():
            if callers:
                value = callers.itervalues().next()
                subheader = isinstance(value, tuple)
                break
        if subheader:
            print >> self.stream, " "*name_size + "    ncalls  tottime  cumtime"

    def print_call_line(self, name_size, source, call_dict, arrow="->"):
        print >> self.stream, func_std_string(source).ljust(name_size) + arrow,
        if not call_dict:
            print >> self.stream
            return
        clist = call_dict.keys()
        clist.sort()
        indent = ""
        for func in clist:
            name = func_std_string(func)
            value = call_dict[func]
            if isinstance(value, tuple):
                nc, cc, tt, ct = value
                if nc != cc:
                    substats = '%d/%d' % (nc, cc)
                else:
                    substats = '%d' % (nc,)
                substats = '%s %s %s  %s' % (substats.rjust(7+2*len(indent)),
                                             f8(tt), f8(ct), name)
                left_width = name_size + 1
            else:
                substats = '%s(%r) %s' % (name, value, f8(self.stats[func][3]))
                left_width = name_size + 3
            print >> self.stream, indent*left_width + substats
            indent = " "

    def print_title(self):
        print >> self.stream, '   ncalls  tottime  percall  cumtime  percall',
        print >> self.stream, 'filename:lineno(function)'

    def print_line(self, func):  # hack : should print percentages
        cc, nc, tt, ct, callers = self.stats[func]
        c = str(nc)
        if nc != cc:
            c = c + '/' + str(cc)
        print >> self.stream, c.rjust(9),
        print >> self.stream, f8(tt),
        if nc == 0:
            print >> self.stream, ' '*8,
        else:
            print >> self.stream, f8(float(tt)/nc),
        print >> self.stream, f8(ct),
        if cc == 0:
            print >> self.stream, ' '*8,
        else:
            print >> self.stream, f8(float(ct)/cc),
        print >> self.stream, func_std_string(func)

class TupleComp:
    """This class provides a generic function for comparing any two tuples.
    Each instance records a list of tuple-indices (from most significant
    to least significant), and sort direction (ascending or decending) for
    each tuple-index.  The compare functions can then be used as the function
    argument to the system sort() function when a list of tuples need to be
    sorted in the instances order."""

    def __init__(self, comp_select_list):
        self.comp_select_list = comp_select_list

    def compare (self, left, right):
        for index, direction in self.comp_select_list:
            l = left[index]
            r = right[index]
            if l < r:
                return -direction
            if l > r:
                return direction
        return 0

def CmpToKey(mycmp):
    """Convert a cmp= function into a key= function"""
    class K(object):
        def __init__(self, obj):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) == -1
    return K


#**************************************************************************
# func_name is a triple (file:string, line:int, name:string)

def func_strip_path(func_name):
    filename, line, name = func_name
    return os.path.basename(filename), line, name

def func_get_function_name(func):
    return func[2]

def func_std_string(func_name): # match what old profile produced
    if func_name[:2] == ('~', 0):
        # special case for built-in functions
        name = func_name[2]
        if name.startswith('<') and name.endswith('>'):
            return '{%s}' % name[1:-1]
        else:
            return name
    else:
        return "%s:%d(%s)" % func_name

#**************************************************************************
# The following functions combine statists for pairs functions.
# The bulk of the processing involves correctly handling "call" lists,
# such as callers and callees.
#**************************************************************************

def add_func_stats(target, source):
    """Add together all the stats for two profile entries."""
    cc, nc, tt, ct, callers = source
    t_cc, t_nc, t_tt, t_ct, t_callers = target
    return (cc+t_cc, nc+t_nc, tt+t_tt, ct+t_ct,
              add_callers(t_callers, callers))

def add_callers(target, source):
    """Combine two caller lists in a single list."""
    new_callers = {}
    for func, caller in target.iteritems():
        new_callers[func] = caller
    for func, caller in source.iteritems():
        if func in new_callers:
            if isinstance(caller, tuple):
                # format used by cProfile
                new_callers[func] = tuple([i[0] + i[1] for i in
                                           zip(caller, new_callers[func])])
            else:
                # format used by profile
                new_callers[func] += caller
        else:
            new_callers[func] = caller
    return new_callers

def count_calls(callers):
    """Sum the caller statistics to get total number of calls received."""
    nc = 0
    for calls in callers.itervalues():
        nc += calls
    return nc

#**************************************************************************
# The following functions support printing of reports
#**************************************************************************

def f8(x):
    return "%8.3f" % x

#**************************************************************************
# Statistics browser added by ESR, April 2001
#**************************************************************************

if __name__ == '__main__':
    import cmd
    try:
        import readline
    except ImportError:
        pass

    class ProfileBrowser(cmd.Cmd):
        def __init__(self, profile=None):
            cmd.Cmd.__init__(self)
            self.prompt = "% "
            if profile is not None:
                self.stats = Stats(profile)
                self.stream = self.stats.stream
            else:
                self.stats = None
                self.stream = sys.stdout

        def generic(self, fn, line):
            args = line.split()
            processed = []
            for term in args:
                try:
                    processed.append(int(term))
                    continue
                except ValueError:
                    pass
                try:
                    frac = float(term)
                    if frac > 1 or frac < 0:
                        print >> self.stream, "Fraction argument must be in [0, 1]"
                        continue
                    processed.append(frac)
                    continue
                except ValueError:
                    pass
                processed.append(term)
            if self.stats:
                getattr(self.stats, fn)(*processed)
            else:
                print >> self.stream, "No statistics object is loaded."
            return 0
        def generic_help(self):
            print >> self.stream, "Arguments may be:"
            print >> self.stream, "* An integer maximum number of entries to print."
            print >> self.stream, "* A decimal fractional number between 0 and 1, controlling"
            print >> self.stream, "  what fraction of selected entries to print."
            print >> self.stream, "* A regular expression; only entries with function names"
            print >> self.stream, "  that match it are printed."

        def do_add(self, line):
            if self.stats:
                self.stats.add(line)
            else:
                print >> self.stream, "No statistics object is loaded."
            return 0
        def help_add(self):
            print >> self.stream, "Add profile info from given file to current statistics object."

        def do_callees(self, line):
            return self.generic('print_callees', line)
        def help_callees(self):
            print >> self.stream, "Print callees statistics from the current stat object."
            self.generic_help()

        def do_callers(self, line):
            return self.generic('print_callers', line)
        def help_callers(self):
            print >> self.stream, "Print callers statistics from the current stat object."
            self.generic_help()

        def do_EOF(self, line):
            print >> self.stream, ""
            return 1
        def help_EOF(self):
            print >> self.stream, "Leave the profile brower."

        def do_quit(self, line):
            return 1
        def help_quit(self):
            print >> self.stream, "Leave the profile brower."

        def do_read(self, line):
            if line:
                try:
                    self.stats = Stats(line)
                except IOError, args:
                    print >> self.stream, args[1]
                    return
                except Exception as err:
                    print >> self.stream, err.__class__.__name__ + ':', err
                    return
                self.prompt = line + "% "
            elif len(self.prompt) > 2:
                line = self.prompt[:-2]
                self.do_read(line)
            else:
                print >> self.stream, "No statistics object is current -- cannot reload."
            return 0
        def help_read(self):
            print >> self.stream, "Read in profile data from a specified file."
            print >> self.stream, "Without argument, reload the current file."

        def do_reverse(self, line):
            if self.stats:
                self.stats.reverse_order()
            else:
                print >> self.stream, "No statistics object is loaded."
            return 0
        def help_reverse(self):
            print >> self.stream, "Reverse the sort order of the profiling report."

        def do_sort(self, line):
            if not self.stats:
                print >> self.stream, "No statistics object is loaded."
                return
            abbrevs = self.stats.get_sort_arg_defs()
            if line and not filter(lambda x,a=abbrevs: x not in a,line.split()):
                self.stats.sort_stats(*line.split())
            else:
                print >> self.stream, "Valid sort keys (unique prefixes are accepted):"
                for (key, value) in Stats.sort_arg_dict_default.iteritems():
                    print >> self.stream, "%s -- %s" % (key, value[1])
            return 0
        def help_sort(self):
            print >> self.stream, "Sort profile data according to specified keys."
            print >> self.stream, "(Typing `sort' without arguments lists valid keys.)"
        def complete_sort(self, text, *args):
            return [a for a in Stats.sort_arg_dict_default if a.startswith(text)]

        def do_stats(self, line):
            return self.generic('print_stats', line)
        def help_stats(self):
            print >> self.stream, "Print statistics from the current stat object."
            self.generic_help()

        def do_strip(self, line):
            if self.stats:
                self.stats.strip_dirs()
            else:
                print >> self.stream, "No statistics object is loaded."
        def help_strip(self):
            print >> self.stream, "Strip leading path information from filenames in the report."

        def help_help(self):
            print >> self.stream, "Show help for a given command."

        def postcmd(self, stop, line):
            if stop:
                return stop
            return None

    import sys
    if len(sys.argv) > 1:
        initprofile = sys.argv[1]
    else:
        initprofile = None
    try:
        browser = ProfileBrowser(initprofile)
        print >> browser.stream, "Welcome to the profile statistics browser."
        browser.cmdloop()
        print >> browser.stream, "Goodbye."
    except KeyboardInterrupt:
        pass

# That's all, folks.

########NEW FILE########
