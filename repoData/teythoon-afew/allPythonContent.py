__FILENAME__ = commands
#!/usr/bin/env python
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import glob
import sys
import time
import logging
import optparse

from afew.Database import Database
from afew.main import main as inner_main
from afew.utils import filter_compat
from afew.FilterRegistry import all_filters
from afew.Settings import user_config_dir, get_filter_chain
from afew.Settings import get_mail_move_rules, get_mail_move_age
from afew.NotmuchSettings import read_notmuch_settings, get_notmuch_new_query

option_parser = optparse.OptionParser(
    usage='%prog [options] [--] [query]'
)

# the actions
action_group = optparse.OptionGroup(
    option_parser,
    'Actions',
    'Please specify exactly one action (both update actions can be specified simultaneously).'
)
action_group.add_option(
    '-t', '--tag', default=False, action='store_true',
    help='run the tag filters'
)
action_group.add_option(
    '-w', '--watch', default=False, action='store_true',
    help='continuously monitor the mailbox for new files'
)
action_group.add_option(
    '-l', '--learn', default=False,
    help='train the category with the messages matching the given query'
)
action_group.add_option(
    '-u', '--update', default=False, action='store_true',
    help='update the categories [requires no query]'
)
action_group.add_option(
    '-U', '--update-reference', default=False, action='store_true',
    help='update the reference category (takes quite some time) [requires no query]'
)
action_group.add_option(
    '-c', '--classify', default=False, action='store_true',
    help='classify each message matching the given query (to test the trained categories)'
)
action_group.add_option(
    '-m', '--move-mails', default=False, action='store_true',
    help='move mail files between maildir folders'
)
option_parser.add_option_group(action_group)

# query modifiers
query_modifier_group = optparse.OptionGroup(
    option_parser,
    'Query modifiers',
    'Please specify either --all or --new or a query string.'
    ' The default query for the update actions is a random selection of'
    ' REFERENCE_SET_SIZE mails from the last REFERENCE_SET_TIMEFRAME days.'
)
query_modifier_group.add_option(
    '-a', '--all', default=False, action='store_true',
    help='operate on all messages'
)
query_modifier_group.add_option(
    '-n', '--new', default=False, action='store_true',
    help='operate on all new messages'
)
option_parser.add_option_group(query_modifier_group)

# general options
options_group = optparse.OptionGroup(
    option_parser,
    'General options',
)
# TODO: get config via notmuch api
options_group.add_option(
    '-C', '--notmuch-config', default=None,
    help='path to the notmuch configuration file [default: $NOTMUCH_CONFIG or ~/.notmuch-config]'
)
options_group.add_option(
    '-e', '--enable-filters',
    help="filter classes to use, separated by ',' [default: filters specified in afew's config]"
)
options_group.add_option(
    '-d', '--dry-run', default=False, action='store_true',
    help="don't change the db [default: %default]"
)
options_group.add_option(
    '-R', '--reference-set-size', default=1000,
    help='size of the reference set [default: %default]'
)

options_group.add_option(
    '-T', '--reference-set-timeframe', default=30, metavar='DAYS',
    help='do not use mails older than DAYS days [default: %default]'
)

options_group.add_option(
    '-v', '--verbose', dest='verbosity', action='count', default=0,
    help='be more verbose, can be given multiple times'
)
option_parser.add_option_group(options_group)


def main():
    options, args = option_parser.parse_args()

    no_actions = len(filter_compat(None, (
        options.tag,
        options.watch,
        options.update or options.update_reference,
        options.learn,
        options.classify,
        options.move_mails
    )))
    if no_actions == 0:
        sys.exit('You need to specify an action')
    elif no_actions > 1:
        sys.exit(
            'Please specify exactly one action (both update actions can be given at once)')

    no_query_modifiers = len(filter_compat(None, (options.all,
                                                  options.new, args)))
    if no_query_modifiers == 0 and not \
       (options.update or options.update_reference or options.watch) and not \
       options.move_mails:
        sys.exit('You need to specify one of --new, --all or a query string')
    elif no_query_modifiers > 1:
        sys.exit('Please specify either --all, --new or a query string')

    read_notmuch_settings(options.notmuch_config)

    if options.new:
        query_string = get_notmuch_new_query()
    elif options.all:
        query_string = ''
    elif not (options.update or options.update_reference):
        query_string = ' '.join(args)
    elif options.update or options.update_reference:
        query_string = '%i..%i' % (
            time.time() - options.reference_set_timeframe * 24 * 60 * 60,
            time.time())
    else:
        sys.exit('Weird... please file a bug containing your command line.')

    loglevel = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }[min(2, options.verbosity)]
    logging.basicConfig(level=loglevel)

    sys.path.insert(0, user_config_dir)
    # py2.7 compat hack
    glob_pattern = b'*.py' if sys.version_info[0] == 2 else '*.py'
    for file_name in glob.glob1(user_config_dir,  glob_pattern):
        print('Importing user filter %r' % (file_name, ))
        __import__(file_name[:-3], level=0)

    if options.move_mails:
        options.mail_move_rules = get_mail_move_rules()
        options.mail_move_age = get_mail_move_age()

    with Database() as database:
        configured_filter_chain = get_filter_chain(database)
        if options.enable_filters:
            options.enable_filters = options.enable_filters.split(',')

            all_filters_set = set(all_filters.keys())
            enabled_filters_set = set(options.enable_filters)
            if not all_filters_set.issuperset(enabled_filters_set):
                sys.exit('Unknown filter(s) selected: %s' % (' '.join(
                    enabled_filters_set.difference(all_filters_set))))

            options.enable_filters = [all_filters[
                filter_name]() for filter_name in options.enable_filters]
        else:
            options.enable_filters = configured_filter_chain

        inner_main(options, database, query_string)

########NEW FILE########
__FILENAME__ = configparser
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

try:
    # py3k
    import configparser
except ImportError:
    import ConfigParser as configparser

class GetListMixIn(object):
    def get_list(self, section, key, delimiter = ';',
                 filter_ = lambda value: value.strip(),
                 include_falsish = False):
        result = (filter_(value)
                  for value in self.get(section, key).split(delimiter))

        if include_falsish:
            return result
        else:
            return filter(None, result)

class SafeConfigParser(configparser.SafeConfigParser, GetListMixIn): pass
class RawConfigParser(configparser.RawConfigParser, GetListMixIn): pass

########NEW FILE########
__FILENAME__ = Database
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import time
import logging

import notmuch

from .NotmuchSettings import notmuch_settings, get_notmuch_new_tags
from .utils import extract_mail_body

class Database(object):
    '''
    Convenience wrapper around `notmuch`.
    '''

    def __init__(self):
        self.db_path = notmuch_settings.get('database', 'path')
        self.handle = None

    def __enter__(self):
        '''
        Implements the context manager protocol.
        '''
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        '''
        Implements the context manager protocol.
        '''
        self.close()

    def open(self, rw=False, retry_for=180, retry_delay=1):
        if rw:
            if self.handle and self.handle.mode == notmuch.Database.MODE.READ_WRITE:
                return self.handle

            start_time = time.time()
            while True:
                try:
                    self.handle = notmuch.Database(self.db_path,
                                                   mode = notmuch.Database.MODE.READ_WRITE)
                    break
                except notmuch.NotmuchError:
                    time_left = int(retry_for - (time.time() - start_time))

                    if time_left <= 0:
                        raise

                    if time_left % 15 == 0:
                        logging.debug('Opening the database failed. Will keep trying for another {} seconds'.format(time_left))

                    time.sleep(retry_delay)
        else:
            if not self.handle:
                self.handle = notmuch.Database(self.db_path)

        return self.handle

    def close(self):
        '''
        Closes the notmuch database if it has been opened.
        '''
        if self.handle:
            self.handle.close()
            self.handle = None

    def do_query(self, query):
        '''
        Executes a notmuch query.

        :param query: the query to execute
        :type  query: str
        :returns: the query result
        :rtype:   :class:`notmuch.Query`
        '''
        logging.debug('Executing query %r' % query)
        return notmuch.Query(self.open(), query)

    def get_messages(self, query, full_thread = False):
        '''
        Get all messages mathing the given query.

        :param query: the query to execute using :func:`Database.do_query`
        :type  query: str
        :param full_thread: return all messages from mathing threads
        :type  full_thread: bool
        :returns: an iterator over :class:`notmuch.Message` objects
        '''
        if not full_thread:
            for message in self.do_query(query).search_messages():
                yield message
        else:
            for thread in self.do_query(query).search_threads():
                for message in self.walk_thread(thread):
                    yield message


    def mail_bodies_matching(self, *args, **kwargs):
        '''
        Filters each message yielded from
        :func:`Database.get_messages` through
        :func:`afew.utils.extract_mail_body`.

        This functions accepts the same arguments as
        :func:`Database.get_messages`.

        :returns: an iterator over :class:`list` of :class:`str`
        '''
        query = self.get_messages(*args, **kwargs)
        for message in query:
            yield extract_mail_body(message)

    def walk_replies(self, message):
        '''
        Returns all replies to the given message.

        :param message: the message to start from
        :type  message: :class:`notmuch.Message`
        :returns: an iterator over :class:`notmuch.Message` objects
        '''
        yield message

        # TODO: bindings are *very* unpythonic here... iterator *or* None
        #       is a nono
        replies = message.get_replies()
        if replies != None:
            for message in replies:
                # TODO: yield from
                for message in self.walk_replies(message):
                    yield message

    def walk_thread(self, thread):
        '''
        Returns all messages in the given thread.

        :param message: the tread you are interested in
        :type  message: :class:`notmuch.Thread`
        :returns: an iterator over :class:`notmuch.Message` objects
        '''
        for message in thread.get_toplevel_messages():
            # TODO: yield from
            for message in self.walk_replies(message):
                yield message

    def add_message(self, path, sync_maildir_flags=False, new_mail_handler=None):
        '''
        Adds the given message to the notmuch index.

        :param path: path to the message
        :type  path: str
        :param sync_maildir_flags: if `True` notmuch converts the
                                   standard maildir flags to tags
        :type  sync_maildir_flags: bool
        :param new_mail_handler: callback for new messages
        :type  new_mail_handler: a function that is called with a
                                 :class:`notmuch.Message` object as
                                 its only argument
        :raises: :class:`notmuch.NotmuchError` if adding the message fails
        :returns: a :class:`notmuch.Message` object
        '''
        # TODO: it would be nice to update notmuchs directory index here
        message, status = self.open(rw=True).add_message(path, sync_maildir_flags=sync_maildir_flags)

        if status != notmuch.STATUS.DUPLICATE_MESSAGE_ID:
            logging.info('Found new mail in {}'.format(path))

            for tag in get_notmuch_new_tags():
                message.add_tag(tag)

            if new_mail_handler:
                new_mail_handler(message)

        return message

    def remove_message(self, path):
        '''
        Remove the given message from the notmuch index.

        :param path: path to the message
        :type  path: str
        '''
        self.open(rw=True).remove_message(path)

########NEW FILE########
__FILENAME__ = DBACL
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import os
import glob
import logging
import functools
import subprocess

class ClassificationError(Exception): pass
class BackendError(ClassificationError): pass

default_db_path = os.path.expanduser('~/.local/share/afew/categories')

class Classifier(object):
    reference_category = 'reference_category'

    def __init__(self, categories, database_directory = default_db_path):
        self.categories = set(categories)
        self.database_directory = database_directory

    def learn(self, category, texts):
        pass

    def classify(self, text):
        pass

class DBACL(Classifier):
    def __init__(self, database_directory = default_db_path):
        categories = glob.glob1(database_directory, '*')
        super(DBACL, self).__init__(categories, database_directory)

    sane_environ = {
        key: value
        for key, value in os.environ.items()
        if not (
            key.startswith('LC_') or
            key == 'LANG' or
            key == 'LANGUAGE'
        )
    }

    def _call_dbacl(self, args, **kwargs):
        command_line = ['dbacl', '-T', 'email'] + args
        logging.debug('executing %r' % command_line)
        return subprocess.Popen(
            command_line,
            shell = False,
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            env = self.sane_environ,
            **kwargs
        )

    def get_category_path(self, category):
        return os.path.join(self.database_directory, category.replace('/', '_'))

    def learn(self, category, texts):
        process = self._call_dbacl(['-l', self.get_category_path(category)])

        for text in texts:
            process.stdin.write((text + '\n').encode('utf-8'))

        process.stdin.close()
        process.wait()

        if process.returncode != 0:
            raise BackendError('dbacl learning failed:\n%s' % process.stderr.read())

    def classify(self, text):
        if not self.categories:
            raise ClassificationError('No categories defined')

        categories = functools.reduce(list.__add__, [
            ['-c', self.get_category_path(category)]
            for category in self.categories
        ], [])

        process = self._call_dbacl(categories + ['-n'])
        stdout, stderr = process.communicate(text.encode('utf-8'))

        if len(stderr) == 0:
            result = stdout.split()
            scores = list()
            while result:
                category = result.pop(0).decode('utf-8', 'replace')
                score = float(result.pop(0))
                scores.append((category, score))
            scores.sort(key = lambda category_score: category_score[1])
        else:
            raise BackendError('dbacl classification failed:\n%s' % stderr)

        return scores

########NEW FILE########
__FILENAME__ = files
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import os
import re
import stat
import logging
import platform
import threading

if platform.system() != 'Linux':
    raise ImportError('Unsupported platform: {!r}'.format(platform.system()))

try:
    # py3k
    import queue
except ImportError:
    import Queue as queue

import notmuch
import pyinotify

class EventHandler(pyinotify.ProcessEvent):
    def __init__(self, options, database):
        self.options = options
        self.database = database
        super(EventHandler, self).__init__()

    ignore_re = re.compile('(/xapian/.*(base.|tmp)$)|(\.lock$)|(/dovecot)')

    def process_IN_DELETE(self, event):
        if self.ignore_re.search(event.pathname):
            return

        logging.debug("Detected file removal: {!r}".format(event.pathname))
        self.database.remove_message(event.pathname)
        self.database.close()

    def process_IN_MOVED_TO(self, event):
        if self.ignore_re.search(event.pathname):
            return

        src_pathname = event.src_pathname if hasattr(event, 'src_pathname') else None
        logging.debug("Detected file rename: {!r} -> {!r}".format(src_pathname, event.pathname))

        def new_mail(message):
            for filter_ in self.options.enable_filters:
                try:
                    filter_.run('id:"{}"'.format(message.get_message_id()))
                    filter_.commit(self.options.dry_run)
                except Exception as e:
                    logging.warn('Error processing mail with filter {!r}: {}'.format(filter_.message, e))

        try:
            self.database.add_message(event.pathname,
                                      sync_maildir_flags=True,
                                      new_mail_handler=new_mail)
        except notmuch.FileError as e:
            logging.warn('Error opening mail file: {}'.format(e))
            return
        except notmuch.FileNotEmailError as e:
            logging.warn('File does not look like an email: {}'.format(e))
            return
        else:
            if src_pathname:
                self.database.remove_message(src_pathname)
        finally:
            self.database.close()

def watch_for_new_files(options, database, paths, daemonize=False):
    wm = pyinotify.WatchManager()
    mask = (
        pyinotify.IN_DELETE |
        pyinotify.IN_MOVED_FROM |
        pyinotify.IN_MOVED_TO)
    handler = EventHandler(options, database)
    notifier = pyinotify.Notifier(wm, handler)

    logging.debug('Registering inotify watch descriptors')
    wdds = dict()
    for path in paths:
        wdds[path] = wm.add_watch(path, mask)

    # TODO: honor daemonize
    logging.debug('Running mainloop')
    notifier.loop()

import ctypes
import contextlib

try:
    libc = ctypes.CDLL(ctypes.util.find_library("c"))
except ImportError as e:
    raise ImportError('Could not load libc: {}'.format(e))

class Libc(object):
    class c_dir(ctypes.Structure):
        pass
    c_dir_p = ctypes.POINTER(c_dir)

    opendir = libc.opendir
    opendir.argtypes = [ctypes.c_char_p]
    opendir.restype = c_dir_p

    closedir = libc.closedir
    closedir.argtypes = [c_dir_p]
    closedir.restype = ctypes.c_int

    @classmethod
    @contextlib.contextmanager
    def open_directory(cls, path):
        handle = cls.opendir(path)
        yield handle
        cls.closedir(handle)

    class c_dirent(ctypes.Structure):
        '''
        man 3 readdir says::

        On Linux, the dirent structure is defined as follows:

           struct dirent {
               ino_t          d_ino;       /* inode number */
               off_t          d_off;       /* offset to the next dirent */
               unsigned short d_reclen;    /* length of this record */
               unsigned char  d_type;      /* type of file; not supported
                                              by all file system types */
               char           d_name[256]; /* filename */
           };
        '''
        _fields_ = (
            ('d_ino', ctypes.c_long),
            ('d_off', ctypes.c_long),
            ('d_reclen', ctypes.c_ushort),
            ('d_type', ctypes.c_byte),
            ('d_name', ctypes.c_char * 4096),
        )
    c_dirent_p = ctypes.POINTER(c_dirent)

    readdir = libc.readdir
    readdir.argtypes = [c_dir_p]
    readdir.restype = c_dirent_p

    # magic value for directory
    DT_DIR = 4

blacklist = {'.', '..', 'tmp'}

def walk_linux(channel, path):
    channel.put(path)

    with Libc.open_directory(path) as handle:
        while True:
            dirent_p = Libc.readdir(handle)
            if not dirent_p:
                break

            if dirent_p.contents.d_type == Libc.DT_DIR and \
                    dirent_p.contents.d_name not in blacklist:
                walk_linux(channel, os.path.join(path, dirent_p.contents.d_name))

def walk(channel, path):
    channel.put(path)

    for child_path in (os.path.join(path, child)
                       for child in os.listdir(path)
                       if child not in blacklist):
        try:
            stat_result = os.stat(child_path)
        except:
            continue

        if stat_result.st_mode & stat.S_IFDIR:
            walk(channel, child_path)

def walker(channel, path):
    walk_linux(channel, path)
    channel.put(None)

def quick_find_dirs_hack(path):
    results = queue.Queue()

    walker_thread = threading.Thread(target=walker, args=(results, path))
    walker_thread.daemon = True
    walker_thread.start()

    while True:
        result = results.get()

        if result != None:
            yield result
        else:
            break

########NEW FILE########
__FILENAME__ = FilterRegistry
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import pkg_resources


RAISEIT = object()


class FilterRegistry(object):
    """
    The FilterRegistry is responsible for returning
    filters by key.
    Filters get registered via entry points.
    To avoid any circular dependencies, the registry loads
    the Filters lazily
    """
    def __init__(self, filters):
        self._filteriterator = filters

    @property
    def filter(self):
        if not hasattr(self, '_filter'):
            self._filter = {}
            for f in self._filteriterator:
                self._filter[f.name] = f.load()
        return self._filter

    def get(self, key, default=RAISEIT):
        if default == RAISEIT:
            return self.filter[key]
        else:
            return self.filter.get(key, default)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.filter[key] = value

    def __delitem__(self, key):
        del self.filter[key]

    def keys(self):
        return self.filter.keys()

    def values(self):
        return self.filter.values()

    def items(self):
        return self.filter.items()


all_filters = FilterRegistry(pkg_resources.iter_entry_points('afew.filter'))

def register_filter (klass):
    '''Decorator function for registering a class as a filter.'''

    all_filters[klass.__name__] = klass
    return klass


########NEW FILE########
__FILENAME__ = ArchiveSentMailsFilter
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

from ..filters.SentMailsFilter import SentMailsFilter
from ..NotmuchSettings import get_notmuch_new_tags

class ArchiveSentMailsFilter(SentMailsFilter):
    message = 'Archiving all mails sent by myself to others'

    def __init__(self, database, sent_tag=''):
        super(ArchiveSentMailsFilter, self).__init__(database, sent_tag)

    def handle_message(self, message):
        super(ArchiveSentMailsFilter, self).handle_message(message)
        self.remove_tags(message, *get_notmuch_new_tags())

########NEW FILE########
__FILENAME__ = BaseFilter
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import collections
import logging

import notmuch


class Filter(object):
    message = 'No message specified for filter'
    tags = []
    tags_blacklist = []

    def __init__(self, database, **kwargs):
        super(Filter, self).__init__()

        self.database = database
        if 'tags' not in kwargs:
            kwargs['tags'] = self.tags
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.flush_changes()
        self._tags_to_add = []
        self._tags_to_remove = []
        for tag_action in self.tags:
            if tag_action[0] not in '+-':
                raise ValueError('Each tag must be preceded by either + or -')

            (self._tags_to_add if tag_action[0] == '+' else self._tags_to_remove).append(tag_action[1:])

        self._tag_blacklist = set(self.tags_blacklist)

    def flush_changes(self):
        '''
        (Re)Initializes the data structures that hold the enqueued
        changes to the notmuch database.
        '''
        self._add_tags = collections.defaultdict(lambda: set())
        self._remove_tags = collections.defaultdict(lambda: set())
        self._flush_tags = []

    def run(self, query):
        logging.info(self.message)

        if getattr(self, 'query', None):
            if query:
                query = '(%s) AND (%s)' % (query, self.query)
            else:
                query = self.query

        for message in self.database.get_messages(query):
            self.handle_message(message)

    def handle_message(self, message):
        if not self._tag_blacklist.intersection(message.get_tags()):
            self.remove_tags(message, *self._tags_to_remove)
            self.add_tags(message, *self._tags_to_add)

    def add_tags(self, message, *tags):
        if tags:
            logging.debug('Adding tags %s to id:%s' % (', '.join(tags),
                                                       message.get_message_id()))
            self._add_tags[message.get_message_id()].update(tags)

    def remove_tags(self, message, *tags):
        if tags:
            logging.debug('Removing tags %s from id:%s' % (', '.join(tags),
                                                           message.get_message_id()))
            self._remove_tags[message.get_message_id()].update(tags)

    def flush_tags(self, message):
        logging.debug('Removing all tags from id:%s' %
                      message.get_message_id())
        self._flush_tags.append(message.get_message_id())

    def commit(self, dry_run=True):
        dirty_messages = set()
        dirty_messages.update(self._flush_tags)
        dirty_messages.update(self._add_tags.keys())
        dirty_messages.update(self._remove_tags.keys())

        if not dirty_messages:
            return

        if dry_run:
            logging.info('I would commit changes to %i messages' % len(dirty_messages))
        else:
            logging.info('Committing changes to %i messages' % len(dirty_messages))
            db = self.database.open(rw=True)

            for message_id in dirty_messages:
                messages = notmuch.Query(db, 'id:"%s"' % message_id).search_messages()

                for message in messages:
                    if message_id in self._flush_tags:
                        message.remove_all_tags()

                    for tag in self._add_tags.get(message_id, []):
                        message.add_tag(tag)

                    for tag in self._remove_tags.get(message_id, []):
                        message.remove_tag(tag)

        self.flush_changes()
########NEW FILE########
__FILENAME__ = ClassifyingFilter
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import logging

from ..DBACL import DBACL as Classifier, ClassificationError
from .BaseFilter import Filter
from ..utils import extract_mail_body

class ClassifyingFilter(Filter):
    message = 'Tagging via classification'
    def __init__(self, database, *args, **kwargs):
        super(ClassifyingFilter, self).__init__(database, *args, **kwargs)

        self.classifier = Classifier()

    def handle_message(self, message):
        try:
            scores = self.classifier.classify(extract_mail_body(message))
        except ClassificationError as e:
            logging.warning('Classification failed: {}'.format(e))
            return

        category = scores[0][0]

        if category != self.classifier.reference_category:
            self.add_tags(message, category)

########NEW FILE########
__FILENAME__ = FolderNameFilter
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) dtk <dtk@gmx.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

from .BaseFilter import Filter
from ..NotmuchSettings import notmuch_settings
import re
import logging
import shlex


class FolderNameFilter(Filter):
    message = 'Tags all new messages with their folder'

    def __init__(self, database, folder_blacklist='', folder_transforms='',
            maildir_separator='.', folder_explicit_list=''):
        super(FolderNameFilter, self).__init__(database)

        self.__filename_pattern = '{mail_root}/(?P<maildirs>.*)/(cur|new)/[^/]+'.format(
            mail_root=notmuch_settings.get('database', 'path').rstrip('/'))
        self.__folder_explicit_list = set(folder_explicit_list.split())
        self.__folder_blacklist = set(folder_blacklist.split())
        self.__folder_transforms = self.__parse_transforms(folder_transforms)
        self.__maildir_separator = maildir_separator


    def handle_message(self, message):
        maildirs = re.match(self.__filename_pattern, message.get_filename())
        if maildirs:
            folders = set(maildirs.group('maildirs').split(self.__maildir_separator))
            logging.debug('found folders {} for message {!r}'.format(
                folders, message.get_header('subject')))

            # remove blacklisted folders
            clean_folders = folders - self.__folder_blacklist
            if self.__folder_explicit_list:
                # only explicitly listed folders
                clean_folders &= self.__folder_explicit_list
            # apply transformations
            transformed_folders = self.__transform_folders(clean_folders)

            self.add_tags(message, *transformed_folders)


    def __transform_folders(self, folders):
        '''
        Transforms the given collection of folders according to the transformation rules.
        '''
        transformations = set()
        for folder in folders:
            if folder in self.__folder_transforms:
                transformations.add(self.__folder_transforms[folder])
            else:
                transformations.add(folder)
        return transformations


    def __parse_transforms(self, transformation_description):
        '''
        Parses the transformation rules specified in the config file.
        '''
        transformations = dict()
        for rule in shlex.split(transformation_description):
            folder, tag = rule.split(':')
            transformations[folder] = tag
        return transformations


########NEW FILE########
__FILENAME__ = HeaderMatchingFilter
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals
from .BaseFilter import Filter

import re


class HeaderMatchingFilter(Filter):
    message = 'Tagging based on specific header values matching a given RE'
    header = None
    pattern = None

    def __init__(self, database, **kwargs):
        super(HeaderMatchingFilter, self).__init__(database, **kwargs)
        if self.pattern is not None:
            self.pattern = re.compile(self.pattern, re.I)

    def handle_message(self, message):
        if self.header is not None and self.pattern is not None:
            if not self._tag_blacklist.intersection(message.get_tags()):
                value = message.get_header(self.header)
                match = self.pattern.search(value)
                if match:
                    sub = (lambda tag:
                        tag.format(**match.groupdict()).lower())
                    self.remove_tags(message, *map(sub, self._tags_to_remove))
                    self.add_tags(message, *map(sub, self._tags_to_add))

########NEW FILE########
__FILENAME__ = InboxFilter
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

from .BaseFilter import Filter
from ..NotmuchSettings import get_notmuch_new_tags, get_notmuch_new_query


class InboxFilter(Filter):
    message = 'Retags all messages not tagged as junk or killed as inbox'
    tags = ['+inbox']
    tags_blacklist = [ 'killed', 'spam' ]

    @property
    def query(self):
        '''
        Need to read the notmuch settings first. Using a property here
        so that the setting is looked up on demand.
        '''
        return get_notmuch_new_query()


    def handle_message(self, message):
        self.remove_tags(message, *get_notmuch_new_tags())
        super(InboxFilter, self).handle_message(message)

########NEW FILE########
__FILENAME__ = KillThreadsFilter
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

from .BaseFilter import Filter


class KillThreadsFilter(Filter):
    message = 'Looking for messages in killed threads that are not yet killed'
    query = 'NOT tag:killed'

    def handle_message(self, message):
        query = self.database.get_messages('thread:"%s" AND tag:killed' % message.get_thread_id())

        if len(list(query)):
            self.add_tags(message, 'killed')

########NEW FILE########
__FILENAME__ = ListMailsFilter
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

from .HeaderMatchingFilter import HeaderMatchingFilter


class ListMailsFilter(HeaderMatchingFilter):
    message = 'Tagging mailing list posts'
    query = 'NOT tag:lists'
    pattern = r"<(?P<list_id>[a-z0-9!#$%&'*+/=?^_`{|}~-]+)\."
    header = 'List-Id'
    tags = ['+lists', '+lists/{list_id}']


########NEW FILE########
__FILENAME__ = SentMailsFilter
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import re

from ..utils import filter_compat
from .BaseFilter import Filter
from ..NotmuchSettings import notmuch_settings


class SentMailsFilter(Filter):
    message = 'Tagging all mails sent by myself to others'
    _bare_email_re = re.compile(r"[^<]*<(?P<email>[^@<>]+@[^@<>]+)>")

    def __init__(self, database, sent_tag='', to_transforms=''):
        super(SentMailsFilter, self).__init__(database)

        my_addresses = set()
        my_addresses.add(notmuch_settings.get('user', 'primary_email'))
        if notmuch_settings.has_option('user', 'other_email'):
            my_addresses.update(filter_compat(None, notmuch_settings.get('user', 'other_email').split(';')))

        self.query = (
            '(' +
            ' OR '.join('from:"%s"' % address for address in my_addresses)
            + ') AND NOT (' +
            ' OR '.join('to:"%s"'   % address for address in my_addresses)
            + ')'
        )

        self.sent_tag = sent_tag
        self.to_transforms = to_transforms
        if to_transforms:
            self.__email_to_tags = self.__build_email_to_tags(to_transforms)


    def handle_message(self, message):
        if self.sent_tag:
            self.add_tags(message, self.sent_tag)
        if self.to_transforms:
            for header in ('To', 'Cc', 'Bcc'):
                email = self.__get_bare_email(message.get_header(header))
                for tag in self.__pick_tags(email):
                    self.add_tags(message, tag)
                else:
                    break


    def __build_email_to_tags(self, to_transforms):
        email_to_tags = dict()

        for rule in to_transforms.split():
            if ':' in rule:
                email, tags = rule.split(':')
                email_to_tags[email] = tuple(tags.split(';'))
            else:
                email = rule
                email_to_tags[email] = tuple()

        return email_to_tags


    def __get_bare_email(self, email):
        if not '<' in email:
            return email
        else:
            match = self._bare_email_re.search(email)
            return match.group('email')


    def __pick_tags(self, email):
        if email in self.__email_to_tags:
            tags = self.__email_to_tags[email]
            if tags:
                return tags
            else:
                user_part, domain_part = email.split('@')
                return (user_part, )

        return tuple()

########NEW FILE########
__FILENAME__ = SpamFilter
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

from .HeaderMatchingFilter import HeaderMatchingFilter


class SpamFilter(HeaderMatchingFilter):
    message = 'Tagging spam messages'
    header = 'X-Spam-Flag'
    pattern = 'YES'

    def __init__(self, database, tags='+spam', spam_tag=None, **kwargs):
        if spam_tag is not None:
            # this is for backward-compatibility
            tags = '+' + spam_tag
        kwargs['tags'] = [tags]
        super(SpamFilter, self).__init__(database, **kwargs)

########NEW FILE########
__FILENAME__ = MailMover
# coding=utf-8

#
# Copyright (c) dtk <dtk@gmx.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#


import notmuch
import logging
import os, shutil
from subprocess import check_call, CalledProcessError

from .Database import Database
from .utils import get_message_summary
from datetime import date, datetime, timedelta


class MailMover(Database):
    '''
    Move mail files matching a given notmuch query into a target maildir folder.
    '''


    def __init__(self, max_age=0, dry_run=False):
        super(MailMover, self).__init__()
        self.db = notmuch.Database(self.db_path)
        self.query = 'folder:{folder} AND {subquery}'
        if max_age:
            days = timedelta(int(max_age))
            start = date.today() - days
            now = datetime.now()
            self.query += ' AND {start}..{now}'.format(start=start.strftime('%s'),
                                                       now=now.strftime('%s'))
        self.dry_run = dry_run


    def move(self, maildir, rules):
        '''
        Move mails in folder maildir according to the given rules.
        '''
        # identify and move messages
        logging.info("checking mails in '{}'".format(maildir))
        to_delete_fnames = []
        for query in rules.keys():
            destination = '{}/{}/cur/'.format(self.db_path, rules[query])
            main_query = self.query.format(folder=maildir, subquery=query)
            logging.debug("query: {}".format(main_query))
            messages = notmuch.Query(self.db, main_query).search_messages()
            for message in messages:
                # a single message (identified by Message-ID) can be in several
                # places; only touch the one(s) that exists in this maildir 
                all_message_fnames = message.get_filenames()
                to_move_fnames = [name for name in all_message_fnames
                                  if maildir in name]
                if not to_move_fnames:
                    continue
                self.__log_move_action(message, maildir, rules[query],
                                       self.dry_run)
                for fname in to_move_fnames:
                    if self.dry_run:
                        continue
                    try:
                        shutil.copy2(fname, destination)
                        to_delete_fnames.append(fname)
                    except shutil.Error as e:
                        # this is ugly, but shutil does not provide more
                        # finely individuated errors
                        if str(e).endswith("already exists"):
                            continue
                        else:
                            raise

        # remove mail from source locations only after all copies are finished
        for fname in set(to_delete_fnames):
            os.remove(fname)

        # update notmuch database
        logging.info("updating database")
        if not self.dry_run:
            self.__update_db(maildir)
        else:
            logging.info("Would update database")


    #
    # private:
    #

    def __update_db(self, maildir):
        '''
        Update the database after mail files have been moved in the filesystem.
        '''
        try:
            check_call(['notmuch', 'new'])
        except CalledProcessError as err:
            logging.error("Could not update notmuch database " \
                          "after syncing maildir '{}': {}".format(maildir, err))
            raise SystemExit


    def __log_move_action(self, message, source, destination, dry_run):
        '''
        Report which mails have been identified for moving.
        '''
        if not dry_run:
            level = logging.DEBUG
            prefix = 'moving mail'
        else:
            level = logging.INFO
            prefix = 'I would move mail'
        logging.log(level, prefix)
        logging.log(level, "    {}".format(get_message_summary(message).encode('utf8')))
        logging.log(level, "from '{}' to '{}'".format(source, destination))
        #logging.debug("rule: '{}' in [{}]".format(tag, message.get_tags()))


########NEW FILE########
__FILENAME__ = main
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import random
import sys

from .DBACL import DBACL as Classifier
from .MailMover import MailMover
from .utils import extract_mail_body

try:
    from .files import watch_for_new_files, quick_find_dirs_hack
except ImportError:
    watch_available = False
else:
    watch_available = True


def main(options, database, query_string):
    if options.tag:
        for filter_ in options.enable_filters:
            filter_.run(query_string)
            filter_.commit(options.dry_run)
    elif options.watch:
        if not watch_available:
            sys.exit('Sorry, this feature requires Linux and pyinotify')
        watch_for_new_files(options, database,
                            quick_find_dirs_hack(database.db_path))
    elif options.learn is not False:
        classifier = Classifier()
        classifier.learn(
            options.learn,
            database.mail_bodies_matching(query_string)
        )
    elif options.update or options.update_reference:
        classifier = Classifier()
        if options.update:
            for category in (category
                             for category in classifier.categories
                             if category != classifier.reference_category):
                classifier.learn(
                    category,
                    database.mail_bodies_matching('tag:%s' % category)
                )

        if options.update_reference:
            all_messages = list(database.mail_bodies_matching(query_string))
            random.shuffle(all_messages)
            classifier.learn(
                classifier.reference_category,
                all_messages[:options.reference_set_size]
            )
    elif options.classify:
        classifier = Classifier()
        for message in database.get_messages(query_string):
            scores = classifier.classify(extract_mail_body(message))

            category = scores[0][0]

            if category == classifier.reference_category:
                category = 'no match'

            print('%s --> %s' % (message, category))
    elif options.move_mails:
        for maildir, rules in options.mail_move_rules.items():
            mover = MailMover(options.mail_move_age, options.dry_run)
            mover.move(maildir, rules)
            mover.close()
    else:
        sys.exit('Weird... please file a bug containing your command line.')

########NEW FILE########
__FILENAME__ = NotmuchSettings
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import os

from .configparser import RawConfigParser

notmuch_settings = RawConfigParser()

def read_notmuch_settings(path = None):
    if path == None:
        path = os.environ.get('NOTMUCH_CONFIG', os.path.expanduser('~/.notmuch-config'))

    notmuch_settings.readfp(open(path))

def get_notmuch_new_tags():
    return notmuch_settings.get_list('new', 'tags')

def get_notmuch_new_query():
    return '(%s)' % ' AND '.join('tag:%s' % tag for tag in get_notmuch_new_tags())

########NEW FILE########
__FILENAME__ = Settings
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import os
import re
import collections

from .configparser import SafeConfigParser
from afew.FilterRegistry import all_filters

user_config_dir = os.path.join(os.environ.get('XDG_CONFIG_HOME',
                                              os.path.expanduser('~/.config')),
                               'afew')

settings = SafeConfigParser()
# preserve the capitalization of the keys.
settings.optionxform = str

settings.readfp(open(os.path.join(os.path.dirname(__file__), 'defaults', 'afew.config')))
settings.read(os.path.join(user_config_dir, 'config'))

# All the values for keys listed here are interpreted as ;-delimited lists
value_is_a_list = ['tags', 'tags_blacklist']
mail_mover_section = 'MailMover'

section_re = re.compile(r'^(?P<name>[a-z_][a-z0-9_]*)(\((?P<parent_class>[a-z_][a-z0-9_]*)\)|\.(?P<index>\d+))?$', re.I)
def get_filter_chain(database):
    filter_chain = []

    for section in settings.sections():
        if section == 'global' or section == mail_mover_section:
            continue

        match = section_re.match(section)
        if not match:
            raise SyntaxError('Malformed section title %r.' % section)

        kwargs = dict(
            (key, settings.get(section, key))
            if key not in value_is_a_list else
            (key, settings.get_list(section, key))
            for key in settings.options(section)
        )

        if match.group('parent_class'):
            try:
                parent_class = all_filters[match.group('parent_class')]
            except KeyError:
                raise NameError('Parent class %r not found in filter type definition %r.' % (match.group('parent_class'), section))

            new_type = type(match.group('name'), (parent_class, ), kwargs)
            all_filters[match.group('name')] = new_type
        else:
            try:
                klass = all_filters[match.group('name')]
            except KeyError:
                raise NameError('Filter type %r not found.' % match.group('name'))
            filter_chain.append(klass(database, **kwargs))

    return filter_chain

def get_mail_move_rules():
    rule_pattern = re.compile(r"'(.+?)':(\S+)")
    if settings.has_option(mail_mover_section, 'folders'):
        all_rules = collections.OrderedDict()

        for folder in settings.get(mail_mover_section, 'folders').split():
            if settings.has_option(mail_mover_section, folder):
                rules = collections.OrderedDict()
                raw_rules = re.findall(rule_pattern,
                                       settings.get(mail_mover_section, folder))
                for rule in raw_rules:
                    rules[rule[0]] = rule[1]
                all_rules[folder] = rules
            else:
                raise NameError("No rules specified for maildir '{}'.".format(folder))

        return all_rules
    else:
        raise NameError("No folders defined to move mails from.")

def get_mail_move_age():
    max_age = 0
    if settings.has_option(mail_mover_section, 'max_age'):
        max_age = settings.get(mail_mover_section, 'max_age')
    return max_age


########NEW FILE########
__FILENAME__ = test_settings
import unittest


class TestFilterRegistry(unittest.TestCase):

    def test_all_filters_exist(self):
        from afew import FilterRegistry
        self.assertTrue(hasattr(FilterRegistry.all_filters, 'get'))

    def test_entry_point_registration(self):
        from afew import FilterRegistry

        class FakeRegistry(object):
            name = 'test'

            def load(self):
                return 'class'
        registry = FilterRegistry.FilterRegistry([FakeRegistry()])

        self.assertEquals('class', registry['test'])

    def test_all_builtin_FilterRegistrys_exist(self):
        from afew import FilterRegistry
        self.assertEquals(['FolderNameFilter',
                           'ArchiveSentMailsFilter',
                           'ClassifyingFilter',
                           'InboxFilter',
                           'SpamFilter',
                           'Filter',
                           'KillThreadsFilter',
                           'SentMailsFilter',
                           'HeaderMatchingFilter',
                           'ListMailsFilter'],
                          FilterRegistry.all_filters.keys())

    def test_add_FilterRegistry(self):
        from afew import FilterRegistry
        try:
            FilterRegistry.all_filters['test'] = 'class'
            self.assertEquals('class', FilterRegistry.all_filters['test'])
        finally:
            del FilterRegistry.all_filters['test']

########NEW FILE########
__FILENAME__ = utils
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

#
# Copyright (c) Justus Winter <4winter@informatik.uni-hamburg.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import codecs
import re
import sys
import email
from datetime import datetime

signature_line_re = re.compile(r'^((--)|(__)|(==)|(\*\*)|(##))')
def strip_signatures(lines, max_signature_size = 10):
    r'''
    Strip signatures from a mail. Used to filter mails before
    classifying mails.

    :param lines: a mail split at newlines
    :type  lines: :class:`list` of :class:`str`
    :param max_signature_size: consider message parts up to this size as signatures
    :type  max_signature_size: int
    :returns: the mail with signatures stripped off
    :rtype:   :class:`list` of :class:`str`

    >>> strip_signatures([
    ...     'Huhu',
    ...     '--',
    ...     'Ikke',
    ... ])
    ['Huhu']
    >>> strip_signatures([
    ...     'Huhu',
    ...     '--',
    ...     'Ikke',
    ...     '**',
    ...     "Sponsored by PowerDoh\'",
    ...     "Sponsored by PowerDoh\'",
    ...     "Sponsored by PowerDoh\'",
    ...     "Sponsored by PowerDoh\'",
    ...     "Sponsored by PowerDoh\'",
    ... ], 5)
    ['Huhu']
    '''

    siglines = 0
    sigline_count = 0

    for n, line in enumerate(reversed(lines)):
        if signature_line_re.match(line):
            # set the last line to include
            siglines = n + 1

            # reset the line code
            sigline_count = 0

        if sigline_count >= max_signature_size:
            break

        sigline_count += 1

    return lines[:-siglines]


def extract_mail_body(message):
    r'''
    Extract the plain text body of the message with signatures
    stripped off.

    :param message: the message to extract the body from
    :type  message: :class:`notmuch.Message`
    :returns: the extracted text body
    :rtype:   :class:`list` of :class:`str`
    '''
    if hasattr(email, 'message_from_binary_file'):
        mail = email.message_from_binary_file(open(message.get_filename(), 'br'))
    else:
        if (3, 1) <= sys.version_info < (3, 2):
            fp = codecs.open(message.get_filename(), 'r', 'utf-8', errors='replace')
        else:
            fp = open(message.get_filename())
        mail = email.message_from_file(fp)

    content = []
    for part in mail.walk():
        if part.get_content_type() == 'text/plain':
            raw_payload = part.get_payload(decode=True)
            encoding = part.get_content_charset()
            if encoding:
                try:
                    raw_payload = raw_payload.decode(encoding, 'replace')
                except LookupError:
                    raw_payload = raw_payload.decode(sys.getdefaultencoding(), 'replace')
            else:
                raw_payload = raw_payload.decode(sys.getdefaultencoding(), 'replace')

            lines = raw_payload.split('\n')
            lines = strip_signatures(lines)

            content.append('\n'.join(lines))
    return '\n'.join(content)

def filter_compat(*args):
    r'''
    Compatibility wrapper for filter builtin.

    The semantic of the filter builtin has been changed in
    python3.x. This is a temporary workaround to support both python
    versions in one code base.
    '''
    return list(filter(*args))

def get_message_summary(message):
    when = datetime.fromtimestamp(float(message.get_date()))
    sender = get_sender(message)
    subject = message.get_header('Subject')
    return '[{date}] {sender} | {subject}'.format(date=when, sender=sender,
                                                  subject=subject)

def get_sender(message):
    sender = message.get_header('From')
    name_match = re.search('(.+) <.+@.+\..+>', sender)
    if name_match:
        sender = name_match.group(1)
    return sender

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# afew documentation build configuration file, created by
# sphinx-quickstart on Fri Dec 23 21:19:37 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# Create mocks so we don't depend on non standard modules to build the
# documentation

class Mock(object):
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return Mock if name != '__file__' else '/dev/null'

MOCK_MODULES = [
    'notmuch',
    'notmuch.globals',
    'argparse',
]

for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = Mock()

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.coverage', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'afew'
copyright = u'2011, Justus Winter'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1pre'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'afewdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'afew.tex', u'afew Documentation',
   u'Justus Winter', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'afew', u'afew Documentation',
     [u'Justus Winter'], 1)
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('http://docs.python.org/3.2', None),
    'notmuch': ('http://packages.python.org/notmuch', None),
    'alot': ('http://alot.readthedocs.org/en/latest', None),
}

########NEW FILE########
