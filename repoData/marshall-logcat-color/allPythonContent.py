__FILENAME__ = column
"""
logcat-color

Copyright 2012, Marshall Culpepper
Licensed under the Apache License, Version 2.0

Columns for displaying logcat log data
"""
import colorama
from colorama import Fore, Back, Style
import StringIO

colorama.init()

class Column(object):
    def __init__(self, layout):
        self.width = layout.config.get_column_width(self)

    def format(self, data):
        return self.FORMAT % data

class DateColumn(Column):
    NAME = "date"
    FORMAT = Fore.WHITE + Back.BLACK + Style.DIM + \
             "%s" + Style.RESET_ALL
    DEFAULT_WIDTH = 7

class TimeColumn(Column):
    NAME = "time"
    FORMAT = Fore.WHITE + Back.BLACK + Style.DIM + \
             "%s" + Style.RESET_ALL
    DEFAULT_WIDTH = 14

class PIDColumn(Column):
    NAME = "pid"
    DEFAULT_WIDTH = 8
    FORMAT = Fore.WHITE + Back.BLACK + Style.DIM + \
             "%s" + Style.RESET_ALL

    def format(self, pid):
        # center process info
        if self.width > 0:
            pid = pid.center(self.width)

        return Column.format(self, pid)

class TIDColumn(PIDColumn):
    NAME = "tid"

    def format(self, tid):
        # normalize thread IDs to be decimal
        if "0x" in tid:
            tid = str(int(tid, 16))

        return PIDColumn.format(self, tid)

class TagColumn(Column):
    NAME = "tag"
    DEFAULT_WIDTH = 20
    COLOR_NAMES = ("RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN", "WHITE")
    COLOR_MAP = {}

    @classmethod
    def init_color_map(cls):
        for color in cls.COLOR_NAMES:
            cls.COLOR_MAP[color] = getattr(Fore, color)

    def __init__(self, layout):
        Column.__init__(self, layout)

        tag_colors = None
        if layout.profile:
            tag_colors = layout.profile.tag_colors

        self.tag_colors = tag_colors or {}
        self.last_used = self.COLOR_MAP.values()[:]

    # This will allocate a unique format for the given tag since we dont have
    # very many colors, we always keep track of the LRU
    def allocate_color(self, tag):
        if tag not in self.tag_colors:
            self.tag_colors[tag] = self.last_used[0]

        color = self.tag_colors[tag]
        self.last_used.remove(color)
        self.last_used.append(color)
        return color

    def format(self, tag):
        color = self.allocate_color(tag)
        if self.width > 2:
            if self.width < len(tag):
                tag = tag[0:self.width-2] + ".."

        tag = tag.rjust(self.width)
        return color + Style.DIM + tag + Style.RESET_ALL

TagColumn.init_color_map()

class PriorityColumn(Column):
    NAME = "priority"
    DEFAULT_WIDTH = 3
    COLORS = {
        "V": Fore.WHITE + Back.BLACK,
        "D": Fore.BLACK + Back.BLUE,
        "I": Fore.BLACK + Back.GREEN,
        "W": Fore.BLACK + Back.YELLOW,
        "E": Fore.BLACK + Back.RED,
        "F": Fore.BLACK + Back.RED
    }

    def __init__(self, layout):
        Column.__init__(self, layout)
        self.formats = {}
        for priority in self.COLORS.keys():
            self.formats[priority] = self.COLORS[priority] + \
                priority.center(self.width) + Style.RESET_ALL

    def format(self, priority):
        return self.formats[priority]

class MessageColumn(Column):
    NAME = "message"
    DEFAULT_WIDTH = 0
    def __init__(self, layout):
        self.width = None
        self.left = layout.total_column_width
        if layout.config.get_wrap() and (not layout.profile or layout.profile.wrap):
            self.width = layout.width - self.left

    def format(self, message):
        # Don't wrap when width is None
        if not self.width:
            return message

        messagebuf = StringIO.StringIO()
        current = 0
        while current < len(message):
            next = min(current + self.width, len(message))
            messagebuf.write(message[current:next])
            if next < len(message):
                messagebuf.write("\n%s" % (" " * self.left))
            current = next
        return messagebuf.getvalue()

########NEW FILE########
__FILENAME__ = config
from logcatcolor.column import TagColumn
from logcatcolor.profile import Profile
import os
import platform
import re
import sys
import traceback

class LogcatColorConfig(object):
    DEFAULT_LAYOUT = "brief"
    DEFAULT_WRAP = True
    DEFAULT_ADB = None
    DEFAULT_STAY_CONNECTED = False

    def __init__(self, options):
        self.options = options
        self.path = options.config or self.get_default_config()
        self.filters = {}

        self.config = {
            "Profile":  Profile,
            "__file__": self.path
        }

        self.config.update(TagColumn.COLOR_MAP)

        if os.path.exists(self.path) and os.path.isfile(self.path):
            # config file is just a python script that globals are imported from
            try:
                execfile(self.path, self.config)
            except:
                self.report_config_error()
                sys.exit(1)

        self.post_load()

    def report_config_error(self):
        config_error = """
########################################
# There was an error loading config from
# %(path)s
########################################

%(error)s"""

        print >>sys.stderr, config_error % {
            "path": self.path,
            "error": traceback.format_exc()
        }

    def get_default_config(self):
        env_key = "HOME"
        if platform.system() == "Windows":
            env_key = "USERPROFILE"

        home_dir = os.environ[env_key]
        return os.path.join(home_dir, ".logcat-color")

    def post_load(self):
        if self.options.wrap is not None:
            self.config["wrap"] = self.options.wrap
        if self.options.stay_connected is not None:
            self.config["stay_connected"] = self.options.stay_connected

    def get_default_layout(self):
        return self.config.get("default_layout", self.DEFAULT_LAYOUT)

    def get_column_width(self, column):
        return self.config.get(column.NAME + "_width", column.DEFAULT_WIDTH)

    def get_wrap(self):
        return self.config.get("wrap", self.DEFAULT_WRAP)

    def get_stay_connected(self):
        return self.config.get("stay_connected", self.DEFAULT_STAY_CONNECTED)

    def get_adb(self):
        return self.config.get("adb", self.DEFAULT_ADB)

########NEW FILE########
__FILENAME__ = format
"""
logcat-color

Copyright 2012, Marshall Culpepper
Licensed under the Apache License, Version 2.0

Support for reading various logcat logging formats into an easier to consume
data map.
"""
import re

def format(cls):
    Format.TYPES[cls.NAME] = cls
    Format.REGEXES[cls.NAME] = re.compile(cls.PATTERN) if cls.PATTERN else None
    return cls

class Format(object):
    TYPES = {}
    REGEXES = {}
    MARKER_REGEX = re.compile(r"^--------- beginning of")

    def __init__(self):
        self.data = {}
        self.regex = self.REGEXES[self.NAME]

    def match(self, line):
        if not self.regex:
            return True

        self.data["line"] = line
        match = self.regex.match(line)
        if not match:
            return False

        for name, value in match.groupdict().iteritems():
            self.data[name] = value.strip()
        return True

    def get(self, name):
        return self.data.get(name)

    def include(self, profile):
        if profile and not profile.include(self.data):
            return False
        return True

@format
class BriefFormat(Format):
    "I/Tag(  PID): message"
    NAME = "brief"
    PRIORITY_PATTERN = r"(?P<priority>[A-Z])"
    PRIORITY_TAG_PATTERN = PRIORITY_PATTERN + r"/" + r"(?P<tag>[^\(]*?)"

    PID_PATTERN = r"(?P<pid>\d+)"
    PID_PAREN_PATTERN = r"\(\s*" + PID_PATTERN + r"\)"
    MESSAGE_PATTERN = r"(?P<message>.*?)"

    BRIEF_PATTERN = PRIORITY_TAG_PATTERN + \
              PID_PAREN_PATTERN + r": " + \
              MESSAGE_PATTERN
    PATTERN = r"^" + BRIEF_PATTERN + r"$"

@format
class ProcessFormat(Format):
    "I(  PID) message (Tag)"
    NAME = "process"
    PATTERN = r"^" + BriefFormat.PRIORITY_PATTERN + \
             BriefFormat.PID_PAREN_PATTERN + r" " + \
             BriefFormat.MESSAGE_PATTERN + r" " + \
             r"\((?P<tag>.+)\)$"

@format
class TagFormat(Format):
    "I/Tag  : message"
    NAME = "tag"
    PATTERN = r"^" + BriefFormat.PRIORITY_TAG_PATTERN + r": " + \
              BriefFormat.MESSAGE_PATTERN + r"$"

@format
class ThreadFormat(Format):
    "I(  PID:TID) message"
    NAME = "thread"
    TID_HEX_PATTERN = r"(?P<tid>0x[0-9a-f]+)"
    PID_TID_HEX_PATTERN = BriefFormat.PID_PATTERN + r":" + TID_HEX_PATTERN

    PATTERN = r"^" + BriefFormat.PRIORITY_PATTERN + \
              r"\(\s*" + PID_TID_HEX_PATTERN + r"\) " + \
              BriefFormat.MESSAGE_PATTERN + r"$"

@format
class TimeFormat(Format):
    "MM-DD HH:MM:SS.mmm D/Tag(  PID): message"
    NAME = "time"
    DATE_TIME_PATTERN = r"(?P<date>\d\d-\d\d)\s(?P<time>\d\d:\d\d:\d\d\.\d\d\d)"
    PATTERN = r"^" + DATE_TIME_PATTERN + r" " + BriefFormat.BRIEF_PATTERN + r"$"

@format
class ThreadTimeFormat(Format):
    "MM-DD HH:MM:SS.mmm   PID   TID I ONCRPC  : rpc_handle_rpc_call: Find Status: 0 Xid: 7062"
    NAME = "threadtime"
    PATTERN = r"^" + TimeFormat.DATE_TIME_PATTERN + r"\s+" + \
              BriefFormat.PID_PATTERN + r"\s+" + \
              r"(?P<tid>\d+)\s+" + \
              BriefFormat.PRIORITY_PATTERN + r"\s+" + \
              r"(?P<tag>.*?)\s*: " + \
              BriefFormat.MESSAGE_PATTERN + r"$"

@format
class LongFormat(Format):
    "[ MM-DD HH:MM:SS.mmm   PID:TID I/Tag ]\nmessage"
    NAME = "long"
    PATTERN = r"^\[ " + TimeFormat.DATE_TIME_PATTERN + r"\s+" + \
                   ThreadFormat.PID_TID_HEX_PATTERN + r"\s+" + \
                   BriefFormat.PRIORITY_TAG_PATTERN + r"\s+\]$"

    def match(self, line):
        if not Format.match(self, line):
            self.data["message"] = line

        return "message" in self.data and "tag" in self.data

"""
A helper to detect the log format from a list of lines
"""
def detect_format(lines):
    if len(lines) == 0:
        return None

    for line in lines:
        if Format.MARKER_REGEX.match(line):
            continue

        for name, regex in Format.REGEXES.iteritems():
            if regex.match(line):
                return name

    return None

########NEW FILE########
__FILENAME__ = layout
"""
logcat-color

Copyright 2012, Marshall Culpepper
Licensed under the Apache License, Version 2.0

Layouts for mapping logcat log data into a colorful terminal interface
"""
from colorama import Fore, Back, Style
from logcatcolor.column import *
from logcatcolor.format import Format
import re
from cStringIO import StringIO

def layout(cls):
    Layout.TYPES[cls.NAME] = cls
    return cls

class Layout(object):
    TYPES = {}
    MARKER_LAYOUT = Fore.WHITE + Back.BLACK + Style.DIM + "%s" + Style.RESET_ALL

    def __init__(self, config=None, profile=None, width=2000):
        self.columns = []
        self.config = config
        self.profile = profile
        self.width = width

        self.total_column_width = 0
        if self.COLUMNS:
            # first get the total column width, then construct each column
            for ColumnType in self.COLUMNS:
                if config:
                    self.total_column_width += config.get_column_width(ColumnType)
                else:
                    self.total_column_width += ColumnType.DEFAULT_WIDTH

            for ColumnType in self.COLUMNS:
                column = ColumnType(self)
                self.columns.append(column)

        self.column_count = len(self.columns)

    def layout_marker(self, line):
        return self.MARKER_LAYOUT % line

    def layout_data(self, data):
        formatted = StringIO()
        for index in range(0, self.column_count):
            column = self.columns[index]
            formatted.write(column.format(data[column.NAME]))
            if index < self.column_count - 1:
                formatted.write(" ")

        return formatted.getvalue()

@layout
class RawLayout(Layout):
    NAME = "raw"
    COLUMNS = None

    def layout_marker(self, line):
        return line

    def layout_data(self, data):
       return data["line"]

@layout
class BriefLayout(Layout):
    NAME = "brief"
    COLUMNS = (PIDColumn, TagColumn, PriorityColumn, MessageColumn)

@layout
class ProcessLayout(Layout):
    NAME = "process"
    COLUMNS = BriefLayout.COLUMNS

@layout
class TagLayout(Layout):
    NAME = "tag"
    COLUMNS = (TagColumn, PriorityColumn, MessageColumn)

@layout
class ThreadLayout(Layout):
    NAME = "thread"
    COLUMNS = (PIDColumn, TIDColumn, PriorityColumn, MessageColumn)

@layout
class TimeLayout(Layout):
    NAME = "time"
    COLUMNS = (DateColumn, TimeColumn, ) + BriefLayout.COLUMNS

@layout
class ThreadTimeLayout(Layout):
    NAME = "threadtime"
    COLUMNS = (DateColumn, TimeColumn, PIDColumn, TIDColumn, TagColumn, PriorityColumn, MessageColumn)

@layout
class LongLayout(Layout):
    NAME = "long"
    COLUMNS = ThreadTimeLayout.COLUMNS

########NEW FILE########
__FILENAME__ = profile
import re

RegexType = type(re.compile(""))

class Profile(object):
    __profiles__ = {}

    @classmethod
    def get_profile(cls, name):
        return cls.__profiles__.get(name, None)

    def __init__(self, name=None, tags=None, priorities=None, filters=None,
            buffers=None, wrap=True, device=None, emulator=None, format=None,
            packages=None):
        if not name:
            raise Exception("Profile is missing a name")

        self.name = name
        self.__profiles__[name] = self

        self.init_tags(tags)
        self.init_priorities(priorities)
        self.init_filters(filters)
        self.init_packages(packages)
        self.buffers = buffers
        self.wrap = wrap
        self.device = device
        self.emulator = emulator
        self.format = format

    def init_packages(self, packages):

        self.pid_map = {}
        self.package_search = {}
        
        if packages:
            for package in packages:
                search_string = 'Start proc ' + package
                regex = re.compile(search_string + ".*?pid=(\\d+)", re.IGNORECASE|re.DOTALL)
                self.package_search[package] = (search_string, regex)

    def init_tags(self, tags):
        self.tags = None
        self.tag_colors = None
        if isinstance(tags, dict):
            self.tags = tags.keys()
            self.tag_colors = tags
        elif isinstance(tags, (list, tuple)):
            self.tags = tags
        elif tags:
            self.tags = (tags)

    def init_priorities(self, priorities):
        self.priorities = None
        if isinstance(priorities, (list, tuple)):
            self.priorities = priorities
        elif priorities:
            self.priorities = (priorities)

    def init_filters(self, filters):
        self.filters = []
        if not filters:
            return

        if not isinstance(filters, (list, tuple)):
            filters = [filters]

        for filter in filters:
            if isinstance(filter, (str, RegexType)):
                self.filters.append(self.regex_filter(filter))
            else:
                self.filters.append(filter)

    def regex_filter(self, regex):
        pattern = regex
        if not isinstance(regex, RegexType):
            pattern = re.compile(regex)

        def __filter(data):
            if "message" not in data:
                return True
            return pattern.search(data["message"])
        return __filter

    def process_new_pid(self, data):
        string = data.get('message')
        if string and string.startswith('Start proc'):
            for package in self.package_search:
                match = self.package_search[package][1].search(string)
                if match:
                    self.pid_map[package] = match.group(1)

    def include(self, data):
        if not data:
            raise Exception("data should not be None")

        self.process_new_pid(data)  #process pid

        if self.tags and data.get("tag") not in self.tags:
            return False

        if self.priorities and data.get("priority") not in self.priorities:
            return False

        if self.package_search and data.get("pid") not in self.pid_map.values():
            return False

        if not self.filters:
            return True

        for filter in self.filters:
            if not filter(data):
                return False

        return True

########NEW FILE########
__FILENAME__ = reader
"""
logcat-color

Copyright 2012, Marshall Culpepper
Licensed under the Apache License, Version 2.0

Logcat I/O stream readers and helpers
"""
import asyncore
import asynchat
from cStringIO import StringIO
import fcntl
import inspect
from logcatcolor.format import Format, detect_format
from logcatcolor.layout import Layout
import os
import sys
import traceback

# Parts copied from asyncore.file_dispatcher
class FileLineReader(asynchat.async_chat):
    LINE_TERMINATOR = "\n"

    def __init__(self, fd):
        asynchat.async_chat.__init__(self)
        self.connected = True
        self.log_buffer = StringIO()

        self.set_file(fd)
        self.set_terminator(self.LINE_TERMINATOR)

    def set_file(self, fd):
        try:
            # fd may be a file object
            fd = fd.fileno()
        except AttributeError:
            pass

        self.socket = asyncore.file_wrapper(fd)
        self._fileno = self.socket.fileno()
        self.add_channel()

        flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
        flags = flags | os.O_NONBLOCK
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)

    def collect_incoming_data(self, data):
        self.log_buffer.write(data)

    def found_terminator(self):
        line = self.log_buffer.getvalue()
        try:
            self.process_line(line)
        except:
            traceback.print_exc()
            sys.exit(1)

        self.log_buffer = StringIO()

    def process_line(self):
        pass

class LogcatReader(FileLineReader):
    DETECT_COUNT = 3

    def __init__(self, file, config, profile=None, format=None, layout=None,
                 writer=None, width=80):
        FileLineReader.__init__(self, file)
        self.detect_lines = []
        self.config = config
        self.profile = profile
        self.width = width
        self.writer = writer or sys.stdout

        self.format = None
        if format is not None:
            FormatType = Format.TYPES[format]
            self.format = FormatType()

        self.layout = None
        if layout is not None:
            LayoutType = Layout.TYPES[layout]
            self.layout = LayoutType(config, profile, width)

    def __del__(self):
        # Clear the "detect" lines if we weren't able to detect a format
        if len(self.detect_lines) > 0 and not self.format:
            self.format = BriefFormat()
            if not self.layout:
                self.layout = BriefLayout()

            for line in self.detect_lines:
                self.layout_line(line)

    def detect_format(self, line):
        if len(self.detect_lines) < self.DETECT_COUNT:
            self.detect_lines.append(line)
            return False

        format_name = detect_format(self.detect_lines) or "brief"
        self.format = Format.TYPES[format_name]()
        if not self.layout:
            self.layout = Layout.TYPES[format_name](self.config, self.profile,
                self.width)

        for line in self.detect_lines:
            self.layout_line(line)

        self.detect_lines = []
        return True

    def process_line(self, line):
        line = line.strip()
        if not self.format:
            if not self.detect_format(line):
                return

        self.layout_line(line)

    def layout_line(self, line):
        if Format.MARKER_REGEX.match(line):
            result = self.layout.layout_marker(line)
            if result:
                self.writer.write(result)
            return

        try:
            if not self.format.match(line) or not self.format.include(self.profile):
                return

            result = self.layout.layout_data(self.format.data)
            if not result:
                return

            self.writer.write(result + "\n")
        finally:
            self.format.data.clear()

########NEW FILE########
__FILENAME__ = release
#!/usr/bin/env python

import base64
import collections
import httplib
import json
import mimetypes
import os
import sys
import subprocess

mimetypes.init()
this_dir = os.path.dirname(os.path.abspath(__file__))
dist_dir = os.path.join(this_dir, "dist")
setup_py = os.path.join(this_dir, "setup.py")

def ordered_hook(pairs):
    ordered = collections.OrderedDict()
    for pair in pairs:
        ordered[pair[0]] = pair[1]
    return ordered

class ReleaseCommand(object):
    def __init__(self):
        self.package = json.load(open("setup.json", "r"),
                object_pairs_hook = ordered_hook)

        self.tarball_name = "%s-%s.tar.gz" % \
            (self.package["name"], self.package["version"])

        self.tarball = os.path.join(dist_dir, self.tarball_name)

    def run(self, *args):
        print "-> %s" % " ".join(args)
        return subprocess.check_output(args)

    def read_access_token(self):
        access_token = self.run("git", "config", "github.files.accesstoken")
        self.access_token = access_token.strip()

    def github_api(self, path, data):
        body = json.dumps(data)
        connection = httplib.HTTPSConnection("api.github.com")
        auth = base64.encodestring('%s:%s' % (self.access_token, 'x-oauth-basic')).replace('\n', '')
        connection.request("POST", path, body, {
            "Authorization": "Basic %s" % auth,
        })

        response = connection.getresponse()
        response_body = response.read()
        connection.close()

        data = json.loads(response_body)
        if "errors" in data:
            print >>sys.stderr, "Github Response Failed: %s" % data["message"]
            for error in data["errors"]:
                print >>sys.stderr, "    Error: %s\n" % error["code"]
        return data

    def github_upload(self):
        self.read_access_token()
        description = "%s version %s" % \
            (self.package["name"], self.package["version"])

        data = self.github_api("/repos/marshall/logcat-color/releases", {
            "tag_name": "v%s" % self.package["version"],
            "name": self.package["version"],
            "body": description,
        })

        print data

        upload_url = data["upload_url"].replace("{?name}", "?name=%s" % self.tarball_name)

        self.run("curl",
            "-u", "%s:x-oauth-basic" % self.access_token,
            "-F", "Content-Type=%s" % mimetypes.guess_type(self.tarball)[0],
            "-F", "file=@%s" % self.tarball,
            upload_url)

    def help(self):
        print """
Usage: %s <command> [args]
Supported commands:
    help            view this help message
    build           build source distribution tarball
    push            push the release tarball to github and pypi, and push git tags
    bump [version]  bump to [version] in setup.json, stage, and prepare a commit message
""" % sys.argv[0]

    def build(self):
        # build sdist
        self.run(sys.executable, setup_py, "sdist")

        print "%s succesfully built. to tag, use %s tag\n" % \
            (self.tarball_name, sys.argv[0])

    def push(self):
        # upload source tarball->github, and setup.py upload for pypi
        self.github_upload()
        self.run(sys.executable, setup_py, "sdist", "upload")

        print "%s successfully uploaded, and v%s tag pushed. to bump, use %s bump\n" % \
            (self.tarball_name, self.package["version"], sys.argv[0])

    def bump(self):
        if len(sys.argv) < 3:
            print >>sys.stderr, "Error: bump requires a version to bump to"
            sys.exit(1)

        bump_version = sys.argv[2]
        self.package["version"] = bump_version

        setup_json = json.dumps(self.package,
            separators = (',', ': '),
            indent = 4)

        open("setup.json", "w").write(setup_json)
        message = "bump to version %s" % bump_version

        self.run("git", "add", "setup.json")

        # TODO -- full path is needed for execv, detect this
        git = "/usr/bin/git"
        os.execv(git, (git, "commit", "-v", "-m", message, "-e"))

    def main(self):
        command = "help"
        if len(sys.argv) > 1:
            command = sys.argv[1]

        if command == "help":
            self.help()
        elif command == "build":
            self.build()
        elif command == "tag":
            self.tag()
        elif command == "push":
            self.push()
        elif command == "bump":
            self.bump()


if __name__ == "__main__":
  ReleaseCommand().main()

########NEW FILE########
__FILENAME__ = common
import json
import os

this_dir = os.path.abspath(os.path.dirname(__file__))
top_dir = os.path.dirname(this_dir)
logcat_color = os.path.join(top_dir, "logcat-color")
execfile(logcat_color)

filter_results = os.path.join(this_dir, ".filter_results")
mock_adb = os.path.join(this_dir, "mock-adb")

class MockObject(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

class MockAdbLogcatColor(LogcatColor):
    def __init__(self, log, results, args=None, max_wait_count=None):
        LogcatColor.__init__(self, args=args)
        self.log = log
        self.results = results
        self.wait_count = 0
        self.max_wait_count = max_wait_count

    def get_adb_args(self):
        adb_args = LogcatColor.get_adb_args(self)
        adb_args[0:1] = [mock_adb, "--log", self.log, "--results", self.results]
        return adb_args

    def wait_for_device(self):
        LogcatColor.wait_for_device(self)
        if self.max_wait_count:
            self.wait_count += 1
            if self.wait_count == self.max_wait_count:
                raise KeyboardInterrupt()

def test_filter(fn):
    def wrapped(data):
        result = fn(data)
        save_filter_results(fn.__name__, data, result)
        return result
    return wrapped

def save_filter_results(name, data, result):
    results = read_filter_results()
    if name not in results:
        results[name] = []

    results[name].append({
        "data": data,
        "result": result
    })

    open(filter_results, "w").write(json.dumps(results))

def read_filter_results():
    results = {}
    if os.path.exists(filter_results):
        results = json.loads(open(filter_results, "r").read())

    return results

########NEW FILE########
__FILENAME__ = config_test
from common import *
from logcatcolor.column import *
from logcatcolor.config import *
from logcatcolor.layout import *
from logcatcolor.profile import *
from logcatcolor.reader import *
import unittest

this_dir = os.path.abspath(os.path.dirname(__file__))
configs_dir = os.path.join(this_dir, "configs")

def config_test(config_file, wrap=None, stay_connected=None):
    def run_config_test(fn):
        def wrapped(self):
            path = os.path.join(configs_dir, config_file)
            options = MockObject(config=path,
                                 wrap=wrap,
                                 stay_connected=stay_connected)
            fn(self, LogcatColorConfig(options))
        return wrapped
    return run_config_test

class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tag_column = MockObject(NAME="tag", DEFAULT_WIDTH=20)

    @config_test("")
    def test_default_config(self, config):
        self.assertEqual(config.get_default_layout(), config.DEFAULT_LAYOUT)
        self.assertEqual(config.get_column_width(self.tag_column), 20)
        self.assertEqual(config.get_wrap(), config.DEFAULT_WRAP)
        self.assertEqual(config.get_adb(), config.DEFAULT_ADB)
        self.assertEqual(config.get_stay_connected(), config.DEFAULT_STAY_CONNECTED)

    @config_test("simple_config")
    def test_simple_config(self, config):
        self.assertEqual(config.get_default_layout(), "test")
        self.assertEqual(config.get_column_width(self.tag_column), 1)
        self.assertFalse(config.get_wrap())
        self.assertEqual(config.get_adb(), "/path/to/adb")
        self.assertEqual(config.get_stay_connected(), True)

    @config_test("simple_config", wrap=True, stay_connected=True)
    def test_simple_config_overrides(self, config):
        self.assertTrue(config.get_wrap())
        self.assertTrue(config.get_stay_connected())

########NEW FILE########
__FILENAME__ = format_test
from common import *
from logcatcolor.format import *
import unittest

MARKER_LINE = "--------- beginning of /dev/log/main"
BRIEF_LINE  = "I/Tag(  123): message"
PROCESS_LINE = "I(  123) message (Tag)"
TAG_LINE = "I/Tag  : message"
THREAD_LINE = "I(  123:0x123) message"
TIME_LINE = "01-02 12:34:56.000 D/Tag(  123): message"
THREAD_TIME_LINE = "01-02 12:34:56.000   123   456 I Tag  : message"
LONG_LINES = ["[ 01-02 12:34:56.000   123:0x123 I/Tag ]", "message"]

def format_test(FormatType):
    def run_format_test(fn):
        def wrapped(self):
            fn(self, FormatType())
        return wrapped
    return run_format_test

class FormatTest(unittest.TestCase):
    @format_test(BriefFormat)
    def test_marker(self, format):
        self.assertNotEqual(Format.MARKER_REGEX.match(MARKER_LINE), None)

    @format_test(BriefFormat)
    def test_brief_format(self, format):
        self.assertTrue(format.match(BRIEF_LINE))
        self.assertEqual(format.get("priority"), "I")
        self.assertEqual(format.get("tag"), "Tag")
        self.assertEqual(format.get("pid"), "123")
        self.assertEqual(format.get("message"), "message")
        self.assertEqual(format.get("tid"), None)
        self.assertEqual(format.get("date"), None)
        self.assertEqual(format.get("time"), None)

    @format_test(ProcessFormat)
    def test_process_format(self, format):
        self.assertTrue(format.match(PROCESS_LINE))
        self.assertEqual(format.get("priority"), "I")
        self.assertEqual(format.get("tag"), "Tag")
        self.assertEqual(format.get("pid"), "123")
        self.assertEqual(format.get("message"), "message")
        self.assertEqual(format.get("tid"), None)
        self.assertEqual(format.get("date"), None)
        self.assertEqual(format.get("time"), None)

    @format_test(TagFormat)
    def test_tag_format(self, format):
        self.assertTrue(format.match(TAG_LINE))
        self.assertEqual(format.get("priority"), "I")
        self.assertEqual(format.get("tag"), "Tag")
        self.assertEqual(format.get("message"), "message")
        self.assertEqual(format.get("pid"), None)
        self.assertEqual(format.get("tid"), None)
        self.assertEqual(format.get("date"), None)
        self.assertEqual(format.get("time"), None)

    @format_test(ThreadFormat)
    def test_thread_format(self, format):
        self.assertTrue(format.match(THREAD_LINE))
        self.assertEqual(format.get("priority"), "I")
        self.assertEqual(format.get("pid"), "123")
        self.assertEqual(format.get("tid"), "0x123")
        self.assertEqual(format.get("message"), "message")
        self.assertEqual(format.get("tag"), None)
        self.assertEqual(format.get("date"), None)
        self.assertEqual(format.get("time"), None)

    @format_test(TimeFormat)
    def test_time_format(self, format):
        self.assertTrue(format.match(TIME_LINE))
        self.assertEqual(format.get("priority"), "D")
        self.assertEqual(format.get("pid"), "123")
        self.assertEqual(format.get("message"), "message")
        self.assertEqual(format.get("tag"), "Tag")
        self.assertEqual(format.get("date"), "01-02")
        self.assertEqual(format.get("time"), "12:34:56.000")
        self.assertEqual(format.get("tid"), None)

    @format_test(ThreadTimeFormat)
    def test_thread_time_format(self, format):
        self.assertTrue(format.match(THREAD_TIME_LINE))
        self.assertEqual(format.get("priority"), "I")
        self.assertEqual(format.get("tag"), "Tag")
        self.assertEqual(format.get("pid"), "123")
        self.assertEqual(format.get("tid"), "456")
        self.assertEqual(format.get("message"), "message")
        self.assertEqual(format.get("date"), "01-02")
        self.assertEqual(format.get("time"), "12:34:56.000")

    @format_test(LongFormat)
    def test_long_format(self, format):
        self.assertFalse(format.match(LONG_LINES[0]))
        self.assertTrue(format.match(LONG_LINES[1]))

        self.assertEqual(format.get("priority"), "I")
        self.assertEqual(format.get("tag"), "Tag")
        self.assertEqual(format.get("pid"), "123")
        self.assertEqual(format.get("tid"), "0x123")
        self.assertEqual(format.get("date"), "01-02")
        self.assertEqual(format.get("time"), "12:34:56.000")
        self.assertEqual(format.get("message"), "message")

    def test_detect_format(self):
        self.assertEqual(detect_format([MARKER_LINE, BRIEF_LINE]), "brief")
        self.assertEqual(detect_format([MARKER_LINE, PROCESS_LINE]), "process")
        self.assertEqual(detect_format([MARKER_LINE, TAG_LINE]), "tag")
        self.assertEqual(detect_format([MARKER_LINE, THREAD_LINE]), "thread")
        self.assertEqual(detect_format([MARKER_LINE, TIME_LINE]), "time")
        self.assertEqual(detect_format([MARKER_LINE, THREAD_TIME_LINE]), "threadtime")
        self.assertEqual(detect_format([MARKER_LINE, LONG_LINES[0], LONG_LINES[1]]), "long")
        self.assertEqual(detect_format([MARKER_LINE]), None)

########NEW FILE########
__FILENAME__ = logcat_color_test
import common
import json
import os
from StringIO import StringIO
from subprocess import Popen, PIPE
import sys
import tempfile
import unittest

from common import LogcatColor, MockAdbLogcatColor
this_dir = os.path.dirname(os.path.abspath(__file__))

def logcat_color_test(*args, **kwargs):
    def run_logcat_color_test(fn):
        def wrapped(self):
            self.start_logcat_color(*args, **kwargs)
            fn(self)
        return wrapped
    return run_logcat_color_test

logs_dir = os.path.join(this_dir, "logs")
configs_dir = os.path.join(this_dir, "configs")

BRIEF_LOG = os.path.join(logs_dir, "brief_log")
BRIEF_FILTER_CONFIG = os.path.join(configs_dir, "brief_filter_config")
EMPTY_CONFIG = os.path.join(configs_dir, "empty_config")

tmpfd, tmpout = tempfile.mkstemp()
os.close(tmpfd)

class LogcatColorTest(unittest.TestCase):
    DEBUG = False

    def setUp(self):
        # Clear out our temporary output file before each test
        global tmpout
        with open(tmpout, "w") as f: f.write("")

    def start_logcat_color(self, *args, **kwargs):
        args = list(args)
        args.insert(0, common.logcat_color)
        if "config" in kwargs:
            args[1:1] = ["--config", kwargs["config"]]
            del kwargs["config"]
        elif "--config" not in args:
            # fall back to empty config
            args[1:1] = ["--config", EMPTY_CONFIG]

        piped = ""
        piped_path = None
        if "piped" in kwargs:
            piped_path = kwargs["piped"]
            piped = open(piped_path, "r").read()
            del kwargs["piped"]
        elif "input" in kwargs:
            piped = None
            args[1:1] = ["--input", kwargs["input"]]
            del kwargs["input"]

        if self.DEBUG:
            piped_debug = ""
            if piped_path:
                piped_debug = " < %s" % piped_path

            print " ".join(args) + piped_debug

        self.proc = Popen(args, stdout=PIPE, stderr=PIPE, stdin=PIPE, **kwargs)
        self.out, self.err = self.proc.communicate(piped)

        self.filter_results = common.read_filter_results()
        if os.path.exists(common.filter_results):
            os.unlink(common.filter_results)

        if self.DEBUG and self.err:
            print >>sys.stderr, self.err

    @logcat_color_test(piped=BRIEF_LOG)
    def test_piped_input(self):
        self.assertEqual(self.proc.returncode, 0)

    @logcat_color_test(config="/does/not/exist")
    def test_invalid_config(self):
        self.assertNotEqual(self.proc.returncode, 0)

    @logcat_color_test("--plain", input=BRIEF_LOG)
    def test_plain_logging(self):
        self.assertEqual(self.proc.returncode, 0)
        brief_data = open(BRIEF_LOG, "r").read()
        self.assertEqual(self.out, brief_data)

    @logcat_color_test("--plain", "brief_filter_fn",
        input=BRIEF_LOG, config=BRIEF_FILTER_CONFIG)
    def test_plain_logging_with_fn_filter(self):
        self.assertEqual(self.proc.returncode, 0)
        self.assertTrue("(  123)" not in self.out)
        self.assertTrue("( 890)" not in self.out)
        self.assertTrue("( 234)" in self.out)
        self.assertTrue("( 567)" in self.out)

        filter_results = self.filter_results.get("brief_filter_fn")
        self.assertNotEqual(filter_results, None)
        self.assertEqual(len(filter_results), 4)

        for result in filter_results:
            self.assertTrue("result" in result)
            self.assertTrue("data" in result)

        def assertResult(result, value, priority, tag, pid, msg):
            self.assertTrue("result" in result)
            self.assertEqual(result["result"], value)

            data = result["data"]
            self.assertEqual(data["priority"], priority)
            self.assertEqual(data["tag"], tag)
            self.assertEqual(data["pid"], pid)
            self.assertEqual(data["message"], msg)

        assertResult(filter_results[0], False, "I", "Tag", "123", "message")
        assertResult(filter_results[1], True, "I", "Tag2", "234", "message 2")
        assertResult(filter_results[2], True, "I", "Tag3", "567", "message 3")
        assertResult(filter_results[3], False, "I", "Tag4", "890", "message 4")

    @logcat_color_test("--plain", "brief_filter_tag",
        input=BRIEF_LOG, config=BRIEF_FILTER_CONFIG)
    def test_plain_logging_with_tag_filter(self):
        self.assertEqual(self.proc.returncode, 0)
        self.assertTrue("Tag1" not in self.out)
        self.assertTrue("Tag3" not in self.out)
        self.assertTrue("Tag2" in self.out)
        self.assertTrue("Tag4" in self.out)

    @logcat_color_test("--plain", "--output", tmpout, input=BRIEF_LOG)
    def test_file_output(self):
        self.assertEqual(self.proc.returncode, 0)
        brief_data = open(BRIEF_LOG, "r").read()
        out_data = open(tmpout, "r").read()
        self.assertEqual(out_data, brief_data)

    def test_logcat_options_with_filters(self):
        # Make sure logcat flags come before filter arguments
        # https://github.com/marshall/logcat-color/issues/5
        lc = LogcatColor(args=["-v", "time", "Tag1:V", "*:S", "--silent",
                               "--print-size", "--dump", "--clear"])
        self.assertEqual(lc.format, "time")

        args = lc.get_logcat_args()

        self.assertEqual(len(args), 8)

        format_index = args.index("-v")
        self.assertTrue(format_index >= 0)
        self.assertEqual(args[format_index+1], "time")
        self.assertTrue("-s" in args)
        self.assertTrue("-d" in args)
        self.assertTrue("-g" in args)
        self.assertTrue("-c" in args)

        self.assertEqual(args[-2], "Tag1:V")
        self.assertEqual(args[-1], "*:S")

    def test_stay_connected(self):
        lc = MockAdbLogcatColor(BRIEF_LOG, tmpout,
                                args=["-s", "serial123", "--stay-connected",
                                      "--config", EMPTY_CONFIG],
                                max_wait_count=3)
        self.assertEqual(lc.config.get_stay_connected(), True)

        lc.loop()
        self.assertEqual(lc.wait_count, 3)

        results = json.loads(open(tmpout, "r").read())
        self.assertEqual(len(results), 6)

        logcat_results = filter(lambda d: d["command"] == "logcat", results)
        self.assertEqual(len(logcat_results), 3)

        wait_results = filter(lambda d: d["command"] == "wait-for-device", results)
        self.assertEquals(len(wait_results), 3)

        for r in results:
            self.assertEqual(r["serial"], "serial123")


########NEW FILE########
__FILENAME__ = profile_test
from common import *
from logcatcolor.column import *
from logcatcolor.config import *
from logcatcolor.layout import *
from logcatcolor.profile import *
from logcatcolor.reader import *
import unittest


class ProfileTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_package_name_filter(self):
        profile = Profile(name = 'package_filt', packages = ['com.example.test'])
        self.assertFalse(profile.include({'message' : 'Start proc com.example.test for activity tw.com.xxxx.android.yyyy/.333Activity: pid=123456 uid=10105 gids={3003}'}))
        self.assertTrue(profile.include({'pid' : '123456', 'message' : 'foo bar'}))

    def test_empty_package_will_still_work(self):
        profile = Profile(name = 'package_filt')
        self.assertTrue(profile.include({'message' : 'Start proc com.example.test for activity tw.com.xxxx.android.yyyy/.333Activity: pid=123456 uid=10105 gids={3003}'}))


########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
import os
import sys
import unittest

this_dir = os.path.dirname(os.path.abspath(__file__))
logcat_color_dir = os.path.dirname(this_dir)
sys.path.append(logcat_color_dir)

from format_test import *
from config_test import *
from logcat_color_test import *
from profile_test import *

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
