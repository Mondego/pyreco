__FILENAME__ = evtest
#!/usr/bin/env python
# encoding: utf-8

'''
evdev example - input device event monitor
'''


from sys import argv, exit
from select import select
from evdev import ecodes, InputDevice, list_devices, AbsInfo


usage = 'usage: evtest <device> [<type> <value>]'
evfmt = 'time {:<16} type {} ({}), code {:<4} ({}), value {}'
device_dir = '/dev/input/'
query_type = None
query_value = None


def select_device():
    '''Select a device from the list of accessible input devices.'''

    devices = [InputDevice(i) for i in reversed(list_devices(device_dir))]
    if not devices:
        print('error: no input devices found (do you have rw permission on /dev/input/*?)')
        exit(1)

    dev_fmt = '{0:<3} {1.fn:<20} {1.name:<35} {1.phys}'
    dev_lns = [dev_fmt.format(n, d) for n, d in enumerate(devices)]

    print('ID  {:<20} {:<35} {}'.format('Device', 'Name', 'Phys'))
    print('-' * len(max(dev_lns, key=len)))
    print('\n'.join(dev_lns))
    print('')

    choice = input('Select device [0-{}]:'.format(len(dev_lns)-1))
    return devices[int(choice)]


def print_event(e):
    if e.type == ecodes.EV_SYN:
        if e.code == ecodes.SYN_MT_REPORT:
            print('time {:<16} +++++++++ {} ++++++++'.format(e.timestamp(), ecodes.SYN[e.code]))
        else:
            print('time {:<16} --------- {} --------'.format(e.timestamp(), ecodes.SYN[e.code]))
    else:
        if e.type in ecodes.bytype:
            codename = ecodes.bytype[e.type][e.code]
        else:
            codename = '?'

        print(evfmt.format(e.timestamp(), e.type, ecodes.EV[e.type], e.code, codename, e.value))


if len(argv) == 1:
    device = select_device()

elif len(argv) == 2:
    device = InputDevice(argv[1])

elif len(argv) == 4:
    device = InputDevice(argv[1])
    query_type = argv[2]
    query_value = argv[3]
else:
    print(usage)
    exit(1)

capabs = device.capabilities(verbose=True)

print('Device name: {.name}'.format(device))
print('Device info: {.info}'.format(device))
print('Repeat settings: {}'.format(device.repeat))

if ('EV_LED', ecodes.EV_LED) in capabs:
    print('Active LEDs: {}\n'.format(','.join(i[0] for i in device.leds(True))))

print('Device capabilities:')
for type, codes in capabs.items():
    print('  Type {} {}:'.format(*type))
    for i in codes:
        # i <- ('BTN_RIGHT', 273) or (['BTN_LEFT', 'BTN_MOUSE'], 272)
        if isinstance(i[1], AbsInfo):
            print('    Code {:<4} {}:'.format(*i[0]))
            print('      {}'.format(i[1]))
        else:
            # multiple names may resolve to one value
            s = ', '.join(i[0]) if isinstance(i[0], list) else i[0]
            print('    Code {:<4} {}'.format(s, i[1]))
    print('')


print('Listening for events ...\n')
while True:
    r, w, e = select([device], [], [])

    for ev in device.read():
        print_event(ev)

########NEW FILE########
__FILENAME__ = udev-example
#!/usr/bin/env python3

'''
This is an example of using pyudev[1] alongside evdev.
[1]: https://pyudev.readthedocs.org/
'''

import functools
import pyudev

from select import select
from evdev import InputDevice

context = pyudev.Context()
monitor = pyudev.Monitor.from_netlink(context)
monitor.filter_by(subsystem='input')
monitor.start()

fds = {monitor.fileno(): monitor}
finalizers = []

while True:
    r, w, x = select(fds, [], [])

    if monitor.fileno() in r:
        r.remove(monitor.fileno())

        for udev in iter(functools.partial(monitor.poll, 0), None):
            # we're only interested in devices that have a device node
            # (e.g. /dev/input/eventX)
            if not udev.device_node:
                break

            # find the device we're interested in and add it to fds
            for name in (i['NAME'] for i in udev.ancestors if 'NAME' in i):
                # I used a virtual input device for this test - you
                # should adapt this to your needs
                if u'py-evdev-uinput' in name:
                    if udev.action == u'add':
                        print('Device added: %s' % udev)
                        fds[dev.fd] = InputDevice(udev.device_node)
                        break
                    if udev.action == u'remove':
                        print('Device removed: %s' % udev)

                        def helper():
                            global fds
                            fds = {monitor.fileno(): monitor}

                        finalizers.append(helper)
                        break

    for fd in r:
        dev = fds[fd]
        for event in dev.read():
            print(event)

    for i in range(len(finalizers)):
        finalizers.pop()()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

import sys, os

# Check if readthedocs is building us
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))
from setup import kw

# Trick autodoc into running without having built the extension modules.
if on_rtd:
    with open('../evdev/_ecodes.py', 'w') as fh:
        fh.write('''
KEY = ABS = REL = SW = MSC = LED = REP = SND = SYN = FF = FF_STATUS = BTN_A = KEY_A = 1
EV_KEY = EV_ABS = EV_REL = EV_SW = EV_MSC = EV_LED = EV_REP = 1
EV_SND = EV_SYN = EV_FF  = EV_FF_STATUS = FF_STATUS = 1
KEY_MAX, KEY_CNT = 1, 2''')

    with open('../evdev/_input.py', 'w'): pass
    with open('../evdev/_uinput.py', 'w'): pass


# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'python-evdev'
copyright = u'2012-2013, Georgi Valkov'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The full version, including alpha/beta/rc tags.
release = kw['version']

# The short X.Y version.
version = release

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
exclude_patterns = ['_build']

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

if not on_rtd:
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
else:
    html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.

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
html_show_sourcelink = True

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
htmlhelp_basename = 'python-evdev-doc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'python-evdev.tex', u'evdev documentation',
   u'Georgi Valkov', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'python-evdev', u'python-evdev Documentation',
     [u'Georgi Valkov'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'python-evdev', u'python-evdev Documentation',
   u'Georgi Valkov', 'evdev', 'Bindings for the linux input handling subsystem.',
   'Miscellaneous'),
]

intersphinx_mapping = {'python': ('http://docs.python.org/3.3', None)}

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = device
# encoding: utf-8

import os
from select import select
from collections import namedtuple

from evdev import _input, _uinput, ecodes, util
from evdev.events import InputEvent


_AbsInfo = namedtuple('AbsInfo', ['value', 'min', 'max', 'fuzz', 'flat', 'resolution'])
_KbdInfo = namedtuple('KbdInfo', ['repeat', 'delay'])
_DeviceInfo = namedtuple('DeviceInfo', ['bustype', 'vendor', 'product', 'version'])


class AbsInfo(_AbsInfo):
    '''
    A ``namedtuple`` for storing absolut axis information -
    corresponds to the ``input_absinfo`` struct:

     - value
        Latest reported value for the axis.

     - min
        Specifies minimum value for the axis.

     - max
        Specifies maximum value for the axis.

     - fuzz
        Specifies fuzz value that is used to filter noise from the
        event stream.

     - flat
        Values that are within this value will be discarded by joydev
        interface and reported as 0 instead.

     - resolution
        Specifies resolution for the values reported for the axis.
        Resolution for main axes (``ABS_X, ABS_Y, ABS_Z``) is reported
        in units per millimeter (units/mm), resolution for rotational
        axes (``ABS_RX, ABS_RY, ABS_RZ``) is reported in units per
        radian.

    .. note: The input core does not clamp reported values to the
       ``[minimum, maximum]`` limits, such task is left to userspace.
    '''

    def __str__(self):
        return 'val {}, min {}, max {}, fuzz {}, flat {}, res {}'.format(*self)


class KbdInfo(_KbdInfo):
    '''
    Keyboard repeat rate:

    - repeat:
       Keyboard repeat rate in characters per second.

    - delay:
       Amount of time that a key must be depressed before it will start
       to repeat (in milliseconds).
    '''

    def __str__(self):
        return 'repeat {}, delay {}'.format(*self)


class DeviceInfo(_DeviceInfo):
    def __str__(self):
        msg = 'bus: {:04x}, vendor {:04x}, product {:04x}, version {:04x}'
        return msg.format(*self)


class InputDevice(object):
    '''
    A linux input device from which input events can be read.
    '''

    __slots__ = ('fn', 'fd', 'info', 'name', 'phys', '_rawcapabilities',
                 'version', 'ff_effects_count')

    def __init__(self, dev):
        '''
        :param dev: path to input device
        '''

        #: Path to input device.
        self.fn = dev

        #: A non-blocking file descriptor to the device file.
        self.fd = os.open(dev, os.O_RDWR | os.O_NONBLOCK)

        # Returns (bustype, vendor, product, version, name, phys, capabilities).
        info_res = _input.ioctl_devinfo(self.fd)

        #: A :class:`DeviceInfo <evdev.device.DeviceInfo>` instance.
        self.info = DeviceInfo(*info_res[:4])

        #: The name of the event device.
        self.name = info_res[4]

        #: The physical topology of the device.
        self.phys = info_res[5]

        #: The evdev protocol version.
        self.version = _input.ioctl_EVIOCGVERSION(self.fd)

        #: The raw dictionary of device capabilities - see `:func:capabilities()`.
        self._rawcapabilities = _input.ioctl_capabilities(self.fd)

        #: The number of force feedback effects the device can keep in its memory.
        self.ff_effects_count = _input.ioctl_EVIOCGEFFECTS(self.fd)

    def __del__(self):
        if hasattr(self, 'fd') and self.fd is not None:
            try:
                self.close()
            except OSError:
                pass

    def _capabilities(self, absinfo=True):
        res = {}
        for etype, ecodes in self._rawcapabilities.items():
            for code in ecodes:
                l = res.setdefault(etype, [])
                if isinstance(code, tuple):
                    if absinfo:
                        a = code[1]  # (0, 0, 0, 255, 0, 0)
                        i = AbsInfo(*a)
                        l.append((code[0], i))
                    else:
                        l.append(code[0])
                else:
                    l.append(code)

        return res

    def capabilities(self, verbose=False, absinfo=True):
        '''
        Return the event types that this device supports as a mapping of
        supported event types to lists of handled event codes. Example::

          { 1: [272, 273, 274],
            2: [0, 1, 6, 8] }

        If ``verbose`` is ``True``, event codes and types will be resolved
        to their names. Example::

          { ('EV_KEY', 1): [('BTN_MOUSE', 272),
                            ('BTN_RIGHT', 273),
                            ('BTN_MIDDLE', 273)],
            ('EV_REL', 2): [('REL_X', 0),
                            ('REL_Y', 1),
                            ('REL_HWHEEL', 6),
                            ('REL_WHEEL', 8)] }

        Unknown codes or types will be resolved to ``'?'``.

        If ``absinfo`` is ``True``, the list of capabilities will also
        include absolute axis information in the form of
        :class:`AbsInfo` instances::

          { 3: [ (0, AbsInfo(min=0, max=255, fuzz=0, flat=0)),
                 (1, AbsInfo(min=0, max=255, fuzz=0, flat=0)) ]}

        Combined with ``verbose`` the above becomes::

          { ('EV_ABS', 3): [ (('ABS_X', 0), AbsInfo(min=0, max=255, fuzz=0, flat=0)),
                             (('ABS_Y', 1), AbsInfo(min=0, max=255, fuzz=0, flat=0)) ]}

        '''

        if verbose:
            return dict(util.resolve_ecodes(self._capabilities(absinfo)))
        else:
            return self._capabilities(absinfo)

    def leds(self, verbose=False):
        '''
        Return currently set LED keys. Example::

          [0, 1, 8, 9]

        If ``verbose`` is ``True``, event codes are resolved to
        their names. Unknown codes are resolved to ``'?'``. Example::

          [('LED_NUML', 0), ('LED_CAPSL', 1), ('LED_MISC', 8), ('LED_MAIL', 9)]

        '''
        leds = _input.get_sw_led_snd(self.fd, ecodes.EV_LED)
        if verbose:
            return [(ecodes.LED[l] if l in ecodes.LED else '?', l) for l in leds]

        return leds

    def set_led(self, led_num, value):
        '''
        Set the state of the selected LED. Example::

           device.set_led(ecodes.LED_NUML, 1)

        ..
        '''
        _uinput.write(self.fd, ecodes.EV_LED, led_num, value)

    def __eq__(self, other):
        '''Two devices are considered equal if their :data:`info` attributes are equal.'''
        return self.info == other.info

    def __str__(self):
        msg = 'device {}, name "{}", phys "{}"'
        return msg.format(self.fn, self.name, self.phys)

    def __repr__(self):
        msg = (self.__class__.__name__, self.fn)
        return '{}({!r})'.format(*msg)

    def close(self):
        if self.fd > -1:
            try:
                os.close(self.fd)
            finally:
                self.fd = -1

    def fileno(self):
        '''
        Return the file descriptor to the open event device. This
        makes it possible to pass pass ``InputDevice`` instances
        directly to :func:`select.select()` and
        :class:`asyncore.file_dispatcher`.'''

        return self.fd

    def read_one(self):
        '''
        Read and return a single input event as an instance of
        :class:`InputEvent <evdev.events.InputEvent>`.

        Return ``None`` if there are no pending input events.
        '''

        # event -> (sec, usec, type, code, val)
        event = _input.device_read(self.fd)

        if event:
            return InputEvent(*event)

    def read_loop(self):
        '''Enter an endless ``select()`` loop that yields input events.'''

        while True:
            r, w, x = select([self.fd], [], [])
            for event in self.read():
                yield event

    def read(self):
        '''
        Read multiple input events from device. Return a generator
        object that yields :class:`InputEvent
        <evdev.events.InputEvent>` instances.
        '''

        # events -> [(sec, usec, type, code, val), ...]
        events = _input.device_read_many(self.fd)

        for i in events:
            yield InputEvent(*i)

    def grab(self):
        '''
        Grab input device using ``EVIOCGRAB`` - other applications will
        be unable to receive events until the device is released. Only
        one process can hold a ``EVIOCGRAB`` on a device.

        .. warning:: Grabbing an already grabbed device will raise an
                     ``IOError``.'''

        _input.ioctl_EVIOCGRAB(self.fd, 1)

    def ungrab(self):
        '''Release device if it has been already grabbed (uses
        `EVIOCGRAB`).

        .. warning:: Releasing an already released device will raise an
                     ``IOError('Invalid argument')``.'''

        _input.ioctl_EVIOCGRAB(self.fd, 0)

    def upload_effect(self, effect):
        '''Upload a force feedback effect to a force feedback device.'''

        data = bytes(buffer(effect)[:])
        ff_id = _input.upload_effect(self.fd, data)
        return ff_id

    def erase_effect(self, ff_id):
        '''Erase a force effect from a force feedback device. This
        also stops the effect.'''

        _input.erase_effect(self.fd, ff_id)

    @property
    def repeat(self):
        '''Get or set the keyboard repeat rate (in characters per
        minute) and delay (in milliseconds).'''

        return KbdInfo(*_input.ioctl_EVIOCGREP(self.fd))

    @repeat.setter
    def repeat(self, value):
        return _input.ioctl_EVIOCSREP(self.fd, *value)

########NEW FILE########
__FILENAME__ = ecodes
# encoding: utf-8

'''
This modules exposes the integer constants defined in ``linux/input.h``.

Exposed constants::

    KEY, ABS, REL, SW, MSC, LED, BTN, REP, SND, ID, EV,
    BUS, SYN, FF, FF_STATUS

This module also provides numerous reverse and forward mappings that are best
illustrated by a few examples::

    >>> evdev.ecodes.KEY_A
    30

    >>> evdev.ecodes.ecodes['KEY_A']
    30

    >>> evdev.ecodes.KEY[30]
    'KEY_A'

    >>> evdev.ecodes.REL[0]
    'REL_X'

    >>> evdev.ecodes.EV[evdev.ecodes.EV_KEY]
    'EV_KEY'

    >>> evdev.ecodes.bytype[evdev.ecodes.EV_REL][0]
    'REL_X'

Values in reverse mappings may point to one or more ecodes. For example::

    >>> evdev.ecodes.FF[80]
    ['FF_EFFECT_MIN', 'FF_RUMBLE']

    >>> evdev.ecodes.FF[81]
    'FF_PERIODIC'
'''

from inspect import getmembers
from evdev import _ecodes


#: Mapping of names to values.
ecodes = {}

prefixes = 'KEY ABS REL SW MSC LED BTN REP SND ID EV BUS SYN FF_STATUS FF'
prev_prefix = ''
g = globals()

# eg. code: 'REL_Z', val: 2
for code, val in getmembers(_ecodes):
    for prefix in prefixes.split():  # eg. 'REL'
        if code.startswith(prefix):
            ecodes[code] = val
            # FF_STATUS codes should not appear in the FF reverse mapping
            if not code.startswith(prev_prefix):
                d = g.setdefault(prefix, {})
                # codes that share the same value will be added to a list. eg:
                # >>> ecodes.FF_STATUS
                # {0: 'FF_STATUS_STOPPED', 1: ['FF_STATUS_MAX', 'FF_STATUS_PLAYING']}
                if val in d:
                    if isinstance(d[val], list):
                        d[val].append(code)
                    else:
                        d[val] = [d[val], code]
                else:
                    d[val] = code

        prev_prefix = prefix

#: Keys are a combination of all BTN and KEY codes.
keys = {}
keys.update(BTN)
keys.update(KEY)

# make keys safe to use for the default list of uinput device
# capabilities
del keys[_ecodes.KEY_MAX]
del keys[_ecodes.KEY_CNT]

#: Mapping of event types to other value/name mappings.
bytype = {
    _ecodes.EV_KEY: keys,
    _ecodes.EV_ABS: ABS,
    _ecodes.EV_REL: REL,
    _ecodes.EV_SW:  SW,
    _ecodes.EV_MSC: MSC,
    _ecodes.EV_LED: LED,
    _ecodes.EV_REP: REP,
    _ecodes.EV_SND: SND,
    _ecodes.EV_SYN: SYN,
    _ecodes.EV_FF:  FF,
    _ecodes.EV_FF_STATUS: FF_STATUS, }

from evdev._ecodes import *

# cheaper than whitelisting in an __all__
del code, val, prefix, getmembers, g, d, prefixes, prev_prefix

########NEW FILE########
__FILENAME__ = events
# encoding: utf-8

'''
This module provides the :class:`InputEvent` class, which closely
resembles the ``input_event`` struct defined in ``linux/input.h``:

.. code-block:: c

    struct input_event {
        struct timeval time;
        __u16 type;
        __u16 code;
        __s32 value;
    };

This module also defines :class:`InputEvent` sub-classes that know
more about the different types of events (key, abs, rel etc). The
:data:`event_factory` dictionary maps event types to these classes.

Assuming you use the :func:`evdev.util.categorize()` function to
categorize events according to their type, adding or replacing a class
for a specific event type becomes a matter of modifying
:data:`event_factory`.

All classes in this module have reasonable ``str()`` and ``repr()``
methods::

    >>> print(event)
    event at 1337197425.477827, code 04, type 04, val 458792
    >>> print(repr(event))
    InputEvent(1337197425L, 477827L, 4, 4, 458792L)

    >>> print(key_event)
    key event at 1337197425.477835, 28 (KEY_ENTER), up
    >>> print(repr(key_event))
    KeyEvent(InputEvent(1337197425L, 477835L, 1, 28, 0L))
'''

# event type descriptions have been taken mot-a-mot from:
# http://www.kernel.org/doc/Documentation/input/event-codes.txt

from evdev.ecodes import keys, KEY, SYN, REL, ABS, EV_KEY, EV_REL, EV_ABS, EV_SYN


class InputEvent(object):
    '''A generic input event.'''

    __slots__ = 'sec', 'usec', 'type', 'code', 'value'

    def __init__(self, sec, usec, type, code, value):
        #: Time in seconds since epoch at which event occurred.
        self.sec = sec

        #: Microsecond portion of the timestamp.
        self.usec = usec

        #: Event type - one of ``ecodes.EV_*``.
        self.type = type

        #: Event code related to the event type.
        self.code = code

        #: Event value related to the event type.
        self.value = value

    def timestamp(self):
        '''Return event timestamp as a float.'''
        return self.sec + (self.usec / 1000000.0)

    def __str__(s):
        msg = 'event at {:f}, code {:02d}, type {:02d}, val {:02d}'
        return msg.format(s.timestamp(), s.code, s.type, s.value)

    def __repr__(s):
        msg = '{}({!r}, {!r}, {!r}, {!r}, {!r})'
        return msg.format(s.__class__.__name__,
                          s.sec, s.usec, s.type, s.code, s.value)


class KeyEvent(object):
    '''An event generated by a keyboard, button or other key-like devices.'''

    key_up   = 0x0
    key_down = 0x1
    key_hold = 0x2

    __slots__ = 'scancode', 'keycode', 'keystate', 'event'

    def __init__(self, event):
        if event.value == 0:
            self.keystate = KeyEvent.key_up
        elif event.value == 2:
            self.keystate = KeyEvent.key_hold
        elif event.value == 1:
            self.keystate = KeyEvent.key_down

        self.keycode  = keys[event.code]  # :todo:
        self.scancode = event.code

        #: Reference to an :class:`InputEvent` instance.
        self.event = event

    def __str__(self):
        try:
            ks = ('up', 'down', 'hold')[self.keystate]
        except IndexError:
            ks = 'unknown'

        msg = 'key event at {:f}, {} ({}), {}'
        return msg.format(self.event.timestamp(),
                          self.scancode, self.keycode, ks)

    def __repr__(s):
        return '{}({!r})'.format(s.__class__.__name__, s.event)


class RelEvent(object):
    '''A relative axis event (e.g moving the mouse 5 units to the left).'''

    __slots__ = 'event'

    def __init__(self, event):
        #: Reference to an :class:`InputEvent` instance.
        self.event = event

    def __str__(self):
        msg = 'relative axis event at {:f}, {} '
        return msg.format(self.event.timestamp(), REL[self.event.code])

    def __repr__(s):
        return '{}({!r})'.format(s.__class__.__name__, s.event)


class AbsEvent(object):
    '''An absolute axis event (e.g the coordinates of a tap on a touchscreen).'''

    __slots__ = 'event'

    def __init__(self, event):
        #: Reference to an :class:`InputEvent` instance.
        self.event = event

    def __str__(self):
        msg = 'absolute axis event at {:f}, {} '
        return msg.format(self.event.timestamp(), ABS[self.event.code])

    def __repr__(s):
        return '{}({!r})'.format(s.__class__.__name__, s.event)


class SynEvent(object):
    '''
    A synchronization event. Synchronization events are used as
    markers to separate event. Used as markers to separate
    events. Events may be separated in time or in space, such as with
    the multitouch protocol.
    '''

    __slots__ = 'event'

    def __init__(self, event):
        #: Reference to an :class:`InputEvent` instance.
        self.event = event

    def __str__(self):
        msg = 'synchronization event at {:f}, {} '
        return msg.format(self.event.timestamp(), SYN[self.event.code])

    def __repr__(s):
        return '{}({!r})'.format(s.__class__.__name__, s.event)


#: A mapping of event types to :class:`InputEvent` sub-classes. Used
#: by:func:`evdev.util.categorize()`
event_factory = {
    EV_KEY: KeyEvent,
    EV_REL: RelEvent,
    EV_ABS: AbsEvent,
    EV_SYN: SynEvent,
}


__all__ = ('InputEvent', 'KeyEvent', 'RelEvent', 'SynEvent',
           'AbsEvent', 'event_factory')

########NEW FILE########
__FILENAME__ = ff
# encoding: utf-8

import ctypes
from evdev import ecodes


_u8  = ctypes.c_uint8
_u16 = ctypes.c_uint16
_u32 = ctypes.c_uint32
_s16 = ctypes.c_int16

class Replay(ctypes.Structure):
    '''
    Defines scheduling of the force-feedback effect
    @length: duration of the effect
    @delay: delay before effect should start playing
    '''

    _fields_ = [
        ('length', _u16),
        ('delay',  _u16),
    ]


class Trigger(ctypes.Structure):
    '''
    Defines what triggers the force-feedback effect
    @button: number of the button triggering the effect
    @interval: controls how soon the effect can be re-triggered
    '''

    _fields_ = [
        ('button', _u16),
        ('interval',  _u16),
    ]


class Envelope(ctypes.Structure):
    '''
    Generic force-feedback effect envelope
    @attack_length: duration of the attack (ms)
    @attack_level: level at the beginning of the attack
    @fade_length: duration of fade (ms)
    @fade_level: level at the end of fade

    The @attack_level and @fade_level are absolute values; when applying
    envelope force-feedback core will convert to positive/negative
    value based on polarity of the default level of the effect.
    Valid range for the attack and fade levels is 0x0000 - 0x7fff
    '''

    _fields_ = [
        ('attach_length', _u16),
        ('attack_level', _u16),
        ('fade_length', _u16),
        ('fade_level', _u16),
    ]


class Constant(ctypes.Structure):
    '''
    Defines parameters of a constant force-feedback effect
    @level: strength of the effect; may be negative
    @envelope: envelope data
    '''

    _fields_ = [
        ('level', _s16),
        ('ff_envelope', Envelope),
    ]


class Ramp(ctypes.Structure):
    '''
    Defines parameters of a ramp force-feedback effect
    @start_level: beginning strength of the effect; may be negative
    @end_level: final strength of the effect; may be negative
    @envelope: envelope data
    '''

    _fields_ = [
        ('start_level', _s16),
        ('end_level', _s16),
        ('ff_envelope', Envelope),
    ]


class Condition(ctypes.Structure):
    '''
    Defines a spring or friction force-feedback effect
    @right_saturation: maximum level when joystick moved all way to the right
    @left_saturation: same for the left side
    @right_coeff: controls how fast the force grows when the joystick moves to the right
    @left_coeff: same for the left side
    @deadband: size of the dead zone, where no force is produced
    @center: position of the dead zone
    '''

    _fields_ = [
        ('right_saturation', _u16),
        ('left_saturation', _u16),
        ('right_coeff', _s16),
        ('left_foeff', _s16),
        ('deadband', _u16),
        ('center', _s16),
    ]


class Periodic(ctypes.Structure):
    '''
    Defines parameters of a periodic force-feedback effect
    @waveform: kind of the effect (wave)
    @period: period of the wave (ms)
    @magnitude: peak value
    @offset: mean value of the wave (roughly)
    @phase: 'horizontal' shift
    @envelope: envelope data
    @custom_len: number of samples (FF_CUSTOM only)
    @custom_data: buffer of samples (FF_CUSTOM only)
    '''

    _fields_ = [
        ('waveform', _u16),
        ('period', _u16),
        ('magnitude', _s16),
        ('offset', _s16),
        ('phase', _u16),
        ('envelope', Envelope),
        ('custom_len', _u32),
        ('custom_data', ctypes.POINTER(_s16)),
    ]


class Rumble(ctypes.Structure):
    '''
    Defines parameters of a periodic force-feedback effect
    @strong_magnitude: magnitude of the heavy motor
    @weak_magnitude: magnitude of the light one

    Some rumble pads have two motors of different weight. Strong_magnitude
    represents the magnitude of the vibration generated by the heavy one.
    '''

    _fields_ = [
        ('strong_magnitude', _u16),
        ('weak_magnitude', _u16),
    ]


class EffectType(ctypes.Union):
    _fields_ = [
        ('ff_constant_effect', Constant),
        ('ff_ramp_effect', Ramp),
        ('ff_periodic_effect', Periodic),
        ('ff_condition_effect', Condition * 2),  # one for each axis
        ('ff_rumble_effect', Rumble),
    ]


class Effect(ctypes.Structure):
    _fields_ = [
        ('type', _u16),
        ('id', _s16),
        ('direction', _u16),
        ('ff_trigger', Trigger),
        ('ff_replay', Replay),
        ('u', EffectType)
    ]

# ff_types = {
#     ecodes.FF_CONSTANT,
#     ecodes.FF_PERIODIC,
#     ecodes.FF_RAMP,
#     ecodes.FF_SPRING,
#     ecodes.FF_FRICTION,
#     ecodes.FF_DAMPER,
#     ecodes.FF_RUMBLE,
#     ecodes.FF_INERTIA,
#     ecodes.FF_CUSTOM,
# }

########NEW FILE########
__FILENAME__ = genecodes
#!/usr/bin/env python
# -*- coding: utf-8; -*-

'''
Generate a Python extension module that exports macros from
/usr/include/linux/input.h
'''

import os, sys, re


template = r'''
#include <Python.h>
#include <linux/input.h>

/* Automatically generated by evdev.genecodes */
/* Generated on %s */

#define MODULE_NAME "_ecodes"
#define MODULE_HELP "linux/input.h macros"

static PyMethodDef MethodTable[] = {
    { NULL, NULL, 0, NULL}
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    MODULE_NAME,
    MODULE_HELP,
    -1,          /* m_size */
    MethodTable, /* m_methods */
    NULL,        /* m_reload */
    NULL,        /* m_traverse */
    NULL,        /* m_clear */
    NULL,        /* m_free */
};
#endif

static PyObject *
moduleinit(void)
{

#if PY_MAJOR_VERSION >= 3
    PyObject* m = PyModule_Create(&moduledef);
#else
    PyObject* m = Py_InitModule3(MODULE_NAME, MethodTable, MODULE_HELP);
#endif

    if (m == NULL) return NULL;

%s

    return m;
}

#if PY_MAJOR_VERSION >= 3
PyMODINIT_FUNC
PyInit__ecodes(void)
{
    return moduleinit();
}
#else
PyMODINIT_FUNC
init_ecodes(void)
{
    moduleinit();
}
#endif
'''

header = '/usr/include/linux/input.h' if len(sys.argv) == 1 else sys.argv[1]
regex = r'#define +((?:KEY|ABS|REL|SW|MSC|LED|BTN|REP|SND|ID|EV|BUS|SYN|FF)_\w+)'
regex = re.compile(regex)

if not os.path.exists(header):
    print('no such file: %s' % header)
    sys.exit(1)

def getmacros():
    for line in open(header):
        macro = regex.search(line)
        if macro:
            yield '    PyModule_AddIntMacro(m, %s);' % macro.group(1)

uname = list(os.uname()); del uname[1]
uname = ' '.join(uname)

macros = os.linesep.join(getmacros())
print(template % (uname, macros))

########NEW FILE########
__FILENAME__ = uinput
# encoding: utf-8

import os
import stat
import time

from evdev import _uinput
from evdev import ecodes, util, device


class UInputError(Exception):
    pass


class UInput(object):
    '''
    A userland input device and that can inject input events into the
    linux input subsystem.
    '''

    __slots__ = (
        'name', 'vendor', 'product', 'version', 'bustype',
        'events', 'devnode', 'fd', 'device',
    )

    def __init__(self,
                 events=None,
                 name='py-evdev-uinput',
                 vendor=0x1, product=0x1, version=0x1, bustype=0x3,
                 devnode='/dev/uinput'):
        '''
        :param events: the event types and codes that the uinput
                       device will be able to inject - defaults to all
                       key codes.

        :type events: dictionary of event types mapping to lists of
                      event codes.

        :param name: the name of the input device.
        :param vendor:  vendor identifier.
        :param product: product identifier.
        :param version: version identifier.
        :param bustype: bustype identifier.

        .. note:: If you do not specify any events, the uinput device
                  will be able to inject only ``KEY_*`` and ``BTN_*``
                  event codes.
        '''

        self.name = name         #: Uinput device name.
        self.vendor = vendor     #: Device vendor identifier.
        self.product = product   #: Device product identifier.
        self.version = version   #: Device version identifier.
        self.bustype = bustype   #: Device bustype - eg. ``BUS_USB``.
        self.devnode = devnode   #: Uinput device node - eg. ``/dev/uinput/``.

        if not events:
            events = {ecodes.EV_KEY: ecodes.keys.keys()}

        # the min, max, fuzz and flat values for the absolute axis for
        # a given code
        absinfo = []

        self._verify()

        #: Write-only, non-blocking file descriptor to the uinput device node.
        self.fd = _uinput.open(devnode)

        # set device capabilities
        for etype, codes in events.items():
            for code in codes:
                # handle max, min, fuzz, flat
                if isinstance(code, (tuple, list, device.AbsInfo)):
                    # flatten (ABS_Y, (0, 255, 0, 0)) to (ABS_Y, 0, 255, 0, 0)
                    f = [code[0]]; f += code[1]
                    absinfo.append(f)
                    code = code[0]

                #:todo: a lot of unnecessary packing/unpacking
                _uinput.enable(self.fd, etype, code)

        # create uinput device
        _uinput.create(self.fd, name, vendor, product, version, bustype, absinfo)

        #: An :class:`InputDevice <evdev.device.InputDevice>` instance
        #: for the fake input device. ``None`` if the device cannot be
        #: opened for reading and writing.
        self.device = self._find_device()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        if hasattr(self, 'fd'):
            self.close()

    def __repr__(self):
        # :todo:
        v = (repr(getattr(self, i)) for i in
             ('name', 'bustype', 'vendor', 'product', 'version'))
        return '{}({})'.format(self.__class__.__name__, ', '.join(v))

    def __str__(self):
        msg = ('name "{}", bus "{}", vendor "{:04x}", product "{:04x}", version "{:04x}"\n'
               'event types: {}')

        evtypes = [i[0] for i in self.capabilities(True).keys()]
        msg = msg.format(self.name, ecodes.BUS[self.bustype],
                         self.vendor, self.product,
                         self.version, ' '.join(evtypes))

        return msg

    def close(self):
        # close the associated InputDevice, if it was previously opened
        if self.device is not None:
            self.device.close()

        # destroy the uinput device
        if self.fd > -1:
            _uinput.close(self.fd)
            self.fd = -1

    def write_event(self, event):
        '''
        Inject an input event into the input subsystem. Events are
        queued until a synchronization event is received.

        :param event: InputEvent instance or an object with an
                      ``event`` attribute (:class:`KeyEvent
                      <evdev.events.KeyEvent>`, :class:`RelEvent
                      <evdev.events.RelEvent>` etc).

        Example::

            ev = InputEvent(1334414993, 274296, ecodes.EV_KEY, ecodes.KEY_A, 1)
            ui.write_event(ev)
        '''

        if hasattr(event, 'event'):
            event = event.event

        self.write(event.type, event.code, event.value)

    def write(self, etype, code, value):
        '''
        Inject an input event into the input subsystem. Events are
        queued until a synchronization event is received.

        :param etype: event type (eg. ``EV_KEY``).
        :param code:  event code (eg. ``KEY_A``).
        :param value: event value (eg. 0 1 2 - depends on event type).

        Example::

            ui.write(e.EV_KEY, e.KEY_A, 1) # key A - down
            ui.write(e.EV_KEY, e.KEY_A, 0) # key A - up
        '''

        _uinput.write(self.fd, etype, code, value)

    def syn(self):
        '''
        Inject a ``SYN_REPORT`` event into the input subsystem. Events
        queued by :func:`write()` will be fired. If possible, events
        will be merged into an 'atomic' event.
        '''

        _uinput.write(self.fd, ecodes.EV_SYN, ecodes.SYN_REPORT, 0)

    def capabilities(self, verbose=False, absinfo=True):
        '''See :func:`capabilities <evdev.device.InputDevice.capabilities>`.'''
        if self.device is None:
            raise UInputError('input device not opened - cannot read capabilites')

        return self.device.capabilities(verbose, absinfo)

    def _verify(self):
        '''
        Verify that an uinput device exists and is readable and writable
        by the current process.
        '''

        try:
            m = os.stat(self.devnode)[stat.ST_MODE]
            if not stat.S_ISCHR(m):
                raise
        except (IndexError, OSError):
            msg = '"{}" does not exist or is not a character device file '\
                  '- verify that the uinput module is loaded'
            raise UInputError(msg.format(self.devnode))

        if not os.access(self.devnode, os.W_OK):
            msg = '"{}" cannot be opened for writing'
            raise UInputError(msg.format(self.devnode))

        if len(self.name) > _uinput.maxnamelen:
            msg = 'uinput device name must not be longer than {} characters'
            raise UInputError(msg.format(_uinput.maxnamelen))

    def _find_device(self):
        #:bug: the device node might not be immediately available
        time.sleep(0.1)

        for fn in util.list_devices('/dev/input/'):
            d = device.InputDevice(fn)
            if d.name == self.name:
                return d

########NEW FILE########
__FILENAME__ = util
# encoding: utf-8

import os
import stat
import glob

from evdev import ecodes
from evdev.events import event_factory


def list_devices(input_device_dir='/dev/input'):
    '''List readable, character devices.'''

    fns = glob.glob('{}/event*'.format(input_device_dir))
    fns = list(filter(is_device, fns))

    return fns


def is_device(fn):
    '''Check if ``fn`` is a readable and writable character device.'''

    if not os.path.exists(fn):
        return False

    m = os.stat(fn)[stat.ST_MODE]
    if not stat.S_ISCHR(m):
        return False

    if not os.access(fn, os.R_OK | os.W_OK):
        return False

    return True


def categorize(event):
    '''
    Categorize an event according to its type.

    The :data:`event_factory <evdev.events.event_factory>` dictionary
    maps event types to sub-classes of :class:`InputEvent
    <evdev.events.InputEvent>`. If there is no corresponding key, the
    event is returned as it is.
    '''

    if event.type in event_factory:
        return event_factory[event.type](event)
    else:
        return event


def resolve_ecodes(typecodemap, unknown='?'):
    '''
    Resolve event codes and types to their verbose names.

    :param typecodemap: mapping of event types to lists of event codes.
    :param unknown: symbol to which unknown types or codes will be resolved.

    Example::

        resolve_ecodes({ 1: [272, 273, 274] })
        { ('EV_KEY', 1): [('BTN_MOUSE',  272),
                          ('BTN_RIGHT',  273),
                          ('BTN_MIDDLE', 274)] }

    If typecodemap contains absolute axis info (instances of
    :class:`AbsInfo <evdev.device.AbsInfo>` ) the result would look
    like::

        resolve_ecodes({ 3: [(0, AbsInfo(...))] })
        { ('EV_ABS', 3L): [(('ABS_X', 0L), AbsInfo(...))] }
    '''

    for etype, codes in typecodemap.items():
        type_name = ecodes.EV[etype]

        # ecodes.keys are a combination of KEY_ and BTN_ codes
        if etype == ecodes.EV_KEY:
            code_names = ecodes.keys
        else:
            code_names = getattr(ecodes, type_name.split('_')[-1])

        res = []
        for i in codes:
            # elements with AbsInfo(), eg { 3 : [(0, AbsInfo(...)), (1, AbsInfo(...))] }
            if isinstance(i, tuple):
                l = ((code_names[i[0]], i[0]), i[1]) if i[0] in code_names \
                    else ((unknown, i[0]), i[1])

            # just ecodes { 0 : [0, 1, 3], 1 : [30, 48] }
            else:
                l = (code_names[i], i) if i in code_names else (unknown, i)

            res.append(l)

        yield (type_name, etype), res


__all__ = ('list_devices', 'is_device', 'categorize', 'resolve_ecodes')

########NEW FILE########
__FILENAME__ = test_ecodes
# encoding: utf-8

from evdev import ecodes

prefixes = 'KEY ABS REL SW MSC LED BTN REP SND ID EV BUS SYN FF_STATUS FF'

def to_tuples(l):
    t = lambda x: tuple(x) if isinstance(x, list) else x
    return map(t, l)

def test_equality():
    keys = []
    for i in prefixes.split():
        keys.extend(getattr(ecodes, i, {}).keys())

    assert set(keys) == set(ecodes.ecodes.values())

def test_access():
    assert ecodes.KEY_A == ecodes.ecodes['KEY_A'] == ecodes.KEY_A
    assert ecodes.KEY[ecodes.ecodes['KEY_A']] == 'KEY_A'
    assert ecodes.REL[0] == 'REL_X'

def test_overlap():
    vals_ff = set(to_tuples(ecodes.FF.values()))
    vals_ff_status = set(to_tuples(ecodes.FF_STATUS.values()))
    assert bool(vals_ff & vals_ff_status) == False

########NEW FILE########
__FILENAME__ = test_events
# encoding: utf-8

from evdev import events, ecodes, util


def test_categorize():
    e = events.InputEvent(1036996631, 984417, ecodes.EV_KEY, ecodes.KEY_A, 0)
    assert isinstance(util.categorize(e), events.KeyEvent)

    e = events.InputEvent(1036996631, 984417, ecodes.EV_ABS, 0, 0)
    assert isinstance(util.categorize(e), events.AbsEvent)

    e = events.InputEvent(1036996631, 984417, ecodes.EV_REL, 0, 0)
    assert isinstance(util.categorize(e), events.RelEvent)

    e = events.InputEvent(1036996631, 984417, ecodes.EV_MSC, 0, 0)
    assert e == util.categorize(e)

def test_keyevent():
    e = events.InputEvent(1036996631, 984417, ecodes.EV_KEY, ecodes.KEY_A, 2)
    k = events.KeyEvent(e)

    assert k.keystate == events.KeyEvent.key_hold
    assert k.event == e
    assert k.scancode == ecodes.KEY_A
    assert k.keycode == 'KEY_A' # :todo:


########NEW FILE########
__FILENAME__ = test_uinput
# encoding: utf-8

from select import select
from pytest import raises

from evdev import uinput, ecodes, events, device, util


uinput_options = {
    'name'      : 'test-py-evdev-uinput',
    'bustype'   : ecodes.BUS_USB,
    'vendor'    : 0x1100,
    'product'   : 0x2200,
    'version'   : 0x3300,
}


def pytest_funcarg__c(request):
    return uinput_options.copy()


def device_exists(bustype, vendor, product, version):
    match = 'I: Bus=%04hx Vendor=%04hx Product=%04hx Version=%04hx' % \
            (bustype, vendor, product, version)

    for line in open('/proc/bus/input/devices'):
        if line.strip() == match: return True

    return False


def test_open(c):
    ui = uinput.UInput(**c)
    args = (c['bustype'], c['vendor'], c['product'], c['version'])
    assert device_exists(*args)
    ui.close()
    assert not device_exists(*args)

def test_open_context(c):
    args = (c['bustype'], c['vendor'], c['product'], c['version'])
    with uinput.UInput(**c):
        assert device_exists(*args)
    assert not device_exists(*args)

def test_maxnamelen(c):
    with raises(uinput.UInputError):
        c['name'] = 'a' * 150
        uinput.UInput(**c)

def test_enable_events(c):
    e = ecodes
    c['events'] = {e.EV_KEY : [e.KEY_A, e.KEY_B, e.KEY_C]}

    with uinput.UInput(**c) as ui:
        cap = ui.capabilities()
        assert e.EV_KEY in cap
        assert sorted(cap[e.EV_KEY]) == sorted(c['events'][e.EV_KEY])

def test_abs_values(c):
    e = ecodes
    c['events'] = {
        e.EV_KEY : [e.KEY_A, e.KEY_B],
        e.EV_ABS : [(e.ABS_X, (0, 255, 0, 0)),
                    (e.ABS_Y, device.AbsInfo(0, 255, 5, 10, 0, 0))],
    }

    with uinput.UInput(**c) as ui:
        c = ui.capabilities()
        abs = device.AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)
        assert c[e.EV_ABS][0] == (0, abs)
        abs = device.AbsInfo(value=0, min=0, max=255, fuzz=5, flat=10, resolution=0)
        assert c[e.EV_ABS][1] == (1, abs)

        c = ui.capabilities(verbose=True)
        abs = device.AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)
        assert c[('EV_ABS', 3)][0] == (('ABS_X', 0), abs)

        c = ui.capabilities(verbose=False, absinfo=False)
        assert c[e.EV_ABS] == list((0, 1))

def test_write(c):
    with uinput.UInput(**c) as ui:
        d = ui.device
        wrote = False

        while True:
            r, w, x = select([d], [d], [])

            if w and not wrote:
                ui.write(ecodes.EV_KEY, ecodes.KEY_P, 1) # KEY_P down
                ui.write(ecodes.EV_KEY, ecodes.KEY_P, 1) # KEY_P down
                ui.write(ecodes.EV_KEY, ecodes.KEY_P, 0) # KEY_P up
                ui.write(ecodes.EV_KEY, ecodes.KEY_A, 1) # KEY_A down
                ui.write(ecodes.EV_KEY, ecodes.KEY_A, 2) # KEY_A hold
                ui.write(ecodes.EV_KEY, ecodes.KEY_A, 0) # KEY_P up
                ui.syn()
                wrote = True

            if r:
                evs = list(d.read())

                assert evs[0].code == ecodes.KEY_P and evs[0].value == 1
                assert evs[1].code == ecodes.KEY_P and evs[1].value == 0
                assert evs[2].code == ecodes.KEY_A and evs[2].value == 1
                assert evs[3].code == ecodes.KEY_A and evs[3].value == 2
                assert evs[4].code == ecodes.KEY_A and evs[4].value == 0
                break

########NEW FILE########
