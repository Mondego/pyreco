__FILENAME__ = conf
# -*- coding: utf-8 -*-

import sys
import os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.append(os.path.join(os.pardir, "tests"))
import kombu

from django.conf import settings
if not settings.configured:
    settings.configure()

# General configuration
# ---------------------

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Kombu'
copyright = '2009-2014, Ask Solem'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ".".join(map(str, kombu.VERSION[0:2]))
# The full version, including alpha/beta/rc tags.
release = kombu.__version__

exclude_trees = ['.build']

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'colorful'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['.static']

html_use_smartypants = True

# If false, no module index is generated.
html_use_modindex = True

# If false, no index is generated.
html_use_index = True

latex_documents = [
    ('index', 'Kombu.tex', 'Kombu Documentation',
     'Ask Solem', 'manual'),
]

html_theme = "celery"
html_theme_path = ["_theme"]
html_sidebars = {
    'index': ['sidebarintro.html', 'sourcelink.html', 'searchbox.html'],
    '**': ['sidebarlogo.html', 'localtoc.html', 'relations.html',
           'sourcelink.html', 'searchbox.html'],
}

########NEW FILE########
__FILENAME__ = applyxrefs
"""Adds xref targets to the top of files."""

import sys
import os

testing = False

DONT_TOUCH = ('./index.txt', )


def target_name(fn):
    if fn.endswith('.txt'):
        fn = fn[:-4]
    return '_' + fn.lstrip('./').replace('/', '-')


def process_file(fn, lines):
    lines.insert(0, '\n')
    lines.insert(0, '.. %s:\n' % target_name(fn))
    try:
        f = open(fn, 'w')
    except IOError:
        print("Can't open %s for writing. Not touching it." % fn)
        return
    try:
        f.writelines(lines)
    except IOError:
        print("Can't write to %s. Not touching it." % fn)
    finally:
        f.close()


def has_target(fn):
    try:
        f = open(fn, 'r')
    except IOError:
        print("Can't open %s. Not touching it." % fn)
        return (True, None)
    readok = True
    try:
        lines = f.readlines()
    except IOError:
        print("Can't read %s. Not touching it." % fn)
        readok = False
    finally:
        f.close()
        if not readok:
            return (True, None)

    if len(lines) < 1:
        print("Not touching empty file %s." % fn)
        return (True, None)
    if lines[0].startswith('.. _'):
        return (True, None)
    return (False, lines)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) == 1:
        argv.extend('.')

    files = []
    for root in argv[1:]:
        for (dirpath, dirnames, filenames) in os.walk(root):
            files.extend([(dirpath, f) for f in filenames])
    files.sort()
    files = [os.path.join(p, fn) for p, fn in files if fn.endswith('.txt')]

    for fn in files:
        if fn in DONT_TOUCH:
            print("Skipping blacklisted file %s." % fn)
            continue

        target_found, lines = has_target(fn)
        if not target_found:
            if testing:
                print '%s: %s' % (fn, lines[0]),
            else:
                print "Adding xref to %s" % fn
                process_file(fn, lines)
        else:
            print "Skipping %s: already has a xref" % fn

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = literals_to_xrefs
"""
Runs through a reST file looking for old-style literals, and helps replace them
with new-style references.
"""

import re
import sys
import shelve

try:
    input = input
except NameError:
    input = raw_input  # noqa

refre = re.compile(r'``([^`\s]+?)``')

ROLES = (
    'attr',
    'class',
    "djadmin",
    'data',
    'exc',
    'file',
    'func',
    'lookup',
    'meth',
    'mod',
    "djadminopt",
    "ref",
    "setting",
    "term",
    "tfilter",
    "ttag",

    # special
    "skip",
)

ALWAYS_SKIP = [
    "NULL",
    "True",
    "False",
]


def fixliterals(fname):
    data = open(fname).read()

    last = 0
    new = []
    storage = shelve.open("/tmp/literals_to_xref.shelve")
    lastvalues = storage.get("lastvalues", {})

    for m in refre.finditer(data):

        new.append(data[last:m.start()])
        last = m.end()

        line_start = data.rfind("\n", 0, m.start())
        line_end = data.find("\n", m.end())
        prev_start = data.rfind("\n", 0, line_start)
        next_end = data.find("\n", line_end + 1)

        # Skip always-skip stuff
        if m.group(1) in ALWAYS_SKIP:
            new.append(m.group(0))
            continue

        # skip when the next line is a title
        next_line = data[m.end():next_end].strip()
        if next_line[0] in "!-/:-@[-`{-~" and \
                all(c == next_line[0] for c in next_line):
            new.append(m.group(0))
            continue

        sys.stdout.write("\n" + "-" * 80 + "\n")
        sys.stdout.write(data[prev_start + 1:m.start()])
        sys.stdout.write(colorize(m.group(0), fg="red"))
        sys.stdout.write(data[m.end():next_end])
        sys.stdout.write("\n\n")

        replace_type = None
        while replace_type is None:
            replace_type = input(
                colorize("Replace role: ", fg="yellow")).strip().lower()
            if replace_type and replace_type not in ROLES:
                replace_type = None

        if replace_type == "":
            new.append(m.group(0))
            continue

        if replace_type == "skip":
            new.append(m.group(0))
            ALWAYS_SKIP.append(m.group(1))
            continue

        default = lastvalues.get(m.group(1), m.group(1))
        if default.endswith("()") and \
                replace_type in ("class", "func", "meth"):
            default = default[:-2]
        replace_value = input(
            colorize("Text <target> [", fg="yellow") +
            default +
            colorize("]: ", fg="yellow"),
        ).strip()
        if not replace_value:
            replace_value = default
        new.append(":%s:`%s`" % (replace_type, replace_value))
        lastvalues[m.group(1)] = replace_value

    new.append(data[last:])
    open(fname, "w").write("".join(new))

    storage["lastvalues"] = lastvalues
    storage.close()


def colorize(text='', opts=(), **kwargs):
    """
    Returns your text, enclosed in ANSI graphics codes.

    Depends on the keyword arguments 'fg' and 'bg', and the contents of
    the opts tuple/list.

    Returns the RESET code if no parameters are given.

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold'
        'underscore'
        'blink'
        'reverse'
        'conceal'
        'noreset' - string will not be auto-terminated with the RESET code

    Examples:
        colorize('hello', fg='red', bg='blue', opts=('blink',))
        colorize()
        colorize('goodbye', opts=('underscore',))
        print colorize('first line', fg='red', opts=('noreset',))
        print 'this should be red too'
        print colorize('and so should this')
        print 'this should not be red'
    """
    color_names = ('black', 'red', 'green', 'yellow',
                   'blue', 'magenta', 'cyan', 'white')
    foreground = dict([(color_names[x], '3%s' % x) for x in range(8)])
    background = dict([(color_names[x], '4%s' % x) for x in range(8)])

    RESET = '0'
    opt_dict = {'bold': '1',
                'underscore': '4',
                'blink': '5',
                'reverse': '7',
                'conceal': '8'}

    text = str(text)
    code_list = []
    if text == '' and len(opts) == 1 and opts[0] == 'reset':
        return '\x1b[%sm' % RESET
    for k, v in kwargs.iteritems():
        if k == 'fg':
            code_list.append(foreground[v])
        elif k == 'bg':
            code_list.append(background[v])
    for o in opts:
        if o in opt_dict:
            code_list.append(opt_dict[o])
    if 'noreset' not in opts:
        text = text + '\x1b[%sm' % RESET
    return ('\x1b[%sm' % ';'.join(code_list)) + text

if __name__ == '__main__':
    try:
        fixliterals(sys.argv[1])
    except (KeyboardInterrupt, SystemExit):
        print

########NEW FILE########
__FILENAME__ = complete_receive
"""
Example of simple consumer that waits for a single message, acknowledges it
and exits.
"""
from kombu import Connection, Exchange, Queue, Consumer, eventloop
from pprint import pformat

#: By default messages sent to exchanges are persistent (delivery_mode=2),
#: and queues and exchanges are durable.
exchange = Exchange('kombu_demo', type='direct')
queue = Queue('kombu_demo', exchange, routing_key='kombu_demo')


def pretty(obj):
    return pformat(obj, indent=4)


#: This is the callback applied when a message is received.
def handle_message(body, message):
    print('Received message: %r' % (body, ))
    print('  properties:\n%s' % (pretty(message.properties), ))
    print('  delivery_info:\n%s' % (pretty(message.delivery_info), ))
    message.ack()

#: Create a connection and a channel.
#: If hostname, userid, password and virtual_host is not specified
#: the values below are the default, but listed here so it can
#: be easily changed.
with Connection('amqp://guest:guest@localhost:5672//') as connection:

    #: Create consumer using our callback and queue.
    #: Second argument can also be a list to consume from
    #: any number of queues.
    with Consumer(connection, queue, callbacks=[handle_message]):

        #: Each iteration waits for a single event.  Note that this
        #: event may not be a message, or a message that is to be
        #: delivered to the consumers channel, but any event received
        #: on the connection.
        for _ in eventloop(connection):
            pass

########NEW FILE########
__FILENAME__ = complete_send
"""

Example producer that sends a single message and exits.

You can use `complete_receive.py` to receive the message sent.

"""
from kombu import Connection, Producer, Exchange, Queue

#: By default messages sent to exchanges are persistent (delivery_mode=2),
#: and queues and exchanges are durable.
exchange = Exchange('kombu_demo', type='direct')
queue = Queue('kombu_demo', exchange, routing_key='kombu_demo')


with Connection('amqp://guest:guest@localhost:5672//') as connection:

    #: Producers are used to publish messages.
    #: a default exchange and routing key can also be specifed
    #: as arguments the Producer, but we rather specify this explicitly
    #: at the publish call.
    producer = Producer(connection)

    #: Publish the message using the json serializer (which is the default),
    #: and zlib compression.  The kombu consumer will automatically detect
    #: encoding, serialization and compression used and decode accordingly.
    producer.publish({'hello': 'world'},
                     exchange=exchange,
                     routing_key='kombu_demo',
                     serializer='json', compression='zlib')

########NEW FILE########
__FILENAME__ = async_consume
#!/usr/bin/env python

from kombu import Connection, Exchange, Queue, Producer, Consumer
from kombu.async import Hub

hub = Hub()
exchange = Exchange('asynt')
queue = Queue('asynt', exchange, 'asynt')


def send_message(conn):
    producer = Producer(conn)
    producer.publish('hello world', exchange=exchange, routing_key='asynt')
    print('MESSAGE SENT')


def on_message(message):
    print('RECEIVED: %r' % (message.body, ))
    message.ack()
    hub.stop()  # <-- exit after one message


if __name__ == '__main__':
    conn = Connection('amqp://')
    conn.register_with_event_loop(hub)

    with Consumer(conn, [queue], on_message=on_message):
        send_message(conn)
        hub.run_forever()

########NEW FILE########
__FILENAME__ = hello_consumer
from kombu import Connection

with Connection('amqp://guest:guest@localhost:5672//') as conn:
    simple_queue = conn.SimpleQueue('simple_queue')
    message = simple_queue.get(block=True, timeout=1)
    print("Received: %s" % message.payload)
    message.ack()
    simple_queue.close()

########NEW FILE########
__FILENAME__ = hello_publisher
from kombu import Connection
import datetime

with Connection('amqp://guest:guest@localhost:5672//') as conn:
    simple_queue = conn.SimpleQueue('simple_queue')
    message = 'helloword, sent at %s' % datetime.datetime.today()
    simple_queue.put(message)
    print('Sent: %s' % message)
    simple_queue.close()

########NEW FILE########
__FILENAME__ = simple_eventlet_receive
"""

Example that sends a single message and exits using the simple interface.

You can use `simple_receive.py` (or `complete_receive.py`) to receive the
message sent.

"""
import eventlet

from kombu import Connection

eventlet.monkey_patch()


def wait_many(timeout=1):

    #: Create connection
    #: If hostname, userid, password and virtual_host is not specified
    #: the values below are the default, but listed here so it can
    #: be easily changed.
    with Connection('amqp://guest:guest@localhost:5672//') as connection:

        #: SimpleQueue mimics the interface of the Python Queue module.
        #: First argument can either be a queue name or a kombu.Queue object.
        #: If a name, then the queue will be declared with the name as the
        #: queue name, exchange name and routing key.
        with connection.SimpleQueue('kombu_demo') as queue:

            while True:
                try:
                    message = queue.get(block=False, timeout=timeout)
                except queue.Empty:
                    break
                else:
                    message.ack()
                    print(message.payload)

eventlet.spawn(wait_many).wait()

########NEW FILE########
__FILENAME__ = simple_eventlet_send
"""

Example that sends a single message and exits using the simple interface.

You can use `simple_receive.py` (or `complete_receive.py`) to receive the
message sent.

"""
import eventlet

from kombu import Connection

eventlet.monkey_patch()


def send_many(n):

    #: Create connection
    #: If hostname, userid, password and virtual_host is not specified
    #: the values below are the default, but listed here so it can
    #: be easily changed.
    with Connection('amqp://guest:guest@localhost:5672//') as connection:

        #: SimpleQueue mimics the interface of the Python Queue module.
        #: First argument can either be a queue name or a kombu.Queue object.
        #: If a name, then the queue will be declared with the name as the
        #: queue name, exchange name and routing key.
        with connection.SimpleQueue('kombu_demo') as queue:

            def send_message(i):
                queue.put({'hello': 'world%s' % (i, )})

            pool = eventlet.GreenPool(10)
            for i in range(n):
                pool.spawn(send_message, i)
            pool.waitall()


if __name__ == '__main__':
    send_many(10)

########NEW FILE########
__FILENAME__ = simple_receive
"""
Example receiving a message using the SimpleQueue interface.
"""

from kombu import Connection

#: Create connection
#: If hostname, userid, password and virtual_host is not specified
#: the values below are the default, but listed here so it can
#: be easily changed.
with Connection('amqp://guest:guest@localhost:5672//') as conn:

    #: SimpleQueue mimics the interface of the Python Queue module.
    #: First argument can either be a queue name or a kombu.Queue object.
    #: If a name, then the queue will be declared with the name as the queue
    #: name, exchange name and routing key.
    with conn.SimpleQueue('kombu_demo') as queue:
        message = queue.get(block=True, timeout=10)
        message.ack()
        print(message.payload)

####
#: If you don't use the with statement then you must aways
# remember to close objects after use:
#   queue.close()
#   connection.close()

########NEW FILE########
__FILENAME__ = simple_send
"""

Example that sends a single message and exits using the simple interface.

You can use `simple_receive.py` (or `complete_receive.py`) to receive the
message sent.

"""
from kombu import Connection

#: Create connection
#: If hostname, userid, password and virtual_host is not specified
#: the values below are the default, but listed here so it can
#: be easily changed.
with Connection('amqp://guest:guest@localhost:5672//') as conn:

    #: SimpleQueue mimics the interface of the Python Queue module.
    #: First argument can either be a queue name or a kombu.Queue object.
    #: If a name, then the queue will be declared with the name as the queue
    #: name, exchange name and routing key.
    with conn.SimpleQueue('kombu_demo') as queue:
        queue.put({'hello': 'world'}, serializer='json', compression='zlib')


#####
# If you don't use the with statement, you must always
# remember to close objects.
#   queue.close()
#   connection.close()

########NEW FILE########
__FILENAME__ = client
from kombu.pools import producers

from .queues import task_exchange

priority_to_routing_key = {'high': 'hipri',
                           'mid': 'midpri',
                           'low': 'lopri'}


def send_as_task(connection, fun, args=(), kwargs={}, priority='mid'):
    payload = {'fun': fun, 'args': args, 'kwargs': kwargs}
    routing_key = priority_to_routing_key[priority]

    with producers[connection].acquire(block=True) as producer:
        producer.publish(payload,
                         serializer='pickle',
                         compression='bzip2',
                         exchange=task_exchange,
                         declare=[task_exchange],
                         routing_key=routing_key)

if __name__ == '__main__':
    from kombu import Connection
    from .tasks import hello_task

    connection = Connection('amqp://guest:guest@localhost:5672//')
    send_as_task(connection, fun=hello_task, args=('Kombu', ), kwargs={},
                 priority='high')

########NEW FILE########
__FILENAME__ = queues
from kombu import Exchange, Queue

task_exchange = Exchange('tasks', type='direct')
task_queues = [Queue('hipri', task_exchange, routing_key='hipri'),
               Queue('midpri', task_exchange, routing_key='midpri'),
               Queue('lopri', task_exchange, routing_key='lopri')]

########NEW FILE########
__FILENAME__ = tasks
def hello_task(who="world"):
    print("Hello %s" % (who, ))

########NEW FILE########
__FILENAME__ = worker
from kombu.mixins import ConsumerMixin
from kombu.log import get_logger
from kombu.utils import reprcall

from .queues import task_queues

logger = get_logger(__name__)


class Worker(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=task_queues,
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task])]

    def process_task(self, body, message):
        fun = body['fun']
        args = body['args']
        kwargs = body['kwargs']
        logger.info('Got task: %s', reprcall(fun.__name__, args, kwargs))
        try:
            fun(*args, **kwargs)
        except Exception as exc:
            logger.error('task raised exception: %r', exc)
        message.ack()

if __name__ == '__main__':
    from kombu import Connection
    from kombu.utils.debug import setup_logging
    # setup root logger
    setup_logging(loglevel='INFO', loggers=[''])

    with Connection('amqp://guest:guest@localhost:5672//') as conn:
        try:
            worker = Worker(conn)
            worker.run()
        except KeyboardInterrupt:
            print('bye bye')

########NEW FILE########
__FILENAME__ = bump_version
#!/usr/bin/env python
from __future__ import absolute_import

import errno
import os
import re
import sys
import subprocess

from contextlib import contextmanager
from tempfile import NamedTemporaryFile

rq = lambda s: s.strip("\"'")
str_t = str if sys.version_info[0] >= 3 else basestring


def cmd(*args):
    return subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]


@contextmanager
def no_enoent():
    try:
        yield
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise


class StringVersion(object):

    def decode(self, s):
        s = rq(s)
        text = ""
        major, minor, release = s.split(".")
        if not release.isdigit():
            pos = release.index(re.split("\d+", release)[1][0])
            release, text = release[:pos], release[pos:]
        return int(major), int(minor), int(release), text

    def encode(self, v):
        return ".".join(map(str, v[:3])) + v[3]
to_str = StringVersion().encode
from_str = StringVersion().decode


class TupleVersion(object):

    def decode(self, s):
        v = list(map(rq, s.split(", ")))
        return (tuple(map(int, v[0:3])) +
                tuple(["".join(v[3:])]))

    def encode(self, v):
        v = list(v)

        def quote(lit):
            if isinstance(lit, str_t):
                return '"%s"' % (lit, )
            return str(lit)

        if not v[-1]:
            v.pop()
        return ", ".join(map(quote, v))


class VersionFile(object):

    def __init__(self, filename):
        self.filename = filename
        self._kept = None

    def _as_orig(self, version):
        return self.wb % {"version": self.type.encode(version),
                          "kept": self._kept}

    def write(self, version):
        pattern = self.regex
        with no_enoent():
            with NamedTemporaryFile() as dest:
                with open(self.filename) as orig:
                    for line in orig:
                        if pattern.match(line):
                            dest.write(self._as_orig(version))
                        else:
                            dest.write(line)
                os.rename(dest.name, self.filename)

    def parse(self):
        pattern = self.regex
        gpos = 0
        with open(self.filename) as fh:
            for line in fh:
                m = pattern.match(line)
                if m:
                    if "?P<keep>" in pattern.pattern:
                        self._kept, gpos = m.groupdict()["keep"], 1
                    return self.type.decode(m.groups()[gpos])


class PyVersion(VersionFile):
    regex = re.compile(r'^VERSION\s*=\s*\((.+?)\)')
    wb = "VERSION = (%(version)s)\n"
    type = TupleVersion()


class SphinxVersion(VersionFile):
    regex = re.compile(r'^:[Vv]ersion:\s*(.+?)$')
    wb = ':Version: %(version)s\n'
    type = StringVersion()


class CPPVersion(VersionFile):
    regex = re.compile(r'^\#\s*define\s*(?P<keep>\w*)VERSION\s+(.+)')
    wb = '#define %(kept)sVERSION "%(version)s"\n'
    type = StringVersion()


_filetype_to_type = {"py": PyVersion,
                     "rst": SphinxVersion,
                     "c": CPPVersion,
                     "h": CPPVersion}


def filetype_to_type(filename):
    _, _, suffix = filename.rpartition(".")
    return _filetype_to_type[suffix](filename)


def bump(*files, **kwargs):
    version = kwargs.get("version")
    files = [filetype_to_type(f) for f in files]
    versions = [v.parse() for v in files]
    current = list(reversed(sorted(versions)))[0]  # find highest

    if version:
        next = from_str(version)
    else:
        major, minor, release, text = current
        if text:
            raise Exception("Can't bump alpha releases")
        next = (major, minor, release + 1, text)

    print("Bump version from %s -> %s" % (to_str(current), to_str(next)))

    for v in files:
        print("  writing %r..." % (v.filename, ))
        v.write(next)

    print(cmd("git", "commit", "-m", "Bumps version to %s" % (to_str(next), ),
          *[f.filename for f in files]))
    print(cmd("git", "tag", "v%s" % (to_str(next), )))


def main(argv=sys.argv, version=None):
    if not len(argv) > 1:
        print("Usage: distdir [docfile] -- <custom version>")
        sys.exit(0)
    if "--" in argv:
        c = argv.index('--')
        version = argv[c + 1]
        argv = argv[:c]
    bump(*argv[1:], version=version)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = flakeplus
#!/usr/bin/env python
from __future__ import absolute_import

import os
import re
import sys

from collections import defaultdict
from unipath import Path

RE_COMMENT = r'^\s*\#'
RE_NOQA = r'.+?\#\s+noqa+'
RE_MULTILINE_COMMENT_O = r'^\s*(?:\'\'\'|""").+?(?:\'\'\'|""")'
RE_MULTILINE_COMMENT_S = r'^\s*(?:\'\'\'|""")'
RE_MULTILINE_COMMENT_E = r'(?:^|.+?)(?:\'\'\'|""")'
RE_WITH = r'(?:^|\s+)with\s+'
RE_WITH_IMPORT = r'''from\s+ __future__\s+ import\s+ with_statement'''
RE_PRINT = r'''(?:^|\s+)print\((?:"|')(?:\W+?)?[A-Z0-9:]{2,}'''
RE_ABS_IMPORT = r'''from\s+ __future__\s+ import\s+ absolute_import'''

acc = defaultdict(lambda: {"abs": False, "print": False})


def compile(regex):
    return re.compile(regex, re.VERBOSE)


class FlakePP(object):
    re_comment = compile(RE_COMMENT)
    re_ml_comment_o = compile(RE_MULTILINE_COMMENT_O)
    re_ml_comment_s = compile(RE_MULTILINE_COMMENT_S)
    re_ml_comment_e = compile(RE_MULTILINE_COMMENT_E)
    re_abs_import = compile(RE_ABS_IMPORT)
    re_print = compile(RE_PRINT)
    re_with_import = compile(RE_WITH_IMPORT)
    re_with = compile(RE_WITH)
    re_noqa = compile(RE_NOQA)
    map = {"abs": True, "print": False,
           "with": False, "with-used": False}

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.steps = (("abs", self.re_abs_import),
                      ("with", self.re_with_import),
                      ("with-used", self.re_with),
                      ("print", self.re_print))

    def analyze_fh(self, fh):
        steps = self.steps
        filename = fh.name
        acc = dict(self.map)
        index = 0
        errors = [0]

        def error(fmt, **kwargs):
            errors[0] += 1
            self.announce(fmt, **dict(kwargs, filename=filename))

        for index, line in enumerate(self.strip_comments(fh)):
            for key, pattern in steps:
                if pattern.match(line):
                    acc[key] = True
        if index:
            if not acc["abs"]:
                error("%(filename)s: missing abs import")
            if acc["with-used"] and not acc["with"]:
                error("%(filename)s: missing with import")
            if acc["print"]:
                error("%(filename)s: left over print statement")

        return filename, errors[0], acc

    def analyze_file(self, filename):
        with open(filename) as fh:
            return self.analyze_fh(fh)

    def analyze_tree(self, dir):
        for dirpath, _, filenames in os.walk(dir):
            for path in (Path(dirpath, f) for f in filenames):
                if path.endswith(".py"):
                    yield self.analyze_file(path)

    def analyze(self, *paths):
        for path in map(Path, paths):
            if path.isdir():
                for res in self.analyze_tree(path):
                    yield res
            else:
                yield self.analyze_file(path)

    def strip_comments(self, fh):
        re_comment = self.re_comment
        re_ml_comment_o = self.re_ml_comment_o
        re_ml_comment_s = self.re_ml_comment_s
        re_ml_comment_e = self.re_ml_comment_e
        re_noqa = self.re_noqa
        in_ml = False

        for line in fh.readlines():
            if in_ml:
                if re_ml_comment_e.match(line):
                    in_ml = False
            else:
                if re_noqa.match(line) or re_ml_comment_o.match(line):
                    pass
                elif re_ml_comment_s.match(line):
                    in_ml = True
                elif re_comment.match(line):
                    pass
                else:
                    yield line

    def announce(self, fmt, **kwargs):
        sys.stderr.write((fmt + "\n") % kwargs)


def main(argv=sys.argv, exitcode=0):
    for _, errors, _ in FlakePP(verbose=True).analyze(*argv[1:]):
        if errors:
            exitcode = 1
    return exitcode


if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = test_amqp
from funtests import transport


class test_pyamqp(transport.TransportCase):
    transport = 'pyamqp'
    prefix = 'pyamqp'

########NEW FILE########
__FILENAME__ = test_amqplib
from nose import SkipTest

from funtests import transport


class test_amqplib(transport.TransportCase):
    transport = 'amqplib'
    prefix = 'amqplib'

    def before_connect(self):
        try:
            import amqplib  # noqa
        except ImportError:
            raise SkipTest('amqplib not installed')

########NEW FILE########
__FILENAME__ = test_beanstalk
from funtests import transport

from nose import SkipTest


class test_beanstalk(transport.TransportCase):
    transport = 'beanstalk'
    prefix = 'beanstalk'
    event_loop_max = 10
    message_size_limit = 47662

    def before_connect(self):
        try:
            import beanstalkc  # noqa
        except ImportError:
            raise SkipTest('beanstalkc not installed')

    def after_connect(self, connection):
        connection.channel().client

########NEW FILE########
__FILENAME__ = test_couchdb
from nose import SkipTest

from funtests import transport


class test_couchdb(transport.TransportCase):
    transport = 'couchdb'
    prefix = 'couchdb'
    event_loop_max = 100

    def before_connect(self):
        try:
            import couchdb  # noqa
        except ImportError:
            raise SkipTest('couchdb not installed')

    def after_connect(self, connection):
        connection.channel().client

########NEW FILE########
__FILENAME__ = test_django
from nose import SkipTest

from kombu.tests.case import redirect_stdouts

from funtests import transport


class test_django(transport.TransportCase):
    transport = 'django'
    prefix = 'django'
    event_loop_max = 10

    def before_connect(self):

        @redirect_stdouts
        def setup_django(stdout, stderr):
            try:
                import django  # noqa
            except ImportError:
                raise SkipTest('django not installed')
            from django.conf import settings
            if not settings.configured:
                settings.configure(
                    DATABASE_ENGINE='sqlite3',
                    DATABASE_NAME=':memory:',
                    DATABASES={
                        'default': {
                            'ENGINE': 'django.db.backends.sqlite3',
                            'NAME': ':memory:',
                        },
                    },
                    INSTALLED_APPS=('kombu.transport.django', ),
                )
            from django.core.management import call_command
            call_command('syncdb')

        setup_django()

########NEW FILE########
__FILENAME__ = test_librabbitmq
from nose import SkipTest

from funtests import transport


class test_librabbitmq(transport.TransportCase):
    transport = 'librabbitmq'
    prefix = 'librabbitmq'

    def before_connect(self):
        try:
            import librabbitmq  # noqa
        except ImportError:
            raise SkipTest('librabbitmq not installed')

########NEW FILE########
__FILENAME__ = test_mongodb
from nose import SkipTest

from kombu import Consumer, Producer, Exchange, Queue
from kombu.five import range
from kombu.utils import nested

from funtests import transport


class test_mongodb(transport.TransportCase):
    transport = 'mongodb'
    prefix = 'mongodb'
    event_loop_max = 100

    def before_connect(self):
        try:
            import pymongo  # noqa
        except ImportError:
            raise SkipTest('pymongo not installed')

    def after_connect(self, connection):
        connection.channel().client  # evaluate connection.

        self.c = self.connection   # shortcut

    def test_fanout(self, name='test_mongodb_fanout'):
        if not self.verify_alive():
            return
        c = self.connection
        self.e = Exchange(name, type='fanout')
        self.q = Queue(name, exchange=self.e, routing_key=name)
        self.q2 = Queue(name + '2', exchange=self.e, routing_key=name + '2')

        channel = c.default_channel
        producer = Producer(channel, self.e)
        consumer1 = Consumer(channel, self.q)
        consumer2 = Consumer(channel, self.q2)
        self.q2(channel).declare()

        for i in range(10):
            producer.publish({'foo': i}, routing_key=name)
        for i in range(10):
            producer.publish({'foo': i}, routing_key=name + '2')

        _received1 = []
        _received2 = []

        def callback1(message_data, message):
            _received1.append(message)
            message.ack()

        def callback2(message_data, message):
            _received2.append(message)
            message.ack()

        consumer1.register_callback(callback1)
        consumer2.register_callback(callback2)

        with nested(consumer1, consumer2):

            while 1:
                if len(_received1) + len(_received2) == 20:
                    break
                c.drain_events(timeout=60)
        self.assertEqual(len(_received1) + len(_received2), 20)

        # queue.delete
        for i in range(10):
            producer.publish({'foo': i}, routing_key=name)
        self.assertTrue(self.q(channel).get())
        self.q(channel).delete()
        self.q(channel).declare()
        self.assertIsNone(self.q(channel).get())

        # queue.purge
        for i in range(10):
            producer.publish({'foo': i}, routing_key=name + '2')
        self.assertTrue(self.q2(channel).get())
        self.q2(channel).purge()
        self.assertIsNone(self.q2(channel).get())

########NEW FILE########
__FILENAME__ = test_pyamqp
from funtests import transport


class test_pyamqp(transport.TransportCase):
    transport = 'pyamqp'
    prefix = 'pyamqp'

########NEW FILE########
__FILENAME__ = test_redis
from nose import SkipTest

from funtests import transport


class test_redis(transport.TransportCase):
    transport = 'redis'
    prefix = 'redis'

    def before_connect(self):
        try:
            import redis  # noqa
        except ImportError:
            raise SkipTest('redis not installed')

    def after_connect(self, connection):
        client = connection.channel().client
        client.info()

    def test_cant_connect_raises_connection_error(self):
        conn = self.get_connection(port=65534)
        self.assertRaises(conn.connection_errors, conn.connect)

########NEW FILE########
__FILENAME__ = test_SLMQ

from funtests import transport
from nose import SkipTest
import os


class test_SLMQ(transport.TransportCase):
    transport = "SLMQ"
    prefix = "slmq"
    event_loop_max = 100
    message_size_limit = 4192
    reliable_purge = False
    #: does not guarantee FIFO order, even in simple cases.
    suppress_disorder_warning = True

    def before_connect(self):
        if "SLMQ_ACCOUNT" not in os.environ:
            raise SkipTest("Missing envvar SLMQ_ACCOUNT")
        if "SL_USERNAME" not in os.environ:
            raise SkipTest("Missing envvar SL_USERNAME")
        if "SL_API_KEY" not in os.environ:
            raise SkipTest("Missing envvar SL_API_KEY")
        if "SLMQ_HOST" not in os.environ:
            raise SkipTest("Missing envvar SLMQ_HOST")
        if "SLMQ_SECURE" not in os.environ:
            raise SkipTest("Missing envvar SLMQ_SECURE")

    def after_connect(self, connection):
        pass

########NEW FILE########
__FILENAME__ = test_sqla
from nose import SkipTest

from funtests import transport


class test_sqla(transport.TransportCase):
    transport = 'sqlalchemy'
    prefix = 'sqlalchemy'
    event_loop_max = 10
    connection_options = {'hostname': 'sqla+sqlite://'}

    def before_connect(self):
        try:
            import sqlalchemy  # noqa
        except ImportError:
            raise SkipTest('sqlalchemy not installed')

########NEW FILE########
__FILENAME__ = test_SQS
import os

from nose import SkipTest

from funtests import transport


class test_SQS(transport.TransportCase):
    transport = 'SQS'
    prefix = 'sqs'
    event_loop_max = 100
    message_size_limit = 4192  # SQS max body size / 2.
    reliable_purge = False
    #: does not guarantee FIFO order, even in simple cases
    suppress_disorder_warning = True

    def before_connect(self):
        try:
            import boto  # noqa
        except ImportError:
            raise SkipTest('boto not installed')
        if 'AWS_ACCESS_KEY_ID' not in os.environ:
            raise SkipTest('Missing envvar AWS_ACCESS_KEY_ID')
        if 'AWS_SECRET_ACCESS_KEY' not in os.environ:
            raise SkipTest('Missing envvar AWS_SECRET_ACCESS_KEY')

    def after_connect(self, connection):
        connection.channel().sqs

########NEW FILE########
__FILENAME__ = test_zookeeper
from nose import SkipTest

from funtests import transport


class test_zookeeper(transport.TransportCase):
    transport = 'zookeeper'
    prefix = 'zookeeper'
    event_loop_max = 100

    def before_connect(self):
        try:
            import kazoo  # noqa
        except ImportError:
            raise SkipTest('kazoo not installed')

    def after_connect(self, connection):
        connection.channel().client

########NEW FILE########
__FILENAME__ = transport
from __future__ import absolute_import, print_function

import random
import socket
import string
import sys
import time
import unittest2 as unittest
import warnings
import weakref

from nose import SkipTest

from kombu import Connection
from kombu import Exchange, Queue
from kombu.five import range

if sys.version_info >= (2, 5):
    from hashlib import sha256 as _digest
else:
    from sha import new as _digest  # noqa


def _nobuf(x):
    return [str(i) if isinstance(i, buffer) else i for i in x]


def consumeN(conn, consumer, n=1, timeout=30):
    messages = []

    def callback(message_data, message):
        messages.append(message_data)
        message.ack()

    prev, consumer.callbacks = consumer.callbacks, [callback]
    consumer.consume()

    seconds = 0
    while True:
        try:
            conn.drain_events(timeout=1)
        except socket.timeout:
            seconds += 1
            msg = 'Received %s/%s messages. %s seconds passed.' % (
                len(messages), n, seconds)
            if seconds >= timeout:
                raise socket.timeout(msg)
            if seconds > 1:
                print(msg)
        if len(messages) >= n:
            break

    consumer.cancel()
    consumer.callback = prev
    return messages


class TransportCase(unittest.TestCase):
    transport = None
    prefix = None
    sep = '.'
    userid = None
    password = None
    event_loop_max = 100
    connection_options = {}
    suppress_disorder_warning = False
    reliable_purge = True

    connected = False
    skip_test_reason = None

    message_size_limit = None

    def before_connect(self):
        pass

    def after_connect(self, connection):
        pass

    def setUp(self):
        if self.transport:
            try:
                self.before_connect()
            except SkipTest as exc:
                self.skip_test_reason = str(exc)
            else:
                self.do_connect()
            self.exchange = Exchange(self.prefix, 'direct')
            self.queue = Queue(self.prefix, self.exchange, self.prefix)

    def purge(self, names):
        chan = self.connection.channel()
        total = 0
        for queue in names:
            while 1:
                # ensure the queue is completly empty
                purged = chan.queue_purge(queue=queue)
                if not purged:
                    break
                total += purged
        chan.close()
        return total

    def get_connection(self, **options):
        if self.userid:
            options.setdefault('userid', self.userid)
        if self.password:
            options.setdefault('password', self.password)
        return Connection(transport=self.transport, **options)

    def do_connect(self):
        self.connection = self.get_connection(**self.connection_options)
        try:
            self.connection.connect()
            self.after_connect(self.connection)
        except self.connection.connection_errors:
            self.skip_test_reason = '%s transport cannot connect' % (
                self.transport, )
        else:
            self.connected = True

    def verify_alive(self):
        if self.transport:
            if not self.connected:
                raise SkipTest(self.skip_test_reason)
            return True

    def purge_consumer(self, consumer):
        return self.purge([queue.name for queue in consumer.queues])

    def test_produce__consume(self):
        if not self.verify_alive():
            return
        chan1 = self.connection.channel()
        consumer = chan1.Consumer(self.queue)
        self.purge_consumer(consumer)
        producer = chan1.Producer(self.exchange)
        producer.publish({'foo': 'bar'}, routing_key=self.prefix)
        message = consumeN(self.connection, consumer)
        self.assertDictEqual(message[0], {'foo': 'bar'})
        chan1.close()
        self.purge([self.queue.name])

    def test_purge(self):
        if not self.verify_alive():
            return
        chan1 = self.connection.channel()
        consumer = chan1.Consumer(self.queue)
        self.purge_consumer(consumer)

        producer = chan1.Producer(self.exchange)
        for i in range(10):
            producer.publish({'foo': 'bar'}, routing_key=self.prefix)
        if self.reliable_purge:
            self.assertEqual(consumer.purge(), 10)
            self.assertEqual(consumer.purge(), 0)
        else:
            purged = 0
            while purged < 9:
                purged += self.purge_consumer(consumer)

    def _digest(self, data):
        return _digest(data).hexdigest()

    def test_produce__consume_large_messages(
            self, bytes=1048576, n=10,
            charset=string.punctuation + string.letters + string.digits):
        if not self.verify_alive():
            return
        bytes = min(x for x in [bytes, self.message_size_limit] if x)
        messages = [''.join(random.choice(charset)
                    for j in range(bytes)) + '--%s' % n
                    for i in range(n)]
        digests = []
        chan1 = self.connection.channel()
        consumer = chan1.Consumer(self.queue)
        self.purge_consumer(consumer)
        producer = chan1.Producer(self.exchange)
        for i, message in enumerate(messages):
            producer.publish({'text': message,
                              'i': i}, routing_key=self.prefix)
            digests.append(self._digest(message))

        received = [(msg['i'], msg['text'])
                    for msg in consumeN(self.connection, consumer, n)]
        self.assertEqual(len(received), n)
        ordering = [i for i, _ in received]
        if ordering != list(range(n)) and not self.suppress_disorder_warning:
            warnings.warn(
                '%s did not deliver messages in FIFO order: %r' % (
                    self.transport, ordering))

        for i, text in received:
            if text != messages[i]:
                raise AssertionError('%i: %r is not %r' % (
                    i, text[-100:], messages[i][-100:]))
            self.assertEqual(self._digest(text), digests[i])

        chan1.close()
        self.purge([self.queue.name])

    def P(self, rest):
        return '%s%s%s' % (self.prefix, self.sep, rest)

    def test_produce__consume_multiple(self):
        if not self.verify_alive():
            return
        chan1 = self.connection.channel()
        producer = chan1.Producer(self.exchange)
        b1 = Queue(self.P('b1'), self.exchange, 'b1')(chan1)
        b2 = Queue(self.P('b2'), self.exchange, 'b2')(chan1)
        b3 = Queue(self.P('b3'), self.exchange, 'b3')(chan1)
        [q.declare() for q in (b1, b2, b3)]
        self.purge([b1.name, b2.name, b3.name])

        producer.publish('b1', routing_key='b1')
        producer.publish('b2', routing_key='b2')
        producer.publish('b3', routing_key='b3')
        chan1.close()

        chan2 = self.connection.channel()
        consumer = chan2.Consumer([b1, b2, b3])
        messages = consumeN(self.connection, consumer, 3)
        self.assertItemsEqual(_nobuf(messages), ['b1', 'b2', 'b3'])
        chan2.close()
        self.purge([self.P('b1'), self.P('b2'), self.P('b3')])

    def test_timeout(self):
        if not self.verify_alive():
            return
        chan = self.connection.channel()
        self.purge([self.queue.name])
        consumer = chan.Consumer(self.queue)
        self.assertRaises(
            socket.timeout, self.connection.drain_events, timeout=0.3,
        )
        consumer.cancel()
        chan.close()

    def test_basic_get(self):
        if not self.verify_alive():
            return
        chan1 = self.connection.channel()
        producer = chan1.Producer(self.exchange)
        chan2 = self.connection.channel()
        queue = Queue(self.P('basic_get'), self.exchange, 'basic_get')
        queue = queue(chan2)
        queue.declare()
        producer.publish({'basic.get': 'this'}, routing_key='basic_get')
        chan1.close()

        for i in range(self.event_loop_max):
            m = queue.get()
            if m:
                break
            time.sleep(0.1)
        self.assertEqual(m.payload, {'basic.get': 'this'})
        self.purge([queue.name])
        chan2.close()

    def test_cyclic_reference_transport(self):
        if not self.verify_alive():
            return

        def _createref():
            conn = self.get_connection()
            conn.transport
            conn.close()
            return weakref.ref(conn)

        self.assertIsNone(_createref()())

    def test_cyclic_reference_connection(self):
        if not self.verify_alive():
            return

        def _createref():
            conn = self.get_connection()
            conn.connect()
            conn.close()
            return weakref.ref(conn)

        self.assertIsNone(_createref()())

    def test_cyclic_reference_channel(self):
        if not self.verify_alive():
            return

        def _createref():
            conn = self.get_connection()
            conn.connect()
            chanrefs = []
            try:
                for i in range(100):
                    channel = conn.channel()
                    chanrefs.append(weakref.ref(channel))
                    channel.close()
            finally:
                conn.close()
            return chanrefs

        for chanref in _createref():
            self.assertIsNone(chanref())

    def tearDown(self):
        if self.transport and self.connected:
            self.connection.close()

########NEW FILE########
__FILENAME__ = abstract
"""
kombu.abstract
==============

Object utilities.

"""
from __future__ import absolute_import

from copy import copy

from .connection import maybe_channel
from .exceptions import NotBoundError
from .utils import ChannelPromise

__all__ = ['Object', 'MaybeChannelBound']


def unpickle_dict(cls, kwargs):
    return cls(**kwargs)


class Object(object):
    """Common base class supporting automatic kwargs->attributes handling,
    and cloning."""
    attrs = ()

    def __init__(self, *args, **kwargs):
        any = lambda v: v
        for name, type_ in self.attrs:
            value = kwargs.get(name)
            if value is not None:
                setattr(self, name, (type_ or any)(value))
            else:
                try:
                    getattr(self, name)
                except AttributeError:
                    setattr(self, name, None)

    def as_dict(self, recurse=False):
        def f(obj, type):
            if recurse and isinstance(obj, Object):
                return obj.as_dict(recurse=True)
            return type(obj) if type else obj
        return {
            attr: f(getattr(self, attr), type) for attr, type in self.attrs
        }

    def __reduce__(self):
        return unpickle_dict, (self.__class__, self.as_dict())

    def __copy__(self):
        return self.__class__(**self.as_dict())


class MaybeChannelBound(Object):
    """Mixin for classes that can be bound to an AMQP channel."""
    _channel = None
    _is_bound = False

    #: Defines whether maybe_declare can skip declaring this entity twice.
    can_cache_declaration = False

    def __call__(self, channel):
        """`self(channel) -> self.bind(channel)`"""
        return self.bind(channel)

    def bind(self, channel):
        """Create copy of the instance that is bound to a channel."""
        return copy(self).maybe_bind(channel)

    def maybe_bind(self, channel):
        """Bind instance to channel if not already bound."""
        if not self.is_bound and channel:
            self._channel = maybe_channel(channel)
            self.when_bound()
            self._is_bound = True
        return self

    def revive(self, channel):
        """Revive channel after the connection has been re-established.

        Used by :meth:`~kombu.Connection.ensure`.

        """
        if self.is_bound:
            self._channel = channel
            self.when_bound()

    def when_bound(self):
        """Callback called when the class is bound."""
        pass

    def __repr__(self, item=''):
        item = item or type(self).__name__
        if self.is_bound:
            return '<{0} bound to chan:{1}>'.format(
                item or type(self).__name__, self.channel.channel_id)
        return '<unbound {0}>'.format(item)

    @property
    def is_bound(self):
        """Flag set if the channel is bound."""
        return self._is_bound and self._channel is not None

    @property
    def channel(self):
        """Current channel if the object is bound."""
        channel = self._channel
        if channel is None:
            raise NotBoundError(
                "Can't call method on {0} not bound to a channel".format(
                    type(self).__name__))
        if isinstance(channel, ChannelPromise):
            channel = self._channel = channel()
        return channel

########NEW FILE########
__FILENAME__ = debug
from __future__ import absolute_import

from kombu.five import items
from kombu.utils import reprcall
from kombu.utils.eventio import READ, WRITE, ERR


def repr_flag(flag):
    return '{0}{1}{2}'.format('R' if flag & READ else '',
                              'W' if flag & WRITE else '',
                              '!' if flag & ERR else '')


def _rcb(obj):
    if obj is None:
        return '<missing>'
    if isinstance(obj, str):
        return obj
    if isinstance(obj, tuple):
        cb, args = obj
        return reprcall(cb.__name__, args=args)
    return obj.__name__


def repr_active(h):
    return ', '.join(repr_readers(h) + repr_writers(h))


def repr_events(h, events):
    return ', '.join(
        '{0}({1})->{2}'.format(
            _rcb(callback_for(h, fd, fl, '(GONE)')), fd,
            repr_flag(fl),
        )
        for fd, fl in events
    )


def repr_readers(h):
    return ['({0}){1}->{2}'.format(fd, _rcb(cb), repr_flag(READ | ERR))
            for fd, cb in items(h.readers)]


def repr_writers(h):
    return ['({0}){1}->{2}'.format(fd, _rcb(cb), repr_flag(WRITE))
            for fd, cb in items(h.writers)]


def callback_for(h, fd, flag, *default):
    try:
        if flag & READ:
            return h.readers[fd]
        if flag & WRITE:
            if fd in h.consolidate:
                return h.consolidate_callback
            return h.writers[fd]
    except KeyError:
        if default:
            return default[0]
        raise

########NEW FILE########
__FILENAME__ = hub
# -*- coding: utf-8 -*-
"""
kombu.async.hub
===============

Event loop implementation.

"""
from __future__ import absolute_import

import errno

from collections import deque
from contextlib import contextmanager
from time import sleep
from types import GeneratorType as generator

from amqp import promise

from kombu.five import Empty, range
from kombu.log import get_logger
from kombu.utils import cached_property, fileno
from kombu.utils.eventio import READ, WRITE, ERR, poll

from .timer import Timer

__all__ = ['Hub', 'get_event_loop', 'set_event_loop']
logger = get_logger(__name__)

_current_loop = None


class Stop(BaseException):
    """Stops the event loop."""


def _raise_stop_error():
    raise Stop()


@contextmanager
def _dummy_context(*args, **kwargs):
    yield


def get_event_loop():
    return _current_loop


def set_event_loop(loop):
    global _current_loop
    _current_loop = loop
    return loop


class Hub(object):
    """Event loop object.

    :keyword timer: Specify timer object.

    """
    #: Flag set if reading from an fd will not block.
    READ = READ

    #: Flag set if writing to an fd will not block.
    WRITE = WRITE

    #: Flag set on error, and the fd should be read from asap.
    ERR = ERR

    #: List of callbacks to be called when the loop is exiting,
    #: applied with the hub instance as sole argument.
    on_close = None

    def __init__(self, timer=None):
        self.timer = timer if timer is not None else Timer()

        self.readers = {}
        self.writers = {}
        self.on_tick = set()
        self.on_close = set()
        self._ready = deque()

        self._running = False
        self._loop = None

        # The eventloop (in celery.worker.loops)
        # will merge fds in this set and then instead of calling
        # the callback for each ready fd it will call the
        # :attr:`consolidate_callback` with the list of ready_fds
        # as an argument.  This API is internal and is only
        # used by the multiprocessing pool to find inqueues
        # that are ready to write.
        self.consolidate = set()
        self.consolidate_callback = None

        self.propagate_errors = ()

        self._create_poller()

    def reset(self):
        self.close()
        self._create_poller()

    def _create_poller(self):
        self.poller = poll()
        self._register_fd = self.poller.register
        self._unregister_fd = self.poller.unregister

    def _close_poller(self):
        if self.poller is not None:
            self.poller.close()
            self.poller = None
            self._register_fd = None
            self._unregister_fd = None

    def stop(self):
        self.call_soon(_raise_stop_error)

    def __repr__(self):
        return '<Hub@{0:#x}: R:{1} W:{2}>'.format(
            id(self), len(self.readers), len(self.writers),
        )

    def fire_timers(self, min_delay=1, max_delay=10, max_timers=10,
                    propagate=()):
        timer = self.timer
        delay = None
        if timer and timer._queue:
            for i in range(max_timers):
                delay, entry = next(self.scheduler)
                if entry is None:
                    break
                try:
                    entry()
                except propagate:
                    raise
                except (MemoryError, AssertionError):
                    raise
                except OSError as exc:
                    if exc.errno == errno.ENOMEM:
                        raise
                    logger.error('Error in timer: %r', exc, exc_info=1)
                except Exception as exc:
                    logger.error('Error in timer: %r', exc, exc_info=1)
        return min(max(delay or 0, min_delay), max_delay)

    def add(self, fd, callback, flags, args=(), consolidate=False):
        fd = fileno(fd)
        try:
            self.poller.register(fd, flags)
        except ValueError:
            self._discard(fd)
            raise
        else:
            dest = self.readers if flags & READ else self.writers
            if consolidate:
                self.consolidate.add(fd)
                dest[fd] = None
            else:
                dest[fd] = callback, args

    def remove(self, fd):
        fd = fileno(fd)
        self._unregister(fd)
        self._discard(fd)

    def run_forever(self):
        self._running = True
        try:
            while 1:
                try:
                    self.run_once()
                except Stop:
                    break
        finally:
            self._running = False

    def run_once(self):
        try:
            next(self.loop)
        except StopIteration:
            self._loop = None

    def call_soon(self, callback, *args):
        handle = promise(callback, args)
        self._ready.append(handle)
        return handle

    def call_later(self, delay, callback, *args):
        return self.timer.call_after(delay, callback, args)

    def call_at(self, when, callback, *args):
        return self.timer.call_at(when, callback, args)

    def call_repeatedly(self, delay, callback, *args):
        return self.timer.call_repeatedly(delay, callback, args)

    def add_reader(self, fds, callback, *args):
        return self.add(fds, callback, READ | ERR, args)

    def add_writer(self, fds, callback, *args):
        return self.add(fds, callback, WRITE, args)

    def remove_reader(self, fd):
        writable = fd in self.writers
        on_write = self.writers.get(fd)
        try:
            self._unregister(fd)
            self._discard(fd)
        finally:
            if writable:
                cb, args = on_write
                self.add(fd, cb, WRITE, args)

    def remove_writer(self, fd):
        readable = fd in self.readers
        on_read = self.readers.get(fd)
        try:
            self._unregister(fd)
            self._discard(fd)
        finally:
            if readable:
                cb, args = on_read
                self.add(fd, cb, READ | ERR, args)

    def _unregister(self, fd):
        try:
            self.poller.unregister(fd)
        except (AttributeError, KeyError, OSError):
            pass

    def close(self, *args):
        [self._unregister(fd) for fd in self.readers]
        self.readers.clear()
        [self._unregister(fd) for fd in self.writers]
        self.writers.clear()
        self.consolidate.clear()
        self._close_poller()
        for callback in self.on_close:
            callback(self)

    def _discard(self, fd):
        fd = fileno(fd)
        self.readers.pop(fd, None)
        self.writers.pop(fd, None)
        self.consolidate.discard(fd)

    def create_loop(self,
                    generator=generator, sleep=sleep, min=min, next=next,
                    Empty=Empty, StopIteration=StopIteration,
                    KeyError=KeyError, READ=READ, WRITE=WRITE, ERR=ERR):
        readers, writers = self.readers, self.writers
        poll = self.poller.poll
        fire_timers = self.fire_timers
        hub_remove = self.remove
        scheduled = self.timer._queue
        consolidate = self.consolidate
        consolidate_callback = self.consolidate_callback
        on_tick = self.on_tick
        todo = self._ready
        propagate = self.propagate_errors

        while 1:
            for tick_callback in on_tick:
                tick_callback()

            while todo:
                item = todo.popleft()
                if item:
                    item()

            poll_timeout = fire_timers(propagate=propagate) if scheduled else 1
            #  print('[[[HUB]]]: %s' % (self.repr_active(), ))
            if readers or writers:
                to_consolidate = []
                try:
                    events = poll(poll_timeout)
                    #  print('[EVENTS]: %s' % (self.repr_events(events), ))
                except ValueError:  # Issue 882
                    raise StopIteration()

                for fd, event in events or ():
                    if fd in consolidate and \
                            writers.get(fd) is None:
                        to_consolidate.append(fd)
                        continue
                    cb = cbargs = None

                    if event & READ:
                        try:
                            cb, cbargs = readers[fd]
                        except KeyError:
                            self.remove_reader(fd)
                            continue
                    elif event & WRITE:
                        try:
                            cb, cbargs = writers[fd]
                        except KeyError:
                            self.remove_writer(fd)
                            continue
                    elif event & ERR:
                        try:
                            cb, cbargs = (readers.get(fd) or
                                          writers.get(fd))
                        except TypeError:
                            pass

                    if cb is None:
                        continue
                    if isinstance(cb, generator):
                        try:
                            next(cb)
                        except OSError as exc:
                            if exc.errno != errno.EBADF:
                                raise
                            hub_remove(fd)
                        except StopIteration:
                            pass
                        except Exception:
                            hub_remove(fd)
                            raise
                    else:
                        try:
                            cb(*cbargs)
                        except Empty:
                            pass
                if to_consolidate:
                    consolidate_callback(to_consolidate)
            else:
                # no sockets yet, startup is probably not done.
                sleep(min(poll_timeout, 0.1))
            yield

    def repr_active(self):
        from .debug import repr_active
        return repr_active(self)

    def repr_events(self, events):
        from .debug import repr_events
        return repr_events(self, events or [])

    @cached_property
    def scheduler(self):
        return iter(self.timer)

    @property
    def loop(self):
        if self._loop is None:
            self._loop = self.create_loop()
        return self._loop

########NEW FILE########
__FILENAME__ = semaphore
# -*- coding: utf-8 -*-
"""
kombu.async.semaphore
=====================

Semaphores and concurrency primitives.

"""
from __future__ import absolute_import

from collections import deque

__all__ = ['DummyLock', 'LaxBoundedSemaphore']


class LaxBoundedSemaphore(object):
    """Asynchronous Bounded Semaphore.

    Lax means that the value will stay within the specified
    range even if released more times than it was acquired.

    Example:

        >>> from future import print_statement as printf
        # ^ ignore: just fooling stupid pyflakes

        >>> x = LaxBoundedSemaphore(2)

        >>> x.acquire(printf, 'HELLO 1')
        HELLO 1

        >>> x.acquire(printf, 'HELLO 2')
        HELLO 2

        >>> x.acquire(printf, 'HELLO 3')
        >>> x._waiters   # private, do not access directly
        [print, ('HELLO 3', )]

        >>> x.release()
        HELLO 3

    """

    def __init__(self, value):
        self.initial_value = self.value = value
        self._waiting = deque()
        self._add_waiter = self._waiting.append
        self._pop_waiter = self._waiting.popleft

    def acquire(self, callback, *partial_args):
        """Acquire semaphore, applying ``callback`` if
        the resource is available.

        :param callback: The callback to apply.
        :param \*partial_args: partial arguments to callback.

        """
        value = self.value
        if value <= 0:
            self._add_waiter((callback, partial_args))
            return False
        else:
            self.value = max(value - 1, 0)
            callback(*partial_args)
            return True

    def release(self):
        """Release semaphore.

        If there are any waiters this will apply the first waiter
        that is waiting for the resource (FIFO order).

        """
        try:
            waiter, args = self._pop_waiter()
        except IndexError:
            self.value = min(self.value + 1, self.initial_value)
        else:
            waiter(*args)

    def grow(self, n=1):
        """Change the size of the semaphore to accept more users."""
        self.initial_value += n
        self.value += n
        [self.release() for _ in range(n)]

    def shrink(self, n=1):
        """Change the size of the semaphore to accept less users."""
        self.initial_value = max(self.initial_value - n, 0)
        self.value = max(self.value - n, 0)

    def clear(self):
        """Reset the semaphore, which also wipes out any waiting callbacks."""
        self._waiting.clear()
        self.value = self.initial_value

    def __repr__(self):
        return '<{0} at {1:#x} value:{2} waiting:{3}>'.format(
            self.__class__.__name__, id(self), self.value, len(self._waiting),
        )


class DummyLock(object):
    """Pretending to be a lock."""

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        pass

########NEW FILE########
__FILENAME__ = timer
# -*- coding: utf-8 -*-
"""
kombu.async.timer
=================

Timer scheduling Python callbacks.

"""
from __future__ import absolute_import

import heapq
import sys

from collections import namedtuple
from datetime import datetime
from functools import wraps
from time import time
from weakref import proxy as weakrefproxy

from kombu.five import monotonic
from kombu.log import get_logger

try:
    from pytz import utc
except ImportError:
    utc = None

DEFAULT_MAX_INTERVAL = 2
EPOCH = datetime.utcfromtimestamp(0).replace(tzinfo=utc)
IS_PYPY = hasattr(sys, 'pypy_version_info')

logger = get_logger(__name__)

__all__ = ['Entry', 'Timer', 'to_timestamp']

scheduled = namedtuple('scheduled', ('eta', 'priority', 'entry'))


def to_timestamp(d, default_timezone=utc):
    if isinstance(d, datetime):
        if d.tzinfo is None:
            d = d.replace(tzinfo=default_timezone)
        return max((d - EPOCH).total_seconds(), 0)
    return d


class Entry(object):
    if not IS_PYPY:  # pragma: no cover
        __slots__ = (
            'fun', 'args', 'kwargs', 'tref', 'cancelled',
            '_last_run', '__weakref__',
        )

    def __init__(self, fun, args=None, kwargs=None):
        self.fun = fun
        self.args = args or []
        self.kwargs = kwargs or {}
        self.tref = weakrefproxy(self)
        self._last_run = None
        self.cancelled = False

    def __call__(self):
        return self.fun(*self.args, **self.kwargs)

    def cancel(self):
        try:
            self.tref.cancelled = True
        except ReferenceError:  # pragma: no cover
            pass

    def __repr__(self):
        return '<TimerEntry: {0}(*{1!r}, **{2!r})'.format(
            self.fun.__name__, self.args, self.kwargs)

    def __hash__(self):
        return hash((self.fun, repr(self.args), repr(self.kwargs)))

    # must not use hash() to order entries
    def __lt__(self, other):
        return id(self) < id(other)

    def __gt__(self, other):
        return id(self) > id(other)

    def __le__(self, other):
        return id(self) <= id(other)

    def __ge__(self, other):
        return id(self) >= id(other)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __ne__(self, other):
        return not self.__eq__(other)


class Timer(object):
    """ETA scheduler."""
    Entry = Entry

    on_error = None

    def __init__(self, max_interval=None, on_error=None, **kwargs):
        self.max_interval = float(max_interval or DEFAULT_MAX_INTERVAL)
        self.on_error = on_error or self.on_error
        self._queue = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.stop()

    def call_at(self, eta, fun, args=(), kwargs={}, priority=0):
        return self.enter_at(self.Entry(fun, args, kwargs), eta, priority)

    def call_after(self, secs, fun, args=(), kwargs={}, priority=0):
        return self.enter_after(secs, self.Entry(fun, args, kwargs), priority)

    def call_repeatedly(self, secs, fun, args=(), kwargs={}, priority=0):
        tref = self.Entry(fun, args, kwargs)

        @wraps(fun)
        def _reschedules(*args, **kwargs):
            last, now = tref._last_run, monotonic()
            lsince = (now - tref._last_run) if last else secs
            try:
                if lsince and lsince >= secs:
                    tref._last_run = now
                    return fun(*args, **kwargs)
            finally:
                if not tref.cancelled:
                    last = tref._last_run
                    next = secs - (now - last) if last else secs
                    self.enter_after(next, tref, priority)

        tref.fun = _reschedules
        tref._last_run = None
        return self.enter_after(secs, tref, priority)

    def enter_at(self, entry, eta=None, priority=0, time=time):
        """Enter function into the scheduler.

        :param entry: Item to enter.
        :keyword eta: Scheduled time as a :class:`datetime.datetime` object.
        :keyword priority: Unused.

        """
        if eta is None:
            eta = time()
        if isinstance(eta, datetime):
            try:
                eta = to_timestamp(eta)
            except Exception as exc:
                if not self.handle_error(exc):
                    raise
                return
        return self._enter(eta, priority, entry)

    def enter_after(self, secs, entry, priority=0, time=time):
        return self.enter_at(entry, time() + secs, priority)

    def _enter(self, eta, priority, entry, push=heapq.heappush):
        push(self._queue, scheduled(eta, priority, entry))
        return entry

    def apply_entry(self, entry):
        try:
            entry()
        except Exception as exc:
            if not self.handle_error(exc):
                logger.error('Error in timer: %r', exc, exc_info=True)

    def handle_error(self, exc_info):
        if self.on_error:
            self.on_error(exc_info)
            return True

    def stop(self):
        pass

    def __iter__(self, min=min, nowfun=time,
                 pop=heapq.heappop, push=heapq.heappush):
        """This iterator yields a tuple of ``(entry, wait_seconds)``,
        where if entry is :const:`None` the caller should wait
        for ``wait_seconds`` until it polls the schedule again."""
        max_interval = self.max_interval
        queue = self._queue

        while 1:
            if queue:
                eventA = queue[0]
                now, eta = nowfun(), eventA[0]

                if now < eta:
                    yield min(eta - now, max_interval), None
                else:
                    eventB = pop(queue)

                    if eventB is eventA:
                        entry = eventA[2]
                        if not entry.cancelled:
                            yield None, entry
                        continue
                    else:
                        push(queue, eventB)
            else:
                yield None, None

    def clear(self):
        self._queue[:] = []  # atomic, without creating a new list.

    def cancel(self, tref):
        tref.cancel()

    def __len__(self):
        return len(self._queue)

    def __nonzero__(self):
        return True

    @property
    def queue(self, _pop=heapq.heappop):
        """Snapshot of underlying datastructure."""
        events = list(self._queue)
        return [_pop(v) for v in [events] * len(events)]

    @property
    def schedule(self):
        return self

########NEW FILE########
__FILENAME__ = clocks
"""
kombu.clocks
============

Logical Clocks and Synchronization.

"""
from __future__ import absolute_import

from threading import Lock
from itertools import islice
from operator import itemgetter

from .five import zip

__all__ = ['LamportClock', 'timetuple']

R_CLOCK = '_lamport(clock={0}, timestamp={1}, id={2} {3!r})'


class timetuple(tuple):
    """Tuple of event clock information.

    Can be used as part of a heap to keep events ordered.

    :param clock:  Event clock value.
    :param timestamp: Event UNIX timestamp value.
    :param id: Event host id (e.g. ``hostname:pid``).
    :param obj: Optional obj to associate with this event.

    """
    __slots__ = ()

    def __new__(cls, clock, timestamp, id, obj=None):
        return tuple.__new__(cls, (clock, timestamp, id, obj))

    def __repr__(self):
        return R_CLOCK.format(*self)

    def __getnewargs__(self):
        return tuple(self)

    def __lt__(self, other):
        # 0: clock 1: timestamp 3: process id
        try:
            A, B = self[0], other[0]
            # uses logical clock value first
            if A and B:  # use logical clock if available
                if A == B:  # equal clocks use lower process id
                    return self[2] < other[2]
                return A < B
            return self[1] < other[1]  # ... or use timestamp
        except IndexError:
            return NotImplemented
    __gt__ = lambda self, other: other < self
    __le__ = lambda self, other: not other < self
    __ge__ = lambda self, other: not self < other

    clock = property(itemgetter(0))
    timestamp = property(itemgetter(1))
    id = property(itemgetter(2))
    obj = property(itemgetter(3))


class LamportClock(object):
    """Lamport's logical clock.

    From Wikipedia:

    A Lamport logical clock is a monotonically incrementing software counter
    maintained in each process.  It follows some simple rules:

        * A process increments its counter before each event in that process;
        * When a process sends a message, it includes its counter value with
          the message;
        * On receiving a message, the receiver process sets its counter to be
          greater than the maximum of its own value and the received value
          before it considers the message received.

    Conceptually, this logical clock can be thought of as a clock that only
    has meaning in relation to messages moving between processes.  When a
    process receives a message, it resynchronizes its logical clock with
    the sender.

    .. seealso::

        * `Lamport timestamps`_

        * `Lamports distributed mutex`_

    .. _`Lamport Timestamps`: http://en.wikipedia.org/wiki/Lamport_timestamps
    .. _`Lamports distributed mutex`: http://bit.ly/p99ybE

    *Usage*

    When sending a message use :meth:`forward` to increment the clock,
    when receiving a message use :meth:`adjust` to sync with
    the time stamp of the incoming message.

    """
    #: The clocks current value.
    value = 0

    def __init__(self, initial_value=0, Lock=Lock):
        self.value = initial_value
        self.mutex = Lock()

    def adjust(self, other):
        with self.mutex:
            value = self.value = max(self.value, other) + 1
            return value

    def forward(self):
        with self.mutex:
            self.value += 1
            return self.value

    def sort_heap(self, h):
        """List of tuples containing at least two elements, representing
        an event, where the first element is the event's scalar clock value,
        and the second element is the id of the process (usually
        ``"hostname:pid"``): ``sh([(clock, processid, ...?), (...)])``

        The list must already be sorted, which is why we refer to it as a
        heap.

        The tuple will not be unpacked, so more than two elements can be
        present.

        Will return the latest event.

        """
        if h[0][0] == h[1][0]:
            same = []
            for PN in zip(h, islice(h, 1, None)):
                if PN[0][0] != PN[1][0]:
                    break  # Prev and Next's clocks differ
                same.append(PN[0])
            # return first item sorted by process id
            return sorted(same, key=lambda event: event[1])[0]
        # clock values unique, return first item
        return h[0]

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return '<LamportClock: {0.value}>'.format(self)

########NEW FILE########
__FILENAME__ = common
"""
kombu.common
============

Common Utilities.

"""
from __future__ import absolute_import

import os
import socket
import threading

from collections import deque
from contextlib import contextmanager
from functools import partial
from itertools import count
from uuid import getnode as _getnode, uuid4, uuid3, NAMESPACE_OID

from amqp import RecoverableConnectionError

from .entity import Exchange, Queue
from .five import range
from .log import get_logger
from .messaging import Consumer as _Consumer
from .serialization import registry as serializers
from .utils import uuid

try:
    from _thread import get_ident
except ImportError:                             # pragma: no cover
    try:                                        # noqa
        from thread import get_ident            # noqa
    except ImportError:                         # pragma: no cover
        from dummy_thread import get_ident      # noqa

__all__ = ['Broadcast', 'maybe_declare', 'uuid',
           'itermessages', 'send_reply',
           'collect_replies', 'insured', 'drain_consumer',
           'eventloop']

#: Prefetch count can't exceed short.
PREFETCH_COUNT_MAX = 0xFFFF

logger = get_logger(__name__)

_node_id = None


def get_node_id():
    global _node_id
    if _node_id is None:
        _node_id = uuid4().int
    return _node_id


def generate_oid(node_id, process_id, thread_id, instance):
    ent = '%x-%x-%x-%x' % (get_node_id(), process_id, thread_id, id(instance))
    return str(uuid3(NAMESPACE_OID, ent))


def oid_from(instance):
    return generate_oid(_getnode(), os.getpid(), get_ident(), instance)


class Broadcast(Queue):
    """Convenience class used to define broadcast queues.

    Every queue instance will have a unique name,
    and both the queue and exchange is configured with auto deletion.

    :keyword name: This is used as the name of the exchange.
    :keyword queue: By default a unique id is used for the queue
       name for every consumer.  You can specify a custom queue
       name here.
    :keyword \*\*kwargs: See :class:`~kombu.Queue` for a list
        of additional keyword arguments supported.

    """

    def __init__(self, name=None, queue=None, **kwargs):
        return super(Broadcast, self).__init__(
            name=queue or 'bcast.%s' % (uuid(), ),
            **dict({'alias': name,
                    'auto_delete': True,
                    'exchange': Exchange(name, type='fanout')}, **kwargs))


def declaration_cached(entity, channel):
    return entity in channel.connection.client.declared_entities


def maybe_declare(entity, channel=None, retry=False, **retry_policy):
    if not entity.is_bound:
        assert channel
        entity = entity.bind(channel)
    if retry:
        return _imaybe_declare(entity, **retry_policy)
    return _maybe_declare(entity)


def _maybe_declare(entity):
    channel = entity.channel
    if not channel.connection:
        raise RecoverableConnectionError('channel disconnected')
    if entity.can_cache_declaration:
        declared = channel.connection.client.declared_entities
        ident = hash(entity)
        if ident not in declared:
            entity.declare()
            declared.add(ident)
            return True
        return False
    entity.declare()
    return True


def _imaybe_declare(entity, **retry_policy):
    return entity.channel.connection.client.ensure(
        entity, _maybe_declare, **retry_policy)(entity)


def drain_consumer(consumer, limit=1, timeout=None, callbacks=None):
    acc = deque()

    def on_message(body, message):
        acc.append((body, message))

    consumer.callbacks = [on_message] + (callbacks or [])

    with consumer:
        for _ in eventloop(consumer.channel.connection.client,
                           limit=limit, timeout=timeout, ignore_timeouts=True):
            try:
                yield acc.popleft()
            except IndexError:
                pass


def itermessages(conn, channel, queue, limit=1, timeout=None,
                 Consumer=_Consumer, callbacks=None, **kwargs):
    return drain_consumer(Consumer(channel, queues=[queue], **kwargs),
                          limit=limit, timeout=timeout, callbacks=callbacks)


def eventloop(conn, limit=None, timeout=None, ignore_timeouts=False):
    """Best practice generator wrapper around ``Connection.drain_events``.

    Able to drain events forever, with a limit, and optionally ignoring
    timeout errors (a timeout of 1 is often used in environments where
    the socket can get "stuck", and is a best practice for Kombu consumers).

    **Examples**

    ``eventloop`` is a generator::

        from kombu.common import eventloop

        def run(connection):
            it = eventloop(connection, timeout=1, ignore_timeouts=True)
            next(it)   # one event consumed, or timed out.

            for _ in eventloop(connection, timeout=1, ignore_timeouts=True):
                pass  # loop forever.

    It also takes an optional limit parameter, and timeout errors
    are propagated by default::

        for _ in eventloop(connection, limit=1, timeout=1):
            pass

    .. seealso::

        :func:`itermessages`, which is an event loop bound to one or more
        consumers, that yields any messages received.

    """
    for i in limit and range(limit) or count():
        try:
            yield conn.drain_events(timeout=timeout)
        except socket.timeout:
            if timeout and not ignore_timeouts:  # pragma: no cover
                raise


def send_reply(exchange, req, msg,
               producer=None, retry=False, retry_policy=None, **props):
    """Send reply for request.

    :param exchange: Reply exchange
    :param req: Original request, a message with a ``reply_to`` property.
    :param producer: Producer instance
    :param retry: If true must retry according to ``reply_policy`` argument.
    :param retry_policy: Retry settings.
    :param props: Extra properties

    """

    producer.publish(
        msg, exchange=exchange,
        retry=retry, retry_policy=retry_policy,
        **dict({'routing_key': req.properties['reply_to'],
                'correlation_id': req.properties.get('correlation_id'),
                'serializer': serializers.type_to_name[req.content_type],
                'content_encoding': req.content_encoding}, **props)
    )


def collect_replies(conn, channel, queue, *args, **kwargs):
    """Generator collecting replies from ``queue``"""
    no_ack = kwargs.setdefault('no_ack', True)
    received = False
    try:
        for body, message in itermessages(conn, channel, queue,
                                          *args, **kwargs):
            if not no_ack:
                message.ack()
            received = True
            yield body
    finally:
        if received:
            channel.after_reply_message_received(queue.name)


def _ensure_errback(exc, interval):
    logger.error(
        'Connection error: %r. Retry in %ss\n', exc, interval,
        exc_info=True,
    )


@contextmanager
def _ignore_errors(conn):
    try:
        yield
    except conn.connection_errors + conn.channel_errors:
        pass


def ignore_errors(conn, fun=None, *args, **kwargs):
    """Ignore connection and channel errors.

    The first argument must be a connection object, or any other object
    with ``connection_error`` and ``channel_error`` attributes.

    Can be used as a function:

    .. code-block:: python

        def example(connection):
            ignore_errors(connection, consumer.channel.close)

    or as a context manager:

    .. code-block:: python

        def example(connection):
            with ignore_errors(connection):
                consumer.channel.close()


    .. note::

        Connection and channel errors should be properly handled,
        and not ignored.  Using this function is only acceptable in a cleanup
        phase, like when a connection is lost or at shutdown.

    """
    if fun:
        with _ignore_errors(conn):
            return fun(*args, **kwargs)
    return _ignore_errors(conn)


def revive_connection(connection, channel, on_revive=None):
    if on_revive:
        on_revive(channel)


def insured(pool, fun, args, kwargs, errback=None, on_revive=None, **opts):
    """Ensures function performing broker commands completes
    despite intermittent connection failures."""
    errback = errback or _ensure_errback

    with pool.acquire(block=True) as conn:
        conn.ensure_connection(errback=errback)
        # we cache the channel for subsequent calls, this has to be
        # reset on revival.
        channel = conn.default_channel
        revive = partial(revive_connection, conn, on_revive=on_revive)
        insured = conn.autoretry(fun, channel, errback=errback,
                                 on_revive=revive, **opts)
        retval, _ = insured(*args, **dict(kwargs, connection=conn))
        return retval


class QoS(object):
    """Thread safe increment/decrement of a channels prefetch_count.

    :param callback: Function used to set new prefetch count,
        e.g. ``consumer.qos`` or ``channel.basic_qos``.  Will be called
        with a single ``prefetch_count`` keyword argument.
    :param initial_value: Initial prefetch count value.

    **Example usage**

    .. code-block:: python

        >>> from kombu import Consumer, Connection
        >>> connection = Connection('amqp://')
        >>> consumer = Consumer(connection)
        >>> qos = QoS(consumer.qos, initial_prefetch_count=2)
        >>> qos.update()  # set initial

        >>> qos.value
        2

        >>> def in_some_thread():
        ...     qos.increment_eventually()

        >>> def in_some_other_thread():
        ...     qos.decrement_eventually()

        >>> while 1:
        ...    if qos.prev != qos.value:
        ...        qos.update()  # prefetch changed so update.

    It can be used with any function supporting a ``prefetch_count`` keyword
    argument::

        >>> channel = connection.channel()
        >>> QoS(channel.basic_qos, 10)


        >>> def set_qos(prefetch_count):
        ...     print('prefetch count now: %r' % (prefetch_count, ))
        >>> QoS(set_qos, 10)

    """
    prev = None

    def __init__(self, callback, initial_value):
        self.callback = callback
        self._mutex = threading.RLock()
        self.value = initial_value or 0

    def increment_eventually(self, n=1):
        """Increment the value, but do not update the channels QoS.

        The MainThread will be responsible for calling :meth:`update`
        when necessary.

        """
        with self._mutex:
            if self.value:
                self.value = self.value + max(n, 0)
        return self.value

    def decrement_eventually(self, n=1):
        """Decrement the value, but do not update the channels QoS.

        The MainThread will be responsible for calling :meth:`update`
        when necessary.

        """
        with self._mutex:
            if self.value:
                self.value -= n
                if self.value < 1:
                    self.value = 1
        return self.value

    def set(self, pcount):
        """Set channel prefetch_count setting."""
        if pcount != self.prev:
            new_value = pcount
            if pcount > PREFETCH_COUNT_MAX:
                logger.warn('QoS: Disabled: prefetch_count exceeds %r',
                            PREFETCH_COUNT_MAX)
                new_value = 0
            logger.debug('basic.qos: prefetch_count->%s', new_value)
            self.callback(prefetch_count=new_value)
            self.prev = pcount
        return pcount

    def update(self):
        """Update prefetch count with current value."""
        with self._mutex:
            return self.set(self.value)

########NEW FILE########
__FILENAME__ = compat
"""
kombu.compat
============

Carrot compatible interface for :class:`Publisher` and :class:`Producer`.

See http://packages.python.org/pypi/carrot for documentation.

"""
from __future__ import absolute_import

from itertools import count

from . import messaging
from .entity import Exchange, Queue
from .five import items

__all__ = ['Publisher', 'Consumer']

# XXX compat attribute
entry_to_queue = Queue.from_dict


def _iterconsume(connection, consumer, no_ack=False, limit=None):
    consumer.consume(no_ack=no_ack)
    for iteration in count(0):  # for infinity
        if limit and iteration >= limit:
            raise StopIteration
        yield connection.drain_events()


class Publisher(messaging.Producer):
    exchange = ''
    exchange_type = 'direct'
    routing_key = ''
    durable = True
    auto_delete = False
    _closed = False

    def __init__(self, connection, exchange=None, routing_key=None,
                 exchange_type=None, durable=None, auto_delete=None,
                 channel=None, **kwargs):
        if channel:
            connection = channel

        self.exchange = exchange or self.exchange
        self.exchange_type = exchange_type or self.exchange_type
        self.routing_key = routing_key or self.routing_key

        if auto_delete is not None:
            self.auto_delete = auto_delete
        if durable is not None:
            self.durable = durable

        if not isinstance(self.exchange, Exchange):
            self.exchange = Exchange(name=self.exchange,
                                     type=self.exchange_type,
                                     routing_key=self.routing_key,
                                     auto_delete=self.auto_delete,
                                     durable=self.durable)
        super(Publisher, self).__init__(connection, self.exchange, **kwargs)

    def send(self, *args, **kwargs):
        return self.publish(*args, **kwargs)

    def close(self):
        super(Publisher, self).close()
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    @property
    def backend(self):
        return self.channel


class Consumer(messaging.Consumer):
    queue = ''
    exchange = ''
    routing_key = ''
    exchange_type = 'direct'
    durable = True
    exclusive = False
    auto_delete = False
    exchange_type = 'direct'
    _closed = False

    def __init__(self, connection, queue=None, exchange=None,
                 routing_key=None, exchange_type=None, durable=None,
                 exclusive=None, auto_delete=None, **kwargs):
        self.backend = connection.channel()

        if durable is not None:
            self.durable = durable
        if exclusive is not None:
            self.exclusive = exclusive
        if auto_delete is not None:
            self.auto_delete = auto_delete

        self.queue = queue or self.queue
        self.exchange = exchange or self.exchange
        self.exchange_type = exchange_type or self.exchange_type
        self.routing_key = routing_key or self.routing_key

        exchange = Exchange(self.exchange,
                            type=self.exchange_type,
                            routing_key=self.routing_key,
                            auto_delete=self.auto_delete,
                            durable=self.durable)
        queue = Queue(self.queue,
                      exchange=exchange,
                      routing_key=self.routing_key,
                      durable=self.durable,
                      exclusive=self.exclusive,
                      auto_delete=self.auto_delete)
        super(Consumer, self).__init__(self.backend, queue, **kwargs)

    def revive(self, channel):
        self.backend = channel
        super(Consumer, self).revive(channel)

    def close(self):
        self.cancel()
        self.backend.close()
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def __iter__(self):
        return self.iterqueue(infinite=True)

    def fetch(self, no_ack=None, enable_callbacks=False):
        if no_ack is None:
            no_ack = self.no_ack
        message = self.queues[0].get(no_ack)
        if message:
            if enable_callbacks:
                self.receive(message.payload, message)
        return message

    def process_next(self):
        raise NotImplementedError('Use fetch(enable_callbacks=True)')

    def discard_all(self, filterfunc=None):
        if filterfunc is not None:
            raise NotImplementedError(
                'discard_all does not implement filters')
        return self.purge()

    def iterconsume(self, limit=None, no_ack=None):
        return _iterconsume(self.connection, self, no_ack, limit)

    def wait(self, limit=None):
        it = self.iterconsume(limit)
        return list(it)

    def iterqueue(self, limit=None, infinite=False):
        for items_since_start in count():  # for infinity
            item = self.fetch()
            if (not infinite and item is None) or \
                    (limit and items_since_start >= limit):
                raise StopIteration
            yield item


class ConsumerSet(messaging.Consumer):

    def __init__(self, connection, from_dict=None, consumers=None,
                 channel=None, **kwargs):
        if channel:
            self._provided_channel = True
            self.backend = channel
        else:
            self._provided_channel = False
            self.backend = connection.channel()

        queues = []
        if consumers:
            for consumer in consumers:
                queues.extend(consumer.queues)
        if from_dict:
            for queue_name, queue_options in items(from_dict):
                queues.append(Queue.from_dict(queue_name, **queue_options))

        super(ConsumerSet, self).__init__(self.backend, queues, **kwargs)

    def iterconsume(self, limit=None, no_ack=False):
        return _iterconsume(self.connection, self, no_ack, limit)

    def discard_all(self):
        return self.purge()

    def add_consumer_from_dict(self, queue, **options):
        return self.add_queue_from_dict(queue, **options)

    def add_consumer(self, consumer):
        for queue in consumer.queues:
            self.add_queue(queue)

    def revive(self, channel):
        self.backend = channel
        super(ConsumerSet, self).revive(channel)

    def close(self):
        self.cancel()
        if not self._provided_channel:
            self.channel.close()

########NEW FILE########
__FILENAME__ = compression
"""
kombu.compression
=================

Compression utilities.

"""
from __future__ import absolute_import

from kombu.utils.encoding import ensure_bytes

import zlib

_aliases = {}
_encoders = {}
_decoders = {}

__all__ = ['register', 'encoders', 'get_encoder',
           'get_decoder', 'compress', 'decompress']


def register(encoder, decoder, content_type, aliases=[]):
    """Register new compression method.

    :param encoder: Function used to compress text.
    :param decoder: Function used to decompress previously compressed text.
    :param content_type: The mime type this compression method identifies as.
    :param aliases: A list of names to associate with this compression method.

    """
    _encoders[content_type] = encoder
    _decoders[content_type] = decoder
    _aliases.update((alias, content_type) for alias in aliases)


def encoders():
    """Return a list of available compression methods."""
    return list(_encoders)


def get_encoder(t):
    """Get encoder by alias name."""
    t = _aliases.get(t, t)
    return _encoders[t], t


def get_decoder(t):
    """Get decoder by alias name."""
    return _decoders[_aliases.get(t, t)]


def compress(body, content_type):
    """Compress text.

    :param body: The text to compress.
    :param content_type: mime-type of compression method to use.

    """
    encoder, content_type = get_encoder(content_type)
    return encoder(ensure_bytes(body)), content_type


def decompress(body, content_type):
    """Decompress compressed text.

    :param body: Previously compressed text to uncompress.
    :param content_type: mime-type of compression method used.

    """
    return get_decoder(content_type)(body)


register(zlib.compress,
         zlib.decompress,
         'application/x-gzip', aliases=['gzip', 'zlib'])
try:
    import bz2
except ImportError:
    pass  # Jython?
else:
    register(bz2.compress,
             bz2.decompress,
             'application/x-bz2', aliases=['bzip2', 'bzip'])

########NEW FILE########
__FILENAME__ = connection
"""
kombu.connection
================

Broker connection and pools.

"""
from __future__ import absolute_import

import os
import socket

from collections import OrderedDict
from contextlib import contextmanager
from itertools import count, cycle
from operator import itemgetter

# jython breaks on relative import for .exceptions for some reason
# (Issue #112)
from kombu import exceptions
from .five import Empty, range, string_t, text_t, LifoQueue as _LifoQueue
from .log import get_logger
from .transport import get_transport_cls, supports_librabbitmq
from .utils import cached_property, retry_over_time, shufflecycle, HashedSeq
from .utils.functional import lazy
from .utils.url import as_url, parse_url, quote, urlparse

__all__ = ['Connection', 'ConnectionPool', 'ChannelPool']

RESOLVE_ALIASES = {'pyamqp': 'amqp',
                   'librabbitmq': 'amqp'}

_LOG_CONNECTION = os.environ.get('KOMBU_LOG_CONNECTION', False)
_LOG_CHANNEL = os.environ.get('KOMBU_LOG_CHANNEL', False)

logger = get_logger(__name__)
roundrobin_failover = cycle

failover_strategies = {
    'round-robin': roundrobin_failover,
    'shuffle': shufflecycle,
}


class Connection(object):
    """A connection to the broker.

    :param URL:  Broker URL, or a list of URLs, e.g.

    .. code-block:: python

        Connection('amqp://guest:guest@localhost:5672//')
        Connection('amqp://foo;amqp://bar', failover_strategy='round-robin')
        Connection('redis://', transport_options={
            'visibility_timeout': 3000,
        })

        import ssl
        Connection('amqp://', login_method='EXTERNAL', ssl={
            'ca_certs': '/etc/pki/tls/certs/something.crt',
            'keyfile': '/etc/something/system.key',
            'certfile': '/etc/something/system.cert',
            'cert_reqs': ssl.CERT_REQUIRED,
        })

    .. admonition:: SSL compatibility

        SSL currently only works with the py-amqp & amqplib transports.
        For other transports you can use stunnel.

    :keyword hostname: Default host name/address if not provided in the URL.
    :keyword userid: Default user name if not provided in the URL.
    :keyword password: Default password if not provided in the URL.
    :keyword virtual_host: Default virtual host if not provided in the URL.
    :keyword port: Default port if not provided in the URL.
    :keyword ssl: Use SSL to connect to the server. Default is ``False``.
      May not be supported by the specified transport.
    :keyword transport: Default transport if not specified in the URL.
    :keyword connect_timeout: Timeout in seconds for connecting to the
      server. May not be supported by the specified transport.
    :keyword transport_options: A dict of additional connection arguments to
      pass to alternate kombu channel implementations.  Consult the transport
      documentation for available options.
    :keyword heartbeat: Heartbeat interval in int/float seconds.
        Note that if heartbeats are enabled then the :meth:`heartbeat_check`
        method must be called regularly, around once per second.

    .. note::

        The connection is established lazily when needed. If you need the
        connection to be established, then force it by calling
        :meth:`connect`::

            >>> conn = Connection('amqp://')
            >>> conn.connect()

        and always remember to close the connection::

            >>> conn.release()

    """
    port = None
    virtual_host = '/'
    connect_timeout = 5

    _closed = None
    _connection = None
    _default_channel = None
    _transport = None
    _logger = False
    uri_prefix = None

    #: The cache of declared entities is per connection,
    #: in case the server loses data.
    declared_entities = None

    #: Iterator returning the next broker URL to try in the event
    #: of connection failure (initialized by :attr:`failover_strategy`).
    cycle = None

    #: Additional transport specific options,
    #: passed on to the transport instance.
    transport_options = None

    #: Strategy used to select new hosts when reconnecting after connection
    #: failure.  One of "round-robin", "shuffle" or any custom iterator
    #: constantly yielding new URLs to try.
    failover_strategy = 'round-robin'

    #: Heartbeat value, currently only supported by the py-amqp transport.
    heartbeat = None

    hostname = userid = password = ssl = login_method = None

    def __init__(self, hostname='localhost', userid=None,
                 password=None, virtual_host=None, port=None, insist=False,
                 ssl=False, transport=None, connect_timeout=5,
                 transport_options=None, login_method=None, uri_prefix=None,
                 heartbeat=0, failover_strategy='round-robin',
                 alternates=None, **kwargs):
        alt = [] if alternates is None else alternates
        # have to spell the args out, just to get nice docstrings :(
        params = self._initial_params = {
            'hostname': hostname, 'userid': userid,
            'password': password, 'virtual_host': virtual_host,
            'port': port, 'insist': insist, 'ssl': ssl,
            'transport': transport, 'connect_timeout': connect_timeout,
            'login_method': login_method, 'heartbeat': heartbeat
        }

        if hostname and not isinstance(hostname, string_t):
            alt.extend(hostname)
            hostname = alt[0]
        if hostname and '://' in hostname:
            if ';' in hostname:
                alt.extend(hostname.split(';'))
                hostname = alt[0]
            if '+' in hostname[:hostname.index('://')]:
                # e.g. sqla+mysql://root:masterkey@localhost/
                params['transport'], params['hostname'] = \
                    hostname.split('+', 1)
                transport = self.uri_prefix = params['transport']
            else:
                transport = transport or urlparse(hostname).scheme
                if get_transport_cls(transport).can_parse_url:
                    # set the transport so that the default is not used.
                    params['transport'] = transport
                else:
                    # we must parse the URL
                    params.update(parse_url(hostname))
        self._init_params(**params)

        # fallback hosts
        self.alt = alt
        self.failover_strategy = failover_strategies.get(
            failover_strategy or 'round-robin') or failover_strategy
        if self.alt:
            self.cycle = self.failover_strategy(self.alt)
            next(self.cycle)  # skip first entry

        if transport_options is None:
            transport_options = {}
        self.transport_options = transport_options

        if _LOG_CONNECTION:  # pragma: no cover
            self._logger = True

        if uri_prefix:
            self.uri_prefix = uri_prefix

        self.declared_entities = set()

    def switch(self, url):
        """Switch connection parameters to use a new URL (does not
        reconnect)"""
        self.close()
        self._closed = False
        self._init_params(**dict(self._initial_params, **parse_url(url)))

    def maybe_switch_next(self):
        """Switch to next URL given by the current failover strategy (if
        any)."""
        if self.cycle:
            self.switch(next(self.cycle))

    def _init_params(self, hostname, userid, password, virtual_host, port,
                     insist, ssl, transport, connect_timeout,
                     login_method, heartbeat):
        transport = transport or 'amqp'
        if transport == 'amqp' and supports_librabbitmq():
            transport = 'librabbitmq'
        self.hostname = hostname
        self.userid = userid
        self.password = password
        self.login_method = login_method
        self.virtual_host = virtual_host or self.virtual_host
        self.port = port or self.port
        self.insist = insist
        self.connect_timeout = connect_timeout
        self.ssl = ssl
        self.transport_cls = transport
        self.heartbeat = heartbeat and float(heartbeat)

    def register_with_event_loop(self, loop):
        self.transport.register_with_event_loop(self.connection, loop)

    def _debug(self, msg, *args, **kwargs):
        if self._logger:  # pragma: no cover
            fmt = '[Kombu connection:0x{id:x}] {msg}'
            logger.debug(fmt.format(id=id(self), msg=text_t(msg)),
                         *args, **kwargs)

    def connect(self):
        """Establish connection to server immediately."""
        self._closed = False
        return self.connection

    def channel(self):
        """Create and return a new channel."""
        self._debug('create channel')
        chan = self.transport.create_channel(self.connection)
        if _LOG_CHANNEL:  # pragma: no cover
            from .utils.debug import Logwrapped
            return Logwrapped(chan, 'kombu.channel',
                              '[Kombu channel:{0.channel_id}] ')
        return chan

    def heartbeat_check(self, rate=2):
        """Allow the transport to perform any periodic tasks
        required to make heartbeats work.  This should be called
        approximately every second.

        If the current transport does not support heartbeats then
        this is a noop operation.

        :keyword rate: Rate is how often the tick is called
            compared to the actual heartbeat value.  E.g. if
            the heartbeat is set to 3 seconds, and the tick
            is called every 3 / 2 seconds, then the rate is 2.
            This value is currently unused by any transports.

        """
        return self.transport.heartbeat_check(self.connection, rate=rate)

    def drain_events(self, **kwargs):
        """Wait for a single event from the server.

        :keyword timeout: Timeout in seconds before we give up.


        :raises :exc:`socket.timeout`: if the timeout is exceeded.

        """
        return self.transport.drain_events(self.connection, **kwargs)

    def maybe_close_channel(self, channel):
        """Close given channel, but ignore connection and channel errors."""
        try:
            channel.close()
        except (self.connection_errors + self.channel_errors):
            pass

    def _do_close_self(self):
        # Close only connection and channel(s), but not transport.
        self.declared_entities.clear()
        if self._default_channel:
            self.maybe_close_channel(self._default_channel)
        if self._connection:
            try:
                self.transport.close_connection(self._connection)
            except self.connection_errors + (AttributeError, socket.error):
                pass
            self._connection = None

    def _close(self):
        """Really close connection, even if part of a connection pool."""
        self._do_close_self()
        if self._transport:
            self._transport.client = None
            self._transport = None
        self._debug('closed')
        self._closed = True

    def collect(self, socket_timeout=None):
        # amqp requires communication to close, we don't need that just
        # to clear out references, Transport._collect can also be implemented
        # by other transports that want fast after fork
        try:
            gc_transport = self._transport._collect
        except AttributeError:
            _timeo = socket.getdefaulttimeout()
            socket.setdefaulttimeout(socket_timeout)
            try:
                self._close()
            except socket.timeout:
                pass
            finally:
                socket.setdefaulttimeout(_timeo)
        else:
            gc_transport(self._connection)
            if self._transport:
                self._transport.client = None
                self._transport = None
            self.declared_entities.clear()
            self._connection = None

    def release(self):
        """Close the connection (if open)."""
        self._close()
    close = release

    def ensure_connection(self, errback=None, max_retries=None,
                          interval_start=2, interval_step=2, interval_max=30,
                          callback=None):
        """Ensure we have a connection to the server.

        If not retry establishing the connection with the settings
        specified.

        :keyword errback: Optional callback called each time the connection
          can't be established. Arguments provided are the exception
          raised and the interval that will be slept ``(exc, interval)``.

        :keyword max_retries: Maximum number of times to retry.
          If this limit is exceeded the connection error will be re-raised.

        :keyword interval_start: The number of seconds we start sleeping for.
        :keyword interval_step: How many seconds added to the interval
          for each retry.
        :keyword interval_max: Maximum number of seconds to sleep between
          each retry.
        :keyword callback: Optional callback that is called for every
           internal iteration (1 s)

        """
        def on_error(exc, intervals, retries, interval=0):
            round = self.completes_cycle(retries)
            if round:
                interval = next(intervals)
            if errback:
                errback(exc, interval)
            self.maybe_switch_next()  # select next host

            return interval if round else 0

        retry_over_time(self.connect, self.recoverable_connection_errors,
                        (), {}, on_error, max_retries,
                        interval_start, interval_step, interval_max, callback)
        return self

    def completes_cycle(self, retries):
        """Return true if the cycle is complete after number of `retries`."""
        return not (retries + 1) % len(self.alt) if self.alt else True

    def revive(self, new_channel):
        """Revive connection after connection re-established."""
        if self._default_channel:
            self.maybe_close_channel(self._default_channel)
            self._default_channel = None

    def _default_ensure_callback(self, exc, interval):
        logger.error("Ensure: Operation error: %r. Retry in %ss",
                     exc, interval, exc_info=True)

    def ensure(self, obj, fun, errback=None, max_retries=None,
               interval_start=1, interval_step=1, interval_max=1,
               on_revive=None):
        """Ensure operation completes, regardless of any channel/connection
        errors occurring.

        Will retry by establishing the connection, and reapplying
        the function.

        :param fun: Method to apply.

        :keyword errback: Optional callback called each time the connection
          can't be established. Arguments provided are the exception
          raised and the interval that will be slept ``(exc, interval)``.

        :keyword max_retries: Maximum number of times to retry.
          If this limit is exceeded the connection error will be re-raised.

        :keyword interval_start: The number of seconds we start sleeping for.
        :keyword interval_step: How many seconds added to the interval
          for each retry.
        :keyword interval_max: Maximum number of seconds to sleep between
          each retry.

        **Example**

        This is an example ensuring a publish operation::

            >>> from kombu import Connection, Producer
            >>> conn = Connection('amqp://')
            >>> producer = Producer(conn)

            >>> def errback(exc, interval):
            ...     logger.error('Error: %r', exc, exc_info=1)
            ...     logger.info('Retry in %s seconds.', interval)

            >>> publish = conn.ensure(producer, producer.publish,
            ...                       errback=errback, max_retries=3)
            >>> publish({'hello': 'world'}, routing_key='dest')

        """
        def _ensured(*args, **kwargs):
            got_connection = 0
            conn_errors = self.recoverable_connection_errors
            chan_errors = self.recoverable_channel_errors
            has_modern_errors = hasattr(
                self.transport, 'recoverable_connection_errors',
            )
            for retries in count(0):  # for infinity
                try:
                    return fun(*args, **kwargs)
                except conn_errors as exc:
                    if got_connection and not has_modern_errors:
                        # transport can not distinguish between
                        # recoverable/irrecoverable errors, so we propagate
                        # the error if it persists after a new connection was
                        # successfully established.
                        raise
                    if max_retries is not None and retries > max_retries:
                        raise
                    self._debug('ensure connection error: %r', exc, exc_info=1)
                    self._connection = None
                    self._do_close_self()
                    errback and errback(exc, 0)
                    remaining_retries = None
                    if max_retries is not None:
                        remaining_retries = max(max_retries - retries, 1)
                    self.ensure_connection(errback,
                                           remaining_retries,
                                           interval_start,
                                           interval_step,
                                           interval_max)
                    new_channel = self.channel()
                    self.revive(new_channel)
                    obj.revive(new_channel)
                    if on_revive:
                        on_revive(new_channel)
                    got_connection += 1
                except chan_errors as exc:
                    if max_retries is not None and retries > max_retries:
                        raise
                    self._debug('ensure channel error: %r', exc, exc_info=1)
                    errback and errback(exc, 0)
        _ensured.__name__ = "%s(ensured)" % fun.__name__
        _ensured.__doc__ = fun.__doc__
        _ensured.__module__ = fun.__module__
        return _ensured

    def autoretry(self, fun, channel=None, **ensure_options):
        """Decorator for functions supporting a ``channel`` keyword argument.

        The resulting callable will retry calling the function if
        it raises connection or channel related errors.
        The return value will be a tuple of ``(retval, last_created_channel)``.

        If a ``channel`` is not provided, then one will be automatically
        acquired (remember to close it afterwards).

        See :meth:`ensure` for the full list of supported keyword arguments.

        Example usage::

            channel = connection.channel()
            try:
                ret, channel = connection.autoretry(publish_messages, channel)
            finally:
                channel.close()
        """
        channels = [channel]
        create_channel = self.channel

        class Revival(object):
            __name__ = fun.__name__
            __module__ = fun.__module__
            __doc__ = fun.__doc__

            def revive(self, channel):
                channels[0] = channel

            def __call__(self, *args, **kwargs):
                if channels[0] is None:
                    self.revive(create_channel())
                return fun(*args, channel=channels[0], **kwargs), channels[0]

        revive = Revival()
        return self.ensure(revive, revive, **ensure_options)

    def create_transport(self):
        return self.get_transport_cls()(client=self)

    def get_transport_cls(self):
        """Get the currently used transport class."""
        transport_cls = self.transport_cls
        if not transport_cls or isinstance(transport_cls, string_t):
            transport_cls = get_transport_cls(transport_cls)
        return transport_cls

    def clone(self, **kwargs):
        """Create a copy of the connection with the same connection
        settings."""
        return self.__class__(**dict(self._info(resolve=False), **kwargs))

    def get_heartbeat_interval(self):
        return self.transport.get_heartbeat_interval(self.connection)

    def _info(self, resolve=True):
        transport_cls = self.transport_cls
        if resolve:
            transport_cls = RESOLVE_ALIASES.get(transport_cls, transport_cls)
        D = self.transport.default_connection_params

        hostname = self.hostname or D.get('hostname')
        if self.uri_prefix:
            hostname = '%s+%s' % (self.uri_prefix, hostname)

        info = (
            ('hostname', hostname),
            ('userid', self.userid or D.get('userid')),
            ('password', self.password or D.get('password')),
            ('virtual_host', self.virtual_host or D.get('virtual_host')),
            ('port', self.port or D.get('port')),
            ('insist', self.insist),
            ('ssl', self.ssl),
            ('transport', transport_cls),
            ('connect_timeout', self.connect_timeout),
            ('transport_options', self.transport_options),
            ('login_method', self.login_method or D.get('login_method')),
            ('uri_prefix', self.uri_prefix),
            ('heartbeat', self.heartbeat),
            ('alternates', self.alt),
        )
        return info

    def info(self):
        """Get connection info."""
        return OrderedDict(self._info())

    def __eqhash__(self):
        return HashedSeq(self.transport_cls, self.hostname, self.userid,
                         self.password, self.virtual_host, self.port,
                         repr(self.transport_options))

    def as_uri(self, include_password=False, mask='**',
               getfields=itemgetter('port', 'userid', 'password',
                                    'virtual_host', 'transport')):
        """Convert connection parameters to URL form."""
        hostname = self.hostname or 'localhost'
        if self.transport.can_parse_url:
            if self.uri_prefix:
                return '%s+%s' % (self.uri_prefix, hostname)
            return self.hostname
        fields = self.info()
        port, userid, password, vhost, transport = getfields(fields)
        scheme = ('{0}+{1}'.format(self.uri_prefix, transport)
                  if self.uri_prefix else transport)
        return as_url(
            scheme, hostname, port, userid, password, quote(vhost),
            sanitize=not include_password, mask=mask,
        )

    def Pool(self, limit=None, preload=None):
        """Pool of connections.

        See :class:`ConnectionPool`.

        :keyword limit: Maximum number of active connections.
          Default is no limit.
        :keyword preload: Number of connections to preload
          when the pool is created.  Default is 0.

        *Example usage*::

            >>> connection = Connection('amqp://')
            >>> pool = connection.Pool(2)
            >>> c1 = pool.acquire()
            >>> c2 = pool.acquire()
            >>> c3 = pool.acquire()
            Traceback (most recent call last):
              File "<stdin>", line 1, in <module>
              File "kombu/connection.py", line 354, in acquire
              raise ConnectionLimitExceeded(self.limit)
                kombu.exceptions.ConnectionLimitExceeded: 2
            >>> c1.release()
            >>> c3 = pool.acquire()

        """
        return ConnectionPool(self, limit, preload)

    def ChannelPool(self, limit=None, preload=None):
        """Pool of channels.

        See :class:`ChannelPool`.

        :keyword limit: Maximum number of active channels.
          Default is no limit.
        :keyword preload: Number of channels to preload
          when the pool is created.  Default is 0.

        *Example usage*::

            >>> connection = Connection('amqp://')
            >>> pool = connection.ChannelPool(2)
            >>> c1 = pool.acquire()
            >>> c2 = pool.acquire()
            >>> c3 = pool.acquire()
            Traceback (most recent call last):
              File "<stdin>", line 1, in <module>
              File "kombu/connection.py", line 354, in acquire
              raise ChannelLimitExceeded(self.limit)
                kombu.connection.ChannelLimitExceeded: 2
            >>> c1.release()
            >>> c3 = pool.acquire()

        """
        return ChannelPool(self, limit, preload)

    def Producer(self, channel=None, *args, **kwargs):
        """Create new :class:`kombu.Producer` instance using this
        connection."""
        from .messaging import Producer
        return Producer(channel or self, *args, **kwargs)

    def Consumer(self, queues=None, channel=None, *args, **kwargs):
        """Create new :class:`kombu.Consumer` instance using this
        connection."""
        from .messaging import Consumer
        return Consumer(channel or self, queues, *args, **kwargs)

    def SimpleQueue(self, name, no_ack=None, queue_opts=None,
                    exchange_opts=None, channel=None, **kwargs):
        """Create new :class:`~kombu.simple.SimpleQueue`, using a channel
        from this connection.

        If ``name`` is a string, a queue and exchange will be automatically
        created using that name as the name of the queue and exchange,
        also it will be used as the default routing key.

        :param name: Name of the queue/or a :class:`~kombu.Queue`.
        :keyword no_ack: Disable acknowledgements. Default is false.
        :keyword queue_opts: Additional keyword arguments passed to the
          constructor of the automatically created
          :class:`~kombu.Queue`.
        :keyword exchange_opts: Additional keyword arguments passed to the
          constructor of the automatically created
          :class:`~kombu.Exchange`.
        :keyword channel: Custom channel to use. If not specified the
            connection default channel is used.

        """
        from .simple import SimpleQueue
        return SimpleQueue(channel or self, name, no_ack, queue_opts,
                           exchange_opts, **kwargs)

    def SimpleBuffer(self, name, no_ack=None, queue_opts=None,
                     exchange_opts=None, channel=None, **kwargs):
        """Create new :class:`~kombu.simple.SimpleQueue` using a channel
        from this connection.

        Same as :meth:`SimpleQueue`, but configured with buffering
        semantics. The resulting queue and exchange will not be durable, also
        auto delete is enabled. Messages will be transient (not persistent),
        and acknowledgements are disabled (``no_ack``).

        """
        from .simple import SimpleBuffer
        return SimpleBuffer(channel or self, name, no_ack, queue_opts,
                            exchange_opts, **kwargs)

    def _establish_connection(self):
        self._debug('establishing connection...')
        conn = self.transport.establish_connection()
        self._debug('connection established: %r', conn)
        return conn

    def __repr__(self):
        """``x.__repr__() <==> repr(x)``"""
        return '<Connection: {0} at 0x{1:x}>'.format(self.as_uri(), id(self))

    def __copy__(self):
        """``x.__copy__() <==> copy(x)``"""
        return self.clone()

    def __reduce__(self):
        return self.__class__, tuple(self.info().values()), None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()

    @property
    def qos_semantics_matches_spec(self):
        return self.transport.qos_semantics_matches_spec(self.connection)

    @property
    def connected(self):
        """Return true if the connection has been established."""
        return (not self._closed and
                self._connection is not None and
                self.transport.verify_connection(self._connection))

    @property
    def connection(self):
        """The underlying connection object.

        .. warning::
            This instance is transport specific, so do not
            depend on the interface of this object.

        """
        if not self._closed:
            if not self.connected:
                self.declared_entities.clear()
                self._default_channel = None
                self._connection = self._establish_connection()
                self._closed = False
            return self._connection

    @property
    def default_channel(self):
        """Default channel, created upon access and closed when the connection
        is closed.

        Can be used for automatic channel handling when you only need one
        channel, and also it is the channel implicitly used if a connection
        is passed instead of a channel, to functions that require a channel.

        """
        # make sure we're still connected, and if not refresh.
        self.connection
        if self._default_channel is None:
            self._default_channel = self.channel()
        return self._default_channel

    @property
    def host(self):
        """The host as a host name/port pair separated by colon."""
        return ':'.join([self.hostname, str(self.port)])

    @property
    def transport(self):
        if self._transport is None:
            self._transport = self.create_transport()
        return self._transport

    @cached_property
    def manager(self):
        """Experimental manager that can be used to manage/monitor the broker
        instance.  Not available for all transports."""
        return self.transport.manager

    def get_manager(self, *args, **kwargs):
        return self.transport.get_manager(*args, **kwargs)

    @cached_property
    def recoverable_connection_errors(self):
        """List of connection related exceptions that can be recovered from,
        but where the connection must be closed and re-established first."""
        try:
            return self.transport.recoverable_connection_errors
        except AttributeError:
            # There were no such classification before,
            # and all errors were assumed to be recoverable,
            # so this is a fallback for transports that do
            # not support the new recoverable/irrecoverable classes.
            return self.connection_errors + self.channel_errors

    @cached_property
    def recoverable_channel_errors(self):
        """List of channel related exceptions that can be automatically
        recovered from without re-establishing the connection."""
        try:
            return self.transport.recoverable_channel_errors
        except AttributeError:
            return ()

    @cached_property
    def connection_errors(self):
        """List of exceptions that may be raised by the connection."""
        return self.transport.connection_errors

    @cached_property
    def channel_errors(self):
        """List of exceptions that may be raised by the channel."""
        return self.transport.channel_errors

    @property
    def supports_heartbeats(self):
        return self.transport.supports_heartbeats

    @property
    def is_evented(self):
        return self.transport.supports_ev
BrokerConnection = Connection


class Resource(object):
    LimitExceeded = exceptions.LimitExceeded

    def __init__(self, limit=None, preload=None):
        self.limit = limit
        self.preload = preload or 0
        self._closed = False

        self._resource = _LifoQueue()
        self._dirty = set()
        self.setup()

    def setup(self):
        raise NotImplementedError('subclass responsibility')

    def _add_when_empty(self):
        if self.limit and len(self._dirty) >= self.limit:
            raise self.LimitExceeded(self.limit)
        # All taken, put new on the queue and
        # try get again, this way the first in line
        # will get the resource.
        self._resource.put_nowait(self.new())

    def acquire(self, block=False, timeout=None):
        """Acquire resource.

        :keyword block: If the limit is exceeded,
          block until there is an available item.
        :keyword timeout: Timeout to wait
          if ``block`` is true. Default is :const:`None` (forever).

        :raises LimitExceeded: if block is false
          and the limit has been exceeded.

        """
        if self._closed:
            raise RuntimeError('Acquire on closed pool')
        if self.limit:
            while 1:
                try:
                    R = self._resource.get(block=block, timeout=timeout)
                except Empty:
                    self._add_when_empty()
                else:
                    try:
                        R = self.prepare(R)
                    except BaseException:
                        if isinstance(R, lazy):
                            # no evaluated yet, just put it back
                            self._resource.put_nowait(R)
                        else:
                            # evaluted so must try to release/close first.
                            self.release(R)
                        raise
                    self._dirty.add(R)
                    break
        else:
            R = self.prepare(self.new())

        def release():
            """Release resource so it can be used by another thread.

            The caller is responsible for discarding the object,
            and to never use the resource again.  A new resource must
            be acquired if so needed.

            """
            self.release(R)
        R.release = release

        return R

    def prepare(self, resource):
        return resource

    def close_resource(self, resource):
        resource.close()

    def release_resource(self, resource):
        pass

    def replace(self, resource):
        """Replace resource with a new instance.  This can be used in case
        of defective resources."""
        if self.limit:
            self._dirty.discard(resource)
        self.close_resource(resource)

    def release(self, resource):
        if self.limit:
            self._dirty.discard(resource)
            self._resource.put_nowait(resource)
            self.release_resource(resource)
        else:
            self.close_resource(resource)

    def collect_resource(self, resource):
        pass

    def force_close_all(self):
        """Close and remove all resources in the pool (also those in use).

        Can be used to close resources from parent processes
        after fork (e.g. sockets/connections).

        """
        self._closed = True
        dirty = self._dirty
        resource = self._resource
        while 1:  # - acquired
            try:
                dres = dirty.pop()
            except KeyError:
                break
            try:
                self.collect_resource(dres)
            except AttributeError:  # Issue #78
                pass
        while 1:  # - available
            # deque supports '.clear', but lists do not, so for that
            # reason we use pop here, so that the underlying object can
            # be any object supporting '.pop' and '.append'.
            try:
                res = resource.queue.pop()
            except IndexError:
                break
            try:
                self.collect_resource(res)
            except AttributeError:
                pass  # Issue #78

    if os.environ.get('KOMBU_DEBUG_POOL'):  # pragma: no cover
        _orig_acquire = acquire
        _orig_release = release

        _next_resource_id = 0

        def acquire(self, *args, **kwargs):  # noqa
            import traceback
            id = self._next_resource_id = self._next_resource_id + 1
            print('+{0} ACQUIRE {1}'.format(id, self.__class__.__name__))
            r = self._orig_acquire(*args, **kwargs)
            r._resource_id = id
            print('-{0} ACQUIRE {1}'.format(id, self.__class__.__name__))
            if not hasattr(r, 'acquired_by'):
                r.acquired_by = []
            r.acquired_by.append(traceback.format_stack())
            return r

        def release(self, resource):  # noqa
            id = resource._resource_id
            print('+{0} RELEASE {1}'.format(id, self.__class__.__name__))
            r = self._orig_release(resource)
            print('-{0} RELEASE {1}'.format(id, self.__class__.__name__))
            self._next_resource_id -= 1
            return r


class ConnectionPool(Resource):
    LimitExceeded = exceptions.ConnectionLimitExceeded

    def __init__(self, connection, limit=None, preload=None):
        self.connection = connection
        super(ConnectionPool, self).__init__(limit=limit,
                                             preload=preload)

    def new(self):
        return self.connection.clone()

    def release_resource(self, resource):
        try:
            resource._debug('released')
        except AttributeError:
            pass

    def close_resource(self, resource):
        resource._close()

    def collect_resource(self, resource, socket_timeout=0.1):
        return resource.collect(socket_timeout)

    @contextmanager
    def acquire_channel(self, block=False):
        with self.acquire(block=block) as connection:
            yield connection, connection.default_channel

    def setup(self):
        if self.limit:
            for i in range(self.limit):
                if i < self.preload:
                    conn = self.new()
                    conn.connect()
                else:
                    conn = lazy(self.new)
                self._resource.put_nowait(conn)

    def prepare(self, resource):
        if callable(resource):
            resource = resource()
        resource._debug('acquired')
        return resource


class ChannelPool(Resource):
    LimitExceeded = exceptions.ChannelLimitExceeded

    def __init__(self, connection, limit=None, preload=None):
        self.connection = connection
        super(ChannelPool, self).__init__(limit=limit,
                                          preload=preload)

    def new(self):
        return lazy(self.connection.channel)

    def setup(self):
        channel = self.new()
        if self.limit:
            for i in range(self.limit):
                self._resource.put_nowait(
                    i < self.preload and channel() or lazy(channel))

    def prepare(self, channel):
        if callable(channel):
            channel = channel()
        return channel


def maybe_channel(channel):
    """Return the default channel if argument is a connection instance,
    otherwise just return the channel given."""
    if isinstance(channel, Connection):
        return channel.default_channel
    return channel


def is_connection(obj):
    return isinstance(obj, Connection)

########NEW FILE########
__FILENAME__ = entity
"""
kombu.entity
================

Exchange and Queue declarations.

"""
from __future__ import absolute_import

from .abstract import MaybeChannelBound
from .exceptions import ContentDisallowed
from .serialization import prepare_accept_content

TRANSIENT_DELIVERY_MODE = 1
PERSISTENT_DELIVERY_MODE = 2
DELIVERY_MODES = {'transient': TRANSIENT_DELIVERY_MODE,
                  'persistent': PERSISTENT_DELIVERY_MODE}

__all__ = ['Exchange', 'Queue', 'binding']


def pretty_bindings(bindings):
    return '[%s]' % (', '.join(map(str, bindings)))


class Exchange(MaybeChannelBound):
    """An Exchange declaration.

    :keyword name: See :attr:`name`.
    :keyword type: See :attr:`type`.
    :keyword channel: See :attr:`channel`.
    :keyword durable: See :attr:`durable`.
    :keyword auto_delete: See :attr:`auto_delete`.
    :keyword delivery_mode: See :attr:`delivery_mode`.
    :keyword arguments: See :attr:`arguments`.

    .. attribute:: name

        Name of the exchange. Default is no name (the default exchange).

    .. attribute:: type

        *This description of AMQP exchange types was shamelessly stolen
        from the blog post `AMQP in 10 minutes: Part 4`_ by
        Rajith Attapattu. Reading this article is recommended if you're
        new to amqp.*

        "AMQP defines four default exchange types (routing algorithms) that
        covers most of the common messaging use cases. An AMQP broker can
        also define additional exchange types, so see your broker
        manual for more information about available exchange types.

            * `direct` (*default*)

                Direct match between the routing key in the message, and the
                routing criteria used when a queue is bound to this exchange.

            * `topic`

                Wildcard match between the routing key and the routing pattern
                specified in the exchange/queue binding. The routing key is
                treated as zero or more words delimited by `"."` and
                supports special wildcard characters. `"*"` matches a
                single word and `"#"` matches zero or more words.

            * `fanout`

                Queues are bound to this exchange with no arguments. Hence any
                message sent to this exchange will be forwarded to all queues
                bound to this exchange.

            * `headers`

                Queues are bound to this exchange with a table of arguments
                containing headers and values (optional). A special argument
                named "x-match" determines the matching algorithm, where
                `"all"` implies an `AND` (all pairs must match) and
                `"any"` implies `OR` (at least one pair must match).

                :attr:`arguments` is used to specify the arguments.


            .. _`AMQP in 10 minutes: Part 4`:
                http://bit.ly/amqp-exchange-types

    .. attribute:: channel

        The channel the exchange is bound to (if bound).

    .. attribute:: durable

        Durable exchanges remain active when a server restarts. Non-durable
        exchanges (transient exchanges) are purged when a server restarts.
        Default is :const:`True`.

    .. attribute:: auto_delete

        If set, the exchange is deleted when all queues have finished
        using it. Default is :const:`False`.

    .. attribute:: delivery_mode

        The default delivery mode used for messages. The value is an integer,
        or alias string.

            * 1 or `"transient"`

                The message is transient. Which means it is stored in
                memory only, and is lost if the server dies or restarts.

            * 2 or "persistent" (*default*)
                The message is persistent. Which means the message is
                stored both in-memory, and on disk, and therefore
                preserved if the server dies or restarts.

        The default value is 2 (persistent).

    .. attribute:: arguments

        Additional arguments to specify when the exchange is declared.

    """
    TRANSIENT_DELIVERY_MODE = TRANSIENT_DELIVERY_MODE
    PERSISTENT_DELIVERY_MODE = PERSISTENT_DELIVERY_MODE

    name = ''
    type = 'direct'
    durable = True
    auto_delete = False
    passive = False
    delivery_mode = PERSISTENT_DELIVERY_MODE

    attrs = (
        ('name', None),
        ('type', None),
        ('arguments', None),
        ('durable', bool),
        ('passive', bool),
        ('auto_delete', bool),
        ('delivery_mode', lambda m: DELIVERY_MODES.get(m) or m),
    )

    def __init__(self, name='', type='', channel=None, **kwargs):
        super(Exchange, self).__init__(**kwargs)
        self.name = name or self.name
        self.type = type or self.type
        self.maybe_bind(channel)

    def __hash__(self):
        return hash('E|%s' % (self.name, ))

    def declare(self, nowait=False, passive=None):
        """Declare the exchange.

        Creates the exchange on the broker.

        :keyword nowait: If set the server will not respond, and a
            response will not be waited for. Default is :const:`False`.

        """
        passive = self.passive if passive is None else passive
        if self.name:
            return self.channel.exchange_declare(
                exchange=self.name, type=self.type, durable=self.durable,
                auto_delete=self.auto_delete, arguments=self.arguments,
                nowait=nowait, passive=passive,
            )

    def bind_to(self, exchange='', routing_key='',
                arguments=None, nowait=False, **kwargs):
        """Binds the exchange to another exchange.

        :keyword nowait: If set the server will not respond, and the call
            will not block waiting for a response.  Default is :const:`False`.

        """
        if isinstance(exchange, Exchange):
            exchange = exchange.name
        return self.channel.exchange_bind(destination=self.name,
                                          source=exchange,
                                          routing_key=routing_key,
                                          nowait=nowait,
                                          arguments=arguments)

    def unbind_from(self, source='', routing_key='',
                    nowait=False, arguments=None):
        """Delete previously created exchange binding from the server."""
        if isinstance(source, Exchange):
            source = source.name
        return self.channel.exchange_unbind(destination=self.name,
                                            source=source,
                                            routing_key=routing_key,
                                            nowait=nowait,
                                            arguments=arguments)

    def Message(self, body, delivery_mode=None, priority=None,
                content_type=None, content_encoding=None,
                properties=None, headers=None):
        """Create message instance to be sent with :meth:`publish`.

        :param body: Message body.

        :keyword delivery_mode: Set custom delivery mode. Defaults
            to :attr:`delivery_mode`.

        :keyword priority: Message priority, 0 to 9. (currently not
            supported by RabbitMQ).

        :keyword content_type: The messages content_type. If content_type
            is set, no serialization occurs as it is assumed this is either
            a binary object, or you've done your own serialization.
            Leave blank if using built-in serialization as our library
            properly sets content_type.

        :keyword content_encoding: The character set in which this object
            is encoded. Use "binary" if sending in raw binary objects.
            Leave blank if using built-in serialization as our library
            properly sets content_encoding.

        :keyword properties: Message properties.

        :keyword headers: Message headers.

        """
        properties = {} if properties is None else properties
        dm = delivery_mode or self.delivery_mode
        properties['delivery_mode'] = \
            DELIVERY_MODES[dm] if (dm != 2 and dm != 1) else dm
        return self.channel.prepare_message(body,
                                            properties=properties,
                                            priority=priority,
                                            content_type=content_type,
                                            content_encoding=content_encoding,
                                            headers=headers)

    def publish(self, message, routing_key=None, mandatory=False,
                immediate=False, exchange=None):
        """Publish message.

        :param message: :meth:`Message` instance to publish.
        :param routing_key: Routing key.
        :param mandatory: Currently not supported.
        :param immediate: Currently not supported.

        """
        exchange = exchange or self.name
        return self.channel.basic_publish(message,
                                          exchange=exchange,
                                          routing_key=routing_key,
                                          mandatory=mandatory,
                                          immediate=immediate)

    def delete(self, if_unused=False, nowait=False):
        """Delete the exchange declaration on server.

        :keyword if_unused: Delete only if the exchange has no bindings.
            Default is :const:`False`.

        :keyword nowait: If set the server will not respond, and a
            response will not be waited for. Default is :const:`False`.

        """
        return self.channel.exchange_delete(exchange=self.name,
                                            if_unused=if_unused,
                                            nowait=nowait)

    def binding(self, routing_key='', arguments=None, unbind_arguments=None):
        return binding(self, routing_key, arguments, unbind_arguments)

    def __eq__(self, other):
        if isinstance(other, Exchange):
            return (self.name == other.name and
                    self.type == other.type and
                    self.arguments == other.arguments and
                    self.durable == other.durable and
                    self.auto_delete == other.auto_delete and
                    self.delivery_mode == other.delivery_mode)
        return NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return super(Exchange, self).__repr__(str(self))

    def __str__(self):
        return 'Exchange %s(%s)' % (self.name or repr(''), self.type)

    @property
    def can_cache_declaration(self):
        return self.durable and not self.auto_delete


class binding(object):
    """Represents a queue or exchange binding.

    :keyword exchange: Exchange to bind to.
    :keyword routing_key: Routing key used as binding key.
    :keyword arguments: Arguments for bind operation.
    :keyword unbind_arguments: Arguments for unbind operation.

    """

    def __init__(self, exchange=None, routing_key='',
                 arguments=None, unbind_arguments=None):
        self.exchange = exchange
        self.routing_key = routing_key
        self.arguments = arguments
        self.unbind_arguments = unbind_arguments

    def declare(self, channel, nowait=False):
        """Declare destination exchange."""
        if self.exchange and self.exchange.name:
            ex = self.exchange(channel)
            ex.declare(nowait=nowait)

    def bind(self, entity, nowait=False):
        """Bind entity to this binding."""
        entity.bind_to(exchange=self.exchange,
                       routing_key=self.routing_key,
                       arguments=self.arguments,
                       nowait=nowait)

    def unbind(self, entity, nowait=False):
        """Unbind entity from this binding."""
        entity.unbind_from(self.exchange,
                           routing_key=self.routing_key,
                           arguments=self.unbind_arguments,
                           nowait=nowait)

    def __repr__(self):
        return '<binding: %s>' % (self, )

    def __str__(self):
        return '%s->%s' % (self.exchange.name, self.routing_key)


class Queue(MaybeChannelBound):
    """A Queue declaration.

    :keyword name: See :attr:`name`.
    :keyword exchange: See :attr:`exchange`.
    :keyword routing_key: See :attr:`routing_key`.
    :keyword channel: See :attr:`channel`.
    :keyword durable: See :attr:`durable`.
    :keyword exclusive: See :attr:`exclusive`.
    :keyword auto_delete: See :attr:`auto_delete`.
    :keyword queue_arguments: See :attr:`queue_arguments`.
    :keyword binding_arguments: See :attr:`binding_arguments`.
    :keyword on_declared: See :attr:`on_declared`

    .. attribute:: name

        Name of the queue. Default is no name (default queue destination).

    .. attribute:: exchange

        The :class:`Exchange` the queue binds to.

    .. attribute:: routing_key

        The routing key (if any), also called *binding key*.

        The interpretation of the routing key depends on
        the :attr:`Exchange.type`.

            * direct exchange

                Matches if the routing key property of the message and
                the :attr:`routing_key` attribute are identical.

            * fanout exchange

                Always matches, even if the binding does not have a key.

            * topic exchange

                Matches the routing key property of the message by a primitive
                pattern matching scheme. The message routing key then consists
                of words separated by dots (`"."`, like domain names), and
                two special characters are available; star (`"*"`) and hash
                (`"#"`). The star matches any word, and the hash matches
                zero or more words. For example `"*.stock.#"` matches the
                routing keys `"usd.stock"` and `"eur.stock.db"` but not
                `"stock.nasdaq"`.

    .. attribute:: channel

        The channel the Queue is bound to (if bound).

    .. attribute:: durable

        Durable queues remain active when a server restarts.
        Non-durable queues (transient queues) are purged if/when
        a server restarts.
        Note that durable queues do not necessarily hold persistent
        messages, although it does not make sense to send
        persistent messages to a transient queue.

        Default is :const:`True`.

    .. attribute:: exclusive

        Exclusive queues may only be consumed from by the
        current connection. Setting the 'exclusive' flag
        always implies 'auto-delete'.

        Default is :const:`False`.

    .. attribute:: auto_delete

        If set, the queue is deleted when all consumers have
        finished using it. Last consumer can be cancelled
        either explicitly or because its channel is closed. If
        there was no consumer ever on the queue, it won't be
        deleted.

    .. attribute:: queue_arguments

        Additional arguments used when declaring the queue.

    .. attribute:: binding_arguments

        Additional arguments used when binding the queue.

    .. attribute:: alias

        Unused in Kombu, but applications can take advantage of this.
        For example to give alternate names to queues with automatically
        generated queue names.

    .. attribute:: on_declared

        Optional callback to be applied when the queue has been
        declared (the ``queue_declare`` operation is complete).
        This must be a function with a signature that accepts at least 3
        positional arguments: ``(name, messages, consumers)``.

    """
    ContentDisallowed = ContentDisallowed

    name = ''
    exchange = Exchange('')
    routing_key = ''

    durable = True
    exclusive = False
    auto_delete = False
    no_ack = False

    attrs = (
        ('name', None),
        ('exchange', None),
        ('routing_key', None),
        ('queue_arguments', None),
        ('binding_arguments', None),
        ('durable', bool),
        ('exclusive', bool),
        ('auto_delete', bool),
        ('no_ack', None),
        ('alias', None),
        ('bindings', list),
    )

    def __init__(self, name='', exchange=None, routing_key='',
                 channel=None, bindings=None, on_declared=None,
                 **kwargs):
        super(Queue, self).__init__(**kwargs)
        self.name = name or self.name
        self.exchange = exchange or self.exchange
        self.routing_key = routing_key or self.routing_key
        self.bindings = set(bindings or [])
        self.on_declared = on_declared

        # allows Queue('name', [binding(...), binding(...), ...])
        if isinstance(exchange, (list, tuple, set)):
            self.bindings |= set(exchange)
        if self.bindings:
            self.exchange = None

        # exclusive implies auto-delete.
        if self.exclusive:
            self.auto_delete = True
        self.maybe_bind(channel)

    def bind(self, channel):
        on_declared = self.on_declared
        bound = super(Queue, self).bind(channel)
        bound.on_declared = on_declared
        return bound

    def __hash__(self):
        return hash('Q|%s' % (self.name, ))

    def when_bound(self):
        if self.exchange:
            self.exchange = self.exchange(self.channel)

    def declare(self, nowait=False):
        """Declares the queue, the exchange and binds the queue to
        the exchange."""
        # - declare main binding.
        if self.exchange:
            self.exchange.declare(nowait)
        self.queue_declare(nowait, passive=False)

        if self.exchange and self.exchange.name:
            self.queue_bind(nowait)

        # - declare extra/multi-bindings.
        for B in self.bindings:
            B.declare(self.channel)
            B.bind(self, nowait=nowait)
        return self.name

    def queue_declare(self, nowait=False, passive=False):
        """Declare queue on the server.

        :keyword nowait: Do not wait for a reply.
        :keyword passive: If set, the server will not create the queue.
            The client can use this to check whether a queue exists
            without modifying the server state.

        """
        ret = self.channel.queue_declare(queue=self.name,
                                         passive=passive,
                                         durable=self.durable,
                                         exclusive=self.exclusive,
                                         auto_delete=self.auto_delete,
                                         arguments=self.queue_arguments,
                                         nowait=nowait)
        if not self.name:
            self.name = ret[0]
        if self.on_declared:
            self.on_declared(*ret)
        return ret

    def queue_bind(self, nowait=False):
        """Create the queue binding on the server."""
        return self.bind_to(self.exchange, self.routing_key,
                            self.binding_arguments, nowait=nowait)

    def bind_to(self, exchange='', routing_key='',
                arguments=None, nowait=False):
        if isinstance(exchange, Exchange):
            exchange = exchange.name
        return self.channel.queue_bind(queue=self.name,
                                       exchange=exchange,
                                       routing_key=routing_key,
                                       arguments=arguments,
                                       nowait=nowait)

    def get(self, no_ack=None, accept=None):
        """Poll the server for a new message.

        Must return the message if a message was available,
        or :const:`None` otherwise.

        :keyword no_ack: If enabled the broker will automatically
            ack messages.
        :keyword accept: Custom list of accepted content types.

        This method provides direct access to the messages in a
        queue using a synchronous dialogue, designed for
        specific types of applications where synchronous functionality
        is more important than performance.

        """
        no_ack = self.no_ack if no_ack is None else no_ack
        message = self.channel.basic_get(queue=self.name, no_ack=no_ack)
        if message is not None:
            m2p = getattr(self.channel, 'message_to_python', None)
            if m2p:
                message = m2p(message)
            if message.errors:
                message._reraise_error()
            message.accept = prepare_accept_content(accept)
        return message

    def purge(self, nowait=False):
        """Remove all ready messages from the queue."""
        return self.channel.queue_purge(queue=self.name,
                                        nowait=nowait) or 0

    def consume(self, consumer_tag='', callback=None,
                no_ack=None, nowait=False):
        """Start a queue consumer.

        Consumers last as long as the channel they were created on, or
        until the client cancels them.

        :keyword consumer_tag: Unique identifier for the consumer. The
          consumer tag is local to a connection, so two clients
          can use the same consumer tags. If this field is empty
          the server will generate a unique tag.

        :keyword no_ack: If enabled the broker will automatically ack
            messages.

        :keyword nowait: Do not wait for a reply.

        :keyword callback: callback called for each delivered message

        """
        if no_ack is None:
            no_ack = self.no_ack
        return self.channel.basic_consume(queue=self.name,
                                          no_ack=no_ack,
                                          consumer_tag=consumer_tag or '',
                                          callback=callback,
                                          nowait=nowait)

    def cancel(self, consumer_tag):
        """Cancel a consumer by consumer tag."""
        return self.channel.basic_cancel(consumer_tag)

    def delete(self, if_unused=False, if_empty=False, nowait=False):
        """Delete the queue.

        :keyword if_unused: If set, the server will only delete the queue
            if it has no consumers. A channel error will be raised
            if the queue has consumers.

        :keyword if_empty: If set, the server will only delete the queue
            if it is empty. If it is not empty a channel error will be raised.

        :keyword nowait: Do not wait for a reply.

        """
        return self.channel.queue_delete(queue=self.name,
                                         if_unused=if_unused,
                                         if_empty=if_empty,
                                         nowait=nowait)

    def queue_unbind(self, arguments=None, nowait=False):
        return self.unbind_from(self.exchange, self.routing_key,
                                arguments, nowait)

    def unbind_from(self, exchange='', routing_key='',
                    arguments=None, nowait=False):
        """Unbind queue by deleting the binding from the server."""
        return self.channel.queue_unbind(queue=self.name,
                                         exchange=exchange.name,
                                         routing_key=routing_key,
                                         arguments=arguments,
                                         nowait=nowait)

    def __eq__(self, other):
        if isinstance(other, Queue):
            return (self.name == other.name and
                    self.exchange == other.exchange and
                    self.routing_key == other.routing_key and
                    self.queue_arguments == other.queue_arguments and
                    self.binding_arguments == other.binding_arguments and
                    self.durable == other.durable and
                    self.exclusive == other.exclusive and
                    self.auto_delete == other.auto_delete)
        return NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        s = super(Queue, self).__repr__
        if self.bindings:
            return s('Queue {0.name} -> {bindings}'.format(
                self, bindings=pretty_bindings(self.bindings),
            ))
        return s(
            'Queue {0.name} -> {0.exchange!r} -> {0.routing_key}'.format(
                self))

    @property
    def can_cache_declaration(self):
        return self.durable and not self.auto_delete

    @classmethod
    def from_dict(self, queue, **options):
        binding_key = options.get('binding_key') or options.get('routing_key')

        e_durable = options.get('exchange_durable')
        if e_durable is None:
            e_durable = options.get('durable')

        e_auto_delete = options.get('exchange_auto_delete')
        if e_auto_delete is None:
            e_auto_delete = options.get('auto_delete')

        q_durable = options.get('queue_durable')
        if q_durable is None:
            q_durable = options.get('durable')

        q_auto_delete = options.get('queue_auto_delete')
        if q_auto_delete is None:
            q_auto_delete = options.get('auto_delete')

        e_arguments = options.get('exchange_arguments')
        q_arguments = options.get('queue_arguments')
        b_arguments = options.get('binding_arguments')
        bindings = options.get('bindings')

        exchange = Exchange(options.get('exchange'),
                            type=options.get('exchange_type'),
                            delivery_mode=options.get('delivery_mode'),
                            routing_key=options.get('routing_key'),
                            durable=e_durable,
                            auto_delete=e_auto_delete,
                            arguments=e_arguments)
        return Queue(queue,
                     exchange=exchange,
                     routing_key=binding_key,
                     durable=q_durable,
                     exclusive=options.get('exclusive'),
                     auto_delete=q_auto_delete,
                     no_ack=options.get('no_ack'),
                     queue_arguments=q_arguments,
                     binding_arguments=b_arguments,
                     bindings=bindings)

########NEW FILE########
__FILENAME__ = exceptions
"""
kombu.exceptions
================

Exceptions.

"""
from __future__ import absolute_import

import socket

from amqp import ChannelError, ConnectionError, ResourceError

__all__ = ['NotBoundError', 'MessageStateError', 'TimeoutError',
           'LimitExceeded', 'ConnectionLimitExceeded',
           'ChannelLimitExceeded', 'ConnectionError', 'ChannelError',
           'VersionMismatch', 'SerializerNotInstalled', 'ResourceError',
           'SerializationError', 'EncodeError', 'DecodeError']

TimeoutError = socket.timeout


class KombuError(Exception):
    """Common subclass for all Kombu exceptions."""
    pass


class SerializationError(KombuError):
    """Failed to serialize/deserialize content."""


class EncodeError(SerializationError):
    """Cannot encode object."""
    pass


class DecodeError(SerializationError):
    """Cannot decode object."""


class NotBoundError(KombuError):
    """Trying to call channel dependent method on unbound entity."""
    pass


class MessageStateError(KombuError):
    """The message has already been acknowledged."""
    pass


class LimitExceeded(KombuError):
    """Limit exceeded."""
    pass


class ConnectionLimitExceeded(LimitExceeded):
    """Maximum number of simultaneous connections exceeded."""
    pass


class ChannelLimitExceeded(LimitExceeded):
    """Maximum number of simultaneous channels exceeded."""
    pass


class VersionMismatch(KombuError):
    pass


class SerializerNotInstalled(KombuError):
    """Support for the requested serialization type is not installed"""
    pass


class ContentDisallowed(SerializerNotInstalled):
    """Consumer does not allow this content-type."""
    pass


class InconsistencyError(ConnectionError):
    """Data or environment has been found to be inconsistent,
    depending on the cause it may be possible to retry the operation."""
    pass

########NEW FILE########
__FILENAME__ = five
# -*- coding: utf-8 -*-
"""
    kombu.five
    ~~~~~~~~~~~

    Compatibility implementations of features
    only available in newer Python versions.


"""
from __future__ import absolute_import

from amqp.five import *        # noqa
from amqp.five import __all__  # noqa

########NEW FILE########
__FILENAME__ = log
from __future__ import absolute_import

import logging
import numbers
import os
import sys

from logging.handlers import WatchedFileHandler

from .five import string_t
from .utils import cached_property
from .utils.encoding import safe_repr, safe_str
from .utils.functional import maybe_evaluate

__all__ = ['LogMixin', 'LOG_LEVELS', 'get_loglevel', 'setup_logging']

try:
    LOG_LEVELS = dict(logging._nameToLevel)
    LOG_LEVELS.update(logging._levelToName)
except AttributeError:
    LOG_LEVELS = dict(logging._levelNames)
LOG_LEVELS.setdefault('FATAL', logging.FATAL)
LOG_LEVELS.setdefault(logging.FATAL, 'FATAL')
DISABLE_TRACEBACKS = os.environ.get('DISABLE_TRACEBACKS')


class NullHandler(logging.Handler):

    def emit(self, record):
        pass


def get_logger(logger):
    if isinstance(logger, string_t):
        logger = logging.getLogger(logger)
    if not logger.handlers:
        logger.addHandler(NullHandler())
    return logger


def get_loglevel(level):
    if isinstance(level, string_t):
        return LOG_LEVELS[level]
    return level


def naive_format_parts(fmt):
    parts = fmt.split('%')
    for i, e in enumerate(parts[1:]):
        yield None if not e or not parts[i - 1] else e[0]


def safeify_format(fmt, args,
                   filters={'s': safe_str,
                            'r': safe_repr}):
    for index, type in enumerate(naive_format_parts(fmt)):
        filt = filters.get(type)
        yield filt(args[index]) if filt else args[index]


class LogMixin(object):

    def debug(self, *args, **kwargs):
        return self.log(logging.DEBUG, *args, **kwargs)

    def info(self, *args, **kwargs):
        return self.log(logging.INFO, *args, **kwargs)

    def warn(self, *args, **kwargs):
        return self.log(logging.WARN, *args, **kwargs)

    def error(self, *args, **kwargs):
        return self._error(logging.ERROR, *args, **kwargs)

    def critical(self, *args, **kwargs):
        return self._error(logging.CRITICAL, *args, **kwargs)

    def _error(self, severity, *args, **kwargs):
        kwargs.setdefault('exc_info', True)
        if DISABLE_TRACEBACKS:
            kwargs.pop('exc_info', None)
        return self.log(severity, *args, **kwargs)

    def annotate(self, text):
        return '%s - %s' % (self.logger_name, text)

    def log(self, severity, *args, **kwargs):
        if self.logger.isEnabledFor(severity):
            log = self.logger.log
            if len(args) > 1 and isinstance(args[0], string_t):
                expand = [maybe_evaluate(arg) for arg in args[1:]]
                return log(severity,
                           self.annotate(args[0].replace('%r', '%s')),
                           *list(safeify_format(args[0], expand)), **kwargs)
            else:
                return self.logger.log(
                    severity, self.annotate(' '.join(map(safe_str, args))),
                    **kwargs)

    def get_logger(self):
        return get_logger(self.logger_name)

    def is_enabled_for(self, level):
        return self.logger.isEnabledFor(self.get_loglevel(level))

    def get_loglevel(self, level):
        if not isinstance(level, numbers.Integral):
            return LOG_LEVELS[level]
        return level

    @cached_property
    def logger(self):
        return self.get_logger()

    @property
    def logger_name(self):
        return self.__class__.__name__


class Log(LogMixin):

    def __init__(self, name, logger=None):
        self._logger_name = name
        self._logger = logger

    def get_logger(self):
        if self._logger:
            return self._logger
        return LogMixin.get_logger(self)

    @property
    def logger_name(self):
        return self._logger_name


def setup_logging(loglevel=None, logfile=None):
    logger = logging.getLogger()
    loglevel = get_loglevel(loglevel or 'ERROR')
    logfile = logfile if logfile else sys.__stderr__
    if not logger.handlers:
        if hasattr(logfile, 'write'):
            handler = logging.StreamHandler(logfile)
        else:
            handler = WatchedFileHandler(logfile)
        logger.addHandler(handler)
        logger.setLevel(loglevel)
    return logger

########NEW FILE########
__FILENAME__ = message
"""
kombu.transport.message
=======================

Message class.

"""
from __future__ import absolute_import

import sys

from .compression import decompress
from .exceptions import MessageStateError
from .five import reraise, text_t
from .serialization import loads

ACK_STATES = frozenset(['ACK', 'REJECTED', 'REQUEUED'])


class Message(object):
    """Base class for received messages."""
    __slots__ = ('_state', 'channel', 'delivery_tag',
                 'content_type', 'content_encoding',
                 'delivery_info', 'headers', 'properties',
                 'body', '_decoded_cache', 'accept', '__dict__')
    MessageStateError = MessageStateError

    errors = None

    def __init__(self, channel, body=None, delivery_tag=None,
                 content_type=None, content_encoding=None, delivery_info={},
                 properties=None, headers=None, postencode=None,
                 accept=None, **kwargs):
        self.errors = [] if self.errors is None else self.errors
        self.channel = channel
        self.delivery_tag = delivery_tag
        self.content_type = content_type
        self.content_encoding = content_encoding
        self.delivery_info = delivery_info
        self.headers = headers or {}
        self.properties = properties or {}
        self._decoded_cache = None
        self._state = 'RECEIVED'
        self.accept = accept

        compression = self.headers.get('compression')
        if not self.errors and compression:
            try:
                body = decompress(body, compression)
            except Exception:
                self.errors.append(sys.exc_info())

        if not self.errors and postencode and isinstance(body, text_t):
            try:
                body = body.encode(postencode)
            except Exception:
                self.errors.append(sys.exc_info())
        self.body = body

    def _reraise_error(self, callback=None):
        try:
            reraise(*self.errors[0])
        except Exception as exc:
            if not callback:
                raise
            callback(self, exc)

    def ack(self):
        """Acknowledge this message as being processed.,
        This will remove the message from the queue.

        :raises MessageStateError: If the message has already been
            acknowledged/requeued/rejected.

        """
        if self.channel.no_ack_consumers is not None:
            try:
                consumer_tag = self.delivery_info['consumer_tag']
            except KeyError:
                pass
            else:
                if consumer_tag in self.channel.no_ack_consumers:
                    return
        if self.acknowledged:
            raise self.MessageStateError(
                'Message already acknowledged with state: {0._state}'.format(
                    self))
        self.channel.basic_ack(self.delivery_tag)
        self._state = 'ACK'

    def ack_log_error(self, logger, errors):
        try:
            self.ack()
        except errors as exc:
            logger.critical("Couldn't ack %r, reason:%r",
                            self.delivery_tag, exc, exc_info=True)

    def reject_log_error(self, logger, errors, requeue=False):
        try:
            self.reject(requeue=requeue)
        except errors as exc:
            logger.critical("Couldn't reject %r, reason: %r",
                            self.delivery_tag, exc, exc_info=True)

    def reject(self, requeue=False):
        """Reject this message.

        The message will be discarded by the server.

        :raises MessageStateError: If the message has already been
            acknowledged/requeued/rejected.

        """
        if self.acknowledged:
            raise self.MessageStateError(
                'Message already acknowledged with state: {0._state}'.format(
                    self))
        self.channel.basic_reject(self.delivery_tag, requeue=requeue)
        self._state = 'REJECTED'

    def requeue(self):
        """Reject this message and put it back on the queue.

        You must not use this method as a means of selecting messages
        to process.

        :raises MessageStateError: If the message has already been
            acknowledged/requeued/rejected.

        """
        if self.acknowledged:
            raise self.MessageStateError(
                'Message already acknowledged with state: {0._state}'.format(
                    self))
        self.channel.basic_reject(self.delivery_tag, requeue=True)
        self._state = 'REQUEUED'

    def decode(self):
        """Deserialize the message body, returning the original
        python structure sent by the publisher."""
        return loads(self.body, self.content_type,
                     self.content_encoding, accept=self.accept)

    @property
    def acknowledged(self):
        """Set to true if the message has been acknowledged."""
        return self._state in ACK_STATES

    @property
    def payload(self):
        """The decoded message body."""
        if not self._decoded_cache:
            self._decoded_cache = self.decode()
        return self._decoded_cache

########NEW FILE########
__FILENAME__ = messaging
"""
kombu.messaging
===============

Sending and receiving messages.

"""
from __future__ import absolute_import

import numbers

from itertools import count

from .compression import compress
from .connection import maybe_channel, is_connection
from .entity import Exchange, Queue, DELIVERY_MODES
from .exceptions import ContentDisallowed
from .five import text_t, values
from .serialization import dumps, prepare_accept_content
from .utils import ChannelPromise, maybe_list

__all__ = ['Exchange', 'Queue', 'Producer', 'Consumer']


class Producer(object):
    """Message Producer.

    :param channel: Connection or channel.
    :keyword exchange: Optional default exchange.
    :keyword routing_key: Optional default routing key.
    :keyword serializer: Default serializer. Default is `"json"`.
    :keyword compression: Default compression method. Default is no
        compression.
    :keyword auto_declare: Automatically declare the default exchange
      at instantiation. Default is :const:`True`.
    :keyword on_return: Callback to call for undeliverable messages,
        when the `mandatory` or `immediate` arguments to
        :meth:`publish` is used. This callback needs the following
        signature: `(exception, exchange, routing_key, message)`.
        Note that the producer needs to drain events to use this feature.

    """

    #: Default exchange
    exchange = None

    #: Default routing key.
    routing_key = ''

    #: Default serializer to use. Default is JSON.
    serializer = None

    #: Default compression method.  Disabled by default.
    compression = None

    #: By default the exchange is declared at instantiation.
    #: If you want to declare manually then you can set this
    #: to :const:`False`.
    auto_declare = True

    #: Basic return callback.
    on_return = None

    #: Set if channel argument was a Connection instance (using
    #: default_channel).
    __connection__ = None

    def __init__(self, channel, exchange=None, routing_key=None,
                 serializer=None, auto_declare=None, compression=None,
                 on_return=None):
        self._channel = channel
        self.exchange = exchange
        self.routing_key = routing_key or self.routing_key
        self.serializer = serializer or self.serializer
        self.compression = compression or self.compression
        self.on_return = on_return or self.on_return
        self._channel_promise = None
        if self.exchange is None:
            self.exchange = Exchange('')
        if auto_declare is not None:
            self.auto_declare = auto_declare

        if self._channel:
            self.revive(self._channel)

    def __repr__(self):
        return '<Producer: {0._channel}>'.format(self)

    def __reduce__(self):
        return self.__class__, self.__reduce_args__()

    def __reduce_args__(self):
        return (None, self.exchange, self.routing_key, self.serializer,
                self.auto_declare, self.compression)

    def declare(self):
        """Declare the exchange.

        This happens automatically at instantiation if
        :attr:`auto_declare` is enabled.

        """
        if self.exchange.name:
            self.exchange.declare()

    def maybe_declare(self, entity, retry=False, **retry_policy):
        """Declare the exchange if it hasn't already been declared
        during this session."""
        if entity:
            from .common import maybe_declare
            return maybe_declare(entity, self.channel, retry, **retry_policy)

    def publish(self, body, routing_key=None, delivery_mode=None,
                mandatory=False, immediate=False, priority=0,
                content_type=None, content_encoding=None, serializer=None,
                headers=None, compression=None, exchange=None, retry=False,
                retry_policy=None, declare=[], **properties):
        """Publish message to the specified exchange.

        :param body: Message body.
        :keyword routing_key: Message routing key.
        :keyword delivery_mode: See :attr:`delivery_mode`.
        :keyword mandatory: Currently not supported.
        :keyword immediate: Currently not supported.
        :keyword priority: Message priority. A number between 0 and 9.
        :keyword content_type: Content type. Default is auto-detect.
        :keyword content_encoding: Content encoding. Default is auto-detect.
        :keyword serializer: Serializer to use. Default is auto-detect.
        :keyword compression: Compression method to use.  Default is none.
        :keyword headers: Mapping of arbitrary headers to pass along
          with the message body.
        :keyword exchange: Override the exchange.  Note that this exchange
          must have been declared.
        :keyword declare: Optional list of required entities that must
            have been declared before publishing the message.  The entities
            will be declared using :func:`~kombu.common.maybe_declare`.
        :keyword retry: Retry publishing, or declaring entities if the
            connection is lost.
        :keyword retry_policy: Retry configuration, this is the keywords
            supported by :meth:`~kombu.Connection.ensure`.
        :keyword \*\*properties: Additional message properties, see AMQP spec.

        """
        headers = {} if headers is None else headers
        retry_policy = {} if retry_policy is None else retry_policy
        routing_key = self.routing_key if routing_key is None else routing_key
        compression = self.compression if compression is None else compression
        exchange = exchange or self.exchange

        if isinstance(exchange, Exchange):
            delivery_mode = delivery_mode or exchange.delivery_mode
            exchange = exchange.name
        else:
            delivery_mode = delivery_mode or self.exchange.delivery_mode
        if not isinstance(delivery_mode, numbers.Integral):
            delivery_mode = DELIVERY_MODES[delivery_mode]
        properties['delivery_mode'] = delivery_mode

        body, content_type, content_encoding = self._prepare(
            body, serializer, content_type, content_encoding,
            compression, headers)

        publish = self._publish
        if retry:
            publish = self.connection.ensure(self, publish, **retry_policy)
        return publish(body, priority, content_type,
                       content_encoding, headers, properties,
                       routing_key, mandatory, immediate, exchange, declare)

    def _publish(self, body, priority, content_type, content_encoding,
                 headers, properties, routing_key, mandatory,
                 immediate, exchange, declare):
        channel = self.channel
        message = channel.prepare_message(
            body, priority, content_type,
            content_encoding, headers, properties,
        )
        if declare:
            maybe_declare = self.maybe_declare
            [maybe_declare(entity) for entity in declare]
        return channel.basic_publish(
            message,
            exchange=exchange, routing_key=routing_key,
            mandatory=mandatory, immediate=immediate,
        )

    def _get_channel(self):
        channel = self._channel
        if isinstance(channel, ChannelPromise):
            channel = self._channel = channel()
            self.exchange.revive(channel)
            if self.on_return:
                channel.events['basic_return'].add(self.on_return)
        return channel

    def _set_channel(self, channel):
        self._channel = channel
    channel = property(_get_channel, _set_channel)

    def revive(self, channel):
        """Revive the producer after connection loss."""
        if is_connection(channel):
            connection = channel
            self.__connection__ = connection
            channel = ChannelPromise(lambda: connection.default_channel)
        if isinstance(channel, ChannelPromise):
            self._channel = channel
            self.exchange = self.exchange(channel)
        else:
            # Channel already concrete
            self._channel = channel
            if self.on_return:
                self._channel.events['basic_return'].add(self.on_return)
            self.exchange = self.exchange(channel)
        if self.auto_declare:
            # auto_decare is not recommended as this will force
            # evaluation of the channel.
            self.declare()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.release()

    def release(self):
        pass
    close = release

    def _prepare(self, body, serializer=None, content_type=None,
                 content_encoding=None, compression=None, headers=None):

        # No content_type? Then we're serializing the data internally.
        if not content_type:
            serializer = serializer or self.serializer
            (content_type, content_encoding,
             body) = dumps(body, serializer=serializer)
        else:
            # If the programmer doesn't want us to serialize,
            # make sure content_encoding is set.
            if isinstance(body, text_t):
                if not content_encoding:
                    content_encoding = 'utf-8'
                body = body.encode(content_encoding)

            # If they passed in a string, we can't know anything
            # about it. So assume it's binary data.
            elif not content_encoding:
                content_encoding = 'binary'

        if compression:
            body, headers['compression'] = compress(body, compression)

        return body, content_type, content_encoding

    @property
    def connection(self):
        try:
            return self.__connection__ or self.channel.connection.client
        except AttributeError:
            pass


class Consumer(object):
    """Message consumer.

    :param channel: see :attr:`channel`.
    :param queues: see :attr:`queues`.
    :keyword no_ack: see :attr:`no_ack`.
    :keyword auto_declare: see :attr:`auto_declare`
    :keyword callbacks: see :attr:`callbacks`.
    :keyword on_message: See :attr:`on_message`
    :keyword on_decode_error: see :attr:`on_decode_error`.

    """
    ContentDisallowed = ContentDisallowed

    #: The connection/channel to use for this consumer.
    channel = None

    #: A single :class:`~kombu.Queue`, or a list of queues to
    #: consume from.
    queues = None

    #: Flag for automatic message acknowledgment.
    #: If enabled the messages are automatically acknowledged by the
    #: broker.  This can increase performance but means that you
    #: have no control of when the message is removed.
    #:
    #: Disabled by default.
    no_ack = None

    #: By default all entities will be declared at instantiation, if you
    #: want to handle this manually you can set this to :const:`False`.
    auto_declare = True

    #: List of callbacks called in order when a message is received.
    #:
    #: The signature of the callbacks must take two arguments:
    #: `(body, message)`, which is the decoded message body and
    #: the `Message` instance (a subclass of
    #: :class:`~kombu.transport.base.Message`).
    callbacks = None

    #: Optional function called whenever a message is received.
    #:
    #: When defined this function will be called instead of the
    #: :meth:`receive` method, and :attr:`callbacks` will be disabled.
    #:
    #: So this can be used as an alternative to :attr:`callbacks` when
    #: you don't want the body to be automatically decoded.
    #: Note that the message will still be decompressed if the message
    #: has the ``compression`` header set.
    #:
    #: The signature of the callback must take a single argument,
    #: which is the raw message object (a subclass of
    #: :class:`~kombu.transport.base.Message`).
    #:
    #: Also note that the ``message.body`` attribute, which is the raw
    #: contents of the message body, may in some cases be a read-only
    #: :class:`buffer` object.
    on_message = None

    #: Callback called when a message can't be decoded.
    #:
    #: The signature of the callback must take two arguments: `(message,
    #: exc)`, which is the message that can't be decoded and the exception
    #: that occurred while trying to decode it.
    on_decode_error = None

    #: List of accepted content-types.
    #:
    #: An exception will be raised if the consumer receives
    #: a message with an untrusted content type.
    #: By default all content-types are accepted, but not if
    #: :func:`kombu.disable_untrusted_serializers` was called,
    #: in which case only json is allowed.
    accept = None

    _tags = count(1)   # global

    def __init__(self, channel, queues=None, no_ack=None, auto_declare=None,
                 callbacks=None, on_decode_error=None, on_message=None,
                 accept=None):
        self.channel = channel
        self.queues = self.queues or [] if queues is None else queues
        self.no_ack = self.no_ack if no_ack is None else no_ack
        self.callbacks = (self.callbacks or [] if callbacks is None
                          else callbacks)
        self.on_message = on_message
        self._active_tags = {}
        if auto_declare is not None:
            self.auto_declare = auto_declare
        if on_decode_error is not None:
            self.on_decode_error = on_decode_error
        self.accept = prepare_accept_content(accept)

        if self.channel:
            self.revive(self.channel)

    def revive(self, channel):
        """Revive consumer after connection loss."""
        self._active_tags.clear()
        channel = self.channel = maybe_channel(channel)
        self.queues = [queue(self.channel)
                       for queue in maybe_list(self.queues)]
        for queue in self.queues:
            queue.revive(channel)

        if self.auto_declare:
            self.declare()

    def declare(self):
        """Declare queues, exchanges and bindings.

        This is done automatically at instantiation if :attr:`auto_declare`
        is set.

        """
        for queue in self.queues:
            queue.declare()

    def register_callback(self, callback):
        """Register a new callback to be called when a message
        is received.

        The signature of the callback needs to accept two arguments:
        `(body, message)`, which is the decoded message body
        and the `Message` instance (a subclass of
        :class:`~kombu.transport.base.Message`.

        """
        self.callbacks.append(callback)

    def __enter__(self):
        self.consume()
        return self

    def __exit__(self, *exc_info):
        try:
            self.cancel()
        except Exception:
            pass

    def add_queue(self, queue):
        """Add a queue to the list of queues to consume from.

        This will not start consuming from the queue,
        for that you will have to call :meth:`consume` after.

        """
        queue = queue(self.channel)
        if self.auto_declare:
            queue.declare()
        self.queues.append(queue)
        return queue

    def add_queue_from_dict(self, queue, **options):
        """This method is deprecated.

        Instead please use::

            consumer.add_queue(Queue.from_dict(d))

        """
        return self.add_queue(Queue.from_dict(queue, **options))

    def consume(self, no_ack=None):
        """Start consuming messages.

        Can be called multiple times, but note that while it
        will consume from new queues added since the last call,
        it will not cancel consuming from removed queues (
        use :meth:`cancel_by_queue`).

        :param no_ack: See :attr:`no_ack`.

        """
        if self.queues:
            no_ack = self.no_ack if no_ack is None else no_ack

            H, T = self.queues[:-1], self.queues[-1]
            for queue in H:
                self._basic_consume(queue, no_ack=no_ack, nowait=True)
            self._basic_consume(T, no_ack=no_ack, nowait=False)

    def cancel(self):
        """End all active queue consumers.

        This does not affect already delivered messages, but it does
        mean the server will not send any more messages for this consumer.

        """
        cancel = self.channel.basic_cancel
        for tag in values(self._active_tags):
            cancel(tag)
        self._active_tags.clear()
    close = cancel

    def cancel_by_queue(self, queue):
        """Cancel consumer by queue name."""
        try:
            tag = self._active_tags.pop(queue)
        except KeyError:
            pass
        else:
            self.queues[:] = [q for q in self.queues if q.name != queue]
            self.channel.basic_cancel(tag)

    def consuming_from(self, queue):
        """Return :const:`True` if the consumer is currently
        consuming from queue'."""
        name = queue
        if isinstance(queue, Queue):
            name = queue.name
        return name in self._active_tags

    def purge(self):
        """Purge messages from all queues.

        .. warning::
            This will *delete all ready messages*, there is no
            undo operation.

        """
        return sum(queue.purge() for queue in self.queues)

    def flow(self, active):
        """Enable/disable flow from peer.

        This is a simple flow-control mechanism that a peer can use
        to avoid overflowing its queues or otherwise finding itself
        receiving more messages than it can process.

        The peer that receives a request to stop sending content
        will finish sending the current content (if any), and then wait
        until flow is reactivated.

        """
        self.channel.flow(active)

    def qos(self, prefetch_size=0, prefetch_count=0, apply_global=False):
        """Specify quality of service.

        The client can request that messages should be sent in
        advance so that when the client finishes processing a message,
        the following message is already held locally, rather than needing
        to be sent down the channel. Prefetching gives a performance
        improvement.

        The prefetch window is Ignored if the :attr:`no_ack` option is set.

        :param prefetch_size: Specify the prefetch window in octets.
          The server will send a message in advance if it is equal to
          or smaller in size than the available prefetch size (and
          also falls within other prefetch limits). May be set to zero,
          meaning "no specific limit", although other prefetch limits
          may still apply.

        :param prefetch_count: Specify the prefetch window in terms of
          whole messages.

        :param apply_global: Apply new settings globally on all channels.

        """
        return self.channel.basic_qos(prefetch_size,
                                      prefetch_count,
                                      apply_global)

    def recover(self, requeue=False):
        """Redeliver unacknowledged messages.

        Asks the broker to redeliver all unacknowledged messages
        on the specified channel.

        :keyword requeue: By default the messages will be redelivered
          to the original recipient. With `requeue` set to true, the
          server will attempt to requeue the message, potentially then
          delivering it to an alternative subscriber.

        """
        return self.channel.basic_recover(requeue=requeue)

    def receive(self, body, message):
        """Method called when a message is received.

        This dispatches to the registered :attr:`callbacks`.

        :param body: The decoded message body.
        :param message: The `Message` instance.

        :raises NotImplementedError: If no consumer callbacks have been
          registered.

        """
        callbacks = self.callbacks
        if not callbacks:
            raise NotImplementedError('Consumer does not have any callbacks')
        [callback(body, message) for callback in callbacks]

    def _basic_consume(self, queue, consumer_tag=None,
                       no_ack=no_ack, nowait=True):
        tag = self._active_tags.get(queue.name)
        if tag is None:
            tag = self._add_tag(queue, consumer_tag)
            queue.consume(tag, self._receive_callback,
                          no_ack=no_ack, nowait=nowait)
        return tag

    def _add_tag(self, queue, consumer_tag=None):
        tag = consumer_tag or str(next(self._tags))
        self._active_tags[queue.name] = tag
        return tag

    def _receive_callback(self, message):
        accept = self.accept
        on_m, channel, decoded = self.on_message, self.channel, None
        try:
            m2p = getattr(channel, 'message_to_python', None)
            if m2p:
                message = m2p(message)
            if accept is not None:
                message.accept = accept
            if message.errors:
                return message._reraise_error(self.on_decode_error)
            decoded = None if on_m else message.decode()
        except Exception as exc:
            if not self.on_decode_error:
                raise
            self.on_decode_error(message, exc)
        else:
            return on_m(message) if on_m else self.receive(decoded, message)

    def __repr__(self):
        return '<Consumer: {0.queues}>'.format(self)

    @property
    def connection(self):
        try:
            return self.channel.connection.client
        except AttributeError:
            pass

########NEW FILE########
__FILENAME__ = mixins
# -*- coding: utf-8 -*-
"""
kombu.mixins
============

Useful mixin classes.

"""
from __future__ import absolute_import

import socket

from contextlib import contextmanager
from functools import partial
from itertools import count
from time import sleep

from .common import ignore_errors
from .five import range
from .messaging import Consumer
from .log import get_logger
from .utils import cached_property, nested
from .utils.encoding import safe_repr
from .utils.limits import TokenBucket

__all__ = ['ConsumerMixin']

logger = get_logger(__name__)
debug, info, warn, error = logger.debug, logger.info, logger.warn, logger.error


class ConsumerMixin(object):
    """Convenience mixin for implementing consumer programs.

    It can be used outside of threads, with threads, or greenthreads
    (eventlet/gevent) too.

    The basic class would need a :attr:`connection` attribute
    which must be a :class:`~kombu.Connection` instance,
    and define a :meth:`get_consumers` method that returns a list
    of :class:`kombu.Consumer` instances to use.
    Supporting multiple consumers is important so that multiple
    channels can be used for different QoS requirements.

    **Example**:

    .. code-block:: python


        class Worker(ConsumerMixin):
            task_queue = Queue('tasks', Exchange('tasks'), 'tasks'))

            def __init__(self, connection):
                self.connection = None

            def get_consumers(self, Consumer, channel):
                return [Consumer(queues=[self.task_queue],
                                 callback=[self.on_task])]

            def on_task(self, body, message):
                print('Got task: {0!r}'.format(body))
                message.ack()

    **Additional handler methods**:

        * :meth:`extra_context`

            Optional extra context manager that will be entered
            after the connection and consumers have been set up.

            Takes arguments ``(connection, channel)``.

        * :meth:`on_connection_error`

            Handler called if the connection is lost/ or
            is unavailable.

            Takes arguments ``(exc, interval)``, where interval
            is the time in seconds when the connection will be retried.

            The default handler will log the exception.

        * :meth:`on_connection_revived`

            Handler called as soon as the connection is re-established
            after connection failure.

            Takes no arguments.

        * :meth:`on_consume_ready`

            Handler called when the consumer is ready to accept
            messages.

            Takes arguments ``(connection, channel, consumers)``.
            Also keyword arguments to ``consume`` are forwarded
            to this handler.

        * :meth:`on_consume_end`

            Handler called after the consumers are cancelled.
            Takes arguments ``(connection, channel)``.

        * :meth:`on_iteration`

            Handler called for every iteration while draining
            events.

            Takes no arguments.

        * :meth:`on_decode_error`

            Handler called if a consumer was unable to decode
            the body of a message.

            Takes arguments ``(message, exc)`` where message is the
            original message object.

            The default handler will log the error and
            acknowledge the message, so if you override make
            sure to call super, or perform these steps yourself.

    """

    #: maximum number of retries trying to re-establish the connection,
    #: if the connection is lost/unavailable.
    connect_max_retries = None

    #: When this is set to true the consumer should stop consuming
    #: and return, so that it can be joined if it is the implementation
    #: of a thread.
    should_stop = False

    def get_consumers(self, Consumer, channel):
        raise NotImplementedError('Subclass responsibility')

    def on_connection_revived(self):
        pass

    def on_consume_ready(self, connection, channel, consumers, **kwargs):
        pass

    def on_consume_end(self, connection, channel):
        pass

    def on_iteration(self):
        pass

    def on_decode_error(self, message, exc):
        error("Can't decode message body: %r (type:%r encoding:%r raw:%r')",
              exc, message.content_type, message.content_encoding,
              safe_repr(message.body))
        message.ack()

    def on_connection_error(self, exc, interval):
        warn('Broker connection error: %r. '
             'Trying again in %s seconds.', exc, interval)

    @contextmanager
    def extra_context(self, connection, channel):
        yield

    def run(self, _tokens=1):
        restart_limit = self.restart_limit
        errors = (self.connection.connection_errors +
                  self.connection.channel_errors)
        while not self.should_stop:
            try:
                if restart_limit.can_consume(_tokens):
                    for _ in self.consume(limit=None):  # pragma: no cover
                        pass
                else:
                    sleep(restart_limit.expected_time(_tokens))
            except errors:
                warn('Connection to broker lost. '
                     'Trying to re-establish the connection...')

    @contextmanager
    def consumer_context(self, **kwargs):
        with self.Consumer() as (connection, channel, consumers):
            with self.extra_context(connection, channel):
                self.on_consume_ready(connection, channel, consumers, **kwargs)
                yield connection, channel, consumers

    def consume(self, limit=None, timeout=None, safety_interval=1, **kwargs):
        elapsed = 0
        with self.consumer_context(**kwargs) as (conn, channel, consumers):
            for i in limit and range(limit) or count():
                if self.should_stop:
                    break
                self.on_iteration()
                try:
                    conn.drain_events(timeout=safety_interval)
                except socket.timeout:
                    conn.heartbeat_check()
                    elapsed += safety_interval
                    if timeout and elapsed >= timeout:
                        raise
                except socket.error:
                    if not self.should_stop:
                        raise
                else:
                    yield
                    elapsed = 0
        debug('consume exiting')

    def maybe_conn_error(self, fun):
        """Use :func:`kombu.common.ignore_errors` instead."""
        return ignore_errors(self, fun)

    def create_connection(self):
        return self.connection.clone()

    @contextmanager
    def establish_connection(self):
        with self.create_connection() as conn:
            conn.ensure_connection(self.on_connection_error,
                                   self.connect_max_retries)
            yield conn

    @contextmanager
    def Consumer(self):
        with self.establish_connection() as conn:
            self.on_connection_revived()
            info('Connected to %s', conn.as_uri())
            channel = conn.default_channel
            cls = partial(Consumer, channel,
                          on_decode_error=self.on_decode_error)
            with self._consume_from(*self.get_consumers(cls, channel)) as c:
                yield conn, channel, c
            debug('Consumers cancelled')
            self.on_consume_end(conn, channel)
        debug('Connection closed')

    def _consume_from(self, *consumers):
        return nested(*consumers)

    @cached_property
    def restart_limit(self):
        # the AttributeError that can be catched from amqplib
        # poses problems for the too often restarts protection
        # in Connection.ensure_connection
        return TokenBucket(1)

    @cached_property
    def connection_errors(self):
        return self.connection.connection_errors

    @cached_property
    def channel_errors(self):
        return self.connection.channel_errors

########NEW FILE########
__FILENAME__ = pidbox
"""
kombu.pidbox
===============

Generic process mailbox.

"""
from __future__ import absolute_import

import socket
import warnings

from collections import defaultdict, deque
from copy import copy
from itertools import count
from threading import local
from time import time

from . import Exchange, Queue, Consumer, Producer
from .clocks import LamportClock
from .common import maybe_declare, oid_from
from .exceptions import InconsistencyError
from .five import range
from .log import get_logger
from .utils import cached_property, uuid, reprcall

REPLY_QUEUE_EXPIRES = 10

W_PIDBOX_IN_USE = """\
A node named {node.hostname} is already using this process mailbox!

Maybe you forgot to shutdown the other node or did not do so properly?
Or if you meant to start multiple nodes on the same host please make sure
you give each node a unique node name!
"""

__all__ = ['Node', 'Mailbox']
logger = get_logger(__name__)
debug, error = logger.debug, logger.error


class Node(object):

    #: hostname of the node.
    hostname = None

    #: the :class:`Mailbox` this is a node for.
    mailbox = None

    #: map of method name/handlers.
    handlers = None

    #: current context (passed on to handlers)
    state = None

    #: current channel.
    channel = None

    def __init__(self, hostname, state=None, channel=None,
                 handlers=None, mailbox=None):
        self.channel = channel
        self.mailbox = mailbox
        self.hostname = hostname
        self.state = state
        self.adjust_clock = self.mailbox.clock.adjust
        if handlers is None:
            handlers = {}
        self.handlers = handlers

    def Consumer(self, channel=None, no_ack=True, accept=None, **options):
        queue = self.mailbox.get_queue(self.hostname)

        def verify_exclusive(name, messages, consumers):
            if consumers:
                warnings.warn(W_PIDBOX_IN_USE.format(node=self))
        queue.on_declared = verify_exclusive

        return Consumer(
            channel or self.channel, [queue], no_ack=no_ack,
            accept=self.mailbox.accept if accept is None else accept,
            **options
        )

    def handler(self, fun):
        self.handlers[fun.__name__] = fun
        return fun

    def on_decode_error(self, message, exc):
        error('Cannot decode message: %r', exc, exc_info=1)

    def listen(self, channel=None, callback=None):
        consumer = self.Consumer(channel=channel,
                                 callbacks=[callback or self.handle_message],
                                 on_decode_error=self.on_decode_error)
        consumer.consume()
        return consumer

    def dispatch(self, method, arguments=None,
                 reply_to=None, ticket=None, **kwargs):
        arguments = arguments or {}
        debug('pidbox received method %s [reply_to:%s ticket:%s]',
              reprcall(method, (), kwargs=arguments), reply_to, ticket)
        handle = reply_to and self.handle_call or self.handle_cast
        try:
            reply = handle(method, arguments)
        except SystemExit:
            raise
        except Exception as exc:
            error('pidbox command error: %r', exc, exc_info=1)
            reply = {'error': repr(exc)}

        if reply_to:
            self.reply({self.hostname: reply},
                       exchange=reply_to['exchange'],
                       routing_key=reply_to['routing_key'],
                       ticket=ticket)
        return reply

    def handle(self, method, arguments={}):
        return self.handlers[method](self.state, **arguments)

    def handle_call(self, method, arguments):
        return self.handle(method, arguments)

    def handle_cast(self, method, arguments):
        return self.handle(method, arguments)

    def handle_message(self, body, message=None):
        destination = body.get('destination')
        if message:
            self.adjust_clock(message.headers.get('clock') or 0)
        if not destination or self.hostname in destination:
            return self.dispatch(**body)
    dispatch_from_message = handle_message

    def reply(self, data, exchange, routing_key, ticket, **kwargs):
        self.mailbox._publish_reply(data, exchange, routing_key, ticket,
                                    channel=self.channel,
                                    serializer=self.mailbox.serializer)


class Mailbox(object):
    node_cls = Node
    exchange_fmt = '%s.pidbox'
    reply_exchange_fmt = 'reply.%s.pidbox'

    #: Name of application.
    namespace = None

    #: Connection (if bound).
    connection = None

    #: Exchange type (usually direct, or fanout for broadcast).
    type = 'direct'

    #: mailbox exchange (init by constructor).
    exchange = None

    #: exchange to send replies to.
    reply_exchange = None

    #: Only accepts json messages by default.
    accept = ['json']

    #: Message serializer
    serializer = None

    def __init__(self, namespace,
                 type='direct', connection=None, clock=None,
                 accept=None, serializer=None):
        self.namespace = namespace
        self.connection = connection
        self.type = type
        self.clock = LamportClock() if clock is None else clock
        self.exchange = self._get_exchange(self.namespace, self.type)
        self.reply_exchange = self._get_reply_exchange(self.namespace)
        self._tls = local()
        self.unclaimed = defaultdict(deque)
        self.accept = self.accept if accept is None else accept
        self.serializer = self.serializer if serializer is None else serializer

    def __call__(self, connection):
        bound = copy(self)
        bound.connection = connection
        return bound

    def Node(self, hostname=None, state=None, channel=None, handlers=None):
        hostname = hostname or socket.gethostname()
        return self.node_cls(hostname, state, channel, handlers, mailbox=self)

    def call(self, destination, command, kwargs={},
             timeout=None, callback=None, channel=None):
        return self._broadcast(command, kwargs, destination,
                               reply=True, timeout=timeout,
                               callback=callback,
                               channel=channel)

    def cast(self, destination, command, kwargs={}):
        return self._broadcast(command, kwargs, destination, reply=False)

    def abcast(self, command, kwargs={}):
        return self._broadcast(command, kwargs, reply=False)

    def multi_call(self, command, kwargs={}, timeout=1,
                   limit=None, callback=None, channel=None):
        return self._broadcast(command, kwargs, reply=True,
                               timeout=timeout, limit=limit,
                               callback=callback,
                               channel=channel)

    def get_reply_queue(self):
        oid = self.oid
        return Queue(
            '%s.%s' % (oid, self.reply_exchange.name),
            exchange=self.reply_exchange,
            routing_key=oid,
            durable=False,
            auto_delete=True,
            queue_arguments={
                'x-expires': int(REPLY_QUEUE_EXPIRES * 1000),
            },
        )

    @cached_property
    def reply_queue(self):
        return self.get_reply_queue()

    def get_queue(self, hostname):
        return Queue('%s.%s.pidbox' % (hostname, self.namespace),
                     exchange=self.exchange,
                     durable=False,
                     auto_delete=True)

    def _publish_reply(self, reply, exchange, routing_key, ticket,
                       channel=None, **opts):
        chan = channel or self.connection.default_channel
        exchange = Exchange(exchange, exchange_type='direct',
                            delivery_mode='transient',
                            durable=False)
        producer = Producer(chan, auto_declare=False)
        try:
            producer.publish(
                reply, exchange=exchange, routing_key=routing_key,
                declare=[exchange], headers={
                    'ticket': ticket, 'clock': self.clock.forward(),
                },
                **opts
            )
        except InconsistencyError:
            pass   # queue probably deleted and no one is expecting a reply.

    def _publish(self, type, arguments, destination=None,
                 reply_ticket=None, channel=None, timeout=None,
                 serializer=None):
        message = {'method': type,
                   'arguments': arguments,
                   'destination': destination}
        chan = channel or self.connection.default_channel
        exchange = self.exchange
        if reply_ticket:
            maybe_declare(self.reply_queue(channel))
            message.update(ticket=reply_ticket,
                           reply_to={'exchange': self.reply_exchange.name,
                                     'routing_key': self.oid})
        serializer = serializer or self.serializer
        producer = Producer(chan, auto_declare=False)
        producer.publish(
            message, exchange=exchange.name, declare=[exchange],
            headers={'clock': self.clock.forward(),
                     'expires': time() + timeout if timeout else 0},
            serializer=serializer,
        )

    def _broadcast(self, command, arguments=None, destination=None,
                   reply=False, timeout=1, limit=None,
                   callback=None, channel=None, serializer=None):
        if destination is not None and \
                not isinstance(destination, (list, tuple)):
            raise ValueError(
                'destination must be a list/tuple not {0}'.format(
                    type(destination)))

        arguments = arguments or {}
        reply_ticket = reply and uuid() or None
        chan = channel or self.connection.default_channel

        # Set reply limit to number of destinations (if specified)
        if limit is None and destination:
            limit = destination and len(destination) or None

        serializer = serializer or self.serializer
        self._publish(command, arguments, destination=destination,
                      reply_ticket=reply_ticket,
                      channel=chan,
                      timeout=timeout,
                      serializer=serializer)

        if reply_ticket:
            return self._collect(reply_ticket, limit=limit,
                                 timeout=timeout,
                                 callback=callback,
                                 channel=chan)

    def _collect(self, ticket,
                 limit=None, timeout=1, callback=None,
                 channel=None, accept=None):
        if accept is None:
            accept = self.accept
        chan = channel or self.connection.default_channel
        queue = self.reply_queue
        consumer = Consumer(channel, [queue], accept=accept, no_ack=True)
        responses = []
        unclaimed = self.unclaimed
        adjust_clock = self.clock.adjust

        try:
            return unclaimed.pop(ticket)
        except KeyError:
            pass

        def on_message(body, message):
            # ticket header added in kombu 2.5
            header = message.headers.get
            adjust_clock(header('clock') or 0)
            expires = header('expires')
            if expires and time() > expires:
                return
            this_id = header('ticket', ticket)
            if this_id == ticket:
                if callback:
                    callback(body)
                responses.append(body)
            else:
                unclaimed[this_id].append(body)

        consumer.register_callback(on_message)
        try:
            with consumer:
                for i in limit and range(limit) or count():
                    try:
                        self.connection.drain_events(timeout=timeout)
                    except socket.timeout:
                        break
                return responses
        finally:
            chan.after_reply_message_received(queue.name)

    def _get_exchange(self, namespace, type):
        return Exchange(self.exchange_fmt % namespace,
                        type=type,
                        durable=False,
                        delivery_mode='transient')

    def _get_reply_exchange(self, namespace):
        return Exchange(self.reply_exchange_fmt % namespace,
                        type='direct',
                        durable=False,
                        delivery_mode='transient')

    @cached_property
    def oid(self):
        try:
            return self._tls.OID
        except AttributeError:
            oid = self._tls.OID = oid_from(self)
            return oid

########NEW FILE########
__FILENAME__ = pools
"""
kombu.pools
===========

Public resource pools.

"""
from __future__ import absolute_import

import os

from itertools import chain

from .connection import Resource
from .five import range, values
from .messaging import Producer
from .utils import EqualityDict
from .utils.functional import lazy

__all__ = ['ProducerPool', 'PoolGroup', 'register_group',
           'connections', 'producers', 'get_limit', 'set_limit', 'reset']
_limit = [200]
_used = [False]
_groups = []
use_global_limit = object()
disable_limit_protection = os.environ.get('KOMBU_DISABLE_LIMIT_PROTECTION')


class ProducerPool(Resource):
    Producer = Producer

    def __init__(self, connections, *args, **kwargs):
        self.connections = connections
        self.Producer = kwargs.pop('Producer', None) or self.Producer
        super(ProducerPool, self).__init__(*args, **kwargs)

    def _acquire_connection(self):
        return self.connections.acquire(block=True)

    def create_producer(self):
        conn = self._acquire_connection()
        try:
            return self.Producer(conn)
        except BaseException:
            conn.release()
            raise

    def new(self):
        return lazy(self.create_producer)

    def setup(self):
        if self.limit:
            for _ in range(self.limit):
                self._resource.put_nowait(self.new())

    def close_resource(self, resource):
        pass

    def prepare(self, p):
        if callable(p):
            p = p()
        if p._channel is None:
            conn = self._acquire_connection()
            try:
                p.revive(conn)
            except BaseException:
                conn.release()
                raise
        return p

    def release(self, resource):
        if resource.__connection__:
            resource.__connection__.release()
        resource.channel = None
        super(ProducerPool, self).release(resource)


class PoolGroup(EqualityDict):

    def __init__(self, limit=None):
        self.limit = limit

    def create(self, resource, limit):
        raise NotImplementedError('PoolGroups must define ``create``')

    def __missing__(self, resource):
        limit = self.limit
        if limit is use_global_limit:
            limit = get_limit()
        if not _used[0]:
            _used[0] = True
        k = self[resource] = self.create(resource, limit)
        return k


def register_group(group):
    _groups.append(group)
    return group


class Connections(PoolGroup):

    def create(self, connection, limit):
        return connection.Pool(limit=limit)
connections = register_group(Connections(limit=use_global_limit))


class Producers(PoolGroup):

    def create(self, connection, limit):
        return ProducerPool(connections[connection], limit=limit)
producers = register_group(Producers(limit=use_global_limit))


def _all_pools():
    return chain(*[(values(g) if g else iter([])) for g in _groups])


def get_limit():
    return _limit[0]


def set_limit(limit, force=False, reset_after=False):
    limit = limit or 0
    glimit = _limit[0] or 0
    if limit < glimit:
        if not disable_limit_protection and (_used[0] and not force):
            raise RuntimeError("Can't lower limit after pool in use.")
        reset_after = True
    if limit != glimit:
        _limit[0] = limit
        for pool in _all_pools():
            pool.limit = limit
        if reset_after:
            reset()
    return limit


def reset(*args, **kwargs):
    for pool in _all_pools():
        try:
            pool.force_close_all()
        except Exception:
            pass
    for group in _groups:
        group.clear()
    _used[0] = False

try:
    from multiprocessing.util import register_after_fork
    register_after_fork(connections, reset)
except ImportError:  # pragma: no cover
    pass

########NEW FILE########
__FILENAME__ = serialization
"""
kombu.serialization
===================

Serialization utilities.

"""
from __future__ import absolute_import

import codecs
import os
import sys

import pickle as pypickle
try:
    import cPickle as cpickle
except ImportError:  # pragma: no cover
    cpickle = None  # noqa

from collections import namedtuple
from contextlib import contextmanager
from io import BytesIO

from .exceptions import (
    ContentDisallowed, DecodeError, EncodeError, SerializerNotInstalled
)
from .five import reraise, text_t
from .utils import entrypoints
from .utils.encoding import str_to_bytes, bytes_t

__all__ = ['pickle', 'loads', 'dumps', 'register', 'unregister']
SKIP_DECODE = frozenset(['binary', 'ascii-8bit'])
TRUSTED_CONTENT = frozenset(['application/data', 'application/text'])

if sys.platform.startswith('java'):  # pragma: no cover

    def _decode(t, coding):
        return codecs.getdecoder(coding)(t)[0]
else:
    _decode = codecs.decode

pickle = cpickle or pypickle
pickle_load = pickle.load

#: Kombu requires Python 2.5 or later so we use protocol 2 by default.
#: There's a new protocol (3) but this is only supported by Python 3.
pickle_protocol = int(os.environ.get('PICKLE_PROTOCOL', 2))

codec = namedtuple('codec', ('content_type', 'content_encoding', 'encoder'))


@contextmanager
def _reraise_errors(wrapper,
                    include=(Exception, ), exclude=(SerializerNotInstalled, )):
    try:
        yield
    except exclude:
        raise
    except include as exc:
        reraise(wrapper, wrapper(exc), sys.exc_info()[2])


def pickle_loads(s, load=pickle_load):
    # used to support buffer objects
    return load(BytesIO(s))


def parenthesize_alias(first, second):
    return '%s (%s)' % (first, second) if first else second


class SerializerRegistry(object):
    """The registry keeps track of serialization methods."""

    def __init__(self):
        self._encoders = {}
        self._decoders = {}
        self._default_encode = None
        self._default_content_type = None
        self._default_content_encoding = None
        self._disabled_content_types = set()
        self.type_to_name = {}
        self.name_to_type = {}

    def register(self, name, encoder, decoder, content_type,
                 content_encoding='utf-8'):
        if encoder:
            self._encoders[name] = codec(
                content_type, content_encoding, encoder,
            )
        if decoder:
            self._decoders[content_type] = decoder
        self.type_to_name[content_type] = name
        self.name_to_type[name] = content_type

    def enable(self, name):
        if '/' not in name:
            name = self.name_to_type[name]
        self._disabled_content_types.discard(name)

    def disable(self, name):
        if '/' not in name:
            name = self.name_to_type[name]
        self._disabled_content_types.add(name)

    def unregister(self, name):
        try:
            content_type = self.name_to_type[name]
            self._decoders.pop(content_type, None)
            self._encoders.pop(name, None)
            self.type_to_name.pop(content_type, None)
            self.name_to_type.pop(name, None)
        except KeyError:
            raise SerializerNotInstalled(
                'No encoder/decoder installed for {0}'.format(name))

    def _set_default_serializer(self, name):
        """
        Set the default serialization method used by this library.

        :param name: The name of the registered serialization method.
            For example, `json` (default), `pickle`, `yaml`, `msgpack`,
            or any custom methods registered using :meth:`register`.

        :raises SerializerNotInstalled: If the serialization method
            requested is not available.
        """
        try:
            (self._default_content_type, self._default_content_encoding,
             self._default_encode) = self._encoders[name]
        except KeyError:
            raise SerializerNotInstalled(
                'No encoder installed for {0}'.format(name))

    def dumps(self, data, serializer=None):
        if serializer == 'raw':
            return raw_encode(data)
        if serializer and not self._encoders.get(serializer):
            raise SerializerNotInstalled(
                'No encoder installed for {0}'.format(serializer))

        # If a raw string was sent, assume binary encoding
        # (it's likely either ASCII or a raw binary file, and a character
        # set of 'binary' will encompass both, even if not ideal.
        if not serializer and isinstance(data, bytes_t):
            # In Python 3+, this would be "bytes"; allow binary data to be
            # sent as a message without getting encoder errors
            return 'application/data', 'binary', data

        # For Unicode objects, force it into a string
        if not serializer and isinstance(data, text_t):
            with _reraise_errors(EncodeError, exclude=()):
                payload = data.encode('utf-8')
            return 'text/plain', 'utf-8', payload

        if serializer:
            content_type, content_encoding, encoder = \
                self._encoders[serializer]
        else:
            encoder = self._default_encode
            content_type = self._default_content_type
            content_encoding = self._default_content_encoding

        with _reraise_errors(EncodeError):
            payload = encoder(data)
        return content_type, content_encoding, payload
    encode = dumps  # XXX compat

    def loads(self, data, content_type, content_encoding,
              accept=None, force=False, _trusted_content=TRUSTED_CONTENT):
        content_type = content_type or 'application/data'
        if accept is not None:
            if content_type not in _trusted_content \
                    and content_type not in accept:
                raise self._for_untrusted_content(content_type, 'untrusted')
        else:
            if content_type in self._disabled_content_types and not force:
                raise self._for_untrusted_content(content_type, 'disabled')
        content_encoding = (content_encoding or 'utf-8').lower()

        if data:
            decode = self._decoders.get(content_type)
            if decode:
                with _reraise_errors(DecodeError):
                    return decode(data)
            if content_encoding not in SKIP_DECODE and \
                    not isinstance(data, text_t):
                with _reraise_errors(DecodeError):
                    return _decode(data, content_encoding)
        return data
    decode = loads  # XXX compat

    def _for_untrusted_content(self, ctype, why):
        return ContentDisallowed(
            'Refusing to deserialize {0} content of type {1}'.format(
                why,
                parenthesize_alias(self.type_to_name.get(ctype, ctype), ctype),
            ),
        )


#: Global registry of serializers/deserializers.
registry = SerializerRegistry()


"""
.. function:: dumps(data, serializer=default_serializer)

    Serialize a data structure into a string suitable for sending
    as an AMQP message body.

    :param data: The message data to send. Can be a list,
        dictionary or a string.

    :keyword serializer: An optional string representing
        the serialization method you want the data marshalled
        into. (For example, `json`, `raw`, or `pickle`).

        If :const:`None` (default), then json will be used, unless
        `data` is a :class:`str` or :class:`unicode` object. In this
        latter case, no serialization occurs as it would be
        unnecessary.

        Note that if `serializer` is specified, then that
        serialization method will be used even if a :class:`str`
        or :class:`unicode` object is passed in.

    :returns: A three-item tuple containing the content type
        (e.g., `application/json`), content encoding, (e.g.,
        `utf-8`) and a string containing the serialized
        data.

    :raises SerializerNotInstalled: If the serialization method
            requested is not available.
"""
dumps = encode = registry.encode   # XXX encode is a compat alias

"""
.. function:: loads(data, content_type, content_encoding):

    Deserialize a data stream as serialized using `dumps`
    based on `content_type`.

    :param data: The message data to deserialize.

    :param content_type: The content-type of the data.
        (e.g., `application/json`).

    :param content_encoding: The content-encoding of the data.
        (e.g., `utf-8`, `binary`, or `us-ascii`).

    :returns: The unserialized data.

"""
loads = decode = registry.decode  # XXX decode is a compat alias


"""
.. function:: register(name, encoder, decoder, content_type,
                       content_encoding='utf-8'):
    Register a new encoder/decoder.

    :param name: A convenience name for the serialization method.

    :param encoder: A method that will be passed a python data structure
        and should return a string representing the serialized data.
        If :const:`None`, then only a decoder will be registered. Encoding
        will not be possible.

    :param decoder: A method that will be passed a string representing
        serialized data and should return a python data structure.
        If :const:`None`, then only an encoder will be registered.
        Decoding will not be possible.

    :param content_type: The mime-type describing the serialized
        structure.

    :param content_encoding: The content encoding (character set) that
        the `decoder` method will be returning. Will usually be
        `utf-8`, `us-ascii`, or `binary`.

"""
register = registry.register


"""
.. function:: unregister(name):
    Unregister registered encoder/decoder.

    :param name: Registered serialization method name.

"""
unregister = registry.unregister


def raw_encode(data):
    """Special case serializer."""
    content_type = 'application/data'
    payload = data
    if isinstance(payload, text_t):
        content_encoding = 'utf-8'
        with _reraise_errors(EncodeError, exclude=()):
            payload = payload.encode(content_encoding)
    else:
        content_encoding = 'binary'
    return content_type, content_encoding, payload


def register_json():
    """Register a encoder/decoder for JSON serialization."""
    from kombu.utils import json as _json

    registry.register('json', _json.dumps, _json.loads,
                      content_type='application/json',
                      content_encoding='utf-8')


def register_yaml():
    """Register a encoder/decoder for YAML serialization.

    It is slower than JSON, but allows for more data types
    to be serialized. Useful if you need to send data such as dates"""
    try:
        import yaml
        registry.register('yaml', yaml.safe_dump, yaml.safe_load,
                          content_type='application/x-yaml',
                          content_encoding='utf-8')
    except ImportError:

        def not_available(*args, **kwargs):
            """In case a client receives a yaml message, but yaml
            isn't installed."""
            raise SerializerNotInstalled(
                'No decoder installed for YAML. Install the PyYAML library')
        registry.register('yaml', None, not_available, 'application/x-yaml')


if sys.version_info[0] == 3:  # pragma: no cover

    def unpickle(s):
        return pickle_loads(str_to_bytes(s))

else:
    unpickle = pickle_loads  # noqa


def register_pickle():
    """The fastest serialization method, but restricts
    you to python clients."""

    def pickle_dumps(obj, dumper=pickle.dumps):
        return dumper(obj, protocol=pickle_protocol)

    registry.register('pickle', pickle_dumps, unpickle,
                      content_type='application/x-python-serialize',
                      content_encoding='binary')


def register_msgpack():
    """See http://msgpack.sourceforge.net/"""
    try:
        try:
            from msgpack import packb as pack, unpackb
            unpack = lambda s: unpackb(s, encoding='utf-8')
        except ImportError:
            # msgpack < 0.2.0 and Python 2.5
            from msgpack import packs as pack, unpacks as unpack  # noqa
        registry.register(
            'msgpack', pack, unpack,
            content_type='application/x-msgpack',
            content_encoding='binary')
    except (ImportError, ValueError):

        def not_available(*args, **kwargs):
            """In case a client receives a msgpack message, but yaml
            isn't installed."""
            raise SerializerNotInstalled(
                'No decoder installed for msgpack. '
                'Please install the msgpack library')
        registry.register('msgpack', None, not_available,
                          'application/x-msgpack')

# Register the base serialization methods.
register_json()
register_pickle()
register_yaml()
register_msgpack()

# Default serializer is 'json'
registry._set_default_serializer('json')


_setupfuns = {
    'json': register_json,
    'pickle': register_pickle,
    'yaml': register_yaml,
    'msgpack': register_msgpack,
    'application/json': register_json,
    'application/x-yaml': register_yaml,
    'application/x-python-serialize': register_pickle,
    'application/x-msgpack': register_msgpack,
}


def enable_insecure_serializers(choices=['pickle', 'yaml', 'msgpack']):
    """Enable serializers that are considered to be unsafe.

    Will enable ``pickle``, ``yaml`` and ``msgpack`` by default,
    but you can also specify a list of serializers (by name or content type)
    to enable.

    """
    for choice in choices:
        try:
            registry.enable(choice)
        except KeyError:
            pass


def disable_insecure_serializers(allowed=['json']):
    """Disable untrusted serializers.

    Will disable all serializers except ``json``
    or you can specify a list of deserializers to allow.

    .. note::

        Producers will still be able to serialize data
        in these formats, but consumers will not accept
        incoming data using the untrusted content types.

    """
    for name in registry._decoders:
        registry.disable(name)
    if allowed is not None:
        for name in allowed:
            registry.enable(name)


# Insecure serializers are disabled by default since v3.0
disable_insecure_serializers()

# Load entrypoints from installed extensions
for ep, args in entrypoints('kombu.serializers'):  # pragma: no cover
    register(ep.name, *args)


def prepare_accept_content(l, name_to_type=registry.name_to_type):
    if l is not None:
        return {n if '/' in n else name_to_type[n] for n in l}
    return l

########NEW FILE########
__FILENAME__ = simple
"""
kombu.simple
============

Simple interface.

"""
from __future__ import absolute_import

import socket

from collections import deque

from . import entity
from . import messaging
from .connection import maybe_channel
from .five import Empty, monotonic

__all__ = ['SimpleQueue', 'SimpleBuffer']


class SimpleBase(object):
    Empty = Empty
    _consuming = False

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def __init__(self, channel, producer, consumer, no_ack=False):
        self.channel = maybe_channel(channel)
        self.producer = producer
        self.consumer = consumer
        self.no_ack = no_ack
        self.queue = self.consumer.queues[0]
        self.buffer = deque()
        self.consumer.register_callback(self._receive)

    def get(self, block=True, timeout=None):
        if not block:
            return self.get_nowait()
        self._consume()
        elapsed = 0.0
        remaining = timeout
        while True:
            time_start = monotonic()
            if self.buffer:
                return self.buffer.pop()
            try:
                self.channel.connection.client.drain_events(
                    timeout=timeout and remaining)
            except socket.timeout:
                raise self.Empty()
            elapsed += monotonic() - time_start
            remaining = timeout and timeout - elapsed or None

    def get_nowait(self):
        m = self.queue.get(no_ack=self.no_ack)
        if not m:
            raise self.Empty()
        return m

    def put(self, message, serializer=None, headers=None, compression=None,
            routing_key=None, **kwargs):
        self.producer.publish(message,
                              serializer=serializer,
                              routing_key=routing_key,
                              headers=headers,
                              compression=compression,
                              **kwargs)

    def clear(self):
        return self.consumer.purge()

    def qsize(self):
        _, size, _ = self.queue.queue_declare(passive=True)
        return size

    def close(self):
        self.consumer.cancel()

    def _receive(self, message_data, message):
        self.buffer.append(message)

    def _consume(self):
        if not self._consuming:
            self.consumer.consume(no_ack=self.no_ack)
            self._consuming = True

    def __len__(self):
        """`len(self) -> self.qsize()`"""
        return self.qsize()

    def __bool__(self):
        return True
    __nonzero__ = __bool__


class SimpleQueue(SimpleBase):
    no_ack = False
    queue_opts = {}
    exchange_opts = {'type': 'direct'}

    def __init__(self, channel, name, no_ack=None, queue_opts=None,
                 exchange_opts=None, serializer=None,
                 compression=None, **kwargs):
        queue = name
        queue_opts = dict(self.queue_opts, **queue_opts or {})
        exchange_opts = dict(self.exchange_opts, **exchange_opts or {})
        if no_ack is None:
            no_ack = self.no_ack
        if not isinstance(queue, entity.Queue):
            exchange = entity.Exchange(name, **exchange_opts)
            queue = entity.Queue(name, exchange, name, **queue_opts)
            routing_key = name
        else:
            name = queue.name
            exchange = queue.exchange
            routing_key = queue.routing_key
        producer = messaging.Producer(channel, exchange,
                                      serializer=serializer,
                                      routing_key=routing_key,
                                      compression=compression)
        consumer = messaging.Consumer(channel, queue)
        super(SimpleQueue, self).__init__(channel, producer,
                                          consumer, no_ack, **kwargs)


class SimpleBuffer(SimpleQueue):
    no_ack = True
    queue_opts = dict(durable=False,
                      auto_delete=True)
    exchange_opts = dict(durable=False,
                         delivery_mode='transient',
                         auto_delete=True)

########NEW FILE########
__FILENAME__ = syn
"""
kombu.syn
=========

"""
from __future__ import absolute_import

import sys

__all__ = ['detect_environment']

_environment = None


def blocking(fun, *args, **kwargs):
    return fun(*args, **kwargs)


def select_blocking_method(type):
    pass


def _detect_environment():
    # ## -eventlet-
    if 'eventlet' in sys.modules:
        try:
            from eventlet.patcher import is_monkey_patched as is_eventlet
            import socket

            if is_eventlet(socket):
                return 'eventlet'
        except ImportError:
            pass

    # ## -gevent-
    if 'gevent' in sys.modules:
        try:
            from gevent import socket as _gsocket
            import socket

            if socket.socket is _gsocket.socket:
                return 'gevent'
        except ImportError:
            pass

    return 'default'


def detect_environment():
    global _environment
    if _environment is None:
        _environment = _detect_environment()
    return _environment

########NEW FILE########
__FILENAME__ = test_hub
from __future__ import absolute_import

from kombu.async import hub as _hub
from kombu.async.hub import Hub, get_event_loop, set_event_loop

from kombu.tests.case import Case


class test_Utils(Case):

    def setUp(self):
        self._prev_loop = get_event_loop()

    def tearDown(self):
        set_event_loop(self._prev_loop)

    def test_get_set_event_loop(self):
        set_event_loop(None)
        self.assertIsNone(_hub._current_loop)
        self.assertIsNone(get_event_loop())
        hub = Hub()
        set_event_loop(hub)
        self.assertIs(_hub._current_loop, hub)
        self.assertIs(get_event_loop(), hub)


class test_Hub(Case):

    def setUp(self):
        self.hub = Hub()

    def tearDown(self):
        self.hub.close()

########NEW FILE########
__FILENAME__ = test_semaphore
from __future__ import absolute_import

from kombu.async.semaphore import LaxBoundedSemaphore

from kombu.tests.case import Case


class test_LaxBoundedSemaphore(Case):

    def test_over_release(self):
        x = LaxBoundedSemaphore(2)
        calls = []
        for i in range(1, 21):
            x.acquire(calls.append, i)
        x.release()
        x.acquire(calls.append, 'x')
        x.release()
        x.acquire(calls.append, 'y')

        self.assertEqual(calls, [1, 2, 3, 4])

        for i in range(30):
            x.release()
        self.assertEqual(calls, list(range(1, 21)) + ['x', 'y'])
        self.assertEqual(x.value, x.initial_value)

        calls[:] = []
        for i in range(1, 11):
            x.acquire(calls.append, i)
        for i in range(1, 11):
            x.release()
        self.assertEqual(calls, list(range(1, 11)))

        calls[:] = []
        self.assertEqual(x.value, x.initial_value)
        x.acquire(calls.append, 'x')
        self.assertEqual(x.value, 1)
        x.acquire(calls.append, 'y')
        self.assertEqual(x.value, 0)
        x.release()
        self.assertEqual(x.value, 1)
        x.release()
        self.assertEqual(x.value, 2)
        x.release()
        self.assertEqual(x.value, 2)

########NEW FILE########
__FILENAME__ = case
from __future__ import absolute_import

import os
import sys
import types

from functools import wraps
from io import StringIO

import mock

from nose import SkipTest

from kombu.five import builtins, string_t
from kombu.utils.encoding import ensure_bytes

try:
    import unittest
    unittest.skip
except AttributeError:
    import unittest2 as unittest  # noqa

PY3 = sys.version_info[0] == 3

patch = mock.patch
call = mock.call


class Case(unittest.TestCase):

    def assertItemsEqual(self, a, b, *args, **kwargs):
        return self.assertEqual(sorted(a), sorted(b), *args, **kwargs)
    assertSameElements = assertItemsEqual


class Mock(mock.Mock):

    def __init__(self, *args, **kwargs):
        attrs = kwargs.pop('attrs', None) or {}
        super(Mock, self).__init__(*args, **kwargs)
        for attr_name, attr_value in attrs.items():
            setattr(self, attr_name, attr_value)


class _ContextMock(Mock):
    """Dummy class implementing __enter__ and __exit__
    as the with statement requires these to be implemented
    in the class, not just the instance."""

    def __enter__(self):
        pass

    def __exit__(self, *exc_info):
        pass


def ContextMock(*args, **kwargs):
    obj = _ContextMock(*args, **kwargs)
    obj.attach_mock(Mock(), '__enter__')
    obj.attach_mock(Mock(), '__exit__')
    obj.__enter__.return_value = obj
    # if __exit__ return a value the exception is ignored,
    # so it must return None here.
    obj.__exit__.return_value = None
    return obj


class MockPool(object):

    def __init__(self, value=None):
        self.value = value or ContextMock()

    def acquire(self, **kwargs):
        return self.value


def redirect_stdouts(fun):

    @wraps(fun)
    def _inner(*args, **kwargs):
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        try:
            return fun(*args, **dict(kwargs,
                                     stdout=sys.stdout, stderr=sys.stderr))
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

    return _inner


def module_exists(*modules):

    def _inner(fun):

        @wraps(fun)
        def __inner(*args, **kwargs):
            gen = []
            for module in modules:
                if isinstance(module, string_t):
                    if not PY3:
                        module = ensure_bytes(module)
                    module = types.ModuleType(module)
                gen.append(module)
                sys.modules[module.__name__] = module
                name = module.__name__
                if '.' in name:
                    parent, _, attr = name.rpartition('.')
                    setattr(sys.modules[parent], attr, module)
            try:
                return fun(*args, **kwargs)
            finally:
                for module in gen:
                    sys.modules.pop(module.__name__, None)

        return __inner
    return _inner


# Taken from
# http://bitbucket.org/runeh/snippets/src/tip/missing_modules.py
def mask_modules(*modnames):
    def _inner(fun):

        @wraps(fun)
        def __inner(*args, **kwargs):
            realimport = builtins.__import__

            def myimp(name, *args, **kwargs):
                if name in modnames:
                    raise ImportError('No module named %s' % name)
                else:
                    return realimport(name, *args, **kwargs)

            builtins.__import__ = myimp
            try:
                return fun(*args, **kwargs)
            finally:
                builtins.__import__ = realimport

        return __inner
    return _inner


def skip_if_environ(env_var_name):

    def _wrap_test(fun):

        @wraps(fun)
        def _skips_if_environ(*args, **kwargs):
            if os.environ.get(env_var_name):
                raise SkipTest('SKIP %s: %s set\n' % (
                    fun.__name__, env_var_name))
            return fun(*args, **kwargs)

        return _skips_if_environ

    return _wrap_test


def skip_if_module(module):
    def _wrap_test(fun):
        @wraps(fun)
        def _skip_if_module(*args, **kwargs):
            try:
                __import__(module)
                raise SkipTest('SKIP %s: %s available\n' % (
                    fun.__name__, module))
            except ImportError:
                pass
            return fun(*args, **kwargs)
        return _skip_if_module
    return _wrap_test


def skip_if_not_module(module, import_errors=(ImportError, )):
    def _wrap_test(fun):
        @wraps(fun)
        def _skip_if_not_module(*args, **kwargs):
            try:
                __import__(module)
            except import_errors:
                raise SkipTest('SKIP %s: %s available\n' % (
                    fun.__name__, module))
            return fun(*args, **kwargs)
        return _skip_if_not_module
    return _wrap_test

########NEW FILE########
__FILENAME__ = mocks
from __future__ import absolute_import

from itertools import count

from kombu.transport import base
from kombu.utils import json


class Message(base.Message):

    def __init__(self, *args, **kwargs):
        self.throw_decode_error = kwargs.get('throw_decode_error', False)
        super(Message, self).__init__(*args, **kwargs)

    def decode(self):
        if self.throw_decode_error:
            raise ValueError("can't decode message")
        return super(Message, self).decode()


class Channel(base.StdChannel):
    open = True
    throw_decode_error = False
    _ids = count(1)

    def __init__(self, connection):
        self.connection = connection
        self.called = []
        self.deliveries = count(1)
        self.to_deliver = []
        self.events = {'basic_return': set()}
        self.channel_id = next(self._ids)

    def _called(self, name):
        self.called.append(name)

    def __contains__(self, key):
        return key in self.called

    def exchange_declare(self, *args, **kwargs):
        self._called('exchange_declare')

    def prepare_message(self, body, priority=0, content_type=None,
                        content_encoding=None, headers=None, properties={}):
        self._called('prepare_message')
        return dict(body=body,
                    headers=headers,
                    properties=properties,
                    priority=priority,
                    content_type=content_type,
                    content_encoding=content_encoding)

    def basic_publish(self, message, exchange='', routing_key='',
                      mandatory=False, immediate=False, **kwargs):
        self._called('basic_publish')
        return message, exchange, routing_key

    def exchange_delete(self, *args, **kwargs):
        self._called('exchange_delete')

    def queue_declare(self, *args, **kwargs):
        self._called('queue_declare')

    def queue_bind(self, *args, **kwargs):
        self._called('queue_bind')

    def queue_unbind(self, *args, **kwargs):
        self._called('queue_unbind')

    def queue_delete(self, queue, if_unused=False, if_empty=False, **kwargs):
        self._called('queue_delete')

    def basic_get(self, *args, **kwargs):
        self._called('basic_get')
        try:
            return self.to_deliver.pop()
        except IndexError:
            pass

    def queue_purge(self, *args, **kwargs):
        self._called('queue_purge')

    def basic_consume(self, *args, **kwargs):
        self._called('basic_consume')

    def basic_cancel(self, *args, **kwargs):
        self._called('basic_cancel')

    def basic_ack(self, *args, **kwargs):
        self._called('basic_ack')

    def basic_recover(self, requeue=False):
        self._called('basic_recover')

    def exchange_bind(self, *args, **kwargs):
        self._called('exchange_bind')

    def exchange_unbind(self, *args, **kwargs):
        self._called('exchange_unbind')

    def close(self):
        self._called('close')

    def message_to_python(self, message, *args, **kwargs):
        self._called('message_to_python')
        return Message(self, body=json.dumps(message),
                       delivery_tag=next(self.deliveries),
                       throw_decode_error=self.throw_decode_error,
                       content_type='application/json',
                       content_encoding='utf-8')

    def flow(self, active):
        self._called('flow')

    def basic_reject(self, delivery_tag, requeue=False):
        if requeue:
            return self._called('basic_reject:requeue')
        return self._called('basic_reject')

    def basic_qos(self, prefetch_size=0, prefetch_count=0,
                  apply_global=False):
        self._called('basic_qos')


class Connection(object):
    connected = True

    def __init__(self, client):
        self.client = client

    def channel(self):
        return Channel(self)


class Transport(base.Transport):

    def establish_connection(self):
        return Connection(self.client)

    def create_channel(self, connection):
        return connection.channel()

    def drain_events(self, connection, **kwargs):
        return 'event'

    def close_connection(self, connection):
        connection.connected = False

########NEW FILE########
__FILENAME__ = test_clocks
from __future__ import absolute_import

import pickle

from heapq import heappush
from time import time

from kombu.clocks import LamportClock, timetuple

from .case import Mock, Case


class test_LamportClock(Case):

    def test_clocks(self):
        c1 = LamportClock()
        c2 = LamportClock()

        c1.forward()
        c2.forward()
        c1.forward()
        c1.forward()
        c2.adjust(c1.value)
        self.assertEqual(c2.value, c1.value + 1)
        self.assertTrue(repr(c1))

        c2_val = c2.value
        c2.forward()
        c2.forward()
        c2.adjust(c1.value)
        self.assertEqual(c2.value, c2_val + 2 + 1)

        c1.adjust(c2.value)
        self.assertEqual(c1.value, c2.value + 1)

    def test_sort(self):
        c = LamportClock()
        pid1 = 'a.example.com:312'
        pid2 = 'b.example.com:311'

        events = []

        m1 = (c.forward(), pid1)
        heappush(events, m1)
        m2 = (c.forward(), pid2)
        heappush(events, m2)
        m3 = (c.forward(), pid1)
        heappush(events, m3)
        m4 = (30, pid1)
        heappush(events, m4)
        m5 = (30, pid2)
        heappush(events, m5)

        self.assertEqual(str(c), str(c.value))

        self.assertEqual(c.sort_heap(events), m1)
        self.assertEqual(c.sort_heap([m4, m5]), m4)
        self.assertEqual(c.sort_heap([m4, m5, m1]), m4)


class test_timetuple(Case):

    def test_repr(self):
        x = timetuple(133, time(), 'id', Mock())
        self.assertTrue(repr(x))

    def test_pickleable(self):
        x = timetuple(133, time(), 'id', 'obj')
        self.assertEqual(pickle.loads(pickle.dumps(x)), tuple(x))

    def test_order(self):
        t1 = time()
        t2 = time() + 300  # windows clock not reliable
        a = timetuple(133, t1, 'A', 'obj')
        b = timetuple(140, t1, 'A', 'obj')
        self.assertTrue(a.__getnewargs__())
        self.assertEqual(a.clock, 133)
        self.assertEqual(a.timestamp, t1)
        self.assertEqual(a.id, 'A')
        self.assertEqual(a.obj, 'obj')
        self.assertTrue(
            a <= b,
        )
        self.assertTrue(
            b >= a,
        )

        self.assertEqual(
            timetuple(134, time(), 'A', 'obj').__lt__(tuple()),
            NotImplemented,
        )
        self.assertGreater(
            timetuple(134, t2, 'A', 'obj'),
            timetuple(133, t1, 'A', 'obj'),
        )
        self.assertGreater(
            timetuple(134, t1, 'B', 'obj'),
            timetuple(134, t1, 'A', 'obj'),
        )

        self.assertGreater(
            timetuple(None, t2, 'B', 'obj'),
            timetuple(None, t1, 'A', 'obj'),
        )

########NEW FILE########
__FILENAME__ = test_common
from __future__ import absolute_import

import socket

from amqp import RecoverableConnectionError

from kombu import common
from kombu.common import (
    Broadcast, maybe_declare,
    send_reply, collect_replies,
    declaration_cached, ignore_errors,
    QoS, PREFETCH_COUNT_MAX,
)

from .case import Case, ContextMock, Mock, MockPool, patch


class test_ignore_errors(Case):

    def test_ignored(self):
        connection = Mock()
        connection.channel_errors = (KeyError, )
        connection.connection_errors = (KeyError, )

        with ignore_errors(connection):
            raise KeyError()

        def raising():
            raise KeyError()

        ignore_errors(connection, raising)

        connection.channel_errors = connection.connection_errors = \
            ()

        with self.assertRaises(KeyError):
            with ignore_errors(connection):
                raise KeyError()


class test_declaration_cached(Case):

    def test_when_cached(self):
        chan = Mock()
        chan.connection.client.declared_entities = ['foo']
        self.assertTrue(declaration_cached('foo', chan))

    def test_when_not_cached(self):
        chan = Mock()
        chan.connection.client.declared_entities = ['bar']
        self.assertFalse(declaration_cached('foo', chan))


class test_Broadcast(Case):

    def test_arguments(self):
        q = Broadcast(name='test_Broadcast')
        self.assertTrue(q.name.startswith('bcast.'))
        self.assertEqual(q.alias, 'test_Broadcast')
        self.assertTrue(q.auto_delete)
        self.assertEqual(q.exchange.name, 'test_Broadcast')
        self.assertEqual(q.exchange.type, 'fanout')

        q = Broadcast('test_Broadcast', 'explicit_queue_name')
        self.assertEqual(q.name, 'explicit_queue_name')
        self.assertEqual(q.exchange.name, 'test_Broadcast')


class test_maybe_declare(Case):

    def test_cacheable(self):
        channel = Mock()
        client = channel.connection.client = Mock()
        client.declared_entities = set()
        entity = Mock()
        entity.can_cache_declaration = True
        entity.auto_delete = False
        entity.is_bound = True
        entity.channel = channel

        maybe_declare(entity, channel)
        self.assertEqual(entity.declare.call_count, 1)
        self.assertIn(
            hash(entity), channel.connection.client.declared_entities,
        )

        maybe_declare(entity, channel)
        self.assertEqual(entity.declare.call_count, 1)

        entity.channel.connection = None
        with self.assertRaises(RecoverableConnectionError):
            maybe_declare(entity)

    def test_binds_entities(self):
        channel = Mock()
        channel.connection.client.declared_entities = set()
        entity = Mock()
        entity.can_cache_declaration = True
        entity.is_bound = False
        entity.bind.return_value = entity
        entity.bind.return_value.channel = channel

        maybe_declare(entity, channel)
        entity.bind.assert_called_with(channel)

    def test_with_retry(self):
        channel = Mock()
        entity = Mock()
        entity.can_cache_declaration = True
        entity.is_bound = True
        entity.channel = channel

        maybe_declare(entity, channel, retry=True)
        self.assertTrue(channel.connection.client.ensure.call_count)


class test_replies(Case):

    def test_send_reply(self):
        req = Mock()
        req.content_type = 'application/json'
        req.content_encoding = 'binary'
        req.properties = {'reply_to': 'hello',
                          'correlation_id': 'world'}
        channel = Mock()
        exchange = Mock()
        exchange.is_bound = True
        exchange.channel = channel
        producer = Mock()
        producer.channel = channel
        producer.channel.connection.client.declared_entities = set()
        send_reply(exchange, req, {'hello': 'world'}, producer)

        self.assertTrue(producer.publish.call_count)
        args = producer.publish.call_args
        self.assertDictEqual(args[0][0], {'hello': 'world'})
        self.assertDictEqual(args[1], {'exchange': exchange,
                                       'routing_key': 'hello',
                                       'correlation_id': 'world',
                                       'serializer': 'json',
                                       'retry': False,
                                       'retry_policy': None,
                                       'content_encoding': 'binary'})

    @patch('kombu.common.itermessages')
    def test_collect_replies_with_ack(self, itermessages):
        conn, channel, queue = Mock(), Mock(), Mock()
        body, message = Mock(), Mock()
        itermessages.return_value = [(body, message)]
        it = collect_replies(conn, channel, queue, no_ack=False)
        m = next(it)
        self.assertIs(m, body)
        itermessages.assert_called_with(conn, channel, queue, no_ack=False)
        message.ack.assert_called_with()

        with self.assertRaises(StopIteration):
            next(it)

        channel.after_reply_message_received.assert_called_with(queue.name)

    @patch('kombu.common.itermessages')
    def test_collect_replies_no_ack(self, itermessages):
        conn, channel, queue = Mock(), Mock(), Mock()
        body, message = Mock(), Mock()
        itermessages.return_value = [(body, message)]
        it = collect_replies(conn, channel, queue)
        m = next(it)
        self.assertIs(m, body)
        itermessages.assert_called_with(conn, channel, queue, no_ack=True)
        self.assertFalse(message.ack.called)

    @patch('kombu.common.itermessages')
    def test_collect_replies_no_replies(self, itermessages):
        conn, channel, queue = Mock(), Mock(), Mock()
        itermessages.return_value = []
        it = collect_replies(conn, channel, queue)
        with self.assertRaises(StopIteration):
            next(it)

        self.assertFalse(channel.after_reply_message_received.called)


class test_insured(Case):

    @patch('kombu.common.logger')
    def test_ensure_errback(self, logger):
        common._ensure_errback('foo', 30)
        self.assertTrue(logger.error.called)

    def test_revive_connection(self):
        on_revive = Mock()
        channel = Mock()
        common.revive_connection(Mock(), channel, on_revive)
        on_revive.assert_called_with(channel)

        common.revive_connection(Mock(), channel, None)

    def get_insured_mocks(self, insured_returns=('works', 'ignored')):
        conn = ContextMock()
        pool = MockPool(conn)
        fun = Mock()
        insured = conn.autoretry.return_value = Mock()
        insured.return_value = insured_returns
        return conn, pool, fun, insured

    def test_insured(self):
        conn, pool, fun, insured = self.get_insured_mocks()

        ret = common.insured(pool, fun, (2, 2), {'foo': 'bar'})
        self.assertEqual(ret, 'works')
        conn.ensure_connection.assert_called_with(
            errback=common._ensure_errback,
        )

        self.assertTrue(insured.called)
        i_args, i_kwargs = insured.call_args
        self.assertTupleEqual(i_args, (2, 2))
        self.assertDictEqual(i_kwargs, {'foo': 'bar',
                                        'connection': conn})

        self.assertTrue(conn.autoretry.called)
        ar_args, ar_kwargs = conn.autoretry.call_args
        self.assertTupleEqual(ar_args, (fun, conn.default_channel))
        self.assertTrue(ar_kwargs.get('on_revive'))
        self.assertTrue(ar_kwargs.get('errback'))

    def test_insured_custom_errback(self):
        conn, pool, fun, insured = self.get_insured_mocks()

        custom_errback = Mock()
        common.insured(pool, fun, (2, 2), {'foo': 'bar'},
                       errback=custom_errback)
        conn.ensure_connection.assert_called_with(errback=custom_errback)


class MockConsumer(object):
    consumers = set()

    def __init__(self, channel, queues=None, callbacks=None, **kwargs):
        self.channel = channel
        self.queues = queues
        self.callbacks = callbacks

    def __enter__(self):
        self.consumers.add(self)
        return self

    def __exit__(self, *exc_info):
        self.consumers.discard(self)


class test_itermessages(Case):

    class MockConnection(object):
        should_raise_timeout = False

        def drain_events(self, **kwargs):
            if self.should_raise_timeout:
                raise socket.timeout()
            for consumer in MockConsumer.consumers:
                for callback in consumer.callbacks:
                    callback('body', 'message')

    def test_default(self):
        conn = self.MockConnection()
        channel = Mock()
        channel.connection.client = conn
        it = common.itermessages(conn, channel, 'q', limit=1,
                                 Consumer=MockConsumer)

        ret = next(it)
        self.assertTupleEqual(ret, ('body', 'message'))

        with self.assertRaises(StopIteration):
            next(it)

    def test_when_raises_socket_timeout(self):
        conn = self.MockConnection()
        conn.should_raise_timeout = True
        channel = Mock()
        channel.connection.client = conn
        it = common.itermessages(conn, channel, 'q', limit=1,
                                 Consumer=MockConsumer)

        with self.assertRaises(StopIteration):
            next(it)

    @patch('kombu.common.deque')
    def test_when_raises_IndexError(self, deque):
        deque_instance = deque.return_value = Mock()
        deque_instance.popleft.side_effect = IndexError()
        conn = self.MockConnection()
        channel = Mock()
        it = common.itermessages(conn, channel, 'q', limit=1,
                                 Consumer=MockConsumer)

        with self.assertRaises(StopIteration):
            next(it)


class test_QoS(Case):

    class _QoS(QoS):
        def __init__(self, value):
            self.value = value
            QoS.__init__(self, None, value)

        def set(self, value):
            return value

    def test_qos_exceeds_16bit(self):
        with patch('kombu.common.logger') as logger:
            callback = Mock()
            qos = QoS(callback, 10)
            qos.prev = 100
            # cannot use 2 ** 32 because of a bug on OSX Py2.5:
            # https://jira.mongodb.org/browse/PYTHON-389
            qos.set(4294967296)
            self.assertTrue(logger.warn.called)
            callback.assert_called_with(prefetch_count=0)

    def test_qos_increment_decrement(self):
        qos = self._QoS(10)
        self.assertEqual(qos.increment_eventually(), 11)
        self.assertEqual(qos.increment_eventually(3), 14)
        self.assertEqual(qos.increment_eventually(-30), 14)
        self.assertEqual(qos.decrement_eventually(7), 7)
        self.assertEqual(qos.decrement_eventually(), 6)

    def test_qos_disabled_increment_decrement(self):
        qos = self._QoS(0)
        self.assertEqual(qos.increment_eventually(), 0)
        self.assertEqual(qos.increment_eventually(3), 0)
        self.assertEqual(qos.increment_eventually(-30), 0)
        self.assertEqual(qos.decrement_eventually(7), 0)
        self.assertEqual(qos.decrement_eventually(), 0)
        self.assertEqual(qos.decrement_eventually(10), 0)

    def test_qos_thread_safe(self):
        qos = self._QoS(10)

        def add():
            for i in range(1000):
                qos.increment_eventually()

        def sub():
            for i in range(1000):
                qos.decrement_eventually()

        def threaded(funs):
            from threading import Thread
            threads = [Thread(target=fun) for fun in funs]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        threaded([add, add])
        self.assertEqual(qos.value, 2010)

        qos.value = 1000
        threaded([add, sub])  # n = 2
        self.assertEqual(qos.value, 1000)

    def test_exceeds_short(self):
        qos = QoS(Mock(), PREFETCH_COUNT_MAX - 1)
        qos.update()
        self.assertEqual(qos.value, PREFETCH_COUNT_MAX - 1)
        qos.increment_eventually()
        self.assertEqual(qos.value, PREFETCH_COUNT_MAX)
        qos.increment_eventually()
        self.assertEqual(qos.value, PREFETCH_COUNT_MAX + 1)
        qos.decrement_eventually()
        self.assertEqual(qos.value, PREFETCH_COUNT_MAX)
        qos.decrement_eventually()
        self.assertEqual(qos.value, PREFETCH_COUNT_MAX - 1)

    def test_consumer_increment_decrement(self):
        mconsumer = Mock()
        qos = QoS(mconsumer.qos, 10)
        qos.update()
        self.assertEqual(qos.value, 10)
        mconsumer.qos.assert_called_with(prefetch_count=10)
        qos.decrement_eventually()
        qos.update()
        self.assertEqual(qos.value, 9)
        mconsumer.qos.assert_called_with(prefetch_count=9)
        qos.decrement_eventually()
        self.assertEqual(qos.value, 8)
        mconsumer.qos.assert_called_with(prefetch_count=9)
        self.assertIn({'prefetch_count': 9}, mconsumer.qos.call_args)

        # Does not decrement 0 value
        qos.value = 0
        qos.decrement_eventually()
        self.assertEqual(qos.value, 0)
        qos.increment_eventually()
        self.assertEqual(qos.value, 0)

    def test_consumer_decrement_eventually(self):
        mconsumer = Mock()
        qos = QoS(mconsumer.qos, 10)
        qos.decrement_eventually()
        self.assertEqual(qos.value, 9)
        qos.value = 0
        qos.decrement_eventually()
        self.assertEqual(qos.value, 0)

    def test_set(self):
        mconsumer = Mock()
        qos = QoS(mconsumer.qos, 10)
        qos.set(12)
        self.assertEqual(qos.prev, 12)
        qos.set(qos.prev)

########NEW FILE########
__FILENAME__ = test_compat
from __future__ import absolute_import

from kombu import Connection, Exchange, Queue
from kombu import compat

from .case import Case, Mock, patch
from .mocks import Transport, Channel


class test_misc(Case):

    def test_iterconsume(self):

        class MyConnection(object):
            drained = 0

            def drain_events(self, *args, **kwargs):
                self.drained += 1
                return self.drained

        class Consumer(object):
            active = False

            def consume(self, *args, **kwargs):
                self.active = True

        conn = MyConnection()
        consumer = Consumer()
        it = compat._iterconsume(conn, consumer)
        self.assertEqual(next(it), 1)
        self.assertTrue(consumer.active)

        it2 = compat._iterconsume(conn, consumer, limit=10)
        self.assertEqual(list(it2), [2, 3, 4, 5, 6, 7, 8, 9, 10, 11])

    def test_Queue_from_dict(self):
        defs = {'binding_key': 'foo.#',
                'exchange': 'fooex',
                'exchange_type': 'topic',
                'durable': True,
                'auto_delete': False}

        q1 = Queue.from_dict('foo', **dict(defs))
        self.assertEqual(q1.name, 'foo')
        self.assertEqual(q1.routing_key, 'foo.#')
        self.assertEqual(q1.exchange.name, 'fooex')
        self.assertEqual(q1.exchange.type, 'topic')
        self.assertTrue(q1.durable)
        self.assertTrue(q1.exchange.durable)
        self.assertFalse(q1.auto_delete)
        self.assertFalse(q1.exchange.auto_delete)

        q2 = Queue.from_dict('foo', **dict(defs,
                                           exchange_durable=False))
        self.assertTrue(q2.durable)
        self.assertFalse(q2.exchange.durable)

        q3 = Queue.from_dict('foo', **dict(defs,
                                           exchange_auto_delete=True))
        self.assertFalse(q3.auto_delete)
        self.assertTrue(q3.exchange.auto_delete)

        q4 = Queue.from_dict('foo', **dict(defs,
                                           queue_durable=False))
        self.assertFalse(q4.durable)
        self.assertTrue(q4.exchange.durable)

        q5 = Queue.from_dict('foo', **dict(defs,
                                           queue_auto_delete=True))
        self.assertTrue(q5.auto_delete)
        self.assertFalse(q5.exchange.auto_delete)

        self.assertEqual(Queue.from_dict('foo', **dict(defs)),
                         Queue.from_dict('foo', **dict(defs)))


class test_Publisher(Case):

    def setUp(self):
        self.connection = Connection(transport=Transport)

    def test_constructor(self):
        pub = compat.Publisher(self.connection,
                               exchange='test_Publisher_constructor',
                               routing_key='rkey')
        self.assertIsInstance(pub.backend, Channel)
        self.assertEqual(pub.exchange.name, 'test_Publisher_constructor')
        self.assertTrue(pub.exchange.durable)
        self.assertFalse(pub.exchange.auto_delete)
        self.assertEqual(pub.exchange.type, 'direct')

        pub2 = compat.Publisher(self.connection,
                                exchange='test_Publisher_constructor2',
                                routing_key='rkey',
                                auto_delete=True,
                                durable=False)
        self.assertTrue(pub2.exchange.auto_delete)
        self.assertFalse(pub2.exchange.durable)

        explicit = Exchange('test_Publisher_constructor_explicit',
                            type='topic')
        pub3 = compat.Publisher(self.connection,
                                exchange=explicit)
        self.assertEqual(pub3.exchange, explicit)

        compat.Publisher(self.connection,
                         exchange='test_Publisher_constructor3',
                         channel=self.connection.default_channel)

    def test_send(self):
        pub = compat.Publisher(self.connection,
                               exchange='test_Publisher_send',
                               routing_key='rkey')
        pub.send({'foo': 'bar'})
        self.assertIn('basic_publish', pub.backend)
        pub.close()

    def test__enter__exit__(self):
        pub = compat.Publisher(self.connection,
                               exchange='test_Publisher_send',
                               routing_key='rkey')
        x = pub.__enter__()
        self.assertIs(x, pub)
        x.__exit__()
        self.assertTrue(pub._closed)


class test_Consumer(Case):

    def setUp(self):
        self.connection = Connection(transport=Transport)

    @patch('kombu.compat._iterconsume')
    def test_iterconsume_calls__iterconsume(self, it, n='test_iterconsume'):
        c = compat.Consumer(self.connection, queue=n, exchange=n)
        c.iterconsume(limit=10, no_ack=True)
        it.assert_called_with(c.connection, c, True, 10)

    def test_constructor(self, n='test_Consumer_constructor'):
        c = compat.Consumer(self.connection, queue=n, exchange=n,
                            routing_key='rkey')
        self.assertIsInstance(c.backend, Channel)
        q = c.queues[0]
        self.assertTrue(q.durable)
        self.assertTrue(q.exchange.durable)
        self.assertFalse(q.auto_delete)
        self.assertFalse(q.exchange.auto_delete)
        self.assertEqual(q.name, n)
        self.assertEqual(q.exchange.name, n)

        c2 = compat.Consumer(self.connection, queue=n + '2',
                             exchange=n + '2',
                             routing_key='rkey', durable=False,
                             auto_delete=True, exclusive=True)
        q2 = c2.queues[0]
        self.assertFalse(q2.durable)
        self.assertFalse(q2.exchange.durable)
        self.assertTrue(q2.auto_delete)
        self.assertTrue(q2.exchange.auto_delete)

    def test__enter__exit__(self, n='test__enter__exit__'):
        c = compat.Consumer(self.connection, queue=n, exchange=n,
                            routing_key='rkey')
        x = c.__enter__()
        self.assertIs(x, c)
        x.__exit__()
        self.assertTrue(c._closed)

    def test_revive(self, n='test_revive'):
        c = compat.Consumer(self.connection, queue=n, exchange=n)

        with self.connection.channel() as c2:
            c.revive(c2)
            self.assertIs(c.backend, c2)

    def test__iter__(self, n='test__iter__'):
        c = compat.Consumer(self.connection, queue=n, exchange=n)
        c.iterqueue = Mock()

        c.__iter__()
        c.iterqueue.assert_called_with(infinite=True)

    def test_iter(self, n='test_iterqueue'):
        c = compat.Consumer(self.connection, queue=n, exchange=n,
                            routing_key='rkey')
        c.close()

    def test_process_next(self, n='test_process_next'):
        c = compat.Consumer(self.connection, queue=n, exchange=n,
                            routing_key='rkey')
        with self.assertRaises(NotImplementedError):
            c.process_next()
        c.close()

    def test_iterconsume(self, n='test_iterconsume'):
        c = compat.Consumer(self.connection, queue=n, exchange=n,
                            routing_key='rkey')
        c.close()

    def test_discard_all(self, n='test_discard_all'):
        c = compat.Consumer(self.connection, queue=n, exchange=n,
                            routing_key='rkey')
        c.discard_all()
        self.assertIn('queue_purge', c.backend)

    def test_fetch(self, n='test_fetch'):
        c = compat.Consumer(self.connection, queue=n, exchange=n,
                            routing_key='rkey')
        self.assertIsNone(c.fetch())
        self.assertIsNone(c.fetch(no_ack=True))
        self.assertIn('basic_get', c.backend)

        callback_called = [False]

        def receive(payload, message):
            callback_called[0] = True

        c.backend.to_deliver.append('42')
        payload = c.fetch().payload
        self.assertEqual(payload, '42')
        c.backend.to_deliver.append('46')
        c.register_callback(receive)
        self.assertEqual(c.fetch(enable_callbacks=True).payload, '46')
        self.assertTrue(callback_called[0])

    def test_discard_all_filterfunc_not_supported(self, n='xjf21j21'):
        c = compat.Consumer(self.connection, queue=n, exchange=n,
                            routing_key='rkey')
        with self.assertRaises(NotImplementedError):
            c.discard_all(filterfunc=lambda x: x)
        c.close()

    def test_wait(self, n='test_wait'):

        class C(compat.Consumer):

            def iterconsume(self, limit=None):
                for i in range(limit):
                    yield i

        c = C(self.connection,
              queue=n, exchange=n, routing_key='rkey')
        self.assertEqual(c.wait(10), list(range(10)))
        c.close()

    def test_iterqueue(self, n='test_iterqueue'):
        i = [0]

        class C(compat.Consumer):

            def fetch(self, limit=None):
                z = i[0]
                i[0] += 1
                return z

        c = C(self.connection,
              queue=n, exchange=n, routing_key='rkey')
        self.assertEqual(list(c.iterqueue(limit=10)), list(range(10)))
        c.close()


class test_ConsumerSet(Case):

    def setUp(self):
        self.connection = Connection(transport=Transport)

    def test_providing_channel(self):
        chan = Mock(name='channel')
        cs = compat.ConsumerSet(self.connection, channel=chan)
        self.assertTrue(cs._provided_channel)
        self.assertIs(cs.backend, chan)

        cs.cancel = Mock(name='cancel')
        cs.close()
        self.assertFalse(chan.close.called)

    @patch('kombu.compat._iterconsume')
    def test_iterconsume(self, _iterconsume, n='test_iterconsume'):
        c = compat.Consumer(self.connection, queue=n, exchange=n)
        cs = compat.ConsumerSet(self.connection, consumers=[c])
        cs.iterconsume(limit=10, no_ack=True)
        _iterconsume.assert_called_with(c.connection, cs, True, 10)

    def test_revive(self, n='test_revive'):
        c = compat.Consumer(self.connection, queue=n, exchange=n)
        cs = compat.ConsumerSet(self.connection, consumers=[c])

        with self.connection.channel() as c2:
            cs.revive(c2)
            self.assertIs(cs.backend, c2)

    def test_constructor(self, prefix='0daf8h21'):
        dcon = {'%s.xyx' % prefix: {'exchange': '%s.xyx' % prefix,
                                    'routing_key': 'xyx'},
                '%s.xyz' % prefix: {'exchange': '%s.xyz' % prefix,
                                    'routing_key': 'xyz'}}
        consumers = [compat.Consumer(self.connection, queue=prefix + str(i),
                                     exchange=prefix + str(i))
                     for i in range(3)]
        c = compat.ConsumerSet(self.connection, consumers=consumers)
        c2 = compat.ConsumerSet(self.connection, from_dict=dcon)

        self.assertEqual(len(c.queues), 3)
        self.assertEqual(len(c2.queues), 2)

        c.add_consumer(compat.Consumer(self.connection,
                                       queue=prefix + 'xaxxxa',
                                       exchange=prefix + 'xaxxxa'))
        self.assertEqual(len(c.queues), 4)
        for cq in c.queues:
            self.assertIs(cq.channel, c.channel)

        c2.add_consumer_from_dict({
            '%s.xxx' % prefix: {
                'exchange': '%s.xxx' % prefix,
                'routing_key': 'xxx',
            },
        })
        self.assertEqual(len(c2.queues), 3)
        for c2q in c2.queues:
            self.assertIs(c2q.channel, c2.channel)

        c.discard_all()
        self.assertEqual(c.channel.called.count('queue_purge'), 4)
        c.consume()

        c.close()
        c2.close()
        self.assertIn('basic_cancel', c.channel)
        self.assertIn('close', c.channel)
        self.assertIn('close', c2.channel)

########NEW FILE########
__FILENAME__ = test_compression
from __future__ import absolute_import

import sys

from kombu import compression

from .case import Case, SkipTest, mask_modules


class test_compression(Case):

    def setUp(self):
        try:
            import bz2  # noqa
        except ImportError:
            self.has_bzip2 = False
        else:
            self.has_bzip2 = True

    @mask_modules('bz2')
    def test_no_bz2(self):
        c = sys.modules.pop('kombu.compression')
        try:
            import kombu.compression
            self.assertFalse(hasattr(kombu.compression, 'bz2'))
        finally:
            if c is not None:
                sys.modules['kombu.compression'] = c

    def test_encoders(self):
        encoders = compression.encoders()
        self.assertIn('application/x-gzip', encoders)
        if self.has_bzip2:
            self.assertIn('application/x-bz2', encoders)

    def test_compress__decompress__zlib(self):
        text = b'The Quick Brown Fox Jumps Over The Lazy Dog'
        c, ctype = compression.compress(text, 'zlib')
        self.assertNotEqual(text, c)
        d = compression.decompress(c, ctype)
        self.assertEqual(d, text)

    def test_compress__decompress__bzip2(self):
        if not self.has_bzip2:
            raise SkipTest('bzip2 not available')
        text = b'The Brown Quick Fox Over The Lazy Dog Jumps'
        c, ctype = compression.compress(text, 'bzip2')
        self.assertNotEqual(text, c)
        d = compression.decompress(c, ctype)
        self.assertEqual(d, text)

########NEW FILE########
__FILENAME__ = test_connection
from __future__ import absolute_import

import pickle
import socket

from copy import copy

from kombu import Connection, Consumer, Producer, parse_url
from kombu.connection import Resource
from kombu.five import items, range

from .case import Case, Mock, SkipTest, patch, skip_if_not_module
from .mocks import Transport


class test_connection_utils(Case):

    def setUp(self):
        self.url = 'amqp://user:pass@localhost:5672/my/vhost'
        self.nopass = 'amqp://user:**@localhost:5672/my/vhost'
        self.expected = {
            'transport': 'amqp',
            'userid': 'user',
            'password': 'pass',
            'hostname': 'localhost',
            'port': 5672,
            'virtual_host': 'my/vhost',
        }

    def test_parse_url(self):
        result = parse_url(self.url)
        self.assertDictEqual(result, self.expected)

    def test_parse_generated_as_uri(self):
        conn = Connection(self.url)
        info = conn.info()
        for k, v in self.expected.items():
            self.assertEqual(info[k], v)
        # by default almost the same- no password
        self.assertEqual(conn.as_uri(), self.nopass)
        self.assertEqual(conn.as_uri(include_password=True), self.url)

    def test_as_uri_when_prefix(self):
        conn = Connection('memory://')
        conn.uri_prefix = 'foo'
        self.assertTrue(conn.as_uri().startswith('foo+memory://'))

    @skip_if_not_module('pymongo')
    def test_as_uri_when_mongodb(self):
        x = Connection('mongodb://localhost')
        self.assertTrue(x.as_uri())

    def test_bogus_scheme(self):
        with self.assertRaises(KeyError):
            Connection('bogus://localhost:7421').transport

    def assert_info(self, conn, **fields):
        info = conn.info()
        for field, expected in items(fields):
            self.assertEqual(info[field], expected)

    def test_rabbitmq_example_urls(self):
        # see Appendix A of http://www.rabbitmq.com/uri-spec.html

        self.assert_info(
            Connection('amqp://user:pass@host:10000/vhost'),
            userid='user', password='pass', hostname='host',
            port=10000, virtual_host='vhost',
        )

        self.assert_info(
            Connection('amqp://user%61:%61pass@ho%61st:10000/v%2fhost'),
            userid='usera', password='apass', hostname='hoast',
            port=10000, virtual_host='v/host',
        )

        self.assert_info(
            Connection('amqp://'),
            userid='guest', password='guest', hostname='localhost',
            port=5672, virtual_host='/',
        )

        self.assert_info(
            Connection('amqp://:@/'),
            userid='guest', password='guest', hostname='localhost',
            port=5672, virtual_host='/',
        )

        self.assert_info(
            Connection('amqp://user@/'),
            userid='user', password='guest', hostname='localhost',
            port=5672, virtual_host='/',
        )

        self.assert_info(
            Connection('amqp://user:pass@/'),
            userid='user', password='pass', hostname='localhost',
            port=5672, virtual_host='/',
        )

        self.assert_info(
            Connection('amqp://host'),
            userid='guest', password='guest', hostname='host',
            port=5672, virtual_host='/',
        )

        self.assert_info(
            Connection('amqp://:10000'),
            userid='guest', password='guest', hostname='localhost',
            port=10000, virtual_host='/',
        )

        self.assert_info(
            Connection('amqp:///vhost'),
            userid='guest', password='guest', hostname='localhost',
            port=5672, virtual_host='vhost',
        )

        self.assert_info(
            Connection('amqp://host/'),
            userid='guest', password='guest', hostname='host',
            port=5672, virtual_host='/',
        )

        self.assert_info(
            Connection('amqp://host/%2f'),
            userid='guest', password='guest', hostname='host',
            port=5672, virtual_host='/',
        )

    def test_url_IPV6(self):
        raise SkipTest("urllib can't parse ipv6 urls")

        self.assert_info(
            Connection('amqp://[::1]'),
            userid='guest', password='guest', hostname='[::1]',
            port=5672, virtual_host='/',
        )


class test_Connection(Case):

    def setUp(self):
        self.conn = Connection(port=5672, transport=Transport)

    def test_establish_connection(self):
        conn = self.conn
        conn.connect()
        self.assertTrue(conn.connection.connected)
        self.assertEqual(conn.host, 'localhost:5672')
        channel = conn.channel()
        self.assertTrue(channel.open)
        self.assertEqual(conn.drain_events(), 'event')
        _connection = conn.connection
        conn.close()
        self.assertFalse(_connection.connected)
        self.assertIsInstance(conn.transport, Transport)

    def test_multiple_urls(self):
        conn1 = Connection('amqp://foo;amqp://bar')
        self.assertEqual(conn1.hostname, 'foo')
        self.assertListEqual(conn1.alt, ['amqp://foo', 'amqp://bar'])

        conn2 = Connection(['amqp://foo', 'amqp://bar'])
        self.assertEqual(conn2.hostname, 'foo')
        self.assertListEqual(conn2.alt, ['amqp://foo', 'amqp://bar'])

    def test_collect(self):
        connection = Connection('memory://')
        trans = connection._transport = Mock(name='transport')
        _collect = trans._collect = Mock(name='transport._collect')
        _close = connection._close = Mock(name='connection._close')
        connection.declared_entities = Mock(name='decl_entities')
        uconn = connection._connection = Mock(name='_connection')
        connection.collect()

        self.assertFalse(_close.called)
        _collect.assert_called_with(uconn)
        connection.declared_entities.clear.assert_called_with()
        self.assertIsNone(trans.client)
        self.assertIsNone(connection._transport)
        self.assertIsNone(connection._connection)

    def test_collect_no_transport(self):
        connection = Connection('memory://')
        connection._transport = None
        connection._close = Mock()
        connection.collect()
        connection._close.assert_called_with()

        connection._close.side_effect = socket.timeout()
        connection.collect()

    def test_collect_transport_gone(self):
        connection = Connection('memory://')
        uconn = connection._connection = Mock(name='conn._conn')
        trans = connection._transport = Mock(name='transport')
        collect = trans._collect = Mock(name='transport._collect')

        def se(conn):
            connection._transport = None
        collect.side_effect = se

        connection.collect()
        collect.assert_called_with(uconn)
        self.assertIsNone(connection._transport)

    def test_uri_passthrough(self):
        transport = Mock(name='transport')
        with patch('kombu.connection.get_transport_cls') as gtc:
            gtc.return_value = transport
            transport.can_parse_url = True
            with patch('kombu.connection.parse_url') as parse_url:
                c = Connection('foo+mysql://some_host')
                self.assertEqual(c.transport_cls, 'foo')
                self.assertFalse(parse_url.called)
                self.assertEqual(c.hostname, 'mysql://some_host')
                self.assertTrue(c.as_uri().startswith('foo+'))
            with patch('kombu.connection.parse_url') as parse_url:
                c = Connection('mysql://some_host', transport='foo')
                self.assertEqual(c.transport_cls, 'foo')
                self.assertFalse(parse_url.called)
                self.assertEqual(c.hostname, 'mysql://some_host')
        c = Connection('pyamqp+sqlite://some_host')
        self.assertTrue(c.as_uri().startswith('pyamqp+'))

    def test_default_ensure_callback(self):
        with patch('kombu.connection.logger') as logger:
            c = Connection(transport=Mock)
            c._default_ensure_callback(KeyError(), 3)
            self.assertTrue(logger.error.called)

    def test_ensure_connection_on_error(self):
        c = Connection('amqp://A;amqp://B')
        with patch('kombu.connection.retry_over_time') as rot:
            c.ensure_connection()
            self.assertTrue(rot.called)

            args = rot.call_args[0]
            cb = args[4]
            intervals = iter([1, 2, 3, 4, 5])
            self.assertEqual(cb(KeyError(), intervals, 0), 0)
            self.assertEqual(cb(KeyError(), intervals, 1), 1)
            self.assertEqual(cb(KeyError(), intervals, 2), 0)
            self.assertEqual(cb(KeyError(), intervals, 3), 2)
            self.assertEqual(cb(KeyError(), intervals, 4), 0)
            self.assertEqual(cb(KeyError(), intervals, 5), 3)
            self.assertEqual(cb(KeyError(), intervals, 6), 0)
            self.assertEqual(cb(KeyError(), intervals, 7), 4)

            errback = Mock()
            c.ensure_connection(errback=errback)
            args = rot.call_args[0]
            cb = args[4]
            self.assertEqual(cb(KeyError(), intervals, 0), 0)
            self.assertTrue(errback.called)

    def test_supports_heartbeats(self):
        c = Connection(transport=Mock)
        c.transport.supports_heartbeats = False
        self.assertFalse(c.supports_heartbeats)

    def test_is_evented(self):
        c = Connection(transport=Mock)
        c.transport.supports_ev = False
        self.assertFalse(c.is_evented)

    def test_register_with_event_loop(self):
        c = Connection(transport=Mock)
        loop = Mock(name='loop')
        c.register_with_event_loop(loop)
        c.transport.register_with_event_loop.assert_called_with(
            c.connection, loop,
        )

    def test_manager(self):
        c = Connection(transport=Mock)
        self.assertIs(c.manager, c.transport.manager)

    def test_copy(self):
        c = Connection('amqp://example.com')
        self.assertEqual(copy(c).info(), c.info())

    def test_copy_multiples(self):
        c = Connection('amqp://A.example.com;amqp://B.example.com')
        self.assertTrue(c.alt)
        d = copy(c)
        self.assertEqual(d.alt, c.alt)

    def test_switch(self):
        c = Connection('amqp://foo')
        c._closed = True
        c.switch('redis://example.com//3')
        self.assertFalse(c._closed)
        self.assertEqual(c.hostname, 'example.com')
        self.assertEqual(c.transport_cls, 'redis')
        self.assertEqual(c.virtual_host, '/3')

    def test_maybe_switch_next(self):
        c = Connection('amqp://foo;redis://example.com//3')
        c.maybe_switch_next()
        self.assertFalse(c._closed)
        self.assertEqual(c.hostname, 'example.com')
        self.assertEqual(c.transport_cls, 'redis')
        self.assertEqual(c.virtual_host, '/3')

    def test_maybe_switch_next_no_cycle(self):
        c = Connection('amqp://foo')
        c.maybe_switch_next()
        self.assertFalse(c._closed)
        self.assertEqual(c.hostname, 'foo')
        self.assertIn(c.transport_cls, ('librabbitmq', 'pyamqp', 'amqp'))

    def test_heartbeat_check(self):
        c = Connection(transport=Transport)
        c.transport.heartbeat_check = Mock()
        c.heartbeat_check(3)
        c.transport.heartbeat_check.assert_called_with(c.connection, rate=3)

    def test_completes_cycle_no_cycle(self):
        c = Connection('amqp://')
        self.assertTrue(c.completes_cycle(0))
        self.assertTrue(c.completes_cycle(1))

    def test_completes_cycle(self):
        c = Connection('amqp://a;amqp://b;amqp://c')
        self.assertFalse(c.completes_cycle(0))
        self.assertFalse(c.completes_cycle(1))
        self.assertTrue(c.completes_cycle(2))

    def test__enter____exit__(self):
        conn = self.conn
        context = conn.__enter__()
        self.assertIs(context, conn)
        conn.connect()
        self.assertTrue(conn.connection.connected)
        conn.__exit__()
        self.assertIsNone(conn.connection)
        conn.close()    # again

    def test_close_survives_connerror(self):

        class _CustomError(Exception):
            pass

        class MyTransport(Transport):
            connection_errors = (_CustomError, )

            def close_connection(self, connection):
                raise _CustomError('foo')

        conn = Connection(transport=MyTransport)
        conn.connect()
        conn.close()
        self.assertTrue(conn._closed)

    def test_close_when_default_channel(self):
        conn = self.conn
        conn._default_channel = Mock()
        conn._close()
        conn._default_channel.close.assert_called_with()

    def test_close_when_default_channel_close_raises(self):

        class Conn(Connection):

            @property
            def connection_errors(self):
                return (KeyError, )

        conn = Conn('memory://')
        conn._default_channel = Mock()
        conn._default_channel.close.side_effect = KeyError()

        conn._close()
        conn._default_channel.close.assert_called_with()

    def test_revive_when_default_channel(self):
        conn = self.conn
        defchan = conn._default_channel = Mock()
        conn.revive(Mock())

        defchan.close.assert_called_with()
        self.assertIsNone(conn._default_channel)

    def test_ensure_connection(self):
        self.assertTrue(self.conn.ensure_connection())

    def test_ensure_success(self):
        def publish():
            return 'foobar'

        ensured = self.conn.ensure(None, publish)
        self.assertEqual(ensured(), 'foobar')

    def test_ensure_failure(self):
        class _CustomError(Exception):
            pass

        def publish():
            raise _CustomError('bar')

        ensured = self.conn.ensure(None, publish)
        with self.assertRaises(_CustomError):
            ensured()

    def test_ensure_connection_failure(self):
        class _ConnectionError(Exception):
            pass

        def publish():
            raise _ConnectionError('failed connection')

        self.conn.transport.connection_errors = (_ConnectionError,)
        ensured = self.conn.ensure(self.conn, publish)
        with self.assertRaises(_ConnectionError):
            ensured()

    def test_autoretry(self):
        myfun = Mock()
        myfun.__name__ = 'test_autoretry'

        self.conn.transport.connection_errors = (KeyError, )

        def on_call(*args, **kwargs):
            myfun.side_effect = None
            raise KeyError('foo')

        myfun.side_effect = on_call
        insured = self.conn.autoretry(myfun)
        insured()

        self.assertTrue(myfun.called)

    def test_SimpleQueue(self):
        conn = self.conn
        q = conn.SimpleQueue('foo')
        self.assertIs(q.channel, conn.default_channel)
        chan = conn.channel()
        q2 = conn.SimpleQueue('foo', channel=chan)
        self.assertIs(q2.channel, chan)

    def test_SimpleBuffer(self):
        conn = self.conn
        q = conn.SimpleBuffer('foo')
        self.assertIs(q.channel, conn.default_channel)
        chan = conn.channel()
        q2 = conn.SimpleBuffer('foo', channel=chan)
        self.assertIs(q2.channel, chan)

    def test_Producer(self):
        conn = self.conn
        self.assertIsInstance(conn.Producer(), Producer)
        self.assertIsInstance(conn.Producer(conn.default_channel), Producer)

    def test_Consumer(self):
        conn = self.conn
        self.assertIsInstance(conn.Consumer(queues=[]), Consumer)
        self.assertIsInstance(conn.Consumer(queues=[],
                              channel=conn.default_channel), Consumer)

    def test__repr__(self):
        self.assertTrue(repr(self.conn))

    def test__reduce__(self):
        x = pickle.loads(pickle.dumps(self.conn))
        self.assertDictEqual(x.info(), self.conn.info())

    def test_channel_errors(self):

        class MyTransport(Transport):
            channel_errors = (KeyError, ValueError)

        conn = Connection(transport=MyTransport)
        self.assertTupleEqual(conn.channel_errors, (KeyError, ValueError))

    def test_connection_errors(self):

        class MyTransport(Transport):
            connection_errors = (KeyError, ValueError)

        conn = Connection(transport=MyTransport)
        self.assertTupleEqual(conn.connection_errors, (KeyError, ValueError))


class test_Connection_with_transport_options(Case):

    transport_options = {'pool_recycler': 3600, 'echo': True}

    def setUp(self):
        self.conn = Connection(port=5672, transport=Transport,
                               transport_options=self.transport_options)

    def test_establish_connection(self):
        conn = self.conn
        self.assertEqual(conn.transport_options, self.transport_options)


class xResource(Resource):

    def setup(self):
        pass


class ResourceCase(Case):
    abstract = True

    def create_resource(self, limit, preload):
        raise NotImplementedError('subclass responsibility')

    def assertState(self, P, avail, dirty):
        self.assertEqual(P._resource.qsize(), avail)
        self.assertEqual(len(P._dirty), dirty)

    def test_setup(self):
        if self.abstract:
            with self.assertRaises(NotImplementedError):
                Resource()

    def test_acquire__release(self):
        if self.abstract:
            return
        P = self.create_resource(10, 0)
        self.assertState(P, 10, 0)
        chans = [P.acquire() for _ in range(10)]
        self.assertState(P, 0, 10)
        with self.assertRaises(P.LimitExceeded):
            P.acquire()
        chans.pop().release()
        self.assertState(P, 1, 9)
        [chan.release() for chan in chans]
        self.assertState(P, 10, 0)

    def test_acquire_prepare_raises(self):
        if self.abstract:
            return
        P = self.create_resource(10, 0)

        self.assertEqual(len(P._resource.queue), 10)
        P.prepare = Mock()
        P.prepare.side_effect = IOError()
        with self.assertRaises(IOError):
            P.acquire(block=True)
        self.assertEqual(len(P._resource.queue), 10)

    def test_acquire_no_limit(self):
        if self.abstract:
            return
        P = self.create_resource(None, 0)
        P.acquire().release()

    def test_replace_when_limit(self):
        if self.abstract:
            return
        P = self.create_resource(10, 0)
        r = P.acquire()
        P._dirty = Mock()
        P.close_resource = Mock()

        P.replace(r)
        P._dirty.discard.assert_called_with(r)
        P.close_resource.assert_called_with(r)

    def test_replace_no_limit(self):
        if self.abstract:
            return
        P = self.create_resource(None, 0)
        r = P.acquire()
        P._dirty = Mock()
        P.close_resource = Mock()

        P.replace(r)
        self.assertFalse(P._dirty.discard.called)
        P.close_resource.assert_called_with(r)

    def test_interface_prepare(self):
        if not self.abstract:
            return
        x = xResource()
        self.assertEqual(x.prepare(10), 10)

    def test_force_close_all_handles_AttributeError(self):
        if self.abstract:
            return
        P = self.create_resource(10, 10)
        cr = P.collect_resource = Mock()
        cr.side_effect = AttributeError('x')

        P.acquire()
        self.assertTrue(P._dirty)

        P.force_close_all()

    def test_force_close_all_no_mutex(self):
        if self.abstract:
            return
        P = self.create_resource(10, 10)
        P.close_resource = Mock()

        m = P._resource = Mock()
        m.mutex = None
        m.queue.pop.side_effect = IndexError

        P.force_close_all()

    def test_add_when_empty(self):
        if self.abstract:
            return
        P = self.create_resource(None, None)
        P._resource.queue[:] = []
        self.assertFalse(P._resource.queue)
        P._add_when_empty()
        self.assertTrue(P._resource.queue)


class test_ConnectionPool(ResourceCase):
    abstract = False

    def create_resource(self, limit, preload):
        return Connection(port=5672, transport=Transport).Pool(limit, preload)

    def test_setup(self):
        P = self.create_resource(10, 2)
        q = P._resource.queue
        self.assertIsNotNone(q[0]._connection)
        self.assertIsNotNone(q[1]._connection)
        self.assertIsNone(q[2]()._connection)

    def test_acquire_raises_evaluated(self):
        P = self.create_resource(1, 0)
        # evaluate the connection first
        r = P.acquire()
        r.release()
        P.prepare = Mock()
        P.prepare.side_effect = MemoryError()
        P.release = Mock()
        with self.assertRaises(MemoryError):
            with P.acquire():
                assert False
        P.release.assert_called_with(r)

    def test_release_no__debug(self):
        P = self.create_resource(10, 2)
        R = Mock()
        R._debug.side_effect = AttributeError()
        P.release_resource(R)

    def test_setup_no_limit(self):
        P = self.create_resource(None, None)
        self.assertFalse(P._resource.queue)
        self.assertIsNone(P.limit)

    def test_prepare_not_callable(self):
        P = self.create_resource(None, None)
        conn = Connection('memory://')
        self.assertIs(P.prepare(conn), conn)

    def test_acquire_channel(self):
        P = self.create_resource(10, 0)
        with P.acquire_channel() as (conn, channel):
            self.assertIs(channel, conn.default_channel)


class test_ChannelPool(ResourceCase):
    abstract = False

    def create_resource(self, limit, preload):
        return Connection(port=5672, transport=Transport) \
            .ChannelPool(limit, preload)

    def test_setup(self):
        P = self.create_resource(10, 2)
        q = P._resource.queue
        self.assertTrue(q[0].basic_consume)
        self.assertTrue(q[1].basic_consume)
        with self.assertRaises(AttributeError):
            getattr(q[2], 'basic_consume')

    def test_setup_no_limit(self):
        P = self.create_resource(None, None)
        self.assertFalse(P._resource.queue)
        self.assertIsNone(P.limit)

    def test_prepare_not_callable(self):
        P = self.create_resource(10, 0)
        conn = Connection('memory://')
        chan = conn.default_channel
        self.assertIs(P.prepare(chan), chan)

########NEW FILE########
__FILENAME__ = test_entities
from __future__ import absolute_import

import pickle

from kombu import Connection, Exchange, Producer, Queue, binding
from kombu.exceptions import NotBoundError

from .case import Case, Mock, call
from .mocks import Transport


def get_conn():
    return Connection(transport=Transport)


class test_binding(Case):

    def test_constructor(self):
        x = binding(
            Exchange('foo'), 'rkey',
            arguments={'barg': 'bval'},
            unbind_arguments={'uarg': 'uval'},
        )
        self.assertEqual(x.exchange, Exchange('foo'))
        self.assertEqual(x.routing_key, 'rkey')
        self.assertDictEqual(x.arguments, {'barg': 'bval'})
        self.assertDictEqual(x.unbind_arguments, {'uarg': 'uval'})

    def test_declare(self):
        chan = get_conn().channel()
        x = binding(Exchange('foo'), 'rkey')
        x.declare(chan)
        self.assertIn('exchange_declare', chan)

    def test_declare_no_exchange(self):
        chan = get_conn().channel()
        x = binding()
        x.declare(chan)
        self.assertNotIn('exchange_declare', chan)

    def test_bind(self):
        chan = get_conn().channel()
        x = binding(Exchange('foo'))
        x.bind(Exchange('bar')(chan))
        self.assertIn('exchange_bind', chan)

    def test_unbind(self):
        chan = get_conn().channel()
        x = binding(Exchange('foo'))
        x.unbind(Exchange('bar')(chan))
        self.assertIn('exchange_unbind', chan)

    def test_repr(self):
        b = binding(Exchange('foo'), 'rkey')
        self.assertIn('foo', repr(b))
        self.assertIn('rkey', repr(b))


class test_Exchange(Case):

    def test_bound(self):
        exchange = Exchange('foo', 'direct')
        self.assertFalse(exchange.is_bound)
        self.assertIn('<unbound', repr(exchange))

        chan = get_conn().channel()
        bound = exchange.bind(chan)
        self.assertTrue(bound.is_bound)
        self.assertIs(bound.channel, chan)
        self.assertIn('bound to chan:%r' % (chan.channel_id, ),
                      repr(bound))

    def test_hash(self):
        self.assertEqual(hash(Exchange('a')), hash(Exchange('a')))
        self.assertNotEqual(hash(Exchange('a')), hash(Exchange('b')))

    def test_can_cache_declaration(self):
        self.assertTrue(Exchange('a', durable=True).can_cache_declaration)
        self.assertFalse(Exchange('a', durable=False).can_cache_declaration)

    def test_pickle(self):
        e1 = Exchange('foo', 'direct')
        e2 = pickle.loads(pickle.dumps(e1))
        self.assertEqual(e1, e2)

    def test_eq(self):
        e1 = Exchange('foo', 'direct')
        e2 = Exchange('foo', 'direct')
        self.assertEqual(e1, e2)

        e3 = Exchange('foo', 'topic')
        self.assertNotEqual(e1, e3)

        self.assertEqual(e1.__eq__(True), NotImplemented)

    def test_revive(self):
        exchange = Exchange('foo', 'direct')
        conn = get_conn()
        chan = conn.channel()

        # reviving unbound channel is a noop.
        exchange.revive(chan)
        self.assertFalse(exchange.is_bound)
        self.assertIsNone(exchange._channel)

        bound = exchange.bind(chan)
        self.assertTrue(bound.is_bound)
        self.assertIs(bound.channel, chan)

        chan2 = conn.channel()
        bound.revive(chan2)
        self.assertTrue(bound.is_bound)
        self.assertIs(bound._channel, chan2)

    def test_assert_is_bound(self):
        exchange = Exchange('foo', 'direct')
        with self.assertRaises(NotBoundError):
            exchange.declare()
        conn = get_conn()

        chan = conn.channel()
        exchange.bind(chan).declare()
        self.assertIn('exchange_declare', chan)

    def test_set_transient_delivery_mode(self):
        exc = Exchange('foo', 'direct', delivery_mode='transient')
        self.assertEqual(exc.delivery_mode, Exchange.TRANSIENT_DELIVERY_MODE)

    def test_set_passive_mode(self):
        exc = Exchange('foo', 'direct', passive=True)
        self.assertTrue(exc.passive)

    def test_set_persistent_delivery_mode(self):
        exc = Exchange('foo', 'direct', delivery_mode='persistent')
        self.assertEqual(exc.delivery_mode, Exchange.PERSISTENT_DELIVERY_MODE)

    def test_bind_at_instantiation(self):
        self.assertTrue(Exchange('foo', channel=get_conn().channel()).is_bound)

    def test_create_message(self):
        chan = get_conn().channel()
        Exchange('foo', channel=chan).Message({'foo': 'bar'})
        self.assertIn('prepare_message', chan)

    def test_publish(self):
        chan = get_conn().channel()
        Exchange('foo', channel=chan).publish('the quick brown fox')
        self.assertIn('basic_publish', chan)

    def test_delete(self):
        chan = get_conn().channel()
        Exchange('foo', channel=chan).delete()
        self.assertIn('exchange_delete', chan)

    def test__repr__(self):
        b = Exchange('foo', 'topic')
        self.assertIn('foo(topic)', repr(b))
        self.assertIn('Exchange', repr(b))

    def test_bind_to(self):
        chan = get_conn().channel()
        foo = Exchange('foo', 'topic')
        bar = Exchange('bar', 'topic')
        foo(chan).bind_to(bar)
        self.assertIn('exchange_bind', chan)

    def test_bind_to_by_name(self):
        chan = get_conn().channel()
        foo = Exchange('foo', 'topic')
        foo(chan).bind_to('bar')
        self.assertIn('exchange_bind', chan)

    def test_unbind_from(self):
        chan = get_conn().channel()
        foo = Exchange('foo', 'topic')
        bar = Exchange('bar', 'topic')
        foo(chan).unbind_from(bar)
        self.assertIn('exchange_unbind', chan)

    def test_unbind_from_by_name(self):
        chan = get_conn().channel()
        foo = Exchange('foo', 'topic')
        foo(chan).unbind_from('bar')
        self.assertIn('exchange_unbind', chan)


class test_Queue(Case):

    def setUp(self):
        self.exchange = Exchange('foo', 'direct')

    def test_hash(self):
        self.assertEqual(hash(Queue('a')), hash(Queue('a')))
        self.assertNotEqual(hash(Queue('a')), hash(Queue('b')))

    def test_repr_with_bindings(self):
        ex = Exchange('foo')
        x = Queue('foo', bindings=[ex.binding('A'), ex.binding('B')])
        self.assertTrue(repr(x))

    def test_anonymous(self):
        chan = Mock()
        x = Queue(bindings=[binding(Exchange('foo'), 'rkey')])
        chan.queue_declare.return_value = 'generated', 0, 0
        xx = x(chan)
        xx.declare()
        self.assertEqual(xx.name, 'generated')

    def test_basic_get__accept_disallowed(self):
        conn = Connection('memory://')
        q = Queue('foo', exchange=self.exchange)
        p = Producer(conn)
        p.publish(
            {'complex': object()},
            declare=[q], exchange=self.exchange, serializer='pickle',
        )

        message = q(conn).get(no_ack=True)
        self.assertIsNotNone(message)

        with self.assertRaises(q.ContentDisallowed):
            message.decode()

    def test_basic_get__accept_allowed(self):
        conn = Connection('memory://')
        q = Queue('foo', exchange=self.exchange)
        p = Producer(conn)
        p.publish(
            {'complex': object()},
            declare=[q], exchange=self.exchange, serializer='pickle',
        )

        message = q(conn).get(accept=['pickle'], no_ack=True)
        self.assertIsNotNone(message)

        payload = message.decode()
        self.assertTrue(payload['complex'])

    def test_when_bound_but_no_exchange(self):
        q = Queue('a')
        q.exchange = None
        self.assertIsNone(q.when_bound())

    def test_declare_but_no_exchange(self):
        q = Queue('a')
        q.queue_declare = Mock()
        q.queue_bind = Mock()
        q.exchange = None

        q.declare()
        q.queue_declare.assert_called_with(False, passive=False)

    def test_bind_to_when_name(self):
        chan = Mock()
        q = Queue('a')
        q(chan).bind_to('ex')
        self.assertTrue(chan.queue_bind.called)

    def test_get_when_no_m2p(self):
        chan = Mock()
        q = Queue('a')(chan)
        chan.message_to_python = None
        self.assertTrue(q.get())

    def test_multiple_bindings(self):
        chan = Mock()
        q = Queue('mul', [
            binding(Exchange('mul1'), 'rkey1'),
            binding(Exchange('mul2'), 'rkey2'),
            binding(Exchange('mul3'), 'rkey3'),
        ])
        q(chan).declare()
        self.assertIn(
            call(
                nowait=False,
                exchange='mul1',
                auto_delete=False,
                passive=False,
                arguments=None,
                type='direct',
                durable=True,
            ),
            chan.exchange_declare.call_args_list,
        )

    def test_can_cache_declaration(self):
        self.assertTrue(Queue('a', durable=True).can_cache_declaration)
        self.assertFalse(Queue('a', durable=False).can_cache_declaration)

    def test_eq(self):
        q1 = Queue('xxx', Exchange('xxx', 'direct'), 'xxx')
        q2 = Queue('xxx', Exchange('xxx', 'direct'), 'xxx')
        self.assertEqual(q1, q2)
        self.assertEqual(q1.__eq__(True), NotImplemented)

        q3 = Queue('yyy', Exchange('xxx', 'direct'), 'xxx')
        self.assertNotEqual(q1, q3)

    def test_exclusive_implies_auto_delete(self):
        self.assertTrue(
            Queue('foo', self.exchange, exclusive=True).auto_delete,
        )

    def test_binds_at_instantiation(self):
        self.assertTrue(Queue('foo', self.exchange,
                              channel=get_conn().channel()).is_bound)

    def test_also_binds_exchange(self):
        chan = get_conn().channel()
        b = Queue('foo', self.exchange)
        self.assertFalse(b.is_bound)
        self.assertFalse(b.exchange.is_bound)
        b = b.bind(chan)
        self.assertTrue(b.is_bound)
        self.assertTrue(b.exchange.is_bound)
        self.assertIs(b.channel, b.exchange.channel)
        self.assertIsNot(b.exchange, self.exchange)

    def test_declare(self):
        chan = get_conn().channel()
        b = Queue('foo', self.exchange, 'foo', channel=chan)
        self.assertTrue(b.is_bound)
        b.declare()
        self.assertIn('exchange_declare', chan)
        self.assertIn('queue_declare', chan)
        self.assertIn('queue_bind', chan)

    def test_get(self):
        b = Queue('foo', self.exchange, 'foo', channel=get_conn().channel())
        b.get()
        self.assertIn('basic_get', b.channel)

    def test_purge(self):
        b = Queue('foo', self.exchange, 'foo', channel=get_conn().channel())
        b.purge()
        self.assertIn('queue_purge', b.channel)

    def test_consume(self):
        b = Queue('foo', self.exchange, 'foo', channel=get_conn().channel())
        b.consume('fifafo', None)
        self.assertIn('basic_consume', b.channel)

    def test_cancel(self):
        b = Queue('foo', self.exchange, 'foo', channel=get_conn().channel())
        b.cancel('fifafo')
        self.assertIn('basic_cancel', b.channel)

    def test_delete(self):
        b = Queue('foo', self.exchange, 'foo', channel=get_conn().channel())
        b.delete()
        self.assertIn('queue_delete', b.channel)

    def test_queue_unbind(self):
        b = Queue('foo', self.exchange, 'foo', channel=get_conn().channel())
        b.queue_unbind()
        self.assertIn('queue_unbind', b.channel)

    def test_as_dict(self):
        q = Queue('foo', self.exchange, 'rk')
        d = q.as_dict(recurse=True)
        self.assertEqual(d['exchange']['name'], self.exchange.name)

    def test__repr__(self):
        b = Queue('foo', self.exchange, 'foo')
        self.assertIn('foo', repr(b))
        self.assertIn('Queue', repr(b))

########NEW FILE########
__FILENAME__ = test_log
from __future__ import absolute_import

import logging
import sys

from kombu.log import (
    NullHandler,
    get_logger,
    get_loglevel,
    safeify_format,
    Log,
    LogMixin,
    setup_logging,
)

from .case import Case, Mock, patch


class test_NullHandler(Case):

    def test_emit(self):
        h = NullHandler()
        h.emit('record')


class test_get_logger(Case):

    def test_when_string(self):
        l = get_logger('foo')

        self.assertIs(l, logging.getLogger('foo'))
        h1 = l.handlers[0]
        self.assertIsInstance(h1, NullHandler)

    def test_when_logger(self):
        l = get_logger(logging.getLogger('foo'))
        h1 = l.handlers[0]
        self.assertIsInstance(h1, NullHandler)

    def test_with_custom_handler(self):
        l = logging.getLogger('bar')
        handler = NullHandler()
        l.addHandler(handler)

        l = get_logger('bar')
        self.assertIs(l.handlers[0], handler)

    def test_get_loglevel(self):
        self.assertEqual(get_loglevel('DEBUG'), logging.DEBUG)
        self.assertEqual(get_loglevel('ERROR'), logging.ERROR)
        self.assertEqual(get_loglevel(logging.INFO), logging.INFO)


class test_safe_format(Case):

    def test_formatting(self):
        fmt = 'The %r jumped %x over the %s'
        args = ['frog', 'foo', 'elephant']

        res = list(safeify_format(fmt, args))
        self.assertListEqual(res, ["'frog'", 'foo', 'elephant'])


class test_LogMixin(Case):

    def setUp(self):
        self.log = Log('Log', Mock())
        self.logger = self.log.logger

    def test_debug(self):
        self.log.debug('debug')
        self.logger.log.assert_called_with(logging.DEBUG, 'Log - debug')

    def test_info(self):
        self.log.info('info')
        self.logger.log.assert_called_with(logging.INFO, 'Log - info')

    def test_warning(self):
        self.log.warn('warning')
        self.logger.log.assert_called_with(logging.WARN, 'Log - warning')

    def test_error(self):
        self.log.error('error', exc_info='exc')
        self.logger.log.assert_called_with(
            logging.ERROR, 'Log - error', exc_info='exc',
        )

    def test_critical(self):
        self.log.critical('crit', exc_info='exc')
        self.logger.log.assert_called_with(
            logging.CRITICAL, 'Log - crit', exc_info='exc',
        )

    def test_error_when_DISABLE_TRACEBACKS(self):
        from kombu import log
        log.DISABLE_TRACEBACKS = True
        try:
            self.log.error('error')
            self.logger.log.assert_called_with(logging.ERROR, 'Log - error')
        finally:
            log.DISABLE_TRACEBACKS = False

    def test_get_loglevel(self):
        self.assertEqual(self.log.get_loglevel('DEBUG'), logging.DEBUG)
        self.assertEqual(self.log.get_loglevel('ERROR'), logging.ERROR)
        self.assertEqual(self.log.get_loglevel(logging.INFO), logging.INFO)

    def test_is_enabled_for(self):
        self.logger.isEnabledFor.return_value = True
        self.assertTrue(self.log.is_enabled_for('DEBUG'))
        self.logger.isEnabledFor.assert_called_with(logging.DEBUG)

    def test_LogMixin_get_logger(self):
        self.assertIs(LogMixin().get_logger(),
                      logging.getLogger('LogMixin'))

    def test_Log_get_logger(self):
        self.assertIs(Log('test_Log').get_logger(),
                      logging.getLogger('test_Log'))

    def test_log_when_not_enabled(self):
        self.logger.isEnabledFor.return_value = False
        self.log.debug('debug')
        self.assertFalse(self.logger.log.called)

    def test_log_with_format(self):
        self.log.debug('Host %r removed', 'example.com')
        self.logger.log.assert_called_with(
            logging.DEBUG, 'Log - Host %s removed', "'example.com'",
        )


class test_setup_logging(Case):

    @patch('logging.getLogger')
    def test_set_up_default_values(self, getLogger):
        logger = logging.getLogger.return_value = Mock()
        logger.handlers = []
        setup_logging()

        logger.setLevel.assert_called_with(logging.ERROR)
        self.assertTrue(logger.addHandler.called)
        ah_args, _ = logger.addHandler.call_args
        handler = ah_args[0]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertIs(handler.stream, sys.__stderr__)

    @patch('logging.getLogger')
    @patch('kombu.log.WatchedFileHandler')
    def test_setup_custom_values(self, getLogger, WatchedFileHandler):
        logger = logging.getLogger.return_value = Mock()
        logger.handlers = []
        setup_logging(loglevel=logging.DEBUG, logfile='/var/logfile')

        logger.setLevel.assert_called_with(logging.DEBUG)
        self.assertTrue(logger.addHandler.called)
        self.assertTrue(WatchedFileHandler.called)

    @patch('logging.getLogger')
    def test_logger_already_setup(self, getLogger):
        logger = logging.getLogger.return_value = Mock()
        logger.handlers = [Mock()]
        setup_logging()

        self.assertFalse(logger.setLevel.called)

########NEW FILE########
__FILENAME__ = test_messaging
from __future__ import absolute_import, unicode_literals

import pickle

from collections import defaultdict

from kombu import Connection, Consumer, Producer, Exchange, Queue
from kombu.exceptions import MessageStateError
from kombu.utils import ChannelPromise
from kombu.utils import json

from .case import Case, Mock, patch
from .mocks import Transport


class test_Producer(Case):

    def setUp(self):
        self.exchange = Exchange('foo', 'direct')
        self.connection = Connection(transport=Transport)
        self.connection.connect()
        self.assertTrue(self.connection.connection.connected)
        self.assertFalse(self.exchange.is_bound)

    def test_repr(self):
        p = Producer(self.connection)
        self.assertTrue(repr(p))

    def test_pickle(self):
        chan = Mock()
        producer = Producer(chan, serializer='pickle')
        p2 = pickle.loads(pickle.dumps(producer))
        self.assertEqual(p2.serializer, producer.serializer)

    def test_no_channel(self):
        p = Producer(None)
        self.assertFalse(p._channel)

    @patch('kombu.common.maybe_declare')
    def test_maybe_declare(self, maybe_declare):
        p = self.connection.Producer()
        q = Queue('foo')
        p.maybe_declare(q)
        maybe_declare.assert_called_with(q, p.channel, False)

    @patch('kombu.common.maybe_declare')
    def test_maybe_declare_when_entity_false(self, maybe_declare):
        p = self.connection.Producer()
        p.maybe_declare(None)
        self.assertFalse(maybe_declare.called)

    def test_auto_declare(self):
        channel = self.connection.channel()
        p = Producer(channel, self.exchange, auto_declare=True)
        self.assertIsNot(p.exchange, self.exchange,
                         'creates Exchange clone at bind')
        self.assertTrue(p.exchange.is_bound)
        self.assertIn('exchange_declare', channel,
                      'auto_declare declares exchange')

    def test_manual_declare(self):
        channel = self.connection.channel()
        p = Producer(channel, self.exchange, auto_declare=False)
        self.assertTrue(p.exchange.is_bound)
        self.assertNotIn('exchange_declare', channel,
                         'auto_declare=False does not declare exchange')
        p.declare()
        self.assertIn('exchange_declare', channel,
                      'p.declare() declares exchange')

    def test_prepare(self):
        message = {'the quick brown fox': 'jumps over the lazy dog'}
        channel = self.connection.channel()
        p = Producer(channel, self.exchange, serializer='json')
        m, ctype, cencoding = p._prepare(message, headers={})
        self.assertDictEqual(message, json.loads(m))
        self.assertEqual(ctype, 'application/json')
        self.assertEqual(cencoding, 'utf-8')

    def test_prepare_compression(self):
        message = {'the quick brown fox': 'jumps over the lazy dog'}
        channel = self.connection.channel()
        p = Producer(channel, self.exchange, serializer='json')
        headers = {}
        m, ctype, cencoding = p._prepare(message, compression='zlib',
                                         headers=headers)
        self.assertEqual(ctype, 'application/json')
        self.assertEqual(cencoding, 'utf-8')
        self.assertEqual(headers['compression'], 'application/x-gzip')
        import zlib
        self.assertEqual(
            json.loads(zlib.decompress(m).decode('utf-8')),
            message,
        )

    def test_prepare_custom_content_type(self):
        message = 'the quick brown fox'.encode('utf-8')
        channel = self.connection.channel()
        p = Producer(channel, self.exchange, serializer='json')
        m, ctype, cencoding = p._prepare(message, content_type='custom')
        self.assertEqual(m, message)
        self.assertEqual(ctype, 'custom')
        self.assertEqual(cencoding, 'binary')
        m, ctype, cencoding = p._prepare(message, content_type='custom',
                                         content_encoding='alien')
        self.assertEqual(m, message)
        self.assertEqual(ctype, 'custom')
        self.assertEqual(cencoding, 'alien')

    def test_prepare_is_already_unicode(self):
        message = 'the quick brown fox'
        channel = self.connection.channel()
        p = Producer(channel, self.exchange, serializer='json')
        m, ctype, cencoding = p._prepare(message, content_type='text/plain')
        self.assertEqual(m, message.encode('utf-8'))
        self.assertEqual(ctype, 'text/plain')
        self.assertEqual(cencoding, 'utf-8')
        m, ctype, cencoding = p._prepare(message, content_type='text/plain',
                                         content_encoding='utf-8')
        self.assertEqual(m, message.encode('utf-8'))
        self.assertEqual(ctype, 'text/plain')
        self.assertEqual(cencoding, 'utf-8')

    def test_publish_with_Exchange_instance(self):
        p = self.connection.Producer()
        p.channel = Mock()
        p.publish('hello', exchange=Exchange('foo'), delivery_mode='transient')
        self.assertEqual(
            p._channel.basic_publish.call_args[1]['exchange'], 'foo',
        )

    def test_set_on_return(self):
        chan = Mock()
        chan.events = defaultdict(Mock)
        p = Producer(ChannelPromise(lambda: chan), on_return='on_return')
        p.channel
        chan.events['basic_return'].add.assert_called_with('on_return')

    def test_publish_retry_calls_ensure(self):
        p = Producer(Mock())
        p._connection = Mock()
        ensure = p.connection.ensure = Mock()
        p.publish('foo', exchange='foo', retry=True)
        self.assertTrue(ensure.called)

    def test_publish_retry_with_declare(self):
        p = self.connection.Producer()
        p.maybe_declare = Mock()
        p.connection.ensure = Mock()
        ex = Exchange('foo')
        p._publish('hello', 0, '', '', {}, {}, 'rk', 0, 0, ex, declare=[ex])
        p.maybe_declare.assert_called_with(ex)

    def test_revive_when_channel_is_connection(self):
        p = self.connection.Producer()
        p.exchange = Mock()
        new_conn = Connection('memory://')
        defchan = new_conn.default_channel
        p.revive(new_conn)

        self.assertIs(p.channel, defchan)
        p.exchange.revive.assert_called_with(defchan)

    def test_enter_exit(self):
        p = self.connection.Producer()
        p.release = Mock()

        self.assertIs(p.__enter__(), p)
        p.__exit__()
        p.release.assert_called_with()

    def test_connection_property_handles_AttributeError(self):
        p = self.connection.Producer()
        p.channel = object()
        p.__connection__ = None
        self.assertIsNone(p.connection)

    def test_publish(self):
        channel = self.connection.channel()
        p = Producer(channel, self.exchange, serializer='json')
        message = {'the quick brown fox': 'jumps over the lazy dog'}
        ret = p.publish(message, routing_key='process')
        self.assertIn('prepare_message', channel)
        self.assertIn('basic_publish', channel)

        m, exc, rkey = ret
        self.assertDictEqual(message, json.loads(m['body']))
        self.assertDictContainsSubset({'content_type': 'application/json',
                                       'content_encoding': 'utf-8',
                                       'priority': 0}, m)
        self.assertDictContainsSubset({'delivery_mode': 2}, m['properties'])
        self.assertEqual(exc, p.exchange.name)
        self.assertEqual(rkey, 'process')

    def test_no_exchange(self):
        chan = self.connection.channel()
        p = Producer(chan)
        self.assertFalse(p.exchange.name)

    def test_revive(self):
        chan = self.connection.channel()
        p = Producer(chan)
        chan2 = self.connection.channel()
        p.revive(chan2)
        self.assertIs(p.channel, chan2)
        self.assertIs(p.exchange.channel, chan2)

    def test_on_return(self):
        chan = self.connection.channel()

        def on_return(exception, exchange, routing_key, message):
            pass

        p = Producer(chan, on_return=on_return)
        self.assertTrue(on_return in chan.events['basic_return'])
        self.assertTrue(p.on_return)


class test_Consumer(Case):

    def setUp(self):
        self.connection = Connection(transport=Transport)
        self.connection.connect()
        self.assertTrue(self.connection.connection.connected)
        self.exchange = Exchange('foo', 'direct')

    def test_accept(self):
        a = Consumer(self.connection)
        self.assertIsNone(a.accept)
        b = Consumer(self.connection, accept=['json', 'pickle'])
        self.assertSetEqual(
            b.accept,
            {'application/json', 'application/x-python-serialize'},
        )
        c = Consumer(self.connection, accept=b.accept)
        self.assertSetEqual(b.accept, c.accept)

    def test_enter_exit_cancel_raises(self):
        c = Consumer(self.connection)
        c.cancel = Mock(name='Consumer.cancel')
        c.cancel.side_effect = KeyError('foo')
        with c:
            pass
        c.cancel.assert_called_with()

    def test_receive_callback_accept(self):
        message = Mock(name='Message')
        message.errors = []
        callback = Mock(name='on_message')
        c = Consumer(self.connection, accept=['json'], on_message=callback)
        c.on_decode_error = None
        c.channel = Mock(name='channel')
        c.channel.message_to_python = None

        c._receive_callback(message)
        callback.assert_called_with(message)
        self.assertSetEqual(message.accept, c.accept)

    def test_accept__content_disallowed(self):
        conn = Connection('memory://')
        q = Queue('foo', exchange=self.exchange)
        p = conn.Producer()
        p.publish(
            {'complex': object()},
            declare=[q], exchange=self.exchange, serializer='pickle',
        )

        callback = Mock(name='callback')
        with conn.Consumer(queues=[q], callbacks=[callback]) as consumer:
            with self.assertRaises(consumer.ContentDisallowed):
                conn.drain_events(timeout=1)
        self.assertFalse(callback.called)

    def test_accept__content_allowed(self):
        conn = Connection('memory://')
        q = Queue('foo', exchange=self.exchange)
        p = conn.Producer()
        p.publish(
            {'complex': object()},
            declare=[q], exchange=self.exchange, serializer='pickle',
        )

        callback = Mock(name='callback')
        with conn.Consumer(queues=[q], accept=['pickle'],
                           callbacks=[callback]):
            conn.drain_events(timeout=1)
        self.assertTrue(callback.called)
        body, message = callback.call_args[0]
        self.assertTrue(body['complex'])

    def test_set_no_channel(self):
        c = Consumer(None)
        self.assertIsNone(c.channel)
        c.revive(Mock())
        self.assertTrue(c.channel)

    def test_set_no_ack(self):
        channel = self.connection.channel()
        queue = Queue('qname', self.exchange, 'rkey')
        consumer = Consumer(channel, queue, auto_declare=True, no_ack=True)
        self.assertTrue(consumer.no_ack)

    def test_add_queue_when_auto_declare(self):
        consumer = self.connection.Consumer(auto_declare=True)
        q = Mock()
        q.return_value = q
        consumer.add_queue(q)
        self.assertIn(q, consumer.queues)
        q.declare.assert_called_with()

    def test_add_queue_when_not_auto_declare(self):
        consumer = self.connection.Consumer(auto_declare=False)
        q = Mock()
        q.return_value = q
        consumer.add_queue(q)
        self.assertIn(q, consumer.queues)
        self.assertFalse(q.declare.call_count)

    def test_consume_without_queues_returns(self):
        consumer = self.connection.Consumer()
        consumer.queues[:] = []
        self.assertIsNone(consumer.consume())

    def test_consuming_from(self):
        consumer = self.connection.Consumer()
        consumer.queues[:] = [Queue('a'), Queue('b'), Queue('d')]
        consumer._active_tags = {'a': 1, 'b': 2}

        self.assertFalse(consumer.consuming_from(Queue('c')))
        self.assertFalse(consumer.consuming_from('c'))
        self.assertFalse(consumer.consuming_from(Queue('d')))
        self.assertFalse(consumer.consuming_from('d'))
        self.assertTrue(consumer.consuming_from(Queue('a')))
        self.assertTrue(consumer.consuming_from(Queue('b')))
        self.assertTrue(consumer.consuming_from('b'))

    def test_receive_callback_without_m2p(self):
        channel = self.connection.channel()
        c = channel.Consumer()
        m2p = getattr(channel, 'message_to_python')
        channel.message_to_python = None
        try:
            message = Mock()
            message.errors = []
            message.decode.return_value = 'Hello'
            recv = c.receive = Mock()
            c._receive_callback(message)
            recv.assert_called_with('Hello', message)
        finally:
            channel.message_to_python = m2p

    def test_set_callbacks(self):
        channel = self.connection.channel()
        queue = Queue('qname', self.exchange, 'rkey')
        callbacks = [lambda x, y: x,
                     lambda x, y: x]
        consumer = Consumer(channel, queue, auto_declare=True,
                            callbacks=callbacks)
        self.assertEqual(consumer.callbacks, callbacks)

    def test_auto_declare(self):
        channel = self.connection.channel()
        queue = Queue('qname', self.exchange, 'rkey')
        consumer = Consumer(channel, queue, auto_declare=True)
        consumer.consume()
        consumer.consume()  # twice is a noop
        self.assertIsNot(consumer.queues[0], queue)
        self.assertTrue(consumer.queues[0].is_bound)
        self.assertTrue(consumer.queues[0].exchange.is_bound)
        self.assertIsNot(consumer.queues[0].exchange, self.exchange)

        for meth in ('exchange_declare',
                     'queue_declare',
                     'queue_bind',
                     'basic_consume'):
            self.assertIn(meth, channel)
        self.assertEqual(channel.called.count('basic_consume'), 1)
        self.assertTrue(consumer._active_tags)

        consumer.cancel_by_queue(queue.name)
        consumer.cancel_by_queue(queue.name)
        self.assertFalse(consumer._active_tags)

    def test_manual_declare(self):
        channel = self.connection.channel()
        queue = Queue('qname', self.exchange, 'rkey')
        consumer = Consumer(channel, queue, auto_declare=False)
        self.assertIsNot(consumer.queues[0], queue)
        self.assertTrue(consumer.queues[0].is_bound)
        self.assertTrue(consumer.queues[0].exchange.is_bound)
        self.assertIsNot(consumer.queues[0].exchange, self.exchange)

        for meth in ('exchange_declare',
                     'queue_declare',
                     'basic_consume'):
            self.assertNotIn(meth, channel)

        consumer.declare()
        for meth in ('exchange_declare',
                     'queue_declare',
                     'queue_bind'):
            self.assertIn(meth, channel)
        self.assertNotIn('basic_consume', channel)

        consumer.consume()
        self.assertIn('basic_consume', channel)

    def test_consume__cancel(self):
        channel = self.connection.channel()
        queue = Queue('qname', self.exchange, 'rkey')
        consumer = Consumer(channel, queue, auto_declare=True)
        consumer.consume()
        consumer.cancel()
        self.assertIn('basic_cancel', channel)
        self.assertFalse(consumer._active_tags)

    def test___enter____exit__(self):
        channel = self.connection.channel()
        queue = Queue('qname', self.exchange, 'rkey')
        consumer = Consumer(channel, queue, auto_declare=True)
        context = consumer.__enter__()
        self.assertIs(context, consumer)
        self.assertTrue(consumer._active_tags)
        res = consumer.__exit__(None, None, None)
        self.assertFalse(res)
        self.assertIn('basic_cancel', channel)
        self.assertFalse(consumer._active_tags)

    def test_flow(self):
        channel = self.connection.channel()
        queue = Queue('qname', self.exchange, 'rkey')
        consumer = Consumer(channel, queue, auto_declare=True)
        consumer.flow(False)
        self.assertIn('flow', channel)

    def test_qos(self):
        channel = self.connection.channel()
        queue = Queue('qname', self.exchange, 'rkey')
        consumer = Consumer(channel, queue, auto_declare=True)
        consumer.qos(30, 10, False)
        self.assertIn('basic_qos', channel)

    def test_purge(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        b2 = Queue('qname2', self.exchange, 'rkey')
        b3 = Queue('qname3', self.exchange, 'rkey')
        b4 = Queue('qname4', self.exchange, 'rkey')
        consumer = Consumer(channel, [b1, b2, b3, b4], auto_declare=True)
        consumer.purge()
        self.assertEqual(channel.called.count('queue_purge'), 4)

    def test_multiple_queues(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        b2 = Queue('qname2', self.exchange, 'rkey')
        b3 = Queue('qname3', self.exchange, 'rkey')
        b4 = Queue('qname4', self.exchange, 'rkey')
        consumer = Consumer(channel, [b1, b2, b3, b4])
        consumer.consume()
        self.assertEqual(channel.called.count('exchange_declare'), 4)
        self.assertEqual(channel.called.count('queue_declare'), 4)
        self.assertEqual(channel.called.count('queue_bind'), 4)
        self.assertEqual(channel.called.count('basic_consume'), 4)
        self.assertEqual(len(consumer._active_tags), 4)
        consumer.cancel()
        self.assertEqual(channel.called.count('basic_cancel'), 4)
        self.assertFalse(len(consumer._active_tags))

    def test_receive_callback(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        consumer = Consumer(channel, [b1])
        received = []

        def callback(message_data, message):
            received.append(message_data)
            message.ack()
            message.payload     # trigger cache

        consumer.register_callback(callback)
        consumer._receive_callback({'foo': 'bar'})

        self.assertIn('basic_ack', channel)
        self.assertIn('message_to_python', channel)
        self.assertEqual(received[0], {'foo': 'bar'})

    def test_basic_ack_twice(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        consumer = Consumer(channel, [b1])

        def callback(message_data, message):
            message.ack()
            message.ack()

        consumer.register_callback(callback)
        with self.assertRaises(MessageStateError):
            consumer._receive_callback({'foo': 'bar'})

    def test_basic_reject(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        consumer = Consumer(channel, [b1])

        def callback(message_data, message):
            message.reject()

        consumer.register_callback(callback)
        consumer._receive_callback({'foo': 'bar'})
        self.assertIn('basic_reject', channel)

    def test_basic_reject_twice(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        consumer = Consumer(channel, [b1])

        def callback(message_data, message):
            message.reject()
            message.reject()

        consumer.register_callback(callback)
        with self.assertRaises(MessageStateError):
            consumer._receive_callback({'foo': 'bar'})
        self.assertIn('basic_reject', channel)

    def test_basic_reject__requeue(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        consumer = Consumer(channel, [b1])

        def callback(message_data, message):
            message.requeue()

        consumer.register_callback(callback)
        consumer._receive_callback({'foo': 'bar'})
        self.assertIn('basic_reject:requeue', channel)

    def test_basic_reject__requeue_twice(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        consumer = Consumer(channel, [b1])

        def callback(message_data, message):
            message.requeue()
            message.requeue()

        consumer.register_callback(callback)
        with self.assertRaises(MessageStateError):
            consumer._receive_callback({'foo': 'bar'})
        self.assertIn('basic_reject:requeue', channel)

    def test_receive_without_callbacks_raises(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        consumer = Consumer(channel, [b1])
        with self.assertRaises(NotImplementedError):
            consumer.receive(1, 2)

    def test_decode_error(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        consumer = Consumer(channel, [b1])
        consumer.channel.throw_decode_error = True

        with self.assertRaises(ValueError):
            consumer._receive_callback({'foo': 'bar'})

    def test_on_decode_error_callback(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        thrown = []

        def on_decode_error(msg, exc):
            thrown.append((msg.body, exc))

        consumer = Consumer(channel, [b1], on_decode_error=on_decode_error)
        consumer.channel.throw_decode_error = True
        consumer._receive_callback({'foo': 'bar'})

        self.assertTrue(thrown)
        m, exc = thrown[0]
        self.assertEqual(json.loads(m), {'foo': 'bar'})
        self.assertIsInstance(exc, ValueError)

    def test_recover(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        consumer = Consumer(channel, [b1])
        consumer.recover()
        self.assertIn('basic_recover', channel)

    def test_revive(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        consumer = Consumer(channel, [b1])
        channel2 = self.connection.channel()
        consumer.revive(channel2)
        self.assertIs(consumer.channel, channel2)
        self.assertIs(consumer.queues[0].channel, channel2)
        self.assertIs(consumer.queues[0].exchange.channel, channel2)

    def test__repr__(self):
        channel = self.connection.channel()
        b1 = Queue('qname1', self.exchange, 'rkey')
        self.assertTrue(repr(Consumer(channel, [b1])))

    def test_connection_property_handles_AttributeError(self):
        p = self.connection.Consumer()
        p.channel = object()
        self.assertIsNone(p.connection)

########NEW FILE########
__FILENAME__ = test_mixins
from __future__ import absolute_import, unicode_literals

import socket

from kombu.mixins import ConsumerMixin

from .case import Case, Mock, ContextMock, patch


def Message(body, content_type='text/plain', content_encoding='utf-8'):
    m = Mock(name='Message')
    m.body = body
    m.content_type = content_type
    m.content_encoding = content_encoding
    return m


class Cons(ConsumerMixin):

    def __init__(self, consumers):
        self.calls = Mock(name='ConsumerMixin')
        self.calls.get_consumers.return_value = consumers
        self.get_consumers = self.calls.get_consumers
        self.on_connection_revived = self.calls.on_connection_revived
        self.on_consume_ready = self.calls.on_consume_ready
        self.on_consume_end = self.calls.on_consume_end
        self.on_iteration = self.calls.on_iteration
        self.on_decode_error = self.calls.on_decode_error
        self.on_connection_error = self.calls.on_connection_error
        self.extra_context = ContextMock(name='extra_context')
        self.extra_context.return_value = self.extra_context


class test_ConsumerMixin(Case):

    def _context(self):
        Acons = ContextMock(name='consumerA')
        Bcons = ContextMock(name='consumerB')
        c = Cons([Acons, Bcons])
        _conn = c.connection = ContextMock(name='connection')
        est = c.establish_connection = Mock(name='est_connection')
        est.return_value = _conn
        return c, Acons, Bcons

    def test_consume(self):
        c, Acons, Bcons = self._context()
        c.should_stop = False
        it = c.consume(no_ack=True)
        next(it)
        Acons.__enter__.assert_called_with()
        Bcons.__enter__.assert_called_with()
        c.extra_context.__enter__.assert_called_with()
        self.assertTrue(c.on_consume_ready.called)
        c.on_iteration.assert_called_with()
        c.connection.drain_events.assert_called_with(timeout=1)
        next(it)
        next(it)
        next(it)
        c.should_stop = True
        with self.assertRaises(StopIteration):
            next(it)

    def test_consume_drain_raises_socket_error(self):
        c, Acons, Bcons = self._context()
        c.should_stop = False
        it = c.consume(no_ack=True)
        c.connection.drain_events.side_effect = socket.error
        with self.assertRaises(socket.error):
            next(it)

        def se2(*args, **kwargs):
            c.should_stop = True
            raise socket.error()
        c.connection.drain_events.side_effect = se2
        it = c.consume(no_ack=True)
        with self.assertRaises(StopIteration):
            next(it)

    def test_consume_drain_raises_socket_timeout(self):
        c, Acons, Bcons = self._context()
        c.should_stop = False
        it = c.consume(no_ack=True, timeout=1)

        def se(*args, **kwargs):
            c.should_stop = True
            raise socket.timeout()
        c.connection.drain_events.side_effect = se
        with self.assertRaises(socket.error):
            next(it)

    def test_Consumer_context(self):
        c, Acons, Bcons = self._context()

        with c.Consumer() as (conn, channel, consumer):
            self.assertIs(conn, c.connection)
            self.assertIs(channel, conn.default_channel)
            c.on_connection_revived.assert_called_with()
            self.assertTrue(c.get_consumers.called)
            cls = c.get_consumers.call_args[0][0]

            subcons = cls()
            self.assertIs(subcons.on_decode_error, c.on_decode_error)
            self.assertIs(subcons.channel, conn.default_channel)
            Acons.__enter__.assert_called_with()
            Bcons.__enter__.assert_called_with()
        c.on_consume_end.assert_called_with(conn, channel)


class test_ConsumerMixin_interface(Case):

    def setUp(self):
        self.c = ConsumerMixin()

    def test_get_consumers(self):
        with self.assertRaises(NotImplementedError):
            self.c.get_consumers(Mock(), Mock())

    def test_on_connection_revived(self):
        self.assertIsNone(self.c.on_connection_revived())

    def test_on_consume_ready(self):
        self.assertIsNone(self.c.on_consume_ready(
            Mock(), Mock(), [],
        ))

    def test_on_consume_end(self):
        self.assertIsNone(self.c.on_consume_end(Mock(), Mock()))

    def test_on_iteration(self):
        self.assertIsNone(self.c.on_iteration())

    def test_on_decode_error(self):
        message = Message('foo')
        with patch('kombu.mixins.error') as error:
            self.c.on_decode_error(message, KeyError('foo'))
            self.assertTrue(error.called)
            message.ack.assert_called_with()

    def test_on_connection_error(self):
        with patch('kombu.mixins.warn') as warn:
            self.c.on_connection_error(KeyError('foo'), 3)
            self.assertTrue(warn.called)

    def test_extra_context(self):
        with self.c.extra_context(Mock(), Mock()):
            pass

    def test_restart_limit(self):
        self.assertTrue(self.c.restart_limit)

    def test_connection_errors(self):
        conn = Mock(name='connection')
        self.c.connection = conn
        conn.connection_errors = (KeyError, )
        self.assertTupleEqual(self.c.connection_errors, conn.connection_errors)
        conn.channel_errors = (ValueError, )
        self.assertTupleEqual(self.c.channel_errors, conn.channel_errors)

    def test__consume_from(self):
        a = ContextMock(name='A')
        b = ContextMock(name='B')
        a.__enter__ = Mock(name='A.__enter__')
        b.__enter__ = Mock(name='B.__enter__')
        with self.c._consume_from(a, b):
            pass
        a.__enter__.assert_called_with()
        b.__enter__.assert_called_with()

    def test_establish_connection(self):
        conn = ContextMock(name='connection')
        conn.clone.return_value = conn
        self.c.connection = conn
        self.c.connect_max_retries = 3

        with self.c.establish_connection() as conn:
            self.assertTrue(conn)
        conn.ensure_connection.assert_called_with(
            self.c.on_connection_error, 3,
        )

    def test_maybe_conn_error(self):
        conn = ContextMock(name='connection')
        conn.connection_errors = (KeyError, )
        conn.channel_errors = ()

        self.c.connection = conn

        def raises():
            raise KeyError('foo')
        self.c.maybe_conn_error(raises)

    def test_run(self):
        conn = ContextMock(name='connection')
        self.c.connection = conn
        conn.connection_errors = (KeyError, )
        conn.channel_errors = ()
        consume = self.c.consume = Mock(name='c.consume')

        def se(*args, **kwargs):
            self.c.should_stop = True
            return [1]
        self.c.should_stop = False
        consume.side_effect = se
        self.c.run()

    def test_run_restart_rate_limited(self):
        conn = ContextMock(name='connection')
        self.c.connection = conn
        conn.connection_errors = (KeyError, )
        conn.channel_errors = ()
        consume = self.c.consume = Mock(name='c.consume')
        with patch('kombu.mixins.sleep') as sleep:
            counter = [0]

            def se(*args, **kwargs):
                if counter[0] >= 1:
                    self.c.should_stop = True
                counter[0] += 1
                return counter
            self.c.should_stop = False
            consume.side_effect = se
            self.c.run()
            self.assertTrue(sleep.called)

    def test_run_raises(self):
        conn = ContextMock(name='connection')
        self.c.connection = conn
        conn.connection_errors = (KeyError, )
        conn.channel_errors = ()
        consume = self.c.consume = Mock(name='c.consume')

        with patch('kombu.mixins.warn') as warn:
            def se_raises(*args, **kwargs):
                self.c.should_stop = True
                raise KeyError('foo')
            self.c.should_stop = False
            consume.side_effect = se_raises
            self.c.run()
            self.assertTrue(warn.called)

########NEW FILE########
__FILENAME__ = test_pidbox
from __future__ import absolute_import

import socket
import warnings

from kombu import Connection
from kombu import pidbox
from kombu.exceptions import ContentDisallowed, InconsistencyError
from kombu.utils import uuid

from .case import Case, Mock, patch


class test_Mailbox(Case):

    def _handler(self, state):
        return self.stats['var']

    def setUp(self):

        class Mailbox(pidbox.Mailbox):

            def _collect(self, *args, **kwargs):
                return 'COLLECTED'

        self.mailbox = Mailbox('test_pidbox')
        self.connection = Connection(transport='memory')
        self.state = {'var': 1}
        self.handlers = {'mymethod': self._handler}
        self.bound = self.mailbox(self.connection)
        self.default_chan = self.connection.channel()
        self.node = self.bound.Node(
            'test_pidbox',
            state=self.state, handlers=self.handlers,
            channel=self.default_chan,
        )

    def test_publish_reply_ignores_InconsistencyError(self):
        mailbox = pidbox.Mailbox('test_reply__collect')(self.connection)
        with patch('kombu.pidbox.Producer') as Producer:
            producer = Producer.return_value = Mock(name='producer')
            producer.publish.side_effect = InconsistencyError()
            mailbox._publish_reply(
                {'foo': 'bar'}, mailbox.reply_exchange, mailbox.oid, 'foo',
            )
            self.assertTrue(producer.publish.called)

    def test_reply__collect(self):
        mailbox = pidbox.Mailbox('test_reply__collect')(self.connection)
        exchange = mailbox.reply_exchange.name
        channel = self.connection.channel()
        mailbox.reply_queue(channel).declare()

        ticket = uuid()
        mailbox._publish_reply({'foo': 'bar'}, exchange, mailbox.oid, ticket)
        _callback_called = [False]

        def callback(body):
            _callback_called[0] = True

        reply = mailbox._collect(ticket, limit=1,
                                 callback=callback, channel=channel)
        self.assertEqual(reply, [{'foo': 'bar'}])
        self.assertTrue(_callback_called[0])

        ticket = uuid()
        mailbox._publish_reply({'biz': 'boz'}, exchange, mailbox.oid, ticket)
        reply = mailbox._collect(ticket, limit=1, channel=channel)
        self.assertEqual(reply, [{'biz': 'boz'}])

        mailbox._publish_reply({'foo': 'BAM'}, exchange, mailbox.oid, 'doom',
                               serializer='pickle')
        with self.assertRaises(ContentDisallowed):
            reply = mailbox._collect('doom', limit=1, channel=channel)
        mailbox._publish_reply(
            {'foo': 'BAMBAM'}, exchange, mailbox.oid, 'doom',
            serializer='pickle',
        )
        reply = mailbox._collect('doom', limit=1, channel=channel,
                                 accept=['pickle'])
        self.assertEqual(reply[0]['foo'], 'BAMBAM')

        de = mailbox.connection.drain_events = Mock()
        de.side_effect = socket.timeout
        mailbox._collect(ticket, limit=1, channel=channel)

    def test_constructor(self):
        self.assertIsNone(self.mailbox.connection)
        self.assertTrue(self.mailbox.exchange.name)
        self.assertTrue(self.mailbox.reply_exchange.name)

    def test_bound(self):
        bound = self.mailbox(self.connection)
        self.assertIs(bound.connection, self.connection)

    def test_Node(self):
        self.assertTrue(self.node.hostname)
        self.assertTrue(self.node.state)
        self.assertIs(self.node.mailbox, self.bound)
        self.assertTrue(self.handlers)

        # No initial handlers
        node2 = self.bound.Node('test_pidbox2', state=self.state)
        self.assertDictEqual(node2.handlers, {})

    def test_Node_consumer(self):
        consumer1 = self.node.Consumer()
        self.assertIs(consumer1.channel, self.default_chan)
        self.assertTrue(consumer1.no_ack)

        chan2 = self.connection.channel()
        consumer2 = self.node.Consumer(channel=chan2, no_ack=False)
        self.assertIs(consumer2.channel, chan2)
        self.assertFalse(consumer2.no_ack)

    def test_Node_consumer_multiple_listeners(self):
        warnings.resetwarnings()
        consumer = self.node.Consumer()
        q = consumer.queues[0]
        with warnings.catch_warnings(record=True) as log:
            q.on_declared('foo', 1, 1)
            self.assertTrue(log)
            self.assertIn('already using this', log[0].message.args[0])

        with warnings.catch_warnings(record=True) as log:
            q.on_declared('foo', 1, 0)
            self.assertFalse(log)

    def test_handler(self):
        node = self.bound.Node('test_handler', state=self.state)

        @node.handler
        def my_handler_name(state):
            return 42

        self.assertIn('my_handler_name', node.handlers)

    def test_dispatch(self):
        node = self.bound.Node('test_dispatch', state=self.state)

        @node.handler
        def my_handler_name(state, x=None, y=None):
            return x + y

        self.assertEqual(node.dispatch('my_handler_name',
                                       arguments={'x': 10, 'y': 10}), 20)

    def test_dispatch_raising_SystemExit(self):
        node = self.bound.Node('test_dispatch_raising_SystemExit',
                               state=self.state)

        @node.handler
        def my_handler_name(state):
            raise SystemExit

        with self.assertRaises(SystemExit):
            node.dispatch('my_handler_name')

    def test_dispatch_raising(self):
        node = self.bound.Node('test_dispatch_raising', state=self.state)

        @node.handler
        def my_handler_name(state):
            raise KeyError('foo')

        res = node.dispatch('my_handler_name')
        self.assertIn('error', res)
        self.assertIn('KeyError', res['error'])

    def test_dispatch_replies(self):
        _replied = [False]

        def reply(data, **options):
            _replied[0] = True

        node = self.bound.Node('test_dispatch', state=self.state)
        node.reply = reply

        @node.handler
        def my_handler_name(state, x=None, y=None):
            return x + y

        node.dispatch('my_handler_name',
                      arguments={'x': 10, 'y': 10},
                      reply_to={'exchange': 'foo', 'routing_key': 'bar'})
        self.assertTrue(_replied[0])

    def test_reply(self):
        _replied = [(None, None, None)]

        def publish_reply(data, exchange, routing_key, ticket, **kwargs):
            _replied[0] = (data, exchange, routing_key, ticket)

        mailbox = self.mailbox(self.connection)
        mailbox._publish_reply = publish_reply
        node = mailbox.Node('test_reply')

        @node.handler
        def my_handler_name(state):
            return 42

        node.dispatch('my_handler_name',
                      reply_to={'exchange': 'exchange',
                                'routing_key': 'rkey'},
                      ticket='TICKET')
        data, exchange, routing_key, ticket = _replied[0]
        self.assertEqual(data, {'test_reply': 42})
        self.assertEqual(exchange, 'exchange')
        self.assertEqual(routing_key, 'rkey')
        self.assertEqual(ticket, 'TICKET')

    def test_handle_message(self):
        node = self.bound.Node('test_dispatch_from_message')

        @node.handler
        def my_handler_name(state, x=None, y=None):
            return x * y

        body = {'method': 'my_handler_name',
                'arguments': {'x': 64, 'y': 64}}

        self.assertEqual(node.handle_message(body, None), 64 * 64)

        # message not for me should not be processed.
        body['destination'] = ['some_other_node']
        self.assertIsNone(node.handle_message(body, None))

    def test_handle_message_adjusts_clock(self):
        node = self.bound.Node('test_adjusts_clock')

        @node.handler
        def my_handler_name(state):
            return 10

        body = {'method': 'my_handler_name',
                'arguments': {}}
        message = Mock(name='message')
        message.headers = {'clock': 313}
        node.adjust_clock = Mock(name='adjust_clock')
        res = node.handle_message(body, message)
        node.adjust_clock.assert_called_with(313)
        self.assertEqual(res, 10)

    def test_listen(self):
        consumer = self.node.listen()
        self.assertEqual(consumer.callbacks[0],
                         self.node.handle_message)
        self.assertEqual(consumer.channel, self.default_chan)

    def test_cast(self):
        self.bound.cast(['somenode'], 'mymethod')
        consumer = self.node.Consumer()
        self.assertIsCast(self.get_next(consumer))

    def test_abcast(self):
        self.bound.abcast('mymethod')
        consumer = self.node.Consumer()
        self.assertIsCast(self.get_next(consumer))

    def test_call_destination_must_be_sequence(self):
        with self.assertRaises(ValueError):
            self.bound.call('some_node', 'mymethod')

    def test_call(self):
        self.assertEqual(
            self.bound.call(['some_node'], 'mymethod'),
            'COLLECTED',
        )
        consumer = self.node.Consumer()
        self.assertIsCall(self.get_next(consumer))

    def test_multi_call(self):
        self.assertEqual(self.bound.multi_call('mymethod'), 'COLLECTED')
        consumer = self.node.Consumer()
        self.assertIsCall(self.get_next(consumer))

    def get_next(self, consumer):
        m = consumer.queues[0].get()
        if m:
            return m.payload

    def assertIsCast(self, message):
        self.assertTrue(message['method'])

    def assertIsCall(self, message):
        self.assertTrue(message['method'])
        self.assertTrue(message['reply_to'])

########NEW FILE########
__FILENAME__ = test_pools
from __future__ import absolute_import

from kombu import Connection, Producer
from kombu import pools
from kombu.connection import ConnectionPool
from kombu.utils import eqhash

from .case import Case, Mock


class test_ProducerPool(Case):
    Pool = pools.ProducerPool

    class MyPool(pools.ProducerPool):

        def __init__(self, *args, **kwargs):
            self.instance = Mock()
            pools.ProducerPool.__init__(self, *args, **kwargs)

        def Producer(self, connection):
            return self.instance

    def setUp(self):
        self.connections = Mock()
        self.pool = self.Pool(self.connections, limit=10)

    def test_close_resource(self):
        self.pool.close_resource(Mock(name='resource'))

    def test_releases_connection_when_Producer_raises(self):
        self.pool.Producer = Mock()
        self.pool.Producer.side_effect = IOError()
        acq = self.pool._acquire_connection = Mock()
        conn = acq.return_value = Mock()
        with self.assertRaises(IOError):
            self.pool.create_producer()
        conn.release.assert_called_with()

    def test_prepare_release_connection_on_error(self):
        pp = Mock()
        p = pp.return_value = Mock()
        p.revive.side_effect = IOError()
        acq = self.pool._acquire_connection = Mock()
        conn = acq.return_value = Mock()
        p._channel = None
        with self.assertRaises(IOError):
            self.pool.prepare(pp)
        conn.release.assert_called_with()

    def test_release_releases_connection(self):
        p = Mock()
        p.__connection__ = Mock()
        self.pool.release(p)
        p.__connection__.release.assert_called_with()
        p.__connection__ = None
        self.pool.release(p)

    def test_init(self):
        self.assertIs(self.pool.connections, self.connections)

    def test_Producer(self):
        self.assertIsInstance(self.pool.Producer(Mock()), Producer)

    def test_acquire_connection(self):
        self.pool._acquire_connection()
        self.connections.acquire.assert_called_with(block=True)

    def test_new(self):
        promise = self.pool.new()
        producer = promise()
        self.assertIsInstance(producer, Producer)
        self.connections.acquire.assert_called_with(block=True)

    def test_setup_unlimited(self):
        pool = self.Pool(self.connections, limit=None)
        pool.setup()
        self.assertFalse(pool._resource.queue)

    def test_setup(self):
        self.assertEqual(len(self.pool._resource.queue), self.pool.limit)

        first = self.pool._resource.get_nowait()
        producer = first()
        self.assertIsInstance(producer, Producer)

    def test_prepare(self):
        connection = self.connections.acquire.return_value = Mock()
        pool = self.MyPool(self.connections, limit=10)
        pool.instance._channel = None
        first = pool._resource.get_nowait()
        producer = pool.prepare(first)
        self.assertTrue(self.connections.acquire.called)
        producer.revive.assert_called_with(connection)

    def test_prepare_channel_already_created(self):
        self.connections.acquire.return_value = Mock()
        pool = self.MyPool(self.connections, limit=10)
        pool.instance._channel = Mock()
        first = pool._resource.get_nowait()
        self.connections.acquire.reset()
        producer = pool.prepare(first)
        self.assertFalse(producer.revive.called)

    def test_prepare_not_callable(self):
        x = Producer(Mock)
        self.pool.prepare(x)

    def test_release(self):
        p = Mock()
        p.channel = Mock()
        p.__connection__ = Mock()
        self.pool.release(p)
        p.__connection__.release.assert_called_with()
        self.assertIsNone(p.channel)


class test_PoolGroup(Case):
    Group = pools.PoolGroup

    class MyGroup(pools.PoolGroup):

        def create(self, resource, limit):
            return resource, limit

    def test_interface_create(self):
        g = self.Group()
        with self.assertRaises(NotImplementedError):
            g.create(Mock(), 10)

    def test_getitem_using_global_limit(self):
        pools._used[0] = False
        g = self.MyGroup(limit=pools.use_global_limit)
        res = g['foo']
        self.assertTupleEqual(res, ('foo', pools.get_limit()))
        self.assertTrue(pools._used[0])

    def test_getitem_using_custom_limit(self):
        pools._used[0] = True
        g = self.MyGroup(limit=102456)
        res = g['foo']
        self.assertTupleEqual(res, ('foo', 102456))

    def test_delitem(self):
        g = self.MyGroup()
        g['foo']
        del(g['foo'])
        self.assertNotIn('foo', g)

    def test_Connections(self):
        conn = Connection('memory://')
        p = pools.connections[conn]
        self.assertTrue(p)
        self.assertIsInstance(p, ConnectionPool)
        self.assertIs(p.connection, conn)
        self.assertEqual(p.limit, pools.get_limit())

    def test_Producers(self):
        conn = Connection('memory://')
        p = pools.producers[conn]
        self.assertTrue(p)
        self.assertIsInstance(p, pools.ProducerPool)
        self.assertIs(p.connections, pools.connections[conn])
        self.assertEqual(p.limit, p.connections.limit)
        self.assertEqual(p.limit, pools.get_limit())

    def test_all_groups(self):
        conn = Connection('memory://')
        pools.connections[conn]

        self.assertTrue(list(pools._all_pools()))

    def test_reset(self):
        pools.reset()

        class MyGroup(dict):
            clear_called = False

            def clear(self):
                self.clear_called = True

        p1 = pools.connections['foo'] = Mock()
        g1 = MyGroup()
        pools._groups.append(g1)

        pools.reset()
        p1.force_close_all.assert_called_with()
        self.assertTrue(g1.clear_called)

        p1 = pools.connections['foo'] = Mock()
        p1.force_close_all.side_effect = KeyError()
        pools.reset()

    def test_set_limit(self):
        pools.reset()
        pools.set_limit(34576)
        limit = pools.get_limit()
        self.assertEqual(limit, 34576)

        pools.connections[Connection('memory://')]
        pools.set_limit(limit + 1)
        self.assertEqual(pools.get_limit(), limit + 1)
        limit = pools.get_limit()
        with self.assertRaises(RuntimeError):
            pools.set_limit(limit - 1)
        pools.set_limit(limit - 1, force=True)
        self.assertEqual(pools.get_limit(), limit - 1)

        pools.set_limit(pools.get_limit())


class test_fun_PoolGroup(Case):

    def test_connections_behavior(self):
        c1u = 'memory://localhost:123'
        c2u = 'memory://localhost:124'
        c1 = Connection(c1u)
        c2 = Connection(c2u)
        c3 = Connection(c1u)

        assert eqhash(c1) != eqhash(c2)
        assert eqhash(c1) == eqhash(c3)

        c4 = Connection(c1u, transport_options={'confirm_publish': True})
        self.assertNotEqual(eqhash(c3), eqhash(c4))

        p1 = pools.connections[c1]
        p2 = pools.connections[c2]
        p3 = pools.connections[c3]

        self.assertIsNot(p1, p2)
        self.assertIs(p1, p3)

        r1 = p1.acquire()
        self.assertTrue(p1._dirty)
        self.assertTrue(p3._dirty)
        self.assertFalse(p2._dirty)
        r1.release()
        self.assertFalse(p1._dirty)
        self.assertFalse(p3._dirty)

########NEW FILE########
__FILENAME__ = test_serialization
#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import sys

from base64 import b64decode

from kombu.exceptions import ContentDisallowed, EncodeError, DecodeError
from kombu.five import text_t, bytes_t
from kombu.serialization import (
    registry, register, SerializerNotInstalled,
    raw_encode, register_yaml, register_msgpack,
    dumps, loads, pickle, pickle_protocol,
    unregister, register_pickle, enable_insecure_serializers,
    disable_insecure_serializers,
)
from kombu.utils.encoding import str_to_bytes

from .case import Case, call, mask_modules, patch, skip_if_not_module

# For content_encoding tests
unicode_string = 'abcdé\u8463'
unicode_string_as_utf8 = unicode_string.encode('utf-8')
latin_string = 'abcdé'
latin_string_as_latin1 = latin_string.encode('latin-1')
latin_string_as_utf8 = latin_string.encode('utf-8')


# For serialization tests
py_data = {
    'string': 'The quick brown fox jumps over the lazy dog',
    'int': 10,
    'float': 3.14159265,
    'unicode': 'Thé quick brown fox jumps over thé lazy dog',
    'list': ['george', 'jerry', 'elaine', 'cosmo'],
}

# JSON serialization tests
json_data = """\
{"int": 10, "float": 3.1415926500000002, \
"list": ["george", "jerry", "elaine", "cosmo"], \
"string": "The quick brown fox jumps over the lazy \
dog", "unicode": "Th\\u00e9 quick brown fox jumps over \
th\\u00e9 lazy dog"}\
"""

# Pickle serialization tests
pickle_data = pickle.dumps(py_data, protocol=pickle_protocol)

# YAML serialization tests
yaml_data = """\
float: 3.1415926500000002
int: 10
list: [george, jerry, elaine, cosmo]
string: The quick brown fox jumps over the lazy dog
unicode: "Th\\xE9 quick brown fox jumps over th\\xE9 lazy dog"
"""


msgpack_py_data = dict(py_data)
# Unicode chars are lost in transmit :(
msgpack_py_data['unicode'] = 'Th quick brown fox jumps over th lazy dog'
msgpack_data = b64decode(str_to_bytes("""\
haNpbnQKpWZsb2F0y0AJIftTyNTxpGxpc3SUpmdlb3JnZaVqZXJyeaZlbGFpbmWlY29zbW+mc3Rya\
W5n2gArVGhlIHF1aWNrIGJyb3duIGZveCBqdW1wcyBvdmVyIHRoZSBsYXp5IGRvZ6d1bmljb2Rl2g\
ApVGggcXVpY2sgYnJvd24gZm94IGp1bXBzIG92ZXIgdGggbGF6eSBkb2c=\
"""))


registry.register('testS', lambda s: s, lambda s: 'decoded',
                  'application/testS', 'utf-8')


class test_Serialization(Case):

    def test_disable(self):
        disabled = registry._disabled_content_types
        try:
            registry.disable('testS')
            self.assertIn('application/testS', disabled)
            disabled.clear()

            registry.disable('application/testS')
            self.assertIn('application/testS', disabled)
        finally:
            disabled.clear()

    def test_enable(self):
        registry._disabled_content_types.add('application/json')
        registry.enable('json')
        self.assertNotIn('application/json', registry._disabled_content_types)
        registry._disabled_content_types.add('application/json')
        registry.enable('application/json')
        self.assertNotIn('application/json', registry._disabled_content_types)

    def test_loads_when_disabled(self):
        disabled = registry._disabled_content_types
        try:
            registry.disable('testS')

            with self.assertRaises(SerializerNotInstalled):
                loads('xxd', 'application/testS', 'utf-8', force=False)

            ret = loads('xxd', 'application/testS', 'utf-8', force=True)
            self.assertEqual(ret, 'decoded')
        finally:
            disabled.clear()

    def test_loads_when_data_is_None(self):
        loads(None, 'application/testS', 'utf-8')

    def test_content_type_decoding(self):
        self.assertEqual(
            unicode_string,
            loads(unicode_string_as_utf8,
                  content_type='plain/text', content_encoding='utf-8'),
        )
        self.assertEqual(
            latin_string,
            loads(latin_string_as_latin1,
                  content_type='application/data', content_encoding='latin-1'),
        )

    def test_content_type_binary(self):
        self.assertIsInstance(
            loads(unicode_string_as_utf8,
                  content_type='application/data', content_encoding='binary'),
            bytes_t,
        )

        self.assertEqual(
            unicode_string_as_utf8,
            loads(unicode_string_as_utf8,
                  content_type='application/data', content_encoding='binary'),
        )

    def test_content_type_encoding(self):
        # Using the 'raw' serializer
        self.assertEqual(
            unicode_string_as_utf8,
            dumps(unicode_string, serializer='raw')[-1],
        )
        self.assertEqual(
            latin_string_as_utf8,
            dumps(latin_string, serializer='raw')[-1],
        )
        # And again w/o a specific serializer to check the
        # code where we force unicode objects into a string.
        self.assertEqual(
            unicode_string_as_utf8,
            dumps(unicode_string)[-1],
        )
        self.assertEqual(
            latin_string_as_utf8,
            dumps(latin_string)[-1],
        )

    def test_enable_insecure_serializers(self):
        with patch('kombu.serialization.registry') as registry:
            enable_insecure_serializers()
            registry.assert_has_calls([
                call.enable('pickle'), call.enable('yaml'),
                call.enable('msgpack'),
            ])
            registry.enable.side_effect = KeyError()
            enable_insecure_serializers()

        with patch('kombu.serialization.registry') as registry:
            enable_insecure_serializers(['msgpack'])
            registry.assert_has_calls([call.enable('msgpack')])

    def test_disable_insecure_serializers(self):
        with patch('kombu.serialization.registry') as registry:
            registry._decoders = ['pickle', 'yaml', 'doomsday']
            disable_insecure_serializers(allowed=['doomsday'])
            registry.disable.assert_has_calls([call('pickle'), call('yaml')])
            registry.enable.assert_has_calls([call('doomsday')])
            disable_insecure_serializers(allowed=None)
            registry.disable.assert_has_calls([
                call('pickle'), call('yaml'), call('doomsday')
            ])

    def test_reraises_EncodeError(self):
        with self.assertRaises(EncodeError):
            dumps([object()], serializer='json')

    def test_reraises_DecodeError(self):
        with self.assertRaises(DecodeError):
            loads(object(), content_type='application/json',
                  content_encoding='utf-8')

    def test_json_loads(self):
        self.assertEqual(
            py_data,
            loads(json_data,
                  content_type='application/json', content_encoding='utf-8'),
        )

    def test_json_dumps(self):
        self.assertEqual(
            loads(
                dumps(py_data, serializer='json')[-1],
                content_type='application/json',
                content_encoding='utf-8',
            ),
            loads(
                json_data,
                content_type='application/json',
                content_encoding='utf-8',
            ),
        )

    @skip_if_not_module('msgpack', (ImportError, ValueError))
    def test_msgpack_loads(self):
        register_msgpack()
        res = loads(msgpack_data,
                    content_type='application/x-msgpack',
                    content_encoding='binary')
        if sys.version_info[0] < 3:
            for k, v in res.items():
                if isinstance(v, text_t):
                    res[k] = v.encode()
                if isinstance(v, (list, tuple)):
                    res[k] = [i.encode() for i in v]
        self.assertEqual(
            msgpack_py_data,
            res,
        )

    @skip_if_not_module('msgpack', (ImportError, ValueError))
    def test_msgpack_dumps(self):
        register_msgpack()
        self.assertEqual(
            loads(
                dumps(msgpack_py_data, serializer='msgpack')[-1],
                content_type='application/x-msgpack',
                content_encoding='binary',
            ),
            loads(
                msgpack_data,
                content_type='application/x-msgpack',
                content_encoding='binary',
            ),
        )

    @skip_if_not_module('yaml')
    def test_yaml_loads(self):
        register_yaml()
        self.assertEqual(
            py_data,
            loads(yaml_data,
                  content_type='application/x-yaml',
                  content_encoding='utf-8'),
        )

    @skip_if_not_module('yaml')
    def test_yaml_dumps(self):
        register_yaml()
        self.assertEqual(
            loads(
                dumps(py_data, serializer='yaml')[-1],
                content_type='application/x-yaml',
                content_encoding='utf-8',
            ),
            loads(
                yaml_data,
                content_type='application/x-yaml',
                content_encoding='utf-8',
            ),
        )

    def test_pickle_loads(self):
        self.assertEqual(
            py_data,
            loads(pickle_data,
                  content_type='application/x-python-serialize',
                  content_encoding='binary'),
        )

    def test_pickle_dumps(self):
        self.assertEqual(
            pickle.loads(pickle_data),
            pickle.loads(dumps(py_data, serializer='pickle')[-1]),
        )

    def test_register(self):
        register(None, None, None, None)

    def test_unregister(self):
        with self.assertRaises(SerializerNotInstalled):
            unregister('nonexisting')
        dumps('foo', serializer='pickle')
        unregister('pickle')
        with self.assertRaises(SerializerNotInstalled):
            dumps('foo', serializer='pickle')
        register_pickle()

    def test_set_default_serializer_missing(self):
        with self.assertRaises(SerializerNotInstalled):
            registry._set_default_serializer('nonexisting')

    def test_dumps_missing(self):
        with self.assertRaises(SerializerNotInstalled):
            dumps('foo', serializer='nonexisting')

    def test_dumps__no_serializer(self):
        ctyp, cenc, data = dumps(str_to_bytes('foo'))
        self.assertEqual(ctyp, 'application/data')
        self.assertEqual(cenc, 'binary')

    def test_loads__trusted_content(self):
        loads('tainted', 'application/data', 'binary', accept=[])
        loads('tainted', 'application/text', 'utf-8', accept=[])

    def test_loads__not_accepted(self):
        with self.assertRaises(ContentDisallowed):
            loads('tainted', 'application/x-evil', 'binary', accept=[])
        with self.assertRaises(ContentDisallowed):
            loads('tainted', 'application/x-evil', 'binary',
                  accept=['application/x-json'])
        self.assertTrue(
            loads('tainted', 'application/x-doomsday', 'binary',
                  accept=['application/x-doomsday'])
        )

    def test_raw_encode(self):
        self.assertTupleEqual(
            raw_encode('foo'.encode('utf-8')),
            ('application/data', 'binary', 'foo'.encode('utf-8')),
        )

    @mask_modules('yaml')
    def test_register_yaml__no_yaml(self):
        register_yaml()
        with self.assertRaises(SerializerNotInstalled):
            loads('foo', 'application/x-yaml', 'utf-8')

    @mask_modules('msgpack')
    def test_register_msgpack__no_msgpack(self):
        register_msgpack()
        with self.assertRaises(SerializerNotInstalled):
            loads('foo', 'application/x-msgpack', 'utf-8')

########NEW FILE########
__FILENAME__ = test_simple
from __future__ import absolute_import

from kombu import Connection, Exchange, Queue

from .case import Case, Mock


class SimpleBase(Case):
    abstract = True

    def Queue(self, name, *args, **kwargs):
        q = name
        if not isinstance(q, Queue):
            q = self.__class__.__name__
            if name:
                q = '%s.%s' % (q, name)
        return self._Queue(q, *args, **kwargs)

    def _Queue(self, *args, **kwargs):
        raise NotImplementedError()

    def setUp(self):
        if not self.abstract:
            self.connection = Connection(transport='memory')
            with self.connection.channel() as channel:
                channel.exchange_declare('amq.direct')
            self.q = self.Queue(None, no_ack=True)

    def tearDown(self):
        if not self.abstract:
            self.q.close()
            self.connection.close()

    def test_produce__consume(self):
        if self.abstract:
            return
        q = self.Queue('test_produce__consume', no_ack=True)

        q.put({'hello': 'Simple'})

        self.assertEqual(q.get(timeout=1).payload, {'hello': 'Simple'})
        with self.assertRaises(q.Empty):
            q.get(timeout=0.1)

    def test_produce__basic_get(self):
        if self.abstract:
            return
        q = self.Queue('test_produce__basic_get', no_ack=True)
        q.put({'hello': 'SimpleSync'})
        self.assertEqual(q.get_nowait().payload, {'hello': 'SimpleSync'})
        with self.assertRaises(q.Empty):
            q.get_nowait()

        q.put({'hello': 'SimpleSync'})
        self.assertEqual(q.get(block=False).payload, {'hello': 'SimpleSync'})
        with self.assertRaises(q.Empty):
            q.get(block=False)

    def test_clear(self):
        if self.abstract:
            return
        q = self.Queue('test_clear', no_ack=True)

        for i in range(10):
            q.put({'hello': 'SimplePurge%d' % (i, )})

        self.assertEqual(q.clear(), 10)

    def test_enter_exit(self):
        if self.abstract:
            return
        q = self.Queue('test_enter_exit')
        q.close = Mock()

        self.assertIs(q.__enter__(), q)
        q.__exit__()
        q.close.assert_called_with()

    def test_qsize(self):
        if self.abstract:
            return
        q = self.Queue('test_clear', no_ack=True)

        for i in range(10):
            q.put({'hello': 'SimplePurge%d' % (i, )})

        self.assertEqual(q.qsize(), 10)
        self.assertEqual(len(q), 10)

    def test_autoclose(self):
        if self.abstract:
            return
        channel = self.connection.channel()
        q = self.Queue('test_autoclose', no_ack=True, channel=channel)
        q.close()

    def test_custom_Queue(self):
        if self.abstract:
            return
        n = self.__class__.__name__
        exchange = Exchange('%s-test.custom.Queue' % (n, ))
        queue = Queue('%s-test.custom.Queue' % (n, ),
                      exchange,
                      'my.routing.key')

        q = self.Queue(queue)
        self.assertEqual(q.consumer.queues[0], queue)
        q.close()

    def test_bool(self):
        if self.abstract:
            return
        q = self.Queue('test_nonzero')
        self.assertTrue(q)


class test_SimpleQueue(SimpleBase):
    abstract = False

    def _Queue(self, *args, **kwargs):
        return self.connection.SimpleQueue(*args, **kwargs)

    def test_is_ack(self):
        q = self.Queue('test_is_no_ack')
        self.assertFalse(q.no_ack)


class test_SimpleBuffer(SimpleBase):
    abstract = False

    def Queue(self, *args, **kwargs):
        return self.connection.SimpleBuffer(*args, **kwargs)

    def test_is_no_ack(self):
        q = self.Queue('test_is_no_ack')
        self.assertTrue(q.no_ack)

########NEW FILE########
__FILENAME__ = test_syn
from __future__ import absolute_import

import socket
import sys
import types

from kombu import syn

from kombu.tests.case import Case, patch, module_exists


class test_syn(Case):

    def test_compat(self):
        self.assertEqual(syn.blocking(lambda: 10), 10)
        syn.select_blocking_method('foo')

    def test_detect_environment(self):
        try:
            syn._environment = None
            X = syn.detect_environment()
            self.assertEqual(syn._environment, X)
            Y = syn.detect_environment()
            self.assertEqual(Y, X)
        finally:
            syn._environment = None

    @module_exists('eventlet', 'eventlet.patcher')
    def test_detect_environment_eventlet(self):
        with patch('eventlet.patcher.is_monkey_patched', create=True) as m:
            self.assertTrue(sys.modules['eventlet'])
            m.return_value = True
            env = syn._detect_environment()
            m.assert_called_with(socket)
            self.assertEqual(env, 'eventlet')

    @module_exists('gevent')
    def test_detect_environment_gevent(self):
        with patch('gevent.socket', create=True) as m:
            prev, socket.socket = socket.socket, m.socket
            try:
                self.assertTrue(sys.modules['gevent'])
                env = syn._detect_environment()
                self.assertEqual(env, 'gevent')
            finally:
                socket.socket = prev

    def test_detect_environment_no_eventlet_or_gevent(self):
        try:
            sys.modules['eventlet'] = types.ModuleType('eventlet')
            sys.modules['eventlet.patcher'] = types.ModuleType('eventlet')
            self.assertEqual(syn._detect_environment(), 'default')
        finally:
            sys.modules.pop('eventlet', None)
        syn._detect_environment()
        try:
            sys.modules['gevent'] = types.ModuleType('gevent')
            self.assertEqual(syn._detect_environment(), 'default')
        finally:
            sys.modules.pop('gevent', None)
        syn._detect_environment()

########NEW FILE########
__FILENAME__ = test_amqplib
from __future__ import absolute_import

import sys

from kombu import Connection

from kombu.tests.case import Case, SkipTest, Mock, mask_modules


class MockConnection(dict):

    def __setattr__(self, key, value):
        self[key] = value

try:
    __import__('amqplib')
except ImportError:
    amqplib = Channel = None
else:
    from kombu.transport import amqplib

    class Channel(amqplib.Channel):
        wait_returns = []

        def _x_open(self, *args, **kwargs):
            pass

        def wait(self, *args, **kwargs):
            return self.wait_returns

        def _send_method(self, *args, **kwargs):
            pass


class amqplibCase(Case):

    def setUp(self):
        if amqplib is None:
            raise SkipTest('amqplib not installed')
        self.setup()

    def setup(self):
        pass


class test_Channel(amqplibCase):

    def setup(self):
        self.conn = Mock()
        self.conn.channels = {}
        self.channel = Channel(self.conn, 0)

    def test_init(self):
        self.assertFalse(self.channel.no_ack_consumers)

    def test_prepare_message(self):
        self.assertTrue(self.channel.prepare_message(
            'foobar', 10, 'application/data', 'utf-8',
            properties={},
        ))

    def test_message_to_python(self):
        message = Mock()
        message.headers = {}
        message.properties = {}
        self.assertTrue(self.channel.message_to_python(message))

    def test_close_resolves_connection_cycle(self):
        self.assertIsNotNone(self.channel.connection)
        self.channel.close()
        self.assertIsNone(self.channel.connection)

    def test_basic_consume_registers_ack_status(self):
        self.channel.wait_returns = 'my-consumer-tag'
        self.channel.basic_consume('foo', no_ack=True)
        self.assertIn('my-consumer-tag', self.channel.no_ack_consumers)

        self.channel.wait_returns = 'other-consumer-tag'
        self.channel.basic_consume('bar', no_ack=False)
        self.assertNotIn('other-consumer-tag', self.channel.no_ack_consumers)

        self.channel.basic_cancel('my-consumer-tag')
        self.assertNotIn('my-consumer-tag', self.channel.no_ack_consumers)


class test_Transport(amqplibCase):

    def setup(self):
        self.connection = Connection('amqplib://')
        self.transport = self.connection.transport

    def test_create_channel(self):
        connection = Mock()
        self.transport.create_channel(connection)
        connection.channel.assert_called_with()

    def test_drain_events(self):
        connection = Mock()
        self.transport.drain_events(connection, timeout=10.0)
        connection.drain_events.assert_called_with(timeout=10.0)

    def test_dnspython_localhost_resolve_bug(self):

        class Conn(object):

            def __init__(self, **kwargs):
                vars(self).update(kwargs)

        self.transport.Connection = Conn
        self.transport.client.hostname = 'localhost'
        conn1 = self.transport.establish_connection()
        self.assertEqual(conn1.host, '127.0.0.1:5672')

        self.transport.client.hostname = 'example.com'
        conn2 = self.transport.establish_connection()
        self.assertEqual(conn2.host, 'example.com:5672')

    def test_close_connection(self):
        connection = Mock()
        connection.client = Mock()
        self.transport.close_connection(connection)

        self.assertIsNone(connection.client)
        connection.close.assert_called_with()

    def test_verify_connection(self):
        connection = Mock()
        connection.channels = None
        self.assertFalse(self.transport.verify_connection(connection))

        connection.channels = {1: 1, 2: 2}
        self.assertTrue(self.transport.verify_connection(connection))

    @mask_modules('ssl')
    def test_import_no_ssl(self):
        pm = sys.modules.pop('kombu.transport.amqplib')
        try:
            from kombu.transport.amqplib import SSLError
            self.assertEqual(SSLError.__module__, 'kombu.transport.amqplib')
        finally:
            if pm is not None:
                sys.modules['kombu.transport.amqplib'] = pm


class test_amqplib(amqplibCase):

    def test_default_port(self):

        class Transport(amqplib.Transport):
            Connection = MockConnection

        c = Connection(port=None, transport=Transport).connect()
        self.assertEqual(c['host'],
                         '127.0.0.1:%s' % (Transport.default_port, ))

    def test_custom_port(self):

        class Transport(amqplib.Transport):
            Connection = MockConnection

        c = Connection(port=1337, transport=Transport).connect()
        self.assertEqual(c['host'], '127.0.0.1:1337')

########NEW FILE########
__FILENAME__ = test_base
from __future__ import absolute_import

from kombu import Connection, Consumer, Exchange, Producer, Queue
from kombu.five import text_t
from kombu.message import Message
from kombu.transport.base import StdChannel, Transport, Management

from kombu.tests.case import Case, Mock


class test_StdChannel(Case):

    def setUp(self):
        self.conn = Connection('memory://')
        self.channel = self.conn.channel()
        self.channel.queues.clear()
        self.conn.connection.state.clear()

    def test_Consumer(self):
        q = Queue('foo', Exchange('foo'))
        print(self.channel.queues)
        cons = self.channel.Consumer(q)
        self.assertIsInstance(cons, Consumer)
        self.assertIs(cons.channel, self.channel)

    def test_Producer(self):
        prod = self.channel.Producer()
        self.assertIsInstance(prod, Producer)
        self.assertIs(prod.channel, self.channel)

    def test_interface_get_bindings(self):
        with self.assertRaises(NotImplementedError):
            StdChannel().get_bindings()

    def test_interface_after_reply_message_received(self):
        self.assertIsNone(
            StdChannel().after_reply_message_received(Queue('foo')),
        )


class test_Message(Case):

    def setUp(self):
        self.conn = Connection('memory://')
        self.channel = self.conn.channel()
        self.message = Message(self.channel, delivery_tag=313)

    def test_postencode(self):
        m = Message(self.channel, text_t('FOO'), postencode='ccyzz')
        with self.assertRaises(LookupError):
            m._reraise_error()
        m.ack()

    def test_ack_respects_no_ack_consumers(self):
        self.channel.no_ack_consumers = {'abc'}
        self.message.delivery_info['consumer_tag'] = 'abc'
        ack = self.channel.basic_ack = Mock()

        self.message.ack()
        self.assertNotEqual(self.message._state, 'ACK')
        self.assertFalse(ack.called)

    def test_ack_missing_consumer_tag(self):
        self.channel.no_ack_consumers = {'abc'}
        self.message.delivery_info = {}
        ack = self.channel.basic_ack = Mock()

        self.message.ack()
        ack.assert_called_with(self.message.delivery_tag)

    def test_ack_not_no_ack(self):
        self.channel.no_ack_consumers = set()
        self.message.delivery_info['consumer_tag'] = 'abc'
        ack = self.channel.basic_ack = Mock()

        self.message.ack()
        ack.assert_called_with(self.message.delivery_tag)

    def test_ack_log_error_when_no_error(self):
        ack = self.message.ack = Mock()
        self.message.ack_log_error(Mock(), KeyError)
        ack.assert_called_with()

    def test_ack_log_error_when_error(self):
        ack = self.message.ack = Mock()
        ack.side_effect = KeyError('foo')
        logger = Mock()
        self.message.ack_log_error(logger, KeyError)
        ack.assert_called_with()
        self.assertTrue(logger.critical.called)
        self.assertIn("Couldn't ack", logger.critical.call_args[0][0])

    def test_reject_log_error_when_no_error(self):
        reject = self.message.reject = Mock()
        self.message.reject_log_error(Mock(), KeyError, requeue=True)
        reject.assert_called_with(requeue=True)

    def test_reject_log_error_when_error(self):
        reject = self.message.reject = Mock()
        reject.side_effect = KeyError('foo')
        logger = Mock()
        self.message.reject_log_error(logger, KeyError)
        reject.assert_called_with(requeue=False)
        self.assertTrue(logger.critical.called)
        self.assertIn("Couldn't reject", logger.critical.call_args[0][0])


class test_interface(Case):

    def test_establish_connection(self):
        with self.assertRaises(NotImplementedError):
            Transport(None).establish_connection()

    def test_close_connection(self):
        with self.assertRaises(NotImplementedError):
            Transport(None).close_connection(None)

    def test_create_channel(self):
        with self.assertRaises(NotImplementedError):
            Transport(None).create_channel(None)

    def test_close_channel(self):
        with self.assertRaises(NotImplementedError):
            Transport(None).close_channel(None)

    def test_drain_events(self):
        with self.assertRaises(NotImplementedError):
            Transport(None).drain_events(None)

    def test_heartbeat_check(self):
        Transport(None).heartbeat_check(Mock(name='connection'))

    def test_driver_version(self):
        self.assertTrue(Transport(None).driver_version())

    def test_register_with_event_loop(self):
        Transport(None).register_with_event_loop(Mock(name='loop'))

    def test_manager(self):
        self.assertTrue(Transport(None).manager)


class test_Management(Case):

    def test_get_bindings(self):
        m = Management(Mock(name='transport'))
        with self.assertRaises(NotImplementedError):
            m.get_bindings()

########NEW FILE########
__FILENAME__ = test_filesystem
from __future__ import absolute_import

import sys
import tempfile

from kombu import Connection, Exchange, Queue, Consumer, Producer

from kombu.tests.case import Case, SkipTest


class test_FilesystemTransport(Case):

    def setUp(self):
        if sys.platform == 'win32':
            raise SkipTest('Needs win32con module')
        try:
            data_folder_in = tempfile.mkdtemp()
            data_folder_out = tempfile.mkdtemp()
        except Exception:
            raise SkipTest('filesystem transport: cannot create tempfiles')
        self.c = Connection(transport='filesystem',
                            transport_options={
                                'data_folder_in': data_folder_in,
                                'data_folder_out': data_folder_out,
                            })
        self.p = Connection(transport='filesystem',
                            transport_options={
                                'data_folder_in': data_folder_out,
                                'data_folder_out': data_folder_in,
                            })
        self.e = Exchange('test_transport_filesystem')
        self.q = Queue('test_transport_filesystem',
                       exchange=self.e,
                       routing_key='test_transport_filesystem')
        self.q2 = Queue('test_transport_filesystem2',
                        exchange=self.e,
                        routing_key='test_transport_filesystem2')

    def test_produce_consume_noack(self):
        producer = Producer(self.p.channel(), self.e)
        consumer = Consumer(self.c.channel(), self.q, no_ack=True)

        for i in range(10):
            producer.publish({'foo': i},
                             routing_key='test_transport_filesystem')

        _received = []

        def callback(message_data, message):
            _received.append(message)

        consumer.register_callback(callback)
        consumer.consume()

        while 1:
            if len(_received) == 10:
                break
            self.c.drain_events()

        self.assertEqual(len(_received), 10)

    def test_produce_consume(self):
        producer_channel = self.p.channel()
        consumer_channel = self.c.channel()
        producer = Producer(producer_channel, self.e)
        consumer1 = Consumer(consumer_channel, self.q)
        consumer2 = Consumer(consumer_channel, self.q2)
        self.q2(consumer_channel).declare()

        for i in range(10):
            producer.publish({'foo': i},
                             routing_key='test_transport_filesystem')
        for i in range(10):
            producer.publish({'foo': i},
                             routing_key='test_transport_filesystem2')

        _received1 = []
        _received2 = []

        def callback1(message_data, message):
            _received1.append(message)
            message.ack()

        def callback2(message_data, message):
            _received2.append(message)
            message.ack()

        consumer1.register_callback(callback1)
        consumer2.register_callback(callback2)

        consumer1.consume()
        consumer2.consume()

        while 1:
            if len(_received1) + len(_received2) == 20:
                break
            self.c.drain_events()

        self.assertEqual(len(_received1) + len(_received2), 20)

        # compression
        producer.publish({'compressed': True},
                         routing_key='test_transport_filesystem',
                         compression='zlib')
        m = self.q(consumer_channel).get()
        self.assertDictEqual(m.payload, {'compressed': True})

        # queue.delete
        for i in range(10):
            producer.publish({'foo': i},
                             routing_key='test_transport_filesystem')
        self.assertTrue(self.q(consumer_channel).get())
        self.q(consumer_channel).delete()
        self.q(consumer_channel).declare()
        self.assertIsNone(self.q(consumer_channel).get())

        # queue.purge
        for i in range(10):
            producer.publish({'foo': i},
                             routing_key='test_transport_filesystem2')
        self.assertTrue(self.q2(consumer_channel).get())
        self.q2(consumer_channel).purge()
        self.assertIsNone(self.q2(consumer_channel).get())

########NEW FILE########
__FILENAME__ = test_librabbitmq
from __future__ import absolute_import

try:
    import librabbitmq
except ImportError:
    librabbitmq = None  # noqa
else:
    from kombu.transport import librabbitmq  # noqa

from kombu.tests.case import Case, Mock, SkipTest, patch


class lrmqCase(Case):

    def setUp(self):
        if librabbitmq is None:
            raise SkipTest('librabbitmq is not installed')


class test_Message(lrmqCase):

    def test_init(self):
        chan = Mock(name='channel')
        message = librabbitmq.Message(
            chan, {'prop': 42}, {'delivery_tag': 337}, 'body',
        )
        self.assertEqual(message.body, 'body')
        self.assertEqual(message.delivery_tag, 337)
        self.assertEqual(message.properties['prop'], 42)


class test_Channel(lrmqCase):

    def test_prepare_message(self):
        conn = Mock(name='connection')
        chan = librabbitmq.Channel(conn, 1)
        self.assertTrue(chan)

        body = 'the quick brown fox...'
        properties = {'name': 'Elaine M.'}

        body2, props2 = chan.prepare_message(
            body, properties=properties,
            priority=999,
            content_type='ctype',
            content_encoding='cenc',
            headers={'H': 2},
        )

        self.assertEqual(props2['name'], 'Elaine M.')
        self.assertEqual(props2['priority'], 999)
        self.assertEqual(props2['content_type'], 'ctype')
        self.assertEqual(props2['content_encoding'], 'cenc')
        self.assertEqual(props2['headers'], {'H': 2})
        self.assertEqual(body2, body)

        body3, props3 = chan.prepare_message(body, priority=777)
        self.assertEqual(props3['priority'], 777)
        self.assertEqual(body3, body)


class test_Transport(lrmqCase):

    def setUp(self):
        super(test_Transport, self).setUp()
        self.client = Mock(name='client')
        self.T = librabbitmq.Transport(self.client)

    def test_driver_version(self):
        self.assertTrue(self.T.driver_version())

    def test_create_channel(self):
        conn = Mock(name='connection')
        chan = self.T.create_channel(conn)
        self.assertTrue(chan)
        conn.channel.assert_called_with()

    def test_drain_events(self):
        conn = Mock(name='connection')
        self.T.drain_events(conn, timeout=1.33)
        conn.drain_events.assert_called_with(timeout=1.33)

    def test_establish_connection_SSL_not_supported(self):
        self.client.ssl = True
        with self.assertRaises(NotImplementedError):
            self.T.establish_connection()

    def test_establish_connection(self):
        self.T.Connection = Mock(name='Connection')
        self.T.client.ssl = False
        self.T.client.port = None
        self.T.client.transport_options = {}

        conn = self.T.establish_connection()
        self.assertEqual(
            self.T.client.port,
            self.T.default_connection_params['port'],
        )
        self.assertEqual(conn.client, self.T.client)
        self.assertEqual(self.T.client.drain_events, conn.drain_events)

    def test_collect__no_conn(self):
        self.T.client.drain_events = 1234
        self.T._collect(None)
        self.assertIsNone(self.client.drain_events)
        self.assertIsNone(self.T.client)

    def test_collect__with_conn(self):
        self.T.client.drain_events = 1234
        conn = Mock(name='connection')
        chans = conn.channels = {1: Mock(name='chan1'), 2: Mock(name='chan2')}
        conn.callbacks = {'foo': Mock(name='cb1'), 'bar': Mock(name='cb2')}
        for i, chan in enumerate(conn.channels.values()):
            chan.connection = i

        with patch('os.close') as close:
            self.T._collect(conn)
            close.assert_called_with(conn.fileno())
        self.assertFalse(conn.channels)
        self.assertFalse(conn.callbacks)
        for chan in chans.values():
            self.assertIsNone(chan.connection)
        self.assertIsNone(self.client.drain_events)
        self.assertIsNone(self.T.client)

        with patch('os.close') as close:
            self.T.client = self.client
            close.side_effect = OSError()
            self.T._collect(conn)
            close.assert_called_with(conn.fileno())

    def test_register_with_event_loop(self):
        conn = Mock(name='conn')
        loop = Mock(name='loop')
        self.T.register_with_event_loop(conn, loop)
        loop.add_reader.assert_called_with(
            conn.fileno(), self.T.on_readable, conn, loop,
        )

    def test_verify_connection(self):
        conn = Mock(name='connection')
        conn.connected = True
        self.assertTrue(self.T.verify_connection(conn))

    def test_close_connection(self):
        conn = Mock(name='connection')
        self.client.drain_events = 1234
        self.T.close_connection(conn)
        self.assertIsNone(self.client.drain_events)
        conn.close.assert_called_with()

########NEW FILE########
__FILENAME__ = test_memory
from __future__ import absolute_import

import socket

from kombu import Connection, Exchange, Queue, Consumer, Producer

from kombu.tests.case import Case


class test_MemoryTransport(Case):

    def setUp(self):
        self.c = Connection(transport='memory')
        self.e = Exchange('test_transport_memory')
        self.q = Queue('test_transport_memory',
                       exchange=self.e,
                       routing_key='test_transport_memory')
        self.q2 = Queue('test_transport_memory2',
                        exchange=self.e,
                        routing_key='test_transport_memory2')
        self.fanout = Exchange('test_transport_memory_fanout', type='fanout')
        self.q3 = Queue('test_transport_memory_fanout1',
                        exchange=self.fanout)
        self.q4 = Queue('test_transport_memory_fanout2',
                        exchange=self.fanout)

    def test_driver_version(self):
        self.assertTrue(self.c.transport.driver_version())

    def test_produce_consume_noack(self):
        channel = self.c.channel()
        producer = Producer(channel, self.e)
        consumer = Consumer(channel, self.q, no_ack=True)

        for i in range(10):
            producer.publish({'foo': i}, routing_key='test_transport_memory')

        _received = []

        def callback(message_data, message):
            _received.append(message)

        consumer.register_callback(callback)
        consumer.consume()

        while 1:
            if len(_received) == 10:
                break
            self.c.drain_events()

        self.assertEqual(len(_received), 10)

    def test_produce_consume_fanout(self):
        producer = self.c.Producer()
        consumer = self.c.Consumer([self.q3, self.q4])

        producer.publish(
            {'hello': 'world'},
            declare=consumer.queues,
            exchange=self.fanout,
        )

        self.assertEqual(self.q3(self.c).get().payload, {'hello': 'world'})
        self.assertEqual(self.q4(self.c).get().payload, {'hello': 'world'})
        self.assertIsNone(self.q3(self.c).get())
        self.assertIsNone(self.q4(self.c).get())

    def test_produce_consume(self):
        channel = self.c.channel()
        producer = Producer(channel, self.e)
        consumer1 = Consumer(channel, self.q)
        consumer2 = Consumer(channel, self.q2)
        self.q2(channel).declare()

        for i in range(10):
            producer.publish({'foo': i}, routing_key='test_transport_memory')
        for i in range(10):
            producer.publish({'foo': i}, routing_key='test_transport_memory2')

        _received1 = []
        _received2 = []

        def callback1(message_data, message):
            _received1.append(message)
            message.ack()

        def callback2(message_data, message):
            _received2.append(message)
            message.ack()

        consumer1.register_callback(callback1)
        consumer2.register_callback(callback2)

        consumer1.consume()
        consumer2.consume()

        while 1:
            if len(_received1) + len(_received2) == 20:
                break
            self.c.drain_events()

        self.assertEqual(len(_received1) + len(_received2), 20)

        # compression
        producer.publish({'compressed': True},
                         routing_key='test_transport_memory',
                         compression='zlib')
        m = self.q(channel).get()
        self.assertDictEqual(m.payload, {'compressed': True})

        # queue.delete
        for i in range(10):
            producer.publish({'foo': i}, routing_key='test_transport_memory')
        self.assertTrue(self.q(channel).get())
        self.q(channel).delete()
        self.q(channel).declare()
        self.assertIsNone(self.q(channel).get())

        # queue.purge
        for i in range(10):
            producer.publish({'foo': i}, routing_key='test_transport_memory2')
        self.assertTrue(self.q2(channel).get())
        self.q2(channel).purge()
        self.assertIsNone(self.q2(channel).get())

    def test_drain_events(self):
        with self.assertRaises(socket.timeout):
            self.c.drain_events(timeout=0.1)

        c1 = self.c.channel()
        c2 = self.c.channel()

        with self.assertRaises(socket.timeout):
            self.c.drain_events(timeout=0.1)

        del(c1)  # so pyflakes doesn't complain.
        del(c2)

    def test_drain_events_unregistered_queue(self):
        c1 = self.c.channel()

        class Cycle(object):

            def get(self, timeout=None):
                return ('foo', 'foo'), c1

        self.c.transport.cycle = Cycle()
        with self.assertRaises(KeyError):
            self.c.drain_events()

    def test_queue_for(self):
        chan = self.c.channel()
        chan.queues.clear()

        x = chan._queue_for('foo')
        self.assertTrue(x)
        self.assertIs(chan._queue_for('foo'), x)

########NEW FILE########
__FILENAME__ = test_mongodb
from __future__ import absolute_import

from kombu import Connection

from kombu.tests.case import Case, SkipTest, skip_if_not_module


class MockConnection(dict):

    def __setattr__(self, key, value):
        self[key] = value


class test_mongodb(Case):

    def _get_connection(self, url, **kwargs):
        from kombu.transport import mongodb

        class Transport(mongodb.Transport):
            Connection = MockConnection

        return Connection(url, transport=Transport, **kwargs).connect()

    @skip_if_not_module('pymongo')
    def test_defaults(self):
        url = 'mongodb://'

        c = self._get_connection(url)
        hostname, dbname, options = c.channels[0]._parse_uri()

        self.assertEquals(dbname, 'kombu_default')
        self.assertEquals(hostname, 'mongodb://127.0.0.1')

    @skip_if_not_module('pymongo')
    def test_custom_host(self):
        url = 'mongodb://localhost'
        c = self._get_connection(url)
        hostname, dbname, options = c.channels[0]._parse_uri()

        self.assertEquals(dbname, 'kombu_default')

    @skip_if_not_module('pymongo')
    def test_custom_database(self):
        url = 'mongodb://localhost/dbname'
        c = self._get_connection(url)
        hostname, dbname, options = c.channels[0]._parse_uri()

        self.assertEquals(dbname, 'dbname')

    @skip_if_not_module('pymongo')
    def test_custom_credentions(self):
        url = 'mongodb://localhost/dbname'
        c = self._get_connection(url, userid='foo', password='bar')
        hostname, dbname, options = c.channels[0]._parse_uri()

        self.assertEquals(hostname, 'mongodb://foo:bar@localhost/dbname')
        self.assertEquals(dbname, 'dbname')

    @skip_if_not_module('pymongo')
    def test_options(self):
        url = 'mongodb://localhost,localhost2:29017/dbname?safe=true'
        c = self._get_connection(url)

        hostname, dbname, options = c.channels[0]._parse_uri()

        self.assertEqual(options['safe'], True)

    @skip_if_not_module('pymongo')
    def test_real_connections(self):
        from pymongo.errors import ConfigurationError

        raise SkipTest(
            'Test is functional: it actually connects to mongod')

        url = 'mongodb://localhost,localhost:29017/dbname'
        c = self._get_connection(url)
        client = c.channels[0].client

        nodes = client.connection.nodes
        # If there's just 1 node it is because we're  connecting to a single
        # server instead of a repl / mongoss.
        if len(nodes) == 2:
            self.assertTrue(('localhost', 29017) in nodes)
            self.assertEquals(client.name, 'dbname')

        url = 'mongodb://localhost:27017,localhost2:29017/dbname'
        c = self._get_connection(url)
        client = c.channels[0].client

        # Login to admin db since there's no db specified
        url = 'mongodb://adminusername:adminpassword@localhost'
        c = self._get_connection()
        client = c.channels[0].client
        self.assertEquals(client.name, 'kombu_default')

        # Lets make sure that using admin db doesn't break anything
        # when no user is specified
        url = 'mongodb://localhost'
        c = self._get_connection(url)
        client = c.channels[0].client

        # Assuming there's user 'username' with password 'password'
        # configured in mongodb
        url = 'mongodb://username:password@localhost/dbname'
        c = self._get_connection(url)
        client = c.channels[0].client

        # Assuming there's no user 'nousername' with password 'nopassword'
        # configured in mongodb
        url = 'mongodb://nousername:nopassword@localhost/dbname'
        c = self._get_connection(url)

        with self.assertRaises(ConfigurationError):
            c.channels[0].client

########NEW FILE########
__FILENAME__ = test_pyamqp
from __future__ import absolute_import

import sys

from itertools import count

try:
    import amqp    # noqa
except ImportError:
    pyamqp = None  # noqa
else:
    from kombu.transport import pyamqp
from kombu import Connection
from kombu.five import nextfun

from kombu.tests.case import Case, Mock, SkipTest, mask_modules, patch


class MockConnection(dict):

    def __setattr__(self, key, value):
        self[key] = value


class test_Channel(Case):

    def setUp(self):
        if pyamqp is None:
            raise SkipTest('py-amqp not installed')

        class Channel(pyamqp.Channel):
            wait_returns = []

            def _x_open(self, *args, **kwargs):
                pass

            def wait(self, *args, **kwargs):
                return self.wait_returns

            def _send_method(self, *args, **kwargs):
                pass

        self.conn = Mock()
        self.conn._get_free_channel_id.side_effect = nextfun(count(0))
        self.conn.channels = {}
        self.channel = Channel(self.conn, 0)

    def test_init(self):
        self.assertFalse(self.channel.no_ack_consumers)

    def test_prepare_message(self):
        self.assertTrue(self.channel.prepare_message(
            'foobar', 10, 'application/data', 'utf-8',
            properties={},
        ))

    def test_message_to_python(self):
        message = Mock()
        message.headers = {}
        message.properties = {}
        self.assertTrue(self.channel.message_to_python(message))

    def test_close_resolves_connection_cycle(self):
        self.assertIsNotNone(self.channel.connection)
        self.channel.close()
        self.assertIsNone(self.channel.connection)

    def test_basic_consume_registers_ack_status(self):
        self.channel.wait_returns = 'my-consumer-tag'
        self.channel.basic_consume('foo', no_ack=True)
        self.assertIn('my-consumer-tag', self.channel.no_ack_consumers)

        self.channel.wait_returns = 'other-consumer-tag'
        self.channel.basic_consume('bar', no_ack=False)
        self.assertNotIn('other-consumer-tag', self.channel.no_ack_consumers)

        self.channel.basic_cancel('my-consumer-tag')
        self.assertNotIn('my-consumer-tag', self.channel.no_ack_consumers)


class test_Transport(Case):

    def setUp(self):
        if pyamqp is None:
            raise SkipTest('py-amqp not installed')
        self.connection = Connection('pyamqp://')
        self.transport = self.connection.transport

    def test_create_channel(self):
        connection = Mock()
        self.transport.create_channel(connection)
        connection.channel.assert_called_with()

    def test_driver_version(self):
        self.assertTrue(self.transport.driver_version())

    def test_drain_events(self):
        connection = Mock()
        self.transport.drain_events(connection, timeout=10.0)
        connection.drain_events.assert_called_with(timeout=10.0)

    def test_dnspython_localhost_resolve_bug(self):

        class Conn(object):

            def __init__(self, **kwargs):
                vars(self).update(kwargs)

        self.transport.Connection = Conn
        self.transport.client.hostname = 'localhost'
        conn1 = self.transport.establish_connection()
        self.assertEqual(conn1.host, '127.0.0.1:5672')

        self.transport.client.hostname = 'example.com'
        conn2 = self.transport.establish_connection()
        self.assertEqual(conn2.host, 'example.com:5672')

    def test_close_connection(self):
        connection = Mock()
        connection.client = Mock()
        self.transport.close_connection(connection)

        self.assertIsNone(connection.client)
        connection.close.assert_called_with()

    @mask_modules('ssl')
    def test_import_no_ssl(self):
        pm = sys.modules.pop('amqp.connection')
        try:
            from amqp.connection import SSLError
            self.assertEqual(SSLError.__module__, 'amqp.connection')
        finally:
            if pm is not None:
                sys.modules['amqp.connection'] = pm


class test_pyamqp(Case):

    def setUp(self):
        if pyamqp is None:
            raise SkipTest('py-amqp not installed')

    def test_default_port(self):

        class Transport(pyamqp.Transport):
            Connection = MockConnection

        c = Connection(port=None, transport=Transport).connect()
        self.assertEqual(c['host'],
                         '127.0.0.1:%s' % (Transport.default_port, ))

    def test_custom_port(self):

        class Transport(pyamqp.Transport):
            Connection = MockConnection

        c = Connection(port=1337, transport=Transport).connect()
        self.assertEqual(c['host'], '127.0.0.1:1337')

    def test_register_with_event_loop(self):
        t = pyamqp.Transport(Mock())
        conn = Mock(name='conn')
        loop = Mock(name='loop')
        t.register_with_event_loop(conn, loop)
        loop.add_reader.assert_called_with(
            conn.sock, t.on_readable, conn, loop,
        )

    def test_heartbeat_check(self):
        t = pyamqp.Transport(Mock())
        conn = Mock()
        t.heartbeat_check(conn, rate=4.331)
        conn.heartbeat_tick.assert_called_with(rate=4.331)

    def test_get_manager(self):
        with patch('kombu.transport.pyamqp.get_manager') as get_manager:
            t = pyamqp.Transport(Mock())
            t.get_manager(1, kw=2)
            get_manager.assert_called_with(t.client, 1, kw=2)

########NEW FILE########
__FILENAME__ = test_redis
from __future__ import absolute_import

import socket
import types

from collections import defaultdict
from itertools import count

from kombu import Connection, Exchange, Queue, Consumer, Producer
from kombu.exceptions import InconsistencyError, VersionMismatch
from kombu.five import Empty, Queue as _Queue
from kombu.transport import virtual
from kombu.utils import eventio  # patch poll
from kombu.utils.json import dumps, loads

from kombu.tests.case import (
    Case, Mock, call, module_exists, skip_if_not_module, patch,
)


class _poll(eventio._select):

    def register(self, fd, flags):
        if flags & eventio.READ:
            self._rfd.add(fd)

    def poll(self, timeout):
        events = []
        for fd in self._rfd:
            if fd.data:
                events.append((fd.fileno(), eventio.READ))
        return events


eventio.poll = _poll
from kombu.transport import redis  # must import after poller patch


class ResponseError(Exception):
    pass


class Client(object):
    queues = {}
    sets = defaultdict(set)
    hashes = defaultdict(dict)
    shard_hint = None

    def __init__(self, db=None, port=None, connection_pool=None, **kwargs):
        self._called = []
        self._connection = None
        self.bgsave_raises_ResponseError = False
        self.connection = self._sconnection(self)

    def bgsave(self):
        self._called.append('BGSAVE')
        if self.bgsave_raises_ResponseError:
            raise ResponseError()

    def delete(self, key):
        self.queues.pop(key, None)

    def exists(self, key):
        return key in self.queues or key in self.sets

    def hset(self, key, k, v):
        self.hashes[key][k] = v

    def hget(self, key, k):
        return self.hashes[key].get(k)

    def hdel(self, key, k):
        self.hashes[key].pop(k, None)

    def sadd(self, key, member, *args):
        self.sets[key].add(member)
    zadd = sadd

    def smembers(self, key):
        return self.sets.get(key, set())

    def srem(self, key, *args):
        self.sets.pop(key, None)
    zrem = srem

    def llen(self, key):
        try:
            return self.queues[key].qsize()
        except KeyError:
            return 0

    def lpush(self, key, value):
        self.queues[key].put_nowait(value)

    def parse_response(self, connection, type, **options):
        cmd, queues = self.connection._sock.data.pop()
        assert cmd == type
        self.connection._sock.data = []
        if type == 'BRPOP':
            item = self.brpop(queues, 0.001)
            if item:
                return item
            raise Empty()

    def brpop(self, keys, timeout=None):
        key = keys[0]
        try:
            item = self.queues[key].get(timeout=timeout)
        except Empty:
            pass
        else:
            return key, item

    def rpop(self, key):
        try:
            return self.queues[key].get_nowait()
        except KeyError:
            pass

    def __contains__(self, k):
        return k in self._called

    def pipeline(self):
        return Pipeline(self)

    def encode(self, value):
        return str(value)

    def _new_queue(self, key):
        self.queues[key] = _Queue()

    class _sconnection(object):
        disconnected = False

        class _socket(object):
            blocking = True
            filenos = count(30)

            def __init__(self, *args):
                self._fileno = next(self.filenos)
                self.data = []

            def fileno(self):
                return self._fileno

            def setblocking(self, blocking):
                self.blocking = blocking

        def __init__(self, client):
            self.client = client
            self._sock = self._socket()

        def disconnect(self):
            self.disconnected = True

        def send_command(self, cmd, *args):
            self._sock.data.append((cmd, args))

    def info(self):
        return {'foo': 1}

    def pubsub(self, *args, **kwargs):
        connection = self.connection

        class ConnectionPool(object):

            def get_connection(self, *args, **kwargs):
                return connection
        self.connection_pool = ConnectionPool()

        return self


class Pipeline(object):

    def __init__(self, client):
        self.client = client
        self.stack = []

    def __getattr__(self, key):
        if key not in self.__dict__:

            def _add(*args, **kwargs):
                self.stack.append((getattr(self.client, key), args, kwargs))
                return self

            return _add
        return self.__dict__[key]

    def execute(self):
        stack = list(self.stack)
        self.stack[:] = []
        return [fun(*args, **kwargs) for fun, args, kwargs in stack]


class Channel(redis.Channel):

    def _get_client(self):
        return Client

    def _get_pool(self):
        return Mock()

    def _get_response_error(self):
        return ResponseError

    def _new_queue(self, queue, **kwargs):
        self.client._new_queue(queue)

    def pipeline(self):
        return Pipeline(Client())


class Transport(redis.Transport):
    Channel = Channel

    def _get_errors(self):
        return ((KeyError, ), (IndexError, ))


class test_Channel(Case):

    def setUp(self):
        self.connection = self.create_connection()
        self.channel = self.connection.default_channel

    def create_connection(self, **kwargs):
        kwargs.setdefault('transport_options', {'fanout_patterns': True})
        return Connection(transport=Transport, **kwargs)

    def _get_one_delivery_tag(self, n='test_uniq_tag'):
        with self.create_connection() as conn1:
            chan = conn1.default_channel
            chan.exchange_declare(n)
            chan.queue_declare(n)
            chan.queue_bind(n, n, n)
            msg = chan.prepare_message('quick brown fox')
            chan.basic_publish(msg, n, n)
            q, payload = chan.client.brpop([n])
            self.assertEqual(q, n)
            self.assertTrue(payload)
            pymsg = chan.message_to_python(loads(payload))
            return pymsg.delivery_tag

    def test_delivery_tag_is_uuid(self):
        seen = set()
        for i in range(100):
            tag = self._get_one_delivery_tag()
            self.assertNotIn(tag, seen)
            seen.add(tag)
            with self.assertRaises(ValueError):
                int(tag)
            self.assertEqual(len(tag), 36)

    def test_disable_ack_emulation(self):
        conn = Connection(transport=Transport, transport_options={
            'ack_emulation': False,
        })

        chan = conn.channel()
        self.assertFalse(chan.ack_emulation)
        self.assertEqual(chan.QoS, virtual.QoS)

    def test_redis_info_raises(self):
        pool = Mock(name='pool')
        pool_at_init = [pool]
        client = Mock(name='client')

        class XChannel(Channel):

            def __init__(self, *args, **kwargs):
                self._pool = pool_at_init[0]
                super(XChannel, self).__init__(*args, **kwargs)

            def _get_client(self):
                return lambda *_, **__: client

        class XTransport(Transport):
            Channel = XChannel

        conn = Connection(transport=XTransport)
        client.info.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError):
            conn.channel()
        pool.disconnect.assert_called_with()
        pool.disconnect.reset_mock()

        pool_at_init = [None]
        with self.assertRaises(RuntimeError):
            conn.channel()
        self.assertFalse(pool.disconnect.called)

    def test_after_fork(self):
        self.channel._pool = None
        self.channel._after_fork()

        self.channel._pool = Mock(name='pool')
        self.channel._after_fork()
        self.channel._pool.disconnect.assert_called_with()

    def test_next_delivery_tag(self):
        self.assertNotEqual(
            self.channel._next_delivery_tag(),
            self.channel._next_delivery_tag(),
        )

    def test_do_restore_message(self):
        client = Mock(name='client')
        pl1 = {'body': 'BODY'}
        spl1 = dumps(pl1)
        lookup = self.channel._lookup = Mock(name='_lookup')
        lookup.return_value = ['george', 'elaine']
        self.channel._do_restore_message(
            pl1, 'ex', 'rkey', client,
        )
        client.rpush.assert_has_calls([
            call('george', spl1), call('elaine', spl1),
        ])

        pl2 = {'body': 'BODY2', 'headers': {'x-funny': 1}}
        headers_after = dict(pl2['headers'], redelivered=True)
        spl2 = dumps(dict(pl2, headers=headers_after))
        self.channel._do_restore_message(
            pl2, 'ex', 'rkey', client,
        )
        client.rpush.assert_has_calls([
            call('george', spl2), call('elaine', spl2),
        ])

        client.rpush.side_effect = KeyError()
        with patch('kombu.transport.redis.crit') as crit:
            self.channel._do_restore_message(
                pl2, 'ex', 'rkey', client,
            )
            self.assertTrue(crit.called)

    def test_restore(self):
        message = Mock(name='message')
        with patch('kombu.transport.redis.loads') as loads:
            loads.return_value = 'M', 'EX', 'RK'
            client = self.channel.client = Mock(name='client')
            restore = self.channel._do_restore_message = Mock(
                name='_do_restore_message',
            )
            pipe = Mock(name='pipe')
            client.pipeline.return_value = pipe
            pipe_hget = Mock(name='pipe.hget')
            pipe.hget.return_value = pipe_hget
            pipe_hget_hdel = Mock(name='pipe.hget.hdel')
            pipe_hget.hdel.return_value = pipe_hget_hdel
            result = Mock(name='result')
            pipe_hget_hdel.execute.return_value = None, None

            self.channel._restore(message)
            client.pipeline.assert_called_with()
            unacked_key = self.channel.unacked_key
            self.assertFalse(loads.called)

            tag = message.delivery_tag
            pipe.hget.assert_called_with(unacked_key, tag)
            pipe_hget.hdel.assert_called_with(unacked_key, tag)
            pipe_hget_hdel.execute.assert_called_with()

            pipe_hget_hdel.execute.return_value = result, None
            self.channel._restore(message)
            loads.assert_called_with(result)
            restore.assert_called_with('M', 'EX', 'RK', client, False)

    def test_qos_restore_visible(self):
        client = self.channel.client = Mock(name='client')
        client.zrevrangebyscore.return_value = [
            (1, 10),
            (2, 20),
            (3, 30),
        ]
        qos = redis.QoS(self.channel)
        restore = qos.restore_by_tag = Mock(name='restore_by_tag')
        qos._vrestore_count = 1
        qos.restore_visible()
        self.assertFalse(client.zrevrangebyscore.called)
        self.assertEqual(qos._vrestore_count, 2)

        qos._vrestore_count = 0
        qos.restore_visible()
        restore.assert_has_calls([
            call(1, client), call(2, client), call(3, client),
        ])
        self.assertEqual(qos._vrestore_count, 1)

        qos._vrestore_count = 0
        restore.reset_mock()
        client.zrevrangebyscore.return_value = []
        qos.restore_visible()
        self.assertFalse(restore.called)
        self.assertEqual(qos._vrestore_count, 1)

        qos._vrestore_count = 0
        client.setnx.side_effect = redis.MutexHeld()
        qos.restore_visible()

    def test_basic_consume_when_fanout_queue(self):
        self.channel.exchange_declare(exchange='txconfan', type='fanout')
        self.channel.queue_declare(queue='txconfanq')
        self.channel.queue_bind(queue='txconfanq', exchange='txconfan')

        self.assertIn('txconfanq', self.channel._fanout_queues)
        self.channel.basic_consume('txconfanq', False, None, 1)
        self.assertIn('txconfanq', self.channel.active_fanout_queues)
        self.assertEqual(self.channel._fanout_to_queue.get('txconfan'),
                         'txconfanq')

    def test_basic_cancel_unknown_delivery_tag(self):
        self.assertIsNone(self.channel.basic_cancel('txaseqwewq'))

    def test_subscribe_no_queues(self):
        self.channel.subclient = Mock()
        self.channel.active_fanout_queues.clear()
        self.channel._subscribe()

        self.assertFalse(self.channel.subclient.subscribe.called)

    def test_subscribe(self):
        self.channel.subclient = Mock()
        self.channel.active_fanout_queues.add('a')
        self.channel.active_fanout_queues.add('b')
        self.channel._fanout_queues.update(a=('a', ''), b=('b', ''))

        self.channel._subscribe()
        self.assertTrue(self.channel.subclient.psubscribe.called)
        s_args, _ = self.channel.subclient.psubscribe.call_args
        self.assertItemsEqual(s_args[0], ['a', 'b'])

        self.channel.subclient.connection._sock = None
        self.channel._subscribe()
        self.channel.subclient.connection.connect.assert_called_with()

    def test_handle_unsubscribe_message(self):
        s = self.channel.subclient
        s.subscribed = True
        self.channel._handle_message(s, ['unsubscribe', 'a', 0])
        self.assertFalse(s.subscribed)

    def test_handle_pmessage_message(self):
        self.assertDictEqual(
            self.channel._handle_message(
                self.channel.subclient,
                ['pmessage', 'pattern', 'channel', 'data'],
            ),
            {
                'type': 'pmessage',
                'pattern': 'pattern',
                'channel': 'channel',
                'data': 'data',
            },
        )

    def test_handle_message(self):
        self.assertDictEqual(
            self.channel._handle_message(
                self.channel.subclient,
                ['type', 'channel', 'data'],
            ),
            {
                'type': 'type',
                'pattern': None,
                'channel': 'channel',
                'data': 'data',
            },
        )

    def test_brpop_start_but_no_queues(self):
        self.assertIsNone(self.channel._brpop_start())

    def test_receive(self):
        s = self.channel.subclient = Mock()
        self.channel._fanout_to_queue['a'] = 'b'
        s.parse_response.return_value = ['message', 'a',
                                         dumps({'hello': 'world'})]
        payload, queue = self.channel._receive()
        self.assertDictEqual(payload, {'hello': 'world'})
        self.assertEqual(queue, 'b')

    def test_receive_raises(self):
        self.channel._in_listen = True
        s = self.channel.subclient = Mock()
        s.parse_response.side_effect = KeyError('foo')

        with self.assertRaises(redis.Empty):
            self.channel._receive()
        self.assertFalse(self.channel._in_listen)

    def test_receive_empty(self):
        s = self.channel.subclient = Mock()
        s.parse_response.return_value = None

        with self.assertRaises(redis.Empty):
            self.channel._receive()

    def test_receive_different_message_Type(self):
        s = self.channel.subclient = Mock()
        s.parse_response.return_value = ['message', '/foo/', 0, 'data']

        with self.assertRaises(redis.Empty):
            self.channel._receive()

    def test_brpop_read_raises(self):
        c = self.channel.client = Mock()
        c.parse_response.side_effect = KeyError('foo')

        with self.assertRaises(redis.Empty):
            self.channel._brpop_read()

        c.connection.disconnect.assert_called_with()

    def test_brpop_read_gives_None(self):
        c = self.channel.client = Mock()
        c.parse_response.return_value = None

        with self.assertRaises(redis.Empty):
            self.channel._brpop_read()

    def test_poll_error(self):
        c = self.channel.client = Mock()
        c.parse_response = Mock()
        self.channel._poll_error('BRPOP')

        c.parse_response.assert_called_with(c.connection, 'BRPOP')

        c.parse_response.side_effect = KeyError('foo')
        with self.assertRaises(KeyError):
            self.channel._poll_error('BRPOP')

    def test_poll_error_on_type_LISTEN(self):
        c = self.channel.subclient = Mock()
        c.parse_response = Mock()
        self.channel._poll_error('LISTEN')

        c.parse_response.assert_called_with()

        c.parse_response.side_effect = KeyError('foo')
        with self.assertRaises(KeyError):
            self.channel._poll_error('LISTEN')

    def test_put_fanout(self):
        self.channel._in_poll = False
        c = self.channel.client = Mock()

        body = {'hello': 'world'}
        self.channel._put_fanout('exchange', body, '')
        c.publish.assert_called_with('exchange', dumps(body))

    def test_put_priority(self):
        client = self.channel.client = Mock(name='client')
        msg1 = {'properties': {'delivery_info': {'priority': 3}}}

        self.channel._put('george', msg1)
        client.lpush.assert_called_with(
            self.channel._q_for_pri('george', 3), dumps(msg1),
        )

        msg2 = {'properties': {'delivery_info': {'priority': 313}}}
        self.channel._put('george', msg2)
        client.lpush.assert_called_with(
            self.channel._q_for_pri('george', 9), dumps(msg2),
        )

        msg3 = {'properties': {'delivery_info': {}}}
        self.channel._put('george', msg3)
        client.lpush.assert_called_with(
            self.channel._q_for_pri('george', 0), dumps(msg3),
        )

    def test_delete(self):
        x = self.channel
        self.channel._in_poll = False
        delete = x.client.delete = Mock()
        srem = x.client.srem = Mock()

        x._delete('queue', 'exchange', 'routing_key', None)
        delete.assert_has_call('queue')
        srem.assert_has_call(x.keyprefix_queue % ('exchange', ),
                             x.sep.join(['routing_key', '', 'queue']))

    def test_has_queue(self):
        self.channel._in_poll = False
        exists = self.channel.client.exists = Mock()
        exists.return_value = True
        self.assertTrue(self.channel._has_queue('foo'))
        exists.assert_has_call('foo')

        exists.return_value = False
        self.assertFalse(self.channel._has_queue('foo'))

    def test_close_when_closed(self):
        self.channel.closed = True
        self.channel.close()

    def test_close_deletes_autodelete_fanout_queues(self):
        self.channel._fanout_queues = {'foo': ('foo', ''), 'bar': ('bar', '')}
        self.channel.auto_delete_queues = ['foo']
        self.channel.queue_delete = Mock(name='queue_delete')

        self.channel.close()
        self.channel.queue_delete.assert_has_calls([call('foo')])

    def test_close_client_close_raises(self):
        c = self.channel.client = Mock()
        c.connection.disconnect.side_effect = self.channel.ResponseError()

        self.channel.close()
        c.connection.disconnect.assert_called_with()

    def test_invalid_database_raises_ValueError(self):

        with self.assertRaises(ValueError):
            self.channel.connection.client.virtual_host = 'dwqeq'
            self.channel._connparams()

    @skip_if_not_module('redis')
    def test_connparams_allows_slash_in_db(self):
        self.channel.connection.client.virtual_host = '/123'
        self.assertEqual(self.channel._connparams()['db'], 123)

    @skip_if_not_module('redis')
    def test_connparams_db_can_be_int(self):
        self.channel.connection.client.virtual_host = 124
        self.assertEqual(self.channel._connparams()['db'], 124)

    def test_new_queue_with_auto_delete(self):
        redis.Channel._new_queue(self.channel, 'george', auto_delete=False)
        self.assertNotIn('george', self.channel.auto_delete_queues)
        redis.Channel._new_queue(self.channel, 'elaine', auto_delete=True)
        self.assertIn('elaine', self.channel.auto_delete_queues)

    @skip_if_not_module('redis')
    def test_connparams_regular_hostname(self):
        self.channel.connection.client.hostname = 'george.vandelay.com'
        self.assertEqual(
            self.channel._connparams()['host'],
            'george.vandelay.com',
        )

    def test_rotate_cycle_ValueError(self):
        cycle = self.channel._queue_cycle = ['kramer', 'jerry']
        self.channel._rotate_cycle('kramer')
        self.assertEqual(cycle, ['jerry', 'kramer'])
        self.channel._rotate_cycle('elaine')

    @skip_if_not_module('redis')
    def test_get_client(self):
        import redis as R
        KombuRedis = redis.Channel._get_client(self.channel)
        self.assertTrue(KombuRedis)

        Rv = getattr(R, 'VERSION', None)
        try:
            R.VERSION = (2, 4, 0)
            with self.assertRaises(VersionMismatch):
                redis.Channel._get_client(self.channel)
        finally:
            if Rv is not None:
                R.VERSION = Rv

    @skip_if_not_module('redis')
    def test_get_response_error(self):
        from redis.exceptions import ResponseError
        self.assertIs(redis.Channel._get_response_error(self.channel),
                      ResponseError)

    def test_avail_client_when_not_in_poll(self):
        self.channel._in_poll = False
        c = self.channel.client = Mock()

        with self.channel.conn_or_acquire() as client:
            self.assertIs(client, c)

    def test_avail_client_when_in_poll(self):
        self.channel._in_poll = True
        self.channel._pool = Mock()
        cc = self.channel._create_client = Mock()
        client = cc.return_value = Mock()

        with self.channel.conn_or_acquire():
            pass
        self.channel.pool.release.assert_called_with(client.connection)
        cc.assert_called_with()

    def test_register_with_event_loop(self):
        transport = self.connection.transport
        transport.cycle = Mock(name='cycle')
        transport.cycle.fds = {12: 'LISTEN', 13: 'BRPOP'}
        conn = Mock(name='conn')
        loop = Mock(name='loop')
        redis.Transport.register_with_event_loop(transport, conn, loop)
        transport.cycle.on_poll_init.assert_called_with(loop.poller)
        loop.call_repeatedly.assert_called_with(
            10, transport.cycle.maybe_restore_messages,
        )
        self.assertTrue(loop.on_tick.add.called)
        on_poll_start = loop.on_tick.add.call_args[0][0]

        on_poll_start()
        transport.cycle.on_poll_start.assert_called_with()
        loop.add_reader.assert_has_calls([
            call(12, transport.on_readable, 12),
            call(13, transport.on_readable, 13),
        ])

    def test_transport_on_readable(self):
        transport = self.connection.transport
        cycle = transport.cycle = Mock(name='cyle')
        cycle.on_readable.return_value = None

        redis.Transport.on_readable(transport, 13)
        cycle.on_readable.assert_called_with(13)
        cycle.on_readable.reset_mock()

        queue = Mock(name='queue')
        ret = (Mock(name='message'), queue)
        cycle.on_readable.return_value = ret
        with self.assertRaises(KeyError):
            redis.Transport.on_readable(transport, 14)

        cb = transport._callbacks[queue] = Mock(name='callback')
        redis.Transport.on_readable(transport, 14)
        cb.assert_called_with(ret[0])

    @skip_if_not_module('redis')
    def test_transport_get_errors(self):
        self.assertTrue(redis.Transport._get_errors(self.connection.transport))

    @skip_if_not_module('redis')
    def test_transport_driver_version(self):
        self.assertTrue(
            redis.Transport.driver_version(self.connection.transport),
        )

    @skip_if_not_module('redis')
    def test_transport_get_errors_when_InvalidData_used(self):
        from redis import exceptions

        class ID(Exception):
            pass

        DataError = getattr(exceptions, 'DataError', None)
        InvalidData = getattr(exceptions, 'InvalidData', None)
        exceptions.InvalidData = ID
        exceptions.DataError = None
        try:
            errors = redis.Transport._get_errors(self.connection.transport)
            self.assertTrue(errors)
            self.assertIn(ID, errors[1])
        finally:
            if DataError is not None:
                exceptions.DataError = DataError
            if InvalidData is not None:
                exceptions.InvalidData = InvalidData

    def test_empty_queues_key(self):
        channel = self.channel
        channel._in_poll = False
        key = channel.keyprefix_queue % 'celery'

        # Everything is fine, there is a list of queues.
        channel.client.sadd(key, 'celery\x06\x16\x06\x16celery')
        self.assertListEqual(channel.get_table('celery'),
                             [('celery', '', 'celery')])

        # ... then for some reason, the _kombu.binding.celery key gets lost
        channel.client.srem(key)

        # which raises a channel error so that the consumer/publisher
        # can recover by redeclaring the required entities.
        with self.assertRaises(InconsistencyError):
            self.channel.get_table('celery')

    @skip_if_not_module('redis')
    def test_socket_connection(self):
        with patch('kombu.transport.redis.Channel._create_client'):
            with Connection('redis+socket:///tmp/redis.sock') as conn:
                connparams = conn.default_channel._connparams()
                self.assertTrue(issubclass(
                    connparams['connection_class'],
                    redis.redis.UnixDomainSocketConnection,
                ))
                self.assertEqual(connparams['path'], '/tmp/redis.sock')


class test_Redis(Case):

    def setUp(self):
        self.connection = Connection(transport=Transport)
        self.exchange = Exchange('test_Redis', type='direct')
        self.queue = Queue('test_Redis', self.exchange, 'test_Redis')

    def tearDown(self):
        self.connection.close()

    def test_publish__get(self):
        channel = self.connection.channel()
        producer = Producer(channel, self.exchange, routing_key='test_Redis')
        self.queue(channel).declare()

        producer.publish({'hello': 'world'})

        self.assertDictEqual(self.queue(channel).get().payload,
                             {'hello': 'world'})
        self.assertIsNone(self.queue(channel).get())
        self.assertIsNone(self.queue(channel).get())
        self.assertIsNone(self.queue(channel).get())

    def test_publish__consume(self):
        connection = Connection(transport=Transport)
        channel = connection.channel()
        producer = Producer(channel, self.exchange, routing_key='test_Redis')
        consumer = Consumer(channel, queues=[self.queue])

        producer.publish({'hello2': 'world2'})
        _received = []

        def callback(message_data, message):
            _received.append(message_data)
            message.ack()

        consumer.register_callback(callback)
        consumer.consume()

        self.assertIn(channel, channel.connection.cycle._channels)
        try:
            connection.drain_events(timeout=1)
            self.assertTrue(_received)
            with self.assertRaises(socket.timeout):
                connection.drain_events(timeout=0.01)
        finally:
            channel.close()

    def test_purge(self):
        channel = self.connection.channel()
        producer = Producer(channel, self.exchange, routing_key='test_Redis')
        self.queue(channel).declare()

        for i in range(10):
            producer.publish({'hello': 'world-%s' % (i, )})

        self.assertEqual(channel._size('test_Redis'), 10)
        self.assertEqual(self.queue(channel).purge(), 10)
        channel.close()

    def test_db_values(self):
        Connection(virtual_host=1,
                   transport=Transport).channel()

        Connection(virtual_host='1',
                   transport=Transport).channel()

        Connection(virtual_host='/1',
                   transport=Transport).channel()

        with self.assertRaises(Exception):
            Connection('redis:///foo').channel()

    def test_db_port(self):
        c1 = Connection(port=None, transport=Transport).channel()
        c1.close()

        c2 = Connection(port=9999, transport=Transport).channel()
        c2.close()

    def test_close_poller_not_active(self):
        c = Connection(transport=Transport).channel()
        cycle = c.connection.cycle
        c.client.connection
        c.close()
        self.assertNotIn(c, cycle._channels)

    def test_close_ResponseError(self):
        c = Connection(transport=Transport).channel()
        c.client.bgsave_raises_ResponseError = True
        c.close()

    def test_close_disconnects(self):
        c = Connection(transport=Transport).channel()
        conn1 = c.client.connection
        conn2 = c.subclient.connection
        c.close()
        self.assertTrue(conn1.disconnected)
        self.assertTrue(conn2.disconnected)

    def test_get__Empty(self):
        channel = self.connection.channel()
        with self.assertRaises(Empty):
            channel._get('does-not-exist')
        channel.close()

    def test_get_client(self):

        myredis, exceptions = _redis_modules()

        @module_exists(myredis, exceptions)
        def _do_test():
            conn = Connection(transport=Transport)
            chan = conn.channel()
            self.assertTrue(chan.Client)
            self.assertTrue(chan.ResponseError)
            self.assertTrue(conn.transport.connection_errors)
            self.assertTrue(conn.transport.channel_errors)

        _do_test()


def _redis_modules():

    class ConnectionError(Exception):
        pass

    class AuthenticationError(Exception):
        pass

    class InvalidData(Exception):
        pass

    class InvalidResponse(Exception):
        pass

    class ResponseError(Exception):
        pass

    exceptions = types.ModuleType('redis.exceptions')
    exceptions.ConnectionError = ConnectionError
    exceptions.AuthenticationError = AuthenticationError
    exceptions.InvalidData = InvalidData
    exceptions.InvalidResponse = InvalidResponse
    exceptions.ResponseError = ResponseError

    class Redis(object):
        pass

    myredis = types.ModuleType('redis')
    myredis.exceptions = exceptions
    myredis.Redis = Redis

    return myredis, exceptions


class test_MultiChannelPoller(Case):

    def setUp(self):
        self.Poller = redis.MultiChannelPoller

    def test_on_poll_start(self):
        p = self.Poller()
        p._channels = []
        p.on_poll_start()
        p._register_BRPOP = Mock(name='_register_BRPOP')
        p._register_LISTEN = Mock(name='_register_LISTEN')

        chan1 = Mock(name='chan1')
        p._channels = [chan1]
        chan1.active_queues = []
        chan1.active_fanout_queues = []
        p.on_poll_start()

        chan1.active_queues = ['q1']
        chan1.active_fanout_queues = ['q2']
        chan1.qos.can_consume.return_value = False

        p.on_poll_start()
        p._register_LISTEN.assert_called_with(chan1)
        self.assertFalse(p._register_BRPOP.called)

        chan1.qos.can_consume.return_value = True
        p._register_LISTEN.reset_mock()
        p.on_poll_start()

        p._register_BRPOP.assert_called_with(chan1)
        p._register_LISTEN.assert_called_with(chan1)

    def test_on_poll_init(self):
        p = self.Poller()
        chan1 = Mock(name='chan1')
        p._channels = []
        poller = Mock(name='poller')
        p.on_poll_init(poller)
        self.assertIs(p.poller, poller)

        p._channels = [chan1]
        p.on_poll_init(poller)
        chan1.qos.restore_visible.assert_called_with(
            num=chan1.unacked_restore_limit,
        )

    def test_handle_event(self):
        p = self.Poller()
        chan = Mock(name='chan')
        p._fd_to_chan[13] = chan, 'BRPOP'
        chan.handlers = {'BRPOP': Mock(name='BRPOP')}

        chan.qos.can_consume.return_value = False
        p.handle_event(13, redis.READ)
        self.assertFalse(chan.handlers['BRPOP'].called)

        chan.qos.can_consume.return_value = True
        p.handle_event(13, redis.READ)
        chan.handlers['BRPOP'].assert_called_with()

        p.handle_event(13, redis.ERR)
        chan._poll_error.assert_called_with('BRPOP')

        p.handle_event(13, ~(redis.READ | redis.ERR))

    def test_fds(self):
        p = self.Poller()
        p._fd_to_chan = {1: 2}
        self.assertDictEqual(p.fds, p._fd_to_chan)

    def test_close_unregisters_fds(self):
        p = self.Poller()
        poller = p.poller = Mock()
        p._chan_to_sock.update({1: 1, 2: 2, 3: 3})

        p.close()

        self.assertEqual(poller.unregister.call_count, 3)
        u_args = poller.unregister.call_args_list

        self.assertItemsEqual(u_args, [((1, ), {}),
                                       ((2, ), {}),
                                       ((3, ), {})])

    def test_close_when_unregister_raises_KeyError(self):
        p = self.Poller()
        p.poller = Mock()
        p._chan_to_sock.update({1: 1})
        p.poller.unregister.side_effect = KeyError(1)
        p.close()

    def test_close_resets_state(self):
        p = self.Poller()
        p.poller = Mock()
        p._channels = Mock()
        p._fd_to_chan = Mock()
        p._chan_to_sock = Mock()

        p._chan_to_sock.itervalues.return_value = []
        p._chan_to_sock.values.return_value = []  # py3k

        p.close()
        p._channels.clear.assert_called_with()
        p._fd_to_chan.clear.assert_called_with()
        p._chan_to_sock.clear.assert_called_with()
        self.assertIsNone(p.poller)

    def test_register_when_registered_reregisters(self):
        p = self.Poller()
        p.poller = Mock()
        channel, client, type = Mock(), Mock(), Mock()
        sock = client.connection._sock = Mock()
        sock.fileno.return_value = 10

        p._chan_to_sock = {(channel, client, type): 6}
        p._register(channel, client, type)
        p.poller.unregister.assert_called_with(6)
        self.assertTupleEqual(p._fd_to_chan[10], (channel, type))
        self.assertEqual(p._chan_to_sock[(channel, client, type)], sock)
        p.poller.register.assert_called_with(sock, p.eventflags)

        # when client not connected yet
        client.connection._sock = None

        def after_connected():
            client.connection._sock = Mock()
        client.connection.connect.side_effect = after_connected

        p._register(channel, client, type)
        client.connection.connect.assert_called_with()

    def test_register_BRPOP(self):
        p = self.Poller()
        channel = Mock()
        channel.client.connection._sock = None
        p._register = Mock()

        channel._in_poll = False
        p._register_BRPOP(channel)
        self.assertEqual(channel._brpop_start.call_count, 1)
        self.assertEqual(p._register.call_count, 1)

        channel.client.connection._sock = Mock()
        p._chan_to_sock[(channel, channel.client, 'BRPOP')] = True
        channel._in_poll = True
        p._register_BRPOP(channel)
        self.assertEqual(channel._brpop_start.call_count, 1)
        self.assertEqual(p._register.call_count, 1)

    def test_register_LISTEN(self):
        p = self.Poller()
        channel = Mock()
        channel.subclient.connection._sock = None
        channel._in_listen = False
        p._register = Mock()

        p._register_LISTEN(channel)
        p._register.assert_called_with(channel, channel.subclient, 'LISTEN')
        self.assertEqual(p._register.call_count, 1)
        self.assertEqual(channel._subscribe.call_count, 1)

        channel._in_listen = True
        channel.subclient.connection._sock = Mock()
        p._register_LISTEN(channel)
        self.assertEqual(p._register.call_count, 1)
        self.assertEqual(channel._subscribe.call_count, 1)

    def create_get(self, events=None, queues=None, fanouts=None):
        _pr = [] if events is None else events
        _aq = [] if queues is None else queues
        _af = [] if fanouts is None else fanouts
        p = self.Poller()
        p.poller = Mock()
        p.poller.poll.return_value = _pr

        p._register_BRPOP = Mock()
        p._register_LISTEN = Mock()

        channel = Mock()
        p._channels = [channel]
        channel.active_queues = _aq
        channel.active_fanout_queues = _af

        return p, channel

    def test_get_no_actions(self):
        p, channel = self.create_get()

        with self.assertRaises(redis.Empty):
            p.get()

    def test_qos_reject(self):
        p, channel = self.create_get()
        qos = redis.QoS(channel)
        qos.ack = Mock(name='Qos.ack')
        qos.reject(1234)
        qos.ack.assert_called_with(1234)

    def test_get_brpop_qos_allow(self):
        p, channel = self.create_get(queues=['a_queue'])
        channel.qos.can_consume.return_value = True

        with self.assertRaises(redis.Empty):
            p.get()

        p._register_BRPOP.assert_called_with(channel)

    def test_get_brpop_qos_disallow(self):
        p, channel = self.create_get(queues=['a_queue'])
        channel.qos.can_consume.return_value = False

        with self.assertRaises(redis.Empty):
            p.get()

        self.assertFalse(p._register_BRPOP.called)

    def test_get_listen(self):
        p, channel = self.create_get(fanouts=['f_queue'])

        with self.assertRaises(redis.Empty):
            p.get()

        p._register_LISTEN.assert_called_with(channel)

    def test_get_receives_ERR(self):
        p, channel = self.create_get(events=[(1, eventio.ERR)])
        p._fd_to_chan[1] = (channel, 'BRPOP')

        with self.assertRaises(redis.Empty):
            p.get()

        channel._poll_error.assert_called_with('BRPOP')

    def test_get_receives_multiple(self):
        p, channel = self.create_get(events=[(1, eventio.ERR),
                                             (1, eventio.ERR)])
        p._fd_to_chan[1] = (channel, 'BRPOP')

        with self.assertRaises(redis.Empty):
            p.get()

        channel._poll_error.assert_called_with('BRPOP')


class test_Mutex(Case):

    @skip_if_not_module('redis')
    def test_mutex(self, lock_id='xxx'):
        client = Mock(name='client')
        with patch('kombu.transport.redis.uuid') as uuid:
            # Won
            uuid.return_value = lock_id
            client.setnx.return_value = True
            pipe = client.pipeline.return_value = Mock(name='pipe')
            pipe.get.return_value = lock_id
            held = False
            with redis.Mutex(client, 'foo1', 100):
                held = True
            self.assertTrue(held)
            client.setnx.assert_called_with('foo1', lock_id)
            pipe.get.return_value = 'yyy'
            held = False
            with redis.Mutex(client, 'foo1', 100):
                held = True
            self.assertTrue(held)

            # Did not win
            client.expire.reset_mock()
            pipe.get.return_value = lock_id
            client.setnx.return_value = False
            with self.assertRaises(redis.MutexHeld):
                held = False
                with redis.Mutex(client, 'foo1', '100'):
                    held = True
                self.assertFalse(held)
            client.ttl.return_value = 0
            with self.assertRaises(redis.MutexHeld):
                held = False
                with redis.Mutex(client, 'foo1', '100'):
                    held = True
                self.assertFalse(held)
            self.assertTrue(client.expire.called)

            # Wins but raises WatchError (and that is ignored)
            client.setnx.return_value = True
            pipe.watch.side_effect = redis.redis.WatchError()
            held = False
            with redis.Mutex(client, 'foo1', 100):
                held = True
            self.assertTrue(held)

########NEW FILE########
__FILENAME__ = test_sqlalchemy
from __future__ import absolute_import

from kombu import Connection
from kombu.tests.case import Case, SkipTest, patch


class test_sqlalchemy(Case):

    def setUp(self):
        try:
            import sqlalchemy  # noqa
        except ImportError:
            raise SkipTest('sqlalchemy not installed')

    def test_url_parser(self):
        with patch('kombu.transport.sqlalchemy.Channel._open'):
            url = 'sqlalchemy+sqlite:///celerydb.sqlite'
            Connection(url).connect()

            url = 'sqla+sqlite:///celerydb.sqlite'
            Connection(url).connect()

            # Should prevent regression fixed by f187ccd
            url = 'sqlb+sqlite:///celerydb.sqlite'
            with self.assertRaises(KeyError):
                Connection(url).connect()

    def test_simple_queueing(self):
        conn = Connection('sqlalchemy+sqlite:///:memory:')
        conn.connect()
        channel = conn.channel()
        self.assertEqual(
            channel.queue_cls.__table__.name,
            'kombu_queue'
        )
        self.assertEqual(
            channel.message_cls.__table__.name,
            'kombu_message'
        )
        channel._put('celery', 'DATA')
        assert channel._get('celery') == 'DATA'

    def test_custom_table_names(self):
        raise SkipTest('causes global side effect')
        conn = Connection('sqlalchemy+sqlite:///:memory:', transport_options={
            'queue_tablename': 'my_custom_queue',
            'message_tablename': 'my_custom_message'
        })
        conn.connect()
        channel = conn.channel()
        self.assertEqual(
            channel.queue_cls.__table__.name,
            'my_custom_queue'
        )
        self.assertEqual(
            channel.message_cls.__table__.name,
            'my_custom_message'
        )
        channel._put('celery', 'DATA')
        assert channel._get('celery') == 'DATA'

    def test_clone(self):
        hostname = 'sqlite:///celerydb.sqlite'
        x = Connection('+'.join(['sqla', hostname]))
        self.assertEqual(x.uri_prefix, 'sqla')
        self.assertEqual(x.hostname, hostname)
        clone = x.clone()
        self.assertEqual(clone.hostname, hostname)
        self.assertEqual(clone.uri_prefix, 'sqla')

########NEW FILE########
__FILENAME__ = test_SQS
"""Testing module for the kombu.transport.SQS package.

NOTE: The SQSQueueMock and SQSConnectionMock classes originally come from
http://github.com/pcsforeducation/sqs-mock-python. They have been patched
slightly.
"""

from __future__ import absolute_import

from kombu import Connection
from kombu import messaging
from kombu import five
from kombu.tests.case import Case, SkipTest
import kombu

try:
    from kombu.transport import SQS
except ImportError:
    # Boto must not be installed if the SQS transport fails to import,
    # so we skip all unit tests. Set SQS to None here, and it will be
    # checked during the setUp() phase later.
    SQS = None


class SQSQueueMock(object):

    def __init__(self, name):
        self.name = name
        self.messages = []
        self._get_message_calls = 0

    def clear(self, page_size=10, vtimeout=10):
        empty, self.messages[:] = not self.messages, []
        return not empty

    def count(self, page_size=10, vtimeout=10):
        return len(self.messages)
    count_slow = count

    def delete(self):
        self.messages[:] = []
        return True

    def delete_message(self, message):
        try:
            self.messages.remove(message)
        except ValueError:
            return False
        return True

    def get_messages(self, num_messages=1, visibility_timeout=None,
                     attributes=None, *args, **kwargs):
        self._get_message_calls += 1
        return self.messages[:num_messages]

    def read(self, visibility_timeout=None):
        return self.messages.pop(0)

    def write(self, message):
        self.messages.append(message)
        return True


class SQSConnectionMock(object):

    def __init__(self):
        self.queues = {}

    def get_queue(self, queue):
        return self.queues.get(queue)

    def get_all_queues(self, prefix=""):
        return self.queues.values()

    def delete_queue(self, queue, force_deletion=False):
        q = self.get_queue(queue)
        if q:
            if q.count():
                return False
            q.clear()
            self.queues.pop(queue, None)

    def delete_message(self, queue, message):
        return queue.delete_message(message)

    def create_queue(self, name, *args, **kwargs):
        q = self.queues[name] = SQSQueueMock(name)
        return q


class test_Channel(Case):

    def handleMessageCallback(self, message):
        self.callback_message = message

    def setUp(self):
        """Mock the back-end SQS classes"""
        # Sanity check... if SQS is None, then it did not import and we
        # cannot execute our tests.
        if SQS is None:
            raise SkipTest('Boto is not installed')

        SQS.Channel._queue_cache.clear()

        # Common variables used in the unit tests
        self.queue_name = 'unittest'

        # Mock the sqs() method that returns an SQSConnection object and
        # instead return an SQSConnectionMock() object.
        self.sqs_conn_mock = SQSConnectionMock()

        def mock_sqs():
            return self.sqs_conn_mock
        SQS.Channel.sqs = mock_sqs()

        # Set up a task exchange for passing tasks through the queue
        self.exchange = kombu.Exchange('test_SQS', type='direct')
        self.queue = kombu.Queue(self.queue_name,
                                 self.exchange,
                                 self.queue_name)

        # Mock up a test SQS Queue with the SQSQueueMock class (and always
        # make sure its a clean empty queue)
        self.sqs_queue_mock = SQSQueueMock(self.queue_name)

        # Now, create our Connection object with the SQS Transport and store
        # the connection/channel objects as references for use in these tests.
        self.connection = Connection(transport=SQS.Transport)
        self.channel = self.connection.channel()

        self.queue(self.channel).declare()
        self.producer = messaging.Producer(self.channel,
                                           self.exchange,
                                           routing_key=self.queue_name)

        # Lastly, make sure that we're set up to 'consume' this queue.
        self.channel.basic_consume(self.queue_name,
                                   no_ack=True,
                                   callback=self.handleMessageCallback,
                                   consumer_tag='unittest')

    def test_init(self):
        """kombu.SQS.Channel instantiates correctly with mocked queues"""
        self.assertIn(self.queue_name, self.channel._queue_cache)

    def test_new_queue(self):
        queue_name = 'new_unittest_queue'
        self.channel._new_queue(queue_name)
        self.assertIn(queue_name, self.sqs_conn_mock.queues)
        # For cleanup purposes, delete the queue and the queue file
        self.channel._delete(queue_name)

    def test_delete(self):
        queue_name = 'new_unittest_queue'
        self.channel._new_queue(queue_name)
        self.channel._delete(queue_name)
        self.assertNotIn(queue_name, self.channel._queue_cache)

    def test_get_from_sqs(self):
        # Test getting a single message
        message = 'my test message'
        self.producer.publish(message)
        results = self.channel._get_from_sqs(self.queue_name)
        self.assertEquals(len(results), 1)

        # Now test getting many messages
        for i in xrange(3):
            message = 'message: {0}'.format(i)
            self.producer.publish(message)

        results = self.channel._get_from_sqs(self.queue_name, count=3)
        self.assertEquals(len(results), 3)

    def test_get_with_empty_list(self):
        with self.assertRaises(five.Empty):
            self.channel._get(self.queue_name)

    def test_get_bulk_raises_empty(self):
        with self.assertRaises(five.Empty):
            self.channel._get_bulk(self.queue_name)

    def test_messages_to_python(self):
        message_count = 3
        # Create several test messages and publish them
        for i in range(message_count):
            message = 'message: %s' % i
            self.producer.publish(message)

        # Get the messages now
        messages = self.channel._get_from_sqs(
            self.queue_name, count=message_count,
        )

        # Now convert them to payloads
        payloads = self.channel._messages_to_python(
            messages, self.queue_name,
        )

        # We got the same number of payloads back, right?
        self.assertEquals(len(payloads), message_count)

        # Make sure they're payload-style objects
        for p in payloads:
            self.assertTrue('properties' in p)

    def test_put_and_get(self):
        message = 'my test message'
        self.producer.publish(message)
        results = self.queue(self.channel).get().payload
        self.assertEquals(message, results)

    def test_puts_and_gets(self):
        for i in xrange(3):
            message = 'message: %s' % i
            self.producer.publish(message)

        for i in xrange(3):
            self.assertEquals('message: %s' % i,
                              self.queue(self.channel).get().payload)

    def test_put_and_get_bulk(self):
        # With QoS.prefetch_count = 0
        message = 'my test message'
        self.producer.publish(message)
        results = self.channel._get_bulk(self.queue_name)
        self.assertEquals(1, len(results))

    def test_puts_and_get_bulk(self):
        # Generate 8 messages
        message_count = 8

        # Set the prefetch_count to 5
        self.channel.qos.prefetch_count = 5

        # Now, generate all the messages
        for i in xrange(message_count):
            message = 'message: %s' % i
            self.producer.publish(message)

        # Count how many messages are retrieved the first time. Should
        # be 5 (message_count).
        results = self.channel._get_bulk(self.queue_name)
        self.assertEquals(5, len(results))

        # Now, do the get again, the number of messages returned should be 3.
        results = self.channel._get_bulk(self.queue_name)
        self.assertEquals(3, len(results))

    def test_drain_events_with_empty_list(self):
        def mock_can_consume():
            return False
        self.channel.qos.can_consume = mock_can_consume
        with self.assertRaises(five.Empty):
            self.channel.drain_events()

    def test_drain_events_with_prefetch_5(self):
        # Generate 20 messages
        message_count = 20
        expected_get_message_count = 4

        # Set the prefetch_count to 5
        self.channel.qos.prefetch_count = 5

        # Now, generate all the messages
        for i in xrange(message_count):
            self.producer.publish('message: %s' % i)

        # Now drain all the events
        for i in xrange(message_count):
            self.channel.drain_events()

        # How many times was the SQSConnectionMock get_message method called?
        self.assertEquals(
            expected_get_message_count,
            self.channel._queue_cache[self.queue_name]._get_message_calls)

    def test_drain_events_with_prefetch_none(self):
        # Generate 20 messages
        message_count = 20
        expected_get_message_count = 2

        # Set the prefetch_count to None
        self.channel.qos.prefetch_count = None

        # Now, generate all the messages
        for i in xrange(message_count):
            self.producer.publish('message: %s' % i)

        # Now drain all the events
        for i in xrange(message_count):
            self.channel.drain_events()

        # How many times was the SQSConnectionMock get_message method called?
        self.assertEquals(
            expected_get_message_count,
            self.channel._queue_cache[self.queue_name]._get_message_calls)

########NEW FILE########
__FILENAME__ = test_transport
from __future__ import absolute_import

from kombu import transport

from kombu.tests.case import Case, Mock, patch


class test_supports_librabbitmq(Case):

    def test_eventlet(self):
        with patch('kombu.transport._detect_environment') as de:
            de.return_value = 'eventlet'
            self.assertFalse(transport.supports_librabbitmq())


class test_transport(Case):

    def test_resolve_transport(self):
        from kombu.transport.memory import Transport
        self.assertIs(transport.resolve_transport(
            'kombu.transport.memory:Transport'),
            Transport)
        self.assertIs(transport.resolve_transport(Transport), Transport)

    def test_resolve_transport_alias_callable(self):
        m = transport.TRANSPORT_ALIASES['George'] = Mock(name='lazyalias')
        try:
            transport.resolve_transport('George')
            m.assert_called_with()
        finally:
            transport.TRANSPORT_ALIASES.pop('George')

    def test_resolve_transport_alias(self):
        self.assertTrue(transport.resolve_transport('pyamqp'))


class test_transport_ghettoq(Case):

    @patch('warnings.warn')
    def test_compat(self, warn):
        x = transport._ghettoq('Redis', 'redis', 'redis')

        self.assertEqual(x(), 'kombu.transport.redis.Transport')
        self.assertTrue(warn.called)

########NEW FILE########
__FILENAME__ = test_base
from __future__ import absolute_import

import sys
import warnings

from kombu import Connection
from kombu.exceptions import ResourceError, ChannelError
from kombu.transport import virtual
from kombu.utils import uuid
from kombu.compression import compress

from kombu.tests.case import Case, Mock, patch, redirect_stdouts

PY3 = sys.version_info[0] == 3
PRINT_FQDN = 'builtins.print' if PY3 else '__builtin__.print'


def client(**kwargs):
    return Connection(transport='kombu.transport.virtual:Transport', **kwargs)


def memory_client():
    return Connection(transport='memory')


class test_BrokerState(Case):

    def test_constructor(self):
        s = virtual.BrokerState()
        self.assertTrue(hasattr(s, 'exchanges'))
        self.assertTrue(hasattr(s, 'bindings'))

        t = virtual.BrokerState(exchanges=16, bindings=32)
        self.assertEqual(t.exchanges, 16)
        self.assertEqual(t.bindings, 32)


class test_QoS(Case):

    def setUp(self):
        self.q = virtual.QoS(client().channel(), prefetch_count=10)

    def tearDown(self):
        self.q._on_collect.cancel()

    def test_constructor(self):
        self.assertTrue(self.q.channel)
        self.assertTrue(self.q.prefetch_count)
        self.assertFalse(self.q._delivered.restored)
        self.assertTrue(self.q._on_collect)

    @redirect_stdouts
    def test_can_consume(self, stdout, stderr):
        _restored = []

        class RestoreChannel(virtual.Channel):
            do_restore = True

            def _restore(self, message):
                _restored.append(message)

        self.assertTrue(self.q.can_consume())
        for i in range(self.q.prefetch_count - 1):
            self.q.append(i, uuid())
            self.assertTrue(self.q.can_consume())
        self.q.append(i + 1, uuid())
        self.assertFalse(self.q.can_consume())

        tag1 = next(iter(self.q._delivered))
        self.q.ack(tag1)
        self.assertTrue(self.q.can_consume())

        tag2 = uuid()
        self.q.append(i + 2, tag2)
        self.assertFalse(self.q.can_consume())
        self.q.reject(tag2)
        self.assertTrue(self.q.can_consume())

        self.q.channel = RestoreChannel(self.q.channel.connection)
        tag3 = uuid()
        self.q.append(i + 3, tag3)
        self.q.reject(tag3, requeue=True)
        self.q._flush()
        self.q.restore_unacked_once()
        self.assertListEqual(_restored, [11, 9, 8, 7, 6, 5, 4, 3, 2, 1])
        self.assertTrue(self.q._delivered.restored)
        self.assertFalse(self.q._delivered)

        self.q.restore_unacked_once()
        self.q._delivered.restored = False
        self.q.restore_unacked_once()

        self.assertTrue(stderr.getvalue())
        self.assertFalse(stdout.getvalue())

        self.q.restore_at_shutdown = False
        self.q.restore_unacked_once()

    def test_get(self):
        self.q._delivered['foo'] = 1
        self.assertEqual(self.q.get('foo'), 1)


class test_Message(Case):

    def test_create(self):
        c = client().channel()
        data = c.prepare_message('the quick brown fox...')
        tag = data['properties']['delivery_tag'] = uuid()
        message = c.message_to_python(data)
        self.assertIsInstance(message, virtual.Message)
        self.assertIs(message, c.message_to_python(message))
        if message.errors:
            message._reraise_error()

        self.assertEqual(message.body,
                         'the quick brown fox...'.encode('utf-8'))
        self.assertTrue(message.delivery_tag, tag)

    def test_create_no_body(self):
        virtual.Message(Mock(), {
            'body': None,
            'properties': {'delivery_tag': 1}})

    def test_serializable(self):
        c = client().channel()
        body, content_type = compress('the quick brown fox...', 'gzip')
        data = c.prepare_message(body, headers={'compression': content_type})
        tag = data['properties']['delivery_tag'] = uuid()
        message = c.message_to_python(data)
        dict_ = message.serializable()
        self.assertEqual(dict_['body'],
                         'the quick brown fox...'.encode('utf-8'))
        self.assertEqual(dict_['properties']['delivery_tag'], tag)
        self.assertFalse('compression' in dict_['headers'])


class test_AbstractChannel(Case):

    def test_get(self):
        with self.assertRaises(NotImplementedError):
            virtual.AbstractChannel()._get('queue')

    def test_put(self):
        with self.assertRaises(NotImplementedError):
            virtual.AbstractChannel()._put('queue', 'm')

    def test_size(self):
        self.assertEqual(virtual.AbstractChannel()._size('queue'), 0)

    def test_purge(self):
        with self.assertRaises(NotImplementedError):
            virtual.AbstractChannel()._purge('queue')

    def test_delete(self):
        with self.assertRaises(NotImplementedError):
            virtual.AbstractChannel()._delete('queue')

    def test_new_queue(self):
        self.assertIsNone(virtual.AbstractChannel()._new_queue('queue'))

    def test_has_queue(self):
        self.assertTrue(virtual.AbstractChannel()._has_queue('queue'))

    def test_poll(self):

        class Cycle(object):
            called = False

            def get(self):
                self.called = True
                return True

        cycle = Cycle()
        self.assertTrue(virtual.AbstractChannel()._poll(cycle))
        self.assertTrue(cycle.called)


class test_Channel(Case):

    def setUp(self):
        self.channel = client().channel()

    def tearDown(self):
        if self.channel._qos is not None:
            self.channel._qos._on_collect.cancel()

    def test_exceeds_channel_max(self):
        c = client()
        t = c.transport
        avail = t._avail_channel_ids = Mock(name='_avail_channel_ids')
        avail.pop.side_effect = IndexError()
        with self.assertRaises(ResourceError):
            virtual.Channel(t)

    def test_exchange_bind_interface(self):
        with self.assertRaises(NotImplementedError):
            self.channel.exchange_bind('dest', 'src', 'key')

    def test_exchange_unbind_interface(self):
        with self.assertRaises(NotImplementedError):
            self.channel.exchange_unbind('dest', 'src', 'key')

    def test_queue_unbind_interface(self):
        with self.assertRaises(NotImplementedError):
            self.channel.queue_unbind('dest', 'ex', 'key')

    def test_management(self):
        m = self.channel.connection.client.get_manager()
        self.assertTrue(m)
        m.get_bindings()
        m.close()

    def test_exchange_declare(self):
        c = self.channel

        with self.assertRaises(ChannelError):
            c.exchange_declare('test_exchange_declare', 'direct',
                               durable=True, auto_delete=True, passive=True)
        c.exchange_declare('test_exchange_declare', 'direct',
                           durable=True, auto_delete=True)
        c.exchange_declare('test_exchange_declare', 'direct',
                           durable=True, auto_delete=True, passive=True)
        self.assertIn('test_exchange_declare', c.state.exchanges)
        # can declare again with same values
        c.exchange_declare('test_exchange_declare', 'direct',
                           durable=True, auto_delete=True)
        self.assertIn('test_exchange_declare', c.state.exchanges)

        # using different values raises NotEquivalentError
        with self.assertRaises(virtual.NotEquivalentError):
            c.exchange_declare('test_exchange_declare', 'direct',
                               durable=False, auto_delete=True)

    def test_exchange_delete(self, ex='test_exchange_delete'):

        class PurgeChannel(virtual.Channel):
            purged = []

            def _purge(self, queue):
                self.purged.append(queue)

        c = PurgeChannel(self.channel.connection)

        c.exchange_declare(ex, 'direct', durable=True, auto_delete=True)
        self.assertIn(ex, c.state.exchanges)
        self.assertNotIn(ex, c.state.bindings)  # no bindings yet
        c.exchange_delete(ex)
        self.assertNotIn(ex, c.state.exchanges)

        c.exchange_declare(ex, 'direct', durable=True, auto_delete=True)
        c.queue_declare(ex)
        c.queue_bind(ex, ex, ex)
        self.assertTrue(c.state.bindings[ex])
        c.exchange_delete(ex)
        self.assertNotIn(ex, c.state.bindings)
        self.assertIn(ex, c.purged)

    def test_queue_delete__if_empty(self, n='test_queue_delete__if_empty'):
        class PurgeChannel(virtual.Channel):
            purged = []
            size = 30

            def _purge(self, queue):
                self.purged.append(queue)

            def _size(self, queue):
                return self.size

        c = PurgeChannel(self.channel.connection)
        c.exchange_declare(n)
        c.queue_declare(n)
        c.queue_bind(n, n, n)
        # tests code path that returns if queue already bound.
        c.queue_bind(n, n, n)

        c.queue_delete(n, if_empty=True)
        self.assertIn(n, c.state.bindings)

        c.size = 0
        c.queue_delete(n, if_empty=True)
        self.assertNotIn(n, c.state.bindings)
        self.assertIn(n, c.purged)

    def test_queue_purge(self, n='test_queue_purge'):

        class PurgeChannel(virtual.Channel):
            purged = []

            def _purge(self, queue):
                self.purged.append(queue)

        c = PurgeChannel(self.channel.connection)
        c.exchange_declare(n)
        c.queue_declare(n)
        c.queue_bind(n, n, n)
        c.queue_purge(n)
        self.assertIn(n, c.purged)

    def test_basic_publish_unique_delivery_tags(self, n='test_uniq_tag'):
        c1 = memory_client().channel()
        c2 = memory_client().channel()

        for c in (c1, c2):
            c.exchange_declare(n)
            c.queue_declare(n)
            c.queue_bind(n, n, n)
        m1 = c1.prepare_message('George Costanza')
        m2 = c2.prepare_message('Elaine Marie Benes')
        c1.basic_publish(m1, n, n)
        c2.basic_publish(m2, n, n)

        r1 = c1.message_to_python(c1.basic_get(n))
        r2 = c2.message_to_python(c2.basic_get(n))

        self.assertNotEqual(r1.delivery_tag, r2.delivery_tag)
        with self.assertRaises(ValueError):
            int(r1.delivery_tag)
        with self.assertRaises(ValueError):
            int(r2.delivery_tag)

    def test_basic_publish__get__consume__restore(self,
                                                  n='test_basic_publish'):
        c = memory_client().channel()

        c.exchange_declare(n)
        c.queue_declare(n)
        c.queue_bind(n, n, n)
        c.queue_declare(n + '2')
        c.queue_bind(n + '2', n, n)

        m = c.prepare_message('nthex quick brown fox...')
        c.basic_publish(m, n, n)

        r1 = c.message_to_python(c.basic_get(n))
        self.assertTrue(r1)
        self.assertEqual(r1.body,
                         'nthex quick brown fox...'.encode('utf-8'))
        self.assertIsNone(c.basic_get(n))

        consumer_tag = uuid()

        c.basic_consume(n + '2', False,
                        consumer_tag=consumer_tag, callback=lambda *a: None)
        self.assertIn(n + '2', c._active_queues)
        r2, _ = c.drain_events()
        r2 = c.message_to_python(r2)
        self.assertEqual(r2.body,
                         'nthex quick brown fox...'.encode('utf-8'))
        self.assertEqual(r2.delivery_info['exchange'], n)
        self.assertEqual(r2.delivery_info['routing_key'], n)
        with self.assertRaises(virtual.Empty):
            c.drain_events()
        c.basic_cancel(consumer_tag)

        c._restore(r2)
        r3 = c.message_to_python(c.basic_get(n))
        self.assertTrue(r3)
        self.assertEqual(r3.body, 'nthex quick brown fox...'.encode('utf-8'))
        self.assertIsNone(c.basic_get(n))

    def test_basic_ack(self):

        class MockQoS(virtual.QoS):
            was_acked = False

            def ack(self, delivery_tag):
                self.was_acked = True

        self.channel._qos = MockQoS(self.channel)
        self.channel.basic_ack('foo')
        self.assertTrue(self.channel._qos.was_acked)

    def test_basic_recover__requeue(self):

        class MockQoS(virtual.QoS):
            was_restored = False

            def restore_unacked(self):
                self.was_restored = True

        self.channel._qos = MockQoS(self.channel)
        self.channel.basic_recover(requeue=True)
        self.assertTrue(self.channel._qos.was_restored)

    def test_restore_unacked_raises_BaseException(self):
        q = self.channel.qos
        q._flush = Mock()
        q._delivered = {1: 1}

        q.channel._restore = Mock()
        q.channel._restore.side_effect = SystemExit

        errors = q.restore_unacked()
        self.assertIsInstance(errors[0][0], SystemExit)
        self.assertEqual(errors[0][1], 1)
        self.assertFalse(q._delivered)

    @patch('kombu.transport.virtual.emergency_dump_state')
    @patch(PRINT_FQDN)
    def test_restore_unacked_once_when_unrestored(self, print_,
                                                  emergency_dump_state):
        q = self.channel.qos
        q._flush = Mock()

        class State(dict):
            restored = False

        q._delivered = State({1: 1})
        ru = q.restore_unacked = Mock()
        exc = None
        try:
            raise KeyError()
        except KeyError as exc_:
            exc = exc_
        ru.return_value = [(exc, 1)]

        self.channel.do_restore = True
        q.restore_unacked_once()
        self.assertTrue(print_.called)
        self.assertTrue(emergency_dump_state.called)

    def test_basic_recover(self):
        with self.assertRaises(NotImplementedError):
            self.channel.basic_recover(requeue=False)

    def test_basic_reject(self):

        class MockQoS(virtual.QoS):
            was_rejected = False

            def reject(self, delivery_tag, requeue=False):
                self.was_rejected = True

        self.channel._qos = MockQoS(self.channel)
        self.channel.basic_reject('foo')
        self.assertTrue(self.channel._qos.was_rejected)

    def test_basic_qos(self):
        self.channel.basic_qos(prefetch_count=128)
        self.assertEqual(self.channel._qos.prefetch_count, 128)

    def test_lookup__undeliverable(self, n='test_lookup__undeliverable'):
        warnings.resetwarnings()
        with warnings.catch_warnings(record=True) as log:
            self.assertListEqual(
                self.channel._lookup(n, n, 'ae.undeliver'),
                ['ae.undeliver'],
            )
            self.assertTrue(log)
            self.assertIn('could not be delivered', log[0].message.args[0])

    def test_context(self):
        x = self.channel.__enter__()
        self.assertIs(x, self.channel)
        x.__exit__()
        self.assertTrue(x.closed)

    def test_cycle_property(self):
        self.assertTrue(self.channel.cycle)

    def test_flow(self):
        with self.assertRaises(NotImplementedError):
            self.channel.flow(False)

    def test_close_when_no_connection(self):
        self.channel.connection = None
        self.channel.close()
        self.assertTrue(self.channel.closed)

    def test_drain_events_has_get_many(self):
        c = self.channel
        c._get_many = Mock()
        c._poll = Mock()
        c._consumers = [1]
        c._qos = Mock()
        c._qos.can_consume.return_value = True

        c.drain_events(timeout=10.0)
        c._get_many.assert_called_with(c._active_queues, timeout=10.0)

    def test_get_exchanges(self):
        self.channel.exchange_declare(exchange='foo')
        self.assertTrue(self.channel.get_exchanges())

    def test_basic_cancel_not_in_active_queues(self):
        c = self.channel
        c._consumers.add('x')
        c._tag_to_queue['x'] = 'foo'
        c._active_queues = Mock()
        c._active_queues.remove.side_effect = ValueError()

        c.basic_cancel('x')
        c._active_queues.remove.assert_called_with('foo')

    def test_basic_cancel_unknown_ctag(self):
        self.assertIsNone(self.channel.basic_cancel('unknown-tag'))

    def test_list_bindings(self):
        c = self.channel
        c.exchange_declare(exchange='foo')
        c.queue_declare(queue='q')
        c.queue_bind(queue='q', exchange='foo', routing_key='rk')

        self.assertIn(('q', 'foo', 'rk'), list(c.list_bindings()))

    def test_after_reply_message_received(self):
        c = self.channel
        c.queue_delete = Mock()
        c.after_reply_message_received('foo')
        c.queue_delete.assert_called_with('foo')

    def test_queue_delete_unknown_queue(self):
        self.assertIsNone(self.channel.queue_delete('xiwjqjwel'))

    def test_queue_declare_passive(self):
        has_queue = self.channel._has_queue = Mock()
        has_queue.return_value = False
        with self.assertRaises(ChannelError):
            self.channel.queue_declare(queue='21wisdjwqe', passive=True)

    def test_get_message_priority(self):

        def _message(priority):
            return self.channel.prepare_message(
                'the message with priority', priority=priority,
            )

        self.assertEqual(
            self.channel._get_message_priority(_message(5)), 5,
        )
        self.assertEqual(
            self.channel._get_message_priority(
                _message(self.channel.min_priority - 10),
            ),
            self.channel.min_priority,
        )
        self.assertEqual(
            self.channel._get_message_priority(
                _message(self.channel.max_priority + 10),
            ),
            self.channel.max_priority,
        )
        self.assertEqual(
            self.channel._get_message_priority(_message('foobar')),
            self.channel.default_priority,
        )
        self.assertEqual(
            self.channel._get_message_priority(_message(2), reverse=True),
            self.channel.max_priority - 2,
        )


class test_Transport(Case):

    def setUp(self):
        self.transport = client().transport

    def test_custom_polling_interval(self):
        x = client(transport_options=dict(polling_interval=32.3))
        self.assertEqual(x.transport.polling_interval, 32.3)

    def test_close_connection(self):
        c1 = self.transport.create_channel(self.transport)
        c2 = self.transport.create_channel(self.transport)
        self.assertEqual(len(self.transport.channels), 2)
        self.transport.close_connection(self.transport)
        self.assertFalse(self.transport.channels)
        del(c1)  # so pyflakes doesn't complain
        del(c2)

    def test_drain_channel(self):
        channel = self.transport.create_channel(self.transport)
        with self.assertRaises(virtual.Empty):
            self.transport._drain_channel(channel)

########NEW FILE########
__FILENAME__ = test_exchange
from __future__ import absolute_import

from kombu import Connection
from kombu.transport.virtual import exchange

from kombu.tests.case import Case, Mock
from kombu.tests.mocks import Transport


class ExchangeCase(Case):
    type = None

    def setUp(self):
        if self.type:
            self.e = self.type(Connection(transport=Transport).channel())


class test_Direct(ExchangeCase):
    type = exchange.DirectExchange
    table = [('rFoo', None, 'qFoo'),
             ('rFoo', None, 'qFox'),
             ('rBar', None, 'qBar'),
             ('rBaz', None, 'qBaz')]

    def test_lookup(self):
        self.assertListEqual(
            self.e.lookup(self.table, 'eFoo', 'rFoo', None),
            ['qFoo', 'qFox'],
        )
        self.assertListEqual(
            self.e.lookup(self.table, 'eMoz', 'rMoz', 'DEFAULT'),
            [],
        )
        self.assertListEqual(
            self.e.lookup(self.table, 'eBar', 'rBar', None),
            ['qBar'],
        )


class test_Fanout(ExchangeCase):
    type = exchange.FanoutExchange
    table = [(None, None, 'qFoo'),
             (None, None, 'qFox'),
             (None, None, 'qBar')]

    def test_lookup(self):
        self.assertListEqual(
            self.e.lookup(self.table, 'eFoo', 'rFoo', None),
            ['qFoo', 'qFox', 'qBar'],
        )

    def test_deliver_when_fanout_supported(self):
        self.e.channel = Mock()
        self.e.channel.supports_fanout = True
        message = Mock()

        self.e.deliver(message, 'exchange', 'rkey')
        self.e.channel._put_fanout.assert_called_with(
            'exchange', message, 'rkey',
        )

    def test_deliver_when_fanout_unsupported(self):
        self.e.channel = Mock()
        self.e.channel.supports_fanout = False

        self.e.deliver(Mock(), 'exchange', None)
        self.assertFalse(self.e.channel._put_fanout.called)


class test_Topic(ExchangeCase):
    type = exchange.TopicExchange
    table = [
        ('stock.#', None, 'rFoo'),
        ('stock.us.*', None, 'rBar'),
    ]

    def setUp(self):
        super(test_Topic, self).setUp()
        self.table = [(rkey, self.e.key_to_pattern(rkey), queue)
                      for rkey, _, queue in self.table]

    def test_prepare_bind(self):
        x = self.e.prepare_bind('qFoo', 'eFoo', 'stock.#', {})
        self.assertTupleEqual(x, ('stock.#', r'^stock\..*?$', 'qFoo'))

    def test_lookup(self):
        self.assertListEqual(
            self.e.lookup(self.table, 'eFoo', 'stock.us.nasdaq', None),
            ['rFoo', 'rBar'],
        )
        self.assertTrue(self.e._compiled)
        self.assertListEqual(
            self.e.lookup(self.table, 'eFoo', 'stock.europe.OSE', None),
            ['rFoo'],
        )
        self.assertListEqual(
            self.e.lookup(self.table, 'eFoo', 'stockxeuropexOSE', None),
            [],
        )
        self.assertListEqual(
            self.e.lookup(self.table, 'eFoo',
                          'candy.schleckpulver.snap_crackle', None),
            [],
        )

    def test_deliver(self):
        self.e.channel = Mock()
        self.e.channel._lookup.return_value = ('a', 'b')
        message = Mock()
        self.e.deliver(message, 'exchange', 'rkey')

        expected = [(('a', message), {}),
                    (('b', message), {})]
        self.assertListEqual(self.e.channel._put.call_args_list, expected)


class test_ExchangeType(ExchangeCase):
    type = exchange.ExchangeType

    def test_lookup(self):
        with self.assertRaises(NotImplementedError):
            self.e.lookup([], 'eFoo', 'rFoo', None)

    def test_prepare_bind(self):
        self.assertTupleEqual(
            self.e.prepare_bind('qFoo', 'eFoo', 'rFoo', {}),
            ('rFoo', None, 'qFoo'),
        )

    def test_equivalent(self):
        e1 = dict(
            type='direct',
            durable=True,
            auto_delete=True,
            arguments={},
        )
        self.assertTrue(
            self.e.equivalent(e1, 'eFoo', 'direct', True, True, {}),
        )
        self.assertFalse(
            self.e.equivalent(e1, 'eFoo', 'topic', True, True, {}),
        )
        self.assertFalse(
            self.e.equivalent(e1, 'eFoo', 'direct', False, True, {}),
        )
        self.assertFalse(
            self.e.equivalent(e1, 'eFoo', 'direct', True, False, {}),
        )
        self.assertFalse(
            self.e.equivalent(e1, 'eFoo', 'direct', True, True,
                              {'expires': 3000}),
        )
        e2 = dict(e1, arguments={'expires': 3000})
        self.assertTrue(
            self.e.equivalent(e2, 'eFoo', 'direct', True, True,
                              {'expires': 3000}),
        )
        self.assertFalse(
            self.e.equivalent(e2, 'eFoo', 'direct', True, True,
                              {'expires': 6000}),
        )

########NEW FILE########
__FILENAME__ = test_scheduling
from __future__ import absolute_import

from kombu.transport.virtual.scheduling import FairCycle

from kombu.tests.case import Case


class MyEmpty(Exception):
    pass


def consume(fun, n):
    r = []
    for i in range(n):
        r.append(fun())
    return r


class test_FairCycle(Case):

    def test_cycle(self):
        resources = ['a', 'b', 'c', 'd', 'e']

        def echo(r, timeout=None):
            return r

        # cycle should be ['a', 'b', 'c', 'd', 'e', ... repeat]
        cycle = FairCycle(echo, resources, MyEmpty)
        for i in range(len(resources)):
            self.assertEqual(cycle.get(), (resources[i],
                                           resources[i]))
        for i in range(len(resources)):
            self.assertEqual(cycle.get(), (resources[i],
                                           resources[i]))

    def test_cycle_breaks(self):
        resources = ['a', 'b', 'c', 'd', 'e']

        def echo(r):
            if r == 'c':
                raise MyEmpty(r)
            return r

        cycle = FairCycle(echo, resources, MyEmpty)
        self.assertEqual(
            consume(cycle.get, len(resources)),
            [('a', 'a'), ('b', 'b'), ('d', 'd'),
             ('e', 'e'), ('a', 'a')],
        )
        self.assertEqual(
            consume(cycle.get, len(resources)),
            [('b', 'b'), ('d', 'd'), ('e', 'e'),
             ('a', 'a'), ('b', 'b')],
        )
        cycle2 = FairCycle(echo, ['c', 'c'], MyEmpty)
        with self.assertRaises(MyEmpty):
            consume(cycle2.get, 3)

    def test_cycle_no_resources(self):
        cycle = FairCycle(None, [], MyEmpty)
        cycle.pos = 10

        with self.assertRaises(MyEmpty):
            cycle._next()

    def test__repr__(self):
        self.assertTrue(repr(FairCycle(lambda x: x, [1, 2, 3], MyEmpty)))

########NEW FILE########
__FILENAME__ = test_amq_manager
from __future__ import absolute_import

from kombu import Connection

from kombu.tests.case import Case, mask_modules, module_exists, patch


class test_get_manager(Case):

    @mask_modules('pyrabbit')
    def test_without_pyrabbit(self):
        with self.assertRaises(ImportError):
            Connection('amqp://').get_manager()

    @module_exists('pyrabbit')
    def test_with_pyrabbit(self):
        with patch('pyrabbit.Client', create=True) as Client:
            manager = Connection('amqp://').get_manager()
            self.assertIsNotNone(manager)
            Client.assert_called_with(
                'localhost:15672', 'guest', 'guest',
            )

    @module_exists('pyrabbit')
    def test_transport_options(self):
        with patch('pyrabbit.Client', create=True) as Client:
            manager = Connection('amqp://', transport_options={
                'manager_hostname': 'admin.mq.vandelay.com',
                'manager_port': 808,
                'manager_userid': 'george',
                'manager_password': 'bosco',
            }).get_manager()
            self.assertIsNotNone(manager)
            Client.assert_called_with(
                'admin.mq.vandelay.com:808', 'george', 'bosco',
            )

########NEW FILE########
__FILENAME__ = test_debug
from __future__ import absolute_import

import logging

from kombu.utils.debug import (
    setup_logging,
    Logwrapped,
)
from kombu.tests.case import Case, Mock, patch


class test_setup_logging(Case):

    def test_adds_handlers_sets_level(self):
        with patch('kombu.utils.debug.get_logger') as get_logger:
            logger = get_logger.return_value = Mock()
            setup_logging(loggers=['kombu.test'])

            get_logger.assert_called_with('kombu.test')

            self.assertTrue(logger.addHandler.called)
            logger.setLevel.assert_called_with(logging.DEBUG)


class test_Logwrapped(Case):

    def test_wraps(self):
        with patch('kombu.utils.debug.get_logger') as get_logger:
            logger = get_logger.return_value = Mock()

            W = Logwrapped(Mock(), 'kombu.test')
            get_logger.assert_called_with('kombu.test')
            self.assertIsNotNone(W.instance)
            self.assertIs(W.logger, logger)

            W.instance.__repr__ = lambda s: 'foo'
            self.assertEqual(repr(W), 'foo')
            W.instance.some_attr = 303
            self.assertEqual(W.some_attr, 303)

            W.instance.some_method.__name__ = 'some_method'
            W.some_method(1, 2, kw=1)
            W.instance.some_method.assert_called_with(1, 2, kw=1)

            W.some_method()
            W.instance.some_method.assert_called_with()

            W.some_method(kw=1)
            W.instance.some_method.assert_called_with(kw=1)

            W.ident = 'ident'
            W.some_method(kw=1)
            self.assertTrue(logger.debug.called)
            self.assertIn('ident', logger.debug.call_args[0][0])

            self.assertEqual(dir(W), dir(W.instance))

########NEW FILE########
__FILENAME__ = test_encoding
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import sys

from contextlib import contextmanager

from kombu.five import bytes_t, string_t
from kombu.utils.encoding import safe_str, default_encoding

from kombu.tests.case import Case, SkipTest, patch


@contextmanager
def clean_encoding():
    old_encoding = sys.modules.pop('kombu.utils.encoding', None)
    import kombu.utils.encoding
    try:
        yield kombu.utils.encoding
    finally:
        if old_encoding:
            sys.modules['kombu.utils.encoding'] = old_encoding


class test_default_encoding(Case):

    @patch('sys.getfilesystemencoding')
    def test_default(self, getdefaultencoding):
        getdefaultencoding.return_value = 'ascii'
        with clean_encoding() as encoding:
            enc = encoding.default_encoding()
            if sys.platform.startswith('java'):
                self.assertEqual(enc, 'utf-8')
            else:
                self.assertEqual(enc, 'ascii')
                getdefaultencoding.assert_called_with()


class test_encoding_utils(Case):

    def setUp(self):
        if sys.version_info >= (3, 0):
            raise SkipTest('not relevant on py3k')

    def test_str_to_bytes(self):
        with clean_encoding() as e:
            self.assertIsInstance(e.str_to_bytes('foobar'), bytes_t)

    def test_from_utf8(self):
        with clean_encoding() as e:
            self.assertIsInstance(e.from_utf8('foobar'), bytes_t)

    def test_default_encode(self):
        with clean_encoding() as e:
            self.assertTrue(e.default_encode(b'foo'))


class test_safe_str(Case):

    def setUp(self):
        self._cencoding = patch('sys.getfilesystemencoding')
        self._encoding = self._cencoding.__enter__()
        self._encoding.return_value = 'ascii'

    def tearDown(self):
        self._cencoding.__exit__()

    def test_when_bytes(self):
        self.assertEqual(safe_str('foo'), 'foo')

    def test_when_unicode(self):
        self.assertIsInstance(safe_str('foo'), string_t)

    def test_when_encoding_utf8(self):
        with patch('sys.getfilesystemencoding') as encoding:
            encoding.return_value = 'utf-8'
            self.assertEqual(default_encoding(), 'utf-8')
            s = 'The quiæk fåx jømps øver the lazy dåg'
            res = safe_str(s)
            self.assertIsInstance(res, str)

    def test_when_containing_high_chars(self):
        with patch('sys.getfilesystemencoding') as encoding:
            encoding.return_value = 'ascii'
            s = 'The quiæk fåx jømps øver the lazy dåg'
            res = safe_str(s)
            self.assertIsInstance(res, str)
            self.assertEqual(len(s), len(res))

    def test_when_not_string(self):
        o = object()
        self.assertEqual(safe_str(o), repr(o))

    def test_when_unrepresentable(self):

        class O(object):

            def __repr__(self):
                raise KeyError('foo')

        self.assertIn('<Unrepresentable', safe_str(O()))

########NEW FILE########
__FILENAME__ = test_functional
from __future__ import absolute_import

import pickle
import sys

from kombu.utils.functional import lazy, maybe_evaluate

from kombu.tests.case import Case, SkipTest


def double(x):
    return x * 2


class test_lazy(Case):

    def test__str__(self):
        self.assertEqual(
            str(lazy(lambda: 'the quick brown fox')),
            'the quick brown fox',
        )

    def test__repr__(self):
        self.assertEqual(
            repr(lazy(lambda: 'fi fa fo')),
            "'fi fa fo'",
        )

    def test__cmp__(self):
        if sys.version_info[0] == 3:
            raise SkipTest('irrelevant on py3')

        self.assertEqual(lazy(lambda: 10).__cmp__(lazy(lambda: 20)), -1)
        self.assertEqual(lazy(lambda: 10).__cmp__(5), 1)

    def test_evaluate(self):
        self.assertEqual(lazy(lambda: 2 + 2)(), 4)
        self.assertEqual(lazy(lambda x: x * 4, 2), 8)
        self.assertEqual(lazy(lambda x: x * 8, 2)(), 16)

    def test_cmp(self):
        self.assertEqual(lazy(lambda: 10), lazy(lambda: 10))
        self.assertNotEqual(lazy(lambda: 10), lazy(lambda: 20))

    def test__reduce__(self):
        x = lazy(double, 4)
        y = pickle.loads(pickle.dumps(x))
        self.assertEqual(x(), y())

    def test__deepcopy__(self):
        from copy import deepcopy
        x = lazy(double, 4)
        y = deepcopy(x)
        self.assertEqual(x._fun, y._fun)
        self.assertEqual(x._args, y._args)
        self.assertEqual(x(), y())


class test_maybe_evaluate(Case):

    def test_evaluates(self):
        self.assertEqual(maybe_evaluate(lazy(lambda: 10)), 10)
        self.assertEqual(maybe_evaluate(20), 20)

########NEW FILE########
__FILENAME__ = test_utils
from __future__ import absolute_import
from __future__ import unicode_literals

import pickle
import sys

from functools import wraps
from io import StringIO, BytesIO

from kombu import version_info_t
from kombu import utils
from kombu.utils.text import version_string_as_tuple
from kombu.five import string_t

from kombu.tests.case import (
    Case, Mock, patch,
    redirect_stdouts, mask_modules, module_exists, skip_if_module,
)


class OldString(object):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def split(self, *args, **kwargs):
        return self.value.split(*args, **kwargs)

    def rsplit(self, *args, **kwargs):
        return self.value.rsplit(*args, **kwargs)


class test_kombu_module(Case):

    def test_dir(self):
        import kombu
        self.assertTrue(dir(kombu))


class test_utils(Case):

    def test_maybe_list(self):
        self.assertEqual(utils.maybe_list(None), [])
        self.assertEqual(utils.maybe_list(1), [1])
        self.assertEqual(utils.maybe_list([1, 2, 3]), [1, 2, 3])

    def test_fxrange_no_repeatlast(self):
        self.assertEqual(list(utils.fxrange(1.0, 3.0, 1.0)),
                         [1.0, 2.0, 3.0])

    def test_fxrangemax(self):
        self.assertEqual(list(utils.fxrangemax(1.0, 3.0, 1.0, 30.0)),
                         [1.0, 2.0, 3.0, 3.0, 3.0, 3.0,
                          3.0, 3.0, 3.0, 3.0, 3.0])
        self.assertEqual(list(utils.fxrangemax(1.0, None, 1.0, 30.0)),
                         [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])

    def test_reprkwargs(self):
        self.assertTrue(utils.reprkwargs({'foo': 'bar', 1: 2, 'k': 'v'}))

    def test_reprcall(self):
        self.assertTrue(
            utils.reprcall('add', (2, 2), {'copy': True}),
        )


class test_UUID(Case):

    def test_uuid4(self):
        self.assertNotEqual(utils.uuid4(),
                            utils.uuid4())

    def test_uuid(self):
        i1 = utils.uuid()
        i2 = utils.uuid()
        self.assertIsInstance(i1, str)
        self.assertNotEqual(i1, i2)

    @skip_if_module('__pypy__')
    def test_uuid_without_ctypes(self):
        old_utils = sys.modules.pop('kombu.utils')

        @mask_modules('ctypes')
        def with_ctypes_masked():
            from kombu.utils import ctypes, uuid

            self.assertIsNone(ctypes)
            tid = uuid()
            self.assertTrue(tid)
            self.assertIsInstance(tid, string_t)

        try:
            with_ctypes_masked()
        finally:
            sys.modules['celery.utils'] = old_utils


class MyStringIO(StringIO):

    def close(self):
        pass


class MyBytesIO(BytesIO):

    def close(self):
        pass


class test_emergency_dump_state(Case):

    @redirect_stdouts
    def test_dump(self, stdout, stderr):
        fh = MyBytesIO()

        utils.emergency_dump_state({'foo': 'bar'}, open_file=lambda n, m: fh)
        self.assertDictEqual(pickle.loads(fh.getvalue()), {'foo': 'bar'})
        self.assertTrue(stderr.getvalue())
        self.assertFalse(stdout.getvalue())

    @redirect_stdouts
    def test_dump_second_strategy(self, stdout, stderr):
        fh = MyStringIO()

        def raise_something(*args, **kwargs):
            raise KeyError('foo')

        utils.emergency_dump_state(
            {'foo': 'bar'},
            open_file=lambda n, m: fh, dump=raise_something
        )
        self.assertIn('foo', fh.getvalue())
        self.assertIn('bar', fh.getvalue())
        self.assertTrue(stderr.getvalue())
        self.assertFalse(stdout.getvalue())


def insomnia(fun):

    @wraps(fun)
    def _inner(*args, **kwargs):
        def mysleep(i):
            pass

        prev_sleep = utils.sleep
        utils.sleep = mysleep
        try:
            return fun(*args, **kwargs)
        finally:
            utils.sleep = prev_sleep

    return _inner


class test_retry_over_time(Case):

    def setUp(self):
        self.index = 0

    class Predicate(Exception):
        pass

    def myfun(self):
        if self.index < 9:
            raise self.Predicate()
        return 42

    def errback(self, exc, intervals, retries):
        interval = next(intervals)
        sleepvals = (None, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 16.0)
        self.index += 1
        self.assertEqual(interval, sleepvals[self.index])
        return interval

    @insomnia
    def test_simple(self):
        prev_count, utils.count = utils.count, Mock()
        try:
            utils.count.return_value = list(range(1))
            x = utils.retry_over_time(self.myfun, self.Predicate,
                                      errback=None, interval_max=14)
            self.assertIsNone(x)
            utils.count.return_value = list(range(10))
            cb = Mock()
            x = utils.retry_over_time(self.myfun, self.Predicate,
                                      errback=self.errback, callback=cb,
                                      interval_max=14)
            self.assertEqual(x, 42)
            self.assertEqual(self.index, 9)
            cb.assert_called_with()
        finally:
            utils.count = prev_count

    @insomnia
    def test_retry_once(self):
        with self.assertRaises(self.Predicate):
            utils.retry_over_time(
                self.myfun, self.Predicate,
                max_retries=1, errback=self.errback, interval_max=14,
            )
        self.assertEqual(self.index, 1)
        # no errback
        with self.assertRaises(self.Predicate):
            utils.retry_over_time(
                self.myfun, self.Predicate,
                max_retries=1, errback=None, interval_max=14,
            )

    @insomnia
    def test_retry_always(self):
        Predicate = self.Predicate

        class Fun(object):

            def __init__(self):
                self.calls = 0

            def __call__(self, *args, **kwargs):
                try:
                    if self.calls >= 10:
                        return 42
                    raise Predicate()
                finally:
                    self.calls += 1
        fun = Fun()

        self.assertEqual(
            utils.retry_over_time(
                fun, self.Predicate,
                max_retries=0, errback=None, interval_max=14,
            ),
            42,
        )
        self.assertEqual(fun.calls, 11)


class test_cached_property(Case):

    def test_deleting(self):

        class X(object):
            xx = False

            @utils.cached_property
            def foo(self):
                return 42

            @foo.deleter  # noqa
            def foo(self, value):
                self.xx = value

        x = X()
        del(x.foo)
        self.assertFalse(x.xx)
        x.__dict__['foo'] = 'here'
        del(x.foo)
        self.assertEqual(x.xx, 'here')

    def test_when_access_from_class(self):

        class X(object):
            xx = None

            @utils.cached_property
            def foo(self):
                return 42

            @foo.setter  # noqa
            def foo(self, value):
                self.xx = 10

        desc = X.__dict__['foo']
        self.assertIs(X.foo, desc)

        self.assertIs(desc.__get__(None), desc)
        self.assertIs(desc.__set__(None, 1), desc)
        self.assertIs(desc.__delete__(None), desc)
        self.assertTrue(desc.setter(1))

        x = X()
        x.foo = 30
        self.assertEqual(x.xx, 10)

        del(x.foo)


class test_symbol_by_name(Case):

    def test_instance_returns_instance(self):
        instance = object()
        self.assertIs(utils.symbol_by_name(instance), instance)

    def test_returns_default(self):
        default = object()
        self.assertIs(
            utils.symbol_by_name('xyz.ryx.qedoa.weq:foz', default=default),
            default,
        )

    def test_no_default(self):
        with self.assertRaises(ImportError):
            utils.symbol_by_name('xyz.ryx.qedoa.weq:foz')

    def test_imp_reraises_ValueError(self):
        imp = Mock()
        imp.side_effect = ValueError()
        with self.assertRaises(ValueError):
            utils.symbol_by_name('kombu.Connection', imp=imp)

    def test_package(self):
        from kombu.entity import Exchange
        self.assertIs(
            utils.symbol_by_name('.entity:Exchange', package='kombu'),
            Exchange,
        )
        self.assertTrue(utils.symbol_by_name(':Consumer', package='kombu'))


class test_ChannelPromise(Case):

    def test_repr(self):
        obj = Mock(name='cb')
        self.assertIn(
            'promise',
            repr(utils.ChannelPromise(obj)),
        )
        self.assertFalse(obj.called)


class test_entrypoints(Case):

    @mask_modules('pkg_resources')
    def test_without_pkg_resources(self):
        self.assertListEqual(list(utils.entrypoints('kombu.test')), [])

    @module_exists('pkg_resources')
    def test_with_pkg_resources(self):
        with patch('pkg_resources.iter_entry_points', create=True) as iterep:
            eps = iterep.return_value = [Mock(), Mock()]

            self.assertTrue(list(utils.entrypoints('kombu.test')))
            iterep.assert_called_with('kombu.test')
            eps[0].load.assert_called_with()
            eps[1].load.assert_called_with()


class test_shufflecycle(Case):

    def test_shuffles(self):
        prev_repeat, utils.repeat = utils.repeat, Mock()
        try:
            utils.repeat.return_value = list(range(10))
            values = {'A', 'B', 'C'}
            cycle = utils.shufflecycle(values)
            seen = set()
            for i in range(10):
                next(cycle)
            utils.repeat.assert_called_with(None)
            self.assertTrue(seen.issubset(values))
            with self.assertRaises(StopIteration):
                next(cycle)
                next(cycle)
        finally:
            utils.repeat = prev_repeat


class test_version_string_as_tuple(Case):

    def test_versions(self):
        self.assertTupleEqual(
            version_string_as_tuple('3'),
            version_info_t(3, 0, 0, '', ''),
        )
        self.assertTupleEqual(
            version_string_as_tuple('3.3'),
            version_info_t(3, 3, 0, '', ''),
        )
        self.assertTupleEqual(
            version_string_as_tuple('3.3.1'),
            version_info_t(3, 3, 1, '', ''),
        )
        self.assertTupleEqual(
            version_string_as_tuple('3.3.1a3'),
            version_info_t(3, 3, 1, 'a3', ''),
        )
        self.assertTupleEqual(
            version_string_as_tuple('3.3.1a3-40c32'),
            version_info_t(3, 3, 1, 'a3', '40c32'),
        )
        self.assertEqual(
            version_string_as_tuple('3.3.1.a3.40c32'),
            version_info_t(3, 3, 1, 'a3', '40c32'),
        )

########NEW FILE########
__FILENAME__ = amqplib
"""
kombu.transport.amqplib
=======================

amqplib transport.

"""
from __future__ import absolute_import

import errno
import socket

try:
    from ssl import SSLError
except ImportError:
    class SSLError(Exception):  # noqa
        pass
from struct import unpack

from amqplib import client_0_8 as amqp
from amqplib.client_0_8 import transport
from amqplib.client_0_8.channel import Channel as _Channel
from amqplib.client_0_8.exceptions import AMQPConnectionException
from amqplib.client_0_8.exceptions import AMQPChannelException

from kombu.five import items
from kombu.utils.encoding import str_to_bytes
from kombu.utils.amq_manager import get_manager

from . import base

DEFAULT_PORT = 5672
HAS_MSG_PEEK = hasattr(socket, 'MSG_PEEK')

# amqplib's handshake mistakenly identifies as protocol version 1191,
# this breaks in RabbitMQ tip, which no longer falls back to
# 0-8 for unknown ids.
transport.AMQP_PROTOCOL_HEADER = str_to_bytes('AMQP\x01\x01\x08\x00')


# - fixes warnings when socket is not connected.
class TCPTransport(transport.TCPTransport):

    def read_frame(self):
        frame_type, channel, size = unpack('>BHI', self._read(7, True))
        payload = self._read(size)
        ch = ord(self._read(1))
        if ch == 206:  # '\xce'
            return frame_type, channel, payload
        else:
            raise Exception(
                'Framing Error, received 0x%02x while expecting 0xce' % ch)

    def _read(self, n, initial=False):
        read_buffer = self._read_buffer
        while len(read_buffer) < n:
            try:
                s = self.sock.recv(n - len(read_buffer))
            except socket.error as exc:
                if not initial and exc.errno in (errno.EAGAIN, errno.EINTR):
                    continue
                raise
            if not s:
                raise IOError('Socket closed')
            read_buffer += s

        result = read_buffer[:n]
        self._read_buffer = read_buffer[n:]

        return result

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
        finally:
            self.sock = None

transport.TCPTransport = TCPTransport


class SSLTransport(transport.SSLTransport):

    def __init__(self, host, connect_timeout, ssl):
        if isinstance(ssl, dict):
            self.sslopts = ssl
        self.sslobj = None

        transport._AbstractTransport.__init__(self, host, connect_timeout)

    def read_frame(self):
        frame_type, channel, size = unpack('>BHI', self._read(7, True))
        payload = self._read(size)
        ch = ord(self._read(1))
        if ch == 206:  # '\xce'
            return frame_type, channel, payload
        else:
            raise Exception(
                'Framing Error, received 0x%02x while expecting 0xce' % ch)

    def _read(self, n, initial=False):
        result = ''

        while len(result) < n:
            try:
                s = self.sslobj.read(n - len(result))
            except socket.error as exc:
                if not initial and exc.errno in (errno.EAGAIN, errno.EINTR):
                    continue
                raise
            if not s:
                raise IOError('Socket closed')
            result += s

        return result

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
        finally:
            self.sock = None
transport.SSLTransport = SSLTransport


class Connection(amqp.Connection):  # pragma: no cover
    connected = True

    def _do_close(self, *args, **kwargs):
        # amqplib does not ignore socket errors when connection
        # is closed on the remote end.
        try:
            super(Connection, self)._do_close(*args, **kwargs)
        except socket.error:
            pass

    def _dispatch_basic_return(self, channel, args, msg):
        reply_code = args.read_short()
        reply_text = args.read_shortstr()
        exchange = args.read_shortstr()
        routing_key = args.read_shortstr()

        exc = AMQPChannelException(reply_code, reply_text, (50, 60))
        if channel.events['basic_return']:
            for callback in channel.events['basic_return']:
                callback(exc, exchange, routing_key, msg)
        else:
            raise exc

    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__(*args, **kwargs)
        self._method_override = {(60, 50): self._dispatch_basic_return}

    def drain_events(self, timeout=None):
        """Wait for an event on a channel."""
        chanmap = self.channels
        chanid, method_sig, args, content = self._wait_multiple(
            chanmap, None, timeout=timeout)

        channel = chanmap[chanid]

        if (content
                and channel.auto_decode
                and hasattr(content, 'content_encoding')):
            try:
                content.body = content.body.decode(content.content_encoding)
            except Exception:
                pass

        amqp_method = self._method_override.get(method_sig) or \
            channel._METHOD_MAP.get(method_sig, None)

        if amqp_method is None:
            raise Exception('Unknown AMQP method (%d, %d)' % method_sig)

        if content is None:
            return amqp_method(channel, args)
        else:
            return amqp_method(channel, args, content)

    def read_timeout(self, timeout=None):
        if timeout is None:
            return self.method_reader.read_method()
        sock = self.transport.sock
        prev = sock.gettimeout()
        if prev != timeout:
            sock.settimeout(timeout)
        try:
            try:
                return self.method_reader.read_method()
            except SSLError as exc:
                # http://bugs.python.org/issue10272
                if 'timed out' in str(exc):
                    raise socket.timeout()
                # Non-blocking SSL sockets can throw SSLError
                if 'The operation did not complete' in str(exc):
                    raise socket.timeout()
                raise
        finally:
            if prev != timeout:
                sock.settimeout(prev)

    def _wait_multiple(self, channels, allowed_methods, timeout=None):
        for channel_id, channel in items(channels):
            method_queue = channel.method_queue
            for queued_method in method_queue:
                method_sig = queued_method[0]
                if (allowed_methods is None
                        or method_sig in allowed_methods
                        or method_sig == (20, 40)):
                    method_queue.remove(queued_method)
                    method_sig, args, content = queued_method
                    return channel_id, method_sig, args, content

        # Nothing queued, need to wait for a method from the peer
        read_timeout = self.read_timeout
        wait = self.wait
        while 1:
            channel, method_sig, args, content = read_timeout(timeout)

            if (channel in channels
                    and allowed_methods is None
                    or method_sig in allowed_methods
                    or method_sig == (20, 40)):
                return channel, method_sig, args, content

            # Not the channel and/or method we were looking for. Queue
            # this method for later
            channels[channel].method_queue.append((method_sig, args, content))

            #
            # If we just queued up a method for channel 0 (the Connection
            # itself) it's probably a close method in reaction to some
            # error, so deal with it right away.
            #
            if channel == 0:
                wait()

    def channel(self, channel_id=None):
        try:
            return self.channels[channel_id]
        except KeyError:
            return Channel(self, channel_id)


class Message(base.Message):

    def __init__(self, channel, msg, **kwargs):
        props = msg.properties
        super(Message, self).__init__(
            channel,
            body=msg.body,
            delivery_tag=msg.delivery_tag,
            content_type=props.get('content_type'),
            content_encoding=props.get('content_encoding'),
            delivery_info=msg.delivery_info,
            properties=msg.properties,
            headers=props.get('application_headers') or {},
            **kwargs)


class Channel(_Channel, base.StdChannel):
    Message = Message
    events = {'basic_return': set()}

    def __init__(self, *args, **kwargs):
        self.no_ack_consumers = set()
        super(Channel, self).__init__(*args, **kwargs)

    def prepare_message(self, body, priority=None, content_type=None,
                        content_encoding=None, headers=None, properties=None):
        """Encapsulate data into a AMQP message."""
        return amqp.Message(body, priority=priority,
                            content_type=content_type,
                            content_encoding=content_encoding,
                            application_headers=headers,
                            **properties)

    def message_to_python(self, raw_message):
        """Convert encoded message body back to a Python value."""
        return self.Message(self, raw_message)

    def close(self):
        try:
            super(Channel, self).close()
        finally:
            self.connection = None

    def basic_consume(self, *args, **kwargs):
        consumer_tag = super(Channel, self).basic_consume(*args, **kwargs)
        if kwargs['no_ack']:
            self.no_ack_consumers.add(consumer_tag)
        return consumer_tag

    def basic_cancel(self, consumer_tag, **kwargs):
        self.no_ack_consumers.discard(consumer_tag)
        return super(Channel, self).basic_cancel(consumer_tag, **kwargs)


class Transport(base.Transport):
    Connection = Connection

    default_port = DEFAULT_PORT

    # it's very annoying that amqplib sometimes raises AttributeError
    # if the connection is lost, but nothing we can do about that here.
    connection_errors = (
        base.Transport.connection_errors + (
            AMQPConnectionException,
            socket.error, IOError, OSError, AttributeError)
    )
    channel_errors = base.Transport.channel_errors + (AMQPChannelException, )

    driver_name = 'amqplib'
    driver_type = 'amqp'
    supports_ev = True

    def __init__(self, client, **kwargs):
        self.client = client
        self.default_port = kwargs.get('default_port') or self.default_port

    def create_channel(self, connection):
        return connection.channel()

    def drain_events(self, connection, **kwargs):
        return connection.drain_events(**kwargs)

    def establish_connection(self):
        """Establish connection to the AMQP broker."""
        conninfo = self.client
        for name, default_value in items(self.default_connection_params):
            if not getattr(conninfo, name, None):
                setattr(conninfo, name, default_value)
        if conninfo.hostname == 'localhost':
            conninfo.hostname = '127.0.0.1'
        conn = self.Connection(host=conninfo.host,
                               userid=conninfo.userid,
                               password=conninfo.password,
                               login_method=conninfo.login_method,
                               virtual_host=conninfo.virtual_host,
                               insist=conninfo.insist,
                               ssl=conninfo.ssl,
                               connect_timeout=conninfo.connect_timeout)
        conn.client = self.client
        return conn

    def close_connection(self, connection):
        """Close the AMQP broker connection."""
        connection.client = None
        connection.close()

    def is_alive(self, connection):
        if HAS_MSG_PEEK:
            sock = connection.transport.sock
            prev = sock.gettimeout()
            sock.settimeout(0.0001)
            try:
                sock.recv(1, socket.MSG_PEEK)
            except socket.timeout:
                pass
            except socket.error:
                return False
            finally:
                sock.settimeout(prev)
        return True

    def verify_connection(self, connection):
        return connection.channels is not None and self.is_alive(connection)

    def register_with_event_loop(self, connection, loop):
        loop.add_reader(connection.method_reader.source.sock,
                        self.on_readable, connection, loop)

    @property
    def default_connection_params(self):
        return {'userid': 'guest', 'password': 'guest',
                'port': self.default_port,
                'hostname': 'localhost', 'login_method': 'AMQPLAIN'}

    def get_manager(self, *args, **kwargs):
        return get_manager(self.client, *args, **kwargs)

########NEW FILE########
__FILENAME__ = base
"""
kombu.transport.base
====================

Base transport interface.

"""
from __future__ import absolute_import

import errno
import socket

from kombu.exceptions import ChannelError, ConnectionError
from kombu.message import Message
from kombu.utils import cached_property

__all__ = ['Message', 'StdChannel', 'Management', 'Transport']


def _LeftBlank(obj, method):
    return NotImplementedError(
        'Transport {0.__module__}.{0.__name__} does not implement {1}'.format(
            obj.__class__, method))


class StdChannel(object):
    no_ack_consumers = None

    def Consumer(self, *args, **kwargs):
        from kombu.messaging import Consumer
        return Consumer(self, *args, **kwargs)

    def Producer(self, *args, **kwargs):
        from kombu.messaging import Producer
        return Producer(self, *args, **kwargs)

    def get_bindings(self):
        raise _LeftBlank(self, 'get_bindings')

    def after_reply_message_received(self, queue):
        """reply queue semantics: can be used to delete the queue
           after transient reply message received."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


class Management(object):

    def __init__(self, transport):
        self.transport = transport

    def get_bindings(self):
        raise _LeftBlank(self, 'get_bindings')


class Transport(object):
    """Base class for transports."""
    Management = Management

    #: The :class:`~kombu.Connection` owning this instance.
    client = None

    #: Set to True if :class:`~kombu.Connection` should pass the URL
    #: unmodified.
    can_parse_url = False

    #: Default port used when no port has been specified.
    default_port = None

    #: Tuple of errors that can happen due to connection failure.
    connection_errors = (ConnectionError, )

    #: Tuple of errors that can happen due to channel/method failure.
    channel_errors = (ChannelError, )

    #: Type of driver, can be used to separate transports
    #: using the AMQP protocol (driver_type: 'amqp'),
    #: Redis (driver_type: 'redis'), etc...
    driver_type = 'N/A'

    #: Name of driver library (e.g. 'py-amqp', 'redis', 'beanstalkc').
    driver_name = 'N/A'

    #: Whether this transports support heartbeats,
    #: and that the :meth:`heartbeat_check` method has any effect.
    supports_heartbeats = False

    #: Set to true if the transport supports the AIO interface.
    supports_ev = False

    __reader = None

    def __init__(self, client, **kwargs):
        self.client = client

    def establish_connection(self):
        raise _LeftBlank(self, 'establish_connection')

    def close_connection(self, connection):
        raise _LeftBlank(self, 'close_connection')

    def create_channel(self, connection):
        raise _LeftBlank(self, 'create_channel')

    def close_channel(self, connection):
        raise _LeftBlank(self, 'close_channel')

    def drain_events(self, connection, **kwargs):
        raise _LeftBlank(self, 'drain_events')

    def heartbeat_check(self, connection, rate=2):
        pass

    def driver_version(self):
        return 'N/A'

    def get_heartbeat_interval(self, connection):
        return 0

    def register_with_event_loop(self, loop):
        pass

    def unregister_from_event_loop(self, loop):
        pass

    def verify_connection(self, connection):
        return True

    def _make_reader(self, connection, timeout=socket.timeout,
                     error=socket.error, _unavail=(errno.EAGAIN, errno.EINTR)):
        drain_events = connection.drain_events

        def _read(loop):
            if not connection.connected:
                raise ConnectionError('Socket was disconnected')
            try:
                drain_events(timeout=0)
            except timeout:
                return
            except error as exc:
                if exc.errno in _unavail:
                    return
                raise
            loop.call_soon(_read, loop)

        return _read

    def qos_semantics_matches_spec(self, connection):
        return True

    def on_readable(self, connection, loop):
        reader = self.__reader
        if reader is None:
            reader = self.__reader = self._make_reader(connection)
        reader(loop)

    @property
    def default_connection_params(self):
        return {}

    def get_manager(self, *args, **kwargs):
        return self.Management(self)

    @cached_property
    def manager(self):
        return self.get_manager()

########NEW FILE########
__FILENAME__ = beanstalk
"""
kombu.transport.beanstalk
=========================

Beanstalk transport.

:copyright: (c) 2010 - 2013 by David Ziegler.
:license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

import beanstalkc
import socket

from kombu.five import Empty
from kombu.utils.encoding import bytes_to_str
from kombu.utils.json import loads, dumps

from . import virtual

DEFAULT_PORT = 11300

__author__ = 'David Ziegler <david.ziegler@gmail.com>'


class Channel(virtual.Channel):
    _client = None

    def _parse_job(self, job):
        item, dest = None, None
        if job:
            try:
                item = loads(bytes_to_str(job.body))
                dest = job.stats()['tube']
            except Exception:
                job.bury()
            else:
                job.delete()
        else:
            raise Empty()
        return item, dest

    def _put(self, queue, message, **kwargs):
        extra = {}
        priority = self._get_message_priority(message)
        ttr = message['properties'].get('ttr')
        if ttr is not None:
            extra['ttr'] = ttr

        self.client.use(queue)
        self.client.put(dumps(message), priority=priority, **extra)

    def _get(self, queue):
        if queue not in self.client.watching():
            self.client.watch(queue)

        [self.client.ignore(active) for active in self.client.watching()
         if active != queue]

        job = self.client.reserve(timeout=1)
        item, dest = self._parse_job(job)
        return item

    def _get_many(self, queues, timeout=1):
        # timeout of None will cause beanstalk to timeout waiting
        # for a new request
        if timeout is None:
            timeout = 1

        watching = self.client.watching()

        [self.client.watch(active) for active in queues
         if active not in watching]

        [self.client.ignore(active) for active in watching
         if active not in queues]

        job = self.client.reserve(timeout=timeout)
        return self._parse_job(job)

    def _purge(self, queue):
        if queue not in self.client.watching():
            self.client.watch(queue)

        [self.client.ignore(active)
         for active in self.client.watching()
         if active != queue]
        count = 0
        while 1:
            job = self.client.reserve(timeout=1)
            if job:
                job.delete()
                count += 1
            else:
                break
        return count

    def _size(self, queue):
        return 0

    def _open(self):
        conninfo = self.connection.client
        host = conninfo.hostname or 'localhost'
        port = conninfo.port or DEFAULT_PORT
        conn = beanstalkc.Connection(host=host, port=port)
        conn.connect()
        return conn

    def close(self):
        if self._client is not None:
            return self._client.close()
        super(Channel, self).close()

    @property
    def client(self):
        if self._client is None:
            self._client = self._open()
        return self._client


class Transport(virtual.Transport):
    Channel = Channel

    polling_interval = 1
    default_port = DEFAULT_PORT
    connection_errors = (
        virtual.Transport.connection_errors + (
            socket.error, beanstalkc.SocketError, IOError)
    )
    channel_errors = (
        virtual.Transport.channel_errors + (
            socket.error, IOError,
            beanstalkc.SocketError,
            beanstalkc.BeanstalkcException)
    )
    driver_type = 'beanstalk'
    driver_name = 'beanstalkc'

    def driver_version(self):
        return beanstalkc.__version__

########NEW FILE########
__FILENAME__ = couchdb
"""
kombu.transport.couchdb
=======================

CouchDB transport.

:copyright: (c) 2010 - 2013 by David Clymer.
:license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

import socket
import couchdb

from kombu.five import Empty
from kombu.utils import uuid4
from kombu.utils.encoding import bytes_to_str
from kombu.utils.json import loads, dumps

from . import virtual

DEFAULT_PORT = 5984
DEFAULT_DATABASE = 'kombu_default'

__author__ = 'David Clymer <david@zettazebra.com>'


def create_message_view(db):
    from couchdb import design

    view = design.ViewDefinition('kombu', 'messages', """
        function (doc) {
          if (doc.queue && doc.payload)
            emit(doc.queue, doc);
        }
        """)
    if not view.get_doc(db):
        view.sync(db)


class Channel(virtual.Channel):
    _client = None

    view_created = False

    def _put(self, queue, message, **kwargs):
        self.client.save({'_id': uuid4().hex,
                          'queue': queue,
                          'payload': dumps(message)})

    def _get(self, queue):
        result = self._query(queue, limit=1)
        if not result:
            raise Empty()

        item = result.rows[0].value
        self.client.delete(item)
        return loads(bytes_to_str(item['payload']))

    def _purge(self, queue):
        result = self._query(queue)
        for item in result:
            self.client.delete(item.value)
        return len(result)

    def _size(self, queue):
        return len(self._query(queue))

    def _open(self):
        conninfo = self.connection.client
        dbname = conninfo.virtual_host
        proto = conninfo.ssl and 'https' or 'http'
        if not dbname or dbname == '/':
            dbname = DEFAULT_DATABASE
        port = conninfo.port or DEFAULT_PORT
        server = couchdb.Server('%s://%s:%s/' % (proto,
                                                 conninfo.hostname,
                                                 port))
        # Use username and password if avaliable
        try:
            server.resource.credentials = (conninfo.userid, conninfo.password)
        except AttributeError:
            pass
        try:
            return server[dbname]
        except couchdb.http.ResourceNotFound:
            return server.create(dbname)

    def _query(self, queue, **kwargs):
        if not self.view_created:
            # if the message view is not yet set up, we'll need it now.
            create_message_view(self.client)
            self.view_created = True
        return self.client.view('kombu/messages', key=queue, **kwargs)

    @property
    def client(self):
        if self._client is None:
            self._client = self._open()
        return self._client


class Transport(virtual.Transport):
    Channel = Channel

    polling_interval = 1
    default_port = DEFAULT_PORT
    connection_errors = (
        virtual.Transport.connection_errors + (
            socket.error,
            couchdb.HTTPError,
            couchdb.ServerError,
            couchdb.Unauthorized)
    )
    channel_errors = (
        virtual.Transport.channel_errors + (
            couchdb.HTTPError,
            couchdb.ServerError,
            couchdb.PreconditionFailed,
            couchdb.ResourceConflict,
            couchdb.ResourceNotFound)
    )
    driver_type = 'couchdb'
    driver_name = 'couchdb'

    def driver_version(self):
        return couchdb.__version__

########NEW FILE########
__FILENAME__ = clean_kombu_messages
from __future__ import absolute_import

from django.core.management.base import BaseCommand


def pluralize(desc, value):
    if value > 1:
        return desc + 's'
    return desc


class Command(BaseCommand):
    requires_model_validation = True

    def handle(self, *args, **options):
        from kombu.transport.django.models import Message

        count = Message.objects.filter(visible=False).count()

        print('Removing {0} invisible {1} from database... '.format(
            count, pluralize('message', count)))
        Message.objects.cleanup()

########NEW FILE########
__FILENAME__ = managers
from __future__ import absolute_import

from django.db import transaction, connection, models
try:
    from django.db import connections, router
except ImportError:  # pre-Django 1.2
    connections = router = None  # noqa


class QueueManager(models.Manager):

    def publish(self, queue_name, payload):
        queue, created = self.get_or_create(name=queue_name)
        queue.messages.create(payload=payload)

    def fetch(self, queue_name):
        try:
            queue = self.get(name=queue_name)
        except self.model.DoesNotExist:
            return

        return queue.messages.pop()

    def size(self, queue_name):
        return self.get(name=queue_name).messages.count()

    def purge(self, queue_name):
        try:
            queue = self.get(name=queue_name)
        except self.model.DoesNotExist:
            return

        messages = queue.messages.all()
        count = messages.count()
        messages.delete()
        return count


def select_for_update(qs):
    try:
        return qs.select_for_update()
    except AttributeError:
        return qs


class MessageManager(models.Manager):
    _messages_received = [0]
    cleanup_every = 10

    @transaction.commit_manually
    def pop(self):
        try:
            resultset = select_for_update(
                self.filter(visible=True).order_by('sent_at', 'id')
            )
            result = resultset[0:1].get()
            result.visible = False
            result.save()
            recv = self.__class__._messages_received
            recv[0] += 1
            if not recv[0] % self.cleanup_every:
                self.cleanup()
            transaction.commit()
            return result.payload
        except self.model.DoesNotExist:
            transaction.commit()
        except:
            transaction.rollback()

    def cleanup(self):
        cursor = self.connection_for_write().cursor()
        try:
            cursor.execute(
                'DELETE FROM %s WHERE visible=%%s' % (
                    self.model._meta.db_table, ),
                (False, )
            )
        except:
            transaction.rollback_unless_managed()
        else:
            transaction.commit_unless_managed()

    def connection_for_write(self):
        if connections:
            return connections[router.db_for_write(self.model)]
        return connection

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
from __future__ import absolute_import

# flake8: noqa
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'Queue'
        db.create_table('djkombu_queue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=200)),
        ))
        db.send_create_signal('django', ['Queue'])

        # Adding model 'Message'
        db.create_table('djkombu_message', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('visible', self.gf('django.db.models.fields.BooleanField')(default=True, db_index=True)),
            ('sent_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, db_index=True, blank=True)),
            ('payload', self.gf('django.db.models.fields.TextField')()),
            ('queue', self.gf('django.db.models.fields.related.ForeignKey')(related_name='messages', to=orm['django.Queue'])),
        ))
        db.send_create_signal('django', ['Message'])


    def backwards(self, orm):

        # Deleting model 'Queue'
        db.delete_table('djkombu_queue')

        # Deleting model 'Message'
        db.delete_table('djkombu_message')


    models = {
        'django.message': {
            'Meta': {'object_name': 'Message', 'db_table': "'djkombu_message'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'payload': ('django.db.models.fields.TextField', [], {}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['django.Queue']"}),
            'sent_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'})
        },
        'django.queue': {
            'Meta': {'object_name': 'Queue', 'db_table': "'djkombu_queue'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        }
    }

    complete_apps = ['django']

########NEW FILE########
__FILENAME__ = models
from __future__ import absolute_import

from django.db import models
from django.utils.translation import ugettext_lazy as _

from .managers import QueueManager, MessageManager


class Queue(models.Model):
    name = models.CharField(_('name'), max_length=200, unique=True)

    objects = QueueManager()

    class Meta:
        db_table = 'djkombu_queue'
        verbose_name = _('queue')
        verbose_name_plural = _('queues')


class Message(models.Model):
    visible = models.BooleanField(default=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True,
                                   auto_now_add=True)
    payload = models.TextField(_('payload'), null=False)
    queue = models.ForeignKey(Queue, related_name='messages')

    objects = MessageManager()

    class Meta:
        db_table = 'djkombu_message'
        verbose_name = _('message')
        verbose_name_plural = _('messages')

########NEW FILE########
__FILENAME__ = filesystem
"""
kombu.transport.filesystem
==========================

Transport using the file system as the message store.

"""
from __future__ import absolute_import

import os
import shutil
import uuid
import tempfile

from . import virtual
from kombu.exceptions import ChannelError
from kombu.five import Empty, monotonic
from kombu.utils import cached_property
from kombu.utils.encoding import bytes_to_str, str_to_bytes
from kombu.utils.json import loads, dumps


VERSION = (1, 0, 0)
__version__ = '.'.join(map(str, VERSION))

# needs win32all to work on Windows
if os.name == 'nt':

    import win32con
    import win32file
    import pywintypes

    LOCK_EX = win32con.LOCKFILE_EXCLUSIVE_LOCK
    # 0 is the default
    LOCK_SH = 0                                     # noqa
    LOCK_NB = win32con.LOCKFILE_FAIL_IMMEDIATELY    # noqa
    __overlapped = pywintypes.OVERLAPPED()

    def lock(file, flags):
        hfile = win32file._get_osfhandle(file.fileno())
        win32file.LockFileEx(hfile, flags, 0, 0xffff0000, __overlapped)

    def unlock(file):
        hfile = win32file._get_osfhandle(file.fileno())
        win32file.UnlockFileEx(hfile, 0, 0xffff0000, __overlapped)

elif os.name == 'posix':

    import fcntl
    from fcntl import LOCK_EX, LOCK_SH, LOCK_NB     # noqa

    def lock(file, flags):  # noqa
        fcntl.flock(file.fileno(), flags)

    def unlock(file):       # noqa
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)
else:
    raise RuntimeError(
        'Filesystem plugin only defined for NT and POSIX platforms')


class Channel(virtual.Channel):

    def _put(self, queue, payload, **kwargs):
        """Put `message` onto `queue`."""

        filename = '%s_%s.%s.msg' % (int(round(monotonic() * 1000)),
                                     uuid.uuid4(), queue)
        filename = os.path.join(self.data_folder_out, filename)

        try:
            f = open(filename, 'wb')
            lock(f, LOCK_EX)
            f.write(str_to_bytes(dumps(payload)))
        except (IOError, OSError):
            raise ChannelError(
                'Cannot add file {0!r} to directory'.format(filename))
        finally:
            unlock(f)
            f.close()

    def _get(self, queue):
        """Get next message from `queue`."""

        queue_find = '.' + queue + '.msg'
        folder = os.listdir(self.data_folder_in)
        folder = sorted(folder)
        while len(folder) > 0:
            filename = folder.pop(0)

            # only handle message for the requested queue
            if filename.find(queue_find) < 0:
                continue

            if self.store_processed:
                processed_folder = self.processed_folder
            else:
                processed_folder = tempfile.gettempdir()

            try:
                # move the file to the tmp/processed folder
                shutil.move(os.path.join(self.data_folder_in, filename),
                            processed_folder)
            except IOError:
                pass  # file could be locked, or removed in meantime so ignore

            filename = os.path.join(processed_folder, filename)
            try:
                f = open(filename, 'rb')
                payload = f.read()
                f.close()
                if not self.store_processed:
                    os.remove(filename)
            except (IOError, OSError):
                raise ChannelError(
                    'Cannot read file {0!r} from queue.'.format(filename))

            return loads(bytes_to_str(payload))

        raise Empty()

    def _purge(self, queue):
        """Remove all messages from `queue`."""
        count = 0
        queue_find = '.' + queue + '.msg'

        folder = os.listdir(self.data_folder_in)
        while len(folder) > 0:
            filename = folder.pop()
            try:
                # only purge messages for the requested queue
                if filename.find(queue_find) < 0:
                    continue

                filename = os.path.join(self.data_folder_in, filename)
                os.remove(filename)

                count += 1

            except OSError:
                # we simply ignore its existence, as it was probably
                # processed by another worker
                pass

        return count

    def _size(self, queue):
        """Return the number of messages in `queue` as an :class:`int`."""
        count = 0

        queue_find = '.{0}.msg'.format(queue)
        folder = os.listdir(self.data_folder_in)
        while len(folder) > 0:
            filename = folder.pop()

            # only handle message for the requested queue
            if filename.find(queue_find) < 0:
                continue

            count += 1

        return count

    @property
    def transport_options(self):
        return self.connection.client.transport_options

    @cached_property
    def data_folder_in(self):
        return self.transport_options.get('data_folder_in', 'data_in')

    @cached_property
    def data_folder_out(self):
        return self.transport_options.get('data_folder_out', 'data_out')

    @cached_property
    def store_processed(self):
        return self.transport_options.get('store_processed', False)

    @cached_property
    def processed_folder(self):
        return self.transport_options.get('processed_folder', 'processed')


class Transport(virtual.Transport):
    Channel = Channel

    default_port = 0
    driver_type = 'filesystem'
    driver_name = 'filesystem'

    def driver_version(self):
        return 'N/A'

########NEW FILE########
__FILENAME__ = librabbitmq
"""
kombu.transport.librabbitmq
===========================

`librabbitmq`_ transport.

.. _`librabbitmq`: http://pypi.python.org/librabbitmq/

"""
from __future__ import absolute_import

import os
import socket
import warnings

try:
    import librabbitmq as amqp
    from librabbitmq import ChannelError, ConnectionError
except ImportError:  # pragma: no cover
    try:
        import pylibrabbitmq as amqp                             # noqa
        from pylibrabbitmq import ChannelError, ConnectionError  # noqa
    except ImportError:
        raise ImportError('No module named librabbitmq')

from kombu.five import items, values
from kombu.utils.amq_manager import get_manager
from kombu.utils.text import version_string_as_tuple

from . import base

W_VERSION = """
    librabbitmq version too old to detect RabbitMQ version information
    so make sure you are using librabbitmq 1.5 when using rabbitmq > 3.3
"""
DEFAULT_PORT = 5672

NO_SSL_ERROR = """\
ssl not supported by librabbitmq, please use pyamqp:// or stunnel\
"""


class Message(base.Message):

    def __init__(self, channel, props, info, body):
        super(Message, self).__init__(
            channel,
            body=body,
            delivery_info=info,
            properties=props,
            delivery_tag=info.get('delivery_tag'),
            content_type=props.get('content_type'),
            content_encoding=props.get('content_encoding'),
            headers=props.get('headers'))


class Channel(amqp.Channel, base.StdChannel):
    Message = Message

    def prepare_message(self, body, priority=None,
                        content_type=None, content_encoding=None,
                        headers=None, properties=None):
        """Encapsulate data into a AMQP message."""
        properties = properties if properties is not None else {}
        properties.update({'content_type': content_type,
                           'content_encoding': content_encoding,
                           'headers': headers,
                           'priority': priority})
        return body, properties


class Connection(amqp.Connection):
    Channel = Channel
    Message = Message


class Transport(base.Transport):
    Connection = Connection

    default_port = DEFAULT_PORT
    connection_errors = (
        base.Transport.connection_errors + (
            ConnectionError, socket.error, IOError, OSError)
    )
    channel_errors = (
        base.Transport.channel_errors + (ChannelError, )
    )
    driver_type = 'amqp'
    driver_name = 'librabbitmq'

    supports_ev = True

    def __init__(self, client, **kwargs):
        self.client = client
        self.default_port = kwargs.get('default_port') or self.default_port
        self.__reader = None

    def driver_version(self):
        return amqp.__version__

    def create_channel(self, connection):
        return connection.channel()

    def drain_events(self, connection, **kwargs):
        return connection.drain_events(**kwargs)

    def establish_connection(self):
        """Establish connection to the AMQP broker."""
        conninfo = self.client
        for name, default_value in items(self.default_connection_params):
            if not getattr(conninfo, name, None):
                setattr(conninfo, name, default_value)
        if conninfo.ssl:
            raise NotImplementedError(NO_SSL_ERROR)
        opts = dict({
            'host': conninfo.host,
            'userid': conninfo.userid,
            'password': conninfo.password,
            'virtual_host': conninfo.virtual_host,
            'login_method': conninfo.login_method,
            'insist': conninfo.insist,
            'ssl': conninfo.ssl,
            'connect_timeout': conninfo.connect_timeout,
        }, **conninfo.transport_options or {})
        conn = self.Connection(**opts)
        conn.client = self.client
        self.client.drain_events = conn.drain_events
        return conn

    def close_connection(self, connection):
        """Close the AMQP broker connection."""
        self.client.drain_events = None
        connection.close()

    def _collect(self, connection):
        if connection is not None:
            for channel in values(connection.channels):
                channel.connection = None
            try:
                os.close(connection.fileno())
            except OSError:
                pass
            connection.channels.clear()
            connection.callbacks.clear()
        self.client.drain_events = None
        self.client = None

    def verify_connection(self, connection):
        return connection.connected

    def register_with_event_loop(self, connection, loop):
        loop.add_reader(
            connection.fileno(), self.on_readable, connection, loop,
        )

    def get_manager(self, *args, **kwargs):
        return get_manager(self.client, *args, **kwargs)

    def qos_semantics_matches_spec(self, connection):
        try:
            props = connection.server_properties
        except AttributeError:
            warnings.warn(UserWarning(W_VERSION))
        else:
            if props.get('product') == 'RabbitMQ':
                return version_string_as_tuple(props['version']) < (3, 3)
        return True

    @property
    def default_connection_params(self):
        return {'userid': 'guest', 'password': 'guest',
                'port': self.default_port,
                'hostname': 'localhost', 'login_method': 'AMQPLAIN'}

########NEW FILE########
__FILENAME__ = memory
"""
kombu.transport.memory
======================

In-memory transport.

"""
from __future__ import absolute_import

from kombu.five import Queue, values

from . import virtual


class Channel(virtual.Channel):
    queues = {}
    do_restore = False
    supports_fanout = True

    def _has_queue(self, queue, **kwargs):
        return queue in self.queues

    def _new_queue(self, queue, **kwargs):
        if queue not in self.queues:
            self.queues[queue] = Queue()

    def _get(self, queue, timeout=None):
        return self._queue_for(queue).get(block=False)

    def _queue_for(self, queue):
        if queue not in self.queues:
            self.queues[queue] = Queue()
        return self.queues[queue]

    def _queue_bind(self, *args):
        pass

    def _put_fanout(self, exchange, message, routing_key=None, **kwargs):
        for queue in self._lookup(exchange, routing_key):
            self._queue_for(queue).put(message)

    def _put(self, queue, message, **kwargs):
        self._queue_for(queue).put(message)

    def _size(self, queue):
        return self._queue_for(queue).qsize()

    def _delete(self, queue, *args):
        self.queues.pop(queue, None)

    def _purge(self, queue):
        q = self._queue_for(queue)
        size = q.qsize()
        q.queue.clear()
        return size

    def close(self):
        super(Channel, self).close()
        for queue in values(self.queues):
            queue.empty()
        self.queues = {}

    def after_reply_message_received(self, queue):
        pass


class Transport(virtual.Transport):
    Channel = Channel

    #: memory backend state is global.
    state = virtual.BrokerState()

    driver_type = 'memory'
    driver_name = 'memory'

    def driver_version(self):
        return 'N/A'

########NEW FILE########
__FILENAME__ = mongodb
"""
kombu.transport.mongodb
=======================

MongoDB transport.

:copyright: (c) 2010 - 2013 by Flavio Percoco Premoli.
:license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

import pymongo

from pymongo import errors
from pymongo import MongoClient, uri_parser

from kombu.five import Empty
from kombu.syn import _detect_environment
from kombu.utils.encoding import bytes_to_str
from kombu.utils.json import loads, dumps

from . import virtual

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 27017

DEFAULT_MESSAGES_COLLECTION = 'messages'
DEFAULT_ROUTING_COLLECTION = 'messages.routing'
DEFAULT_BROADCAST_COLLECTION = 'messages.broadcast'


class BroadcastCursor(object):
    """Cursor for broadcast queues."""

    def __init__(self, cursor):
        self._cursor = cursor

        self.purge(rewind=False)

    def get_size(self):
        return self._cursor.count() - self._offset

    def close(self):
        self._cursor.close()

    def purge(self, rewind=True):
        if rewind:
            self._cursor.rewind()

        # Fast forward the cursor past old events
        self._offset = self._cursor.count()
        self._cursor = self._cursor.skip(self._offset)

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            try:
                msg = next(self._cursor)
            except pymongo.errors.OperationFailure as exc:
                # In some cases tailed cursor can become invalid
                # and have to be reinitalized
                if 'not valid at server' in exc.message:
                    self.purge()

                    continue

                raise
            else:
                break

        self._offset += 1

        return msg
    next = __next__


class Channel(virtual.Channel):
    _client = None
    supports_fanout = True
    _fanout_queues = {}

    def __init__(self, *vargs, **kwargs):
        super(Channel, self).__init__(*vargs, **kwargs)

        self._broadcast_cursors = {}

    def _new_queue(self, queue, **kwargs):
        pass

    def _get(self, queue):
        if queue in self._fanout_queues:
            try:
                msg = next(self.get_broadcast_cursor(queue))
            except StopIteration:
                msg = None
        else:
            msg = self.get_messages().find_and_modify(
                query={'queue': queue},
                sort=[('priority', pymongo.ASCENDING),
                      ('_id', pymongo.ASCENDING)],
                remove=True,
            )

        if msg is None:
            raise Empty()

        return loads(bytes_to_str(msg['payload']))

    def _size(self, queue):
        if queue in self._fanout_queues:
            return self.get_broadcast_cursor(queue).get_size()

        return self.get_messages().find({'queue': queue}).count()

    def _put(self, queue, message, **kwargs):
        self.get_messages().insert({
            'payload': dumps(message),
            'queue': queue,
            'priority': self._get_message_priority(message, reverse=True),
        })

    def _purge(self, queue):
        size = self._size(queue)

        if queue in self._fanout_queues:
            self.get_broadcaset_cursor(queue).purge()
        else:
            self.get_messages().remove({'queue': queue})

        return size

    def _parse_uri(self, scheme='mongodb://'):
        # See mongodb uri documentation:
        # http://docs.mongodb.org/manual/reference/connection-string/
        client = self.connection.client
        hostname = client.hostname

        if not hostname.startswith(scheme):
            hostname = scheme + hostname

        if not hostname[len(scheme):]:
            hostname += DEFAULT_HOST

        if client.userid and '@' not in hostname:
            head, tail = hostname.split('://')

            credentials = client.userid
            if client.password:
                credentials += ':' + client.password

            hostname = head + '://' + credentials + '@' + tail

        port = client.port if client.port is not None else DEFAULT_PORT

        parsed = uri_parser.parse_uri(hostname, port)

        dbname = parsed['database'] or client.virtual_host

        if dbname in ('/', None):
            dbname = 'kombu_default'

        options = {
            'auto_start_request': True,
            'ssl': client.ssl,
            'connectTimeoutMS': (int(client.connect_timeout * 1000)
                                 if client.connect_timeout else None),
        }
        options.update(client.transport_options)
        options.update(parsed['options'])

        return hostname, dbname, options

    def _open(self, scheme='mongodb://'):
        hostname, dbname, options = self._parse_uri(scheme=scheme)

        mongoconn = MongoClient(
            host=hostname, ssl=options['ssl'],
            auto_start_request=options['auto_start_request'],
            connectTimeoutMS=options['connectTimeoutMS'],
            use_greenlets=_detect_environment() != 'default',
        )
        database = mongoconn[dbname]

        version = mongoconn.server_info()['version']
        if tuple(map(int, version.split('.')[:2])) < (1, 3):
            raise NotImplementedError(
                'Kombu requires MongoDB version 1.3+ (server is {0})'.format(
                    version))

        self._create_broadcast(database, options)

        self._client = database

    def _create_broadcast(self, database, options):
        '''Create capped collection for broadcast messages.'''
        if DEFAULT_BROADCAST_COLLECTION in database.collection_names():
            return

        capsize = options.get('capped_queue_size') or 100000
        database.create_collection(DEFAULT_BROADCAST_COLLECTION,
                                   size=capsize, capped=True)

    def _ensure_indexes(self):
        '''Ensure indexes on collections.'''
        self.get_messages().ensure_index(
            [('queue', 1), ('priority', 1), ('_id', 1)], background=True,
        )
        self.get_broadcast().ensure_index([('queue', 1)])
        self.get_routing().ensure_index([('queue', 1), ('exchange', 1)])

    def get_table(self, exchange):
        """Get table of bindings for ``exchange``."""
        # TODO Store a more complete exchange metatable in the
        #      routing collection
        localRoutes = frozenset(self.state.exchanges[exchange]['table'])
        brokerRoutes = self.get_messages().routing.find(
            {'exchange': exchange}
        )

        return localRoutes | frozenset((r['routing_key'],
                                        r['pattern'],
                                        r['queue']) for r in brokerRoutes)

    def _put_fanout(self, exchange, message, routing_key, **kwargs):
        """Deliver fanout message."""
        self.get_broadcast().insert({'payload': dumps(message),
                                     'queue': exchange})

    def _queue_bind(self, exchange, routing_key, pattern, queue):
        if self.typeof(exchange).type == 'fanout':
            self.create_broadcast_cursor(exchange, routing_key, pattern, queue)
            self._fanout_queues[queue] = exchange

        meta = {'exchange': exchange,
                'queue': queue,
                'routing_key': routing_key,
                'pattern': pattern}
        self.get_routing().update(meta, meta, upsert=True)

    def queue_delete(self, queue, **kwargs):
        self.get_routing().remove({'queue': queue})

        super(Channel, self).queue_delete(queue, **kwargs)

        if queue in self._fanout_queues:
            try:
                cursor = self._broadcast_cursors.pop(queue)
            except KeyError:
                pass
            else:
                cursor.close()

                self._fanout_queues.pop(queue)

    @property
    def client(self):
        if self._client is None:
            self._open()
            self._ensure_indexes()

        return self._client

    def get_messages(self):
        return self.client[DEFAULT_MESSAGES_COLLECTION]

    def get_routing(self):
        return self.client[DEFAULT_ROUTING_COLLECTION]

    def get_broadcast(self):
        return self.client[DEFAULT_BROADCAST_COLLECTION]

    def get_broadcast_cursor(self, queue):
        try:
            return self._broadcast_cursors[queue]
        except KeyError:
            # Cursor may be absent when Channel created more than once.
            # _fanout_queues is a class-level mutable attribute so it's
            # shared over all Channel instances.
            return self.create_broadcast_cursor(
                self._fanout_queues[queue], None, None, queue,
            )

    def create_broadcast_cursor(self, exchange, routing_key, pattern, queue):
        cursor = self.get_broadcast().find(
            query={'queue': exchange},
            sort=[('$natural', 1)],
            tailable=True,
        )
        ret = self._broadcast_cursors[queue] = BroadcastCursor(cursor)
        return ret


class Transport(virtual.Transport):
    Channel = Channel

    can_parse_url = True
    polling_interval = 1
    default_port = DEFAULT_PORT
    connection_errors = (
        virtual.Transport.connection_errors + (errors.ConnectionFailure, )
    )
    channel_errors = (
        virtual.Transport.channel_errors + (
            errors.ConnectionFailure,
            errors.OperationFailure)
    )
    driver_type = 'mongodb'
    driver_name = 'pymongo'

    def driver_version(self):
        return pymongo.version

########NEW FILE########
__FILENAME__ = pyamqp
"""
kombu.transport.pyamqp
======================

pure python amqp transport.

"""
from __future__ import absolute_import

import amqp

from kombu.five import items
from kombu.utils.amq_manager import get_manager
from kombu.utils.text import version_string_as_tuple

from . import base

DEFAULT_PORT = 5672


class Message(base.Message):

    def __init__(self, channel, msg, **kwargs):
        props = msg.properties
        super(Message, self).__init__(
            channel,
            body=msg.body,
            delivery_tag=msg.delivery_tag,
            content_type=props.get('content_type'),
            content_encoding=props.get('content_encoding'),
            delivery_info=msg.delivery_info,
            properties=msg.properties,
            headers=props.get('application_headers') or {},
            **kwargs)


class Channel(amqp.Channel, base.StdChannel):
    Message = Message

    def prepare_message(self, body, priority=None,
                        content_type=None, content_encoding=None,
                        headers=None, properties=None, _Message=amqp.Message):
        """Prepares message so that it can be sent using this transport."""
        return _Message(
            body,
            priority=priority,
            content_type=content_type,
            content_encoding=content_encoding,
            application_headers=headers,
            **properties or {}
        )

    def message_to_python(self, raw_message):
        """Convert encoded message body back to a Python value."""
        return self.Message(self, raw_message)


class Connection(amqp.Connection):
    Channel = Channel


class Transport(base.Transport):
    Connection = Connection

    default_port = DEFAULT_PORT

    # it's very annoying that pyamqp sometimes raises AttributeError
    # if the connection is lost, but nothing we can do about that here.
    connection_errors = amqp.Connection.connection_errors
    channel_errors = amqp.Connection.channel_errors
    recoverable_connection_errors = \
        amqp.Connection.recoverable_connection_errors
    recoverable_channel_errors = amqp.Connection.recoverable_channel_errors

    driver_name = 'py-amqp'
    driver_type = 'amqp'
    supports_heartbeats = True
    supports_ev = True

    def __init__(self, client, default_port=None, **kwargs):
        self.client = client
        self.default_port = default_port or self.default_port

    def driver_version(self):
        return amqp.__version__

    def create_channel(self, connection):
        return connection.channel()

    def drain_events(self, connection, **kwargs):
        return connection.drain_events(**kwargs)

    def establish_connection(self):
        """Establish connection to the AMQP broker."""
        conninfo = self.client
        for name, default_value in items(self.default_connection_params):
            if not getattr(conninfo, name, None):
                setattr(conninfo, name, default_value)
        if conninfo.hostname == 'localhost':
            conninfo.hostname = '127.0.0.1'
        opts = dict({
            'host': conninfo.host,
            'userid': conninfo.userid,
            'password': conninfo.password,
            'login_method': conninfo.login_method,
            'virtual_host': conninfo.virtual_host,
            'insist': conninfo.insist,
            'ssl': conninfo.ssl,
            'connect_timeout': conninfo.connect_timeout,
            'heartbeat': conninfo.heartbeat,
        }, **conninfo.transport_options or {})
        conn = self.Connection(**opts)
        conn.client = self.client
        return conn

    def verify_connection(self, connection):
        return connection.connected

    def close_connection(self, connection):
        """Close the AMQP broker connection."""
        connection.client = None
        connection.close()

    def get_heartbeat_interval(self, connection):
        return connection.heartbeat

    def register_with_event_loop(self, connection, loop):
        loop.add_reader(connection.sock, self.on_readable, connection, loop)

    def heartbeat_check(self, connection, rate=2):
        return connection.heartbeat_tick(rate=rate)

    def qos_semantics_matches_spec(self, connection):
        props = connection.server_properties
        if props.get('product') == 'RabbitMQ':
            return version_string_as_tuple(props['version']) < (3, 3)
        return True

    @property
    def default_connection_params(self):
        return {'userid': 'guest', 'password': 'guest',
                'port': self.default_port,
                'hostname': 'localhost', 'login_method': 'AMQPLAIN'}

    def get_manager(self, *args, **kwargs):
        return get_manager(self.client, *args, **kwargs)

########NEW FILE########
__FILENAME__ = pyro
"""
kombu.transport.pyro
======================

Pyro transport.

Requires the :mod:`Pyro4` library to be installed.

"""
from __future__ import absolute_import

import sys

from kombu.five import reraise
from kombu.utils import cached_property

from . import virtual

try:
    import Pyro4 as pyro
    from Pyro4.errors import NamingError
except ImportError:          # pragma: no cover
    pyro = NamingError = None  # noqa

DEFAULT_PORT = 9090
E_LOOKUP = """\
Unable to locate pyro nameserver {0.virtual_host} on host {0.hostname}\
"""


class Channel(virtual.Channel):

    def queues(self):
        return self.shared_queues.get_queue_names()

    def _new_queue(self, queue, **kwargs):
        if queue not in self.queues():
            self.shared_queues.new_queue(queue)

    def _get(self, queue, timeout=None):
        queue = self._queue_for(queue)
        msg = self.shared_queues._get(queue)
        return msg

    def _queue_for(self, queue):
        if queue not in self.queues():
            self.shared_queues.new_queue(queue)
        return queue

    def _put(self, queue, message, **kwargs):
        queue = self._queue_for(queue)
        self.shared_queues._put(queue, message)

    def _size(self, queue):
        return self.shared_queues._size(queue)

    def _delete(self, queue, *args):
        self.shared_queues._delete(queue)

    def _purge(self, queue):
        return self.shared_queues._purge(queue)

    def after_reply_message_received(self, queue):
        pass

    @cached_property
    def shared_queues(self):
        return self.connection.shared_queues


class Transport(virtual.Transport):
    Channel = Channel

    #: memory backend state is global.
    state = virtual.BrokerState()

    default_port = DEFAULT_PORT

    driver_type = driver_name = 'pyro'

    def _open(self):
        conninfo = self.client
        pyro.config.HMAC_KEY = conninfo.virtual_host
        try:
            nameserver = pyro.locateNS(host=conninfo.hostname,
                                       port=self.default_port)
            # name of registered pyro object
            uri = nameserver.lookup(conninfo.virtual_host)
            return pyro.Proxy(uri)
        except NamingError:
            reraise(NamingError, NamingError(E_LOOKUP.format(conninfo)),
                    sys.exc_info()[2])

    def driver_version(self):
        return pyro.__version__

    @cached_property
    def shared_queues(self):
        return self._open()

########NEW FILE########
__FILENAME__ = redis
"""
kombu.transport.redis
=====================

Redis transport.

"""
from __future__ import absolute_import

import numbers
import socket

from bisect import bisect
from collections import namedtuple
from contextlib import contextmanager
from time import time

from amqp import promise

from kombu.exceptions import InconsistencyError, VersionMismatch
from kombu.five import Empty, values, string_t
from kombu.log import get_logger
from kombu.utils import cached_property, uuid
from kombu.utils.eventio import poll, READ, ERR
from kombu.utils.encoding import bytes_to_str
from kombu.utils.json import loads, dumps
from kombu.utils.url import _parse_url

NO_ROUTE_ERROR = """
Cannot route message for exchange {0!r}: Table empty or key no longer exists.
Probably the key ({1!r}) has been removed from the Redis database.
"""

try:
    from billiard.util import register_after_fork
except ImportError:  # pragma: no cover
    try:
        from multiprocessing.util import register_after_fork  # noqa
    except ImportError:
        def register_after_fork(*args, **kwargs):  # noqa
            pass

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None     # noqa

from . import virtual

logger = get_logger('kombu.transport.redis')
crit, warn = logger.critical, logger.warn

DEFAULT_PORT = 6379
DEFAULT_DB = 0

PRIORITY_STEPS = [0, 3, 6, 9]

error_classes_t = namedtuple('error_classes_t', (
    'connection_errors', 'channel_errors',
))

# This implementation may seem overly complex, but I assure you there is
# a good reason for doing it this way.
#
# Consuming from several connections enables us to emulate channels,
# which means we can have different service guarantees for individual
# channels.
#
# So we need to consume messages from multiple connections simultaneously,
# and using epoll means we don't have to do so using multiple threads.
#
# Also it means we can easily use PUBLISH/SUBSCRIBE to do fanout
# exchanges (broadcast), as an alternative to pushing messages to fanout-bound
# queues manually.


def get_redis_error_classes():
    from redis import exceptions
    # This exception suddenly changed name between redis-py versions
    if hasattr(exceptions, 'InvalidData'):
        DataError = exceptions.InvalidData
    else:
        DataError = exceptions.DataError
    return error_classes_t(
        (virtual.Transport.connection_errors + (
            InconsistencyError,
            socket.error,
            IOError,
            OSError,
            exceptions.ConnectionError,
            exceptions.AuthenticationError)),
        (virtual.Transport.channel_errors + (
            DataError,
            exceptions.InvalidResponse,
            exceptions.ResponseError)),
    )


class MutexHeld(Exception):
    pass


@contextmanager
def Mutex(client, name, expire):
    lock_id = uuid()
    i_won = client.setnx(name, lock_id)
    try:
        if i_won:
            client.expire(name, expire)
            yield
        else:
            if not client.ttl(name):
                client.expire(name, expire)
            raise MutexHeld()
    finally:
        if i_won:
            pipe = client.pipeline(True)
            try:
                pipe.watch(name)
                if pipe.get(name) == lock_id:
                    pipe.multi()
                    pipe.delete(name)
                    pipe.execute()
                pipe.unwatch()
            except redis.WatchError:
                pass


class QoS(virtual.QoS):
    restore_at_shutdown = True

    def __init__(self, *args, **kwargs):
        super(QoS, self).__init__(*args, **kwargs)
        self._vrestore_count = 0

    def append(self, message, delivery_tag):
        delivery = message.delivery_info
        EX, RK = delivery['exchange'], delivery['routing_key']
        with self.pipe_or_acquire() as pipe:
            pipe.zadd(self.unacked_index_key, delivery_tag, time()) \
                .hset(self.unacked_key, delivery_tag,
                      dumps([message._raw, EX, RK])) \
                .execute()
            super(QoS, self).append(message, delivery_tag)

    def restore_unacked(self):
        for tag in self._delivered:
            self.restore_by_tag(tag)
        self._delivered.clear()

    def ack(self, delivery_tag):
        self._remove_from_indices(delivery_tag).execute()
        super(QoS, self).ack(delivery_tag)

    def reject(self, delivery_tag, requeue=False):
        if requeue:
            self.restore_by_tag(delivery_tag, leftmost=True)
        self.ack(delivery_tag)

    @contextmanager
    def pipe_or_acquire(self, pipe=None):
        if pipe:
            yield pipe
        else:
            with self.channel.conn_or_acquire() as client:
                yield client.pipeline()

    def _remove_from_indices(self, delivery_tag, pipe=None):
        with self.pipe_or_acquire(pipe) as pipe:
            return pipe.zrem(self.unacked_index_key, delivery_tag) \
                       .hdel(self.unacked_key, delivery_tag)

    def restore_visible(self, start=0, num=10, interval=10):
        self._vrestore_count += 1
        if (self._vrestore_count - 1) % interval:
            return
        with self.channel.conn_or_acquire() as client:
            ceil = time() - self.visibility_timeout
            try:
                with Mutex(client, self.unacked_mutex_key,
                           self.unacked_mutex_expire):
                    visible = client.zrevrangebyscore(
                        self.unacked_index_key, ceil, 0,
                        start=num and start, num=num, withscores=True)
                    for tag, score in visible or []:
                        self.restore_by_tag(tag, client)
            except MutexHeld:
                pass

    def restore_by_tag(self, tag, client=None, leftmost=False):
        with self.channel.conn_or_acquire(client) as client:
            p, _, _ = self._remove_from_indices(
                tag, client.pipeline().hget(self.unacked_key, tag)).execute()
            if p:
                M, EX, RK = loads(bytes_to_str(p))  # json is unicode
                self.channel._do_restore_message(M, EX, RK, client, leftmost)

    @cached_property
    def unacked_key(self):
        return self.channel.unacked_key

    @cached_property
    def unacked_index_key(self):
        return self.channel.unacked_index_key

    @cached_property
    def unacked_mutex_key(self):
        return self.channel.unacked_mutex_key

    @cached_property
    def unacked_mutex_expire(self):
        return self.channel.unacked_mutex_expire

    @cached_property
    def visibility_timeout(self):
        return self.channel.visibility_timeout


class MultiChannelPoller(object):
    eventflags = READ | ERR

    #: Set by :meth:`get` while reading from the socket.
    _in_protected_read = False

    #: Set of one-shot callbacks to call after reading from socket.
    after_read = None

    def __init__(self):
        # active channels
        self._channels = set()
        # file descriptor -> channel map.
        self._fd_to_chan = {}
        # channel -> socket map
        self._chan_to_sock = {}
        # poll implementation (epoll/kqueue/select)
        self.poller = poll()
        # one-shot callbacks called after reading from socket.
        self.after_read = set()

    def close(self):
        for fd in values(self._chan_to_sock):
            try:
                self.poller.unregister(fd)
            except (KeyError, ValueError):
                pass
        self._channels.clear()
        self._fd_to_chan.clear()
        self._chan_to_sock.clear()
        self.poller = None

    def add(self, channel):
        self._channels.add(channel)

    def discard(self, channel):
        self._channels.discard(channel)

    def _on_connection_disconnect(self, connection):
        sock = getattr(connection, '_sock', None)
        if sock is not None:
            self.poller.unregister(sock)

    def _register(self, channel, client, type):
        if (channel, client, type) in self._chan_to_sock:
            self._unregister(channel, client, type)
        if client.connection._sock is None:   # not connected yet.
            client.connection.connect()
        sock = client.connection._sock
        self._fd_to_chan[sock.fileno()] = (channel, type)
        self._chan_to_sock[(channel, client, type)] = sock
        self.poller.register(sock, self.eventflags)

    def _unregister(self, channel, client, type):
        self.poller.unregister(self._chan_to_sock[(channel, client, type)])

    def _register_BRPOP(self, channel):
        """enable BRPOP mode for channel."""
        ident = channel, channel.client, 'BRPOP'
        if channel.client.connection._sock is None or \
                ident not in self._chan_to_sock:
            channel._in_poll = False
            self._register(*ident)

        if not channel._in_poll:  # send BRPOP
            channel._brpop_start()

    def _register_LISTEN(self, channel):
        """enable LISTEN mode for channel."""
        if channel.subclient.connection._sock is None:
            channel._in_listen = False
            self._register(channel, channel.subclient, 'LISTEN')
        if not channel._in_listen:
            channel._subscribe()  # send SUBSCRIBE

    def on_poll_start(self):
        for channel in self._channels:
            if channel.active_queues:           # BRPOP mode?
                if channel.qos.can_consume():
                    self._register_BRPOP(channel)
            if channel.active_fanout_queues:    # LISTEN mode?
                self._register_LISTEN(channel)

    def on_poll_init(self, poller):
        self.poller = poller
        for channel in self._channels:
            return channel.qos.restore_visible(
                num=channel.unacked_restore_limit,
            )

    def maybe_restore_messages(self):
        for channel in self._channels:
            if channel.active_queues:
                # only need to do this once, as they are not local to channel.
                return channel.qos.restore_visible(
                    num=channel.unacked_restore_limit,
                )

    def on_readable(self, fileno):
        chan, type = self._fd_to_chan[fileno]
        if chan.qos.can_consume():
            return chan.handlers[type]()

    def handle_event(self, fileno, event):
        if event & READ:
            return self.on_readable(fileno), self
        elif event & ERR:
            chan, type = self._fd_to_chan[fileno]
            chan._poll_error(type)

    def get(self, timeout=None):
        self._in_protected_read = True
        try:
            for channel in self._channels:
                if channel.active_queues:           # BRPOP mode?
                    if channel.qos.can_consume():
                        self._register_BRPOP(channel)
                if channel.active_fanout_queues:    # LISTEN mode?
                    self._register_LISTEN(channel)

            events = self.poller.poll(timeout)
            for fileno, event in events or []:
                ret = self.handle_event(fileno, event)
                if ret:
                    return ret

            # - no new data, so try to restore messages.
            # - reset active redis commands.
            self.maybe_restore_messages()

            raise Empty()
        finally:
            self._in_protected_read = False
            while self.after_read:
                try:
                    fun = self.after_read.pop()
                except KeyError:
                    break
                else:
                    fun()

    @property
    def fds(self):
        return self._fd_to_chan


class Channel(virtual.Channel):
    QoS = QoS

    _client = None
    _subclient = None
    supports_fanout = True
    keyprefix_queue = '_kombu.binding.%s'
    keyprefix_fanout = '/{db}.'
    sep = '\x06\x16'
    _in_poll = False
    _in_listen = False
    _fanout_queues = {}
    ack_emulation = True
    unacked_key = 'unacked'
    unacked_index_key = 'unacked_index'
    unacked_mutex_key = 'unacked_mutex'
    unacked_mutex_expire = 300  # 5 minutes
    unacked_restore_limit = None
    visibility_timeout = 3600   # 1 hour
    priority_steps = PRIORITY_STEPS
    socket_timeout = None
    max_connections = 10
    #: Transport option to enable disable fanout keyprefix.
    #: Should be enabled by default, but that is not
    #: backwards compatible.  Can also be string, in which
    #: case it changes the default prefix ('/{db}.') into to something
    #: else.  The prefix must include a leading slash and a trailing dot.
    fanout_prefix = False

    #: If enabled the fanout exchange will support patterns in routing
    #: and binding keys (like a topic exchange but using PUB/SUB).
    #: This will be enabled by default in a future version.
    fanout_patterns = False
    _pool = None

    from_transport_options = (
        virtual.Channel.from_transport_options +
        ('ack_emulation',
         'unacked_key',
         'unacked_index_key',
         'unacked_mutex_key',
         'unacked_mutex_expire',
         'visibility_timeout',
         'unacked_restore_limit',
         'fanout_prefix',
         'fanout_patterns',
         'socket_timeout',
         'max_connections',
         'priority_steps')  # <-- do not add comma here!
    )

    def __init__(self, *args, **kwargs):
        super_ = super(Channel, self)
        super_.__init__(*args, **kwargs)

        if not self.ack_emulation:  # disable visibility timeout
            self.QoS = virtual.QoS

        self._queue_cycle = []
        self.Client = self._get_client()
        self.ResponseError = self._get_response_error()
        self.active_fanout_queues = set()
        self.auto_delete_queues = set()
        self._fanout_to_queue = {}
        self.handlers = {'BRPOP': self._brpop_read, 'LISTEN': self._receive}

        if self.fanout_prefix:
            if isinstance(self.fanout_prefix, string_t):
                self.keyprefix_fanout = self.fanout_prefix
        else:
            # previous versions did not set a fanout, so cannot enable
            # by default.
            self.keyprefix_fanout = ''

        # Evaluate connection.
        try:
            self.client.info()
        except Exception:
            if self._pool:
                self._pool.disconnect()
            raise

        self.connection.cycle.add(self)  # add to channel poller.
        # copy errors, in case channel closed but threads still
        # are still waiting for data.
        self.connection_errors = self.connection.connection_errors

        register_after_fork(self, self._after_fork)

    def _after_fork(self):
        if self._pool is not None:
            self._pool.disconnect()

    def _on_connection_disconnect(self, connection):
        if self.connection and self.connection.cycle:
            self.connection.cycle._on_connection_disconnect(connection)

    def _do_restore_message(self, payload, exchange, routing_key,
                            client=None, leftmost=False):
        with self.conn_or_acquire(client) as client:
            try:
                try:
                    payload['headers']['redelivered'] = True
                except KeyError:
                    pass
                for queue in self._lookup(exchange, routing_key):
                    (client.lpush if leftmost else client.rpush)(
                        queue, dumps(payload),
                    )
            except Exception:
                crit('Could not restore message: %r', payload, exc_info=True)

    def _restore(self, message, leftmost=False):
        tag = message.delivery_tag
        with self.conn_or_acquire() as client:
            P, _ = client.pipeline() \
                .hget(self.unacked_key, tag) \
                .hdel(self.unacked_key, tag) \
                .execute()
            if P:
                M, EX, RK = loads(bytes_to_str(P))  # json is unicode
                self._do_restore_message(M, EX, RK, client, leftmost)

    def _restore_at_beginning(self, message):
        return self._restore(message, leftmost=True)

    def basic_consume(self, queue, *args, **kwargs):
        if queue in self._fanout_queues:
            exchange, _ = self._fanout_queues[queue]
            self.active_fanout_queues.add(queue)
            self._fanout_to_queue[exchange] = queue
        ret = super(Channel, self).basic_consume(queue, *args, **kwargs)
        self._update_cycle()
        return ret

    def basic_cancel(self, consumer_tag):
        # If we are busy reading messages we may experience
        # a race condition where a message is consumed after
        # cancelling, so we must delay this operation until reading
        # is complete (Issue celery/celery#1773).
        connection = self.connection
        if connection:
            if connection.cycle._in_protected_read:
                return connection.cycle.after_read.add(
                    promise(self._basic_cancel, (consumer_tag, )),
                )
            return self._basic_cancel(consumer_tag)

    def _basic_cancel(self, consumer_tag):
        try:
            queue = self._tag_to_queue[consumer_tag]
        except KeyError:
            return
        try:
            self.active_fanout_queues.remove(queue)
        except KeyError:
            pass
        else:
            self._unsubscribe_from(queue)
        try:
            exchange, _ = self._fanout_queues[queue]
            self._fanout_to_queue.pop(exchange)
        except KeyError:
            pass
        ret = super(Channel, self).basic_cancel(consumer_tag)
        self._update_cycle()
        return ret

    def _get_publish_topic(self, exchange, routing_key):
        if routing_key and self.fanout_patterns:
            return ''.join([self.keyprefix_fanout, exchange, '/', routing_key])
        return ''.join([self.keyprefix_fanout, exchange])

    def _get_subscribe_topic(self, queue):
        exchange, routing_key = self._fanout_queues[queue]
        return self._get_publish_topic(exchange, routing_key)

    def _subscribe(self):
        keys = [self._get_subscribe_topic(queue)
                for queue in self.active_fanout_queues]
        if not keys:
            return
        c = self.subclient
        if c.connection._sock is None:
            c.connection.connect()
        self._in_listen = True
        c.psubscribe(keys)

    def _unsubscribe_from(self, queue):
        topic = self._get_subscribe_topic(queue)
        c = self.subclient
        should_disconnect = False
        if c.connection._sock is None:
            c.connection.connect()
            should_disconnect = True
        try:
            c.unsubscribe([topic])
        finally:
            if should_disconnect and c.connection:
                c.connection.disconnect()

    def _handle_message(self, client, r):
        if bytes_to_str(r[0]) == 'unsubscribe' and r[2] == 0:
            client.subscribed = False
        elif bytes_to_str(r[0]) == 'pmessage':
            return {'type':    r[0], 'pattern': r[1],
                    'channel': r[2], 'data':    r[3]}
        else:
            return {'type':    r[0], 'pattern': None,
                    'channel': r[1], 'data':    r[2]}

    def _receive(self):
        c = self.subclient
        response = None
        try:
            response = c.parse_response()
        except self.connection_errors:
            self._in_listen = False
            raise Empty()
        if response is not None:
            payload = self._handle_message(c, response)
            if bytes_to_str(payload['type']).endswith('message'):
                channel = bytes_to_str(payload['channel'])
                if payload['data']:
                    if channel[0] == '/':
                        _, _, channel = channel.partition('.')
                    try:
                        message = loads(bytes_to_str(payload['data']))
                    except (TypeError, ValueError):
                        warn('Cannot process event on channel %r: %s',
                             channel, repr(payload)[:4096], exc_info=1)
                        raise Empty()
                    exchange = channel.split('/', 1)[0]
                    return message, self._fanout_to_queue[exchange]
        raise Empty()

    def _brpop_start(self, timeout=1):
        queues = self._consume_cycle()
        if not queues:
            return
        keys = [self._q_for_pri(queue, pri) for pri in PRIORITY_STEPS
                for queue in queues] + [timeout or 0]
        self._in_poll = True
        self.client.connection.send_command('BRPOP', *keys)

    def _brpop_read(self, **options):
        try:
            try:
                dest__item = self.client.parse_response(self.client.connection,
                                                        'BRPOP',
                                                        **options)
            except self.connection_errors:
                # if there's a ConnectionError, disconnect so the next
                # iteration will reconnect automatically.
                self.client.connection.disconnect()
                raise Empty()
            if dest__item:
                dest, item = dest__item
                dest = bytes_to_str(dest).rsplit(self.sep, 1)[0]
                self._rotate_cycle(dest)
                return loads(bytes_to_str(item)), dest
            else:
                raise Empty()
        finally:
            self._in_poll = False

    def _poll_error(self, type, **options):
        if type == 'LISTEN':
            self.subclient.parse_response()
        else:
            self.client.parse_response(self.client.connection, type)

    def _get(self, queue):
        with self.conn_or_acquire() as client:
            for pri in PRIORITY_STEPS:
                item = client.rpop(self._q_for_pri(queue, pri))
                if item:
                    return loads(bytes_to_str(item))
            raise Empty()

    def _size(self, queue):
        with self.conn_or_acquire() as client:
            cmds = client.pipeline()
            for pri in PRIORITY_STEPS:
                cmds = cmds.llen(self._q_for_pri(queue, pri))
            sizes = cmds.execute()
            return sum(size for size in sizes
                       if isinstance(size, numbers.Integral))

    def _q_for_pri(self, queue, pri):
        pri = self.priority(pri)
        return '%s%s%s' % ((queue, self.sep, pri) if pri else (queue, '', ''))

    def priority(self, n):
        steps = self.priority_steps
        return steps[bisect(steps, n) - 1]

    def _put(self, queue, message, **kwargs):
        """Deliver message."""
        pri = self._get_message_priority(message)

        with self.conn_or_acquire() as client:
            client.lpush(self._q_for_pri(queue, pri), dumps(message))

    def _put_fanout(self, exchange, message, routing_key, **kwargs):
        """Deliver fanout message."""
        with self.conn_or_acquire() as client:
            client.publish(
                self._get_publish_topic(exchange, routing_key),
                dumps(message),
            )

    def _new_queue(self, queue, auto_delete=False, **kwargs):
        if auto_delete:
            self.auto_delete_queues.add(queue)

    def _queue_bind(self, exchange, routing_key, pattern, queue):
        if self.typeof(exchange).type == 'fanout':
            # Mark exchange as fanout.
            self._fanout_queues[queue] = (
                exchange, routing_key.replace('#', '*'),
            )
        with self.conn_or_acquire() as client:
            client.sadd(self.keyprefix_queue % (exchange, ),
                        self.sep.join([routing_key or '',
                                       pattern or '',
                                       queue or '']))

    def _delete(self, queue, exchange, routing_key, pattern, *args):
        self.auto_delete_queues.discard(queue)
        with self.conn_or_acquire() as client:
            client.srem(self.keyprefix_queue % (exchange, ),
                        self.sep.join([routing_key or '',
                                       pattern or '',
                                       queue or '']))
            cmds = client.pipeline()
            for pri in PRIORITY_STEPS:
                cmds = cmds.delete(self._q_for_pri(queue, pri))
            cmds.execute()

    def _has_queue(self, queue, **kwargs):
        with self.conn_or_acquire() as client:
            cmds = client.pipeline()
            for pri in PRIORITY_STEPS:
                cmds = cmds.exists(self._q_for_pri(queue, pri))
            return any(cmds.execute())

    def get_table(self, exchange):
        key = self.keyprefix_queue % exchange
        with self.conn_or_acquire() as client:
            values = client.smembers(key)
            if not values:
                raise InconsistencyError(NO_ROUTE_ERROR.format(exchange, key))
            return [tuple(bytes_to_str(val).split(self.sep)) for val in values]

    def _purge(self, queue):
        with self.conn_or_acquire() as client:
            cmds = client.pipeline()
            for pri in PRIORITY_STEPS:
                priq = self._q_for_pri(queue, pri)
                cmds = cmds.llen(priq).delete(priq)
            sizes = cmds.execute()
            return sum(sizes[::2])

    def close(self):
        if self._pool:
            self._pool.disconnect()
        if not self.closed:
            # remove from channel poller.
            self.connection.cycle.discard(self)

            # delete fanout bindings
            for queue in self._fanout_queues:
                if queue in self.auto_delete_queues:
                    self.queue_delete(queue)

            self._close_clients()

        super(Channel, self).close()

    def _close_clients(self):
        # Close connections
        for attr in 'client', 'subclient':
            try:
                self.__dict__[attr].connection.disconnect()
            except (KeyError, AttributeError, self.ResponseError):
                pass

    def _prepare_virtual_host(self, vhost):
        if not isinstance(vhost, numbers.Integral):
            if not vhost or vhost == '/':
                vhost = DEFAULT_DB
            elif vhost.startswith('/'):
                vhost = vhost[1:]
            try:
                vhost = int(vhost)
            except ValueError:
                raise ValueError(
                    'Database is int between 0 and limit - 1, not {0}'.format(
                        vhost,
                    ))
        return vhost

    def _connparams(self):
        conninfo = self.connection.client
        connparams = {'host': conninfo.hostname or '127.0.0.1',
                      'port': conninfo.port or DEFAULT_PORT,
                      'virtual_host': conninfo.virtual_host,
                      'password': conninfo.password,
                      'max_connections': self.max_connections,
                      'socket_timeout': self.socket_timeout}
        host = connparams['host']
        if '://' in host:
            scheme, _, _, _, _, path, query = _parse_url(host)
            if scheme == 'socket':
                connparams.update({
                    'connection_class': redis.UnixDomainSocketConnection,
                    'path': '/' + path}, **query)
            connparams.pop('host', None)
            connparams.pop('port', None)
        connparams['db'] = self._prepare_virtual_host(
            connparams.pop('virtual_host', None))

        channel = self
        connection_cls = (
            connparams.get('connection_class') or
            redis.Connection
            )

        class Connection(connection_cls):
            def disconnect(self):
                channel._on_connection_disconnect(self)
                super(Connection, self).disconnect()
        connparams['connection_class'] = Connection

        return connparams

    def _create_client(self):
        return self.Client(connection_pool=self.pool)

    def _get_pool(self):
        params = self._connparams()
        self.keyprefix_fanout = self.keyprefix_fanout.format(db=params['db'])
        return redis.ConnectionPool(**params)

    def _get_client(self):
        if redis.VERSION < (2, 4, 4):
            raise VersionMismatch(
                'Redis transport requires redis-py versions 2.4.4 or later. '
                'You have {0.__version__}'.format(redis))

        # KombuRedis maintains a connection attribute on it's instance and
        # uses that when executing commands
        # This was added after redis-py was changed.
        class KombuRedis(redis.Redis):  # pragma: no cover

            def __init__(self, *args, **kwargs):
                super(KombuRedis, self).__init__(*args, **kwargs)
                self.connection = self.connection_pool.get_connection('_')

        return KombuRedis

    @contextmanager
    def conn_or_acquire(self, client=None):
        if client:
            yield client
        else:
            if self._in_poll:
                client = self._create_client()
                try:
                    yield client
                finally:
                    self.pool.release(client.connection)
            else:
                yield self.client

    @property
    def pool(self):
        if self._pool is None:
            self._pool = self._get_pool()
        return self._pool

    @cached_property
    def client(self):
        """Client used to publish messages, BRPOP etc."""
        return self._create_client()

    @cached_property
    def subclient(self):
        """Pub/Sub connection used to consume fanout queues."""
        client = self._create_client()
        pubsub = client.pubsub()
        pool = pubsub.connection_pool
        pubsub.connection = pool.get_connection('pubsub', pubsub.shard_hint)
        return pubsub

    def _update_cycle(self):
        """Update fair cycle between queues.

        We cycle between queues fairly to make sure that
        each queue is equally likely to be consumed from,
        so that a very busy queue will not block others.

        This works by using Redis's `BRPOP` command and
        by rotating the most recently used queue to the
        and of the list.  See Kombu github issue #166 for
        more discussion of this method.

        """
        self._queue_cycle = list(self.active_queues)

    def _consume_cycle(self):
        """Get a fresh list of queues from the queue cycle."""
        active = len(self.active_queues)
        return self._queue_cycle[0:active]

    def _rotate_cycle(self, used):
        """Move most recently used queue to end of list."""
        cycle = self._queue_cycle
        try:
            cycle.append(cycle.pop(cycle.index(used)))
        except ValueError:
            pass

    def _get_response_error(self):
        from redis import exceptions
        return exceptions.ResponseError

    @property
    def active_queues(self):
        """Set of queues being consumed from (excluding fanout queues)."""
        return {queue for queue in self._active_queues
                if queue not in self.active_fanout_queues}


class Transport(virtual.Transport):
    Channel = Channel

    polling_interval = None  # disable sleep between unsuccessful polls.
    default_port = DEFAULT_PORT
    supports_ev = True
    driver_type = 'redis'
    driver_name = 'redis'

    def __init__(self, *args, **kwargs):
        super(Transport, self).__init__(*args, **kwargs)

        # Get redis-py exceptions.
        self.connection_errors, self.channel_errors = self._get_errors()
        # All channels share the same poller.
        self.cycle = MultiChannelPoller()

    def driver_version(self):
        return redis.__version__

    def register_with_event_loop(self, connection, loop):
        cycle = self.cycle
        cycle.on_poll_init(loop.poller)
        cycle_poll_start = cycle.on_poll_start
        add_reader = loop.add_reader
        on_readable = self.on_readable

        def _on_disconnect(connection):
            if connection._sock:
                loop.remove(connection._sock)
        cycle._on_connection_disconnect = _on_disconnect

        def on_poll_start():
            cycle_poll_start()
            [add_reader(fd, on_readable, fd) for fd in cycle.fds]
        loop.on_tick.add(on_poll_start)
        loop.call_repeatedly(10, cycle.maybe_restore_messages)

    def on_readable(self, fileno):
        """Handle AIO event for one of our file descriptors."""
        item = self.cycle.on_readable(fileno)
        if item:
            message, queue = item
            if not queue or queue not in self._callbacks:
                raise KeyError(
                    'Message for queue {0!r} without consumers: {1}'.format(
                        queue, message))
            self._callbacks[queue](message)

    def _get_errors(self):
        """Utility to import redis-py's exceptions at runtime."""
        return get_redis_error_classes()

########NEW FILE########
__FILENAME__ = SLMQ
"""
kombu.transport.SLMQ
====================

SoftLayer Message Queue transport.

"""
from __future__ import absolute_import

import socket
import string

import os

from kombu.five import Empty, text_t
from kombu.utils import cached_property  # , uuid
from kombu.utils.encoding import bytes_to_str, safe_str
from kombu.utils.json import loads, dumps

from . import virtual

try:
    from softlayer_messaging import get_client
    from softlayer_messaging.errors import ResponseError
except ImportError:  # pragma: no cover
    get_client = ResponseError = None  # noqa

# dots are replaced by dash, all other punctuation replaced by underscore.
CHARS_REPLACE_TABLE = {
    ord(c): 0x5f for c in string.punctuation if c not in '_'
}


class Channel(virtual.Channel):
    default_visibility_timeout = 1800  # 30 minutes.
    domain_format = 'kombu%(vhost)s'
    _slmq = None
    _queue_cache = {}
    _noack_queues = set()

    def __init__(self, *args, **kwargs):
        if get_client is None:
            raise ImportError(
                'SLMQ transport requires the softlayer_messaging library',
            )
        super(Channel, self).__init__(*args, **kwargs)
        queues = self.slmq.queues()
        for queue in queues:
            self._queue_cache[queue] = queue

    def basic_consume(self, queue, no_ack, *args, **kwargs):
        if no_ack:
            self._noack_queues.add(queue)
        return super(Channel, self).basic_consume(queue, no_ack,
                                                  *args, **kwargs)

    def basic_cancel(self, consumer_tag):
        if consumer_tag in self._consumers:
            queue = self._tag_to_queue[consumer_tag]
            self._noack_queues.discard(queue)
        return super(Channel, self).basic_cancel(consumer_tag)

    def entity_name(self, name, table=CHARS_REPLACE_TABLE):
        """Format AMQP queue name into a valid SLQS queue name."""
        return text_t(safe_str(name)).translate(table)

    def _new_queue(self, queue, **kwargs):
        """Ensures a queue exists in SLQS."""
        queue = self.entity_name(self.queue_name_prefix + queue)
        try:
            return self._queue_cache[queue]
        except KeyError:
            try:
                self.slmq.create_queue(
                    queue, visibility_timeout=self.visibility_timeout)
            except ResponseError:
                pass
            q = self._queue_cache[queue] = self.slmq.queue(queue)
            return q

    def _delete(self, queue, *args):
        """delete queue by name."""
        queue_name = self.entity_name(queue)
        self._queue_cache.pop(queue_name, None)
        self.slmq.queue(queue_name).delete(force=True)
        super(Channel, self)._delete(queue_name)

    def _put(self, queue, message, **kwargs):
        """Put message onto queue."""
        q = self._new_queue(queue)
        q.push(dumps(message))

    def _get(self, queue):
        """Try to retrieve a single message off ``queue``."""
        q = self._new_queue(queue)
        rs = q.pop(1)
        if rs['items']:
            m = rs['items'][0]
            payload = loads(bytes_to_str(m['body']))
            if queue in self._noack_queues:
                q.message(m['id']).delete()
            else:
                payload['properties']['delivery_info'].update({
                    'slmq_message_id': m['id'], 'slmq_queue_name': q.name})
            return payload
        raise Empty()

    def basic_ack(self, delivery_tag):
        delivery_info = self.qos.get(delivery_tag).delivery_info
        try:
            queue = delivery_info['slmq_queue_name']
        except KeyError:
            pass
        else:
            self.delete_message(queue, delivery_info['slmq_message_id'])
        super(Channel, self).basic_ack(delivery_tag)

    def _size(self, queue):
        """Return the number of messages in a queue."""
        return self._new_queue(queue).detail()['message_count']

    def _purge(self, queue):
        """Delete all current messages in a queue."""
        q = self._new_queue(queue)
        n = 0
        l = q.pop(10)
        while l['items']:
            for m in l['items']:
                self.delete_message(queue, m['id'])
                n += 1
            l = q.pop(10)
        return n

    def delete_message(self, queue, message_id):
        q = self.slmq.queue(self.entity_name(queue))
        return q.message(message_id).delete()

    @property
    def slmq(self):
        if self._slmq is None:
            conninfo = self.conninfo
            account = os.environ.get('SLMQ_ACCOUNT', conninfo.virtual_host)
            user = os.environ.get('SL_USERNAME', conninfo.userid)
            api_key = os.environ.get('SL_API_KEY', conninfo.password)
            host = os.environ.get('SLMQ_HOST', conninfo.hostname)
            port = os.environ.get('SLMQ_PORT', conninfo.port)
            secure = bool(os.environ.get(
                'SLMQ_SECURE', self.transport_options.get('secure')) or True,
            )
            endpoint = '{0}://{1}{2}'.format(
                'https' if secure else 'http', host,
                ':{0}'.format(port) if port else '',
            )

            self._slmq = get_client(account, endpoint=endpoint)
            self._slmq.authenticate(user, api_key)
        return self._slmq

    @property
    def conninfo(self):
        return self.connection.client

    @property
    def transport_options(self):
        return self.connection.client.transport_options

    @cached_property
    def visibility_timeout(self):
        return (self.transport_options.get('visibility_timeout') or
                self.default_visibility_timeout)

    @cached_property
    def queue_name_prefix(self):
        return self.transport_options.get('queue_name_prefix', '')


class Transport(virtual.Transport):
    Channel = Channel

    polling_interval = 1
    default_port = None
    connection_errors = (
        virtual.Transport.connection_errors + (
            ResponseError, socket.error
        )
    )

########NEW FILE########
__FILENAME__ = models
from __future__ import absolute_import

import datetime

from sqlalchemy import (Column, Integer, String, Text, DateTime,
                        Sequence, Boolean, ForeignKey, SmallInteger)
from sqlalchemy.orm import relation
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.schema import MetaData

class_registry = {}
metadata = MetaData()
ModelBase = declarative_base(metadata=metadata, class_registry=class_registry)


class Queue(object):
    __table_args__ = {'sqlite_autoincrement': True, 'mysql_engine': 'InnoDB'}

    id = Column(Integer, Sequence('queue_id_sequence'), primary_key=True,
                autoincrement=True)
    name = Column(String(200), unique=True)

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return '<Queue({self.name})>'.format(self=self)

    @declared_attr
    def messages(cls):
        return relation('Message', backref='queue', lazy='noload')


class Message(object):
    __table_args__ = {'sqlite_autoincrement': True, 'mysql_engine': 'InnoDB'}

    id = Column(Integer, Sequence('message_id_sequence'),
                primary_key=True, autoincrement=True)
    visible = Column(Boolean, default=True, index=True)
    sent_at = Column('timestamp', DateTime, nullable=True, index=True,
                     onupdate=datetime.datetime.now)
    payload = Column(Text, nullable=False)
    version = Column(SmallInteger, nullable=False, default=1)

    __mapper_args__ = {'version_id_col': version}

    def __init__(self, payload, queue):
        self.payload = payload
        self.queue = queue

    def __str__(self):
        return '<Message: {0.sent_at} {0.payload} {0.queue_id}>'.format(self)

    @declared_attr
    def queue_id(self):
        return Column(
            Integer,
            ForeignKey(
                '%s.id' % class_registry['Queue'].__tablename__,
                name='FK_kombu_message_queue'
            )
        )

########NEW FILE########
__FILENAME__ = SQS
"""
kombu.transport.SQS
===================

Amazon SQS transport module for Kombu. This package implements an AMQP-like
interface on top of Amazons SQS service, with the goal of being optimized for
high performance and reliability.

The default settings for this module are focused now on high performance in
task queue situations where tasks are small, idempotent and run very fast.

SQS Features supported by this transport:
  Long Polling:
    http://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/
      sqs-long-polling.html

    Long polling is enabled by setting the `wait_time_seconds` transport
    option to a number > 1. Amazon supports up to 20 seconds. This is
    disabled for now, but will be enabled by default in the near future.

  Batch API Actions:
   http://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/
     sqs-batch-api.html

    The default behavior of the SQS Channel.drain_events() method is to
    request up to the 'prefetch_count' messages on every request to SQS.
    These messages are stored locally in a deque object and passed back
    to the Transport until the deque is empty, before triggering a new
    API call to Amazon.

    This behavior dramatically speeds up the rate that you can pull tasks
    from SQS when you have short-running tasks (or a large number of workers).

    When a Celery worker has multiple queues to monitor, it will pull down
    up to 'prefetch_count' messages from queueA and work on them all before
    moving on to queueB. If queueB is empty, it will wait up until
    'polling_interval' expires before moving back and checking on queueA.
"""

from __future__ import absolute_import

import collections
import socket
import string

import boto
from boto import exception
from boto import sdb as _sdb
from boto import sqs as _sqs
from boto.sdb.domain import Domain
from boto.sdb.connection import SDBConnection
from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message

from kombu.five import Empty, range, text_t
from kombu.log import get_logger
from kombu.utils import cached_property, uuid
from kombu.utils.encoding import bytes_to_str, safe_str
from kombu.utils.json import loads, dumps
from kombu.transport.virtual import scheduling

from . import virtual

logger = get_logger(__name__)

# dots are replaced by dash, all other punctuation
# replaced by underscore.
CHARS_REPLACE_TABLE = {
    ord(c): 0x5f for c in string.punctuation if c not in '-_.'
}
CHARS_REPLACE_TABLE[0x2e] = 0x2d  # '.' -> '-'


def maybe_int(x):
    try:
        return int(x)
    except ValueError:
        return x
BOTO_VERSION = tuple(maybe_int(part) for part in boto.__version__.split('.'))
W_LONG_POLLING = BOTO_VERSION >= (2, 8)

#: SQS bulk get supports a maximum of 10 messages at a time.
SQS_MAX_MESSAGES = 10


class Table(Domain):
    """Amazon SimpleDB domain describing the message routing table."""
    # caches queues already bound, so we don't have to declare them again.
    _already_bound = set()

    def routes_for(self, exchange):
        """Iterator giving all routes for an exchange."""
        return self.select("""WHERE exchange = '%s'""" % exchange)

    def get_queue(self, queue):
        """Get binding for queue."""
        qid = self._get_queue_id(queue)
        if qid:
            return self.get_item(qid)

    def create_binding(self, queue):
        """Get binding item for queue.

        Creates the item if it doesn't exist.

        """
        item = self.get_queue(queue)
        if item:
            return item, item['id']
        id = uuid()
        return self.new_item(id), id

    def queue_bind(self, exchange, routing_key, pattern, queue):
        if queue not in self._already_bound:
            binding, id = self.create_binding(queue)
            binding.update(exchange=exchange,
                           routing_key=routing_key or '',
                           pattern=pattern or '',
                           queue=queue or '',
                           id=id)
            binding.save()
            self._already_bound.add(queue)

    def queue_delete(self, queue):
        """delete queue by name."""
        self._already_bound.discard(queue)
        item = self._get_queue_item(queue)
        if item:
            self.delete_item(item)

    def exchange_delete(self, exchange):
        """Delete all routes for `exchange`."""
        for item in self.routes_for(exchange):
            self.delete_item(item['id'])

    def get_item(self, item_name):
        """Uses `consistent_read` by default."""
        # Domain is an old-style class, can't use super().
        for consistent_read in (False, True):
            item = Domain.get_item(self, item_name, consistent_read)
            if item:
                return item

    def select(self, query='', next_token=None,
               consistent_read=True, max_items=None):
        """Uses `consistent_read` by default."""
        query = """SELECT * FROM `%s` %s""" % (self.name, query)
        return Domain.select(self, query, next_token,
                             consistent_read, max_items)

    def _try_first(self, query='', **kwargs):
        for c in (False, True):
            for item in self.select(query, consistent_read=c, **kwargs):
                return item

    def get_exchanges(self):
        return list({i['exchange'] for i in self.select()})

    def _get_queue_item(self, queue):
        return self._try_first("""WHERE queue = '%s' limit 1""" % queue)

    def _get_queue_id(self, queue):
        item = self._get_queue_item(queue)
        if item:
            return item['id']


class Channel(virtual.Channel):
    Table = Table

    default_region = 'us-east-1'
    default_visibility_timeout = 1800  # 30 minutes.
    default_wait_time_seconds = 0  # disabled see #198
    domain_format = 'kombu%(vhost)s'
    _sdb = None
    _sqs = None
    _queue_cache = {}
    _noack_queues = set()

    def __init__(self, *args, **kwargs):
        super(Channel, self).__init__(*args, **kwargs)

        # SQS blows up when you try to create a new queue if one already
        # exists with a different visibility_timeout, so this prepopulates
        # the queue_cache to protect us from recreating
        # queues that are known to already exist.
        queues = self.sqs.get_all_queues(prefix=self.queue_name_prefix)
        for queue in queues:
            self._queue_cache[queue.name] = queue
        self._fanout_queues = set()

        # The drain_events() method stores extra messages in a local
        # Deque object. This allows multiple messages to be requested from
        # SQS at once for performance, but maintains the same external API
        # to the caller of the drain_events() method.
        self._queue_message_cache = collections.deque()

    def basic_consume(self, queue, no_ack, *args, **kwargs):
        if no_ack:
            self._noack_queues.add(queue)
        return super(Channel, self).basic_consume(
            queue, no_ack, *args, **kwargs
        )

    def basic_cancel(self, consumer_tag):
        if consumer_tag in self._consumers:
            queue = self._tag_to_queue[consumer_tag]
            self._noack_queues.discard(queue)
        return super(Channel, self).basic_cancel(consumer_tag)

    def drain_events(self, timeout=None):
        """Return a single payload message from one of our queues.

        :raises Empty: if no messages available.

        """
        # If we're not allowed to consume or have no consumers, raise Empty
        if not self._consumers or not self.qos.can_consume():
            raise Empty()
        message_cache = self._queue_message_cache

        # Check if there are any items in our buffer. If there are any, pop
        # off that queue first.
        try:
            return message_cache.popleft()
        except IndexError:
            pass

        # At this point, go and get more messages from SQS
        res, queue = self._poll(self.cycle, timeout=timeout)
        message_cache.extend((r, queue) for r in res)

        # Now try to pop off the queue again.
        try:
            return message_cache.popleft()
        except IndexError:
            raise Empty()

    def _reset_cycle(self):
        """Reset the consume cycle.

        :returns: a FairCycle object that points to our _get_bulk() method
          rather than the standard _get() method. This allows for multiple
          messages to be returned at once from SQS (based on the prefetch
          limit).

        """
        self._cycle = scheduling.FairCycle(
            self._get_bulk, self._active_queues, Empty,
        )

    def entity_name(self, name, table=CHARS_REPLACE_TABLE):
        """Format AMQP queue name into a legal SQS queue name."""
        return text_t(safe_str(name)).translate(table)

    def _new_queue(self, queue, **kwargs):
        """Ensure a queue with given name exists in SQS."""
        # Translate to SQS name for consistency with initial
        # _queue_cache population.
        queue = self.entity_name(self.queue_name_prefix + queue)
        try:
            return self._queue_cache[queue]
        except KeyError:
            q = self._queue_cache[queue] = self.sqs.create_queue(
                queue, self.visibility_timeout,
            )
            return q

    def queue_bind(self, queue, exchange=None, routing_key='',
                   arguments=None, **kwargs):
        super(Channel, self).queue_bind(queue, exchange, routing_key,
                                        arguments, **kwargs)
        if self.typeof(exchange).type == 'fanout':
            self._fanout_queues.add(queue)

    def _queue_bind(self, *args):
        """Bind ``queue`` to ``exchange`` with routing key.

        Route will be stored in SDB if so enabled.

        """
        if self.supports_fanout:
            self.table.queue_bind(*args)

    def get_table(self, exchange):
        """Get routing table.

        Retrieved from SDB if :attr:`supports_fanout`.

        """
        if self.supports_fanout:
            return [(r['routing_key'], r['pattern'], r['queue'])
                    for r in self.table.routes_for(exchange)]
        return super(Channel, self).get_table(exchange)

    def get_exchanges(self):
        if self.supports_fanout:
            return self.table.get_exchanges()
        return super(Channel, self).get_exchanges()

    def _delete(self, queue, *args):
        """delete queue by name."""
        if self.supports_fanout:
            self.table.queue_delete(queue)
        super(Channel, self)._delete(queue)
        self._queue_cache.pop(queue, None)

    def exchange_delete(self, exchange, **kwargs):
        """Delete exchange by name."""
        if self.supports_fanout:
            self.table.exchange_delete(exchange)
        super(Channel, self).exchange_delete(exchange, **kwargs)

    def _has_queue(self, queue, **kwargs):
        """Return True if ``queue`` was previously declared."""
        if self.supports_fanout:
            return bool(self.table.get_queue(queue))
        return super(Channel, self)._has_queue(queue)

    def _put(self, queue, message, **kwargs):
        """Put message onto queue."""
        q = self._new_queue(queue)
        m = Message()
        m.set_body(dumps(message))
        q.write(m)

    def _put_fanout(self, exchange, message, routing_key, **kwargs):
        """Deliver fanout message to all queues in ``exchange``."""
        for route in self.table.routes_for(exchange):
            self._put(route['queue'], message, **kwargs)

    def _get_from_sqs(self, queue, count=1):
        """Retrieve messages from SQS and returns the raw SQS message objects.

        :returns: List of SQS message objects

        """
        q = self._new_queue(queue)
        if W_LONG_POLLING and queue not in self._fanout_queues:
            return q.get_messages(
                count, wait_time_seconds=self.wait_time_seconds,
            )
        else:  # boto < 2.8
            return q.get_messages(count)

    def _message_to_python(self, message, queue_name, queue):
        payload = loads(bytes_to_str(message.get_body()))
        if queue_name in self._noack_queues:
            queue.delete_message(message)
        else:
            payload['properties']['delivery_info'].update({
                'sqs_message': message, 'sqs_queue': queue,
            })
        return payload

    def _messages_to_python(self, messages, queue):
        """Convert a list of SQS Message objects into Payloads.

        This method handles converting SQS Message objects into
        Payloads, and appropriately updating the queue depending on
        the 'ack' settings for that queue.

        :param messages: A list of SQS Message objects.
        :param queue: String name representing the queue they came from

        :returns: A list of Payload objects

        """
        q = self._new_queue(queue)
        return [self._message_to_python(m, queue, q) for m in messages]

    def _get_bulk(self, queue, max_if_unlimited=SQS_MAX_MESSAGES):
        """Try to retrieve multiple messages off ``queue``.

        Where _get() returns a single Payload object, this method returns a
        list of Payload objects. The number of objects returned is determined
        by the total number of messages available in the queue and the
        number of messages that the QoS object allows (based on the
        prefetch_count).

        .. note::
            Ignores QoS limits so caller is responsible for checking
            that we are allowed to consume at least one message from the
            queue.  get_bulk will then ask QoS for an estimate of
            the number of extra messages that we can consume.

        args:
            queue: The queue name (string) to pull from

        returns:
            payloads: A list of payload objects returned
        """
        # drain_events calls `can_consume` first, consuming
        # a token, so we know that we are allowed to consume at least
        # one message.
        maxcount = self.qos.can_consume_max_estimate()
        maxcount = max_if_unlimited if maxcount is None else max(maxcount, 1)
        if maxcount:
            messages = self._get_from_sqs(
                queue, count=min(maxcount, SQS_MAX_MESSAGES),
            )

            if messages:
                return self._messages_to_python(messages, queue)
        raise Empty()

    def _get(self, queue):
        """Try to retrieve a single message off ``queue``."""
        messages = self._get_from_sqs(queue, count=1)

        if messages:
            return self._messages_to_python(messages, queue)[0]
        raise Empty()

    def _restore(self, message,
                 unwanted_delivery_info=('sqs_message', 'sqs_queue')):
        for unwanted_key in unwanted_delivery_info:
            # Remove objects that aren't JSON serializable (Issue #1108).
            message.delivery_info.pop(unwanted_key, None)
        return super(Channel, self)._restore(message)

    def basic_ack(self, delivery_tag):
        delivery_info = self.qos.get(delivery_tag).delivery_info
        try:
            queue = delivery_info['sqs_queue']
        except KeyError:
            pass
        else:
            queue.delete_message(delivery_info['sqs_message'])
        super(Channel, self).basic_ack(delivery_tag)

    def _size(self, queue):
        """Return the number of messages in a queue."""
        return self._new_queue(queue).count()

    def _purge(self, queue):
        """Delete all current messages in a queue."""
        q = self._new_queue(queue)
        # SQS is slow at registering messages, so run for a few
        # iterations to ensure messages are deleted.
        size = 0
        for i in range(10):
            size += q.count()
            if not size:
                break
        q.clear()
        return size

    def close(self):
        super(Channel, self).close()
        for conn in (self._sqs, self._sdb):
            if conn:
                try:
                    conn.close()
                except AttributeError as exc:  # FIXME ???
                    if "can't set attribute" not in str(exc):
                        raise

    def _get_regioninfo(self, regions):
        if self.region:
            for _r in regions:
                if _r.name == self.region:
                    return _r

    def _aws_connect_to(self, fun, regions):
        conninfo = self.conninfo
        region = self._get_regioninfo(regions)
        return fun(region=region,
                   aws_access_key_id=conninfo.userid,
                   aws_secret_access_key=conninfo.password,
                   port=conninfo.port)

    @property
    def sqs(self):
        if self._sqs is None:
            self._sqs = self._aws_connect_to(SQSConnection, _sqs.regions())
        return self._sqs

    @property
    def sdb(self):
        if self._sdb is None:
            self._sdb = self._aws_connect_to(SDBConnection, _sdb.regions())
        return self._sdb

    @property
    def table(self):
        name = self.entity_name(
            self.domain_format % {'vhost': self.conninfo.virtual_host})
        d = self.sdb.get_object(
            'CreateDomain', {'DomainName': name}, self.Table)
        d.name = name
        return d

    @property
    def conninfo(self):
        return self.connection.client

    @property
    def transport_options(self):
        return self.connection.client.transport_options

    @cached_property
    def visibility_timeout(self):
        return (self.transport_options.get('visibility_timeout') or
                self.default_visibility_timeout)

    @cached_property
    def queue_name_prefix(self):
        return self.transport_options.get('queue_name_prefix', '')

    @cached_property
    def supports_fanout(self):
        return self.transport_options.get('sdb_persistence', False)

    @cached_property
    def region(self):
        return self.transport_options.get('region') or self.default_region

    @cached_property
    def wait_time_seconds(self):
        return self.transport_options.get('wait_time_seconds',
                                          self.default_wait_time_seconds)


class Transport(virtual.Transport):
    Channel = Channel

    polling_interval = 1
    wait_time_seconds = 0
    default_port = None
    connection_errors = (
        virtual.Transport.connection_errors +
        (exception.SQSError, socket.error)
    )
    channel_errors = (
        virtual.Transport.channel_errors + (exception.SQSDecodeError, )
    )
    driver_type = 'sqs'
    driver_name = 'sqs'

########NEW FILE########
__FILENAME__ = exchange
"""
kombu.transport.virtual.exchange
================================

Implementations of the standard exchanges defined
by the AMQ protocol  (excluding the `headers` exchange).

"""
from __future__ import absolute_import

from kombu.utils import escape_regex

import re


class ExchangeType(object):
    """Implements the specifics for an exchange type.

    :param channel: AMQ Channel

    """
    type = None

    def __init__(self, channel):
        self.channel = channel

    def lookup(self, table, exchange, routing_key, default):
        """Lookup all queues matching `routing_key` in `exchange`.

        :returns: `default` if no queues matched.

        """
        raise NotImplementedError('subclass responsibility')

    def prepare_bind(self, queue, exchange, routing_key, arguments):
        """Return tuple of `(routing_key, regex, queue)` to be stored
        for bindings to this exchange."""
        return routing_key, None, queue

    def equivalent(self, prev, exchange, type,
                   durable, auto_delete, arguments):
        """Return true if `prev` and `exchange` is equivalent."""
        return (type == prev['type'] and
                durable == prev['durable'] and
                auto_delete == prev['auto_delete'] and
                (arguments or {}) == (prev['arguments'] or {}))


class DirectExchange(ExchangeType):
    """The `direct` exchange routes based on exact routing keys."""
    type = 'direct'

    def lookup(self, table, exchange, routing_key, default):
        return [queue for rkey, _, queue in table
                if rkey == routing_key]

    def deliver(self, message, exchange, routing_key, **kwargs):
        _lookup = self.channel._lookup
        _put = self.channel._put
        for queue in _lookup(exchange, routing_key):
            _put(queue, message, **kwargs)


class TopicExchange(ExchangeType):
    """The `topic` exchange routes messages based on words separated by
    dots, using wildcard characters ``*`` (any single word), and ``#``
    (one or more words)."""
    type = 'topic'

    #: map of wildcard to regex conversions
    wildcards = {'*': r'.*?[^\.]',
                 '#': r'.*?'}

    #: compiled regex cache
    _compiled = {}

    def lookup(self, table, exchange, routing_key, default):
        return [queue for rkey, pattern, queue in table
                if self._match(pattern, routing_key)]

    def deliver(self, message, exchange, routing_key, **kwargs):
        _lookup = self.channel._lookup
        _put = self.channel._put
        deadletter = self.channel.deadletter_queue
        for queue in [q for q in _lookup(exchange, routing_key)
                      if q and q != deadletter]:
            _put(queue, message, **kwargs)

    def prepare_bind(self, queue, exchange, routing_key, arguments):
        return routing_key, self.key_to_pattern(routing_key), queue

    def key_to_pattern(self, rkey):
        """Get the corresponding regex for any routing key."""
        return '^%s$' % ('\.'.join(
            self.wildcards.get(word, word)
            for word in escape_regex(rkey, '.#*').split('.')
        ))

    def _match(self, pattern, string):
        """Same as :func:`re.match`, except the regex is compiled and cached,
        then reused on subsequent matches with the same pattern."""
        try:
            compiled = self._compiled[pattern]
        except KeyError:
            compiled = self._compiled[pattern] = re.compile(pattern, re.U)
        return compiled.match(string)


class FanoutExchange(ExchangeType):
    """The `fanout` exchange implements broadcast messaging by delivering
    copies of all messages to all queues bound to the exchange.

    To support fanout the virtual channel needs to store the table
    as shared state.  This requires that the `Channel.supports_fanout`
    attribute is set to true, and the `Channel._queue_bind` and
    `Channel.get_table` methods are implemented.  See the redis backend
    for an example implementation of these methods.

    """
    type = 'fanout'

    def lookup(self, table, exchange, routing_key, default):
        return [queue for _, _, queue in table]

    def deliver(self, message, exchange, routing_key, **kwargs):
        if self.channel.supports_fanout:
            self.channel._put_fanout(
                exchange, message, routing_key, **kwargs)


#: Map of standard exchange types and corresponding classes.
STANDARD_EXCHANGE_TYPES = {'direct': DirectExchange,
                           'topic': TopicExchange,
                           'fanout': FanoutExchange}

########NEW FILE########
__FILENAME__ = scheduling
"""
    kombu.transport.virtual.scheduling
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Consumer utilities.

"""
from __future__ import absolute_import

from itertools import count


class FairCycle(object):
    """Consume from a set of resources, where each resource gets
    an equal chance to be consumed from."""

    def __init__(self, fun, resources, predicate=Exception):
        self.fun = fun
        self.resources = resources
        self.predicate = predicate
        self.pos = 0

    def _next(self):
        while 1:
            try:
                resource = self.resources[self.pos]
                self.pos += 1
                return resource
            except IndexError:
                self.pos = 0
                if not self.resources:
                    raise self.predicate()

    def get(self, **kwargs):
        for tried in count(0):  # for infinity
            resource = self._next()

            try:
                return self.fun(resource, **kwargs), resource
            except self.predicate:
                if tried >= len(self.resources) - 1:
                    raise

    def close(self):
        pass

    def __repr__(self):
        return '<FairCycle: {self.pos}/{size} {self.resources}>'.format(
            self=self, size=len(self.resources))

########NEW FILE########
__FILENAME__ = zmq
"""
kombu.transport.zmq
===================

ZeroMQ transport.

"""
from __future__ import absolute_import

import errno
import os
import socket

try:
    import zmq
    from zmq import ZMQError
except ImportError:
    zmq = ZMQError = None  # noqa

from kombu.five import Empty
from kombu.log import get_logger
from kombu.serialization import pickle
from kombu.utils import cached_property
from kombu.utils.eventio import poll, READ

from . import virtual

logger = get_logger('kombu.transport.zmq')

DEFAULT_PORT = 5555
DEFAULT_HWM = 128
DEFAULT_INCR = 1

dumps, loads = pickle.dumps, pickle.loads


class MultiChannelPoller(object):
    eventflags = READ

    def __init__(self):
        # active channels
        self._channels = set()
        # file descriptor -> channel map
        self._fd_to_chan = {}
        # poll implementation (epoll/kqueue/select)
        self.poller = poll()

    def close(self):
        for fd in self._fd_to_chan:
            try:
                self.poller.unregister(fd)
            except KeyError:
                pass
        self._channels.clear()
        self._fd_to_chan.clear()
        self.poller = None

    def add(self, channel):
        self._channels.add(channel)

    def discard(self, channel):
        self._channels.discard(channel)
        self._fd_to_chan.pop(channel.client.connection.fd, None)

    def _register(self, channel):
        conn = channel.client.connection
        self._fd_to_chan[conn.fd] = channel
        self.poller.register(conn.fd, self.eventflags)

    def on_poll_start(self):
        for channel in self._channels:
            self._register(channel)

    def on_readable(self, fileno):
        chan = self._fd_to_chan[fileno]
        return chan.drain_events(), chan

    def get(self, timeout=None):
        self.on_poll_start()

        events = self.poller.poll(timeout)
        for fileno, _ in events or []:
            return self.on_readable(fileno)

        raise Empty()

    @property
    def fds(self):
        return self._fd_to_chan


class Client(object):

    def __init__(self, uri='tcp://127.0.0.1', port=DEFAULT_PORT,
                 hwm=DEFAULT_HWM, swap_size=None, enable_sink=True,
                 context=None):
        try:
            scheme, parts = uri.split('://')
        except ValueError:
            scheme = 'tcp'
            parts = uri
        endpoints = parts.split(';')
        self.port = port

        if scheme != 'tcp':
            raise NotImplementedError('Currently only TCP can be used')

        self.context = context or zmq.Context.instance()

        if enable_sink:
            self.sink = self.context.socket(zmq.PULL)
            self.sink.bind('tcp://*:{0.port}'.format(self))
        else:
            self.sink = None

        self.vent = self.context.socket(zmq.PUSH)

        if hasattr(zmq, 'SNDHWM'):
            self.vent.setsockopt(zmq.SNDHWM, hwm)
        else:
            self.vent.setsockopt(zmq.HWM, hwm)

        if swap_size:
            self.vent.setsockopt(zmq.SWAP, swap_size)

        for endpoint in endpoints:
            if scheme == 'tcp' and ':' not in endpoint:
                endpoint += ':' + str(DEFAULT_PORT)

            endpoint = ''.join([scheme, '://', endpoint])

            self.connect(endpoint)

    def connect(self, endpoint):
        self.vent.connect(endpoint)

    def get(self, queue=None, timeout=None):
        sink = self.sink
        try:
            if timeout is not None:
                prev_timeout, sink.RCVTIMEO = sink.RCVTIMEO, timeout
                try:
                    return sink.recv()
                finally:
                    sink.RCVTIMEO = prev_timeout
            else:
                return sink.recv()
        except ZMQError as exc:
            if exc.errno == zmq.EAGAIN:
                raise socket.error(errno.EAGAIN, exc.strerror)
            else:
                raise

    def put(self, queue, message, **kwargs):
        return self.vent.send(message)

    def close(self):
        if self.sink and not self.sink.closed:
            self.sink.close()
        if not self.vent.closed:
            self.vent.close()

    @property
    def connection(self):
        if self.sink:
            return self.sink
        return self.vent


class Channel(virtual.Channel):
    Client = Client

    hwm = DEFAULT_HWM
    swap_size = None
    enable_sink = True
    port_incr = DEFAULT_INCR

    from_transport_options = (
        virtual.Channel.from_transport_options +
        ('hwm', 'swap_size', 'enable_sink', 'port_incr')
    )

    def __init__(self, *args, **kwargs):
        super_ = super(Channel, self)
        super_.__init__(*args, **kwargs)

        # Evaluate socket
        self.client.connection.closed

        self.connection.cycle.add(self)
        self.connection_errors = self.connection.connection_errors

    def _get(self, queue, timeout=None):
        try:
            return loads(self.client.get(queue, timeout))
        except socket.error as exc:
            if exc.errno == errno.EAGAIN and timeout != 0:
                raise Empty()
            else:
                raise

    def _put(self, queue, message, **kwargs):
        self.client.put(queue, dumps(message, -1), **kwargs)

    def _purge(self, queue):
        return 0

    def _poll(self, cycle, timeout=None):
        return cycle.get(timeout=timeout)

    def close(self):
        if not self.closed:
            self.connection.cycle.discard(self)
            try:
                self.__dict__['client'].close()
            except KeyError:
                pass
        super(Channel, self).close()

    def _prepare_port(self, port):
        return (port + self.channel_id - 1) * self.port_incr

    def _create_client(self):
        conninfo = self.connection.client
        port = self._prepare_port(conninfo.port or DEFAULT_PORT)
        return self.Client(uri=conninfo.hostname or 'tcp://127.0.0.1',
                           port=port,
                           hwm=self.hwm,
                           swap_size=self.swap_size,
                           enable_sink=self.enable_sink,
                           context=self.connection.context)

    @cached_property
    def client(self):
        return self._create_client()


class Transport(virtual.Transport):
    Channel = Channel

    can_parse_url = True
    default_port = DEFAULT_PORT
    driver_type = 'zeromq'
    driver_name = 'zmq'

    connection_errors = virtual.Transport.connection_errors + (ZMQError, )

    supports_ev = True
    polling_interval = None

    def __init__(self, *args, **kwargs):
        if zmq is None:
            raise ImportError('The zmq library is not installed')
        super(Transport, self).__init__(*args, **kwargs)
        self.cycle = MultiChannelPoller()

    def driver_version(self):
        return zmq.__version__

    def register_with_event_loop(self, connection, loop):
        cycle = self.cycle
        cycle.poller = loop.poller
        add_reader = loop.add_reader
        on_readable = self.on_readable

        cycle_poll_start = cycle.on_poll_start

        def on_poll_start():
            cycle_poll_start()
            [add_reader(fd, on_readable, fd) for fd in cycle.fds]

        loop.on_tick.add(on_poll_start)

    def on_readable(self, fileno):
        self._handle_event(self.cycle.on_readable(fileno))

    def drain_events(self, connection, timeout=None):
        more_to_read = False
        for channel in connection.channels:
            try:
                evt = channel.cycle.get(timeout=timeout)
            except socket.error as exc:
                if exc.errno == errno.EAGAIN:
                    continue
                raise
            else:
                connection._handle_event((evt, channel))
                more_to_read = True
        if not more_to_read:
            raise socket.error(errno.EAGAIN, os.strerror(errno.EAGAIN))

    def _handle_event(self, evt):
        item, channel = evt
        message, queue = item
        if not queue or queue not in self._callbacks:
            raise KeyError(
                'Message for queue {0!r} without consumers: {1}'.format(
                    queue, message))
        self._callbacks[queue](message)

    def establish_connection(self):
        self.context.closed
        return super(Transport, self).establish_connection()

    def close_connection(self, connection):
        super(Transport, self).close_connection(connection)
        try:
            connection.__dict__['context'].term()
        except KeyError:
            pass

    @cached_property
    def context(self):
        return zmq.Context(1)

########NEW FILE########
__FILENAME__ = zookeeper
"""
kombu.transport.zookeeper
=========================

Zookeeper transport.

:copyright: (c) 2010 - 2013 by Mahendra M.
:license: BSD, see LICENSE for more details.

**Synopsis**

Connects to a zookeeper node as <server>:<port>/<vhost>
The <vhost> becomes the base for all the other znodes. So we can use
it like a vhost.

This uses the built-in kazoo recipe for queues

**References**

- https://zookeeper.apache.org/doc/trunk/recipes.html#sc_recipes_Queues
- https://kazoo.readthedocs.org/en/latest/api/recipe/queue.html

**Limitations**
This queue does not offer reliable consumption. An entry is removed from
the queue prior to being processed. So if an error occurs, the consumer
has to re-queue the item or it will be lost.
"""
from __future__ import absolute_import

import os
import socket

from kombu.five import Empty
from kombu.utils.encoding import bytes_to_str
from kombu.utils.json import loads, dumps

from . import virtual

try:
    import kazoo
    from kazoo.client import KazooClient
    from kazoo.recipe.queue import Queue

    KZ_CONNECTION_ERRORS = (
        kazoo.exceptions.SystemErrorException,
        kazoo.exceptions.ConnectionLossException,
        kazoo.exceptions.MarshallingErrorException,
        kazoo.exceptions.UnimplementedException,
        kazoo.exceptions.OperationTimeoutException,
        kazoo.exceptions.NoAuthException,
        kazoo.exceptions.InvalidACLException,
        kazoo.exceptions.AuthFailedException,
        kazoo.exceptions.SessionExpiredException,
    )

    KZ_CHANNEL_ERRORS = (
        kazoo.exceptions.RuntimeInconsistencyException,
        kazoo.exceptions.DataInconsistencyException,
        kazoo.exceptions.BadArgumentsException,
        kazoo.exceptions.MarshallingErrorException,
        kazoo.exceptions.UnimplementedException,
        kazoo.exceptions.OperationTimeoutException,
        kazoo.exceptions.ApiErrorException,
        kazoo.exceptions.NoNodeException,
        kazoo.exceptions.NoAuthException,
        kazoo.exceptions.NodeExistsException,
        kazoo.exceptions.NoChildrenForEphemeralsException,
        kazoo.exceptions.NotEmptyException,
        kazoo.exceptions.SessionExpiredException,
        kazoo.exceptions.InvalidCallbackException,
        socket.error,
    )
except ImportError:
    kazoo = None                                    # noqa
    KZ_CONNECTION_ERRORS = KZ_CHANNEL_ERRORS = ()   # noqa

DEFAULT_PORT = 2181

__author__ = 'Mahendra M <mahendra.m@gmail.com>'


class Channel(virtual.Channel):

    _client = None
    _queues = {}

    def _get_path(self, queue_name):
        return os.path.join(self.vhost, queue_name)

    def _get_queue(self, queue_name):
        queue = self._queues.get(queue_name, None)

        if queue is None:
            queue = Queue(self.client, self._get_path(queue_name))
            self._queues[queue_name] = queue

            # Ensure that the queue is created
            len(queue)

        return queue

    def _put(self, queue, message, **kwargs):
        return self._get_queue(queue).put(
            dumps(message),
            priority=self._get_message_priority(message, reverse=True),
        )

    def _get(self, queue):
        queue = self._get_queue(queue)
        msg = queue.get()

        if msg is None:
            raise Empty()

        return loads(bytes_to_str(msg))

    def _purge(self, queue):
        count = 0
        queue = self._get_queue(queue)

        while True:
            msg = queue.get()
            if msg is None:
                break
            count += 1

        return count

    def _delete(self, queue, *args, **kwargs):
        if self._has_queue(queue):
            self._purge(queue)
            self.client.delete(self._get_path(queue))

    def _size(self, queue):
        queue = self._get_queue(queue)
        return len(queue)

    def _new_queue(self, queue, **kwargs):
        if not self._has_queue(queue):
            queue = self._get_queue(queue)

    def _has_queue(self, queue):
        return self.client.exists(self._get_path(queue)) is not None

    def _open(self):
        conninfo = self.connection.client
        port = conninfo.port or DEFAULT_PORT
        conn_str = '%s:%s' % (conninfo.hostname, port)
        self.vhost = os.path.join('/', conninfo.virtual_host[0:-1])

        conn = KazooClient(conn_str)
        conn.start()
        return conn

    @property
    def client(self):
        if self._client is None:
            self._client = self._open()
        return self._client


class Transport(virtual.Transport):
    Channel = Channel
    polling_interval = 1
    default_port = DEFAULT_PORT
    connection_errors = (
        virtual.Transport.connection_errors + KZ_CONNECTION_ERRORS
    )
    channel_errors = (
        virtual.Transport.channel_errors + KZ_CHANNEL_ERRORS
    )
    driver_type = 'zookeeper'
    driver_name = 'kazoo'

    def __init__(self, *args, **kwargs):
        if kazoo is None:
            raise ImportError('The kazoo library is not installed')

        super(Transport, self).__init__(*args, **kwargs)

    def driver_version(self):
        return kazoo.__version__

########NEW FILE########
__FILENAME__ = amq_manager
from __future__ import absolute_import


def get_manager(client, hostname=None, port=None, userid=None,
                password=None):
    import pyrabbit
    opt = client.transport_options.get

    def get(name, val, default):
        return (val if val is not None
                else opt('manager_%s' % name)
                or getattr(client, name, None) or default)

    host = get('hostname', hostname, 'localhost')
    port = port if port is not None else opt('manager_port', 15672)
    userid = get('userid', userid, 'guest')
    password = get('password', password, 'guest')
    return pyrabbit.Client('%s:%s' % (host, port), userid, password)

########NEW FILE########
__FILENAME__ = debug
"""
kombu.utils.debug
=================

Debugging support.

"""
from __future__ import absolute_import

import logging

from functools import wraps

from kombu.five import items
from kombu.log import get_logger

__all__ = ['setup_logging', 'Logwrapped']


def setup_logging(loglevel=logging.DEBUG, loggers=['kombu.connection',
                                                   'kombu.channel']):
    for logger in loggers:
        l = get_logger(logger)
        l.addHandler(logging.StreamHandler())
        l.setLevel(loglevel)


class Logwrapped(object):
    __ignore = ('__enter__', '__exit__')

    def __init__(self, instance, logger=None, ident=None):
        self.instance = instance
        self.logger = get_logger(logger)
        self.ident = ident

    def __getattr__(self, key):
        meth = getattr(self.instance, key)

        if not callable(meth) or key in self.__ignore:
            return meth

        @wraps(meth)
        def __wrapped(*args, **kwargs):
            info = ''
            if self.ident:
                info += self.ident.format(self.instance)
            info += '{0.__name__}('.format(meth)
            if args:
                info += ', '.join(map(repr, args))
            if kwargs:
                if args:
                    info += ', '
                info += ', '.join('{k}={v!r}'.format(k=key, v=value)
                                  for key, value in items(kwargs))
            info += ')'
            self.logger.debug(info)
            return meth(*args, **kwargs)

        return __wrapped

    def __repr__(self):
        return repr(self.instance)

    def __dir__(self):
        return dir(self.instance)

########NEW FILE########
__FILENAME__ = encoding
# -*- coding: utf-8 -*-
"""
kombu.utils.encoding
~~~~~~~~~~~~~~~~~~~~~

Utilities to encode text, and to safely emit text from running
applications without crashing with the infamous :exc:`UnicodeDecodeError`
exception.

"""
from __future__ import absolute_import

import sys
import traceback

from kombu.five import text_t

is_py3k = sys.version_info >= (3, 0)

#: safe_str takes encoding from this file by default.
#: :func:`set_default_encoding_file` can used to set the
#: default output file.
default_encoding_file = None


def set_default_encoding_file(file):
    global default_encoding_file
    default_encoding_file = file


def get_default_encoding_file():
    return default_encoding_file


if sys.platform.startswith('java'):     # pragma: no cover

    def default_encoding(file=None):
        return 'utf-8'
else:

    def default_encoding(file=None):  # noqa
        file = file or get_default_encoding_file()
        return getattr(file, 'encoding', None) or sys.getfilesystemencoding()

if is_py3k:  # pragma: no cover

    def str_to_bytes(s):
        if isinstance(s, str):
            return s.encode()
        return s

    def bytes_to_str(s):
        if isinstance(s, bytes):
            return s.decode()
        return s

    def from_utf8(s, *args, **kwargs):
        return s

    def ensure_bytes(s):
        if not isinstance(s, bytes):
            return str_to_bytes(s)
        return s

    def default_encode(obj):
        return obj

    str_t = str

else:

    def str_to_bytes(s):                # noqa
        if isinstance(s, unicode):
            return s.encode()
        return s

    def bytes_to_str(s):                # noqa
        return s

    def from_utf8(s, *args, **kwargs):  # noqa
        return s.encode('utf-8', *args, **kwargs)

    def default_encode(obj, file=None):            # noqa
        return unicode(obj, default_encoding(file))

    str_t = unicode
    ensure_bytes = str_to_bytes


try:
    bytes_t = bytes
except NameError:  # pragma: no cover
    bytes_t = str  # noqa


def safe_str(s, errors='replace'):
    s = bytes_to_str(s)
    if not isinstance(s, (text_t, bytes)):
        return safe_repr(s, errors)
    return _safe_str(s, errors)


if is_py3k:

    def _safe_str(s, errors='replace', file=None):
        if isinstance(s, str):
            return s
        try:
            return str(s)
        except Exception as exc:
            return '<Unrepresentable {0!r}: {1!r} {2!r}>'.format(
                type(s), exc, '\n'.join(traceback.format_stack()))
else:
    def _safe_str(s, errors='replace', file=None):  # noqa
        encoding = default_encoding(file)
        try:
            if isinstance(s, unicode):
                return s.encode(encoding, errors)
            return unicode(s, encoding, errors)
        except Exception as exc:
            return '<Unrepresentable {0!r}: {1!r} {2!r}>'.format(
                type(s), exc, '\n'.join(traceback.format_stack()))


def safe_repr(o, errors='replace'):
    try:
        return repr(o)
    except Exception:
        return _safe_str(o, errors)

########NEW FILE########
__FILENAME__ = eventio
"""
kombu.utils.eventio
===================

Evented IO support for multiple platforms.

"""
from __future__ import absolute_import

import errno
import select as __select__
import socket

from numbers import Integral

_selectf = __select__.select
_selecterr = __select__.error
epoll = getattr(__select__, 'epoll', None)
kqueue = getattr(__select__, 'kqueue', None)
kevent = getattr(__select__, 'kevent', None)
KQ_EV_ADD = getattr(__select__, 'KQ_EV_ADD', 1)
KQ_EV_DELETE = getattr(__select__, 'KQ_EV_DELETE', 2)
KQ_EV_ENABLE = getattr(__select__, 'KQ_EV_ENABLE', 4)
KQ_EV_CLEAR = getattr(__select__, 'KQ_EV_CLEAR', 32)
KQ_EV_ERROR = getattr(__select__, 'KQ_EV_ERROR', 16384)
KQ_EV_EOF = getattr(__select__, 'KQ_EV_EOF', 32768)
KQ_FILTER_READ = getattr(__select__, 'KQ_FILTER_READ', -1)
KQ_FILTER_WRITE = getattr(__select__, 'KQ_FILTER_WRITE', -2)
KQ_FILTER_AIO = getattr(__select__, 'KQ_FILTER_AIO', -3)
KQ_FILTER_VNODE = getattr(__select__, 'KQ_FILTER_VNODE', -4)
KQ_FILTER_PROC = getattr(__select__, 'KQ_FILTER_PROC', -5)
KQ_FILTER_SIGNAL = getattr(__select__, 'KQ_FILTER_SIGNAL', -6)
KQ_FILTER_TIMER = getattr(__select__, 'KQ_FILTER_TIMER', -7)
KQ_NOTE_LOWAT = getattr(__select__, 'KQ_NOTE_LOWAT', 1)
KQ_NOTE_DELETE = getattr(__select__, 'KQ_NOTE_DELETE', 1)
KQ_NOTE_WRITE = getattr(__select__, 'KQ_NOTE_WRITE', 2)
KQ_NOTE_EXTEND = getattr(__select__, 'KQ_NOTE_EXTEND', 4)
KQ_NOTE_ATTRIB = getattr(__select__, 'KQ_NOTE_ATTRIB', 8)
KQ_NOTE_LINK = getattr(__select__, 'KQ_NOTE_LINK', 16)
KQ_NOTE_RENAME = getattr(__select__, 'KQ_NOTE_RENAME', 32)
KQ_NOTE_REVOKE = getattr(__select__, 'kQ_NOTE_REVOKE', 64)


from kombu.syn import detect_environment

from . import fileno

__all__ = ['poll']

READ = POLL_READ = 0x001
WRITE = POLL_WRITE = 0x004
ERR = POLL_ERR = 0x008 | 0x010

try:
    SELECT_BAD_FD = {errno.EBADF, errno.WSAENOTSOCK}
except AttributeError:
    SELECT_BAD_FD = {errno.EBADF}


class Poller(object):

    def poll(self, timeout):
        try:
            return self._poll(timeout)
        except Exception as exc:
            if exc.errno != errno.EINTR:
                raise


class _epoll(Poller):

    def __init__(self):
        self._epoll = epoll()

    def register(self, fd, events):
        try:
            self._epoll.register(fd, events)
        except Exception as exc:
            if exc.errno != errno.EEXIST:
                raise

    def unregister(self, fd):
        try:
            self._epoll.unregister(fd)
        except (socket.error, ValueError, KeyError, TypeError):
            pass
        except (IOError, OSError) as exc:
            if exc.errno != errno.ENOENT:
                raise

    def _poll(self, timeout):
        return self._epoll.poll(timeout if timeout is not None else -1)

    def close(self):
        self._epoll.close()


class _kqueue(Poller):
    w_fflags = (KQ_NOTE_WRITE | KQ_NOTE_EXTEND |
                KQ_NOTE_ATTRIB | KQ_NOTE_DELETE)

    def __init__(self):
        self._kqueue = kqueue()
        self._active = {}
        self.on_file_change = None
        self._kcontrol = self._kqueue.control

    def register(self, fd, events):
        self._control(fd, events, KQ_EV_ADD)
        self._active[fd] = events

    def unregister(self, fd):
        events = self._active.pop(fd, None)
        if events:
            try:
                self._control(fd, events, KQ_EV_DELETE)
            except socket.error:
                pass

    def watch_file(self, fd):
        ev = kevent(fd,
                    filter=KQ_FILTER_VNODE,
                    flags=KQ_EV_ADD | KQ_EV_ENABLE | KQ_EV_CLEAR,
                    fflags=self.w_fflags)
        self._kcontrol([ev], 0)

    def unwatch_file(self, fd):
        ev = kevent(fd,
                    filter=KQ_FILTER_VNODE,
                    flags=KQ_EV_DELETE,
                    fflags=self.w_fflags)
        self._kcontrol([ev], 0)

    def _control(self, fd, events, flags):
        if not events:
            return
        kevents = []
        if events & WRITE:
            kevents.append(kevent(fd,
                           filter=KQ_FILTER_WRITE,
                           flags=flags))
        if not kevents or events & READ:
            kevents.append(
                kevent(fd, filter=KQ_FILTER_READ, flags=flags),
            )
        control = self._kcontrol
        for e in kevents:
            try:
                control([e], 0)
            except ValueError:
                pass

    def _poll(self, timeout):
        kevents = self._kcontrol(None, 1000, timeout)
        events, file_changes = {}, []
        for k in kevents:
            fd = k.ident
            if k.filter == KQ_FILTER_READ:
                events[fd] = events.get(fd, 0) | READ
            elif k.filter == KQ_FILTER_WRITE:
                if k.flags & KQ_EV_EOF:
                    events[fd] = ERR
                else:
                    events[fd] = events.get(fd, 0) | WRITE
            elif k.filter == KQ_EV_ERROR:
                events[fd] = events.get(fd, 0) | ERR
            elif k.filter == KQ_FILTER_VNODE:
                if k.fflags & KQ_NOTE_DELETE:
                    self.unregister(fd)
                file_changes.append(k)
        if file_changes:
            self.on_file_change(file_changes)
        return list(events.items())

    def close(self):
        self._kqueue.close()


class _select(Poller):

    def __init__(self):
        self._all = (self._rfd,
                     self._wfd,
                     self._efd) = set(), set(), set()

    def register(self, fd, events):
        fd = fileno(fd)
        if events & ERR:
            self._efd.add(fd)
        if events & WRITE:
            self._wfd.add(fd)
        if events & READ:
            self._rfd.add(fd)

    def _remove_bad(self):
        for fd in self._rfd | self._wfd | self._efd:
            try:
                _selectf([fd], [], [], 0)
            except (_selecterr, socket.error) as exc:
                if exc.errno in SELECT_BAD_FD:
                    self.unregister(fd)

    def unregister(self, fd):
        try:
            fd = fileno(fd)
        except socket.error as exc:
            # we don't know the previous fd of this object
            # but it will be removed by the next poll iteration.
            if exc.errno in SELECT_BAD_FD:
                return
            raise
        self._rfd.discard(fd)
        self._wfd.discard(fd)
        self._efd.discard(fd)

    def _poll(self, timeout):
        try:
            read, write, error = _selectf(
                self._rfd, self._wfd, self._efd, timeout,
            )
        except (_selecterr, socket.error) as exc:
            if exc.errno == errno.EINTR:
                return
            elif exc.errno in SELECT_BAD_FD:
                return self._remove_bad()
            raise

        events = {}
        for fd in read:
            if not isinstance(fd, Integral):
                fd = fd.fileno()
            events[fd] = events.get(fd, 0) | READ
        for fd in write:
            if not isinstance(fd, Integral):
                fd = fd.fileno()
            events[fd] = events.get(fd, 0) | WRITE
        for fd in error:
            if not isinstance(fd, Integral):
                fd = fd.fileno()
            events[fd] = events.get(fd, 0) | ERR
        return list(events.items())

    def close(self):
        self._rfd.clear()
        self._wfd.clear()
        self._efd.clear()


def _get_poller():
    if detect_environment() != 'default':
        # greenlet
        return _select
    elif epoll:
        # Py2.6+ Linux
        return _epoll
    elif kqueue:
        # Py2.6+ on BSD / Darwin
        return _select  # was: _kqueue
    else:
        return _select


def poll(*args, **kwargs):
    return _get_poller()(*args, **kwargs)

########NEW FILE########
__FILENAME__ = functional
from __future__ import absolute_import

import sys

from collections import Iterable, Mapping

from kombu.five import string_t

__all__ = ['lazy', 'maybe_evaluate', 'is_list', 'maybe_list']


class lazy(object):
    """Holds lazy evaluation.

    Evaluated when called or if the :meth:`evaluate` method is called.
    The function is re-evaluated on every call.

    Overloaded operations that will evaluate the promise:
        :meth:`__str__`, :meth:`__repr__`, :meth:`__cmp__`.

    """

    def __init__(self, fun, *args, **kwargs):
        self._fun = fun
        self._args = args
        self._kwargs = kwargs

    def __call__(self):
        return self.evaluate()

    def evaluate(self):
        return self._fun(*self._args, **self._kwargs)

    def __str__(self):
        return str(self())

    def __repr__(self):
        return repr(self())

    def __eq__(self, rhs):
        return self() == rhs

    def __ne__(self, rhs):
        return self() != rhs

    def __deepcopy__(self, memo):
        memo[id(self)] = self
        return self

    def __reduce__(self):
        return (self.__class__, (self._fun, ), {'_args': self._args,
                                                '_kwargs': self._kwargs})

    if sys.version_info[0] < 3:

        def __cmp__(self, rhs):
            if isinstance(rhs, self.__class__):
                return -cmp(rhs, self())
            return cmp(self(), rhs)


def maybe_evaluate(value):
    """Evaluates if the value is a :class:`lazy` instance."""
    if isinstance(value, lazy):
        return value.evaluate()
    return value


def is_list(l, scalars=(Mapping, string_t), iters=(Iterable, )):
    """Return true if the object is iterable (but not
    if object is a mapping or string)."""
    return isinstance(l, iters) and not isinstance(l, scalars or ())


def maybe_list(l, scalars=(Mapping, string_t)):
    """Return list of one element if ``l`` is a scalar."""
    return l if l is None or is_list(l, scalars) else [l]


# Compat names (before kombu 3.0)
promise = lazy
maybe_promise = maybe_evaluate

########NEW FILE########
__FILENAME__ = json
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import sys

from kombu.five import buffer_t, text_t, bytes_t

try:
    import simplejson as json
except ImportError:  # pragma: no cover
    import json  # noqa

IS_PY3 = sys.version_info[0] == 3


class JSONEncoder(json.JSONEncoder):

    def default(self, obj, _super=json.JSONEncoder.default):
        try:
            _super(self, obj)
        except TypeError:
            try:
                reducer = obj.__json__
            except AttributeError:
                raise
            else:
                return reducer()


def dumps(s, _dumps=json.dumps, cls=JSONEncoder):
    return _dumps(s, cls=cls)


def loads(s, _loads=json.loads, decode_bytes=IS_PY3):
    # None of the json implementations supports decoding from
    # a buffer/memoryview, or even reading from a stream
    #    (load is just loads(fp.read()))
    # but this is Python, we love copying strings, preferably many times
    # over.  Note that pickle does support buffer/memoryview
    # </rant>
    if isinstance(s, memoryview):
        s = s.tobytes().decode('utf-8')
    elif isinstance(s, bytearray):
        s = s.decode('utf-8')
    elif decode_bytes and isinstance(s, bytes_t):
        s = s.decode('utf-8')
    elif isinstance(s, buffer_t):
        s = text_t(s)  # ... awwwwwww :(
    return _loads(s)

########NEW FILE########
__FILENAME__ = limits
"""
kombu.utils.limits
==================

Token bucket implementation for rate limiting.

"""
from __future__ import absolute_import

from kombu.five import monotonic

__all__ = ['TokenBucket']


class TokenBucket(object):
    """Token Bucket Algorithm.

    See http://en.wikipedia.org/wiki/Token_Bucket
    Most of this code was stolen from an entry in the ASPN Python Cookbook:
    http://code.activestate.com/recipes/511490/

    .. admonition:: Thread safety

        This implementation may not be thread safe.

    """

    #: The rate in tokens/second that the bucket will be refilled
    fill_rate = None

    #: Maximum number of tokensin the bucket.
    capacity = 1

    #: Timestamp of the last time a token was taken out of the bucket.
    timestamp = None

    def __init__(self, fill_rate, capacity=1):
        self.capacity = float(capacity)
        self._tokens = capacity
        self.fill_rate = float(fill_rate)
        self.timestamp = monotonic()

    def can_consume(self, tokens=1):
        """Return :const:`True` if the number of tokens can be consumed
        from the bucket."""
        if tokens <= self._get_tokens():
            self._tokens -= tokens
            return True
        return False

    def expected_time(self, tokens=1):
        """Return the time (in seconds) when a new token is expected
        to be available.

        This will also consume a token from the bucket.

        """
        _tokens = self._get_tokens()
        tokens = max(tokens, _tokens)
        return (tokens - _tokens) / self.fill_rate

    def _get_tokens(self):
        if self._tokens < self.capacity:
            now = monotonic()
            delta = self.fill_rate * (now - self.timestamp)
            self._tokens = min(self.capacity, self._tokens + delta)
            self.timestamp = now
        return self._tokens

########NEW FILE########
__FILENAME__ = text
# -*- coding: utf-8 -*-
from __future__ import absolute_import

from difflib import SequenceMatcher

from kombu import version_info_t
from kombu.five import string_t


def fmatch_iter(needle, haystack, min_ratio=0.6):
    for key in haystack:
        ratio = SequenceMatcher(None, needle, key).ratio()
        if ratio >= min_ratio:
            yield ratio, key


def fmatch_best(needle, haystack, min_ratio=0.6):
    try:
        return sorted(
            fmatch_iter(needle, haystack, min_ratio), reverse=True,
        )[0][1]
    except IndexError:
        pass


def version_string_as_tuple(s):
    v = _unpack_version(*s.split('.'))
    # X.Y.3a1 -> (X, Y, 3, 'a1')
    if isinstance(v.micro, string_t):
        v = version_info_t(v.major, v.minor, *_splitmicro(*v[2:]))
    # X.Y.3a1-40 -> (X, Y, 3, 'a1', '40')
    if not v.serial and v.releaselevel and '-' in v.releaselevel:
        v = version_info_t(*list(v[0:3]) + v.releaselevel.split('-'))
    return v


def _unpack_version(major, minor=0, micro=0, releaselevel='', serial=''):
    return version_info_t(int(major), int(minor), micro, releaselevel, serial)


def _splitmicro(micro, releaselevel='', serial=''):
    for index, char in enumerate(micro):
        if not char.isdigit():
            break
    else:
        return int(micro or 0), releaselevel, serial
    return int(micro[:index]), micro[index:], serial

########NEW FILE########
__FILENAME__ = url
from __future__ import absolute_import

from functools import partial

try:
    from urllib.parse import parse_qsl, quote, unquote, urlparse
except ImportError:
    from urllib import quote, unquote                  # noqa
    from urlparse import urlparse, parse_qsl    # noqa

from kombu.five import string_t

safequote = partial(quote, safe='')


def _parse_url(url):
    scheme = urlparse(url).scheme
    schemeless = url[len(scheme) + 3:]
    # parse with HTTP URL semantics
    parts = urlparse('http://' + schemeless)
    path = parts.path or ''
    path = path[1:] if path and path[0] == '/' else path
    return (scheme, unquote(parts.hostname or '') or None, parts.port,
            unquote(parts.username or '') or None,
            unquote(parts.password or '') or None,
            unquote(path or '') or None,
            dict(parse_qsl(parts.query)))


def parse_url(url):
    scheme, host, port, user, password, path, query = _parse_url(url)
    return dict(transport=scheme, hostname=host,
                port=port, userid=user,
                password=password, virtual_host=path, **query)


def as_url(scheme, host=None, port=None, user=None, password=None,
           path=None, query=None, sanitize=False, mask='**'):
        parts = ['{0}://'.format(scheme)]
        if user or password:
            if user:
                parts.append(safequote(user))
            if password:
                if sanitize:
                    parts.extend([':', mask] if mask else [':'])
                else:
                    parts.extend([':', safequote(password)])
            parts.append('@')
        parts.append(safequote(host) if host else '')
        if port:
            parts.extend([':', port])
        parts.extend(['/', path])
        return ''.join(str(part) for part in parts if part)


def sanitize_url(url, mask='**'):
    return as_url(*_parse_url(url), sanitize=True, mask=mask)


def maybe_sanitize_url(url, mask='**'):
    if isinstance(url, string_t) and '://' in url:
        return sanitize_url(url, mask)
    return url

########NEW FILE########
