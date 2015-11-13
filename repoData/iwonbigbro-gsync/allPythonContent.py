__FILENAME__ = bind
#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""Module for providing a function paramater binding closure"""

class BindNoFuncError(Exception):
    pass

class bind(object):
    """Binds a function to a set of arguments and a defined context"""

    def __init__(self, func, context, *args):
        self.__f = func
        self.__c = context
        self.__a = args

    def __call__(self, *args):
        func, context = self.__f, self.__c
        xargs = () + self.__a + args

        if isinstance(func, str):
            func = context.__class__.__dict__.get(func, None)

        if not callable(func):
            raise BindNoFuncError

        if context:
            return func(context, *xargs)

        return func(*xargs)

########NEW FILE########
__FILENAME__ = crawler
#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""
Crawler module which provides the interface for crawling local and remote
file systems.
"""

import os, re, sys
from libgsync.sync import Sync
from libgsync.output import verbose, debug
from libgsync.options import GsyncOptions
from libgsync.drive import Drive
from libgsync.drive.mimetypes import MimeTypes
from libgsync.bind import bind


def os_walk_wrapper(path):
    """
    The os.walk function doesn't yield anything if passed a file.  This
    wrapper simply yields the file as if the directory had been provided
    as the path.
    """
    if os.path.isdir(path):
        for dirpath, dirs, files in os.walk(path):
            yield (dirpath, dirs, files)

    elif os.path.exists(path):
        dirpart, filepart = os.path.split(path)
        yield (dirpart, [], [filepart])


class Crawler(object):
    """
    Crawler class that defines an instance of a crawler that is bound to
    either a local or remote filesystem.
    """
    def __init__(self, src, dst):
        self._dev = None
        self._src = None
        self._dst = None
        self._sync = None
        
        force_dest_file = GsyncOptions.force_dest_file

        self._drive = Drive()

        if self._drive.is_drivepath(src):
            self._walk_callback = bind("walk", self._drive)
            self._src = self._drive.normpath(src)
            info = self._drive.stat(self._src)

            if info and info.mimeType != MimeTypes.FOLDER:
                debug("Source is not a directory, forcing dest file: %s" % (
                    repr(self._src)
                ))
                force_dest_file = True
        else:
            self._walk_callback = os_walk_wrapper
            self._src = os.path.normpath(src)
            st_info = os.stat(self._src)

            if os.path.isfile(self._src):
                debug("Source is not a directory, forcing dest file: %s" % (
                    repr(self._src)
                ))
                force_dest_file = True

            if GsyncOptions.one_file_system:
                self._dev = st_info.st_dev

        if self._drive.is_drivepath(dst):
            self._dst = self._drive.normpath(dst)
            info = self._drive.stat(self._dst)

            if info and info.mimeType == MimeTypes.FOLDER:
                debug("Dest is a directory, not forcing dest file: %s" % (
                    repr(self._dst)
                ))
                force_dest_file = False
        else:
            self._dst = os.path.normpath(dst)
            if os.path.isdir(self._dst):
                debug("Dest is a directory, not forcing dest file: %s" % (
                    repr(self._dst)
                ))
                force_dest_file = False

        if src[-1] == "/":
            self._src += "/"

        if dst[-1] == "/":
            self._dst += "/"
            debug("Dest has trailing slash, not forcing dest file: %s" % (
                self._dst
            ))
            force_dest_file = False

        # Only update if not already set.
        if GsyncOptions.force_dest_file is None:
            debug("force_dest_file = %s" % force_dest_file)
            GsyncOptions.force_dest_file = force_dest_file

        #super(Crawler, self).__init__(name = "Crawler: %s" % src)
    

    def _dev_check(self, device_id, path):
        """
        Checks if the path provided resides on the device specified by the
        device ID provided.

        @param {int} device_id    The device ID.
        @param {String} path      Path to verify.

        @return {bool} True if the path resides on device with the
                       specified ID.
        """
        if device_id is not None:
            st_info = os.stat(path)
            if st_info.st_dev != device_id:
                debug("Not on same device: %s" % repr(path))
                return False

        return True


    def _walk(self, path, generator, device_id):
        """
        Walks the path provided, calling the generator function on the path,
        which yields the subdirectories and files.  It then iterates these
        lists and calls the sync method '_sync'.

        @param {String} path          Path to walk.
        @param {Function} generator   Generator function to call on path.
        @param {int} device_id        Device ID for the path, None if device
                                      cannot be determined.
        """
        for dirpath, _, files in generator(path):
            debug("Walking: %s" % repr(dirpath))

            if not self._dev_check(device_id, dirpath):
                debug("Not on same device: %s" % repr(dirpath))
                continue

            if not GsyncOptions.force_dest_file:
                if GsyncOptions.dirs or GsyncOptions.recursive:

                    # Sync the directory but not its contents
                    debug("Synchronising directory: %s" % repr(dirpath))
                    self._sync(dirpath)
                else:
                    sys.stdout.write("skipping directory %s\n" % dirpath)
                    break

            for filename in files:
                absfile = os.path.join(dirpath, filename)
                if not self._dev_check(device_id, absfile):
                    continue
                    
                debug("Synchronising file: %s" % repr(absfile))
                self._sync(absfile)

            if not GsyncOptions.recursive:
                break


    def run(self):
        """
        Worker method called synchronously or as part of an asynchronous
        thread or subprocess.
        """
        srcpath = self._src
        basepath, path = os.path.split(srcpath)

        if self._drive.is_drivepath(self._src):
            basepath = self._drive.normpath(basepath)

        debug("Source srcpath: %s" % repr(srcpath))
        debug("Source basepath: %s" % repr(basepath))
        debug("Source path: %s" % repr(path))

        if GsyncOptions.relative:
            # Supports the foo/./bar notation in rsync.
            path = re.sub(r'^.*/\./', "", path)

        self._sync = Sync(basepath, self._dst)

        debug("Enumerating: %s" % repr(srcpath))

        try:
            self._walk(srcpath, self._walk_callback, self._dev)

        except KeyboardInterrupt, ex:
            print("\nInterrupted")
            raise

        except Exception, ex:
            debug.exception(ex)
            print("Error: %s" % repr(ex))

        finally:
            verbose("sent %d bytes  received %d bytes  %.2f bytes/sec" % (
                self._sync.total_bytes_sent,
                self._sync.total_bytes_received,
                self._sync.rate()
            ))


########NEW FILE########
__FILENAME__ = client_json
#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""Defines the client object to be used during authentication"""

# pylint: disable-msg=C0103

client_obj = {
    "installed": {
        "client_id": "542942405111.apps.googleusercontent.com",
        "client_secret": "Y4iSAluo7pCY57m8HFOfv2W_",
        "redirect_uris": [
            "http://localhost", "urn:ietf:oauth:2.0:oob"
        ],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://accounts.google.com/o/oauth2/token"
    }
}

########NEW FILE########
__FILENAME__ = file
#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2013 Craig Phillips.  All rights reserved.

"""Drive file objects"""

class DriveFile(dict):
    """
    Defines the DriveFile adapter that provides an interface to a
    drive file information dictionary.
    """
    __setattr__ = dict.__setitem__


    def __getattr__(self, key):
        return self.get(key)


    def __repr__(self):
        return "DriveFile(%s)" % self.items()

########NEW FILE########
__FILENAME__ = mimetypes
#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""
Defines the MimeTypes static class used for mimetype related file
operations and for defining simple Google Drive types.
"""

from __future__ import absolute_import

class MimeTypes(object):
    """The MimeTypes static API class"""

    NONE = "none/unknown-mimetype"
    FOLDER = "application/vnd.google-apps.folder"
    BINARY_FILE = "application/octet-stream"
    SYMLINK = "inode/symlink"

    @staticmethod
    def get(path):
        """
        Returns the mimetype of a file based on magic if the magic library
        is installed, otherwise uses the file extension method.
        """
        mimetype = None
        try:
            import magic
            mimetype = magic.from_file(path, mime=True)
        except Exception:
            import mimetypes
            mimetype = mimetypes.guess_type(path)[0]

        if mimetype is not None:
            return mimetype

        return MimeTypes.NONE

########NEW FILE########
__FILENAME__ = enum
#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

"""Create static enum objects"""


class Enum(object):
    """Enum class"""

    def __init__(self): # pragma: no cover
        raise TypeError

########NEW FILE########
__FILENAME__ = filter
#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013 Craig Phillips.  All rights reserved.

"""
Defines the filter feature of gsync, as specified by --filter like options.
"""

import re, fnmatch
from libgsync.output import debug

RULEMOD_PAIRS = [
    ("exclude", "-"),
    ("include", "+"),
    ("hide", "H"),
    ("show", "S"),
    ("protect", "P"),
    ("risk", "R"),
    ("dir-merge", ":"),
    ("merge", "."),
]
RULES = r"(%s)" % "|".join([ r for r, m in RULEMOD_PAIRS ])
MODIFIERS = r"([%s])" % "".join([ m for r, m in RULEMOD_PAIRS ])
EXPR_RULE_MOD_PATTERN = r"\s*%s,\s*%s\s*(\S+)" % (RULES, MODIFIERS)
EXPR_RULE_PATTERN = r"\s*%s\s*(\S+)" % (RULES)
EXPR_MOD_PATTERN = r"\s*,?\s*%s\s*(\S+)" % (MODIFIERS)
EXPR_LIST = (
    EXPR_RULE_MOD_PATTERN,
    EXPR_MOD_PATTERN,
    EXPR_RULE_PATTERN,
)


class FilterException(Exception):
    """For exceptions that occur relating to filters or filtering."""
    pass


class FilterObject(object):
    """Defines a singleton loadable filter definition."""

    def __init__(self):
        self.rules = []
        self.pathcache = {}
        self.merge_dir = ""
    
    def get_modifier(self, path):
        """Returns a rule modifier that matches the given path"""

        modifer = self.pathcache.get(path)
        if modifer is None:
            return modifer

        for modifer, pattern in self.rules:
            if fnmatch.fnmatch(path, pattern):
                return self.pathcache.setdefault(path, modifer)

        return None

    def load_rules(self, path, modifier=""):
        """Loads filter rules from the file specified by 'path'."""

        with open(path, "r") as fd:
            for line in fd:
                self.add_rule(modifier + " " + line)
                
    def add_rules(self, rules, modifier = ""):
        """
        Adds rules to the filter object, specified with 'rules' and an
        optional modifier, where rules do not contain modifiers.
        """
        for rule in rules:
            self.add_rule(modifier + " " + rule)

    def add_rule(self, rule_string):
        """
        Adds a single rule to the filter object.
        """
        match = None
        for expr in EXPR_LIST:
            match = re.match(expr, rule_string)
            if match is not None:
                break

        if match is None:
            return

        ngroups = len(match.groups())
        debug("%s matched %d groups" % (repr(rule_string), ngroups))
        debug(" * [%s]" % ",".join([
            x if x else "" for x in match.groups()
        ]))

        if ngroups == 3:
            mod, pattern = match.groups(2, 3)

        elif ngroups == 2:
            mod, pattern = match.groups(1, 2)
            mod = mod[0].upper()

            if mod == "I":
                mod = "+"
            elif mod == "E":
                mod = "-"
            elif mod == "D":
                mod = ":"
            elif mod == "M":
                mod = "."
        else:
            raise FilterException("Invalid rule: %s" % rule_string)

        if mod == ":":
            self.merge_dir = pattern
            return

        if mod == ".":
            # Stop and load some more rules.
            self.load_rules(pattern)
            return

        self.rules.append((mod, pattern))


Filter = FilterObject() # pylint: disable-msg=C0103

########NEW FILE########
__FILENAME__ = hashlib
#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

"""
A hashlib wrapper library to work around pylint errors generated by
hashlib's use of globals() to dynamically hoist openssl libraries into
its namespace.
"""

from __future__ import absolute_import

__all__ = ( "new" )

import hashlib

new = getattr(hashlib, "new", lambda x: None) # pylint: disable-msg=C0103

########NEW FILE########
__FILENAME__ = doc
#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013 Craig Phillips.  All rights reserved.

"""
gsync version %s

Copyright (C) 2013 Craig Phillips.  All rights reserved.

gsync comes with ABSOLUTELY NO WARRANTY.  This is free software, and you
are welcome to redistribute it under certain conditions.  See the BSD
Licence for details.

gsync is a file transfer program based on the rsync file transfer program.
The only functional difference is that gsync is intended to be used for
synchronising between a source directory and remote Google Drive directory.

Usage:
 gsync ( --authenticate [--debug] | [options]... <path> <path>... )

Arguments:
 <path>                      path to a local file, directory, remote file or 
                             remote directory.  The last argument in the list
                             of provided paths is considered the destination.
                             The destination must be specified along with at
                             least one source.  If a source or destination is
                             remote, then it must be specified in the form:

                                drive:///some/folder

                             any local file or directory can be specified by
                             absolute path or relative to the current working
                             directory.

Options:
     --authenticate          setup authentication with your Google Drive
 -v, --verbose               enable verbose output
     --debug                 enable debug output
 -q, --quiet                 suppress non-error messages
 -c, --checksum              skip based on checksum, not mod-time & size
 -r, --recursive             recurse into directories
 -R, --relative              use relative path names
     --no-implied-dirs       don't send implied dirs with --relative
 -b, --backup                make backups (see --suffix & --backup-dir)
     --backup-dir=DIR        make backups into hierarchy based in DIR
     --suffix=SUFFIX         set backup suffix (default ~ w/o --backup-dir)
 -u, --update                skip files that are newer on the receiver
     --append                append data onto shorter files
 -d, --dirs                  transfer directories without recursing
 -l, --links                 copy symlinks as symlinks
 -L, --copy-links            transform symlink into referent file/dir
     --copy-unsafe-links     only "unsafe" symlinks are transformed
     --safe-links            ignore symlinks that point outside the source tree
 -k, --copy-dirlinks         transform symlink to a dir into referent dir
 -K, --keep-dirlinks         treat symlinked dir on receiver as dir
 -H, --hard-links            preserve hard links
 -p, --perms                 preserve permissions
 -E, --executability         preserve the file's executability
     --chmod=CHMOD           affect file and/or directory permissions
 -o, --owner                 preserve owner (super-user only)
 -g, --group                 preserve group
 -t, --times                 preserve modification times
 -O, --omit-dir-times        omit directories from --times
     --super                 receiver attempts super-user activities
     --fake-super            store/recover privileged attrs using xattrs
 -S, --sparse                handle sparse files efficiently
 -n, --dry-run               perform a trial run with no changes made
 -x, --one-file-system       don't cross filesystem boundaries
     --existing              skip creating new files on receiver
     --ignore-existing       skip updating files that already exist on receiver
     --remove-source-files   sender removes synchronized files (non-dirs)
     --del                   an alias for --delete-during
     --delete                delete extraneous files from destination dirs
     --delete-before         receiver deletes before transfer, not during
     --delete-during         receiver deletes during the transfer
     --delete-delay          find deletions during, delete after
     --delete-after          receiver deletes after transfer, not during
     --delete-excluded       also delete excluded files from destination dirs
     --ignore-errors         delete even if there are I/O errors
     --force                 force deletion of directories even if not empty
     --max-delete=NUM        don't delete more than NUM files
     --max-size=SIZE         don't transfer any file larger than SIZE
     --min-size=SIZE         don't transfer any file smaller than SIZE
     --partial               keep partially transferred files
     --partial-dir=DIR       put a partially transferred file into DIR
     --delay-updates         put all updated files into place at transfer's end
 -m, --prune-empty-dirs      prune empty directory chains from the file-list
     --timeout=SECONDS       set I/O timeout in seconds
     --contimeout=SECONDS    set daemon connection timeout in seconds
 -I, --ignore-times          don't skip files that match in size and mod-time
     --size-only             skip files that match in size
     --modify-window=NUM     compare mod-times with reduced accuracy
 -T, --temp-dir=DIR          create temporary files in directory DIR
 -y, --fuzzy                 find similar file for basis if no dest file
     --compare-dest=DIR      also compare destination files relative to DIR
     --copy-dest=DIR         ... and include copies of unchanged files
 -C, --cvs-exclude           auto-ignore files the same way CVS does
 -fd, --filter=RULE           add a file-filtering RULE
 -F                          same as --filter='dir-merge /.rsync-filter'
                             repeated: --filter='- .rsync-filter'
     --exclude=PATTERN       exclude files matching PATTERN
     --exclude-from=FILE     read exclude patterns from FILE
     --include=PATTERN       don't exclude files matching PATTERN
     --include-from=FILE     read include patterns from FILE
     --files-from=FILE       read list of source-file names from FILE
 -0, --from0                 all *-from/filter files are delimited by 0s
 -s, --protect-args          no space-splitting; only wildcard special-chars
     --stats                 give some file-transfer stats
 -8, --8-bit-output          leave high-bit chars unescaped in output
 -h, --human-readable        output numbers in a human-readable format
     --progress              show progress during transfer
 -P                          same as --partial --progress
 -i, --itemize-changes       output a change-summary for all updates
     --out-format=FORMAT     output updates using the specified FORMAT
     --log-file=FILE         log what we're doing to the specified FILE
     --log-file-format=FMT   log updates using the specified FMT
     --list-only             list the files instead of copying them
     --bwlimit=KBPS          limit I/O bandwidth; KBytes per second
     --version               print version number
     --proxy                 use http_proxy or https_proxy environment
                             variables for web proxy configuration
 -h, --help                  show this help

See https://github.com/iwonbigbro/gsync for updates, bug reports and answers

Environment variables:

   The configuration directory defaults to $HOME/.gsync.  This path can be
   overridden by specifying the environment variable GSYNC_CONFIG_DIR.  Any
   configuration files will be loaded from this directory.

   Individual configuration files can also be overridden by substituting any
   non-alphanumeric character in the filename with an underscore and adding
   the GSYNC_ prefix.  For example, to override the client.json configuration
   file, specify an environment variable named GSYNC_CLIENT_JSON.
"""

########NEW FILE########
__FILENAME__ = output
#!/usr/bin/env python
# -*- coding: utf8 -*-
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""Defines output channels for gsync"""

import os, sys, inspect, re, codecs
from datetime import datetime

# Make stdout unbuffered.
sys.stdout = (codecs.getwriter(sys.stdout.encoding))\
    (os.fdopen(sys.stdout.fileno(), "w", 0), "replace")


class Channel(object):
    """Base channel class to define the interface"""

    _priority = -1 

    def enable(self):
        """Enables the channel."""

        if self._priority < 0:
            self._priority = 0
        self._priority += 1

    def disable(self): 
        """Disables the channel."""

        self._priority = -1

    def enabled(self):
        """Returns True if the channel is enabled."""

        return self._priority > 0

    def __call__(self, msg, priority=1):
        self.write(msg, priority)

    def write(self, msg, priority=1):
        """Writes messages to the buffer provided by this channel."""

        if self._priority >= priority:
            sys.stdout.write(u"%s\n" % unicode(msg))

class Debug(Channel):
    """
    Defines a debug channel for writing debugging information to stdout
    and stderr.
    """
    def write(self, msg, priority=1):
        if self._priority >= priority:
            stack = inspect.stack()
            indent = "".join([ " " for _ in range(len(stack) - 2) ])

            self._write_frame(stack[2], msg, indent)

    def _write_frame(self, frame, message=None, indent=""):
        """Writes a formatted stack frame to the channel buffer."""

        filename, lineno, function = frame[1:4]
        filename = re.sub(r'^.*libgsync/', "", filename)
        filename = re.sub(r'/__init__.py', "/", filename)
        if message is not None:
            super(Debug, self).write("DEBUG: %s%s:%d:%s(): %s" % (
                indent, filename, lineno, function, message
            ))
        else:
            super(Debug, self).write("DEBUG: %s%s:%d:%s()" % (
                indent, filename, lineno, function
            ))

    def stack(self):
        """Writes a stack trace to the channel buffer."""

        super(Debug, self).write("DEBUG: BEGIN STACK TRACE")

        stack = inspect.stack()[1:]
        for frame in stack:
            self._write_frame(frame, indent="    ")

        super(Debug, self).write("DEBUG: END STACK TRACE")

    def exception(self, ex = "Exception"):
        """Writes a formatted exception to the channel buffer."""

        if isinstance(ex, Exception):
            super(Debug, self).write("DEBUG: %s: %s" % (
                repr(ex), str(ex)
            ), -1)

        import traceback
        super(Debug, self).write("DEBUG: %s: %s" % (
            repr(ex), "".join(traceback.format_tb(sys.exc_info()[2]))
        ), -1)

    def function(self, func):
        """Provides function decoration debugging"""

        if self._priority < 1:
            return func

        def __function(*args, **kwargs):
            ret = func(*args, **kwargs)
            self.write("%s(%s, %s) = %s" % (
                func.__name__, repr(args), repr(kwargs), repr(ret)
            ))
            return ret

        return __function


class Verbose(Channel):
    """
    Defines a channel for writing verbose output to stdout and stderr.
    """
    pass


class Itemize(object):
    """
    Defines a channel for the output of the rsync style itemized change
    summary on stdout and stderr.
    """
    def __call__(self, changes, filename):
        sys.stdout.write(u"%11s %s\n" % \
            (unicode(changes[:11]), unicode(filename)))


class Progress(object):
    """
    Defines a non-singleton channel for writing file transfer progress
    output to stdout and stderr.
    """
    def __init__(self, enable_output = True, callback = None):
        self._callback = callback
        self._enable_output = enable_output
        self._start = datetime.now()

        self.bytes_written = 0L
        self.bytes_total = 0L
        self.percentage = 0
        self.time_taken = 0

        self.write()

    def write(self):
        """
        Writes the current state of the transfer to the output stream.
        """
        if self._enable_output:
            epoch = int(self.time_taken)
            secs = epoch % 60
            mins = int(epoch / 60) % 60
            hrs = int((epoch / 60) / 60) % 60

            sys.stdout.write(u"\r%12d %3d%% %11s %10s" % (
                self.bytes_written, self.percentage, unicode(self.rate()),
                u"%d:%02d:%02d" % (hrs, mins, secs)
            ))
        
    def __call__(self, status):
        self.time_taken = (datetime.now() - self._start).seconds
        self.bytes_written = long(status.resumable_progress)
        self.percentage = int(status.progress() * 100.0)
        self.bytes_total = status.total_size

        self.write()

        if self._callback is not None:
            self._callback(status)

    def rate(self):
        """
        Returns a string representing the bytes transferred against time
        taken, as a rate of units of bytes per second.
        """
        rate = float(self.bytes_written) / max(0.1, float(self.time_taken))

        for modifier in [ 'B', 'KB', 'MB', 'GB', 'TB' ]:
            if rate < 1024.0:
                return "%3.2f%s/s" % (rate, modifier)
            rate /= 1024.0

    def complete(self, bytes_written):
        """
        Called when a transfer has been completed, so that the summary can
        be flushed for this transfer.
        """
        self.time_taken = (datetime.now() - self._start).seconds
        self.bytes_written = bytes_written

        if self.bytes_total > 0L:
            self.percentage = int(
                (float(self.bytes_written) / float(self.bytes_total)) * 100.0
            )
        elif self.bytes_written == 0L:
            self.percentage = 100
        else:
            self.percentage = 0

        if self._enable_output:
            self.write()
            sys.stdout.write(u"\n")


class Critical(object):
    """
    Defines a channel for critical messages to be written to stdout
    and stderr IO buffers.
    """
    def __call__(self, ex):
        sys.stderr.write(u"gsync: %s\n" % unicode(ex))

        from libgsync import __version__
        import traceback

        tb = traceback.extract_tb((sys.exc_info())[-1])
        source_file = "unknown"
        lineno = 0

        for i in xrange(len(tb) - 1, -1, -1):
            if re.match(r'^.*/libgsync/.*$', tb[i][0]) is not None:
                source_file = os.path.basename(tb[i][0])
                if source_file == "__init__.py":
                    source_file = os.path.basename(
                        os.path.dirname(tb[i][0])
                    )
                lineno = tb[i][1]
                break

        sys.stderr.write(u"gsync error: %s at %s(%d) [client=%s]\n" % (
            ex.__class__.__name__, source_file, lineno, __version__
        ))


verbose = Verbose() # pylint: disable-msg=C0103
debug = Debug() # pylint: disable-msg=C0103
itemize = Itemize() # pylint: disable-msg=C0103
critical = Critical() # pylint: disable-msg=C0103

__all__ = [ "verbose", "debug", "itemize", "critical" ]

if os.environ.get('GSYNC_DEBUG', '0') == '1': # pragma: no cover
    debug.enable()

########NEW FILE########
__FILENAME__ = factory
#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""Factory class for the SyncFile adapter"""

import os
from libgsync.output import debug
from libgsync.drive import Drive

class SyncFileFactory(object):
    """
    SyncFileFactory class creates either a remote or local SyncFile
    instance to be used with the SyncFile adapter.  Remote files are those
    that exist in the Google Drive space, while local files exist on the
    local system.  Both file classes share the same common interface.
    """

    @staticmethod
    @debug.function
    def create(path):
        """Creates a new SyncFile instance"""

        drive = Drive()

        if drive.is_drivepath(path):
            filepath = drive.normpath(path)

            from libgsync.sync.file.remote import SyncFileRemote
            return SyncFileRemote(filepath)

        else:
            filepath = os.path.normpath(path)

            from libgsync.sync.file.local import SyncFileLocal
            return SyncFileLocal(filepath)

########NEW FILE########
__FILENAME__ = test_unicode
#!/usr/bin/env python
# -*- coding: utf8 -*-

import sys, os

FS_ENCODING = sys.getfilesystemencoding()

for p in sys.argv[1:]:
    print "p = %s" % repr(p)

    if not isinstance(p, unicode):
        up = unicode(p, encoding="latin-1", errors="strict")
        
    print "up = %s" % repr(up)
    print "up.utf8 = %s" % up.encode("utf8")

    print "Command line file exists = %s" % os.path.exists(p)
    print "Unicode file exists = %s" % os.path.exists(up)
    print "%s file exists = %s" % (
        FS_ENCODING, os.path.exists(up.encode(FS_ENCODING))
    )

########NEW FILE########
__FILENAME__ = test_file
#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest
from libgsync.drive.file import DriveFile


class TestCaseDriveFile(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    
    def test_drive_file_is_a_dict(self):
        self.assertTrue(isinstance(DriveFile(), dict))


    def test_instantiate_from_dictionary(self):
        data = {
            'a': 'a_val',
            'b': 'b_val'
        }

        drive_file = DriveFile(data)

        self.assertEqual(data['a'], drive_file.a)
        self.assertEqual(data['b'], drive_file.b)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_mimetypes
#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest
from libgsync.drive.mimetypes import MimeTypes

class TestDriveMimeTypes(unittest.TestCase):
    def setUp(self):
        try:
            import magic
            self.magic_from_file = magic.from_file
        except Exception:
            pass

    def tearDown(self):
        try:
            import magic
            magic.from_file = self.magic_from_file
        except Exception:
            pass

    def test_DriveMimeTypes_get_unknown_mimetype(self):
        self.assertEqual(MimeTypes.get("/dev/null"), "inode/chardevice")

    def test_DriveMimeTypes_get_binary_mimetype(self):
        self.assertEqual(
            MimeTypes.get("/bin/true"), "application/x-executable"
        )

    def test_DriveMimeTypes_get_folder_mimetype(self):
        self.assertEqual(MimeTypes.get("/bin"), "inode/directory")

    def test_DriveMimeTypes_get_magic_exception(self):
        try:
            import magic
        except Exception:
            self.skipTest("Module 'magic' not present")
            return

        def func(*args, **kwargs):
            raise Exception("Fake exception")

        magic.from_file = func

        self.assertEqual(MimeTypes.get("/bin/true"), MimeTypes.NONE)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_file
#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest
from libgsync.sync.file import SyncFile

class TestSyncFile(unittest.TestCase):
    def test_SyncFile_relative_to(self):
        f = SyncFile("/gsync_unittest")

        self.assertEqual(
            f.relative_to("/gsync_unittest/open_for_read.txt"),
            "open_for_read.txt"
        )

########NEW FILE########
__FILENAME__ = test_drive
#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest, os, inspect
from libgsync.output import debug
from libgsync.drive import Drive, DriveFile, DrivePathCache
from libgsync.drive.mimetypes import MimeTypes
from apiclient.http import MediaFileUpload

# This decorator is used to skip tests that require authentication and a
# connection to a user's drive account.  Rather than fail setup or tests,
# we simply skip them and flag them as such.
def requires_auth(func):
    def __requires_auth(testcase, *args, **kwargs):
        config_dir = Drive()._get_config_dir()
        credentials = os.path.join(config_dir, "credentials")

        if os.path.exists(credentials):
            return func(testcase, *args, **kwargs)

        if inspect.isclass(testcase):
            return None

        testcase.skipTest("Authentication not established")
        return None

    return __requires_auth

@requires_auth
def setup_drive_data(testcase):
    # Ironic, using Gsync to setup the tests, but if it fails the tests
    # will fail anyway, so we will be okay.
    assert os.path.exists("tests/data")

    drive = Drive()
    drive.delete("drive://gsync_unittest/", skip_trash=True)
    drive.mkdir("drive://gsync_unittest/")
    drive.create("drive://gsync_unittest/open_for_read.txt", {})
    drive.update("drive://gsync_unittest/open_for_read.txt", {},
        media_body=MediaFileUpload("tests/data/open_for_read.txt",
            mimetype=MimeTypes.BINARY_FILE, resumable=True
        )
    )


class TestDrivePathCache(unittest.TestCase):
    def test_constructor(self):
        dpc = DrivePathCache({
            "junk": "junk",
            "drive://gsync_unittest/a_valid_path": {}
        })

        self.assertEqual(dpc.get("junk"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest/a_valid_path"), {})

    def test_put(self):
        dpc = DrivePathCache()

        self.assertEqual(dpc.get("drive://gsync_unittest"), None)
        dpc.put("drive://gsync_unittest//////", {})
        self.assertEqual(dpc.get("drive://gsync_unittest"), {})

    def test_get(self):
        dpc = DrivePathCache()

        dpc.put("drive://gsync_unittest", {})
        self.assertEqual(dpc.get("drive://gsync_unittest/123"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest//////"), {})
        self.assertEqual(dpc.get("drive://gsync_unittest"), {})

    def test_clear(self):
        dpc = DrivePathCache()

        dpc.put("drive://gsync_unittest/1", {})
        dpc.put("drive://gsync_unittest/2", {})
        dpc.put("drive://gsync_unittest/3", {})

        self.assertEqual(dpc.get("drive://gsync_unittest/1"), {})
        self.assertEqual(dpc.get("drive://gsync_unittest/2"), {})
        self.assertEqual(dpc.get("drive://gsync_unittest/3"), {})

        dpc.clear("drive://gsync_unittest/1")
        self.assertEqual(dpc.get("drive://gsync_unittest/1"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest/2"), {})
        self.assertEqual(dpc.get("drive://gsync_unittest/3"), {})

        dpc.clear("drive://gsync_unittest/2")
        self.assertEqual(dpc.get("drive://gsync_unittest/1"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest/2"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest/3"), {})

        dpc.clear("drive://gsync_unittest/3")
        self.assertEqual(dpc.get("drive://gsync_unittest/1"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest/2"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest/3"), None)

    def test_repr(self):
        dpc = DrivePathCache()
        self.assertEqual(repr(dpc), "DrivePathCache({})")


class TestDrive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setup_drive_data(cls)

    def test_normpath(self):
        drive = Drive()

        paths = [
            "drive:",
            "drive:/",
            "drive://",
            "drive://gsync_unittest",
            "drive://gsync_unittest/",
            "//gsync_unittest/a/b/c",
            "gsync_unittest/a/b/c/.",
            "/gsync_unittest/a/b/c/..",
        ]
        expected_paths = [
            "drive://",
            "drive://",
            "drive://",
            "drive://gsync_unittest",
            "drive://gsync_unittest",
            "drive://gsync_unittest/a/b/c",
            "gsync_unittest/a/b/c",
            "drive://gsync_unittest/a/b",
        ]

        for i in xrange(0, len(paths)):
            expected = str(expected_paths[i])
            actual = str(drive.normpath(paths[i]))

            self.assertEqual(expected, actual,
                "From %s expected %s but got %s" % (
                    paths[i], expected, actual
                )
            )

    def test_strippath(self):
        drive = Drive()

        paths = [
            "drive:",
            "drive:/",
            "drive://",
            "drive://gsync_unittest",
            "drive://gsync_unittest/",
            "drive://gsync_unittest/a/b/c",
            "drive://gsync_unittest/a/b/c/.",
            "drive://gsync_unittest/a/b/c/..",
        ]
        expected_paths = [
            "/",
            "/",
            "/",
            "/gsync_unittest",
            "/gsync_unittest",
            "/gsync_unittest/a/b/c",
            "/gsync_unittest/a/b/c",
            "/gsync_unittest/a/b",
        ]

        for i in xrange(0, len(paths)):
            expected = str(expected_paths[i])
            actual = str(drive.strippath(paths[i]))

            self.assertEqual(expected, actual,
                "From %s expected %s but got %s" % (
                    paths[i], expected, actual
                )
            )

    def test_pathlist(self):
        drive = Drive()
        paths = [
            "drive://",
            "drive://gsync_unittest",
            "drive://gsync_unittest/",
            "drive://gsync_unittest/a/b/c",
            "drive://gsync_unittest/a/b/c/.",
            "drive://gsync_unittest/a/b/c/..",
        ]
        expected_paths = [
            [ "drive://" ],
            [ "drive://", "gsync_unittest" ],
            [ "drive://", "gsync_unittest" ],
            [ "drive://", "gsync_unittest", "a", "b", "c" ],
            [ "drive://", "gsync_unittest", "a", "b", "c" ],
            [ "drive://", "gsync_unittest", "a", "b" ],
        ]

        for i in xrange(0, len(paths)):
            expected = str(expected_paths[i])
            actual = str(drive.pathlist(paths[i]))

            self.assertEqual(expected, actual,
                "From %s expected %s but got %s" % (
                    paths[i], expected, actual
                )
            )

    @requires_auth
    def test_isdir(self):
        drive = Drive()

        self.assertFalse(drive.isdir("drive://gsync_unittest/is_a_dir"))
        drive.mkdir("drive://gsync_unittest/is_a_dir")
        self.assertTrue(drive.isdir("drive://gsync_unittest/is_a_dir"))

        drive.create("drive://gsync_unittest/not_a_dir", {})
        self.assertFalse(drive.isdir("drive://gsync_unittest/not_a_dir"))

    @requires_auth
    def test_stat(self):
        drive = Drive()

        info = drive.stat("drive://")
        self.assertIsNotNone(info)
        self.assertEqual("root", info.id)

        info = drive.stat("drive://gsync_unittest/")
        self.assertIsNotNone(info)
        self.assertIsNotNone(info.id)
        self.assertEqual(info.title, "gsync_unittest")

    @requires_auth
    def test_mkdir(self):
        drive = Drive()

        info = drive.mkdir("drive://gsync_unittest/test_mkdir/a/b/c/d/e/f/g")
        self.assertIsNotNone(info)
        self.assertEqual(info.title, "g")

        drive.delete("drive://gsync_unittest/test_mkdir", skip_trash=True)

    @requires_auth
    def test_listdir(self):
        drive = Drive()

        info = drive.create("drive://gsync_unittest/a_file_to_list", {})
        self.assertIsNotNone(info)

        items = drive.listdir("drive://gsync_unittest/")
        self.assertTrue(isinstance(items, list))
        self.assertTrue("a_file_to_list" in items)

    @requires_auth
    def test_create(self):
        drive = Drive()

        info = drive.create("drive://gsync_unittest/create_test", {
            "title": "Will be overwritten",
            "description": "Will be kept"
        })
        self.assertEqual(info['title'], "create_test")
        self.assertEqual(info['description'], "Will be kept")

        info2 = drive.create("drive://gsync_unittest/create_test", {
            "description": "This file will replace the first one"
        })
        self.assertNotEqual(info['id'], info2['id'])
        self.assertEqual(info2['title'], "create_test")
        self.assertEqual(info2['description'], "This file will replace the first one")

    @requires_auth
    def test_update_with_progress(self):
        drive = Drive()

        info = drive.create("drive://gsync_unittest/update_test", {
            "description": "Old description"
        })
        self.assertEqual(info['title'], "update_test")

        def progress_callback(status):
            progress_callback.called = True

        progress_callback.called = False

        info = drive.update("drive://gsync_unittest/update_test", {
                "description": "New description"
            },
            media_body=MediaFileUpload("tests/data/open_for_read.txt",
                mimetype=MimeTypes.BINARY_FILE, resumable=True
            ),
            progress_callback=progress_callback
        )
        self.assertEqual(info['description'], "New description")
        self.assertTrue(int(info['fileSize']) > 0)
        self.assertTrue(progress_callback.called)


class TestDriveFileObject(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setup_drive_data(cls)

    def test_constructor(self):
        data = {
            'id': 'fhebfhbf',
            'title': 'Test file',
            'mimeType': 'application/dummy'
        }

        f = DriveFile(**data)
        self.assertIsNotNone(f)
        self.assertEqual(f.id, data['id'])

        ff = DriveFile(**f)
        self.assertIsNotNone(ff)
        self.assertEqual(f.id, ff.id)

    @requires_auth
    def test_open_for_read(self):
        drive = Drive()
        f = drive.open("drive://gsync_unittest/open_for_read.txt", "r")
        self.assertIsNotNone(f)

    @requires_auth
    def test_open_for_read_and_seek(self):
        drive = Drive()
        f = drive.open("drive://gsync_unittest/open_for_read.txt", "r")

        self.assertNotEqual(int(f._info.fileSize), 0)
        f.seek(0, os.SEEK_END)

        self.assertNotEqual(f.tell(), 0)

    @requires_auth
    def test_open_for_read_and_read_data(self):
        drive = Drive()
        f = drive.open("drive://gsync_unittest/open_for_read.txt", "r")
        contents = f.read()

        self.assertIsNotNone(contents)
        self.assertNotEqual(contents, "")

    @requires_auth
    def test_revisions(self):
        drive = Drive()

        num_revisions = 6

        info = drive.create("drive://gsync_unittest/revision_test", {
            "description": "revision-0"
        })
        self.assertEqual(info['description'], "revision-0")

        for revision in range(1, num_revisions):
            description = "revision-%d" % revision
            info = drive.update("drive://gsync_unittest/revision_test", {
                    "description": description
                },
                media_body=MediaFileUpload("tests/data/open_for_read.txt",
                    mimetype=MimeTypes.BINARY_FILE, resumable=True
                )
            )
            self.assertEqual(info['description'], description)

        f = drive.open("drive://gsync_unittest/revision_test", "r")
        revisions = f.revisions()

        self.assertEqual(len(revisions), num_revisions)
        self.assertEqual(int(revisions[0]['fileSize']), 0)
        self.assertNotEqual(int(revisions[-1]['fileSize']), 0)

    @requires_auth
    def test_mimetypes(self):
        drive = Drive()

        drive.mkdir("drive://gsync_unittest/mimetype_test_dir")

        f = drive.open("drive://gsync_unittest/mimetype_test_dir", "r")
        self.assertEqual(f.mimetype(), MimeTypes.FOLDER)

        f.mimetype(MimeTypes.BINARY_FILE)
        self.assertEqual(f.mimetype(), MimeTypes.BINARY_FILE)

    @requires_auth
    def test_close(self):
        drive = Drive()

        f = drive.open("drive://gsync_unittest/open_for_read.txt", "r")
        contents = f.read()
        self.assertNotEqual(contents, None)

        f.close()
        self.assertTrue(f.closed)

        try:
            f.seek(0)
            self.assertEqual("Expected IOError for seek on closed file", None)
        except IOError:
            pass

    @requires_auth
    def test_write(self):
        drive = Drive()

        try:
            drive.open("drive://gsync_unittest/open_for_read.txt", "w")
            self.assertEqual("Expected IOError for unsupported mode", None)
        except IOError:
            pass
            
        f = drive.open("drive://gsync_unittest/open_for_read.txt", "r")
        try:
            f.write("Some data")
            self.assertEqual(
                "Expected IOError for writing to readable file", None
            )
        except IOError:
            pass


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_options
#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest, sys


class TestGsyncOptions(unittest.TestCase):
    def setUp(self):
        self.argv = sys.argv
        sys.argv = [ "gsync", "path", "path" ]

    def tearDown(self):
        sys.argv = self.argv

    def test_01_is_initialised_on_property_inspection(self):
        import libgsync.options
        GsyncOptions = libgsync.options.GsyncOptions
        GsyncListOptions = GsyncOptions.list()
        GsyncListOptionsType = libgsync.options.GsyncListOptionsType

        def hooked_init(func):
            def __hooked_init(*args, **kwargs):
                hooked_init.call_count += 1
                func(*args, **kwargs)

            return __hooked_init

        hooked_init.call_count = 0

        GsyncListOptionsType._GsyncListOptionsType__initialise_class = hooked_init(
            GsyncListOptionsType._GsyncListOptionsType__initialise_class
        )

        self.assertNotEqual(GsyncOptions.debug, None)
        self.assertNotEqual(GsyncOptions.debug, None)
        self.assertEqual(1, hooked_init.call_count)

    def test_02_list_options(self):
        import libgsync.options
        GsyncOptions = libgsync.options.GsyncOptions

        self.assertFalse(isinstance(GsyncOptions.debug, list))
        self.assertTrue(isinstance(GsyncOptions.list().debug, list))
        self.assertEqual(GsyncOptions.debug, GsyncOptions.list().debug[-1])

    def test_03_dynamic_property_creation(self):
        import libgsync.options
        GsyncOptions = libgsync.options.GsyncOptions

        GsyncOptions.an_undefined_attribute = "undefined_attribute"

        self.assertEqual(
            GsyncOptions.an_undefined_attribute,
            "undefined_attribute"
        )

        self.assertIsNone(GsyncOptions.another_undefined_attribute)
        self.assertEqual(
            GsyncOptions.list().another_undefined_attribute, [ None ]
        )

        self.assertEqual(
            GsyncOptions.list().another_listtype_undefined_attribute, [ None ]
        )


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_output
#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest, StringIO, sys
from libgsync.output import Channel, Debug, Itemize, Progress, Critical

class TestCaseStdStringIO(unittest.TestCase):
    def setUp(self):
        self.stdout, sys.stdout = sys.stdout, StringIO.StringIO()
        self.stderr, sys.stderr = sys.stderr, StringIO.StringIO()

    def tearDown(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr


class TestChannel(TestCaseStdStringIO):
    def test_disabled_by_default(self):
        channel = Channel()
        self.assertFalse(channel.enabled())

    def test_no_output_when_disabled(self):
        channel = Channel()
        channel.disable()
        self.assertFalse(channel.enabled())

        channel("Hello World")
        self.assertEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

    def test_output_when_enabled(self):
        channel = Channel()
        channel.enable()
        self.assertTrue(channel.enabled())

        channel("Hello World")
        self.assertEqual("Hello World\n", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())


class TestCritical(TestCaseStdStringIO):
    def test_call(self):
        channel = Critical()

        try:
            raise Exception("CriticalException")
        except Exception, ex:
            channel(ex)

        import re
        pat = re.compile(
            r'^gsync: CriticalException\n' \
            r'gsync error: Exception at .*\(\d+\) \[client=[\d.]+\]\n$',
            re.M | re.S
        )

        self.assertIsNotNone(pat.search(sys.stderr.getvalue()))
        self.assertEqual("", sys.stdout.getvalue())


class TestDebug(TestCaseStdStringIO):
    def test_stack(self):
        channel = Debug()
        channel.enable()
        self.assertTrue(channel.enabled())

        channel.stack()

        import re
        pat = re.compile(
            r'^DEBUG: BEGIN STACK TRACE\n' \
            r'.*\n' \
            r'DEBUG: END STACK TRACE\n$',
            re.M | re.S
        )
        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))
        self.assertEqual("", sys.stderr.getvalue())

    def test_exception_as_object(self):
        channel = Debug()
        channel.enable()
        self.assertTrue(channel.enabled())

        import re
        pat = re.compile(
            r'''^DEBUG: Exception\('Test exception',\): ''',
            re.M | re.S
        )

        try:
            raise Exception("Test exception")
        except Exception, e:
            channel.exception(e)

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))
        self.assertEqual("", sys.stderr.getvalue())

    def test_exception_as_string(self):
        channel = Debug()
        channel.enable()
        self.assertTrue(channel.enabled())

        import re
        pat = re.compile(
            r'''^DEBUG: 'Test exception': ''',
            re.M | re.S
        )

        try:
            raise Exception("Test exception")
        except Exception, e:
            channel.exception(str(e))

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))
        self.assertEqual("", sys.stderr.getvalue())
        
    def test_exception_as_custom_string(self):
        channel = Debug()
        channel.enable()
        self.assertTrue(channel.enabled())

        custom_string = "This is a custom string"

        import re
        pat = re.compile(
            r'''^DEBUG: %s: ''' % repr(custom_string),
            re.M | re.S
        )

        try:
            raise Exception("Test exception")
        except Exception, e:
            channel.exception(custom_string)

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))
        self.assertEqual("", sys.stderr.getvalue())

    def test_exception_as_default(self):
        channel = Debug()
        channel.enable()
        self.assertTrue(channel.enabled())

        import re
        pat = re.compile(
            r'''^DEBUG: 'Exception': ''',
            re.M | re.S
        )

        try:
            raise Exception("Test exception")
        except Exception, e:
            channel.exception()

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))
        self.assertEqual("", sys.stderr.getvalue())


class TestItemize(TestCaseStdStringIO):
    def test_callable(self):
        channel = Itemize()

        channel(">+", "/dev/null")

        self.assertEqual(sys.stdout.getvalue(), "         >+ /dev/null\n")
        self.assertEqual("", sys.stderr.getvalue())

        sys.stdout.truncate(0)

        channel(">+++++++++++++++++", "/dev/null")

        self.assertEqual(sys.stdout.getvalue(), ">++++++++++ /dev/null\n")
        self.assertEqual("", sys.stderr.getvalue())


class ProgressStatus(object):
    def __init__(self, total_size = 0, resumable_progress = 0):
        self.total_size = total_size
        self.resumable_progress = resumable_progress

    def progress(self):
        return float(self.resumable_progress) / float(self.total_size)


class TestProgress(TestCaseStdStringIO):
    def test_with_disabled_output(self):
        channel = Progress(enable_output=False)

        self.assertEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

    def test_enabled_output_by_default(self):
        channel = Progress()

        self.assertNotEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

    def test_with_enabled_output(self):
        channel = Progress(enable_output=True)

        self.assertNotEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

    def test_status_messages_with_callback(self):
        def callback(status):
            callback.called = True

        callback.called = False

        channel = Progress(callback=callback)

        self.assertNotEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

        import re

        for i in ( 5, 10, 20, 40, 50, 75, 100 ):
            pat = re.compile(
                r'^\s+%d\s+%d%%\s+\d+\.\d{2}(?:B|KB|MB|GB|TB)/s\s+\d+:\d+:\d+$' % (i, i),
                re.S | re.M
            )

            sys.stdout.truncate(0)
            channel(ProgressStatus(100, i))

            self.assertIsNotNone(pat.search(sys.stdout.getvalue()))

        self.assertTrue(callback.called)

    def test_rate_normalization(self):
        channel = Progress()

        self.assertNotEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

        fileSize = 1000000000

        import re
        pat = re.compile(
            r'^\s+%d\s+%d%%\s+\d+\.\d{2}(?:KB|MB|GB|TB)/s\s+\d+:\d+:\d+$' % (fileSize, 100),
            re.S | re.M
        )

        sys.stdout.truncate(0)
        channel(ProgressStatus(fileSize, fileSize / 4))

        self.assertIsNone(pat.search(sys.stdout.getvalue()))

        sys.stdout.truncate(0)
        channel.complete(fileSize)

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))

    def test_zero_byte_file(self):
        channel = Progress()

        self.assertNotEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

        import re
        pat = re.compile(
            r'^\s+%d\s+%d%%\s+\d+\.\d{2}(?:B|KB|MB|GB|TB)/s\s+\d+:\d+:\d+$' % (0, 100),
            re.S | re.M
        )

        sys.stdout.truncate(0)
        channel.complete(0)

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))


    def test_complete(self):
        channel = Progress()

        self.assertNotEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

        import re
        pat = re.compile(
            r'^\s+%d\s+%d%%\s+\d+\.\d{2}(?:B|KB|MB|GB|TB)/s\s+\d+:\d+:\d+$' % (100, 100),
            re.S | re.M
        )

        sys.stdout.truncate(0)
        channel(ProgressStatus(100, 25))

        self.assertIsNone(pat.search(sys.stdout.getvalue()))

        sys.stdout.truncate(0)
        channel.complete(100)

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sync
#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest, tempfile, sys, os, shutil
import libgsync.options
import libgsync.sync
import libgsync.hashlib as hashlib

try: import posix as os_platform
except ImportError: import nt as os_platform

def sha256sum(path):
    blocksize = 65536
    sha = hashlib.new("sha256")
    with open(path, "r+b") as f:
        for block in iter(lambda: f.read(blocksize), ""):
            sha.update(block)

    return sha.hexdigest()


class TestCaseSync(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.argv = sys.argv

        # Setup fake arguments to satisfy GsyncOptions and docopt validation.
        sys.argv = [ "gsync", os.path.join("tests", "data"), self.tempdir ]
        sys.argc = len(sys.argv)

        # Reset this flag for tests that do not expect it.
        libgsync.options = reload(libgsync.options)
        libgsync.sync = reload(libgsync.sync)

    def tearDown(self):
        sys.argv = self.argv
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)

    def test_local_files(self):
        src = sys.argv[1]
        dst = os.path.join(self.tempdir, "open_for_read.txt")

        self.assertFalse(os.path.exists(dst))

        sync = libgsync.sync.Sync(src, self.tempdir)
        sync("open_for_read.txt")

        self.assertTrue(os.path.exists(dst))
        self.assertEqual(
            sha256sum(os.path.join(src, "open_for_read.txt")),
            sha256sum(dst)
        )

    def test_local_files_with_identical_mimetypes(self):
        src = sys.argv[1]
        dst = os.path.join(self.tempdir, "open_for_read.txt")

        # Copy a binary file to ensure it isn't ascii.
        shutil.copyfile(os.path.join(src, "open_for_read.txt"), dst)
        self.assertTrue(os.path.exists(dst))

        sync = libgsync.sync.Sync(src, self.tempdir)
        sync("open_for_read.txt")

        self.assertTrue(os.path.exists(dst))
        self.assertEqual(
            sha256sum(os.path.join(src, "open_for_read.txt")),
            sha256sum(os.path.join(self.tempdir, "open_for_read.txt"))
        )

    def test_local_files_with_different_mimetypes(self):
        src = sys.argv[1]
        dst = os.path.join(self.tempdir, "open_for_read.txt")

        # Copy a binary file to ensure it isn't ascii.
        shutil.copyfile("/bin/true", dst)
        self.assertTrue(os.path.exists(dst))

        sync = libgsync.sync.Sync(src, self.tempdir)
        sync("open_for_read.txt")

        self.assertTrue(os.path.exists(dst))
        self.assertEqual(
            sha256sum(os.path.join(src, "open_for_read.txt")),
            sha256sum(os.path.join(self.tempdir, "open_for_read.txt"))
        )

    def test_local_files_with_different_sizes(self):
        src = sys.argv[1]
        dst = os.path.join(self.tempdir, "open_for_read.txt")

        # Copy a binary file to ensure it isn't ascii.
        shutil.copyfile(os.path.join(src, "open_for_read.txt"), dst)

        # Alter the destination file size.
        with open(dst, "a") as f:
            f.write("Some extra text\n")

        sync = libgsync.sync.Sync(src, self.tempdir)
        sync("open_for_read.txt")

        self.assertTrue(os.path.exists(dst))
        self.assertEqual(
            sha256sum(os.path.join(src, "open_for_read.txt")),
            sha256sum(os.path.join(self.tempdir, "open_for_read.txt"))
        )

    def test_local_files_force_dest_file(self):
        src = sys.argv[1]
        dst = os.path.join(self.tempdir, "a_different_filename.txt")

        libgsync.options.GsyncOptions.force_dest_file = True

        self.assertFalse(os.path.exists(dst))

        sync = libgsync.sync.Sync(src, dst)
        sync("open_for_read.txt")

        self.assertTrue(os.path.exists(dst))

        self.assertEqual(
            sha256sum(os.path.join(src, "open_for_read.txt")),
            sha256sum(dst)
        )

    def test_non_existent_source_file(self):
        dst = os.path.join(self.tempdir, "a_different_filename.txt")

        self.assertFalse(os.path.exists(dst))

        sync = libgsync.sync.Sync(sys.argv[1], dst)
        sync("file_not_found.txt")

        self.assertFalse(os.path.exists(dst))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
