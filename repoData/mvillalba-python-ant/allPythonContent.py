__FILENAME__ = 01-reset
"""
Perform basic node initialization and shutdown cleanly.

"""

import sys

from ant.core import driver
from ant.core import node

from config import *

# Initialize and configure our ANT stick's driver
stick = driver.USB1Driver(SERIAL, log=LOG, debug=DEBUG)

# Now create an ANT node, and pass it our driver so it can talk to the stick
antnode = node.Node(stick)

# Open driver if closed, start event listener, reset internal settings, and
# send a system reset command to the ANT stick (blocks).
try:
    antnode.start()
except driver.DriverError, e:
    print e
    sys.exit()

# At any point in our node's life, we could manually call reset() to re-
# initialize the stick and Node. Like this:
#antnode.reset()

# Stop the ANT node. This should close all open channels, and do final system
# reset on the stick. However, considering we just did a reset, we explicitly
# tell our node to skip the reset. This call will also automatically release
# the stick by calling close() on the driver.
antnode.stop(reset=False)

########NEW FILE########
__FILENAME__ = 02-capabilities-USB
"""
Interrogate stick for supported capabilities.

"""

import sys

from ant.core import driver
from ant.core import node

from config import *

# Initialize
stick = driver.USB2Driver(SERIAL, log=LOG, debug=DEBUG)
antnode = node.Node(stick)
antnode.start()

# Interrogate stick
# Note: This method will return immediately, as the stick's capabilities are
# interrogated on node initialization (node.start()) in order to set proper
# internal Node instance state.
capabilities = antnode.getCapabilities()

print 'Maximum channels:', capabilities[0]
print 'Maximum network keys:', capabilities[1]
print 'Standard options: %X' % capabilities[2][0]
print 'Advanced options: %X' % capabilities[2][1]

# Shutdown
antnode.stop()

########NEW FILE########
__FILENAME__ = 02-capabilities
"""
Interrogate stick for supported capabilities.

"""

import sys

from ant.core import driver
from ant.core import node

from config import *

# Initialize
stick = driver.USB1Driver(SERIAL, log=LOG, debug=DEBUG)
antnode = node.Node(stick)
antnode.start()

# Interrogate stick
# Note: This method will return immediately, as the stick's capabilities are
# interrogated on node initialization (node.start()) in order to set proper
# internal Node instance state.
capabilities = antnode.getCapabilities()

print 'Maximum channels:', capabilities[0]
print 'Maximum network keys:', capabilities[1]
print 'Standard options: %X' % capabilities[2][0]
print 'Advanced options: %X' % capabilities[2][1]

# Shutdown
antnode.stop()

########NEW FILE########
__FILENAME__ = 03-basicchannel
"""
Initialize a basic broadcast slave channel for listening to
an ANT+ HR monitor.

"""

import sys
import time

from ant.core import driver
from ant.core import node
from ant.core.constants import *

from config import *

NETKEY = '\xB9\xA5\x21\xFB\xBD\x72\xC3\x45'

# Initialize
stick = driver.USB1Driver(SERIAL, log=LOG, debug=DEBUG)
antnode = node.Node(stick)
antnode.start()

# Set network key
key = node.NetworkKey('N:ANT+', NETKEY)
antnode.setNetworkKey(0, key)

# Get the first unused channel. Returns an instance of the node.Channel class.
channel = antnode.getFreeChannel()

# Let's give our channel a nickname
channel.name = 'C:HRM'

# Initialize it as a receiving channel using our network key
channel.assign('N:ANT+', CHANNEL_TYPE_TWOWAY_RECEIVE)

# Now set the channel id for pairing with an ANT+ HR monitor
channel.setID(120, 0, 0)

# Listen forever and ever (not really, but for a long time)
channel.setSearchTimeout(TIMEOUT_NEVER)

# We want a ~4.06 Hz transmission period
channel.setPeriod(8070)

# And ANT frequency 57
channel.setFrequency(57)

# Time to go live
channel.open()

print "Listening for HR monitor events (120 seconds)..."
time.sleep(120)

# Shutdown channel
channel.close()
channel.unassign()

# Shutdown
antnode.stop()

########NEW FILE########
__FILENAME__ = 04-processevents
"""
Extending on demo-03, implements an event callback we can use to process the
incoming data.

"""

import sys
import time

from ant.core import driver
from ant.core import node
from ant.core import event
from ant.core import message
from ant.core.constants import *

from config import *

NETKEY = '\xB9\xA5\x21\xFB\xBD\x72\xC3\x45'

# A run-the-mill event listener
class HRMListener(event.EventCallback):
    def process(self, msg):
        if isinstance(msg, message.ChannelBroadcastDataMessage):
            print 'Heart Rate:', ord(msg.payload[-1])

# Initialize
stick = driver.USB1Driver(SERIAL, log=LOG, debug=DEBUG)
antnode = node.Node(stick)
antnode.start()

# Setup channel
key = node.NetworkKey('N:ANT+', NETKEY)
antnode.setNetworkKey(0, key)
channel = antnode.getFreeChannel()
channel.name = 'C:HRM'
channel.assign('N:ANT+', CHANNEL_TYPE_TWOWAY_RECEIVE)
channel.setID(120, 0, 0)
channel.setSearchTimeout(TIMEOUT_NEVER)
channel.setPeriod(8070)
channel.setFrequency(57)
channel.open()

# Setup callback
# Note: We could also register an event listener for non-channel events by
# calling registerEventListener() on antnode rather than channel.
channel.registerCallback(HRMListener())

# Wait
print "Listening for HR monitor events (120 seconds)..."
time.sleep(120)

# Shutdown
channel.close()
channel.unassign()
antnode.stop()

########NEW FILE########
__FILENAME__ = 05-rawmessage
"""
Do a system reset using raw messages.

"""

import sys
import time

from ant.core import driver
from ant.core import message
from ant.core.constants import *

from config import *

# Initialize
stick = driver.USB1Driver(SERIAL, log=LOG, debug=DEBUG)
stick.open()

# Prepare system reset message
msg = message.Message()
msg.setType(MESSAGE_SYSTEM_RESET)
msg.setPayload('\x00')

# Send
stick.write(msg.encode())

# Wait for reset to complete
time.sleep(1)

# Alternatively, we could have done this:
msg = message.SystemResetMessage()
stick.write(msg.encode())
time.sleep(1)

# Shutdown
stick.close()

########NEW FILE########
__FILENAME__ = 06-rawmessage2
"""
Extending on demo 05, request stick capabilities using raw messages.

"""

import sys
import time

from ant.core import driver
from ant.core import message
from ant.core.constants import *

from config import *

# Initialize
stick = driver.USB1Driver(SERIAL, log=LOG, debug=DEBUG)
stick.open()

# Reset stick
msg = message.SystemResetMessage()
stick.write(msg.encode())
time.sleep(1)

# Request stick capabilities
msg = message.ChannelRequestMessage()
msg.setMessageID(MESSAGE_CAPABILITIES)
stick.write(msg.encode())

# Read response
hdlfinder = message.Message()
capmsg = hdlfinder.getHandler(stick.read(8))

print 'Std Options:', capmsg.getStdOptions()
print 'Adv Options:', capmsg.getAdvOptions()
print 'Adv Options 2:', capmsg.getAdvOptions2()
print 'Max Channels:', capmsg.getMaxChannels()
print 'Max Networks:', capmsg.getMaxNetworks()

# Shutdown
stick.close()

########NEW FILE########
__FILENAME__ = 07-rawmessage3
"""
Initialize a basic broadcast slave channel for listening to
an ANT+ Bicycle cadence and speed senser, using raw messages
and event handlers.

"""

import sys
import time

from ant.core import driver
from ant.core import event
from ant.core.constants import *
from ant.core.message import *

from config import *

NETKEY = '\xB9\xA5\x21\xFB\xBD\x72\xC3\x45'

# Event callback
class MyCallback(event.EventCallback):
    def process(self, msg):
        print msg

# Initialize driver
stick = driver.USB1Driver(SERIAL, log=LOG, debug=DEBUG)
stick.open()

# Initialize event machine
evm = event.EventMachine(stick)
evm.registerCallback(MyCallback())
evm.start()

# Reset
msg = SystemResetMessage()
stick.write(msg.encode())
time.sleep(1)

# Set network key
msg = NetworkKeyMessage(key=NETKEY)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Initialize it as a receiving channel using our network key
msg = ChannelAssignMessage()
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Now set the channel id for pairing with an ANT+ bike cadence/speed sensor
msg = ChannelIDMessage(device_type=121)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Listen forever and ever (not really, but for a long time)
msg = ChannelSearchTimeoutMessage(timeout=255)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# We want a ~4.05 Hz transmission period
msg = ChannelPeriodMessage(period=8085)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# And ANT frequency 57, of course
msg = ChannelFrequencyMessage(frequency=57)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Time to go live
msg = ChannelOpenMessage()
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

print "Listening for ANT events (120 seconds)..."
time.sleep(120)

# Shutdown
msg = SystemResetMessage()
stick.write(msg.encode())
time.sleep(1)

evm.stop()
stick.close()

########NEW FILE########
__FILENAME__ = 07-rawmessage3_SparkFun
"""
Initialize a basic broadcast slave channel for listening to
an ANT+ Bicycle cadence and speed senser, using raw messages
and event handlers.

"""

import sys
import time

from ant.core import driver
from ant.core import event
from ant.core.constants import *
from ant.core.message import *

from config import *

NETKEY = '\xB9\xA5\x21\xFB\xBD\x72\xC3\x45'

# Event callback
class MyCallback(event.EventCallback):
    def process(self, msg):
        print msg

# Initialize driver
stick = driver.USB1Driver(SERIAL, log=LOG, debug=DEBUG,baud_rate=4800)
stick.open()

# Initialize event machine
evm = event.EventMachine(stick)
evm.registerCallback(MyCallback())
evm.start()

# Reset
msg = SystemResetMessage()
stick.write(msg.encode())
time.sleep(1)

# Set network key
msg = NetworkKeyMessage(key=NETKEY)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Initialize it as a receiving channel using our network key
msg = ChannelAssignMessage()
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Now set the channel id for pairing with an ANT+ bike cadence/speed sensor
msg = ChannelIDMessage(device_type=121)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Listen forever and ever (not really, but for a long time)
msg = ChannelSearchTimeoutMessage(timeout=255)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# We want a ~4.05 Hz transmission period
msg = ChannelPeriodMessage(period=8085)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# And ANT frequency 57, of course
msg = ChannelFrequencyMessage(frequency=57)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Time to go live
msg = ChannelOpenMessage()
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

print "Listening for ANT events (120 seconds)..."
time.sleep(120)

# Shutdown
msg = SystemResetMessage()
stick.write(msg.encode())
time.sleep(1)

evm.stop()
stick.close()

########NEW FILE########
__FILENAME__ = 08-rawmessage4
"""
Initialize a basic broadcast slave channel for listening to
an ANT+ HRM monitor, using raw messages.

"""

import sys
import time

from ant.core import driver
from ant.core import event
from ant.core.constants import *
from ant.core.message import *

from config import *

NETKEY = '\xB9\xA5\x21\xFB\xBD\x72\xC3\x45'

# Event callback
class MyCallback(event.EventCallback):
    def process(self, msg):
        print msg
        if isinstance(msg, ChannelBroadcastDataMessage):
            print 'Beat Count:', ord(msg.getPayload()[7])
            print 'Heart Rate:', ord(msg.getPayload()[8])

# Initialize driver
stick = driver.USB1Driver(SERIAL, log=LOG) # No debug, too much data
stick.open()

# Initialize event machine
evm = event.EventMachine(stick)
evm.registerCallback(MyCallback())
evm.start()

# Reset
msg = SystemResetMessage()
stick.write(msg.encode())
time.sleep(1)

# Set network key
msg = NetworkKeyMessage(key=NETKEY)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Initialize it as a receiving channel using our network key
msg = ChannelAssignMessage()
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Now set the channel id for pairing with an ANT+ heart rate monitor
msg = ChannelIDMessage(device_type=120)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Listen forever and ever (not really, but for a long time)
msg = ChannelSearchTimeoutMessage(timeout=255)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# We want a ~4.06 Hz transmission period
msg = ChannelPeriodMessage(period=8070)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# And ANT frequency 57, of course
msg = ChannelFrequencyMessage(frequency=57)
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Time to go live
msg = ChannelOpenMessage()
stick.write(msg.encode())
if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

print "Listening for ANT events (120 seconds)..."
time.sleep(120)

# Shutdown
msg = SystemResetMessage()
stick.write(msg.encode())
time.sleep(1)

evm.stop()
stick.close()

########NEW FILE########
__FILENAME__ = 09-logreader
"""
Read an ANT-LOG file.

"""

import sys

from ant.core import log

from config import *

# Open log
if len(sys.argv) != 2:
    print "Usage: {0} file.ant".format(sys.argv[0])
    sys.exit()

lr = log.LogReader(sys.argv[1])

event = lr.read()
while (event != None):
    if event[0] == log.EVENT_OPEN:
        title = 'EVENT_OPEN'
    elif event[0] == log.EVENT_CLOSE:
        title = 'EVENT_CLOSE'
    elif event[0] == log.EVENT_READ:
        title = 'EVENT_READ'
    elif event[0] == log.EVENT_WRITE:
        title = 'EVENT_WRITE'

    print '========== [{0}:{1}] =========='.format(title, event[1])
    if event[0] == log.EVENT_READ or event[0] == log.EVENT_WRITE:
        length = 8
        line = 0
        data = event[2]
        while data:
            row = data[:length]
            data = data[length:]
            hex_data = ['%02X' % ord(byte) for byte in row]
            print '%04X' % line, ' '.join(hex_data)

    print ''
    event = lr.read()

########NEW FILE########
__FILENAME__ = config
from ant.core import log

# USB1 ANT stick interface. Running `dmesg | tail -n 25` after plugging the
# stick on a USB port should tell you the exact interface.
SERIAL = '/dev/ttyUSB0'

# If set to True, the stick's driver will dump everything it reads/writes
# from/to the stick.
# Some demos depend on this setting being True, so unless you know what you
# are doing, leave it as is.
DEBUG = True

# Set to None to disable logging
#LOG = None
LOG = log.LogWriter()

# ========== DO NOT CHANGE ANYTHING BELOW THIS LINE ==========
print "Using log file:", LOG.filename
print ""

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# ant documentation build configuration file, created by
# sphinx-quickstart on Thu May 26 09:57:48 2011.
#
# This file is execfile()d with the current directory set to its containing
# dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

import ant

# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'ant'
copyright = u'2011, Martín Raúl Villalba'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ant.__version__
# The full version, including alpha/beta/rc tags.
release = ant.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
language = 'en'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%Y-%m-%d'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all
# documents.
default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
modindex_common_prefix = []


# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = 'Documentation for ant, version {0}' \
             .format(ant.__version__)

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = html_title

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%Y-%m-%d'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
html_additional_pages = {}

# If false, no module index is generated.
html_domain_indices = True

# If false, no index is generated.
html_use_index = True

# If true, the index is split into individual pages for each letter.
html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'ant_doc'


# -- Options for LaTeX output -------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
  ('index', 'ant.tex', u'Documentation for ant',
   u'Martín Raúl Villalba', 'manual'),
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


# -- Options for manual page output -------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'ant', u'Documentation for ant',
     [u'Martín Raúl Villalba'], 1)
]

########NEW FILE########
__FILENAME__ = constants
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

MESSAGE_TX_SYNC = 0xA4

# Configuration messages
MESSAGE_CHANNEL_UNASSIGN = 0x41
MESSAGE_CHANNEL_ASSIGN = 0x42
MESSAGE_CHANNEL_ID = 0x51
MESSAGE_CHANNEL_PERIOD = 0x43
MESSAGE_CHANNEL_SEARCH_TIMEOUT = 0x44
MESSAGE_CHANNEL_FREQUENCY = 0x45
MESSAGE_CHANNEL_TX_POWER = 0x60
MESSAGE_NETWORK_KEY = 0x46
MESSAGE_TX_POWER = 0x47
MESSAGE_PROXIMITY_SEARCH = 0x71

# Notification messages
MESSAGE_STARTUP = 0x6F

# Control messages
MESSAGE_SYSTEM_RESET = 0x4A
MESSAGE_CHANNEL_OPEN = 0x4B
MESSAGE_CHANNEL_CLOSE = 0x4C
MESSAGE_CHANNEL_REQUEST = 0x4D

# Data messages
MESSAGE_CHANNEL_BROADCAST_DATA = 0x4E
MESSAGE_CHANNEL_ACKNOWLEDGED_DATA = 0x4F
MESSAGE_CHANNEL_BURST_DATA = 0x50

# Channel event messages
MESSAGE_CHANNEL_EVENT = 0x40

# Requested response messages
MESSAGE_CHANNEL_STATUS = 0x52
#MESSAGE_CHANNEL_ID = 0x51
MESSAGE_VERSION = 0x3E
MESSAGE_CAPABILITIES = 0x54
MESSAGE_SERIAL_NUMBER = 0x61

# Message parameters
CHANNEL_TYPE_TWOWAY_RECEIVE = 0x00
CHANNEL_TYPE_TWOWAY_TRANSMIT = 0x10
CHANNEL_TYPE_SHARED_RECEIVE = 0x20
CHANNEL_TYPE_SHARED_TRANSMIT = 0x30
CHANNEL_TYPE_ONEWAY_RECEIVE = 0x40
CHANNEL_TYPE_ONEWAY_TRANSMIT = 0x50
RADIO_TX_POWER_MINUS20DB = 0x00
RADIO_TX_POWER_MINUS10DB = 0x01
RADIO_TX_POWER_0DB = 0x02
RADIO_TX_POWER_PLUS4DB = 0x03
RESPONSE_NO_ERROR = 0x00
EVENT_RX_SEARCH_TIMEOUT = 0x01
EVENT_RX_FAIL = 0x02
EVENT_TX = 0x03
EVENT_TRANSFER_RX_FAILED = 0x04
EVENT_TRANSFER_TX_COMPLETED = 0x05
EVENT_TRANSFER_TX_FAILED = 0x06
EVENT_CHANNEL_CLOSED = 0x07
EVENT_RX_FAIL_GO_TO_SEARCH = 0x08
EVENT_CHANNEL_COLLISION = 0x09
EVENT_TRANSFER_TX_START = 0x0A
CHANNEL_IN_WRONG_STATE = 0x15
CHANNEL_NOT_OPENED = 0x16
CHANNEL_ID_NOT_SET = 0x18
CLOSE_ALL_CHANNELS = 0x19
TRANSFER_IN_PROGRESS = 0x1F
TRANSFER_SEQUENCE_NUMBER_ERROR = 0x20
TRANSFER_IN_ERROR = 0x21
MESSAGE_SIZE_EXCEEDS_LIMIT = 0x27
INVALID_MESSAGE = 0x28
INVALID_NETWORK_NUMBER = 0x29
INVALID_LIST_ID = 0x30
INVALID_SCAN_TX_CHANNEL = 0x31
INVALID_PARAMETER_PROVIDED = 0x33
EVENT_QUEUE_OVERFLOW = 0x35
USB_STRING_WRITE_FAIL = 0x70
CHANNEL_STATE_UNASSIGNED = 0x00
CHANNEL_STATE_ASSIGNED = 0x01
CHANNEL_STATE_SEARCHING = 0x02
CHANNEL_STATE_TRACKING = 0x03
CAPABILITIES_NO_RECEIVE_CHANNELS = 0x01
CAPABILITIES_NO_TRANSMIT_CHANNELS = 0x02
CAPABILITIES_NO_RECEIVE_MESSAGES = 0x04
CAPABILITIES_NO_TRANSMIT_MESSAGES = 0x08
CAPABILITIES_NO_ACKNOWLEDGED_MESSAGES = 0x10
CAPABILITIES_NO_BURST_MESSAGES = 0x20
CAPABILITIES_NETWORK_ENABLED = 0x02
CAPABILITIES_SERIAL_NUMBER_ENABLED = 0x08
CAPABILITIES_PER_CHANNEL_TX_POWER_ENABLED = 0x10
CAPABILITIES_LOW_PRIORITY_SEARCH_ENABLED = 0x20
CAPABILITIES_SCRIPT_ENABLED = 0x40
CAPABILITIES_SEARCH_LIST_ENABLED = 0x80
CAPABILITIES_LED_ENABLED = 0x01
CAPABILITIES_EXT_MESSAGE_ENABLED = 0x02
CAPABILITIES_SCAN_MODE_ENABLED = 0x04
CAPABILITIES_PROX_SEARCH_ENABLED = 0x10
CAPABILITIES_EXT_ASSIGN_ENABLED = 0x20
CAPABILITIES_FS_ANTFS_ENABLED = 0x40
TIMEOUT_NEVER = 0xFF

########NEW FILE########
__FILENAME__ = driver
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

import thread

# USB1 driver uses a USB<->Serial bridge
import serial
# USB2 driver uses direct USB connection. Requires PyUSB
import usb.core
import usb.util

from ant.core.exceptions import DriverError

from array import *


class Driver(object):
    _lock = thread.allocate_lock()

    def __init__(self, device, log=None, debug=False):
        self.device = device
        self.debug = debug
        self.log = log
        self.is_open = False

    def isOpen(self):
        self._lock.acquire()
        io = self.is_open
        self._lock.release()
        return io

    def open(self):
        self._lock.acquire()

        try:
            if self.is_open:
                raise DriverError("Could not open device (already open).")

            self._open()
            self.is_open = True
            if self.log:
                self.log.logOpen()
        finally:
            self._lock.release()

    def close(self):
        self._lock.acquire()

        try:
            if not self.is_open:
                raise DriverError("Could not close device (not open).")

            self._close()
            self.is_open = False
            if self.log:
                self.log.logClose()
        finally:
            self._lock.release()

    def read(self, count):
        self._lock.acquire()

        try:
            if not self.is_open:
                raise DriverError("Could not read from device (not open).")
            if count <= 0:
                raise DriverError("Could not read from device (zero request).")

            data = self._read(count)
            if self.log:
                self.log.logRead(data)

            if self.debug:
                self._dump(data, 'READ')
        finally:
            self._lock.release()

        return data

    def write(self, data):
        self._lock.acquire()

        try:
            if not self.is_open:
                raise DriverError("Could not write to device (not open).")
            if len(data) <= 0:
                raise DriverError("Could not write to device (no data).")

            if self.debug:
                self._dump(data, 'WRITE')

            ret = self._write(data)
            if self.log:
                self.log.logWrite(data[0:ret])
        finally:
            self._lock.release()

        return ret

    def _dump(self, data, title):
        if len(data) == 0:
            return

        print '========== [{0}] =========='.format(title)

        length = 8
        line = 0
        while data:
            row = data[:length]
            data = data[length:]
            hex_data = ['%02X' % ord(byte) for byte in row]
            print '%04X' % line, ' '.join(hex_data)

        print ''

    def _open(self):
        raise DriverError("Not Implemented")

    def _close(self):
        raise DriverError("Not Implemented")

    def _read(self, count):
        raise DriverError("Not Implemented")

    def _write(self, data):
        raise DriverError("Not Implemented")


class USB1Driver(Driver):
    def __init__(self, device, baud_rate=115200, log=None, debug=False):
        Driver.__init__(self, device, log, debug)
        self.baud = baud_rate

    def _open(self):
        try:
            dev = serial.Serial(self.device, self.baud)
        except serial.SerialException, e:
            raise DriverError(str(e))

        if not dev.isOpen():
            raise DriverError('Could not open device')

        self._serial = dev
        self._serial.timeout = 0.01

    def _close(self):
        self._serial.close()

    def _read(self, count):
        return self._serial.read(count)

    def _write(self, data):
        try:
            count = self._serial.write(data)
            self._serial.flush()
        except serial.SerialTimeoutException, e:
            raise DriverError(str(e))

        return count


class USB2Driver(Driver):
    def _open(self):
        # Most of this is straight from the PyUSB example documentation		
        dev = usb.core.find(idVendor=0x0fcf, idProduct=0x1008)

        if dev is None:
            raise DriverError('Could not open device (not found)')
        dev.set_configuration()
        cfg = dev.get_active_configuration()
        interface_number = cfg[(0,0)].bInterfaceNumber
        alternate_setting = usb.control.get_interface(dev, interface_number)
        intf = usb.util.find_descriptor(
            cfg, bInterfaceNumber = interface_number,
            AlternateSetting = alternate_setting
        )
        usb.util.claim_interface(dev, interface_number)
        ep_out = usb.util.find_descriptor(
            intf,
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_OUT
        )
        assert ep_out is not None
        ep_in = usb.util.find_descriptor(
            intf,
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_IN
        )
        assert ep_in is not None
        self._ep_out = ep_out
        self._ep_in = ep_in
        self._dev = dev
        self._int = interface_number

    def _close(self):
        usb.util.release_interface(self._dev, self._int)

    def _read(self, count):
        arr_inp = array('B')
        try:
            arr_inp = self._ep_in.read(count)
        except usb.core.USBError:
            # Timeout errors seem to occasionally be expected
            pass

        return arr_inp.tostring()

    def _write(self, data):
        count = self._ep_out.write(data)

        return count

########NEW FILE########
__FILENAME__ = event
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

#
# Beware s/he who enters: uncommented, non unit-tested,
# don't-fix-it-if-it-ain't-broken kind of threaded code ahead.
#

MAX_ACK_QUEUE = 25
MAX_MSG_QUEUE = 25

import thread
import time

from ant.core.constants import *
from ant.core.message import Message, ChannelEventMessage
from ant.core.exceptions import MessageError


def ProcessBuffer(buffer_):
    messages = []

    while True:
        hf = Message()
        try:
            msg = hf.getHandler(buffer_)
            buffer_ = buffer_[len(msg.getPayload()) + 4:]
            messages.append(msg)
        except MessageError, e:
            if e.internal == "CHECKSUM":
                buffer_ = buffer_[ord(buffer_[1]) + 4:]
            else:
                break

    return (buffer_, messages,)


def EventPump(evm):
    evm.pump_lock.acquire()
    evm.pump = True
    evm.pump_lock.release()

    go = True
    buffer_ = ''
    while go:
        evm.running_lock.acquire()
        if not evm.running:
            go = False
        evm.running_lock.release()

        buffer_ += evm.driver.read(20)
        if len(buffer_) == 0:
            continue
        buffer_, messages = ProcessBuffer(buffer_)

        evm.callbacks_lock.acquire()
        for message in messages:
            for callback in evm.callbacks:
                try:
                    callback.process(message)
                except Exception, e:
                    pass

        evm.callbacks_lock.release()

        time.sleep(0.002)

    evm.pump_lock.acquire()
    evm.pump = False
    evm.pump_lock.release()


class EventCallback(object):
    def process(self, msg):
        pass


class AckCallback(EventCallback):
    def __init__(self, evm):
        self.evm = evm

    def process(self, msg):
        if isinstance(msg, ChannelEventMessage):
            self.evm.ack_lock.acquire()
            self.evm.ack.append(msg)
            if len(self.evm.ack) > MAX_ACK_QUEUE:
                self.evm.ack = self.evm.ack[-MAX_ACK_QUEUE:]
            self.evm.ack_lock.release()


class MsgCallback(EventCallback):
    def __init__(self, evm):
        self.evm = evm

    def process(self, msg):
        self.evm.msg_lock.acquire()
        self.evm.msg.append(msg)
        if len(self.evm.msg) > MAX_MSG_QUEUE:
            self.evm.msg = self.evm.msg[-MAX_MSG_QUEUE:]
        self.evm.msg_lock.release()


class EventMachine(object):
    callbacks_lock = thread.allocate_lock()
    running_lock = thread.allocate_lock()
    pump_lock = thread.allocate_lock()
    ack_lock = thread.allocate_lock()
    msg_lock = thread.allocate_lock()

    def __init__(self, driver):
        self.driver = driver
        self.callbacks = []
        self.running = False
        self.pump = False
        self.ack = []
        self.msg = []
        self.registerCallback(AckCallback(self))
        self.registerCallback(MsgCallback(self))

    def registerCallback(self, callback):
        self.callbacks_lock.acquire()
        if callback not in self.callbacks:
            self.callbacks.append(callback)
        self.callbacks_lock.release()

    def removeCallback(self, callback):
        self.callbacks_lock.acquire()
        if callback in self.callbacks:
            self.callbacks.remove(callback)
        self.callbacks_lock.release()

    def waitForAck(self, msg):
        while True:
            self.ack_lock.acquire()
            for emsg in self.ack:
                if msg.getType() != emsg.getMessageID():
                    continue
                self.ack.remove(emsg)
                self.ack_lock.release()
                return emsg.getMessageCode()
            self.ack_lock.release()
            time.sleep(0.002)

    def waitForMessage(self, class_):
        while True:
            self.msg_lock.acquire()
            for emsg in self.msg:
                if not isinstance(emsg, class_):
                    continue
                self.msg.remove(emsg)
                self.msg_lock.release()
                return emsg
            self.msg_lock.release()
            time.sleep(0.002)

    def start(self, driver=None):
        self.running_lock.acquire()

        if self.running:
            self.running_lock.release()
            return
        self.running = True
        if driver is not None:
            self.driver = driver

        thread.start_new_thread(EventPump, (self,))
        while True:
            self.pump_lock.acquire()
            if self.pump:
                self.pump_lock.release()
                break
            self.pump_lock.release()
            time.sleep(0.001)

        self.running_lock.release()

    def stop(self):
        self.running_lock.acquire()

        if not self.running:
            self.running_lock.release()
            return
        self.running = False
        self.running_lock.release()

        while True:
            self.pump_lock.acquire()
            if not self.pump:
                self.pump_lock.release()
                break
            self.pump_lock.release()
            time.sleep(0.001)

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################


class ANTException(Exception):
    pass


class DriverError(ANTException):
    pass


class MessageError(ANTException):
    def __init__(self, msg, internal=''):
        Exception.__init__(self, msg)
        self.internal = internal


class NodeError(ANTException):
    pass


class ChannelError(ANTException):
    pass

########NEW FILE########
__FILENAME__ = log
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

import time
import datetime

import msgpack

EVENT_OPEN = 0x01
EVENT_CLOSE = 0x02
EVENT_READ = 0x03
EVENT_WRITE = 0x04


class LogReader(object):
    def __init__(self, filename):
        self.is_open = False
        self.open(filename)

    def __del__(self):
        if self.is_open:
            self.fd.close()

    def open(self, filename):
        if self.is_open == True:
            self.close()

        self.fd = open(filename, 'r')
        self.is_open = True
        self.unpacker = msgpack.Unpacker()

        # Here be dragons
        self.unpacker.feed(self.fd.read())
        self.fd.close()

        header = self.unpacker.unpack()
        if len(header) != 2 or header[0] != 'ANT-LOG' or header[1] != 0x01:
            raise IOError('Could not open log file (unknown format).')

    def close(self):
        if self.is_open:
            self.fd.close()
            self.is_open = False

    def read(self):
        try:
            return self.unpacker.unpack()
        except StopIteration:
            return None


class LogWriter(object):
    def __init__(self, filename=''):
        self.packer = msgpack.Packer()
        self.is_open = False
        self.open(filename)

    def __del__(self):
        if self.is_open:
            self.fd.close()

    def open(self, filename=''):
        if filename == '':
            filename = datetime.datetime.now().isoformat() + '.ant'
        self.filename = filename

        if self.is_open == True:
            self.close()

        self.fd = open(filename, 'w')
        self.is_open = True
        self.packer = msgpack.Packer()

        header = ['ANT-LOG', 0x01]  # [MAGIC, VERSION]
        self.fd.write(self.packer.pack(header))

    def close(self):
        if self.is_open:
            self.fd.close()
            self.is_open = False

    def _logEvent(self, event, data=None):
        ev = [event, int(time.time()), data]

        if data is None:
            ev = ev[0:-1]
        elif len(data) == 0:
            return

        self.fd.write(self.packer.pack(ev))

    def logOpen(self):
        self._logEvent(EVENT_OPEN)

    def logClose(self):
        self._logEvent(EVENT_CLOSE)

    def logRead(self, data):
        self._logEvent(EVENT_READ, data)

    def logWrite(self, data):
        self._logEvent(EVENT_WRITE, data)

########NEW FILE########
__FILENAME__ = message
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

import struct

from ant.core.exceptions import MessageError
from ant.core.constants import *


class Message(object):
    def __init__(self, type_=0x00, payload=''):
        self.setType(type_)
        self.setPayload(payload)

    def getPayload(self):
        return ''.join(self.payload)

    def setPayload(self, payload):
        if len(payload) > 9:
            raise MessageError(
                  'Could not set payload (payload too long).')

        self.payload = []
        for byte in payload:
            self.payload += byte

    def getType(self):
        return self.type_

    def setType(self, type_):
        if (type_ > 0xFF) or (type_ < 0x00):
            raise MessageError('Could not set type (type out of range).')

        self.type_ = type_

    def getChecksum(self):
        data = chr(len(self.getPayload()))
        data += chr(self.getType())
        data += self.getPayload()

        checksum = MESSAGE_TX_SYNC
        for byte in data:
            checksum = (checksum ^ ord(byte)) % 0xFF

        return checksum

    def getSize(self):
        return len(self.getPayload()) + 4

    def encode(self):
        raw = struct.pack('BBB',
                          MESSAGE_TX_SYNC,
                          len(self.getPayload()),
                          self.getType())
        raw += self.getPayload()
        raw += chr(self.getChecksum())

        return raw

    def decode(self, raw):
        if len(raw) < 5:
            raise MessageError('Could not decode (message is incomplete).')

        sync, length, type_ = struct.unpack('BBB', raw[:3])

        if sync != MESSAGE_TX_SYNC:
            raise MessageError('Could not decode (expected TX sync).')
        if length > 9:
            raise MessageError('Could not decode (payload too long).')
        if len(raw) < (length + 4):
            raise MessageError('Could not decode (message is incomplete).')

        self.setType(type_)
        self.setPayload(raw[3:length + 3])

        if self.getChecksum() != ord(raw[length + 3]):
            raise MessageError('Could not decode (bad checksum).',
                               internal='CHECKSUM')

        return self.getSize()

    def getHandler(self, raw=None):
        if raw:
            self.decode(raw)

        msg = None
        if self.type_ == MESSAGE_CHANNEL_UNASSIGN:
            msg = ChannelUnassignMessage()
        elif self.type_ == MESSAGE_CHANNEL_ASSIGN:
            msg = ChannelAssignMessage()
        elif self.type_ == MESSAGE_CHANNEL_ID:
            msg = ChannelIDMessage()
        elif self.type_ == MESSAGE_CHANNEL_PERIOD:
            msg = ChannelPeriodMessage()
        elif self.type_ == MESSAGE_CHANNEL_SEARCH_TIMEOUT:
            msg = ChannelSearchTimeoutMessage()
        elif self.type_ == MESSAGE_CHANNEL_FREQUENCY:
            msg = ChannelFrequencyMessage()
        elif self.type_ == MESSAGE_CHANNEL_TX_POWER:
            msg = ChannelTXPowerMessage()
        elif self.type_ == MESSAGE_NETWORK_KEY:
            msg = NetworkKeyMessage()
        elif self.type_ == MESSAGE_TX_POWER:
            msg = TXPowerMessage()
        elif self.type_ == MESSAGE_SYSTEM_RESET:
            msg = SystemResetMessage()
        elif self.type_ == MESSAGE_CHANNEL_OPEN:
            msg = ChannelOpenMessage()
        elif self.type_ == MESSAGE_CHANNEL_CLOSE:
            msg = ChannelCloseMessage()
        elif self.type_ == MESSAGE_CHANNEL_REQUEST:
            msg = ChannelRequestMessage()
        elif self.type_ == MESSAGE_CHANNEL_BROADCAST_DATA:
            msg = ChannelBroadcastDataMessage()
        elif self.type_ == MESSAGE_CHANNEL_ACKNOWLEDGED_DATA:
            msg = ChannelAcknowledgedDataMessage()
        elif self.type_ == MESSAGE_CHANNEL_BURST_DATA:
            msg = ChannelBurstDataMessage()
        elif self.type_ == MESSAGE_CHANNEL_EVENT:
            msg = ChannelEventMessage()
        elif self.type_ == MESSAGE_CHANNEL_STATUS:
            msg = ChannelStatusMessage()
        elif self.type_ == MESSAGE_VERSION:
            msg = VersionMessage()
        elif self.type_ == MESSAGE_CAPABILITIES:
            msg = CapabilitiesMessage()
        elif self.type_ == MESSAGE_SERIAL_NUMBER:
            msg = SerialNumberMessage()
        else:
            raise MessageError('Could not find message handler ' \
                               '(unknown message type).')

        msg.setPayload(self.getPayload())
        return msg


class ChannelMessage(Message):
    def __init__(self, type_, payload='', number=0x00):
        Message.__init__(self, type_, '\x00' + payload)
        self.setChannelNumber(number)

    def getChannelNumber(self):
        return ord(self.payload[0])

    def setChannelNumber(self, number):
        if (number > 0xFF) or (number < 0x00):
            raise MessageError('Could not set channel number ' \
                                   '(out of range).')

        self.payload[0] = chr(number)


# Config messages
class ChannelUnassignMessage(ChannelMessage):
    def __init__(self, number=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_UNASSIGN,
                         number=number)


class ChannelAssignMessage(ChannelMessage):
    def __init__(self, number=0x00, type_=0x00, network=0x00):
        payload = struct.pack('BB', type_, network)
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_ASSIGN,
                                payload=payload, number=number)

    def getChannelType(self):
        return ord(self.payload[1])

    def setChannelType(self, type_):
        self.payload[1] = chr(type_)

    def getNetworkNumber(self):
        return ord(self.payload[2])

    def setNetworkNumber(self, number):
        self.payload[2] = chr(number)


class ChannelIDMessage(ChannelMessage):
    def __init__(self, number=0x00, device_number=0x0000, device_type=0x00,
                 trans_type=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_ID,
                                payload='\x00' * 4, number=number)
        self.setDeviceNumber(device_number)
        self.setDeviceType(device_type)
        self.setTransmissionType(trans_type)

    def getDeviceNumber(self):
        return struct.unpack('<H', self.getPayload()[1:3])[0]

    def setDeviceNumber(self, device_number):
        self.payload[1:3] = struct.pack('<H', device_number)

    def getDeviceType(self):
        return ord(self.payload[3])

    def setDeviceType(self, device_type):
        self.payload[3] = chr(device_type)

    def getTransmissionType(self):
        return ord(self.payload[4])

    def setTransmissionType(self, trans_type):
        self.payload[4] = chr(trans_type)


class ChannelPeriodMessage(ChannelMessage):
    def __init__(self, number=0x00, period=8192):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_PERIOD,
                                payload='\x00' * 2, number=number)
        self.setChannelPeriod(period)

    def getChannelPeriod(self):
        return struct.unpack('<H', self.getPayload()[1:3])[0]

    def setChannelPeriod(self, period):
        self.payload[1:3] = struct.pack('<H', period)


class ChannelSearchTimeoutMessage(ChannelMessage):
    def __init__(self, number=0x00, timeout=0xFF):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_SEARCH_TIMEOUT,
                                payload='\x00', number=number)
        self.setTimeout(timeout)

    def getTimeout(self):
        return ord(self.payload[1])

    def setTimeout(self, timeout):
        self.payload[1] = chr(timeout)


class ChannelFrequencyMessage(ChannelMessage):
    def __init__(self, number=0x00, frequency=66):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_FREQUENCY,
                                payload='\x00', number=number)
        self.setFrequency(frequency)

    def getFrequency(self):
        return ord(self.payload[1])

    def setFrequency(self, frequency):
        self.payload[1] = chr(frequency)


class ChannelTXPowerMessage(ChannelMessage):
    def __init__(self, number=0x00, power=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_TX_POWER,
                                payload='\x00', number=number)

    def getPower(self):
        return ord(self.payload[1])

    def setPower(self, power):
        self.payload[1] = chr(power)


class NetworkKeyMessage(Message):
    def __init__(self, number=0x00, key='\x00' * 8):
        Message.__init__(self, type_=MESSAGE_NETWORK_KEY, payload='\x00' * 9)
        self.setNumber(number)
        self.setKey(key)

    def getNumber(self):
        return ord(self.payload[0])

    def setNumber(self, number):
        self.payload[0] = chr(number)

    def getKey(self):
        return self.getPayload()[1:]

    def setKey(self, key):
        self.payload[1:] = key


class TXPowerMessage(Message):
    def __init__(self, power=0x00):
        Message.__init__(self, type_=MESSAGE_TX_POWER, payload='\x00\x00')
        self.setPower(power)

    def getPower(self):
        return ord(self.payload[1])

    def setPower(self, power):
        self.payload[1] = chr(power)


# Control messages
class SystemResetMessage(Message):
    def __init__(self):
        Message.__init__(self, type_=MESSAGE_SYSTEM_RESET, payload='\x00')


class ChannelOpenMessage(ChannelMessage):
    def __init__(self, number=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_OPEN,
                                number=number)


class ChannelCloseMessage(ChannelMessage):
    def __init__(self, number=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_CLOSE,
                                number=number)


class ChannelRequestMessage(ChannelMessage):
    def __init__(self, number=0x00, message_id=MESSAGE_CHANNEL_STATUS):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_REQUEST,
                                number=number, payload='\x00')
        self.setMessageID(message_id)

    def getMessageID(self):
        return ord(self.payload[1])

    def setMessageID(self, message_id):
        if (message_id > 0xFF) or (message_id < 0x00):
            raise MessageError('Could not set message ID ' \
                                   '(out of range).')

        self.payload[1] = chr(message_id)


class RequestMessage(ChannelRequestMessage):
    pass


# Data messages
class ChannelBroadcastDataMessage(ChannelMessage):
    def __init__(self, number=0x00, data='\x00' * 7):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_BROADCAST_DATA,
                                payload=data, number=number)


class ChannelAcknowledgedDataMessage(ChannelMessage):
    def __init__(self, number=0x00, data='\x00' * 7):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_ACKNOWLEDGED_DATA,
                                payload=data, number=number)


class ChannelBurstDataMessage(ChannelMessage):
    def __init__(self, number=0x00, data='\x00' * 7):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_BURST_DATA,
                                payload=data, number=number)


# Channel event messages
class ChannelEventMessage(ChannelMessage):
    def __init__(self, number=0x00, message_id=0x00, message_code=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_EVENT,
                                number=number, payload='\x00\x00')
        self.setMessageID(message_id)
        self.setMessageCode(message_code)

    def getMessageID(self):
        return ord(self.payload[1])

    def setMessageID(self, message_id):
        if (message_id > 0xFF) or (message_id < 0x00):
            raise MessageError('Could not set message ID ' \
                                   '(out of range).')

        self.payload[1] = chr(message_id)

    def getMessageCode(self):
        return ord(self.payload[2])

    def setMessageCode(self, message_code):
        if (message_code > 0xFF) or (message_code < 0x00):
            raise MessageError('Could not set message code ' \
                                   '(out of range).')

        self.payload[2] = chr(message_code)


# Requested response messages
class ChannelStatusMessage(ChannelMessage):
    def __init__(self, number=0x00, status=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_STATUS,
                                payload='\x00', number=number)
        self.setStatus(status)

    def getStatus(self):
        return ord(self.payload[1])

    def setStatus(self, status):
        if (status > 0xFF) or (status < 0x00):
            raise MessageError('Could not set channel status ' \
                                   '(out of range).')

        self.payload[1] = chr(status)

#class ChannelIDMessage(ChannelMessage):


class VersionMessage(Message):
    def __init__(self, version='\x00' * 9):
        Message.__init__(self, type_=MESSAGE_VERSION, payload='\x00' * 9)
        self.setVersion(version)

    def getVersion(self):
        return self.getPayload()

    def setVersion(self, version):
        if (len(version) != 9):
            raise MessageError('Could not set ANT version ' \
                               '(expected 9 bytes).')

        self.setPayload(version)


class CapabilitiesMessage(Message):
    def __init__(self, max_channels=0x00, max_nets=0x00, std_opts=0x00,
                 adv_opts=0x00, adv_opts2=0x00):
        Message.__init__(self, type_=MESSAGE_CAPABILITIES, payload='\x00' * 4)
        self.setMaxChannels(max_channels)
        self.setMaxNetworks(max_nets)
        self.setStdOptions(std_opts)
        self.setAdvOptions(adv_opts)
        if adv_opts2 is not None:
            self.setAdvOptions2(adv_opts2)

    def getMaxChannels(self):
        return ord(self.payload[0])

    def getMaxNetworks(self):
        return ord(self.payload[1])

    def getStdOptions(self):
        return ord(self.payload[2])

    def getAdvOptions(self):
        return ord(self.payload[3])

    def getAdvOptions2(self):
        return ord(self.payload[4]) if len(self.payload) == 5 else 0x00

    def setMaxChannels(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set max channels ' \
                                   '(out of range).')

        self.payload[0] = chr(num)

    def setMaxNetworks(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set max networks ' \
                                   '(out of range).')

        self.payload[1] = chr(num)

    def setStdOptions(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set std options ' \
                                   '(out of range).')

        self.payload[2] = chr(num)

    def setAdvOptions(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set adv options ' \
                                   '(out of range).')

        self.payload[3] = chr(num)

    def setAdvOptions2(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set adv options 2 ' \
                                   '(out of range).')

        if len(self.payload) == 4:
            self.payload.append('\x00')
        self.payload[4] = chr(num)


class SerialNumberMessage(Message):
    def __init__(self, serial='\x00' * 4):
        Message.__init__(self, type_=MESSAGE_SERIAL_NUMBER)
        self.setSerialNumber(serial)

    def getSerialNumber(self):
        return self.getPayload()

    def setSerialNumber(self, serial):
        if (len(serial) != 4):
            raise MessageError('Could not set serial number ' \
                               '(expected 4 bytes).')

        self.setPayload(serial)

########NEW FILE########
__FILENAME__ = node
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

import time
import thread
import uuid

from ant.core.constants import *
from ant.core.exceptions import *
from ant.core import message
from ant.core import event


class NetworkKey(object):
    def __init__(self, name=None, key='\x00' * 8):
        self.key = key
        if name:
            self.name = name
        else:
            self.name = str(uuid.uuid4())
        self.number = 0


class Channel(event.EventCallback):
    cb_lock = thread.allocate_lock()

    def __init__(self, node):
        self.node = node
        self.is_free = True
        self.name = str(uuid.uuid4())
        self.number = 0
        self.cb = []
        self.node.evm.registerCallback(self)

    def __del__(self):
        self.node.evm.removeCallback(self)

    def assign(self, net_key, ch_type):
        msg = message.ChannelAssignMessage(number=self.number)
        msg.setNetworkNumber(self.node.getNetworkKey(net_key).number)
        msg.setChannelType(ch_type)
        self.node.driver.write(msg.encode())
        if self.node.evm.waitForAck(msg) != RESPONSE_NO_ERROR:
            raise ChannelError('Could not assign channel.')
        self.is_free = False

    def setID(self, dev_type, dev_num, trans_type):
        msg = message.ChannelIDMessage(number=self.number)
        msg.setDeviceType(dev_type)
        msg.setDeviceNumber(dev_num)
        msg.setTransmissionType(trans_type)
        self.node.driver.write(msg.encode())
        if self.node.evm.waitForAck(msg) != RESPONSE_NO_ERROR:
            raise ChannelError('Could not set channel ID.')

    def setSearchTimeout(self, timeout):
        msg = message.ChannelSearchTimeoutMessage(number=self.number)
        msg.setTimeout(timeout)
        self.node.driver.write(msg.encode())
        if self.node.evm.waitForAck(msg) != RESPONSE_NO_ERROR:
            raise ChannelError('Could not set channel search timeout.')

    def setPeriod(self, counts):
        msg = message.ChannelPeriodMessage(number=self.number)
        msg.setChannelPeriod(counts)
        self.node.driver.write(msg.encode())
        if self.node.evm.waitForAck(msg) != RESPONSE_NO_ERROR:
            raise ChannelError('Could not set channel period.')

    def setFrequency(self, frequency):
        msg = message.ChannelFrequencyMessage(number=self.number)
        msg.setFrequency(frequency)
        self.node.driver.write(msg.encode())
        if self.node.evm.waitForAck(msg) != RESPONSE_NO_ERROR:
            raise ChannelError('Could not set channel frequency.')

    def open(self):
        msg = message.ChannelOpenMessage(number=self.number)
        self.node.driver.write(msg.encode())
        if self.node.evm.waitForAck(msg) != RESPONSE_NO_ERROR:
            raise ChannelError('Could not open channel.')

    def close(self):
        msg = message.ChannelCloseMessage(number=self.number)
        self.node.driver.write(msg.encode())
        if self.node.evm.waitForAck(msg) != RESPONSE_NO_ERROR:
            raise ChannelError('Could not close channel.')

        while True:
            msg = self.node.evm.waitForMessage(message.ChannelEventMessage)
            if msg.getMessageCode() == EVENT_CHANNEL_CLOSED:
                break

    def unassign(self):
        msg = message.ChannelUnassignMessage(number=self.number)
        self.node.driver.write(msg.encode())
        if self.node.evm.waitForAck(msg) != RESPONSE_NO_ERROR:
            raise ChannelError('Could not unassign channel.')
        self.is_free = True

    def registerCallback(self, callback):
        self.cb_lock.acquire()
        if callback not in self.cb:
            self.cb.append(callback)
        self.cb_lock.release()

    def process(self, msg):
        self.cb_lock.acquire()
        if isinstance(msg, message.ChannelMessage) and \
        msg.getChannelNumber() == self.number:
            for callback in self.cb:
                try:
                    callback.process(msg)
                except:
                    pass  # Who cares?
        self.cb_lock.release()


class Node(event.EventCallback):
    node_lock = thread.allocate_lock()

    def __init__(self, driver):
        self.driver = driver
        self.evm = event.EventMachine(self.driver)
        self.evm.registerCallback(self)
        self.networks = []
        self.channels = []
        self.running = False
        self.options = [0x00, 0x00, 0x00]

    def start(self):
        if self.running:
            raise NodeError('Could not start ANT node (already started).')

        if not self.driver.isOpen():
            self.driver.open()

        self.reset()
        self.evm.start()
        self.running = True
        self.init()

    def stop(self, reset=True):
        if not self.running:
            raise NodeError('Could not stop ANT node (not started).')

        if reset:
            self.reset()
        self.evm.stop()
        self.running = False
        self.driver.close()

    def reset(self):
        msg = message.SystemResetMessage()
        self.driver.write(msg.encode())
        time.sleep(1)

    def init(self):
        if not self.running:
            raise NodeError('Could not reset ANT node (not started).')

        msg = message.ChannelRequestMessage()
        msg.setMessageID(MESSAGE_CAPABILITIES)
        self.driver.write(msg.encode())

        caps = self.evm.waitForMessage(message.CapabilitiesMessage)

        self.networks = []
        for i in range(0, caps.getMaxNetworks()):
            self.networks.append(NetworkKey())
            self.setNetworkKey(i)
        self.channels = []
        for i in range(0, caps.getMaxChannels()):
            self.channels.append(Channel(self))
            self.channels[i].number = i
        self.options = (caps.getStdOptions(),
                        caps.getAdvOptions(),
                        caps.getAdvOptions2(),)

    def getCapabilities(self):
        return (len(self.channels),
                len(self.networks),
                self.options,)

    def setNetworkKey(self, number, key=None):
        if key:
            self.networks[number] = key

        msg = message.NetworkKeyMessage()
        msg.setNumber(number)
        msg.setKey(self.networks[number].key)
        self.driver.write(msg.encode())
        self.evm.waitForAck(msg)
        self.networks[number].number = number

    def getNetworkKey(self, name):
        for netkey in self.networks:
            if netkey.name == name:
                return netkey
        raise NodeError('Could not find network key with the supplied name.')

    def getFreeChannel(self):
        for channel in self.channels:
            if channel.is_free:
                return channel
        raise NodeError('Could not find free channel.')

    def registerEventListener(self, callback):
        self.evm.registerCallback(callback)

    def process(self, msg):
        pass

########NEW FILE########
__FILENAME__ = driver_tests
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

import unittest

from ant.core.driver import *


class DummyDriver(Driver):
    def _open(self):
        pass

    def _close(self):
        pass

    def _read(self, count):
        return '\x00' * count

    def _write(self, data):
        return len(data)


class DriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = DummyDriver('superdrive')

    def tearDown(self):
        pass

    def test_isOpen(self):
        self.assertFalse(self.driver.isOpen())
        self.driver.open()
        self.assertTrue(self.driver.isOpen())
        self.driver.close()
        self.assertFalse(self.driver.isOpen())

    def test_open(self):
        self.driver.open()
        self.assertRaises(DriverError, self.driver.open)
        self.driver.close()

    def test_close(self):
        pass    # Nothing to test for

    def test_read(self):
        self.assertFalse(self.driver.isOpen())
        self.assertRaises(DriverError, self.driver.read, 1)
        self.driver.open()
        self.assertEqual(len(self.driver.read(5)), 5)
        self.assertRaises(DriverError, self.driver.read, -1)
        self.assertRaises(DriverError, self.driver.read, 0)
        self.driver.close()

    def test_write(self):
        self.assertRaises(DriverError, self.driver.write, '\xFF')
        self.driver.open()
        self.assertRaises(DriverError, self.driver.write, '')
        self.assertEquals(self.driver.write('\xFF' * 10), 10)
        self.driver.close()


# How do you even test this without hardware?
class USB1DriverTest(unittest.TestCase):
    def _open(self):
        pass

    def _close(self):
        pass

    def _read(self):
        pass

    def _write(self):
        pass

########NEW FILE########
__FILENAME__ = event_tests
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

import unittest

from ant.core.event import *

#TODO: How exactly do you properly test threaded code?

########NEW FILE########
__FILENAME__ = log_tests
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

LOG_LOCATION = '/tmp/python-ant.logtest.ant'

import unittest

from ant.core.log import *


class LogReaderTest(unittest.TestCase):
    def setUp(self):
        lw = LogWriter(LOG_LOCATION)
        lw.logOpen()
        lw.logRead('\x01')
        lw.logWrite('\x00')
        lw.logRead('TEST')
        lw.logClose()
        lw.close()

        self.log = LogReader(LOG_LOCATION)

    def test_open_close(self):
        self.assertTrue(self.log.is_open)
        self.log.close()
        self.assertFalse(self.log.is_open)
        self.log.open(LOG_LOCATION)
        self.assertTrue(self.log.is_open)

    def test_read(self):
        t1 = self.log.read()
        t2 = self.log.read()
        t3 = self.log.read()
        t4 = self.log.read()
        t5 = self.log.read()

        self.assertEquals(self.log.read(), None)

        self.assertEquals(t1[0], EVENT_OPEN)
        self.assertTrue(isinstance(t1[1], int))
        self.assertEquals(len(t1), 2)

        self.assertEquals(t2[0], EVENT_READ)
        self.assertTrue(isinstance(t1[1], int))
        self.assertEquals(len(t2), 3)
        self.assertEquals(t2[2], '\x01')

        self.assertEquals(t3[0], EVENT_WRITE)
        self.assertTrue(isinstance(t1[1], int))
        self.assertEquals(len(t3), 3)
        self.assertEquals(t3[2], '\x00')

        self.assertEquals(t4[0], EVENT_READ)
        self.assertEquals(t4[2], 'TEST')

        self.assertEquals(t5[0], EVENT_CLOSE)
        self.assertTrue(isinstance(t1[1], int))
        self.assertEquals(len(t5), 2)


class LogWriterTest(unittest.TestCase):
    def setUp(self):
        self.log = LogWriter(LOG_LOCATION)

    def test_open_close(self):
        self.assertTrue(self.log.is_open)
        self.log.close()
        self.assertFalse(self.log.is_open)
        self.log.open(LOG_LOCATION)
        self.assertTrue(self.log.is_open)

    def test_log(self):
        # Redundant, any error in log* methods will cause the LogReader test
        # suite to fail.
        pass

########NEW FILE########
__FILENAME__ = message_tests
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

import unittest

from ant.core.message import *


class MessageTest(unittest.TestCase):
    def setUp(self):
        self.message = Message()

    def test_get_setPayload(self):
        self.assertRaises(MessageError, self.message.setPayload,
                          '\xFF' * 15)
        self.message.setPayload('\x11' * 5)
        self.assertEquals(self.message.getPayload(), '\x11' * 5)

    def test_get_setType(self):
        self.assertRaises(MessageError, self.message.setType, -1)
        self.assertRaises(MessageError, self.message.setType, 300)
        self.message.setType(0x23)
        self.assertEquals(self.message.getType(), 0x23)

    def test_getChecksum(self):
        self.message = Message(type_=MESSAGE_SYSTEM_RESET, payload='\x00')
        self.assertEquals(self.message.getChecksum(), 0xEF)
        self.message = Message(type_=MESSAGE_CHANNEL_ASSIGN,
                               payload='\x00' * 3)
        self.assertEquals(self.message.getChecksum(), 0xE5)

    def test_getSize(self):
        self.message.setPayload('\x11' * 7)
        self.assertEquals(self.message.getSize(), 11)

    def test_encode(self):
        self.message = Message(type_=MESSAGE_CHANNEL_ASSIGN,
                               payload='\x00' * 3)
        self.assertEqual(self.message.encode(),
                         '\xA4\x03\x42\x00\x00\x00\xE5')

    def test_decode(self):
        self.assertRaises(MessageError, self.message.decode,
                          '\xA5\x03\x42\x00\x00\x00\xE5')
        self.assertRaises(MessageError, self.message.decode,
                          '\xA4\x14\x42' + ('\x00' * 20) + '\xE5')
        self.assertRaises(MessageError, self.message.decode,
                          '\xA4\x03\x42\x01\x02\xF3\xE5')
        self.assertEqual(self.message.decode('\xA4\x03\x42\x00\x00\x00\xE5'),
                         7)
        self.assertEqual(self.message.getType(), MESSAGE_CHANNEL_ASSIGN)
        self.assertEqual(self.message.getPayload(), '\x00' * 3)
        self.assertEqual(self.message.getChecksum(), 0xE5)

    def test_getHandler(self):
        handler = self.message.getHandler('\xA4\x03\x42\x00\x00\x00\xE5')
        self.assertTrue(isinstance(handler, ChannelAssignMessage))
        self.assertRaises(MessageError, self.message.getHandler,
                          '\xA4\x03\xFF\x00\x00\x00\xE5')
        self.assertRaises(MessageError, self.message.getHandler,
                          '\xA4\x03\x42')
        self.assertRaises(MessageError, self.message.getHandler,
                          '\xA4\x05\x42\x00\x00\x00\x00')


class ChannelMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = ChannelMessage(type_=MESSAGE_SYSTEM_RESET)

    def test_get_setChannelNumber(self):
        self.assertEquals(self.message.getChannelNumber(), 0)
        self.message.setChannelNumber(3)
        self.assertEquals(self.message.getChannelNumber(), 3)


class ChannelUnassignMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelAssignMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = ChannelAssignMessage()

    def test_get_setChannelType(self):
        self.message.setChannelType(0x10)
        self.assertEquals(self.message.getChannelType(), 0x10)

    def test_get_setNetworkNumber(self):
        self.message.setNetworkNumber(0x11)
        self.assertEquals(self.message.getNetworkNumber(), 0x11)

    def test_payload(self):
        self.message.setChannelNumber(0x01)
        self.message.setChannelType(0x02)
        self.message.setNetworkNumber(0x03)
        self.assertEquals(self.message.getPayload(), '\x01\x02\x03')


class ChannelIDMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = ChannelIDMessage()

    def test_get_setDeviceNumber(self):
        self.message.setDeviceNumber(0x10FA)
        self.assertEquals(self.message.getDeviceNumber(), 0x10FA)

    def test_get_setDeviceType(self):
        self.message.setDeviceType(0x10)
        self.assertEquals(self.message.getDeviceType(), 0x10)

    def test_get_setTransmissionType(self):
        self.message.setTransmissionType(0x11)
        self.assertEquals(self.message.getTransmissionType(), 0x11)

    def test_payload(self):
        self.message.setChannelNumber(0x01)
        self.message.setDeviceNumber(0x0302)
        self.message.setDeviceType(0x04)
        self.message.setTransmissionType(0x05)
        self.assertEquals(self.message.getPayload(), '\x01\x02\x03\x04\x05')


class ChannelPeriodMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = ChannelPeriodMessage()

    def test_get_setChannelPeriod(self):
        self.message.setChannelPeriod(0x10FA)
        self.assertEquals(self.message.getChannelPeriod(), 0x10FA)

    def test_payload(self):
        self.message.setChannelNumber(0x01)
        self.message.setChannelPeriod(0x0302)
        self.assertEquals(self.message.getPayload(), '\x01\x02\x03')


class ChannelSearchTimeoutMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = ChannelSearchTimeoutMessage()

    def test_get_setTimeout(self):
        self.message.setTimeout(0x10)
        self.assertEquals(self.message.getTimeout(), 0x10)

    def test_payload(self):
        self.message.setChannelNumber(0x01)
        self.message.setTimeout(0x02)
        self.assertEquals(self.message.getPayload(), '\x01\x02')


class ChannelFrequencyMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = ChannelFrequencyMessage()

    def test_get_setFrequency(self):
        self.message.setFrequency(22)
        self.assertEquals(self.message.getFrequency(), 22)

    def test_payload(self):
        self.message.setChannelNumber(0x01)
        self.message.setFrequency(0x02)
        self.assertEquals(self.message.getPayload(), '\x01\x02')


class ChannelTXPowerMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = ChannelTXPowerMessage()

    def test_get_setPower(self):
        self.message.setPower(0xFA)
        self.assertEquals(self.message.getPower(), 0xFA)

    def test_payload(self):
        self.message.setChannelNumber(0x01)
        self.message.setPower(0x02)
        self.assertEquals(self.message.getPayload(), '\x01\x02')


class NetworkKeyMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = NetworkKeyMessage()

    def test_get_setNumber(self):
        self.message.setNumber(0xFA)
        self.assertEquals(self.message.getNumber(), 0xFA)

    def test_get_setKey(self):
        self.message.setKey('\xFD' * 8)
        self.assertEquals(self.message.getKey(), '\xFD' * 8)

    def test_payload(self):
        self.message.setNumber(0x01)
        self.message.setKey('\x02\x03\x04\x05\x06\x07\x08\x09')
        self.assertEquals(self.message.getPayload(),
                          '\x01\x02\x03\x04\x05\x06\x07\x08\x09')


class TXPowerMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = TXPowerMessage()

    def test_get_setPower(self):
        self.message.setPower(0xFA)
        self.assertEquals(self.message.getPower(), 0xFA)

    def test_payload(self):
        self.message.setPower(0x01)
        self.assertEquals(self.message.getPayload(), '\x00\x01')


class SystemResetMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelOpenMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelCloseMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelRequestMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = ChannelRequestMessage()

    def test_get_setMessageID(self):
        self.message.setMessageID(0xFA)
        self.assertEquals(self.message.getMessageID(), 0xFA)
        self.assertRaises(MessageError, self.message.setMessageID, 0xFFFF)

    def test_payload(self):
        self.message.setChannelNumber(0x01)
        self.message.setMessageID(0x02)
        self.assertEquals(self.message.getPayload(), '\x01\x02')


class ChannelBroadcastDataMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelAcknowledgedDataMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelBurstDataMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelEventMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = ChannelEventMessage()

    def test_get_setMessageID(self):
        self.message.setMessageID(0xFA)
        self.assertEquals(self.message.getMessageID(), 0xFA)
        self.assertRaises(MessageError, self.message.setMessageID, 0xFFFF)

    def test_get_setMessageCode(self):
        self.message.setMessageCode(0xFA)
        self.assertEquals(self.message.getMessageCode(), 0xFA)
        self.assertRaises(MessageError, self.message.setMessageCode, 0xFFFF)

    def test_payload(self):
        self.message.setChannelNumber(0x01)
        self.message.setMessageID(0x02)
        self.message.setMessageCode(0x03)
        self.assertEquals(self.message.getPayload(), '\x01\x02\x03')


class ChannelStatusMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = ChannelStatusMessage()

    def test_get_setStatus(self):
        self.message.setStatus(0xFA)
        self.assertEquals(self.message.getStatus(), 0xFA)
        self.assertRaises(MessageError, self.message.setStatus, 0xFFFF)

    def test_payload(self):
        self.message.setChannelNumber(0x01)
        self.message.setStatus(0x02)
        self.assertEquals(self.message.getPayload(), '\x01\x02')


class VersionMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = VersionMessage()

    def test_get_setVersion(self):
        self.message.setVersion('\xAB' * 9)
        self.assertEquals(self.message.getVersion(), '\xAB' * 9)
        self.assertRaises(MessageError, self.message.setVersion, '1234')

    def test_payload(self):
        self.message.setVersion('\x01' * 9)
        self.assertEquals(self.message.getPayload(), '\x01' * 9)


class CapabilitiesMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = CapabilitiesMessage()

    def test_get_setMaxChannels(self):
        self.message.setMaxChannels(0xFA)
        self.assertEquals(self.message.getMaxChannels(), 0xFA)
        self.assertRaises(MessageError, self.message.setMaxChannels, 0xFFFF)

    def test_get_setMaxNetworks(self):
        self.message.setMaxNetworks(0xFA)
        self.assertEquals(self.message.getMaxNetworks(), 0xFA)
        self.assertRaises(MessageError, self.message.setMaxNetworks, 0xFFFF)

    def test_get_setStdOptions(self):
        self.message.setStdOptions(0xFA)
        self.assertEquals(self.message.getStdOptions(), 0xFA)
        self.assertRaises(MessageError, self.message.setStdOptions, 0xFFFF)

    def test_get_setAdvOptions(self):
        self.message.setAdvOptions(0xFA)
        self.assertEquals(self.message.getAdvOptions(), 0xFA)
        self.assertRaises(MessageError, self.message.setAdvOptions, 0xFFFF)

    def test_get_setAdvOptions2(self):
        self.message.setAdvOptions2(0xFA)
        self.assertEquals(self.message.getAdvOptions2(), 0xFA)
        self.assertRaises(MessageError, self.message.setAdvOptions2, 0xFFFF)
        self.message = CapabilitiesMessage(adv_opts2=None)
        self.assertEquals(len(self.message.payload), 4)

    def test_payload(self):
        self.message.setMaxChannels(0x01)
        self.message.setMaxNetworks(0x02)
        self.message.setStdOptions(0x03)
        self.message.setAdvOptions(0x04)
        self.message.setAdvOptions2(0x05)
        self.assertEquals(self.message.getPayload(), '\x01\x02\x03\x04\x05')


class SerialNumberMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = SerialNumberMessage()

    def test_get_setSerialNumber(self):
        self.message.setSerialNumber('\xFA\xFB\xFC\xFD')
        self.assertEquals(self.message.getSerialNumber(), '\xFA\xFB\xFC\xFD')
        self.assertRaises(MessageError, self.message.setSerialNumber,
                          '\xFF' * 8)

    def test_payload(self):
        self.message.setSerialNumber('\x01\x02\x03\x04')
        self.assertEquals(self.message.getPayload(), '\x01\x02\x03\x04')

########NEW FILE########
__FILENAME__ = node_tests
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

import unittest

from ant.core.node import *

#TODO

########NEW FILE########
