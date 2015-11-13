__FILENAME__ = test_tracemalloc
import ctypes
import gc
import imp
import os
import sys
import time
import tracemalloc
import unittest
try:
    # Python 2
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
except ImportError:
    # Python 3
    from io import StringIO

pythonapi = ctypes.cdll.LoadLibrary(None)

# Need a special patch to track Python free lists (ex: PyDict free list)
TRACK_FREE_LISTS = hasattr(pythonapi, '_PyFreeList_SetAllocators')

EMPTY_STRING_SIZE = sys.getsizeof(b'')
THIS_FILE = os.path.basename(__file__)

# Minimum size in bytes of a C pointer (void*)
MIN_SIZE_PTR = 4

class UncollectableObject:
    def __init__(self):
        self.ref = self

    def __del__(self):
        pass

def clear_stats():
    tracemalloc.disable()
    tracemalloc.enable()

def get_source(lineno_delta):
    filename = __file__
    frame = sys._getframe(1)
    lineno = frame.f_lineno + lineno_delta
    return filename, lineno

def allocate_bytes(size):
    source = get_source(1)
    data = b'x' * (size - EMPTY_STRING_SIZE)
    return data, source

class TestTracemalloc(unittest.TestCase):
    def setUp(self):
        tracemalloc.enable()

    def tearDown(self):
        tracemalloc.disable()
        gc.set_debug(0)

    def test_get_trace(self):
        size = 12345
        obj, obj_source = allocate_bytes(size)
        trace = tracemalloc._get_object_trace(obj)
        self.assertEqual(trace, (size,) + obj_source)

    def test_get_process_memory(self):
        obj_size = 1024 * 1024
        orig = tracemalloc.get_process_memory()
        if orig is None:
            self.skipTest("get_process_memory is not supported")
        obj, obj_source = allocate_bytes(obj_size)
        curr = tracemalloc.get_process_memory()
        # Allocating obj_size may allocate less memory than requested because
        # the Linux kernel overallocates memory mappings... or something like
        # that
        self.assertGreaterEqual(curr - orig, obj_size // 2)

    def test_get_stats(self):
        total = 0
        count = 0
        objs = []
        for index in range(5):
            size = 1234
            obj, source = allocate_bytes(size)
            objs.append(obj)
            total += size
            count += 1

            stats = tracemalloc._get_stats()
            filename, lineno = source
            self.assertEqual(stats[filename][lineno], (total, count))

    @unittest.skipUnless(TRACK_FREE_LISTS, "free lists are not tracked")
    def test_free_lists(self):
        data = None

        if sys.version_info < (3,):
            # Python 2.x
            test_types = (int, unicode, tuple, list, dict, set)
            # FIXME: test more types: float, binded method, C function
        else:
            # Python 3.x
            test_types = (tuple, list, dict, set)

        for test_type in test_types:
            clear_stats()

            if test_type in (tuple, list):
                length = 10 ** 5
                if test_type == tuple:
                    base = (None,)
                else:
                    base = [None]
                filename, lineno = get_source(1)
                data = base * length
                min_size = MIN_SIZE_PTR * length

            elif test_type == dict:
                length = 1024
                items = [(str(key), key) for key in range(length)]
                filename, lineno = get_source(1)
                data = dict(items)
                min_size = MIN_SIZE_PTR * length

            elif test_type == set:
                length = 1024
                items = tuple(map(str, range(length)))
                filename, lineno = get_source(1)
                data = set(items)
                min_size = MIN_SIZE_PTR * length

            elif test_type == unicode:
                length = 4 * 1024

                filename, lineno = get_source(1)
                data = u"\uffff" * length

                if hasattr(sys, 'getsizeof'):
                    min_size = sys.getsizeof(data)
                else:
                    # In narrow mode, Python uses UCS-2: 16-bit per character
                    min_size = 2 * length

            else:
                assert test_type == int

                # build an integer bigger than 4 KB
                pow2 = 1000000

                filename, lineno = get_source(1)
                data = 2 ** pow2

                if hasattr(sys, 'getsizeof'):
                    min_size = sys.getsizeof(data)
                else:
                    # Python 2.7 on 64-bit system uses 30 bits per digit
                    ndigits = (pow2 + 1) // 30
                    # 32 bits per Python digit
                    min_size = ndigits * 4

            stats = tracemalloc._get_stats()
            trace = stats[filename][lineno]
            self.assertGreaterEqual(trace[0], min_size)
            self.assertGreaterEqual(trace[1], 1)

            # Deallocate
            data = None
            stats = tracemalloc._get_stats()
            self.assertNotIn(lineno, stats[filename])


    def test_timer(self):
        calls = []
        def func(*args, **kw):
            calls.append((args, kw))

        # timer enabled
        args = (1, 2, 3)
        kwargs = {'arg': 4}
        tracemalloc.start_timer(1, func, args, kwargs)
        time.sleep(1)
        obj, source = allocate_bytes(123)
        self.assertEqual(len(calls), 1)
        call = calls[0]
        self.assertEqual(call, (args, kwargs))

        # timer disabled
        tracemalloc.stop_timer()
        time.sleep(1)
        obj2, source2 = allocate_bytes(123)
        self.assertEqual(len(calls), 1)

    def _test_get_uncollectable(self, saveall):
        getter = tracemalloc._GetUncollectable()

        leak_source = get_source(1)
        leak = UncollectableObject()
        leak_id = id(leak)
        leak_dict_id = id(leak.__dict__)
        leak = None

        objects = getter.get_new_objects()
        if saveall:
            self.assertEqual(len(objects), 2)
        else:
            self.assertEqual(len(objects), 1)

        obj, obj_source = objects[0]
        self.assertEqual(id(obj), leak_id)
        self.assertGreater(obj_source[0], 1)
        self.assertEqual(obj_source[1:], leak_source)

        if saveall:
            obj, obj_source = objects[1]
            self.assertEqual(id(obj), leak_dict_id)

    def test_get_uncollectable(self):
        self._test_get_uncollectable(False)

    def test_get_uncollectable_saveall(self):
        gc.set_debug(gc.DEBUG_SAVEALL)
        self._test_get_uncollectable(True)

    def _test_display_uncollectable(self, saveall):
        stream = StringIO()
        display = tracemalloc.DisplayGarbage(file=stream)
        stream.truncate()

        leak_source = get_source(1)
        leak = UncollectableObject()
        leak_id = id(leak)
        leak_dict_id = id(leak.__dict__)
        leak = None

        display.display()
        output = stream.getvalue().splitlines()
        self.assertIn('UncollectableObject', output[0])
        self.assertIn(THIS_FILE, output[0])
        if saveall:
            self.assertEqual(len(output), 2)
            self.assertIn('{', output[1])
        else:
            self.assertEqual(len(output), 1)

    def test_display_uncollectable(self):
        self._test_display_uncollectable(False)

    def test_display_uncollectable_saveall(self):
        gc.set_debug(gc.DEBUG_SAVEALL)
        self._test_display_uncollectable(True)

    def _test_display_uncollectable_cumulative(self, saveall):
        gc.set_debug(gc.DEBUG_SAVEALL)
        stream = StringIO()
        display = tracemalloc.DisplayGarbage(file=stream)
        display.cumulative = True

        # Leak 1
        UncollectableObject()

        display.display()
        output = stream.getvalue().splitlines()
        self.assertIn('UncollectableObject', output[0])
        self.assertIn(THIS_FILE, output[0])
        if saveall:
            self.assertEqual(len(output), 2)
            self.assertIn('{', output[1])
        else:
            self.assertEqual(len(output), 1)

        # Leak 2
        UncollectableObject()

        stream.seek(0)
        stream.truncate()
        display.display()
        output = stream.getvalue().splitlines()
        self.assertIn('UncollectableObject', output[0])
        self.assertIn(THIS_FILE, output[0])
        if saveall:
            self.assertEqual(len(output), 4)
            self.assertIn('{', output[1])
            self.assertIn('UncollectableObject', output[2])
            self.assertIn(THIS_FILE, output[2])
            self.assertIn('{', output[3])
        else:
            self.assertEqual(len(output), 2)
            self.assertIn('UncollectableObject', output[1])
            self.assertIn(THIS_FILE, output[1])

    def test_display_uncollectable_cumulative(self):
        self._test_display_uncollectable_cumulative(False)

    def test_display_uncollectable_cumulative(self):
        gc.set_debug(gc.DEBUG_SAVEALL)
        self._test_display_uncollectable_cumulative(True)

    def test_version(self):
        filename = os.path.join(os.path.dirname(__file__), 'setup.py')
        if sys.version_info >= (3, 4):
            import importlib
            loader = importlib.machinery.SourceFileLoader('setup', filename)
            setup_py = loader.load_module()
        else:
            setup_py = imp.load_source('setup', filename)
        self.assertEqual(tracemalloc.__version__, setup_py.VERSION)


if __name__ == "__main__":
    unittest.main()


########NEW FILE########
__FILENAME__ = tracemalloc
from __future__ import with_statement
import datetime
import operator
import os
import sys
import types
pickle = None

from _tracemalloc import *
from _tracemalloc import __version__, _get_stats, _get_object_trace

if sys.version_info >= (3,):
    def _iteritems(obj):
        return obj.items()
else:
    def _iteritems(obj):
        return obj.iteritems()

def _get_timestamp():
    return str(datetime.datetime.now()).split(".")[0]

def __format_size(size, sign=False):
    for unit in ('B', 'KiB', 'MiB', 'GiB'):
        if abs(size) < 5 * 1024:
            if sign:
                return "%+i %s" % (size, unit)
            else:
                return "%i %s" % (size, unit)
        size /= 1024

    if sign:
        return "%+i TiB" % size
    else:
        return "%i TiB" % size

_FORMAT_YELLOW = '\x1b[1;33m%s\x1b[0m'
_FORMAT_BOLD = '\x1b[1m%s\x1b[0m'
_FORMAT_CYAN = '\x1b[36m%s\x1b[0m'

def _format_size(size, color):
    text = __format_size(size)
    if color:
        text = _FORMAT_YELLOW % text
    return text

def _format_size_diff(size, diff, color):
    text = __format_size(size)
    if diff is not None:
        if color:
            text = _FORMAT_BOLD % text
        textdiff = __format_size(diff, sign=True)
        if color:
            textdiff = _FORMAT_YELLOW % textdiff
        text += " (%s)" % textdiff
    else:
        if color:
            text = _FORMAT_YELLOW % text
    return text

def _colorize_filename(filename):
    path, basename = os.path.split(filename)
    if path:
        path += os.path.sep
    return _FORMAT_CYAN % path + basename

def get_process_memory():
    if get_process_memory.psutil_process is None:
        try:
            import psutil
        except ImportError:
            get_process_memory.psutil_process = False
        else:
            pid = os.getpid()
            get_process_memory.psutil_process = psutil.Process(pid)

    if get_process_memory.psutil_process != False:
        meminfo = get_process_memory.psutil_process.get_memory_info()
        return meminfo.rss

    if get_process_memory.support_proc == False:
        return

    try:
        fp = open("/proc/self/status")
    except IOError:
        get_process_memory.support_proc = False
        return None

    get_process_memory.support_proc = True
    with fp:
        for line in fp:
            if not(line.startswith("VmRSS:") and line.endswith(" kB\n")):
                continue
            value = line[6:-4].strip()
            value = int(value) * 1024
            return value

    # VmRss not found in /proc/self/status
    get_process_memory.support_proc = False
    return None
get_process_memory.support_proc = None
get_process_memory.psutil_process = None

# (size diff, size, count diff, count)
_TRACE_ZERO = (0, 0, 0, 0)

class _TopSnapshot:
    __slots__ = ('name', 'stats', 'process_memory', 'user_data')

    def __init__(self, top):
        self.name = top.name
        self.stats = top.snapshot_stats
        self.process_memory = top.process_memory
        self.user_data = top.user_data


class _Top:
    __slots__ = (
        'name', 'raw_stats', 'real_process_memory', 'user_data',
        'top_stats', 'snapshot_stats', 'tracemalloc_size', 'process_memory')

    def __init__(self, name, raw_stats, real_process_memory, user_data):
        self.name = name
        self.raw_stats = raw_stats
        self.real_process_memory = real_process_memory
        self.user_data = user_data

        self.top_stats = None
        self.snapshot_stats = None
        self.tracemalloc_size = None
        self.process_memory = None

    def compute(self, display_top, want_snapshot):
        if display_top._snapshot is not None:
            snapshot = display_top._snapshot.stats.copy()
        else:
            snapshot = None

        # list of: (filename: str, line number: int, trace: tuple)
        stats = []
        if want_snapshot:
            new_snapshot = {}
        else:
            new_snapshot = None
        tracemalloc_size = 0
        for filename, line_dict in _iteritems(self.raw_stats):
            if os.path.basename(filename) == "tracemalloc.py":
                tracemalloc_size += sum(
                    item[0]
                    for lineno, item in _iteritems(line_dict))
                # ignore allocations in this file
                continue
            if display_top.show_lineno:
                for lineno, item in _iteritems(line_dict):
                    key = (filename, lineno)

                    size, count = item
                    if snapshot is not None:
                        previous = snapshot.pop(key, _TRACE_ZERO)
                        trace = (size - previous[1], size, count - previous[3], count)
                    else:
                        trace = (0, size, 0, count)
                    if lineno is None:
                        lineno = "?"
                    stats.append((filename, lineno, trace))
                    if want_snapshot:
                        new_snapshot[key] = trace
            else:
                key = (filename, None)
                size = count = 0
                for lineno, item in _iteritems(line_dict):
                    size += item[0]
                    count += item[1]
                if snapshot is not None:
                    previous = snapshot.pop(key, _TRACE_ZERO)
                    trace = (
                        size - previous[1], size,
                        count - previous[3], count)
                else:
                    trace = (0, size, 0, count)
                stats.append((filename, None, trace))
                if want_snapshot:
                    new_snapshot[key] = trace

        if snapshot is not None:
            for key, trace in _iteritems(snapshot):
                trace = (-trace[1], 0, -trace[3], 0)
                stats.append((key[0], key[1], trace))

        self.top_stats = stats
        self.snapshot_stats = new_snapshot
        self.tracemalloc_size = tracemalloc_size
        if self.real_process_memory:
            size = self.real_process_memory - self.tracemalloc_size
            self.process_memory = size


class DisplayTop:
    def __init__(self, top_count, file=None):
        self.top_count = top_count
        self._snapshot = None
        self.show_lineno = False
        self.show_size = True
        self.show_count = True
        self.show_average = True
        self.filename_parts = 3
        if file is not None:
            self.stream = file
        else:
            self.stream = sys.stdout
        self.compare_with_previous = True
        self.color = self.stream.isatty()
        self.user_data_callback = None

    def cleanup_filename(self, filename):
        parts = filename.split(os.path.sep)
        if self.filename_parts < len(parts):
            parts = ['...'] + parts[-self.filename_parts:]
        return os.path.sep.join(parts)

    def _format_trace(self, trace, show_diff):
        if not self.show_count and not self.show_average:
            if show_diff:
                return _format_size_diff(trace[1], trace[0], self.color)
            else:
                return _format_size(trace[1], self.color)

        parts = []
        if self.show_size:
            if show_diff:
                text = _format_size_diff(trace[1], trace[0], self.color)
            else:
                text = _format_size(trace[1], self.color)
            parts.append("size=%s" % text)
        if self.show_count and (trace[3] or trace[2]):
            text = "count=%s" % trace[3]
            if show_diff:
                text += " (%+i)" % trace[2]
            parts.append(text)
        if (self.show_average
        and trace[3] > 1):
            parts.append('average=%s' % _format_size(trace[1] // trace[3], False))
        return ', '.join(parts)

    def _display(self, top):
        log = self.stream.write
        snapshot = self._snapshot
        has_snapshot = (snapshot is not None)

        stats = top.top_stats
        stats.sort(key=operator.itemgetter(2), reverse=True)

        count = min(self.top_count, len(stats))
        if self.show_lineno:
            text = "file and line"
        else:
            text = "file"
        text = "Top %s allocations per %s" % (count, text)
        if self.color:
            text = _FORMAT_CYAN % text
        if has_snapshot:
            text += ' (compared to %s)' % snapshot.name
        name = top.name
        if self.color:
            name = _FORMAT_BOLD % name
        log("%s: %s\n" % (name, text))

        total = [0, 0, 0, 0]
        other = None
        for index, item in enumerate(stats):
            filename, lineno, trace = item
            if index < self.top_count:
                filename = self.cleanup_filename(filename)
                if lineno is not None:
                    filename = "%s:%s" % (filename, lineno)
                text = self._format_trace(trace, has_snapshot)
                if self.color:
                    filename = _colorize_filename(filename)
                log("#%s: %s: %s\n" % (1 + index, filename, text))
            elif other is None:
                other = tuple(total)
            total[0] += trace[0]
            total[1] += trace[1]
            total[2] += trace[2]
            total[3] += trace[3]

        nother = len(stats) - self.top_count
        if nother > 0:
            other = [
                total[0] - other[0],
                total[1] - other[1],
                total[2] - other[2],
                total[3] - other[3],
            ]
            text = self._format_trace(other, has_snapshot)
            log("%s more: %s\n" % (nother, text))

        text = self._format_trace(total, has_snapshot)
        log("Total Python memory: %s\n" % text)

        if top.process_memory:
            trace = [0, top.process_memory, 0, 0]
            if has_snapshot:
                trace[0] = trace[1] - snapshot.process_memory
            text = self._format_trace(trace, has_snapshot)
            ignore = (" (ignore tracemalloc: %s)"
                          % _format_size(top.tracemalloc_size, False))
            if self.color:
                ignore = _FORMAT_CYAN % ignore
            text += ignore
            log("Total process memory: %s\n" % text)
        else:
            text = ("Ignore tracemalloc: %s"
                    % _format_size(top.tracemalloc_size, False))
            if self.color:
                text = _FORMAT_CYAN % text
            log(text + "\n")

        if top.user_data:
            for index, item in enumerate(top.user_data):
                title, format, value = item
                if format == 'size':
                    trace = [0, value, 0, 0]
                    if has_snapshot:
                        trace[0] = trace[1] - snapshot.user_data[index][2]
                    text = self._format_trace(trace, has_snapshot)
                else:
                    text = str(value)
                log("%s: %s\n" % (title, text))

        log("\n")
        self.stream.flush()

    def _run(self, top):
        save_snapshot = self.compare_with_previous
        if self._snapshot is None:
            save_snapshot = True

        top.compute(self, save_snapshot)
        self._display(top)
        if save_snapshot:
            self._snapshot = _TopSnapshot(top)

    def display(self):
        snapshot = Snapshot.create(self.user_data_callback)
        snapshot.display(self)

    def start(self, delay):
        start_timer(int(delay), self.display)

    def stop(self):
        stop_timer()


def _lazy_import_pickle():
    # lazy loader for the pickle module
    global pickle
    if pickle is None:
        try:
            import cPickle as pickle
        except ImportError:
            import pickle
    return pickle


class Snapshot:
    FORMAT_VERSION = 1
    __slots__ = ('stats', 'timestamp', 'pid', 'process_memory', 'user_data')

    def __init__(self, stats, timestamp, pid, process_memory, user_data):
        self.stats = stats
        self.timestamp = timestamp
        self.pid = pid
        self.process_memory = process_memory
        self.user_data = user_data

    @classmethod
    def create(cls, user_data_callback=None):
        timestamp = _get_timestamp()
        stats = _get_stats()
        pid = os.getpid()
        process_memory = get_process_memory()
        if user_data_callback is not None:
            user_data = user_data_callback()
        else:
            user_data = None
        return cls(stats, timestamp, pid, process_memory, user_data)

    @classmethod
    def load(cls, filename):
        pickle = _lazy_import_pickle()
        try:
            with open(filename, "rb") as fp:
                data = pickle.load(fp)
        except Exception:
            err = sys.exc_info()[1]
            print("ERROR: Failed to load %s: [%s] %s" % (filename, type(err).__name__, err))
            sys.exit(1)

        try:
            if data['format_version'] != cls.FORMAT_VERSION:
                raise TypeError("unknown format version")

            stats = data['stats']
            timestamp = data['timestamp']
            pid = data['pid']
            process_memory = data.get('process_memory')
            user_data = data.get('user_data')
        except KeyError:
            raise TypeError("invalid file format")

        return cls(stats, timestamp, pid, process_memory, user_data)

    def write(self, filename):
        pickle = _lazy_import_pickle()
        data = {
            'format_version': self.FORMAT_VERSION,
            'timestamp': self.timestamp,
            'stats': self.stats,
            'pid': self.pid,
        }
        if self.process_memory is not None:
            data['process_memory'] = self.process_memory
        if self.user_data is not None:
            data['user_data'] = self.user_data

        with open(filename, "wb") as fp:
            pickle.dump(data, fp, pickle.HIGHEST_PROTOCOL)

    def filter_filenames(self, patterns, include):
        import fnmatch
        if isinstance(patterns, str):
            # backward compatibility with pytracemalloc 0.7
            patterns = (patterns,)
        new_stats = {}
        for filename, file_stats in _iteritems(self.stats):
            if include:
                ignore = all(
                    not fnmatch.fnmatch(filename, pattern)
                    for pattern in patterns)
            else:
                ignore = any(
                    fnmatch.fnmatch(filename, pattern)
                    for pattern in patterns)
            if ignore:
                continue
            new_stats[filename] = file_stats
        self.stats = new_stats

    def display(self, display_top, show_pid=False):
        name = self.timestamp
        if show_pid:
            name += ' [pid %s]' % self.pid
        top = _Top(name, self.stats, self.process_memory, self.user_data)
        display_top._run(top)


class TakeSnapshot:
    def __init__(self):
        self.filename_template = "tracemalloc-$counter.pickle"
        self.counter = 1
        self.user_data_callback = None

    def take_snapshot(self):
        snapshot = Snapshot.create(self.user_data_callback)

        filename = self.filename_template
        filename = filename.replace("$pid", str(snapshot.pid))
        timestamp = snapshot.timestamp.replace(" ", "-")
        filename = filename.replace("$timestamp", timestamp)
        filename = filename.replace("$counter", "%04i" % self.counter)

        snapshot.write(filename)
        self.counter += 1
        return snapshot, filename

    def _task(self):
        snapshot, filename = self.take_snapshot()
        sys.stderr.write("%s: Write a snapshot of memory allocations into %s\n"
                         % (snapshot.timestamp, filename))

    def start(self, delay):
        start_timer(int(delay), self._task)

    def stop(self):
        stop_timer()


class _GetUncollectable:
    def __init__(self):
        enable()
        import gc
        self._gc = gc
        self.seen = set()
        self._gc.collect()
        garbage = tuple(self._gc.garbage)
        for obj in garbage:
            obj_id = id(obj)
            if obj_id in self.seen:
                continue
            self.seen.add(obj_id)

    def get_new_objects(self):
        self._gc.collect()
        garbage = tuple(self._gc.garbage)
        objects = []
        for obj in garbage:
            obj_id = id(obj)
            if obj_id in self.seen:
                continue
            self.seen.add(obj_id)

            source = _get_object_trace(obj)
            objects.append((obj, source))
        return objects


class DisplayGarbage:
    def __init__(self, file=None):
        try:
            # Python 3
            import reprlib
        except ImportError:
            # Python 2
            import repr as reprlib

        if file is not None:
            self.stream = file
        else:
            self.stream = sys.stdout
        self.cumulative = False
        self._getter = _GetUncollectable()
        self._objects = []
        self.color = self.stream.isatty()
        reprobj = reprlib.Repr()
        reprobj.maxstring = 100
        reprobj.maxother = 100
        reprobj.maxlevel = 1
        self.format_object = reprobj.repr

    def display(self):
        objects = self._getter.get_new_objects()
        if self.cumulative:
            self._objects.extend(objects)
            objects = self._objects
        for obj, source in objects:
            obj_repr = self.format_object(obj)
            #if isinstance(obj, types.InstanceType):
            #    obj_repr = '%s instance' % obj.__class__.__name__
            #else:
            #    obj_repr = type(obj).__name__
            obj_repr = "[id %x] %s" % (id(obj), obj_repr)
            if source is not None:
                size, filename, lineno = source
                if lineno is None:
                    lineno = "?"
                if self.color:
                    filename = _colorize_filename(filename)
                size = _format_size(size, self.color)
            else:
                filename = "???"
                lineno = "?"
                size = "?"
            text = "UNCOLLECTABLE OBJECT: %s:%s: %s (%s)" % (filename, lineno, obj_repr, size)
            self.stream.write(text + "\n")
        self.stream.flush()


def main():
    from optparse import OptionParser

    print("tracemalloc %s" % __version__)
    print("")

    parser = OptionParser(usage="%prog trace1.pickle [trace2.pickle  trace3.pickle ...]")
    parser.add_option("-l", "--line-number",
        help="Display line number",
        action="store_true", default=False)
    parser.add_option("-n", "--number",
        help="Number of traces displayed per top (default: 10)",
        type="int", action="store", default=10)
    parser.add_option("--first",
        help="Compare with the first trace, instead of with the previous trace",
        action="store_true", default=False)
    parser.add_option("--include", metavar="MATCH",
        help="Only include filenames matching pattern MATCH, "
             "the option can be specified multiple times",
        action="append", type=str)
    parser.add_option("--exclude", metavar="MATCH",
        help="Exclude filenames matching pattern MATCH, "
             "the option can be specified multiple times",
        action="append", type=str)
    parser.add_option("-S", "--hide-size",
        help="Hide the size of allocations",
        action="store_true", default=False)
    parser.add_option("-C", "--hide-count",
        help="Hide the number of allocations",
        action="store_true", default=False)
    parser.add_option("-A", "--hide-average",
        help="Hide the average size of allocations",
        action="store_true", default=False)
    parser.add_option("-P", "--filename-parts",
        help="Number of displayed filename parts (default: 3)",
        type="int", action="store", default=3)
    parser.add_option("--color",
        help="Enable colors even if stdout is not a TTY",
        action="store_true", default=False)
    parser.add_option("--no-color",
        help="Disable colors",
        action="store_true", default=False)

    options, filenames = parser.parse_args()
    if not filenames:
        parser.print_usage()
        sys.exit(1)
    # remove duplicates
    filenames = list(set(filenames))

    snapshots = []
    for filename in filenames:
        snapshot = Snapshot.load(filename)
        if options.include:
            snapshot.filter_filenames(options.include, True)
        if options.exclude:
            snapshot.filter_filenames(options.exclude, False)
        snapshots.append(snapshot)
    snapshots.sort(key=lambda snapshot: snapshot.timestamp)

    pids = set(snapshot.pid for snapshot in snapshots)
    show_pid = (len(pids) > 1)
    if show_pid:
        pids = ', '.join(map(str, sorted(pids)))
        print("WARNING: Traces generated by different processes: %s" % pids)
        print("")

    top = DisplayTop(options.number)
    top.filename_parts = options.filename_parts
    top.show_average = not options.hide_average
    top.show_count = not options.hide_count
    top.show_lineno = options.line_number
    top.show_size = not options.hide_size
    top.compare_with_previous = not options.first
    if options.color:
        top.color = True
    elif options.no_color:
        top.color = False

    for snapshot in snapshots:
        snapshot.display(top, show_pid=show_pid)

    print("%s snapshots" % len(snapshots))


if __name__ == "__main__":
    if 0:
        import cProfile
        cProfile.run('main()', sort='tottime')
    else:
        main()


########NEW FILE########
