__FILENAME__ = fsevents
import os
import sys
import threading

from _fsevents import (
    loop,
    stop,
    schedule,
    unschedule,
    CF_POLLIN,
    CF_POLLOUT,
    FS_IGNORESELF,
    FS_FILEEVENTS,
    FS_ITEMCREATED,
    FS_ITEMREMOVED,
    FS_ITEMINODEMETAMOD,
    FS_ITEMRENAMED,
    FS_ITEMMODIFIED,
    FS_ITEMFINDERINFOMOD,
    FS_ITEMCHANGEOWNER,
    FS_ITEMXATTRMOD,
    FS_ITEMISFILE,
    FS_ITEMISDIR,
    FS_ITEMISSYMLINK,  
)

# inotify event flags
IN_MODIFY = 0x00000002
IN_ATTRIB = 0x00000004
IN_CREATE = 0x00000100
IN_DELETE = 0x00000200
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080

def check_path_string_type(*paths):
    for path in paths:
        if not isinstance(path, str):
            raise TypeError(
                "Path must be string, not '%s'." % type(path).__name__)


class Observer(threading.Thread):
    event = None
    runloop = None

    def __init__(self):
        self.streams = set()
        self.schedulings = {}
        self.lock = threading.Lock()
        threading.Thread.__init__(self)

    def run(self):
        # wait until we have streams registered
        while not self.streams:
            self.event = threading.Event()
            self.event.wait()
            if self.event is None:
                return
            self.event = None

        self.lock.acquire()

        try:
            # schedule all streams
            for stream in self.streams:
                self._schedule(stream)

            self.streams = None
        finally:
            self.lock.release()

        # start run-loop
        loop(self)

    def _schedule(self, stream):
        if not stream.paths:
            raise ValueError("No paths to observe.")
        if stream.file_events:
            callback = FileEventCallback(stream.callback, stream.raw_paths)
        else:
            def callback(paths, masks):
                for path, mask in zip(paths, masks):
                    if sys.version_info[0] >= 3:
                        path = path.decode('utf-8')
                    stream.callback(path, mask)
        schedule(self, stream, callback, stream.paths)

    def schedule(self, stream):
        self.lock.acquire()
        try:
            if self.streams is None:
                self._schedule(stream)
            elif stream in self.streams:
                raise ValueError("Stream already scheduled.")
            else:
                self.streams.add(stream)
                if self.event is not None:
                    self.event.set()
        finally:
            self.lock.release()

    def unschedule(self, stream):
        self.lock.acquire()
        try:
            if self.streams is None:
                unschedule(stream)
            else:
                self.streams.remove(stream)
        finally:
            self.lock.release()

    def stop(self):
        if self.event is None:
            stop(self)
        else:
            event = self.event
            self.event = None
            event.set()

class Stream(object):
    def __init__(self, callback, *paths, **options):
        file_events = options.pop('file_events', False)
        assert len(options) == 0, "Invalid option(s): %s" % repr(options.keys())
        check_path_string_type(*paths)

        self.callback = callback
        self.raw_paths = paths

        # The C-extension needs the path in 8-bit form.
        self.paths = [
            path if isinstance(path, bytes) 
            else path.encode('utf-8') for path in paths
        ]

        self.file_events = file_events

class FileEvent(object):
    __slots__ = 'mask', 'cookie', 'name'

    def __init__(self, mask, cookie, name):
        self.mask = mask
        self.cookie = cookie
        self.name = name

    def __repr__(self):
        return repr((self.mask, self.cookie, self.name))

class FileEventCallback(object):
    def __init__(self, callback, paths):
        self.snapshots = {}
        for path in paths:
            check_path_string_type(path)
            self.snapshot(path)
        self.callback = callback
        self.cookie = 0

    def __call__(self, paths, masks):
        events = []
        deleted = {}

        for path in sorted(paths):
            if sys.version_info[0] >= 3:
                path = path.decode('utf-8')
                
            path = path.rstrip('/')
            snapshot = self.snapshots[path]

            current = {}
            try:
                for name in os.listdir(path):
                    try:
                        current[name] = os.lstat(os.path.join(path, name))
                    except OSError:
                        pass
            except OSError:
                # recursive delete causes problems with path being non-existent
                pass

            observed = set(current)

            for name, snap_stat in snapshot.items():
                filename = os.path.join(path, name)

                if name in observed:
                    stat = current[name]
                    if stat.st_mtime > snap_stat.st_mtime:
                        events.append(FileEvent(IN_MODIFY, None, filename))
                    elif stat.st_ctime > snap_stat.st_ctime:
                        events.append(FileEvent(IN_ATTRIB, None, filename))
                    observed.discard(name)
                else:
                    event = FileEvent(IN_DELETE, None, filename)
                    deleted[snap_stat.st_ino] = event
                    events.append(event)

            for name in observed:
                stat = current[name]
                filename = os.path.join(path, name)

                event = deleted.get(stat.st_ino)
                if event is not None:
                    self.cookie += 1
                    event.mask = IN_MOVED_FROM
                    event.cookie = self.cookie
                    event = FileEvent(IN_MOVED_TO, self.cookie, filename)
                else:
                    event = FileEvent(IN_CREATE, None, filename)

                if os.path.isdir(filename):
                    self.snapshot(filename)

                events.append(event)

            snapshot.clear()
            snapshot.update(current)

        for event in events:
            self.callback(event)

    def snapshot(self, path):
        path = os.path.realpath(path)
        refs = self.snapshots

        for root, dirs, files in os.walk(path):
            refs[root] = {}
            entry = refs[root]
            for obj in files + dirs:
                try:
                    entry[obj] = os.lstat(os.path.join(root, obj))
                except OSError:
                    continue

########NEW FILE########
__FILENAME__ = tests
import unittest

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = self._make_tempdir()

    def tearDown(self):
        import os
        os.rmdir(self.tempdir)

    def _make_temporary(self, directory=None):
        import os
        import tempfile
        if directory is None:
            directory = self.tempdir
        f = tempfile.NamedTemporaryFile(dir=directory)
        f.flush()
        path = os.path.realpath(os.path.dirname(f.name)).rstrip('/') + '/'
        return f, path

    def _make_tempdir(self):
        import os
        import tempfile
        tempdir = tempfile.gettempdir()
        f = tempfile.NamedTemporaryFile(dir=tempdir)
        tempdir = os.path.join(tempdir, os.path.basename(f.name))
        f.close()
        os.mkdir(tempdir)
        return tempdir

class PathObservationTestCase(BaseTestCase):
    @property
    def modified_mask(self):
        import fsevents
        return (
            fsevents.FS_ITEMCREATED + 
            fsevents.FS_ITEMMODIFIED +
            fsevents.FS_ITEMISFILE
        )
    @property
    def create_and_remove_mask(self):
        import fsevents
        return (
            fsevents.FS_ITEMCREATED + 
            fsevents.FS_ITEMREMOVED + 
            fsevents.FS_ITEMISFILE
        )
        
    def test_single_file_added(self):
        events = []
        def callback(*args):
            events.append(args)

        f, path = self._make_temporary()
        from fsevents import Stream
        stream = Stream(callback, path)

        from fsevents import Observer
        observer = Observer()
        observer.schedule(stream)
        observer.start()

        # add single file
        import time
        while not observer.isAlive():
            time.sleep(0.1)
        del events[:]
        f.close()
        time.sleep(1.1)

        # stop and join observer
        observer.stop()
        observer.unschedule(stream)
        observer.join()

        self.assertEqual(events, [(path, self.create_and_remove_mask)])

    def test_multiple_files_added(self):
        events = []
        def callback(*args):
            events.append(args)

        from fsevents import Observer
        observer = Observer()
        from fsevents import Stream
        observer.start()

        # wait until activation
        import time
        while not observer.isAlive():
            time.sleep(0.1)
        time.sleep(0.1)

        # two files in same directory
        import os
        path1 = os.path.realpath(self._make_tempdir()) + '/'
        f = self._make_temporary(path1)[0]
        g = self._make_temporary(path1)[0]

        # one file in a separate directory
        path2 = os.path.realpath(self._make_tempdir()) + '/'
        h = self._make_temporary(path2)[0]

        stream = Stream(callback, path1, path2)
        observer.schedule(stream)

        try:
            del events[:]
            f.close()
            g.close()
            h.close()
            time.sleep(0.2)
            self.assertEqual(sorted(events), sorted([(path1, self.create_and_remove_mask), (path2, self.create_and_remove_mask)]))
        finally:
            f.close()
            g.close()
            h.close()
            os.rmdir(path1)
            os.rmdir(path2)

            # stop and join observer
            observer.stop()
            observer.unschedule(stream)
            observer.join()

    def test_single_file_added_multiple_streams(self):
        events = []
        def callback(*args):
            events.append(args)

        f, path = self._make_temporary()
        from fsevents import Stream
        stream1 = Stream(callback, path)
        stream2 = Stream(callback, path)

        from fsevents import Observer
        observer = Observer()
        observer.schedule(stream1)
        observer.schedule(stream2)
        observer.start()

        # add single file
        import time
        while not observer.isAlive():
            time.sleep(0.1)
        time.sleep(0.1)
        del events[:]
        f.close()
        time.sleep(0.2)

        # stop and join observer
        observer.stop()
        observer.unschedule(stream1)
        observer.unschedule(stream2)
        observer.join()

        self.assertEqual(events, [(path, self.create_and_remove_mask), (path, self.create_and_remove_mask)])

    def test_single_file_added_with_observer_unscheduled(self):
        events = []
        def callback(*args):
            events.append(args)

        f, path = self._make_temporary()
        from fsevents import Stream
        stream = Stream(callback, path)

        from fsevents import Observer
        observer = Observer()
        observer.start()
        import time
        while not observer.isAlive():
            time.sleep(0.1)

        observer.schedule(stream)
        observer.unschedule(stream)

        # add single file
        del events[:]
        f.close()
        time.sleep(0.1)

        # stop and join observer
        observer.stop()
        observer.join()

        self.assertEqual(events, [])

    def test_single_file_added_with_observer_rescheduled(self):
        events = []
        def callback(*args):
            events.append(args)

        f, path = self._make_temporary()
        from fsevents import Stream
        stream = Stream(callback, path)

        from fsevents import Observer
        observer = Observer()
        observer.start()

        import time
        while not observer.isAlive():
            time.sleep(0.1)

        observer.schedule(stream)
        observer.unschedule(stream)
        observer.schedule(stream)

        # add single file
        del events[:]
        f.close()
        time.sleep(0.2)

        # stop and join observer
        observer.stop()
        observer.join()

        self.assertEqual(events, [(path, self.create_and_remove_mask)])

    def test_single_file_added_to_subdirectory(self):
        events = []
        def callback(*args):
            events.append(args)

        import os
        directory = self._make_tempdir()
        subdirectory = os.path.realpath(os.path.join(directory, 'subdir')) + '/'
        os.mkdir(subdirectory)
        import time
        time.sleep(0.1)

        try:
            from fsevents import Stream
            stream = Stream(callback, directory)

            from fsevents import Observer
            observer = Observer()
            observer.schedule(stream)
            observer.start()

            # add single file
            while not observer.isAlive():
                time.sleep(0.1)
            del events[:]
            f = open(os.path.join(subdirectory, "test"), "w")
            f.write("abc")
            f.close()
            time.sleep(0.2)

            # stop and join observer
            observer.stop()
            observer.unschedule(stream)
            observer.join()

            self.assertEqual(len(events), 1)
            self.assertEqual(events, [(subdirectory, self.modified_mask)])
        finally:
            os.unlink(f.name)
            os.rmdir(subdirectory)
            os.rmdir(directory)

    def test_single_file_added_unschedule_then_stop(self):
        events = []
        def callback(*args):
            events.append(args)

        f, path = self._make_temporary()
        from fsevents import Stream
        stream = Stream(callback, path)

        from fsevents import Observer
        observer = Observer()
        observer.schedule(stream)
        observer.start()

        # add single file
        import time
        while not observer.isAlive():
            time.sleep(0.1)
        del events[:]
        f.close()
        time.sleep(0.2)

        # stop and join observer
        observer.unschedule(stream)
        observer.stop()
        observer.join()

        self.assertEqual(events, [(path, self.create_and_remove_mask)])

    def test_start_then_watch(self):
        events = []
        def callback(*args):
            events.append(args)

        f, path = self._make_temporary()
        from fsevents import Stream
        stream = Stream(callback, path)

        from fsevents import Observer
        observer = Observer()
        observer.schedule(stream)
        observer.start()

        # add single file
        import time
        while not observer.isAlive():
            time.sleep(0.1)
        del events[:]
        f.close()
        time.sleep(0.2)

        # stop and join observer
        observer.stop()
        observer.unschedule(stream)
        observer.join()

        self.assertEqual(events, [(path, self.create_and_remove_mask)])

    def test_start_no_watch(self):
        events = []
        def callback(*args):
            events.append(args)

        from fsevents import Observer
        observer = Observer()

        f, path = self._make_temporary()
        observer.start()

        # add single file
        import time
        while not observer.isAlive():
            time.sleep(0.1)
        del events[:]
        f.close()
        time.sleep(0.2)

        # stop and join observer
        observer.stop()
        observer.join()

        self.assertEqual(events, [])

class FileObservationTestCase(BaseTestCase):
    def test_single_file_created(self):
        events = []
        def callback(event):
            events.append(event)

        from fsevents import Stream
        stream = Stream(callback, self.tempdir, file_events=True)

        from fsevents import Observer
        observer = Observer()
        observer.schedule(stream)
        observer.start()

        # add single file
        import time
        while not observer.isAlive():
            time.sleep(0.1)
        del events[:]
        time.sleep(0.1)
        import os
        f = open(os.path.join(self.tempdir, "test"), "w")
        f.write("abc")
        f.flush()
        f.close()
        time.sleep(0.1)

        # stop and join observer
        observer.stop()
        observer.unschedule(stream)
        observer.join()

        os.unlink(f.name)
        from fsevents import IN_CREATE
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].mask, IN_CREATE)
        self.assertEqual(events[0].name, os.path.realpath(f.name))

    def test_single_file_deleted(self):
        events = []
        def callback(event):
            events.append(event)

        import os
        f = open(os.path.join(self.tempdir, "test"), "w")
        f.write("abc")
        f.flush()
        f.close()
        from fsevents import Stream
        stream = Stream(callback, self.tempdir, file_events=True)

        from fsevents import Observer
        observer = Observer()
        observer.schedule(stream)
        observer.start()

        # add single file
        import time
        while not observer.isAlive():
            time.sleep(0.1)
        del events[:]
        time.sleep(2.1)
        os.unlink(f.name)
        time.sleep(0.1)

        # stop and join observer
        observer.stop()
        observer.unschedule(stream)
        observer.join()

        from fsevents import IN_DELETE
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].mask, IN_DELETE)
        self.assertEqual(events[0].name, os.path.realpath(f.name))

    def test_single_file_moved(self):
        events = []
        def callback(event):
            events.append(event)

        import os
        f = open(os.path.join(self.tempdir, "test"), "w")
        f.write("abc")
        f.flush()
        f.close()
        from fsevents import Stream
        stream = Stream(callback, self.tempdir, file_events=True)

        from fsevents import Observer
        observer = Observer()
        observer.schedule(stream)
        observer.start()

        # add single file
        import time
        while not observer.isAlive():
            time.sleep(0.1)
        del events[:]
        time.sleep(2.1)
        new = "%s.new" % f.name
        os.rename(f.name, new)
        time.sleep(0.1)

        # stop and join observer
        observer.stop()
        observer.unschedule(stream)
        observer.join()

        os.unlink(new)
        from fsevents import IN_MOVED_FROM
        from fsevents import IN_MOVED_TO
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].mask, IN_MOVED_FROM)
        self.assertEqual(events[0].name, os.path.realpath(f.name))
        self.assertEqual(events[1].mask, IN_MOVED_TO)
        self.assertEqual(events[1].name, os.path.realpath(new))
        self.assertEqual(events[0].cookie, events[1].cookie)

    def test_single_file_modified(self):
        events = []
        def callback(event):
            events.append(event)

        import os
        f = open(os.path.join(self.tempdir, "test"), "w")
        f.write("abc")
        f.flush()
        from fsevents import Stream
        stream = Stream(callback, self.tempdir, file_events=True)

        from fsevents import Observer
        observer = Observer()
        observer.schedule(stream)
        observer.start()

        # add single file
        import time
        while not observer.isAlive():
            time.sleep(0.1)
        del events[:]
        time.sleep(2.1)
        f.write("abc")
        f.flush()
        f.close()
        time.sleep(0.1)

        # stop and join observer
        observer.stop()
        observer.unschedule(stream)
        observer.join()

        os.unlink(f.name)
        from fsevents import IN_MODIFY
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].mask, IN_MODIFY)
        self.assertEqual(events[0].name, os.path.realpath(f.name))

    def test_single_file_created_and_modified(self):
        events = []
        def callback(event):
            events.append(event)

        from fsevents import Stream
        stream = Stream(callback, self.tempdir, file_events=True)

        from fsevents import Observer
        observer = Observer()
        observer.schedule(stream)
        observer.start()

        # add single file
        import time
        while not observer.isAlive():
            time.sleep(0.1)
        del events[:]
        time.sleep(2.1)

        import os
        f = open(os.path.join(self.tempdir, "test"), "w")
        f.write("abc")
        f.flush()

        time.sleep(1.0)

        f.write("def")
        f.flush()
        f.close()
        time.sleep(0.1)

        # stop and join observer
        observer.stop()
        observer.unschedule(stream)
        observer.join()

        os.unlink(f.name)
        from fsevents import IN_CREATE, IN_MODIFY
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].mask, IN_CREATE)
        self.assertEqual(events[0].name, os.path.realpath(f.name))
        self.assertEqual(events[1].mask, IN_MODIFY)
        self.assertEqual(events[1].name, os.path.realpath(f.name))

    def test_single_directory_deleted(self):
        events = []
        def callback(event):
            events.append(event)

        import os
        new1 = os.path.join(self.tempdir, "newdir1")
        new2 = os.path.join(self.tempdir, "newdir2")
        try:
            os.mkdir(new1)
            os.mkdir(new2)
            import time
            time.sleep(0.2)
            from fsevents import Stream
            stream = Stream(callback, self.tempdir, file_events=True)

            from fsevents import Observer
            observer = Observer()
            observer.schedule(stream)
            observer.start()

            # add single file
            import time
            while not observer.isAlive():
                time.sleep(0.1)
            del events[:]
            time.sleep(0.1)
            os.rmdir(new2)
            time.sleep(1.0)

            # stop and join observer
            observer.stop()
            observer.unschedule(stream)
            observer.join()

            from fsevents import IN_DELETE
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].mask, IN_DELETE)
            self.assertEqual(events[0].name, os.path.realpath(new2))
        finally:
            os.rmdir(new1)

    def test_existing_directories_are_not_reported(self):
        import os
        from fsevents import Stream, Observer

        events = []
        def callback(event):
            events.append(event)
        
        stream = Stream(callback, self.tempdir, file_events=True)
        new1 = os.path.join(self.tempdir, "newdir1")
        new2 = os.path.join(self.tempdir, "newdir2")
        os.mkdir(new1)
        observer = Observer()
        observer.schedule(stream)
        observer.start()

        import time
        while not observer.isAlive():
            time.sleep(0.1)
        del events[:]
        time.sleep(1)
        os.mkdir(new2)
        try:
            time.sleep(1.1)
            observer.stop()
            observer.unschedule(stream)
            observer.join()

            from fsevents import IN_CREATE
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].mask, IN_CREATE)
            self.assertEqual(events[0].name, os.path.realpath(new2))
        finally:
            os.rmdir(new1)
            os.rmdir(new2)

########NEW FILE########
